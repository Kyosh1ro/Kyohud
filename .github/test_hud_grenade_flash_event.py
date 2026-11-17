"""Event contract: `HUDManager:animate_grenade_flash(i)` POSTHOOK starts an owned
0.6 s full-icon cyan pulse for the local slot only. The native method is still
called and its return is preserved. The pulse is driven by the game clock, not
by native ghost color/size, and the two native ghosts stay leased hidden only
while a real certified pulse exists. The terminal native completion releases
the H5 flash group without resurrecting either ghost.
"""
import unittest
from pathlib import Path

from test_hud_grenade_flash_replacement import _flash_lua

ROOT = Path(__file__).resolve().parents[1]
EQUIPMENT_PATH = ROOT / "lua" / "hud" / "equipment.lua"


def _event_lua():
    """Reusable fixture: the literal shared flash runtime, the previous native
    mirror completed, then a native-shaped `animate_grenade_flash` stub installed
    before the real equipment chunk is reloaded so production `install()` sees it.
    """
    lua = _flash_lua()
    lua.execute(r'''
        local radial_ghost = _gren:child("grenades_radial_ghost")
        local icon_ghost = _gren:child("grenades_icon_ghost")
        local sentinel = _gren:child("native_flash_sentinel")
        _G._flash_event_radial_ghost = radial_ghost
        _G._flash_event_icon_ghost = icon_ghost
        _G._flash_event_sentinel = sentinel
        _G._flash_event_sentinel_shape = {
            sentinel:x(), sentinel:y(), sentinel:w(), sentinel:h()}
        function _flash_event_sentinel_owned()
            return sentinel:parent() == _gren
        end

        local function finish(ghost, base)
            ghost:set_shape(base:x(), base:y(), base:w(), base:h())
            ghost:set_color(Color(0, 1, 1, 1))
            ghost:set_visible(false)
        end
        finish(radial_ghost, _radial)
        finish(icon_ghost, _icon)
        _R:update(_m, 1.12, .06)

        local row = _E._rows[4]
        local flash = row and row._grenade_flash
        local snap = _E:get_snapshot()
        _G._initial_flash_hidden = flash ~= nil and flash:visible() == false
        _G._initial_charges = snap.projectile.charges.raw
        _G._initial_maximum = snap.projectile.maximum.raw
        _G._initial_cooldown = {
            known = snap.cooldown.known, active = snap.cooldown.active,
            remaining = snap.cooldown.remaining, duration = snap.cooldown.duration,
            integrated = snap.cooldown.integrated}
        _G._initial_group_absent = _R._h5_groups == nil
            or _R._h5_groups.local_p_grenade_flash == nil
        _G._initial_ghosts_false = radial_ghost:visible() == false
            and icon_ghost:visible() == false

        _G._native_flash_calls = 0
        _G._native_flash_return = nil
        local NATIVE_RETURN = "kyohud-native-animate-grenade-flash"
        _G._native_flash_expected_return = NATIVE_RETURN
        function HUDManager:animate_grenade_flash(i)
            _G._native_flash_calls = _G._native_flash_calls + 1
            radial_ghost:set_shape(_radial:x(), _radial:y(), _radial:w(), _radial:h())
            icon_ghost:set_shape(_icon:x(), _icon:y(), _icon:w(), _icon:h())
            radial_ghost:set_color(Color(1, 1, 1, 1))
            icon_ghost:set_color(Color(1, 1, 1, 1))
            radial_ghost:set_visible(true)
            icon_ghost:set_visible(true)
            return NATIVE_RETURN
        end
        _G._native_flash_orig = HUDManager.animate_grenade_flash

        function _emit_flash(i)
            local result = HUDManager.animate_grenade_flash(managers.hud, i)
            dispatch(HUDManager, "animate_grenade_flash", managers.hud, i)
            _G._native_flash_return = result
            return result
        end
    ''')
    lua.globals().RequiredScript = "lib/managers/hudmanagerpd2"
    source = EQUIPMENT_PATH.read_text(encoding="utf-8-sig")
    lua.execute(source)
    lua.execute(source)
    lua.execute("_E:refresh(_m)")
    lua.execute(r'''
        _G._flash_event_hook_count = 0
        for _, hook in ipairs(Hooks._all) do
            if hook.class == HUDManager and hook.method == "animate_grenade_flash"
                and hook.kind == "post" then
                _G._flash_event_hook_count = _G._flash_event_hook_count + 1
            end
        end
        local snap = _E:get_snapshot()
        _G._reload_charges = snap.projectile.charges.raw
        _G._reload_maximum = snap.projectile.maximum.raw
        _G._reload_cooldown_active = snap.cooldown.known == true
            and snap.cooldown.active == true
    ''')
    return lua


def _sentinel_ok(g):
    s = g._flash_event_sentinel
    shape = g._flash_event_sentinel_shape
    if s is None:
        return False
    return (bool(s.visible(s)) and bool(g._flash_event_sentinel_owned())
            and float(s.x(s)) == float(shape[1]) and float(s.y(s)) == float(shape[2])
            and float(s.w(s)) == float(shape[3]) and float(s.h(s)) == float(shape[4]))


class GrenadeFlashEventTests(unittest.TestCase):
    def test_native_event_certified_cyan_pulse_is_geometry_independent(self):
        lua = _event_lua()
        g = lua.globals()

        self.assertEqual(int(g._flash_event_hook_count), 1,
            "RED: equipment must register exactly one animate_grenade_flash POSTHOOK")
        self.assertTrue(bool(g._initial_flash_hidden),
            "RED: owned flash must stay hidden before any native event")
        self.assertEqual(float(g._initial_charges), 1.0,
            "fixture stock must be 1 of 2")
        self.assertEqual(float(g._initial_maximum), 2.0)
        self.assertTrue(bool(g._initial_cooldown.active),
            "fixture RECHARGE/cooldown must be active")
        self.assertTrue(bool(g._initial_group_absent),
            "RED: the previous mirror must have released the flash group")
        self.assertTrue(bool(g._initial_ghosts_false))
        self.assertEqual(float(g._reload_charges), 1.0,
            "module reload must not change stock")
        self.assertEqual(float(g._reload_maximum), 2.0)
        self.assertTrue(bool(g._reload_cooldown_active))

        lua.execute(r'''
            _game_clock:set_time(1000)
            _G._event_return = _emit_flash(HUDManager.PLAYER_PANEL)
            _R:update(_m, 1.20, .08)

            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            local icon = row and row._icon
            local function close(a, b) return math.abs(a - b) <= .05 end
            _G._event_flash = flash
            _G._event_flash_visible = flash ~= nil and flash:visible() == true
            _G._event_full_shape = flash ~= nil and icon ~= nil
                and close(flash:x(), icon:x()) and close(flash:y(), icon:y())
                and close(flash:w(), icon:w()) and close(flash:h(), icon:h())
            local c = flash and flash:color()
            _G._event_cyan = c ~= nil and c.r < .5 and c.g > .5 and c.b > .5
            _G._event_white = c ~= nil and close(c.r, 1) and close(c.g, 1)
                and close(c.b, 1)
            _G._event_alpha = flash and flash:alpha() or -1
            _G._event_ghosts_false = _G._flash_event_radial_ghost:visible() == false
                and _G._flash_event_icon_ghost:visible() == false
            _G._event_group_present = _R._h5_groups ~= nil
                and _R._h5_groups.local_p_grenade_flash ~= nil
            _G._event_native_calls = _G._native_flash_calls
            _G._event_native_return_ok = _G._event_return
                == _G._native_flash_expected_return
                and _G._native_flash_return == _G._native_flash_expected_return
            local snap = _E:get_snapshot()
            _G._event_charges = snap.projectile.charges.raw
            _G._event_maximum = snap.projectile.maximum.raw
            _G._event_cooldown_known = snap.cooldown.known
            _G._event_cooldown_active = snap.cooldown.active
            _G._event_cooldown_remaining = snap.cooldown.remaining
            _G._event_sentinel_ok = _G._flash_event_sentinel:visible() == true
                and _G._flash_event_sentinel:parent() == _gren
        ''')
        self.assertTrue(bool(g._event_flash_visible),
            "RED: local native event must reveal the owned full-icon pulse")
        self.assertTrue(bool(g._event_full_shape),
            "RED: event pulse must use the full original row icon, not a shrunken mirror")
        self.assertTrue(bool(g._event_cyan),
            "RED: event pulse must be cyan")
        self.assertFalse(bool(g._event_white),
            "RED: event pulse must not keep the native white mirror color")
        self.assertAlmostEqual(float(g._event_alpha), 1.0, delta=.01,
            msg="RED: event pulse must start fully opaque")
        self.assertTrue(bool(g._event_ghosts_false),
            "RED: both native ghosts must stay leased hidden during a real pulse")
        self.assertTrue(bool(g._event_group_present),
            "RED: the local_p_grenade_flash H5 group must hold the certified pulse")
        self.assertEqual(int(g._event_native_calls), 1,
            "RED: the native animate_grenade_flash must be called exactly once")
        self.assertTrue(bool(g._event_native_return_ok),
            "RED: the native return value must survive the POSTHOOK dispatch")
        self.assertEqual(float(g._event_charges), 1.0,
            "event must not clamp the grenade stock")
        self.assertEqual(float(g._event_maximum), 2.0)
        self.assertTrue(bool(g._event_cooldown_known))
        self.assertTrue(bool(g._event_cooldown_active),
            "RECHARGE/cooldown must remain active and unchanged by the event")
        self.assertAlmostEqual(float(g._event_cooldown_remaining),
            float(g._initial_cooldown.remaining), delta=.001)
        self.assertTrue(bool(g._event_sentinel_ok))
        self.assertTrue(_sentinel_ok(g))

        lua.execute(r'''
            local function scale(ghost, base, factor)
                local w, h = base:w() * factor, base:h() * factor
                ghost:set_shape(base:x() + base:w() * .5 - w * .5,
                    base:y() + base:h() * .5 - h * .5, w, h)
            end
            scale(_G._flash_event_radial_ghost, _radial, 1.2)
            scale(_G._flash_event_icon_ghost, _icon, 1.2)
            _G._flash_event_radial_ghost:set_color(Color(.15, 1, 1, 1))
            _G._flash_event_icon_ghost:set_color(Color(.15, 1, 1, 1))
            _game_clock:set_time(1000.30)
            local before = _E._rows[4]._grenade_flash
            _R:update(_m, 1.21, .01)
            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            local icon = row and row._icon
            local function close(a, b) return math.abs(a - b) <= .05 end
            _G._pulse_same = flash ~= nil and flash == before
            _G._pulse_visible = flash ~= nil and flash:visible() == true
            _G._pulse_full_shape = flash ~= nil and icon ~= nil
                and close(flash:x(), icon:x()) and close(flash:y(), icon:y())
                and close(flash:w(), icon:w()) and close(flash:h(), icon:h())
            _G._pulse_alpha = flash and flash:alpha() or -1
            local c = flash and flash:color()
            _G._pulse_cyan = c ~= nil and c.r < .5 and c.g > .5 and c.b > .5
            _G._pulse_cert = _E._grenade_flash_ok == true
                and row._flash_active == true
                and row:_verify_grenade_flash() == true
                and _E:verify() == true
            _G._pulse_ghosts_false = _G._flash_event_radial_ghost:visible() == false
                and _G._flash_event_icon_ghost:visible() == false
            _G._pulse_group_present = _R._h5_groups ~= nil
                and _R._h5_groups.local_p_grenade_flash ~= nil
            _G._pulse_sentinel_ok = _G._flash_event_sentinel:visible() == true
                and _G._flash_event_sentinel:parent() == _gren
        ''')
        self.assertTrue(bool(g._pulse_same),
            "RED: throttled frame must retain the same owned flash primitive")
        self.assertTrue(bool(g._pulse_visible),
            "RED: event pulse must survive inconsistent native geometry")
        self.assertTrue(bool(g._pulse_full_shape),
            "RED: pulsed frame must keep the full original row icon shape")
        self.assertAlmostEqual(float(g._pulse_alpha), .5, delta=.08,
            msg="RED: pulse alpha must follow the 0.6 s game-clock fade")
        self.assertTrue(bool(g._pulse_cyan),
            "RED: inconsistent native color must not replace the owned cyan")
        self.assertTrue(bool(g._pulse_cert),
            "RED: event pulse must stay certified while native geometry disagrees")
        self.assertTrue(bool(g._pulse_ghosts_false),
            "RED: native ghosts must keep their visible lease, not be repainted")
        self.assertTrue(bool(g._pulse_group_present),
            "RED: the flash H5 group must stay held on a throttled pulse frame")
        self.assertTrue(bool(g._pulse_sentinel_ok))
        self.assertTrue(_sentinel_ok(g))

        lua.execute(r'''
            local function finish(ghost, base)
                ghost:set_shape(base:x(), base:y(), base:w(), base:h())
                ghost:set_color(Color(0, 1, 1, 1))
                ghost:set_visible(false)
            end
            finish(_G._flash_event_radial_ghost, _radial)
            finish(_G._flash_event_icon_ghost, _icon)
            _game_clock:set_time(1000.61)
            local before = _E._rows[4]._grenade_flash
            _R:update(_m, 1.22, .01)
            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            _G._terminal_same = flash == before
            _G._terminal_hidden = flash == nil or flash:visible() == false
            _G._terminal_group_absent = _R._h5_groups == nil
                or _R._h5_groups.local_p_grenade_flash == nil
            _G._terminal_ghosts_false = _G._flash_event_radial_ghost:visible() == false
                and _G._flash_event_icon_ghost:visible() == false
            local snap = _E:get_snapshot()
            _G._terminal_charges = snap.projectile.charges.raw
            _G._terminal_maximum = snap.projectile.maximum.raw
            _G._terminal_cooldown_active = snap.cooldown.known == true
                and snap.cooldown.active == true
            _G._terminal_sentinel_ok = _G._flash_event_sentinel:visible() == true
                and _G._flash_event_sentinel:parent() == _gren
        ''')
        self.assertTrue(bool(g._terminal_same),
            "terminal completion must use the same owned bitmap")
        self.assertTrue(bool(g._terminal_hidden),
            "RED: terminal native completion must hide the owned pulse")
        self.assertTrue(bool(g._terminal_group_absent),
            "RED: terminal native completion must release the flash H5 group")
        self.assertTrue(bool(g._terminal_ghosts_false),
            "RED: release must not resurrect either native ghost")
        self.assertEqual(float(g._terminal_charges), 1.0)
        self.assertEqual(float(g._terminal_maximum), 2.0)
        self.assertTrue(bool(g._terminal_cooldown_active),
            "RECHARGE/cooldown must keep running after the pulse ends")
        self.assertTrue(bool(g._terminal_sentinel_ok))
        self.assertTrue(_sentinel_ok(g))

        lua.execute(r'''
            _game_clock:set_time(2000)
            _emit_flash(2)
            local function finish(ghost, base)
                ghost:set_shape(base:x(), base:y(), base:w(), base:h())
                ghost:set_color(Color(0, 1, 1, 1))
                ghost:set_visible(false)
            end
            finish(_G._flash_event_radial_ghost, _radial)
            finish(_G._flash_event_icon_ghost, _icon)
            _R:update(_m, 1.23, .01)
            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            _G._remote_hidden = flash == nil or flash:visible() == false
            _G._remote_group_absent = _R._h5_groups == nil
                or _R._h5_groups.local_p_grenade_flash == nil
            _G._remote_ghosts_false = _G._flash_event_radial_ghost:visible() == false
                and _G._flash_event_icon_ghost:visible() == false
            _G._remote_native_calls = _G._native_flash_calls
            local snap = _E:get_snapshot()
            _G._remote_charges = snap.projectile.charges.raw
            _G._remote_maximum = snap.projectile.maximum.raw
        ''')
        self.assertTrue(bool(g._remote_hidden),
            "RED: a remote-slot animate_grenade_flash must not start the local pulse")
        self.assertTrue(bool(g._remote_group_absent),
            "RED: a remote event must not acquire the local flash group")
        self.assertTrue(bool(g._remote_ghosts_false))
        self.assertEqual(int(g._remote_native_calls), 2,
            "native method must still be called for the remote slot")
        self.assertEqual(float(g._remote_charges), 1.0)
        self.assertEqual(float(g._remote_maximum), 2.0)

    def test_refresh_registry_swap_does_not_reauthorize_captured_event(self):
        lua = _event_lua()
        g = lua.globals()

        lua.execute(r'''
            _game_clock:set_time(1000)
            _emit_flash(HUDManager.PLAYER_PANEL)
            _R:update(_m, 1.20, .08)

            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            local rg = _G._flash_event_radial_ghost
            local ig = _G._flash_event_icon_ghost
            _G._reg_flash = flash
            _G._reg_initial_cert = flash ~= nil
                and _E._grenade_flash_ok == true
                and row._flash_active == true
                and row:_verify_grenade_flash() == true
                and _E:verify() == true
            _G._reg_initial_ghosts_leased = rg:visible() == false
                and ig:visible() == false
            _G._reg_generation = _E._source_generation

            local holder = managers.player._global
            local old_registry = holder.synced_grenades
            local new_registry = {}
            for key, value in pairs(old_registry) do
                new_registry[key] = value
            end
            new_registry[1] = old_registry[1]
            holder.synced_grenades = new_registry
            _E:refresh(_m)

            _G._reg_registry_replaced = holder.synced_grenades == new_registry
            _G._reg_entry_same = old_registry[1] ~= nil
                and holder.synced_grenades[1] == old_registry[1]
            _G._reg_generation_after = _E._source_generation

            _game_clock:set_time(1000.2)
            _R:update(_m, 1.21, .01)

            row = _E._rows[4]
            flash = row and row._grenade_flash
            _G._reg_old_hidden = flash == nil or flash:visible() == false
            _G._reg_ghosts_true = rg:visible() == true and ig:visible() == true
            _G._reg_group_absent = _R._h5_groups == nil
                or _R._h5_groups.local_p_grenade_flash == nil
            _G._reg_flash_ok_false = _E._grenade_flash_ok == false
            local snap = _E:get_snapshot()
            _G._reg_charges = snap.projectile.charges.raw
            _G._reg_maximum = snap.projectile.maximum.raw
            _G._reg_cooldown_active = snap.cooldown.known == true
                and snap.cooldown.active == true

            _game_clock:set_time(1000.25)
            _emit_flash(HUDManager.PLAYER_PANEL)
            _R:update(_m, 1.30, .09)

            row = _E._rows[4]
            local recovered = row and row._grenade_flash
            _G._reg_recovered_same = recovered == _G._reg_flash
            _G._reg_recovered_cert = recovered ~= nil
                and _E._grenade_flash_ok == true
                and row._flash_active == true
                and row:_verify_grenade_flash() == true
                and _E:verify() == true
            _G._reg_recovered_ghosts_false = rg:visible() == false
                and ig:visible() == false
            _G._reg_recovered_group_present = _R._h5_groups ~= nil
                and _R._h5_groups.local_p_grenade_flash ~= nil
            snap = _E:get_snapshot()
            _G._reg_recovered_charges = snap.projectile.charges.raw
            _G._reg_recovered_maximum = snap.projectile.maximum.raw
            _G._reg_recovered_cooldown_active = snap.cooldown.known == true
                and snap.cooldown.active == true
        ''')

        self.assertTrue(bool(g._reg_initial_cert),
            "precondition: the local event must start a certified owned pulse")
        self.assertTrue(bool(g._reg_initial_ghosts_leased),
            "precondition: both native ghosts must be leased hidden initially")
        self.assertTrue(bool(g._reg_registry_replaced),
            "the fixture must replace synced_grenades with a new table")
        self.assertTrue(bool(g._reg_entry_same),
            "the new registry must keep the exact same local peer entry")
        self.assertEqual(g._reg_generation, g._reg_generation_after,
            "precondition: a pure synced_grenades table swap must not advance "
            "the captured source generation (remove this precondition if the "
            "actual counter includes registry identity)")
        self.assertTrue(bool(g._reg_old_hidden),
            "RED: the old event must not authorize the refreshed registry; "
            "the owned flash must be hidden")
        self.assertTrue(bool(g._reg_ghosts_true),
            "RED: the old event must release both native ghosts after refresh")
        self.assertTrue(bool(g._reg_group_absent),
            "RED: the old event must leave no local_p_grenade_flash H5 group")
        self.assertTrue(bool(g._reg_flash_ok_false),
            "RED: the old event must no longer certify the owned flash")
        self.assertEqual(float(g._reg_charges), 1.0,
            "the registry swap must not change the grenade counter")
        self.assertEqual(float(g._reg_maximum), 2.0)
        self.assertTrue(bool(g._reg_cooldown_active),
            "RECHARGE must keep running through the registry swap")
        self.assertTrue(bool(g._reg_recovered_same),
            "a new native event must reuse the same owned flash primitive")
        self.assertTrue(bool(g._reg_recovered_cert),
            "a new native event on the valid registry must certify again")
        self.assertTrue(bool(g._reg_recovered_ghosts_false),
            "a recovered event must lease both native ghosts hidden")
        self.assertTrue(bool(g._reg_recovered_group_present),
            "a recovered event must reacquire local_p_grenade_flash")
        self.assertEqual(float(g._reg_recovered_charges), 1.0,
            "recovery must not change the grenade counter")
        self.assertEqual(float(g._reg_recovered_maximum), 2.0)
        self.assertTrue(bool(g._reg_recovered_cooldown_active),
            "RECHARGE must keep running after recovery")

    def test_same_event_corruption_repair_backward_clock_and_new_epoch(self):
        lua = _event_lua()
        g = lua.globals()

        lua.execute(r'''
            _game_clock:set_time(1000)
            _emit_flash(HUDManager.PLAYER_PANEL)
            _R:update(_m, 1.20, .08)

            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            local rg = _G._flash_event_radial_ghost
            local ig = _G._flash_event_icon_ghost
            _G._life_flash = flash
            _G._life_initial_cert = flash ~= nil
                and _E._grenade_flash_ok == true
                and row._flash_active == true
                and row:_verify_grenade_flash() == true
                and _E:verify() == true
            _G._life_initial_ghosts_leased = rg:visible() == false
                and ig:visible() == false

            flash:set_color(Color(1, 1, 1, 1))
            flash:set_alpha(.2)

            _game_clock:set_time(1000.1)
            _R:update(_m, 1.21, .01)

            row = _E._rows[4]
            local throttled = row and row._grenade_flash
            _G._life_throttle_same = throttled == _G._life_flash
            _G._life_throttle_hidden = throttled ~= nil
                and throttled:visible() == false
            _G._life_throttle_alpha = throttled and throttled:alpha() or -1
            _G._life_throttle_cert_false = _E._grenade_flash_ok == false
                and row:_verify_grenade_flash() == false
            _G._life_throttle_ghosts_true = rg:visible() == true
                and ig:visible() == true
            _G._life_throttle_group_absent = _R._h5_groups == nil
                or _R._h5_groups.local_p_grenade_flash == nil
            local snap = _E:get_snapshot()
            _G._life_throttle_charges = snap.projectile.charges.raw
            _G._life_throttle_maximum = snap.projectile.maximum.raw
            _G._life_throttle_cooldown_active = snap.cooldown.known == true
                and snap.cooldown.active == true

            _game_clock:set_time(1000.2)
            _R:update(_m, 1.30, .09)

            row = _E._rows[4]
            local repaired = row and row._grenade_flash
            local color = repaired and repaired:color()
            _G._life_repair_same = repaired == _G._life_flash
            _G._life_repair_cyan = color ~= nil and color.r < .5
                and color.g > .5 and color.b > .5
            _G._life_repair_cert = repaired ~= nil
                and _E._grenade_flash_ok == true
                and row._flash_active == true
                and row:_verify_grenade_flash() == true
                and _E:verify() == true
            _G._life_repair_ghosts_false = rg:visible() == false
                and ig:visible() == false
            _G._life_repair_group_present = _R._h5_groups ~= nil
                and _R._h5_groups.local_p_grenade_flash ~= nil

            _game_clock:set_time(1000.3)
            _R:update(_m, 1.31, .01)

            _G._life_native_replenish_before = managers.player._timers.replenish_grenades
            _G._life_native_replenish_present = _G._life_native_replenish_before ~= nil

            _game_clock:set_time(1000.25)
            _R:update(_m, 1.32, .01)

            row = _E._rows[4]
            local backward = row and row._grenade_flash
            _G._life_backward_hidden = backward == nil
                or backward:visible() == false
            _G._life_backward_cert_false = _E._grenade_flash_ok == false
                and _E:_verify_grenade_flash() == false
            _G._life_backward_group_absent = _R._h5_groups == nil
                or _R._h5_groups.local_p_grenade_flash == nil
            _G._life_backward_ghosts_true = rg:visible() == true
                and ig:visible() == true
            snap = _E:get_snapshot()
            _G._life_backward_charges = snap.projectile.charges.raw
            _G._life_backward_maximum = snap.projectile.maximum.raw
            _G._life_backward_cooldown_unknown = snap.cooldown.known ~= true
                and snap.cooldown.active ~= true
            _G._life_native_replenish_same =
                managers.player._timers.replenish_grenades
                    == _G._life_native_replenish_before

            _game_clock:set_time(1000.4)
            _emit_flash(HUDManager.PLAYER_PANEL)
            _R:update(_m, 1.40, .09)

            row = _E._rows[4]
            local recovered = row and row._grenade_flash
            _G._life_recovered_same = recovered == _G._life_flash
            _G._life_recovered_cert = recovered ~= nil
                and _E._grenade_flash_ok == true
                and row._flash_active == true
                and row:_verify_grenade_flash() == true
                and _E:verify() == true
            _G._life_recovered_ghosts_false = rg:visible() == false
                and ig:visible() == false
            _G._life_recovered_group_present = _R._h5_groups ~= nil
                and _R._h5_groups.local_p_grenade_flash ~= nil
            snap = _E:get_snapshot()
            _G._life_recovered_charges = snap.projectile.charges.raw
            _G._life_recovered_maximum = snap.projectile.maximum.raw
            _G._life_recovered_cooldown_active = snap.cooldown.known == true
                and snap.cooldown.active == true
        ''')

        self.assertTrue(bool(g._life_initial_cert),
            "precondition: the local event must start a certified owned pulse")
        self.assertTrue(bool(g._life_initial_ghosts_leased),
            "precondition: both native ghosts must be leased hidden initially")
        self.assertTrue(bool(g._life_throttle_same),
            "a throttled corruption must retain the same owned flash bitmap")
        self.assertTrue(bool(g._life_throttle_hidden),
            "a corrupted owned flash must be hidden on the throttled update")
        self.assertAlmostEqual(float(g._life_throttle_alpha), .2, delta=.01,
            msg="a throttled update must not silently repair the corrupted "
                "owned flash alpha")
        self.assertTrue(bool(g._life_throttle_cert_false),
            "the corrupted owned flash must fail certification on throttle")
        self.assertTrue(bool(g._life_throttle_ghosts_true),
            "a corrupted owned flash must restore both native ghosts")
        self.assertTrue(bool(g._life_throttle_group_absent),
            "a corrupted owned flash must release local_p_grenade_flash")
        self.assertEqual(float(g._life_throttle_charges), 1.0,
            "corruption must not change the grenade counter")
        self.assertEqual(float(g._life_throttle_maximum), 2.0)
        self.assertTrue(bool(g._life_throttle_cooldown_active),
            "RECHARGE must keep running through the corrupted throttle")
        self.assertTrue(bool(g._life_repair_same),
            "an ordinary update must repair the same owned flash bitmap")
        self.assertTrue(bool(g._life_repair_cyan),
            "an ordinary repair must restore the owned cyan pulse")
        self.assertTrue(bool(g._life_repair_cert),
            "an ordinary repair must recertify the owned flash")
        self.assertTrue(bool(g._life_repair_ghosts_false),
            "an ordinary repair must lease both native ghosts hidden")
        self.assertTrue(bool(g._life_repair_group_present),
            "an ordinary repair must reacquire local_p_grenade_flash")
        self.assertTrue(bool(g._life_backward_hidden),
            "a backward game clock must hide the owned flash mirror")
        self.assertTrue(bool(g._life_backward_cert_false),
            "a backward game clock must fail owned flash certification")
        self.assertTrue(bool(g._life_backward_group_absent),
            "a backward game clock must release local_p_grenade_flash")
        self.assertTrue(bool(g._life_backward_ghosts_true),
            "a backward game clock must restore both native ghosts")
        self.assertEqual(float(g._life_backward_charges), 1.0,
            "a backward game clock must not change the grenade counter")
        self.assertEqual(float(g._life_backward_maximum), 2.0)
        self.assertTrue(bool(g._life_native_replenish_present),
            "precondition: the actual native replenish timer must exist before "
            "the backward clock")
        self.assertTrue(bool(g._life_backward_cooldown_unknown),
            "a backward clock must invalidate the untrusted time-derived recharge "
            "display without forcing it active or inactive")
        self.assertTrue(bool(g._life_native_replenish_same),
            "a backward clock must preserve the actual native replenish timer "
            "object")
        self.assertTrue(bool(g._life_recovered_same),
            "a new real native event must reuse the same owned flash bitmap")
        self.assertTrue(bool(g._life_recovered_cert),
            "a new real native event must reset the epoch and recertify")
        self.assertTrue(bool(g._life_recovered_ghosts_false),
            "the recovered epoch must lease both native ghosts hidden")
        self.assertTrue(bool(g._life_recovered_group_present),
            "the recovered epoch must reacquire local_p_grenade_flash")
        self.assertEqual(float(g._life_recovered_charges), 1.0,
            "recovery must not change the grenade counter")
        self.assertEqual(float(g._life_recovered_maximum), 2.0)
        self.assertTrue(bool(g._life_recovered_cooldown_active),
            "RECHARGE must keep running after the new native event")

    def test_event_stock_pre_clamp_off_on_and_completion(self):
        lua = _event_lua()
        lua.execute(r'''
            local slot = HUDManager.PLAYER_PANEL
            local function snap() return _E:get_snapshot() end
            _game_clock:set_time(1000)
            managers.player:_native_set_grenades("pocket", 0, 2)
            dispatch(HUDManager, "set_teammate_grenades_amount", managers.hud, slot, {amount = 0, icon = "frag_grenade"})
            _G._pre_charges = snap().projectile.charges.raw
            _G._pre_maximum = snap().projectile.maximum.raw
            _G._event_stock = _G._pre_charges
            _G._emit_return = _emit_flash(slot)
            _G._emit_same = _G._emit_return == _G._native_flash_expected_return
            _G._calls_after_emit = _native_flash_calls
            managers.player:_native_set_grenades("pocket", 1, 2)
            dispatch(HUDManager, "set_teammate_grenades_amount", managers.hud, slot, {amount = 1, icon = "frag_grenade"})
            _G._post_charges = snap().projectile.charges.raw
            _G._post_maximum = snap().projectile.maximum.raw
            _R:update(_m, 1.20, .08)
            local row = _E._rows[slot]
            local flash = row and row._grenade_flash
            local icon = row and row._icon
            local c = flash and flash:color()
            _G._pulse_visible = flash ~= nil and flash:visible()
            _G._pulse_cyan = c ~= nil and math.abs(c.r - .15) <= .001
                and math.abs(c.g - .85) <= .001 and math.abs(c.b - 1) <= .001
            _G._pulse_full = flash ~= nil and icon ~= nil and math.abs(flash:w() - icon:w()) <= .05 and math.abs(flash:h() - icon:h()) <= .05
            _G._pulse_cert = _E:verify() == true and _E._visible_rows[slot] == true and row._root:visible() == true
            _G._snap_ok = snap().projectile.charges.raw == 1 and snap().projectile.maximum.raw == 2
            _G._recharge_ok = snap().cooldown.known == true and snap().cooldown.active == true
            _G._ghosts_first = _flash_event_radial_ghost:visible() == false and _flash_event_icon_ghost:visible() == false
            _G._pulse_seen = flash ~= nil
            _G._root = row._root
            _G._radial_handle = _gren:child("grenades_radial_ghost")
            _G._icon_handle = _gren:child("grenades_icon_ghost")
            kyohud.settings.enable_equipment = false
            _R:refresh_settings(_m)
            _game_clock:set_time(1000.1)
            _R:update(_m, 1.21, .08)
            _G._off_ghosts = _flash_event_radial_ghost:visible() == true and _flash_event_icon_ghost:visible() == true and _gren:child("grenades_radial_ghost") == _G._radial_handle and _gren:child("grenades_icon_ghost") == _G._icon_handle
            _G._off_group = _R._h5_groups == nil or _R._h5_groups.local_p_grenade_flash == nil
            _G._off_root_hidden = _E._root == nil or _E._root:visible() == false
            _G._off_root_unmounted = _E._root == nil
            _G._off_calls = _native_flash_calls == 1
            kyohud.settings.enable_equipment = true
            _R:refresh_settings(_m)
            _game_clock:set_time(1000.2)
            _R:update(_m, 1.30, .09)
            row = _E._rows[slot]
            flash = row and row._grenade_flash
            c = flash and flash:color()
            _G._on_visible = flash ~= nil and flash:visible()
            _G._on_cyan = c ~= nil and math.abs(c.r - .15) <= .001
                and math.abs(c.g - .85) <= .001 and math.abs(c.b - 1) <= .001
            _G._on_alpha = flash ~= nil and math.abs(flash:alpha() - (2 / 3)) <= .02
            _G._on_cert = _E:verify() == true and _E._visible_rows[slot] == true and row._root:visible() == true
            _G._on_ghosts = _flash_event_radial_ghost:visible() == false and _flash_event_icon_ghost:visible() == false
            _G._on_counts = snap().projectile.charges.raw == 1 and snap().projectile.maximum.raw == 2
            _G._on_recharge = snap().cooldown.known == true and snap().cooldown.active == true
            _G._on_calls = _native_flash_calls == 1
            _G._on_group = _R._h5_groups ~= nil and _R._h5_groups.local_p_grenade_flash ~= nil
            _G._on_sources = _gren:child("grenades_radial_ghost") == _G._radial_handle and _gren:child("grenades_icon_ghost") == _G._icon_handle
            local function finish(ghost, base)
                ghost:set_shape(base:x(), base:y(), base:w(), base:h())
                ghost:set_color(Color(0, 1, 1, 1)); ghost:set_visible(false)
            end
            finish(_flash_event_radial_ghost, _radial)
            finish(_flash_event_icon_ghost, _icon)
            _game_clock:set_time(1000.61)
            _R:update(_m, 1.40, .08)
            row = _E._rows[slot]
            flash = row and row._grenade_flash
            _G._done_hidden = flash == nil or flash:visible() == false
            _G._done_group = _R._h5_groups == nil or _R._h5_groups.local_p_grenade_flash == nil
            _G._done_ghosts = _flash_event_radial_ghost:visible() == false and _flash_event_icon_ghost:visible() == false
            _G._done_counts = snap().projectile.charges.raw == 1 and snap().projectile.maximum.raw == 2
            _G._done_calls = _native_flash_calls == 1
        ''')
        g = lua.globals()
        self.assertEqual(float(g._event_stock), 0.0,
            "the real event must capture stock 0 before any clamp")
        for name, expected in (("_pre_charges", 0), ("_pre_maximum", 2),
            ("_calls_after_emit", 1), ("_post_charges", 1),
            ("_post_maximum", 2)):
            self.assertEqual(float(getattr(g, name)), float(expected), name)
        for name in (
            "_emit_same", "_pulse_visible", "_pulse_cyan", "_pulse_full",
            "_pulse_cert", "_snap_ok", "_recharge_ok", "_ghosts_first",
            "_pulse_seen", "_off_ghosts", "_off_group", "_off_root_hidden",
            "_off_root_unmounted", "_off_calls", "_on_visible", "_on_cyan",
            "_on_alpha", "_on_cert", "_on_ghosts", "_on_counts",
            "_on_recharge", "_on_calls", "_on_group", "_on_sources",
            "_done_hidden", "_done_group", "_done_ghosts", "_done_counts",
            "_done_calls",
        ):
            self.assertTrue(bool(getattr(g, name)), name)


if __name__ == "__main__":
    unittest.main()
