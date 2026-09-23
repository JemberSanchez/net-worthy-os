"""Anclas de storyboard -> segundos, contra las palabras MEDIDAS de la voz (words.json).

Un storyboard no habla en segundos (el LLM que lo escribe no sabe cuándo sonará cada palabra):
habla en FRASES y PALABRAS del guion. Sintaxis de un ancla (string):

    "6"               arranque de la frase 6 (0-based)
    "6:reinvested"    arranque de la 1ª "reinvested" DENTRO de la frase 6
    "21:team#2"       la 2ª "team" de la frase 21
    "14:it$"          el FINAL de esa palabra (no el arranque)
    "6:shares$+0.2"   desplazamiento en segundos (también "-0.1")

La comparación de palabras ignora mayúsculas y puntuación ("dollars." == "dollars").
Un ancla que no resuelve es un ERROR (AnclaError), nunca un fallback silencioso: es la puerta que
caza un storyboard mal escrito antes de gastar 6 minutos de render.
"""
from __future__ import annotations

import re

_FIN_FRASE = re.compile(r"[.?!][\"')\]]*$")
# palabra perezosa: "ninety-five" es palabra; "big-0.1" es "big" con desplazamiento -0.1 (el
# desplazamiento exige dígitos tras el signo, así que un guion entre letras nunca lo es).
_ANCLA = re.compile(r"^(\d+)(?::([^#$]+?)(?:#(\d+))?(\$)?)?([+-]\d+(?:\.\d+)?)?$")


# Claves cuyo valor string es un ancla (un número en la misma clave, p. ej. `hasta: 2014`, no se toca).
CLAVES = ("en", "hasta", "llega", "fin", "marca", "golpe", "tachar")


class AnclaError(ValueError):
    pass


def norm(p: str) -> str:
    return re.sub(r"[^a-z0-9'\-]", "", p.lower()).strip("-'")


def frases(words: list[dict]) -> list[list[int]]:
    """Índices de palabra agrupados por frase (corta en . ? ! al final de la palabra)."""
    out, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        if _FIN_FRASE.search(w["text"]):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


def palabra(words: list[dict], ancla: str, _fr: list[list[int]] | None = None) -> tuple[int, bool, float]:
    """Resuelve un ancla a (índice de palabra, ¿final?, desplazamiento)."""
    m = _ANCLA.match(str(ancla).strip())
    if not m:
        raise AnclaError(f"ancla mal escrita: {ancla!r} (formato: 'frase[:palabra[#n]][$][+seg]')")
    k, pal, nth, fin, desp = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
    fr = _fr if _fr is not None else frases(words)
    k = int(k)
    if k >= len(fr):
        raise AnclaError(f"ancla {ancla!r}: el guion solo tiene {len(fr)} frases (0..{len(fr) - 1})")
    idx = fr[k]
    if pal is None:
        i = idx[0]
    else:
        objetivo, n = norm(pal), int(nth or 1)
        hits = [i for i in idx if norm(words[i]["text"]) == objetivo]
        if len(hits) < n:
            texto = " ".join(words[i]["text"] for i in idx)
            raise AnclaError(f"ancla {ancla!r}: '{pal}' aparece {len(hits)} vez/veces en la frase {k}: «{texto}»")
        i = hits[n - 1]
    return i, bool(fin), float(desp or 0.0)


def t(words: list[dict], ancla: str, _fr: list[list[int]] | None = None) -> float:
    """Ancla -> segundos."""
    i, fin, desp = palabra(words, ancla, _fr)
    return round((words[i]["end"] if fin else words[i]["start"]) + desp, 3)


def resolver(obj, words: list[dict], _fr: list[list[int]] | None = None):
    """Recorre un storyboard y sustituye cada clave de CLAVES cuyo valor sea un ancla (string)
    por su tiempo, guardando el original en `<clave>_ancla` (para mensajes y depuración)."""
    fr = _fr if _fr is not None else frases(words)
    if isinstance(obj, list):
        return [resolver(x, words, fr) for x in obj]
    if not isinstance(obj, dict):
        return obj
    out = {}
    for k, v in obj.items():
        if k in CLAVES and isinstance(v, str):
            out[k] = t(words, v, fr)
            out[k + "_ancla"] = v
        else:
            out[k] = resolver(v, words, fr)
    return out
