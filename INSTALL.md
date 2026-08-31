# Installation

Le Système Stories est une **extension** : il s'installe **dans ton dossier Monteur IA**
existant. Rien d'autre à télécharger, rien à configurer à la main.

> ⚠️ **Prérequis : Monteur IA installé et fonctionnel.** Si ce n'est pas encore fait, installe
> d'abord le système principal (son INSTALL.md), puis reviens ici.

---

## 🚀 Le prompt d'installation

> **Le plus simple :** ouvre ton agent (Claude Code ou Codex) **dans ton dossier Monteur IA**
> et dis-lui : « Télécharge l'extension https://github.com/Alex-lmdm/systeme-stories et suis
> les instructions d'installation de son INSTALL.md. » Il fait tout.

Sinon, télécharge le ZIP de ce repo, dézippe-le où tu veux, ouvre ton agent **dans ton dossier
Monteur IA**, et copie-colle exactement le bloc ci-dessous comme premier message (remplace le
chemin de la première ligne par l'endroit où tu as dézippé) :

```text
Tu es mon assistant d'installation pour l'extension « Système Stories » de mon Monteur IA.
Le dossier de l'extension dézippé est ici : ~/Downloads/systeme-stories-main
Installe l'extension étape par étape, sans jamais rien casser. Suis ces règles :

1. VÉRIFIE d'abord que le dossier courant est bien une installation Monteur IA : les dossiers
   `tools/` et `.claude/skills/` existent, et `brand.config.json` ou
   `brand.config.example.json` est présent. Si ce n'est pas le cas, ARRÊTE-TOI et dis-moi
   d'ouvrir mon agent dans mon dossier Monteur IA.

2. COPIE dans ce dossier, depuis le dossier de l'extension (étapes idempotentes : si un
   fichier identique est déjà là, ne le copie pas deux fois ; s'il existe en version
   différente, remplace-le) :
   a) `.claude/skills/story/`, `.claude/skills/story-script/`, `.claude/skills/setup-stories/`
      → dans `.claude/skills/` ;
   b) `tools/story.py` et `tools/story_text.py` → dans `tools/` ;
   c) crée le dossier `stories/` s'il n'existe pas ;
   d) AIGUILLAGE : si `templates/AGENT.md.tpl` ne contient PAS le marqueur
      « BEGIN EXTENSION: systeme-stories », ajoute le contenu INTÉGRAL du fichier
      `templates/agent-extension-stories.md` de l'extension À LA FIN de
      `templates/AGENT.md.tpl` (sans le modifier). S'il contient déjà le marqueur, ne
      touche à rien.

3. VÉRIFIE Python et Pillow (le rendu des sous-titres en dépend) :
   - `python3 --version` (macOS l'a toujours ; Windows : `python --version`) ;
   - `python3 -c "import PIL"` — si ça échoue : `python3 -m pip install --user pillow`
     (Windows : `python -m pip install --user pillow`).

4. Lance `npm run sync` à la racine (il régénère CLAUDE.md / AGENTS.md avec l'aiguillage
   stories, et duplique les nouveaux skills pour Codex dans `.agents/skills/`). Si la
   commande échoue, copie simplement les 3 dossiers de skills dans `.agents/skills/` à la
   main.

5. SMOKE TEST : exécute
   `python3 -c "import sys; sys.path.insert(0,'tools'); import story_text; story_text.caption_png('test sous-titre','stories/_test.png'); print('ok')"`
   puis vérifie que `stories/_test.png` existe et supprime-le. N'importe quel « ok » prouve
   que le rendu des sous-titres fonctionne.

6. Ne PASSE JAMAIS à l'étape suivante si l'étape en cours a échoué. En cas d'échec :
   diagnostique en trois lignes (message d'erreur → cause probable → UNE action corrective),
   puis retente.

7. Affiche un TABLEAU récapitulatif ✅ / ❌ (dossier Monteur IA, skills copiés, tools copiés,
   Pillow, sync, smoke test). Si tout est ✅, conclus par : « Extension installée. Lance
   /setup-stories — 3 questions, 2 minutes, pour poser l'allure de TES sous-titres de story.
   Ensuite dis-moi "écris-moi un script de story" ou "on monte une story". »
```

C'est tout. Laisse l'IA travailler et réponds-lui quand elle te pose une question.

---

## Installation manuelle (si tu préfères)

1. Télécharge et dézippe ce repo.
2. Copie `.claude/skills/story/`, `.claude/skills/story-script/` et
   `.claude/skills/setup-stories/` dans le dossier `.claude/skills/` de ton Monteur IA
   (et dans `.agents/skills/` si tu utilises Codex).
3. Copie `tools/story.py` et `tools/story_text.py` dans le dossier `tools/`.
4. Crée un dossier `stories/` à la racine.
5. Ajoute le contenu de `templates/agent-extension-stories.md` à la fin de
   `templates/AGENT.md.tpl` (une seule fois), puis lance `npm run sync`.
6. Vérifie Pillow : `python3 -c "import PIL"` — sinon `python3 -m pip install --user pillow`.
7. Ouvre ton agent dans le dossier et lance `/setup-stories`.

## Problèmes courants

- **« Aucune police de sous-titre trouvée »** : le fichier `assets/fonts/Inter-900.ttf` du
  produit principal manque. Re-télécharge le repo Monteur IA ou renseigne un chemin de .ttf
  dans `brand.config.json` → `story.captionFont`.
- **« Modèle Whisper introuvable »** : l'installation du produit principal n'est pas allée au
  bout (c'est elle qui télécharge le modèle et écrit `env.whisperModel`). Relance son prompt
  d'installation.
- **`pip` refuse d'installer Pillow (environnement géré)** : utilise
  `python3 -m pip install --user --break-system-packages pillow`, ou installe Python via
  Homebrew (`brew install python`) et recommence.
