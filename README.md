# KyoHUD - Killfeed & Combat Score

KyoHUD is a **PAYDAY 2** mod focused on a tactical killfeed, kill streak and special-enemy announcements, combat score, and customizable buffs around the crosshair.

## Features

- Killfeed for eliminations made by the local player.
- Announcements for kill streaks and special enemies.
- Combat score displayed alongside the killfeed.
- Horizontal display of VanillaHUD+ active buffs with their remaining duration.
- Configurable position, icon size, and opacity.
- Individual buff visibility follows the VanillaHUD+ buff settings.
- Menus available in English and French.

## Installation

1. Install [SuperBLT](https://superblt.znix.xyz/).
2. To display buffs, install [VanillaHUD Plus](https://modworkshop.net/mod/25629). KyoHUD's killfeed, score, and medals remain available without it.
3. Place the `Kyohud` folder in `PAYDAY 2/mods/`.
4. Launch the game.

## Configuration

Open **Options > Mod Options > KyoHUD - Killfeed & Combat Score** to customize the display. Use **Preview Buffs & Kills** and **Clear Preview** to quickly test the layout.

## Credits

KyoHUD's combat-score concept and initial unit score values were inspired by **Joy's Score Counter** by **Offyerrocker**, itself based on Joy's in-game scoring voice lines. KyoHUD uses its own kill detection, attribution, rendering, and state management.

KyoHUD reads active buff state and display metadata at runtime from the **HUDList** and **GameInfoManager** implementation included in **VanillaHUD Plus**, maintained by **Test1, LT71/Bunnie, Kamikaze94, and BangL** and originally created by **NN / pjal3urb (Thomas G. Hall)**.

VanillaHUD Plus is optional for KyoHUD as a whole but required for buff display. KyoHUD does not bundle a copy of HUDList, GameInfoManager, or their buff catalog. See [CREDITS.md](CREDITS.md) for the full source lineage and links.
