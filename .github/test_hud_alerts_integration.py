"""LOT3b -- alerts integration: option contract, callback, manifest, render gate.

Bounded integration regressions BEFORE production wiring.

Proposed contract:
  - enable_alerts=false default in KH._defaults
  - KY_ToggleAlerts saves bool and invokes runtime refresh, independent of enable_assault
  - menu: exactly one toggle id ky_enable_alerts, value enable_alerts,
    callback KY_ToggleAlerts, default_value false, enabled_by enable_hud_foundation
  - loc keys: ky_opt_enable_alerts, ky_opt_enable_alerts_desc, ky_hud_pnr_title,
    ky_hud_pnr_inside, ky_hud_pnr_outside in fallbacks and EN/FR
  - mod.txt: exactly one alerts.lua entry RequiredScript hudmanagerpd2,
    after runtime/objectives and BEFORE assault

No production writes. No bash/Git/external writes. Missing functionality = fail not skip.
"""
from pathlib import Path
import json as pyjson
import unittest

from test_hud_assault_render import (
    _lua_with_assault_state,
    _read,
)
from test_hud_alerts_casing import (
    _lua_with_assault_and_alerts_casing_slice,
    NATIVE_CASING_FIXTURE,
)
from test_hud_alerts import (
    ALERTS_PATH,
    NATIVE_PNR_SHOW_FIXTURE,
)
from test_hud_mission_acceptance import _KY_OPTS_STUBS

ROOT = Path(__file__).resolve().parents[1]
OPTIONS_PATH = ROOT / "lua" / "ky_options.lua"
MENU_PATH = ROOT / "menu" / "menu.json"
LOC_EN_PATH = ROOT / "loc" / "english.json"
LOC_FR_PATH = ROOT / "loc" / "french.json"
LOC_LUA_PATH = ROOT / "lua" / "ky_localization.lua"


def _lua_with_options():
    lua, ok = _lua_with_assault_and_alerts_casing_slice()
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
    kyohud.settings.enable_alerts = false
    kyohud.settings.enable_assault = false
    kyohud.killstreak = 17
    local mgr = _G.managers.hud
    kyohud.hud.runtime:mount(mgr)
'''


class OptionContractTests(unittest.TestCase):
    """enable_alerts=false default; old save absent => false even if runtime
    value was true; real Save/Load true and false roundtrip."""

    def test_option_contract(self):
        lua, ok = _lua_with_options()
        self.assertTrue(ok, "RED: ky_options.lua must exist")
        self.assertTrue(lua.eval("kyohud._defaults.enable_alerts ~= nil"),
            "RED: _defaults must explicitly have enable_alerts key")
        self.assertEqual(lua.eval("kyohud._defaults.enable_alerts"), False,
            "RED: _defaults.enable_alerts must explicitly be false")
        self.assertEqual(lua.eval("kyohud.settings.enable_alerts"), False,
            "RED: settings.enable_alerts must default to false")
        lua.execute('''
            for k in pairs(_ky_mem_files) do _ky_mem_files[k] = nil end
            local old = '{"enable_killfeed":true}'
            local f = io.open(kyohud._settings_path, "w"); f:write(old); f:close()
            kyohud.settings.enable_alerts = true
            kyohud.Load()
            _absent_old = kyohud.settings.enable_alerts
        ''')
        self.assertEqual(lua.eval("_absent_old"), False,
            "RED: old save without enable_alerts must yield false after Load")
        lua.execute('''
            kyohud.settings.enable_alerts = true; kyohud.Save()
            kyohud.settings.enable_alerts = false; kyohud.Load()
            _rt_true = kyohud.settings.enable_alerts
            kyohud.settings.enable_alerts = false; kyohud.Save()
            kyohud.settings.enable_alerts = true; kyohud.Load()
            _rt_false = kyohud.settings.enable_alerts
        ''')
        self.assertEqual(lua.eval("_rt_true"), True,
            "RED: Save(true)/Load must preserve true")
        self.assertEqual(lua.eval("_rt_false"), False,
            "RED: Save(false)/Load must preserve false")


class CallbackContractTests(unittest.TestCase):
    """KY_ToggleAlerts persists on/off through Save (decoded in-memory file)
    and Load, without changing enable_assault, for both enable_assault true
    and enable_assault false independence cases."""

    def test_callback_contract(self):
        lua, ok = _lua_with_options()
        self.assertTrue(ok, "RED: ky_options.lua must load")
        self.assertTrue(lua.eval("MenuCallbackHandler.KY_ToggleAlerts ~= nil"),
            "RED: MenuCallbackHandler.KY_ToggleAlerts must exist")
        lua.execute(_ACTIVATE_BOILER + '''
            kyohud.settings.enable_assault = false
            local fake_on = {value = function() return "on" end}
            MenuCallbackHandler.KY_ToggleAlerts(nil, fake_on)
            _alerts_on = kyohud.settings.enable_alerts
            _assault_unchanged_1 = kyohud.settings.enable_assault

            local file_on = _ky_mem_files[kyohud._settings_path]
            assert(type(file_on) == "string" and #file_on > 0,
                "RED: Save must write nonempty in-memory file")
            local decoded_on = json.decode(file_on)
            _file_alerts_on = decoded_on.enable_alerts
            _file_assault_on = decoded_on.enable_assault

            kyohud.settings.enable_alerts = false
            kyohud.Load()
            _after_load_on = kyohud.settings.enable_alerts
        ''')
        g = lua.globals()
        self.assertEqual(g._alerts_on, True,
            "RED: callback ON must set enable_alerts=true")
        self.assertEqual(g._assault_unchanged_1, False,
            "RED: callback ON must not change enable_assault")
        self.assertEqual(g._file_alerts_on, True,
            "RED: decoded in-memory file must contain enable_alerts=true after callback ON")
        self.assertEqual(g._file_assault_on, False,
            "RED: decoded in-memory file must preserve enable_assault=false after callback ON")
        self.assertEqual(g._after_load_on, True,
            "RED: Load after Save(true) must restore enable_alerts=true")
        lua.execute('''
            local fake_off = {value = function() return "off" end}
            MenuCallbackHandler.KY_ToggleAlerts(nil, fake_off)
            _alerts_off = kyohud.settings.enable_alerts
            _assault_unchanged_2 = kyohud.settings.enable_assault

            local file_off = _ky_mem_files[kyohud._settings_path]
            local decoded_off = json.decode(file_off)
            _file_alerts_off = decoded_off.enable_alerts
            _file_assault_off = decoded_off.enable_assault

            kyohud.settings.enable_alerts = true
            kyohud.Load()
            _after_load_off = kyohud.settings.enable_alerts
        ''')
        g2 = lua.globals()
        self.assertEqual(g2._alerts_off, False,
            "RED: callback OFF must set enable_alerts=false")
        self.assertEqual(g2._assault_unchanged_2, False,
            "RED: callback OFF must not change enable_assault")
        self.assertEqual(g2._file_alerts_off, False,
            "RED: decoded in-memory file must contain enable_alerts=false after callback OFF")
        self.assertEqual(g2._file_assault_off, False,
            "RED: decoded in-memory file must preserve enable_assault=false after callback OFF")
        self.assertEqual(g2._after_load_off, False,
            "RED: Load after Save(false) must restore enable_alerts=false")
        lua.execute('''
            kyohud.settings.enable_assault = true
            local fake_on2 = {value = function() return "on" end}
            MenuCallbackHandler.KY_ToggleAlerts(nil, fake_on2)
            local file_a = _ky_mem_files[kyohud._settings_path]
            local decoded_a = json.decode(file_a)
            _file_alerts_assault_true = decoded_a.enable_alerts
            _file_assault_preserved = decoded_a.enable_assault

            local fake_off2 = {value = function() return "off" end}
            MenuCallbackHandler.KY_ToggleAlerts(nil, fake_off2)
            local file_b = _ky_mem_files[kyohud._settings_path]
            local decoded_b = json.decode(file_b)
            _file_alerts_assault_true_off = decoded_b.enable_alerts
            _file_assault_still_true = decoded_b.enable_assault
        ''')
        g3 = lua.globals()
        self.assertEqual(g3._file_alerts_assault_true, True,
            "RED: callback ON with enable_assault=true must set enable_alerts=true in file")
        self.assertEqual(g3._file_assault_preserved, True,
            "RED: enable_assault=true must be preserved in saved file when callback toggles alerts")
        self.assertEqual(g3._file_alerts_assault_true_off, False,
            "RED: callback OFF with enable_assault=true must set enable_alerts=false in file")
        self.assertEqual(g3._file_assault_still_true, True,
            "RED: enable_assault=true must remain preserved after callback OFF")


class ManifestContractTests(unittest.TestCase):
    """Exactly one hudmanagerpd2 alerts.lua in mod.txt, after runtime/objectives
    and before assault; menu toggle; EN/FR parity; fallback keys."""

    def test_manifest_contract(self):
        src = _read(ALERTS_PATH)
        self.assertIsNotNone(src, "RED: alerts.lua must exist")
        self.assertIn("RequiredScript", src,
            "RED: alerts.lua must check RequiredScript")
        self.assertIn("lib/managers/hudmanagerpd2", src,
            "RED: alerts.lua must gate on hudmanagerpd2 context")
        mod_raw = _read(ROOT / "mod.txt")
        self.assertIsNotNone(mod_raw, "RED: mod.txt must exist")
        mod = pyjson.loads(mod_raw)
        hooks = mod.get("hooks", [])
        alerts_hooks = [h for h in hooks if h.get("script_path") == "lua/hud/alerts.lua"]
        self.assertEqual(len(alerts_hooks), 1,
            "RED: exactly one mod.txt hook for lua/hud/alerts.lua")
        ah = alerts_hooks[0]
        self.assertEqual(ah.get("hook_id"), "lib/managers/hudmanagerpd2",
            "RED: alerts.lua hook context must be hudmanagerpd2")
        hudmgrpd2_hooks = [h for h in hooks if h.get("hook_id") == "lib/managers/hudmanagerpd2"]
        alerts_idx = runtime_idx = objectives_idx = assault_idx = None
        for i, h in enumerate(hudmgrpd2_hooks):
            sp = h.get("script_path")
            if sp == "lua/hud/alerts.lua":
                alerts_idx = i
            elif sp == "lua/hud/runtime.lua":
                runtime_idx = i
            elif sp == "lua/hud/objectives.lua":
                objectives_idx = i
            elif sp == "lua/hud/assault.lua":
                assault_idx = i
        self.assertIsNotNone(alerts_idx,
            "RED: alerts.lua must appear in hudmanagerpd2 hooks")
        self.assertIsNotNone(runtime_idx,
            "RED: runtime.lua must appear in hudmanagerpd2 hooks")
        self.assertIsNotNone(objectives_idx,
            "RED: objectives.lua must appear in hudmanagerpd2 hooks")
        self.assertIsNotNone(assault_idx,
            "RED: assault.lua must appear in hudmanagerpd2 hooks")
        self.assertGreater(alerts_idx, runtime_idx,
            "RED: alerts.lua must come after runtime.lua")
        self.assertGreater(alerts_idx, objectives_idx,
            "RED: alerts.lua must come after objectives.lua")
        self.assertGreater(assault_idx, alerts_idx,
            "RED: assault.lua must come after alerts.lua")
        menu_raw = _read(MENU_PATH)
        self.assertIsNotNone(menu_raw, "RED: menu.json must exist")
        menu = pyjson.loads(menu_raw)
        items = menu.get("items", menu) if isinstance(menu, dict) else menu
        alerts_entries = [
            e for e in items
            if isinstance(e, dict) and e.get("value") == "enable_alerts"
        ]
        self.assertEqual(len(alerts_entries), 1,
            "RED: exactly one menu entry with value enable_alerts")
        entry = alerts_entries[0]
        self.assertEqual(entry.get("type"), "toggle",
            "RED: menu entry type must be toggle")
        self.assertEqual(entry.get("default_value"), False,
            "RED: menu default_value must be false")
        self.assertEqual(entry.get("callback"), "KY_ToggleAlerts",
            "RED: callback must be KY_ToggleAlerts")
        self.assertEqual(entry.get("enabled_by"), "enable_hud_foundation",
            "RED: enabled_by must be enable_hud_foundation")
        lua, ok = _lua_with_options()
        self.assertTrue(ok, "RED: ky_options.lua must load")
        self.assertTrue(lua.eval("MenuCallbackHandler.KY_ToggleAlerts ~= nil"),
            "RED: KY_ToggleAlerts symbol must exist (not regex-only)")
        required_keys = [
            "ky_opt_enable_alerts", "ky_opt_enable_alerts_desc",
            "ky_hud_pnr_title", "ky_hud_pnr_inside", "ky_hud_pnr_outside",
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
        loc_src = _read(LOC_LUA_PATH)
        self.assertIsNotNone(loc_src, "RED: ky_localization.lua must exist")
        for key in required_keys:
            self.assertIn(key, loc_src,
                f"RED: ky_localization.lua fallback must contain key {key}")


class RenderContractTests(unittest.TestCase):
    """enable_alerts=true + active PNR renders standard PNR (8 NV) and off
    restores exact properties; positive PNR re-established before foundation off."""

    def test_render_on_off_foundation(self):
        lua, ok = _lua_with_options()
        self.assertTrue(ok, "RED: ky_options.lua must load")
        self.assertTrue(lua.eval("kyohud.hud.alerts ~= nil"),
            "RED: kyohud.hud.alerts must exist")
        lua.execute(_ACTIVATE_BOILER + '''
            local AL = kyohud.hud.alerts
            local RT = kyohud.hud.runtime
            local mgr = _G.managers.hud
            local nv = kyohud.hud.native_visibility
            local state = managers.groupai:state()

            local fake_on = {value = function() return "on" end}
            MenuCallbackHandler.KY_ToggleAlerts(nil, fake_on)

            state._point_of_no_return_timer = 65.9
            state._point_of_no_return_id = 101
            state._point_of_no_return_tweak_id = "noreturn"
            state._is_inside_point_of_no_return = false
            mgr:show_point_of_no_return_timer("noreturn")
            mgr:feed_point_of_no_return_timer(65.9, false)
            mgr:update(1.0, 0.05)
            assert(AL:_verify_render() == true,
                "RED: AL:_verify_render() must be true during active PNR")

            _root_alive = AL._root_panel ~= nil
            _root_visible = AL._root_panel ~= nil and AL._root_panel:visible() == true
            _mounted_on = AL._mounted

            local pnr_timer = AL._root_panel and AL._root_panel:child("pnr_timer")
            _timer_text = pnr_timer and pnr_timer:text() or nil
            local pnr_status = AL._root_panel and AL._root_panel:child("pnr_status")
            _status_text = pnr_status and pnr_status:text() or nil

            _nv_count = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == "alerts" then _nv_count = _nv_count + 1 end
            end
            _sentinel_on = kyohud.killstreak
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._root_alive),
            "RED: AL._root_panel must exist after callback ON + PNR show + update")
        self.assertTrue(bool(g._root_visible),
            "RED: AL._root_panel must be visible during active standard PNR")
        self.assertTrue(bool(g._mounted_on),
            "RED: callback ON must mount alerts")
        self.assertEqual(g._timer_text, "01:05",
            "RED: pnr_timer text for 65.9s must be '01:05', got " + repr(g._timer_text))
        status = g._status_text
        self.assertTrue(isinstance(status, str) and len(status) > 0,
            "RED: pnr_status text must be nonempty, got " + repr(status))
        self.assertTrue(status.upper().find("OUTSIDE") >= 0 if status else False,
            "RED: pnr_status when is_inside=false must contain OUTSIDE, got " + repr(status))
        self.assertEqual(int(g._nv_count), 8,
            "RED: exactly 8 NV entries for alerts (standard PNR leaves)")
        self.assertEqual(g._sentinel_on, 17,
            "RED: combat sentinel 17 must be preserved")
        lua.execute('''
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            local fake_off = {value = function() return "off" end}
            MenuCallbackHandler.KY_ToggleAlerts(nil, fake_off)

            _root_gone = AL._root_panel == nil
            _mounted_off = AL._mounted == false

            _nv_after = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == "alerts" then _nv_after = _nv_after + 1 end
            end

            local pnr_leaves = {
                _na.icon_noreturnbox,
                _na.pnr_text,
                _na.pnr_timer,
                _na.pnr_bg,
                _na.pnr_lt,
                _na.pnr_lb,
                _na.pnr_rt,
                _na.pnr_rb,
            }
            _leaf_vis_ok = true
            for _, leaf in ipairs(pnr_leaves) do
                if leaf._name == "right_bottom" then
                    if leaf:visible() ~= false then _leaf_vis_ok = false end
                else
                    if leaf:visible() ~= true then _leaf_vis_ok = false end
                end
            end

            _sentinel_off = kyohud.killstreak
        ''')
        g2 = lua.globals()
        self.assertTrue(bool(g2._root_gone),
            "RED: callback OFF must remove AL._root_panel")
        self.assertTrue(bool(g2._mounted_off),
            "RED: AL._mounted must be false after OFF")
        self.assertEqual(int(g2._nv_after), 0,
            "RED: all alerts NV entries must be released after OFF")
        self.assertTrue(bool(g2._leaf_vis_ok),
            "RED: native PNR leaves must restore exact original visibility after OFF")
        self.assertEqual(g2._sentinel_off, 17,
            "RED: combat sentinel 17 must be preserved after OFF")
        lua.execute('''
            local AL = kyohud.hud.alerts
            local RT = kyohud.hud.runtime
            local mgr = _G.managers.hud
            local nv = kyohud.hud.native_visibility
            local state = managers.groupai:state()

            local fake_reon = {value = function() return "on" end}
            MenuCallbackHandler.KY_ToggleAlerts(nil, fake_reon)

            state._point_of_no_return_timer = 65.9
            state._point_of_no_return_id = 101
            state._point_of_no_return_tweak_id = "noreturn"
            state._is_inside_point_of_no_return = false
            mgr:show_point_of_no_return_timer("noreturn")
            mgr:feed_point_of_no_return_timer(65.9, false)
            mgr:update(1.1, 0.05)
            assert(AL:_verify_render() == true,
                "RED: AL:_verify_render() must be true during re-established PNR")

            _repr_root_alive = AL._root_panel ~= nil
            _repr_root_visible = AL._root_panel ~= nil and AL._root_panel:visible() == true
            _repr_nv = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == "alerts" then _repr_nv = _repr_nv + 1 end
            end

            local fake_foundation_off = {value = function() return "off" end}
            MenuCallbackHandler.KY_ToggleHudFoundation(nil, fake_foundation_off)

            _foundation_off_root = AL._root_panel == nil
            _foundation_off_mounted = AL._mounted == false
            _foundation_off_nv = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == "alerts" then _foundation_off_nv = _foundation_off_nv + 1 end
            end
        ''')
        g3 = lua.globals()
        self.assertTrue(bool(g3._repr_root_alive),
            "RED: positive PNR must be re-established before foundation OFF")
        self.assertTrue(bool(g3._repr_root_visible),
            "RED: re-established positive PNR must have visible root")
        self.assertEqual(int(g3._repr_nv), 8,
            "RED: re-established positive PNR must have 8 NV entries")
        self.assertTrue(bool(g3._foundation_off_root),
            "RED: foundation off must remove AL._root_panel")
        self.assertTrue(bool(g3._foundation_off_mounted),
            "RED: foundation off must set AL._mounted=false")
        self.assertEqual(int(g3._foundation_off_nv), 0,
            "RED: foundation off must release all alerts NV entries")


class ContextGateTests(unittest.TestCase):
    """Wrong RequiredScript registers no alerts hooks; correct context with
    native-shaped HUDManager PNR/casing/open-left installed BEFORE alerts
    chunk loads registers exactly 11 hook IDs (5 PNR + 2 global + 4 casing);
    repeated load does not duplicate."""

    def test_context_gate_and_idempotency(self):
        lua, ok = _lua_with_assault_state()
        self.assertTrue(ok, "RED: base state must load")
        lua.execute("kyohud.settings.enable_alerts = false")
        lua.execute('RequiredScript = "unrelated/wrong_context"')
        lua.execute(NATIVE_PNR_SHOW_FIXTURE)
        lua.execute(NATIVE_CASING_FIXTURE)
        lua.execute(r'''
            _HUDBGBox_animate_open_left_called = false
            function HUDBGBox_animate_open_left(panel, wait_t, target_w, done_cb, config)
                coroutine.yield()
                if type(done_cb) == "function" then done_cb() end
            end
            function HUDAssaultCorner:_animate_show_texts(anim_object, texts)
                coroutine.yield()
            end
        ''')
        alerts_src = _read(ALERTS_PATH)
        self.assertIsNotNone(alerts_src, "RED: alerts.lua must exist")
        lua.execute(alerts_src)
        lua.execute('''
            _wrong_hooks = 0
            for _, e in ipairs(Hooks._all) do
                if e.id and tostring(e.id):find("Alerts") then
                    _wrong_hooks = _wrong_hooks + 1
                end
            end
        ''')
        self.assertEqual(int(lua.globals()._wrong_hooks), 0,
            "RED: wrong RequiredScript must register no alerts hooks")
        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        lua.execute(alerts_src)
        lua.execute('''
            _first_load_ids = {}
            _first_load_count = 0
            for _, e in ipairs(Hooks._all) do
                if e.id and tostring(e.id):find("Alerts") then
                    _first_load_count = _first_load_count + 1
                    _first_load_ids[_first_load_count] = tostring(e.id)
                end
            end
        ''')
        first_count = int(lua.globals()._first_load_count)
        self.assertEqual(first_count, 11,
            "RED: correct context must register exactly 11 alerts hooks "
            "(5 PNR + 2 global + 4 casing), got " + str(first_count))
        lua.execute(alerts_src)
        lua.execute('''
            _second_load_count = 0
            for _, e in ipairs(Hooks._all) do
                if e.id and tostring(e.id):find("Alerts") then
                    _second_load_count = _second_load_count + 1
                end
            end
        ''')
        self.assertEqual(int(lua.globals()._second_load_count), 11,
            "RED: repeated load must not duplicate alerts hooks, expected 11 got "
            + str(int(lua.globals()._second_load_count)))


class HUDSubgraphTests(unittest.TestCase):
    """Execute HUD subgraph from actual manifest order; require alerts present;
    exercise native show/feed and mgr:update with combat sentinel preserved.
    Distinct from load_order full fresh graph replay.
    """

    def test_hud_subgraph_manifest_order(self):
        meta = pyjson.loads(_read(ROOT / "mod.txt"))
        paths = [h["script_path"] for h in meta["hooks"]
                 if h["hook_id"] == "lib/managers/hudmanagerpd2"]
        self.assertIn("lua/hud/alerts.lua", paths,
            "RED: alerts.lua must appear in hudmanagerpd2 hooks")
        alerts_idx = paths.index("lua/hud/alerts.lua")

        lua, ok = _lua_with_assault_state()
        self.assertTrue(ok, "RED: base state must load")
        lua.execute('kyohud.settings.enable_alerts = true')
        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        lua.execute(NATIVE_PNR_SHOW_FIXTURE)
        lua.execute(NATIVE_CASING_FIXTURE)
        lua.execute(r'''
            _HUDBGBox_animate_open_left_called = false
            function HUDBGBox_animate_open_left(panel, wait_t, target_w, done_cb, config)
                coroutine.yield()
                if type(done_cb) == "function" then done_cb() end
            end
            function HUDAssaultCorner:_animate_show_texts(anim_object, texts)
                coroutine.yield()
            end
        ''')

        self.assertIsNotNone(_read(ROOT / "lua" / "hud" / "alerts.lua"),
            "RED: alerts.lua source must be readable")
        for p in paths:
            if p.startswith("lua/hud/"):
                lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
                src = _read(ROOT / p)
                self.assertIsNotNone(src,
                    f"RED: {p} must be loadable in manifest order")
                lua.execute(src)

        self.assertTrue(lua.eval("kyohud.hud.alerts ~= nil"),
            "RED: kyohud.hud.alerts must exist after subgraph load")
        self.assertTrue(lua.eval("type(kyohud.hud.alerts.mount) == 'function'"),
            "RED: alerts.mount must be a function")
        self.assertTrue(lua.eval("type(kyohud.hud.alerts.update) == 'function'"),
            "RED: alerts.update must be a function")
        self.assertTrue(lua.eval("type(kyohud.hud.alerts.snapshot) == 'function'"),
            "RED: alerts.snapshot must be a function")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local mgr = _G.managers.hud
            local nv = kyohud.hud.native_visibility
            local state = managers.groupai:state()

            RT:mount(mgr)

            state._point_of_no_return_timer = 65.9
            state._point_of_no_return_id = 101
            state._point_of_no_return_tweak_id = "noreturn"
            state._is_inside_point_of_no_return = false
            mgr:show_point_of_no_return_timer("noreturn")
            mgr:feed_point_of_no_return_timer(65.9, false)
            mgr:update(1.0, 0.05)

            assert(type(AL._root_panel) == "table",
                "RED: AL._root_panel must exist after native show+feed+update")
            assert(AL._root_panel:visible() == true,
                "RED: AL._root_panel must be visible")
            assert(AL:_verify_render() == true,
                "RED: AL:_verify_render() must return true")

            local pnr_timer = AL._root_panel:child("pnr_timer")
            assert(type(pnr_timer) == "table" and pnr_timer:text() == "01:05",
                "RED: pnr_timer must be '01:05', got " .. tostring(pnr_timer and pnr_timer:text()))

            local pnr_status = AL._root_panel:child("pnr_status")
            local st = pnr_status and pnr_status:text() or ""
            assert(st:upper():find("OUTSIDE") ~= nil,
                "RED: pnr_status must contain OUTSIDE, got " .. tostring(st))

            local nv8 = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then nv8 = nv8 + 1 end
            end
            assert(nv8 == 8,
                "RED: expected 8 NV entries, got " .. tostring(nv8))

            assert(kyohud.killstreak == _sentinel_before,
                "RED: combat sentinel must be preserved, got "
                .. tostring(kyohud.killstreak) .. " expected " .. tostring(_sentinel_before))
        ''')


class NativeCasingTextContractTests(unittest.TestCase):
    """Native casing normal/civilian text assertions using reusable helper.
    After native show_casing and RT:update with enable_alerts=true, owned
    casing ticker text must contain the correct mode label."""

    def test_normal_casing_ticker_text(self):
        lua, ok = _lua_with_assault_and_alerts_casing_slice(True)
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")
        lua.execute('''
            kyohud.settings.enable_alerts = true
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)
            assert(type(AL._casing_root_panel) == "table" and AL._casing_root_panel:visible() == true,
                "RED: positive casing must have visible root")
            assert(type(AL._casing_a) == "table",
                "RED: _casing_a must exist")
            local a_text = AL._casing_a:text()
            assert(type(a_text) == "string" and #a_text > 0,
                "RED: _casing_a text must be nonempty, got " .. tostring(a_text))
            assert(a_text:find("CASING MODE") ~= nil,
                "RED: normal casing ticker must contain CASING MODE, got " .. tostring(a_text))
        ''')

    def test_civilian_casing_ticker_text(self):
        lua, ok = _lua_with_assault_and_alerts_casing_slice(True)
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")
        lua.execute('''
            kyohud.settings.enable_alerts = true
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            RT:mount(managers.hud)
            managers.hud:show_casing("civilian")
            RT:update(managers.hud, 1.0, 0.05)
            assert(type(AL._casing_root_panel) == "table" and AL._casing_root_panel:visible() == true,
                "RED: positive civilian casing must have visible root")
            assert(type(AL._casing_a) == "table",
                "RED: _casing_a must exist")
            local a_text = AL._casing_a:text()
            assert(type(a_text) == "string" and #a_text > 0,
                "RED: _casing_a text must be nonempty, got " .. tostring(a_text))
            assert(a_text:find("CIVILIAN MODE") ~= nil,
                "RED: civilian casing ticker must contain CIVILIAN MODE, got " .. tostring(a_text))
        ''')


class StaleCasingProvenanceTests(unittest.TestCase):
    """Regression: stale native casing text_list with unknown mode must not
    leave owned casing visible. After replacement state, owned root must hide,
    _verify_render false, no alerts records, native casing text alpha restored
    to .43 and original leaves restored. Desired fallback, not current bug."""

    def test_stale_casing_unknown_mode_desired_fallback(self):
        lua, ok = _lua_with_assault_and_alerts_casing_slice(True)
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")
        lua.execute('''
            kyohud.settings.enable_alerts = true
            local AL = kyohud.hud.alerts
            local mgr = _G.managers.hud
            local nv = kyohud.hud.native_visibility

            kyohud.hud.runtime:mount(mgr)
            mgr:show_casing(nil)
            mgr:update(1.0, 0.05)
            assert(type(AL._casing_root_panel) == "table" and AL._casing_root_panel:visible() == true,
                "RED: positive casing must have visible root initially")

            local nv7 = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then nv7 = nv7 + 1 end
            end
            assert(nv7 == 7, "RED: positive casing must have 7 NV entries, got " .. tostring(nv7))

            local corner = _G.managers.hud._hud_assault_corner
            local casing_bg = corner._casing_bg_box
            casing_bg:script().text_list = {"custom_unknown"}

            local GroupAIState = _G.GroupAIState
            _G.managers.groupai._state = GroupAIState:new()

            mgr:update(2.0, 0.05)

            _owned_root_hidden = AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false
            _verify_render_false = AL:_verify_render() == false

            _alerts_records = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then _alerts_records = _alerts_records + 1 end
            end

            _native_alpha_ok = math.abs(_na.cas_text_panel:alpha() - 0.43) < 0.01

            local casing_leaves = {
                _na.icon_casingbox,
                _na.cas_bg,
                _na.cas_lt,
                _na.cas_lb,
                _na.cas_rt,
                _na.cas_rb,
            }
            _native_leaves_restored = true
            for i, leaf in ipairs(casing_leaves) do
                if i <= 5 then
                    if leaf:visible() ~= true then _native_leaves_restored = false end
                else
                    if leaf:visible() ~= false then _native_leaves_restored = false end
                end
            end
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._owned_root_hidden),
            "DESIRED: owned casing root must be hidden after stale unknown mode, got visible")
        self.assertTrue(bool(g._verify_render_false),
            "DESIRED: AL:_verify_render() must be false after stale unknown mode")
        self.assertEqual(int(g._alerts_records), 0,
            "DESIRED: no alerts records after stale unknown mode, got " + str(int(g._alerts_records)))
        self.assertTrue(bool(g._native_alpha_ok),
            "DESIRED: native casing text alpha must be restored to .43, got " + repr(g._native_alpha_ok))
        self.assertTrue(bool(g._native_leaves_restored),
            "DESIRED: native casing leaves must be restored to original visibility")



if __name__ == "__main__":
    unittest.main()
