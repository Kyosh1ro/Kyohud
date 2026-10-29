"""LOT4c -- hud/equipment.lua: cables + projectile/cooldown snapshot extensions.

Scope: local bounded slice extending hud/equipment.lua refresh/get_snapshot with
cables, projectile and cooldown data. Each test uses a fresh Lua runtime via
_lua() imported from test_hud_equipment; the existing loader runs STUBS, the
native equipment fixture, then per-test setup, then the production chunk.

Proposed minimal snapshot extensions (added alongside deployables):
  snapshot.cables = {raw, known, unlimited}
  snapshot.projectile = {projectile_id, kind,
                         charges={raw, known}, maximum={raw, known}}
  snapshot.cooldown  = {known, active, remaining, duration, clock_kind="game"}
    -- duration is optional; sourced from tweak.base_cooldown only when qualified.

Native fixture shape:
  managers.player._specials[equipment_id].amount = {digest_token, ...}
  PM:get_synced_grenades()  -> table {grenade=string, amount=token, max=number} or nil
  PM:get_grenade_amount()   -> decoded number or nil (nil when no synced table)
  PM:get_max_grenades()     -> number or nil (nil when no synced table)
  TimerManager.game():time() -> game clock seconds
  PM:get_timer_remaining()  -> number (remaining) or nil (no replenish timer)
  tweak_data.blackmarket.projectiles[id] = {type, ability, base_cooldown, ...}

Five focused tests:
1. Cable count 3 -> 0 known-zero using existing entry -> -1 known-false unlimited
   true; missing specials table -> unknown not zero.
2. Projectile: ability=true and ability="string" both classified "ability";
   ordinary throwable including smoke with base_cooldown classified "throwable";
   unknown metadata classified "unknown". Authoritative projectile_id from
   synced grenades, not BlackMarket. Decoded charges 2 / max 2, then 0.
3. Missing tweak registry / throwing getter / invalid charges -> unknown not 0.
4. Cooldown: initial PM remaining 17 with game clock 1000 vs GPC heist 100,
   base_cooldown 30 -> remaining 17, duration 30, known true, active true.
   Change remaining to 4.5 -> snapshot current. Nil native timer -> inactive
   (getter present + source valid only).
5. Identity replacement: projectile new ID with different count and no cooldown
   cannot inherit prior snapshot state.

RED state: production chunk does not yet emit cables / projectile / cooldown
in the snapshot. Each test must detect missing fields and fail with an
explicit RED message.
"""
from pathlib import Path
import unittest

from test_hud_equipment import _lua  # noqa: E402  -- imported from sibling test module

ROOT = Path(__file__).resolve().parents[1]

NATIVE_CONSUMABLES_FIXTURE = r'''
-- Native consumables fixture: specials (cable_tie), grenades, timers, tweaks.
-- Modeled on PlayerManager specials, grenades and TimerManager.game shapes.

-- Specials table for cable_tie with digest tokens.
managers.player._equipment.specials = {}
managers.player._global = {synced_grenades = {}}
native_max = {}
managers.blackmarket = {equipped_grenade = function() return "wrong_id" end}

function PlayerManager:_native_set_specials(equipment_id, quantities)
    self._equipment.specials[equipment_id] = {
        amount = Application:digest_value(quantities[1], true), is_cable_tie = true}
end

function PlayerManager:_native_remove_specials(equipment_id)
    self._equipment.specials[equipment_id] = nil
end

function PlayerManager:_native_clear_specials_table()
    self._equipment.specials = nil
end

-- Grenades / throwables: real-shaped methods returning nil (not 0) when absent.
function PlayerManager:_native_set_grenades(grenade_id, amount, max_amount)
    native_max[grenade_id] = max_amount
    self._global.synced_grenades[1] = {
        grenade = grenade_id,
        amount = Application:digest_value(amount, true)
    }
end

function PlayerManager:_native_replace_grenade(grenade_id, amount, max_amount)
    self:_native_set_grenades(grenade_id, amount, max_amount)
end

function PlayerManager:_native_clear_grenades()
    self._global.synced_grenades[1] = nil
end

function PlayerManager:get_synced_grenades(peer_id)
    assert(peer_id == 1, "local peer must be explicit")
    return self._global.synced_grenades[peer_id]
end

function PlayerManager:get_grenade_amount(peer_id)
    assert(peer_id == 1, "local peer must be explicit")
    return Application:digest_value(self._global.synced_grenades[peer_id].amount, false)
end

function PlayerManager:get_max_grenades(id)
    return native_max[id]
end

-- TimerManager game clock.
TimerManager = TimerManager or {}
_game_clock = {_time = 0}
function TimerManager.game() return _game_clock end
function _game_clock:time() return self._time end
function _game_clock:set_time(t) self._time = t end

-- Replenish timer for grenade cooldown.
function PlayerManager:_native_set_replenish_timer(game_time)
    self._timers = {replenish_grenades = {t = game_time}}
end

function PlayerManager:_native_clear_replenish_timer()
    self._timers = {}
end

function PlayerManager:get_timer_remaining(key)
    assert(key == "replenish_grenades", "timer key must be explicit")
    local timer = self._timers and self._timers[key]
    if not timer then return nil end
    local gt = TimerManager.game():time()
    return timer.t > gt and timer.t - gt or nil
end

-- Projectile tweak_data.
tweak_data = tweak_data or {}
tweak_data.blackmarket = tweak_data.blackmarket or {}
tweak_data.blackmarket.projectiles = tweak_data.blackmarket.projectiles or {}

function _native_set_projectile_tweak(id, entry)
    tweak_data.blackmarket.projectiles[id] = entry
end

function _native_remove_projectile_tweak(id)
    tweak_data.blackmarket.projectiles[id] = nil
end

-- GamePlayCentralManager stub for heist time (used as alternative clock source).
GamePlayCentralManager = GamePlayCentralManager or {}
GamePlayCentralManager.heist_time = GamePlayCentralManager.heist_time or 0
function GamePlayCentralManager:get_heist_timer()
    return self.heist_time
end
managers.game_play_central = GamePlayCentralManager
'''


def _consumable_setup(state=""):
    return NATIVE_CONSUMABLES_FIXTURE + "\n" + state


def _check_extended_api(lua, test_case):
    g = lua.globals()
    if g._missing_extended_api:
        test_case.fail(
            "RED: kyohud.hud.equipment snapshot must include cables, "
            "projectile and/or cooldown extensions")
        return False
    return True


class EquipmentConsumablesFileExistsTests(unittest.TestCase):
    def test_equipment_chunk_exists(self):
        self.assertTrue((ROOT / "lua" / "hud" / "equipment.lua").is_file(),
            "RED: lua/hud/equipment.lua must exist (production chunk missing)")


class CableCountAndSpecialsTests(unittest.TestCase):
    """Test 1 -- cable tie count transitions and missing specials table."""

    def test_cable_count_transitions_and_missing_specials(self):
        """cable count 3 -> 0 known zero using existing entry -> -1 known
        unlimited true; missing specials table -> unknown not zero."""
        setup = _consumable_setup('''
            managers.player:_native_set_specials("cable_tie", {3})
        ''')
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/equipment.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local EQ = kyohud.hud.equipment
            if not EQ or not EQ.refresh or not EQ.get_snapshot then
                _missing_extended_api = true
                return
            end
            _missing_extended_api = false
            EQ:refresh(managers.hud)
            local snap1 = EQ:get_snapshot()

            _cables1 = snap1.cables
            _has_cables1 = _cables1 ~= nil
            _c1_raw = _cables1 and _cables1.raw
            _c1_known = _cables1 and _cables1.known
            _c1_unlimited = _cables1 and _cables1.unlimited

            -- Decrement to 0: existing entry, known zero
            managers.player:_native_set_specials("cable_tie", {0})
            EQ:refresh(managers.hud)
            local snap2 = EQ:get_snapshot()
            _c2_raw = snap2.cables and snap2.cables.raw
            _c2_known = snap2.cables and snap2.cables.known

            -- Decrement to -1: invalid negative, unlimited true
            managers.player:_native_set_specials("cable_tie", {-1})
            EQ:refresh(managers.hud)
            local snap3 = EQ:get_snapshot()
            _c3_raw = snap3.cables and snap3.cables.raw
            _c3_known = snap3.cables and snap3.cables.known
            _c3_unlimited = snap3.cables and snap3.cables.unlimited

            -- Missing specials table entirely
            managers.player:_native_clear_specials_table()
            EQ:refresh(managers.hud)
            local snap4 = EQ:get_snapshot()
            _c4_raw = snap4.cables and snap4.cables.raw
            _c4_known = snap4.cables and snap4.cables.known
            _c4_is_zero = (_c4_raw == 0)
        ''')
        if not _check_extended_api(lua, self):
            return
        g = lua.globals()
        self.assertTrue(bool(g._has_cables1),
            "RED: snapshot must include cables table")
        self.assertEqual(float(g._c1_raw), 3.0,
            "RED: cables raw must be 3 (initial count)")
        self.assertTrue(bool(g._c1_known),
            "RED: cables known must be true for valid count")
        self.assertFalse(bool(g._c1_unlimited),
            "RED: cables unlimited must be false for finite count")
        self.assertEqual(float(g._c2_raw), 0.0,
            "RED: cables raw must be 0 after decrement to zero (existing entry)")
        self.assertTrue(bool(g._c2_known),
            "RED: cables known must be true for zero (valid count using existing entry)")
        self.assertEqual(float(g._c3_raw), -1.0,
            "RED: cables raw must be -1 (preserved invalid value)")
        self.assertTrue(bool(g._c3_known),
            "RED: native -1 sentinel is known unlimited")
        self.assertTrue(bool(g._c3_unlimited),
            "RED: cables unlimited must be true for negative value")
        self.assertFalse(bool(g._c4_is_zero),
            "RED: missing specials table must produce unknown (not 0)")
        self.assertFalse(bool(g._c4_known),
            "RED: missing specials table must produce known=false")


class ProjectileClassificationTests(unittest.TestCase):
    """Test 2 -- projectile kind classification and synced ID authority."""

    def test_projectile_kind_classification_and_synced_id(self):
        """ability=true and ability="string" both classified "ability";
        ordinary throwable including smoke with base_cooldown classified
        "throwable"; unknown metadata classified "unknown". Authoritative
        projectile_id from synced grenades, not BlackMarket. Decoded
        charges 2 / max 2, then 0."""
        setup = _consumable_setup('''
            _native_set_projectile_tweak("frag",
                {throwable = true, is_a_grenade = true, base_cooldown = 30})
            _native_set_projectile_tweak("smoke",
                {throwable = true, is_a_grenade = true, base_cooldown = 25})
            _native_set_projectile_tweak("ability_bool",
                {ability = true})
            _native_set_projectile_tweak("ability_str",
                {ability = "flash"})
            managers.player:_native_set_grenades("frag", 2, 2)
        ''')
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/equipment.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local EQ = kyohud.hud.equipment
            if not EQ or not EQ.refresh or not EQ.get_snapshot then
                _missing_extended_api = true
                return
            end
            _missing_extended_api = false
            EQ:refresh(managers.hud)
            local snap1 = EQ:get_snapshot()

            _p1 = snap1.projectile
            _has_p1 = _p1 ~= nil
            _p1_id = _p1 and _p1.projectile_id
            _p1_kind = _p1 and _p1.kind
            _p1_charges_raw = _p1 and _p1.charges and _p1.charges.raw
            _p1_charges_known = _p1 and _p1.charges and _p1.charges.known
            _p1_max_raw = _p1 and _p1.maximum and _p1.maximum.raw
            _p1_max_known = _p1 and _p1.maximum and _p1.maximum.known

            -- Decrement to 0
            managers.player:_native_set_grenades("frag", 0, 2)
            EQ:refresh(managers.hud)
            local snap2 = EQ:get_snapshot()
            _p2_charges_raw = snap2.projectile and snap2.projectile.charges
                and snap2.projectile.charges.raw
            _p2_charges_known = snap2.projectile and snap2.projectile.charges
                and snap2.projectile.charges.known

            -- ability=true
            managers.player:_native_set_grenades("ability_bool", 1, 1)
            EQ:refresh(managers.hud)
            local snap3 = EQ:get_snapshot()
            _p3_kind = snap3.projectile and snap3.projectile.kind

            -- ability="flash"
            managers.player:_native_set_grenades("ability_str", 1, 1)
            EQ:refresh(managers.hud)
            local snap4 = EQ:get_snapshot()
            _p4_kind = snap4.projectile and snap4.projectile.kind

            -- smoke (throwable with base_cooldown)
            managers.player:_native_set_grenades("smoke", 3, 3)
            EQ:refresh(managers.hud)
            local snap5 = EQ:get_snapshot()
            _p5_kind = snap5.projectile and snap5.projectile.kind

            -- unknown (no tweak entry)
            managers.player:_native_set_grenades("unknown_grenade", 1, 1)
            EQ:refresh(managers.hud)
            local snap6 = EQ:get_snapshot()
            _p6_kind = snap6.projectile and snap6.projectile.kind
        ''')
        if not _check_extended_api(lua, self):
            return
        g = lua.globals()
        self.assertTrue(bool(g._has_p1),
            "RED: snapshot must include projectile table")
        self.assertEqual(g._p1_id, "frag",
            "RED: projectile_id must come from synced grenades, not BlackMarket")
        self.assertEqual(g._p1_kind, "throwable",
            "RED: frag with base_cooldown must be classified throwable")
        self.assertEqual(float(g._p1_charges_raw), 2.0,
            "RED: decoded charges must be 2")
        self.assertTrue(bool(g._p1_charges_known),
            "RED: decoded charges known must be true")
        self.assertEqual(float(g._p1_max_raw), 2.0,
            "RED: decoded maximum must be 2")
        self.assertTrue(bool(g._p1_max_known),
            "RED: decoded maximum known must be true")
        self.assertEqual(float(g._p2_charges_raw), 0.0,
            "RED: charges raw must be 0 after decrement")
        self.assertTrue(bool(g._p2_charges_known),
            "RED: charges known must be true for zero (valid count)")
        self.assertEqual(g._p3_kind, "ability",
            "RED: ability=true must classify as ability")
        self.assertEqual(g._p4_kind, "ability",
            "RED: ability='flash' (string truthy) must classify as ability")
        self.assertEqual(g._p5_kind, "throwable",
            "RED: smoke with base_cooldown must classify as throwable")
        self.assertEqual(g._p6_kind, "unknown",
            "RED: missing tweak entry must classify as unknown")


class ProjectileInvalidMetadataTests(unittest.TestCase):
    """Test 3 -- missing registry, throwing getter, invalid charges."""

    def test_invalid_projectile_metadata_unknown_not_zero(self):
        """Missing tweak registry / throwing getter / invalid charges ->
        unknown classification and unknown charges, not 0."""
        setup = _consumable_setup('''
            managers.player:_native_set_grenades("no_tweak_here", 0/0, -3)
        ''')
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/equipment.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local EQ = kyohud.hud.equipment
            if not EQ or not EQ.refresh or not EQ.get_snapshot then
                _missing_extended_api = true
                return
            end
            _missing_extended_api = false

            -- Invalid charges (NaN amount, negative max) with no tweak entry
            EQ:refresh(managers.hud)
            local snap1 = EQ:get_snapshot()
            _p1 = snap1.projectile
            _p1_kind = _p1 and _p1.kind
            _p1_charges_raw = _p1 and _p1.charges and _p1.charges.raw
            _p1_charges_known = _p1 and _p1.charges and _p1.charges.known
            _p1_charges_is_nan = (_p1_charges_raw ~= _p1_charges_raw)
            _p1_max_raw = _p1 and _p1.maximum and _p1.maximum.raw
            _p1_max_known = _p1 and _p1.maximum and _p1.maximum.known
            _p1_charges_is_zero = (_p1_charges_raw == 0)
            _p1_max_is_zero = (_p1_max_raw == 0)

            -- Missing registry only (valid charges, no tweak)
            managers.player:_native_set_grenades("orphan_grenade", 2, 2)
            EQ:refresh(managers.hud)
            local snap2 = EQ:get_snapshot()
            _p2_kind = snap2.projectile and snap2.projectile.kind

            -- Throwing getter
            local _orig_synced = PlayerManager.get_synced_grenades
            function PlayerManager:get_synced_grenades()
                error("synced_grenades failed")
            end
            _threw = not pcall(function() EQ:refresh(managers.hud) end)
            local snap3 = EQ:get_snapshot()
            _p3 = snap3.projectile
            _p3_kind = _p3 and _p3.kind
            _p3_charges_known = _p3 and _p3.charges and _p3.charges.known
            _p3_charges_raw = _p3 and _p3.charges and _p3.charges.raw
            _p3_charges_is_zero = (_p3_charges_raw == 0)
            PlayerManager.get_synced_grenades = _orig_synced

            -- Nil synced grenades (getter returns nil, not 0)
            managers.player:_native_clear_grenades()
            _native_amount = nil -- absent entry must not reach the native getter
            _native_max = managers.player:get_max_grenades()
            _native_synced = managers.player:get_synced_grenades(1)
            EQ:refresh(managers.hud)
            local snap4 = EQ:get_snapshot()
            _p4 = snap4.projectile
            _p4_kind = _p4 and _p4.kind
            _p4_charges_known = _p4 and _p4.charges and _p4.charges.known
        ''')
        if not _check_extended_api(lua, self):
            return
        g = lua.globals()
        self.assertIsNone(g._native_amount,
            "precondition: absent entry is not passed to get_grenade_amount")
        self.assertFalse(bool(g._threw), "throwing getter must remain protected")
        self.assertIsNone(g._native_max,
            "precondition: get_max_grenades returns nil when no grenades")
        self.assertIsNone(g._native_synced,
            "precondition: get_synced_grenades returns nil when no grenades")
        self.assertEqual(g._p1_kind, "unknown",
            "RED: missing tweak registry must classify as unknown")
        self.assertTrue(bool(g._p1_charges_is_nan),
            "RED: NaN charges raw must remain NaN (not replaced with 0)")
        self.assertFalse(bool(g._p1_charges_known),
            "RED: NaN charges must have known=false")
        self.assertFalse(bool(g._p1_max_known),
            "RED: negative maximum must have known=false")
        self.assertFalse(bool(g._p1_charges_is_zero),
            "RED: NaN charges must NOT equal 0")
        self.assertFalse(bool(g._p1_max_is_zero),
            "RED: negative maximum must NOT equal 0")
        self.assertEqual(g._p2_kind, "unknown",
            "RED: missing registry with valid charges still unknown kind")
        self.assertFalse(bool(g._p3_charges_known),
            "RED: throwing getter must produce charges known=false")
        self.assertFalse(bool(g._p3_charges_is_zero),
            "RED: throwing getter charges must NOT silently be 0")
        self.assertFalse(bool(g._p4_charges_known),
            "RED: nil synced grenades must produce charges known=false")


class CooldownStateTests(unittest.TestCase):
    """Test 4 -- cooldown initial, change, nil timer transitions."""

    def test_cooldown_state_transitions(self):
        """initial PM remaining 17 with game clock 1000 vs GPC heist 100,
        base_cooldown 30 -> remaining 17, duration 30, known active.
        Change remaining to 4.5 -> snapshot current. Nil native timer ->
        inactive (only getter present + source valid)."""
        setup = _consumable_setup('''
            _game_clock:set_time(1000)
            GamePlayCentralManager.heist_time = 100
            managers.player:_native_set_grenades("frag", 0, 2)
            managers.player:_native_set_replenish_timer(1017)
            _native_set_projectile_tweak("frag",
                {throwable = true, base_cooldown = 30})
        ''')
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/equipment.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local EQ = kyohud.hud.equipment
            if not EQ or not EQ.refresh or not EQ.get_snapshot then
                _missing_extended_api = true
                return
            end
            _missing_extended_api = false

            -- Verify native remaining is 17
            _native_remaining = managers.player:get_timer_remaining("replenish_grenades")

            EQ:refresh(managers.hud)
            local snap1 = EQ:get_snapshot()
            _cd1 = snap1.cooldown
            _has_cd1 = _cd1 ~= nil
            _cd1_known = _cd1 and _cd1.known
            _cd1_active = _cd1 and _cd1.active
            _cd1_remaining = _cd1 and _cd1.remaining
            _cd1_duration = _cd1 and _cd1.duration
            _cd1_clock = _cd1 and _cd1.clock_kind

            -- Change: remaining becomes 4.5
            _game_clock:set_time(1000)
            managers.player:_native_set_replenish_timer(1004.5)
            EQ:refresh(managers.hud)
            local snap2 = EQ:get_snapshot()
            _cd2_remaining = snap2.cooldown and snap2.cooldown.remaining

            -- Nil native timer, getter still present + source valid
            managers.player:_native_clear_replenish_timer()
            _native_timer_after_clear = managers.player:get_timer_remaining("replenish_grenades")
            EQ:refresh(managers.hud)
            local snap3 = EQ:get_snapshot()
            _cd3 = snap3.cooldown
            _cd3_known = _cd3 and _cd3.known
            _cd3_active = _cd3 and _cd3.active
        ''')
        if not _check_extended_api(lua, self):
            return
        g = lua.globals()
        self.assertEqual(float(g._native_remaining), 17.0,
            "precondition: native get_timer_remaining returns 17")
        self.assertTrue(bool(g._has_cd1),
            "RED: snapshot must include cooldown table")
        self.assertTrue(bool(g._cd1_known),
            "RED: cooldown known must be true when getter returns value")
        self.assertTrue(bool(g._cd1_active),
            "RED: cooldown active must be true when remaining > 0")
        self.assertEqual(float(g._cd1_remaining), 17.0,
            "RED: cooldown remaining must be 17 (game clock source, not GPC)")
        self.assertEqual(float(g._cd1_duration), 30.0,
            "RED: cooldown duration must be 30 (from tweak base_cooldown)")
        self.assertEqual(g._cd1_clock, "game",
            "RED: cooldown clock_kind must be 'game'")
        self.assertEqual(float(g._cd2_remaining), 4.5,
            "RED: cooldown remaining must track current value 4.5")
        self.assertIsNone(g._native_timer_after_clear,
            "precondition: native get_timer_remaining returns nil after clear")
        self.assertTrue(bool(g._cd3_known),
            "RED: cooldown known true when getter present + source valid (nil timer)")
        self.assertFalse(bool(g._cd3_active),
            "RED: cooldown active must be false when native timer is nil")


class ProjectileIdentityReplacementTests(unittest.TestCase):
    """Test 5 -- replacing projectile identity must not inherit prior state."""

    def test_identity_replacement_no_inheritance(self):
        """projectile new ID with different count and no cooldown cannot
        inherit prior snapshot state."""
        setup = _consumable_setup('''
            _native_set_projectile_tweak("frag",
                {throwable = true, base_cooldown = 30})
            managers.player:_native_set_grenades("frag", 2, 4)
            _game_clock:set_time(1000)
            managers.player:_native_set_replenish_timer(1017)
        ''')
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/equipment.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local EQ = kyohud.hud.equipment
            if not EQ or not EQ.refresh or not EQ.get_snapshot then
                _missing_extended_api = true
                return
            end
            _missing_extended_api = false
            EQ:refresh(managers.hud)
            local snap1 = EQ:get_snapshot()

            _p1_id = snap1.projectile and snap1.projectile.projectile_id
            _p1_charges = snap1.projectile and snap1.projectile.charges
                and snap1.projectile.charges.raw
            _cd1_active = snap1.cooldown and snap1.cooldown.active
            _cd1_remaining = snap1.cooldown and snap1.cooldown.remaining

            -- Replace projectile identity: new ID, different count, no cooldown
            _native_set_projectile_tweak("smoke",
                {throwable = true, base_cooldown = 25})
            managers.player:_native_replace_grenade("smoke", 1, 3)
            managers.player:_native_clear_replenish_timer()
            EQ:refresh(managers.hud)
            local snap2 = EQ:get_snapshot()

            _p2_id = snap2.projectile and snap2.projectile.projectile_id
            _p2_charges = snap2.projectile and snap2.projectile.charges
                and snap2.projectile.charges.raw
            _p2_max = snap2.projectile and snap2.projectile.maximum
                and snap2.projectile.maximum.raw
            _cd2_active = snap2.cooldown and snap2.cooldown.active
            _cd2_remaining = snap2.cooldown and snap2.cooldown.remaining
            _cd2_duration = snap2.cooldown and snap2.cooldown.duration
        ''')
        if not _check_extended_api(lua, self):
            return
        g = lua.globals()
        self.assertEqual(g._p1_id, "frag",
            "precondition: initial projectile_id is 'frag'")
        self.assertEqual(float(g._p1_charges), 2.0,
            "precondition: initial charges is 2")
        self.assertTrue(bool(g._cd1_active),
            "precondition: initial cooldown active")
        self.assertEqual(float(g._cd1_remaining), 17.0,
            "precondition: initial cooldown remaining is 17")
        self.assertEqual(g._p2_id, "smoke",
            "RED: after identity replace, projectile_id must be 'smoke'")
        self.assertEqual(float(g._p2_charges), 1.0,
            "RED: after identity replace, charges must be 1 (not inherited 2)")
        self.assertEqual(float(g._p2_max), 3.0,
            "RED: after identity replace, maximum must be 3 (not inherited 4)")
        self.assertFalse(bool(g._cd2_active),
            "RED: after identity replace with no timer, cooldown active must be false")
        self.assertIsNone(g._cd2_remaining,
            "RED: after identity replace with no timer, remaining must be nil (not inherited 17)")
        self.assertEqual(float(g._cd2_duration), 25.0,
            "RED: after identity replace, duration from new tweak base_cooldown 25")


if __name__ == "__main__":
    unittest.main()
