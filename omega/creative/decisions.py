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
CREATE TABLE IF NOT EXISTS production_context (
    production_ref TEXT    PRIMARY KEY,      -- contexto: emoción, audiencia, duración, plataforma...
    context        TEXT    NOT NULL,         -- json genérico
    updated_at     INTEGER NOT NULL
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


def record_context(con: sqlite3.Connection, production_ref: str, context: dict,
                   now: int | None = None) -> None:
    """Contexto de una producción (emoción, audiencia, duración, plataforma...).

    Es lo que vuelve el CKB MULTI-DIMENSIONAL: un patrón no tiene una tasa de éxito, sino tasas
    condicionadas por contexto ('curiosity_gap con emoción=awe -> 0.9').
    """
    now = now or int(time.time())
    con.execute(
        "INSERT OR REPLACE INTO production_context (production_ref, context, updated_at) "
        "VALUES (?,?,?)", (production_ref, json.dumps(context), now),
    )
    con.commit()


def pattern_calibration(con: sqlite3.Connection, *, context_filter: dict | None = None,
                        min_n: int = 1) -> list[dict]:
    """Tasa de éxito real por patrón, opcionalmente CONDICIONADA por contexto.

    Sin filtro: 'curiosity_gap -> 0.81'. Con context_filter={'emotion':'awe'}: la tasa de
    curiosity_gap SOLO en producciones con esa emoción. Esto es el CKB como memoria creativa
    multi-dimensional, no una tabla plana. Solo cuenta producciones con resultado MEDIDO.
    """
    rows = con.execute(
        "SELECT cd.pattern_tags, po.success, pc.context "
        "FROM creative_decision cd "
        "JOIN production_outcome po ON po.production_ref = cd.production_ref "
        "LEFT JOIN production_context pc ON pc.production_ref = cd.production_ref"
    ).fetchall()

    agg: dict[str, list[float]] = {}
    for r in rows:
        if context_filter:
            ctx = json.loads(r["context"]) if r["context"] else {}
            if any(ctx.get(k) != v for k, v in context_filter.items()):
                continue
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
