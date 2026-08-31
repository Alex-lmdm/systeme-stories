---
name: setup-stories
description: >-
  Onboarding du Système Stories : choisir le style des sous-titres de story (skin, taille,
  position calibrée sur un rush test) et l'écrire dans brand.config.json → section `story`.
  Use when the user types /setup-stories, or asks to configure / personnaliser ses stories,
  or at the first story if the `story` section is missing from brand.config.json.
---

# /setup-stories — le style de tes stories, une fois

> **2 minutes, 3 questions.** Une story n'a presque pas de style : c'est voulu, le format doit
> avoir l'air spontané. La seule chose à poser, c'est l'allure des sous-titres — et elle est à
> toi, pas celle d'un autre.

## Principes de fonctionnement

1. **Une question à la fois**, réponse par défaut toujours proposée, « je ne sais pas encore »
   est une réponse valable (les défauts sont bons, on peut monter tout de suite et revenir).
2. **Source de vérité** : `brand.config.json` → section `story`. Si le fichier n'existe pas du
   tout, le produit principal n'est pas installé : arrêter et renvoyer vers son installation.
3. **Aucune écriture avant validation** : récapituler les valeurs, attendre un OK, écrire.
4. **Le pourquoi en une phrase** quand un réglage a un enjeu, jamais un paragraphe technique.
5. Ce skill n'installe rien.

## Les 3 questions

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

## Écriture

Récapituler puis écrire dans `brand.config.json` (créer la section si absente, ne toucher à
RIEN d'autre dans le fichier) :

```json
"story": {
  "captionsSkin": "ombre",
  "captionFont": null,
  "captionSize": 56,
  "captionY": 1180,
  "captionCase": "as-is",
  "captionColor": "#ffffff",
  "setupDone": true
}
```

`captionFont` reste `null` sauf demande explicite : le défaut (Inter 900, livré avec le produit
principal) est le bon choix pour 95 % des gens — une graisse forte reste lisible en petit.

Conclure par : « C'est réglé. Dis-moi "on monte une story" avec ta vidéo brute, ou "écris-moi
un script de story" si tu pars de zéro. »
