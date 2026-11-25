# Plan de velocidad: todo el paquete del día (23-nov)

Meta del usuario: cuando diga "haz lo de hoy", **todo** (Short + vídeo largo + carrusel + historia)
listo para aprobar en **< 15 min de su tiempo**, y el tiempo total de máquina lo más bajo posible.

## Línea base (medida, no estimada)

Fuente: 123 corridas de `video-v2/*/renders/corridas.jsonl` (13 vídeos) + 23 `critica/informe.json`.

| Qué                                    | Medido                                                            |
| -------------------------------------- | ----------------------------------------------------------------- |
| Máquina por Short (todas sus corridas) | **~57 min** de media (25-135), ~10 corridas por vídeo             |
| Corridas fallidas                      | **205 de 735 min (28 %)**                                         |
| De ellas, `--auto` sin arreglo         | **147 min**: el crítico bloquea con algo que no sabe parchear     |
| Corrida completa de un Short (ok)      | mediana 631 s: render 109 s; crítico 220-656 s en paralelo        |
| Fallos que bloquean (sev. alta)        | 9 L1 "no se lee" (OCR) · 5 L1 contraste en píxel · 2 L1 DOM · 1 J |
| Claude + herramientas por Short        | ~13 + ~15 min (12-nov)                                            |
| Vídeo largo (7.4 min)                  | previo 12-16 min (contraste ~600 s) + render 14 + crítico ~9.5    |

Conclusión: el tiempo no se va en un paso lento, se va en **repetir**. Un Short corre ~10 veces;
casi un tercio de la máquina se tira en corridas que fallan.

## Por qué hacen falta dos cosas

1. **Tanda previa** (sección C): el render del largo solo ya son 14 min. Sin producir antes, "lo de
   hoy" no cabe en 15 min, por rápido que sea todo lo demás.
2. **Menos máquina** (secciones A y B): la tanda tiene que caber en una sesión razonable.

## A. Dejar de repetir (lo que más ahorra)

| #   | Cambio                                                                                                                                                     | Ahorro esperado               | Cómo se valida                                                                          |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | --------------------------------------------------------------------------------------- |
| A1  | Volver a pasar el crítico por los 23 informes con el OCR sin cls (f9f9bdc): ¿cuántos de los 9 L1 "no se lee" eran lecturas giradas?                        | parte de los 147 min          | mismo informe sin cls vs con cls; cada L1 que desaparezca, mirar su fotograma           |
| A2  | Los L1 "no se lee" que queden: si caen en la entrada animada (texto aún moviéndose), juzgar solo cuando el texto ya está quieto                            | el resto de los L1 falsos     | fotogramas mirados: el texto se lee a ojo; ningún L1 real desaparece en los 23 informes |
| A3  | Contraste en píxel (5 bloqueos): la puerta del previo ya lo mide; ver por qué no lo cazó antes del render                                                  | 1 ronda (~10-20 min) por caso | los 5 casos pasan a fallar en el previo, no en el crítico                               |
| A4  | Fallos `storyboard`/`repeticion` (26 corridas, ~3 min de máquina pero 1 turno de Claude cada una): validar el storyboard mientras se escribe, no al lanzar | turnos de Claude              | 0 corridas que mueren en la puerta estática                                             |

Objetivo A: corridas fallidas de **28 % a < 10 %**; Short de ~10 corridas a **≤ 3**.

## B. Lo que queda, en paralelo

| #   | Cambio                                                                                     | Ahorro esperado      | Riesgo / validación                                                 |
| --- | ------------------------------------------------------------------------------------------ | -------------------- | ------------------------------------------------------------------- |
| B1  | Crítico: OCR (GPU) a la vez que Whisper, parecido, ritmo y grises (CPU)                    | ~3-4 min por ronda   | mismo `informe.json` que en serie                                   |
| B2  | Whisper de la voz limpia cacheado por hash de `voice.mp3` (no cambia entre rondas)         | ~32 s por ronda      | misma transcripción                                                 |
| B3  | Largo: contraste del previo (~10 min) a la vez que el render, sin esperar                  | ~10 min              | si el contraste falla, se tira ese render: medir cuántas veces pasa |
| B4  | Varios Shorts de la tanda: el render de uno mientras el crítico (CPU/GPU) mide el anterior | ~30-40 % de la tanda | que no se pisen en la GPU: medir con 2 a la vez                     |

## C. Tanda previa ("lote")

- Una orden que **tú lanzas** (nada corre solo en tu PC) y produce N paquetes completos: guion →
  voz → previo → render → crítico → carrusel → historia, con `--auto`.
- Lo que no se arregla solo queda en una lista de pendientes, **sin bloquear** los demás paquetes.
- "Haz lo de hoy" = te enseño el paquete ya hecho (vídeo, carrusel, historia, crítico) → apruebas →
  publico. **Objetivo: < 15 min.**
- El vídeo largo entra en la tanda según la cadencia que elijas (por ejemplo, 1 por semana).

## Orden y criterio de "hecho"

1. **A1 → A2 → A3** (barato, es lo que más ahorra). Hecho = re-medir los 13 vídeos: % de corridas
   fallidas y fallos que bloquean, antes vs después.
2. **C** (la tanda). Hecho = una tanda real de 3 Shorts + 1 largo sin que intervengas, y "lo de hoy"
   cronometrado en < 15 min.
3. **B1-B4**, cada uno medido solo (una variable a la vez).
4. **A4**, si los turnos de Claude siguen pesando.

Metas: máquina por Short **57 → ≤ 25 min**; largo **60-80 → ≤ 35 min**; tu tiempo diario **< 15 min**.
Todas son PROVISIONALES hasta medirlas en la tanda real.

## Render por escena: IMPLEMENTADO (24-nov, `video-v2/motor/tramos.py`)

Medición: `docs/ESTADO.md`, "Render por escena". Parche de 1 escena en el largo: **175 s** de reloj
contra 13-21 min del completo; fuera del tramo, igual que dos completos entre sí.

Cómo funciona, en la puerta `render` de `producir.py` (`render_por_tramos`), cuando la página cambió:

1. **Qué cambió.** Compara `index.html` con la copia del último render bueno
   (`renders/render-index.html`) y los hashes de los assets (`render.json`). Cada elemento con
   `data-start` ocupa una línea (así lo escribe construir): una línea distinta marca su intervalo. En
   `window.PLAN`, cada entrada de lista distinta marca el suyo (`t0/t1/start/end/en/t/marca/dur`). Un
   asset cambiado marca dónde se usa. **Render completo** si cambia cualquier otra cosa (CSS, `motor.js`,
   un escalar del PLAN, una entrada sin tiempo como `calientes`), **cualquier audio** (`<audio>`,
   `sonidos`, `sfx_mezcla`, volúmenes, voz), otra versión de HyperFrames, o el final ya no es el del
   último render. El motivo se imprime (`· render completo: ...`).
2. **Ventanas.** Intervalo ±1 s → escenas enteras, contiguas fundidas. Más de 8 ventanas o más de la
   mitad de la película → completo.
3. **Tramo.** Página copiada sin `<audio>` y sin `<video>` fuera de la ventana (`renders/` no cuenta
   para el tope de 2 GiB de HF: comprobado con el final de 878 MB dentro) + `render -c _tramo.html
   --start --end`.
4. **Empalme.** Final anterior + tramos, re-codificado con h264_nvenc (libx264 con `PRODUCIR_SIN_GPU`);
   audio copiado del final anterior, ya normalizado, así que no se repite loudnorm. Se comprueba el
   número de frames de cada tramo y del resultado; cualquier fallo → render completo.

`--completo` lo fuerza. El crítico no cambia: sus rondas llaman a `producir.py --sin-subir
--sin-critico` y heredan el ahorro.

**Cambios frente a la propuesta:** con audio cambiado no se empalma el PCM, se hace el completo (más
simple, y el audio hay que normalizarlo entero). Sin la "red de seguridad" de SSIM en los cortes: los
cortes caen en bordes de escena, donde la imagen cambia de todos modos, así que esa medida no detecta
nada; la red real es el crítico, que vuelve a medir el MP4 entero.

**Límites:**

- Cada tramo paga ~60-70 s fijos. 8 ventanas ≈ un completo (umbral PROVISIONAL).
- Cada empalme re-codifica: máx. 2 rondas del crítico → máx. 2 generaciones (SSIM 0.996 por pasada).
- Sin medir: un Short (el completo dura poco, ahorrará menos) y una ronda real del crítico de punta a
  punta (lo medido es la función sobre un parche simulado: texto de s40 + `fondo.opacidad`).

## Fuera de este plan (a propósito)

- Bajar la calidad del render o del OCR (`limit_side_len`, detector más ligero): ya se midió que
  pierde texto (19-nov).
- Renderizar en la nube: sin medir; solo si la tanda en tu PC no cabe.
