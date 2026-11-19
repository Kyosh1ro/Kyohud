"""Integrated grenade recharge text priority: known charges keep the counter,
zero charges show the cooldown seconds; the orange reveal keeps advancing and
the native radial stays leased."""
import unittest

from test_hud_native_cooldown_replacement import _runtime


class EquipmentChargePriorityTests(unittest.TestCase):
    def test_known_charges_keep_counter_zero_charges_show_cooldown(self):
        lua = _runtime()
        lua.execute(r'''
            local row, root, value, reveal
            local function same_primitives()
                local now = _E._rows[4]
                return now == row and now._root == root and now._value == value
                    and now._recharge_reveal == reveal
            end
            local function ratio()
                if not reveal or not root or root:h() <= 0 then return nil end
                return reveal:h() / root:h()
            end
            local function held()
                return _radial:visible() == false and _radial == _leaf
                    and _radial:alpha() == .5
            end
            local function close(a, b)
                return a ~= nil and math.abs(a - b) <= .02
            end

            dispatch(HUDManager, 'set_teammate_grenade_cooldown', _m,
                HUDManager.PLAYER_PANEL, {duration = 20, end_time = 1017})
            _R:update(_m, 1.06, .06)

            row = _E._rows[4]
            root, value, reveal = row._root, row._value, row._recharge_reveal
            local snap = _E:get_snapshot()
            _initial_ok = root ~= nil and value ~= nil and reveal ~= nil
                and reveal:visible() and same_primitives()
            _initial_text = value and value:text() or nil
            _initial_progress = ratio()
            _initial_held = held()
            _initial_verify = _E:verify()
            _initial_charges_known = snap.projectile.charges.known == true
            _initial_charges = snap.projectile.charges.raw
            _initial_remaining = snap.cooldown.remaining

            _game_clock:set_time(1001)
            _R:update(_m, 1.07, .01)

            snap = _E:get_snapshot()
            _throttle_text = value:text()
            _throttle_progress = ratio()
            _throttle_held = held()
            _throttle_verify = _E:verify()
            _throttle_same = same_primitives()
            _throttle_charges_known = snap.projectile.charges.known == true
            _throttle_charges = snap.projectile.charges.raw
            _throttle_remaining = snap.cooldown.remaining

            managers.player:_native_set_grenades('pocket', 0, 2)
            dispatch(HUDManager, 'set_teammate_grenades_amount', _m,
                HUDManager.PLAYER_PANEL, {amount = 0})
            _R:update(_m, 1.13, .06)

            snap = _E:get_snapshot()
            _zero_text = value:text()
            _zero_progress = ratio()
            _zero_held = held()
            _zero_verify = _E:verify()
            _zero_same = same_primitives()
            _zero_charges_known = snap.projectile.charges.known == true
            _zero_charges = snap.projectile.charges.raw
            _zero_remaining = snap.cooldown.remaining

            _game_clock:set_time(1002)
            _R:update(_m, 1.14, .01)

            snap = _E:get_snapshot()
            _zero_throttle_text = value:text()
            _zero_throttle_progress = ratio()
            _zero_throttle_held = held()
            _zero_throttle_verify = _E:verify()
            _zero_throttle_same = same_primitives()
            _zero_throttle_remaining = snap.cooldown.remaining

            _unknown_charges_rejected = _E:integrated_recharge_text(
                {remaining = 15, duration = 20}, {known = false, raw = 0}) == nil

            managers.player:_native_set_grenades('pocket', 1, 2)
            dispatch(HUDManager, 'set_teammate_grenades_amount', _m,
                HUDManager.PLAYER_PANEL, {amount = 1})
            _R:update(_m, 1.2, .06)

            snap = _E:get_snapshot()
            _recovered_text = value:text()
            _recovered_progress = ratio()
            _recovered_held = held()
            _recovered_verify = _E:verify()
            _recovered_same = same_primitives()
            _recovered_charges_known = snap.projectile.charges.known == true
            _recovered_charges = snap.projectile.charges.raw
            _recovered_remaining = snap.cooldown.remaining
            _recovered_active = snap.cooldown.active == true
            _recovered_integrated = snap.cooldown.integrated == true
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._initial_ok),
            "integrated recharge must be visible on the same owned primitives")
        self.assertEqual(g._initial_text, "1", "known charge must keep the counter")
        self.assertLess(abs(float(g._initial_progress) - .15), .02)
        self.assertTrue(bool(g._initial_held), "native radial must stay leased")
        self.assertTrue(bool(g._initial_verify), "equipment must verify")
        self.assertTrue(bool(g._initial_charges_known))
        self.assertEqual(float(g._initial_charges), 1.0)
        self.assertEqual(float(g._initial_remaining), 17.0)

        self.assertEqual(g._throttle_text, "1", "throttled frame must keep the counter")
        self.assertLess(abs(float(g._throttle_progress) - .20), .02)
        self.assertTrue(bool(g._throttle_held), "throttled frame must keep the native lease")
        self.assertTrue(bool(g._throttle_verify))
        self.assertTrue(bool(g._throttle_same), "throttled frame must retain primitives")
        self.assertTrue(bool(g._throttle_charges_known))
        self.assertEqual(float(g._throttle_charges), 1.0)
        self.assertEqual(float(g._throttle_remaining), 16.0)

        self.assertEqual(g._zero_text, "16s", "zero charges must show the cooldown")
        self.assertLess(abs(float(g._zero_progress) - .20), .02)
        self.assertTrue(bool(g._zero_held))
        self.assertTrue(bool(g._zero_verify))
        self.assertTrue(bool(g._zero_same))
        self.assertTrue(bool(g._zero_charges_known))
        self.assertEqual(float(g._zero_charges), 0.0)
        self.assertEqual(float(g._zero_remaining), 16.0)

        self.assertEqual(g._zero_throttle_text, "15s",
            "throttled zero-charge frame must advance the cooldown text")
        self.assertLess(abs(float(g._zero_throttle_progress) - .25), .02)
        self.assertTrue(bool(g._zero_throttle_held), "throttled zero frame must keep the native lease")
        self.assertTrue(bool(g._zero_throttle_verify))
        self.assertTrue(bool(g._zero_throttle_same), "throttled zero frame must retain primitives")
        self.assertEqual(float(g._zero_throttle_remaining), 15.0)
        self.assertTrue(bool(g._unknown_charges_rejected),
            "unknown charges must not synthesize cooldown text")

        self.assertEqual(g._recovered_text, "1", "recovered charge must restore the counter")
        self.assertLess(abs(float(g._recovered_progress) - .25), .02)
        self.assertTrue(bool(g._recovered_held))
        self.assertTrue(bool(g._recovered_verify))
        self.assertTrue(bool(g._recovered_same), "recovery must retain the same primitives")
        self.assertTrue(bool(g._recovered_charges_known))
        self.assertEqual(float(g._recovered_charges), 1.0)
        self.assertEqual(float(g._recovered_remaining), 15.0)
        self.assertTrue(bool(g._recovered_active), "cooldown must stay active")
        self.assertTrue(bool(g._recovered_integrated), "cooldown must stay integrated")


if __name__ == "__main__":
    unittest.main()
