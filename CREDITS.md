# Credits and source lineage

KyoHUD is an independent PAYDAY 2 SuperBLT mod. It does not bundle HUDList, GameInfoManager, or their buff catalog. VanillaHUD Plus is optional for the killfeed, score, and medals, but required for buff display.

## HUDList and GameInfoManager

The runtime buff state, source mappings, and display metadata consumed by KyoHUD are provided by implementations derived from:

- **HUDList**, originally created by **NN / pjal3urb (Thomas G. Hall)**:  
  https://bitbucket.org/pjal3urb/hudlist/src/master/
- **GameInfoManager**, originally created by **NN / pjal3urb (Thomas G. Hall)**:  
  https://bitbucket.org/pjal3urb/gameinfomanager/src/master/

The original HUDList project uses GameInfoManager as its information-gathering layer. KyoHUD keeps its own rendering and presentation overrides, but reads these upstream runtime interfaces instead of redistributing their catalog.

## VanillaHUD Plus

KyoHUD integrates at runtime with the expanded HUDList and GameInfoManager implementation maintained in **VanillaHUD Plus** by:

- **Test1**
- **LT71 / Bunnie**
- **Kamikaze94**
- **BangL**

VanillaHUD Plus:  
https://modworkshop.net/mod/25629

When VanillaHUD Plus exposes `managers.gameinfo`, `HUDListManager.BUFFS`, and `HUDList.BuffItemBase.MAP`, KyoHUD uses them for active buff state, source mappings, and display metadata. Without that full provider contract, only KyoHUD's buff display is disabled; unrelated HUD features remain operational.

## Joy's Score Counter

KyoHUD's combat-score concept and initial unit score values were inspired by **Joy's Score Counter** by **Offyerrocker**, whose scoring rubric is based on Joy's in-game scoring voice lines:

https://modworkshop.net/mod/24730

KyoHUD does not include Joy's Score Counter and does not reuse its kill-detection, popup, high-score, menu, or persistence implementation. KyoHUD independently handles local-player attribution, host/client kill detection, civilian penalties, deduplication, killfeed rendering, combat-state lifetime, and its later scoring fallbacks and extensions.

## KyoHUD

KyoHUD's horizontal HUD layout, tactical frames, killfeed, combat-score implementation, kill-streak announcements, weapon-family medals, settings, localization, state management, and release tooling are implemented specifically for KyoHUD by **Kyosh1ro** and its contributors.
