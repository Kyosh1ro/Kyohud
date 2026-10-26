"""Enable objectives option end-to-end test (RED state).

Verifies the enable_objectives option exists with correct defaults, persistence,
callback behavior, menu registration, and localization. This test FAILS because
the feature is not yet implemented.
"""
from pathlib import Path
import json
import unittest

from test_hud_objectives import _read, OBJECTIVES_PATH, _lua
from test_hud_mission_acceptance import _KY_OPTS_STUBS

ROOT = Path(__file__).resolve().parents[1]


def _lua_with_options():
    """Create Lua runtime with native fixtures + ky_options.lua loaded."""
    lua = _lua()[0]

    # Load ky_options.lua with in-memory stubs
    lua.execute(_KY_OPTS_STUBS)

    # Override json.encode/decode with Python stdlib-backed adapters
    # (flat settings dict: string keys, primitive values only)
    import json as pyjson

    def _py_json_encode(lua_table):
        d = {}
        for k, v in lua_table.items():
            if not isinstance(k, str):
                raise RuntimeError(f"json.encode: non-string key {k!r}")
            if not isinstance(v, (bool, int, float, str)) and v is not None:
                raise RuntimeError(f"json.encode: unsupported value type {type(v).__name__} for key {k!r}")
            d[k] = v
        return pyjson.dumps(d)

    def _py_json_decode(text):
        if not isinstance(text, str):
            raise RuntimeError("json.decode: input must be string")
        d = pyjson.loads(text)
        if not isinstance(d, dict):
            raise RuntimeError("json.decode: top-level must be object")
        for k, v in d.items():
            if not isinstance(k, str):
                raise RuntimeError(f"json.decode: non-string key {k!r}")
            if not isinstance(v, (bool, int, float, str)) and v is not None:
                raise RuntimeError(f"json.decode: unsupported value type {type(v).__name__} for key {k!r}")
        return lua.table_from(d)

    lua.globals().json.encode = _py_json_encode
    lua.globals().json.decode = _py_json_decode

    opts_src = _read(ROOT / "lua" / "ky_options.lua")
    if opts_src:
        lua.execute(opts_src)

    obj_src = _read(OBJECTIVES_PATH)
    return lua, obj_src is not None and opts_src is not None


class EnableObjectivesOptionTests(unittest.TestCase):
    """End-to-end test for enable_objectives option."""

    def test_enable_objectives_option_end_to_end(self):
        """enable_objectives option must exist with correct defaults, persistence,
        callback behavior, menu registration, and localization."""
        lua, ok = _lua_with_options()
        self.assertTrue(ok, "objectives production chunk or ky_options.lua missing")

        # 1. _defaults must explicitly have enable_objectives = false
        defaults_has_key = lua.eval("kyohud._defaults.enable_objectives ~= nil")
        self.assertTrue(defaults_has_key,
            "kyohud._defaults must explicitly have enable_objectives key")

        defaults_value = lua.eval("kyohud._defaults.enable_objectives")
        self.assertEqual(defaults_value, False,
            "kyohud._defaults.enable_objectives must explicitly be false")

        # 2. Current settings must default to false
        settings_value = lua.eval("kyohud.settings.enable_objectives")
        self.assertEqual(settings_value, False,
            "kyohud.settings.enable_objectives must default to false")

        # 3. Old save missing key -> false after Load
        lua.execute('''
            -- Clear in-memory files
            for k in pairs(_ky_mem_files) do _ky_mem_files[k] = nil end

            -- Create a save file without enable_objectives
            local old_save = '{"enable_killfeed":true,"enable_buffs":true}'
            local f = io.open(kyohud._settings_path, "w")
            f:write(old_save)
            f:close()

            -- Reload
            kyohud.settings.enable_objectives = true  -- Set to true first
            kyohud.Load()
            _value_after_load = kyohud.settings.enable_objectives
        ''')
        value_after_load = lua.eval("_value_after_load")
        self.assertEqual(value_after_load, False,
            "Old save missing enable_objectives key must result in false after Load")

        # 4. true/false Save/Load roundtrip via actual in-memory code
        lua.execute('''
            -- Set to true and save
            kyohud.settings.enable_objectives = true
            local save_ok = kyohud.Save()

            -- Load and verify
            kyohud.settings.enable_objectives = false  -- Reset to false
            kyohud.Load()
            _value_true = kyohud.settings.enable_objectives

            -- Set to false and save
            kyohud.settings.enable_objectives = false
            kyohud.Save()

            -- Load and verify
            kyohud.settings.enable_objectives = true  -- Reset to true
            kyohud.Load()
            _value_false = kyohud.settings.enable_objectives
        ''')
        value_true = lua.eval("_value_true")
        value_false = lua.eval("_value_false")
        self.assertEqual(value_true, True,
            "Save(true)/Load roundtrip must preserve true")
        self.assertEqual(value_false, False,
            "Save(false)/Load roundtrip must preserve false")

        # 5. KY_ToggleObjectives callback must exist
        callback_exists = lua.eval("MenuCallbackHandler.KY_ToggleObjectives ~= nil")
        self.assertTrue(callback_exists,
            "MenuCallbackHandler.KY_ToggleObjectives must exist")

        # 6. Callback on/off with foundation=true must mount/unmount objectives
        lua.execute('''
            -- Enable foundation and objectives
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = false

            -- Mount foundation
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud
            kyohud.hud.runtime:mount(mgr)

            -- Seed objective source
            local OM = _make_om()
            OM._objectives["test_obj"] = {
                id = "test_obj",
                text = "Test objective",
                amount = nil,
                current_amount = nil,
                sub_objectives = {},
            }
            OM:activate_objective("test_obj", nil, {})

            -- Toggle ON
            local fake_item_on = {value = function() return "on" end}
            MenuCallbackHandler.KY_ToggleObjectives(nil, fake_item_on)

            -- Verify objectives mounted (O._mounted is true and panel exists)
            local O = kyohud.hud.objectives
            _mounted_on = O and O._mounted or false
            _panel_on = O and O._root_panel or nil
            _panel_alive_on = O and O._root_panel and true or false
            _verify_render_on = O and O:_verify_render() or false

            -- Toggle OFF
            local fake_item_off = {value = function() return "off" end}
            MenuCallbackHandler.KY_ToggleObjectives(nil, fake_item_off)

            -- Verify objectives unmounted (O._mounted is false, _root_panel is nil)
            _mounted_off = O and O._mounted or false
            _panel_off = O and O._root_panel or nil

            -- Verify source state preserved (O._active still has 1 entry from OM)
            _active_count_off = O and #O._active or -1
        ''')
        mounted_on = lua.eval("_mounted_on")
        panel_on = lua.eval("_panel_on")
        panel_alive_on = lua.eval("_panel_alive_on")
        verify_render_on = lua.eval("_verify_render_on")
        mounted_off = lua.eval("_mounted_off")
        panel_off = lua.eval("_panel_off")
        active_count_off = lua.eval("_active_count_off")

        self.assertEqual(mounted_on, True,
            "Callback ON must set O._mounted to true")
        self.assertIsNotNone(panel_on,
            "Callback ON must create live panel (O._root_panel exists)")
        self.assertTrue(panel_alive_on,
            "Callback ON must produce an alive panel (O._root_panel alive)")
        self.assertTrue(verify_render_on,
            "Callback ON must pass O:_verify_render() before OFF")
        self.assertEqual(mounted_off, False,
            "Callback OFF must set O._mounted to false")
        self.assertIsNone(panel_off,
            "Callback OFF must remove panel (O._root_panel is nil)")
        self.assertEqual(active_count_off, 1,
            "Callback OFF must preserve source state (O._active still has 1 entry)")

        # 7. Callback must write settings file (prove by reading immediately after callback)
        lua.execute('''
            -- Toggle ON and verify file written
            local fake_item_on = {value = function() return "on" end}
            MenuCallbackHandler.KY_ToggleObjectives(nil, fake_item_on)

            -- Read file immediately after callback (no manual Save)
            local f = io.open(kyohud._settings_path, "r")
            local content = f:read("*all")
            f:close()
            _settings_contains_true = json.decode(content).enable_objectives == true

            -- Toggle OFF and verify file written
            local fake_item_off = {value = function() return "off" end}
            MenuCallbackHandler.KY_ToggleObjectives(nil, fake_item_off)

            -- Read file immediately after callback (no manual Save)
            local f2 = io.open(kyohud._settings_path, "r")
            local content2 = f2:read("*all")
            f2:close()
            _settings_contains_false = json.decode(content2).enable_objectives == false
        ''')
        settings_contains_true = lua.eval("_settings_contains_true")
        settings_contains_false = lua.eval("_settings_contains_false")
        self.assertTrue(settings_contains_true,
            "Callback ON must write settings file with enable_objectives=true")
        self.assertTrue(settings_contains_false,
            "Callback OFF must write settings file with enable_objectives=false")

        # 8. Menu validation via Python (not Lua)
        menu_path = ROOT / "menu" / "menu.json"
        self.assertTrue(menu_path.exists(), "menu/menu.json must exist")
        menu_data = json.loads(menu_path.read_text(encoding="utf-8-sig"))

        # Find toggle with value "enable_objectives"
        enable_objectives_toggles = [
            item for item in menu_data.get("items", [])
            if item.get("type") == "toggle" and item.get("value") == "enable_objectives"
        ]

        self.assertEqual(len(enable_objectives_toggles), 1,
            "menu.json must have exactly one toggle with value 'enable_objectives'")

        toggle = enable_objectives_toggles[0]
        self.assertEqual(toggle.get("callback"), "KY_ToggleObjectives",
            "Menu toggle callback must be 'KY_ToggleObjectives'")
        self.assertEqual(toggle.get("default_value"), False,
            "Menu toggle default_value must be false")

        title_key = toggle.get("title")
        desc_key = toggle.get("description")
        self.assertIsNotNone(title_key, "Menu toggle must have title key")
        self.assertIsNotNone(desc_key, "Menu toggle must have description key")
        self.assertTrue(len(title_key) > 0, "Title key must be nonempty")
        self.assertTrue(len(desc_key) > 0, "Description key must be nonempty")

        # 9. Localization validation via Python
        en_path = ROOT / "loc" / "english.json"
        fr_path = ROOT / "loc" / "french.json"
        loc_path = ROOT / "lua" / "ky_localization.lua"

        self.assertTrue(en_path.exists(), "loc/english.json must exist")
        self.assertTrue(fr_path.exists(), "loc/french.json must exist")
        self.assertTrue(loc_path.exists(), "lua/ky_localization.lua must exist")

        en_data = json.loads(en_path.read_text(encoding="utf-8-sig"))
        fr_data = json.loads(fr_path.read_text(encoding="utf-8-sig"))
        loc_src = loc_path.read_text(encoding="utf-8-sig")

        self.assertIn(title_key, en_data,
            "english.json must contain title key")
        self.assertIsInstance(en_data[title_key], str,
            "english.json title value must be a string")
        self.assertTrue(len(en_data[title_key]) > 0,
            "english.json title value must be nonempty")
        self.assertIn(desc_key, en_data,
            "english.json must contain description key")
        self.assertIsInstance(en_data[desc_key], str,
            "english.json description value must be a string")
        self.assertTrue(len(en_data[desc_key]) > 0,
            "english.json description value must be nonempty")
        self.assertIn(title_key, fr_data,
            "french.json must contain title key")
        self.assertIsInstance(fr_data[title_key], str,
            "french.json title value must be a string")
        self.assertTrue(len(fr_data[title_key]) > 0,
            "french.json title value must be nonempty")
        self.assertIn(desc_key, fr_data,
            "french.json must contain description key")
        self.assertIsInstance(fr_data[desc_key], str,
            "french.json description value must be a string")
        self.assertTrue(len(fr_data[desc_key]) > 0,
            "french.json description value must be nonempty")
        self.assertIn(title_key, loc_src,
            "ky_localization.lua must contain title key in fallbacks")
        self.assertIn(desc_key, loc_src,
            "ky_localization.lua must contain description key in fallbacks")

    def test_objectives_visible_limit_option_slice(self):
        """objectives_visible_limit option must exist with correct defaults, persistence,
        normalization, callback behavior, menu registration, localization, and render impact."""
        lua, ok = _lua_with_options()
        self.assertTrue(ok, "objectives production chunk or ky_options.lua missing")

        # 1. _defaults must explicitly have objectives_visible_limit = 1
        defaults_has_key = lua.eval("kyohud._defaults.objectives_visible_limit ~= nil")
        self.assertTrue(defaults_has_key,
            "kyohud._defaults must explicitly have objectives_visible_limit key")

        defaults_value = lua.eval("kyohud._defaults.objectives_visible_limit")
        self.assertEqual(defaults_value, 1,
            "kyohud._defaults.objectives_visible_limit must be 1")

        # 2. Current settings must default to 1
        settings_value = lua.eval("kyohud.settings.objectives_visible_limit")
        self.assertEqual(settings_value, 1,
            "kyohud.settings.objectives_visible_limit must default to 1")

        # 3. Old save missing key -> 1 after Load, preserving enable_objectives=false
        lua.execute('''
            for k in pairs(_ky_mem_files) do _ky_mem_files[k] = nil end
            local old_save = '{"enable_killfeed":true,"enable_buffs":true,"enable_objectives":false}'
            local f = io.open(kyohud._settings_path, "w")
            f:write(old_save)
            f:close()
            kyohud.settings.objectives_visible_limit = 3
            kyohud.settings.enable_objectives = true
            kyohud.Load()
            _value_after_load = kyohud.settings.objectives_visible_limit
            _enable_after_load = kyohud.settings.enable_objectives
        ''')
        value_after_load = lua.eval("_value_after_load")
        enable_after_load = lua.eval("_enable_after_load")
        self.assertEqual(value_after_load, 1,
            "Old save missing objectives_visible_limit must result in 1 after Load")
        self.assertEqual(enable_after_load, False,
            "enable_objectives must be preserved as false from saved JSON")

        # 4. Load normalization: numeric finite floor then clamp 1..3
        lua.execute('''
            for k in pairs(_ky_mem_files) do _ky_mem_files[k] = nil end
            local f = io.open(kyohud._settings_path, "w")
            f:write('{"objectives_visible_limit":0}')
            f:close()
            kyohud.Load()
            _clamp_zero = kyohud.settings.objectives_visible_limit

            _ky_mem_files[kyohud._settings_path] = nil
            f = io.open(kyohud._settings_path, "w")
            f:write('{"objectives_visible_limit":4}')
            f:close()
            kyohud.Load()
            _clamp_four = kyohud.settings.objectives_visible_limit

            _ky_mem_files[kyohud._settings_path] = nil
            f = io.open(kyohud._settings_path, "w")
            f:write('{"objectives_visible_limit":2.8}')
            f:close()
            kyohud.Load()
            _floor_28 = kyohud.settings.objectives_visible_limit

            _ky_mem_files[kyohud._settings_path] = nil
            f = io.open(kyohud._settings_path, "w")
            f:write('{"objectives_visible_limit":"hello"}')
            f:close()
            kyohud.Load()
            _invalid_string = kyohud.settings.objectives_visible_limit
        ''')
        self.assertEqual(lua.eval("_clamp_zero"), 1, "0 must clamp to 1")
        self.assertEqual(lua.eval("_clamp_four"), 3, "4 must clamp to 3")
        self.assertEqual(lua.eval("_floor_28"), 2, "2.8 must floor to 2")
        self.assertEqual(lua.eval("_invalid_string"), 1, "string must fallback to 1")

        # 5. KY_SetObjectivesVisibleLimit callback must exist
        callback_exists = lua.eval("MenuCallbackHandler.KY_SetObjectivesVisibleLimit ~= nil")
        self.assertTrue(callback_exists,
            "MenuCallbackHandler.KY_SetObjectivesVisibleLimit must exist")

        # 6. Callback persists integer and refreshes mounted O
        lua.execute('''
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud
            kyohud.hud.runtime:mount(mgr)

            local fake_foundation_on = {value = function() return "on" end}
            MenuCallbackHandler.KY_ToggleHudFoundation(nil, fake_foundation_on)

            local fake_objectives_on = {value = function() return "on" end}
            MenuCallbackHandler.KY_ToggleObjectives(nil, fake_objectives_on)

            local O = kyohud.hud.objectives
            assert(O, "O must exist")

            local OM = _make_om()
            OM._objectives["a"] = {
                id = "a", text = "Objective A", amount = nil, current_amount = nil, sub_objectives = {},
            }
            OM._objectives["b"] = {
                id = "b", text = "Objective B", amount = nil, current_amount = nil, sub_objectives = {},
            }
            OM._objectives["c"] = {
                id = "c", text = "Objective C", amount = nil, current_amount = nil, sub_objectives = {},
            }
            OM:activate_objective("a", nil, {})
            OM:activate_objective("b", nil, {})
            OM:activate_objective("c", nil, {})

            local fake_item_3 = {value = function() return 3 end}
            MenuCallbackHandler.KY_SetObjectivesVisibleLimit(nil, fake_item_3)

            _persisted_3 = kyohud.settings.objectives_visible_limit
            _active_count_3 = #O._active
            _panel_id_3 = O._root_panel

            local sel3 = O:select_visible()
            _sel3_count = #sel3
            _sel3_ok = (sel3[1] and sel3[1].id == "c")

            local f3 = io.open(kyohud._settings_path, "r")
            local content3 = f3:read("*all")
            f3:close()
            _saved_3 = json.decode(content3).objectives_visible_limit

            _slot1_text_vis_3 = O._slot_prims[1] and O._slot_prims[1].text and O._slot_prims[1].text:visible()
            _slot2_text_vis_3 = O._slot_prims[2] and O._slot_prims[2].text and O._slot_prims[2].text:visible()
            _slot3_text_vis_3 = O._slot_prims[3] and O._slot_prims[3].text and O._slot_prims[3].text:visible()

            _slot1_title_3 = O._slot_prims[1] and O._slot_prims[1].text and O._slot_prims[1].text:text() or nil
            _slot2_title_3 = O._slot_prims[2] and O._slot_prims[2].text and O._slot_prims[2].text:text() or nil
            _slot3_title_3 = O._slot_prims[3] and O._slot_prims[3].text and O._slot_prims[3].text:text() or nil
            _verify_render_3 = O:_verify_render()

            local fake_item_1 = {value = function() return 1 end}
            MenuCallbackHandler.KY_SetObjectivesVisibleLimit(nil, fake_item_1)

            _persisted_1 = kyohud.settings.objectives_visible_limit
            _panel_id_1 = O._root_panel
            _active_count_1 = #O._active

            local sel1 = O:select_visible()
            _sel1_count = #sel1
            _sel1_id = sel1[1] and sel1[1].id or nil

            local f1 = io.open(kyohud._settings_path, "r")
            local content1 = f1:read("*all")
            f1:close()
            _saved_1 = json.decode(content1).objectives_visible_limit

            _slot1_text_vis_1 = O._slot_prims[1] and O._slot_prims[1].text and O._slot_prims[1].text:visible()
            _slot1_amt_vis_1 = O._slot_prims[1] and O._slot_prims[1].amount and O._slot_prims[1].amount:visible()
            _slot2_text_vis_1 = O._slot_prims[2] and O._slot_prims[2].text and O._slot_prims[2].text:visible()
            _slot2_amt_vis_1 = O._slot_prims[2] and O._slot_prims[2].amount and O._slot_prims[2].amount:visible()
            _slot3_text_vis_1 = O._slot_prims[3] and O._slot_prims[3].text and O._slot_prims[3].text:visible()
            _slot3_amt_vis_1 = O._slot_prims[3] and O._slot_prims[3].amount and O._slot_prims[3].amount:visible()

            _slot1_title_1 = O._slot_prims[1] and O._slot_prims[1].text and O._slot_prims[1].text:text() or nil
            _verify_render_1 = O:_verify_render()
            _same_panel = (_panel_id_1 == _panel_id_3)
        ''')
        self.assertEqual(lua.eval("_persisted_3"), 3, "Callback must persist integer 3")
        self.assertEqual(lua.eval("_active_count_3"), 3, "All 3 objectives must remain active")
        self.assertEqual(lua.eval("_sel3_count"), 1, "select_visible must return 1 entry")
        self.assertTrue(lua.eval("_sel3_ok"), "select_visible must return c")
        self.assertEqual(lua.eval("_saved_3"), 3, "Settings file must contain 3")
        self.assertEqual(lua.eval("_slot1_text_vis_3"), True, "Slot 1 text must be visible with limit 3")
        self.assertEqual(lua.eval("_slot2_text_vis_3"), False, "Slot 2 text must be hidden with limit 3")
        self.assertEqual(lua.eval("_slot3_text_vis_3"), False, "Slot 3 text must be hidden with limit 3")
        self.assertEqual(lua.eval("_slot1_title_3"), "Objective C", "Slot 1 title must be Objective C with limit 3")
        self.assertEqual(lua.eval("_slot2_title_3"), "", "Slot 2 title must be empty string with limit 3")
        self.assertEqual(lua.eval("_slot3_title_3"), "", "Slot 3 title must be empty string with limit 3")
        self.assertTrue(lua.eval("_verify_render_3"), "verify_render must pass with limit 3")

        self.assertEqual(lua.eval("_persisted_1"), 1, "Callback must persist integer 1")
        self.assertEqual(lua.eval("_active_count_1"), 3, "All 3 objectives must remain active after limit change")
        self.assertTrue(lua.eval("_same_panel"), "Panel identity must be preserved (same object)")
        self.assertEqual(lua.eval("_sel1_count"), 1, "select_visible must return 1 entry")
        self.assertEqual(lua.eval("_sel1_id"), "c", "select_visible must return c")
        self.assertEqual(lua.eval("_saved_1"), 1, "Settings file must contain 1")
        self.assertEqual(lua.eval("_slot1_title_1"), "Objective C", "Slot 1 title must be Objective C with limit 1")
        self.assertTrue(lua.eval("_verify_render_1"), "verify_render must pass with limit 1")
        self.assertEqual(lua.eval("_slot1_text_vis_1"), True, "Slot 1 text must be visible with limit 1")
        self.assertEqual(lua.eval("_slot1_amt_vis_1"), False, "Slot 1 amount must be hidden (no amount)")
        self.assertEqual(lua.eval("_slot2_text_vis_1"), False, "Slot 2 text must be hidden with limit 1")
        self.assertEqual(lua.eval("_slot2_amt_vis_1"), False, "Slot 2 amount must be hidden with limit 1")
        self.assertEqual(lua.eval("_slot3_text_vis_1"), False, "Slot 3 text must be hidden with limit 1")
        self.assertEqual(lua.eval("_slot3_amt_vis_1"), False, "Slot 3 amount must be hidden with limit 1")

        # 7. Menu validation
        menu_path = ROOT / "menu" / "menu.json"
        self.assertTrue(menu_path.exists(), "menu/menu.json must exist")
        menu_data = json.loads(menu_path.read_text(encoding="utf-8-sig"))

        sliders = [
            item for item in menu_data.get("items", [])
            if item.get("type") == "slider" and item.get("value") == "objectives_visible_limit"
        ]

        self.assertEqual(len(sliders), 1,
            "menu.json must have exactly one slider with value 'objectives_visible_limit'")

        slider = sliders[0]
        self.assertEqual(slider.get("callback"), "KY_SetObjectivesVisibleLimit",
            "Menu slider callback must be 'KY_SetObjectivesVisibleLimit'")
        self.assertEqual(slider.get("min"), 1, "min must be 1")
        self.assertEqual(slider.get("max"), 3, "max must be 3")
        self.assertEqual(slider.get("step"), 1, "step must be 1")
        self.assertEqual(slider.get("default_value"), 1, "default_value must be 1")

        title_key = slider.get("title")
        desc_key = slider.get("description")
        self.assertIsNotNone(title_key, "Menu slider must have title key")
        self.assertIsNotNone(desc_key, "Menu slider must have description key")
        self.assertTrue(len(title_key) > 0, "Title key must be nonempty")
        self.assertTrue(len(desc_key) > 0, "Description key must be nonempty")

        # 8. Localization validation
        en_path = ROOT / "loc" / "english.json"
        fr_path = ROOT / "loc" / "french.json"
        loc_path = ROOT / "lua" / "ky_localization.lua"

        self.assertTrue(en_path.exists(), "loc/english.json must exist")
        self.assertTrue(fr_path.exists(), "loc/french.json must exist")
        self.assertTrue(loc_path.exists(), "lua/ky_localization.lua must exist")

        en_data = json.loads(en_path.read_text(encoding="utf-8-sig"))
        fr_data = json.loads(fr_path.read_text(encoding="utf-8-sig"))
        loc_src = loc_path.read_text(encoding="utf-8-sig")

        self.assertIn(title_key, en_data, "english.json must contain title key")
        self.assertIsInstance(en_data[title_key], str, "english.json title value must be a string")
        self.assertTrue(len(en_data[title_key]) > 0, "english.json title value must be nonempty")
        self.assertIn(desc_key, en_data, "english.json must contain description key")
        self.assertIsInstance(en_data[desc_key], str, "english.json description value must be a string")
        self.assertTrue(len(en_data[desc_key]) > 0, "english.json description value must be nonempty")
        self.assertIn(title_key, fr_data, "french.json must contain title key")
        self.assertIsInstance(fr_data[title_key], str, "french.json title value must be a string")
        self.assertTrue(len(fr_data[title_key]) > 0, "french.json title value must be nonempty")
        self.assertIn(desc_key, fr_data, "french.json must contain description key")
        self.assertIsInstance(fr_data[desc_key], str, "french.json description value must be a string")
        self.assertTrue(len(fr_data[desc_key]) > 0, "french.json description value must be nonempty")
        self.assertIn(title_key, loc_src, "ky_localization.lua must contain title key in fallbacks")
        self.assertIn(desc_key, loc_src, "ky_localization.lua must contain description key in fallbacks")


if __name__ == '__main__':
    unittest.main()
