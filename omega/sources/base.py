"""Interfaz común de fuentes de datos. El core solo conoce esta abstracción."""
from __future__ import annotations
from typing import Protocol, TypedDict


class ContentItem(TypedDict):
    source: str
    external_id: str
    title: str
    summary: str
    url: str
    published_at: int | None  # epoch segundos
    ingested_at: int


class Source(Protocol):
    """Toda fuente (RSS, YouTube, Reddit...) implementa fetch()."""
    name: str

    def fetch(self) -> list[ContentItem]:
        ...
