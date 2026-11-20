"""Rutas de datos del usuario y recursos empaquetados."""
import logging
import os
import shutil
import sys
from pathlib import Path

from . import APP_ID, LEGACY_APP_ID

log = logging.getLogger(__name__)


def resource_path(*parts: str) -> Path:
    """Ruta a un recurso empaquetado (funciona en desarrollo y con PyInstaller)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base.joinpath(*parts)


def data_dir() -> Path:
    """Carpeta de datos del usuario: %APPDATA%/Glosa."""
    root = Path(os.environ.get("APPDATA") or str(Path.home()))
    d = root / APP_ID
    legacy = root / LEGACY_APP_ID
    if not d.exists() and legacy.exists():
        # Migración desde la 1.0.0: se conservan la memoria de traducciones y los ajustes
        try:
            shutil.move(str(legacy), str(d))
        except OSError:
            shutil.copytree(legacy, d, dirs_exist_ok=True)
    d.mkdir(parents=True, exist_ok=True)
    return d
