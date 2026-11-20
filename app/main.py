"""Punto de entrada: icono en la bandeja del sistema que coordina todo."""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QProgressDialog, QSystemTrayIcon

from . import APP_ID, APP_NAME, APP_TAGLINE, GITHUB_REPO, LEGACY_APP_ID, __version__, ocr, winutil
from .config import MODE_BOTH, MODE_CORNER, MODE_FLOAT, MODE_LABELS, MODES, Config
from .hotkeys import HOTKEYS, HotkeyManager
from .overlay import CornerOverlay, FloatingOverlay, physical_to_logical
from .paths import data_dir, resource_path
from .selector import RegionSelector
from .settings_dialog import SettingsDialog
from .translator import Translator
from .updater import Updater
from .worker import LiveWorker

log = logging.getLogger("app")


def setup_logging():
    handler = RotatingFileHandler(data_dir() / "app.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)
    if sys.stderr:
        root.addHandler(logging.StreamHandler())


class Controller:
    def __init__(self, app: QApplication):
        self.app = app
        self.cfg = Config.load()
        if winutil.migrate_autostart(LEGACY_APP_ID, APP_ID):
            self.cfg.autostart = True
            self.cfg.save()
        self.icon = QIcon(str(resource_path("assets", "icon.ico")))
        app.setWindowIcon(self.icon)
        self.translator = Translator(self.cfg.source_lang, self.cfg.target_lang)
        self.hidden = False
        self.ocr_language = ""
        self.has_text = False
        self.worker = None

        self.floating = FloatingOverlay()
        self.corner = CornerOverlay()
        self.selector = RegionSelector()
        self.selector.selected.connect(self.on_region_selected)
        self.selector.canceled.connect(self.refresh_overlays)

        self.updater = Updater()
        self.updater.update_available.connect(self.on_update_available)
        self.updater.up_to_date.connect(lambda: self._manual_check and self.notify("Ya tienes la última versión", f"Versión {__version__}"))
        self.updater.check_failed.connect(lambda m: self._manual_check and self.notify("No se pudo comprobar", m))
        self._manual_check = False

        self.hotkeys = HotkeyManager()
        app.installNativeEventFilter(self.hotkeys)
        self.hotkeys.register_all()
        self.hotkeys.triggered.connect(self.on_hotkey)

        self._build_tray()
        self.apply_style()
        self.start_worker()

        if self.cfg.check_updates:
            QTimer.singleShot(4000, self.updater.check)
        if self.hotkeys.failed:
            self.notify("Algunos atajos no están disponibles", "Ya los usa otro programa: " + ", ".join(self.hotkeys.failed))
        if self.cfg.first_run or not self.cfg.region:
            QTimer.singleShot(500, self.welcome)

    # ---------- bandeja ----------
    def _build_tray(self):
        self.tray = QSystemTrayIcon(self.icon)
        menu = QMenu()
        self.act_select = menu.addAction("Seleccionar zona…  (Ctrl+Shift+T)", self.selector_start)
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

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.selector_start()

    def update_tooltip(self):
        state = "en pausa" if self.worker and self.worker.is_paused() else "leyendo"
        if not self.cfg.region:
            state = "sin zona seleccionada"
        self.tray.setToolTip(f"{APP_NAME} {__version__} · {APP_TAGLINE}\n{state}")

    def notify(self, title: str, msg: str):
        self.tray.showMessage(title, msg, self.icon, 5000)

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
            "Se queda en la bandeja del sistema (junto al reloj) y lee en vivo la zona que marques.\n\n"
            f"Atajos:\n{keys}{extra}\n\nAhora marca la zona donde aparece el texto del juego.",
        )
        box.setIconPixmap(QPixmap(str(resource_path("assets", "logo.png"))).scaledToWidth(96, Qt.SmoothTransformation))
        box.exec()
        self.cfg.first_run = False
        self.cfg.save()
        self.selector_start()

    # ---------- lectura en vivo ----------
    def start_worker(self):
        if self.worker:
            self.worker.stop()
        self.worker = LiveWorker(self.cfg, self.translator)
        self.worker.translated.connect(self.on_translated)
        self.worker.cleared.connect(self.on_cleared)
        self.worker.ocr_ready.connect(self.on_ocr_ready)
        self.worker.failed.connect(lambda m: QMessageBox.critical(None, APP_NAME, f"No se pudo iniciar el OCR de Windows:\n{m}"))
        self.worker.start()

    def on_ocr_ready(self, lang):
        self.ocr_language = lang

    def on_translated(self, original, translation, source, ok):
        log.info("[%s] %r -> %r", source, original, translation)
        self.has_text = True
        self.floating.set_text(translation, offline=not ok)
        self.corner.set_text(original, translation, source, offline=not ok)
        self.refresh_overlays()

    def on_cleared(self):
        if self.cfg.hide_when_empty:
            self.has_text = False
            self.refresh_overlays()

    def refresh_overlays(self):
        paused = self.worker is not None and self.worker.is_paused()
        visible = self.has_text and not self.hidden and not paused and bool(self.cfg.region)
        mode = self.cfg.display_mode
        for widget, wanted in ((self.floating, mode in (MODE_FLOAT, MODE_BOTH)), (self.corner, mode in (MODE_CORNER, MODE_BOTH))):
            if visible and wanted:
                widget.show()
                widget.raise_()
            else:
                widget.hide()

    def apply_style(self):
        rect = physical_to_logical(self.cfg.region) if self.cfg.region else None
        for w in (self.floating, self.corner):
            w.apply_style(self.cfg.font_size, self.cfg.opacity)
        if rect is not None:
            self.floating.set_region(rect, self.cfg.float_position)
        self.corner.configure(self.cfg.corner, self.cfg.show_original, rect)
        self.floating.update()
        self.corner.update()
        self.refresh_overlays()

    # ---------- acciones ----------
    def selector_start(self):
        self.floating.hide()
        self.corner.hide()
        self.selector.start()

    def on_region_selected(self, region):
        self.cfg.region = region
        self.cfg.save()
        self.has_text = False
        self.worker.set_region(region)
        self.apply_style()
        self.update_tooltip()
        log.info("Zona seleccionada: %s", region)

    def toggle_pause(self):
        paused = not self.worker.is_paused()
        self.worker.set_paused(paused)
        self.act_pause.setText(("Reanudar" if paused else "Pausar") + "  (Ctrl+Shift+P)")
        self.notify(APP_NAME, "En pausa" if paused else "Leyendo en vivo")
        self.refresh_overlays()
        self.update_tooltip()

    def toggle_hidden(self):
        self.hidden = not self.hidden
        self.act_hide.setText(("Mostrar" if self.hidden else "Ocultar") + " traducción  (Ctrl+Shift+H)")
        self.refresh_overlays()

    def set_mode(self, mode):
        self.cfg.display_mode = mode
        self.cfg.save()
        self.mode_actions[mode].setChecked(True)
        self.refresh_overlays()

    def cycle_mode(self):
        nxt = MODES[(MODES.index(self.cfg.display_mode) + 1) % len(MODES)]
        self.set_mode(nxt)
        self.notify("Modo de visualización", MODE_LABELS[nxt])

    def on_hotkey(self, hid):
        {1: self.selector_start, 2: self.toggle_pause, 3: self.cycle_mode, 4: self.toggle_hidden}[hid]()

    def open_settings(self):
        dlg = SettingsDialog(
            self.cfg, self.ocr_language, self.translator.memory_size(), self.install_english_ocr, self.translator.clear_memory
        )
        dlg.setWindowIcon(self.icon)
        if dlg.exec():
            old_target = self.cfg.target_lang
            dlg.apply_to(self.cfg)
            self.cfg.save()
            winutil.set_autostart(self.cfg.autostart, APP_ID)
            if self.cfg.target_lang != old_target:
                self.translator.set_languages(self.cfg.source_lang, self.cfg.target_lang)
            self.mode_actions[self.cfg.display_mode].setChecked(True)
            self.apply_style()
            self.worker.force_refresh()

    def install_english_ocr(self):
        cmd = (
            "-NoProfile -ExecutionPolicy Bypass -Command "
            f"\"Write-Host 'Instalando OCR en inglés...'; Add-WindowsCapability -Online -Name '{ocr.ENGLISH_OCR_CAPABILITY}'\""
        )
        if winutil.run_elevated("powershell.exe", cmd):
            self.notify("Instalando OCR en inglés", "Cuando termine, la app empezará a usarlo sola.")
            self._ocr_poll_left = 120
            self._ocr_timer = QTimer()
            self._ocr_timer.timeout.connect(self._poll_english_ocr)
            self._ocr_timer.start(5000)

    def _poll_english_ocr(self):
        self._ocr_poll_left -= 1
        if ocr.has_language("en"):
            self._ocr_timer.stop()
            self.start_worker()
            self.notify("OCR en inglés listo", "Ahora la lectura en inglés será más precisa.")
        elif self._ocr_poll_left <= 0:
            self._ocr_timer.stop()

    # ---------- actualizaciones ----------
    def manual_update_check(self):
        self._manual_check = True
        self.updater.check()

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
        self.updater.download_failed.connect(lambda m: (self.progress.close(), QMessageBox.warning(None, APP_NAME, f"Falló la descarga:\n{m}")))
        self.updater.download(url)

    def on_update_downloaded(self, path):
        self.progress.close()
        Updater.launch_installer(path)
        self.quit()

    def quit(self):
        self.hotkeys.unregister_all()
        if self.worker:
            self.worker.stop()
        self.translator.close()
        self.tray.hide()
        self.app.quit()


def main():
    setup_logging()
    if not winutil.acquire_single_instance(f"{APP_ID}Mutex"):
        return 0
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, APP_NAME, "No se encontró la bandeja del sistema.")
        return 1
    log.info("Iniciando %s %s (Windows build %s)", APP_NAME, __version__, winutil.windows_build())
    controller = Controller(app)  # noqa: F841 (mantener referencia viva)
    return app.exec()
