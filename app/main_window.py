"""Ventana principal de Glosa: estado, perfiles, historial, ajustes y acerca de.

La ventana es solo una forma cómoda de controlar la app: todo sigue funcionando en segundo plano
(bandeja del sistema y atajos) aunque esté cerrada.
"""
import os
import time

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, APP_TAGLINE, GITHUB_REPO, __version__, winutil
from .config import MODE_LABELS, MODES
from .hotkeys import HOTKEYS
from .paths import data_dir, resource_path

ACCENT = "#7A3FE4"
AMBER = "#FFB627"

STYLE = f"""
QMainWindow, QWidget#page {{ background: #15161f; }}
QWidget {{ color: #e8e8f0; font-family: 'Segoe UI'; font-size: 13px; }}
QListWidget#nav {{
    background: #1d1e2b; border: none; padding: 8px 6px; outline: 0;
}}
QListWidget#nav::item {{ padding: 10px 12px; border-radius: 8px; margin: 2px 0; }}
QListWidget#nav::item:selected {{ background: {ACCENT}; color: white; }}
QListWidget#nav::item:hover:!selected {{ background: #2a2b3d; }}
QFrame#card {{ background: #1f2030; border: 1px solid #2c2d42; border-radius: 12px; }}
QLabel#h1 {{ font-size: 22px; font-weight: 700; }}
QLabel#h2 {{ font-size: 15px; font-weight: 700; }}
QLabel#muted {{ color: #9a9bb3; }}
QLabel#pill {{ background: #2c2d42; border-radius: 10px; padding: 3px 10px; }}
QLabel#pillOn {{ background: #1f5f3a; color: #b8f5cf; border-radius: 10px; padding: 3px 10px; }}
QLabel#pillOff {{ background: #5f4a1f; color: #ffe2a8; border-radius: 10px; padding: 3px 10px; }}
QPushButton {{
    background: #2c2d42; border: 1px solid #3a3b55; border-radius: 8px; padding: 7px 14px;
}}
QPushButton:hover {{ background: #36374f; }}
QPushButton:disabled {{ color: #66677d; }}
QPushButton#primary {{ background: {ACCENT}; border-color: {ACCENT}; color: white; font-weight: 600; }}
QPushButton#primary:hover {{ background: #8a55ee; }}
QPushButton#danger {{ background: #4a2230; border-color: #6b2c40; }}
QPushButton#danger:hover {{ background: #5c2a3b; }}
QListWidget {{ background: #1a1b27; border: 1px solid #2c2d42; border-radius: 8px; padding: 4px; outline: 0; }}
QListWidget::item {{ padding: 7px; border-radius: 6px; }}
QListWidget::item:selected {{ background: #3a2f63; color: white; }}
QLineEdit, QComboBox {{
    background: #1a1b27; border: 1px solid #3a3b55; border-radius: 6px; padding: 6px 8px;
}}
QComboBox QAbstractItemView {{ background: #1f2030; selection-background-color: {ACCENT}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; }}
QSlider::groove:horizontal {{ height: 6px; background: #2c2d42; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {AMBER}; width: 16px; margin: -6px 0; border-radius: 8px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
"""


def _card(*widgets_or_layouts, spacing=10) -> QFrame:
    card = QFrame()
    card.setObjectName("card")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(16, 14, 16, 14)
    lay.setSpacing(spacing)
    for w in widgets_or_layouts:
        if isinstance(w, QWidget):
            lay.addWidget(w)
        else:
            lay.addLayout(w)
    return card


def _label(text, name=None, wrap=False) -> QLabel:
    lab = QLabel(text)
    if name:
        lab.setObjectName(name)
    lab.setWordWrap(wrap)
    return lab


def _button(text, slot, name=None) -> QPushButton:
    b = QPushButton(text)
    if name:
        b.setObjectName(name)
    b.setCursor(Qt.PointingHandCursor)
    b.clicked.connect(slot)
    b.setMinimumWidth(b.fontMetrics().horizontalAdvance(text) + 40)  # que el relleno del estilo no corte el texto
    return b


def _page() -> tuple[QWidget, QVBoxLayout]:
    page = QWidget()
    page.setObjectName("page")
    lay = QVBoxLayout(page)
    lay.setContentsMargins(24, 22, 24, 22)
    lay.setSpacing(14)
    return page, lay


def _zone_text(i: int, r) -> str:
    x, y, w, h = r
    return f"Zona {i + 1}:  {w} × {h} px  en ({x}, {y})"


class MainWindow(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.c = controller
        self._told_background = False
        self.setWindowTitle(f"{APP_NAME} · {APP_TAGLINE}")
        self.setWindowIcon(QIcon(str(resource_path("assets", "icon.ico"))))
        self.resize(980, 720)
        self.setMinimumSize(880, 640)
        self.setStyleSheet(STYLE)

        root = QWidget()
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)

        # Barra lateral
        side = QWidget()
        side.setFixedWidth(200)
        side.setStyleSheet("background: #1d1e2b;")
        sv = QVBoxLayout(side)
        sv.setContentsMargins(10, 18, 10, 12)
        brand = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QPixmap(str(resource_path("assets", "logo.png"))).scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        name = _label(APP_NAME, "h2")
        name.setStyleSheet("font-size: 19px;")
        brand.addWidget(logo)
        brand.addWidget(name)
        brand.addStretch()
        sv.addLayout(brand)
        sv.addSpacing(12)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for text in ("🏠  Inicio", "🗂️  Perfiles", "🕘  Historial", "⚙️  Ajustes", "ℹ️  Acerca de"):
            self.nav.addItem(QListWidgetItem(text))
        sv.addWidget(self.nav, 1)
        ver = _label(f"Versión {__version__}", "muted")
        sv.addWidget(ver)
        h.addWidget(side)

        self.stack = QStackedWidget()
        h.addWidget(self.stack, 1)
        for build in (self._build_home, self._build_profiles, self._build_history, self._build_settings, self._build_about):
            self.stack.addWidget(self._scrollable(build()))
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.currentRowChanged.connect(lambda _: self.refresh())
        self.nav.setCurrentRow(0)
        self.setCentralWidget(root)

    @staticmethod
    def _scrollable(page: QWidget) -> QScrollArea:
        """Si la ventana es pequeña, la página se desplaza en vez de aplastarse."""
        area = QScrollArea()
        area.setWidget(page)
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        area.setStyleSheet("QScrollArea { background: #15161f; border: none; }")
        return area

    # ================= Inicio =================
    def _build_home(self):
        page, lay = _page()
        lay.addWidget(_label("Inicio", "h1"))

        self.home_profile = _label("", "h2")
        self.home_state = _label("", "pillOn")
        self.home_detail = _label("", "muted", wrap=True)
        top = QHBoxLayout()
        top.addWidget(self.home_profile)
        top.addStretch()
        top.addWidget(self.home_state)
        self.btn_zones = _button("✏️  Editar zonas en pantalla", lambda: self.c.edit_profile_zones(self.c.cfg.active_profile), "primary")
        self.btn_pause = _button("Pausar", self.c.toggle_pause)
        self.btn_hide = _button("Ocultar traducción", self.c.toggle_hidden)
        self.btn_switch = _button("Cambiar de perfil…", lambda: self.nav.setCurrentRow(1))
        self.btn_speak = _button("🔊  Leer última", self.c.speak_last)
        row = QHBoxLayout()
        for b in (self.btn_zones, self.btn_pause, self.btn_hide, self.btn_speak, self.btn_switch):
            row.addWidget(b)
        row.addStretch()
        lay.addWidget(_card(top, self.home_detail, row))

        # Apariencia rápida
        self.mode_combo = QComboBox()
        for m in MODES:
            self.mode_combo.addItem(MODE_LABELS[m], m)
        self.mode_combo.currentIndexChanged.connect(self._on_mode_combo)
        self.sl_bg, bg_row, self.lb_bg = self._slider(0, 100)
        self.sl_txt, txt_row, self.lb_txt = self._slider(20, 100)
        self.sl_bg.valueChanged.connect(self._on_opacity)
        self.sl_txt.valueChanged.connect(self._on_opacity)
        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.addWidget(_label("Modo de visualización"), 0, 0)
        grid.addWidget(self.mode_combo, 0, 1)
        grid.addWidget(_label("Opacidad del fondo"), 1, 0)
        grid.addLayout(bg_row, 1, 1)
        grid.addWidget(_label("Opacidad del texto"), 2, 0)
        grid.addLayout(txt_row, 2, 1)
        self.chk_tts_home = QCheckBox("Leer en voz alta cada traducción nueva")
        self.chk_tts_home.toggled.connect(lambda on: None if self._refreshing else self.c.set_tts(auto=on))
        grid.addWidget(self.chk_tts_home, 3, 0, 1, 2)
        grid.setColumnStretch(1, 1)
        lay.addWidget(_card(_label("Apariencia rápida", "h2"), grid))

        # Última traducción
        self.home_last = _label("Todavía no hay traducciones en esta sesión.", "muted", wrap=True)
        self.home_last.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(_card(
            _label("Última traducción", "h2"), self.home_last,
            _label("Consejo: mantén <b>Alt</b> y haz clic en una traducción en pantalla para copiarla, "
                   "o <b>Alt + clic derecho</b> para corregirla.", "muted", wrap=True),
        ))
        lay.addStretch()
        return page

    def _slider(self, lo, hi):
        s = QSlider(Qt.Horizontal)
        s.setRange(lo, hi)
        lab = QLabel()
        lab.setMinimumWidth(44)
        s.valueChanged.connect(lambda v: lab.setText(f"{v} %"))
        row = QHBoxLayout()
        row.addWidget(s)
        row.addWidget(lab)
        return s, row, lab

    def _on_mode_combo(self, _):
        mode = self.mode_combo.currentData()
        if mode and mode != self.c.cfg.display_mode:
            self.c.set_mode(mode)

    def _on_opacity(self, _):
        if self._refreshing:
            return
        self.c.set_opacity(self.sl_bg.value(), self.sl_txt.value())

    # ================= Perfiles =================
    def _build_profiles(self):
        page, lay = _page()
        head = QHBoxLayout()
        head.addWidget(_label("Perfiles", "h1"))
        head.addStretch()
        self.chk_auto = QCheckBox("Cambiar de perfil automáticamente según el programa o juego")
        self.chk_auto.toggled.connect(lambda on: None if self._refreshing else self.c.set_auto_profile(on))
        head.addWidget(self.chk_auto)
        lay.addLayout(head)
        lay.addWidget(_label(
            "Cada perfil guarda sus zonas de pantalla. Si lo vinculas a un programa o juego, "
            "Glosa lo activa sola cuando ese programa pasa a primer plano.", "muted", wrap=True))

        body = QHBoxLayout()
        body.setSpacing(14)

        # Lista de perfiles
        left = QVBoxLayout()
        self.prof_list = QListWidget()
        self.prof_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.prof_list.setWordWrap(True)
        self.prof_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.prof_list.currentRowChanged.connect(self._on_profile_selected)
        self.prof_list.itemDoubleClicked.connect(lambda _: self._activate_selected())
        left.addWidget(self.prof_list, 1)
        lrow = QHBoxLayout()
        lrow.addWidget(_button("＋ Nuevo", self._new_profile, "primary"))
        lrow.addWidget(_button("Duplicar", self._duplicate_profile))
        left.addLayout(lrow)
        lw = QWidget()
        lw.setLayout(left)
        lw.setFixedWidth(270)
        body.addWidget(lw)

        # Detalle
        self.det_name = QLineEdit()
        self.det_name.setPlaceholderText("Nombre del perfil")
        self.det_name.editingFinished.connect(self._rename_selected)
        self.det_active = _label("", "pill")
        name_row = QHBoxLayout()
        name_row.addWidget(self.det_name, 1)
        name_row.addWidget(self.det_active)

        self.det_game = QComboBox()
        self.det_game.setEditable(True)
        self.det_game.setInsertPolicy(QComboBox.NoInsert)
        self.det_game.lineEdit().setPlaceholderText("ningún programa (no se activa solo)")
        game_row = QVBoxLayout()
        game_row.addWidget(self.det_game)
        game_btns = QHBoxLayout()
        game_btns.addWidget(_button("Elegir de los programas abiertos…", self._fill_running_programs))
        game_btns.addWidget(_button("Vincular", self._link_selected))
        game_btns.addWidget(_button("Desvincular", self._unlink_selected))
        game_btns.addStretch()
        game_row.addLayout(game_btns)

        self.det_zones = QListWidget()
        self.det_zones.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.det_zones.setWordWrap(True)
        self.det_zones.setMinimumHeight(70)
        zrow = QHBoxLayout()
        zrow.addWidget(_button("✏️  Editar zonas en pantalla", self._edit_selected_zones, "primary"))
        zrow.addWidget(_button("Quitar zona seleccionada", self._remove_selected_zone))
        zrow.addStretch()

        self.det_glossary = QListWidget()
        self.det_glossary.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.det_glossary.setMinimumHeight(70)
        self.det_glossary.itemDoubleClicked.connect(lambda _: self._edit_glossary_term())
        grow = QHBoxLayout()
        grow.addWidget(_button("＋ Añadir término", self._add_glossary_term))
        grow.addWidget(_button("Editar", self._edit_glossary_term))
        grow.addWidget(_button("Quitar", self._remove_glossary_term))
        grow.addStretch()

        arow = QHBoxLayout()
        self.btn_activate = _button("✔  Activar este perfil", self._activate_selected)
        arow.addWidget(self.btn_activate)
        arow.addStretch()
        self.btn_delete = _button("Eliminar perfil", self._delete_selected, "danger")
        arow.addWidget(self.btn_delete)

        detail = _card(
            _label("Nombre", "muted"), name_row,
            _label("Programa o juego vinculado", "muted"), game_row,
            _label("Zonas de pantalla", "muted"), self.det_zones, zrow,
            _label("Glosario del perfil: nombres y términos que se traducen siempre igual (o no se traducen)", "muted", wrap=True),
            self.det_glossary, grow,
            arow,
            spacing=8,
        )
        body.addWidget(detail, 1)
        lay.addLayout(body, 1)
        return page

    def _selected_profile(self):
        row = self.prof_list.currentRow()
        if 0 <= row < len(self.c.cfg.profiles):
            return self.c.cfg.profiles[row]
        return None

    def _on_profile_selected(self, _row):
        if self._refreshing:
            return
        self._fill_profile_detail()

    def _fill_profile_detail(self):
        p = self._selected_profile()
        enabled = p is not None
        for w in (self.det_name, self.det_game, self.det_zones, self.det_glossary, self.btn_activate, self.btn_delete):
            w.setEnabled(enabled)
        if not p:
            return
        self.det_name.setText(p["name"])
        is_active = p["name"] == self.c.cfg.active_profile
        self.det_active.setText("● Activo" if is_active else "Inactivo")
        self.det_active.setObjectName("pillOn" if is_active else "pill")
        self.det_active.style().unpolish(self.det_active)
        self.det_active.style().polish(self.det_active)
        self.btn_activate.setEnabled(not is_active)
        self.btn_delete.setEnabled(len(self.c.cfg.profiles) > 1)
        self.det_game.setEditText(p.get("game", ""))
        self.det_zones.clear()
        for i, r in enumerate(p["regions"]):
            self.det_zones.addItem(_zone_text(i, r))
        if not p["regions"]:
            item = QListWidgetItem("Sin zonas: pulsa «Editar zonas en pantalla» para marcarlas")
            item.setFlags(Qt.NoItemFlags)
            self.det_zones.addItem(item)
        self.det_glossary.clear()
        glossary = p.get("glossary", {})
        for term in sorted(glossary, key=str.lower):
            target = glossary[term].strip() or "(no traducir)"
            item = QListWidgetItem(f"{term}   →   {target}")
            item.setData(Qt.UserRole, term)
            self.det_glossary.addItem(item)
        if not glossary:
            item = QListWidgetItem("Vacío. Ejemplo: «Mercenary → Mercenario» o «Kylian → (no traducir)»")
            item.setFlags(Qt.NoItemFlags)
            self.det_glossary.addItem(item)

    def _fill_running_programs(self):
        current = self.det_game.currentText()
        self.det_game.clear()
        for exe, title in winutil.list_windows():
            short = title if len(title) <= 45 else title[:42] + "…"
            self.det_game.addItem(f"{exe}   —   {short}", exe)
        self.det_game.setEditText(current)
        self.det_game.showPopup()

    def _game_from_combo(self) -> str:
        idx = self.det_game.currentIndex()
        text = self.det_game.currentText().strip()
        if idx >= 0 and self.det_game.itemText(idx) == text:
            return self.det_game.itemData(idx) or ""
        return text.split()[0].lower() if text else ""

    def _new_profile(self):
        name, ok = QInputDialog.getText(self, APP_NAME, "Nombre del nuevo perfil:")
        if ok and name.strip():
            p = self.c.cfg.add_profile(name.strip())
            self.c.cfg.save()
            self._select_profile_name(p["name"])

    def _duplicate_profile(self):
        p = self._selected_profile()
        if not p:
            return
        copy = self.c.cfg.add_profile(f"{p['name']} (copia)")
        copy["regions"] = [list(r) for r in p["regions"]]
        self.c.cfg.save()
        self._select_profile_name(copy["name"])

    def _rename_selected(self):
        p = self._selected_profile()
        new = self.det_name.text().strip()
        if p and new and new != p["name"]:
            self.c.rename_profile_to(p["name"], new)
            self._select_profile_name(self.c.cfg.profiles[self.prof_list.currentRow()]["name"])

    def _link_selected(self):
        p = self._selected_profile()
        exe = self._game_from_combo()
        if p and exe:
            if not exe.endswith(".exe"):
                exe += ".exe"
            self.c.set_profile_game(p["name"], exe)
            self.refresh()

    def _unlink_selected(self):
        p = self._selected_profile()
        if p:
            self.c.set_profile_game(p["name"], "")
            self.refresh()

    def _edit_selected_zones(self):
        p = self._selected_profile()
        if p:
            self.c.edit_profile_zones(p["name"])

    def _remove_selected_zone(self):
        p = self._selected_profile()
        row = self.det_zones.currentRow()
        if p and 0 <= row < len(p["regions"]):
            self.c.remove_profile_zone(p["name"], row)
            self.refresh()

    def _glossary_dialog(self, term: str = "", target: str = "") -> tuple[str, str] | None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Término del glosario")
        dlg.setStyleSheet(STYLE)
        form = QFormLayout(dlg)
        e_term = QLineEdit(term)
        e_term.setPlaceholderText("Ej.: Mercenary, Kylian, Sky Armor")
        e_target = QLineEdit(target)
        e_target.setPlaceholderText("Vacío = no traducirlo (se deja tal cual)")
        form.addRow("Término original:", e_term)
        form.addRow("Traducción fija:", e_target)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Guardar")
        bb.button(QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        form.addRow(bb)
        dlg.resize(460, 140)
        if dlg.exec() and e_term.text().strip():
            return e_term.text().strip(), e_target.text().strip()
        return None

    def _add_glossary_term(self):
        p = self._selected_profile()
        if not p:
            return
        res = self._glossary_dialog()
        if res:
            g = dict(p.get("glossary", {}))
            g[res[0]] = res[1]
            self.c.set_profile_glossary(p["name"], g)
            self._fill_profile_detail()

    def _edit_glossary_term(self):
        p = self._selected_profile()
        item = self.det_glossary.currentItem()
        if not p or not item or not item.data(Qt.UserRole):
            return
        term = item.data(Qt.UserRole)
        g = dict(p.get("glossary", {}))
        res = self._glossary_dialog(term, g.get(term, ""))
        if res:
            g.pop(term, None)
            g[res[0]] = res[1]
            self.c.set_profile_glossary(p["name"], g)
            self._fill_profile_detail()

    def _remove_glossary_term(self):
        p = self._selected_profile()
        item = self.det_glossary.currentItem()
        if p and item and item.data(Qt.UserRole):
            g = dict(p.get("glossary", {}))
            g.pop(item.data(Qt.UserRole), None)
            self.c.set_profile_glossary(p["name"], g)
            self._fill_profile_detail()

    def _activate_selected(self):
        p = self._selected_profile()
        if p and p["name"] != self.c.cfg.active_profile:
            self.c.switch_profile(p["name"])

    def _delete_selected(self):
        p = self._selected_profile()
        if not p or len(self.c.cfg.profiles) <= 1:
            return
        if QMessageBox.question(self, APP_NAME, f"¿Eliminar el perfil «{p['name']}» y sus zonas?") == QMessageBox.Yes:
            self.c.delete_profile_named(p["name"])

    def _select_profile_name(self, name):
        self.refresh()
        for i, p in enumerate(self.c.cfg.profiles):
            if p["name"] == name:
                self.prof_list.setCurrentRow(i)
                break
        self._fill_profile_detail()

    # ================= Historial =================
    def _build_history(self):
        page, lay = _page()
        head = QHBoxLayout()
        head.addWidget(_label("Historial", "h1"))
        head.addStretch()
        head.addWidget(_button("Copiar", self._copy_history))
        head.addWidget(_button("🔊  Leer", self._speak_history))
        head.addWidget(_button("✏️  Corregir…", self._correct_history, "primary"))
        head.addWidget(_button("Vaciar", lambda: self.history.clear()))
        lay.addLayout(head)
        lay.addWidget(_label("Las últimas traducciones de esta sesión (las más recientes arriba). Si una traducción "
                             "es mala, selecciónala y pulsa «Corregir»: se guardará y se usará siempre.", "muted", wrap=True))
        self.history = QListWidget()
        self.history.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.history.setWordWrap(True)
        self.history.setSpacing(2)
        self.history.itemDoubleClicked.connect(lambda _: self._correct_history())
        lay.addWidget(self.history, 1)
        return page

    def add_history(self, zone: int, original: str, translation: str, source: str):
        stamp = time.strftime("%H:%M:%S")
        item = QListWidgetItem(f"{translation}\n{original}\n{stamp} · Zona {zone + 1} · {source}")
        item.setData(Qt.UserRole, (original, translation, stamp, zone, source))
        self.history.insertItem(0, item)
        while self.history.count() > 200:
            self.history.takeItem(self.history.count() - 1)
        self.home_last.setText(f"<b>{translation}</b><br><span style='color:#9a9bb3'>{original}</span>")

    def _history_entry(self):
        item = self.history.currentItem()
        return item.data(Qt.UserRole) if item else None

    def _copy_history(self):
        entry = self._history_entry()
        if entry:
            QApplication.clipboard().setText(entry[1])

    def _speak_history(self):
        entry = self._history_entry()
        if entry:
            self.c.speak_text(entry[1])

    def _correct_history(self):
        entry = self._history_entry()
        if entry:
            self.c.correct_translation(entry[0], entry[1])

    def update_history_translation(self, original: str, translation: str):
        for i in range(self.history.count()):
            item = self.history.item(i)
            o, _t, stamp, zone, _source = item.data(Qt.UserRole)
            if o == original:
                item.setData(Qt.UserRole, (o, translation, stamp, zone, "corregida"))
                item.setText(f"{translation}\n{o}\n{stamp} · Zona {zone + 1} · corregida")

    # ================= Ajustes =================
    def _build_settings(self):
        page, lay = _page()
        lay.addWidget(_label("Ajustes", "h1"))
        self.chk_autostart = QCheckBox("Iniciar con Windows (en segundo plano)")
        self.chk_autostart.toggled.connect(lambda on: None if self._refreshing else self.c.set_autostart(on))
        self.chk_updates = QCheckBox("Buscar actualizaciones al iniciar")
        self.chk_updates.toggled.connect(lambda on: None if self._refreshing else self.c.set_check_updates(on))
        lay.addWidget(_card(_label("General", "h2"), self.chk_autostart, self.chk_updates))
        lay.addWidget(_card(
            _label("Apariencia, lectura, idioma y OCR", "h2"),
            _label("Tamaño de letra, posición, esquina, intervalo de lectura, idioma de destino, OCR en inglés "
                   "y memoria de traducciones.", "muted", wrap=True),
            _button("Abrir todos los ajustes…", self.c.open_settings, "primary"),
        ))
        self.chk_tts = QCheckBox("Leer en voz alta cada traducción nueva")
        self.chk_tts.toggled.connect(lambda on: None if self._refreshing else self.c.set_tts(auto=on))
        self.cmb_voice = QComboBox()
        self.cmb_voice.setMinimumHeight(32)
        self.cmb_voice.currentIndexChanged.connect(
            lambda _: None if self._refreshing else self.c.set_tts(voice=self.cmb_voice.currentText()))
        self.sl_rate = QSlider(Qt.Horizontal)
        self.sl_rate.setRange(-5, 5)
        self.sl_rate.valueChanged.connect(lambda v: None if self._refreshing else self.c.set_tts(rate=v))
        vgrid = QGridLayout()
        vgrid.addWidget(_label("Voz de Windows"), 0, 0)
        vgrid.addWidget(self.cmb_voice, 0, 1)
        vgrid.addWidget(_label("Velocidad"), 1, 0)
        rate_row = QHBoxLayout()
        rate_row.addWidget(_label("lenta", "muted"))
        rate_row.addWidget(self.sl_rate)
        rate_row.addWidget(_label("rápida", "muted"))
        vgrid.addLayout(rate_row, 1, 1)
        vgrid.setColumnStretch(1, 1)
        test_row = QHBoxLayout()
        test_row.addWidget(_button("▶  Probar voz", lambda: self.c.speak_text("Hola, así sonarán las traducciones.")))
        test_row.addStretch()
        lay.addWidget(_card(
            _label("Lectura en voz alta", "h2"),
            _label("Usa las voces que trae Windows: gratis y sin internet. Con Ctrl+Shift+L se lee la última traducción.",
                   "muted", wrap=True),
            self.chk_tts, vgrid, test_row,
        ))
        keys = "<br>".join(f"<b>{v[2]}</b> &nbsp; {v[3]}" for v in HOTKEYS.values())
        keys += "<br><b>Alt + clic</b> &nbsp; Copiar una traducción en pantalla<br><b>Alt + clic derecho</b> &nbsp; Corregirla"
        lay.addWidget(_card(_label("Atajos (funcionan con el juego o programa en primer plano)", "h2"), _label(keys)))
        lay.addStretch()
        return page

    # ================= Acerca de =================
    def _build_about(self):
        page, lay = _page()
        lay.addWidget(_label("Acerca de", "h1"))
        logo = QLabel()
        logo.setPixmap(QPixmap(str(resource_path("assets", "logo.png"))).scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        info = QVBoxLayout()
        info.addWidget(_label(f"{APP_NAME} {__version__}", "h1"))
        info.addWidget(_label(APP_TAGLINE, "muted"))
        info.addWidget(_label(
            "Código abierto bajo la licencia PolyForm Shield 1.0.0: se puede usar gratis, también en empresas, "
            "pero no venderla ni ofrecerla como otro producto.", wrap=True))
        top = QHBoxLayout()
        top.addWidget(logo)
        top.addSpacing(12)
        top.addLayout(info, 1)
        btns = QHBoxLayout()
        btns.addWidget(_button("Buscar actualizaciones", self.c.manual_update_check, "primary"))
        btns.addWidget(_button("Página del proyecto", lambda: QDesktopServices.openUrl(QUrl(f"https://github.com/{GITHUB_REPO}"))))
        btns.addWidget(_button("Abrir carpeta de datos", lambda: os.startfile(str(data_dir()))))
        btns.addStretch()
        lay.addWidget(_card(top, btns))
        self.about_ocr = _label("", "muted")
        lay.addWidget(_card(_label("Estado", "h2"), self.about_ocr))
        lay.addStretch()
        return page

    # ================= Refresco general =================
    _refreshing = False

    def refresh(self):
        """Vuelve a pintar la ventana con el estado actual del controlador."""
        if not self.isVisible():
            return
        self._refreshing = True
        try:
            c, cfg = self.c, self.c.cfg
            p = c.profile
            n = len(p["regions"])
            self.home_profile.setText(f"Perfil activo: {p['name']}")
            if c.paused:
                state, obj = "⏸  En pausa", "pillOff"
            elif not n:
                state, obj = "Sin zonas", "pillOff"
            else:
                state, obj = "●  Leyendo en vivo", "pillOn"
            self.home_state.setText(state)
            self.home_state.setObjectName(obj)
            self.home_state.style().unpolish(self.home_state)
            self.home_state.style().polish(self.home_state)
            game = f" · vinculado a {p['game']}" if p.get("game") else " · sin programa vinculado"
            self.home_detail.setText(
                f"{n} zona(s){game}. " + ("" if n else "Pulsa «Editar zonas en pantalla» para marcar dónde aparece el texto.")
            )
            self.btn_pause.setText("▶  Reanudar" if c.paused else "⏸  Pausar")
            self.btn_hide.setText("Mostrar traducción" if c.hidden else "Ocultar traducción")
            self.mode_combo.setCurrentIndex(max(0, self.mode_combo.findData(cfg.display_mode)))
            self.sl_bg.setValue(cfg.opacity)
            self.sl_txt.setValue(cfg.text_opacity)
            self.lb_bg.setText(f"{cfg.opacity} %")
            self.lb_txt.setText(f"{cfg.text_opacity} %")

            # Perfiles
            self.chk_auto.setChecked(cfg.auto_profile)
            selected = self._selected_profile()
            selected_name = selected["name"] if selected else cfg.active_profile
            self.prof_list.clear()
            row_to_select = 0
            for i, prof in enumerate(cfg.profiles):
                active = prof["name"] == cfg.active_profile
                game = prof.get("game") or "sin programa"
                item = QListWidgetItem(f"{'● ' if active else '   '}{prof['name']}\n     {len(prof['regions'])} zona(s) · {game}")
                if active:
                    f = QFont()
                    f.setBold(True)
                    item.setFont(f)
                self.prof_list.addItem(item)
                if prof["name"] == selected_name:
                    row_to_select = i
            self.prof_list.setCurrentRow(row_to_select)

            # Voz
            self.chk_tts_home.setChecked(cfg.tts_auto)
            self.chk_tts.setChecked(cfg.tts_auto)
            if self.cmb_voice.count() == 0:
                voices = c.speaker.voices()
                self.cmb_voice.addItems(voices or ["(no hay voces de Windows disponibles)"])
            idx = self.cmb_voice.findText(cfg.tts_voice)
            self.cmb_voice.setCurrentIndex(idx if idx >= 0 else 0)
            self.sl_rate.setValue(cfg.tts_rate)

            # Ajustes y estado
            self.chk_autostart.setChecked(cfg.autostart)
            self.chk_updates.setChecked(cfg.check_updates)
            ocr = c.ocr_language or "—"
            self.about_ocr.setText(
                f"OCR de Windows en uso: {ocr}  ·  Frases en la memoria: {c.translator.memory_size()}  ·  "
                f"Perfiles: {len(cfg.profiles)}"
            )
        finally:
            self._refreshing = False
        self._fill_profile_detail()

    def show_and_raise(self):
        self.show()
        self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
        self.raise_()
        self.activateWindow()
        winutil.bring_to_front(int(self.winId()))
        self.refresh()

    def closeEvent(self, e):
        # Cerrar la ventana no cierra Glosa: sigue en la bandeja
        e.ignore()
        self.hide()
        if not self._told_background:
            self._told_background = True
            self.c.notify(APP_NAME, "Glosa sigue funcionando en segundo plano. Ábrela desde el icono junto al reloj.")
