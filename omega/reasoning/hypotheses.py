"""Kernel: Hypothesis — tier de CANDIDATAS (efímero).

Una hipótesis es una explicación candidata generada desde señales. Hay muchas por ciclo y la
mayoría se descartan. Solo las que "se ganan una apuesta" se PROMUEVEN a Belief (tracked, con
todo el ciclo predict→verify y No Silent Learning). Mantener este tier separado evita inundar
el store de creencias con ruido diario. Domain-agnostic.
"""
from __future__ import annotations
import json
import sqlite3
import time

from . import store  # intra-kernel (permitido por el guardarraíl de pureza)

STATUS = {"candidate", "promoted", "discarded"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS hypothesis (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    domain             TEXT    NOT NULL,
    statement          TEXT    NOT NULL,
    confidence         REAL    NOT NULL,
    evidence           TEXT,                       -- json: refs a señales, etc.
    status             TEXT    NOT NULL DEFAULT 'candidate',  -- candidate|promoted|discarded
    promoted_belief_id INTEGER REFERENCES belief(id),
    created_at         INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_hyp_status ON hypothesis(domain, status);
"""


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def create_hypothesis(con: sqlite3.Connection, *, domain: str, statement: str,
                      confidence: float, evidence: dict | None = None,
                      now: int | None = None) -> int:
    store._check_conf(confidence)
    now = now or int(time.time())
    cur = con.execute(
        "INSERT INTO hypothesis (domain, statement, confidence, evidence, status, created_at) "
        "VALUES (?,?,?,?, 'candidate', ?)",
        (domain, statement, confidence, json.dumps(evidence) if evidence else None, now),
    )
    con.commit()
    return cur.lastrowid


def list_candidates(con: sqlite3.Connection, domain: str | None = None) -> list[sqlite3.Row]:
    sql, args = "SELECT * FROM hypothesis WHERE status='candidate'", []
    if domain:
        sql += " AND domain=?"
        args.append(domain)
    sql += " ORDER BY confidence DESC"
    return con.execute(sql, args).fetchall()


def discard(con: sqlite3.Connection, hyp_id: int) -> None:
    con.execute(
        "UPDATE hypothesis SET status='discarded' WHERE id=? AND status='candidate'", (hyp_id,)
    )
    con.commit()


def promote_to_belief(con: sqlite3.Connection, hyp_id: int, *, now: int | None = None) -> int:
    """Gate de promoción: una hipótesis candidata pasa a ser Belief tracked.

    Es el punto donde 'nace una creencia' (se gana una apuesta). Devuelve el belief_id.
    """
    now = now or int(time.time())
    h = con.execute("SELECT * FROM hypothesis WHERE id=?", (hyp_id,)).fetchone()
    if h is None:
        raise ValueError(f"hypothesis {hyp_id} no existe")
    if h["status"] != "candidate":
        raise ValueError(f"hypothesis {hyp_id} no es candidata (status={h['status']})")
    bid = store.create_belief(con, h["domain"], h["statement"], h["confidence"], now=now)
    con.execute(
        "UPDATE hypothesis SET status='promoted', promoted_belief_id=? WHERE id=?", (bid, hyp_id)
    )
    con.commit()
    return bid
