# Credits and source lineage

KyoHUD is an independent PAYDAY 2 SuperBLT mod. It does not bundle HUDList or GameInfoManager, and VanillaHUD Plus is not a required dependency.

## HUDList and GameInfoManager

The buff catalog, icon descriptor conventions, and parts of the buff-event model are adapted from:

- **HUDList**, originally created by **NN / pjal3urb (Thomas G. Hall)**:  
  https://bitbucket.org/pjal3urb/hudlist/src/master/
- **GameInfoManager**, originally created by **NN / pjal3urb (Thomas G. Hall)**:  
  https://bitbucket.org/pjal3urb/gameinfomanager/src/master/

The original HUDList project uses GameInfoManager as its information-gathering layer. KyoHUD keeps its own local catalog and rendering implementation rather than loading either project as a required runtime dependency.

## VanillaHUD Plus

KyoHUD also references the expanded HUDList and GameInfoManager implementation maintained in **VanillaHUD Plus** by:

- **Test1**
- **LT71 / Bunnie**
- **Kamikaze94**
- **BangL**

VanillaHUD Plus:  
https://modworkshop.net/mod/25629

When VanillaHUD Plus exposes its optional `managers.gameinfo` interface, KyoHUD can use that interface to enrich buff detection. KyoHUD continues to provide its own native hooks and remains usable without VanillaHUD Plus.

## KyoHUD

KyoHUD's horizontal HUD layout, tactical frames, killfeed, combat scoring, kill-streak announcements, weapon-family medals, settings, localization, state management, and release tooling are implemented specifically for KyoHUD by **Kyosh1ro** and its contributors.
