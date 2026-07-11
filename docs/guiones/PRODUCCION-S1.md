# PRODUCCIÓN S1 — runbook para montar y publicar HOY

> Short: `build-wealth-short-01-story` · gancho **story** · escena de dos columnas (SPENT vs OWNED).
> Todo lo de abajo está verificado contra el motor real (2026-07-10). El renderizador tiene un
> **checklist que se marca solo**: si un paso no se marca, no avances.

---

## Paso 1 — La voz (CapCut TTS, ~5 min)

1. CapCut → texto a voz → voz **"Firme Pilot"** (la MISMA del S3: si cambias la voz, rompes la
   comparabilidad del experimento).
2. Pega EXACTAMENTE este guion — **494 caracteres, entra en UN bloque** (CapCut tope 500).
   (También está en `shorts-pack-01.md`.) Son frases completas para que el TTS no suene robótico.

```
Two men earn the same salary and work just as hard. Thirty years later, one has almost nothing while the other has over a million, on the same money in. So what changed? One spent his paycheck, and the other owned things that paid him back. His habits never failed him. A habit only moves money you already have, but an asset earns while you sleep. You already have the hard part; the only question is where you point it. So does your next hundred dollars leave, or does it work? Tell me below.
```
> **Escrito para el OÍDO.** El TTS lee los fragmentos ("Two men. Same salary.") a tirones, robótico.
> Estas son frases completas que fluyen. La PORTADA en pantalla sigue siendo punchy (`TWO MEN` /
> `SAME SALARY`) — es la voz la que fluye, no el texto. Si un guion pasa de 500, pártelo en 2 bloques
> de texto en CapCut y exporta el audio junto.

**Voz robótica, plan B:** si aun así la voz "Firme Pilot" te suena a robot, prueba otra voz de CapCut
más natural en el mismo panel de TTS. Cambiar de voz rompe la comparabilidad con el S3 (anótalo en el
ADN como `{"block":"voice","technique":"capcut_tts_<voz>"}`), pero una voz que engancha vale más que
la comparabilidad de un experimento con n=1.

3. Exporta **solo el audio** a MP3 y guárdalo como **`data/voz-short-01.mp3`** (ese nombre exacto:
   el botón "🎙 Usar la voz del proyecto" lo busca ahí).

## Paso 2 — Renderizar (~10 min)

1. Servidor: `python -m http.server 8765` desde la raíz del repo (o ya está en `.claude/launch.json`).
2. Abre `http://localhost:8765/docs/guiones/short-renderer.html`.
3. Selector de arriba → **"S1 · story"**.
4. **"🎙 Usar la voz del proyecto (voz-short-01.mp3)"** → se calibra solo contra el guion
   (el status dice cuántos bloques de voz encontró y dónde puso los cortes).
5. **▶ Previsualizar ENTERO** y verifica estos 4 momentos:
   - **Arranque:** "SAME SALARY", las dos barras suben IGUALES, monedas bajando por las DOS ramas.
   - **Divergencia:** "OPPOSITE ENDING" + YEAR corriendo; la izquierda se drena (gotea),
     la derecha crece con chispas; el número CUENTA hacia el millón.
   - **Aterrizaje:** el `$1,000,000+` debe caer **justo cuando la voz dice "over a million"**.
     Si no cuadra, mueve el slider **"La cifra grande aterriza (draw)"** con "ver reloj" activado.
   - **Cierre:** subtítulos en la zona izquierda durante la parte de "his habits didn't fail him",
     y el CTA "YOUR NEXT $100: LEAVE OR WORK?" al final.
6. Activa una vez **"ver zonas seguras"**: nada importante puede caer en el rojo. Desactívala.

## Paso 3 — Exportar

- **⏺ Grabar y descargar el Short** → `net-worthy-build-wealth-short-01-story-1080x1920.mp4`
  (H.264+AAC, 30 fps exactos; tarda ~1 min y puedes cambiar de pestaña).
- **⬇ Frame final** → PNG del clímax: portada para Facebook y miniatura.

## Paso 4 — Subir (YouTube Shorts + Facebook Reels)

**Hora:** elige una franja con EEUU despierto (p. ej. **13:00–15:00 hora local**, somos UTC-5 = tarde
del Este) y **repite ESA MISMA hora con S2, S4 y S5**: la hora fija es lo que aísla el gancho como
única variable. (El S3 salió a las 02:00 — confounder ya anotado; no repetir.)

**Título (ambas plataformas):**
```
Same Salary. Opposite Ending.
```
**Descripción:**
```
Two men. Same paycheck, same discipline — one retires with almost nothing, the other with over $1,000,000. The only difference: where the money pointed. Illustrative example, not financial advice. Investing involves risk of loss.

#shorts #personalfinance #investing #wealth #money
```

## Paso 5 — ANOTAR (mismo día; sin esto el video no existe para el sistema)

⚠ **No toques `data/production_dna.json` ni `data/production_cost.json`**: los archivos por defecto
están reservados para la medición del S3 el sábado. El S1 usa archivos propios con argumento explícito.

1. Crea **`data/production_dna-short-01.json`** (misma estructura que el del S3). Los `length_s` de
   hook/diverge/principle/cta salen de los cortes que te dio el status al calibrar
   (hook = corte intro; diverge = draw − hook; principle = CTA − curve…; redondea a enteros):

```json
{
  "production_ref": "build-wealth-short-01-story",
  "hook_type": "story",
  "story_type": "character",
  "cta_type": "comment",
  "length_s": 31,
  "blocks": [
    {"block": "voice",     "technique": "capcut_tts_firme_pilot",          "length_s": 0},
    {"block": "visuals",   "technique": "canvas_renderer_columns_scene",   "length_s": 0},
    {"block": "captions",  "technique": "burned_calibrated_rms",           "length_s": 0},
    {"block": "hook",      "technique": "two_men_same_salary",             "length_s": 3},
    {"block": "diverge",   "technique": "bars_split_year_ticker_counter",  "length_s": 6},
    {"block": "principle", "technique": "spent_vs_owned_no_shame",         "length_s": 15},
    {"block": "cta",       "technique": "your_next_100_leave_or_work",     "length_s": 4}
  ]
}
```

2. Crea **`data/production_cost-short-01.json`** con tus horas REALES:

```json
{
  "production_ref": "build-wealth-short-01-story",
  "research_hours": 0,
  "script_hours": 0.2,
  "edit_hours": 0.5,
  "ai_cost_usd": 0,
  "time_to_publish_h": 1
}
```

3. Registra (nota el argumento de archivo explícito):

```
python -m omega.cli record-dna  data/production_dna-short-01.json
python -m omega.cli record-cost data/production_cost-short-01.json
```

4. Dime la hora exacta de publicación y las URLs y anoto el contexto (como se hizo con el S3).

## Recordatorio — SÁBADO 12 (el S3, lo único que de verdad importa)

Con YouTube Studio y Facebook abiertos:
```
python -m omega.cli record-analytics      # fracciones 0..1, NUNCA porcentajes
python -m omega.cli record-cost
python -m omega.cli record-outcome build-wealth-short-03-stat <0..1>
python -m omega.cli dna
```
