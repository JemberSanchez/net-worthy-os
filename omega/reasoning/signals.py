"""Kernel: almacén genérico de SEÑALES.

El kernel NO razona sobre videos — razona sobre señales. Una señal es una pieza de
evidencia estructurada y genérica: (name, value) + metadatos. El kernel almacena las
señales como pares opacos y **nunca ramifica sobre su significado** ('hook', 'emotion',
'theme' son strings sin sentido para el kernel). Solo la capa de dominio las interpreta.

Domain-agnostic: 'name' y 'value' son libres; no hay columnas tipadas de ningún formato.
"""
from __future__ import annotations
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS signal (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    domain            TEXT    NOT NULL,
    asset_ref         TEXT    NOT NULL,   -- id del asset en su dominio (opaco para el kernel)
    source            TEXT,
    name              TEXT    NOT NULL,   -- 'theme','language',... opaco para el kernel
    value             TEXT,
    value_num         REAL,
    kind              TEXT    NOT NULL DEFAULT 'categorical',  -- categorical | numeric
    confidence        REAL    NOT NULL DEFAULT 1.0,
    observed_at       INTEGER,
    extractor         TEXT    NOT NULL,
    extractor_version TEXT,
    UNIQUE(domain, asset_ref, name, value, extractor)
);
CREATE INDEX IF NOT EXISTS idx_signal_name  ON signal(domain, name);
CREATE INDEX IF NOT EXISTS idx_signal_asset ON signal(domain, asset_ref);
"""


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def add_signal(con: sqlite3.Connection, *, domain: str, asset_ref: str, name: str,
               extractor: str, value: str | None = None, value_num: float | None = None,
               kind: str = "categorical", confidence: float = 1.0,
               source: str | None = None, observed_at: int | None = None,
               extractor_version: str | None = None) -> int:
    """Inserta una señal (idempotente por UNIQUE). Devuelve 1 si nueva, 0 si duplicada."""
    cur = con.execute(
        "INSERT OR IGNORE INTO signal "
        "(domain, asset_ref, source, name, value, value_num, kind, confidence, "
        " observed_at, extractor, extractor_version) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (domain, asset_ref, source, name, value, value_num, kind, confidence,
         observed_at, extractor, extractor_version),
    )
    con.commit()
    return cur.rowcount


def count_total(con: sqlite3.Connection) -> int:
    return con.execute("SELECT COUNT(*) AS n FROM signal").fetchone()["n"]


def count_by_name(con: sqlite3.Connection, domain: str | None = None) -> list[sqlite3.Row]:
    sql, args = "SELECT name, COUNT(*) AS n FROM signal", []
    if domain:
        sql += " WHERE domain = ?"
        args.append(domain)
    sql += " GROUP BY name ORDER BY n DESC"
    return con.execute(sql, args).fetchall()
