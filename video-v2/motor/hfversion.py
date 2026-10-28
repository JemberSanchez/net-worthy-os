"""Single source of truth for the HyperFrames version (user decision 28-oct: always the latest).

`HF_VERSION=<x.y.z>` pins it (to reproduce or roll back a render); otherwise it is the latest
published on npm, resolved once per process. `producir.py` exports it to its child processes so
one production uses one version, and records it in `renders/qa.json`.
"""

from __future__ import annotations

import functools
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][\w.-]+)?$")


class VersionError(RuntimeError):
    pass


@functools.cache
def version() -> str:
    v = os.environ.get("HF_VERSION", "").strip()
    if not v:
        npm = (
            shutil.which("npm") or "npm"
        )  # Windows: npm is npm.cmd, CreateProcess will not find it bare
        try:
            r = subprocess.run(
                [npm, "view", "hyperframes", "version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            raise VersionError(f"npm view hyperframes version failed: {e}") from e
        v = r.stdout.strip()
        if r.returncode != 0:
            raise VersionError(
                f"npm view hyperframes version failed: {(r.stderr or r.stdout)[-300:]}"
            )
    if not SEMVER.match(v):
        raise VersionError(f"not a HyperFrames version: {v!r}")
    return v


def npx(*args: str) -> list[str]:
    """Command line for `npx hyperframes@<version> <args>`."""
    return [shutil.which("npx") or "npx", "--yes", f"hyperframes@{version()}", *args]


def version_core(core: str | os.PathLike | None) -> str | None:
    """Installed @hyperframes/core in the HF_CORE folder, or None."""
    p = Path(core or "") / "node_modules" / "@hyperframes" / "core" / "package.json"
    return (
        json.loads(p.read_text(encoding="utf-8")).get("version")
        if core and p.exists()
        else None
    )


def version_carve(carve: str | os.PathLike | None) -> str | None:
    """Version of the hyperframes checkout that holds carve.mjs (its packages/cli/package.json),
    or None when carve does not live in a checkout (e.g. a bare skill install)."""
    if not carve:
        return None
    for d in Path(carve).resolve().parents:
        p = d / "packages" / "cli" / "package.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8")).get("version")
    return None
