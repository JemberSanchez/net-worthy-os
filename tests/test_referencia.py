"""Tests de video-v2/motor/referencia.py y del dataset research/referencia_nicho.json."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "video-v2" / "motor"))

import guionista as G
import referencia as R

# referencia sintética: duraciones 10, 20, ..., 90 s (mediana 50)
REF = [{"dur_s": s} for s in range(10, 100, 10)]


def guion_de(segundos: float) -> list[str]:
    return ["word " * round(segundos * G.PALABRAS_POR_S)]


class TestPercentil(unittest.TestCase):
    def test_rango_medio_con_empates(self):
        self.assertEqual(R.percentil(50, [10, 50, 90]), 0.5)
        self.assertEqual(R.percentil(5, [10, 50, 90]), 0.0)
        self.assertEqual(R.percentil(100, [10, 50, 90]), 1.0)

    def test_cuartiles(self):
        self.assertEqual(R.cuartiles([r["dur_s"] for r in REF]), (30, 70))


class TestDistancia(unittest.TestCase):
    def test_cero_en_la_mediana_y_uno_fuera_del_rango(self):
        self.assertEqual(R.distancia(guion_de(50), REF)["distancia"], 0.0)
        self.assertEqual(R.distancia(guion_de(200), REF)["distancia"], 1.0)
        self.assertEqual(R.distancia(guion_de(2), REF)["distancia"], 1.0)

    def test_mas_cerca_de_la_mediana_es_menor(self):
        self.assertLess(
            R.distancia(guion_de(45), REF)["distancia"],
            R.distancia(guion_de(25), REF)["distancia"],
        )

    def test_acepta_dicts_de_storyboard(self):
        frases = [{"id": "a", "texto": t} for t in guion_de(50)]
        self.assertEqual(R.distancia(frases, REF)["distancia"], 0.0)


class TestPuertasCalibradas(unittest.TestCase):
    def test_largo_usa_rango_de_la_referencia(self):
        # p25-p75 = 30-70 s -> 93-217 palabras: 60 s pasa, 80 s (248 palabras) falla
        dentro = {p["id"]: p for p in R.puertas_calibradas(guion_de(60), REF)}
        fuera = {p["id"]: p for p in R.puertas_calibradas(guion_de(80), REF)}
        self.assertTrue(dentro["G-LARGO"]["ok"] and dentro["G-LARGO"]["calibrada"])
        self.assertFalse(fuera["G-LARGO"]["ok"])
        self.assertFalse(dentro["G-CIFRA"]["calibrada"])


class TestDataset(unittest.TestCase):
    def test_versionado_con_metricas_y_urls(self):
        ref = R.cargar()
        self.assertGreaterEqual(len(ref), 20)
        for r in ref:
            self.assertTrue(r["url"].startswith("https://youtube.com/shorts/"))
            self.assertTrue(0 < r["dur_s"] <= 180)
            self.assertGreater(r["views"], 0)


if __name__ == "__main__":
    unittest.main()
