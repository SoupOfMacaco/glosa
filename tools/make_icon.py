"""Genera los iconos a partir de assets/logo.svg: icon.ico, logo.png y la imagen del instalador."""
import io
import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

app = QGuiApplication.instance() or QGuiApplication(sys.argv)
renderer = QSvgRenderer(str(ASSETS / "logo.svg"))


def render(size: int) -> Image.Image:
    img = QImage(size, size, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    renderer.render(p)
    p.end()
    buf = QBuffer()
    buf.open(QIODevice.WriteOnly)
    img.save(buf, "PNG")
    return Image.open(io.BytesIO(bytes(buf.data()))).convert("RGBA")


big = render(1024)
big.resize((512, 512), Image.LANCZOS).save(ASSETS / "logo.png")
sizes = [16, 20, 24, 32, 40, 48, 64, 128, 256]
frames = [render(s * 4).resize((s, s), Image.LANCZOS) for s in sizes]
frames[-1].save(ASSETS / "icon.ico", sizes=[(s, s) for s in sizes], append_images=frames[:-1])
# Imagen pequeña del asistente de instalación (Inno Setup usa BMP)
wiz = Image.new("RGB", (110, 110), "white")
wiz.paste(render(400).resize((100, 100), Image.LANCZOS), (5, 5), render(400).resize((100, 100), Image.LANCZOS))
wiz.save(ASSETS / "wizard-small.bmp")
print("iconos generados en", ASSETS)
