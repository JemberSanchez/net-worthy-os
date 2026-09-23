"""Base musical sintetizada del Short (sin licencias): sigue la FORMA del guion, no un loop.

    python gen_musica.py            # -> assets/music-bed.wav (48 kHz estéreo)

Secciones ancladas a los tiempos MEDIDOS de la voz (assets/words.json):
  gancho (0 -> "dollars" del intro): pad tenso + tic que acelera + subida -> golpe
  cuenta (thesis/proof/payoff): groove a 96 bpm, La menor -> Fa -> Do -> Sol
  "the part nobody says" (honesty): cae a oscuro, sin bombo, latido grave
  lesson: vuelve el groove, más brillante (resuelve)
  CTA: acorde sostenido y cola hasta el final
Determinista (semilla fija). El ducking bajo la voz NO se hace aquí: lo escribe carve.mjs en el HTML.
"""
from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np

SR = 48000
AQUI = Path(__file__).resolve().parent
rng = np.random.default_rng(7)


def palabra(i: int) -> float:
    return WORDS[i]["start"]


WORDS = json.loads((AQUI / "assets" / "words.json").read_text())
DUR = 49.8
T_GOLPE1 = palabra(14)          # "dollars." del gancho
T_CUENTA_FIN = palabra(50)      # "eight" (million) de proof: aterriza la cuenta
T_OSCURO = palabra(75) - 0.25   # "Now the part nobody says"
T_LUZ = palabra(119) - 0.1      # "You don't need..."
T_CTA = palabra(143) - 0.1      # "So, skill..."
BPM = 96
BEAT = 60 / BPM

n = int(DUR * SR)
t = np.arange(n) / SR
L = np.zeros(n)
R = np.zeros(n)


def nota(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


def env(t0: float, t1: float, a: float = 0.4, r: float = 0.6) -> np.ndarray:
    e = np.clip((t - t0) / a, 0, 1) * np.clip((t1 - t) / r, 0, 1)
    return e * ((t >= t0) & (t <= t1))


def lowpass(x: np.ndarray, fc: float) -> np.ndarray:
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(0, len(x)):         # one-pole: suficiente para suavizar el pad
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def pad(acordes: list[tuple[float, float, list[int]]], vol: float, brillo: float) -> None:
    """acordes: (t0, t1, notas midi). Sierra suave desafinada en estéreo + lowpass."""
    sig_l = np.zeros(n)
    sig_r = np.zeros(n)
    for t0, t1, notas in acordes:
        e = env(t0, t1, 0.35, 0.5)
        m = e > 0
        for k, mi in enumerate(notas):
            f = nota(mi)
            for det, lado in ((-0.12, sig_l), (0.12, sig_r)):
                ph = 2 * np.pi * f * (1 + det / 100) * t[m]
                onda = sum(np.sin(h * ph) / h for h in range(1, 6)) * 0.6
                lado[m] += onda * e[m] / len(notas)
    L[:] += lowpass(sig_l, brillo) * vol
    R[:] += lowpass(sig_r, brillo) * vol


def bombo(t0: float, vol: float) -> None:
    i0, d = int(t0 * SR), int(0.35 * SR)
    if i0 >= n:
        return
    tt = np.arange(min(d, n - i0)) / SR
    f = 50 + 90 * np.exp(-tt * 35)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9) * vol
    L[i0:i0 + len(s)] += s
    R[i0:i0 + len(s)] += s


def tic(t0: float, vol: float, pan: float = 0.0) -> None:
    i0, d = int(t0 * SR), int(0.05 * SR)
    if i0 >= n:
        return
    s = rng.standard_normal(min(d, n - i0))
    s = np.diff(np.concatenate([[0], s])) * np.exp(-np.arange(len(s)) / SR * 90) * vol
    L[i0:i0 + len(s)] += s * (1 - pan)
    R[i0:i0 + len(s)] += s * (1 + pan)


def subida(t0: float, t1: float, vol: float) -> None:
    m = (t >= t0) & (t < t1)
    u = (t[m] - t0) / (t1 - t0)
    ruido = rng.standard_normal(m.sum())
    ruido = np.diff(np.concatenate([[0], ruido])) * u ** 2.2 * vol
    tono = np.sin(2 * np.pi * np.cumsum(200 + 900 * u ** 2) / SR) * u ** 3 * vol * 0.35
    L[m] += ruido + tono
    R[m] += ruido + tono


def golpe(t0: float, vol: float) -> None:
    bombo(t0, vol * 1.3)
    i0, d = int(t0 * SR), int(1.6 * SR)
    tt = np.arange(min(d, n - i0)) / SR
    s = (np.sin(2 * np.pi * nota(33) * tt) + 0.5 * np.sin(2 * np.pi * nota(45) * tt)) * np.exp(-tt * 2.2) * vol * 0.6
    L[i0:i0 + len(s)] += s
    R[i0:i0 + len(s)] += s


Am, F, C, G, Dm, E = [57, 60, 64], [53, 57, 60], [48, 55, 64], [55, 59, 62], [50, 57, 62], [52, 56, 59]

# ── gancho: pad tenso + tic que acelera + subida al golpe ─────────────────────────────────────
pad([(0.0, T_GOLPE1 + 0.3, [45, 52, 57, 60])], 0.22, 900)
k, tt0 = 0, 0.2
while tt0 < T_GOLPE1:
    tic(tt0, 0.10 + 0.08 * tt0 / T_GOLPE1, pan=0.3 if k % 2 else -0.3)
    tt0 += max(0.09, 0.42 - 0.08 * tt0)
    k += 1
subida(T_GOLPE1 - 1.6, T_GOLPE1, 0.12)
golpe(T_GOLPE1, 0.55)

# ── cuenta: groove 96 bpm hasta lo oscuro ────────────────────────────────────────────────────
inicio = T_GOLPE1 + 0.55
prog = [Am, F, C, G]
acordes, b = [], inicio
while b < T_OSCURO:
    ch = prog[int((b - inicio) / (4 * BEAT)) % 4]
    acordes.append((b, min(b + 4 * BEAT, T_OSCURO + 0.3), [x - 12 for x in ch] + [ch[0]]))
    b += 4 * BEAT
pad(acordes, 0.20, 1400)
b = inicio
while b < T_OSCURO - 0.1:
    bombo(b, 0.30)
    tic(b + BEAT / 2, 0.07, 0.2)
    b += BEAT
subida(T_CUENTA_FIN - 1.3, T_CUENTA_FIN, 0.10)
golpe(T_CUENTA_FIN, 0.5)

# ── lo que nadie dice: oscuro, sin bombo, latido ─────────────────────────────────────────────
pad([(T_OSCURO, T_LUZ + 0.3, [40, 47, 52, 55])], 0.24, 600)
b = T_OSCURO + 0.4
while b < T_LUZ - 0.2:
    bombo(b, 0.20)
    bombo(b + 0.22, 0.12)
    b += 60 / 64

# ── lección: vuelve el groove, más brillante ────────────────────────────────────────────────
prog2 = [F, C, G, Am]
acordes, b = [], T_LUZ
while b < T_CTA:
    ch = prog2[int((b - T_LUZ) / (4 * BEAT)) % 4]
    acordes.append((b, min(b + 4 * BEAT, T_CTA + 0.3), [x - 12 for x in ch] + ch))
    b += 4 * BEAT
pad(acordes, 0.20, 2200)
b = T_LUZ
while b < T_CTA - 0.1:
    bombo(b, 0.28)
    tic(b + BEAT / 2, 0.08, -0.2)
    b += BEAT

# ── CTA: acorde sostenido, cola ───────────────────────────────────────────────────────────────
pad([(T_CTA, DUR, [48, 55, 60, 64, 67])], 0.24, 1800)
b = T_CTA
while b < DUR - 1.2:
    tic(b, 0.05)
    b += BEAT

# fundidos de borde y normalización de pico a -3 dBFS (el loudnorm final va sobre la mezcla)
fade = np.clip(t / 0.05, 0, 1) * np.clip((DUR - t) / 1.5, 0, 1)
L *= fade
R *= fade
pico = max(np.abs(L).max(), np.abs(R).max())
g = 10 ** (-3 / 20) / pico
st = (np.stack([L, R], axis=1) * g * 32767).astype(np.int16)
with wave.open(str(AQUI / "assets" / "music-bed.wav"), "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(st.tobytes())
print(f"✓ music-bed.wav {DUR}s  golpes en {T_GOLPE1:.2f}s y {T_CUENTA_FIN:.2f}s  oscuro {T_OSCURO:.2f}-{T_LUZ:.2f}s")
