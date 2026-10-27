"""LOT3a: fitted extra title vs verifier mismatch during coordinated slide.

Verifies coordinated-slide extra row bounds, lifecycle (hidden/cleared after t=1.2),
successor fitted title in slot1, faded "Collect bags" in slot2 at alpha .45,
and exactly one visible "Collect bags" across slots 1..3 and extra at checkpoints.
"""
import unittest
from test_hud_objectives_animation import _lua_native_ready_animation


class ObjectivesLongTitleTransitionTests(unittest.TestCase):

    def test_long_successor_title_fitted_transition_limit3(self):
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            function wait(seconds, fixed_dt)
                local t = 0
                while t < seconds do
                    local dt = coroutine.yield()
                    t = t + (fixed_dt and 0.03333333333333333 or dt)
                end
            end

            kyohud.settings.objectives_visible_limit = 3
            kyohud.settings.hud_scale = 1.1736226804493
            local RT = kyohud.hud.runtime
            RT:refresh_settings(managers.hud)

            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local leaves = r.leaves
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")
            assert(O:_verify_render() == true, "baseline verifier true")

            local owner_count_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_base = owner_count_base + 1
                end
            end
            assert(owner_count_base == 8, "baseline owner 8, got " .. owner_count_base)

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false, "baseline leaf " .. i .. " false")
            end

            local OM = managers.objectives
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            assert(OM._active_objectives["collect"] == nil, "collect cleared")
            assert(#O._active == 0, "O._active empty")

            local long_text = string.rep("Long next objective title ", 8)
            OM._objectives["next_obj"] = {
                id = "next_obj", text = long_text, amount = nil,
                current_amount = nil, sub_objectives = {},
            }
            OM:activate_objective("next_obj", nil, {delay_presentation = false})
            assert(OM._active_objectives["next_obj"] ~= nil, "next_obj activated")
            assert(#O._active == 1, "O._active has 1")
            assert(O._active[1].id == "next_obj", "active is next_obj")

            local native_obj = managers.hud._hud_objectives
            assert(native_obj and native_obj._bg_box, "native HUDObjectives exists")
            local bg_box_native = native_obj._bg_box
            assert(bg_box_native._scheduled_fn, "bg_box has scheduled coroutine")

            local native_co = coroutine.create(bg_box_native._scheduled_fn)
            local native_args = bg_box_native._scheduled_args or {}
            local ok1, err1 = coroutine.resume(native_co, bg_box_native, unpack(native_args))
            assert(ok1, "first resume failed: " .. tostring(err1))

            for i = 1, 80 do
                local elapsed = i * 0.016
                if coroutine.status(native_co) == "suspended" then
                    local okr, errr = coroutine.resume(native_co, 0.016)
                    assert(okr, "resume i=" .. i .. ": " .. tostring(errr))
                end
                RT:update(managers.hud, 1 + elapsed, 0.016)

                local cp = (i == 10 or i == 55 or i == 57 or i == 66
                            or i == 74 or i == 76 or i == 80)
                if cp then
                    assert(O:_verify_render() == true, "verifier i=" .. i)
                    local oc = 0
                    for _, e in ipairs(nv._entries) do
                        if e.owner == O and e.property == "visible" then oc = oc + 1 end
                    end
                    assert(oc == 8, "owner i=" .. i .. " got " .. oc)
                    for li, leaf in ipairs(leaves) do
                        assert(leaf:visible() == false, "leaf " .. li .. " i=" .. i)
                    end
                    assert(sentinel:visible() == true, "sentinel vis i=" .. i)
                    assert(sentinel:alpha() == 1, "sentinel alpha i=" .. i)

                    local hc = 0
                    for _, h in ipairs(O._completion_history) do
                        if h.id == "collect" and h.text == "Collect bags" then hc = hc + 1 end
                    end
                    assert(hc == 1, "history i=" .. i .. " got " .. hc)

                    local cb_vis = 0
                    for si = 1, 3 do
                        local s = O._slot_prims[si]
                        if s and s.text and s.text:visible() and s.text:text() == "Collect bags" then
                            cb_vis = cb_vis + 1
                        end
                    end
                    local extra_cp = O._coordinated_slide_extra
                    if extra_cp and extra_cp.text and extra_cp.text:visible() and extra_cp.text:text() == "Collect bags" then
                        cb_vis = cb_vis + 1
                    end
                    assert(cb_vis == 1, "cb_vis i=" .. i .. " got " .. cb_vis)
                end

                if i == 57 or i == 66 or i == 74 then
                    assert(objectives_panel:visible(), "obj panel i=" .. i)
                    assert(bg_box_native:visible(), "bg_box vis i=" .. i)
                    assert(bg_box_native:w() > 0, "bg_box w i=" .. i)
                    local extra = O._coordinated_slide_extra
                    assert(extra and extra.text, "extra exists i=" .. i)
                    assert(extra.text:visible(), "extra text vis i=" .. i)
                    local et = extra.text:text()
                    assert(type(et) == "string" and #et > 0, "nonempty i=" .. i)
                    assert(et ~= long_text and #et < #long_text, "fitted i=" .. i)
                    local ly = O._layout_cache
                    local row_h = ly.row_h
                    local _,_,ew,eh = extra.text:text_rect()
                    assert(ew <= extra.text:w() + 1, "ew i=" .. i)
                    assert(eh <= row_h + 1, "eh i=" .. i)
                    local ea = extra.text:alpha()
                    assert(ea > 0 and ea <= 1, "alpha i=" .. i)
                    local ey = extra.text:y()
                    assert(ey >= -row_h and ey < 0, "y i=" .. i .. " got " .. ey)
                    if i == 66 then
                        assert(ey > -row_h, "y midpoint i=66 got " .. ey)
                    end
                end

                if i == 66 then
                    local extra = O._coordinated_slide_extra
                    local ot = extra.text:text()
                    extra.text:set_text("CORRUPTED")
                    assert(O:_verify_render() == false, "corrupt text")
                    extra.text:set_text(ot)
                    assert(O:_verify_render() == true, "restore text")
                    local oy = extra.text:y()
                    extra.text:set_y(9999)
                    assert(O:_verify_render() == false, "corrupt y")
                    extra.text:set_y(oy)
                    assert(O:_verify_render() == true, "restore y")
                    local oa = extra.text:alpha()
                    extra.text:set_alpha(0.0)
                    assert(O:_verify_render() == false, "corrupt alpha")
                    extra.text:set_alpha(oa)
                    assert(O:_verify_render() == true, "restore alpha")
                end

                if i == 76 or i == 80 then
                    local extra = O._coordinated_slide_extra
                    assert(extra and extra.text, "extra settled i=" .. i)
                    assert(extra.text:visible() == false, "extra hidden i=" .. i)
                    local et = extra.text:text()
                    assert(type(et) == "string" and #et == 0, "extra empty i=" .. i)
                    local slot1 = O._slot_prims[1]
                    assert(slot1 and slot1.text, "slot1 exists i=" .. i)
                    assert(slot1.text:visible(), "slot1 vis i=" .. i)
                    local s1t = slot1.text:text()
                    assert(type(s1t) == "string" and #s1t > 0, "slot1 nonempty i=" .. i)
                    assert(s1t ~= long_text and #s1t < #long_text, "slot1 fitted i=" .. i)
                    local slot2 = O._slot_prims[2]
                    assert(slot2 and slot2.text, "slot2 exists i=" .. i)
                    assert(slot2.text:visible(), "slot2 vis i=" .. i)
                    assert(slot2.text:text() == "Collect bags", "slot2 text i=" .. i)
                    local s2a = slot2.text:alpha()
                    assert(math.abs(s2a - 0.45) < 0.05, "slot2 alpha i=" .. i .. " got " .. s2a)
                    local hc = 0
                    for _, h in ipairs(O._completion_history) do
                        if h.id == "collect" and h.text == "Collect bags" then hc = hc + 1 end
                    end
                    assert(hc == 1, "history settled i=" .. i)
                end
            end

            assert(objectives_panel:visible() == true, "panel remains")
            assert(bg_box:visible() == true, "bg_box remains")
            assert(sentinel:visible() == true, "sentinel remains")
            assert(sentinel:alpha() == 1, "sentinel alpha 1")
        ''')


if __name__ == '__main__':
    unittest.main()
