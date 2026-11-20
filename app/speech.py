"""Lectura en voz alta con las voces que trae Windows (SAPI): gratis y sin internet."""
import logging

log = logging.getLogger(__name__)

SVSF_ASYNC = 1
SVSF_PURGE = 2


class Speaker:
    """Usar siempre desde el hilo de la interfaz (COM)."""

    def __init__(self):
        self._voice = None
        self._tokens = {}
        self.available = True

    def _ensure(self) -> bool:
        if self._voice is not None:
            return True
        if not self.available:
            return False
        try:
            import comtypes.client as cc

            self._voice = cc.CreateObject("SAPI.SpVoice", dynamic=True)
            voices = self._voice.GetVoices()
            self._tokens = {voices.Item(i).GetDescription(): voices.Item(i) for i in range(voices.Count)}
        except Exception:
            log.exception("No se pudo iniciar la voz de Windows")
            self.available = False
            return False
        return True

    def voices(self) -> list[str]:
        """Nombres de las voces instaladas; primero las del idioma de destino (español)."""
        if not self._ensure():
            return []
        names = list(self._tokens)
        return sorted(names, key=lambda n: (0 if "spanish" in n.lower() or "español" in n.lower() else 1, n))

    def speak(self, text: str, voice: str = "", rate: int = 0, volume: int = 100) -> None:
        if not text.strip() or not self._ensure():
            return
        try:
            names = self.voices()
            name = voice if voice in self._tokens else (names[0] if names else "")
            if name:
                self._voice.Voice = self._tokens[name]
            self._voice.Rate = max(-10, min(10, int(rate)))
            self._voice.Volume = max(0, min(100, int(volume)))
            self._voice.Speak(text, SVSF_ASYNC | SVSF_PURGE)  # corta lo anterior y habla sin bloquear
        except Exception:
            log.exception("Fallo al leer en voz alta")

    def stop(self) -> None:
        if self._voice is not None:
            try:
                self._voice.Speak("", SVSF_ASYNC | SVSF_PURGE)
            except Exception:
                pass
