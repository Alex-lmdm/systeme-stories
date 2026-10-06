<!-- BEGIN EXTENSION: systeme-stories (ajouté par l'installation du Système Stories ; ne pas dupliquer) -->

## 🟣 Extension installée : Système Stories

Une story Instagram n'est **pas un petit Reel** : autre pipeline, ses propres skills, et le pipeline
en 7 étapes ne s'applique pas. Elle vit dans `stories/<slug>/` du dossier Monteur IA, jamais dans un
Reel.

- « une story », « monte ma story », « monta esta story » → skill **`story`**, et rien d'autre.
- « un script de story », « escríbeme un guion de story » → skill **`story-script`**.
- `/setup-stories`, « personnaliser mes stories » → skill **`setup-stories`**.
- Rappels : visage plein écran, jamais de split-screen ni de composition HTML (tout en ffmpeg via
  `tools/story.py`). En cas de doute : « c'est pour un Reel ou une story ? »

<!-- END EXTENSION: systeme-stories -->
