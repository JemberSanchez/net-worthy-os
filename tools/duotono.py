"""Trata una imagen con la paleta de la marca: duotono verde #0A1A14 -> dorado #D8B25A.

    python tools/duotono.py <entrada.jpg> <salida.jpg> [--recorte 0.03] [--contraste 1.15] [--ancho 1400]

Por qué
-------
Fotos de archivo de fuentes distintas (Kodachrome de 1940, negativos de la FSA, certificados
del XIX, una foto digital del parqué) no parecen un mismo vídeo hasta que comparten paleta. El
duotono las unifica y las ata a la marca. Se hace AQUÍ, una vez, y no con filtros CSS en cada
frame: el render de HyperFrames captura frame a frame, así que un filtro por frame se paga ~1500
veces y además depende del compositor del navegador.

El grano y el movimiento de cámara NO van aquí: van animados en la composición (grano estático
horneado en la foto se ve como suciedad fija, no como película).

--recorte quita un margen por lado (fracción): los negativos de la FSA traen el marco y el número
de negativo quemados en el borde.
"""
from __future__ import annotations

import argparse

import numpy as np
from PIL import Image, ImageOps

OSCURO = np.array([0x0A, 0x1A, 0x14], dtype=np.float32)   # --bg de la marca
MEDIO = np.array([0x3E, 0x5A, 0x3C], dtype=np.float32)    # verde medio: evita el gris sucio del lerp directo
CLARO = np.array([0xD8, 0xB2, 0x5A], dtype=np.float32)    # --gold de la marca
LUZ = np.array([0xF4, 0xE6, 0xC0], dtype=np.float32)      # altas luces: papel envejecido, no blanco puro


def duotono(img: Image.Image, recorte: float = 0.0, contraste: float = 1.15,
            ancho: int | None = None) -> Image.Image:
    """Función pura sobre PIL (testeable sin disco)."""
    if recorte > 0:
        dx, dy = int(img.width * recorte), int(img.height * recorte)
        img = img.crop((dx, dy, img.width - dx, img.height - dy))
    if ancho and img.width > ancho:
        img = img.resize((ancho, round(img.height * ancho / img.width)), Image.LANCZOS)
    g = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    y = np.asarray(g, dtype=np.float32) / 255.0
    # curva S suave centrada en 0.5 (contraste > 1 separa sombras y luces)
    y = np.clip(0.5 + (y - 0.5) * contraste, 0, 1)
    y = y * y * (3 - 2 * y) * 0.35 + y * 0.65
    # rampa de 4 paradas: oscuro -> medio -> dorado -> luz
    paradas = [(0.0, OSCURO), (0.38, MEDIO), (0.78, CLARO), (1.0, LUZ)]
    out = np.zeros(y.shape + (3,), dtype=np.float32)
    for (t0, c0), (t1, c1) in zip(paradas, paradas[1:]):
        m = (y >= t0) & (y <= t1)
        u = ((y[m] - t0) / (t1 - t0))[:, None]
        out[m] = c0 * (1 - u) + c1 * u
    return Image.fromarray(out.clip(0, 255).astype(np.uint8), "RGB")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("entrada")
    ap.add_argument("salida")
    ap.add_argument("--recorte", type=float, default=0.0)
    ap.add_argument("--contraste", type=float, default=1.15)
    ap.add_argument("--ancho", type=int, default=None)
    a = ap.parse_args()
    duotono(Image.open(a.entrada), a.recorte, a.contraste, a.ancho).save(a.salida, quality=88)
    print(f"✓ {a.salida}")


if __name__ == "__main__":
    main()
