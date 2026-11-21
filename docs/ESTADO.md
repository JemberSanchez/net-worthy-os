# ESTADO — traspaso (5-nov-2026)

Corto a propósito. Todo lo anterior, íntegro: `docs/archivo/ESTADO-v1.md` (julio-octubre: base v1,
cifras, calibrador del motor v1, las secciones "validar el instrumento", `pacing_2_3s` 31-jul y
`extractor_version` que citan comentarios del código). Plan: `docs/PLAN.md`. Reglas: `docs/POLITICA.md`.
Si este archivo y la realidad discrepan, gana la realidad (`git log`, la DB): corrígelo.

## Dónde estamos

- **Motor vigente:** v2, `video-v2/motor/` (storyboard → voz → construir → render → puertas →
  crítico). `docs/guiones/short-renderer.html` es el motor v1: ya no produce vídeos, pero
  `tools/check_motor.mjs`, `tools/alinear_voz.py` y `omega/creative/production_dna.py` aún lo citan.
- **Hito:** juez automático que coincida con el usuario y 10 vídeos v2 publicados. La autonomía va
  AL FINAL y solo cuando el usuario lo diga.
- **Calidad:** 1.ª nota a ciegas (#7, 28-oct): prefiere la versión del crítico (n=1), pero "aún puede
  mejorar mucho" en lo que cuenta. El guion en inglés no lo juzga el usuario (no es nativo): lo juzgan
  la referencia del nicho y la retención real.
- **Queja abierta:** el piloto `interest-vs-defense` "se ve mucho más simple": 0 clips, 0 imágenes,
  0 cortes (auditoría del 3-nov, `docs/mejora/auditoria.md`; `docs/mejora/` está gitignored, solo local).

## Turnos y herramientas de /producir (21-nov, rama `claude/modest-archimedes-c779c4`)

Instrumento: `tools/costo_sesion.py <proy> [--transcript X]` escribe `pasos` (minutos por paso,
modelo vs herramienta; las esperas en segundo plano y del usuario no cuentan). Validado contra la
auditoría del 20-nov en las mismas 7 sesiones: setup 4.8 = 4.8, sondeo 11.1 vs 10.6, 148 vs 147
turnos (la voz da 2.1 y no 6.3: la auditoría contaba la espera en segundo plano).

| Paso (mediana, 7 sesiones) | Antes (min)    | Ahora: medido por pieza, 21-nov                                      | Después en un /producir real |
| -------------------------- | -------------- | -------------------------------------------------------------------- | ---------------------------- |
| setup (estado+daily+sync)  | 4.8            | `estado-bajar; cola` 2 s (9 s si la nube movió la DB)                | pendiente                    |
| medios                     | 7.4            | `lote` 13 s con las hojas de la cola vs 311 s en frío (4 clips)      | pendiente                    |
| voz                        | 2.1 (máx 22.6) | en segundo plano mientras se escriben escenas                        | pendiente                    |
| entregar                   | 6.8            | `tools/entregar.py` en segundo plano: guardar+subir 6 s (repo local) | pendiente                    |
| sondeo (grep/cat + turnos) | 11.1           | `cadena.py`: voz ∥ lote → `--rapido`, solo fallos                    | pendiente                    |
| turnos                     | 148            | —                                                                    | pendiente                    |

Cola en la nube (`omega/cola.py`, `nube/cola.yml`): corrida real el 21-nov contra una COPIA local del
repo de estado: 834 s (signals 394, analytics-sync 42, meta-sync 56, medios 311), 3 temas con 6
titulares cada uno, todo verde. **Instalada el 21-nov** (`net-worthy-data/.github/workflows/cola.yml`, 7 secretos): 1.ª corrida en
GitHub 295 s, todo verde (signals 58 s, 3 temas, 8 clips). Lo que sigue es el procedimiento seguido.
**Antes de instalar:** falta copiar `nube/cola.yml` a
`net-worthy-data/.github/workflows/` y poner sus secretos (`YOUTUBE_API_KEY`, `PEXELS_API_KEY`,
`YOUTUBE_TOKEN_JSON`, `META_TOKEN_JSON`, `META_APP_ID`, `META_APP_SECRET`); antes, un `estado-subir --forzar` en el PC
(crea `data/.estado_base` y sube el primer volcado sin señales).
**Tamaño de `omega.sql` (21-nov):** `signal` era 26 de 30 MB y crecía ~2.4 MB/día (GitHub rechaza archivos
> 100 MB: ~24 días con la cola diaria). Es caché derivada de `observed_content`: ya no viaja en el volcado
(30.5 → 4.4 MB) y `decide` la regenera si falta (39 376 señales, idénticas a la tabla original).
Lo que queda crece ~0.3 MB/día (`observed_content`): ~1 año hasta 100 MB. Sin eso, `/producir` cae al camino viejo (`/daily`).
Hallazgo: los clips buscados con el término crudo son flojos (2 de 3 temas sin clip admitido; "worst
week" trajo un discurso con persona reconocible). La hoja lo enseña y la sesión decide; la cifra de
`lote` sí vale para cualquier clip que se reutilice. La columna "después" exige un `/producir` real con
la cola instalada.

## F1 long-form (18-nov, rama `claude/f1-longform-35b6f4`): previo en verde, SIN render aún

- **Retención sin render (19-nov):** avisos de `construir.py`, antes → después:

  | aviso                                 | antes                      | después                        |
  | ------------------------------------- | -------------------------- | ------------------------------ |
  | huecos sin re-gancho (> 12 s)         | 13 (peor 44 s, 73.8-117.4) | 0                              |
  | tramos "sin nada nuevo" (> 2.5 s)     | 19                         | 0                              |
  | % del tiempo con texto grande         | 91 %                       | 81 % (tope 70: sigue avisando) |
  | rachas > 3 escenas con texto centrado | 4                          | 0                              |
  | L1 contraste < 3 (previo)             | 11 (2.2-2.95:1)            | 4 (2.44-2.95:1)                |

  Cómo: 22 `golpes` en palabras de giro; fondos nuevos en 16 escenas de solo texto (6 clips Pexels
  vistos en su hoja: `grafico`, `niebla`, `oficina_vacia`, `fichas`, `rotativa`, `tarro`; foto PD
  `rpiunion`; `grafico2` descartado: mismo metraje que `mercado`); 14 `titulo` con fondo pasan a
  `foto` con el mismo medio a opacidad plena y `rotulos` que se van (`hasta`) ~2.8 s después;
  `posicion` arriba/abajo en 12 títulos; `--mute: #c3cfc7` en `plantilla-ancho.css` (el `mute` de
  `revelacion.linea1` era la causa de 9 de los 11 L1). Quedan 7 L1 de OCR en la entrada animada
  (no cambiaron) y 4 de contraste.

- Errores nuevos cerrados como prevenidos: **E11** (rótulos apilados con `top` que se pisan al
  partir línea, `construir._rotulos_solapados`, solo tema base) y **E12** (en 16:9 la placa del
  aviso tapa el kicker/sub de una `foto`, `construir.bajo_el_aviso`).
- ⚠ **El previo volvió a ser lento: 24.4 min** (contraste 715 s, texto 706 s; antes 332 + 120 s).
  Medido (19-nov, máquina libre): el OCR del previo cuesta **9.1 s de DETECCIÓN por fotograma**
  (PP-OCRv6 det small a `limit_side_len` 1920, 2 hilos; reconocimiento 0.3 s) igual con fondo liso,
  foto o clip: NO es el metraje nuevo. 140 fotogramas → 4.7 s/fotograma con 6 procesos (3 procesos
  rinden casi igual: 5.5). No es la CPU frenada (176 % de rendimiento, en corriente) ni EcoQoS
  (quitarlo: 5.57, igual). Bajar `limit_side_len` a 1280/960 acelera 2-4x pero pierde texto
  (30 y 28 de 46 líneas): descartado. Historial: solo la corrida de 18-nov 19:36 fue rápida (texto
  120 s ≈ 25 fotogramas, cuadra con los "24 frames" del commit 84dc90d); antes y después, 700-1400 s.
  Suposición sin verificar: aquella corrida muestreó ~25 fotogramas y no 140. Palancas sin probar:
  det PP-OCRv4 mobile (cambia el instrumento del crítico: validar contra el actual antes) o
  muestrear menos. Con `--auto` (por defecto) un fallo cuesta 3 rondas: 58 min. Para medir,
  `--sin-auto` y `PYTHONUNBUFFERED=1` (sin eso el log sale vacío hasta el final).

- **Previo arreglado (18-nov, 84dc90d):** la causa no era muestrear de más sino el OCR del previo
  (`medir_cuadros.ocr_imagen`) sin el tope de hilos de onnxruntime: 5.25 → 1.09 s/fotograma, mismo
  texto. Previo completo **8.0 min** (contraste 332 s, texto 120 s), TODAS las puertas pasan: s76 y
  gancho verificados. Contraste: `check` mide como mucho 5 instantes por pasada (`CONTRAST_SAMPLES = 5`
  fijo en HyperFrames, medido: 85 `--at` → 5 muestras), ~50 s fijos cada una. Siguiente: render.
- El previo añade el ref a `video-v2/usado.json`: revertirlo si no se publica (rompe
  `test_todos_los_publicados_siguen_validando`).

Historia anterior al arreglo:

- Hecho: layout 16:9, capítulos, miniatura, puertas de layout y cifra-vs-fuente. Storyboard real
  `video-v2/huang-exit-largo` (85 escenas, voz 441.8 s = 7.4 min, bajo el objetivo de 8-10 min).
  Lista de capítulos OK (6, empieza en `0:00`). Miniatura 1280x720 OK, 11 s.
- **Tiempo medido (reloj de pared):** `producir --previo --sin-subir` tarda **24.6 min** (1.ª pasada)
  y **35.1 min** (2.ª). La puerta de contraste sola: 9.0 / 11.7 min. Luego, texto/gancho (OCR):
  ~15-20 min. Dos previos suman ~60 min **antes** de renderizar: la regla de "ronda > 60 min = parar"
  se cumplió sin llegar a render, loudness, pausas ni crítico. El previo escala con la duración:
  hay que muestrear menos en vídeos largos antes de seguir.
- Puertas duras: 19 fallos de contraste bajaron a 1 (título IBM de 4 líneas tapaba el kicker, Denny's
  dorado sobre cartel amarillo, `linea2` de 4 líneas se salía por arriba). Pendientes sin verificar con
  un previo: s76 `100 companies` saltaba de línea bajo la rejilla de `puntos` (ahora `firms`) y el gancho
  con luma 31.8 < 33.5 (fondo `placa` 0.8 → 1.0).
- Avisos L1 que siguen (⚠, no bloquean): `linea1` de `revelacion` en color `mute` lee 2.2-2.95:1 en
  9 escenas. Quitar la atenuación en 16:9 NO lo movió (2.53 → 2.54): la causa es el color `mute`.
  5 avisos de OCR caen en la entrada animada (frames mirados: el texto se lee).

## Fallos recurrentes imposibles por construcción (13-nov, sin commitear)

Medido el 13-nov: 45 de 99 corridas fallaron (173 de 583 min). Tres defectos dejan de depender del
crítico: **M1** `construir.duck_sfx`/`tope_vol` baja cada efecto (whoosh, `barrido_sint`, caja…) lo
justo para que la voz quede `voz_sobre_fondo_db` + 3 dB por encima en cada ventana que mide
`tools/medir_mezcla.py` (en average-401k: `barrido_sint` 0.032 → 0.011, 3 de 18 efectos bajados;
el plan guarda los volúmenes reales en `sfx_mezcla`). **V1** `voz.py` hace UNA toma entera y re-sintetiza
solo la frase con un silencio V1 dentro (regla del crítico, comas incluidas), hasta 3 intentos medidos
por energía sobre el clip, nivel igualado y un solo realineamiento; sigue bloqueando solo la pausa sin
puntuación (`pausas_rotas`). **Log** `renders/corridas.jsonl` lleva `reglas` (regla exacta por puerta) y
`pendientes` (lo que --auto no arregló); `python tools/resumen_corridas.py` lo agrega (las corridas
anteriores solo tienen el nombre de la puerta: storyboard 27, repetición 11). Tests:
`test_sfx_ducking`, `test_voz_reparar`, `test_corridas_log`. Sin verificar aún en una producción real
(ni render ni Kokoro): confirmar M1/V1 en el informe del crítico del próximo Short.
**Puerta storyboard, reglas exactas** (sacadas de los transcripts: qa.json solo guarda la última corrida,
que pasó): 25 de los 27 fallos son ANTERIORES a `autoarreglo` (12-nov) y sus tres reglas más frecuentes
(ancla en otra frase o dentro de palabra con guion 37, ambiente sin `dur` 8, texto < 0,5 s 7) ya las
arregla `--auto`. Los 2 posteriores (huang-resigns): "voz sin subtítulo" sin arreglo mecánico → a mano
`"subtitulos": ["0:now", …]`, que `validar` aceptaba y `plan()` reventaba con `int()`. Ahora `plan()`
acepta anclas en `subtitulos` y `--auto` ensancha `subtitulos` a la frase muda (salvo escena `limpio`).
No hay más regla frecuente que convertir en valor por defecto con estos datos: medir con el log nuevo.

## Velocidad de /producir (12-nov, rama `claude/heuristic-jennings-f19905`)

Meta del usuario: tema → preview en < 5 min sin perder calidad. Medido en `huang-exit` (RTX 5050,
12 núcleos; ruido de render ±20-30 % entre corridas). La sesión real de huang-exit: 69 min de reloj =
~40 min esperando procesos en segundo plano + ~15 min de herramientas + ~13 min generando Claude.

| Etapa                            | Antes (s)                      | Después (s)   | Cambio                              | Efecto en calidad (medido)                                 |
| -------------------------------- | ------------------------------ | ------------- | ----------------------------------- | ---------------------------------------------------------- |
| Puertas estáticas + build + lint | 8-20                           | 9-25          | + P1 del storyboard, contador ancho | más fallos cazados antes de la voz                         |
| Contraste (`check`)              | 65-85                          | 27-52         | `--no-craft`                        | mismos 62 textos                                           |
| OCR del previo                   | 123                            | 68            | 6 procesos                          | mismo modelo y límite                                      |
| **`--previo` entero**            | **312** (282-444 en la sesión) | **228**       |                                     | + puerta `gancho` (C1)                                     |
| Render `--quality high`          | 133-173                        | 114           | sin cambio (dentro del ruido)       | —                                                          |
| Preview ffmpeg                   | 31                             | ~7            | `veryfast`                          | SSIM 0.988 vs 0.989                                        |
| Ritmo / loudness / social        | 36 / 12 / 128                  | 39 / 12 / 126 | sin cambio                          | —                                                          |
| Crítico (OCR + medidores)        | 364-443                        | 239           | OCR en 6 procesos                   | 74/74 fotogramas idénticos                                 |
| **`--sin-subir` entero**         | **924**                        | **612**       |                                     | igual o mejor                                              |
| Rondas evitadas                  | —                              | —             | P1, aviso, gancho, contador         | huang-exit: 3 bloqueantes que costaron un render de 1157 s |

Fallos que ya no llegan al render: P1 recursos/guion/estructura (puerta `repeticion`, mismos
máximos de la rúbrica), contador3d más ancho que el cuadro (`puertas.contador_ancho`), gancho oscuro
C1 (puerta `gancho` del previo, margen de luma +3.5 PROVISIONAL n=1), aviso final pequeño (`tam`
ahora llega a `#avisofin` y el parche escala lo medido). Bug del instrumento arreglado: `en_orden`
cruzaba líneas a menos de 57.6 px y daba un aviso legible por "no leído".

**Hueco a 5 min (sin rebajar nada):** previo 228 s + render-y-crítico 612 s ≈ 14 min de máquina
con UNA sola ronda, más la voz (~2 min) y los turnos de Claude. Con la red completa (render high +
crítico) **< 5 min no es alcanzable hoy**: render 114 s + OCR del crítico ~200 s ya son 5 min.
**Preview rápida (12-nov, elegida por el usuario; render alto desde el 21-nov):** `producir.py <ref> --auto --rapido` =
puertas estáticas + build + lint + contraste + render **high** + loudnorm + gancho → `renders/<ref>-final.mp4`

- `renders/render.json`. El `--sin-subir` de detrás lo reutiliza (misma página y assets) en vez de
  renderizar otra vez; draft solo ahorraba 2.7 s (75.0 vs 77.7 s, huang-resigns). Ojo: `--rapido` sobrescribe
  el final anterior, aprobado o no; publicar sigue exigiendo la aprobación del crítico sobre ESTE MP4 (sha).

**Par `--rapido` + `--sin-subir` (21-nov, berkshire-1999, una corrida de cada lado, cachés en frío, puerta
`fuentes` simulada en ambas porque su contenido ya no pasa):** **975 s → 399 s (−576 s)**. rápido 190 → 164
(render draft 123 vs high 98.5: ruido), sin-subir 785 → 235: render 271 → 0 (reutilizado), loudnorm 4 → 0,
crítico 496 → 205 (no vuelve a decodificar ritmo y loudness: `<final>.medidas.json` por sha; el resto de la
caída no está aislado, n=1). Hecho a la vez: ritmo y loudness se miden UNA vez y en paralelo, en el proceso
(`producir.medir_final`); la preview ffmpeg va en segundo plano; la tarjeta de la historia se fotografía
en el hilo del carrusel (la historia solo corta el MP4); con render reutilizado el carrusel corre junto a
las medidas y el crítico. `medir_loudness` daba el pico de MUESTRA como "Pico real"; ahora es true peak 4x
(BS.1770-4): en 10 finales reales difiere ≤0.04 dB del ebur128 de ffmpeg (el pico de muestra quedaba hasta
0.22 dB por debajo). Storyboard listo → preview en ~2.6 min; tema → preview sigue
dependiendo de los turnos de Claude (guion, medios, voz ~2 min).
Pendiente de decidir: cola de temas preparada de antemano (investigación + cifras + guion fuera del reloj).
Sin medir aún: worker de voz persistente (Kokoro se recarga en cada toma), social y ritmo en
paralelo con el crítico, anclas desnudas que derivan (no hay arreglo estático todavía).

## Vídeos (DB local `data/omega.sqlite`, 5-nov)

Filas: `production_video` 39, `production_dna` 6, `production_outcome` 5, `production_cost` **0**.
Publicación según `production_video`, no comprobada en vivo. Puntuación = score v3, **PROVISIONAL**.

| Ref                                  | YouTube `publish_at`      | FB/IG | Vistas FB+IG | Score v3                                        |
| ------------------------------------ | ------------------------- | ----- | ------------ | ----------------------------------------------- |
| housing-turn                         | 29-oct                    | sí    | 10           | sin ADN ni outcome                              |
| fed-vs-card                          | sin fecha (subido 30-oct) | sí    | 62           | 0,37                                            |
| binance-heist                        | 31-oct                    | sí    | 195          | 0,26                                            |
| gdp-annualized                       | 1-nov                     | sí    | 30           | 0,73 (retención 1,0 con 75 vistas: sin validar) |
| aws-profit                           | 2-nov                     | sí    | 3            | 0,61                                            |
| saving-rate                          | 3-nov                     | sí    | 2            | sin outcome                                     |
| midterm-rally                        | 5-nov                     | sí    | 421          | 0,61                                            |
| ronald-wayne                         | 6-nov (UTC)               | sí    | -            | sin outcome                                     |
| interest-vs-defense                  | no publicado (piloto)     | no    | -            | -                                               |
| read-janitor (#7), grace-groner (#8) | no publicados en v2       | no    | -            | -                                               |

n=5 con outcome: observaciones, no reglas. v1, v2 y v3 no son comparables.
Huecos: `production_cost` vacío (punto 4.2 del PLAN), `housing-turn` sin ADN, `saving-rate` sin outcome.

## Siguiente paso

Orden en `docs/PLAN.md`. Hecho: 1.1 (`guionista.py`), 3.1 parcial (solo duración), crítico Fase 1,
score v3, `meta-sync`. Abiertos de mayor peso: 1.2 contar con imagen y la queja del piloto, 2.1
verificar cifras contra la fuente, 3.2 tema.

Decisiones del 5-nov: `aspecto: cine` sigue opt-in (A ganó, n=1 y temas distintos: no aísla la variable),
pero se usa en vídeos nuevos hasta tener un par con el mismo tema. Demo `interest-outran-defense` fuera de
`video-v2/usado.json` (no publicada, bloqueaba aperturas; un rebuild la vuelve a añadir). Turno 2 del
calendario de `docs/VIRALIDAD.md` §7: noticia con estructura "error común".

## Trampas vigentes

- **Meta 500 en `media_publish`:** puede haber publicado igual. `_ig_publicar` ya mira el contenedor; si
  ves un 500 en otro paso, mira el feed antes de reintentar.

- **Publicar:** nada público sin aprobación explícita en el chat. Meta (FB/IG) `--publicar` SIEMPRE
  con confirmación. Fijar el comentario es a mano en Studio.
- **Tasa "se quedaron":** no está en la API; se lee en Studio.
- **`pkill -f`** con un patrón que aparece en tu propio comando mata tu shell.
- **`critico.py --mp4`:** el `index.html` y el `qa.json` del proyecto deben ser los de ese vídeo.
- **Commons** limita por IP (429, hasta 600 s): `lote`, nunca bucles de `bajar`.
- **Kokoro** no es determinista entre síntesis (±0,2 s): alinear siempre sobre el audio final (`voz.py`).
- **Auditoría `check` de HyperFrames** con poca espera devuelve 0 textos "ok": `producir.py` usa 60 s
  y exige que haya medido.
- **HyperFrames** siempre en la última versión (se registra en `qa.json`). Si Chrome se actualiza, el
  render puede caer a la iGPU (~2× más lento); `producir.py` avisa.
- **Render:** ≈7× la duración en CPU. Medir antes de prometer vídeos largos.
- **Contenido "inauténtico" de YouTube:** historias distintas, fuentes, variar también lo visual.
- **YMYL:** nada de consejo personalizado; "10 % histórico" va con "≈7 % tras inflación"; el S&P 500
  no es "seguro" (-57 % en 2007-09). Tabla de cifras corregidas: sección 7 del archivo.
- **Zonas seguras:** YouTube tapa ~350 px abajo y ~120 px a la derecha; Reels ~290 px abajo.
- **Nube:** YouTube bloqueado salvo dominios permitidos; el repo de estado llegó a estar en solo lectura.
- **Commit:** mensaje por archivo (`git commit -F`) si lleva comillas, `&` o `$`.

## Disco

`renders/` no se versiona y crece ~100-200 MB por vídeo. `<ref>-final.mp4` hay que conservarlo:
`medir_parecido.py` y `social.py` lo leen. `<ref>.mp4` (crudo antes de loudnorm) y `critica/r0.mp4`
idéntico al final sobran una vez terminado el vídeo. Borrar es decisión del usuario.
