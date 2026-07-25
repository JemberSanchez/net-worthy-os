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
import re
import time
import urllib.error
import urllib.parse
import urllib.request

# config carga .env al importarse -> YOUTUBE_API_KEY queda disponible en os.environ.
from .. import config  # noqa: F401  (import por efecto secundario: _load_dotenv)

_API = "https://www.googleapis.com/youtube/v3"

# Rangos Unicode de alfabetos NO latinos (árabe, índicos, tamil, CJK, kana, hangul, tailandés).
# Red secundaria: si el título está escrito en uno de estos, no es contenido en inglés.
_NON_LATIN = re.compile(
    r"[؀-ۿऀ-ॿঀ-৿਀-੿଀-୿஀-௿"
    r"ఀ-౿ഀ-ൿ฀-๿぀-ヿ㐀-鿿가-힯]")


# Idiomas que se auto-etiquetan en el título en alfabeto latino (shorts de "motivación" que
# declaran su lengua). Patrón observado que se cuela pese al filtro de alfabeto/idioma declarado.
_LANG_NAME = re.compile(
    r"\b(tamil|hindi|telugu|kannada|malayalam|marathi|bhojpuri|punjabi|urdu|bangla|bengali|"
    r"gujarati|odia|sinhala|nepali|pinoy|tagalog|filipino)\b", re.IGNORECASE)


# ── Guard de MERCADO (distinto del de idioma) ─────────────────────────────────────────────────
# El idioma NO es el mercado. Un video indio escrito en inglés pasa `_is_english` (su
# defaultAudioLanguage ES 'en') y aun así vale ~10x menos: RPM de audiencia IN ~$1-3 contra
# $10-40 en US/EN, y el RPM es justo la variable que `decide` pondera. `relevanceLanguage` y
# `regionCode` solo SESGAN el ranking de la búsqueda; no excluyen nada.
# Caso real que disparó este guard (2026-07-24): 'build wealth' ganó `decide` con 1.812.824
# vistas de las que el 70% venían de canales indios (Indiabulls "Stock SIP", "₹2 Lakh").
_MARKET_SYMBOL = re.compile(r"[₹₨₦₱]")  # rupia india/pakistaní, naira, peso filipino

# Términos inequívocos de otro mercado. Deliberadamente CONSERVADOR: quedan fuera las palabras
# que también son inglés corriente ('nifty' = ingenioso, 'sip' = sorbo, 'RBI' = runs batted in
# en béisbol — este corpus ya sufrió una fuga deportiva) salvo en su forma no ambigua.
_MARKET_TERM = re.compile(
    r"\b(lakh|lakhs|crore|crores|rupee|rupees|sensex|demat|"
    r"nifty\s*50|bank\s*nifty)\b", re.IGNORECASE)

# Acrónimos de institución/mercado. SENSIBLES A MAYÚSCULAS a propósito: así 'sip' (beber) no
# colisiona con 'SIP' (Systematic Investment Plan).
_MARKET_ACRONYM = re.compile(r"\b(NSE|BSE|SEBI|ELSS|PPF|UPI|SIP)\b")

# Solo para el NOMBRE DEL CANAL: un canal que se llama a sí mismo por un país está declarando su
# mercado. No se aplica al título, donde "India's economy" es un tema legítimo para un canal US.
_MARKET_CHANNEL = re.compile(r"\b(india|indian|bharat|pakistan|nigeria|philippines)\b",
                             re.IGNORECASE)


def _is_target_market(video: dict) -> bool:
    """True si el video apunta al mercado que paga (US/EN). Complementa `_is_english`, no lo
    sustituye: filtra contenido EN CORRECTO INGLÉS pero dirigido a otro mercado, que infla la
    demanda y envenena el prior de RPM. Guard de captura-en-origen: se rechaza ANTES de entrar
    a `scanned_video`, no se limpia después."""
    title = video.get("title", "")
    if _MARKET_SYMBOL.search(title) or _MARKET_TERM.search(title) or _MARKET_ACRONYM.search(title):
        return False
    channel = video.get("channel", "")
    if (_MARKET_SYMBOL.search(channel) or _MARKET_TERM.search(channel)
            or _MARKET_ACRONYM.search(channel) or _MARKET_CHANNEL.search(channel)):
        return False
    return True


def _is_english(video: dict) -> bool:
    """True si el video es inglés. El TÍTULO manda: si se delata (alfabeto no-latino o nombre de
    idioma auto-declarado como 'Tamil Motivation'), se descarta AUNQUE declare audio 'en' — muchos
    canales mislabelan su audio. Solo si el título no se delata se usa el idioma declarado como
    segundo filtro. Cierra la fuga de contenido no-EN que baja el RPM y ensucia la señal."""
    title = video.get("title", "")
    if _NON_LATIN.search(title) or _LANG_NAME.search(title):
        return False  # el título delata no-inglés: no confiar en una etiqueta de audio mentida
    lang = (video.get("language") or "").lower()
    if lang:
        return lang.startswith("en")
    return True


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
              "maxResults": min(max_results, 50), "relevanceLanguage": "en",
              "regionCode": "US"}  # localiza a EE.UU.: recorta contenido de otros mercados en origen
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
                "channel_id": sn.get("channelId", ""),
                "published_at": sn.get("publishedAt", ""),
                "language": sn.get("defaultAudioLanguage") or sn.get("defaultLanguage") or "",
                "views": int(st.get("viewCount", 0) or 0),
                "likes": int(st.get("likeCount", 0) or 0),
                "comments": int(st.get("commentCount", 0) or 0),
                "url": f"https://youtu.be/{it['id']}",
            })
    return out


def channel_subs(channel_ids: list[str]) -> dict[str, int]:
    """{channel_id: suscriptores}. Batches de 50, 1 unidad de cuota cada uno (barato).

    Existe para replicar el método que `docs/VIRALIDAD.md` §1 validó: comparar SOLO dentro de
    canales del tamaño real de este canal. Sin esto, un barrido por vistas devuelve lo que hacen
    los canales de 166.000 subs — y ahí "lo que distingue a los ganadores" puede ser simplemente
    TENER audiencia. Ese confounder invalidó el Intento 2 del estudio.
    """
    out: dict[str, int] = {}
    ids = [c for c in dict.fromkeys(channel_ids) if c]
    for i in range(0, len(ids), 50):
        data = _get("channels", {"part": "statistics", "id": ",".join(ids[i:i + 50])})
        for it in data.get("items", []):
            try:
                out[it["id"]] = int(it.get("statistics", {}).get("subscriberCount", 0) or 0)
            except (TypeError, ValueError):
                out[it["id"]] = 0
    return out


def fetch_recent(query: str, days: int = 30, max_results: int = 25,
                 order: str = "viewCount", english_only: bool = True,
                 target_market_only: bool = True) -> list[dict]:
    """Videos recientes de una búsqueda con sus vistas reales, ordenados por vistas desc.

    english_only (por defecto): descarta contenido no-inglés. El nicho paga por audiencia EN
    (RPM alto); el contenido en otros idiomas ensucia la señal y diluye el RPM.

    target_market_only (por defecto): descarta contenido en inglés CORRECTO pero dirigido a otro
    mercado (India, etc.). Son dos filtros distintos a propósito: el idioma no es el mercado."""
    published_after = None
    if days:
        published_after = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime(time.time() - days * 86400))
    ids = search_video_ids(query, published_after, max_results, order)
    stats = video_stats(ids)
    if english_only:
        stats = [v for v in stats if _is_english(v)]
    if target_market_only:
        stats = [v for v in stats if _is_target_market(v)]
    stats.sort(key=lambda v: v["views"], reverse=True)
    return stats
