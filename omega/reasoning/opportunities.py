"""Kernel: Opportunity — output DOMAIN-AGNOSTIC del Decision Engine.

El kernel NO emite "un video". Emite una Opportunity con atributos genéricos (payload opaco)
que cada ADAPTER de dominio convierte en su activo (video, campaña, personaje...). Es el gemelo
simétrico de Signal: Signal = boundary dominio→kernel (entrada); Opportunity = kernel→dominio
(salida). Cardinalidad: se surfacean muchas; el Decision Record decide perseguir 1-3 o abstener.
"""
from __future__ import annotations
import json
import sqlite3
import time

from . import store  # intra-kernel (permitido por el guardarraíl de pureza)

STATUS = {"open", "pursued", "rejected", "expired"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS opportunity (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    domain        TEXT    NOT NULL,
    attributes    TEXT,                  -- json genérico; el adapter lo interpreta
    value_level   REAL,                  -- 0..1 atractivo estimado
    confidence    REAL    NOT NULL,
    risk          REAL,                  -- 0..1
    hypothesis_id INTEGER REFERENCES hypothesis(id),
    status        TEXT    NOT NULL DEFAULT 'open',  -- open|pursued|rejected|expired
    created_at    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_opp_status ON opportunity(domain, status);
"""


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def create_opportunity(con: sqlite3.Connection, *, domain: str, confidence: float,
                       attributes: dict | None = None, value_level: float | None = None,
                       risk: float | None = None, hypothesis_id: int | None = None,
                       now: int | None = None) -> int:
    store._check_conf(confidence)
    now = now or int(time.time())
    cur = con.execute(
        "INSERT INTO opportunity (domain, attributes, value_level, confidence, risk, "
        "hypothesis_id, status, created_at) VALUES (?,?,?,?,?,?, 'open', ?)",
        (domain, json.dumps(attributes) if attributes else None, value_level, confidence,
         risk, hypothesis_id, now),
    )
    con.commit()
    return cur.lastrowid


def list_open(con: sqlite3.Connection, domain: str | None = None) -> list[sqlite3.Row]:
    """Oportunidades abiertas, mejores primero (NULLs de value_level quedan al final en DESC)."""
    sql, args = "SELECT * FROM opportunity WHERE status='open'", []
    if domain:
        sql += " AND domain=?"
        args.append(domain)
    sql += " ORDER BY value_level DESC, confidence DESC"
    return con.execute(sql, args).fetchall()


def set_status(con: sqlite3.Connection, opp_id: int, status: str) -> None:
    if status not in STATUS:
        raise ValueError(f"status inválido: {status!r}. Permitidos: {sorted(STATUS)}")
    n = con.execute("UPDATE opportunity SET status=? WHERE id=?", (status, opp_id)).rowcount
    if n == 0:
        raise ValueError(f"opportunity {opp_id} no existe")
    con.commit()
