"""Lot 6 regression: while a valid local Kingpin source owns the ACTIVE row,
the non-selected Hacker throttle path must not run the full equipment verifier.

Both counters observe the real production method identities through a call hook;
no production method is replaced. The expected state is 0 full verifications on
the direct dispatch and 6 full verifications during the throttle-only update that
follows a normal setup update (previous 8, throttle fix 7, chain deferral 6).
"""
import unittest

from test_hud_kingpin_active import KINGPIN_ACTIVATE, kingpin_lua
from test_hud_kingpin_lifecycle import HELPERS, _scan

OBSERVER_INSTALL = r'''
local e_ref = _E.verify
local row6_ref = _E._rows[6] and _E._rows[6].verify
_G._ky_e_verify_calls = 0
_G._ky_row6_verify_calls = 0
function _ky_observer_hook()
    local e_hit, row_hit = false, false
    for level = 1, 2 do
        local info = debug.getinfo(level, "f")
        local f = info and info.func
        if f ~= nil and f ~= _ky_observer_hook then
            if f == e_ref then e_hit = true end
            if f == row6_ref then row_hit = true end
        end
    end
    if e_hit then _G._ky_e_verify_calls = _G._ky_e_verify_calls + 1 end
    if row_hit then _G._ky_row6_verify_calls = _G._ky_row6_verify_calls + 1 end
end
-- JIT traces omit call hooks; an interpreter-only census is required for
-- deterministic counts. This is not a performance benchmark.
_G._ky_e_observer_jit_was_on = jit.status()
jit.off()
jit.flush()
debug.sethook(_ky_observer_hook, "c")
'''

OBSERVER_REMOVE = r'''
debug.sethook()
if _G._ky_e_observer_jit_was_on then
    jit.on()
end
_G._ky_e_observer_jit_was_on = nil
_ky_observer_hook = nil
'''


def _runtime():
    lua = kingpin_lua()
    lua.execute(HELPERS)
    lua.execute(KINGPIN_ACTIVATE)
    return lua


class KingpinThrottleDispatchTests(unittest.TestCase):
    def test_non_selected_hacker_throttle_skips_full_verify(self):
        lua = _runtime()
        g = lua.globals()

        lua.execute(r'''
_G._t1_root = _E._root
_G._t1_row6 = _E._rows[6]
_G._t1_value = _E._rows[6]._value
_G._t1_text = _E._rows[6]._value:text()
_G._t1_progress = _E._rows[6]._progress
_G._t1_parent_visible = _ability_parent:visible()
_G._t1_parent_alpha = _ability_parent:alpha()
_G._t1_meter_visible = _ability_meter:visible()
_G._t1_meter_alpha = _ability_meter:alpha()
_G._t1_icon_visible = _ability_icon:visible()
_G._t1_icon_alpha = _ability_icon:alpha()
_G._t1_entry_count = #kyohud.hud.native_visibility._entries
_G._t1_source = _E:get_kingpin_activity_source()
''')
        before = _scan(lua)
        self.assertTrue(bool(before.meter_held),
            "precondition: Kingpin must lease ability_meter")
        self.assertTrue(bool(before.icon_held),
            "precondition: Kingpin must lease ability_icon")
        self.assertTrue(bool(before.root_visible),
            "precondition: owned Kingpin equipment must be visible")
        self.assertTrue(bool(before.e_verify),
            "precondition: owned Kingpin equipment must certify")
        self.assertTrue(bool(before.row6_verify),
            "precondition: ACTIVE row 6 must certify")
        self.assertIsNotNone(g._t1_source,
            "precondition: actual local Kingpin activity source")
        self.assertEqual(g._t1_source.kind, "chico_injector_local")
        self.assertTrue(bool(g._t1_source.active))

        lua.execute(OBSERVER_INSTALL)
        lua.execute("_G._t1_result = _E:_throttle_hacker_activity()")
        lua.execute(OBSERVER_REMOVE)

        lua.execute(r'''
_G._t1_same_root = (_E._root == _t1_root)
_G._t1_same_row6 = (_E._rows[6] == _t1_row6)
_G._t1_same_value = (_E._rows[6]._value == _t1_value)
_G._t1_text_after = _E._rows[6]._value:text()
_G._t1_progress_after = _E._rows[6]._progress
_G._t1_parent_visible_after = _ability_parent:visible()
_G._t1_parent_alpha_after = _ability_parent:alpha()
_G._t1_meter_visible_after = _ability_meter:visible()
_G._t1_meter_alpha_after = _ability_meter:alpha()
_G._t1_icon_visible_after = _ability_icon:visible()
_G._t1_icon_alpha_after = _ability_icon:alpha()
_G._t1_entry_count_after = #kyohud.hud.native_visibility._entries
_G._t1_source_after = _E:get_kingpin_activity_source()
''')
        after = _scan(lua)

        self.assertFalse(bool(g._t1_result),
            "non-selected Hacker throttle must fail closed")
        self.assertEqual(int(g._ky_e_verify_calls), 0,
            "RED: non-selected Hacker path must not call E.verify (current 1)")
        self.assertEqual(int(g._ky_row6_verify_calls), 0,
            "RED: non-selected Hacker path must not call row 6 verify")

        self.assertTrue(bool(g._t1_same_root))
        self.assertTrue(bool(g._t1_same_row6))
        self.assertTrue(bool(g._t1_same_value))
        self.assertEqual(g._t1_text_after, g._t1_text)
        self.assertEqual(float(g._t1_progress_after), float(g._t1_progress))
        self.assertEqual(bool(g._t1_parent_visible_after),
            bool(g._t1_parent_visible))
        self.assertEqual(float(g._t1_parent_alpha_after),
            float(g._t1_parent_alpha))
        self.assertEqual(bool(g._t1_meter_visible_after),
            bool(g._t1_meter_visible))
        self.assertEqual(float(g._t1_meter_alpha_after),
            float(g._t1_meter_alpha))
        self.assertEqual(bool(g._t1_icon_visible_after),
            bool(g._t1_icon_visible))
        self.assertEqual(float(g._t1_icon_alpha_after),
            float(g._t1_icon_alpha))
        self.assertEqual(int(g._t1_entry_count_after),
            int(g._t1_entry_count),
            "non-selected Hacker throttle must not touch native leases")
        self.assertIsNotNone(g._t1_source_after,
            "actual local Kingpin source must stay valid")
        self.assertEqual(after.meter_leases, before.meter_leases)
        self.assertEqual(after.icon_leases, before.icon_leases)
        self.assertFalse(bool(after.parent_lease))
        self.assertTrue(bool(after.meter_held))
        self.assertTrue(bool(after.icon_held))
        self.assertTrue(bool(after.root_visible))

    def test_throttled_runtime_drops_one_full_verify_and_fails_closed(self):
        lua = _runtime()
        g = lua.globals()

        lua.execute(r'''
_R:update(_m, 3.1, .1)
''')
        lua.execute(OBSERVER_INSTALL)
        lua.execute(r'''
_R:update(_m, 3.11, .01)
''')
        lua.execute(OBSERVER_REMOVE)
        lua.execute(r'''
_G._t2_e_calls = _G._ky_e_verify_calls
_G._t2_row6_calls = _G._ky_row6_verify_calls
_G._t2_root = _E._root
_G._t2_meter_hidden = (_ability_meter:visible() == false)
_G._t2_icon_hidden = (_ability_icon:visible() == false)
_G._t2_root_visible = (_E._root ~= nil and _E._root:visible() == true)
_G._t2_e_verify = (_E:verify() == true)
_G._t2_row6_visible = (_E._visible_rows and _E._visible_rows[6] == true)
    or false
_G._t2_row6_label = _E._rows and _E._rows[6] and _E._rows[6]._label:text()
    or nil
_G._t2_row6_value = _E._rows and _E._rows[6] and _E._rows[6]._value:text()
    or nil
_G._t2_row6_progress = _E._rows and _E._rows[6] and _E._rows[6]._progress
''')
        positive = _scan(lua)

        self.assertEqual(int(g._t2_e_calls), 6,
            "throttle-only runtime after normal setup must run 6 full verifies "
            "(previous 8, throttle fix 7, chain deferral 6)")
        self.assertTrue(bool(g._t2_meter_hidden),
            "positive Kingpin must keep ability_meter leased")
        self.assertTrue(bool(g._t2_icon_hidden),
            "positive Kingpin must keep ability_icon leased")
        self.assertTrue(bool(g._t2_root_visible),
            "positive Kingpin owned root must stay visible")
        self.assertTrue(bool(g._t2_e_verify),
            "positive Kingpin render must certify")
        self.assertTrue(bool(g._t2_row6_visible))
        self.assertEqual(g._t2_row6_label, "ACTIVE")
        self.assertEqual(g._t2_row6_value, "6s")
        self.assertAlmostEqual(float(g._t2_row6_progress), 1.0, places=5)
        self.assertTrue(bool(positive.meter_held))
        self.assertTrue(bool(positive.icon_held))
        self.assertFalse(bool(positive.parent_lease))

        lua.execute(r'''
local row3 = _E._rows[3]
_G._t2_row3 = row3
_G._t2_row3_text = row3._value:text()
row3._value:set_text("BROKEN")
_R:update(_m, 3.12, .01)
''')
        broken = _scan(lua)
        self.assertTrue(bool(broken.meter_visible),
            "corrupted owned render must restore ability_meter visible")
        self.assertTrue(bool(broken.icon_visible),
            "corrupted owned render must restore ability_icon visible")
        self.assertFalse(bool(broken.meter_held),
            "corrupted owned render must release the ability_meter lease")
        self.assertFalse(bool(broken.icon_held),
            "corrupted owned render must release the ability_icon lease")
        self.assertFalse(bool(broken.parent_lease),
            "native radial_ability parent must never be leased")

        lua.execute(r'''
_R:update(_m, 3.3, .1)
_G._t2_root_after = _E._root
_G._t2_same_root = (_E._root == _t2_root)
_G._t2_same_row3 = (_E._rows[3] == _t2_row3)
_G._t2_row3_text_after = _E._rows[3]._value:text()
''')
        recovered = _scan(lua)
        self.assertTrue(bool(g._t2_same_root),
            "ordinary runtime must recover the same owned equipment root")
        self.assertTrue(bool(g._t2_same_row3))
        self.assertEqual(g._t2_row3_text_after, g._t2_row3_text,
            "ordinary runtime must repair the same owned row 3 text")
        self.assertTrue(bool(recovered.root_visible),
            "recovered owned root must be visible")
        self.assertTrue(bool(recovered.e_verify),
            "recovered owned equipment must certify")
        self.assertTrue(bool(recovered.meter_held),
            "recovered Kingpin must lease ability_meter again")
        self.assertTrue(bool(recovered.icon_held),
            "recovered Kingpin must lease ability_icon again")
        self.assertFalse(bool(recovered.parent_lease))


if __name__ == "__main__":
    unittest.main()
