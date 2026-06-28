"""Implementación del adaptador de LLM (SDK oficial de Anthropic).

Convenciones (referencia oficial claude-api): modelo por defecto claude-opus-4-8, adaptive
thinking para pasos de razonamiento, streaming + get_final_message para evitar timeouts.
La API key se resuelve del entorno (ANTHROPIC_API_KEY); nunca se hardcodea.
"""
from __future__ import annotations
import os
from typing import Protocol


# Niveles -> modelos. El kernel/dominio piden un tier; aquí se mapea al modelo concreto.
MODELS = {
    "fast": "claude-haiku-4-5",   # barato, alto volumen (divergencia)
    "smart": "claude-opus-4-8",   # default: juicio, refinamiento, escritura
    "max": "claude-fable-5",      # máxima capacidad, lo más difícil
}


class LLM(Protocol):
    name: str

    def complete(self, prompt: str, *, system: str | None = None,
                 tier: str = "smart", max_tokens: int = 8000) -> str | None:
        ...


class NullLLM:
    """Sin modelo: modo export-prompt a $0. complete() siempre devuelve None (queda pendiente)."""
    name = "ninguno ($0, modo export-prompt)"

    def complete(self, prompt: str, *, system: str | None = None,
                 tier: str = "smart", max_tokens: int = 8000) -> str | None:
        return None


class AnthropicLLM:
    """Llama a Claude vía el SDK oficial. Tiers -> modelos; thinking adaptativo en smart/max."""
    name = "Anthropic (default Opus 4.8, tiered)"

    def __init__(self):
        import anthropic  # import perezoso: solo si de verdad se usa
        self.anthropic = anthropic
        self.client = anthropic.Anthropic()  # lee ANTHROPIC_API_KEY del entorno

    def complete(self, prompt: str, *, system: str | None = None,
                 tier: str = "smart", max_tokens: int = 8000) -> str | None:
        model = MODELS.get(tier, MODELS["smart"])
        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        if tier != "fast":  # razonamiento solo donde aporta (fast = rápido/barato, sin thinking)
            kwargs["thinking"] = {"type": "adaptive"}
        try:
            with self.client.messages.stream(**kwargs) as stream:  # streaming evita timeouts
                msg = stream.get_final_message()
        except self.anthropic.APIError as exc:  # red/clave/límite: degradar a None, no romper
            print(f"[llm] error de API: {exc}")
            return None
        if getattr(msg, "stop_reason", None) == "refusal":
            return None
        text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
        return text.strip() or None


def get_llm() -> LLM:
    """Devuelve un LLM real si hay ANTHROPIC_API_KEY; si no, NullLLM ($0)."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return AnthropicLLM()
        except Exception as exc:  # noqa: BLE001 — si el SDK no está, caer a $0
            print(f"[llm] no se pudo inicializar Anthropic ({exc}); usando modo $0")
    return NullLLM()


def make_think_fn(llm: LLM, *, tier: str = "smart"):
    """Convierte un LLM en el `think_fn` que espera creative.thinking.ThinkingSession."""
    def think(prompt: str) -> str | None:
        return llm.complete(prompt, tier=tier)
    return think
