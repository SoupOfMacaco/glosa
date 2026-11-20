"""Bucle en vivo: captura la zona continuamente, detecta cambios, lee el texto y lo traduce."""
import difflib
import logging
import threading
import time

import mss
from PIL import Image, ImageChops
from PySide6.QtCore import QThread, Signal

from . import textfix
from .ocr import WindowsOcr
from .translator import Translator

log = logging.getLogger(__name__)

PIXEL_DELTA = 28            # diferencia de gris (0-255) para considerar que un píxel cambió
MIN_CHANGED_PIXELS = 3      # basta con que aparezca una letra nueva
FORCE_OCR_AFTER = 4.0       # si la zona no para de cambiar (fondo animado), leer igualmente
FORCE_OCR_EVERY = 1.5
RETRY_OFFLINE_EVERY = 5.0
SIMILARITY_SKIP = 0.93      # textos casi iguales no se vuelven a traducir


class LiveWorker(QThread):
    translated = Signal(int, str, str, str, bool)   # zona, original, traducción, fuente, ok
    cleared = Signal(int)                           # zona
    ocr_ready = Signal(str)                         # idioma del OCR en uso
    failed = Signal(str)

    def __init__(self, config, translator: Translator, region, index: int = 0, glossary=None):
        super().__init__()
        self.config = config
        self.translator = translator
        self.index = index
        self._glossary = glossary or (lambda: {})  # función que devuelve el glosario del perfil
        self._stop = threading.Event()
        self._paused = False
        self._region = list(region) if region else None
        self._reset = True
        self._seq = 0
        self._ocr_lang_pref = config.source_lang

    # ---------- control desde el hilo de la interfaz ----------
    def set_region(self, region):
        self._region = list(region) if region else None
        self._reset = True

    def set_paused(self, paused: bool):
        self._paused = paused
        self._reset = True

    def is_paused(self) -> bool:
        return self._paused

    def force_refresh(self):
        self._reset = True

    def stop(self):
        self._stop.set()
        self.wait(3000)

    # ---------- bucle principal ----------
    def run(self):
        try:
            ocr = WindowsOcr(self._ocr_lang_pref)
        except Exception as e:
            log.exception("No se pudo iniciar el OCR")
            self.failed.emit(str(e))
            return
        self.ocr_ready.emit(ocr.language)
        log.info("OCR iniciado con idioma %s", ocr.language)

        prev_thumb = None
        last_change = 0.0
        changing_since = None
        pending = False           # hay un cambio sin leer todavía
        last_forced = 0.0
        last_text = ""
        empty_count = 0
        failed_text = None
        retry_at = 0.0

        with (mss.MSS() if hasattr(mss, "MSS") else mss.mss()) as sct:
            while not self._stop.is_set():
                t0 = time.monotonic()
                cfg = self.config
                region = self._region
                if self._paused or not region:
                    time.sleep(0.2)
                    continue
                if self._reset:
                    self._reset = False
                    prev_thumb, pending, last_text, failed_text = None, True, "", None
                    last_change = time.monotonic()
                    changing_since = None

                try:
                    x, y, w, h = region
                    shot = sct.grab({"left": x, "top": y, "width": w, "height": h})
                    img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
                except Exception as e:
                    log.warning("Fallo al capturar la zona: %s", e)
                    time.sleep(1)
                    continue

                now = time.monotonic()
                thumb = img.convert("L").reduce(2) if w > 400 else img.convert("L")
                if prev_thumb is not None and prev_thumb.size == thumb.size:
                    mask = ImageChops.difference(thumb, prev_thumb).point(lambda p: 255 if p > PIXEL_DELTA else 0)
                    changed_pixels = mask.histogram()[255]
                    if changed_pixels >= MIN_CHANGED_PIXELS:
                        pending = True
                        last_change = now
                        if changing_since is None:
                            changing_since = now
                    else:
                        changing_since = None
                prev_thumb = thumb

                do_ocr = False
                if pending:
                    settled = (now - last_change) * 1000 >= (cfg.settle_ms if cfg.wait_typing else 0)
                    endless = changing_since is not None and now - changing_since > FORCE_OCR_AFTER
                    if settled:
                        do_ocr = True
                    elif endless and now - last_forced > FORCE_OCR_EVERY:
                        do_ocr = True
                        last_forced = now
                if failed_text and now >= retry_at:
                    do_ocr = True

                if do_ocr:
                    pending = False
                    try:
                        lines = ocr.recognize(img)
                    except Exception as e:
                        log.warning("Fallo del OCR: %s", e)
                        lines = []
                    text = textfix.lines_to_paragraphs(lines)
                    if cfg.spellfix and text:
                        text = textfix.spellfix(text)

                    if not text or not textfix.looks_like_text(text):
                        empty_count += 1
                        if empty_count >= 2 and last_text:
                            last_text, failed_text = "", None
                            self.cleared.emit(self.index)
                        elif empty_count >= 2:
                            self.cleared.emit(self.index)
                    else:
                        empty_count = 0
                        retrying = failed_text is not None and text == failed_text
                        similar = difflib.SequenceMatcher(None, text, last_text).ratio() >= SIMILARITY_SKIP
                        if retrying or not similar:
                            last_text = text
                            failed_text = None
                            self._submit(text)
                        elif failed_text:
                            retry_at = now + RETRY_OFFLINE_EVERY

                # recoger fallos que hayan llegado mientras tanto
                if self._last_failed is not None:
                    failed_text, self._last_failed = self._last_failed, None
                    retry_at = time.monotonic() + RETRY_OFFLINE_EVERY

                elapsed = time.monotonic() - t0
                time.sleep(max(0.03, cfg.interval_ms / 1000 - elapsed))

    _last_failed = None

    def _submit(self, text: str):
        self._seq += 1
        seq = self._seq
        future = self.translator.translate_async(text, self._glossary())

        def done(f):
            if seq != self._seq:
                return  # ya hay un texto más nuevo en pantalla
            try:
                res = f.result()
            except Exception as e:
                log.warning("Error de traducción: %s", e)
                return
            if not res.ok:
                self._last_failed = text
            if res.same_language:
                self.cleared.emit(self.index)  # ya está en el idioma de destino: no hace falta traducir
                return
            self.translated.emit(self.index, res.original, res.text, res.source, res.ok)

        future.add_done_callback(done)
