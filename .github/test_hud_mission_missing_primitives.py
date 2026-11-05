"""REGRESSION: mission primitives must not log nil dereference errors.

When _verify_labels dereferences nil inside pcall, it produces engine logged
errors despite returning false. This test wraps global pcall before loading
production with a delegating wrapper that captures errors while preserving
all return values via select('#', ...) + unpack(results, 1, n).

Tests:
1. Startup with absent primitives: reset errors BEFORE mount, assert title
   initially nil, mount, positive _verify_render(), zero caught errors.
2. Recovery after primitive removal: remove primitive from parent, clear field,
   runtime:update at increasing times, zero errors, verify recreated primitive.
3. Missing required primitive: each title/bags_label/bags/timer individually,
   nil field returns false with zero errors, restore before next.
4. Color corruption: positive verify, corrupt RGB, false, restore, true.
"""
import unittest
from lupa.luajit21 import LuaRuntime
from test_hud_mission import STUBS, DIESEL, _read, ROOT, MISSION_PATH, LAYOUT_PATH, RUNTIME_PATH, NATIVE_VIS_PATH
from test_hud_mission import NATIVE_TIMER_FIXTURE, HUDMANAGER_TIMER_FIXTURE
from hud_presentation_fixture import PRESENTATION_DIESEL

PCALL_WRAPPER = r'''
-- Wrap global pcall to capture errors while preserving all return values.
_original_pcall = pcall
_caught_errors = {}
_caught_error_count = 0

local function capture_count(...)
    return select('#', ...), {...}
end

function pcall(func, ...)
    local n, results = capture_count(_original_pcall(func, ...))
    local ok = results[1]
    if not ok then
        local err = results[2]
        _caught_error_count = _caught_error_count + 1
        table.insert(_caught_errors, tostring(err))
    end
    return unpack(results, 1, n)
end

function _get_caught_error_count()
    return _caught_error_count
end

function _get_caught_errors()
    return _caught_errors
end

function _reset_caught_errors()
    _caught_errors = {}
    _caught_error_count = 0
end
'''


CHILD_REGISTRATION_WRAPPER = r'''
-- Test-local wrapper: register named text children created via p:text().
local _outer_original_make_panel = _make_panel
function _make_panel(name)
    local p = _outer_original_make_panel(name)
    local _outer_original_text = p.text
    function p:text(opts)
        local t = _outer_original_text(self, opts)
        if opts and opts.name then
            self._children[opts.name] = t
        end
        return t
    end
    return p
end
'''


def _lua_with_pcall_wrapper():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute(PCALL_WRAPPER)
    lua.execute(DIESEL)
    lua.execute(PRESENTATION_DIESEL)
    lua.execute(CHILD_REGISTRATION_WRAPPER)
    lua.execute(NATIVE_TIMER_FIXTURE)
    lua.execute(HUDMANAGER_TIMER_FIXTURE)
    lua.execute(_read(LAYOUT_PATH))
    lua.execute(_read(RUNTIME_PATH))
    lua.execute(_read(NATIVE_VIS_PATH))
    mission_src = _read(MISSION_PATH)
    lua.execute(mission_src)
    return lua, mission_src is not None


class MissingPrimitivesTests(unittest.TestCase):

    def test_startup_absent_primitives_zero_errors(self):
        lua, ok = _lua_with_pcall_wrapper()
        self.assertTrue(ok, "mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud
            _reset_caught_errors()
            _title_before = kyohud.hud.mission._title_prim
            kyohud.hud.runtime:mount(mgr)
            _verified = kyohud.hud.mission:_verify_render()
            _errors = _get_caught_error_count()
        ''')
        g = lua.globals()
        self.assertIsNone(g._title_before, "title must be nil before mount")
        self.assertTrue(bool(g._verified), "_verify_render must succeed")
        self.assertEqual(int(g._errors), 0, "zero caught errors during startup")

    def test_recovery_after_primitive_removal(self):
        lua, ok = _lua_with_pcall_wrapper()
        self.assertTrue(ok, "mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud
            kyohud.hud.runtime:mount(mgr)
            local old_prim = kyohud.hud.mission._title_prim
            local root = kyohud.hud.mission._root_panel
            _registered_before = false
            for _, v in pairs(root._children) do
                if v == old_prim then _registered_before = true; break end
            end
            root:remove(old_prim)
            _registered_after = false
            for _, v in pairs(root._children) do
                if v == old_prim then _registered_after = true; break end
            end
            _absent_after = not _registered_after
            kyohud.hud.mission._title_prim = nil
            _reset_caught_errors()
            _advance_time(1.0)
            kyohud.hud.runtime:update(mgr, _get_time(), 1.0)
            _advance_time(1.0)
            kyohud.hud.runtime:update(mgr, _get_time(), 1.0)
            _verified = kyohud.hud.mission:_verify_render()
            _recreated = kyohud.hud.mission._title_prim ~= nil
            _is_different = kyohud.hud.mission._title_prim ~= old_prim
            _old_dead = not alive(old_prim)
            _errors = _get_caught_error_count()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._registered_before), "old child must be registered in parent before remove")
        self.assertEqual(int(g._errors), 0, "zero caught errors during recovery")
        self.assertTrue(bool(g._verified), "_verify_render must succeed")
        self.assertTrue(bool(g._recreated), "primitive must be recreated")
        self.assertTrue(bool(g._is_different), "recreated primitive must be different object")
        self.assertTrue(bool(g._old_dead), "old primitive must be dead")
        self.assertTrue(bool(g._absent_after), "old child must be absent from parent after remove")

    def test_missing_required_primitive_returns_false_zero_errors(self):
        lua, ok = _lua_with_pcall_wrapper()
        self.assertTrue(ok, "mission.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud
            mgr:_create_heist_timer({})
            mgr:feed_heist_time(42)
            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 42) end
            end
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.mission:mount(mgr)
            _timer_known_before = kyohud.hud.mission._timer_known
            _timer_enabled_before = kyohud.hud.mission:_is_timer_enabled()
            _verified_positive = kyohud.hud.mission:_verify_render()
            _results = {}
            local saved_title = kyohud.hud.mission._title_prim
            kyohud.hud.mission._title_prim = nil
            _reset_caught_errors()
            _results.title = kyohud.hud.mission:_verify_labels()
            _results.title_errors = _get_caught_error_count()
            kyohud.hud.mission._title_prim = saved_title
            _results.title_positive = kyohud.hud.mission:_verify_render()
            local saved_bags_label = kyohud.hud.mission._bags_label_prim
            kyohud.hud.mission._bags_label_prim = nil
            _reset_caught_errors()
            _results.bags_label = kyohud.hud.mission:_verify_labels()
            _results.bags_label_errors = _get_caught_error_count()
            kyohud.hud.mission._bags_label_prim = saved_bags_label
            _results.bags_label_positive = kyohud.hud.mission:_verify_render()
            local saved_bags = kyohud.hud.mission._bags_prim
            kyohud.hud.mission._bags_prim = nil
            _reset_caught_errors()
            _results.bags = kyohud.hud.mission:_verify_labels()
            _results.bags_errors = _get_caught_error_count()
            kyohud.hud.mission._bags_prim = saved_bags
            _results.bags_positive = kyohud.hud.mission:_verify_render()
            local saved_timer = kyohud.hud.mission._timer_prim
            local saved_timer_known = kyohud.hud.mission._timer_known
            local saved_timer_text = kyohud.hud.mission._timer_text
            kyohud.hud.mission._timer_prim = nil
            _reset_caught_errors()
            _results.timer = kyohud.hud.mission:_verify_labels()
            _results.timer_errors = _get_caught_error_count()
            kyohud.hud.mission._timer_prim = saved_timer
            kyohud.hud.mission._timer_known = saved_timer_known
            kyohud.hud.mission._timer_text = saved_timer_text
            _results.timer_positive = kyohud.hud.mission:_verify_render()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._timer_known_before), "timer must be known after real feed seed")
        self.assertTrue(bool(g._timer_enabled_before), "timer must be enabled after real feed seed")
        self.assertTrue(bool(g._verified_positive), "positive verification must succeed before nil corruption")
        self.assertFalse(bool(g._results.title), "missing title must return false")
        self.assertEqual(int(g._results.title_errors), 0, "zero errors for missing title")
        self.assertTrue(bool(g._results.title_positive), "positive verify after restoring title")
        self.assertFalse(bool(g._results.bags_label), "missing bags_label must return false")
        self.assertEqual(int(g._results.bags_label_errors), 0, "zero errors for missing bags_label")
        self.assertTrue(bool(g._results.bags_label_positive), "positive verify after restoring bags_label")
        self.assertFalse(bool(g._results.bags), "missing bags must return false")
        self.assertEqual(int(g._results.bags_errors), 0, "zero errors for missing bags")
        self.assertTrue(bool(g._results.bags_positive), "positive verify after restoring bags")
        self.assertFalse(bool(g._results.timer), "missing timer must return false")
        self.assertEqual(int(g._results.timer_errors), 0, "zero errors for missing timer")
        self.assertTrue(bool(g._results.timer_positive), "positive verify after restoring timer")

    def test_color_corruption_rejected(self):
        lua, ok = _lua_with_pcall_wrapper()
        self.assertTrue(ok, "mission.lua must exist")
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
            _verified_positive = kyohud.hud.mission:_verify_render()
            local prim = kyohud.hud.mission._title_prim
            local original_color = prim:color()
            prim:set_color(Color(0, 0, 0))
            _verified_corrupt = kyohud.hud.mission:_verify_labels()
            prim:set_color(original_color)
            _verified_restored = kyohud.hud.mission:_verify_labels()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._verified_positive), "positive verification must succeed")
        self.assertFalse(bool(g._verified_corrupt), "corrupted color must return false")
        self.assertTrue(bool(g._verified_restored), "restored color must return true")


if __name__ == '__main__':
    unittest.main()
