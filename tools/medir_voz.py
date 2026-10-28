"""Mide el RITMO de la voz y la calidad del alineamiento (sincronía de subtítulos) de un Short.

    python tools/medir_voz.py video-v2/<proyecto>            # words.json + voice.mp3 del proyecto
    python tools/medir_voz.py <words.json|.align.json> [--audio voice.mp3] [--json]

Por qué existe
---------------
Los subtítulos, los cortes y los golpes del motor v2 se anclan a los tiempos de `words.json`
(alineamiento de `tools/alinear_voz.py`). Si una palabra está mal medida, TODO lo que se ancla a
ella sale desfasado; y si la voz tiene un silencio largo, el vídeo "se para" aunque la imagen se
mueva. Este medidor no re-alinea nada: lee los tiempos ya medidos y, si hay audio, los contrasta
con la energía real de la voz.

Qué mide
--------
- Velocidad: palabras por minuto de la voz (sin el silencio inicial) y por frase.
- Silencios: inicial (antes de la 1ª palabra), DENTRO de una frase y ENTRE frases, con su segundo.
- Sincronía (calidad del alineamiento): palabras de duración ~0 (el alineador no las midió y
  colapsó su tiempo) y, con audio, palabras cuyo tramo no contiene voz (medidas sobre silencio).

Validación del instrumento: ver tests/test_medir_voz.py (casos sintéticos con la respuesta
conocida) y el caso real conocido del #7 (`words.json` trae "This" en 0.42-0.42: una palabra de
duración cero que el alineador no midió; el medidor tiene que encontrarla).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DUR_MIN = 0.03          # s: por debajo, la palabra no se midió (start == end)
FIN_FRASE = re.compile(r"[.?!][\"')\]]*$")


def cargar_palabras(ruta: Path) -> list[dict]:
    """words.json ([{text,start,end}]) o .align.json ({palabras:[{w,t0,t1}]}) -> [{text,start,end}]."""
    d = json.loads(ruta.read_text(encoding="utf-8"))
    if isinstance(d, dict):
        d = d.get("palabras") or d.get("words") or []
    out = []
    for p in d:
        out.append({"text": p.get("text", p.get("w", "")),
                    "start": float(p.get("start", p.get("t0", 0.0))),
                    "end": float(p.get("end", p.get("t1", 0.0)))})
    return out


def frases(words: list[dict]) -> list[tuple[int, int]]:
    """[(i0, i1)] índices inclusivos de cada frase (corta en . ? ! al final de palabra)."""
    out, i0 = [], 0
    for i, w in enumerate(words):
        if FIN_FRASE.search(w["text"].strip()):
            out.append((i0, i))
            i0 = i + 1
    if i0 < len(words):
        out.append((i0, len(words) - 1))
    return out


def medir(words: list[dict], *, voz_en=None, pausa_dentro: float = 0.45, pausa_entre: float = 0.9) -> dict:
    """Función pura. `voz_en(t0, t1) -> bool` (opcional) dice si hay voz real en ese tramo.

    Devuelve {wpm, wpm_frases, silencio_inicial_s, pausas[], degeneradas[], sobre_silencio[], ...}.
    Cada pausa: {t, dur, tipo: 'dentro'|'entre', tras}. Solo se listan las que pasan del umbral."""
    if not words:
        return {"n_palabras": 0, "wpm": 0.0, "wpm_frases": [], "pausas": [], "degeneradas": [],
                "sobre_silencio": [], "silencio_inicial_s": 0.0, "duracion_voz_s": 0.0}
    fr = frases(words)
    ultimo_de_frase = {i1 for _, i1 in fr}
    pausas = []
    for i in range(len(words) - 1):
        hueco = words[i + 1]["start"] - words[i]["end"]
        entre = i in ultimo_de_frase
        if hueco > (pausa_entre if entre else pausa_dentro):
            pausas.append({"t": round(words[i]["end"], 2), "dur": round(hueco, 2),
                           "tipo": "entre" if entre else "dentro", "tras": words[i]["text"]})
    dur_voz = words[-1]["end"] - words[0]["start"]
    wpm = len(words) / dur_voz * 60 if dur_voz > 0 else 0.0
    wpm_fr = []
    for k, (a, b) in enumerate(fr):
        d = words[b]["end"] - words[a]["start"]
        n = b - a + 1
        wpm_fr.append({"frase": k, "t": round(words[a]["start"], 2), "palabras": n,
                       "wpm": round(n / d * 60, 0) if d > 0 else None})
    deg = [{"t": round(w["start"], 2), "palabra": w["text"]} for w in words if w["end"] - w["start"] < DUR_MIN]
    sobre = []
    if voz_en is not None:
        sobre = [{"t": round(w["start"], 2), "palabra": w["text"]} for w in words
                 if w["end"] - w["start"] >= DUR_MIN and not voz_en(w["start"], w["end"])]
    medidas = len(words) - len(deg) - len(sobre)
    return {"n_palabras": len(words), "wpm": round(wpm, 0), "wpm_frases": wpm_fr,
            "silencio_inicial_s": round(words[0]["start"], 2), "duracion_voz_s": round(dur_voz, 2),
            "pausas": pausas, "degeneradas": deg, "sobre_silencio": sobre,
            "pct_medidas": round(100 * medidas / len(words), 1)}


def detector_voz(audio: Path):
    """voz_en(t0, t1): ¿hay energía de voz en ese tramo? Reutiliza la envolvente RMS y el umbral
    de tools/alinear_voz.py (el MISMO criterio con el que se validó el alineamiento)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import numpy as np
    from alinear_voz import envolvente_rms
    rms, ventana = envolvente_rms(audio)
    piso = float(np.percentile(rms, 10)) if len(rms) >= 10 else 0.0
    thr = max(float(rms.max()) * 0.05, piso * 2.5)   # mismo umbral que alinear_audio

    def voz_en(t0: float, t1: float) -> bool:
        a, b = int(t0 / ventana), max(int(t0 / ventana) + 1, int(t1 / ventana) + 1)
        return bool((rms[a:b] > thr).any())
    return voz_en


def resolver(arg: str, audio: str | None) -> tuple[Path, Path | None]:
    p = Path(arg)
    if p.is_dir():
        a = p / "assets" / "voice.mp3"
        return p / "assets" / "words.json", (Path(audio) if audio else (a if a.exists() else None))
    return p, Path(audio) if audio else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("ruta", help="proyecto v2, words.json o .align.json")
    ap.add_argument("--audio")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    ruta, audio = resolver(a.ruta, a.audio)
    r = medir(cargar_palabras(ruta), voz_en=detector_voz(audio) if audio else None)
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    print(f"Velocidad       : {r['wpm']:.0f} palabras/min ({r['n_palabras']} palabras en {r['duracion_voz_s']} s)")
    print(f"Silencio inicial: {r['silencio_inicial_s']} s")
    print(f"Pausas largas   : {len(r['pausas'])}" + "".join(f"\n  t={p['t']}s {p['dur']}s ({p['tipo']}, tras \"{p['tras']}\")" for p in r["pausas"][:5]))
    print(f"Alineamiento    : {r['pct_medidas']} % medidas · {len(r['degeneradas'])} de duración 0 · "
          f"{len(r['sobre_silencio'])} sobre silencio" + (" (sin audio: no comprobado)" if not audio else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
