"""Tests des outils du Système Stories (hors livraison : l'installation ne copie que tools/, les skills
et le bloc de consignes, jamais tests/).

    python3 -m unittest discover -s tests -v

Sans dépendance au-delà de ce que l'extension exige déjà (Pillow, pour story_text.py). Tout se
passe dans un dossier temporaire : rien n'est écrit dans le dépôt.
"""
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

DEPOT = pathlib.Path(__file__).resolve().parents[1]
PIL_PRESENT = importlib.util.find_spec("PIL") is not None


@unittest.skipUnless(PIL_PRESENT, "Pillow absent (story_text.py en dépend)")
class SortieWindows(unittest.TestCase):
    """Windows : la sortie lue par l'agent est en cp1252 ; le « ⚠️ » de `story.py captions` ne doit
    pas faire planter l'outil (Monteur IA 1, sans lieux.py)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.racine = pathlib.Path(self.tmp.name) / "Monteur IA · Été"
        (self.racine / "tools").mkdir(parents=True)
        for f in ("story.py", "story_text.py"):
            shutil.copy2(DEPOT / "tools" / f, self.racine / "tools" / f)
        story = self.racine / "stories" / "essai"
        story.mkdir(parents=True)
        (story / "story.json").write_text(json.dumps({
            "slug": "essai", "islands": [[0.0, 1.2, "Bonjour à tous"]], "chunks": [["Bonjour à tous"]],
        }, ensure_ascii=False), encoding="utf-8")
        (story / "words.json").write_text(json.dumps([
            {"w": "Bonjour", "start": 0.1, "end": 0.5, "take": 0},
            {"w": "à", "start": 0.5, "end": 0.6, "take": 0},
            {"w": "tous", "start": 0.6, "end": 1.0, "take": 0},
        ], ensure_ascii=False), encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_captions_en_cp1252(self):
        env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
        env.pop("PYTHONUTF8", None)
        r = subprocess.run([sys.executable, str(self.racine / "tools" / "story.py"), "captions", "essai"],
                           capture_output=True, env=env, cwd=self.racine)
        self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace")[-800:])
        self.assertIn("⚠️".encode("utf-8"), r.stdout)
        cfg = json.loads((self.racine / "stories" / "essai" / "story.json").read_text(encoding="utf-8"))
        self.assertEqual([c["t"] for c in cfg["captions"]], ["Bonjour à tous"])


@unittest.skipUnless(PIL_PRESENT and shutil.which("ffmpeg") and shutil.which("ffprobe"),
                     "Pillow ou ffmpeg absent")
class StoryCommeUnReel(unittest.TestCase):
    """Monteur IA 2 : une story est un projet de l'app, montée techniquement comme un Reel (vraie
    composition HyperFrames, éléments séparés), avec le style du Système Stories ; la vidéo glissée
    dans l'accueil part dans la story ; une retouche faite dans l'app n'est jamais écrasée ; la
    clôture garde un projet léger, marqué publié."""

    MONTEUR = pathlib.Path(os.environ.get("MONTEUR_IA", DEPOT.parent / "monteur-ia-template"))

    def setUp(self):
        if not (self.MONTEUR / "tools" / "lieux.py").exists():
            self.skipTest("Monteur IA 2 introuvable (variable MONTEUR_IA)")
        self.tmp = tempfile.TemporaryDirectory()
        self.maison = pathlib.Path(self.tmp.name) / "Monteur IA"
        (self.maison / "templates").mkdir(parents=True)
        (self.maison / "templates" / "AGENT.md.tpl").write_text("# test\n", encoding="utf-8")
        (self.maison / "tools").mkdir()
        for f in ("story.py", "story_text.py"):
            shutil.copy2(DEPOT / "tools" / f, self.maison / "tools" / f)
        shutil.copy2(self.MONTEUR / "tools" / "lieux.py", self.maison / "tools" / "lieux.py")
        (self.maison / "assets" / "fonts").mkdir(parents=True)
        shutil.copy2(self.MONTEUR / "assets" / "fonts" / "Inter-900.ttf", self.maison / "assets" / "fonts" / "Inter-900.ttf")
        (self.maison / "hyperframes.json").write_text("{}", encoding="utf-8")
        (self.maison / "assets" / "vendor").mkdir(parents=True)
        (self.maison / "assets" / "vendor" / "gsap.min.js").write_text("// gsap", encoding="utf-8")
        self.accueil = self.maison / "Accueil · Test"
        (self.accueil / "assets").mkdir(parents=True)
        (self.accueil / "meta.json").write_text(json.dumps({"monteurIa": {"lieu": "accueil"}}), encoding="utf-8")
        self.rush = self.accueil / "assets" / "rush.mp4"
        self.video(self.rush, 3)
        self.plan = self.maison / "plan.mp4"
        self.video(self.plan, 2, taille="1920x1080")

    def video(self, out, secondes, taille="1080x1920"):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={taille}:rate=30",
                        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000", "-t", str(secondes),
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(out)], check=True)

    def tearDown(self):
        self.tmp.cleanup()

    def story(self, *args, check=True):
        return subprocess.run([sys.executable, str(self.maison / "tools" / "story.py"), *args],
                              capture_output=True, text=True, encoding="utf-8", check=check)

    def test_story_montee_comme_un_reel(self):
        d = self.maison / "stories" / "essai"
        self.story("init", "essai", "--rush", str(self.rush))
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        self.assertEqual((meta["monteurIa"]["lieu"], meta["monteurIa"]["etat"]), ("story", "en-cours"))
        self.assertTrue((d / "hyperframes.json").exists() and (d / "assets/vendor/gsap.min.js").exists())
        self.assertIn("Story en préparation", (d / "index.html").read_text(encoding="utf-8"))
        self.assertFalse(self.rush.exists(), "la copie de l'accueil part dans la story")
        cfg = json.loads((d / "story.json").read_text(encoding="utf-8"))
        self.assertEqual(pathlib.Path(cfg["rush"]).parent, d.resolve())

        cfg["islands"] = [[0.2, 2.4, "test"]]
        (d / "story.json").write_text(json.dumps(cfg), encoding="utf-8")
        self.story("cut", "essai")
        page = (d / "index.html").read_text(encoding="utf-8")
        self.assertIn('<video id="visage" class="plein clip" src="cut.mp4" muted', page)
        self.assertIn('<audio id="voix" src="cut.mp4"', page)

        cfg = json.loads((d / "story.json").read_text(encoding="utf-8"))
        cfg["captions"] = [{"t": "Bonjour à tous", "start": 0.0, "end": 1.0}, {"t": "Et voilà", "start": 1.0, "end": 2.0}]
        cfg["media"] = [{"src": str(self.plan), "start": 0.5, "end": 1.5}]
        (d / "story.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        self.story("compose", "essai")
        page = (d / "index.html").read_text(encoding="utf-8")
        self.assertRegex(page, r'<video id="plan-0" class="plein clip" src="assets/plans/plan-0-\w+\.mp4"')
        self.assertIn('<span>Bonjour à tous</span>', page)
        self.assertIn('style="top: 1124px; height: 112px; font-size: 56px"', page,
                      "un sous-titre a une hauteur réelle (un élément de hauteur nulle n'est pas rendu)")
        self.assertIn('@font-face { font-family: "StoryCaption"; src: url("assets/fonts/Inter-900.ttf")', page)
        self.assertIn("text-shadow:", page, "skin ombre par défaut")
        self.assertNotIn("../", page, "le rendu ne voit que le dossier de la story")
        self.assertTrue(any((d / "assets" / "plans").glob("plan-0-*.mp4")))

        # L'app pose ses data-hf-id : ce n'est pas une retouche.
        (d / "index.html").write_text(page.replace('<span>', '<span data-hf-id="hf-1">'), encoding="utf-8")
        self.story("compose", "essai")
        # Une vraie retouche dans l'app (sous-titre retimé, texte changé, emoji ajouté) est REPORTÉE
        # dans story.json avant la réécriture : rien n'est perdu, jamais besoin de --ecraser.
        page = (d / "index.html").read_text(encoding="utf-8")
        retouche = (page.replace('data-start="1.000"', 'data-start="1.200"')
                    .replace('<span>Et voilà</span>', '<span data-hf-id="hf-9">Et voilà 🎉</span>'))
        (d / "index.html").write_text(retouche, encoding="utf-8")
        r = self.story("compose", "essai")
        self.assertIn("reportées dans story.json", r.stdout)
        cfg = json.loads((d / "story.json").read_text(encoding="utf-8"))
        self.assertEqual((cfg["captions"][1]["start"], cfg["captions"][1]["t"]), (1.2, "Et voilà 🎉"))
        page = (d / "index.html").read_text(encoding="utf-8")
        self.assertIn('data-start="1.200"', page)
        self.assertIn("Et voilà 🎉", page)
        # Un plan supprimé dans l'app disparaît de story.json ; un plan décalé garde son point d'entrée.
        page = re.sub(r'\n\s*<video id="plan-0"[^\n]*', "", page)
        (d / "index.html").write_text(page, encoding="utf-8")
        self.story("compose", "essai")
        cfg = json.loads((d / "story.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["media"], [])
        # Story composée par une version antérieure (pas d'état connu) : l'ancien garde-fou reste.
        (d / ".composee.json").unlink()
        (d / "index.html").write_text((d / "index.html").read_text(encoding="utf-8").replace('data-start="1.200"', 'data-start="1.300"'),
                                      encoding="utf-8")
        r = self.story("compose", "essai", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("état d'origine n'est pas connu", r.stderr + r.stdout)
        self.story("compose", "essai", "--ecraser")
        self.assertIn('data-start="1.200"', (d / "index.html").read_text(encoding="utf-8"))

        # Un sous-titre trop large : la composition s'écrit (l'app le montre), l'export le refuse.
        cfg = json.loads((d / "story.json").read_text(encoding="utf-8"))
        cfg["captions"].append({"t": "Un sous-titre beaucoup trop long pour une seule ligne", "start": 2.0, "end": 2.3})
        (d / "story.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
        sortie = self.story("compose", "essai", "--ecraser").stdout
        self.assertIn("trop large", sortie)
        self.assertIn("beaucoup trop long", (d / "index.html").read_text(encoding="utf-8"))
        r = self.story("render", "essai", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("trop large", r.stderr + r.stdout)

        shutil.copy2(d / "cut.mp4", d / "story_essai_FINAL.mp4")
        (d / "renders").mkdir()
        shutil.copy2(d / "cut.mp4", d / "renders" / "export-app.mp4")   # l'export du bouton Export de l'app
        self.story("close", "essai", "--no-archive")
        self.assertEqual(sorted(p.name for p in d.iterdir()),
                         ["assets", "hyperframes.json", "index.html", "meta.json", "renders", "story.json"],
                         "les dossiers de l'app (renders/, caches) ne sont jamais touchés à la clôture")
        self.assertEqual(json.loads((d / "meta.json").read_text(encoding="utf-8"))["monteurIa"]["etat"], "publie")
        self.assertIn("Story publiée", (d / "index.html").read_text(encoding="utf-8"))


    def test_musique_zoom_et_banque_de_brolls(self):
        """Réglages de /setup-stories : visage un peu zoomé au cut (sans perte), musique de fond posée
        par compose sous la voix (volume, point d'entrée, retouchable dans l'app), banque de B-rolls
        décrite dans assets/b-roll/catalog.json."""
        musique = self.maison / "assets" / "music" / "fond.mp3"
        musique.parent.mkdir(parents=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:sample_rate=44100",
                        "-t", "40", "-c:a", "libmp3lame", str(musique)], check=True)
        (self.maison / "brand.config.json").write_text(json.dumps({
            "story": {"faceZoom": 1.2, "music": {"src": "assets/music/fond.mp3", "in": 10, "volume": 0.07}, "broll": True},
        }), encoding="utf-8")
        d = self.maison / "stories" / "zoom"
        self.story("init", "zoom", "--rush", str(self.plan))   # rush 1920x1080 : le zoom recadre dedans
        cfg = json.loads((d / "story.json").read_text(encoding="utf-8"))
        cfg["islands"] = [[0.1, 1.9, "test"]]
        (d / "story.json").write_text(json.dumps(cfg), encoding="utf-8")
        self.assertIn("visage x1.2", self.story("cut", "zoom").stdout)
        dims = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                               str(d / "cut.mp4")], capture_output=True, text=True).stdout.split()[0]
        self.assertEqual(dims, "1080,1920")
        page = (d / "index.html").read_text(encoding="utf-8")
        self.assertIn('<audio id="musique" src="assets/musique/fond.mp3" data-start="0"', page)
        self.assertIn('data-media-start="10" data-volume="0.07"', page)
        self.assertTrue((d / "assets" / "musique" / "fond.mp3").exists(), "le rendu ne voit que la story")
        # Volume baissé dans l'app -> reporté dans story.json (la musique devient propre à la story).
        (d / "index.html").write_text(page.replace('data-volume="0.07"', 'data-volume="0.04"'), encoding="utf-8")
        self.story("compose", "zoom")
        cfg = json.loads((d / "story.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["music"]["volume"], 0.04)
        # "music": null dans story.json = cette story sans musique, malgré le réglage.
        cfg["music"] = None
        (d / "story.json").write_text(json.dumps(cfg), encoding="utf-8")
        self.story("compose", "zoom")
        self.assertNotIn('id="musique"', (d / "index.html").read_text(encoding="utf-8"))

        # Banque de B-rolls : un plan fourni est converti, catalogué, puis utilisable par son chemin.
        r = self.story("broll", "apercu", str(self.rush))
        self.assertTrue((self.maison / "assets" / "b-roll" / ".apercus" / "rush.jpg").exists(), r.stdout)
        r = self.story("broll", "add", str(self.rush), check=False)
        self.assertNotEqual(r.returncode, 0, "une description est obligatoire")
        r = self.story("broll", "add", str(self.rush), "--description", "Mire de test", "--categorie", "Écran", "--nom", "mire")
        clip = self.maison / "assets" / "b-roll" / "mire.mp4"
        self.assertTrue(clip.exists(), r.stdout)
        cat = json.loads((self.maison / "assets" / "b-roll" / "catalog.json").read_text(encoding="utf-8"))
        self.assertEqual((cat[0]["file"], cat[0]["categorie"], cat[0]["description"]), ("mire.mp4", "ecran", "Mire de test"))
        self.assertIn("Mire de test", self.story("broll", "list").stdout)
        r = self.story("broll", "add", str(self.rush), "--description", "doublon", "--nom", "mire", check=False)
        self.assertNotEqual(r.returncode, 0, "jamais d'écrasement dans la banque")
        cfg = json.loads((d / "story.json").read_text(encoding="utf-8"))
        cfg["media"] = [{"src": "assets/b-roll/mire.mp4", "start": 0.2, "end": 1.2, "in": 0.5}]
        (d / "story.json").write_text(json.dumps(cfg), encoding="utf-8")
        self.story("compose", "zoom")
        self.assertRegex((d / "index.html").read_text(encoding="utf-8"), r'<video id="plan-0" class="plein clip" src="assets/plans/plan-0-\w+\.mp4"')

    def test_script_d_abord_puis_video(self):
        """Dans l'app, un script se brainstorme dans le projet de la story : init --brief sans vidéo,
        puis la vidéo arrive au tournage par le même init, sans rien perdre."""
        d = self.maison / "stories" / "idee"
        self.story("init", "idee", "--brief", "Teaser de mon offre, ton détendu")
        self.assertIn("Teaser de mon offre", (d / "brief.md").read_text(encoding="utf-8"))
        self.assertIn("Script de la story en cours", (d / "index.html").read_text(encoding="utf-8"))
        self.assertEqual(json.loads((d / "meta.json").read_text(encoding="utf-8"))["monteurIa"]["lieu"], "story")
        r = self.story("silences", "idee", check=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Pas encore de vidéo", r.stderr + r.stdout)
        cfg = json.loads((d / "story.json").read_text(encoding="utf-8"))
        cfg["caption_size"] = 60   # un réglage pris pendant le script
        (d / "story.json").write_text(json.dumps(cfg), encoding="utf-8")
        self.story("init", "idee", "--rush", str(self.rush))
        cfg = json.loads((d / "story.json").read_text(encoding="utf-8"))
        self.assertEqual((pathlib.Path(cfg["rush"]).name, cfg["caption_size"]), ("rush.mp4", 60))
        self.assertTrue((d / "brief.md").exists())
        r = self.story("init", "idee", "--rush", str(self.plan), check=False)
        self.assertNotEqual(r.returncode, 0, "une story qui a sa vidéo ne se réinitialise pas")


if __name__ == "__main__":
    unittest.main()
