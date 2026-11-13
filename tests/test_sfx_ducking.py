"""M1 by construction: construir.tope_vol caps an SFX so the voice keeps the rubric margin over it.

Checked with the critic's own instrument (tools/medir_mezcla.medir) on a synthetic mix."""

from __future__ import annotations

import os
import sys
import unittest

import numpy as np

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "tools"))
sys.path.insert(0, os.path.join(RAIZ, "video-v2", "motor"))

import construir as C
import medir_mezcla as M

SR = M.SR


def banda(n, seed, lo=250, hi=3500):
    rng = np.random.default_rng(seed)
    X = np.fft.rfft(rng.standard_normal(n))
    f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    x = np.fft.irfft(X, n)
    return x / np.abs(x).max()


def mezcla(voz, sfx, t, vol):
    mix = voz.copy()
    a = int(t * SR)
    mix[a : a + len(sfx)] += vol * sfx[: len(mix) - a]
    return mix


class DuckingTest(unittest.TestCase):
    def setUp(self):
        self.voz = 0.5 * banda(int(6 * SR), 0)
        self.whoosh = banda(
            int(0.7 * SR), 1, 800, 3000
        )  # a loud sweep right in the voice band
        self.tramos = [(0.0, 6.0)]

    def test_capped_sfx_keeps_margin(self):
        vol = C.tope_vol(self.whoosh, 2.1, 0.5, self.voz, self.tramos, SR, 10.0)
        self.assertLess(vol, 0.5)
        r = M.medir(
            mezcla(self.voz, self.whoosh, 2.1, vol),
            self.voz,
            self.tramos,
            umbral_db=10.0,
        )
        self.assertGreaterEqual(r["min_db"], 10.0, r["tapada"])

    def test_uncapped_sfx_fails_the_critic(self):  # the case above is a real one
        r = M.medir(
            mezcla(self.voz, self.whoosh, 2.1, 0.5),
            self.voz,
            self.tramos,
            umbral_db=10.0,
        )
        self.assertLess(r["min_db"], 10.0)

    def test_sfx_in_a_voice_gap_is_untouched(self):
        voz = self.voz.copy()
        voz[int(2 * SR) : int(3.5 * SR)] = 0
        vol = C.tope_vol(self.whoosh, 2.2, 0.5, voz, [(0.0, 2.0), (3.5, 6.0)], SR, 10.0)
        self.assertEqual(vol, 0.5)


if __name__ == "__main__":
    unittest.main()
