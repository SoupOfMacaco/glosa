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
SOURCE_MANUAL = "corregida"
SOURCE_PROFILE_GLOSSARY = "glosario del perfil"

PLACEHOLDER = "ZQ{}X"            # los traductores dejan intacto este tipo de palabra inventada
PLACEHOLDER_RE = re.compile(r"ZQ(\d+)X", re.IGNORECASE)


def _glossary_terms(text: str, glossary: dict) -> list[tuple[str, str]]:
    """Términos del glosario que aparecen en el texto (los más largos primero)."""
    found = []
    for term in sorted(glossary, key=len, reverse=True):
        if term.strip() and re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.IGNORECASE):
            found.append((term, glossary[term]))
    return found


def protect_terms(text: str, terms: list[tuple[str, str]]) -> tuple[str, list[str]]:
    """Sustituye cada término por un marcador. Devuelve el texto protegido y, por marcador, el texto final."""
    finals = []
    for term, replacement in terms:
        idx = len(finals)

        def repl(m, idx=idx):
            return PLACEHOLDER.format(idx)

        new_text = re.sub(rf"(?<!\w){re.escape(term)}(?!\w)", repl, text, flags=re.IGNORECASE)
        if new_text != text:
            text = new_text
            finals.append(replacement.strip() or term)  # vacío = no traducir (se deja el término original)
    return text, finals


def restore_terms(text: str, finals: list[str]) -> str:
    return PLACEHOLDER_RE.sub(lambda m: finals[int(m.group(1))] if int(m.group(1)) < len(finals) else m.group(0), text)


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

    def lookup(self, text: str, manual_only: bool = False) -> TranslationResult | None:
        key = normalize(text)
        with self._lock:
            row = self._db.execute(
                "SELECT traduccion, fuente FROM traducciones WHERE src_lang=? AND dst_lang=? AND clave=?",
                (self.source_lang, self.target_lang, key),
            ).fetchone()
            if row and (not manual_only or row[1] == SOURCE_MANUAL):
                self._db.execute(
                    "UPDATE traducciones SET usos=usos+1 WHERE src_lang=? AND dst_lang=? AND clave=?",
                    (self.source_lang, self.target_lang, key),
                )
                self._db.commit()
                source = {SOURCE_SAME: SOURCE_SAME, SOURCE_MANUAL: SOURCE_MANUAL}.get(row[1], SOURCE_MEMORY)
                return TranslationResult(text, row[0], source)
        if manual_only:
            return None
        if key in self._glossary:
            return TranslationResult(text, self._glossary[key], SOURCE_GLOSSARY)
        stripped = key.rstrip(".!?")
        if stripped in self._glossary:
            return TranslationResult(text, self._glossary[stripped] + key[len(stripped):], SOURCE_GLOSSARY)
        return None

    def _store(self, original: str, translated: str, source: str) -> None:
        if self._closed:
            return  # la app se está cerrando: una traducción que llegue tarde no se guarda
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO traducciones (src_lang, dst_lang, clave, original, traduccion, fuente, usos, creado)"
                " VALUES (?,?,?,?,?,?,1,?)",
                (self.source_lang, self.target_lang, normalize(original), original, translated, source, time.time()),
            )
            self._db.commit()

    def set_correction(self, original: str, translated: str) -> None:
        """Guarda una traducción corregida a mano: tiene prioridad sobre todo lo demás y no se sobrescribe."""
        self._store(original, translated, SOURCE_MANUAL)

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

    @staticmethod
    def _done(result: TranslationResult) -> Future:
        f: Future = Future()
        f.set_result(result)
        return f

    def translate_async(self, text: str, glossary: dict | None = None) -> Future:
        """Devuelve un Future con un TranslationResult.

        Orden: corrección manual > glosario del perfil > memoria > glosario incluido > internet.
        """
        manual = self.lookup(text, manual_only=True)
        if manual:
            return self._done(manual)
        glossary = {k: v for k, v in (glossary or {}).items() if k.strip()}
        if glossary:
            for term, replacement in glossary.items():
                if normalize(term) == normalize(text).rstrip(".!?"):
                    return self._done(TranslationResult(text, replacement.strip() or text, SOURCE_PROFILE_GLOSSARY))
            terms = _glossary_terms(text, glossary)
            if terms:
                protected, finals = protect_terms(text, terms)
                return self._pool.submit(self._translate_protected, text, protected, finals)
        hit = self.lookup(text)
        if hit:
            return self._done(hit)
        return self._pool.submit(self.translate_online, text)

    def _translate_protected(self, original: str, protected: str, finals: list[str]) -> TranslationResult:
        """Traduce con los términos del glosario sustituidos por marcadores y luego los repone."""
        res = self.lookup(protected) or self.translate_online(protected)
        if not res.ok:
            return TranslationResult(original, restore_terms(protected, finals), res.source, ok=False)
        if res.same_language:
            return TranslationResult(original, original, res.source)
        missing = len(set(PLACEHOLDER_RE.findall(res.text))) < len(finals)
        if missing:
            log.warning("El traductor alteró algún término del glosario: %r", res.text)
        return TranslationResult(original, restore_terms(res.text, finals), f"{res.source} + glosario")

    _closed = False

    def close(self) -> None:
        self._closed = True
        self._pool.shutdown(wait=False, cancel_futures=True)
        with self._lock:
            self._db.close()
