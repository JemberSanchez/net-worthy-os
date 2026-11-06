---
description: Producción diaria de un Short v2 de punta a punta (tema → guion → storyboard → render → QA → preview). NO publica sin aprobación.
---

Produce el Short de hoy con el motor v2. Responde en español; el contenido del canal, en inglés.
Lee `video-v2/motor/README.md` solo si no lo tienes (catálogo de escenas y anclas). `CLAUDE.md` ya está
cargado: no lo releas. Storyboards: `Grep` o un extracto, no `Read` entero (44 KB).

## 0. Entorno y estado (sesión nueva en la nube)

1. `bash tools/setup_nube.sh` — idempotente. Si falla, para y reporta qué paso y su salida.
2. `python -m omega.cli estado-bajar` — si falta `ESTADO_REPO`, PARA: sin la base, `decide` no
   tiene historia y el tema saldría a ciegas. Reporta qué secreto falta.
   Después, `python -m omega.cli analytics-sync` y `python -m omega.cli meta-sync`: mide los vídeos ya publicados (curva de
   retención, fuente de tráfico, búsquedas) y re-puntúa sus outcomes. "Sin datos aún" o "aún
   privado" es normal (Analytics va ~2-3 días tarde); un ✗ de permisos se reporta pero NO para la
   rutina. Guarda del resumen: el punto de la curva donde más cae y las búsquedas que trajeron gente.

## 1. Qué contar (el sistema decide, no el gusto)

3. `/daily`: `ingest`, `youtube-scan`, `signals`, `decide`. Si un paso falla por red (dominio no
   permitido), anota el dominio exacto y sigue con los demás.
4. Tema = ganador de `decide`. Regla dura: el término crudo es un QUÉ, no un vídeo → conviértelo en
   un explainer. Descarta si ya existe un proyecto con ese tema (`ls video-v2/`) o si no hay
   datos verificables para contarlo: en ese caso toma el siguiente de la lista y dilo.
   Si `analytics-sync` mostró búsquedas reales que encajan con un candidato de `decide`, ese
   candidato gana el empate (demanda medida en NUESTRO canal > demanda estimada). Dilo en el resumen.

## 2. Guion (inglés, 85-110 palabras ≈ 27-35 s con Kokoro — medido 26-sep: 85 palabras = 27,5 s)

5. **Formato según el calendario** (`docs/VIRALIDAD.md` §7): alterna noticia y personaje atemporal;
   mira el `formato` del último publicado y no lo repitas. Cada guion usa UNA estructura de esta lista,
   distinta de la del vídeo anterior (no existe una plantilla fija):
   - **contradicción**: dos hechos que no deberían ir juntos → la causa → qué significa para ti;
   - **misterio**: resultado raro → qué nadie entendía → revelación tardía;
   - **error común**: lo que casi todos leen mal → la lectura correcta → qué cambia para ti;
   - **cuenta atrás**: la secuencia en orden, con la decisión clave al final;
   - **vida de personaje**: quién era → la decisión → el precio o el premio → qué te llevas tú.
     Frases cortas: cada frase es un ancla. La parte honesta (riesgo, sesgo de superviviente) sigue
     siendo obligatoria, sin fórmula de anuncio. Técnicas de retención (la curva cae entre 3 s y 20 s;
     en `aws-profit`, de 0,90 a 0,33 entre los segundos 5 y 11, donde va el repaso de la noticia):
   - **Gancho que se entiende sin contexto** (puerta G-GANCHO): un sujeto concreto y una tensión. La
     cifra es opcional. PROVISIONAL (n=5, ver `docs/mejora/guion/linea_base.md`): la cifra SOLA retiene
     menos que la cifra con contraste; sin cifra no hay ningún vídeo con ≥30 vistas para comparar.
     Nada de empezar por el número, siglas ni nombres sin explicar. Nada de "hoy vamos a…".
   - **Qué gana o pierde el espectador antes de la palabra 19** (≈6 s, puerta G-TU): di "you/your".
   - **Máximo 3 cifras dichas** (G-CIFRAS): el resto va en pantalla o se quita. Nada de repasar la
     noticia con una ristra de datos.
   - **Sin frases comodín** (G-COMODIN, lista cerrada en `guionista.py`): nunca "here's the part nobody
     tells you"; estaba en 7 de 10 guiones.
   - **Cierre distinto** (G-CIERRE): dicotomía, pregunta, imperativo, dato o afirmación; el tipo no puede
     repetir ninguno de los últimos 3 vídeos publicados. La dicotomía ya no es obligatoria; 8 de 10
     la usaban. Sin dicotomía, el comentario fijado va en `publicacion.comentario`.
   - **Open loop**: la primera o segunda frase abre una pregunta que se cierra tarde. El espectador
     se queda por la respuesta.
   - **Re-gancho cada ~8-10 s**: un giro PROPIO de esta historia o una cifra nueva. Nunca una
     fórmula de giro reutilizable: la puerta `repeticion` falla si una frase de 4 palabras se repite
     en los últimos 10 vídeos. El validador avisa si pasan >12 s sin golpe.
   - **Final en bucle**: la última frase enlaza con la primera, para que la repetición
     suene continua (una vista repetida sube el % visto por encima de 100 %).
   - Ritmo de voz 150-175 palabras/min; nada de frases de relleno ("so basically", "you see").
6. **Cada cifra con fuente** (URL en `cifras`). Si no puedes verificar un número, no lo uses. Nada
   de consejo financiero personalizado; las curvas son ILUSTRATIVAS y se dice.
   6b. **Alternativas, no un guion único (bloque 1.1, PROVISIONAL).** Escribe `video-v2/<ref>/guiones.json`
   con 2-3 estructuras completas de la lista del paso 5 y 3-5 ganchos, y corre
   `python video-v2/motor/guionista.py video-v2/<ref>`: aplica las puertas medibles (G-GANCHO, G-TU,
   G-CIFRAS, G-COMODIN, G-CIERRE, 85-110 palabras, relleno, giro cada ≤10 s, final que retoma la
   1.ª frase) y pide tu juicio 1-5 (una idea, pregunta abierta, giro) de cada candidato.
   `producir.py` repite esas puertas sobre el guion final (`guion`; exento lo ya publicado o renderizado).
   Si una puerta falla, reescribe la alternativa (no la juzgues para salvarla). Escribe el ganador en
   el `guion` del storyboard y deja `guiones.md` con las descartadas: enséñaselas al usuario.
   Referencia: `video-v2/housing-turn/` (plantilla congelada vs. elegido, par ciego con `--ciego`).

## 3. Storyboard (`video-v2/<ref>/storyboard.json`)

7. Copia la forma de `video-v2/read-janitor/storyboard.json`. Reglas:
   - un cambio visual cada ≤2,5 s (una escena por frase, o sub-anclas dentro de la escena);
   - ≥3 imágenes reales: `python tools/imagenes_libres.py buscar "<q>"` (Commons, solo PD/CC0/CC BY;
     UNA búsqueda por concepto, sin bucles: la API limita por IP). Nunca fotos de prensa de
     personas reales. Declara cada imagen en `imagenes` con su `commons`;
   - **≥4 clips de vídeo (b-roll)**: uno SIEMPRE en el gancho (0-3 s); el resto se usan solos como
     fondos en movimiento de las escenas de texto. Metraje moderno: `python tools/broll.py buscar
pexels "<q>"` (sale en COLOR con el grado de marca); histórico: `buscar commons` (o
     `"duotono": true` en el clip para que case con fotos de archivo). Declara en `clips` (`{"commons": "File:X.webm", "desde": s}`
     o `{"pexels": id, "desde": s}`) y usa `"clip": "<nombre>"` en lugar de `"img"` en esa `foto`
     (o en un `fondo`). Antes de fijar `desde`, mira UNA hoja de miniaturas
     (`ffmpeg -i assets/clips/<n>.src -vf "fps=1/2,scale=192:108,tile=8x2" -frames:v 1 hoja.jpg`):
     objetos/manos/lugares sí; caras reconocibles, logos o noticias con personas reales, no;
   - **Música real:** `"musica": {"pista": {"mood": "tension"}}` (tension, oscuro, documental, reflexivo,
     urgente, neutro): `construir.py` elige de `motor/musica.json` una pista no usada en los últimos
     vídeos (la política de "contenido inauténtico" castiga plantillas idénticas). Sin `mood` puede
     salir cualquiera. Para fijar una: `{"commons": "File:X.ogg", "desde": s}` (manda sobre `mood` y
     cuenta para la puerta; catálogo: `python tools/musica_libre.py buscar "<q>"`). Certificados y
     periódicos en `imagenes` llevan `"documento": true` (sin parallax 2.5D).
   - **Edición sin repetir (5-nov, `video-v2/motor/README.md`):** en un vídeo nuevo `construir.py` elige
     transiciones, cámara, punch, entrada de texto, efectos y pista evitando los últimos 3 vídeos
     (`video-v2/usado.json`, puerta P1 `repeticion`). **`mov` se ignora en vídeos nuevos**: no lo
     escribas; para fijar el movimiento de una escena usa `"cam"` (y `"transicion"`, o `"corte"`, para
     su transición). Lo fijado a mano cuenta para la puerta. La elección queda congelada al construir;
     si la puerta salta o quieres otra, `python video-v2/motor/construir.py video-v2/<ref> --reelegir`.
   - **Sonido real sincronizado (27-sep):** 4-7 efectos del catálogo `video-v2/motor/sfx.json`
     (grabaciones reales, no whoosh genéricos): `"sfx"` en el clip que SE VE (máquina de escribir
     en un clip de máquina) y `"sonidos"` para golpes en palabras (caja en la cifra del gancho,
     página/sello cuando entran documentos, reloj bajo "X years later", monedas en el payoff).
     Solo lo que casa con la imagen: un efecto sin motivo visual es ruido.
   - **La prueba (1-oct):** si hay un documento REAL (periódico, certificado, informe) que dice
     el dato, ponlo en `pruebas` con la frase TAL CUAL está impresa (`python tools/ocr_doc.py
assets/t/<img>.jpg "<frase>"` para comprobarla); `marca` = la palabra de la voz donde se
     subraya. 1-1,5 s basta. Es lo que convierte "te lo cuento" en "aquí está".
   - **Serie:** `"serie": {"nombre": "Quiet Millionaires", "ep": N}` si el tema es de la serie
     (gente corriente que se hizo rica en silencio); N = siguiente episodio. El comentario para
     fijar sale solo de la dicotomía del CTA si la hay; si no, `publicacion.comentario`.
   - **Nada genérico ni de clip-art (26-sep):** cada visual es metraje real, un documento real
     (certificados, fotos de archivo) o un dato real con ejes. En `curva`, pon `"desde_anio"` SOLO
     si el año de inicio está verificado en las fuentes (Grace: 1935); si no, el eje va en "Yr N".
     El `contador3d` va sobre metraje real (sin monedas 3D).
   - subtítulos sin el gancho ni el CTA; como mucho un `contador3d`;
   - `publicacion` con título (≤100), descripción, tags y hashtags; `adn` con `renderer_version: v2-hyperframes`.
     Lecciones del ensayo del 23-sep (Grace Groner), no repetirlas:
   - Genera la voz ANTES de escribir las escenas (`python video-v2/motor/voz.py video-v2/<ref>`,
     con solo `guion` en el storyboard) y lista las frases con sus palabras exactas: las anclas
     se escriben contra ese listado (p. ej. "—" es una palabra; "seventy-five" va con guion).
   - Imágenes: busca OBJETOS y lugares ("vintage typewriter", "stock certificate"), no personas:
     Commons responde mal a conceptos genéricos de gente y las fotos de personas traen contexto
     (una "stenographer" resultó ser de un campo de internamiento de 1942). Reutiliza las del
     catálogo ya bajado (`video-v2/*/assets/t/` + su creditos.json) antes de buscar.
   - CTA: la `pregunta` va ANTES que los `botones` (los botones la ocultan al entrar).
8. `python video-v2/motor/construir.py video-v2/<ref> --validar` hasta que pase. El mensaje dice
   qué frase y qué palabra fallan: corrige el storyboard, no el validador. Después revisa una
   hoja de contactos (`npx hyperframes snapshot --at ...`) ANTES del render: el validador no ve
   solapes ni textos que no caben.

## 3b. Páginas vivas (carrusel + historia)

Añade al storyboard un bloque `social` (formato en `video-v2/motor/social.py`): 5-7 diapositivas
con `fondo` real (`img:<clave>` o `clip:<clave>@<s>`), portada con el gancho, una idea por
diapositiva (texto ≤170 caracteres, dato verificado en `cifras`), última con la pregunta del CTA;
`caption` sin hashtags ni fuentes (se añaden solos); `historia.hasta` = final de la 2.ª frase.
`producir.py` lo genera en `social/` como una puerta más. Publicar en Facebook/Instagram:
`python -m omega.cli publish-social <ref>` muestra el plan; `--publicar` SOLO con confirmación
explícita del usuario en el chat (regla del proyecto).

## 4. Producir y medir

**`producir.py` y `critico.py` van SIEMPRE en segundo plano** (`run_in_background`): el aviso llega solo.
Nada de `tail`, `sleep` ni `Monitor`: cada consulta relee todo el contexto.

9. `python video-v2/motor/producir.py video-v2/<ref>` — voz, build, lint, render, loudness, ritmo.
   Si una puerta falla, arregla la CAUSA (máx. 2 rondas). Nunca subas un umbral para pasar.

## 4b. Crítico (máx. 2 rondas, nunca publica)

10. `python video-v2/motor/critico.py video-v2/<ref> --mp4 video-v2/<ref>/renders/<ref>-final.mp4 --solo-revisar`
    → medidores sobre el MP4 (legibilidad por OCR, ritmo, voz, sincronía, mezcla, datos, parecido;
    rúbrica PROVISIONAL en `docs/RUBRICA.md`). Deja `renders/critica/r0/juicio.md` + fotogramas.
11. **Juicio:** mira `renders/critica/r0/hoja.jpg` (no las imágenes sueltas; abre un `f_*.jpg` solo si
    dudas de ese segundo o para leer letra pequeña) y escribe `renders/critica/r0/juicio.json` con J1-J6 (lo que los medidores no ven: gancho,
    imagen = palabra, exactitud contra la fuente, cierre). Parches solo del catálogo; sin perilla
    segura -> `"parche": null` (se reporta, no se toca a ciegas).
12. `python video-v2/motor/critico.py video-v2/<ref> --mp4 video-v2/<ref>/renders/critica/r0.mp4 --rondas 2`
    → parchea el storyboard, re-renderiza (sin subir) y se queda con la mejor ronda MEDIDA. Entrega
    `renders/critica/informe.md` (fallos con segundo y escena por ronda + parches) y `rN.mp4`.
    Si quedó subido un borrador de la ronda 0 y ganó otra ronda: avisa, no re-subas solo.

## 5. Entregar y PARAR

13. `python -m omega.cli estado-subir` y `python -m omega.cli produccion-guardar video-v2/<ref>`
    (el proyecto va al repo PRIVADO, no a una rama suelta del repo de código). `producir.py` ya lo
    habrá subido a YouTube como PRIVADO si hay token.
14. Envía la preview con SendUserFile y un resumen corto: tema y por qué ganó, el guion, las
    fuentes, la tabla de puertas de `renders/qa.json`, la lista de fallos del crítico (informe.md:
    qué arregló y qué queda) y título y descripción propuestos. Pide la nota a ciegas (1-10 +
    queja con segundo): es lo que calibra la rúbrica.
15. **PARA aquí.** No publiques nada. Espera la aprobación explícita del usuario en esta sesión.

## 6. Solo si el usuario aprueba

16. YouTube: `python -m omega.cli programar <ref>` (lo publica a las 12:00 de Nueva York, hora
    pico de la audiencia; `--hora HH:MM` para otra) o `--ahora` si lo pide ya. Si no se subió como
    borrador (sin token), antes `python -m omega.cli publish <ref>`.
17. Facebook/Instagram: **solo con confirmación explícita para Meta** (regla del proyecto):
    `publish-fb <ref> --publicar` / `publish-ig <ref> --publicar`.
18. `python -m omega.cli record-dna video-v2/<ref>/adn.json`.
19. `python -m omega.cli record-cost` (lee `data/production_cost.json`; o pásale otra ruta):
    `{"production_ref": "<ref>", "research_hours": null, "script_hours": null, "edit_hours": null, "ai_cost_usd": null, "time_to_publish_h": null}`.
    Solo valores medidos o dichos por el usuario: lo que no se sepa va en `null`, no se estima.
20. `python -m omega.cli estado-subir`.
