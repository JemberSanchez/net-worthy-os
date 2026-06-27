"""Longitud del título como señal numérica (proxy de estilo) -> señal 'title_length'."""
from __future__ import annotations


class TitleLengthExtractor:
    name = "title_length"
    version = "0.1.0"

    def extract(self, asset: dict) -> list[dict]:
        n = len(asset.get("title", "") or "")
        return [{"name": "title_length", "value_num": float(n),
                 "kind": "numeric", "confidence": 1.0}]


EXTRACTOR = TitleLengthExtractor()
