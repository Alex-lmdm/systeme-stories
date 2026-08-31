---
name: story-script
description: >-
  Écrit le script parlé d'une STORY Instagram face caméra dans la voix du créateur, prêt à lire
  au prompteur (20 à 55 secondes, ton décontracté). Use when the user wants a story script: he
  brings une idée en vrac, une réflexion du jour, un contenu ou une offre à teaser, une nouveauté
  à annoncer — and wants the finished script. Produit du texte ; le montage relève du skill story.
---

# Script de story (voix du créateur, prêt prompteur)

Ce skill écrit le **script parlé d'une story face caméra** : le créateur donne son idée en vrac,
le skill sort un texte qu'il n'a plus qu'à lire au prompteur, naturellement, comme s'il parlait
à ses abonnés. Identité et voix viennent de `brand.config.json` (`brand.firstName`,
`brand.niche`, `brand.language`) et du **profil de voix** du skill `reel-script` (§4, généré par
`/setup` bloc Voix) : si le profil existe, l'utiliser ; sinon, les règles universelles suffisent.

> Une story n'est **pas un Reel**. Le Reel performe devant des inconnus : hook maximal, densité,
> CTA. La story parle à des gens **déjà abonnés** : plus près, plus détendu, plus personnel.
> Même voix, mais on baisse d'un ton.

---

## 0. Quand utiliser ce skill

Dès que le créateur veut une story parlée, quel que soit le point de départ :

1. **Une idée en vrac** — « j'aimerais faire une story où je parle de ça, ça et ça ».
2. **Une réflexion, une anecdote, un moment de vie** à partager avec ses abonnés.
3. **Un contenu à teaser** — un post qui vient de sortir, un article, une vidéo en préparation.
4. **Une offre à vendre en douceur**, ou une nouveauté à annoncer.
5. **Un brouillon** qu'il veut passer à sa sauce.

**Toujours commencer par demander** (une seule question) : « Tu veux partager quoi dans cette
story ? » — et le laisser vider son sac en vrac. C'est la matière première. Ne jamais écrire à
partir de rien.

---

## 1. Les 6 familles de story (choisir avant d'écrire)

La structure et la chute dépendent de la famille. Identifier la bonne dès l'idée reçue :

| Famille | Ce que c'est | La chute type |
|---|---|---|
| **La réflexion** | Une idée, une opinion, un déclic du jour lié à sa niche | Une phrase qui reste en tête, ou une question à l'audience |
| **Les coulisses** | Ce qu'il est en train de construire, tester, vivre | Le teasing : « je t'en reparle très vite » |
| **Le bilan** | Retour chiffré ou honnête sur une période, une expérience | La leçon en une phrase |
| **Le tease de contenu** | Un post/une vidéo vient de sortir ou arrive | Renvoyer vers le contenu (« va voir le dernier post ») |
| **La vente douce** | Parler d'un produit à travers un résultat, une question reçue, une anecdote | Le sticker 🔗 ou « réponds à cette story » |
| **L'annonce** | Une nouveauté, un lancement, un cap franchi | La suite concrète (« ça sort [quand] ») |

Une story = **une seule famille, une seule idée**. Deux idées = deux stories (et c'est tant
mieux : le format se poste plusieurs fois par jour).

---

## 2. Le hook — la première ligne fait tout

Personne ne « scrolle » une story, mais tout le monde peut la passer d'un tap. La première
phrase décide s'ils restent. Deux procédés, à choisir selon le sujet :

**Procédé 1 — la phrase inattendue.** Jamais d'ouverture générique (« Je voulais te parler
de… », « Aujourd'hui je vais te montrer… »). À la place, une affirmation qui surprend, une
question qui pique, ou une anecdote qui démarre au milieu de l'action. L'effet cherché :
« attends… quoi ? ». Des patrons qui marchent :

- « Je vais te dire un truc que personne n'a envie d'entendre… »
- « Tu fais sûrement cette erreur sans même t'en rendre compte. »
- « Personne ne te le dira, mais… »
- « J'ai failli abandonner l'idée… »
- « Je sais que tu vas lever les yeux au ciel, mais… »
- « [Untel] m'a posé une question hier, et j'y pense encore. »

**Procédé 2 — le résultat d'abord.** Commencer par le résultat, jamais par le processus.
Promettre l'arrivée dans les premiers mots, dérouler le chemin ensuite.

- ❌ « J'ai découvert une méthode pour mieux dormir » → ✅ « Je n'ai pas eu besoin de réveil
  depuis 6 mois. »
- ❌ « Voici comment j'ai créé mon outil » → ✅ « J'ai créé un vrai logiciel en 5 jours. Sans
  écrire une ligne de code. »

Écrire **2 ou 3 hooks** sur les deux procédés et laisser le créateur choisir.

---

## 3. Le corps — écrire comme on parle à UN abonné

- **Tutoiement**, comme si on parlait à une seule personne, pas à une audience.
- **Phrases courtes, fragments assumés.** Une idée par ligne. Le point est une respiration.
- **Oralité complète** : élisions (« j'me suis dit », « t'as pas à »), tournures parlées,
  relances (« Bon. », « Bref. », « Et en vrai… »).
- **Le concret plutôt que le concept** : des chiffres réels, des noms, des moments datés
  (« il y a 3 heures », « ce matin »). Jamais de chiffre inventé.
- **L'honnêteté paie** : un aveu (« je m'attendais à galérer », « c'est pas parfait ») rend le
  reste crédible. Une story trop propre sonne comme une pub.
- **Dérouler en escalier** : chaque ligne donne envie de la suivante. Les énumérations courtes
  avec 3-4 items (éventuellement des emojis ✅ en marqueurs) passent très bien à l'oral.
- **Baliser 1-3 mots à accentuer** en gras : ce sont des indices prompteur.

## 4. La chute

Choisie selon la famille (§1). Trois règles transverses :

- **Une seule action demandée**, ou aucune. Une story peut juste... se terminer sur une idée.
- Pour la vente ou le tease : ne **jamais** dire le mot « lien » (à l'écran comme à l'oral,
  l'algorithme n'aime pas ça) → « le 🔗 est sur cette story », « c'est en bio », « réponds-moi
  ici ».
- **La signature de fin** : une formule récurrente pour clore ses stories (une phrase rituelle,
  un « allez, à demain », un geste verbal à soi) crée un rendez-vous reconnaissable et donne
  envie de revenir. Si le créateur en a une (profil de voix, ou demande-lui s'il veut s'en
  créer une), la poser en dernière ligne. Ne jamais lui en inventer une sans lui proposer.

---

## 5. Longueur et format de livraison

- **Cible : 20 à 55 secondes parlées**, soit environ **50 à 140 mots**. Une réflexion simple
  tient en 20-30 s ; un bilan ou une annonce peut aller à 45-55 s. Au-delà, couper en deux
  stories.
- Livrer **en bloc prompteur** : une idée par ligne, saut de ligne aux respirations, jamais de
  paragraphe dense.
- Après livraison, proposer un ajustement en une passe (« plus court ? plus direct ? autre
  hook ? »), pas dix.

---

## 6. Anti-slop (ce qu'il ne faut JAMAIS faire)

- ❌ Pas de tirets longs (—).
- ❌ Pas d'ouverture générique (« Salut à tous », « J'espère que vous allez bien », « Petit
  point rapide »).
- ❌ Pas de ton corporate ou IA (« Découvrez », « N'hésitez pas », « au programme aujourd'hui »).
- ❌ Pas de sur-vente dans une story : le format est un canal de proximité, une vente qui
  s'entend tue la proximité. On raconte, on montre, on propose ; on ne « pitch » pas.
- ❌ Pas de remplissage : si l'idée tient en 25 secondes, la story dure 25 secondes.

---

## 7. Checklist avant de livrer

- [ ] La première ligne surprend ou promet un résultat (jamais d'intro).
- [ ] Une seule idée, une seule famille (§1), une chute adaptée.
- [ ] Ça se lit à voix haute sans buter : fragments, élisions, respirations.
- [ ] Tutoiement, ton d'une conversation avec UN abonné.
- [ ] Chiffres et faits réels uniquement.
- [ ] Le mot « lien » n'apparaît nulle part.
- [ ] 50 à 140 mots, mise en page prompteur, mots à accentuer balisés.
- [ ] Si un profil de voix existe (`reel-script` §4) : le script sonne comme lui.

---

## 8. Et après ?

Le script est validé → le créateur tourne face caméra (résolution max, pas de HDR), puis le
montage passe au skill **`story`** : dérush, sous-titres, B-roll éventuels. S'il veut illustrer
des passages, lui rappeler de **filmer ses plans du quotidien au moment du tournage** (son
écran, son lieu, ce dont il parle) : 3-4 secondes par plan suffisent.
