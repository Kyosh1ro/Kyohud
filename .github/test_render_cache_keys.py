"""Tests for render cache key collision fixes.

Validates that buff frame edge/footer/outline and killfeed top-edge caches
use collision-free nested (color.r, color.g, color.b, alpha_key) buckets
instead of the former non-injective flat numeric keys.

Regression scenarios:
  1. Black(0,0,0) alpha 0.8 and Color(0,0,153/255) alpha 0.2 both produced
     flat key 80 (0*100+80 == 0.6*100+20).
  2. Color(0, 0.5, 0.5) and Color(0, 0.501953125, 0) both produced flat
     color_key 128.5 (0 + 128+0.5 == 0 + 128.5+0).
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


def _make_buff_lua():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.globals().RequiredScript = "lib/managers/hudmanagerpd2"
    lua.execute('''
        Color = {}
        setmetatable(Color, {
            __call = function(_, r, g, b)
                local c = {r = r, g = g, b = b, a = 1}
                function c:with_alpha(alpha)
                    return {r = self.r, g = self.g, b = self.b, a = alpha}
                end
                return c
            end,
        })
        Color.white = Color(1, 1, 1)
        Color.black = Color(0, 0, 0)
        kyohud = {RENDER_CACHES = {
            buff_cell_bg = {},
            edge_points = {},
            buff_cell_footer = {},
            buff_cell_outline = {},
            progress = {},
        }}
        Kyosh1roHUD = kyohud
        Vector3 = function(x, y, z) return {x = x, y = y, z = z} end
        alive = function(x) return x ~= nil end
        log = function() end
        tweak_data = {
            menu = {
                pd2_large_font = "fonts/font_large_mf",
                pd2_medium_font = "fonts/font_medium_mf",
                pd2_small_font = "fonts/font_small_mf",
            },
        }
        kyohud.HUD_ACCENT_COLOR = Color(0.2, 0.8, 1.0)
        kyohud.FALLBACK_TEXTURE = "fallback"
    ''')
    lua.execute(
        (ROOT / "lua" / "ky_buff_presentation.lua").read_text(encoding="utf-8-sig")
    )
    lua.execute((ROOT / "lua" / "ky_buff_render.lua").read_text(encoding="utf-8-sig"))
    return lua


def _make_buff_panel(lua):
    lua.execute('''
        local panel = {
            gradients = {}, rects = {},
        }
        function panel:gradient(params)
            self.gradients[#self.gradients + 1] = params
            return params
        end
        function panel:rect(params)
            self.rects[#self.rects + 1] = params
            return params
        end
        kyohud._test_panel = panel
    ''')


def _make_killfeed_lua():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.globals().RequiredScript = "lib/managers/hudmanagerpd2"
    lua.execute('''
        Hooks = {callbacks = {}}
        function Hooks:PostHook(class, method, id, fn) self.callbacks[id] = fn end
        function Hooks:PreHook(class, method, id, fn) self.callbacks[id] = fn end
        function Hooks:Add(...) end
        HUDManager = {}; PlayerManager = {}; managers = {}; tweak_data = {}
        function Vector3(...) return {...} end
        function log(...) end
        function alive(x) return x ~= nil end
        function Idstring(s) return s end
        DB = { has = function() return false end }
        local function color(r, g, b)
            local c = {r = r or 0, g = g or 0, b = b or 0}
            function c:with_alpha(a)
                return {r = self.r, g = self.g, b = self.b, a = a}
            end
            return c
        end
        Color = setmetatable({white = color(1,1,1), black = color(0,0,0)}, {
            __call = function(_, ...) return color(...) end
        })
        tweak_data.menu = {
            pd2_small_font = "test_font",
            pd2_large_font = "test_font_large",
            pd2_medium_font = "test_font_medium",
        }
        game_t = 100
        TimerManager = {game = function() return {time = function() return game_t end} end}
        PlayerBase = {
            PLAYER_INFO_HUD_PD2 = "pd2",
            PLAYER_INFO_HUD_FULLSCREEN_PD2 = "fs",
        }
    ''')
    for name in [
        "hudlist.lua",
        "core.lua",
        "ky_buff_render.lua",
        "ky_combat_medals.lua",
        "ky_heist_score.lua",
        "ky_hud_banners.lua",
        "ky_killfeed_render.lua",
    ]:
        lua.execute((ROOT / "lua" / name).read_text(encoding="utf-8-sig"))
    return lua


def _make_killfeed_panel(lua):
    lua.execute('''
        local panel = {
            gradients = {}, rects = {}, texts = {}, bitmaps = {}, polygons = {},
            _children = {},
        }
        function panel:w() return 800 end
        function panel:h() return 600 end
        function panel:child() return nil end
        function panel:panel(params)
            self._children[#self._children+1] = params; return self
        end
        function panel:gradient(params)
            self.gradients[#self.gradients + 1] = params
            return params
        end
        function panel:rect(params)
            self.rects[#self.rects + 1] = params
            return params
        end
        function panel:text(params)
            self.texts[#self.texts + 1] = params
            return {
                set_text = function() end,
                text_rect = function() return 0, 0, 15, 10 end,
            }
        end
        function panel:bitmap(params)
            self.bitmaps[#self.bitmaps + 1] = params
            return {
                set_color = function() end,
                set_alpha = function() end,
                set_rotation = function() end,
            }
        end
        function panel:polygon(params)
            self.polygons[#self.polygons + 1] = params
            return params
        end
        function panel:remove() end
        function panel:clear()
            self.gradients = {}; self.rects = {}; self.texts = {}
            self.bitmaps = {}; self.polygons = {}
        end
        kyohud._panel = panel
    ''')


class BuffEdgeCacheCollisionTests(unittest.TestCase):
    """Buff cell frame edge cache: collision-free nested buckets."""

    def test_edge_black_alpha08_vs_blue_alpha02(self):
        """Black(0,0,0) alpha=0.8 and Color(0,0,153/255) alpha=0.2 both
        produced flat key 80 in the old scheme. The new nested scheme must
        yield distinct gradient_points with correct per-call alphas."""
        lua = _make_buff_lua()
        _make_buff_panel(lua)
        lua.execute('''
            local panel = kyohud._test_panel
            local color_a = Color(0, 0, 0)
            local color_b = Color(0, 0, 153/255)

            kyohud.DrawBuffCellFrame(panel, 10, 10, 40, 60, 0.8, 1, color_a)
            local edge_a = panel.gradients[2].gradient_points

            panel.gradients = {}
            kyohud.DrawBuffCellFrame(panel, 10, 10, 40, 60, 0.2, 1, color_b)
            local edge_b = panel.gradients[2].gradient_points

            assert(edge_a ~= edge_b,
                "edge gradient tables must be distinct for colliding pairs")

            assert(math.abs(edge_a[2].a - 0.8 * 0.34) < 1e-9,
                "edge_a[2].a expected " .. tostring(0.8*0.34)
                .. " got " .. tostring(edge_a[2].a))
            assert(math.abs(edge_a[4].a - 0.8 * 0.66) < 1e-9,
                "edge_a[4].a expected " .. tostring(0.8*0.66)
                .. " got " .. tostring(edge_a[4].a))
            assert(math.abs(edge_a[6].a - 0.8) < 1e-9,
                "edge_a[6].a expected 0.8 got " .. tostring(edge_a[6].a))

            assert(math.abs(edge_b[2].a - 0.2 * 0.34) < 1e-9,
                "edge_b[2].a expected " .. tostring(0.2*0.34)
                .. " got " .. tostring(edge_b[2].a))
            assert(math.abs(edge_b[4].a - 0.2 * 0.66) < 1e-9,
                "edge_b[4].a expected " .. tostring(0.2*0.66)
                .. " got " .. tostring(edge_b[4].a))
            assert(math.abs(edge_b[6].a - 0.2) < 1e-9,
                "edge_b[6].a expected 0.2 got " .. tostring(edge_b[6].a))

            assert(edge_b[2].b > 0.5,
                "edge_b color must carry blue; got b=" .. tostring(edge_b[2].b))
        ''')

    def test_footer_black_alpha08_vs_blue_alpha02(self):
        """Footer gradient cache must not collide for the same pair."""
        lua = _make_buff_lua()
        _make_buff_panel(lua)
        lua.execute('''
            local panel = kyohud._test_panel
            local color_a = Color(0, 0, 0)
            local color_b = Color(0, 0, 153/255)

            kyohud.DrawBuffCellFrame(panel, 10, 10, 40, 60, 0.8, 1, color_a)
            local footer_a = panel.gradients[4].gradient_points

            panel.gradients = {}
            kyohud.DrawBuffCellFrame(panel, 10, 10, 40, 60, 0.2, 1, color_b)
            local footer_b = panel.gradients[4].gradient_points

            assert(footer_a ~= footer_b,
                "footer gradient tables must be distinct for colliding pairs")

            assert(math.abs(footer_a[2].a - 0.8 * 0.8) < 1e-9,
                "footer_a[2].a expected " .. tostring(0.8*0.8)
                .. " got " .. tostring(footer_a[2].a))
            assert(math.abs(footer_b[2].a - 0.2 * 0.8) < 1e-9,
                "footer_b[2].a expected " .. tostring(0.2*0.8)
                .. " got " .. tostring(footer_b[2].a))
        ''')

    def test_outline_black_alpha08_vs_blue_alpha02(self):
        """Outline color cache must not collide for the same pair."""
        lua = _make_buff_lua()
        _make_buff_panel(lua)
        lua.execute('''
            local panel = kyohud._test_panel
            local color_a = Color(0, 0, 0)
            local color_b = Color(0, 0, 153/255)

            kyohud.DrawBuffCellFrame(panel, 10, 10, 40, 60, 0.8, 1, color_a)
            local outline_a = panel.rects[1].color

            panel.rects = {}
            kyohud.DrawBuffCellFrame(panel, 10, 10, 40, 60, 0.2, 1, color_b)
            local outline_b = panel.rects[1].color

            assert(outline_a ~= outline_b,
                "outline colors must be distinct for colliding pairs")

            assert(math.abs(outline_a.a - math.min(1, 0.8 * 1.15)) < 1e-9,
                "outline_a.a expected " .. tostring(math.min(1, 0.8*1.15))
                .. " got " .. tostring(outline_a.a))
            assert(math.abs(outline_b.a - math.min(1, 0.2 * 1.15)) < 1e-9,
                "outline_b.a expected " .. tostring(math.min(1, 0.2*1.15))
                .. " got " .. tostring(outline_b.a))

            assert(outline_a.b == 0, "outline_a.b must be 0")
            assert(outline_b.b > 0.5, "outline_b.b must carry blue")
        ''')


class BuffFloatingRGBCollisionTests(unittest.TestCase):
    """Floating-point RGB collision: (0,0.5,0.5) vs (0,0.501953125,0)."""

    def test_floating_rgb_collision_edge(self):
        """Both colors produced flat color_key 128.5; must now differ."""
        lua = _make_buff_lua()
        _make_buff_panel(lua)
        lua.execute('''
            local panel = kyohud._test_panel
            local color_a = Color(0, 0.5, 0.5)
            local color_b = Color(0, 0.501953125, 0)
            local alpha = 0.5

            kyohud.DrawBuffCellFrame(panel, 10, 10, 40, 60, alpha, 1, color_a)
            local edge_a = panel.gradients[2].gradient_points

            panel.gradients = {}
            kyohud.DrawBuffCellFrame(panel, 10, 10, 40, 60, alpha, 1, color_b)
            local edge_b = panel.gradients[2].gradient_points

            assert(edge_a ~= edge_b,
                "floating RGB collision must produce distinct edge tables")

            assert(math.abs(edge_a[2].g - 0.5) < 1e-9,
                "edge_a[2].g expected 0.5 got " .. tostring(edge_a[2].g))
            assert(math.abs(edge_a[2].b - 0.5) < 1e-9,
                "edge_a[2].b expected 0.5 got " .. tostring(edge_a[2].b))
            assert(math.abs(edge_b[2].g - 0.501953125) < 1e-9,
                "edge_b[2].g expected 0.501953125 got " .. tostring(edge_b[2].g))
            assert(edge_b[2].b == 0,
                "edge_b[2].b expected 0 got " .. tostring(edge_b[2].b))
        ''')


class BuffCacheReuseTests(unittest.TestCase):
    """Same-RGB distinct objects must share cache; repeated calls reuse it."""

    def test_same_rgb_different_object_reuses_cache(self):
        lua = _make_buff_lua()
        _make_buff_panel(lua)
        lua.execute('''
            local panel = kyohud._test_panel
            local color_a = Color(0.3, 0.6, 0.9)
            local color_b = Color(0.3, 0.6, 0.9)
            assert(color_a ~= color_b, "precondition: distinct objects")

            kyohud.DrawBuffCellFrame(panel, 10, 10, 40, 60, 0.5, 1, color_a)
            local edge_a = panel.gradients[2].gradient_points
            local footer_a = panel.gradients[4].gradient_points
            local outline_a = panel.rects[1].color

            panel.gradients = {}
            panel.rects = {}
            kyohud.DrawBuffCellFrame(panel, 10, 10, 40, 60, 0.5, 1, color_b)
            local edge_b = panel.gradients[2].gradient_points
            local footer_b = panel.gradients[4].gradient_points
            local outline_b = panel.rects[1].color

            assert(edge_a == edge_b,
                "same RGB distinct objects must share cached edge gradient")
            assert(footer_a == footer_b,
                "same RGB distinct objects must share cached footer gradient")
            assert(outline_a == outline_b,
                "same RGB distinct objects must share cached outline color")
        ''')

    def test_repeated_render_reuses_cache(self):
        lua = _make_buff_lua()
        _make_buff_panel(lua)
        lua.execute('''
            local panel = kyohud._test_panel
            local color = Color(0.4, 0.7, 0.2)

            kyohud.DrawBuffCellFrame(panel, 10, 10, 40, 60, 0.6, 1, color)
            local first_edge = panel.gradients[2].gradient_points
            local first_footer = panel.gradients[4].gradient_points
            local first_outline = panel.rects[1].color
            local first_edge_alpha = first_edge[2].a

            panel.gradients = {}
            panel.rects = {}
            kyohud.DrawBuffCellFrame(panel, 10, 10, 40, 60, 0.6001, 1, color)
            local second_edge = panel.gradients[2].gradient_points
            local second_footer = panel.gradients[4].gradient_points
            local second_outline = panel.rects[1].color

            assert(first_edge == second_edge,
                "0.6 and 0.6001 share quantized bucket; must reuse cached edge")
            assert(first_footer == second_footer,
                "0.6 and 0.6001 share quantized bucket; must reuse cached footer")
            assert(first_outline == second_outline,
                "0.6 and 0.6001 share quantized bucket; must reuse cached outline")
            assert(math.abs(first_edge_alpha - 0.6 * 0.34) < 1e-9,
                "first-use alpha must be retained; got " .. tostring(first_edge_alpha))

            panel.gradients = {}
            panel.rects = {}
            kyohud.DrawBuffCellFrame(panel, 10, 10, 40, 60, 0.6, 1, color)
            local third_edge = panel.gradients[2].gradient_points
            assert(first_edge == third_edge,
                "third call must also reuse the same cached table")
        ''')


class KillfeedTopEdgeCacheCollisionTests(unittest.TestCase):
    """Killfeed top-edge cache via render_killfeed."""

    def test_top_edge_collision_through_render_killfeed(self):
        """Two kill colors that collided at flat key 80 must produce distinct
        top-edge gradient_points when rendered through render_killfeed."""
        lua = _make_killfeed_lua()
        _make_killfeed_panel(lua)
        lua.execute('''
            game_t = 100

            kyohud.SPECIAL_ENEMY_DEFINITIONS = {
                black_kind = {color = Color(0, 0, 0)},
                blue_kind = {color = Color(0, 0, 153/255)},
            }

            kyohud._killfeed_score_total = 0
            kyohud._killfeed_score_has_value = false
            kyohud._special_kill_banner = nil
            kyohud._medal_card = nil
            kyohud.settings = {
                enable_killfeed = true, icon_size = 32, opacity = 0.9,
                killfeed_size = 5, circle_radius = 250,
            }

            -- start_t well past KILL_SCROLL_TIME=0.2 so scroll=1;
            -- t_end far future so life~=1 and item_alpha~=alpha_arg.
            local function compute_item_alpha(alpha_arg, start_t, t_end, t)
                local dur = t_end - start_t
                local life = 1
                if dur > 0 then
                    life = math.max(0, math.min(1, 1 - ((t - start_t) / dur)))
                end
                return alpha_arg * (0.25 + 0.75 * life)
            end

            -- Black kill at alpha_arg=0.8
            kyohud._kills = {{
                name = "Black", display_text = "Black",
                score_text = nil,
                special_kind = "black_kind",
                start_t = 99.7, t_end = 100000,
            }}
            kyohud:render_killfeed(kyohud._panel, 800, 600, 32, 0.8, 250)

            local top_edge_a = nil
            for _, g in ipairs(kyohud._panel.gradients) do
                if g.layer == 102 and g.orientation == "horizontal"
                        and g.h == 1 then
                    top_edge_a = g.gradient_points
                    break
                end
            end
            assert(top_edge_a ~= nil, "must find top-edge gradient for black kill")

            local expected_alpha_a = compute_item_alpha(0.8, 99.7, 100000, 100)

            -- Blue kill at alpha_arg=0.2
            kyohud._panel:clear()
            kyohud._kills = {{
                name = "Blue", display_text = "Blue",
                score_text = nil,
                special_kind = "blue_kind",
                start_t = 99.7, t_end = 100000,
            }}
            kyohud:render_killfeed(kyohud._panel, 800, 600, 32, 0.2, 250)

            local top_edge_b = nil
            for _, g in ipairs(kyohud._panel.gradients) do
                if g.layer == 102 and g.orientation == "horizontal"
                        and g.h == 1 then
                    top_edge_b = g.gradient_points
                    break
                end
            end
            assert(top_edge_b ~= nil, "must find top-edge gradient for blue kill")

            local expected_alpha_b = compute_item_alpha(0.2, 99.7, 100000, 100)

            assert(top_edge_a ~= top_edge_b,
                "top-edge gradients must be distinct for colliding pairs")

            assert(math.abs(top_edge_a[2].a - expected_alpha_a * 0.9) < 1e-6,
                "top_edge_a[2].a expected " .. tostring(expected_alpha_a * 0.9)
                .. " got " .. tostring(top_edge_a[2].a))
            assert(math.abs(top_edge_a[4].a - expected_alpha_a * 0.5) < 1e-6,
                "top_edge_a[4].a expected " .. tostring(expected_alpha_a * 0.5)
                .. " got " .. tostring(top_edge_a[4].a))

            assert(math.abs(top_edge_b[2].a - expected_alpha_b * 0.9) < 1e-6,
                "top_edge_b[2].a expected " .. tostring(expected_alpha_b * 0.9)
                .. " got " .. tostring(top_edge_b[2].a))
            assert(math.abs(top_edge_b[4].a - expected_alpha_b * 0.5) < 1e-6,
                "top_edge_b[4].a expected " .. tostring(expected_alpha_b * 0.5)
                .. " got " .. tostring(top_edge_b[4].a))

            assert(top_edge_a[2].b == 0,
                "black kill top-edge must have b=0")
            assert(top_edge_b[2].b > 0.5,
                "blue kill top-edge must carry blue; got "
                .. tostring(top_edge_b[2].b))
        ''')


class KillfeedFloatingRGBCollisionAndReuseTests(unittest.TestCase):
    """Killfeed top-edge: floating RGB collision and distinct-object reuse."""

    def test_floating_rgb_collision_and_reuse_through_render_killfeed(self):
        """Color(0,0.5,0.5) vs Color(0,0.501953125,0) at same effective alpha
        must yield distinct top-edge payloads; a later distinct Color object
        with RGB equal to the first must reuse its top-edge payload."""
        lua = _make_killfeed_lua()
        _make_killfeed_panel(lua)
        lua.execute('''
            game_t = 100

            kyohud._killfeed_score_total = 0
            kyohud._killfeed_score_has_value = false
            kyohud._special_kill_banner = nil
            kyohud._medal_card = nil
            kyohud.settings = {
                enable_killfeed = true, icon_size = 32, opacity = 0.9,
                killfeed_size = 5, circle_radius = 250,
            }

            local function find_top_edge(panel)
                for _, g in ipairs(panel.gradients) do
                    if g.layer == 102 and g.orientation == "horizontal"
                            and g.h == 1 then
                        return g.gradient_points
                    end
                end
                return nil
            end

            kyohud.SPECIAL_ENEMY_DEFINITIONS = {
                teal_kind = {color = Color(0, 0.5, 0.5)},
                green_kind = {color = Color(0, 0.501953125, 0)},
            }

            kyohud._kills = {{
                name = "Teal", display_text = "Teal",
                score_text = nil,
                special_kind = "teal_kind",
                start_t = 99.7, t_end = 100000,
            }}
            kyohud:render_killfeed(kyohud._panel, 800, 600, 32, 0.7, 250)
            local top_edge_a = find_top_edge(kyohud._panel)
            assert(top_edge_a ~= nil, "must find top-edge for teal kill")

            kyohud._panel:clear()
            kyohud.SPECIAL_ENEMY_DEFINITIONS.green_kind = {
                color = Color(0, 0.501953125, 0),
            }
            kyohud._kills = {{
                name = "Green", display_text = "Green",
                score_text = nil,
                special_kind = "green_kind",
                start_t = 99.7, t_end = 100000,
            }}
            kyohud:render_killfeed(kyohud._panel, 800, 600, 32, 0.7, 250)
            local top_edge_b = find_top_edge(kyohud._panel)
            assert(top_edge_b ~= nil, "must find top-edge for green kill")

            assert(top_edge_a ~= top_edge_b,
                "floating RGB collision must produce distinct top-edge payloads")

            assert(math.abs(top_edge_a[2].g - 0.5) < 1e-9,
                "teal top_edge g expected 0.5 got " .. tostring(top_edge_a[2].g))
            assert(math.abs(top_edge_a[2].b - 0.5) < 1e-9,
                "teal top_edge b expected 0.5 got " .. tostring(top_edge_a[2].b))
            assert(math.abs(top_edge_b[2].g - 0.501953125) < 1e-9,
                "green top_edge g expected 0.501953125 got "
                .. tostring(top_edge_b[2].g))
            assert(top_edge_b[2].b == 0,
                "green top_edge b expected 0 got " .. tostring(top_edge_b[2].b))

            kyohud._panel:clear()
            kyohud.SPECIAL_ENEMY_DEFINITIONS.teal2_kind = {
                color = Color(0, 0.5, 0.5),
            }
            kyohud._kills = {{
                name = "Teal2", display_text = "Teal2",
                score_text = nil,
                special_kind = "teal2_kind",
                start_t = 99.7, t_end = 100000,
            }}
            kyohud:render_killfeed(kyohud._panel, 800, 600, 32, 0.7, 250)
            local top_edge_c = find_top_edge(kyohud._panel)
            assert(top_edge_c ~= nil, "must find top-edge for teal2 kill")

            assert(top_edge_a == top_edge_c,
                "distinct Color with equal RGB must reuse first top-edge payload")
        ''')


if __name__ == "__main__":
    unittest.main()
