"""Fuente YouTube Data API v3 — señal de DEMANDA REAL (vistas), no solo presencia editorial.

A diferencia del RSS (que mide en cuántos ARTÍCULOS aparece un tema), YouTube nos dice
cuántas VISTAS mueve realmente un tema: la señal que de verdad importa para decidir qué crear.

Usa solo la librería estándar (urllib) — sin google-api-python-client, sin instalar nada.
La key se resuelve del entorno (YOUTUBE_API_KEY, cargada de .env por config); nunca se hardcodea.

Cuota: search.list cuesta 100 unidades, videos.list ~1. Con 10.000/día (gratis) caben ~90
búsquedas diarias, de sobra para este uso.
"""
from __future__ import annotations
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

# config carga .env al importarse -> YOUTUBE_API_KEY queda disponible en os.environ.
from .. import config  # noqa: F401  (import por efecto secundario: _load_dotenv)

_API = "https://www.googleapis.com/youtube/v3"


class YouTubeError(RuntimeError):
    """Fallo de red, cuota agotada o key inválida. El caller decide cómo degradar."""


def _key() -> str:
    k = os.environ.get("YOUTUBE_API_KEY")
    if not k:
        raise YouTubeError("Falta YOUTUBE_API_KEY. Ponla en el archivo .env de la raíz.")
    return k


def _get(endpoint: str, params: dict) -> dict:
    query = urllib.parse.urlencode({**params, "key": _key()})
    req = urllib.request.Request(f"{_API}/{endpoint}?{query}",
                                 headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        # 403 con 'quotaExceeded' o 'API key not valid' llegan aquí -> mensaje útil.
        raise YouTubeError(f"HTTP {exc.code}: {body[:300]}") from exc
    except urllib.error.URLError as exc:
        raise YouTubeError(f"Sin conexión: {exc.reason}") from exc


def search_video_ids(query: str, published_after: str | None = None,
                     max_results: int = 25, order: str = "viewCount") -> list[str]:
    """IDs de videos que matchean la búsqueda. order='viewCount' -> más vistos primero."""
    params = {"part": "id", "q": query, "type": "video", "order": order,
              "maxResults": min(max_results, 50), "relevanceLanguage": "en"}
    if published_after:
        params["publishedAfter"] = published_after  # RFC3339, p.ej. 2026-06-07T00:00:00Z
    data = _get("search", params)
    return [it["id"]["videoId"] for it in data.get("items", [])
            if it.get("id", {}).get("videoId")]


def video_stats(ids: list[str]) -> list[dict]:
    """Estadísticas reales (vistas/likes/comentarios) de cada video. Batches de 50 (1 unidad c/u)."""
    out: list[dict] = []
    for i in range(0, len(ids), 50):
        chunk = ids[i:i + 50]
        data = _get("videos", {"part": "snippet,statistics", "id": ",".join(chunk)})
        for it in data.get("items", []):
            sn, st = it.get("snippet", {}), it.get("statistics", {})
            out.append({
                "video_id": it["id"],
                "title": sn.get("title", ""),
                "channel": sn.get("channelTitle", ""),
                "published_at": sn.get("publishedAt", ""),
                "views": int(st.get("viewCount", 0) or 0),
                "likes": int(st.get("likeCount", 0) or 0),
                "comments": int(st.get("commentCount", 0) or 0),
                "url": f"https://youtu.be/{it['id']}",
            })
    return out


def fetch_recent(query: str, days: int = 30, max_results: int = 25,
                 order: str = "viewCount") -> list[dict]:
    """Videos recientes de una búsqueda con sus vistas reales, ordenados por vistas desc."""
    published_after = None
    if days:
        published_after = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime(time.time() - days * 86400))
    ids = search_video_ids(query, published_after, max_results, order)
    stats = video_stats(ids)
    stats.sort(key=lambda v: v["views"], reverse=True)
    return stats
