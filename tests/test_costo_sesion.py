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


class TestPasos(unittest.TestCase):
    def test_modelo_y_herramienta_por_paso_sin_contar_esperas(self):
        def l(ts, tipo, contenido, mid=None):
            return json.dumps({"timestamp": f"2026-11-20T10:{ts}.000Z", "type": tipo,
                               "message": {"id": mid, "content": contenido}})

        uso = {"type": "tool_use", "id": "t1", "name": "Bash",
               "input": {"command": "python video-v2/motor/voz.py video-v2/x"}}
        lineas = [
            l("00:00", "user", "haz el video"),
            l("01:00", "assistant", [uso], "m1"),  # 1 min writing the turn
            l("04:00", "user", [{"type": "tool_result", "tool_use_id": "t1"}]),  # 3 min tool
            l("30:00", "user", "<task-notification>"),  # 26 min idle: not charged
            l("30:30", "assistant", [{"type": "text", "text": "listo"}], "m2"),
        ]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.jsonl"
            p.write_text("\n".join(lineas), encoding="utf-8")
            self.assertEqual(costo_sesion.pasos(p), {"voz": {"modelo": 1.5, "herramienta": 3.0}})

    def test_clasifica_por_comando(self):
        def b(cmd):
            return {"name": "Bash", "input": {"command": cmd}}

        self.assertEqual(costo_sesion.paso_de(b("python -m omega.cli estado-subir")), "entregar")
        self.assertEqual(costo_sesion.paso_de(b("python tools/broll.py lote video-v2/x")), "medios")
        self.assertEqual(costo_sesion.paso_de(b("python video-v2/motor/cadena.py video-v2/x")), "producir")
        self.assertEqual(costo_sesion.paso_de(b("grep -n foo bar.py")), "sondeo")
