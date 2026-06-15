"""`sertor-flow`: installer del metodo di sviluppo (SDLC) di Sertor.

Pacchetto separato e ortogonale al RAG, senza dipendenza da `sertor-core`. Consumatore sottile del
toolkit condiviso `sertor-install-kit`. Deposita su un repo ospite il bundle di governance (flusso
SpecKit, gestione requisiti, delega git, costituzione-starter, blocco rituale `CLAUDE.md`) in modo
non distruttivo e idempotente — install ≠ run (nessuna fase SDLC/git/index avviata).
"""
from __future__ import annotations

from sertor_flow.install_governance import build_governance_plan, execute_governance_plan
from sertor_flow.profile import GovernanceProfile, build_governance_profile

__all__ = [
    "GovernanceProfile",
    "build_governance_profile",
    "build_governance_plan",
    "execute_governance_plan",
]
