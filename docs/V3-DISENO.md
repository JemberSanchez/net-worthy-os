# Motor v3 — diseño (13-nov-2026)

Decisiones del usuario (entrevista del 13-nov): calidad de nivel anuncio (referencia: ElevenLabs),
mucho más rápido, más creativo, guion más viral, **cero fallos de raíz**. Presupuesto: gratis.
"Mejoras reales, no cosas simples".

## Principio

**Separar la creatividad (antes, sin reloj) de la fabricación (después, rápida y sin fallos).**
Un fallo no se corrige: se vuelve imposible (regla de plantilla + test). El crítico pasa a ser red
de seguridad, no el sitio donde se descubren los fallos.

## Evidencia (medida el 13-nov)

### Fallos: 229 en la ronda 0 de 20 informes del crítico (11,4 por vídeo)

| Código | Fallos | %   | Causa raíz                                                              | Arreglo de raíz                                                                              |
| ------ | ------ | --- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| L1     | 142    | 62  | `#caps` llegaba a x=1030 (base) y x=946 (editorial): columna de botones | **HECHO 13-nov**: caja dentro de x≤907, `tests/test_zona_segura.py`                          |
| V1     | 33     | 14  | Kokoro mete silencios dentro de frase (no determinista)                 | Tras alinear, re-sintetizar sola la frase con hueco > 0,4 s, antes del build (puerta de voz) |
| M1     | 20     | 9   | música o SFX colocados encima de la voz                                 | Mezcla por construcción: ducking con la envolvente de la voz del `.align.json`               |
| resto  | 34     | 15  | J1-J6 (juicio), P1 (parecido), A1, G1-G2                                | Plantillas v3 con tiempos del gancho fijos; catálogo variado                                 |

Con L1, V1 y M1 resueltos por construcción desaparece el **85 %** de los fallos de ronda 0.
Pendiente: L1 de textos de escena (no subtítulos) — medirlos tras el próximo vídeo; si quedan,
misma regla en cada plantilla v3.

### Retención real (15 Shorts, score v4)

Bajó: ~34-47 % (30-oct a 5-nov) → 32 % (6-8 nov) → **19 %** (10-11 nov). Ganchos mejores:
midterm-rally (cifra + contraste concreto), ronald-wayne ("for the price of your phone"),
jesse-livermore. Peores: hot-inflation y holiday-debt abren con algo abstracto ("The government
agency that…", "Half of America says…"). **Hipótesis, n=15, temas distintos: no es regla.**

### Escenas v2 usadas (319 escenas, 22 storyboards)

`foto` 148 (en los 22) · `titulo` 108 · `revelacion` 14 · `lista` 12 · `cta` 12 · `contador3d` 9 ·
`grafica` 6 · `anios` 4 · `puntos` 4 · `tarjetas` 2. **`foto` + `titulo` = 80 % de la pantalla.**

### Tiempo (sesión huang-exit, 69 min)

~40 min esperando procesos · ~15 herramientas · ~13 Claude. Storyboard listo → preview 154 s.
Render alto 114 s + OCR del crítico ~200 s ≈ 5 min: suelo con la red completa.

### Bloques disponibles gratis

`hyperframes catalog` (v0.9.41): 448 bloques, 172 relevantes para cine: `camera-dolly-zoom`,
`cinemagraph`, `light-leak`, `organic-light-leak-overlay`, `cinematic-zoom`, `lens-flare`,
`data-chart`, `bar-chart-race`, `mk-progress-stat`, `mk-line-graph`, mapas animados, lower thirds,
21 bloques 3D, 52 transiciones. Reutilizar antes de construir.

## Fases

### Fase 0 — raíz de los fallos mecánicos (días)

1. ✅ L1 subtítulos (62 %).
2. V1: puerta de voz con re-síntesis de la frase (14 %).
3. M1: ducking por construcción (9 %).

**Hecho cuando:** el crítico de los 2 próximos vídeos da ≤ 3 fallos de ronda 0 (hoy 11,4).

### Fase 1 — velocidad y gancho (semana 1)

1. **Cola de temas**: lote fuera del reloj que deja 3-5 vídeos listos hasta la voz (tema por
   `decide`, cifras con fuente, 3 ganchos, guion, medios con licencia, voz alineada).
2. **Ganchos**: `guionista.py` genera 3 por tema y elige por patrones medidos (top del nicho +
   nuestros ganadores). Regla dura candidata: primera frase concreta (persona, cifra o objeto).
3. Kokoro persistente (medir antes/después).

**Hecho cuando:** tema aprobado → preview < 5 min, medido en 2 vídeos.

### Fase 2 — piloto cinematográfico (semana 2)

Escena piloto: **`foto` v3** (la más usada: 148 escenas). Foto real → capas de profundidad
(mapa de profundidad local, CPU/GPU 4 GB) → parallax 2.5D con movimiento de cámara, luz y grano
→ tipografía cinética dentro de la zona segura → transición motivada.

**Aceptación (todas):**

- Gana a ciegas a la `foto` v2 en ≥ 4 de 5 pares (mismo tema, misma voz).
- Render ≤ +20 % frente a v2 por segundo de vídeo.
- 0 fallos L1 / contraste por construcción (tests de plantilla).

Si no gana, no se construye el resto: se cambia el enfoque.

### Fase 3 — catálogo v3 (semanas 3-4)

`titulo` v3 (tipografía cinética) → `revelacion`/`contador3d` (3D con luz) → `grafica`
(`data-chart`/`bar-chart-race`). Cada plantilla: zona segura, tiempos y contraste con test.
3-4 looks por tipo de historia (biografía, noticia, error común, dato) sobre identidad fija.
v2 publica en paralelo hasta que v3 le gane medido.

## Medidas de éxito

1. Retención real ≥ 35 % (hoy 19 % en los últimos 5) — juez final.
2. Nota a ciegas del usuario: v3 gana ≥ 4 de 5.
3. Fallos de ronda 0 ≤ 3 por vídeo; ninguno repetido (cada uno nuevo → test).
4. Tema → preview < 5 min.

## Límites conocidos

- Vídeo generado por IA (el look de ElevenLabs/Veo/Kling) no es viable gratis con 4 GB de VRAM:
  el nivel sale de metraje real + 2.5D/3D + movimiento + sonido.
- < 5 min hasta el MP4 final con crítico completo no es alcanzable hoy (render + OCR ≈ 5 min).
