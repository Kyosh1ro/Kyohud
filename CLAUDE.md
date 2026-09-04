# KyoHUD — Claude

Les instructions de travail de ce dépôt sont partagées entre agents et vivent dans
`AGENTS.md` (source unique). L'architecture détaillée et les invariants sont dans
`CODEX.md`. Lis-les avant toute modification.

@AGENTS.md

## Références externes (read-only, hors dépôt — ne jamais committer ici)

Détails et autres chemins dans la section « Références locales » d'`AGENTS.md`. À retenir :

- `G:\PD2-Modding-Docs\Payday-2-LuaJIT-Complete` : sources Lua décompilées du jeu.
  Aller y vérifier les vrais champs plutôt que deviner (`CopDamage:die` → `attack_data`,
  `CopMovement`/`HuskCopMovement` → `anim_data()`, `rope_unit()`, etc.).
- `G:\SteamLibrary\steamapps\common\PAYDAY 2\mods\base\lua` : base SuperBLT installée
  (référence pour `Hooks:PostHook`, `dofile`, `ModPath`, `LuaNetworking`, menus).

Vérifier l'existence d'un chemin avant de le consulter. Une lecture de source ne
remplace pas un test en partie avec SuperBLT.
