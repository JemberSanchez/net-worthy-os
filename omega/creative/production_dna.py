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
    traffic_source     TEXT,                -- browse | suggested | search | shorts | external ...
    retention_by_block TEXT,               -- json: {block: retention_pct}
    measured_at        INTEGER NOT NULL
);
"""


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
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
                     traffic_source: str | None = None,
                     retention_by_block: dict | None = None, now: int | None = None) -> None:
    """Registra las analíticas MEDIDAS (el 'qué pasó') tras publicar. Se une al ADN + outcome."""
    now = now or int(time.time())
    con.execute(
        "INSERT OR REPLACE INTO production_analytics (production_ref, ctr, avd_pct, retention_avg, "
        "traffic_source, retention_by_block, measured_at) VALUES (?,?,?,?,?,?,?)",
        (production_ref, ctr, avd_pct, retention_avg, traffic_source,
         json.dumps(retention_by_block, ensure_ascii=False) if retention_by_block else None, now),
    )
    con.commit()


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
