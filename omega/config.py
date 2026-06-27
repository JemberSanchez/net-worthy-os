"""Configuración central. Sin secretos aquí; las API keys irán en .env (fases futuras)."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "omega.sqlite"
FEEDS_PATH = ROOT / "feeds.json"

# Ventanas de momentum (en días). "recent" vs "prior" para medir si un tema sube o baja.
RECENT_WINDOW_DAYS = 3
PRIOR_WINDOW_DAYS = 7          # baseline inmediatamente anterior a la ventana recent
MIN_RECENT_DOC_FREQ = 3       # un término debe aparecer en >=3 documentos recientes (anti-ruido)
TOP_N = 15


def load_feeds() -> list[dict]:
    data = json.loads(FEEDS_PATH.read_text(encoding="utf-8"))
    return [f for f in data.get("feeds", []) if "url" in f and "source" in f]
