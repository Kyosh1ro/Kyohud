# KyoHUD - Killfeed & Combat Score

KyoHUD is a **PAYDAY 2** mod focused on a tactical killfeed, kill streak and special-enemy announcements, combat score, and customizable buffs around the crosshair.

## Features

- Killfeed for eliminations made by the local player.
- Announcements for kill streaks and special enemies.
- Combat score displayed alongside the killfeed.
- Horizontal display of active buffs with their remaining duration.
- Configurable position, icon size, and opacity.
- Filters by category and individual buff.
- Menus available in English and French.

## Installation

1. Install [SuperBLT](https://superblt.znix.xyz/).
2. Place the `Kyohud` folder in `PAYDAY 2/mods/`.
3. Launch the game.

## Configuration

Open **Options > Mod Options > KyoHUD - Killfeed & Combat Score** to customize the display. Use **Preview Buffs & Kills** and **Clear Preview** to quickly test the layout.

## Versioning

KyoHUD follows semantic versioning from **v1.0.0** onward. The version in `mod.txt` is the bare `MAJOR.MINOR.PATCH` number, and each release is tagged with the matching `vMAJOR.MINOR.PATCH` tag. Entries before v1.0.0 use the old `rN` revision scheme and are kept in [changelog.txt](changelog.txt) as the historical record.

## Releases

Releases are published on the [GitHub releases page](https://github.com/Kyosh1ro/kyohud/releases). Each one attaches a `latest.zip` archive and a SuperBLT `meta.json`, so an installed copy of KyoHUD updates itself through SuperBLT's mod-update check.

## Usage and redistribution

Do not re-upload KyoHUD without permission or present it as your own work.

Third-party attribution is documented separately in [CREDITS.md](CREDITS.md). The 7-Zip build tool used only by the release workflow remains covered by its own [license](.github/7ZIP_LICENSE.txt) and is not included in the published mod archive.

## Credits

KyoHUD's combat-score concept and initial unit score values were inspired by **Joy's Score Counter** by **Offyerrocker**, itself based on Joy's in-game scoring voice lines. KyoHUD uses its own kill detection, attribution, rendering, and state management.

KyoHUD's buff catalog and icon descriptor conventions are adapted from **HUDList** and **GameInfoManager** by **NN / pjal3urb (Thomas G. Hall)**, and from the expanded implementation maintained in **VanillaHUD Plus** by **Test1, LT71/Bunnie, Kamikaze94, and BangL**.

VanillaHUD Plus support is optional; KyoHUD keeps its own local catalog and does not bundle HUDList or GameInfoManager. See [CREDITS.md](CREDITS.md) for the full source lineage and links.
