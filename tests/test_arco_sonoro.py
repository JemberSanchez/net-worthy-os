"""Music arc and voice ride: the ffmpeg gain expression and the baked bed."""

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import soundfile as sf

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "video-v2" / "motor"))
sys.path.insert(0, str(RAIZ / "tools"))
spec = importlib.util.spec_from_file_location(
    "construir_arco_test", RAIZ / "video-v2" / "motor" / "construir.py"
)
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)


def _rms_db(x):
    return 20 * np.log10(np.sqrt(np.mean(x**2)) + 1e-9)


class ArcoTest(unittest.TestCase):
    def test_lerp_interpola_y_mantiene_el_ultimo_valor(self):
        e = (
            C._lerp([(1.0, 0.0), (3.0, 10.0)])
            .replace("lt", "_lt")
            .replace("if(", "_if(")
        )
        ev = lambda t: eval(
            e, {"t": t, "_lt": lambda a, b: a < b, "_if": lambda c, a, b: a if c else b}
        )
        self.assertAlmostEqual(ev(2.0), 5.0)
        self.assertAlmostEqual(ev(9.0), 10.0)

    def test_arco_baja_la_ganancia_y_cierra_el_filtro_donde_se_ancla(self):
        words = [
            {"text": "uno", "start": 0.0, "end": 0.2},
            {"text": "dos", "start": 2.0, "end": 2.2},
        ]
        with tempfile.TemporaryDirectory() as d:
            bed = Path(d) / "bed.wav"
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=f=4000:d=4:r=48000",
                    "-ac",
                    "2",
                    str(bed),
                ],
                check=True,
            )
            antes, sr = sf.read(bed)
            arco = [
                {"en": "0:uno", "db": 0, "abre": 1},
                {"en": "0:dos", "db": -20, "abre": 1},
            ]
            C.hornear_arco(bed, arco, words)
            x, _ = sf.read(bed)
        self.assertEqual(len(x), len(antes))
        self.assertAlmostEqual(
            _rms_db(x[3 * sr :]) - _rms_db(antes[3 * sr :]), -20, delta=1
        )
        self.assertAlmostEqual(
            _rms_db(x[: sr // 20]), _rms_db(antes[: sr // 20]), delta=1
        )

    def test_arco_solo_con_db_o_solo_con_abre_no_revienta(self):
        words = [{"text": "uno", "start": 0.0, "end": 0.2}]
        for arco in ([{"en": "0:uno", "db": -6}], [{"en": "0:uno", "abre": 1}]):
            with self.subTest(arco=arco), tempfile.TemporaryDirectory() as d:
                bed = Path(d) / "bed.wav"
                subprocess.run(
                    [
                        "ffmpeg",
                        "-v",
                        "error",
                        "-y",
                        "-f",
                        "lavfi",
                        "-i",
                        "sine=f=4000:d=1:r=48000",
                        str(bed),
                    ],
                    check=True,
                )
                antes, _ = sf.read(bed)
                C.hornear_arco(bed, arco, words)
                x, _ = sf.read(bed)
                # a missing key means neutral: 0 dB when absent, fully open when absent
                esperado = -6 if "db" in arco[0] else 0
                self.assertAlmostEqual(_rms_db(x) - _rms_db(antes), esperado, delta=1)


if __name__ == "__main__":
    unittest.main()
