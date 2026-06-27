"""Almacén del Reasoning Engine (SQLite, domain-agnostic).

Entidades:
  belief          — una creencia de primera clase, con confianza mutable SOLO vía update_belief.
  belief_update   — log append-only de cada cambio de creencia (No Silent Learning).
  prediction      — el núcleo falsable del Decision Record (Every belief is a prediction).

Diseño clave:
  - `confidence` de una belief jamás se escribe con UPDATE directo desde fuera: el único
    camino es update_belief(), que exige causa + rationale y deja rastro. Hacerlo imposible
    "en silencio" es el enforcement estructural de la regla.
  - `domain` está en belief y prediction: el kernel es agnóstico ('content' hoy, otro mañana).
  - `evidence` es payload JSON genérico: NADA tipado de video.
"""
from __future__ import annotations
import json
import sqlite3
import time

ALLOWED_CAUSES = {
    "created",             # alta de la creencia
    "prediction_resolved", # una predicción se confirmó/refutó
    "evidence_drift",      # la evidencia cambió sin una predicción dueña (p.ej. el patrón desapareció)
    "decay",               # staleness: sin evidencia nueva, la incertidumbre crece
    "dependency",          # una creencia relacionada se actualizó
    "human",               # override humano
    "status_change",       # confirmada/refutada/retirada
}
OUTCOMES = {"confirmed", "refuted", "inconclusive"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS belief (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    domain      TEXT    NOT NULL,
    statement   TEXT    NOT NULL,
    confidence  REAL    NOT NULL,                 -- [0,1]; mutar SOLO vía update_belief()
    status      TEXT    NOT NULL DEFAULT 'active',-- active|confirmed|refuted|retired
    created_at  INTEGER NOT NULL,
    updated_at  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS belief_update (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    belief_id      INTEGER NOT NULL REFERENCES belief(id),
    at             INTEGER NOT NULL,
    old_confidence REAL,
    new_confidence REAL,
    old_status     TEXT,
    new_status     TEXT,
    cause_type     TEXT    NOT NULL,
    cause_refs     TEXT,                            -- json: ids de predicciones/evidencia
    rationale      TEXT    NOT NULL                 -- derivado de inputs reales, no narración libre
);
CREATE TABLE IF NOT EXISTS prediction (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    belief_id                INTEGER REFERENCES belief(id),
    domain                   TEXT    NOT NULL,
    statement                TEXT    NOT NULL,      -- falsable
    confidence               REAL    NOT NULL,
    evidence                 TEXT,                  -- json genérico
    verification_method      TEXT    NOT NULL,
    refutation_criterion     TEXT    NOT NULL,      -- umbral pre-comprometido
    created_at               INTEGER NOT NULL,
    expected_verification_at INTEGER NOT NULL,
    resolved_at              INTEGER,
    outcome                  TEXT,                  -- confirmed|refuted|inconclusive
    resolution_note          TEXT
);
CREATE INDEX IF NOT EXISTS idx_pred_due ON prediction(expected_verification_at, resolved_at);
CREATE INDEX IF NOT EXISTS idx_bu_belief ON belief_update(belief_id);
"""


def connect(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


# --------------------------------------------------------------------------- beliefs

def create_belief(con: sqlite3.Connection, domain: str, statement: str,
                  confidence: float, *, now: int | None = None) -> int:
    """Da de alta una creencia y registra el primer evento en el log (No Silent Learning)."""
    _check_conf(confidence)
    now = now or int(time.time())
    cur = con.execute(
        "INSERT INTO belief (domain, statement, confidence, status, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?)",
        (domain, statement, confidence, "active", now, now),
    )
    bid = cur.lastrowid
    con.execute(
        "INSERT INTO belief_update (belief_id, at, old_confidence, new_confidence, "
        "old_status, new_status, cause_type, cause_refs, rationale) VALUES (?,?,?,?,?,?,?,?,?)",
        (bid, now, None, confidence, None, "active", "created", None,
         "Alta de la creencia con confianza inicial."),
    )
    con.commit()
    return bid


def update_belief(con: sqlite3.Connection, belief_id: int, *, cause_type: str,
                  rationale: str, new_confidence: float | None = None,
                  new_status: str | None = None, cause_refs: list | None = None,
                  now: int | None = None) -> None:
    """ÚNICO camino para mutar una creencia. Exige causa válida y rationale no vacío.

    Esto es el enforcement estructural de "No Silent Learning": no existe ningún otro
    setter de confidence/status. Sin rationale o con causa inválida, lanza ValueError.
    """
    if cause_type not in ALLOWED_CAUSES:
        raise ValueError(f"cause_type inválido: {cause_type!r}. Permitidos: {sorted(ALLOWED_CAUSES)}")
    if not rationale or not rationale.strip():
        raise ValueError("No Silent Learning: toda actualización exige un rationale explícito.")
    if new_confidence is None and new_status is None:
        raise ValueError("Nada que actualizar: aporta new_confidence y/o new_status.")
    if new_confidence is not None:
        _check_conf(new_confidence)

    now = now or int(time.time())
    row = con.execute(
        "SELECT confidence, status FROM belief WHERE id = ?", (belief_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"belief {belief_id} no existe")
    old_conf, old_status = row["confidence"], row["status"]
    next_conf = new_confidence if new_confidence is not None else old_conf
    next_status = new_status if new_status is not None else old_status

    con.execute(
        "UPDATE belief SET confidence = ?, status = ?, updated_at = ? WHERE id = ?",
        (next_conf, next_status, now, belief_id),
    )
    con.execute(
        "INSERT INTO belief_update (belief_id, at, old_confidence, new_confidence, "
        "old_status, new_status, cause_type, cause_refs, rationale) VALUES (?,?,?,?,?,?,?,?,?)",
        (belief_id, now, old_conf, next_conf, old_status, next_status, cause_type,
         json.dumps(cause_refs) if cause_refs else None, rationale.strip()),
    )
    con.commit()


def belief_history(con: sqlite3.Connection, belief_id: int) -> list[sqlite3.Row]:
    """Trayectoria completa del razonamiento: cómo evolucionó la creencia y por qué."""
    return con.execute(
        "SELECT * FROM belief_update WHERE belief_id = ? ORDER BY id", (belief_id,)
    ).fetchall()


# ----------------------------------------------------------------------- predictions

def create_prediction(con: sqlite3.Connection, *, domain: str, statement: str,
                      confidence: float, verification_method: str,
                      refutation_criterion: str, expected_verification_at: int,
                      belief_id: int | None = None, evidence: dict | None = None,
                      now: int | None = None) -> int:
    """Crea una predicción falsable. Exige los 3 campos que la hacen verificable.

    Sin verification_method, refutation_criterion o fecha esperada, lanza ValueError:
    una afirmación sin forma de comprobarla NO es una predicción, es una opinión.
    """
    _check_conf(confidence)
    if not verification_method.strip():
        raise ValueError("Every belief is a prediction: falta verification_method.")
    if not refutation_criterion.strip():
        raise ValueError("Falta refutation_criterion (umbral pre-comprometido).")
    if not expected_verification_at or expected_verification_at <= 0:
        raise ValueError("Falta expected_verification_at: toda predicción sabe cuándo se evalúa.")
    now = now or int(time.time())
    cur = con.execute(
        "INSERT INTO prediction (belief_id, domain, statement, confidence, evidence, "
        "verification_method, refutation_criterion, created_at, expected_verification_at) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (belief_id, domain, statement, confidence,
         json.dumps(evidence) if evidence else None,
         verification_method, refutation_criterion, now, expected_verification_at),
    )
    con.commit()
    return cur.lastrowid


def resolve_prediction(con: sqlite3.Connection, prediction_id: int, *, outcome: str,
                       note: str = "", now: int | None = None) -> None:
    """Marca una predicción como resuelta. NO toca la confianza de la creencia.

    Deliberado: la actualización de la creencia es un paso EXPLÍCITO y separado, vía
    update_belief(cause_type='prediction_resolved'). Resolver no aprende en silencio.
    """
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome inválido: {outcome!r}. Permitidos: {sorted(OUTCOMES)}")
    now = now or int(time.time())
    n = con.execute(
        "UPDATE prediction SET outcome = ?, resolution_note = ?, resolved_at = ? "
        "WHERE id = ? AND resolved_at IS NULL",
        (outcome, note, now, prediction_id),
    ).rowcount
    if n == 0:
        raise ValueError(f"prediction {prediction_id} no existe o ya estaba resuelta")
    con.commit()


def due_predictions(con: sqlite3.Connection, now: int | None = None) -> list[sqlite3.Row]:
    """Predicciones cuya fecha de verificación llegó y siguen sin resolver.

    Esto evita el fallo nº1: predicciones que nunca se comprueban. Lo que aparezca aquí
    es deuda epistémica pendiente.
    """
    now = now or int(time.time())
    return con.execute(
        "SELECT * FROM prediction WHERE resolved_at IS NULL AND expected_verification_at <= ? "
        "ORDER BY expected_verification_at",
        (now,),
    ).fetchall()


def calibration(con: sqlite3.Connection, domain: str | None = None,
                bucket: float = 0.1) -> list[dict]:
    """¿Cuando decimos 70%, acertamos ~70%? Agrupa predicciones resueltas por banda de
    confianza y compara la confianza media declarada vs la tasa real de acierto.

    Es el activo medible del sistema: la prueba de que el razonamiento está calibrado.
    'inconclusive' se excluye (no informa sobre acierto/error).
    """
    sql = ("SELECT confidence, outcome FROM prediction "
           "WHERE outcome IN ('confirmed','refuted')")
    args: list = []
    if domain:
        sql += " AND domain = ?"
        args.append(domain)
    rows = con.execute(sql, args).fetchall()

    buckets: dict[float, list] = {}
    for r in rows:
        key = round(round(r["confidence"] / bucket) * bucket, 4)
        buckets.setdefault(key, []).append(1 if r["outcome"] == "confirmed" else 0)

    out = []
    for key in sorted(buckets):
        hits = buckets[key]
        out.append({
            "band": key,
            "n": len(hits),
            "predicted_rate": key,
            "actual_rate": round(sum(hits) / len(hits), 3),
        })
    return out


def _check_conf(c: float) -> None:
    if not (0.0 <= c <= 1.0):
        raise ValueError(f"confidence debe estar en [0,1]; recibido {c}")
