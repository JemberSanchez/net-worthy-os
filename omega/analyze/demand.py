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


def scan_nicho(queries: list[str], days: int = 30, max_results: int = 25) -> tuple[list[dict], list[dict]]:
    """Barre varias búsquedas del nicho, DEDUPLICA videos entre queries y agrega la demanda.

    Devuelve (ranking_de_temas, videos_únicos). Un mismo video que aparece en dos búsquedas
    cuenta una sola vez (dedupe por video_id) para no inflar la demanda."""
    from ..sources import youtube  # import local: demand no depende de la red salvo aquí

    seen: dict[str, dict] = {}
    for q in queries:
        for v in youtube.fetch_recent(q, days=days, max_results=max_results):
            seen[v["video_id"]] = v
    videos = list(seen.values())
    return theme_demand(videos), videos


def related(root: str, videos: list[dict], top_k: int = 12, min_together: int = 2) -> list[dict]:
    """ADYACENCIA (#1): qué OTROS temas ven quienes ven 'root'. Co-ocurrencia en títulos,
    ponderada por vistas. No es el salto creativo (eso es el LLM/manual): es su INPUT de datos —
    'si la audiencia ve X, también le interesa Y'. Adelantarse = servir esa adyacencia desatendida.
    """
    root = root.lower().strip()
    root_words = set(root.split())  # match a NIVEL DE PALABRA, no subcadena ('ai' no debe pegar en 'retail')
    co_views: dict[str, int] = defaultdict(int)
    co_n: dict[str, int] = defaultdict(int)
    for v in videos:
        terms = _terms(v.get("title", ""))
        if root not in terms:
            continue
        for t in terms:
            # fuera el propio root y cualquier término que comparta una palabra con él
            if t == root or (root_words & set(t.split())):
                continue
            co_views[t] += v.get("views", 0)
            co_n[t] += 1
    rows = [{"term": t, "views": co_views[t], "together": co_n[t]}
            for t in co_views if co_n[t] >= min_together]
    rows.sort(key=lambda r: r["views"], reverse=True)
    return rows[:top_k]
