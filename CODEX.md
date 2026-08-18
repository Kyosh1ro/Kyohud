# Kyosh1ro HUD — dossier technique

État fonctionnel attendu au 17 août 2026.

## Résumé

Kyosh1ro HUD est un mod PAYDAY 2 autonome chargé par SuperBLT. Il affiche :

- les buffs actifs et leur temps restant dans une rangée horizontale configurable ;
- les derniers kills du joueur dans une rangée tactique horizontale sous le viseur ;
- un bandeau temporaire pour les séries de kills.

Le mod reprend des identifiants et conventions d'icônes de VanillaHUD+, sans dépendre de VanillaHUD+ à l'exécution.

## Architecture effective

### Observation du jeu

- `ky_hooks.lua` observe les upgrades temporaires et d'autres sources de buffs prises en charge.
- `ky_playerdamage.lua` observe les évènements liés aux dégâts du joueur quand ils alimentent les buffs.
- `ky_killfeed.lua` observe `CopDamage:die` et attribue les kills directs ou les projectiles au joueur local.
- Ces modules appellent `KH:add_buff`, `KH:remove_buff` et `KH:add_kill`.

### Présentation et configuration

- `ky_buff_catalog.lua` est la source de vérité des buffs, catégories, icônes et correspondances.
- `ky_buffhud.lua` conserve l'état actif et dessine les buffs, le killfeed et le bandeau de série.
- `ky_options.lua` gère les valeurs par défaut, la persistance et les menus.
- `ky_localization.lua` et `loc/` fournissent les fallbacks et les traductions.

Tous les modules partagent la table globale `Kyosh1roHUD`, abrégée en `KH`.

## Cycle de vie des buffs

Le flux principal est :

```text
évènement PAYDAY 2
    -> résolution de l'identifiant du buff
    -> KH:add_buff / KH:remove_buff
    -> KH._buffs
    -> rangée horizontale
```

`KH:add_buff` indexe les entrées par identifiant. Une nouvelle activation du même buff rafraîchit son timer sans créer de doublon. `order_t` conserve sa position relative lors du rafraîchissement.

## Rendu des buffs

La position de référence est exprimée en pourcentage du panneau :

```text
x = largeur_panneau * buff_position_x / 100
y = hauteur_panneau * buff_position_y / 100
```

Les valeurs par défaut `50` et `85` placent le centre de la rangée en bas au centre. Les buffs sont triés par ordre d'arrivée, placés de gauche à droite et recentrés quand une entrée expire. Le calcul resserre l'espacement si nécessaire afin de conserver toute la rangée dans le panneau.

Les anciens réglages `angle_start` et `angle_end` ne pilotent plus le rendu. Une résolution de conflit ne doit jamais réintroduire le calcul circulaire à leur place.

## Rendu du killfeed

`KH:add_kill` conserve de 1 à 3 entrées selon `killfeed_size`. Le rendu les place sur une seule rangée :

- le kill le plus ancien visible à gauche ;
- le kill le plus récent à droite ;
- largeur des cartes et espacement adaptés à la largeur du panneau ;
- bandeau de série centré au-dessus de la rangée ;
- `circle_radius` conservé comme décalage vertical historique du bloc.

Les kills partagent actuellement le réglage `buff_duration` pour leur durée d'affichage.

## Menus et persistance

Les paramètres sont enregistrés dans `SavePath/kyosh1ro_hud_settings.json`. Toute nouvelle option doit être ajoutée ensemble aux valeurs par défaut, au chargement, au callback, au menu, aux fallbacks et aux deux fichiers de langue.

Les tests explicites `value ~= nil` sont nécessaires pour conserver les booléens sauvegardés à `false`. Le menu principal est construit avec `MenuHelper:BuildMenu` ; les sous-menus restent créés par `deep_clone`.

## Coût et limites

Le panneau est vidé puis reconstruit environ toutes les 0,05 seconde. Les scans lourds, allocations inutiles et logs permanents sont donc à éviter dans `KH:draw`.

Les classes et textures PAYDAY 2 ne sont pas disponibles hors du moteur. Une validation statique peut vérifier la syntaxe Lua et JSON, mais le rendu, les hooks, les textures et la compatibilité VanillaHUD+ doivent être validés en jeu.

## Discipline de merge

La création d'une branche destinée à `main` suit obligatoirement cette séquence :

```text
git fetch origin --prune
git switch -c <branche> origin/main
git merge-base HEAD origin/main
git rev-parse origin/main
```

Les deux dernières commandes doivent renvoyer le même commit avant toute modification. Si `git fetch` échoue ou si les commits diffèrent sur une branche nouvellement créée, le travail doit s'arrêter jusqu'à correction de la base. Un `main` local en retard ne doit jamais servir de base ni être fusionné dans une branche récente.

En cas de conflit dans `ky_buffhud.lua`, comparer les trois versions — base commune, cible et branche — au lieu de choisir le fichier complet d'un seul côté. Après résolution, vérifier au minimum :

- `compute_horizontal_positions` et les options `buff_position_x` / `buff_position_y` ;
- `killfeed_size` et sa limite de 1 à 3 ;
- la rangée horizontale du killfeed ;
- les JSON et `mod.txt` ;
- le diff final, pour détecter toute réintroduction du rendu circulaire.

## Vérification en jeu

Utiliser **Debug: Simulate** pour contrôler plusieurs buffs, les timers, l'ordre, les deux rangées horizontales, les largeurs d'écran et les positions configurables. Utiliser ensuite **Debug: Clear**, puis tester un vrai buff, son rafraîchissement, un kill direct et un kill par projectile.
