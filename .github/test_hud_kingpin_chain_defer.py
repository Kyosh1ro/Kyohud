"""Lot 6 RED: while a real local Kingpin source owns the ACTIVE row and the
owned equipment root is exposed, the aggregate verifier identity may defer the
initial full render check in RT:_hacker_active_chain to the existing FINAL full
check performed after the fresh source read.

The verifier is never replaced: a call hook observes the real _E.verify
identity only during the chain invocation. The expected RED count is 1 call
instead of the current 2. Hacker and hidden recovery keep their original
behaviour.

T2 temporarily delegates the real getter to corrupt the actual owned row 3 text
on the second chain source read (call 3 overall: one sync read then two chain
reads), then calls the real _R:_sync_hacker_active(). The publication must fail
closed, restore the native leaves, release the leases and
not certify the corrupted root; an ordinary update must repair the same owned
root/row 3 and acquire the two leaves again. This characterisation is expected
to be green on the current production and is labelled honestly.

Two compact safety tests reuse the same real-identity observer without replacing
production. Replacing the aggregate verifier disables the deferral gate (two
full checks, no lying certificate); a real Hacker activation keeps the original
two full checks because the deferral is Kingpin-only.
"""
import unittest

from test_hud_hacker_active import ACTIVATE_AND_OBSERVE, hacker_lua
from test_hud_kingpin_active import KINGPIN_ACTIVATE, kingpin_lua
from test_hud_kingpin_lifecycle import HELPERS, _scan


CHAIN_OBSERVER_INSTALL = r'''
local e_ref = _E.verify
local src_ref = _E.get_local_ability_activity_source
_G._ky_chain_e_verify_calls = 0
_G._ky_chain_source_calls = 0
function _ky_chain_observer()
    for level = 1, 2 do
        local info = debug.getinfo(level, "f")
        local f = info and info.func
        if f ~= nil and f ~= _ky_chain_observer then
            if f == e_ref then
                _G._ky_chain_e_verify_calls = _G._ky_chain_e_verify_calls + 1
            end
            if f == src_ref then
                _G._ky_chain_source_calls = _G._ky_chain_source_calls + 1
            end
        end
    end
end
-- JIT traces omit call hooks; an interpreter-only census is required for
-- deterministic counts. This is not a performance benchmark.
_G._ky_chain_observer_jit_was_on = jit.status()
jit.off()
jit.flush()
debug.sethook(_ky_chain_observer, "c")
'''

CHAIN_OBSERVER_REMOVE = r'''
debug.sethook()
if _G._ky_chain_observer_jit_was_on then
    jit.on()
end
_G._ky_chain_observer_jit_was_on = nil
_ky_chain_observer = nil
'''


def _runtime():
    lua = kingpin_lua()
    lua.execute(HELPERS)
    lua.execute(KINGPIN_ACTIVATE)
    return lua


class KingpinChainDeferTests(unittest.TestCase):
    def test_positive_chain_runs_a_single_full_verify(self):
        lua = _runtime()
        g = lua.globals()

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

        lua.execute(r'''
_G._t1_root = _E._root
''')
        lua.execute(CHAIN_OBSERVER_INSTALL)
        lua.execute("_G._t1_chain = _R:_hacker_active_chain()")
        lua.execute(CHAIN_OBSERVER_REMOVE)
        lua.execute(r'''
_G._t1_chain_ok = (_t1_chain ~= nil)
_G._t1_chain_kind = _t1_chain and _t1_chain.source
    and _t1_chain.source.kind or nil
_G._t1_chain_leaves = (_t1_chain and _t1_chain.leaves
    and #_t1_chain.leaves) or -1
_G._t1_chain_meter = (_t1_chain and _t1_chain.meter == _ability_meter)
_G._t1_chain_icon = (_t1_chain and _t1_chain.icon == _ability_icon)
_G._t1_same_root = (_E._root == _t1_root)
''')
        after = _scan(lua)

        self.assertTrue(bool(g._t1_chain_ok),
            "real Kingpin positive chain must return a binding candidate")
        self.assertEqual(g._t1_chain_kind, "chico_injector_local")
        self.assertEqual(int(g._t1_chain_leaves), 2)
        self.assertTrue(bool(g._t1_chain_meter))
        self.assertTrue(bool(g._t1_chain_icon))
        self.assertTrue(bool(g._t1_same_root),
            "chain must not replace the owned equipment root")
        self.assertTrue(bool(after.meter_held))
        self.assertTrue(bool(after.icon_held))
        self.assertFalse(bool(after.meter_visible))
        self.assertFalse(bool(after.icon_visible))
        self.assertFalse(bool(after.parent_lease))
        self.assertTrue(bool(after.root_visible))
        self.assertTrue(bool(after.e_verify))
        self.assertTrue(bool(after.row6_verify))

        self.assertEqual(int(g._ky_chain_e_verify_calls), 1,
            "RED: a Kingpin positive chain must defer the initial full render "
            "check to the FINAL check and run exactly one E.verify (current 2)")
        self.assertEqual(int(g._ky_chain_source_calls), 2,
            "chain must still read the source getter exactly twice")

    def test_corrupted_second_source_read_fails_closed_and_recovers(self):
        lua = _runtime()
        g = lua.globals()

        before = _scan(lua)
        self.assertTrue(bool(before.meter_held),
            "precondition: Kingpin must lease ability_meter")
        self.assertTrue(bool(before.icon_held),
            "precondition: Kingpin must lease ability_icon")

        lua.execute(r'''
_G._t2_root = _E._root
_G._t2_row3 = _E._rows[3]
_G._t2_row3_value = _E._rows[3]._value
_G._t2_row3_good = _E._rows[3]._value:text()
local original = _E.get_local_ability_activity_source
_G._t2_source_calls = 0
-- _sync_hacker_active reads the source once BEFORE _hacker_active_chain,
-- then the chain reads it twice: call 1 = sync's initial read,
-- call 2 = first chain read, call 3 = second chain read (the one to corrupt).
_E.get_local_ability_activity_source = function(self, ...)
    _G._t2_source_calls = _G._t2_source_calls + 1
    if _G._t2_source_calls == 3 then
        _E._rows[3]._value:set_text("BROKEN")
    end
    return original(self, ...)
end
_G._t2_result = _R:_sync_hacker_active()
_E.get_local_ability_activity_source = original
_G._t2_row3_text_broken = _E._rows[3]._value:text()
_G._t2_same_root = (_E._root == _t2_root)
_G._t2_same_row3 = (_E._rows[3] == _t2_row3)
''')
        broken = _scan(lua)

        self.assertFalse(bool(g._t2_result),
            "corrupted second source read must fail the Hacker ACTIVE sync")
        self.assertEqual(int(g._t2_source_calls), 3,
            "one sync read plus two chain reads: the corruption must target "
            "call 3, the second CHAIN read")
        self.assertEqual(g._t2_row3_text_broken, "BROKEN",
            "characterisation: the mutation must hit the real owned row 3")
        self.assertTrue(bool(broken.meter_visible),
            "failed sync must restore ability_meter visible")
        self.assertTrue(bool(broken.icon_visible),
            "failed sync must restore ability_icon visible")
        self.assertFalse(bool(broken.meter_held),
            "failed sync must hold no ability_meter lease")
        self.assertFalse(bool(broken.icon_held),
            "failed sync must hold no ability_icon lease")
        self.assertEqual(int(broken.meter_leases), 0)
        self.assertEqual(int(broken.icon_leases), 0)
        self.assertFalse(bool(broken.parent_lease))
        self.assertFalse(bool(broken.e_verify),
            "corrupted owned root must not newly certify")
        self.assertTrue(bool(g._t2_same_root))
        self.assertTrue(bool(g._t2_same_row3))

        lua.execute(r'''
_R:update(_m, 3.1, .1)
_G._t2_after_same_root = (_E._root == _t2_root)
_G._t2_after_same_row3 = (_E._rows[3] == _t2_row3)
_G._t2_after_row3_text = _E._rows[3]._value:text()
''')
        recovered = _scan(lua)

        self.assertTrue(bool(g._t2_after_same_root),
            "ordinary update must keep the same owned equipment root")
        self.assertTrue(bool(g._t2_after_same_row3),
            "ordinary update must keep the same owned row 3")
        self.assertEqual(g._t2_after_row3_text, g._t2_row3_good,
            "ordinary update must repair the same owned row 3 text")
        self.assertTrue(bool(recovered.meter_held),
            "recovered Kingpin must lease ability_meter again")
        self.assertTrue(bool(recovered.icon_held),
            "recovered Kingpin must lease ability_icon again")
        self.assertFalse(bool(recovered.meter_visible))
        self.assertFalse(bool(recovered.icon_visible))
        self.assertFalse(bool(recovered.parent_lease))
        self.assertTrue(bool(recovered.root_visible))
        self.assertTrue(bool(recovered.e_verify))
        self.assertTrue(bool(recovered.row6_verify))

    def test_replaced_aggregate_verifier_disables_deferral(self):
        lua = _runtime()
        g = lua.globals()

        before = _scan(lua)
        self.assertTrue(bool(before.e_verify),
            "precondition: Kingpin equipment must certify")
        self.assertTrue(bool(before.row6_verify),
            "precondition: ACTIVE row 6 must certify")

        lua.execute(r'''
_G._s1_root = _E._root
_G._s1_actual_verify = _E.verify
_E.verify = function(self, ...)
    return _s1_actual_verify(self, ...)
end
''')
        lua.execute(CHAIN_OBSERVER_INSTALL)
        lua.execute("_G._s1_chain = _R:_hacker_active_chain()")
        lua.execute(CHAIN_OBSERVER_REMOVE)
        lua.execute(r'''
_E.verify = _s1_actual_verify
_G._s1_chain_ok = (_s1_chain ~= nil)
_G._s1_chain_kind = _s1_chain and _s1_chain.source
    and _s1_chain.source.kind or nil
_G._s1_same_root = (_E._root == _s1_root)
_G._s1_restored_verify = (_E:verify() == true)
''')
        after = _scan(lua)

        self.assertTrue(bool(g._s1_chain_ok),
            "chain must still return a binding candidate")
        self.assertEqual(g._s1_chain_kind, "chico_injector_local")
        self.assertTrue(bool(g._s1_same_root),
            "chain must not replace the owned equipment root")
        self.assertTrue(bool(g._s1_restored_verify),
            "restored actual verifier must certify the owned equipment")
        self.assertEqual(int(g._ky_chain_e_verify_calls), 2,
            "a replaced aggregate verifier must disable the deferral gate and "
            "run both the initial and FINAL full checks (2, not 1)")
        self.assertEqual(int(g._ky_chain_source_calls), 2,
            "chain must still read the source getter exactly twice")
        self.assertTrue(bool(after.e_verify))
        self.assertTrue(bool(after.row6_verify))

    def test_hacker_chain_keeps_two_full_verifies(self):
        lua = hacker_lua()
        g = lua.globals()
        lua.execute(HELPERS)
        lua.execute(ACTIVATE_AND_OBSERVE)

        before = _scan(lua)
        self.assertTrue(bool(before.meter_held),
            "precondition: ACTIVE must lease ability_meter")
        self.assertTrue(bool(before.icon_held),
            "precondition: ACTIVE must lease ability_icon")
        self.assertTrue(bool(before.root_visible),
            "precondition: owned equipment must be visible")
        self.assertTrue(bool(before.row6_verify),
            "precondition: ACTIVE row 6 must certify")

        lua.execute(CHAIN_OBSERVER_INSTALL)
        lua.execute("_G._s2_chain = _R:_hacker_active_chain()")
        lua.execute(CHAIN_OBSERVER_REMOVE)
        lua.execute(r'''
_G._s2_chain_ok = (_s2_chain ~= nil)
_G._s2_chain_kind = _s2_chain and _s2_chain.source
    and _s2_chain.source.kind or nil
''')

        self.assertTrue(bool(g._s2_chain_ok),
            "Hacker positive chain must return a binding candidate")
        self.assertEqual(g._s2_chain_kind, "pocket_ecm_jammer_local")
        self.assertEqual(int(g._ky_chain_e_verify_calls), 2,
            "Hacker must keep the original two full checks (deferral is "
            "Kingpin-only)")
        self.assertEqual(int(g._ky_chain_source_calls), 2,
            "chain must still read the source getter exactly twice")


if __name__ == "__main__":
    unittest.main()
