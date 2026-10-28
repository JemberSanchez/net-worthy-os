"""Tests de tools/alinear_voz.py: el emparejamiento Needleman-Wunsch guion<->Whisper, y la
validación contra energía real (`hay_voz`) que descarta palabras que Whisper MIDIÓ pero que caen
en silencio real — visto en Ronald Read: "He" medido en t=24.62 con el audio en silencio ahí.
"""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from alinear_voz import DUR_MIN, alinear  # noqa: E402


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


class PalabrasColapsadasTest(unittest.TestCase):
    """Medido el 28-oct (tools/medir_voz.py): 5 palabras de duración ~0 en read-janitor y 5 en
    grace-groner, casi todas INICIO de frase. Whisper mide la 1ª palabra tras una pausa con
    start == end pegado a la siguiente, o la pone en 0.0 (silencio) y `hay_voz` la descarta. Tienen
    que salir con duración real dentro del tramo con voz, sin pisar a la palabra anterior."""

    def test_inicio_de_frase_colapsado_por_whisper(self):
        # read-janitor: "one." | pausa | "Sixty"(12.86-12.86) "years"(12.86-13.14); la voz arranca en 12.70.
        guion = ["one.", "Sixty", "years", "later,"]
        oidas = [{"word": "one.", "start": 11.84, "end": 12.18},
                 {"word": "sixty", "start": 12.86, "end": 12.86},
                 {"word": "years", "start": 12.86, "end": 13.14},
                 {"word": "later,", "start": 13.14, "end": 13.42}]
        salida = alinear(guion, oidas, segmentos=[(11.8, 12.22), (12.70, 14.65)])
        sixty, years = salida[1], salida[2]
        self.assertAlmostEqual(sixty["t0"], 12.70, places=2)            # arranque real de la voz
        self.assertGreaterEqual(sixty["t1"] - sixty["t0"], DUR_MIN)
        self.assertGreaterEqual(years["t1"] - years["t0"], DUR_MIN)
        self.assertEqual(years["t1"], 13.14)                             # el tramo total se conserva
        self.assertEqual(salida[0]["t1"], 12.18)                         # la anterior no se toca
        self.assertEqual(salida[3]["t0"], 13.14)

    def test_primera_palabra_descartada_por_silencio(self):
        # read-janitor: Whisper pone "This" en 0.0-0.42 (silencio hasta 0.37) -> hay_voz la
        # descarta y la extrapolación le daba 0.42-0.42.
        guion = ["This", "janitor", "died"]
        oidas = [{"word": "This", "start": 0.0, "end": 0.42},
                 {"word": "janitor", "start": 0.42, "end": 0.84},
                 {"word": "died", "start": 0.84, "end": 1.12}]
        salida = alinear(guion, oidas, hay_voz=lambda t: t >= 0.30, segmentos=[(0.37, 2.58)])
        this, janitor = salida[0], salida[1]
        self.assertFalse(this["medido"])
        self.assertAlmostEqual(this["t0"], 0.37, places=2)
        self.assertGreaterEqual(this["t1"] - this["t0"], DUR_MIN)
        self.assertEqual(this["t1"], janitor["t0"])
        self.assertEqual(janitor["t1"], 0.84)

    def test_palabra_sin_pareja_entre_dos_contiguas(self):
        # grace-groner: Whisper oye "180" -> "one hundred eighty"; el "and" del guion no tiene
        # pareja y el hueco entre "hundred" y "eighty" mide 0. Voz continua: sin arranque nuevo.
        guion = ["hundred", "and", "eighty"]
        oidas = [{"word": "hundred", "start": 5.70, "end": 5.85},
                 {"word": "eighty", "start": 5.85, "end": 5.97}]
        salida = alinear(guion, oidas, segmentos=[(5.0, 7.0)])
        self.assertTrue(all(x["t1"] - x["t0"] >= DUR_MIN for x in salida))
        self.assertEqual((salida[0]["t0"], salida[2]["t1"]), (5.70, 5.97))
        self.assertTrue(all(salida[k]["t1"] == salida[k + 1]["t0"] for k in range(2)))

    def test_palabras_con_duracion_no_se_tocan(self):
        salida = alinear(["says.", "He", "held"], [{"word": "says.", "start": 1.0, "end": 1.4},
                                                     {"word": "He", "start": 1.9, "end": 2.1},
                                                     {"word": "held", "start": 2.1, "end": 2.4}],
                         segmentos=[(0.9, 1.45), (1.85, 2.5)])
        self.assertEqual([(x["t0"], x["t1"]) for x in salida], [(1.0, 1.4), (1.9, 2.1), (2.1, 2.4)])


if __name__ == "__main__":
    unittest.main(verbosity=2)


class ExpandirNumerosTest(unittest.TestCase):
    """Whisper escribe cifras donde el guion tiene palabras (y las PARTE: "$7", ",200", ",000.").
    Sin expandirlas, "a hundred and eighty" quedó con duración 0 y el subtítulo se pegó (23-sep)."""

    def test_numero_a_palabras(self):
        from alinear_voz import numero_a_palabras
        self.assertEqual(numero_a_palabras(75), ["seventy-five"])          # una palabra, como el guion
        self.assertEqual(numero_a_palabras(180), ["one", "hundred", "eighty"])
        self.assertEqual(numero_a_palabras(7_200_000), ["seven", "million", "two", "hundred", "thousand"])

    def test_une_trozos_y_reparte_el_tiempo(self):
        from alinear_voz import expandir_numeros
        out = expandir_numeros([{"word": "$7", "start": 2.64, "end": 2.98}, {"word": ",200", "start": 2.98, "end": 3.52},
                                {"word": ",000.", "start": 3.52, "end": 4.22}, {"word": "No", "start": 4.96, "end": 5.14}])
        self.assertEqual([o["word"] for o in out],
                         ["seven", "million", "two", "hundred", "thousand", "dollars.", "No"])
        self.assertAlmostEqual(out[0]["start"], 2.64)
        self.assertAlmostEqual(out[5]["end"], 4.22)                           # el tramo entero se conserva
        self.assertTrue(all(o["end"] > o["start"] for o in out[:6]))          # ninguna palabra de duración 0
