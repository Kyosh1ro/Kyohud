"""LOT4c -- hud/equipment.lua: deployables snapshot via refresh/get_snapshot (RED vertical slice).

Scope: local two-selection deployables snapshot via kyohud.hud.equipment:refresh(managers.hud)
and :get_snapshot() returning detached {deployables={[equipment_id]={equipment_id,
quantities={{raw, known}, ...}}}, selected_index, selected_effective}.

Native shaped fixture: managers.player._equipment.selections with opaque digest tokens;
Application:digest_value wraps/unwraps; PM:selected_equipment returns nil when all
sub-quantities of selected entry exhausted; PM:get_equipment_amount decodes after
presence check (returns 0 for absent, must distinguish from present-zero).

Stable live player unit + managers.player:player_unit(), HUD manager instance,
local session peer via managers.network:session():local_peer():id().

PlayerManager class with __index metatable; methods on class to allow later PostHooks.

Proposed minimal API:
  kyohud.hud.equipment:refresh(managers.hud)
  kyohud.hud.equipment:get_snapshot()

Snapshot shape:
  snapshot.deployables[equipment_id] = {equipment_id, quantities={{raw, known}, ...}}
  snapshot.selected_index    -- native numeric index (always present if set)
  snapshot.selected_effective -- equipment_id of usable selected entry, or nil

Four focused tests:
1. Two selections trip_mine [3,2] and doctor_bag [1] remain independent ordered
   stocks; doctor_bag becomes [0], refresh reflects it.
2. selected_index retained but effective nil on exhausted selected entry;
   native accepted selection change selects other; refused selection of exhausted
   next entry preserves actual index/effective.
3. Snapshot detached nested quantities; invalid raw NaN/infinity become
   unknown (known=false) not 0; negative raw preserved known=false then restored;
   missing selection not invented zero. At most TWO equipment entries per fixture.
4. Replacing player_unit identity yields fresh data; removing doctor_bag yields
   snapshot without old entry (no inherited entry after removal).

RED state: lua/hud/equipment.lua does not exist yet. Tests that depend on the
production chunk must fail with an explicit message, not FileNotFoundError.
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
EQUIPMENT_PATH = ROOT / "lua" / "hud" / "equipment.lua"

NATIVE_EQUIPMENT_FIXTURE = r'''
-- Native equipment fixture: Application:digest_value opaque tokens,
-- managers.player._equipment.selections, PM helpers.
-- Modeled on lib/managers/playermanager.lua:4141-4369.

Application = Application or {}
function Application:digest_value(value, do_digest)
    if do_digest then
        return {_ky_d = true, v = value}
    else
        if type(value) == "table" and value._ky_d then
            return value.v
        elseif type(value) == "number" then
            return value
        end
        return 0
    end
end

PlayerManager = PlayerManager or {}

function PlayerManager:_native_set_equipment(equipment_id, quantities)
    local amount = {}
    for _, q in ipairs(quantities) do
        table.insert(amount, Application:digest_value(q, true))
    end
    for i, sel in ipairs(self._equipment.selections) do
        if sel.equipment == equipment_id then
            self._equipment.selections[i] = {equipment = equipment_id, amount = amount}
            return i
        end
    end
    table.insert(self._equipment.selections,
        {equipment = equipment_id, amount = amount})
    return #self._equipment.selections
end

function PlayerManager:_native_remove_equipment(equipment_id)
    for i, sel in ipairs(self._equipment.selections) do
        if sel.equipment == equipment_id then
            table.remove(self._equipment.selections, i)
            return
        end
    end
end

function PlayerManager:_native_replace_equipment_table()
    local old = self._equipment
    local new_selections = {}
    for _, sel in ipairs(old.selections) do
        local new_amount = {}
        for _, tok in ipairs(sel.amount) do
            table.insert(new_amount, tok)
        end
        table.insert(new_selections,
            {equipment = sel.equipment, amount = new_amount})
    end
    self._equipment = {selections = new_selections, selected_index = old.selected_index}
end

function PlayerManager:has_equipment(equipment)
    for _, sel in ipairs(self._equipment.selections) do
        if sel.equipment == equipment then return true end
    end
    return false
end

function PlayerManager:get_equipment_amount(equipment, slot)
    for _, sel in ipairs(self._equipment.selections) do
        if sel.equipment == equipment then
            return Application:digest_value(sel.amount[slot or 1], false)
        end
    end
    return 0
end

function PlayerManager:selected_equipment()
    local idx = self._equipment.selected_index
    if not idx then return nil end
    local sel = self._equipment.selections[idx]
    if not sel or not sel.amount then return nil end
    for i = 1, #sel.amount do
        if Application:digest_value(sel.amount[i], false) > 0 then
            return sel
        end
    end
    return nil
end

function PlayerManager:select_next_item()
    if not self._equipment.selected_index then return end
    local n = #self._equipment.selections
    if n == 0 then return end
    local new_idx = (self._equipment.selected_index % n) + 1
    local sel = self._equipment.selections[new_idx]
    if not sel then return end
    for i = 1, #sel.amount do
        if Application:digest_value(sel.amount[i], false) > 0 then
            self._equipment.selected_index = new_idx
            return
        end
    end
end

function PlayerManager:player_unit() return player_unit end

managers.player = setmetatable({_equipment = {selections = {}, selected_index = nil}}, {__index = PlayerManager})

player_unit = {_alive = true}

managers.network = managers.network or {}
native_session = {}
native_local_peer = {_id = 1}
function native_local_peer:id() return self._id end
function native_session:local_peer() return native_local_peer end
function managers.network:session() return native_session end
'''

STUBS = '''
kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end
kyohud.settings = kyohud.settings or {}
if kyohud.settings.enable_hud_foundation == nil then
    kyohud.settings.enable_hud_foundation = false
end
kyohud.hud = kyohud.hud or {}

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
HUDManager.PLAYER_PANEL = 1
HUDManager.update = function() end
HUDManager.init_finalize = function() end
HUDManager._setup_player_info_hud_pd2 = function() end
HUDManager.resolution_changed = function() end
HUDManager.set_disabled = function() end
HUDManager.set_enabled = function() end
HUDManager.set_freeflight_disabled = function() end
HUDManager.set_freeflight_enabled = function() end
HUDManager.destroy = function() end

managers = managers or {}
managers.hud = setmetatable({_teammate_panels={}}, {__index=HUDManager})

RequiredScript = "lib/managers/playermanager"

tweak_data = tweak_data or {}
'''


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua(setup=None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute(NATIVE_EQUIPMENT_FIXTURE)
    if setup:
        lua.execute(setup)
    src = _read(EQUIPMENT_PATH)
    exists = src is not None
    if exists:
        lua.execute(src)
    return lua, exists


def _check_api(lua, test_case):
    g = lua.globals()
    if g._missing_api:
        test_case.fail("RED: kyohud.hud.equipment:refresh and :get_snapshot must exist")
        return False
    return True


class EquipmentFileExistsTests(unittest.TestCase):
    def test_equipment_chunk_exists(self):
        self.assertTrue(EQUIPMENT_PATH.is_file(),
            "RED: lua/hud/equipment.lua must exist (production chunk missing)")


class EquipmentIndependentOrderedQuantitiesTests(unittest.TestCase):
    """Test 1 -- two selections with independent ordered stocks."""

    def test_two_selections_independent_ordered_stocks(self):
        """trip_mine [3,2] and doctor_bag [1] are independent ordered stocks;
        after doctor_bag becomes [0], refresh reflects it and trip_mine unchanged."""
        setup = '''
            managers.player:_native_set_equipment("trip_mine", {3, 2})
            managers.player:_native_set_equipment("doctor_bag", {1})
            managers.player._equipment.selected_index = 1
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/equipment.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local EQ = kyohud.hud.equipment
            if not EQ or not EQ.refresh or not EQ.get_snapshot then
                _missing_api = true
                return
            end
            _missing_api = false
            EQ:refresh(managers.hud)
            local snap1 = EQ:get_snapshot()

            _tm_id1 = snap1.deployables.trip_mine.equipment_id
            _tm_n1 = #snap1.deployables.trip_mine.quantities
            _tm_q1_1 = snap1.deployables.trip_mine.quantities[1].raw
            _tm_q1_2 = snap1.deployables.trip_mine.quantities[2].raw

            _db_id1 = snap1.deployables.doctor_bag.equipment_id
            _db_n1 = #snap1.deployables.doctor_bag.quantities
            _db_q1_1 = snap1.deployables.doctor_bag.quantities[1].raw

            -- doctor_bag becomes 0
            managers.player:_native_set_equipment("doctor_bag", {0})
            EQ:refresh(managers.hud)
            local snap2 = EQ:get_snapshot()

            _tm_q2_1 = snap2.deployables.trip_mine.quantities[1].raw
            _tm_q2_2 = snap2.deployables.trip_mine.quantities[2].raw
            _db_q2_1 = snap2.deployables.doctor_bag.quantities[1].raw
        ''')
        if not _check_api(lua, self):
            return
        g = lua.globals()
        self.assertEqual(g._tm_id1, "trip_mine",
            "RED: trip_mine equipment_id must be 'trip_mine'")
        self.assertEqual(int(g._tm_n1), 2,
            "RED: trip_mine must have 2 ordered sub-quantities")
        self.assertEqual(float(g._tm_q1_1), 3.0,
            "RED: trip_mine quantities[1].raw = 3")
        self.assertEqual(float(g._tm_q1_2), 2.0,
            "RED: trip_mine quantities[2].raw = 2")
        self.assertEqual(g._db_id1, "doctor_bag",
            "RED: doctor_bag equipment_id must be 'doctor_bag'")
        self.assertEqual(int(g._db_n1), 1,
            "RED: doctor_bag must have 1 sub-quantity")
        self.assertEqual(float(g._db_q1_1), 1.0,
            "RED: doctor_bag quantities[1].raw = 1")
        self.assertEqual(float(g._tm_q2_1), 3.0,
            "RED: trip_mine quantities[1] unchanged after doctor_bag change")
        self.assertEqual(float(g._tm_q2_2), 2.0,
            "RED: trip_mine quantities[2] unchanged after doctor_bag change")
        self.assertEqual(float(g._db_q2_1), 0.0,
            "RED: doctor_bag quantities[1].raw = 0 after stock becomes 0")


class EquipmentSelectedIndexVsEffectiveTests(unittest.TestCase):
    """Test 2 -- selected_index retained but effective nil on exhausted entry."""

    def test_selected_index_retained_effective_nil_then_native_change(self):
        """selected_index=1 with all quantities 0 -> selected_effective=nil;
        then native select_next_item moves to doctor_bag -> effective=doctor_bag;
        then both exhausted -> select_next_item refused, index/effective preserved."""
        setup = '''
            managers.player:_native_set_equipment("trip_mine", {0, 0})
            managers.player:_native_set_equipment("doctor_bag", {1})
            managers.player._equipment.selected_index = 1
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/equipment.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local EQ = kyohud.hud.equipment
            if not EQ or not EQ.refresh or not EQ.get_snapshot then
                _missing_api = true
                return
            end
            _missing_api = false

            -- Verify native selected_equipment() returns nil when exhausted
            _native_sel_eq = managers.player:selected_equipment()

            EQ:refresh(managers.hud)
            local snap1 = EQ:get_snapshot()
            _sel_idx1 = snap1.selected_index
            _sel_eff1 = snap1.selected_effective

            -- Native accepted selection change
            managers.player:select_next_item()
            _native_sel_after = managers.player:selected_equipment()
            _native_sel_id = _native_sel_after and _native_sel_after.equipment

            EQ:refresh(managers.hud)
            local snap2 = EQ:get_snapshot()
            _sel_idx2 = snap2.selected_index
            _sel_eff2 = snap2.selected_effective

            -- Exhaust doctor_bag too, so both entries have 0 quantities
            managers.player:_native_set_equipment("doctor_bag", {0})
            managers.player._equipment.selected_index = 1
            _native_sel_both_exhausted = managers.player:selected_equipment()

            managers.player:select_next_item()
            _sel_idx3 = managers.player._equipment.selected_index
            EQ:refresh(managers.hud)
            local snap3 = EQ:get_snapshot()
            _sel_idx3_snap = snap3.selected_index
            _sel_eff3 = snap3.selected_effective
        ''')
        if not _check_api(lua, self):
            return
        g = lua.globals()
        self.assertIsNone(g._native_sel_eq,
            "precondition: native selected_equipment() nil when all quantities 0")
        self.assertEqual(float(g._sel_idx1), 1.0,
            "RED: selected_index retained as 1 even when entry exhausted")
        self.assertIsNone(g._sel_eff1,
            "RED: selected_effective must be nil when selected entry exhausted")
        self.assertIsNotNone(g._native_sel_after,
            "precondition: native selected_equipment() non-nil after select_next_item")
        self.assertEqual(g._native_sel_id, "doctor_bag",
            "precondition: native selected_equipment().equipment = 'doctor_bag'")
        self.assertEqual(float(g._sel_idx2), 2.0,
            "RED: after select_next_item, selected_index = 2")
        self.assertEqual(g._sel_eff2, "doctor_bag",
            "RED: after select_next_item, selected_effective = 'doctor_bag'")
        self.assertIsNone(g._native_sel_both_exhausted,
            "precondition: native selected_equipment() nil when both entries exhausted")
        self.assertEqual(float(g._sel_idx3), 1.0,
            "RED: refused selection of exhausted next entry preserves actual index")
        self.assertEqual(float(g._sel_idx3_snap), 1.0,
            "RED: refused selection of exhausted next entry preserves snapshot index")
        self.assertIsNone(g._sel_eff3,
            "RED: refused selection of exhausted next entry preserves effective nil")


class EquipmentDetachedSnapshotAndInvalidValuesTests(unittest.TestCase):
    """Test 3 -- detached snapshot, invalid raw, missing not invented."""

    def test_detached_snapshot_invalid_raw_and_missing_not_invented(self):
        """Mutating nested quantities must not affect subsequent snapshot;
        NaN/infinity raw become unknown (known=false) not 0;
        negative raw preserved with known=false then restored to valid;
        equipment absent from selections must not appear in snapshot."""
        setup = '''
            managers.player:_native_set_equipment("trip_mine", {0/0, math.huge})
            managers.player:_native_set_equipment("doctor_bag", {-5})
            managers.player._equipment.selected_index = 1
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/equipment.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local EQ = kyohud.hud.equipment
            if not EQ or not EQ.refresh or not EQ.get_snapshot then
                _missing_api = true
                return
            end
            _missing_api = false
            EQ:refresh(managers.hud)
            local snap1 = EQ:get_snapshot()

            -- Invalid values: trip_mine NaN/inf
            _tm_q1_raw = snap1.deployables.trip_mine.quantities[1].raw
            _tm_q1_known = snap1.deployables.trip_mine.quantities[1].known
            _tm_q1_is_nan = (_tm_q1_raw ~= _tm_q1_raw)

            _tm_q2_raw = snap1.deployables.trip_mine.quantities[2].raw
            _tm_q2_known = snap1.deployables.trip_mine.quantities[2].known
            _tm_q2_is_inf = (_tm_q2_raw == math.huge)

            -- Negative: doctor_bag
            _db_q1_raw = snap1.deployables.doctor_bag.quantities[1].raw
            _db_q1_known = snap1.deployables.doctor_bag.quantities[1].known

            -- Missing: ecm_jammer not in selections
            _has_ecm = snap1.deployables.ecm_jammer ~= nil

            -- Restore doctor_bag to valid value
            managers.player:_native_set_equipment("doctor_bag", {1})
            EQ:refresh(managers.hud)
            local snap2 = EQ:get_snapshot()
            _db_q1_raw_restored = snap2.deployables.doctor_bag.quantities[1].raw
            _db_q1_known_restored = snap2.deployables.doctor_bag.quantities[1].known

            -- Detach test: mutate nested quantities (no intervening refresh)
            snap2.deployables.doctor_bag.quantities[1].raw = 9999
            snap2.deployables.trip_mine.quantities[1].known = true
            local snap3 = EQ:get_snapshot()
            _db_q1_raw_after_mutation = snap3.deployables.doctor_bag.quantities[1].raw
            _tm_q1_known_after_mutation = snap3.deployables.trip_mine.quantities[1].known
        ''')
        if not _check_api(lua, self):
            return
        g = lua.globals()
        # NaN: known must be false
        self.assertFalse(bool(g._tm_q1_known),
            "RED: NaN raw must have known=false (unknown), not silently 0")
        self.assertTrue(bool(g._tm_q1_is_nan),
            "RED: NaN raw must remain NaN in snapshot (not replaced with 0)")
        # Infinity: known must be false
        self.assertFalse(bool(g._tm_q2_known),
            "RED: infinity raw must have known=false (unknown)")
        self.assertTrue(bool(g._tm_q2_is_inf),
            "RED: infinity raw must remain math.huge in snapshot")
        # Negative: known must be false
        self.assertFalse(bool(g._db_q1_known),
            "RED: negative raw must have known=false (unknown), not silently 0")
        self.assertEqual(float(g._db_q1_raw), -5.0,
            "RED: negative raw must be preserved as -5, not clamped to 0")
        # Missing: not invented
        self.assertFalse(bool(g._has_ecm),
            "RED: absent equipment must not appear in snapshot as zero")
        # Restored: doctor_bag valid
        self.assertTrue(bool(g._db_q1_known_restored),
            "RED: restored doctor_bag raw must have known=true")
        self.assertEqual(float(g._db_q1_raw_restored), 1.0,
            "RED: restored doctor_bag raw must be 1.0")
        # Detached: mutation must not affect subsequent snapshot
        self.assertEqual(float(g._db_q1_raw_after_mutation), 1.0,
            "RED: mutating snapshot raw must not affect subsequent snapshot")
        self.assertFalse(bool(g._tm_q1_known_after_mutation),
            "RED: mutating snapshot known must not affect subsequent snapshot")


class EquipmentIdentityChangeTests(unittest.TestCase):
    """Test 4 -- replacing equipment table yields fresh data, no old after removal."""

    def test_replacing_equipment_table_yields_fresh_data_no_old_entries(self):
        """Replacing player_unit identity then removing doctor_bag yields snapshot
        without old entry (no inherited entry after removal)."""
        setup = '''
            managers.player:_native_set_equipment("trip_mine", {3, 2})
            managers.player:_native_set_equipment("doctor_bag", {1})
            managers.player._equipment.selected_index = 1
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/equipment.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local EQ = kyohud.hud.equipment
            if not EQ or not EQ.refresh or not EQ.get_snapshot then
                _missing_api = true
                return
            end
            _missing_api = false
            EQ:refresh(managers.hud)
            local snap1 = EQ:get_snapshot()
            _before_n = 0
            for _ in pairs(snap1.deployables) do _before_n = _before_n + 1 end

            -- Replace player_unit identity (new table)
            player_unit = {_alive = true}
            EQ:refresh(managers.hud)
            local snap2 = EQ:get_snapshot()
            _after_player_unit_replace_n = 0
            for _ in pairs(snap2.deployables) do _after_player_unit_replace_n = _after_player_unit_replace_n + 1 end
            _after_player_unit_replace_tm = snap2.deployables.trip_mine
                and snap2.deployables.trip_mine.quantities[1].raw
            _after_player_unit_replace_db = snap2.deployables.doctor_bag
                and snap2.deployables.doctor_bag.quantities[1].raw

            -- Equipment TABLE replacement (replace the _equipment table itself)
            managers.player:_native_replace_equipment_table()
            EQ:refresh(managers.hud)
            local snap2b = EQ:get_snapshot()
            _after_table_replace_n = 0
            for _ in pairs(snap2b.deployables) do _after_table_replace_n = _after_table_replace_n + 1 end
            _after_table_replace_tm = snap2b.deployables.trip_mine
                and snap2b.deployables.trip_mine.quantities[1].raw
            _after_table_replace_db = snap2b.deployables.doctor_bag
                and snap2b.deployables.doctor_bag.quantities[1].raw

            -- Detached snapshot: mutate snap2 before removal
            snap2.deployables.trip_mine.quantities[1].raw = 9999
            snap2.deployables.doctor_bag.quantities[1].known = true

            -- Remove doctor_bag entry
            managers.player:_native_remove_equipment("doctor_bag")
            EQ:refresh(managers.hud)
            local snap3 = EQ:get_snapshot()
            _after_remove_has_tm = snap3.deployables.trip_mine ~= nil
            _after_remove_has_db = snap3.deployables.doctor_bag ~= nil
            _after_remove_n = 0
            for _ in pairs(snap3.deployables) do _after_remove_n = _after_remove_n + 1 end
            _after_mutation_tm_raw = snap3.deployables.trip_mine
                and snap3.deployables.trip_mine.quantities[1].raw
        ''')
        if not _check_api(lua, self):
            return
        g = lua.globals()
        self.assertEqual(int(g._before_n), 2,
            "precondition: two deployable entries before player_unit replace")
        self.assertEqual(int(g._after_player_unit_replace_n), 2,
            "RED: after replacing player_unit identity, snapshot must have 2 entries")
        self.assertEqual(float(g._after_player_unit_replace_tm), 3.0,
            "RED: trip_mine quantities[1].raw = 3 after player_unit replace (fresh data)")
        self.assertEqual(float(g._after_player_unit_replace_db), 1.0,
            "RED: doctor_bag quantities[1].raw = 1 after player_unit replace (fresh data)")
        self.assertEqual(int(g._after_table_replace_n), 2,
            "RED: after replacing equipment table, snapshot must have 2 entries")
        self.assertEqual(float(g._after_table_replace_tm), 3.0,
            "RED: trip_mine quantities[1].raw = 3 after equipment table replace (fresh data)")
        self.assertEqual(float(g._after_table_replace_db), 1.0,
            "RED: doctor_bag quantities[1].raw = 1 after equipment table replace (fresh data)")
        self.assertEqual(float(g._after_mutation_tm_raw), 3.0,
            "RED: mutating snapshot raw must not affect subsequent snapshot after table replace")
        self.assertTrue(bool(g._after_remove_has_tm),
            "RED: trip_mine still present after removing doctor_bag")
        self.assertFalse(bool(g._after_remove_has_db),
            "RED: doctor_bag must be absent from snapshot after removal (no inherited entry)")
        self.assertEqual(int(g._after_remove_n), 1,
            "RED: only 1 deployable entry after removing doctor_bag")


class EquipmentEngineBoundaryFailureTests(unittest.TestCase):
    """Test 5 -- engine boundary failures: refresh must not throw, no stale data."""

    def test_engine_boundary_failures(self):
        """For each engine boundary failure, refresh must not throw and next
        snapshot must not expose stale deployables/source_known true."""

        failure_modes = [
            ("pm_player_unit_throwing",
                "function PlayerManager:player_unit() error('player_unit failed') end",
                "function PlayerManager:player_unit() return player_unit end"),
            ("network_session_throwing",
                "function managers.network:session() error('session failed') end",
                "function managers.network:session() return native_session end"),
            ("local_peer_throwing",
                "function native_session:local_peer() error('local_peer failed') end",
                "function native_session:local_peer() return native_local_peer end"),
            ("application_digest_throwing",
                "_orig_digest = Application.digest_value; "
                "function Application:digest_value() error('digest failed') end",
                "Application.digest_value = _orig_digest"),
            ("missing_managers",
                "_saved_managers_hud = managers.hud; "
                "_saved_managers_player = managers.player; "
                "managers.hud = nil; managers.player = nil",
                "managers.hud = _saved_managers_hud; "
                "managers.player = _saved_managers_player"),
        ]

        for mode_name, break_code, restore_code in failure_modes:
            with self.subTest(mode=mode_name):
                setup = '''
                    managers.player:_native_set_equipment("trip_mine", {3, 2})
                    managers.player:_native_set_equipment("doctor_bag", {1})
                    managers.player._equipment.selected_index = 1
                '''
                lua, ok = _lua(setup=setup)
                self.assertTrue(ok,
                    "RED: lua/hud/equipment.lua must exist (production chunk missing)")
                if not ok:
                    return
                lua.execute('''
                    local EQ = kyohud.hud.equipment
                    if not EQ or not EQ.refresh or not EQ.get_snapshot then
                        _missing_api = true
                        return
                    end
                    _missing_api = false
                    EQ:refresh(managers.hud)
                    local snap1 = EQ:get_snapshot()
                    _valid_n = 0
                    for _ in pairs(snap1.deployables) do _valid_n = _valid_n + 1 end
                ''')
                if not _check_api(lua, self):
                    return
                g = lua.globals()
                self.assertEqual(int(g._valid_n), 2,
                    "precondition: valid snapshot has 2 deployable entries")

                lua.execute("_hud_ref = managers.hud")

                lua.execute(break_code)

                refresh_ok = True
                try:
                    lua.execute('''
                        local EQ = kyohud.hud.equipment
                        EQ:refresh(_hud_ref)
                    ''')
                except Exception:
                    refresh_ok = False
                self.assertTrue(refresh_ok,
                    f"RED: refresh must not throw on {mode_name}")

                lua.execute('''
                    local EQ = kyohud.hud.equipment
                    local snap2 = EQ:get_snapshot()
                    _after_n = 0
                    for _ in pairs(snap2.deployables or {}) do
                        _after_n = _after_n + 1
                    end
                    _after_source_known = snap2.source_known or false
                ''')
                g = lua.globals()
                self.assertEqual(int(g._after_n), 0,
                    f"RED: after {mode_name}, snapshot must not expose stale deployables")
                self.assertFalse(bool(g._after_source_known),
                    f"RED: after {mode_name}, snapshot must not expose stale source_known true")

                lua.execute(restore_code)

                if mode_name == "missing_managers":
                    lua.execute('''
                        managers.player:_native_set_equipment("trip_mine", {3, 2})
                        managers.player:_native_set_equipment("doctor_bag", {1})
                        managers.player._equipment.selected_index = 1
                    ''')

                lua.execute('''
                    local EQ = kyohud.hud.equipment
                    EQ:refresh(_hud_ref)
                    local snap3 = EQ:get_snapshot()
                    _recovered_n = 0
                    for _ in pairs(snap3.deployables or {}) do
                        _recovered_n = _recovered_n + 1
                    end
                    _recovered_source_known = snap3.source_known or false
                ''')
                g = lua.globals()
                self.assertEqual(int(g._recovered_n), 2,
                    f"RED: after {mode_name} restore, snapshot must have 2 deployable entries")
                self.assertTrue(bool(g._recovered_source_known),
                    f"RED: after {mode_name} restore, source_known must be true")


class EquipmentInvalidSelectedIndexAndSourceGenerationTests(unittest.TestCase):
    """Test 6 -- invalid selected_index and source_generation tracking."""

    def test_invalid_selected_index_and_source_generation(self):
        """Invalid selected_index NaN/infinity/1.5 -> nil/effective nil without throw;
        replace session with same peer id advances source_generation;
        unchanged repeated refresh must not advance source_generation."""
        setup = '''
            managers.player:_native_set_equipment("trip_mine", {3, 2})
            managers.player:_native_set_equipment("doctor_bag", {1})
            managers.player._equipment.selected_index = 1
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/equipment.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local EQ = kyohud.hud.equipment
            if not EQ or not EQ.refresh or not EQ.get_snapshot then
                _missing_api = true
                return
            end
            _missing_api = false

            local EQ = kyohud.hud.equipment

            _invalid_results = {}
            local invalid_indices = {0/0, math.huge, 1.5}
            for _, idx in ipairs(invalid_indices) do
                managers.player._equipment.selected_index = idx
                local threw = not pcall(function() EQ:refresh(managers.hud) end)
                local snap = EQ:get_snapshot()
                table.insert(_invalid_results, {
                    threw = threw,
                    idx = snap.selected_index,
                    eff = snap.selected_effective,
                })
            end

            managers.player._equipment.selected_index = 1
            EQ:refresh(managers.hud)
            _gen_baseline = EQ._source_generation or 0

            native_session = {_id = 1}
            function native_session:local_peer() return native_local_peer end
            EQ:refresh(managers.hud)
            _gen_after_session_replace = EQ._source_generation or 0

            EQ:refresh(managers.hud)
            EQ:refresh(managers.hud)
            EQ:refresh(managers.hud)
            _gen_after_repeated = EQ._source_generation or 0
        ''')
        if not _check_api(lua, self):
            return
        g = lua.globals()

        for i in range(3):
            entry = g._invalid_results[i + 1]
            self.assertFalse(bool(entry.threw),
                f"RED: refresh must not throw on invalid selected_index (case {i})")
            self.assertIsNone(entry.idx,
                f"RED: invalid selected_index (case {i}) must produce selected_index nil")
            self.assertIsNone(entry.eff,
                f"RED: invalid selected_index (case {i}) must produce selected_effective nil")

        self.assertGreater(int(g._gen_after_session_replace), int(g._gen_baseline),
            "RED: session replacement with same peer id must advance source_generation")
        self.assertEqual(int(g._gen_after_repeated), int(g._gen_after_session_replace),
            "RED: unchanged repeated refresh must not advance source_generation")


if __name__ == "__main__":
    unittest.main()
