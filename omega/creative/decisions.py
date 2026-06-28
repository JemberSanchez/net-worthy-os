"""Decisiones creativas justificadas + calibración (el aprendizaje creativo real).

Regla "Every Creative Decision Needs a Reason": toda decisión creativa DEBE justificarse con
≥1 tag del vocabulario controlado (el CKB). Sin tags válidos -> ValueError. Esto es lo que hace
posible, con el tiempo, computar "las decisiones por curiosity_gap funcionan 81%".
"""
from __future__ import annotations
import json
import sqlite3
import time

from . import patterns

SCHEMA = """
CREATE TABLE IF NOT EXISTS creative_decision (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    production_ref TEXT    NOT NULL,        -- a qué video/asset pertenece
    decision_type  TEXT    NOT NULL,        -- 'hook' | 'structure' | 'character' | 'title' ...
    choice         TEXT    NOT NULL,        -- la decisión concreta tomada
    pattern_tags   TEXT    NOT NULL,        -- json: tags del CKB que la justifican
    created_at     INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS production_outcome (
    production_ref TEXT    PRIMARY KEY,
    success        REAL    NOT NULL,        -- 0..1 (medido tras publicar; NO predicho)
    measured_at    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_cd_prod ON creative_decision(production_ref);
"""


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def record_decision(con: sqlite3.Connection, *, production_ref: str, decision_type: str,
                    choice: str, pattern_tags: list[str], now: int | None = None) -> int:
    """Registra una decisión creativa. EXIGE justificación con tags del vocabulario controlado."""
    if not pattern_tags:
        raise ValueError("Every Creative Decision Needs a Reason: faltan pattern_tags.")
    vocab = patterns.vocabulary(con)
    invalid = [t for t in pattern_tags if t not in vocab]
    if invalid:
        raise ValueError(f"tags fuera del vocabulario (CKB): {invalid}. "
                         f"El 'porqué' debe venir del CKB, no ser texto libre.")
    now = now or int(time.time())
    cur = con.execute(
        "INSERT INTO creative_decision (production_ref, decision_type, choice, pattern_tags, "
        "created_at) VALUES (?,?,?,?,?)",
        (production_ref, decision_type, choice, json.dumps(pattern_tags), now),
    )
    con.commit()
    return cur.lastrowid


def record_outcome(con: sqlite3.Connection, production_ref: str, success: float,
                   now: int | None = None) -> None:
    """Resultado MEDIDO (no predicho) de una producción publicada."""
    if not (0.0 <= success <= 1.0):
        raise ValueError("success debe estar en [0,1]")
    now = now or int(time.time())
    con.execute(
        "INSERT OR REPLACE INTO production_outcome (production_ref, success, measured_at) "
        "VALUES (?,?,?)", (production_ref, success, now),
    )
    con.commit()


def pattern_calibration(con: sqlite3.Connection, min_n: int = 1) -> list[dict]:
    """Por cada patrón: tasa de éxito real de las decisiones que lo invocaron.

    Aquí aparece el aprendizaje creativo: 'curiosity_gap -> 0.81', 'shock -> 0.44'. Solo cuenta
    producciones con resultado medido (predict→verify aplicado a la creatividad).
    """
    rows = con.execute(
        "SELECT cd.pattern_tags, po.success FROM creative_decision cd "
        "JOIN production_outcome po ON po.production_ref = cd.production_ref"
    ).fetchall()

    agg: dict[str, list[float]] = {}
    for r in rows:
        for tag in json.loads(r["pattern_tags"]):
            agg.setdefault(tag, []).append(r["success"])

    out = []
    for tag, vals in agg.items():
        if len(vals) < min_n:
            continue
        out.append({"pattern": tag, "n": len(vals),
                    "success_rate": round(sum(vals) / len(vals), 3)})
    out.sort(key=lambda x: x["success_rate"], reverse=True)
    return out
