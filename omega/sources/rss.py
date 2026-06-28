"""Fuente RSS/Atom. Gratis, sin API key. Funciona hoy mismo."""
from __future__ import annotations
import calendar
import html
import re
import time
import feedparser

from .base import ContentItem

_TAGS = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _clean(text: str) -> str:
    """Quita etiquetas HTML y decodifica entidades (&amp; -> &). Vital para feeds de Reddit."""
    if not text:
        return ""
    text = _TAGS.sub(" ", text)
    text = html.unescape(text)
    return _WS.sub(" ", text).strip()


def _to_epoch(struct) -> int | None:
    if not struct:
        return None
    try:
        return calendar.timegm(struct)  # struct_time UTC -> epoch
    except Exception:
        return None


# Reddit (y otros) bloquean el user-agent por defecto de feedparser -> usamos uno de navegador.
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def fetch_feed(source: str, url: str) -> list[ContentItem]:
    now = int(time.time())
    parsed = feedparser.parse(url, agent=_UA)
    items: list[ContentItem] = []
    for e in parsed.entries:
        ext_id = e.get("id") or e.get("link") or e.get("title")
        if not ext_id:
            continue
        published = _to_epoch(e.get("published_parsed") or e.get("updated_parsed"))
        items.append(ContentItem(
            source=source,
            external_id=str(ext_id)[:500],
            title=_clean(e.get("title") or "")[:1000],
            summary=_clean(e.get("summary") or "")[:4000],
            url=(e.get("link") or "")[:1000],
            published_at=published,
            ingested_at=now,
        ))
    return items


def fetch_all(feeds: list[dict]) -> tuple[list[ContentItem], list[str]]:
    """Devuelve (items, errores). Una fuente caída no tumba la ingesta."""
    all_items: list[ContentItem] = []
    errors: list[str] = []
    for f in feeds:
        try:
            got = fetch_feed(f["source"], f["url"])
            all_items.extend(got)
            print(f"  [{f['source']:<16}] {len(got):>3} items")
        except Exception as exc:  # noqa: BLE001 — resiliencia: seguir con el resto
            errors.append(f"{f['source']}: {exc}")
            print(f"  [{f['source']:<16}] ERROR: {exc}")
    return all_items, errors
