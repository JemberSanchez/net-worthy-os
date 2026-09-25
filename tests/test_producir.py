"""Tests de la descripción que se publica (video-v2/motor/producir.py): lo que va a YouTube tiene
que llevar SIEMPRE el aviso YMYL, las fuentes de las cifras y la atribución de imágenes (CC BY la
exige: publicar sin ella es incumplir la licencia)."""
from __future__ import annotations
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video-v2", "motor"))

import producir  # noqa: E402

SB = {"publicacion": {"descripcion": "The janitor.", "hashtags": ["#shorts"]},
      "aviso": {"lineas": ["Illustrative", "Not financial advice"]},
      "cifras": [{"dato": "$8M", "fuente": "https://a.org"}, {"dato": "95", "fuente": "https://a.org"}]}


class ContrasteTest(unittest.TestCase):
    def test_un_instante_por_escena(self):
        h = ('<section id="s0" class="clip scene" data-start="0.000" data-duration="2.000">'
             '<section id="s1" class="clip scene" data-start="2.000" data-duration="0.100">')
        self.assertEqual(producir.instantes_escena(h), [1.2, 2.0])        # escena corta: nunca fuera de su ventana

    def test_solo_cuenta_lo_que_no_llega_a_aa(self):
        inf = [{"contrast": {"findings": [
            {"text": "Here's", "ratio": 2.67, "requiredRatio": 3, "time": 31.3},
            {"text": "ok", "ratio": 4.8, "requiredRatio": 4.5, "time": 2}]}}, {"contrast": None}]
        f = producir.fallos_contraste(inf)
        self.assertEqual(len(f), 1)
        self.assertIn('"Here\'s" 2.67:1', f[0])


class DescripcionTest(unittest.TestCase):
    def test_lleva_aviso_fuentes_creditos_y_hashtags(self):
        with tempfile.TemporaryDirectory() as d:
            img = Path(d, "assets", "img"); img.mkdir(parents=True)
            (img / "creditos.json").write_text(json.dumps([{"archivo": "x.jpg", "titulo": "File:Crash.jpg",
                "autor": "Orange County Archives", "licencia": "CC BY 2.0", "url_licencia": "https://cc/by/2.0",
                "fuente": "https://commons/x"}]))
            t = producir.descripcion(SB, Path(d))
        self.assertTrue(t.startswith("The janitor."))
        self.assertIn("Not financial advice", t)
        self.assertEqual(t.count("https://a.org"), 1)                 # fuentes sin repetir
        self.assertIn("Orange County Archives — CC BY 2.0", t)       # atribución exigida por CC BY
        self.assertTrue(t.rstrip().endswith("#shorts"))
        self.assertLessEqual(len(t), 5000)

    def test_sin_creditos_no_rompe(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("Not financial advice", producir.descripcion(SB, Path(d)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
