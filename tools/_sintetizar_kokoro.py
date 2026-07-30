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


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("Uso: _sintetizar_kokoro.py <voz> <wav-destino>  (texto por stdin)")
    voz, destino = sys.argv[1], sys.argv[2]
    texto = sys.stdin.read().strip()
    if not texto:
        raise SystemExit("stdin vacío: no hay texto que sintetizar")

    # lang_code='a' = American English. Cambia a 'b' si algún día se usa una voz bm_/bf_ (británica).
    lang = "b" if voz.startswith(("bm_", "bf_")) else "a"
    pipe = KPipeline(lang_code=lang)

    trozos = [audio for _, _, audio in pipe(texto, voice=voz)]
    if not trozos:
        raise SystemExit(f"Kokoro no generó audio para la voz {voz!r}")
    audio = np.concatenate(trozos)
    sf.write(destino, audio, 24000)   # Kokoro sintetiza siempre a 24kHz
    print(f"{len(audio)/24000:.2f}s")


if __name__ == "__main__":
    main()
