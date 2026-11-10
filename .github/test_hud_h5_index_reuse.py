"""H5 child binding index: reuse only validated (parent, name) lookups.

The real runtime chunk is executed through lupa/luajit21. The local h5_child is
reached through the real coordinator upvalues; known_child is exercised through
the real _apply_native_priority path. No Python copy of the Lua logic and no
production test hook.

RED before the index: repeated lookups always call parent:child(), no binding
exists, and the bounded purge has nothing to enforce. GREEN after the index:
stable bindings avoid repeated lookups, removed/reparented children fall back to
the fresh path, the bound is enforced, native value reads stay fresh, and the
conservative H4 lookup-failure flags are unchanged.
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = ROOT / "lua" / "hud" / "runtime.lua"

BASE = r'''
kyohud = kyohud or {}
Kyosh1roHUD = kyohud
kyohud.settings = {enable_hud_foundation = false, hud_scale = 1}
RequiredScript = "test/no-hooks"
function log(...) end
function alive(p) return p ~= nil and p._alive ~= false end

function _panel(name)
    local p = {
        _alive = true, _visible = true, _alpha = 1, _name = name or "panel",
        _children = {}, _child_calls = 0, _throw_child = false,
    }
    function p:child(n)
        self._child_calls = self._child_calls + 1
        if self._throw_child then error("child lookup failed") end
        return self._children[n]
    end
    function p:parent() return self._parent end
    function p:add_child(n, c)
        c._alive = true
        c._parent = self
        self._children[n] = c
        return c
    end
    function p:remove_child(n)
        local c = self._children[n]
        if c then
            self._children[n] = nil
            c._alive = false
            c._parent = nil
        end
        return c
    end
    function p:reparent(n, other)
        local c = self:remove_child(n)
        if c then
            c._alive = true
            other:add_child(n, c)
        end
        return c
    end
    function p:set_visible(v) self._visible = v end
    function p:visible() return self._visible end
    function p:set_alpha(a) self._alpha = a end
    function p:alpha() return self._alpha end
    function p:x() return 0 end
    function p:y() return 0 end
    function p:w() return 100 end
    function p:h() return 100 end
    return p
end
'''

EXTRACT = r'''
local function named_upvalue(fn, wanted)
    if type(fn) ~= "function" then return nil end
    for i = 1, 128 do
        local name, value = debug.getupvalue(fn, i)
        if name == nil then return nil end
        if name == wanted then return value end
    end
    return nil
end

local coord = kyohud.hud.runtime._coordinate_h5_native_duplicates
assert(type(coord) == "function", "H5 coordinator missing")
local collect = named_upvalue(coord, "h5_collect_player_targets")
assert(type(collect) == "function", "collector upvalue missing")
H5CHILD = named_upvalue(collect, "h5_child")
assert(type(H5CHILD) == "function", "h5_child upvalue missing")
'''


def _lua():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(BASE)
    lua.execute(RUNTIME_PATH.read_text(encoding="utf-8-sig"))
    lua.execute(EXTRACT)
    return lua


class BindingReuseTests(unittest.TestCase):
    def test_repeated_lookup_reuses_one_binding_and_one_child_call(self):
        lua = _lua()
        lua.execute(r'''
            parent = _panel("parent")
            child = _panel("child")
            parent:add_child("leaf", child)
            first = H5CHILD(parent, "leaf")
            index_first = kyohud.hud.runtime._h5_child_index
            calls_first = parent._child_calls
            second = H5CHILD(parent, "leaf")
            _same_child = first == second and first ~= nil
            _calls_first = calls_first
            _calls_second = parent._child_calls
            _index_created = index_first ~= nil
            _index_same = kyohud.hud.runtime._h5_child_index == index_first
            _index_count = index_first and index_first.count or -1
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._same_child))
        self.assertEqual(float(g._calls_first), 1.0,
                         "first lookup must use the fresh child path once")
        self.assertEqual(float(g._calls_second), 1.0,
                         "validated binding must avoid a second child() call")
        self.assertTrue(bool(g._index_created),
                        "a successful lookup must create the binding index")
        self.assertTrue(bool(g._index_same),
                        "stable generation must keep the same index table")
        self.assertEqual(float(g._index_count), 1.0)

    def test_same_name_under_two_parents_stays_distinct(self):
        lua = _lua()
        lua.execute(r'''
            left = _panel("left")
            right = _panel("right")
            left_child = _panel("left_child")
            right_child = _panel("right_child")
            left:add_child("same", left_child)
            right:add_child("same", right_child)
            l1 = H5CHILD(left, "same")
            r1 = H5CHILD(right, "same")
            l2 = H5CHILD(left, "same")
            r2 = H5CHILD(right, "same")
            _distinct = l1 == l2 and r1 == r2 and l1 ~= r1
            _left_calls = left._child_calls
            _right_calls = right._child_calls
            _index_count = kyohud.hud.runtime._h5_child_index
                and kyohud.hud.runtime._h5_child_index.count or -1
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._distinct))
        self.assertEqual(float(g._left_calls), 1.0)
        self.assertEqual(float(g._right_calls), 1.0)
        self.assertEqual(float(g._index_count), 2.0)

    def test_generation_change_drops_stale_bindings(self):
        lua = _lua()
        lua.execute(r'''
            parent = _panel("parent")
            child = _panel("child")
            parent:add_child("leaf", child)
            H5CHILD(parent, "leaf")
            first_index = kyohud.hud.runtime._h5_child_index
            kyohud.hud.runtime._generation = kyohud.hud.runtime._generation + 1
            again = H5CHILD(parent, "leaf")
            second_index = kyohud.hud.runtime._h5_child_index
            _same_child = again == child
            _first_index_exists = first_index ~= nil
            _second_index_exists = second_index ~= nil
            _replaced = first_index ~= second_index
            _second_count = second_index and second_index.count or -1
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._same_child))
        self.assertTrue(bool(g._first_index_exists))
        self.assertTrue(bool(g._second_index_exists))
        self.assertTrue(bool(g._replaced),
                        "a new root generation must not reuse bindings")
        self.assertEqual(float(g._second_count), 1.0)

    def test_release_clears_bindings(self):
        lua = _lua()
        lua.execute(r'''
            parent = _panel("parent")
            parent:add_child("leaf", _panel("child"))
            H5CHILD(parent, "leaf")
            before = kyohud.hud.runtime._h5_child_index
            kyohud.hud.runtime:_release_h5()
            after = kyohud.hud.runtime._h5_child_index
            _had_index = before ~= nil
            _cleared = after == nil
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._had_index))
        self.assertTrue(bool(g._cleared),
                        "release/unmount must drop all child bindings")


class InvalidationTests(unittest.TestCase):
    def test_removed_child_is_never_served_and_lookup_refreshes(self):
        lua = _lua()
        lua.execute(r'''
            parent = _panel("parent")
            old_child = _panel("old_child")
            parent:add_child("leaf", old_child)
            first = H5CHILD(parent, "leaf")
            index_created = kyohud.hud.runtime._h5_child_index ~= nil
            parent:remove_child("leaf")
            removed = H5CHILD(parent, "leaf")
            calls_after_remove = parent._child_calls
            new_child = _panel("new_child")
            parent:add_child("leaf", new_child)
            refreshed = H5CHILD(parent, "leaf")
            _first_ok = first == old_child
            _index_created = index_created
            _removed_nil = removed == nil
            _calls_after_remove = calls_after_remove
            _refreshed_new = refreshed == new_child
            _old_not_served = removed ~= old_child and refreshed ~= old_child
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._first_ok))
        self.assertTrue(bool(g._index_created))
        self.assertTrue(bool(g._removed_nil),
                        "a dead cached child must not be served")
        self.assertEqual(float(g._calls_after_remove), 2.0,
                         "a dead binding must fall back to the fresh path")
        self.assertTrue(bool(g._refreshed_new),
                        "a recreated child must refresh the binding")
        self.assertTrue(bool(g._old_not_served))

    def test_reparented_child_is_not_served_for_the_old_parent(self):
        lua = _lua()
        lua.execute(r'''
            old_parent = _panel("old_parent")
            new_parent = _panel("new_parent")
            child = _panel("child")
            old_parent:add_child("leaf", child)
            first = H5CHILD(old_parent, "leaf")
            index_created = kyohud.hud.runtime._h5_child_index ~= nil
            old_parent:reparent("leaf", new_parent)
            stale = H5CHILD(old_parent, "leaf")
            moved = H5CHILD(new_parent, "leaf")
            _first_ok = first == child
            _index_created = index_created
            _stale_nil = stale == nil
            _moved_is_child = moved == child
            _old_parent_calls = old_parent._child_calls
            _new_parent_calls = new_parent._child_calls
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._first_ok))
        self.assertTrue(bool(g._index_created))
        self.assertTrue(bool(g._stale_nil),
                        "a cached child reparented elsewhere must not be served")
        self.assertTrue(bool(g._moved_is_child))
        self.assertEqual(float(g._old_parent_calls), 2.0,
                         "the old parent must be looked up fresh after reparenting")
        self.assertEqual(float(g._new_parent_calls), 1.0)

    def test_index_bound_purges_and_never_exceeds_limit(self):
        lua = _lua()
        lua.execute(r'''
            for i = 1, 200 do
                local parent = _panel("parent_" .. i)
                parent:add_child("leaf", _panel("child_" .. i))
                H5CHILD(parent, "leaf")
            end
            index = kyohud.hud.runtime._h5_child_index
            _index_exists = index ~= nil
            _count = index and index.count or -1
            _bounded = index == nil or (index.count or 0) <= 128
            _positive = index == nil or (index.count or 0) > 0
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._index_exists),
                        "bindings must remain usable after a purge")
        self.assertTrue(bool(g._bounded),
                        "binding index must never exceed its fixed bound")
        self.assertTrue(bool(g._positive))

    def test_native_value_reads_stay_fresh(self):
        lua = _lua()
        lua.execute(r'''
            parent = _panel("parent")
            child = _panel("child")
            child:set_alpha(1)
            parent:add_child("leaf", child)
            first = H5CHILD(parent, "leaf")
            child:set_alpha(0.25)
            second = H5CHILD(parent, "leaf")
            _same_child = first == child and second == child
            _fresh_alpha = second:alpha() == 0.25
            _calls = parent._child_calls
            _index_created = kyohud.hud.runtime._h5_child_index ~= nil
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._same_child))
        self.assertTrue(bool(g._fresh_alpha),
                        "native values must be read fresh on every frame")
        self.assertEqual(float(g._calls), 1.0)
        self.assertTrue(bool(g._index_created))


class H4SemanticsTests(unittest.TestCase):
    def test_lookup_failure_still_hides_crew_and_local(self):
        lua = _lua()
        lua.execute(r'''
            common = _panel("common")
            crew_root = _panel("crew_root")
            player_root = _panel("player_root")
            temp = _panel("temp")
            bag = _panel("bag")
            temp:add_child("bag_panel", bag)
            bag:set_visible(false)

            mgr = {_teammate_panels = {}, _hud_temp = {_temp_panel = temp}}
            kyohud.hud.crew = {_root = crew_root}
            kyohud.hud.player = {_root = player_root}
            kyohud.hud.weapons = nil
            kyohud.hud.equipment = nil

            R = kyohud.hud.runtime
            R._manager = mgr
            R._parent_panel = common

            R:_apply_native_priority(1)
            first_crew_visible = crew_root:visible()
            first_local_visible = player_root:visible()
            index_created = R._h5_child_index ~= nil

            temp:remove_child("bag_panel")
            temp._throw_child = true
            R:_apply_native_priority(2)
            _first_crew_visible = first_crew_visible
            _first_local_visible = first_local_visible
            _index_created = index_created
            _crew_hidden = crew_root:visible() == false
            _local_hidden = player_root:visible() == false
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._first_crew_visible),
                        "a valid child lookup must not hide crew")
        self.assertTrue(bool(g._first_local_visible),
                        "a valid child lookup must not hide local")
        self.assertTrue(bool(g._index_created),
                        "H4 known_child must use the shared binding index")
        self.assertTrue(bool(g._crew_hidden),
                        "lookup status != CALL_OK must hide crew")
        self.assertTrue(bool(g._local_hidden),
                        "lookup status != CALL_OK must hide local")

    def test_copr_dynamic_child_zero_is_never_served_from_index(self):
        lua = _lua()
        lua.execute(r'''
            common = _panel("common")
            crew_root = _panel("crew_root")
            player_root = _panel("player_root")
            entry = _panel("entry")
            native_player = _panel("player")
            radial = _panel("radial_health_panel")
            copr = _panel("copr_overlay_panel")
            c0 = _panel("0")

            common:add_child("crew_root", crew_root)
            common:add_child("entry", entry)
            entry:add_child("player", native_player)
            native_player:add_child("radial_health_panel", radial)
            radial:add_child("copr_overlay_panel", copr)
            copr:add_child("0", c0)

            mgr = {_teammate_panels = {[1] = {_panel = entry, _special_equipment = {}}}}
            kyohud.hud.crew = {_root = crew_root}
            kyohud.hud.player = {_root = player_root}
            kyohud.hud.weapons = nil
            kyohud.hud.equipment = nil

            R = kyohud.hud.runtime
            R._manager = mgr
            R._parent_panel = common

            R:_apply_native_priority(1)
            _first_hidden = crew_root:visible() == false
            _first_calls = copr._child_calls

            -- Install the binding the index could reuse, then mimic a native
            -- clear that empties the container while the old object stays alive
            -- with the same immediate parent.
            local index = R._h5_child_index
            if not index then
                index = {generation = R._generation, parents = {}, count = 0}
                R._h5_child_index = index
            end
            if not index.parents[copr] then index.parents[copr] = {} end
            if index.parents[copr]["0"] == nil then index.count = index.count + 1 end
            index.parents[copr]["0"] = c0
            _binding_exists = index.parents[copr]["0"] == c0

            copr._children = {}
            crew_root:set_visible(true)

            R:_apply_native_priority(2)
            _calls_delta = copr._child_calls - _first_calls
            _second_crew_visible = crew_root:visible()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._first_hidden),
                        "the live copr child 0 must hide crew on the first scan")
        self.assertTrue(bool(g._binding_exists),
                        "the regression must exercise an existing (copr, 0) binding")
        self.assertEqual(float(g._calls_delta), 1.0,
                         "the copr child 0 lookup must re-consult its parent")
        self.assertTrue(bool(g._second_crew_visible),
                        "a stale (copr, 0) binding must never be served")


if __name__ == "__main__":
    unittest.main()
