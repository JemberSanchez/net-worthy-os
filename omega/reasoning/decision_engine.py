"""Kernel: Decision Engine v0 — elige entre hipótesis; no las inventa.

Puro y domain-agnostic: rankea candidatas con una función de scoring genérica parametrizada
por PESOS que aporta el dominio (Strategy Profile). El kernel hace el producto peso·feature
sin conocer el significado de las features. Si el mejor score < umbral, ABSTENERSE.

Flujo: hipótesis candidatas -> score -> Opportunity + Decision Record -> (apuesta) Belief +
Prediction. Las creencias nacen aquí, en la promoción.
"""
from __future__ import annotations
import json
import sqlite3
import time

from . import hypotheses, opportunities, store, decisions


def score(hyp_row: sqlite3.Row, weights: dict) -> tuple[float, dict]:
    """score = confianza + Σ peso·feature. El kernel no sabe qué significan las features."""
    ev = json.loads(hyp_row["evidence"]) if hyp_row["evidence"] else {}
    features = ev.get("features", {})
    contributions = {k: round(weights.get(k, 0.0) * float(v), 4) for k, v in features.items()}
    s = float(hyp_row["confidence"]) + sum(contributions.values())
    return max(0.0, round(s, 4)), contributions


def decide(con: sqlite3.Connection, *, domain: str, weights: dict,
           abstain_threshold: float, horizon_days: int = 14, now: int | None = None,
           instrument_version: str | None = None) -> dict:
    """instrument_version lo APORTA EL DOMINIO (el kernel no puede importar los extractores: lo
    prohíbe el test de pureza). Se sella en la predicción para que cerrarla más tarde con una
    versión distinta no pase por medición. Ver `store.resolve_prediction`."""
    now = now or int(time.time())
    cands = hypotheses.list_candidates(con, domain)
    scored = []
    for c in cands:
        s, contrib = score(c, weights)
        scored.append({"hypothesis_id": c["id"], "statement": c["statement"],
                       "confidence": c["confidence"], "score": s, "contributions": contrib})
    scored.sort(key=lambda x: x["score"], reverse=True)

    # --- Abstención: decisión válida de primera clase ---
    if not scored or scored[0]["score"] < abstain_threshold:
        reason = ("sin hipótesis candidatas" if not scored
                  else f"mejor score {scored[0]['score']} < umbral {abstain_threshold}")
        did = decisions.create_decision(con, domain=domain, decision="abstain", considered=scored,
                                        rationale="Evidencia insuficiente para producir hoy.",
                                        abstain_reason=reason, now=now)
        return {"decision": "abstain", "decision_id": did, "reason": reason}

    # --- Perseguir la mejor: Opportunity -> promoción a Belief -> Prediction ---
    best = scored[0]
    hyp = next(c for c in cands if c["id"] == best["hypothesis_id"])
    ev = json.loads(hyp["evidence"]) if hyp["evidence"] else {}
    contradiction = ev.get("features", {}).get("contradiction")

    opp_id = opportunities.create_opportunity(
        con, domain=domain, confidence=best["confidence"], value_level=best["score"],
        risk=contradiction, hypothesis_id=hyp["id"],
        attributes={"hypothesis": hyp["statement"], "evidence": ev}, now=now)

    belief_id = hypotheses.promote_to_belief(con, hyp["id"], now=now)
    pred_id = store.create_prediction(
        con, domain=domain, belief_id=belief_id,
        statement=f"Se confirmará: {hyp['statement']}",
        confidence=best["confidence"],
        verification_method=f"momentum de presencia (DF) a {horizon_days} días",
        refutation_criterion="refutada si el crecimiento de presencia < +10% en el horizonte",
        expected_verification_at=now + horizon_days * 86400, evidence=ev, now=now,
        instrument_version=instrument_version)

    opportunities.set_status(con, opp_id, "pursued")
    did = decisions.create_decision(
        con, domain=domain, decision="pursue", considered=scored,
        rationale=f"Mejor score {best['score']} ≥ umbral {abstain_threshold}.",
        chosen_hypothesis_id=hyp["id"], chosen_opportunity_id=opp_id, prediction_id=pred_id,
        now=now)
    return {"decision": "pursue", "decision_id": did, "opportunity_id": opp_id,
            "belief_id": belief_id, "prediction_id": pred_id}
