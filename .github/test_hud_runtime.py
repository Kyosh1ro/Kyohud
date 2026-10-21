"""LOT1 -- hud/runtime.lua: lifecycle, root ownership, combat isolation."""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / "lua" / "hud" / "layout.lua"
RUNTIME_PATH = ROOT / "lua" / "hud" / "runtime.lua"

STUBS = '''
kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end
kyohud.settings = kyohud.settings or {}
if kyohud.settings.enable_hud_foundation == nil then
    kyohud.settings.enable_hud_foundation = false
end
if kyohud.settings.hud_scale == nil then
    kyohud.settings.hud_scale = 1.0
end

Hooks = {_all = {}}
function Hooks:PostHook(class, method, id, fn)
    table.insert(self._all, {kind="post", class=class, method=method, id=id, fn=fn})
end
function Hooks:PreHook(class, method, id, fn)
    table.insert(self._all, {kind="pre", class=class, method=method, id=id, fn=fn})
end
function Hooks:Add(id, event, fn) end
function log(...) end
function alive(x) return x ~= nil and x._alive ~= false end
Color = setmetatable({}, {__call = function(...) return {} end})

HUDManager = {}
HUDManager.update = function() end
HUDManager.init_finalize = function() end
HUDManager._setup_player_info_hud_pd2 = function() end
HUDManager.resolution_changed = function() end
HUDManager.set_disabled = function() end
HUDManager.set_enabled = function() end
HUDManager.set_freeflight_disabled = function() end
HUDManager.set_freeflight_enabled = function() end
HUDManager.destroy = function() end

managers = {}
PlayerBase = {
    PLAYER_INFO_HUD_PD2 = "player_info_hud_pd2",
    PLAYER_INFO_HUD_FULLSCREEN_PD2 = "player_info_hud_fullscreen_pd2",
}
RequiredScript = "lib/managers/hudmanagerpd2"
'''

DIESEL = '''
_panel_id = 0
function _make_panel(name)
    _panel_id = _panel_id + 1
    local p = {
        _alive = true, _visible = true, _alpha = 1,
        _children = {}, _name = name or ("p" .. _panel_id),
        _w = 1920, _h = 1080,
    }
    function p:w() return self._w end
    function p:h() return self._h end
    function p:set_shape(x,y,w,h) self._x=x; self._y=y; self._w=w; self._h=h end
    function p:set_visible(v) self._visible = v end
    function p:visible() return self._visible end
    function p:set_alpha(a) self._alpha = a end
    function p:alpha() return self._alpha end
    function p:child(n) return self._children[n] end
    function p:remove(c)
        if c then
            for k, v in pairs(self._children) do
                if v == c then self._children[k] = nil; c._alive = false; return end
            end
        end
    end
    function p:panel(opts)
        local ch = _make_panel(opts and opts.name)
        if opts then
            if opts.w then ch._w = opts.w end
            if opts.h then ch._h = opts.h end
        end
        self._children[ch._name] = ch
        return ch
    end
    return p
end

function _make_parent()
    local p = _make_panel("safe_hud_parent")
    p._w = 1920; p._h = 1080
    return p
end

function _make_mgr(parent)
    local safe = {panel = parent}
    _G.managers.hud = setmetatable({}, {__index = {
        script = function(self, name) return safe end,
        disabled = function() return false end,
    }})
    return safe
end
'''


ACCEPTANCE_ENV = r'''
kyohud={settings={enable_hud_foundation=false,hud_scale=1}}
Kyosh1roHUD=kyohud
PlayerBase={PLAYER_INFO_HUD_PD2='safe'}
HUDManager={}
for _,name in ipairs({'init_finalize','_setup_player_info_hud_pd2','resolution_changed','set_disabled','set_enabled','set_freeflight_disabled','set_freeflight_enabled','update','destroy'}) do HUDManager[name]=function() end end
Hooks={entries={},_all={}}
function Hooks:PostHook(c,m,id,fn) assert(type(c[m])=='function','hook absent method'); table.insert(self.entries,{method=m,id=id,fn=fn}); table.insert(self._all,{kind='post',class=c,method=m,id=id,fn=fn}) end
Hooks.PreHook=Hooks.PostHook
function fire(m,mgr,...)
 for _,e in ipairs(Hooks.entries) do if e.method==m then e.fn(mgr,...) end end
end
S=setmetatable({},{__mode='k'})
function alive(p) return S[p] and S[p].alive==true end
function panel(w,h,parent)
 local p=newproxy(true)
 S[p]={alive=true,w=w or 1280,h=h or 720,parent=parent,children={},visible=true,creates=0,removes=0,shape_calls=0}
 local methods={}
 function methods:w() return S[self].w end
 function methods:h() return S[self].h end
 function methods:parent() return S[self].parent end
 function methods:child(name) return S[self].children[name] end
 function methods:panel(opts)
  S[self].creates=S[self].creates+1
  local ch=panel(opts.w or S[self].w,opts.h or S[self].h,self)
  S[ch].layer=opts.layer
  S[self].children[opts.name]=ch
  return ch
 end
 function methods:remove(ch)
  if S[self].fail_remove then error('remove blocked') end
  S[self].removes=S[self].removes+1
  for k,v in pairs(S[self].children) do if v==ch then S[self].children[k]=nil end end
  S[ch].alive=false
 end
 function methods:set_shape(x,y,w,h)
  if S[self].fail_shape then error('shape blocked') end
  S[self].x=x;S[self].y=y;S[self].w=w;S[self].h=h;S[self].shape_calls=S[self].shape_calls+1
 end
 function methods:set_visible(v) S[self].visible=v end
 function methods:visible() return S[self].visible end
 getmetatable(p).__index=methods
 getmetatable(p).__newindex=function() error('Diesel userdata arbitrary field assignment') end
 return p
end
function manager()
 local m={p=panel(1280,720),off=false}
 function m:script(id) assert(id=='safe');return {panel=self.p} end
 function m:disabled() return self.off end
 return m
end
M=manager();managers={hud=M}
RequiredScript='lib/managers/hudmanagerpd2'
function log() end
'''


def acceptance_env(context='lib/managers/hudmanagerpd2', methods=True):
    l = LuaRuntime(unpack_returned_tuples=True)
    l.execute(ACCEPTANCE_ENV)
    l.globals().RequiredScript = context
    if not methods:
        l.execute('HUDManager={}')
    for name in ['layout', 'native_visibility', 'runtime']:
        l.execute((ROOT / 'lua' / 'hud' / f'{name}.lua').read_text(encoding='utf-8-sig'))
    return l


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute(DIESEL)
    lua.execute(_read(LAYOUT_PATH))
    rt = _read(RUNTIME_PATH)
    if rt is not None:
        lua.execute(rt)
    return lua, rt is not None


class RuntimeExistsTests(unittest.TestCase):
    def test_file_exists(self):
        self.assertTrue(RUNTIME_PATH.is_file())

    def test_namespace_and_alias(self):
        lua, ok = _lua()
        self.assertTrue(ok, "runtime.lua must exist")
        lua.execute("assert(type(kyohud.hud.runtime) == 'table')")
        lua.execute("assert(rawequal(kyohud, Kyosh1roHUD))")

    def test_methods_are_functions(self):
        lua, _ = _lua()
        lua.execute('''
            local RT = kyohud.hud.runtime
            for _, n in ipairs{"mount","unmount","rebuild","refresh_settings",
                "on_heist_start","destroy","update"} do
                assert(type(RT[n]) == "function", n .. " must be function")
            end
        ''')


class DefaultStateTests(unittest.TestCase):
    def test_defaults(self):
        lua, _ = _lua()
        lua.execute('''
            _r = kyohud.hud.runtime._root_panel
            _p = kyohud.hud.runtime._parent_panel
            _m = kyohud.hud.runtime._manager
            _mnt = kyohud.hud.runtime._mounted
            _g = kyohud.hud.runtime._generation or 0
            _hg = kyohud.hud.runtime._heist_generation or 0
        ''')
        g = lua.globals()
        self.assertIsNone(g._r)
        self.assertIsNone(g._p)
        self.assertIsNone(g._m)
        self.assertFalse(bool(g._mnt))
        self.assertEqual(int(g._g), 0)
        self.assertEqual(int(g._hg), 0)


class MountTests(unittest.TestCase):
    def _mount(self, lua):
        lua.execute('''
            _fp = _make_parent()
            _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
        ''')

    def test_mount_creates_root(self):
        lua, _ = _lua()
        self._mount(lua)
        lua.execute("_r = kyohud.hud.runtime._root_panel")
        self.assertIsNotNone(lua.globals()._r)

    def test_disabled_no_root(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = false
            kyohud.hud.runtime:mount(_G.managers.hud)
            _r = kyohud.hud.runtime._root_panel
        ''')
        self.assertIsNone(lua.globals()._r)

    def test_no_manager_no_root(self):
        lua, _ = _lua()
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            _G.managers.hud = nil
            kyohud.hud.runtime:mount(nil)
            _r = kyohud.hud.runtime._root_panel
        ''')
        self.assertIsNone(lua.globals()._r)

    def test_vr_no_root(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            _G.IS_VR = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _r = kyohud.hud.runtime._root_panel
        ''')
        self.assertIsNone(lua.globals()._r)

    def test_idempotent_single_root(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            _cnt = 0
            local _orig = _fp.panel
            _fp.panel = function(self, opts)
                _cnt = _cnt + 1
                return _orig(self, opts)
            end
        ''')
        for _ in range(3):
            lua.execute("kyohud.hud.runtime:mount(_G.managers.hud)")
        lua.execute("_r = kyohud.hud.runtime._root_panel")
        self.assertIsNotNone(lua.globals()._r)
        self.assertEqual(int(lua.globals()._cnt), 1)


class UnmountTests(unittest.TestCase):
    def test_unmount_clears(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _rname = kyohud.hud.runtime._root_panel._name
            kyohud.hud.runtime:unmount()
            _r = kyohud.hud.runtime._root_panel
            _mnt = kyohud.hud.runtime._mounted
            _child = _fp:child(tostring(_rname))
        ''')
        g = lua.globals()
        self.assertIsNone(g._r)
        self.assertFalse(bool(g._mnt))
        self.assertIsNone(g._child)

    def test_unmount_failure_preserves_handle(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _orig_root = kyohud.hud.runtime._root_panel
            _orig_remove = _fp.remove
            _fp.remove = function() error("engine fail") end
            local _ok, _err = pcall(function() kyohud.hud.runtime:unmount() end)
            _r = kyohud.hud.runtime._root_panel
            _fp.remove = _orig_remove
            _retry_ok = pcall(function() kyohud.hud.runtime:unmount() end)
            _r2 = kyohud.hud.runtime._root_panel
            _removed = not alive(_orig_root)
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._r,
            "unmount failure must retain root handle for retry")
        self.assertTrue(bool(g._retry_ok),
            "retry unmount must succeed without error")
        self.assertIsNone(g._r2,
            "retry unmount must clear root panel")
        self.assertTrue(bool(g._removed),
            "retry unmount must actually remove old root")


class CombatIsolationTests(unittest.TestCase):
    def test_rebuild_preserves_score_kills_buffs(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud._heist_score_total = 42
            kyohud._kills = {{name="a"},{name="b"}}
            kyohud._buffs = {overkill={id="overkill"}}
            kyohud.hud.runtime:mount(_G.managers.hud)
            kyohud.hud.runtime:rebuild(_G.managers.hud)
            _s = kyohud._heist_score_total
            _k = #kyohud._kills
            _b = kyohud._buffs.overkill ~= nil
        ''')
        g = lua.globals()
        self.assertEqual(int(g._s), 42)
        self.assertEqual(int(g._k), 2)
        self.assertTrue(bool(g._b))

    def test_rebuild_increments_generation(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _g1 = kyohud.hud.runtime._generation
            kyohud.hud.runtime:rebuild(_G.managers.hud)
            _g2 = kyohud.hud.runtime._generation
        ''')
        self.assertGreater(int(lua.globals()._g2), int(lua.globals()._g1))

    def test_heist_gen_increments_only_on_heist_start(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            kyohud.hud.runtime:on_heist_start(_G.managers.hud)
            _h1 = kyohud.hud.runtime._heist_generation
            kyohud.hud.runtime:rebuild(_G.managers.hud)
            kyohud.hud.runtime:refresh_settings(_G.managers.hud)
            kyohud.hud.runtime:update(_G.managers.hud, 1, 0.016)
            _h2 = kyohud.hud.runtime._heist_generation
            kyohud.hud.runtime:on_heist_start(_G.managers.hud)
            _h3 = kyohud.hud.runtime._heist_generation
            _make_mgr(_fp)
            local mgr2 = _G.managers.hud
            kyohud.hud.runtime:on_heist_start(mgr2)
            _h4 = kyohud.hud.runtime._heist_generation
        ''')
        g = lua.globals()
        self.assertEqual(int(g._h1), int(g._h2))
        self.assertEqual(int(g._h3), int(g._h2),
            "same manager must not increment heist_generation twice")
        self.assertGreater(int(g._h4), int(g._h3),
            "different manager must increment heist_generation")


class HookTests(unittest.TestCase):
    def test_hooks_on_hudmanager_only(self):
        lua, _ = _lua()
        lua.execute('''
            _bad = 0
            for _, e in ipairs(Hooks._all) do
                if e.class ~= HUDManager then _bad = _bad + 1 end
            end
        ''')
        self.assertEqual(int(lua.globals()._bad), 0)

    def test_expected_hook_methods(self):
        lua, _ = _lua()
        lua.execute('''
            _methods = {}
            for _, e in ipairs(Hooks._all) do
                _methods[e.kind .. ":" .. e.method] = true
            end
        ''')
        expected = [
            "post:init_finalize", "post:_setup_player_info_hud_pd2",
            "post:resolution_changed", "post:set_disabled",
            "post:set_enabled", "post:set_freeflight_disabled",
            "post:set_freeflight_enabled", "post:update",
            "pre:destroy",
        ]
        for m in expected:
            self.assertTrue(
                bool(lua.eval(f"function() return _methods['{m}'] or false end")()),
                f"missing hook {m}",
            )

    def test_double_load_no_duplicate_hooks(self):
        lua, _ = _lua()
        lua.execute("_before = #Hooks._all")
        lua.execute(_read(RUNTIME_PATH))
        lua.execute("_after = #Hooks._all")
        self.assertEqual(int(lua.globals()._before), int(lua.globals()._after))


class DestroyAndRecoveryTests(unittest.TestCase):
    def test_destroy_clears_no_combat_reset(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud._heist_score_total = 99
            kyohud.hud.runtime:mount(_G.managers.hud)
            kyohud.hud.runtime:destroy(_G.managers.hud)
            _r = kyohud.hud.runtime._root_panel
            _mnt = kyohud.hud.runtime._mounted
            _s = kyohud._heist_score_total
        ''')
        g = lua.globals()
        self.assertIsNone(g._r)
        self.assertFalse(bool(g._mnt))
        self.assertEqual(int(g._s), 99)

    def test_update_recovery_throttled(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _old_root = kyohud.hud.runtime._root_panel
            _fp:remove(_old_root)
            _script_calls = 0
            _orig_script = _G.managers.hud.script
            _G.managers.hud.script = function(self, name)
                _script_calls = _script_calls + 1
                return _orig_script(self, name)
            end
        ''')
        for t in [1.0, 1.1, 1.2, 1.3, 1.4]:
            lua.execute(f"kyohud.hud.runtime:update(_G.managers.hud, {t}, 0.016)")
        lua.execute('''
            _r = kyohud.hud.runtime._root_panel
            _alive = _r ~= nil and _r._alive ~= false
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._r, "recovery must recreate root")
        self.assertTrue(bool(g._alive), "recovered root must be alive")
        self.assertLessEqual(int(g._script_calls), 2,
            "recovery must throttle parent discovery to <=2 calls in 0.5s")

    def test_foreign_same_name_not_touched(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            local foreign = _fp:panel({name = "kyohud_root_panel"})
            foreign._foreign = true
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            kyohud.hud.runtime:unmount()
            _ch = _fp:child("kyohud_root_panel")
            _is_foreign = _ch ~= nil and _ch._foreign == true
        ''')
        self.assertTrue(bool(lua.globals()._is_foreign))


SHARED_USERDATA_DIESEL = '''
_upanel_id = 0
function _make_userdata_panel(name)
    _upanel_id = _upanel_id + 1
    local private = {
        _alive = true, _visible = true, _alpha = 1,
        _children = {}, _name = name or ("up" .. _upanel_id),
        _w = 1920, _h = 1080, _x = 0, _y = 0,
    }
    local ud = newproxy(true)
    local mt = getmetatable(ud)
    mt.__index = function(self, key)
        if key == "child" then
            if private._child_errors then
                error("child lookup crashed")
            end
            return function(_, n) return private._children[n] end
        end
        if key == "w" then return function() return private._w end end
        if key == "h" then return function() return private._h end end
        if key == "set_shape" then return function(_, x, y, w, h)
            private._x = x; private._y = y; private._w = w; private._h = h
        end end
        if key == "set_visible" then return function(_, v) private._visible = v end end
        if key == "visible" then return function() return private._visible end end
        if key == "set_alpha" then return function(_, a) private._alpha = a end end
        if key == "alpha" then return function() return private._alpha end end
        if key == "remove" then return function(_, c)
            if c then
                for k, v in pairs(private._children) do
                    if v == c then private._children[k] = nil; c._private._alive = false; return end
                end
            end
        end end
        if key == "panel" then return function(_, opts)
            local ch = _make_userdata_panel(opts and opts.name)
            if opts then
                if opts.w then ch._private._w = opts.w end
                if opts.h then ch._private._h = opts.h end
            end
            private._children[opts and opts.name or "anon"] = ch
            return ch
        end end
        if key == "_private" then return private end
        if key == "_alive" then return private._alive end
        return nil
    end
    mt.__newindex = function(self, key, value)
        error("cannot set arbitrary fields on userdata panel: " .. tostring(key))
    end
    return ud
end

function _make_ud_parent()
    local p = _make_userdata_panel("safe_hud_parent")
    return p
end

function _make_ud_mgr(parent)
    local safe = {panel = parent}
    _G.managers.hud = setmetatable({}, {__index = {
        script = function(self, name) return safe end,
        disabled = function() return false end,
    }})
    return safe
end
'''


def _lua_ud():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute(SHARED_USERDATA_DIESEL)
    lua.execute(_read(LAYOUT_PATH))
    rt = _read(RUNTIME_PATH)
    if rt:
        lua.execute(rt)
    return lua


class UserdataPanelTests(unittest.TestCase):
    def test_userdata_panel_rejects_arbitrary_fields(self):
        lua = _lua_ud()
        lua.execute('''
            _p = _make_userdata_panel("test")
            _ok, _err = pcall(function() _p._ky_owned = true end)
        ''')
        self.assertFalse(bool(lua.globals()._ok),
            "userdata panel must reject arbitrary field assignment")

    def test_mount_with_userdata_parent_creates_root(self):
        lua = _lua_ud()
        lua.execute('''
            _fp = _make_ud_parent()
            _make_ud_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _r = kyohud.hud.runtime._root_panel
        ''')
        self.assertIsNotNone(lua.globals()._r,
            "mount must work with userdata panels")

    def test_no_ky_owned_written_to_panel(self):
        lua = _lua_ud()
        lua.execute('''
            _fp = _make_ud_parent()
            _make_ud_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            _ok = pcall(function() kyohud.hud.runtime:mount(_G.managers.hud) end)
        ''')
        self.assertTrue(bool(lua.globals()._ok),
            "mount must not write _ky_owned or any field to panels")


class ReloadPreservationTests(unittest.TestCase):
    def test_reload_preserves_root_and_hooks(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _root1 = kyohud.hud.runtime._root_panel
            _gen1 = kyohud.hud.runtime._generation
        ''')
        lua.execute(_read(RUNTIME_PATH))
        lua.execute('''
            _root2 = kyohud.hud.runtime._root_panel
            _gen2 = kyohud.hud.runtime._generation
            _same_rt = rawequal(_root1, _root2)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._same_rt),
            "reload must preserve existing root panel handle")
        self.assertEqual(int(g._gen1), int(g._gen2),
            "reload must preserve generation")


class RefreshSettingsTests(unittest.TestCase):
    def test_refresh_settings_sets_shape(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.hud_scale = 1.0
            kyohud.hud.runtime:mount(_G.managers.hud)
            _root = kyohud.hud.runtime._root_panel
            _root:set_shape(0, 0, 1, 1)
            kyohud.hud.runtime:refresh_settings(_G.managers.hud)
            _w = _root:w()
            _h = _root:h()
        ''')
        g = lua.globals()
        self.assertEqual(int(g._w), 1920,
            "refresh_settings must set root width to parent:w()")
        self.assertEqual(int(g._h), 1080,
            "refresh_settings must set root height to parent:h()")

    def test_refresh_settings_computes_layout(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.hud_scale = 1.5
            kyohud.hud.runtime:mount(_G.managers.hud)
            kyohud.hud.runtime:refresh_settings(_G.managers.hud)
            _layout = kyohud.hud.runtime._layout
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._layout,
            "refresh_settings must store computed layout")

    def test_refresh_settings_not_mounted_noop(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = false
            kyohud.hud.runtime:refresh_settings(_G.managers.hud)
            _r = kyohud.hud.runtime._root_panel
        ''')
        self.assertIsNone(lua.globals()._r,
            "refresh_settings when disabled must not create root")

    def test_refresh_settings_enabled_mounts(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:refresh_settings(_G.managers.hud)
            _r = kyohud.hud.runtime._root_panel
            _mnt = kyohud.hud.runtime._mounted
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._r,
            "refresh_settings when enabled must mount and create root")
        self.assertTrue(bool(g._mnt))


class VisibilityHookTests(unittest.TestCase):
    def test_disabled_sets_root_invisible(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _root = kyohud.hud.runtime._root_panel
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_disabled" then e.fn(_G.managers.hud) end
            end
            _vis = _root:visible()
        ''')
        self.assertFalse(bool(lua.globals()._vis),
            "set_disabled hook must set root invisible")

    def test_freeflight_sets_root_invisible(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _root = kyohud.hud.runtime._root_panel
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_freeflight_disabled" then e.fn(_G.managers.hud) end
            end
            _vis = _root:visible()
        ''')
        self.assertFalse(bool(lua.globals()._vis),
            "freeflight hook must set root invisible")

    def test_reenable_restores_visible(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _root = kyohud.hud.runtime._root_panel
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_disabled" then e.fn(_G.managers.hud) end
            end
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_enabled" then e.fn(_G.managers.hud) end
            end
            _vis = _root:visible()
        ''')
        self.assertTrue(bool(lua.globals()._vis),
            "set_enabled after disabled must restore visibility")

    def test_freeflight_return_no_show_if_disabled(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _root = kyohud.hud.runtime._root_panel
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_disabled" then e.fn(_G.managers.hud) end
            end
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_freeflight_enabled" then e.fn(_G.managers.hud) end
            end
            _vis = _root:visible()
        ''')
        self.assertFalse(bool(lua.globals()._vis),
            "returning from freeflight must not show a disabled HUD")


class HeistIdentityExtraTests(unittest.TestCase):
    def test_init_finalize_triggers_heist_start(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _h0 = kyohud.hud.runtime._heist_generation
            for _, e in ipairs(Hooks._all) do
                if e.method == "init_finalize" then e.fn(_G.managers.hud) end
            end
            _h1 = kyohud.hud.runtime._heist_generation
        ''')
        g = lua.globals()
        self.assertGreater(int(g._h1), int(g._h0),
            "init_finalize must call on_heist_start")

    def test_destroy_resets_heist_identity(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            kyohud.hud.runtime:on_heist_start(_G.managers.hud)
            _h1 = kyohud.hud.runtime._heist_generation
            kyohud.hud.runtime:destroy(_G.managers.hud)
            kyohud.hud.runtime:mount(_G.managers.hud)
            kyohud.hud.runtime:on_heist_start(_G.managers.hud)
            _h2 = kyohud.hud.runtime._heist_generation
        ''')
        g = lua.globals()
        self.assertGreater(int(g._h2), int(g._h1),
            "after destroy, new heist start must increment again")


class DeadRootRemountTests(unittest.TestCase):
    def test_mount_detects_dead_root_and_remounts(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _old_root = kyohud.hud.runtime._root_panel
            _old_root._alive = false
            kyohud.hud.runtime:mount(_G.managers.hud)
            _r = kyohud.hud.runtime._root_panel
            _alive = _r ~= nil
            _is_new = (_r ~= _old_root)
            _new_alive = _r ~= nil and _r._alive ~= false
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._alive),
            "mount with dead root must detect and create new root")
        self.assertTrue(bool(g._is_new),
            "new root must be a different object from dead root")
        self.assertTrue(bool(g._new_alive),
            "new root must be alive")


class ForeignSentinelTests(unittest.TestCase):
    def test_foreign_table_with_ky_owned_not_mutated(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            local foreign = _fp:panel({name = "kyohud_root_panel"})
            foreign._ky_owned = true
            kyohud.settings.enable_hud_foundation = true
            _ok = pcall(function() kyohud.hud.runtime:mount(_G.managers.hud) end)
            _mnt = kyohud.hud.runtime._mounted
            kyohud.hud.runtime:unmount()
            _ch = _fp:child("kyohud_root_panel")
            _still_foreign = _ch ~= nil and _ch._ky_owned == true
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._still_foreign),
            "foreign sentinel with _ky_owned=true must not be mutated or removed")


class ManagerArgumentTests(unittest.TestCase):
    def test_uses_manager_script_argument(self):
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent()
            _script_calls = {}
            local fake_mgr = setmetatable({}, {__index = {
                script = function(self, name)
                    table.insert(_script_calls, name)
                    return {panel = _fp}
                end,
                disabled = function() return false end,
            }})
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(fake_mgr)
            _called = #_script_calls > 0
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._called),
            "mount must use manager:script() argument, not global managers.hud")


class MountDestroyFailureTests(unittest.TestCase):
    def test_mount_retains_old_root_when_destroy_fails(self):
        """SOL probe (1): env from verify_foundation_acceptance - must retain old root"""
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _old_root = kyohud.hud.runtime._root_panel
            _old_gen = kyohud.hud.runtime._generation
            _fp.remove = function() error("engine fail") end
            _new_parent = _make_parent()
            _make_mgr(_new_parent)
            kyohud.hud.runtime:mount(_G.managers.hud)
            _r = kyohud.hud.runtime._root_panel
            _g = kyohud.hud.runtime._generation
            _is_old = (_r == _old_root)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._is_old),
            "mount must retain old root when _destroy_owned_root fails")
        self.assertEqual(int(g._g), int(g._old_gen),
            "generation must not increment when destroy fails")

    def test_mount_retry_succeeds_after_restoring_api(self):
        """SOL probe (1) retry: restore remove then retry actually removes old"""
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _old_root = kyohud.hud.runtime._root_panel
            _orig_remove = _fp.remove
            _fp.remove = function() error("engine fail") end
            _new_parent = _make_parent()
            _make_mgr(_new_parent)
            kyohud.hud.runtime:mount(_G.managers.hud)
            _r1 = kyohud.hud.runtime._root_panel
            _fp.remove = _orig_remove
            kyohud.hud.runtime:mount(_G.managers.hud)
            _r2 = kyohud.hud.runtime._root_panel
            _removed = not alive(_old_root)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._removed),
            "after restoring API, old root must be removed")
        self.assertNotEqual(g._r1, g._r2,
            "retry mount must create new root")

    def test_remove_false_on_rebuild_retains_identity(self):
        """SOL extra: remove false or missing on rebuild => retain identity and no duplicate"""
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _old_root = kyohud.hud.runtime._root_panel
            _fp.remove = function() return false end
            kyohud.hud.runtime:rebuild(_G.managers.hud)
            _r = kyohud.hud.runtime._root_panel
            _is_same = (_r == _old_root)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._is_same),
            "rebuild with remove returning false must retain identity")

    def test_remove_missing_on_unmount_retains_identity(self):
        """SOL extra: remove missing on unmount => retain identity"""
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _old_root = kyohud.hud.runtime._root_panel
            _fp.remove = nil
            kyohud.hud.runtime:unmount()
            _r = kyohud.hud.runtime._root_panel
            _is_same = (_r == _old_root)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._is_same),
            "unmount with remove missing must retain identity")

    def test_failed_unmount_option_off_then_restore(self):
        """SOL extra: failed unmount with option off then restoring remove + update => root removed"""
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _orig_remove = _fp.remove
            _fp.remove = function() error("fail") end
            kyohud.settings.enable_hud_foundation = false
            kyohud.hud.runtime:refresh_settings(_G.managers.hud)
            _r1 = kyohud.hud.runtime._root_panel
            _fp.remove = _orig_remove
            kyohud.hud.runtime:update(_G.managers.hud, 10, 0.016)
            _r2 = kyohud.hud.runtime._root_panel
        ''')
        g = lua.globals()
        self.assertIsNone(g._r2,
            "after restoring remove and update, root must be removed")


class UpdateThrottleTests(unittest.TestCase):
    def test_update_throttles_parent_discovery(self):
        """SOL probe (2): twenty update calls at t=10+i*.01 must call script <=2"""
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _calls = 0
            _orig_script = _G.managers.hud.script
            _G.managers.hud.script = function(self, name)
                _calls = _calls + 1
                return _orig_script(self, name)
            end
            for i = 0, 19 do
                local t = 10 + i * 0.01
                kyohud.hud.runtime:update(_G.managers.hud, t, 0.016)
            end
        ''')
        self.assertLessEqual(int(lua.globals()._calls), 2,
            "update must throttle parent discovery to <=2 calls in 0.2s")


class HookRegistrationGuardTests(unittest.TestCase):
    def test_per_method_hook_guard_absent_then_add(self):
        """Per-method bookkeeping: only HUDManager.update present => exactly 1 hook, reload stays 1."""
        l = acceptance_env(methods=False)
        l.execute('HUDManager.update = function() end')
        l.execute((ROOT / 'lua' / 'hud' / 'runtime.lua').read_text(encoding='utf-8-sig'))
        l.execute('_after1 = #Hooks.entries')
        l.execute((ROOT / 'lua' / 'hud' / 'runtime.lua').read_text(encoding='utf-8-sig'))
        l.execute('_after2 = #Hooks.entries')
        g = l.globals()
        self.assertEqual(int(g._after1), 1,
            "adding update method after initial load must install exactly 1 hook")
        self.assertEqual(int(g._after2), 1,
            "reload must not duplicate the update hook")


class StaleManagerIsolationTests(unittest.TestCase):
    def test_stale_callbacks_no_affect_newer_root(self):
        """SOL probe (7): stale manager callbacks ALL kinds cannot affect newer root"""
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent(); _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _old_mgr = _G.managers.hud
            _old_root = kyohud.hud.runtime._root_panel
            _fp2 = _make_parent()
            _make_mgr(_fp2)
            kyohud.hud.runtime:mount(_G.managers.hud)
            _new_root = kyohud.hud.runtime._root_panel
            _gen_before = kyohud.hud.runtime._generation
            _new_vis_before = _new_root:visible()

            for _, e in ipairs(Hooks._all) do
                if e.method == "set_disabled" then e.fn(_old_mgr) end
            end
            _vis_after_disabled = _new_root:visible()

            for _, e in ipairs(Hooks._all) do
                if e.method == "set_enabled" then e.fn(_old_mgr) end
            end
            _vis_after_enabled = _new_root:visible()

            for _, e in ipairs(Hooks._all) do
                if e.method == "set_freeflight_disabled" then e.fn(_old_mgr) end
            end
            _vis_after_ff_off = _new_root:visible()

            for _, e in ipairs(Hooks._all) do
                if e.method == "set_freeflight_enabled" then e.fn(_old_mgr) end
            end
            _vis_after_ff_on = _new_root:visible()

            for _, e in ipairs(Hooks._all) do
                if e.method == "resolution_changed" then e.fn(_old_mgr) end
            end
            _same_after_res = (kyohud.hud.runtime._root_panel == _new_root)

            for _, e in ipairs(Hooks._all) do
                if e.method == "update" then e.fn(_old_mgr, 100, 0.016) end
            end
            _same_after_update = (kyohud.hud.runtime._root_panel == _new_root)
            _gen_after = kyohud.hud.runtime._generation

            for _, e in ipairs(Hooks._all) do
                if e.method == "destroy" then e.fn(_old_mgr) end
            end
            _same_after_destroy = (kyohud.hud.runtime._root_panel == _new_root)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._vis_after_disabled),
            "stale set_disabled must not hide newer root")
        self.assertTrue(bool(g._vis_after_enabled),
            "stale set_enabled must not affect newer root")
        self.assertTrue(bool(g._vis_after_ff_off),
            "stale freeflight_disabled must not hide newer root")
        self.assertTrue(bool(g._vis_after_ff_on),
            "stale freeflight_enabled must not affect newer root")
        self.assertTrue(bool(g._same_after_res),
            "stale resolution_changed must not recreate newer root")
        self.assertTrue(bool(g._same_after_update),
            "stale update must not recreate newer root")
        self.assertEqual(int(g._gen_before), int(g._gen_after),
            "stale callbacks must not increment generation")
        self.assertTrue(bool(g._same_after_destroy),
            "stale destroy must not remove newer root")


class UserdataChildExceptionTests(unittest.TestCase):
    def test_child_exception_protected_by_pcall(self):
        """SOL probe (8): child() exceptions outside pcall must be protected"""
        lua = _lua_ud()
        lua.execute('''
            _fp = _make_ud_parent()
            _fp._private._child_errors = true
            _make_ud_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            _ok = pcall(function() kyohud.hud.runtime:mount(_G.managers.hud) end)
        ''')
        self.assertTrue(bool(lua.globals()._ok),
            "child() exception must be protected by pcall")

    def test_child_throws_with_foreign_same_name(self):
        """SOL extra: parent.child throws while foreign same-name root exists => must not create/remove anything"""
        lua = _lua_ud()
        lua.execute('''
            _fp = _make_ud_parent()
            -- Create a foreign panel with the same name
            local foreign_private = {
                _alive = true,
                _foreign = true,
                _name = "kyohud_root_panel",
                _w = 1920,
                _h = 1080,
            }
            local foreign = newproxy(true)
            local foreign_mt = getmetatable(foreign)
            foreign_mt.__index = function(self, key)
                if key == "w" then return function() return foreign_private._w end end
                if key == "h" then return function() return foreign_private._h end end
                return nil
            end
            -- Add foreign to parent's children
            _fp._private._children["kyohud_root_panel"] = foreign
            -- Make child throw
            _fp._private._child_errors = true
            _make_ud_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            _ok = pcall(function() kyohud.hud.runtime:mount(_G.managers.hud) end)
            _mnt = kyohud.hud.runtime._mounted
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._ok),
            "mount must not throw")
        self.assertFalse(bool(g._mnt),
            "mount must not succeed when child throws with foreign present")


class InitialMountParentAbsentTests(unittest.TestCase):
    def test_initial_mount_parent_absent_then_present(self):
        """Retry: initial failed mount, parent restored, update retries => mounted live root."""
        l = acceptance_env()
        l.execute('''
        local rt=kyohud.hud.runtime
        kyohud.settings.enable_hud_foundation=true
        local p=M.p
        M.p=nil
        fire('init_finalize',M)
        M.p=p
        fire('update',M,10,.5)
        assert(alive(rt._root_panel),'initial failed mount never retried')
        ''')


class ShapeFailureRecoveryTests(unittest.TestCase):
    def test_shape_fails_during_refresh_then_recovers(self):
        """Retry: shape fails during refresh, update retries => root shaped to new width."""
        l = acceptance_env()
        l.execute('''
        kyohud.settings.enable_hud_foundation=true
        fire('init_finalize',M)
        local rt=kyohud.hud.runtime
        local r=rt._root_panel
        S[r].fail_shape=true
        S[M.p].w=1024
        rt:refresh_settings(M)
        S[r].fail_shape=false
        fire('update',M,10,.5)
        assert(S[r].w==1024,'failed refresh never retried')
        ''')


class FoundationAcceptanceTests(unittest.TestCase):
    def test_toggle_mount_unmount_no_combat_reset(self):
        l = acceptance_env()
        l.execute('''
        kyohud.ResetHeistCombatState=function() error('combat reset prohibited') end
        fire('init_finalize',M)
        assert(kyohud.hud.runtime._root_panel==nil)
        kyohud.settings.enable_hud_foundation=true
        kyohud.hud.runtime:refresh_settings(M)
        local r=kyohud.hud.runtime._root_panel
        assert(alive(r),'activation must create owned Diesel root')
        assert(S[r].w==1280 and S[r].h==720,'root effective dimensions')
        kyohud.settings.enable_hud_foundation=false
        kyohud.hud.runtime:refresh_settings(M)
        assert(not alive(r),'deactivation must remove root')
        assert(kyohud.hud.runtime._root_panel==nil)
        ''')

    def test_wrong_context_then_correct_context(self):
        l = acceptance_env('unrelated/context')
        l.execute("assert(#Hooks.entries==0,'wrong context installed hooks')")
        l.execute("assert(#Hooks._all==0,'wrong context installed hooks (_all)')")
        l.globals().RequiredScript = 'lib/managers/hudmanagerpd2'
        l.execute((ROOT / 'lua' / 'hud' / 'runtime.lua').read_text(encoding='utf-8-sig'))
        l.execute("assert(#Hooks.entries==9,'late correct context must install hooks')")

    def test_no_hooks_side_effects(self):
        l = acceptance_env(methods=False)
        l.execute('assert(#Hooks.entries==0)')
        l.execute('assert(#Hooks._all==0)')

    def test_repeated_heist_does_not_follow_graphics_generation(self):
        l = acceptance_env()
        l.execute('''
        kyohud.settings.enable_hud_foundation=true
        fire('init_finalize',M)
        local rt=kyohud.hud.runtime
        local h=rt._heist_generation
        rt:unmount();rt:mount(M);fire('init_finalize',M)
        assert(rt._heist_generation==h,'remount must not reset heist identity')
        local g=rt._generation
        rt:unmount();rt:mount(M)
        assert(rt._generation>g,'each created root needs unique generation')
        ''')

    def test_changed_parent_recovered_without_reset(self):
        l = acceptance_env()
        l.execute('''
        kyohud.settings.enable_hud_foundation=true;fire('init_finalize',M)
        local rt=kyohud.hud.runtime;local old=rt._root_panel;local oldp=M.p;local h=rt._heist_generation
        M.p=panel(1024,768)
        fire('update',M,10,.5)
        assert(rt._parent_panel==M.p,'replacement parent not discovered')
        assert(alive(rt._root_panel) and rt._root_panel~=old)
        assert(not alive(old),'old owned root leaked')
        assert(rt._heist_generation==h)
        ''')

    def test_failed_rebuild_keeps_retryable_identity(self):
        l = acceptance_env()
        l.execute('''
        kyohud.settings.enable_hud_foundation=true;fire('init_finalize',M)
        local rt=kyohud.hud.runtime;local old=rt._root_panel;local n=S[M.p].creates
        S[M.p].fail_remove=true
        rt:rebuild(M)
        assert(rt._root_panel==old,'failed rebuild lost owned identity')
        assert(S[M.p].creates==n,'failed removal created duplicate root')
        S[M.p].fail_remove=false;rt:rebuild(M)
        assert(not alive(old) and alive(rt._root_panel))
        ''')

    def test_disabled_and_freeflight_combined(self):
        l = acceptance_env()
        l.execute('''
        kyohud.settings.enable_hud_foundation=true;M.off=true;fire('init_finalize',M)
        local rt=kyohud.hud.runtime;assert(not rt._root_panel:visible())
        fire('set_freeflight_disabled',M);fire('set_freeflight_enabled',M)
        assert(not rt._root_panel:visible())
        M.off=false;fire('set_enabled',M);assert(rt._root_panel:visible())
        ''')

    def test_new_manager_replaces_old_owned_root(self):
        l = acceptance_env()
        l.execute('''
        kyohud.settings.enable_hud_foundation=true;fire('init_finalize',M)
        local rt=kyohud.hud.runtime;local old=rt._root_panel;local h=rt._heist_generation
        local newer=manager();managers.hud=newer;fire('init_finalize',newer)
        assert(rt._manager==newer and rt._parent_panel==newer.p)
        assert(not alive(old) and rt._heist_generation==h+1)
        fire('destroy',M)
        assert(alive(rt._root_panel),'stale manager destroy removed new manager root')
        ''')


class ThirdPartyCollisionTests(unittest.TestCase):
    def test_update_does_not_create_root_when_foreign_same_name_exists(self):
        """Owned root destroyed, foreign kyohud_root_panel alive, update must not create new root.
        After collision removed, next update recovers."""
        l = acceptance_env()
        l.execute('''
        kyohud.settings.enable_hud_foundation=true
        fire('init_finalize',M)
        local rt=kyohud.hud.runtime
        local old=rt._root_panel
        S[old].alive=false
        local foreign=panel(100,100,M.p)
        S[M.p].children["kyohud_root_panel"]=foreign
        local n_creates=S[M.p].creates
        fire('update',M,10,.5)
        assert(S[M.p].creates==n_creates,'update must not create root when foreign panel exists, creates='..tostring(S[M.p].creates-n_creates))
        assert(rt._root_panel==nil,'root_panel must be nil when foreign panel blocks')
        assert(S[foreign].alive==true,'foreign panel must not be deleted')
        S[M.p].children["kyohud_root_panel"]=nil
        fire('update',M,11,.5)
        assert(alive(rt._root_panel),'update must recover after collision removed')
        assert(rt._root_panel~=foreign,'recovered root must not be the foreign panel')
        ''')

    def test_rebuild_does_not_create_root_when_foreign_same_name_exists(self):
        """rebuild with foreign kyohud_root_panel alive must not create new root.
        After collision removed, rebuild recovers."""
        l = acceptance_env()
        l.execute('''
        kyohud.settings.enable_hud_foundation=true
        fire('init_finalize',M)
        local rt=kyohud.hud.runtime
        local old=rt._root_panel
        S[old].alive=false
        local foreign=panel(100,100,M.p)
        S[M.p].children["kyohud_root_panel"]=foreign
        local n_creates=S[M.p].creates
        rt:rebuild(M)
        assert(S[M.p].creates==n_creates,'rebuild must not create root when foreign panel exists, creates='..tostring(S[M.p].creates-n_creates))
        assert(rt._root_panel==nil,'root_panel must be nil when foreign panel blocks rebuild')
        S[M.p].children["kyohud_root_panel"]=nil
        rt:rebuild(M)
        assert(alive(rt._root_panel),'rebuild must recover after collision removed')
        assert(rt._root_panel~=foreign,'recovered root must not be the foreign panel')
        ''')


class UnmountedRetryTests(unittest.TestCase):
    def test_unmounted_updates_bounded_tries_and_counts_script_calls(self):
        """init_finalize registers manager and fails mount (M.p=nil).
        Updates at t=0,.1,.49 are throttled to 1 script call.
        Parent restored at t=.5, one more call, root alive."""
        l = acceptance_env()
        l.execute('''
        kyohud.settings.enable_hud_foundation=true
        local rt=kyohud.hud.runtime
        local saved_p=M.p
        M.p=nil
        fire('init_finalize',M)
        local calls=0
        local orig_script=M.script
        M.script=function(self,name)
            calls=calls+1
            return orig_script(self,name)
        end
        rt:update(M,0,.016)
        rt:update(M,.1,.016)
        rt:update(M,.49,.016)
        assert(calls==1,'unmounted updates must be bounded to 1 call before restoration, got '..tostring(calls))
        M.p=saved_p
        rt:update(M,.5,.016)
        assert(calls==2,'recovery at t=0.5 must add exactly 1 script call, got '..tostring(calls))
        assert(alive(rt._root_panel),'mount must succeed once parent restored at t=0.5')
        ''')


class RedRegressionRuntimeTests(unittest.TestCase):
    def test_red_d_parent_missing_child_with_foreign_sentinel_no_create(self):
        """RED (d): parent exists, parent.panel() works, but parent.child is missing.
        A third-party sentinel named kyohud_root_panel is present on parent.
        No mount/rebuild/update path must create on this uninspectable parent."""
        lua, _ = _lua()
        lua.execute('''
            _fp = _make_parent()
            _fp.child = nil
            local foreign = _fp:panel({name = "kyohud_root_panel"})
            foreign._foreign = true
            _make_mgr(_fp)
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:mount(_G.managers.hud)
            _r1 = kyohud.hud.runtime._root_panel
            kyohud.hud.runtime:rebuild(_G.managers.hud)
            _r2 = kyohud.hud.runtime._root_panel
            kyohud.hud.runtime:update(_G.managers.hud, 10, 0.016)
            _r3 = kyohud.hud.runtime._root_panel
            _foreign_alive = foreign._foreign == true
        ''')
        g = lua.globals()
        self.assertIsNone(g._r1,
            "mount must not create root when parent.child is missing with foreign sentinel")
        self.assertIsNone(g._r2,
            "rebuild must not create root when parent.child is missing with foreign sentinel")
        self.assertIsNone(g._r3,
            "update must not create root when parent.child is missing with foreign sentinel")
        self.assertTrue(bool(g._foreign_alive),
            "foreign sentinel must remain untouched")


if __name__ == "__main__":
    unittest.main()
