"""Adaptador de LLM — el hook al modelo que el director creativo necesita para PENSAR.

Agnóstico de proveedor por diseño (hoy: Anthropic). Expone una interfaz mínima `complete()`
con NIVELES (tiers) para el pipeline coste/calidad:
  - fast  → barato, alto volumen (divergencia): Claude Haiku 4.5
  - smart → el caballo de batalla (juicio, refinamiento): Claude Opus 4.8   [default]
  - max   → máxima capacidad (lo más difícil): Claude Fable 5

Degradación a $0: sin ANTHROPIC_API_KEY, get_llm() devuelve un NullLLM que opera en modo
export-prompt (no llama a nada, no cuesta nada) — coherente con el resto del sistema.
"""
from .adapter import AnthropicLLM, NullLLM, get_llm, make_think_fn  # noqa: F401
