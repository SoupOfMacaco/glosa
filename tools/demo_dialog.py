"""Ventana de prueba que imita el cuadro de diálogo de un juego (texto que se va escribiendo).

Uso:  python tools/demo_dialog.py [--set-region]
Con --set-region guarda su propia posición como zona a leer en la configuración de la app.
"""
import ctypes
import json
import os
import sys
from ctypes import wintypes
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLabel

LINES = [
    "If we survive this, we'll get back at them!",
    "The bridge to the north has collapsed. We need another way across the river.",
    "Do you have enough gold to buy the sword?",
    "Watch out! There are enemies behind you.",
]

app = QApplication(sys.argv)
label = QLabel()
label.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
label.setStyleSheet("background:#e8e2d6; color:#3a1f1a; padding:14px; border:3px solid #7a2b26;")
f = QFont("Consolas")
f.setPixelSize(26)
f.setBold(True)
label.setFont(f)
label.setWordWrap(True)
label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
label.setGeometry(200, 600, 900, 110)
label.show()

state = {"line": 0, "chars": 0, "hold": 0}


def tick():
    text = LINES[state["line"]]
    if state["chars"] < len(text):
        state["chars"] += 1
    else:
        state["hold"] += 1
        if state["hold"] > 120:  # ~4 s con el texto completo
            state.update(line=(state["line"] + 1) % len(LINES), chars=0, hold=0)
    label.setText(LINES[state["line"]][: state["chars"]])


timer = QTimer()
timer.timeout.connect(tick)
timer.start(33)

if "--set-region" in sys.argv:
    def save_region():
        r = wintypes.RECT()
        ctypes.windll.user32.GetWindowRect(int(label.winId()), ctypes.byref(r))
        cfg_path = Path(os.environ["APPDATA"]) / "TraductorEnVivo" / "config.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
        cfg.update(region=[r.left, r.top, r.right - r.left, r.bottom - r.top], first_run=False)
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        print("zona guardada:", cfg["region"], flush=True)
    QTimer.singleShot(300, save_region)

sys.exit(app.exec())
