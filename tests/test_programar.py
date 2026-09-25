"""Tests de la aprobación de un Short (tarea 8b): borrador privado -> programado a la hora pico.

`videos.update` de YouTube REEMPLAZA el bloque status entero: si no se lee antes, un update pierde
selfDeclaredMadeForKids y compañía. Y la hora pico va en hora de Nueva York con horario de verano.
"""
from __future__ import annotations
import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega import publish  # noqa: E402


class ProximoSlotTest(unittest.TestCase):
    def test_horario_de_verano_y_de_invierno(self):
        # 25-sep (EDT, UTC-4): 12:00 NY = 16:00 UTC · 15-ene (EST, UTC-5): 12:00 NY = 17:00 UTC
        self.assertEqual(publish.proximo_slot(datetime(2026, 9, 25, 10, 0, tzinfo=timezone.utc)),
                         datetime(2026, 9, 25, 16, 0, tzinfo=timezone.utc))
        self.assertEqual(publish.proximo_slot(datetime(2026, 1, 15, 10, 0, tzinfo=timezone.utc)),
                         datetime(2026, 1, 15, 17, 0, tzinfo=timezone.utc))

    def test_si_ya_paso_o_esta_muy_cerca_salta_al_dia_siguiente(self):
        self.assertEqual(publish.proximo_slot(datetime(2026, 9, 25, 15, 50, tzinfo=timezone.utc)),
                         datetime(2026, 9, 26, 16, 0, tzinfo=timezone.utc))       # 10 min antes: margen 20
        self.assertEqual(publish.proximo_slot(datetime(2026, 9, 25, 20, 0, tzinfo=timezone.utc), "18:30"),
                         datetime(2026, 9, 25, 22, 30, tzinfo=timezone.utc))

    def test_cambio_de_hora_de_noviembre(self):
        # 1-nov-2026 acaba el horario de verano en EE. UU.: el 31-oct es UTC-4, el 1-nov ya UTC-5
        self.assertEqual(publish.proximo_slot(datetime(2026, 10, 31, 18, 0, tzinfo=timezone.utc)),
                         datetime(2026, 11, 1, 17, 0, tzinfo=timezone.utc))

    def test_escalonar_dias_cruzando_el_cambio_de_hora(self):
        # 30-oct 12:00 NY es UTC-4 (16:00Z); +2 días = 1-nov, ya UTC-5 -> 17:00Z (no 16:00Z)
        ahora = datetime(2026, 10, 30, 10, 0, tzinfo=timezone.utc)
        self.assertEqual(publish.proximo_slot(ahora, dias=0), datetime(2026, 10, 30, 16, 0, tzinfo=timezone.utc))
        self.assertEqual(publish.proximo_slot(ahora, dias=2), datetime(2026, 11, 1, 17, 0, tzinfo=timezone.utc))


class _Llamada:
    def __init__(self, resultado): self.resultado = resultado
    def execute(self): return self.resultado


class _YouTubeFalso:
    def __init__(self, status):
        self.status, self.update_body = status, None
    def videos(self): return self
    def list(self, part, id): return _Llamada({"items": [{"id": id, "status": dict(self.status)}]} if self.status else {"items": []})
    def update(self, part, body):
        self.update_body = body
        return _Llamada(body)


class ActualizarStatusTest(unittest.TestCase):
    def test_programar_conserva_el_resto_del_status(self):
        yt = _YouTubeFalso({"privacyStatus": "private", "selfDeclaredMadeForKids": False, "license": "youtube",
                            "uploadStatus": "processed"})
        publish.programar("abc", datetime(2026, 9, 26, 16, 0, tzinfo=timezone.utc), youtube=yt)
        st = yt.update_body["status"]
        self.assertEqual(st["privacyStatus"], "private")
        self.assertEqual(st["publishAt"], "2026-09-26T16:00:00Z")
        self.assertIs(st["selfDeclaredMadeForKids"], False)          # no se pierde
        self.assertNotIn("uploadStatus", st)                         # solo lectura: no se reenvía

    def test_hacer_publico_quita_la_programacion(self):
        yt = _YouTubeFalso({"privacyStatus": "private", "publishAt": "2026-09-26T16:00:00Z", "selfDeclaredMadeForKids": False})
        publish.hacer_publico("abc", youtube=yt)
        self.assertEqual(yt.update_body["status"]["privacyStatus"], "public")
        self.assertNotIn("publishAt", yt.update_body["status"])

    def test_video_inexistente_da_error_claro(self):
        with self.assertRaisesRegex(publish.PublishError, "no encuentra"):
            publish.hacer_publico("nope", youtube=_YouTubeFalso({}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
