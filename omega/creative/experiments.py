"""Creative Experiment — la unidad de APRENDIZAJE del laboratorio creativo.

Cambio de perspectiva: no publicamos videos, publicamos EXPERIMENTOS. Cada publicación responde
UNA pregunta falsable aislando UNA variable (misma pieza, distintas miniaturas/títulos/hooks).
Eso da atribución: no preguntas "¿funcionó el video?" sino "¿qué variante ganó?".

Un experimento es, literalmente, una predicción del Reasoning Engine con variantes.

GUARD CRÍTICO: aislar la variable arregla el confounding, NO el poder estadístico. Por eso
resolve() corre un test de dos proporciones y RECHAZA declarar ganador si la diferencia no es
significativa. El laboratorio sabe cuándo su propio resultado es ruido — y NO aprende de ruido.
"""
from __future__ import annotations
import json
import math
import sqlite3
import time

SCHEMA = """
CREATE TABLE IF NOT EXISTS experiment (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    hypothesis  TEXT    NOT NULL,            -- falsable: "hook emocional > misterioso (terror 60s)"
    variable    TEXT    NOT NULL,            -- qué se aísla: thumbnail | title | hook ...
    context     TEXT,                        -- json: emoción, duración, plataforma...
    status      TEXT    NOT NULL DEFAULT 'open',  -- open | resolved | inconclusive
    winner      TEXT,
    created_at  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS experiment_variant (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    experiment_id INTEGER NOT NULL REFERENCES experiment(id),
    label         TEXT    NOT NULL,
    description   TEXT,
    tags          TEXT,                      -- json: patrones del CKB que encarna
    impressions   INTEGER NOT NULL DEFAULT 0,
    successes     INTEGER NOT NULL DEFAULT 0  -- p.ej. clics (para CTR)
);
"""


def init(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)
    con.commit()


def design(con: sqlite3.Connection, *, hypothesis: str, variable: str, variants: list[dict],
           context: dict | None = None, now: int | None = None) -> int:
    """Diseña un experimento: una hipótesis falsable + variantes que aíslan UNA variable."""
    if len(variants) < 2:
        raise ValueError("un experimento necesita al menos 2 variantes para comparar.")
    now = now or int(time.time())
    eid = con.execute(
        "INSERT INTO experiment (hypothesis, variable, context, created_at) VALUES (?,?,?,?)",
        (hypothesis, variable, json.dumps(context or {}), now)).lastrowid
    for v in variants:
        con.execute(
            "INSERT INTO experiment_variant (experiment_id, label, description, tags) "
            "VALUES (?,?,?,?)",
            (eid, v["label"], v.get("description", ""), json.dumps(v.get("tags") or [])))
    con.commit()
    return eid


def record_result(con: sqlite3.Connection, *, experiment_id: int, label: str,
                  impressions: int, successes: int) -> None:
    """Resultado MEDIDO de una variante (tras publicar). No predicho."""
    if successes > impressions or impressions < 0 or successes < 0:
        raise ValueError("datos inválidos: 0 <= successes <= impressions")
    con.execute(
        "UPDATE experiment_variant SET impressions=?, successes=? "
        "WHERE experiment_id=? AND label=?", (impressions, successes, experiment_id, label))
    con.commit()


def _two_proportion_z(s1: int, n1: int, s2: int, n2: int) -> float | None:
    if n1 == 0 or n2 == 0:
        return None
    p1, p2 = s1 / n1, s2 / n2
    p = (s1 + s2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return None if se == 0 else (p1 - p2) / se


def resolve(con: sqlite3.Connection, experiment_id: int, *, alpha_z: float = 1.96,
            min_impressions: int = 100) -> dict:
    """Compara variantes y declara ganador SOLO si la diferencia es estadísticamente sólida.

    Si la muestra es pequeña o la diferencia no supera el umbral, devuelve 'inconclusive' y el
    laboratorio NO aprende de ese resultado (evita calibrar sobre ruido).
    """
    rows = con.execute(
        "SELECT label, impressions, successes FROM experiment_variant WHERE experiment_id=?",
        (experiment_id,)).fetchall()
    rates = [{"label": r["label"], "impressions": r["impressions"], "successes": r["successes"],
              "rate": round(r["successes"] / r["impressions"], 4) if r["impressions"] else 0.0}
             for r in rows]
    rates.sort(key=lambda x: x["rate"], reverse=True)

    top, second = rates[0], rates[1]
    z = _two_proportion_z(top["successes"], top["impressions"],
                          second["successes"], second["impressions"])
    underpowered = (top["impressions"] < min_impressions or second["impressions"] < min_impressions)
    significant = (z is not None) and (abs(z) >= alpha_z) and not underpowered

    if significant:
        status, winner = "resolved", top["label"]
        note = f"ganador '{winner}' (z={round(z, 2)}, significativo)"
    else:
        status, winner = "inconclusive", None
        reason = "muestra insuficiente" if underpowered else "diferencia no significativa"
        note = f"INCONCLUSO ({reason}) — el laboratorio NO aprende de esto (sería ruido)"

    con.execute("UPDATE experiment SET status=?, winner=? WHERE id=?",
                (status, winner, experiment_id))
    con.commit()
    return {"status": status, "winner": winner, "significant": significant,
            "z": round(z, 3) if z is not None else None, "rates": rates, "note": note}
