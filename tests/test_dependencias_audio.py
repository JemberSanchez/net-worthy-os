"""Humo de compatibilidad faster-whisper <-> PyAV: decodifica un WAV mínimo generado en memoria con
el decodificador REAL de faster-whisper. PyAV 19 quitó `metadata_errors` de av.open() y
faster-whisper 1.2.1 lo pasa -> TypeError en transcribe(), que rompe tools/alinear_voz.py y
`motor/voz.py --alinear`. Los tests unitarios de alinear_voz no tocan el audio y no lo vieron.
No descarga ningún modelo: solo ejercita la ruta de decodificación (<0.1 s).
"""
from __future__ import annotations
import importlib.util
import io
import math
import struct
import unittest
import wave

TIENE_FW = importlib.util.find_spec("faster_whisper") is not None


def _wav_seno(segundos: float = 0.5, sr: int = 16000) -> io.BytesIO:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        n = int(segundos * sr)
        w.writeframes(b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / sr))) for i in range(n)))
    buf.seek(0)
    return buf


@unittest.skipUnless(TIENE_FW, "faster-whisper no instalado (CI sí lo instala desde requirements.txt)")
class DecodificadorWhisperTest(unittest.TestCase):
    def test_decode_audio_con_el_pyav_instalado(self):
        from faster_whisper.audio import decode_audio
        import av

        try:
            audio = decode_audio(_wav_seno(0.5), sampling_rate=16000)
        except TypeError as e:  # la firma de av.open() cambió bajo faster-whisper
            self.fail(f"faster-whisper no puede decodificar con av=={av.__version__}: {e}. "
                      "Revisar el tope de `av` en requirements.txt.")
        self.assertEqual(audio.shape, (8000,))
        self.assertGreater(float(abs(audio).max()), 0.1)  # no es silencio: decodificó de verdad


if __name__ == "__main__":
    unittest.main()
