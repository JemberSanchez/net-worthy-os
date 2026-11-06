"""Las métricas de docs/mejora/auditoria.md sobre un MP4 + su PLAN (index.html), reproducibles.

    python tools/medir_aspecto.py video-v2/<ref> [--mp4 x.mp4] [--json] [--sin-cortes]

Píxel (MP4): luma, saturación, entropía de color, % verde-amarillo, % muy oscuros, esquinas/centro,
cortes por 10 s, cambios de composición y composiciones distintas (dHash), tramo quieto.
Plan (index.html): % de imagen sin texto grande, % de imagen limpia (además sin subtítulo), posiciones
de texto, fuentes/escena, fuente más repetida, pruebas, tipos de escena, CV de planos, % de aviso.

Caso conocido: tests/test_medir_aspecto.py (sintético) y la tabla de la auditoría. Luma y % muy oscuros
reproducen la tabla (±2); la auditoría no guardó su definición exacta de verde-amarillo, entropía y
esquinas/centro: estas se ajustaron a fed-vs-card, binance-heist y aws-profit (error en el comentario junto a
`OBJETIVOS`). Compara siempre con esta misma herramienta, no con la tabla original.

Solo mide; sale con 0 siempre. Los objetivos son PROVISIONALES (auditoría: "umbrales a calibrar").
"""

from __future__ import annotations

import itertools
import json
import re
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import medir_parecido
import medir_ritmo

ANCHO, ALTO = 270, 480
HAMMING_CAMBIO = 8  # bits of 64 between frames 0.5 s apart: a new composition, not grain or a pan
HAMMING_DISTINTA = 16  # bits of 64 to any earlier frame: a composition not seen before
# Calibration against the audit table (fed, binance, aws): verde_amarillo error up to 9 points,
# entropia up to 0.3 bits, esquinas_centro up to 0.07, cambios up to 1, composiciones up to 3.
OBJETIVOS = {
    "verde_amarillo_pct": ("<", 45),
    "muy_oscuros_pct": ("<", 20),
    "esquinas_centro": (">", 0.6),
    "imagen_limpia_pct": (">=", 20),
    "posiciones": (">=", 3),
    "fuentes_por_escena": (">", 0.8),
    "pruebas": (">=", 1),
    "tipos_escena": (">=", 5),
    "cortes_10s": (">", 2.5),
    "entropia_color": (">", 4),
}


def frames_rgb(mp4: Path, fps: float = 2.0) -> np.ndarray:
    raw = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-i", str(mp4),
            "-vf", f"fps={fps},scale={ANCHO}:{ALTO},format=rgb24",
            "-f", "rawvideo", "-",
        ],
        capture_output=True,
        check=True,
    ).stdout  # fmt: skip
    return np.frombuffer(raw, np.uint8).reshape(-1, ALTO, ANCHO, 3)


def medir_pixeles(f: np.ndarray) -> dict:
    """Pure: frames (n, h, w, 3) RGB -> colour metrics."""
    hsv = np.stack([cv2.cvtColor(x, cv2.COLOR_RGB2HSV) for x in f])
    h, s = hsv[..., 0], hsv[..., 1]
    y = f[..., 0] * 0.299 + f[..., 1] * 0.587 + f[..., 2] * 0.114
    sat = s > 40
    vy = ((h >= 25) & (h <= 90) & sat).sum() / max(1, sat.sum())
    hist = np.histogram2d(
        h.ravel(), s.ravel(), bins=(18, 4), range=((0, 180), (0, 256))
    )[0].ravel()
    p = hist[hist > 0] / hist.sum()
    alto, ancho = f.shape[1:3]
    a, b = int(alto * 0.2), int(ancho * 0.2)
    esquinas = np.concatenate(
        [
            y[:, :a, :b].ravel(),
            y[:, :a, -b:].ravel(),
            y[:, -a:, :b].ravel(),
            y[:, -a:, -b:].ravel(),
        ]
    ).mean()
    ca, cb = alto // 6, ancho // 6
    centro = y[
        :, alto // 2 - ca : alto // 2 + ca, ancho // 2 - cb : ancho // 2 + cb
    ].mean()
    return {
        "luma": round(float(y.mean()), 1),
        "saturacion": round(float(s.mean()), 1),
        "entropia_color": round(float(-(p * np.log2(p)).sum()), 2),
        "verde_amarillo_pct": round(float(100 * vy), 1),
        "muy_oscuros_pct": round(float(100 * (y < 30).mean()), 1),
        "esquinas_centro": round(float(esquinas / max(centro, 1e-6)), 2),
    }


def composiciones(f: np.ndarray, fps: float = 2.0) -> dict:
    """Pure: composition changes per 10 s and distinct compositions (greedy clustering by dHash)."""
    gris = [cv2.cvtColor(x, cv2.COLOR_RGB2GRAY) for x in f]
    hs = [medir_parecido.dhash(g) for g in gris]
    cambios = sum(
        (a ^ b).bit_count() > HAMMING_CAMBIO for a, b in itertools.pairwise(hs)
    )
    distintas: list[int] = []
    for x in hs:
        if all((x ^ d).bit_count() > HAMMING_DISTINTA for d in distintas):
            distintas.append(x)
    dur = max(len(hs) / fps, 1e-6)
    return {
        "cambios_composicion_10s": round(10 * cambios / dur, 1),
        "composiciones": len(distintas),
    }


def cortes_10s(mp4: Path, dur: float) -> float:
    from scenedetect import ContentDetector, detect

    return round(
        10 * max(0, len(detect(str(mp4), ContentDetector(threshold=27))) - 1) / dur, 1
    )


def leer_plan(index_html: Path) -> dict | None:
    """The PLAN the render used, from index.html."""
    if not index_html.exists():
        return None
    m = re.search(
        r"window\.PLAN = (\{.*?\});</script>",
        index_html.read_text(encoding="utf-8"),
        re.DOTALL,
    )
    return json.loads(m.group(1)) if m else None


def _union(v: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[list[float]] = []
    for a, b in sorted(x for x in v if x[1] > x[0]):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return [(a, b) for a, b in out]


def _dur(v) -> float:
    return sum(b - a for a, b in v)


def _resta(
    a: list[tuple[float, float]], b: list[tuple[float, float]]
) -> list[tuple[float, float]]:
    out = []
    for x0, x1 in a:
        cur = x0
        for y0, y1 in _union(b):
            if y1 <= cur or y0 >= x1:
                continue
            if y0 > cur:
                out.append((cur, y0))
            cur = max(cur, y1)
        if cur < x1:
            out.append((cur, x1))
    return out


def _texto_grande(s: dict) -> list[tuple[float, float]]:
    out = [
        (r.get("en", s["t0"]), r.get("hasta", s["t1"])) for r in s.get("rotulos") or []
    ]
    if s.get("titulo"):
        out.append((s["titulo"].get("en", s["t0"]), s["t1"]))
    return [(max(a, s["t0"]), min(b, s["t1"])) for a, b in out]


def medir_plan(p: dict) -> dict:
    """Pure: PLAN -> composition metrics."""
    esc, D = p["escenas"], p["D"]
    pruebas = [(x["t0"], x["t1"]) for x in p.get("pruebas") or []]
    fotos = [s for s in esc if s["tipo"] == "foto"]
    sin_texto: list[tuple[float, float]] = []
    limpias: list[tuple[float, float]] = []
    for s in fotos:
        libre = _resta([(s["t0"], s["t1"])], _texto_grande(s) + pruebas)
        sin_texto += libre
        if s.get("limpio"):
            limpias += libre
    posiciones = []
    for s in esc:
        if s["tipo"] in ("foto", "grafica"):
            if s.get("rotulos") or s.get("titulo"):
                posiciones.append(
                    s.get("pos") or ("centro" if s.get("titulo") else "sup")
                )
        else:
            posiciones.append(s.get("posicion") or "centro")
    fuentes: dict[str, int] = {}
    for f in p.get("fotos") or []:
        n = f.get("clip") or f.get("img")
        if n and f.get("capa") != "fondo":
            fuentes[n] = fuentes.get(n, 0) + 1
    for f in (
        p.get("fotos") or []
    ):  # background layers count as uses too, once per scene
        n = f.get("clip") or f.get("img")
        if n and f.get("capa") == "fondo":
            fuentes[n] = fuentes.get(n, 0) + 1
    for x in p.get("pruebas") or []:
        fuentes[x.get("img")] = fuentes.get(x.get("img"), 0) + 1
    t0s = sorted(s["t0"] for s in esc) + [D]
    dur = np.diff(t0s)
    aviso = _union(
        [tuple(v) for v in p["aviso"].get("ventanas") or []]
        + ([(p["aviso"]["final"], D)] if p["aviso"].get("final") is not None else [])
    )
    n_esc = len(esc)  # the audit counted PLAN scenes; proofs are overlays, their documents do count as sources
    return {
        "duracion": round(D, 1),
        "imagen_sin_texto_grande_pct": round(100 * _dur(_union(sin_texto)) / D, 1),
        "imagen_limpia_pct": round(100 * _dur(_union(limpias)) / D, 1),
        "posiciones": len(set(posiciones)),
        "fuentes": len(fuentes),
        "escenas": n_esc,
        "fuentes_por_escena": round(len(fuentes) / max(1, n_esc), 2),
        "fuente_mas_repetida": max(fuentes.values(), default=0),
        "pruebas": len(pruebas),
        "tipos_escena": len(
            {s["tipo"] for s in esc} | ({"prueba"} if pruebas else set())
        ),
        "cv_planos": round(float(dur.std() / dur.mean()), 2) if len(dur) > 1 else 0.0,
        "aviso_pct": round(100 * _dur(aviso) / D, 1),
    }


def medir(proy: Path, mp4: Path | None = None, con_cortes: bool = True) -> dict:
    proy = Path(proy)
    mp4 = Path(mp4) if mp4 else medir_parecido.mp4_final(proy)
    if not mp4 or not Path(mp4).exists():
        raise SystemExit(f"no hay MP4 final en {proy}")
    f = frames_rgb(mp4)
    out = {"mp4": str(mp4), **medir_pixeles(f), **composiciones(f)}
    quieto = medir_ritmo.tramo_quieto(medir_ritmo.leer_frames(str(mp4)))
    out["tramo_quieto_s"] = quieto["max_s"]
    p = leer_plan(proy / "index.html")
    if p:
        out.update(medir_plan(p))
    if con_cortes:
        out["cortes_10s"] = cortes_10s(mp4, len(f) / 2.0)
    return out


def objetivos(m: dict) -> list[str]:
    """The audit targets this measurement misses."""
    op = {"<": float.__lt__, ">": float.__gt__, ">=": float.__ge__}
    return [
        f"{k} = {m[k]} (objetivo {o} {v})"
        for k, (o, v) in OBJETIVOS.items()
        if k in m and not op[o](float(m[k]), float(v))
    ]


def main() -> int:
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    m = medir(
        Path(a[0]),
        Path(a[a.index("--mp4") + 1]) if "--mp4" in a else None,
        "--sin-cortes" not in a,
    )
    if "--json" in a:
        print(json.dumps(m, ensure_ascii=False))
        return 0
    for k, v in m.items():
        print(f"{k:32} {v}")
    fallos = objetivos(m)
    print("✓ objetivos de la auditoría" if not fallos else "⚠ " + " · ".join(fallos))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
