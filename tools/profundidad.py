"""Profundidad de una foto -> capas para PARALLAX 2.5D (el acabado de documental: la foto "respira").

    python tools/profundidad.py <foto.jpg> <salida.mp4> [push|pull|izq|der|sube] [segundos]

Por qué: el Ken Burns plano (zoom a una foto) lo hace todo el mundo; separar la foto en planos de
profundidad y moverlos a velocidades distintas es lo que da el aire de documental de alto
presupuesto, y casi ningún canal faceless lo usa. El segmentador de personas de HyperFrames no
sirve para esto (medido 26-sep: 3 % de sujeto en la foto del conserje, 0 % en edificios): hace
falta un mapa de profundidad de TODA la imagen.

Modelo: Depth Anything V2 Small (ONNX, licencia Apache-2.0, onnx-community en Hugging Face), en
CPU con onnxruntime (~1-2 s por foto). Se descarga una vez a tools/.modelos/ (gitignored).

Técnica: mapeo INVERSO por píxel (cv2.remap) con un desplazamiento proporcional a la profundidad.
Se probó antes separar la foto en capas recortadas: deja huecos y bordes fantasma al moverlas;
el remap estira el fondo en vez de rasgarlo y no necesita rellenar nada.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

RAIZ = Path(__file__).resolve().parents[1]
MODELO = RAIZ / "tools" / ".modelos" / "depth-anything-v2-small.onnx"
URL = "https://huggingface.co/onnx-community/depth-anything-v2-small/resolve/main/onnx/model.onnx"
LADO = 518                                  # múltiplo de 14 (patch del ViT)
MEDIA, DESV = np.array([0.485, 0.456, 0.406]), np.array([0.229, 0.224, 0.225])
_SESION = None


def _sesion():
    global _SESION
    if _SESION is None:
        import onnxruntime as ort
        if not MODELO.exists():
            MODELO.parent.mkdir(parents=True, exist_ok=True)
            tmp = MODELO.with_suffix(".part")
            urllib.request.urlretrieve(URL, tmp)
            tmp.replace(MODELO)
        _SESION = ort.InferenceSession(str(MODELO), providers=["CPUExecutionProvider"])
    return _SESION


def mapa(img: Image.Image) -> np.ndarray:
    """Profundidad RELATIVA normalizada a [0,1] con 1 = CERCA, al tamaño de la foto."""
    s = _sesion()
    x = np.asarray(img.convert("RGB").resize((LADO, LADO), Image.BICUBIC), dtype=np.float32) / 255.0
    x = ((x - MEDIA) / DESV).transpose(2, 0, 1)[None].astype(np.float32)
    d = s.run(None, {s.get_inputs()[0].name: x})[0].squeeze()
    d = (d - d.min()) / max(float(d.max() - d.min()), 1e-6)
    return np.asarray(Image.fromarray((d * 255).astype(np.uint8)).resize(img.size, Image.BICUBIC), dtype=np.float32) / 255.0


def video_2p5d(foto: Path, destino: Path, dur: float, mov: str = "push", fps: int = 30,
               amp: float = 0.035, ancho: int = 1080, alto: int = 1920) -> dict:
    """Foto -> MP4 con movimiento 2.5D: cada píxel se desplaza según su profundidad (lo cercano
    más que lo lejano). Mapeo INVERSO con cv2.remap: sin huecos (el fondo se estira, no se rasga),
    que es lo que evita los bordes fantasma del recorte por capas. `mov` (el mismo vocabulario que
    el Ken Burns): izq/der = paneo lateral, sube = vertical, push/pull = dolly hacia dentro/fuera."""
    import subprocess
    import cv2
    img = Image.open(foto).convert("RGB")
    # encuadre 9:16 (cubrir) con margen para el movimiento
    m = 1.0 + 2.2 * amp
    esc = max(ancho * m / img.width, alto * m / img.height)
    img = img.resize((round(img.width * esc), round(img.height * esc)), Image.LANCZOS)
    iw, ih = img.size
    x0, y0 = (iw - ancho) // 2, (ih - alto) // 2
    d = mapa(img)
    d = np.asarray(Image.fromarray((d * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(3)), dtype=np.float32) / 255.0
    src = np.asarray(img)[:, :, ::-1]                      # BGR para cv2
    yy, xx = np.mgrid[0:alto, 0:ancho].astype(np.float32)
    xx += x0; yy += y0
    dd = d[y0:y0 + alto, x0:x0 + ancho]
    peso = dd - 0.35                                       # lo lejano casi quieto; lo cercano, en contra
    cx, cy = x0 + ancho / 2, y0 + alto / 2
    n = max(2, round(dur * fps))
    destino.parent.mkdir(parents=True, exist_ok=True)
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{ancho}x{alto}",
                           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                           "-pix_fmt", "yuv420p", "-g", str(fps // 2), "-movflags", "+faststart", str(destino)],
                          stdin=subprocess.PIPE)
    for i in range(n):
        u = i / (n - 1)
        u = u * u * (3 - 2 * u)                            # suave al entrar y al salir
        k = (u - 0.5) * 2                                  # -1 -> 1
        if mov in ("izq", "der"):
            s = amp * ancho * (1 if mov == "izq" else -1)
            mx, my = xx + k * s * peso, yy
        elif mov == "sube":
            mx, my = xx, yy + k * amp * alto * peso
        else:                                              # push (dolly in) / pull (out) / final
            z = amp * 2.2 * (u if mov != "pull" else 1 - u)
            f = 1.0 / (1.0 + z * (0.35 + dd))              # lo cercano crece más: sensación de avanzar
            mx, my = cx + (xx - cx) * f, cy + (yy - cy) * f
        cuadro = cv2.remap(src, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        ff.stdin.write(cuadro.tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError(f"ffmpeg falló codificando {destino}")
    return {"frames": n, "profundidad_media": round(float(dd.mean()), 3)}


def main() -> None:
    """Vista previa: python tools/profundidad.py <foto.jpg> <salida.mp4> [mov] [dur]"""
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    mov = sys.argv[3] if len(sys.argv) > 3 else "push"
    dur = float(sys.argv[4]) if len(sys.argv) > 4 else 3.0
    print(video_2p5d(Path(sys.argv[1]), Path(sys.argv[2]), dur, mov))


if __name__ == "__main__":
    main()
