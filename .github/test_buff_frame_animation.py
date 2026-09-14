"""Animated frame regressions for the passive_health_regen buff outline."""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class BuffFrameAnimationTests(unittest.TestCase):
    def make_runtime(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/hudmanagerpd2"
            Hooks = {callbacks = {}}
            function Hooks:PostHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:PreHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:Add(...) end
            HUDManager = {}; PlayerManager = {}; managers = {}; tweak_data = {}
            function Vector3(...) return {...} end
            function log(...) end
            function alive(value) return value ~= nil end
            function Idstring(value) return value end
            DB = {has = function() return true end}
            local function color(r, g, b)
                return {r = r or 0, g = g or 0, b = b or 0,
                        with_alpha = function(self) return self end}
            end
            Color = setmetatable({white = color(1,1,1), black = color(0,0,0)}, {
                __call = function(_, r, g, b) return color(r, g, b) end,
            })
            TimerManager = {game = function()
                return {time = function() return 100 end}
            end}
            Application = {time = function() return 100 end}
        ''')
        lua.execute((ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig"))
        lua.execute((ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig"))
        lua.execute('kyohud.settings = {enable_buffs = true}')
        return lua

    def test_passive_health_regen_has_animation_cache(self):
        lua = self.make_runtime()
        lua.execute('''
            local cache = kyohud._frame_anim_cache
            assert(cache ~= nil, "_frame_anim_cache must exist")
            local anim = cache.passive_health_regen
            assert(anim ~= nil, "passive_health_regen must have an animation entry")
            assert(type(anim.period) == "number" and anim.period > 0,
                "period must be a positive number")
            assert(type(anim.r1) == "number" and type(anim.g1) == "number" and type(anim.b1) == "number",
                "first endpoint must have r/g/b")
            assert(type(anim.r2) == "number" and type(anim.g2) == "number" and type(anim.b2) == "number",
                "second endpoint must have r/g/b")
        ''')

    def test_passive_health_regen_frame_color_changes_over_time(self):
        lua = self.make_runtime()
        lua.execute('''
            local r0, g0, b0, f0 = kyohud:_compute_frame_color("passive_health_regen", 0)
            assert(r0 ~= nil, "must return a color at t=0")
            local r1, g1, b1, f1 = kyohud:_compute_frame_color(
                "passive_health_regen",
                kyohud._frame_anim_cache.passive_health_regen.period * 0.25)
            assert(r1 ~= nil, "must return a color at t=period/4")
            assert(r0 ~= r1 or g0 ~= g1 or b0 ~= b1,
                "frame color must change between t=0 and t=period/4")
        ''')

    def test_passive_health_regen_frame_stays_bounded_between_two_greens(self):
        lua = self.make_runtime()
        lua.execute('''
            local anim = kyohud._frame_anim_cache.passive_health_regen
            local lo_r = math.min(anim.r1, anim.r2)
            local hi_r = math.max(anim.r1, anim.r2)
            local lo_g = math.min(anim.g1, anim.g2)
            local hi_g = math.max(anim.g1, anim.g2)
            local lo_b = math.min(anim.b1, anim.b2)
            local hi_b = math.max(anim.b1, anim.b2)
            local period = anim.period
            for step = 0, 40 do
                local t = period * step / 40
                local r, g, b = kyohud:_compute_frame_color("passive_health_regen", t)
                assert(r ~= nil, "must return a color")
                assert(r >= lo_r - 0.002 and r <= hi_r + 0.002,
                    "r out of bounds at step " .. step .. ": " .. r)
                assert(g >= lo_g - 0.002 and g <= hi_g + 0.002,
                    "g out of bounds at step " .. step .. ": " .. g)
                assert(b >= lo_b - 0.002 and b <= hi_b + 0.002,
                    "b out of bounds at step " .. step .. ": " .. b)
            end
        ''')

    def test_passive_health_regen_frame_loops_without_jump(self):
        lua = self.make_runtime()
        lua.execute('''
            local period = kyohud._frame_anim_cache.passive_health_regen.period
            local r0, g0, b0 = kyohud:_compute_frame_color("passive_health_regen", 0)
            local r_end, g_end, b_end = kyohud:_compute_frame_color("passive_health_regen", period)
            assert(math.abs(r0 - r_end) < 0.001,
                "r must match at loop boundary: " .. r0 .. " vs " .. r_end)
            assert(math.abs(g0 - g_end) < 0.001,
                "g must match at loop boundary: " .. g0 .. " vs " .. g_end)
            assert(math.abs(b0 - b_end) < 0.001,
                "b must match at loop boundary: " .. b0 .. " vs " .. b_end)
            local r_2p, g_2p, b_2p = kyohud:_compute_frame_color("passive_health_regen", period * 2)
            assert(math.abs(r0 - r_2p) < 0.001 and math.abs(g0 - g_2p) < 0.001
                and math.abs(b0 - b_2p) < 0.001,
                "animation must loop cleanly over multiple periods")
        ''')

    def test_non_animated_buff_frame_returns_nil(self):
        lua = self.make_runtime()
        lua.execute('''
            local r = kyohud:_compute_frame_color("total_dodge_chance", 0)
            assert(r == nil,
                "non-animated buff must return nil from _compute_frame_color")
            local r2 = kyohud:_compute_frame_color("damage_increase", 5)
            assert(r2 == nil,
                "another non-animated buff must also return nil")
        ''')

    def test_animated_endpoints_differ_from_dodge_green(self):
        lua = self.make_runtime()
        lua.execute('''
            local anim = kyohud._frame_anim_cache.passive_health_regen
            local dodge_r = 0x2E / 255
            local dodge_g = 0x8B / 255
            local dodge_b = 0x57 / 255
            local dist_a = math.sqrt(
                (anim.r1 - dodge_r)^2 + (anim.g1 - dodge_g)^2 + (anim.b1 - dodge_b)^2)
            local dist_b = math.sqrt(
                (anim.r2 - dodge_r)^2 + (anim.g2 - dodge_g)^2 + (anim.b2 - dodge_b)^2)
            assert(dist_a > 0.1,
                "first PV+ endpoint must be clearly distinct from dodge green, dist=" .. dist_a)
            assert(dist_b > 0.1,
                "second PV+ endpoint must be clearly distinct from dodge green, dist=" .. dist_b)
        ''')

    def test_animated_period_is_in_reasonable_range(self):
        lua = self.make_runtime()
        lua.execute('''
            local period = kyohud._frame_anim_cache.passive_health_regen.period
            assert(period >= 2.0 and period <= 3.0,
                "period must be between 2 and 3 seconds, got " .. period)
        ''')


if __name__ == "__main__":
    unittest.main()
