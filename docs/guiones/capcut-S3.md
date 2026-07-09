# MONTAJE EN CAPCUT — Short S3 (el de la curva)

> El más barato de los cinco: la animación ya es el clímax. Objetivo: publicar hoy.
> `ref: build-wealth-short-03-stat` · `hook_type: stat` · ~30s · 1080x1920

---

## PASO 0 — Vuelve a bajar la curva (ahora sale en MP4)
Abre `docs/guiones/curva-compuesta.html` en Chrome → **9:16 · Short** → **Grabar y descargar video**.
El estado te dirá `MP4` o `WEBM`. Si dice MP4, CapCut lo importará seguro.
El archivo viejo `.webm` sirve igual si tu CapCut lo acepta; si lo rechaza, usa el MP4 nuevo.

---

## PASO 1 — Proyecto
1. CapCut → **Nuevo proyecto**.
2. Abajo a la derecha, **Relación de aspecto → 9:16**.
3. El fps se fija al exportar (paso 7). No te preocupes ahora.

---

## PASO 2 — La voz (CapCut TTS, gratis)
1. Pestaña **Texto** → **Texto predeterminado** → arrástralo a la línea de tiempo.
2. Pega el guion completo del S3 en la caja de texto:

```
Five hundred dollars a month. An S and P five hundred fund. Thirty years.

You put in a hundred and eighty thousand dollars of your own money. You walk away with about six hundred and ten thousand — and that's in today's money, after inflation.

That gap? Four hundred and thirty thousand dollars you never worked a single hour for. Your asset made it while you slept.

Could you start with fifty a month?
```

3. Con el clip de texto seleccionado, panel derecho → **Texto a voz** (Text to speech).
4. Elige una voz **masculina, grave, US**. Evita las que suenan de dibujos animados.
5. **Generar** → aparece un clip de audio en la pista de sonido.

> **Si al borrar el clip de texto desaparece el audio:** no lo borres. Ponle **opacidad 0** o
> arrástralo fuera del lienzo. El audio es lo que necesitamos; los subtítulos vienen en el paso 4.

**Escucha estas cuatro cosas** (las mismas trampas de siempre):
- "S and P" debe sonar *"es-and-pi"*. Si falla, escribe `S. and P.`
- "four hundred and thirty thousand" tiene que **pesar**. Si corre, baja la velocidad de voz.
- "while you slept" debe bajar de tono.
- Ningún número leído como cifra rara.

---

## PASO 3 — La curva (el clímax)
1. Arrastra `net-worthy-curva-compuesta-1080x1920.mp4` a la línea de tiempo, **encima** del b-roll.
2. Colócala justo donde la voz dice *"You put in a hundred and eighty thousand…"*.
3. Selecciónala → **Velocidad → Normal → 0.6x**. Pasa de 7,7s a ~12,8s: cubre toda la parte
   de los números.
4. Debe seguir en pantalla cuando la voz diga *"four hundred and thirty thousand"* — ese frame,
   con el número dorado, es el que la gente va a rebobinar.

---

## PASO 4 — Subtítulos quemados (obligatorio: el 85% ve en mute)
1. Pestaña **Texto** → **Subtítulos automáticos** → **Generar** (los saca del audio).
2. **REVISA LAS CIFRAS A MANO.** Los subtítulos automáticos SIEMPRE escriben mal
   `$609,985` y `$429,985`. Es el detalle que separa un canal serio de uno de plantilla.
3. Estilo: fuente gruesa, blanca, borde/sombra negros, centrado, tamaño grande.
4. Palabra clave en verde de marca: **`#1F9E6E`**.

---

## PASO 5 — B-roll (solo donde NO está la curva)
Descarga de **Pexels** (gratis, sin atribución) y ponlos debajo de la voz:
- `person sleeping peacefully night`  → va bajo *"while you slept"*
- `city skyline time lapse`
- `seed growing into tree timelapse`

**Corte cada 1.5–2.5s.** Nunca el mismo clip en dos frases seguidas.

---

## PASO 6 — Música
- **Pixabay Music** (licencia libre, comercial, sin atribución). Sirve en YouTube y en Facebook.
- Volumen **-18 dB** por debajo de la voz. Sube un poco cuando aparece la cifra grande.
- Evita la biblioteca de CapCut salvo lo marcado como uso comercial.

---

## PASO 7 — Exportar
- Resolución **1080x1920** · **30 fps** · calidad alta.
- **Si CapCut añade un clip final con su logo, BÓRRALO.** Delata la plantilla.
- Comprueba que el archivo **no lleva marca de agua** antes de subirlo.

---

## PASO 8 — Publicar
- **YouTube Shorts:** vertical, <60s. Título corto y con tensión.
- **Facebook Reels:** mismo archivo limpio + una línea en el texto del post
  (FB premia el texto): *"You paid $180k. You kept $610k. Here's the gap 👇"*.
- **Nunca** republiques un archivo con marca de agua de TikTok: YouTube y FB lo penalizan.
- Fija un comentario con la pregunta del cierre: *"Could you start with $50 a month?"*

---

## PASO 9 — INSTRUMENTAR (esto es lo que llena el moat)
Antes o justo después de publicar, crea `data/production_dna.json`:

```json
{
  "production_ref": "build-wealth-short-03-stat",
  "hook_type": "stat",
  "story_type": "none",
  "cta_type": "comment",
  "length_s": 30,
  "blocks": [
    {"block": "voice",  "technique": "capcut_tts",     "length_s": 0},
    {"block": "hook",   "technique": "big_number",     "length_s": 6},
    {"block": "proof",  "technique": "compound_curve", "length_s": 13},
    {"block": "cta",    "technique": "anchored_question", "length_s": 4}
  ]
}
```
```
python -m omega.cli record-dna
```

A las 48h, con Analytics (**CTR y retención como FRACCIÓN 0..1, no porcentaje**):
```
python -m omega.cli record-analytics
python -m omega.cli record-cost
python -m omega.cli record-outcome build-wealth-short-03-stat <0..1>
python -m omega.cli dna
```

> El bloque `voice` no es decorativo: si el Short #6 lleva otra voz, sus retenciones no serían
> comparables. Anotarlo en origen es lo único que mantiene el dataset honesto.
