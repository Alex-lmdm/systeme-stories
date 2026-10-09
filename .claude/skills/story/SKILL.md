---
name: story
description: >-
  Montage d'une STORY Instagram : visage plein écran, naturel, sous-titres sobres une ligne,
  parfois un plan filmé en plein écran (B-roll) et un petit bandeau motion. Use when the user says
  « une story », « monte ma story », « c'est pour les stories » with a face-cam rush.
  PAS un Reel (→ derush + motion-design) : zéro split-screen, zéro motion de Reel, tout passe par
  tools/story.py (B-rolls de la banque du créateur, musique de fond réglée une fois).
  Entrée : un rush brut. Sortie : un MP4 1080x1920 prêt à poster.
---

# Story Instagram — le montage

> ⚠️ **Ce n'est PAS le pipeline Reel.** Une story se publie souvent, vit 24 h et n'a presque pas
> de motion : ni split-screen, ni sections de motion, ni `compositions/`. Tout passe par
> `tools/story.py`, qui écrit lui-même la composition de la story (Monteur IA 2) ou la monte en ffmpeg
> (Monteur IA 1). Si tu te retrouves à écrire du HTML, tu t'es trompé
> de pipeline (sauf porte de sortie §8).

> **Où travailler :** une story vit dans `stories/<slug>/` du **dossier Monteur IA** (celui qui
> contient `templates/AGENT.md.tpl` ; dans l'app HyperFrames, le dossier parent de l'accueil),
> jamais dans un Reel. Les chemins de ce skill, dont `brand.config.json`, partent de ce dossier.
> **Dans l'app HyperFrames (Monteur IA 2), une story se monte techniquement comme un Reel** : un
> projet par story (`init --ouvrir`, conversation neuve), et un `index.html` qui est sa vraie
> composition (visage, voix, plans insérés, bandeaux, sous-titres en éléments séparés), écrite par
> `story.py compose` depuis `story.json` (aussi après `cut` et `captions`). Le créateur peut la
> retoucher à la main dans l'app (texte, emoji, timing, place, taille, volume) : **`compose` reporte
> seul ces retouches dans `story.json` avant de réécrire**, rien n'est jamais perdu. **Ne lance jamais
> `compose --ecraser`** : il jette les retouches du créateur (seul cas : une story composée par une
> version antérieure, sans `.composee.json`, après les avoir reportées à la main). Export natif :
> bouton Export de l'app, ou `story.py render`. Depuis la story, les commandes s'écrivent
> `python3 ../../tools/story.py …`.

> Le style des sous-titres (police, skin, position), le cadrage du visage, la musique de fond et
> la banque de B-rolls viennent de `brand.config.json` → section `story`, écrite par
> **`/setup-stories`**. Si cette section n'existe pas encore, propose de lancer `/setup-stories`
> (2 minutes) avant le premier montage, sinon la story sort dans le style de départ, identique
> pour tout le monde.

> **Musique et B-rolls : une suggestion, jamais une insistance (§4.1).** `story.music` et
> `story.broll` ont trois états : **absent ou `null`** = jamais proposé → tu le proposes **une
> fois par story, en une phrase, à la fin des sous-titres**, puis tu continues ; **`false`** =
> le créateur a refusé → **plus jamais un mot** ; **réglé** (`music` = un fichier, `broll` =
> `true`) → tu t'en sers sans demander. Un refus se note tout de suite dans `brand.config.json`
> (`"music": false` ou `"broll": false`, sans toucher au reste), un oui se règle par
> `/setup-stories` (ou directement, si le créateur donne le fichier dans la conversation).

---

## 1. Le format, en une page

| | Story | (rappel Reel) |
|---|---|---|
| Cadre | 1080×1920, 30 fps | idem |
| Plan par défaut | **visage PLEIN ÉCRAN**, naturel | split-screen |
| Cadrage visage | tel quel, ou **un peu resserré** si le créateur l'a choisi (`faceZoom`, ex. 1,2), appliqué par `cut` sur le rush, donc sans perte de netteté | visage zoomé selon la section |
| Split-screen | **JAMAIS** | par défaut |
| Motion | quasi aucun ; au mieux un **bandeau** haut ou bas par-dessus le visage (un logo, un chiffre, 3 mots) | motion-first, section par section |
| Sous-titres | sobres, **une seule ligne**, skin choisi au `/setup-stories` | style Reel du créateur |
| Position sous-titre | **juste sous le visage** (`captionY`, défaut 1180) | selon la section |
| B-roll | des plans **du créateur** (fournis, ou pris dans **sa banque** `assets/b-roll/`), en **plein écran**, sa voix continue dessous ; **une étape du montage** (§4.1), pas une option | intégré aux sections |
| SFX / musique | **musique de fond** si le créateur en a réglé une (`story.music`, posée par `compose` et par le rendu ffmpeg, ≈ 10 dB sous la voix) ; sinon proposée une fois (§4.1). SFX seulement s'il le demande | sound design complet |
| Publication | pas de légende, pas de DM ; la story se poste telle quelle | étape publication complète |

**Ce qui reste identique au Reel** : le dérush (meilleure prise, blancs coupés, souffle inter-cut
≈ 0,1 s), la doctrine de **découpage des sous-titres** (unité grammaticale, §5), le timing sur
les **vrais mots**, les **safe-zones** Instagram.

**L'esprit du format** : une story réussie a l'air spontanée. Le montage doit se faire oublier :
des coupes propres, des sous-titres discrets, et c'est tout. On n'ajoute un plan ou un bandeau
que s'il sert ce que la personne est en train de dire.

---

## 2. Isolation — une story n'écrase jamais un reel

Tout vit dans `stories/<slug>/` :

```
stories/<slug>/
  story.json     ← LE fichier de config (îlots, sous-titres, plans, bandeaux)
  cut.mp4        ← le dérush (non versionné)
  words.json     ← transcription mot-à-mot
  _caps/         ← les PNG de sous-titres (générés)
  story_<slug>_FINAL.mp4
```

`tools/story.py` ne touche **jamais** un Reel, `derush/` ni `assets/video/` (son seul `index.html`
est la composition de la story). Une story et un reel peuvent donc être montés en parallèle sans se marcher
dessus.

Une fois la story postée : `python3 tools/story.py close <slug>` archive le master dans
`~/Movies/stories-publiees/<slug>/` puis efface le travail (compter ~200 Mo par story). En Monteur
IA 2, le projet de l'app reste, marqué publié (seuls les médias partent) ; en Monteur IA 1, le
dossier est supprimé. `--no-archive` pour ne rien garder du tout.

---

## 3. Le pipeline (7 commandes)

Ordre d'une story : **dérush → sous-titres → B-roll (§4.1) → review du créateur → export**.

```bash
python3 tools/story.py init     <slug> --rush ~/Downloads/rush.MP4 --ouvrir   # projet de l'app
python3 tools/story.py init     <slug> --brief "<demande>" --ouvrir  # app : script d'abord, puis --rush au tournage
python3 tools/story.py silences <slug>          # îlots NUMÉROTÉS + transcription par îlot
python3 tools/story.py cut      <slug>          # après avoir rempli `islands` (cadrage faceZoom appliqué ici)
python3 tools/story.py words    <slug>          # transcription mot-à-mot, prise par prise
python3 tools/story.py captions <slug>          # 1er jet de découpe → story.json
#                                                 puis les B-rolls dans `media` (§4.1) + compose
python3 tools/story.py preview  <slug> --t 3.0  # contrôle visuel d'une frame
python3 tools/story.py render   <slug>          # MP4 final (copié dans ~/Downloads)
python3 tools/story.py broll    list            # la banque de B-rolls du créateur (§4.1)
```

### 3.1 Dérush — choisir les prises

- Bornes = **îlots `silencedetect`** (`-40 dB`, `d=0.18`), **jamais** un timestamp Whisper
  (un LLM ne donne JAMAIS de timestamp de coupe fiable ; le *où couper* vient d'outils
  déterministes, le *quoi garder* vient du raisonnement).
- `pad_start 0.04` / `pad_end 0.02` (valeurs éprouvées) — resserrer les **fins**, jamais les
  débuts (les voyelles d'attaque sont fragiles).

**C'est TOI (l'agent) qui proposes la sélection, pas l'utilisateur.** Après `story.py silences` :

1. Lis la liste numérotée des îlots avec leur transcription.
2. Si le script existe (écrit avec `story-script`), aligne chaque phrase du script sur les
   îlots : la bonne prise est en général la **dernière prise complète** d'une phrase (quand on
   se rate, on recommence). Sans script, reconstitue le fil du propos et repère les reprises,
   les faux départs et les ratés.
3. Propose la sélection : « je garde [2, 5, 6, 9], je jette [3, 4] (reprises de la phrase 2) »,
   avec le texte de chaque prise gardée. **Attends la validation avant d'écrire `islands`.**
4. Écris `islands` dans `story.json` : `[[start, end, "texte de la prise"], …]`, puis
   `story.py cut`.

- ⚠️ L'index dérive dès qu'une phrase a 3-4 prises ratées d'affilée : **recroise les index
  contre la liste numérotée** avant de builder.
- **Re-transcrire le cut** avant de continuer (repasser `silences` sur le cut, ou écouter) :
  lecture = le propos complet, zéro mot coupé ou doublé. Fais valider à l'oreille.

### 3.2 Nettoyage audio (optionnel mais recommandé)

Si l'utilisateur veut le son « studio », applique la même méthode que pour les Reels
(`brand.config.json` → `audio.enhanceMethod`) : Adobe Podcast Enhance sur l'audio du cut, puis
remuxer. La voix d'une story peut aussi rester brute : c'est un format spontané, un son propre
suffit souvent.

---

## 4. `story.json` — le seul fichier à éditer

```jsonc
{
  "slug": "ma-story",
  "rush": "/Users/…/rush.MP4",
  "pad_start": 0.04, "pad_end": 0.02,
  "caption_y": 1180,          // override ponctuel ; le défaut vient de /setup-stories
  "caption_size": 56,
  "caption_case": "as-is",    // "as-is" | "upper"
  "islands":  [[11.05, 14.11, "texte de la prise"]],
  "chunks":   [["premier sous-titre", "de la prise 0"], ["prise 1"]],   // découpage DICTÉ (§5)
  "captions": [{"t": "tu peux", "start": 0.0, "end": 0.6}],             // + "y"/"size"/"x" en override
  "media":    [{"src": "assets/b-roll/2026-10-09-coworking.mp4", "start": 5.0, "end": 8.0, "in": 0.0, "fit": "cover"}],
  "overlays": [{"src": "stories/ma-story/bandeau.mov", "start": 5.0, "end": 8.0, "y": 300, "w": 420}],
  "music":    null                 // absent = la musique réglée au /setup-stories ; null = cette story sans musique
}
```

- **`face_zoom`** (défaut : `story.faceZoom` de brand.config, 1 = tel quel) et **`music`**
  (défaut : `story.music`) se règlent une fois au `/setup-stories` ; une story peut y déroger
  (`"music": null`, ou `{"src": "assets/music/autre.mp3", "in": 12, "volume": 0.07}`). Le
  volume est bas, audible sous la voix ; si le créateur le baisse dans l'app, `compose` le reporte.
- **`media`** = un plan **du créateur** (B-roll), en **plein écran**, qui recouvre son visage sur
  `[start, end]`. Il est **muet** : la voix du cut continue dessous. `src` = un chemin absolu, ou
  relatif au dossier Monteur IA (la banque : `assets/b-roll/<fichier>`).
  - `fit: "cover"` (défaut) : recadré plein cadre (`scale`+`crop` centré).
  - `fit: "blur"` : pour un plan horizontal ou une photo qui ne remplit pas le cadre — posé net
    sur son propre fond flouté, sans déformation.
  - `story.py render` **vérifie les durées** avant de lancer ffmpeg : un plan trop court ou un
    `end` au-delà du cut échoue avec un message clair, pas une erreur ffmpeg cryptique.
- **`overlays`** = le bandeau motion : PNG (ou MOV alpha), centré en x, `y` = son centre
  vertical. Un **SVG est refusé** → l'exporter en PNG avant.
- Les **sous-titres passent toujours au-dessus** de tout, y compris d'un plan plein écran.

### 4.1 B-roll et musique : l'étape qui suit les sous-titres

Une fois les sous-titres posés, **tu enchaînes sur les B-rolls sans attendre que le créateur y
pense** : c'est une étape du montage. Selon l'état de `story.broll` (brand.config) :

- **`true`** (banque réglée) : tu montes les plans, puis tu montres le découpage (§ ci-dessous).
- **absent / `null`** : tu proposes, **une phrase, une fois** : « Si tu veux, je peux insérer des
  plans de toi en plein écran pendant que tu parles (toi qui travailles, qui marches, ton écran,
  ton lieu…). Donne-moi des vidéos courtes, je les garde dans une banque et je pioche dedans à
  chaque story. Optionnel, dis-moi. » Un oui → tu verses ses plans (ci-dessous) et tu règles
  `"broll": true` ; un non → `"broll": false` dans `brand.config.json` et **tu n'en reparles
  jamais** ; pas de réponse → tu continues sans, et tu reproposeras à la prochaine story.
- **`false`** : rien, pas un mot, sauf si le créateur fournit lui-même un plan (alors tu le
  places, sans rouvrir la question de la banque).

**La musique suit la même règle** (`story.music`) : absent → une phrase, une fois, au même
moment : « Tu veux une musique de fond sur tes stories, très bas sous ta voix ? Si tu as déjà
une musique dans ton Monteur IA (`audio.musicFile`), je peux la reprendre, ou tu m'en donnes une
réservée aux stories ; elle sera reprise à chaque fois. » Oui → `/setup-stories` (bloc musique)
ou directement `"music": {"src": "assets/music/<fichier>", "in": 0, "volume": 0.07}` ; non →
`"music": false`. Le monteur ne va **pas** chercher de musique tout seul : c'est le créateur
qui la fournit.

**La banque de B-rolls** (`assets/b-roll/` du dossier Monteur IA, décrite dans `catalog.json`) :

1. **Verser d'abord les plans fournis** (souvent déposés dans la story ou glissés dans l'app),
   pour les retrouver la fois suivante :
   `story.py broll apercu <vidéo>` (planche de 3 images : regarde-la pour décrire le plan), puis
   `story.py broll add <vidéo> --description "<ce qu'on voit, en une phrase>" --categorie <lieu|ecran|geste|ambiance|createur> [--visible]`.
   L'outil convertit en 1080×1920 SDR 30 i/s, garde le son, refuse d'écraser un nom existant.
   Une source filmée debout mais enregistrée couchée (4K sans rotation) : `--pivoter`, à vérifier
   sur l'aperçu avant.
2. **Choisir sur le catalogue**, jamais en ouvrant les vidéos : `story.py broll list`
   (description, catégorie, durée, créateur visible). Un même plan peut servir deux fois avec
   deux `in` différents.
3. Déclarer dans `media` (`"src": "assets/b-roll/<fichier>"`, `in` = point d'entrée dans le
   clip). Caler le moment fort du plan sur le mot (`in` = moment du geste − (mot − start)).

**Le dosage** (ce qui fait une story qui tient) :

- Repérer les **phrases qui se montrent** : un lieu (« je suis dans un coworking »), un geste
  (« j'écris », « je lui parle »), un objet, l'écran, la formule de fin.
- **Environ la moitié du temps en B-roll**, en alternance avec le visage : sur ~40 s, 8 à 9 plans
  de 1,3 à 4 s. En dessous de 1,3 s ça clignote, au-dessus de 4 s on oublie le visage.
- **Le hook** gagne à s'ouvrir sur un plan du **créateur en situation** (en mouvement, dans la
  rue, à son bureau), pris dès sa première image (`in` 0) sur toute la première phrase ; le
  visage face caméra arrive à la 2ᵉ phrase.
- **Le visage** tient les réactions et les phrases d'opinion (« et franchement c'est fatigant »,
  « je vous jure… », le résumé final). Le B-roll montre les lieux, les gestes, le contraste.
- **Le plan de fin** = un plan d'ambiance doux (extérieur, nature, lumière) sur la formule de sortie.
  Le dernier plan finit à la **durée exacte du cut**, sinon le visage revient une image à la fin.
- Un plan couvre une **idée entière**, jamais un bout de mot : caler `start`/`end` sur les
  bornes des sous-titres (`captions` déjà timés). Un plan qui raconte en deux temps (une porte
  qu'on pousse, puis l'espace) mérite d'être allongé : raccourcir le voisin plutôt que couper le geste.
- Le créateur dit « mets cette vidéo quand je parle de X » : retrouve le passage dans
  `captions`, propose les bornes, montre un `preview` au milieu du plan.
- **Dire au créateur quels plans manquent** : chaque phrase forte qu'aucun plan de la banque
  n'illustre vraiment, avec ce qu'il faudrait filmer (5 à 8 s, en vertical). Trois lignes, pas plus.

**Après la première story validée**, note le déroulé plan par plan (temps, voix, image,
sous-titres) dans `stories/reference.md` du dossier Monteur IA : c'est le modèle à relire avant
chaque story suivante (même niveau de dosage, de rythme et de structure). Le créateur peut te
dire « celle-là est la référence » pour la remplacer.

---

## 5. Sous-titres — le découpage par unité grammaticale

`story.py captions` produit un **1er jet légal en largeur mais SANS conscience grammaticale**.
Le découpage final se décide par **unité grammaticale**, se propose à l'utilisateur, et une fois
validé s'écrit dans `chunks` (une liste par prise). Règles, par ordre de force :

1. **Jamais de ponctuation de fin affichée** : retirer `. , ; : ! ?` du texte affiché.
2. **Jamais à cheval sur 2 phrases** : un `. ! ?` ferme TOUJOURS le sous-titre courant.
3. **Nom + adjectif = insécable.** Ne jamais orpheliner l'adjectif de son nom.
4. **Groupe verbal = insécable**, y compris les périphrases : « vient de te donner », « prêt à
   copier », « en train de » = un seul bloc. Les « de »/« à » qui suivent un verbe ne sont PAS
   des points de coupe.
5. **Couper à une frontière logique** : après une virgule, ou avant un connecteur qui démarre
   une nouvelle bribe (`et mais ou donc car puis ensuite alors comme qui que dont où quand si
   parce que`, prépositions de tête, pronoms sujets).
6. **Ne JAMAIS finir un sous-titre sur un mot faible** (article, préposition, conjonction,
   forme élidée, nombre) : il s'accroche au suivant.
7. **Viser 2-3 mots** par sous-titre ; max 4 si ça reste court ET cohérent.
8. **Le mot fort de chute s'isole** : c'est le défaut du rythme court. « ils ont partagé ça » ·
   « dans leur documentation » · « officielle » (et NON « dans leur » · « documentation
   officielle »). Un adjectif, un adverbe ou un nom seul pour l'emphase = OK et fréquent.
9. **En cas de doute : couper plus court.** Chunks courts et variés = lisent mieux, collent
   mieux à la voix, ne débordent jamais.
10. **Corriger les mots mal transcrits** en s'appuyant sur le script (« qu'il » pas « qui »,
    les noms propres, les nombres).

Spécificités story :

- **TOUJOURS une seule ligne.** `story.py` mesure la largeur sur le vrai TTF et **refuse** un
  sous-titre > 880 px. Trop large → re-couper, **jamais réduire la police pour faire rentrer**.
- Pas de sections (il n'y en a pas) : le snap se fait aux **bords de prise**.
- Timing **sur les vrais mots** (`words.json`), jamais au prorata du texte.
- CTA : ne **jamais** écrire le mot « lien » à l'écran → l'emoji 🔗.
- Casse **naturelle** par défaut (le tout-majuscules crie ; une story parle).

**Workflow** : 1er jet `story.py captions` → re-couper par unité → proposer le découpage complet
à l'utilisateur (liste par prise) → coller SES corrections au mot près dans `chunks` → relancer
`captions` → `preview` sur 2-3 moments.

---

## 6. Safe-zones

- Rien d'important dans les **~150 px du haut** (Instagram y pose son UI).
- Rien d'important à **moins de 100 px** des bords — c'est la limite des 880 px de large.
- Bas de cadre : garder **~250 px libres** (barre « Répondre » d'Instagram).
- **Si l'utilisateur prévoit un sticker Instagram** (lien, sondage, question) : demander OÙ il
  compte le poser, et laisser cette zone libre de sous-titres et de bandeaux. Le classique :
  sticker lien au tiers haut (`y ≈ 500-700`), donc bandeaux en bas ce jour-là.

---

## 7. Checklist avant de livrer

- [ ] Cut re-transcrit : lecture = le propos, zéro mot coupé ou doublé.
- [ ] Souffle inter-cut ≈ 0,1 s, régulier.
- [ ] Sous-titres **re-coupés par unité grammaticale**, une seule ligne, sans ponctuation finale.
- [ ] Timing calé sur `words.json` (pas au prorata).
- [ ] `story.py preview` sur 2-3 moments clés : texte lisible, sous le visage, safe-zones OK.
- [ ] Aucun sous-titre ne bave d'une prise sur la suivante.
- [ ] Le mot « lien » n'apparaît nulle part → 🔗.
- [ ] B-roll : proposés ou posés (§4.1), chaque plan couvre une idée entière, le dernier finit à la durée du cut.
- [ ] Musique : celle du réglage, ou proposée une fois si `story.music` est absent ; jamais si `false`.
- [ ] Plans fournis par le créateur versés dans la banque (`broll add`), plans manquants signalés.

---

## 8. Porte de sortie — quand une story a VRAIMENT besoin de motion

Ne pas basculer toute la story sur HyperFrames. Fabriquer **le seul bandeau concerné** en
composition, le rendre en **overlay transparent**, puis le déclarer dans `overlays` :

Deux patrons prêts à copier dans `references/` :

- **`bandeau-texte.html`** — 2 à 4 mots qui claquent (un chiffre, un nom, une punchline), dans
  les couleurs du `brand.config.json` du créateur.
- **`bandeau-logos.html`** — des logos qui arrivent l'un après l'autre, groupe recentré à
  chaque arrivée.

Copier le patron dans `stories/<slug>/`, adapter textes et timings, puis :

```bash
npx hyperframes render -c stories/<slug>/bandeau.html --format mov -o stories/<slug>/bandeau.mov
```

Déclaré ensuite en overlay **plein cadre** : `{"w": 1080, "y": 960}` (le code centre en x et pose
le centre vertical à `y` → un calque 1080×1920 tombe pile).

Deux règles apprises sur ces bandeaux :

- Un groupe dimensionné pour N éléments est **décentré tant qu'il en manque** : recentrer le
  conteneur à chaque arrivée (demi-pas = (largeur + gap) / 2). Le `x` va sur le **conteneur**,
  jamais sur un élément timé.
- Quand le bandeau occupe la ligne des sous-titres, **descendre les sous-titres concernés**
  (`"y": 1420` par caption) au lieu de les supprimer.

Le reste du pipeline ne change pas.

---

## 9. Pièges déjà rencontrés

- **Rush HDR** (iPhone/DJI en HLG) : le rendu SDR délave le visage. `story.py init` le détecte
  et prévient. Filmer en SDR, ou transcoder d'abord (même méthode que pour les Reels).
- **`loop=loop=-1` sur une image en overlay fait pendre ffmpeg indéfiniment.** Inutile :
  `overlay` répète déjà la dernière frame de son input. `story.py` ne boucle donc rien.
- Un `-ss` au-delà de la durée du fichier produit un MP4 **sans flux vidéo**. `story.py render`
  vérifie désormais les durées avant de lancer ffmpeg.
- Une prise **sans aucun sous-titre** (recouverte par un plan : `"chunks": [[…], [], …]`) est
  légitime — `story.py captions` la saute au lieu de planter.
- Un sous-titre qui déborde de 880 px = `story.py` s'arrête net. C'est voulu : re-couper, ne
  jamais réduire la police pour faire rentrer.
- Caméras à 2 flux vidéo (DJI : 2ᵉ flux mjpeg) : `story.py` mappe déjà `[0:v:0]` explicitement.
- **Jamais `-v error` avec `silencedetect`** (le filtre logue en *info*).
