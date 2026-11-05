import unittest
from pathlib import Path

import test_hud_assault_states as states

ROOT = Path(__file__).resolve().parents[1]


class AssaultStateTransitionTests(unittest.TestCase):

    def test_sustain_to_fade_crossfade_midpoint_and_settle(self):
        # sustain->fade crossfade 150ms on owned primitives
        lua, ok = states.AssaultMultiStateLabelTests()._make_lua(
            True, "sustain", False, True, False, False
        )
        self.assertTrue(ok, "runtime must mount")

        g = lua.globals()

        lua.execute('''
            _initial_text = kyohud.hud.assault._ticker_a:text()
            _root_identity = tostring(kyohud.hud.assault._root_panel)
            _ticker_a_identity = tostring(kyohud.hud.assault._ticker_a)
        ''')
        initial_text = str(g._initial_text)
        self.assertEqual(initial_text, "MAINTIEN", "initial text must be MAINTIEN")

        # Mutate native phase to fade
        lua.execute('''
            local state = managers.groupai:state()
            state._task_data.assault.phase = "fade"
        ''')

        # Poll triggers refresh then midpoint at 75ms into 150ms fade
        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.0, 0.0)
            A:update(managers.hud, 2.075, 0.075)
        ''')

        # Crossfade: current alpha < 1 at midpoint
        alpha_current = float(lua.eval("kyohud.hud.assault._ticker_a:alpha()"))
        self.assertLess(alpha_current, 1.0,
            "ticker_a alpha must be < 1 at midpoint, got " + str(alpha_current))

        # Outgoing fields must exist
        has_outgoing_a = lua.eval("kyohud.hud.assault._outgoing_ticker_a ~= nil")
        self.assertTrue(has_outgoing_a,
            "_outgoing_ticker_a must exist during crossfade")

        # Outgoing text is old label
        outgoing_text = str(lua.eval("kyohud.hud.assault._outgoing_ticker_a:text()"))
        self.assertEqual(outgoing_text, "MAINTIEN",
            "outgoing text must be MAINTIEN during crossfade")

        # Current text is new label
        current_text = str(lua.eval("kyohud.hud.assault._ticker_a:text()"))
        self.assertEqual(current_text, "RETRAIT",
            "current text must be RETRAIT after phase change")

        # Alphas complementary
        alpha_outgoing = float(lua.eval("kyohud.hud.assault._outgoing_ticker_a:alpha()"))
        self.assertGreaterEqual(alpha_outgoing, 0.0)
        self.assertLessEqual(alpha_outgoing, 1.0)
        self.assertGreaterEqual(alpha_current, 0.0)
        self.assertLessEqual(alpha_current, 1.0)
        alpha_sum = alpha_current + alpha_outgoing
        self.assertAlmostEqual(alpha_sum, 1.0, delta=0.1,
            msg="alpha sum must be ~1.0 at midpoint, got " + str(alpha_sum))

        # Render cert and native acquired
        verify_render = bool(lua.eval("kyohud.hud.assault:_verify_render()"))
        self.assertTrue(verify_render, "_verify_render must be true at midpoint")

        native_acquired = bool(lua.eval("kyohud.hud.assault._native_acquired"))
        self.assertTrue(native_acquired, "_native_acquired must be true at midpoint")

        # Settle past 150ms
        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.16, 0.085)
        ''')

        outgoing_alpha_settled = float(lua.eval(
            "kyohud.hud.assault._outgoing_ticker_a and "
            "kyohud.hud.assault._outgoing_ticker_a:alpha() or 0"
        ))
        outgoing_visible = bool(lua.eval(
            "kyohud.hud.assault._outgoing_ticker_a and "
            "kyohud.hud.assault._outgoing_ticker_a:visible() or false"
        ))
        self.assertTrue(outgoing_alpha_settled == 0 or not outgoing_visible,
            "outgoing must be hidden or alpha=0 after settle")

        alpha_current_settled = float(lua.eval("kyohud.hud.assault._ticker_a:alpha()"))
        self.assertEqual(alpha_current_settled, 1.0,
            "current alpha must be 1.0 after settle")

        lua.execute('''
            _root_identity_after = tostring(kyohud.hud.assault._root_panel)
            _ticker_a_identity_after = tostring(kyohud.hud.assault._ticker_a)
        ''')
        self.assertEqual(str(g._root_identity), str(g._root_identity_after),
            "root identity must be preserved")
        self.assertEqual(str(g._ticker_a_identity), str(g._ticker_a_identity_after),
            "ticker_a identity must be preserved")

    def test_outgoing_corruption_recovery(self):
        # Outgoing corruption detection via _verify_render with exact restore
        lua, ok = states.AssaultMultiStateLabelTests()._make_lua(
            True, "sustain", False, True, False, False
        )
        self.assertTrue(ok, "runtime must mount")

        # Setup crossfade midpoint
        lua.execute('''
            local state = managers.groupai:state()
            state._task_data.assault.phase = "fade"
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.0, 0.0)
            A:update(managers.hud, 2.075, 0.075)
        ''')

        # Require outgoing exists before any corruption
        lua.execute('''
            _out_a = kyohud.hud.assault._outgoing_ticker_a
            assert(_out_a ~= nil, "outgoing must exist at midpoint")
            _cap_text = _out_a:text()
            _cap_alpha = _out_a:alpha()
            _cap_x = _out_a:x()
            _cap_identity = tostring(_out_a)
        ''')
        g = lua.globals()
        self.assertTrue(bool(lua.eval("_out_a ~= nil")),
            "outgoing_ticker_a must exist at midpoint")

        # Positive cert baseline
        verify_before = bool(lua.eval("kyohud.hud.assault:_verify_render()"))
        self.assertTrue(verify_before, "must have positive cert before corruption")

        # --- text corruption ---
        lua.execute("_out_a:set_text('CORRUPTED_TEXT')")
        verify_after_text = bool(lua.eval("kyohud.hud.assault:_verify_render()"))
        self.assertFalse(verify_after_text,
            "_verify_render must be false after outgoing text corruption")

        # Restore captured text
        lua.execute("_out_a:set_text(_cap_text)")
        self.assertEqual(str(lua.eval("_out_a:text()")), str(g._cap_text),
            "restored text must match captured")
        verify_after_text_restore = bool(lua.eval("kyohud.hud.assault:_verify_render()"))
        self.assertTrue(verify_after_text_restore,
            "_verify_render must recover after text restore")

        # --- alpha corruption ---
        lua.execute("_out_a:set_alpha(2.0)")
        verify_after_alpha = bool(lua.eval("kyohud.hud.assault:_verify_render()"))
        self.assertFalse(verify_after_alpha,
            "_verify_render must be false after outgoing alpha corruption")

        # Restore captured alpha
        lua.execute("_out_a:set_alpha(_cap_alpha)")
        self.assertAlmostEqual(float(lua.eval("_out_a:alpha()")), float(g._cap_alpha), delta=0.01,
            msg="restored alpha must match captured")
        verify_after_alpha_restore = bool(lua.eval("kyohud.hud.assault:_verify_render()"))
        self.assertTrue(verify_after_alpha_restore,
            "_verify_render must recover after alpha restore")

        # --- x corruption ---
        lua.execute("_out_a:set_x(9999)")
        verify_after_x = bool(lua.eval("kyohud.hud.assault:_verify_render()"))
        self.assertFalse(verify_after_x,
            "_verify_render must be false after outgoing x corruption")

        # Restore captured x (not arbitrary 0)
        lua.execute("_out_a:set_x(_cap_x)")
        self.assertAlmostEqual(float(lua.eval("_out_a:x()")), float(g._cap_x), delta=0.01,
            msg="restored x must match captured")
        verify_after_x_restore = bool(lua.eval("kyohud.hud.assault:_verify_render()"))
        self.assertTrue(verify_after_x_restore,
            "_verify_render must recover after x restore")

        # Identity preserved throughout
        self.assertEqual(str(lua.eval("tostring(_out_a)")), str(g._cap_identity),
            "outgoing identity must be preserved")

    def test_pnr_preemption_during_fade(self):
        # PNR preemption during fade disables root and outgoing
        lua, ok = states.AssaultMultiStateLabelTests()._make_lua(
            True, "sustain", False, True, False, False
        )
        self.assertTrue(ok, "runtime must mount")

        # Setup crossfade midpoint
        lua.execute('''
            local state = managers.groupai:state()
            state._task_data.assault.phase = "fade"
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.0, 0.0)
            A:update(managers.hud, 2.075, 0.075)
        ''')

        # Require outgoing exists and is visible at midpoint before preemption
        outgoing_exists = bool(lua.eval(
            "kyohud.hud.assault._outgoing_ticker_a ~= nil"
        ))
        self.assertTrue(outgoing_exists,
            "outgoing_ticker_a must exist at midpoint")
        outgoing_visible_before = bool(lua.eval(
            "kyohud.hud.assault._outgoing_ticker_a:visible()"
        ))
        self.assertTrue(outgoing_visible_before,
            "outgoing must be visible at midpoint before preemption")

        # PNR preemption
        lua.execute('''
            local corner = managers.hud._hud_assault_corner
            corner._point_of_no_return = true
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.1, 0.025)
        ''')

        # Root and native disabled
        root_visible = bool(lua.eval("kyohud.hud.assault._root_panel:visible()"))
        self.assertFalse(root_visible,
            "root must be invisible after PNR preemption")

        native_acquired = bool(lua.eval("kyohud.hud.assault._native_acquired"))
        self.assertFalse(native_acquired,
            "_native_acquired must be false after PNR preemption")

        # Outgoing disabled (unconditional since we required existence+visibility)
        outgoing_visible = bool(lua.eval(
            "kyohud.hud.assault._outgoing_ticker_a:visible()"
        ))
        self.assertFalse(outgoing_visible,
            "outgoing must be disabled after PNR preemption")

        # Fresh source recovery
        lua.execute('''
            local corner = managers.hud._hud_assault_corner
            corner._point_of_no_return = false
            local state = managers.groupai:state()
            state._task_data.assault.phase = "sustain"
            local A = kyohud.hud.assault
            A:update(managers.hud, 3.0, 0.0)
            A:update(managers.hud, 3.5, 0.05)
        ''')

        verify_recovered = bool(lua.eval("kyohud.hud.assault:_verify_render()"))
        self.assertTrue(verify_recovered,
            "cert must recover after fresh source")

    def test_after_assault_brief(self):
        # After-assault 1.5s visibility window, client generic active
        lua, ok = states.AssaultMultiStateLabelTests()._make_lua(
            False, "sustain", False, True, False, True
        )
        self.assertTrue(ok, "runtime must mount")

        # Extend loc map with after-assault key
        lua.execute('''
            local _loc_map = {
                ky_hud_assault_status = "ASSAULT",
                ky_hud_assault_endless = "ENDLESS",
                ky_hud_assault_preparation = "PREPARATION",
                ky_hud_assault_build = "MONTEE",
                ky_hud_assault_sustain = "MAINTIEN",
                ky_hud_assault_fade = "RETRAIT",
                ky_hud_assault_after = "AFTER ASSAULT",
            }
            function managers.localization:text(key)
                return _loc_map[key] or ("LOC:" .. tostring(key))
            end
        ''')

        # sync_end_assault triggers window
        lua.execute("managers.hud:sync_end_assault(1)")

        # t=2.0: label and root visible
        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.0, 0.01)
        ''')

        label = str(lua.eval("kyohud.hud.assault:_resolve_status_label()"))
        self.assertEqual(label, "AFTER ASSAULT",
            "label must be AFTER ASSAULT, got " + label)

        root_visible = bool(lua.eval("kyohud.hud.assault._root_panel:visible()"))
        self.assertTrue(root_visible, "root must be visible at t=2.0")

        # t=2.8 within 1.5s window
        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.8, 0.8)
        ''')
        root_still_visible = bool(lua.eval("kyohud.hud.assault._root_panel:visible()"))
        self.assertTrue(root_still_visible, "root must still be visible at t=2.8")

        # t=3.6 beyond 1.5s window
        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 3.6, 0.8)
        ''')

        root_hidden = not bool(lua.eval("kyohud.hud.assault._root_panel:visible()"))
        self.assertFalse(root_hidden, "known end must persist as lull at t=3.6")
        self.assertEqual(lua.eval("kyohud.hud.assault:_resolve_status_label()"), "LULL")

        native_restored = not bool(lua.eval("kyohud.hud.assault._native_acquired"))
        self.assertFalse(native_restored, "lull replacement retains exact native ownership")

    def test_outgoing_verification_completeness(self):
        lua, ok = states.AssaultMultiStateLabelTests()._make_lua(
            True, "sustain", False, True, False, False
        )
        self.assertTrue(ok, "runtime must mount")

        lua.execute("_parent = _make_panel_extended('substitute_parent')")

        lua.execute('''
            local state = managers.groupai:state()
            state._task_data.assault.phase = "fade"
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.0, 0.0)
            A:update(managers.hud, 2.075, 0.075)
        ''')

        self.assertTrue(bool(lua.eval("kyohud.hud.assault._outgoing_ticker_a ~= nil")),
            "outgoing_a must exist at midpoint")
        self.assertTrue(bool(lua.eval("kyohud.hud.assault._outgoing_ticker_b ~= nil")),
            "outgoing_b must exist at midpoint")
        self.assertTrue(bool(lua.eval("kyohud.hud.assault:_verify_render()")),
            "positive cert baseline at midpoint")

        lua.execute('''
            _results = {}
            _ri = 0
            local function rec(v) _ri = _ri + 1; _results[_ri] = v end
            local A = kyohud.hud.assault
            local outs = {A._outgoing_ticker_a, A._outgoing_ticker_b}
            for oi, out in ipairs(outs) do
                local cy = out:y()
                out:set_y(cy + 20)
                rec(A:_verify_render())
                out:set_y(cy)
                rec(A:_verify_render())

                local cx, cw, ch = out:x(), out:w(), out:h()
                out:set_shape(cx, out:y(), cw + 20, ch)
                rec(A:_verify_render())
                out:set_shape(cx, out:y(), cw, ch)
                rec(A:_verify_render())

                cx, cy, ch = out:x(), out:y(), out:h()
                local cw2 = out:w()
                out:set_shape(cx, cy, cw2, ch + 20)
                rec(A:_verify_render())
                out:set_shape(cx, cy, cw2, ch)
                rec(A:_verify_render())

                local cl = out:layer()
                out:set_layer(cl + 5)
                rec(A:_verify_render())
                out:set_layer(cl)
                rec(A:_verify_render())

                local cfs = out:font_size()
                out:set_font_size(cfs + 5)
                rec(A:_verify_render())
                out:set_font_size(cfs)
                rec(A:_verify_render())

                local cp = out:parent()
                out._parent = _parent
                rec(A:_verify_render())
                out._parent = cp
                rec(A:_verify_render())
            end
        ''')

        n = int(lua.eval("#_results"))
        self.assertEqual(n, 24,
            "2 outgoings * 6 fields * 2 (mutated+restored) = 24")

        fields = ["y", "w", "h", "layer", "font_size", "parent"]
        for oi in range(2):
            for fi, fname in enumerate(fields):
                idx_false = oi * 12 + fi * 2 + 1
                idx_true = idx_false + 1
                val_false = bool(lua.eval(f"_results[{idx_false}]"))
                val_true = bool(lua.eval(f"_results[{idx_true}]"))
                self.assertFalse(val_false,
                    f"outgoing[{oi}] {fname} mutation must cause"
                    f" _verify_render false")
                self.assertTrue(val_true,
                    f"outgoing[{oi}] {fname} restore must recover"
                    f" _verify_render true")

        lua.execute('''
            _orig_alpha_fn = kyohud.hud.assault._ticker_a.alpha
            kyohud.hud.assault._ticker_a.alpha = function() return 0.9 end
            _alpha_override = kyohud.hud.assault:_verify_render()
            kyohud.hud.assault._ticker_a.alpha = _orig_alpha_fn
            _alpha_restored = kyohud.hud.assault:_verify_render()
        ''')

        self.assertFalse(bool(lua.eval("_alpha_override")),
            "_verify_render must be false when current alpha getter"
            " returns 0.9 while color is preserved")
        self.assertTrue(bool(lua.eval("_alpha_restored")),
            "_verify_render must recover after alpha getter restore")

    def test_after_assault_source_replacement_and_duplicate_sync_end(self):
        lua, ok = states.AssaultMultiStateLabelTests()._make_lua(
            True, "sustain", False, True, False, False
        )
        self.assertTrue(ok, "runtime must mount")

        lua.execute('''
            local _loc_map = {
                ky_hud_assault_status = "ASSAULT",
                ky_hud_assault_endless = "ENDLESS",
                ky_hud_assault_preparation = "PREPARATION",
                ky_hud_assault_build = "MONTEE",
                ky_hud_assault_sustain = "MAINTIEN",
                ky_hud_assault_fade = "RETRAIT",
                ky_hud_assault_after = "AFTER ASSAULT",
            }
            function managers.localization:text(key)
                return _loc_map[key] or ("LOC:" .. tostring(key))
            end
        ''')

        lua.execute('''
            managers.groupai:state()._task_data.assault.active = false
            managers.groupai:state()._assault_mode = false
        ''')
        lua.execute("managers.hud:sync_end_assault(1)")
        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.0, 0.01)
        ''')

        self.assertTrue(bool(lua.eval("kyohud.hud.assault._after_assault_active")),
            "after_assault must be active after sync_end + update")
        label = str(lua.eval("kyohud.hud.assault:_resolve_status_label()"))
        self.assertEqual(label, "AFTER ASSAULT")
        root_visible = bool(lua.eval("kyohud.hud.assault._root_panel:visible()"))
        self.assertTrue(root_visible, "root must be visible during after_assault")

        lua.execute('''
            managers.groupai._state = GroupAIState:new()
            managers.groupai._state._is_server = true
            managers.groupai._state._assault_mode = false
            managers.groupai._state._task_data = {assault = {active = false}}
            managers.groupai._state._hostage_count = 0
            managers.groupai._state._converted = {}
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.6, 0.05)
        ''')

        root_after = bool(lua.eval("kyohud.hud.assault._root_panel:visible()"))
        after_active = bool(lua.eval("kyohud.hud.assault._after_assault_active"))
        self.assertFalse(root_after,
            "RED: root must be hidden after source replacement during after_assault")
        self.assertFalse(after_active,
            "RED: after_assault must be cleared after source replacement")

        lua2, ok2 = states.AssaultMultiStateLabelTests()._make_lua(
            True, "sustain", False, True, False, False
        )
        self.assertTrue(ok2, "runtime must mount")

        lua2.execute('''
            local _loc_map = {
                ky_hud_assault_status = "ASSAULT",
                ky_hud_assault_endless = "ENDLESS",
                ky_hud_assault_preparation = "PREPARATION",
                ky_hud_assault_build = "MONTEE",
                ky_hud_assault_sustain = "MAINTIEN",
                ky_hud_assault_fade = "RETRAIT",
                ky_hud_assault_after = "AFTER ASSAULT",
            }
            function managers.localization:text(key)
                return _loc_map[key] or ("LOC:" .. tostring(key))
            end
        ''')

        lua2.execute('''
            managers.groupai:state()._task_data.assault.active = false
            managers.groupai:state()._assault_mode = false
        ''')
        lua2.execute("managers.hud:sync_end_assault(1)")
        lua2.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.0, 0.01)
        ''')

        self.assertTrue(bool(lua2.eval("kyohud.hud.assault._after_assault_active")),
            "after_assault must be active before duplicate sync_end")
        label_before = str(lua2.eval("kyohud.hud.assault:_resolve_status_label()"))
        self.assertEqual(label_before, "AFTER ASSAULT")
        start_before = float(lua2.eval("kyohud.hud.assault._after_assault_start"))

        lua2.execute("managers.hud:sync_end_assault(0)")
        lua2.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.5, 0.01)
        ''')

        after_dup = bool(lua2.eval("kyohud.hud.assault._after_assault_active"))
        label_dup = str(lua2.eval("kyohud.hud.assault:_resolve_status_label()"))
        self.assertTrue(after_dup,
            "RED: duplicate sync_end must not cancel after_assault window")
        self.assertEqual(label_dup, "AFTER ASSAULT",
            "RED: label must remain AFTER ASSAULT after duplicate sync_end")
        start_after = float(lua2.eval("kyohud.hud.assault._after_assault_start"))
        self.assertAlmostEqual(start_after, start_before, delta=0.001,
            msg="RED: duplicate sync_end must not restart after_assault window")

        lua2.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 3.6, 0.05)
        ''')

        root_hidden = not bool(lua2.eval("kyohud.hud.assault._root_panel:visible()"))
        self.assertFalse(root_hidden,
            "known end must persist after original window expiry at t=3.6")
        self.assertFalse(bool(lua2.eval("kyohud.hud.assault._after_assault_active")))
        self.assertEqual(lua2.eval("kyohud.hud.assault:_resolve_status_label()"), "LULL")

    def test_outgoing_a_alpha_drift_on_fresh_transition(self):
        lua, ok = states.AssaultMultiStateLabelTests()._make_lua(
            True, "sustain", False, True, False, False
        )
        self.assertTrue(ok, "runtime must mount")

        lua.execute('''
            local state = managers.groupai:state()
            state._task_data.assault.phase = "fade"
        ''')

        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 2, 0)
            A:update(managers.hud, 2.1486, 0.1486)
            A:update(managers.hud, 2.16, 0.0114)
        ''')

        lua.execute('''
            _fade_out_a = kyohud.hud.assault._outgoing_ticker_a
            _fade_out_b = kyohud.hud.assault._outgoing_ticker_b
            assert(_fade_out_a ~= nil, "outgoing_a must exist after fade")
            assert(_fade_out_b ~= nil, "outgoing_b must exist after fade")
            _fade_out_a_id = tostring(_fade_out_a)
            _fade_out_b_id = tostring(_fade_out_b)
            _fade_out_a_alpha = _fade_out_a:alpha()
            _fade_out_b_alpha = _fade_out_b:alpha()
        ''')
        g = lua.globals()

        residue_a = float(g._fade_out_a_alpha)
        residue_b = float(g._fade_out_b_alpha)
        self.assertGreater(residue_a, 0,
            "outgoing_a must have small positive residue alpha, got "
            + str(residue_a))
        self.assertLess(residue_a, 0.1,
            "outgoing_a residue must be small positive, got " + str(residue_a))
        self.assertGreater(residue_b, 0,
            "outgoing_b must have small positive residue alpha, got "
            + str(residue_b))
        self.assertLess(residue_b, 0.1,
            "outgoing_b residue must be small positive, got " + str(residue_b))

        lua.execute('''
            if _fade_out_a then
                _fade_out_a.set_color = function(self, c)
                    if c then
                        self._color = {r=c.r, g=c.g, b=c.b, a=self._alpha,
                            [1]=c.r, [2]=c.g, [3]=c.b, [4]=self._alpha}
                    end
                end
            end
            if _fade_out_b then
                _fade_out_b.set_color = function(self, c)
                    if c then
                        self._color = {r=c.r, g=c.g, b=c.b, a=self._alpha,
                            [1]=c.r, [2]=c.g, [3]=c.b, [4]=self._alpha}
                    end
                end
            end
        ''')

        lua.execute('''
            managers.groupai:state()._task_data.assault.phase = "build"
            local A = kyohud.hud.assault
            A:update(managers.hud, 3, 0)
        ''')

        lua.execute('''
            _new_out_a_id = tostring(kyohud.hud.assault._outgoing_ticker_a)
            _new_out_b_id = tostring(kyohud.hud.assault._outgoing_ticker_b)
            _new_out_a_alpha = kyohud.hud.assault._outgoing_ticker_a
                and kyohud.hud.assault._outgoing_ticker_a:alpha() or -1
            _new_out_b_alpha = kyohud.hud.assault._outgoing_ticker_b
                and kyohud.hud.assault._outgoing_ticker_b:alpha() or -1
            _fresh_root_vis = kyohud.hud.assault._root_panel:visible()
            _fresh_verify = kyohud.hud.assault:_verify_render()
            _fresh_native = kyohud.hud.assault._native_acquired
        ''')

        self.assertEqual(str(g._fade_out_a_id), str(g._new_out_a_id),
            "outgoing_a identity must be preserved into build transition")
        self.assertEqual(str(g._fade_out_b_id), str(g._new_out_b_id),
            "outgoing_b identity must be preserved into build transition")

        new_alpha_a = float(g._new_out_a_alpha)
        new_alpha_b = float(g._new_out_b_alpha)
        self.assertAlmostEqual(new_alpha_a, 1.0, delta=0.01,
            msg="SOL: outgoing_a alpha must be 1 at fresh transition start,"
            " got " + str(new_alpha_a))
        self.assertAlmostEqual(new_alpha_b, 1.0, delta=0.01,
            msg="SOL: outgoing_b alpha must be 1 at fresh transition start,"
            " got " + str(new_alpha_b))
        self.assertTrue(bool(g._fresh_root_vis),
            "root must be visible at fresh transition start")
        self.assertTrue(bool(g._fresh_verify),
            "_verify_render must be true at fresh transition start")
        self.assertTrue(bool(g._fresh_native),
            "_native_acquired must be true at fresh transition start")

        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 3.075, 0.075)
        ''')

        mid_out_a = float(lua.eval(
            "kyohud.hud.assault._outgoing_ticker_a:alpha()"))
        mid_cur_a = float(lua.eval(
            "kyohud.hud.assault._ticker_a:alpha()"))
        self.assertAlmostEqual(mid_out_a, 0.5, delta=0.1,
            msg="outgoing_a alpha at midpoint, got " + str(mid_out_a))
        self.assertAlmostEqual(mid_cur_a, 0.5, delta=0.1,
            msg="current alpha at midpoint, got " + str(mid_cur_a))
        self.assertTrue(bool(lua.eval("kyohud.hud.assault:_verify_render()")),
            "cert must be true at midpoint")

        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 3.16, 0.085)
        ''')

        self.assertTrue(bool(lua.eval("kyohud.hud.assault:_verify_render()")),
            "cert must be true after settle")
        self.assertEqual(
            str(lua.eval("tostring(kyohud.hud.assault._outgoing_ticker_a)")),
            str(g._fade_out_a_id),
            "outgoing_a identity must be retained after settle")
        self.assertEqual(
            str(lua.eval("tostring(kyohud.hud.assault._outgoing_ticker_b)")),
            str(g._fade_out_b_id),
            "outgoing_b identity must be retained after settle")

    def test_client_preparation_to_assault_crossfade(self):
        lua, ok = states.AssaultMultiStateLabelTests()._make_lua(
            False, "sustain", False, False, True, False
        )
        self.assertTrue(ok, "runtime must mount")

        label = str(lua.eval("kyohud.hud.assault:_resolve_status_label()"))
        self.assertEqual(label, "PREPARATION",
            "initial label must be PREPARATION with client anticipation")

        ticker_text = str(lua.eval("kyohud.hud.assault._ticker_a:text()"))
        self.assertTrue(ticker_text.startswith("PREPARATION"),
            "ticker must start with PREPARATION, got " + ticker_text)

        self.assertTrue(bool(lua.eval("kyohud.hud.assault:_verify_render()")),
            "positive cert baseline for PREPARATION")

        lua.execute("managers.hud:sync_start_assault(1)")
        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.0, 0.0)
            A:update(managers.hud, 2.075, 0.075)
        ''')

        label_after = str(lua.eval("kyohud.hud.assault:_resolve_status_label()"))
        self.assertEqual(label_after, "ASSAULT",
            "label must be ASSAULT after sync_start_assault")

        alpha_current = float(lua.eval("kyohud.hud.assault._ticker_a:alpha()"))
        self.assertLess(alpha_current, 1.0,
            "RED: current alpha must be < 1 at midpoint of"
            " PREPARATION->ASSAULT crossfade, got " + str(alpha_current))

        has_outgoing = bool(lua.eval(
            "kyohud.hud.assault._outgoing_ticker_a ~= nil"))
        self.assertTrue(has_outgoing,
            "RED: outgoing must exist during PREPARATION->ASSAULT crossfade")

        outgoing_text = str(lua.eval(
            "kyohud.hud.assault._outgoing_ticker_a:text()"))
        self.assertEqual(outgoing_text, "PREPARATION",
            "outgoing text must be PREPARATION")

        lua.execute('''
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.2, 0.125)
        ''')

        alpha_settled = float(lua.eval("kyohud.hud.assault._ticker_a:alpha()"))
        self.assertEqual(alpha_settled, 1.0,
            "current alpha must be 1.0 after settle")

        verify_settled = bool(lua.eval("kyohud.hud.assault:_verify_render()"))
        self.assertTrue(verify_settled,
            "_verify_render must be true after settle")


if __name__ == "__main__":
    unittest.main()
