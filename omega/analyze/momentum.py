"""Detección de momentum de temas (v0, stdlib, sin coste).

Idea: comparar la frecuencia-de-documento (DF) de cada término en una ventana
RECIENTE vs una ventana PREVIA (baseline). Un término que aparece en muchos más
documentos ahora que antes => tema "en alza". Lo contrario => "en caída".

Usamos DF (en cuántos documentos aparece) y no frecuencia bruta: más robusto al
spam de un único artículo repetitivo.

Esto es un PLACEHOLDER honesto del motor real: en la siguiente fase se sustituye
el término por CLUSTER semántico (embeddings) y el conteo por engagement, no solo
volumen. Pero la mecánica de ventanas y momentum se mantiene idéntica.
"""
from __future__ import annotations
import math
import re
import time
from collections import defaultdict

from .. import config, db

# Stopwords mínimas EN + ES. Ampliar según ruido observado.
_STOP = set("""
a an the of to in on for and or but with from by at as is are was were be been being
this that these those it its it's they them their there here what which who whom how
new latest first best top your you we our us i me my he she his her not no yes do does
did have has had will would can could should may might must about into over under after
before more most less least very just also than then once only own same so up out off
www http https html com span href url link links comments submitted redd reddit item
items article articles points user users amp nbsp via comment post posts read full
all new one two three get got make made use used way ways thing things now today says
say said back even still going know dont cant wont let us em new big top best
de la el los las un una unos unas y o pero con sin por para en del al lo le su sus se
es son era eran ser que como mas más este esta estos estas esto eso esa ese aqui aquí
ya no si sí muy todo todos toda todas sobre entre cuando donde quien cual cuales hoy
""".split())

_TOKEN = re.compile(r"[a-záéíóúñü0-9][a-záéíóúñü0-9'\-]+", re.IGNORECASE)


def _content(tok: str) -> bool:
    return len(tok) >= 3 and tok not in _STOP and not tok.isdigit()


def _terms(text: str) -> set[str]:
    """Unigramas + bigramas de palabras de contenido ADYACENTES.

    Así emergen temas reales como 'prime day' o 'amazon prime' en vez de tokens sueltos
    ('day', 'prime', 'amazon'). El bigrama solo se forma si ambas palabras son de contenido
    y están pegadas en el texto (sin stopword en medio)."""
    raw = _TOKEN.findall(text.lower())
    out: set[str] = set()
    for i, tok in enumerate(raw):
        if not _content(tok):
            continue
        out.add(tok)
        if i + 1 < len(raw) and _content(raw[i + 1]):
            out.add(f"{tok} {raw[i + 1]}")
    return out


def _doc_freq(rows) -> tuple[dict[str, int], int, dict[str, list[str]]]:
    """DF por término + total de docs + ejemplos de titulares por término."""
    df: dict[str, int] = defaultdict(int)
    examples: dict[str, list[str]] = defaultdict(list)
    n = 0
    for r in rows:
        n += 1
        text = f"{r['title']} {r['summary'] or ''}"
        for t in _terms(text):
            df[t] += 1
            if len(examples[t]) < 3:
                examples[t].append(r["title"])
    return df, n, examples


def compute(now: int | None = None) -> dict:
    now = now or int(time.time())
    day = 86400
    recent_start = now - config.RECENT_WINDOW_DAYS * day
    prior_start = recent_start - config.PRIOR_WINDOW_DAYS * day

    recent_rows = db.fetch_between(recent_start, now)
    prior_rows = db.fetch_between(prior_start, recent_start)

    rdf, rn, examples = _doc_freq(recent_rows)
    pdf, pn, _ = _doc_freq(prior_rows)

    results = []
    for term, rc in rdf.items():
        if rc < config.MIN_RECENT_DOC_FREQ:
            continue
        # Tasas normalizadas por tamaño de ventana (con suavizado de Laplace).
        recent_rate = rc / (rn + 1)
        prior_rate = (pdf.get(term, 0) + 1) / (pn + 1)  # +1 evita división por cero
        ratio = recent_rate / prior_rate
        results.append({
            "term": term,
            "recent_df": rc,
            "prior_df": pdf.get(term, 0),
            "momentum": round(math.log2(ratio), 2),  # log2: +1 = duplicó presencia
            "examples": examples[term],
        })

    rising = sorted(results, key=lambda x: x["momentum"], reverse=True)
    declining = sorted(results, key=lambda x: x["momentum"])
    return {
        "now": now,
        "recent_docs": rn,
        "prior_docs": pn,
        "rising": rising[: config.TOP_N],
        "declining": [d for d in declining if d["momentum"] < 0][: config.TOP_N],
    }
