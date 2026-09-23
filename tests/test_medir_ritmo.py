"""Tests de tools/medir_ritmo.py: el tramo quieto más largo sobre frames sintéticos."""
from __future__ import annotations
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from medir_ritmo import tramo_quieto  # noqa: E402

FPS = 5


def plano(v: float) -> np.ndarray:
    return np.full((60, 34), v, dtype=np.uint8)


class TramoQuietoTest(unittest.TestCase):
    def test_video_totalmente_quieto_es_todo_quieto(self):
        r = tramo_quieto([plano(40)] * 30, fps=FPS)
        self.assertEqual(r["pct_quieto"], 100.0)
        self.assertAlmostEqual(r["max_s"], 30 / FPS)

    def test_cambio_constante_no_tiene_tramos_quietos(self):
        r = tramo_quieto([plano(i * 8 % 250) for i in range(30)], fps=FPS)
        self.assertEqual(r["max_s"], 0.0)
        self.assertEqual(r["pct_quieto"], 0.0)

    def test_encuentra_el_tramo_quieto_en_medio(self):
        # 2 s de cambio, 3 s quieto, 2 s de cambio
        frames = [plano(i * 20) for i in range(10)] + [plano(200)] * 15 + [plano(i * 15) for i in range(10)]
        r = tramo_quieto(frames, fps=FPS)
        self.assertAlmostEqual(r["max_s"], 3.0)      # 15 frames quietos a 5 fps
        self.assertAlmostEqual(r["desde_s"], 2.0)    # la meseta empieza en el frame 10

    def test_ruido_por_debajo_del_umbral_no_cuenta_como_cambio(self):
        rng = np.random.default_rng(0)
        # grano: +-1 nivel alrededor de 100 (lo que queda tras desenfocar y reducir)
        frames = [np.clip(100 + rng.integers(-1, 2, (60, 34)), 0, 255).astype(np.uint8) for _ in range(30)]
        r = tramo_quieto(frames, fps=FPS)
        self.assertEqual(r["pct_quieto"], 100.0)

    def test_video_mas_corto_que_el_lag_no_revienta(self):
        r = tramo_quieto([plano(1)] * 2, fps=FPS)
        self.assertEqual(r["max_s"], 0.0)


if __name__ == "__main__":
    unittest.main()
