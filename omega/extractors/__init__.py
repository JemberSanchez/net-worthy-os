"""Registro de extractores con auto-descubrimiento.

Suelta un archivo nuevo en este paquete con un objeto module-level `EXTRACTOR` y queda
registrado automáticamente. El núcleo nunca cambia. (La regla: "nunca un if".)
"""
from __future__ import annotations
import importlib
import pkgutil

_SKIP = {"base", "run"}


def load_extractors() -> list:
    """Descubre e instancia todos los extractores del paquete. Resiliente: un extractor
    roto se reporta y se omite, sin tumbar al resto."""
    exts = []
    for m in pkgutil.iter_modules(__path__):
        if m.name in _SKIP or m.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"{__name__}.{m.name}")
        except Exception as exc:  # noqa: BLE001
            print(f"[extractors] no se pudo cargar {m.name}: {exc}")
            continue
        ext = getattr(mod, "EXTRACTOR", None)
        if ext is not None:
            exts.append(ext)
    return exts
