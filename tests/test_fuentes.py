"""Every figure in `cifras` must be on its source page (F1 decision 5): video-v2/motor/fuentes.py."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "video-v2" / "motor"), str(RAIZ / "tools")]

import fuentes as F


class Numeros(unittest.TestCase):
    def test_magnitudes_and_formats_normalise(self):
        vals = [
            round(n["v"])
            for n in F.numeros("$64.16B, 850,364 BTC and $8 million; 10% stake")
        ]
        self.assertEqual(vals, [64_160_000_000, 850_364, 8_000_000, 10])

    def test_own_calculations_are_not_checked(self):
        d = "Held 850,364 BTC; 850,364 / 21,000,000 = 4.05%, about 1 in 25 (own calculation)"
        self.assertEqual([n["v"] for n in F.numeros_a_verificar(d)], [850_364])
        d = "kept his shares, about $70 billion (shown on screen as 70, in billions of dollars)"
        self.assertEqual([n["v"] for n in F.numeros_a_verificar(d)], [70e9])


class Encontrada(unittest.TestCase):
    def test_rounding_tolerance_by_stated_precision(self):
        pagina = F.numeros(
            "aggregate cost of $64,158.9 million and an estate worth $7,950,000"
        )
        self.assertTrue(F.encontrada(F.numeros("$64.16B")[0], pagina))
        self.assertTrue(F.encontrada(F.numeros("~$8 million")[0], pagina))
        self.assertFalse(F.encontrada(F.numeros("$65.2B")[0], pagina))


class Revisar(unittest.TestCase):
    def test_missing_figure_and_unreachable_source_block(self):
        paginas = {"https://a.example/x": "Strategy held 850,364 BTC at $75,456 each."}

        def leer(url):
            if url not in paginas:
                raise OSError("HTTP 403")
            return paginas[url]

        malos = F.revisar(
            [
                {"dato": "850,364 BTC at $75,456", "fuente": "https://a.example/x"},
                {"dato": "cost $64.16B", "fuente": "https://a.example/x"},
                {"dato": "12 days later", "fuente": "https://b.example/y"},
            ],
            leer,
        )
        self.assertEqual(len(malos), 2)
        self.assertIn("64.16B", malos[0])
        self.assertIn("403", malos[1])

    def test_cache_avoids_second_fetch(self):
        llamadas = []

        def bajar(url):
            llamadas.append(url)
            return "<html><body><script>var x=9;</script><p>Price: $1,234.50</p></body></html>"

        with tempfile.TemporaryDirectory() as d:
            leer = F.lector(Path(d), bajar)
            self.assertNotIn("var x", leer("https://c.example/p"))
            self.assertIn("1,234.50", leer("https://c.example/p"))
        self.assertEqual(llamadas, ["https://c.example/p"])


if __name__ == "__main__":
    unittest.main()
