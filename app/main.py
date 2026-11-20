"""Punto de entrada: icono en la bandeja del sistema que coordina todo."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QObject, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QIcon, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QInputDialog, QMenu, QMessageBox, QProgressDialog, QSystemTrayIcon

from . import APP_ID, APP_NAME, APP_TAGLINE, GITHUB_REPO, LEGACY_APP_ID, __version__, ocr, winutil
from .config import DEFAULT_PROFILE, MODE_BOTH, MODE_CORNER, MODE_FLOAT, MODE_LABELS, MODES, Config
from .hotkeys import HOTKEYS, HotkeyManager
from .main_window import MainWindow
from .overlay import CornerOverlay, FloatingOverlay, physical_to_logical
from .paths import data_dir, resource_path
from .selector import RegionSelector
from .settings_dialog import SettingsDialog
from .translator import Translator
from .updater import Updater
from .worker import LiveWorker

log = logging.getLogger("app")
IPC_NAME = "GlosaIPC"


def setup_logging():
    handler = RotatingFileHandler(data_dir() / "app.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    if sys.stderr:
        root.addHandler(logging.StreamHandler())


class Controller(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self.app = app
        self.cfg = Config.load()
        if winutil.migrate_autostart(LEGACY_APP_ID, APP_ID):
            self.cfg.autostart = True
        self.cfg.save()
        self.icon = QIcon(str(resource_path("assets", "icon.ico")))
        app.setWindowIcon(self.icon)
        self.translator = Translator(self.cfg.source_lang, self.cfg.target_lang)
        self.hidden = False
        self.paused = False
        self.ocr_language = ""
        self._ocr_error_shown = False
        self.workers: list[LiveWorker] = []
        self.floats: list[FloatingOverlay] = []
        self.zone_has_text: dict[int, bool] = {}
        self.corner = CornerOverlay()

        # Último juego (ventana externa) que estuvo en primer plano
        self.fg_exe, self.fg_title = "", ""
        self._pending_new_profile = None
        self._profile_before_edit = None

        self.selector = RegionSelector()
        self.selector.selected.connect(self.on_regions_selected)
        self.selector.canceled.connect(self.on_selector_canceled)

        self.updater = Updater()
        self.updater.update_available.connect(self.on_update_available)
        self.updater.up_to_date.connect(self._on_up_to_date)
        self.updater.check_failed.connect(self._on_check_failed)
        self._manual_check = False

        self.hotkeys = HotkeyManager()
        app.installNativeEventFilter(self.hotkeys)
        self.hotkeys.register_all()
        self.hotkeys.triggered.connect(self.on_hotkey)

        self.window = None
        self._reopen_window_after_edit = False
        self._build_tray()
        self.window = MainWindow(self)
        self.start_workers()
        self.apply_style()

        # Si se abre Glosa otra vez (acceso directo, menú Inicio...), la instancia ya abierta muestra su ventana
        self.ipc = QLocalServer(self)
        QLocalServer.removeServer(IPC_NAME)
        self.ipc.listen(IPC_NAME)
        self.ipc.newConnection.connect(self._on_ipc)

        self.fg_timer = QTimer(self)
        self.fg_timer.timeout.connect(self.watch_foreground)
        self.fg_timer.start(1500)

        if self.cfg.check_updates:
            QTimer.singleShot(4000, self.updater.check)
        if self.hotkeys.failed:
            self.notify("Algunos atajos no están disponibles", "Ya los usa otro programa: " + ", ".join(self.hotkeys.failed))
        if self.cfg.first_run or not any(p["regions"] for p in self.cfg.profiles):
            QTimer.singleShot(500, self.welcome)

    @property
    def profile(self) -> dict:
        return self.cfg.active()

    @property
    def regions(self) -> list:
        return self.profile["regions"]

    # ---------- bandeja ----------
    def _build_tray(self):
        self.tray = QSystemTrayIcon(self.icon)
        menu = QMenu()
        open_act = menu.addAction("Abrir Glosa", self.show_window)
        f = open_act.font()
        f.setBold(True)
        open_act.setFont(f)
        self.act_profile_title = menu.addAction("")
        self.act_profile_title.setEnabled(False)
        menu.addAction("Editar zonas del perfil…  (Ctrl+Shift+T)", lambda: self.selector_start(from_menu=True))
        self.profile_menu = menu.addMenu("Perfiles  (Ctrl+Shift+O cambia)")
        self.profile_menu.aboutToShow.connect(self._fill_profile_menu)
        menu.addSeparator()
        self.act_pause = menu.addAction("Pausar  (Ctrl+Shift+P)", self.toggle_pause)
        self.act_hide = menu.addAction("Ocultar traducción  (Ctrl+Shift+H)", self.toggle_hidden)
        mode_menu = menu.addMenu("Modo de visualización  (Ctrl+Shift+M)")
        self.mode_group = QActionGroup(menu)
        self.mode_actions = {}
        for m in MODES:
            a = QAction(MODE_LABELS[m], mode_menu, checkable=True)
            a.setChecked(m == self.cfg.display_mode)
            a.triggered.connect(lambda _=False, m=m: self.set_mode(m))
            self.mode_group.addAction(a)
            mode_menu.addAction(a)
            self.mode_actions[m] = a
        menu.addSeparator()
        menu.addAction("Ajustes…", self.open_settings)
        menu.addAction("Buscar actualizaciones", self.manual_update_check)
        menu.addAction("Abrir carpeta de datos", lambda: os.startfile(str(data_dir())))
        menu.addAction("Ayuda y código fuente", lambda: QDesktopServices.openUrl(QUrl(f"https://github.com/{GITHUB_REPO}")))
        menu.addSeparator()
        menu.addAction("Salir", self.quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()
        self.update_tooltip()

    def _fill_profile_menu(self):
        m = self.profile_menu
        m.clear()
        group = QActionGroup(m)
        for p in self.cfg.profiles:
            extra = [f"{len(p['regions'])} zona(s)"]
            if p.get("game"):
                extra.append(p["game"])
            a = QAction(f"{p['name']}   ({', '.join(extra)})", m, checkable=True)
            a.setChecked(p["name"] == self.cfg.active_profile)
            a.triggered.connect(lambda _=False, n=p["name"]: self.switch_profile(n))
            group.addAction(a)
            m.addAction(a)
        m.addSeparator()
        m.addAction("Nuevo perfil…", self.new_profile)
        m.addAction("Renombrar perfil actual…", self.rename_profile)
        game = self.profile.get("game")
        if game:
            m.addAction(f"Desvincular del programa ({game})", self.unlink_game)
        elif self.fg_exe:
            m.addAction(f"Vincular al programa {self.fg_exe}", self.link_game)
        a = m.addAction("Eliminar perfil actual…", self.delete_profile)
        a.setEnabled(len(self.cfg.profiles) > 1)
        m.addSeparator()
        auto = QAction("Cambiar de perfil automáticamente según el programa o juego", m, checkable=True)
        auto.setChecked(self.cfg.auto_profile)
        auto.toggled.connect(self.set_auto_profile)
        m.addAction(auto)

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
            self.show_window()

    def show_window(self):
        if self.window:
            self.window.show_and_raise()

    def _on_ipc(self):
        sock = self.ipc.nextPendingConnection()
        if sock:
            sock.waitForReadyRead(500)
            sock.readAll()
            sock.disconnectFromServer()
        self.show_window()

    def refresh_window(self):
        if self.window:
            self.window.refresh()

    # ---------- acciones usadas desde la ventana ----------
    def edit_profile_zones(self, name: str):
        """Abre el editor de zonas para un perfil concreto (lo activa si no lo está)."""
        if self.selector.is_active():
            return
        self._reopen_window_after_edit = bool(self.window and self.window.isVisible())
        if self.window:
            self.window.hide()
        if name != self.cfg.active_profile and self.cfg.get_profile(name):
            self.cfg.active_profile = name
            self.cfg.save()
            self.start_workers()
            self.apply_style()
        # pequeña espera para que la ventana desaparezca antes de mostrar el editor
        QTimer.singleShot(250, lambda: self.selector_start(from_menu=True))

    def _after_edit(self):
        if self._reopen_window_after_edit:
            self._reopen_window_after_edit = False
            self.show_window()

    def rename_profile_to(self, old: str, new: str):
        p = self.cfg.get_profile(old)
        if not p or not new.strip() or new.strip() == old:
            return
        p["name"] = self.cfg.unique_name(new.strip())
        if self.cfg.active_profile == old:
            self.cfg.active_profile = p["name"]
        self.cfg.save()
        self.update_tooltip()

    def set_profile_game(self, name: str, exe: str):
        p = self.cfg.get_profile(name)
        if not p:
            return
        exe = (exe or "").lower()
        if exe:
            other = self.cfg.profile_for_game(exe)
            if other and other is not p:
                other["game"] = ""  # un programa solo puede estar vinculado a un perfil
        p["game"] = exe
        self.cfg.save()
        self.update_tooltip()

    def remove_profile_zone(self, name: str, index: int):
        p = self.cfg.get_profile(name)
        if p and 0 <= index < len(p["regions"]):
            del p["regions"][index]
            self.cfg.save()
            if name == self.cfg.active_profile:
                self.start_workers()
                self.apply_style()
            self.update_tooltip()

    def delete_profile_named(self, name: str):
        p = self.cfg.get_profile(name)
        if not p or len(self.cfg.profiles) <= 1:
            return
        self.cfg.profiles.remove(p)
        if name == self.cfg.active_profile:
            self.switch_profile(self.cfg.profiles[0]["name"])
        else:
            self.cfg.save()
            self.update_tooltip()

    def set_opacity(self, background: int, text: int):
        self.cfg.opacity, self.cfg.text_opacity = background, text
        self.cfg.save()
        self.apply_style()

    def set_autostart(self, on: bool):
        self.cfg.autostart = on
        self.cfg.save()
        winutil.set_autostart(on, APP_ID)

    def set_check_updates(self, on: bool):
        self.cfg.check_updates = on
        self.cfg.save()

    def update_tooltip(self):
        n = len(self.regions)
        state = "en pausa" if self.paused else f"leyendo {n} zona(s)"
        if not n:
            state = "sin zonas: pulsa Ctrl+Shift+T"
        self.tray.setToolTip(f"{APP_NAME} {__version__} · {APP_TAGLINE}\nPerfil: {self.profile['name']} · {state}")
        self.act_profile_title.setText(f"Perfil: {self.profile['name']}  ·  {n} zona(s)")
        self.refresh_window()

    def notify(self, title: str, msg: str):
        self.tray.showMessage(title, msg, self.icon, 4000)

    def welcome(self):
        keys = "\n".join(f"  {v[2]}: {v[3]}" for v in HOTKEYS.values())
        extra = ""
        if not self.ocr_language.lower().startswith("en") and self.ocr_language:
            extra = (
                "\n\nConsejo: tu Windows no tiene el OCR en inglés instalado (se usa "
                f"{self.ocr_language}). Funciona, pero lee mejor el inglés si lo instalas desde Ajustes."
            )
        box = QMessageBox(
            QMessageBox.NoIcon,
            APP_NAME,
            f"Bienvenido a {APP_NAME}, {APP_TAGLINE.lower()}.\n\n"
            "Se queda en la bandeja del sistema (junto al reloj) y lee en vivo las zonas que marques. "
            "Sirve para el día a día, para estudiar, para juegos, vídeos o cualquier programa en otro idioma. "
            "Puedes marcar varias zonas (por ejemplo, diálogos arriba y abajo) y se guardan en un perfil por programa.\n\n"
            f"Atajos:\n{keys}{extra}\n\nAbre el programa o juego y pulsa Ctrl+Shift+T desde él: el perfil queda asociado "
            "a ese programa y se activa solo la próxima vez que lo abras.",
        )
        box.setIconPixmap(QPixmap(str(resource_path("assets", "logo.png"))).scaledToWidth(96, Qt.SmoothTransformation))
        box.exec()
        self.cfg.first_run = False
        self.cfg.save()
        self.show_window()
        if self.window:
            self.window.nav.setCurrentRow(1)  # Perfiles: lo primero es marcar las zonas

    # ---------- lectura en vivo ----------
    def start_workers(self):
        for w in self.workers:
            w.stop()
        self.workers = []
        for f in self.floats:
            f.hide()
            f.deleteLater()
        self.floats = []
        self.zone_has_text = {}
        self.corner.clear_all()
        for i, region in enumerate(self.regions):
            w = LiveWorker(self.cfg, self.translator, region, i)
            w.translated.connect(self.on_translated)
            w.cleared.connect(self.on_cleared)
            w.ocr_ready.connect(self.on_ocr_ready)
            w.failed.connect(self.on_ocr_failed)
            w.set_paused(self.paused)
            w.start()
            self.workers.append(w)
            self.floats.append(FloatingOverlay())
        self.refresh_overlays()
        self.update_tooltip()

    def on_ocr_ready(self, lang):
        self.ocr_language = lang

    def on_ocr_failed(self, msg):
        if not self._ocr_error_shown:
            self._ocr_error_shown = True
            QMessageBox.critical(None, APP_NAME, f"No se pudo iniciar el OCR de Windows:\n{msg}")

    def on_translated(self, index, original, translation, source, ok):
        if index >= len(self.floats):
            return  # resultado de un perfil anterior
        log.info("[zona %d · %s] %r -> %r", index + 1, source, original, translation)
        if self.window:
            self.window.add_history(index, original, translation, source)
        self.zone_has_text[index] = True
        self.floats[index].set_text(translation, offline=not ok)
        self.corner.set_entry(index, original, translation, source, offline=not ok)
        self.refresh_overlays()

    def on_cleared(self, index):
        if self.cfg.hide_when_empty and index < len(self.floats):
            self.zone_has_text[index] = False
            self.corner.clear_entry(index)
            self.refresh_overlays()

    def refresh_overlays(self):
        visible = not self.hidden and not self.paused and not self.selector.is_active()
        mode = self.cfg.display_mode
        want_float = visible and mode in (MODE_FLOAT, MODE_BOTH)
        for i, f in enumerate(self.floats):
            if want_float and self.zone_has_text.get(i):
                f.show()
                f.raise_()
            else:
                f.hide()
        if visible and mode in (MODE_CORNER, MODE_BOTH) and self.corner.has_entries():
            self.corner.show()
            self.corner.raise_()
        else:
            self.corner.hide()

    def apply_style(self):
        rects = [physical_to_logical(r) for r in self.regions]
        for w in [self.corner, *self.floats]:
            w.apply_style(self.cfg.font_size, self.cfg.opacity, self.cfg.text_opacity)
        for f, rect in zip(self.floats, rects):
            f.set_region(rect, self.cfg.float_position)
            f.update()
        self.corner.configure(self.cfg.corner, self.cfg.show_original, rects[0] if rects else None, len(rects))
        self.corner.update()
        self.refresh_overlays()

    # ---------- perfiles ----------
    def watch_foreground(self):
        exe, title = winutil.foreground_app()
        if not exe:
            return
        self.fg_exe, self.fg_title = exe, title
        if self.cfg.auto_profile and not self.selector.is_active():
            p = self.cfg.profile_for_game(exe)
            if p and p["name"] != self.cfg.active_profile:
                self.switch_profile(p["name"], reason="programa detectado")

    def switch_profile(self, name: str, reason: str = ""):
        if not self.cfg.get_profile(name):
            return
        self.cfg.active_profile = name
        self.cfg.save()
        self.start_workers()
        self.apply_style()
        msg = f"{len(self.regions)} zona(s)" + (f" · {reason}" if reason else "")
        self.notify(f"Perfil: {name}", msg)
        log.info("Perfil activo: %s (%s)", name, msg)

    def cycle_profile(self):
        names = [p["name"] for p in self.cfg.profiles]
        if len(names) > 1:
            i = names.index(self.cfg.active_profile) if self.cfg.active_profile in names else 0
            self.switch_profile(names[(i + 1) % len(names)])

    def _game_display_name(self) -> str:
        title = (self.fg_title or "").strip()
        if not title or len(title) > 40:
            title = self.fg_exe.rsplit(".", 1)[0]
        return title or "Perfil"

    def new_profile(self):
        suggestion = self._game_display_name() if self.fg_exe else ""
        name, ok = QInputDialog.getText(None, APP_NAME, "Nombre del nuevo perfil:", text=suggestion)
        if not ok or not name.strip():
            return
        p = self.cfg.add_profile(name.strip())
        self.switch_profile(p["name"])
        self.selector_start(from_menu=True)

    def rename_profile(self):
        p = self.profile
        name, ok = QInputDialog.getText(None, APP_NAME, "Nuevo nombre del perfil:", text=p["name"])
        if ok and name.strip() and name.strip() != p["name"]:
            p["name"] = self.cfg.unique_name(name.strip())
            self.cfg.active_profile = p["name"]
            self.cfg.save()
            self.update_tooltip()

    def delete_profile(self):
        if len(self.cfg.profiles) <= 1:
            return
        p = self.profile
        if QMessageBox.question(None, APP_NAME, f"¿Eliminar el perfil «{p['name']}» y sus zonas?") != QMessageBox.Yes:
            return
        self.cfg.profiles.remove(p)
        self.switch_profile(self.cfg.profiles[0]["name"])

    def link_game(self):
        if not self.fg_exe:
            return
        other = self.cfg.profile_for_game(self.fg_exe)
        if other:
            other["game"] = ""
        self.profile["game"] = self.fg_exe
        self.cfg.save()
        self.notify(f"Perfil: {self.profile['name']}", f"Vinculado a {self.fg_exe}")

    def unlink_game(self):
        self.profile["game"] = ""
        self.cfg.save()

    def set_auto_profile(self, on: bool):
        self.cfg.auto_profile = on
        self.cfg.save()

    # ---------- acciones ----------
    def selector_start(self, from_menu: bool = False):
        """Edita las zonas. Lanzado desde un juego (atajo), usa o crea el perfil de ese juego."""
        if self.selector.is_active():
            return
        exe, title = winutil.foreground_app()
        if exe:
            self.fg_exe, self.fg_title = exe, title
        self._pending_new_profile = None
        self._profile_before_edit = self.cfg.active_profile
        if self.fg_exe and self.cfg.auto_profile and not from_menu:
            target = self.cfg.profile_for_game(self.fg_exe)
            current = self.profile
            if target is None and current.get("game") and current["game"] != self.fg_exe:
                target = self.cfg.add_profile(self._game_display_name(), self.fg_exe)
                self._pending_new_profile = target["name"]
            if target is not None and target["name"] != self.cfg.active_profile:
                self.cfg.active_profile = target["name"]
                self.start_workers()
                self.apply_style()
        self.selector.start(self.regions, self.profile["name"])
        self.refresh_overlays()

    def on_regions_selected(self, regions):
        p = self.profile
        p["regions"] = regions
        if not p.get("game") and self.fg_exe and self.cfg.auto_profile and not self.cfg.profile_for_game(self.fg_exe):
            p["game"] = self.fg_exe
            if p["name"] == DEFAULT_PROFILE:
                p["name"] = self.cfg.unique_name(self._game_display_name())
                self.cfg.active_profile = p["name"]
        self._pending_new_profile = None
        self.cfg.save()
        self.start_workers()
        self.apply_style()
        game = f" · {p['game']}" if p.get("game") else ""
        self.notify(f"Perfil: {p['name']}", f"{len(regions)} zona(s) guardadas{game}")
        log.info("Perfil %s: zonas %s, juego %s", p["name"], regions, p.get("game"))
        self._after_edit()

    def on_selector_canceled(self):
        if self._pending_new_profile:
            p = self.cfg.get_profile(self._pending_new_profile)
            if p and not p["regions"]:
                self.cfg.profiles.remove(p)
            self._pending_new_profile = None
            if self.cfg.get_profile(self._profile_before_edit or ""):
                self.cfg.active_profile = self._profile_before_edit
            self.start_workers()
            self.apply_style()
        self.refresh_overlays()
        self._after_edit()

    def toggle_pause(self):
        self.paused = not self.paused
        for w in self.workers:
            w.set_paused(self.paused)
        self.act_pause.setText(("Reanudar" if self.paused else "Pausar") + "  (Ctrl+Shift+P)")
        self.notify(APP_NAME, "En pausa" if self.paused else "Leyendo en vivo")
        self.refresh_overlays()
        self.update_tooltip()

    def toggle_hidden(self):
        self.hidden = not self.hidden
        self.act_hide.setText(("Mostrar" if self.hidden else "Ocultar") + " traducción  (Ctrl+Shift+H)")
        self.refresh_overlays()
        self.refresh_window()

    def set_mode(self, mode):
        self.cfg.display_mode = mode
        self.cfg.save()
        self.mode_actions[mode].setChecked(True)
        self.refresh_overlays()
        self.refresh_window()

    def cycle_mode(self):
        nxt = MODES[(MODES.index(self.cfg.display_mode) + 1) % len(MODES)]
        self.set_mode(nxt)
        self.notify("Modo de visualización", MODE_LABELS[nxt])

    def on_hotkey(self, hid):
        actions = {
            1: self.selector_start,
            2: self.toggle_pause,
            3: self.cycle_mode,
            4: self.toggle_hidden,
            5: self.cycle_profile,
        }
        actions[hid]()

    def preview_style(self, font_size: int, opacity: int, text_opacity: int):
        """Aplica el estilo en vivo mientras se mueven los controles de Ajustes (con texto de ejemplo si hace falta)."""
        sample = "Así se verá la traducción mientras juegas."
        for i, f in enumerate(self.floats):
            if not self.zone_has_text.get(i):
                f.set_text(sample)
                self.zone_has_text[i] = True
                self._preview_samples.add(i)
        if not self.corner.has_entries():
            self.corner.set_entry(0, "This is how the translation will look.", sample, "vista previa")
            self._preview_samples.add(-1)
        for w in [self.corner, *self.floats]:
            w.apply_style(font_size, opacity, text_opacity)
            w._relayout()
        self.refresh_overlays()

    def _end_preview(self):
        for i in self._preview_samples:
            if i == -1:
                self.corner.clear_entry(0)
            else:
                self.zone_has_text[i] = False
        self._preview_samples = set()
        self.apply_style()

    def open_settings(self):
        self._preview_samples = set()
        dlg = SettingsDialog(
            self.cfg, self.ocr_language, self.translator.memory_size(), self.install_english_ocr, self.translator.clear_memory,
            on_preview=self.preview_style,
        )
        dlg.setWindowIcon(self.icon)
        accepted = dlg.exec()
        self._end_preview()
        if accepted:
            old_target = self.cfg.target_lang
            dlg.apply_to(self.cfg)
            self.cfg.save()
            winutil.set_autostart(self.cfg.autostart, APP_ID)
            if self.cfg.target_lang != old_target:
                self.translator.set_languages(self.cfg.source_lang, self.cfg.target_lang)
            self.mode_actions[self.cfg.display_mode].setChecked(True)
            self.apply_style()
            for w in self.workers:
                w.force_refresh()

    def install_english_ocr(self):
        cmd = (
            "-NoProfile -ExecutionPolicy Bypass -Command "
            f"\"Write-Host 'Instalando OCR en inglés...'; Add-WindowsCapability -Online -Name '{ocr.ENGLISH_OCR_CAPABILITY}'\""
        )
        if winutil.run_elevated("powershell.exe", cmd):
            self.notify("Instalando OCR en inglés", "Cuando termine, la app empezará a usarlo sola.")
            self._ocr_poll_left = 120
            self._ocr_timer = QTimer(self)
            self._ocr_timer.timeout.connect(self._poll_english_ocr)
            self._ocr_timer.start(5000)

    def _poll_english_ocr(self):
        self._ocr_poll_left -= 1
        if ocr.has_language("en"):
            self._ocr_timer.stop()
            self.start_workers()
            self.apply_style()
            self.notify("OCR en inglés listo", "Ahora la lectura en inglés será más precisa.")
        elif self._ocr_poll_left <= 0:
            self._ocr_timer.stop()

    # ---------- actualizaciones ----------
    def manual_update_check(self):
        self._manual_check = True
        self.updater.check()

    def _on_up_to_date(self):
        if self._manual_check:
            self.notify("Ya tienes la última versión", f"Versión {__version__}")

    def _on_check_failed(self, msg):
        if self._manual_check:
            self.notify("No se pudo comprobar", msg)

    def on_update_available(self, version, notes, url):
        notes = notes.strip()[:1200]
        box = QMessageBox(QMessageBox.Question, APP_NAME, f"Hay una nueva versión: {version} (tienes {__version__}).")
        box.setInformativeText("¿Descargarla e instalarla ahora? La app se cerrará y se volverá a abrir sola.")
        if notes:
            box.setDetailedText(notes)
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.button(QMessageBox.Yes).setText("Actualizar")
        box.button(QMessageBox.No).setText("Más tarde")
        box.setWindowIcon(self.icon)
        if box.exec() != QMessageBox.Yes:
            return
        self.progress = QProgressDialog("Descargando actualización…", None, 0, 100)
        self.progress.setWindowTitle(APP_NAME)
        self.progress.setWindowIcon(self.icon)
        self.progress.show()
        self.updater.progress.connect(self.progress.setValue)
        self.updater.downloaded.connect(self.on_update_downloaded)
        self.updater.download_failed.connect(self._on_download_failed)
        self.updater.download(url)

    def _on_download_failed(self, msg):
        self.progress.close()
        QMessageBox.warning(None, APP_NAME, f"Falló la descarga:\n{msg}")

    def on_update_downloaded(self, path):
        self.progress.close()
        Updater.launch_installer(path)
        self.quit()

    def quit(self):
        self.hotkeys.unregister_all()
        for w in self.workers:
            w.stop()
        self.translator.close()
        self.tray.hide()
        self.app.quit()


def _ask_running_instance_to_show() -> None:
    winutil.allow_any_foreground()
    sock = QLocalSocket()
    sock.connectToServer(IPC_NAME)
    if sock.waitForConnected(1500):
        sock.write(b"show")
        sock.flush()
        sock.waitForBytesWritten(500)
        sock.disconnectFromServer()


def main():
    setup_logging()
    minimized = "--minimized" in sys.argv
    if not winutil.acquire_single_instance(f"{APP_ID}Mutex"):
        # Ya está abierta en segundo plano: le pedimos que muestre su ventana
        if not minimized:
            QApplication(sys.argv)
            _ask_running_instance_to_show()
        return 0
    winutil.set_app_id("SoupOfMacaco.Glosa")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, APP_NAME, "No se encontró la bandeja del sistema.")
        return 1
    log.info("Iniciando %s %s (Windows build %s)", APP_NAME, __version__, winutil.windows_build())
    controller = Controller(app)
    if not minimized and not controller.cfg.first_run:
        QTimer.singleShot(0, controller.show_window)
    return app.exec()
