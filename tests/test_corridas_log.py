"""renders/corridas.jsonl names the exact rule that failed, not just the gate ("storyboard" x26 on 13-nov)."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

RUTA = Path(__file__).resolve().parent.parent / "video-v2" / "motor" / "producir.py"
sys.path.insert(0, str(RUTA.parent))
_spec = importlib.util.spec_from_file_location("producir_corridas_test", RUTA)
P = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(P)

STORYBOARD = (
    "✗ storyboard inválido:\n"
    "  - escena 3: cifra '$1.2M' sin fuente\n"
    "  - sonidos[0]: sfx 'gong' no está en el catálogo (caja, sello)\n"
)


class CorridasTest(unittest.TestCase):
    def test_log_line_lists_each_failing_rule(self):
        detalles = {
            "storyboard": (False, STORYBOARD),
            "repeticion": (True, "ok"),
            "guion": (False, "✗ G2: gancho de 19 palabras (máx. 14)\n"),
        }
        with tempfile.TemporaryDirectory() as d:
            reg = Path(d) / "renders" / "corridas.jsonl"
            reg.parent.mkdir()
            P.registrar_corrida(
                reg,
                0.0,
                "✗ puertas fallidas: storyboard, guion",
                [],
                detalles,
                ["M1 t=4.2s barrido_sint"],
            )
            linea = json.loads(reg.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(
            linea["reglas"],
            {
                "storyboard": [
                    "escena 3: cifra '$1.2M' sin fuente",
                    "sonidos[0]: sfx 'gong' no está en el catálogo (caja, sello)",
                ],
                "guion": ["G2: gancho de 19 palabras (máx. 14)"],
            },
        )
        self.assertEqual(linea["pendientes"], ["M1 t=4.2s barrido_sint"])
        self.assertEqual(linea["fallo"], "✗ puertas fallidas: storyboard, guion")

    def test_clean_run_has_no_rules(self):
        with tempfile.TemporaryDirectory() as d:
            reg = Path(d) / "corridas.jsonl"
            P.registrar_corrida(
                reg, 0.0, None, ["--previo"], {"build": (True, "ok")}, []
            )
            linea = json.loads(reg.read_text(encoding="utf-8"))
        self.assertNotIn("reglas", linea)
        self.assertTrue(linea["previo"])


class ResumenTest(unittest.TestCase):
    def test_counts_rule_classes_across_runs(self):
        sys.path.insert(0, str(RUTA.parents[2] / "tools"))
        import resumen_corridas as R

        r = R.resumir(
            [
                {
                    "s": 60,
                    "fallo": "✗ puertas fallidas: storyboard",
                    "reglas": {"storyboard": ["escena 3: cifra '$1.2M' sin fuente"]},
                },
                {
                    "s": 120,
                    "fallo": "✗ puerta 'voz' fallida",
                    "reglas": {"storyboard": ["escena 7: cifra '40%' sin fuente"]},
                },
                {"s": 30, "fallo": None},
            ]
        )
        self.assertEqual((r["corridas"], r["fallidas"], r["min_fallidas"]), (3, 2, 3))
        self.assertEqual(r["puertas"], {"storyboard": 1, "voz": 1})
        self.assertEqual(
            r["reglas"].most_common(1),
            [("storyboard: escena N: cifra '…' sin fuente", 2)],
        )


if __name__ == "__main__":
    unittest.main()
