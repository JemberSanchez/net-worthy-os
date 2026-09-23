"""Tests de tools/imagenes_libres.py: la puerta de copyright y la elección de miniatura.

`licencia_ok` decide qué imagen puede entrar en un video monetizable: un falso positivo aquí es
una reclamación de copyright, así que se prueba la lista cerrada caso por caso.
"""
from __future__ import annotations
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import imagenes_libres as il  # noqa: E402


class LicenciaTest(unittest.TestCase):
    def test_admitidas(self):
        for n, clase in (("Public domain", "pd"), ("PD-US", "pd"), ("PD-USGov", "pd"),
                         ("CC0", "cc0"), ("CC BY 4.0", "cc-by"), ("CC BY 2.0", "cc-by"),
                         ("CC-BY-3.0", "cc-by")):
            self.assertEqual(il.licencia_ok(n), clase, n)

    def test_rechazadas(self):
        # SA: el share-alike puede extenderse al video · NC: el canal monetiza · ND: el duotono ES derivada
        for n in ("CC BY-SA 4.0", "CC BY-SA 3.0", "CC BY-NC 4.0", "CC BY-ND 2.0",
                  "CC BY-NC-SA 2.0", "GFDL", "Fair use", "", None, "Copyrighted", "All rights reserved"):
            self.assertIsNone(il.licencia_ok(n), n)


class MiniaturaTest(unittest.TestCase):
    def test_elige_el_menor_ancho_estandar_que_da_el_alto(self):
        # vertical 3442x4319: 1920 de ancho -> 2409 de alto, basta
        self.assertIn("/1920px-", il.miniatura("File:A.jpg", 3442, 4319))
        # apaisada grande: 1920 -> ~1470 de alto, no basta -> 3840
        self.assertIn("/3840px-", il.miniatura("File:B.jpg", 13869, 10576))

    def test_si_ninguno_llega_toma_el_mayor_que_quepa_nunca_el_original(self):
        # 3000x1989: 3840 > original -> el mayor que cabe es 1920 (aunque no llegue al alto)
        self.assertIn("/1920px-", il.miniatura("File:C.jpg", 3000, 1989))
        # 1175 de ancho: 1280 no cabe -> 960
        self.assertIn("/960px-", il.miniatura("File:D.jpg", 1175, 1536))

    def test_tif_se_sirve_como_jpg_de_la_primera_pagina(self):
        u = il.miniatura("File:E e.tif", 13869, 10576)
        self.assertTrue(u.endswith("/lossy-page1-3840px-E_e.tif.jpg"), u)

    def test_ruta_md5_de_commons(self):
        # ruta verificada contra upload.wikimedia.org el 23-sep (respondió 200)
        u = il.miniatura("File:Russellfillingstation.jpg", 3000, 1989)
        import hashlib
        h = hashlib.md5(b"Russellfillingstation.jpg").hexdigest()
        self.assertIn(f"/thumb/{h[0]}/{h[:2]}/Russellfillingstation.jpg/", u)

    def test_sin_tamano_no_inventa(self):
        self.assertIsNone(il.miniatura("File:F.jpg", None, None))
        self.assertIsNone(il.miniatura("File:G.jpg", 400, 300))   # más chica que cualquier estándar útil


if __name__ == "__main__":
    unittest.main(verbosity=2)
