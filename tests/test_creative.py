"""Tests de Creative Intelligence v0: vocabulario controlado, justificación obligatoria y
calibración creativa (el aprendizaje real de qué patrones funcionan)."""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega.reasoning import store               # noqa: E402  (solo para abrir SQLite)
from omega.creative import patterns, decisions  # noqa: E402


class CreativeTest(unittest.TestCase):
    def setUp(self):
        self.con = store.connect(":memory:")
        patterns.init(self.con)
        decisions.init(self.con)
        patterns.seed(self.con)

    def tearDown(self):
        self.con.close()

    def test_ckb_is_seeded(self):
        vocab = patterns.vocabulary(self.con)
        self.assertIn("curiosity_gap", vocab)
        self.assertIn("novel_combination", vocab)
        self.assertGreaterEqual(len(vocab), 15)

    # --- Every Creative Decision Needs a Reason -----------------------------

    def test_decision_requires_a_reason(self):
        with self.assertRaises(ValueError):
            decisions.record_decision(self.con, production_ref="v1", decision_type="hook",
                                      choice="Empieza con una pregunta", pattern_tags=[])

    def test_reason_must_come_from_controlled_vocabulary(self):
        # texto libre inventado -> rechazado (si no, la calibración sería imposible)
        with self.assertRaises(ValueError):
            decisions.record_decision(self.con, production_ref="v1", decision_type="hook",
                                      choice="algo", pattern_tags=["porque_mola"])

    def test_valid_decision_is_recorded(self):
        did = decisions.record_decision(
            self.con, production_ref="v1", decision_type="hook",
            choice="¿Y si un tiburón apareciera en una piscina olímpica?",
            pattern_tags=["curiosity_gap", "novel_combination"])
        self.assertIsInstance(did, int)

    # --- Calibración creativa: reproduce "curiosity_gap 81% vs shock 44%" ---

    def test_pattern_calibration_learns_what_works(self):
        # 10 videos con curiosity_gap, 8 funcionan -> 0.8
        for i in range(10):
            ref = f"cg{i}"
            decisions.record_decision(self.con, production_ref=ref, decision_type="hook",
                                      choice="hook", pattern_tags=["curiosity_gap"])
            decisions.record_outcome(self.con, ref, 1.0 if i < 8 else 0.0)
        # 9 videos con shock, 4 funcionan -> ~0.44
        for i in range(9):
            ref = f"sh{i}"
            decisions.record_decision(self.con, production_ref=ref, decision_type="hook",
                                      choice="hook", pattern_tags=["shock"])
            decisions.record_outcome(self.con, ref, 1.0 if i < 4 else 0.0)

        cal = {c["pattern"]: c for c in decisions.pattern_calibration(self.con)}
        self.assertEqual(cal["curiosity_gap"]["success_rate"], 0.8)
        self.assertEqual(cal["shock"]["success_rate"], 0.444)
        # y el ranking pone curiosity_gap por delante de shock (aprendizaje creativo real)
        ranked = [c["pattern"] for c in decisions.pattern_calibration(self.con)]
        self.assertLess(ranked.index("curiosity_gap"), ranked.index("shock"))

    def test_calibration_only_counts_measured_productions(self):
        # decisión sin outcome medido -> no entra en la calibración (no se predice nada)
        decisions.record_decision(self.con, production_ref="nomeasure", decision_type="hook",
                                  choice="hook", pattern_tags=["twist"])
        self.assertEqual(decisions.pattern_calibration(self.con), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
