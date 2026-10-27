"""Where a package came from, and who signed it (specs/028).

Origin: where the package was reached (a git repository, a commit, a subdirectory), deduced from
uv's install metadata or from the producer's git checkout, or declared by the operator.
Signature: an SSH signature of the package record (`ssh-keygen -Y`), checked against the host's
trusted signers in the main Kaelen's `.kaelen/trust/allowed_signers`. Every external tool is reached
through an object a test can replace (`Keygen`, `Git`, `Fetcher`), so the engine never needs one to
install an unsigned package and the tests never touch a real one.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import shutil
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

NAMESPACE = "kaelen-package"
SIGNATURE = "kaelen-package.json.sig"
TRUST = ".kaelen/trust/allowed_signers"
_ARMOR = ("-----BEGIN SSH SIGNATURE-----", "-----END SSH SIGNATURE-----")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


class NotChecked(Exception):
    """A provenance check that could not run: never a pass (FR-008)."""


class TrustUnreadable(Exception):
    pass


# --- origin --------------------------------------------------------------------------------------


def unknown_origin() -> dict:
    return {"repository": None, "commit": None, "subdirectory": None, "how": "unknown",
            "resolved": False}  # fmt: skip


def parse_reference(text: str) -> dict | None:
    """`git+URL@COMMIT#subdirectory=S` (the form uvx takes) as an origin; None otherwise."""
    if not text.startswith("git+"):
        return None
    rest, _, fragment = text[4:].partition("#")
    if "@" not in rest.rsplit("/", 1)[-1]:
        return None
    url, _, ref = rest.rpartition("@")
    sub = None
    for part in fragment.split("&"):
        if part.startswith("subdirectory="):
            sub = part.split("=", 1)[1]
    if not url or not ref:
        return None
    return {"repository": url, "commit": ref, "subdirectory": sub, "how": "declared",
            "resolved": bool(_COMMIT.match(ref))}  # fmt: skip


def from_uv(root: Path, distribution: str) -> dict | None:
    """The origin uv recorded beside an installed package (PEP 610 `direct_url.json`)."""
    stem = re.sub(r"[-_.]+", "_", distribution).lower()
    for meta in sorted(root.parent.glob("*.dist-info/direct_url.json")):
        name = meta.parent.name.removesuffix(".dist-info").rsplit("-", 1)[0]
        if re.sub(r"[-_.]+", "_", name).lower() != stem:
            continue
        try:
            doc = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        url = str(doc.get("url", ""))
        url = url[4:] if url.startswith("git+") else url
        commit = (doc.get("vcs_info") or {}).get("commit_id")
        return {"repository": url or None, "commit": commit,
                "subdirectory": doc.get("subdirectory"), "how": "deduced",
                "resolved": bool(commit and _COMMIT.match(commit))}  # fmt: skip
    return None


class Git:
    """`git` as a process; `run` returns (exit code, stdout)."""

    def run(
        self, args: list[str], cwd: Path, timeout: float = 60, input: str | None = None
    ) -> tuple[int, str]:
        exe = shutil.which("git")
        if exe is None:
            return 127, ""
        try:
            done = subprocess.run(
                [exe, *args],
                cwd=cwd,
                input=input,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return 124, ""  # named by the caller: a timeout is not a failure of git (R-8)
        except (OSError, subprocess.SubprocessError):
            return 127, ""
        return done.returncode, done.stdout.strip()


def from_git(root: Path, git: Git) -> dict | None:
    """The origin of a package lying in the producer's git checkout; unresolved when it changed."""
    code, top = git.run(["rev-parse", "--show-toplevel"], root)
    if code != 0 or not top:
        return None
    code, commit = git.run(["rev-parse", "HEAD"], root)
    if code != 0:
        return None
    _, url = git.run(["remote", "get-url", "origin"], root)
    _, dirty = git.run(["status", "--porcelain", "--", "."], root)
    try:
        sub = root.resolve().relative_to(Path(top).resolve()).as_posix()
    except ValueError:
        return None
    return {"repository": url or None, "commit": commit, "subdirectory": sub or None,
            "how": "deduced",
            "resolved": bool(_COMMIT.match(commit)) and not dirty and bool(url)}  # fmt: skip


def origin(root: Path, distribution: str, declared: str | None, git: Git) -> dict:
    """Where the package at `root` came from (specs/028 R-7)."""
    if declared:
        found = parse_reference(declared)
        if found is None:
            raise ValueError(
                f"--origin {declared!r} is not a git reference: git+URL@COMMIT#subdirectory=PATH"
            )
        return found
    return from_uv(root, distribution) or from_git(root, git) or unknown_origin()


# --- signatures ----------------------------------------------------------------------------------


def _strings(blob: bytes) -> list[bytes]:
    out, i = [], 0
    while i + 4 <= len(blob):
        (n,) = struct.unpack(">I", blob[i : i + 4])
        out.append(blob[i + 4 : i + 4 + n])
        i += 4 + n
    return out


def _unarmor(sig: bytes) -> bytes:
    text = sig.decode("ascii", errors="replace")
    if _ARMOR[0] not in text or _ARMOR[1] not in text:
        raise ValueError("not an SSH signature")
    body = text.split(_ARMOR[0], 1)[1].split(_ARMOR[1], 1)[0]
    return base64.b64decode("".join(body.split()))


def public_key(sig: bytes) -> tuple[str, str]:
    """(key type, base64 key) carried by an SSH signature (SSHSIG wire format)."""
    raw = _unarmor(sig)
    if raw[:6] != b"SSHSIG":
        raise ValueError("not an SSH signature")
    blob = _strings(raw[10:])[0]
    keytype = _strings(blob)[0].decode("ascii")
    return keytype, base64.b64encode(blob).decode("ascii")


def fingerprint(key_b64: str) -> str:
    digest = hashlib.sha256(base64.b64decode(key_b64)).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


class Keygen:
    """`ssh-keygen -Y` as a process (OpenSSH >= 8.0)."""

    def available(self) -> bool:
        return shutil.which("ssh-keygen") is not None

    def _run(self, args: list[str], data: bytes | None = None) -> bool:
        exe = shutil.which("ssh-keygen")
        if exe is None:
            raise NotChecked("ssh-keygen is not available")
        try:
            done = subprocess.run(
                [exe, *args], input=data, capture_output=True, timeout=60, check=False
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise NotChecked(f"ssh-keygen could not run: {exc}") from exc
        return done.returncode == 0

    def sign(self, key: Path, target: Path) -> None:
        """Write `<target>.sig`; raises when it cannot."""
        if not self._run(["-Y", "sign", "-f", str(key), "-n", NAMESPACE, str(target)]):
            raise OSError(f"ssh-keygen could not sign with {key}")

    def check(self, data: bytes, sig: Path) -> bool:
        return self._run(["-Y", "check-novalidate", "-n", NAMESPACE, "-s", str(sig)], data)

    def verify(self, data: bytes, sig: Path, allowed: Path, principal: str) -> bool:
        args = ["-Y", "verify", "-f", str(allowed), "-I", principal, "-n", NAMESPACE, "-s"]
        return self._run([*args, str(sig)], data)


@dataclass
class Signed:
    """What a package's signature says, checked: valid, by whom, and whether the host trusts it."""

    state: str  # valid | invalid | absent
    signer: str | None = None
    key: str | None = None  # fingerprint
    trusted: bool = False
    line: str | None = None  # the trust line this signature would need


def check_signature(
    root: Path, record: bytes, signer: str | None, host: Path | None, keygen: Keygen,
    trust_also: str | None = None,
) -> Signed:  # fmt: skip
    """Check `root`'s signature against its record bytes, then against the host's trust file
    (and, with `trust_also`, a consent for that principal in this operation)."""
    sig = root / SIGNATURE
    if not sig.is_file():
        return Signed("absent", signer)
    if not keygen.available():
        raise NotChecked("ssh-keygen is not available")
    try:
        keytype, key = public_key(sig.read_bytes())
    except ValueError:
        return Signed("invalid", signer)
    if not keygen.check(record, sig):
        return Signed("invalid", signer)
    line = trust_line(signer or "", keytype, key)
    out = Signed("valid", signer, fingerprint(key), False, line)
    if host is not None and signer and (signer, keytype, key) in set(read_trust(host)):
        with tempfile.TemporaryDirectory() as tmp:
            allowed = Path(tmp) / "allowed_signers"
            allowed.write_text(line + "\n", encoding="utf-8")
            out.trusted = keygen.verify(record, sig, allowed, signer)
    elif trust_also and signer and trust_also == signer:
        with tempfile.TemporaryDirectory() as tmp:
            allowed = Path(tmp) / "allowed_signers"
            allowed.write_text(line + "\n", encoding="utf-8")
            out.trusted = keygen.verify(record, sig, allowed, signer)
    return out


# --- the trust file ------------------------------------------------------------------------------


def trust_line(principal: str, keytype: str, key: str) -> str:
    return f'{principal} namespaces="{NAMESPACE}" {keytype} {key}'


def read_trust(host: Path) -> list[tuple[str, str, str]]:
    """(principal, key type, base64 key) per trusted signer; empty when the file is absent."""
    path = host / TRUST
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise TrustUnreadable(f"{TRUST}: {exc}") from exc
    out = []
    for line in text.splitlines():
        parts = line.split()
        if not parts or parts[0].startswith("#"):
            continue
        rest = parts[1:]
        if rest and "=" in rest[0] and not rest[0].startswith(("ssh-", "ecdsa-", "sk-")):
            rest = rest[1:]
        if len(rest) < 2:
            continue
        for principal in parts[0].split(","):
            out.append((principal, rest[0], rest[1]))
    return out


# --- fetching a commit ---------------------------------------------------------------------------


class Fetcher:
    """Brings `subdirectory` of `commit` from `repository` into `dest` with git (R-8)."""

    def __init__(self, git: Git | None = None):
        self.git = git or Git()

    def fetch(self, repository: str, commit: str, subdirectory: str | None, dest: Path,
              timeout: float) -> Path:  # fmt: skip
        if shutil.which("git") is None:
            raise NotChecked("git is not available")
        steps = [
            ["init", "-q"],
            ["fetch", "-q", "--depth", "1", repository, commit],
            ["checkout", "-q", "FETCH_HEAD"],
        ]
        for args in steps:
            code, _ = self.git.run(args, dest, timeout)
            if code == 124:
                raise NotChecked(f"git {args[0]} timed out after {timeout:g} s for {repository}")
            if code != 0:
                raise NotChecked(f"git {args[0]} failed for {repository}@{commit}")
        return dest / subdirectory if subdirectory else dest


def remove_tree(path: Path) -> None:
    """Remove a temporary folder, including the read-only files git writes (`.git/objects`)."""
    import os
    import stat
    import sys

    def writable_then_retry(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=writable_then_retry)
    else:  # pragma: no cover - Python 3.11
        shutil.rmtree(path, onerror=writable_then_retry)


DEFAULT_KEYGEN: Keygen = Keygen()
DEFAULT_GIT: Git = Git()
DEFAULT_FETCHER: Fetcher = Fetcher()
