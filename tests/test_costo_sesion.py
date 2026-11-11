"""tools/costo_sesion.py: one API message is one turn, however many transcript lines repeat it."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import costo_sesion


class TestMedir(unittest.TestCase):
    def test_un_mensaje_repetido_cuenta_una_vez(self):
        def linea(mid, ts, leida):
            uso = {"cache_read_input_tokens": leida, "output_tokens": 10}
            return json.dumps({"timestamp": ts, "message": {"id": mid, "usage": uso}})

        lineas = [
            linea("m1", "2026-11-11T14:00:00.000Z", 100),
            linea(
                "m1", "2026-11-11T14:00:01.000Z", 100
            ),  # second content block, same message
            "not json",
            json.dumps({"timestamp": "2026-11-11T14:10:00.000Z", "message": "texto"}),
            linea("m2", "2026-11-11T14:30:00.000Z", 300),
        ]
        with tempfile.TemporaryDirectory() as d:
            t = Path(d) / "s.jsonl"
            t.write_text("\n".join(lineas), encoding="utf-8")
            c = costo_sesion.medir(t)
        self.assertEqual(
            c,
            {
                "turnos": 2,
                "cache_leida": 400,
                "cache_escrita": 0,
                "salida": 20,
                "minutos": 30,
            },
        )


if __name__ == "__main__":
    unittest.main()
