# KyoHUD - Killfeed & Combat Score

KyoHUD adds a killfeed, kill streak announcements, a combat score, and optional buff display to PAYDAY 2.

## Features

- Killfeed for your kills.
- Kill streak and special enemy announcements.
- Combat score and medals.
- Active buffs displayed in a horizontal row.
- English and French menus.

## Installation

1. Install [SuperBLT](https://superblt.znix.xyz/).
2. Extract the `Kyohud` folder into `PAYDAY 2/mods/`.
3. Launch the game.

## Configuration

Open **Options > Mod Options > KyoHUD - Killfeed & Combat Score**.

### Optional HUD modules (development branch)

The HUD foundation is required by the optional Mission, Objectives, Assault,
Alerts, Player, Weapons, Equipment and Teammates modules. These modules are
disabled by default and can be enabled independently once the foundation is on.
The supported HUD scale range is **0.95–1.05**, with **1.00** as the default.

The local player, weapons, equipment and teammate displays are currently
additive, with provisional placement; they do not remove the corresponding
native HUD. Unknown remote values remain unknown rather than being invented.
VR and unsupported states retain the native display. Compatibility with every
third-party HUD, final visual parity with the design reference and performance
gains are not promised. Combined in-game qualification is still in progress.

## Credits

The combat score was inspired by **Joy's Score Counter** by **Offyerrocker**.

KyoHUD's autonomous buff provider is reconstructed from **HUDList** and **GameInfoManager**. See [CREDITS.md](CREDITS.md) for details and links.

## Permission

Do not re-upload KyoHUD without permission or present it as your own work.
