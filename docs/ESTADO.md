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
