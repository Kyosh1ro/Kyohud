# Kyosh1ro HUD — guide de travail

## But du projet

Kyosh1ro HUD est un mod PAYDAY 2 chargé par SuperBLT. Il affiche autour du réticule :

- les buffs temporaires actuellement actifs, avec leur temps restant ;
- les éliminations du joueur local, sous forme de killfeed ;
- les éléments à la suite les uns des autres sur des arcs de cercle.

Le mod doit rester compatible avec le HUD du jeu et pouvoir cohabiter avec VanillaHUD+.

## Environnement d'exécution

Il n'y a ni étape de compilation, ni gestionnaire de dépendances, ni suite de tests automatisés. Les scripts Lua sont chargés directement par SuperBLT selon les hooks déclarés dans `mod.txt`.

Le code s'appuie sur les API globales de PAYDAY 2/SuperBLT (`Hooks`, `managers`, `TimerManager`, `MenuHelper`, `DB`, `tweak_data`, etc.). Garder une syntaxe compatible avec la version de Lua embarquée par le jeu et protéger les accès fragiles aux API du moteur avec `pcall` quand c'est pertinent.

Tous les modules partagent la table globale `Kyosh1roHUD`, abrégée localement en `KH`. Ne pas créer un second état global concurrent.

## Architecture

| Fichier | Responsabilité |
| --- | --- |
| `mod.txt` | Métadonnées SuperBLT et association entre hooks du jeu et scripts du mod. |
| `ky_buff_catalog.lua` | Source de vérité des catégories, définitions d'icônes, valeurs `default_show` et correspondances upgrade → buff. Son garde empêche une réinitialisation lors de chargements multiples. |
| `ky_hooks.lua` | Détecte l'activation et la désactivation des upgrades temporaires via `PlayerManager`, résout leur durée puis appelle `KH:add_buff` ou `KH:remove_buff`. |
| `ky_killfeed.lua` | Observe `CopDamage:die`, garde uniquement les kills du joueur local ou de ses projectiles et appelle `KH:add_kill`. Ce hook doit rester associé à `lib/units/enemies/cop/copdamage`. |
| `ky_buffhud.lua` | État actif, résolution des textures, création du panneau, calcul des positions sur les arcs et rendu. Contient aussi les outils de simulation. |
| `ky_options.lua` | Valeurs par défaut, lecture/écriture de `SavePath/kyosh1ro_hud_settings.json`, callbacks et menus SuperBLT. |
| `ky_localization.lua` | Fallbacks intégrés et chargement des traductions anglaise/française. Capture immédiatement `ModPath` car SuperBLT peut ensuite écraser ce global. |
| `loc/english.json`, `loc/french.json` | Libellés visibles dans le menu. |
| `2026_04_04_log.txt` | Ancien journal de diagnostic ; il ne participe pas à l'exécution. |

## Flux des données

### Buffs

1. `PlayerManager:activate_temporary_upgrade` déclenche le PostHook de `ky_hooks.lua`.
2. `KH.UPGRADE_TO_BUFF` convertit le nom interne de l'upgrade en identifiant du catalogue.
3. La durée restante est lue depuis `_temporary_upgrades`, puis depuis `upgrade_value`, avec le réglage utilisateur comme dernier recours.
4. `KH:add_buff` applique les filtres, résout l'icône et écrit une entrée dans `KH._buffs`, indexée par identifiant.
5. `KH:draw` purge les entrées expirées, trie les buffs et les dessine sur l'arc.

Une réactivation du même buff doit rafraîchir son timer sans dupliquer son entrée. Quand l'ordre d'arrivée est utilisé pour le rendu, conserver sa position d'origine lors de ce rafraîchissement.

### Kills

1. `CopDamage:die` déclenche le PostHook de `ky_killfeed.lua`.
2. Le hook rejette les kills qui ne proviennent pas du joueur local ou d'un objet lancé par lui.
3. `KH:add_kill` ajoute une entrée chronologique dans `KH._kills`, avec une limite de 20 entrées.
4. `KH:draw` purge puis dessine les kills sur leur arc dédié.

## Invariants du rendu en arc

Le centre de référence est le centre du panneau HUD. Pour un angle `a` et un rayon `r`, le point calculé est :

```text
x = centre_x + cos(a) * r
y = centre_y - sin(a) * r
```

Le signe négatif sur `sin` vient de l'axe vertical de l'interface, orienté vers le bas.

L'arc des buffs utilise les réglages `angle_start`, `angle_end` et `circle_radius`. Par défaut il va de 315° à 90° dans le sens des angles croissants, en traversant 360°/0°. Les icônes sont centrées sur les points calculés et leur timer est placé dessous.

Les éléments doivent être séquentiels : le premier commence à `angle_start`, puis chaque élément avance d'un pas angulaire dérivé de sa taille et d'une marge. Si tous les éléments ne tiennent pas, adapter l'espacement sans perdre silencieusement des entrées. Un buff qui expire peut libérer sa place et faire avancer les suivants vers le début de l'arc.

Le killfeed utilise actuellement un arc fixe de 250° à 290°, sur un rayon extérieur (`circle_radius + icon_size + 20`). Si ce comportement devient configurable, ajouter les réglages, leur persistance et les traductions dans la même branche.

Le panneau est vidé puis reconstruit environ toutes les 0,05 seconde. Éviter les allocations ou logs permanents inutiles dans `KH:draw` ; tout diagnostic temporaire doit être clairement marqué et retiré une fois le problème validé.

## Ajouter ou modifier un buff

Vérifier ensemble les éléments suivants :

1. Ajouter ou corriger l'entrée de `KH.BUFF_MAP` avec son atlas, ses coordonnées, sa catégorie et `default_show`.
2. Ajouter la correspondance dans `KH.UPGRADE_TO_BUFF` si le nom envoyé par PAYDAY 2 diffère de l'identifiant d'affichage.
3. Confirmer que l'évènement concerné passe réellement par `activate_temporary_upgrade`. Les buffs provenant d'un autre mécanisme nécessitent un hook adapté ; ne pas simuler leur détection dans le rendu.
4. Ajouter les clés `ky_opt_buff_<id>` et `ky_opt_buff_<id>_desc` aux deux fichiers de langue pour un libellé soigné. Les fallbacks dynamiques évitent seulement une erreur de menu.
5. Tester l'activation, le rafraîchissement, la désactivation, l'expiration et les filtres de catégorie/individuels.

## Réglages et menus

Quand un réglage est ajouté ou renommé, mettre à jour dans la même modification :

- `KH._defaults` et la fusion dans `KH.Load` ;
- le callback approprié ;
- l'élément de menu et ses bornes ;
- les fallbacks de localisation ;
- `loc/english.json` et `loc/french.json` ;
- le rendu qui consomme la valeur.

Ne pas remplacer les tests explicites `value ~= nil` par l'idiome Lua `x and y or default` pour les booléens : une valeur sauvegardée à `false` serait perdue.

Le menu principal est le seul construit avec `MenuHelper:BuildMenu`. Les sous-menus sont créés par `deep_clone` à cause de la limitation SuperBLT documentée dans `ky_options.lua`. Préserver ce fonctionnement sauf si un test en jeu démontre qu'une autre approche est sûre.

## Vérification

Avant de considérer une modification terminée :

1. Valider que `mod.txt` et les JSON de `loc/` sont syntaxiquement corrects.
2. Relire le diff pour repérer un changement involontaire de fins de ligne ou de fichier utilisateur.
3. Lancer PAYDAY 2 avec SuperBLT et ouvrir les options de Kyosh1ro HUD.
4. Utiliser **Debug: Simulate** pour vérifier plusieurs icônes, les timers, l'ordre, les deux arcs et les différentes valeurs de rayon/taille/angles.
5. Utiliser **Debug: Clear**, puis tester en partie un vrai buff, son rafraîchissement et un kill direct ainsi qu'un kill par projectile si le hook concerné a changé.
6. Contrôler le journal SuperBLT pour les erreurs `[Kyosh1ro HUD]` et supprimer les traces de debug temporaires avant livraison.

Une vérification statique ne remplace pas le test en jeu, car les classes et textures PAYDAY 2 ne sont pas disponibles hors du moteur.

## Git et branches

- Travailler sur une branche dédiée par sujet : `fix/<sujet-court>` pour une correction et `feature/<sujet-court>` pour une nouvelle fonctionnalité.
- Choisir le préfixe selon l'objectif principal de la branche. La documentation directement liée à une correction ou une fonctionnalité reste sur la même branche.
- Faire `git status --short --branch` avant toute modification et préserver les changements locaux déjà présents.
- Ne jamais inclure dans un commit une modification utilisateur préexistante sans l'identifier clairement.
- Garder les commits ciblés : documentation, correction de rendu, catalogue ou options doivent rester séparables quand cela aide la revue.
- Ne pas pousser, fusionner, réécrire l'historique ou supprimer une branche sans demande explicite.
- Avant une proposition de fusion, indiquer les tests réellement effectués et ceux qui nécessitent encore PAYDAY 2.

## Points d'attention connus

- Les numéros de version présents dans `mod.txt` et certains en-têtes Lua ne sont pas toujours alignés. Ne pas les modifier au passage ; les harmoniser seulement dans une tâche de versionnage dédiée.
- Les textures peuvent dépendre d'atlas ou de DLC. `ky_buffhud.lua` doit conserver une texture de repli quand une ressource n'existe pas.
- L'ordre de chargement des hooks compte. Déclarer un hook dans le contexte où la classe du jeu existe déjà.
- Les appels de rendu arrivent fréquemment. Les opérations lourdes, les scans de catalogue et les logs détaillés ne doivent pas être exécutés à chaque frame.
