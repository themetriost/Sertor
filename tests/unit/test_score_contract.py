"""Il contratto di comparabilità del punteggio è DERIVATO dalla configurazione (118, FR-005..013).

La scelta di fondo: il contratto è una proprietà del **tool**, costante fra le risposte, quindi vive
nella descrizione letta una volta — non in un campo ripetuto a ogni chiamata e pagato in token.

Ma un testo statico sarebbe **falso in una delle due configurazioni**: sotto fusione per rango il
punteggio deriva dalle posizioni e aggiunge poco all'ordine; sotto motore vettoriale è una
similarità, la cui distribuzione porta informazione. Questi test verificano che la descrizione dica
la verità sull'istanza che gira davvero.

Offline, F.I.R.S.T.: `score_contract` è una funzione pura.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from sertor_core.config.settings import Settings
from sertor_mcp.server import score_contract


@pytest.fixture
def settings() -> Settings:
    return Settings.load()


# --- L'invariante comune a ogni configurazione -------------------------------------------------


@pytest.mark.parametrize("engine", ["hybrid", "baseline"])
def test_scope_is_always_declared(settings: Settings, engine: str):
    """FR-005: l'ambito è dichiarato sempre, qualunque sia il motore."""
    text = score_contract(replace(settings, engine=engine))

    assert "ONLY within their own list" in text
    assert "never across flows" in text
    assert "never across queries" in text
    assert "absolute measure of quality" in text


@pytest.mark.parametrize("engine", ["hybrid", "baseline"])
def test_abstention_asymmetry_is_always_declared(settings: Settings, engine: str):
    """FR-013: che il valore dell'astensione e quello esposto siano grandezze diverse va detto.

    È l'asimmetria che il contratto taceva: tacerla invita esattamente il confronto falso che il
    contratto esiste per prevenire.
    """
    text = score_contract(replace(settings, engine=engine))

    assert "abstention" in text.lower()


# --- Ciò che DEVE differire fra le due configurazioni -------------------------------------------


def test_rank_fusion_engine_declares_the_score_adds_little(settings: Settings):
    """FR-012: sotto fusione per rango il punteggio è derivato dalle posizioni."""
    text = score_contract(replace(settings, engine="hybrid"))

    assert "RANK-FUSION" in text
    assert "not a similarity" in text
    assert "adds little beyond the ordering" in text
    assert "BEFORE fusion" in text, "l'asimmetria pre/post fusione va nominata sotto ibrido"


def test_vector_engine_declares_the_score_is_a_similarity(settings: Settings):
    """Sotto motore vettoriale la forma della distribuzione porta informazione."""
    text = score_contract(replace(settings, engine="baseline"))

    assert "SIMILARITY" in text
    assert "RANK-FUSION" not in text
    assert "distribution" in text


def test_the_two_configurations_do_not_produce_the_same_text(settings: Settings):
    """Il cuore del requisito: un testo unico sarebbe falso in una delle due configurazioni."""
    hybrid = score_contract(replace(settings, engine="hybrid"))
    baseline = score_contract(replace(settings, engine="baseline"))

    assert hybrid != baseline


# --- La descrizione effettivamente esposta dai tool --------------------------------------------


def test_search_tool_descriptions_carry_the_contract():
    """FR-007: la descrizione dei tool di ricerca porta il contratto, non solo le `instructions`."""
    from sertor_mcp import server

    for desc in (server._SEARCH_CODE_DESC, server._SEARCH_DOCS_DESC, server._SEARCH_COMBINED_DESC):
        assert "ONLY within their own list" in desc


def test_unresolvable_configuration_degrades_loudly_not_silently(monkeypatch, caplog):
    """Principio XII: se la configurazione non è leggibile, il fallback lo DICE.

    Non deve impedire l'avvio (era il guasto `-32000 Connection closed`), ma nemmeno spacciare per
    valido un contratto che l'istanza non onora.
    """
    import logging as _logging

    from sertor_mcp import server

    def _boom():
        raise RuntimeError("config unreadable")

    monkeypatch.setattr(server.Settings, "load", staticmethod(_boom))

    with caplog.at_level(_logging.WARNING, logger="sertor_core"):
        text = server._score_contract_for_active_config()

    assert "could not be determined" in text
    assert "ordering hint only" in text
    assert any("score_contract.unresolved" in r.getMessage() for r in caplog.records)
