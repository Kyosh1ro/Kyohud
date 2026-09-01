# KyoHUD v1.0.0 — first public release

KyoHUD is a PAYDAY 2 SuperBLT mod built around a tactical killfeed, combat
score, and a compact buff row near the crosshair.

This is the first stable public release. It contains the same mod as the
internal `r84` revision, now published under semantic versioning.

## What's in it

- **Killfeed** — up to five chronological cards for your own eliminations,
  oldest on the left, with adaptive spacing.
- **Announcements** — multikill banners with mirrored chevrons, plus dedicated
  banners for Bulldozers and bosses.
- **Weapon-family medals** — tiered streaks for shotguns, snipers, incendiary,
  melee, and explosive kills, in their own killfeed row.
- **Combat score** — a persistent widget showing Total Score for the heist
  (civilian penalties included) and Best Streak, each independently
  positionable and hideable.
- **Buffs** — a horizontal row of active buffs with remaining time and adaptive
  frames that shift to warning and critical states as they expire.
- **Options** — position, icon size, opacity, and per-category or per-buff
  filters, in English and French, with **Preview Buffs & Kills** to check your
  layout without a heist.

## Install

1. Install [SuperBLT](https://superblt.znix.xyz/).
2. Download `latest.zip` from this release and extract it so you get
   `PAYDAY 2/mods/Kyohud/`, with `mod.txt` directly inside that folder.
3. Launch the game and open
   **Options > Mod Options > KyoHUD - Killfeed & Combat Score**.

Already running an older KyoHUD? SuperBLT picks this version up automatically
through the mod-update check.

## Compatibility

- Requires SuperBLT. VanillaHUD Plus is optional — KyoHUD keeps its own buff
  catalog and native hooks, and only uses `managers.gameinfo` when it happens
  to be available.
- KyoHUD only touches its own HUD panels, so it coexists with full HUD
  replacements such as Void UI.

## Versioning

From this release on, KyoHUD follows semantic versioning: tags are `vN.N.N` and
match `mod.txt` exactly. Pre-1.0 `rN` entries remain in `changelog.txt` as the
historical record.

## Usage and credits

Do not re-upload KyoHUD without permission or present it as your own work.
Third-party source lineage is documented in `CREDITS.md`.

Thanks to the authors of HUDList and GameInfoManager (NN / pjal3urb), VanillaHUD
Plus (Test1, LT71/Bunnie, Kamikaze94, BangL), and Joy's Score Counter
(Offyerrocker), whose work KyoHUD builds on.
