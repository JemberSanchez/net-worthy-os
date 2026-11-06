---
description: Producción diaria de un Short v2 de punta a punta (tema → guion → storyboard → render → QA → preview). NO publica sin aprobación.
---

Produce el Short de hoy con el motor v2. Español al usuario; contenido del canal en inglés. Una sesión por vídeo.
`CLAUDE.md` ya está cargado. El catálogo de escenas está en `video-v2/motor/README.md`: `Grep`, no `Read` entero;
storyboards igual (copia la forma de `video-v2/read-janitor/storyboard.json` con un extracto). Las puertas dicen
qué falla: corrige la causa, nunca un umbral. Si algo se resiste dos rondas, para y pregunta si ya está resuelto.

## 0. Estado

1. `bash tools/setup_nube.sh`. Si falla, para y reporta.
2. `python -m omega.cli estado-bajar` (sin `ESTADO_REPO`, PARA: `decide` iría a ciegas). Luego `analytics-sync` y
   `meta-sync`: "sin datos aún" es normal; un ✗ de permisos se reporta pero no para. Anota dónde cae la curva y las búsquedas.

## 1. Tema

3. `/daily`. Tema = ganador de `decide`, convertido en explainer (el término crudo es un QUÉ). Descarta si ya existe
   (`ls video-v2/`) o no hay datos verificables, y dilo. Una búsqueda real de `analytics-sync` que encaje gana el empate.

## 2. Guion (inglés, 85-110 palabras ≈ 27-35 s)

4. Alterna formato noticia/personaje con el último publicado. Elige una estructura distinta de la anterior: contradicción,
   misterio, error común, cuenta atrás o vida de personaje. Frases cortas (cada una es un ancla); la parte honesta
   (riesgo, sesgo de superviviente) es obligatoria, sin fórmula de anuncio. Open loop que se cierra tarde, giro propio
   cada 8-10 s, última frase que enlaza con la primera. Cada cifra con URL en `cifras`; sin verificar, no se usa. Nada de
   consejo personalizado; curvas ILUSTRATIVAS y se dice.
5. Escribe `video-v2/<ref>/guiones.json` (2-3 estructuras, 3-5 ganchos) y corre `python video-v2/motor/guionista.py video-v2/<ref>`:
   sus puertas (G-GANCHO, G-TU, G-CIFRAS, G-COMODIN, G-CIERRE, longitud, relleno) dicen qué reescribir, y pide tu juicio 1-5.
   No juzgues para salvar una alternativa. Ganador al `guion` del storyboard; descartadas en `guiones.md`.

## 3. Storyboard (`video-v2/<ref>/storyboard.json`)

6. Primero la voz, con solo `guion`: `python video-v2/motor/voz.py video-v2/<ref>`. Hace hasta 3 tomas; si sale con ✗, reescribe la frase que señala y repite con `--forzar`. Lista las frases: las anclas se
   escriben contra sus palabras exactas ("—" es una palabra; "seventy-five" va con guion).
7. Decisiones que las puertas no toman por ti:
   - Medios: reutiliza primero `video-v2/*/assets/` + su `creditos.json`. Una búsqueda por concepto, sin bucles:
     `python tools/imagenes_libres.py buscar "<q>"` (objetos y lugares, nunca personas ni fotos de prensa),
     `python tools/broll.py buscar pexels|commons "<q>"`. ≥3 imágenes en `imagenes`, ≥4 clips en `clips`, uno en el gancho (0-3 s).
     Sin caras reconocibles, logos ni noticias con personas: `python tools/broll.py lote video-v2/<ref>` deja `assets/clips/<n>.hoja.jpg` e imprime el
     texto que el OCR lee en cada clip (billetes de otro país, tickers, marcas). Mira cada hoja y solo entonces pon `"visto": true`: sin él `construir` rechaza el clip.
     Metraje histórico con `"duotono": true`; documentos con `"documento": true`.
   - Música: `"musica": {"pista": {"mood": "tension|oscuro|documental|reflexivo|urgente|neutro"}}`.
   - Edición: no escribas `mov`; `"cam"` o `"transicion"` solo para fijar algo. `--reelegir` en `construir.py` repite la elección.
   - Sonido: 4-7 efectos de `video-v2/motor/sfx.json`, solo si casan con lo que se ve (`"sfx"` en clip, `"sonidos"` en palabras).
   - Prueba: documento REAL que diga el dato, en `pruebas`, con la frase tal cual (`python tools/ocr_doc.py assets/t/<img>.jpg "<frase>"`).
   - Serie: `"serie": {"nombre": "Quiet Millionaires", "ep": N}` si es de gente corriente rica en silencio.
   - Nada genérico: metraje, documento o dato real. `"desde_anio"` solo con año verificado, si no "Yr N". Como mucho un `contador3d`.
   - Subtítulos sin gancho ni CTA; la `pregunta` del CTA antes que los `botones`.
   - `publicacion` (título ≤100, descripción, tags, hashtags; sin dicotomía, `comentario`); `adn` con `renderer_version: v2-hyperframes`.
   - `social` (formato en `motor/social.py`): 5-7 diapositivas con fondo real, portada con el gancho, última con la pregunta.

## 4. Comprobar y producir

**Siempre en segundo plano** (`run_in_background`): el aviso llega solo. Nada de `tail`, `sleep` ni `Monitor`.

8. `python video-v2/motor/producir.py video-v2/<ref> --previo`: todas las puertas estáticas a la vez, build, lint, contraste,
   hoja de contactos, texto sobre documentos y carrusel. Un ⚠ de L1 solo avisa: mira ese segundo en la hoja. Mira la hoja que imprime (solapes, textos que no caben, imagen = palabra). Agrupa todos los
   arreglos y repite; nunca renderices con un defecto visible en la hoja.
9. `python video-v2/motor/producir.py video-v2/<ref> --sin-subir`: render (3-4 min), loudness, ritmo, preview, carrusel e historia, y
   medidores del crítico, que sigue siendo la red final. Imprime solo fallos, con segundo y escena. No sube: lo hace `publicar` en el paso 13.
10. **Juicio** sobre `renders/critica/r0/hoja.jpg` (no fotogramas sueltos, salvo para dudar de un segundo): escribe
    `renders/critica/r0/juicio.json` con J1-J6 y el `mp4_sha256` que da `juicio.md` (gancho, imagen = palabra, exactitud contra
    la fuente, cierre). Luego `python video-v2/motor/critico.py video-v2/<ref> --mp4 video-v2/<ref>/renders/critica/r0.mp4`
    escribe `aprobacion.json`, que exige publicar. Arregla la causa de un fallo `alta` en el storyboard y vuelve al paso 8.
    Rondas automáticas solo si se piden (`--rondas 2`): ninguna ganó a la ronda 0 en 11 proyectos.

## 5. Entregar y PARAR

11. `python -m omega.cli estado-subir` y `python -m omega.cli produccion-guardar video-v2/<ref>`.
12. SendUserFile con la preview y un resumen corto: tema y por qué ganó, guion, fuentes, puertas (`renders/qa.json`), fallos del
    crítico, título y descripción. Pide la nota a ciegas (1-10 + queja con segundo). **PARA.** No publiques sin aprobación
    explícita en esta sesión.

## 6. Solo si el usuario aprueba

13. `python -m omega.cli publicar <ref>` muestra el plan (estado de cada red, crítico). Con confirmación explícita para Meta,
    `publicar <ref> --publicar` sube y programa YouTube (12:00 Nueva York; `--hora`, `--ahora`), Facebook, Instagram (sale al
    momento) y páginas. Si una red tiene un render anterior, para: dilo al usuario, que lo borre a mano, y usa `--reemplazar <red>`.
14. `python -m omega.cli record-dna video-v2/<ref>/adn.json`; `record-cost` con
    `{"production_ref": "<ref>", "research_hours": null, "script_hours": null, "edit_hours": null, "ai_cost_usd": null, "time_to_publish_h": null}`
    (solo valores medidos, si no `null`); `estado-subir`.
