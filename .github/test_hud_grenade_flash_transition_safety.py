"""Transition-safety contract for the owned grenade-flash event seam.

These tests exercise the real registered `HUDManager:animate_grenade_flash`
POSTHOOK and the shared flash runtime through `_event_lua`. They pin the desired
contract, not the currently defective baseline:

1. A second local event observed before any runtime update must keep the new
   certified cyan owned pulse, keep both native ghosts leased hidden through the
   real H5 group, and still preserve the native call/return.
2. An error injected after the real `_present` body must fail closed: hide the
   owned flash, leave both native ghosts positive, release the flash H5 lease,
   clear the reentrancy latch, and then recover on the next real event.
3. A stale event whose first tail observation happens long after its start must
   be retired immediately and must not rearm or fall back on the next update.
"""
import unittest

from test_hud_grenade_flash_event import _event_lua, _sentinel_ok


class GrenadeFlashTransitionSafetyTests(unittest.TestCase):
    def test_second_local_event_keeps_certified_pulse_and_real_lease(self):
        lua = _event_lua()
        g = lua.globals()

        lua.execute(r'''
            _game_clock:set_time(1000)
            _G._t1_first_return = _emit_flash(HUDManager.PLAYER_PANEL)
            _game_clock:set_time(1000.1)
            _G._t1_second_return = _emit_flash(HUDManager.PLAYER_PANEL)

            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            local rg = _G._flash_event_radial_ghost
            local ig = _G._flash_event_icon_ghost
            _G._t1_flash = flash
            _G._t1_visible = flash ~= nil and flash:visible() == true
            local c = flash and flash:color()
            _G._t1_cyan = c ~= nil and c.r < .5 and c.g > .5 and c.b > .5
            _G._t1_alpha_positive = flash ~= nil
                and type(flash:alpha()) == "number" and flash:alpha() > 0
            _G._t1_cert = flash ~= nil and _E._grenade_flash_ok == true
                and row._flash_active == true
                and row:_verify_grenade_flash() == true
                and _E:verify() == true
            _G._t1_ghosts_false = rg:visible() == false and ig:visible() == false
            _G._t1_group_present = _R._h5_groups ~= nil
                and _R._h5_groups.local_p_grenade_flash ~= nil
            _G._t1_held_radial = _R:_h5_group_holds_visible(
                "local_p_grenade_flash", rg) == true
            _G._t1_held_icon = _R:_h5_group_holds_visible(
                "local_p_grenade_flash", ig) == true
            _G._t1_native_calls = _G._native_flash_calls
            local expected = _G._native_flash_expected_return
            _G._t1_returns = _G._t1_first_return == expected
                and _G._t1_second_return == expected
                and _G._native_flash_return == expected
            local snap = _E:get_snapshot()
            _G._t1_charges = snap.projectile.charges.raw
            _G._t1_maximum = snap.projectile.maximum.raw
            _G._t1_recharge = snap.cooldown.known == true
                and snap.cooldown.active == true
        ''')

        self.assertTrue(bool(g._t1_visible),
            "RED: the second event must keep the owned pulse visible")
        self.assertTrue(bool(g._t1_cyan),
            "RED: the second event must keep the owned pulse cyan")
        self.assertTrue(bool(g._t1_alpha_positive),
            "RED: the second event pulse must have a positive alpha")
        self.assertTrue(bool(g._t1_cert),
            "RED: the second event pulse must stay certified")
        self.assertTrue(bool(g._t1_ghosts_false),
            "RED: the second event must keep both native ghosts hidden")
        self.assertTrue(bool(g._t1_group_present),
            "RED: the second event must hold local_p_grenade_flash")
        self.assertTrue(bool(g._t1_held_radial),
            "RED: the real H5 group must hold the radial ghost")
        self.assertTrue(bool(g._t1_held_icon),
            "RED: the real H5 group must hold the icon ghost")
        self.assertEqual(int(g._t1_native_calls), 2,
            "the native method must be called once per event")
        self.assertTrue(bool(g._t1_returns),
            "RED: both native calls must preserve the original return")
        self.assertEqual(float(g._t1_charges), 1.0,
            "transition must not change the grenade stock")
        self.assertEqual(float(g._t1_maximum), 2.0)
        self.assertTrue(bool(g._t1_recharge),
            "RECHARGE must remain active through the second event")
        self.assertTrue(_sentinel_ok(g))

    def test_present_error_fails_closed_and_next_event_recovers(self):
        lua = _event_lua()
        g = lua.globals()

        lua.execute(r'''
            local slot = HUDManager.PLAYER_PANEL
            _G._t2_present_original = _E._present
            _E._present = function(self)
                _G._t2_present_original(self)
                error("injected_after_present")
            end
            _game_clock:set_time(1000)
            _G._t2_first_return = _emit_flash(slot)

            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            local rg = _G._flash_event_radial_ghost
            local ig = _G._flash_event_icon_ghost
            _G._t2_flash = flash
            _G._t2_latch_cleared = _R._local_flash_event_sync == false
            _G._t2_hidden = flash == nil or flash:visible() == false
            _G._t2_owned_ok_false = _E._grenade_flash_ok == false
            _G._t2_source_absent = _E._grenade_flash_source == nil
            _G._t2_ghosts_true = rg:visible() == true and ig:visible() == true
            _G._t2_group_absent = _R._h5_groups == nil
                or _R._h5_groups.local_p_grenade_flash == nil
            _G._t2_first_return_ok = _G._t2_first_return
                == _G._native_flash_expected_return
            _G._t2_sentinel_first = _G._flash_event_sentinel:visible() == true
                and _G._flash_event_sentinel:parent() == _gren

            _E._present = _G._t2_present_original
            _game_clock:set_time(1000.1)
            _G._t2_second_return = _emit_flash(slot)

            row = _E._rows[4]
            local recovered = row and row._grenade_flash
            rg = _G._flash_event_radial_ghost
            ig = _G._flash_event_icon_ghost
            _G._t2_recovered_same = recovered ~= nil
                and recovered == _G._t2_flash
            _G._t2_recovered_visible = recovered ~= nil
                and recovered:visible() == true
            _G._t2_recovered_cert = recovered ~= nil
                and _E._grenade_flash_ok == true
                and row._flash_active == true
                and row:_verify_grenade_flash() == true
                and _E:verify() == true
            _G._t2_recovered_ghosts_false = rg:visible() == false
                and ig:visible() == false
            _G._t2_recovered_group = _R._h5_groups ~= nil
                and _R._h5_groups.local_p_grenade_flash ~= nil
            _G._t2_recovered_held_radial = _R:_h5_group_holds_visible(
                "local_p_grenade_flash", rg) == true
            _G._t2_recovered_held_icon = _R:_h5_group_holds_visible(
                "local_p_grenade_flash", ig) == true
            _G._t2_native_calls = _G._native_flash_calls
            _G._t2_returns_ok = _G._t2_first_return
                    == _G._native_flash_expected_return
                and _G._t2_second_return == _G._native_flash_expected_return
                and _G._native_flash_return == _G._native_flash_expected_return
            _G._t2_latch_after = _R._local_flash_event_sync == false
            local snap = _E:get_snapshot()
            _G._t2_charges = snap.projectile.charges.raw
            _G._t2_maximum = snap.projectile.maximum.raw
            _G._t2_recharge = snap.cooldown.known == true
                and snap.cooldown.active == true
        ''')

        self.assertTrue(bool(g._t2_latch_cleared),
            "RED: the reentrancy latch must be cleared after the injected error")
        self.assertTrue(bool(g._t2_hidden),
            "RED: a failed present must hide the owned flash")
        self.assertTrue(bool(g._t2_owned_ok_false),
            "RED: a failed present must drop the stale certification")
        self.assertTrue(bool(g._t2_source_absent),
            "RED: a failed present must clear the owned flash source")
        self.assertTrue(bool(g._t2_ghosts_true),
            "RED: fail-closed cleanup must leave both native ghosts positive")
        self.assertTrue(bool(g._t2_group_absent),
            "RED: fail-closed cleanup must release the flash H5 lease")
        self.assertTrue(bool(g._t2_first_return_ok),
            "the native return must survive the injected present error")
        self.assertTrue(bool(g._t2_sentinel_first))
        self.assertTrue(_sentinel_ok(g))

        self.assertTrue(bool(g._t2_recovered_same),
            "RED: the next real event must reuse the same owned bitmap")
        self.assertTrue(bool(g._t2_recovered_visible),
            "RED: the recovered owned flash must be visible")
        self.assertTrue(bool(g._t2_recovered_cert),
            "RED: the recovered owned flash must be certified again")
        self.assertTrue(bool(g._t2_recovered_ghosts_false),
            "RED: recovery must lease both native ghosts hidden")
        self.assertTrue(bool(g._t2_recovered_group),
            "RED: recovery must reacquire local_p_grenade_flash")
        self.assertTrue(bool(g._t2_recovered_held_radial),
            "RED: recovery must hold the radial ghost through the real H5 group")
        self.assertTrue(bool(g._t2_recovered_held_icon),
            "RED: recovery must hold the icon ghost through the real H5 group")
        self.assertEqual(int(g._t2_native_calls), 2,
            "both real events must call the native method")
        self.assertTrue(bool(g._t2_returns_ok),
            "native returns must be preserved across error and recovery")
        self.assertTrue(bool(g._t2_latch_after),
            "the latch must stay clear after recovery")
        self.assertEqual(float(g._t2_charges), 1.0,
            "error and recovery must not change the grenade stock")
        self.assertEqual(float(g._t2_maximum), 2.0)
        self.assertTrue(bool(g._t2_recharge),
            "RECHARGE must keep running through error and recovery")
        self.assertTrue(_sentinel_ok(g))

    def test_stale_event_first_tail_observation_expires_without_rearm(self):
        lua = _event_lua()
        g = lua.globals()

        lua.execute(r'''
            local slot = HUDManager.PLAYER_PANEL
            _game_clock:set_time(1000)
            _emit_flash(slot)

            local rg = _G._flash_event_radial_ghost
            local ig = _G._flash_event_icon_ghost
            rg:set_shape(_radial:x(), _radial:y(), _radial:w(), _radial:h())
            ig:set_shape(_icon:x(), _icon:y(), _icon:w(), _icon:h())
            rg:set_color(Color(1, 1, 1, 1))
            ig:set_color(Color(1, 1, 1, 1))

            local row = _E._rows[4]
            _G._t3_armed_group = _R._h5_groups ~= nil
                and _R._h5_groups.local_p_grenade_flash ~= nil
            _G._t3_armed_ghosts = rg:visible() == false and ig:visible() == false
                and rg:color().a > 0 and ig:color().a > 0
                and _R:_h5_group_holds_visible("local_p_grenade_flash", rg) == true
                and _R:_h5_group_holds_visible("local_p_grenade_flash", ig) == true
            _G._t3_armed_owned = row ~= nil and row._grenade_flash ~= nil
                and row._grenade_flash:visible() == true

            _game_clock:set_time(1010)
            _R:update(_m, 1.20, .08)

            row = _E._rows[4]
            local flash = row and row._grenade_flash
            _G._t3_first_hidden = flash == nil or flash:visible() == false
            _G._t3_first_ghosts = rg:visible() == true and ig:visible() == true
            _G._t3_first_group_absent = _R._h5_groups == nil
                or _R._h5_groups.local_p_grenade_flash == nil
            _G._t3_first_ok_false = _E._grenade_flash_ok == false
            local event = _E._grenade_flash_event
            _G._t3_first_retired = event == nil or event.expired == true
                or event.invalid == true
            local snap = _E:get_snapshot()
            _G._t3_first_charges = snap.projectile.charges.raw
            _G._t3_first_maximum = snap.projectile.maximum.raw
            _G._t3_first_recharge = snap.cooldown.known == true
                and snap.cooldown.active == true
            _G._t3_first_sentinel = _G._flash_event_sentinel:visible() == true
                and _G._flash_event_sentinel:parent() == _gren

            _game_clock:set_time(1010.01)
            _R:update(_m, 1.21, .01)

            row = _E._rows[4]
            flash = row and row._grenade_flash
            _G._t3_second_hidden = flash == nil or flash:visible() == false
            _G._t3_second_ghosts = rg:visible() == true and ig:visible() == true
            _G._t3_second_group_absent = _R._h5_groups == nil
                or _R._h5_groups.local_p_grenade_flash == nil
            _G._t3_second_ok_false = _E._grenade_flash_ok == false
            event = _E._grenade_flash_event
            _G._t3_second_retired = event == nil or event.expired == true
                or event.invalid == true
            snap = _E:get_snapshot()
            _G._t3_second_charges = snap.projectile.charges.raw
            _G._t3_second_maximum = snap.projectile.maximum.raw
            _G._t3_second_recharge = snap.cooldown.known == true
                and snap.cooldown.active == true
            _G._t3_second_sentinel = _G._flash_event_sentinel:visible() == true
                and _G._flash_event_sentinel:parent() == _gren
        ''')

        self.assertTrue(bool(g._t3_armed_group),
            "precondition: the local event must have acquired the flash H5 group")
        self.assertTrue(bool(g._t3_armed_ghosts),
            "precondition: both native ghosts must be alpha-positive under the "
            "legitimate held lease before the jump")
        self.assertTrue(bool(g._t3_armed_owned),
            "precondition: the first event must own a visible pulse")

        self.assertTrue(bool(g._t3_first_hidden),
            "RED: the first stale tail observation must hide the owned flash")
        self.assertTrue(bool(g._t3_first_ghosts),
            "RED: the first stale tail observation must restore both natives")
        self.assertTrue(bool(g._t3_first_group_absent),
            "RED: the first stale tail observation must release the flash lease")
        self.assertTrue(bool(g._t3_first_ok_false),
            "RED: the stale event must not stay certified")
        self.assertTrue(bool(g._t3_first_retired),
            "RED: a stale event must be retired on its first tail read")
        self.assertEqual(float(g._t3_first_charges), 1.0,
            "stale expiry must not change the grenade stock")
        self.assertEqual(float(g._t3_first_maximum), 2.0)
        self.assertTrue(bool(g._t3_first_recharge),
            "RECHARGE must keep running after stale expiry")
        self.assertTrue(bool(g._t3_first_sentinel))
        self.assertTrue(_sentinel_ok(g))

        self.assertTrue(bool(g._t3_second_hidden),
            "RED: a retired event must not rearm the owned flash")
        self.assertTrue(bool(g._t3_second_ghosts),
            "RED: a retired event must leave both natives positive")
        self.assertTrue(bool(g._t3_second_group_absent),
            "RED: a retired event must not fall back to an H5 lease")
        self.assertTrue(bool(g._t3_second_ok_false),
            "RED: a retired event must not certify again")
        self.assertTrue(bool(g._t3_second_retired),
            "RED: the expired record must stay retired")
        self.assertEqual(float(g._t3_second_charges), 1.0,
            "the second stale update must not change the grenade stock")
        self.assertEqual(float(g._t3_second_maximum), 2.0)
        self.assertTrue(bool(g._t3_second_recharge),
            "RECHARGE must keep running after the second stale update")
        self.assertTrue(bool(g._t3_second_sentinel))
        self.assertTrue(_sentinel_ok(g))


if __name__ == "__main__":
    unittest.main()
