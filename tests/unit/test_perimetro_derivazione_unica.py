"""Il perimetro «lavoro non ancora consegnato» ha UNA sola derivazione (E10-FEAT-060/066).

Storia breve, perche' spiega la forma di questo file. La prima stesura di E10-FEAT-060 allineava il
comportamento di `ritual_check` a quello di `scan` **per riuso**, lasciando in piedi la copia
privata `scan._worktree_changes`: due implementazioni identiche, e un test di *equivalenza* a
sorvegliarle.

Quel test era il sintomo, non la cura — esisteva **solo** perche' avevamo declinato una modifica da
due righe. Rimossa la copia, l'equivalenza e' diventata vacua per costruzione (confrontava una
funzione con se' stessa) e un test che non puo' fallire va **tolto**, non tenuto per conforto.

Resta una domanda che nessun test comportamentale puo' porre, perche' due copie divergenti
funzionerebbero entrambe finche' non divergono: **esiste una sola derivazione?** E' strutturale, e
quindi la guardia lo e'.

Si sorvegliano le **invocazioni git che costituiscono** la derivazione, non i nomi delle funzioni:
un wrapper che delega (come il fail-loud di `ritual_check`) e' legittimo e non va confuso con una
copia.
"""
from __future__ import annotations

import importlib
import inspect

# `importlib`, non `import ... as`: il pacchetto ri-esporta le funzioni omonime (`from ...scan
# import scan` in `__init__.py`), quindi `import sertor_core.wiki_tools.scan as x` lega la
# **funzione** e non il **modulo** — e una guardia che ispeziona l'oggetto sbagliato passa a vuoto.
# Gia' successo scrivendo questo file.
scan_mod = importlib.import_module("sertor_core.wiki_tools.scan")
rc_mod = importlib.import_module("sertor_core.wiki_tools.ritual_check")
vcs_mod = importlib.import_module("sertor_core.wiki_tools.vcs")

# I due comandi che INSIEME definiscono «cosa e' stato toccato ma non consegnato»: il diff
# content-aware sui tracciati e lo stato dei non tracciati. Chi li scrive, sta derivando.
_INVOCAZIONI = ('"diff", "--name-only", "-z", "HEAD"', '"status", "--porcelain"')

_CONSUMATORI = (scan_mod, rc_mod)


def test_i_moduli_sono_moduli_non_funzioni_omonime():
    """Anti-vacuita' del file intero: se `scan_mod` fosse la funzione `scan`, `inspect.getsource`
    leggerebbe poche righe e OGNI asserzione sotto passerebbe gratis. E' successo davvero.
    """
    for modulo in (scan_mod, rc_mod, vcs_mod):
        assert inspect.ismodule(modulo), f"{modulo!r} non e' un modulo"


def test_le_invocazioni_della_derivazione_stanno_solo_in_vcs():
    """Nessun consumatore puo' rifarsi la derivazione in proprio.

    E' il difetto di E10-FEAT-060 alla radice: due capacita' che rispondono alla stessa domanda con
    codice diverso, senza che nulla le confronti. Un test comportamentale non lo vedrebbe — due
    copie funzionano entrambe, finche' non divergono.
    """
    for invocazione in _INVOCAZIONI:
        for modulo in _CONSUMATORI:
            sorgente = inspect.getsource(modulo)
            assert invocazione not in sorgente, (
                f"{modulo.__name__} invoca {invocazione} in proprio: sta riderivando l'albero di "
                "lavoro invece di consumare `vcs.worktree_changes`. Una sola derivazione."
            )


def test_la_derivazione_esiste_davvero_in_vcs():
    """Anti-vacuita': se le invocazioni sparissero anche da `vcs`, il test sopra passerebbe gratis.

    Un contatore che va a zero perche' non c'e' piu' niente da contare non e' una misura.
    """
    sorgente = inspect.getsource(vcs_mod)
    for invocazione in _INVOCAZIONI:
        assert invocazione in sorgente, (
            f"`vcs` non contiene piu' {invocazione}: la guardia sopra e' diventata vacua."
        )


def test_entrambi_i_consumatori_usano_l_helper_condiviso():
    """Il complemento positivo: non basta che non riderivino, devono davvero consumare l'helper."""
    for modulo in _CONSUMATORI:
        assert getattr(modulo, "worktree_changes", None) is vcs_mod.worktree_changes, (
            f"{modulo.__name__} non consuma `vcs.worktree_changes`."
        )


def test_anche_lo_split_dell_output_git_e_uno_solo():
    """Stessa regola per l'helper minore: due `split_z` sono due modi di sbagliare i path con
    spazi.
    """
    assert scan_mod.split_z is vcs_mod.split_z
    assert 'out.split("\\0")' not in inspect.getsource(scan_mod)
    assert 'out.split("\\0")' in inspect.getsource(vcs_mod)  # anti-vacuita'
