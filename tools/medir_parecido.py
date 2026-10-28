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

Validación del instrumento: tests/test_medir_parecido.py (el mismo vídeo contra sí mismo y contra
una recodificación ~1; contra ruido ~0) y caso real medido al crearlo (#7 vs #8, ver docs/RUBRICA.md).
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

HAMMING_MAX = 10
STD_MIN = 6.0           # fotogramas casi lisos (negro, fundidos) no cuentan: su hash es degenerado


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
    return round(sum(1 for x in a if min(bin(x ^ y).count("1") for y in b) <= hmax) / len(a), 3)


def trigramas(texto: str) -> set[tuple[str, ...]]:
    w = re.findall(r"[a-z0-9$%']+", texto.lower())
    return {tuple(w[i:i + 3]) for i in range(len(w) - 2)}


def jaccard(a: set, b: set) -> float:
    return round(len(a & b) / len(a | b), 3) if a | b else 0.0


def recursos(sb: dict) -> set[str]:
    """Identificadores de recursos externos (no claves locales: dos vídeos pueden llamar 'reloj' a
    clips distintos)."""
    out = set()
    pista = ((sb.get("musica") or {}).get("pista") or {})
    if pista.get("commons"):
        out.add("musica:" + pista["commons"])
    for c in (sb.get("clips") or {}).values():
        out.add(f'clip:{c.get("pexels") or c.get("commons")}')
    for i in (sb.get("imagenes") or {}).values():
        if i.get("commons"):
            out.add("img:" + i["commons"])
    return out


def comparar(sa: dict, sb_: dict, ha: list[int] | None = None, hb: list[int] | None = None) -> dict:
    """Función pura sobre dos storyboards (+ hashes opcionales)."""
    ga = " ".join(g["texto"] for g in sa.get("guion") or [])
    gb = " ".join(g["texto"] for g in sb_.get("guion") or [])
    ta = [e["tipo"] for e in sa.get("escenas") or []]
    tb = [e["tipo"] for e in sb_.get("escenas") or []]
    ra, rb = recursos(sa), recursos(sb_)
    return {"visual": parecido_visual(ha, hb) if ha and hb else None,
            "guion": jaccard(trigramas(ga), trigramas(gb)),
            "estructura": round(difflib.SequenceMatcher(None, ta, tb).ratio(), 3),
            "recursos": jaccard(ra, rb),
            "recursos_comunes": sorted(ra & rb)}


def mp4_final(proy: Path) -> Path | None:
    r = proy / "renders"
    cands = sorted(r.glob("*-final.mp4"), key=lambda p: p.stat().st_mtime, reverse=True) if r.exists() else []
    return cands[0] if cands else None


def corpus(proy: Path, raiz: Path) -> list[Path]:
    """Otros proyectos v2 de la MISMA marca (storyboard.marca; ausente = misma)."""
    marca = json.loads((proy / "storyboard.json").read_text(encoding="utf-8")).get("marca")
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
        filas.append({"ref": otro.name, **comparar(sa, so, ha, hashes_video(mo) if (mo and ha) else None)})
    def peor(k):
        v = [f for f in filas if f[k] is not None]
        return max(v, key=lambda f: f[k]) if v else None
    return {"comparados": len(filas), "filas": filas,
            "max": {k: ({"valor": p[k], "ref": p["ref"]} if (p := peor(k)) else None)
                    for k in ("visual", "guion", "estructura", "recursos")}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("proyecto")
    ap.add_argument("--corpus")
    ap.add_argument("--mp4")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = medir(Path(a.proyecto), Path(a.corpus) if a.corpus else None, Path(a.mp4) if a.mp4 else None)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    print(f"Comparado con {r['comparados']} vídeo(s) de la misma marca")
    for f in r["filas"]:
        print(f"  {f['ref']:<22} visual {f['visual']} · guion {f['guion']} · estructura {f['estructura']} · "
              f"recursos {f['recursos']} {f['recursos_comunes'][:3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
