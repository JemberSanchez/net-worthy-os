"""Tests del flujo de decisión end-to-end (kernel) + explicabilidad obligatoria.

Usa hipótesis sintéticas (deterministas) para no depender de RSS. Valida: pursue, abstain,
promoción a belief + predicción, y que explain() reconstruye el razonamiento.
"""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega.reasoning import (store, hypotheses, opportunities, decisions,  # noqa: E402
                             decision_engine)

WEIGHTS = {"momentum": 0.05, "prevalence": 0.0, "contradiction": -0.30}


class DecisionFlowTest(unittest.TestCase):
    def setUp(self):
        self.con = store.connect(":memory:")
        for mod in (store, hypotheses, opportunities, decisions):
            mod.init(self.con)

    def tearDown(self):
        self.con.close()

    def _cand(self, term, conf, momentum, prevalence, contradiction=0.0):
        return hypotheses.create_hypothesis(
            self.con, domain="content", statement=f"Demanda creciente en torno a '{term}'",
            confidence=conf, evidence={
                "features": {"momentum": momentum, "prevalence": prevalence,
                             "contradiction": contradiction},
                "signals": [{"name": "theme", "value": term, "count": prevalence}],
                "for": [f"'{term}' aparece en {prevalence} items"],
                "against": (["señal mixta"] if contradiction else []),
            })

    def test_pursue_creates_opportunity_belief_and_prediction(self):
        self._cand("ai", 0.70, 1.0, 30)
        self._cand("blockchain", 0.40, 0.2, 5)
        r = decision_engine.decide(self.con, domain="content", weights=WEIGHTS,
                                   abstain_threshold=0.5)
        self.assertEqual(r["decision"], "pursue")
        # se creó una predicción falsable ligada a una belief tracked
        pred = self.con.execute("SELECT * FROM prediction WHERE id=?", (r["prediction_id"],)).fetchone()
        self.assertIsNotNone(pred["refutation_criterion"])
        self.assertGreater(pred["expected_verification_at"], 0)
        hist = store.belief_history(self.con, r["belief_id"])
        self.assertEqual(hist[0]["cause_type"], "created")

    def test_abstain_when_below_threshold(self):
        self._cand("weak1", 0.30, 0.1, 4)
        self._cand("weak2", 0.35, 0.0, 3)
        r = decision_engine.decide(self.con, domain="content", weights=WEIGHTS,
                                   abstain_threshold=0.5)
        self.assertEqual(r["decision"], "abstain")
        self.assertEqual(self.con.execute("SELECT COUNT(*) n FROM opportunity").fetchone()["n"], 0)
        self.assertEqual(self.con.execute("SELECT COUNT(*) n FROM prediction").fetchone()["n"], 0)

    def test_abstain_with_no_candidates(self):
        r = decision_engine.decide(self.con, domain="content", weights=WEIGHTS,
                                   abstain_threshold=0.5)
        self.assertEqual(r["decision"], "abstain")

    def test_contradiction_penalizes_score(self):
        """La misma confianza, pero con contradicción, baja el score (evidencia en contra pesa)."""
        self._cand("clean", 0.60, 0.0, 10, contradiction=0.0)
        self._cand("mixed", 0.60, 0.0, 10, contradiction=1.0)
        r = decision_engine.decide(self.con, domain="content", weights=WEIGHTS,
                                   abstain_threshold=0.0)
        e = decisions.explain(self.con, r["decision_id"])
        self.assertEqual(e["why"]["statement"], "Demanda creciente en torno a 'clean'")

    def test_explainability_reconstructs_reasoning(self):
        self._cand("ai", 0.72, 1.0, 40)
        self._cand("nft", 0.50, 0.3, 6)
        r = decision_engine.decide(self.con, domain="content", weights=WEIGHTS,
                                   abstain_threshold=0.5)
        e = decisions.explain(self.con, r["decision_id"])
        self.assertEqual(e["decision"], "pursue")
        self.assertIn("ai", e["why"]["statement"])
        self.assertTrue(e["originating_signals"])              # qué señales la originaron
        self.assertTrue(e["evidence_for"])                     # evidencia a favor
        self.assertTrue(any("nft" in d["statement"] for d in e["discarded_hypotheses"]))  # descartadas
        self.assertIsNotNone(e["prediction"])                  # predicción falsable
        self.assertGreaterEqual(e["uncertainty"], 0.0)         # incertidumbre restante
        # y se renderiza sin romper
        self.assertIn("DECISIÓN", decisions.render_explanation(e))


if __name__ == "__main__":
    unittest.main(verbosity=2)
