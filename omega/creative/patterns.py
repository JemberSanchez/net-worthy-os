"""Creative Knowledge Base (CKB) — vocabulario controlado de patrones de craft.

v0 = patrones genéricos (conocimiento de escuela de cine, NO propietario). El moat NO son
estos patrones: es el metadato CALIBRADO que se acumula encima (ver decisions.pattern_calibration).

Los patrones son a la vez (a) la biblioteca creativa y (b) el VOCABULARIO de razones con el que
toda decisión creativa debe justificarse. Esa unión es lo que hace posible el aprendizaje
creativo ("curiosity_gap funciona 81%").
"""
from __future__ import annotations
import sqlite3
import time

# (tag, categoría, descripción). Semilla v0; se amplía con el tiempo.
SEED = [
    ("curiosity_gap",     "curiosity",       "Abre una pregunta que el espectador NECESITA resolver."),
    ("open_loop",         "curiosity",       "Deja un hilo sin cerrar que obliga a seguir viendo."),
    ("clear_conflict",    "conflict",        "Conflicto nítido en los primeros segundos."),
    ("escalation",        "conflict",        "La tensión sube de forma sostenida."),
    ("stakes",            "conflict",        "Hay algo importante en juego."),
    ("wow_moment",        "payoff",          "Un momento visual o conceptual que sorprende."),
    ("twist",             "payoff",          "Giro inesperado que recontextualiza."),
    ("reward",            "payoff",          "El final recompensa la atención invertida."),
    ("strong_hook_3s",    "structure",       "Engancha en los primeros 3 segundos."),
    ("rewatchable",       "structure",       "Merece verse dos veces."),
    ("series_potential",  "structure",       "Puede convertirse en serie/personaje persistente."),
    ("novel_combination", "distinctiveness", "Combina elementos que nadie junta (tiburón+piscina olímpica)."),
    ("pattern_break",     "distinctiveness", "Rompe la expectativa del feed."),
    ("awe",               "emotion",         "Provoca asombro."),
    ("humor_absurd",      "emotion",         "Humor absurdo/inesperado."),
    ("tension",           "emotion",         "Mantiene tensión."),
    ("empathy",           "emotion",         "Genera conexión emocional."),
    ("shock",             "emotion",         "Impacto bruto (a menudo sobrevalorado; calibrar)."),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS creative_pattern (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tag         TEXT    NOT NULL UNIQUE,
    category    TEXT    NOT NULL,
    description TEXT,
    created_at  INTEGER NOT NULL
);
"""


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def seed(con: sqlite3.Connection, now: int | None = None) -> int:
    """Inserta la semilla (idempotente). Devuelve nº de patrones nuevos."""
    now = now or int(time.time())
    before = con.total_changes
    con.executemany(
        "INSERT OR IGNORE INTO creative_pattern (tag, category, description, created_at) "
        "VALUES (?,?,?,?)",
        [(t, c, d, now) for (t, c, d) in SEED],
    )
    con.commit()
    return con.total_changes - before


def vocabulary(con: sqlite3.Connection) -> set[str]:
    return {r["tag"] for r in con.execute("SELECT tag FROM creative_pattern").fetchall()}


def list_patterns(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT * FROM creative_pattern ORDER BY category, tag"
    ).fetchall()
