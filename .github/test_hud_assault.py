"""LOT3a -- hud/assault.lua: bounded data-collection slice (RED vertical tracer).

Scope: assault state transitions and hostage snapshot ONLY. No renderer, no
visibility framework, no survived banner (survived is Holdout/skirmish ONLY,
never standard-assault). No PNR, no casing, no VIP rendering, no wave display.

Native HUDManager methods under test:
  sync_start_assault(assault_number)  :966 -> HUDAssaultCorner:sync_start_assault
  sync_end_assault(result)            :976 -> HUDAssaultCorner:sync_end_assault
  sync_assault_number(assault_number) :992 -> HUDAssaultCorner:sync_start_assault
  sync_set_assault_mode(mode)         :1004 -> HUDAssaultCorner:sync_set_assault_mode
  set_control_info(data)              :962 -> HUDAssaultCorner:set_control_info

GroupAI getters (optional native snapshot):
  get_assault_mode()                  :195 -> self._assault_mode (BOOLEAN)
  get_hunt_mode()                     :199 -> self._hunt_mode (BOOLEAN)
  get_assault_number()                :203 -> self._assault_number

Contract: kyohud.hud.assault._state = {active, number, endless, hostages}

RED state: lua/hud/assault.lua does not exist yet. Tests that depend on
the production chunk must fail with assertTrue(path.exists()), not
FileNotFoundError or skip.
"""
from pathlib import Path
import unittest
from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
ASSAULT_PATH = ROOT / "lua" / "hud" / "assault.lua"

NATIVE_ASSAULT_CORNER_FIXTURE = r'''
HUDAssaultCorner = {}
HUDAssaultCorner.__index = HUDAssaultCorner
function HUDAssaultCorner:new()
    local obj = setmetatable({}, self)
    obj._assault = false; obj._assault_mode = "normal"; obj._wave_number = 0
    obj._hostages = 0; obj._point_of_no_return = false; obj._casing = false
    obj._start_assault_after_hostage_offset = false
    return obj
end
function HUDAssaultCorner:sync_start_assault(assault_number)
    if self._point_of_no_return or self._casing then return end
    self._start_assault_after_hostage_offset = true; self._wave_number = assault_number
end
function HUDAssaultCorner:sync_end_assault(result)
    if self._point_of_no_return or self._casing then return end
    self._assault = false
end
function HUDAssaultCorner:set_control_info(data)
    if data and data.nr_hostages then self._hostages = data.nr_hostages end
end
function HUDAssaultCorner:sync_set_assault_mode(mode)
    if self._assault_mode == mode then return end
    self._assault_mode = mode
end
'''

HUDMANAGER_ASSAULT_FIXTURE = r'''
HUDManager._hud_assault_corner = nil
function HUDManager:_create_assault_corner()
    self._hud_assault_corner = HUDAssaultCorner:new()
end
function HUDManager:set_control_info(data)
    self._hud_assault_corner:set_control_info(data)
end
function HUDManager:sync_start_assault(assault_number)
    self._hud_assault_corner:sync_start_assault(assault_number)
end
function HUDManager:sync_end_assault(result)
    self._hud_assault_corner:sync_end_assault(result)
end
function HUDManager:sync_assault_number(assault_number)
    self._hud_assault_corner:sync_start_assault(assault_number)
end
function HUDManager:sync_set_assault_mode(mode)
    self._hud_assault_corner:sync_set_assault_mode(mode)
end
'''

GROUPAI_STATE_FIXTURE = r'''
GroupAIState = {}
GroupAIState.__index = GroupAIState
function GroupAIState:new()
    local obj = setmetatable({}, self)
    obj._assault_mode = false; obj._hunt_mode = false; obj._assault_number = 0
    return obj
end
function GroupAIState:get_assault_mode() return self._assault_mode end
function GroupAIState:get_hunt_mode() return self._hunt_mode end
function GroupAIState:get_assault_number() return self._assault_number end
function GroupAIState:set_assault_endless(enabled) self._hunt_mode = enabled end
managers.groupai = managers.groupai or {}
managers.groupai._state = nil
function managers.groupai:state()
    if not self._state then self._state = GroupAIState:new() end
    return self._state
end
'''

STUBS = '''
kyohud = kyohud or {}; Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end
PlayerBase = {PLAYER_INFO_HUD_PD2 = "player_info_hud_pd2"}
kyohud.settings = kyohud.settings or {}
if kyohud.settings.enable_hud_foundation == nil then kyohud.settings.enable_hud_foundation = false end
if kyohud.settings.hud_scale == nil then kyohud.settings.hud_scale = 1.0 end
kyohud.settings.enable_mission = false
if not math.round then function math.round(v) return math.floor(v + 0.5) end end
Hooks = {_all = {}}
function Hooks:PostHook(class, method, id, fn)
    table.insert(self._all, {kind="post", class=class, method=method, id=id, fn=fn})
    local orig = class[method]
    if orig then
        class[method] = function(self, ...)
            local r = {orig(self, ...)}; fn(self, ...); return unpack(r)
        end
    end
end
function Hooks:PreHook(class, method, id, fn)
    table.insert(self._all, {kind="pre", class=class, method=method, id=id, fn=fn})
    local orig = class[method]
    if orig then
        class[method] = function(self, ...)
            fn(self, ...); return orig(self, ...)
        end
    end
end
function Hooks:Add(id, event, fn) end
function log(...) end
function alive(x) return x ~= nil and x._alive ~= false end
Color = setmetatable({}, {__call = function(...) return {} end})
HUDManager = {}
HUDManager.update = function() end; HUDManager.init_finalize = function() end
HUDManager._setup_player_info_hud_pd2 = function() end
HUDManager.resolution_changed = function() end; HUDManager.destroy = function() end
managers = managers or {}; RequiredScript = "lib/managers/hudmanagerpd2"
tweak_data = tweak_data or {}; tweak_data.hud = tweak_data.hud or {}
'''

def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None

def _lua(with_assault=True, context=None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute(NATIVE_ASSAULT_CORNER_FIXTURE)
    lua.execute(HUDMANAGER_ASSAULT_FIXTURE)
    lua.execute(GROUPAI_STATE_FIXTURE)
    if context:
        lua.execute(f'RequiredScript = "{context}"')
    lua.execute("_G.managers.hud = setmetatable({_hud_assault_corner = {_assault=false, _wave_number=0, _assault_mode=\"normal\"}}, {__index = HUDManager})")
    lua.execute("_G.managers.hud:_create_assault_corner()")
    assault_src = _read(ASSAULT_PATH)
    assault_exists = assault_src is not None
    if with_assault and assault_src:
        lua.execute(assault_src)
    return lua, assault_exists

class AssaultProductionChunkTests(unittest.TestCase):
    def test_assault_file_exists_and_readable(self):
        self.assertTrue(ASSAULT_PATH.is_file(), "RED: lua/hud/assault.lua must exist")
        src = _read(ASSAULT_PATH)
        self.assertIsNotNone(src)
        self.assertGreater(len(src), 0, "RED: assault.lua must not be empty")

class AssaultStartEndTransitionTests(unittest.TestCase):
    def test_start_end_transitions(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: assault.lua must exist")
        if not ok: return
        lua.execute('''
            local mgr = _G.managers.hud; mgr:sync_start_assault(3)
            _active1 = kyohud.hud.assault._state.active
            _number1 = kyohud.hud.assault._state.number
            mgr:sync_end_assault(0); _active2 = kyohud.hud.assault._state.active
            mgr:sync_assault_number(4)
            _active3 = kyohud.hud.assault._state.active
            _number3 = kyohud.hud.assault._state.number
            mgr:sync_start_assault(5)
            _active4 = kyohud.hud.assault._state.active
            _number4 = kyohud.hud.assault._state.number
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._active1), "RED: sync_start_assault(3) must set active=true")
        self.assertEqual(g._number1, 3, "RED: sync_start_assault(3) must set number=3")
        self.assertFalse(bool(g._active2), "RED: after sync_end_assault, active must be false")
        self.assertFalse(bool(g._active3), "RED: sync_assault_number(4) must NOT set active=true (async native)")
        self.assertEqual(g._number3, 4, "RED: sync_assault_number(4) must set number=4")
        self.assertTrue(bool(g._active4), "RED: sync_start_assault(5) must set active=true")
        self.assertEqual(g._number4, 5, "RED: sync_start_assault(5) must set number=5")

class AssaultEndlessModeTests(unittest.TestCase):
    def test_endless_driven_by_hunt_mode(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: assault.lua must exist")
        if not ok: return
        lua.execute('''
            local mgr = _G.managers.hud; local state = _G.managers.groupai:state()
            state._hunt_mode = false; mgr:sync_set_assault_mode("phalanx")
            _endless1 = kyohud.hud.assault._state.endless
            state._hunt_mode = true; mgr:sync_set_assault_mode("phalanx")
            _endless2 = kyohud.hud.assault._state.endless
            state._hunt_mode = false; mgr:sync_set_assault_mode("normal")
            _endless3 = kyohud.hud.assault._state.endless
        ''')
        g = lua.globals()
        self.assertFalse(bool(g._endless1), "RED: phalanx with hunt_mode=false must NOT set endless=true")
        self.assertTrue(bool(g._endless2), "RED: phalanx with hunt_mode=true must set endless=true")
        self.assertFalse(bool(g._endless3), "RED: normal with hunt_mode=false must set endless=false")

class AssaultHostageSnapshotTests(unittest.TestCase):
    def test_hostage_capture_and_detachment(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: assault.lua must exist")
        if not ok: return
        lua.execute('''
            local mgr = _G.managers.hud; mgr:set_control_info({nr_hostages = 7})
            _count = kyohud.hud.assault._state.hostages
            local data = {nr_hostages = 5}; mgr:set_control_info(data)
            _before = kyohud.hud.assault._state.hostages
            data.nr_hostages = 99; _after = kyohud.hud.assault._state.hostages
            mgr:set_control_info({nr_hostages = 0})
            _zero = kyohud.hud.assault._state.hostages
        ''')
        g = lua.globals()
        self.assertEqual(g._count, 7, "RED: set_control_info must capture nr_hostages=7")
        self.assertEqual(g._before, 5, "RED: initial hostage count must be 5")
        self.assertEqual(g._after, 5, "RED: hostage snapshot must be detached from source mutation")
        self.assertEqual(g._zero, 0, "RED: nr_hostages=0 must be valid and stored as 0")

class AssaultStartBoundaryTests(unittest.TestCase):
    def test_start_callback_isolated_from_throwing_pnr_getter(self):
        """Registration boundary test vs integration.

        Integration path: calling mgr:sync_start_assault(3) invokes the
        wrapped method, which calls the ORIGINAL HUDAssaultCorner method
        first. The original reads corner._point_of_no_return directly
        (no pcall) and throws. The PostHook callback never executes.

        Registration boundary path: by extracting the registered PostHook
        callback (Hooks._all[].fn) and invoking it directly exactly once,
        we skip the original method entirely and test only the callback's
        engine-read boundary handling. The callback wraps getter reads in
        pcall; when _point_of_no_return throws, the callback must fail
        closed and keep _state.active = false.

        Unknown getter cannot authorize start."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: assault.lua must exist")
        if not ok: return
        lua.execute('''
            local mgr = _G.managers.hud
            local corner = mgr._hud_assault_corner
            rawset(corner, "_point_of_no_return", nil)
            assert(rawget(corner, "_point_of_no_return") == nil, "raw _point_of_no_return must be nil")
            corner._casing = false
            setmetatable(corner, {
                __index = function(t, key)
                    if key == "_point_of_no_return" then error("pnr unavailable") end
                    return HUDAssaultCorner[key]
                end
            })
            _found_cb = nil
            for _, e in ipairs(Hooks._all) do
                if e.method == "sync_start_assault" and e.kind == "post" then
                    _found_cb = e.fn
                    break
                end
            end
            assert(_found_cb ~= nil, "must find registered sync_start_assault PostHook callback")
            _before_active = kyohud.hud.assault._state.active
            _found_cb(_G.managers.hud, 3)
            _after_active = kyohud.hud.assault._state.active
        ''')
        g = lua.globals()
        self.assertFalse(bool(g._before_active), "active must start false")
        self.assertFalse(bool(g._after_active), "RED: unknown pnr getter cannot authorize start, active stays false")

class AssaultHookContextTests(unittest.TestCase):
    TARGET_METHODS = {"set_control_info", "sync_assault_number", "sync_end_assault", "sync_set_assault_mode", "sync_start_assault"}
    EXPECTED_SORTED = ["set_control_info", "sync_assault_number", "sync_end_assault", "sync_set_assault_mode", "sync_start_assault"]

    def test_hooks_only_on_hudmanager_context(self):
        lua, ok = _lua(with_assault=False)
        self.assertTrue(ok, "RED: assault.lua must exist")
        assault_src = _read(ASSAULT_PATH)
        if not assault_src:
            self.fail("RED: assault.lua must exist"); return
        lua.execute('RequiredScript = "lib/units/something_else"')
        lua.execute(assault_src)
        lua.execute('_total_wrong = #Hooks._all')
        self.assertEqual(lua.globals()._total_wrong, 0, "RED: wrong context must not register any hooks at all")
        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        lua.execute(assault_src)
        lua.execute('''
            _methods = {}
            _classes_ok = true
            _kinds_ok = true
            _total = #Hooks._all
            for _, e in ipairs(Hooks._all) do
                table.insert(_methods, e.method)
                if e.class ~= HUDManager then _classes_ok = false end
                if e.kind ~= "post" then _kinds_ok = false end
            end
            table.sort(_methods)
        ''')
        g = lua.globals()
        self.assertEqual(g._total, 5, "RED: must register exactly 5 hooks total")
        self.assertTrue(bool(g._classes_ok), "RED: all hooks must target class HUDManager")
        self.assertTrue(bool(g._kinds_ok), "RED: all hooks must be kind post")
        self.assertEqual(len(g._methods), 5, "RED: must have exactly 5 methods")
        self.assertEqual(list(g._methods.values()), self.EXPECTED_SORTED, "RED: hook methods must match expected sorted list")

class AssaultDuplicateLoadTests(unittest.TestCase):
    EXPECTED_SORTED = ["set_control_info", "sync_assault_number", "sync_end_assault", "sync_set_assault_mode", "sync_start_assault"]

    def test_double_load_no_duplicate_hooks(self):
        lua, ok = _lua(with_assault=False)
        self.assertTrue(ok, "RED: assault.lua must exist")
        assault_src = _read(ASSAULT_PATH)
        if not assault_src:
            self.fail("RED: assault.lua must exist"); return
        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        lua.execute(assault_src)
        lua.execute(assault_src)
        lua.execute('''
            _methods = {}
            _ids = {}
            _classes_ok = true
            _kinds_ok = true
            _total = #Hooks._all
            for _, e in ipairs(Hooks._all) do
                table.insert(_methods, e.method)
                table.insert(_ids, e.id)
                if e.class ~= HUDManager then _classes_ok = false end
                if e.kind ~= "post" then _kinds_ok = false end
            end
            _seen = {}; _dupes = 0
            for _, id in ipairs(_ids) do
                if _seen[id] then _dupes = _dupes + 1 end; _seen[id] = true
            end
            table.sort(_methods)
        ''')
        g = lua.globals()
        self.assertEqual(g._total, 5, "RED: exactly 5 hooks total after double load")
        self.assertTrue(bool(g._classes_ok), "RED: all hooks must target class HUDManager")
        self.assertTrue(bool(g._kinds_ok), "RED: all hooks must be kind post")
        self.assertEqual(g._dupes, 0, "RED: no duplicate hook IDs after double load")
        self.assertEqual(len(g._methods), 5, "RED: exactly 5 methods after double load")
        self.assertEqual(list(g._methods.values()), sorted(self.EXPECTED_SORTED), "RED: hook methods must match expected sorted list")

class AssaultSharedTableTests(unittest.TestCase):
    def test_shared_kyohud_table_and_state(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: assault.lua must exist")
        if not ok: return
        lua.execute('''
            _same = rawequal(kyohud, Kyosh1roHUD)
            _has_hud = (type(kyohud.hud) == "table")
            _has_assault = (type(kyohud.hud.assault) == "table")
            _state_before = kyohud.hud.assault._state
            _identity_before = tostring(_state_before)
            _state_before._test_sentinel = "SENTINEL_BEFORE"
            _sentinel_before = _state_before._test_sentinel
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._same), "RED: kyohud and Kyosh1roHUD must be same table")
        self.assertTrue(bool(g._has_hud), "RED: kyohud.hud must exist")
        self.assertTrue(bool(g._has_assault), "RED: kyohud.hud.assault must exist")
        assault_src = _read(ASSAULT_PATH)
        if assault_src:
            lua.execute(assault_src)
        lua.execute('''
            _state_after = kyohud.hud.assault._state
            _identity_after = tostring(_state_after)
            _sentinel_after = _state_after._test_sentinel
            _state_same = rawequal(_state_before, _state_after)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._state_same), "RED: _state table identity must be preserved across reload")
        self.assertEqual(g._identity_before, g._identity_after, "RED: _state tostring identity must be identical before/after reload")
        self.assertEqual(g._sentinel_after, "SENTINEL_BEFORE", "RED: _state sentinel must survive reload (same table, not replaced)")
