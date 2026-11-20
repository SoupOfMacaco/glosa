"""Ventanas flotantes con la traducción (siempre encima y sin capturar el ratón)."""
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QPainter, QPainterPath
from PySide6.QtWidgets import QWidget

from . import winutil
from .config import FLOAT_ABOVE, FLOAT_COVER

PAD = 10
CORNER_MARGIN = 24
CORNER_MAX_WIDTH = 520


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
        self.opacity = 88
        self._excluded = False

    def showEvent(self, e):
        super().showEvent(e)
        if not self._excluded:
            self._excluded = winutil.exclude_from_capture(int(self.winId()))

    def apply_style(self, font_size: int, opacity: int):
        self.font_size, self.opacity = font_size, opacity

    def _font(self, size, bold=False) -> QFont:
        f = QFont("Segoe UI", 1)
        f.setPixelSize(max(8, size))
        f.setBold(bold)
        return f

    def _paint_background(self, p: QPainter):
        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(0, 0, -1, -1), 8, 8)
        alpha = round(255 * max(30, min(100, self.opacity)) / 100)
        p.fillPath(path, QColor(18, 18, 26, alpha))
        p.setPen(QColor(255, 196, 0, 160) if self.offline else QColor(255, 255, 255, 40))
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

    def set_text(self, translation: str, offline: bool = False):
        self.translation, self.offline = translation, offline
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
        p.setPen(QColor(255, 255, 255))
        rect = self.rect().adjusted(PAD, PAD, -PAD, -PAD)
        align = Qt.AlignVCenter | Qt.AlignLeft | Qt.TextWordWrap
        p.drawText(rect, align, self.translation)


class CornerOverlay(_Bubble):
    """Traducción en una esquina de la pantalla, con el texto original opcional debajo."""

    def __init__(self):
        super().__init__()
        self.corner = "sup-der"
        self.show_original = True
        self.source_label = ""
        self._screen = None

    def configure(self, corner: str, show_original: bool, region_rect: QRect | None):
        self.corner, self.show_original = corner, show_original
        self._screen = None
        if region_rect is not None and not region_rect.isNull():
            self._screen = QGuiApplication.screenAt(region_rect.center())
        self._relayout()

    def set_text(self, original: str, translation: str, source: str, offline: bool = False):
        self.original, self.translation, self.source_label, self.offline = original, translation, source, offline
        self._relayout()
        self.update()

    def _layout_metrics(self, width):
        flags = Qt.TextWordWrap
        inner = QRect(0, 0, width - 2 * PAD, 10_000)
        fm_t = QFontMetrics(self._font(self.font_size, True))
        t_h = fm_t.boundingRect(inner, flags, self.translation).height()
        o_h = 0
        if self.show_original and self.original:
            fm_o = QFontMetrics(self._font(max(9, self.font_size - 4)))
            o_h = fm_o.boundingRect(inner, flags, self.original).height() + 6
        footer = QFontMetrics(self._font(10)).height() + 4
        return t_h, o_h, footer

    def _relayout(self):
        if not self.translation:
            return
        screen = self._screen or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()
        width = min(CORNER_MAX_WIDTH, avail.width() - 2 * CORNER_MARGIN)
        t_h, o_h, footer = self._layout_metrics(width)
        height = t_h + o_h + footer + 2 * PAD
        x = avail.right() - width - CORNER_MARGIN if self.corner.endswith("der") else avail.x() + CORNER_MARGIN
        y = avail.y() + CORNER_MARGIN if self.corner.startswith("sup") else avail.bottom() - height - CORNER_MARGIN
        self.setGeometry(QRect(QPoint(x, y), QPoint(x + width - 1, y + height - 1)))

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        self._paint_background(p)
        width = self.width()
        t_h, o_h, footer = self._layout_metrics(width)
        y = PAD
        p.setPen(QColor(255, 255, 255))
        p.setFont(self._font(self.font_size, True))
        p.drawText(QRect(PAD, y, width - 2 * PAD, t_h), Qt.TextWordWrap, self.translation)
        y += t_h
        if o_h:
            y += 6
            p.setPen(QColor(190, 190, 200))
            p.setFont(self._font(max(9, self.font_size - 4)))
            p.drawText(QRect(PAD, y, width - 2 * PAD, o_h), Qt.TextWordWrap, self.original)
            y += o_h - 6
        p.setPen(QColor(255, 196, 0) if self.offline else QColor(140, 140, 155))
        p.setFont(self._font(10))
        label = "⚠ sin conexión: se reintentará" if self.offline else f"vía {self.source_label}"
        p.drawText(QRect(PAD, self.height() - PAD - footer + 4, width - 2 * PAD, footer), Qt.AlignRight, label)
