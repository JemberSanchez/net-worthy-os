"""Tests del adaptador de LLM. NO llaman a la API real — solo la lógica de selección y el modo $0."""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega.llm import adapter  # noqa: E402


class LLMAdapterTest(unittest.TestCase):
    def test_tiers_map_to_real_model_ids(self):
        self.assertEqual(adapter.MODELS["smart"], "claude-opus-4-8")   # default = caballo de batalla
        self.assertEqual(adapter.MODELS["fast"], "claude-haiku-4-5")
        self.assertEqual(adapter.MODELS["max"], "claude-fable-5")

    def test_without_api_key_get_llm_falls_back_to_zero_cost(self):
        saved = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            llm = adapter.get_llm()
            self.assertIsInstance(llm, adapter.NullLLM)
            # en modo $0, completar siempre devuelve None (queda pendiente de modelo)
            self.assertIsNone(llm.complete("piensa algo"))
        finally:
            if saved is not None:
                os.environ["ANTHROPIC_API_KEY"] = saved

    def test_make_think_fn_passes_through_none_in_zero_cost(self):
        think = adapter.make_think_fn(adapter.NullLLM())
        self.assertIsNone(think("¿y si un tiburón aprende a volar?"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
