"""Limpieza del texto reconocido por el OCR."""
import itertools
import logging
import re

log = logging.getLogger(__name__)

# Confusiones típicas del OCR con fuentes pixeladas
CONFUSIONS = {
    "y": "r", "r": "y", "u": "v", "v": "u", "l": "i", "i": "l",
    "p": "r", "g": "y", "0": "o", "1": "l", "5": "s", "8": "b", "c": "e", "e": "c", "n": "h", "h": "n",
}
WORD_RE = re.compile(r"[A-Za-z][A-Za-z']*[A-Za-z]|[A-Za-z]")

_spell = None


def _speller():
    global _spell
    if _spell is None:
        from spellchecker import SpellChecker
        _spell = SpellChecker(language="en", distance=1)
    return _spell


def _match_case(src: str, fixed: str) -> str:
    if src.isupper() and len(src) > 1:
        return fixed.upper()
    if src[0].isupper():
        return fixed[0].upper() + fixed[1:]
    return fixed


def _confusion_variants(word: str, max_changes: int = 3):
    idx = [i for i, ch in enumerate(word) if ch in CONFUSIONS]
    for n in range(1, min(max_changes, len(idx)) + 1):
        for combo in itertools.combinations(idx, n):
            chars = list(word)
            for i in combo:
                chars[i] = CONFUSIONS[chars[i]]
            yield "".join(chars)


def fix_word(word: str) -> str:
    if "'" in word or len(word) < 3:
        return word
    sp = _speller()
    low = word.lower()
    if sp.known([low]):
        return word
    # 1) Sustituir caracteres que el OCR suele confundir (y/r, u/v, l/i...)
    best, best_freq = None, 0.0
    for v in _confusion_variants(low):
        if sp.known([v]):
            f = sp.word_usage_frequency(v)
            if f > best_freq:
                best, best_freq = v, f
    if best:
        return _match_case(word, best)
    # 2) Corrección general solo en minúsculas, para no estropear nombres propios
    if word.islower() and len(word) >= 4:
        c = sp.correction(low)
        if c and c != low:
            return c
    return word


def spellfix(text: str) -> str:
    try:
        return WORD_RE.sub(lambda m: fix_word(m.group(0)), text)
    except Exception:
        log.exception("Fallo en la corrección ortográfica")
        return text


def lines_to_paragraphs(lines: list[str]) -> str:
    """Une las líneas del OCR en párrafos (los diálogos suelen partirse en varias líneas)."""
    lines = [re.sub(r"\s+", " ", l).strip() for l in lines]
    lines = [l for l in lines if l]
    if not lines:
        return ""
    longest = max(len(l) for l in lines)
    paras, cur = [], lines[0]
    for prev, line in zip(lines, lines[1:]):
        ends_sentence = prev.endswith((".", "!", "?", ":", '"', "…"))
        short_label = len(prev) < 0.4 * longest and line[:1].isupper()
        if ends_sentence or short_label:
            paras.append(cur)
            cur = line
        else:
            cur += " " + line
    paras.append(cur)
    return "\n".join(paras)


def looks_like_text(text: str) -> bool:
    compact = text.replace(" ", "").replace("\n", "")
    letters = sum(ch.isalpha() for ch in compact)
    return letters >= 2 and letters >= 0.4 * len(compact)
