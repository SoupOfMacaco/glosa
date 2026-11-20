"""Ventanas flotantes con la traducción (siempre encima y sin capturar el ratón).

Manteniendo Alt pulsado se vuelven clicables: Alt+clic copia la traducción y Alt+clic derecho permite corregirla.
"""
import time

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from . import winutil
from .config import FLOAT_ABOVE, FLOAT_COVER

PAD = 10
CORNER_MARGIN = 24
CORNER_MAX_WIDTH = 520
BLOCK_GAP = 12


def screen_for_physical_point(px: int, py: int):
    for s in QGuiApplication.screens():
        g, dpr = s.geometry(), s.devicePixelRatio()
        native = QRect(g.x(), g.y(), round(g.width() * dpr), round(g.height() * dpr))
        if native.contains(px, py):
            return s
    return QGuiApplication.primaryScreen()


def physical_to_logical(region) -> QRect:
    """Convierte [x, y, w, h] en píxeles físicos a coordenadas lógicas de Qt."""
    x, y, w, h = region
    s = screen_for_physical_point(x + w // 2, y + h // 2)
    g, dpr = s.geometry(), s.devicePixelRatio()
    lx = g.x() + (x - g.x()) / dpr
    ly = g.y() + (y - g.y()) / dpr
    return QRect(round(lx), round(ly), max(1, round(w / dpr)), max(1, round(h / dpr)))


class _Bubble(QWidget):
    """Base: ventana transparente, sin bordes, encima de todo y que deja pasar los clics."""

    copy_requested = Signal(str, str)      # original, traducción
    correct_requested = Signal(str, str)   # original, traducción

    def __init__(self):
        super().__init__(None)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowTransparentForInput
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.translation = ""
        self.original = ""
        self.offline = False
        self.font_size = 15
        self.opacity = 88        # opacidad del fondo, 0-100 %
        self.text_opacity = 100  # opacidad del texto, 20-100 %
        self._excluded = False
        self.interactive = False
        self._flash_until = 0.0

    def showEvent(self, e):
        super().showEvent(e)
        if not self._excluded:
            self._excluded = winutil.exclude_from_capture(int(self.winId()))

    def set_interactive(self, on: bool):
        """Mientras se mantiene Alt, la ventana deja de ser "atravesable" para poder hacer clic en ella."""
        if on == self.interactive:
            return
        self.interactive = on
        if self.isVisible():
            winutil.set_click_through(int(self.winId()), not on)
        self.update()

    def entry_at(self, pos) -> tuple[str, str] | None:
        return (self.original, self.translation) if self.translation else None

    def mousePressEvent(self, e):
        entry = self.entry_at(e.position().toPoint())
        if not entry:
            return
        if e.button() == Qt.LeftButton:
            self.copy_requested.emit(*entry)
            self._flash_until = time.monotonic() + 1.2
            self.update()
            QTimer.singleShot(1300, self.update)
        elif e.button() == Qt.RightButton:
            self.correct_requested.emit(*entry)

    def _paint_overlay_state(self, p: QPainter):
        """Borde ámbar mientras se puede hacer clic y aviso de "copiado"."""
        if self.interactive:
            pen = p.pen()
            p.setPen(QColor(255, 182, 39, 230))
            p.drawRoundedRect(self.rect().adjusted(1, 1, -2, -2), 8, 8)
            p.setPen(pen)
        if time.monotonic() < self._flash_until:
            p.setFont(self._font(12, True))
            r = QRect(self.width() - 110, 4, 104, 22)
            p.fillRect(r, QColor(31, 95, 58, 235))
            p.setPen(QColor(184, 245, 207))
            p.drawText(r, Qt.AlignCenter, "✓ Copiado")

    def apply_style(self, font_size: int, opacity: int, text_opacity: int = 100):
        self.font_size = font_size
        self.opacity = max(0, min(100, opacity))
        self.text_opacity = max(20, min(100, text_opacity))
        self.update()

    def _draw_text(self, p: QPainter, rect: QRect, flags, text: str, rgb=(255, 255, 255)):
        """Dibuja texto con la opacidad elegida. Con fondo muy transparente añade un contorno oscuro para que se lea."""
        alpha = round(255 * self.text_opacity / 100)
        if self.opacity < 45:
            p.setPen(QColor(0, 0, 0, round(alpha * 0.9)))
            for dx, dy in ((1, 1), (-1, -1), (1, -1), (-1, 1), (0, 2), (2, 0)):
                p.drawText(rect.translated(dx, dy), flags, text)
        p.setPen(QColor(*rgb, alpha))
        p.drawText(rect, flags, text)

    def _font(self, size, bold=False) -> QFont:
        f = QFont("Segoe UI", 1)
        f.setPixelSize(max(8, size))
        f.setBold(bold)
        return f

    def _paint_background(self, p: QPainter):
        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8, 8)
        alpha = round(255 * self.opacity / 100)
        if alpha:
            p.fillPath(path, QColor(18, 18, 26, alpha))
        if self.offline:
            p.setPen(QColor(255, 196, 0, 160))
            p.drawPath(path)
        elif alpha:
            p.setPen(QColor(255, 255, 255, round(40 * self.opacity / 100)))
            p.drawPath(path)


class FloatingOverlay(_Bubble):
    """Traducción colocada sobre la zona seleccionada (tapándola) o justo encima."""

    def __init__(self):
        super().__init__()
        self.position = FLOAT_COVER
        self._region_rect = QRect()

    def set_region(self, logical_rect: QRect, position: str):
        self._region_rect = logical_rect
        # En Windows antiguos no se puede excluir de la captura: tapar el texto rompería el OCR
        if position == FLOAT_COVER and not winutil.supports_capture_exclusion():
            position = FLOAT_ABOVE
        self.position = position
        self._relayout()

    def set_text(self, translation: str, offline: bool = False, original: str = ""):
        self.translation, self.offline, self.original = translation, offline, original
        self._relayout()
        self.update()

    def _fit_font_size(self, width: int, height: int | None) -> tuple[int, int]:
        size = self.font_size
        flags = Qt.TextWordWrap
        while True:
            fm = QFontMetrics(self._font(size, True))
            br = fm.boundingRect(QRect(0, 0, width - 2 * PAD, 10_000), flags, self.translation)
            if height is None or br.height() + 2 * PAD <= height or size <= 9:
                return size, br.height() + 2 * PAD
            size -= 1

    def _relayout(self):
        r = self._region_rect
        if r.isNull() or not self.translation:
            return
        width = max(r.width(), 160)
        if self.position == FLOAT_COVER:
            size, needed = self._fit_font_size(width, r.height())
            self._draw_size = size
            self.setGeometry(QRect(r.x(), r.y(), width, max(r.height(), needed)))
            return
        size, needed = self._fit_font_size(width, None)
        self._draw_size = size
        screen = QGuiApplication.screenAt(r.center()) or QGuiApplication.primaryScreen()
        top = r.y() - needed - 6
        if top < screen.geometry().y():
            top = r.bottom() + 6
        self.setGeometry(QRect(r.x(), top, width, needed))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._paint_background(p)
        p.setFont(self._font(getattr(self, "_draw_size", self.font_size), True))
        rect = self.rect().adjusted(PAD, PAD, -PAD, -PAD)
        align = Qt.AlignVCenter | Qt.AlignLeft | Qt.TextWordWrap
        self._draw_text(p, rect, align, self.translation)
        self._paint_overlay_state(p)


class CornerOverlay(_Bubble):
    """Traducciones en una esquina de la pantalla: un bloque por zona, con el original opcional debajo."""

    def __init__(self):
        super().__init__()
        self.corner = "sup-der"
        self.show_original = True
        self.entries = {}       # índice de zona -> (original, traducción, fuente, sin_conexión)
        self.zone_count = 1
        self._screen = None
        self._block_rects = []  # (rect, índice de zona)

    def configure(self, corner: str, show_original: bool, region_rect: QRect | None, zone_count: int = 1):
        self.corner, self.show_original, self.zone_count = corner, show_original, max(1, zone_count)
        self._screen = None
        if region_rect is not None and not region_rect.isNull():
            self._screen = QGuiApplication.screenAt(region_rect.center())
        self._relayout()

    def set_entry(self, index: int, original: str, translation: str, source: str, offline: bool = False):
        self.entries[index] = (original, translation, source, offline)
        self.offline = any(e[3] for e in self.entries.values())
        self._relayout()
        self.update()

    def clear_entry(self, index: int):
        self.entries.pop(index, None)
        self.offline = any(e[3] for e in self.entries.values())
        self._relayout()
        self.update()

    def clear_all(self):
        self.entries = {}
        self.offline = False

    def has_entries(self) -> bool:
        return bool(self.entries)

    def _blocks(self, width):
        """Medidas de cada bloque: (índice, entrada, alto traducción, alto original, alto pie)."""
        flags = Qt.TextWordWrap
        inner = QRect(0, 0, width - 2 * PAD, 10_000)
        fm_t = QFontMetrics(self._font(self.font_size, True))
        fm_o = QFontMetrics(self._font(max(9, self.font_size - 4)))
        footer = QFontMetrics(self._font(10)).height() + 2
        out = []
        for idx in sorted(self.entries):
            e = self.entries[idx]
            t_h = fm_t.boundingRect(inner, flags, e[1]).height()
            o_h = fm_o.boundingRect(inner, flags, e[0]).height() + 4 if self.show_original and e[0] else 0
            out.append((idx, e, t_h, o_h, footer))
        return out

    def _relayout(self):
        if not self.entries:
            return
        screen = self._screen or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        width = min(CORNER_MAX_WIDTH, avail.width() - 2 * CORNER_MARGIN)
        blocks = self._blocks(width)
        height = sum(t + o + f for _, _, t, o, f in blocks) + BLOCK_GAP * (len(blocks) - 1) + 2 * PAD
        height = min(height, avail.height() - 2 * CORNER_MARGIN)
        x = avail.right() - width - CORNER_MARGIN if self.corner.endswith("der") else avail.x() + CORNER_MARGIN
        y = avail.y() + CORNER_MARGIN if self.corner.startswith("sup") else avail.bottom() - height - CORNER_MARGIN
        self.setGeometry(QRect(QPoint(x, y), QPoint(x + width - 1, y + height - 1)))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._paint_background(p)
        width = self.width()
        y = PAD
        blocks = self._blocks(width)
        self._block_rects = []
        for n, (idx, (original, translation, source, offline), t_h, o_h, footer) in enumerate(blocks):
            if n:
                p.setPen(QColor(255, 255, 255, 40))
                p.drawLine(PAD, y + BLOCK_GAP // 2, width - PAD, y + BLOCK_GAP // 2)
                y += BLOCK_GAP
            self._block_rects.append((QRect(0, y - PAD // 2, width, t_h + o_h + footer + PAD), idx))
            p.setFont(self._font(self.font_size, True))
            self._draw_text(p, QRect(PAD, y, width - 2 * PAD, t_h), Qt.TextWordWrap, translation)
            y += t_h
            if o_h:
                p.setFont(self._font(max(9, self.font_size - 4)))
                self._draw_text(p, QRect(PAD, y + 4, width - 2 * PAD, o_h), Qt.TextWordWrap, original, (190, 190, 200))
                y += o_h
            p.setFont(self._font(10))
            label = "⚠ sin conexión: se reintentará" if offline else f"vía {source}"
            if self.zone_count > 1:
                label = f"Zona {idx + 1}  ·  {label}"
            color = (255, 196, 0) if offline else (160, 160, 175)
            self._draw_text(p, QRect(PAD, y, width - 2 * PAD, footer), Qt.AlignRight | Qt.AlignVCenter, label, color)
            y += footer
        self._paint_overlay_state(p)

    def entry_at(self, pos):
        for rect, idx in self._block_rects:
            if rect.contains(pos) and idx in self.entries:
                original, translation = self.entries[idx][0], self.entries[idx][1]
                return original, translation
        return None
