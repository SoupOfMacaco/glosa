"""Traducción híbrida: memoria local (SQLite) + glosario incluido + servicios gratuitos en internet.

Orden de búsqueda:
  1. Memoria local: todo lo que ya se tradujo antes (crece sola mientras usas la app).
  2. Glosario incluido con frases comunes de juegos.
  3. Internet: Google Translate (endpoint público gratuito) y, si falla, MyMemory.
Cada traducción obtenida de internet se guarda en la memoria local.
"""
import json
import logging
import re
import sqlite3
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor

import requests

from .paths import data_dir, resource_path

log = logging.getLogger(__name__)

SOURCE_MEMORY = "memoria"
SOURCE_GLOSSARY = "glosario"
SOURCE_OFFLINE = "sin conexión"
SOURCE_SAME = "mismo idioma"


def normalize(text: str) -> str:
    return re.sub(r"[ \t]+", " ", text.strip()).lower()


class TranslationResult:
    def __init__(self, original: str, text: str, source: str, ok: bool = True):
        self.original = original
        self.text = text
        self.source = source
        self.ok = ok
        self.same_language = source == SOURCE_SAME


class Translator:
    def __init__(self, source_lang: str = "en", target_lang: str = "es"):
        self.source_lang = source_lang
        self.target_lang = target_lang
        self._lock = threading.Lock()
        self._db = sqlite3.connect(str(data_dir() / "memoria.db"), check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS traducciones ("
            " src_lang TEXT, dst_lang TEXT, clave TEXT, original TEXT, traduccion TEXT,"
            " fuente TEXT, usos INTEGER DEFAULT 1, creado REAL, PRIMARY KEY (src_lang, dst_lang, clave))"
        )
        self._db.commit()
        self._glossary = self._load_glossary()
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="traductor")
        self._paused_until: dict[str, float] = {}
        self._session = requests.Session()
        self._session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

    # ---------- memoria local ----------
    def _load_glossary(self) -> dict:
        try:
            data = json.loads(resource_path("app", "data", "glosario.json").read_text(encoding="utf-8"))
            return {normalize(k): v for k, v in data.get(f"{self.source_lang}-{self.target_lang}", {}).items()}
        except Exception:
            log.exception("No se pudo cargar el glosario")
            return {}

    def set_languages(self, source_lang: str, target_lang: str) -> None:
        self.source_lang, self.target_lang = source_lang, target_lang
        self._glossary = self._load_glossary()

    def lookup(self, text: str) -> TranslationResult | None:
        key = normalize(text)
        with self._lock:
            row = self._db.execute(
                "SELECT traduccion, fuente FROM traducciones WHERE src_lang=? AND dst_lang=? AND clave=?",
                (self.source_lang, self.target_lang, key),
            ).fetchone()
            if row:
                self._db.execute(
                    "UPDATE traducciones SET usos=usos+1 WHERE src_lang=? AND dst_lang=? AND clave=?",
                    (self.source_lang, self.target_lang, key),
                )
                self._db.commit()
                return TranslationResult(text, row[0], SOURCE_SAME if row[1] == SOURCE_SAME else SOURCE_MEMORY)
        if key in self._glossary:
            return TranslationResult(text, self._glossary[key], SOURCE_GLOSSARY)
        stripped = key.rstrip(".!?")
        if stripped in self._glossary:
            return TranslationResult(text, self._glossary[stripped] + key[len(stripped):], SOURCE_GLOSSARY)
        return None

    def _store(self, original: str, translated: str, source: str) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO traducciones (src_lang, dst_lang, clave, original, traduccion, fuente, usos, creado)"
                " VALUES (?,?,?,?,?,?,1,?)",
                (self.source_lang, self.target_lang, normalize(original), original, translated, source, time.time()),
            )
            self._db.commit()

    def memory_size(self) -> int:
        with self._lock:
            return self._db.execute("SELECT COUNT(*) FROM traducciones").fetchone()[0]

    def clear_memory(self) -> None:
        with self._lock:
            self._db.execute("DELETE FROM traducciones")
            self._db.commit()

    # ---------- internet ----------
    def _google(self, text: str) -> tuple[str, str]:
        """Devuelve (traducción, idioma detectado). Con sl=auto también detecta textos que ya están traducidos."""
        r = self._session.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "auto", "tl": self.target_lang, "dt": "t", "q": text},
            timeout=5,
        )
        r.raise_for_status()
        data = r.json()
        out = "".join(seg[0] for seg in data[0] if seg and seg[0])
        if not out:
            raise ValueError("respuesta vacía")
        detected = data[2] if len(data) > 2 and isinstance(data[2], str) else ""
        return out, detected

    def _mymemory(self, text: str) -> tuple[str, str]:
        r = self._session.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": f"{self.source_lang}|{self.target_lang}"},
            timeout=6,
        )
        r.raise_for_status()
        data = r.json()
        if str(data.get("responseStatus")) != "200":
            raise ValueError(data.get("responseDetails") or "error de MyMemory")
        return data["responseData"]["translatedText"], self.source_lang

    RATE_LIMIT_PAUSE = 300  # segundos sin usar un servicio que nos ha limitado (HTTP 429)

    def translate_online(self, text: str) -> TranslationResult:
        now = time.time()
        for name, fn in (("Google", self._google), ("MyMemory", self._mymemory)):
            if self._paused_until.get(name, 0) > now:
                continue  # este servicio nos limitó hace poco: probamos el siguiente
            try:
                out, detected = fn(text)
                if detected and detected.split("-")[0] == self.target_lang:
                    self._store(text, text, SOURCE_SAME)
                    return TranslationResult(text, text, SOURCE_SAME)
                self._store(text, out, name)
                return TranslationResult(text, out, name)
            except requests.HTTPError as e:
                if e.response is not None and e.response.status_code == 429:
                    self._paused_until[name] = now + self.RATE_LIMIT_PAUSE
                    log.warning("%s limita las peticiones (429): se pausa %d s y se usa el siguiente servicio",
                                name, self.RATE_LIMIT_PAUSE)
                else:
                    log.warning("Fallo al traducir con %s: %s", name, e)
            except Exception as e:
                log.warning("Fallo al traducir con %s: %s", name, e)
        return TranslationResult(text, text, SOURCE_OFFLINE, ok=False)

    def translate_async(self, text: str) -> Future:
        """Devuelve un Future con un TranslationResult. Primero mira la memoria y el glosario."""
        hit = self.lookup(text)
        if hit:
            f: Future = Future()
            f.set_result(hit)
            return f
        return self._pool.submit(self.translate_online, text)

    def close(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
        with self._lock:
            self._db.close()
