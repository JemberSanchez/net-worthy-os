import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parent.parent
RUTA = RAIZ / "video-v2" / "motor" / "producir.py"


def _cargar():
    sys.path.insert(0, str(RUTA.parent))
    spec = importlib.util.spec_from_file_location("producir_run_test", RUTA)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestRunUnicode(unittest.TestCase):
    def test_child_printing_non_cp1252_survives_on_any_console(self):
        # medir_ritmo prints "≈" and "✓": on cp1252 it crashed and failed the gate with empty output
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
        with mock.patch.dict(os.environ, env, clear=True):
            r = _cargar()._run([sys.executable, "-c", "print('≈ ✓')"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("≈ ✓", r.stdout)


if __name__ == "__main__":
    unittest.main()
