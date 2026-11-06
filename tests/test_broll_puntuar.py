"""Candidate scoring in tools/broll.py (docs/mejora/metraje/SHOTLIST.md)."""

import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"),
)

import broll


def clip(titulo, descripcion, clase="pd", alto=1080, ancho=1920, fecha=""):
    return {
        "titulo": titulo,
        "descripcion": descripcion,
        "clase": clase,
        "alto": alto,
        "ancho": ancho,
        "fecha": fecha,
    }


CARRIER = clip(
    "USS Abraham Lincoln (CVN-72) Conducts Flight Operations (1016141).webm",
    "aircraft carrier conducting flight operations, July 21, 2026",
)


class TestPuntuar(unittest.TestCase):
    def test_real_mismatches_are_rejected(self):
        # aws-profit "servers" and fed-vs-card "washington", as credited in video-v2.
        rango = clip("pexels:6091131", "footage of a shooting range", "pexels")
        seattle = clip(
            "pexels:32160297", "seattle ferris wheel and downtown skyline", "pexels"
        )
        self.assertIsNone(broll.puntuar(rango, "server data center cloud"))
        self.assertIsNone(broll.puntuar(seattle, "washington capitol treasury"))

    def test_specific_beats_generic(self):
        generico = clip(
            "pexels:1", "businessman pointing at a laptop on an aircraft", "pexels"
        )
        terminos = "aircraft carrier flight operations"
        self.assertGreater(
            broll.puntuar(CARRIER, terminos), broll.puntuar(generico, terminos)
        )

    def test_gates(self):
        t = "aircraft carrier flight"
        self.assertIsNone(broll.puntuar({**CARRIER, "clase": None}, t))
        self.assertIsNone(broll.puntuar({**CARRIER, "alto": 720}, t))
        self.assertIsNone(broll.puntuar(CARRIER, t, veto=("July 21",)))

    def test_period_reused_and_portrait(self):
        t = "aircraft carrier flight"
        self.assertLess(
            broll.puntuar(CARRIER, t, anio=1980), broll.puntuar(CARRIER, t, anio=2026)
        )
        self.assertLess(
            broll.puntuar(CARRIER, t, vistos={CARRIER["titulo"]}),
            broll.puntuar(CARRIER, t),
        )
        self.assertIsNotNone(broll.puntuar({**CARRIER, "alto": 1920, "ancho": 1080}, t))


class UsadosTest(unittest.TestCase):
    def test_no_depende_del_directorio_actual(self):
        cwd = os.getcwd()
        desde_raiz = broll.usados()
        self.assertTrue(desde_raiz)
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        try:
            self.assertEqual(broll.usados(), desde_raiz)
        finally:
            os.chdir(cwd)


if __name__ == "__main__":
    unittest.main()
