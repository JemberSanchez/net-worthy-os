# SHORTS PACK 01 — 5 cortes de "Habits vs Assets"

> **Diseño experimental:** los 5 salen del MISMO material, con la MISMA voz, el MISMO estilo y la
> MISMA duración (~35s). **Solo cambia el gancho.** Es la única variable aislada, así que la
> retención de los primeros 3s mide el gancho y nada más. Eso es lo que `omega/creative/experiments.py`
> exige antes de concluir nada. Con n=1 por tipo esto es PROVISIONAL: no concluyas, acumula.

**Formato:** 1080x1920, 30 fps, subtítulos quemados, corte cada 1.5–2.5s.
**Cifras verificadas:** $609,985 final · $180,000 aportado · gap $429,985 · café: $18,250 ahorrado vs $26,323 invertido.

### VOZ — opciones gratis CON derechos comerciales (verificado 2026-07-09)
| Opción | Comercial gratis | Calidad | Fricción |
|---|---|---|---|
| **CapCut TTS** | Sí (según CapCut; no verificado en el ToS) | Decente, suena genérica | Cero |
| **Google Cloud TTS** | **Sí** — el free tier es promoción de facturación, misma licencia | Muy buena | Cuenta + tarjeta |
| **Kokoro-82M** | Sí (Apache 2.0) | Buena, #1 TTS Arena | Instalación local |
| ~~Azure Speech F0~~ | **NO** — "evaluación y pruebas" | — | — |
| ~~ElevenLabs Free~~ | **NO** — sin licencia comercial | — | — |

Google: 1M chars/mes gratis (WaveNet) · 4M (Standard). Un Short = ~700 chars.
Meta final: ElevenLabs Starter ($5) + la voz de Voice Design B ("el que te cuenta la verdad"),
ajustes stability 40 · similarity 75 · style 20 · boost ON · speed 1.0 · Multilingual v2.

### ⚠️ ANOTA EL MOTOR DE VOZ O EL MOAT NACE CONTAMINADO
Si los 5 Shorts salen con una voz y el #6 con otra, **sus retenciones no son comparables**.
No hace falta tocar el motor: `production_dna.blocks` es JSON libre. Añade siempre un bloque:
```json
{"block": "voice", "technique": "capcut_tts", "length_s": 0}
```
(o `google_wavenet`, `kokoro_82m`, `elevenlabs_voicedesign_b`). Cuando cambies de motor, el dataset
lo sabe y `dna` no mezclará peras con manzanas.

---

## S1 · GANCHO DE HISTORIA  → `hook_type: story`
`ref: build-wealth-short-01-story`

**Voz (pegar en el TTS — 494 caracteres, entra en UN bloque de CapCut, tope 500):**
```
Two men earn the same salary and work just as hard. Thirty years later, one has almost nothing while the other has over a million, on the same money in. So what changed? One spent his paycheck, and the other owned things that paid him back. His habits never failed him. A habit only moves money you already have, but an asset earns while you sleep. You already have the hard part; the only question is where you point it. So does your next hundred dollars leave, or does it work? Tell me below.
```
> **Escrito para el OÍDO, no para el ojo.** El TTS lee los FRAGMENTOS ("Two men. Same salary. Same
> discipline.") de forma robótica, con una pausa dura en cada trozo. Este guion son **frases completas
> que fluyen** — el TTS las lee natural. OJO: el texto de la PORTADA en pantalla sí es punchy
> (`TWO MEN` / `SAME SALARY`); es la VOZ la que tiene que fluir, no lo que se lee. Si alargas un guion
> por encima de 500, pártelo en 2 bloques de texto en CapCut y exporta el audio junto (el calibrador
> trabaja sobre el MP3 final).
**Reencuadre (2026-07-10):** el eje ya NO es *hábitos vs activos* (dicotomía falsa y que aleja al
viewer: invertir $500/mes ES un hábito, y el CTA "¿cuál eres tú?" humilla a media audiencia). El eje
es **qué hace el dinero: se MUEVE (se gasta, se va) o se MULTIPLICA (se posee, compone)**. Mismo
sueldo, misma disciplina, distinta DIRECCIÓN. Honra el hábito (es el combustible) y el cierre es
accionable, no acusatorio. Alineado con el S2 ("Discipline is fuel. Fuel with no engine goes nowhere").
**Texto en pantalla:** `SAME SALARY.` → `OPPOSITE ENDING.` → `SPENT $0  vs  OWNED $1,000,000+` → `LEAVE OR WORK?`
**Columnas:** `SPENT` (money leaves) vs `OWNED` (money works) — juzgan al *dinero*, no a la persona.
**Pexels:** `two businessmen walking opposite directions` · `crossroads silhouette` · `empty wallet` · `luxury home sunset` · `stock chart rising`

---

## S2 · GANCHO CONTRARIAN  → `hook_type: contrarian`
`ref: build-wealth-short-02-contrarian`

**Voz:**
**Voz (pegar en el TTS — 477 caracteres, UN bloque de CapCut; frases completas para el oído):**
```
You skipped the coffee, you wake up at five, and you budget every dollar. And you're still broke. Here's the part nobody says out loud: discipline alone can't build wealth, because a habit only moves the money you already have. Discipline is fuel, and fuel without an engine goes nowhere. An asset is the engine. It takes what you save and turns it into money you didn't work for. You already have the fuel. So could you put fifty dollars a month into an engine? Tell me below.
```
**Reencuadre (2026-07-11):** fuera "habits don't build wealth / HABITS ❌" (humilla y es falso — ver
memoria del S1). El eje: la disciplina es **COMBUSTIBLE** (se honra: "you already have the fuel"),
pero sin **MOTOR** no hay avance. El activo es el motor. CTA accionable, no acusatorio.
**Secuencia en el motor (LISTA — `s2-contrarian` en el selector):** portada `YOU DID / EVERYTHING
RIGHT.` → **checklist** (SKIP THE COFFEE ✓ / WAKE UP AT 5AM ✓ / BUDGET EVERY DOLLAR ✓, checks en
BRASS = disciplina honrada) con **dos barras en vivo: `EFFORT` sube 33→67→100% con cada ✓, `GROWTH`
clavado en `$0`** → sello `STILL BROKE.` con golpe + destello → **insight** `DISCIPLINE IS THE FUEL`
(—) vs `AN ASSET IS THE ENGINE` (↑) → CTA `COULD YOU PUT $50 A MONTH INTO AN ENGINE?`.
El contraste EFFORT 100% / GROWTH $0 ES la prueba visual del contrarian, sin humillar (esfuerzo real,
pero sin motor no crece).
**Voz:** CapCut TTS Firme Pilot (la misma de S3/S1) → exportar como `data/voz-short-02.mp3`.
**Hora:** 11:30 local (la misma del S1 — la hora fija aísla el gancho).

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
