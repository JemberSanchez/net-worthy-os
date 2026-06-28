"""Creative Question Engine — la unidad de CONOCIMIENTO: una pregunta respondida.

Un experimento responde "¿miniatura A o B?" (táctico, perecedero). Una PREGUNTA acumula muchos
experimentos en un PRINCIPIO reutilizable ("¿amenaza visible > implícita, en terror?"). Las
miniaturas cambian; los principios permanecen. El activo deja de ser "1M de videos" y pasa a ser
"N preguntas respondidas" — conocimiento que genera infinitos productos futuros.

GUARDS (sin ellos esto produce principios confiados pero falsos):
1. CONTEXT-BOUND: cada pregunta se define dentro de un contexto; NO se agrupa evidencia entre
   contextos (evita la paradoja de Simpson y la sobre-generalización confiada).
2. AUDITABLE: cada evidencia declara qué experimento y qué polo ganó (No Silent Learning para la
   abstracción) — no se infiere a posteriori.
3. CONSISTENCIA: un principio se resuelve solo con evidencia SUFICIENTE y CONSISTENTE; si está
   dividida, sigue 'open' (no se inventa un principio sobre evidencia en conflicto).
"""
from __future__ import annotations
import json
import sqlite3
import time
from collections import Counter

SCHEMA = """
CREATE TABLE IF NOT EXISTS creative_question (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    question       TEXT    NOT NULL,
    pole_a         TEXT    NOT NULL,
    pole_b         TEXT    NOT NULL,
    context        TEXT,                       -- envoltura de contexto (json)
    value          REAL    NOT NULL DEFAULT 0.5,  -- generalidad/accionabilidad (prioriza la agenda)
    status         TEXT    NOT NULL DEFAULT 'open',  -- open | resolved
    leading_pole   TEXT,
    principle      TEXT,
    confidence     REAL    NOT NULL DEFAULT 0,
    evidence_count INTEGER NOT NULL DEFAULT 0,
    created_at     INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS question_evidence (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id   INTEGER NOT NULL REFERENCES creative_question(id),
    experiment_id INTEGER,
    winning_pole  TEXT    NOT NULL,
    context       TEXT,
    at            INTEGER NOT NULL
);
"""


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def ask(con: sqlite3.Connection, *, question: str, pole_a: str, pole_b: str,
        context: dict | None = None, value: float = 0.5, now: int | None = None) -> int:
    """Registra una pregunta abierta (context-bound). Es la agenda de investigación."""
    now = now or int(time.time())
    return con.execute(
        "INSERT INTO creative_question (question, pole_a, pole_b, context, value, created_at) "
        "VALUES (?,?,?,?,?,?)",
        (question, pole_a, pole_b, json.dumps(context or {}), value, now)).lastrowid


def record_evidence(con: sqlite3.Connection, question_id: int, *, winning_pole: str,
                    experiment_id: int | None = None, context: dict | None = None,
                    now: int | None = None) -> None:
    """Añade una evidencia: qué polo ganó en un experimento decisivo. Auditable y explícita."""
    q = con.execute("SELECT pole_a, pole_b FROM creative_question WHERE id=?",
                    (question_id,)).fetchone()
    if q is None:
        raise ValueError(f"pregunta {question_id} no existe")
    if winning_pole not in (q["pole_a"], q["pole_b"]):
        raise ValueError(f"polo inválido: {winning_pole!r} (debe ser {q['pole_a']} o {q['pole_b']})")
    now = now or int(time.time())
    con.execute(
        "INSERT INTO question_evidence (question_id, experiment_id, winning_pole, context, at) "
        "VALUES (?,?,?,?,?)",
        (question_id, experiment_id, winning_pole, json.dumps(context or {}), now))
    con.commit()


def assess(con: sqlite3.Connection, question_id: int, *, min_evidence: int = 5,
           min_consistency: float = 0.7) -> dict:
    """Agrupa la evidencia y decide si la pregunta está RESUELTA (principio) o sigue ABIERTA.

    Resuelve solo con evidencia suficiente Y consistente. Si no, sigue abierta — el sistema no
    inventa principios sobre evidencia escasa o en conflicto.
    """
    q = con.execute("SELECT * FROM creative_question WHERE id=?", (question_id,)).fetchone()
    if q is None:
        raise ValueError(f"pregunta {question_id} no existe")
    poles = [r["winning_pole"] for r in con.execute(
        "SELECT winning_pole FROM question_evidence WHERE question_id=?", (question_id,)).fetchall()]
    n = len(poles)
    if n == 0:
        return {"status": "open", "confidence": 0.0, "evidence_count": 0,
                "reason": "sin evidencia"}

    counts = Counter(poles)
    leading, lead_wins = counts.most_common(1)[0]
    other = q["pole_b"] if leading == q["pole_a"] else q["pole_a"]
    confidence = round(lead_wins / n, 3)

    resolved = (n >= min_evidence) and (confidence >= min_consistency)
    status = "resolved" if resolved else "open"
    principle = f"{leading} > {other}" if resolved else None
    reason = ("evidencia suficiente y consistente" if resolved
              else ("evidencia insuficiente" if n < min_evidence else "evidencia en conflicto"))

    con.execute(
        "UPDATE creative_question SET status=?, leading_pole=?, principle=?, confidence=?, "
        "evidence_count=? WHERE id=?",
        (status, leading, principle, confidence, n, question_id))
    con.commit()
    return {"status": status, "leading_pole": leading, "principle": principle,
            "confidence": confidence, "evidence_count": n, "context": json.loads(q["context"] or "{}"),
            "reason": reason}


def open_questions(con: sqlite3.Connection) -> list[sqlite3.Row]:
    """Agenda de investigación: preguntas sin resolver, las de mayor valor primero."""
    return con.execute(
        "SELECT * FROM creative_question WHERE status='open' "
        "ORDER BY value DESC, evidence_count ASC").fetchall()


def validated_principles(con: sqlite3.Connection) -> list[sqlite3.Row]:
    """El activo: principios validados con su contexto, confianza y nº de experimentos."""
    return con.execute(
        "SELECT * FROM creative_question WHERE status='resolved' ORDER BY confidence DESC").fetchall()
