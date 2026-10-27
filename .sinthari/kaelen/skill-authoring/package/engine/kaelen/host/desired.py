"""What a capability should look like on a host: declaration × targets × placement rule.

Every location comes from the placement rule the engine carries, rendered by the wrapper the rule
names (specs/017 FR-008); a location relied on by several targets is one placement with every
target recorded (FR-010). Nothing here touches the host.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from kaelen.host import home as homes
from kaelen.host import render as renderers
from kaelen.host import runtime, sections
from kaelen.host.jsonspan import canonical_digest
from kaelen.host.render import RenderError
from kaelen.outcome import Problem
from kaelen.package.record import digest_tree
from kaelen.placement import PLACED, place_item, with_source_suffix

# Section styles by wrapper; JSON wrappers are members or elements.
_STYLE = {"markdown-section": "markdown", "mcp-toml-entry": "hash", "git-section": "hash"}


@dataclass
class Placement:
    path: str
    form: str  # file | directory
    ownership: str  # owned | section
    style: str | None  # markdown | hash | json-member | json-element (sections only)
    address: str | None
    item: dict
    wrapper: str
    content: object  # bytes, [(rel, bytes)], or str for sections
    digest: str
    targets: list[str] = field(default_factory=list)
    json_path: list[str] | None = None
    json_key: str | None = None

    @property
    def key(self) -> tuple[str, str]:
        return (self.path, self.address or "")


def sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def content_digest(form: str, style: str | None, content) -> str:
    if style in ("markdown", "hash"):
        return sections.digest(content)
    if style in ("json-member", "json-element"):
        return canonical_digest(json.loads(content))
    if form == "directory":
        return digest_tree(content)
    return sha(content)


def _applies(item: dict, target: str, document: dict) -> bool:
    return target in item.get("targets", document["targets"])


def desired(pkg, targets: list[str]) -> tuple[list[Placement], list[dict], list[Problem]]:
    """(placements, unsupported entries, findings) for `targets`, in a deterministic order."""
    document = pkg.document
    capability, node = document["capability"], document["node"]
    placements: dict[tuple[str, str], Placement] = {}
    unsupported: list[dict] = []
    findings: list[Problem] = []
    also: dict[str, list[str]] = {}
    for target in targets:
        for i, item in enumerate(document["items"]):
            if not _applies(item, target, document):
                continue
            answer = place_item(target, item, capability, node)
            ref = {"kind": item["kind"], "name": item["name"]}
            if answer["outcome"] != PLACED:
                unsupported.append({"item": ref, "target": target, "reason": answer["reason"]})
                findings.append(
                    Problem(
                        "unsupported-on-target",
                        f"items[{i}]",
                        f"{item['kind']} {item['name']!r}: not supported on {target} "
                        f"({answer['reason']}): {answer['detail']}",
                    )
                )
                continue
            also.setdefault(target, []).extend(answer.get("also_reads") or [])
            data = pkg.content(item)
            if item["kind"] == "mcp-server" and item.get("entry"):
                data = runtime.mcp_definition(data, node, capability, item["entry"])
            locations = [_as_source(loc, item, data) for loc in answer["locations"]]
            script = next((loc["path"] for loc in locations if loc["wrapper"] == "verbatim"), None)
            try:
                made = []
                for loc in locations:
                    context = {
                        "capability": capability,
                        "name": item["name"],
                        "section": loc["section"],
                        "script": script,
                        "launcher": runtime.launcher_rel(node, capability)
                        if item.get("runtime")
                        else None,
                    }
                    made.append((loc, renderers.render(loc["wrapper"], data, context)))
            except RenderError as exc:
                unsupported.append({"item": ref, "target": target, "reason": "render-refused"})
                findings.append(
                    Problem(
                        "render-refused",
                        f"items[{i}]",
                        f"{item['kind']} {item['name']!r} on {target}: {exc}",
                    )
                )
                continue
            for loc, out in made:
                p = _placement(loc, out, ref)
                existing = placements.get(p.key)
                if existing is None:
                    p.targets = [target]
                    placements[p.key] = p
                elif existing.digest != p.digest:
                    raise RuntimeError(f"{p.path}: two targets render different content")
                elif target not in existing.targets:
                    existing.targets.append(target)
    if len(targets) > 1:
        findings.extend(_double_loading(list(placements.values()), also))
    if document.get("runtime") and targets:
        for p in _runtime_placements(pkg, list(targets)):
            placements[p.key] = p
    if targets:
        deposit = _deposit(pkg, list(targets))
        placements[deposit.key] = deposit
    return sorted(placements.values(), key=lambda p: p.key), unsupported, findings


def _deposit(pkg, targets: list[str]) -> Placement:
    """The whole package, kept in the capability's home so its own engine can uninstall, verify and
    roll it back without the producer (specs/026 R-3)."""
    document = pkg.document
    files = pkg.files()
    return Placement(
        homes.new(document["node"], document["capability"]).package,
        "directory",
        "owned",
        None,
        None,
        {"kind": "package", "name": document["capability"]},
        "verbatim",
        files,
        digest_tree(files),
        targets=list(targets),
    )


def _runtime_placements(pkg, targets: list[str]) -> list[Placement]:
    """The environment (form `runtime`) and its committed launcher (specs/022 research R-3)."""
    document = pkg.document
    capability = document["capability"]
    recipe = runtime.recipe(
        document,
        read_file=lambda rel: pkg.content({"kind": "runtime", "source": rel}),
        read_tree=lambda rel: pkg.content({"kind": "runtime", "source": rel}),
    )
    launcher = runtime.launcher_bytes(capability, recipe["entry_points"])
    return [
        Placement(
            runtime.runtime_rel(document["node"], capability),
            "runtime",
            "owned",
            None,
            None,
            {"kind": "runtime", "name": capability},
            "runtime",
            recipe,
            runtime.recipe_digest(recipe),
            targets=list(targets),
        ),
        Placement(
            runtime.launcher_rel(document["node"], capability),
            "file",
            "owned",
            None,
            None,
            {"kind": "runtime", "name": "launcher"},
            "verbatim",
            launcher,
            sha(launcher),
            targets=list(targets),
        ),
    ]


def _as_source(loc: dict, item: dict, data) -> dict:
    return with_source_suffix(loc, item, isinstance(data, bytes))


def _placement(loc: dict, out, item: dict) -> Placement:
    path = loc["path"].rstrip("/")
    if out.kind in ("file", "tree"):
        form = "directory" if out.kind == "tree" else "file"
        ownership = "owned" if loc["shared"] is None else "section"
        return Placement(
            path,
            form,
            ownership,
            None,
            None,
            item,
            loc["wrapper"],
            out.data,
            content_digest(form, None, out.data),
        )
    if out.kind == "section":
        style = _STYLE[loc["wrapper"]]
        return Placement(
            path,
            "file",
            "section",
            style,
            out.address,
            item,
            loc["wrapper"],
            out.data,
            content_digest("file", style, out.data),
        )
    digest = canonical_digest(json.loads(out.data))
    if out.kind == "member":
        address = ".".join([*out.path, out.key])
        return Placement(
            path,
            "file",
            "section",
            "json-member",
            address,
            item,
            loc["wrapper"],
            out.data,
            digest,
            json_path=out.path,
            json_key=out.key,
        )
    address = ".".join(out.path) + f"[{digest}]"
    return Placement(
        path,
        "file",
        "section",
        "json-element",
        address,
        item,
        loc["wrapper"],
        out.data,
        digest,
        json_path=out.path,
    )


def _double_loading(placements: list[Placement], also: dict[str, list[str]]) -> list[Problem]:
    """A location one target also reads, holding another target's item (FR-011)."""
    findings = []
    for target, reads in sorted(also.items()):
        for p in placements:
            if target in p.targets:
                continue
            for read in reads:
                read = read.rstrip("/")
                if p.path == read or p.path.startswith(read + "/"):
                    findings.append(
                        Problem(
                            "double-loading",
                            p.path,
                            f"{p.item['kind']} {p.item['name']!r} placed for "
                            f"{', '.join(p.targets)} at {p.path} is also read by {target}",
                        )
                    )
                    break
    return findings
