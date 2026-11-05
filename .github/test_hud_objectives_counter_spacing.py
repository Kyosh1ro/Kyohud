"""Amount placement follows current title ink, not max history width.

Bug: _compute_layout maximizes title widths across histories and places
amount at layout.text_w. Short current title with amount gets pushed right
by longer history.

Desired: amount left ink edge follows actual fitted current title ink right
edge plus 10*layout.e (allow outward round safety ~1 logical unit).

Test: short current "Branchez les batteries" with amount 1/3, completed
longer history. Assert certification valid, amount visible exact 1/3, and
amount position follows current title (not layout.text_w).
"""
import unittest

from test_hud_objectives_animation import _lua_native_ready_animation


class AmountSpacingAfterCurrentTitleTests(unittest.TestCase):
    """Amount must follow current title ink, not max history width."""

    def test_short_current_amount_follows_current_ink_not_history_width(self):
        """Short current with amount 1/3, longer completed history.

        Assert amount left edge follows current title ink right edge + 10*e,
        not layout.text_w (max width across all slots).
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "animation-ready runtime required")

        lua.execute(r'''
            local O, RT, OM = kyohud.hud.objectives, kyohud.hud.runtime, managers.objectives
            local e = O._layout_cache.e

            kyohud.settings.objectives_visible_limit = 3
            RT:refresh_settings(managers.hud)

            OM:remove_objective("collect")

            local current_title = "Branchez les batteries"
            local history_title = string.rep("Piratez la base de données principale et sécurisez les accès ", 2)

            OM._objectives.history_obj = {
                id = "history_obj",
                text = history_title,
                sub_objectives = {},
            }

            OM._objectives.current_obj = {
                id = "current_obj",
                text = current_title,
                amount = 3,
                current_amount = 1,
                sub_objectives = {},
            }

            OM:activate_objective("history_obj", nil, {delay_presentation = false})
            for i = 1, 15 do
                RT:update(managers.hud, i * 0.1, 0.1)
            end

            OM:complete_objective("history_obj")
            OM:activate_objective("current_obj", nil, {delay_presentation = false})

            for i = 1, 20 do
                RT:update(managers.hud, 1.5 + i * 0.1, 0.1)
            end
            for i = 1, 10 do
                RT:update(managers.hud, 3.5 + i * 0.05, 0.05)
            end

            assert(O:_verify_render(), "render must be certified")

            local slot1 = O._slot_prims[1]
            assert(slot1 and slot1.text and slot1.text:visible(), "current title must exist")
            assert(slot1.text:text() == current_title,
                "current title must be '" .. current_title .. "', got " .. tostring(slot1.text:text()))

            assert(slot1.amount and slot1.amount:visible(), "amount must be visible")
            local amount_text = slot1.amount:text()
            assert(amount_text == "1/3", "amount must be '1/3', got " .. tostring(amount_text))

            local _, _, current_ink_w, _ = slot1.text:text_rect()
            local text_x = slot1.text:x()
            local current_ink_right = text_x + current_ink_w

            local slot2 = O._slot_prims[2]
            assert(slot2 and slot2.text and slot2.text:visible(), "historical primitive must exist and be visible")
            local _, _, hist_ink_w, _ = slot2.text:text_rect()
            assert(hist_ink_w > current_ink_w,
                "history ink width must exceed current ink width: history=" .. hist_ink_w .. " current=" .. current_ink_w)

            local amount_x = slot1.amount:x()

            local desired_amount_x = current_ink_right + 10 * e
            local tolerance = 1.5 * e

            local layout_text_w = O._layout_cache.text_w

            assert(math.abs(amount_x - desired_amount_x) <= tolerance,
                string.format(
                    "amount left edge must follow current title ink + 10*e (not layout.text_w):\n" ..
                    "  current title: '%s' (ink width=%.1f)\n" ..
                    "  history title: '%s' (much longer)\n" ..
                    "  current_ink_right=%.1f\n" ..
                    "  desired amount_x=%.1f (current_ink_right + 10*e)\n" ..
                    "  actual amount_x=%.1f\n" ..
                    "  layout.text_w=%.1f (max width across all slots)\n" ..
                    "  tolerance=%.1f\n" ..
                    "  gap from actual to desired: %.1f\n" ..
                    "  gap from layout.text_w to desired: %.1f",
                    current_title, current_ink_w,
                    history_title,
                    current_ink_right,
                    desired_amount_x,
                    amount_x,
                    layout_text_w,
                    tolerance,
                    math.abs(amount_x - desired_amount_x),
                    math.abs(layout_text_w - desired_amount_x)
                ))

            assert(math.abs(amount_x - layout_text_w) > 20 * e,
                string.format(
                    "amount must NOT be at layout.text_w (max history width):\n" ..
                    "  layout.text_w=%.1f\n" ..
                    "  actual amount_x=%.1f\n" ..
                    "  These are too close (< 20*e), suggesting amount is placed at max width",
                    layout_text_w,
                    amount_x
                ))
        ''')

    def test_short_current_spacing_across_hud_scales(self):
        """Short current with amount 1/3, longer completed history.

        Parameterized at hud_scale 0.95, 1.0, 1.05 with fresh runtime per case.
        At each scale, verify amount left edge follows current title ink right
        edge + 10*layout.e using actual layout.e, exact visible amount 1/3,
        and amount NOT at layout.text_w.
        """
        for scale in (0.95, 1.0, 1.05):
            with self.subTest(scale=scale):
                lua, ok = _lua_native_ready_animation()
                self.assertTrue(ok, "animation-ready runtime required")

                lua.execute('''
                    local O, RT, OM = kyohud.hud.objectives, kyohud.hud.runtime, managers.objectives

                    kyohud.settings.hud_scale = ''' + str(scale) + '''
                    kyohud.settings.objectives_visible_limit = 3
                    RT:refresh_settings(managers.hud)

                    local e = O._layout_cache.e

                    OM:remove_objective("collect")

                    local current_title = "Branchez les batteries"
                    local history_title = string.rep("Piratez la base de donnees principale et securisez les acces ", 2)

                    OM._objectives.history_obj = {
                        id = "history_obj",
                        text = history_title,
                        sub_objectives = {},
                    }

                    OM._objectives.current_obj = {
                        id = "current_obj",
                        text = current_title,
                        amount = 3,
                        current_amount = 1,
                        sub_objectives = {},
                    }

                    OM:activate_objective("history_obj", nil, {delay_presentation = false})
                    for i = 1, 15 do
                        RT:update(managers.hud, i * 0.1, 0.1)
                    end

                    OM:complete_objective("history_obj")
                    OM:activate_objective("current_obj", nil, {delay_presentation = false})

                    for i = 1, 20 do
                        RT:update(managers.hud, 1.5 + i * 0.1, 0.1)
                    end
                    for i = 1, 10 do
                        RT:update(managers.hud, 3.5 + i * 0.05, 0.05)
                    end

                    assert(O:_verify_render(), "render must be certified")

                    local slot1 = O._slot_prims[1]
                    assert(slot1 and slot1.text and slot1.text:visible(), "current title must exist")
                    assert(slot1.text:text() == current_title,
                        "current title text mismatch")

                    local _, _, slot1_ink_w, _ = slot1.text:text_rect()
                    local slot1_font_size = slot1.text:font_size()

                    local slot2 = O._slot_prims[2]
                    assert(slot2 and slot2.text and slot2.text:visible(), "history must be visible")
                    local _, _, slot2_ink_w, _ = slot2.text:text_rect()
                    assert(slot2_ink_w > slot1_ink_w,
                        "visible historical title must measure longer than current: slot2=" ..
                        slot2_ink_w .. " slot1=" .. slot1_ink_w)

                    local parent_w = O._parent_panel:w()
                    local parent_h = O._parent_panel:h()
                    local requested_scale = ''' + str(scale) + '''
                    local expected_e = math.min(parent_w / 1920, parent_h / 1080) * requested_scale
                    assert(math.abs(O._layout_cache.e - expected_e) < 1e-6,
                        string.format(
                            "layout.e must equal min(parent_w/1920, parent_h/1080) * requested_scale:\\n" ..
                            "  parent_w=%.1f parent_h=%.1f requested_scale=%.2f expected_e=%.6f actual_e=%.6f",
                            parent_w, parent_h, requested_scale, expected_e, O._layout_cache.e))

                    local expected_font_size = math.floor(28 * expected_e)
                    assert(slot1_font_size == expected_font_size,
                        string.format(
                            "primitive font_size must equal math.floor(28 * expected_e):\\n" ..
                            "  expected_font_size=%d actual_font_size=%d expected_e=%.6f",
                            expected_font_size, slot1_font_size, expected_e))

                    assert(slot1.amount and slot1.amount:visible(), "amount must be visible")
                    assert(slot1.amount:text() == "1/3", "amount must be exact 1/3")

                    local _, _, current_ink_w, _ = slot1.text:text_rect()
                    local text_x = slot1.text:x()
                    local current_ink_right = text_x + current_ink_w

                    local amount_x = slot1.amount:x()
                    local desired_amount_x = current_ink_right + 10 * e
                    local tolerance = 1.5 * e

                    local layout_text_w = O._layout_cache.text_w

                    assert(math.abs(amount_x - desired_amount_x) <= tolerance,
                        string.format(
                            "amount must follow current ink + 10*e at scale %.2f:\\n" ..
                            "  desired=%.1f actual=%.1f tolerance=%.1f e=%.4f",
                            ''' + str(scale) + ''', desired_amount_x, amount_x, tolerance, e))

                    assert(math.abs(amount_x - layout_text_w) > 20 * e,
                        string.format(
                            "amount must NOT be at layout.text_w at scale %.2f:\\n" ..
                            "  layout.text_w=%.1f actual=%.1f",
                            ''' + str(scale) + ''', layout_text_w, amount_x))
                ''')

    def test_successor_spacing_during_coordinated_slide(self):
        """Successor with amount during coordinated slide.

        Real completion of collect (3 calls), then activate successor with
        amount 2/5. Monotonic clock: hold (1.0,0) -> midpoint slide (2.050,.150)
        -> settled (2.200,.150).

        At midpoint: locate extra pair (text+amount) while visible, assert
        extra amount x follows extra text ink right + 10*e, and render
        certification holds.

        After settled: slot1 has successor with correct spacing. Retained
        primitive identities and history widths not widened by unrelated title.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "animation-ready runtime required")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local RT = r.RT
            local OM = managers.objectives

            kyohud.settings.objectives_visible_limit = 3
            RT:refresh_settings(managers.hud)

            assert(O._mounted and O:_verify_render(), "must be mounted and render")

            local root_identity = O._root_panel
            local slot1_identity = O._slot_prims[1]
            local slot2_identity = O._slot_prims[2]

            local slot1_text_before = slot1_identity.text
            local collect_title_before = slot1_text_before:text()
            local _, _, collect_w_before, _ = slot1_text_before:text_rect()

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            assert(OM._active_objectives["collect"] == nil, "OM must not contain collect")

            OM._objectives["next_obj"] = {
                id = "next_obj", text = "Next objective", amount = 5,
                current_amount = 2, sub_objectives = {},
            }
            OM:activate_objective("next_obj", nil, {delay_presentation = false})

            assert(#O._active == 1 and O._active[1].id == "next_obj", "O._active must have next_obj")

            RT:update(managers.hud, 1.0, 0)
            RT:update(managers.hud, 1.600, 0.600)
            assert(O:_verify_render(), "render must be certified during hold after 1.600")
            RT:update(managers.hud, 1.900, 0.300)

            local extra = O._coordinated_slide_extra
            assert(extra and extra.text, "coordinated slide extra must exist")
            assert(extra.amount, "coordinated slide extra amount must exist")

            RT:update(managers.hud, 2.050, 0.150)

            assert(extra.text:visible() == true, "extra text must be visible at midpoint")
            assert(extra.text:text() == "Next objective",
                "extra text must be Next objective, got " .. tostring(extra.text:text()))

            assert(extra.amount:visible() == true, "extra amount must be visible at midpoint")
            assert(extra.amount:text() == "2/5",
                "extra amount must be 2/5, got " .. tostring(extra.amount:text()))

            local e = O._layout_cache.e
            local _, _, extra_ink_w, _ = extra.text:text_rect()
            local extra_text_x = extra.text:x()
            local extra_ink_right = extra_text_x + extra_ink_w
            local extra_amount_x = extra.amount:x()
            local desired_extra_x = extra_ink_right + 10 * e
            local tolerance = 1.5 * e

            assert(math.abs(extra_amount_x - desired_extra_x) <= tolerance,
                string.format(
                    "extra amount x must follow extra text ink + 10*e at midpoint:\\n" ..
                    "  desired=%.1f actual=%.1f tolerance=%.1f e=%.4f",
                    desired_extra_x, extra_amount_x, tolerance, e))

            assert(O:_verify_render(), "render must be certified at midpoint")

            local vc_mid = 0
            for i = 1, 3 do
                local s = O._slot_prims[i]
                if s and s.text and s.text:visible() and s.text:text() == "Next objective" then
                    vc_mid = vc_mid + 1
                end
            end
            if extra.text:visible() and extra.text:text() == "Next objective" then
                vc_mid = vc_mid + 1
            end
            assert(vc_mid == 1, "REGRESSION: exactly 1 visible Next objective at midpoint, got " .. vc_mid)

            RT:update(managers.hud, 2.200, 0.150)

            local s1 = O._slot_prims[1]
            assert(s1.text:text() == "Next objective", "row1 settled must be Next objective")
            assert(math.abs(s1.text:alpha() - 1) < 0.05, "row1 alpha must be ~1")
            assert(s1.amount:visible() == true, "row1 amount must be visible after settled")
            assert(s1.amount:text() == "2/5", "row1 amount must be 2/5 after settled")

            local _, _, s1_ink_w, _ = s1.text:text_rect()
            local s1_ink_right = s1.text:x() + s1_ink_w
            local s1_amount_x = s1.amount:x()
            local s1_desired_x = s1_ink_right + 10 * e

            assert(math.abs(s1_amount_x - s1_desired_x) <= tolerance,
                string.format(
                    "row1 amount x must follow row1 text ink + 10*e after settled:\\n" ..
                    "  desired=%.1f actual=%.1f",
                    s1_desired_x, s1_amount_x))

            assert(O:_verify_render(), "render must be certified after settled")

            assert(O._root_panel == root_identity, "root_panel identity unchanged")
            assert(O._slot_prims[1] == slot1_identity, "slot1 identity unchanged")
            assert(O._slot_prims[2] == slot2_identity, "slot2 identity unchanged")

            local s2 = O._slot_prims[2]
            assert(s2 and s2.text and s2.text:visible(), "slot2 must be visible after settled")
            assert(s2.text:text() == collect_title_before,
                "slot2 must hold pre-completion collect title '" .. collect_title_before ..
                "', got " .. tostring(s2.text:text()))
            local _, _, slot2_w_after, _ = s2.text:text_rect()
            assert(math.abs(slot2_w_after - collect_w_before) < 0.5,
                "slot2 ink width must match pre-completion collect width: expected=" ..
                collect_w_before .. " actual=" .. slot2_w_after)
        ''')

    def test_counter_x_corruption_and_recovery(self):
        """Counter X corruption via set_shape: certification false, then
        ordinary runtime update repairs same primitive and certification true.

        Set up settled state with current having amount. Corrupt amount
        primitive x position via set_shape (supported fixture method, not
        set_x). Assert _verify_render returns false. Run ordinary RT:update
        to repair. Assert same primitive identity and _verify_render true.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "animation-ready runtime required")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local RT = r.RT
            local OM = managers.objectives

            kyohud.settings.objectives_visible_limit = 3
            RT:refresh_settings(managers.hud)

            assert(O:_verify_render(), "baseline render must be certified")

            local slot1 = O._slot_prims[1]
            local amount_prim = slot1.amount
            assert(amount_prim, "amount primitive must exist")

            local amount_identity = amount_prim

            local orig_x = amount_prim:x()
            local orig_y = amount_prim:y()
            local orig_w = amount_prim:w()
            local orig_h = amount_prim:h()

            amount_prim:set_shape(9999, orig_y, orig_w, orig_h)

            local vr_corrupt = O:_verify_render()
            assert(vr_corrupt == false,
                "_verify_render must be false with corrupted amount x, got " .. tostring(vr_corrupt))

            RT:update(managers.hud, 10.0, 0.1)

            local vr_recover = O:_verify_render()
            assert(vr_recover == true,
                "_verify_render must be true after ordinary RT update repair, got " .. tostring(vr_recover))

            assert(O._slot_prims[1].amount == amount_identity,
                "amount primitive identity must be preserved after repair")

            local recovered_x = O._slot_prims[1].amount:x()
            assert(math.abs(recovered_x - orig_x) < 1.0,
                string.format(
                    "recovered amount x must match original:\\n" ..
                    "  original=%.1f recovered=%.1f",
                    orig_x, recovered_x))
        ''')

    def test_long_fitted_title_bounded_within_root_and_counter(self):
        """Long fitted title bounded within root panel and counter visible.

        Create a very long current title with amount. Verify title is
        fitted/bounded within root_w (text rect width <= text_w), and
        counter/amount remains visible with correct spacing.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "animation-ready runtime required")

        lua.execute('''
            local O, RT, OM = kyohud.hud.objectives, kyohud.hud.runtime, managers.objectives

            kyohud.settings.objectives_visible_limit = 3
            RT:refresh_settings(managers.hud)

            OM:remove_objective("collect")

            local long_title = string.rep("This is a very long objective title that should be fitted within the root panel width ", 3)

            OM._objectives["long_obj"] = {
                id = "long_obj",
                text = long_title,
                amount = 10,
                current_amount = 3,
                sub_objectives = {},
            }
            OM:activate_objective("long_obj", nil, {delay_presentation = false})

            for i = 1, 20 do
                RT:update(managers.hud, i * 0.1, 0.1)
            end
            for i = 1, 10 do
                RT:update(managers.hud, 2.0 + i * 0.05, 0.05)
            end

            assert(O:_verify_render(), "render must be certified with long title")

            local slot1 = O._slot_prims[1]
            assert(slot1 and slot1.text and slot1.text:visible(), "long title must exist and be visible")

            local displayed_title = slot1.text:text()
            assert(displayed_title ~= long_title,
                "long title must be truncated, but displayed matches source")
            assert(string.find(displayed_title, "%.%.%.") or string.find(displayed_title, "…"),
                "truncated title must contain ellipsis, got: " .. displayed_title)

            local text_w = O._layout_cache.text_w
            local _, _, ink_w, _ = slot1.text:text_rect()

            assert(ink_w <= text_w + 1.0,
                string.format(
                    "long title ink width must be bounded within text_w:\\n" ..
                    "  ink_w=%.1f text_w=%.1f",
                    ink_w, text_w))

            assert(slot1.amount and slot1.amount:visible(), "counter must be visible with long title")
            assert(slot1.amount:text() == "3/10", "counter must be exact 3/10")

            local e = O._layout_cache.e
            local root_w = O._layout_cache.root_w
            local amount_x = slot1.amount:x()
            local amount_w = slot1.amount:w()

            assert(amount_x + amount_w <= root_w + 1.0,
                string.format(
                    "counter must be bounded within root_w:\\n" ..
                    "  amount_x=%.1f amount_w=%.1f root_w=%.1f",
                    amount_x, amount_w, root_w))

            local _, _, current_ink_w, _ = slot1.text:text_rect()
            local current_ink_right = slot1.text:x() + current_ink_w
            local desired_amount_x = current_ink_right + 10 * e
            local tolerance = 1.5 * e

            assert(math.abs(amount_x - desired_amount_x) <= tolerance,
                string.format(
                    "counter spacing must follow fitted current ink + 10*e exactly:\\n" ..
                    "  desired=%.1f actual=%.1f tolerance=%.1f e=%.4f gap_left=%.1f",
                    desired_amount_x, amount_x, tolerance, e, amount_x - current_ink_right))
        ''')


if __name__ == "__main__":
    unittest.main()
