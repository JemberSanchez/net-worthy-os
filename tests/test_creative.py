"""Tests de Creative Intelligence v0: vocabulario controlado, justificación obligatoria y
calibración creativa (el aprendizaje real de qué patrones funcionan)."""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega.reasoning import store                           # noqa: E402  (solo para abrir SQLite)
from omega.creative import (patterns, decisions, combinator, reasoning_loop,  # noqa: E402
                            production, tradeoffs, experiments)


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


    def test_propose_compares_options_and_picks_best(self):
        idea = reasoning_loop.start(self.con, subject="x", content="base",
                                    tags=["curiosity_gap"])
        r = reasoning_loop.propose(self.con, idea, step="expand", options=[
            {"content": "opción floja", "tags": ["curiosity_gap"]},
            {"content": "opción fuerte",
             "tags": ["curiosity_gap", "twist", "stakes", "novel_combination"], "novelty": 0.5},
            {"content": "opción media", "tags": ["curiosity_gap", "twist"]},
        ])
        self.assertEqual(r["n_options"], 3)
        self.assertTrue(r["improved"])
        self.assertEqual(r["chosen"], "opción fuerte")  # eligió la mejor entre todas
        imp = reasoning_loop.improvement(self.con, idea)
        self.assertGreater(imp["final"], imp["initial"])


class ProductionTest(unittest.TestCase):
    def setUp(self):
        self.con = store.connect(":memory:")
        for mod in (patterns, reasoning_loop, production):
            mod.init(self.con)
        patterns.seed(self.con)

    def tearDown(self):
        self.con.close()

    def _component(self, name, tags, novelty=0.0):
        return reasoning_loop.start(self.con, subject=name, content=name,
                                    tags=tags, novelty=novelty)

    def _build(self):
        pid = production.create_production(self.con, subject="tiburones")
        idea = self._component("idea", ["curiosity_gap", "novel_combination", "twist"], 0.5)  # fuerte
        hook = self._component("hook", ["curiosity_gap"])                                      # débil
        production.add_component(self.con, pid, component_type="idea", idea_id=idea)
        production.add_component(self.con, pid, component_type="hook", idea_id=hook)
        return pid

    def test_bottleneck_is_the_weakest_component(self):
        pid = self._build()
        b = production.bottleneck(self.con, pid)
        self.assertEqual(b["component_type"], "hook")
        # calidad de la producción = eslabón más débil
        self.assertEqual(production.production_quality(self.con, pid), b["score"])

    def test_fixing_only_the_bottleneck_raises_quality(self):
        pid = self._build()
        before = production.production_quality(self.con, pid)
        b = production.bottleneck(self.con, pid)
        # rehace SOLO el cuello de botella (el hook), no toca la idea
        reasoning_loop.advance(self.con, b["idea_id"], step="refine", content="hook mejor",
                               tags=["curiosity_gap", "strong_hook_3s", "open_loop"])
        after = production.production_quality(self.con, pid)
        self.assertGreater(after, before)


class TradeoffTest(unittest.TestCase):
    def setUp(self):
        self.con = store.connect(":memory:")
        tradeoffs.init(self.con)

    def tearDown(self):
        self.con.close()

    def test_detects_conflicting_goals(self):
        # intentar 'hook que revela pronto' Y 'guardar el giro' es una tensión
        conflicts = tradeoffs.detect_conflicts(["strong_hook_3s", "twist", "curiosity_gap"])
        pairs = {(c["a"], c["b"]) for c in conflicts}
        self.assertIn(("strong_hook_3s", "twist"), pairs)

    def test_no_conflict_when_goals_are_compatible(self):
        self.assertEqual(tradeoffs.detect_conflicts(["curiosity_gap", "novel_combination"]), [])

    def test_resolution_requires_a_reason(self):
        with self.assertRaises(ValueError):
            tradeoffs.record_resolution(self.con, ref="v1", kept="twist",
                                        sacrificed="strong_hook_3s", reason="  ")

    def test_resolution_is_logged(self):
        rid = tradeoffs.record_resolution(self.con, ref="v1", kept="twist",
                                          sacrificed="strong_hook_3s",
                                          reason="el payoff vale más que un hook agresivo")
        self.assertIsInstance(rid, int)


class StopOptimizationTest(unittest.TestCase):
    def setUp(self):
        self.con = store.connect(":memory:")
        for mod in (patterns, reasoning_loop):
            mod.init(self.con)

    def tearDown(self):
        self.con.close()

    def _idea_with_scores(self, scores):
        """Inserta una idea con versiones aceptadas de scores dados (test de la lógica de parada)."""
        iid = self.con.execute("INSERT INTO idea (subject, created_at) VALUES ('x',0)").lastrowid
        for n, sc in enumerate(scores):
            self.con.execute(
                "INSERT INTO idea_version (idea_id, version_no, step, content, pattern_tags, "
                "novelty, craft_score, accepted, created_at) VALUES (?,?,?,?,?,?,?,1,0)",
                (iid, n, "refine", "c", "[]", 0, sc))
        self.con.commit()
        return iid

    def test_stops_on_diminishing_returns(self):
        iid = self._idea_with_scores([0.32, 0.61, 0.78, 0.84, 0.85, 0.851])
        r = reasoning_loop.should_stop(self.con, iid)
        self.assertTrue(r["stop"])  # últimas mejoras 0.01 y 0.001 < 0.02

    def test_keeps_going_while_improving(self):
        iid = self._idea_with_scores([0.20, 0.40, 0.60, 0.80])
        r = reasoning_loop.should_stop(self.con, iid)
        self.assertFalse(r["stop"])  # aún sube 0.20 por paso


class CreativeExperimentTest(unittest.TestCase):
    def setUp(self):
        self.con = store.connect(":memory:")
        experiments.init(self.con)

    def tearDown(self):
        self.con.close()

    def _exp(self):
        return experiments.design(
            self.con, hypothesis="hook emocional > misterioso (terror 60s)", variable="hook",
            context={"emotion": "fear", "duration": "60s"},
            variants=[{"label": "emocional", "tags": ["empathy"]},
                      {"label": "misterioso", "tags": ["curiosity_gap"]}])

    def test_design_requires_two_variants(self):
        with self.assertRaises(ValueError):
            experiments.design(self.con, hypothesis="h", variable="hook",
                               variants=[{"label": "solo"}])

    def test_significant_result_declares_winner(self):
        eid = self._exp()
        experiments.record_result(self.con, experiment_id=eid, label="emocional",
                                  impressions=1000, successes=100)   # 10%
        experiments.record_result(self.con, experiment_id=eid, label="misterioso",
                                  impressions=1000, successes=50)    # 5%
        r = experiments.resolve(self.con, eid)
        self.assertTrue(r["significant"])
        self.assertEqual(r["winner"], "emocional")
        self.assertEqual(r["status"], "resolved")

    def test_underpowered_result_is_inconclusive(self):
        """El guard estadístico: con muestra pequeña, NO se declara ganador (no se aprende ruido)."""
        eid = self._exp()
        experiments.record_result(self.con, experiment_id=eid, label="emocional",
                                  impressions=50, successes=5)       # 10% pero N pequeño
        experiments.record_result(self.con, experiment_id=eid, label="misterioso",
                                  impressions=50, successes=4)       # 8%
        r = experiments.resolve(self.con, eid)
        self.assertFalse(r["significant"])
        self.assertIsNone(r["winner"])
        self.assertEqual(r["status"], "inconclusive")

    def test_invalid_result_rejected(self):
        eid = self._exp()
        with self.assertRaises(ValueError):
            experiments.record_result(self.con, experiment_id=eid, label="emocional",
                                      impressions=10, successes=20)  # successes > impressions


if __name__ == "__main__":
    unittest.main(verbosity=2)
