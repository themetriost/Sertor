"""Dalla domanda in prosa ai simboli da interrogare nel grafo (118, FR-022/023/023a).

Il grafo vuole un **nome esatto**; la domanda è **linguaggio naturale**. Serve un ponte, e questo
ponte è **deterministico**: nessun modello linguistico entra nel percorso di retrieval (RNF-1) — a
parità di domanda e di corpus, gli stessi ingressi.

Due vie, ordinate per affidabilità dell'ingresso che producono:

1. **identificatori scritti nella domanda** — segnale forte: l'utente l'ha nominato;
2. **confronto lessicale con la tabella dei simboli** — segnale più debole: dedotto.

Il limite della seconda è **dichiarato, non nascosto**: copre la sovrapposizione fra le parole della
domanda e le *parti* di un identificatore, non «il concetto». Una domanda in italiano su
identificatori inglesi cade nel lexical gap e non produce ingressi — che è un esito **onesto**
«non tentato», a costo zero), non un errore da mascherare.

Funzioni pure, stdlib-only: testabili senza I/O.
"""
from __future__ import annotations

import re

from sertor_core.domain.agent_context import EntryPoint

# Un token "a forma di identificatore": maiuscola interna (CachingEmbedder), underscore
# (build_indexer) o notazione puntata (Settings.load). Le parole tutte minuscole senza separatori
# sono ESCLUSE di proposito: «cache», «index», «query» sono parole comuni in prosa, e agganciarle
# pescherebbe simboli irrilevanti su domande che non ne parlavano.
_IDENTIFIER = re.compile(
    r"\b(?:[A-Za-z_][\w]*\.)+[A-Za-z_]\w*"   # notazione puntata: Settings.load
    r"|\b\w*[a-z]\w*_\w+"                    # underscore: build_indexer
    r"|\b[a-z]+[A-Z]\w*"                       # camelCase: buildIndexer
    r"|\b[A-Z][a-z]+[A-Z]\w*"                  # PascalCase: CachingEmbedder
)

# Separatori con cui si spezza un nome qualificato nelle sue parti.
_SPLIT = re.compile(r"[._]|(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")

_WORD = re.compile(r"[a-zA-Z][a-zA-Z0-9]*")


def extract_identifiers(query: str) -> list[str]:
    """Token della domanda che HANNO FORMA di identificatore, in ordine di apparizione.

    Deliberatamente conservativa: preferisce non trovare nulla piuttosto che agganciare parole
    comuni. Un falso ingresso costa contesto dell'agente proprio dove il beneficio è nullo.
    """
    seen: set[str] = set()
    out: list[str] = []
    for match in _IDENTIFIER.finditer(query):
        token = match.group(0)
        if token not in seen:
            seen.add(token)
            out.append(token)
    return out


def split_qualname(qualname: str) -> set[str]:
    """Parti minuscole di un nome qualificato: `CachingEmbedder` → `{caching, embedder}`."""
    return {p.lower() for p in _SPLIT.split(qualname) if p}


# Lunghezza minima del prefisso comune perché due parole contino come la stessa (vedi `_akin`).
_STEM = 4


def _akin(part: str, word: str) -> bool:
    """Vero se due parole condividono una radice abbastanza lunga.

    Serve a superare la **variazione morfologica**, che il confronto esatto non attraversa e che
    nella pratica è la regola, non l'eccezione: chi scrive «embedding» cerca `CachingEmbedder`,
    «indicizzazione» non trova nulla ma chi scrive «indexing» deve trovare `IndexingService`.

    Il prefisso comune di 4 caratteri è la regola più semplice che copre i casi reali
    (`caching`/`cache` → `cach`, `embedding`/`embedder` → `embedd`, `indexing`/`index` → `index`)
    senza introdurre uno stemmer, che sarebbe una dipendenza e una fonte di non-determinismo
    linguistico. È una regola grossolana e **dichiarata tale**: `index`/`indent` condividono
    `inde` e si agganciano a vicenda. Il costo di quel falso positivo è un ingresso di troppo,
    all'agente tramite `source` e limitato dal tetto.
    """
    if part == word:
        return True
    if len(part) < _STEM or len(word) < _STEM:
        return False
    return part[:_STEM] == word[:_STEM]


def match_symbol_table(
    query: str, qualnames: list[str], min_overlap: int = 2
) -> list[str]:
    """Simboli le cui PARTI si sovrappongono al vocabolario della domanda (FR-023a).

    Un simbolo è candidato se la domanda ne contiene il nome intero (match forte, sempre valido)
    oppure se almeno `min_overlap` sue parti trovano una parola **affine** (vedi `_akin`).

    Perché la soglia di default è 2: con 1 una domanda contenente «index» pescherebbe ogni simbolo
    con «index» nel nome; con 3 si ricade di fatto sul nome intero. Due è il primo valore che
    discrimina.

    Ordine deterministico: parti coincidenti decrescenti, poi alfabetico.
    """
    words = {w.lower() for w in _WORD.findall(query)}
    if not words:
        return []
    # Il match sul nome intero richiede un CONFINE DI PAROLA, non una sottostringa: senza, la
    # domanda «chi chiama build_indexer» aggancia anche `build` e `_index`, che ne sono pezzi, e
    # quei due si prendono gli slot del tetto sottraendoli a ingressi veri. (Trovato dallo smoke
    # sul corpus reale: gli unit test usavano simboli senza sovrapposizioni di questo tipo.)
    tokens = {t.lower() for t in re.findall(r"[\w.]+", query)}

    scored: list[tuple[int, str]] = []
    for qualname in qualnames:
        if qualname.lower() in tokens:
            scored.append((len(split_qualname(qualname)) + 1, qualname))  # il match intero vince
            continue
        overlap = sum(
            1 for part in split_qualname(qualname) if any(_akin(part, w) for w in words)
        )
        if overlap >= min_overlap:
            scored.append((overlap, qualname))

    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [qualname for _, qualname in scored]


def resolve_entry_points(
    query: str,
    qualnames: list[str],
    *,
    max_symbols: int = 3,
    min_overlap: int = 2,
) -> list[EntryPoint]:
    """Compone le due vie e produce gli ingressi finali, al più `max_symbols`.

    Precedenza agli identificatori scritti nella domanda: a parità di posti disponibili vanno agli
    ingressi di cui ci si può fidare di più. La deduplica conserva la **prima** provenienza, cioè la
    più affidabile — e poiché `source` viaggia fino all'agente, questi può scontare gli altri.

    Restituisce `[]` quando nessuna via produce candidati: il chiamante riporterà «non tentato» e
    **non interrogherà il grafo**, che è ciò che rende il costo auto-correlato alla rilevanza.
    """
    known = set(qualnames)
    picked: dict[str, EntryPoint] = {}

    for token in extract_identifiers(query):
        if token in known and token not in picked:
            picked[token] = EntryPoint(symbol=token, source="extracted_from_query")

    for qualname in match_symbol_table(query, qualnames, min_overlap):
        if qualname not in picked:
            picked[qualname] = EntryPoint(symbol=qualname, source="symbol_table_match")

    return list(picked.values())[:max_symbols]
