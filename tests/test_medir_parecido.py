"""Tests de tools/medir_parecido.py: el instrumento separa copia, plantilla y vídeo distinto."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import medir_parecido as P  # noqa: E402

SB_A = {"guion": [{"texto": "This janitor died with eight million dollars. He bought boring companies."}],
        "escenas": [{"tipo": t} for t in ("foto", "foto", "lista", "tarjetas", "contador3d", "cta")],
        "musica": {"pista": {"commons": "File:Hustle.ogg"}},
        "clips": {"gas": {"pexels": 1}, "mop": {"pexels": 2}}, "imagenes": {"c": {"commons": "File:Cert.jpg"}}}


class ComparacionTest(unittest.TestCase):
    def test_un_storyboard_contra_si_mismo_es_identico(self):
        r = P.comparar(SB_A, SB_A)
        self.assertEqual((r["guion"], r["estructura"], r["recursos"]), (1.0, 1.0, 1.0))

    def test_otra_historia_con_la_misma_plantilla(self):
        b = {**SB_A, "guion": [{"texto": "A secretary left seven million to her college in 2010."}],
             "musica": {"pista": {"commons": "File:Other.ogg"}}, "clips": {"gas": {"pexels": 1}}, "imagenes": {}}
        r = P.comparar(SB_A, b)
        self.assertEqual(r["guion"], 0.0)
        self.assertEqual(r["estructura"], 1.0)                 # misma secuencia de escenas = plantilla
        self.assertEqual(r["recursos_comunes"], ["clip:1"])    # el mismo clip de Pexels reutilizado

    def test_claves_locales_iguales_con_recursos_distintos_no_cuentan(self):
        b = {**SB_A, "clips": {"gas": {"pexels": 99}, "mop": {"pexels": 98}}}
        self.assertNotIn("clip:1", P.comparar(SB_A, b)["recursos_comunes"])


class VisualTest(unittest.TestCase):
    def test_dhash_estable_ante_recompresion_y_distinto_entre_imagenes(self):
        import cv2
        rng = np.random.default_rng(1)
        a = cv2.GaussianBlur((rng.random((192, 108)) * 255).astype(np.uint8), (0, 0), 6)
        b = cv2.GaussianBlur((rng.random((192, 108)) * 255).astype(np.uint8), (0, 0), 6)
        ok, enc = cv2.imencode(".jpg", a, [cv2.IMWRITE_JPEG_QUALITY, 40])
        a2 = cv2.imdecode(enc, cv2.IMREAD_GRAYSCALE)
        ha, ha2, hb = P.dhash(a), P.dhash(a2), P.dhash(b)
        self.assertLessEqual(bin(ha ^ ha2).count("1"), P.HAMMING_MAX)
        self.assertGreater(bin(ha ^ hb).count("1"), P.HAMMING_MAX)

    def test_parecido_visual(self):
        self.assertEqual(P.parecido_visual([0b1010, 0xFFFF], [0b1011]), 0.5)
        self.assertEqual(P.parecido_visual([], [1]), 0.0)


class CorpusTest(unittest.TestCase):
    def test_solo_compara_con_la_misma_marca(self):
        with tempfile.TemporaryDirectory() as d:
            raiz = Path(d)
            for nombre, marca in (("yo", None), ("otro", None), ("ajena", "otra-marca"), ("sin_sb", "x")):
                (raiz / nombre).mkdir()
                if nombre != "sin_sb":
                    (raiz / nombre / "storyboard.json").write_text(json.dumps({**SB_A, "marca": marca}))
            self.assertEqual([p.name for p in P.corpus(raiz / "yo", raiz)], ["otro"])


if __name__ == "__main__":
    unittest.main()
