"""Costruttori di fixture condivisi per i test SpecAudit."""

from __future__ import annotations

from typing import Any


def speclift_output(changeset_ref: str = "abc123", *, version: str = "1") -> dict[str, Any]:
    """Un output SpecLift minimo ma valido (output.schema.json v1)."""

    return {
        "version": version,
        "changeset_ref": changeset_ref,
        "requirements": [
            {
                "id": "R1",
                "quota": "behaviour",
                "statement": "WHEN Esc is pressed, the system SHALL flush pending output.",
                "anchor": {
                    "file": "src/view.py",
                    "lines": [10, 20],
                    "symbol": "flush_on_esc",
                    "test": {
                        "name": "test_flush",
                        "path": "tests/test_view.py",
                        "covers_symbol": "flush_on_esc",
                    },
                    "granularity": "symbol",
                    "status": "verified",
                },
            },
            {
                "id": "R2",
                "quota": "implementation",
                "statement": "The launcher SHALL call spawn_tool().",
                "anchor": {
                    "file": "src/launch.py",
                    "lines": [5, 8],
                    "symbol": "spawn_tool",
                    "test": None,
                    "granularity": "symbol",
                    "status": "verified",
                },
            },
        ],
        "drifts": [
            {
                "description": "Un timer di background viene avviato all'apertura del workspace.",
                "anchor": {
                    "file": "src/launch.py",
                    "lines": [30, 34],
                    "symbol": "start_timer",
                    "test": None,
                    "granularity": "symbol",
                    "status": "unverified",
                },
                "status": "proposed",
            }
        ],
        "excluded": [],
        "open_questions": [],
    }


def requirements_md() -> str:
    """Un documento requirements/ canonico con due bullet EARS."""

    return (
        "# Requisiti — Workspace\n\n"
        "## 5. Requisiti funzionali (EARS)\n\n"
        "- **FR-001** *(Event-driven)* — **When** l'utente preme Esc, **the** system **shall** "
        "svuotare subito l'output in sospeso.\n"
        "- **FR-002** *(Ubiquitous)* — **The** launcher **shall** avviare lo strumento richiesto.\n"
        "- **FR-003** *(Ubiquitous)* — **The** system **shall** salvare la sessione su disco.\n"
    )
