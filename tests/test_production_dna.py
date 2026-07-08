"""Tests de la instrumentación de ADN de producción: el dataset rico por video.

Validan: round-trip del ADN (block_count derivado), analíticas, y la calibración por dimensión
con su GUARD de rigor (marca 'provisional' cuando n es bajo — con pocos datos es ruido, no ley).
"""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega.reasoning import store  # noqa: E402
from omega.creative import production_dna, decisions  # noqa: E402


class ProductionDnaTest(unittest.TestCase):
    def setUp(self):
        self.con = store.connect(":memory:")
        for mod in (production_dna, decisions):
            mod.init(self.con)

    def tearDown(self):
        self.con.close()

    def test_record_and_fetch_dna_derives_block_count(self):
        production_dna.record_dna(
            self.con, production_ref="v1", hook_type="story", story_type="character",
            cta_type="session", length_s=450,
            blocks=[{"block": "hook", "technique": "two_men", "length_s": 35},
                    {"block": "proof", "technique": "compound_curve", "length_s": 135}])
        d = production_dna.fetch_dna(self.con, "v1")
        self.assertEqual(d["block_count"], 2)
        self.assertEqual(d["hook_type"], "story")
        self.assertEqual(d["blocks"][1]["technique"], "compound_curve")

    def test_analytics_round_trip(self):
        production_dna.record_dna(self.con, production_ref="v1", blocks=[])
        production_dna.record_analytics(
            self.con, production_ref="v1", ctr=0.06, avd_pct=0.52, retention_avg=0.48,
            traffic_source="browse", retention_by_block={"hook": 0.85, "proof": 0.6})
        r = self.con.execute("SELECT * FROM production_analytics WHERE production_ref='v1'").fetchone()
        self.assertAlmostEqual(r["ctr"], 0.06)
        self.assertEqual(r["traffic_source"], "browse")

    def test_dna_calibration_groups_by_dimension_and_needs_outcome(self):
        # dos videos story + uno stat; solo cuentan los que tienen outcome medido
        for ref, hook in [("a", "story"), ("b", "story"), ("c", "stat")]:
            production_dna.record_dna(self.con, production_ref=ref, hook_type=hook, blocks=[])
        decisions.record_outcome(self.con, "a", 0.8)
        decisions.record_outcome(self.con, "b", 0.6)
        decisions.record_outcome(self.con, "c", 0.2)
        cal = {c["value"]: c for c in production_dna.dna_calibration(self.con, "hook_type")}
        self.assertAlmostEqual(cal["story"]["success_rate"], 0.7)  # (0.8+0.6)/2
        self.assertEqual(cal["story"]["n"], 2)
        self.assertAlmostEqual(cal["stat"]["success_rate"], 0.2)

    def test_low_n_is_flagged_provisional(self):
        production_dna.record_dna(self.con, production_ref="a", hook_type="story", blocks=[])
        decisions.record_outcome(self.con, "a", 0.9)
        cal = production_dna.dna_calibration(self.con, "hook_type")
        self.assertTrue(cal[0]["provisional"])  # n=1 -> provisional: no es conclusión, es ruido

    def test_invalid_dimension_rejected(self):
        with self.assertRaises(ValueError):
            production_dna.dna_calibration(self.con, "b_roll")  # no está en la whitelist


if __name__ == "__main__":
    unittest.main(verbosity=2)
