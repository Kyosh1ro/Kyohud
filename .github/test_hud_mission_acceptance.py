"""RED final acceptance slice -- hud/mission.lua cross-cutting acceptance tests.

Imports fixtures from test_hud_mission, enhances doubles with real Diesel API
shapes (shape/text/font_size/set_visible/alpha, creation/setter counts, errors
controllable). Native leaf _hud_heist_timer._timer_text has real alpha
getter/setter. Hooks wrap real class methods and execute callbacks automatically
in production order. Loads actual chunks: layout, native_visibility, runtime,
mission. Asserts IDs unique, repeated load safe, early class context.

No production edits. Coordinator executes RED.
"""
from pathlib import Path
import json as pyjson
import unittest
from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
from test_hud_mission import _read, MISSION_PATH, LAYOUT_PATH, RUNTIME_PATH, NATIVE_VIS_PATH

_ENH_TIMER = r'''
HUDHeistTimer = {}; HUDHeistTimer.__index = HUDHeistTimer
function HUDHeistTimer:new(tweak_hud)
    local obj = setmetatable({}, self)
    obj._last_time = 0
    obj._enabled = not (tweak_hud and tweak_hud.no_timer)
    obj._timer_text = {
        _text = "00:00", _alpha = 0.37, _font_size = 24, _visible = true,
        text = function(s) return s._text end,
        set_text = function(s, str) if s._throw_on_set then error("broken") end; s._text = str end,
        alpha = function(s) return s._alpha end,
        set_alpha = function(s, a) if s._throw_alpha then error("broken") end; s._alpha = a end,
        font_size = function(s) return s._font_size end,
        set_visible = function(s, v) s._visible = v end,
        visible = function(s) return s._visible end,
    }
    return obj
end
function HUDHeistTimer:set_time(time)
    local inv = false; if time < 0 then inv = true; time = math.abs(time) end
    if not self._enabled or not inv and math.floor(time) < self._last_time then return end
    self._last_time = time; time = math.floor(time)
    local h = math.floor(time/3600); time = time - h*3600
    local m = math.floor(time/60); time = time - m*60; local s = math.round(time)
    local t = h > 0 and (h < 10 and "0"..h or h)..":" or ""
    t = t..(m < 10 and "0"..m or m)..":"..(s < 10 and "0"..s or s)
    self._timer_text:set_text(t)
end
function HUDHeistTimer:modify_time(time) self:set_time(self._last_time + time) end
function HUDHeistTimer:reset() self._last_time = 0 end
'''
_ENH_HM = r'''
HUDManager._hud_heist_timer = nil
function HUDManager:_create_heist_timer() local tweaks = tweak_data.levels[Global.game_settings.level_id].hud or {}; self._hud_heist_timer = HUDHeistTimer:new(tweaks) end
function HUDManager:feed_heist_time(t) self._hud_heist_timer:set_time(t) end
function HUDManager:modify_heist_time(t) self._hud_heist_timer:modify_time(t) end
function HUDManager:loot_value_updated() end
'''
_GPC = r'''
Application = Application or {}
if not Application._time then Application._time = 0 end
function Application:time() return Application._time end
function Application:_set_time(t) Application._time = t end
GamePlayCentralManager = {}; GamePlayCentralManager.__index = GamePlayCentralManager
function GamePlayCentralManager:new()
    local o = setmetatable({}, self)
    o._heist_timer = {running=false,start_time=0,offset_time=0}
    return o
end
function GamePlayCentralManager:start_heist_timer()
    self._heist_timer.running = true
    self._heist_timer.start_time = Application:time()
    self._heist_timer.offset_time = 0
end
function GamePlayCentralManager:stop_heist_timer()
    self._heist_timer.running = false
end
function GamePlayCentralManager:sync_heist_time(time, id)
    if id == 1 then
        self._heist_timer.offset_time = time
        self._heist_timer.start_time = Application:time()
    elseif id == 2 then
    end
end
function GamePlayCentralManager:save(data)
    data = data or {}
    local state = {}
    state.heist_timer = Application:time() - self._heist_timer.start_time
    state.heist_timer_running = self._heist_timer.running
    data.GamePlayCentralManager = state
    return data
end
function GamePlayCentralManager:load(data)
    local state = data.GamePlayCentralManager
    if state and state.heist_timer then
        self._heist_timer.offset_time = state.heist_timer
        self._heist_timer.start_time = Application:time()
        self._heist_timer.running = state.heist_timer_running
    end
end
function GamePlayCentralManager:get_heist_timer()
    if not self._heist_timer then return 0 end
    return Application:time() - (self._heist_timer.start_time or 0) + (self._heist_timer.offset_time or 0)
end
managers = managers or {}; managers.game_play_central = GamePlayCentralManager:new()
'''
_STUBS = '''
kyohud = kyohud or {}; Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end
kyohud.settings = kyohud.settings or {}
if kyohud.settings.enable_hud_foundation == nil then kyohud.settings.enable_hud_foundation = false end
if kyohud.settings.hud_scale == nil then kyohud.settings.hud_scale = 1.0 end
if kyohud.settings.enable_mission == nil then kyohud.settings.enable_mission = false end
if not math.round then function math.round(v) return math.floor(v + 0.5) end end
Hooks = {_all = {}, _wrap = {}}
function Hooks:PostHook(class, method, id, fn)
    table.insert(self._all, {kind="post", class=class, method=method, id=id, fn=fn})
    if type(class) == "table" and type(class[method]) == "function" then
        local orig = class[method]; local key = tostring(class)..":"..method
        if not self._wrap[key] then
            self._wrap[key] = true
            class[method] = function(self, ...)
                local r = {orig(self, ...)}
                for _, e in ipairs(Hooks._all) do
                    if e.kind=="post" and e.class==class and e.method==method then e.fn(self, ...) end
                end
                return unpack(r)
            end
        end
    end
end
function Hooks:PreHook(class, method, id, fn)
    table.insert(self._all, {kind="pre", class=class, method=method, id=id, fn=fn})
    if type(class) == "table" and type(class[method]) == "function" then
        local orig = class[method]; local key = tostring(class)..":"..method
        if not self._wrap[key] then
            self._wrap[key] = true
            class[method] = function(self, ...)
                for _, e in ipairs(Hooks._all) do
                    if e.kind=="pre" and e.class==class and e.method==method then e.fn(self, ...) end
                end
                return orig(self, ...)
            end
        end
    end
end
function Hooks:Add(id, event, fn) end
function log(...) end; function alive(x) return x ~= nil and x._alive ~= false end
Color = setmetatable({}, {__call = function(...) return {} end})
HUDManager = {}
for _, m in ipairs{"update","init_finalize","_setup_player_info_hud_pd2","resolution_changed",
    "set_disabled","set_enabled","set_freeflight_disabled","set_freeflight_enabled","destroy"} do
    HUDManager[m] = function() end
end
HUDManager.loot_value_updated = function() end
LootManager = {}; LootManager.__index = LootManager
function LootManager:new()
    local obj = setmetatable({}, self); obj._global = {secured = {}}; return obj
end
function LootManager:sync_load(data)
    self._global = data.LootManager
end
function LootManager:get_secured_bags_amount(is_vehicle)
    local amount = 0
    for _, data in ipairs(self._global.secured) do
        if not tweak_data.carry.small_loot[data.carry_id] then
            amount = amount + 1
        end
    end
    return amount
end
GamePlayCentralManager = {}; GamePlayCentralManager.__index = GamePlayCentralManager
function GamePlayCentralManager:new()
    local o = setmetatable({}, self); o._heist_timer = {running=false,start_time=0,offset_time=0}; return o
end
managers = {}
managers.loot = LootManager:new()
PlayerBase = {PLAYER_INFO_HUD_PD2="player_info_hud_pd2", PLAYER_INFO_HUD_FULLSCREEN_PD2="player_info_hud_fullscreen_pd2"}
tweak_data = tweak_data or {}; tweak_data.hud = tweak_data.hud or {}
if tweak_data.hud.medium_font_noshadow == nil then tweak_data.hud.medium_font_noshadow = "fonts/font_medium_mf" end
tweak_data.carry = tweak_data.carry or {small_loot = {}}
Global = {game_settings = {level_id = "test"}}
tweak_data.levels = tweak_data.levels or {}
tweak_data.levels.test = tweak_data.levels.test or {hud = {}}
_fake_time = 0
function _advance_time(dt) _fake_time = _fake_time + (dt or 0) end
function _get_time() return _fake_time end
'''
_DIESEL = '''
_panel_id = 0; _create_count = 0; _set_text_count = 0
function _make_panel(name)
    _panel_id = _panel_id + 1
    local p = {_alive=true,_visible=true,_alpha=1,_children={},_name=name or ("p".._panel_id),_w=1920,_h=1080,_x=0,_y=0}
    function p:w() return self._w end; function p:h() return self._h end
    function p:x() return self._x or 0 end; function p:y() return self._y or 0 end
    function p:set_shape(x,y,w,h) self._x=x;self._y=y;self._w=w;self._h=h end
    function p:set_visible(v) self._visible=v end; function p:visible() return self._visible end
    function p:set_alpha(a) self._alpha=a end; function p:alpha() return self._alpha end
    function p:child(n) return self._children[n] end
    function p:remove(c) if c then for k,v in pairs(self._children) do if v==c then self._children[k]=nil; c._alive=false; return end end end end
    function p:panel(opts)
        _create_count = _create_count + 1; local ch = _make_panel(opts and opts.name)
        if opts then if opts.w then ch._w=opts.w end; if opts.h then ch._h=opts.h end end
        self._children[ch._name] = ch; return ch
    end
    function p:text(opts)
        _create_count = _create_count + 1; local t = _make_panel(opts and opts.name)
        t._text = opts and opts.text or ""; t._font = opts and opts.font; t._alpha = 1; t._visible = true
        t._x = opts and opts.x or 0; t._y = opts and opts.y or 0
        if opts and opts.w then t._w = opts.w end; if opts and opts.h then t._h = opts.h end
        t._font_size = opts and opts.font_size or 24
        function t:x() return self._x end
        function t:y() return self._y end
        function t:set_text(str) _set_text_count=_set_text_count+1; self._text=str end
        function t:text() return self._text end
        function t:font_size() return self._font_size end
        function t:set_font_size(s) self._font_size = s end
        function t:set_visible(v) self._visible=v end; function t:visible() return self._visible end
        function t:set_alpha(a) self._alpha=a end; function t:alpha() return self._alpha end
        self._children[t._name] = t
        return t
    end
    return p
end
function _make_parent() local p=_make_panel("safe_hud_parent"); p._w=1920; p._h=1080; return p end
function _make_mgr(parent)
    local safe = {panel = parent}
    _G.managers.hud = setmetatable({script=function(self,name) return safe end, disabled=function() return false end}, {__index=HUDManager})
    return safe
end
function _count_children(p) if not p then return 0 end; local n=0; for _ in pairs(p._children) do n=n+1 end; return n end
function _kill_panel_tree(p) if not p then return end; p._alive=false; for _,ch in pairs(p._children or {}) do _kill_panel_tree(ch) end end
function _reset_counters() _create_count=0; _set_text_count=0 end
function _get_create_count() return _create_count end
function _get_set_text_count() return _set_text_count end
'''
_KY_OPTS_STUBS = '''
SavePath = "/tmp/kyohud_test/"
MenuCallbackHandler = MenuCallbackHandler or {}; MenuHelper = {}
function MenuHelper:AddToggle(opts) end; function MenuHelper:AddSlider(opts) end
function MenuHelper:AddMultipleChoice(opts) end; function MenuHelper:AddButton(opts) end
function MenuHelper:AddDivider(opts) end; function MenuHelper:NewMenu(id) end
function MenuHelper:BuildMenu(id, opts) return {} end
function MenuHelper:AddMenuItem(parent, child, title, desc) end
BLT = nil
_ky_mem_files = {}
io = io or {}
function io.open(path, mode)
    mode = mode or "r"
    local data = _ky_mem_files[path]
    if mode == "r" then
        if not data then return nil end
        local pos = 1
        local f = {}
        function f:read(what)
            if what == "*all" then local r = data; data = nil; return r end
            return nil
        end
        function f:write(s) return false end
        function f:close() return true end
        return f
    elseif mode == "w" then
        local buf = ""
        local f = {}
        function f:write(s) buf = buf .. s; return true end
        function f:read(what) return nil end
        function f:close() _ky_mem_files[path] = buf; return true end
        return f
    end
    return nil
end
function os.remove(path) _ky_mem_files[path] = nil; return true end
function os.rename(a, b)
    local d = _ky_mem_files[a]
    if d == nil then return false end
    _ky_mem_files[b] = d; _ky_mem_files[a] = nil; return true
end
json = json or {}
function json.encode(t)
    local parts = {"{"}
    local first = true
    for k, v in pairs(t) do
        if not first then parts[#parts+1] = "," end
        first = false
        if type(k) == "string" then parts[#parts+1] = '"'..k..'"'
        else parts[#parts+1] = '"'..tostring(k)..'"' end
        parts[#parts+1] = ":"
        if type(v) == "boolean" then parts[#parts+1] = v and "true" or "false"
        elseif type(v) == "number" then parts[#parts+1] = tostring(v)
        elseif type(v) == "string" then parts[#parts+1] = '"'..v..'"'
        else parts[#parts+1] = "null" end
    end
    parts[#parts+1] = "}"
    return table.concat(parts)
end
function json.decode(s)
    if type(s) ~= "string" then return false end
    local data = {}
    for k, v in s:gmatch('"([^"]+)"%s*:%s*(%S+)') do
        v = v:gsub("[,}]$", "")
        if v == "true" then data[k] = true
        elseif v == "false" then data[k] = false
        elseif tonumber(v) then data[k] = tonumber(v)
        else data[k] = v:gsub('^"(.*)"$', "%1") end
    end
    return data
end
'''
_MOUNT_BOILER = '''
    kyohud.settings.enable_hud_foundation = true
    kyohud.settings.enable_mission = true
    local fp = _make_parent()
    local safe = _make_mgr(fp)
    local mgr = _G.managers.hud
    kyohud.hud.runtime:mount(mgr)
    kyohud.hud.mission:mount(mgr)
'''


def _lua_acc(with_mission=True, ctx=None, gpc=False, ky_opts=False):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(_STUBS); lua.execute(_DIESEL); lua.execute(_ENH_TIMER); lua.execute(_ENH_HM)
    if gpc: lua.execute(_GPC)
    if ctx: lua.execute(f'RequiredScript = "{ctx}"')
    lua.execute("_init_fp = _make_parent(); _make_mgr(_init_fp)")
    lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
    for p in [LAYOUT_PATH, NATIVE_VIS_PATH, RUNTIME_PATH]:
        s = _read(p)
        if s: lua.execute(s)
    if with_mission:
        msrc = _read(MISSION_PATH)
        if msrc:
            lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"'); lua.execute(msrc)
            lua.execute('RequiredScript = "lib/managers/lootmanager"'); lua.execute(msrc)
            lua.execute('RequiredScript = "lib/managers/gameplaycentralmanager"'); lua.execute(msrc)
    if ky_opts:
        lua.execute(_KY_OPTS_STUBS)
        s = _read(ROOT / "lua" / "ky_options.lua")
        if s: lua.execute(s)
    return lua, _read(MISSION_PATH) is not None


class NativeAlphaAcquisitionTests(unittest.TestCase):
    """(1) native timer leaf alpha acquired AFTER successful render; restore 0.37."""
    def test_alpha_acquired_only_after_rendered_text(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation = false
            kyohud.settings.enable_mission = false
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud
            mgr:_create_heist_timer({})
            mgr:feed_heist_time(300)
            _alpha_before = mgr._hud_heist_timer._timer_text:alpha()
        ''')
        self.assertAlmostEqual(float(lua.globals()._alpha_before), 0.37, places=2,
            msg="RED: native alpha must remain 0.37 before mission mount")
        lua.execute('''
            local mgr = _G.managers.hud
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)
            _owned_text = kyohud.hud.mission._timer_prim and kyohud.hud.mission._timer_prim:text() or nil
            _owned_visible = kyohud.hud.mission._timer_prim and kyohud.hud.mission._timer_prim:visible() or false
            _alpha_after = mgr._hud_heist_timer._timer_text:alpha()
        ''')
        g = lua.globals()
        self.assertEqual(g._owned_text, "05:00",
            msg="RED: owned timer must display captured '05:00'")
        self.assertTrue(bool(g._owned_visible),
            msg="RED: owned timer must be visible after mount")
        self.assertAlmostEqual(float(g._alpha_after), 0.0, places=2,
            msg="RED: native leaf alpha must be acquired to 0 after successful render")
    def test_native_alpha_restored_on_disable(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute(_MOUNT_BOILER + '''
            mgr:_create_heist_timer({}); mgr:feed_heist_time(300)
            local leaf = mgr._hud_heist_timer._timer_text
            _alpha_initial = leaf:alpha()
            kyohud.settings.enable_mission = false
            kyohud.hud.mission:refresh_settings(mgr)
            _alpha_after_disable = leaf:alpha()
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._alpha_initial), 0.0, places=2,
            msg="RED: acquired alpha must be 0 after render")
        self.assertAlmostEqual(float(g._alpha_after_disable), 0.37, places=2,
            msg="RED: native alpha 0.37 must be restored on disable")
    def test_no_broad_masking_native_parents(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute(_MOUNT_BOILER + '''
            mgr:_create_heist_timer({}); mgr:feed_heist_time(300)
            _parent_alpha = fp:alpha(); _parent_visible = fp:visible()
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._parent_alpha), 1.0, places=2,
            msg="RED: native parent alpha must NOT be masked")
        self.assertTrue(bool(g._parent_visible),
            "RED: native parent visible must NOT be masked")


class RenderingFailureRecoveryTests(unittest.TestCase):
    """(2) rendering failure/throwing setter/missing font => native restored."""
    def test_throwing_setter_no_duplicate_primitives(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute(_MOUNT_BOILER + '''
            mgr:_create_heist_timer({}); mgr:feed_heist_time(300)
            managers.job = {current_level_id = function() return "test" end}
            tweak_data.levels = {test = {name_id = "heist_test"}}
            managers.localization = {text = function() return "Test Heist" end}
            tweak_data.carry = {small_loot = {}, gold = {is_vehicle = false}}
            managers.loot = {_global = {secured = {{carry_id = "gold"}}}}
            function managers.loot:get_secured_bags_amount(is_vehicle) return 1 end
            kyohud.hud.mission:_update_title_display()
            kyohud.hud.mission:_ensure_primitives()
            local prim = kyohud.hud.mission._timer_prim
            local leaf = mgr._hud_heist_timer._timer_text
            _alpha_before_failure = leaf:alpha()
            _prim_count_before = _get_create_count()
            local orig_set_text = prim.set_text
            prim.set_text = function(s, str) error("owned setter broken") end
            mgr:feed_heist_time(400)
            _prim_count_after_throw = _get_create_count()
            _alpha_after_failure = leaf:alpha()
            prim.set_text = orig_set_text
            mgr:feed_heist_time(400)
            _alpha_after_retry_400 = leaf:alpha()
            _prim_text_after_retry_400 = prim:text()
            _prim_visible_after_retry_400 = prim:visible()
            _prim_count_after_retry_400 = _get_create_count()
            mgr:feed_heist_time(500)
            _prim_count_after_recover = _get_create_count()
            _alpha_after_recover = leaf:alpha()
            _prim_visible_after_recover = prim:visible()
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._alpha_before_failure), 0.0, places=2,
            msg="RED: native alpha must be 0 before owned setter failure")
        self.assertAlmostEqual(float(g._alpha_after_failure), 0.37, places=2,
            msg="RED: native alpha must be restored to .37 after owned setter failure")
        self.assertEqual(int(g._prim_count_before), int(g._prim_count_after_throw),
            "RED: throwing owned setter must not create duplicate primitives")
        self.assertAlmostEqual(float(g._alpha_after_retry_400), 0.0, places=2,
            msg="RED: native alpha must be 0 after retry of same failed text 400")
        self.assertEqual(g._prim_text_after_retry_400, "06:40",
            "RED: owned prim must show 06:40 after retry of same failed text 400")
        self.assertTrue(bool(g._prim_visible_after_retry_400),
            "RED: prim must be visible after retry of same failed text 400")
        self.assertEqual(int(g._prim_count_after_retry_400), int(g._prim_count_after_recover),
            "RED: retry and recovery must not create duplicate primitives")
        self.assertAlmostEqual(float(g._alpha_after_recover), 0.0, places=2,
            msg="RED: native alpha must be 0 after recovery")
        self.assertTrue(bool(g._prim_visible_after_recover),
            "RED: prim must be visible after recovery when native reacquired 0")
    def test_missing_font_no_native_mutation(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute('''
            tweak_data.hud.medium_font_noshadow = nil
        ''' + _MOUNT_BOILER + '''
            mgr:_create_heist_timer({}); mgr:feed_heist_time(300)
            _native_alpha = mgr._hud_heist_timer._timer_text:alpha()
            _native_text = mgr._hud_heist_timer._timer_text:text()
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._native_alpha), 0.37, places=2)
        self.assertEqual(g._native_text, "05:00")


class VRNoTimerTests(unittest.TestCase):
    """(3) VR/native no_timer no hiding."""
    def test_vr_no_hiding(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute('''_G.IS_VR = true''' + _MOUNT_BOILER + '''
            mgr:_create_heist_timer({}); mgr:feed_heist_time(300)
            _leaf_vis = mgr._hud_heist_timer._timer_text:visible()
            _leaf_alpha = mgr._hud_heist_timer._timer_text:alpha()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._leaf_vis), "RED: VR must not hide native leaf")
        self.assertAlmostEqual(float(g._leaf_alpha), 0.37, places=2)
    def test_no_timer_no_hiding(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute('''
            tweak_data.levels.test.hud = {no_timer = true}
        ''' + _MOUNT_BOILER + '''
            mgr:_create_heist_timer()
            mgr:feed_heist_time(300)
            _leaf_vis = mgr._hud_heist_timer._timer_text:visible()
        ''')
        self.assertTrue(bool(lua.globals()._leaf_vis),
            "RED: no_timer must not hide native leaf")


class TimerLeafReplacementTests(unittest.TestCase):
    """(4) timer leaf replacement: old restored, new acquired."""
    def test_old_timer_restored_new_acquired(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute(_MOUNT_BOILER + '''
            mgr:_create_heist_timer({}); local old_leaf = mgr._hud_heist_timer._timer_text
            mgr:feed_heist_time(300)
            _old_alpha_initial = old_leaf:alpha()
            mgr:_create_heist_timer({}); local new_leaf = mgr._hud_heist_timer._timer_text
            mgr:feed_heist_time(600)
            _old_alpha_restored = old_leaf:alpha()
            _new_alpha_initial = new_leaf:alpha()
            _same_leaf = rawequal(old_leaf, new_leaf)
        ''')
        g = lua.globals()
        self.assertFalse(bool(g._same_leaf), "RED: new timer leaf must be different")
        self.assertAlmostEqual(float(g._old_alpha_initial), 0.0, places=2,
            msg="RED: old leaf initial alpha must be 0 after render")
        self.assertAlmostEqual(float(g._new_alpha_initial), 0.0, places=2,
            msg="RED: new leaf initial alpha must be 0 after render")
        self.assertAlmostEqual(float(g._old_alpha_restored), 0.37, places=2,
            msg="RED: old leaf alpha must be restored to .37 on replacement")


class ThirdPartyAlphaPreservationTests(unittest.TestCase):
    """(5) thirdparty different alpha preserved on release."""
    def test_thirdparty_alpha_preserved(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute(_MOUNT_BOILER + '''
            mgr:_create_heist_timer({}); mgr:feed_heist_time(300)
            local leaf = mgr._hud_heist_timer._timer_text
            _alpha_acquired = leaf:alpha()
            leaf:set_alpha(0.88); _alpha_thirdparty = leaf:alpha()
            kyohud.settings.enable_mission = false
            kyohud.hud.mission:refresh_settings(mgr)
            _alpha_after = leaf:alpha()
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._alpha_acquired), 0.0, places=2,
            msg="RED: acquired alpha must be 0 before thirdparty change")
        self.assertAlmostEqual(float(g._alpha_thirdparty), 0.88, places=2)
        self.assertAlmostEqual(float(g._alpha_after), 0.88, places=2,
            msg="RED: thirdparty alpha 0.88 must be preserved")


class RootLossRebuildTests(unittest.TestCase):
    """(6) root-loss/rebuild restores/reacquires without reset combat."""
    def test_root_loss_reacquires_preserves_combat(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute('''
            kyohud._heist_score_total = 999
        ''' + _MOUNT_BOILER + '''
            mgr:_create_heist_timer({}); mgr:feed_heist_time(300)
            _timer_before = kyohud.hud.mission._timer_text
            local old_rt = kyohud.hud.runtime._root_panel
            fp:remove(old_rt); _kill_panel_tree(old_rt)
            _advance_time(1.0)
            kyohud.hud.runtime:update(mgr, _get_time(), 1.0)
            kyohud.hud.mission:update(mgr, _get_time(), 1.0)
            _root_after = kyohud.hud.mission._root_panel
            _timer_after = kyohud.hud.mission._timer_text
            _score = kyohud._heist_score_total
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._root_after, "RED: mission must reacquire root")
        self.assertEqual(g._timer_after, "05:00", "RED: timer text preserved")
        self.assertEqual(g._score, 999, "RED: combat score NOT reset")


class LayoutNonOverlapTests(unittest.TestCase):
    """(7) layout non-overlapping, outside native objectives rect, scale A-B-A."""
    def test_primitives_exist_when_data_available(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute(_MOUNT_BOILER + '''
            mgr:_create_heist_timer({}); mgr:feed_heist_time(300)
            managers.job = {current_level_id = function() return "test" end}
            tweak_data.levels = {test = {name_id = "heist_test"}}
            managers.localization = {text = function() return "Test Heist" end}
            tweak_data.carry = {small_loot = {}, gold = {is_vehicle = false}}
            managers.loot = {_global = {secured = {{carry_id = "gold"}}}}
            function managers.loot:get_secured_bags_amount(is_vehicle) return 1 end
            kyohud.hud.mission:_update_title_display()
            kyohud.hud.mission:_ensure_primitives()
            local tp = kyohud.hud.mission._timer_prim
            local tip = kyohud.hud.mission._title_prim
            local bp = kyohud.hud.mission._bags_prim
            _all_exist = (tp and tip and bp) ~= nil
            _timer_fs = tp and tp:font_size() or 0
            _title_fs = tip and tip:font_size() or 0
            _bags_fs = bp and bp:font_size() or 0
            _timer_w = tp and tp._w or 0
            _timer_h = tp and tp._h or 0
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._all_exist),
            "RED: all three primitives must exist when data available")
        self.assertGreater(int(g._timer_fs), 0, "RED: timer font size must be positive")
        self.assertGreater(int(g._title_fs), 0, "RED: title font size must be positive")
        self.assertGreater(int(g._bags_fs), 0, "RED: bags font size must be positive")
        self.assertGreater(int(g._timer_w), 0, "RED: timer width must be positive")
        self.assertGreater(int(g._timer_h), 0, "RED: timer height must be positive")
    def test_mission_outside_native_objectives_rect(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute(_MOUNT_BOILER + '''
            mgr:_create_heist_timer({}); mgr:feed_heist_time(300)
            managers.job = {current_level_id = function() return "test" end}
            tweak_data.levels = {test = {name_id = "heist_test"}}
            managers.localization = {text = function() return "Test Heist" end}
            tweak_data.carry = {small_loot = {}, gold = {is_vehicle = false}}
            managers.loot = {_global = {secured = {{carry_id = "gold"}}}}
            function managers.loot:get_secured_bags_amount(is_vehicle) return 1 end
            kyohud.hud.mission:_update_title_display()
            kyohud.hud.mission:_ensure_primitives()
            local r = kyohud.hud.mission._root_panel
            _rx = r and r._x or -1; _ry = r and r._y or -1
            _rw = r and r._w or 0; _rh = r and r._h or 0
            _nx, _ny, _nw, _nh = 0, 0, 500, 100
            _overlap = not (_rx >= _nx+_nw or _rx+_rw <= _nx or _ry >= _ny+_nh or _ry+_rh <= _ny)
            _pos_dim = (_rw > 0) and (_rh > 0)
            local tp = kyohud.hud.mission._timer_prim
            local tip = kyohud.hud.mission._title_prim
            local bp = kyohud.hud.mission._bags_prim
            local function rects_overlap(ax,ay,aw,ah, bx,by,bw,bh)
                return not (ax+aw <= bx or bx+bw <= ax or ay+ah <= by or by+bh <= ay)
            end
            _tx = tp and tp:x() or 0; _ty = tp and tp:y() or 0; _tw = tp and tp._w or 0; _th = tp and tp._h or 0
            _tix = tip and tip:x() or 0; _tiy = tip and tip:y() or 0; _tiw = tip and tip._w or 0; _tih = tip and tip._h or 0
            _bx = bp and bp:x() or 0; _by = bp and bp:y() or 0; _bw = bp and bp._w or 0; _bh = bp and bp._h or 0
            _overlap_timer_title = rects_overlap(_tx,_ty,_tw,_th, _tix,_tiy,_tiw,_tih)
            _overlap_timer_bags = rects_overlap(_tx,_ty,_tw,_th, _bx,_by,_bw,_bh)
            _overlap_title_bags = rects_overlap(_tix,_tiy,_tiw,_tih, _bx,_by,_bw,_bh)
        ''')
        g = lua.globals()
        self.assertFalse(bool(g._overlap),
            "RED: mission root must NOT intersect native objectives rect (0,0,500,100)")
        self.assertTrue(bool(g._pos_dim),
            "RED: mission root must have positive dimensions")
        self.assertFalse(bool(g._overlap_timer_title),
            "RED: timer and title primitives must NOT overlap")
        self.assertFalse(bool(g._overlap_timer_bags),
            "RED: timer and bags primitives must NOT overlap")
        self.assertFalse(bool(g._overlap_title_bags),
            "RED: title and bags primitives must NOT overlap")
    def test_scale_resize_ABA_no_drift(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute(_MOUNT_BOILER + '''
            mgr:_create_heist_timer({}); mgr:feed_heist_time(300)
            managers.job = {current_level_id = function() return "test" end}
            tweak_data.levels = {test = {name_id = "heist_test"}}
            managers.localization = {text = function() return "Test Heist" end}
            tweak_data.carry = {small_loot = {}, gold = {is_vehicle = false}}
            managers.loot = {_global = {secured = {{carry_id = "gold"}}}}
            function managers.loot:get_secured_bags_amount(is_vehicle) return 1 end
            kyohud.hud.mission:_update_title_display()
            kyohud.hud.mission:_ensure_primitives()
            _x_a = kyohud.hud.mission._root_panel._x
            _y_a = kyohud.hud.mission._root_panel._y
            _w_a = kyohud.hud.mission._root_panel._w
            _h_a = kyohud.hud.mission._root_panel._h
            _id_a = tostring(kyohud.hud.mission._root_panel)
            kyohud.settings.hud_scale = 1.5
            kyohud.hud.runtime:refresh_settings(mgr); kyohud.hud.mission:refresh_settings(mgr)
            _x_b = kyohud.hud.mission._root_panel._x
            _y_b = kyohud.hud.mission._root_panel._y
            _w_b = kyohud.hud.mission._root_panel._w
            _h_b = kyohud.hud.mission._root_panel._h
            _b_differs = not ((_x_b == _x_a) and (_y_b == _y_a) and (_w_b == _w_a) and (_h_b == _h_a))
            kyohud.settings.hud_scale = 1.0
            kyohud.hud.runtime:refresh_settings(mgr); kyohud.hud.mission:refresh_settings(mgr)
            _x_c = kyohud.hud.mission._root_panel._x
            _y_c = kyohud.hud.mission._root_panel._y
            _w_c = kyohud.hud.mission._root_panel._w
            _h_c = kyohud.hud.mission._root_panel._h
            _id_c = tostring(kyohud.hud.mission._root_panel)
            _same_geom = (_x_a == _x_c) and (_y_a == _y_c) and (_w_a == _w_c) and (_h_a == _h_c)
            _same_id = (_id_a == _id_c)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._b_differs),
            "RED: scale B geometry must differ from A (non-vacuous)")
        self.assertTrue(bool(g._same_id),
            "RED: scale A-B-A must preserve root panel identity")
        self.assertTrue(bool(g._same_geom),
            "RED: scale A-B-A must preserve exact geometry (x,y,w,h)")


class StablePrimitiveCountTests(unittest.TestCase):
    """(8) stable total primitive creation/set_text counts."""
    def test_stable_creation_count_identical_feeds(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute(_MOUNT_BOILER + '''
            mgr:_create_heist_timer({}); _reset_counters()
            mgr:feed_heist_time(300)
            _set_text_after_first = _get_set_text_count()
            _creates_after_first = _get_create_count()
            mgr:feed_heist_time(300); mgr:feed_heist_time(300)
            _creates1 = _get_create_count()
            _set_text1 = _get_set_text_count()
            mgr:feed_heist_time(300); mgr:feed_heist_time(300)
            _creates2 = _get_create_count()
            _set_text2 = _get_set_text_count()
        ''')
        g = lua.globals()
        self.assertEqual(g._creates1, g._creates2,
            "RED: identical feeds must NOT create duplicate primitives")
        self.assertEqual(int(g._set_text1), int(g._set_text2),
            "RED: identical feeds must NOT change set_text count")


class BagsEdgeCaseTests(unittest.TestCase):
    """(9) missing bags renders --, finite validation, no repeated scans."""
    def test_missing_bags_renders_dashdash(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent(); local safe = _make_mgr(fp); local mgr = _G.managers.hud
            managers.loot = nil
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)
            _bags_text = kyohud.hud.mission._bags_prim and kyohud.hud.mission._bags_prim:text() or nil
        ''')
        self.assertEqual(lua.globals()._bags_text, "--",
            "RED: missing loot manager must render '--'")
    def test_finite_validation_rejects_invalid(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute(_MOUNT_BOILER + '''
            managers.loot = {}
            function managers.loot:get_secured_bags_amount() return math.huge end
            _r1 = kyohud.hud.mission:_resolve_bags()
            function managers.loot:get_secured_bags_amount() return 0/0 end
            _r2 = kyohud.hud.mission:_resolve_bags()
            function managers.loot:get_secured_bags_amount() return -5 end
            _r3 = kyohud.hud.mission:_resolve_bags()
            function managers.loot:get_secured_bags_amount() return 2.7 end
            _r4 = kyohud.hud.mission:_resolve_bags()
        ''')
        g = lua.globals()
        self.assertIsNone(g._r1, "RED: inf rejected"); self.assertIsNone(g._r2, "RED: nan rejected")
        self.assertIsNone(g._r3, "RED: negative rejected"); self.assertIsNone(g._r4, "RED: fraction rejected")
    def test_no_repeated_loot_scans_after_snapshot(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent(); local safe = _make_mgr(fp); local mgr = _G.managers.hud
            tweak_data.carry = {small_loot = {}, gold = {is_vehicle = false}}
            managers.loot = {_global = {secured = {{carry_id = "gold"}}}}
            _scan_count = 0
            function managers.loot:get_secured_bags_amount(is_vehicle) _scan_count=_scan_count+1; return 1 end
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)
            _scans_mount = _scan_count
            _advance_time(2.0)
            kyohud.hud.mission:update(mgr, _get_time(), 2.0)
            kyohud.hud.mission:update(mgr, _get_time(), 2.0)
            _scans_after = _scan_count
        ''')
        g = lua.globals()
        self.assertGreater(int(g._scans_mount), 0)
        self.assertEqual(int(g._scans_mount), int(g._scans_after),
            "RED: no repeated loot scans after successful snapshot")


class GPCTimerSnapshotTests(unittest.TestCase):
    """(10) GPC:load → mission integration with real timer display.

    Tests use gpc=True, call actual gpc:load before mounting, then create
    native timer, mount runtime and mission, and assert owned text.
    """
    def test_gpc_load_mount_timer_display(self):
        lua, ok = _lua_acc(gpc=True); self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud
            local gpc = managers.game_play_central
            Application:_set_time(0)
            gpc:load({GamePlayCentralManager = {heist_timer = 3661, heist_timer_running = false}})
            Application:_set_time(100)
            mgr:_create_heist_timer({})

            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)
            _timer_text = kyohud.hud.mission._timer_prim and kyohud.hud.mission._timer_prim:text() or nil
            _native_text = mgr._hud_heist_timer._timer_text:text()
            _native_last = mgr._hud_heist_timer._last_time
        ''')
        g = lua.globals()
        self.assertEqual(g._timer_text, "01:01:01",
            "RED: GPC load 3661 → mission timer must display '01:01:01' (raw loaded scalar)")
        self.assertEqual(g._native_text, "00:00",
            "RED: native text must stay '00:00' (no feed from stopped timer)")
        self.assertAlmostEqual(float(g._native_last), 0.0, places=1,
            msg="RED: native _last_time must stay 0")
    def test_gpc_stopped_frozen_after_advance(self):
        lua, ok = _lua_acc(gpc=True); self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud
            local gpc = managers.game_play_central
            Application:_set_time(0)
            gpc:load({GamePlayCentralManager = {heist_timer = 3661, heist_timer_running = false}})
            mgr:_create_heist_timer({})

            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)
            _text_before = kyohud.hud.mission._timer_prim:text()
            Application:_set_time(100)
            kyohud.hud.mission:update(mgr, Application:time(), 100)
            _text_after = kyohud.hud.mission._timer_prim:text()
        ''')
        g = lua.globals()
        self.assertEqual(g._text_before, "01:01:01")
        self.assertEqual(g._text_after, "01:01:01",
            "RED: stopped timer must remain frozen after time advance")
    def test_gpc_sync_id1_updates_id2_preserves(self):
        lua, ok = _lua_acc(gpc=True); self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud
            local gpc = managers.game_play_central
            Application:_set_time(0)
            mgr:_create_heist_timer({})
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)
            gpc:sync_heist_time(500, 1)

            _text_id1 = kyohud.hud.mission._timer_prim:text()
            gpc:sync_heist_time(9999, 2)

            _text_id2 = kyohud.hud.mission._timer_prim:text()
        ''')
        g = lua.globals()
        self.assertEqual(g._text_id1, "08:20",
            "RED: sync id=1 with 500 must display '08:20'")
        self.assertEqual(g._text_id2, "08:20",
            "RED: sync id=2 PNR must NOT change timer display")
    def test_native_feed_precedence_over_sync(self):
        """Native feed establishes owned time; sync updates owned but native unchanged;
        native reset+feed(0) clears owned to 00:00 (pending scalar cleared on real feed)."""
        lua, ok = _lua_acc(gpc=True); self.assertTrue(ok)
        lua.execute(_MOUNT_BOILER + '''
            mgr:_create_heist_timer({})
            mgr:feed_heist_time(300)
            _owned_after_native = kyohud.hud.mission._timer_prim:text()
            _native_after_native = mgr._hud_heist_timer._timer_text:text()
            _native_last_after_native = mgr._hud_heist_timer._last_time
            local gpc = managers.game_play_central
            gpc:sync_heist_time(500, 1)
            _owned_after_sync = kyohud.hud.mission._timer_prim:text()
            _native_after_sync = mgr._hud_heist_timer._timer_text:text()
            _native_last_after_sync = mgr._hud_heist_timer._last_time
            mgr._hud_heist_timer:reset()
            mgr:feed_heist_time(0)
            _owned_after_reset_feed = kyohud.hud.mission._timer_prim:text()
        ''')
        g = lua.globals()
        self.assertEqual(g._owned_after_native, "05:00",
            "RED: native feed 300 must establish owned 05:00")
        self.assertEqual(g._native_after_native, "05:00",
            "RED: native text must be 05:00 after feed")
        self.assertAlmostEqual(float(g._native_last_after_native), 300.0, places=1,
            msg="RED: native _last_time must be 300 after feed")
        self.assertEqual(g._owned_after_sync, "08:20",
            "RED: sync 500 must update owned to 08:20")
        self.assertEqual(g._native_after_sync, "05:00",
            "RED: native text must STILL be 05:00 after sync (no native feed)")
        self.assertAlmostEqual(float(g._native_last_after_sync), 300.0, places=1,
            msg="RED: native _last_time must STILL be 300 after sync")
        self.assertEqual(g._owned_after_reset_feed, "00:00",
            "RED: native reset+feed(0) must clear owned to 00:00 (pending scalar cleared)")

    def test_owned_timer_shape_override_noop_then_restore(self):
        """Scale 1.5 + refresh: native restored .37, owned invisible (shape override no-op).
        Restore setter + refresh same scale: native 0, owned visible, shape matches desired, identity unchanged."""
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute(_MOUNT_BOILER + '''
            mgr:_create_heist_timer({})
            mgr:feed_heist_time(300)
            local tp = kyohud.hud.mission._timer_prim
            local leaf = mgr._hud_heist_timer._timer_text
            local orig_set_shape = tp.set_shape
            tp.set_shape = function() end
            kyohud.settings.hud_scale = 1.5
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.mission:refresh_settings(mgr)
            _native_alpha_override = leaf:alpha()
            _owned_vis_override = tp:visible()
            _id_before = tostring(kyohud.hud.mission._root_panel)
            tp.set_shape = orig_set_shape
            kyohud.settings.hud_scale = 1.5
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.mission:refresh_settings(mgr)
            _native_alpha_restore = leaf:alpha()
            _owned_vis_restore = tp:visible()
            _owned_text_restore = tp:text()
            _id_after = tostring(kyohud.hud.mission._root_panel)
            local lc = kyohud.hud.mission._layout_cache
            _desired_x = lc and lc.timer and lc.timer.x or -1
            _desired_y = lc and lc.timer and lc.timer.y or -1
            _desired_w = lc and lc.timer and lc.timer.w or -1
            _desired_h = lc and lc.timer and lc.timer.h or -1
            _actual_x = tp:x()
            _actual_y = tp:y()
            _actual_w = tp._w
            _actual_h = tp._h
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._native_alpha_override), 0.37, places=2,
            msg="RED: native must be restored .37 when owned set_shape is no-op")
        self.assertFalse(bool(g._owned_vis_override),
            msg="RED: owned must be invisible when set_shape is no-op")
        self.assertAlmostEqual(float(g._native_alpha_restore), 0.0, places=2,
            msg="RED: native must be 0 after setter restored and refresh")
        self.assertTrue(bool(g._owned_vis_restore),
            msg="RED: owned must be visible after setter restored")
        self.assertEqual(g._owned_text_restore, "05:00",
            msg="RED: owned text must match desired after restore")
        self.assertEqual(g._id_before, g._id_after,
            msg="RED: root panel identity must be unchanged (no production-state repair)")
        self.assertAlmostEqual(float(g._actual_x), float(g._desired_x), places=1,
            msg="RED: actual timer x must match layout_cache.timer.x after restore")
        self.assertAlmostEqual(float(g._actual_y), float(g._desired_y), places=1,
            msg="RED: actual timer y must match layout_cache.timer.y after restore")
        self.assertAlmostEqual(float(g._actual_w), float(g._desired_w), places=1,
            msg="RED: actual timer w must match layout_cache.timer.w after restore")
        self.assertAlmostEqual(float(g._actual_h), float(g._desired_h), places=1,
            msg="RED: actual timer h must match layout_cache.timer.h after restore")

    def test_gpc_load_new_manager_no_inheritance(self):
        """GPC load stopped@3661 → mount first manager/native → owned 01:01:01.
        Replace managers.game_play_central and managers.hud with new instances.
        New native timer + mount: new owned must NOT inherit 01:01:01,
        native stays 00:00/_last_time=0."""
        lua, ok = _lua_acc(gpc=True); self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp1 = _make_parent()
            local safe1 = _make_mgr(fp1)
            local mgr1 = _G.managers.hud
            local gpc1 = managers.game_play_central
            Application:_set_time(0)
            gpc1:load({GamePlayCentralManager = {heist_timer = 3661, heist_timer_running = false}})
            Application:_set_time(100)
            mgr1:_create_heist_timer({})
            kyohud.hud.runtime:mount(mgr1)
            kyohud.hud.mission:mount(mgr1)
            _owned_first = kyohud.hud.mission._timer_prim:text()
            local newGPC = GamePlayCentralManager:new()
            managers.game_play_central = newGPC
            local fp2 = _make_parent()
            local safe2 = _make_mgr(fp2)
            local mgr2 = _G.managers.hud
            mgr2:_create_heist_timer({})
            mgr2:init_finalize()
            kyohud.hud.runtime:mount(mgr2)
            kyohud.hud.mission:mount(mgr2)
            _owned_second = kyohud.hud.mission._timer_prim:text()
            _native_second = mgr2._hud_heist_timer._timer_text:text()
            _native_last_second = mgr2._hud_heist_timer._last_time
        ''')
        g = lua.globals()
        self.assertEqual(g._owned_first, "01:01:01",
            "RED: first mount must capture GPC load 3661 as 01:01:01")
        self.assertEqual(g._owned_second, "00:00",
            "RED: new manager mount must NOT inherit 01:01:01 from previous GPC")
        self.assertEqual(g._native_second, "00:00",
            "RED: new native text must be 00:00")
        self.assertAlmostEqual(float(g._native_last_second), 0.0, places=1,
            msg="RED: new native _last_time must be 0")

    def test_early_context_gpc_load_no_feed_native_semantics(self):
        """Regression: mission loaded under gameplaycentralmanager BEFORE
        runtime/layout/NV must capture GPC scalar without feeding native timer.
        No feed_heist_time calls — native must stay pristine."""
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute(_STUBS)
        lua.execute(_DIESEL)
        lua.execute(_ENH_TIMER)
        lua.execute(_ENH_HM)
        lua.execute(_GPC)
        msrc = _read(MISSION_PATH)
        self.assertIsNotNone(msrc, "RED: mission.lua must exist")
        lua.execute('RequiredScript = "lib/managers/gameplaycentralmanager"')
        lua.execute(msrc)
        lua.execute('''
            Application:_set_time(0)
            local gpc = managers.game_play_central
            gpc:load({GamePlayCentralManager = {heist_timer = 3661, heist_timer_running = false}})
            Application:_set_time(100)
        ''')
        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        for p in [LAYOUT_PATH, NATIVE_VIS_PATH, RUNTIME_PATH]:
            s = _read(p)
            if s: lua.execute(s)
        lua.execute(msrc)
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud
            mgr:_create_heist_timer({})
            mgr:init_finalize()
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)
            _owned_text = kyohud.hud.mission._timer_prim and kyohud.hud.mission._timer_prim:text() or nil
            _native_text = mgr._hud_heist_timer._timer_text:text()
            _native_last = mgr._hud_heist_timer._last_time
        ''')
        g = lua.globals()
        self.assertEqual(g._owned_text, "01:01:01",
            "RED: early-context GPC load must capture owned '01:01:01'")
        self.assertEqual(g._native_text, "00:00",
            "RED: native text must stay '00:00' (no feed)")
        self.assertAlmostEqual(float(g._native_last), 0.0, places=1,
            msg="RED: native _last_time must stay 0")
        lua.execute('''
            local mgr = _G.managers.hud
            local gpc = managers.game_play_central
            gpc:sync_heist_time(500, 1)
            _owned_after_sync = kyohud.hud.mission._timer_prim and kyohud.hud.mission._timer_prim:text() or nil
            _native_after_sync = mgr._hud_heist_timer._timer_text:text()
            _native_last_after = mgr._hud_heist_timer._last_time
            gpc:sync_heist_time(9999, 2)
            _owned_after_id2 = kyohud.hud.mission._timer_prim and kyohud.hud.mission._timer_prim:text() or nil
        ''')
        g2 = lua.globals()
        self.assertEqual(g2._owned_after_sync, "08:20",
            "RED: sync id=1 with 500 must display '08:20'")
        self.assertEqual(g2._native_after_sync, "00:00",
            "RED: native STILL '00:00' after sync (no feed)")
        self.assertAlmostEqual(float(g2._native_last_after), 0.0, places=1,
            msg="RED: native _last_time STILL 0 after sync")
        self.assertEqual(g2._owned_after_id2, "08:20",
            "RED: sync id=2 PNR must NOT change owned display")


class OptionPersistenceTests(unittest.TestCase):
    """(11) option enable_mission false defaults; KH.Load with in-memory io/json."""
    def test_enable_mission_default_false(self):
        lua, ok = _lua_acc(ky_opts=True); self.assertTrue(ok)
        lua.execute('_default = kyohud._defaults.enable_mission')
        val = lua.globals()._default
        self.assertIsNotNone(val, "RED: enable_mission must exist in _defaults")
        self.assertFalse(bool(val), "RED: enable_mission default must be false")
    def test_load_old_save_missing_key_uses_default(self):
        lua, ok = _lua_acc(ky_opts=True); self.assertTrue(ok)
        lua.execute('''
            _ky_mem_files[kyohud._settings_path] = '{"enable_killfeed":true}'
            kyohud.settings.enable_mission = nil
            kyohud.Load()
            _val = kyohud.settings.enable_mission
        ''')
        val = lua.globals()._val
        self.assertIsNotNone(val, "RED: KH.Load must resolve missing key from defaults")
        self.assertFalse(bool(val), "RED: missing key in old save must default to false")
    def test_load_explicit_false_preserved(self):
        lua, ok = _lua_acc(ky_opts=True); self.assertTrue(ok)
        lua.execute('''
            _ky_mem_files[kyohud._settings_path] = '{"enable_mission":false}'
            kyohud.Load()
            _val = kyohud.settings.enable_mission
        ''')
        val = lua.globals()._val
        self.assertIsNotNone(val, "RED: explicit false must survive KH.Load")
        self.assertFalse(bool(val), "RED: explicit false must not become true")
    def test_callback_KY_ToggleMission_exists(self):
        lua, ok = _lua_acc(ky_opts=True); self.assertTrue(ok)
        lua.execute('_has_cb = (type(MenuCallbackHandler.KY_ToggleMission) == "function")')
        self.assertTrue(bool(lua.globals()._has_cb),
            "RED: KY_ToggleMission callback must exist")
    def test_callback_invokes_save(self):
        lua, ok = _lua_acc(ky_opts=True); self.assertTrue(ok)
        lua.execute('''
            _save_called = false
            local orig_save = kyohud.Save
            kyohud.Save = function() _save_called = true; return orig_save() end
            local item = {value = function() return "on" end}
            MenuCallbackHandler.KY_ToggleMission(MenuCallbackHandler, item)
            _val_on = kyohud.settings.enable_mission
            _save_on = _save_called
            _save_called = false
            local item_off = {value = function() return "off" end}
            MenuCallbackHandler.KY_ToggleMission(MenuCallbackHandler, item_off)
            _val_off = kyohud.settings.enable_mission
            _save_off = _save_called
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._save_on),
            "RED: KY_ToggleMission must invoke KH.Save on enable")
        self.assertTrue(bool(g._val_on),
            "RED: item:value()='on' must set enable_mission true")
        self.assertTrue(bool(g._save_off),
            "RED: KY_ToggleMission must invoke KH.Save on disable")
        self.assertFalse(bool(g._val_off),
            "RED: item:value()='off' must set enable_mission false")


class ManifestIntegrationTests(unittest.TestCase):
    """(12) manifest: exact mission hook entries in mod.txt, menu, localization."""
    def test_mod_txt_mission_hooks(self):
        mod_path = ROOT / "mod.txt"
        self.assertTrue(mod_path.is_file(), "RED: mod.txt must exist")
        data = pyjson.loads(mod_path.read_text(encoding="utf-8"))
        hooks = data.get("hooks", [])
        mission_hooks = [h for h in hooks if h.get("script_path") == "lua/hud/mission.lua"]
        hook_ids = {h.get("hook_id") for h in mission_hooks}
        self.assertIn("lib/managers/hudmanagerpd2", hook_ids,
            "RED: mod.txt must have mission.lua hook under hudmanagerpd2")
        self.assertIn("lib/managers/lootmanager", hook_ids,
            "RED: mod.txt must have mission.lua hook under lootmanager")
        self.assertIn("lib/managers/gameplaycentralmanager", hook_ids,
            "RED: mod.txt must have mission.lua hook under gameplaycentralmanager")
    def test_hooks_registered_under_correct_contexts(self):
        lua, ok = _lua_acc(with_mission=False); self.assertTrue(ok)
        msrc = _read(MISSION_PATH); self.assertIsNotNone(msrc)
        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"'); lua.execute(msrc)
        lua.execute('RequiredScript = "lib/managers/lootmanager"'); lua.execute(msrc)
        lua.execute('RequiredScript = "lib/managers/gameplaycentralmanager"'); lua.execute(msrc)
        lua.execute('''
            _hudmgr=0; _loot=0; _ids={}; _dupes=0
            for _, e in ipairs(Hooks._all) do
                if e.class==HUDManager then _hudmgr=_hudmgr+1 end
                if e.class==LootManager then _loot=_loot+1 end
                if _ids[e.id] then _dupes=_dupes+1 end; _ids[e.id]=true
            end
        ''')
        g = lua.globals()
        self.assertGreaterEqual(int(g._hudmgr), 2, "RED: HUDManager hooks for feed/modify")
        self.assertGreaterEqual(int(g._loot), 1, "RED: LootManager sync_load hook")
        self.assertEqual(int(g._dupes), 0, "RED: no duplicate hook IDs")
    def test_menu_toggle_entry_exists(self):
        mp = ROOT / "menu" / "menu.json"
        self.assertTrue(mp.is_file())
        data = pyjson.loads(mp.read_text(encoding="utf-8"))
        mission_items = [i for i in data.get("items", []) if i.get("value") == "enable_mission"]
        self.assertGreaterEqual(len(mission_items), 1,
            "RED: menu.json must have enable_mission toggle")
    def test_localization_en_fr_fallback_parity(self):
        en_path = ROOT / "loc" / "english.json"
        fr_path = ROOT / "loc" / "french.json"
        en = pyjson.loads(en_path.read_text(encoding="utf-8"))
        fr = pyjson.loads(fr_path.read_text(encoding="utf-8"))
        en_keys = set(en.keys()) if isinstance(en, dict) else set()
        fr_keys = set(fr.keys()) if isinstance(fr, dict) else set()
        mission_keys = {"ky_hud_mission_title", "ky_opt_enable_mission", "ky_opt_enable_mission_desc"}
        for k in mission_keys:
            self.assertIn(k, en_keys, f"RED: english.json must have {k}")
            self.assertIn(k, fr_keys, f"RED: french.json must have {k}")
            self.assertTrue(len(str(en.get(k, ""))) > 0, f"RED: english.json {k} must be non-empty")
            self.assertTrue(len(str(fr.get(k, ""))) > 0, f"RED: french.json {k} must be non-empty")
        fallback_src = (ROOT / "lua" / "ky_localization.lua").read_text(encoding="utf-8-sig")
        for k in mission_keys:
            self.assertIn(k, fallback_src, f"RED: ky_localization.lua fallback must contain {k}")
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute('''
            local src = kyohud.hud.mission
            _title_nil = (src:_resolve_title() == nil)
        ''')
        self.assertTrue(bool(lua.globals()._title_nil),
            "RED: without job, title resolver returns nil (fallback at display)")


class BoundedFourRegressionsTests(unittest.TestCase):
    """Bounded 4 regressions: geometry at nonstandard parent, alpha setter throw
    on restore, mutate-then-throw acquire, no_timer switch."""

    def test_absolute_rects_disjoint_native_nonstandard_parent_scale(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            kyohud.settings.hud_scale = 0.5
            local fp = _make_parent()
            fp._w = 1198; fp._h = 673
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)
            mgr:_create_heist_timer({})
            mgr:feed_heist_time(300)
            managers.job = {current_level_id = function() return "test" end}
            tweak_data.levels = {test = {name_id = "heist_test"}}
            managers.localization = {text = function() return "Test Heist" end}
            tweak_data.carry = {small_loot = {}, gold = {is_vehicle = false}}
            managers.loot = {_global = {secured = {{carry_id = "gold"}}}}
            function managers.loot:get_secured_bags_amount(is_vehicle) return 1 end
            kyohud.hud.mission:_update_title_display()
            kyohud.hud.mission:_ensure_primitives()
            local r = kyohud.hud.mission._root_panel
            local tp = kyohud.hud.mission._timer_prim
            local tip = kyohud.hud.mission._title_prim
            local bp = kyohud.hud.mission._bags_prim
            local rx = r:x(); local ry = r:y()
            local function rects_overlap(ax,ay,aw,ah, bx,by,bw,bh)
                return not (ax+aw <= bx or bx+bw <= ax or ay+ah <= by or by+bh <= ay)
            end
            local nx, ny, nw, nh = 0, 0, 500, 100
            local tx = rx + tp:x(); local ty = ry + tp:y(); local tw = tp._w; local th = tp._h
            local tix = rx + tip:x(); local tiy = ry + tip:y(); local tiw = tip._w; local tih = tip._h
            local bx = rx + bp:x(); local by = ry + bp:y(); local bw = bp._w; local bh = bp._h
            _overlap_timer_native = rects_overlap(tx,ty,tw,th, nx,ny,nw,nh)
            _overlap_title_native = rects_overlap(tix,tiy,tiw,tih, nx,ny,nw,nh)
            _overlap_bags_native = rects_overlap(bx,by,bw,bh, nx,ny,nw,nh)
            local pw = fp:w(); local ph = fp:h()
            _timer_finite = (tx >= 0) and (ty >= 0) and (tx+tw <= pw) and (ty+th <= ph)
            _title_finite = (tix >= 0) and (tiy >= 0) and (tix+tiw <= pw) and (tiy+tih <= ph)
            _bags_finite = (bx >= 0) and (by >= 0) and (bx+bw <= pw) and (by+bh <= ph)
            _bags_within_75 = (bx + bw) <= (pw * 0.75)
            _fs_a = tp:font_size()
            _id_a = tostring(r)
            kyohud.settings.hud_scale = 2.0
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.mission:refresh_settings(mgr)
            _fs_b = tp:font_size()
            kyohud.settings.hud_scale = 0.5
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.mission:refresh_settings(mgr)
            _fs_c = tp:font_size()
            _id_c = tostring(kyohud.hud.mission._root_panel)
            _b_differs = (_fs_b ~= _fs_a)
            _same_id = (_id_a == _id_c)
            _same_fs = (_fs_a == _fs_c)
        ''')
        g = lua.globals()
        self.assertFalse(bool(g._overlap_timer_native),
            "RED: timer absolute rect must be disjoint from native (0,0,500,100)")
        self.assertFalse(bool(g._overlap_title_native),
            "RED: title absolute rect must be disjoint from native (0,0,500,100)")
        self.assertFalse(bool(g._overlap_bags_native),
            "RED: bags absolute rect must be disjoint from native (0,0,500,100)")
        self.assertTrue(bool(g._timer_finite),
            "RED: timer must be positive finite within parent")
        self.assertTrue(bool(g._title_finite),
            "RED: title must be positive finite within parent")
        self.assertTrue(bool(g._bags_finite),
            "RED: bags must be positive finite within parent")
        self.assertTrue(bool(g._bags_within_75),
            "RED: bags must be within left 75% of parent, not far-right assault zone")
        self.assertTrue(bool(g._b_differs),
            "RED: font size must change at scale B")
        self.assertTrue(bool(g._same_id),
            "RED: root panel identity must be preserved after A-B-A resize")
        self.assertTrue(bool(g._same_fs),
            "RED: font size must be restored at scale A after A-B-A")

    def test_alpha_setter_throw_on_restore_retains_record_then_recovers(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute(_MOUNT_BOILER + '''
            mgr:_create_heist_timer({})
            mgr:feed_heist_time(300)
            local leaf = mgr._hud_heist_timer._timer_text
            _alpha_acquired = leaf:alpha()
            leaf._throw_alpha = true
            kyohud.settings.enable_mission = false
            kyohud.hud.mission:refresh_settings(mgr)
            _alpha_after_disable = leaf:alpha()
            local nv = kyohud.hud.native_visibility
            _entries_after_disable = #nv._entries
            leaf._throw_alpha = false
            _advance_time(1.0)
            kyohud.hud.runtime:update(mgr, _get_time(), 1.0)
            _alpha_after_update = leaf:alpha()
            _entries_after_update = #nv._entries
            _whitelist_count_after_update = 0
            for _ in pairs(nv._whitelist) do _whitelist_count_after_update = _whitelist_count_after_update + 1 end
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._alpha_acquired), 0.0, places=2,
            msg="RED: native alpha must be 0 after acquisition")
        self.assertAlmostEqual(float(g._alpha_after_disable), 0.0, places=2,
            msg="RED: native alpha must remain 0 when setter throws during restore")
        self.assertGreater(int(g._entries_after_disable), 0,
            "RED: service must retain record after failed restore")
        self.assertAlmostEqual(float(g._alpha_after_update), 0.37, places=2,
            msg="RED: runtime:update must restore .37 after setter fixed")
        self.assertEqual(int(g._entries_after_update), 0,
            "RED: entries must be empty after successful restore")
        self.assertEqual(int(g._whitelist_count_after_update), 0,
            "RED: whitelist must be empty after successful restore")

    def test_failed_acquire_mutates_then_throws_retains_uncertain_record(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute(_MOUNT_BOILER + '''
            mgr:_create_heist_timer({})
            local leaf = mgr._hud_heist_timer._timer_text
            local _first_alpha_call = true
            local _orig_set_alpha = leaf.set_alpha
            leaf.set_alpha = function(s, a)
                s._alpha = a
                if _first_alpha_call then
                    _first_alpha_call = false
                    error("set_alpha mutated then failed")
                end
            end
            mgr:feed_heist_time(300)
            local nv = kyohud.hud.native_visibility
            _entries_after_feed = #nv._entries
            leaf.set_alpha = _orig_set_alpha
            kyohud.settings.enable_mission = false
            kyohud.hud.mission:refresh_settings(mgr)
            _advance_time(1.0)
            kyohud.hud.runtime:update(mgr, _get_time(), 1.0)
            _alpha_after_update = leaf:alpha()
            _entries_after_update = #nv._entries
            _whitelist_count_after_update = 0
            for _ in pairs(nv._whitelist) do _whitelist_count_after_update = _whitelist_count_after_update + 1 end
        ''')
        g = lua.globals()
        self.assertGreater(int(g._entries_after_feed), 0,
            "RED: service must retain uncertain record after mutate-then-throw acquire")
        self.assertAlmostEqual(float(g._alpha_after_update), 0.37, places=2,
            msg="RED: runtime:update must restore .37 after mutate-throw")
        self.assertEqual(int(g._entries_after_update), 0,
            "RED: entries must be empty after successful restore")
        self.assertEqual(int(g._whitelist_count_after_update), 0,
            "RED: whitelist must be empty after successful restore")

    def test_no_timer_switch_restores_old_acquires_new(self):
        lua, ok = _lua_acc(); self.assertTrue(ok)
        lua.execute(_MOUNT_BOILER + '''
            mgr:_create_heist_timer({})
            mgr:feed_heist_time(300)
            local old_leaf = mgr._hud_heist_timer._timer_text
            _alpha_acquired = old_leaf:alpha()
            tweak_data.levels.test.hud = {no_timer = true}
            mgr:_create_heist_timer()
            local no_timer_leaf = mgr._hud_heist_timer._timer_text
            mgr:feed_heist_time(300)
            _old_alpha_after_switch = old_leaf:alpha()
            _no_timer_leaf_alpha = no_timer_leaf:alpha()
            _timer_prim_vis = kyohud.hud.mission._timer_prim
                and kyohud.hud.mission._timer_prim:visible() or false
            tweak_data.levels.test.hud = {}
            mgr:_create_heist_timer()
            local new_leaf = mgr._hud_heist_timer._timer_text
            mgr:feed_heist_time(600)
            _new_leaf_alpha = new_leaf:alpha()
            _owned_text = kyohud.hud.mission._timer_prim
                and kyohud.hud.mission._timer_prim:text() or nil
            _owned_visible = kyohud.hud.mission._timer_prim
                and kyohud.hud.mission._timer_prim:visible() or false
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._alpha_acquired), 0.0, places=2,
            msg="RED: native alpha must be 0 after initial acquisition")
        self.assertAlmostEqual(float(g._old_alpha_after_switch), 0.37, places=2,
            msg="RED: old leaf must be restored to .37 when timer switched to no_timer")
        self.assertAlmostEqual(float(g._no_timer_leaf_alpha), 0.37, places=2,
            msg="RED: no_timer leaf must remain unmasked at .37")
        self.assertFalse(bool(g._timer_prim_vis),
            "RED: owned timer prim must be invisible when no_timer active")
        self.assertAlmostEqual(float(g._new_leaf_alpha), 0.0, places=2,
            msg="RED: new enabled timer leaf must be acquired to 0")
        self.assertEqual(g._owned_text, "10:00",
            "RED: owned timer must display 10:00 after feed 600")
        self.assertTrue(bool(g._owned_visible),
            "RED: owned timer must be visible after normal timer recreated")


if __name__ == "__main__":
    unittest.main()
