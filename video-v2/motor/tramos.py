"""Per-scene re-render (docs/PLAN-VELOCIDAD.md, "Render por escena"): after a patch, render only the
scenes whose page changed and splice them into the last good final MP4.

Measured on huang-exit-largo (23-nov, docs/ESTADO.md): one scene ~1m45-2m15 + splice 43 s, against
~16 min for the whole long-form. Conservative by design: anything it cannot place in time (CSS,
motor.js, a plan scalar) returns a reason and the caller renders the whole film. An audio change is
not placed in time: the caller re-mixes the whole track from a 1 fps render (24-nov: bit-identical to
the 30 fps mix on huang-resigns, 40 s against 128 s; ~4 min on the long-form against ~16).
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path

MARGEN = 1.0  # s around a change: a golpe's punch lasts 0.73 s, transitions 0.4 s (PLAN.edicion)
MAX_VENTANAS = 8  # each span pays ~60-70 s fixed: beyond this the whole render is close
MAX_FRAC = 0.5  # share of the film: above it, render it all
# PLAN keys only construir's audio reads (fin_voz is not one: motor.js times visuals with it)
AUDIO_PLAN = {"sonidos", "sfx_mezcla", "musica_volumen", "vol_motor", "voz_mix"}
_T = ("t0", "t1", "start", "end", "en", "t", "marca")
# lists whose entries are timeline events; any other changed list (subtitulos is a [C0, C1] range,
# oscuro belongs to the music) renders the whole film
LISTAS_T = {
    "escenas",
    "fotos",
    "words",
    "transiciones",
    "pruebas",
    "golpes",
    "cortes",
    "impactos",
}
_START = re.compile(r'data-start="([\d.]+)"(?:[^>]*?data-duration="([\d.]+)")?')
_PLAN = re.compile(
    r"(.*?window\.PLAN = )(\{.*\})(;.*)"
)  # construir: <script>window.PLAN = {...};</script>


def frame(t: float, fps: int) -> int:
    """HyperFrames' span frame (Math.round, half up), not Python's banker's round."""
    return math.floor(t * fps + 0.5)


def fps_de(html: str) -> int:
    m = re.search(r'id="root"[^>]*data-fps="(\d+)"', html)
    return int(m.group(1)) if m else 30


def _plan(html: str) -> tuple[dict, list[str]]:
    """(window.PLAN, the page's other lines; the PLAN's own line kept with a placeholder, so a change to
    its wrapper still counts)."""
    plan, resto = {}, []
    for linea in html.splitlines():
        s = linea.strip()
        if m := _PLAN.fullmatch(s):
            plan = json.loads(m.group(2))
            s = m.group(1) + "{PLAN}" + m.group(3)
        resto.append(s)
    return plan, resto


def _intervalo_linea(linea: str) -> tuple[float, float] | None:
    """Time span of a one-line timed element (construir writes each on its own line); None when the
    line is untimed or not a whole element (the root opens on one line and closes far below)."""
    m = re.match(r"<(\w+)\b", linea)
    if not m or "data-start=" not in linea or not linea.endswith(f"</{m.group(1)}>"):
        return None
    ts = [(float(a), float(a) + float(d or 0)) for a, d in _START.findall(linea)]
    return (min(t[0] for t in ts), max(t[1] for t in ts)) if ts else None


def _intervalo_entrada(e) -> tuple[float, float] | None:
    if isinstance(e, bool):
        return None
    if isinstance(e, (int, float)):
        return (float(e), float(e))
    if not isinstance(e, dict):
        return None
    ts = [float(e[k]) for k in _T if isinstance(e.get(k), (int, float))]
    if isinstance(e.get("t"), (int, float)):
        t = float(e["t"])
        ts += [
            t + float(e.get("dur") or 0),
            t - float(e.get("dur_sale") or 0),
            t + float(e.get("dur_entra") or 0),
        ]
    return (min(ts), max(ts)) if ts else None


def _diferencia(a: list, b: list) -> list:
    ca, cb = Counter(a), Counter(b)
    return list((ca - cb).elements()) + list((cb - ca).elements())


def cambios(
    viejo: str, nuevo: str, assets_viejos: dict, assets_nuevos: dict
) -> tuple[list[tuple[float, float]] | None, str, bool]:
    """(time spans that changed between two built pages, "", whether the audio changed), or
    (None, why the whole film must render, False)."""
    pv, rv = _plan(viejo)
    pn, rn = _plan(nuevo)
    if not pv or not pn:
        return None, "página sin window.PLAN", False
    spans: list[tuple[float, float]] = []
    audio = False
    for linea in _diferencia(rv, rn):
        if "<audio" in linea:
            audio = True
            if linea.startswith("<audio"):  # the element alone: nothing to see
                continue
        iv = _intervalo_linea(linea)
        if iv is None:
            return None, f"cambio sin tiempo en la página: {linea[:60]!r}", False
        spans.append(iv)
    for k in sorted(set(pv) | set(pn)):
        if pv.get(k) == pn.get(k):
            continue
        if k in AUDIO_PLAN:
            audio = True
            continue
        if k not in LISTAS_T or not (
            isinstance(pv.get(k), list) and isinstance(pn.get(k), list)
        ):
            return None, f"cambió PLAN.{k}", False
        dv = [json.dumps(e, sort_keys=True) for e in pv[k]]
        dn = [json.dumps(e, sort_keys=True) for e in pn[k]]
        for e in _diferencia(dv, dn):
            iv = _intervalo_entrada(json.loads(e))
            if iv is None:
                return None, f"cambio sin tiempo en PLAN.{k}", False
            spans.append(iv)
    lineas = [ln for ln in rv + rn if "data-start=" in ln]
    sin_tiempo = [
        ln for ln in rv + rn if "data-start=" not in ln
    ]  # CSS, motor.js: whole film
    planes = [
        json.dumps(e)
        for p in (pv, pn)
        for v in p.values()
        if isinstance(v, list)
        for e in v
    ]
    for rel in sorted(
        set(assets_viejos) ^ set(assets_nuevos)
        | {
            r
            for r in set(assets_viejos) & set(assets_nuevos)
            if assets_viejos[r] != assets_nuevos[r]
        }
    ):
        nombre = re.compile(rf"\b{re.escape(Path(rel).stem)}\b")
        if any(nombre.search(ln) for ln in sin_tiempo):
            return None, f"cambió {rel}, usado en toda la película", False
        usos = [ln for ln in lineas if nombre.search(ln)] + [
            e for e in planes if nombre.search(e)
        ]
        if not usos:
            return None, f"cambió {rel} y no sé dónde se ve", False
        for u in usos:
            if u.startswith("<audio"):
                audio = True
                continue
            iv = (
                _intervalo_linea(u)
                if u.startswith("<")
                else _intervalo_entrada(json.loads(u))
            )
            if iv is None:
                return None, f"cambió {rel}, usado sin tiempo", False
            spans.append(iv)
    return spans, "", audio


def ventanas(
    spans: list[tuple[float, float]], plan: dict
) -> tuple[list[tuple[float, float]] | None, str]:
    """Changed spans -> whole scenes [start_i, start_{i+1}), contiguous ones merged."""
    inicios = sorted(float(e["t0"]) for e in plan.get("escenas", []))
    dur = float(plan.get("D") or 0)
    if not inicios or inicios[0] != 0 or not dur:
        return None, "PLAN sin escenas"
    bordes = list(zip(inicios, inicios[1:] + [dur]))
    sucias = sorted(
        {
            i
            for lo, hi in spans
            for i, (a, b) in enumerate(bordes)
            if a < hi + MARGEN and b > lo - MARGEN
        }
    )
    out: list[tuple[float, float]] = []
    for i in sucias:
        a, b = bordes[i]
        if out and out[-1][1] == a:
            out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    if not out:
        return None, "sin cambios visibles"
    if len(out) > MAX_VENTANAS or sum(b - a for a, b in out) > MAX_FRAC * dur:
        return (
            None,
            f"{len(out)} tramos, {sum(b - a for a, b in out):.0f} s: sale más a cuenta el completo",
        )
    return out, ""


def recortar(html: str, a: float, b: float) -> str:
    """The page for one span: no audio (the final keeps the old track) and no video that never shows
    in [a, b), so HyperFrames neither mixes nor extracts them. The DOM stays: motor.js needs it."""
    html = re.sub(r"<audio\b[^>]*></audio>", "", html)

    def fuera(m: re.Match) -> str:
        t = _START.search(m.group(0))
        if t is None:
            return m.group(0)
        s, d = float(t.group(1)), float(t.group(2) or 0)
        return "" if s >= b or s + d <= a else m.group(0)

    return re.sub(r"<video\b[^>]*data-start=[^>]*></video>", fuera, html)


def n_frames(mp4: Path) -> int:
    r = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-count_packets",
            "-select_streams",
            "v",
            "-show_entries",
            "stream=nb_read_packets",
            "-of",
            "csv=p=0",
            str(mp4),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    return int(r.stdout.strip() or 0)


def empalmar(
    viejo: Path,
    partes: list[tuple[float, float, Path]],
    fps: int,
    salida: Path,
    gpu: bool,
) -> tuple[bool, str]:
    """Old final with each [a, b) replaced by its span render; audio copied from the old final."""
    total = n_frames(viejo)
    cortes, f = [], 0
    for i, (a, b, mp4) in enumerate(partes, 1):
        fa, fb = frame(a, fps), min(frame(b, fps), total)
        if (n := n_frames(mp4)) != fb - fa:
            return False, f"tramo {a}-{b}: {n} frames, esperaba {fb - fa}"
        if fa > f:
            cortes.append(
                f"[0:v]trim=start_frame={f}:end_frame={fa},setpts=PTS-STARTPTS[v{len(cortes)}]"
            )
        cortes.append(f"[{i}:v]setpts=PTS-STARTPTS[v{len(cortes)}]")
        f = fb
    if f < total:
        cortes.append(f"[0:v]trim=start_frame={f},setpts=PTS-STARTPTS[v{len(cortes)}]")
    fc = ";".join(cortes) + ";" + "".join(f"[v{i}]" for i in range(len(cortes)))
    fc += f"concat=n={len(cortes)}:v=1:a=0[v]"
    enc = (
        ["-c:v", "h264_nvenc", "-preset", "p5", "-cq", "16"]
        if gpu
        else ["-c:v", "libx264", "-preset", "medium", "-crf", "16"]
    )
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(viejo)]
    for *_, mp4 in partes:
        cmd += ["-i", str(mp4)]
    cmd += [
        "-filter_complex",
        fc,
        "-map",
        "[v]",
        "-map",
        "0:a?",
        *enc,
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "copy",
        "-movflags",
        "+faststart",
        str(salida),
    ]
    r = subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode or not salida.exists():
        return False, f"ffmpeg: {r.stderr[-300:]}"
    if (n := n_frames(salida)) != total:
        return False, f"empalme con {n} frames, el anterior tenía {total}"
    return True, f"{len(partes)} tramo(s), {total} frames"


def espejo(proy: Path) -> Path:
    """Hard-linked copy of the project without renders/, next to it: HyperFrames copies the whole
    folder into a span's plan, and the critic's old MP4s (r0.mp4: 838 MB) push it past the 2 GiB cap
    (PLAN_TOO_LARGE, 24-nov; .hyperframesignore does not reach that copy)."""
    dst = proy.parent / f".{proy.name}-tramos"
    shutil.rmtree(dst, ignore_errors=True)
    for f in proy.rglob("*"):
        rel = f.relative_to(proy)
        if rel.parts[0] == "renders" or not f.is_file():
            continue
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        try:
            os.link(f, dst / rel)
        except OSError:  # another volume or a filesystem without hard links
            shutil.copy2(f, dst / rel)
    return dst


def con_audio(video: Path, fuente: Path, fps: int, salida: Path) -> tuple[bool, str]:
    """`video`'s frames with `fuente`'s audio, cut to the video's length (a 1 fps render rounds the
    film up to whole seconds). Both streams copied: loudnorm re-encodes the audio next."""
    total = n_frames(video)
    r = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(video),
            "-i",
            str(fuente),
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c",
            "copy",
            "-t",
            f"{total / fps:.6f}",
            "-movflags",
            "+faststart",
            str(salida),
        ],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if r.returncode or not salida.exists():
        return False, f"ffmpeg: {r.stderr[-300:]}"
    if (n := n_frames(salida)) != total:
        return False, f"con audio: {n} frames, el vídeo tenía {total}"
    return True, "audio re-mezclado"
