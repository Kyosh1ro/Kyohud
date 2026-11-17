"""Cooldown-to-flash H5 handoff for the native radial's final progress frame.

When a known-inactive grenade cooldown still exposes the native final progress
in the base radial's `Color.r == 1` and a real local `animate_grenade_flash`
event owns a certified cyan pulse, the existing `local_p_cooldown` lease must
stay held so the native base radial remains hidden. Once native writes
`Color.r == 0`, the cooldown group is released and the base visibility is
restored while `local_p_grenade_flash` keeps both native ghosts leased hidden.
Disabling equipment restores the exact native visibility and leaves the source
color, parent and sentinel untouched.
"""
import unittest

from test_hud_grenade_flash_event import _event_lua, _sentinel_ok


class GrenadeCooldownFlashHandoffTests(unittest.TestCase):
    def test_inactive_cooldown_keeps_lease_until_native_progress_cleanup(self):
        lua = _event_lua()
        g = lua.globals()

        self.assertTrue(bool(g._reload_cooldown_active),
            "precondition: the fixture recharge must start active")
        self.assertAlmostEqual(float(g._initial_cooldown.remaining), 17.0,
            delta=.001,
            msg="precondition: the fixture recharge must still expose 17 s")
        self.assertEqual(float(g._reload_charges), 1.0,
            "precondition: the fixture stock must be 1 of 2")
        self.assertEqual(float(g._reload_maximum), 2.0)

        lua.execute(r'''
            local base = _G._radial
            local rg = _G._flash_event_radial_ghost
            local ig = _G._flash_event_icon_ghost
            local row = _E._rows[4]
            local function held()
                local state = _R._h5_groups and _R._h5_groups.local_p_cooldown
                return state ~= nil and state.property == "visible"
                    and _R:_h5_group_holds_visible("local_p_cooldown", base) == true
            end
            _G._t1_owned = row and row._grenade_flash
            _G._t1_base = base
            _G._t1_base_parent = base:parent()
            _G._t1_pre_visible = base:visible()
            _G._t1_pre_held = held()
            _G._t1_pre_r = base:color().r

            base:set_color(Color(.5, 1, 1, 1))
            managers.player:_native_clear_replenish_timer()
            _game_clock:set_time(1000)
            _G._t1_emit_return = _emit_flash(HUDManager.PLAYER_PANEL)
            _G._t1_emit_ok = _G._t1_emit_return
                == _G._native_flash_expected_return

            row = _E._rows[4]
            local flash = row and row._grenade_flash
            local color = flash and flash:color()
            _G._t1_flash_same = flash == _G._t1_owned
            _G._t1_flash_visible = flash ~= nil and flash:visible() == true
            _G._t1_flash_alpha = flash and flash:alpha() or -1
            _G._t1_flash_cyan = color ~= nil and color.r < .5
                and color.g > .5 and color.b > .5
            _G._t1_flash_cert = _E._grenade_flash_ok == true
                and row._flash_active == true
                and row:_verify_grenade_flash() == true
                and _E:_verify_grenade_flash() == true
                and _E:verify() == true
            _G._t1_ghosts_false = rg:visible() == false and ig:visible() == false
            _G._t1_base_hidden = base:visible() == false
            _G._t1_cooldown_held = held()
            _G._t1_base_r = base:color().r
            _G._t1_base_alpha = base:color().a
            local snap = _E:get_snapshot()
            _G._t1_cooldown_known = snap.cooldown.known == true
            _G._t1_cooldown_inactive = snap.cooldown.active ~= true
            _G._t1_charges = snap.projectile.charges.raw
            _G._t1_maximum = snap.projectile.maximum.raw
            _G._t1_recharge_hidden = _E._visible_rows[5] ~= true
                and _E._rows[5]._root:visible() == false
            _G._t1_active_hidden = _E._visible_rows[6] ~= true
                and _E._rows[6]._root:visible() == false
            _G._t1_value = row._value:text()
        ''')

        self.assertTrue(bool(g._t1_pre_held),
            "precondition: the active cooldown must hold the real base lease")
        self.assertFalse(bool(g._t1_pre_visible),
            "precondition: the native base radial must start leased hidden")
        self.assertAlmostEqual(float(g._t1_pre_r), 0.0, delta=.001)
        self.assertTrue(bool(g._t1_emit_ok),
            "the real native event return must survive the POSTHOOK dispatch")
        self.assertTrue(bool(g._t1_flash_same),
            "the certified recovery pulse must reuse the same owned bitmap")
        self.assertTrue(bool(g._t1_flash_visible),
            "the real local flash must be visible")
        self.assertAlmostEqual(float(g._t1_flash_alpha), 1.0, delta=.01,
            msg="the recovery pulse must start fully opaque")
        self.assertTrue(bool(g._t1_flash_cyan),
            "the recovery pulse must be the positive owned cyan color")
        self.assertTrue(bool(g._t1_flash_cert),
            "the owned flash must certify through the real verifiers")
        self.assertTrue(bool(g._t1_ghosts_false),
            "both native ghosts must stay leased hidden")
        self.assertTrue(bool(g._t1_base_hidden),
            "RED: the final progress frame must keep the native base radial "
            "hidden")
        self.assertTrue(bool(g._t1_cooldown_held),
            "RED: the existing local_p_cooldown lease must stay held while the "
            "native radial still exposes final progress")
        self.assertAlmostEqual(float(g._t1_base_r), 1.0, delta=.001,
            msg="the native final progress in Color.r must stay unchanged")
        self.assertAlmostEqual(float(g._t1_base_alpha), .5, delta=.001)
        self.assertTrue(bool(g._t1_cooldown_known),
            "the cleared replenish timer must remain a known cooldown")
        self.assertTrue(bool(g._t1_cooldown_inactive),
            "the cleared replenish timer must be known inactive")
        self.assertEqual(float(g._t1_charges), 1.0)
        self.assertEqual(float(g._t1_maximum), 2.0)
        self.assertTrue(bool(g._t1_recharge_hidden),
            "an inactive cooldown must not show the RECHARGE row")
        self.assertTrue(bool(g._t1_active_hidden),
            "an inactive cooldown must not show the ACTIVE row")
        self.assertEqual(g._t1_value, "1",
            "the row must keep the real stock, not a bogus seconds value")

        lua.execute(r'''
            local base = _G._t1_base
            local rg = _G._flash_event_radial_ghost
            local ig = _G._flash_event_icon_ghost
            base:set_color(Color(.5, 0, 1, 1))
            _R:update(_m, 1.20, .08)
            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            _G._t1_restored = base:visible() == true
            _G._t1_cooldown_absent = _R._h5_groups == nil
                or _R._h5_groups.local_p_cooldown == nil
            _G._t1_base_r0 = base:color().r == 0
            _G._t1_ghosts_false_after = rg:visible() == false
                and ig:visible() == false
            _G._t1_ghost_held_after = _R._h5_groups ~= nil
                and _R._h5_groups.local_p_grenade_flash ~= nil
                and _R:_h5_group_holds_visible("local_p_grenade_flash", rg) == true
                and _R:_h5_group_holds_visible("local_p_grenade_flash", ig) == true
            _G._t1_flash_same_after = flash == _G._t1_owned
            _G._t1_flash_visible_after = flash ~= nil
                and flash:visible() == true
            _G._t1_flash_cert_after = _E._grenade_flash_ok == true
                and row._flash_active == true
                and row:_verify_grenade_flash() == true
                and _E:_verify_grenade_flash() == true
                and _E:verify() == true
            _G._t1_parent_after = base:parent() == _G._t1_base_parent
                and _G._t1_base_parent == _gren
            _G._t1_sentinel_after = _G._flash_event_sentinel:visible() == true
                and _G._flash_event_sentinel:parent() == _gren
        ''')

        self.assertTrue(bool(g._t1_restored),
            "RED: native Color.r == 0 cleanup must restore the base visibility")
        self.assertTrue(bool(g._t1_cooldown_absent),
            "RED: native Color.r == 0 cleanup must release local_p_cooldown")
        self.assertTrue(bool(g._t1_base_r0),
            "native cleanup must stay color-only and preserve Color.r == 0")
        self.assertTrue(bool(g._t1_ghosts_false_after),
            "the flash group must keep both native ghosts leased hidden")
        self.assertTrue(bool(g._t1_ghost_held_after),
            "the local_p_grenade_flash group must stay held after cleanup")
        self.assertTrue(bool(g._t1_flash_same_after),
            "the recovery pulse must keep the same owned bitmap")
        self.assertTrue(bool(g._t1_flash_visible_after))
        self.assertTrue(bool(g._t1_flash_cert_after),
            "the owned pulse must stay certified after native cleanup")
        self.assertTrue(bool(g._t1_parent_after),
            "the native base parent must remain unchanged")
        self.assertTrue(bool(g._t1_sentinel_after))
        self.assertTrue(_sentinel_ok(g))

    def test_inactive_cooldown_lease_survives_throttle_then_off_restores(self):
        lua = _event_lua()
        g = lua.globals()

        self.assertTrue(bool(g._reload_cooldown_active),
            "precondition: the fixture recharge must start active")
        self.assertAlmostEqual(float(g._initial_cooldown.remaining), 17.0,
            delta=.001)
        self.assertEqual(float(g._reload_charges), 1.0)
        self.assertEqual(float(g._reload_maximum), 2.0)

        lua.execute(r'''
            local base = _G._radial
            local rg = _G._flash_event_radial_ghost
            local ig = _G._flash_event_icon_ghost
            local row = _E._rows[4]
            local function held()
                local state = _R._h5_groups and _R._h5_groups.local_p_cooldown
                return state ~= nil and state.property == "visible"
                    and _R:_h5_group_holds_visible("local_p_cooldown", base) == true
            end
            local function certified(owned)
                local current = _E._rows[4]
                local flash = current and current._grenade_flash
                return flash ~= nil and flash == owned
                    and flash:visible() == true
                    and _E._grenade_flash_ok == true
                    and current._flash_active == true
                    and current:_verify_grenade_flash() == true
                    and _E:_verify_grenade_flash() == true
                    and _E:verify() == true
            end
            _G._t2_owned = row and row._grenade_flash
            _G._t2_base_parent = base:parent()

            base:set_color(Color(.5, 1, 1, 1))
            managers.player:_native_clear_replenish_timer()
            _game_clock:set_time(1000)
            _G._t2_emit_return = _emit_flash(HUDManager.PLAYER_PANEL)
            _G._t2_emit_ok = _G._t2_emit_return
                == _G._native_flash_expected_return

            _R:update(_m, 1.20, .08)
            _G._t2_main_base_hidden = base:visible() == false
            _G._t2_main_held = held()
            _G._t2_main_owned_cert = certified(_G._t2_owned)
            _G._t2_main_ghosts_false = rg:visible() == false
                and ig:visible() == false
            _G._t2_main_r = base:color().r

            _R:update(_m, 1.21, .01)
            _G._t2_throttle_base_hidden = base:visible() == false
            _G._t2_throttle_held = held()
            _G._t2_throttle_owned_cert = certified(_G._t2_owned)
            _G._t2_throttle_ghosts_false = rg:visible() == false
                and ig:visible() == false
            _G._t2_throttle_r = base:color().r

            kyohud.settings.enable_equipment = false
            _R:refresh_settings(_m)
            _G._t2_off_base_visible = base:visible() == true
            _G._t2_off_ghosts_true = rg:visible() == true
                and ig:visible() == true
            _G._t2_off_groups_absent = _R._h5_groups == nil
                or (_R._h5_groups.local_p_grenade_flash == nil
                    and _R._h5_groups.local_p_cooldown == nil)
            local off = base:color()
            _G._t2_off_color = off.r == 1 and off.g == 1 and off.b == 1
                and off.a == .5
            _G._t2_off_parent = base:parent() == _G._t2_base_parent
                and _G._t2_base_parent == _gren
            _G._t2_off_sentinel = _G._flash_event_sentinel:visible() == true
                and _G._flash_event_sentinel:parent() == _gren
        ''')

        self.assertTrue(bool(g._t2_emit_ok),
            "the real native event return must survive the POSTHOOK dispatch")
        self.assertTrue(bool(g._t2_main_base_hidden),
            "RED: the final progress frame must keep the base radial hidden on "
            "an ordinary update")
        self.assertTrue(bool(g._t2_main_held),
            "RED: local_p_cooldown must stay held while final progress persists")
        self.assertTrue(bool(g._t2_main_owned_cert),
            "the recovery pulse must stay certified on the ordinary update")
        self.assertTrue(bool(g._t2_main_ghosts_false),
            "both native ghosts must stay leased hidden")
        self.assertAlmostEqual(float(g._t2_main_r), 1.0, delta=.001,
            msg="the native final progress in Color.r must stay unchanged")
        self.assertTrue(bool(g._t2_throttle_base_hidden),
            "RED: a throttled update must keep the base radial hidden while "
            "final progress persists")
        self.assertTrue(bool(g._t2_throttle_held),
            "RED: a throttled update must keep local_p_cooldown held")
        self.assertTrue(bool(g._t2_throttle_owned_cert),
            "the recovery pulse must stay certified on the throttled update")
        self.assertTrue(bool(g._t2_throttle_ghosts_false),
            "the throttled update must keep both native ghosts leased hidden")
        self.assertAlmostEqual(float(g._t2_throttle_r), 1.0, delta=.001,
            msg="the throttled update must not rewrite the native Color.r")
        self.assertTrue(bool(g._t2_off_base_visible),
            "disabling equipment must restore the exact native base visibility")
        self.assertTrue(bool(g._t2_off_ghosts_true),
            "disabling equipment must restore both native ghosts")
        self.assertTrue(bool(g._t2_off_groups_absent),
            "disabling equipment must release both local H5 groups")
        self.assertTrue(bool(g._t2_off_color),
            "disabling equipment must leave the native source color untouched")
        self.assertTrue(bool(g._t2_off_parent),
            "disabling equipment must leave the native base parent untouched")
        self.assertTrue(bool(g._t2_off_sentinel),
            "disabling equipment must leave the native sentinel untouched")
        self.assertTrue(_sentinel_ok(g))


if __name__ == "__main__":
    unittest.main()
