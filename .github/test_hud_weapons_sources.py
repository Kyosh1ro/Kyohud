"""LOT4b sources -- hud/weapons.lua: source tracking, alt/mode edge cases, state guards.

Behavioral tests against the real module focusing on:
- selected nil when equipped_unit missing or equipped_selection outside 1-2
- alt getter nil/throwing edge cases and alt_known field
- protected __index throwing ammo_info isolation
- invalid ammo value sanitization (negative/NaN/infinite)
- source_generation tracking and advancement in snapshot
- ammo_base override detection for fresh tuple/mode
- manager mismatch isolation (old manager vs current managers.hud)
- turret state nil snapshot and standard recovery

No production edits.
"""
import unittest

from test_hud_weapons import _lua


class SourcesSelectedNilWhenEquippedMissingOrSelected3Tests(unittest.TestCase):
    """selected must be nil when equipped_unit is missing or equipped_selection is 3."""

    def test_selected_nil_when_equipped_unit_missing(self):
        setup = '''
            managers.player.current_state = function(self) return "standard" end
            unit1, base1 = make_weapon("wpn_a")
            base1:_native_set_ammo(30, 25, 120, 150)
            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_equipped(1)
            inventory.equipped_unit = function(self) return nil end
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/weapons.lua must exist")
        if not ok:
            return
        lua.execute('''
            local WPNS = kyohud.hud.weapons
            if not WPNS or not WPNS.refresh or not WPNS.get_snapshot then
                _missing_api = true; return
            end
            _missing_api = false
            WPNS:refresh(managers.hud)
            local snap = WPNS:get_snapshot()
            _selected = snap and snap.selected or nil
        ''')
        g = lua.globals()
        if g._missing_api:
            self.fail("RED: kyohud.hud.weapons API missing")
            return
        self.assertIsNone(g._selected,
            "RED: selected must be nil when equipped_unit is missing")

    def test_selected_nil_when_selected3(self):
        setup = '''
            managers.player.current_state = function(self) return "standard" end
            unit1, base1 = make_weapon("wpn_a")
            base1:_native_set_ammo(30, 25, 120, 150)
            unit2, base2 = make_weapon("wpn_b")
            base2:_native_set_ammo(8, 6, 32, 40)
            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_slot(2, unit2)
            inventory:_native_set_equipped(3)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/weapons.lua must exist")
        if not ok:
            return
        lua.execute('''
            local WPNS = kyohud.hud.weapons
            if not WPNS or not WPNS.refresh or not WPNS.get_snapshot then
                _missing_api = true; return
            end
            _missing_api = false
            WPNS:refresh(managers.hud)
            local snap = WPNS:get_snapshot()
            _selected = snap and snap.selected or nil
        ''')
        g = lua.globals()
        if g._missing_api:
            self.fail("RED: kyohud.hud.weapons API missing")
            return
        self.assertIsNone(g._selected,
            "RED: selected must be nil when equipped_selection is 3 (outside 1-2)")


class SourcesAltGetterEdgeTests(unittest.TestCase):
    """nil alt getter successful means false; throwing getter yields nil/alt_known false."""

    def test_nil_alt_getter_means_false(self):
        setup = '''
            managers.player.current_state = function(self) return "standard" end
            unit1, base1 = make_weapon("wpn_a")
            base1:_native_set_ammo(30, 25, 120, 150)
            base1:_native_set_fire_mode("auto")
            base1:_native_set_alt_fire(nil)
            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_equipped(1)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/weapons.lua must exist")
        if not ok:
            return
        lua.execute('''
            local WPNS = kyohud.hud.weapons
            if not WPNS or not WPNS.refresh or not WPNS.get_snapshot then
                _missing_api = true; return
            end
            _missing_api = false
            WPNS:refresh(managers.hud)
            local snap = WPNS:get_snapshot()
            _alt = snap.slots[1].alt_fire
            _alt_known = snap.slots[1].alt_known
        ''')
        g = lua.globals()
        if g._missing_api:
            self.fail("RED: kyohud.hud.weapons API missing")
            return
        self.assertFalse(bool(g._alt),
            "RED: nil alt getter successful must normalize to false")
        self.assertTrue(bool(g._alt_known),
            "RED: nil alt getter successful must yield alt_known true")

    def test_throwing_alt_getter_yields_false(self):
        setup = '''
            managers.player.current_state = function(self) return "standard" end
            unit1, base1 = make_weapon("wpn_a")
            base1:_native_set_ammo(30, 25, 120, 150)
            base1:_native_set_fire_mode("auto")
            base1.alt_fire_active = function() error("alt boom") end
            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_equipped(1)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/weapons.lua must exist")
        if not ok:
            return
        lua.execute('''
            local WPNS = kyohud.hud.weapons
            if not WPNS or not WPNS.refresh or not WPNS.get_snapshot then
                _missing_api = true; return
            end
            _missing_api = false
            local ok2, err2 = pcall(function()
                WPNS:refresh(managers.hud)
            end)
            _refresh_ok = ok2
            if ok2 then
                local snap = WPNS:get_snapshot()
                _alt = snap.slots[1].alt_fire
                _alt_known = snap.slots[1].alt_known
            end
        ''')
        g = lua.globals()
        if g._missing_api:
            self.fail("RED: kyohud.hud.weapons API missing")
            return
        self.assertTrue(bool(g._refresh_ok),
            "RED: throwing alt getter must not crash refresh")
        self.assertIsNone(g._alt,
            "RED: throwing alt getter must yield nil")
        self.assertFalse(bool(g._alt_known),
            "RED: throwing alt getter must yield alt_known false")


class SourcesProtectedIndexThrowingAmmoInfoTests(unittest.TestCase):
    """protected __index throwing base.ammo_info must not escape refresh; counters nil."""

    def test_throwing_ammo_info_via_metatable(self):
        setup = '''
            managers.player.current_state = function(self) return "standard" end
            unit1, base1 = make_weapon("wpn_a")
            local broken = setmetatable({}, {
                __index = function(t, k)
                    if k == "ammo_info" then
                        error("ammo_info boom")
                    end
                    return rawget(t, k)
                end
            })
            broken.fire_mode = function() return "auto" end
            broken.alt_fire_active = function() return false end
            unit1.base = function() return broken end
            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_equipped(1)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/weapons.lua must exist")
        if not ok:
            return
        lua.execute('''
            local WPNS = kyohud.hud.weapons
            if not WPNS or not WPNS.refresh or not WPNS.get_snapshot then
                _missing_api = true; return
            end
            _missing_api = false
            local ok2, err2 = pcall(function()
                WPNS:refresh(managers.hud)
            end)
            _refresh_ok = ok2
            if ok2 then
                local snap = WPNS:get_snapshot()
                _clip = snap.slots[1].current_clip
                _total = snap.slots[1].total_raw
                _max_clip = snap.slots[1].max_clip
                _max_total = snap.slots[1].max_total
            end
        ''')
        g = lua.globals()
        if g._missing_api:
            self.fail("RED: kyohud.hud.weapons API missing")
            return
        self.assertTrue(bool(g._refresh_ok),
            "RED: throwing ammo_info must not escape refresh")
        self.assertIsNone(g._clip,
            "RED: current_clip must be nil when ammo_info throws")
        self.assertIsNone(g._total,
            "RED: total_raw must be nil when ammo_info throws")
        self.assertIsNone(g._max_clip,
            "RED: max_clip must be nil when ammo_info throws")
        self.assertIsNone(g._max_total,
            "RED: max_total must be nil when ammo_info throws")


class SourcesInvalidAmmoValuesNilTests(unittest.TestCase):
    """Invalid negative/NaN/infinite ammo values must become nil."""

    def test_invalid_ammo_values_nil(self):
        setup = '''
            managers.player.current_state = function(self) return "standard" end
            unit1, base1 = make_weapon("wpn_neg")
            base1:_native_set_ammo(-5, -3, -10, -20)
            unit2, base2 = make_weapon("wpn_nan")
            base2:_native_set_ammo(0/0, 0/0, 0/0, 0/0)
            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_slot(2, unit2)
            inventory:_native_set_equipped(1)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/weapons.lua must exist")
        if not ok:
            return
        lua.execute('''
            local WPNS = kyohud.hud.weapons
            if not WPNS or not WPNS.refresh or not WPNS.get_snapshot then
                _missing_api = true; return
            end
            _missing_api = false
            unit3, base3 = make_weapon("wpn_inf")
            base3:_native_set_ammo(math.huge, math.huge, math.huge, math.huge)
            inventory:_native_set_slot(3, unit3)
            WPNS:refresh(managers.hud)
            local snap = WPNS:get_snapshot()
            _s1_clip = snap.slots[1].current_clip
            _s1_total = snap.slots[1].total_raw
            _s2_clip = snap.slots[2].current_clip
            _s2_total = snap.slots[2].total_raw
        ''')
        g = lua.globals()
        if g._missing_api:
            self.fail("RED: kyohud.hud.weapons API missing")
            return
        self.assertIsNone(g._s1_clip,
            "RED: negative current_clip must be nil")
        self.assertIsNone(g._s1_total,
            "RED: negative total_raw must be nil")
        self.assertIsNone(g._s2_clip,
            "RED: NaN current_clip must be nil")
        self.assertIsNone(g._s2_total,
            "RED: NaN total_raw must be nil")


class SourcesGenerationStableAndAdvancesTests(unittest.TestCase):
    """source_generation stable across equal refresh and advances when same slot weapon replaced."""

    def test_source_generation_advances(self):
        setup = '''
            managers.player.current_state = function(self) return "standard" end
            unit1, base1 = make_weapon("wpn_a")
            base1:_native_set_ammo(30, 25, 120, 150)
            base1:_native_set_fire_mode("auto")
            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_equipped(1)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/weapons.lua must exist")
        if not ok:
            return
        lua.execute('''
            local WPNS = kyohud.hud.weapons
            if not WPNS or not WPNS.refresh or not WPNS.get_snapshot then
                _missing_api = true; return
            end
            _missing_api = false
            WPNS:refresh(managers.hud)
            local snap1 = WPNS:get_snapshot()
            _gen1 = snap1 and snap1.source_generation or nil
            WPNS:refresh(managers.hud)
            local snap2 = WPNS:get_snapshot()
            _gen2 = snap2 and snap2.source_generation or nil
            unit_new, base_new = make_weapon("wpn_replaced")
            base_new:_native_set_ammo(20, 15, 80, 100)
            inventory:_native_set_slot(1, unit_new)
            WPNS:refresh(managers.hud)
            local snap3 = WPNS:get_snapshot()
            _gen3 = snap3 and snap3.source_generation or nil
        ''')
        g = lua.globals()
        if g._missing_api:
            self.fail("RED: kyohud.hud.weapons API missing")
            return
        self.assertIsNotNone(g._gen1,
            "RED: snapshot must expose source_generation")
        self.assertIsNotNone(g._gen2,
            "RED: snapshot must expose source_generation after second refresh")
        self.assertIsNotNone(g._gen3,
            "RED: snapshot must expose source_generation after weapon replacement")
        if g._gen1 is not None and g._gen2 is not None and g._gen3 is not None:
            gen1 = float(g._gen1)
            gen2 = float(g._gen2)
            gen3 = float(g._gen3)
            self.assertEqual(gen2, gen1,
                "RED: source_generation must remain equal across equal refresh")
            self.assertGreater(gen3, gen2,
                "RED: source_generation must advance when same slot weapon replaced")


class SourcesSameUnitAmmoBaseOverrideTests(unittest.TestCase):
    """Same-unit ammo_base override change gets fresh tuple/mode."""

    def test_ammo_base_override_fresh_tuple(self):
        setup = '''
            managers.player.current_state = function(self) return "standard" end
            unit1, base1 = make_weapon("wpn_a")
            base1:_native_set_ammo(30, 25, 120, 150)
            base1:_native_set_fire_mode("auto")
            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_equipped(1)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/weapons.lua must exist")
        if not ok:
            return
        lua.execute('''
            local WPNS = kyohud.hud.weapons
            if not WPNS or not WPNS.refresh or not WPNS.get_snapshot then
                _missing_api = true; return
            end
            _missing_api = false
            WPNS:refresh(managers.hud)
            local snap1 = WPNS:get_snapshot()
            _clip1 = snap1.slots[1].current_clip
            _mode1 = snap1.slots[1].fire_mode
            _gen1 = snap1 and snap1.source_generation or nil
            local new_base = RaycastWeaponBase.new("wpn_a")
            new_base:_native_set_ammo(20, 10, 60, 80)
            new_base:_native_set_fire_mode("burst")
            base1.ammo_info = function() return new_base:ammo_info() end
            base1.fire_mode = function() return new_base:fire_mode() end
            base1.ammo_base = function() return new_base end
            WPNS:refresh(managers.hud)
            local snap2 = WPNS:get_snapshot()
            _clip2 = snap2.slots[1].current_clip
            _mode2 = snap2.slots[1].fire_mode
            _gen2 = snap2 and snap2.source_generation or nil
        ''')
        g = lua.globals()
        if g._missing_api:
            self.fail("RED: kyohud.hud.weapons API missing")
            return
        self.assertEqual(float(g._clip1), 25.0,
            "RED: initial clip = 25")
        self.assertEqual(g._mode1, "auto",
            "RED: initial mode = auto")
        self.assertEqual(float(g._clip2), 10.0,
            "RED: after ammo_base override, clip must be fresh = 10")
        self.assertEqual(g._mode2, "burst",
            "RED: after ammo_base override, mode must be fresh = burst")
        self.assertIsNotNone(g._gen1,
            "RED: snapshot must expose source_generation")
        self.assertIsNotNone(g._gen2,
            "RED: snapshot must expose source_generation after override")
        if g._gen1 is not None and g._gen2 is not None:
            self.assertGreater(float(g._gen2), float(g._gen1),
                "RED: source_generation must increase on ammo_base override")


class SourcesManagerMismatchIgnoredTests(unittest.TestCase):
    """Manager mismatch ignored: refresh old manager after managers.hud replaced should not overwrite new snapshot."""

    def test_manager_mismatch_ignored(self):
        setup = '''
            managers.player.current_state = function(self) return "standard" end
            unit1, base1 = make_weapon("wpn_a")
            base1:_native_set_ammo(30, 25, 120, 150)
            base1:_native_set_fire_mode("auto")
            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_equipped(1)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/weapons.lua must exist")
        if not ok:
            return
        lua.execute('''
            local WPNS = kyohud.hud.weapons
            if not WPNS or not WPNS.refresh or not WPNS.get_snapshot then
                _missing_api = true; return
            end
            _missing_api = false
            local old_manager = managers.hud
            WPNS:refresh(old_manager)
            local snap1 = WPNS:get_snapshot()
            _clip1 = snap1 and snap1.slots[1].current_clip or nil
            base1:_native_set_ammo(30, 10, 120, 150)
            managers.hud = setmetatable({_teammate_panels={}}, {__index=HUDManager})
            WPNS:refresh(old_manager)
            local snap2 = WPNS:get_snapshot()
            _clip2 = snap2 and snap2.slots[1].current_clip or nil
        ''')
        g = lua.globals()
        if g._missing_api:
            self.fail("RED: kyohud.hud.weapons API missing")
            return
        self.assertEqual(float(g._clip1), 25.0,
            "RED: initial refresh gives clip = 25")
        self.assertEqual(float(g._clip2), 25.0,
            "RED: refresh with old manager after managers.hud replaced must not overwrite snapshot")


class SourcesTurretNilThenRecoveryTests(unittest.TestCase):
    """current_state turret returns nil snapshot then standard recovery."""

    def test_turret_nil_then_standard_recovery(self):
        setup = '''
            managers.player.current_state = function(self) return "standard" end
            unit1, base1 = make_weapon("wpn_a")
            base1:_native_set_ammo(30, 25, 120, 150)
            base1:_native_set_fire_mode("auto")
            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_equipped(1)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/weapons.lua must exist")
        if not ok:
            return
        lua.execute('''
            local WPNS = kyohud.hud.weapons
            if not WPNS or not WPNS.refresh or not WPNS.get_snapshot then
                _missing_api = true; return
            end
            _missing_api = false
            WPNS:refresh(managers.hud)
            local snap1 = WPNS:get_snapshot()
            _clip1 = snap1 and snap1.slots[1].current_clip or nil
            managers.player.current_state = function(self) return "turret" end
            WPNS:refresh(managers.hud)
            local snap2 = WPNS:get_snapshot()
            _snap2_nil = (snap2 == nil)
            managers.player.current_state = function(self) return "standard" end
            WPNS:refresh(managers.hud)
            local snap3 = WPNS:get_snapshot()
            _clip3 = snap3 and snap3.slots[1].current_clip or nil
        ''')
        g = lua.globals()
        if g._missing_api:
            self.fail("RED: kyohud.hud.weapons API missing")
            return
        self.assertEqual(float(g._clip1), 25.0,
            "RED: standard state gives clip = 25")
        self.assertTrue(bool(g._snap2_nil),
            "RED: turret state must return nil snapshot")
        self.assertEqual(float(g._clip3), 25.0,
            "RED: recovery to standard must restore snapshot")


if __name__ == "__main__":
    unittest.main()
