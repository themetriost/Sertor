"""Test of the composition root — decoupling vector store ↔ embedding provider (Principio II/VIII).

The vector store (`store_backend`) is chosen independently from the embedding provider
(`backend`): Azure embeddings can be combined with a local Chroma store. Collection naming
applies Azure Search constraints **only** when the store is Azure.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sertor_core.adapters.embeddings.azure import AzureEmbedder
from sertor_core.adapters.vectorstores.chroma import ChromaStore
from sertor_core.composition import build_embedder, build_store, collection_name
from sertor_core.config.settings import Settings
from tests.fixtures.mocks import FakeEmbedder


def test_azure_embeddings_with_local_store(monkeypatch):
    # Azure embeddings but local Chroma store: prototype combination (decoupling Princ. II).
    monkeypatch.setenv("SERTOR_EMBED_PROVIDER", "azure")
    monkeypatch.setenv("SERTOR_STORE_BACKEND", "local")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://x.openai.azure.com/openai/v1")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "k")
    monkeypatch.setenv("AZURE_OPENAI_EMBED_DEPLOYMENT", "text-embedding-3-large")
    settings = Settings.load(env_file=None)

    assert isinstance(build_embedder(settings), AzureEmbedder)
    # local store despite embed_provider=azure
    assert isinstance(build_store(settings), ChromaStore)


def test_build_embedder_glove_branch(monkeypatch, tmp_path):
    # 068: the default provider builds a GloveEmbedder (no download in tests → override path).
    from sertor_core.adapters.embeddings.glove import GloveEmbedder

    fixture = Path(__file__).parent.parent / "fixtures" / "glove_mini.txt"
    settings = Settings(embed_provider="glove", glove_path=fixture)
    assert isinstance(build_embedder(settings), GloveEmbedder)


def test_build_embedder_hash_branch():
    # 068: the airgapped provider builds a HashingEmbedder.
    from sertor_core.adapters.embeddings.hashing import HashingEmbedder

    assert isinstance(build_embedder(Settings(embed_provider="hash")), HashingEmbedder)


def test_build_facade_wires_extra_corpora(monkeypatch):
    # Extra corpora (FR-007) become derived collections with the current provider (feature 010).
    monkeypatch.setenv("SERTOR_EMBED_PROVIDER", "hash")
    monkeypatch.setenv("SERTOR_STORE_BACKEND", "local")
    monkeypatch.setenv("SERTOR_CORPUS", "sertor")
    monkeypatch.setenv("SERTOR_EXTRA_CORPORA", "wiki")
    settings = Settings.load(env_file=None)

    from dataclasses import replace

    from sertor_core.composition import build_facade

    facade = build_facade(settings)
    expected = collection_name(replace(settings, corpus="wiki"), facade._embedder)
    assert facade._extra_collections == {"wiki": expected}
    assert expected.startswith("wiki__")          # namespaced by (corpus, provider)


def test_build_facade_without_extra_corpora_has_empty_map(monkeypatch):
    monkeypatch.delenv("SERTOR_EXTRA_CORPORA", raising=False)
    monkeypatch.setenv("SERTOR_EMBED_PROVIDER", "hash")
    monkeypatch.setenv("SERTOR_STORE_BACKEND", "local")
    settings = Settings.load(env_file=None)

    from sertor_core.composition import build_facade

    assert build_facade(settings)._extra_collections == {}


def test_collection_name_keys_on_store_backend():
    emb = FakeEmbedder()  # .name == "fake:8" → sanitized to "fake_8"

    # Local store (Chroma): no naming constraints → preserves corpus case.
    local = collection_name(Settings(corpus="Sertor", store_backend="local"), emb)
    assert local == "Sertor__fake_8"

    # Azure store: index constraints (lowercase, no leading digit) → forced lowercase.
    azure = collection_name(Settings(corpus="Sertor", store_backend="azure"), emb)
    assert azure == "sertor__fake_8"


def test_consumer_factories_wire_runtime(monkeypatch, tmp_path):
    """Feature 041 (Principio XI): each consumer-entry factory wires the cross-cutting concerns.

    A direct `build_*` use must activate observability like the CLI/MCP do — closing the gap where a
    re-index via the library bypassed `enable_observability`.
    """
    from sertor_core import composition
    from tests.fixtures.mocks import InMemoryStore

    settings = Settings.load(env_file=None)
    object.__setattr__(settings, "engine", "baseline")     # avoid lexical/hybrid construction
    object.__setattr__(settings, "graph_enabled", False)   # avoid the graph sink in build_indexer
    object.__setattr__(settings, "index_dir", tmp_path)

    calls: list[str] = []

    def _record(_s):
        calls.append("wired")
        return False

    monkeypatch.setattr(composition, "enable_observability", _record)
    monkeypatch.setattr(composition, "build_embedder", lambda *a, **k: FakeEmbedder())
    monkeypatch.setattr(composition, "build_store", lambda *a, **k: InMemoryStore())

    for factory in (
        composition.build_indexer,
        composition.build_facade,
        composition.build_baseline_engine,
        composition.build_graph_service,
        composition.build_engine,
    ):
        calls.clear()
        factory(settings)
        assert calls, f"{factory.__name__} did not wire the runtime (Principio XI)"


def test_memory_archiver_none_when_disabled(monkeypatch, tmp_path):
    # 031 (FR-002, D8): memory off → build_memory_archiver returns None.
    monkeypatch.delenv("SERTOR_MEMORY", raising=False)
    settings = Settings.load(env_file=None)
    object.__setattr__(settings, "index_dir", tmp_path)
    from sertor_core.composition import build_memory_archiver
    assert build_memory_archiver(settings) is None


def test_memory_archiver_built_when_enabled(monkeypatch, tmp_path):
    # 031: memory on → a wired MemoryArchiveService (claude-code adapter, pointed at a tmp dir).
    monkeypatch.setenv("SERTOR_MEMORY", "true")
    monkeypatch.setenv("SERTOR_MEMORY_CLAUDE_PROJECTS_DIR", str(tmp_path / "projects"))
    settings = Settings.load(env_file=None)
    object.__setattr__(settings, "index_dir", tmp_path)
    from sertor_core.composition import build_memory_archiver
    from sertor_core.services.memory_archive import MemoryArchiveService
    archiver = build_memory_archiver(settings)
    assert isinstance(archiver, MemoryArchiveService)


def test_memory_unknown_adapter_raises_configerror(monkeypatch, tmp_path):
    # 031 (FR-005): an unknown memory adapter → ConfigError listing the allowed values.
    monkeypatch.setenv("SERTOR_MEMORY", "true")
    monkeypatch.setenv("SERTOR_MEMORY_ADAPTER", "bogus")
    settings = Settings.load(env_file=None)
    object.__setattr__(settings, "index_dir", tmp_path)
    from sertor_core.composition import build_memory_archiver
    from sertor_core.domain.errors import ConfigError
    with pytest.raises(ConfigError) as exc:
        build_memory_archiver(settings)
    # FEAT-008 (FR-002): the actionable error now names BOTH allowed values.
    assert "claude-code" in str(exc.value)
    assert "copilot-cli" in str(exc.value)


def test_capture_adapter_copilot_cli_selected(monkeypatch, tmp_path):
    # FEAT-008 (US2-AC1/SC-001): copilot-cli → CopilotCliCaptureAdapter at copilot_session_dir.
    monkeypatch.setenv("SERTOR_MEMORY", "true")
    monkeypatch.setenv("SERTOR_MEMORY_ADAPTER", "copilot-cli")
    monkeypatch.setenv("SERTOR_MEMORY_COPILOT_SESSION_DIR", str(tmp_path / "session-state"))
    settings = Settings.load(env_file=None)
    from sertor_core.adapters.capture.copilot_cli import CopilotCliCaptureAdapter
    from sertor_core.composition import build_capture_adapter
    adapter = build_capture_adapter(settings)
    assert isinstance(adapter, CopilotCliCaptureAdapter)
    assert adapter.kind == "copilot-cli"


def test_capture_adapter_claude_code_default(monkeypatch):
    # FEAT-008 (FR-003/SC-010): default (unset) → claude-code → ClaudeCodeCaptureAdapter.
    monkeypatch.delenv("SERTOR_MEMORY_ADAPTER", raising=False)
    settings = Settings.load(env_file=None)
    assert settings.memory_adapter == "claude-code"
    from sertor_core.adapters.capture.claude_code import ClaudeCodeCaptureAdapter
    from sertor_core.composition import build_capture_adapter
    adapter = build_capture_adapter(settings)
    assert isinstance(adapter, ClaudeCodeCaptureAdapter)


def test_valid_memory_adapters_is_exactly_two():
    # FEAT-008 (contratto §Selettore): exactly the two known adapters, no more no less.
    from sertor_core.composition import _VALID_MEMORY_ADAPTERS
    assert _VALID_MEMORY_ADAPTERS == ("claude-code", "copilot-cli")


def test_memory_archiver_copilot_cli_wired(monkeypatch, tmp_path):
    # FEAT-008 (US7-AC1/SC-007): memory on + copilot-cli → MemoryArchiveService with the Copilot
    # adapter injected (the hook pipe is connected; we don't capture real sessions here).
    monkeypatch.setenv("SERTOR_MEMORY", "true")
    monkeypatch.setenv("SERTOR_MEMORY_ADAPTER", "copilot-cli")
    monkeypatch.setenv("SERTOR_MEMORY_COPILOT_SESSION_DIR", str(tmp_path / "session-state"))
    settings = Settings.load(env_file=None)
    object.__setattr__(settings, "index_dir", tmp_path)
    from sertor_core.adapters.capture.copilot_cli import CopilotCliCaptureAdapter
    from sertor_core.composition import build_memory_archiver
    from sertor_core.services.memory_archive import MemoryArchiveService
    archiver = build_memory_archiver(settings)
    assert isinstance(archiver, MemoryArchiveService)
    assert isinstance(archiver._adapter, CopilotCliCaptureAdapter)


def test_memory_off_copilot_adapter_not_built(monkeypatch, tmp_path):
    # FEAT-008 (US5-AC1/US7-AC2/SC-011/RNF-3): memory off → None even with adapter=copilot-cli;
    # the new branch / Copilot import never runs (additività a leva spenta).
    monkeypatch.setenv("SERTOR_MEMORY", "false")
    monkeypatch.setenv("SERTOR_MEMORY_ADAPTER", "copilot-cli")
    settings = Settings.load(env_file=None)
    object.__setattr__(settings, "index_dir", tmp_path)
    from sertor_core.composition import build_memory_archiver
    assert build_memory_archiver(settings) is None


def test_composition_does_not_import_claude_code_at_module_level():
    # 031 (FR-002): the host-specific adapter is imported lazily inside the build_* function,
    # never at composition import time (zero overhead at flag off).
    import sertor_core.composition as comp
    source = Path(comp.__file__).read_text(encoding="utf-8")
    module_lines = [
        ln for ln in source.splitlines()
        if ln.lstrip().startswith(("from sertor_core.adapters.capture",
                                   "import sertor_core.adapters.capture"))
        and not ln.startswith((" ", "\t"))  # exclude the in-function (indented) lazy import
    ]
    assert module_lines == []  # only the in-function lazy import exists


# --- 074: doctor helpers (build_provider_probe / read_mcp_registration / current_source_stats) ----


class _RaisingEmbedder:
    name = "fake"

    def embed(self, texts):
        raise RuntimeError("boom sk-secretkey1234")


class _OkEmbedder:
    name = "fake"

    def __init__(self):
        self.embedded: list[str] = []

    def embed(self, texts):
        self.embedded.extend(texts)
        return [[0.0] for _ in texts]


def test_build_provider_probe_reachable(monkeypatch):
    import sertor_core.composition as comp
    from sertor_core.composition import build_provider_probe
    from sertor_core.services.doctor import ProbeStatus

    monkeypatch.setattr(comp, "build_embedder", lambda s, allow_download=False: _OkEmbedder())
    probe = build_provider_probe(Settings(embed_provider="hash"))
    assert probe.status is ProbeStatus.reachable
    assert probe.reason == ""


def test_build_provider_probe_unreachable_on_exception(monkeypatch):
    import sertor_core.composition as comp
    from sertor_core.composition import build_provider_probe
    from sertor_core.services.doctor import ProbeStatus

    monkeypatch.setattr(comp, "build_embedder", lambda s, allow_download=False: _RaisingEmbedder())
    probe = build_provider_probe(Settings(embed_provider="hash"))
    assert probe.status is ProbeStatus.unreachable
    assert "sk-secretkey1234" not in probe.reason  # scrubbed (FR-013/SC-006)


def test_build_provider_probe_allow_download_false(monkeypatch):
    import sertor_core.composition as comp
    from sertor_core.composition import build_provider_probe

    seen = {}

    def _fake(s, allow_download=True):
        seen["allow_download"] = allow_download
        return _OkEmbedder()

    monkeypatch.setattr(comp, "build_embedder", _fake)
    build_provider_probe(Settings(embed_provider="hash"))
    assert seen["allow_download"] is False  # never downloads GloVe (DA-D5/R-2/SC-008)


def test_build_provider_probe_no_upsert(monkeypatch):
    import sertor_core.composition as comp
    from sertor_core.composition import build_provider_probe

    emb = _OkEmbedder()
    monkeypatch.setattr(comp, "build_embedder", lambda s, allow_download=False: emb)
    build_provider_probe(Settings(embed_provider="hash"))
    # only ONE sentinel embedded, no store/upsert touched (non-indexing, SC-008)
    assert len(emb.embedded) == 1


def test_read_mcp_registration_true(tmp_path):
    from sertor_core.composition import read_mcp_registration

    (tmp_path / ".mcp.json").write_text(
        '{"mcpServers": {"sertor-rag": {"command": "x"}}}', encoding="utf-8"
    )
    assert read_mcp_registration(tmp_path) is True


def test_read_mcp_registration_false_absent(tmp_path):
    from sertor_core.composition import read_mcp_registration

    assert read_mcp_registration(tmp_path) is False


def test_read_mcp_registration_false_no_sertor_key(tmp_path):
    from sertor_core.composition import read_mcp_registration

    (tmp_path / ".mcp.json").write_text('{"mcpServers": {"other": {}}}', encoding="utf-8")
    assert read_mcp_registration(tmp_path) is False


def test_read_mcp_registration_invalid_json(tmp_path):
    from sertor_core.composition import read_mcp_registration

    (tmp_path / ".mcp.json").write_text("{not json", encoding="utf-8")
    assert read_mcp_registration(tmp_path) is False


def test_read_mcp_registration_servers_key(tmp_path):
    from sertor_core.composition import read_mcp_registration

    (tmp_path / ".mcp.json").write_text(
        '{"servers": {"sertor-rag": {}}}', encoding="utf-8"
    )
    assert read_mcp_registration(tmp_path) is True


def test_read_mcp_registration_readonly(tmp_path):
    from sertor_core.composition import read_mcp_registration

    path = tmp_path / ".mcp.json"
    path.write_text('{"mcpServers": {"sertor-rag": {}}}', encoding="utf-8")
    before = path.read_bytes()
    read_mcp_registration(tmp_path)
    assert path.read_bytes() == before  # no write
    assert sorted(p.name for p in tmp_path.iterdir()) == [".mcp.json"]


def test_current_source_stats_returns_mtime_for_known_files(tmp_path):
    from sertor_core.composition import current_source_stats

    (tmp_path / "a.py").write_text("x", encoding="utf-8")
    (tmp_path / "b.md").write_text("y", encoding="utf-8")

    class _S:
        files = {"a.py": (0.0, "h", "v"), "b.md": (0.0, "h", "v")}

    stats = dict(current_source_stats(_S(), tmp_path))
    assert all(m > 0.0 for m in stats.values())
    assert {p.as_posix() for p in stats} == {"a.py", "b.md"}


def test_current_source_stats_deleted_file_returns_zero_mtime(tmp_path):
    from sertor_core.composition import current_source_stats

    class _S:
        files = {"gone.py": (0.0, "h", "v")}

    stats = current_source_stats(_S(), tmp_path)
    assert stats == [(Path("gone.py"), 0.0)]


def test_current_source_stats_none_state(tmp_path):
    from sertor_core.composition import current_source_stats

    assert current_source_stats(None, tmp_path) == []


def test_current_source_stats_no_rescan(tmp_path, monkeypatch):
    # Only the manifest files are stat-ed; extra files on disk are NOT discovered (no glob/walk).
    from sertor_core.composition import current_source_stats

    (tmp_path / "known.py").write_text("x", encoding="utf-8")
    (tmp_path / "extra.py").write_text("z", encoding="utf-8")

    class _S:
        files = {"known.py": (0.0, "h", "v")}

    stats = current_source_stats(_S(), tmp_path)
    assert [p.as_posix() for p, _ in stats] == ["known.py"]  # extra.py never seen
