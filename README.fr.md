<div align="center">

# 2D Limited MV Studio

**Atelier de clips d'anime 2D · discipline de caméra 2D · une image, une chanson, plusieurs mondes**

*La contrainte est le style.*
*Le monde mute, le personnage ne change pas.*

[![Built with DeepSeek Harness](https://img.shields.io/badge/built%20with-DeepSeek%20Harness-4B4BFF)](#built-with-deepseek-harness)
[![DSH Skill](https://img.shields.io/badge/DSH-agent%20skill-111111)](#install)
[![Target](https://img.shields.io/badge/target-MiniMax%20H3-FF4E8A)](#platforms)
[![Best on](https://img.shields.io/badge/best%20on-小云雀%20%C2%B7%20MiniMax%20Design-3DD6D0)](#platforms)
[![Tests](https://img.shields.io/badge/tests-173%20passing-2E7D32)](#tests)
[![Dependencies](https://img.shields.io/badge/dependencies-zero-8A9BA8)](#requirements)
[![Camera](https://img.shields.io/badge/camera-2D%20limited%20%C2%B7%20no%203D-6B4FBB)](#the-camera-never-leaves-the-paper)

[中文](README.zh-CN.md) · [English](README.md) · [한국어](README.ko.md) · [日本語](README.ja.md) · **Français**

</div>

---

> Un clip n'est pas une suite de jolies images. C'est **un seul corps qui refuse de cesser de
> danser** pendant que le monde autour de lui est redessiné encore et encore — imprimé, déchiré,
> gravé, dissous, désaligné — et à la dernière image, c'est toujours indiscutablement la même
> personne.

**Des clips d'anime 2D en un clic.** Donnez une image de personnage et une chanson ; le skill
renvoie un package de prompts **MiniMax H3** complet et vérifié par machine : la musique coupée à
**14,5 s**, une distribution de mouvements artistiques que le personnage traverse, des objets
lyriques inscrits dans le décor, un langage caméra restreint au vocabulaire officiel de H3, et
chaque segment enchaîné au précédent par sa **véritable dernière image**.

## Pourquoi 14,5 secondes

Le paramètre `duration` de H3 n'accepte que des **entiers**, entre 4 et 15 secondes — et sa grille
d'images (`17k+5`) fait qu'une demande de 15 s délivre en réalité **362 images ≈ 15,083 s**.

Les deux nombres sont donc délibérément séparés :

| | valeur | pourquoi |
|---|---|---|
| coupe musicale | **14,5 s**, calée sur la mesure la plus proche | musical, et c'est l'unité de l'utilisateur |
| `duration` H3 | **15** | le plus petit entier légal dont la durée *livrée* couvre encore la musique |
| livré | **15,083 s** | vérifié sur une sortie H3 réelle |
| utilisable | 14,5 s | les **0,58 s** restantes sont le **chevauchement de couture** — cachez la jointure dans le mouvement le plus rapide |

Un arrondi naïf **tronque silencieusement la musique** (une demande de 6 s ne livre que 5,875 s).
`2d-limited-mv-studio` choisit le plus petit entier dont la durée livrée couvre encore l'audio.

## Le prompt en six sections

Chaque prompt utilise une forme fixe, dans cet ordre :

```text
人物与参考保持一致性：   reference roles + full character canon + drift prohibitions
风格提示词：           2D · limited animation · hand-drawn · flat composition + this segment's movement
内容提示词：           the continuity clause, then shot by shot
integrated_multimodal_description:  how reference, lyrics, music, dance and edit co-operate
overall_soundscape:    ambience and the physical sounds of the body
non_diegetic_music: N/A
```

`N/A` n'est pas un oubli. **Vous avez déjà téléversé la chanson.** Rien ici ne demande à un modèle
de composer de la musique — ce qui évite aussi le mode d'échec officiel : demander de la musique et
l'interdire dans le même prompt.

## La caméra ne quitte jamais le papier

Ce n'est pas une caméra live-action pointée par hasard sur un dessin. **C'est une caméra posée
au-dessus d'une pile de feuilles**, et c'est tout l'enjeu.

Ce que la caméra peut faire est borné à dessein :

- **Pas de caméra 3D.** Pas d'orbite dans l'espace, pas d'élévation de drone, pas de survol, pas de
  travelling en perspective. La profondeur vient des **calques** — papier en premier plan, cel du
  personnage, illustration de fond, surimpression graphique — jamais d'un point de vue mobile.
- **Le mouvement s'écrit en 2D.** Un mouvement de banc-titre fait glisser l'image **à plat, sans
  aucun changement de perspective**. Un glissement de cel laisse le fond parfaitement immobile
  pendant que le personnage bouge. Un parallaxe multiplan sépare les calques par la vitesse —
  la seule « profondeur de champ » honnête dont dispose la 2D.
- **L'animation limitée est la texture.** Images tenues, animation « on twos », mouvement saccadé,
  pose à pose, dessins de flou. La fluidité n'est pas le but ; un dessin qui **se comporte comme un
  dessin** l'est.
- **Le désalignement est un langage, pas une erreur.** Des calques de couleur qui glissent de
  quelques pixels, c'est ainsi que ce skill dit *qu'une identité s'est détachée*.

Le vocabulaire du mouvement est plafonné aux **20 termes officiels** de H3, précisément pour cette
raison — un vocabulaire plus large tenterait la caméra de quitter le papier. Ce qui s'enrichit à la
place, c'est ce que la caméra **regarde** : angle, composition, focus, et ce que le plan révèle.

> **Le test que nous nous imposons :** si vous retiriez tous les mouvements de caméra 3D, le film
> tiendrait-il encore ? Sinon, ce n'était jamais un film 2D.

## Caméra : six couches, un seul vocabulaire

H3 ne reconnaît exactement que **20 mots de mouvement de caméra** — et rien d'autre. « Un travail
caméra plus riche » ne peut donc pas venir de termes inventés ; `crane shot` et `whip pan` ne sont
simplement pas lus. L'enrichissement vient de la **superposition** :

```
taille de plan → angle → composition → focus → mot de mouvement officiel → relation sujet–caméra → ce que le plan révèle
```

| Couche | Nombre | Exemples |
|---|---|---|
| Taille de plan | 10 | très large → très gros plan |
| **Angle** | **12** | bas / haut / hollandais / plongée / contre-plongée extrême / épaule / POV / **frontal à plat (natif 2D)** |
| Composition | 12 | règle des tiers, symétrie, espace négatif, cadre dans le cadre, mise en page affiche |
| Focus | 4 | profond, court, doux, **rack** |
| **Mouvements natifs 2D** | **10** | banc-titre, parallaxe multiplan, glissement de cel, **décalage de repérage**, balayage papier, iris, recadrage dur, écran divisé, flash d'exposition, dérive d'image tenue |
| Relation | 7 | suit / précède / même rythme / observe / révèle / s'oppose / tourne autour |

**La couche manquante n'a jamais été le mouvement — c'était l'*angle*.** Une bibliothèque faite
uniquement de panoramiques et de travellings avant, voilà pourquoi la caméra semblait plate.

Trois règles, toutes vérifiées par machine :

1. **Un plan fixe reçoit une ligne de verrouillage explicite.** Les modèles dérivent, surtout en
   plan large. Chaque `Static Shot` reçoit : « La caméra est entièrement immobile pendant toute la
   scène, le mouvement ne venant que du sujet. »
2. **Tout plan en mouvement doit nommer sa relation au sujet.** Sans cela, les deux mouvements
   tournent sur des horloges séparées — visible en tremblement et en personnage qui semble glisser.
3. **Un travail caméra riche n'est pas un showreel de caméra.** Au plus **la moitié** des plans d'un
   segment peuvent bouger ; les autres sont verrouillés, l'énergie venant des **mouvements natifs
   2D** — une caméra fixe au-dessus d'un dessin vivant.

Les termes live-action servent à *penser* ; tout ce qui est émis est ramené vers les 20 officiels
(`crane_up → Pedestal Up`, `whip_pan → Pan Right + large + fast`). Un test impose que chaque cible
de correspondance soit un vrai terme officiel — le skill ne vous apprendra pas à écrire des mots que
le modèle ignore. Sources et tables complètes : `references/camera-vocabulary.md`.

## Rendre la danse addictive

Une danse devient mémorable non pas en étant complexe, mais en étant **répétée jusqu'à ce qu'on
puisse la faire soi-même**. La couche de mouvement n'est donc pas une liste de mots plus longue :
c'est une **conception de la répétition**.

| Couche | Champ | Ce qu'elle décide |
|---|---|---|
| **Niveau viral** | `seg.motion.viral_level` | à quel point ce segment répète — 0 retenu → 3 obsédant |
| **Planning de répétition** | `seg.motion.*` | longueur de l'unité, longueur du cycle, nombre de répétitions, où ça mute, quelle variation |
| **Hook** | `plan.motion_design.hook_id` | le mouvement signature **unique** du film, obligatoire dans chaque refrain |

Le niveau viral est dérivé segment par segment depuis la musique — et **il monte vers la fin**,
parce que l'addiction se construit puis se déclenche. Même sur un morceau à énergie plate, vous
obtenez couplet retenu → refrain accrocheur → fin obsédante.

```bash
python3 scripts/mvstudio.py motion                          # le menu + la conception courante
python3 scripts/mvstudio.py motion --hook shoulder_pop_8
python3 scripts/mvstudio.py motion --viral 3                # tout le film en obsédant
python3 scripts/mvstudio.py motion --segment C2 --viral 0   # un segment retenu
```

**Huit mouvements de hook**, chacun pour une saveur d'addiction : une tête qui hoche pendant que
le corps reste parfaitement immobile ; huit haussements d'épaules où *le compte est la blague* ;
un stomp qui marque une pause plus longue à chaque fois ; une pulsation de squat dont le
squash-and-stretch est la route la plus rapide vers une maladresse attendrissante ; un demi-tour
qui s'arrête court trois fois puis sur-livre.

**Cinq variations de répétition** — accent croissant, double tempo, demi-tempo, canon décalé d'un
demi-temps, et *supprimer la dernière répétition* (le hook que vous fredonniez s'arrête à moitié).
La règle dure : **une mutation varie le même mouvement ; elle ne le remplace jamais.** Remplacez le
mouvement et la mémoire se casse.

Le planning est **piloté par la grille de temps**, pas par un « répéter 4 fois » deviné — la même
prémisse que partagent tous les modèles publiés de génération de danse conditionnée par la musique.
Nous prenons le principe et aucune des dépendances ; le pipeline reste sans dépendance.

## Le dernier geste

Une pose debout est la façon la plus paresseuse de finir un film. Le dernier geste est ce que le
public emporte. `2d-limited-mv-studio` propose **huit fins dirigeables**, classées selon le
caractère de fin de la musique elle-même :

| id | Fin | Ce qui se passe |
|---|---|---|
| `jump_freeze` | **Saut et gel** | saut complet, gel au sommet, le fond est retiré et il ne reste qu'un contour décalé |
| `reach_and_crack` | **Tendre et fissurer** | elle pousse un bout de doigt dans l'objectif ; toute l'image se fissure comme du verre, laissant passer une lumière blanche |
| `swipe_to_black` | **Balayage au noir** | le bras balaie l'objectif, l'écran coupe au noir exactement sur le temps fort, une rémanence demeure |
| `frame_drop_vanish` | **Disparition image par image** | les bras partent, puis le torse, le mouvement continue, jusqu'à ce qu'il ne reste qu'une ligne de contour |
| `misregistration_exit` | **Sortie par désalignement** | désimpression par couches : couleur → trait → rien que les repères de repérage |
| `spin_to_line` | **Tourner jusqu'à la ligne** | en pleine rotation le corps se replie en une seule ligne verticale, puis est effacé vers le haut |
| `paper_tear_exit` | **Sortie par déchirure** | le cadre se déchire au milieu ; elle danse hors de la déchirure |
| `look_back_fade` | **Regard en arrière, fondu** | le seul arrêt complet du film — elle se retourne, l'image s'estompe en vieille photographie |

Chaque fin préserve l'identité. **Ce qui disparaît, c'est le dessin, jamais la personne.**

## Chaînage par dernière image

```
C1 ──sa dernière image──▶ C2 ──sa dernière image──▶ C3 ──▶ C4
```

La **dernière image** du segment précédent devient la **première image** du suivant.
C'est la seule preuve de continuité qu'un modèle ne peut pas contester : il regarde la même image.

Deux contraintes dures en découlent, et l'une est une vraie tension de conception qui mérite d'être
nommée :

1. **Le changement de style se produit *à l'intérieur* du segment.** Une première image chaînée
   entraîne le style du segment précédent. Plutôt que de choisir entre « connecté » et « un nouveau
   style à chaque segment », `2d-limited-mv-studio` fait les deux : `0–1,5 s` garde le style et la
   pose précédents, puis le monde bascule **dans le même plan**. La transition devient un événement
   au lieu d'une coupe.
2. **Ne changez pas la pose pendant le chaînage.** Un rapport de terrain tiers (non vérifié — voir
   `references/platform-playbook.md`) situe le déchirement des membres au-delà de **12 % de la
   hauteur d'image** de déplacement vertical entre les deux images chaînées. Nous prenons le côté
   conservateur.

Échelle de capture d'image : `ffmpeg` → **AVFoundation de macOS** (sans installation ; vérifié en
extrayant une image 2560×1440 à 15,034 s) → export depuis la timeline de la plateforme.
Il ne fait jamais passer une première image pour une dernière.

## Chaque étape vous attend

```bash
python3 scripts/mvstudio.py confirm --status
python3 scripts/mvstudio.py confirm --step canon --note "人设没问题"
python3 scripts/mvstudio.py confirm --all
```

Les points de confirmation sont écrits dans `workspace/confirmations.json` — auditables,
révocables :

```
gate → analyze → lyrics → canon → threeview → styles → segments
     → prompt-01 … prompt-N      chaque prompt
     → chain-01  … chain-N       la sortie et l'image finale de chaque segment
     → ending → render → validate → pack
```

`render` et `pack` **refusent de continuer (exit 5)** tant que quelque chose n'est pas confirmé,
sauf si vous passez `--unattended`. (La revue pratique de MiniMax Design elle-même ne décrit que
deux actions pour l'utilisateur : *« confirmer, et attendre »*. Le rythme correspond.)

## Ce qui est vérifié par machine

Pas « ça a l'air bien » — les choses qui peuvent être affirmées :

```
segments = ceil(durée / 14,5), chacun ≤ 15 s, contigus
chaque mot de caméra appartient au vocabulaire officiel de 20 termes de H3
chaque élément lyrique du fond est dérivable des paroles de ce segment
≥ 3 mouvements artistiques distincts sur le film, jamais deux fois le même d'affilée
six sections présentes, dans l'ordre, zéro Markdown, ≤ 7000 caractères par prompt
aucune instruction de génération musicale nulle part
les six champs de canon critiques au rendu sont remplis
```

## Démarrage rapide

```bash
git clone <this repo> ~/Desktop/2d-limited-mv-studio && cd ~/Desktop/2d-limited-mv-studio

python3 scripts/mvstudio.py doctor          # vérification de l'environnement
python3 scripts/mvstudio.py all             # pipeline déterministe
python3 scripts/mvstudio.py endings         # choisir le dernier geste
python3 scripts/mvstudio.py confirm --all   # confirmer chaque étape
python3 scripts/mvstudio.py render          # package en six sections
python3 scripts/mvstudio.py validate        # doit sortir en 0
python3 scripts/mvstudio.py pack --platform xiaoyunque
```

Fonctionne depuis n'importe quel répertoire avec `--project <répertoire inscriptible>`. Si le
dossier du skill est lui-même en lecture seule (installation partagée, session sandboxée), la CLI
vous indique exactement quelle commande lancer à la place.

## Plateformes

**Idéal sur Xiaoyunque et MiniMax Design** — ce skill est réglé pour leurs fonctions de découpe,
d'image de début/fin et de montage IA. **D'autres plateformes fonctionnent aussi** : tout ce qui
accepte un asset téléversé plus un prompt par segment peut exécuter le package ; avec
`--platform generic` vous obtenez un mode opératoire agnostique du canevas.

| | Xiaoyunque | MiniMax Design |
|---|---|---|
| découpe | storyboard intelligent / coupe sur timeline | montage IA (langage naturel) — « couper les 2 dernières secondes » vérifié |
| première image | mode première/dernière image | dernière image comme référence de première ; ou poser d'abord dans l'étage de réalisation 3D |
| verrou d'identité | bibliothèque de personnages / retouche locale | centre d'assets (ancre personnage) |
| rythme | soumettre prompt par prompt | l'Agent **redemande d'abord**, puis agit |

La répartition : **le skill coupe la musique, la plateforme coupe l'image.** Manuel complet, pièges
de chaque plateforme, provenance et confiance de chaque affirmation :
`references/platform-playbook.md`.

## Installation

<a id="install"></a>

```bash
bash install-to-dsh.sh ~/my-project    # lien symbolique vers <project>/.dsh/skills/2d-limited-mv-studio
```

## Construit avec DeepSeek Harness

C'est un **skill d'agent pour DeepSeek Harness (DSH)** — composé pour que tout agent DSH puisse le
monter, et tout aussi utilisable depuis Claude Code, Codex ou Cursor, car ce n'est que `SKILL.md`
plus du Python sans dépendance.

**Tags communautaires :** `deepseek-harness` `dsh` `agent-skill` `ai-video` `minimax-h3`
`music-video` `prompt-engineering` `2d-animation` `lyrics` `art-direction` `xiaoyunque`

## Prérequis

- **Python ≥ 3,7**, bibliothèque standard uniquement. Tout le pipeline fonctionne avec **zéro
  dépendance tierce** (testé sur le Python système 3.9.6).
- Optionnels, chacun strictement additif :
  - `ffmpeg` **ou** `afconvert` de macOS — couper de l'audio non WAV
  - **AVFoundation** de macOS (intégré) — extraire des dernières images exactes
  - `numpy` / `librosa` — analyse BPM et spectrale plus fine
  - une bibliothèque de styles artistiques (147 mouvements avec prompts en couches) — chemin
    configurable ; sans elle, le skill se rabat sur une palette média intégrée et le dit

## Tests

<a id="tests"></a>

```bash
python3 -m unittest discover -s tests -t tests
# Ran 173 tests … OK
```

173 tests, zéro dépendance, dont une exécution de bout en bout (assets synthétiques → `all` → le
brouillon doit refuser de rendre → remplir → rendre → valider → packager) et un **garde-fou de
confidentialité** qui fait échouer le build si un nom propre au projet, un jeu de prompts privé ou
un chemin local codé en dur entre dans le package.

## Structure du dépôt

```
2d-limited-mv-studio/
├── SKILL.md                    the skill itself — workflow, hard gates, DoD
├── config/defaults.yaml        tunable parameters (directorial judgement is not here)
├── scripts/
│   ├── mvstudio.py                single entry point, 15 subcommands
│   └── lib/
│       ├── beats.py            beat grid · bar snapping · 14.5 s segmentation · H3 duration contract
│       ├── slicer.py           actually cuts audio (ffmpeg → afconvert → wave)
│       ├── h3render.py         six-section renderer (mv / ref / i2va / t2va)
│       ├── chain.py            last-frame chaining across segments
│       ├── frames.py           frame capture (ffmpeg → AVFoundation → platform export)
│       ├── endings.py          eight directable endings
│       ├── motion.py           魔性动作：viral level · beat-driven repeat schedule · hook
│       ├── camera.py           six-layer camera vocabulary (angles, framing, 2D moves)
│       ├── styleroutes.py      six fusion routes through art history
│       ├── threeview.py        character turnaround sheet
│       ├── confirm.py          per-step confirmation ledger
│       ├── platforms.py        小云雀 / MiniMax Design adapters
│       ├── gates.py            the machine-checkable gates
│       ├── director.py         draft + worksheet
│       ├── materials.py        material & duration gates
│       ├── canon.py            character canon scaffold
│       ├── pack.py             the upload package
│       ├── music.py            audio analysis (librosa → numpy → stdlib)
│       ├── audioprobe.py       ffprobe → afinfo → pure Python
│       ├── imgprobe.py         image probe & palette, pure Python
│       ├── lyricsrc.py         lyrics sources (embedded / lrc / srt / vtt / txt / ASR)
│       ├── artbridge.py        bridge to the art-style library
│       ├── miniyaml.py         tiny YAML reader (no PyYAML)
│       └── common.py           paths, config, logging, degradation
├── references/                 method, vocabularies, official H3 guides
└── tests/                      173 tests, zero dependencies
```

## Notes de conception

Quelques décisions qui n'étaient pas évidentes, et le raisonnement derrière :

**Le canon du personnage vit dans l'emplacement officiel, pas dans le corps du prompt.**
Une méthode source insiste pour que chaque prompt réénonce le canon complet ; une autre insiste
pour ne jamais décrire l'apparence dans le corps, car le texte et l'image de référence se
combattent et le modèle dérive. Les deux ont raison, à des endroits différents. Le mode référence
complète de H3 a `subject_definitions` et `retention_analysis` — les emplacements que le format
réserve exactement à cela. Le canon y va ; le corps reste propre.

**Dégrader bruyamment, jamais en silence.**
Pas de `ffmpeg` ? Vous recevez une feuille de coupe précise à la milliseconde et l'instruction de
la couper vous-même — pas un résultat silencieusement faux. Pas d'extracteur d'images ? Une erreur
et une route vers l'export de la plateforme elle-même. Chaque repli est consigné avec son impact.

**La couleur n'est pas une décoration.**
Le choix du mouvement artistique est indexé depuis les paroles, et chaque élément de fond doit
pouvoir être rattaché à la ligne qu'il accompagne. Un ornement aléatoire est un échec de validation,
pas un style.

## Licence

MIT — voir [LICENSE](LICENSE).

<div align="center">

*Un seul corps. Plusieurs mondes. Le même visage à la dernière image.*

</div>
