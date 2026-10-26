"""LOT3a -- hud/assault.lua integration: options, callback, manifest, pre-mount.

Three tests verifying end-to-end activation flow, static manifest consistency,
and activation-before-mount state preservation. RED state: assertions fail
because enable_assault, KY_ToggleAssault, runtime coordinator, menu entry and
loc keys are not yet implemented.

Required APIs (explicit -- no skips):
  kyohud._defaults.enable_assault
  MenuCallbackHandler.KY_ToggleAssault
  runtime._coordinate_assault(method_name, ...)
  HUDManager:sync_start_assault(n)
  A:mount / A:refresh_settings / A:update
  nv._entries / nv._whitelist for assault owner

No production writes. No bypass fixtures. No bash/Git/external writes.
"""
from pathlib import Path
import json as pyjson
import unittest

from test_hud_assault_render import _lua_with_assault_state, _read
from test_hud_mission_acceptance import _KY_OPTS_STUBS

ROOT = Path(__file__).resolve().parents[1]
ASSAULT_PATH = ROOT / "lua" / "hud" / "assault.lua"
OPTIONS_PATH = ROOT / "lua" / "ky_options.lua"
MENU_PATH = ROOT / "menu" / "menu.json"
LOC_EN_PATH = ROOT / "loc" / "english.json"
LOC_FR_PATH = ROOT / "loc" / "french.json"


def _lua_with_options(assault_mode=True, hunt_mode=False, assault_number=3):
    lua, ok = _lua_with_assault_state(
        difficulty_stars=3, hostages=4, converted_alive=2,
        assault_mode=assault_mode, hunt_mode=hunt_mode,
        assault_number=assault_number,
    )
    if not ok:
        return lua, ok
    lua.execute(_KY_OPTS_STUBS)

    def _py_json_encode(lua_table):
        d = {}
        for k, v in lua_table.items():
            if not isinstance(k, str):
                raise RuntimeError(f"json.encode: non-string key {k!r}")
            if not isinstance(v, (bool, int, float, str)) and v is not None:
                raise RuntimeError(f"json.encode: unsupported {type(v).__name__}")
            d[k] = v
        return pyjson.dumps(d)

    def _py_json_decode(text):
        if not isinstance(text, str):
            raise RuntimeError("json.decode: input must be string")
        d = pyjson.loads(text)
        if not isinstance(d, dict):
            raise RuntimeError("json.decode: top-level must be object")
        return lua.table_from(d)

    lua.globals().json.encode = _py_json_encode
    lua.globals().json.decode = _py_json_decode
    lua.execute("kyohud.settings = nil")
    opts_src = _read(OPTIONS_PATH)
    if opts_src:
        lua.execute(opts_src)
    return lua, opts_src is not None


_ACTIVATE_BOILER = '''
    kyohud.settings.enable_hud_foundation = true
    kyohud.settings.enable_assault = false
    kyohud.killstreak = 17
    local mgr = _G.managers.hud
    kyohud.hud.runtime:mount(mgr)
'''


class EndToEndActivationTests(unittest.TestCase):
    """_defaults.enable_assault false, old save absent -> false,
    true/false roundtrip, callback on mounts with 14 NV entries,
    HUDManager:update ticks ticker, off callback unmounts."""

    def test_end_to_end_activation(self):
        lua, ok = _lua_with_options()
        self.assertTrue(ok, "RED: ky_options.lua must exist")
        self.assertTrue(lua.eval("kyohud._defaults.enable_assault ~= nil"),
            "RED: _defaults must explicitly have enable_assault key")
        self.assertEqual(lua.eval("kyohud._defaults.enable_assault"), False,
            "RED: _defaults.enable_assault must explicitly be false")
        self.assertEqual(lua.eval("kyohud.settings.enable_assault"), False,
            "RED: settings.enable_assault must default to false")
        lua.execute('''
            for k in pairs(_ky_mem_files) do _ky_mem_files[k] = nil end
            local old = '{"enable_killfeed":true}'
            local f = io.open(kyohud._settings_path, "w"); f:write(old); f:close()
            kyohud.settings.enable_assault = true
            kyohud.Load()
            _absent_old = kyohud.settings.enable_assault
        ''')
        self.assertEqual(lua.eval("_absent_old"), False,
            "RED: old save without enable_assault must yield false after Load")
        lua.execute('''
            kyohud.settings.enable_assault = true; kyohud.Save()
            kyohud.settings.enable_assault = false; kyohud.Load()
            _rt_true = kyohud.settings.enable_assault
            kyohud.settings.enable_assault = false; kyohud.Save()
            kyohud.settings.enable_assault = true; kyohud.Load()
            _rt_false = kyohud.settings.enable_assault
        ''')
        self.assertEqual(lua.eval("_rt_true"), True,
            "RED: Save(true)/Load must preserve true")
        self.assertEqual(lua.eval("_rt_false"), False,
            "RED: Save(false)/Load must preserve false")
        self.assertTrue(lua.eval("MenuCallbackHandler.KY_ToggleAssault ~= nil"),
            "RED: MenuCallbackHandler.KY_ToggleAssault must exist")
        self.assertTrue(lua.eval(
            "type(kyohud.hud.runtime._coordinate_assault) == 'function'"),
            "RED: runtime must have _coordinate_assault method")
        lua.execute(_ACTIVATE_BOILER + '''
            local A = kyohud.hud.assault
            local fake_on = {value = function() return "on" end}
            MenuCallbackHandler.KY_ToggleAssault(nil, fake_on)
            _root_vis = A._root_panel and A._root_panel:visible()
            _root_alive = A._root_panel ~= nil
            _mounted = A._mounted
            local nv = kyohud.hud.native_visibility
            _nv_count = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == "assault" then _nv_count = _nv_count + 1 end
            end
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._root_alive),
            "RED: callback ON must create A._root_panel")
        self.assertTrue(bool(g._root_vis),
            "RED: A._root_panel must be visible")
        self.assertTrue(bool(g._mounted),
            "RED: A._mounted must be true")
        self.assertEqual(int(g._nv_count), 14,
            "RED: exactly 14 NV entries for assault (1 alpha + 13 visible)")
        self.assertEqual(lua.eval("kyohud.killstreak"), 17,
            "RED: combat sentinel 17 must be preserved")
        lua.execute('''
            _ticker_x_before = kyohud.hud.assault._ticker_a:x()
            local mgr = _G.managers.hud
            mgr:update(1.0, 0.05)
            _ticker_x_t1 = kyohud.hud.assault._ticker_a:x()
            mgr:update(1.05, 0.05)
            _ticker_x_t2 = kyohud.hud.assault._ticker_a:x()
        ''')
        g2 = lua.globals()
        self.assertLess(float(g2._ticker_x_t1), float(g2._ticker_x_before),
            "RED: ticker must move left after first update")
        self.assertLess(float(g2._ticker_x_t2), float(g2._ticker_x_t1),
            "RED: ticker must move left after second update")
        lua.execute('''
            local A_pre = kyohud.hud.assault
            local _text_panel_ref
            if A_pre._native_targets and A_pre._native_targets.text_panel then
                _text_panel_ref = A_pre._native_targets.text_panel
            end
            local fake_off = {value = function() return "off" end}
            MenuCallbackHandler.KY_ToggleAssault(nil, fake_off)
            local A = kyohud.hud.assault
            _root_gone = A._root_panel == nil
            _mounted_off = A._mounted == false
            local nv = kyohud.hud.native_visibility
            _nv_after = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == "assault" then _nv_after = _nv_after + 1 end
            end
            _alpha_off = 0
            if _text_panel_ref then
                _alpha_off = _text_panel_ref:alpha()
            end
        ''')
        g3 = lua.globals()
        self.assertTrue(bool(g3._root_gone),
            "RED: callback OFF must remove A._root_panel")
        self.assertTrue(bool(g3._mounted_off),
            "RED: A._mounted must be false after OFF")
        self.assertEqual(int(g3._nv_after), 0,
            "RED: all assault NV entries must be released after OFF")
        self.assertAlmostEqual(float(g3._alpha_off), 0.37, places=2,
            msg="RED: native text_panel alpha restored to .37 after OFF")


class StaticManifestTests(unittest.TestCase):
    """Exactly one hudmanagerpd2 assault.lua, menu entry, EN/FR parity,
    actual symbol checks (no regex-only persistence)."""

    def test_static_manifest(self):
        src = _read(ASSAULT_PATH)
        self.assertIsNotNone(src, "RED: assault.lua must exist")
        self.assertIn("RequiredScript", src,
            "RED: assault.lua must check RequiredScript")
        self.assertIn("lib/managers/hudmanagerpd2", src,
            "RED: assault.lua must gate on hudmanagerpd2 context")
        lua, ok = _lua_with_options()
        self.assertTrue(ok, "RED: ky_options.lua must load")
        menu_raw = _read(MENU_PATH)
        self.assertIsNotNone(menu_raw, "RED: menu.json must exist")
        menu = pyjson.loads(menu_raw)
        items = menu.get("items", menu) if isinstance(menu, dict) else menu
        assault_entries = [
            e for e in items
            if isinstance(e, dict) and e.get("value") == "enable_assault"
        ]
        self.assertEqual(len(assault_entries), 1,
            "RED: exactly one menu entry with value enable_assault")
        entry = assault_entries[0]
        self.assertEqual(entry.get("type"), "toggle",
            "RED: menu entry type must be toggle")
        self.assertEqual(entry.get("default_value"), False,
            "RED: menu default_value must be false")
        self.assertEqual(entry.get("callback"), "KY_ToggleAssault",
            "RED: callback must be KY_ToggleAssault")
        self.assertEqual(entry.get("enabled_by"), "enable_hud_foundation",
            "RED: enabled_by must be enable_hud_foundation")
        self.assertTrue(lua.eval("MenuCallbackHandler.KY_ToggleAssault ~= nil"),
            "RED: KY_ToggleAssault symbol must exist (not regex-only)")
        required_keys = [
            "ky_opt_enable_assault", "ky_opt_enable_assault_desc",
            "ky_hud_assault_status", "ky_hud_assault_endless",
            "ky_hud_hostages_label", "ky_hud_converted_label",
        ]
        en = pyjson.loads(_read(LOC_EN_PATH))
        fr = pyjson.loads(_read(LOC_FR_PATH))
        for key in required_keys:
            self.assertIn(key, en, f"RED: EN loc missing {key}")
            self.assertIn(key, fr, f"RED: FR loc missing {key}")
            self.assertTrue(isinstance(en[key], str) and len(en[key]) > 0,
                f"RED: EN value for {key} must be nonempty")
            self.assertTrue(isinstance(fr[key], str) and len(fr[key]) > 0,
                f"RED: FR value for {key} must be nonempty")
        lua.execute('''
            local loc_keys = {
                "ky_hud_assault_status", "ky_hud_assault_endless",
                "ky_hud_hostages_label", "ky_hud_converted_label",
            }
            _all_resolved = true
            for _, k in ipairs(loc_keys) do
                local v = managers.localization:text(k)
                if v == nil or v == "" or v:find("LOC:") == 1 then
                    _all_resolved = false
                end
            end
        ''')
        self.assertTrue(bool(lua.eval("_all_resolved")),
            "RED: all assault loc keys must resolve via localization:text")
        mod_raw = _read(ROOT / "mod.txt")
        self.assertIsNotNone(mod_raw, "RED: mod.txt must exist")
        mod = pyjson.loads(mod_raw)
        hooks = mod.get("hooks", [])
        assault_hooks = [h for h in hooks if h.get("script_path") == "lua/hud/assault.lua"]
        self.assertEqual(len(assault_hooks), 1,
            "RED: exactly one mod.txt hook for lua/hud/assault.lua")
        ah = assault_hooks[0]
        self.assertEqual(ah.get("hook_id"), "lib/managers/hudmanagerpd2",
            "RED: assault.lua hook context must be hudmanagerpd2")
        hudmgrpd2_hooks = [h for h in hooks if h.get("hook_id") == "lib/managers/hudmanagerpd2"]
        assault_idx = runtime_idx = objectives_idx = None
        for i, h in enumerate(hudmgrpd2_hooks):
            sp = h.get("script_path")
            if sp == "lua/hud/assault.lua":
                assault_idx = i
            elif sp == "lua/hud/runtime.lua":
                runtime_idx = i
            elif sp == "lua/hud/objectives.lua":
                objectives_idx = i
        self.assertIsNotNone(assault_idx,
            "RED: assault.lua must appear in hudmanagerpd2 hooks")
        self.assertIsNotNone(runtime_idx,
            "RED: runtime.lua must appear in hudmanagerpd2 hooks")
        self.assertIsNotNone(objectives_idx,
            "RED: objectives.lua must appear in hudmanagerpd2 hooks")
        self.assertGreater(assault_idx, runtime_idx,
            "RED: assault.lua must come after runtime.lua in hudmanagerpd2 hooks")
        self.assertGreater(assault_idx, objectives_idx,
            "RED: assault.lua must come after objectives.lua in hudmanagerpd2 hooks")
        loc_src = _read(OPTIONS_PATH.parent / "ky_localization.lua")
        self.assertIsNotNone(loc_src, "RED: ky_localization.lua must exist")
        fallback_keys = [
            "ky_opt_enable_assault", "ky_opt_enable_assault_desc",
            "ky_hud_assault_status", "ky_hud_assault_endless",
            "ky_hud_hostages_label", "ky_hud_converted_label",
        ]
        for key in fallback_keys:
            self.assertIn(key, loc_src,
                f"RED: ky_localization.lua fallback must contain key {key}")


class ActivationBeforeMountTests(unittest.TestCase):
    """sync_start_assault(7) BEFORE enabling: runtime refresh_settings
    must preserve active=true, number=7 over stale GroupAI false/0.
    Combat sentinel 17 preserved."""

    def test_activation_before_mount_preserves_state(self):
        lua, ok = _lua_with_options(
            assault_mode=False, hunt_mode=False, assault_number=0,
        )
        self.assertTrue(ok, "RED: assault.lua must exist")
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_assault = false
            kyohud.killstreak = 17
            _sentinel = kyohud.killstreak
            local mgr = _G.managers.hud
            kyohud.hud.runtime:mount(mgr)
            mgr:sync_start_assault(7)
            _active_pre = kyohud.hud.assault._state.active
            _number_pre = kyohud.hud.assault._state.number
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._active_pre),
            "RED: sync_start_assault(7) must set active=true before enable")
        self.assertEqual(g._number_pre, 7,
            "RED: sync_start_assault(7) must set number=7 before enable")
        lua.execute('''
            local fake_on = {value = function() return "on" end}
            MenuCallbackHandler.KY_ToggleAssault(nil, fake_on)
            local A = kyohud.hud.assault
            _active_post = A._state.active
            _number_post = A._state.number
            _root_alive = A._root_panel ~= nil
            _sentinel_after = kyohud.killstreak
        ''')
        g2 = lua.globals()
        self.assertTrue(bool(g2._active_post),
            "RED: active must remain true after enable+refresh_settings")
        self.assertEqual(g2._number_post, 7,
            "RED: number must remain 7, not stale GroupAI 0")
        self.assertTrue(bool(g2._root_alive),
            "RED: root panel must exist after enable+refresh")
        self.assertEqual(g2._sentinel_after, 17,
            "RED: combat sentinel 17 must be preserved")


class SourceRebindRuntimeTests(unittest.TestCase):
    """Source rebind: A→B→nil through real mgr:update. No test-side production
    methods, registry edits, or manual snapshot calls."""

    def test_source_rebind_runtime(self):
        lua, ok = _lua_with_options()
        self.assertTrue(ok, "RED: ky_options.lua must load")
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.killstreak = 17
            local mgr = _G.managers.hud
            kyohud.hud.runtime:mount(mgr)
            MenuCallbackHandler.KY_ToggleAssault(nil, {value = function() return "on" end})
            local A = kyohud.hud.assault
            mgr:sync_start_assault(7)
            mgr:update(1.0, 0.05)
            _a1 = A._state.active; _n1 = A._state.number
            _nv1 = 0
            for _, e in ipairs(kyohud.hud.native_visibility._entries) do
                if e.owner == "assault" then _nv1 = _nv1 + 1 end
            end
            _or1 = A._root_panel; _nc1 = A._native_corner; _c17 = kyohud.killstreak
            local B = GroupAIState:new()
            B._hostage_count = 0; B._converted = {}
            managers.groupai._state = B
            mgr:update(2.0, 0.05)
            _sb = (A._source == B); _a2 = A._state.active; _n2 = A._state.number
            _h2 = A._state.hostages; _cv2 = A._state.converted
            _nv2 = 0
            for _, e in ipairs(kyohud.hud.native_visibility._entries) do
                if e.owner == "assault" then _nv2 = _nv2 + 1 end
            end
            _or2 = A._root_panel; _si2 = (_or2 == _or1); _c17b = kyohud.killstreak
            B._hunt_mode = true; B._assault_mode = true
            mgr:sync_start_assault(8)
            mgr:update(3.0, 0.05)
            _a3 = A._state.active; _n3 = A._state.number; _e3 = A._state.endless
            _nv3 = 0
            for _, e in ipairs(kyohud.hud.native_visibility._entries) do
                if e.owner == "assault" then _nv3 = _nv3 + 1 end
            end
            _or3 = A._root_panel; _sr3 = (_or3 == _or1)
            managers.groupai.state = function() return nil end
            mgr:update(4.0, 0.05)
            _a4 = A._state.active; _n4 = A._state.number
            _nv4 = 0
            for _, e in ipairs(kyohud.hud.native_visibility._entries) do
                if e.owner == "assault" then _nv4 = _nv4 + 1 end
            end
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._a1), "sync_start_assault(7) must set active=true")
        self.assertEqual(g._n1, 7, "sync_start_assault(7) must set number=7")
        self.assertEqual(int(g._nv1), 14, "exactly 14 NV entries for assault")
        self.assertIsNotNone(g._or1, "ownedroot must exist"); self.assertIsNotNone(g._nc1, "nativecorner must exist")
        self.assertEqual(g._c17, 17, "combat sentinel 17 must be preserved")
        self.assertTrue(bool(g._sb), "A._source must be B after rebind")
        self.assertFalse(bool(g._a2), "source B false -> active false")
        self.assertEqual(g._n2, 0, "source B number=0")
        self.assertEqual(g._h2, 0, "source B hostages=0")
        self.assertEqual(g._cv2, 0, "source B converted=0")
        self.assertEqual(int(g._nv2), 0, "NV must be 0 after source rebind")
        self.assertTrue(bool(g._or2), "ownedroot must still exist")
        self.assertTrue(bool(g._si2), "ownedroot same identity")
        self.assertEqual(g._c17b, 17, "no resetcombat, sentinel 17 preserved")
        self.assertTrue(bool(g._a3), "sync_start_assault(8) must set active=true")
        self.assertEqual(g._n3, 8, "sync_start_assault(8) must set number=8")
        self.assertTrue(bool(g._e3), "hunt_mode=true -> endless=true")
        self.assertEqual(int(g._nv3), 14, "14 NV entries same root")
        self.assertTrue(bool(g._or3), "ownedroot must exist")
        self.assertTrue(bool(g._sr3), "same root identity")
        self.assertFalse(bool(g._a4), "missing source -> active false")
        self.assertIsNone(g._n4, "missing source -> number nil")
        self.assertEqual(int(g._nv4), 0, "missing source -> NV 0")
