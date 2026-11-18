# Plan de velocidad de /producir (17-nov-2026)

Fuente: 3 agentes (perfil de 4 sesiones reales, auditoría del motor, investigación externa).
Scripts del perfil: scratchpad de la sesión (`an2.py`, `turns.py`), no versionados.

## Medido (media de berkshire-1999, strategy-underwater, huang-resigns, huang-exit sin cuelgue)

156 min y ~150 turnos por Short:

| Categoría                                                             | min | %   |
| --------------------------------------------------------------------- | --- | --- |
| Espera a procesos (producir/render/crítico), 10-14 corridas por vídeo | 70  | 45  |
| Espera al usuario (3-8 aprobaciones)                                  | 39  | 25  |
| Generación de Claude                                                  | 19  | 12  |
| Voz (heredoc edita storyboard + Kokoro recargado)                     | 10  | 7   |
| omega cli + publicar dentro de la sesión                              | 9   | 6   |
| Medios + otras                                                        | 9   | 5   |

- 25 de 45 corridas fallaron en puertas (proyecto: 59/123, 205 de 735 min).
- Turnos: solo 22 % creativos; 31 % vigilando logs, 11 % editando JSON con heredoc, 11 % ceremonia.
- Máquina pura por Short bien hecho: ~14 min. Render: 114 s. **El renderer no es el cuello.**

## Decisión técnica

Mantener HyperFrames (ninguna alternativa tiene medición que justifique migrar; el render es ~2 min).
Atacar: reintentos completos, puertas tardías, storyboard escrito a mano, vigilancia y aprobaciones.

## Trinquete de errores (base de la Fase 1): cada error ocurre UNA vez

Ya existe: `renders/corridas.jsonl` guarda la regla exacta que falla, `tools/resumen_corridas.py`
la agrupa por clase (`clase()`), `autoarreglo.py` arregla las mecánicas, `tests/test_cero_errores.py`
reproduce cada defecto en un fixture. Falta cerrar el ciclo:

1. **Registro versionado** `video-v2/motor/errores.json`: clase de error → `{estado, donde, test, desde}`.
   Estados: `imposible` (el compilador ya no puede generarlo), `prevenido` (chequeo estático antes de
   la voz que lo corrige solo), `autoarreglo` (parche mecánico), `abierto`.
2. **Error nuevo = parada**: si una corrida falla con una clase que no está en el registro,
   `producir.py` la añade como `abierto`, imprime `ERROR NUEVO` y para. `/producir` obliga a
   arreglar la causa ANTES de seguir con el vídeo, en este orden de preferencia: imposible >
   prevenido > autoarreglo, siempre con un test que lo reproduce primero.
3. **Test trinquete** `test_registro_errores`: falla si una clase no `abierta` no nombra una función
   y un test que existen, o si reaparece en `corridas.jsonl` después de su `desde` (regresión).
4. Métrica en `resumen_corridas`: errores repetidos tras su arreglo (meta 0) y minutos perdidos.

Límite honesto: un error de una clase NUNCA vista puede ocurrir una vez; lo que el sistema garantiza es
que no vuelve. Primeras entradas (del log): repetición de efectos, gancho oscuro, contraste, borde
social, ritmo, corte a media frase.

## Fase 1: quitar corridas fallidas y esperas (días)

1. Reintento desde la etapa que falló, no `producir()` entero (`producir.py` `producir_auto`).
2. Puertas estáticas ANTES de voz/render: repetición de efectos (rotar sfx solo), luma del gancho
   y del fondo medida al elegir el medio (opacidad del overlay calculada), corte a media frase,
   borde de texto social medido en layout, `huecos_estaticos` como bloqueo en `validar`.
3. Kokoro: worker persistente + comprobar CUDA en el venv; re-sintetizar solo frases cambiadas.
4. Social, ritmo y loudness en paralelo con el crítico.
5. Crítico en una pasada, sin rondas (ninguna ronda ganó a la ronda 0 en 11 proyectos).
6. Render: `looks` en vez de `high` y `--workers` según `npx hyperframes benchmark`.
7. Una sola orden `producir.py --auto` que corre todo y avisa al terminar: Claude no vigila logs.

Meta Fase 1: 1 corrida por Short, ~15 min de máquina.

Medido 18-nov (escenario real E4, `strategy-underwater`, `--auto --sin-subir`, n=1, PROVISIONAL):

- Antes: 21,7 min (1301 s), 2 rondas y salida 1 (L1 y C2 sin arreglo). Después: 16,4 min (986 s),
  1 corrida y salida 0. No aislado: el crítico de "después" dio 0 fallos y el de "antes" dio 2.
- Kokoro (torch `+cpu`, sin CUDA), CPU libre: cargar el modelo tarda 16 s (import 13,5 s +
  pipeline 2,5 s) y sintetizar una frase de ~10 palabras unos 4,5 s. El worker persistente paga la
  carga una vez por corrida.
- Render `high` (lo que ya usa el motor): con `--workers auto` el motor ya elige 4. Con caché
  caliente: auto 81 s, 4w 74 s, 6w 73 s, es decir, ruido. El primer render en frío tardó 120 s.
  `looks` (CRF 16): 74 s, un 17 % más ligero y SSIM 0,9936 contra `high`. No hay ganancia de
  tiempo, así que **el punto 6 se descarta: se queda `high` con workers en auto**.
- Faltaban unos 850 s de los 986: `corridas.jsonl` solo guardaba la última ronda de `--auto`
  (`qa.json` se sobrescribe). Ahora suma todas las rondas y guarda el detalle en `rondas`.
- Corrida limpia, `strategy-underwater` actual (no el escenario E4): 6,8 min (410 s), 1 ronda y
  407,6 s registrados. Render 132 s, ritmo 111 s, social 60 s, loudness 49 s. El crítico (221 s)
  corre en paralelo. Con una corrida que pasa a la primera, la meta de 15 min se cumple.
- En la corrida de 986 s, la ronda 2 (reintento por `social`, con render y crítico en caché) costó solo
  138 s. La ronda 1 costó unos 848 s, el doble de una corrida limpia, y no se sabe por qué (los
  datos de esa ronda no se guardaron). Ahora `rondas` lo registra si vuelve a pasar.
- El carrusel social se hace en paralelo con el render, y después solo la historia: 410 s → 384 s
  (6,4 min), social 60 s → 28 s, render 132 s → 135 s (sin freno visible). n=1.
- Ritmo en paralelo con loudness: descartado. 384 s → 379 s (ruido): esas dos bajaron de 160 a 72 s,
  pero social subió de 28 a 111 s. Tras el render, el camino crítico es el crítico (~203 s, en
  paralelo): lo que corre a su lado solo se reparte la CPU. La siguiente palanca es el propio crítico.
- OCR del crítico: 6 procesos × 12 hilos de onnxruntime (su valor por defecto) en 12 núcleos.
  Limitado a `núcleos // procesos` hilos por proceso: crítico 203 s → 121 s y corrida 384 s → 301 s
  (5,0 min), mismo informe (0 fallos, 100 % leído). A solas, el crítico baja de 212 a 96 s.

## Fase 2: brief → compilador (1-2 semanas)

Claude escribe solo un brief (~400 tokens): guion, cifras con URL, ~10 beats
`{frase, dato?, concepto_medio, prueba?}`. Código compila el storyboard entero con las `m_*`
existentes de `construir.py`: anclas desde la alineación, golpes/calientes desde cifras, sfx por
tipo de escena, mood, rótulos, social y publicación por plantilla, tipo de escena por la regla de
variedad. Medios desde biblioteca local ya revisada (`visto`); solo un concepto nuevo pide hoja.

Meta Fase 2: ~25-30 turnos, 20-30 min tema → preview.

## No se pierde (medido o codificado)

Alineación forzada, reparación V1 de pausas, ducking M1, -14 LUFS / pico < -1 dBTP, ritmo ≤ 2,5 s,
gancho C1, contraste WCAG AA, OCR de clips (marcas/tickers), prueba documental con OCR, cifras con
URL + aviso YMYL, puerta `repeticion`, aprobación del crítico sobre el SHA del MP4 final.

## Verificación

Cada fase se mide en un Short real: minutos de reloj y turnos (`costo.json`) y corridas
(`tools/resumen_corridas.py`). Calidad: nota a ciegas del usuario vs un Short previo (POLITICA.md).
