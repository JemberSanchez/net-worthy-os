"""Analizador de vídeo: encuentra saltos de movimiento SIN depender de mi criterio.

    python tools/analizar_video.py data/net-worthy-read-janitor.mp4

Por qué existe
---------------
Hasta ahora "verificar el vídeo" significaba: yo escribía mis propias métricas (cajas de texto,
deltas de matriz de cámara, brillo medio) y las corría sobre EL MISMO MODELO (`drawFrame`) que
generó el vídeo — así que un bug de concepto en el motor podía colarse sin que ninguna métrica lo
viera, porque la métrica y el bug salían del mismo sitio. Y varias de esas métricas caseras dieron
falsos positivos (ver docs/ESTADO.md, "validar el instrumento").

Esto es distinto: analiza el **archivo MP4 ya exportado**, con dos librerías estándar de visión por
computador, ninguna de las dos escrita por mí:

1. **PySceneDetect** (`ContentDetector`) — el algoritmo que usan los editores de vídeo para detectar
   cortes de plano. Si aquí aparece un corte que el guion NO planeó, es una señal real de que algo
   se ve como un corte cuando no debería.
2. **Optical flow** (OpenCV, Farneback) — mide cuánto se MUEVE la imagen entre cada dos frames.
   Un salto brusco de movimiento (un pico que no tienen sus vecinos) es exactamente lo que un ojo
   humano lee como "tirón" o "artificial", sin necesidad de que yo sepa de antemano dónde mirar.

Qué NO hace
-----------
No sustituye ver el vídeo. Dice DÓNDE mirar con más probabilidad de encontrar algo, no si se ve
bien — eso último lo decide un ojo humano o, como mucho, mi inspección visual del frame señalado.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np


def analizar(ruta: str, *, muestra_cada: int = 1, umbral_z: float = 3.0) -> None:
    cap = cv2.VideoCapture(ruta)
    if not cap.isOpened():
        raise SystemExit(f"No pude abrir {ruta}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    n_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"Archivo : {ruta}")
    print(f"FPS     : {fps:.2f}  ·  Frames: {n_frames}  ·  Duración: {n_frames/fps:.2f}s\n")

    # ── 1. CORTES DE PLANO (PySceneDetect) ──────────────────────────────────────────────────
    from scenedetect import detect, ContentDetector
    escenas = detect(ruta, ContentDetector(threshold=27.0))
    # PySceneDetect 0.7.1 devuelve [] (no 1 escena cubriendo todo el vídeo) cuando NO hay ningún
    # corte -- versiones viejas sí devolvían esa "escena única". max(0, ...) evita el -1 en ese caso.
    n_cortes = max(0, len(escenas) - 1)
    print(f"=== Cortes de plano detectados: {n_cortes} ===")
    for i in range(n_cortes):
        print(f"  corte en {escenas[i][1].seconds:6.2f}s")
    print()

    # ── 2. MOVIMIENTO BRUSCO (optical flow, downsampleado para que sea rápido) ─────────────
    # ⚠ PROBADO Y DESCARTADO COMO SEÑAL AUTOMÁTICA (2026-07-28): tanto en el frame completo como
    # enmascarando el centro, esto genera MUCHO ruido en este tipo de contenido — un fondo casi
    # quieto interrumpido por texto/contadores de alto contraste (un número que pasa de "$432,844"
    # a "$1,517,725" cambia de ANCHO cada frame y eso solo ya dispara el motion-energy, sin que la
    # cámara se haya movido). Enmascarar el centro tampoco lo arregla: la escena snowball tiene su
    # contenido legítimo (bola + pendiente) cruzando el cuadro de esquina a esquina.
    # Se deja como AYUDA PARA MIRAR, no como veredicto automático: úsalo para encontrar candidatos
    # y luego decide a ojo (extrae el frame con drawFrame(t) y compáralo con los vecinos). El
    # corte de plano (arriba, ContentDetector) SÍ es fiable como señal automática — está validado
    # contra una librería de terceros, no contra un umbral que yo mismo elegí sin calibrar.
    W_PEQUENO = 160
    prev_gray = None
    energia: list[float] = []
    t_seg: list[float] = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % muestra_cada == 0:
            h, w = frame.shape[:2]
            peq = cv2.resize(frame, (W_PEQUENO, int(h * W_PEQUENO / w)))
            gray = cv2.cvtColor(peq, cv2.COLOR_BGR2GRAY)
            if prev_gray is not None:
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, gray, None, 0.5, 2, 12, 2, 5, 1.1, 0)
                mag = float(np.sqrt(flow[..., 0]**2 + flow[..., 1]**2).mean())
                energia.append(mag)
                t_seg.append(idx / fps)
            prev_gray = gray
        idx += 1
    cap.release()

    energia_a = np.array(energia)
    mediana = float(np.median(energia_a))
    mad = float(np.median(np.abs(energia_a - mediana))) or 1e-6
    z = (energia_a - mediana) / (mad * 1.4826)   # z-score robusto (MAD, no afectado por outliers)

    # un salto = z alto Y mucho más que el frame inmediatamente anterior (no una escena ya movida)
    saltos = []
    for i in range(1, len(z)):
        if z[i] > umbral_z and energia_a[i] > energia_a[i-1] * 1.8:
            saltos.append((t_seg[i], energia_a[i], z[i]))

    print(f"=== Candidatos por movimiento: mediana={mediana:.2f}  |  {len(saltos)} sobre z={umbral_z} ===")
    print("⚠ RUIDOSO en vídeos con contadores/texto animado (ver comentario arriba): un número que")
    print("  cambia de ancho dispara esto igual que un tirón de cámara. Úsalo para ELEGIR dónde")
    print("  mirar, no como veredicto — confirma cada candidato viendo el frame.")
    for t, e, zz in sorted(saltos, key=lambda x: -x[2])[:12]:
        print(f"  t={t:6.2f}s   energía={e:6.2f} (mediana {mediana:.2f})   z={zz:.1f}")
    if not saltos:
        print("  Ninguno.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    analizar(sys.argv[1])
