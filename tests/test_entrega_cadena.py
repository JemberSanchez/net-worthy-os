"""tools/entregar.py and video-v2/motor/cadena.py: background steps with no Claude turn in between."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tools"))
sys.path.insert(0, str(RAIZ / "video-v2" / "motor"))

import cadena  # noqa: E402 -- motor folder on sys.path first
import entregar  # noqa: E402 -- tools folder on sys.path first


class EntregarTest(unittest.TestCase):
    def test_nunca_publica(self):
        for p in entregar.pasos(Path("video-v2/x")):
            self.assertNotIn("--publicar", p)
        self.assertEqual([p[0] for p in entregar.pasos(Path("video-v2/x"))],
                         ["produccion-guardar", "estado-subir", "publicar"])


class CadenaTest(unittest.TestCase):
    def test_avisos_solo_lo_accionable(self):
        salida = "Proyecto: x\nSintetizando…\n✓ voice.mp3\n✗ pausa rota. Reescribe:\n  - frase 3\n⚠ V1 queda"
        self.assertEqual(cadena.avisos(salida), "✗ pausa rota. Reescribe:\n  - frase 3\n⚠ V1 queda")

    def test_sin_ver(self):
        self.assertEqual(cadena.sin_ver({"a": {"visto": True}, "b": {}, "c": {"visto": "si"}}), ["b", "c"])

    def test_copia_hojas_de_la_cola_sin_pisar(self):
        with tempfile.TemporaryDirectory() as d:
            medios = Path(d, "cola", "medios")
            (medios / "oro").mkdir(parents=True)
            (medios / "oro" / "c1.hoja.jpg").write_bytes(b"nube")
            (medios / "oro" / "c1.hoja.txt").write_text("GOLD\n")
            Path(d, "cola", "actual.json").write_text(json.dumps(
                {"temas": [{"ref": "oro", "medios": [{"pexels": 5, "hoja": "c1.hoja.jpg"}]}]}))
            proy = Path(d, "p")
            (proy / "assets" / "clips").mkdir(parents=True)
            (proy / "assets" / "clips" / "viejo.hoja.jpg").write_bytes(b"propia")
            decl = {"gancho": {"pexels": 5}, "viejo": {"pexels": 5}}
            self.assertEqual(cadena.copiar_hojas(proy, decl, medios), ["gancho"])
            self.assertEqual((proy / "assets" / "clips" / "gancho.hoja.txt").read_text(), "GOLD\n")
            self.assertEqual((proy / "assets" / "clips" / "viejo.hoja.jpg").read_bytes(), b"propia")


if __name__ == "__main__":
    unittest.main()
