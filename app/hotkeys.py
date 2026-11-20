"""Atajos de teclado globales (funcionan aunque el juego tenga el foco)."""
import ctypes
import logging
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

log = logging.getLogger(__name__)
user32 = ctypes.WinDLL("user32", use_last_error=True)

WM_HOTKEY = 0x0312
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x4000

# id: (modificadores, tecla, descripción)
HOTKEYS = {
    1: (MOD_CONTROL | MOD_SHIFT, ord("T"), "Ctrl+Shift+T", "Seleccionar zona"),
    2: (MOD_CONTROL | MOD_SHIFT, ord("P"), "Ctrl+Shift+P", "Pausar / reanudar"),
    3: (MOD_CONTROL | MOD_SHIFT, ord("M"), "Ctrl+Shift+M", "Cambiar modo de visualización"),
    4: (MOD_CONTROL | MOD_SHIFT, ord("H"), "Ctrl+Shift+H", "Ocultar / mostrar traducción"),
}


class HotkeyManager(QObject, QAbstractNativeEventFilter):
    triggered = Signal(int)

    def __init__(self):
        QObject.__init__(self)
        QAbstractNativeEventFilter.__init__(self)
        self.registered = []
        self.failed = []

    def register_all(self):
        for hid, (mods, vk, label, _) in HOTKEYS.items():
            if user32.RegisterHotKey(None, hid, mods | MOD_NOREPEAT, vk):
                self.registered.append(hid)
            else:
                self.failed.append(label)
                log.warning("No se pudo registrar el atajo %s (¿lo usa otro programa?)", label)

    def unregister_all(self):
        for hid in self.registered:
            user32.UnregisterHotKey(None, hid)
        self.registered = []

    def nativeEventFilter(self, event_type, message):
        if event_type in (b"windows_generic_MSG", "windows_generic_MSG"):
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam in HOTKEYS:
                self.triggered.emit(int(msg.wParam))
                return True, 0
        return False, 0
