"""LOT3a -- bounded behavioral test for completion animation transition.

Tests ONE transition: visible quantity objective genuinely completed through
real hooked ObjectivesManager methods; retained owned displayed title stays
alpha 1.0 with stable Mission cyan for .900 seconds (no pulses); then over
.300 seconds title/counter fade and move upward 4 logical units (no successor)
or coordinated slide with successor entering from top via extra primitives.

Exercises real runtime update with explicit dt/time, not test-side production
state mutation. Asserts live registry removes completed objective immediately,
and no native properties beyond existing whitelist change.

Uses public slot text/amount and owned rect geometry behavior; does not
prescribe a new production method API. During coordinated slide, successor
is located in _coordinated_slide_extra primitives, not in slot prims.
"""
import unittest
from unittest.mock import patch

from test_hud_objectives import STUBS
import test_hud_objectives
from test_hud_objectives_visibility import _lua_native_ready


REAL_COLOR_STUB = '''
Color = function(...)
    local args = {...}
    if #args == 3 then
        return {1, args[1], args[2], args[3]}
    elseif #args == 4 then
        return {args[1], args[2], args[3], args[4]}
    end
    return {1, 1, 1, 1}
end
'''


def _lua_native_ready_animation():
    """Extend _lua_native_ready with color/rect primitive reads for animation testing.

    Does NOT implement animation in fixtures; only adds read capabilities.
    """
    with patch.object(test_hud_objectives, 'STUBS', STUBS + REAL_COLOR_STUB):
        lua, ok = _lua_native_ready()
    if not ok:
        return None, False

    lua.execute('''
        local function extend_prim_with_color(p)
            if p._color_extended then return end
            p._color_extended = true
            if not p._color then
                p._color = {1, 1, 1, 1}
            end

            function p:set_color(c)
                if type(c) == "table" then
                    if #c == 3 then
                        self._color = {1, c[1], c[2], c[3]}
                    else
                        self._color = c
                    end
                end
            end

            function p:color()
                return self._color
            end
        end

        local root = kyohud.hud.runtime._root_panel
        if root then
            extend_prim_with_color(root)
            for name, child in pairs(root._children) do
                extend_prim_with_color(child)
            end
        end

        local O = kyohud.hud.objectives
        if O._root_panel then
            extend_prim_with_color(O._root_panel)

            if not O._root_panel.rect then
                function O._root_panel:rect(opts)
                    local ch = _make_panel(opts and opts.name)
                    ch._parent = self
                    if opts then
                        if opts.x then ch._x = opts.x end
                        if opts.y then ch._y = opts.y end
                        if opts.w then ch._w = opts.w end
                        if opts.h then ch._h = opts.h end
                        if opts.visible ~= nil then ch._visible = opts.visible end
                        if opts.alpha ~= nil then ch._alpha = opts.alpha end
                        if opts.color ~= nil then ch._color = opts.color end
                    end
                    self._children[ch._name] = ch
                    return ch
                end
            end

            local orig_rect = O._root_panel.rect
            function O._root_panel:rect(...)
                local r = orig_rect(self, ...)
                extend_prim_with_color(r)
                return r
            end

            for name, child in pairs(O._root_panel._children) do
                extend_prim_with_color(child)
            end
        end

        if O._slot_prims then
            for i = 1, 3 do
                local slot = O._slot_prims[i]
                if slot then
                    if slot.text then extend_prim_with_color(slot.text) end
                    if slot.amount then extend_prim_with_color(slot.amount) end
                end
            end
        end
    ''')

    return lua, True


class ObjectivesAnimationTests(unittest.TestCase):
    """Bounded behavioral test for completion animation transition."""

    def test_completion_animation_single_transition(self):
        """ONE transition: quantity objective genuinely completed through real
        hooked ObjectivesManager methods; retained owned displayed title stays
        alpha 1.0 with stable cyan for .900 seconds; then over .300 seconds
        title/counter fade and move upward 4 logical units, eventually
        absent/hidden with no successor. Total animation: 1.200s.

        Exercises real runtime update with explicit dt/time, not test-side
        production state mutation. Asserts live registry removes completed
        objective immediately, and no native properties beyond existing whitelist
        change.

        Uses public slot text/amount and owned rect geometry behavior; does not
        prescribe a new production method API.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local amount_text = r.amount_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true, got " .. tostring(vr_base))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "baseline leaf " .. i .. " must be false, got " .. tostring(leaf:visible()))
            end

            local owner_count_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_base = owner_count_base + 1
                end
            end
            assert(owner_count_base == 8, "baseline owner must be 8, got " .. owner_count_base)

            assert(#O._active == 1, "O._active must have 1 entry before completion")
            assert(O._active[1].id == "collect", "active must be collect before completion")
            assert(O._active[1].amount == 3, "amount must be 3 before completion")
            assert(O._active[1].current_amount == 0, "current_amount must be 0 before completion")

            local slot1 = O._slot_prims[1]
            assert(slot1, "slot1 must exist")
            local title_prim = slot1.text
            local amount_prim = slot1.amount
            assert(title_prim, "title primitive must exist")
            assert(amount_prim, "amount primitive must exist")

            local initial_title_text = title_prim:text()
            assert(initial_title_text == "Collect bags",
                "initial title text must be 'Collect bags', got " .. tostring(initial_title_text))

            local initial_amount_text = amount_prim:text()
            assert(initial_amount_text == "0/3",
                "initial amount text must be '0/3', got " .. tostring(initial_amount_text))

            local initial_title_visible = title_prim:visible()
            assert(initial_title_visible == true,
                "initial title visible must be true, got " .. tostring(initial_title_visible))

            local initial_amount_visible = amount_prim:visible()
            assert(initial_amount_visible == true,
                "initial amount visible must be true, got " .. tostring(initial_amount_visible))

            local initial_title_alpha = title_prim:alpha()
            local initial_amount_alpha = amount_prim:alpha()
            local initial_title_y = title_prim:y()
            local initial_amount_y = amount_prim:y()

            local OM = managers.objectives

            OM:complete_objective("collect")
            assert(#O._active == 1, "O._active must still have 1 entry after call 1")
            assert(O._active[1].current_amount == 1, "current_amount must be 1 after call 1")
            assert(slot1.amount:text() == "1/3",
                "owned amount must be '1/3' after call 1, got " .. tostring(slot1.amount:text()))

            OM:complete_objective("collect")
            assert(#O._active == 1, "O._active must still have 1 entry after call 2")
            assert(O._active[1].current_amount == 2, "current_amount must be 2 after call 2")
            assert(slot1.amount:text() == "2/3",
                "owned amount must be '2/3' after call 2, got " .. tostring(slot1.amount:text()))

            OM:complete_objective("collect")
            assert(OM._active_objectives["collect"] == nil,
                "OM registry must not contain collect after call 3")
            assert(#O._active == 0,
                "O._active must have 0 entries after call 3, got " .. #O._active)

            local title_retained_immediately = title_prim:text()
            assert(title_retained_immediately == initial_title_text,
                "title must be retained immediately after completion, got " .. tostring(title_retained_immediately))

            local title_visible_after_completion = title_prim:visible()
            assert(title_visible_after_completion == true,
                "title must remain visible immediately after completion, got " .. tostring(title_visible_after_completion))

            local amount_retained_immediately = amount_prim:text()
            assert(amount_retained_immediately == "3/3",
                "amount must be retained immediately after completion, got " .. tostring(amount_retained_immediately))

            RT:update(managers.hud, 1.0, 0)

            local title_visible_after_update = title_prim:visible()
            assert(title_visible_after_update == true,
                "title must remain visible after first update (RED: baseline removes title immediately), got " .. tostring(title_visible_after_update))

            local title_text_after_update = title_prim:text()
            assert(title_text_after_update == initial_title_text,
                "title text must be retained after first update, got " .. tostring(title_text_after_update))

            local strike_prim = O._root_panel:child("objective_1_strike")
            if strike_prim then
                assert(strike_prim:visible() == false,
                    "strike must NOT be visible at t=0 (no growing rect), got " .. tostring(strike_prim:visible()))
            end

            local title_alpha_after_update = title_prim:alpha()
            assert(title_alpha_after_update > 0.5,
                "title alpha must be > 0.5 after first update, got " .. tostring(title_alpha_after_update))

            local t = 1.0
            RT:update(managers.hud, 1.150, 0.150)
            t = 1.150

            local title_alpha_stable = title_prim:alpha()
            assert(math.abs(title_alpha_stable - 1.0) < 0.01,
                "title alpha must be 1.0 during stable cyan phase (t=.150), got " .. tostring(title_alpha_stable))

            if strike_prim then
                assert(strike_prim:visible() == false,
                    "strike must NOT be visible during stable phase (no growing rect), got " .. tostring(strike_prim:visible()))
            end

            local title_y_stable = title_prim:y()

            RT:update(managers.hud, 1.600, 0.450)
            t = 1.600

            local title_alpha_stable2 = title_prim:alpha()
            assert(math.abs(title_alpha_stable2 - 1.0) < 0.01,
                "title alpha must be 1.0 during stable cyan phase (t=.600), got " .. tostring(title_alpha_stable2))

            if strike_prim then
                assert(strike_prim:visible() == false,
                    "strike must NOT be visible during stable phase (no growing rect), got " .. tostring(strike_prim:visible()))
            end

            local title_y_stable2 = title_prim:y()
            assert(math.abs(title_y_stable2 - title_y_stable) < 1,
                "title y must be stable during phase 1, stable=" .. tostring(title_y_stable) ..
                " stable2=" .. tostring(title_y_stable2))

            local amount_alpha_phase1 = amount_prim:alpha()

            RT:update(managers.hud, 1.900, 0.300)
            t = 1.900

            local title_alpha_exit_start = title_prim:alpha()
            assert(math.abs(title_alpha_exit_start - 1.0) < 0.01,
                "title alpha must be 1.0 at exit start (t=.900), got " .. tostring(title_alpha_exit_start))

            RT:update(managers.hud, 2.050, 0.150)
            t = 2.050

            local title_alpha_exit = title_prim:alpha()
            assert(title_alpha_exit > 0 and title_alpha_exit < 1,
                "title alpha at exit midpoint must be between 0 and 1, got " .. tostring(title_alpha_exit))
            local title_y_exit = title_prim:y()
            local title_y_delta_exit = initial_title_y - title_y_exit
            assert(math.abs(title_y_delta_exit - 2) < 0.5,
                "title y delta at exit midpoint must be ~2, got " .. tostring(title_y_delta_exit))

            assert(title_alpha_exit < title_alpha_stable,
                "title alpha must fade during phase 2, stable=" .. tostring(title_alpha_stable) ..
                " exit=" .. tostring(title_alpha_exit))

            local amount_alpha_exit = amount_prim:alpha()
            assert(amount_alpha_exit < amount_alpha_phase1,
                "amount alpha must fade during phase 2, phase1=" .. tostring(amount_alpha_phase1) ..
                " exit=" .. tostring(amount_alpha_exit))

            RT:update(managers.hud, 2.200, 0.150)
            t = 2.200

            local title_visible_final = title_prim:visible()
            assert(title_visible_final == false,
                "title must be hidden after animation completes, got " .. tostring(title_visible_final))

            local amount_visible_final = amount_prim:visible()
            assert(amount_visible_final == false,
                "amount must be hidden after animation completes, got " .. tostring(amount_visible_final))

            if strike_prim then
                local strike_visible_final = strike_prim:visible()
                assert(strike_visible_final == false,
                    "strike must be hidden after animation completes, got " .. tostring(strike_visible_final))
            end

            assert(#O._active == 0,
                "no successor objective, O._active must remain empty, got " .. #O._active)

            local owner_count_final = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_final = owner_count_final + 1
                end
            end
            assert(owner_count_final == 8,
                "NV owner must remain 8 after owned animation (pending native coroutine never ran), got " .. owner_count_final)

            assert(objectives_panel:visible() == true,
                "objectives_panel must remain visible after animation")
            assert(bg_box:visible() == true,
                "bg_box must remain visible after animation")
            assert(sentinel:visible() == true,
                "sentinel must remain visible after animation")
            assert(sentinel:alpha() == 1,
                "sentinel alpha must remain 1 after animation")

            local whitelist_changed = false
            for i, leaf in ipairs(leaves) do
                local wl_entry = nv._whitelist[leaf]
                if wl_entry and (wl_entry.visible ~= true or wl_entry.alpha ~= nil) then
                    whitelist_changed = true
                end
            end
            assert(whitelist_changed == false,
                "no native whitelist properties must change beyond existing visible=true")
        ''')

    def test_completion_animation_with_multiple_objectives(self):
        """Completed-history: complete first quantity objective with successor, verify
        completed title retained stable cyan then slides to history, successor
        enters via extra during slide, eventually settled with successor visible
        at full alpha in slot1 and completed in slot2 at alpha .45.
        Asserts live registry removes completed objective immediately, successor activates
        natively. Uses real hooked OM methods with explicit dt/time progression.
        """
        for limit in [2, 3]:
            with self.subTest(limit=limit):
                lua, ok = _lua_native_ready_animation()
                self.assertTrue(ok, "objectives production chunk missing")

                lua.execute(f'''
                    local r = _test_refs
                    local O, nv, RT = r.O, r.nv, r.RT
                    local objectives_panel, bg_box, sentinel = r.objectives_panel, r.bg_box, r.sentinel

                    kyohud.settings.objectives_visible_limit = {limit}
                    RT:refresh_settings(managers.hud)

                    assert(O._mounted and O:_verify_render(), "must be mounted and render")

                    local root_identity, sentinel_identity = O._root_panel, sentinel
                    local OM = managers.objectives

                    OM:complete_objective("collect")
                    OM:complete_objective("collect")
                    OM:complete_objective("collect")

                    assert(OM._active_objectives["collect"] == nil, "OM must not contain collect")
                    assert(#O._active == 0, "O._active must be empty, got " .. #O._active)

                    OM._objectives["next_obj"] = {{
                        id = "next_obj", text = "Next objective", amount = nil,
                        current_amount = nil, sub_objectives = {{}},
                    }}
                    OM:activate_objective("next_obj", nil, {{delay_presentation = false}})

                    assert(OM._active_objectives["next_obj"], "next_obj must be active")
                    assert(#O._active == 1 and O._active[1].id == "next_obj", "O._active must have next_obj")

                    local function count_text(text)
                        local c = 0
                        for i = 1, 3 do
                            local s = O._slot_prims[i]
                            if s and s.text and s.text:visible() and s.text:text() == text then c = c + 1 end
                        end
                        return c
                    end

                    local function check_bounds(elapsed)
                        local cc, nc = count_text("Collect bags"), count_text("Next objective")
                        assert(cc <= 1, "Collect bags <= 1 at " .. elapsed .. ", got " .. cc)
                        assert(nc <= 1, "Next objective <= 1 at " .. elapsed .. ", got " .. nc)
                        assert(cc + nc <= {limit}, "total <= " .. {limit} .. " at " .. elapsed)
                        assert(OM._active_objectives["collect"] == nil, "native collect absent at " .. elapsed)
                        assert(OM._active_objectives["next_obj"], "next active at " .. elapsed)
                    end

                    RT:update(managers.hud, 1.0, 0); check_bounds(0)
                    RT:update(managers.hud, 1.150, 0.150); check_bounds(.150)
                    RT:update(managers.hud, 1.600, 0.450); check_bounds(.600)
                    RT:update(managers.hud, 1.750, 0.150); check_bounds(.750)

                    RT:update(managers.hud, 1.900, 0.150)
                    RT:update(managers.hud, 2.050, 0.150)

                    local extra = O._coordinated_slide_extra
                    assert(extra and extra.text, "coordinated slide extra must exist at midpoint")
                    assert(extra.text:visible() == true,
                        "extra text must be visible at midpoint, got " .. tostring(extra.text:visible()))
                    assert(extra.text:text() == "Next objective",
                        "extra text must be Next objective during slide, got " .. tostring(extra.text:text()))
                    local extra_alpha = extra.text:alpha()
                    assert(extra_alpha > 0 and extra_alpha < 1,
                        "extra alpha during slide must be between 0 and 1, got " .. tostring(extra_alpha))

                    local vc_mid = 0
                    for i = 1, 3 do
                        local s = O._slot_prims[i]
                        if s and s.text and s.text:visible() and s.text:text() == "Next objective" then vc_mid = vc_mid + 1 end
                    end
                    if extra.text:visible() and extra.text:text() == "Next objective" then vc_mid = vc_mid + 1 end
                    assert(vc_mid == 1, "REGRESSION: exactly 1 visible 'Next objective' at midpoint across slots+extra, got " .. vc_mid)

                    RT:update(managers.hud, 2.200, 0.150)

                    local s1, s2, s3 = O._slot_prims[1], O._slot_prims[2], O._slot_prims[3]
                    assert(s1.text:text() == "Next objective" and math.abs(s1.text:alpha() - 1) < 0.05, "row1 settled")
                    assert(s2.text:text() == "Collect bags" and math.abs(s2.text:alpha() - 0.45) < 0.05, "row2 faded")
                    assert(s2.amount:text() == "" or not s2.amount:visible(), "row2 amount empty")
                    if s3 then assert(not s3.text:visible() or s3.text:text() == "", "row3 empty") end

                    for i = 1, 3 do
                        local strike = O._root_panel:child("objective_" .. i .. "_strike")
                        if strike then assert(not strike:visible(), "no visible strike") end
                    end

                    assert(O:_verify_render(), "render must be true")

                    local r1_id, r1_txt, r2_id, r2_txt = s1, s1.text:text(), s2, s2.text:text()
                    RT:update(managers.hud, 2.220, 0.020)
                    assert(s1 == r1_id and s1.text:text() == r1_txt, "row1 preserved")
                    assert(s2 == r2_id and s2.text:text() == r2_txt, "row2 preserved")

                    assert(O._root_panel == root_identity and sentinel == sentinel_identity, "identities unchanged")
                    assert(objectives_panel:visible() and bg_box:visible(), "panels visible")
                    assert(sentinel:visible() and sentinel:alpha() == 1, "sentinel ok")
                ''')

    def test_verify_render_detects_corrupted_text_rect_after_completion(self):
        """Regression: _verify_render must detect corrupted owned title text_rect
        after completing 3 real OM calls.

        Complete real OM 3x via hooked methods. Corrupt owned title primitive
        text_rect to return huge values. Assert _verify_render returns false.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local OM = managers.objectives

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true, got " .. tostring(vr_base))

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            assert(OM._active_objectives["collect"] == nil,
                "OM registry must not contain collect after call 3")
            assert(#O._active == 0,
                "O._active must have 0 entries after call 3, got " .. #O._active)

            local title_prim = O._slot_prims[1].text
            assert(title_prim, "title primitive must exist")

            local orig_text_rect = title_prim.text_rect
            function title_prim:text_rect() return 0, 0, 99999, 99999 end

            local vr_corrupt = O:_verify_render()
            assert(vr_corrupt == false,
                "_verify_render must be false with corrupted text_rect, got " .. tostring(vr_corrupt))

            title_prim.text_rect = orig_text_rect
        ''')

    def test_successor_transition_immediate_activation(self):
        """ONE transition with successor: quantity objective genuinely completed
        through real hooked ObjectivesManager methods; stable cyan for .900s;
        then .300s coordinated slide: completed title slides down, existing
        history shifts, successor enters from top via extra primitives.
        After slide (t=1.200): successor visible in slot1 alpha 1.

        Exercises real runtime update with explicit dt/time, not test-side
        production state mutation. Asserts live registry removes completed
        objective immediately. Locates successor in extra during slide,
        then in slot after slide completes.

        Uses public slot text/amount and owned rect geometry behavior; does not
        prescribe a new production method API.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local amount_text = r.amount_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true, got " .. tostring(vr_base))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "baseline leaf " .. i .. " must be false, got " .. tostring(leaf:visible()))
            end

            assert(#O._active == 1, "O._active must have 1 entry before completion")
            assert(O._active[1].id == "collect", "active must be collect before completion")
            assert(O._active[1].amount == 3, "amount must be 3 before completion")
            assert(O._active[1].current_amount == 0, "current_amount must be 0 before completion")

            local slot1 = O._slot_prims[1]
            assert(slot1, "slot1 must exist")
            local title_prim = slot1.text
            local amount_prim = slot1.amount
            assert(title_prim, "title primitive must exist")
            assert(amount_prim, "amount primitive must exist")

            local initial_title_text = title_prim:text()
            assert(initial_title_text == "Collect bags",
                "initial title text must be 'Collect bags', got " .. tostring(initial_title_text))

            local initial_amount_text = amount_prim:text()
            assert(initial_amount_text == "0/3",
                "initial amount text must be '0/3', got " .. tostring(initial_amount_text))

            local initial_title_y = title_prim:y()
            local baseline_title_y = initial_title_y

            local OM = managers.objectives

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
            assert(managers.hud._hud_objectives._active_objective_id == "next_obj",
                "native _active_objective_id must be next_obj immediately, got " .. tostring(managers.hud._hud_objectives._active_objective_id))
            assert(#O._active == 1,
                "O._active must have 1 entry after next activation, got " .. #O._active)
            assert(O._active[1].id == "next_obj",
                "O._active must contain next_obj, got " .. tostring(O._active[1].id))

            local title_retained_immediately = title_prim:text()
            assert(title_retained_immediately == initial_title_text,
                "title must be retained immediately after completion, got " .. tostring(title_retained_immediately))

            RT:update(managers.hud, 1.0, 0)

            local strike_prim = O._root_panel:child("objective_1_strike")
            if strike_prim then
                assert(strike_prim:visible() == false,
                    "strike must NOT be visible at t=0 (no growing rect), got " .. tostring(strike_prim:visible()))
            end

            local t = 1.0
            RT:update(managers.hud, 1.600, 0.600)
            t = 1.600

            if strike_prim then
                assert(strike_prim:visible() == false,
                    "strike must NOT be visible at t=.600 (end of pulse phase), got " .. tostring(strike_prim:visible()))
            end

            RT:update(managers.hud, 1.900, 0.300)
            t = 1.900

            local extra = O._coordinated_slide_extra
            assert(extra and extra.text, "coordinated slide extra must exist at t=.900")

            local next_title_text = extra.text:text()
            assert(next_title_text == "Next objective",
                "extra text must be 'Next objective' at t=.900, got " .. tostring(next_title_text))

            local next_title_alpha = extra.text:alpha()
            assert(math.abs(next_title_alpha - 0) < 0.05,
                "extra alpha must be ~0 at t=.900 (slide starts), got " .. tostring(next_title_alpha))

            local next_title_y = extra.text:y()
            local ly = O._layout_cache
            assert(ly, "layout cache must exist")
            local row_h = ly.row_h
            assert(math.abs(next_title_y - (-row_h)) < 0.5,
                "extra y must be ~-row_h at t=.900 (slide starts above), got " .. tostring(next_title_y))

            local next_strike = O._root_panel:child("objective_1_strike")
            if next_strike then
                assert(next_strike:visible() == false,
                    "next objective must have NO visible strike, strike visible=" .. tostring(next_strike:visible()))
            end

            local vr_mid = O:_verify_render()
            assert(vr_mid == true, "_verify_render must be true at t=.900, got " .. tostring(vr_mid))

            local vc900 = 0
            for i = 1, 3 do
                local s = O._slot_prims[i]
                if s and s.text and s.text:visible() and s.text:text() == "Next objective" then vc900 = vc900 + 1 end
            end
            if extra.text:visible() and extra.text:text() == "Next objective" then vc900 = vc900 + 1 end
            assert(vc900 == 1, "REGRESSION: exactly 1 visible 'Next objective' at .900 (in extra), got " .. vc900)

            RT:update(managers.hud, 2.050, 0.150)
            t = 2.050

            local vc_mid2 = 0
            for i = 1, 3 do
                local s = O._slot_prims[i]
                if s and s.text and s.text:visible() and s.text:text() == "Next objective" then vc_mid2 = vc_mid2 + 1 end
            end
            if extra.text:visible() and extra.text:text() == "Next objective" then vc_mid2 = vc_mid2 + 1 end
            assert(vc_mid2 == 1, "REGRESSION: exactly 1 visible 'Next objective' at midpoint across slots+extra, got " .. vc_mid2)

            local next_title_alpha_mid = extra.text:alpha()
            assert(math.abs(next_title_alpha_mid - 0.5) < 0.1,
                "extra alpha must be ~0.5 at t=1.050 (midpoint), got " .. tostring(next_title_alpha_mid))

            local next_title_y_mid = extra.text:y()
            assert(next_title_y_mid > -row_h and next_title_y_mid < 0,
                "extra y at midpoint must be between -row_h and 0, got " .. tostring(next_title_y_mid))

            local vr_mid2 = O:_verify_render()
            assert(vr_mid2 == true, "_verify_render must be true at t=1.050, got " .. tostring(vr_mid2))

            RT:update(managers.hud, 2.200, 0.150)
            t = 2.200

            local slot1_after = O._slot_prims[1]
            local next_title_alpha_final = slot1_after.text:alpha()
            assert(math.abs(next_title_alpha_final - 1) < 0.05,
                "slot1 alpha must be ~1 at t=1.200 (slide complete), got " .. tostring(next_title_alpha_final))

            local next_title_text_final = slot1_after.text:text()
            assert(next_title_text_final == "Next objective",
                "slot1 text must be 'Next objective' at t=1.200, got " .. tostring(next_title_text_final))

            local next_title_y_final = slot1_after.text:y()
            assert(math.abs(next_title_y_final - baseline_title_y) < 0.5,
                "slot1 y must be ~baseline at t=1.200 (at baseline), baseline=" .. tostring(baseline_title_y) ..
                " got " .. tostring(next_title_y_final))

            local vr_final = O:_verify_render()
            assert(vr_final == true, "_verify_render must be true at t=1.200, got " .. tostring(vr_final))

            local slot2 = O._slot_prims[2]
            if slot2 then
                local slot2_title = slot2.text
                if slot2_title then
                    assert(slot2_title:visible() == false or slot2_title:text() == "",
                        "slot2 must be empty or hidden, got text=" .. tostring(slot2_title:text()) ..
                        " visible=" .. tostring(slot2_title:visible()))
                end
            end

            local slot3 = O._slot_prims[3]
            if slot3 then
                local slot3_title = slot3.text
                if slot3_title then
                    assert(slot3_title:visible() == false or slot3_title:text() == "",
                        "slot3 must be empty or hidden, got text=" .. tostring(slot3_title:text()) ..
                        " visible=" .. tostring(slot3_title:visible()))
                end
            end

            assert(objectives_panel:visible() == true,
                "objectives_panel must remain visible after transition")
            assert(bg_box:visible() == true,
                "bg_box must remain visible after transition")
            assert(sentinel:visible() == true,
                "sentinel must remain visible after transition")
            assert(sentinel:alpha() == 1,
                "sentinel alpha must remain 1 after transition")
        ''')

    def test_successor_title_not_blank_between_polling_deadlines(self):
        """Regression: SOL found successor entry cleanup blanks title at end.

        Existing .580 test gets repaired by recovery poll in same RT tick.
        Split final update into (1.570,.080) then (1.580,.010) to end entry
        BETWEEN polling deadlines, exposing that cleanup blanks successor
        title before recovery can repair it.

        Drive RT update(1,0), (1.220,.220), (1.400,.180), (1.490,.090),
        then (1.570,.080) to set recovery poll while entry active, then
        (1.580,.010) to end entry BETWEEN polling deadlines. Require next
        title text "Next objective" visible true alpha 1 baseline y and
        render certification true immediately at 1.580 and again at
        (1.600,.020), with no manual sync/repair. Assert real OM active
        remains next throughout, strike hidden.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true, got " .. tostring(vr_base))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "baseline leaf " .. i .. " must be false, got " .. tostring(leaf:visible()))
            end

            assert(#O._active == 1, "O._active must have 1 entry before completion")
            assert(O._active[1].id == "collect", "active must be collect before completion")

            local slot1 = O._slot_prims[1]
            assert(slot1, "slot1 must exist")
            local title_prim = slot1.text
            assert(title_prim, "title primitive must exist")

            local baseline_title_y = title_prim:y()
            local OM = managers.objectives

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

            local strike_prim = O._root_panel:child("objective_1_strike")
            assert(strike_prim, "strike rect must exist after first update")

            RT:update(managers.hud, 1.600, 0.600)
            RT:update(managers.hud, 1.900, 0.300)

            local extra = O._coordinated_slide_extra
            assert(extra and extra.text, "coordinated slide extra must exist")
            local next_title_prim = extra.text
            assert(next_title_prim:text() == "Next objective",
                "extra text must be 'Next objective' at t=1.900, got " .. tostring(next_title_prim:text()))

            RT:update(managers.hud, 2.050, 0.150)
            RT:update(managers.hud, 2.190, 0.140)

            assert(OM._active_objectives["next_obj"] ~= nil,
                "OM active must remain next at t=2.190")
            assert(O._active[1].id == "next_obj",
                "O._active must remain next at t=2.190")

            RT:update(managers.hud, 2.200, 0.010)

            local slot1_after = O._slot_prims[1]
            assert(slot1_after.text:text() == "Next objective",
                "REGRESSION: successor title must be 'Next objective' at t=2.200, got " .. tostring(slot1_after.text:text()))
            assert(slot1_after.text:visible() == true,
                "successor title must be visible at t=2.200, got " .. tostring(slot1_after.text:visible()))
            assert(math.abs(slot1_after.text:alpha() - 1) < 0.05,
                "successor title alpha must be ~1 at t=2.200, got " .. tostring(slot1_after.text:alpha()))
            assert(math.abs(slot1_after.text:y() - baseline_title_y) < 0.5,
                "successor title y must be at baseline at t=2.200, baseline=" .. tostring(baseline_title_y) ..
                " got " .. tostring(slot1_after.text:y()))
            assert(O:_verify_render() == true,
                "_verify_render must be true at t=2.200")

            local strike_at_2200 = O._root_panel:child("objective_1_strike")
            if strike_at_2200 then
                assert(strike_at_2200:visible() == false,
                    "strike must be hidden at t=2.200")
            end

            assert(OM._active_objectives["next_obj"] ~= nil,
                "OM active must remain next at t=2.200")
            assert(O._active[1].id == "next_obj",
                "O._active must remain next at t=2.200")

            RT:update(managers.hud, 2.220, 0.020)

            assert(slot1_after.text:text() == "Next objective",
                "REGRESSION: successor title must still be 'Next objective' at t=2.220, got " .. tostring(slot1_after.text:text()))
            assert(slot1_after.text:visible() == true,
                "successor title must be visible at t=2.220")
            assert(math.abs(slot1_after.text:alpha() - 1) < 0.05,
                "successor title alpha must be ~1 at t=2.220")
            assert(math.abs(slot1_after.text:y() - baseline_title_y) < 0.5,
                "successor title y must be at baseline at t=2.220")
            assert(O:_verify_render() == true,
                "_verify_render must be true at t=2.220")

            local strike_at_2220 = O._root_panel:child("objective_1_strike")
            if strike_at_2220 then
                assert(strike_at_2220:visible() == false,
                    "strike must remain hidden at t=2.220")
            end

            assert(OM._active_objectives["next_obj"] ~= nil,
                "OM active must remain next at t=2.220")
            assert(O._active[1].id == "next_obj",
                "O._active must remain next at t=2.220")

            assert(objectives_panel:visible() == true,
                "objectives_panel must remain visible")
            assert(bg_box:visible() == true,
                "bg_box must remain visible")
            assert(sentinel:visible() == true,
                "sentinel must remain visible")
            assert(sentinel:alpha() == 1,
                "sentinel alpha must remain 1")
        ''')


    def test_bounded_interruption_reset_phases(self):
        """OM:reset() during active completion animation must immediately empty
        O._active and clear all owned title/amount/strike text (empty or hidden).
        No ghost reappears via subsequent RT updates after animation duration.
        Root/parent identities and unrelated sentinel unchanged.

        Parameterized across three reset phases:
          pulse  (.150) -- during stable cyan phase
          exit   (.750) -- during stable cyan phase (before exit starts at .900)
          entry  (2.200) -- after slide completes, successor visible in slot

        Uses real hooked OM:reset() (no-arg, takes self only). Does NOT manually
        clear animation state or call repair sync.
        """
        for phase in ("pulse", "exit", "entry"):
            with self.subTest(phase=phase):
                lua, ok = _lua_native_ready_animation()
                self.assertTrue(ok, "objectives production chunk missing")

                lua.globals().test_phase = phase

                lua.execute('''
                    local r = _test_refs
                    local O = r.O
                    local nv = r.nv
                    local RT = r.RT
                    local leaves = r.leaves
                    local objectives_panel = r.objectives_panel
                    local bg_box = r.bg_box
                    local sentinel = r.sentinel

                    assert(O._mounted == true, "O must be mounted")
                    local vr_base = O:_verify_render()
                    assert(vr_base == true, "baseline verifier must be true")

                    local root_identity = O._root_panel
                    local panel_identity = O._panel
                    local rt_gen_before = RT._generation
                    local heist_gen_before = RT._heist_generation
                    local sentinel_val = sentinel:alpha()

                    local slot1 = O._slot_prims[1]
                    assert(slot1, "slot1 must exist")
                    local title_prim = slot1.text
                    local amount_prim = slot1.amount
                    assert(title_prim, "title primitive must exist")
                    assert(amount_prim, "amount primitive must exist")

                    local OM = managers.objectives
                    OM:complete_objective("collect")
                    OM:complete_objective("collect")
                    OM:complete_objective("collect")

                    assert(OM._active_objectives["collect"] == nil,
                        "OM registry must not contain collect after call 3")
                    assert(#O._active == 0,
                        "O._active must have 0 entries after call 3")

                    OM._objectives["next_obj"] = {
                        id = "next_obj", text = "Next objective", amount = nil,
                        current_amount = nil, sub_objectives = {},
                    }
                    OM:activate_objective("next_obj", nil, {delay_presentation = false})

                    assert(OM._active_objectives["next_obj"] ~= nil,
                        "OM registry must contain next_obj")
                    assert(#O._active == 1,
                        "O._active must have 1 entry after next activation")
                    assert(O._active[1].id == "next_obj",
                        "O._active must contain next_obj")

                    RT:update(managers.hud, 1.0, 0)

                    local phase = test_phase
                    local reset_t
                    if phase == "pulse" then
                        RT:update(managers.hud, 1.150, 0.150)
                        reset_t = 1.150
                    elseif phase == "exit" then
                        RT:update(managers.hud, 1.150, 0.150)
                        RT:update(managers.hud, 1.750, 0.600)
                        reset_t = 1.750
                    elseif phase == "entry" then
                        RT:update(managers.hud, 1.150, 0.150)
                        RT:update(managers.hud, 1.750, 0.600)
                        RT:update(managers.hud, 1.900, 0.150)
                        RT:update(managers.hud, 2.050, 0.150)
                        RT:update(managers.hud, 2.200, 0.150)
                        reset_t = 2.200
                    end

                    if phase == "entry" then
                        assert(title_prim:text() == "Next objective",
                            "title must show 'Next objective' before reset, got '" ..
                            tostring(title_prim:text()) .. "'")
                        local title_alpha_before = title_prim:alpha()
                        assert(math.abs(title_alpha_before - 1.0) < 0.05,
                            "title alpha must be ~1.0 before reset, got " .. tostring(title_alpha_before))
                    end

                    OM:reset()

                    assert(#O._active == 0,
                        "O._active must be empty immediately after reset, got " .. #O._active)

                    local title_text_after = title_prim:text()
                    local title_visible_after = title_prim:visible()
                    assert(title_text_after == "" or title_visible_after == false,
                        "REGRESSION: title must be empty or hidden immediately after reset, got text='" ..
                        tostring(title_text_after) .. "' visible=" .. tostring(title_visible_after))

                    local amount_text_after = amount_prim:text()
                    local amount_visible_after = amount_prim:visible()
                    assert(amount_text_after == "" or amount_visible_after == false,
                        "REGRESSION: amount must be empty or hidden immediately after reset, got text='" ..
                        tostring(amount_text_after) .. "' visible=" .. tostring(amount_visible_after))

                    local strike_prim = O._root_panel:child("objective_1_strike")
                    if strike_prim then
                        assert(strike_prim:visible() == false,
                            "REGRESSION: strike must be hidden immediately after reset, got " ..
                            tostring(strike_prim:visible()))
                    end

                    RT:update(managers.hud, reset_t + 0.6, 0.6)

                    local title_text_ghost = title_prim:text()
                    local title_visible_ghost = title_prim:visible()
                    assert(title_text_ghost == "" or title_visible_ghost == false,
                        "REGRESSION: ghost title after reset+RT update, text='" ..
                        tostring(title_text_ghost) .. "' visible=" .. tostring(title_visible_ghost))

                    local amount_text_ghost = amount_prim:text()
                    local amount_visible_ghost = amount_prim:visible()
                    assert(amount_text_ghost == "" or amount_visible_ghost == false,
                        "REGRESSION: ghost amount after reset+RT update, text='" ..
                        tostring(amount_text_ghost) .. "' visible=" .. tostring(amount_visible_ghost))

                    local strike_ghost = O._root_panel:child("objective_1_strike")
                    if strike_ghost then
                        assert(strike_ghost:visible() == false,
                            "REGRESSION: ghost strike after reset+RT update")
                    end

                    assert(O._root_panel == root_identity,
                        "root_panel identity must remain unchanged after reset")
                    assert(O._panel == panel_identity,
                        "panel identity must remain unchanged after reset")
                    assert(RT._generation == rt_gen_before,
                        "RT._generation must remain " .. rt_gen_before ..
                        ", got " .. RT._generation)
                    assert(RT._heist_generation == heist_gen_before,
                        "RT._heist_generation must remain " .. heist_gen_before ..
                        ", got " .. RT._heist_generation)
                    assert(sentinel:alpha() == sentinel_val,
                        "sentinel alpha must remain " .. sentinel_val ..
                        ", got " .. sentinel:alpha())

                    assert(objectives_panel:visible() == true,
                        "objectives_panel must remain visible")
                    assert(bg_box:visible() == true,
                        "bg_box must remain visible")
                ''')


    def test_removal_of_successor_during_entry(self):
        """ONE interruption: removal of successor while entry running.

        Collect completion then immediate Next. RT .490 entry alpha positive;
        real OM:remove_objective(next_obj, nil); registry/O active empty
        immediately, title empty/hidden immediately. Strike hidden (removal NOT
        completion). RT beyond .580 cannot resurrect. Root/sentinel unchanged.

        Expected RED: entry animation state persists after remove.
        """
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local RT = r.RT
            local sentinel = r.sentinel
            local root_id = O._root_panel
            local title_prim = O._slot_prims[1].text
            local OM = managers.objectives

            assert(O._mounted and O:_verify_render())

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            assert(#O._active == 0)

            OM._objectives["next_obj"] = {
                id = "next_obj", text = "Next objective",
                amount = nil, current_amount = nil, sub_objectives = {},
            }
            OM:activate_objective("next_obj", nil, {delay_presentation = false})
            assert(O._active[1].id == "next_obj")

            RT:update(managers.hud, 1.0, 0)
            RT:update(managers.hud, 1.600, 0.600)
            RT:update(managers.hud, 1.900, 0.300)
            RT:update(managers.hud, 2.050, 0.150)
            RT:update(managers.hud, 2.200, 0.150)

            assert(title_prim:text() == "Next objective",
                "title must be 'Next objective' before removal, got " .. tostring(title_prim:text()))
            assert(math.abs(title_prim:alpha() - 1.0) < 0.05,
                "entry alpha ~1.0 before removal, got " .. tostring(title_prim:alpha()))

            OM:remove_objective("next_obj", nil)

            assert(OM._active_objectives["next_obj"] == nil,
                "registry must be empty after remove")
            assert(#O._active == 0,
                "O._active must be empty after remove")

            local t = title_prim:text()
            local v = title_prim:visible()
            assert(t == "" or v == false,
                "REGRESSION: title must clear after remove, text='" ..
                tostring(t) .. "' visible=" .. tostring(v))

            local sp = O._root_panel:child("objective_1_strike")
            if sp then
                assert(sp:visible() == false,
                    "strike hidden (removal NOT completion)")
            end

            RT:update(managers.hud, 2.200, 0.150)
            local t1 = title_prim:text()
            local v1 = title_prim:visible()
            assert(t1 == "" or v1 == false,
                "no resurrection at 2.200")

            RT:update(managers.hud, 2.620, 0.420)
            local t2 = title_prim:text()
            local v2 = title_prim:visible()
            assert(t2 == "" or v2 == false,
                "no resurrection beyond 2.620")

            assert(O._root_panel == root_id, "root unchanged")
            assert(sentinel:alpha() == 1, "sentinel untouched")
        ''')


if __name__ == '__main__':
    unittest.main()
