# SHORTS PACK 01 — 5 cortes de "Habits vs Assets"

> **Diseño experimental:** los 5 salen del MISMO material, con la MISMA voz, el MISMO estilo y la
> MISMA duración (~35s). **Solo cambia el gancho.** Es la única variable aislada, así que la
> retención de los primeros 3s mide el gancho y nada más. Eso es lo que `omega/creative/experiments.py`
> exige antes de concluir nada. Con n=1 por tipo esto es PROVISIONAL: no concluyas, acumula.

**Voz:** la tuya (Voice Design B, "el que te cuenta la verdad").
**Ajustes:** stability 40 · similarity 75 · style 20 · boost ON · speed 1.0 · Multilingual v2.
**Formato:** 1080x1920, 30 fps, subtítulos quemados, corte cada 1.5–2.5s.
**Cifras verificadas:** $609,985 final · $180,000 aportado · gap $429,985 · café: $18,250 ahorrado vs $26,323 invertido.

---

## S1 · GANCHO DE HISTORIA  → `hook_type: story`
`ref: build-wealth-short-01-story`

**Voz (pegar en ElevenLabs):**
```
Two men. Same job. Same salary. Thirty years later, one retires with almost nothing. The other retires with over a million dollars. Same money in. So what did the millionaire do?

He didn't budget harder. He didn't wake up at five in the morning. He bought assets.

A habit moves money you already have. An asset makes money while you sleep.

Which one are you right now? Tell me below.
```
**Texto en pantalla:** `SAME SALARY.` → `OPPOSITE ENDING.` → `$0 vs $1,000,000+` → `WHICH ONE ARE YOU?`
**Pexels:** `two businessmen walking opposite directions` · `crossroads silhouette` · `empty wallet` · `luxury home sunset` · `stock chart rising`

---

## S2 · GANCHO CONTRARIAN  → `hook_type: contrarian`
`ref: build-wealth-short-02-contrarian`

**Voz:**
```
Skip the coffee. Wake up at five in the morning. Budget every dollar. You've done it all — and you're still broke.

Here's why: habits don't build wealth. Assets do.

A habit only moves money you already have from one pocket to another. It never makes money. Discipline is fuel. Fuel with no engine goes nowhere.

Could you do fifty a month? Comment below.
```
**Texto en pantalla:** `HABITS WON'T MAKE YOU RICH` → `HABITS ❌  ASSETS ✅` → `FUEL ≠ ENGINE`
**Pexels:** `alarm clock 5am dark bedroom` · `hands typing budget spreadsheet` · `pouring coffee slow motion` · `car engine turning` · `person on phone banking app`

---

## S3 · GANCHO DE CIFRA (usa la curva)  → `hook_type: stat`
`ref: build-wealth-short-03-stat`

**Voz:**
```
Five hundred dollars a month. An S and P five hundred fund. Thirty years.

You put in a hundred and eighty thousand dollars of your own money. You walk away with about six hundred and ten thousand — and that's in today's money, after inflation.

That gap? Four hundred and thirty thousand dollars you never worked a single hour for. Your asset made it while you slept.

Could you start with fifty a month?
```
**Visual central:** `net-worthy-curva-compuesta-1080x1920.webm` (ralentízalo a 0.6x para que dure ~12s).
**Pexels:** `person sleeping peacefully night` · `city skyline time lapse` · `seed growing into tree timelapse`
> Este es el Short más barato de montar: la curva ya ES el vídeo. Empieza por este si vas justo de tiempo.

---

## S4 · GANCHO DE ADVERTENCIA  → `hook_type: shock`
`ref: build-wealth-short-04-trap`

**Voz:**
```
There's a trap, and it catches smart people the hardest. It's spending that feels like investing.

The upgraded car you needed for work. The three hundred dollar course you never finished. The gadget that was going to make you rich.

They feel like progress. But an asset puts money into your pocket. A liability quietly takes it out — wearing the costume of an investment.

So ask one question before you buy: does this pay me back, or do I pay for it forever?

If you can't answer that in one sentence, it's not an asset. It's a bill with better marketing.
```
**Texto en pantalla:** `SPENDING THAT FEELS LIKE INVESTING` → `ASSET → $ IN` / `LIABILITY → $ OUT` → `A BILL WITH BETTER MARKETING`
**Pexels:** `new car dealership` · `online course laptop` · `unboxing gadget` · `money flying out of wallet` · `person thinking doubt`

---

## S5 · GANCHO DE PREGUNTA (el café)  → `hook_type: question`
`ref: build-wealth-short-05-coffee`

**Voz:**
```
Is your five dollar coffee really why you're broke?

They were half right. And the half they got wrong is the reason you're still stuck.

Skip that coffee for ten years and you've saved about eighteen thousand dollars. Put the same five dollars into an asset instead, and you have about twenty-six thousand.

The habit saved the eighteen. The asset made the other eight — while you slept.

The coffee was never the point. Where the money goes is.
```
**Texto en pantalla:** `IS YOUR COFFEE THE PROBLEM?` → `SAVED: $18,250` / `INVESTED: $26,323` → `THE COFFEE WAS NEVER THE POINT`
**Pexels:** `coffee cup close up` · `coins stacking` · `two stacks of coins comparison` · `hands holding phone investing app`
> El gancho ES la corrección de un error que casi cometemos nosotros. Honestidad = confianza.

---

## MONTAJE EN CAPCUT (idéntico en los 5)
1. Proyecto **9:16, 30 fps**. Importa el MP3 de la voz.
2. B-roll de Pexels detrás. **Corte cada 1.5–2.5s.** Nunca el mismo clip dos frases seguidas.
3. **Subtítulos automáticos** → revisa las cifras a mano (siempre las escribe mal) → palabra clave en `#1F9E6E`.
4. Texto de gancho en el **frame 1**, con golpe de sonido (whoosh + bass).
5. Música de la YouTube Audio Library, **-18 dB** bajo la voz. Sube en la cifra grande.
6. **BORRA el clip final de logo que CapCut añade solo.** Delata la plantilla.
7. Exporta 1080x1920, 30 fps, sin marca de agua.

## PUBLICACIÓN
- **Uno al día**, cinco días. No los sueltes todos de golpe: no aprendes nada y parece spam.
- Sube el **archivo limpio** a cada red. Nunca republiques con la marca de agua de TikTok — YouTube y FB lo penalizan.
- **Facebook** premia el texto del post: añade una línea ("Same salary. Opposite ending. 👇").
- Fija el comentario con la pregunta del Short (genera respuestas = alcance).

## INSTRUMENTAR (esto es lo que llena el moat)
Antes de publicar cada uno:
```
python -m omega.cli record-dna        # con su ref y su hook_type
```
Después, con datos de Analytics (CTR/retención como FRACCIÓN 0..1, no %):
```
python -m omega.cli record-analytics
python -m omega.cli record-cost
python -m omega.cli record-outcome <ref> <0..1>
python -m omega.cli dna
```
> Al quinto Short tendrás 5 ganchos medidos con todo lo demás constante. Ahí `dna` empieza a
> decir algo — todavía PROVISIONAL (n=1 por tipo), pero es la primera señal real del sistema.
