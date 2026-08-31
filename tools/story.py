#!/usr/bin/env python3
"""Pipeline STORY Instagram (format vertical 1080x1920, 30 fps) — 100 % ffmpeg, sans studio.

POURQUOI un pipeline séparé des Reels : une story = visage plein écran, sous-titres sobres,
parfois un plan filmé en plein écran et un petit bandeau motion. Zéro split-screen, zéro
composition HTML. Passer par HyperFrames coûterait le prix d'un Reel pour un format publié
beaucoup plus souvent et qui vit 24 h. La doctrine complète vit dans le skill `story`.

Tout se déclare dans stories/<slug>/story.json ; ce fichier ne touche JAMAIS index.html,
compositions/ ni derush/ -> une story et un reel peuvent être montés en parallèle.

Les chemins (ffmpeg, whisper) et le style des sous-titres viennent de brand.config.json
(sections `env` et `story`) : rien n'est codé en dur.

Usage :
  python3 tools/story.py init      <slug> --rush /chemin/rush.MP4
  python3 tools/story.py silences  <slug> [--noise -40] [--d 0.18] [--no-text]
  python3 tools/story.py cut       <slug>
  python3 tools/story.py words     <slug>
  python3 tools/story.py captions  <slug>
  python3 tools/story.py preview   <slug> [--t 2.0]
  python3 tools/story.py render    <slug>
  python3 tools/story.py close     <slug> [--no-archive]
"""
import argparse
import difflib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import story_text as ST  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
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
            return json.loads(p.read_text())
        except (OSError, ValueError):
            pass
    return {}


def _env_bin(key, fallback):
    v = (_brand_config().get("env") or {}).get(key)
    if v and (pathlib.Path(v).exists() or shutil.which(v)):
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
    base = {**DEFAULTS, "caption_y": st["captionY"], "caption_size": st["captionSize"],
            "caption_case": st["captionCase"]}
    return {**base, **json.loads(p.read_text())}


def save(slug, cfg):
    (sdir(slug) / "story.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1))


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


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
    d = sdir(a.slug)
    d.mkdir(parents=True, exist_ok=True)
    rush = pathlib.Path(a.rush).expanduser().resolve()
    if not rush.exists():
        sys.exit(f"Rush introuvable : {rush}")
    info = probe(rush, "stream=index,codec_type,codec_name,width,height,color_transfer")
    print(f"Rush : {rush}\nDurée : {probe(rush)} s\n{info}")
    if "color_transfer=arib-std-b67" in info or "color_transfer=smpte2084" in info:
        print("⚠️  Rush en HDR : le rendu SDR délavera les couleurs. Filmer en SDR, ou "
              "transcoder d'abord (voir skill story, section pièges).")
    cfg = {"slug": a.slug, "rush": str(rush), **DEFAULTS,
           "islands": [], "captions": [], "media": [], "overlays": []}
    save(a.slug, cfg)
    print(f"\n-> {d/'story.json'}  (remplir `islands` après `story.py silences {a.slug}`)")


# --------------------------------------------------------------------- silences
def cmd_silences(a):
    cfg = load(a.slug)
    src = cfg["rush"]
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
    parts, cin, kept = [], "", 0.0
    for i, isl in enumerate(cfg["islands"]):
        s = max(isl[0] - cfg["pad_start"], 0.0)
        e = isl[1] + cfg["pad_end"]
        kept += e - s
        parts.append(f"[0:v:0]trim=start={s:.3f}:end={e:.3f},setpts=PTS-STARTPTS,"
                     f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}[v{i}];")
        parts.append(f"[0:a:0]atrim=start={s:.3f}:end={e:.3f},asetpts=PTS-STARTPTS[a{i}];")
        cin += f"[v{i}][a{i}]"
    fg = "".join(parts) + f"{cin}concat=n={len(cfg['islands'])}:v=1:a=1[v][a]"
    print(f"Prises : {len(cfg['islands'])} | durée estimée : {kept:.2f} s")
    r = run([FFMPEG, "-y", "-i", cfg["rush"], "-filter_complex", fg,
             "-map", "[v]", "-map", "[a]", "-r", FPS,
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "192k", str(out)])
    if r.returncode:
        sys.exit(r.stderr[-1800:])
    print(f"-> {out}  ({probe(out)} s)")


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
    p.write_text(json.dumps(words, ensure_ascii=False, indent=1))
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
    words = json.loads(wp.read_text())
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


def cmd_render(a):
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
        fg.append(f"[{n}:v]format=rgba[c{n}];")
        fg.append(f"{last}[c{n}]overlay=(W-w)/2:{y}-h/2:"
                  f"enable='between(t,{c['start']:.3f},{c['end']:.3f})'[s{n}];")
        last, n = f"[s{n}]", n + 1

    # ⚠️ Le master reste dans le dossier isolé de la story (jamais dans renders/, que le
    # pipeline Reel purge à la clôture d'un montage).
    out = sdir(a.slug) / f"story_{cfg['slug']}_FINAL.mp4"
    chain = "".join(fg)
    if chain.endswith(";"):
        chain = chain[:-1]
    cmd = [FFMPEG, "-y"] + inputs
    if chain:
        cmd += ["-filter_complex", chain, "-map", last, "-map", "0:a"]
    else:
        cmd += ["-map", "0:v", "-map", "0:a"]
    cmd += ["-r", FPS, "-c:v", "libx264", "-preset", "slow", "-crf", "16",
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", str(out)]
    print(f"{len(cfg.get('media',[]))} plan(s) · {len(cfg.get('overlays',[]))} bandeau(x) · "
          f"{len(cfg.get('captions',[]))} sous-titres · skin {st['captionsSkin']}")
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
    if master and not a.no_archive:
        arch = pathlib.Path.home() / "Movies" / "stories-publiees" / a.slug
        arch.mkdir(parents=True, exist_ok=True)
        (arch / master.name).write_bytes(master.read_bytes())
        print(f"master archivé -> {arch / master.name}")
    elif not master:
        print("aucun master trouvé (rien à archiver)")
    size = sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
    shutil.rmtree(d)
    print(f"stories/{a.slug}/ supprimé ({size/1e6:.0f} Mo libérés)")


# ----------------------------------------------------------------------- cli
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = ap.add_subparsers(dest="cmd", required=True)
for name, fn in [("init", cmd_init), ("silences", cmd_silences), ("cut", cmd_cut),
                 ("words", cmd_words), ("captions", cmd_captions),
                 ("preview", cmd_preview), ("render", cmd_render), ("close", cmd_close)]:
    s = sub.add_parser(name)
    s.add_argument("slug")
    s.set_defaults(fn=fn)
    if name == "init":
        s.add_argument("--rush", required=True)
    if name == "silences":
        s.add_argument("--noise", type=float, default=-40)
        s.add_argument("--d", type=float, default=0.18)
        s.add_argument("--no-text", action="store_true")
    if name == "close":
        s.add_argument("--no-archive", action="store_true")
    if name == "preview":
        s.add_argument("--t", type=float, default=2.0)
        s.add_argument("--text", default=None)
args = ap.parse_args()
args.fn(args)
