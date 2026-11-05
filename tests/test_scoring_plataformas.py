"""v3: a score needs enough views on some platform, and it reads Facebook and Instagram too."""

import sqlite3
import unittest

from omega.creative import decisions, production_dna, scoring


class ScorePorPlataforma(unittest.TestCase):
    def setUp(self):
        self.con = sqlite3.connect(":memory:")
        self.con.row_factory = sqlite3.Row
        decisions.init(self.con)
        production_dna.init(self.con)
        production_dna.record_dna(
            self.con,
            production_ref="r",
            blocks=[{"block": "b", "technique": "t", "length_s": 40}],
            length_s=40,
        )

    def test_pocas_vistas_con_repeticiones_no_puntua(self):
        # housing-turn: 13 views at 130 % watched scored 0.705 under v2.
        production_dna.record_analytics(
            self.con, production_ref="r", retention_avg=1.0, views=13
        )
        with self.assertRaises(scoring.MuestraInsuficiente):
            scoring.desde_analytics(self.con, "r")

    def test_cuenta_meta_aunque_youtube_tenga_poco(self):
        # binance-heist: YouTube 5 views at 0 % scored 0.002 despite 195 views on Meta.
        production_dna.record_analytics(
            self.con, production_ref="r", retention_avg=0.0, views=5
        )
        production_dna.record_social(
            self.con, "r", "facebook", {"views": 80, "avg_watch_s": 4.0}
        )
        production_dna.record_social(
            self.con, "r", "instagram", {"views": 120, "avg_watch_s": 8.0}
        )
        score, partes = scoring.desde_analytics(self.con, "r")
        self.assertAlmostEqual(partes["retencion"], (80 * 0.1 + 120 * 0.2) / 200)
        self.assertEqual(partes["views"], 205)
        self.assertFalse(partes["plataformas"]["youtube"]["cuenta"])
        self.assertTrue(partes["plataformas"]["instagram"]["cuenta"])
        self.assertGreater(score, 0.1)

    def test_solo_meta_puntua_sin_fila_de_youtube(self):
        production_dna.record_social(
            self.con, "r", "facebook", {"views": 300, "avg_watch_s": 12.0}
        )
        _, partes = scoring.desde_analytics(self.con, "r")
        self.assertAlmostEqual(partes["retencion"], 0.3)

    def test_guarda_se_quedaron_de_youtube(self):
        production_dna.record_analytics(
            self.con,
            production_ref="r",
            retention_avg=0.42,
            views=56,
            engaged_views=21,
        )
        _, partes = scoring.desde_analytics(self.con, "r")
        self.assertAlmostEqual(partes["plataformas"]["youtube"]["se_quedaron"], 0.375)

    def test_tiempo_visto_con_bucles_no_pasa_de_uno(self):
        production_dna.record_social(
            self.con, "r", "facebook", {"views": 50, "avg_watch_s": 90.0}
        )
        _, partes = scoring.desde_analytics(self.con, "r")
        self.assertEqual(partes["retencion"], 1.0)


if __name__ == "__main__":
    unittest.main()
