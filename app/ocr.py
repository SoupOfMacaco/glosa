"""Reconocimiento de texto con el OCR que trae Windows 10/11 (gratis y sin internet)."""
import asyncio
import logging

from PIL import Image, ImageFilter

from winrt.windows.globalization import Language
from winrt.windows.graphics.imaging import BitmapAlphaMode, BitmapPixelFormat, SoftwareBitmap
from winrt.windows.media.ocr import OcrEngine
from winrt.windows.security.cryptography import CryptographicBuffer

log = logging.getLogger(__name__)

ENGLISH_OCR_CAPABILITY = "Language.OCR~~~en-US~0.0.1.0"


def available_languages() -> list[str]:
    try:
        return [l.language_tag for l in OcrEngine.available_recognizer_languages]
    except Exception:
        log.exception("No se pudieron listar los idiomas de OCR")
        return []


def has_language(prefix: str) -> bool:
    return any(t.lower().startswith(prefix.lower()) for t in available_languages())


class WindowsOcr:
    """Motor OCR. Hay que crearlo y usarlo siempre desde el mismo hilo."""

    def __init__(self, preferred: str = "en"):
        self.loop = asyncio.new_event_loop()
        self.engine, self.language = self._create(preferred)
        self.max_dim = OcrEngine.max_image_dimension or 2600

    @staticmethod
    def _create(preferred: str):
        langs = available_languages()
        ordered = [t for t in langs if t.lower().startswith(preferred.lower())]
        ordered += [t for t in langs if t not in ordered]
        for tag in ordered:
            eng = OcrEngine.try_create_from_language(Language(tag))
            if eng:
                return eng, tag
        eng = OcrEngine.try_create_from_user_profile_languages()
        if eng:
            return eng, eng.recognizer_language.language_tag
        raise RuntimeError("Windows no tiene ningún idioma de OCR instalado")

    def _prepare(self, img: Image.Image) -> Image.Image:
        g = img.convert("L")
        # Ampliar ayuda con fuentes pequeñas o pixeladas, y un ligero desenfoque suaviza los bordes
        scale = 1
        if g.height < 400:
            scale = 3 if g.height < 150 else 2
        while scale > 1 and max(g.width, g.height) * scale > self.max_dim:
            scale -= 1
        if scale > 1:
            g = g.resize((g.width * scale, g.height * scale), Image.NEAREST)
            g = g.filter(ImageFilter.GaussianBlur(scale * 0.5))
        if max(g.width, g.height) > self.max_dim:
            g.thumbnail((self.max_dim, self.max_dim), Image.LANCZOS)
        return g

    def recognize(self, img: Image.Image) -> list[str]:
        im = self._prepare(img).convert("RGBA")
        buf = CryptographicBuffer.create_from_byte_array(im.tobytes("raw", "BGRA"))
        bmp = SoftwareBitmap.create_copy_from_buffer(
            buf, BitmapPixelFormat.BGRA8, im.width, im.height, BitmapAlphaMode.PREMULTIPLIED
        )

        async def run():
            return await self.engine.recognize_async(bmp)

        result = self.loop.run_until_complete(run())
        return [line.text for line in result.lines]
