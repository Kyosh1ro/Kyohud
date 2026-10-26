"""LOT3a -- objectives completion continuity animation (RED state).

Tests the NEW desired contract for completion animation with limit 3:
- NO MORE PULSES
- Completed current stays alpha 1 with stable Mission cyan RGB .52,.88,.92 for .900s
- Then coordinated .300s smooth slide:
  - completed current down to historical row1 at alpha .45
  - existing history down one rank continuously
  - only oldest fades out
  - next current enters top

Establishes history through actual OM completion + runtime updates, then
completes next current and activates successor. Asserts authoritative registry
immediate. Locates titles across owned primitives by identity/text, not fixed
slot index during transition. Asserts previous history remains visible alpha>0
at .150, .450, .899 and at slide midpoint 1.050. Midpoint y must lie strictly
between old and destination y for completed and previous historical row.

No test-side production state mutation, no conditional skipping, no copied
feature implementation. Separate stable cyan test ensures actual visibility
disappearance RED is independently observable.

Reuses _lua_native_ready_animation from test_hud_objectives_animation.
"""
import unittest

from test_hud_objectives_animation import _lua_native_ready_animation


class ObjectivesContinuityTests(unittest.TestCase):
    """Bounded behavioral tests for completion continuity animation."""

    def test_completion_continuous_slide_limit_3(self):
        """ONE transition with limit 3: established history [collect, B],
        complete C (successor to B), activate D.

        Phase 1 (0 to .900s): C stable alpha 1, no pulse
        Phase 2 (.900 to 1.200s): coordinated smooth slide
          - C slides down to history row1 (row2), alpha .45
          - B slides down one rank (row2 to row3), alpha .45
          - collect (oldest, row3) fades out
          - D enters top (row1)
        After slide: D at row1, C at row2 (history .45), B at row3 (history .45)

        Locates primitives by text identity, not slot index. Asserts previous
        history remains visible alpha>0 at .150, .450, .899 and midpoint 1.050.
        Midpoint y strictly between old and destination y for C and B.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local RT = r.RT
            local OM = managers.objectives

            kyohud.settings.objectives_visible_limit = 3
            RT:refresh_settings(managers.hud)

            local function find_prim_by_text(text)
                for i = 1, 3 do
                    local s = O._slot_prims[i]
                    if s and s.text and s.text:text() == text then
                        return s.text, i
                    end
                end
                return nil, nil
            end

            local t = 0

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            OM._objectives["B"] = {id="B", text="Objective B", sub_objectives={}}
            OM:activate_objective("B", nil, {delay_presentation = false})
            for i = 1, 20 do
                t = t + 0.1
                RT:update(managers.hud, t, 0.1)
            end

            OM:complete_objective("B")

            OM._objectives["C"] = {id="C", text="Objective C", sub_objectives={}}
            OM:activate_objective("C", nil, {delay_presentation = false})
            for i = 1, 20 do
                t = t + 0.1
                RT:update(managers.hud, t, 0.1)
            end

            OM:complete_objective("C")
            assert(OM._active_objectives["C"] == nil,
                "REGISTRY: C must be absent immediately after completion")
            assert(#O._active == 0,
                "O._active must be empty after completion")

            OM._objectives["D"] = {id="D", text="Objective D", sub_objectives={}}
            OM:activate_objective("D", nil, {delay_presentation = false})
            assert(OM._active_objectives["D"] ~= nil,
                "D must be in registry after activation")

            local C_prim, C_slot = find_prim_by_text("Objective C")
            assert(C_prim, "Objective C primitive must exist after completion")

            local B_prim, B_slot = find_prim_by_text("Objective B")
            assert(B_prim, "Objective B primitive must exist (history1)")

            local collect_prim, collect_slot = find_prim_by_text("Collect bags")
            assert(collect_prim, "Collect bags primitive must exist (history2)")

            local C_y_before = C_prim:y()
            local B_y_before = B_prim:y()
            local collect_y_before = collect_prim:y()

            local ly = O._layout_cache
            assert(ly, "layout cache must exist")
            local row_h = ly.row_h

            t = t + 0.1
            RT:update(managers.hud, t, 0)

            assert(C_prim:visible() == true,
                "C must be visible at t=0")
            assert(math.abs(C_prim:alpha() - 1.0) < 0.01,
                "C alpha must be 1.0 at t=0, got " .. tostring(C_prim:alpha()))

            t = t + 0.150
            RT:update(managers.hud, t, 0.150)

            assert(C_prim:visible() == true,
                "C must be visible at t=.150")
            assert(math.abs(C_prim:alpha() - 1.0) < 0.01,
                "C alpha must be 1.0 at t=.150, got " .. tostring(C_prim:alpha()))
            assert(B_prim:visible() == true,
                "B must be visible at t=.150")
            assert(B_prim:alpha() > 0,
                "B alpha must be > 0 at t=.150, got " .. tostring(B_prim:alpha()))
            assert(collect_prim:visible() == true,
                "collect must be visible at t=.150")
            assert(collect_prim:alpha() > 0,
                "collect alpha must be > 0 at t=.150, got " .. tostring(collect_prim:alpha()))

            t = t + 0.300
            RT:update(managers.hud, t, 0.300)

            assert(C_prim:visible() == true,
                "C must be visible at t=.450")
            assert(math.abs(C_prim:alpha() - 1.0) < 0.01,
                "C alpha must be 1.0 at t=.450, got " .. tostring(C_prim:alpha()))
            assert(B_prim:visible() == true,
                "B must be visible at t=.450")
            assert(B_prim:alpha() > 0,
                "B alpha must be > 0 at t=.450")
            assert(collect_prim:visible() == true,
                "collect must be visible at t=.450")
            assert(collect_prim:alpha() > 0,
                "collect alpha must be > 0 at t=.450")

            t = t + 0.449
            RT:update(managers.hud, t, 0.449)

            assert(C_prim:visible() == true,
                "C must be visible at t=.899")
            assert(math.abs(C_prim:alpha() - 1.0) < 0.01,
                "C alpha must be 1.0 at t=.899, got " .. tostring(C_prim:alpha()))
            assert(B_prim:visible() == true,
                "B must be visible at t=.899")
            assert(B_prim:alpha() > 0,
                "B alpha must be > 0 at t=.899")
            assert(collect_prim:visible() == true,
                "collect must be visible at t=.899")
            assert(collect_prim:alpha() > 0,
                "collect alpha must be > 0 at t=.899")

            t = t + 0.150
            RT:update(managers.hud, t, 0.150)

            local C_y_mid = C_prim:y()
            local B_y_mid = B_prim:y()

            assert(C_y_mid > C_y_before,
                "C y must have increased (sliding down), before=" .. tostring(C_y_before) .. " mid=" .. tostring(C_y_mid))
            assert(C_y_mid < C_y_before + row_h,
                "C y at midpoint must be < destination (old + row_h), mid=" .. tostring(C_y_mid) .. " dest=" .. tostring(C_y_before + row_h))

            assert(B_y_mid > B_y_before,
                "B y must have increased (sliding down), before=" .. tostring(B_y_before) .. " mid=" .. tostring(B_y_mid))
            assert(B_y_mid < B_y_before + row_h,
                "B y at midpoint must be < destination (old + row_h), mid=" .. tostring(B_y_mid) .. " dest=" .. tostring(B_y_before + row_h))

            assert(C_prim:alpha() > 0,
                "C alpha must be > 0 at midpoint, got " .. tostring(C_prim:alpha()))
            assert(B_prim:alpha() > 0,
                "B alpha must be > 0 at midpoint, got " .. tostring(B_prim:alpha()))

            for i = 1, 20 do
                t = t + 0.1
                RT:update(managers.hud, t, 0.1)
            end

            local D_prim, D_slot = find_prim_by_text("Objective D")
            assert(D_prim, "Objective D primitive must exist after slide")
            assert(D_prim:visible() == true,
                "D must be visible")
            assert(math.abs(D_prim:alpha() - 1.0) < 0.05,
                "D alpha must be ~1.0, got " .. tostring(D_prim:alpha()))

            local C_prim_after, C_slot_after = find_prim_by_text("Objective C")
            assert(C_prim_after, "Objective C primitive must exist (history)")
            assert(C_prim_after:visible() == true,
                "C must be visible (history)")
            assert(math.abs(C_prim_after:alpha() - 0.45) < 0.05,
                "C alpha must be ~0.45 (history), got " .. tostring(C_prim_after:alpha()))

            local B_prim_after, B_slot_after = find_prim_by_text("Objective B")
            assert(B_prim_after, "Objective B primitive must exist (history)")
            assert(B_prim_after:visible() == true,
                "B must be visible (history)")
            assert(math.abs(B_prim_after:alpha() - 0.45) < 0.05,
                "B alpha must be ~0.45 (history), got " .. tostring(B_prim_after:alpha()))

            local collect_prim_after, collect_slot_after = find_prim_by_text("Collect bags")
            local collect_gone = true
            if collect_prim_after and collect_prim_after:visible() and collect_prim_after:text() ~= "" then
                collect_gone = false
            end
            assert(collect_gone,
                "collect must be invisible/empty (oldest, faded out)")
        ''')

    def test_completed_current_stable_cyan_color(self):
        """Separate test: completed current displays stable Mission cyan RGB .52,.88,.92.

        This test verifies the color is actually set, not just alpha.
        If color is not set, this will RED independently of visibility issues.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local RT = r.RT
            local OM = managers.objectives

            local function find_prim_by_text(text)
                for i = 1, 3 do
                    local s = O._slot_prims[i]
                    if s and s.text and s.text:text() == text then
                        return s.text, i
                    end
                end
                return nil, nil
            end

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            local C_prim = find_prim_by_text("Collect bags")
            assert(C_prim, "Collect bags primitive must exist after completion")

            RT:update(managers.hud, 1.0, 0)

            assert(C_prim:visible() == true,
                "C must be visible at t=0")

            local c = C_prim:color()
            assert(c, "color must not be nil")
            assert(type(c) == "table", "color must be a table, got " .. type(c))

            local r_val = c[2]
            local g_val = c[3]
            local b_val = c[4]

            assert(math.abs(r_val - 0.52) < 0.01,
                "RED channel must be ~0.52, got " .. tostring(r_val))
            assert(math.abs(g_val - 0.88) < 0.01,
                "GREEN channel must be ~0.88, got " .. tostring(g_val))
            assert(math.abs(b_val - 0.92) < 0.01,
                "BLUE channel must be ~0.92, got " .. tostring(b_val))

            RT:update(managers.hud, 1.450, 0.450)

            local c2 = C_prim:color()
            local r2 = c2[2]
            local g2 = c2[3]
            local b2 = c2[4]

            assert(math.abs(r2 - 0.52) < 0.01,
                "RED channel must remain ~0.52 at t=.450, got " .. tostring(r2))
            assert(math.abs(g2 - 0.88) < 0.01,
                "GREEN channel must remain ~0.88 at t=.450, got " .. tostring(g2))
            assert(math.abs(b2 - 0.92) < 0.01,
                "BLUE channel must remain ~0.92 at t=.450, got " .. tostring(b2))
        ''')


    def test_bounded_no_current_all_hidden_after_animation(self):
        """Bounded no-current case: complete the only objective with no successor.

        After completion animation (stable .900 + exit .300 = 1.200s), all owned
        slot texts must be empty/hidden. History retains collect for future use.
        No production state mutation. Registry absent immediately.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local RT = r.RT
            local OM = managers.objectives

            assert(O._mounted == true, "O must be mounted")

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            assert(OM._active_objectives["collect"] == nil,
                "OM registry must be absent immediately after 3rd complete")
            assert(#O._active == 0,
                "O._active must be empty after completion")

            local t = 0
            for i = 1, 15 do
                t = t + 0.1
                RT:update(managers.hud, t, 0.1)
            end

            local all_hidden = true
            for i = 1, 3 do
                local slot = O._slot_prims[i]
                if slot and slot.text and slot.text:visible() and slot.text:text() ~= "" then
                    all_hidden = false
                end
            end
            assert(all_hidden == true,
                "all 3 titles must be hidden/empty after no-current animation completes")

            assert(O:_verify_render() == true,
                "_verify_render must be true after animation completes")
        ''')

    def test_native_color_userdata_fixture_support(self):
        """Native color userdata fixture support: verify Color() returns a table
        with RGBA accessible via numeric indices [1]=alpha, [2]=r, [3]=g, [4]=b.

        This ensures the test fixture properly supports the production code's
        o_read_color_rgba function which reads color via [2], [3], [4].
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local c3 = Color(0.52, 0.88, 0.92)
            assert(type(c3) == "table", "Color(3 args) must return table, got " .. type(c3))
            assert(type(c3[1]) == "number", "Color[1] (alpha) must be number")
            assert(type(c3[2]) == "number", "Color[2] (r) must be number")
            assert(type(c3[3]) == "number", "Color[3] (g) must be number")
            assert(type(c3[4]) == "number", "Color[4] (b) must be number")
            assert(math.abs(c3[2] - 0.52) < 0.01, "r must be ~0.52, got " .. tostring(c3[2]))
            assert(math.abs(c3[3] - 0.88) < 0.01, "g must be ~0.88, got " .. tostring(c3[3]))
            assert(math.abs(c3[4] - 0.92) < 0.01, "b must be ~0.92, got " .. tostring(c3[4]))

            local c4 = Color(0.5, 0.6, 0.7, 0.8)
            assert(type(c4) == "table", "Color(4 args) must return table")
            assert(math.abs(c4[1] - 0.5) < 0.01, "alpha must be ~0.5")
            assert(math.abs(c4[2] - 0.6) < 0.01, "r must be ~0.6")
            assert(math.abs(c4[3] - 0.7) < 0.01, "g must be ~0.7")
            assert(math.abs(c4[4] - 0.8) < 0.01, "b must be ~0.8")

            local r = _test_refs
            local O = r.O
            local prim = O._slot_prims[1] and O._slot_prims[1].text
            if prim then
                prim:set_color(Color(0.1, 0.2, 0.3))
                local pc = prim:color()
                assert(type(pc) == "table", "prim:color() must return table")
                assert(math.abs(pc[2] - 0.1) < 0.01, "prim r must be ~0.1")
                assert(math.abs(pc[3] - 0.2) < 0.01, "prim g must be ~0.2")
                assert(math.abs(pc[4] - 0.3) < 0.01, "prim b must be ~0.3")
            end
        ''')


    def test_reset_during_incoming_slide_clears_extra(self):
        """Regression: OM:reset() during incoming slide must clear extra.text and all rows.

        Coordinator repro: fixture, complete collect3, activate n Next,
        RT:update(hud,1,.9); RT:update(hud,1.15,.15); assert extra.text visible true and Next;
        OM:reset(); REQUIRE extra text hidden or cleared immediately, all standard rows
        hidden/empty, no resurrection later update.

        Bug: extra.text remained true for Next after reset.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local RT = r.RT
            local OM = managers.objectives
            local hud = managers.hud

            kyohud.settings.objectives_visible_limit = 3
            RT:refresh_settings(hud)

            local function find_prim_by_text(text)
                for i = 1, 3 do
                    local s = O._slot_prims[i]
                    if s and s.text and s.text:text() == text then
                        return s.text, i
                    end
                end
                return nil, nil
            end

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            OM._objectives["n"] = {id="n", text="Next", sub_objectives={}}
            OM:activate_objective("n", nil, {delay_presentation = false})
            assert(OM._active_objectives["n"] ~= nil, "n must be in registry")

            RT:update(hud, 1.0, 0.9)
            RT:update(hud, 1.15, 0.15)

            assert(O._coordinated_slide_extra,
                "O._coordinated_slide_extra must exist during incoming slide")
            local extra_text = O._coordinated_slide_extra.text
            assert(extra_text,
                "O._coordinated_slide_extra.text must exist during incoming slide")
            assert(extra_text:visible() == true,
                "extra.text must be visible during slide")
            assert(extra_text:text() == "Next",
                "extra.text must be Next, got " .. tostring(extra_text:text()))

            OM:reset()

            local extra_hidden = (not extra_text:visible()) or (extra_text:text() == "")
            assert(extra_hidden,
                "REGRESSION: extra.text must be hidden/cleared after reset, visible=" ..
                tostring(extra_text:visible()) .. " text=" .. tostring(extra_text:text()))

            local all_standard_hidden = true
            for i = 1, 3 do
                local slot = O._slot_prims[i]
                if slot and slot.text then
                    if slot.text:visible() and slot.text:text() ~= "" then
                        all_standard_hidden = false
                    end
                end
            end
            assert(all_standard_hidden,
                "REGRESSION: all standard rows must be hidden/empty after reset")

            for i = 1, 10 do
                RT:update(hud, 1.15 + i * 0.1, 0.1)
            end

            local resurrected = false
            if extra_text:visible() and extra_text:text() ~= "" then
                resurrected = true
            end
            for i = 1, 3 do
                local slot = O._slot_prims[i]
                if slot and slot.text and slot.text:visible() and slot.text:text() ~= "" then
                    resurrected = true
                end
            end
            assert(not resurrected,
                "REGRESSION: no resurrection of text after reset in later updates")
        ''')

    def test_slide_continuity_retained_collect_midpoint(self):
        """Regression: slide continuity with limit 3, retained collect stays .45 alpha.

        limit3 collect->B settled then B->C midpoint1.05; retained collect alpha
        stays .45, y halfway row2->row3.

        When existing history has only one older (collect), oldest should NOT fade
        if room. At midpoint of B->C slide: collect retained alpha .45, y halfway
        between row2 and row3.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local RT = r.RT
            local OM = managers.objectives
            local hud = managers.hud

            kyohud.settings.objectives_visible_limit = 3
            RT:refresh_settings(hud)

            local function find_prim_by_text(text)
                for i = 1, 3 do
                    local s = O._slot_prims[i]
                    if s and s.text and s.text:text() == text then
                        return s.text, i
                    end
                end
                return nil, nil
            end

            local t = 0

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            OM._objectives["B"] = {id="B", text="Objective B", sub_objectives={}}
            OM:activate_objective("B", nil, {delay_presentation = false})
            for i = 1, 20 do
                t = t + 0.1
                RT:update(hud, t, 0.1)
            end

            OM:complete_objective("B")
            assert(OM._active_objectives["B"] == nil, "B must be absent after completion")

            OM._objectives["C"] = {id="C", text="Objective C", sub_objectives={}}
            OM:activate_objective("C", nil, {delay_presentation = false})
            assert(OM._active_objectives["C"] ~= nil, "C must be in registry")

            local collect_prim, collect_slot = find_prim_by_text("Collect bags")
            assert(collect_prim, "Collect bags primitive must exist (retained history)")

            local B_prim, B_slot = find_prim_by_text("Objective B")
            assert(B_prim, "Objective B primitive must exist (completed current)")

            local ly = O._layout_cache
            assert(ly, "layout cache must exist")
            local row_h = ly.row_h

            local collect_y_before = collect_prim:y()
            local B_y_before = B_prim:y()

            t = t + 0.9
            RT:update(hud, t, 0.9)

            t = t + 0.15
            RT:update(hud, t, 0.15)

            local collect_y_mid = collect_prim:y()
            local collect_alpha_mid = collect_prim:alpha()

            assert(math.abs(collect_alpha_mid - 0.45) < 0.05,
                "REGRESSION: retained collect alpha must stay ~0.45 at midpoint, got " ..
                tostring(collect_alpha_mid))

            local expected_collect_y_mid = collect_y_before + (row_h * 0.5)
            assert(math.abs(collect_y_mid - expected_collect_y_mid) < (row_h * 0.1),
                "REGRESSION: retained collect y must be halfway row2->row3, expected ~" ..
                tostring(expected_collect_y_mid) .. " got " .. tostring(collect_y_mid))
        ''')


    def test_limit3_retained_collect_uniqueness_midpoint_and_settled(self):
        """Regression: limit-3 coordinated slide retains collect alpha .45 (NOT .225),
        unique titles across 3 standard slots + extra pair, and settled C/B/collect.

        Exact repro:
        - limit3 refresh_settings
        - complete collect thrice, activate B "Objective B"
        - 20 RT updates dt .1 at times .1..2
        - BEFORE completing B: retain B prim and collect prim + y/alpha,
          assert unique titles across all 3 standard AND _coordinated_slide_extra
          text when visible alpha>0 nonempty
        - Complete B, activate C "Objective C"
        - RT:update(hud,2.9,.9), RT:update(hud,3.05,.15)
        - Desired midpoint: exactly one visible B (same retained primitive),
          y strictly between old and old+row_h alpha .725;
          retained collect moves toward row3 and stays .45 (NOT .225);
          C visibly enters via extra pair exactly once;
          O:_verify_render() true
        - Final update to settled C/B/collect at alphas 1/.45/.45 with uniqueness
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local RT = r.RT
            local OM = managers.objectives
            local hud = managers.hud

            kyohud.settings.objectives_visible_limit = 3
            RT:refresh_settings(hud)

            local function find_prim_by_text(text)
                for i = 1, 3 do
                    local s = O._slot_prims[i]
                    if s and s.text and s.text:text() == text then
                        return s.text, i
                    end
                end
                return nil, nil
            end

            local function gather_visible_titles()
                local titles = {}
                for i = 1, 3 do
                    local s = O._slot_prims[i]
                    if s and s.text and s.text:visible()
                        and s.text:alpha() > 0
                        and s.text:text() ~= "" then
                        titles[#titles + 1] = s.text:text()
                    end
                end
                if O._coordinated_slide_extra
                    and O._coordinated_slide_extra.text
                    and O._coordinated_slide_extra.text:visible()
                    and O._coordinated_slide_extra.text:alpha() > 0
                    and O._coordinated_slide_extra.text:text() ~= "" then
                    titles[#titles + 1] = O._coordinated_slide_extra.text:text()
                end
                return titles
            end

            local function assert_unique(titles, label)
                local seen = {}
                for _, t in ipairs(titles) do
                    assert(not seen[t],
                        "REGRESSION: duplicate title '" .. t .. "' at " .. label)
                    seen[t] = true
                end
            end

            local t = 0

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            OM._objectives["B"] = {id="B", text="Objective B", sub_objectives={}}
            OM:activate_objective("B", nil, {delay_presentation = false})
            for i = 1, 20 do
                t = t + 0.1
                RT:update(hud, t, 0.1)
            end

            local B_prim, B_slot = find_prim_by_text("Objective B")
            assert(B_prim, "Objective B primitive must exist before completion")
            local B_y_before = B_prim:y()
            local B_alpha_before = B_prim:alpha()

            local collect_prim, collect_slot = find_prim_by_text("Collect bags")
            assert(collect_prim, "Collect bags primitive must exist before B completion")
            local collect_y_before = collect_prim:y()
            local collect_alpha_before = collect_prim:alpha()

            assert(math.abs(B_alpha_before - 1.0) < 0.01,
                "REGRESSION: B alpha must be ~1.0 before completion, got " ..
                tostring(B_alpha_before))
            assert(math.abs(collect_alpha_before - 0.45) < 0.05,
                "REGRESSION: collect alpha must be ~0.45 before B completion, got " ..
                tostring(collect_alpha_before))

            local titles_before = gather_visible_titles()
            assert(#titles_before >= 2,
                "at least 2 visible titles before B completion, got " .. #titles_before)
            assert_unique(titles_before, "before B completion")

            OM:complete_objective("B")
            assert(OM._active_objectives["B"] == nil,
                "B must be absent from registry immediately after completion")
            assert(#O._active == 0,
                "O._active must be empty after B completion")

            OM._objectives["C"] = {id="C", text="Objective C", sub_objectives={}}
            OM:activate_objective("C", nil, {delay_presentation = false})
            assert(OM._active_objectives["C"] ~= nil,
                "C must be in registry after activation")

            RT:update(hud, 2.9, 0.9)
            RT:update(hud, 3.05, 0.15)

            assert(B_prim:text() == "Objective B",
                "REGRESSION: B prim must still say 'Objective B' at midpoint, got '" ..
                tostring(B_prim:text()) .. "'")
            assert(B_prim:visible() == true,
                "B must be visible at midpoint")

            local B_y_mid = B_prim:y()
            local ly = O._layout_cache
            assert(ly, "layout cache must exist")
            local row_h = ly.row_h

            assert(B_y_mid > B_y_before,
                "B y must increase (slide down), before=" .. tostring(B_y_before) ..
                " mid=" .. tostring(B_y_mid))
            assert(B_y_mid < B_y_before + row_h,
                "B y at midpoint must be < old+row_h, mid=" .. tostring(B_y_mid) ..
                " dest=" .. tostring(B_y_before + row_h))

            local B_alpha_mid = B_prim:alpha()
            assert(math.abs(B_alpha_mid - 0.725) < 0.025,
                "REGRESSION: B alpha must be ~0.725 at midpoint, got " ..
                tostring(B_alpha_mid))

            assert(collect_prim:visible() == true,
                "collect must be visible at midpoint")
            assert(collect_prim:text() == "Collect bags",
                "REGRESSION: retained collect_prim text must be 'Collect bags' at midpoint, got '" ..
                tostring(collect_prim:text()) .. "'")

            local collect_alpha_mid = collect_prim:alpha()
            assert(math.abs(collect_alpha_mid - 0.45) < 0.025,
                "REGRESSION: retained collect alpha must stay ~0.45 (NOT .225) at midpoint, got " ..
                tostring(collect_alpha_mid))

            local collect_y_mid = collect_prim:y()
            assert(collect_y_mid > collect_y_before,
                "collect y must increase toward row3, before=" .. tostring(collect_y_before) ..
                " mid=" .. tostring(collect_y_mid))
            assert(collect_y_mid < collect_y_before + row_h,
                "collect y at midpoint must be < old+row_h, mid=" .. tostring(collect_y_mid) ..
                " dest=" .. tostring(collect_y_before + row_h))

            local extra = O._coordinated_slide_extra
            assert(extra, "O._coordinated_slide_extra must exist during slide")
            assert(extra.text, "extra.text primitive must exist")
            assert(extra.amount, "extra.amount primitive must exist")

            local extra_vis = false
            if extra.text:visible()
                and extra.text:alpha() > 0
                and extra.text:text() ~= ""
                and extra.text:text() == "Objective C" then
                extra_vis = true
            end
            assert(extra_vis,
                "REGRESSION: C must visibly enter via extra pair, extra.text='" ..
                tostring(extra.text:text()) .. "' alpha=" .. tostring(extra.text:alpha()) ..
                " visible=" .. tostring(extra.text:visible()))

            local C_incoming_y = extra.text:y()
            assert(C_incoming_y > -row_h and C_incoming_y < 0,
                "REGRESSION: incoming C y must be strictly between -row_h and 0, got " ..
                tostring(C_incoming_y) .. " row_h=" .. tostring(row_h))
            local C_incoming_alpha = extra.text:alpha()
            assert(math.abs(C_incoming_alpha - 0.5) < 0.05,
                "REGRESSION: incoming C alpha must be ~0.5 at midpoint, got " ..
                tostring(C_incoming_alpha))

            local c_in_slots = 0
            for i = 1, 3 do
                local s = O._slot_prims[i]
                if s and s.text and s.text:visible()
                    and s.text:text() == "Objective C"
                    and s.text:alpha() > 0 then
                    c_in_slots = c_in_slots + 1
                end
            end
            local c_total = c_in_slots
            if extra_vis then c_total = c_total + 1 end
            assert(c_total == 1,
                "REGRESSION: exactly 1 visible C across slots+extra at midpoint, got " ..
                tostring(c_total))

            local titles_mid = gather_visible_titles()
            assert_unique(titles_mid, "midpoint")

            assert(O:_verify_render() == true,
                "_verify_render must be true at midpoint")

            t = 3.05
            for i = 1, 20 do
                t = t + 0.1
                RT:update(hud, t, 0.1)
            end

            local C_final, C_slot_final = find_prim_by_text("Objective C")
            assert(C_final, "Objective C must exist after slide settles")
            assert(C_final:visible() == true, "C must be visible after settle")
            assert(math.abs(C_final:alpha() - 1.0) < 0.05,
                "C alpha must be ~1.0 after settle, got " .. tostring(C_final:alpha()))

            local B_final, B_slot_final = find_prim_by_text("Objective B")
            assert(B_final, "Objective B must exist as history after settle")
            assert(B_final:visible() == true, "B must be visible after settle")
            assert(math.abs(B_final:alpha() - 0.45) < 0.05,
                "B alpha must be ~0.45 after settle, got " .. tostring(B_final:alpha()))

            local collect_final, collect_slot_final = find_prim_by_text("Collect bags")
            assert(collect_final,
                "Collect bags must exist as retained history after settle")
            assert(collect_final:visible() == true,
                "collect must be visible after settle")
            assert(math.abs(collect_final:alpha() - 0.45) < 0.05,
                "collect alpha must be ~0.45 after settle, got " .. tostring(collect_final:alpha()))

            assert(C_slot_final == 1,
                "REGRESSION: C must settle at slot 1, got " .. tostring(C_slot_final))
            assert(B_slot_final == 2,
                "REGRESSION: B must settle at slot 2, got " .. tostring(B_slot_final))
            assert(collect_slot_final == 3,
                "REGRESSION: collect must settle at slot 3, got " .. tostring(collect_slot_final))
            assert(math.abs(C_final:y() - 0) < row_h * 0.1,
                "REGRESSION: C y must be ~0 after settle, got " .. tostring(C_final:y()))
            assert(math.abs(B_final:y() - row_h) < row_h * 0.1,
                "REGRESSION: B y must be ~row_h after settle, got " .. tostring(B_final:y()))
            assert(math.abs(collect_final:y() - 2 * row_h) < row_h * 0.1,
                "REGRESSION: collect y must be ~2*row_h after settle, got " .. tostring(collect_final:y()))

            local titles_final = gather_visible_titles()
            assert(#titles_final == 3,
                "REGRESSION: exactly 3 visible titles across standard+extra after settle, got " ..
                tostring(#titles_final))
            assert_unique(titles_final, "settled")

            assert(O:_verify_render() == true,
                "_verify_render must be true after settle")
        ''')

    def test_retained_history_certification_during_hold(self):
        """Retained history primitive readback boundary: _verify_render detects
        test-side corruption of slot2 text/y/alpha during stable hold, and
        recovers after restore.

        Sequence: limit3 refresh; complete collect3; activate B "Objective B";
        20 RT updates dt .1; complete B; activate C "Objective C";
        RT:update(hud,2.45,.45) (stable phase, B completed current alpha 1,
        collect retained history at slot2 alpha .45). Assert _verify_render true.
        Retain slot2 primitive text "Collect bags". Corrupt text to "CORRUPT",
        assert _verify_render false. Restore "Collect bags", assert true.
        Corrupt y to old+10, assert false. Restore y, assert true.
        Corrupt alpha to .9, assert false. Restore .45, assert true.

        Test-side primitive corruption is intentional negative readback boundary,
        not mutation of production state.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local RT = r.RT
            local OM = managers.objectives
            local hud = managers.hud

            kyohud.settings.objectives_visible_limit = 3
            RT:refresh_settings(hud)

            local t = 0

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            OM._objectives["B"] = {id="B", text="Objective B", sub_objectives={}}
            OM:activate_objective("B", nil, {delay_presentation = false})
            for i = 1, 20 do
                t = t + 0.1
                RT:update(hud, t, 0.1)
            end

            OM:complete_objective("B")
            assert(OM._active_objectives["B"] == nil,
                "B must be absent from registry after completion")

            OM._objectives["C"] = {id="C", text="Objective C", sub_objectives={}}
            OM:activate_objective("C", nil, {delay_presentation = false})
            assert(OM._active_objectives["C"] ~= nil,
                "C must be in registry after activation")

            RT:update(hud, 2.45, 0.45)

            assert(O:_verify_render() == true,
                "_verify_render must be true during stable hold")

            local slot2 = O._slot_prims[2]
            assert(slot2 and slot2.text,
                "slot2 primitive must exist")
            assert(slot2.text:text() == "Collect bags",
                "slot2 text must be 'Collect bags', got '" ..
                tostring(slot2.text:text()) .. "'")

            local orig_text = slot2.text:text()
            slot2.text:set_text("CORRUPT")
            assert(O:_verify_render() == false,
                "REGRESSION: _verify_render must be false after text corruption")
            slot2.text:set_text(orig_text)
            assert(O:_verify_render() == true,
                "_verify_render must recover after text restore")

            local orig_y = slot2.text:y()
            slot2.text:set_y(orig_y + 10)
            assert(O:_verify_render() == false,
                "REGRESSION: _verify_render must be false after y corruption")
            slot2.text:set_y(orig_y)
            assert(O:_verify_render() == true,
                "_verify_render must recover after y restore")

            local orig_alpha = slot2.text:alpha()
            slot2.text:set_alpha(0.9)
            assert(O:_verify_render() == false,
                "REGRESSION: _verify_render must be false after alpha corruption")
            slot2.text:set_alpha(orig_alpha)
            assert(O:_verify_render() == true,
                "_verify_render must recover after alpha restore")
        ''')


if __name__ == '__main__':
    unittest.main()
