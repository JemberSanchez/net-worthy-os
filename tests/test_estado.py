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

from omega import config, estado


def _db(path: Path, filas: int) -> None:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER PRIMARY KEY, v TEXT)")
    con.executemany(
        "INSERT INTO t (v) VALUES (?)", [(f"fila {i}",) for i in range(filas)]
    )
    con.commit()
    con.close()


class ExportarImportarTest(unittest.TestCase):
    def test_ida_y_vuelta_sin_perdidas_y_determinista(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d, "a.sqlite"), Path(d, "b.sqlite")
            _db(a, 5)
            sql = estado.exportar(a)
            self.assertEqual(sql, estado.exportar(a))  # mismo contenido = mismo texto
            estado.importar(sql, b)
            self.assertEqual(estado.exportar(b), sql)
            self.assertFalse(Path(d, "b.sqlite.tmp").exists())  # sin restos a medias


class GuardaSubirTest(unittest.TestCase):
    def test_no_sube_una_base_recortada(self):
        ok, motivo = estado.puede_subir("x" * 10, "x" * 100)
        self.assertFalse(ok)
        self.assertIn("estado-bajar", motivo)

    def test_crecer_primera_vez_y_forzar(self):
        self.assertTrue(estado.puede_subir("x" * 100, "x" * 90)[0])
        self.assertTrue(estado.puede_subir("x", None)[0])  # repo vacío: primera subida
        self.assertTrue(estado.puede_subir("x", "x" * 100, forzar=True)[0])


class FlujoGitTest(unittest.TestCase):
    """bajar/subir contra un repo git LOCAL que hace de remoto privado."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.remoto = base / "remoto.git"
        subprocess.run(["git", "init", "-q", "--bare", str(self.remoto)], check=True)
        semilla = base / "semilla"
        subprocess.run(
            ["git", "clone", "-q", str(self.remoto), str(semilla)],
            check=True,
            capture_output=True,
        )
        Path(semilla, "README.md").write_text("estado\n")
        for c in (
            ["add", "."],
            ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init"],
            ["push", "-q"],
        ):
            subprocess.run(["git", *c], cwd=semilla, check=True, capture_output=True)
        self.data = base / "data"
        self.data.mkdir()
        self.p = [
            mock.patch.object(config, "DATA_DIR", self.data),
            mock.patch.object(config, "DB_PATH", self.data / "omega.sqlite"),
            mock.patch.dict(os.environ, {"ESTADO_REPO": str(self.remoto)}),
        ]
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
        con = sqlite3.connect(
            config.DB_PATH
        )  # cerrarla: Windows no deja borrar un archivo abierto
        self.assertEqual(con.execute("SELECT COUNT(*) FROM t").fetchone()[0], 50)
        con.close()
        self.assertIn("ya al día", estado.bajar())
        # con cambios locales sin subir, no la pisa sin --forzar
        _db(config.DB_PATH, 1)
        self.assertIn("no la piso", estado.bajar())
        estado.subir()
        # una base casi vacía no se sube encima de la buena
        config.DB_PATH.unlink()
        _db(config.DB_PATH, 1)
        with self.assertRaises(estado.EstadoError):
            estado.subir()

    def _nube_escribe(self, filas: int) -> None:
        """The cloud queue job: its own clone, its own DB, pushes a new omega.sql."""
        otra = Path(self.tmp.name, "nube")
        with (
            mock.patch.object(config, "DATA_DIR", otra),
            mock.patch.object(config, "DB_PATH", otra / "omega.sqlite"),
        ):
            otra.mkdir(exist_ok=True)
            estado.bajar(forzar=True)
            _db(config.DB_PATH, filas)
            estado.subir()

    def _filas(self) -> int:
        con = sqlite3.connect(config.DB_PATH)
        n = con.execute("SELECT COUNT(*) FROM t").fetchone()[0]
        con.close()
        return n

    def test_la_nube_y_el_pc_no_se_pisan(self):
        _db(config.DB_PATH, 50)
        estado.subir()
        self._nube_escribe(5)  # cron: remote moves, local untouched
        self.assertIn(
            "✓ base restaurada", estado.bajar()
        )  # fast-forward, no --forzar needed
        self.assertEqual(self._filas(), 55)
        _db(config.DB_PATH, 2)  # session work...
        self._nube_escribe(3)  # ...while the cron runs again
        with self.assertRaises(estado.EstadoError):
            estado.subir()  # would drop the cron's rows
        self.assertIn("no la piso", estado.bajar())  # nor drop the session's
        self.assertIn("✓ estado subido", estado.subir(forzar=True))

    def test_guardar_produccion_sin_regenerables(self):
        proy = Path(self.tmp.name) / "mi-short"
        for rel in (
            "storyboard.json",
            "assets/voice.mp3",
            "assets/words.json",
            "assets/t/a.jpg",
            "assets/img/creditos.json",
            "assets/img/a.jpg",
            "assets/music-bed.wav",
            "assets/clips/c.src",
            "assets/clips/creditos.json",
            "assets/v/c-0-300.mp4",
            "assets/_motor/gsap.min.js",
            "renders/x-final.mp4",
            "renders/qa.json",
            "index.html",
            "assets/sfx/caja.src",
            "assets/sfx/caja.wav",
            "assets/sfx/creditos.json",
        ):
            (proy / rel).parent.mkdir(parents=True, exist_ok=True)
            (proy / rel).write_text("x")
        guardados = {p.as_posix() for p in estado.archivos_produccion(proy)}
        self.assertEqual(
            guardados,
            {
                "storyboard.json",
                "assets/voice.mp3",
                "assets/words.json",
                "assets/t/a.jpg",
                "assets/img/creditos.json",
                "assets/clips/creditos.json",
                "renders/qa.json",
                "index.html",
                "assets/sfx/creditos.json",
            },
        )
        self.assertIn("guardada (9 archivos)", estado.guardar_produccion(proy))
        self.assertIn("sin cambios", estado.guardar_produccion(proy))


if __name__ == "__main__":
    unittest.main(verbosity=2)


class SinBaseTest(FlujoGitTest):
    def test_sin_base_no_pisa_una_corrida_de_la_nube(self):
        _db(config.DB_PATH, 50)
        estado.subir()
        self._nube_escribe(5)
        (config.DATA_DIR / ".estado_base").unlink()  # PC that synced before the base file existed
        _db(config.DB_PATH, 1)
        with self.assertRaises(estado.EstadoError):
            estado.subir()


class DerivadasTest(unittest.TestCase):
    def test_signal_no_viaja_pero_su_tabla_si(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d, "a.sqlite"), Path(d, "b.sqlite")
            _db(a, 3)
            con = sqlite3.connect(a)
            con.execute("CREATE TABLE signal (id INTEGER PRIMARY KEY, value TEXT)")
            con.executemany("INSERT INTO signal (value) VALUES (?)", [("x" * 100,)] * 50)
            con.commit()
            con.close()
            sql = estado.exportar(a)
            self.assertNotIn('INSERT INTO "signal"', sql)
            estado.importar(sql, b)
            con = sqlite3.connect(b)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM signal").fetchone()[0], 0)
            self.assertEqual(con.execute("SELECT COUNT(*) FROM t").fetchone()[0], 3)
            con.close()

    def test_volcado_viejo_con_senales_no_bloquea_la_subida(self):
        viejo = "CREATE TABLE t;\n" + '\n'.join(['INSERT INTO "signal" VALUES(1);'] * 1000)
        nuevo = "CREATE TABLE t;\n" + "x" * 10
        previo = "\n".join(x for x in viejo.split("\n") if not estado._derivada(x))
        self.assertTrue(estado.puede_subir(nuevo, previo)[0])
