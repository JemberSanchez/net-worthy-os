"""Tests de Hypothesis y Opportunity (entidades del kernel) y del gate de promoción."""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega.reasoning import store, hypotheses, opportunities  # noqa: E402


class PipelineEntitiesTest(unittest.TestCase):
    def setUp(self):
        self.con = store.connect(":memory:")
        store.init(self.con)
        hypotheses.init(self.con)
        opportunities.init(self.con)

    def tearDown(self):
        self.con.close()

    # --- Hypothesis: tier de candidatas + gate de promoción -----------------

    def test_hypotheses_start_as_candidates(self):
        hid = hypotheses.create_hypothesis(self.con, domain="content",
                                           statement="Demanda creciente de tutoriales de IA",
                                           confidence=0.73)
        cands = hypotheses.list_candidates(self.con, "content")
        self.assertEqual([c["id"] for c in cands], [hid])

    def test_promotion_creates_tracked_belief(self):
        """El gate de promoción: una hipótesis se convierte en Belief (nace en la apuesta)."""
        hid = hypotheses.create_hypothesis(self.con, domain="content",
                                           statement="X crece", confidence=0.70)
        bid = hypotheses.promote_to_belief(self.con, hid)
        # nace una creencia tracked, con su primer evento en el log (No Silent Learning)
        hist = store.belief_history(self.con, bid)
        self.assertEqual(len(hist), 1)
        self.assertEqual(hist[0]["cause_type"], "created")
        # la hipótesis queda marcada y enlazada; ya no es candidata
        h = self.con.execute("SELECT * FROM hypothesis WHERE id=?", (hid,)).fetchone()
        self.assertEqual(h["status"], "promoted")
        self.assertEqual(h["promoted_belief_id"], bid)
        self.assertEqual(hypotheses.list_candidates(self.con, "content"), [])

    def test_cannot_promote_twice(self):
        hid = hypotheses.create_hypothesis(self.con, domain="content",
                                           statement="X", confidence=0.6)
        hypotheses.promote_to_belief(self.con, hid)
        with self.assertRaises(ValueError):
            hypotheses.promote_to_belief(self.con, hid)

    def test_discard_removes_from_candidates(self):
        hid = hypotheses.create_hypothesis(self.con, domain="content",
                                           statement="ruido", confidence=0.3)
        hypotheses.discard(self.con, hid)
        self.assertEqual(hypotheses.list_candidates(self.con, "content"), [])

    # --- Opportunity: output domain-agnostic, cardinalidad N ----------------

    def test_opportunities_are_domain_agnostic_payload(self):
        oid = opportunities.create_opportunity(
            self.con, domain="content", confidence=0.82, value_level=0.9, risk=0.2,
            attributes={"theme": "ai", "problem": "aprender ia", "audience": "principiantes"})
        row = self.con.execute("SELECT * FROM opportunity WHERE id=?", (oid,)).fetchone()
        # el kernel guarda atributos como JSON opaco; no hay columnas tipadas de dominio
        self.assertIn("theme", row["attributes"])
        self.assertEqual(row["status"], "open")

    def test_many_opportunities_one_gets_pursued(self):
        ids = [opportunities.create_opportunity(self.con, domain="content",
               confidence=0.5 + i * 0.1, value_level=0.4 + i * 0.2) for i in range(3)]
        # se surfacearon 3; el Decision Engine perseguirá la mejor y rechazará el resto
        best = opportunities.list_open(self.con, "content")[0]
        self.assertEqual(best["id"], ids[-1])  # mayor value_level primero
        opportunities.set_status(self.con, best["id"], "pursued")
        for other in ids[:-1]:
            opportunities.set_status(self.con, other, "rejected")
        self.assertEqual(opportunities.list_open(self.con, "content"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
