"""Plan-level gates for what the older gates let through (first average-401k, 6-nov-2026): voice with no
text on screen, mispronounced finance terms, empty screens, text that vanishes, colliding captions.
All are pure functions over the storyboard or the plan, and return one error per defect."""

from __future__ import annotations

import itertools
import json
import re
from pathlib import Path

_U = json.loads((Path(__file__).parent / "rubrica.json").read_text(encoding="utf-8"))[
    "criterios"
]["E1"]

# Published before these gates: re-rendering them must keep working. Closed list, never add to it.
ANTERIORES = frozenset(
    {
        "aws-profit",
        "binance-heist",
        "fed-vs-card",
        "gdp-annualized",
        "grace-groner",
        "housing-turn",
        "interest-outran-defense",
        "interest-vs-defense",
        "midterm-rally",
        "poc-read-janitor",
        "read-janitor",
        "ronald-wayne",
        "saving-rate",
    }
)

# Kokoro's G2P (misaki) reads the digits as a plain number, measured 6-nov: "401k" -> fˈɔɹ hˈʌndɹəd wˈʌn kˈA.
# shortcut: closed list of measured terms, add one when the G2P is measured to misread it
PRONUNCIACION = (
    (re.compile(r"\b401\s?\(?k\b\)?", re.IGNORECASE), "four-oh-one-k"),
    (re.compile(r"\b403\s?\(?b\b\)?", re.IGNORECASE), "four-oh-three-b"),
    (re.compile(r"\b457\s?\(?b\b\)?", re.IGNORECASE), "four-fifty-seven-b"),
    (re.compile(r"(?<![$\d])\b529 plan", re.IGNORECASE), "five twenty-nine plan"),
)
TIPOS_CON_FONDO = ("titulo", "cta", "revelacion")


def pronunciacion(sb: dict) -> list[str]:
    return [
        f'guion {f.get("id", k)}: "{m.group(0)}" suena mal en la voz: escribe "{bien}"'
        for k, f in enumerate(sb.get("guion") or [])
        for mal, bien in PRONUNCIACION
        for m in mal.finditer(f.get("texto", ""))
    ]


def voz_sin_subtitulo(p: dict) -> list[str]:
    """`limpio` hides the captions (motor.js), and outside `subtitulos` only the scene's own text is left."""
    c0, c1 = p["subtitulos"]
    mudos: dict[int, list[dict]] = {}
    for i, w in enumerate(p["words"]):
        medio = (w["start"] + w["end"]) / 2
        for k, s in enumerate(p["escenas"]):
            if s["t0"] <= medio < s["t1"]:
                if s.get("limpio") or (not c0 <= i <= c1 and not s["texto_visible"]):
                    mudos.setdefault(k, []).append(w)
                break
    return [
        f"escena {k}: voz sin subtítulo {ws[0]['start']:.1f}-{ws[-1]['end']:.1f}s "
        f'("{" ".join(w["text"] for w in ws)[:40]}"): quita `limpio` o añade texto'
        for k, ws in mudos.items()
    ]


def _textos(s: dict) -> list[tuple[str, float, float]]:
    """Every designed text of a scene as (text, enters, leaves), whatever the scene type calls it."""
    out = []

    def caminar(o):
        if isinstance(o, dict):
            if o.get("texto") and isinstance(o["texto"], str):
                en = o.get("en")
                en = en if isinstance(en, (int, float)) else s["t0"]
                hasta = o.get("hasta")
                hasta = hasta if isinstance(hasta, (int, float)) else s["t1"]
                out.append((o["texto"], en, min(hasta, s["t1"])))
            for v in o.values():
                caminar(v)
        elif isinstance(o, list):
            for v in o:
                caminar(v)

    caminar(s)
    return out


def pantalla_vacia(p: dict) -> list[str]:
    """A title card lives on its text: until it enters there is a faint background (or nothing)."""
    out = []
    for k, s in enumerate(p["escenas"]):
        f = s.get("fondo")
        nitido = isinstance(f, dict) and f.get("opacidad", 0) > _U["fondo_tenue_max"]
        textos = _textos(s)
        if s["tipo"] not in TIPOS_CON_FONDO or nitido or not textos:
            continue
        vacia = min(t[1] for t in textos) - s["t0"]
        if vacia > _U["vacia_max_s"]:
            out.append(
                f"escena {k} ({s['tipo']}): pantalla vacía {vacia:.1f}s desde {s['t0']:.1f}s "
                f"(> {_U['vacia_max_s']}): adelanta el primer texto"
            )
    return out


def texto_breve(p: dict) -> list[str]:
    return [
        f'escena {k}: "{txt}" se ve solo {fin - en:.2f}s desde {en:.1f}s (< {_U["texto_min_s"]}): '
        "retrasa el corte o adelanta el texto"
        for k, s in enumerate(p["escenas"])
        for txt, en, fin in _textos(s)
        if fin - en < _U["texto_min_s"]
    ]


def rotulos_solapados(p: dict) -> list[str]:
    """Captions are absolute at the scene's `pos` (plantilla.tpl): same height + same time = on top of each other."""
    out = []
    for k, s in enumerate(p["escenas"]):
        for a, b in itertools.combinations(s.get("rotulos") or [], 2):
            fin_a, fin_b = a.get("hasta", s["t1"]), b.get("hasta", s["t1"])
            if a.get("top") == b.get("top") and max(a["en"], b["en"]) < min(
                fin_a, fin_b
            ):
                out.append(
                    f'escena {k}: "{a["texto"]}" y "{b["texto"]}" se solapan '
                    f"(misma altura desde {max(a['en'], b['en']):.1f}s): un solo rótulo, `hasta` o `top`"
                )
    return out


def errores(sb: dict, p: dict) -> list[str]:
    if sb.get("ref") in ANTERIORES:
        return []
    return (
        pronunciacion(sb)
        + voz_sin_subtitulo(p)
        + pantalla_vacia(p)
        + texto_breve(p)
        + rotulos_solapados(p)
    )
