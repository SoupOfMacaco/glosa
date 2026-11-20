"""Selección de la zona de pantalla a leer (arrastrando un rectángulo)."""
from PySide6.QtCore import QObject, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import winutil


class _ScreenSelector(QWidget):
    def __init__(self, screen, owner: "RegionSelector"):
        super().__init__(None)
        self.owner = owner
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.setGeometry(screen.geometry())
        self.start = None
        self.current = None

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 110))
        p.setPen(QColor(255, 255, 255))
        f = QFont("Segoe UI")
        f.setPixelSize(18)
        p.setFont(f)
        p.drawText(
            self.rect().adjusted(0, 30, 0, 0),
            Qt.AlignHCenter | Qt.AlignTop,
            "Arrastra para marcar la zona del texto  ·  Esc para cancelar",
        )
        if self.start and self.current:
            r = QRect(self.start, self.current).normalized()
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.fillRect(r, Qt.transparent)
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
            p.fillRect(r, QColor(255, 255, 255, 1))  # casi invisible, pero sigue recibiendo el ratón
            p.setPen(QPen(QColor(0, 200, 255), 2))
            p.drawRect(r)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.start = self.current = e.position().toPoint()
            self.owner._phys_start = winutil.cursor_pos_physical()
            self.update()
        elif e.button() == Qt.RightButton:
            self.owner.cancel()

    def mouseMoveEvent(self, e):
        if self.start:
            self.current = e.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.start:
            end = winutil.cursor_pos_physical()
            self.owner.finish(self.owner._phys_start, end)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.owner.cancel()


class RegionSelector(QObject):
    selected = Signal(list)   # [x, y, w, h] en píxeles físicos
    canceled = Signal()

    def __init__(self):
        super().__init__()
        self._widgets = []
        self._phys_start = None

    def start(self):
        self.close()
        for screen in QGuiApplication.screens():
            w = _ScreenSelector(screen, self)
            w.show()
            w.raise_()
            self._widgets.append(w)
        cur = QGuiApplication.screenAt(QCursor.pos())
        for w in self._widgets:
            if cur and w.geometry() == cur.geometry():
                w.activateWindow()
                w.setFocus()

    def finish(self, a, b):
        self.close()
        x1, y1 = min(a[0], b[0]), min(a[1], b[1])
        x2, y2 = max(a[0], b[0]), max(a[1], b[1])
        if x2 - x1 < 10 or y2 - y1 < 8:
            self.canceled.emit()
            return
        self.selected.emit([x1, y1, x2 - x1, y2 - y1])

    def cancel(self):
        self.close()
        self.canceled.emit()

    def close(self):
        for w in self._widgets:
            w.close()
            w.deleteLater()
        self._widgets = []
