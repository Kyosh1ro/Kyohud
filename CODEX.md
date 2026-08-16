# Kyosh1ro HUD — dossier technique

État observé le 16 août 2026 sur la branche `fix/hud-arc-workflow`.

## Résumé

Kyosh1ro HUD est un mod PAYDAY 2 autonome chargé par SuperBLT. Il poursuit deux objectifs :

- afficher les buffs actifs et leur temps restant sur un arc autour du réticule ;
- afficher les éliminations du joueur local sur un second arc.

Le projet reprend des identifiants et conventions d'icônes de VanillaHUD+, mais il ne dépend pas de VanillaHUD+ à l'exécution. Son implémentation est volontairement beaucoup plus petite : un catalogue partagé, quelques hooks du jeu et un rendu HUD dédié.

Le catalogue et les menus sont aujourd'hui plus complets que la couche de détection. C'est la principale différence entre ce que le mod sait présenter et ce qu'il sait réellement observer en partie.

## Évolution du projet

L'historique Git montre les étapes suivantes :

1. Création du prototype avec affichage des buffs et du killfeed autour du viseur.
2. Adoption des atlas et définitions d'icônes inspirés de VanillaHUD+.
3. Ajout des filtres par catégorie et par buff.
4. Plusieurs itérations sur les menus SuperBLT, notamment après des crashs de `CoreMenuItemToggle` et des problèmes de sous-menus multiples.
5. Extraction du catalogue dans `ky_buff_catalog.lua` afin qu'il soit chargé avant les options et partagé par tous les modules.
6. Correction de la priorité des langues : anglais chargé comme base, puis français par-dessus quand il est demandé.
7. Séparation du killfeed dans un hook `CopDamage`, car cette classe n'existe pas encore dans le contexte de chargement de `PlayerManager`.
8. Travail actuel sur l'ordre d'arrivée et l'espacement séquentiel des icônes le long de l'arc.

Le dépôt contient 15 commits entre le prototype initial d'avril 2026 et la dernière révision de juillet 2026.

## Architecture effective

Le mod possède deux couches distinctes.

### Observation du jeu

- `ky_hooks.lua` observe les upgrades temporaires du joueur.
- `ky_killfeed.lua` observe la mort des ennemis.
- Ces modules convertissent les données internes de PAYDAY 2 en appels simples vers `KH:add_buff`, `KH:remove_buff` et `KH:add_kill`.

### Présentation

- `ky_buff_catalog.lua` décrit les buffs connus et leurs icônes.
- `ky_buffhud.lua` conserve l'état actif et dessine les deux arcs.
- `ky_options.lua` gère les filtres et paramètres persistants.
- `ky_localization.lua` et `loc/` fournissent les textes visibles.

La table globale `Kyosh1roHUD`, généralement nommée `KH` localement, relie ces modules. Il n'existe pas encore de bus d'évènements ou de modèle intermédiaire séparé.

## Inventaire actuel

Le catalogue contient 83 définitions réparties ainsi :

| Catégorie | Nombre |
| --- | ---: |
| AI | 3 |
| Debuffs | 10 |
| Enforcer | 5 |
| Fugitive | 13 |
| Gage | 2 |
| Ghost | 5 |
| Mastermind | 13 |
| Perk Decks | 21 |
| Player Actions | 6 |
| Team Buffs | 4 |
| Technician | 1 |

Parmi ces 83 entrées :

- 61 sont visibles par défaut ;
- 22 sont masquées par défaut ;
- 36 correspondances explicites upgrade → buff sont déclarées ;
- toutes les cibles de ces correspondances existent dans `KH.BUFF_MAP` ;
- toutes les clés de buff attendues existent dans `loc/english.json` et `loc/french.json`.

Le nombre de correspondances n'est pas le nombre exact de buffs détectables : un upgrade dont l'identifiant correspond déjà à celui du catalogue n'a pas besoin de correspondance explicite.

## Couverture réelle des buffs

La détection actuelle repose uniquement sur deux fonctions de `PlayerManager` :

```text
activate_temporary_upgrade
deactivate_temporary_upgrade
```

Le flux actuel est :

```text
upgrade temporaire PAYDAY 2
    -> résolution par KH.UPGRADE_TO_BUFF
    -> vérification dans KH.BUFF_MAP
    -> KH:add_buff / KH:remove_buff
    -> KH._buffs
    -> rendu circulaire
```

Cette approche couvre correctement les effets passant par la catégorie `temporary`, mais pas nécessairement :

- les buffs permanents ou calculés à partir d'une valeur ;
- les buffs à piles ;
- les effets avec progression ;
- les actions du joueur comme recharger, interagir ou charger une attaque ;
- certains effets d'équipe ;
- certains effets et cooldowns de perk decks ;
- les buffs produits par d'autres classes ou systèmes du jeu.

Certaines entrées peuvent donc être proposées dans les filtres sans jamais être alimentées par les hooks actuels.

VanillaHUD+ résout ce problème avec un `GameInfoManager` qui agrège plusieurs sources du jeu. Son HUD écoute des évènements `buff` et `player_action`, dont l'activation, la désactivation, la durée, la progression, les piles et les valeurs. Kyosh1ro HUD n'a importé que les informations de présentation nécessaires, pas toute cette infrastructure de détection.

VanillaHUD+ doit rester une référence fonctionnelle, pas une dépendance obligatoire. Une future extension peut reprendre le principe d'une couche d'observation unifiée sans importer toute sa complexité.

## Durée et cycle de vie d'un buff

Après l'activation d'un upgrade temporaire, `ky_hooks.lua` recherche sa durée dans cet ordre :

1. temps restant calculé depuis `_temporary_upgrades.temporary[upgrade].expire_time` ;
2. deuxième valeur renvoyée par `upgrade_value("temporary", upgrade, nil)` ;
3. réglage utilisateur `buff_duration` ;
4. valeur de repli de 5 secondes.

`KH:add_buff` indexe les entrées par identifiant. Une nouvelle activation du même buff remplace donc son timer au lieu de créer un doublon.

Dans le travail actuel, `order_t` mémorise la première arrivée du buff. Un rafraîchissement renouvelle `start_t`, `duration` et `t_end`, tout en conservant sa position relative dans l'arc.

## Rendu circulaire

Le panneau `kyosh1ro_buff_panel` est attaché en priorité au panneau `PlayerBase.PLAYER_INFO_HUD_PD2`. Le centre géométrique de ce panneau sert de centre au cercle.

Pour chaque angle `a` :

```text
x = centre_x + cos(a) * rayon
y = centre_y - sin(a) * rayon
```

L'axe Y des interfaces étant orienté vers le bas, le sinus est soustrait.

### Arc des buffs

- angle de départ par défaut : 315° ;
- angle de fin par défaut : 90° ;
- rayon par défaut : 250 px ;
- taille d'icône par défaut : 32 px ;
- direction : angles croissants en traversant 360°/0°.

Le premier buff est placé à l'angle de départ. Les suivants avancent selon un pas angulaire dérivé de la taille de l'icône, d'une marge et du rayon.

Le travail en cours apporte trois propriétés importantes :

- tri par ordre d'arrivée au lieu de l'identifiant alphabétique ;
- marge suffisante pour limiter le chevauchement des icônes et timers ;
- compression du pas lorsque tous les éléments ne tiennent pas sur l'arc, sans masquer les derniers.

Lorsqu'un buff disparaît, les suivants peuvent se rapprocher du début de l'arc. Lorsque les angles de début et de fin sont identiques, l'étendue vaut actuellement zéro et toutes les icônes risquent de se superposer.

### Arc du killfeed

Le killfeed utilise actuellement :

- un arc fixe de 250° à 290° ;
- un rayon extérieur égal à `circle_radius + icon_size + 20` ;
- des icônes à 80 % de la taille des buffs ;
- le même réglage de durée que les buffs.

## Coût du rendu

`HUDManager:update` appelle le rendu environ toutes les 0,05 seconde, soit 20 fois par seconde. À chaque rendu :

1. les buffs et kills expirés sont purgés ;
2. le panneau entier est vidé ;
3. tous les bitmaps et textes encore visibles sont recréés.

Cette stratégie est simple et probablement suffisante avec peu d'éléments. Elle génère cependant davantage d'allocations qu'un système conservant chaque élément graphique et mettant seulement à jour sa position, son texte et son alpha.

Les logs détaillés ne doivent pas rester actifs à chaque rendu. Les traces temporaires actuelles ne se déclenchent que lorsque le nombre de buffs change, mais doivent être retirées après validation du problème d'arc.

## Killfeed : couverture et limites

`ky_killfeed.lua` accepte actuellement :

- un attaquant égal à l'unité du joueur local ;
- un attaquant possédant un `thrower_unit` égal au joueur local.

Cela couvre les armes directes et certains objets lancés. Les kills indirects provenant de dégâts persistants, d'une sentry, d'un joker ou d'autres unités possédées peuvent ne pas être attribués au joueur avec cette logique.

Le nom affiché provient de `_tweak_table`, avec une petite table de noms lisibles. Malgré ces types différents, toutes les entrées de `ENEMY_ICON_MAP` pointent actuellement vers la même icône `hud_icons:mugshot_normal`.

## Compatibilité avec les autres HUD

Le mod crée un panneau séparé au-dessus du HUD avec un layer élevé. Il n'écrase pas directement le rendu de VanillaHUD+, ce qui favorise leur coexistence.

Un risque subsiste : le centre utilisé est celui du panneau `PLAYER_INFO_HUD_PD2`, pas une position de réticule explicitement lue depuis le jeu. Un autre HUD qui redimensionne, déplace ou met à l'échelle ce panneau pourrait décaler l'arc par rapport au véritable réticule.

Les textures sont validées avec `DB:has`. Une texture absente, notamment pour un DLC non disponible, doit continuer à utiliser `guis/textures/pd2/hud_timer` comme repli.

## Menus et persistance

La construction du menu suit le cycle SuperBLT attendu :

1. `MenuManagerSetupCustomMenus` initialise le menu principal ;
2. `MenuManagerPopulateCustomMenus` ajoute ses contrôles ;
3. `MenuManagerBuildCustomMenus` construit et rattache le menu.

Les sous-menus de catégories sont clonés depuis le menu principal avec `deep_clone`. Ce choix vient de problèmes constatés en jeu avec plusieurs appels à `MenuHelper:BuildMenu`.

Les paramètres sont enregistrés dans :

```text
SavePath/kyosh1ro_hud_settings.json
```

Le chargement fusionne les valeurs sauvegardées avec les valeurs par défaut. Les tests `~= nil` sont indispensables pour conserver correctement les options booléennes sauvegardées à `false`.

## Localisation

`ky_localization.lua` charge d'abord les fallbacks anglais, puis `english.json`, puis `french.json` lorsque la langue demandée est le français. Le français peut ainsi écraser l'anglais sans que l'anglais réécrase ensuite le français.

`ModPath` est capturé immédiatement dans une variable locale. C'est nécessaire car SuperBLT peut modifier ce global lors du chargement d'autres mods.

Les fallbacks dynamiques génèrent un nom lisible pour tout buff du catalogue, mais ils ne remplacent pas une traduction manuelle de qualité dans les deux JSON.

## Risques techniques connus

- La présentation est plus complète que la détection réelle.
- Le centre géométrique du panneau peut différer du centre réel du réticule avec certains HUD ou réglages d'échelle.
- Le panneau est entièrement reconstruit 20 fois par seconde.
- Le killfeed ne couvre pas encore toutes les sources de dégâts appartenant au joueur.
- Les icônes du killfeed ne différencient pas réellement les types d'ennemis.
- Un arc d'étendue nulle superpose ses éléments.
- Les versions de `mod.txt` et des en-têtes Lua ne sont pas harmonisées.
- Aucun test automatisé ne peut valider les classes et textures disponibles uniquement dans PAYDAY 2.

## Priorités proposées

1. Terminer le placement séquentiel et le valider en jeu avec plusieurs tailles, rayons et angles.
2. Retirer les logs temporaires après validation.
3. Définir précisément les buffs que le mod promet de supporter.
4. Ajouter une couche d'observation adaptée aux autres familles de buffs, une famille à la fois.
5. Améliorer l'attribution des kills indirects.
6. Vérifier le centre du réticule avec VanillaHUD+ et différentes valeurs d'échelle HUD.
7. Envisager un rendu persistant si le coût de reconstruction devient mesurable.

## Références externes

- [Définition d'un mod SuperBLT](https://superblt.znix.xyz/doc/mod_definition/basics/)
- [Hooks SuperBLT](https://superblt.znix.xyz/doc/common_functions/hooks/)
- [Cycle des menus SuperBLT](https://superblt.znix.xyz/doc/menus/menu_helper_hooks/)
- [Variables `ModPath` et `SavePath`](https://superblt.znix.xyz/doc/mod_definition/variables/)
- [Dépôt VanillaHUD+](https://github.com/steam-test1/VPlusHUD)
- [HUDList de VanillaHUD+](https://github.com/steam-test1/VPlusHUD/blob/master/devlua/HUDList.lua)
- [GameInfoManager de VanillaHUD+](https://github.com/steam-test1/VPlusHUD/blob/master/devlua/GameInfoManager.lua)

Ces références servent à comprendre les API et l'architecture existante. Elles ne dispensent pas de vérifier le comportement directement dans PAYDAY 2.
