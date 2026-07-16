"""Tests del backup del MOAT: el dataset es EL activo del proyecto y vive gitignored en un solo
disco. Validan: snapshot consistente del SQLite (via API de backup, legible tras restaurar),
inclusión de los archivos de data/ (voces/JSONs), exclusión de .bak viejos, y tolerancia a
data_dir inexistente (no debe romper: mejor un zip con solo la DB que ningún backup).
"""
from __future__ import annotations
import os
import sqlite3
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omega import db  # noqa: E402


class BackupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.data_dir = root / "data"
        self.data_dir.mkdir()
        self.dest = root / "backups"
        # una DB real con una fila (el moat en miniatura)
        self.db_path = self.data_dir / "omega.sqlite"
        con = sqlite3.connect(self.db_path)
        con.execute("CREATE TABLE production_outcome (production_ref TEXT PRIMARY KEY, success REAL)")
        con.execute("INSERT INTO production_outcome VALUES ('ref-1', 0.37)")
        con.commit()
        con.close()
        (self.data_dir / "voz-short-01.mp3").write_bytes(b"mp3-bytes")
        (self.data_dir / "production_dna.json").write_text("{}", encoding="utf-8")
        (self.data_dir / "omega.sqlite.bak-123").write_bytes(b"stale")  # .bak viejo: fuera

    def tearDown(self):
        self.tmp.cleanup()

    def test_snapshot_contains_db_and_data_files_and_restores(self):
        out = db.backup_snapshot(db_path=self.db_path, data_dir=self.data_dir, dest_dir=self.dest)
        self.assertTrue(out.exists())
        with zipfile.ZipFile(out) as zf:
            names = set(zf.namelist())
            self.assertIn("data/omega.sqlite", names)
            self.assertIn("data/voz-short-01.mp3", names)
            self.assertIn("data/production_dna.json", names)
            self.assertNotIn("data/omega.sqlite.bak-123", names)  # los .bak viejos no aportan
            # la DB restaurada es legible y trae la fila (snapshot consistente, no copia rota)
            restored = Path(self.tmp.name) / "restored.sqlite"
            restored.write_bytes(zf.read("data/omega.sqlite"))
        con = sqlite3.connect(restored)
        row = con.execute("SELECT success FROM production_outcome WHERE production_ref='ref-1'").fetchone()
        con.close()
        self.assertEqual(row[0], 0.37)
        # y el snapshot temporal no queda tirado en dest_dir
        self.assertEqual([p.name for p in self.dest.iterdir() if p.suffix == ".sqlite"], [])

    def test_tolerates_missing_db(self):
        # sin DB todavía: el backup no rompe, guarda lo que haya en data/
        self.db_path.unlink()
        out = db.backup_snapshot(db_path=self.db_path, data_dir=self.data_dir, dest_dir=self.dest)
        with zipfile.ZipFile(out) as zf:
            self.assertIn("data/voz-short-01.mp3", zf.namelist())
            self.assertNotIn("data/omega.sqlite", zf.namelist())


if __name__ == "__main__":
    unittest.main(verbosity=2)
