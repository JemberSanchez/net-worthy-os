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
