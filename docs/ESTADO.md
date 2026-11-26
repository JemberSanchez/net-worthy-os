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

## Crítico antes del render (25-nov, `huang-exit-largo`, HF 0.9.96): boceto a 10 fps

`critico.py` sin `--mp4`: cada ronda mide un **boceto** (`producir.py --boceto`: render 10 fps draft +
loudnorm, sin contraste) y el render completo va UNA vez al final. 10 fps contiene exactamente los
cuadros que muestrean los medidores (OCR 2, ritmo/cuadros 5, parecido 1 fps; test `TestBoceto`).
Publicar sigue exigiendo el crítico sobre el MP4 final (`--mp4 <final> --solo-revisar`): sin cambio.

| paso (1 corrida, `--rondas 0`)                   | medido                                        |
| ------------------------------------------------ | --------------------------------------------- |
| sin MP4: G2 re-ganchos / V1 voz / Whisper limpia | 0.0 s (5 fallos) / 0.6 s (4) / 21.7 s         |
| boceto (puertas + build + render 10 fps + loud.) | **681 s**                                     |
| crítico sobre el boceto                          | **195 s**                                     |
| render final (puertas + contraste 310 s + HF)    | 2417 s: HF 31m51s en la **Intel** (ver abajo) |
| crítico sobre el final (solo para validar)       | ~5 min                                        |

Fidelidad, boceto vs final de la MISMA página: **26 de 32 fallos iguales**. Distintos: 4+4 A1 "escuchar"
(una sola medida de Whisper, el propio informe lo marca dudoso), L1 "DREAMCAST" 2.98:1 solo en el final
(umbral 3.0, al filo), un C1 (84.2 s) solo en el boceto, el mismo M1 (~188-191 s) en escena 36 vs 37.
Contra el r0 del 22-nov (HF 0.9.86, otra EQ de música): 24 de 37; esos 37 ya no son la referencia (sus 2
M1 de loudness/pico desaparecen: el loudnorm actual da -14.4 LUFS / -1.85 dBTP).
Siguiente (sin medir): boceto en `--quality high` para quitar la diferencia de codificador en los casos al filo.

**Render lento = GPU:** desde el 21-nov HF usa Chrome `win64-158.0.8127.88`, sin `GpuPreference=2` en
`HKCU\Software\Microsoft\DirectX\UserGpuPreferences`: el render cayó a la Intel (31m51s vs ~16).
Añadida a mano el 25-nov; se repetirá con cada Chrome nuevo de HF.

## Render por escena (23-nov, medido en `huang-exit-largo`, HF 0.9.86): SÍ funciona, con recorte

Paso 1 de `docs/PLAN-VELOCIDAD.md`. **Implementado el 24-nov** (`video-v2/motor/tramos.py`, puerta
`render` de `producir.py`; cómo funciona: sección "Render por escena" de ese archivo). Medido sobre una copia del proyecto (rama f1, `index.html` del 22-nov):

| medida                                                    | resultado                                                                                                                                                         |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| render completo `--gpu --workers 4 --quality high`        | **15m 56s** reloj (capture 13m14s; fijos: compile 33 + extract 78 + audio 105 s)                                                                                  |
| `--start/--end` nativo sobre `index.html`                 | **falla siempre**: `PLAN_TOO_LARGE` (3.48 GiB > tope 2 GiB, no expuesto en la CLI). Planifica la película entera (64 clips, 63 s de extract) para cualquier tramo |
| recortar la página (quitar recursos fuera del tramo)      | quitar `<section>` rompe `motor.js` (`puntos`: `appendChild` de null). Quitar solo `<video>`/`<audio>` fuera del tramo: funciona                                  |
| 1 escena recortada (s10, 6.6 s; s11, 5.8 s)               | **1m 44s y 2m 14s** reloj (HF: 1m32s, 2m02s). ~60-70 s fijos (audio 41 s, probe 9 s, npx ~12 s) + captura                                                         |
| fidelidad escena vs completo (198 frames)                 | SSIM medio 0.990 (mín 0.989), PSNR 46.8 dB. Diferencia de codificador: el tramo ignora `--gpu` y sale en libx264 8.7 Mbps; el completo es h264_nvenc 15.7 Mbps    |
| unir s10+s11 por stream copy                              | 372 frames exactos (198+174), sin salto en el corte (SSIM 0.9892 → 0.9904 en el frame 1589), audio idéntico (error rel. 0.0000, desfase constante 12 ms)          |
| empalmar el tramo en el MP4 completo (re-codificar nvenc) | **43 s**; 13288 frames (= completo); zonas sin tocar SSIM 0.9959 (mín 0.9916); cortes sin salto                                                                   |

Conclusión: un parche de 1 escena pasa de ~16 min a **~2.5-3 min** (tramo ~1m45-2m15 + empalme 43 s).
Los tramos usan `[round(a·fps), round(b·fps))`: tramos contiguos encajan sin huecos ni duplicados.
`--resume` de HF NO sirve de caché: reusa segmentos solo con el mismo `planHash` (misma página).
Scripts del experimento (`recortar.py`, `comparar.py`): carpeta de notas de la sesión, no en el repo.

Prueba de la implementación (24-nov): parche simulado en s40 (texto + `fondo.opacidad`) →
`render_por_tramos` eligió el tramo 200.2-213.7 s (s40 ± vecinas) y tardó **175 s** de reloj en total.
SSIM por frame sobre 13288 frames, audio idéntico (err. 0.0000) en todos:

| comparación                                | fuera del tramo | escena s40 |
| ------------------------------------------ | --------------- | ---------- |
| suelo: dos completos de la MISMA página    | 0.9941          | 0.9929     |
| empalme vs completo de la página parcheada | 0.9934          | 0.9885     |
| empalme vs original sin parche             | 0.9958          | 0.9813     |

Fuera del tramo, el empalme queda en el suelo de ruido: el render completo tampoco es exacto contra sí
mismo. En s40 se parece más a la verdad que al original: el parche entró. Lo que falta hasta 0.9929 es
libx264 contra nvenc. Ese día el completo tardó 12m55s y 20m45s (mismo PC).

## F1 long-form (18-nov, rama `claude/f1-longform-35b6f4`): previo en verde, render medido 22-nov (sin publicar)

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
- **Contraste por píxel DESCARTADO (22-nov):** sustituir `check` (589 s) por
  `medir_texto.contraste_caja` sobre los fotogramas del previo (OCR de 85 en 28 s) no da el mismo
  veredicto: `check` aprobó los 244 textos; el píxel suspende 4 de 122 líneas diseñadas a 3:1 (SIX
  MONTHS 2.44, LATE-NINETIES PC 2.86, MICROSOFT DIRECTX 2.97, THE PC NEEDED 2.98) y el usuario los lee
  bien en el fotograma entero. p95/p5 subestima el texto grande tenue; bajar el umbral para que cuadre
  con n=4 sería ajustar a ojo. `check --json` no da razón ni caja por texto (solo totales).
- **Render medido (22-nov, `--quality high`, 443 s de vídeo):** CPU **1953 s** vs `--gpu` (NVENC)
  **1680 s** (-14 %); SSIM 0.9916 / PSNR 49.8 dB GPU contra CPU (como el Short: 0.992). El cuello
  es la captura (CPU 1870 s, GPU 1522 s de captura) con **1 worker**: la calibración de HyperFrames
  mide p95 2034 ms/fotograma y baja `auto` de 4 a 1 ("compositor starvation"). `--start/--end` falla
  aquí (`PLAN_TOO_LARGE`, plan 2.98 GiB > 2 GiB): no hay tramo barato.
- **`--gpu --workers 4` medido (23-nov):** **846 s** (-50 % vs 1 worker; captura a disco 753 s).
  SSIM 0.9916 igual, pero 6 de 13288 fotogramas (330.3-330.5 s, PSNR mín. 31.5 dB vs 46.5) muestran
  la píldora "BILLION · FORBES EST." aún borrosa (estado anterior de su entrada): el "starvation" que
  la calibración temía existe, aquí 0.2 s. Adoptado en `producir.py` (RENDER_GPU) con OK del usuario.
- **Crítico `--solo-revisar` medido (22-nov, OCR DirectML, MP4 crudo):** **940 s**. `medir_ritmo.leer_frames`
  322 s, OCR 288 s (887 fotogramas, 0.32 s c/u), `medir_parecido` 82, loudness 78,
  `revisar_audio` 72, `leer_grises` 34, resto < 25. Antes (OCR en CPU) sin medir; suposición con
  4.7 s/fotograma: ~70 min solo de OCR.
- **`medir_ritmo.leer_frames` 323 → 54 s (23-nov):** `grab()` sin convertir los fotogramas que no se
  muestrean + blur a 270 px de ancho en vez de a 1080p. `max_s`/`desde_s` idénticos en 6 vídeos (5
  Shorts + el long-form); `pct_quieto` ±0.5 pt, 5 cruces del umbral en ~3100 comparaciones.
- **OCR sin clasificador de ángulo 288 → 234 s, y MÁS correcto (23-nov):** `Global.use_cls: False`.
  El cls giraba 70 de 886 fotogramas a basura ("WOULD IT SURVIVE?" → "WOUS SUIES"): un L1 falso
  (escena 3) desaparece, los otros 6 fallos idénticos. ⚠ `motor(img, use_cls=...)` por llamada se
  queda pegado al motor: comparar con dos motores. Descartado con datos: reusar OCR entre fotogramas
  consecutivos (solo 29/885 iguales) y 1 fps (7 → 11 fallos, falsos en entradas animadas).
- **`medir_parecido.hashes_video` 94.8 → 42.3 s:** `grab()` en saltados, 443 hashes idénticos.
- No se reproducen: loudness 8.8 s aislado (no 78); Whisper 32 s por transcripción igual con
  0/8/12 hilos (`revisar_audio` = 2 transcripciones). Siguiente: `/producir` completo con `--workers 4`.
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
**Preview rápida (12-nov, elegida por el usuario):** `producir.py <ref> --auto --rapido` = puertas
estáticas + build + lint + contraste + render `draft` + gancho sobre ese MP4 → `renders/<ref>-rapido.mp4`.
Medido en huang-exit con la máquina libre: **154 s** (puertas 7, contraste 32, render 109, loudnorm 4,
gancho 1). Con otra sesión renderizando a la vez: 350-383 s (no lanzar dos producciones juntas).
Draft = mismo 1080x1920, 30 fps y fotogramas, SSIM 0.973 vs high. `/producir` la manda al usuario y
lanza `--sin-subir` (render alto + crítico, ~10 min) detrás; publicar sigue exigiendo la aprobación
del crítico sobre el MP4 final. Storyboard listo → preview en ~2.6 min; tema → preview sigue
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
