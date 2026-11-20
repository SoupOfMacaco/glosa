"""Configuración persistente (JSON en la carpeta de datos)."""
import json
import logging
from dataclasses import asdict, dataclass, field, fields

from .paths import data_dir

log = logging.getLogger(__name__)

# Modos de visualización
MODE_FLOAT = "flotante"   # sobre/encima del texto original
MODE_CORNER = "esquina"   # en una esquina de la pantalla
MODE_BOTH = "ambos"
MODES = [MODE_FLOAT, MODE_CORNER, MODE_BOTH]
MODE_LABELS = {
    MODE_FLOAT: "Flotante sobre el texto",
    MODE_CORNER: "En una esquina",
    MODE_BOTH: "Ambos a la vez",
}

FLOAT_COVER = "tapar"     # tapa el texto original
FLOAT_ABOVE = "arriba"    # justo encima, sin taparlo
FLOAT_LABELS = {FLOAT_COVER: "Tapando el texto original", FLOAT_ABOVE: "Justo encima del texto"}

CORNERS = {
    "sup-der": "Arriba a la derecha",
    "sup-izq": "Arriba a la izquierda",
    "inf-der": "Abajo a la derecha",
    "inf-izq": "Abajo a la izquierda",
}

TARGET_LANGS = {
    "es": "Español",
    "en": "Inglés",
    "pt": "Portugués",
    "fr": "Francés",
    "it": "Italiano",
    "de": "Alemán",
}


@dataclass
class Config:
    # Zona a leer en píxeles físicos de pantalla: [x, y, ancho, alto]
    region: list = field(default_factory=list)
    display_mode: str = MODE_BOTH
    float_position: str = FLOAT_COVER
    corner: str = "sup-der"
    font_size: int = 15
    opacity: int = 88               # 30..100 %
    interval_ms: int = 250          # cada cuánto se mira la zona
    wait_typing: bool = True        # esperar a que el texto deje de "escribirse"
    settle_ms: int = 300
    show_original: bool = True      # en la esquina, mostrar también el original
    hide_when_empty: bool = True
    spellfix: bool = True           # corregir errores típicos del OCR
    source_lang: str = "en"
    target_lang: str = "es"
    autostart: bool = False
    check_updates: bool = True
    first_run: bool = True

    @classmethod
    def path(cls):
        return data_dir() / "config.json"

    @classmethod
    def load(cls) -> "Config":
        cfg = cls()
        try:
            raw = json.loads(cls.path().read_text(encoding="utf-8"))
            names = {f.name for f in fields(cls)}
            for k, v in raw.items():
                if k in names:
                    setattr(cfg, k, v)
        except FileNotFoundError:
            pass
        except Exception:
            log.exception("No se pudo leer la configuración; se usan valores por defecto")
        if cfg.display_mode not in MODES:
            cfg.display_mode = MODE_BOTH
        return cfg

    def save(self) -> None:
        tmp = self.path().with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path())
