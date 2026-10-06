---
name: story
description: >-
  Montage d'une STORY Instagram : visage plein écran, naturel, sous-titres sobres une ligne,
  parfois un plan filmé en plein écran (B-roll) et un petit bandeau motion. Use when the user says
  « une story », « monte ma story », « c'est pour les stories » with a face-cam rush.
  PAS un Reel (→ derush + motion-design) : zéro split-screen, zéro composition HTML, pipeline
  100 % ffmpeg via tools/story.py. Entrée : un rush brut. Sortie : un MP4 1080x1920 prêt à poster.
---

# Story Instagram — le montage

> ⚠️ **Ce n'est PAS le pipeline Reel.** Une story se publie souvent, vit 24 h et n'a presque pas
> de motion. Elle ne passe **jamais** par HyperFrames, `index.html`, `compositions/` ou le studio.
> Tout se fait en ffmpeg via `tools/story.py`. Si tu te retrouves à écrire du HTML, tu t'es trompé
> de pipeline (sauf porte de sortie §8).

> **Où travailler :** une story vit dans `stories/<slug>/` du **dossier Monteur IA** (celui qui
> contient `templates/AGENT.md.tpl` ; dans l'app HyperFrames, le dossier parent de l'accueil),
> jamais dans un Reel. Lance chaque commande depuis ce dossier : les chemins de ce skill, dont
> `brand.config.json`, partent de là. Dans l'app, une story n'a ni aperçu ni timeline : elle sort
> directement en MP4.

> Le style des sous-titres (police, skin, position) vient de `brand.config.json` → section
> `story`, écrite par **`/setup-stories`**. Si cette section n'existe pas encore, propose de
> lancer `/setup-stories` (2 minutes) avant le premier montage — sinon la story sort dans le
> style de départ, identique pour tout le monde.

---

## 1. Le format, en une page

| | Story | (rappel Reel) |
|---|---|---|
| Cadre | 1080×1920, 30 fps | idem |
| Plan par défaut | **visage PLEIN ÉCRAN**, naturel | split-screen |
| Split-screen | **JAMAIS** | par défaut |
| Motion | quasi aucun ; au mieux un **bandeau** haut ou bas par-dessus le visage (un logo, un chiffre, 3 mots) | motion-first, section par section |
| Sous-titres | sobres, **une seule ligne**, skin choisi au `/setup-stories` | style Reel du créateur |
| Position sous-titre | **juste sous le visage** (`captionY`, défaut 1180) | selon la section |
| B-roll | des plans **que le créateur fournit**, en **plein écran**, sa voix continue dessous | intégré aux sections |
| SFX / musique | pas par défaut ; seulement s'il le demande | sound design complet |
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

`tools/story.py` ne touche **jamais** `index.html`, `compositions/`, `derush/` ni
`assets/video/`. Une story et un reel peuvent donc être montés en parallèle sans se marcher
dessus.

Une fois la story postée : `python3 tools/story.py close <slug>` — archive le master dans
`~/Movies/stories-publiees/<slug>/` puis supprime le dossier de travail (compter ~200 Mo par
story). `--no-archive` pour ne rien garder du tout.

---

## 3. Le pipeline (7 commandes)

```bash
python3 tools/story.py init     <slug> --rush ~/Downloads/rush.MP4
python3 tools/story.py silences <slug>          # îlots NUMÉROTÉS + transcription par îlot
python3 tools/story.py cut      <slug>          # après avoir rempli `islands`
python3 tools/story.py words    <slug>          # transcription mot-à-mot, prise par prise
python3 tools/story.py captions <slug>          # 1er jet de découpe → story.json
python3 tools/story.py preview  <slug> --t 3.0  # contrôle visuel d'une frame
python3 tools/story.py render   <slug>          # MP4 final (copié dans ~/Downloads)
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
  "captions": [{"t": "tu peux", "start": 0.0, "end": 0.6}],             // + "y"/"size" en override
  "media":    [{"src": "/chemin/plan.mp4", "start": 5.0, "end": 8.0, "in": 0.0, "fit": "cover"}],
  "overlays": [{"src": "stories/ma-story/bandeau.mov", "start": 5.0, "end": 8.0, "y": 300, "w": 420}]
}
```

- **`media`** = un plan que le créateur a filmé (B-roll), en **plein écran**, qui recouvre son
  visage sur `[start, end]`. Il est **muet** : la voix du cut continue dessous.
  - `fit: "cover"` (défaut) : recadré plein cadre (`scale`+`crop` centré).
  - `fit: "blur"` : pour un plan horizontal ou une photo qui ne remplit pas le cadre — posé net
    sur son propre fond flouté, sans déformation.
  - `story.py render` **vérifie les durées** avant de lancer ffmpeg : un plan trop court ou un
    `end` au-delà du cut échoue avec un message clair, pas une erreur ffmpeg cryptique.
- **`overlays`** = le bandeau motion : PNG (ou MOV alpha), centré en x, `y` = son centre
  vertical. Un **SVG est refusé** → l'exporter en PNG avant.
- Les **sous-titres passent toujours au-dessus** de tout, y compris d'un plan plein écran.

### Placer un B-roll — les règles

- Un plan couvre une **idée entière** (une phrase ou un groupe de phrases), jamais un bout de
  mot : caler `start`/`end` sur les bornes des sous-titres concernés (`captions` déjà timés).
- 2 à 4 secondes par plan : en dessous ça clignote, au-dessus on oublie le visage.
- L'utilisateur dit « mets cette vidéo quand je parle de X » : retrouve le passage dans
  `captions`, propose les bornes, montre un `preview` au milieu du plan.

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
- [ ] B-roll : chaque plan couvre une idée entière, durées vérifiées.

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
