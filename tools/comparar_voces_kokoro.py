"""Genera la misma frase con varias voces de Kokoro y mide su tono medio (Hz) por autocorrelación.
Comparativo, no absoluto: sirve para ORDENAR las voces de mas grave a mas aguda, medido, no a ojo."""
import numpy as np
import soundfile as sf
from kokoro import KPipeline

TEXTO = "He pumped gas and cleaned floors his whole life. He died with eight million dollars."
VOCES = ["am_michael", "am_onyx", "am_fenrir", "am_adam", "am_echo", "bm_george", "bm_daniel"]

def f0_medio(audio: np.ndarray, sr: int) -> float:
    """F0 medio por autocorrelación en ventanas de 40ms, rango vocal masculino 70-260Hz."""
    win = int(sr * 0.04)
    lo, hi = int(sr / 260), int(sr / 70)
    f0s = []
    for i in range(0, len(audio) - win, win // 2):
        frame = audio[i:i+win]
        if np.abs(frame).mean() < 0.01:
            continue
        frame = frame - frame.mean()
        corr = np.correlate(frame, frame, mode="full")[len(frame)-1:]
        if len(corr) <= hi:
            continue
        seg = corr[lo:hi]
        if len(seg) == 0 or corr[0] <= 0:
            continue
        pico = seg.argmax() + lo
        if corr[pico] / corr[0] > 0.3:
            f0s.append(sr / pico)
    return float(np.median(f0s)) if f0s else -1.0

pipe = KPipeline(lang_code="a")
resultados = []
for voz in VOCES:
    audio_total = []
    for _, _, audio in pipe(TEXTO, voice=voz):
        audio_total.append(audio)
    audio_np = np.concatenate(audio_total)
    sr = 24000
    destino = f"muestra-{voz}.wav"
    sf.write(destino, audio_np, sr)
    f0 = f0_medio(audio_np, sr)
    resultados.append((voz, f0, len(audio_np)/sr))
    print(f"{voz:12s}  F0 medio: {f0:6.1f} Hz  ({len(audio_np)/sr:.1f}s)  -> {destino}")

print()
print("De mas grave a mas aguda:")
for voz, f0, dur in sorted(resultados, key=lambda x: x[1]):
    print(f"  {voz:12s}  {f0:.0f} Hz")
