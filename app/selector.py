"""Edición de las zonas del perfil: se pueden marcar varias a la vez."""
from PySide6.QtCore import QObject, QRect, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import winutil
from .overlay import physical_to_logical

HELP = (
    "Arrastra para añadir zonas (puedes marcar varias)  ·  clic derecho sobre una zona para quitarla\n"
    "Enter: guardar   ·   Retroceso: quitar la última   ·   Supr: quitar todas   ·   Esc: cancelar"
)


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

    def _local_rects(self):
        origin = self.geometry().topLeft()
        for i, region in enumerate(self.owner.regions):
            yield i, physical_to_logical(region).translated(-origin)

    def paintEvent(self, e):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0, 110))
        rects = list(self._local_rects())
        if self.start and self.current:
            rects.append((-1, QRect(self.start, self.current).normalized()))
        for i, r in rects:
            p.setCompositionMode(QPainter.CompositionMode_Clear)
            p.fillRect(r, Qt.transparent)
            p.setCompositionMode(QPainter.CompositionMode_SourceOver)
            p.fillRect(r, QColor(255, 255, 255, 1))  # casi invisible, pero sigue recibiendo el ratón
            p.setPen(QPen(QColor(0, 200, 255) if i < 0 else QColor(255, 182, 39), 2))
            p.drawRect(r)
            if i >= 0:
                tag = QRect(r.x(), r.y() - 22 if r.y() >= 22 else r.y(), 64, 22)
                p.fillRect(tag, QColor(255, 182, 39))
                p.setPen(QColor(30, 30, 60))
                f = QFont("Segoe UI")
                f.setPixelSize(13)
                f.setBold(True)
                p.setFont(f)
                p.drawText(tag, Qt.AlignCenter, f"Zona {i + 1}")
        # Cabecera
        header = QRect(self.rect().center().x() - 420, 24, 840, 74)
        p.fillRect(header, QColor(20, 20, 30, 220))
        p.setPen(QColor(255, 255, 255))
        f = QFont("Segoe UI")
        f.setPixelSize(15)
        f.setBold(True)
        p.setFont(f)
        p.drawText(header.adjusted(0, 6, 0, 0), Qt.AlignHCenter | Qt.AlignTop, f"Perfil: {self.owner.profile_name}   ·   {len(self.owner.regions)} zona(s)")
        f.setBold(False)
        f.setPixelSize(13)
        p.setFont(f)
        p.drawText(header.adjusted(0, 0, 0, -6), Qt.AlignHCenter | Qt.AlignBottom, HELP)

    def mousePressEvent(self, e):
        pos = e.position().toPoint()
        if e.button() == Qt.LeftButton:
            self.start = self.current = pos
            self.owner._phys_start = winutil.cursor_pos_physical()
            self.update()
        elif e.button() == Qt.RightButton:
            for i, r in reversed(list(self._local_rects())):
                if r.contains(pos):
                    self.owner.remove(i)
                    return

    def mouseMoveEvent(self, e):
        if self.start:
            self.current = e.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton and self.start:
            self.start = self.current = None
            self.owner.add(self.owner._phys_start, winutil.cursor_pos_physical())

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key_Escape:
            self.owner.cancel()
        elif k in (Qt.Key_Return, Qt.Key_Enter):
            self.owner.finish()
        elif k == Qt.Key_Backspace:
            self.owner.remove(len(self.owner.regions) - 1)
        elif k == Qt.Key_Delete:
            self.owner.clear()


class RegionSelector(QObject):
    selected = Signal(list)   # lista de [x, y, w, h] en píxeles físicos
    canceled = Signal()

    def __init__(self):
        super().__init__()
        self._widgets = []
        self._phys_start = None
        self.regions = []
        self.profile_name = ""

    def is_active(self) -> bool:
        return bool(self._widgets)

    def start(self, regions, profile_name: str):
        self.close()
        self.regions = [list(r) for r in regions]
        self.profile_name = profile_name
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

    def _repaint(self):
        for w in self._widgets:
            w.update()

    def add(self, a, b):
        x1, y1 = min(a[0], b[0]), min(a[1], b[1])
        x2, y2 = max(a[0], b[0]), max(a[1], b[1])
        if x2 - x1 >= 10 and y2 - y1 >= 8:
            self.regions.append([x1, y1, x2 - x1, y2 - y1])
        self._repaint()

    def remove(self, index: int):
        if 0 <= index < len(self.regions):
            del self.regions[index]
        self._repaint()

    def clear(self):
        self.regions = []
        self._repaint()

    def finish(self):
        regions = self.regions
        self.close()
        self.selected.emit(regions)

    def cancel(self):
        self.close()
        self.canceled.emit()

    def close(self):
        for w in self._widgets:
            w.close()
            w.deleteLater()
        self._widgets = []
