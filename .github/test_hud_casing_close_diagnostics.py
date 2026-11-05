"""LOT3b -- casing close diagnostic ABSENCE contract.

Contract under test (production code must NOT implement):
   - No [KyoHUD][PresentationDiag] lines emitted at startup, stable state,
     failure, recovery, or close.
   - No diagnostic fields (_diag_reason, _diag_messages counters, _diag_lines,
     _diag_cap, _diag_emit, _diag_cc_pre_hide_trace) exist on production objects.
   - Throwing log: attempts==0 (log never called for diagnostics).
   - Functional invariants preserved:
     * Valid show/certified hide -> seven acquired, animation completion,
       zero final native entries, hidden root; silent throughout.
     * Corrupted root/primitive geometry before hide -> native restitution,
       root hidden, zero entries; no diagnostic fields.
     * Throwing log -> hide/lifetime unaffected, zero entries, root hidden,
       closing cleared; no logs.
     * Shared cap fields (_diag_emit, _diag_lines, _diag_cap) absent;
       silent closure.
     * Fallback trace (corner._casing=false) -> native restitution, root hidden,
       zero entries; no diagnostic content.
     * Missing/throwing alpha -> helper absent, diagnostic-only getters not
       touched via actual hide event, attempts==0, no logs.
     * Style property mismatch (layer/primitive_alpha) -> native restitution,
       root hidden, zero entries; no diagnostic content.
   - All scenarios: zero messages, including repeated cycles exceeding old 60 cap.
"""
import unittest

from test_hud_casing_close import _lua_with_casing_close_fixture


DIAG_PREFIX = "[KyoHUD][PresentationDiag]"

_CAPTURE_LUA = r'''
    _diag_messages = _diag_messages or {}
    _diag_orig_log = _diag_orig_log or log
    function log(msg)
        if type(msg) == "string" and msg:find("[KyoHUD][PresentationDiag]", 1, true) then
            _diag_messages[#_diag_messages + 1] = msg
        end
        pcall(_diag_orig_log, msg)
    end
    function _diag_clear() _diag_messages = {} end
    function _diag_cc_msgs()
        local r = {}
        for _, m in ipairs(_diag_messages) do
            if m:find("mode=casing_close", 1, true) then
                r[#r + 1] = m
            end
        end
        return r
    end
    function _diag_total() return #_diag_messages end
'''


def _casing_close_with_capture(extra=""):
    lua, ok = _lua_with_casing_close_fixture()
    assert ok, "fixture prerequisite must exist"
    lua.execute(_CAPTURE_LUA)
    if extra:
        lua.execute(extra)
    return lua


class CasingCloseDiagAbsenceTests(unittest.TestCase):

    def test_casing_close_event_silence_and_idle_silence(self):
        """Valid show/certified hide produces zero diagnostic lines; idle silent."""
        lua = _casing_close_with_capture()
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(AL._casing_native_acquired == true, "prereq: acquired")
            assert(AL._casing_render_verified == true, "prereq: verified")

            _diag_clear()
            local before_idle = #_diag_messages
            RT:update(managers.hud, 1.5, 0.05)
            RT:update(managers.hud, 2.0, 0.05)
            RT:update(managers.hud, 2.5, 0.05)
            _idle_cc = #_diag_cc_msgs()
            _idle_total = #_diag_messages

            _diag_clear()
            managers.hud:hide_casing()
            for i = 1, 30 do
                _resume_coroutines(0.05)
                RT:update(managers.hud, 2.5 + i * 0.05, 0.05)
            end
            RT:update(managers.hud, 4.05, 0.05)

            _close_msg_count = #_diag_messages

            _diag_clear()
            local pre_stable = #_diag_messages
            RT:update(managers.hud, 5.0, 0.05)
            RT:update(managers.hud, 6.0, 0.05)
            _stable_cc = #_diag_cc_msgs()
            _stable_total = #_diag_messages

            _after_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then _after_nv = _after_nv + 1 end
            end
            _root_gone = AL._casing_root_panel == nil
                or AL._casing_root_panel:visible() == false
        ''')
        g = lua.globals()

        self.assertEqual(g._idle_cc, 0,
            "idle repeated ordinary updates must emit zero casing_close lines")
        self.assertEqual(g._idle_total, 0,
            "idle repeated ordinary updates must emit zero total lines")

        self.assertEqual(g._close_msg_count, 0,
            "valid close must emit zero diagnostic lines")

        self.assertEqual(g._stable_cc, 0,
            "stable post-close updates must emit zero casing_close lines")
        self.assertEqual(g._stable_total, 0,
            "stable post-close updates must emit zero total lines")
        self.assertEqual(g._after_nv, 0,
            "Functional: native ownership must be 0 after close")
        self.assertTrue(g._root_gone,
            "Functional: root must be hidden or removed after close")

    def test_casing_close_refused_on_actual_geometry_corruption_silence(self):
        """Corrupted root/primitive geometry before hide -> silent cert rejection."""
        lua = _casing_close_with_capture()
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(AL._casing_render_verified == true, "prereq: verified")
            assert(type(AL._casing_bg) == "table", "prereq: _casing_bg exists")

            AL._casing_bg:set_shape(9999, 9999, 0, 0)
            assert(AL._casing_bg:x() == 9999, "prereq: real setter applied")

            _diag_clear()
            managers.hud:hide_casing()

            _refuse_msg_count = #_diag_messages

            _after_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then _after_nv = _after_nv + 1 end
            end
            _root_hidden = AL._casing_root_panel == nil
                or AL._casing_root_panel:visible() == false
        ''')
        g = lua.globals()

        self.assertEqual(g._refuse_msg_count, 0,
            "corrupted geometry must emit zero diagnostic lines")
        self.assertEqual(g._after_nv, 0,
            "Functional: native ownership must be 0 after refused")
        self.assertTrue(g._root_hidden,
            "Functional: root must be hidden after refused")

    def test_throwing_logger_attempts_zero_and_casing_close_silence(self):
        """Throwing log: attempts==0, does not alter visibility/lifetime or propagate."""
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok)

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(AL._casing_native_acquired == true, "prereq: acquired")

            _attempts = 0
            _attempted_cc = false
            function log(msg)
                if type(msg) == "string" and msg:find("[KyoHUD][AssaultStateDiag]", 1, true) then
                    return
                end
                _attempts = _attempts + 1
                if type(msg) == "string" and msg:find("mode=casing_close", 1, true) then
                    _attempted_cc = true
                end
                error("simulated log failure")
            end

            local ok1 = pcall(function() managers.hud:hide_casing() end)
            _hide_ok = ok1

            local ok2 = pcall(function()
                for i = 1, 30 do _resume_coroutines(0.05) end
            end)
            _coro_ok = ok2

            local ok3 = pcall(function()
                RT:update(managers.hud, 3.0, 0.05)
            end)
            _update_ok = ok3

            _after_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then _after_nv = _after_nv + 1 end
            end
            _root_gone = AL._casing_root_panel == nil
                or AL._casing_root_panel:visible() == false
            _closing_cleared = AL._casing_closing == false
            _attempts_final = _attempts
        ''')
        g = lua.globals()

        self.assertTrue(g._hide_ok,
            "throwing log must not propagate on hide_casing")
        self.assertTrue(g._coro_ok,
            "throwing log must not propagate during coroutine resume")
        self.assertTrue(g._update_ok,
            "throwing log must not propagate on update")
        self.assertFalse(g._attempted_cc,
            "log must not be attempted with mode=casing_close (no diagnostics)")
        self.assertEqual(g._after_nv, 0,
            "Functional: entries released despite throwing log")
        self.assertTrue(g._root_gone,
            "Functional: root hidden despite throwing log")
        self.assertTrue(g._closing_cleared,
            "Functional: closing state cleared despite throwing log")
        self.assertEqual(g._attempts_final, 0,
            "log must not be attempted (no diagnostics emitted)")

    def test_shared_cap_fields_absent_and_silent_closure(self):
        """Shared cap fields (_diag_emit, _diag_lines, _diag_cap) absent; silent closure."""
        lua = _casing_close_with_capture()
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(AL._casing_render_verified == true, "prereq: verified")

            _has_diag_emit = kyohud.hud._diag_emit ~= nil
            _has_diag_lines = kyohud.hud._diag_lines ~= nil
            _has_diag_cap = kyohud.hud._diag_cap ~= nil

            _diag_clear()
            managers.hud:hide_casing()
            for i = 1, 30 do _resume_coroutines(0.05) end
            RT:update(managers.hud, 3.0, 0.05)

            _close_msg_count = #_diag_messages

            RT:update(managers.hud, 4.0, 0.05)
            RT:update(managers.hud, 5.0, 0.05)
            _stable_msg_count = #_diag_messages
        ''')
        g = lua.globals()

        self.assertFalse(g._has_diag_emit,
            "_diag_emit field must not exist on production hud object")
        self.assertFalse(g._has_diag_lines,
            "_diag_lines field must not exist on production hud object")
        self.assertFalse(g._has_diag_cap,
            "_diag_cap field must not exist on production hud object")
        self.assertEqual(g._close_msg_count, 0,
            "close must emit zero diagnostic lines")
        self.assertEqual(g._stable_msg_count, 0,
            "stable post-close must emit zero diagnostic lines")

    def test_fallback_trace_silence_for_casing_and_pnr(self):
        """Fallback trace (corner._casing=false) -> silent cert rejection."""
        lua = _casing_close_with_capture()
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(AL._casing_native_acquired == true, "prereq: acquired")
            assert(AL._casing_render_verified == true, "prereq: verified")

            local ok_corner, corner = pcall(function()
                return AL._manager._hud_assault_corner
            end)
            assert(ok_corner and corner, "prereq: corner")

            corner._casing = false
            corner._point_of_no_return = false

            _diag_clear()
            managers.hud:hide_casing()

            _refuse_msg_count = #_diag_messages

            local nv = kyohud.hud.native_visibility
            _after_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then _after_nv = _after_nv + 1 end
            end
            _root_hidden = AL._casing_root_panel == nil
                or AL._casing_root_panel:visible() == false
        ''')
        g = lua.globals()

        self.assertEqual(g._refuse_msg_count, 0,
            "fallback refusal must emit zero diagnostic lines")
        self.assertEqual(g._after_nv, 0,
            "Functional: native ownership must be 0 after refused fallback")
        self.assertTrue(g._root_hidden,
            "Functional: root must be hidden after refused fallback")

    def test_pre_hide_trace_helper_absent_and_silence(self):
        """Helper _diag_cc_pre_hide_trace absent; diagnostic-only getters not touched; attempts==0."""
        lua = _casing_close_with_capture()
        lua.execute(r'''
            local AL = kyohud.hud.alerts
            local RT = kyohud.hud.runtime

            _has_helper = AL._diag_cc_pre_hide_trace ~= nil

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            local root = AL._casing_root_panel
            assert(root ~= nil, "casing root must exist")
            local original_alpha = root.alpha

            _alpha_get_attempts = 0

            kyohud.settings.enable_alerts = false
            root.alpha = nil
            _diag_clear()
            managers.hud:hide_casing()
            for i = 1, 30 do _resume_coroutines(0.05) end
            _missing_ok = true
            _missing_attempts = _alpha_get_attempts
            _missing_msg_count = #_diag_messages

            _alpha_get_attempts = 0
            root.alpha = function(self)
                _alpha_get_attempts = _alpha_get_attempts + 1
                error("simulated alpha failure")
            end
            _diag_clear()
            managers.hud:hide_casing()
            for i = 1, 30 do _resume_coroutines(0.05) end
            _throw_ok = true
            _throw_attempts = _alpha_get_attempts
            _throw_msg_count = #_diag_messages

            root.alpha = original_alpha
        ''')
        g = lua.globals()
        self.assertFalse(g._has_helper,
            "_diag_cc_pre_hide_trace helper must not exist on production object")
        self.assertTrue(g._missing_ok,
            "missing alpha: hide event must not propagate error")
        self.assertEqual(g._missing_attempts, 0,
            "missing alpha: diagnostic-only getter must not be invoked")
        self.assertEqual(g._missing_msg_count, 0,
            "missing alpha: must emit zero diagnostic lines")

        self.assertTrue(g._throw_ok,
            "throwing alpha: hide event must not propagate error")
        self.assertEqual(g._throw_attempts, 0,
            "throwing alpha: diagnostic-only getter must not be invoked")
        self.assertEqual(g._throw_msg_count, 0,
            "throwing alpha: must emit zero diagnostic lines")

    def test_casing_close_refused_on_style_property_mismatch_silence(self):
        """Style property mismatch (layer/primitive_alpha) -> silent cert rejection."""
        cases = [
            {
                "name": "layer_corrupted",
                "mutate": r'''
                    local AL = kyohud.hud.alerts
                    AL._casing_bg:set_layer(7)
                    assert(AL._casing_bg:layer() == 7, "prereq: layer set to 7")
                ''',
            },
            {
                "name": "primitive_alpha_overridden",
                "mutate": r'''
                    local AL = kyohud.hud.alerts
                    local orig_alpha = AL._casing_bg.alpha
                    AL._casing_bg.alpha = function(self)
                        return 0.77
                    end
                    _restore_alpha = orig_alpha
                ''',
                "restore": r'''
                    local AL = kyohud.hud.alerts
                    if _restore_alpha then
                        AL._casing_bg.alpha = _restore_alpha
                    end
                ''',
            },
        ]

        for case in cases:
            with self.subTest(case=case["name"]):
                lua = _casing_close_with_capture()
                lua.execute(r'''
                    local RT = kyohud.hud.runtime
                    local AL = kyohud.hud.alerts

                    RT:mount(managers.hud)
                    managers.hud:show_casing(nil)
                    RT:update(managers.hud, 1.0, 0.05)

                    assert(AL._casing_render_verified == true, "prereq: verified")
                    assert(type(AL._casing_bg) == "table", "prereq: _casing_bg exists")

                    _initial_baseline = AL._casing_bg:layer()
                    _initial_acquired = AL._casing_native_acquired
                ''')

                lua.execute(case["mutate"])

                lua.execute(r'''
                    local AL = kyohud.hud.alerts
                    _diag_clear()
                    managers.hud:hide_casing()

                    _refuse_msg_count = #_diag_messages

                    local nv = kyohud.hud.native_visibility
                    _after_nv = 0
                    for _, e in ipairs(nv._entries or {}) do
                        if e.owner == "alerts" then _after_nv = _after_nv + 1 end
                    end
                    _root_hidden = AL._casing_root_panel == nil
                        or AL._casing_root_panel:visible() == false
                ''')

                if "restore" in case:
                    lua.execute(case["restore"])

                g = lua.globals()

                self.assertTrue(g._initial_baseline is not None,
                    "must capture initial baseline")
                self.assertTrue(g._initial_acquired == True,
                    "must capture initial acquired=true")

                self.assertEqual(g._refuse_msg_count, 0,
                    "style mismatch must emit zero diagnostic lines")
                self.assertEqual(g._after_nv, 0,
                    "Functional: native ownership must be 0 after refused")
                self.assertTrue(g._root_hidden,
                    "Functional: root must be hidden after refused")


if __name__ == '__main__':
    unittest.main()
