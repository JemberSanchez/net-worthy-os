"""Plan de síntesis por frase de video-v2/motor/voz.py: silencio dentro de una frase y velocidad."""
import importlib.util
import os
import unittest

import numpy as np

_ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "video-v2", "motor", "voz.py")
_spec = importlib.util.spec_from_file_location("voz_motor", _ruta)
V = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(V)


class TomasTest(unittest.TestCase):
    def test_corte_inserta_silencio_y_pausa_entre_frases(self):
        sb = {"guion": [{"id": "a", "texto": "One two."}, {"id": "b", "texto": "The lines crossed."}],
              "voz": {"speed": 0.9, "pausa_s": 0.3, "cortes": {"b": ["The lines", 0.7, "crossed."]}}}
        self.assertEqual(V.tomas(sb), [("One two.", 0.9), 0.3, ("The lines", 0.9), 0.7, ("crossed.", 0.9)])

    def test_speed_por_frase(self):
        sb = {"guion": [{"id": "a", "texto": "x"}, {"id": "b", "texto": "y"}], "voz": {"speed": {"a": 0.8, "*": 1.1}}}
        self.assertEqual([t[1] for t in V.tomas(sb) if isinstance(t, tuple)], [0.8, 1.1])

    def test_recortar_quita_silencio_de_extremos(self):
        m = np.concatenate([np.zeros(2400), np.ones(2400) * 0.5, np.zeros(2400)]).astype("float32")
        r = V.recortar(m, 24000, margen_s=0)
        self.assertEqual(len(r), 2400)


if __name__ == "__main__":
    unittest.main()
