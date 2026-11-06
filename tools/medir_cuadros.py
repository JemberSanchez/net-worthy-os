"""What is actually on the final MP4, frame by frame: black, frozen, flat frames, dark hook, and from the OCR
already done for L1 (no second pass): text boxes on top of each other and text cut by the frame edge.

    python tools/medir_cuadros.py <mp4>

Pure functions over numpy frames / OCR frames, so each is tested with a fixture. Thresholds live in
`motor/rubrica.json` -> C1 (PROVISIONAL), validated per video in docs/CERO-ERRORES.md.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np

_MOTOR = None
FPS = 5
TAM = (
    108,
    192,
)  # enough for brightness and flatness, and decoding a Short takes about 2 s


def leer_grises(mp4: Path, fps: int = FPS) -> np.ndarray:
    w, h = TAM
    p = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            str(mp4),
            "-vf",
            f"fps={fps},scale={w}:{h}",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "-",
        ],
        capture_output=True,
        check=True,
    )
    return np.frombuffer(p.stdout, np.uint8).reshape(-1, h, w)


def _tramos(malo: np.ndarray, fps: int, min_s: float) -> list[dict]:
    """Runs of True at least `min_s` long, in seconds."""
    out, i, n = [], 0, len(malo)
    while i < n:
        if not malo[i]:
            i += 1
            continue
        j = i
        while j < n and malo[j]:
            j += 1
        if (j - i) / fps >= min_s:
            out.append({"t": round(i / fps, 2), "t_fin": round(j / fps, 2)})
        i = j
    return out


def negros(fr: np.ndarray, u: dict, fps: int = FPS) -> list[dict]:
    """Frame with nothing on it: dark everywhere. A dark frame with text keeps a bright maximum."""
    malo = (fr.mean(axis=(1, 2)) < u["negro_luma"]) & (
        np.percentile(fr, 99.5, axis=(1, 2)) < 3 * u["negro_luma"]
    )
    return _tramos(malo, fps, u["negro_min_s"])


def congelados(fr: np.ndarray, u: dict, fps: int = FPS) -> list[dict]:
    """Literally the same frame: a stuck decode or capture. R1 measures "nothing interesting", this does not."""
    if len(fr) < 2:
        return []
    dif = np.abs(fr[1:].astype(np.int16) - fr[:-1]).mean(axis=(1, 2))
    return _tramos(np.r_[False, dif < u["congelado_dif"]], fps, u["congelado_min_s"])


def gancho(fr: np.ndarray, u: dict, fps: int = FPS) -> dict:
    """Brightness and contrast of the frames the viewer judges the video on."""
    g = fr[: int(u["gancho_s"] * fps)]
    return {
        "luma": round(float(g.mean()), 1),
        "contraste": round(float(g.std(axis=(1, 2)).mean()), 1),
    }


def planos(fr: np.ndarray, u: dict, fps: int = FPS) -> list[dict]:
    """Nothing to look at: one flat colour or a very faint background. `textos` can then clear it."""
    malo = fr.std(axis=(1, 2)) < u["plano_std"]
    return _tramos(malo, fps, u["plano_min_s"])


def banda_vacia(fr: np.ndarray, u: dict) -> dict | None:
    """Layout slipped: the same flat strip at the top or bottom for nearly the whole video. average-401k: 300 px of
    empty green on every frame (`tema` broke the root class) and every gate passed."""
    k = max(1, int(u["banda_alto"] * fr.shape[1]))
    for lado, tira in (("arriba", fr[:, :k, :]), ("abajo", fr[:, -k:, :])):
        pct = float((tira.std(axis=(1, 2)) < u["banda_std"]).mean())
        if pct >= u["banda_pct"]:
            return {"lado": lado, "pct": round(100 * pct)}
    return None


def sin_texto(f: dict, u: dict) -> bool:
    """No line a viewer reads as content: the brand and the disclaimer are smaller than `texto_alto_px`."""
    return not any(x["caja"][3] - x["caja"][1] >= u["texto_alto_px"] for x in f["lineas"])


def _area(c: list[float]) -> float:
    return max(0, c[2] - c[0]) * max(0, c[3] - c[1])


def solape(a: list[float], b: list[float]) -> float:
    """Intersection over the smaller box."""
    i = [max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])]
    return (
        _area(i) / min(_area(a), _area(b))
        if i[2] > i[0] and i[3] > i[1] and _area(a) and _area(b)
        else 0.0
    )


def glifos(c: list[int], u: dict) -> list[float]:
    """RapidOCR pads a big line's box by up to 20 % of its height (measured: "$103,202" 911-1228 for glyphs at
    about 936-1160), so stacked title + number overlap on paper and not on screen."""
    r = u["caja_recorte"] * (c[3] - c[1])
    return [c[0], c[1] + r, c[2], c[3] - r]


def colisiones(frames: list[dict], es_disenada, u: dict) -> list[dict]:
    """Two designed lines on top of each other in the same frame. Kept only if seen `colision_frames`+ times in
    a row at the OCR rate: during a cross-fade the outgoing and incoming text legitimately share a frame."""
    vistas: dict[tuple[str, str], list[float]] = {}
    for f in frames:
        lin = [
            x
            for x in f["lineas"]
            if len(x["texto"]) >= 3 and es_disenada(x["texto"], f["t"])
        ]
        for i, a in enumerate(lin):
            for b in lin[i + 1 :]:
                if (
                    solape(glifos(a["caja"], u), glifos(b["caja"], u))
                    >= u["colision_solape"]
                ):
                    par = tuple(sorted((a["texto"], b["texto"])))
                    vistas.setdefault(par, []).append(f["t"])
    return [
        {"t": ts[0], "t_fin": ts[-1], "a": par[0], "b": par[1]}
        for par, ts in vistas.items()
        if len(ts) >= u["colision_frames"]
    ]


def subtitulo_sobre_documento(frames: list[dict], es_disenada, u: dict) -> list[dict]:
    """Inside a `prueba`: a designed line (the caption) on top of a line that is not designed (the document)."""
    vistas: dict[tuple[str, str], list[float]] = {}
    for f in frames:
        for a in f["lineas"]:
            if not es_disenada(a["texto"], f["t"]):
                continue
            for b in f["lineas"]:
                if (
                    len(b["texto"]) >= 3
                    and not es_disenada(b["texto"], f["t"])
                    and solape(glifos(a["caja"], u), glifos(b["caja"], u))
                    >= u["colision_solape"]
                ):
                    vistas.setdefault((a["texto"], b["texto"]), []).append(f["t"])
    return [
        {"t": ts[0], "t_fin": ts[-1], "a": par[0], "b": par[1]}
        for par, ts in vistas.items()
        if len(ts) >= u["colision_frames"]
    ]


def cortados(frames: list[dict], es_disenada, u: dict) -> list[dict]:
    """Designed text against the frame edge, seen in `colision_frames`+ frames (a slide-in crosses the edge)."""
    vistas: dict[str, list[float]] = {}
    for f in frames:
        m = u["borde_margen"] * f["ancho"]
        for x in f["lineas"]:
            c = x["caja"]
            if (c[0] <= m or c[2] >= f["ancho"] - m) and es_disenada(
                x["texto"], f["t"]
            ):
                vistas.setdefault(x["texto"], []).append(f["t"])
    return [
        {"t": ts[0], "t_fin": ts[-1], "texto": k}
        for k, ts in vistas.items()
        if len(ts) >= u["colision_frames"]
    ]


def ocr_imagen(ruta: Path) -> dict:
    """OCR of one still, in the same shape as medir_texto.ocr_frames."""
    import logging

    import cv2
    import medir_texto
    from rapidocr import RapidOCR

    logging.getLogger("RapidOCR").setLevel(logging.ERROR)
    global _MOTOR  # loading the model costs seconds per slide
    _MOTOR = _MOTOR or RapidOCR(params={"Global.log_level": "error", "Det.limit_type": "max", "Det.limit_side_len": 1920})
    motor = _MOTOR
    bgr = cv2.imread(str(ruta))
    h, w = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    res = motor(rgb)
    lineas = []
    for caja, txt, conf in zip(res.boxes, res.txts, res.scores) if res.boxes is not None else []:
        xs, ys = [p[0] for p in caja], [p[1] for p in caja]
        c = [round(min(xs)), round(min(ys)), round(max(xs)), round(max(ys))]
        lineas.append({"texto": txt, "conf": round(float(conf), 3), "caja": c, "contraste": medir_texto.contraste_caja(rgb, c)})
    return {"ancho": w, "alto": h, "lineas": lineas}


def main() -> int:
    mp4 = Path(sys.argv[1])
    u = json.loads(
        (Path(__file__).parents[1] / "video-v2" / "motor" / "rubrica.json").read_text(
            encoding="utf-8"
        )
    )["criterios"]["C1"]
    fr = leer_grises(mp4)
    r = {
        "negros": negros(fr, u),
        "congelados": congelados(fr, u),
        "gancho": gancho(fr, u),
        "planos": planos(fr, u),
        "banda": banda_vacia(fr, u),
    }
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 1 if r["negros"] or r["congelados"] or r["banda"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
