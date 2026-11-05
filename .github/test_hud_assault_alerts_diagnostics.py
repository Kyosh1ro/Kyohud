"""Presentation diagnostics: ABSENCE contract for assault/alerts native fallback.

Contract under test (production code must NOT implement):
   - No [KyoHUD][PresentationDiag] lines emitted at startup, stable state,
     failure, recovery, or close.
   - No diagnostic fields (_diag_reason, _diag_messages counters, _diag_lines,
     _diag_cap, _diag_emit) exist on production objects.
   - Throwing log: attempts==0 (log never called for diagnostics).
   - Functional invariants preserved:
     * Decoration corruption -> _verify_render false, root hidden, NV released;
       restore setter -> same primitive/root retained, _verify_render true.
     * Ticker x/y/w/h/alpha/layer/parent mutations -> each fails _verify_render,
       restore passes; no production diagnostic fields.
     * Translucent alpha -> fail/restore invariant preserved.
     * DB false / bitmap throw / bitmap nil -> mount/update protected,
       root hidden, _verify_render false, zero native entries; stable silence.
   - Session cap: repeated cycles (including >60) emit zero messages.
"""
import unittest

from test_hud_presentation_recovery import runtime


DIAG_PREFIX = "[KyoHUD][PresentationDiag]"

DECORATION = {"assault": "_hostages_bg", "casing": "_casing_bg", "pnr": "_pnr_bg"}
ROOT_FIELD = {"assault": "_root_panel", "casing": "_casing_root_panel", "pnr": "_root_panel"}
OWNER = {"assault": "assault", "casing": "alerts", "pnr": "alerts"}


def _diag_runtime(mode, before=""):
    capture = (
        '_diag_messages = _diag_messages or {};'
        '_diag_orig_log = _diag_orig_log or log;'
        'function log(msg)'
        '  if type(msg) == "string" and msg:find("' + DIAG_PREFIX + '", 1, true) then'
        '    _diag_messages[#_diag_messages + 1] = msg'
        '  end;'
        '  pcall(_diag_orig_log, msg)'
        'end;'
        'function _diag_clear() _diag_messages = {} end'
    )
    combined = capture + "\n" + before
    return runtime(mode, combined)


def _diag_count(lua):
    return lua.globals()._diag_messages


class PresentationDiagAbsenceTests(unittest.TestCase):

    def test_initial_state_silence_and_monotonic_silence(self):
        for mode in ("assault", "casing", "pnr"):
            with self.subTest(mode=mode):
                lua = _diag_runtime(mode)
                msgs = _diag_count(lua)
                self.assertEqual(len(msgs), 0,
                    mode + ": initial update must produce zero diagnostic lines")
                lua.execute(r'''
                    _before = #_diag_messages
                    kyohud.hud.runtime:update(managers.hud, 1.6, .05)
                    kyohud.hud.runtime:update(managers.hud, 2.2, .05)
                    kyohud.hud.runtime:update(managers.hud, 3.0, .05)
                    _after = #_diag_messages
                    _has_diag_reason = subject._diag_reason ~= nil
                    _has_diag_transition = subject._diag_transition ~= nil
                    _has_glyph_prim_diag = subject._glyph_prim_diag ~= nil
                    _has_diag_emit = kyohud.hud._diag_emit ~= nil
                    _has_diag_cap = kyohud.hud._diag_cap ~= nil
                    _has_diag_lines = kyohud.hud._diag_lines ~= nil
                ''')
                g = lua.globals()
                self.assertEqual(g._after, 0,
                    mode + ": repeated monotonic updates must remain silent")
                self.assertFalse(g._has_diag_reason,
                    mode + ": _diag_reason field must not exist on production subject")
                self.assertFalse(g._has_diag_transition,
                    mode + ": _diag_transition field must not exist on production subject")
                self.assertFalse(g._has_glyph_prim_diag,
                    mode + ": _glyph_prim_diag field must not exist on production subject")
                self.assertFalse(g._has_diag_emit,
                    mode + ": _diag_emit field must not exist on production hud object")
                self.assertFalse(g._has_diag_cap,
                    mode + ": _diag_cap field must not exist on production hud object")
                self.assertFalse(g._has_diag_lines,
                    mode + ": _diag_lines field must not exist on production hud object")

    def test_decoration_failure_and_recovery_silence(self):
        for mode, field in DECORATION.items():
            with self.subTest(mode=mode):
                lua = _diag_runtime(mode)
                rf = ROOT_FIELD[mode]
                owner = OWNER[mode]
                lua.globals().field = field
                lua.globals().rf = rf
                lua.globals().owner = owner
                lua.execute(r'''
                    local p = subject[field]
                    local root = subject[rf]
                    local original_set_shape = p.set_shape
                    p:set_shape(p:x() + 30, p:y(), p:w(), p:h())
                    p.set_shape = function() end
                    _diag_clear()
                    kyohud.hud.runtime:update(managers.hud, 1.6, .05)
                    _fail_count = #_diag_messages
                    _verify_ok = subject:_verify_render()
                    _root_hidden = not root:visible()
                    _nv_released = true
                    for _, entry in ipairs(kyohud.hud.native_visibility._entries) do
                        if entry.owner == owner then _nv_released = false end
                    end
                    p.set_shape = original_set_shape
                    _diag_clear()
                    kyohud.hud.runtime:update(managers.hud, 2.2, .05)
                    _recover_count = #_diag_messages
                    _same_prim = (subject[field] == p)
                    _same_root = (subject[rf] == root)
                    _render_ok = subject:_verify_render()
                    kyohud.hud.runtime:update(managers.hud, 3.0, .05)
                    kyohud.hud.runtime:update(managers.hud, 4.0, .05)
                    _post_stable = #_diag_messages
                ''')
                g = lua.globals()
                self.assertEqual(g._fail_count, 0,
                    mode + ": failure must emit zero diagnostic lines")
                self.assertFalse(g._verify_ok,
                    mode + ": _verify_render must be false after corruption")
                self.assertTrue(g._root_hidden,
                    mode + ": root must be hidden on failure")
                self.assertTrue(g._nv_released,
                    mode + ": native ownership must be released on failure")
                self.assertEqual(g._recover_count, 0,
                    mode + ": repair must emit zero diagnostic lines")
                self.assertTrue(g._same_prim,
                    mode + ": same primitive retained after recovery")
                self.assertTrue(g._same_root,
                    mode + ": same root retained after recovery")
                self.assertTrue(g._render_ok,
                    mode + ": render must verify after recovery")
                self.assertEqual(g._post_stable, 0,
                    mode + ": post-recovery updates must remain silent")

    def test_session_cap_silence_exceeding_old_cap(self):
        for mode, field in DECORATION.items():
            with self.subTest(mode=mode):
                lua = _diag_runtime(mode)
                rf = ROOT_FIELD[mode]
                lua.globals().field = field
                lua.globals().rf = rf
                lua.execute(r'''
                    local p = subject[field]
                    local root = subject[rf]
                    local original_set_shape = p.set_shape
                    local all_fail_hidden = true
                    local all_repair_verified = true
                    local t = 10.0
                    for cycle = 1, 40 do
                        p:set_shape(p:x() + 30, p:y(), p:w(), p:h())
                        p.set_shape = function() end
                        t = t + 0.6
                        kyohud.hud.runtime:update(managers.hud, t, .05)
                        if root:visible() then all_fail_hidden = false end
                        p.set_shape = original_set_shape
                        t = t + 0.6
                        kyohud.hud.runtime:update(managers.hud, t, .05)
                        if not subject:_verify_render() then all_repair_verified = false end
                    end
                    _final_lines = #_diag_messages
                    _all_fail_hidden = all_fail_hidden
                    _all_repair_verified = all_repair_verified
                    for extra = 1, 25 do
                        p:set_shape(p:x() + 30, p:y(), p:w(), p:h())
                        p.set_shape = function() end
                        t = t + 0.6
                        kyohud.hud.runtime:update(managers.hud, t, .05)
                        p.set_shape = original_set_shape
                        t = t + 0.6
                        kyohud.hud.runtime:update(managers.hud, t, .05)
                    end
                    _post_lines = #_diag_messages
                ''')
                g = lua.globals()
                self.assertTrue(g._all_fail_hidden,
                    mode + ": every failure must hide root")
                self.assertTrue(g._all_repair_verified,
                    mode + ": every repair must verify render")
                self.assertEqual(g._final_lines, 0,
                    mode + ": zero diagnostic lines after 40 cycles")
                self.assertEqual(g._post_lines, 0,
                    mode + ": zero lines after exceeding old 60 cap (65 total cycles)")

    def test_throwing_logger_attempts_zero_and_silence(self):
        for mode, field in DECORATION.items():
            with self.subTest(mode=mode):
                lua = runtime(mode)
                rf = ROOT_FIELD[mode]
                lua.globals().field = field
                lua.globals().rf = rf
                lua.execute(r'''
                    _attempts = 0
                    function log(msg)
                        _attempts = _attempts + 1
                        error("simulated log failure")
                    end
                    local p = subject[field]
                    local root = subject[rf]
                    local original_set_shape = p.set_shape
                    p:set_shape(p:x() + 30, p:y(), p:w(), p:h())
                    p.set_shape = function() end
                    local ok1 = pcall(function()
                        kyohud.hud.runtime:update(managers.hud, 1.6, .05)
                    end)
                    _update_ok_failure = ok1
                    _root_hidden = not root:visible()
                    p.set_shape = original_set_shape
                    local ok2 = pcall(function()
                        kyohud.hud.runtime:update(managers.hud, 2.2, .05)
                    end)
                    _update_ok_recovery = ok2
                    _root_visible = root:visible()
                    _render_ok = subject:_verify_render()
                    _attempts_final = _attempts
                ''')
                g = lua.globals()
                self.assertTrue(g._update_ok_failure,
                    mode + ": throwing log must not propagate on failure")
                self.assertTrue(g._root_hidden,
                    mode + ": root must be hidden despite throwing log")
                self.assertTrue(g._update_ok_recovery,
                    mode + ": throwing log must not propagate on recovery")
                self.assertTrue(g._root_visible,
                    mode + ": root must be visible after recovery")
                self.assertTrue(g._render_ok,
                    mode + ": render must verify after recovery")
                self.assertEqual(g._attempts_final, 0,
                    mode + ": log must not be attempted (no diagnostics emitted)")

    def test_casing_ticker_property_mutation_silence(self):
        """Mutate each retained ticker property; verify fail/restore with zero diagnostics."""
        lua = _diag_runtime("casing")
        lua.execute(r'''
            local tp = subject._casing_ticker_panel
            local geom = subject._casing_layout_cache.ticker

            local properties = {
                {name = "x", getter = function(p) return p:x() end,
                 setter = function(p, v) p:set_x(v) end, desired = geom.x},
                {name = "y", getter = function(p) return p:y() end,
                 setter = function(p, v) p:set_y(v) end, desired = geom.y},
                {name = "w", getter = function(p) return p:w() end,
                 setter = function(p, v) p:set_shape(p:x(), p:y(), v, p:h()) end, desired = geom.w},
                {name = "h", getter = function(p) return p:h() end,
                 setter = function(p, v) p:set_shape(p:x(), p:y(), p:w(), v) end, desired = geom.h},
                {name = "alpha", getter = function(p) return p:alpha() end,
                 setter = function(p, v) p:set_alpha(v) end, desired = 1},
                {name = "layer", getter = function(p) return p:layer() end,
                 setter = function(p, v) p:set_layer(v) end, desired = 1},
            }

            _prop_results = {}
            for idx, prop in ipairs(properties) do
                local original = prop.getter(tp)
                prop.setter(tp, original + 999)
                _diag_clear()
                local ok = subject:_verify_render()
                local actual_val = prop.getter(tp)
                local desired_val = prop.desired
                _prop_results[idx] = {
                    name = prop.name,
                    fail_ok = ok,
                    actual = string.format("%.17g", actual_val),
                    desired = string.format("%.17g", desired_val),
                }
                prop.setter(tp, original)
                local ok2 = subject:_verify_render()
                _prop_results[idx].restore_ok = ok2
                _prop_results[idx].msg_count = #_diag_messages
            end

            local original_parent = tp:parent()
            local fake_parent = _make_panel_extended("fake_parent")
            tp._parent = fake_parent
            _diag_clear()
            local ok_parent = subject:_verify_render()
            _parent_diff = {
                fail_ok = ok_parent,
                msg_count = #_diag_messages,
            }

            tp._parent = original_parent
            local ok_restore = subject:_verify_render()
            _parent_same = {
                restore_ok = ok_restore,
            }
        ''')
        g = lua.globals()
        for idx in range(1, 7):
            r = g._prop_results[idx]
            name = str(r["name"])
            self.assertFalse(r["fail_ok"],
                name + ": mutation must_fail")
            self.assertEqual(r["msg_count"], 0,
                name + ": mutation must emit zero diagnostic lines")
            self.assertTrue(r["restore_ok"],
                name + ": restore must pass before next mutation")

        pd = g._parent_diff
        self.assertFalse(pd["fail_ok"], "parent: mutation must fail")
        self.assertEqual(pd["msg_count"], 0,
            "parent: mutation must emit zero diagnostic lines")

        ps = g._parent_same
        self.assertTrue(ps["restore_ok"], "parent: restore must pass")

    def test_translucent_background_alpha_silence(self):
        """Engine evidence: _casing_bg and _pnr_status_bg alpha mutations fail/restore silently."""
        ALPHA_FIELD = {"casing": "_casing_bg", "pnr": "_pnr_status_bg"}
        DESIRED_ALPHA = {"casing": 0.80, "pnr": 0.75}

        for mode in ("casing", "pnr"):
            with self.subTest(mode=mode):
                lua = _diag_runtime(mode)
                field = ALPHA_FIELD[mode]
                desired = DESIRED_ALPHA[mode]
                lua.globals().field = field
                lua.globals().desired = desired
                lua.execute(r'''
                    local p = subject[field]
                    local original_alpha = p:alpha()
                    p:set_alpha(0.2)
                    _diag_clear()
                    local ok = subject:_verify_render()
                    local color_alpha = p:color().a
                    local primitive_alpha = p:alpha()
                    _fail_result = {
                        ok = ok,
                        msg_count = #_diag_messages,
                        color_alpha = string.format("%.17g", color_alpha),
                        primitive_alpha = string.format("%.17g", primitive_alpha),
                        desired = string.format("%.17g", desired),
                    }
                    p:set_alpha(original_alpha)
                    local ok2 = subject:_verify_render()
                    _restore_result = {
                        ok = ok2,
                        msg_count = #_diag_messages,
                    }
                ''')
                g = lua.globals()
                fr = g._fail_result
                self.assertFalse(fr["ok"],
                    mode + ": mutation must_fail")
                self.assertEqual(fr["msg_count"], 0,
                    mode + ": mutation must emit zero diagnostic lines")
                rr = g._restore_result
                self.assertTrue(rr["ok"],
                    mode + ": restore must pass")
                self.assertEqual(rr["msg_count"], 0,
                    mode + ": restore must emit zero diagnostic lines")

    def test_assault_db_unavailable_and_bitmap_constructor_silence(self):
        """Assault before mount: DB.has false, bitmap throw vs nil -> silent protection."""
        from test_hud_assault_alerts_presentation import _lua_with_presentation_state

        lua, ok = _lua_with_presentation_state()
        self.assertTrue(ok)

        lua.execute(r'''
            _diag_messages = _diag_messages or {}
            _diag_orig_log = _diag_orig_log or log
            function log(msg)
                if type(msg) == "string" and msg:find("[KyoHUD][PresentationDiag]", 1, true) then
                    _diag_messages[#_diag_messages + 1] = msg
                end
                pcall(_diag_orig_log, msg)
            end

            DB = {has = function() return false end}
            function Idstring(path) return path end

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            RT:update(managers.hud, 1.0, 0.05)

            _db_msg_count = #_diag_messages

            local root = kyohud.hud.assault._root_panel
            _db_root_hidden = not root:visible()
            _db_verify_ok = kyohud.hud.assault:_verify_render()
            _db_no_native = true
            for _, entry in ipairs(kyohud.hud.native_visibility._entries) do
                if entry.owner == "assault" then _db_no_native = false end
            end
        ''')
        g = lua.globals()
        self.assertEqual(g._db_msg_count, 0,
            "DB false: must emit zero diagnostic lines")
        self.assertTrue(g._db_root_hidden,
            "DB false: Assault root must be hidden")
        self.assertFalse(g._db_verify_ok,
            "DB false: _verify_render must be false")
        self.assertTrue(g._db_no_native,
            "DB false: no assault native entries must exist")

        lua2, ok2 = _lua_with_presentation_state()
        self.assertTrue(ok2)
        lua2.execute(r'''
            _diag_messages = _diag_messages or {}
            _diag_orig_log = _diag_orig_log or log
            function log(msg)
                if type(msg) == "string" and msg:find("[KyoHUD][PresentationDiag]", 1, true) then
                    _diag_messages[#_diag_messages + 1] = msg
                end
                pcall(_diag_orig_log, msg)
            end

            local _current_make = _make_panel_extended
            function _make_panel_extended(name)
                local p = _current_make(name)
                p.bitmap = function(self, opts)
                    error("simulated bitmap constructor failure")
                end
                return p
            end

            local ok_mount = pcall(function()
                kyohud.hud.runtime:mount(managers.hud)
            end)
            local ok_update = pcall(function()
                kyohud.hud.runtime:update(managers.hud, 1.0, 0.05)
            end)
            _bitmap_throw_mount_ok = ok_mount
            _bitmap_throw_update_ok = ok_update

            _bt_msg_count = #_diag_messages

            local root = kyohud.hud.assault._root_panel
            _bt_root_hidden = not root:visible()
            _bt_verify_ok = kyohud.hud.assault:_verify_render()
            _bt_no_native = true
            for _, entry in ipairs(kyohud.hud.native_visibility._entries) do
                if entry.owner == "assault" then _bt_no_native = false end
            end
        ''')
        g2 = lua2.globals()
        self.assertTrue(g2._bitmap_throw_mount_ok,
            "bitmap throw: mount must not propagate (protected)")
        self.assertTrue(g2._bitmap_throw_update_ok,
            "bitmap throw: update must not propagate (protected)")
        self.assertEqual(g2._bt_msg_count, 0,
            "bitmap throw: must emit zero diagnostic lines")
        self.assertTrue(g2._bt_root_hidden,
            "bitmap throw: Assault root must be hidden")
        self.assertFalse(g2._bt_verify_ok,
            "bitmap throw: _verify_render must be false")
        self.assertTrue(g2._bt_no_native,
            "bitmap throw: no assault native entries must exist")

        lua3, ok3 = _lua_with_presentation_state()
        self.assertTrue(ok3)
        lua3.execute(r'''
            _diag_messages = _diag_messages or {}
            _diag_orig_log = _diag_orig_log or log
            function log(msg)
                if type(msg) == "string" and msg:find("[KyoHUD][PresentationDiag]", 1, true) then
                    _diag_messages[#_diag_messages + 1] = msg
                end
                pcall(_diag_orig_log, msg)
            end

            local _current_make = _make_panel_extended
            function _make_panel_extended(name)
                local p = _current_make(name)
                p.bitmap = function(self, opts)
                    return nil
                end
                return p
            end

            kyohud.hud.runtime:mount(managers.hud)
            kyohud.hud.runtime:update(managers.hud, 1.0, 0.05)

            _bn_msg_count = #_diag_messages

            local root = kyohud.hud.assault._root_panel
            _bn_root_hidden = not root:visible()
            _bn_verify_ok = kyohud.hud.assault:_verify_render()
            _bn_no_native = true
            for _, entry in ipairs(kyohud.hud.native_visibility._entries) do
                if entry.owner == "assault" then _bn_no_native = false end
            end
        ''')
        g3 = lua3.globals()
        self.assertEqual(g3._bn_msg_count, 0,
            "bitmap nil: must emit zero diagnostic lines")
        self.assertTrue(g3._bn_root_hidden,
            "bitmap nil: Assault root must be hidden")
        self.assertFalse(g3._bn_verify_ok,
            "bitmap nil: _verify_render must be false")
        self.assertTrue(g3._bn_no_native,
            "bitmap nil: no assault native entries must exist")

        for lua_vm in [lua, lua2, lua3]:
            lua_vm.execute(r'''
                _before_silent = #_diag_messages
                kyohud.hud.runtime:update(managers.hud, 10.0, 0.05)
                kyohud.hud.runtime:update(managers.hud, 11.0, 0.05)
                _after_silent = #_diag_messages
            ''')
            g_vm = lua_vm.globals()
            self.assertEqual(g_vm._after_silent, 0,
                "stable-state must remain silent after initial failure")


if __name__ == "__main__":
    unittest.main()
