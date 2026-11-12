"""Closed catalog of MECHANICAL fixes for gate failures, used by `producir.py --auto`.

Mechanical = the gate's own message says what to change and nothing is invented: an anchor naming a
word the script holds exactly once, a text shown too briefly entering earlier inside its own scene, a
document's `hasta` lengthened to its reading time, an ambient sound given the rest of its scene...
Everything else (a figure missing from `cifras`, the same opening as recent videos, a script too long,
two texts on one cine photo) comes back untouched in `pendientes`, for Claude.

The gates are never loosened here: thresholds are read from the same `puertas._U` / rubric, and
producir re-runs the SAME gates after every fix. A fix that does not satisfy its gate fails again.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import anclas
import construir
import critico
import puertas

MARGEN = 0.05  # s past each threshold: a fix must not land exactly on the limit


# ───────────────────────────── anchors ─────────────────────────────
def desplazar(ancla: str, d: float) -> str:
    """'6:shares$+0.2' moved by d seconds (offset merged, '+0' dropped)."""
    a = str(ancla).strip()
    m = anclas._ANCLA.match(a)
    if not m:
        raise anclas.AnclaError(f"ancla mal escrita: {ancla!r}")
    base = a[: m.start(5)] if m.group(5) else a
    off = round(float(m.group(5) or 0) + d, 2)
    return base + (f"{off:+g}" if off else "")


def ancla_de_palabra(words: list[dict], i: int, fin: bool = False) -> str:
    """Anchor 'frase:palabra[#n][$]' that resolves to word i."""
    fr = anclas.frases(words)
    k = next(k for k, idx in enumerate(fr) if i in idx)
    w = anclas.norm(words[i]["text"])
    n = sum(anclas.norm(words[j]["text"]) == w for j in fr[k] if j <= i)
    return f"{k}:{w}" + (f"#{n}" if n > 1 else "") + ("$" if fin else "")


def reancla(words: list[dict], ancla: str) -> str | None:
    """A broken anchor whose word is unambiguous: 'ninety' inside 'ninety-three' of the same sentence,
    a word the whole script says once (sentences renumbered), or 'K$' = end of sentence K."""
    a = str(ancla).strip()
    fr = anclas.frases(words)
    if m := re.fullmatch(r"(\d+)\$([+-]\d+(?:\.\d+)?)?", a):
        k = int(m.group(1))
        return (
            ancla_de_palabra(words, fr[k][-1], True) + (m.group(2) or "")
            if k < len(fr)
            else None
        )
    m = anclas._ANCLA.match(a)
    if (
        not m or m.group(2) is None or m.group(3)
    ):  # an explicit #n was counted by hand: no guessing
        return None
    k, obj = int(m.group(1)), anclas.norm(m.group(2))
    dentro = [
        i
        for i in (fr[k] if k < len(fr) else [])
        if obj in anclas.norm(words[i]["text"]).split("-")
    ]
    todas = [i for i, w in enumerate(words) if anclas.norm(w["text"]) == obj]
    if len(dentro) == 1:
        i = dentro[0]
    elif not dentro and len(todas) == 1:
        i = todas[0]
    else:
        return None
    return ancla_de_palabra(words, i, bool(m.group(4))) + (m.group(5) or "")


def _sustituir(o, viejo: str, nuevo: str) -> int:
    """Replaces every string == viejo (anchors live in dicts and in lists such as `golpes`)."""
    n = 0
    items = (
        o.items()
        if isinstance(o, dict)
        else enumerate(o)
        if isinstance(o, list)
        else []
    )
    for k, v in list(items):
        if k == "guion":
            continue
        if v == viejo:
            o[k], n = nuevo, n + 1
        else:
            n += _sustituir(v, viejo, nuevo)
    return n


# ───────────────────────────── helpers ─────────────────────────────
def _objetos(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from _objetos(v)
    elif isinstance(o, list):
        for v in o:
            yield from _objetos(v)


def _t(words: list[dict], v, defecto: float) -> float:
    if isinstance(v, str):
        return anclas.t(words, v)
    return float(v) if isinstance(v, (int, float)) else defecto


# ───────────────────────────── one fixer per gate message ─────────────────────────────
# Each takes (sb, words, plan, match) and returns what it did, or None (not mechanical HERE).
def _ancla(sb, words, p, m):
    viejo = m.group(1)[1:-1]  # the gate prints anchors with repr(): '4$' -> 4$
    nuevo = reancla(words, viejo)
    if nuevo is None or _sustituir(sb, viejo, nuevo) == 0:
        return None
    return f"ancla {viejo!r} -> {nuevo!r}"


def _texto_breve(sb, words, p, m):
    k, txt = int(m.group(1)), m.group(2)
    s, ps = sb["escenas"][k], p["escenas"][k]
    minimo = puertas._U["texto_min_s"] + MARGEN
    for o in _objetos(s):
        if o.get("texto") != txt:
            continue
        en = _t(words, o.get("en"), ps["t0"])
        fin = min(_t(words, o.get("hasta"), ps["t1"]), ps["t1"])
        falta = minimo - (fin - en)
        if falta <= 0:
            continue
        alargar = min(falta, ps["t1"] - fin) if isinstance(o.get("hasta"), str) else 0.0
        adelantar = falta - alargar
        if adelantar > 0 and (
            not isinstance(o.get("en"), str) or en - adelantar < ps["t0"]
        ):
            return (
                None  # would leave its scene: the cut itself must move (not mechanical)
            )
        if alargar > 0:
            o["hasta"] = desplazar(o["hasta"], alargar)
        if adelantar > 0:
            o["en"] = desplazar(o["en"], -adelantar)
        return f'escena {k}: "{txt}" {minimo:.2f}s en pantalla'
    return None


def _pantalla_vacia(sb, words, p, m):
    k = int(m.group(1))
    s, ps = sb["escenas"][k], p["escenas"][k]
    con_texto = [
        o for o in _objetos(s) if o.get("texto") and isinstance(o["texto"], str)
    ]
    if not con_texto:
        return None
    o = min(con_texto, key=lambda o: _t(words, o.get("en"), ps["t0"]))
    objetivo = ps["t0"] + puertas._U["vacia_max_s"] - MARGEN
    en = _t(words, o.get("en"), ps["t0"])
    if not isinstance(o.get("en"), str) or en <= objetivo:
        return None
    o["en"] = desplazar(o["en"], objetivo - en)
    return f'escena {k}: "{o["texto"]}" entra {en - objetivo:.2f}s antes'


def _prueba_breve(sb, words, p, m):
    img, visto, desde, pide = m.group(1), float(m.group(2)), float(m.group(3)), float(m.group(4))
    # the same document can be shown twice: the one the gate measured starts at `desde`
    x = next(
        (
            x
            for x in sb.get("pruebas") or []
            if x.get("img") == img and abs(anclas.t(words, x["en"]) - desde) < 0.06
        ),
        None,
    )
    if x is None:
        return None
    falta = pide - visto + MARGEN
    t0 = anclas.t(words, x["en"])
    if t0 + visto + falta > p["D"]:
        return None  # capped by the end of the video: lengthening cannot help
    x["hasta"] = (
        desplazar(x["hasta"], falta)
        if x.get("hasta")
        else desplazar(x["en"], round(visto + falta, 2))
    )
    return f"prueba {img}: hasta {x['hasta']!r}"


def _sfx_dur(sb, words, p, m):
    j = int(m.group(1))
    x = sb["sonidos"][j]
    t = anclas.t(words, x["en"])
    fin = next((s["t1"] for s in p["escenas"] if s["t0"] <= t < s["t1"]), None)
    if fin is None:
        return None
    x["dur"] = round(max(1.0, fin - t), 2)  # an ambient bed lasts its scene
    return f"sonidos[{j}] ({x['sfx']}): dur {x['dur']}s"


def _duotono(sb, words, p, m):
    v = (sb.get("imagenes") or {}).get(m.group(1))
    if v is None or v.get("color") or v.get("archivo"):
        return None
    v["color"] = (
        True  # `archivo` would claim a provenance nobody checked; colour claims nothing
    )
    return f"imagenes.{m.group(1)}: color"


def _solapados(sb, words, p, m):
    k, ta, tb = int(m.group(1)), m.group(2), m.group(3)
    rs = sb["escenas"][k].get("rotulos") or []
    a = next((r for r in rs if r.get("texto") == ta), None)
    b = next((r for r in rs if r.get("texto") == tb), None)
    if a is None or b is None or not isinstance(b.get("en"), str):
        return None
    if _t(words, a.get("en"), 0) > _t(words, b.get("en"), 0):
        a, b = b, a
    if not isinstance(b.get("en"), str):
        return None
    a["hasta"] = b["en"]  # the first one leaves when the second one enters
    return f'escena {k}: "{a["texto"]}" hasta {b["en"]!r}'


def _contador(sb, words, p, m):
    k = int(m.group(1))
    s, ps = sb["escenas"][k], p["escenas"][k]
    valor = float(m.group(2).replace(",", ""))
    voz = puertas._voz_dice(
        p["words"], valor, ps["t0"] - puertas._U["contador_ventana_s"]
    )
    i = next((i for i, w in enumerate(words) if w["start"] == voz), None)
    if voz is None or i is None:
        return None
    ancla = ancla_de_palabra(words, i)
    if s.get("contador") and float(s["contador"].get("valor", -1)) == valor:
        s["contador"]["en"] = ancla
    elif ((s.get("flujo") or {}).get("contador") or {}).get("valor") == valor:
        s["flujo"]["en"] = desplazar(
            ancla, -0.5
        )  # plan(): the count starts at flujo.en + 0.5
    elif s.get("tipo") == "contador3d" and float(s.get("valor", -1)) == valor:
        s["en"] = (
            ancla  # plan(): counts from en - PRE + 0.05, inside the gate's tolerance
        )
    else:
        return None
    return f"escena {k}: contador de {m.group(2)} anclado a {ancla!r}"


def _aspecto_cine(sb, words, p, m):
    """A cine photo carries its one text as a caption, in the look this storyboard's captions already
    have (most common `pos` and `estilo`). Two texts would need a layout decision: not mechanical."""
    k = int(m.group(1))
    s = sb["escenas"][k]
    campos = [c for c in ("kicker", "titulo", "sub") if s.get(c)]
    otros = [
        (e.get("pos"), r.get("estilo"))
        for e in sb["escenas"]
        if e is not s and e.get("pos")
        for r in e.get("rotulos") or []
    ]
    if len(campos) != 1 or s.get("rotulos") or not otros:
        return None
    pos, estilo = max(set(otros), key=otros.count)
    v = s.pop(campos[0])
    r = dict(v) if isinstance(v, dict) else {"texto": v}
    s["rotulos"] = [{**({"estilo": estilo} if estilo else {}), **r}]  # the author's own style wins
    s.setdefault("pos", pos)
    return f"escena {k}: {campos[0]} -> rotulos (pos {s['pos']})"


CATALOGO = [
    (
        re.compile(r"^escena (\d+): con aspecto cine el texto va en `rotulos`"),
        _aspecto_cine,
    ),
    (re.compile(r"^ancla ('[^']*'|\"[^\"]*\"): '[^']*' aparece \d+ vez/veces"), _ancla),
    (re.compile(r"^ancla mal escrita: ('[^']*'|\"[^\"]*\")"), _ancla),
    (re.compile(r'^escena (\d+): "(.*)" se ve solo [\d.]+s desde'), _texto_breve),
    (re.compile(r"^escena (\d+) \(\w+\): pantalla vacía"), _pantalla_vacia),
    (
        re.compile(r"^prueba (.+?): se ve ([\d.]+)s desde ([\d.]+)s .* pide ([\d.]+)s: alarga"),
        _prueba_breve,
    ),
    (re.compile(r"^sonidos\[(\d+)\]: '[^']*' es ambiente: lleva `dur`"), _sfx_dur),
    (re.compile(r"^imagenes\.(.+?): duotono solo para archivo real"), _duotono),
    (re.compile(r'^escena (\d+): "(.*)" y "(.*)" se solapan'), _solapados),
    (re.compile(r"^escena (\d+): el contador de ([\d,.]+) arranca"), _contador),
]
_SIN_PLAN = {_ancla, _duotono, _aspecto_cine}  # the rest read scene times from the plan


def arreglar_storyboard(
    sb: dict, words: list[dict], errores: list[str]
) -> tuple[dict, list[str], list[str]]:
    """(new storyboard, what was fixed, what is left for Claude). Never mutates `sb`."""
    nuevo = copy.deepcopy(sb)
    p = None  # broken anchors: only the plan-free fixers can run this round
    # sounds do not move scenes, and a malformed one (ambient without `dur`) crashes plan()
    for intento in (sb, {**sb, "sonidos": []}):
        try:
            p = construir.plan(copy.deepcopy(intento), words)
            break
        except (anclas.AnclaError, KeyError, ValueError, TypeError, IndexError):
            continue
    hechos, pendientes = [], []
    for e in (x.strip() for x in errores):
        fn, m = next(
            ((fn, m) for rx, fn in CATALOGO if (m := rx.match(e))), (None, None)
        )
        r = (
            fn(nuevo, words, p, m)
            if fn and (p is not None or fn in _SIN_PLAN)
            else None
        )
        if r:
            hechos.append(r)
        else:
            pendientes.append(e)
    return nuevo, list(dict.fromkeys(hechos)), pendientes


# ───────────────────────────── gates after the build / render ─────────────────────────────
def _ventanas(proy: Path):
    return critico.ventanas(
        critico.plan_de_html((proy / "index.html").read_text(encoding="utf-8"))
    )


def _aplicar_parches(sb: dict, fallos: list[dict]) -> tuple[dict, list[str], list[str]]:
    """The critic's own closed catalog (critico.aplicar), one failure at a time so a patch that
    changes nothing (fondo_suave on a photo, opacity already at its floor) stays pending."""
    hechos, pendientes = [], []
    for f in fallos:
        nuevo, h = critico.aplicar(sb, [f["parche"]]) if f.get("parche") else (sb, [])
        if h:
            sb, hechos = nuevo, hechos + h
        else:
            pendientes.append(critico.linea(f))
    return sb, list(dict.fromkeys(hechos)), pendientes


def fallos_contraste(proy: Path, sb: dict, detalle: str) -> list[dict]:
    qa = {
        "puertas": [{"puerta": "contraste", "ok": False, "detalle": detalle}],
        "_aviso": (sb.get("aviso") or {}).get("lineas") or [],
    }
    return critico.fallos_de_qa(qa, _ventanas(proy))


def fallos_ritmo(proy: Path, words: list[dict], detalle: str) -> list[dict]:
    m = re.search(r"([\d.]+) s \(desde t≈([\d.]+) s\)", detalle)
    if not m:
        return []
    rr = {"max_s": float(m.group(1)), "desde_s": float(m.group(2))}
    rub = critico.cargar_rubrica(proy)
    u = {k: v for c in rub["criterios"].values() for k, v in c.items() if k != "nombre"}
    return critico.revisar_ritmo(rr, words, _ventanas(proy), u)


def arreglar(
    proy: Path,
    fallidas: dict[str, str],
    informe: dict | None = None,
    bloquean: tuple[str, ...] = ("alta",),
) -> tuple[list[str], list[str], bool]:
    """One --auto round over producir's failed gates ({name: full detail}) and the critic's last
    round. Writes the storyboard when something changed. Returns (fixed, pending, re-synth voice)."""
    ruta = proy / "storyboard.json"
    original = ruta.read_text(encoding="utf-8")
    sb = json.loads(original)
    words = json.loads((proy / "assets" / "words.json").read_text(encoding="utf-8"))
    hechos, pendientes, voz = [], [], False
    for nombre, detalle in fallidas.items():
        if nombre == "storyboard":
            errores = re.findall(r"^\s+- (.+)$", detalle, re.MULTILINE)
            sb, h, pend = arreglar_storyboard(sb, words, errores or [detalle])
        elif nombre == "contraste":
            sb, h, pend = _aplicar_parches(sb, fallos_contraste(proy, sb, detalle))
            pend = pend or ([] if h else [f"contraste: {detalle.strip()}"])
        elif nombre == "ritmo":
            sb, h, pend = _aplicar_parches(sb, fallos_ritmo(proy, words, detalle))
            pend = pend or ([] if h else [f"ritmo: {detalle.strip()}"])
        else:
            h, pend = [], [f"{nombre}: {detalle.strip()}"]
        hechos += h
        pendientes += pend
    if informe:
        for f in informe["rondas"][-1]["fallos"]:
            if f["severidad"] not in bloquean:
                continue
            if f.get("parche"):
                sb, h, pend = _aplicar_parches(sb, [f])
                hechos, pendientes = hechos + h, pendientes + pend
            elif f["criterio"] == "V1" and " dentro de frase " in f["detalle"]:
                voz = True  # the critic's own advice: re-synthesise, not the storyboard
                pendientes.append(critico.linea(f))  # still failing until a re-run measures it
            else:
                pendientes.append(critico.linea(f))
    if hechos:
        ruta.write_text(critico.volcar(sb, original), encoding="utf-8")
    return hechos, pendientes, voz
