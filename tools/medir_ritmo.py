"""Mide el RITMO VISUAL de un MP4: el tramo más largo en que el cuadro no muestra nada nuevo.

    python tools/medir_ritmo.py data/net-worthy-read-janitor.mp4 [--max 2.5]

Por qué existe
---------------
La hipótesis `pacing_2_3s` (ver docs/ESTADO.md, 31-jul) dice que un Short necesita un cambio
visual cada <=2-3 s para no perder al espectador entre los 3 y los 20 s. `analizar_video.py`
cuenta CORTES de plano con PySceneDetect, pero no sirve para medir esto: un barrido con
desenfoque sobre el mismo fondo, un contador que corre o una columna que crece son cambios
visuales reales y NO son cortes. Validado el 23-sep: PySceneDetect vio 1 corte en la PoC v3,
que no tiene ni un solo tramo quieto de más de 0,8 s.

Qué mide
--------
Muestrea el vídeo a 5 fps, lo desenfoca y lo reduce a 34x60 (así el grano, el ruido de
compresión y el texto pequeño no cuentan) y compara cada frame con el de 0,6 s antes. Si la
diferencia media es < 2/255, en ese instante no apareció nada nuevo. Devuelve el tramo quieto
más largo y el % del vídeo que está quieto.

Validación del instrumento (23-sep, PoC de Ronald Read):
- Ruido de fondo del grano animado de la v3: 0,48, muy por debajo del umbral de 2,0.
- Motor canvas viejo (read-janitor, frames de drawFrame con el reloj demo, sin voz): 90 % del
  tiempo quieto, tramo máximo de 6,0 s. v3 HyperFrames (MP4 exportado): 4 % y 0,8 s.
  Coincide con lo que se ve a ojo, así que la métrica separa lo que tiene que separar.

Qué NO hace
-----------
No dice si el cambio es BUENO: una animación ruidosa sin sentido también "pasa". Es una puerta
mínima (no dejar el cuadro muerto), no un juicio de calidad.
"""
from __future__ import annotations

import argparse
import sys

import numpy as np

FPS_MUESTREO = 5
LAG_S = 0.6
UMBRAL = 2.0          # diferencia media (0..255) por debajo de la cual "no pasó nada"
TAMANO = (34, 60)     # ancho, alto: lo bastante chico para ignorar grano y texto pequeño


def tramo_quieto(frames: list[np.ndarray], fps: float = FPS_MUESTREO, lag_s: float = LAG_S,
                 umbral: float = UMBRAL) -> dict:
    """Frames en gris ya reducidos -> {'max_s', 'desde_s', 'pct_quieto', 'cambio_medio'}.

    Función pura (sin vídeo ni OpenCV) para poder testearla con arrays sintéticos.
    """
    lag = max(1, round(lag_s * fps))
    if len(frames) <= lag:
        return {"max_s": 0.0, "desde_s": 0.0, "pct_quieto": 0.0, "cambio_medio": 0.0}
    d = np.array([np.mean(np.abs(frames[i].astype(float) - frames[i - lag].astype(float)))
                  for i in range(lag, len(frames))])
    quieto = d < umbral
    mejor = racha = 0
    fin_mejor = 0
    for i, q in enumerate(quieto):
        racha = racha + 1 if q else 0
        if racha > mejor:
            mejor, fin_mejor = racha, i
    # `mejor` comparaciones quietas seguidas (frame i contra i+lag) = mejor + lag frames sin cambio
    desde = (fin_mejor - mejor + 1) / fps if mejor else 0.0
    dur = (mejor + lag) / fps if mejor else 0.0
    return {"max_s": round(dur, 2), "desde_s": round(desde, 2),
            "pct_quieto": round(float(quieto.mean()) * 100, 1), "cambio_medio": round(float(d.mean()), 2)}


def leer_frames(ruta: str) -> list[np.ndarray]:
    import cv2
    cap = cv2.VideoCapture(ruta)
    if not cap.isOpened():
        raise SystemExit(f"No pude abrir {ruta}")
    fps_video = cap.get(cv2.CAP_PROP_FPS) or 30.0
    paso = max(1, round(fps_video / FPS_MUESTREO))
    frames, i = [], 0
    while True:
        ok, fr = cap.read()
        if not ok:
            break
        if i % paso == 0:
            g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
            g = cv2.GaussianBlur(g, (0, 0), sigmaX=g.shape[1] / 270 * 4)  # ~4 px a 270 de ancho
            frames.append(cv2.resize(g, TAMANO, interpolation=cv2.INTER_AREA))
        i += 1
    cap.release()
    return frames


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("mp4")
    ap.add_argument("--max", type=float, default=2.5, help="tramo quieto máximo tolerado (s)")
    a = ap.parse_args()
    r = tramo_quieto(leer_frames(a.mp4))
    print(f"Tramo quieto más largo : {r['max_s']:.1f} s (desde t≈{r['desde_s']:.1f} s)   "
          f"objetivo <= {a.max:.1f} s")
    print(f"Tiempo quieto          : {r['pct_quieto']:.0f} %   cambio medio/{LAG_S}s = {r['cambio_medio']:.1f}")
    if r["max_s"] > a.max:
        print(f"✗ Hay {r['max_s']:.1f} s sin nada nuevo en pantalla: ahí es donde se va la gente.")
        return 1
    print("✓ El cuadro nunca se queda muerto más de lo tolerado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
