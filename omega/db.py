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

-- Cache de DEMANDA real por tema (vistas de YouTube). Separado de observed_content a
-- propósito: son señales distintas (presencia editorial vs demanda de audiencia) y NO deben
-- mezclarse en el conteo de momentum. 'decide' lee esta tabla offline; 'youtube-scan' la llena.
CREATE TABLE IF NOT EXISTS theme_demand (
    term        TEXT    PRIMARY KEY,
    total_views INTEGER NOT NULL,
    videos      INTEGER NOT NULL,
    avg_views   INTEGER NOT NULL,
    example     TEXT,
    scanned_at  INTEGER NOT NULL          -- epoch: cuándo se midió esta demanda
);
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


# --- Cache de demanda (YouTube) ---

def upsert_theme_demand(rows: list[dict], scanned_at: int) -> int:
    """Reemplaza la demanda cacheada por término (INSERT OR REPLACE). Devuelve nº de temas."""
    if not rows:
        return 0
    sql = (
        "INSERT OR REPLACE INTO theme_demand "
        "(term, total_views, videos, avg_views, example, scanned_at) "
        "VALUES (:term, :total_views, :videos, :avg_views, :example, :scanned_at)"
    )
    payload = [{
        "term": r["term"], "total_views": r["total_views"], "videos": r["videos"],
        "avg_views": r["avg_views"],
        "example": (r["examples"][0] if r.get("examples") else ""),
        "scanned_at": scanned_at,
    } for r in rows]
    with connect() as con:
        con.executemany(sql, payload)
    return len(payload)


def clear_theme_demand() -> None:
    """Vacía el cache de demanda. Un escaneo es un SNAPSHOT del presente, no un acumulado: si se
    cambian las queries del nicho, los términos del basket viejo NO deben sobrevivir y contaminar."""
    try:
        with connect() as con:
            con.execute("DELETE FROM theme_demand")
    except sqlite3.OperationalError:
        pass  # tabla aún no creada -> nada que limpiar


def fetch_theme_demand() -> dict[str, int]:
    """{término: vistas_totales}. Tolerante: si aún no se ha escaneado, devuelve {} (no rompe decide)."""
    try:
        with connect() as con:
            rows = con.execute("SELECT term, total_views FROM theme_demand").fetchall()
    except sqlite3.OperationalError:
        return {}  # tabla aún no creada -> sin demanda, comportamiento idéntico al previo
    return {r["term"]: r["total_views"] for r in rows}


def fetch_theme_demand_full() -> list[dict]:
    """Filas completas del cache de demanda (term, vistas, nº videos, media, ejemplo), desc por
    vistas. Para que el Hypothesis Engine ORIGINE hipótesis desde frases de alta demanda."""
    try:
        with connect() as con:
            rows = con.execute(
                "SELECT term, total_views, videos, avg_views, example "
                "FROM theme_demand ORDER BY total_views DESC").fetchall()
    except sqlite3.OperationalError:
        return []
    return [dict(r) for r in rows]


def theme_demand_scanned_at() -> int | None:
    """Epoch del último escaneo de demanda (para saber si el cache está fresco). None si no hay."""
    try:
        with connect() as con:
            r = con.execute("SELECT MAX(scanned_at) AS t FROM theme_demand").fetchone()
    except sqlite3.OperationalError:
        return None
    return r["t"] if r and r["t"] is not None else None
