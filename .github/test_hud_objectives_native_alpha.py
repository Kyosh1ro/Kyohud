"""LOT3a: native alpha/color coupled semantics for completed objectives.

Engine log establishes: completed amount alpha=.45 AND amount:color().a=.45
(Diesel shares alpha/color channel). Verifier o_color_matches_ref expects
constant alpha=1 during blink. Reproduces SOL in memory with fixture coupled
readbacks. Wraps each of 3 slots text+amount getters/setters: old color()
returns stored table array; new color() returns {r=c.r or c[2], g=c.g or c[3],
b=c.b or c[4], a=self:alpha()}; new set_color calls old then self:set_alpha(c.a
or c[1] or 1), preserving native coupled RGBA semantics and separate alpha
getters. Fixture boundary only, no production state injections.

Test actual OM collect3x, baseline verified & native8 held. Immediately after
final completion require verifier true, acquired true all8 leaves hidden;
amount alpha/color.a=.45 while cyan RGB .52,.88,.92. Create native blink co
from recorded objectives_panel fn/args; resume at16ms and RT:update monotonic
through .5 sec; assert verifier true and owner8 throughout blink. Finish blink,
run actual recorded close co interleaved updates through native w0/done_cb;
eight leaves held until close done then owner0 title+amount false,
sentinel/parents untouched. Continue owned animation to 1.2 sec and no fake
active/history. Negative color/alpha checks while completion hold before
running native blink: corrupt title RGB without changing alpha require verifier
false then restore true; corrupt amount alpha from .45 to .9 require false
then restore true. Keep 110-160 lines, no forced repair sync ticks.
"""
import unittest
from test_hud_objectives_animation import _lua_native_ready_animation


class ObjectivesNativeAlphaTests(unittest.TestCase):

    def test_native_alpha_color_coupled_semantics(self):
        """Native alpha/color coupled: amount alpha=.45 and color().a=.45,
        verifier expects constant alpha=1 during blink. Wraps text+amount
        primitives with coupled RGBA semantics."""
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
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

            for i = 1, 3 do
                local slot = O._slot_prims[i]
                assert(slot, "slot " .. i .. " must exist")
                for _, prim_name in ipairs({"text", "amount"}) do
                    local prim = slot[prim_name]
                    assert(prim, "prim " .. prim_name .. " must exist")
                    local old_color = prim.color
                    local old_set_color = prim.set_color
                    prim.color = function(self)
                        local c = old_color(self)
                        return {r=c.r or c[2], g=c.g or c[3],
                                b=c.b or c[4], a=self:alpha()}
                    end
                    prim.set_color = function(self, c)
                        old_set_color(self, c)
                        if type(c) == "table" then
                            self:set_alpha(c.a or c[1] or 1)
                        end
                    end
                end
            end

            assert(O._mounted == true, "O must be mounted")
            assert(O:_verify_render() == true, "baseline verifier true")
            local owner_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_base = owner_base + 1
                end
            end
            assert(owner_base == 8, "baseline owner 8")
            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false, "leaf " .. i .. " hidden")
            end

            local OM = managers.objectives
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            assert(OM._active_objectives["collect"] == nil, "collect cleared")
            assert(#O._active == 0, "O._active empty")

            assert(O:_verify_render() == true, "verifier true after completion")
            local owner_after = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_after = owner_after + 1
                end
            end
            assert(owner_after == 8, "owner 8 after completion")
            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false, "leaf " .. i .. " hidden")
            end

            local slot1 = O._slot_prims[1]
            local amount = slot1.amount
            local amount_alpha = amount:alpha()
            assert(math.abs(amount_alpha - 0.45) < 0.05,
                "amount alpha ~.45 got " .. tostring(amount_alpha))
            local amount_color = amount:color()
            assert(math.abs(amount_color.a - 0.45) < 0.05,
                "amount color.a ~.45 got " .. tostring(amount_color.a))
            assert(math.abs(amount_color.r - 0.52) < 0.01, "cyan R .52")
            assert(math.abs(amount_color.g - 0.88) < 0.01, "cyan G .88")
            assert(math.abs(amount_color.b - 0.92) < 0.01, "cyan B .92")

            local title = slot1.text
            local orig_r, orig_g, orig_b = title:color().r, title:color().g, title:color().b
            local orig_alpha = title:alpha()
            title:set_color({r=0.99, g=0.99, b=0.99, a=orig_alpha})
            assert(O:_verify_render() == false, "corrupt RGB verifier false")
            title:set_color({r=orig_r, g=orig_g, b=orig_b, a=orig_alpha})
            assert(O:_verify_render() == true, "restore RGB verifier true")

            local amount_orig_alpha = amount:alpha()
            amount:set_alpha(0.9)
            assert(O:_verify_render() == false, "corrupt amount alpha verifier false")
            amount:set_alpha(amount_orig_alpha)
            assert(O:_verify_render() == true, "restore amount alpha verifier true")

            assert(objectives_panel._scheduled_fn, "blink fn must be scheduled")
            local blink_fn = objectives_panel._scheduled_fn
            local blink_args = objectives_panel._scheduled_args or {}
            local blink_co = coroutine.create(blink_fn)
            local ok1, err1 = coroutine.resume(blink_co, objectives_panel, unpack(blink_args))
            assert(ok1, "first blink resume failed: " .. tostring(err1))

            local t = 1.0
            for i = 1, 32 do
                if coroutine.status(blink_co) == "suspended" then
                    local okr, errr = coroutine.resume(blink_co, 0.016)
                    assert(okr, "blink resume i=" .. i .. ": " .. tostring(errr))
                end
                RT:update(managers.hud, t + 0.016, 0.016)
                t = t + 0.016

                if i % 8 == 0 then
                    assert(O:_verify_render() == true, "verifier i=" .. i)
                    local oc = 0
                    for _, e in ipairs(nv._entries) do
                        if e.owner == O and e.property == "visible" then oc = oc + 1 end
                    end
                    assert(oc == 8, "owner i=" .. i .. " got " .. oc)
                    for li, lf in ipairs(leaves) do
                        assert(lf:visible() == false, "leaf " .. li .. " hidden i=" .. i)
                    end
                end
            end

            assert(coroutine.status(blink_co) == "dead", "blink must be dead")
            assert(bg_box._scheduled_fn, "close fn must be scheduled after blink")
            local close_fn = bg_box._scheduled_fn
            local close_args = bg_box._scheduled_args or {}
            local close_co = coroutine.create(close_fn)
            local ok2, err2 = coroutine.resume(close_co, bg_box, unpack(close_args))
            assert(ok2, "first close resume failed: " .. tostring(err2))

            while coroutine.status(close_co) == "suspended" do
                local okr, errr = coroutine.resume(close_co, 0.016)
                assert(okr, "close resume suspended: " .. tostring(errr))
                RT:update(managers.hud, t + 0.016, 0.016)
                t = t + 0.016

                if coroutine.status(close_co) == "suspended" then
                    local oc = 0
                    for _, e in ipairs(nv._entries) do
                        if e.owner == O and e.property == "visible" then oc = oc + 1 end
                    end
                    assert(oc == 8, "owner 8 while close suspended")
                    assert(bg_box:w() > 0, "native width positive while close suspended")
                end
            end

            assert(coroutine.status(close_co) == "dead", "close must be dead")
            assert(bg_box:w() == 0, "bg_box w 0 after close dead")
            assert(objectives_panel:visible() == false, "objectives_panel hidden")
            local owner_final = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then owner_final = owner_final + 1 end
            end
            assert(owner_final == 0, "owner 0 after close")
            assert(r.objective_text:visible() == false, "native objective_text hidden")
            assert(r.amount_text:visible() == false, "native amount_text hidden")
            for li, lf in ipairs(leaves) do
                if lf ~= r.objective_text and lf ~= r.amount_text then
                    assert(lf:visible() == true, "other leaf " .. li .. " restored")
                end
            end
            assert(sentinel:visible() == true, "sentinel same")
            assert(sentinel:alpha() == 1, "sentinel alpha same")

            while t < 2.25 do
                RT:update(managers.hud, t + 0.016, 0.016)
                t = t + 0.016
            end
            assert(O:_verify_render() == true, "verifier true final")
            assert(#O._active == 0, "O._active empty")
            local owner_final_check = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then owner_final_check = owner_final_check + 1 end
            end
            assert(owner_final_check == 0, "owner 0 remains")
            assert(#O._completion_history == 1, "completion_history has 1 entry")
            assert(O._completion_history[1].id == "collect", "history id is collect")
        ''')


if __name__ == '__main__':
    unittest.main()
