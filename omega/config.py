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
#   demand          = vistas totales de YouTube (0..1). Cuánta atención mueve el tema.
#   gap             = vistas por video (0..1). #3 HUECO: mucha demanda + poca oferta = entrar
#                     en lo DESATENDIDO, no seguir lo saturado. "Adelantarse" a lo desabastecido.
#   demand_momentum = log2 del cambio de demanda entre escaneos. #2: demanda SUBIENDO = indicador
#                     adelantado (entrar en la ola, no en el pico). Necesita >=2 escaneos.
# Pesos altos en demanda A PROPÓSITO: la audiencia manda sobre la mera presencia en titulares.
DECISION_WEIGHTS = {"momentum": 0.05, "prevalence": 0.0, "contradiction": -0.30,
                    "demand": 0.35, "gap": 0.20, "demand_momentum": 0.15}
ABSTAIN_THRESHOLD = 0.50          # si el mejor score < umbral -> ABSTENERSE
PREDICTION_HORIZON_DAYS = 14      # a cuántos días se verifica la predicción

# Búsquedas que definen el NICHO en YouTube (finanzas/inversiones/crypto, audiencia EN).
# 'youtube-scan' las barre para medir qué temas mueven vistas reales. ~100 unidades/query.
#
# PRINCIPIO DE DISEÑO (aprendido): evitar framings de CATEGORÍA/STREAM ('today', 'live', 'news',
# 'tips', 'for beginners') -> arrastran directos en vivo con títulos genéricos ('live updates').
# Preferir framings de NARRATIVA/ENTIDAD/EVENTO (análisis con tesis, empresas/tickers, nombres
# propios, eventos macro, forecast) -> emergen frases-HISTORIA, no frases-categoría. Siguen siendo
# áreas de descubrimiento amplias, no una historia concreta (eso lo descubre la demanda).
YOUTUBE_NICHE_QUERIES = [
    "stock market analysis",           # análisis con tesis (no stream "live today")
    "best stocks to buy now",          # saca empresas/tickers concretos
    "bitcoin price prediction",        # crypto forward-looking, con historia
    "warren buffett investing",        # personalidad -> temas específicos
    "federal reserve interest rates",  # macro/evento con narrativa
    "housing market forecast",         # real estate/macro, no "today"
    "how to build wealth",             # personal finance aspiracional (faceless-friendly)
]


def load_feeds() -> list[dict]:
    data = json.loads(FEEDS_PATH.read_text(encoding="utf-8"))
    return [f for f in data.get("feeds", []) if "url" in f and "source" in f]
