"""Plan-level gates for what the older gates let through (first average-401k, 6-nov-2026): voice with no
text on screen, mispronounced finance terms, empty screens, text that vanishes, colliding captions.
All are pure functions over the storyboard or the plan, and return one error per defect."""

from __future__ import annotations

import itertools
import json
import re
import subprocess
from pathlib import Path

import trazabilidad

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


def contador_adelantado(p: dict) -> list[str]:
    """A counter that runs before the voice says the figure spoils it: first average-401k started 0.69 s early
    (corrected: 0.09 s). A figure the voice never says has nothing to be early for: `sin_fuente` still sees it."""
    out = []
    ws = p["words"]
    for k, s in enumerate(p["escenas"]):
        fl = s.get("flujo") or {}
        cuentas = []
        if s["tipo"] == "contador3d":
            cuentas.append((s["t0"] + 0.05, s["valor"]))
        if s.get("contador"):
            cuentas.append((s["contador"]["en"], s["contador"]["valor"]))
        if fl.get("contador"):
            cuentas.append((fl["en"] + 0.5, fl["contador"]["valor"]))
        for ini, valor in cuentas:
            voz = _voz_dice(ws, valor, s["t0"] - _U["contador_ventana_s"])
            if voz is not None and voz - ini > _U["contador_antes_max_s"]:
                out.append(
                    f"escena {k}: el contador de {valor:,} arranca {voz - ini:.2f}s antes de que la voz diga la cifra "
                    f"(> {_U['contador_antes_max_s']}): ancla el contador a la cifra"
                )
    return out


def _voz_dice(ws: list[dict], valor: float, desde: float) -> float | None:
    """Second the voice starts saying `valor`, at the precision it says it."""
    for i, w in enumerate(ws):
        if w["start"] < desde:
            continue
        for j in range(i + 1, min(i + 9, len(ws)) + 1):
            frase = " ".join(x["text"].strip(".,?!") for x in ws[i:j])
            r = trazabilidad.de_palabras(frase) + trazabilidad.de_digitos(frase)
            if len(r) == 1 and frase.lower().startswith(r[0]["texto"].split()[0]) and trazabilidad.casa(r[0], [valor]):
                return w["start"]
    return None


def prueba_breve(sb: dict, p: dict) -> list[str]:
    """A document only proves something if it can be read: entry + the highlighted phrase at 3 words/s."""
    out = []
    pruebas = {x.get("img"): x for x in sb.get("pruebas") or []}
    for pr in p.get("pruebas") or []:
        n = len(str(pruebas.get(pr.get("img"), {}).get("texto") or "").split())
        minimo = _U["prueba_entrada_s"] + n / _U["prueba_palabras_s"]
        if pr["t1"] - pr["t0"] < minimo:
            out.append(
                f"prueba {pr.get('img')}: se ve {pr['t1'] - pr['t0']:.2f}s desde {pr['t0']:.1f}s y su frase de {n} palabras "
                f"pide {minimo:.2f}s: alarga `hasta`"
            )
    return out


_FORMAS_HABLADAS = tuple(
    re.compile(re.escape(b).replace(r"\ ", "[ -]").replace(r"\-", "[ -]"), re.IGNORECASE) for _, b in PRONUNCIACION
)


def forma_hablada_escrita(sb: dict, p: dict | None = None) -> list[str]:
    """What is respelled for the voice must never be read: "four-oh-one-k" on screen or in a caption."""
    textos = [(d, t) for d, t in trazabilidad._textos_pantalla(sb)] + list(_textos_publicacion(sb).items())
    if p:
        c0, c1 = p["subtitulos"]
        textos.append(("subtítulos", " ".join(w["text"] for w in p["words"][c0 : c1 + 1])))
    return [
        f'{d}: "{m.group(0)}" es la forma para la voz; escrito va "401(k)" o similar'
        for d, t in textos
        for f in _FORMAS_HABLADAS
        for m in f.finditer(t)
    ]


def _textos_publicacion(sb: dict) -> dict[str, str]:
    pub, so = sb.get("publicacion") or {}, sb.get("social") or {}
    out = {"título": pub.get("titulo") or "", "descripción": pub.get("descripcion") or "", "caption": so.get("caption") or ""}
    for k, d in enumerate(so.get("carrusel") or []):
        for c in ("kicker", "titulo", "texto"):
            out[f"carrusel {k + 1} {c}"] = d.get(c) or ""
    return {k: v for k, v in out.items() if v}


def publicacion(sb: dict) -> list[str]:
    """Written figures out of `cifras`."""
    if not sb.get("publicacion") and not sb.get("social"):
        return []
    return trazabilidad.sin_fuente_publicacion(sb, _textos_publicacion(sb))


def historia_corte(sb: dict, words: list[dict]) -> list[str]:
    """The story is the hook cut at `hasta`: 14 s max (social.py). It must end on a finished sentence."""
    h = (sb.get("social") or {}).get("historia") or {}
    if not h.get("hasta"):
        return []
    import anclas

    try:
        t = anclas.t(words, h["hasta"])
    except anclas.AnclaError as e:
        return [f"historia: `hasta`: {e}"]
    previas = [w for w in words if w["end"] <= t + 0.01]
    ult = previas[-1]["text"] if previas else ""
    if t + 0.35 > 14.0:
        return [f"historia: `hasta` en {t:.1f}s se corta a 14 s en medio de una frase: elige una frase anterior"]
    if not re.search(r"[.?!][\"')\]]*$", ult):
        return [f'historia: el corte en {t:.1f}s cae tras "{ult}", sin terminar la frase: ancla al final de una frase']
    return []


def g2p_dudosas(sb: dict, python: Path, script: Path) -> list[str]:
    """Before synthesis, in the Kokoro venv: words its lexicon does not know (espeak guesses them) and acronyms
    read as a word ("AWS" -> "oz", published that way in aws-profit). `pronuncia_ok`: heard and accepted."""
    texto = " ".join(g["texto"] for g in sb.get("guion") or [])
    r = subprocess.run([str(python), str(script)], input=texto.encode("utf-8"), capture_output=True, check=False)
    if r.returncode:
        return [f"g2p no midió ({r.stderr.decode('utf-8', 'replace')[-200:]})"]
    return filtrar_g2p(json.loads(r.stdout.decode("utf-8").splitlines()[-1]), sb.get("pronuncia_ok") or [])


def filtrar_g2p(d: dict, aceptadas: list[str]) -> list[str]:
    out = [
        f'"{w}" no está en el léxico de Kokoro y espeak adivina /{f}/: escríbela como suena o escúchala y añádela a `pronuncia_ok`'
        for w, f in d["desconocidas"].items()
        if w not in aceptadas
    ]
    # a spelled acronym stresses every letter ("IOU" 3 marks); fewer marks = read as a word
    out += [
        f'"{w}" se lee como palabra /{f}/, no letra a letra: escribe "A-W-S" o similar, o añádela a `pronuncia_ok`'
        for w, f in d["siglas"].items()
        if w not in aceptadas and f.count("ˈ") + f.count("ˌ") < len(w)
    ]
    return out


def tema_valido(sb: dict) -> list[str]:
    """`tema` is a CSS class, not the topic: "average 401(k) vs median" shifted every frame down 300 px on the
    published average-401k. `cine` only exists on top of `editorial` (plantilla.tpl)."""
    t = sb.get("tema")
    if t not in (None, "", "claro", "editorial"):
        return [f'`tema` {t!r} no existe (claro, editorial): el asunto del vídeo no va ahí, descoloca toda la maqueta']
    if sb.get("aspecto") == "cine" and t != "editorial":
        return ['`aspecto: cine` necesita `tema: "editorial"`']
    return []


def errores(sb: dict, p: dict) -> list[str]:
    if sb.get("ref") in ANTERIORES:
        return []
    return (
        tema_valido(sb)
        + pronunciacion(sb)
        + voz_sin_subtitulo(p)
        + pantalla_vacia(p)
        + texto_breve(p)
        + rotulos_solapados(p)
        + contador_adelantado(p)
        + prueba_breve(sb, p)
        + forma_hablada_escrita(sb, p)
        + publicacion(sb)
        + historia_corte(sb, p["words"])
        + trazabilidad.sin_fuente(sb)
    )
