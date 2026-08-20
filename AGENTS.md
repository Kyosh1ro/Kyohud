# Kyosh1ro HUD — guide de travail

## But du projet

Kyosh1ro HUD est un mod PAYDAY 2 chargé par SuperBLT. Il affiche autour du réticule :

- les buffs temporaires actuellement actifs, avec leur temps restant ;
- les éliminations du joueur local, sous forme de killfeed ;
- les buffs à la suite les uns des autres sur une rangée horizontale configurable ;
- le killfeed tactique sous le viseur.

Le mod doit rester compatible avec le HUD du jeu et pouvoir cohabiter avec VanillaHUD+.

## Environnement d'exécution

Il n'y a ni étape de compilation, ni gestionnaire de dépendances, ni suite de tests automatisés. Les scripts Lua sont chargés directement par SuperBLT selon les hooks déclarés dans `mod.txt`.

Le code s'appuie sur les API globales de PAYDAY 2/SuperBLT (`Hooks`, `managers`, `TimerManager`, `MenuHelper`, `DB`, `tweak_data`, etc.). Garder une syntaxe compatible avec la version de Lua embarquée par le jeu et protéger les accès fragiles aux API du moteur avec `pcall` quand c'est pertinent.

Tous les modules partagent la table globale `Kyosh1roHUD`, abrégée localement en `KH`. Ne pas créer un second état global concurrent.

## Références locales de développement

- Les annotations des types du moteur Diesel et des fonctions Lua de PAYDAY 2 sont disponibles dans `G:\PD2-Modding-Docs\pd2-code-doc`. Les consulter pour vérifier les signatures et les objets du moteur, notamment `PlayerManager`, `CopDamage`, `CivilianDamage`, `Panel`, `Bitmap` et `Text`.
- L'implémentation SuperBLT effectivement installée est disponible dans `G:\SteamLibrary\steamapps\common\PAYDAY 2\mods\base`. La privilégier pour confirmer le comportement de `Hooks`, `MenuHelper`, du chargement des mods et de la localisation.
- Ces dossiers sont des références de développement uniquement : ne pas les charger à l'exécution, les copier dans le mod ou les inclure dans une publication.
- Les annotations documentent surtout les signatures. Pour les champs privés, la sémantique réseau et les comportements dépendant du moteur, confronter la documentation au code du jeu disponible et valider en jeu.

## Architecture

| Fichier | Responsabilité |
| --- | --- |
| `mod.txt` | Métadonnées SuperBLT et association entre hooks du jeu et scripts du mod. |
| `ky_buff_catalog.lua` | Source de vérité des catégories, définitions d'icônes, valeurs `default_show` et correspondances upgrade → buff. Son garde empêche une réinitialisation lors de chargements multiples. |
| `ky_hooks.lua` | Détecte l'activation et la désactivation des upgrades temporaires via `PlayerManager`, résout leur durée puis appelle `KH:add_buff` ou `KH:remove_buff`. |
| `ky_killfeed.lua` | Observe `CopDamage:die` côté hôte et `PlayerManager:on_killshot` côté client, puis transmet les kills locaux au calcul partagé du killfeed. Le script doit rester associé aux deux contextes dans `mod.txt`. |
| `ky_buffhud.lua` | État actif, résolution des textures, création du panneau, calcul de la rangée horizontale des buffs et rendu du killfeed. Contient aussi les outils de simulation. |
| `ky_options.lua` | Valeurs par défaut, lecture/écriture de `SavePath/kyosh1ro_hud_settings.json`, callbacks et conversion des définitions JSON en menus SuperBLT. |
| `menu/menu.json`, `menu/buffs.json` | Structure fixe du menu principal et du sous-menu de catégories de buffs ; les buffs individuels restent générés depuis le catalogue. |
| `ky_localization.lua` | Fallbacks intégrés et chargement des traductions anglaise/française. Capture immédiatement `ModPath` car SuperBLT peut ensuite écraser ce global. |
| `loc/english.json`, `loc/french.json` | Libellés visibles dans le menu. |
| `changelog.txt` | Historique utilisateur numéroté des commits directs et des pull requests fusionnées dans `main`. |
| `2026_04_04_log.txt` | Ancien journal de diagnostic ; il ne participe pas à l'exécution. |

## Flux des données

### Buffs

1. `PlayerManager:activate_temporary_upgrade` déclenche le PostHook de `ky_hooks.lua`.
2. `KH.UPGRADE_TO_BUFF` convertit le nom interne de l'upgrade en identifiant du catalogue.
3. La durée restante est lue depuis `_temporary_upgrades`, puis depuis `upgrade_value`, avec le réglage utilisateur comme dernier recours.
4. `KH:add_buff` applique les filtres, résout l'icône et écrit une entrée dans `KH._buffs`, indexée par identifiant.
5. `KH:draw` purge les entrées expirées, trie les buffs et les dessine sur la rangée horizontale.

Une réactivation du même buff doit rafraîchir son timer sans dupliquer son entrée. Quand l'ordre d'arrivée est utilisé pour le rendu, conserver sa position d'origine lors de ce rafraîchissement.

### Kills

1. Sur l'hôte, `CopDamage:die` déclenche le PostHook historique de `ky_killfeed.lua`.
2. Sur un client, `PlayerManager:on_killshot` fournit la notification du kill obtenu par le joueur local, indépendamment de l'autorité de l'hôte sur la mort de l'unité.
3. Le chemin hôte rejette les kills qui ne proviennent pas du joueur local ou d'un objet lancé par lui ; le chemin client est déjà limité aux kills locaux par `on_killshot`.
4. Le calcul partagé déduplique l'unité, détermine son nom et son score, puis `KH:add_kill` ajoute une entrée chronologique dans `KH._kills`, avec une limite configurable de 1 à 3 entrées.
5. `KH:draw` purge puis dessine les kills dans la rangée tactique horizontale dédiée.

## Invariants du rendu

La position de référence des buffs est exprimée en pourcentage du panneau HUD :

```text
x = largeur_panneau * buff_position_x / 100
y = hauteur_panneau * buff_position_y / 100
```

Par défaut, `buff_position_x = 50` et `buff_position_y = 85` placent la rangée en bas au centre, indépendamment de la résolution. Ces valeurs représentent le centre de la rangée, pas son coin supérieur gauche.

Les icônes sont centrées verticalement sur cette position et leur timer est placé dessous. La rangée complète doit rester dans le panneau : près d'un bord, décaler son point de départ pour conserver tous les cadres et timers visibles.

Les éléments doivent être séquentiels de gauche à droite. Le pas horizontal dépend de la taille de l'icône, de son cadre et d'une marge. Si tous les éléments ne tiennent pas, adapter l'espacement sans perdre silencieusement des entrées. Un buff qui expire peut libérer sa place et recentrer les autres autour de la position configurée.

Le killfeed utilise une rangée tactique horizontale sous le viseur, limitée à 1-3 entrées. L'ordre est chronologique de gauche à droite : le kill le plus ancien visible reste à gauche et le plus récent s'ajoute à droite. La rangée est centrée et doit se resserrer pour rester dans le panneau. Le bandeau de série reste centré au-dessus. Le réglage historique `circle_radius` sert de décalage vertical de ce bloc.

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
4. Utiliser **Debug: Simulate** pour vérifier plusieurs icônes, les timers, l'ordre, les deux rangées horizontales, l'ajout d'un kill à droite et différentes valeurs de position X/Y, de taille et de largeur d'écran.
5. Utiliser **Debug: Clear**, puis tester en partie un vrai buff, son rafraîchissement et un kill direct ainsi qu'un kill par projectile si le hook concerné a changé.
6. Contrôler le journal SuperBLT pour les erreurs `[Kyosh1ro HUD]` et supprimer les traces de debug temporaires avant livraison.

Une vérification statique ne remplace pas le test en jeu, car les classes et textures PAYDAY 2 ne sont pas disponibles hors du moteur.

## Git et branches

- Travailler sur une branche dédiée par sujet : `fix/<sujet-court>` pour une correction et `feature/<sujet-court>` pour une nouvelle fonctionnalité.
- Choisir le préfixe selon l'objectif principal de la branche. La documentation directement liée à une correction ou une fonctionnalité reste sur la même branche.
- Faire `git status --short --branch` avant toute modification et préserver les changements locaux déjà présents.
- Avant toute nouvelle branche destinée à `main`, exécuter `git fetch origin --prune`, puis créer directement la branche avec `git switch -c <branche> origin/main`. Ne pas utiliser le `main` local ni la branche courante comme base implicite.
- Vérifier avant la première modification que `git merge-base HEAD origin/main` est égal à `git rev-parse origin/main`. Si la récupération distante échoue ou si cette égalité n'est pas vraie sur une branche nouvellement créée, arrêter et corriger la base avant d'éditer.
- Ne jamais fusionner un ancien `main` local dans une branche de fonctionnalité.
- Une fois les changements d'un sujet commités sur leur branche, ne pas réutiliser cette branche pour une reprise ou une correction ultérieure : créer une nouvelle branche dédiée depuis la branche cible à jour.
- Lors d'un conflit, ne pas accepter tout `ky_buffhud.lua` depuis un seul côté. Comparer la base commune, la branche cible et la branche de travail, puis conserver ensemble les invariants des buffs horizontaux et du killfeed horizontal.
- Après une résolution de conflit dans le rendu, confirmer que `compute_horizontal_positions`, `buff_position_x`, `buff_position_y`, `killfeed_size` et la rangée horizontale du killfeed sont toujours présents avant de committer.
- Ne jamais inclure dans un commit une modification utilisateur préexistante sans l'identifier clairement.
- Garder les commits ciblés : documentation, correction de rendu, catalogue ou options doivent rester séparables quand cela aide la revue.
- Ne pas pousser, fusionner, réécrire l'historique ou supprimer une branche sans demande explicite.
- Avant une proposition de fusion, indiquer les tests réellement effectués et ceux qui nécessitent encore PAYDAY 2.

## Versionnage et changelog

- Utiliser un numéro de révision entier, dans le style de Better Assault Indicator : `r1`, `r2`, `r3`, etc. Ne pas employer de version sémantique `X.Y.Z` pour ce projet.
- Une révision correspond à un changement intégré à `main` : soit un ancien commit effectué directement sur `main`, soit une pull request fusionnée. Les commits de travail internes à une pull request et les merges servant seulement à synchroniser sa branche sont regroupés sous la révision de la fusion et ne créent pas de doublons.
- Mettre à jour `changelog.txt` dans la même branche que tout changement visible par l'utilisateur. Ajouter la révision la plus récente en haut au format `rN (JJ.MM.AAAA):` et décrire l'effet utile du changement au lieu de recopier le message Git brut.
- Pour une pull request, préparer une seule nouvelle révision correspondant à sa future fusion dans `main` et conserver son numéro de pull request dans le changelog dès qu'il est connu.
- Lors d'une publication, la clé `version` de `mod.txt` contient uniquement le numéro entier de la dernière révision, sans préfixe `r` ; par exemple, l'entrée `r36` correspond à `"version": "36"`.
- Inclure `changelog.txt` dans la vérification du diff et dans le commit concerné ; une fonctionnalité ou correction livrable ne doit pas être fusionnée sans son entrée de changelog.

## Points d'attention connus

- Les numéros de version présents dans `mod.txt` et certains en-têtes Lua ne sont pas toujours alignés. Ne pas les modifier au passage ; les harmoniser seulement dans une tâche de versionnage dédiée.
- Les textures peuvent dépendre d'atlas ou de DLC. `ky_buffhud.lua` doit conserver une texture de repli quand une ressource n'existe pas.
- L'ordre de chargement des hooks compte. Déclarer un hook dans le contexte où la classe du jeu existe déjà.
- Les appels de rendu arrivent fréquemment. Les opérations lourdes, les scans de catalogue et les logs détaillés ne doivent pas être exécutés à chaque frame.
