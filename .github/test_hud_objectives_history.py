"""LOT2b -- objectives history and new animation contract (RED state).

First vertical slice: real OM quantity completion collect then actual
HUD-presented successor Next objective, setting limit 2, after animations
settled using real runtime update.

Desired rendered titles:
  row1: "Next objective" (current)
  row2: "Collect bags" (historical)

Historical amount: empty (no "3/3" shown)
Historical alpha: .45 (stable history opacity)
No visible strike: strike rect either absent or invisible

Authoritative registry removes collect immediately before animation finishes.

New approved animation contract:
  - Stable cyan alpha 1 for .900 seconds (no pulses)
  - Then .300s coordinated slide (completed slides down, history shifts,
    successor enters from top via extra)
  - Total: 1.200s
  - NO strike anywhere

Without current finish animation then hide all objective rows but retain
history for next current.

Negative sibling test: remove_objective rather than genuine completion
creates no historical row.

Uses real runtime update with explicit dt/time, not test-side production
state mutation. Reuses existing real LuaJIT fixtures from
test_hud_objectives_animation and test_hud_objectives_visibility.
"""
import unittest
from unittest.mock import patch

from test_hud_objectives import STUBS
import test_hud_objectives
from test_hud_objectives_animation import _lua_native_ready_animation


class ObjectivesHistoryTests(unittest.TestCase):
    """Bounded behavioral tests for objectives history and new animation contract."""

    def test_history_row_with_successor_limit_2(self):
        """ONE transition: real OM quantity completion collect (3 calls) then
        actual HUD-presented successor Next objective, with limit 2, after
        animations settled using real runtime update.

        Desired rendered titles:
          row1: "Next objective" (current, alpha 1.0)
          row2: "Collect bags" (historical, alpha .45, no amount, no strike)

        New animation contract: stable cyan .900s then .300s coordinated slide.
        Total: 1.200s. NO strike anywhere.

        Authoritative registry removes collect immediately before animation
        finishes.

        Uses real runtime update with explicit dt/time. Asserts no strike
        visible at any point.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            kyohud.settings.objectives_visible_limit = 2
            RT:refresh_settings(managers.hud)

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true, got " .. tostring(vr_base))

            local OM = managers.objectives

            assert(#O._active == 1, "O._active must have 1 entry before completion")
            assert(O._active[1].id == "collect", "active must be collect before completion")

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            assert(OM._active_objectives["collect"] == nil,
                "OM registry must not contain collect after call 3")
            assert(#O._active == 0,
                "O._active must have 0 entries after call 3, got " .. #O._active)

            OM._objectives["next_obj"] = {
                id = "next_obj", text = "Next objective", amount = nil,
                current_amount = nil, sub_objectives = {},
            }
            OM:activate_objective("next_obj", nil, {delay_presentation = false})

            assert(OM._active_objectives["next_obj"] ~= nil,
                "OM registry must contain next_obj immediately after activation")
            assert(#O._active == 1,
                "O._active must have 1 entry after next activation, got " .. #O._active)
            assert(O._active[1].id == "next_obj",
                "O._active must contain next_obj, got " .. tostring(O._active[1].id))

            RT:update(managers.hud, 1.0, 0)

            local t = 1.0

            for pulse_i = 1, 2 do
                local pulse_t = t + 0.300
                RT:update(managers.hud, pulse_t, 0.300)
                t = pulse_t

                local row1_title = O._slot_prims[1].text
                assert(row1_title, "row1 title must exist")
                local row1_text = row1_title:text()
                assert(row1_text == "Next objective" or row1_text == "Collect bags",
                    "row1 must be current or historical, got " .. tostring(row1_text))

                local row1_alpha = row1_title:alpha()
                assert(row1_alpha >= 0.4 and row1_alpha <= 1.0,
                    "row1 alpha during pulse " .. pulse_i .. " must be in [0.4, 1.0], got " .. tostring(row1_alpha))

                local row1_strike = O._root_panel:child("objective_1_strike")
                if row1_strike then
                    assert(row1_strike:visible() == false,
                        "row1 strike must be invisible during pulse " .. pulse_i)
                end
            end

            RT:update(managers.hud, t + 0.300, 0.300)
            t = t + 0.300

            RT:update(managers.hud, t + 0.150, 0.150)
            t = t + 0.150

            RT:update(managers.hud, t + 0.150, 0.150)
            t = t + 0.150

            RT:update(managers.hud, t + 0.050, 0.050)
            t = t + 0.050

            local slot1 = O._slot_prims[1]
            assert(slot1 and slot1.text, "slot1 must exist")
            local row1_text = slot1.text:text()
            assert(row1_text == "Next objective",
                "row1 text must be 'Next objective' after animations settled, got " .. tostring(row1_text))
            assert(slot1.text:visible() == true,
                "row1 must be visible after animations settled")
            local row1_alpha = slot1.text:alpha()
            assert(math.abs(row1_alpha - 1.0) < 0.05,
                "row1 alpha must be ~1.0 (current), got " .. tostring(row1_alpha))

            local slot2 = O._slot_prims[2]
            assert(slot2 and slot2.text, "slot2 must exist")
            local row2_text = slot2.text:text()
            assert(row2_text == "Collect bags",
                "row2 text must be 'Collect bags' (historical), got " .. tostring(row2_text))
            assert(slot2.text:visible() == true,
                "row2 must be visible after animations settled")
            local row2_alpha = slot2.text:alpha()
            assert(math.abs(row2_alpha - 0.45) < 0.05,
                "row2 alpha must be ~0.45 (historical), got " .. tostring(row2_alpha))

            local row2_amount = slot2.amount
            if row2_amount then
                local row2_amount_text = row2_amount:text()
                assert(row2_amount_text == "" or row2_amount_text == nil,
                    "row2 amount must be empty (historical), got " .. tostring(row2_amount_text))
            end

            local row1_strike = O._root_panel:child("objective_1_strike")
            if row1_strike then
                assert(row1_strike:visible() == false,
                    "row1 strike must be invisible (no strike in new contract)")
            end

            local row2_strike = O._root_panel:child("objective_2_strike")
            if row2_strike then
                assert(row2_strike:visible() == false,
                    "row2 strike must be invisible (no strike in new contract)")
            end

            local vr_final = O:_verify_render()
            assert(vr_final == true, "_verify_render must be true after animations settled, got " .. tostring(vr_final))

            assert(#O._active == 1,
                "O._active must have 1 entry after animations, got " .. #O._active)
            assert(O._active[1].id == "next_obj",
                "O._active must contain next_obj after animations")

            assert(objectives_panel:visible() == true,
                "objectives_panel must remain visible after animations")
            assert(bg_box:visible() == true,
                "bg_box must remain visible after animations")
            assert(sentinel:visible() == true,
                "sentinel must remain visible after animations")
        ''')

    def test_remove_objective_no_history_row(self):
        """Negative test: remove_objective rather than genuine completion
        creates no historical row.

        Activate collect, then remove via OM:remove_objective. Activate next_obj.
        After animations settled, only row1 shows "Next objective" (current).
        No row2 with "Collect bags" historical entry.

        Asserts remove_objective does NOT create a historical row, only genuine
        completion does.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            kyohud.settings.objectives_visible_limit = 2
            RT:refresh_settings(managers.hud)

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true, got " .. tostring(vr_base))

            local OM = managers.objectives

            assert(#O._active == 1, "O._active must have 1 entry before removal")
            assert(O._active[1].id == "collect", "active must be collect before removal")

            OM:remove_objective("collect", nil)

            assert(OM._active_objectives["collect"] == nil,
                "OM registry must not contain collect after remove_objective")
            assert(#O._active == 0,
                "O._active must have 0 entries after remove_objective, got " .. #O._active)

            OM._objectives["next_obj"] = {
                id = "next_obj", text = "Next objective", amount = nil,
                current_amount = nil, sub_objectives = {},
            }
            OM:activate_objective("next_obj", nil, {delay_presentation = false})

            assert(OM._active_objectives["next_obj"] ~= nil,
                "OM registry must contain next_obj immediately after activation")
            assert(#O._active == 1,
                "O._active must have 1 entry after next activation, got " .. #O._active)
            assert(O._active[1].id == "next_obj",
                "O._active must contain next_obj, got " .. tostring(O._active[1].id))

            RT:update(managers.hud, 1.0, 0)

            RT:update(managers.hud, 1.600, 0.600)
            RT:update(managers.hud, 1.900, 0.300)
            RT:update(managers.hud, 2.200, 0.300)

            local slot1 = O._slot_prims[1]
            assert(slot1 and slot1.text, "slot1 must exist")
            local row1_text = slot1.text:text()
            assert(row1_text == "Next objective",
                "row1 text must be 'Next objective' after remove_objective, got " .. tostring(row1_text))
            assert(slot1.text:visible() == true,
                "row1 must be visible after remove_objective")

            local slot2 = O._slot_prims[2]
            if slot2 and slot2.text then
                local row2_text = slot2.text:text()
                local row2_visible = slot2.text:visible()
                assert(row2_text == "" or row2_text == nil or row2_visible == false,
                    "row2 must be empty or hidden after remove_objective (no historical row), got text=" .. tostring(row2_text) .. " visible=" .. tostring(row2_visible))
            end

            local vr_final = O:_verify_render()
            assert(vr_final == true, "_verify_render must be true after remove_objective, got " .. tostring(vr_final))

            assert(#O._active == 1,
                "O._active must have 1 entry after remove_objective, got " .. #O._active)
            assert(O._active[1].id == "next_obj",
                "O._active must contain next_obj after remove_objective")

            assert(objectives_panel:visible() == true,
                "objectives_panel must remain visible after remove_objective")
            assert(bg_box:visible() == true,
                "bg_box must remain visible after remove_objective")
            assert(sentinel:visible() == true,
                "sentinel must remain visible after remove_objective")
        ''')

    def test_no_current_hides_all_rows_restores_with_new(self):
        """After completion settles with no current, all titles must be
        hidden/empty; later new current restores history."""
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local RT = r.RT
            local OM = managers.objectives

            kyohud.settings.objectives_visible_limit = 3
            RT:refresh_settings(managers.hud)

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            for i = 1, 20 do
                RT:update(managers.hud, i * 0.1, 0.1)
            end
            for i = 1, 5 do
                RT:update(managers.hud, 2.0 + i * 0.05, 0.05)
            end

            local all_hidden = true
            for i = 1, 3 do
                local slot = O._slot_prims[i]
                if slot and slot.text and slot.text:visible() and slot.text:text() ~= "" then
                    all_hidden = false
                end
            end
            assert(all_hidden == true,
                "all 3 titles must be hidden/empty after completion with no current")

            OM._objectives["new_obj"] = {
                id = "new_obj", text = "New objective",
                sub_objectives = {},
            }
            OM:activate_objective("new_obj", nil, {delay_presentation = false})

            for i = 1, 20 do
                RT:update(managers.hud, 2.3 + i * 0.1, 0.1)
            end
            for i = 1, 5 do
                RT:update(managers.hud, 4.3 + i * 0.05, 0.05)
            end

            local slot1 = O._slot_prims[1]
            assert(slot1 and slot1.text and slot1.text:visible(), "slot1 must be visible with new current")
            assert(slot1.text:text() == "New objective",
                "row1 must be New objective, got " .. tostring(slot1.text:text()))

            local slot2 = O._slot_prims[2]
            assert(slot2 and slot2.text and slot2.text:visible(), "slot2 must restore historical entry")
            assert(slot2.text:text() == "Collect bags",
                "row2 must be Collect bags, got " .. tostring(slot2.text:text()))
        ''')

    def test_history_limit_selection_after_two_completions(self):
        """After two genuine completions (collect, B), test limit selection.

        Sequence: collect3 complete; define B, activate B, settle 20 updates;
        complete B; define C, activate C, settle 20 updates.

        Iterate limit=3,1,2,3 via settings+RT refresh. Desired nonempty visible
        slot texts:
          limit=3: [Objective C, Objective B, Collect bags]
          limit=1: [Objective C]
          limit=2: [Objective C, Objective B]
          limit=3: [Objective C, Objective B, Collect bags]

        Assert alpha: current ~1.0, historical ~0.45. No production state
        assignment. Native OM objective definitions only.
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

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            OM._objectives["B"] = {
                id = "B", text = "Objective B", sub_objectives = {},
            }
            OM:activate_objective("B", nil, {delay_presentation = false})

            for i = 1, 20 do
                RT:update(managers.hud, i * 0.1, 0.1)
            end
            for i = 1, 5 do
                RT:update(managers.hud, 2.0 + i * 0.05, 0.05)
            end

            OM:complete_objective("B")

            OM._objectives["C"] = {
                id = "C", text = "Objective C", sub_objectives = {},
            }
            OM:activate_objective("C", nil, {delay_presentation = false})

            for i = 1, 20 do
                RT:update(managers.hud, 2.3 + i * 0.1, 0.1)
            end
            for i = 1, 5 do
                RT:update(managers.hud, 4.3 + i * 0.05, 0.05)
            end

            local function get_visible_texts()
                local texts = {}
                for i = 1, 3 do
                    local slot = O._slot_prims[i]
                    if slot and slot.text and slot.text:visible() then
                        local t = slot.text:text()
                        if t and t ~= "" then
                            table.insert(texts, t)
                        end
                    end
                end
                return texts
            end

            local function assert_texts(expected, label)
                local actual = get_visible_texts()
                assert(#actual == #expected,
                    label .. ": expected " .. #expected .. " visible, got " .. #actual)
                for i = 1, #expected do
                    assert(actual[i] == expected[i],
                        label .. ": slot " .. i .. " expected '" .. expected[i] .. "' got '" .. tostring(actual[i]) .. "'")
                end
            end

            local function assert_alphas()
                for i = 1, 3 do
                    local slot = O._slot_prims[i]
                    if slot and slot.text and slot.text:visible() then
                        local a = slot.text:alpha()
                        if i == 1 then
                            assert(math.abs(a - 1.0) < 0.05,
                                "current alpha must be ~1.0, got " .. tostring(a))
                        else
                            local t = slot.text:text()
                            if t and t ~= "" then
                                assert(math.abs(a - 0.45) < 0.05,
                                    "historical alpha must be ~0.45, got " .. tostring(a))
                            end
                        end
                    end
                end
            end

            assert_texts({"Objective C", "Objective B", "Collect bags"}, "limit=3 initial")
            assert_alphas()

            kyohud.settings.objectives_visible_limit = 1
            RT:refresh_settings(managers.hud)
            RT:update(managers.hud, 4.1, 0.1)
            assert_texts({"Objective C"}, "limit=1")

            kyohud.settings.objectives_visible_limit = 2
            RT:refresh_settings(managers.hud)
            RT:update(managers.hud, 4.2, 0.1)
            assert_texts({"Objective C", "Objective B"}, "limit=2")

            kyohud.settings.objectives_visible_limit = 3
            RT:refresh_settings(managers.hud)
            RT:update(managers.hud, 4.3, 0.1)
            assert_texts({"Objective C", "Objective B", "Collect bags"}, "limit=3 restored")
            assert_alphas()
        ''')

    def test_real_current_not_multi_active(self):
        """ONE real current: collect remains active uncompleted; define B,
        activate B, settle 20 updates. Exactly one nonempty visible text
        "Current B". Collect bags still in native active registry but NOT
        displayed as history. No completion fabricated.

        Native OM definition insertion only, no production state assignments.
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

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true, got " .. tostring(vr_base))

            assert(#O._active == 1, "O._active must have 1 entry before B activation")
            assert(O._active[1].id == "collect", "active must be collect before B activation")
            assert(OM._active_objectives["collect"] ~= nil,
                "OM registry must contain collect before B activation")

            OM._objectives["B"] = {
                id = "B", text = "Current B", sub_objectives = {},
            }
            OM:activate_objective("B", nil, {delay_presentation = false})

            for i = 1, 20 do
                RT:update(managers.hud, i * 0.1, 0.1)
            end

            local visible_count = 0
            local found_current_b = false
            for i = 1, 3 do
                local slot = O._slot_prims[i]
                if slot and slot.text and slot.text:visible() then
                    local t = slot.text:text()
                    if t and t ~= "" then
                        visible_count = visible_count + 1
                        assert(t == "Current B",
                            "only visible text must be 'Current B', got '" .. tostring(t) .. "'")
                        found_current_b = true
                        assert(math.abs(slot.text:alpha() - 1.0) < 0.05,
                            "current alpha must be ~1.0, got " .. tostring(slot.text:alpha()))
                    end
                end
            end

            assert(visible_count == 1,
                "exactly one nonempty visible text expected, got " .. visible_count)
            assert(found_current_b == true,
                "Current B must be the visible text")

            assert(OM._active_objectives["collect"] ~= nil,
                "collect must remain in native active registry")
            assert(OM._active_objectives["B"] ~= nil,
                "B must be in native active registry")

            for i = 1, 3 do
                local slot = O._slot_prims[i]
                if slot and slot.text then
                    local t = slot.text:text()
                    assert(t ~= "Collect bags",
                        "Collect bags must NOT be displayed as history")
                end
            end

            local vr_final = O:_verify_render()
            assert(vr_final == true,
                "_verify_render must be true after B activation, got " .. tostring(vr_final))
        ''')

    def test_collect_visible_pulse_exit_registry_absent(self):
        """Native fixture complete collect3; real RT update from t0 dt0 then
        sample elapsed .150,.300,.450,.600 with dt .150 each. Title Collect
        bags visible, alpha 1.0 (stable cyan phase), strike absent or hidden.
        At elapsed .900 exit starts, alpha still 1.0.
        At elapsed 1.050 exit midpoint: alpha ~0.5, y initial-2.
        At elapsed 1.200 absent no current; registry absent immediately
        after 3rd native complete. No production state writes.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local RT = r.RT
            local OM = managers.objectives

            kyohud.settings.objectives_visible_limit = 2
            RT:refresh_settings(managers.hud)

            assert(O._mounted == true, "O must be mounted")

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            assert(OM._active_objectives["collect"] == nil,
                "OM registry must be absent immediately after 3rd native complete")

            RT:update(managers.hud, 1.0, 0)

            local y_0
            local slot = O._slot_prims[1]
            if slot and slot.text and slot.text:visible() then
                assert(slot.text:text() == "Collect bags",
                    "title must be 'Collect bags', got " .. tostring(slot.text:text()))
                y_0 = slot.text:y()
            end

            local strike = O._root_panel:child("objective_1_strike")
            if strike then
                assert(strike:visible() == false,
                    "strike must be hidden when visible")
            end

            local function sample(elapsed, expected_alpha, dt)
                RT:update(managers.hud, 1.0 + elapsed, dt)
                local s = O._slot_prims[1]
                assert(s and s.text, "slot text must exist at elapsed " .. elapsed)
                assert(s.text:visible() == true,
                    "text must be visible at elapsed " .. elapsed)
                assert(s.text:text() == "Collect bags",
                    "title must remain 'Collect bags' at elapsed " .. elapsed)
                local a = s.text:alpha()
                assert(math.abs(a - expected_alpha) <= 0.02,
                    "alpha at elapsed " .. elapsed .. " expected " .. expected_alpha .. " got " .. tostring(a))
                local st = O._root_panel:child("objective_1_strike")
                if st then
                    assert(st:visible() == false,
                        "strike must be hidden at elapsed " .. elapsed)
                end
            end

            sample(0.150, 1.00, 0.150)
            sample(0.300, 1.00, 0.150)
            sample(0.450, 1.00, 0.150)
            sample(0.600, 1.00, 0.150)

            RT:update(managers.hud, 1.900, 0.300)
            local s_exit_start = O._slot_prims[1]
            if s_exit_start and s_exit_start.text and s_exit_start.text:visible() then
                local a_exit_start = s_exit_start.text:alpha()
                assert(math.abs(a_exit_start - 1.0) <= 0.02,
                    "alpha at exit start expected ~1.0 got " .. tostring(a_exit_start))
            end

            RT:update(managers.hud, 2.050, 0.150)
            local s_mid = O._slot_prims[1]
            if s_mid and s_mid.text and s_mid.text:visible() then
                local a_mid = s_mid.text:alpha()
                assert(math.abs(a_mid - 0.5) <= 0.02,
                    "alpha at exit midpoint expected ~0.5 got " .. tostring(a_mid))
                if y_0 ~= nil then
                    local y_mid = s_mid.text:y()
                    assert(math.abs((y_mid - y_0) - (-2)) <= 0.5,
                        "y at exit midpoint expected initial-2, got y0=" .. tostring(y_0) .. " y=" .. tostring(y_mid))
                end
            end

            RT:update(managers.hud, 2.200, 0.150)
            local s_final = O._slot_prims[1]
            local final_gone = true
            if s_final and s_final.text and s_final.text:visible() then
                local t = s_final.text:text()
                if t and t ~= "" then
                    final_gone = false
                end
            end
            assert(final_gone == true,
                "no current at elapsed 1.200: text must be absent/non-visible/empty")
            assert(OM._active_objectives["collect"] == nil,
                "OM registry must remain absent at elapsed 1.200")
        ''')

    def test_same_id_distinct_occurrences_limit_3(self):
        """Distinct genuine occurrences of same id create 2 histories.

        Phase 1: complete collect 3 times, settle 20 updates. No current.
        Phase 2: reactivate SAME collect id (existing native definition
        amount 3 numeric retained) via OM:activate_objective(collect,nil,
        {delay_presentation=false}); complete 3 times.
        Phase 3: define next_obj text 'Next objective' sub_objectives={}
        activate; settle 20 updates.
        Limit 3.

        Assert row1 'Next objective', row2 'Collect bags', row3 'Collect bags',
        both histories alpha ~0.45, native collect absent, no more than 2
        histories (same id twice, not duplicate callbacks).

        No assignments to O state or native active registry; only next
        objective definition.
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

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            for i = 1, 20 do
                RT:update(managers.hud, i * 0.1, 0.1)
            end
            for i = 1, 5 do
                RT:update(managers.hud, 2.0 + i * 0.05, 0.05)
            end

            OM:activate_objective("collect", nil, {delay_presentation = false})

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            OM._objectives["next_obj"] = {
                id = "next_obj", text = "Next objective", amount = nil,
                current_amount = nil, sub_objectives = {},
            }
            OM:activate_objective("next_obj", nil, {delay_presentation = false})

            for i = 1, 20 do
                RT:update(managers.hud, 2.3 + i * 0.1, 0.1)
            end
            for i = 1, 5 do
                RT:update(managers.hud, 4.3 + i * 0.05, 0.05)
            end

            local slot1 = O._slot_prims[1]
            assert(slot1 and slot1.text and slot1.text:visible(),
                "slot1 must be visible")
            assert(slot1.text:text() == "Next objective",
                "row1 must be 'Next objective', got " .. tostring(slot1.text:text()))
            assert(math.abs(slot1.text:alpha() - 1.0) < 0.05,
                "row1 alpha must be ~1.0 (current), got " .. tostring(slot1.text:alpha()))

            local slot2 = O._slot_prims[2]
            assert(slot2 and slot2.text and slot2.text:visible(),
                "slot2 must be visible")
            assert(slot2.text:text() == "Collect bags",
                "row2 must be 'Collect bags', got " .. tostring(slot2.text:text()))
            assert(math.abs(slot2.text:alpha() - 0.45) < 0.05,
                "row2 alpha must be ~0.45, got " .. tostring(slot2.text:alpha()))

            local slot3 = O._slot_prims[3]
            assert(slot3 and slot3.text and slot3.text:visible(),
                "slot3 must be visible")
            assert(slot3.text:text() == "Collect bags",
                "row3 must be 'Collect bags', got " .. tostring(slot3.text:text()))
            assert(math.abs(slot3.text:alpha() - 0.45) < 0.05,
                "row3 alpha must be ~0.45, got " .. tostring(slot3.text:alpha()))

            assert(OM._active_objectives["collect"] == nil,
                "native collect must be absent")

            local history_count = 0
            for i = 2, 3 do
                local s = O._slot_prims[i]
                if s and s.text and s.text:visible() then
                    local t = s.text:text()
                    if t and t ~= "" then
                        history_count = history_count + 1
                    end
                end
            end
            assert(history_count <= 2,
                "no more than 2 histories expected, got " .. history_count)
        ''')

    def test_rebuild_preserves_history_then_new_om_clears(self):
        """RT:rebuild preserves historical collect; fresh native-shaped OM source
        replacement discards prior history. New OM:reset clears all."""
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")
        lua.execute('''
            local r, O, RT = _test_refs, _test_refs.O, _test_refs.RT
            local OM = managers.objectives
            kyohud.settings.objectives_visible_limit = 3
            RT:refresh_settings(managers.hud)
            local function settle(t0, n)
                for i = 1, n do RT:update(managers.hud, t0 + i * 0.1, 0.1) end
                for i = 1, 5 do RT:update(managers.hud, t0 + n * 0.1 + i * 0.05, 0.05) end
            end
            local function texts()
                local out = {}
                for i = 1, 3 do
                    local s = O._slot_prims[i]
                    if s and s.text and s.text:visible() then
                        local t = s.text:text()
                        if t and t ~= "" then out[#out+1] = t end
                    end
                end
                return out
            end
            local function check(exp, label)
                local a = texts()
                assert(#a == #exp, label .. ": expected " .. #exp .. " got " .. #a)
                for i = 1, #exp do
                    assert(a[i] == exp[i], label .. " slot" .. i .. " " .. tostring(a[i]))
                end
            end
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM._objectives["B"] = {id="B", text="Objective B", sub_objectives={}}
            OM:activate_objective("B", nil, {delay_presentation = false})
            settle(0, 20)
            check({"Objective B", "Collect bags"}, "post-B")
            RT:rebuild(managers.hud)
            settle(2.1, 20)
            check({"Objective B", "Collect bags"}, "post-rebuild")
            managers.objectives = setmetatable(
                {_objectives={}, _active_objectives={},
                 _completed_objectives={}, _remind_objectives={}},
                {__index = ObjectivesManager})
            local nOM = managers.objectives
            nOM._objectives["C"] = {id="C", text="Objective C", sub_objectives={}}
            nOM:activate_objective("C", nil, {delay_presentation = false})
            settle(4.2, 20)
            check({"Objective C"}, "post-newOM")
            for i = 1, 3 do
                local s = O._slot_prims[i]
                if s and s.text and s.text:visible() then
                    assert(s.text:text() ~= "Collect bags", "no Collect with new OM")
                end
            end
            nOM:reset()
            settle(6.3, 20)
            for i = 1, 3 do
                local s = O._slot_prims[i]
                if s and s.text then
                    local t, v = s.text:text(), s.text:visible()
                    assert(t == "" or t == nil or v == false,
                        "slot" .. i .. " text=" .. tostring(t) .. " vis=" .. tostring(v))
                end
            end
        ''')
