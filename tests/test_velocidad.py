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

    def test_contraste_aprobado_se_reutiliza_solo_con_la_misma_pagina(self):
        llamadas = []

        def medir(ok):
            return lambda p, e, ya: (llamadas.append(1), (ok, "medido", []))[1]

        env = {"HF_VERSION": "1.0"}
        self.assertFalse(producir.auditar_contraste(self.proy, env, medir(False))[0])
        producir.auditar_contraste(
            self.proy, env, medir(True)
        )  # a failure is never cached
        self.assertEqual(len(llamadas), 2)
        self.assertIn(
            "reutilizado", producir.auditar_contraste(self.proy, env, medir(False))[1]
        )
        self.assertEqual(len(llamadas), 2)
        for cambio in (
            lambda: (self.proy / "index.html").write_text(
                "<html>2</html>", encoding="utf-8"
            ),
            lambda: env.update(HF_VERSION="1.1"),
        ):
            cambio()
            producir.auditar_contraste(self.proy, env, medir(True))
        self.assertEqual(len(llamadas), 4)

    def test_contraste_salta_solo_los_fotogramas_ya_aprobados_byte_a_byte(self):
        (self.proy / "index.html").write_text(
            '<section id="s0" class="clip scene" data-start="0.000" data-duration="2.000">'
            '<section id="s1" class="clip scene" data-start="2.000" data-duration="2.000">',
            encoding="utf-8",
        )
        cuadros = self.proy / "renders" / "previo"
        cuadros.mkdir()
        for i, t in enumerate((1.2, 3.2)):
            (cuadros / f"frame-0{i}-at-{t}s.png").write_bytes(b"px")
        vistos = []

        def medir(ok, bien):
            return lambda p, e, ya: (vistos.append(set(ya)), (ok, "m", bien))[1]

        env = {"HF_VERSION": "1.0"}
        # s0 fails, s1 passes: the next audit skips only s1
        producir.auditar_contraste(self.proy, env, medir(False, [3.2]), cuadros)
        producir.auditar_contraste(self.proy, env, medir(True, [1.2]), cuadros)
        with (self.proy / "index.html").open("a", encoding="utf-8") as f:
            f.write("<i>s1 edited</i>")  # a new page, so the whole-page reuse misses
        (cuadros / "frame-01-at-3.2s.png").write_bytes(b"otro")
        producir.auditar_contraste(self.proy, env, medir(True, []), cuadros)
        env["HF_VERSION"] = "1.1"  # other rules: nothing reused
        producir.auditar_contraste(self.proy, env, medir(True, []), cuadros)
        self.assertEqual(vistos, [set(), {3.2}, {1.2}, set()])

    def test_contraste_con_la_hoja_en_paralelo_guarda_lo_aprobado(self):
        from concurrent.futures import Future

        (self.proy / "index.html").write_text(
            '<section id="s0" class="clip scene" data-start="0.000" data-duration="2.000">',
            encoding="utf-8",
        )
        cuadros = self.proy / "renders" / "previo"
        cuadros.mkdir()
        (cuadros / "frame-00-at-1.2s.png").write_bytes(b"px")
        hoja, vistos = Future(), []
        hoja.set_result((True, "hoja"))
        env = {"HF_VERSION": "1.0"}

        def medir(ya):
            vistos.append(set(ya))
            return False, "m", [1.2]  # fails elsewhere: no whole-page reuse

        producir.auditar_contraste(
            self.proy, env, lambda p, e, ya: medir(ya), cuadros, hoja
        )
        self.assertTrue(producir.aprobados_contraste(self.proy, env)[2])
        producir.auditar_contraste(self.proy, env, lambda p, e, ya: medir(ya), cuadros)
        self.assertEqual(vistos, [set(), {1.2}])

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
                                {
                                    "severidad": "media",
                                    "criterio": "M1",
                                    "detalle": "x",
                                    "t": 1.0,
                                    "t_fin": None,
                                    "escena": 0,
                                    "parche": None,
                                }
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
        # the critic never reads title, description, tags or the DNA: editing them after it must not re-run it
        self.sb["publicacion"] = {"titulo": "New title", "tags": ["x"]}
        self.sb["adn"] = {"hook": "y"}
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
            t = (
                time.time() + 1
            )  # Windows mtime ticks ~15 ms: same-tick writes look older than t0
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
