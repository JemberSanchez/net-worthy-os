"""Topic queue (omega/cola.py): what the cloud leaves ready for /producir."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega import cola  # noqa: E402 -- needs the repo root on sys.path first


class TemaTest(unittest.TestCase):
    def test_tema_y_ref(self):
        self.assertEqual(cola.tema_de("Demanda creciente en torno a 'long-term investors'"), "long-term investors")
        self.assertEqual(cola.slug("Fed's Collins: 70k?"), "fed-s-collins-70k")


class FuentesTest(unittest.TestCase):
    def test_titulares_recientes_con_todas_las_palabras_y_sus_cifras(self):
        con = sqlite3.connect(":memory:")
        con.execute("CREATE TABLE observed_content (source, title, summary, url, published_at)")
        ahora = int(time.time())
        con.executemany(
            "INSERT INTO observed_content VALUES (?,?,?,?,?)",
            [
                ("g", "Long-term investors pulled $4.2 billion, up 12% since 2024", "", "u1", ahora - 60),
                ("g", "Investors flee", "", "u2", ahora - 30),  # missing a topic word
                ("g", "Long-term investors were right", "", "u3", ahora - 30 * 86400),  # too old
            ],
        )
        f = cola.fuentes(con, "long-term investors")
        self.assertEqual([x["url"] for x in f], ["u1"])
        self.assertEqual(f[0]["cifras"], ["$4.2 billion", "12%", "2024"])


class HojasPreviasTest(unittest.TestCase):
    def test_empareja_por_origen_no_por_nombre(self):
        with tempfile.TemporaryDirectory() as d:
            medios = Path(d, "cola", "medios")
            (medios / "bitcoin").mkdir(parents=True)
            (medios / "bitcoin" / "c1.hoja.jpg").write_bytes(b"jpg")
            Path(d, "cola", "actual.json").write_text(json.dumps({"temas": [
                {"ref": "bitcoin", "medios": [{"pexels": 123, "hoja": "c1.hoja.jpg"},
                                              {"pexels": 9, "hoja": "c2.hoja.jpg"}]}]}))
            decl = {"gancho": {"pexels": 123, "desde": 0}, "otro": {"pexels": 9}, "nuevo": {"pexels": 77}}
            self.assertEqual(cola.hojas_previas(decl, medios), {"gancho": medios / "bitcoin" / "c1.hoja.jpg"})


class MostrarTest(unittest.TestCase):
    def test_solo_fallos_del_pipeline_y_un_bloque_por_tema(self):
        c = {"preparada": "2026-11-21T09:00", "segundos": 300,
             "pasos": [{"paso": "ingest", "ok": True, "salida": ["ok"]},
                       {"paso": "meta-sync", "ok": False, "salida": ["✗ token caducado"]}],
             "temas": [{"tema": "gold", "ref": "gold", "score": 1.0, "por_que": ["momentum"],
                        "fuentes": [{"fecha": "2026-11-20", "titulo": "Gold at $4,000", "url": "u", "cifras": ["$4,000"]}],
                        "medios": [{"pexels": 1, "titulo": "pexels:1", "texto_ocr": [], "hoja": "c1.hoja.jpg"}]}]}
        s = cola.mostrar(c, Path("m"))
        self.assertIn("✗ meta-sync: ✗ token caducado", s)
        self.assertNotIn("ingest", s)
        self.assertIn("cifras: $4,000", s)
        self.assertIn("pexels 1", s)


if __name__ == "__main__":
    unittest.main()
