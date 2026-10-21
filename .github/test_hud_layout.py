"""LOT1 — hud/layout.lua: pure geometry behavior regressions.

Run: uv run --with lupa python -B -m unittest discover -s .github -p test_hud_layout.py -v
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / "lua" / "hud" / "layout.lua"


def _make_lua():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute('''
        _hook_calls = {add=0, post=0, pre=0}
        Hooks = {}
        function Hooks:PostHook(class, method, id, fn)
            _hook_calls.post = _hook_calls.post + 1
        end
        function Hooks:PreHook(class, method, id, fn)
            _hook_calls.pre = _hook_calls.pre + 1
        end
        function Hooks:Add(event, id, callback)
            _hook_calls.add = _hook_calls.add + 1
        end
        function log(...) end
    ''')
    with open(LAYOUT_PATH, "r", encoding="utf-8-sig") as f:
        lua.execute(f.read())
    return lua


class HudLayoutInitTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(LAYOUT_PATH.is_file(), f"lua/hud/layout.lua must exist at {LAYOUT_PATH}")
        self.lua = _make_lua()

    def test_globals_and_alias(self):
        self.lua.execute("_a = kyohud ~= nil; _b = kyohud.hud.layout ~= nil; _c = Kyosh1roHUD ~= nil; _d = (kyohud == Kyosh1roHUD)")
        g = self.lua.globals()
        self.assertTrue(bool(g._a))
        self.assertTrue(bool(g._b))
        self.assertTrue(bool(g._c))
        self.assertTrue(bool(g._d))

    def test_no_hooks_side_effects(self):
        g = self.lua.globals()
        self.assertEqual(int(g._hook_calls.add), 0)
        self.assertEqual(int(g._hook_calls.post), 0)
        self.assertEqual(int(g._hook_calls.pre), 0)


class HudLayoutResolveTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(LAYOUT_PATH.is_file())
        self.lua = _make_lua()

    def test_uniform_scale(self):
        cases = [
            (1920, 1080, 1.0, 1.0),
            (3840, 2160, 1.0, 2.0),
            (960, 540, 1.0, 0.5),
            (1280, 720, 1.0, 1280 / 1920),
            (2560, 1080, 1.0, 1.0),
            (800, 600, 1.0, min(800 / 1920, 600 / 1080)),
        ]
        for w, h, scale, expected in cases:
            with self.subTest(w=w, h=h):
                self.lua.execute(f"_u = kyohud.hud.layout.resolve({w}, {h}, {scale}).uniform_scale")
                self.assertAlmostEqual(float(self.lua.globals()._u), expected, places=5)

    def test_aspect_ratio_scale(self):
        cases = [
            (1920, 1200, min(1920 / 1920, 1200 / 1080)),
            (1024, 768, min(1024 / 1920, 768 / 1080)),
        ]
        for w, h, expected in cases:
            with self.subTest(w=w, h=h):
                self.lua.execute(f"_u = kyohud.hud.layout.resolve({w}, {h}, 1.0).uniform_scale")
                self.assertAlmostEqual(float(self.lua.globals()._u), expected, places=5)

    def test_user_scale_clamped(self):
        cases = [
            (0.1, 0.5),
            (10.0, 2.0),
        ]
        for inp, expected in cases:
            with self.subTest(inp=inp):
                self.lua.execute(f"_s = kyohud.hud.layout.resolve(1920, 1080, {inp}).scale")
                self.assertAlmostEqual(float(self.lua.globals()._s), expected, places=5)

    def test_numeric_string_scale_coerced(self):
        self.lua.execute('_s = kyohud.hud.layout.resolve(1920, 1080, "1.5").scale')
        self.assertAlmostEqual(float(self.lua.globals()._s), 1.5, places=5)

    def test_invalid_dims(self):
        cases = [
            ("0, 1080", "zero_w"),
            ("1920, 0", "zero_h"),
            ("-100, 1080", "neg_w"),
            ("1920, -100", "neg_h"),
            ("0/0, 1080", "nan_w"),
            ("1920, 0/0", "nan_h"),
            ("math.huge, 1080", "inf_w"),
            ("1920, math.huge", "inf_h"),
            ("nil, 1080", "nil_w"),
            ("1920, nil", "nil_h"),
        ]
        for args, label in cases:
            with self.subTest(label=label):
                self.lua.execute(f"_v = kyohud.hud.layout.resolve({args}, 1.0).valid")
                self.assertFalse(bool(self.lua.globals()._v))

    def test_invalid_dims_zero_fields(self):
        self.lua.execute('''
            local g = kyohud.hud.layout.resolve(0, 0, 1.0)
            _w=g.width; _h=g.height; _u=g.uniform_scale; _ax=g.available_x; _ay=g.available_y
        ''')
        g = self.lua.globals()
        for name in ("_w", "_h", "_u", "_ax", "_ay"):
            self.assertEqual(float(getattr(g, name)), 0)

    def test_nil_width_zero(self):
        self.lua.execute("local g=kyohud.hud.layout.resolve(nil,1080,1.0); _v=g.valid; _w=g.width")
        g = self.lua.globals()
        self.assertFalse(bool(g._v))
        self.assertEqual(float(g._w), 0)

    def test_nil_height_zero(self):
        self.lua.execute("local g=kyohud.hud.layout.resolve(1920,nil,1.0); _v=g.valid; _h=g.height")
        g = self.lua.globals()
        self.assertFalse(bool(g._v))
        self.assertEqual(float(g._h), 0)

    def test_scale_defaults(self):
        with self.subTest(case="nil"):
            self.lua.execute("_s = kyohud.hud.layout.resolve(1920, 1080, nil).scale")
            self.assertAlmostEqual(float(self.lua.globals()._s), 1.0, places=5)
        with self.subTest(case="zero"):
            self.lua.execute("_s = kyohud.hud.layout.resolve(1920, 1080, 0).scale")
            self.assertAlmostEqual(float(self.lua.globals()._s), 1.0, places=5)


class HudLayoutResolveBoundsTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(LAYOUT_PATH.is_file())
        self.lua = _make_lua()

    def test_available_nonnegative(self):
        self.lua.execute("local g=kyohud.hud.layout.resolve(1,1,1.0); _ax=g.available_x; _ay=g.available_y")
        g = self.lua.globals()
        self.assertGreaterEqual(float(g._ax), 0)
        self.assertGreaterEqual(float(g._ay), 0)

    def test_margins_in_panel_units(self):
        self.lua.execute("local g=kyohud.hud.layout.resolve(1920,1080,1.0); _mx=g.margin_x; _my=g.margin_y")
        g = self.lua.globals()
        self.assertAlmostEqual(float(g._mx), 1920 * 0.02, places=2)
        self.assertAlmostEqual(float(g._my), 1080 * 0.02, places=2)

    def test_aba_no_drift(self):
        self.lua.execute('''
            local L = kyohud.hud.layout
            local g1 = L.resolve(1920, 1080, 1.0)
            local _tmp = L.resolve(100, 100, 2.0)
            local g3 = L.resolve(1920, 1080, 1.0)
            _u1=g1.uniform_scale; _ax1=g1.available_x; _ay1=g1.available_y
            _u3=g3.uniform_scale; _ax3=g3.available_x; _ay3=g3.available_y
        ''')
        g = self.lua.globals()
        self.assertAlmostEqual(float(g._u1), float(g._u3), places=10)
        self.assertAlmostEqual(float(g._ax1), float(g._ax3), places=10)
        self.assertAlmostEqual(float(g._ay1), float(g._ay3), places=10)


class HudLayoutAnchorRectTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(LAYOUT_PATH.is_file())
        self.lua = _make_lua()

    def _anchor(self, code):
        self.lua.execute(code)
        return self.lua.globals()

    def test_anchor_positions(self):
        with self.subTest(pos="center"):
            g = self._anchor('''
                local L=kyohud.hud.layout; local geom=L.resolve(1920,1080,1.0)
                local r=L.anchor_rect(geom,50,50,200,100)
                _cx=r.x+r.w*0.5; _cy=r.y+r.h*0.5
            ''')
            self.assertAlmostEqual(float(g._cx), 960, places=1)
            self.assertAlmostEqual(float(g._cy), 540, places=1)
        with self.subTest(pos="top_left"):
            g = self._anchor('''
                local L=kyohud.hud.layout; local geom=L.resolve(1920,1080,1.0)
                local r=L.anchor_rect(geom,0,0,200,100)
                _x=r.x; _y=r.y
            ''')
            self.assertAlmostEqual(float(g._x), 1920 * 0.02, places=1)
            self.assertAlmostEqual(float(g._y), 1080 * 0.02, places=1)
        with self.subTest(pos="bottom_right"):
            g = self._anchor('''
                local L=kyohud.hud.layout; local geom=L.resolve(1920,1080,1.0)
                local r=L.anchor_rect(geom,100,100,200,100)
                _right=r.x+r.w; _bottom=r.y+r.h
            ''')
            self.assertAlmostEqual(float(g._right), 1920 - 1920 * 0.02, places=1)
            self.assertAlmostEqual(float(g._bottom), 1080 - 1080 * 0.02, places=1)

    def test_anchor_invalid_geom_zero_rect(self):
        g = self._anchor('''
            local r=kyohud.hud.layout.anchor_rect(nil,50,50,200,100)
            _x=r.x; _y=r.y; _w=r.w; _h=r.h
        ''')
        for f in ("_x", "_y", "_w", "_h"):
            self.assertEqual(float(getattr(g, f)), 0)

    def test_anchor_clamped_finite_nonnegative(self):
        g = self._anchor('''
            local L=kyohud.hud.layout; local geom=L.resolve(1920,1080,1.0)
            local r=L.anchor_rect(geom,50,50,-100,-50)
            _w=r.w; _h=r.h
        ''')
        self.assertGreaterEqual(float(g._w), 0)
        self.assertGreaterEqual(float(g._h), 0)

    def test_anchor_dimensions_scaled(self):
        cases = [
            ("3840,2160,1.0", 200, 100, 200 * 2.0, 100 * 2.0),
            ("1920,1080,1.5", 200, 100, 200 * 1.0 * 1.5, 100 * 1.0 * 1.5),
            ("3840,2160,1.5", 200, 100, 200 * 2.0 * 1.5, 100 * 2.0 * 1.5),
        ]
        for args, rw, rh, ew, eh in cases:
            with self.subTest(args=args):
                g = self._anchor(f'''
                    local L=kyohud.hud.layout; local geom=L.resolve({args})
                    local r=L.anchor_rect(geom,50,50,{rw},{rh})
                    _w=r.w; _h=r.h
                ''')
                self.assertAlmostEqual(float(g._w), ew, places=1)
                self.assertAlmostEqual(float(g._h), eh, places=1)

    def test_anchor_large_ref_clamped(self):
        g = self._anchor('''
            local L=kyohud.hud.layout; local geom=L.resolve(1920,1080,1.0)
            local r=L.anchor_rect(geom,50,50,10000,10000)
            _w=r.w; _h=r.h; _ax=geom.available_x; _ay=geom.available_y
        ''')
        self.assertLessEqual(float(g._w), float(g._ax) + 0.01)
        self.assertLessEqual(float(g._h), float(g._ay) + 0.01)

    def test_anchor_no_input_mutation(self):
        g = self._anchor('''
            local L=kyohud.hud.layout; local geom=L.resolve(1920,1080,1.0)
            local bw=geom.available_x; local bh=geom.available_y
            L.anchor_rect(geom,50,50,200,100)
            _mw = bw ~= geom.available_x; _mh = bh ~= geom.available_y
        ''')
        self.assertFalse(bool(g._mw))
        self.assertFalse(bool(g._mh))

    def test_anchor_nan_safe(self):
        cases = [
            ("0/0, 50", "nan_x"),
            ("50, 0/0", "nan_y"),
        ]
        for args, label in cases:
            with self.subTest(label=label):
                g = self._anchor(f'''
                    local L=kyohud.hud.layout; local geom=L.resolve(1920,1080,1.0)
                    local r=L.anchor_rect(geom,{args},200,100)
                    _fx=math.abs(r.x)<1e9; _fy=math.abs(r.y)<1e9
                ''')
                self.assertTrue(bool(g._fx))
                self.assertTrue(bool(g._fy))

    def test_anchor_extreme_ref_dims_safe(self):
        cases = [
            ("math.huge, math.huge", "inf"),
            ("0/0, 0/0", "nan"),
        ]
        for args, label in cases:
            with self.subTest(label=label):
                g = self._anchor(f'''
                    local L=kyohud.hud.layout; local geom=L.resolve(1920,1080,1.0)
                    local r=L.anchor_rect(geom,50,50,{args})
                    _fw=math.abs(r.w)<1e9; _fh=math.abs(r.h)<1e9
                ''')
                self.assertTrue(bool(g._fw))
                self.assertTrue(bool(g._fh))

    def test_anchor_aba_rect_no_drift(self):
        g = self._anchor('''
            local L=kyohud.hud.layout; local geom=L.resolve(1920,1080,1.0)
            local r1=L.anchor_rect(geom,50,50,200,100)
            local _tmp=L.anchor_rect(geom,99,99,50,50)
            local r3=L.anchor_rect(geom,50,50,200,100)
            _x1=r1.x; _y1=r1.y; _x3=r3.x; _y3=r3.y
        ''')
        self.assertAlmostEqual(float(g._x1), float(g._x3), places=10)
        self.assertAlmostEqual(float(g._y1), float(g._y3), places=10)


if __name__ == "__main__":
    unittest.main()
