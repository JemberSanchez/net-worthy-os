"""Capa de almacenamiento (SQLite, cero instalación).

Separamos ya conceptualmente lo OBSERVADO (terceros, fuente del aprendizaje)
de lo que en el futuro será PRODUCTION (tus videos). Por ahora solo observed_content.
La migración futura a Postgres+pgvector no toca el resto del código si pasa por aquí.
"""
from __future__ import annotations
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS observed_content (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source       TEXT    NOT NULL,
    external_id  TEXT    NOT NULL UNIQUE,   -- link o guid: dedup entre ejecuciones
    title        TEXT    NOT NULL,
    summary      TEXT,
    url          TEXT,
    published_at INTEGER,                   -- epoch segundos (fecha de publicación real)
    ingested_at  INTEGER NOT NULL           -- epoch segundos (cuándo lo capturamos)
);
CREATE INDEX IF NOT EXISTS idx_obs_published ON observed_content(published_at);
CREATE INDEX IF NOT EXISTS idx_obs_source    ON observed_content(source);
"""


def init() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as con:
        con.executescript(SCHEMA)


@contextmanager
def connect(path: Path | None = None):
    con = sqlite3.connect(path or config.DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def upsert_items(items: list[dict]) -> int:
    """Inserta items nuevos; ignora duplicados por external_id. Devuelve nº insertados."""
    if not items:
        return 0
    sql = (
        "INSERT OR IGNORE INTO observed_content "
        "(source, external_id, title, summary, url, published_at, ingested_at) "
        "VALUES (:source, :external_id, :title, :summary, :url, :published_at, :ingested_at)"
    )
    with connect() as con:
        before = con.total_changes
        con.executemany(sql, items)
        return con.total_changes - before


def fetch_between(start_epoch: int, end_epoch: int) -> list[sqlite3.Row]:
    """Documentos cuyo published_at cae en [start, end). Si falta fecha, usa ingested_at."""
    sql = (
        "SELECT * FROM observed_content "
        "WHERE COALESCE(published_at, ingested_at) >= ? "
        "AND COALESCE(published_at, ingested_at) < ?"
    )
    with connect() as con:
        return con.execute(sql, (start_epoch, end_epoch)).fetchall()


def count_total() -> int:
    with connect() as con:
        return con.execute("SELECT COUNT(*) AS n FROM observed_content").fetchone()["n"]
