"""Actualizaciones automáticas a partir de las Releases de GitHub."""
import logging
import os
import re
import subprocess
import tempfile
import threading

import requests
from PySide6.QtCore import QObject, Signal

from . import GITHUB_REPO, __version__

log = logging.getLogger(__name__)

API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"


def parse_version(v: str) -> tuple:
    nums = re.findall(r"\d+", v)
    return tuple(int(n) for n in nums[:3]) + (0,) * (3 - len(nums[:3]))


class Updater(QObject):
    update_available = Signal(str, str, str)   # versión, notas, url del instalador
    up_to_date = Signal()
    check_failed = Signal(str)
    progress = Signal(int)                     # 0-100
    downloaded = Signal(str)                   # ruta del instalador
    download_failed = Signal(str)

    def check(self):
        threading.Thread(target=self._check, daemon=True, name="updater").start()

    def _check(self):
        try:
            r = requests.get(API, timeout=8, headers={"Accept": "application/vnd.github+json"})
            if r.status_code == 404:
                self.up_to_date.emit()
                return
            r.raise_for_status()
            data = r.json()
            latest = data.get("tag_name", "")
            if parse_version(latest) <= parse_version(__version__):
                self.up_to_date.emit()
                return
            asset = next(
                (a for a in data.get("assets", []) if a["name"].lower().endswith(".exe") and "setup" in a["name"].lower()),
                None,
            )
            if not asset:
                self.check_failed.emit(f"La versión {latest} no tiene instalador adjunto")
                return
            self.update_available.emit(latest.lstrip("v"), data.get("body") or "", asset["browser_download_url"])
        except Exception as e:
            log.warning("No se pudo comprobar si hay actualizaciones: %s", e)
            self.check_failed.emit(str(e))

    def download(self, url: str):
        threading.Thread(target=self._download, args=(url,), daemon=True, name="updater-dl").start()

    def _download(self, url: str):
        try:
            dest = os.path.join(tempfile.gettempdir(), url.rsplit("/", 1)[-1])
            with requests.get(url, stream=True, timeout=15) as r:
                r.raise_for_status()
                total = int(r.headers.get("Content-Length", 0))
                done = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(256 * 1024):
                        f.write(chunk)
                        done += len(chunk)
                        if total:
                            self.progress.emit(int(done * 100 / total))
            self.downloaded.emit(dest)
        except Exception as e:
            log.exception("Fallo al descargar la actualización")
            self.download_failed.emit(str(e))

    @staticmethod
    def launch_installer(path: str):
        # /SILENT muestra solo la barra de progreso. El instalador espera a que la app se cierre
        # (o la cierra él) y la vuelve a abrir al terminar. Se lanza desacoplado para que sobreviva al cierre.
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(
            [path, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS"],
            close_fds=True,
            creationflags=flags,
        )
