#!/usr/bin/env python3
"""Rendu d'un sous-titre de STORY en PNG transparent, selon le skin choisi au /setup-stories.

POURQUOI un PNG et pas un fichier .ass / drawtext :
  ni `drawtext` ni libass ne savent flouter UNIQUEMENT l'ombre (le `\\blur` d'ASS floute aussi le
  texte). On compose donc chaque sous-titre à la main avec Pillow, ce qui donne un rendu propre
  quel que soit le skin et, en bonus, la MESURE de largeur -> garantie « toujours une seule ligne ».

Les réglages (police, taille, skin, couleurs) viennent de brand.config.json -> section `story`,
écrite par /setup-stories. Ce fichier ne contient AUCUNE identité : que des mécanismes.
"""
import json
import math
import pathlib
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
try:  # Monteur IA 2 : réglages et polices dans le dossier Monteur IA, même depuis un Reel
    from lieux import MAISON as ROOT  # noqa: E402
except ImportError:  # Monteur IA 1 : la racine du projet
    pass

W, H = 1080, 1920
SAFE_X = 100                      # safe-zone latérale Instagram
MAX_TEXT_W = W - 2 * SAFE_X       # 880 px : au-delà on re-coupe le sous-titre

# --- Défauts (utilisés tant que /setup-stories n'a pas été lancé) -------------
DEFAULT_STORY = {
    "captionsSkin": "ombre",      # ombre | contour | plaque | bloc
    "captionFont": None,          # chemin .ttf ; sinon fallback Inter 900 du produit principal
    "captionSize": 56,
    "captionY": 1180,
    "captionCase": "as-is",       # "as-is" | "upper"
    "captionColor": "#ffffff",
    "plateColor": "#000000",      # fond du skin plaque/bloc (bloc préfère visual.accent s'il existe)
    "shadow": {"opacity": 0.85, "blur": 0.24, "distance": 5.0, "angle": -45.0},
}
BLUR_FULL_SCALE = 30.0   # flou 100 % == rayon gaussien de 30 px (calibré à l'oeil)

_FONT_FALLBACKS = ["assets/fonts/Inter-900.ttf", "assets/fonts/Inter-Black.ttf"]


def load_config():
    """brand.config.json du produit principal + section `story` (défauts si absente)."""
    cfg = {}
    p = ROOT / "brand.config.json"
    if p.exists():
        try:
            cfg = json.loads(p.read_text())
        except (OSError, ValueError):
            cfg = {}
    story = {**DEFAULT_STORY, **(cfg.get("story") or {})}
    story["shadow"] = {**DEFAULT_STORY["shadow"], **(story.get("shadow") or {})}
    # le skin `bloc` reprend l'accent de la marque s'il est réglé (cohérence avec les Reels)
    accent = (cfg.get("visual") or {}).get("accent")
    if story["captionsSkin"] == "bloc" and accent and not (cfg.get("story") or {}).get("plateColor"):
        story["plateColor"] = accent
    return story


def _hex(color, alpha=255):
    c = color.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), alpha)


def font_path(story=None):
    story = story or load_config()
    if story.get("captionFont"):
        p = pathlib.Path(story["captionFont"])
        p = p if p.is_absolute() else ROOT / p
        if p.exists():
            return p
    for f in _FONT_FALLBACKS:
        if (ROOT / f).exists():
            return ROOT / f
    raise SystemExit("Aucune police de sous-titre trouvée : lance /setup-stories, ou vérifie "
                     "assets/fonts/ (le produit principal fournit Inter-900.ttf).")


def load_font(size, story=None):
    return ImageFont.truetype(str(font_path(story)), size)


def measure(text, size, story=None):
    """Largeur/hauteur du texte rendu, en px."""
    f = load_font(size, story)
    box = f.getbbox(text)
    return box[2] - box[0], box[3] - box[1]


def _shadow_offset(distance, angle_deg):
    """(dx, dy) en px. Angle : 0 = à droite, négatif = vers le bas."""
    a = math.radians(angle_deg)
    return distance * math.cos(a), -distance * math.sin(a)


def render_caption(text, size=None, story=None):
    """PNG RGBA serré autour du texte, rendu selon le skin. Retourne (Image, dx_ancre, dy_ancre).

    L'ancre est le centre du GLYPHE (pas du PNG, qui porte marges de flou / padding de plaque).
    """
    story = story or load_config()
    size = size or story["captionSize"]
    f = load_font(size, story)
    box = f.getbbox(text)
    tw, th = box[2] - box[0], box[3] - box[1]
    color = _hex(story["captionColor"])
    skin = story["captionsSkin"]

    if skin == "ombre":
        sh = story["shadow"]
        radius = sh["blur"] * BLUR_FULL_SCALE
        dx, dy = _shadow_offset(sh["distance"], sh["angle"])
        pad = int(radius * 3 + abs(dx) + abs(dy) + 4)
        size_px = (tw + 2 * pad, th + 2 * pad)
        origin = (pad - box[0], pad - box[1])
        # calque d'ombre : texte noir opaque, décalé, flouté, puis passé à l'opacité voulue
        shadow_layer = Image.new("RGBA", size_px, (0, 0, 0, 0))
        ImageDraw.Draw(shadow_layer).text((origin[0] + dx, origin[1] + dy), text,
                                          font=f, fill=(0, 0, 0, 255))
        if radius > 0:
            shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius))
        a = shadow_layer.getchannel("A").point(lambda v: int(v * sh["opacity"]))
        shadow_layer.putalpha(a)
        text_layer = Image.new("RGBA", size_px, (0, 0, 0, 0))
        ImageDraw.Draw(text_layer).text(origin, text, font=f, fill=color)
        img = Image.alpha_composite(shadow_layer, text_layer)
        return img, pad + tw / 2, pad + th / 2

    if skin == "contour":
        stroke = max(2, size // 18)
        pad = stroke * 3 + 4
        size_px = (tw + 2 * pad, th + 2 * pad)
        origin = (pad - box[0], pad - box[1])
        img = Image.new("RGBA", size_px, (0, 0, 0, 0))
        ImageDraw.Draw(img).text(origin, text, font=f, fill=color,
                                 stroke_width=stroke, stroke_fill=(0, 0, 0, 230))
        return img, pad + tw / 2, pad + th / 2

    if skin in ("plaque", "bloc"):
        pad_x, pad_y = int(size * 0.42), int(size * 0.24)
        alpha = 170 if skin == "plaque" else 255
        plate = _hex(story["plateColor"], alpha)
        # le texte doit rester lisible sur la plaque : plaque claire -> texte noir
        r, g, b, _ = plate
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        fill = color if skin == "plaque" else ((16, 16, 16, 255) if lum > 140 else color)
        size_px = (tw + 2 * pad_x, th + 2 * pad_y)
        origin = (pad_x - box[0], pad_y - box[1])
        img = Image.new("RGBA", size_px, (0, 0, 0, 0))
        radius = int(size * 0.22) if skin == "plaque" else 0
        ImageDraw.Draw(img).rounded_rectangle([0, 0, size_px[0] - 1, size_px[1] - 1],
                                              radius=radius, fill=plate)
        ImageDraw.Draw(img).text(origin, text, font=f, fill=fill)
        return img, pad_x + tw / 2, pad_y + th / 2

    raise SystemExit(f"Skin de sous-titre inconnu : « {skin} » (ombre | contour | plaque | bloc). "
                     "Relance /setup-stories.")


def caption_png(text, out_path, size=None, y=None, story=None):
    """Écrit un PNG PLEIN CADRE 1080x1920, texte centré en x, centre vertical à `y`."""
    story = story or load_config()
    size = size or story["captionSize"]
    y = y or story["captionY"]
    tw, _ = measure(text, size, story)
    if tw > MAX_TEXT_W:
        raise SystemExit(f"Sous-titre trop large ({tw:.0f} > {MAX_TEXT_W} px) : « {text} »\n"
                         f"  -> re-couper le sous-titre (règle : TOUJOURS une seule ligne).")
    frame = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    img, ax, ay = render_caption(text, size=size, story=story)
    frame.alpha_composite(img, (int(W / 2 - ax), int(y - ay)))
    out_path = pathlib.Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    frame.save(out_path)
    return out_path
