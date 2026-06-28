"""Creative Reasoning Loop — el proceso central: transforma una idea mediocre en una mejor.

El trabajo del director no es generar, sino TRANSFORMAR: tomar una idea y mejorarla por pasos de
pensamiento (understand→question→expand→combine→evaluate→refine), quedándose con una versión solo
si MEJORA. North-star: cuánto mejora una idea desde que nace hasta que se publica.

HONESTIDAD: craft_score es un PROXY transparente (y gameable): cuenta de patrones de craft
satisfechos + novedad. NO es la verdad; es lo medible hoy. Su validez se calibra contra resultados
reales (un "+0.3 de craft" debe correlacionar con mejor rendimiento, o el proxy se ajusta). El
valor durable es la MAQUINARIA reproducible de mejora, no el número.

Los pasos LLM (cuestionar/expandir/...) van en modo export-prompt ($0). Aquí vive la estructura, el
versionado, el gate "acepta solo si mejora" y la medición — incluida la contribución de cada paso
(cada paso del loop es una hipótesis: '¿Challenge mejora? ¿Refine aplana?').
"""
from __future__ import annotations
import json
import sqlite3
import time

from . import patterns

STEPS = ("understand", "research", "explore", "combine", "challenge", "expand",
         "reduce", "structure", "stress_test", "refine", "package")

SCHEMA = """
CREATE TABLE IF NOT EXISTS idea (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    subject    TEXT    NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS idea_version (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    idea_id      INTEGER NOT NULL REFERENCES idea(id),
    version_no   INTEGER NOT NULL,
    step         TEXT    NOT NULL,
    content      TEXT    NOT NULL,
    pattern_tags TEXT,
    novelty      REAL    DEFAULT 0,
    craft_score  REAL    NOT NULL,         -- PROXY transparente, no la verdad
    accepted     INTEGER NOT NULL,         -- 1 si mejoró la mejor versión hasta ahora
    created_at   INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_iv_idea ON idea_version(idea_id);
"""


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def craft_score(con: sqlite3.Connection, tags: list[str] | None, novelty: float = 0.0) -> float:
    """Proxy v0: + por cada patrón de craft VÁLIDO satisfecho, + por novedad. Cap 1.0."""
    vocab = patterns.vocabulary(con)
    valid = {t for t in (tags or []) if t in vocab}
    return round(min(1.0, 0.12 * len(valid) + 0.3 * float(novelty)), 3)


def start(con: sqlite3.Connection, *, subject: str, content: str,
          tags: list[str] | None = None, novelty: float = 0.0, now: int | None = None) -> int:
    now = now or int(time.time())
    idea_id = con.execute("INSERT INTO idea (subject, created_at) VALUES (?,?)",
                          (subject, now)).lastrowid
    con.execute(
        "INSERT INTO idea_version (idea_id, version_no, step, content, pattern_tags, novelty, "
        "craft_score, accepted, created_at) VALUES (?,?,?,?,?,?,?,1,?)",
        (idea_id, 0, "understand", content, json.dumps(tags or []), novelty,
         craft_score(con, tags, novelty), now),
    )
    con.commit()
    return idea_id


def _best_accepted(con: sqlite3.Connection, idea_id: int):
    return con.execute(
        "SELECT * FROM idea_version WHERE idea_id=? AND accepted=1 "
        "ORDER BY version_no DESC LIMIT 1", (idea_id,)).fetchone()


def advance(con: sqlite3.Connection, idea_id: int, *, step: str, content: str,
            tags: list[str] | None = None, novelty: float = 0.0, now: int | None = None) -> dict:
    """Aplica un paso de pensamiento. Se ACEPTA solo si mejora el craft_score ('repeat if improves')."""
    if step not in STEPS:
        raise ValueError(f"step inválido: {step!r}")
    now = now or int(time.time())
    last = _best_accepted(con, idea_id)
    last_no = con.execute("SELECT MAX(version_no) AS m FROM idea_version WHERE idea_id=?",
                          (idea_id,)).fetchone()["m"]
    score = craft_score(con, tags, novelty)
    accepted = 1 if (last is None or score > last["craft_score"]) else 0
    con.execute(
        "INSERT INTO idea_version (idea_id, version_no, step, content, pattern_tags, novelty, "
        "craft_score, accepted, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (idea_id, last_no + 1, step, content, json.dumps(tags or []), novelty, score, accepted, now),
    )
    con.commit()
    return {"step": step, "craft_score": score, "accepted": bool(accepted),
            "delta": round(score - (last["craft_score"] if last else 0.0), 3)}


def improvement(con: sqlite3.Connection, idea_id: int) -> dict:
    """La métrica north-star: cuánto mejoró la idea de nacimiento a versión final, y por paso."""
    versions = con.execute(
        "SELECT * FROM idea_version WHERE idea_id=? ORDER BY version_no", (idea_id,)).fetchall()
    if not versions:
        raise ValueError("idea sin versiones")
    accepted = [v for v in versions if v["accepted"]]
    return {
        "initial": versions[0]["craft_score"],
        "final": accepted[-1]["craft_score"],
        "improvement": round(accepted[-1]["craft_score"] - versions[0]["craft_score"], 3),
        "attempts": len(versions),
        "accepted": len(accepted),
        "path": [{"step": v["step"], "craft_score": v["craft_score"]} for v in accepted],
    }
