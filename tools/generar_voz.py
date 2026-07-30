"""Guion -> voz -> alineamiento, en un solo comando. Sin CapCut, sin límite mensual.

    python tools/generar_voz.py <clave-del-short> [--motor piper|kokoro] [--voz <nombre>] [--forzar]

Por qué existe
---------------
El paso de voz era el único que seguía siendo 100% manual: abrir CapCut, pegar el guion, generar,
exportar, mover el archivo a `data/`. Y la voz "Firme Pilot" de CapCut no se puede invocar por
script — no hay API, es la app.

Dos motores, los dos locales y sin caducidad — la elección entre ellos SIEMPRE fue del usuario,
comparando audio real, nunca decidida por mí:

- **Kokoro** (Apache-2.0), voz `am_adam` — la que ganó una comparativa a ciego de 7 voces (4
  americanas + 3 británicas, medidas por tono real en Hz para poder elegir "más grave" con datos,
  no a ojo) escuchada por el usuario el 2026-07-30. Es el motor POR DEFECTO desde esa decisión.
  Corre en un venv de Python 3.12 aparte (`tools/.venv-voces/`): la cadena
  `kokoro -> misaki[en] -> spacy -> thinc -> blis<1.1.0` no tiene wheel para el 3.14 del proyecto
  — verificado forzando la instalación, no es un límite de metadata sin más.
- **Piper** (MIT), voz `en_US-ryan-high` — el primero que se probó y automatizó, sigue disponible
  con `--motor piper`. Corre en el Python 3.14 principal, sin dependencias extra.

Qué hace
--------
1. Lee el guion del Short desde el HTML (`guion_del_short`, la misma fuente de verdad que usa
   `alinear_voz.py` — el guion nunca se teclea dos veces).
2. Sintetiza. Guarda como `data/<voz>` con el nombre EXACTO que el Short ya declara (`CFG.voz`),
   así que el motor de vídeo lo encuentra sin tocar ni una línea del HTML.
3. Encadena `alinear_voz.generar_alineamiento()` sobre el audio recién creado: sale con
   `.align.json` listo, no solo el audio — "Usar la voz del proyecto" ya calibra con tiempos
   medidos desde el primer render, no hace falta un paso aparte.

Qué NO hace
-----------
No decide el timbre de voz del canal — eso lo decide quien escucha. No sobrescribe un audio ya
existente salvo que se pida `--forzar` — la voz de un Short ya revisado no se toca sola.
"""
from __future__ import annotations

import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):     # cp1252 no tiene "✓"; no tumbar el cálculo por eso
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alinear_voz import guion_del_short, generar_alineamiento, RAIZ  # noqa: E402

MOTOR_DEFECTO = "kokoro"

VOZ_PIPER = RAIZ / "data" / "voces-piper" / "en_US-ryan-high.onnx"
VOZ_KOKORO_DEFECTO = "am_adam"
VENV_KOKORO = RAIZ / "tools" / ".venv-voces"
PYTHON_KOKORO = VENV_KOKORO / "Scripts" / "python.exe"
HELPER_KOKORO = Path(__file__).resolve().parent / "_sintetizar_kokoro.py"

PICO_OBJETIVO = 0.89   # ~ -1 dBFS: dentro del margen, sin clipear (medido: el bruto llegaba a 1.0)


def _normalizar_pico(muestras: np.ndarray) -> np.ndarray:
    pico = float(np.abs(muestras).max()) or 1.0
    return (muestras * (PICO_OBJETIVO / pico)).astype(np.float32)


def sintetizar_piper(texto: str, modelo_path: Path) -> tuple[np.ndarray, int]:
    """Devuelve (muestras float32 en [-1,1] ya normalizadas de pico, sample_rate)."""
    from piper import PiperVoice

    voz = PiperVoice.load(str(modelo_path))
    trozos = list(voz.synthesize(texto))
    if not trozos:
        raise SystemExit("Piper no generó audio (¿texto vacío?)")
    muestras = np.concatenate([t.audio_float_array for t in trozos])
    sr = trozos[0].sample_rate
    return _normalizar_pico(muestras), sr


def sintetizar_kokoro(texto: str, voz: str) -> tuple[np.ndarray, int]:
    """Sintetiza con Kokoro en el venv de Python 3.12 (subproceso: Kokoro no vive en el 3.14
    principal). El texto viaja por stdin — evita límites/escapes de línea de comandos."""
    import soundfile as sf
    import tempfile

    if not PYTHON_KOKORO.exists():
        raise SystemExit(
            f"No encuentro el entorno de Kokoro en {VENV_KOKORO}.\n"
            "Créalo (una vez):\n"
            f'  py -3.12 -m venv "{VENV_KOKORO}"\n'
            f'  "{PYTHON_KOKORO}" -m pip install "kokoro>=0.9.4" soundfile\n'
            "O usa --motor piper mientras tanto.")
    with tempfile.TemporaryDirectory() as tmp:
        wav_tmp = Path(tmp) / "kokoro.wav"
        r = subprocess.run(
            [str(PYTHON_KOKORO), str(HELPER_KOKORO), voz, str(wav_tmp)],
            input=texto, capture_output=True, text=True, encoding="utf-8")
        if r.returncode != 0 or not wav_tmp.exists():
            raise SystemExit(f"Kokoro falló (voz={voz}):\n{r.stderr[-2000:]}")
        muestras, sr = sf.read(str(wav_tmp), dtype="float32")
    return _normalizar_pico(muestras), sr


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


def _valor_de(bandera: str) -> str | None:
    if bandera in sys.argv:
        i = sys.argv.index(bandera)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return None


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    clave = sys.argv[1]
    forzar = "--forzar" in sys.argv
    motor = _valor_de("--motor") or MOTOR_DEFECTO
    if motor not in ("piper", "kokoro"):
        raise SystemExit(f"--motor debe ser 'piper' o 'kokoro', no {motor!r}")
    voz_motor = _valor_de("--voz") or (VOZ_KOKORO_DEFECTO if motor == "kokoro" else None)

    if motor == "piper" and not VOZ_PIPER.exists():
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
    print(f"Motor   : {motor}" + (f" ({voz_motor})" if voz_motor else f" ({VOZ_PIPER.stem})"))
    print(f"Guion   : {len(texto)} caracteres, {len(frases)} frases\n")
    print("Sintetizando…")

    if motor == "kokoro":
        muestras, sr = sintetizar_kokoro(texto, voz_motor)
    else:
        muestras, sr = sintetizar_piper(texto, VOZ_PIPER)

    destino.parent.mkdir(parents=True, exist_ok=True)
    guardar(muestras, sr, destino)
    print(f"✓ {destino}  ({len(muestras)/sr:.2f}s a {sr}Hz)\n")

    print("Alineando (faster-whisper, tiempo real medido por palabra)…\n")
    generar_alineamiento(clave, ruta_audio=destino)
    print("\nListo: audio + alineamiento generados. En el motor, «Usar la voz del proyecto» ya calibra con tiempos medidos.")


if __name__ == "__main__":
    main()
