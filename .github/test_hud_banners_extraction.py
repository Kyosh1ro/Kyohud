"""Regression tests for the HUD banner extraction."""

import json
import unittest
from pathlib import Path

from lupa.luajit21 import LuaRuntime


ROOT = Path(__file__).resolve().parents[1]
BANNERS_PATH = ROOT / "lua" / "ky_hud_banners.lua"
BANNERS_SOURCE = BANNERS_PATH.read_text(encoding="utf-8-sig")


def make_runtime(required_script="lib/managers/hudmanagerpd2"):
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
        Color.black = Color(0, 0, 0)
        kyohud = {RENDER_CACHES = {tactical_bg = {}}}
        Kyosh1roHUD = kyohud
        """
    )
    lua.globals().RequiredScript = required_script
    return lua


class HudBannersExtractionTests(unittest.TestCase):
    def load_module(self, required_script="lib/managers/hudmanagerpd2"):
        lua = make_runtime(required_script)
        lua.execute(BANNERS_SOURCE)
        return lua

    def test_real_chunk_exports_only_cross_chunk_contract(self):
        lua = self.load_module()
        lua.execute(
            """
            assert(kyohud._hud_banners_initialized == true)
            assert(kyohud.BANNER_FRAME_EXTENSION == 4)
            assert(kyohud.BANNER_FRAME_STYLE.inset == 2)
            assert(kyohud.BANNER_FRAME_STYLE.glow_alpha == 0.16)
            assert(kyohud.BANNER_FRAME_STYLE.brackets.extension == 4)
            assert(kyohud.MAX_BANNER_QUEUE == 4)
            assert(#kyohud.DEBUG_BANNER_PREVIEWS == 28)
            assert(type(kyohud.DrawTacticalFrame) == "function")
            assert(type(kyohud.BannerPriority) == "function")
            assert(type(kyohud.BannerQueueInsertIndex) == "function")
            assert(kyohud.BANNER_PRIORITIES == nil)
            assert(kyohud.DrawCornerBrackets == nil)
            """
        )

    def test_wrong_context_does_not_initialize_module(self):
        lua = self.load_module("lib/managers/playermanager")
        lua.execute(
            """
            assert(kyohud._hud_banners_initialized == nil)
            assert(kyohud.DrawTacticalFrame == nil)
            assert(kyohud.BannerPriority == nil)
            """
        )

    def test_repeated_load_is_idempotent(self):
        lua = self.load_module()
        lua.execute(
            """
            first_draw = kyohud.DrawTacticalFrame
            first_previews = kyohud.DEBUG_BANNER_PREVIEWS
            """
        )
        lua.execute(BANNERS_SOURCE)
        lua.execute(
            """
            assert(rawequal(first_draw, kyohud.DrawTacticalFrame))
            assert(rawequal(first_previews, kyohud.DEBUG_BANNER_PREVIEWS))
            """
        )

    def test_priority_and_stable_queue_insertion(self):
        lua = self.load_module()
        lua.execute(
            """
            assert(kyohud.BannerPriority(nil) == 0)
            assert(kyohud.BannerPriority({kind = "unknown"}) == 0)
            assert(kyohud.BannerPriority({kind = "dozer"}) == 1)
            assert(kyohud.BannerPriority({kind = "boss"}) == 2)

            local queue = {
                {kind = "boss", marker = "first boss"},
                {kind = "dozer", marker = "first dozer"},
                {kind = "dozer", marker = "second dozer"},
            }
            assert(kyohud.BannerQueueInsertIndex(queue, 2) == 2)
            assert(kyohud.BannerQueueInsertIndex(queue, 1) == 4)
            assert(kyohud.BannerQueueInsertIndex(queue, 0) == 4)
            """
        )

    def test_real_core_queue_is_bounded_sorted_and_preempts(self):
        from test_combat_state import CombatStateTests

        fixture = CombatStateTests(methodName="runTest")
        fixture.setUp()
        fixture.lua.execute(
            """
            kyohud._banner_queue = {}
            kyohud._special_kill_banner = nil

            kyohud:_enqueue_special_banner({kind = "dozer", marker = "d1"})
            kyohud:_enqueue_special_banner({kind = "dozer", marker = "d2"})
            kyohud:_enqueue_special_banner({kind = "dozer", marker = "d3"})
            kyohud:_enqueue_special_banner({kind = "dozer", marker = "d4"})
            kyohud:_enqueue_special_banner({kind = "dozer", marker = "discarded"})
            assert(#kyohud._banner_queue == 4)
            assert(kyohud._banner_queue[4].marker == "d4")

            kyohud:_enqueue_special_banner({kind = "boss", marker = "boss"})
            assert(#kyohud._banner_queue == 4)
            assert(kyohud._banner_queue[1].marker == "boss")
            assert(kyohud._banner_queue[2].marker == "d1")
            assert(kyohud._banner_queue[4].marker == "d3")

            kyohud._banner_queue = {}
            kyohud:_start_special_banner(10, {kind = "dozer", marker = "active"}, false)
            kyohud:_show_special_banner(11, {kind = "boss", marker = "replacement"}, false)
            assert(kyohud._special_kill_banner.marker == "replacement")
            assert(#kyohud._banner_queue == 1)
            assert(kyohud._banner_queue[1].marker == "active")
            """
        )

    def test_tactical_frame_preserves_diesel_primitives_and_cache(self):
        lua = self.load_module()
        lua.execute(
            """
            local panel = {rects = {}, gradients = {}}
            function panel:rect(params)
                table.insert(self.rects, params)
            end
            function panel:gradient(params)
                table.insert(self.gradients, params)
            end

            kyohud.DrawTacticalFrame(
                panel, 100, 50, 200, 40, Color(1, 0.5, 0.25), 0.5, 100,
                kyohud.BANNER_FRAME_STYLE
            )

            assert(#panel.gradients == 1)
            assert(#panel.rects == 20)
            assert(panel.gradients[1].x == 102)
            assert(panel.gradients[1].y == 52)
            assert(panel.gradients[1].w == 196)
            assert(panel.gradients[1].h == 36)
            assert(panel.gradients[1].layer == 100)
            assert(kyohud.RENDER_CACHES.tactical_bg[50] ~= nil)

            assert(panel.rects[1].x == 118)
            assert(panel.rects[1].y == 49)
            assert(panel.rects[1].w == 40)
            assert(panel.rects[1].h == 3)
            assert(panel.rects[1].layer == 101)

            assert(panel.rects[13].x == 96)
            assert(panel.rects[13].y == 46)
            assert(panel.rects[13].w == 16)
            assert(panel.rects[13].h == 1)
            assert(panel.rects[13].layer == 102)
            """
        )

    def test_mod_metadata_loads_module_once_after_core(self):
        metadata = json.loads((ROOT / "mod.txt").read_text(encoding="utf-8-sig"))
        hooks = [
            hook
            for hook in metadata["hooks"]
            if hook["script_path"] == "lua/ky_hud_banners.lua"
        ]
        self.assertEqual(
            [
                {
                    "hook_id": "lib/managers/hudmanagerpd2",
                    "script_path": "lua/ky_hud_banners.lua",
                }
            ],
            hooks,
        )
        paths = [hook["script_path"] for hook in metadata["hooks"]]
        self.assertLess(paths.index("lua/core.lua"), paths.index("lua/ky_hud_banners.lua"))
        self.assertLess(
            paths.index("lua/ky_heist_score.lua"),
            paths.index("lua/ky_hud_banners.lua"),
        )

    def test_killfeed_chevron_gap_remains_in_core(self):
        core_source = (ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig")
        self.assertIn("local BANNER_CHEVRON_TEXT_GAP = 5", core_source)
        self.assertNotIn("BANNER_CHEVRON_TEXT_GAP", BANNERS_SOURCE)


if __name__ == "__main__":
    unittest.main()
