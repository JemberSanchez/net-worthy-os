# Activar la producción diaria en la nube — checklist

Lo que falta para que la rutina diaria (`/producir`) funcione sola es CONFIGURACIÓN, no código.
Los pasos web los puede hacer **Claude in Chrome** con el prompt de abajo. El único paso que exige
terminal es el token de YouTube (paso B).

## A) Prompt para Claude in Chrome (copiar y pegar tal cual)

```
Necesito que configures mi proyecto "Net Worthy OS" en el navegador. Reglas: NUNCA escribas en
ningún chat ni en ningún campo que no sea el indicado el valor de una clave o token; si algo pide
confirmación de pago, de borrar datos o de permisos a terceros que no sean los que te indico, para
y pregúntame. Hazlo en este orden y al final dime qué hiciste y qué quedó pendiente.

1. GitHub (github.com, cuenta JemberSanchez):
   a) Crea un repositorio nuevo llamado "net-worthy-data", PRIVADO, marcando "Add a README".
      Descripción: "Estado privado de Net Worthy OS (base de datos y producciones). Sin tokens."
   b) Ve a https://github.com/settings/installations, abre la app "Claude" -> Configure ->
      Repository access. Si está en "Only select repositories", añade "net-worthy-data" y guarda.

2. Google Cloud Console (console.cloud.google.com, el proyecto donde está la YouTube Data API):
   a) "APIs y servicios" -> "Pantalla de consentimiento de OAuth" (o "Google Auth Platform" ->
      "Público"). Si el estado de publicación es "En prueba"/"Testing", pulsa "Publicar app" /
      "Pasar a producción" y confirma. (En prueba, el token caduca cada 7 días.)
   b) "APIs y servicios" -> "Biblioteca": busca "YouTube Analytics API" y pulsa "Habilitar" si no
      lo está.
   c) "APIs y servicios" -> "Credenciales" -> "Claves de API": copia al portapapeles el valor de la
      clave que ya existe (NO crees una nueva). La usarás en el paso 3.

3. Entorno de la nube de Claude Code (claude.ai/code): abre la sesión del proyecto net-worthy-os,
   menú del entorno en la barra de título -> "Edit".
   a) Variables de entorno: añade
      - YOUTUBE_API_KEY = (pega la clave del paso 2c)
      - ESTADO_REPO = https://github.com/JemberSanchez/net-worthy-data.git
   b) Acceso de red / dominios permitidos: añade estos dominios (uno por línea) sin quitar los que
      ya hay:
      news.google.com
      cointelegraph.com
      www.coindesk.com
      finance.yahoo.com
      feeds.marketwatch.com
      www.reddit.com
      en.wikipedia.org
      suggestqueries.google.com
      graph.facebook.com
      rupload.facebook.com
      videos.pexels.com
   c) (Opcional, b-roll de Pexels además del de Commons) Variable PEXELS_API_KEY: créala gratis
      en https://www.pexels.com/api/ con la cuenta del usuario y pega su valor en el entorno.
   d) Guarda.

4. Dime cuáles de los pasos 1-3 quedaron hechos y cuáles no, sin mostrar ningún valor secreto.
```

## B) En tu PC (terminal, 3 minutos) — lo único que Chrome no puede hacer
**Atajo en un comando** (descarga antes el JSON del cliente OAuth "Escritorio" de Google Cloud →
Credenciales, y el script `tools/preparar_pc.ps1` desde GitHub):
```powershell
powershell -ExecutionPolicy Bypass -File preparar_pc.ps1 -ClientSecret "$HOME\Downloads\client_secret_XXXX.json"
```
Paso a paso, si prefieres hacerlo a mano:
```powershell
git clone https://github.com/JemberSanchez/net-worthy-os.git ; cd net-worthy-os
pip install -r requirements.txt
# descarga el JSON del cliente OAuth "Escritorio" desde Google Cloud -> Credenciales y guárdalo como:
#   data\youtube_client_secret.json
python -m omega.cli youtube-auth          # abre el navegador; elige la cuenta del canal Net Worthy
Get-Content data\youtube_token.json -Raw | Set-Clipboard
```
Pega el portapapeles en el entorno de la nube como variable **`YOUTUBE_TOKEN_JSON`**.

~~Subir la base del PC anterior~~ — ya no hace falta: el 25-sep se decidió empezar desde 0 y la
base nueva ya está en el repo privado (ADN de #7 y #8).

Meta (opcional, cuando quieras publicar también en Facebook/Instagram): `.env` con
`META_APP_ID`/`META_APP_SECRET` → `python -m omega.cli meta-auth` → contenido de
`data\meta_token.json` en la variable `META_TOKEN_JSON`. Caduca a los 60 días.

## C) Después
Abre una **sesión nueva** (las variables solo entran al arrancar) y pide: "ejecuta una prueba
vigilada de /producir y programa la rutina diaria". Claude verifica todo, produce el primer vídeo
de punta a punta (queda como borrador PRIVADO en YouTube) y deja la rutina programada.
Aprobar cada día = `python -m omega.cli programar <ref>` (lo publica a las 12:00 de Nueva York).

## D) Pexels (b-roll moderno en vertical) — prompt para Claude in Chrome
```
Necesito una clave de la API de Pexels para mi proyecto Net Worthy OS. Reglas: NUNCA escribas el
valor de la clave en ningún chat ni en otro campo que el indicado; si algo pide pago o permisos
distintos de los que indico, para y pregúntame.

1. Ve a https://www.pexels.com/api/ . Si no hay sesión iniciada, pídeme que inicie sesión yo
   (no crees cuentas ni escribas contraseñas).
2. Pulsa "Your API Key" / "Get Started" y rellena el formulario de solicitud:
   - Project name / Nombre: Net Worthy
   - Descripción: "Faceless personal-finance YouTube Shorts. Uses Pexels videos as b-roll with
     attribution in each video description."
   - URL: https://www.youtube.com/@networthytv
   Acepta los términos de la API de Pexels y envía. Copia la clave al portapapeles.
3. Abre claude.ai/code, la sesión del proyecto net-worthy-os, menú del entorno en la barra de
   título -> "Edit":
   a) Variables de entorno: añade PEXELS_API_KEY = (pega la clave).
   b) Acceso de red / dominios permitidos: añade videos.pexels.com (sin quitar los que hay).
   c) Guarda.
4. Dime qué pasos quedaron hechos, sin mostrar la clave.
```

## E) Publicar #7 y #8 (en una sesión NUEVA, con el token de YouTube ya cargado)
Pedir: "publica #7 y #8 en YouTube". La sesión hace:
1. `bash tools/setup_nube.sh` y `python -m omega.cli estado-bajar`.
2. `python video-v2/motor/producir.py video-v2/read-janitor` y lo mismo con `video-v2/grace-groner`
   (render + todas las puertas + subida como PRIVADO; los MP4 no viajan entre sesiones).
3. Solo si las dos pasan todas las puertas: `python -m omega.cli programar ronald-read-janitor-v2-2026-09`
   y `python -m omega.cli programar grace-groner-secretary-v2-2026-09 --dias 1` (uno por día, 12:00 NY).
4. `record-dna` de los dos `adn.json`, `estado-subir` y `produccion-guardar` de los dos.
Facebook/Instagram NO van en este paso: requieren confirmación explícita aparte.
