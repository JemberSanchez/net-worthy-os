"""Tests de tools/medir_mezcla.py: relación voz/fondo recuperada en mezclas con la respuesta conocida."""
from __future__ import annotations

import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import medir_mezcla as M  # noqa: E402

SR = M.SR


def voz_sintetica(dur=8.0, seed=0):
    """Habla de mentira: ruido filtrado en la banda de voz, a ráfagas de 0,4 s con silencios."""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    x = rng.standard_normal(n)
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(n, 1 / SR)
    X[(f < 250) | (f > 3500)] = 0
    x = np.fft.irfft(X, n)
    env = (np.sin(2 * np.pi * np.arange(n) / SR / 0.8) > -0.2).astype(float)
    return x * env / np.abs(x).max()


def musica_sintetica(dur=8.0):
    t = np.arange(int(dur * SR)) / SR
    return sum(np.sin(2 * np.pi * f0 * t) for f0 in (220, 330, 440, 660, 990, 1320)) / 6


def mezclar(v, m, db, g=0.8, lag=40):
    """Escala la música para que voz/fondo en banda (global, en tramos con voz) sea `db`."""
    k = np.sqrt(M.energia_banda(v) / M.energia_banda(m) / 10 ** (db / 10))
    mix = g * (v + k * m)
    return np.concatenate([np.zeros(lag), mix])[: len(v)]


class MedirMezclaTest(unittest.TestCase):
    def setUp(self):
        self.v, self.m = voz_sintetica(), musica_sintetica()

    def test_recupera_retardo_y_ganancia_desconocidos(self):
        r = M.medir(mezclar(self.v, self.m, 15, g=0.8, lag=40), self.v)
        self.assertAlmostEqual(r["retardo_ms"], 1000 * 40 / SR, places=1)
        self.assertAlmostEqual(r["ganancia"], 0.8, places=2)

    def test_relacion_conocida_dentro_de_1_db(self):
        for db in (20, 10, 0):
            r = M.medir(mezclar(self.v, self.m, db), self.v)
            self.assertLess(abs(r["mediana_db"] - db), 2.0, f"objetivo {db}: medido {r['mediana_db']}")

    def test_mezcla_limpia_no_tiene_tramos_tapados(self):
        r = M.medir(mezclar(self.v, self.m, 25), self.v)
        self.assertEqual(r["tapada"], [])

    def test_musica_encima_marca_los_tramos_con_su_segundo(self):
        r = M.medir(mezclar(self.v, self.m, 0), self.v)
        self.assertGreater(r["pct_tapada"], 80)
        self.assertTrue(r["tapada"][0]["t"] < 1.0)

    def test_solo_cuenta_los_tramos_con_voz(self):
        r = M.medir(mezclar(self.v, self.m, 0), self.v, tramos_voz=[(2.0, 3.0)])
        self.assertTrue(all(2.0 - M.VENTANA_S <= x["t"] < 3.0 for x in r["tapada"]))

    def test_tramos_de_words_ignora_palabras_degeneradas(self):
        self.assertEqual(M.tramos_de_words([{"start": 1.0, "end": 1.0}, {"start": 1.0, "end": 1.5}]),
                         [(0.95, 1.55)])


if __name__ == "__main__":
    unittest.main()
