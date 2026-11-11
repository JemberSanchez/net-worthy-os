"""Every figure the viewer hears or reads must trace to `cifras`. Until 6-nov `cifras` only needed a URL, so a
number could change between the source note and the script unnoticed.

What this proves: the figure on screen is the figure written in `cifras`, allowing for rounding.
What it cannot prove: that `cifras` matches its source. That stays with the judgment (J3, juicio_lista.py).
"""

from __future__ import annotations

import re

_U = [
    "zero",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "thirteen",
    "fourteen",
    "fifteen",
    "sixteen",
    "seventeen",
    "eighteen",
    "nineteen",
]
_D = ["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_NUM = {w: i for i, w in enumerate(_U)} | {w: (i + 2) * 10 for i, w in enumerate(_D)}
_ESC = {"thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
_SUFIJO = {"k": 1e3, "m": 1e6, "b": 1e9, "t": 1e12}
_DIGITOS = re.compile(
    r"(?<![\w.,])[$+\-−]?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(?:(thousand|million|billion|trillion)\b|([kKmMbBtT])\b(?!\())?(%?)"
)
# names, not quantities: 401(k), 403(b), 457(b), 529 plan, S&P 500, Form 1040
_NOMBRES = re.compile(
    r"\b(?:401\s*\(?k\)?|403\s*\(?b\)?|457\s*\(?b\)?|529 plans?|s&p\s*500|form \d+|top \d+)",
    re.IGNORECASE,
)
_COMPUESTO = re.compile(r"[-‑–—]")
PEQUENO = (
    12  # "three in four", "two accounts": counting words, not figures anyone sources
)


def _cifra(v: float, txt: str) -> dict:
    return {"valor": v, "texto": txt, "sig": _significativas(txt)}


def _significativas(txt: str) -> int:
    d = re.sub(r"[^\d.]", "", txt.split("%")[0]).lstrip("0.")
    d = d.replace(".", "") if "." in d else d.rstrip("0")
    return max(1, len(d))


def de_digitos(texto: str) -> list[dict]:
    out = []
    for m in _DIGITOS.finditer(_NOMBRES.sub(" ", texto.replace("*", ""))):
        v = float(m.group(1).replace(",", ""))
        esc = (
            _ESC.get((m.group(2) or "").lower())
            or _SUFIJO.get((m.group(3) or "").lower())
            or 1
        )
        if esc == 1 and not m.group(4) and "$" not in m.group(0) and v <= PEQUENO:
            continue
        out.append(_cifra(v * esc, m.group(1)))
    return out


def _entero(ws: list[str]) -> float:
    total = actual = 0.0
    for w in ws:
        if w == "hundred":
            actual = max(actual, 1) * 100
        elif w in _ESC:
            total += max(actual, 1) * _ESC[w]
            actual = 0.0
        else:
            actual += _NUM[w]
    return total + actual


def _valor_hablado(run: list[str]) -> float:
    """ "three hundred thirty thousand", "one point three trillion", "twenty twenty five" (a year)."""
    if "point" in run:
        k = run.index("point")
        cola = run[k + 1 :]
        esc = _ESC.get(cola[-1], 1) if cola else 1
        dec = "".join(str(_NUM[w]) for w in cola if w in _NUM)
        return float(f"{_entero(run[:k]):.0f}.{dec or 0}") * esc
    siglo = ("sixteen", "seventeen", "eighteen", "nineteen", "twenty")
    if len(run) >= 2 and run[0] in siglo and run[1] in _NUM and _NUM[run[1]] >= 10:
        return _NUM[run[0]] * 100 + _entero(run[1:])
    return _entero(run)


def de_palabras(texto: str) -> list[dict]:
    """Spoken numbers. A lone small word ("one", "three") counts things: it is not a figure."""
    # a comma ends a number: "in twenty twenty five, three hundred" is two
    limpio = _COMPUESTO.sub(" ", _NOMBRES.sub(" ", texto.lower()))
    ws = re.findall(r"[a-z]+|[,.;:?!]", limpio)
    out, i = [], 0
    numero = set(_NUM) | {"hundred", "point"} | set(_ESC)
    while i < len(ws):
        if ws[i] not in _NUM:
            i += 1
            continue
        j = i
        while j < len(ws) and ws[j] in numero:
            j += 1
        run = ws[i:j]
        while run[-1] == "point":
            run.pop()
            j -= 1
        v = _valor_hablado(run)
        if v > PEQUENO or "point" in run:
            out.append({"valor": v, "texto": " ".join(run), "sig": _sig_valor(v)})
        i = j
    return out


def _sig_valor(v: float) -> int:
    return _significativas(f"{v:.10f}".rstrip("0").rstrip("."))


def _redondea(fuente: float, sig: int) -> float:
    return float(f"{fuente:.{sig - 1}e}")


def casa(c: dict, fuentes: list[float]) -> bool:
    """A figure traces if a source value equals it, or rounds to it at the precision the figure shows."""
    v = c["valor"]
    return any(
        abs(v - f) <= 1e-9 * max(abs(f), 1)
        or abs(v - _redondea(f, c["sig"])) <= 1e-9 * max(abs(f), 1)
        for f in fuentes
    )


def fuentes(sb: dict) -> list[float]:
    vals: list[float] = []
    for c in sb.get("cifras") or []:
        d = str(c.get("dato", ""))
        vals += [x["valor"] for x in de_digitos(d) + de_palabras(d)]
    return vals


def _textos_pantalla(sb: dict) -> list[tuple[str, str]]:
    """(where, text) of everything the storyboard writes on screen, whatever the scene type calls it."""
    out: list[tuple[str, str]] = []

    def caminar(o, donde: str) -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                if k in (
                    "texto",
                    "kicker",
                    "titulo",
                    "sub",
                    "linea",
                    "etiqueta",
                ) and isinstance(v, str):
                    out.append((donde, v))
                elif k in ("valor", "monto") and isinstance(v, (int, float)):
                    out.append(
                        (donde, f"${v:,}" if o.get("prefijo", "$") == "$" else str(v))
                    )
                else:
                    caminar(v, donde)
        elif isinstance(o, list):
            for v in o:
                caminar(v, donde)

    for k, e in enumerate(sb.get("escenas") or []):
        caminar(e, f"escena {k}")
    for k, e in enumerate(sb.get("pruebas") or []):
        caminar({"texto": e.get("texto")}, f"prueba {k}")
    return out


def sin_fuente(sb: dict) -> list[str]:
    """One error per figure with no trace, reported once per place it appears."""
    fs = fuentes(sb)
    errores, vistos = [], set()

    def revisar(donde: str, cs: list[dict]) -> None:
        for c in cs:
            if not casa(c, fs) and (donde, c["texto"]) not in vistos:
                vistos.add((donde, c["texto"]))
                errores.append(
                    f'{donde}: "{c["texto"]}" no sale de `cifras` (añade el dato con su fuente o corrige la cifra)'
                )

    for g in sb.get("guion") or []:
        revisar(
            f"guion {g.get('id', '')}", de_palabras(g["texto"]) + de_digitos(g["texto"])
        )
    for donde, t in _textos_pantalla(sb):
        revisar(donde, de_digitos(t))
    return errores


def sin_fuente_publicacion(sb: dict, textos: dict[str, str]) -> list[str]:
    """Same check on what goes out in writing: title, description, captions, carousel."""
    fs = fuentes(sb)
    return [
        f'{k}: "{c["texto"]}" no sale de `cifras`'
        for k, t in textos.items()
        for c in de_digitos(t) + de_palabras(t)
        if not casa(c, fs)
    ]
