"""Configuración central. Sin secretos aquí; las API keys viven en .env (gitignored)."""
from __future__ import annotations
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "omega.sqlite"
FEEDS_PATH = ROOT / "feeds.json"


def _load_dotenv() -> None:
    """Carga ROOT/.env en os.environ, sin dependencias externas.

    No pisa variables ya presentes en el entorno (setdefault): quien exporta a mano gana.
    Formato: líneas 'CLAVE=valor'; ignora vacías y comentarios (#). Comillas opcionales."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


_load_dotenv()

# Ventanas de momentum (en días). "recent" vs "prior" para medir si un tema sube o baja.
RECENT_WINDOW_DAYS = 3
PRIOR_WINDOW_DAYS = 7          # baseline inmediatamente anterior a la ventana recent
MIN_RECENT_DOC_FREQ = 3       # un término debe aparecer en >=3 documentos recientes (anti-ruido)
TOP_N = 15


# Strategy Profile: pesos que el DOMINIO pasa al Decision Engine del kernel.
# El kernel NO conoce el significado de estas features; solo hace el producto peso·feature.
DECISION_WEIGHTS = {"momentum": 0.05, "prevalence": 0.0, "contradiction": -0.30}
ABSTAIN_THRESHOLD = 0.50          # si el mejor score < umbral -> ABSTENERSE
PREDICTION_HORIZON_DAYS = 14      # a cuántos días se verifica la predicción


def load_feeds() -> list[dict]:
    data = json.loads(FEEDS_PATH.read_text(encoding="utf-8"))
    return [f for f in data.get("feeds", []) if "url" in f and "source" in f]
