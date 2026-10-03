

<!-- BEGIN EXTENSION: systeme-stories (ajouté par l'installation du Système Stories ; ne pas dupliquer) -->

## 🟣 Extension installée : Système Stories

Ce projet sait AUSSI monter les **stories Instagram**. Une story n'est **pas un petit Reel** :
c'est un autre pipeline, avec ses propres skills. Le pipeline en 7 étapes ci-dessus ne s'applique
PAS aux stories.

Réponds dans la langue de l'utilisateur et reconnais aussi les demandes en espagnol.
Les exemples français ci-dessous sont illustratifs. Garde les noms techniques inchangés
et transcris l'audio dans sa langue réelle, sans traduction implicite.

| L'utilisateur dit… | Format | Route |
|---|---|---|
| « une story », « monte ma story », « monta esta story », « c'est pour les stories » | Story | charge le skill **`story`** et arrête-toi là |
| « écris-moi un script de story », « escríbeme un guion de story », « une story sur [idée] » | Story | charge le skill **`story-script`** |
| `/setup-stories`, « personnaliser mes stories » | Story | charge le skill **`setup-stories`** |
| « un Reel », « monte ma vidéo », tout le reste | Reel | le pipeline en 7 étapes ci-dessus |

Rappels stories (le détail vit dans les skills) : visage plein écran, **jamais de split-screen**,
**jamais de composition HTML** (tout en ffmpeg via `tools/story.py`, sauf un bandeau ponctuel),
sous-titres sobres une ligne dont le style vient de `brand.config.json` → section `story`
(posée par `/setup-stories`). En cas de doute sur le format, **demande** : « c'est pour un Reel
ou une story ? »

<!-- END EXTENSION: systeme-stories -->
