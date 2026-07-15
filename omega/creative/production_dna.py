"""ADN de producción — instrumentación rica por video (el dataset propietario, no solo el número).

Un `production_outcome` guarda UN número (éxito 0..1). Eso dice "funcionó o no", pero no POR QUÉ.
El ADN captura el "cómo se hizo" de cada video ANTES de publicar (hook_type, story_type, cta_type,
bloques con su técnica y duración) y, cuando llegan las analíticas, el "qué pasó" (CTR, AVD,
retención media y por bloque, fuente de tráfico). Unidos al outcome, permiten preguntar
"¿qué tipo de hook retiene mejor en MI audiencia?" — el activo difícil de copiar.

RIGOR (crítico): con pocos videos, agrupar éxito por una dimensión del ADN es RUIDO — cada bloque
co-varía con b-roll/voz/música/ritmo (confounding). `dna_calibration` marca 'provisional' hasta
tener n suficiente. La gráfica dice DÓNDE; para saber POR QUÉ hay que aislar la variable
(ver creative/experiments.py y su guard de significancia). Este módulo ALMACENA; no concluye solo.
"""
from __future__ import annotations
import json
import sqlite3
import time

# Dimensiones categóricas por las que se puede calibrar (whitelist: también evita inyección SQL).
DIMENSIONS = {"hook_type", "story_type", "cta_type"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS production_dna (
    production_ref TEXT    PRIMARY KEY,
    hook_type      TEXT,                    -- story | question | contrarian | stat | shock ...
    story_type     TEXT,                    -- personal | character | case_study | none ...
    cta_type       TEXT,                    -- session | subscribe | comment | none ...
    length_s       INTEGER,                 -- duración total del video (s)
    block_count    INTEGER NOT NULL,
    blocks         TEXT    NOT NULL,        -- json: [{block, technique, length_s}]
    recorded_at    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS production_analytics (
    production_ref     TEXT    PRIMARY KEY,
    ctr                REAL,                -- click-through de la miniatura (0..1)
    avd_pct            REAL,                -- average view duration como % del video (0..1)
    retention_avg      REAL,                -- retención media (0..1)
    views              INTEGER,             -- vistas absolutas (para horas-vistas = views*avd)
    traffic_source     TEXT,                -- browse | suggested | search | shorts | external ...
    retention_by_block TEXT,               -- json: {block: retention_pct}
    measured_at        INTEGER NOT NULL
);
-- COSTE de aprendizaje: cuánto costó producir este video. Sin esto no puedes optimizar el
-- RENDIMIENTO POR UNIDAD DE ESFUERZO (horas vistas por hora de trabajo) — clave para una fábrica.
CREATE TABLE IF NOT EXISTS production_cost (
    production_ref     TEXT    PRIMARY KEY,
    research_hours     REAL,
    script_hours       REAL,
    edit_hours         REAL,
    ai_cost_usd        REAL,
    time_to_publish_h  REAL,                -- horas de calendario idea -> publicado
    recorded_at        INTEGER NOT NULL
);
"""


def _ensure_columns(con: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
    """Añade columnas que faltan en una tabla ya existente. `CREATE TABLE IF NOT EXISTS` NO
    migra: si el esquema gana una columna nueva, una BD creada con el esquema viejo se queda
    sin ella y los INSERT petan en silencio. Idempotente."""
    have = {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
    for name, decl in columns.items():
        if name not in have:
            con.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    # Migraciones idempotentes para BDs creadas antes de que el esquema ganara estas columnas.
    _ensure_columns(con, "production_analytics", {"views": "INTEGER"})
    con.commit()


def record_dna(con: sqlite3.Connection, *, production_ref: str, blocks: list[dict],
               hook_type: str | None = None, story_type: str | None = None,
               cta_type: str | None = None, length_s: int | None = None,
               now: int | None = None) -> None:
    """Registra el ADN de producción (el 'cómo se hizo') ANTES de publicar. Idempotente por ref.

    blocks: lista de {block, technique, length_s}. block_count se deriva. Capturar esto antes de
    publicar es lo que evita PERDER la señal por bloque del primer video."""
    if not production_ref:
        raise ValueError("falta production_ref")
    if not isinstance(blocks, list):
        raise ValueError("blocks debe ser una lista de {block, technique, length_s}")
    now = now or int(time.time())
    con.execute(
        "INSERT OR REPLACE INTO production_dna (production_ref, hook_type, story_type, cta_type, "
        "length_s, block_count, blocks, recorded_at) VALUES (?,?,?,?,?,?,?,?)",
        (production_ref, hook_type, story_type, cta_type, length_s, len(blocks),
         json.dumps(blocks, ensure_ascii=False), now),
    )
    con.commit()


def record_analytics(con: sqlite3.Connection, *, production_ref: str, ctr: float | None = None,
                     avd_pct: float | None = None, retention_avg: float | None = None,
                     views: int | None = None, traffic_source: str | None = None,
                     retention_by_block: dict | None = None, now: int | None = None) -> None:
    """Registra las analíticas MEDIDAS (el 'qué pasó') tras publicar. Se une al ADN + outcome.

    GUARD de captura-en-origen: ctr/avd_pct/retention_avg son FRACCIONES [0,1], pero YouTube
    Studio las muestra como porcentaje ("CTR 4.5%"). Sin este guard, teclear 4.5 envenenaría el
    dataset en silencio y la calibración con n bajo quedaría basura sin aviso."""
    for field, val in (("ctr", ctr), ("avd_pct", avd_pct), ("retention_avg", retention_avg)):
        if val is not None and not (0.0 <= val <= 1.0):
            raise ValueError(f"{field}={val} fuera de [0,1]. Es FRACCIÓN, no porcentaje: "
                             f"si YouTube Studio dice '{val}%', registra {val}/100.")
    if views is not None and views < 0:
        raise ValueError(f"views={views} no puede ser negativo")
    if retention_by_block:
        bad = {k: v for k, v in retention_by_block.items() if not (0.0 <= float(v) <= 1.0)}
        if bad:
            raise ValueError(f"retention_by_block fuera de [0,1]: {bad}. "
                             "Son fracciones (85% -> 0.85).")
    now = now or int(time.time())
    con.execute(
        "INSERT OR REPLACE INTO production_analytics (production_ref, ctr, avd_pct, retention_avg, "
        "views, traffic_source, retention_by_block, measured_at) VALUES (?,?,?,?,?,?,?,?)",
        (production_ref, ctr, avd_pct, retention_avg, views, traffic_source,
         json.dumps(retention_by_block, ensure_ascii=False) if retention_by_block else None, now),
    )
    con.commit()


def record_cost(con: sqlite3.Connection, *, production_ref: str, research_hours: float | None = None,
                script_hours: float | None = None, edit_hours: float | None = None,
                ai_cost_usd: float | None = None, time_to_publish_h: float | None = None,
                now: int | None = None) -> None:
    """Registra el COSTE de producir un video. Habilita el rendimiento por unidad de esfuerzo."""
    now = now or int(time.time())
    con.execute(
        "INSERT OR REPLACE INTO production_cost (production_ref, research_hours, script_hours, "
        "edit_hours, ai_cost_usd, time_to_publish_h, recorded_at) VALUES (?,?,?,?,?,?,?)",
        (production_ref, research_hours, script_hours, edit_hours, ai_cost_usd,
         time_to_publish_h, now),
    )
    con.commit()


def efficiency(con: sqlite3.Connection) -> list[dict]:
    """Rendimiento por esfuerzo: para cada video con coste + resultado, éxito por hora de trabajo.

    CRUDO a propósito (proxy): 'éxito/hora' hasta que se registren horas-vistas absolutas. Responde
    la pregunta que un canal normal no puede: ¿qué produce más valor por hora invertida?"""
    rows = con.execute(
        "SELECT c.production_ref, c.research_hours, c.script_hours, c.edit_hours, po.success "
        "FROM production_cost c JOIN production_outcome po ON po.production_ref = c.production_ref"
    ).fetchall()
    out = []
    for r in rows:
        total_h = sum(x for x in (r["research_hours"], r["script_hours"], r["edit_hours"]) if x)
        out.append({"production_ref": r["production_ref"], "total_hours": round(total_h, 1),
                    "success": r["success"],
                    "success_per_hour": round(r["success"] / total_h, 3) if total_h else None})
    out.sort(key=lambda x: (x["success_per_hour"] is not None, x["success_per_hour"] or 0),
             reverse=True)
    return out


def fetch_dna(con: sqlite3.Connection, production_ref: str) -> dict | None:
    r = con.execute("SELECT * FROM production_dna WHERE production_ref=?", (production_ref,)).fetchone()
    if r is None:
        return None
    d = dict(r)
    d["blocks"] = json.loads(d["blocks"]) if d["blocks"] else []
    return d


def list_dna(con: sqlite3.Connection) -> list[dict]:
    rows = con.execute("SELECT * FROM production_dna ORDER BY recorded_at").fetchall()
    return [dict(r) for r in rows]


def dna_calibration(con: sqlite3.Connection, dimension: str, *, min_n: int = 1,
                    confident_n: int = 3) -> list[dict]:
    """Tasa de éxito real agrupada por una dimensión del ADN (hook_type/story_type/cta_type).

    Solo cuenta producciones con resultado MEDIDO (join con production_outcome). Marca
    'provisional': True cuando n < confident_n — con pocos datos NO es una conclusión (confounding).
    """
    if dimension not in DIMENSIONS:
        raise ValueError(f"dimensión inválida: {dimension!r}. Permitidas: {sorted(DIMENSIONS)}")
    # dimension viene de la whitelist DIMENSIONS -> seguro interpolarlo
    rows = con.execute(
        f"SELECT d.{dimension} AS v, po.success FROM production_dna d "
        "JOIN production_outcome po ON po.production_ref = d.production_ref"
    ).fetchall()

    agg: dict[str, list[float]] = {}
    for r in rows:
        if r["v"] is None:
            continue
        agg.setdefault(r["v"], []).append(r["success"])

    out = []
    for value, vals in agg.items():
        if len(vals) < min_n:
            continue
        out.append({"value": value, "n": len(vals),
                    "success_rate": round(sum(vals) / len(vals), 3),
                    "provisional": len(vals) < confident_n})
    out.sort(key=lambda x: x["success_rate"], reverse=True)
    return out
