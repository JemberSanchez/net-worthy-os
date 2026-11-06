"""Gates over the final MP4 that the plan cannot see: audio against the script, frames, rendered text boxes,
voice lost in the mix, pauses in the middle of a clause. Called once from critico.revisar; every failure comes
back with its second. Measured costs and per-video results: docs/CERO-ERRORES.md. All PROVISIONAL."""

from __future__ import annotations

import re
from pathlib import Path

import medir_cuadros as mc
import medir_guion_audio as mga
import medir_texto

PUNTUACION = re.compile(r"[,:;—–\-.?!][\"')\]]*$")


def revisar_audio(
    sb: dict, mp4: Path, voz: Path, rm: dict | None, vs, u: dict, fallo, escena_en
) -> list[dict]:
    """Whisper also slips on correct audio, so a difference only blocks when a second measure agrees: the clean
    voice says it too (wrong take, A1), or the voice is under the background right there (masked, M1)."""
    guion = " ".join(g["texto"] for g in sb["guion"])
    res = mga.comparar(guion, mga.transcribir(mp4))
    out = []
    if not res["grave"] and not res["leve"]:
        return out
    limpia = mga.comparar(guion, mga.transcribir(voz))
    en_voz = {(d["guion"], d["oido"]) for d in limpia["grave"]} | {
        d["guion"] for d in limpia["grave"]
    }
    ventanas = (rm or {}).get("ventanas") or []
    lim = u["voz_sobre_fondo_db"]

    def db_en(t: float) -> float | None:
        c = [w["db"] for w in ventanas if w["t"] - 0.5 <= t < w["t"] + 0.5]
        return min(c) if c else None

    for d in res["grave"]:
        db = db_en(d["t"])
        if d["guion"] in en_voz or (d["guion"], d["oido"]) in en_voz:
            out.append(
                fallo(
                    "A1",
                    "alta",
                    f'la voz dice "{d["oido"]}" donde el guion dice "{d["guion"]}" (también en la voz limpia): re-sintetiza',
                    t=d["t"],
                    escena=escena_en(d["t"], vs),
                    evidencia="tools/medir_guion_audio.py",
                )
            )
        elif db is not None and db < lim:
            out.append(
                fallo(
                    "M1",
                    "alta",
                    f'no se oye "{d["guion"]}" en la mezcla ({db} dB < {lim}) y en la voz limpia sí',
                    t=d["t"],
                    escena=escena_en(d["t"], vs),
                    evidencia="tools/medir_guion_audio.py + tools/medir_mezcla.py",
                )
            )
        else:
            out.append(_a_escuchar(d, vs, fallo, escena_en))
    claros = {d["guion"] for d in limpia["leve"]}
    for d in res["leve"]:
        db = db_en(d["t"])
        if not d["oido"] and d["guion"] not in claros and db is not None and db < lim:
            out.append(
                fallo(
                    "M1",
                    "alta",
                    f'se pierde "{d["guion"]}" en la mezcla ({db} dB < {lim}) y en la voz limpia se oye',
                    t=d["t"],
                    escena=escena_en(d["t"], vs),
                    evidencia="tools/medir_guion_audio.py + tools/medir_mezcla.py",
                )
            )
        else:
            out.append(_a_escuchar(d, vs, fallo, escena_en))
    return out


def _a_escuchar(d: dict, vs, fallo, escena_en) -> dict:
    return fallo(
        "A1",
        "media",
        f'escuchar: guion "{d["guion"]}", transcrito "{d["oido"]}" (una sola medida, puede ser error del reconocedor)',
        t=d["t"],
        escena=escena_en(d["t"], vs),
        evidencia="tools/medir_guion_audio.py",
    )


def pausas_sin_puntuacion(
    rv: dict, vs, u: dict, fallo, escena_en
) -> list[dict]:
    """A pause after a comma is how Kokoro reads a comma (p90 0.48 s in 11 videos); with no punctuation the p99 is
    0.15 s, so a gap there is a broken take. Same limit as V1: the comma case stays `media` and does not block."""
    out = []
    for p in rv["pausas"]:
        if (
            p["tipo"] == "dentro"
            and p["dur"] > u["pausa_dentro_s"]
            and not PUNTUACION.search(p["tras"])
        ):
            out.append(
                fallo(
                    "V1",
                    "alta",
                    f'silencio de {p["dur"]}s sin puntuación tras "{p["tras"]}": toma rota, re-sintetiza',
                    t=p["t"],
                    t_fin=p["t"] + p["dur"],
                    escena=escena_en(p["t"], vs),
                )
            )
    return out


def revisar_cuadros(
    fr, frames: list[dict], vs, u: dict, fallo, escena_en
) -> list[dict]:
    """Black, frozen, flat and dark frames. Flat only counts if the OCR finds no text during it."""
    out = []
    for x in mc.negros(fr, u):
        out.append(
            fallo(
                "C1",
                "alta",
                "cuadros en negro",
                t=x["t"],
                t_fin=x["t_fin"],
                escena=escena_en(x["t"], vs),
            )
        )
    for x in mc.congelados(fr, u):
        out.append(
            fallo(
                "C1",
                "alta",
                "imagen congelada",
                t=x["t"],
                t_fin=x["t_fin"],
                escena=escena_en(x["t"], vs),
            )
        )
    g = mc.gancho(fr, u)
    if g["luma"] < u["gancho_luma_min"] or g["contraste"] < u["gancho_contraste_min"]:
        out.append(
            fallo(
                "C1",
                "alta",
                f"gancho oscuro o plano: luma {g['luma']} (mín. {u['gancho_luma_min']}), "
                f"contraste {g['contraste']} (mín. {u['gancho_contraste_min']})",
                t=0,
                escena=0,
            )
        )
    b = mc.banda_vacia(fr, u)
    if b:
        out.append(
            fallo("C1", "alta", f"franja vacía {b['lado']} en el {b['pct']} % del vídeo: la maqueta se ha descolocado", t=0)
        )
    for x in mc.planos(fr, u):
        if all(mc.sin_texto(f, u) for f in frames if x["t"] <= f["t"] <= x["t_fin"]):
            out.append(
                fallo(
                    "C1",
                    "alta",
                    "pantalla vacía en el MP4: sin texto y sin imagen visible",
                    t=x["t"],
                    t_fin=x["t_fin"],
                    escena=escena_en(x["t"], vs),
                )
            )
    return out


def revisar_cajas(
    frames: list[dict],
    diseno: list[dict],
    plan: dict,
    vs,
    u: dict,
    fallo,
    escena_en,
) -> list[dict]:
    """Rendered text boxes: designed text on designed text, against the frame edge, captions over a document."""
    es = lambda texto, t: medir_texto.es_disenado(texto, t, diseno)
    out = []
    for c in mc.colisiones(frames, es, u):
        out.append(
            fallo(
                "C2",
                "alta",
                f'"{c["a"]}" y "{c["b"]}" se pisan en pantalla',
                t=c["t"],
                t_fin=c["t_fin"],
                escena=escena_en(c["t"], vs),
                evidencia="OCR, cajas de texto reales",
            )
        )
    for c in mc.cortados(frames, es, u):
        out.append(
            fallo(
                "C2",
                "media",
                f'"{c["texto"]}" toca el borde según el OCR: mira si está cortado (OCR infla las cajas; 2 de 2 avisos en 11 vídeos fueron falsos)',
                t=c["t"],
                t_fin=c["t_fin"],
                escena=escena_en(c["t"], vs),
                evidencia="OCR, cajas de texto reales",
            )
        )
    for pr in plan.get("pruebas") or []:
        for c in mc.subtitulo_sobre_documento(
            [f for f in frames if pr["t0"] <= f["t"] < pr["t1"]], es, u
        ):
            out.append(
                fallo(
                    "C2",
                    "alta",
                    f'subtítulo "{c["a"]}" encima del texto del documento "{c["b"]}"',
                    t=c["t"],
                    t_fin=c["t_fin"],
                    escena=escena_en(c["t"], vs),
                    evidencia="OCR, cajas de texto reales",
                )
            )
    return out
