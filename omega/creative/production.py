"""Localized optimization — el director arregla el ESLABÓN DÉBIL, no rehace todo.

Una producción es un conjunto de COMPONENTES (idea, título, hook, miniatura, guion...), cada uno
con su propio Creative Reasoning Loop (reasoning_loop) y su craft_score. La calidad de la
producción está limitada por su componente más débil: un video con gran idea pero hook horrible
es un mal video.

bottleneck() encuentra ese eslabón débil; así el sistema mejora SOLO esa parte — más inteligente
y más barato que rehacer todo. Reutiliza reasoning_loop; no añade lógica creativa nueva.

Caveat honesto: comparar craft_score ENTRE tipos de componente (¿un hook 0.4 es peor que un título
0.5?) asume una comparabilidad que aún NO está calibrada. v0 usa el score absoluto; la
comparabilidad por tipo es ella misma una hipótesis a calibrar contra resultados.
"""
from __future__ import annotations
import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS production (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    subject    TEXT    NOT NULL,
    created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS production_component (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    production_id  INTEGER NOT NULL REFERENCES production(id),
    component_type TEXT    NOT NULL,        -- idea | title | hook | thumbnail | script ...
    idea_id        INTEGER NOT NULL,        -- su propio loop en reasoning_loop
    created_at     INTEGER NOT NULL,
    UNIQUE (production_id, component_type)
);
"""


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def create_production(con: sqlite3.Connection, *, subject: str, now: int | None = None) -> int:
    now = now or int(time.time())
    return con.execute("INSERT INTO production (subject, created_at) VALUES (?,?)",
                       (subject, now)).lastrowid


def add_component(con: sqlite3.Connection, production_id: int, *, component_type: str,
                  idea_id: int, now: int | None = None) -> None:
    now = now or int(time.time())
    con.execute(
        "INSERT OR REPLACE INTO production_component (production_id, component_type, idea_id, "
        "created_at) VALUES (?,?,?,?)", (production_id, component_type, idea_id, now))
    con.commit()


def _component_score(con: sqlite3.Connection, idea_id: int) -> float:
    row = con.execute(
        "SELECT MAX(craft_score) AS s FROM idea_version WHERE idea_id=? AND accepted=1",
        (idea_id,)).fetchone()
    return row["s"] if row and row["s"] is not None else 0.0


def component_scores(con: sqlite3.Connection, production_id: int) -> dict:
    rows = con.execute(
        "SELECT component_type, idea_id FROM production_component WHERE production_id=?",
        (production_id,)).fetchall()
    return {r["component_type"]: _component_score(con, r["idea_id"]) for r in rows}


def production_quality(con: sqlite3.Connection, production_id: int) -> float:
    """Tan fuerte como el eslabón más débil: la calidad la limita el peor componente."""
    scores = component_scores(con, production_id)
    return round(min(scores.values()), 3) if scores else 0.0


def bottleneck(con: sqlite3.Connection, production_id: int) -> dict | None:
    """El componente más débil — lo único que vale la pena rehacer ahora."""
    scores = component_scores(con, production_id)
    if not scores:
        return None
    ct = min(scores, key=scores.get)
    row = con.execute(
        "SELECT idea_id FROM production_component WHERE production_id=? AND component_type=?",
        (production_id, ct)).fetchone()
    return {"component_type": ct, "score": round(scores[ct], 3), "idea_id": row["idea_id"]}
