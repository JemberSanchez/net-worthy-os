"""Sintetiza texto con Kokoro y lo guarda en WAV. SOLO corre bajo el intérprete del venv de
Python 3.12 (`tools/.venv-voces/`) — Kokoro no instala en el 3.14 principal del proyecto (cadena
`kokoro -> misaki[en] -> spacy -> thinc -> blis<1.1.0`, sin wheel para 3.14; verificado forzando la
instalación, no es un límite arbitrario de metadata). `generar_voz.py`, que sí corre en 3.14, invoca
esto como subproceso y solo lee de vuelta el WAV — así el resto del pipeline (normalizar, codificar
a mp3, alinear) no necesita saber que hay dos Pythons de por medio.

    tools/.venv-voces/Scripts/python.exe tools/_sintetizar_kokoro.py <voz> <wav-destino>
    (el TEXTO se pasa por stdin, en UTF-8 — evita límites/():escapes de línea de comandos)
"""
import sys

import numpy as np
import soundfile as sf
from kokoro import KPipeline


def servidor() -> None:
    """--servidor: one process for a whole voice run; the pipeline loads once (~15-25 s each time
    otherwise). One JSON line in {"voz", "wav", "speed", "texto"}, one JSON line out {"s"} or {"error"}."""
    import json

    out, sys.stdout = sys.stdout, sys.stderr  # library prints must not break the one-line protocol
    pipes: dict[str, KPipeline] = {}
    for linea in sys.stdin:
        try:
            q = json.loads(linea)
            lang = "b" if q["voz"].startswith(("bm_", "bf_")) else "a"
            pipe = pipes.get(lang) or pipes.setdefault(lang, KPipeline(lang_code=lang))
            trozos = [a for _, _, a in pipe(q["texto"], voice=q["voz"], speed=float(q.get("speed", 1.0)))]
            if not trozos:
                raise ValueError(f"Kokoro no generó audio para la voz {q['voz']!r}")
            audio = np.concatenate(trozos)
            sf.write(q["wav"], audio, 24000)
            print(json.dumps({"s": round(len(audio) / 24000, 2)}), file=out, flush=True)
        except Exception as e:  # noqa: BLE001 -- the client gets the error and decides; the worker stays up
            print(json.dumps({"error": repr(e)[-2000:]}), file=out, flush=True)


def main() -> None:
    if sys.argv[1:] == ["--servidor"]:
        return servidor()
    if len(sys.argv) < 3:
        raise SystemExit("Uso: _sintetizar_kokoro.py <voz> <wav-destino>  (texto por stdin)")
    voz, destino = sys.argv[1], sys.argv[2]
    speed = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    texto = sys.stdin.read().strip()
    if not texto:
        raise SystemExit("stdin vacío: no hay texto que sintetizar")

    # lang_code='a' = American English. Cambia a 'b' si algún día se usa una voz bm_/bf_ (británica).
    lang = "b" if voz.startswith(("bm_", "bf_")) else "a"
    pipe = KPipeline(lang_code=lang)

    trozos = [audio for _, _, audio in pipe(texto, voice=voz, speed=speed)]
    if not trozos:
        raise SystemExit(f"Kokoro no generó audio para la voz {voz!r}")
    audio = np.concatenate(trozos)
    sf.write(destino, audio, 24000)   # Kokoro sintetiza siempre a 24kHz
    print(f"{len(audio)/24000:.2f}s")


if __name__ == "__main__":
    main()
