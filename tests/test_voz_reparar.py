"""V1 by construction: voz.reparar_frases re-synthesizes ONLY the sentence with a silence inside it.

The rule is the critic's (tools/medir_voz.medir + rubrica V1 pausa_dentro_s) on an audio with an
injected silence; a fake aligner reads the word bursts back from the audio."""

import importlib.util
import os
import unittest

import numpy as np

_ruta = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "video-v2",
    "motor",
    "voz.py",
)
_spec = importlib.util.spec_from_file_location("voz_reparar", _ruta)
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)

SR = 24000
SB = {
    "guion": [
        {"id": "a", "texto": "One two three."},
        {"id": "b", "texto": "Four five six."},
    ]
}


def clip(seed, hueco=None):
    """Three 0.25 s 'words' 0.08 s apart; `hueco` = silence (s) after the first word."""
    rng = np.random.default_rng(seed)
    out = []
    for k in range(3):
        out.append(0.5 * rng.standard_normal(int(0.25 * SR)).astype("float32"))
        if k < 2:
            out.append(
                np.zeros(
                    int((hueco if hueco and k == 0 else 0.08) * SR), dtype="float32"
                )
            )
    return np.concatenate(out)


def alinear(toma):
    """Word bursts by energy (10 ms frames), named with the script words in order."""
    m, sr = toma
    w = sr // 100
    on = np.abs(m[: len(m) // w * w]).reshape(-1, w).max(axis=1) > 0.05
    palabras, texto, i = [], " ".join(g["texto"] for g in SB["guion"]).split(), 0
    while i < len(on):
        if on[i]:
            j = i
            while j < len(on) and on[j]:
                j += 1
            palabras.append({"w": texto[len(palabras)], "t0": i / 100, "t1": j / 100})
            i = j
        i += 1
    return palabras


class RepararTest(unittest.TestCase):
    def setUp(self):
        self.a = clip(1)
        self.m = np.concatenate(
            [self.a, np.zeros(int(0.3 * SR), dtype="float32"), clip(2, hueco=0.6)]
        )

    def _reparar(self, *respuestas):
        pedidas, cola = [], list(respuestas)

        def sintetizar_frase(g):
            pedidas.append(g["texto"])
            return cola.pop(0) if len(cola) > 1 else cola[0], SR

        r = V.reparar_frases(
            SB, (self.m, SR), alinear((self.m, SR)), sintetizar_frase, alinear
        )
        return r, pedidas

    def test_measures_the_injected_silence(self):
        self.assertEqual(len(V.silencios_internos(clip(2, hueco=0.6), SR, 0.45)), 1)
        self.assertEqual(V.silencios_internos(clip(2), SR, 0.45), [])

    def test_critic_rule_sees_the_broken_sentence(self):
        rotas = V.pausas_v1(V._a_words(alinear((self.m, SR))))
        self.assertEqual([p["tras"] for p in rotas], ["Four"])

    def test_resynthesizes_only_the_bad_sentence_until_clean(self):
        r, pedidas = self._reparar(clip(3, hueco=0.6), clip(4))
        self.assertEqual(pedidas, ["Four five six."] * 2)
        self.assertEqual(V.pausas_v1(V._a_words(r["palabras"])), [])
        self.assertEqual(r["quedan"], [])
        np.testing.assert_array_equal(
            r["toma"][0][: len(self.a)], self.a
        )  # sentence a untouched
        nuevo = r["toma"][0][len(self.a) + int(0.3 * SR) :]
        self.assertAlmostEqual(
            V._rms_voz(nuevo, SR) / V._rms_voz(self.a, SR), 1.0, delta=0.1
        )

    def test_gives_up_after_three_tries_and_reports(self):
        r, pedidas = self._reparar(clip(3, hueco=0.6))
        self.assertEqual(len(pedidas), V.MAX_TOMAS)
        self.assertEqual(len(r["quedan"]), 1)
        self.assertIn("Four", r["quedan"][0]["tras"])

    def test_clean_take_is_not_touched(self):
        m = np.concatenate([self.a, np.zeros(int(0.3 * SR), dtype="float32"), clip(2)])
        pedidas = []
        r = V.reparar_frases(
            SB,
            (m, SR),
            alinear((m, SR)),
            lambda g: pedidas.append(g) or (m, SR),
            alinear,
        )
        self.assertEqual((pedidas, r["quedan"]), ([], []))
        self.assertIs(r["toma"][0], m)


class VozFallidaTest(unittest.TestCase):
    """20 'sigue la pausa rota' and 21 'Pronunciación sin revisar' exits in the session logs (to 21-nov):
    both leave a voice.mp3 on disk (the best broken take, or the OLD one after --forzar) that producir built."""

    def test_un_fallo_con_voz_en_disco_bloquea_hasta_una_voz_limpia(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as d:
            proy = Path(d)
            (proy / "assets").mkdir()
            with self.assertRaises(SystemExit):
                V.fallar(proy, "✗ Pronunciación sin revisar, no se sintetiza")
            self.assertIsNone(
                V.fallida(proy)
            )  # no voice on disk: producir synthesises it itself
            (proy / "assets" / "voice.mp3").write_bytes(b"old take")
            self.assertIn("Pronunciación", V.fallida(proy))
            (proy / "assets" / V.FALLO).unlink()  # what a clean voz.py run does
            self.assertIsNone(V.fallida(proy))


if __name__ == "__main__":
    unittest.main()
