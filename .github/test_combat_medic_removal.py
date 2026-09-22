"""Regression: combat_medic and combat_medic_passive must not be offered as real buffs.

These two identifiers are native damage/reduction components in PAYDAY 2,
not user-facing toggleable buffs. KyoHUD must therefore:
- not expose them as individual buff toggles in defaults, menus or callbacks;
- not map them as standalone buff IDs in the HUDList catalog;
- not ship localization keys for them as buff toggles;
- still preserve `combat_medic_interaction` (a distinct, real buff) and the
  native `combat_medic_damage_multiplier` computation in ky_buff_render.lua.

Run: uv run --with lupa python -B -m unittest discover -s .github -p test_combat_medic_removal.py -v
"""

from __future__ import annotations

import json
import re
import tempfile
import unittest
from pathlib import Path

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
OPTIONS_CHUNK = (ROOT / "lua" / "ky_options.lua").read_text(encoding="utf-8-sig")
HUDLIST_CATALOG_CHUNK = (ROOT / "lua" / "hudlist_catalog.lua").read_text(encoding="utf-8-sig")
LOCALIZATION_CHUNK = (ROOT / "lua" / "ky_localization.lua").read_text(encoding="utf-8-sig")


REMOVED_BUFF_IDS = ("combat_medic", "combat_medic_passive")


def _load_options(save_dir: str):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.globals().SavePath = Path(save_dir).as_posix() + "/"
    lua.execute(
        r'''
        kyohud = nil
        Kyosh1roHUD = nil
        MenuCallbackHandler = {}
        Hooks = {callbacks = {}}
        function Hooks:Add(event, id, callback) self.callbacks[id] = callback end
        MenuHelper = {}
        BLT = nil
        function log(...) end
        function dofile(...) return true end
        json = {}
        function json.encode(data)
            return "language=" .. tostring(data.language)
        end
        function json.decode(raw)
            local language = tonumber(string.match(raw, "language=(%d+)"))
            if not language then error("invalid settings") end
            return {language = language}
        end
        '''
    )
    lua.execute(OPTIONS_CHUNK)
    return lua


class CombatMedicBuffRemovalTests(unittest.TestCase):
    # ------------------------------------------------------------------
    # Defaults / callbacks
    # ------------------------------------------------------------------
    def test_defaults_do_not_expose_combat_medic_toggles(self):
        with tempfile.TemporaryDirectory() as save_dir:
            lua = _load_options(save_dir)
            for buff_id in REMOVED_BUFF_IDS:
                self.assertIsNone(
                    lua.eval(f"kyohud._defaults[{buff_id!r}]"),
                    f"kyohud._defaults must not contain {buff_id!r}",
                )

    def test_toggle_ids_and_callbacks_do_not_include_combat_medic(self):
        with tempfile.TemporaryDirectory() as save_dir:
            lua = _load_options(save_dir)
            toggle_ids = lua.eval("kyohud._BUFF_TOGGLE_IDS") or []
            as_list = list(toggle_ids.values()) if hasattr(toggle_ids, "values") else list(toggle_ids)
            for buff_id in REMOVED_BUFF_IDS:
                self.assertNotIn(buff_id, as_list)
                self.assertIsNone(
                    lua.eval(f"MenuCallbackHandler['KY_ToggleBuff_{buff_id}']"),
                    f"Callback KY_ToggleBuff_{buff_id} must not be registered",
                )

    # ------------------------------------------------------------------
    # Declarative menu
    # ------------------------------------------------------------------
    def test_mastermind_menu_does_not_list_combat_medic_toggles(self):
        mastermind = json.loads((ROOT / "menu" / "buffs_mastermind.json").read_text(encoding="utf-8-sig"))
        values = {item["value"] for item in mastermind["items"] if item.get("type") == "toggle"}
        ids = {item["id"] for item in mastermind["items"] if item.get("type") == "toggle"}
        for buff_id in REMOVED_BUFF_IDS:
            self.assertNotIn(buff_id, values)
            self.assertNotIn(f"ky_buff_{buff_id}", ids)

    # ------------------------------------------------------------------
    # Localization
    # ------------------------------------------------------------------
    def test_localization_does_not_expose_combat_medic_toggle_keys(self):
        removed_keys = [f"ky_opt_buff_{buff_id}" for buff_id in REMOVED_BUFF_IDS]
        removed_keys += [f"ky_opt_buff_{buff_id}_desc" for buff_id in REMOVED_BUFF_IDS]
        for key in removed_keys:
            self.assertNotIn(key, LOCALIZATION_CHUNK, f"fallback key {key!r} must be removed")
            english = json.loads((ROOT / "loc" / "english.json").read_text(encoding="utf-8-sig"))
            french = json.loads((ROOT / "loc" / "french.json").read_text(encoding="utf-8-sig"))
            self.assertNotIn(key, english, f"English loc {key!r} must be removed")
            self.assertNotIn(key, french, f"French loc {key!r} must be removed")

    # ------------------------------------------------------------------
    # HUDList catalog
    # ------------------------------------------------------------------
    def _load_catalog_lua(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.execute('''
            kyohud = nil; Kyosh1roHUD = nil
            local function skill_icon(...) return "icon" end
            local function perk_icon(...) return "icon" end
            local function hud_icon(...) return "icon" end
        ''')
        lua.execute(HUDLIST_CATALOG_CHUNK)
        return lua

    def test_hudlist_catalog_does_not_map_combat_medic_as_standalone_buff(self):
        lua = self._load_catalog_lua()
        # Temporary upgrade mapping: no RHS must equal the removed IDs.
        temporary = lua.eval("kyohud.hudlist_catalog.mappings.temporary") or {}
        for upgrade, buff_id in temporary.items():
            if isinstance(buff_id, str):
                self.assertNotEqual(buff_id, "combat_medic")
                self.assertNotEqual(buff_id, "combat_medic_passive")
            elif isinstance(buff_id, (list, tuple)):
                for entry in buff_id:
                    self.assertNotEqual(entry, "combat_medic")
                    self.assertNotEqual(entry, "combat_medic_passive")
            elif isinstance(buff_id, dict):
                for entry in buff_id.values():
                    self.assertNotEqual(entry, "combat_medic")
                    self.assertNotEqual(entry, "combat_medic_passive")

        # Property mapping: same check.
        properties = lua.eval("kyohud.hudlist_catalog.mappings.property") or {}
        for upgrade, buff_ids in properties.items():
            if buff_ids is False:
                continue
            if isinstance(buff_ids, str):
                self.assertNotEqual(buff_ids, "combat_medic")
                self.assertNotEqual(buff_ids, "combat_medic_passive")
            elif isinstance(buff_ids, (list, tuple, dict)):
                items = buff_ids.values() if isinstance(buff_ids, dict) else buff_ids
                for entry in items:
                    self.assertNotEqual(entry, "combat_medic")
                    self.assertNotEqual(entry, "combat_medic_passive")

        # Direct IDs must not list the removed IDs as literals.
        direct = lua.eval("kyohud.hudlist_catalog.direct_ids.literals") or {}
        self.assertNotIn("combat_medic", direct)
        self.assertNotIn("combat_medic_passive", direct)

        # Definitions (built from VISUALS): no entry for the removed IDs.
        definitions = lua.eval("kyohud.hudlist_catalog.definitions") or {}
        self.assertNotIn("combat_medic", definitions)
        self.assertNotIn("combat_medic_passive", definitions)

    # ------------------------------------------------------------------
    # Preservation of the distinct interaction buff / damage multiplier
    # ------------------------------------------------------------------
    def test_combat_medic_interaction_is_preserved_in_catalog(self):
        lua = self._load_catalog_lua()
        definitions = lua.eval("kyohud.hudlist_catalog.definitions") or {}
        self.assertIn("combat_medic_interaction", definitions)
        properties = lua.eval("kyohud.hudlist_catalog.mappings.property") or {}
        self.assertIn("revive_damage_reduction", properties)

    def test_combat_medic_damage_multiplier_is_preserved_in_render(self):
        render_source = (ROOT / "lua" / "ky_buff_render.lua").read_text(encoding="utf-8-sig")
        self.assertIn("combat_medic_damage_multiplier", render_source)


if __name__ == "__main__":
    unittest.main()
