"""Capacidad de COMBINACIÓN — el operador de divergencia del director creativo.

Las grandes ideas no salen de aplicar un patrón, sino de combinar elementos distantes
("historia romana como anime", "física cuántica como thriller"). Esto NO reemplaza el CKB:
opera sobre él. El CKB aporta los elementos (tratamientos/géneros); la combinación los empareja
y puntúa su NOVEDAD (medible). Una combinación elegida se registra como decisión justificada y
se calibra con resultados reales (creative.decisions).

Capacidad medible vs "ayer": antes 1 encuadre por defecto de un sujeto; ahora k encuadres
distintos rankeados por novedad, evitando repetirse (la novedad decae con el uso).
"""
from __future__ import annotations
import sqlite3
import time

# Vocabulario de tratamientos/lentes (parte del CKB; se amplía con el tiempo).
TREATMENTS = [
    ("documentary",      "Tratado como documental serio."),
    ("horror",           "Contado como película de terror."),
    ("anime",            "Estética y ritmo de anime."),
    ("thriller",         "Tensión de thriller."),
    ("noir",             "Cine negro."),
    ("heist",            "Estructura de golpe/atraco."),
    ("comedy",           "Comedia."),
    ("mockumentary",     "Falso documental."),
    ("fairy_tale",       "Contado como cuento de hadas."),
    ("nature_doc",       "Documental de naturaleza (voz tipo Attenborough)."),
    ("courtroom",        "Drama de juicio."),
    ("sports_broadcast", "Retransmisión deportiva en directo."),
]

# Tratamiento "esperado" según una palabra del sujeto (penaliza lo obvio/cliché).
DEFAULTS = {
    "histor": "documentary", "cienc": "documentary", "science": "documentary",
    "crim": "noir", "natural": "nature_doc", "nature": "nature_doc",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS combination_use (
    subject   TEXT    NOT NULL,
    treatment TEXT    NOT NULL,
    count     INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (subject, treatment)
);
"""


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def _default_treatment(subject: str) -> str | None:
    s = subject.lower()
    for key, treatment in DEFAULTS.items():
        if key in s:
            return treatment
    return None


def _use_count(con: sqlite3.Connection, subject: str, treatment: str) -> int:
    row = con.execute(
        "SELECT count FROM combination_use WHERE subject=? AND treatment=?",
        (subject, treatment),
    ).fetchone()
    return row["count"] if row else 0


def generate(con: sqlite3.Connection, subject: str, k: int = 5) -> list[dict]:
    """Genera k combinaciones distintas sujeto×tratamiento, rankeadas por NOVEDAD.

    Novedad alta = tratamiento poco usado para este sujeto y no-obvio. Lo cliché se penaliza;
    lo ya explorado decae (el sistema busca lo que nunca se combinó).
    """
    default = _default_treatment(subject)
    out = []
    for tag, desc in TREATMENTS:
        used = _use_count(con, subject, tag)
        novelty = 1.0 / (1 + used)               # decae con el uso -> busca lo fresco
        if tag == default:
            novelty *= 0.3                        # penaliza el encuadre obvio
        out.append({
            "subject": subject,
            "treatment": tag,
            "novelty": round(novelty, 3),
            "statement": f"{subject} — {desc}",
            "is_default": tag == default,
        })
    out.sort(key=lambda x: x["novelty"], reverse=True)
    return out[:k]


def record_use(con: sqlite3.Connection, subject: str, treatment: str) -> None:
    """Marca una combinación como usada -> baja su novedad futura (evita repetirse)."""
    con.execute(
        "INSERT INTO combination_use (subject, treatment, count) VALUES (?,?,1) "
        "ON CONFLICT(subject, treatment) DO UPDATE SET count = count + 1",
        (subject, treatment),
    )
    con.commit()
