"""Demanda por tema desde VISTAS reales de YouTube (no volumen editorial).

El momentum de RSS responde "¿de qué se habla?" (presencia en artículos). Esto responde
"¿qué mueve vistas?" (demanda real de la audiencia). Sumamos las vistas de cada término de
contenido que aparece en los títulos: un tema que sale en videos muy vistos sube; uno que solo
sale en videos ignorados, no. Ese es el detector de temas serio que faltaba.
"""
from __future__ import annotations
import time
from collections import defaultdict
from datetime import datetime, timezone

from .momentum import _TOKEN as _TOKEN_WORDS  # mismo regex de token que los títulos
from .momentum import _terms  # mismo tokenizador (unigramas + bigramas, stopwords EN/ES)


def _agrupar_por_termino(videos: list[dict], peso, min_videos: int) -> list[tuple]:
    """Núcleo compartido por el ranking de demanda y el de evergreen: suma `peso(video)` por
    término del título, con el filtro anti-autobombo. Devuelve (term, total, n, ejemplos)."""
    total: dict[str, float] = defaultdict(float)
    count: dict[str, int] = defaultdict(int)
    examples: dict[str, list[str]] = defaultdict(list)

    for v in videos:
        # misma normalización que _terms (lowercase + apóstrofe tipográfico -> ASCII)
        channel_words = set(_TOKEN_WORDS.findall((v.get("channel") or "").lower().replace("’", "'")))
        for t in _terms(v.get("title", "")):
            if channel_words and set(t.split()) <= channel_words:
                continue  # autobombo: el término ES (parte de) el nombre del canal
            total[t] += peso(v)
            count[t] += 1
            if len(examples[t]) < 2:
                examples[t].append(v.get("title", ""))

    return [(t, total[t], count[t], examples[t]) for t in total if count[t] >= min_videos]


def views_per_day(video: dict, *, now: float | None = None) -> float:
    """Vistas por día desde que se publicó. Es la métrica que separa un catálogo VIVO de uno que
    solo es viejo: 300.000 vistas en 300 días (1.000/día) valen más que 300.000 en 3 años.

    ⚠ CAVEAT HONESTO: es un promedio sobre toda la vida del video, así que NO distingue
    'explotó la primera semana y murió' de 'acumula constante'. Para eso hacen falta dos escaneos
    separados en el tiempo y comparar el delta — que es exactamente lo que `theme_demand_history`
    ya hace para la demanda de noticia. Hasta entonces, tratar esto como una APROXIMACIÓN.
    """
    pub = (video.get("published_at") or "").strip()
    if not pub:
        return 0.0
    try:
        dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    ahora = now if now is not None else time.time()
    edad_dias = (ahora - dt.timestamp()) / 86400
    if edad_dias < 1:
        edad_dias = 1.0            # un video de hoy no tiene velocidad medible: no lo infles
    return video.get("views", 0) / edad_dias


def theme_demand(videos: list[dict], min_videos: int = 2) -> list[dict]:
    """Ranking de términos por vistas totales acumuladas en los títulos de los videos.

    min_videos: un término debe aparecer en >=N videos distintos para contar (anti-ruido:
    evita que un único video viral infle un término que solo él usa).

    ANTI-AUTOBOMBO: un canal que pone su nombre en sus títulos ("CryptoNews Net: ...") convierte
    su marca en falso "tema de demanda" — y min_videos no protege (el mismo canal aporta N
    videos). Por eso un término cuyas palabras salgan todas del nombre del PROPIO canal se
    descarta para ese video. Si otros canales usan la frase como tema real, sobrevive por ellos.
    Es filtro en origen, no stoplist manual (que sería deuda de mantenimiento infinita)."""
    rows = [{
        "term": t,
        "total_views": int(total),
        "videos": n,
        "avg_views": int(total) // max(n, 1),
        "examples": ej,
    } for t, total, n, ej in _agrupar_por_termino(videos, lambda v: v.get("views", 0), min_videos)]

    rows.sort(key=lambda r: r["total_views"], reverse=True)
    return rows


def theme_evergreen(videos: list[dict], min_videos: int = 2,
                    *, now: float | None = None) -> list[dict]:
    """Ranking EVERGREEN: pondera por vistas/DÍA, no por vistas totales.

    Con `days=0` el barrido trae catálogo antiguo, y ahí las vistas totales premian a lo viejo por
    ser viejo. La velocidad es lo que dice si un tema sigue moviendo audiencia HOY."""
    rows = [{
        "term": t,
        "views_per_day": round(total, 1),
        "videos": n,
        "avg_views_per_day": round(total / max(n, 1), 1),
        "examples": ej,
    } for t, total, n, ej in _agrupar_por_termino(
        videos, lambda v: views_per_day(v, now=now), min_videos)]

    rows.sort(key=lambda r: r["views_per_day"], reverse=True)
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


def scan_evergreen(queries: list[str], *, min_age_days: int = 90, max_results: int = 25,
                   min_subs: int = 1_000, max_subs: int = 100_000,
                   min_like_rate: float = 0.01,
                   now: float | None = None) -> tuple[list[dict], list[dict]]:
    """Barrido EVERGREEN: el catálogo que `decide` no puede ver.

    POR QUÉ EXISTE (docs/VIRALIDAD.md §3.1, evidencia medida): de los 39 despegues del estudio,
    NINGUNO es noticia — tienen entre 133 y 352 días y siguen acumulando. Pero `youtube-scan` pide
    `publishedAfter = hoy - 30d`, así que **ese catálogo es literalmente invisible** para el
    sistema: solo puede proponer noticia. Y la noticia es justo lo que peor le fue al canal
    (el FED, único Short noticioso, hizo 10 espectadores).

    Reusa `fetch_recent(days=0)`, que ya omite `publishedAfter`, con `order=viewCount`. El guard
    de mercado (`_is_target_market`) protege este barrido igual que el de noticia.

    min_age_days: descarta lo reciente. Un video de la semana pasada no ha demostrado que aguante
    — VIRALIDAD.md §6 recomienda >=90 días para que el n útil sea sólido.

    min_subs/max_subs y min_like_rate replican el ÚNICO método que VIRALIDAD.md validó (§1,
    "Intento 3"): comparar solo dentro de canales del tamaño real de este canal, con engagement
    real. Sin la banda de suscriptores, el barrido devuelve lo que hacen los canales enormes y
    reproduce el confounder que ya invalidó el Intento 2 del estudio.
    """
    from ..sources import youtube  # import local: demand no depende de la red salvo aquí

    ahora = now if now is not None else time.time()
    seen: dict[str, dict] = {}
    for q in queries:
        for v in youtube.fetch_recent(q, days=0, max_results=max_results, order="viewCount"):
            pub = (v.get("published_at") or "").strip()
            if not pub:
                continue                       # sin fecha no hay edad ni velocidad: fuera
            try:
                dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            except ValueError:
                continue
            if (ahora - dt.timestamp()) / 86400 < min_age_days:
                continue                       # demasiado nuevo para llamarse evergreen
            if v.get("views", 0) and (v.get("likes", 0) / v["views"]) < min_like_rate:
                continue                       # engagement de humo: §3.3 fija el suelo en 1%
            v = {**v, "views_per_day": round(views_per_day(v, now=ahora), 1)}
            seen[v["video_id"]] = v

    videos = list(seen.values())
    # Tamaño de canal en un solo lote (1 unidad/50 canales): el filtro que hace comparable la
    # muestra con la situación real del canal.
    if videos and (min_subs or max_subs):
        subs = youtube.channel_subs([v.get("channel_id", "") for v in videos])
        dentro = []
        for v in videos:
            n = subs.get(v.get("channel_id", ""), 0)
            v["subs"] = n
            if n and min_subs <= n <= max_subs:
                dentro.append(v)
        videos = dentro

    return theme_evergreen(videos, now=ahora), videos


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
