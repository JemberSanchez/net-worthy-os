"""Tests del estado persistente (omega/estado.py): la base viaja a un repo privado como volcado SQL.

Las dos guardas son lo importante: no pisar una base local sin --forzar y no subir una base vacía
encima de meses de datos (la firma de una sesión nueva en la nube que olvidó `estado-bajar`).
"""
from __future__ import annotations
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega import config, estado  # noqa: E402


def _db(path: Path, filas: int) -> None:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, v TEXT)")
    con.executemany("INSERT INTO t (v) VALUES (?)", [(f"fila {i}",) for i in range(filas)])
    con.commit()
    con.close()


class ExportarImportarTest(unittest.TestCase):
    def test_ida_y_vuelta_sin_perdidas_y_determinista(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d, "a.sqlite"), Path(d, "b.sqlite")
            _db(a, 5)
            sql = estado.exportar(a)
            self.assertEqual(sql, estado.exportar(a))            # mismo contenido = mismo texto
            estado.importar(sql, b)
            self.assertEqual(estado.exportar(b), sql)
            self.assertFalse(Path(d, "b.sqlite.tmp").exists())   # sin restos a medias


class GuardaSubirTest(unittest.TestCase):
    def test_no_sube_una_base_recortada(self):
        ok, motivo = estado.puede_subir("x" * 10, "x" * 100)
        self.assertFalse(ok)
        self.assertIn("estado-bajar", motivo)

    def test_crecer_primera_vez_y_forzar(self):
        self.assertTrue(estado.puede_subir("x" * 100, "x" * 90)[0])
        self.assertTrue(estado.puede_subir("x", None)[0])        # repo vacío: primera subida
        self.assertTrue(estado.puede_subir("x", "x" * 100, forzar=True)[0])


class FlujoGitTest(unittest.TestCase):
    """bajar/subir contra un repo git LOCAL que hace de remoto privado."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.remoto = base / "remoto.git"
        subprocess.run(["git", "init", "-q", "--bare", str(self.remoto)], check=True)
        semilla = base / "semilla"
        subprocess.run(["git", "clone", "-q", str(self.remoto), str(semilla)], check=True, capture_output=True)
        Path(semilla, "README.md").write_text("estado\n")
        for c in (["add", "."], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init"], ["push", "-q"]):
            subprocess.run(["git", *c], cwd=semilla, check=True, capture_output=True)
        self.data = base / "data"
        self.data.mkdir()
        self.p = [mock.patch.object(config, "DATA_DIR", self.data),
                  mock.patch.object(config, "DB_PATH", self.data / "omega.sqlite"),
                  mock.patch.dict(os.environ, {"ESTADO_REPO": str(self.remoto)})]
        for p in self.p:
            p.start()

    def tearDown(self):
        for p in self.p:
            p.stop()
        self.tmp.cleanup()

    def test_subir_bajar_y_guardas(self):
        self.assertIn("aún no tiene volcado", estado.bajar())
        _db(config.DB_PATH, 50)
        self.assertIn("✓ estado subido", estado.subir())
        self.assertIn("sin cambios", estado.subir())
        # sesión nueva: sin base local -> bajar la reconstruye
        config.DB_PATH.unlink()
        self.assertIn("✓ base restaurada", estado.bajar())
        self.assertEqual(sqlite3.connect(config.DB_PATH).execute("SELECT COUNT(*) FROM t").fetchone()[0], 50)
        # con base local, no la pisa sin --forzar
        self.assertIn("no la piso", estado.bajar())
        # una base casi vacía no se sube encima de la buena
        config.DB_PATH.unlink()
        _db(config.DB_PATH, 1)
        with self.assertRaises(estado.EstadoError):
            estado.subir()


    def test_guardar_produccion_sin_regenerables(self):
        proy = Path(self.tmp.name) / "mi-short"
        for rel in ("storyboard.json", "assets/voice.mp3", "assets/words.json", "assets/t/a.jpg",
                    "assets/img/creditos.json", "assets/img/a.jpg", "assets/music-bed.wav",
                    "assets/_motor/gsap.min.js", "renders/x-final.mp4", "renders/qa.json", "index.html"):
            (proy / rel).parent.mkdir(parents=True, exist_ok=True)
            (proy / rel).write_text("x")
        guardados = {p.as_posix() for p in estado.archivos_produccion(proy)}
        self.assertEqual(guardados, {"storyboard.json", "assets/voice.mp3", "assets/words.json", "assets/t/a.jpg",
                                     "assets/img/creditos.json", "renders/qa.json", "index.html"})
        self.assertIn("guardada (7 archivos)", estado.guardar_produccion(proy))
        self.assertIn("sin cambios", estado.guardar_produccion(proy))


if __name__ == "__main__":
    unittest.main(verbosity=2)
