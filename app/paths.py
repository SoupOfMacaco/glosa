"""Rutas de datos del usuario y recursos empaquetados."""
import os
import sys
from pathlib import Path

from . import APP_ID


def resource_path(*parts: str) -> Path:
    """Ruta a un recurso empaquetado (funciona en desarrollo y con PyInstaller)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base.joinpath(*parts)


def data_dir() -> Path:
    """Carpeta de datos del usuario: %APPDATA%/TraductorEnVivo."""
    root = os.environ.get("APPDATA") or str(Path.home())
    d = Path(root) / APP_ID
    d.mkdir(parents=True, exist_ok=True)
    return d
