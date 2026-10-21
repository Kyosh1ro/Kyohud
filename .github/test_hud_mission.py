"""LOT2a -- hud/mission.lua: timer capture and display (RED vertical tracer).

Scope: time/title/secured bags. No objectives, assault, player, or crew.

The native HUDHeistTimer fixture below is extracted verbatim from
Payday-2-LuaJIT-Complete-master/lib/managers/hud/hudheisttimer.lua and
hudmanagerpd2.lua:1143-1155. It is embedded so permanent tests do not
require external G: files.

RED state: lua/hud/mission.lua does not exist yet. Tests that depend on
the production chunk must fail with an explicit message, not
FileNotFoundError.
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
MISSION_PATH = ROOT / "lua" / "hud" / "mission.lua"
LAYOUT_PATH = ROOT / "lua" / "hud" / "layout.lua"
RUNTIME_PATH = ROOT / "lua" / "hud" / "runtime.lua"
NATIVE_VIS_PATH = ROOT / "lua" / "hud" / "native_visibility.lua"

NATIVE_TIMER_FIXTURE = r'''
-- Native HUDHeistTimer fixture (verbatim logic from hud/hudheisttimer.lua).
-- Uses _timer_text primitive with :text() and :set_text() as in real native.
HUDHeistTimer = {}
HUDHeistTimer.__index = HUDHeistTimer

function HUDHeistTimer:new(tweak_hud)
    local obj = setmetatable({}, self)
    obj._last_time = 0
    obj._enabled = not (tweak_hud and tweak_hud.no_timer)
    obj._timer_text = {
        _text = "00:00",
        text = function(s) return s._text end,
        set_text = function(s, str) s._text = str end,
    }
    return obj
end

function HUDHeistTimer:set_time(time)
    local inverted = false
    if time < 0 then
        inverted = true
        time = math.abs(time)
    end
    if not self._enabled or not inverted and math.floor(time) < self._last_time then
        return
    end
    self._last_time = time
    time = math.floor(time)
    local hours = math.floor(time / 3600)
    time = time - hours * 3600
    local minutes = math.floor(time / 60)
    time = time - minutes * 60
    local seconds = math.round(time)
    local text = hours > 0 and (hours < 10 and "0" .. hours or hours) .. ":" or ""
    text = text .. (minutes < 10 and "0" .. minutes or minutes) .. ":" .. (seconds < 10 and "0" .. seconds or seconds)
    self._timer_text:set_text(text)
end

function HUDHeistTimer:modify_time(time)
    self:set_time(self._last_time + time)
end

function HUDHeistTimer:reset()
    self._last_time = 0
end

-- Test helper only; production must use _timer_text:text() directly.
function HUDHeistTimer:get_text()
    return self._timer_text:text()
end
'''

HUDMANAGER_TIMER_FIXTURE = r'''
-- HUDManager timer relay fixture (from hudmanagerpd2.lua:1143-1155).
HUDManager._hud_heist_timer = nil

function HUDManager:_create_heist_timer(tweak_hud)
    self._hud_heist_timer = HUDHeistTimer:new(tweak_hud or {})
end

function HUDManager:feed_heist_time(time)
    self._hud_heist_timer:set_time(time)
end

function HUDManager:modify_heist_time(time)
    self._hud_heist_timer:modify_time(time)
end

-- Test helper only; production must use _hud_heist_timer._timer_text:text().
function HUDManager:get_native_timer_text()
    if self._hud_heist_timer then
        return self._hud_heist_timer._timer_text:text()
    end
    return nil
end
'''

LOOTMANAGER_FIXTURE = r'''
-- LootManager fixture matching native source shapes.
-- sync_secure_loot: inserts secured then calls managers.hud:loot_value_updated().
-- sync_load: replaces _global only, no HUD notification.
-- get_secured_bags_amount: strict native loop (no nil guard on carry).
LootManager = {}
LootManager.__index = LootManager

function LootManager:new()
    local obj = setmetatable({}, self)
    obj._global = {secured = {}}
    return obj
end

function LootManager:get_secured_bags_amount(is_vehicle)
    local amount = 0
    for _, data in ipairs(self._global.secured) do
        if not tweak_data.carry.small_loot[data.carry_id] and not tweak_data.carry[data.carry_id].is_vehicle == not is_vehicle then
            amount = amount + 1
        end
    end
    return amount
end

function LootManager:sync_secure_loot(carry_id, multiplier_level, silent, peer_id)
    if peer_id == 0 then
        peer_id = nil
    end
    local multiplier = 1
    table.insert(self._global.secured, {
        carry_id = carry_id,
        multiplier = multiplier,
        peer_id = peer_id
    })
    managers.hud:loot_value_updated()
end

function LootManager:sync_load(data)
    self._global = data.LootManager
    Global.loot_manager = self._global
    for _, entry in ipairs(self._global.secured) do
        if entry.multiplier and entry.multiplier > 2 then
            entry.multiplier = 2
        end
    end
end

Global = Global or {}
managers.loot = LootManager:new()
'''

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
kyohud.settings.enable_mission = false

if not math.round then
    function math.round(v) return math.floor(v + 0.5) end
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
HUDManager.loot_value_updated = function() end

managers = {}
PlayerBase = {
    PLAYER_INFO_HUD_PD2 = "player_info_hud_pd2",
    PLAYER_INFO_HUD_FULLSCREEN_PD2 = "player_info_hud_fullscreen_pd2",
}
RequiredScript = "lib/managers/hudmanagerpd2"

tweak_data = tweak_data or {}
tweak_data.hud = tweak_data.hud or {}
if tweak_data.hud.medium_font_noshadow == nil then
    tweak_data.hud.medium_font_noshadow = "fonts/font_medium_mf"
end
tweak_data.carry = tweak_data.carry or {small_loot = {}}

_fake_time = 0
function _advance_time(dt) _fake_time = _fake_time + (dt or 0) end
function _get_time() return _fake_time end
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
    function p:text(opts)
        local t = _make_panel(opts and opts.name)
        t._text = opts and opts.text or ""
        t._font = opts and opts.font
        function t:set_text(str) self._text = str end
        function t:text() return self._text end
        return t
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
    _G.managers.hud = setmetatable({
        script = function(self, name) return safe end,
        disabled = function() return false end,
    }, {__index = HUDManager})
    return safe
end

function _count_children(p)
    if not p then return 0 end
    local n = 0
    for _ in pairs(p._children) do n = n + 1 end
    return n
end

function _kill_panel_tree(p)
    if not p then return end
    p._alive = false
    for _, ch in pairs(p._children or {}) do
        _kill_panel_tree(ch)
    end
end
'''


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua(with_mission=True, context=None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute(DIESEL)
    lua.execute(NATIVE_TIMER_FIXTURE)
    lua.execute(HUDMANAGER_TIMER_FIXTURE)
    if context:
        lua.execute(f'RequiredScript = "{context}"')
    lua.execute("_init_fp = _make_parent(); _make_mgr(_init_fp)")
    layout_src = _read(LAYOUT_PATH)
    if layout_src:
        lua.execute(layout_src)
    rt_src = _read(RUNTIME_PATH)
    if rt_src:
        lua.execute(rt_src)
    nv_src = _read(NATIVE_VIS_PATH)
    if nv_src:
        lua.execute(nv_src)
    mission_src = _read(MISSION_PATH)
    mission_exists = mission_src is not None
    if with_mission and mission_src:
        lua.execute(mission_src)
    return lua, mission_exists


def _load_mission_src(lua):
    src = _read(MISSION_PATH)
    if src:
        lua.execute(src)
    return src is not None


class NativeTimerFixtureTests(unittest.TestCase):
    """Validate the embedded HUDHeistTimer fixture matches native behavior.

    These tests are GREEN: they verify the fixture logic itself, serving
    as reference for what mission.lua must preserve when copying text.
    """

    def test_fixture_monotone_guard_rejects_backwards(self):
        lua, _ = _lua(with_mission=False)
        lua.execute('''
            local t = HUDHeistTimer:new({})
            t:set_time(100)
            t:set_time(50)
            _text = t._timer_text:text()
        ''')
        self.assertEqual(lua.globals()._text, "01:40",
            "native monotone guard: set_time(50) after set_time(100) must keep 01:40")

    def test_fixture_forward_progress(self):
        lua, _ = _lua(with_mission=False)
        lua.execute('''
            local t = HUDHeistTimer:new({})
            t:set_time(10)
            t:set_time(20)
            t:set_time(30)
            _text = t._timer_text:text()
        ''')
        self.assertEqual(lua.globals()._text, "00:30")

    def test_fixture_inverted_negative_input(self):
        lua, _ = _lua(with_mission=False)
        lua.execute('''
            local t = HUDHeistTimer:new({})
            t:set_time(-300)
            _text = t._timer_text:text()
            _last = t._last_time
        ''')
        g = lua.globals()
        self.assertEqual(g._text, "05:00",
            "inverted input: abs value formatted")
        self.assertAlmostEqual(float(g._last), 300.0, places=1)

    def test_fixture_inverted_bypasses_monotone_guard(self):
        lua, _ = _lua(with_mission=False)
        lua.execute('''
            local t = HUDHeistTimer:new({})
            t:set_time(100)
            t:set_time(-50)
            _text = t._timer_text:text()
        ''')
        self.assertEqual(lua.globals()._text, "00:50",
            "inverted must bypass monotone guard")

    def test_fixture_hours_format(self):
        lua, _ = _lua(with_mission=False)
        lua.execute('''
            local t = HUDHeistTimer:new({})
            t:set_time(3661)
            _text = t._timer_text:text()
        ''')
        self.assertEqual(lua.globals()._text, "01:01:01",
            "hours > 0 must include zero-padded hour prefix")

    def test_fixture_hours_large(self):
        lua, _ = _lua(with_mission=False)
        lua.execute('''
            local t = HUDHeistTimer:new({})
            t:set_time(36000)
            _text = t._timer_text:text()
        ''')
        self.assertEqual(lua.globals()._text, "10:00:00",
            "two-digit hours")

    def test_fixture_modify_time_adds_delta(self):
        lua, _ = _lua(with_mission=False)
        lua.execute('''
            local t = HUDHeistTimer:new({})
            t:set_time(60)
            t:modify_time(30)
            _text = t._timer_text:text()
            _last = t._last_time
        ''')
        g = lua.globals()
        self.assertEqual(g._text, "01:30")
        self.assertAlmostEqual(float(g._last), 90.0, places=1)

    def test_fixture_modify_time_negative_delta_rejected_by_monotone(self):
        """modify_time(-30) after set_time(100): 100+(-30)=70 < 100,
        monotone guard rejects. Text remains 01:40, NOT 01:10."""
        lua, _ = _lua(with_mission=False)
        lua.execute('''
            local t = HUDHeistTimer:new({})
            t:set_time(100)
            t:modify_time(-30)
            _text = t._timer_text:text()
            _last = t._last_time
        ''')
        g = lua.globals()
        self.assertEqual(g._text, "01:40",
            "negative modify rejected by monotone guard: text stays at pre-modify value")
        self.assertAlmostEqual(float(g._last), 100.0, places=1,
            msg="_last_time must remain at pre-modify value when guard rejects")

    def test_fixture_no_timer_disables_updates(self):
        lua, _ = _lua(with_mission=False)
        lua.execute('''
            local t = HUDHeistTimer:new({no_timer = true})
            t:set_time(100)
            _text = t._timer_text:text()
        ''')
        self.assertEqual(lua.globals()._text, "00:00",
            "no_timer must suppress set_time updates")

    def test_fixture_reset_clears_last_time_not_text(self):
        """Native reset() only resets _last_time; _timer_text keeps its value."""
        lua, _ = _lua(with_mission=False)
        lua.execute('''
            local t = HUDHeistTimer:new({})
            t:set_time(100)
            t:reset()
            _last = t._last_time
            _text = t._timer_text:text()
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._last), 0.0, places=1)
        self.assertEqual(g._text, "01:40",
            "reset only resets _last_time; _timer_text retains previous value")

    def test_fixture_hudmanager_relay(self):
        lua, _ = _lua(with_mission=False)
        lua.execute('''
            _G.managers.hud:_create_heist_timer({})
            _G.managers.hud:feed_heist_time(125)
            _text = _G.managers.hud._hud_heist_timer._timer_text:text()
        ''')
        self.assertEqual(lua.globals()._text, "02:05",
            "HUDManager:feed_heist_time must relay to HUDHeistTimer")

    def test_fixture_hudmanager_modify_relay(self):
        lua, _ = _lua(with_mission=False)
        lua.execute('''
            _G.managers.hud:_create_heist_timer({})
            _G.managers.hud:feed_heist_time(60)
            _G.managers.hud:modify_heist_time(45)
            _text = _G.managers.hud._hud_heist_timer._timer_text:text()
        ''')
        self.assertEqual(lua.globals()._text, "01:45",
            "HUDManager:modify_heist_time must forward last_time+delta")

    def test_fixture_hudmanager_no_timer_source_returns_nil(self):
        lua, _ = _lua(with_mission=False)
        lua.execute('''
            _text = _G.managers.hud:get_native_timer_text()
        ''')
        self.assertIsNone(lua.globals()._text,
            "before _create_heist_timer, native text must be nil")

    def test_fixture_timer_text_identity_stable(self):
        """The _timer_text primitive object must remain the same across set_time calls."""
        lua, _ = _lua(with_mission=False)
        lua.execute('''
            local t = HUDHeistTimer:new({})
            _ref1 = t._timer_text
            t:set_time(42)
            _ref2 = t._timer_text
            t:set_time(99)
            _ref3 = t._timer_text
            _same = (rawequal(_ref1, _ref2) and rawequal(_ref2, _ref3))
        ''')
        self.assertTrue(bool(lua.globals()._same),
            "_timer_text primitive identity must be stable across set_time calls")


class MissionProductionChunkTests(unittest.TestCase):
    """RED: lua/hud/mission.lua must exist as a production chunk."""

    def test_mission_file_exists(self):
        self.assertTrue(
            MISSION_PATH.is_file(),
            "RED: lua/hud/mission.lua must exist (production chunk missing)",
        )

    def test_mission_source_readable(self):
        if not MISSION_PATH.is_file():
            self.fail("RED: lua/hud/mission.lua not found")
        src = _read(MISSION_PATH)
        self.assertIsNotNone(src)
        self.assertGreater(len(src), 0,
            "RED: mission.lua must not be empty")


class MissionNamespaceTests(unittest.TestCase):
    """RED: kyohud.hud.mission must exist with expected interface."""

    def test_mission_table_exists(self):
        lua, ok = _lua()
        self.assertTrue(ok,
            "RED: mission.lua must exist to define kyohud.hud.mission")
        if not ok:
            return
        lua.execute("assert(type(kyohud.hud.mission) == 'table', 'kyohud.hud.mission must be table')")

    def test_mission_alias_consistency(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute("assert(rawequal(kyohud, Kyosh1roHUD))")

    def test_mission_lifecycle_methods(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            local M = kyohud.hud.mission
            for _, n in ipairs{"mount","unmount","rebuild","refresh_settings",
                "on_heist_start","destroy","update"} do
                assert(type(M[n]) == "function", n .. " must be function")
            end
        ''')


class MissionTimerCallbackCaptureTests(unittest.TestCase):
    """RED: timer text captured through registered HUDManager callbacks.

    mission.lua must install PostHooks on feed_heist_time and
    modify_heist_time. After native set_time runs, the accepted text
    must be copied into kyohud.hud.mission._timer_text.
    """

    def test_hooks_registered_on_hudmanager(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            _timer_hooks = {}
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" or e.method == "modify_heist_time"
                    or e.method == "_create_heist_timer" then
                    table.insert(_timer_hooks, e.method)
                end
            end
            _count = #_timer_hooks
        ''')
        self.assertGreaterEqual(lua.globals()._count, 2,
            "RED: mission must register hooks on feed_heist_time and modify_heist_time")

    def test_feed_heist_time_captures_text(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            _G.managers.hud:_create_heist_timer({})
            local mgr = _G.managers.hud
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then
                    mgr:feed_heist_time(125)
                    e.fn(mgr, 125)
                end
            end
            _text = kyohud.hud.mission._timer_text
        ''')
        self.assertEqual(lua.globals()._text, "02:05",
            "RED: feed_heist_time callback must copy native '02:05'")

    def test_modify_heist_time_captures_text(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            _G.managers.hud:_create_heist_timer({})
            local mgr = _G.managers.hud
            mgr:feed_heist_time(60)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 60) end
            end
            mgr:modify_heist_time(45)
            for _, e in ipairs(Hooks._all) do
                if e.method == "modify_heist_time" then e.fn(mgr, 45) end
            end
            _text = kyohud.hud.mission._timer_text
        ''')
        self.assertEqual(lua.globals()._text, "01:45",
            "RED: modify_heist_time must copy native '01:45' (60+45=105)")

    def test_copied_not_recomputed(self):
        """mission must copy the native formatted string, not compute its own."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            _G.managers.hud:_create_heist_timer({})
            local mgr = _G.managers.hud
            mgr:feed_heist_time(3661)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 3661) end
            end
            _text = kyohud.hud.mission._timer_text
            _native = mgr._hud_heist_timer._timer_text:text()
        ''')
        g = lua.globals()
        self.assertEqual(g._text, g._native,
            "RED: mission text must equal native text (copy, not recompute)")
        self.assertEqual(g._text, "01:01:01")


class MissionTimerEdgeCaseTests(unittest.TestCase):
    """RED: stopped timer, inverted, >hour, source absence."""

    def test_stopped_timer_keeps_last_text(self):
        """After feed stops and update is called with advanced clock,
        mission._timer_text retains the last accepted string.
        Uses actual native getter on _timer_text primitive."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            _G.managers.hud:_create_heist_timer({})
            local mgr = _G.managers.hud
            mgr:feed_heist_time(200)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 200) end
            end
            _text_frozen = kyohud.hud.mission._timer_text
            _native_frozen = mgr._hud_heist_timer._timer_text:text()
            _advance_time(60)
            if type(kyohud.hud.mission.update) == "function" then
                kyohud.hud.mission:update(mgr, _get_time(), 60)
            end
            _text_after_update = kyohud.hud.mission._timer_text
        ''')
        g = lua.globals()
        self.assertEqual(g._text_frozen, "03:20",
            "RED: frozen text must be '03:20'")
        self.assertEqual(g._native_frozen, "03:20",
            "native _timer_text:text() must also be '03:20'")
        self.assertEqual(g._text_after_update, "03:20",
            "RED: after update with advanced clock and no new feed, text stays frozen")

    def test_inverted_timer_text_preserved(self):
        """Negative native input -> inverted display; mission must copy it."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            _G.managers.hud:_create_heist_timer({})
            local mgr = _G.managers.hud
            mgr:feed_heist_time(-600)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, -600) end
            end
            _text = kyohud.hud.mission._timer_text
        ''')
        self.assertEqual(lua.globals()._text, "10:00",
            "RED: inverted timer text must be copied as '10:00'")

    def test_over_hour_text_preserved(self):
        """>3600 seconds: native formats with zero-padded hour prefix; mission must copy."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            _G.managers.hud:_create_heist_timer({})
            local mgr = _G.managers.hud
            mgr:feed_heist_time(7200)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 7200) end
            end
            _text = kyohud.hud.mission._timer_text
        ''')
        self.assertEqual(lua.globals()._text, "02:00:00",
            "RED: >hour text must be '02:00:00' (zero-padded)")

    def test_source_absence_is_unknown_not_zero(self):
        """When native timer source is absent (no _create_heist_timer called),
        mission._timer_text must be nil, not '00:00' or 0."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            _text = kyohud.hud.mission._timer_text
            _known = kyohud.hud.mission._timer_known
        ''')
        g = lua.globals()
        self.assertIsNone(g._text,
            "RED: source absence must leave _timer_text nil (unknown)")
        self.assertFalse(bool(g._known),
            "RED: source absence must leave _timer_known false")


class MissionPreMountCaptureTests(unittest.TestCase):
    """RED: timer events captured before mounting."""

    def test_feed_before_mount_captures_text(self):
        """Timer feed callback must capture text even when mission is not mounted."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            _G.managers.hud:_create_heist_timer({})
            local mgr = _G.managers.hud
            mgr:feed_heist_time(90)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 90) end
            end
            _text = kyohud.hud.mission._timer_text
            _mounted = kyohud.hud.mission._mounted
        ''')
        g = lua.globals()
        self.assertEqual(g._text, "01:30",
            "RED: pre-mount feed must capture '01:30'")
        self.assertFalse(bool(g._mounted),
            "capture must work without mounting")

    def test_modify_before_mount_captures_text(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            _G.managers.hud:_create_heist_timer({})
            local mgr = _G.managers.hud
            mgr:feed_heist_time(100)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 100) end
            end
            mgr:modify_heist_time(50)
            for _, e in ipairs(Hooks._all) do
                if e.method == "modify_heist_time" then e.fn(mgr, 50) end
            end
            _text = kyohud.hud.mission._timer_text
        ''')
        self.assertEqual(lua.globals()._text, "02:30",
            "RED: pre-mount modify must capture '02:30' (100+50=150)")


class MissionPersistentDisplayTests(unittest.TestCase):
    """RED: when enabled, timer text displayed via persistent owned primitives."""

    def test_enabled_option_shows_captured_text(self):
        """When enable_mission is true and mounted, the captured timer text
        must be available for display via owned primitives."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_mission = true
            _G.managers.hud:_create_heist_timer({})
            local mgr = _G.managers.hud
            mgr:feed_heist_time(45)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 45) end
            end
            _text = kyohud.hud.mission._timer_text
            _known = kyohud.hud.mission._timer_known
        ''')
        g = lua.globals()
        self.assertEqual(g._text, "00:45",
            "RED: enabled mission must have captured '00:45'")
        self.assertTrue(bool(g._known),
            "RED: after feed, _timer_known must be true")

    def test_disabled_option_no_display(self):
        """When enable_mission is false, no timer display is created."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_mission = false
            kyohud.hud.mission:mount(_G.managers.hud)
            _r = kyohud.hud.mission._root_panel
        ''')
        self.assertIsNone(lua.globals()._r,
            "RED: disabled mission must not create a root panel")

    def test_persistent_display_owns_text_primitive(self):
        """With foundation+enable_mission enabled, mount runtime and mission.
        Feed timer values. Assert actual owned text primitive holds captured
        text. Identity and creation count remain stable across feeds.
        No native-parent structure mutation."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true

            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud

            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)

            _root = kyohud.hud.mission._root_panel
            _native_children_before = _count_children(fp)

            mgr:_create_heist_timer({})
            mgr:feed_heist_time(125)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 125) end
            end

            _text1 = kyohud.hud.mission._timer_text
            _prim1 = kyohud.hud.mission._timer_prim

            mgr:feed_heist_time(200)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 200) end
            end

            _text2 = kyohud.hud.mission._timer_text
            _prim2 = kyohud.hud.mission._timer_prim

            _native_children_after = _count_children(fp)
            _same_prim = rawequal(_prim1, _prim2)
            _prim_text = _prim1 and _prim1:text() or nil
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._root,
            "RED: enabled+mounted mission must create root panel")
        self.assertEqual(g._text1, "02:05")
        self.assertEqual(g._text2, "03:20")
        self.assertIsNotNone(g._prim1,
            "RED: mission must create owned text primitive for timer display")
        self.assertTrue(bool(g._same_prim),
            "RED: text primitive identity must remain stable across feeds")
        self.assertEqual(g._prim_text, "03:20",
            "RED: owned text primitive must hold latest captured text")
        self.assertEqual(g._native_children_before, g._native_children_after,
            "RED: mission must not mutate native parent children count")


class MissionHookContextTests(unittest.TestCase):
    """RED: mission hooks only install under correct RequiredScript."""

    def test_hooks_only_on_hudmanager_context(self):
        """Load mission with wrong RequiredScript: no timer hooks.
        Load with correct RequiredScript: hooks appear, no duplicate IDs."""
        lua, ok = _lua(with_mission=False)
        self.assertTrue(ok, "RED: mission.lua must exist")
        mission_src = _read(MISSION_PATH)
        if not mission_src:
            self.fail("RED: mission.lua must exist")
            return

        lua.execute('RequiredScript = "lib/units/something_else"')
        lua.execute(mission_src)
        lua.execute('''
            _wrong_hooks = 0
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" or e.method == "modify_heist_time"
                    or e.method == "_create_heist_timer" then
                    _wrong_hooks = _wrong_hooks + 1
                end
            end
        ''')
        self.assertEqual(lua.globals()._wrong_hooks, 0,
            "RED: wrong RequiredScript must not register mission timer hooks")

        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        lua.execute(mission_src)
        lua.execute('''
            _timer_ids = {}
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" or e.method == "modify_heist_time"
                    or e.method == "_create_heist_timer" then
                    table.insert(_timer_ids, e.id)
                end
            end
            _count = #_timer_ids
            _seen = {}
            _dupes = 0
            for _, id in ipairs(_timer_ids) do
                if _seen[id] then _dupes = _dupes + 1 end
                _seen[id] = true
            end
            _bad_class = 0
            for _, e in ipairs(Hooks._all) do
                if (e.method == "feed_heist_time" or e.method == "modify_heist_time"
                    or e.method == "_create_heist_timer")
                    and e.class ~= HUDManager then
                    _bad_class = _bad_class + 1
                end
            end
        ''')
        g = lua.globals()
        self.assertGreaterEqual(g._count, 2,
            "RED: must register at least 2 hooks")
        self.assertEqual(g._dupes, 0,
            "RED: no duplicate hooks")
        self.assertEqual(g._bad_class, 0,
            "RED: mission timer hooks must target HUDManager only")


class MissionNoRecomputeTests(unittest.TestCase):
    """RED: mission must never derive its own chrono from elapsed time."""

    def test_no_independent_chrono_after_stop(self):
        """After native stops feeding, mission text must stay frozen at
        last accepted value, not advance from any internal clock.
        Invoke update after advancing fake Application clock."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            _G.managers.hud:_create_heist_timer({})
            local mgr = _G.managers.hud
            mgr:feed_heist_time(300)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 300) end
            end
            _text_before = kyohud.hud.mission._timer_text
            _native_before = mgr._hud_heist_timer._timer_text:text()

            _advance_time(120)
            if type(kyohud.hud.mission.update) == "function" then
                kyohud.hud.mission:update(mgr, _get_time(), 120)
            end

            _text_after = kyohud.hud.mission._timer_text
            _native_after = mgr._hud_heist_timer._timer_text:text()
        ''')
        g = lua.globals()
        self.assertEqual(g._text_before, "05:00")
        self.assertEqual(g._native_before, "05:00")
        self.assertEqual(g._text_after, "05:00",
            "RED: text must remain frozen after update with no new feed")
        self.assertEqual(g._native_after, "05:00",
            "native _timer_text:text() also remains '05:00' (no new set_time)")
        self.assertEqual(g._text_before, g._text_after,
            "RED: no internal recomputation allowed")



class MissionTitleTests(unittest.TestCase):
    """RED: mission title resolution with explicit fallbacks.

    Title = JobManager:current_level_id() -> tweak_data.levels[id].name_id ->
    managers.localization:text(name_id). Fallback: ky_hud_mission_title
    (HEIST IN PROGRESS / BRAQUAGE EN COURS). Unknown -> nil, not empty string.
    """

    def _assert_resolve_title_exists(self, lua):
        lua.execute('''
            _has_resolve_title = (type(kyohud.hud.mission._resolve_title) == "function")
        ''')
        self.assertTrue(bool(lua.globals()._has_resolve_title),
            "RED: _resolve_title method must exist on mission table")

    def test_title_missing_job_returns_nil(self):
        """When JobManager or current_level_id is missing, title must be nil."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        self._assert_resolve_title_exists(lua)
        lua.execute('''
            _title = kyohud.hud.mission:_resolve_title()
        ''')
        self.assertIsNone(lua.globals()._title,
            "RED: missing job must yield nil title (unknown)")

    def test_title_missing_tweak_data_returns_nil(self):
        """When tweak_data.levels[id] is missing, title must be nil."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        self._assert_resolve_title_exists(lua)
        lua.execute('''
            managers.job = {current_level_id = function() return "nonexistent_level" end}
            tweak_data = {levels = {}, hud = {medium_font_noshadow = "fonts/font_medium_mf"}, carry = {small_loot = {}}}
            _title = kyohud.hud.mission:_resolve_title()
        ''')
        self.assertIsNone(lua.globals()._title,
            "RED: missing tweak_data entry must yield nil title")

    def test_title_missing_name_id_returns_nil(self):
        """When level data lacks name_id, title must be nil."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        self._assert_resolve_title_exists(lua)
        lua.execute('''
            managers.job = {current_level_id = function() return "firestarter_1" end}
            tweak_data = {levels = {firestarter_1 = {}}, hud = {medium_font_noshadow = "fonts/font_medium_mf"}, carry = {small_loot = {}}}
            _title = kyohud.hud.mission:_resolve_title()
        ''')
        self.assertIsNone(lua.globals()._title,
            "RED: missing name_id must yield nil title")

    def test_title_missing_localization_returns_nil(self):
        """When managers.localization is missing, title must be nil."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        self._assert_resolve_title_exists(lua)
        lua.execute('''
            managers.job = {current_level_id = function() return "firestarter_1" end}
            tweak_data = {levels = {firestarter_1 = {name_id = "heist_firestarter"}}, hud = {medium_font_noshadow = "fonts/font_medium_mf"}, carry = {small_loot = {}}}
            _title = kyohud.hud.mission:_resolve_title()
        ''')
        self.assertIsNone(lua.globals()._title,
            "RED: missing localization manager must yield nil title")

    def test_title_localization_throws_returns_nil(self):
        """When localization:text() throws, title must be nil."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        self._assert_resolve_title_exists(lua)
        lua.execute('''
            managers.job = {current_level_id = function() return "firestarter_1" end}
            tweak_data = {levels = {firestarter_1 = {name_id = "heist_firestarter"}}, hud = {medium_font_noshadow = "fonts/font_medium_mf"}, carry = {small_loot = {}}}
            managers.localization = {text = function() error("broken") end}
            _title = kyohud.hud.mission:_resolve_title()
        ''')
        self.assertIsNone(lua.globals()._title,
            "RED: throwing localization must yield nil title (fail closed)")

    def test_title_valid_chain_captures_text(self):
        """Valid job/tweak/localization chain must capture the title."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        self._assert_resolve_title_exists(lua)
        lua.execute('''
            managers.job = {current_level_id = function() return "firestarter_1" end}
            tweak_data = {levels = {firestarter_1 = {name_id = "heist_firestarter"}}, hud = {medium_font_noshadow = "fonts/font_medium_mf"}, carry = {small_loot = {}}}
            managers.localization = {text = function(self, id) return "Firestarter" end}
            _title = kyohud.hud.mission:_resolve_title()
        ''')
        self.assertEqual(lua.globals()._title, "Firestarter",
            "RED: valid chain must capture title text")

    def test_title_with_interruption(self):
        """current_level_id() includes interruption; title must reflect it."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        self._assert_resolve_title_exists(lua)
        lua.execute('''
            managers.job = {
                current_level_id = function(self)
                    if self._global and self._global.interupt_stage then
                        return self._global.interupt_stage
                    end
                    return "firestarter_1"
                end,
                _global = {interupt_stage = "firestarter_2"}
            }
            tweak_data = {
                levels = {
                    firestarter_1 = {name_id = "heist_firestarter_1"},
                    firestarter_2 = {name_id = "heist_firestarter_2"}
                },
                hud = {medium_font_noshadow = "fonts/font_medium_mf"},
                carry = {small_loot = {}}
            }
            managers.localization = {text = function(self, id)
                if id == "heist_firestarter_2" then return "Firestarter Day 2 (Interrupt)" end
                return "Firestarter Day 1"
            end}
            _title = kyohud.hud.mission:_resolve_title()
        ''')
        self.assertEqual(lua.globals()._title, "Firestarter Day 2 (Interrupt)",
            "RED: title must reflect interrupted level_id")

    def test_title_late_job_recovery_through_update(self):
        """When job becomes ready later, bounded update must recover title.
        Recovery goes through update(), not direct resolver call."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        self._assert_resolve_title_exists(lua)
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)

            _title_before = kyohud.hud.mission:_resolve_title()

            managers.job = {current_level_id = function() return "firestarter_1" end}
            tweak_data.levels = {firestarter_1 = {name_id = "heist_firestarter"}}
            tweak_data.hud = {medium_font_noshadow = "fonts/font_medium_mf"}
            managers.localization = {text = function() return "Firestarter" end}

            _advance_time(1.0)
            if type(kyohud.hud.mission.update) == "function" then
                kyohud.hud.mission:update(mgr, _get_time(), 1.0)
            end
            _title_after_update = kyohud.hud.mission:_resolve_title()
        ''')
        g = lua.globals()
        self.assertIsNone(g._title_before, "RED: before job ready, title must be nil")
        self.assertEqual(g._title_after_update, "Firestarter",
            "RED: after update with job ready, title must be recovered")

    def test_title_fallback_when_resolver_returns_nil(self):
        """When _resolve_title returns nil, displayed title falls back to
        HEIST IN PROGRESS / BRAQUAGE EN COURS (ky_hud_mission_title)."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        self._assert_resolve_title_exists(lua)
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)

            _resolved = kyohud.hud.mission:_resolve_title()
            _displayed = kyohud.hud.mission._title_text
            _has_fallback = (_displayed ~= nil and _displayed ~= "")
        ''')
        g = lua.globals()
        self.assertIsNone(g._resolved,
            "RED: without job, resolver must return nil")
        self.assertTrue(bool(g._has_fallback),
            "RED: displayed title must fall back to HEIST IN PROGRESS / BRAQUAGE EN COURS when resolver returns nil")


class MissionBagsTests(unittest.TestCase):
    """RED: absolute bags count from LootManager:get_secured_bags_amount(false).

    Counts all secured minus small_loot and vehicles. Unknown source -> nil,
    not 0. sync_load replaces registry with no HUD notification.
    """

    def _assert_resolve_bags_exists(self, lua):
        lua.execute('''
            _has_resolve_bags = (type(kyohud.hud.mission._resolve_bags) == "function")
        ''')
        self.assertTrue(bool(lua.globals()._has_resolve_bags),
            "RED: _resolve_bags method must exist on mission table")

    def _standard_carry_tweak(self):
        return '''
            tweak_data = tweak_data or {}
            tweak_data.carry = {
                small_loot = {},
                gold = {is_vehicle = false},
                cash = {is_vehicle = false},
                diamond = {is_vehicle = false},
                artwork = {is_vehicle = false},
                van = {is_vehicle = true}
            }
            tweak_data.hud = {medium_font_noshadow = "fonts/font_medium_mf"}
        '''

    def test_bags_missing_source_establishes_positive_then_removes(self):
        """First establish a known positive count, then remove LootManager
        and invoke callback. Assert bags go to nil (not vacuously from nil)."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        self._assert_resolve_bags_exists(lua)
        lua.execute(self._standard_carry_tweak())
        lua.execute('''
            _bags_default = kyohud.hud.mission._bags_count

            managers.loot = {
                _global = {secured = {
                    {carry_id = "gold"},
                    {carry_id = "gold"},
                    {carry_id = "gold"}
                }}
            }
            function managers.loot:get_secured_bags_amount(is_vehicle)
                local amount = 0
                for _, data in ipairs(self._global.secured) do
                    local carry = tweak_data.carry[data.carry_id]
                    if carry and not tweak_data.carry.small_loot[data.carry_id]
                       and (not carry.is_vehicle) == (not is_vehicle) then
                        amount = amount + 1
                    end
                end
                return amount
            end
            _count_positive = kyohud.hud.mission:_resolve_bags()
        ''')
        self.assertIsNone(lua.globals()._bags_default,
            "RED: default _bags_count must be nil (unknown), not invented 0")
        self.assertEqual(lua.globals()._count_positive, 3,
            "RED: positive baseline must be 3 bags")

        lua.execute('''
            managers.loot = nil
            _count_after_remove = kyohud.hud.mission:_resolve_bags()
            _known_after_remove = kyohud.hud.mission._bags_known
        ''')
        g = lua.globals()
        self.assertIsNone(g._count_after_remove,
            "RED: after removing LootManager, bags must be nil (unknown)")
        self.assertFalse(bool(g._known_after_remove),
            "RED: after removing LootManager, _bags_known must be false")

    def test_bags_getter_throws_establishes_positive_then_throws(self):
        """First establish a known positive count, then make getter throw.
        Assert bags go to nil (not vacuously from nil)."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        self._assert_resolve_bags_exists(lua)
        lua.execute(self._standard_carry_tweak())
        lua.execute('''
            managers.loot = {
                _global = {secured = {
                    {carry_id = "gold"},
                    {carry_id = "diamond"}
                }}
            }
            function managers.loot:get_secured_bags_amount(is_vehicle)
                local amount = 0
                for _, data in ipairs(self._global.secured) do
                    local carry = tweak_data.carry[data.carry_id]
                    if carry and not tweak_data.carry.small_loot[data.carry_id]
                       and (not carry.is_vehicle) == (not is_vehicle) then
                        amount = amount + 1
                    end
                end
                return amount
            end
            _count_positive = kyohud.hud.mission:_resolve_bags()
        ''')
        self.assertEqual(lua.globals()._count_positive, 2,
            "RED: positive baseline must be 2 bags")

        lua.execute('''
            function managers.loot:get_secured_bags_amount(is_vehicle)
                error("broken")
            end
            _count_after_throw = kyohud.hud.mission:_resolve_bags()
            _known_after_throw = kyohud.hud.mission._bags_known
        ''')
        g = lua.globals()
        self.assertIsNone(g._count_after_throw,
            "RED: after getter throws, bags must be nil (fail closed)")
        self.assertFalse(bool(g._known_after_throw),
            "RED: after getter throws, _bags_known must be false")

    def test_bags_excludes_small_loot(self):
        """get_secured_bags_amount(false) excludes small_loot.
        Fixture: gold, cash (small_loot), gold -> 2 non-small bags."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        self._assert_resolve_bags_exists(lua)
        lua.execute('''
            tweak_data = {
                carry = {
                    small_loot = {cash = true},
                    gold = {is_vehicle = false},
                    cash = {is_vehicle = false}
                },
                hud = {medium_font_noshadow = "fonts/font_medium_mf"}
            }
            managers.loot = {
                _global = {secured = {
                    {carry_id = "gold"},
                    {carry_id = "cash"},
                    {carry_id = "gold"}
                }}
            }
            function managers.loot:get_secured_bags_amount(is_vehicle)
                local amount = 0
                for _, data in ipairs(self._global.secured) do
                    if not tweak_data.carry.small_loot[data.carry_id]
                       and not tweak_data.carry[data.carry_id].is_vehicle == not is_vehicle then
                        amount = amount + 1
                    end
                end
                return amount
            end
            _count = kyohud.hud.mission:_resolve_bags()
        ''')
        self.assertEqual(lua.globals()._count, 2,
            "RED: bags must exclude small_loot (2 gold, cash excluded)")

    def test_bags_excludes_vehicles(self):
        """get_secured_bags_amount(false) excludes vehicles."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        self._assert_resolve_bags_exists(lua)
        lua.execute('''
            tweak_data = {
                carry = {
                    small_loot = {},
                    gold = {is_vehicle = false},
                    van = {is_vehicle = true}
                },
                hud = {medium_font_noshadow = "fonts/font_medium_mf"}
            }
            managers.loot = {
                _global = {secured = {
                    {carry_id = "gold"},
                    {carry_id = "van"},
                    {carry_id = "gold"}
                }}
            }
            function managers.loot:get_secured_bags_amount(is_vehicle)
                local amount = 0
                for _, data in ipairs(self._global.secured) do
                    if not tweak_data.carry.small_loot[data.carry_id]
                       and not tweak_data.carry[data.carry_id].is_vehicle == not is_vehicle then
                        amount = amount + 1
                    end
                end
                return amount
            end
            _count = kyohud.hud.mission:_resolve_bags()
        ''')
        self.assertEqual(lua.globals()._count, 2,
            "RED: bags must exclude vehicles (2 gold, 0 van)")

    def test_bags_includes_mandatory_and_bonus(self):
        """Mandatory + bonus + silent all count in get_secured_bags_amount(false)."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        self._assert_resolve_bags_exists(lua)
        lua.execute('''
            tweak_data = {
                carry = {
                    small_loot = {},
                    gold = {is_vehicle = false},
                    diamond = {is_vehicle = false},
                    artwork = {is_vehicle = false}
                },
                hud = {medium_font_noshadow = "fonts/font_medium_mf"}
            }
            managers.loot = {
                _global = {
                    mandatory_bags = {amount = 1, carry_id = "gold"},
                    secured = {
                        {carry_id = "gold"},
                        {carry_id = "diamond"},
                        {carry_id = "artwork"}
                    }
                }
            }
            function managers.loot:get_secured_bags_amount(is_vehicle)
                local amount = 0
                for _, data in ipairs(self._global.secured) do
                    if not tweak_data.carry.small_loot[data.carry_id]
                       and not tweak_data.carry[data.carry_id].is_vehicle == not is_vehicle then
                        amount = amount + 1
                    end
                end
                return amount
            end
            _count = kyohud.hud.mission:_resolve_bags()
        ''')
        self.assertEqual(lua.globals()._count, 3,
            "RED: bags must count mandatory+bonus+silent (all 3)")

    def test_bags_sync_load_resets_without_notification(self):
        """sync_load replaces _global with no HUD notification;
        next _resolve_bags must reflect the new registry."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        self._assert_resolve_bags_exists(lua)
        lua.execute('''
            tweak_data = {
                carry = {
                    small_loot = {},
                    gold = {is_vehicle = false}
                },
                hud = {medium_font_noshadow = "fonts/font_medium_mf"}
            }
            managers.loot = {
                _global = {secured = {
                    {carry_id = "gold"},
                    {carry_id = "gold"},
                    {carry_id = "gold"}
                }}
            }
            function managers.loot:get_secured_bags_amount(is_vehicle)
                local amount = 0
                for _, data in ipairs(self._global.secured) do
                    if not tweak_data.carry.small_loot[data.carry_id]
                       and not tweak_data.carry[data.carry_id].is_vehicle == not is_vehicle then
                        amount = amount + 1
                    end
                end
                return amount
            end
            _count_before = kyohud.hud.mission:_resolve_bags()

            function managers.loot:sync_load(data)
                self._global = data.LootManager
            end
            managers.loot:sync_load({LootManager = {secured = {{carry_id = "gold"}}}})

            _count_after = kyohud.hud.mission:_resolve_bags()
        ''')
        g = lua.globals()
        self.assertEqual(g._count_before, 3, "RED: before sync_load, 3 bags")
        self.assertEqual(g._count_after, 1,
            "RED: after sync_load replaces registry, 1 bag")

    def test_bags_sync_load_callback_invoked_absolute_count(self):
        """When mission registers a sync_load callback, invoking native sync_load
        must update _bags_count to the absolute new count (not additive)."""
        lua, ok = _lua(with_mission=False, context="lib/managers/lootmanager")
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        mission_src = _read(MISSION_PATH)
        if not mission_src:
            self.fail("RED: mission.lua must exist")
            return

        lua.execute(LOOTMANAGER_FIXTURE)
        lua.execute(self._standard_carry_tweak())
        lua.execute('''
            managers.loot._global = {secured = {
                {carry_id = "gold"},
                {carry_id = "gold"},
                {carry_id = "gold"}
            }}
        ''')
        lua.execute(mission_src)

        lua.execute('''
            _sync_hooks = 0
            for _, e in ipairs(Hooks._all) do
                if e.method == "sync_load" then _sync_hooks = _sync_hooks + 1 end
            end
        ''')
        self.assertGreaterEqual(lua.globals()._sync_hooks, 1,
            "RED: mission must register sync_load hook under lootmanager context")

        lua.execute('''
            managers.loot:sync_load({LootManager = {secured = {
                {carry_id = "gold"}
            }}})
            for _, e in ipairs(Hooks._all) do
                if e.method == "sync_load" then e.fn(managers.loot, {LootManager = {secured = {{carry_id = "gold"}}}}) end
            end
            _bags_count = kyohud.hud.mission._bags_count
        ''')
        self.assertEqual(lua.globals()._bags_count, 1,
            "RED: sync_load callback must set absolute count (1), not additive")

    def test_bags_sync_load_repeated_no_double_count(self):
        """Repeated sync_load with same data must not accumulate count."""
        lua, ok = _lua(with_mission=False, context="lib/managers/lootmanager")
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        mission_src = _read(MISSION_PATH)
        if not mission_src:
            self.fail("RED: mission.lua must exist")
            return

        lua.execute(LOOTMANAGER_FIXTURE)
        lua.execute(self._standard_carry_tweak())
        lua.execute(mission_src)

        lua.execute('''
            local data = {LootManager = {secured = {{carry_id = "gold"}, {carry_id = "gold"}}}}
            managers.loot:sync_load(data)
            for _, e in ipairs(Hooks._all) do
                if e.method == "sync_load" then e.fn(managers.loot, data) end
            end
            _count_first = kyohud.hud.mission._bags_count

            managers.loot:sync_load(data)
            for _, e in ipairs(Hooks._all) do
                if e.method == "sync_load" then e.fn(managers.loot, data) end
            end
            _count_second = kyohud.hud.mission._bags_count
        ''')
        g = lua.globals()
        self.assertEqual(g._count_first, 2,
            "RED: first sync_load must yield absolute count 2")
        self.assertEqual(g._count_second, 2,
            "RED: repeated sync_load must NOT accumulate (still 2, not 4)")

    def test_bags_loot_value_updated_silent_true(self):
        """sync_secure_loot with silent=true still updates _bags_count via
        loot_value_updated callback."""
        lua, ok = _lua(with_mission=False)
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        mission_src = _read(MISSION_PATH)
        if not mission_src:
            self.fail("RED: mission.lua must exist")
            return

        lua.execute(LOOTMANAGER_FIXTURE)
        lua.execute(self._standard_carry_tweak())
        lua.execute('''
            managers.loot._global = {secured = {
                {carry_id = "gold"}
            }}
        ''')
        lua.execute(mission_src)
        lua.execute('''
            RequiredScript = "lib/managers/lootmanager"
        ''')
        lua.execute(mission_src)

        lua.execute('''
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)

            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 0) end
            end
            _count_before = kyohud.hud.mission._bags_count

            managers.loot:sync_secure_loot("gold", 1, true, nil)
            for _, e in ipairs(Hooks._all) do
                if e.method == "sync_secure_loot" and e.class == LootManager then
                    e.fn(managers.loot, "gold", 1, true, nil)
                end
                if e.method == "loot_value_updated" and e.class == HUDManager then
                    e.fn(mgr)
                end
            end
            _count_after = kyohud.hud.mission._bags_count
        ''')
        g = lua.globals()
        self.assertEqual(g._count_before, 1,
            "RED: before secure, 1 bag")
        self.assertEqual(g._count_after, 2,
            "RED: after secure (silent true), _bags_count must be 2")

    def test_bags_loot_value_updated_silent_false(self):
        """sync_secure_loot with silent=false updates _bags_count via
        loot_value_updated callback."""
        lua, ok = _lua(with_mission=False)
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        mission_src = _read(MISSION_PATH)
        if not mission_src:
            self.fail("RED: mission.lua must exist")
            return

        lua.execute(LOOTMANAGER_FIXTURE)
        lua.execute(self._standard_carry_tweak())
        lua.execute('''
            managers.loot._global = {secured = {
                {carry_id = "gold"}
            }}
        ''')
        lua.execute(mission_src)
        lua.execute('''
            RequiredScript = "lib/managers/lootmanager"
        ''')
        lua.execute(mission_src)

        lua.execute('''
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)

            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 0) end
            end
            _count_before = kyohud.hud.mission._bags_count

            managers.loot:sync_secure_loot("diamond", 1, false, nil)
            for _, e in ipairs(Hooks._all) do
                if e.method == "sync_secure_loot" and e.class == LootManager then
                    e.fn(managers.loot, "diamond", 1, false, nil)
                end
                if e.method == "loot_value_updated" and e.class == HUDManager then
                    e.fn(mgr)
                end
            end
            _count_after = kyohud.hud.mission._bags_count
        ''')
        g = lua.globals()
        self.assertEqual(g._count_before, 1,
            "RED: before secure, 1 bag")
        self.assertEqual(g._count_after, 2,
            "RED: after secure (silent false), _bags_count must be 2")


class MissionLifecycleSnapshotTests(unittest.TestCase):
    """RED: mission integrates with runtime lifecycle via callbacks.

    init_finalize, enable, refresh_settings, root loss/rebuild/unmount/destroy.
    Repeated chunk loading preserves mounted identity/captured data.
    """

    def test_init_finalize_triggers_mount(self):
        """init_finalize callback must trigger mission mount."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud

            kyohud.hud.runtime:mount(mgr)

            local hooks_before = 0
            for _, e in ipairs(Hooks._all) do
                if e.method == "init_finalize" then hooks_before = hooks_before + 1 end
            end

            for _, e in ipairs(Hooks._all) do
                if e.method == "init_finalize" then
                    e.fn(mgr)
                end
            end

            _root = kyohud.hud.mission._root_panel
        ''')
        self.assertIsNotNone(lua.globals()._root,
            "RED: init_finalize must trigger mission mount when enabled")

    def test_refresh_settings_enables_mount(self):
        """refresh_settings from disabled to enabled must mount mission."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = false
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud

            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)
            _root_disabled = kyohud.hud.mission._root_panel

            kyohud.settings.enable_mission = true
            for _, e in ipairs(Hooks._all) do
                if e.method == "resolution_changed" then e.fn(mgr) end
            end

            _root_enabled = kyohud.hud.mission._root_panel
        ''')
        g = lua.globals()
        self.assertIsNone(g._root_disabled, "RED: disabled mission has no root")
        self.assertIsNotNone(g._root_enabled,
            "RED: refresh_settings must mount when enabled")

    def test_refresh_settings_disables_unmount(self):
        """refresh_settings from enabled to disabled must unmount mission."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud

            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)
            _root_enabled = kyohud.hud.mission._root_panel

            kyohud.settings.enable_mission = false
            for _, e in ipairs(Hooks._all) do
                if e.method == "resolution_changed" then e.fn(mgr) end
            end

            _root_disabled = kyohud.hud.mission._root_panel
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._root_enabled, "RED: enabled mission has root")
        self.assertIsNone(g._root_disabled,
            "RED: refresh_settings must unmount when disabled")

    def test_root_loss_triggers_remount(self):
        """When runtime root is lost (engine removes panel, marks dead),
        next update must recover with a new live root. Mission root and
        captured text must be preserved."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            _fp = _make_parent()
            _safe = _make_mgr(_fp)
            _mgr = _G.managers.hud

            kyohud.hud.runtime:mount(_mgr)
            kyohud.hud.mission:mount(_mgr)

            _mgr:_create_heist_timer({})
            _mgr:feed_heist_time(100)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(_mgr, 100) end
            end

            _root_before = kyohud.hud.mission._root_panel
            _runtime_root_before = kyohud.hud.runtime._root_panel
            _timer_before = kyohud.hud.mission._timer_text

            -- Simulate ENGINE loss: remove old runtime root from parent
            -- and mark it + descendants dead. Do NOT just nil _root_panel.
            local old_rt_root = kyohud.hud.runtime._root_panel
            if old_rt_root then
                local parent = kyohud.hud.runtime._parent_panel
                if parent then
                    parent:remove(old_rt_root)
                end
                _kill_panel_tree(old_rt_root)
            end

            -- Advance time past recovery interval (0.5s)
            _advance_time(1.0)
            kyohud.hud.runtime:update(_mgr, _get_time(), 1.0)
            kyohud.hud.mission:update(_mgr, _get_time(), 1.0)

            _runtime_root_after = kyohud.hud.runtime._root_panel
            _mission_root_after = kyohud.hud.mission._root_panel
            _timer_after = kyohud.hud.mission._timer_text
            _root_alive = _mission_root_after and _mission_root_after._alive or false
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._root_before, "RED: mission mounted initially")
        self.assertIsNotNone(g._runtime_root_before,
            "RED: runtime root existed before simulated loss")
        self.assertIsNotNone(g._runtime_root_after,
            "RED: runtime must recover root on update after engine loss")
        self.assertIsNotNone(g._mission_root_after,
            "RED: mission root must exist after recovery")
        self.assertTrue(bool(g._root_alive),
            "RED: recovered mission root must be alive")
        self.assertEqual(g._timer_before, "01:40",
            "RED: captured timer text before loss")
        self.assertEqual(g._timer_after, "01:40",
            "RED: captured timer text preserved after recovery")

    def test_repeated_chunk_loading_preserves_identity(self):
        """Repeated mission.lua loads must preserve mounted identity and captured data."""
        lua, ok = _lua(with_mission=False)
        self.assertTrue(ok, "RED: mission.lua must exist")
        mission_src = _read(MISSION_PATH)
        if not mission_src:
            self.fail("RED: mission.lua must exist")
            return

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            _fp = _make_parent()
            _safe = _make_mgr(_fp)
            _mgr = _G.managers.hud

            kyohud.hud.runtime:mount(_mgr)
        ''')
        lua.execute(mission_src)
        lua.execute('''
            kyohud.hud.mission:mount(_mgr)
            _mgr:_create_heist_timer({})
            _mgr:feed_heist_time(100)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(_mgr, 100) end
            end
            _root1 = kyohud.hud.mission._root_panel
            _timer1 = kyohud.hud.mission._timer_text
            _mounted1 = kyohud.hud.mission._mounted
        ''')
        lua.execute(mission_src)
        lua.execute('''
            _root2 = kyohud.hud.mission._root_panel
            _timer2 = kyohud.hud.mission._timer_text
            _mounted2 = kyohud.hud.mission._mounted
            _same_root = rawequal(_root1, _root2)
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._root1, "RED: first load mounts")
        self.assertEqual(g._timer1, "01:40", "RED: first load captures timer")
        self.assertTrue(bool(g._mounted1), "RED: first load marks mounted")
        self.assertIsNotNone(g._root2, "RED: second load preserves root")
        self.assertEqual(g._timer2, "01:40", "RED: second load preserves captured timer")
        self.assertTrue(bool(g._mounted2), "RED: second load preserves mounted flag")
        self.assertTrue(bool(g._same_root),
            "RED: repeated loads must preserve root identity")


class MissionFontTests(unittest.TestCase):
    """RED: mission must use tweak_data.hud.medium_font_noshadow, not hud_fonts.timer."""

    def test_timer_prim_uses_medium_font_noshadow(self):
        """Timer primitive font must be tweak_data.hud.medium_font_noshadow."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud

            tweak_data = {hud = {medium_font_noshadow = "fonts/font_medium_mf"}, carry = {small_loot = {}}}

            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)

            mgr:_create_heist_timer({})
            mgr:feed_heist_time(60)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 60) end
            end

            _prim = kyohud.hud.mission._timer_prim
            _font = _prim and _prim._font or nil
        ''')
        self.assertEqual(lua.globals()._font, "fonts/font_medium_mf",
            "RED: timer primitive must use tweak_data.hud.medium_font_noshadow")

    def test_missing_font_fails_closed(self):
        """When tweak_data.hud.medium_font_noshadow is missing, primitive
        creation must fail closed."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud

            tweak_data = {}

            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)

            _prim = kyohud.hud.mission._timer_prim
        ''')
        self.assertIsNone(lua.globals()._prim,
            "RED: missing font must fail closed (no primitive created)")


class MissionNoTimerTests(unittest.TestCase):
    """RED: no_timer must not show mission timer."""

    def test_no_timer_disables_timer_display(self):
        """When HUDHeistTimer is created with no_timer=true, mission must not
        display the timer. The primitive may be absent or invisible."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud

            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)

            mgr:_create_heist_timer({no_timer = true})
            mgr:feed_heist_time(100)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 100) end
            end

            _prim = kyohud.hud.mission._timer_prim
            _prim_absent = (_prim == nil)
            _prim_hidden = false
            if _prim then
                local v = _prim:visible()
                local a = _prim:alpha()
                _prim_hidden = (v == false) or (a == 0)
            end
            _no_display = _prim_absent or _prim_hidden
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._no_display),
            "RED: no_timer must not display timer (primitive absent or invisible)")

    def test_no_timer_text_remains_unknown(self):
        """no_timer must leave _timer_text nil (unknown), not '00:00'."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            _G.managers.hud:_create_heist_timer({no_timer = true})
            local mgr = _G.managers.hud
            mgr:feed_heist_time(100)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 100) end
            end
            _text = kyohud.hud.mission._timer_text
            _known = kyohud.hud.mission._timer_known
        ''')
        g = lua.globals()
        self.assertIsNone(g._text,
            "RED: no_timer must leave _timer_text nil")
        self.assertFalse(bool(g._known),
            "RED: no_timer must leave _timer_known false")


class MissionSnapshotActivationTests(unittest.TestCase):
    """RED: snapshot activation with existing native state, rebuild preserve,
    and new heist reset."""

    def test_snapshot_captures_existing_timer_title_loot(self):
        """When mission mounts with existing native timer, title, and loot,
        all are captured."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud

            mgr:_create_heist_timer({})
            mgr:feed_heist_time(300)

            managers.job = {current_level_id = function() return "firestarter_1" end}
            tweak_data.levels = {firestarter_1 = {name_id = "heist_firestarter"}}
            managers.localization = {text = function() return "Firestarter" end}

            tweak_data.carry = {small_loot = {}, gold = {is_vehicle = false}}
            managers.loot = {
                _global = {secured = {{carry_id = "gold"}, {carry_id = "gold"}}}
            }
            function managers.loot:get_secured_bags_amount(is_vehicle)
                local n = 0
                for _, d in ipairs(self._global.secured) do
                    if not tweak_data.carry.small_loot[d.carry_id] then n = n + 1 end
                end
                return n
            end

            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)

            _timer = kyohud.hud.mission._timer_text
            _title_text = kyohud.hud.mission._title_text
            _bags_count = kyohud.hud.mission._bags_count
            _title_prim_text = kyohud.hud.mission._title_prim and kyohud.hud.mission._title_prim:text() or nil
            _bags_prim_text = kyohud.hud.mission._bags_prim and kyohud.hud.mission._bags_prim:text() or nil
        ''')
        g = lua.globals()
        self.assertEqual(g._timer, "05:00",
            "RED: snapshot must capture existing timer text")
        self.assertEqual(g._title_text, "Firestarter",
            "RED: snapshot must capture existing title")
        self.assertEqual(g._bags_count, 2,
            "RED: snapshot must capture existing bag count")
        self.assertEqual(g._title_prim_text, "Firestarter",
            "RED: title primitive must display captured title")
        self.assertEqual(g._bags_prim_text, "2",
            "RED: bags primitive must display captured bag count")

    def test_rebuild_preserves_captured_state(self):
        """After rebuild (resolution_changed), captured timer/title/loot
        are preserved, not lost."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud

            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)

            mgr:_create_heist_timer({})
            mgr:feed_heist_time(200)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 200) end
            end

            _timer_before = kyohud.hud.mission._timer_text
            _root_before = kyohud.hud.mission._root_panel

            for _, e in ipairs(Hooks._all) do
                if e.method == "resolution_changed" then e.fn(mgr) end
            end

            _timer_after = kyohud.hud.mission._timer_text
            _root_after = kyohud.hud.mission._root_panel
        ''')
        g = lua.globals()
        self.assertEqual(g._timer_before, "03:20",
            "RED: timer captured before rebuild")
        self.assertEqual(g._timer_after, "03:20",
            "RED: timer preserved after rebuild")
        self.assertIsNotNone(g._root_after,
            "RED: root exists after rebuild")

    def test_first_init_finalize_preserves_same_heist(self):
        """First init_finalize on same manager with pre-mount captured state
        must preserve that same heist (no reset)."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud

            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)

            mgr:_create_heist_timer({})
            mgr:feed_heist_time(500)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 500) end
            end
            _timer_before = kyohud.hud.mission._timer_text
            _title_before = kyohud.hud.mission._title_text
            _bags_before = kyohud.hud.mission._bags_count

            for _, e in ipairs(Hooks._all) do
                if e.method == "init_finalize" then e.fn(mgr) end
            end

            _timer_after = kyohud.hud.mission._timer_text
            _title_after = kyohud.hud.mission._title_text
            _bags_after = kyohud.hud.mission._bags_count
        ''')
        g = lua.globals()
        self.assertEqual(g._timer_before, "08:20",
            "RED: timer captured before first init_finalize")
        self.assertEqual(g._timer_after, "08:20",
            "RED: first init_finalize on same manager must preserve timer (same heist)")
        self.assertEqual(g._title_after, g._title_before,
            "RED: first init_finalize on same manager must preserve title (same heist)")
        self.assertEqual(g._bags_after, g._bags_before,
            "RED: first init_finalize on same manager must preserve bags (same heist)")

    def test_new_heist_resets_captured_state(self):
        """init_finalize on a genuinely NEW HUD manager (different object, no
        native timer) must reset captured state: no old time/title/bag inherited.
        Combat state must remain untouched by mission."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true

            managers.loot = {
                _global = {secured = {
                    {carry_id = "gold"},
                    {carry_id = "gold"},
                    {carry_id = "gold"}
                }}
            }
            function managers.loot:get_secured_bags_amount(is_vehicle)
                return 3
            end

            managers.job = {current_level_id = function() return "old" end}
            tweak_data.levels = {old = {name_id = "heist_old"}}
            managers.localization = {text = function(self, key)
                if key == "heist_old" then return "Old Heist" end
                if key == "ky_hud_mission_title" then return "HEIST IN PROGRESS" end
                return key
            end}

            kyohud._heist_score_total = 123

            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr_old = _G.managers.hud

            kyohud.hud.runtime:mount(mgr_old)
            kyohud.hud.mission:mount(mgr_old)

            mgr_old:_create_heist_timer({})
            mgr_old:feed_heist_time(500)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr_old, 500) end
            end

            _oldbag = kyohud.hud.mission._bags_count
            _oldtitle = kyohud.hud.mission._title_text
            _oldtimer = kyohud.hud.mission._timer_text

            managers.loot = nil
            managers.job = nil

            local fp2 = _make_parent()
            local safe2 = _make_mgr(fp2)
            local mgr_new = _G.managers.hud

            for _, e in ipairs(Hooks._all) do
                if e.method == "init_finalize" then e.fn(mgr_new) end
            end

            _newbag = kyohud.hud.mission._bags_count
            _newtitle = kyohud.hud.mission._title_text
            _newtimer = kyohud.hud.mission._timer_text
            _real_score = kyohud._heist_score_total
            _mission_root = kyohud.hud.mission._root_panel
            _runtime_root = kyohud.hud.runtime._root_panel
            _is_child = false
            if _runtime_root and _mission_root then
                for _, ch in pairs(_runtime_root._children) do
                    if ch == _mission_root then
                        _is_child = true
                        break
                    end
                end
            end
        ''')
        g = lua.globals()
        self.assertEqual(g._oldbag, 3, "RED: old heist must capture 3 bags")
        self.assertEqual(g._oldtitle, "Old Heist", "RED: old heist must capture title")
        self.assertEqual(g._oldtimer, "08:20", "RED: timer captured before new heist")
        self.assertIsNone(g._newtimer, "RED: new heist must reset captured timer")
        self.assertIsNone(g._newbag, "RED: new heist must reset bags to nil")
        self.assertNotEqual(g._newtitle, "Old Heist", "RED: new heist must not inherit old title")
        self.assertEqual(g._real_score, 123, "RED: mission must not touch real combat score")
        self.assertTrue(bool(g._is_child), "RED: mission root must be child of current runtime root")


if __name__ == "__main__":
    unittest.main()
