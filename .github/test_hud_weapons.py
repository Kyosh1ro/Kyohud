"""LOT4b -- hud/weapons.lua: two-slot weapons snapshot via refresh/get_snapshot (RED vertical tracer).

Scope: local two-slot snapshot via kyohud.hud.weapons:refresh(manager) and
:get_snapshot() returning detached {selected, slots={[1]={present, current_clip,
total_raw, max_clip, max_total, reserve, fire_mode, alt_fire}, [2]=...}}.

Native shaped fixture: slot.unit has :base() returning weapon base; stable global
player unit and inventory; instance-owned selections; managers.player:current_state()
returns standard state. Weapon base: ammo_info() returns 4 values (max_clip,
current_clip, total, maximum); fire_mode() returns mode string; alt_fire_active()
returns boolean.

Five focused tests:
1. Two present slots and equipped dominance
2. Detached snapshots
3. Reserve once with zero
4. Distinct burst/volley and alt
5. Invalid maxima zero must preserve valid zero counters without division
6. Real total<clip anomaly (total actually less than clip)

No rendering, no events, no crew, no gauge, no player panel composition.

RED state: lua/hud/weapons.lua does not exist yet. Tests that depend on
the production chunk must fail with an explicit message, not FileNotFoundError.
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
WEAPONS_PATH = ROOT / "lua" / "hud" / "weapons.lua"

NATIVE_INVENTORY_WEAPON_FIXTURE = r'''
-- Native PlayerInventory and weapon base fixture (minimal shape for testing).
-- slot.unit has :base() returning weapon base; stable global player unit and inventory;
-- instance-owned selections; managers.player:current_state() returns standard state.
-- Weapon base: ammo_info() returns 4 values (max_clip, current_clip, total, maximum);
-- fire_mode() returns mode string; alt_fire_active() returns boolean.

PlayerInventory = {}
PlayerInventory.__index = PlayerInventory

function PlayerInventory.new()
    local self = setmetatable({}, PlayerInventory)
    self._selections = {}
    self._equipped_slot = 1
    self._alive = true
    return self
end

function PlayerInventory:available_selections()
    return self._selections
end

function PlayerInventory:equipped_selection()
    return self._equipped_slot
end

function PlayerInventory:equipped_unit()
    local sel = self._selections[self._equipped_slot]
    return sel and sel.unit or nil
end

function PlayerInventory:_native_set_slot(slot, unit)
    self._selections[slot] = {unit = unit}
end

function PlayerInventory:_native_set_equipped(slot)
    self._equipped_slot = slot
end

RaycastWeaponBase = {}
RaycastWeaponBase.__index = RaycastWeaponBase

function RaycastWeaponBase.new(name_id)
    local self = setmetatable({}, RaycastWeaponBase)
    self._name_id = name_id or "weapon_unknown"
    self._alive = true
    self._ammo_info = {max_clip=0, current_clip=0, total=0, maximum=0}
    self._fire_mode = "single"
    self._alt_fire = false
    self._tweak = {}
    return self
end

function RaycastWeaponBase:ammo_info()
    local info = self._ammo_info
    return info.max_clip, info.current_clip, info.total, info.maximum
end

function RaycastWeaponBase:fire_mode()
    return self._fire_mode
end

function RaycastWeaponBase:alt_fire_active()
    return self._alt_fire
end

function RaycastWeaponBase:ammo_base()
    return self
end

function RaycastWeaponBase:get_name_id()
    return self._name_id
end

function RaycastWeaponBase:weapon_tweak_data()
    return self._tweak
end

function RaycastWeaponBase:_native_set_ammo(max_clip, current_clip, total, maximum)
    self._ammo_info = {max_clip=max_clip, current_clip=current_clip, total=total, maximum=maximum}
end

function RaycastWeaponBase:_native_set_fire_mode(mode)
    self._fire_mode = mode
end

function RaycastWeaponBase:_native_set_alt_fire(active)
    self._alt_fire = active
end

function make_weapon(name_id)
    local base = RaycastWeaponBase.new(name_id)
    local unit = {
        _alive = true,
        base = function() return base end
    }
    return unit, base
end

inventory = PlayerInventory.new()

player_unit = {
    _alive = true,
    inventory = function() return inventory end,
    current_state = function() return {name="standard"} end
}

managers.player.player_unit = function(self)
    return player_unit
end

managers.player.current_state = function(self)
    return player_unit:current_state()
end
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

managers = managers or {}
managers.hud = setmetatable({_teammate_panels={}}, {__index=HUDManager})
managers.player = managers.player or {}

PlayerBase = {
    PLAYER_INFO_HUD_PD2 = "player_info_hud_pd2",
    PLAYER_INFO_HUD_FULLSCREEN_PD2 = "player_info_hud_fullscreen_pd2",
}
RequiredScript = "lib/units/beings/player/playerinventory"

tweak_data = tweak_data or {}
'''


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua(with_weapons=True, context=None, setup=None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute(NATIVE_INVENTORY_WEAPON_FIXTURE)
    if context:
        lua.execute(f'RequiredScript = "{context}"')
    if setup:
        lua.execute(setup)
    weapons_src = _read(WEAPONS_PATH)
    weapons_exists = weapons_src is not None
    if with_weapons and weapons_src:
        lua.execute(weapons_src)
    return lua, weapons_exists


class WeaponsFileExistsTests(unittest.TestCase):
    def test_weapons_chunk_exists(self):
        self.assertTrue(WEAPONS_PATH.is_file(),
            "RED: lua/hud/weapons.lua must exist (production chunk missing)")


class WeaponsTwoSlotAndEquippedDominanceTests(unittest.TestCase):
    """RED: two present slots, equipped selection dominance in snapshot."""

    def test_two_present_slots_equipped_dominance(self):
        """refresh(manager) snapshots both slots; selected matches equipped_selection."""
        setup = '''
            unit1, base1 = make_weapon("new_m1014")
            base1:_native_set_ammo(8, 6, 32, 40)
            base1:_native_set_fire_mode("auto")
            base1:_native_set_alt_fire(false)

            unit2, base2 = make_weapon("new_m16")
            base2:_native_set_ammo(30, 25, 120, 150)
            base2:_native_set_fire_mode("single")
            base2:_native_set_alt_fire(false)

            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_slot(2, unit2)
            inventory:_native_set_equipped(2)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/weapons.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local WPNS = kyohud.hud.weapons
            if not WPNS or not WPNS.refresh or not WPNS.get_snapshot then
                _missing_api = true
                return
            end
            _missing_api = false
            WPNS:refresh(managers.hud)
            local snap = WPNS:get_snapshot()
            _selected = snap and snap.selected or nil
            _s1_present = snap and snap.slots and snap.slots[1] and snap.slots[1].present
            _s1_clip = snap and snap.slots and snap.slots[1] and snap.slots[1].current_clip
            _s1_total = snap and snap.slots and snap.slots[1] and snap.slots[1].total_raw
            _s2_present = snap and snap.slots and snap.slots[2] and snap.slots[2].present
            _s2_clip = snap and snap.slots and snap.slots[2] and snap.slots[2].current_clip
            _s2_total = snap and snap.slots and snap.slots[2] and snap.slots[2].total_raw
        ''')
        g = lua.globals()
        if g._missing_api:
            self.fail("RED: kyohud.hud.weapons:refresh and :get_snapshot must exist")
            return
        self.assertEqual(float(g._selected), 2.0,
            "RED: selected must match equipped_selection() = 2")
        self.assertTrue(bool(g._s1_present),
            "RED: slot 1 must be present")
        self.assertEqual(float(g._s1_clip), 6.0,
            "RED: slot 1 current_clip = 6")
        self.assertEqual(float(g._s1_total), 32.0,
            "RED: slot 1 total_raw = 32")
        self.assertTrue(bool(g._s2_present),
            "RED: slot 2 must be present")
        self.assertEqual(float(g._s2_clip), 25.0,
            "RED: slot 2 current_clip = 25")
        self.assertEqual(float(g._s2_total), 120.0,
            "RED: slot 2 total_raw = 120")


class WeaponsDetachedSnapshotTests(unittest.TestCase):
    """RED: get_snapshot returns detached copy; mutation does not affect internal state."""

    def test_detached_snapshot(self):
        """Mutating returned snapshot must not affect subsequent get_snapshot calls."""
        setup = '''
            unit1, base1 = make_weapon("new_m1014")
            base1:_native_set_ammo(8, 6, 32, 40)
            base1:_native_set_fire_mode("auto")

            unit2, base2 = make_weapon("new_m16")
            base2:_native_set_ammo(30, 25, 120, 150)
            base2:_native_set_fire_mode("single")

            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_slot(2, unit2)
            inventory:_native_set_equipped(2)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/weapons.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local WPNS = kyohud.hud.weapons
            if not WPNS or not WPNS.refresh or not WPNS.get_snapshot then
                _missing_api = true
                return
            end
            _missing_api = false
            WPNS:refresh(managers.hud)
            local snap1 = WPNS:get_snapshot()
            snap1.slots[1].current_clip = 9999
            snap1.slots[2].current_clip = 9999
            local snap2 = WPNS:get_snapshot()
            _s1_clip = snap2.slots[1].current_clip
            _s2_clip = snap2.slots[2].current_clip
        ''')
        g = lua.globals()
        if g._missing_api:
            self.fail("RED: kyohud.hud.weapons:refresh and :get_snapshot must exist")
            return
        self.assertEqual(float(g._s1_clip), 6.0,
            "RED: mutating snapshot must not affect internal state (slot 1)")
        self.assertEqual(float(g._s2_clip), 25.0,
            "RED: mutating snapshot must not affect internal state (slot 2)")


class WeaponsReserveOnceWithZeroTests(unittest.TestCase):
    """RED: reserve = max(total_raw - current_clip, 0) computed once; zero is valid."""

    def test_reserve_once_with_zero(self):
        """reserve computed once; total_raw < current_clip preserved as anomaly, not repaired."""
        setup = '''
            unit1, base1 = make_weapon("new_m1014")
            base1:_native_set_ammo(10, 5, 20, 30)

            unit2, base2 = make_weapon("new_m16")
            base2:_native_set_ammo(30, 35, 30, 60)

            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_slot(2, unit2)
            inventory:_native_set_equipped(2)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/weapons.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local WPNS = kyohud.hud.weapons
            if not WPNS or not WPNS.refresh or not WPNS.get_snapshot then
                _missing_api = true
                return
            end
            _missing_api = false
            WPNS:refresh(managers.hud)
            local snap = WPNS:get_snapshot()
            _s1_reserve = snap.slots[1].reserve
            _s1_total = snap.slots[1].total_raw
            _s1_clip = snap.slots[1].current_clip
            _s2_reserve = snap.slots[2].reserve
            _s2_total = snap.slots[2].total_raw
            _s2_clip = snap.slots[2].current_clip
        ''')
        g = lua.globals()
        if g._missing_api:
            self.fail("RED: kyohud.hud.weapons:refresh and :get_snapshot must exist")
            return
        self.assertEqual(float(g._s1_reserve), 15.0,
            "RED: slot 1 reserve = max(20-5,0) = 15")
        self.assertEqual(float(g._s1_total), 20.0,
            "RED: slot 1 total_raw preserved as 20")
        self.assertEqual(float(g._s1_clip), 5.0,
            "RED: slot 1 current_clip preserved as 5")
        self.assertEqual(float(g._s2_reserve), 0.0,
            "RED: slot 2 reserve = max(30-35,0) = 0 (zero is valid, total<clip anomaly)")
        self.assertEqual(float(g._s2_total), 30.0,
            "RED: slot 2 total_raw preserved as 30 (total<clip anomaly)")
        self.assertEqual(float(g._s2_clip), 35.0,
            "RED: slot 2 current_clip preserved as 35 (total<clip anomaly)")


class WeaponsDistinctBurstVolleyAndAltTests(unittest.TestCase):
    """RED: fire_mode distinct values (burst/volley); alt_fire_active separate."""

    def test_distinct_burst_volley_and_alt(self):
        """burst and volley are distinct modes; alt_fire_active is separate boolean."""
        setup = '''
            unit1, base1 = make_weapon("new_m1014")
            base1:_native_set_ammo(8, 6, 32, 40)
            base1:_native_set_fire_mode("burst")
            base1:_native_set_alt_fire(true)

            unit2, base2 = make_weapon("new_m16")
            base2:_native_set_ammo(30, 25, 120, 150)
            base2:_native_set_fire_mode("volley")
            base2:_native_set_alt_fire(false)

            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_slot(2, unit2)
            inventory:_native_set_equipped(2)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/weapons.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local WPNS = kyohud.hud.weapons
            if not WPNS or not WPNS.refresh or not WPNS.get_snapshot then
                _missing_api = true
                return
            end
            _missing_api = false
            WPNS:refresh(managers.hud)
            local snap = WPNS:get_snapshot()
            _s1_mode = snap.slots[1].fire_mode
            _s1_alt = snap.slots[1].alt_fire
            _s2_mode = snap.slots[2].fire_mode
            _s2_alt = snap.slots[2].alt_fire
        ''')
        g = lua.globals()
        if g._missing_api:
            self.fail("RED: kyohud.hud.weapons:refresh and :get_snapshot must exist")
            return
        self.assertEqual(g._s1_mode, "burst",
            "RED: slot 1 fire_mode must be 'burst' (distinct from 'auto'/'single')")
        self.assertTrue(bool(g._s1_alt),
            "RED: slot 1 alt_fire must be true (separate from mode)")
        self.assertEqual(g._s2_mode, "volley",
            "RED: slot 2 fire_mode must be 'volley' (distinct from 'burst')")
        self.assertFalse(bool(g._s2_alt),
            "RED: slot 2 alt_fire must be false (separate from mode)")


class WeaponsInvalidMaximaZeroTests(unittest.TestCase):
    """RED: max_clip=0 or max_total=0 must preserve valid zero counters without division."""

    def test_invalid_maxima_zero_preserves_valid_zero_counters(self):
        """max_clip=0 or max_total=0: no division; valid zero counters preserved."""
        setup = '''
            unit1, base1 = make_weapon("new_m1014")
            base1:_native_set_ammo(0, 0, 0, 0)

            unit2, base2 = make_weapon("new_m16")
            base2:_native_set_ammo(10, 5, 20, 0)

            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_slot(2, unit2)
            inventory:_native_set_equipped(2)
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/weapons.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local WPNS = kyohud.hud.weapons
            if not WPNS or not WPNS.refresh or not WPNS.get_snapshot then
                _missing_api = true
                return
            end
            _missing_api = false
            local ok, err = pcall(function()
                WPNS:refresh(managers.hud)
            end)
            _refresh_ok = ok
            _refresh_err = err
            if ok then
                local snap = WPNS:get_snapshot()
                _s1_max_clip = snap.slots[1].max_clip
                _s1_clip = snap.slots[1].current_clip
                _s1_max_total = snap.slots[1].max_total
                _s1_total = snap.slots[1].total_raw
                _s2_max_clip = snap.slots[2].max_clip
                _s2_clip = snap.slots[2].current_clip
                _s2_max_total = snap.slots[2].max_total
                _s2_total = snap.slots[2].total_raw
            end
        ''')
        g = lua.globals()
        if g._missing_api:
            self.fail("RED: kyohud.hud.weapons:refresh and :get_snapshot must exist")
            return
        self.assertTrue(bool(g._refresh_ok),
            "RED: refresh must not crash with maxima=0 (no division)")
        self.assertEqual(float(g._s1_max_clip), 0.0,
            "RED: slot 1 max_clip preserved as 0")
        self.assertEqual(float(g._s1_clip), 0.0,
            "RED: slot 1 current_clip preserved as 0 (valid zero)")
        self.assertEqual(float(g._s1_max_total), 0.0,
            "RED: slot 1 max_total preserved as 0")
        self.assertEqual(float(g._s1_total), 0.0,
            "RED: slot 1 total_raw preserved as 0 (valid zero)")
        self.assertEqual(float(g._s2_max_clip), 10.0,
            "RED: slot 2 max_clip preserved as 10")
        self.assertEqual(float(g._s2_clip), 5.0,
            "RED: slot 2 current_clip preserved as 5")
        self.assertEqual(float(g._s2_max_total), 0.0,
            "RED: slot 2 max_total preserved as 0")
        self.assertEqual(float(g._s2_total), 20.0,
            "RED: slot 2 total_raw preserved as 20")


if __name__ == "__main__":
    unittest.main()
