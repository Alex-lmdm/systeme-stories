#!/usr/bin/env python3
"""Pipeline STORY Instagram (format vertical 1080x1920, 30 fps) — 100 % ffmpeg, sans studio.

POURQUOI un pipeline séparé des Reels : une story = visage plein écran, sous-titres sobres,
parfois un plan filmé en plein écran et un petit bandeau motion. Zéro split-screen, zéro
composition HTML. Passer par HyperFrames coûterait le prix d'un Reel pour un format publié
beaucoup plus souvent et qui vit 24 h. La doctrine complète vit dans le skill `story`.

Tout se déclare dans stories/<slug>/story.json ; ce fichier ne touche JAMAIS un Reel ni derush/
-> une story et un reel peuvent être montés en parallèle.

Monteur IA 2 (app HyperFrames) : une story se monte TECHNIQUEMENT COMME UN REEL, avec le style et
les règles du Système Stories. stories/<slug>/ est un projet de l'app (meta.json monteurIa.lieu =
"story", une conversation neuve par story) et son index.html une vraie composition HyperFrames,
écrite par `compose` depuis story.json : visage (cut.mp4) et voix, plans insérés, bandeaux et
sous-titres en éléments séparés, retouchables à la main dans l'app. L'export est natif, comme un
Reel : bouton Export de l'app, ou `story.py render` (HyperFrames). Une retouche faite dans l'app
(texte, emoji, timing, place, taille, volume) n'est jamais perdue : `compose` la REPORTE dans
story.json avant de réécrire (il compare index.html à l'état qu'il avait posé, noté dans
.composee.json). `--ecraser` ne sert qu'à une story d'avant cette version, sans cet état.
Monteur IA 1 (sans app) : rendu ffmpeg, comme avant.

Les chemins (ffmpeg, whisper), le style des sous-titres, le cadrage du visage (faceZoom), la
musique de fond et la banque de B-rolls viennent de brand.config.json (sections `env` et
`story`, écrites par /setup-stories) : rien n'est codé en dur.

Usage :
  python3 tools/story.py init      <slug> --rush /chemin/rush.MP4 [--ouvrir]
  python3 tools/story.py init      <slug> --brief "<demande>" --ouvrir   (app : script d'abord, vidéo plus tard)
  python3 tools/story.py silences  <slug> [--noise -40] [--d 0.18] [--no-text]
  python3 tools/story.py cut       <slug>
  python3 tools/story.py words     <slug>
  python3 tools/story.py captions  <slug>
  python3 tools/story.py preview   <slug> [--t 2.0]
  python3 tools/story.py compose   <slug> [--ecraser]      (Monteur IA 2 : la composition de l'app)
  python3 tools/story.py render    <slug>
  python3 tools/story.py close     <slug> [--no-archive]
  python3 tools/story.py broll     list | apercu <vidéo> | add <vidéo> --description "…" [--nom x] [--categorie y]
"""
import argparse
import difflib
import hashlib
import html as HTML
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
from html.parser import HTMLParser

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import story_text as ST  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = False   # Monteur IA 2 : chaque story est aussi un projet de l'app HyperFrames
try:  # Monteur IA 2 (un Reel = un projet) : les stories vivent dans le dossier Monteur IA, jamais dans un Reel
    from lieux import MAISON as ROOT  # noqa: E402
    APP = True
except ImportError:  # Monteur IA 1 : la racine du projet
    # Windows : une sortie lue par l'agent (redirigée) est en cp1252, et un « ⚠️ » y fait planter
    # l'outil. Monteur IA 2 règle ça dans lieux.py.
    for _flux in (sys.stdout, sys.stderr):
        try:
            _flux.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
STORIES = ROOT / "stories"

W, H, FPS = 1080, 1920, "30000/1001"
DEFAULTS = {
    "pad_start": 0.04,      # début : garder l'élan d'attaque (voyelles fragiles)
    "pad_end": 0.02,        # fin : resserrée -> ~0.10 s de souffle inter-cut
}


# ----------------------------------------------------------------- env & style
def _brand_config():
    p = ROOT / "brand.config.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return {}


def _env_bin(key, fallback):
    """Binaire réglé dans env : son chemin, ou le dossier qui le contient (convention du dérush
    pour ffmpegPath) ; sinon le PATH."""
    v = (_brand_config().get("env") or {}).get(key)
    if not v:
        return fallback
    p = pathlib.Path(v).expanduser()
    if p.is_dir():
        for ext in ("", ".exe"):
            if (p / f"{fallback}{ext}").is_file():
                return str(p / f"{fallback}{ext}")
        return fallback
    if p.is_file() or shutil.which(v):
        return v
    return fallback


FFMPEG = _env_bin("ffmpegPath", "ffmpeg")
WHISPER = _env_bin("whisperCli", "whisper-cli")


def _ffprobe_bin():
    """ffprobe vit à côté de ffmpeg : si ffmpegPath est un chemin custom (Windows), on le dérive."""
    p = pathlib.Path(FFMPEG)
    if p.name.lower().startswith("ffmpeg") and p.parent != pathlib.Path("."):
        cand = p.with_name(p.name.replace("ffmpeg", "ffprobe"))
        if cand.exists():
            return str(cand)
    return "ffprobe"


FFPROBE = _ffprobe_bin()


def whisper_model():
    v = (_brand_config().get("env") or {}).get("whisperModel")
    if v and pathlib.Path(v).expanduser().exists():
        return str(pathlib.Path(v).expanduser())
    for d in ("~/.cache/monteur-ia/whisper", "~/.cache/hyperframes/whisper/models",
              "~/whisper-models", "~/.cache/whisper"):
        hits = sorted(pathlib.Path(d).expanduser().glob("ggml-*.bin"))
        if hits:
            return str(hits[0])
    sys.exit("Modèle Whisper introuvable : renseigne env.whisperModel dans brand.config.json "
             "(le produit principal l'écrit à l'installation).")


def story_style():
    return ST.load_config()


# --------------------------------------------------------------------------- io
def sdir(slug):
    return STORIES / slug


def load(slug):
    p = sdir(slug) / "story.json"
    if not p.exists():
        sys.exit(f"Aucune story « {slug} ». Lance d'abord : python3 tools/story.py init {slug} --rush …")
    st = story_style()
    # La musique de brand.config est le défaut de toute story ; "music": null dans story.json = aucune.
    musique = st.get("music") if isinstance(st.get("music"), dict) else None
    base = {**DEFAULTS, "caption_y": st["captionY"], "caption_size": st["captionSize"],
            "caption_case": st["captionCase"], "face_zoom": st.get("faceZoom") or 1.0,
            "face_zoom_y": st.get("faceZoomY", 0.38), "music": musique}
    return {**base, **json.loads(p.read_text(encoding="utf-8"))}


def save(slug, cfg):
    (sdir(slug) / "story.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8")


# ----------------------------------------------------------- projet de l'app
COMPOSITION = """<!DOCTYPE html>
<html lang="fr">
  <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=1080, height=1920">
    <script src="assets/vendor/gsap.min.js"></script>
    <!-- Story « {slug} » ({etat}), écrite par tools/story.py compose depuis story.json. Une retouche
         faite ici, dans l'app, est reportée dans story.json avant toute réécriture (compose l'adopte). -->
    <style>
{polices}      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1080px; height: 1920px; overflow: hidden; background: #141414; }}
      .plein {{ position: absolute; left: 0; top: 0; width: 1080px; height: 1920px; object-fit: cover; }}
      .repere {{ position: absolute; display: flex; align-items: center; justify-content: center; }}
      .sous-titre {{ left: 0; width: 1080px; white-space: nowrap; font-family: "StoryCaption", sans-serif;
        line-height: 1; color: {couleur}; }}
      .sous-titre span {{ {skin} }}
      .ligne {{ position: absolute; left: 120px; right: 120px; color: #a3a3a3;
        font-family: "Avenir Next", "Segoe UI", Arial, sans-serif; font-size: 46px; line-height: 1.35; }}
      #titre {{ top: 760px; color: #ffffff; font-weight: 800; font-size: 92px; line-height: 1.05; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="{cid}" data-start="0" data-duration="{dur}" data-fps="30" data-width="1080" data-height="1920">
{corps}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["{cid}"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
"""
IMAGES = (".png", ".jpg", ".jpeg", ".webp", ".gif")
VIDES = {"img", "br", "source", "meta", "link", "input", "hr"}
ID_ECRIT = re.compile(r"(st|plan|bandeau)-\d+|musique")


# --------------------------------------------------- retouches faites dans l'app
# Le créateur retouche sa story dans l'app (texte d'un sous-titre, emoji, timing, place, taille,
# volume). Ces retouches vivent dans index.html ; story.json reste la source de `compose`. Pour
# qu'une réécriture ne les efface jamais, `compose` relève à chaque écriture l'état qu'il a posé
# (.composee.json), puis, avant la suivante, compare index.html à cet état et REPORTE dans
# story.json tout ce qui a changé.
class _Lecteur(HTMLParser):
    """Relève les éléments que compose a écrits (sous-titres, plans, bandeaux, musique)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.el, self._cour, self._prof = {}, None, 0

    def handle_starttag(self, tag, attrs):
        a = {k: (v or "") for k, v in attrs}
        if self._cour:
            if tag not in VIDES:
                self._prof += 1
            if tag == "span" and self.el[self._cour]["span"] is None:
                self.el[self._cour]["span"] = a
        elif ID_ECRIT.fullmatch(a.get("id", "")):
            self.el[a["id"]] = {"tag": tag, "attrs": a, "texte": "", "span": None}
            if tag not in VIDES:
                self._cour, self._prof = a["id"], 0

    def handle_endtag(self, tag):
        if self._cour and tag not in VIDES:
            if self._prof == 0:
                self._cour = None
            else:
                self._prof -= 1

    def handle_data(self, data):
        if self._cour:
            self.el[self._cour]["texte"] += data


def _style(s):
    return {k.strip(): v.strip() for k, v in (p.split(":", 1) for p in (s or "").split(";") if ":" in p)}


def _px(v, defaut=0.0):
    m = re.match(r"\s*(-?[\d.]+)", v or "")
    return float(m.group(1)) if m else defaut


def _valeurs(texte):
    """Ce que montre index.html, élément par élément, dans les unités de story.json."""
    lec = _Lecteur()
    lec.feed(texte)
    out = {}
    for i, e in lec.el.items():
        a = e["attrs"]
        start = round(_px(a.get("data-start")), 3)
        v = {"start": start, "end": round(start + _px(a.get("data-duration")), 3)}
        if i.startswith("st-"):
            st, sp = _style(a.get("style")), _style((e["span"] or {}).get("style"))
            tx, ty = ((st.get("translate") or "0px 0px").split() + ["0px"])[:2]
            v["t"] = " ".join(e["texte"].split())
            v["size"] = round(_px(sp.get("font-size") or st.get("font-size"), 56), 1)
            v["x"] = round(W / 2 + _px(tx), 1)
            v["y"] = round(_px(st.get("top")) + _px(st.get("height")) / 2 + _px(ty), 1)
        elif i == "musique" or i.startswith("plan-"):
            v["media_start"] = round(_px(a.get("data-media-start")), 3)
            if i == "musique":
                v["volume"] = round(_px(a.get("data-volume"), 1.0), 3)
        out[i] = v
    return out


def _base_path(slug):
    return sdir(slug) / ".composee.json"


def adopter(slug, cfg, page):
    """Reporte dans cfg (story.json) les retouches faites dans l'app depuis la dernière écriture.
    Rend la liste des retouches reportées (et sauve story.json s'il y en a)."""
    try:
        base = json.loads(_base_path(slug).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not page.exists():
        return []
    lu = _valeurs(page.read_text(encoding="utf-8"))
    notes, suppr = [], []
    for ident, b in base.get("ids", {}).items():
        liste, i = b["liste"], b["i"]
        if liste == "music":
            entree = cfg.get("music")
        else:
            lst = cfg.get(liste, [])
            # story.json a pu bouger depuis : on retrouve l'entrée telle qu'elle était écrite
            if not (i < len(lst) and lst[i] == b["entree"]):
                i = next((k for k, x in enumerate(lst) if x == b["entree"]), None)
            entree = lst[i] if i is not None else None
        if not isinstance(entree, dict):
            continue
        if ident not in lu:
            if liste != "music":
                suppr.append((liste, i))
            else:
                cfg["music"] = None
            notes.append(f"{ident} supprimé dans l'app")
            continue
        for k, val in lu[ident].items():
            avant = b["v"].get(k)
            if avant is None or val == avant or (isinstance(val, float) and abs(val - avant) < 1e-3):
                continue
            if k == "media_start":
                entree["in"] = round(entree.get("in", 0) + val - avant, 3)
            else:
                entree[k] = val
            notes.append(f"{ident} : {k} {avant} -> {val}")
    for liste, i in sorted(suppr, key=lambda x: -x[1]):
        del cfg[liste][i]
    inconnus = [i for i in lu if i not in base.get("ids", {})]
    if inconnus:
        notes.append("⚠️  élément(s) ajouté(s) dans l'app, non reportables dans story.json : " + ", ".join(inconnus))
    if notes:
        save(slug, cfg)
    return notes


def _noter_base(slug, contenu, cfg, medias, bandeaux):
    """État posé par cette écriture, pour reconnaître ensuite les retouches de l'app."""
    lu, ids = _valeurs(contenu), {}
    sources = ([("captions", i, c) for i, c in enumerate(cfg.get("captions", []))],
               [("media", cfg.get("media", []).index(m), m) for m in medias],
               [("overlays", cfg.get("overlays", []).index(o), o) for o in bandeaux])
    for prefixe, lot in zip(("st", "plan", "bandeau"), sources):
        for n, (liste, i, entree) in enumerate(lot):
            ident = f"{prefixe}-{n}"
            if ident in lu:
                ids[ident] = {"liste": liste, "i": i, "entree": json.loads(json.dumps(entree)), "v": lu[ident]}
    if "musique" in lu:
        ids["musique"] = {"liste": "music", "i": None, "entree": cfg.get("music"), "v": lu["musique"]}
    _base_path(slug).write_text(json.dumps({"ids": ids}, ensure_ascii=False, indent=1), encoding="utf-8")


def _chemin(src):
    """Un chemin de story.json ou de brand.config : absolu, ou relatif au dossier Monteur IA."""
    p = pathlib.Path(str(src)).expanduser()
    return p if p.is_absolute() else ROOT / p


def _musique(slug, mu):
    """Copie la musique de fond dans la story (le rendu ne voit que son dossier)."""
    src = _chemin(mu["src"])
    if not src.exists():
        sys.exit(f"Musique introuvable : {src} (brand.config.json -> story.music, ou story.json -> music)")
    out = sdir(slug) / "assets" / "musique" / src.name
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists() or out.stat().st_size != src.stat().st_size:
        shutil.copy2(src, out)
    return out.relative_to(sdir(slug)).as_posix()


def _lieu(dossier):
    try:
        return (json.loads((dossier / "meta.json").read_text(encoding="utf-8")).get("monteurIa") or {}).get("lieu")
    except (OSError, ValueError):
        return None


def copie_de_l_accueil(path):
    """Vrai si `path` est la copie qu'a faite l'app en recevant la vidéo dans l'accueil de Monteur IA."""
    try:
        rel = pathlib.Path(path).resolve().relative_to(ROOT.resolve())
    except ValueError:
        return False
    return len(rel.parts) > 1 and _lieu(ROOT / rel.parts[0]) == "accueil"


def _meta(slug):
    try:
        return json.loads((sdir(slug) / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"id": slug, "name": slug, "monteurIa": {"lieu": "story", "etat": "en-cours"}}


def _ecrire_meta(slug, meta):
    (sdir(slug) / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def projet(slug, etat=None):
    """Fait de stories/<slug>/ un projet de l'app (idempotent) ; etat = "publie" à la clôture."""
    d = sdir(slug)
    nouveau = not (d / "meta.json").exists()
    meta = _meta(slug)
    if etat:
        meta.setdefault("monteurIa", {"lieu": "story"})["etat"] = etat
    _ecrire_meta(slug, meta)
    if not (d / "hyperframes.json").exists() and (ROOT / "hyperframes.json").exists():
        shutil.copy2(ROOT / "hyperframes.json", d / "hyperframes.json")
    gsap, source = d / "assets" / "vendor" / "gsap.min.js", ROOT / "assets" / "vendor" / "gsap.min.js"
    if not gsap.exists() and source.exists():
        gsap.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, gsap)
    if nouveau:   # ses consignes (CLAUDE.md, AGENTS.md, bloc LIEU_STORY du Système Stories)
        subprocess.run(["node", "scripts/sync.mjs"], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")


def _empreinte(texte):
    """Empreinte d'une composition, insensible à ce que l'app réécrit sans rien changer à l'image
    (data-hf-id posés à l'ouverture, mise en forme du HTML, écriture des entités)."""
    t = re.sub(r'\s?data-hf-id="[^"]*"', "", HTML.unescape(texte))
    t = re.sub(r'\s(class|style)=""', "", t).replace('=""', "")
    t = re.sub(r"\s*/>", ">", t)
    return hashlib.sha256(re.sub(r"\s+", "", t).lower().encode("utf-8")).hexdigest()


def _pistes(elements, depart):
    """Une piste par élément qui en chevauche un autre ; sinon la même (lecture plus claire)."""
    fins, out = [], []
    for e in elements:
        for i, fin in enumerate(fins):
            if e["start"] >= fin - 1e-6:
                fins[i] = e["end"]
                out.append(depart + i)
                break
        else:
            fins.append(e["end"])
            out.append(depart + len(fins) - 1)
    return out, depart + max(len(fins), 1)


def _plan(slug, i, m, cut_dur):
    """Plan inséré pré-cadré en 1080x1920 dans assets/plans/ (le rendu ne voit que la story, et le
    cadrage reste déterministe) ; refait seulement quand sa source ou ses réglages changent."""
    src = pathlib.Path(_check_media(m, cut_dur))
    d = m["end"] - m["start"]
    cle = hashlib.sha1(f"{src.resolve()}|{src.stat().st_mtime}|{m.get('in', 0)}|{d:.3f}|{m.get('fit')}".encode()).hexdigest()[:8]
    dossier = sdir(slug) / "assets" / "plans"
    dossier.mkdir(parents=True, exist_ok=True)
    out = dossier / f"plan-{i}-{cle}.mp4"
    if not out.exists():
        for vieux in dossier.glob(f"plan-{i}-*.mp4"):
            vieux.unlink()
        if m.get("fit") == "blur":
            vf = (f"split=2[b][f];[b]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},gblur=sigma=40[bg];"
                  f"[f]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1")
        else:
            vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"
        r = run([FFMPEG, "-y", "-ss", str(m.get("in", 0)), "-t", f"{d:.3f}", "-i", str(src), "-an",
                 "-filter_complex", vf, "-r", FPS, "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                 "-g", "30", "-pix_fmt", "yuv420p", str(out)])
        if r.returncode:
            sys.exit(f"Plan {src.name} : préparation impossible\n{r.stderr[-1500:]}")
    return out.relative_to(sdir(slug)).as_posix()


def _bandeau(slug, o):
    """Bandeau (image ou vidéo) copié dans assets/bandeaux/ ; un MOV passe en WebM avec alpha (Chrome
    ne lit pas le ProRes). Rend (chemin dans la story, hauteur à la largeur voulue ou None)."""
    src = pathlib.Path(o["src"]) if str(o["src"]).startswith("/") else ROOT / o["src"]
    if not src.exists():
        sys.exit(f"Bandeau introuvable : {src}")
    w = o.get("w", 420)
    dossier = sdir(slug) / "assets" / "bandeaux"
    dossier.mkdir(parents=True, exist_ok=True)
    if src.suffix.lower() == ".mov":
        out = dossier / f"{src.stem}.webm"
        if not out.exists():
            r = run([FFMPEG, "-y", "-i", str(src), "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-an", str(out)])
            if r.returncode:
                sys.exit(f"Bandeau {src.name} : conversion impossible\n{r.stderr[-1500:]}")
    else:
        out = dossier / src.name
        if not out.exists() or out.stat().st_mtime < src.stat().st_mtime:
            shutil.copy2(src, out)
    h = None
    try:
        if out.suffix.lower() in IMAGES:
            from PIL import Image
            with Image.open(out) as im:
                h = round(w * im.height / im.width)
        elif out.suffix.lower() == ".svg":
            vb = re.search(r'viewBox="\s*[-\d.]+[\s,]+[-\d.]+[\s,]+([\d.]+)[\s,]+([\d.]+)', out.read_text(encoding="utf-8", errors="ignore"))
            h = round(w * float(vb.group(2)) / float(vb.group(1))) if vb else None
        elif out.suffix.lower() in (".webm", ".mp4"):
            dims = probe(out, "stream=width,height").split()
            h = round(w * int(dims[1]) / int(dims[0]))
    except (OSError, ValueError, IndexError):
        h = None
    return out.relative_to(sdir(slug)).as_posix(), h


def _skin_css(st, size):
    """Les 4 skins du /setup-stories, en CSS (mêmes réglages que story_text.render_caption)."""
    skin = st["captionsSkin"]
    if skin == "ombre":
        sh = st["shadow"]
        dx, dy = ST._shadow_offset(sh["distance"], sh["angle"])
        flou = 2 * sh["blur"] * ST.BLUR_FULL_SCALE        # CSS : rayon = 2 x écart-type de Pillow
        return f"text-shadow: {dx:.1f}px {dy:.1f}px {flou:.1f}px rgba(0, 0, 0, {sh['opacity']});"
    if skin == "contour":
        trait = max(2, size // 18)
        return f"-webkit-text-stroke: {2 * trait}px rgba(0, 0, 0, 0.9); paint-order: stroke fill;"
    if skin in ("plaque", "bloc"):
        r, g, b, _ = ST._hex(st["plateColor"])
        alpha = 0.67 if skin == "plaque" else 1
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        texte = "" if skin == "plaque" or lum <= 140 else " color: #101010;"
        rayon = int(size * 0.22) if skin == "plaque" else 0
        return (f"background: rgba({r}, {g}, {b}, {alpha}); padding: {int(size * 0.24)}px {int(size * 0.42)}px; "
                f"border-radius: {rayon}px;{texte}")
    sys.exit(f"Skin de sous-titre inconnu : « {skin} » (ombre | contour | plaque | bloc). Relance /setup-stories.")


def _polices(slug, st):
    """La police des sous-titres, copiée dans la story (le rendu ne voit que ce dossier)."""
    src = ST.font_path(st)
    dossier = sdir(slug) / "assets" / "fonts"
    dossier.mkdir(parents=True, exist_ok=True)
    if not (dossier / src.name).exists():
        shutil.copy2(src, dossier / src.name)
    fmt = {".ttf": "truetype", ".otf": "opentype", ".woff2": "woff2", ".woff": "woff"}.get(src.suffix.lower(), "truetype")
    return (f'      @font-face {{ font-family: "StoryCaption"; src: url("assets/fonts/{src.name}") format("{fmt}"); '
            f'font-display: block; }}\n')


def composer(slug, publiee=False, ecraser=False, auto=True):
    """index.html = la composition de la story (Monteur IA 2). Rend False si une retouche faite dans
    l'app a été gardée (rien d'écrit)."""
    if not APP:
        return True
    projet(slug)
    d = sdir(slug)
    page = d / "index.html"
    meta = _meta(slug)
    connue = (meta.get("monteurIa") or {}).get("composition")
    cfg = load(slug)
    retouchee = page.exists() and connue and not publiee and _empreinte(page.read_text(encoding="utf-8")) != connue
    if retouchee and not ecraser:
        if not _base_path(slug).exists():
            # Story composée par une version antérieure : l'état d'origine n'est pas connu.
            msg = ("index.html a été retouché dans l'app et son état d'origine n'est pas connu : composition NON "
                   f"réécrite. Reporte la retouche dans story.json, puis `story.py compose {slug} --ecraser`.")
            if auto:
                print("⚠️  " + msg)
                return False
            sys.exit(msg)
        notes = adopter(slug, cfg, page)
        print("Retouches de l'app reportées dans story.json :" + "".join(f"\n  · {n}" for n in notes) if notes
              else "Retouche de l'app sans équivalent dans story.json (rien à reporter).")
    cut = d / "cut.mp4"
    st = story_style()
    corps, etat = [], "vignette d'attente"
    if publiee or not cut.exists():
        dur = 5
        texte = ("Story publiée : sa vidéo est dans Vidéos/stories-publiees." if publiee
                 else "Story en préparation : la composition arrive après le cut." if cfg.get("rush")
                 else "Script de la story en cours : la vidéo arrive au tournage.")
        corps = [f'      <h1 id="titre" class="ligne clip" data-start="0" data-duration="5" data-track-index="0">{HTML.escape(slug)}</h1>',
                 f'      <p id="etat" class="ligne clip" data-start="0" data-duration="5" data-track-index="1" style="top: 980px">{texte}</p>']
        etat = "publiée" if publiee else etat
    else:
        dur = round(float(probe(cut)), 3)
        corps = [f'      <video id="visage" class="plein clip" src="cut.mp4" muted playsinline data-start="0" data-duration="{dur}" data-track-index="0"></video>',
                 f'      <audio id="voix" src="cut.mp4" data-start="0" data-duration="{dur}" data-track-index="1"></audio>']
        medias = sorted(cfg.get("media", []), key=lambda m: m["start"])
        pistes, suite = _pistes(medias, 2)
        for i, (m, piste) in enumerate(zip(medias, pistes)):
            src = _plan(slug, i, m, dur)
            corps.append(f'      <video id="plan-{i}" class="plein clip" src="{src}" muted playsinline data-start="{m["start"]:.3f}" '
                         f'data-duration="{m["end"] - m["start"]:.3f}" data-track-index="{piste}"></video>')
        bandeaux = sorted(cfg.get("overlays", []), key=lambda o: o["start"])
        pistes, suite = _pistes(bandeaux, suite)
        for i, (o, piste) in enumerate(zip(bandeaux, pistes)):
            src, h = _bandeau(slug, o)
            w, y = o.get("w", 420), o.get("y", 300)
            temps = f'data-start="{o["start"]:.3f}" data-duration="{o["end"] - o["start"]:.3f}" data-track-index="{piste}"'
            if src.endswith((".webm", ".mp4")):
                corps.append(f'      <video id="bandeau-{i}" class="clip" src="{src}" muted playsinline {temps} '
                             f'style="position: absolute; left: {(W - w) // 2}px; top: {y - (h or 0) // 2}px; width: {w}px"></video>')
            elif h:
                corps.append(f'      <img id="bandeau-{i}" class="clip" src="{src}" alt="" {temps} '
                             f'style="position: absolute; left: {(W - w) // 2}px; top: {y - h // 2}px; width: {w}px">')
            else:   # hauteur illisible : cadre de la largeur voulue, carré, image centrée dedans
                corps.append(f'      <div id="bandeau-{i}" class="repere clip" {temps} style="left: {(W - w) // 2}px; '
                             f'top: {y - w // 2}px; width: {w}px; height: {w}px"><img src="{src}" alt="" style="width: {w}px"></div>')
        # Un sous-titre déplacé dans l'app peut en chevaucher un autre : chacun garde alors sa piste.
        # "x" = centre horizontal (défaut : le centre du cadre), "y" = centre vertical.
        legendes = cfg.get("captions", [])
        pistes, suite = _pistes(legendes, suite)
        for i, (c, piste) in enumerate(zip(legendes, pistes)):
            txt = c["t"].upper() if cfg.get("caption_case", st.get("captionCase")) == "upper" else c["t"]
            size, y = c.get("size", cfg["caption_size"]), c.get("y", cfg["caption_y"])
            decale = f"; translate: {c['x'] - W / 2:.1f}px 0px" if "x" in c else ""
            corps.append(f'      <div id="st-{i}" class="repere sous-titre clip" data-start="{c["start"]:.3f}" '
                         f'data-duration="{c["end"] - c["start"]:.3f}" data-track-index="{piste}" '
                         f'style="top: {y - size}px; height: {2 * size}px; font-size: {size}px{decale}">'
                         f'<span>{HTML.escape(txt, quote=False)}</span></div>')
        mu = cfg.get("music")
        if mu:
            corps.append(f'      <audio id="musique" src="{_musique(slug, mu)}" data-start="0" data-duration="{dur}" '
                         f'data-media-start="{mu.get("in", 0)}" data-volume="{mu.get("volume", 0.07)}" data-track-index="{suite}"></audio>')
        etat = (f"{len(medias)} plan(s), {len(bandeaux)} bandeau(x), {len(cfg.get('captions', []))} sous-titres"
                + (", musique" if mu else ""))
    taille = cfg.get("caption_size", st["captionSize"])
    contenu = COMPOSITION.format(slug=slug, cid=f"story-{slug}", dur=dur, etat=etat, corps="\n".join(corps),
                                 polices=_polices(slug, st), couleur=st["captionColor"], skin=_skin_css(st, taille))
    page.write_text(contenu, encoding="utf-8")
    if not (publiee or not cut.exists()):
        _noter_base(slug, contenu, cfg, medias, bandeaux)
    meta = _meta(slug)
    meta.setdefault("monteurIa", {"lieu": "story"})["composition"] = _empreinte(contenu)
    _ecrire_meta(slug, meta)
    trop = trop_larges(cfg, st)
    if trop and not publiee:
        print("⚠️  Sous-titre(s) trop large(s) (> 880 px), à re-couper avant l'export : " + " | ".join(trop))
    return True


def trop_larges(cfg, st=None):
    """Sous-titres qui ne tiennent pas sur une ligne : l'app les montre (à re-couper), l'export les refuse."""
    st = st or story_style()
    out = []
    for c in cfg.get("captions", []):
        txt = c["t"].upper() if cfg.get("caption_case", st.get("captionCase")) == "upper" else c["t"]
        larg = ST.measure(txt, c.get("size", cfg["caption_size"]), st)[0]
        x = c.get("x", W / 2)
        if larg > ST.MAX_TEXT_W:
            out.append(txt)
        elif x - larg / 2 < ST.SAFE_X or x + larg / 2 > W - ST.SAFE_X:
            out.append(f"{txt} (x={x} : sort de la marge de {ST.SAFE_X} px)")
    return out


def ouvrir(slug):
    r = subprocess.run(["node", "scripts/app-hyperframes.mjs", "ouvrir", str(sdir(slug))], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("-> " + ((r.stdout or r.stderr).strip() or "ouverte dans l'app HyperFrames"))


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", **kw)


def probe(path, entries="format=duration"):
    r = run([FFPROBE, "-v", "error", "-show_entries", entries,
             "-of", "default=nw=1:nk=1", str(path)])
    return r.stdout.strip()


def takes_of(cfg):
    """Bornes THÉORIQUES des prises dans le cut (cumul des îlots padés).

    Pas de scene-detect ici (contrairement aux Reels) : rien n'ouvre de fenêtre visage sur une
    frontière, donc les ~0.07 s d'arrondi frame du concat sont sans conséquence. Les slices
    Whisper prennent une marge.
    """
    out, t = [], 0.0
    for i, isl in enumerate(cfg["islands"]):
        d = (isl[1] + cfg["pad_end"]) - max(isl[0] - cfg["pad_start"], 0.0)
        out.append({"i": i, "start": round(t, 3), "end": round(t + d, 3), "text": isl[2]})
        t += d
    return out


# ------------------------------------------------------------------------- init
def cmd_init(a):
    """Crée la story. Dans l'app, un script se brainstorme dans le projet de la story : `--brief` sans
    vidéo crée le projet tout de suite ; la vidéo s'ajoute au tournage, par le même `init --rush`."""
    d = sdir(a.slug)
    existante = (d / "story.json").exists()
    if existante and load(a.slug).get("rush"):
        sys.exit(f"La story « {a.slug} » a déjà sa vidéo. Choisis un autre slug pour une nouvelle story.")
    if not a.rush and not a.brief:
        sys.exit("Donne la vidéo (--rush) ou, pour écrire le script d'abord, la demande (--brief).")
    d.mkdir(parents=True, exist_ok=True)
    if a.brief and a.brief.strip():
        brief = d / "brief.md"
        debut = brief.read_text(encoding="utf-8") if brief.exists() else "# Brief\n\n"
        brief.write_text(debut + f"Demande du client :\n\n{a.brief.strip()}\n\n", encoding="utf-8")
        print(f"Demande notée dans stories/{a.slug}/brief.md (lue en début de conversation de la story)")
    rush = None
    if a.rush:
        rush = pathlib.Path(a.rush).expanduser().resolve()
        if not rush.exists():
            sys.exit(f"Rush introuvable : {rush}")
        if copie_de_l_accueil(rush):
            # Copie faite par l'app dans l'accueil : elle part dans la story (effacée à la clôture).
            cible = d / f"rush{rush.suffix}"
            shutil.move(str(rush), str(cible))
            rush = cible
            print(f"Vidéo glissée dans l'accueil -> rangée dans la story : {cible}")
        info = probe(rush, "stream=index,codec_type,codec_name,width,height,color_transfer")
        print(f"Rush : {rush}\nDurée : {probe(rush)} s\n{info}")
        if "color_transfer=arib-std-b67" in info or "color_transfer=smpte2084" in info:
            print("⚠️  Rush en HDR : le rendu SDR délavera les couleurs. Filmer en SDR, ou "
                  "transcoder d'abord (voir skill story, section pièges).")
    if existante:   # story créée pour son script : la vidéo arrive, le reste est gardé
        cfg = json.loads((d / "story.json").read_text(encoding="utf-8"))
        cfg["rush"] = str(rush) if rush else cfg.get("rush")
    else:
        cfg = {"slug": a.slug, "rush": str(rush) if rush else None, **DEFAULTS,
               "islands": [], "captions": [], "media": [], "overlays": []}
    save(a.slug, cfg)
    composer(a.slug)
    if rush:
        print(f"\n-> {d/'story.json'}  (remplir `islands` après `story.py silences {a.slug}`)")
    else:
        print(f"\n-> stories/{a.slug}/ : pas encore de vidéo, on commence par le script (skill story-script) ; "
              f"une fois tournée : story.py init {a.slug} --rush <vidéo>")
    if APP:
        print(f"-> projet de l'app HyperFrames : stories/{a.slug}/ (une conversation neuve pour cette story)")
        if a.ouvrir:
            ouvrir(a.slug)


def rush_de(cfg):
    if not cfg.get("rush"):
        sys.exit(f"Pas encore de vidéo pour « {cfg['slug']} » : une fois tournée, "
                 f"story.py init {cfg['slug']} --rush <vidéo> (le script et les réglages sont gardés).")
    return cfg["rush"]


# --------------------------------------------------------------------- silences
def cmd_silences(a):
    cfg = load(a.slug)
    src = rush_de(cfg)
    model = whisper_model()
    with tempfile.TemporaryDirectory() as tmp:
        wav = pathlib.Path(tmp) / "a.wav"
        run([FFMPEG, "-y", "-i", src, "-vn", "-ar", "16000", "-ac", "1", str(wav)])
        # ⚠️ JAMAIS -v error ici : silencedetect logue en *info*.
        r = run([FFMPEG, "-i", str(wav), "-af",
                 f"silencedetect=noise={a.noise}dB:d={a.d}", "-f", "null", "-"])
        log = r.stderr
        starts = [float(m) for m in re.findall(r"silence_start: ([\d.]+)", log)]
        ends = [float(m) for m in re.findall(r"silence_end: ([\d.]+)", log)]
        dur = float(probe(src))

        # îlots de parole = complément des silences
        bounds, cur = [], 0.0
        for i, s in enumerate(starts):
            e = ends[i] if i < len(ends) else dur
            if s - cur > 0.25:
                bounds.append((cur, s))
            cur = e
        if dur - cur > 0.25:
            bounds.append((cur, dur))

        print(f"{len(bounds)} îlots ({a.noise} dB, d={a.d}) — à recroiser AVANT de remplir `islands`\n")
        for i, (s, e) in enumerate(bounds):
            txt = ""
            if not a.no_text:
                sl = pathlib.Path(tmp) / f"i{i}.wav"
                run([FFMPEG, "-v", "error", "-y", "-ss", str(s), "-to", str(e), "-i", str(wav),
                     "-ar", "16000", "-ac", "1", str(sl)])
                p = run([WHISPER, "-m", model, "-l", _lang(), "-nt", "-np", str(sl)])
                txt = " ".join(p.stdout.split())
            print(f"  [{i:2d}]  ({s:7.2f}, {e:7.2f}, {(e-s):5.2f}s)  {txt}")


def _lang():
    cfg = _brand_config()
    return ((cfg.get("derush") or {}).get("whisperLanguage")
            or (cfg.get("brand") or {}).get("language") or "fr")


# ---------------------------------------------------------------------- cut
def cmd_cut(a):
    cfg = load(a.slug)
    if not cfg["islands"]:
        sys.exit("`islands` est vide : remplis-le depuis la sortie de `story.py silences`.")
    out = sdir(a.slug) / "cut.mp4"
    # Cadrage du visage (story.faceZoom) appliqué ici, sur le rush, plus grand que 1080x1920 :
    # le cut reste net. À 1.0 : le cadre tel quel, centré.
    zoom = max(float(cfg.get("face_zoom") or 1.0), 1.0)
    zw, zh = round(W * zoom / 2) * 2, round(H * zoom / 2) * 2
    ancre = min(max(float(cfg.get("face_zoom_y", 0.38)), 0.0), 1.0) if zoom > 1 else 0.5   # 1.0 : centré, comme avant
    parts, cin, kept = [], "", 0.0
    for i, isl in enumerate(cfg["islands"]):
        s = max(isl[0] - cfg["pad_start"], 0.0)
        e = isl[1] + cfg["pad_end"]
        kept += e - s
        parts.append(f"[0:v:0]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS,"
                     f"scale={zw}:{zh}:force_original_aspect_ratio=increase,"
                     f"crop={W}:{H}:(iw-{W})/2:(ih-{H})*{ancre}[v{i}];")
        parts.append(f"[0:a:0]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}];")
        cin += f"[v{i}][a{i}]"
    fg = "".join(parts) + f"{cin}concat=n={len(cfg['islands'])}:v=1:a=1[v][a]"
    print(f"Prises : {len(cfg['islands'])} | durée estimée : {kept:.2f} s" + (f" | visage x{zoom:g}" if zoom > 1 else ""))
    r = run([FFMPEG, "-y", "-i", rush_de(cfg), "-filter_complex", fg,
             "-map", "[v]", "-map", "[a]", "-r", FPS,
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", str(out)])
    if r.returncode:
        sys.exit(r.stderr[-1800:])
    print(f"-> {out}  ({probe(out)} s)")
    composer(a.slug)


# --------------------------------------------------------------------- words
WLINE = re.compile(r"\[(\d+):(\d+):([\d.]+) --> (\d+):(\d+):([\d.]+)\]\s*(.*)")


def _secs(h, m, s):
    return int(h) * 3600 + int(m) * 60 + float(s)


def cmd_words(a):
    """Transcription MOT-À-MOT, PRISE PAR PRISE (sur le fichier entier ce mode hallucine)."""
    cfg = load(a.slug)
    cut = sdir(a.slug) / "cut.mp4"
    if not cut.exists():
        sys.exit("cut.mp4 manquant : lance `story.py cut` d'abord.")
    model = whisper_model()
    words = []
    with tempfile.TemporaryDirectory() as tmp:
        for tk in takes_of(cfg):
            wav = pathlib.Path(tmp) / f"t{tk['i']:02d}.wav"
            run([FFMPEG, "-v", "error", "-y", "-ss", str(max(tk["start"] - 0.1, 0)),
                 "-to", str(tk["end"] + 0.1), "-i", str(cut),
                 "-ar", "16000", "-ac", "1", str(wav)], check=False)
            p = run([WHISPER, "-m", model, "-l", _lang(),
                     "-ml", "1", "-sow", "-wt", "0.01", "-np", str(wav)])
            base = max(tk["start"] - 0.1, 0)
            for line in p.stdout.split("\n"):
                m = WLINE.match(line.strip())
                if not m or not m.group(7).strip():
                    continue
                words.append({"w": m.group(7).strip(),
                              "start": round(base + _secs(*m.group(1, 2, 3)), 3),
                              "end": round(base + _secs(*m.group(4, 5, 6)), 3),
                              "take": tk["i"]})
    p = sdir(a.slug) / "words.json"
    p.write_text(json.dumps(words, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(words)} mots -> {p}")


# ------------------------------------------------------------------- captions
WEAK = set("""le la les l' un une des du de d' au aux à a et ou mais donc car que qu' qui dont où
si ce cet cette ces mon ma mes ton ta tes son sa ses notre nos votre vos leur leurs en dans sur
avec pour par sans sous entre vers chez je j' tu il elle on nous vous ils elles n' c' s' t' m'
deux trois quatre cinq six sept huit neuf dix cent mille""".split())
BREAK = set("""et mais ou donc car puis ensuite alors comme qui que qu' dont où quand si parce
à au aux dans sur avec pour par en vers chez sans sous entre il elle on ils elles ça ce je tu
nous vous voire certains""".split())


def _norm(s):
    return re.sub(r"[^a-z0-9àâäéèêëîïôöùûüç ]", "", s.lower()).strip()


def chunk(text, size):
    """1er jet de découpe (2-3 mots). Le découpage FINAL se décide par unité grammaticale
    (skill story §3.2) : ce jet est légal en largeur mais SANS conscience grammaticale."""
    out = []
    for phrase in re.split(r"(?<=[.!?])\s+", text.strip()):
        toks = [t for t in phrase.split() if t]
        cur = []
        for i, t in enumerate(toks):
            cur.append(t)
            nxt = toks[i + 1] if i + 1 < len(toks) else None
            disp = " ".join(cur).rstrip(".,;:!?")
            too_wide = ST.measure(disp, size)[0] > ST.MAX_TEXT_W
            weak_end = _norm(cur[-1]) in WEAK
            good = len(cur) >= 2 and nxt and (_norm(nxt) in BREAK or cur[-1].endswith(","))
            if too_wide and len(cur) > 1:
                out.append(" ".join(cur[:-1]).rstrip(".,;:!?"))
                cur = [t]
            elif (good or len(cur) >= 3) and not weak_end and nxt:
                out.append(disp)
                cur = []
        if cur:
            out.append(" ".join(cur).rstrip(".,;:!?"))
    return [c for c in out if c]


def cmd_captions(a):
    cfg = load(a.slug)
    wp = sdir(a.slug) / "words.json"
    if not wp.exists():
        sys.exit("words.json manquant : lance `story.py words` d'abord.")
    words = json.loads(wp.read_text(encoding="utf-8"))
    takes = takes_of(cfg)
    caps = []
    for tk in takes:
        tw = [w for w in words if w["take"] == tk["i"]]
        if not tw:
            continue
        # `chunks` dans story.json = le découpage DICTÉ (validé par le créateur) : une liste de
        # sous-titres par prise. Sinon, 1er jet automatique.
        manual = cfg.get("chunks")
        chunks = manual[tk["i"]] if manual else chunk(tk["text"], cfg["caption_size"])
        if not chunks:
            continue   # prise volontairement SANS sous-titre (ex. recouverte par un plan)
        seq = [_norm(w["w"]) for w in tw]
        pos = 0
        for c in chunks:
            need = _norm(c).split()
            # alignement tolérant (variantes « 4 »/« quatre », élisions…)
            best, bi = 0.0, pos
            for j in range(pos, max(pos + 1, len(seq) - len(need) + 1)):
                cand = " ".join(seq[j:j + len(need)])
                r = difflib.SequenceMatcher(None, cand, " ".join(need)).ratio()
                if r > best:
                    best, bi = r, j
            start = tw[bi]["start"] if bi < len(tw) else tk["start"]
            end_i = min(bi + len(need), len(tw)) - 1
            end = tw[max(end_i, bi)]["end"]
            pos = min(bi + len(need), len(seq))
            caps.append({"t": c, "start": round(start, 3), "end": round(end, 3), "take": tk["i"]})
        # snap aux DEUX bords de la prise
        first = next(i for i, x in enumerate(caps) if x["take"] == tk["i"])
        caps[first]["start"] = tk["start"]
        caps[-1]["end"] = tk["end"]
    # timing continu : chaque sous-titre tient jusqu'au suivant (dans la même prise)
    for i in range(len(caps) - 1):
        if caps[i + 1]["take"] == caps[i]["take"]:
            caps[i]["end"] = caps[i + 1]["start"]
    cfg["captions"] = [{k: c[k] for k in ("t", "start", "end")} for c in caps]
    save(a.slug, cfg)
    print(f"{len(caps)} sous-titres -> stories/{a.slug}/story.json (clé `captions`)")
    print("⚠️  1er jet SANS conscience grammaticale : re-couper par unité avant de livrer.\n")
    composer(a.slug)
    for c in caps:
        print(f"  {c['start']:6.2f} -> {c['end']:6.2f}  {c['t']}")


# -------------------------------------------------------------------- preview
def cmd_preview(a):
    cfg = load(a.slug)
    cut = sdir(a.slug) / "cut.mp4"
    txt = a.text
    if txt is None:
        act = [c for c in cfg["captions"] if c["start"] <= a.t <= c["end"]]
        txt = act[0]["t"] if act else "sous-titre de test"
    if cfg["caption_case"] == "upper":
        txt = txt.upper()
    out = sdir(a.slug) / f"preview_{a.t:.1f}s.png".replace(".", "_", 1)
    with tempfile.TemporaryDirectory() as tmp:
        frame = pathlib.Path(tmp) / "f.png"
        cap = pathlib.Path(tmp) / "c.png"
        run([FFMPEG, "-v", "error", "-y", "-ss", str(a.t), "-i", str(cut),
             "-frames:v", "1", str(frame)], check=False)
        ST.caption_png(txt, cap, size=cfg["caption_size"], y=cfg["caption_y"])
        run([FFMPEG, "-v", "error", "-y", "-i", str(frame), "-i", str(cap),
             "-filter_complex", "[0:v][1:v]overlay=0:0", "-frames:v", "1", str(out)])
    print(f"-> {out}")


# --------------------------------------------------------------------- render
def _check_media(m, cut_dur):
    """Vérifie le média AVANT le filtergraph : un -ss/-t hors durée produit un MP4 sans flux
    vidéo et une erreur ffmpeg incompréhensible. Autant échouer ici, avec un message clair."""
    src = pathlib.Path(m["src"]) if str(m["src"]).startswith("/") else ROOT / m["src"]
    if not src.exists():
        sys.exit(f"Média introuvable : {src}")
    if m["end"] <= m["start"]:
        sys.exit(f"Média {src.name} : end ({m['end']}) doit être > start ({m['start']}).")
    if m["end"] > cut_dur + 0.05:
        sys.exit(f"Média {src.name} : end ({m['end']} s) dépasse la durée du cut ({cut_dur:.2f} s).")
    d = probe(src)
    if d:
        need = m.get("in", 0) + (m["end"] - m["start"])
        if need > float(d) + 0.05:
            sys.exit(f"Média {src.name} : il faut {need:.2f} s à partir de in={m.get('in', 0)} s, "
                     f"mais le fichier ne dure que {float(d):.2f} s.")
    return str(src)


def cmd_compose(a):
    load(a.slug)
    if not APP:
        sys.exit("`compose` sert l'app HyperFrames (Monteur IA 2) ; ici, `render` monte en ffmpeg.")
    composer(a.slug, ecraser=a.ecraser, auto=False)
    print(f"-> stories/{a.slug}/index.html : composition à jour (ouvre la story dans l'app pour la voir)")


def rendu_natif(a):
    """Monteur IA 2 : la story s'exporte comme un Reel, depuis sa composition (retouches de l'app
    comprises). Même résultat que le bouton Export de l'app."""
    cfg = load(a.slug)
    d = sdir(a.slug)
    if not (d / "cut.mp4").exists():
        sys.exit("cut.mp4 manquant : lance `story.py cut` d'abord.")
    trop = trop_larges(cfg)
    if trop:
        sys.exit("Sous-titre(s) trop large(s), à re-couper avant l'export (toujours une seule ligne) : " + " | ".join(trop))
    composer(a.slug)
    out = d / f"story_{cfg['slug']}_FINAL.mp4"
    r = subprocess.run(["npx", "--yes", "hyperframes", "render", "-o", str(out)], cwd=d, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", shell=sys.platform == "win32")
    if r.returncode or not out.exists():
        sys.exit("Rendu HyperFrames impossible :\n" + (r.stdout + r.stderr)[-2500:])
    dl = pathlib.Path.home() / "Downloads" / out.name
    try:
        shutil.copy2(out, dl)
    except OSError:
        dl = None
    print(f"-> {out}  ({probe(out)} s)" + (f"\n-> {dl}" if dl else ""))


def cmd_render(a):
    if APP:
        return rendu_natif(a)
    cfg = load(a.slug)
    cut = sdir(a.slug) / "cut.mp4"
    if not cut.exists():
        sys.exit("cut.mp4 manquant.")
    cut_dur = float(probe(cut) or 0)
    tmpd = sdir(a.slug) / "_caps"
    tmpd.mkdir(exist_ok=True)

    inputs, fg, last, n = ["-i", str(cut)], [], "[0:v]", 1

    # 1. plans plein écran fournis par le créateur (le son reste celui du cut)
    for m in cfg.get("media", []):
        src = _check_media(m, cut_dur)
        inputs += ["-i", src]
        d = m["end"] - m["start"]
        if m.get("fit") == "blur":
            # média qui ne remplit pas le cadre : on le pose net sur son propre fond flouté
            fg.append(f"[{n}:v]trim=start={m.get('in',0)}:duration={d:.3f},setpts=PTS-STARTPTS+"
                      f"{m['start']:.3f}/TB,split=2[mb{n}][mf{n}];"
                      f"[mb{n}]scale={W}:{H}:force_original_aspect_ratio=increase,"
                      f"crop={W}:{H},gblur=sigma=40[bg{n}];"
                      f"[mf{n}]scale={W}:{H}:force_original_aspect_ratio=decrease[fgm{n}];"
                      f"[bg{n}][fgm{n}]overlay=(W-w)/2:(H-h)/2,setsar=1[m{n}];")
        else:
            fg.append(f"[{n}:v]trim=start={m.get('in',0)}:duration={d:.3f},setpts=PTS-STARTPTS+"
                      f"{m['start']:.3f}/TB,scale={W}:{H}:force_original_aspect_ratio=increase,"
                      f"crop={W}:{H},setsar=1[m{n}];")
        fg.append(f"{last}[m{n}]overlay=0:0:enable='between(t,{m['start']:.3f},{m['end']:.3f})'[s{n}];")
        last, n = f"[s{n}]", n + 1

    # 2. bandeaux motion (PNG ou MOV alpha), posés en haut ou en bas
    for o in cfg.get("overlays", []):
        src = o["src"] if str(o["src"]).startswith("/") else str(ROOT / o["src"])
        if src.lower().endswith(".svg"):
            sys.exit(f"SVG non rasterisé : {src} — exporter en PNG avant le render.")
        inputs += ["-i", src]
        w = o.get("w", 420)
        # image fixe -> `overlay` répète sa dernière frame (eof_action=repeat) : ne JAMAIS
        # ajouter loop=-1, le filtergraph ne termine alors plus (2 min de blocage observées).
        if src.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            fg.append(f"[{n}:v]scale={w}:-1,format=rgba[o{n}];")
        else:
            fg.append(f"[{n}:v]scale={w}:-1,format=rgba,setpts=PTS-STARTPTS+"
                      f"{o['start']:.3f}/TB[o{n}];")
        fg.append(f"{last}[o{n}]overlay=(W-w)/2:{o.get('y',300)}-h/2:"
                  f"enable='between(t,{o['start']:.3f},{o['end']:.3f})'[s{n}];")
        last, n = f"[s{n}]", n + 1

    # 3. sous-titres, TOUJOURS au-dessus (la voix continue sous un plan plein écran)
    st = story_style()
    for i, c in enumerate(cfg.get("captions", [])):
        txt = c["t"].upper() if cfg["caption_case"] == "upper" else c["t"]
        size = c.get("size", cfg["caption_size"])
        if ST.measure(txt, size)[0] > ST.MAX_TEXT_W:
            sys.exit(f"Sous-titre trop large : « {txt} » — re-couper.")
        img, ax, ay = ST.render_caption(txt, size=size, story=st)
        p = tmpd / f"cap{i:03d}.png"
        img.save(p)
        inputs += ["-i", str(p)]
        y = c.get("y", cfg["caption_y"])
        # ancre = centre du glyphe (le PNG porte les marges du skin) ; "x" = centre horizontal voulu
        px = f"{c['x']:.1f}-{ax:.1f}" if "x" in c else f"(W-w)/2+{(img.width / 2 - ax):.1f}"
        fg.append(f"[{n}:v]format=rgba[c{n}];")
        fg.append(f"{last}[c{n}]overlay={px}:{y}-{ay:.1f}:"
                  f"enable='between(t,{c['start']:.3f},{c['end']:.3f})'[s{n}];")
        last, n = f"[s{n}]", n + 1

    # ⚠️ Le master reste dans le dossier isolé de la story (jamais dans renders/, que le
    # pipeline Reel purge à la clôture d'un montage).
    out = sdir(a.slug) / f"story_{cfg['slug']}_FINAL.mp4"
    chain = "".join(fg)
    if chain.endswith(";"):
        chain = chain[:-1]
    # 4. musique de fond (brand.config story.music, ou music de story.json), sous la voix
    son = "0:a"
    mu = cfg.get("music")
    if mu:
        src = _chemin(mu["src"])
        if not src.exists():
            sys.exit(f"Musique introuvable : {src}")
        inputs += ["-ss", str(mu.get("in", 0)), "-i", str(src)]
        chain = (chain + ";" if chain else "") + (f"[{n}:a]volume={mu.get('volume', 0.07)}[mu];"
                                                  f"[0:a][mu]amix=inputs=2:duration=first:normalize=0[son]")
        son = "[son]"
    cmd = [FFMPEG, "-y"] + inputs
    if chain:
        cmd += ["-filter_complex", chain, "-map", last if fg else "0:v", "-map", son]
    else:
        cmd += ["-map", "0:v", "-map", "0:a"]
    cmd += ["-r", FPS, "-c:v", "libx264", "-preset", "slow", "-crf", "16",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(out)]
    print(f"{len(cfg.get('media',[]))} plan(s) · {len(cfg.get('overlays',[]))} bandeau(x) · "
          f"{len(cfg.get('captions',[]))} sous-titres · skin {st['captionsSkin']}" + (" · musique" if mu else ""))
    r = run(cmd)
    if r.returncode:
        sys.exit(r.stderr[-2500:])
    dl = pathlib.Path.home() / "Downloads" / out.name
    try:
        dl.write_bytes(out.read_bytes())
    except OSError:
        dl = None
    print(f"-> {out}  ({probe(out)} s)" + (f"\n-> {dl}" if dl else ""))


# ---------------------------------------------------------------------- close
def cmd_close(a):
    """Story postée : on archive le master et on jette le plan de travail (~200 Mo/story).

    Ce qui doit survivre à une story, c'est la MÉTHODE (les skills), pas le montage : une story
    vit 24 h. Le master est archivé dans ~/Movies/stories-publiees/ sauf --no-archive.
    """
    d = sdir(a.slug)
    if not d.exists():
        sys.exit(f"Aucune story « {a.slug} ».")
    master = next(iter(sorted(d.glob("story_*_FINAL.mp4"))), None)
    if not master and (d / "renders").is_dir():   # export fait avec le bouton Export de l'app
        master = max((p for p in (d / "renders").glob("*.mp4")), key=lambda p: p.stat().st_mtime, default=None)
    if master and not a.no_archive:
        arch = pathlib.Path.home() / "Movies" / "stories-publiees" / a.slug
        arch.mkdir(parents=True, exist_ok=True)
        (arch / master.name).write_bytes(master.read_bytes())
        print(f"master archivé -> {arch / master.name}")
    elif not master:
        print("aucun master trouvé (rien à archiver)")
    if not APP:
        size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
        shutil.rmtree(d)
        print(f"stories/{a.slug}/ supprimé ({size/1e6:.0f} Mo libérés)")
        return
    # Monteur IA 2 : le projet de l'app reste (story.json + vignette « publiée »), seuls les médias partent.
    # Les dossiers de l'app (exports, caches, réglages) ne se touchent jamais : renders/ garde l'export du créateur.
    rush = pathlib.Path(load(a.slug).get("rush") or "")
    garder = {"story.json", "meta.json", "hyperframes.json", "CLAUDE.md", "AGENTS.md", ".hyperframes", ".thumbnails",
              "renders", ".transcode-cache", ".waveform-cache", ".claude"}
    size = 0
    for p in d.iterdir():
        if p.name in garder:
            continue
        size += p.stat().st_size if p.is_file() else sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        p.unlink() if p.is_file() or p.is_symlink() else shutil.rmtree(p)
    if str(rush) and copie_de_l_accueil(rush) and rush.is_file():
        size += rush.stat().st_size
        rush.unlink()
        print(f"copie de la vidéo laissée dans l'accueil effacée : {rush.name}")
    projet(a.slug, etat="publie")
    composer(a.slug, publiee=True)
    print(f"stories/{a.slug}/ vidé ({size/1e6:.0f} Mo libérés) ; son projet reste dans l'app, marqué publié "
          "(l'archiver dans l'app pour le retirer de la liste)")


# ---------------------------------------------------------------------- b-roll
# La banque de B-rolls du créateur : assets/b-roll/ du dossier Monteur IA, décrite dans catalog.json.
# L'IA y CHOISIT un plan sur sa description (jamais en ouvrant les vidéos), puis le déclare dans
# `media` ("src": "assets/b-roll/<fichier>"). Un plan fourni pour une story y est versé d'abord,
# pour être retrouvé la fois suivante. Réglage : brand.config.json -> story.broll (true | false | null).
BROLL = ROOT / "assets" / "b-roll"
CATALOGUE = BROLL / "catalog.json"


def _catalogue():
    try:
        data = json.loads(CATALOGUE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def _slug(texte):
    import unicodedata
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", t)).strip("-")


def _date_de(src):
    """Date de tournage (métadonnées), sinon aujourd'hui."""
    import datetime
    for tag in ("format_tags=com.apple.quicktime.creationdate", "format_tags=creation_time"):
        v = probe(src, tag)
        if re.match(r"\d{4}-\d{2}-\d{2}", v or ""):
            return v[:10]
    return datetime.date.today().isoformat()


def _hdr(src):
    info = probe(src, "stream=color_transfer")
    return "arib-std-b67" in info or "smpte2084" in info


def cmd_broll(a):
    if a.action == "list":
        clips = _catalogue()
        if not clips:
            print(f"Banque vide : {BROLL}/ (story.py broll add <vidéo> --description \"…\")")
            return
        for c in clips:
            if a.categorie and c.get("categorie") != a.categorie:
                continue
            qui = " · créateur visible" if c.get("visible") else ""
            print(f"- {c['file']} · {c.get('duree', 0):.1f} s · [{c.get('categorie', '?')}]{qui} · {c.get('description', '')}")
        print(f"\n{len(clips)} plan(s) dans {BROLL}/ ; dans story.json : \"src\": \"assets/b-roll/<fichier>\"")
        return
    if not a.source:
        sys.exit("Donne la vidéo : story.py broll apercu <vidéo> | add <vidéo> --description \"…\"")
    src = pathlib.Path(a.source).expanduser().resolve()
    if not src.exists():
        sys.exit(f"Vidéo introuvable : {src}")
    duree = float(probe(src) or 0)
    if a.action == "apercu":
        # Planche de 3 images (début, milieu, fin) : l'IA la regarde pour écrire la description.
        BROLL.mkdir(parents=True, exist_ok=True)
        out = BROLL / ".apercus" / f"{_slug(src.stem)}.jpg"
        out.parent.mkdir(parents=True, exist_ok=True)
        n = max(int(duree * 30), 3)
        pas = max(n // 3, 1)
        r = run([FFMPEG, "-v", "error", "-y", "-i", str(src), "-vf",
                 f"select='not(mod(n\\,{pas}))',scale=360:-2,tile=3x1", "-frames:v", "1", str(out)])
        if r.returncode or not out.exists():
            sys.exit(f"Aperçu impossible :\n{r.stderr[-800:]}")
        dims = probe(src, "stream=width,height").split()
        print(f"{src.name} : {duree:.1f} s, {'x'.join(dims[:2])}{' (HDR)' if _hdr(src) else ''}, tournée le {_date_de(src)}")
        print(f"-> {out}  (regarde cette planche, puis : story.py broll add \"{src}\" --description \"…\")")
        return
    # add
    if not (a.description or "").strip():
        sys.exit("Il faut --description \"<ce qu'on voit, en une phrase>\" (c'est sur elle que le plan sera choisi).")
    nom = _slug(a.nom) if a.nom else f"{_date_de(src)}-{_slug(src.stem)}"
    BROLL.mkdir(parents=True, exist_ok=True)
    out = BROLL / f"{nom}.mp4"
    if out.exists():
        sys.exit(f"{out.name} existe déjà dans la banque : donne un autre --nom.")
    pivot = "transpose=1," if a.pivoter else ""
    cadre = f"{pivot}scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1"
    sdr = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable,"
           "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")
    base = [FFMPEG, "-v", "error", "-y", "-i", str(src), "-r", FPS, "-c:v", "libx264", "-preset", "medium",
            "-crf", "18", "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709",
            "-color_trc", "bt709", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart"]
    r = None
    if _hdr(src):
        r = run(base[:6] + ["-vf", sdr + cadre] + base[6:] + [str(out)])
        if r.returncode:
            print("⚠️  Conversion HDR -> SDR impossible avec ce ffmpeg (zscale absent) : plan gardé tel quel, "
                  "couleurs peut-être délavées.")
    if r is None or r.returncode:
        r = run(base[:6] + ["-vf", cadre] + base[6:] + [str(out)])
    if r.returncode or not out.exists():
        sys.exit(f"Conversion impossible :\n{r.stderr[-1200:]}")
    entree = {"file": out.name, "description": a.description.strip(), "categorie": _slug(a.categorie or "divers"),
              "duree": round(float(probe(out) or duree), 1), "visible": bool(a.visible), "date": _date_de(src),
              "source": src.name}
    clips = _catalogue() + [entree]
    CATALOGUE.write_text(json.dumps(clips, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"-> {out}  ({entree['duree']} s, {len(clips)} plan(s) dans la banque)")
    print(f"   story.json : {{\"src\": \"assets/b-roll/{out.name}\", \"start\": …, \"end\": …, \"in\": 0}}")


# ----------------------------------------------------------------------- cli
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = ap.add_subparsers(dest="cmd", required=True)
sb = sub.add_parser("broll", help="la banque de B-rolls du créateur (assets/b-roll/)")
sb.add_argument("action", choices=["list", "apercu", "add"])
sb.add_argument("source", nargs="?", help="la vidéo (apercu, add)")
sb.add_argument("--description", help="ce qu'on voit, en une phrase (add)")
sb.add_argument("--nom", help="nom du fichier dans la banque (défaut : date + nom d'origine)")
sb.add_argument("--categorie", help="ex. lieu, ecran, geste, ambiance, createur")
sb.add_argument("--visible", action="store_true", help="le créateur est à l'image")
sb.add_argument("--pivoter", action="store_true", help="source filmée debout mais enregistrée couchée (sans rotation)")
sb.set_defaults(fn=cmd_broll)
for name, fn in [("init", cmd_init), ("silences", cmd_silences), ("cut", cmd_cut),
                 ("words", cmd_words), ("captions", cmd_captions),
                 ("preview", cmd_preview), ("compose", cmd_compose), ("render", cmd_render), ("close", cmd_close)]:
    s = sub.add_parser(name)
    s.add_argument("slug")
    s.set_defaults(fn=fn)
    if name == "init":
        s.add_argument("--rush", help="la vidéo brute (absente : story créée pour écrire son script d'abord)")
        s.add_argument("--brief", help="la demande du client (idées, liens, consignes), notée dans brief.md")
        s.add_argument("--ouvrir", action="store_true", help="ouvre la story dans l'app HyperFrames")
    if name == "silences":
        s.add_argument("--noise", type=float, default=-40)
        s.add_argument("--d", type=float, default=0.18)
        s.add_argument("--no-text", action="store_true")
    if name == "close":
        s.add_argument("--no-archive", action="store_true")
    if name == "compose":
        s.add_argument("--ecraser", action="store_true", help="réécrit la composition même retouchée dans l'app")
    if name == "preview":
        s.add_argument("--t", type=float, default=2.0)
        s.add_argument("--text", default=None)
args = ap.parse_args()
args.fn(args)
