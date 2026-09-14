# Credits and source lineage

KyoHUD is an independent PAYDAY 2 SuperBLT mod. Its buff display uses a namespaced autonomous provider reconstructed from the official HUDList and GameInfoManager projects. VanillaHUD Plus is not required.

## HUDList and GameInfoManager

KyoHUD's runtime buff state, source mappings, and display metadata are reconstructed from:

- **HUDList**, originally created by **NN / pjal3urb (Thomas G. Hall)**:  
  https://bitbucket.org/pjal3urb/hudlist/src/master/
- **GameInfoManager**, originally created by **NN / pjal3urb (Thomas G. Hall)**:  
  https://bitbucket.org/pjal3urb/gameinfomanager/src/master/

The original HUDList project uses GameInfoManager as its information-gathering layer. KyoHUD keeps the reconstructed provider namespaced under `kyohud`, together with its own rendering and presentation overrides.

## VanillaHUD Plus

The expanded HUDList and GameInfoManager implementation maintained in **VanillaHUD Plus** served as a modern behavioral reference during reconstruction. Credits include:

- **Test1**
- **LT71 / Bunnie**
- **Kamikaze94**
- **BangL**

VanillaHUD Plus:  
https://modworkshop.net/mod/25629

KyoHUD does not require or consume VanillaHUD Plus at runtime. Its autonomous provider reads PAYDAY 2's native APIs directly; VanillaHUD Plus remains a provenance and comparison reference only.

## Joy's Score Counter

KyoHUD's combat-score concept and initial unit score values were inspired by **Joy's Score Counter** by **Offyerrocker**, whose scoring rubric is based on Joy's in-game scoring voice lines:

https://modworkshop.net/mod/24730

KyoHUD does not include Joy's Score Counter and does not reuse its kill-detection, popup, high-score, menu, or persistence implementation. KyoHUD independently handles local-player attribution, host/client kill detection, civilian penalties, deduplication, killfeed rendering, combat-state lifetime, and its later scoring fallbacks and extensions.

## KyoHUD

KyoHUD's horizontal HUD layout, tactical frames, killfeed, combat-score implementation, kill-streak announcements, weapon-family medals, settings, localization, state management, and release tooling are implemented specifically for KyoHUD by **Kyosh1ro** and its contributors.
