"""Tests de tools/medir_voz.py: ritmo de la voz y calidad del alineamiento con respuestas conocidas."""
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from medir_voz import frases, medir  # noqa: E402


def w(text, s, e):
    return {"text": text, "start": s, "end": e}


# 10 palabras en 4 s exactos -> 150 palabras/min; pausa de 0,6 s DENTRO de la 1ª frase y 1,2 s ENTRE frases
WORDS = [w("He", 0.5, 0.7), w("bought", 0.7, 1.0), w("boring", 1.6, 1.9), w("stocks.", 1.9, 2.3),
         w("Sixty", 3.5, 3.5),                                    # duración 0: el alineador no la midió
         w("years", 3.5, 3.7), w("later", 3.7, 3.9), w("eight", 3.9, 4.1), w("million", 4.1, 4.3),
         w("dollars.", 4.3, 4.5)]


class MedirVozTest(unittest.TestCase):
    def test_frases_cortan_en_puntuacion_final(self):
        self.assertEqual(frases(WORDS), [(0, 3), (4, 9)])

    def test_velocidad_en_palabras_por_minuto(self):
        self.assertEqual(medir(WORDS)["wpm"], 150)

    def test_pausas_dentro_y_entre_frases_con_su_segundo(self):
        p = medir(WORDS)["pausas"]
        self.assertEqual([(x["t"], x["dur"], x["tipo"]) for x in p], [(1.0, 0.6, "dentro"), (2.3, 1.2, "entre")])

    def test_pausa_normal_entre_frases_no_es_hallazgo(self):
        corto = WORDS[:4] + [w("Sixty", 2.9, 3.1)]
        self.assertEqual([x["tipo"] for x in medir(corto)["pausas"]], ["dentro"])

    def test_palabra_de_duracion_cero_es_degenerada(self):
        r = medir(WORDS)
        self.assertEqual(r["degeneradas"], [{"t": 3.5, "palabra": "Sixty"}])
        self.assertEqual(r["pct_medidas"], 90.0)

    def test_palabra_medida_sobre_silencio_se_detecta_con_audio(self):
        r = medir(WORDS, voz_en=lambda a, b: not (1.5 < a < 1.7))     # "boring" cae en silencio
        self.assertEqual([x["palabra"] for x in r["sobre_silencio"]], ["boring"])

    def test_silencio_inicial(self):
        self.assertEqual(medir(WORDS)["silencio_inicial_s"], 0.5)

    def test_sin_palabras_no_revienta(self):
        self.assertEqual(medir([])["n_palabras"], 0)


if __name__ == "__main__":
    unittest.main()
