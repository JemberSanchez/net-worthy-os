# Arquitectura multi-escena — del Short a los 8-10 min

> Estado (2026-07-10): la **base está construida y verificada**. El motor pasó de "una escena por
> Short" a "una escena base + overlays componibles". Lo que falta para long-form real está listado
> abajo, en orden, con el porqué de que esté aplazado.

## El modelo

Un vídeo se compone de **escenas**. Cada escena es una función pura `dibujar(t, W, H, s, alpha, opts)`
que pinta sobre el canvas. `drawFrame(t)` sigue siendo **pura** (mismo `t` → mismos píxeles): es el
contrato del exportador MP4, que re-renderiza offline frame a frame. **Verificado por comparación de
píxeles** en cada cambio.

```
SCENES = { chart, columns, titulo, outro, … }     // registro: añadir escena = añadir entrada aquí
```

Cada Short declara:
- `escena`  — la **escena base**, que corre toda la voz (`chart` = curva del S3, `columns` = S1).
- `overlays[]` — escenas superpuestas con ventana de tiempo `{escena, desde, hasta, fadeIn, fadeOut, …opts}`.
  `desde/hasta` pueden ser segundos o funciones de `T` (se mueven con la calibración de la voz).

El compositor (`drawFrame`) dibuja la base y encima cada overlay activo con su alpha de ventana. Como
el overlay respeta una **alpha entrante**, se funde con la base **sin tocar el interior de la escena
base** — por eso `columns` y `chart` no se modificaron al añadir la portada.

### Ejemplo real (el S1)
```js
escena: 'columns',
overlays: [
  {escena:'titulo', desde:0, hasta:1.9, fadeOut:0.55,
   lineas:['TWO MEN.','SAME SALARY.'], sub:'same discipline.'},
]
```
→ portada 0–1.9s que tapa el llenado de barras y se **disuelve** en las columnas. No cambia ningún
corte de voz, así que no desincroniza nada.

## Cómo añadir una escena nueva (5 min)
1. Escribe `function drawX(t, W, H, s, a, ov){ … }` (respeta `a` como alpha; lee datos de `ov`).
2. Regístrala: `SCENES.miEscena = (t,W,H,s,a,ov) => drawX(t,W,H,s,a,ov)`.
3. Úsala como base (`escena:'miEscena'`) o como overlay en cualquier Short.
No se toca `drawFrame`. No se toca ninguna otra escena.

## Ya construido y verificado
- Registro de escenas + compositor de overlays (alpha por ventana, fundidos).
- Escenas: `chart` (S3), `columns` (S1), `titulo` (portada), `outro` (cierre de marca, reutilizable).
- Pureza de `drawFrame` mantenida (contrato del exportador) — probado en S1 y S3.
- El S3 publicado queda **idéntico** (pixel a pixel).

## Ruta a long-form (8-10 min) — en orden, con el porqué del aplazamiento

El cuello de botella NO es la arquitectura de escenas (ya está), son estas 4 piezas:

1. **Romper el muro de memoria (ffmpeg).** El exportador acumula todo el vídeo en RAM (a 14 Mbps,
   10 min ≈ 1 GB, pico 2-3 GB → la pestaña muere; techo real ~2-3 min). Solución estándar: renderizar
   **por segmentos** (cada uno un MP4 corto que cabe en memoria) y **concatenar con ffmpeg** (`-c copy`,
   sin recodificar). Requiere instalar ffmpeg (`winget install Gyan.FFmpeg`). Bonus: recomponer una
   escena no re-renderiza el vídeo entero.
2. **Timeline de segmentos con voz por segmento.** Para long-form cada segmento lleva **su propio clip
   de voz** (y así cada calibración es un guion corto — el régimen para el que el calibrador ya
   funciona; segmentar *facilita* los subtítulos). Distinto del Short, que usa una voz continua.
3. **Layout horizontal.** Hoy está cableado a 1080×1920 (Shorts). Long-form = 1920×1080: parametrizar
   `W×H` y la zona segura (ya casi todo se dibuja relativo a `W/H/s`).
4. **Biblioteca de escenas.** 8-10 min necesita ~8-10 tipos: portada (✓), divisor de capítulo, stat
   grande, bullets/puntos, cita, comparación (≈`columns`), lower-third sobre B-roll, cita de fuente,
   outro (✓). Es el grueso creativo.

**Por qué aplazado (no es un "no", es un "aún no"):** `POLITICA.md` congela el motor hasta que un
experimento publicado revele una limitación; el S1 aún no se ha medido; y con **0 suscriptores el
algoritmo no empuja long-form** (se construiría capacidad que nadie ve todavía). La base multi-escena,
en cambio, **paga ya** porque mejora los Shorts (que son el alcance real). Cuando el canal demuestre
tracción, el long-form es una **extensión** de esto, no un motor nuevo.

## Nota: post-roll (outro al final de un Short)
La escena `outro` está lista, pero encadenarla DESPUÉS de la voz de un Short necesita dos cosas
pequeñas: (a) extender `T.total` con silencio de cola; (b) que `reproducir()` pase a reloj de pared
cuando el audio acaba (hoy el reloj lo manda `audioEl.currentTime`, que se congela al terminar la voz —
es el bug del bucle infinito ya documentado). El export MP4 (frame-driven) no sufre esto; solo el
preview. Es un follow-up de ~10 líneas cuando se quiera un cierre post-voz.
