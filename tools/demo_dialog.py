"""Ventanas de prueba que imitan dos cuadros de diálogo de un juego (arriba y abajo) con texto que se va escribiendo.

Uso:  python tools/demo_dialog.py [--set-region]
Con --set-region crea en la configuración de Glosa un perfil "Demo" con las dos zonas y lo activa.
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

BOTTOM = [
    "If we survive this, we'll get back at them!",
    "The bridge to the north has collapsed. We need another way across the river.",
    "Do you have enough gold to buy the sword?",
]
TOP = [
    "New objective: find the old lighthouse.",
    "Your party gained 120 experience points.",
    "The merchant has new items for sale.",
]

app = QApplication(sys.argv)


def make_box(x, y, w, h, color):
    label = QLabel()
    label.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
    label.setStyleSheet(f"background:#e8e2d6; color:#3a1f1a; padding:14px; border:3px solid {color};")
    f = QFont("Consolas")
    f.setPixelSize(24)
    f.setBold(True)
    label.setFont(f)
    label.setWordWrap(True)
    label.setGeometry(x, y, w, h)
    label.show()
    return label


boxes = [
    (make_box(200, 600, 900, 100, "#7a2b26"), BOTTOM, {"line": 0, "chars": 0, "hold": 0}),
    (make_box(200, 120, 700, 70, "#26507a"), TOP, {"line": 0, "chars": 0, "hold": 60}),
]


def tick():
    for label, lines, st in boxes:
        text = lines[st["line"]]
        if st["chars"] < len(text):
            st["chars"] += 1
        else:
            st["hold"] += 1
            if st["hold"] > 130:
                st.update(line=(st["line"] + 1) % len(lines), chars=0, hold=0)
        label.setText(lines[st["line"]][: st["chars"]])


timer = QTimer()
timer.timeout.connect(tick)
timer.start(33)

if "--set-region" in sys.argv:
    def save_regions():
        regions = []
        for label, _, _ in boxes:
            r = wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(int(label.winId()), ctypes.byref(r))
            regions.append([r.left, r.top, r.right - r.left, r.bottom - r.top])
        cfg_path = Path(os.environ["APPDATA"]) / "Glosa" / "config.json"
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        cfg = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
        profiles = [p for p in cfg.get("profiles", []) if p.get("name") != "Demo"]
        profiles.append({"name": "Demo", "regions": regions, "game": ""})
        cfg.update(profiles=profiles, active_profile="Demo", first_run=False, auto_profile=False)
        cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        print("perfil Demo guardado:", regions, flush=True)
    QTimer.singleShot(300, save_regions)

sys.exit(app.exec())
