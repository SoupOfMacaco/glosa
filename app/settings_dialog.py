"""Ventana de ajustes."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)

from .config import CORNERS, FLOAT_LABELS, MODE_LABELS, TARGET_LANGS
from .hotkeys import HOTKEYS


def _combo(options: dict, current: str) -> QComboBox:
    c = QComboBox()
    for key, label in options.items():
        c.addItem(label, key)
    idx = c.findData(current)
    c.setCurrentIndex(max(0, idx))
    return c


class SettingsDialog(QDialog):
    @staticmethod
    def _slider(lo: int, hi: int, value: int):
        s = QSlider(Qt.Horizontal)
        s.setRange(lo, hi)
        s.setValue(max(lo, min(hi, value)))
        label = QLabel(f"{s.value()} %")
        label.setMinimumWidth(40)
        s.valueChanged.connect(lambda v: label.setText(f"{v} %"))
        row = QHBoxLayout()
        row.addWidget(s)
        row.addWidget(label)
        return s, row

    def __init__(self, config, ocr_language: str, memory_size: int, on_install_english, on_clear_memory,
                 on_preview=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajustes · Glosa")
        self.setMinimumWidth(460)
        self.config = config
        lay = QVBoxLayout(self)

        # --- Visualización ---
        g = QGroupBox("Dónde se muestra la traducción")
        f = QFormLayout(g)
        self.mode = _combo(MODE_LABELS, config.display_mode)
        self.float_pos = _combo(FLOAT_LABELS, config.float_position)
        self.corner = _combo(CORNERS, config.corner)
        self.font_size = QSpinBox()
        self.font_size.setRange(9, 40)
        self.font_size.setValue(config.font_size)
        self.opacity, opacity_row = self._slider(0, 100, config.opacity)
        self.text_opacity, text_row = self._slider(20, 100, config.text_opacity)
        self.opacity.setToolTip("0 % = sin fondo (el texto lleva un contorno oscuro para que se lea)")
        self.show_original = QCheckBox("Mostrar también el texto original en la esquina")
        self.show_original.setChecked(config.show_original)
        self.hide_empty = QCheckBox("Ocultar la traducción cuando no hay texto")
        self.hide_empty.setChecked(config.hide_when_empty)
        f.addRow("Modo:", self.mode)
        f.addRow("Flotante:", self.float_pos)
        f.addRow("Esquina:", self.corner)
        f.addRow("Tamaño de letra:", self.font_size)
        f.addRow("Opacidad del fondo:", opacity_row)
        f.addRow("Opacidad del texto:", text_row)
        f.addRow(self.show_original)
        f.addRow(self.hide_empty)
        # Vista previa en vivo: la traducción en pantalla cambia mientras mueves los controles
        if on_preview:
            preview = lambda *_: on_preview(self.font_size.value(), self.opacity.value(), self.text_opacity.value())
            self.opacity.valueChanged.connect(preview)
            self.text_opacity.valueChanged.connect(preview)
            self.font_size.valueChanged.connect(preview)
        lay.addWidget(g)

        # --- Lectura ---
        g = QGroupBox("Lectura en vivo")
        f = QFormLayout(g)
        self.interval = QSpinBox()
        self.interval.setRange(100, 2000)
        self.interval.setSingleStep(50)
        self.interval.setSuffix(" ms")
        self.interval.setValue(config.interval_ms)
        self.wait_typing = QCheckBox("Esperar a que el texto termine de escribirse")
        self.wait_typing.setChecked(config.wait_typing)
        self.spellfix = QCheckBox("Corregir errores típicos del OCR (inglés)")
        self.spellfix.setChecked(config.spellfix)
        self.target = _combo(TARGET_LANGS, config.target_lang)
        f.addRow("Revisar la zona cada:", self.interval)
        f.addRow(self.wait_typing)
        f.addRow(self.spellfix)
        f.addRow("Traducir al:", self.target)
        ocr_row = QHBoxLayout()
        ocr_row.addWidget(QLabel(ocr_language or "—"))
        if not (ocr_language or "").lower().startswith("en"):
            b = QPushButton("Instalar OCR en inglés…")
            b.setToolTip("Mejora mucho la lectura de textos en inglés. Pide permisos de administrador.")
            b.clicked.connect(on_install_english)
            ocr_row.addWidget(b)
        ocr_row.addStretch()
        f.addRow("Idioma del OCR:", ocr_row)
        lay.addWidget(g)

        # --- Sistema ---
        g = QGroupBox("Sistema")
        f = QFormLayout(g)
        self.autostart = QCheckBox("Iniciar con Windows")
        self.autostart.setChecked(config.autostart)
        self.updates = QCheckBox("Buscar actualizaciones al iniciar")
        self.updates.setChecked(config.check_updates)
        mem_row = QHBoxLayout()
        self.mem_label = QLabel(f"{memory_size} frases guardadas")
        clear = QPushButton("Vaciar")
        clear.clicked.connect(lambda: (on_clear_memory(), self.mem_label.setText("0 frases guardadas")))
        mem_row.addWidget(self.mem_label)
        mem_row.addWidget(clear)
        mem_row.addStretch()
        f.addRow(self.autostart)
        f.addRow(self.updates)
        f.addRow("Memoria de traducciones:", mem_row)
        keys = "<br>".join(f"<b>{v[2]}</b>: {v[3]}" for v in HOTKEYS.values())
        f.addRow("Atajos:", QLabel(keys))
        lay.addWidget(g)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Guardar")
        bb.button(QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def apply_to(self, cfg):
        cfg.display_mode = self.mode.currentData()
        cfg.float_position = self.float_pos.currentData()
        cfg.corner = self.corner.currentData()
        cfg.font_size = self.font_size.value()
        cfg.opacity = self.opacity.value()
        cfg.text_opacity = self.text_opacity.value()
        cfg.show_original = self.show_original.isChecked()
        cfg.hide_when_empty = self.hide_empty.isChecked()
        cfg.interval_ms = self.interval.value()
        cfg.wait_typing = self.wait_typing.isChecked()
        cfg.spellfix = self.spellfix.isChecked()
        cfg.target_lang = self.target.currentData()
        cfg.autostart = self.autostart.isChecked()
        cfg.check_updates = self.updates.isChecked()
