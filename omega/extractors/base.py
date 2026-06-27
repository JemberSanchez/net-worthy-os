"""Interfaz de extractores (capa de DOMINIO).

Un extractor transforma un asset crudo (un item RSS hoy; un video de YouTube mañana) en
SEÑALES genéricas que el kernel almacena. Añadir una capacidad = un archivo nuevo en este
paquete, sin tocar el núcleo.
"""
from __future__ import annotations
from typing import Protocol, TypedDict, runtime_checkable


class Signal(TypedDict, total=False):
    name: str               # 'theme', 'language', 'title_length'...
    value: str | None       # valor categórico
    value_num: float | None # valor numérico
    kind: str               # 'categorical' | 'numeric'
    confidence: float


@runtime_checkable
class Extractor(Protocol):
    name: str
    version: str

    def extract(self, asset: dict) -> list[Signal]:
        ...
