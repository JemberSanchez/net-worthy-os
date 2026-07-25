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

-- Historial de demanda (append-only, un registro por término y escaneo). A diferencia de
-- theme_demand (snapshot del presente), esto ACUMULA en el tiempo para medir MOMENTUM de demanda:
-- ¿la demanda de un tema SUBE entre escaneos? = adelantarse a la ola, no llegar al pico.
CREATE TABLE IF NOT EXISTS theme_demand_history (
    scanned_at  INTEGER NOT NULL,
    term        TEXT    NOT NULL,
    total_views INTEGER NOT NULL,
    videos      INTEGER NOT NULL,
    PRIMARY KEY (scanned_at, term)
);

-- Videos crudos del último escaneo (snapshot). Guardar título+vistas permite la ADYACENCIA (#1):
-- qué OTROS temas ven quienes ven un tema dado (co-ocurrencia en títulos, ponderada por vistas).
CREATE TABLE IF NOT EXISTS scanned_video (
    video_id   TEXT    PRIMARY KEY,
    title      TEXT    NOT NULL,
    views      INTEGER NOT NULL,
    scanned_at INTEGER NOT NULL
);

-- Demanda EVERGREEN: catálogo de >=90 días que SIGUE moviendo vistas. Tabla SEPARADA de
-- theme_demand a propósito: son dos regímenes distintos y mezclarlos los destruye. theme_demand
-- mide "de qué se habla ahora" (noticia, publishedAfter=30d); esto mide "qué sigue funcionando
-- meses después", que es lo único que VIRALIDAD.md §3.1 encontró entre los 39 despegues reales.
-- Se pondera por vistas/DÍA, no por total: con catálogo viejo el total premia la edad, no el interés.
CREATE TABLE IF NOT EXISTS theme_evergreen (
    term          TEXT    PRIMARY KEY,
    views_per_day REAL    NOT NULL,
    videos        INTEGER NOT NULL,
    example       TEXT,
    scanned_at    INTEGER NOT NULL
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


def append_theme_demand_history(rows: list[dict], scanned_at: int) -> int:
    """Añade el snapshot actual al historial (append-only). Alimenta el momentum de demanda."""
    if not rows:
        return 0
    sql = ("INSERT OR REPLACE INTO theme_demand_history (scanned_at, term, total_views, videos) "
           "VALUES (:scanned_at, :term, :total_views, :videos)")
    payload = [{"scanned_at": scanned_at, "term": r["term"],
                "total_views": r["total_views"], "videos": r["videos"]} for r in rows]
    with connect() as con:
        con.executemany(sql, payload)
    return len(payload)


def fetch_demand_momentum() -> dict[str, float]:
    """log2(vistas_ahora / vistas_escaneo_anterior) por término, entre los DOS últimos escaneos.

    Mide si la DEMANDA de un tema SUBE (indicador adelantado). Con <2 escaneos -> {} (momentum 0,
    igual que el momentum de RSS necesita baseline).

    Un término SIN baseline en el escaneo previo NO puntúa: sale del dict -> momentum 0.
    Antes se le aplicaba old=0 -> log2(v+1) -> ratio enorme -> capado a 2.0 -> +0.40 al score,
    IGUAL para un término de 1.000 vistas que para uno de 700.000 (el cap aplasta la diferencia).
    Eso es casi el máximo que puede aportar `demand` (+0.45), así que cualquier término nuevo
    ganaba `decide` por goleada — y "nuevo" no significa demanda emergente: significa que el
    basket de queries pescó algo distinto. Sin baseline el momentum NO ES MEDIBLE, y el propio
    docstring ya exigía baseline a nivel global: esto lo hace coherente a nivel de término.
    El precio: la demanda de verdad emergente tarda un escaneo más en verse. Aceptable —
    inventarse un momentum es peor que esperar."""
    import math
    try:
        with connect() as con:
            scans = [r["scanned_at"] for r in con.execute(
                "SELECT DISTINCT scanned_at FROM theme_demand_history "
                "ORDER BY scanned_at DESC LIMIT 2").fetchall()]
            if len(scans) < 2:
                return {}
            latest, prev = scans[0], scans[1]
            cur = {r["term"]: r["total_views"] for r in con.execute(
                "SELECT term, total_views FROM theme_demand_history WHERE scanned_at=?", (latest,))}
            old = {r["term"]: r["total_views"] for r in con.execute(
                "SELECT term, total_views FROM theme_demand_history WHERE scanned_at=?", (prev,))}
    except sqlite3.OperationalError:
        return {}
    return {term: round(math.log2((v + 1) / (old[term] + 1)), 3)
            for term, v in cur.items() if term in old}


def replace_scanned_videos(videos: list[dict], scanned_at: int) -> int:
    """Reemplaza el snapshot de videos crudos (DELETE + insert). Base de la adyacencia (#1)."""
    with connect() as con:
        con.execute("DELETE FROM scanned_video")
        if videos:
            con.executemany(
                "INSERT OR REPLACE INTO scanned_video (video_id, title, views, scanned_at) "
                "VALUES (:video_id, :title, :views, :scanned_at)",
                [{"video_id": v["video_id"], "title": v["title"],
                  "views": v["views"], "scanned_at": scanned_at} for v in videos])
    return len(videos)


def fetch_scanned_videos() -> list[dict]:
    """Videos crudos del último escaneo (title + views). Para computar temas adyacentes."""
    try:
        with connect() as con:
            rows = con.execute("SELECT title, views FROM scanned_video").fetchall()
    except sqlite3.OperationalError:
        return []
    return [dict(r) for r in rows]


def clear_theme_demand() -> None:
    """Vacía el cache de demanda. Un escaneo es un SNAPSHOT del presente, no un acumulado: si se
    cambian las queries del nicho, los términos del basket viejo NO deben sobrevivir y contaminar."""
    try:
        with connect() as con:
            con.execute("DELETE FROM theme_demand")
    except sqlite3.OperationalError:
        pass  # tabla aún no creada -> nada que limpiar


def replace_theme_evergreen(rows: list[dict], scanned_at: int) -> int:
    """Reemplaza el snapshot de demanda evergreen. Como `theme_demand`, es una foto del presente:
    si cambian las queries del nicho, los términos viejos no deben sobrevivir."""
    with connect() as con:
        con.execute("DELETE FROM theme_evergreen")
        if rows:
            con.executemany(
                "INSERT OR REPLACE INTO theme_evergreen "
                "(term, views_per_day, videos, example, scanned_at) "
                "VALUES (:term, :views_per_day, :videos, :example, :scanned_at)",
                [{"term": r["term"], "views_per_day": r["views_per_day"], "videos": r["videos"],
                  "example": (r["examples"][0] if r.get("examples") else ""),
                  "scanned_at": scanned_at} for r in rows])
    return len(rows)


def fetch_theme_evergreen() -> list[dict]:
    """Filas del cache evergreen, desc por vistas/día. Tolerante: {} si aún no se escaneó."""
    try:
        with connect() as con:
            rows = con.execute(
                "SELECT term, views_per_day, videos, example, scanned_at "
                "FROM theme_evergreen ORDER BY views_per_day DESC").fetchall()
    except sqlite3.OperationalError:
        return []
    return [dict(r) for r in rows]


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


def backup_snapshot(db_path: Path | None = None, data_dir: Path | None = None,
                    dest_dir: Path | None = None, now: int | None = None) -> Path:
    """Backup del MOAT: zip fechado con snapshot CONSISTENTE del SQLite + todo data/ (JSONs, MP3s).

    El SQLite se copia vía la API de backup (con.backup): consistente aunque haya conexiones
    abiertas — un copy del archivo a pelo puede llevarse un estado a medio commit. El resto de
    data/ (voces, instrumentación) entra tal cual. El zip queda en dest_dir (default:
    ROOT/backups, gitignored): la copia a nube/USB es del humano — un backup en el MISMO disco
    solo protege de borrados, no de fallos de disco."""
    import time as _time
    import zipfile

    db_path = db_path or config.DB_PATH
    data_dir = data_dir or config.DATA_DIR
    dest_dir = dest_dir or (config.ROOT / "backups")
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = _time.strftime("%Y%m%d-%H%M%S", _time.localtime(now or _time.time()))
    out = dest_dir / f"omega-backup-{stamp}.zip"

    snap = dest_dir / f".snapshot-{stamp}.sqlite"
    try:
        if db_path.exists():
            src = sqlite3.connect(db_path)
            dst = sqlite3.connect(snap)
            try:
                src.backup(dst)
            finally:
                dst.close()
                src.close()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            if snap.exists():
                zf.write(snap, arcname=f"data/{db_path.name}")
            if data_dir.exists():
                for f in sorted(data_dir.iterdir()):
                    # el snapshot ya representa la DB; los .bak viejos no aportan
                    if f.is_file() and f.name != db_path.name and not f.name.startswith(db_path.name + ".bak"):
                        zf.write(f, arcname=f"data/{f.name}")
    finally:
        snap.unlink(missing_ok=True)
    return out


def theme_demand_scanned_at() -> int | None:
    """Epoch del último escaneo de demanda (para saber si el cache está fresco). None si no hay."""
    try:
        with connect() as con:
            r = con.execute("SELECT MAX(scanned_at) AS t FROM theme_demand").fetchone()
    except sqlite3.OperationalError:
        return None
    return r["t"] if r and r["t"] is not None else None
