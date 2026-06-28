"""Kernel: Decision Record — el registro EXPLICABLE de una decisión.

Requisito obligatorio (no módulo): toda decisión debe poder reconstruir su razonamiento.
Por eso el decision_record guarda las candidatas CONSIDERADAS (con su score), la elegida,
las descartadas, la oportunidad y la predicción. `explain()` lo reconstruye todo; ninguna
decisión es una caja negra.
"""
from __future__ import annotations
import json
import sqlite3
import time

DECISIONS = {"pursue", "abstain"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS decision_record (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    domain                TEXT    NOT NULL,
    decision              TEXT    NOT NULL,    -- pursue | abstain
    rationale             TEXT,
    considered            TEXT,                -- json: [{hypothesis_id, statement, confidence, score, contributions}]
    chosen_hypothesis_id  INTEGER,
    chosen_opportunity_id INTEGER,
    prediction_id         INTEGER,
    abstain_reason        TEXT,
    created_at            INTEGER NOT NULL
);
"""


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def create_decision(con: sqlite3.Connection, *, domain: str, decision: str, considered: list,
                    rationale: str = "", chosen_hypothesis_id: int | None = None,
                    chosen_opportunity_id: int | None = None, prediction_id: int | None = None,
                    abstain_reason: str | None = None, now: int | None = None) -> int:
    if decision not in DECISIONS:
        raise ValueError(f"decision inválida: {decision!r}")
    now = now or int(time.time())
    cur = con.execute(
        "INSERT INTO decision_record (domain, decision, rationale, considered, "
        "chosen_hypothesis_id, chosen_opportunity_id, prediction_id, abstain_reason, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (domain, decision, rationale, json.dumps(considered), chosen_hypothesis_id,
         chosen_opportunity_id, prediction_id, abstain_reason, now),
    )
    con.commit()
    return cur.lastrowid


def explain(con: sqlite3.Connection, decision_id: int) -> dict:
    """Reconstruye el razonamiento completo de una decisión. La explicabilidad es obligatoria."""
    dr = con.execute("SELECT * FROM decision_record WHERE id=?", (decision_id,)).fetchone()
    if dr is None:
        raise ValueError(f"decision_record {decision_id} no existe")
    considered = json.loads(dr["considered"]) if dr["considered"] else []

    if dr["decision"] == "abstain":
        return {"decision": "abstain", "abstain_reason": dr["abstain_reason"],
                "discarded_hypotheses": considered}

    chosen = next((c for c in considered if c["hypothesis_id"] == dr["chosen_hypothesis_id"]), {})
    discarded = [c for c in considered if c["hypothesis_id"] != dr["chosen_hypothesis_id"]]

    ev = {}
    if dr["chosen_opportunity_id"]:
        opp = con.execute("SELECT attributes FROM opportunity WHERE id=?",
                          (dr["chosen_opportunity_id"],)).fetchone()
        if opp and opp["attributes"]:
            ev = json.loads(opp["attributes"]).get("evidence", {})

    pred = None
    if dr["prediction_id"]:
        pr = con.execute("SELECT * FROM prediction WHERE id=?", (dr["prediction_id"],)).fetchone()
        if pr:
            pred = {"statement": pr["statement"], "method": pr["verification_method"],
                    "refutation": pr["refutation_criterion"],
                    "expected_at": pr["expected_verification_at"]}

    signals = ev.get("signals", [])
    return {
        "decision": "pursue",
        "why": {"statement": chosen.get("statement"), "score": chosen.get("score"),
                "confidence": chosen.get("confidence")},
        "score_contributions": chosen.get("contributions", {}),
        "originating_signals": [f"{s['name']}='{s['value']}' ({s.get('count', '?')} items)"
                                for s in signals],
        "evidence_for": ev.get("for", []),
        "evidence_against": ev.get("against", []),
        "discarded_hypotheses": discarded,
        "uncertainty": round(1 - chosen.get("confidence", 0), 3),
        "prediction": pred,
    }


def render_explanation(e: dict) -> str:
    """Render legible del razonamiento (precursor de la consola)."""
    L = []
    if e["decision"] == "abstain":
        L.append("DECISIÓN: ABSTENERSE HOY")
        L.append(f"  Motivo: {e['abstain_reason']}")
        if e["discarded_hypotheses"]:
            L.append("  Candidatas (ninguna supera el umbral):")
            for d in e["discarded_hypotheses"][:5]:
                L.append(f"    - {d['statement']}  (score {d['score']})")
        return "\n".join(L)

    w = e["why"]
    L.append("DECISIÓN: PERSEGUIR")
    L.append(f"  Oportunidad: {w['statement']}")
    L.append(f"  Score {w['score']} | confianza {w['confidence']} | incertidumbre {e['uncertainty']}")
    L.append("  ¿Por qué? (contribuciones al score)")
    L.append(f"    base (confianza): {w['confidence']}")
    for k, v in e["score_contributions"].items():
        L.append(f"    {k}: {v:+}")
    if e["originating_signals"]:
        L.append("  Señales que la originaron:")
        for s in e["originating_signals"]:
            L.append(f"    ✔ {s}")
    if e["evidence_for"]:
        L.append("  Evidencia a favor:")
        for f in e["evidence_for"]:
            L.append(f"    ✔ {f}")
    if e["evidence_against"]:
        L.append("  Contradicciones:")
        for a in e["evidence_against"]:
            L.append(f"    ✘ {a}")
    if e["discarded_hypotheses"]:
        L.append("  Hipótesis descartadas:")
        for d in e["discarded_hypotheses"][:4]:
            L.append(f"    - {d['statement']}  (score {d['score']})")
    if e["prediction"]:
        p = e["prediction"]
        L.append("  Predicción falsable:")
        L.append(f"    {p['statement']}")
        L.append(f"    Verificación: {p['method']}")
        L.append(f"    Refutación: {p['refutation']}")
    return "\n".join(L)
