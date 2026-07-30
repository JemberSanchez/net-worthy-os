"""Guion -> voz -> alineamiento, en un solo comando. Sin CapCut, sin límite mensual.

    python tools/generar_voz.py <clave-del-short>

Por qué existe
---------------
El paso de voz era el único que seguía siendo 100% manual: abrir CapCut, pegar el guion, generar,
exportar, mover el archivo a `data/`. Y la voz "Firme Pilot" de CapCut no se puede invocar por
script — no hay API, es la app.

**Piper** (MIT, sin caducidad — verificado antes de tocar el código: era justo lo que descartó
ElevenLabs en este proyecto, licencia y expiración de voces) sí corre en local, headless, en el
Python de esta máquina. Probado contra el gancho real del #7 y aprobado por el usuario antes de
automatizarlo — este script no decide el timbre de voz del canal, solo ejecuta la decisión ya
tomada.

Qué hace
--------
1. Lee el guion del Short desde el HTML (`guion_del_short`, la misma fuente de verdad que usa
   `alinear_voz.py` — el guion nunca se teclea dos veces).
2. Sintetiza con Piper. Guarda como `data/<voz>` con el nombre EXACTO que el Short ya declara
   (`CFG.voz`), así que el motor lo encuentra sin tocar ni una línea del HTML.
3. Encadena `alinear_voz.generar_alineamiento()` sobre el audio recién creado: sale con
   `.align.json` listo, no solo el audio — "Usar la voz del proyecto" ya calibra con tiempos
   medidos desde el primer render, no hace falta un paso aparte.

Qué NO hace
-----------
No sustituye el juicio del usuario sobre CÓMO suena. No sobrescribe un audio ya existente salvo que
se pida `--forzar` — la voz de un Short ya publicado es parte de lo que se midió; no se toca sola.
"""
from __future__ import annotations

import sys
import wave
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):     # cp1252 no tiene "✓"; no tumbar el cálculo por eso
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alinear_voz import guion_del_short, generar_alineamiento, RAIZ  # noqa: E402

# Voz por defecto: en_US-ryan-high (Piper, MIT). Para probar otra, descárgala en data/voces-piper/
# desde https://huggingface.co/rhasspy/piper-voices y cambia esta constante.
VOZ_PIPER = RAIZ / "data" / "voces-piper" / "en_US-ryan-high.onnx"

PICO_OBJETIVO = 0.89   # ~ -1 dBFS: dentro dentro del margen, sin clipear (medido: el bruto llegaba a 1.0)


def sintetizar(texto: str, modelo_path: Path) -> tuple[np.ndarray, int]:
    """Devuelve (muestras float32 en [-1,1] ya normalizadas de pico, sample_rate)."""
    from piper import PiperVoice

    voz = PiperVoice.load(str(modelo_path))
    trozos = list(voz.synthesize(texto))
    if not trozos:
        raise SystemExit("Piper no generó audio (¿texto vacío?)")
    muestras = np.concatenate([t.audio_float_array for t in trozos])
    sr = trozos[0].sample_rate

    pico = float(np.abs(muestras).max()) or 1.0
    muestras = muestras * (PICO_OBJETIVO / pico)
    return muestras.astype(np.float32), sr


def guardar(muestras: np.ndarray, sr: int, destino: Path) -> None:
    pcm16 = (muestras * 32767).astype(np.int16)
    if destino.suffix.lower() == ".mp3":
        import lameenc
        enc = lameenc.Encoder()
        enc.set_bit_rate(128)
        enc.set_in_sample_rate(sr)
        enc.set_channels(1)
        enc.set_quality(2)  # 2 = alta calidad (0 mejor/lento .. 9 peor/rápido)
        mp3 = enc.encode(pcm16.tobytes()) + enc.flush()
        destino.write_bytes(mp3)
    else:
        with wave.open(str(destino), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
            w.writeframes(pcm16.tobytes())


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    clave = sys.argv[1]
    forzar = "--forzar" in sys.argv

    if not VOZ_PIPER.exists():
        raise SystemExit(
            f"No encuentro el modelo de voz en {VOZ_PIPER}.\n"
            "Descárgalo (una vez, ~120MB):\n"
            f"  curl -L -o \"{VOZ_PIPER}\" "
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx\n"
            f"  curl -L -o \"{VOZ_PIPER}.json\" "
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx.json")

    voz_nombre, frases = guion_del_short(clave)
    destino = RAIZ / "data" / voz_nombre
    if destino.exists() and not forzar:
        raise SystemExit(
            f"{destino} ya existe (probablemente la voz de un Short ya publicado o revisado).\n"
            "No se sobrescribe sola. Si de verdad quieres regenerarla: --forzar")

    texto = " ".join(frases)
    print(f"Short   : {clave}")
    print(f"Destino : {destino.name}")
    print(f"Voz     : {VOZ_PIPER.stem} (Piper, MIT)")
    print(f"Guion   : {len(texto)} caracteres, {len(frases)} frases\n")
    print("Sintetizando…")

    muestras, sr = sintetizar(texto, VOZ_PIPER)
    destino.parent.mkdir(parents=True, exist_ok=True)
    guardar(muestras, sr, destino)
    print(f"✓ {destino}  ({len(muestras)/sr:.2f}s a {sr}Hz)\n")

    print("Alineando (faster-whisper, tiempo real medido por palabra)…\n")
    generar_alineamiento(clave, ruta_audio=destino)
    print("\nListo: audio + alineamiento generados. En el motor, «Usar la voz del proyecto» ya calibra con tiempos medidos.")


if __name__ == "__main__":
    main()
