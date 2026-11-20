"""Genera assets/icon.ico (bocadillo de diálogo con "ES")."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

S = 256
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((16, 24, 240, 184), radius=40, fill=(0, 150, 220, 255))
d.polygon([(70, 176), (130, 176), (60, 238)], fill=(0, 150, 220, 255))
try:
    font = ImageFont.truetype("segoeuib.ttf", 104)
except OSError:
    font = ImageFont.load_default()
d.text((128, 104), "ES", font=font, fill="white", anchor="mm")
out = Path(__file__).resolve().parent.parent / "assets" / "icon.ico"
out.parent.mkdir(exist_ok=True)
img.save(out, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icono:", out)
