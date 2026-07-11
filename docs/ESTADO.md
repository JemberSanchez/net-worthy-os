# ESTADO DEL PROYECTO — documento de traspaso

> **Para el nuevo chat:** lee este archivo entero antes de tocar nada. Luego `CLAUDE.md`,
> `docs/POLITICA.md` y `docs/VISION.md`. Ruta: `C:\Users\Asus\Desktop\Proyecto AI`
> (repo git, rama `master`). Hay memoria en `~/.claude/projects/.../memory/` que se carga sola.
>
> **Última actualización: 2026-07-11.** Estado en una línea:
> *DOS Shorts PUBLICADOS (S3 stat el 07-10, S1 story multi-escena el 07-11); `production_outcome = 0`;
> lo único que importa es MEDIR — el S3 el sábado 12, el S1 ~48h tras publicar (~13). ADN de ambos
> registrado (3/10 instrumentados). POR CONFIRMAR del S1: hora local, variante de voz CapCut, horas
> (`record-cost`). URLs y contexto de ambos en la tabla `production_context`.*

---

## 1. Qué es
Sistema que decide **QUÉ** contenido crear (por datos: demanda + dinero) y acumula **qué funciona**.
NO es un generador de video — el video es el primer producto, el activo es el conocimiento calibrado.
Nicho: **finanzas/inversiones/crypto, faceless, audiencia EN**. Canal: **Net Worthy** (@networthytv).

## 2. El reparto mental (lo más importante)
```
SISTEMA decide QUÉ (tema, por demanda+RPM)  →  TU CLAUDE piensa CÓMO (ángulo estructurado)
                                            →  SISTEMA acumula QUÉ FUNCIONA (record-outcome)
```
Regla dura (memoria [[raw-term-is-que-not-video]]): un término del detector ("build wealth") es
una **señal de demanda, NO un video**. Estructurarlo siempre + aviso YMYL.

---

## 3. ⚠️ LO ÚNICO QUE IMPORTA AHORA
El Short #1 se publicó. **`production_outcome` sigue en 0 filas.** El moat no se llena al publicar,
se llena al **medir**.

**Sábado 2026-07-12** (48h), con YouTube Studio y Facebook abiertos:
```
python -m omega.cli record-analytics    # ctr/avd/retención como FRACCIÓN 0..1, NUNCA %
python -m omega.cli record-cost         # horas REALES del usuario
python -m omega.cli record-outcome build-wealth-short-03-stat <0..1>
python -m omega.cli dna
```
`data/production_analytics.json` y `data/production_cost.json` ya existen con ceros y con el aviso
del formato. **Si el usuario escribe `4.5` en vez de `0.045`, el comando lo rechaza** (guard añadido).

Las **vistas/likes/comentarios** se pueden sacar por API sin copiar nada:
```python
from omega.sources import youtube
youtube.video_stats(['HMkPACqdvV8'])
```
CTR y retención **no son públicos**: solo en Studio. Eso lo copia el usuario.

> ⚠️ **CONFOUNDER ANOTADO.** Se publicó a las **02:00 hora local (UTC-5)** y la audiencia es EN/US.
> Si la velocidad inicial es baja, puede ser la HORA, no el gancho. **No lo atribuyas a
> `hook_type=stat`.** Está guardado en `production_context`. Es la Regla 3 de POLITICA.md.

---

## 4. El video publicado
| | |
|---|---|
| `production_ref` | **`build-wealth-short-03-stat`** |
| Publicado | 2026-07-10 · 07:00:32 UTC (02:00 local) |
| YouTube | https://youtube.com/shorts/HMkPACqdvV8 (id `HMkPACqdvV8`) |
| Facebook | https://www.facebook.com/share/r/1CiuGzWcRV/ |
| Archivo | MP4 H.264+AAC · 1080x1920 · 30.00 fps exactos · 24.03s · 13 MB |
| ADN | `hook=stat, story=none, cta=comment`, 7 bloques |
| Voz | CapCut TTS "Firme Pilot" (`data/voz-short-03.mp3`, gitignored) |
| Música | **ninguna** |

Todo el contexto (motor de voz, motor de visuales, fps, confounder, URLs) está en la tabla
`production_context`, escrito con `omega.creative.decisions.record_context` — una API que ya existía.

---

## 5. EL MOTOR DE VIDEO — `docs/guiones/short-renderer.html`
Un solo HTML, sin dependencias, se abre con doble clic. **Genera el Short entero**: intro, curva
compuesta, número dorado, CTA y subtítulos quemados, con la voz incrustada. **No hace falta CapCut.**

**Desde 2026-07-10 es MULTI-SHORT** (selector arriba): cada Short es un bloque en `SHORTS[...]` con
su `escena` (`chart` = curva del S3 · `columns` = dos columnas del S1), su `voz` (`data/voz-short-NN.mp3`),
su guion y su CTA. La escena `columns` narra SPENT vs OWNED con monedas por las ramas, año corriendo,
conteo al millón, fuga y chispas — **todo determinista** (`drawFrame` sigue siendo pura: verificado
por comparación de píxeles). **Desde 2026-07-10 (tarde) hay COMPOSITOR MULTI-ESCENA**: un Short tiene
una escena base + `overlays[]` componibles (portada, cierre) que se funden por alpha sin tocar el
interior de la base. El S1 estrena una **portada** ("TWO MEN. / SAME SALARY.") que se disuelve en las
columnas. Escenas registradas: `chart`, `columns`, `titulo`, `outro`. Arquitectura completa y ruta a
long-form (8-10 min) en **`docs/ARQUITECTURA-MULTIESCENA.md`** — el cuello de botella no son las
escenas (ya están) sino memoria (ffmpeg + render por segmentos), voz por segmento y layout horizontal. Hay un **checklist de producción que se marca solo** (voz → calibración →
previsualización entera → MP4). Guards añadidos tras auditoría: sin voz o sin cortes medidos no se
graba (ahora también en el camino MP4), el audio decodificado se suelta al cambiar de Short (antes el
S1 habría salido CON LA VOZ DEL S3), la calibración manual del S3 solo se aplica si el S3 está activo,
y el `.srt` deriva los cortes del guion activo (ya no está cableado al S3).

```
1. Servirlo por http (el botón "Usar la voz del proyecto" hace fetch y file:// lo bloquea):
   .claude/launch.json ya tiene un servidor estático -> http://localhost:8765/docs/guiones/short-renderer.html
2. "🎙 Usar la voz del proyecto" -> carga data/voz-short-03.mp3 y calibra
3. "⏺ Grabar y descargar el Short" -> MP4 listo para subir. ~1 min. Puedes cambiar de pestaña.
4. "⬇ Frame final" -> PNG del número dorado (miniatura YT + portada FB)
```

### Datos vs motor
`SHORTS['s3-stat']` contiene **todo** lo que define un Short: `spec` (3 líneas de la intro), `cta`,
`pmt/years/rate`, y un `guion` con:
- `grupos[]` — el texto **hablado**, partido en bloques narrativos. **Sus arranques SON los cortes.**
- `cifras[]` — spans hablados → token que se pinta (`"a hundred and eighty thousand dollars"` → `"$180,000"`)
- `subtitulos[]` — qué grupos llevan subtítulos
- `curvaLlegaEn` — la curva termina cuando la voz acaba de decir esa cifra
- `omitirEnSubtitulos[]` — muletillas que se oyen pero no se escriben

El resto del archivo es motor y **no se toca por Short**.

### Calibrador automático (lo más valioso)
Dado el MP3 + el guion, deduce solo los cortes, el spec drop y los subtítulos:
1. segmenta la voz por energía (RMS 10 ms, silencio ≥250 ms)
2. reparte los grupos entre los segmentos con **programación dinámica** (el mapeo 1:1 es FALSO:
   en el S3 exigía 11.1 sílabas/s en un bloque)
3. dentro de cada grupo alinea palabra a palabra sobre el tiempo de **voz real**, saltándose las
   pausas → la deriva no se acumula

**Verificado:** contra `voz-short-03.mp3` reproduce **exactamente** lo que se calibró a mano —
cortes `5.94 / 12.80 / 15.99 / 22.44`, spec `[-0.30, 2.15, 4.41]` y **11 de 11 subtítulos idénticos**.
Método completo en `docs/guiones/calibracion-voz-short-03.md`.

El S3 (ya publicado) usa su calibración manual; no se re-renderiza lo que está en la calle.

### Exportador MP4
`MediaRecorder` **no sirve**: `isTypeSupported('video/mp4')` devuelve `true` y luego produce **0 bytes**.
Y **Facebook no acepta WebM** (su lista oficial: mp4, mov, mkv, avi, ogv… sin webm).
Por eso el MP4 se construye a mano: `drawFrame(t)` es pura → render offline frame a frame →
**WebCodecs** (`VideoEncoder` H.264 + `AudioEncoder` AAC) → **muxer ISO BMFF escrito a mano**
(`ftyp | mdat | moov`, orden que evita el huevo-y-la-gallina de los offsets `stco`).
Regalo: 30 fps exactos, cero frames perdidos, y no depende de `requestAnimationFrame` (se puede
cambiar de pestaña; el yield usa `MessageChannel`, no `setTimeout`, que se estrangula en background).

---

## 6. ZONAS SEGURAS (no las muevas sin medir)
```js
SAFE = { top: 190, bottom: 360, left: 70, right: 130 }   // sobre 1080x1920
```
YouTube Shorts tapa los **350 px inferiores** (canal/título/música) y **120 px** a la derecha.
Facebook Reels, ~290 px abajo. El `$429,985` y el aviso YMYL **estaban dentro de esa franja** y no se
veían. Hay un interruptor "ver zonas seguras" en el renderizador para comprobarlo a ojo.

---

## 7. CIFRAS VERIFICADAS (tres eran falsas)
| Cosa | Estaba mal | Correcto |
|---|---|---|
| Gap del compuesto | $420,000 | **$429,985** ($609,985 final, no ~$600k) |
| Convención | ambigua | **7% nominal capitalizado mensual** ($500/mes × 360) |
| El café | "$18,000 invertido" | $18,250 es el ahorro **SIN invertir**; invertido: **$26,323** |
| S&P 500 | "9,5%" | ~10,4–10,7% **nominal** · ~6,5–6,8% **real** desde 1957 |

**Regla YMYL:** si dices "10% histórico" tienes que decir "≈7% tras inflación", o el número final no
cuadra. Y **nunca** llamar al S&P "sólido" o "seguro": cayó **-57%** en 2007-09.

---

## 8. VOZ — estado real
- **Ahora se usa CapCut TTS** (voz "Firme Pilot"). Gratis, uso comercial según CapCut.
- **ElevenLabs está APLAZADO**, y por dos razones verificadas:
  1. su **plan gratis no da derechos comerciales**, y los derechos se conceden **AL GENERAR**
     (lo hecho en gratis no se legaliza pagando después). Hace falta Starter ($5/mes).
  2. sus voces **Default (Brian, Adam, Antoni…) EXPIRAN el 31-dic-2026**. Para un canal faceless la
     voz ES la identidad. Si se paga, hay que usar **Voice Design** (permanente y única).
- Si el usuario decide pagar: el prompt de voz elegido está en `docs/guiones/voice-design.txt`
  (prompt B, *"el que te cuenta la verdad"*). Ajustes: stability 40 / similarity 75 / style 20.
- **Cambiar de motor de voz rompe la comparabilidad.** Se anota como bloque en `production_dna.blocks`.

---

## 9. QUÉ HACER DESPUÉS (en este orden)
1. **Sábado 12: MEDIR.** `record-analytics` + `record-cost` + `record-outcome` + `dna`. Nada más.
2. **Producir el S1** (`hook_type=story`). La escena de dos columnas **YA EXISTE** y el guion se
   **reencuadró** (2026-07-10): el eje ya no es "hábitos vs activos" (falso y humilla al viewer),
   es **qué hace el dinero — se GASTA (SPENT, $0) o se POSEE (OWNED, $1M+)** — respetando la
   disciplina. Solo falta: **que el usuario grabe la voz** (CapCut TTS "Firme Pilot" →
   `data/voz-short-01.mp3`). Todo el paso a paso, textos de subida y comandos de anotación:
   **`docs/guiones/PRODUCCION-S1.md`**. Guion en `shorts-pack-01.md`.
3. Luego S2 (`contrarian`), S4 (`shock`), S5 (`question`). **Uno al día.**
   Los 5 comparten tema, voz y estilo: **la única variable es el gancho.** Es un experimento con la
   variable aislada, que es lo que exige la Regla 3.

**NO construir un generador de posts de texto.** Verificado: el alcance orgánico de una Página de
Facebook es el **1-6% de sus seguidores**, y el canal tiene **cero**. Los posts de texto no se
distribuyen a no-seguidores; los Reels sí. Los Community posts de YouTube tampoco (van a suscriptores).
"Contenido diario" = **más Shorts**, no más formatos.

---

## 10. TRAMPAS CONOCIDAS (le costaron horas a la sesión anterior)
- **`MediaRecorder.isTypeSupported()` MIENTE.** Hay que sondear grabando de verdad, y sondear el
  **vídeo aislado**: con una pista de audio adjunta, un contenedor sin códec de vídeo igual emite
  bytes (los del audio) y el sondeo da un falso positivo → archivo con voz y sin imagen.
- **`+duration.toFixed(2)` redondea HACIA ARRIBA** la mitad de las veces → `currentTime` nunca
  alcanza el límite → bucle infinito al grabar. Usar `Math.floor` y `audioEl.ended`.
- **La pestaña en segundo plano estrangula `requestAnimationFrame`** → vídeo a saltos, sin avisar.
  Hay guards; el camino MP4 (WebCodecs) no lo sufre.
- **Los subtítulos NUNCA se reparten proporcionalmente.** Ese fue el desfase del S3: el habla no es
  un metrónomo. Sin tiempos medidos → sin subtítulos, y grabar está vetado.
- **El panel de preview de Claude reporta `document.hidden = true`** y estrangula rAF: los guards
  saltan. Para verificar hay que tomar una captura antes (trae la pestaña al frente) o sondear
  la lógica directamente.
- **PowerShell rompe los mensajes de commit** con comillas/`&`/`$`. Escribir el mensaje a un archivo
  y usar `git commit -F <archivo>`.
- Hay un hook de plugin roto (`validate_antipatterns.py` no existe) que escupe un error tras cada
  edición. **Es ruido, se ignora.** Las ediciones se aplican bien.

---

## 11. Qué está construido (código)
- **92 tests verdes** (`python -m unittest discover -s tests -q`). Correr SIEMPRE antes de commitear lógica.
- **Kernel** `omega/reasoning/` (domain-agnostic, test de pureza por AST): beliefs/predictions,
  signals, hypotheses, opportunities, decision_engine (score = confianza + Σ peso·feature), decisions.
- **Observación + decisión** `omega/`: `sources/rss.py` (12 feeds) · `sources/youtube.py` (API, filtro
  solo-EN) · `analyze/momentum.py` · `analyze/demand.py` · `analyze/monetization.py` (RPM) ·
  `analyze/hypothesis_engine.py`.
- **`decide`** pondera demand · gap · demand_momentum · **monetization** (dinero, no viralidad).
- **Creativo** `omega/creative/`: patterns (CKB), decisions+calibración, combinator, experiments,
  production_dna (ADN + analíticas + coste, con guard de confounding).
- **Auditoría 2026-07-09:** 3 bugs de señal arreglados (contracciones inglesas esquivaban las
  stopwords; `record_analytics` sin validación de rango; `feeds.json` arrastraba retiros DEPORTIVOS
  vía "OR retirement" — "justin verlander" llegó a **ganar** `decide`).

## 12. Comandos
Diario: `ingest` · `youtube-scan` · `signals` · `decide` (atajo **`/daily`**).
Explorar: `trends` · `youtube <q>` · `related <tema>` · `patterns` · `combine`.
Tras publicar: `record-dna` · `record-cost` · `record-analytics` · `record-outcome <ref> <0..1>` ·
`dna` · `learnings`.

## 13. Convenciones
- Responder en **español**; el contenido del canal va en **inglés**.
- **Verificar antes de afirmar.** Esta sesión encontró 3 cifras falsas y ~8 bugs; ninguno se evitó
  "siendo cuidadoso", todos aparecieron al **medir**. Es el activo del proyecto.
- `data/` y `.env` gitignored. Rama `master`. Commits terminan con
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Windows + PowerShell. Kernel `omega/reasoning/` es domain-agnostic (test de pureza): nada de video.

## 14. Cómo arrancar el nuevo chat
> *"Lee `docs/ESTADO.md`. Estamos en: Short #1 publicado, `production_outcome = 0`.
> [Si es sábado 12 o después] Vamos a medir y cerrar el bucle.
> [Si no] Vamos a producir el S1: necesito la escena de las dos columnas."*

**No empieces a construir nada sin leer `docs/POLITICA.md`.** El motor creativo está congelado.
Progreso del proyecto = **filas del dataset**, no commits ni módulos. Van 2 de 10 instrumentados,
y **0 medidos**.
