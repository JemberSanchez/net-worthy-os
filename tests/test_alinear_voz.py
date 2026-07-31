"""Tests de tools/alinear_voz.py: el emparejamiento Needleman-Wunsch guion<->Whisper, y la
validación contra energía real (`hay_voz`) que descarta palabras que Whisper MIDIÓ pero que caen
en silencio real — visto en Ronald Read: "He" medido en t=24.62 con el audio en silencio ahí.
"""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from alinear_voz import alinear  # noqa: E402


class AlinearTest(unittest.TestCase):
    def setUp(self):
        self.guion = ["Says.", "He", "held", "ninety"]
        self.oidas = [
            {"word": "Says.", "start": 23.64, "end": 24.08},
            {"word": "He", "start": 24.62, "end": 25.06},
            {"word": "held", "start": 25.06, "end": 25.5},
            {"word": "ninety", "start": 25.5, "end": 25.72},
        ]

    def test_sin_hay_voz_confia_en_whisper_tal_cual(self):
        salida = alinear(self.guion, self.oidas)
        he = salida[1]
        self.assertTrue(he["medido"])
        self.assertEqual(he["t0"], 24.62)

    def test_con_hay_voz_descarta_medicion_sobre_silencio(self):
        # Silencio real solo alrededor de t=24.62 (donde Whisper midió "He" mal); el resto suena.
        hay_voz = lambda t: not (24.5 <= t <= 24.8)  # noqa: E731
        salida = alinear(self.guion, self.oidas, hay_voz=hay_voz)
        he = salida[1]
        self.assertFalse(he["medido"])
        self.assertNotEqual(he["t0"], 24.62)
        # Interpolado entre "Says." (t1=24.08) y "held" (t0=25.06), a mitad de camino.
        self.assertAlmostEqual(he["t0"], 24.57, places=2)
        # Los vecinos NO se tocan: siguen con su tiempo medido de Whisper.
        self.assertTrue(salida[0]["medido"])
        self.assertTrue(salida[2]["medido"])
        self.assertEqual(salida[2]["t0"], 25.06)

    def test_hay_voz_no_toca_palabras_sin_pareja(self):
        # Una palabra del guion sin match en Whisper sigue sin medir, con o sin hay_voz.
        guion = ["Says.", "He", "mumbled", "held"]
        salida = alinear(guion, self.oidas, hay_voz=lambda t: True)
        self.assertFalse(salida[2]["medido"])  # "mumbled" no existe en `oidas`

    def test_segmentos_saltan_el_silencio_real(self):
        # Caso real (Ronald Read, 30-jul): interpolar "He"/"held" en línea recta entre "says."
        # (t1=24.08) y "ninety-five" (t0=25.5) los dejaba a partir de 24.55 — pero la voz no vuelve
        # a sonar hasta ~25.3. Con `segmentos` (los tramos con voz real), deben caer DENTRO del
        # tramo activo (25.3, 25.5), no repartidos por todo el hueco silencioso.
        guion = ["says.", "He", "held", "ninety-five"]
        oidas = [
            {"word": "says.", "start": 23.64, "end": 24.08},
            {"word": "ninety-five", "start": 25.5, "end": 25.72},
        ]
        segmentos = [(23.6, 24.1), (25.3, 26.4)]  # silencio real entre 24.1 y 25.3
        salida = alinear(guion, oidas, segmentos=segmentos)
        he, held = salida[1], salida[2]
        self.assertGreaterEqual(he["t0"], 25.3 - 0.01)
        self.assertLessEqual(held["t1"], 25.5 + 0.01)

    def test_segmentos_camino_feliz_igual_al_reparto_lineal(self):
        # Si el hueco es voz continua (el caso normal: el tramo activo cubre TODO el hueco), el
        # resultado no cambia frente al reparto lineal de siempre — cero riesgo de regresión.
        guion = ["says.", "He", "held", "ninety-five"]
        oidas = [
            {"word": "says.", "start": 23.64, "end": 24.08},
            {"word": "ninety-five", "start": 25.5, "end": 25.72},
        ]
        sin_segmentos = alinear(guion, oidas)
        con_segmentos = alinear(guion, oidas, segmentos=[(23.6, 26.0)])
        self.assertAlmostEqual(sin_segmentos[1]["t0"], con_segmentos[1]["t0"], places=6)
        self.assertAlmostEqual(sin_segmentos[2]["t0"], con_segmentos[2]["t0"], places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
