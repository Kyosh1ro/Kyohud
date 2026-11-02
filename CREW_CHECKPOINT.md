# Lot 5 — checkpoint de reprise (non livré)

## Priorité autoritaire — 2026-11-02

Branche `feature/hud-crew`, HEAD `b5c853ca73336a551812a8a1076643fa4bc29ecf`, changements locaux préservés, aucun commit/déploiement. Dernier log 13:44:17, 12 transitions enregistrées uniquement ; zéro conflit plein écran/Polyline et 5 vrais conflits Gradient, pas de couverture après plafonnement. Exécution réelle SOL reproduit 522,482.5,236,36 via DrawTacticalFrame(520,480.5,240,40,inset2) et 520,527.5,240,33 via DrawMedalFrame(520,526.5,240,35) ; journal non nommé seul non preuve producteur exclusif, ne pas étiqueter tous les buffs. Correctif crew seul y=min(y précédent, parent_h*.5-margin_x-card_h), haut-gauche fixe au-dessus du milieu, aucun suivi d'animation. Échelle 1280×720 journalisée ~1.0033 crew maintenant 25.6,254.1,577.9,80.3 vs 25.6,480.8,577.9,80.3. Garde intacte, vrais conflits cachent et récupèrent mêmes objets. Trois régressions test_hud_crew_placement.py RED significatif avant production puis GREEN ; 48 tests crew OK, suite complète 1243 OK, 35 chunks LuaJIT compilés, 10 JSON valides, toutes entrées manifeste vers scripts existants (33 chemins distincts), parité EN/FR et diff checks OK. Correction polyligne buff locale préservée. Correctif de clignotement validé par utilisateur en client sur une partie entière. Diagnostics temporaires retirés de crew.lua et crew_card.lua ; placement, certification et garde conservés. Vérification SOL après nettoyage : 1243 tests OK, 48 crew OK, 35 chunks LuaJIT, 10 JSON, 56 entrées manifeste, EN/FR et diff checks OK. Prochaine action : utilisateur copie lua/hud/crew.lua ET lua/hud/components/crew_card.lua puis Dernier smoke moteur sans instrumentation confirmé par l'utilisateur : acceptation acquise pour le smoke final observé ; ce journal court seul ne prouve pas la couverture complète du braquage, la confirmation utilisateur établit le smoke observé. Journal courant vérifié : G:/SteamLibrary/steamapps/common/PAYDAY 2/mods/logs/2026_11_02_log.txt, 210 lignes, 16:36:30–16:37:09, aucune exception Lua CrewDiag ni KyoHUD, kyodev initialisé ; avertissements — définition de mod invalide pour mods/Kyohud/ et mods/Proving Grounds/ et LVM sans métadonnée de mise à jour, ne pas qualifier ce journal d'exempt d'erreurs ; lot5 non clôturé. G strictement lecture seule agents, aucune opération Git/déploiement. Aucun font()/set_font(), masquage, 4c/lot6. Qwen seul writer, SOL vérification indépendante. Sections précédentes historiques supersédées.

Branche : `feature/hud-crew`, HEAD `b5c853c`. Ce checkpoint sauvegarde le travail en cours ; il ne clôture ni ne publie le lot 5. Aucun changement de version/changelog, fusion, déploiement ou lot 6. Lot 5 **non accepté** ; pas de commit/push/branche/écriture native/font/lot6/4c.

## Priorité actuelle — polylignes de buffs identifiées

Cette section remplace les bilans précédents. Le log moteur du 02.11.2026 identifie les faux obstacles plein écran comme Polyline, is_root=false. Les deux producteurs sont les contours temporisés de DrawTimedBuffProgress dans lua/ky_buff_render.lua. Ils omettaient x/y/w/h : leur boîte héritait 1280×720, indépendamment du tracé. Correction dépôt par Qwen : boîte explicite incluant le halo et points locaux, mêmes coordonnées écran et même style. Aucun assouplissement global des conflits.

Les Gradient 547.2,527,46,27 et 588.7,527,38,27 sont de vrais chevauchements avec crew ; ils continuent légitimement à le cacher. La disparition complète ne peut donc pas être déclarée résolue sans traiter ou éviter ce placement réel. Ne pas déplacer les acquis 4a/4b/4c implicitement.

Vérification SOL : deux régressions RED sur source avant correctif puis GREEN sur source actuelle, intégration hors/avec chevauchement et récupération mêmes primitifs ; 1240 tests OK,35 chunks LuaJIT,10 JSON,56 chemins manifeste,parité EN/FR et diff checks OK. Nouvelle couverture .github/test_hud_buff_progress_bounds.py.

Prochain essai : utilisateur copie seulement lua/ky_buff_render.lua (crew.lua enrichi déjà installé identique), redémarre et reproduit ; vérifier que les contours de buffs restent alignés et que les conflits plein écran disparaissent. Les diagnostics restent actifs. Lot5 non accepté en moteur. Aucun commit/push/branche/déploiement/version/changelog/G écrit/natif/font/lot6.

## PRIORITÉ ACTUELLE — 2026-11-02

2026_11_02 engine test failed disappearance persists with installed crew.lua byte identical repository verified SOL. Log conflicts0,0,1280,720 and555.2,527,46,27 /569.7,527,46,27. Removing root shortcut fixes reproduced bug but DOES NOT identify full engine cause; root attribution not proven. New temporary diagnostic in crew.lua reports actual obstacle name/object/is_root/local_rect/combat_rect/crew_rect plus prior rect; display policy unchanged,12 lines transitions cap preserved.45 crew tests GREEN independent; full suite validation pending coordinator. User next action copy ONLY lua/hud/crew.lua restart reproduce then supply enriched log. No native masking/font()/set_font()/4c/G writes/git/lot6, lot5 NOT accepted. Mark previous status summaries historical superseded by this paragraph; preserve ALL original bytes below insertion, do not normalize apostrophes or delete history.

## État conservé

- Collecte roster/identité, santé/armure, armes/munitions, équipements et interactions ; cartes horizontales persistantes et intégration runtime.
- Chaîne option `enable_crew=false`, sauvegarde, callback, menu et localisations EN/FR/fallback intégrée.
- Acquis 4a/4b/4c conservés. Ne pas modifier RECHARGE/ACTIVE du lot 4c.
- Aucun nouveau masquage natif.
- Police définie uniquement au constructeur texte : aucun appel crew à `font()` ou `set_font()`. Les deux approches précédentes ont provoqué des crashes natifs ; `pcall` ne protège pas d'une access violation.

## Correction producteur : racine et enfants

- `core.lua` lignes 1714/1720 : la racine `kyohud_buff_panel` n'est pas un conteneur d'occupation ; seul le placement direct y contribue. Le conteneur lui-même n'est pas obstacle, seuls les enfants dessinés directs contribuent.
- `crew.lua` ligne 260 : le raccourci de dimension fautif a été retiré ; la racine ne compte plus comme obstacle. Les gardes enfant réelles, la branche world et le poll sont conservés.
- Le scan enfants ne concerne que nos enfants dessinés directs, jamais un scan natif.

## Diagnostics moteur : pending

Log exact 1280×720 : cause cohérente de fallback racine, pas de mesure de texte, aucune preuve de transformation de coordonnées spécifique à cette résolution. Aucune preuve de transformation moteur 1280×720. Diagnostics en attente de reproduction moteur ; nettoyage uniquement après confirmation.

## Divulgation worker

Ajout non autorisé de méthodes world partagées dans `test_hud_gauge.py` détecté, arrêté et entièrement reverti vers le baseline byte-equal ; SOL n'a jamais écrit de production/tests pour ce fichier.

## Acceptation moteur : ouverte, défaut identifié

Après suppression des deux bindings de police, l'utilisateur rapporte une activation fonctionnelle sans nouveau crash dans cet essai. Les alliés apparaissent, disparaissent et reviennent : **corrigé dépôt seulement, non confirmé moteur**.

Log moteur `mods/logs/2026_10_29_log.txt` examiné : les transitions de disparition enregistrées sont `state=conflict`, pas un roster vide ni une erreur de certification. Plusieurs obstacles ont pour rectangle `0,0,1280,720` : le contrôle de chevauchement utilise une boîte plein écran comme obstacle occupé. Une autre transition donne `520,527.5,240,33`, à qualifier séparément comme chevauchement potentiel réel. Ne pas conclure que tous les conflits sont faux.

Instrumentation temporaire conservée : `[KyoHUD][CrewDiag]`, transitions uniquement, maximum 12 lignes par session Lua, dans `lua/hud/crew.lua`. `crew_card.lua` expose le premier champ de certification fautif. Tests dédiés : `.github/test_hud_crew_diagnostics.py` et `.github/test_hud_crew_obstacles.py` (4 tests, fixtures sentinelles ajoutent des rectangles réels). Retirer ces traces après correction et confirmation moteur, puis vérifier un dernier essai sans instrumentation.

## Reprise avec Qwen

1. SOL inspecte les fichiers réels, le statut Git et les processus natifs. Qwen est le seul writer de production/tests ; SOL vérifie indépendamment. Ne pas lancer une seconde passe si un ancien processus reste actif.
2. Route : `opencode run --model opencode-go/qwen3.7-plus` ; permissions par commande : `OPENCODE_PERMISSION='{"bash":"deny","external_directory":"allow","task":"deny","skill":"deny"}'`.
3. Étape 3 déjà complétée : qualification des obstacles de `_combat_conflict` corrigée. Maintenant vérification moteur : l'utilisateur copie crew.lua puis test de disparition/réapparition avec log SuperBLT.
4. Passes bornées : tests → RED significatif → production → GREEN ; suite entière, compilation LuaJIT récursive, JSON/manifeste/localisations, diff checks.
5. L'utilisateur copie ensuite le dépôt vers son installation `mods/kyodev`. G: reste strictement en lecture seule pour les agents. Essai moteur disparition/réapparition, puis nettoyage diagnostique et dernier smoke avant acceptation.

## Vérifications du checkpoint

Dernière vérification avant préparation : **1237 tests OK**, **35 chunks compilés LuaJIT**, **10 JSON valides**, **56 chemins manifeste présents**, parité EN/FR et diff checks OK. Ces résultats sont hors moteur, pas une acceptation hôte/client ni une garantie Diesel. Les vérifications sont relancées avant commit.

Le handoff local détaillé, ignoré par Git, est `.hermes/plans/handoff-lot5-crew-in-progress.md` ; son état prioritaire doit être lu avant l'historique. Ce document suivi permet une reprise même sans les plans locaux. Lire également `AGENTS.md` et `CODEX.md`.
