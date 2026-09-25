# Prepara el token de YouTube para la nube en UN comando (Windows + PowerShell).
#
#   powershell -ExecutionPolicy Bypass -File preparar_pc.ps1 -ClientSecret "$HOME\Downloads\client_secret_XXXX.json"
#
# Qué hace: clona (o actualiza) el repo, instala dependencias, copia el JSON del cliente OAuth a
# data\youtube_client_secret.json, abre el login de Google (youtube-auth) y deja el contenido de
# data\youtube_token.json en el portapapeles para pegarlo en la variable YOUTUBE_TOKEN_JSON del
# entorno de la nube. Nunca imprime el token en pantalla.
param(
  [Parameter(Mandatory = $true)] [string] $ClientSecret,
  [string] $Destino = "$HOME\net-worthy-os"
)
$ErrorActionPreference = "Stop"

if (-not (Test-Path $ClientSecret)) { throw "No encuentro $ClientSecret (descárgalo de Google Cloud -> Credenciales -> cliente OAuth 'Escritorio')." }
foreach ($c in "git", "python") { if (-not (Get-Command $c -ErrorAction SilentlyContinue)) { throw "Falta '$c' en el PATH." } }

if (Test-Path "$Destino\.git") { git -C $Destino pull --ff-only } else { git clone https://github.com/JemberSanchez/net-worthy-os.git $Destino }
Set-Location $Destino
python -m pip install -q google-api-python-client google-auth-oauthlib google-auth-httplib2 requests tzdata

New-Item -ItemType Directory -Force -Path data | Out-Null
Copy-Item $ClientSecret data\youtube_client_secret.json -Force

Write-Host "`nSe abrirá el navegador: elige la cuenta del canal Net Worthy y acepta los permisos." -ForegroundColor Yellow
python -m omega.cli youtube-auth
if ($LASTEXITCODE -ne 0 -or -not (Test-Path data\youtube_token.json)) { throw "El login no terminó bien (mira el mensaje de arriba)." }

Get-Content data\youtube_token.json -Raw | Set-Clipboard
Write-Host "`n✓ Token en el portapapeles. Pégalo en el entorno de la nube como variable YOUTUBE_TOKEN_JSON." -ForegroundColor Green
Write-Host "  (Claude in Chrome puede hacerlo: 'pega el portapapeles en la variable YOUTUBE_TOKEN_JSON del entorno')."
