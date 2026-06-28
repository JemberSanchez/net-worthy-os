"""Tests de Creative Intelligence v0: vocabulario controlado, justificación obligatoria y
calibración creativa (el aprendizaje real de qué patrones funcionan)."""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega.reasoning import store                           # noqa: E402  (solo para abrir SQLite)
from omega.creative import patterns, decisions, combinator, reasoning_loop  # noqa: E402


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

    # --- CKB multi-dimensional: la tasa de un patrón depende del CONTEXTO ----

    def test_conditional_calibration_by_context(self):
        # mismo patrón (curiosity_gap), distinto resultado segun la emoción del video
        decisions.record_decision(self.con, production_ref="a", decision_type="hook",
                                  choice="h", pattern_tags=["curiosity_gap"])
        decisions.record_outcome(self.con, "a", 1.0)
        decisions.record_context(self.con, "a", {"emotion": "awe", "duration": "short"})

        decisions.record_decision(self.con, production_ref="b", decision_type="hook",
                                  choice="h", pattern_tags=["curiosity_gap"])
        decisions.record_outcome(self.con, "b", 0.0)
        decisions.record_context(self.con, "b", {"emotion": "shock", "duration": "short"})

        # global: curiosity_gap = 0.5
        overall = {c["pattern"]: c for c in decisions.pattern_calibration(self.con)}
        self.assertEqual(overall["curiosity_gap"]["success_rate"], 0.5)
        # condicionado a emoción=awe -> 1.0; a emoción=shock -> 0.0 (memoria multi-dimensional)
        awe = {c["pattern"]: c for c in
               decisions.pattern_calibration(self.con, context_filter={"emotion": "awe"})}
        shock = {c["pattern"]: c for c in
                 decisions.pattern_calibration(self.con, context_filter={"emotion": "shock"})}
        self.assertEqual(awe["curiosity_gap"]["success_rate"], 1.0)
        self.assertEqual(shock["curiosity_gap"]["success_rate"], 0.0)


class CombinatorTest(unittest.TestCase):
    def setUp(self):
        self.con = store.connect(":memory:")
        combinator.init(self.con)

    def tearDown(self):
        self.con.close()

    def test_generates_k_distinct_combinations(self):
        combos = combinator.generate(self.con, "historia romana", k=5)
        self.assertEqual(len(combos), 5)
        self.assertEqual(len({c["treatment"] for c in combos}), 5)  # todos distintos

    def test_obvious_treatment_ranks_low(self):
        # 'historia' -> default 'documentary' (cliché) debe quedar penalizado
        combos = combinator.generate(self.con, "historia romana", k=12)
        by_t = {c["treatment"]: c for c in combos}
        self.assertTrue(by_t["documentary"]["is_default"])
        self.assertLess(by_t["documentary"]["novelty"], by_t["anime"]["novelty"])

    def test_used_combination_loses_novelty(self):
        before = {c["treatment"]: c["novelty"]
                  for c in combinator.generate(self.con, "gatos", k=12)}
        combinator.record_use(self.con, "gatos", "anime")
        after = {c["treatment"]: c["novelty"]
                 for c in combinator.generate(self.con, "gatos", k=12)}
        # tras usar 'anime' para 'gatos', su novedad baja -> el sistema busca lo fresco
        self.assertLess(after["anime"], before["anime"])


class ReasoningLoopTest(unittest.TestCase):
    def setUp(self):
        self.con = store.connect(":memory:")
        for mod in (patterns, decisions, reasoning_loop):
            mod.init(self.con)
        patterns.seed(self.con)

    def tearDown(self):
        self.con.close()

    def test_idea_improves_through_the_loop(self):
        # idea mediocre: 1 patrón de craft
        idea = reasoning_loop.start(self.con, subject="tiburones",
                                    content="Un video sobre tiburones",
                                    tags=["curiosity_gap"])
        # paso 'combine': más craft + novedad -> mejora y se acepta
        r = reasoning_loop.advance(self.con, idea, step="combine",
                                   content="Un tiburón en una piscina olímpica, como thriller",
                                   tags=["curiosity_gap", "novel_combination", "tension"],
                                   novelty=0.5)
        self.assertTrue(r["accepted"])
        self.assertGreater(r["delta"], 0)
        imp = reasoning_loop.improvement(self.con, idea)
        self.assertGreater(imp["final"], imp["initial"])
        self.assertGreater(imp["improvement"], 0)

    def test_weaker_version_is_not_accepted(self):
        idea = reasoning_loop.start(self.con, subject="x", content="fuerte",
                                    tags=["curiosity_gap", "twist", "stakes"], novelty=0.4)
        r = reasoning_loop.advance(self.con, idea, step="refine",
                                   content="aguada", tags=[])  # peor -> gate la rechaza
        self.assertFalse(r["accepted"])
        imp = reasoning_loop.improvement(self.con, idea)
        self.assertEqual(imp["final"], imp["initial"])  # la mejor versión sigue siendo la inicial

    def test_invalid_step_rejected(self):
        idea = reasoning_loop.start(self.con, subject="x", content="c", tags=["twist"])
        with self.assertRaises(ValueError):
            reasoning_loop.advance(self.con, idea, step="vibes", content="c")

    # --- CKB como mentor ----------------------------------------------------

    def test_ckb_advises_from_calibration(self):
        # sin datos: el mentor lo dice, no inventa
        self.assertFalse(patterns.advise(self.con)["calibrated"])
        # con un resultado real, 'curiosity_gap' aparece como lo que funciona aquí
        decisions.record_decision(self.con, production_ref="v1", decision_type="hook",
                                  choice="h", pattern_tags=["curiosity_gap"])
        decisions.record_outcome(self.con, "v1", 1.0)
        adv = patterns.advise(self.con, used_tags=["curiosity_gap"])
        self.assertTrue(adv["calibrated"])
        self.assertIn("curiosity_gap", [w["pattern"] for w in adv["works_here"]])
        self.assertNotIn("curiosity_gap", adv["untested"])  # ya usado/calibrado


if __name__ == "__main__":
    unittest.main(verbosity=2)
