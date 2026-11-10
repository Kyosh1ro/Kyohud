"""Assault state diagnostics: ABSENCE contract.

Production must NOT emit any [KyoHUD][AssaultStateDiag] line at startup,
state transitions, render failure, recovery, session churn, or when the host
logger throws. The former lot-3a emitter has been removed; only the functional
state machine remains.

Functional invariants preserved and asserted here:
  * BAI={} fallback hides the owned root; BAI=nil restores visibility.
  * Render corruption fails verification, hides the root and releases native
    ownership; restoring the setter returns the same primitive and verifies.
  * 70 alternating BAI updates stay silent.
  * A throwing host log never blocks updates and is never called.
"""
import unittest

import test_hud_assault_states as states

DIAG_PREFIX = "[KyoHUD][AssaultStateDiag]"

CAPTURE_SETUP = r'''
_diag_cap = _diag_cap or {}
_diag_orig_log = _diag_orig_log or log
function log(msg)
    if type(msg) == "string" and msg:find("[KyoHUD][AssaultStateDiag]", 1, true) then
        _diag_cap[#_diag_cap + 1] = msg
    end
    pcall(_diag_orig_log, msg)
end
function _diag_clear()
    _diag_cap = {}
end
'''


class AssaultStateDiagAbsenceTests(unittest.TestCase):

    def test_bai_transitions_and_stable_state_are_silent(self):
        helper = states.AssaultMultiStateLabelTests()
        lua, ok = helper._make_lua(True, "sustain", False, True, False, False)
        self.assertTrue(ok, "runtime must mount")

        lua.execute(CAPTURE_SETUP)
        lua.execute("_diag_clear()")

        lua.execute(r'''
            local A = kyohud.hud.assault

            BAI = {}
            A:update(managers.hud, 2.0, 0.05)
            _root_hidden_bai = not A._root_panel:visible()

            BAI = nil
            A:update(managers.hud, 2.5, 0.05)
            _root_visible_bai = A._root_panel:visible()

            A:update(managers.hud, 3.1, 0.05)
            A:update(managers.hud, 3.2, 0.05)
            A:update(managers.hud, 3.3, 0.05)
            _msg_count = #_diag_cap
        ''')

        g = lua.globals()
        self.assertEqual(g._msg_count, 0,
            "state transitions and stable updates must emit zero diagnostic lines")
        self.assertTrue(g._root_hidden_bai,
            "BAI={} fallback must hide the owned root")
        self.assertTrue(g._root_visible_bai,
            "BAI=nil recovery must restore root visibility")

    def test_render_corruption_and_restore_are_silent(self):
        helper = states.AssaultMultiStateLabelTests()
        lua, ok = helper._make_lua(True, "sustain", False, True, False, False)
        self.assertTrue(ok, "runtime must mount")

        lua.execute(CAPTURE_SETUP)
        lua.execute("_diag_clear()")

        lua.execute(r'''
            local A = kyohud.hud.assault
            local p = A._ticker_a
            p:set_y(p:y() + 20)

            local orig_set_shape = p.set_shape
            p.set_shape = function() end

            A:update(managers.hud, 2.0, 0.05)
            _root_hidden = not A._root_panel:visible()
            _native_released = not A._native_acquired
            _msg_count_corrupt = #_diag_cap
            _prim_identity = tostring(p)

            p.set_shape = orig_set_shape
            _diag_clear()
            A:update(managers.hud, 3.0, 0.05)
            _verify_restored = A._render_verified
            _same_prim = (tostring(A._ticker_a) == _prim_identity)
            _msg_count_restore = #_diag_cap
        ''')

        g = lua.globals()
        self.assertTrue(g._root_hidden,
            "root must be hidden after set_shape corruption")
        self.assertTrue(g._native_released,
            "native must be released after set_shape corruption")
        self.assertEqual(g._msg_count_corrupt, 0,
            "render corruption must emit zero diagnostic lines")
        self.assertTrue(g._verify_restored,
            "render must be verified after setter restore")
        self.assertTrue(g._same_prim,
            "same primitive identity must be retained after restore")
        self.assertEqual(g._msg_count_restore, 0,
            "render recovery must emit zero diagnostic lines")

    def test_session_churn_and_throwing_log_are_silent(self):
        helper = states.AssaultMultiStateLabelTests()
        lua, ok = helper._make_lua(True, "sustain", False, True, False, False)
        self.assertTrue(ok, "runtime must mount")

        lua.execute(CAPTURE_SETUP)
        lua.execute("_diag_clear()")

        lua.execute(r'''
            local A = kyohud.hud.assault

            local t = 2.0
            for i = 1, 70 do
                if i % 2 == 0 then
                    BAI = {}
                else
                    BAI = nil
                end
                t = t + 0.6
                A:update(managers.hud, t, 0.05)
            end
            _msg_count_cap = #_diag_cap
        ''')

        g = lua.globals()
        self.assertEqual(g._msg_count_cap, 0,
            "70 alternating updates must emit zero diagnostic lines")

        helper2 = states.AssaultMultiStateLabelTests()
        lua2, ok2 = helper2._make_lua(True, "sustain", False, True, False, False)
        self.assertTrue(ok2, "fresh runtime must mount")

        lua2.execute(r'''
            local A = kyohud.hud.assault
            _attempts = 0
            function log(msg)
                _attempts = _attempts + 1
                error("simulated log failure")
            end

            BAI = {}
            local ok_update2 = pcall(function()
                A:update(managers.hud, 2.0, 0.05)
            end)
            _update_ok_2 = ok_update2
            _root_hidden_throw = not A._root_panel:visible()
            _attempts_after_2 = _attempts

            BAI = nil
            local ok_update3 = pcall(function()
                A:update(managers.hud, 2.5, 0.05)
            end)
            _update_ok_3 = ok_update3
            _root_visible_restore = A._root_panel:visible()
            _attempts_final = _attempts
        ''')

        g2 = lua2.globals()
        self.assertTrue(g2._update_ok_2,
            "throwing log must not propagate on BAI={} update")
        self.assertTrue(g2._root_hidden_throw,
            "root must be hidden despite throwing log")
        self.assertEqual(g2._attempts_after_2, 0,
            "log must not be called for diagnostics on BAI={}")
        self.assertTrue(g2._update_ok_3,
            "throwing log must not propagate on BAI=nil update")
        self.assertTrue(g2._root_visible_restore,
            "root must be visible after BAI=nil recovery")
        self.assertEqual(g2._attempts_final, 0,
            "log must not be called at all when diagnostics are removed")


if __name__ == "__main__":
    unittest.main()
