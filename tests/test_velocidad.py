"""Phase 1 speed (docs/VELOCIDAD-PLAN.md): --auto retries from the failed stage, not the whole production.
A social-only fix must reuse the render and the critic; any change to the page, an asset or the video's
storyboard must not."""

from __future__ import annotations

import importlib
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "video-v2" / "motor"), str(RAIZ / "tools")]
producir = importlib.import_module("producir")
A = importlib.import_module("autoarreglo")


class CacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.proy = self.tmp / "p"
        (self.proy / "assets" / "clips").mkdir(parents=True)
        (self.proy / "renders" / "critica").mkdir(parents=True)
        (self.proy / "index.html").write_text("<html>1</html>", encoding="utf-8")
        (self.proy / "assets" / "voice.mp3").write_bytes(b"voz")
        (self.proy / "assets" / "clips" / "a.src").write_bytes(b"x" * 10)
        self.sb = {"ref": "p", "guion": [{"texto": "hi"}], "social": {"caption": "a"}}
        (self.proy / "storyboard.json").write_text(
            json.dumps(self.sb), encoding="utf-8"
        )
        self.final = self.proy / "renders" / "p-final.mp4"
        self.final.write_bytes(b"mp4")
        self.cache = self.proy / "renders" / "render.json"
        self.cache.write_text(
            json.dumps(
                {
                    "clave": producir.clave_render(self.proy),
                    "final_sha": producir._sha(self.final),
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def reutiliza(self):
        return producir.render_reutilizable(
            self.cache, producir.clave_render(self.proy), self.final
        )

    def test_mismo_html_y_assets_reutiliza_el_render(self):
        self.assertTrue(self.reutiliza())

    def test_cambio_en_html_asset_o_final_rehace_el_render(self):
        for cambio in (
            lambda: (self.proy / "index.html").write_text(
                "<html>2</html>", encoding="utf-8"
            ),
            lambda: (self.proy / "assets" / "voice.mp3").write_bytes(
                b"voy"
            ),  # same size, other content
            lambda: (self.proy / "assets" / "clips" / "a.src").write_bytes(b"x" * 11),
            lambda: self.final.write_bytes(b"otro"),
        ):
            self.setUp()
            cambio()
            self.assertFalse(self.reutiliza())

    def test_critico_reutilizado_solo_si_cambia_social(self):
        (self.proy / "renders" / "critica" / "informe.json").write_text(
            json.dumps(
                {
                    "rondas": [
                        {
                            "fallos": [
                                {"severidad": "media", "criterio": "M1", "detalle": "x", "t": 1.0, "t_fin": None, "escena": 0, "parche": None}
                            ]
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (self.proy / "renders" / "critica" / "cache.json").write_text(
            json.dumps({"clave": producir.clave_critico(self.proy, self.final)}),
            encoding="utf-8",
        )
        self.sb["social"]["caption"] = "b"
        (self.proy / "storyboard.json").write_text(
            json.dumps(self.sb), encoding="utf-8"
        )
        t = time.time()
        self.assertEqual(len(producir.critico_cacheado(self.proy, self.final)), 1)
        self.assertGreaterEqual(
            (self.proy / "renders" / "critica" / "informe.json").stat().st_mtime, t - 1
        )
        self.sb["guion"][0]["texto"] = "hello"
        (self.proy / "storyboard.json").write_text(
            json.dumps(self.sb), encoding="utf-8"
        )
        self.assertIsNone(producir.critico_cacheado(self.proy, self.final))


class AutoConCriticoParaleloTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.orig = producir.producir, A.arreglar

    def tearDown(self):
        producir.producir, A.arreglar = self.orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_informe_del_critico_cuenta_aunque_falle_una_puerta(self):
        inf = self.tmp / "renders" / "critica" / "informe.json"
        inf.parent.mkdir(parents=True)
        llamadas, recibido = [], []

        def falso(proy):
            llamadas.append(proy)
            producir.DETALLES.clear()
            inf.write_text('{"rondas": [{"fallos": []}]}', encoding="utf-8")
            t = time.time() + 1  # Windows mtime ticks ~15 ms: same-tick writes look older than t0
            os.utime(inf, (t, t))
            if len(llamadas) == 1:
                producir.DETALLES["social"] = (
                    False,
                    "social con defectos:\n  - diapositiva 6: x",
                )
                raise SystemExit("✗ puertas fallidas: social")
            return {"ok": True}

        def arreglar(proy, fallidas, informe, bloquean):
            recibido.append(informe)
            return (["fondo"], [], False) if fallidas else ([], [], False)

        producir.producir, A.arreglar = falso, arreglar
        with redirect_stdout(io.StringIO()):
            self.assertEqual(producir.producir_auto(self.tmp), {"ok": True})
        self.assertIsNotNone(recibido[0])


if __name__ == "__main__":
    unittest.main()
