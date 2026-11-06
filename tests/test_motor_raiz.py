"""Faults that used to cost a render, caught at the cheapest step: clip cache by source, years in the audio gate,
checks on preview frames, voice takes before anything is built, clips looked at before they are used."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / "video-v2" / "motor"), str(RAIZ / "tools")]

import broll
import construir as c
import critico
import medir_guion_audio as mga
import medir_texto
import producir
import puertas
import puertas_final as pf
import social


class CacheClipsTest(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.clips = Path(d.name) / "assets" / "clips"
        self.v = Path(d.name) / "assets" / "v"
        self.clips.mkdir(parents=True)
        self.v.mkdir()

    def _cache(self, k: str, origen: str, tratado: str) -> None:
        (self.clips / f"{k}.src").write_bytes(b"x")
        (self.clips / f"{k}.src.origen").write_text(origen, encoding="utf-8")
        (self.clips / f"{k}.hoja.jpg").write_bytes(b"x")
        (self.v / tratado).write_bytes(b"x")

    def _fichas(self, *archivos: str) -> None:
        (self.clips / "creditos.json").write_text(
            json.dumps([{"archivo": a} for a in archivos]), encoding="utf-8"
        )

    def test_new_source_with_same_key_drops_every_cached_derivative(self):
        self._cache("mazo", "111", "mazo-3-420-f.mp4")
        self._cache("mazo-roto", "222", "mazo-roto-0-300-f.mp4")
        self._fichas("mazo.src", "mazo-roto.src")
        (self.clips / "detalle.json").write_text(
            json.dumps({"mazo@3": 9.0, "mazo-roto@0": 5.0}), encoding="utf-8"
        )

        cambiados = broll.purgar_cambiados(
            {"mazo": {"pexels": 999}, "mazo-roto": {"pexels": 222}}, self.clips
        )

        self.assertEqual(cambiados, ["mazo"])
        self.assertFalse((self.clips / "mazo.src").exists())
        self.assertFalse((self.clips / "mazo.src.origen").exists())
        self.assertFalse((self.clips / "mazo.hoja.jpg").exists())
        self.assertFalse((self.v / "mazo-3-420-f.mp4").exists())
        self.assertTrue(
            (self.clips / "mazo-roto.src").exists(),
            "a key sharing the prefix is another clip",
        )
        self.assertTrue((self.v / "mazo-roto-0-300-f.mp4").exists())
        self.assertEqual(
            json.loads((self.clips / "detalle.json").read_text(encoding="utf-8")),
            {"mazo-roto@0": 5.0},
        )
        fichas = json.loads((self.clips / "creditos.json").read_text(encoding="utf-8"))
        self.assertEqual([f["archivo"] for f in fichas], ["mazo-roto.src"])

    def test_same_source_touches_nothing(self):
        self._cache("mazo", "111", "mazo-3-420-f.mp4")
        self._fichas("mazo.src")
        self.assertEqual(
            broll.purgar_cambiados({"mazo": {"pexels": 111}}, self.clips), []
        )
        self.assertTrue((self.v / "mazo-3-420-f.mp4").exists())
        self.assertEqual(
            len(json.loads((self.clips / "creditos.json").read_text(encoding="utf-8"))),
            1,
        )

    def test_clip_without_source_record_is_kept(self):
        (self.clips / "viejo.src").write_bytes(b"x")
        (self.v / "viejo-0-300-f.mp4").write_bytes(b"x")
        self.assertEqual(
            broll.purgar_cambiados({"viejo": {"pexels": 1}}, self.clips), []
        )
        self.assertTrue((self.v / "viejo-0-300-f.mp4").exists())

    def test_credit_of_a_clip_no_longer_declared_is_dropped(self):
        self._fichas("sigue.src", "quitado.src")
        broll.purgar_cambiados({"sigue": {"pexels": 1}}, self.clips)
        fichas = json.loads((self.clips / "creditos.json").read_text(encoding="utf-8"))
        self.assertEqual([f["archivo"] for f in fichas], ["sigue.src"])


class CreditosValidarTest(CacheClipsTest):
    def test_validating_keeps_undeclared_credits(self):
        self._fichas("sigue.src", "quitado.src")
        broll.purgar_cambiados({"sigue": {"pexels": 1}}, self.clips, huerfanos=False)
        self.assertEqual(len(json.loads((self.clips / "creditos.json").read_text(encoding="utf-8"))), 2)


class AniosTest(unittest.TestCase):
    def _oido(self, *ws: str) -> list[dict]:
        return [{"word": w, "start": float(i), "end": i + 0.5} for i, w in enumerate(ws)]

    def test_year_read_as_a_year_is_the_script(self):
        for oido in (
            ("In", "nineteen", "twenty", "nine", "he", "won."),
            ("In", "nineteen-twenty-nine", "he", "won."),
        ):
            r = mga.comparar("In 1929 he won.", self._oido(*oido))
            self.assertEqual((r["grave"], r["leve"]), ([], []), oido)

    def test_other_year_forms(self):
        for guion, oido in (
            ("1905", ("nineteen", "oh", "five")),
            ("2024", ("twenty", "twenty", "four")),
            ("2008", ("two", "thousand", "eight")),
            ("1900", ("nineteen", "hundred")),
            ("1920s", ("nineteen", "twenties")),
        ):
            r = mga.comparar(f"Back in {guion} it fell.", self._oido("Back", "in", *oido, "it", "fell."))
            self.assertEqual(r["grave"], [], guion)

    def test_a_different_year_is_still_a_defect(self):
        r = mga.comparar("In 1929 he won.", self._oido("In", "nineteen", "thirty", "nine", "he", "won."))
        self.assertEqual(len(r["grave"]), 1)

    def test_year_form_does_not_excuse_a_plain_number(self):
        r = mga.comparar("It cost 48 dollars.", self._oido("It", "cost", "nineteen", "twenty", "nine", "dollars."))
        self.assertEqual(len(r["grave"]), 1)


def _voz():
    spec = importlib.util.spec_from_file_location("voz_motor", RAIZ / "video-v2" / "motor" / "voz.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _palabras(*huecos: tuple[str, float]) -> list[dict]:
    """[(word, silence after it)] -> what alinear_audio returns."""
    out, t = [], 0.0
    for w, h in huecos:
        out.append({"w": w, "t0": t, "t1": t + 0.3})
        t += 0.3 + h
    return out


class TomasVozTest(unittest.TestCase):
    ROTA = _palabras(("One", 0.1), ("million", 0.48), ("dollars.", 0.1), ("Gone.", 0.1))
    PEOR = _palabras(("One", 0.6), ("million", 0.48), ("dollars.", 0.1), ("Gone.", 0.1))
    LIMPIA = _palabras(("One", 0.1), ("million", 0.1), ("dollars.", 0.1), ("Gone.", 0.1))

    def _elegir(self, *tomas):
        v, pendientes, hechas = _voz(), list(tomas), []

        def sintetizar():
            hechas.append(1)
            return pendientes.pop(0)

        return v.mejor_toma(sintetizar, lambda m: m), hechas

    def test_stops_at_the_first_clean_take(self):
        r, hechas = self._elegir(self.ROTA, self.LIMPIA, self.ROTA)
        self.assertEqual((r["rotas"], r["palabras"], len(hechas)), ([], self.LIMPIA, 2))

    def test_at_most_three_takes_and_keeps_the_best(self):
        r, hechas = self._elegir(self.PEOR, self.ROTA, self.PEOR, self.LIMPIA)
        self.assertEqual(len(hechas), 3)
        self.assertEqual(r["palabras"], self.ROTA)
        self.assertEqual(len(r["rotas"]), 1)

    def test_a_comma_pause_is_not_a_broken_take(self):
        r, hechas = self._elegir(_palabras(("One,", 0.48), ("two.", 0.1)))
        self.assertEqual((r["rotas"], len(hechas)), ([], 1))

    def test_names_the_sentence_to_rewrite(self):
        v = _voz()
        r, _ = self._elegir(self.ROTA, self.ROTA, self.ROTA)
        sb = {"guion": [{"id": "gancho", "texto": "One million dollars."}, {"id": "fin", "texto": "Gone."}]}
        msg = v.frases_a_reescribir(sb, r["palabras"], r["rotas"])
        self.assertEqual(len(msg), 1)
        self.assertIn("gancho", msg[0])
        self.assertIn("One million dollars.", msg[0])
        self.assertIn("million", msg[0])

    def test_existing_voice_is_not_touched_without_forzar(self):
        v = _voz()
        with tempfile.TemporaryDirectory() as d:
            proy = Path(d)
            (proy / "assets").mkdir()
            (proy / "assets" / "voice.mp3").write_bytes(b"old")
            (proy / "storyboard.json").write_text('{"guion": [{"id": "a", "texto": "x"}]}', encoding="utf-8")
            with mock.patch.object(sys, "argv", ["voz.py", str(proy)]), mock.patch.object(v, "mejor_toma") as tomar:
                with self.assertRaises(SystemExit):
                    v.main()
            tomar.assert_not_called()
            self.assertEqual((proy / "assets" / "voice.mp3").read_bytes(), b"old")


class ClipsVistosTest(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        self.proy = Path(d.name) / "nuevo"
        (self.proy / "assets" / "clips").mkdir(parents=True)

    def test_clip_not_looked_at_is_rejected(self):
        e = puertas.clips_sin_ver({"clips": {"mazo": {"pexels": 1}}}, self.proy)
        self.assertEqual(len(e), 1)
        self.assertIn("mazo", e[0])
        self.assertIn("broll.py lote", e[0])

    def test_visto_without_its_sheet_is_rejected(self):
        """Changing the source deletes the sheet (broll.purgar_cambiados): an old `visto` does not cover the new clip."""
        e = puertas.clips_sin_ver({"clips": {"mazo": {"pexels": 1, "visto": True}}}, self.proy)
        self.assertEqual(len(e), 1)

    def test_visto_with_sheet_passes(self):
        (self.proy / "assets" / "clips" / "mazo.hoja.jpg").write_bytes(b"x")
        self.assertEqual(puertas.clips_sin_ver({"clips": {"mazo": {"pexels": 1, "visto": True}}}, self.proy), [])

    def test_build_rejects_it_and_older_videos_are_exempt(self):
        sb = {"clips": {"mazo": {"pexels": 1}}, "guion": []}
        self.assertTrue(c._puertas(self.proy, sb, [], True, False))
        anterior = self.proy.parent / "ronald-wayne"
        self.assertEqual(c._puertas(anterior, sb, [], True, False), [])

    def test_sheet_reads_the_text_inside_the_clip(self):
        from PIL import Image, ImageDraw, ImageFont

        png = self.proy / "f.png"
        im = Image.new("RGB", (1280, 720), (30, 60, 40))
        ImageDraw.Draw(im).text((200, 300), "NARODOWY BANK POLSKI", fill="white", font=ImageFont.load_default(72))
        im.save(png)
        crudo = self.proy / "assets" / "clips" / "billetes.src"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", "4", "-i", str(png), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-f", "mp4", str(crudo)],
            check=True,
        )
        textos = broll.hoja_clip(crudo)
        self.assertTrue((crudo.with_suffix(".hoja.jpg")).stat().st_size > 0)
        self.assertIn("NARODOWY BANK POLSKI", " ".join(textos))
        self.assertIn("NARODOWY", crudo.with_suffix(".hoja.txt").read_text(encoding="utf-8"))


class PrevioTest(unittest.TestCase):
    PLAN = {
        "D": 12.0,
        "escenas": [
            {"tipo": "foto", "t0": 0.0, "t1": 4.0, "rotulos": [{"texto": "Late label", "en": 3.0, "hasta": 4.0}]},
            {"tipo": "foto", "t0": 4.0, "t1": 12.0, "rotulos": [{"texto": "Doc label", "en": 6.0, "hasta": 8.0}]},
        ],
        "pruebas": [{"img": "nyt", "t0": 6.0, "t1": 8.0}],
    }
    SB = {
        "escenas": [
            {"tipo": "foto", "rotulos": [{"texto": "Late *label*"}]},
            {"tipo": "foto", "rotulos": [{"texto": "Doc label"}]},
        ],
        "pruebas": [{"img": "nyt", "texto": "COLLAPSE"}],
    }
    WORDS = [{"text": "Words.", "start": 0.1, "end": 0.5}]

    @staticmethod
    def _frame(t, *lineas):
        return {
            "t": t,
            "ancho": 1080,
            "alto": 1920,
            "lineas": [{"texto": x, "conf": 0.9, "caja": c, "contraste": 9.0} for x, c in lineas],
        }

    def test_each_text_is_sampled_inside_its_own_window(self):
        m = critico.muestreo_previo(self.SB, self.PLAN, self.WORDS, [2.4, 9.0])
        late = next(e for e in m["textos"] if e["texto"] == "Late label")
        self.assertEqual((late["t0"], late["t1"]), (3.0, 4.0))
        self.assertTrue(any(3.0 <= x < 4.0 for x in m["ocr"]))
        self.assertTrue(set(m["ocr"]) <= set(m["todos"]))
        self.assertTrue({2.4, 9.0} <= set(m["todos"]), "the per-scene frames stay on the sheet")

    def test_a_document_gets_enough_frames_for_the_overlap_measure(self):
        m = critico.muestreo_previo(self.SB, self.PLAN, self.WORDS, [2.4])
        dentro = [x for x in m["ocr"] if 6.0 <= x < 8.0]
        self.assertGreaterEqual(len(dentro), 2)
        self.assertGreater(min(dentro), 6.2, "the first frames of a document are its entrance")

    def test_text_partly_under_a_document_is_sampled_where_it_shows(self):
        plan = {
            "D": 10.0,
            "escenas": [{"tipo": "foto", "t0": 0.0, "t1": 10.0, "rotulos": [{"texto": "Under", "en": 0.0, "hasta": 8.0}]}],
            "pruebas": [{"img": "nyt", "t0": 2.0, "t1": 7.9}],
        }
        sb = {"escenas": [{"tipo": "foto", "rotulos": [{"texto": "Under"}]}], "pruebas": [{"img": "nyt", "texto": ""}]}
        m = critico.muestreo_previo(sb, plan, self.WORDS, [])
        self.assertTrue(any(x < 2.0 for x in m["ocr"]), m["ocr"])

    def test_unreadable_label_blocks_and_read_ones_do_not(self):
        rub = {"criterios": json.loads((RAIZ / "video-v2" / "motor" / "rubrica.json").read_text(encoding="utf-8"))["criterios"]}
        bien = [
            self._frame(3.6, ("Late label", [100, 500, 600, 560])),
            self._frame(6.8, ("Doc label", [100, 500, 600, 560]), ("COLLAPSE", [100, 100, 900, 200])),
            self._frame(7.3, ("Doc label", [100, 500, 600, 560]), ("COLLAPSE", [100, 100, 900, 200])),
        ]
        self.assertEqual([f for f in critico.revisar_previo(self.SB, self.PLAN, self.WORDS, bien, rub) if f["severidad"] == "alta"], [])
        mal = [bien[0], self._frame(6.8, ("D0c", [100, 500, 600, 560])), self._frame(7.3, ("D0c", [100, 500, 600, 560]))]
        fallos = critico.revisar_previo(self.SB, self.PLAN, self.WORDS, mal, rub)
        self.assertTrue(any("Doc label" in f["detalle"] and f["severidad"] == "alta" for f in fallos))

    def test_brand_over_the_headline_is_named_the_right_way_round(self):
        """jesse-livermore: the document's phrase counted as design, so the headline was "the caption" and the brand "the document"."""
        u = json.loads((RAIZ / "video-v2" / "motor" / "rubrica.json").read_text(encoding="utf-8"))["criterios"]["C1"]
        frames = [
            self._frame(t, ("Net Worthy", [100, 150, 400, 200]), ("STOCKS COLLAPSE", [100, 120, 900, 230])) for t in (6.5, 7.0)
        ]
        diseno = [{"texto": "COLLAPSE", "t0": 6.0, "t1": 8.0, "doc": True}, {"texto": "STOCKS COLLAPSE", "t0": 6.0, "t1": 8.0, "doc": True}]
        fallos = pf.revisar_cajas(frames, diseno, {"pruebas": self.PLAN["pruebas"]}, [], u, lambda _c, _s, d, **k: {"detalle": d, **k}, lambda _t, _v: None)
        self.assertEqual(len(fallos), 1, fallos)
        self.assertTrue(fallos[0]["detalle"].startswith('"Net Worthy" encima'), fallos[0]["detalle"])

    def test_preview_frames_are_matched_by_their_second(self):
        with tempfile.TemporaryDirectory() as d:
            for n in ("frame-00-at-1.99s.png", "frame-01-at-14.5s.png"):
                (Path(d) / n).write_bytes(b"x")
            with mock.patch("medir_cuadros.ocr_imagen", return_value={"ancho": 1080, "alto": 1920, "lineas": []}) as ocr:
                frames = producir.ocr_previo(Path(d), [14.5])
            self.assertEqual([f["t"] for f in frames], [14.5])
            self.assertEqual(ocr.call_count, 1)

    def test_a_line_split_by_the_ocr_is_read_in_screen_order(self):
        """Measured on a preview frame of jesse-livermore: "$100 million?" came back as "million?" then "$1001"."""
        f = self._frame(25.3, ("That", [300, 500, 500, 560]), ("million?", [500, 620, 900, 720]), ("$1001", [200, 620, 480, 720]))
        rt = medir_texto.analizar([f], [{"texto": "$100 million?", "escena": 0, "t0": 25.0, "t1": 26.0}])
        self.assertEqual(rt["no_leidos"], [])

    def test_in_the_preview_text_over_a_document_stops_and_unread_only_warns(self):
        with tempfile.TemporaryDirectory() as d:
            proy = Path(d)
            (proy / "assets").mkdir()
            (proy / "index.html").write_text("", encoding="utf-8")
            (proy / "assets" / "words.json").write_text("[]", encoding="utf-8")
            base = {"t": 1.0, "t_fin": None, "escena": 0, "severidad": "alta", "detalle": "x"}
            for criterio, pasa in (("L1", True), ("C2", False)):
                with mock.patch.object(producir, "ocr_previo", return_value=[]), mock.patch.object(
                    critico, "revisar_previo", return_value=[{**base, "criterio": criterio}]
                ):
                    self.assertEqual(producir.texto_previo(proy, {}, {"ocr": []})[0], pasa, criterio)

    def test_social_without_story_ignores_an_old_render(self):
        self.assertIn("con_historia", social.generar.__code__.co_varnames)


if __name__ == "__main__":
    unittest.main()
