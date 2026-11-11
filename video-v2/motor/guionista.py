"""Crítico de GUION (bloque 1.1 del PLAN): elige entre alternativas ANTES de renderizar nada.

    python video-v2/motor/guionista.py video-v2/<proyecto>            # elige y escribe el guion
    python video-v2/motor/guionista.py video-v2/<proyecto> --ciego    # + par A/B (texto + voz Kokoro)

Lee `<proyecto>/guiones.json`:
    {"estructuras": [{"id", "nombre", "frases": [{"id", "texto", "giro"?}]}],   # 2-3 completas
     "ganchos":     [{"id", "texto"}],                                          # 3-5, sustituyen la 1.ª frase
     "juicio":      {"<id candidato>": {"una_idea": 1-5, "bucle_abierto": 1-5, "giro": 1-5, "nota": ""}}}

Dos etapas: 1) gana una estructura; 2) gana un gancho sobre esa estructura (ids "estructura+gN").
Orden: primero las PUERTAS medibles (menos fallos gana), luego el juicio (lo que no se mide).
Las puertas de retención (G-GANCHO, G-TU, G-CIFRAS, G-COMODIN, G-CIERRE) y su evidencia:
docs/mejora/guion/. `producir.py` las aplica solo a guiones nuevos (puerta_guion).
Si falta juicio de algún candidato, lo lista con sus puertas y sale con código 2: se rellena y se repite.
Sale con `guiones.md` (ganador + descartadas y por qué) y el `guion` del storyboard. PROVISIONAL:
umbrales sin calibrar con notas a ciegas del usuario (docs/RUBRICA.md).
"""

from __future__ import annotations

import itertools
import json
import random
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import NoReturn

RAIZ = Path(__file__).resolve().parents[2]

PALABRAS_MIN, PALABRAS_MAX = 85, 110  # producir.md: 85-110 palabras ≈ 27-35 s
PALABRAS_POR_S = 3.1  # medido 26-sep con Kokoro: 85 palabras = 27,5 s
HUECO_GIRO_MAX_S = 10.0  # re-gancho cada ~8-10 s
CRITERIOS = ("una_idea", "bucle_abierto", "giro")
# PROVISIONAL thresholds (docs/mejora/guion/linea_base.md): 10 scripts, 5 with >=30 measured views.
TU_PALABRA_MAX = 19  # second 6 at 3.1 words/s; measured: median 19 words before 6 s (words.json, n=10)
CIFRAS_MAX = 3
CIERRE_VENTANA = 3  # a close type cannot repeat within the last N published videos

NUMEROS = {
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
    "twenty",
    "thirty",
    "forty",
    "fifty",
    "sixty",
    "seventy",
    "eighty",
    "ninety",
    "hundred",
    "thousand",
    "million",
    "billion",
    "trillion",
    "percent",
    "half",
    "double",
    "triple",
}
RELLENO = (
    "so basically",
    "basically",
    "you see",
    "let me tell you",
    "in this video",
    "today we",
    "actually",
    "literally",
    "kind of",
    "sort of",
    "you know",
)
# Closed list. Measured: "here's the part nobody tells you" in 7 of 10 scripts, a variant in an 8th.
COMODINES = (
    "here's the part",
    "here's the thing",
    "here's the catch",
    "here's the kicker",
    "here's the twist",
    "here's the crazy part",
    "here's the uncomfortable part",
    "here's the problem",
    "here's the truth",
    "here's what nobody",
    "here's what they",
    "nobody tells you",
    "nobody talks about",
    "no one tells you",
    "no one talks about",
    "what they don't tell you",
    "they don't want you to know",
    "most people don't know",
    "most people don't realize",
    "let that sink in",
    "think about that",
    "the truth is",
    "the real question is",
    "but wait",
    "and that's not all",
    "you won't believe",
)
CONTRASTE = {"but", "and", "yet", "while", "still", "instead", "than", "you", "your"}
TU = {
    "you",
    "your",
    "you're",
    "you'll",
    "you've",
    "yours",
    "yourself",
}
# Bare "anyone" is not a stake: "Wall Street wasn't cheering for anyone" (midterm-rally) was a false hit.
TU_FRASES = {"most people", "almost everyone", "anyone who"}
# Closed list of names a global English-speaking viewer needs no explanation for.
CONOCIDOS = {
    "America",
    "American",
    "Americans",
    "Amazon",
    "Apple",
    "Bitcoin",
    "Congress",
    "Dow",
    "Fed",
    "Google",
    "Microsoft",
    "Street",
    "Tesla",
    "Trump",
    "Wall",
    "Walmart",
    "AI",
    "CEO",
    "IRS",
    "US",
    "USA",
    "January",
    "February",
    "March",
    "April",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
}
PRONOMBRES = {"he", "she", "it", "they", "that", "those", "these"}
IMPERATIVOS = {
    "add",
    "ask",
    "check",
    "compare",
    "count",
    "don't",
    "find",
    "look",
    "open",
    "own",
    "pull",
    "read",
    "remember",
    "run",
    "start",
    "stop",
    "try",
    "watch",
    "write",
}
UNIDADES = {"dollar", "dollars", "cent", "cents", "percent", "points", "bucks"}
MAGNITUDES = {"hundred", "thousand", "million", "billion", "trillion"}
PEQUENAS = {
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
}
# Stock phrases ("here's", "nobody") no longer count as a re-hook: see G-COMODIN.
GIROS = (
    "but",
    "instead",
    "that's not",
    "the catch",
    "turns out",
    "except",
    "until",
)
VACIAS = {
    "this",
    "that",
    "what",
    "they",
    "them",
    "with",
    "have",
    "from",
    "your",
    "will",
    "would",
    "there",
    "their",
    "then",
    "than",
    "just",
    "into",
    "about",
    "were",
    "been",
    "when",
    "which",
    "think",
    "does",
    "these",
    "those",
    "only",
    "some",
    "more",
    "most",
    "very",
    "here",
    "it's",
    "that's",
    "here's",
}


class FaltaJuicio(Exception):
    def __init__(self, faltan: list[str]):
        super().__init__(f"falta juicio de: {', '.join(faltan)}")
        self.faltan = faltan


def _tokens(texto: str) -> list[str]:
    return re.findall(r"[a-z0-9$%.']+(?:-[a-z0-9]+)*", texto.lower())


def tiene_cifra(texto: str) -> bool:
    if re.search(r"\d", texto):
        return True
    return any(p in NUMEROS for t in _tokens(texto) for p in t.split("-"))


def _contiene(texto: str, frase: str) -> bool:
    return (
        re.search(rf"(?<![a-z']){re.escape(frase)}(?![a-z'])", texto.lower())
        is not None
    )


def _frases_guion(frases: list[dict]) -> list[dict]:
    """Frases para el storyboard. `giro` se conserva: producir.py repite G-GIRO sobre este guion."""
    return [
        {
            "id": f["id"],
            "texto": f["texto"],
            **({"giro": True} if f.get("giro") else {}),
        }
        for f in frases
    ]


def _es_giro(f: dict) -> bool:
    return (
        bool(f.get("giro"))
        or tiene_cifra(f["texto"])
        or any(_contiene(f["texto"], g) for g in GIROS)
    )


def _raiz(t: str) -> str:
    t = t.strip(".'")
    return t[:-1] if len(t) > 4 and t.endswith("s") else t


def _contenido(texto: str) -> set[str]:
    return {
        _raiz(t)
        for t in _tokens(texto)
        if len(t) >= 4 and t not in VACIAS and not tiene_cifra(t)
    }


def _normal(texto: str) -> str:
    return texto.lower().replace("’", "'")


def _es_num(t: str) -> bool:
    if re.fullmatch(r"\$?\d[\d,]*(?:\.\d+)?%?", t):
        return True
    validos = NUMEROS - UNIDADES - {"half", "double", "triple"}
    return all(p in validos for p in t.split("-"))


def cifras_protagonistas(texto: str) -> list[str]:
    """Distinct figures said aloud: contiguous number words are one; years and bare small counts are none."""
    toks = re.findall(
        r"\$?\d[\d,]*(?:\.\d+)?%?|[a-z]+(?:-[a-z]+)*|[^\sa-z0-9]", _normal(texto)
    )
    grupos, i = [], 0
    while i < len(toks):
        if not _es_num(toks[i]):
            i += 1
            continue
        g = [toks[i]]
        i += 1
        while i < len(toks):
            sig = toks[i + 1] if i + 1 < len(toks) else ""
            if (
                _es_num(toks[i])
                or toks[i] in UNIDADES
                or toks[i] == "point"
                or toks[i] == "and"
                and _es_num(sig)
            ):
                g.append(toks[i])
            elif not (toks[i] == "," and _es_num(sig) and g[-1] in MAGNITUDES):
                break  # the comma case: "seven million, two hundred thousand" is one spoken figure
            i += 1
        grupos.append(g)

    out: list[str] = []
    for g in grupos:
        nums = [t for t in g if t not in UNIDADES and t != "and"]
        anio = re.fullmatch(r"(?:19|20)\d\d", g[0]) is not None or (
            len(g) == 2
            and g[0] in ("nineteen", "twenty")
            and g[1] not in MAGNITUDES | UNIDADES
        )
        cuenta = (len(g) == 1 and g[0] in PEQUENAS) or nums == ["one"]
        # "a hundred and eighty" and "one hundred and eighty" are the same figure
        clave = " ".join(nums[1:] if nums[:2] == ["one", "hundred"] else nums)
        if not anio and not cuenta and clave not in out:
            out.append(clave)
    return out


def _gancho(fs: list[dict]) -> str:
    """Text up to the first sentence end, even if it spans several script phrases."""
    texto = " ".join(f["texto"].strip() for f in fs)
    return re.split(r"(?<=[.?!])\s", texto, maxsplit=1)[0]


def _nombres_sin_explicar(gancho: str, guion: str) -> list[str]:
    out = []
    aposicion = r",\s+(?:a|an|the|its|one|who|which|[A-Z][a-z]+'s)\b"
    for m in re.finditer(r"\b[A-Z][A-Za-z]*(?:\s+[A-Z][A-Za-z]*)*", gancho):
        palabras = m.group().split()
        if m.group() == "I":
            continue
        # shortcut: a lone capitalised first word counts only if it reappears mid-sentence;
        # a name used once as the very first word escapes. Upgrade with a dictionary if it bites.
        solo_al_inicio = (
            m.start() == 0
            and len(palabras) == 1
            and not re.fullmatch(r"[A-Z]{2,}", palabras[0])
        )
        if solo_al_inicio and not re.search(
            rf"[a-z,]\s{re.escape(palabras[0])}\b", guion
        ):
            continue
        if all(p in CONOCIDOS for p in palabras):
            continue
        if not re.match(aposicion, gancho[m.end() :]):
            out.append(m.group())
    return out


def _puerta_gancho(fs: list[dict]) -> dict:
    g = _gancho(fs)
    toks = [t.strip(".,:;?!'") for t in _normal(g).split()]
    nombres = _nombres_sin_explicar(g, " ".join(f["texto"] for f in fs))
    motivos = []
    if toks and _es_num(toks[0]) and not CONTRASTE & set(toks):
        motivos.append("cifra sola: empieza por el número, sin sujeto ni contraste")
    if nombres:
        motivos.append(f"nombre sin explicar: {', '.join(nombres)}")
    if toks and toks[0] in PRONOMBRES:
        motivos.append(f"pronombre sin referente: {toks[0]}")
    return {
        "id": "G-GANCHO",
        "ok": not motivos,
        "detalle": "; ".join(motivos) or "se entiende sin contexto",
    }


def _puerta_tu(fs: list[dict]) -> dict:
    ps = [w.strip('.,:;?!"') for f in fs for w in _normal(f["texto"]).split()]
    pos = next(
        (
            i + 1
            for i, w in enumerate(ps)
            if w in TU or (i > 0 and f"{ps[i - 1]} {w}" in TU_FRASES)
        ),
        None,
    )
    return {
        "id": "G-TU",
        "ok": pos is not None and pos <= TU_PALABRA_MAX,
        "detalle": f"espectador en la palabra {pos} (≤{TU_PALABRA_MAX})"
        if pos
        else "nunca habla del espectador",
    }


def tipo_cierre(frases: list) -> str:
    """Close type of the last sentence: dicotomia, pregunta, imperativo, dato or afirmacion."""
    ult = frases[-1]["texto"] if isinstance(frases[-1], dict) else frases[-1]
    ult = re.split(r"(?<=[.?!])\s+", ult.strip())[-1]
    if ult.endswith("?"):
        return "dicotomia" if re.search(r"\bor\b", ult.lower()) else "pregunta"
    if _normal(ult).split()[0].strip(".,:;") in IMPERATIVOS:
        return "imperativo"
    return "dato" if cifras_protagonistas(ult) else "afirmacion"


def refs_publicadas() -> list[str]:
    """Published refs, newest first (data/omega.sqlite; empty when the base is missing)."""
    ruta = RAIZ / "data" / "omega.sqlite"
    if not ruta.exists():
        return []
    con = sqlite3.connect(f"{ruta.as_uri()}?mode=ro", uri=True)
    try:
        filas = con.execute(
            "SELECT production_ref, publish_at, recorded_at FROM production_video"
            " WHERE platform = 'youtube'"
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        con.close()

    def cuando(f: tuple) -> float:
        if f[1]:
            return datetime.fromisoformat(f[1]).timestamp()
        return float(f[2] or 0)

    return [f[0] for f in sorted(filas, key=cuando, reverse=True)]


def cierres_previos(proy: Path, publicados: list[str] | None = None) -> list[str]:
    """Close types of earlier videos, newest first. Without a base: storyboard mtime of the siblings."""
    orden = refs_publicadas() if publicados is None else publicados
    if not orden:
        # shortcut: mtime order, a fresh clone scrambles it; same limit as medir_parecido.puerta_repeticion
        sbs = proy.parent.glob("*/storyboard.json")
        orden = [
            s.parent.name
            for s in sorted(sbs, key=lambda s: s.stat().st_mtime, reverse=True)
        ]
    out = []
    for ref in orden:
        ruta = proy.parent / ref / "storyboard.json"
        if ref == proy.name or not ruta.exists():
            continue
        guion = json.loads(ruta.read_text(encoding="utf-8")).get("guion")
        if guion:
            out.append(tipo_cierre(guion))
    return out


def puerta_guion(proy: Path, publicados: list[str] | None = None) -> tuple[bool, str]:
    """Gate for producir.py: new scripts only, so re-rendering a published video keeps working."""
    pub = refs_publicadas() if publicados is None else publicados
    if proy.name in pub or list((proy / "renders").glob("*-final.mp4")):
        return True, "exento: vídeo anterior a la puerta o ya publicado"
    sb = json.loads((proy / "storyboard.json").read_text(encoding="utf-8"))
    ps = puertas(sb["guion"], previos=cierres_previos(proy, pub))
    fallan = [f"{p['id']}: {p['detalle']}" for p in ps if not p["ok"]]
    if not sb.get(
        "formato"
    ):  # edicion.preparar exempts it from the repetition gate otherwise
        fallan.append(
            "G-FORMATO: falta `formato`, sin él no pasa por la puerta de edición"
        )
    return not fallan, " · ".join(fallan) or f"{len(ps)} puertas de guion OK"


def puertas(frases: list, previos: list[str] | None = None) -> list[dict]:
    """Criterios que se miden sin juicio. `frases`: textos o dicts {texto, giro?}.
    `previos`: close types of earlier videos, newest first (None = no history, nothing vetoed)."""
    fs = [f if isinstance(f, dict) else {"texto": f} for f in frases]
    n = [len(f["texto"].split()) for f in fs]
    total = sum(n)
    out = []

    out.append(_puerta_gancho(fs))
    out.append(_puerta_tu(fs))
    cifras = cifras_protagonistas(" ".join(f["texto"] for f in fs))
    out.append(
        {
            "id": "G-CIFRAS",
            "ok": len(cifras) <= CIFRAS_MAX,
            "detalle": f"{len(cifras)} cifras dichas (≤{CIFRAS_MAX}): {'; '.join(cifras)}",
        }
    )
    comodines = sorted(
        {
            c
            for f in fs
            for c in COMODINES
            if _contiene(_normal(f["texto"]).replace("here is", "here's"), c)
        }
    )
    out.append(
        {
            "id": "G-COMODIN",
            "ok": not comodines,
            "detalle": ", ".join(comodines) or "sin frases comodín",
        }
    )
    tipo = tipo_cierre(fs)
    vetado = tipo in (previos or [])[:CIERRE_VENTANA]
    out.append(
        {
            "id": "G-CIERRE",
            "ok": not vetado,
            "detalle": f"cierre «{tipo}»"
            + (f" ya usado en los últimos {CIERRE_VENTANA} vídeos" if vetado else ""),
        }
    )
    out.append(
        {
            "id": "G-LARGO",
            "ok": PALABRAS_MIN <= total <= PALABRAS_MAX,
            "detalle": f"{total} palabras ({PALABRAS_MIN}-{PALABRAS_MAX}) ≈ {total / PALABRAS_POR_S:.1f} s",
        }
    )

    hallado = sorted({r for f in fs for r in RELLENO if _contiene(f["texto"], r)})
    out.append(
        {
            "id": "G-RELLENO",
            "ok": not hallado,
            "detalle": ", ".join(hallado) or "sin relleno",
        }
    )

    # inicio estimado de cada frase giro (la 1.ª siempre cuenta: es el gancho) + el final del guion
    marcas, acum = [], 0
    for i, f in enumerate(fs):
        if i == 0 or _es_giro(f):
            marcas.append(acum / PALABRAS_POR_S)
        acum += n[i]
    marcas.append(total / PALABRAS_POR_S)
    huecos = [b - a for a, b in itertools.pairwise(marcas)]
    peor = max(huecos, default=0.0)
    out.append(
        {
            "id": "G-GIRO",
            "ok": peor <= HUECO_GIRO_MAX_S,
            "detalle": f"hueco máx. sin giro {peor:.1f} s (≤{HUECO_GIRO_MAX_S:.0f} s)",
        }
    )

    comun = (
        sorted(_contenido(fs[0]["texto"]) & _contenido(fs[-1]["texto"]))
        if len(fs) > 1
        else []
    )
    out.append(
        {
            "id": "G-BUCLE",
            "ok": bool(comun),
            "detalle": f"enlaza por: {', '.join(comun)}"
            if comun
            else "la última frase no retoma la primera",
        }
    )
    return out


def candidatos_gancho(estructura: dict, ganchos: list[dict]) -> list[dict]:
    """La estructura tal cual + una variante por gancho (sustituye la 1.ª frase). No muta la entrada."""
    out = [{"id": estructura["id"], "frases": [dict(f) for f in estructura["frases"]]}]
    for g in ganchos:
        frases = [dict(f) for f in estructura["frases"]]
        frases[0] = {**frases[0], "texto": g["texto"]}
        out.append({"id": f"{estructura['id']}+{g['id']}", "frases": frases})
    return out


def _nota(j: dict) -> int:
    for c in CRITERIOS:
        if not isinstance(j.get(c), int) or not 1 <= j[c] <= 5:
            raise ValueError(f"juicio.{c} debe ser un entero 1-5 (es {j.get(c)!r})")
    return sum(j[c] for c in CRITERIOS)


def elegir(cands: list[dict], juicio: dict) -> tuple[dict, list[dict]]:
    """Menos fallos de puerta primero; a igualdad, más juicio. Cada candidato: {id, fallos, ...}."""
    faltan = [c["id"] for c in cands if c["id"] not in juicio]
    if faltan:
        raise FaltaJuicio(faltan)
    ranking = sorted(cands, key=lambda c: (c["fallos"], -_nota(juicio[c["id"]])))
    return ranking[0], ranking


def evaluar(cands: list[dict], previos: list[str] | None = None) -> list[dict]:
    for c in cands:
        c["puertas"] = puertas(c["frases"], previos)
        c["fallos"] = sum(not p["ok"] for p in c["puertas"])
    return cands


def par_ciego(
    dir_: Path,
    plantilla: list[str],
    elegido: list[str],
    semilla: int | None = None,
    audio: bool = True,
) -> dict:
    """A/B sin etiquetas: A.txt/B.txt (+ A.mp3/B.mp3 con Kokoro). La correspondencia va en .clave.json."""
    dir_.mkdir(parents=True, exist_ok=True)
    lados = [("plantilla", plantilla), ("elegido", elegido)]
    random.Random(semilla).shuffle(lados)
    clave = {}
    for letra, (nombre, frases) in zip("AB", lados):
        clave[nombre] = letra
        (dir_ / f"{letra}.txt").write_text("\n".join(frases), encoding="utf-8")
        if audio:
            sys.path.insert(0, str(RAIZ / "tools"))
            import generar_voz as gv

            muestras, sr = gv.sintetizar_kokoro(" ".join(frases), gv.VOZ_KOKORO_DEFECTO)
            gv.guardar(muestras, sr, dir_ / f"{letra}.mp3")
    (dir_ / ".clave.json").write_text(json.dumps(clave), encoding="utf-8")
    return clave


def _fila(c: dict, juicio: dict) -> str:
    j = juicio.get(c["id"], {})
    fallan = ", ".join(p["id"] for p in c["puertas"] if not p["ok"]) or "—"
    nota = _nota(j) if j else "?"
    return (
        f"| `{c['id']}` | {c['fallos']} ({fallan}) | {nota}/15 | {j.get('nota', '')} |"
    )


def informe(etapas: list[tuple[str, list[dict]]], juicio: dict, ganador: dict) -> str:
    ls = [
        "# Guiones — crítico de guion (PROVISIONAL)",
        "",
        f"**Ganador:** `{ganador['id']}`",
        "",
        *[f"> {f['texto']}" for f in ganador["frases"]],
        "",
    ]
    for titulo, ranking in etapas:
        ls += [
            f"## {titulo}",
            "",
            "| candidato | fallos de puerta | juicio | por qué |",
            "|---|---|---|---|",
            *[_fila(c, juicio) for c in ranking],
            "",
        ]
    ls += [
        "## Puertas del ganador",
        "",
        *[
            f"- {'✓' if p['ok'] else '✗'} {p['id']}: {p['detalle']}"
            for p in ganador["puertas"]
        ],
        "",
        "## Descartadas (texto completo)",
        "",
    ]
    vistos = {ganador["id"]}
    for _, ranking in etapas:
        for c in ranking:
            if c["id"] in vistos:
                continue
            vistos.add(c["id"])
            ls += [
                f"### `{c['id']}`",
                "",
                *[f"> {f['texto']}" for f in c["frases"]],
                "",
            ]
    return "\n".join(ls)


def _pedir_juicio(e: FaltaJuicio, cands: list[dict]) -> NoReturn:
    print(f"Falta juicio (1-5: {', '.join(CRITERIOS)}) en guiones.json para:")
    for c in cands:
        if c["id"] in e.faltan:
            print(f"\n- {c['id']}  ({c['fallos']} fallos de puerta)")
            for p in c["puertas"]:
                print(f"    {'✓' if p['ok'] else '✗'} {p['id']}: {p['detalle']}")
    raise SystemExit(2)


def reglas(proy: Path, publicados: list[str] | None = None) -> str:
    """Everything the gates will check, with today's vetoes, BEFORE writing: the same gates failed
    in 3 of 4 sessions (11-nov) and each failed run is a full-context turn."""
    pub = refs_publicadas() if publicados is None else publicados
    vetados = cierres_previos(proy, pub)[:CIERRE_VENTANA]
    libres = [
        c
        for c in ("pregunta", "dicotomia", "imperativo", "dato", "afirmacion")
        if c not in vetados
    ]
    previos = []
    for ref in [r for r in pub if r != proy.name][:3]:
        try:
            adn = json.loads(
                (proy.parent / ref / "adn.json").read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            continue
        previos.append(
            f"{ref} ({adn.get('story_type')}, gancho {adn.get('hook_type')})"
        )
    p10 = int(HUECO_GIRO_MAX_S * PALABRAS_POR_S)
    cierres = f"{', '.join(vetados) or 'ninguno'}. Libres: {', '.join(libres)}"
    return f"""\
G-LARGO    {PALABRAS_MIN}-{PALABRAS_MAX} palabras en total.
G-GANCHO   1.ª oración: no empieza por número solo ni pronombre; nombre propio poco conocido con aposición ("Ronald Wayne, a ...").
G-TU       you/your (o "most people") antes de la palabra {TU_PALABRA_MAX}.
G-GIRO     un giro cada ≤{p10} palabras. Cuenta como giro: frase con cifra, o "giro": true (solo si de verdad gira).
G-CIFRAS   ≤{CIFRAS_MAX} cifras protagonistas dichas en todo el guion (los años cuentan).
G-BUCLE    la última frase comparte una palabra de contenido (≥4 letras, no cifra) con la 1.ª.
G-CIERRE   tipos vetados (últimos {CIERRE_VENTANA} vídeos): {cierres}.
G-COMODIN  prohibido: {", ".join(COMODINES)}.
G-RELLENO  prohibido: {", ".join(RELLENO)}.
Últimos publicados (no repetir estructura ni gancho): {"; ".join(previos) or "sin datos"}
guiones.json: estructuras[2-3]{{id,nombre,frases[{{id,texto,giro?}}]}}, ganchos[3-5]{{id,texto}}, juicio{{<id>: {{una_idea,bucle_abierto,giro: 1-5, nota}}}}.
Rellena ya el juicio de cada estructura; el de <estructura>+gN solo para la que gane (2 corridas en total)."""


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # consola de Windows en cp1252: ✓/✗/≈
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    proy = Path(sys.argv[1]).resolve()
    if "--reglas" in sys.argv:
        print(reglas(proy))
        return
    datos = json.loads((proy / "guiones.json").read_text(encoding="utf-8"))
    juicio = datos.get("juicio") or {}
    previos = cierres_previos(proy)

    ests = evaluar(
        [{"id": e["id"], "frases": e["frases"]} for e in datos["estructuras"]], previos
    )
    try:
        mejor_est, rank1 = elegir(ests, juicio)
    except FaltaJuicio as e:
        _pedir_juicio(e, ests)
    est = next(e for e in datos["estructuras"] if e["id"] == mejor_est["id"])
    variantes = evaluar(candidatos_gancho(est, datos.get("ganchos") or []), previos)
    try:
        ganador, rank2 = elegir(variantes, juicio)
    except FaltaJuicio as e:
        _pedir_juicio(e, variantes)

    (proy / "guiones.md").write_text(
        informe(
            [
                ("Etapa 1 — estructura", rank1),
                (f"Etapa 2 — gancho sobre `{est['id']}`", rank2),
            ],
            juicio,
            ganador,
        ),
        encoding="utf-8",
    )
    sb_ruta = proy / "storyboard.json"
    sb: dict = (
        json.loads(sb_ruta.read_text(encoding="utf-8"))
        if sb_ruta.exists()
        else {"ref": proy.name}
    )
    sb["guion"] = _frases_guion(ganador["frases"])
    sb_ruta.write_text(
        json.dumps(sb, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"✓ ganador {ganador['id']} ({ganador['fallos']} fallos de puerta) → {sb_ruta.name}, guiones.md"
    )

    if "--ciego" in sys.argv:
        base = json.loads((proy / "guion_plantilla.json").read_text(encoding="utf-8"))[
            "guion"
        ]
        par_ciego(
            proy / "renders" / "ciego",
            [f["texto"] for f in base],
            [f["texto"] for f in ganador["frases"]],
        )
        print(
            "✓ par ciego en renders/ciego/ (A/B .txt + .mp3; la clave en .clave.json, no la abras)"
        )


if __name__ == "__main__":
    main()
