"""Trade-off Engine — el director NEGOCIA, no maximiza todo a la vez.

Un fallo de craft_score: premia APILAR patrones, como si pudieras tener máximo misterio Y máxima
claridad, máximo ritmo Y máxima emoción. Imposible. La creatividad es elegir QUÉ sacrificar.

Este módulo modela tensiones entre objetivos creativos: si una idea intenta dos cosas en tensión,
las detecta y obliga a una decisión registrada (qué se prioriza, qué se sacrifica y por qué).

v0: tensiones sembradas (heurística honesta, ampliable y calibrable con resultados reales).
"""
from __future__ import annotations
import sqlite3
import time

# (a, b, descripción) — pares de patrones/objetivos en tensión.
TENSIONS = [
    ("open_loop",      "reward",       "misterio abierto vs cierre satisfactorio"),
    ("escalation",     "empathy",      "ritmo/tensión vs conexión emocional"),
    ("strong_hook_3s", "twist",        "hook que revela pronto vs guardar el giro"),
    ("shock",          "rewatchable",  "impacto bruto vs merecer un segundo visionado"),
    ("humor_absurd",   "tension",      "comedia vs tensión sostenida"),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS tradeoff_decision (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ref        TEXT    NOT NULL,        -- a qué idea/producción pertenece
    kept       TEXT    NOT NULL,        -- objetivo priorizado
    sacrificed TEXT    NOT NULL,        -- objetivo sacrificado
    reason     TEXT    NOT NULL,
    created_at INTEGER NOT NULL
);
"""


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def detect_conflicts(tags: list[str]) -> list[dict]:
    """Tensiones presentes en un conjunto de objetivos. Pura (sin DB)."""
    s = set(tags or [])
    found = []
    for a, b, note in TENSIONS:
        if a in s and b in s:
            found.append({"a": a, "b": b, "note": note})
    return found


def record_resolution(con: sqlite3.Connection, *, ref: str, kept: str, sacrificed: str,
                      reason: str, now: int | None = None) -> int:
    """Registra la negociación: qué se prioriza, qué se sacrifica y por qué (explicable)."""
    if not reason or not reason.strip():
        raise ValueError("un trade-off exige una razón explícita (qué ganas al sacrificar).")
    now = now or int(time.time())
    return con.execute(
        "INSERT INTO tradeoff_decision (ref, kept, sacrificed, reason, created_at) "
        "VALUES (?,?,?,?,?)", (ref, kept, sacrificed, reason.strip(), now)).lastrowid
