"""Estimación de idioma (es/en) por solapamiento de stopwords -> señal 'language'."""
from __future__ import annotations
import re

_ES = set("de la el los las una unos que con por para como pero más está cómo qué".split())
_EN = set("the of and to in is for with how that this you are not your what".split())
_TOK = re.compile(r"[a-záéíóúñü]+", re.IGNORECASE)


class LanguageExtractor:
    name = "language"
    version = "0.1.0"

    def extract(self, asset: dict) -> list[dict]:
        text = f"{asset.get('title', '') or ''} {asset.get('summary', '') or ''}".lower()
        toks = _TOK.findall(text)
        es = sum(t in _ES for t in toks)
        en = sum(t in _EN for t in toks)
        if es == 0 and en == 0:
            lang, conf = "unknown", 0.2
        elif es >= en:
            lang, conf = "es", round(es / (es + en + 1e-9), 2)
        else:
            lang, conf = "en", round(en / (es + en + 1e-9), 2)
        return [{"name": "language", "value": lang, "kind": "categorical", "confidence": conf}]


EXTRACTOR = LanguageExtractor()
