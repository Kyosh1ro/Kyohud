"""RED: Kingpin ACTIVE verification must call each engaged row verifier once
per source, without duplicate nested verification. Receipt trust is identity
bound: replacing the public verifier must fall back to the old duplicate row
checks instead of trusting a forged or cached receipt.
"""
import unittest

from test_hud_kingpin_active import KINGPIN_ACTIVATE, kingpin_lua


WRAP_AND_VERIFY = r'''
local E = _E
local original_row4_verify = E._rows[4].verify
local original_row6_verify = E._rows[6].verify
_G._verify_cost_row4 = 0
_G._verify_cost_row6 = 0
E._rows[4].verify = function(self, ...)
    _G._verify_cost_row4 = _G._verify_cost_row4 + 1
    return original_row4_verify(self, ...)
end
E._rows[6].verify = function(self, ...)
    _G._verify_cost_row6 = _G._verify_cost_row6 + 1
    return original_row6_verify(self, ...)
end
local source = E:get_kingpin_activity_source()
_G._verify_cost_row4 = 0
_G._verify_cost_row6 = 0
_G._verify_cost_actual = E:_verify_kingpin_activity(source)
'''

REVERIFY_FRESH_SOURCE = r'''
local E = _E
local source = E:get_kingpin_activity_source()
_G._verify_cost_row4 = 0
_G._verify_cost_row6 = 0
_G._verify_cost_actual = E:_verify_kingpin_activity(source)
'''

FORGED_VERIFIER_CORRUPT_ROW4 = r'''
local E = _E
_G._forged_original_verify = E.verify
_G._forged_original_row4_shape = {
    E._rows[4]._root:x(), E._rows[4]._root:y(),
    E._rows[4]._root:w(), E._rows[4]._root:h(),
}
E.verify = function(self, requested)
    return true, requested
end
local row4_root = E._rows[4]._root
local x, y, w, h = row4_root:x(), row4_root:y(), row4_root:w(), row4_root:h()
row4_root:set_shape(x + 5, y, w, h)
local source = E:get_kingpin_activity_source()
_G._forged_row4_verify = E:_verify_kingpin_activity(source)
'''

RESTORE_VERIFIER_AND_ROW4 = r'''
local E = _E
E.verify = _G._forged_original_verify
local row4_root = E._rows[4]._root
local shape = _G._forged_original_row4_shape
row4_root:set_shape(shape[1], shape[2], shape[3], shape[4])
local source = E:get_kingpin_activity_source()
_G._restored_row4_verify = E:_verify_kingpin_activity(source)
'''

FORGED_VERIFIER_CORRUPT_ROW6 = r'''
local E = _E
_G._forged_row6_original_verify = E.verify
_G._forged_row6_original_text = E._rows[6]._value:text()
E.verify = function(self, requested)
    return true, requested
end
E._rows[6]._value:set_text("CORRUPT")
local source = E:get_kingpin_activity_source()
_G._forged_row6_verify = E:_verify_kingpin_activity(source)
'''

RESTORE_VERIFIER_AND_ROW6 = r'''
local E = _E
E.verify = _G._forged_row6_original_verify
E._rows[6]._value:set_text(_G._forged_row6_original_text)
local source = E:get_kingpin_activity_source()
_G._restored_row6_verify = E:_verify_kingpin_activity(source)
'''


class KingpinVerificationCostTests(unittest.TestCase):
    def test_kingpin_activity_verification_costs_one_row_pass_per_source(self):
        lua = kingpin_lua()
        lua.execute(KINGPIN_ACTIVATE)
        lua.execute(WRAP_AND_VERIFY)
        g = lua.globals()

        self.assertTrue(bool(g._verify_cost_actual),
            "RED: real Kingpin activity source must verify")
        self.assertEqual(int(g._verify_cost_row4), 1)
        self.assertEqual(int(g._verify_cost_row6), 1)

        lua.execute(REVERIFY_FRESH_SOURCE)

        self.assertTrue(bool(g._verify_cost_actual),
            "RED: a fresh Kingpin activity source must verify")
        self.assertEqual(int(g._verify_cost_row4), 1)
        self.assertEqual(int(g._verify_cost_row6), 1)

    def test_replaced_public_verifier_must_not_trust_forged_receipt(self):
        lua = kingpin_lua()
        lua.execute(KINGPIN_ACTIVATE)
        lua.execute(FORGED_VERIFIER_CORRUPT_ROW4)
        g = lua.globals()

        self.assertFalse(bool(g._forged_row4_verify),
            "RED: forged true+requested receipt must fall back to row4 duplicate check")

        lua.execute(RESTORE_VERIFIER_AND_ROW4)
        self.assertTrue(bool(g._restored_row4_verify),
            "RED: actual verifier and restored row4 geometry must verify again")

        lua.execute(FORGED_VERIFIER_CORRUPT_ROW6)
        self.assertFalse(bool(g._forged_row6_verify),
            "RED: forged receipt must fall back to row6 duplicate text check")

        lua.execute(RESTORE_VERIFIER_AND_ROW6)
        self.assertTrue(bool(g._restored_row6_verify),
            "RED: actual verifier and restored row6 text must verify again")


if __name__ == "__main__":
    unittest.main()
