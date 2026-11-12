"""Mide cuánto se PARECE un Short a los ya hechos de la misma marca (riesgo de "contenido repetitivo").

    python tools/medir_parecido.py video-v2/<ref> [--corpus video-v2] [--json]

Por qué existe
---------------
YouTube desmonetiza/penaliza el contenido "inauténtico o repetitivo" (plantillas producidas a
escala, detección por canal). Un motor que genera Shorts desde un catálogo de escenas tiende a
clonarse a sí mismo. Este medidor no decide qué es "demasiado"; da cuatro números comparables
contra CADA vídeo previo de la misma marca (`storyboard.marca`, ausente = la misma):

- visual:     fracción de segundos cuyo fotograma tiene un gemelo (dHash 64 bits, Hamming <= 10)
              en el otro vídeo. Necesita los MP4 (renders/*-final.mp4); si falta, no se calcula.
- guion:      Jaccard de trigramas de palabras del guion (frases copiadas, no tema).
- estructura: parecido de la SECUENCIA de tipos de escena (difflib) = misma plantilla.
- recursos:   Jaccard de recursos con licencia (pista de música, clips, imágenes de Commons/Pexels).
- edicion:    de lo que usa este vídeo (transiciones, cámara, punch, entrada de texto, efectos, risers,
              música), fracción ya usada en los últimos N (`--tabla video-v2` = pares consecutivos).

Validación del instrumento: tests/test_medir_parecido.py (el mismo vídeo contra sí mismo y contra
una recodificación ~1; contra ruido ~0) y caso real medido al crearlo (#7 vs #8, ver docs/RUBRICA.md).
"""

from __future__ import annotations

import argparse
import difflib
import itertools
import json
import re
import sys
from pathlib import Path

HAMMING_MAX = 10
STD_MIN = (
    6.0  # fotogramas casi lisos (negro, fundidos) no cuentan: su hash es degenerado
)


def dhash(gris) -> int:
    """dHash de 64 bits de una imagen en gris (array 2D): 9x8, gradiente horizontal."""
    import cv2

    p = cv2.resize(gris, (9, 8), interpolation=cv2.INTER_AREA)
    bits = (p[:, 1:] > p[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hashes_video(mp4: Path, fps: float = 1.0) -> list[int]:
    """Un dHash por segundo, cacheado en <mp4>.hash.json. Fotogramas lisos -> se omiten."""
    cache = mp4.with_suffix(".hash.json")
    clave = {"fps": fps, "tam": mp4.stat().st_size, "mtime": int(mp4.stat().st_mtime)}
    if cache.exists():
        d = json.loads(cache.read_text(encoding="utf-8"))
        if d.get("clave") == clave:
            return d["hashes"]
    import cv2

    cap = cv2.VideoCapture(str(mp4))
    paso = max(1, round((cap.get(cv2.CAP_PROP_FPS) or 30.0) / fps))
    out, i = [], 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i % paso == 0:
            g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
            if float(g.std()) >= STD_MIN:
                out.append(dhash(g))
        i += 1
    cap.release()
    cache.write_text(json.dumps({"clave": clave, "hashes": out}), encoding="utf-8")
    return out


def parecido_visual(a: list[int], b: list[int], hmax: int = HAMMING_MAX) -> float:
    """Fracción de hashes de `a` con un gemelo en `b`. Función pura."""
    if not a or not b:
        return 0.0
    return round(
        sum(1 for x in a if min((x ^ y).bit_count() for y in b) <= hmax) / len(a), 3
    )


def trigramas(texto: str) -> set[tuple[str, ...]]:
    w = re.findall(r"[a-z0-9$%']+", texto.lower())
    return {tuple(w[i : i + 3]) for i in range(len(w) - 2)}


def jaccard(a: set, b: set) -> float:
    return round(len(a & b) / len(a | b), 3) if a | b else 0.0


def recursos(sb: dict) -> set[str]:
    """Identificadores de recursos externos (no claves locales: dos vídeos pueden llamar 'reloj' a
    clips distintos)."""
    out = set()
    pista = (sb.get("musica") or {}).get("pista") or {}
    if pista.get("commons"):
        out.add("musica:" + pista["commons"])
    for c in (sb.get("clips") or {}).values():
        out.add(f"clip:{c.get('pexels') or c.get('commons')}")
    for i in (sb.get("imagenes") or {}).values():
        if i.get("commons"):
            out.add("img:" + i["commons"])
    return out


def comparar(
    sa: dict, sb_: dict, ha: list[int] | None = None, hb: list[int] | None = None
) -> dict:
    """Función pura sobre dos storyboards (+ hashes opcionales)."""
    ga = " ".join(g["texto"] for g in sa.get("guion") or [])
    gb = " ".join(g["texto"] for g in sb_.get("guion") or [])
    ta = [e["tipo"] for e in sa.get("escenas") or []]
    tb = [e["tipo"] for e in sb_.get("escenas") or []]
    ra, rb = recursos(sa), recursos(sb_)
    return {
        "visual": parecido_visual(ha, hb) if ha and hb else None,
        "guion": jaccard(trigramas(ga), trigramas(gb)),
        "estructura": round(difflib.SequenceMatcher(None, ta, tb).ratio(), 3),
        "recursos": jaccard(ra, rb),
        "recursos_comunes": sorted(ra & rb),
    }


def mp4_final(proy: Path) -> Path | None:
    r = proy / "renders"
    cands = (
        sorted(r.glob("*-final.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if r.exists()
        else []
    )
    return cands[0] if cands else None


def corpus(proy: Path, raiz: Path) -> list[Path]:
    """Otros proyectos v2 de la MISMA marca (storyboard.marca; ausente = misma)."""
    marca = json.loads((proy / "storyboard.json").read_text(encoding="utf-8")).get(
        "marca"
    )
    out = []
    for p in sorted(raiz.iterdir()):
        f = p / "storyboard.json"
        if p.resolve() == proy.resolve() or not f.exists():
            continue
        if json.loads(f.read_text(encoding="utf-8")).get("marca") == marca:
            out.append(p)
    return out


def medir(proy: Path, raiz: Path | None = None, mp4: Path | None = None) -> dict:
    raiz = raiz or proy.parent
    sa = json.loads((proy / "storyboard.json").read_text(encoding="utf-8"))
    m = mp4 or mp4_final(proy)
    ha = hashes_video(m) if m else None
    filas = []
    for otro in corpus(proy, raiz):
        so = json.loads((otro / "storyboard.json").read_text(encoding="utf-8"))
        mo = mp4_final(otro)
        filas.append(
            {
                "ref": otro.name,
                **comparar(sa, so, ha, hashes_video(mo) if (mo and ha) else None),
            }
        )

    def peor(k):
        v = [f for f in filas if f[k] is not None]
        return max(v, key=lambda f: f[k]) if v else None

    return {
        "comparados": len(filas),
        "filas": filas,
        "max": {
            k: ({"valor": p[k], "ref": p["ref"]} if (p := peor(k)) else None)
            for k in ("visual", "guion", "estructura", "recursos")
        },
        "edicion": _edicion_registrada(sa, proy, raiz),
    }


def _edicion_registrada(sa: dict, proy: Path, raiz: Path) -> dict | None:
    """Repetition of an already built video against the ones before it. None = legacy or not built."""
    f = raiz / "usado.json"
    if not f.exists():
        return None
    reg = json.loads(f.read_text(encoding="utf-8"))
    ref = sa.get("ref") or proy.name
    fila = next((v for v in reg["videos"] if v["ref"] == ref), None)
    if not fila or fila.get("legacy"):
        return None
    return repeticion_edicion(
        fila["firma"], previas_registro(reg, ref, sa.get("marca"))
    )


def previas_registro(reg: dict, ref: str, marca) -> list[dict]:
    """Rows of the videos BEFORE `ref` of the same brand, newest first. Registry order = creation."""
    out = []
    for v in reg["videos"]:
        if v["ref"] == ref:
            break
        if v.get("marca") == marca:
            out.append(v)
    return out[::-1]


VENTANA_FRASES = 10  # frases y rótulos: no repetir ninguno en los últimos 10 vídeos
VENTANA_SELLOS = (
    3  # final/apertura/música: pocos tipos posibles, por eso una ventana más corta
)
_NUMEROS = {
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
    "point",
    "percent",
    "dollars",
}


def _cuatrigramas(sb_: dict) -> set[str]:
    p = re.findall(
        r"[a-z0-9$%'.-]*[a-z0-9$%]",
        " ".join(g["texto"] for g in sb_.get("guion") or []).lower(),
    )
    # share a data point ("three point eight percent") is legitimate; only sentence formulas count
    return {
        " ".join(q)
        for q in zip(p, p[1:], p[2:], p[3:])
        if not any(w in _NUMEROS or any(c.isdigit() for c in w) for w in q)
    }


def _rotulos(o) -> set[str]:
    """Textos de pantalla de 2+ palabras, normalizados, sin cifras."""
    out: set[str] = set()
    if isinstance(o, dict):
        for k, v in o.items():
            if isinstance(v, str) and k in ("texto", "sub", "sup", "tag", "linea"):
                t = " ".join(v.lower().split())
                if len(t.split()) >= 2 and not any(c.isdigit() for c in t):
                    out.add(t)
            else:
                out |= _rotulos(v)
    elif isinstance(o, list):
        for x in o:
            out |= _rotulos(x)
    return out


def _sello_final(sb_: dict) -> str:
    e = (sb_.get("escenas") or [{}])[-1]
    return e.get("tipo", "?") + ("+botones" if e.get("botones") else "")


def _autor_musica(sb_: dict) -> str | None:
    f = ((sb_.get("musica") or {}).get("pista") or {}).get("commons") or ""
    if (
        "macleod" in f.lower()
    ):  # Commons names him two ways: "Kevin MacLeod - X" / "X (MacLeod, Kevin)"
        return "kevin macleod"
    f = f.removeprefix("File:")
    return f.split(" - ")[0].strip().lower() if " - " in f else (f.lower() or None)


def repeticiones(sa: dict, previos: list[dict]) -> list[str]:
    """Motivos por los que `sa` repite a `previos` (el más reciente primero). Vacío = pasa."""
    motivos = []
    for pv in previos[:VENTANA_FRASES]:
        comun = sorted(_cuatrigramas(sa) & _cuatrigramas(pv))
        if comun:
            motivos.append(
                f"guion repite «{comun[0]}» ({len(comun)} frases de 4 palabras)"
            )
        comun = sorted(_rotulos(sa.get("escenas")) & _rotulos(pv.get("escenas")))
        if comun:
            motivos.append(f"pantalla repite «{comun[0]}»")
    for pv in previos[:VENTANA_SELLOS]:
        if _sello_final(sa) == _sello_final(pv):
            motivos.append(f"mismo final: {_sello_final(sa)}")
        if (sa.get("escenas") or [{}])[0].get("tipo") == (pv.get("escenas") or [{}])[
            0
        ].get("tipo") and sa.get("tema") == pv.get(
            "tema"
        ):  # a new visual theme is not a repeat
            motivos.append(
                f"misma apertura: {(sa.get('escenas') or [{}])[0].get('tipo')}"
            )
        if _autor_musica(sa) and _autor_musica(sa) == _autor_musica(pv):
            motivos.append(f"misma música (autor): {_autor_musica(sa)}")
    return list(dict.fromkeys(motivos))


# Sub-meter "repetición de edición": fraction of what this video uses (transitions, camera moves,
# effects...) that one of the last N videos of the brand already used. Limits in rubrica.json
# P1.repeticion, PROVISIONAL. Signatures come from video-v2/motor/edicion.py, stored in usado.json.
DIMS_EDICION = (
    "transiciones",
    "camara",
    "punch",
    "texto",
    "efectos",
    "riser",
    "musica",
)
RUBRICA = Path(__file__).resolve().parents[1] / "video-v2" / "motor" / "rubrica.json"


def limites_repeticion() -> dict:
    return json.loads(RUBRICA.read_text(encoding="utf-8"))["criterios"]["P1"][
        "repeticion"
    ]


def fraccion_compartida(a, b) -> float:
    """|A ∩ B| / |A|: of what A uses, how much B already used. Nothing used = nothing repeated."""
    a = set(a)
    return round(len(a & set(b)) / len(a), 3) if a else 0.0


def repeticion_edicion(
    firma: dict, previas: list[dict], lims: dict | None = None
) -> dict:
    """`previas`: registry rows ({"ref", "firma"}), newest first. Compared with their union in the window."""
    lims = lims or limites_repeticion()
    ventana = previas[: int(lims["ventana"])]
    dims, motivos = {}, []
    for d in DIMS_EDICION:
        union = {x for v in ventana for x in v["firma"].get(d) or []}
        val = fraccion_compartida(firma.get(d) or [], union)
        comunes = sorted(set(firma.get(d) or []) & union)
        dims[d] = {"valor": val, "limite": lims[f"{d}_max"], "comunes": comunes}
        if val > lims[f"{d}_max"]:
            motivos.append(
                f"{d}: {val} > {lims[f'{d}_max']} con los últimos {len(ventana)} vídeos ({', '.join(comunes[:4])})"
            )
    return {"dims": dims, "motivos": motivos, "ventana": len(ventana)}


def tabla_repeticion(raiz: Path) -> list[dict]:
    """Consecutive pairs of the registry: fraction shared per dimension (baseline and after)."""
    vids = json.loads((raiz / "usado.json").read_text(encoding="utf-8"))["videos"]
    return [
        {
            "par": f"{a['ref']} -> {b['ref']}",
            **{
                d: fraccion_compartida(b["firma"].get(d) or [], a["firma"].get(d) or [])
                for d in DIMS_EDICION
            },
        }
        for a, b in itertools.pairwise(vids)
    ]


def parecido_estatico(sa: dict, otros: list[Path], previos: list[dict]) -> list[str]:
    """The critic's P1 on the storyboard-only keys, same maxima: caught before voice and render, not after.
    `visual` needs the MP4 and stays with the critic."""
    p1 = json.loads(RUBRICA.read_text(encoding="utf-8"))["criterios"]["P1"]
    motivos = []
    filas = [(comparar(sa, so), p.name) for p, so in zip(otros, previos, strict=True)]
    for k in ("guion", "estructura", "recursos"):
        c, ref = max(filas, key=lambda f: f[0][k], default=(None, None))
        if c and c[k] > p1[f"{k}_max"]:
            extra = (
                f": {', '.join(c['recursos_comunes'][:4])}" if k == "recursos" else ""
            )
            motivos.append(f"parecido {k} {c[k]} con {ref} (> {p1[f'{k}_max']}){extra}")
    return motivos


def puerta_repeticion(proy: Path) -> tuple[bool, str]:
    sa = json.loads((proy / "storyboard.json").read_text(encoding="utf-8"))
    if not sa.get("formato"):
        if mp4_final(
            proy
        ):  # made before this gate existed; re-rendering it must keep working
            return True, "exento: vídeo anterior a la puerta (sin `formato`)"
        return (
            False,
            "falta `formato` en el storyboard (p. ej. grafica-viva, expediente, reconstruccion, archivo, la-cuenta)",
        )
    # shortcut: order by storyboard mtime, a fresh clone scrambles it; add a date to the storyboard if that bites
    otros = sorted(
        corpus(proy, proy.parent),
        key=lambda p: (p / "storyboard.json").stat().st_mtime,
        reverse=True,
    )
    previos = [
        json.loads((p / "storyboard.json").read_text(encoding="utf-8")) for p in otros
    ]
    motivos = repeticiones(sa, previos) + parecido_estatico(sa, otros, previos)
    return (
        not motivos,
        " · ".join(motivos) or f"sin repetición contra {len(otros)} vídeos",
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("proyecto", nargs="?")
    ap.add_argument("--corpus")
    ap.add_argument("--mp4")
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--tabla", help="carpeta con usado.json: repetición entre vídeos consecutivos"
    )
    a = ap.parse_args()
    if a.tabla:
        print("par | " + " | ".join(DIMS_EDICION))
        for t in tabla_repeticion(Path(a.tabla)):
            print(t["par"] + " | " + " | ".join(str(t[d]) for d in DIMS_EDICION))
        return 0
    if not a.proyecto:
        ap.error("falta el proyecto")
    r = medir(
        Path(a.proyecto),
        Path(a.corpus) if a.corpus else None,
        Path(a.mp4) if a.mp4 else None,
    )
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    print(f"Comparado con {r['comparados']} vídeo(s) de la misma marca")
    for f in r["filas"]:
        print(
            f"  {f['ref']:<22} visual {f['visual']} · guion {f['guion']} · estructura {f['estructura']} · "
            f"recursos {f['recursos']} {f['recursos_comunes'][:3]}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
