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


if __name__ == "__main__":
    unittest.main()
