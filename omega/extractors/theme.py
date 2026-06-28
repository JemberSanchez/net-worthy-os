"""Extractor de tema: términos clave del título -> señales 'theme'."""
from __future__ import annotations
from ..analyze.momentum import _terms


class ThemeExtractor:
    name = "theme"
    version = "0.2.0"  # v0.2: incluye bigramas; frases primero

    def extract(self, asset: dict) -> list[dict]:
        # frases (bigramas) antes que palabras sueltas -> temas reales, no tokens
        terms = sorted(_terms(asset.get("title", "") or ""),
                       key=lambda t: (" " not in t, t))[:6]
        return [{"name": "theme", "value": t, "kind": "categorical", "confidence": 0.5}
                for t in terms]


EXTRACTOR = ThemeExtractor()
