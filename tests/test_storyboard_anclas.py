"""Tests de las anclas del storyboard v2 (frase:palabra -> segundos).

Es la puerta que caza un storyboard mal escrito (a mano o por un LLM) ANTES del render: un ancla
que no resuelve tiene que fallar con un mensaje que diga qué frase y qué palabra, no caer a 0 s.
"""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video-v2", "motor"))

import anclas  # noqa: E402

W = [{"text": x, "start": i * 0.5, "end": i * 0.5 + 0.4} for i, x in enumerate(
    "He died with eight million dollars. No big salary. Team skill, or team time?".split())]
# frases: 0 = He..dollars. (0-5) · 1 = No big salary. (6-8) · 2 = Team skill, or team time? (9-13)


class AnclasTest(unittest.TestCase):
    def test_frases(self):
        self.assertEqual(anclas.frases(W), [[0, 1, 2, 3, 4, 5], [6, 7, 8], [9, 10, 11, 12, 13]])

    def test_arranque_de_frase_palabra_y_final(self):
        self.assertEqual(anclas.t(W, "1"), 3.0)
        self.assertEqual(anclas.t(W, "0:eight"), 1.5)
        self.assertEqual(anclas.t(W, "0:dollars"), 2.5)       # ignora la puntuación
        self.assertEqual(anclas.t(W, "0:dollars$"), 2.9)      # final de la palabra
        self.assertEqual(anclas.t(W, "1:salary$+0.2"), 4.6)   # termina en 4.4, +0.2
        self.assertEqual(anclas.t(W, "1:big-0.1"), 3.4)

    def test_palabra_con_guion_no_es_desplazamiento(self):
        w = [{"text": x, "start": i * 1.0, "end": i * 1.0 + 0.5} for i, x in enumerate("He held ninety-five stocks.".split())]
        self.assertEqual(anclas.t(w, "0:ninety-five"), 2.0)
        self.assertEqual(anclas.t(w, "0:ninety-five$-0.1"), 2.4)

    def test_n_esima_aparicion(self):
        self.assertEqual(anclas.t(W, "2:team"), 4.5)
        self.assertEqual(anclas.t(W, "2:team#2"), 6.0)

    def test_errores_explican_que_falla(self):
        with self.assertRaisesRegex(anclas.AnclaError, "solo tiene 3 frases"):
            anclas.t(W, "7")
        with self.assertRaisesRegex(anclas.AnclaError, "aparece 0 vez"):
            anclas.t(W, "1:million")                          # está en la frase 0, no en la 1
        with self.assertRaisesRegex(anclas.AnclaError, "aparece 2 vez"):
            anclas.t(W, "2:team#3")
        with self.assertRaisesRegex(anclas.AnclaError, "mal escrita"):
            anclas.t(W, "cero")

    def test_resolver_recorre_y_guarda_el_original(self):
        sb = {"escenas": [{"tipo": "titulo", "en": "1", "lineas": [{"texto": "x", "en": "1:big"}]}],
              "otro": "1"}                                    # solo las claves de ancla se tocan
        r = anclas.resolver(sb, W)
        self.assertEqual(r["escenas"][0]["en"], 3.0)
        self.assertEqual(r["escenas"][0]["en_ancla"], "1")
        self.assertEqual(r["escenas"][0]["lineas"][0]["en"], 3.5)
        self.assertEqual(r["otro"], "1")


if __name__ == "__main__":
    unittest.main(verbosity=2)
