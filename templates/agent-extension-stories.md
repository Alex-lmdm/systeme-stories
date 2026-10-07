<!-- BEGIN EXTENSION: systeme-stories (ajouté par l'installation du Système Stories ; ne pas dupliquer) -->

## 🟣 Extension installée : Système Stories

Une story Instagram n'est **pas un petit Reel** : autre pipeline, ses propres skills, et le pipeline
en 7 étapes ne s'applique pas. Elle vit dans `stories/<slug>/` du dossier Monteur IA, jamais dans un
Reel.

- « une story », « monte ma story », « monta esta story » → skill **`story`**, et rien d'autre.
- « un script de story », « escríbeme un guion de story » → skill **`story-script`**.
- `/setup-stories`, « personnaliser mes stories » → skill **`setup-stories`**.
- Rappels : visage plein écran, jamais de split-screen ni de motion de Reel ; tout passe par
  `tools/story.py`. En cas de doute : « c'est pour un Reel ou une story ? »
{{#LIEU_MAISON}}- Une story = un projet de l'app HyperFrames (une conversation neuve par story) : `python3
  tools/story.py init <slug> --rush "<vidéo>" --ouvrir` (slug court, ex. `story-offre-1`).
{{/LIEU_MAISON}}{{#LIEU_ACCUEIL}}- Story demandée ici : `python3 ../tools/story.py init <slug> --rush "<vidéo glissée>" --ouvrir`
  (slug court, ex. `story-offre-1` ; la vidéo part dans la story), puis dis : « Ta story est dans la
  liste des projets : ouvre-la. » Ne la monte pas dans l'accueil.
- Script de story à écrire ou à brainstormer : crée d'abord la story, sans vidéo : `python3
  ../tools/story.py init <slug> --brief "<sa demande : idées, liens, consignes>" --ouvrir`, puis dis :
  « Ta story est ouverte dans la liste des projets : on écrit le script là-bas. Ouvre-la et écris-lui
  « On y va ». » N'écris pas le script ici.
{{/LIEU_ACCUEIL}}{{#LIEU_REEL}}- Une story ne se monte jamais dans un Reel : `python3 ../../tools/story.py init <slug> --rush "<vidéo>" --ouvrir`.
{{/LIEU_REEL}}{{#LIEU_STORY}}- 📍 **Tu es dans une story** (le nom de ce dossier est son slug), montée techniquement comme un Reel
  avec le style et les règles du skill `story` : commandes `python3 ../../tools/story.py <commande> <slug>`.
  `index.html` est sa composition (visage, voix, plans, bandeaux, sous-titres), écrite par `compose` depuis
  `story.json`. Une retouche faite dans l'app est gardée : `compose` refuse de l'écraser ; reporte-la dans
  `story.json`, puis `compose --ecraser`. Export : bouton Export de l'app, ou `story.py render`.
  Début de conversation : lis `brief.md` s'il existe. Pas encore de vidéo (`rush` vide dans `story.json`) :
  on en est au script (skill `story-script`) ; tournée, elle s'ajoute par `init <slug> --rush "<vidéo>"`.
{{/LIEU_STORY}}
<!-- END EXTENSION: systeme-stories -->
