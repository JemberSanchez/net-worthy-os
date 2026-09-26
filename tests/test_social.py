"""Tests de las páginas vivas: generador de carrusel/historia (partes puras) y publicación en Meta
con un _request FALSO. Lo crítico: sin publish=True no sale NADA hacia Meta (regla del proyecto)."""
from __future__ import annotations
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "video-v2", "motor"))

import social  # noqa: E402
from omega import publish_meta as pm  # noqa: E402

SB = {"imagenes": {"a": {}}, "clips": {"c": {"pexels": 1}},
      "cifras": [{"dato": "x", "fuente": "https://en.wikipedia.org/wiki/X"}],
      "aviso": {"lineas": ["Not financial advice"]},
      "publicacion": {"hashtags": ["#shorts", "#investing", "#money"]},
      "social": {"carrusel": [{"fondo": "clip:c@1", "titulo": "*$8M*", "kicker": "K"},
                              {"fondo": "img:a", "titulo": "Dos"}, {"fondo": "img:a", "titulo": "Tres"}],
                 "caption": "Texto base."}}


class GeneradorTest(unittest.TestCase):
    def test_valida(self):
        self.assertEqual(social.validar(SB), [])
        import copy
        d = copy.deepcopy(SB); d["social"]["carrusel"] = d["social"]["carrusel"][:2]
        self.assertTrue(any("3-10" in e for e in social.validar(d)))
        d = copy.deepcopy(SB); d["social"]["carrusel"][1]["fondo"] = "img:nada"
        self.assertTrue(any("'nada' no declarada" in e for e in social.validar(d)))
        d = copy.deepcopy(SB); d["social"]["carrusel"][0]["texto"] = "x" * 200
        self.assertTrue(any("máx. 170" in e for e in social.validar(d)))

    def test_captions_con_aviso_fuentes_y_sin_shorts(self):
        c = social.captions(SB)
        self.assertTrue(c["caption_ig"].startswith("Texto base."))
        self.assertIn("Not financial advice", c["caption_ig"])
        self.assertIn("wikipedia.org/wiki/X", c["caption_ig"])
        self.assertIn("#investing", c["caption_ig"])
        self.assertNotIn("#shorts", c["caption_ig"])                  # etiqueta de YouTube, no de IG
        self.assertIn("Sources:\n- https://en.wikipedia.org/wiki/X", c["caption_fb"])
        self.assertEqual(c["alt"], "$8M / Dos / Tres")

    def test_html_del_carrusel(self):
        h = social._html_carrusel(SB["social"]["carrusel"], ["f1.jpg", "f2.jpg", "f3.jpg"])
        self.assertEqual(h.count('class="clip slide'), 3)
        self.assertIn('<span class="gold">$8M</span>', h)
        self.assertIn("Swipe", h)                                       # solo en la portada
        self.assertEqual(h.count("Swipe"), 1)
        self.assertIn("@networthytv", h)
        self.assertIn('data-width="1080" data-height="1350"', h)

    def test_tarjeta_de_historia_sin_elementos_de_carrusel(self):
        h = social._html_tarjeta("How a janitor made *$8M*", "Full story in our Reels")
        self.assertNotIn("Swipe", h); self.assertNotIn('class="dots"', h); self.assertNotIn('class="num"', h)
        self.assertEqual(h.count("@networthytv"), 0)                    # sin línea de follow duplicada
        self.assertIn('data-width="1080" data-height="1920"', h)


class PublicacionMetaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.imgs = []
        for i in range(3):
            p = Path(self.tmp.name, f"{i}.jpg"); p.write_bytes(b"jpg"); self.imgs.append(p)
        self.mp4 = Path(self.tmp.name, "h.mp4"); self.mp4.write_bytes(b"mp4")

    def tearDown(self):
        self.tmp.cleanup()

    def test_sin_publish_no_sale_nada(self):
        with mock.patch.object(pm, "_request", side_effect=AssertionError("llamó a Meta")):
            for r in (pm.upload_instagram_carousel(self.imgs, "c"), pm.upload_facebook_carousel(self.imgs, "c"),
                      pm.upload_instagram_story(self.mp4), pm.upload_facebook_story(self.mp4)):
                self.assertIn("sin enviar", r["status"])

    def test_carrusel_ig_usa_urls_de_la_pagina(self):
        llamadas = []

        def falso(method, url, **kw):
            llamadas.append((method, url.split("/v25.0/")[-1], dict(kw.get("data") or kw.get("params") or {})))
            if url.endswith("/photos"):
                return {"id": f"f{len(llamadas)}"}
            if "fields" in (kw.get("params") or {}) and kw["params"]["fields"] == "images":
                return {"images": [{"width": 720, "source": "https://cdn/s.jpg"}, {"width": 1080, "source": "https://cdn/L.jpg"}]}
            if url.endswith("/media") and (kw.get("data") or {}).get("media_type") == "CAROUSEL":
                return {"id": "CAR"}
            if url.endswith("/media"):
                return {"id": f"h{len(llamadas)}"}
            if "status_code" in str(kw.get("params")):
                return {"status_code": "FINISHED"}
            if url.endswith("/media_publish"):
                return {"id": "M1"}
            return {"permalink": "https://instagram.com/p/X"}

        with mock.patch.object(pm, "_request", side_effect=falso), \
             mock.patch.object(pm, "_get_page_token", return_value={"page_id": "P", "page_access_token": "T", "ig_user_id": "IG"}):
            r = pm.upload_instagram_carousel(self.imgs, "pie", publish=True)
        self.assertEqual(r, {"media_id": "M1", "url": "https://instagram.com/p/X"})
        hijos = [d for m, u, d in llamadas if d.get("is_carousel_item")]
        self.assertEqual(len(hijos), 3)
        self.assertTrue(all(h["image_url"] == "https://cdn/L.jpg" for h in hijos))   # la mayor resolución
        car = next(d for m, u, d in llamadas if d.get("media_type") == "CAROUSEL")
        self.assertEqual(car["caption"], "pie")
        self.assertEqual(len(car["children"].split(",")), 3)

    def test_limites_del_carrusel(self):
        with self.assertRaises(pm.PublishError):
            pm.upload_instagram_carousel(self.imgs[:1], "c", publish=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
