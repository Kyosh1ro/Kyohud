"""Transition contracts for the H5 grenade flash replacement.

RED today: the real registered `HUDManager:animate_grenade_flash` POSTHOOK must
synchronously reveal the owned full-icon cyan pulse (with the H5
`local_p_grenade_flash` lease) during the native call, and an already certified
pulse must survive past the 0.6 s event clock until the native ghosts actually
reach their terminal (baseline geometry, alpha 0, visible false) state.
"""
import unittest

from test_hud_grenade_flash_event import _event_lua, _sentinel_ok


class GrenadeFlashTransitionTests(unittest.TestCase):
    def test_registered_posthook_reveals_certified_pulse_without_update(self):
        lua = _event_lua()
        g = lua.globals()

        self.assertEqual(int(g._flash_event_hook_count), 1,
            "precondition: exactly one real animate_grenade_flash PostHook")

        lua.execute(r'''
            _game_clock:set_time(1000)

            _G._t_hooks_before = 0
            _G._t_hook_before = nil
            for _, hook in ipairs(Hooks._all) do
                if hook.class == HUDManager and hook.method == "animate_grenade_flash"
                    and hook.kind == "post" then
                    _G._t_hooks_before = _G._t_hooks_before + 1
                    if _G._t_hook_before == nil then
                        _G._t_hook_before = hook
                    end
                end
            end

            _G._t_native_calls_before = _G._native_flash_calls
            _G._t_emit_return = _emit_flash(HUDManager.PLAYER_PANEL)

            _G._t_hooks_after = 0
            _G._t_hook_after = nil
            for _, hook in ipairs(Hooks._all) do
                if hook.class == HUDManager and hook.method == "animate_grenade_flash"
                    and hook.kind == "post" then
                    _G._t_hooks_after = _G._t_hooks_after + 1
                    if _G._t_hook_after == nil then
                        _G._t_hook_after = hook
                    end
                end
            end
            _G._t_hook_same = _G._t_hook_before ~= nil
                and _G._t_hook_before == _G._t_hook_after
                and _G._t_hook_before.fn == _G._t_hook_after.fn

            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            local icon = row and row._icon
            local function close(a, b) return math.abs(a - b) <= .05 end
            _G._t_flash_visible = flash ~= nil and flash:visible() == true
            _G._t_full_shape = flash ~= nil and icon ~= nil
                and close(flash:x(), icon:x()) and close(flash:y(), icon:y())
                and close(flash:w(), icon:w()) and close(flash:h(), icon:h())
            local c = flash and flash:color()
            _G._t_cyan = c ~= nil and c.r < .5 and c.g > .5 and c.b > .5
            _G._t_alpha = flash and flash:alpha() or -1
            _G._t_active = row ~= nil and row._flash_active == true
                and _E._grenade_flash_ok == true
            _G._t_row_verify = row ~= nil
                and row:_verify_grenade_flash() == true
            _G._t_equipment_verify = _E:verify() == true

            local rg = _G._flash_event_radial_ghost
            local ig = _G._flash_event_icon_ghost
            _G._t_ghosts_false = rg:visible() == false
                and ig:visible() == false
            _G._t_group_present = _R._h5_groups ~= nil
                and _R._h5_groups.local_p_grenade_flash ~= nil
            _G._t_group_held = _R:_h5_group_holds_visible(
                "local_p_grenade_flash", rg) == true
                and _R:_h5_group_holds_visible(
                    "local_p_grenade_flash", ig) == true

            _G._t_native_calls = _G._native_flash_calls
            _G._t_native_return_ok =
                _G._t_emit_return == _G._native_flash_expected_return
                and _G._native_flash_return == _G._native_flash_expected_return

            local snap = _E:get_snapshot()
            _G._t_charges = snap.projectile.charges.raw
            _G._t_maximum = snap.projectile.maximum.raw
            _G._t_recharge = snap.cooldown.known == true
                and snap.cooldown.active == true
        ''')

        self.assertEqual(int(g._t_hooks_before), 1,
            "the real equipment PostHook must be the only registered one")
        self.assertEqual(int(g._t_hooks_after), 1,
            "dispatching the event must not add another PostHook")
        self.assertTrue(bool(g._t_hook_same),
            "RED: the same real registered PostHook must still be installed")
        self.assertEqual(int(g._t_native_calls_before), 0)
        self.assertTrue(bool(g._t_flash_visible),
            "RED: the event PostHook must reveal the owned pulse synchronously, "
            "without a later runtime update")
        self.assertTrue(bool(g._t_full_shape),
            "RED: the synchronous pulse must use the full original row icon")
        self.assertTrue(bool(g._t_cyan),
            "RED: the synchronous pulse must be cyan")
        self.assertGreater(float(g._t_alpha), 0.0,
            "RED: the synchronous pulse alpha must be positive")
        self.assertTrue(bool(g._t_active),
            "RED: the synchronous pulse must be the certified active bitmap")
        self.assertTrue(bool(g._t_row_verify),
            "RED: row:_verify_grenade_flash() must certify the synchronous pulse")
        self.assertTrue(bool(g._t_equipment_verify),
            "RED: equipment:verify() must certify the synchronous pulse")
        self.assertTrue(bool(g._t_ghosts_false),
            "RED: the synchronous event must leave both native ghosts hidden")
        self.assertTrue(bool(g._t_group_present),
            "RED: the synchronous event must acquire local_p_grenade_flash")
        self.assertTrue(bool(g._t_group_held),
            "RED: both native ghosts must be held by local_p_grenade_flash")
        self.assertEqual(int(g._t_native_calls), 1,
            "the original animate_grenade_flash must still run exactly once")
        self.assertTrue(bool(g._t_native_return_ok),
            "the original animate_grenade_flash return must be preserved")
        self.assertEqual(float(g._t_charges), 1.0,
            "the event must not clamp the grenade stock")
        self.assertEqual(float(g._t_maximum), 2.0)
        self.assertTrue(bool(g._t_recharge),
            "RECHARGE must stay active through the synchronous event")
        self.assertTrue(_sentinel_ok(g),
            "the native sibling sentinel must stay untouched")

    def test_certified_pulse_outlives_event_clock_until_native_terminal(self):
        lua = _event_lua()
        g = lua.globals()

        lua.execute(r'''
            function _t_sentinel_ok()
                local s = _G._flash_event_sentinel
                local shape = _G._flash_event_sentinel_shape
                return s ~= nil and s:visible() == true
                    and _G._flash_event_sentinel_owned()
                    and s:x() == shape[1] and s:y() == shape[2]
                    and s:w() == shape[3] and s:h() == shape[4]
            end

            _game_clock:set_time(1000)
            _G._u_emit_return = _emit_flash(HUDManager.PLAYER_PANEL)
            _R:update(_m, 1.20, .08)

            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            local icon = row and row._icon
            local function close(a, b) return math.abs(a - b) <= .05 end
            _G._u_owned = flash
            _G._u_a_visible = flash ~= nil and flash:visible() == true
            _G._u_a_full_shape = flash ~= nil and icon ~= nil
                and close(flash:x(), icon:x()) and close(flash:y(), icon:y())
                and close(flash:w(), icon:w()) and close(flash:h(), icon:h())
            local c = flash and flash:color()
            _G._u_a_cyan = c ~= nil and c.r < .5 and c.g > .5 and c.b > .5
            _G._u_a_alpha = flash and flash:alpha() or -1
            _G._u_a_cert = flash ~= nil and _E._grenade_flash_ok == true
                and row._flash_active == true
                and row:_verify_grenade_flash() == true
                and _E:verify() == true
            local rg = _G._flash_event_radial_ghost
            local ig = _G._flash_event_icon_ghost
            _G._u_a_ghosts_false = rg:visible() == false
                and ig:visible() == false
            _G._u_a_group = _R._h5_groups ~= nil
                and _R._h5_groups.local_p_grenade_flash ~= nil
            _G._u_a_held = _R:_h5_group_holds_visible(
                "local_p_grenade_flash", rg) == true
                and _R:_h5_group_holds_visible(
                    "local_p_grenade_flash", ig) == true
            _G._u_a_sentinel = _t_sentinel_ok()
            local snap = _E:get_snapshot()
            _G._u_a_charges = snap.projectile.charges.raw
            _G._u_a_maximum = snap.projectile.maximum.raw
            _G._u_a_recharge = snap.cooldown.known == true
                and snap.cooldown.active == true

            local function scale(ghost, base, factor)
                local w, h = base:w() * factor, base:h() * factor
                ghost:set_shape(base:x() + base:w() * .5 - w * .5,
                    base:y() + base:h() * .5 - h * .5, w, h)
            end
            scale(rg, _radial, 1.9)
            scale(ig, _icon, 1.9)
            rg:set_color(Color(.1, 1, 1, 1))
            ig:set_color(Color(.1, 1, 1, 1))
            _G._u_input_ghosts_false = rg:visible() == false
                and ig:visible() == false

            _game_clock:set_time(1000.61)
            _R:update(_m, 1.21, .01)

            row = _E._rows[4]
            flash = row and row._grenade_flash
            _G._u_b_same = flash == _G._u_owned
            _G._u_b_visible = flash ~= nil and flash:visible() == true
            c = flash and flash:color()
            _G._u_b_cyan = c ~= nil and c.r < .5 and c.g > .5 and c.b > .5
            _G._u_b_alpha = flash and flash:alpha() or -1
            _G._u_b_cert = flash ~= nil and _E._grenade_flash_ok == true
                and row._flash_active == true
                and row:_verify_grenade_flash() == true
                and _E:verify() == true
            _G._u_b_ghosts_false = rg:visible() == false
                and ig:visible() == false
            _G._u_b_group = _R._h5_groups ~= nil
                and _R._h5_groups.local_p_grenade_flash ~= nil
            _G._u_b_held = _R:_h5_group_holds_visible(
                "local_p_grenade_flash", rg) == true
                and _R:_h5_group_holds_visible(
                    "local_p_grenade_flash", ig) == true
            _G._u_b_sentinel = _t_sentinel_ok()
            snap = _E:get_snapshot()
            _G._u_b_charges = snap.projectile.charges.raw
            _G._u_b_maximum = snap.projectile.maximum.raw
            _G._u_b_recharge = snap.cooldown.known == true
                and snap.cooldown.active == true

            local function finish(ghost, base)
                ghost:set_shape(base:x(), base:y(), base:w(), base:h())
                ghost:set_color(Color(0, 1, 1, 1))
                ghost:set_visible(false)
            end
            finish(rg, _radial)
            finish(ig, _icon)
            _R:update(_m, 1.22, .01)

            row = _E._rows[4]
            flash = row and row._grenade_flash
            _G._u_c_hidden = flash == nil or flash:visible() == false
            _G._u_c_group_absent = _R._h5_groups == nil
                or _R._h5_groups.local_p_grenade_flash == nil
            _G._u_c_ghosts_false = rg:visible() == false
                and ig:visible() == false
            _G._u_c_sentinel = _t_sentinel_ok()
            snap = _E:get_snapshot()
            _G._u_c_charges = snap.projectile.charges.raw
            _G._u_c_maximum = snap.projectile.maximum.raw
            _G._u_c_recharge = snap.cooldown.known == true
                and snap.cooldown.active == true
        ''')

        self.assertTrue(bool(g._u_a_visible), "precondition: pulse is visible")
        self.assertTrue(bool(g._u_a_full_shape),
            "precondition: pulse uses the full row icon")
        self.assertTrue(bool(g._u_a_cyan), "precondition: pulse is cyan")
        self.assertGreater(float(g._u_a_alpha), 0.0)
        self.assertTrue(bool(g._u_a_cert),
            "precondition: the event pulse is certified")
        self.assertTrue(bool(g._u_a_ghosts_false))
        self.assertTrue(bool(g._u_a_group),
            "precondition: the pulse holds local_p_grenade_flash")
        self.assertTrue(bool(g._u_a_held))
        self.assertTrue(bool(g._u_a_sentinel))
        self.assertEqual(float(g._u_a_charges), 1.0)
        self.assertEqual(float(g._u_a_maximum), 2.0)
        self.assertTrue(bool(g._u_a_recharge))
        self.assertTrue(bool(g._u_input_ghosts_false),
            "precondition: the mutated native animation stays leased hidden")

        self.assertTrue(bool(g._u_b_same),
            "RED: the throttled frame must keep the same owned bitmap")
        self.assertTrue(bool(g._u_b_visible),
            "RED: a certified pulse must stay visible past the 0.6 s event "
            "clock while the native animation is still positive")
        self.assertTrue(bool(g._u_b_cyan),
            "RED: the surviving pulse must stay cyan")
        self.assertGreater(float(g._u_b_alpha), 0.0,
            "RED: the surviving pulse alpha must stay positive")
        self.assertTrue(bool(g._u_b_cert),
            "RED: the surviving pulse must stay certified")
        self.assertTrue(bool(g._u_b_ghosts_false),
            "RED: both native ghosts must stay hidden while the pulse survives")
        self.assertTrue(bool(g._u_b_group),
            "RED: the pulse must keep local_p_grenade_flash")
        self.assertTrue(bool(g._u_b_held),
            "RED: both native ghosts must stay held by local_p_grenade_flash")
        self.assertTrue(bool(g._u_b_sentinel))
        self.assertEqual(float(g._u_b_charges), 1.0,
            "the surviving pulse must not change the grenade counter")
        self.assertEqual(float(g._u_b_maximum), 2.0)
        self.assertTrue(bool(g._u_b_recharge),
            "RECHARGE must keep running while the pulse survives")

        self.assertTrue(bool(g._u_c_hidden),
            "terminal native completion must hide the owned pulse")
        self.assertTrue(bool(g._u_c_group_absent),
            "terminal native completion must release local_p_grenade_flash")
        self.assertTrue(bool(g._u_c_ghosts_false),
            "release must not resurrect either native ghost")
        self.assertTrue(bool(g._u_c_sentinel))
        self.assertEqual(float(g._u_c_charges), 1.0)
        self.assertEqual(float(g._u_c_maximum), 2.0)
        self.assertTrue(bool(g._u_c_recharge),
            "RECHARGE must keep running after the terminal release")
        self.assertTrue(_sentinel_ok(g),
            "the native sibling sentinel must stay untouched")


if __name__ == "__main__":
    unittest.main()
