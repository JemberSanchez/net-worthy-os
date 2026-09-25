"""Estado persistente del sistema (la base SQLite) en un repo git PRIVADO aparte.

    python -m omega.cli estado-bajar [--forzar]     # repo privado -> data/omega.sqlite
    python -m omega.cli estado-subir [--forzar]     # data/omega.sqlite -> repo privado (commit + push)

Por qué existe
--------------
La producción diaria corre en una sesión en la nube que nace VACÍA cada día; el dataset (corpus,
señales, outcomes, ADN) es el activo del proyecto y no puede vivir solo en un disco. El repo de
código es PÚBLICO: los datos van a otro repo, privado (`ESTADO_REPO`, p. ej.
https://github.com/<usuario>/net-worthy-data.git).

Formato: volcado SQL en texto (`omega.sql`), no el .sqlite binario: git comprime por diferencias
y el historial de un año de volcados diarios no pesa lo que pesarían 365 binarios.

Qué NUNCA viaja: tokens y secretos (youtube_token.json, meta_token.json, client_secret, .env).
Solo la base.

Dos guardas, porque los dos errores posibles destruyen datos en silencio:
  - `bajar` no pisa una base local que ya existe (salvo --forzar): la del PC puede ser más nueva.
  - `subir` no sube una base mucho más pequeña que la remota (salvo --forzar): es la firma de una
    sesión nueva que olvidó bajar primero y subiría una base vacía encima de meses de datos.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
from pathlib import Path

from . import config

ARCHIVO = "omega.sql"
UMBRAL_ENCOGE = 0.5      # subir un volcado < 50 % del remoto exige --forzar


class EstadoError(RuntimeError):
    pass


def exportar(db_path: Path) -> str:
    """SQLite -> volcado SQL determinista (mismo contenido = mismo texto)."""
    con = sqlite3.connect(db_path)
    try:
        return "\n".join(con.iterdump()) + "\n"
    finally:
        con.close()


def importar(sql: str, db_path: Path) -> None:
    """Volcado SQL -> SQLite nuevo (se escribe aparte y se renombra: nunca queda a medias)."""
    tmp = db_path.with_suffix(".sqlite.tmp")
    if tmp.exists():
        tmp.unlink()
    con = sqlite3.connect(tmp)
    try:
        con.executescript(sql)
        con.commit()
    finally:
        con.close()
    tmp.replace(db_path)


def puede_subir(local: str, remoto: str | None, forzar: bool = False) -> tuple[bool, str]:
    """Guarda contra subir una base vacía/recortada encima de la buena. Función pura."""
    if forzar or not remoto:
        return True, "ok"
    if len(local) < len(remoto) * UMBRAL_ENCOGE:
        return False, (f"el volcado local ({len(local):,} B) es menos de la mitad del remoto ({len(remoto):,} B): "
                       "¿sesión nueva que no hizo `estado-bajar`? No subo. Si es intencionado: --forzar")
    return True, "ok"


def _git(*args: str, cwd: Path) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise EstadoError(f"git {' '.join(args)} falló: {r.stderr.strip()[-400:]}")
    return r.stdout


def _clon() -> Path:
    url = os.environ.get("ESTADO_REPO")
    if not url:
        raise EstadoError("falta ESTADO_REPO (URL del repo PRIVADO de datos, p. ej. "
                          "https://github.com/<usuario>/net-worthy-data.git)")
    dst = config.DATA_DIR / ".estado"
    if (dst / ".git").exists():
        _git("pull", "--ff-only", "-q", cwd=dst)
    else:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        _git("clone", "-q", url, str(dst), cwd=config.DATA_DIR)
    return dst


def bajar(forzar: bool = False) -> str:
    clon = _clon()
    sql = clon / ARCHIVO
    if not sql.exists():
        return "el repo de estado aún no tiene volcado (primera vez): nada que bajar"
    if config.DB_PATH.exists() and not forzar:
        return f"{config.DB_PATH.name} ya existe en local: no la piso (usa --forzar para reemplazarla por la remota)"
    importar(sql.read_text(encoding="utf-8"), config.DB_PATH)
    return f"✓ base restaurada desde el repo de estado ({sql.stat().st_size:,} B de volcado)"


def subir(forzar: bool = False, mensaje: str = "estado: volcado diario") -> str:
    if not config.DB_PATH.exists():
        raise EstadoError(f"no existe {config.DB_PATH}: nada que subir")
    clon = _clon()
    sql = clon / ARCHIVO
    local = exportar(config.DB_PATH)
    remoto = sql.read_text(encoding="utf-8") if sql.exists() else None
    ok, motivo = puede_subir(local, remoto, forzar)
    if not ok:
        raise EstadoError(motivo)
    if local == remoto:
        return "sin cambios: el repo de estado ya tiene esta base"
    sql.write_text(local, encoding="utf-8")
    _git("add", ARCHIVO, cwd=clon)
    _git("-c", "user.name=net-worthy-os", "-c", "user.email=net-worthy-os@users.noreply.github.com",
         "commit", "-q", "-m", mensaje, cwd=clon)
    _git("push", "-q", cwd=clon)
    return f"✓ estado subido ({len(local):,} B)"


# ── Producciones: cada Short producido se guarda en el MISMO repo privado ─────────────────────────
# Una sesión nueva en la nube trabaja en su propia rama del repo de código: guardar allí los
# proyectos los dejaría dispersos en ramas sueltas. El repo privado ya existe para el estado, así
# que las producciones viven a su lado: producciones/<proyecto>/ (storyboard, voz, words.json,
# imágenes tratadas, créditos, ADN, qa.json). NO viajan: MP4 (se regeneran), originales de
# imágenes, música generada ni los assets comunes del motor.
EXCLUIR_PROD = ("renders/", "snapshots/", ".hyperframes/", "node_modules/", "assets/_motor/", "assets/img/")
EXCLUIR_ARCH = ("music-bed.wav",)
INCLUIR_SIEMPRE = ("assets/img/creditos.json", "renders/qa.json")


def archivos_produccion(proy: Path) -> list[Path]:
    """Qué archivos de un proyecto se guardan (relativos al proyecto). Función pura sobre el disco."""
    out = []
    for f in sorted(proy.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(proy).as_posix()
        if rel in INCLUIR_SIEMPRE or not (rel.startswith(EXCLUIR_PROD) or f.name in EXCLUIR_ARCH):
            out.append(Path(rel))
    return out


def guardar_produccion(proy: Path, mensaje: str | None = None) -> str:
    import shutil
    proy = Path(proy).resolve()
    if not (proy / "storyboard.json").exists():
        raise EstadoError(f"{proy} no es un proyecto v2 (falta storyboard.json)")
    clon = _clon()
    dst = clon / "producciones" / proy.name
    if dst.exists():
        shutil.rmtree(dst)
    archivos = archivos_produccion(proy)
    for rel in archivos:
        (dst / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(proy / rel, dst / rel)
    _git("add", "-A", "producciones", cwd=clon)
    if not _git("status", "--porcelain", cwd=clon).strip():
        return f"sin cambios: producciones/{proy.name} ya estaba guardada"
    _git("-c", "user.name=net-worthy-os", "-c", "user.email=net-worthy-os@users.noreply.github.com",
         "commit", "-q", "-m", mensaje or f"produccion: {proy.name}", cwd=clon)
    _git("push", "-q", cwd=clon)
    return f"✓ producciones/{proy.name} guardada ({len(archivos)} archivos)"
