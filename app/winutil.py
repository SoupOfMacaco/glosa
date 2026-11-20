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


# Procesos del propio Windows que no cuentan como "juego en primer plano"
SHELL_PROCESSES = {
    "explorer.exe", "shellexperiencehost.exe", "searchhost.exe", "searchapp.exe",
    "startmenuexperiencehost.exe", "lockapp.exe", "applicationframehost.exe", "taskmgr.exe",
}


def foreground_app() -> tuple[str, str]:
    """(nombre del .exe en minúsculas, título de la ventana) de la ventana en primer plano."""
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return "", ""
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value == os.getpid():
        return "", ""
    length = user32.GetWindowTextLengthW(hwnd)
    title_buf = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, title_buf, length + 1)
    exe = ""
    h = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if h:
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                exe = os.path.basename(buf.value).lower()
        finally:
            kernel32.CloseHandle(h)
    if exe in SHELL_PROCESSES:
        return "", ""
    return exe, title_buf.value


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


def migrate_autostart(old_name: str, new_name: str) -> bool:
    """Si la versión antigua tenía inicio automático, lo pasa al nombre nuevo. Devuelve True si existía."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE) as key:
            try:
                winreg.QueryValueEx(key, old_name)
            except FileNotFoundError:
                return False
            winreg.DeleteValue(key, old_name)
    except OSError:
        return False
    set_autostart(True, new_name)
    return True


def run_elevated(exe: str, params: str) -> bool:
    """Ejecuta un programa pidiendo permisos de administrador (UAC)."""
    shell32 = ctypes.WinDLL("shell32")
    shell32.ShellExecuteW.restype = ctypes.c_void_p
    r = shell32.ShellExecuteW(None, "runas", exe, params, None, 1)
    return (r or 0) > 32
