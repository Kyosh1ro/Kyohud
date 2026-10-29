# Lot 5 — checkpoint de reprise (non livré)

Branche : `feature/hud-crew`. Ce checkpoint sauvegarde le travail en cours ; il ne clôture ni ne publie le lot 5. Aucun changement de version/changelog, fusion, déploiement ou lot 6.

## État conservé

- Collecte roster/identité, santé/armure, armes/munitions, équipements et interactions ; cartes horizontales persistantes et intégration runtime.
- Chaîne option `enable_crew=false`, sauvegarde, callback, menu et localisations EN/FR/fallback intégrée.
- Acquis 4a/4b/4c conservés. Ne pas modifier RECHARGE/ACTIVE du lot 4c.
- Aucun nouveau masquage natif.
- Police définie uniquement au constructeur texte : aucun appel crew à `font()` ou `set_font()`. Les deux approches précédentes ont provoqué des crashes natifs ; `pcall` ne protège pas d’une access violation.

## Acceptation moteur : ouverte, défaut identifié

Après suppression des deux bindings de police, l’utilisateur rapporte une activation fonctionnelle sans nouveau crash dans cet essai. Les alliés apparaissent, disparaissent et reviennent : **défaut non corrigé**.

Log moteur `mods/logs/2026_10_29_log.txt` examiné : les transitions de disparition enregistrées sont `state=conflict`, pas un roster vide ni une erreur de certification. Plusieurs obstacles ont pour rectangle `0,0,1280,720` : le contrôle de chevauchement utilise une boîte plein écran comme obstacle occupé. Une autre transition donne `520,527.5,240,33`, à qualifier séparément comme chevauchement potentiel réel. Ne pas conclure que tous les conflits sont faux.

Instrumentation temporaire conservée : `[KyoHUD][CrewDiag]`, transitions uniquement, maximum 12 lignes par session Lua, dans `lua/hud/crew.lua`. `crew_card.lua` expose le premier champ de certification fautif. Test dédié : `.github/test_hud_crew_diagnostics.py`. Retirer ces traces après correction et confirmation moteur, puis vérifier un dernier essai sans instrumentation.

## Reprise avec Qwen

1. SOL inspecte les fichiers réels, le statut Git et les processus natifs. Qwen est le seul writer de production/tests ; SOL vérifie indépendamment. Ne pas lancer une seconde passe si un ancien processus reste actif.
2. Route : `opencode run --model opencode-go/qwen3.7-plus` ; permissions par commande : `OPENCODE_PERMISSION='{"bash":"deny","external_directory":"allow","task":"deny","skill":"deny"}'`.
3. Corriger uniquement la qualification des obstacles de `_combat_conflict` : distinguer boîte de mise en page/conteneur et contenu réellement visible. Identifier le producteur exact du rectangle plein écran. Ne pas supprimer globalement la protection contre les vrais chevauchements.
4. Passes bornées : tests → RED significatif → production → GREEN ; suite entière, compilation LuaJIT récursive, JSON/manifeste/localisations, diff checks.
5. L’utilisateur copie ensuite le dépôt vers son installation `mods/kyodev`. G: reste strictement en lecture seule pour les agents. Essai moteur disparition/réapparition, puis nettoyage diagnostique et dernier smoke avant acceptation.

## Vérifications du checkpoint

Dernière vérification avant préparation : 1233 tests passent ; 35 chunks compilés avec LuaJIT ; diff checks OK. Ces résultats sont hors moteur, pas une acceptation hôte/client ni une garantie Diesel. Les vérifications sont relancées avant commit.

Le handoff local détaillé, ignoré par Git, est `.hermes/plans/handoff-lot5-crew-in-progress.md` ; son état prioritaire doit être lu avant l’historique. Ce document suivi permet une reprise même sans les plans locaux. Lire également `AGENTS.md` et `CODEX.md`.
