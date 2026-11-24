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

## Render por escena: diseño (PROPUESTA, pendiente de tu OK)

Medición que lo respalda: `docs/ESTADO.md`, "Render por escena" (23-nov). Un parche de 1 escena:
~16 min → ~2.5-3 min en el largo.

**Idea:** no guardar 85 trozos. Guardar el último render bueno (`<ref>-final.mp4` + su `index.html`)
y, tras un parche, re-renderizar solo las ventanas que cambiaron y empalmarlas.

1. **Qué cambió (diff, no hash por escena).** `window.PLAN` (en `index.html`) lleva las listas con
   tiempos (`escenas`, `words`, `fotos`, `sonidos`, `transiciones`, `golpes`, ...). Se comparan la página
   nueva y la del último render entrada por entrada: cada entrada nueva o distinta marca su intervalo
   de tiempo; lo mismo para los elementos con `data-start` del DOM y para cada asset cuyo hash cambió
   (marca las ventanas donde se usa). **Cualquier otra diferencia** (escalares del PLAN, `motor.js`,
   CSS, una entrada sin tiempo deducible) → render completo, como hoy. Conservador a propósito.
2. **Ventanas.** Cada intervalo sucio se amplía a escenas enteras (`[inicio_i, inicio_{i+1})`, que ya
   cubre el solape de 0.02 s de las transiciones) y se funden las contiguas.
3. **Render del tramo.** Copia de la página quitando `<video>`/`<audio>` que no tocan la ventana (el
   resto del DOM se queda: `motor.js` lo necesita) + `hyperframes render -c <copia> --start a --end b`.
4. **Empalme.** ffmpeg: completo anterior `[0, a)` + tramos + completo `[b, fin)`, re-codificado con
   h264_nvenc (43 s medidos), mismo `--quality`. Audio: el del completo anterior por stream copy si
   ningún `<audio>`/`sonidos` cambió; si cambió, empalmar también el audio en PCM con el del tramo
   (medido idéntico, desfase fijo de 12 ms a compensar) y codificar AAC una vez.
5. **Dónde entra.** Solo en la puerta `render` de `producir.py` (líneas ~1189-1212): hoy es
   `render_reutilizable` (todo o nada); pasa a todo / nada / tramos. `render.json` guarda además la
   copia de `index.html` del render bueno. El crítico no cambia: sus rondas ya llaman a
   `producir.py --sin-subir --sin-critico`, así que heredan el ahorro. `qa.json` registra
   `render: {modo: "tramos", ventanas: [...], s}`.
6. **Red de seguridad.** Tras empalmar, SSIM de los frames a ±3 de cada corte contra el render anterior
   en la parte NO tocada (medido: ≥ 0.99); si baja de 0.98, render completo. Y el crítico vuelve a medir
   el MP4 final entero, como siempre.

**Riesgos y límites (medidos o declarados):**

- Cada tramo paga ~60-70 s fijos (audio 41 s, probe 9 s, npx 12 s). 5 escenas sueltas ≈ 5 × 1m45s: aún
  la mitad que un completo. Con > ~8 ventanas sueltas compensa el completo (umbral PROVISIONAL).
- El tramo ignora `--gpu` (sale libx264) y su captura BeginFrame falla y reintenta en screenshot (~3 s).
  No afecta al resultado: el empalme re-codifica con nvenc.
- Re-codificar el completo pierde un poco (SSIM 0.996 en lo no tocado, PSNR 53 dB): invisible, pero
  se acumula si se empalma ronda tras ronda. Máx. 2 rondas del crítico → máx. 2 generaciones.
- Medido solo en el largo. En un Short (~60 s) el completo dura poco: el ahorro será menor; medirlo.
- Sin medir: quitar también el audio de la copia (ahorraría ~41 s por tramo) cuando el audio no cambió.

**Implementación estimada:** ~150 líneas en `producir.py` (diff de PLAN/DOM, recorte, empalme) + tests
del diff con dos páginas de juguete. Hecho = una ronda real del crítico con parche de 1-2 escenas en el
largo: minutos medidos y SSIM en los cortes.

## Fuera de este plan (a propósito)

- Bajar la calidad del render o del OCR (`limit_side_len`, detector más ligero): ya se midió que
  pierde texto (19-nov).
- Renderizar en la nube: sin medir; solo si la tanda en tu PC no cabe.
