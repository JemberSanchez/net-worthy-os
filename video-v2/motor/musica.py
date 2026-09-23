"""Base musical sintetizada (sin licencias) que sigue la FORMA del guion, no un loop.

Secciones, todas ancladas a tiempos del plan:
  gancho (0 -> 1er golpe): pad tenso + tic que acelera + subida -> golpe
  cuenta: groove a 96 bpm, La menor -> Fa -> Do -> Sol, con subida+golpe en cada golpe siguiente
  oscuro (opcional, p. ej. "the part nobody says"): cae, sin bombo, latido grave
  luz: vuelve el groove, más brillante (resuelve)
  CTA: acorde sostenido y cola hasta el final
Determinista (semilla fija). El ducking bajo la voz NO se hace aquí: lo escribe carve.mjs.
Deuda anotada (docs/V2-CALIDAD.md): una librería con licencia suena mejor que esto.
"""
from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

SR = 48000
BPM = 96
BEAT = 60 / BPM
Am, F, C, G = [57, 60, 64], [53, 57, 60], [48, 55, 64], [55, 59, 62]


def nota(midi: float) -> float:
    return 440.0 * 2 ** ((midi - 69) / 12)


class Mezcla:
    def __init__(self, dur: float, semilla: int = 7):
        self.dur, self.n = dur, int(dur * SR)
        self.t = np.arange(self.n) / SR
        self.L, self.R = np.zeros(self.n), np.zeros(self.n)
        self.rng = np.random.default_rng(semilla)

    def _env(self, t0, t1, a=0.4, r=0.6):
        t = self.t
        return np.clip((t - t0) / a, 0, 1) * np.clip((t1 - t) / r, 0, 1) * ((t >= t0) & (t <= t1))

    @staticmethod
    def _lowpass(x, fc):
        a = np.exp(-2 * np.pi * fc / SR)
        y, acc = np.empty_like(x), 0.0
        for i in range(len(x)):             # one-pole: suficiente para suavizar el pad
            acc = (1 - a) * x[i] + a * acc
            y[i] = acc
        return y

    def pad(self, acordes, vol, brillo):
        sl, sr = np.zeros(self.n), np.zeros(self.n)
        for t0, t1, notas in acordes:
            e = self._env(t0, t1, 0.35, 0.5)
            m = e > 0
            for mi in notas:
                f = nota(mi)
                for det, lado in ((-0.12, sl), (0.12, sr)):
                    ph = 2 * np.pi * f * (1 + det / 100) * self.t[m]
                    lado[m] += sum(np.sin(h * ph) / h for h in range(1, 6)) * 0.6 * e[m] / len(notas)
        self.L += self._lowpass(sl, brillo) * vol
        self.R += self._lowpass(sr, brillo) * vol

    def _pega(self, t0, s, pan=0.0):
        i0 = int(t0 * SR)
        if i0 >= self.n or i0 < 0:
            return
        s = s[: self.n - i0]
        self.L[i0:i0 + len(s)] += s * (1 - pan)
        self.R[i0:i0 + len(s)] += s * (1 + pan)

    def bombo(self, t0, vol):
        tt = np.arange(int(0.35 * SR)) / SR
        f = 50 + 90 * np.exp(-tt * 35)
        self._pega(t0, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 9) * vol)

    def tic(self, t0, vol, pan=0.0):
        s = self.rng.standard_normal(int(0.05 * SR))
        s = np.diff(np.concatenate([[0], s])) * np.exp(-np.arange(len(s)) / SR * 90) * vol
        self._pega(t0, s, pan)

    def subida(self, t0, t1, vol):
        m = (self.t >= t0) & (self.t < t1)
        if not m.any():
            return
        u = (self.t[m] - t0) / (t1 - t0)
        ruido = np.diff(np.concatenate([[0], self.rng.standard_normal(m.sum())])) * u ** 2.2 * vol
        tono = np.sin(2 * np.pi * np.cumsum(200 + 900 * u ** 2) / SR) * u ** 3 * vol * 0.35
        self.L[m] += ruido + tono
        self.R[m] += ruido + tono

    def golpe(self, t0, vol):
        self.bombo(t0, vol * 1.3)
        tt = np.arange(int(1.6 * SR)) / SR
        self._pega(t0, (np.sin(2 * np.pi * nota(33) * tt) + 0.5 * np.sin(2 * np.pi * nota(45) * tt)) * np.exp(-tt * 2.2) * vol * 0.6)

    def groove(self, a, b, prog, vol_pad, brillo, vol_bombo, vol_tic, octava_alta=False):
        acordes, x = [], a
        while x < b:
            ch = prog[int((x - a) / (4 * BEAT)) % len(prog)]
            notas = [n - 12 for n in ch] + (ch if octava_alta else [ch[0]])
            acordes.append((x, min(x + 4 * BEAT, b + 0.3), notas))
            x += 4 * BEAT
        self.pad(acordes, vol_pad, brillo)
        x = a
        while x < b - 0.1:
            self.bombo(x, vol_bombo)
            self.tic(x + BEAT / 2, vol_tic, 0.2)
            x += BEAT

    def guardar(self, ruta: Path):
        fade = np.clip(self.t / 0.05, 0, 1) * np.clip((self.dur - self.t) / 1.5, 0, 1)
        L, R = self.L * fade, self.R * fade
        pico = max(np.abs(L).max(), np.abs(R).max()) or 1.0
        st = (np.stack([L, R], axis=1) * (10 ** (-3 / 20) / pico) * 32767).astype(np.int16)
        with wave.open(str(ruta), "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes(st.tobytes())


def generar(ruta: Path, dur: float, golpes: list[float], oscuro: tuple[float, float] | None,
            cta: float | None) -> None:
    golpes = sorted(g for g in golpes if 0 < g < dur)
    g1 = golpes[0] if golpes else min(4.0, dur)
    fin_cuerpo = cta if cta else dur
    m = Mezcla(dur)
    # gancho
    m.pad([(0.0, g1 + 0.3, [45, 52, 57, 60])], 0.22, 900)
    x, k = 0.2, 0
    while x < g1:
        m.tic(x, 0.10 + 0.08 * x / g1, pan=0.3 if k % 2 else -0.3)
        x += max(0.09, 0.42 - 0.08 * x)
        k += 1
    m.subida(g1 - 1.6, g1, 0.12)
    m.golpe(g1, 0.55)
    # cuerpo: groove, con tramo oscuro opcional
    a = g1 + 0.55
    tramos = [(a, oscuro[0], "cuenta"), (oscuro[0], oscuro[1], "oscuro"), (oscuro[1], fin_cuerpo, "luz")] \
        if oscuro else [(a, fin_cuerpo, "cuenta")]
    for t0, t1, tipo in tramos:
        if t1 - t0 < 0.5:
            continue
        if tipo == "cuenta":
            m.groove(t0, t1, [Am, F, C, G], 0.20, 1400, 0.30, 0.07)
        elif tipo == "luz":
            m.groove(t0, t1, [F, C, G, Am], 0.20, 2200, 0.28, 0.08, octava_alta=True)
        else:
            m.pad([(t0, t1 + 0.3, [40, 47, 52, 55])], 0.24, 600)
            x = t0 + 0.4
            while x < t1 - 0.2:
                m.bombo(x, 0.20); m.bombo(x + 0.22, 0.12)
                x += 60 / 64
    for g in golpes[1:]:
        m.subida(g - 1.3, g, 0.10)
        m.golpe(g, 0.5)
    # CTA
    if cta:
        m.pad([(cta, dur, [48, 55, 60, 64, 67])], 0.24, 1800)
        x = cta
        while x < dur - 1.2:
            m.tic(x, 0.05)
            x += BEAT
    m.guardar(ruta)
