"""Demanda por tema desde VISTAS reales de YouTube (no volumen editorial).

El momentum de RSS responde "¿de qué se habla?" (presencia en artículos). Esto responde
"¿qué mueve vistas?" (demanda real de la audiencia). Sumamos las vistas de cada término de
contenido que aparece en los títulos: un tema que sale en videos muy vistos sube; uno que solo
sale en videos ignorados, no. Ese es el detector de temas serio que faltaba.
"""
from __future__ import annotations
from collections import defaultdict

from .momentum import _terms  # mismo tokenizador (unigramas + bigramas, stopwords EN/ES)


def theme_demand(videos: list[dict], min_videos: int = 2) -> list[dict]:
    """Ranking de términos por vistas totales acumuladas en los títulos de los videos.

    min_videos: un término debe aparecer en >=N videos distintos para contar (anti-ruido:
    evita que un único video viral infle un término que solo él usa)."""
    views: dict[str, int] = defaultdict(int)
    count: dict[str, int] = defaultdict(int)
    examples: dict[str, list[str]] = defaultdict(list)

    for v in videos:
        for t in _terms(v.get("title", "")):
            views[t] += v.get("views", 0)
            count[t] += 1
            if len(examples[t]) < 2:
                examples[t].append(v.get("title", ""))

    rows = [{
        "term": t,
        "total_views": views[t],
        "videos": count[t],
        "avg_views": views[t] // max(count[t], 1),
        "examples": examples[t],
    } for t in views if count[t] >= min_videos]

    rows.sort(key=lambda r: r["total_views"], reverse=True)
    return rows
