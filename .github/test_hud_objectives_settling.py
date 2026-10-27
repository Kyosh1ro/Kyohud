import unittest
from test_hud_objectives_animation import _lua_native_ready_animation

class TestHUDObjectivesSettling(unittest.TestCase):
    def test_settling_i13_release_timing(self):
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

            local r = _test_refs
            local O = r.O
            local RT = r.RT
            local OM = managers.objectives
            local leaves = r.leaves

            kyohud.settings.objectives_visible_limit = 3
            RT:refresh_settings(managers.hud)

            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            OM._objectives.B = {id="B", text="Objective B", sub_objectives={}}
            OM:activate_objective("B", nil, {delay_presentation=false})

            _run_coroutine(r.bg_box, 200)

            for i = 1, 125 do
                RT:update(managers.hud, 1 + i * 0.016, 0.016)
            end

            OM:complete_objective("B")

            _run_coroutine(r.objectives_panel, 200)
            _run_coroutine(r.bg_box, 200)

            RT:update(managers.hud, 4, 1)

            OM._objectives.C = {id="C", text="Objective C", sub_objectives={}}
            OM:activate_objective("C", nil, {delay_presentation=false})

            assert(O:_verify_render() == true, "baseline verifier")
            assert(O._native_acquired == true, "baseline acquired")

            local release_count = 0
            local orig_release = O._release_native
            function O:_release_native(...)
                if self._native_acquired then
                    release_count = release_count + 1
                end
                return orig_release(self, ...)
            end

            local row_h = O._layout_cache.row_h
            local slot1 = O._slot_prims[1]
            local slot2 = O._slot_prims[2]
            local slot3 = O._slot_prims[3]
            local root_panel = O._root_panel

            for i = 1, 20 do
                RT:update(managers.hud, 4 + i * 0.016, 0.016)

                assert(O:_verify_render() == true, "certification i=" .. i)
                assert(release_count == 0, "spurious release i=" .. i)

                for j, leaf in ipairs(leaves) do
                    assert(leaf:visible() == false, "leaf " .. j .. " visible i=" .. i)
                end

                if i >= 13 then
                    assert(slot1.text:text() == "Objective C", "slot1 title i=" .. i .. " got " .. tostring(slot1.text:text()))
                    assert(slot2.text:text() == "Objective B", "slot2 title i=" .. i .. " got " .. tostring(slot2.text:text()))
                    assert(slot3.text:text() == "Collect bags", "slot3 title i=" .. i .. " got " .. tostring(slot3.text:text()))

                    assert(slot1.text:y() == 0, "slot1 y i=" .. i .. " got " .. tostring(slot1.text:y()))
                    assert(slot2.text:y() == row_h, "slot2 y i=" .. i .. " got " .. tostring(slot2.text:y()))
                    assert(slot3.text:y() == 2 * row_h, "slot3 y i=" .. i .. " got " .. tostring(slot3.text:y()))

                    assert(slot1.text:alpha() == 1, "slot1 alpha i=" .. i .. " got " .. tostring(slot1.text:alpha()))
                    assert(math.abs(slot2.text:alpha() - 0.45) < 0.01, "slot2 alpha i=" .. i .. " got " .. tostring(slot2.text:alpha()))
                    assert(math.abs(slot3.text:alpha() - 0.45) < 0.01, "slot3 alpha i=" .. i .. " got " .. tostring(slot3.text:alpha()))

                    assert(O._root_panel == root_panel, "root changed i=" .. i)
                    assert(O._slot_prims[1] == slot1, "slot1 changed i=" .. i)
                    assert(O._slot_prims[2] == slot2, "slot2 changed i=" .. i)
                    assert(O._slot_prims[3] == slot3, "slot3 changed i=" .. i)
                end
            end
        ''')

if __name__ == '__main__':
    unittest.main()
