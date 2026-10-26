"""LOT3a -- snapshot(manager) rebind: captures GroupAI state identity, detached scalars, alive converted count."""
import unittest
from test_hud_assault import _lua

GROUPAI_SNAPSHOT_FIXTURE = r'''
function GroupAIState:hostage_count() return self._hostage_count or 0 end
function GroupAIState:all_converted_enemies() return self._converted or {} end
'''

UNIT_FIXTURE = r'''
local Unit = {}; Unit.__index = Unit
function Unit:new(dead)
    local obj = setmetatable({}, self); obj._dead = dead
    obj._damage = {dead = function() return obj._dead end}
    return obj
end
function Unit:character_damage() return self._damage end
function make_unit(dead) return Unit:new(dead) end
'''

class SnapshotCaptureTests(unittest.TestCase):
    def test_snapshot_captures_and_detaches(self):
        lua, ok = _lua()
        self.assertTrue(ok, "assault.lua must exist")
        if not ok: return
        lua.execute(GROUPAI_SNAPSHOT_FIXTURE)
        lua.execute(UNIT_FIXTURE)
        lua.execute('assert(type(kyohud.hud.assault.snapshot)=="function","snapshot must be a function")')
        lua.execute('''
            local state = managers.groupai:state()
            state._assault_mode = true; state._hunt_mode = true; state._assault_number = 7
            state._hostage_count = 4
            state._converted = {make_unit(false), make_unit(false), make_unit(true)}
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('''
            _active = kyohud.hud.assault._state.active
            _number = kyohud.hud.assault._state.number
            _endless = kyohud.hud.assault._state.endless
            _hostages = kyohud.hud.assault._state.hostages
            _converted = kyohud.hud.assault._state.converted
            _source = kyohud.hud.assault._source
            _source_is_state = (_source == managers.groupai:state())
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._active), "snapshot must capture active=true from assault_mode")
        self.assertEqual(g._number, 7, "snapshot must capture number=7")
        self.assertTrue(bool(g._endless), "snapshot must capture endless=true from hunt_mode")
        self.assertEqual(g._hostages, 4, "snapshot must capture hostages=4")
        self.assertEqual(g._converted, 2, "snapshot must count 2 alive converted units")
        self.assertTrue(bool(g._source_is_state), "snapshot _source must be actual GroupAI state")
        lua.execute('''
            local state = managers.groupai:state()
            state._assault_number = 99
            state._converted = {make_unit(true), make_unit(true), make_unit(true)}
            _converted_after = kyohud.hud.assault._state.converted
        ''')
        g = lua.globals()
        self.assertEqual(g._converted_after, 2, "snapshot converted must stay 2 after source mutation")

    def test_snapshot_rebind_clears_old(self):
        lua, ok = _lua()
        self.assertTrue(ok, "assault.lua must exist")
        if not ok: return
        lua.execute(GROUPAI_SNAPSHOT_FIXTURE)
        lua.execute(UNIT_FIXTURE)
        lua.execute('assert(type(kyohud.hud.assault.snapshot)=="function","snapshot must be a function")')
        lua.execute('''
            local stateA = managers.groupai:state()
            stateA._assault_mode = true; stateA._assault_number = 7; stateA._hostage_count = 4
            stateA._converted = {make_unit(false)}
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('''
            local GroupAIState2 = {}
            GroupAIState2.__index = GroupAIState2
            function GroupAIState2:new()
                local obj = setmetatable({}, self)
                obj._assault_mode = false; obj._hunt_mode = false; obj._assault_number = 0
                obj._hostage_count = 0; obj._converted = {}
                return obj
            end
            function GroupAIState2:get_assault_mode() return self._assault_mode end
            function GroupAIState2:get_hunt_mode() return self._hunt_mode end
            function GroupAIState2:get_assault_number() return self._assault_number end
            function GroupAIState2:hostage_count() return self._hostage_count end
            function GroupAIState2:all_converted_enemies() return self._converted end
            managers.groupai._state = GroupAIState2:new()
            kyohud.hud.assault:snapshot(managers.hud)
            _active2 = kyohud.hud.assault._state.active
            _number2 = kyohud.hud.assault._state.number
            _hostages2 = kyohud.hud.assault._state.hostages
            _converted2 = kyohud.hud.assault._state.converted
        ''')
        g = lua.globals()
        self.assertFalse(bool(g._active2), "snapshot rebind must clear active to false")
        self.assertEqual(g._number2, 0, "snapshot rebind must capture number=0 from new source")
        self.assertEqual(g._hostages2, 0, "snapshot rebind must capture hostages=0")
        self.assertEqual(g._converted2, 0, "snapshot rebind must clear converted to 0")

    def test_snapshot_unknown_source_fails_closed(self):
        lua, ok = _lua()
        self.assertTrue(ok, "assault.lua must exist")
        if not ok: return
        lua.execute(GROUPAI_SNAPSHOT_FIXTURE)
        lua.execute(UNIT_FIXTURE)
        lua.execute('assert(type(kyohud.hud.assault.snapshot)=="function","snapshot must be a function")')
        lua.execute('''
            local state = managers.groupai:state()
            state._assault_mode = true; state._assault_number = 5; state._hostage_count = 3
            state._converted = {make_unit(false)}
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('''
            managers.groupai.state = function() return nil end
            kyohud.hud.assault:snapshot(managers.hud)
            _active_nil = kyohud.hud.assault._state.active
            _number_nil = kyohud.hud.assault._state.number
            _hostages_nil = kyohud.hud.assault._state.hostages
            _converted_nil = kyohud.hud.assault._state.converted
            _source_nil = kyohud.hud.assault._source
        ''')
        g = lua.globals()
        self.assertFalse(bool(g._active_nil), "unknown source must fail closed active=false")
        self.assertIsNone(g._number_nil, "unknown source must fail closed number=nil")
        self.assertIsNone(g._hostages_nil, "unknown source must fail closed hostages=nil")
        self.assertIsNone(g._converted_nil, "unknown source must fail closed converted=nil")
        self.assertIsNone(g._source_nil, "unknown source must clear A._source to nil")

    def test_snapshot_negative_boundary_damage_error(self):
        lua, ok = _lua()
        self.assertTrue(ok, "assault.lua must exist")
        if not ok: return
        lua.execute(GROUPAI_SNAPSHOT_FIXTURE)
        lua.execute(UNIT_FIXTURE)
        lua.execute('assert(type(kyohud.hud.assault.snapshot)=="function","snapshot must be a function")')
        lua.execute('''
            local state = managers.groupai:state()
            state._assault_mode = true; state._assault_number = 5; state._hostage_count = 2
            state._converted = {make_unit(false), make_unit(false)}
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('_converted2_before = kyohud.hud.assault._state.converted')
        g = lua.globals()
        self.assertEqual(g._converted2_before, 2, "initial snapshot must capture converted=2")
        lua.execute('''
            local state = managers.groupai:state()
            state._converted[1].character_damage = function() error("unavailable") end
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('_converted_nil = kyohud.hud.assault._state.converted')
        g = lua.globals()
        self.assertIsNone(g._converted_nil, "damage error must cause converted=nil, not partial")
        lua.execute('''
            local state = managers.groupai:state()
            state._converted[1].character_damage = function() return {dead = function() return false end} end
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('_converted2_after = kyohud.hud.assault._state.converted')
        g = lua.globals()
        self.assertEqual(g._converted2_after, 2, "repaired snapshot must capture converted=2 again")
        lua.execute('''
            local state = managers.groupai:state()
            state._assault_mode = true; state._hunt_mode = true
            local original_index = getmetatable(state).__index
            local broken_meta = {}
            broken_meta.__index = function(t, key)
                if key == "get_hunt_mode" then error("hunt_mode unavailable") end
                return original_index[key]
            end
            setmetatable(state, broken_meta)
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('''
            _endless_false = kyohud.hud.assault._state.endless
            _active_true = kyohud.hud.assault._state.active
        ''')
        g = lua.globals()
        self.assertFalse(bool(g._endless_false), "hunt_mode error must cause endless=false, not reuse previous true")
        self.assertTrue(bool(g._active_true), "assault_mode must still capture active=true")

    def test_snapshot_alive_throw_boundary(self):
        lua, ok = _lua()
        self.assertTrue(ok, "assault.lua must exist")
        if not ok: return
        lua.execute(GROUPAI_SNAPSHOT_FIXTURE)
        lua.execute(UNIT_FIXTURE)
        lua.execute('assert(type(kyohud.hud.assault.snapshot)=="function","snapshot must be a function")')
        lua.execute('''
            local state = managers.groupai:state()
            state._assault_mode = true; state._assault_number = 5; state._hostage_count = 2
            state._converted = {make_unit(false), make_unit(false), make_unit(true)}
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('_converted2 = kyohud.hud.assault._state.converted')
        g = lua.globals()
        self.assertEqual(g._converted2, 2, "initial snapshot must capture converted=2")
        lua.execute('_original_alive = alive')
        lua.execute('alive = function() error("alive unavailable") end')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('_converted_nil = kyohud.hud.assault._state.converted')
        g = lua.globals()
        self.assertIsNone(g._converted_nil, "alive throw must cause converted=nil, not partial count")
        lua.execute('alive = _original_alive')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('_converted2_after = kyohud.hud.assault._state.converted')
        g = lua.globals()
        self.assertEqual(g._converted2_after, 2, "repaired alive must capture converted=2 again")

class SnapshotNativeDeadShapeTests(unittest.TestCase):
    """Regression: native CopDamage:dead() returns self._dead.

    Native contract (verified):
    - GroupAIStateBase:all_converted_enemies() returns _converted_police
      keyed by unit key, values are units.
    - CopDamage:dead() returns self._dead.
    - Healthy unit: _dead is nil (not false).
    - Dead unit: _dead is true.

    Current bug: assault.snapshot and _refresh_counters demand boolean dead
    and reject healthy nil (type(nil) ~= "boolean" causes all_ok=false).

    These tests verify the DESIRED correct behavior.
    They should RED (fail) with the current production code until the
    dead-value contract is relaxed to accept nil as alive.
    """

    def test_empty_registry_yields_zero(self):
        lua, ok = _lua()
        self.assertTrue(ok, "assault.lua must exist")
        if not ok: return
        lua.execute(GROUPAI_SNAPSHOT_FIXTURE)
        lua.execute(UNIT_FIXTURE)
        lua.execute('assert(type(kyohud.hud.assault.snapshot)=="function","snapshot must be a function")')
        lua.execute('''
            local state = managers.groupai:state()
            state._assault_mode = true; state._assault_number = 5; state._hostage_count = 2
            state._converted = {}
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('_converted = kyohud.hud.assault._state.converted')
        g = lua.globals()
        self.assertEqual(g._converted, 0, "empty keyed registry must yield converted=0")

    def test_snapshot_counts_nil_dead_as_alive(self):
        lua, ok = _lua()
        self.assertTrue(ok, "assault.lua must exist")
        if not ok: return
        lua.execute(GROUPAI_SNAPSHOT_FIXTURE)
        lua.execute(UNIT_FIXTURE)
        lua.execute('assert(type(kyohud.hud.assault.snapshot)=="function","snapshot must be a function")')
        lua.execute('''
            local state = managers.groupai:state()
            state._assault_mode = true; state._assault_number = 5; state._hostage_count = 2
            state._converted = {["u1"] = make_unit(nil)}
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('_converted = kyohud.hud.assault._state.converted')
        g = lua.globals()
        self.assertEqual(g._converted, 1, "snapshot must count native nil-dead unit as alive (1)")

    def test_refresh_counters_counts_nil_dead_as_alive(self):
        lua, ok = _lua()
        self.assertTrue(ok, "assault.lua must exist")
        if not ok: return
        lua.execute(GROUPAI_SNAPSHOT_FIXTURE)
        lua.execute(UNIT_FIXTURE)
        lua.execute('assert(type(kyohud.hud.assault.snapshot)=="function","snapshot must be a function")')
        lua.execute('assert(type(kyohud.hud.assault._refresh_counters)=="function","_refresh_counters must be a function")')
        lua.execute('''
            local state = managers.groupai:state()
            state._assault_mode = true; state._assault_number = 5; state._hostage_count = 2
            state._converted = {["u1"] = make_unit(nil)}
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('kyohud.hud.assault:_refresh_counters()')
        lua.execute('_converted = kyohud.hud.assault._state.converted')
        g = lua.globals()
        self.assertEqual(g._converted, 1, "_refresh_counters must count native nil-dead unit as alive (1)")

    def test_true_dead_ignored(self):
        lua, ok = _lua()
        self.assertTrue(ok, "assault.lua must exist")
        if not ok: return
        lua.execute(GROUPAI_SNAPSHOT_FIXTURE)
        lua.execute(UNIT_FIXTURE)
        lua.execute('assert(type(kyohud.hud.assault.snapshot)=="function","snapshot must be a function")')
        lua.execute('''
            local state = managers.groupai:state()
            state._assault_mode = true; state._assault_number = 5; state._hostage_count = 2
            state._converted = {["u1"] = make_unit(true)}
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('_converted = kyohud.hud.assault._state.converted')
        g = lua.globals()
        self.assertEqual(g._converted, 0, "snapshot must ignore true-dead unit (0)")

    def test_snapshot_nil_dead_mixed_with_true_dead(self):
        lua, ok = _lua()
        self.assertTrue(ok, "assault.lua must exist")
        if not ok: return
        lua.execute(GROUPAI_SNAPSHOT_FIXTURE)
        lua.execute(UNIT_FIXTURE)
        lua.execute('assert(type(kyohud.hud.assault.snapshot)=="function","snapshot must be a function")')
        lua.execute('''
            local state = managers.groupai:state()
            state._assault_mode = true; state._assault_number = 5; state._hostage_count = 2
            state._converted = {
                ["u1"] = make_unit(nil),
                ["u2"] = make_unit(nil),
                ["u3"] = make_unit(true),
            }
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('_converted = kyohud.hud.assault._state.converted')
        g = lua.globals()
        self.assertEqual(g._converted, 2, "snapshot must count 2 nil-dead units and ignore 1 true-dead unit")

    def test_snapshot_throw_nil_dead_recovery(self):
        lua, ok = _lua()
        self.assertTrue(ok, "assault.lua must exist")
        if not ok: return
        lua.execute(GROUPAI_SNAPSHOT_FIXTURE)
        lua.execute(UNIT_FIXTURE)
        lua.execute('assert(type(kyohud.hud.assault.snapshot)=="function","snapshot must be a function")')
        lua.execute('''
            local state = managers.groupai:state()
            state._assault_mode = true; state._assault_number = 5; state._hostage_count = 2
            state._converted = {["u1"] = make_unit(nil)}
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('_converted_normal = kyohud.hud.assault._state.converted')
        lua.execute('''
            local state = managers.groupai:state()
            state._converted["u1"].character_damage = function() error("unavailable") end
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('_converted_throw = kyohud.hud.assault._state.converted')
        lua.execute('''
            local state = managers.groupai:state()
            state._converted["u1"].character_damage = function() return {dead = function() return nil end} end
        ''')
        lua.execute('kyohud.hud.assault:snapshot(managers.hud)')
        lua.execute('_converted_recovery = kyohud.hud.assault._state.converted')
        g = lua.globals()
        self.assertEqual(g._converted_normal, 1, "normal: nil-dead must be counted as alive (1)")
        self.assertIsNone(g._converted_throw, "throw: converted must be nil (unknown)")
        self.assertEqual(g._converted_recovery, 1, "recovery: nil-dead must be counted as alive (1)")

if __name__ == '__main__':
    unittest.main()
