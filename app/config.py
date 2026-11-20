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


DEFAULT_PROFILE = "General"


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
    # Perfiles: cada uno con una o varias zonas y, opcionalmente, el juego (.exe) al que pertenece
    #   {"name": "Chained Echoes", "regions": [[x, y, w, h], ...], "game": "chainedechoes.exe"}
    profiles: list = field(default_factory=list)
    active_profile: str = ""
    auto_profile: bool = True       # cambiar de perfil solo al cambiar de juego

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
        # Migración desde versiones con una sola zona
        if cfg.region and not cfg.profiles:
            cfg.profiles = [{"name": DEFAULT_PROFILE, "regions": [list(cfg.region)], "game": ""}]
            cfg.active_profile = DEFAULT_PROFILE
        cfg.region = []
        cfg.active()
        return cfg

    # ---------- perfiles ----------
    def get_profile(self, name: str) -> dict | None:
        return next((p for p in self.profiles if p["name"] == name), None)

    def active(self) -> dict:
        """Perfil activo (crea uno por defecto si no hay ninguno)."""
        if not self.profiles:
            self.profiles.append({"name": DEFAULT_PROFILE, "regions": [], "game": ""})
        p = self.get_profile(self.active_profile)
        if p is None:
            p = self.profiles[0]
            self.active_profile = p["name"]
        p.setdefault("regions", [])
        p.setdefault("game", "")
        return p

    def profile_for_game(self, exe: str) -> dict | None:
        exe = (exe or "").lower()
        return next((p for p in self.profiles if exe and p.get("game", "").lower() == exe), None)

    def unique_name(self, base: str) -> str:
        base = (base or "Perfil").strip()[:40] or "Perfil"
        name, n = base, 2
        while self.get_profile(name):
            name, n = f"{base} ({n})", n + 1
        return name

    def add_profile(self, name: str, game: str = "") -> dict:
        p = {"name": self.unique_name(name), "regions": [], "game": (game or "").lower()}
        self.profiles.append(p)
        return p

    def save(self) -> None:
        tmp = self.path().with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path())
