"""La definición de ÉXITO es el corazón del moat: si está mal, todo lo que el sistema 'aprende'
está sesgado. Estos tests fijan el contrato de la v2."""
import sqlite3
import unittest

from omega.creative import decisions, production_dna, scoring


class TestScoring(unittest.TestCase):

    def test_retencion_manda_sobre_alcance(self):
        """Dos videos con el MISMO alcance pero retención distinta NO pueden puntuar igual.
        Con la v1 (solo vistas) puntuaban idéntico: ese era el fallo."""
        bueno, _ = scoring.calcular(retention_avg=0.45, views=250)
        malo, _ = scoring.calcular(retention_avg=0.06, views=250)
        self.assertGreater(bueno, malo)
        # y la diferencia es grande, no marginal: la retención pesa el 70%
        self.assertGreater(bueno - malo, 0.4)

    def test_alcance_alto_no_tapa_retencion_mala(self):
        """El caso que envenenaba el dataset: un video con alcance de sobra y retención pésima
        no puede parecer un éxito solo porque muchos pasaron por encima."""
        s, partes = scoring.calcular(retention_avg=0.05, views=5000)
        self.assertLessEqual(s, 0.4)
        self.assertEqual(partes["alcance_norm"], 1.0)   # el alcance está topado

    def test_topes(self):
        s, _ = scoring.calcular(retention_avg=0.99, views=99999)
        self.assertLessEqual(s, 1.0)
        s0, _ = scoring.calcular(retention_avg=0.0, views=0)
        self.assertEqual(s0, 0.0)

    def test_umbral_de_distribucion_da_la_nota_de_retencion(self):
        """Retención = el umbral del algoritmo (50%) => la parte de retención va al máximo."""
        _, partes = scoring.calcular(retention_avg=scoring.UMBRAL_RETENCION, views=0)
        self.assertEqual(partes["retencion_norm"], 1.0)

    def test_sin_retencion_se_marca_parcial(self):
        """No se inventa un número: se puntúa con lo que hay y se avisa de que vale menos."""
        s, partes = scoring.calcular(retention_avg=None, views=375)
        self.assertTrue(partes["parcial"])
        self.assertIn("scroll-by", partes["motivo"])
        self.assertAlmostEqual(s, 0.5, places=3)

    def test_rechaza_porcentaje_en_vez_de_fraccion(self):
        """Mismo guard que el resto del módulo: teclear '11' por '0.11' envenena el dataset."""
        with self.assertRaises(ValueError):
            scoring.calcular(retention_avg=11.0, views=100)

    def test_sin_datos_no_puntua(self):
        with self.assertRaises(ValueError):
            scoring.calcular(retention_avg=None, views=None)

    def test_el_outcome_guarda_su_version(self):
        """Sin `score_version` no se puede saber si dos outcomes son comparables. Es el mismo gap
        que ya destapó `extractor_version` en las predicciones."""
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        decisions.init(con)
        production_dna.init(con)
        production_dna.record_analytics(con, production_ref="x", retention_avg=0.40, views=300)
        s, partes = scoring.desde_analytics(con, "x")
        decisions.record_outcome(con, "x", s, score_version=scoring.SCORE_VERSION, score_parts=partes)
        r = con.execute("SELECT success, score_version, score_parts FROM production_outcome "
                        "WHERE production_ref='x'").fetchone()
        self.assertEqual(r["score_version"], scoring.SCORE_VERSION)
        self.assertIn("retencion", r["score_parts"])
        self.assertAlmostEqual(r["success"], s, places=4)

    def test_migracion_idempotente_en_base_vieja(self):
        """Una base creada con el esquema ANTIGUO debe ganar las columnas al llamar init(),
        no fallar al insertar. `CREATE TABLE IF NOT EXISTS` no migra."""
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        con.execute("CREATE TABLE production_outcome (production_ref TEXT PRIMARY KEY, "
                    "success REAL NOT NULL, measured_at INTEGER NOT NULL)")
        con.commit()
        decisions.init(con)          # no debe explotar
        decisions.init(con)          # idempotente: dos veces tampoco
        cols = {r[1] for r in con.execute("PRAGMA table_info(production_outcome)")}
        self.assertIn("score_version", cols)
        self.assertIn("score_parts", cols)
        decisions.record_outcome(con, "y", 0.5, score_version="v2-retencion", score_parts={"a": 1})

    def test_sin_analytics_avisa(self):
        con = sqlite3.connect(":memory:")
        con.row_factory = sqlite3.Row
        decisions.init(con)
        production_dna.init(con)
        with self.assertRaises(ValueError) as ctx:
            scoring.desde_analytics(con, "no-existe")
        self.assertIn("record-analytics", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
