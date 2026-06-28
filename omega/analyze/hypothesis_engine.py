"""Hypothesis Engine v0 — capa de DOMINIO (contenido).

Convierte señales dispersas en hipótesis candidatas. v0 = REGLAS transparentes (no LLM, no
embeddings): un tema PREVALENTE y EN ALZA sugiere demanda creciente. Es explicable y barato.

ESTE algoritmo es el que cambiará 20 veces durante el primer año (clustering, embeddings, LLM,
mezclas). Está aislado a propósito: el kernel (Decision Engine) no cambia cuando esto cambie.
Interpreta el significado de las señales ('theme', 'momentum') -> por eso vive en el dominio.
"""
from __future__ import annotations
import sqlite3

from .momentum import compute as compute_momentum
from ..reasoning import hypotheses


def _theme_prevalence(con: sqlite3.Connection, domain: str) -> dict[str, int]:
    rows = con.execute(
        "SELECT value, COUNT(*) AS n FROM signal WHERE domain=? AND name='theme' GROUP BY value",
        (domain,),
    ).fetchall()
    return {r["value"]: r["n"] for r in rows}


def generate(con: sqlite3.Connection, *, domain: str = "content",
             min_prevalence: int = 3, now: int | None = None) -> list[int]:
    """Genera hipótesis candidatas. Devuelve los ids creados."""
    prevalence = _theme_prevalence(con, domain)
    mom = compute_momentum()
    rising = {x["term"]: x["momentum"] for x in mom["rising"]}
    declining = {x["term"] for x in mom["declining"]}

    created: list[int] = []
    for term, m in rising.items():
        p = prevalence.get(term, 0)
        if p < min_prevalence:
            continue
        contradiction = 1.0 if term in declining else 0.0
        # confianza heurística v0: modesta y honesta con datos escasos
        conf = max(0.05, min(0.80, 0.45 + 0.08 * m - 0.20 * contradiction))
        evidence = {
            "features": {"momentum": round(m, 3), "prevalence": p, "contradiction": contradiction},
            "signals": [{"name": "theme", "value": term, "count": p}],
            "for": [f"'{term}' aparece en {p} items observados",
                    f"momentum {round(m, 2)} (en alza)"],
            "against": ([f"'{term}' también aparece en temas en declive (señal mixta)"]
                        if contradiction else []),
        }
        hid = hypotheses.create_hypothesis(
            con, domain=domain, statement=f"Demanda creciente en torno a '{term}'",
            confidence=round(conf, 3), evidence=evidence, now=now)
        created.append(hid)
    return created
