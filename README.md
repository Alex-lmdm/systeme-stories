# Système Stories : tes stories montées par ton monteur IA

Extension du système **Monteur IA** : elle apprend à ton monteur le format **story Instagram**.

Ta tête en plein écran, naturel. Les blancs et les ratés coupés. Des sous-titres sobres, dans
ton style. Tes plans du quotidien insérés au bon moment, pris dans ta banque de B-rolls (tu lui
donnes des vidéos de toi une fois, il pioche dedans à chaque story) ou à la demande (« cette
vidéo, mets-la quand je parle du resto »). Une musique de fond si tu en veux une, réglée une
fois. Et un générateur de scripts : tu donnes ton idée en vrac, il écrit le script dans ta voix,
tu le lis face caméra, ton monteur fait le reste.

Les Reels font venir tes abonnés. Les stories les transforment en clients : c'est là que tu
crées le lien, que tu teases tes contenus, que tu vends au quotidien sans forcer.

---

## Ce qu'il te faut

Le Système Stories **s'installe dans ton dossier Monteur IA**. Il te faut donc :

- **Monteur IA installé et fonctionnel** (si ce n'est pas fait : c'est son INSTALL.md à lui,
  d'abord) ;
- rien d'autre. Pas de nouvel outil, pas de nouvel abonnement : la story utilise ce que ton
  monteur sait déjà faire (ffmpeg, Whisper), en plus léger.

## Installation (2 minutes)

Ouvre **Claude Code** (ou **Codex**) **dans ton dossier Monteur IA** (ou, dans l'app HyperFrames,
dans l'accueil de Monteur IA), et colle le prompt d'installation : il est dans **[INSTALL.md](INSTALL.md)**.

Puis tape :

```
/setup-stories
```

3 minutes : l'allure de tes sous-titres de story (4 styles au choix), leur position calibrée sur
ton cadrage à toi, ton visage tel quel ou un peu plus serré, et deux options : une musique de
fond et une banque de plans de toi. Tu peux répondre « pas maintenant » : il te les reproposera
en une phrase à ta prochaine story, et n'insistera jamais si tu dis non.

## Comment on s'en sert

Trois phrases à dire à ton monteur, selon où tu en es :

1. **« Écris-moi un script de story »** : tu donnes ton idée en vrac (une réflexion, un
   contenu à teaser, une offre, une annonce), il écrit le script dans ta voix, prêt à lire au
   prompteur. 20 à 55 secondes.
2. **« On monte une story »** : tu donnes ta vidéo brute, il coupe les blancs et les ratés,
   pose les sous-titres, et tu diriges en français.
3. **« Mets cette vidéo quand je parle de… »** : tes plans du quotidien (ton écran, ton lieu,
   ce dont tu parles) passent en plein écran pendant que ta voix continue. Avec une banque de
   B-rolls (« voilà des plans pour ma banque »), il les place lui-même après les sous-titres,
   environ la moitié du temps, et te dit quels plans il lui manque.

Le résultat : un MP4 1080×1920 prêt à poster, copié dans ton dossier Téléchargements.

Dans l'app HyperFrames, chaque story a son propre projet, monté comme un Reel : une conversation
neuve, ta story dans la timeline (sous-titres, plans, musique et bandeaux séparés) pour la
retoucher à la main ou donner tes retours, et le bouton Export pour la sortir. Ce que tu
retouches à la main est gardé, même quand tu redemandes ensuite un changement au monteur.

## FAQ

**En quoi c'est différent de mes Reels ?**
Un Reel est monté pour des inconnus : split-screen, motion design, densité. Une story parle à
tes abonnés : plein écran, naturel, sobre. C'est un autre format, avec ses propres règles, et
c'est exactement ce que cette extension apprend à ton monteur.

**Mes stories vont ressembler à celles des autres ?**
Non. Comme pour Monteur IA, aucune identité n'est livrée : le style de tes sous-titres se
choisit au `/setup-stories`, et le générateur de scripts écrit dans **ta** voix (celle de ton
Empreinte). Ce qui est partagé, c'est la méthode.

**Il me faut du motion design ?**
Non, et c'est le but : une story réussie a l'air spontanée. Pour les rares fois où un bandeau
vaut le coup (un chiffre, des logos), deux patrons prêts à l'emploi sont fournis.

**Ça rallonge mes journées ?**
L'inverse. Un script en 2 minutes, un tournage d'une minute, un montage que tu diriges en
quelques retours. Le format est fait pour être quotidien.
