"""Assault state diagnostics (RED): require [KyoHUD][AssaultStateDiag] messages.

Contract: tests REQUIRE real global `log` calls matching the diagnostic prefix.
Production must emit diagnostic messages on state transitions. Only stable
repeated updates should produce no NEW messages. Field names use
`_assault_state_diag_*` only; no `_diag_reason`, no `PresentationDiag`.

3:1  BAI={} (exact empty table, no getter) -> 1 message reason=bai_advanced_unknown
     with bai_type=table and bai_getter_type=nil. BAI=nil -> 2 total, last has
     state=owned phase=sustain. Repeated updates -> stable at 2.
3:2  set_shape corruption -> rootfalse/nativefalse + 1 reason=render message
     with nonempty predicate. Restore -> certtrue, same prim, 1 owned message.
3:3  70 alternating BAI updates -> 1<=messages<=30 (cap before throw). FRESH
     runtime logthrow: BAI={} -> pcalltrue, rootfalse, attempts>0; BAI=nil ->
     roottrue despite throw.
"""
import unittest

import test_hud_assault_states as states

DIAG_PREFIX = "[KyoHUD][AssaultStateDiag]"

CAPTURE_SETUP = r'''
_assault_state_diag_cap = _assault_state_diag_cap or {}
_assault_state_diag_orig_log = _assault_state_diag_orig_log or log
function log(msg)
    if type(msg) == "string" and msg:find("[KyoHUD][AssaultStateDiag]", 1, true) then
        _assault_state_diag_cap[#_assault_state_diag_cap + 1] = msg
    end
    pcall(_assault_state_diag_orig_log, msg)
end
function _assault_state_diag_clear()
    _assault_state_diag_cap = {}
end
'''


class AssaultStateDiagCaptureTests(unittest.TestCase):
    """RED: require diagnostic messages for state transitions.

    Production must emit [KyoHUD][AssaultStateDiag] messages on BAI changes
    and render failures. Only stable repeated updates should remain silent.
    """

    def test_3_1_bai_empty_then_nil_requires_diagnostics(self):
        """BAI={} -> 1 bai_advanced_unknown; BAI=nil -> 2 total owned+sustain."""
        helper = states.AssaultMultiStateLabelTests()
        lua, ok = helper._make_lua(True, "sustain", False, True, False, False)
        self.assertTrue(ok, "runtime must mount")

        lua.execute(CAPTURE_SETUP)
        lua.execute("_assault_state_diag_clear()")

        lua.execute(r'''
            local A = kyohud.hud.assault

            BAI = {}
            A:update(managers.hud, 2.0, 0.05)
            _msg_count_2 = #_assault_state_diag_cap
            _has_reason_bai = false
            _has_bai_type_table = false
            _has_getter_type_nil = false
            for _, msg in ipairs(_assault_state_diag_cap) do
                if msg:find("reason=bai_advanced_unknown", 1, true) then
                    _has_reason_bai = true
                end
                if msg:find("bai_type=table", 1, true) then
                    _has_bai_type_table = true
                end
                if msg:find("bai_getter_type=nil", 1, true) then
                    _has_getter_type_nil = true
                end
            end

            BAI = nil
            A:update(managers.hud, 2.5, 0.05)
            _msg_count_3 = #_assault_state_diag_cap
            _last_msg = _assault_state_diag_cap[#_assault_state_diag_cap] or ""
            _has_state_owned = _last_msg:find("state=owned", 1, true) ~= nil
            _has_phase_sustain = _last_msg:find("phase=sustain", 1, true) ~= nil

            _assault_state_diag_clear()
            A:update(managers.hud, 3.1, 0.05)
            A:update(managers.hud, 3.2, 0.05)
            A:update(managers.hud, 3.3, 0.05)
            _msg_count_stable = #_assault_state_diag_cap
        ''')

        g = lua.globals()
        self.assertEqual(g._msg_count_2, 1,
            "RED: BAI={} must emit exactly 1 diagnostic message")
        self.assertTrue(g._has_reason_bai,
            "RED: message must contain reason=bai_advanced_unknown")
        self.assertTrue(g._has_bai_type_table,
            "RED: message must contain bai_type=table")
        self.assertTrue(g._has_getter_type_nil,
            "RED: message must contain bai_getter_type=nil")

        self.assertEqual(g._msg_count_3, 2,
            "RED: BAI=nil must result in exactly 2 total messages")
        self.assertTrue(g._has_state_owned,
            "RED: last message must contain state=owned")
        self.assertTrue(g._has_phase_sustain,
            "RED: last message must contain phase=sustain")

        self.assertEqual(g._msg_count_stable, 0,
            "RED: stable repeated updates must emit no new messages")

    def test_3_2_set_shape_corruption_requires_render_diagnostic(self):
        """set_shape corruption -> rootfalse + reason=render; restore -> owned."""
        helper = states.AssaultMultiStateLabelTests()
        lua, ok = helper._make_lua(True, "sustain", False, True, False, False)
        self.assertTrue(ok, "runtime must mount")

        lua.execute(CAPTURE_SETUP)
        lua.execute("_assault_state_diag_clear()")

        lua.execute(r'''
            local A = kyohud.hud.assault
            local p = A._ticker_a
            p:set_y(p:y() + 20)

            local orig_set_shape = p.set_shape
            p.set_shape = function() end

            A:update(managers.hud, 2.0, 0.05)
            _root_hidden = not A._root_panel:visible()
            _native_released = not A._native_acquired
            _msg_count_corrupt = #_assault_state_diag_cap
            _has_reason_render = false
            _has_nonempty_predicate = false
            for _, msg in ipairs(_assault_state_diag_cap) do
                if msg:find("reason=render", 1, true) then
                    _has_reason_render = true
                end
                if msg:find("predicate=") and not msg:find("predicate=$", 1, true) then
                    _has_nonempty_predicate = true
                end
            end
            _prim_identity = tostring(p)

            p.set_shape = orig_set_shape
            _assault_state_diag_clear()
            A:update(managers.hud, 3.0, 0.05)
            _verify_restored = A._render_verified
            _same_prim = (tostring(A._ticker_a) == _prim_identity)
            _msg_count_restore = #_assault_state_diag_cap
            _has_owned_restore = false
            for _, msg in ipairs(_assault_state_diag_cap) do
                if msg:find("state=owned", 1, true) then
                    _has_owned_restore = true
                end
            end
        ''')

        g = lua.globals()
        self.assertTrue(g._root_hidden,
            "RED: root must be hidden after set_shape corruption")
        self.assertTrue(g._native_released,
            "RED: native must be released after set_shape corruption")
        self.assertEqual(g._msg_count_corrupt, 1,
            "RED: corruption must emit exactly 1 diagnostic message")
        self.assertTrue(g._has_reason_render,
            "RED: message must contain reason=render")
        self.assertTrue(g._has_nonempty_predicate,
            "RED: message must contain nonempty predicate=")

        self.assertTrue(g._verify_restored,
            "RED: render must be verified after setter restore")
        self.assertTrue(g._same_prim,
            "RED: same primitive identity after restore")
        self.assertEqual(g._msg_count_restore, 1,
            "RED: restore must emit exactly 1 diagnostic message")
        self.assertTrue(g._has_owned_restore,
            "RED: restore message must contain state=owned")

    def test_3_3_session_cap_and_logthrow_protection(self):
        """70 updates alternating BAI -> 1<=msgs<=30; logthrow protected."""
        helper = states.AssaultMultiStateLabelTests()
        lua, ok = helper._make_lua(True, "sustain", False, True, False, False)
        self.assertTrue(ok, "runtime must mount")

        lua.execute(CAPTURE_SETUP)
        lua.execute("_assault_state_diag_clear()")

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
            _msg_count_cap = #_assault_state_diag_cap
        ''')

        g = lua.globals()
        self.assertGreaterEqual(g._msg_count_cap, 1,
            "RED: 70 alternating updates must emit at least 1 message")
        self.assertLessEqual(g._msg_count_cap, 30,
            "RED: 70 alternating updates must emit at most 30 messages (cap)")

        helper2 = states.AssaultMultiStateLabelTests()
        lua2, ok2 = helper2._make_lua(True, "sustain", False, True, False, False)
        self.assertTrue(ok2, "FRESH runtime must mount")

        lua2.execute(CAPTURE_SETUP)
        lua2.execute("_assault_state_diag_clear()")

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
            "RED: throwing log must not propagate on BAI={} update")
        self.assertTrue(g2._root_hidden_throw,
            "RED: root must be hidden despite throwing log")
        self.assertGreater(g2._attempts_after_2, 0,
            "RED: log must be attempted at least once")

        self.assertTrue(g2._update_ok_3,
            "RED: throwing log must not propagate on BAI=nil update")
        self.assertTrue(g2._root_visible_restore,
            "RED: root must be visible after BAI=nil recovery")


if __name__ == "__main__":
    unittest.main()
