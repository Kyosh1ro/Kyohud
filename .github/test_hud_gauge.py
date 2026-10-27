"""Gauge -- hud/components/gauge.lua: health/armor dual-bar renderer (RED tracer).

Six small tests against lua/hud/components/gauge.lua via real lupa.luajit21.

Interface under test:
  kyohud.hud.gauge.new(parent, name) -> instance
    instance.root, instance.health_fill, instance.armor_fill,
    instance.markers[1..3], instance.health_text, instance.armor_text
    :set_geometry(x, y, w, h)
    :render(health, armor, mode, multiplier)
    :verify()
    :destroy()

health metrics: {current, total, ratio, valid, provenance}
armor metrics:  {current, total, ratio, valid, provenance}

render modes:
  "percentage" -> rounded(ratio*100) .. "%"  (or "0%" when valid but ratio=0)
                  "--" when invalid (total=0: ratio unknown, not 0)
  "real"       -> rounded(current*multiplier) ONLY when provenance=="local"
                  else "--"
  missing/invalid/non-finite multiplier in real -> "--", no invented conversion.

Markers at x = 0.3/0.5/0.75 * w within health row only.
Native multiplier=10 verified at blackmarketgui.lua:5335-5353 /
guitweakdata.lua:726 stats_present_multiplier=10; gauge receives it explicitly,
no managers/tweak_data access.

RED: lua/hud/components/gauge.lua does not exist yet. Tests that need it
fail with assertTrue(path.exists()), not FileNotFoundError.
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
GAUGE_PATH = ROOT / "lua" / "hud" / "components" / "gauge.lua"

STUBS = '''
kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end
kyohud.hud = kyohud.hud or {}
if not math.round then
    function math.round(v) return math.floor(v + 0.5) end
end

-- Diesel-shaped primitive mock: unique names, proper parent/child refs,
-- constructor helpers respecting config, text() getter overload, parent(),
-- remove kills subtree only, alive, Color callable mock only.
-- No production gauge logic here.

local _alloc = 0

local function _uniq(base)
    _alloc = _alloc + 1
    return (base or "p") .. "_" .. _alloc
end

local function _apply(p, cfg)
    if type(cfg) ~= "table" then return end
    if cfg.x ~= nil then p._x = cfg.x end
    if cfg.y ~= nil then p._y = cfg.y end
    if cfg.w ~= nil then p._w = cfg.w end
    if cfg.h ~= nil then p._h = cfg.h end
    if cfg.text ~= nil then p._text = tostring(cfg.text) end
    if cfg.font_size ~= nil then p._font_size = cfg.font_size end
    if cfg.visible ~= nil then p._visible = cfg.visible end
    if cfg.color ~= nil then p._color = cfg.color end
end

local Panel = {}
Panel.__index = Panel

local function _make(name, kind)
    _alloc = _alloc + 1
    local p = setmetatable({}, Panel)
    p._name = name or ("_anon_" .. _alloc)
    p._kind = kind or "panel"
    p._children = {}
    p._parent = nil
    p._x = 0; p._y = 0; p._w = 0; p._h = 0
    p._text = ""
    p._font_size = 14
    p._visible = true
    p._color = nil
    p._alive = true
    return p
end

function Panel:new(name) return _make(name) end

function Panel:x() return self._x end
function Panel:y() return self._y end
function Panel:w() return self._w end
function Panel:h() return self._h end
function Panel:name() return self._name end
function Panel:parent() return self._parent end
function Panel:visible() return self._visible end
function Panel:font_size() return self._font_size end

-- text() overload: no args / non-table -> getter; table -> constructor creates child
function Panel:text(cfg)
    if cfg ~= nil and type(cfg) == "table" then
        local n = cfg.name or _uniq("text")
        local ch = _make(n, "text")
        ch._parent = self
        _apply(ch, cfg)
        self._children[ch._name] = ch
        return ch
    end
    return self._text
end

function Panel:set_shape(x, y, w, h)
    self._x = x; self._y = y; self._w = w; self._h = h
end
function Panel:set_position(x, y) self._x = x; self._y = y end
function Panel:set_text(t) self._text = tostring(t) end
function Panel:set_font_size(s) self._font_size = s end
function Panel:set_visible(v) self._visible = v end
function Panel:set_color(c) self._color = c end

function Panel:child(n) return self._children[n] end
function Panel:children() return self._children end

-- panel(name) creates a named child panel (NOT self)
function Panel:panel(cfg)
    local n
    if type(cfg) == "table" and cfg.name then n = cfg.name
    else n = _uniq("panel") end
    local ch = _make(n, "panel")
    ch._parent = self
    _apply(ch, cfg)
    self._children[ch._name] = ch
    return ch
end

-- rect(cfg) creates a child rect; unique name; respects config geometry/color/visible
function Panel:rect(cfg)
    local n
    if type(cfg) == "table" and cfg.name then n = cfg.name
    else n = _uniq("rect") end
    local ch = _make(n, "rect")
    ch._parent = self
    _apply(ch, cfg)
    self._children[ch._name] = ch
    return ch
end

-- bitmap(cfg) creates a child bitmap; unique name; respects config geometry/visible
function Panel:bitmap(cfg)
    local n
    if type(cfg) == "table" and cfg.name then n = cfg.name
    else n = _uniq("bitmap") end
    local ch = _make(n, "bitmap")
    ch._parent = self
    _apply(ch, cfg)
    self._children[ch._name] = ch
    return ch
end

function Panel:textbox(name)
    local n = name or _uniq("textbox")
    local ch = _make(n, "textbox")
    ch._parent = self
    self._children[ch._name] = ch
    return ch
end

function Panel:clear()
    self._children = {}
end

-- remove kills only the subtree (marks _alive=false recursively), then unlinks
function Panel:remove(c)
    if c == nil then return end
    if type(c) == "string" then c = self._children[c] end
    if c == nil then return end
    local function _kill(p)
        p._alive = false
        for _, sub in pairs(p._children or {}) do _kill(sub) end
    end
    _kill(c)
    self._children[c._name] = nil
end

function alive(p)
    return p ~= nil and p._alive ~= false
end

-- Color: callable mock only, returns a table
Color = function(r, g, b)
    return { r = r or 0, g = g or 0, b = b or 0 }
end

-- Expose global allocation counter (increments on every primitive allocation)
_G._alloc_count = function() return _alloc end

_G.panel_double = _make("root_parent", "panel")
'''


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    gauge_src = _read(GAUGE_PATH)
    exists = gauge_src is not None
    if exists:
        lua.execute(gauge_src)
    return lua, exists


class GaugeFileExistsTests(unittest.TestCase):
    def test_gauge_chunk_exists(self):
        self.assertTrue(GAUGE_PATH.is_file(),
            "RED: lua/hud/components/gauge.lua must exist")


class GaugeCreationAndShapeTests(unittest.TestCase):
    def test_new_returns_instance_with_fields_and_markers(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local G = kyohud.hud.gauge
            assert(G and G.new, "RED: kyohud.hud.gauge.new must exist")
            local inst = G.new(parent, "mygauge")
            _root = inst and inst.root or nil
            _hf = inst and inst.health_fill or nil
            _af = inst and inst.armor_fill or nil
            _m1 = inst.markers and inst.markers[1] or nil
            _m2 = inst.markers and inst.markers[2] or nil
            _m3 = inst.markers and inst.markers[3] or nil
            _ht = inst and inst.health_text or nil
            _at = inst and inst.armor_text or nil
            inst:set_geometry(10, 20, 400, 60)
            _rx = inst.root:x(); _ry = inst.root:y()
            _rw = inst.root:w(); _rh = inst.root:h()
            -- markers must be at 0.3/0.5/0.75 * w within health row
            _mx1 = _m1:x(); _mx2 = _m2:x(); _mx3 = _m3:x()
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._root, "instance.root required")
        self.assertIsNotNone(g._hf, "health_fill required")
        self.assertIsNotNone(g._af, "armor_fill required")
        self.assertIsNotNone(g._m1, "markers[1] required")
        self.assertIsNotNone(g._m2, "markers[2] required")
        self.assertIsNotNone(g._m3, "markers[3] required")
        self.assertIsNotNone(g._ht, "health_text required")
        self.assertIsNotNone(g._at, "armor_text required")
        self.assertEqual(float(g._rx), 10.0)
        self.assertEqual(float(g._ry), 20.0)
        self.assertEqual(float(g._rw), 400.0)
        self.assertEqual(float(g._rh), 60.0)
        self.assertAlmostEqual(float(g._mx1), 400 * 0.3, places=3,
            msg="marker 1 must be at 0.3 * w")
        self.assertAlmostEqual(float(g._mx2), 400 * 0.5, places=3,
            msg="marker 2 must be at 0.5 * w")
        self.assertAlmostEqual(float(g._mx3), 400 * 0.75, places=3,
            msg="marker 3 must be at 0.75 * w")


class GaugeRenderPercentageAndRealTests(unittest.TestCase):
    def test_percentage_boundary_values_and_real_local(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local inst = kyohud.hud.gauge.new(parent, "g1")
            inst:set_geometry(0, 0, 100, 40)

            -- percentage boundaries (ratio)
            local cases = {
                {cur=0,   tot=100, mode="percentage", mult=10, expect="0%"},
                {cur=1,   tot=100, mode="percentage", mult=10, expect="1%"},
                {cur=29,  tot=100, mode="percentage", mult=10, expect="29%"},
                {cur=30,  tot=100, mode="percentage", mult=10, expect="30%"},
                {cur=31,  tot=100, mode="percentage", mult=10, expect="31%"},
                {cur=49,  tot=100, mode="percentage", mult=10, expect="49%"},
                {cur=50,  tot=100, mode="percentage", mult=10, expect="50%"},
                {cur=51,  tot=100, mode="percentage", mult=10, expect="51%"},
                {cur=74,  tot=100, mode="percentage", mult=10, expect="74%"},
                {cur=75,  tot=100, mode="percentage", mult=10, expect="75%"},
                {cur=76,  tot=100, mode="percentage", mult=10, expect="76%"},
                {cur=82,  tot=100, mode="percentage", mult=10, expect="82%"},
                {cur=100, tot=100, mode="percentage", mult=10, expect="100%"},
                -- clamped over 100
                {cur=200, tot=100, mode="percentage", mult=10, expect="100%"},
                -- total=0: ratio unknown -> "--" (not "0%")
                {cur=50,  tot=0,   mode="percentage", mult=10, expect="--"},
            }
            _pct_results = {}
            for i, c in ipairs(cases) do
                local hp = {current=c.cur, total=c.tot, ratio=(c.tot>0 and c.cur/c.tot or 0), valid=(c.tot>0), provenance="local"}
                local ar = {current=0, total=1, ratio=0, valid=true, provenance="local"}
                inst:render(hp, ar, c.mode, c.mult)
                _pct_results[i] = inst.health_text:text()
            end
        ''')
        g = lua.globals()
        results = {int(k): str(v) for k, v in g._pct_results.items()}
        cases_expected = [
            "0%", "1%", "29%", "30%", "31%", "49%", "50%",
            "51%", "74%", "75%", "76%", "82%", "100%", "100%", "--",
        ]
        for i, exp in enumerate(cases_expected, 1):
            self.assertEqual(results[i], exp,
                f"percentage case {i}: expected {exp!r}, got {results[i]!r}")

    def test_real_mode_uses_multiplier_only_when_local(self):
        """real 8/23 -> 80 (mult 10), armor 2/5 -> 20 (mult 10).
        real missing/nonfinite multiplier -> '--'. real provenance!='local' -> '--'.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local inst = kyohud.hud.gauge.new(parent, "g2")
            inst:set_geometry(0, 0, 100, 40)

            -- health real 8/23, multiplier 10 -> 80
            local hp1 = {current=8, total=23, ratio=8/23, valid=true, provenance="local"}
            local ar1 = {current=2, total=5, ratio=2/5, valid=true, provenance="local"}
            inst:render(hp1, ar1, "real", 10)
            _hp_text1 = inst.health_text:text()
            _ar_text1 = inst.armor_text:text()

            -- health real provenance ~= local -> "--"
            local hp2 = {current=8, total=23, ratio=8/23, valid=true, provenance="remote"}
            inst:render(hp2, ar1, "real", 10)
            _hp_text2 = inst.health_text:text()

            -- real with non-finite multiplier -> "--"
            inst:render(hp1, ar1, "real", 0/0)
            _hp_text_nan = inst.health_text:text()
            inst:render(hp1, ar1, "real", math.huge)
            _hp_text_inf = inst.health_text:text()

            -- real with nil multiplier -> "--"
            inst:render(hp1, ar1, "real", nil)
            _hp_text_nil = inst.health_text:text()
        ''')
        g = lua.globals()
        self.assertEqual(g._hp_text1, "80", "real 8/23 * 10 -> 80")
        self.assertEqual(g._ar_text1, "20", "real 2/5 * 10 -> 20")
        self.assertEqual(g._hp_text2, "--",
            "real with provenance!='local' must yield '--'")
        self.assertEqual(g._hp_text_nan, "--",
            "real with NaN multiplier must yield '--'")
        self.assertEqual(g._hp_text_inf, "--",
            "real with inf multiplier must yield '--'")
        self.assertEqual(g._hp_text_nil, "--",
            "real with nil multiplier must yield '--'")


class GaugeIndependenceAndStabilityTests(unittest.TestCase):
    def test_two_instances_independent_state_and_geometry(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local a = kyohud.hud.gauge.new(parent, "ga")
            local b = kyohud.hud.gauge.new(parent, "gb")
            a:set_geometry(0, 0, 200, 30)
            b:set_geometry(0, 0, 500, 80)
            _aw = a.root:w(); _bw = b.root:w()
            _ah = a.root:h(); _bh = b.root:h()

            local hp_a = {current=50, total=100, ratio=0.5, valid=true, provenance="local"}
            local hp_b = {current=10, total=100, ratio=0.1, valid=true, provenance="local"}
            local ar = {current=1, total=2, ratio=0.5, valid=true, provenance="local"}
            a:render(hp_a, ar, "percentage", 10)
            b:render(hp_b, ar, "percentage", 10)
            _a_text = a.health_text:text()
            _b_text = b.health_text:text()
        ''')
        g = lua.globals()
        self.assertEqual(float(g._aw), 200.0)
        self.assertEqual(float(g._bw), 500.0)
        self.assertEqual(float(g._ah), 30.0)
        self.assertEqual(float(g._bh), 80.0)
        self.assertEqual(g._a_text, "50%")
        self.assertEqual(g._b_text, "10%")

    def test_fill_widths_proportional_clamped_and_independent(self):
        """Fill widths scale with ratio, clamp to [0, w], health independent of armor."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local inst = kyohud.hud.gauge.new(parent, "gf")
            inst:set_geometry(0, 0, 200, 40)

            local function hp(r) return {current=r*100, total=100, ratio=r, valid=true, provenance="local"} end
            local function ar(r) return {current=r*100, total=100, ratio=r, valid=true, provenance="local"} end

            -- ratio=0 -> fill w=0
            inst:render(hp(0), ar(0), "percentage", 10)
            _hf0 = inst.health_fill:w()
            _af0 = inst.armor_fill:w()

            -- ratio=0.5 -> fill w=100
            inst:render(hp(0.5), ar(0.5), "percentage", 10)
            _hf50 = inst.health_fill:w()
            _af50 = inst.armor_fill:w()

            -- ratio=1.0 -> fill w=200 (full width)
            inst:render(hp(1.0), ar(1.0), "percentage", 10)
            _hf100 = inst.health_fill:w()
            _af100 = inst.armor_fill:w()

            -- ratio>1.0 -> clamped to 200
            inst:render(hp(2.0), ar(1.0), "percentage", 10)
            _hf_over = inst.health_fill:w()

            -- health independent of armor: different ratios
            inst:render(hp(0.25), ar(0.75), "percentage", 10)
            _hf25 = inst.health_fill:w()
            _af75 = inst.armor_fill:w()
        ''')
        g = lua.globals()
        self.assertEqual(float(g._hf0), 0.0, "ratio=0 -> health fill w=0")
        self.assertEqual(float(g._af0), 0.0, "ratio=0 -> armor fill w=0")
        self.assertEqual(float(g._hf50), 100.0, "ratio=0.5 -> health fill w=w/2")
        self.assertEqual(float(g._af50), 100.0, "ratio=0.5 -> armor fill w=w/2")
        self.assertEqual(float(g._hf100), 200.0, "ratio=1.0 -> health fill w=w")
        self.assertEqual(float(g._af100), 200.0, "ratio=1.0 -> armor fill w=w")
        self.assertEqual(float(g._hf_over), 200.0, "ratio>1.0 -> clamped to w")
        self.assertEqual(float(g._hf25), 50.0, "health 25% -> fill w=50")
        self.assertEqual(float(g._af75), 150.0, "armor 75% -> fill w=150")

    def test_geometry_aba_no_drift_and_creation_count_stable(self):
        """set_geometry A -> B -> A returns to A; render does not allocate new panels."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local inst = kyohud.hud.gauge.new(parent, "gc")

            inst:set_geometry(5, 6, 77, 33)
            _x1 = inst.root:x(); _y1 = inst.root:y()
            _w1 = inst.root:w(); _h1 = inst.root:h()

            inst:set_geometry(100, 200, 999, 50)

            inst:set_geometry(5, 6, 77, 33)
            _x2 = inst.root:x(); _y2 = inst.root:y()
            _w2 = inst.root:w(); _h2 = inst.root:h()

            -- render repeatedly: no new primitives must be allocated after first render
            local hp = {current=25, total=100, ratio=0.25, valid=true, provenance="local"}
            local ar = {current=1, total=2, ratio=0.5, valid=true, provenance="local"}
            inst:render(hp, ar, "percentage", 10)
            _after_first = _G._alloc_count()
            for _ = 1, 20 do
                inst:render(hp, ar, "percentage", 10)
            end
            _after_many = _G._alloc_count()
        ''')
        g = lua.globals()
        self.assertEqual(float(g._x1), 5.0)
        self.assertEqual(float(g._y1), 6.0)
        self.assertEqual(float(g._w1), 77.0)
        self.assertEqual(float(g._h1), 33.0)
        self.assertEqual(float(g._x2), 5.0, "set_geometry A-B-A must restore x")
        self.assertEqual(float(g._y2), 6.0, "set_geometry A-B-A must restore y")
        self.assertEqual(float(g._w2), 77.0, "set_geometry A-B-A must restore w")
        self.assertEqual(float(g._h2), 33.0, "set_geometry A-B-A must restore h")
        self.assertEqual(int(g._after_first), int(g._after_many),
            "repeated render must not allocate new primitives (global counter)")


class GaugeVerifyAndDestroyTests(unittest.TestCase):
    def test_verify_false_on_corrupt_fill_then_true_when_restored(self):
        """verify() returns false after corrupting fill width or text, true restored."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local inst = kyohud.hud.gauge.new(parent, "gv")
            inst:set_geometry(0, 0, 200, 40)
            local hp = {current=40, total=100, ratio=0.4, valid=true, provenance="local"}
            local ar = {current=2, total=5, ratio=0.4, valid=true, provenance="local"}
            inst:render(hp, ar, "percentage", 10)
            _ok_clean = inst:verify()

            -- Corrupt health fill width
            if inst.health_fill then
                inst.health_fill:set_shape(-1, -1, -1, -1)
            end
            _ok_bad_fill = inst:verify()

            -- Restore fill
            inst:render(hp, ar, "percentage", 10)
            _ok_fill_restored = inst:verify()

            -- Corrupt health text
            if inst.health_text then
                inst.health_text:set_text("WRONG")
            end
            _ok_bad_text = inst:verify()

            -- Restore text
            inst:render(hp, ar, "percentage", 10)
            _ok_text_restored = inst:verify()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._ok_clean),
            "verify() must be true on a healthy gauge")
        self.assertFalse(bool(g._ok_bad_fill),
            "verify() must be false after corrupting a fill")
        self.assertTrue(bool(g._ok_fill_restored),
            "verify() must be true after render restores fill")
        self.assertFalse(bool(g._ok_bad_text),
            "verify() must be false after corrupting text")
        self.assertTrue(bool(g._ok_text_restored),
            "verify() must be true after render restores text")

    def test_destroy_only_own_root(self):
        """destroy() must mark only the gauge's own root as destroyed."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local inst = kyohud.hud.gauge.new(parent, "gd")
            local sibling = _G.panel_double  -- shared parent must survive
            local own_root = inst.root
            inst:destroy()
            _own_alive = alive(own_root)
            _parent_alive = alive(sibling)
        ''')
        g = lua.globals()
        self.assertFalse(bool(g._own_alive),
            "destroy() must kill the gauge's own root panel")
        self.assertTrue(bool(g._parent_alive),
            "destroy() must NOT destroy the parent panel")


if __name__ == "__main__":
    unittest.main()
