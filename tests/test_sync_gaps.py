"""Gaps found in the measurement flow: DNA never recorded, publish date lost, wrong platform's id."""

import json
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from omega import analytics_yt as ay
from omega import cli, config
from omega.creative import decisions, patterns, production_dna

RAIZ = Path(__file__).resolve().parent.parent


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        for nombre, valor in (
            ("ROOT", self.tmp),
            ("DATA_DIR", self.tmp),
            ("DB_PATH", self.tmp / "o.sqlite"),
        ):
            p = mock.patch.object(config, nombre, valor)
            p.start()
            self.addCleanup(p.stop)
        self.con = sqlite3.connect(self.tmp / "o.sqlite")
        self.con.row_factory = sqlite3.Row
        self.addCleanup(self.con.close)
        for mod in (patterns, decisions, production_dna):
            mod.init(self.con)

    def adn(self, ref, length_s=40):
        d = self.tmp / "video-v2" / ref
        d.mkdir(parents=True)
        (d / "adn.json").write_text(
            json.dumps(
                {
                    "production_ref": ref,
                    "hook_type": "contrast",
                    "renderer_version": "v2-hyperframes",
                    "length_s": length_s,
                    "blocks": [{"block": "h1", "technique": "v2-storyboard"}],
                }
            ),
            encoding="utf-8",
        )


class AdnAutomatico(Base):
    """housing-turn: adn.json on disk, no DNA row. Without length_s the Meta retention is lost."""

    def test_repuntuar_registra_el_adn_que_falta_y_mide_la_retencion_de_meta(self):
        self.adn("r", 40)
        production_dna.record_social(
            self.con, "r", "facebook", {"views": 100, "avg_watch_s": 10.0}
        )
        score, partes = cli._repuntuar(self.con, "r")
        self.assertEqual(production_dna.fetch_dna(self.con, "r")["length_s"], 40)
        self.assertFalse(partes["parcial"])
        self.assertEqual(partes["retencion"], 0.25)
        self.assertGreater(score, 0)

    def test_no_pisa_un_adn_ya_registrado(self):
        self.adn("r", 40)
        production_dna.record_dna(self.con, production_ref="r", blocks=[], length_s=99)
        cli._asegurar_adn(self.con, "r")
        self.assertEqual(production_dna.fetch_dna(self.con, "r")["length_s"], 99)

    def test_sin_adn_json_no_inventa_nada(self):
        cli._asegurar_adn(self.con, "r")
        self.assertIsNone(production_dna.fetch_dna(self.con, "r"))

    def test_rescore_tambien_lo_registra(self):
        self.adn("r", 40)
        production_dna.record_social(
            self.con, "r", "facebook", {"views": 100, "avg_watch_s": 10.0}
        )
        self.con.commit()
        with mock.patch("sys.argv", ["omega", "rescore"]), mock.patch("builtins.print"):
            cli.cmd_rescore()
        fila = self.con.execute(
            "SELECT score_parts FROM production_outcome WHERE production_ref='r'"
        ).fetchone()
        self.assertEqual(json.loads(fila[0])["retencion"], 0.25)


class FechaDePublicacion(Base):
    """fed-vs-card: `programar --ahora` leaves publish_at NULL although YouTube knows the date."""

    def _yt(self, respuestas):
        yt, yta = mock.MagicMock(), mock.MagicMock()
        yt.videos.return_value.list.return_value.execute.return_value = {
            "items": [
                {
                    "status": {"privacyStatus": "public"},
                    "contentDetails": {"duration": "PT37S"},
                    "snippet": {"publishedAt": "2026-10-30T14:12:09Z"},
                }
            ]
        }
        yta.reports.return_value.query.return_value.execute.side_effect = respuestas
        return yt, yta

    def test_consultar_devuelve_la_fecha_real_aunque_no_haya_datos(self):
        yt, yta = self._yt([{"columnHeaders": [], "rows": []}])
        datos = ay.consultar("v", yt, yta)
        self.assertEqual(datos["estado"], "sin_datos")
        self.assertEqual(datos["published_at"], "2026-10-30T14:12:09Z")

    def _sync(self, *flags):
        production_dna.record_video(self.con, "r", "v")
        self.con.commit()
        datos = {"estado": "sin_datos", "published_at": "2026-10-30T14:12:09Z"}
        with (
            mock.patch("sys.argv", ["omega", "analytics-sync", "r", *flags]),
            mock.patch.object(ay, "_clientes", return_value=(None, None)),
            mock.patch.object(ay, "consultar", return_value=datos),
            mock.patch.object(cli, "_comentar_pendiente"),
            mock.patch("builtins.print"),
        ):
            cli.cmd_analytics_sync()
        return self.con.execute(
            "SELECT publish_at FROM production_video WHERE production_ref='r'"
        ).fetchone()[0]

    def test_analytics_sync_guarda_la_fecha(self):
        self.assertEqual(self._sync(), "2026-10-30T14:12:09Z")

    def test_dry_run_no_escribe(self):
        self.assertIsNone(self._sync("--dry-run"))


class VideoDesdeArchivos(Base):
    def test_no_toma_el_id_de_facebook_como_si_fuera_de_youtube(self):
        (self.tmp / "publish_log.jsonl").write_text(
            json.dumps(
                {
                    "production_ref": "r",
                    "video_id": "yt123",
                    "privacy_status": "private",
                }
            )
            + "\n"
            + json.dumps(
                {"production_ref": "r", "platform": "facebook", "video_id": "1048987"}
            )
            + "\n",
            encoding="utf-8",
        )
        self.assertEqual(ay.video_desde_archivos("r"), "yt123")

    def test_solo_rastro_de_facebook_no_da_video_de_youtube(self):
        (self.tmp / "publish_log.jsonl").write_text(
            json.dumps(
                {"production_ref": "r", "platform": "facebook", "video_id": "1048987"}
            )
            + "\n",
            encoding="utf-8",
        )
        self.assertIsNone(ay.video_desde_archivos("r"))


@unittest.skipUnless(shutil.which("node"), "node not installed")
class LintMotorV2(unittest.TestCase):
    def test_caza_una_redeclaracion_en_motor_js(self):
        with tempfile.TemporaryDirectory() as t:
            raiz = Path(t)
            (raiz / "docs/guiones").mkdir(parents=True)
            (raiz / "video-v2/motor").mkdir(parents=True)
            for html in ("short-renderer.html", "tests-motor.html"):
                (raiz / "docs/guiones" / html).write_text("<p></p>", encoding="utf-8")
            (raiz / "video-v2/motor/motor.js").write_text(
                "var a = 1;\nvar a = 2;\n", encoding="utf-8"
            )
            r = subprocess.run(
                ["node", str(RAIZ / "tools/lint_motor.mjs")],
                cwd=raiz,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("video-v2/motor/motor.js:2", r.stderr)
        self.assertIn("no-redeclare", r.stderr)


if __name__ == "__main__":
    unittest.main()
