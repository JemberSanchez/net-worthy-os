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
from .. import db


def _theme_prevalence(con: sqlite3.Connection, domain: str) -> dict[str, int]:
    rows = con.execute(
        "SELECT value, COUNT(*) AS n FROM signal WHERE domain=? AND name='theme' GROUP BY value",
        (domain,),
    ).fetchall()
    return {r["value"]: r["n"] for r in rows}


def generate(con: sqlite3.Connection, *, domain: str = "content",
             min_prevalence: int = 3, demand_top_k: int = 8,
             demand_min_videos: int = 2, demand_min_norm: float = 0.15,
             now: int | None = None) -> list[int]:
    """Genera hipótesis candidatas de DOS orígenes y devuelve los ids creados:

    1. PRESENCIA (RSS): temas prevalentes y en alza en titulares (ponderados por demanda).
    2. DEMANDA (YouTube): frases específicas que mueven muchas vistas AUNQUE RSS no las levante.
       Este segundo origen ataca la raíz del detector débil: RSS solo produce tokens genéricos;
       las frases de alta demanda ('stock market', 'michael saylor') son temas reales.
    """
    prevalence = _theme_prevalence(con, domain)
    mom = compute_momentum()
    rising = {x["term"]: x["momentum"] for x in mom["rising"]}
    declining = {x["term"] for x in mom["declining"]}

    # DEMANDA real (vistas de YouTube), cacheada por 'youtube-scan'. Vacío -> demand=0 (idéntico
    # al comportamiento previo). Normalizamos por el máximo del cache -> feature en [0, 1].
    demand = db.fetch_theme_demand()
    max_demand = max(demand.values(), default=0)

    # palabras ya cubiertas por una FRASE candidata fuerte -> el token suelto se omite
    # (p.ej. con 'prime day' presente, se descartan 'prime' y 'day' por separado)
    covered: set[str] = set()
    for term in rising:
        if " " in term and prevalence.get(term, 0) >= min_prevalence:
            covered.update(term.split())

    created: list[int] = []
    created_terms: set[str] = set()

    # --- Origen 1: PRESENCIA editorial (RSS), ponderada por demanda ---
    for term, m in rising.items():
        p = prevalence.get(term, 0)
        if p < min_prevalence:
            continue
        is_phrase = " " in term
        if not is_phrase and term in covered:
            continue  # token suelto redundante: una frase ya lo representa mejor
        contradiction = 1.0 if term in declining else 0.0
        d_views = demand.get(term, 0)
        d_norm = round(d_views / max_demand, 3) if max_demand else 0.0
        # confianza heurística v0: modesta; las frases (más específicas) reciben un plus
        conf = max(0.05, min(0.80, 0.45 + 0.08 * m - 0.20 * contradiction
                             + (0.10 if is_phrase else 0.0)))
        for_ev = [f"'{term}' aparece en {p} items observados",
                  f"momentum {round(m, 2)} (en alza)"]
        if d_views:
            for_ev.append(f"demanda real: {d_views:,} vistas en YouTube (nicho)")
        evidence = {
            "features": {"momentum": round(m, 3), "prevalence": p,
                         "contradiction": contradiction, "demand": d_norm},
            "signals": [{"name": "theme", "value": term, "count": p}],
            "for": for_ev,
            "against": ([f"'{term}' también aparece en temas en declive (señal mixta)"]
                        if contradiction else []),
        }
        hid = hypotheses.create_hypothesis(
            con, domain=domain, statement=f"Demanda creciente en torno a '{term}'",
            confidence=round(conf, 3), evidence=evidence, now=now)
        created.append(hid)
        created_terms.add(term)

    # --- Origen 2: DEMANDA (YouTube ORIGINA temas, no solo pondera) ---
    # Solo FRASES (bigramas): el espacio de tokens sueltos ya lo cubre RSS y ahí está el ruido
    # genérico ('news', 'live'); una frase específica de alta demanda SÍ es un tema real.
    if max_demand:
        added = 0
        for row in db.fetch_theme_demand_full():
            if added >= demand_top_k:
                break
            term = row["term"]
            if " " not in term:                       # solo frases
                continue
            if term in created_terms:                 # ya la levantó RSS: no duplicar
                continue
            if row["videos"] < demand_min_videos:     # anti-ruido: >=N videos distintos
                continue
            d_norm = round(row["total_views"] / max_demand, 3)
            if d_norm < demand_min_norm:              # descarta la cola débil
                continue
            m = rising.get(term, 0.0)                 # si además sube en RSS, lo aprovechamos
            contradiction = 1.0 if term in declining else 0.0
            # confianza base mayor que un token RSS suelto: una frase con demanda real es
            # una candidata fuerte por sí misma (la feature 'demand' aporta el resto del score).
            conf = max(0.05, min(0.85, 0.50 + 0.08 * m - 0.20 * contradiction))
            evidence = {
                "features": {"momentum": round(m, 3), "prevalence": prevalence.get(term, 0),
                             "contradiction": contradiction, "demand": d_norm},
                "signals": [{"name": "youtube_demand", "value": term, "count": row["videos"]}],
                "for": [f"demanda real: {row['total_views']:,} vistas en YouTube (nicho)",
                        f"tema específico (frase) presente en {row['videos']} videos distintos",
                        f"ej.: {row['example']}" if row["example"] else "originado por demanda"],
                "against": ([f"'{term}' también aparece en temas en declive (señal mixta)"]
                            if contradiction else
                            ["origen: demanda de audiencia, no presencia editorial (a validar)"]),
            }
            hid = hypotheses.create_hypothesis(
                con, domain=domain, statement=f"Demanda creciente en torno a '{term}'",
                confidence=round(conf, 3), evidence=evidence, now=now)
            created.append(hid)
            created_terms.add(term)
            added += 1

    return created
