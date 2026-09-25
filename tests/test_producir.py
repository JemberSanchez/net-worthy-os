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


class MedicionValidaTest(unittest.TestCase):
    def test_no_aprueba_si_no_midio(self):
        """El falso aprobado real del #7: runtime con timeout, 0 muestras, contraste 'ok'."""
        falso = {"contrast": {"ok": True, "samples": [], "checked": 0},
                 "runtime": {"errorCount": 1, "findings": [{"message": "Navigation timeout of 10000 ms exceeded"}]}}
        ok, motivo = producir.medicion_valida(falso)
        self.assertFalse(ok)
        self.assertIn("Navigation timeout", motivo)
        self.assertFalse(producir.medicion_valida({"contrast": {"samples": [1.0], "checked": 0}, "runtime": {}})[0])
        self.assertTrue(producir.medicion_valida({"contrast": {"samples": [1.0], "checked": 7}, "runtime": {"errorCount": 0}})[0])


class BloquesAdnTest(unittest.TestCase):
    W = [{"text": x, "start": i * 1.0, "end": i * 1.0 + 0.8} for i, x in enumerate("Hi there. Big news! It works. The end.".split())]

    def test_duracion_real_y_tecnica(self):
        sb = {"cola_s": 2, "guion": [{"id": "hook", "texto": "Hi there. Big news!"}, {"id": "cierre", "texto": "It works. The end."}],
              "escenas": [{"tipo": "foto", "en": "0", "clip": "x"}, {"tipo": "revelacion", "en": "1"}, {"tipo": "cta", "en": "3:end"}]}
        b = producir.bloques_adn(sb, self.W)
        self.assertEqual(b, [{"block": "hook", "technique": "foto+clip,revelacion", "length_s": 4.0},
                             {"block": "cierre", "technique": "cta", "length_s": 5.8}])
        self.assertAlmostEqual(sum(x["length_s"] for x in b), self.W[-1]["end"] + 2)

    def test_si_guion_y_voz_no_casan_no_inventa(self):
        sb = {"guion": [{"id": "a", "texto": "Solo una frase."}], "escenas": []}
        self.assertNotIn("length_s", producir.bloques_adn(sb, self.W)[0])


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
