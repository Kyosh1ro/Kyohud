"""Player options contract: defaults, callbacks, menu, localization, manifest.

Bounded integration regressions BEFORE production wiring.

Proposed contract:
  - enable_player=false default in KH._defaults
  - player_value_mode=1 default in KH._defaults
  - KY_TogglePlayer saves bool and invokes runtime refresh
  - KY_SetPlayerValueMode saves mode and invokes runtime refresh
  - Invalid modes 0,3,1.5,string reset to 1
  - menu: toggle id ky_enable_player, callback KY_TogglePlayer
  - menu: multiple_choice id ky_player_value_mode, items ky_opt_player_value_percentage/real, callback KY_SetPlayerValueMode
  - loc keys: ky_opt_enable_player, ky_opt_enable_player_desc, ky_opt_player_value_mode, ky_opt_player_value_mode_desc, ky_opt_player_value_percentage, ky_opt_player_value_real, ky_hud_player_health, ky_hud_player_armor, ky_hud_player_downs, ky_hud_player_unknown_condition
  - mod.txt: exactly one entry each for hud/actors.lua, hud/components/gauge.lua, hud/player.lua under hudmanagerpd2, ordered runtime < actors < gauge < player

No production writes. No bash/Git/external writes. Missing functionality = fail not skip.
"""
from pathlib import Path
import json as pyjson
import unittest

from test_hud_alerts_integration import _lua_with_options

ROOT = Path(__file__).resolve().parents[1]
MENU_PATH = ROOT / "menu" / "menu.json"
LOC_EN_PATH = ROOT / "loc" / "english.json"
LOC_FR_PATH = ROOT / "loc" / "french.json"
LOC_LUA_PATH = ROOT / "lua" / "ky_localization.lua"


class OptionDefaultsAndPersistenceTests(unittest.TestCase):
    """enable_player=false default, player_value_mode=1 default; save/load
    preservation of false and mode 2; old save without keys resets to defaults."""

    def test_option_defaults_and_persistence(self):
        lua, ok = _lua_with_options()
        self.assertTrue(ok, "RED: ky_options.lua must exist")
        self.assertTrue(lua.eval("kyohud._defaults.enable_player ~= nil"),
            "RED: _defaults must explicitly have enable_player key")
        self.assertEqual(lua.eval("kyohud._defaults.enable_player"), False,
            "RED: _defaults.enable_player must explicitly be false")
        self.assertEqual(lua.eval("kyohud.settings.enable_player"), False,
            "RED: settings.enable_player must default to false")
        self.assertTrue(lua.eval("kyohud._defaults.player_value_mode ~= nil"),
            "RED: _defaults must explicitly have player_value_mode key")
        self.assertEqual(lua.eval("kyohud._defaults.player_value_mode"), 1,
            "RED: _defaults.player_value_mode must explicitly be 1")
        self.assertEqual(lua.eval("kyohud.settings.player_value_mode"), 1,
            "RED: settings.player_value_mode must default to 1")
        lua.execute('''
            for k in pairs(_ky_mem_files) do _ky_mem_files[k] = nil end
            local old = '{"enable_killfeed":true}'
            local f = io.open(kyohud._settings_path, "w"); f:write(old); f:close()
            kyohud.settings.enable_player = true
            kyohud.settings.player_value_mode = 2
            kyohud.Load()
            _absent_player = kyohud.settings.enable_player
            _absent_mode = kyohud.settings.player_value_mode
        ''')
        self.assertEqual(lua.eval("_absent_player"), False,
            "RED: old save without enable_player must yield false after Load")
        self.assertEqual(lua.eval("_absent_mode"), 1,
            "RED: old save without player_value_mode must yield 1 after Load")
        lua.execute('''
            kyohud.settings.enable_player = true; kyohud.Save()
            kyohud.settings.enable_player = false; kyohud.Load()
            _rt_true = kyohud.settings.enable_player
            kyohud.settings.enable_player = false; kyohud.Save()
            kyohud.settings.enable_player = true; kyohud.Load()
            _rt_false = kyohud.settings.enable_player
        ''')
        self.assertEqual(lua.eval("_rt_true"), True,
            "RED: Save(true)/Load must preserve enable_player=true")
        self.assertEqual(lua.eval("_rt_false"), False,
            "RED: Save(false)/Load must preserve enable_player=false")
        lua.execute('''
            kyohud.settings.player_value_mode = 2; kyohud.Save()
            kyohud.settings.player_value_mode = 1; kyohud.Load()
            _rt_mode2 = kyohud.settings.player_value_mode
            kyohud.settings.player_value_mode = 1; kyohud.Save()
            kyohud.settings.player_value_mode = 2; kyohud.Load()
            _rt_mode1 = kyohud.settings.player_value_mode
        ''')
        self.assertEqual(lua.eval("_rt_mode2"), 2,
            "RED: Save(2)/Load must preserve player_value_mode=2")
        self.assertEqual(lua.eval("_rt_mode1"), 1,
            "RED: Save(1)/Load must preserve player_value_mode=1")


class CallbacksAndInvalidModeTests(unittest.TestCase):
    """KY_TogglePlayer and KY_SetPlayerValueMode persist through Save/Load and
    invoke runtime refresh; invalid modes 0,3,1.5,string reset to 1."""

    def test_callbacks_and_invalid_mode_reset(self):
        lua, ok = _lua_with_options()
        self.assertTrue(ok, "RED: ky_options.lua must load")
        self.assertTrue(lua.eval("MenuCallbackHandler.KY_TogglePlayer ~= nil"),
            "RED: MenuCallbackHandler.KY_TogglePlayer must exist")
        self.assertTrue(lua.eval("MenuCallbackHandler.KY_SetPlayerValueMode ~= nil"),
            "RED: MenuCallbackHandler.KY_SetPlayerValueMode must exist")
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = false
            kyohud.settings.player_value_mode = 1
            kyohud.hud.runtime:mount(_G.managers.hud)
            local fake_on = {value = function() return "on" end}
            MenuCallbackHandler.KY_TogglePlayer(nil, fake_on)
            _player_on = kyohud.settings.enable_player
            local file_on = _ky_mem_files[kyohud._settings_path]
            assert(type(file_on) == "string" and #file_on > 0,
                "RED: Save must write nonempty in-memory file")
            local decoded_on = json.decode(file_on)
            _file_player_on = decoded_on.enable_player
            kyohud.settings.enable_player = false
            kyohud.Load()
            _after_load_on = kyohud.settings.enable_player
        ''')
        g = lua.globals()
        self.assertEqual(g._player_on, True,
            "RED: callback ON must set enable_player=true")
        self.assertEqual(g._file_player_on, True,
            "RED: decoded in-memory file must contain enable_player=true after callback ON")
        self.assertEqual(g._after_load_on, True,
            "RED: Load after Save(true) must restore enable_player=true")
        lua.execute('''
            local fake_off = {value = function() return "off" end}
            MenuCallbackHandler.KY_TogglePlayer(nil, fake_off)
            _player_off = kyohud.settings.enable_player
            local file_off = _ky_mem_files[kyohud._settings_path]
            local decoded_off = json.decode(file_off)
            _file_player_off = decoded_off.enable_player
            kyohud.settings.enable_player = true
            kyohud.Load()
            _after_load_off = kyohud.settings.enable_player
        ''')
        g2 = lua.globals()
        self.assertEqual(g2._player_off, False,
            "RED: callback OFF must set enable_player=false")
        self.assertEqual(g2._file_player_off, False,
            "RED: decoded in-memory file must contain enable_player=false after callback OFF")
        self.assertEqual(g2._after_load_off, False,
            "RED: Load after Save(false) must restore enable_player=false")
        lua.execute('''
            kyohud.settings.player_value_mode = 1
            local fake_mode2 = {value = function() return "2" end}
            MenuCallbackHandler.KY_SetPlayerValueMode(nil, fake_mode2)
            _mode2 = kyohud.settings.player_value_mode
            local file_mode2 = _ky_mem_files[kyohud._settings_path]
            local decoded_mode2 = json.decode(file_mode2)
            _file_mode2 = decoded_mode2.player_value_mode
            kyohud.settings.player_value_mode = 1
            kyohud.Load()
            _after_load_mode2 = kyohud.settings.player_value_mode
        ''')
        g3 = lua.globals()
        self.assertEqual(g3._mode2, 2,
            "RED: callback mode 2 must set player_value_mode=2")
        self.assertEqual(g3._file_mode2, 2,
            "RED: decoded in-memory file must contain player_value_mode=2 after callback")
        self.assertEqual(g3._after_load_mode2, 2,
            "RED: Load after Save(2) must restore player_value_mode=2")
        lua.execute('''
            local _orig_refresh = kyohud.hud.runtime.refresh_settings
            local _refresh_count = 0
            kyohud.hud.runtime.refresh_settings = function(self, mgr)
                _refresh_count = _refresh_count + 1
                return _orig_refresh(self, mgr)
            end
            _before_toggle = _refresh_count
            local fake_toggle = {value = function() return "on" end}
            MenuCallbackHandler.KY_TogglePlayer(nil, fake_toggle)
            _after_toggle = _refresh_count
            _before_mode = _refresh_count
            local fake_mode = {value = function() return "1" end}
            MenuCallbackHandler.KY_SetPlayerValueMode(nil, fake_mode)
            _after_mode = _refresh_count
            kyohud.hud.runtime.refresh_settings = _orig_refresh
        ''')
        g3b = lua.globals()
        self.assertEqual(g3b._after_toggle - g3b._before_toggle, 1,
            "RED: KY_TogglePlayer callback must invoke runtime.refresh_settings exactly once")
        self.assertEqual(g3b._after_mode - g3b._before_mode, 1,
            "RED: KY_SetPlayerValueMode callback must invoke runtime.refresh_settings exactly once")
        lua.execute('''
            local function write_bad_mode(bad)
                local tbl = {enable_killfeed = true, player_value_mode = bad}
                local payload = json.encode(tbl)
                local f = io.open(kyohud._settings_path, "w")
                f:write(payload)
                f:close()
            end
            write_bad_mode(0)
            kyohud.Load()
            _invalid_0 = kyohud.settings.player_value_mode
            write_bad_mode(3)
            kyohud.Load()
            _invalid_3 = kyohud.settings.player_value_mode
            write_bad_mode(1.5)
            kyohud.Load()
            _invalid_1_5 = kyohud.settings.player_value_mode
            write_bad_mode("string")
            kyohud.Load()
            _invalid_string = kyohud.settings.player_value_mode
        ''')
        g4 = lua.globals()
        self.assertEqual(g4._invalid_0, 1,
            "RED: invalid mode 0 must reset to 1, got " + str(g4._invalid_0))
        self.assertEqual(g4._invalid_3, 1,
            "RED: invalid mode 3 must reset to 1, got " + str(g4._invalid_3))
        self.assertEqual(g4._invalid_1_5, 1,
            "RED: invalid mode 1.5 must reset to 1, got " + str(g4._invalid_1_5))
        self.assertEqual(g4._invalid_string, 1,
            "RED: invalid mode 'string' must reset to 1, got " + repr(g4._invalid_string))


class JsonMenuStructureTests(unittest.TestCase):
    """Menu has toggle ky_enable_player and multiple_choice ky_player_value_mode
    with items ky_opt_player_value_percentage/real, callback KY_SetPlayerValueMode."""

    def test_json_menu_structure(self):
        menu_raw = _read_file(MENU_PATH)
        self.assertIsNotNone(menu_raw, "RED: menu.json must exist")
        menu = pyjson.loads(menu_raw)
        items = menu.get("items", menu) if isinstance(menu, dict) else menu
        player_toggle_entries = [
            e for e in items
            if isinstance(e, dict) and e.get("value") == "enable_player"
        ]
        self.assertEqual(len(player_toggle_entries), 1,
            "RED: exactly one menu entry with value enable_player")
        player_toggle = player_toggle_entries[0]
        self.assertEqual(player_toggle.get("type"), "toggle",
            "RED: ky_enable_player menu entry type must be toggle")
        self.assertEqual(player_toggle.get("id"), "ky_enable_player",
            "RED: ky_enable_player menu entry id must be ky_enable_player")
        self.assertEqual(player_toggle.get("default_value"), False,
            "RED: ky_enable_player menu default_value must be false")
        self.assertEqual(player_toggle.get("callback"), "KY_TogglePlayer",
            "RED: ky_enable_player callback must be KY_TogglePlayer")
        self.assertEqual(player_toggle.get("enabled_by"), "enable_hud_foundation",
            "RED: ky_enable_player must be enabled_by enable_hud_foundation")
        player_mode_entries = [
            e for e in items
            if isinstance(e, dict) and e.get("value") == "player_value_mode"
        ]
        self.assertEqual(len(player_mode_entries), 1,
            "RED: exactly one menu entry with value player_value_mode")
        player_mode = player_mode_entries[0]
        self.assertEqual(player_mode.get("type"), "multiple_choice",
            "RED: ky_player_value_mode menu entry type must be multiple_choice")
        self.assertEqual(player_mode.get("callback"), "KY_SetPlayerValueMode",
            "RED: ky_player_value_mode callback must be KY_SetPlayerValueMode")
        mode_items = player_mode.get("items", [])
        self.assertIsInstance(mode_items, list,
            "RED: ky_player_value_mode items must be a list")
        for it in mode_items:
            self.assertIsInstance(it, str,
                "RED: each mode item must be a localization key string, got " + repr(it))
        self.assertEqual(mode_items,
            ["ky_opt_player_value_percentage", "ky_opt_player_value_real"],
            "RED: ky_player_value_mode items must be exactly "
            "[ky_opt_player_value_percentage, ky_opt_player_value_real]")
        if "item_values" in player_mode:
            self.assertEqual(player_mode["item_values"], [1, 2],
                "RED: ky_player_value_mode item_values must be [1, 2]")


class LocalizationAndManifestTests(unittest.TestCase):
    """EN/FR/fallback keys for player options; manifest exactly one entry each
    for lua/hud/actors.lua, lua/hud/components/gauge.lua, lua/hud/player.lua
    under HUDManager, ordered runtime < actors < gauge < player."""

    def test_localization_and_manifest(self):
        required_keys = [
            "ky_opt_enable_player", "ky_opt_enable_player_desc",
            "ky_opt_player_value_mode", "ky_opt_player_value_mode_desc",
            "ky_opt_player_value_percentage", "ky_opt_player_value_real",
            "ky_hud_player_health", "ky_hud_player_armor",
            "ky_hud_player_downs", "ky_hud_player_unknown_condition",
        ]
        en = pyjson.loads(_read_file(LOC_EN_PATH))
        fr = pyjson.loads(_read_file(LOC_FR_PATH))
        for key in required_keys:
            self.assertIn(key, en, f"RED: EN loc missing {key}")
            self.assertIn(key, fr, f"RED: FR loc missing {key}")
            self.assertTrue(isinstance(en[key], str) and len(en[key]) > 0,
                f"RED: EN value for {key} must be nonempty")
            self.assertTrue(isinstance(fr[key], str) and len(fr[key]) > 0,
                f"RED: FR value for {key} must be nonempty")
        loc_src = _read_file(LOC_LUA_PATH)
        self.assertIsNotNone(loc_src, "RED: ky_localization.lua must exist")
        for key in required_keys:
            self.assertIn(key, loc_src,
                f"RED: ky_localization.lua fallback must contain key {key}")
        mod_raw = _read_file(ROOT / "mod.txt")
        self.assertIsNotNone(mod_raw, "RED: mod.txt must exist")
        mod = pyjson.loads(mod_raw)
        hooks = mod.get("hooks", [])
        hudmgrpd2_hooks = [h for h in hooks if h.get("hook_id") == "lib/managers/hudmanagerpd2"]
        expected_paths = [
            "lua/hud/actors.lua",
            "lua/hud/components/gauge.lua",
            "lua/hud/player.lua",
        ]
        for path in expected_paths:
            matches = [h for h in hudmgrpd2_hooks if h.get("script_path") == path]
            self.assertEqual(len(matches), 1,
                f"RED: exactly one hudmanagerpd2 hook for {path}, got {len(matches)}")
        runtime_idx = None
        path_indices = {}
        for i, h in enumerate(hudmgrpd2_hooks):
            sp = h.get("script_path")
            if sp == "lua/hud/runtime.lua":
                runtime_idx = i
            if sp in expected_paths:
                path_indices[sp] = i
        self.assertIsNotNone(runtime_idx,
            "RED: runtime.lua must appear in hudmanagerpd2 hooks")
        for path in expected_paths:
            self.assertIn(path, path_indices,
                f"RED: {path} must appear in hudmanagerpd2 hooks")
        self.assertLess(runtime_idx, path_indices["lua/hud/actors.lua"],
            "RED: actors.lua must come after runtime.lua")
        self.assertLess(path_indices["lua/hud/actors.lua"], path_indices["lua/hud/components/gauge.lua"],
            "RED: gauge.lua must come after actors.lua")
        self.assertLess(path_indices["lua/hud/components/gauge.lua"], path_indices["lua/hud/player.lua"],
            "RED: player.lua must come after gauge.lua")


def _read_file(path):
    """Read file contents, return None if not found."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (FileNotFoundError, OSError):
        return None


if __name__ == "__main__":
    unittest.main()
