"""Tests for heist score extraction to ky_heist_score.lua."""
import re
import unittest
from pathlib import Path

from lupa import LuaRuntime

ROOT = Path(__file__).resolve().parent.parent


def make_lua_runtime():
    """Create a Lua runtime with minimal PD2 API mocks."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute("""
        -- Color constructor: a table that's callable and has properties
        Color = {}
        setmetatable(Color, {
            __call = function(self, r, g, b)
                return {
                    r = r, g = g, b = b, a = 1,
                    with_alpha = function(color, a)
                        return { r = color.r, g = color.g, b = color.b, a = a,
                            with_alpha = function(c2, a2)
                                return { r = c2.r, g = c2.g, b = c2.b, a = a2 }
                            end
                        }
                    end
                }
            end
        })

        -- Pre-built color constants
        Color.white = Color(1, 1, 1)
        Color.black = Color(0, 0, 0)

        -- Idstring mock
        Idstring = function(x) return x end

        -- DB mock
        DB = {
            has = function(...) return true end
        }

        -- tweak_data mock
        tweak_data = {
            menu = {
                pd2_large_font = "fonts/font_large_mf",
                pd2_medium_font = "fonts/font_medium_mf",
                pd2_small_font = "fonts/font_small_mf",
            },
            hud = { present_font_size = 24 },
            hud_icons = {
                get_icon_data = function(self, tweak_id, default_rect)
                    return "guis/textures/pd2/hud_timer", default_rect
                end
            },
            skilltree = { skills = {} },
            preplanning = nil,
        }

        -- managers mock
        managers = {
            localization = {
                text = function(self, id) return id end,
            },
            player = {
                player_unit = function() return nil end,
            },
            skilltree = {},
            environment = {
                worlddirector = {
                    get_wind_direction = function() return 0 end
                }
            }
        }

        -- TimerManager mock
        TimerManager = {
            game = function()
                return {
                    time = function() return 0 end,
                    delta_time = function() return 0.016 end,
                }
            end
        }

        -- Hooks mock
        Hooks = {
            PostHook = function() end,
            PreHook = function() end,
        }

        -- Global helpers
        alive = function(panel) return panel ~= nil end
        log = function() end
        ModPath = "mods/KyoHUD/"
        RequiredScript = "lib/managers/hudmanagerpd2"
        Idstring = function(x) return { str = function() return x end } end

        -- kyohud global table (created by core.lua)
        kyohud = {}
        Kyosh1roHUD = kyohud
    """)
    return lua


class HeistScoreExtractionTests(unittest.TestCase):
    """Test that heist score rendering was correctly extracted to ky_heist_score.lua."""

    def test_heist_score_functions_removed_from_core(self):
        """Core.lua should no longer define heist score rendering functions."""
        core_path = ROOT / "lua" / "core.lua"
        core_src = core_path.read_text(encoding="utf-8-sig")

        self.assertNotIn("local function draw_heist_score_frame", core_src)
        self.assertNotIn("local function draw_heist_score_widget", core_src)
        self.assertNotIn("local function heist_score_labels", core_src)
        self.assertNotIn("local heist_score_labels_cache", core_src)

    def test_heist_score_constants_removed_from_core(self):
        """Core.lua should no longer define heist score constants."""
        core_path = ROOT / "lua" / "core.lua"
        core_src = core_path.read_text(encoding="utf-8-sig")

        self.assertNotIn("HEIST_SCORE_LABEL_COLOR", core_src)
        self.assertNotIn("HEIST_SCORE_BEST_VALUE_COLOR", core_src)
        self.assertNotIn("HEIST_SCORE_EDGE_MARGIN", core_src)

    def test_heist_score_file_exists(self):
        """ky_heist_score.lua should exist."""
        heist_path = ROOT / "lua" / "ky_heist_score.lua"
        self.assertTrue(heist_path.exists(), "ky_heist_score.lua should exist")

    def test_heist_score_functions_moved_to_ky_file(self):
        """ky_heist_score.lua should define the extracted functions."""
        heist_path = ROOT / "lua" / "ky_heist_score.lua"
        heist_src = heist_path.read_text(encoding="utf-8-sig")

        self.assertIn("local function draw_heist_score_frame", heist_src)
        self.assertIn("local function draw_heist_score_widget", heist_src)
        self.assertIn("local function heist_score_labels", heist_src)

    def test_heist_score_constants_moved_to_ky_file(self):
        """ky_heist_score.lua should define the extracted constants."""
        heist_path = ROOT / "lua" / "ky_heist_score.lua"
        heist_src = heist_path.read_text(encoding="utf-8-sig")

        self.assertIn("HEIST_SCORE_LABEL_COLOR", heist_src)
        self.assertIn("HEIST_SCORE_BEST_VALUE_COLOR", heist_src)
        self.assertIn("HEIST_SCORE_EDGE_MARGIN", heist_src)

    def test_heist_score_widget_exposed_on_kh(self):
        """ky_heist_score.lua should expose DrawHeistScoreWidget on KH."""
        heist_path = ROOT / "lua" / "ky_heist_score.lua"
        heist_src = heist_path.read_text(encoding="utf-8-sig")

        self.assertIn("KH.DrawHeistScoreWidget", heist_src)
        self.assertRegex(heist_src, r"KH\.DrawHeistScoreWidget\s*=\s*draw_heist_score_widget")

    def test_core_exposes_required_dependencies(self):
        """Core.lua should expose utilities needed by ky_heist_score.lua."""
        core_path = ROOT / "lua" / "core.lua"
        core_src = core_path.read_text(encoding="utf-8-sig")

        self.assertIn("KH.clamp", core_src)
        self.assertIn("KH.format_kill_score", core_src)
        self.assertIn("KH.approximate_text_width", core_src)
        self.assertIn("KH.localized_text", core_src)
        self.assertIn("KH.KILLFEED_SCORE_COLOR", core_src)
        self.assertIn("KH.KILLFEED_SCORE_PENALTY_COLOR", core_src)

    def test_core_calls_extracted_function(self):
        """Core.lua should call KH.DrawHeistScoreWidget instead of local function."""
        core_path = ROOT / "lua" / "core.lua"
        core_src = core_path.read_text(encoding="utf-8-sig")

        # Should call the extracted function
        self.assertRegex(core_src, r"KH\.DrawHeistScoreWidget\s*\(")

        # Should NOT call the old local function
        self.assertNotRegex(core_src, r"^\s*draw_heist_score_widget\s*\(", re.MULTILINE)

    def test_mod_txt_loads_heist_score_after_core(self):
        """mod.txt should load ky_heist_score.lua after core.lua."""
        mod_path = ROOT / "mod.txt"
        mod_src = mod_path.read_text(encoding="utf-8-sig")

        # Find positions
        core_pos = mod_src.find("lua/core.lua")
        heist_pos = mod_src.find("lua/ky_heist_score.lua")

        self.assertGreater(heist_pos, -1, "ky_heist_score.lua should be in mod.txt")
        self.assertGreater(core_pos, -1, "core.lua should be in mod.txt")
        self.assertGreater(heist_pos, core_pos, "ky_heist_score.lua should load after core.lua")


if __name__ == "__main__":
    unittest.main()
