"""Fallos de entorno vistos al producir fed-vs-card (30-oct): cada test los reproduce."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "video-v2" / "motor"))


def _env_cp1252() -> dict:
    """Entorno sin forzar UTF-8: en Windows, la salida redirigida usa cp1252 (no tiene ✓)."""
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("PYTHONIOENCODING", "PYTHONUTF8")
    }
    env["PYTHONIOENCODING"] = "cp1252"
    return env


class SalidaRedirigida(unittest.TestCase):
    def test_producir_no_revienta_al_imprimir_puertas(self):
        import tempfile

        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "storyboard.json").write_text(
                '{"ref": "x", "guion": []}', encoding="utf-8"
            )
            r = subprocess.run(
                [
                    sys.executable,
                    str(RAIZ / "video-v2/motor/producir.py"),
                    d,
                    "--sin-subir",
                ],
                check=False,
                capture_output=True,
                env=_env_cp1252(),
                cwd=RAIZ,
            )
        self.assertNotIn(b"UnicodeEncodeError", r.stderr)
        self.assertIn("✗".encode(), r.stdout)

    def test_cli_imprime_utf8(self):
        r = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; from omega import cli; cli.main(['cli']); print('✓')",
            ],
            check=False,
            capture_output=True,
            env=_env_cp1252(),
            cwd=RAIZ,
        )
        self.assertNotIn(b"UnicodeEncodeError", r.stderr)


class CaptionInstagram(unittest.TestCase):
    def test_descripcion_larga_cabe_y_conserva_fuentes_y_creditos(self):
        from omega.publish_meta import caption_ig

        ficha = "- Photo {i}.jpg · Author {i} · CC BY 2.0 (https://creativecommons.org/licenses/by/2.0) · https://commons.wikimedia.org/wiki/File:Photo_{i}.jpg"
        desc = (
            "Intro text. Not financial advice.\n\n#shorts #money\n\nSources:\n- https://example.com/a\n\n"
            "Images:\n" + "\n".join(ficha.format(i=i) for i in range(12)) + "\n\n"
            "Footage:\n"
            + "\n".join(
                ficha.format(i=i).replace("CC BY 2.0", "Pexels License")
                for i in range(12, 24)
            )
        )
        self.assertGreater(len(desc), 2200)
        cap = caption_ig(desc)
        self.assertLessEqual(len(cap), 2200)
        for imprescindible in (
            "Not financial advice",
            "https://example.com/a",
            "Author 3 (CC BY 2.0)",
            "Author 20 (Pexels License)",
        ):
            self.assertIn(imprescindible, cap)

    def test_descripcion_corta_no_cambia(self):
        from omega.publish_meta import caption_ig

        self.assertEqual(caption_ig("short"), "short")


class ClavePexels(unittest.TestCase):
    @unittest.skipUnless(
        "PEXELS_API_KEY="
        in (
            (RAIZ / ".env").read_text(encoding="utf-8")
            if (RAIZ / ".env").exists()
            else ""
        ),
        "sin PEXELS_API_KEY en .env",
    )
    def test_broll_lee_env(self):
        env = {k: v for k, v in os.environ.items() if k != "PEXELS_API_KEY"}
        r = subprocess.run(
            [
                sys.executable,
                "-c",
                "import os, sys; sys.path.insert(0, 'tools'); import broll; print('PEXELS_API_KEY' in os.environ)",
            ],
            check=False,
            capture_output=True,
            text=True,
            env=env,
            cwd=RAIZ,
        )
        self.assertEqual(r.stdout.strip(), "True", r.stderr)


class HfCoreWindows(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "rutas MSYS solo en Windows")
    def test_ruta_msys_de_setup_nube_se_traduce(self):
        import tempfile

        import producir

        with tempfile.TemporaryDirectory() as d:
            p = Path(d).resolve()
            msys = "/" + p.drive[0].lower() + p.as_posix()[2:]
            salida = mock.Mock(stdout=f"export HF_CORE={msys}\n")
            with (
                mock.patch.object(producir, "_run", return_value=salida),
                mock.patch.dict(os.environ, {}, clear=False),
            ):
                os.environ.pop("HF_CORE", None)
                env = producir._entorno()
        self.assertEqual(Path(env.get("HF_CORE", "")).resolve(), p)


if __name__ == "__main__":
    unittest.main()
