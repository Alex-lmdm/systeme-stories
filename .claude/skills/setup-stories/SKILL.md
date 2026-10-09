---
name: setup-stories
description: >-
  Onboarding du Système Stories : choisir le style des sous-titres de story (skin, taille,
  position calibrée sur un rush test), le cadrage du visage, la musique de fond et la banque de
  B-rolls, et l'écrire dans brand.config.json → section `story`. Use when the user types
  /setup-stories, asks to configure / personnaliser ses stories, veut régler sa musique ou ses
  B-rolls de story, or at the first story if the `story` section is missing from brand.config.json.
---

# /setup-stories — le style de tes stories, une fois

> **3 minutes, 6 questions, dont 3 optionnelles.** Une story n'a presque pas de style : c'est
> voulu, le format doit avoir l'air spontané. Ce qu'on pose : l'allure des sous-titres (à toi,
> pas celle d'un autre), le cadrage de ton visage, et deux options qui reviennent à chaque story
> si tu les prends : une musique de fond et une banque de plans de toi (B-rolls).

> **Où travailler :** dans le **dossier Monteur IA**, celui qui contient `templates/AGENT.md.tpl`
> (dans l'app HyperFrames, la conversation est ouverte dans l'accueil ou un Reel : c'est leur
> dossier parent). `brand.config.json`, `tools/story.py` et `stories/` s'entendent depuis ce
> dossier : lance les commandes depuis lui, et ne crée jamais de `brand.config.json` dans un Reel
> ou dans l'accueil (l'outil ne le lirait pas, le réglage serait perdu).

## Principes de fonctionnement

1. **Une question à la fois**, réponse par défaut toujours proposée, « je ne sais pas encore »
   est une réponse valable (les défauts sont bons, on peut monter tout de suite et revenir).
2. **Source de vérité** : `brand.config.json` du dossier Monteur IA → section `story`. Si ce
   fichier n'existe pas du tout dans le dossier Monteur IA, le produit principal n'est pas
   installé ou pas personnalisé : arrêter et renvoyer vers son installation (puis `/setup`).
3. **Aucune écriture avant validation** : récapituler les valeurs, attendre un OK, écrire.
4. **Le pourquoi en une phrase** quand un réglage a un enjeu, jamais un paragraphe technique.
5. Ce skill n'installe rien.

## Les 6 questions

Un bloc seul se refait sans tout reprendre : « /setup-stories musique », « /setup-stories
b-roll », « /setup-stories cadrage » → poser seulement la question concernée, écrire, s'arrêter.

### Q1 — Le skin des sous-titres

« Tes sous-titres de story, tu les veux comment ? » (montrer les 4, recommander `ombre`) :

| Skin | Description à donner | Pour qui |
|---|---|---|
| **ombre** (défaut) | Texte blanc, ombre portée douce, aucun fond. Le look le plus naturel, lisible sur presque tout. | Le choix sobre, recommandé |
| **contour** | Texte blanc cerclé de noir. Très lisible même sur fond clair et agité. | Ceux qui filment en extérieur |
| **plaque** | Texte sur une plaque sombre semi-transparente arrondie. | Fonds très clairs ou chargés |
| **bloc** | Texte sur un fond plein aux couleurs de ta marque (reprend ton accent du /setup principal). | Ceux qui veulent rappeler leur identité Reel |

→ `story.captionsSkin`. Couleur du texte : blanc par défaut (`story.captionColor`), ne demander
que si l'utilisateur veut autre chose.

### Q2 — La taille et la casse

« Taille de texte 56 px (bon défaut, lisible sans crier) et casse naturelle, ça te va ? »
La casse naturelle est recommandée : le tout-majuscules crie, une story parle.
→ `story.captionSize` (56), `story.captionCase` (`as-is` | `upper`).

### Q3 — La position, calibrée sur TON cadrage (optionnelle mais recommandée)

Le sous-titre se pose **juste sous le visage**. Le bon `captionY` dépend de comment la personne
se cadre. Deux chemins :

- **Sans rush** : garder le défaut `1180` (visage centré classique). Dire que ça se calibrera
  à la première story.
- **Avec un rush test** (recommandé) : demander une vidéo de quelques secondes cadrée comme
  d'habitude, puis :
  1. `python3 tools/story.py init calibrage --rush <fichier>`
  2. Créer un îlot factice couvrant 2-3 s, `cut`, puis `story.py preview calibrage --t 1.0 --text "un sous-titre de test"`
  3. Montrer le PNG : « le texte est bien sous ton visage ? trop haut ? trop bas ? »
  4. Ajuster `caption_y` par pas de 60-80 px, re-preview, jusqu'au « parfait ».
  5. Écrire la valeur dans `story.captionY`, puis `python3 tools/story.py close calibrage --no-archive`.

Garde-fous : jamais au-dessus de 300 (UI Instagram) ni en dessous de 1550 (barre « Répondre »,
et il faut la place d'un B-roll). Entre 1100 et 1300 pour un visage centré.

### Q4 : le cadrage du visage

« Ton visage, tu le veux tel que tu le filmes, ou un peu plus serré ? Un léger zoom (×1,2)
rapproche, ça fait plus "story", et comme il est pris dans ta vidéo d'origine, il n'y a aucune
perte de netteté. Beaucoup de créateurs le préfèrent ; par défaut je laisse tel quel. »
→ `story.faceZoom` (`1.0` tel quel, `1.2` recommandé si oui, jamais au-delà de `1.4` : au-delà
on coupe le front). Le point d'ancrage `story.faceZoomY` reste `0.38` (le visage ne bouge pas de
place) sauf cadrage très haut ou très bas. Si Q3 est calibrée sur un rush, montrer un `preview`
avec le zoom choisi (relancer `cut` du calibrage après avoir écrit `faceZoom`).

### Q5 : une musique de fond (optionnelle)

« Tu veux une musique de fond sur tes stories, très bas sous ta voix, reprise à chaque fois ?
Trois réponses : la musique de tes Reels (si `audio.musicFile` existe dans `brand.config.json`,
la nommer), une autre que tu me donnes maintenant (un MP3, je le range dans `assets/music/`), ou
pas de musique. "Pas maintenant" est une réponse valable : je te la reproposerai en une phrase
à ta prochaine story. »
→ `story.music` :
- un fichier → `{"src": "assets/music/<fichier>", "in": 0, "volume": 0.07}` (`in` = seconde où
  le morceau commence, utile pour sauter une intro ; `volume` 0,07 ≈ 10 dB sous la voix, ne pas
  dépasser 0,12) ; copier le fichier donné dans `assets/music/` du dossier Monteur IA s'il vient
  d'ailleurs ;
- « pas de musique » → `false` (le monteur n'en reparlera jamais) ;
- « pas maintenant » → ne rien écrire (clé absente).
Le monteur ne cherche pas de musique à la place du créateur : pas de catalogue, pas de
génération ; c'est son fichier, donc sa responsabilité sur les droits.

### Q6 : une banque de plans de toi, les B-rolls (optionnelle)

« Pendant que tu parles, je peux insérer en plein écran des plans courts de toi : toi qui
travailles, qui marches, qui fais du sport, ton écran, ton lieu, un beau truc filmé en balade.
Si tu m'en donnes un lot (5 à 8 s chacun, en vertical), je les garde dans une banque décrite,
et je pioche dedans à chaque story, au bon moment. Tu veux ? "Pas maintenant" est OK. »
→ `story.broll` : oui → `true`, et verser les plans donnés tout de suite (`story.py broll apercu`
puis `broll add … --description "…"`, voir skill `story` §4.1) ; non → `false` ; pas maintenant
→ ne rien écrire. Dire que la banque vit dans `assets/b-roll/` et qu'il peut en ajouter à tout
moment (« voilà des plans pour ma banque »).

## Écriture

Récapituler puis écrire dans le `brand.config.json` du dossier Monteur IA (créer la section si
absente, ne toucher à RIEN d'autre dans le fichier ; les clés `music` et `broll` ne s'écrivent
que si le créateur a répondu) :

```json
"story": {
  "captionsSkin": "ombre",
  "captionFont": null,
  "captionSize": 56,
  "captionY": 1180,
  "captionCase": "as-is",
  "captionColor": "#ffffff",
  "faceZoom": 1.0,
  "faceZoomY": 0.38,
  "music": {"src": "assets/music/fond.mp3", "in": 0, "volume": 0.07},
  "broll": true,
  "setupDone": true
}
```

`captionFont` reste `null` sauf demande explicite : le défaut (Inter 900, livré avec le produit
principal) est le bon choix pour 95 % des gens — une graisse forte reste lisible en petit.

Conclure par : « C'est réglé. Dis-moi "on monte une story" avec ta vidéo brute, ou "écris-moi
un script de story" si tu pars de zéro. » (et, si musique ou B-rolls sont restés en « pas
maintenant » : « je te les reproposerai en une phrase, tu décideras à ce moment-là »).
