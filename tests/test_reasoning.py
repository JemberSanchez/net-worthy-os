"""Tests del kernel Reasoning Engine.

Verifican que las reglas transversales son inviolables por construcción, no por convención.
Ejecutar desde la raíz del proyecto:  python -m unittest tests.test_reasoning  -v
"""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega.reasoning import store  # noqa: E402

DAY = 86400


class ReasoningKernelTest(unittest.TestCase):
    def setUp(self):
        self.con = store.connect(":memory:")
        store.init(self.con)

    def tearDown(self):
        self.con.close()

    # --- No Silent Learning -------------------------------------------------

    def test_create_belief_logs_initial_event(self):
        bid = store.create_belief(self.con, "content", "El humor absurdo está subiendo", 0.60)
        hist = store.belief_history(self.con, bid)
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["cause_type"], "created")
        self.assertEqual(hist[0]["new_confidence"], 0.60)

    def test_update_requires_rationale(self):
        bid = store.create_belief(self.con, "content", "X crece", 0.5)
        with self.assertRaises(ValueError):
            store.update_belief(self.con, bid, cause_type="human", rationale="  ",
                                new_confidence=0.6)

    def test_update_rejects_invalid_cause(self):
        bid = store.create_belief(self.con, "content", "X crece", 0.5)
        with self.assertRaises(ValueError):
            store.update_belief(self.con, bid, cause_type="vibes", rationale="porque sí",
                                new_confidence=0.6)

    def test_confidence_only_changes_through_logged_update(self):
        bid = store.create_belief(self.con, "content", "X crece", 0.50)
        store.update_belief(self.con, bid, cause_type="evidence_drift",
                            rationale="El patrón dejó de aparecer 3 días seguidos.",
                            new_confidence=0.38)
        # confianza cambió...
        row = self.con.execute("SELECT confidence FROM belief WHERE id=?", (bid,)).fetchone()
        self.assertAlmostEqual(row["confidence"], 0.38)
        # ...y dejó rastro explícito con su causa (no hay cambio silencioso posible)
        hist = store.belief_history(self.con, bid)
        self.assertEqual(len(hist), 2)
        self.assertEqual(hist[1]["old_confidence"], 0.50)
        self.assertEqual(hist[1]["new_confidence"], 0.38)
        self.assertEqual(hist[1]["cause_type"], "evidence_drift")
        self.assertIn("patrón", hist[1]["rationale"])

    # --- Every belief is a prediction ---------------------------------------

    def test_prediction_requires_falsifiability(self):
        # sin criterio de refutación -> no es una predicción
        with self.assertRaises(ValueError):
            store.create_prediction(self.con, domain="content",
                                    statement="El nicho crecerá", confidence=0.7,
                                    verification_method="comparar vistas en 30d",
                                    refutation_criterion="",
                                    expected_verification_at=int(1e9))
        # sin fecha esperada -> tampoco
        with self.assertRaises(ValueError):
            store.create_prediction(self.con, domain="content",
                                    statement="El nicho crecerá", confidence=0.7,
                                    verification_method="comparar vistas en 30d",
                                    refutation_criterion="refutada si <+15%",
                                    expected_verification_at=0)

    def test_resolution_does_not_silently_update_belief(self):
        """Resolver una predicción NO toca la creencia: el aprendizaje es un paso explícito."""
        now = 1_000_000
        bid = store.create_belief(self.con, "content", "Tema T satura pronto", 0.70, now=now)
        pid = store.create_prediction(self.con, domain="content", belief_id=bid,
                                      statement="Presencia de T cae >20% en 30d",
                                      confidence=0.70,
                                      verification_method="DF en RSS/YouTube a 30d",
                                      refutation_criterion="refutada si caída <20%",
                                      expected_verification_at=now + 30 * DAY, now=now)
        store.resolve_prediction(self.con, pid, outcome="refuted",
                                 note="Cayó solo 8%.", now=now + 30 * DAY)
        # la creencia sigue intacta hasta que se decida actualizarla explícitamente
        row = self.con.execute("SELECT confidence FROM belief WHERE id=?", (bid,)).fetchone()
        self.assertAlmostEqual(row["confidence"], 0.70)
        self.assertEqual(len(store.belief_history(self.con, bid)), 1)
        # ahora el paso explícito de aprendizaje, citando la predicción como causa
        store.update_belief(self.con, bid, cause_type="prediction_resolved",
                            rationale="Predicción de saturación refutada (cayó 8%, umbral 20%).",
                            new_confidence=0.55, cause_refs=[pid], now=now + 30 * DAY)
        hist = store.belief_history(self.con, bid)
        self.assertEqual(hist[1]["cause_type"], "prediction_resolved")
        self.assertIn(pid, __import__("json").loads(hist[1]["cause_refs"]))

    def test_due_predictions_flags_unverified(self):
        now = 2_000_000
        pid = store.create_prediction(self.con, domain="content",
                                      statement="A > B", confidence=0.6,
                                      verification_method="m", refutation_criterion="r",
                                      expected_verification_at=now - 1, now=now - DAY)
        due = store.due_predictions(self.con, now=now)
        self.assertEqual([d["id"] for d in due], [pid])
        store.resolve_prediction(self.con, pid, outcome="confirmed", now=now)
        self.assertEqual(store.due_predictions(self.con, now=now), [])

    # --- Calibración (el activo medible) ------------------------------------

    def test_calibration_reports_predicted_vs_actual(self):
        now = 3_000_000
        # 10 predicciones al 70%: 7 confirmadas, 3 refutadas -> banda 0.7 acierta 0.7
        for i in range(10):
            pid = store.create_prediction(self.con, domain="content",
                                          statement=f"p{i}", confidence=0.70,
                                          verification_method="m", refutation_criterion="r",
                                          expected_verification_at=now + 1, now=now)
            store.resolve_prediction(self.con, pid,
                                     outcome="confirmed" if i < 7 else "refuted", now=now + 1)
        cal = store.calibration(self.con, domain="content")
        band = next(b for b in cal if b["band"] == 0.7)
        self.assertEqual(band["n"], 10)
        self.assertAlmostEqual(band["actual_rate"], 0.7)


if __name__ == "__main__":
    unittest.main(verbosity=2)
