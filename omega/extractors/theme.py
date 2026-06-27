"""Extractor de tema: términos clave del título -> señales 'theme'."""
from __future__ import annotations
from ..analyze.momentum import _terms


class ThemeExtractor:
    name = "theme"
    version = "0.1.0"

    def extract(self, asset: dict) -> list[dict]:
        terms = sorted(_terms(asset.get("title", "") or ""))[:3]
        return [{"name": "theme", "value": t, "kind": "categorical", "confidence": 0.5}
                for t in terms]


EXTRACTOR = ThemeExtractor()
