"""Utilidades específicas de Windows (DPI, captura, autoarranque, instancia única)."""
import ctypes
import logging
import os
import sys
import winreg
from ctypes import wintypes

log = logging.getLogger(__name__)

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

WDA_EXCLUDEFROMCAPTURE = 0x11
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def windows_build() -> int:
    try:
        return sys.getwindowsversion().build
    except Exception:
        return 0


def supports_capture_exclusion() -> bool:
    """Windows 10 2004 (build 19041) o superior permite excluir ventanas de las capturas."""
    return windows_build() >= 19041


def exclude_from_capture(hwnd: int) -> bool:
    """Hace que la ventana no salga en capturas, para que el OCR no lea nuestra propia traducción."""
    if not supports_capture_exclusion() or os.environ.get("TEV_DEBUG_VISIBLE") == "1":
        return False
    ok = bool(user32.SetWindowDisplayAffinity(wintypes.HWND(hwnd), WDA_EXCLUDEFROMCAPTURE))
    if not ok:
        log.warning("SetWindowDisplayAffinity falló (error %s)", ctypes.get_last_error())
    return ok


def cursor_pos_physical() -> tuple[int, int]:
    """Posición del ratón en píxeles físicos (el proceso es DPI-aware por monitor)."""
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


_mutex = None


def acquire_single_instance(name: str) -> bool:
    """Devuelve False si ya hay otra instancia ejecutándose."""
    global _mutex
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    _mutex = kernel32.CreateMutexW(None, False, name)
    return ctypes.get_last_error() != 183  # ERROR_ALREADY_EXISTS


def _exe_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pyw = sys.executable.replace("python.exe", "pythonw.exe")
    return f'"{pyw}" -m app'


def set_autostart(enabled: bool, value_name: str) -> None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, _exe_command())
            else:
                try:
                    winreg.DeleteValue(key, value_name)
                except FileNotFoundError:
                    pass
    except OSError:
        log.exception("No se pudo cambiar el inicio automático")


def run_elevated(exe: str, params: str) -> bool:
    """Ejecuta un programa pidiendo permisos de administrador (UAC)."""
    shell32 = ctypes.WinDLL("shell32")
    shell32.ShellExecuteW.restype = ctypes.c_void_p
    r = shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    return (r or 0) > 32
