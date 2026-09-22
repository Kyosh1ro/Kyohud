"""Regression tests for the buff rendering extraction to ky_buff_render.lua."""

import json
import unittest
from pathlib import Path

from lupa.luajit21 import LuaRuntime


ROOT = Path(__file__).resolve().parents[1]
BUFF_RENDER_PATH = ROOT / "lua" / "ky_buff_render.lua"
BUFF_RENDER_SOURCE = BUFF_RENDER_PATH.read_text(encoding="utf-8-sig")
CORE_PATH = ROOT / "lua" / "core.lua"
CORE_SOURCE = CORE_PATH.read_text(encoding="utf-8-sig")


def make_runtime(required_script="lib/managers/hudmanagerpd2"):
    """Create a minimal Lua runtime with PD2 API mocks."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute(
        """
        Color = {}
        setmetatable(Color, {
            __call = function(_, r, g, b)
                return {
                    r = r,
                    g = g,
                    b = b,
                    a = 1,
                    with_alpha = function(self, alpha)
                        return {r = self.r, g = self.g, b = self.b, a = alpha}
                    end,
                }
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
        ModPath = "mods/KyoHUD/"
        tweak_data = {
            menu = {
                pd2_large_font = "fonts/font_large_mf",
                pd2_medium_font = "fonts/font_medium_mf",
                pd2_small_font = "fonts/font_small_mf",
            },
        }
        """
    )
    lua.globals().RequiredScript = required_script
    return lua


class BuffRenderExtractionTests(unittest.TestCase):
    """Test that buff rendering was correctly extracted to ky_buff_render.lua."""

    def load_module(self, required_script="lib/managers/hudmanagerpd2"):
        lua = make_runtime(required_script)
        # Load ky_buff_presentation first (provides KYO_BUFF_CONFIG)
        lua.execute((ROOT / "lua" / "ky_buff_presentation.lua").read_text(encoding="utf-8-sig"))
        # Load ky_buff_render
        lua.execute(BUFF_RENDER_SOURCE)
        return lua

    def test_definitions_removed_from_core(self):
        """Core.lua should no longer define buff rendering functions."""
        # Functions moved to ky_buff_render.lua
        self.assertNotIn("local function draw_buff_cell_frame", CORE_SOURCE)
        self.assertNotIn("local function draw_timed_buff_progress", CORE_SOURCE)
        self.assertNotIn("local function resolve_buff_state", CORE_SOURCE)
        self.assertNotIn("local function icon_for_buff", CORE_SOURCE)
        self.assertNotIn("local function color_for_buff", CORE_SOURCE)
        self.assertNotIn("local function title_for_buff", CORE_SOURCE)
        self.assertNotIn("local function presentation_label_for_buff", CORE_SOURCE)
        self.assertNotIn("local function compare_buff_arrival", CORE_SOURCE)
        # Value resolution functions moved
        self.assertNotIn("local function application_time", CORE_SOURCE)
        self.assertNotIn("local function source_remaining", CORE_SOURCE)
        self.assertNotIn("local function format_buff_value", CORE_SOURCE)
        self.assertNotIn("local function format_vanillahud_value", CORE_SOURCE)
        self.assertNotIn("local function largest_source_value", CORE_SOURCE)
        self.assertNotIn("local function largest_stack_count", CORE_SOURCE)
        self.assertNotIn("local function compact_number", CORE_SOURCE)
        self.assertNotIn("local function damage_increase_text", CORE_SOURCE)
        self.assertNotIn("local function damage_reduction_text", CORE_SOURCE)
        self.assertNotIn("local function passive_health_regen_text", CORE_SOURCE)
        self.assertNotIn("local function melee_damage_increase_text", CORE_SOURCE)
        self.assertNotIn("local function calculated_base_dodge", CORE_SOURCE)
        self.assertNotIn("local function total_dodge_chance_text", CORE_SOURCE)
        self.assertNotIn("local function equipped_skill_counter_text", CORE_SOURCE)
        self.assertNotIn("local function equipped_pocket_ecm_amount", CORE_SOURCE)
        self.assertNotIn("local function pocket_ecm_cooldown_remaining", CORE_SOURCE)

        # Constants moved to ky_buff_render.lua
        self.assertNotRegex(CORE_SOURCE, r'BUFF_CELL_LINE_WIDTH\s*=')
        self.assertNotRegex(CORE_SOURCE, r'BUFF_WARNING_RATIO\s*=')
        self.assertNotRegex(CORE_SOURCE, r'BUFF_CRITICAL_RATIO\s*=')
        self.assertNotRegex(CORE_SOURCE, r'PASSIVE_REGEN_INTERVAL\s*=')
        self.assertNotRegex(CORE_SOURCE, r'HACKER_SPECIALIZATION_ID\s*=')
        self.assertNotRegex(CORE_SOURCE, r'POCKET_ECM_GRENADE_ID\s*=')
        self.assertNotRegex(CORE_SOURCE, r'POCKET_ECM_COOLDOWN_ID\s*=')

    def test_definitions_moved_to_ky_buff_render(self):
        """ky_buff_render.lua should define the extracted functions."""
        # Rendering functions
        self.assertIn("local function draw_buff_cell_frame", BUFF_RENDER_SOURCE)
        self.assertIn("local function draw_timed_buff_progress", BUFF_RENDER_SOURCE)
        self.assertIn("local function resolve_buff_state", BUFF_RENDER_SOURCE)
        self.assertIn("local function icon_for_buff", BUFF_RENDER_SOURCE)
        self.assertIn("local function color_for_buff", BUFF_RENDER_SOURCE)
        self.assertIn("local function title_for_buff", BUFF_RENDER_SOURCE)
        self.assertIn("local function presentation_label_for_buff", BUFF_RENDER_SOURCE)
        self.assertIn("local function compare_buff_arrival", BUFF_RENDER_SOURCE)
        # Value resolution functions
        self.assertIn("local function application_time", BUFF_RENDER_SOURCE)
        self.assertIn("local function source_remaining", BUFF_RENDER_SOURCE)
        self.assertIn("local function format_buff_value", BUFF_RENDER_SOURCE)
        self.assertIn("local function format_vanillahud_value", BUFF_RENDER_SOURCE)
        self.assertIn("local function largest_source_value", BUFF_RENDER_SOURCE)
        self.assertIn("local function largest_stack_count", BUFF_RENDER_SOURCE)
        self.assertIn("local function compact_number", BUFF_RENDER_SOURCE)
        self.assertIn("local function damage_increase_text", BUFF_RENDER_SOURCE)
        self.assertIn("local function damage_reduction_text", BUFF_RENDER_SOURCE)
        self.assertIn("local function passive_health_regen_text", BUFF_RENDER_SOURCE)
        self.assertIn("local function melee_damage_increase_text", BUFF_RENDER_SOURCE)
        self.assertIn("local function calculated_base_dodge", BUFF_RENDER_SOURCE)
        self.assertIn("local function total_dodge_chance_text", BUFF_RENDER_SOURCE)
        self.assertIn("local function equipped_skill_counter_text", BUFF_RENDER_SOURCE)
        self.assertIn("local function equipped_pocket_ecm_amount", BUFF_RENDER_SOURCE)
        self.assertIn("local function pocket_ecm_cooldown_remaining", BUFF_RENDER_SOURCE)

        # Tables moved
        self.assertIn("BUFF_VALUE_FORMATTERS", BUFF_RENDER_SOURCE)
        self.assertIn("EQUIPPED_SKILL_COUNTER_BUFFS", BUFF_RENDER_SOURCE)
        self.assertIn("STAT_CARD_BUFF_IDS", BUFF_RENDER_SOURCE)
        self.assertIn("STAT_CARD_VALUE_TEXT", BUFF_RENDER_SOURCE)

    def test_real_chunk_exports_only_cross_chunk_contract(self):
        """ky_buff_render.lua should expose only the public interface on KH."""
        lua = self.load_module()
        lua.execute(
            """
            assert(kyohud._buff_render_initialized == true)
            assert(type(kyohud.DrawBuffCellFrame) == "function")
            assert(type(kyohud.DrawTimedBuffProgress) == "function")
            assert(type(kyohud.ResolveBuffState) == "function")
            assert(type(kyohud.IconForBuff) == "function")
            assert(type(kyohud.ColorForBuff) == "function")
            assert(type(kyohud.FrameColorForBuff) == "function")
            assert(type(kyohud.TitleForBuff) == "function")
            assert(type(kyohud.PresentationLabelForBuff) == "function")
            assert(type(kyohud.CompareBuffArrival) == "function")
            assert(type(kyohud.BuffLabel) == "function")
            assert(type(kyohud.EquippedPerkDeckEntry) == "function")
            assert(type(kyohud.IconForEquippedPerkDeck) == "function")
            assert(type(kyohud.ActiveEquippedPerkBuff) == "function")
            assert(type(kyohud.CurrentPerkDeckIds) == "function")
            assert(type(kyohud.ApplicationTime) == "function")
            assert(kyohud.BUFF_LABEL_TOP == "top")
            assert(kyohud.BUFF_LABEL_TIMER == "timer")
            assert(kyohud.HACKER_SPECIALIZATION_ID == 21)
            """
        )

    def test_wrong_context_does_not_initialize_module(self):
        """Module should not initialize when RequiredScript is wrong."""
        lua = self.load_module("lib/managers/playermanager")
        lua.execute(
            """
            assert(kyohud._buff_render_initialized == nil)
            assert(kyohud.DrawBuffCellFrame == nil)
            assert(kyohud.ResolveBuffState == nil)
            """
        )

    def test_repeated_load_is_idempotent(self):
        """Loading the module twice should not duplicate initialization."""
        lua = self.load_module()
        lua.execute(
            """
            first_draw = kyohud.DrawBuffCellFrame
            first_resolve = kyohud.ResolveBuffState
            """
        )
        lua.execute(BUFF_RENDER_SOURCE)
        lua.execute(
            """
            assert(rawequal(first_draw, kyohud.DrawBuffCellFrame))
            assert(rawequal(first_resolve, kyohud.ResolveBuffState))
            """
        )

    def test_mod_metadata_loads_module_once_after_core(self):
        """mod.txt should load ky_buff_render.lua after core.lua in hudmanagerpd2."""
        metadata = json.loads((ROOT / "mod.txt").read_text(encoding="utf-8-sig"))
        hooks = [
            hook
            for hook in metadata["hooks"]
            if hook["script_path"] == "lua/ky_buff_render.lua"
        ]
        self.assertEqual(
            [
                {
                    "hook_id": "lib/managers/hudmanagerpd2",
                    "script_path": "lua/ky_buff_render.lua",
                }
            ],
            hooks,
        )
        paths = [hook["script_path"] for hook in metadata["hooks"]]
        self.assertLess(paths.index("lua/core.lua"), paths.index("lua/ky_buff_render.lua"))

    def test_no_external_globals(self):
        """ky_buff_render.lua should not define external globals."""
        # Should not create new global tables or functions
        self.assertNotIn("BuffRenderGlobals", BUFF_RENDER_SOURCE)
        self.assertNotIn("BuffRenderModule", BUFF_RENDER_SOURCE)
        # All exports should go through the shared kyohud table (or its local alias KH)
        self.assertIn("KH.DrawBuffCellFrame", BUFF_RENDER_SOURCE)
        self.assertIn("KH.ResolveBuffState", BUFF_RENDER_SOURCE)

    def test_core_references_moved_functions_via_kh(self):
        """Core.lua should reference moved functions via KH interface."""
        # Core should call the public interface
        self.assertIn("KH.PresentationLabelForBuff", CORE_SOURCE)
        self.assertIn("KH.IconForBuff", CORE_SOURCE)
        self.assertIn("KH.ColorForBuff", CORE_SOURCE)
        self.assertIn("KH.TitleForBuff", CORE_SOURCE)
        self.assertIn("KH.FrameColorForBuff", CORE_SOURCE)
        self.assertIn("KH.EquippedPerkDeckEntry", CORE_SOURCE)
        self.assertIn("KH.ApplicationTime", CORE_SOURCE)
        self.assertIn("KH.HACKER_SPECIALIZATION_ID", CORE_SOURCE)


if __name__ == "__main__":
    unittest.main()
