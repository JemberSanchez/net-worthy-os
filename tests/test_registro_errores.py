"""Error ratchet (video-v2/motor/errores.py): a closed error class must name a real fix and test,
and must never show up again in a run logged after it was closed."""

from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "video-v2" / "motor"))

import errores


def _existe_def(nombre: str, carpeta: Path) -> bool:
    pat = re.compile(rf"^\s*def {re.escape(nombre)}\(", re.MULTILINE)
    return any(pat.search(f.read_text(encoding="utf-8")) for f in carpeta.rglob("*.py"))


class TestRegistro(unittest.TestCase):
    def setUp(self):
        self.registro = errores.cargar()

    def test_entradas_validas(self):
        ids = [e["id"] for e in self.registro]
        self.assertEqual(len(ids), len(set(ids)), "ids repetidos")
        for e in self.registro:
            self.assertIn(e["estado"], errores.ESTADOS, e["id"])
            re.compile(e["patron"])
            self.assertRegex(e["ejemplo"], e["patron"], e["id"])

    def test_cerrada_nombra_arreglo_y_test_que_existen(self):
        for e in self.registro:
            if e["estado"] == "abierto":
                continue
            funcion = e["donde"].split(".")[-1]
            self.assertTrue(_existe_def(funcion, RAIZ / "video-v2" / "motor"), e)
            self.assertTrue(_existe_def(e["test"], RAIZ / "tests"), e)

    def test_ninguna_cerrada_reaparece(self):
        """Run logs are gitignored: this checks the local history, and passes empty in CI."""
        regresiones = []
        for f in (RAIZ / "video-v2").glob("*/renders/corridas.jsonl"):
            for s in f.read_text(encoding="utf-8").splitlines():
                if not s.strip():
                    continue
                x = json.loads(s)
                if not x.get("fallo"):
                    continue
                dia = datetime.fromtimestamp(x["t"]).date().isoformat()
                for r in errores.reglas_de(x):
                    e = errores.entrada_de(r, self.registro)
                    if e and e["estado"] != "abierto" and dia > e["cerrado"]:
                        regresiones.append(
                            f"{e['id']} {f.parent.parent.name} {dia}: {r[:80]}"
                        )
        self.assertEqual(regresiones, [])


class TestRevisar(unittest.TestCase):
    def test_nuevo_se_registra_y_luego_es_abierto(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "e.json"
            regla = 'diapositiva 3: "Buy now" toca el borde'
            out = errores.revisar([regla], ruta, "2026-11-17")
            self.assertEqual([i for i, _ in out["nuevos"]], ["E1"])
            out = errores.revisar(['diapositiva 5: "Other" toca el borde'], ruta)
            self.assertEqual(out["nuevos"], [])
            self.assertEqual([i for i, _ in out["abiertos"]], ["E1"])

    def test_cerrada_que_vuelve_es_regresion(self):
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "e.json"
            errores.revisar(["Hay 3 s sin nada nuevo en pantalla"], ruta, "2026-11-17")
            reg = errores.cargar(ruta)
            reg[0]["estado"] = "prevenido"
            ruta.write_text(json.dumps(reg), encoding="utf-8")
            out = errores.revisar(["ritmo: Hay 4.5 s sin nada nuevo en pantalla"], ruta)
            self.assertEqual([i for i, _ in out["regresiones"]], ["E1"])

    def test_patron_ignora_cifras_citas_y_lista_final(self):
        p = errores.patron_de(
            "repite los últimos vídeos: efectos: 0.43 > 0.34 con los últimos 3 vídeos (Deep hit.wav)"
        )
        self.assertRegex(
            "storyboard: repite los últimos vídeos: efectos: 0.5 > 0.34 con los últimos 3 vídeos (x.wav)",
            p,
        )

    def test_auto_usa_pendientes_y_manual_las_reglas(self):
        self.assertEqual(
            errores.reglas_de({"reglas": {"g": ["a"]}, "pendientes": ["b"]}), ["b"]
        )
        self.assertEqual(errores.reglas_de({"reglas": {"g": ["a"]}}), ["a"])


if __name__ == "__main__":
    unittest.main()
