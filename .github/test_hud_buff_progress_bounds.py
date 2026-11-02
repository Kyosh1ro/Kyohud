"""Buff progress polyline bounds -- test for explicit x/y/w/h in DrawTimedBuffProgress.

Diagnosed from log2026_11_02 lines 215/217/223: engine Polyline becomes full-screen
child because ky_buff_render.lua:321/328 DrawTimedBuffProgress omits x/y/w/h.

This test verifies the fix: polylines must have explicit tight bounds, not inherited
parent dimensions. Against current buggy code, this test FAILS (missing x/y/w/h).
After fix, this test PASSES.

Run: uv run --with lupa python -B -m unittest .github.test_hud_buff_progress_bounds -v
"""
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_buff_render_extraction import make_runtime
from test_hud_crew_acceptance import mounted

ROOT = Path(__file__).resolve().parents[1]
BUFF_RENDER_PATH = ROOT / "lua" / "ky_buff_render.lua"
BUFF_RENDER_SOURCE = BUFF_RENDER_PATH.read_text(encoding="utf-8-sig")
BUFF_PRESENTATION_PATH = ROOT / "lua" / "ky_buff_presentation.lua"
BUFF_PRESENTATION_SOURCE = BUFF_PRESENTATION_PATH.read_text(encoding="utf-8-sig")


class DrawTimedBuffProgressBoundsTest(unittest.TestCase):
    """Verify DrawTimedBuffProgress produces polylines with explicit tight bounds."""

    def test_polyline_explicit_bounds_and_world_points(self):
        """DrawTimedBuffProgress must pass explicit x/y/w/h to polyline config.

        Call with known parameters and verify:
        - Exactly 2 polylines (halo + stroke)
        - Each has explicit x/y/w/h (non-nil)
        - Tight bounding box (w<60, h<40 for input w=46, h=27)
        - Half stroke padding >= line_width/2
        - All points lie inside bounds
        - World points (origin + local) match expected perimeter trace
        - Widths 4 (halo) and 2 (stroke), alpha .16 and .8, layers 99 and 100
        """
        lua = make_runtime()

        # Set kyohud.clamp BEFORE loading modules
        lua.execute(
            """
            kyohud.clamp = function(v, lo, hi)
                return math.min(math.max(v, lo), hi)
            end
            """
        )

        # Load presentation first, then render
        lua.execute(BUFF_PRESENTATION_SOURCE)
        lua.execute(BUFF_RENDER_SOURCE)

        lua.execute(
            r"""
            -- Panel mock: w=1280, h=720
            local panel = {
                _w = 1280,
                _h = 720,
                _polylines = {},
            }
            function panel:w() return self._w end
            function panel:h() return self._h end

            -- Polyline constructor: copies points as numbers and config fields
            -- Defaults x/y=0, w/h=1280/720 ONLY when absent
            function panel:polyline(cfg)
                -- Capture whether config had explicit values BEFORE defaulting
                local x_explicit = (cfg.x ~= nil)
                local y_explicit = (cfg.y ~= nil)
                local w_explicit = (cfg.w ~= nil)
                local h_explicit = (cfg.h ~= nil)
                local pl = {
                    x = cfg.x,
                    y = cfg.y,
                    w = cfg.w,
                    h = cfg.h,
                    line_width = cfg.line_width,
                    color = cfg.color,
                    alpha = cfg.alpha,
                    layer = cfg.layer,
                    x_explicit = x_explicit,
                    y_explicit = y_explicit,
                    w_explicit = w_explicit,
                    h_explicit = h_explicit,
                    points = {},
                }
                -- Copy points as numbers (Diesel copies them)
                for i, pt in ipairs(cfg.points) do
                    pl.points[i] = Vector3(pt.x, pt.y, pt.z)
                end
                -- Apply defaults ONLY when absent
                if pl.x == nil then pl.x = 0 end
                if pl.y == nil then pl.y = 0 end
                if pl.w == nil then pl.w = self._w end
                if pl.h == nil then pl.h = self._h end
                table.insert(self._polylines, pl)
                return pl
            end

            -- Clear progress cache
            kyohud.RENDER_CACHES.progress = {}

            -- Call with: x=100, y=80, w=46, h=27, progress=1, color=white, alpha=0.8, layer=99
            kyohud.DrawTimedBuffProgress(panel, 100, 80, 46, 27, 1, Color.white, 0.8, 99)

            -- Capture results
            _polyline_count = #panel._polylines

            if _polyline_count >= 1 then
                local pl1 = panel._polylines[1]
                _pl1_x = pl1.x
                _pl1_y = pl1.y
                _pl1_w = pl1.w
                _pl1_h = pl1.h
                _pl1_line_width = pl1.line_width
                _pl1_alpha = pl1.alpha
                _pl1_layer = pl1.layer
                _pl1_x_explicit = pl1.x_explicit
                _pl1_y_explicit = pl1.y_explicit
                _pl1_w_explicit = pl1.w_explicit
                _pl1_h_explicit = pl1.h_explicit
                _pl1_points = {}
                for i, pt in ipairs(pl1.points) do
                    _pl1_points[i] = {x = pt.x, y = pt.y}
                end
            end

            if _polyline_count >= 2 then
                local pl2 = panel._polylines[2]
                _pl2_x = pl2.x
                _pl2_y = pl2.y
                _pl2_w = pl2.w
                _pl2_h = pl2.h
                _pl2_line_width = pl2.line_width
                _pl2_alpha = pl2.alpha
                _pl2_layer = pl2.layer
                _pl2_x_explicit = pl2.x_explicit
                _pl2_y_explicit = pl2.y_explicit
                _pl2_w_explicit = pl2.w_explicit
                _pl2_h_explicit = pl2.h_explicit
                _pl2_points = {}
                for i, pt in ipairs(pl2.points) do
                    _pl2_points[i] = {x = pt.x, y = pt.y}
                end
            end
            """
        )

        g = lua.globals()

        # Exactly 2 polylines
        self.assertEqual(int(g._polyline_count), 2, "must produce exactly 2 polylines")

        # Both polylines must have explicit x/y/w/h (non-nil)
        self.assertTrue(bool(g._pl1_x_explicit), "polyline 1 must have explicit x")
        self.assertTrue(bool(g._pl1_y_explicit), "polyline 1 must have explicit y")
        self.assertTrue(bool(g._pl1_w_explicit), "polyline 1 must have explicit w")
        self.assertTrue(bool(g._pl1_h_explicit), "polyline 1 must have explicit h")
        self.assertTrue(bool(g._pl2_x_explicit), "polyline 2 must have explicit x")
        self.assertTrue(bool(g._pl2_y_explicit), "polyline 2 must have explicit y")
        self.assertTrue(bool(g._pl2_w_explicit), "polyline 2 must have explicit w")
        self.assertTrue(bool(g._pl2_h_explicit), "polyline 2 must have explicit h")

        # Tight bounding box: w<60, h<40 (for input w=46, h=27)
        pl1_w = float(g._pl1_w)
        pl1_h = float(g._pl1_h)
        self.assertLess(pl1_w, 60, f"polyline 1 width must be <60, got {pl1_w}")
        self.assertLess(pl1_h, 40, f"polyline 1 height must be <40, got {pl1_h}")
        self.assertGreater(pl1_w, 0, f"polyline 1 width must be positive, got {pl1_w}")
        self.assertGreater(pl1_h, 0, f"polyline 1 height must be positive, got {pl1_h}")

        pl2_w = float(g._pl2_w)
        pl2_h = float(g._pl2_h)
        self.assertLess(pl2_w, 60, f"polyline 2 width must be <60, got {pl2_w}")
        self.assertLess(pl2_h, 40, f"polyline 2 height must be <40, got {pl2_h}")
        self.assertGreater(pl2_w, 0, f"polyline 2 width must be positive, got {pl2_w}")
        self.assertGreater(pl2_h, 0, f"polyline 2 height must be positive, got {pl2_h}")

        # Each point's LOCAL px/py must respect line_width padding
        pl1_line_width = float(g._pl1_line_width)
        pl2_line_width = float(g._pl2_line_width)
        pl1_x = float(g._pl1_x)
        pl1_y = float(g._pl1_y)
        pl1_w = float(g._pl1_w)
        pl1_h = float(g._pl1_h)
        pl2_x = float(g._pl2_x)
        pl2_y = float(g._pl2_y)
        pl2_w = float(g._pl2_w)
        pl2_h = float(g._pl2_h)

        for i in range(1, len(g._pl1_points) + 1):
            pt = g._pl1_points[i]
            px = float(pt["x"])
            py = float(pt["y"])
            self.assertGreaterEqual(px, pl1_line_width / 2.0,
                f"polyline 1 point {i} local px={px} < line_width/2={pl1_line_width / 2.0}")
            self.assertLessEqual(px, pl1_w - pl1_line_width / 2.0,
                f"polyline 1 point {i} local px={px} > w-line_width/2={pl1_w - pl1_line_width / 2.0}")
            self.assertGreaterEqual(py, pl1_line_width / 2.0,
                f"polyline 1 point {i} local py={py} < line_width/2={pl1_line_width / 2.0}")
            self.assertLessEqual(py, pl1_h - pl1_line_width / 2.0,
                f"polyline 1 point {i} local py={py} > h-line_width/2={pl1_h - pl1_line_width / 2.0}")

        for i in range(1, len(g._pl2_points) + 1):
            pt = g._pl2_points[i]
            px = float(pt["x"])
            py = float(pt["y"])
            self.assertGreaterEqual(px, pl2_line_width / 2.0,
                f"polyline 2 point {i} local px={px} < line_width/2={pl2_line_width / 2.0}")
            self.assertLessEqual(px, pl2_w - pl2_line_width / 2.0,
                f"polyline 2 point {i} local px={px} > w-line_width/2={pl2_w - pl2_line_width / 2.0}")
            self.assertGreaterEqual(py, pl2_line_width / 2.0,
                f"polyline 2 point {i} local py={py} < line_width/2={pl2_line_width / 2.0}")
            self.assertLessEqual(py, pl2_h - pl2_line_width / 2.0,
                f"polyline 2 point {i} local py={py} > h-line_width/2={pl2_h - pl2_line_width / 2.0}")

        # All points lie inside bounds
        for i in range(1, len(g._pl1_points) + 1):
            pt = g._pl1_points[i]
            px = float(pt["x"])
            py = float(pt["y"])
            world_x = pl1_x + px
            world_y = pl1_y + py
            self.assertGreaterEqual(world_x, pl1_x, f"polyline 1 point {i} x={world_x} < bounds x={pl1_x}")
            self.assertLessEqual(world_x, pl1_x + pl1_w, f"polyline 1 point {i} x={world_x} > bounds x+w={pl1_x + pl1_w}")
            self.assertGreaterEqual(world_y, pl1_y, f"polyline 1 point {i} y={world_y} < bounds y={pl1_y}")
            self.assertLessEqual(world_y, pl1_y + pl1_h, f"polyline 1 point {i} y={world_y} > bounds y+h={pl1_y + pl1_h}")

        for i in range(1, len(g._pl2_points) + 1):
            pt = g._pl2_points[i]
            px = float(pt["x"])
            py = float(pt["y"])
            world_x = pl2_x + px
            world_y = pl2_y + py
            self.assertGreaterEqual(world_x, pl2_x, f"polyline 2 point {i} x={world_x} < bounds x={pl2_x}")
            self.assertLessEqual(world_x, pl2_x + pl2_w, f"polyline 2 point {i} x={world_x} > bounds x+w={pl2_x + pl2_w}")
            self.assertGreaterEqual(world_y, pl2_y, f"polyline 2 point {i} y={world_y} < bounds y={pl2_y}")
            self.assertLessEqual(world_y, pl2_y + pl2_h, f"polyline 2 point {i} y={world_y} > bounds y+h={pl2_y + pl2_h}")

        # World points origin+local exactly [(123,80),(146,80),(146,107),(100,107),(100,80),(123,80)]
        expected_points = [(123.0, 80.0), (146.0, 80.0), (146.0, 107.0), (100.0, 107.0), (100.0, 80.0), (123.0, 80.0)]

        # Polyline 1
        self.assertEqual(len(g._pl1_points), len(expected_points), f"polyline 1 must have {len(expected_points)} points")
        for i, (exp_x, exp_y) in enumerate(expected_points, start=1):
            pt = g._pl1_points[i]
            world_x = pl1_x + float(pt["x"])
            world_y = pl1_y + float(pt["y"])
            self.assertAlmostEqual(world_x, exp_x, places=5, msg=f"polyline 1 point {i} world x={world_x} != expected {exp_x}")
            self.assertAlmostEqual(world_y, exp_y, places=5, msg=f"polyline 1 point {i} world y={world_y} != expected {exp_y}")

        # Polyline 2
        self.assertEqual(len(g._pl2_points), len(expected_points), f"polyline 2 must have {len(expected_points)} points")
        for i, (exp_x, exp_y) in enumerate(expected_points, start=1):
            pt = g._pl2_points[i]
            world_x = pl2_x + float(pt["x"])
            world_y = pl2_y + float(pt["y"])
            self.assertAlmostEqual(world_x, exp_x, places=5, msg=f"polyline 2 point {i} world x={world_x} != expected {exp_x}")
            self.assertAlmostEqual(world_y, exp_y, places=5, msg=f"polyline 2 point {i} world y={world_y} != expected {exp_y}")

        # Widths 4 and 2, alpha .16 and .8, layers 99/100
        self.assertAlmostEqual(pl1_line_width, 4.0, places=5, msg=f"polyline 1 line_width must be 4, got {pl1_line_width}")
        self.assertAlmostEqual(pl2_line_width, 2.0, places=5, msg=f"polyline 2 line_width must be 2, got {pl2_line_width}")
        self.assertAlmostEqual(float(g._pl1_alpha), 0.16, places=5, msg=f"polyline 1 alpha must be .16, got {g._pl1_alpha}")
        self.assertAlmostEqual(float(g._pl2_alpha), 0.8, places=5, msg=f"polyline 2 alpha must be .8, got {g._pl2_alpha}")
        self.assertEqual(int(g._pl1_layer), 99, msg=f"polyline 1 layer must be 99, got {g._pl1_layer}")
        self.assertEqual(int(g._pl2_layer), 100, msg=f"polyline 2 layer must be 100, got {g._pl2_layer}")


class RuntimeIntegrationBuffProgressCrewConflictTest(unittest.TestCase):
    """Runtime integration: DrawTimedBuffProgress polylines must not fullscreen over crew.

    Uses mounted crew acceptance environment. Creates kyohud._panel fullsize 1920x1080.
    Polyline mock calls rect with defaults for x/y/w/h (mimics Diesel).
    Calls actual DrawTimedBuffProgress(900,100,46,27,1) which creates 2 polyline children.
    Currently (buggy): polylines inherit 1920x1080 => overlap crew => FAIL.
    After fix: polylines have explicit tight bounds => no overlap => crew visible.
    Then test conflict detection with overlapping rects and recovery.
    """

    def test_runtime_integration_buff_progress_crew_conflict(self):
        lua = mounted()

        lua.execute('''
            kyohud.clamp = function(v, lo, hi)
                return math.min(math.max(v, lo), hi)
            end
            kyohud.RENDER_CACHES = {
                progress = {},
                buff_cell_bg = {},
                edge_points = {},
                buff_cell_footer = {},
                buff_cell_outline = {},
            }
            Vector3 = function(x, y, z)
                return {x = x, y = y, z = z}
            end
        ''')
        lua.globals().RequiredScript = "lib/managers/hudmanagerpd2"

        lua.execute(BUFF_PRESENTATION_SOURCE)
        lua.execute(BUFF_RENDER_SOURCE)

        lua.execute('''
            kyohud._panel = panel_double:panel({name='kyohud_combat_panel'})
            kyohud._panel:set_shape(0, 0, 1920, 1080)

            kyohud._panel.polyline = function(self, cfg)
                return self:rect({
                    x = cfg.x or 0,
                    y = cfg.y or 0,
                    w = cfg.w or self:w(),
                    h = cfg.h or self:h(),
                    alpha = cfg.alpha,
                    visible = true,
                })
            end

            _orig_root = C._root
            _orig_card = C._cards[1]
            _orig_card_root = _orig_card.root
        ''')

        lua.execute('''
            kyohud.DrawTimedBuffProgress(kyohud._panel, 900, 100, 46, 27, 1, Color(1, 1, 1), 0.8, 99)
            RT:update(managers.hud, 2, 0.05)
            _visible_at_2 = C._root:visible()
            _cert_at_2 = C:_verify_render()
        ''')

        g = lua.globals()
        self.assertIs(g._visible_at_2, True, "crew must be visible at t=2 (outside polylines)")
        self.assertIs(g._cert_at_2, True, "crew must be certified at t=2")

        lua.execute('''
            local lc = C._layout_cache
            kyohud.DrawTimedBuffProgress(kyohud._panel, lc.x + 5, lc.y + 5, 46, 27, 1, Color(1, 1, 1), 0.8, 99)
            RT:update(managers.hud, 2.6, 0.05)
            _hidden_at_2_6 = not C._root:visible()
        ''')

        g = lua.globals()
        self.assertIs(g._hidden_at_2_6, True, "crew must be hidden at t=2.6 (inside polylines overlap)")

        lua.execute('''
            local children = kyohud._panel:children()
            for _, child in pairs(children) do
                child:set_visible(false)
            end
            RT:update(managers.hud, 3.2, 0.05)
            _cert_at_3_2 = C:_verify_render()
            _same_root_3_2 = C._root == _orig_root
            _same_card_3_2 = C._cards[1].root == _orig_card_root
        ''')

        g = lua.globals()
        self.assertIs(g._cert_at_3_2, True, "crew must be certified at t=3.2 after hiding inner polylines")
        self.assertIs(g._same_root_3_2, True, "same crew root at t=3.2")
        self.assertIs(g._same_card_3_2, True, "same card root at t=3.2")

        lua.execute('''
            local lc = C._layout_cache
            _producer = kyohud._panel:rect({
                x = lc.x + 5,
                y = lc.y + 5,
                w = 46,
                h = 27,
                color = Color(1, 1, 1),
                alpha = 0.5,
            })
            RT:update(managers.hud, 3.8, 0.05)
            _hidden_at_3_8 = not C._root:visible()
        ''')

        g = lua.globals()
        self.assertIs(g._hidden_at_3_8, True, "crew must be hidden at t=3.8 (rect overlaps)")

        lua.execute('''
            _producer:set_visible(false)
            RT:update(managers.hud, 4.4, 0.05)
            _cert_at_4_4 = C:_verify_render()
            _same_root_4_4 = C._root == _orig_root
            _same_card_4_4 = C._cards[1].root == _orig_card_root
        ''')

        g = lua.globals()
        self.assertIs(g._cert_at_4_4, True, "crew must be certified at t=4.4 after hiding rect")
        self.assertIs(g._same_root_4_4, True, "same crew root at t=4.4")
        self.assertIs(g._same_card_4_4, True, "same card root at t=4.4")


if __name__ == "__main__":
    unittest.main(verbosity=2)
