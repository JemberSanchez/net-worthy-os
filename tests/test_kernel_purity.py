"""Architecture fitness test: "el kernel no sabe qué es un video".

Enforcea la regla a nivel de IMPORTS (robusto: ignora comentarios y strings, a diferencia
de un grep de palabras). El kernel (omega/reasoning) no puede:
  - importar paquetes de dominio (omega.sources, omega.analyze, omega.extractors),
  - importar librerías de dominio (feedparser),
  - usar imports relativos que escapen del paquete kernel (level >= 2, p.ej. `from ..analyze`).

Si alguien acopla el kernel a una plataforma, este test falla. El principio no se puede pudrir.
"""
from __future__ import annotations
import ast
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
KERNEL_DIR = ROOT / "omega" / "reasoning"
FORBIDDEN_ABS_PREFIXES = ("omega.sources", "omega.analyze", "omega.extractors")
FORBIDDEN_TOP = {"feedparser"}


def _violations(path: pathlib.Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    bad: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith(FORBIDDEN_ABS_PREFIXES) or a.name.split(".")[0] in FORBIDDEN_TOP:
                    bad.append(f"import {a.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.level >= 2:  # escapa del paquete kernel
                bad.append(f"from {'.' * node.level}{node.module or ''} ...")
            elif node.level == 0 and node.module:
                if node.module.startswith(FORBIDDEN_ABS_PREFIXES) or node.module.split(".")[0] in FORBIDDEN_TOP:
                    bad.append(f"from {node.module} import ...")
    return bad


class KernelPurityTest(unittest.TestCase):
    def test_kernel_has_no_domain_coupling(self):
        files = list(KERNEL_DIR.glob("*.py"))
        self.assertTrue(files, "no se encontraron módulos del kernel")
        for py in files:
            with self.subTest(module=py.name):
                bad = _violations(py)
                self.assertEqual(bad, [], f"{py.name} acopla el kernel al dominio: {bad}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
