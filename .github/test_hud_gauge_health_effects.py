"""RED first pass -- gauge stored-health reserve (Ex-President second bar).

Scope: bounded gauge rendering test only. No player runtime integration, no
delayed-damage/absorption effects, no native masks, no production edits.

Expected gauge API (not implemented yet):
  instance:render(health, armor, mode, multiplier, peer_color, health_effects)
  instance._stored_health_bg    -- native rect track
  instance._stored_health_fill  -- native rect fill

health_effects.stored_health = {known = true, ratio = <current>, max_ratio = <max>}

The reserve track mirrors _armor_bg x/w, sits at y = 35*e with h = 4*e inside
the 42*e gauge height, and the fill is ratio/max_ratio of that track in a
blue/cyan ink distinct from the primary health ink. Missing reserve primitives
must fail the explicit presence assertions below, never skip.

Reuses the literal fixture path from test_hud_gauge._lua; no shared fixture copy.
"""
import math
import unittest

from test_hud_gauge import _lua

RESERVE_SCRIPT = r'''
local G = kyohud.hud.gauge
local parent = _G.panel_double
local e = _KY_scale

local inst = G.new(parent, "gh_" .. tostring(e))
inst:set_geometry(0, 0, 440 * e, 42 * e)

local hp = {current = 60, total = 100, ratio = 0.6, valid = true, provenance = "local"}
local ar = {current = 50, total = 100, ratio = 0.5, valid = true, provenance = "local"}
local positive = {stored_health = {known = true, ratio = 0.2, max_ratio = 0.4}}

local function render(effects)
    inst:render(hp, ar, "percentage", 10, nil, effects)
end

local function geom(p)
    return {p:x(), p:y(), p:w(), p:h()}
end

local function same_geom(a, b)
    for i = 1, 4 do
        if math.abs(a[i] - b[i]) > 0.01 then return false end
    end
    return true
end

local function main_snapshot()
    local s = {
        health_text = inst.health_text:text(),
        armor_text = inst.armor_text:text(),
        armor_bg = geom(inst._armor_bg),
        armor_fill = geom(inst.armor_fill),
    }
    for i = 1, 4 do
        s["hbg" .. i] = geom(inst.health_segments[i].background)
        s["hfill" .. i] = geom(inst.health_segments[i].fill)
    end
    return s
end

local function same_main(a, b)
    if a.health_text ~= b.health_text or a.armor_text ~= b.armor_text then
        return false
    end
    if not same_geom(a.armor_bg, b.armor_bg) then return false end
    if not same_geom(a.armor_fill, b.armor_fill) then return false end
    for i = 1, 4 do
        if not same_geom(a["hbg" .. i], b["hbg" .. i]) then return false end
        if not same_geom(a["hfill" .. i], b["hfill" .. i]) then return false end
    end
    return true
end

render(positive)
_positive_verify = inst:verify()
local baseline = main_snapshot()
_main_unchanged = true
_main_failure = nil

local function check_main(phase)
    if not same_main(baseline, main_snapshot()) then
        _main_unchanged = false
        _main_failure = phase
    end
end

local bg = inst._stored_health_bg
local fill = inst._stored_health_fill
_reserve_bg_present = bg ~= nil
_reserve_fill_present = fill ~= nil
if not (_reserve_bg_present and _reserve_fill_present) then return end

local bg_ref, fill_ref = bg, fill
_identity_stable = true
_identity_failure = nil

local function check_identity(phase)
    if inst._stored_health_bg ~= bg_ref or inst._stored_health_fill ~= fill_ref then
        _identity_stable = false
        _identity_failure = phase
    end
end

check_identity("positive")
check_main("positive")

-- Positive reserve: full track mirrors the armor track, fill is half of it.
local armor_bg = inst._armor_bg
_track_x = bg:x()
_track_y = bg:y()
_track_w = bg:w()
_track_h = bg:h()
_armor_bg_x = armor_bg:x()
_armor_bg_w = armor_bg:w()
_track_visible = bg:visible()
_fill_x = fill:x()
_fill_y = fill:y()
_fill_w = fill:w()
_fill_h = fill:h()
_fill_visible = fill:visible()
local hp_color = inst.health_segments[1].fill:color()
local reserve_color = fill:color()
_reserve_distinct = hp_color ~= nil and reserve_color ~= nil
    and not (reserve_color.r == hp_color.r
        and reserve_color.g == hp_color.g
        and reserve_color.b == hp_color.b)
_reserve_blue_cyan = reserve_color ~= nil
    and reserve_color.b > reserve_color.r
    and reserve_color.g > reserve_color.r
    and reserve_color.b >= 0.5

-- Corrupt only the reserve fill x; verify must reject it.
fill:set_shape(fill:x() - 5 * e, fill:y(), fill:w(), fill:h())
_verify_bad_fill_x = inst:verify()
check_identity("fill_x_corrupt")
check_main("fill_x_corrupt")
render(positive)
_verify_recovered_fill_x = inst:verify()
check_identity("fill_x")
check_main("fill_x")

-- Corrupt only the reserve fill visibility; verify must reject it.
fill:set_visible(false)
_verify_bad_fill_visibility = inst:verify()
check_identity("fill_visibility_corrupt")
check_main("fill_visibility_corrupt")
render(positive)
_verify_recovered_fill_visibility = inst:verify()
check_identity("fill_visibility")
check_main("fill_visibility")

-- Zero stock with a known max: track stays visible, fill collapses to 0.
render({stored_health = {known = true, ratio = 0, max_ratio = 0.4}})
_zero_track_visible = bg:visible()
_zero_fill_w = fill:w()
_zero_verify = inst:verify()
check_identity("zero")
check_main("zero")

-- max_ratio = 0 hides both reserve primitives.
render({stored_health = {known = true, ratio = 0.2, max_ratio = 0}})
_maxzero_bg_visible = bg:visible()
_maxzero_fill_visible = fill:visible()
_maxzero_verify = inst:verify()
check_identity("max_zero")
check_main("max_zero")

-- known = false hides both reserve primitives.
render({stored_health = {known = false, ratio = 0.2, max_ratio = 0.4}})
_unknown_bg_visible = bg:visible()
_unknown_fill_visible = fill:visible()
_unknown_verify = inst:verify()
check_identity("unknown")
check_main("unknown")

-- Absent effects hide both reserve primitives.
render(nil)
_absent_bg_visible = bg:visible()
_absent_fill_visible = fill:visible()
_absent_verify = inst:verify()
check_identity("absent")
check_main("absent")

-- A hidden reserve primitive cannot be made visible behind verify's back.
bg:set_visible(true)
_verify_mutated_absent_bg = inst:verify()
check_identity("absent_bg_mutated")
check_main("absent_bg_mutated")
render(nil)
_verify_recovered_absent_bg = inst:verify()
_absent_recovered_bg_visible = bg:visible()
_absent_recovered_fill_visible = fill:visible()
check_identity("absent_recovered")
check_main("absent_recovered")
'''


class GaugeStoredHealthReserveTests(unittest.TestCase):
    def test_stored_health_reserve_rendering(self):
        for scale in (1.0, 0.672):
            with self.subTest(scale=scale):
                lua, ok = _lua()
                self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
                if not ok:
                    return

                lua.globals()._KY_scale = scale
                lua.execute(RESERVE_SCRIPT)
                g = lua.globals()

                self.assertTrue(bool(g._positive_verify),
                    f"scale {scale}: positive reserve render must verify")
                self.assertTrue(bool(g._reserve_bg_present),
                    f"scale {scale}: RED missing instance._stored_health_bg")
                self.assertTrue(bool(g._reserve_fill_present),
                    f"scale {scale}: RED missing instance._stored_health_fill")

                self.assertTrue(bool(g._track_visible),
                    f"scale {scale}: reserve track must be visible with stock")
                self.assertTrue(bool(g._fill_visible),
                    f"scale {scale}: reserve fill must be visible with stock")
                self.assertAlmostEqual(float(g._track_x), float(g._armor_bg_x),
                    delta=0.01,
                    msg=f"scale {scale}: reserve track x must match _armor_bg x")
                self.assertAlmostEqual(float(g._track_w), float(g._armor_bg_w),
                    delta=0.01,
                    msg=f"scale {scale}: reserve track w must match _armor_bg w")
                self.assertAlmostEqual(float(g._track_y), 35 * scale,
                    delta=0.01,
                    msg=f"scale {scale}: reserve track y must be 35*e")
                self.assertAlmostEqual(float(g._track_h), 4 * scale,
                    delta=0.01,
                    msg=f"scale {scale}: reserve track h must be 4*e")
                self.assertLessEqual(float(g._track_y) + float(g._track_h),
                    42 * scale + 0.01,
                    f"scale {scale}: reserve track must stay within 42*e")
                self.assertAlmostEqual(float(g._fill_x), float(g._track_x),
                    delta=0.01,
                    msg=f"scale {scale}: reserve fill x must match track x")
                self.assertAlmostEqual(float(g._fill_y), float(g._track_y),
                    delta=0.01,
                    msg=f"scale {scale}: reserve fill y must match track y")
                self.assertAlmostEqual(float(g._fill_h), float(g._track_h),
                    delta=0.01,
                    msg=f"scale {scale}: reserve fill h must match track h")
                self.assertAlmostEqual(float(g._fill_w), float(g._track_w) * 0.5,
                    delta=0.01,
                    msg=f"scale {scale}: reserve fill must be half the track")
                self.assertTrue(bool(g._reserve_distinct),
                    f"scale {scale}: reserve fill must differ from primary health ink")
                self.assertTrue(bool(g._reserve_blue_cyan),
                    f"scale {scale}: reserve fill must be blue/cyan, not health green")

                self.assertFalse(bool(g._verify_bad_fill_x),
                    f"scale {scale}: verify must reject a corrupted reserve fill x")
                self.assertTrue(bool(g._verify_recovered_fill_x),
                    f"scale {scale}: verify must recover after rerendering fill x")
                self.assertFalse(bool(g._verify_bad_fill_visibility),
                    f"scale {scale}: verify must reject a hidden reserve fill")
                self.assertTrue(bool(g._verify_recovered_fill_visibility),
                    f"scale {scale}: verify must recover after rerendering fill visibility")

                self.assertTrue(bool(g._zero_track_visible),
                    f"scale {scale}: zero stock with max 0.4 keeps the track visible")
                self.assertAlmostEqual(float(g._zero_fill_w), 0.0,
                    delta=0.01,
                    msg=f"scale {scale}: zero stock must collapse the fill width")
                self.assertTrue(bool(g._zero_verify),
                    f"scale {scale}: zero stock render must verify")

                for prefix in ("maxzero", "unknown", "absent"):
                    self.assertFalse(bool(g[f"_{prefix}_bg_visible"]),
                        f"scale {scale}: {prefix} must hide the reserve track")
                    self.assertFalse(bool(g[f"_{prefix}_fill_visible"]),
                        f"scale {scale}: {prefix} must hide the reserve fill")
                    self.assertTrue(bool(g[f"_{prefix}_verify"]),
                        f"scale {scale}: {prefix} hidden reserve must verify")

                self.assertFalse(bool(g._verify_mutated_absent_bg),
                    f"scale {scale}: verify must reject a visible reserve track when absent")
                self.assertTrue(bool(g._verify_recovered_absent_bg),
                    f"scale {scale}: verify must recover after rerendering absent effects")
                self.assertFalse(bool(g._absent_recovered_bg_visible),
                    f"scale {scale}: absent rerender must hide the reserve track")
                self.assertFalse(bool(g._absent_recovered_fill_visible),
                    f"scale {scale}: absent rerender must hide the reserve fill")

                self.assertTrue(bool(g._identity_stable),
                    f"scale {scale}: reserve primitive identity lost at "
                    f"{g._identity_failure}")
                self.assertTrue(bool(g._main_unchanged),
                    f"scale {scale}: main health/armor changed at {g._main_failure}")


DEBT_SCRIPT = r'''
local G = kyohud.hud.gauge
local parent = _G.panel_double
local e = _KY_scale

local inst = G.new(parent, "debt_" .. tostring(e))
inst:set_geometry(0, 0, 440 * e, 42 * e)

local hp = {current = 60, total = 100, ratio = 0.6, valid = true, provenance = "local"}
local ar = {current = 25, total = 50, ratio = 0.5, valid = true, provenance = "local"}

-- known == nil means ordinary render without effects (explicit nil clears).
local function render(amount, known)
    local effects = nil
    if known ~= nil then
        effects = {delayed_damage = {known = known, amount = amount}}
    end
    inst:render(hp, ar, "percentage", 10, nil, effects)
end

local function geom(p)
    return {x = p:x(), y = p:y(), w = p:w(), h = p:h()}
end

local function same_geom(a, b)
    return math.abs(a.x - b.x) <= 0.05 and math.abs(a.y - b.y) <= 0.05
        and math.abs(a.w - b.w) <= 0.05 and math.abs(a.h - b.h) <= 0.05
end

local function same_color(a, b)
    if not a or not b then return a == b end
    return math.abs(a.r - b.r) <= 0.001 and math.abs(a.g - b.g) <= 0.001
        and math.abs(a.b - b.b) <= 0.001
end

local function principal()
    local s = {
        health_text = inst.health_text:text(),
        armor_text = inst.armor_text:text(),
        armor_fill = geom(inst.armor_fill),
        armor_color = inst.armor_fill:color(),
        health_fill = geom(inst.health_fill),
        segments = {},
    }
    for i = 1, 4 do
        local seg = inst.health_segments[i]
        s.segments[i] = {
            bg = geom(seg.background), fill = geom(seg.fill),
            bg_color = seg.background:color(), fill_color = seg.fill:color(),
        }
    end
    return s
end

local function same_principal(a, b)
    if a.health_text ~= b.health_text or a.armor_text ~= b.armor_text then return false end
    if not same_geom(a.armor_fill, b.armor_fill)
        or not same_geom(a.health_fill, b.health_fill) then return false end
    if not same_color(a.armor_color, b.armor_color) then return false end
    for i = 1, 4 do
        local x, y = a.segments[i], b.segments[i]
        if not same_geom(x.bg, y.bg) or not same_geom(x.fill, y.fill)
            or not same_color(x.bg_color, y.bg_color)
            or not same_color(x.fill_color, y.fill_color) then return false end
    end
    return true
end

local function sample()
    local t = {
        verify = inst:verify(),
        armor_fill = geom(inst.armor_fill),
        armor_track = geom(inst._armor_bg),
        health_fill = geom(inst.health_fill),
        health_fill_layer = inst.health_fill:layer(),
        armor = {},
        health = {},
        segments = {},
    }
    local a = inst._delayed_armor
    if a then
        t.armor = {visible = a:visible(), geom = geom(a), layer = a:layer(),
            on_root = a:parent() == inst.root, color = a:color()}
    else
        t.armor = {visible = false}
    end
    for i = 1, 4 do
        local p = inst._delayed_health and inst._delayed_health[i]
        local bg = inst.health_segments[i].background
        local fill = inst.health_segments[i].fill
        t.segments[i] = {x = bg:x(), w = bg:w(), fill_h = fill:h()}
        if p then
            t.health[i] = {visible = p:visible(), geom = geom(p), layer = p:layer(),
                on_fill = p:parent() == inst.health_fill}
        else
            t.health[i] = {visible = false}
        end
    end
    return t
end

_debt_present = inst._delayed_armor ~= nil and type(inst._delayed_health) == "table"
if type(inst._delayed_health) == "table" then
    for i = 1, 4 do _debt_present = _debt_present and inst._delayed_health[i] ~= nil end
end
if not _debt_present then return end

render(nil, nil)
local baseline = principal()

render(60, true)
_debt_cases = {positive = sample()}
_debt_main = {positive = same_principal(baseline, principal())}
_debt_primary_health = inst.health_segments[1].fill:color()

local ref_armor = inst._delayed_armor
local ref_health = {}
for i = 1, 4 do ref_health[i] = inst._delayed_health[i] end
_debt_identity = true
local function check_identity()
    if inst._delayed_armor ~= ref_armor then _debt_identity = false end
    for i = 1, 4 do
        if inst._delayed_health[i] ~= ref_health[i] then _debt_identity = false end
    end
end
check_identity()

render(10, true)
_debt_cases.armor_only = sample()
_debt_main.armor_only = same_principal(baseline, principal())
check_identity()

render(0, true)
_debt_cases.zero = sample()
_debt_main.zero = same_principal(baseline, principal())
check_identity()

render(60, false)
_debt_cases.unknown = sample()
_debt_main.unknown = same_principal(baseline, principal())
check_identity()

render(60, true)
_debt_cases.recovered = sample()
_debt_main.recovered = same_principal(baseline, principal())
check_identity()

ref_armor:set_shape(ref_armor:x() - 5 * e, ref_armor:y(),
    ref_armor:w(), ref_armor:h())
_debt_corrupt_verify = inst:verify()
check_identity()

render(60, true)
_debt_recovered_verify = inst:verify()
_debt_identity_after_rerender = _debt_identity
    and inst._delayed_armor == ref_armor
    and inst._delayed_armor:visible()
'''

DEBT_ZERO_ARMOR_SCRIPT = r'''
local G = kyohud.hud.gauge
local parent = _G.panel_double
local e = _KY_scale

local inst = G.new(parent, "debt_zero_" .. tostring(e))
inst:set_geometry(0, 0, 440 * e, 42 * e)

local hp = {current = 60, total = 100, ratio = 0.6, valid = true, provenance = "local"}
local zero = {current = 0, total = 0, ratio = nil, valid = false, provenance = "local"}
local unknown = {current = nil, total = nil, ratio = nil, valid = false, provenance = "local"}
local debt = {known = true, amount = 35}

local function render(armor)
    inst:render(hp, armor, "percentage", 10, nil, {delayed_damage = debt})
end

local function geom(p)
    return {x = p:x(), y = p:y(), w = p:w(), h = p:h()}
end

local function snapshot()
    local t = {
        verify = inst:verify(),
        armor_visible = inst._delayed_armor:visible(),
        health = {},
        segments = {},
    }
    for i = 1, 4 do
        local bg = inst.health_segments[i].background
        local fill = inst.health_segments[i].fill
        local d = inst._delayed_health[i]
        t.segments[i] = {x = bg:x(), w = bg:w(), fill_h = fill:h()}
        t.health[i] = {visible = d:visible(), geom = geom(d)}
    end
    return t
end

_debt_zero_present = inst._delayed_armor ~= nil and type(inst._delayed_health) == "table"
if type(inst._delayed_health) == "table" then
    for i = 1, 4 do
        _debt_zero_present = _debt_zero_present and inst._delayed_health[i] ~= nil
    end
end
if not _debt_zero_present then return end

render(zero)
_zero = snapshot()
_ref_armor = inst._delayed_armor
_ref_health = {}
for i = 1, 4 do _ref_health[i] = inst._delayed_health[i] end

render(unknown)
_unknown = snapshot()

render(zero)
_recovered = snapshot()
_recovered_identity = inst._delayed_armor == _ref_armor
for i = 1, 4 do
    _recovered_identity = _recovered_identity
        and inst._delayed_health[i] == _ref_health[i]
end
'''


class GaugeDelayedDamageDebtOverlayTests(unittest.TestCase):
    """Debt overlays are pure component geometry, not player runtime state.

    The gauge API is RED here: ``_delayed_armor`` and ``_delayed_health[1..4]``
    do not exist yet. Missing rects fail explicitly through ``_debt_present``,
    never through a skipped subtest. No debt text, timer, font or native
    mutation is exercised in this pass.
    """

    def test_delayed_damage_debt_overlays(self):
        for scale in (1.0, 0.672):
            with self.subTest(scale=scale):
                lua, ok = _lua()
                self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
                if not ok:
                    return

                lua.globals()._KY_scale = scale
                lua.execute(DEBT_SCRIPT)
                g = lua.globals()

                self.assertTrue(bool(g._debt_present),
                    f"scale {scale}: RED missing _delayed_armor or "
                    f"_delayed_health[1..4]")

                cases = g._debt_cases
                positive = cases.positive

                self.assertTrue(bool(positive.verify),
                    f"scale {scale}: positive debt render must verify")
                self.assertTrue(bool(g._debt_main.positive),
                    f"scale {scale}: positive debt must not alter principal "
                    f"fill/text/geometry")

                armor = positive.armor
                self.assertTrue(bool(armor.visible),
                    f"scale {scale}: all-current-armor debt must be visible")
                self.assertAlmostEqual(float(armor.geom.x),
                    float(positive.armor_fill.x), delta=0.05,
                    msg=f"scale {scale}: armor debt x must match armor_fill")
                self.assertAlmostEqual(float(armor.geom.y),
                    float(positive.armor_fill.y), delta=0.05,
                    msg=f"scale {scale}: armor debt y must match armor_fill")
                self.assertAlmostEqual(float(armor.geom.w),
                    float(positive.armor_fill.w), delta=0.05,
                    msg=f"scale {scale}: armor debt w must match armor_fill")
                self.assertAlmostEqual(float(armor.geom.h),
                    float(positive.armor_fill.h), delta=0.05,
                    msg=f"scale {scale}: armor debt h must match armor_fill")
                self.assertEqual(int(armor.layer), 2,
                    f"scale {scale}: armor debt layer must be 2")
                self.assertTrue(bool(armor.on_root),
                    f"scale {scale}: armor debt must stay on root")
                self.assertLess(int(armor.layer),
                    int(positive.health_fill_layer),
                    f"scale {scale}: armor debt must sit below health_fill")
                ink = armor.color
                primary = g._debt_primary_health
                self.assertGreater(float(ink.r), float(ink.g),
                    f"scale {scale}: armor debt ink must be orange")
                self.assertGreater(float(ink.g), float(ink.b),
                    f"scale {scale}: armor debt ink must be orange")
                self.assertGreater(float(ink.r), 0.5,
                    f"scale {scale}: armor debt ink must be orange")
                self.assertFalse(
                    abs(float(ink.r) - float(primary.r)) <= 0.001
                    and abs(float(ink.g) - float(primary.g)) <= 0.001
                    and abs(float(ink.b) - float(primary.b)) <= 0.001,
                    f"scale {scale}: armor debt ink must differ from health ink")

                ratios = (0.3, 0.2, 0.25, 0.25)
                debt_lo, debt_hi = 0.25, 0.6
                cursor = 0.0
                for i in range(4):
                    seg = positive.segments[i + 1]
                    h = positive.health[i + 1]
                    seg_lo, seg_w = float(seg.x), float(seg.w)
                    span = min(debt_hi, cursor + ratios[i]) - max(debt_lo, cursor)
                    if span > 1e-9:
                        self.assertTrue(bool(h.visible),
                            f"scale {scale}: health debt segment {i + 1} "
                            f"must be visible")
                        expected_x = seg_lo + seg_w * (
                            max(debt_lo, cursor) - cursor) / ratios[i]
                        expected_w = seg_w * span / ratios[i]
                        self.assertAlmostEqual(float(h.geom.x), expected_x,
                            delta=0.05,
                            msg=f"scale {scale}: health debt segment {i + 1} x")
                        self.assertAlmostEqual(float(h.geom.w), expected_w,
                            delta=0.05,
                            msg=f"scale {scale}: health debt segment {i + 1} w")
                        self.assertGreaterEqual(float(h.geom.x),
                            seg_lo - 0.05,
                            f"scale {scale}: health debt segment {i + 1} "
                            f"must not cross left gap")
                        self.assertLessEqual(float(h.geom.x) + float(h.geom.w),
                            seg_lo + seg_w + 0.05,
                            f"scale {scale}: health debt segment {i + 1} "
                            f"must not cross right gap")
                        self.assertAlmostEqual(float(h.geom.h),
                            float(seg.fill_h), delta=0.05,
                            msg=f"scale {scale}: health debt segment {i + 1} h")
                        self.assertEqual(int(h.layer), 2,
                            f"scale {scale}: health debt segment {i + 1} "
                            f"must be layer 2 above fill layer 1")
                        self.assertTrue(bool(h.on_fill),
                            f"scale {scale}: health debt segment {i + 1} "
                            f"must be a health_fill child")
                    else:
                        self.assertFalse(bool(h.visible),
                            f"scale {scale}: health debt segment {i + 1} "
                            f"outside [.25,.6] must be hidden")
                    cursor += ratios[i]

                armor_only = cases.armor_only
                self.assertTrue(bool(armor_only.verify),
                    f"scale {scale}: armor-only debt render must verify")
                self.assertTrue(bool(g._debt_main.armor_only),
                    f"scale {scale}: armor-only debt must not alter principal")
                track = armor_only.armor_track
                self.assertTrue(bool(armor_only.armor.visible),
                    f"scale {scale}: armor-only debt must be visible")
                self.assertAlmostEqual(float(armor_only.armor.geom.w),
                    float(track.w) * 0.2, delta=0.05,
                    msg=f"scale {scale}: armor-only width must be 20% of armor track")
                self.assertAlmostEqual(
                    float(armor_only.armor.geom.x)
                        + float(armor_only.armor.geom.w),
                    float(track.x) + float(track.w) * 0.5, delta=0.05,
                    msg=f"scale {scale}: armor-only debt must end at 50% armor")
                self.assertAlmostEqual(float(armor_only.armor.geom.y),
                    float(armor_only.armor_fill.y), delta=0.05,
                    msg=f"scale {scale}: armor-only debt y must match armor_fill")
                self.assertAlmostEqual(float(armor_only.armor.geom.h),
                    float(armor_only.armor_fill.h), delta=0.05,
                    msg=f"scale {scale}: armor-only debt h must match armor_fill")
                for i in range(4):
                    self.assertFalse(bool(armor_only.health[i + 1].visible),
                        f"scale {scale}: armor-only debt must hide health "
                        f"segment {i + 1}")

                for phase in ("zero", "unknown"):
                    case = cases[phase]
                    self.assertTrue(bool(case.verify),
                        f"scale {scale}: {phase} debt render must verify")
                    self.assertTrue(bool(g._debt_main[phase]),
                        f"scale {scale}: {phase} debt must not alter principal")
                    self.assertFalse(bool(case.armor.visible),
                        f"scale {scale}: {phase} must hide armor debt")
                    for i in range(4):
                        self.assertFalse(bool(case.health[i + 1].visible),
                            f"scale {scale}: {phase} must hide health "
                            f"segment {i + 1}")

                self.assertFalse(bool(g._debt_corrupt_verify),
                    f"scale {scale}: verify must reject a corrupted debt x")
                self.assertTrue(bool(g._debt_recovered_verify),
                    f"scale {scale}: verify must recover after same-effects "
                    f"rerender")
                self.assertTrue(bool(g._debt_identity_after_rerender),
                    f"scale {scale}: debt rect identity must survive rerender")
                self.assertTrue(bool(g._debt_identity),
                    f"scale {scale}: debt rect identity must remain stable")
                self.assertTrue(bool(g._debt_main.recovered),
                    f"scale {scale}: recovery render must not alter principal")

    def test_zero_local_armor_is_known_debt_not_unknown(self):
        for scale in (1.0, 0.672):
            with self.subTest(scale=scale):
                lua, ok = _lua()
                self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
                if not ok:
                    return

                lua.globals()._KY_scale = scale
                lua.execute(DEBT_ZERO_ARMOR_SCRIPT)
                g = lua.globals()

                self.assertTrue(bool(g._debt_zero_present),
                    f"scale {scale}: RED missing _delayed_armor or "
                    f"_delayed_health[1..4]")

                zero = g._zero
                self.assertTrue(bool(zero.verify),
                    f"scale {scale}: proven zero-armor debt render must verify")
                self.assertFalse(bool(zero.armor_visible),
                    f"scale {scale}: zero armor has nothing to convert, "
                    f"armor debt must be hidden")

                ratios = (0.3, 0.2, 0.25, 0.25)
                lo, hi = 0.25, 0.6
                cursor = 0.0
                for i in range(4):
                    seg = zero.segments[i + 1]
                    debt = zero.health[i + 1]
                    span = min(hi, cursor + ratios[i]) - max(lo, cursor)
                    if span > 1e-9:
                        self.assertTrue(bool(debt.visible),
                            f"scale {scale}: zero-armor health debt "
                            f"segment {i + 1} must be visible")
                        self.assertAlmostEqual(float(debt.geom.x),
                            float(seg.x) + float(seg.w)
                                * (max(lo, cursor) - cursor) / ratios[i],
                            delta=0.05,
                            msg=f"scale {scale}: zero-armor segment {i + 1} x")
                        self.assertAlmostEqual(float(debt.geom.w),
                            float(seg.w) * span / ratios[i], delta=0.05,
                            msg=f"scale {scale}: zero-armor segment {i + 1} w")
                        self.assertAlmostEqual(float(debt.geom.h),
                            float(seg.fill_h), delta=0.05,
                            msg=f"scale {scale}: zero-armor segment {i + 1} h")
                    else:
                        self.assertFalse(bool(debt.visible),
                            f"scale {scale}: zero-armor health debt "
                            f"segment {i + 1} outside [.25,.6] must be hidden")
                    cursor += ratios[i]

                unknown = g._unknown
                self.assertTrue(bool(unknown.verify),
                    f"scale {scale}: unknown-armor debt render must verify")
                self.assertFalse(bool(unknown.armor_visible),
                    f"scale {scale}: unknown armor must hide armor debt")
                for i in range(4):
                    self.assertFalse(bool(unknown.health[i + 1].visible),
                        f"scale {scale}: unknown armor must hide health debt "
                        f"segment {i + 1} instead of inventing a split")

                recovered = g._recovered
                self.assertTrue(bool(g._recovered_identity),
                    f"scale {scale}: restoring proven zero armor must reuse "
                    f"the same debt primitives")
                self.assertTrue(bool(recovered.verify),
                    f"scale {scale}: recovered zero-armor debt render must verify")
                self.assertFalse(bool(recovered.armor_visible),
                    f"scale {scale}: recovered zero armor keeps armor debt hidden")
                for i in range(4):
                    self.assertEqual(bool(recovered.health[i + 1].visible),
                        bool(zero.health[i + 1].visible),
                        f"scale {scale}: recovered segment {i + 1} visibility")
                    if zero.health[i + 1].visible:
                        self.assertTrue(_same_geom(recovered.health[i + 1].geom,
                            zero.health[i + 1].geom),
                            f"scale {scale}: recovered segment {i + 1} geom")


ABSORB_SCRIPT = r'''
local G = kyohud.hud.gauge
local parent = _G.panel_double
local e = _KY_scale

local inst = G.new(parent, "absorb_" .. tostring(e))
inst:set_geometry(0, 0, 440 * e, 42 * e)

local hp = {current = 60, total = 100, ratio = 0.6, valid = true, provenance = "local"}
local ar = {current = 25, total = 50, ratio = 0.5, valid = true, provenance = "local"}
local debt60 = {known = true, amount = 60}

local function render(absorb, debt)
    local effects = nil
    if absorb ~= nil or debt ~= nil then
        effects = {}
        if absorb ~= nil then effects.absorption = absorb end
        if debt ~= nil then effects.delayed_damage = debt end
    end
    inst:render(hp, ar, "percentage", 10, nil, effects)
end

local function geom(p)
    return {x = p:x(), y = p:y(), w = p:w(), h = p:h()}
end

local function same_geom(a, b)
    return math.abs(a.x - b.x) <= 0.05 and math.abs(a.y - b.y) <= 0.05
        and math.abs(a.w - b.w) <= 0.05 and math.abs(a.h - b.h) <= 0.05
end

local function principal()
    local s = {
        health_text = inst.health_text:text(),
        armor_text = inst.armor_text:text(),
        armor_fill = geom(inst.armor_fill),
        health_fill = geom(inst.health_fill),
        segments = {},
    }
    for i = 1, 4 do
        local seg = inst.health_segments[i]
        s.segments[i] = {bg = geom(seg.background), fill = geom(seg.fill)}
    end
    return s
end

local function same_principal(a, b)
    if a.health_text ~= b.health_text or a.armor_text ~= b.armor_text then return false end
    if not same_geom(a.armor_fill, b.armor_fill)
        or not same_geom(a.health_fill, b.health_fill) then return false end
    for i = 1, 4 do
        if not same_geom(a.segments[i].bg, b.segments[i].bg)
            or not same_geom(a.segments[i].fill, b.segments[i].fill) then return false end
    end
    return true
end

local function sample()
    local t = {
        verify = inst:verify(),
        armor_bg = geom(inst._armor_bg),
        armor_fill = geom(inst.armor_fill),
        health_fill = geom(inst.health_fill),
        health_fill_layer = inst.health_fill:layer(),
        armor = {
            visible = inst._absorb_armor:visible(),
            geom = geom(inst._absorb_armor),
            layer = inst._absorb_armor:layer(),
            on_root = inst._absorb_armor:parent() == inst.root,
            color = inst._absorb_armor:color(),
        },
        health = {}, segments = {}, debt = {visible = false}, debt_health = {},
    }
    if inst._delayed_armor ~= nil then
        t.debt = {
            visible = inst._delayed_armor:visible(),
            geom = geom(inst._delayed_armor),
            layer = inst._delayed_armor:layer(),
            color = inst._delayed_armor:color(),
        }
    end
    for i = 1, 4 do
        local bg = inst.health_segments[i].background
        local fill = inst.health_segments[i].fill
        t.segments[i] = {x = bg:x(), w = bg:w(), fill_h = fill:h()}
        local p = inst._absorb_health[i]
        t.health[i] = {
            visible = p:visible(), geom = geom(p), layer = p:layer(),
            on_fill = p:parent() == inst.health_fill, color = p:color(),
        }
        local d = inst._delayed_health and inst._delayed_health[i]
        t.debt_health[i] = d and {visible = d:visible(), geom = geom(d)}
            or {visible = false}
    end
    return t
end

_absorb_present = inst._absorb_armor ~= nil and type(inst._absorb_health) == "table"
if type(inst._absorb_health) == "table" then
    for i = 1, 4 do
        _absorb_present = _absorb_present and inst._absorb_health[i] ~= nil
    end
end
if not _absorb_present then return end

render(nil, nil)
local baseline = principal()

local ref_armor, ref_health
_absorb_identity = true
_absorb_identity_failure = nil
local function check_identity(phase)
    if inst._absorb_armor ~= ref_armor then
        _absorb_identity = false
        _absorb_identity_failure = phase
    end
    for i = 1, 4 do
        if inst._absorb_health[i] ~= ref_health[i] then
            _absorb_identity = false
            _absorb_identity_failure = phase
        end
    end
end

_absorb_cases = {}
_absorb_main = {}

render({known = true, amount = 60}, nil)
_absorb_cases.positive = sample()
_absorb_main.positive = same_principal(baseline, principal())
ref_armor = inst._absorb_armor
ref_health = {}
for i = 1, 4 do ref_health[i] = inst._absorb_health[i] end
check_identity("positive")

render(nil, debt60)
_absorb_cases.debt_only = sample()
_absorb_main.debt_only = same_principal(baseline, principal())
check_identity("debt_only")

render({known = true, amount = 60}, debt60)
_absorb_cases.simultaneous = sample()
_absorb_main.simultaneous = same_principal(baseline, principal())
check_identity("simultaneous")

render({known = true, amount = 0}, debt60)
_absorb_cases.zero = sample()
_absorb_main.zero = same_principal(baseline, principal())
check_identity("zero")

render({known = 0, amount = 60}, debt60)
_absorb_cases.known_zero = sample()
_absorb_main.known_zero = same_principal(baseline, principal())
check_identity("known_zero")

render({known = false, amount = 60}, debt60)
_absorb_cases.unknown = sample()
_absorb_main.unknown = same_principal(baseline, principal())
check_identity("unknown")

render(nil, debt60)
_absorb_cases.absent = sample()
_absorb_main.absent = same_principal(baseline, principal())
check_identity("absent")

render({known = true, amount = 60}, nil)
_absorb_cases.recovered = sample()
_absorb_main.recovered = same_principal(baseline, principal())
check_identity("recovered")

ref_armor:set_shape(ref_armor:x() - 5 * e, ref_armor:y(),
    ref_armor:w(), ref_armor:h())
_absorb_corrupt_verify = inst:verify()
check_identity("corrupt")

render({known = true, amount = 60}, nil)
_absorb_recovered_verify = inst:verify()
check_identity("rerendered")
_absorb_identity_after_rerender = _absorb_identity and inst._absorb_armor == ref_armor
'''


def _same_geom(a, b, delta=0.05):
    return all(abs(float(getattr(a, key)) - float(getattr(b, key))) <= delta
               for key in ("x", "y", "w", "h"))


def _same_rgb(a, b, delta=0.001):
    return all(abs(float(getattr(a, key)) - float(getattr(b, key))) <= delta
               for key in ("r", "g", "b"))


def _luma(color):
    return (0.299 * float(color.r) + 0.587 * float(color.g)
            + 0.114 * float(color.b))


class GaugeAbsorptionStripeTests(unittest.TestCase):
    """Absorption is a lower cyan stripe; absolute amount, no smoothing/blink.

    Source amount 60 splits armor current 25 first, then 35 health. The armor
    stripe mirrors the whole armor fill at y = 26*e (h = 3*e); health stripes
    use the [.25,.6] interval over gap-excluded SEGMENT_RATIOS like debt.
    Missing _absorb_* primitives fail RED explicitly; no runtime/native writes.
    """

    def test_absorption_stripe_overlays(self):
        for scale in (1.0, 0.672):
            with self.subTest(scale=scale):
                lua, ok = _lua()
                self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
                if not ok:
                    return

                lua.globals()._KY_scale = scale
                lua.execute(ABSORB_SCRIPT)
                g = lua.globals()

                self.assertTrue(bool(g._absorb_present),
                    f"scale {scale}: RED missing _absorb_armor or "
                    f"_absorb_health[1..4]")

                cases = g._absorb_cases
                positive = cases.positive

                self.assertTrue(bool(positive.verify),
                    f"scale {scale}: positive absorption render must verify")
                self.assertTrue(bool(g._absorb_main.positive),
                    f"scale {scale}: absorption must not alter main fills/numbers")

                armor = positive.armor
                self.assertTrue(bool(armor.visible),
                    f"scale {scale}: armor absorption stripe must be visible")
                self.assertAlmostEqual(float(armor.geom.x),
                    float(positive.armor_fill.x), delta=0.05,
                    msg=f"scale {scale}: armor stripe x must match armor_fill")
                self.assertAlmostEqual(float(armor.geom.w),
                    float(positive.armor_fill.w), delta=0.05,
                    msg=f"scale {scale}: armor stripe w must match armor_fill")
                self.assertAlmostEqual(float(positive.armor_bg.y), 3 * scale,
                    delta=0.05, msg=f"scale {scale}: armor track starts at y=3*e")
                self.assertAlmostEqual(float(positive.armor_bg.h), 26 * scale,
                    delta=0.05, msg=f"scale {scale}: armor track h must be 26*e")
                self.assertAlmostEqual(float(armor.geom.y), 26 * scale,
                    delta=0.05, msg=f"scale {scale}: armor stripe y must be 26*e")
                self.assertAlmostEqual(float(armor.geom.h), 3 * scale,
                    delta=0.05, msg=f"scale {scale}: armor stripe h must be 3*e")
                self.assertAlmostEqual(
                    float(armor.geom.y) + float(armor.geom.h),
                    float(positive.armor_bg.y) + float(positive.armor_bg.h),
                    delta=0.05,
                    msg=f"scale {scale}: armor stripe must end at armor track bottom")
                self.assertEqual(int(armor.layer), 2,
                    f"scale {scale}: armor stripe layer must be 2")
                self.assertTrue(bool(armor.on_root),
                    f"scale {scale}: armor stripe must stay on root")
                self.assertLess(int(armor.layer), int(positive.health_fill_layer),
                    f"scale {scale}: armor stripe must sit below health_fill")

                ink = armor.color
                self.assertGreater(float(ink.b), float(ink.r),
                    f"scale {scale}: absorption ink must be cyan")
                self.assertGreater(float(ink.g), float(ink.r),
                    f"scale {scale}: absorption ink must be cyan")
                self.assertGreaterEqual(float(ink.b), 0.5,
                    f"scale {scale}: absorption ink must be cyan, not orange")
                debt_ink = cases.debt_only.debt.color
                self.assertTrue(bool(cases.debt_only.debt.visible),
                    f"scale {scale}: debt reference must be visible")
                self.assertGreater(float(debt_ink.r), float(debt_ink.g),
                    f"scale {scale}: debt reference must stay orange")
                self.assertGreater(float(debt_ink.g), float(debt_ink.b),
                    f"scale {scale}: debt reference must stay orange")
                self.assertFalse(_same_rgb(ink, debt_ink),
                    f"scale {scale}: absorption cyan must differ from debt orange")

                ratios = (0.3, 0.2, 0.25, 0.25)
                lo, hi = 0.25, 0.6

                def intervals():
                    cursor = 0.0
                    for i, ratio in enumerate(ratios):
                        span = min(hi, cursor + ratio) - max(lo, cursor)
                        if span > 1e-9:
                            yield i, cursor, span
                        cursor += ratio

                visible = {i for i, _, _ in intervals()}
                self.assertEqual(visible, {0, 1, 2},
                    f"scale {scale}: absorption interval must cover segments 1-3")
                for i, cursor, span in intervals():
                    seg = positive.segments[i + 1]
                    stripe = positive.health[i + 1]
                    seg_lo, seg_w = float(seg.x), float(seg.w)
                    self.assertTrue(bool(stripe.visible),
                        f"scale {scale}: absorption segment {i + 1} must be visible")
                    self.assertAlmostEqual(float(stripe.geom.x),
                        seg_lo + seg_w * (max(lo, cursor) - cursor) / ratios[i],
                        delta=0.05,
                        msg=f"scale {scale}: absorption segment {i + 1} x")
                    self.assertAlmostEqual(float(stripe.geom.w),
                        seg_w * span / ratios[i], delta=0.05,
                        msg=f"scale {scale}: absorption segment {i + 1} w")
                    self.assertAlmostEqual(float(stripe.geom.y), 11 * scale,
                        delta=0.05,
                        msg=f"scale {scale}: absorption segment {i + 1} y")
                    self.assertAlmostEqual(float(stripe.geom.h), 3 * scale,
                        delta=0.05,
                        msg=f"scale {scale}: absorption segment {i + 1} h")
                    self.assertLessEqual(
                        float(stripe.geom.y) + float(stripe.geom.h),
                        float(seg.fill_h) + 0.05,
                        f"scale {scale}: absorption segment {i + 1} must stay "
                        f"inside health fill")
                    self.assertGreaterEqual(float(stripe.geom.x), seg_lo - 0.05,
                        f"scale {scale}: absorption segment {i + 1} left gap")
                    self.assertLessEqual(
                        float(stripe.geom.x) + float(stripe.geom.w),
                        seg_lo + seg_w + 0.05,
                        f"scale {scale}: absorption segment {i + 1} right gap")
                    self.assertEqual(int(stripe.layer), 3,
                        f"scale {scale}: absorption segment {i + 1} layer")
                    self.assertTrue(bool(stripe.on_fill),
                        f"scale {scale}: absorption segment {i + 1} on health_fill")
                    seg_ink = stripe.color
                    self.assertGreater(float(seg_ink.b), float(seg_ink.r),
                        f"scale {scale}: absorption segment {i + 1} must be cyan")
                    self.assertGreater(float(seg_ink.g), float(seg_ink.r),
                        f"scale {scale}: absorption segment {i + 1} must be cyan")
                    self.assertGreaterEqual(float(seg_ink.b), 0.5,
                        f"scale {scale}: absorption segment {i + 1} must be cyan")
                    self.assertFalse(_same_rgb(seg_ink, debt_ink),
                        f"scale {scale}: absorption segment {i + 1} is debt orange")
                for i in range(4):
                    if i not in visible:
                        self.assertFalse(bool(positive.health[i + 1].visible),
                            f"scale {scale}: absorption segment {i + 1} "
                            f"outside [.25,.6] must be hidden")

                sim = cases.simultaneous
                self.assertTrue(bool(sim.verify),
                    f"scale {scale}: simultaneous debt+absorption must verify")
                self.assertTrue(bool(g._absorb_main.simultaneous),
                    f"scale {scale}: simultaneous effects must not alter main")
                self.assertTrue(bool(sim.armor.visible),
                    f"scale {scale}: simultaneous absorption must remain visible")
                self.assertTrue(bool(sim.debt.visible),
                    f"scale {scale}: simultaneous debt must remain visible")
                self.assertTrue(_same_geom(sim.armor.geom, armor.geom),
                    f"scale {scale}: simultaneous absorption must stay skinny")
                self.assertAlmostEqual(float(sim.armor.geom.h), 3 * scale,
                    delta=0.05,
                    msg=f"scale {scale}: simultaneous absorption h must be 3*e")
                self.assertAlmostEqual(float(sim.debt.geom.h),
                    float(sim.armor_fill.h), delta=0.05,
                    msg=f"scale {scale}: simultaneous debt must keep full height")
                self.assertGreater(float(sim.debt.geom.h),
                    float(sim.armor.geom.h),
                    f"scale {scale}: absorption must stay a skinny stripe")
                self.assertTrue(_same_rgb(sim.armor.color, ink),
                    f"scale {scale}: simultaneous absorption cyan must remain")
                self.assertTrue(
                    _same_rgb(sim.debt.color, cases.debt_only.debt.color),
                    f"scale {scale}: simultaneous debt orange must remain")
                for i, cursor, span in intervals():
                    stripe = sim.health[i + 1]
                    debt = sim.debt_health[i + 1]
                    seg = sim.segments[i + 1]
                    self.assertTrue(bool(stripe.visible) and bool(debt.visible),
                        f"scale {scale}: simultaneous segment {i + 1} both visible")
                    self.assertAlmostEqual(float(stripe.geom.x),
                        float(debt.geom.x), delta=0.05,
                        msg=f"scale {scale}: simultaneous segment {i + 1} x")
                    self.assertAlmostEqual(float(stripe.geom.w),
                        float(debt.geom.w), delta=0.05,
                        msg=f"scale {scale}: simultaneous segment {i + 1} w")
                    self.assertAlmostEqual(float(stripe.geom.y), 11 * scale,
                        delta=0.05,
                        msg=f"scale {scale}: simultaneous segment {i + 1} stripe y")
                    self.assertAlmostEqual(float(stripe.geom.h), 3 * scale,
                        delta=0.05,
                        msg=f"scale {scale}: simultaneous segment {i + 1} stripe h")
                    self.assertAlmostEqual(float(debt.geom.y), 0.0,
                        delta=0.05,
                        msg=f"scale {scale}: simultaneous segment {i + 1} debt y")
                    self.assertAlmostEqual(float(debt.geom.h),
                        float(seg.fill_h), delta=0.05,
                        msg=f"scale {scale}: simultaneous segment {i + 1} debt h")

                debt_ref = cases.debt_only
                self.assertTrue(bool(debt_ref.verify),
                    f"scale {scale}: debt-only reference must verify")
                self.assertTrue(bool(g._absorb_main.debt_only),
                    f"scale {scale}: debt-only must not alter main")
                for phase in ("zero", "known_zero", "unknown", "absent"):
                    case = cases[phase]
                    self.assertTrue(bool(case.verify),
                        f"scale {scale}: {phase} absorption render must verify")
                    self.assertTrue(bool(g._absorb_main[phase]),
                        f"scale {scale}: {phase} must not alter main")
                    self.assertFalse(bool(case.armor.visible),
                        f"scale {scale}: {phase} must hide armor absorption")
                    for i in range(4):
                        self.assertFalse(bool(case.health[i + 1].visible),
                            f"scale {scale}: {phase} must hide absorption "
                            f"segment {i + 1}")
                    self.assertTrue(bool(case.debt.visible),
                        f"scale {scale}: {phase} must retain active debt")
                    self.assertTrue(_same_geom(case.debt.geom, debt_ref.debt.geom),
                        f"scale {scale}: {phase} must not move active debt")
                    for i in range(4):
                        debt = case.debt_health[i + 1]
                        ref = debt_ref.debt_health[i + 1]
                        self.assertEqual(bool(debt.visible), bool(ref.visible),
                            f"scale {scale}: {phase} debt segment {i + 1} visibility")
                        if ref.visible:
                            self.assertTrue(_same_geom(debt.geom, ref.geom),
                                f"scale {scale}: {phase} debt segment {i + 1} geom")

                recovered = cases.recovered
                self.assertTrue(bool(recovered.verify),
                    f"scale {scale}: recovered absorption must verify")
                self.assertTrue(bool(g._absorb_main.recovered),
                    f"scale {scale}: recovery must not alter main")
                self.assertTrue(bool(recovered.armor.visible),
                    f"scale {scale}: recovered armor absorption must be visible")
                self.assertTrue(_same_geom(recovered.armor.geom, armor.geom),
                    f"scale {scale}: recovered armor stripe must match positive")
                for i in range(4):
                    self.assertEqual(bool(recovered.health[i + 1].visible),
                        bool(positive.health[i + 1].visible),
                        f"scale {scale}: recovered segment {i + 1} visibility")

                self.assertFalse(bool(g._absorb_corrupt_verify),
                    f"scale {scale}: verify must reject a corrupted absorption x")
                self.assertTrue(bool(g._absorb_recovered_verify),
                    f"scale {scale}: verify must recover after absorption rerender")
                self.assertTrue(bool(g._absorb_identity_after_rerender),
                    f"scale {scale}: absorption identity must survive rerender")
                self.assertTrue(bool(g._absorb_identity),
                    f"scale {scale}: absorption identity lost at "
                    f"{g._absorb_identity_failure}")


COPR_SCRIPT = r'''
local G = kyohud.hud.gauge
local parent = _G.panel_double
local e = _KY_scale
local RATIOS = {0.3, 0.2, 0.25, 0.25}
local MW = math.ceil(2 * e)

local inst = G.new(parent, "copr_" .. tostring(e))
inst:set_geometry(0, 0, 440 * e, 42 * e)

local hp = {current = 60, total = 100, ratio = 0.6, valid = true, provenance = "local"}
local ar = {current = 50, total = 100, ratio = 0.5, valid = true, provenance = "local"}
local ACTIVE2 = {copr = {known = true, active = true, static_damage_ratio = 0.2}}
local ACTIVE3 = {copr = {known = true, active = true, static_damage_ratio = 0.3}}

local function render(effects)
    inst:render(hp, ar, "percentage", 10, nil, effects)
end

local function geom(p) return {p:x(), p:y(), p:w(), p:h()} end

local function same_geom(a, b)
    for i = 1, 4 do
        if math.abs(a[i] - b[i]) > 0.01 then return false end
    end
    return true
end

local function main_snapshot()
    local s = {health_text = inst.health_text:text(), armor_text = inst.armor_text:text()}
    for i = 1, 4 do
        s["hbg" .. i] = geom(inst.health_segments[i].background)
        s["hfill" .. i] = geom(inst.health_segments[i].fill)
    end
    return s
end

local function same_main(a, b)
    if a.health_text ~= b.health_text or a.armor_text ~= b.armor_text then return false end
    for i = 1, 4 do
        if not same_geom(a["hbg" .. i], b["hbg" .. i]) then return false end
        if not same_geom(a["hfill" .. i], b["hfill" .. i]) then return false end
    end
    return true
end

render(nil)
local baseline = main_snapshot()
_main_ok = true
_main_failure = nil
local function check_main(phase)
    if not same_main(baseline, main_snapshot()) then
        _main_ok = false
        _main_failure = phase
    end
end

local function marker_list(n)
    local v = {}
    for i = 1, n do
        v[i] = inst._copr_markers[i] and inst._copr_markers[i]:visible() or false
    end
    return v
end

local function all_hidden()
    for i = 1, #inst._copr_markers do
        if inst._copr_markers[i]:visible() then return false end
    end
    return true
end

-- Thresholds follow native hudteammate.lua:2615-2668: N = ceil(1/ratio) and
-- threshold_i = 1 - (i-1)/N. Map each threshold through the real segment
-- backgrounds; a notch stays inside its segment and never straddles a gap.
local function threshold_ok(t, m)
    local lo, w = 0, m:w()
    for i = 1, 4 do
        local hi = lo + RATIOS[i]
        if t >= lo - 1e-9 and t <= hi + 1e-9 then
            local bg = inst.health_segments[i].background
            local f = math.max(0, math.min(1, (t - lo) / RATIOS[i]))
            local base = bg:x() + bg:w() * f
            local maxx = bg:x() + bg:w() - w
            if maxx < bg:x() then maxx = bg:x() end
            local left = math.max(bg:x(), math.min(base, maxx))
            local center = math.max(bg:x(), math.min(base - w / 2, maxx))
            if (math.abs(m:x() - left) <= 0.6 * e
                or math.abs(m:x() - center) <= 0.6 * e)
                and m:x() >= bg:x() - 0.01
                and m:x() + w <= bg:x() + bg:w() + 0.01 then
                return true
            end
        end
        lo = hi
    end
    return false
end

render(ACTIVE2)
_copr_present = type(inst._copr_markers) == "table"
if not _copr_present then return end
_copr_verify5 = inst:verify()
_copr_count5 = #inst._copr_markers
_copr_visible5 = marker_list(5)
_copr_refs = {}
for i = 1, 5 do _copr_refs[i] = inst._copr_markers[i] end

_copr_parent_ok = true
_copr_layer_ok = true
_copr_size_ok = true
_copr_pos_ok = true
_copr_pos_fail = nil
for i = 1, _copr_count5 do
    local m = inst._copr_markers[i]
    local t = 1 - (i - 1) / _copr_count5
    if m:parent() ~= inst.health_fill then _copr_parent_ok = false end
    if m:layer() ~= 4 then _copr_layer_ok = false end
    if math.abs(m:w() - MW) > 0.01 or math.abs(m:h() - 14 * e) > 0.01 then
        _copr_size_ok = false
    end
    if m:visible() and not threshold_ok(t, m) then
        _copr_pos_ok = false
        _copr_pos_fail = i
    end
end
check_main("active_0.2")

_copr_identity_ok = true
_copr_identity_fail = nil
local function check_identity(phase)
    for i = 1, 5 do
        if inst._copr_markers[i] ~= _copr_refs[i] then
            _copr_identity_ok = false
            _copr_identity_fail = phase
        end
    end
end

render(ACTIVE3)
_copr_verify4 = inst:verify()
_copr_retained = #inst._copr_markers
_copr_visible4 = marker_list(4)
_copr_surplus_hidden = inst._copr_markers[5] ~= nil
    and not inst._copr_markers[5]:visible()
_copr_pos4_ok = true
_copr_pos4_fail = nil
for i = 1, math.min(4, _copr_retained) do
    local m = inst._copr_markers[i]
    local t = 1 - (i - 1) / 4
    if m:visible() and not threshold_ok(t, m) then
        _copr_pos4_ok = false
        _copr_pos4_fail = i
    end
end
check_identity("active_0.3")
check_main("active_0.3")

render({copr = {known = false}})
_copr_known_false = {verify = inst:verify(), hidden = all_hidden()}
check_identity("known_false")
check_main("known_false")

render({copr = {known = true, active = false, static_damage_ratio = 0.2}})
_copr_active_false = {verify = inst:verify(), hidden = all_hidden()}
check_identity("active_false")
check_main("active_false")

render(nil)
_copr_absent = {verify = inst:verify(), hidden = all_hidden()}
check_identity("absent")
check_main("absent")

render(ACTIVE2)
_copr_restore_verify = inst:verify()
_copr_restore_visible = marker_list(5)
check_identity("restored")
check_main("restored")

local m3 = inst._copr_markers[3]
m3:set_shape(m3:x() - 5 * e, m3:y(), m3:w(), m3:h())
_copr_corrupt_verify = inst:verify()
check_identity("corrupt")
render(ACTIVE2)
_copr_recover_verify = inst:verify()
check_identity("recovered")
check_main("recovered")

-- N = ceil(1/.01) = 100 exceeds the 64-marker cap: owned notches stay hidden.
render({copr = {known = true, active = true, static_damage_ratio = 0.01}})
_copr_overcap_count = #inst._copr_markers
_copr_overcap_hidden = all_hidden()
_copr_overcap_verify = inst:verify()
check_main("overcap")
'''


def _copr_expected_visible(n, health_ratio=0.6):
    return [1 - k / n <= health_ratio + 0.01 for k in range(n)]


class GaugeCoprNotchTests(unittest.TestCase):
    """COPR static-damage notches mirrored from native hudteammate.lua:2615-2668.

    N = ceil(1 / static_damage_ratio) and threshold_i = 1 - (i-1)/N, not
    arbitrary static-ratio increments. A notch is visible when
    threshold <= health_ratio + .01. Owned markers are retained in a bounded
    (<=64) array under health_fill at layer 4. RED: _copr_markers is not
    implemented yet; no native writes or production edits in this pass.
    """

    def test_copr_notch_thresholds_and_retention(self):
        for scale in (1.0, 0.672):
            with self.subTest(scale=scale):
                lua, ok = _lua()
                self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
                if not ok:
                    return

                lua.globals()._KY_scale = scale
                lua.execute(COPR_SCRIPT)
                g = lua.globals()

                self.assertTrue(bool(g._copr_present),
                    f"scale {scale}: RED missing instance._copr_markers")

                self.assertEqual(int(g._copr_count5), 5,
                    f"scale {scale}: ratio .2 must allocate ceil(1/.2)=5 notches")
                self.assertTrue(bool(g._copr_verify5),
                    f"scale {scale}: ratio .2 render must verify")
                self.assertTrue(bool(g._copr_parent_ok),
                    f"scale {scale}: notches must be health_fill children")
                self.assertTrue(bool(g._copr_layer_ok),
                    f"scale {scale}: notches must sit on layer 4")
                self.assertTrue(bool(g._copr_size_ok),
                    f"scale {scale}: notch must be ceil(2e) wide and 14e tall")
                self.assertTrue(bool(g._copr_pos_ok),
                    f"scale {scale}: notch {g._copr_pos_fail} must map its "
                    f"threshold through segment geometry without covering gaps")

                got5 = [bool(g._copr_visible5[i]) for i in range(1, 6)]
                self.assertEqual(got5, _copr_expected_visible(5),
                    f"scale {scale}: ratio .2 thresholds 1 .8 .6 .4 .2 must "
                    f"show only .6 .4 .2")

                self.assertEqual(int(g._copr_retained), 5,
                    f"scale {scale}: retained array must keep the 5 allocated "
                    f"notches when ratio .3 needs only 4")
                got4 = [bool(g._copr_visible4[i]) for i in range(1, 5)]
                self.assertEqual(got4, _copr_expected_visible(4),
                    f"scale {scale}: ratio .3 thresholds 1 .75 .5 .25 must "
                    f"show only .5 .25")
                self.assertTrue(bool(g._copr_surplus_hidden),
                    f"scale {scale}: retained notch 5 must be hidden for N=4")
                self.assertTrue(bool(g._copr_verify4),
                    f"scale {scale}: ratio .3 render must verify")
                self.assertTrue(bool(g._copr_pos4_ok),
                    f"scale {scale}: ratio .3 notch {g._copr_pos4_fail} must "
                    f"map its threshold")

                for name in ("known_false", "active_false", "absent"):
                    phase = getattr(g, f"_copr_{name}")
                    self.assertTrue(bool(phase.verify),
                        f"scale {scale}: {name} render must verify")
                    self.assertTrue(bool(phase.hidden),
                        f"scale {scale}: {name} must hide every allocated notch")

                self.assertTrue(bool(g._copr_identity_ok),
                    f"scale {scale}: marker identity lost at "
                    f"{g._copr_identity_fail}")

                self.assertTrue(bool(g._copr_restore_verify),
                    f"scale {scale}: re-enabling COPR must verify")
                self.assertEqual(
                    [bool(g._copr_restore_visible[i]) for i in range(1, 6)],
                    _copr_expected_visible(5),
                    f"scale {scale}: re-enabled visibility must be restored")

                self.assertFalse(bool(g._copr_corrupt_verify),
                    f"scale {scale}: verify must reject a corrupted notch x")
                self.assertTrue(bool(g._copr_recover_verify),
                    f"scale {scale}: same-effects rerender must recover")

                self.assertLessEqual(int(g._copr_overcap_count), 64,
                    f"scale {scale}: retained array must stay capped at 64")
                self.assertTrue(bool(g._copr_overcap_hidden),
                    f"scale {scale}: N=100 exceeds the cap and must not draw "
                    f"owned notches")
                self.assertTrue(bool(g._copr_overcap_verify),
                    f"scale {scale}: over-cap render must remain verifiable")

                self.assertTrue(bool(g._main_ok),
                    f"scale {scale}: COPR changed main strings/fills at "
                    f"{g._main_failure}")


INFO_METER_SCRIPT = r'''
local G = kyohud.hud.gauge
local parent = _G.panel_double
local e = _KY_scale

local inst = G.new(parent, "info_meter_" .. tostring(e))
inst:set_geometry(0, 0, 440 * e, 42 * e)

local hp = {current = 60, total = 100, ratio = 0.6, valid = true, provenance = "local"}
local ar = {current = 25, total = 50, ratio = 0.5, valid = true, provenance = "local"}
local POSITIVE = {known = true, current = 0.2, total = 0.8, max = 1}

local function render(info)
    local effects = nil
    if info ~= nil then effects = {info_meter = info} end
    inst:render(hp, ar, "percentage", 10, nil, effects)
end

local function geom(p) return {x = p:x(), y = p:y(), w = p:w(), h = p:h()} end

local function same_geom(a, b)
    return math.abs(a.x - b.x) <= 0.01 and math.abs(a.y - b.y) <= 0.01
        and math.abs(a.w - b.w) <= 0.01 and math.abs(a.h - b.h) <= 0.01
end

local function main_snapshot()
    local s = {
        health_text = inst.health_text:text(),
        armor_text = inst.armor_text:text(),
        armor_bg = geom(inst._armor_bg),
        armor_fill = geom(inst.armor_fill),
        health_fill = geom(inst.health_fill),
        segs = {},
    }
    for i = 1, 4 do
        s.segs[i] = {
            bg = geom(inst.health_segments[i].background),
            fill = geom(inst.health_segments[i].fill),
        }
    end
    return s
end

local function same_main(a, b)
    if a.health_text ~= b.health_text or a.armor_text ~= b.armor_text then return false end
    if not same_geom(a.armor_bg, b.armor_bg)
        or not same_geom(a.armor_fill, b.armor_fill)
        or not same_geom(a.health_fill, b.health_fill) then
        return false
    end
    for i = 1, 4 do
        if not same_geom(a.segs[i].bg, b.segs[i].bg)
            or not same_geom(a.segs[i].fill, b.segs[i].fill) then
            return false
        end
    end
    return true
end

render(nil)
local baseline = main_snapshot()
_track_x = baseline.armor_bg.x
_track_w = baseline.armor_bg.w
_main_ok = true
_main_failure = nil
local function check_main(phase)
    if not same_main(baseline, main_snapshot()) then
        _main_ok = false
        _main_failure = phase
    end
end

local bg = inst._info_meter_bg
local fill = inst._info_meter_fill
_info_meter_present = bg ~= nil and fill ~= nil
if not _info_meter_present then return end

local bg_ref, fill_ref = bg, fill
_identity_ok = true
_identity_failure = nil
local function check_identity(phase)
    if inst._info_meter_bg ~= bg_ref or inst._info_meter_fill ~= fill_ref then
        _identity_ok = false
        _identity_failure = phase
    end
end

local function sample()
    return {
        verify = inst:verify(),
        bg = {visible = bg:visible(), geom = geom(bg), layer = bg:layer(),
            on_root = bg:parent() == inst.root},
        fill = {visible = fill:visible(), geom = geom(fill), layer = fill:layer(),
            on_root = fill:parent() == inst.root},
    }
end

_cases = {}
_main = {}
local function capture(name)
    _cases[name] = sample()
    _main[name] = same_main(baseline, main_snapshot())
    check_identity(name)
end

render(POSITIVE)
capture("positive")
check_main("positive")
_armor_color = inst.armor_fill:color()
_bg_color = bg:color()
_fill_color = fill:color()

fill:set_shape(fill:x() - 5 * e, fill:y(), fill:w(), fill:h())
_corrupt_fill_verify = inst:verify()
check_identity("fill_x_corrupt")
check_main("fill_x_corrupt")
render(POSITIVE)
_recover_fill_verify = inst:verify()
check_identity("fill_x_recovered")
check_main("fill_x_recovered")

-- Ordered state matrix: only the info meter changes, never debt/absorb/timer.
local states = {
    {"current_zero", {known = true, current = 0, total = 0.8, max = 1}},
    {"both_zero", {known = true, current = 0, total = 0, max = 1}},
    {"unknown", {known = false, current = 0.2, total = 0.8, max = 1}},
    {"absent", nil},
    {"max_zero", {known = true, current = 0.2, total = 0.8, max = 0}},
    {"max_inf", {known = true, current = 0.2, total = 0.8, max = math.huge}},
    {"max_nan", {known = true, current = 0.2, total = 0.8, max = 0 / 0}},
}
for _, state in ipairs(states) do
    render(state[2])
    capture(state[1])
    check_main(state[1])
end

render({known = true, current = 0, total = 0, max = 1})
_forced_hidden_verify_before = inst:verify()
bg:set_visible(true)
_forced_hidden_verify = inst:verify()
check_identity("hidden_bg_forced")
render({known = true, current = 0, total = 0, max = 1})
_forced_recover_verify = inst:verify()
_forced_recover_bg_visible = bg:visible()
_forced_recover_fill_visible = fill:visible()
check_identity("hidden_recovered")
check_main("hidden_recovered")

render(POSITIVE)
_final_verify = inst:verify()
check_identity("final_positive")
check_main("final_positive")
'''


class GaugeInfoMeterTests(unittest.TestCase):
    """Info meter: total/max is the track, current/max is the fill.

    Both are owned root rects on layer 3 inside the armor upper rim
    (y = 3*e, h = 2*e) starting at _armor_bg.x. Total and current stay
    distinct, colors stay non-white and readable, and zero/unknown/max-invalid
    states hide both without bad geometry. RED: the two primitives do not
    exist yet; no production edits, native writes or other effects here.
    """

    def test_info_meter_track_and_fill_are_distinct(self):
        for scale in (1.0, 0.672):
            with self.subTest(scale=scale):
                lua, ok = _lua()
                self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
                if not ok:
                    return

                lua.globals()._KY_scale = scale
                lua.execute(INFO_METER_SCRIPT)
                g = lua.globals()

                self.assertTrue(bool(g._info_meter_present),
                    f"scale {scale}: RED missing instance._info_meter_bg or "
                    f"instance._info_meter_fill")
                if not bool(g._info_meter_present):
                    return

                cases = g._cases
                positive = cases.positive
                track_x = float(g._track_x)
                track_w = float(g._track_w)

                self.assertTrue(bool(positive.verify),
                    f"scale {scale}: positive info meter render must verify")
                self.assertTrue(bool(g._main.positive),
                    f"scale {scale}: info meter must not alter main "
                    f"geometry/strings")

                for name in ("bg", "fill"):
                    prim = getattr(positive, name)
                    self.assertTrue(bool(prim.visible),
                        f"scale {scale}: positive info {name} must be visible")
                    self.assertEqual(int(prim.layer), 3,
                        f"scale {scale}: info {name} must sit on layer 3")
                    self.assertTrue(bool(prim.on_root),
                        f"scale {scale}: info {name} must be a root rect")
                    self.assertAlmostEqual(float(prim.geom.x), track_x,
                        delta=0.01,
                        msg=f"scale {scale}: info {name} x must match _armor_bg x")
                    self.assertAlmostEqual(float(prim.geom.y), 3 * scale,
                        delta=0.01,
                        msg=f"scale {scale}: info {name} y must be 3*e")
                    self.assertAlmostEqual(float(prim.geom.h), 2 * scale,
                        delta=0.01,
                        msg=f"scale {scale}: info {name} h must be 2*e")
                self.assertAlmostEqual(float(positive.bg.geom.w),
                    track_w * 0.8, delta=0.01,
                    msg=f"scale {scale}: info bg width must be total/max * "
                        f"armor track width")
                self.assertAlmostEqual(float(positive.fill.geom.w),
                    track_w * 0.2, delta=0.01,
                    msg=f"scale {scale}: info fill width must be current/max * "
                        f"armor track width")
                self.assertGreater(
                    abs(float(positive.bg.geom.w) - float(positive.fill.geom.w)),
                    0.01,
                    f"scale {scale}: total/max and current/max must stay distinct")

                armor = g._armor_color
                bg_ink = g._bg_color
                fill_ink = g._fill_color
                self.assertIsNotNone(armor,
                    f"scale {scale}: armor fill color missing")
                self.assertIsNotNone(bg_ink,
                    f"scale {scale}: info bg color missing")
                self.assertIsNotNone(fill_ink,
                    f"scale {scale}: info fill color missing")
                self.assertFalse(_same_rgb(armor, bg_ink),
                    f"scale {scale}: info bg must not be plain white armor")
                self.assertFalse(_same_rgb(armor, fill_ink),
                    f"scale {scale}: info fill must not be plain white armor")
                self.assertFalse(_same_rgb(bg_ink, fill_ink),
                    f"scale {scale}: info bg and fill must differ")
                self.assertGreaterEqual(abs(_luma(bg_ink) - _luma(fill_ink)), 0.2,
                    f"scale {scale}: info fill must read against the info bg")

                self.assertFalse(bool(g._corrupt_fill_verify),
                    f"scale {scale}: verify must reject a corrupted info fill x")
                self.assertTrue(bool(g._recover_fill_verify),
                    f"scale {scale}: verify must recover after info fill rerender")

                hidden = {
                    "both_zero": "both zero",
                    "unknown": "known=false",
                    "absent": "absent effects",
                    "max_zero": "max=0",
                    "max_inf": "max=inf",
                    "max_nan": "max=NaN",
                }
                for name, label in hidden.items():
                    case = cases[name]
                    self.assertTrue(bool(case.verify),
                        f"scale {scale}: {label} info render must verify")
                    self.assertFalse(bool(case.bg.visible),
                        f"scale {scale}: {label} must hide info bg")
                    self.assertFalse(bool(case.fill.visible),
                        f"scale {scale}: {label} must hide info fill")
                    self.assertTrue(bool(g._main[name]),
                        f"scale {scale}: {label} must not alter main")
                    for part in ("bg", "fill"):
                        prim = getattr(case, part)
                        for key in ("x", "y", "w", "h"):
                            value = float(getattr(prim.geom, key))
                            self.assertTrue(math.isfinite(value),
                                f"scale {scale}: {label} info {part}.{key} "
                                f"must stay finite")
                        self.assertGreaterEqual(float(prim.geom.w), 0.0,
                            f"scale {scale}: {label} info {part} width must not "
                            f"go negative")
                        self.assertGreaterEqual(float(prim.geom.h), 0.0,
                            f"scale {scale}: {label} info {part} height must not "
                            f"go negative")

                zero = cases.current_zero
                self.assertTrue(bool(zero.verify),
                    f"scale {scale}: current=0 info render must verify")
                self.assertTrue(bool(zero.bg.visible),
                    f"scale {scale}: current=0 keeps the info bg visible")
                self.assertAlmostEqual(float(zero.bg.geom.w),
                    track_w * 0.8, delta=0.01,
                    msg=f"scale {scale}: current=0 bg still spans total/max")
                self.assertAlmostEqual(float(zero.fill.geom.w), 0.0,
                    delta=0.01,
                    msg=f"scale {scale}: current=0 collapses the info fill width")
                self.assertTrue(bool(g._main.current_zero),
                    f"scale {scale}: current=0 must not alter main")

                self.assertTrue(bool(g._forced_hidden_verify_before),
                    f"scale {scale}: hidden info meter must verify before mutation")
                self.assertFalse(bool(g._forced_hidden_verify),
                    f"scale {scale}: verify must reject a hidden info bg forced "
                    f"visible")
                self.assertTrue(bool(g._forced_recover_verify),
                    f"scale {scale}: verify must recover after hiding again")
                self.assertFalse(bool(g._forced_recover_bg_visible),
                    f"scale {scale}: recovery must hide the info bg")
                self.assertFalse(bool(g._forced_recover_fill_visible),
                    f"scale {scale}: recovery must hide the info fill")

                self.assertTrue(bool(g._final_verify),
                    f"scale {scale}: positive info meter must recover")
                self.assertAlmostEqual(float(cases.positive.bg.geom.w),
                    track_w * 0.8, delta=0.01,
                    msg=f"scale {scale}: recovered bg width must stay total/max")
                self.assertAlmostEqual(float(cases.positive.fill.geom.w),
                    track_w * 0.2, delta=0.01,
                    msg=f"scale {scale}: recovered fill width must stay current/max")
                self.assertTrue(bool(g._identity_ok),
                    f"scale {scale}: info primitive identity lost at "
                    f"{g._identity_failure}")
                self.assertTrue(bool(g._main_ok),
                    f"scale {scale}: main geometry/strings changed at "
                    f"{g._main_failure}")


CUSTOM_RADIAL_SCRIPT = r'''
local G = kyohud.hud.gauge
local parent = _G.panel_double
local e = _KY_scale

local inst = G.new(parent, "custom_" .. tostring(e))
inst:set_geometry(0, 0, 440 * e, 42 * e)

-- Swansong-like local state: current HP is proven zero, the custom progress
-- comes only from custom_radial and must never be inferred from extra health.
local hp = {current = 0, total = 100, ratio = 0, valid = true, provenance = "local"}
local ar = {current = 50, total = 100, ratio = 0.5, valid = true, provenance = "local"}
local POSITIVE = {custom_radial = {known = true, current = 60, total = 100, ratio = 0.6}}

local function render(effects)
    inst:render(hp, ar, "percentage", 10, nil, effects)
end

local function geom(p) return {x = p:x(), y = p:y(), w = p:w(), h = p:h()} end

local function same_geom(a, b)
    return math.abs(a.x - b.x) <= 0.05 and math.abs(a.y - b.y) <= 0.05
        and math.abs(a.w - b.w) <= 0.05 and math.abs(a.h - b.h) <= 0.05
end

local function main_snapshot()
    local s = {health_text = inst.health_text:text(), armor_text = inst.armor_text:text(), fills = {}}
    for i = 1, 4 do s.fills[i] = geom(inst.health_segments[i].fill) end
    return s
end

local function same_main(a, b)
    if a.health_text ~= b.health_text or a.armor_text ~= b.armor_text then return false end
    for i = 1, 4 do
        if not same_geom(a.fills[i], b.fills[i]) then return false end
    end
    return true
end

render(nil)
local baseline = main_snapshot()
_main_ok = true
_main_failure = nil
local function check_main(phase)
    if not same_main(baseline, main_snapshot()) then
        _main_ok = false
        _main_failure = phase
    end
end

_custom_present = type(inst._custom_health) == "table"
if _custom_present then
    for i = 1, 4 do
        _custom_present = _custom_present and inst._custom_health[i] ~= nil
    end
end
if not _custom_present then return end

local refs = {}
for i = 1, 4 do refs[i] = inst._custom_health[i] end
_identity_ok = true
_identity_failure = nil
local function check_identity(phase)
    for i = 1, 4 do
        if inst._custom_health[i] ~= refs[i] then
            _identity_ok = false
            _identity_failure = phase
        end
    end
end

_cases = {}
local function capture(phase)
    local stripes = {}
    for i = 1, 4 do
        local p = inst._custom_health[i]
        stripes[i] = {
            visible = p:visible(), geom = geom(p), layer = p:layer(),
            on_fill = p:parent() == inst.health_fill, color = p:color(),
            seg = geom(inst.health_segments[i].background),
        }
    end
    _cases[phase] = {verify = inst:verify(), stripes = stripes}
    check_identity(phase)
    check_main(phase)
end

render(POSITIVE)
capture("positive")
_hp_zero = true
for i = 1, 4 do
    if math.abs(inst.health_segments[i].fill:w()) > 0.01 then _hp_zero = false end
end
_hp_text = inst.health_text:text()
_hp_ink = inst.health_segments[1].fill:color()
_debt_ink = inst._delayed_armor and inst._delayed_armor:color() or nil

local ref = inst._custom_health[1]
ref:set_shape(ref:x() - 5 * e, ref:y(), ref:w(), ref:h())
_corrupt_verify = inst:verify()
check_identity("corrupt")
render(POSITIVE)
_recover_verify = inst:verify()
_recover_geom_ok = true
for i = 1, 4 do
    if not same_geom(_cases.positive.stripes[i].geom,
        geom(inst._custom_health[i])) then
        _recover_geom_ok = false
    end
end
check_identity("recovered")
check_main("recovered")

local hidden = {
    {"ratio_zero", {custom_radial = {known = true, current = 0, total = 100, ratio = 0}}},
    {"unknown", {custom_radial = {known = false, current = 60, total = 100, ratio = 0.6}}},
    {"absent", nil},
    {"mismatch", {custom_radial = {known = true, current = 60, total = 100, ratio = 0.2}}},
    {"ratio_inf", {custom_radial = {known = true, current = 60, total = 100, ratio = math.huge}}},
    {"ratio_nan", {custom_radial = {known = true, current = 60, total = 100, ratio = 0 / 0}}},
    {"current_inf", {custom_radial = {known = true, current = math.huge, total = 100, ratio = 0.6}}},
    {"total_zero", {custom_radial = {known = true, current = 60, total = 0, ratio = 0.6}}},
}
for _, state in ipairs(hidden) do
    render(state[2])
    capture(state[1])
end

render(POSITIVE)
capture("restored")
'''


class GaugeCustomStateStripeTests(unittest.TestCase):
    """Custom progress stripe is independent from a proven-zero current HP.

    ``inst._custom_health[1..4]`` are retained health_fill children on layer 3,
    top stripe y = 0 and h = 4*e, magenta and distinct from debt/HP ink.
    custom_radial.ratio .6 fills segments 1-2 and 40% of segment 3, hides
    segment 4 and never crosses a gap. Mismatched/non-finite data hides every
    stripe instead of inferring extra health. RED until gauge implements it.
    """

    def test_custom_state_stripe_is_independent_of_current_hp(self):
        for scale in (1.0, 0.672):
            with self.subTest(scale=scale):
                lua, ok = _lua()
                self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
                if not ok:
                    return

                lua.globals()._KY_scale = scale
                lua.execute(CUSTOM_RADIAL_SCRIPT)
                g = lua.globals()

                self.assertTrue(bool(g._custom_present),
                    f"scale {scale}: RED missing instance._custom_health[1..4]")
                if not bool(g._custom_present):
                    return

                positive = g._cases.positive
                self.assertTrue(bool(positive.verify),
                    f"scale {scale}: positive custom stripe render must verify")
                self.assertTrue(bool(g._main_ok),
                    f"scale {scale}: custom stripe altered main HP at "
                    f"{g._main_failure}")
                self.assertTrue(bool(g._hp_zero),
                    f"scale {scale}: current HP must stay zero")
                self.assertEqual(g._hp_text, "0%",
                    f"scale {scale}: main HP text must stay 0%")

                expected = (1.0, 1.0, 0.1 / 0.25, 0.0)
                for i in range(4):
                    stripe = positive.stripes[i + 1]
                    seg = stripe.seg
                    if expected[i] > 1e-9:
                        self.assertTrue(bool(stripe.visible),
                            f"scale {scale}: custom stripe {i + 1} must be visible")
                        self.assertTrue(bool(stripe.on_fill),
                            f"scale {scale}: custom stripe {i + 1} must be a "
                            f"health_fill child")
                        self.assertEqual(int(stripe.layer), 3,
                            f"scale {scale}: custom stripe {i + 1} layer must be 3")
                        self.assertAlmostEqual(float(stripe.geom.y), 0.0,
                            delta=0.05,
                            msg=f"scale {scale}: custom stripe {i + 1} top y must be 0")
                        self.assertAlmostEqual(float(stripe.geom.h), 4 * scale,
                            delta=0.05,
                            msg=f"scale {scale}: custom stripe {i + 1} h must be 4*e")
                        self.assertAlmostEqual(float(stripe.geom.x), float(seg.x),
                            delta=0.05,
                            msg=f"scale {scale}: custom stripe {i + 1} x must "
                                f"match its segment background")
                        self.assertAlmostEqual(float(stripe.geom.w),
                            float(seg.w) * expected[i], delta=0.05,
                            msg=f"scale {scale}: custom stripe {i + 1} width must "
                                f"follow ratio .6")
                        self.assertGreaterEqual(float(stripe.geom.x),
                            float(seg.x) - 0.05,
                            f"scale {scale}: custom stripe {i + 1} left gap")
                        self.assertLessEqual(
                            float(stripe.geom.x) + float(stripe.geom.w),
                            float(seg.x) + float(seg.w) + 0.05,
                            f"scale {scale}: custom stripe {i + 1} right gap")
                    else:
                        self.assertFalse(bool(stripe.visible),
                            f"scale {scale}: custom stripe {i + 1} must be hidden")

                ink = positive.stripes[1].color
                self.assertIsNotNone(ink,
                    f"scale {scale}: custom stripe ink missing")
                self.assertGreaterEqual(float(ink.r), 0.5,
                    f"scale {scale}: custom stripe must be magenta (r)")
                self.assertGreaterEqual(float(ink.b), 0.5,
                    f"scale {scale}: custom stripe must be magenta (b)")
                self.assertLess(float(ink.g), float(ink.r),
                    f"scale {scale}: custom stripe must be magenta (g<r)")
                self.assertLess(float(ink.g), float(ink.b),
                    f"scale {scale}: custom stripe must be magenta (g<b)")
                self.assertIsNotNone(g._hp_ink,
                    f"scale {scale}: HP ink reference missing")
                self.assertFalse(_same_rgb(ink, g._hp_ink),
                    f"scale {scale}: custom stripe must differ from HP ink")
                self.assertIsNotNone(g._debt_ink,
                    f"scale {scale}: debt ink reference missing")
                self.assertFalse(_same_rgb(ink, g._debt_ink),
                    f"scale {scale}: custom stripe must differ from debt ink")

                self.assertFalse(bool(g._corrupt_verify),
                    f"scale {scale}: verify must reject a corrupted positive x")
                self.assertTrue(bool(g._recover_verify),
                    f"scale {scale}: positive rerender must recover")
                self.assertTrue(bool(g._recover_geom_ok),
                    f"scale {scale}: recovered positive geometry must match")

                for name in ("ratio_zero", "unknown", "absent", "mismatch",
                             "ratio_inf", "ratio_nan", "current_inf",
                             "total_zero"):
                    case = g._cases[name]
                    self.assertTrue(bool(case.verify),
                        f"scale {scale}: {name} custom render must verify")
                    for i in range(4):
                        self.assertFalse(bool(case.stripes[i + 1].visible),
                            f"scale {scale}: {name} must hide custom stripe "
                            f"{i + 1}")
                    self.assertTrue(bool(g._main_ok),
                        f"scale {scale}: {name} must not alter main HP")

                restored = g._cases.restored
                self.assertTrue(bool(restored.verify),
                    f"scale {scale}: restored custom stripe must verify")
                for i in range(4):
                    self.assertEqual(bool(restored.stripes[i + 1].visible),
                        bool(positive.stripes[i + 1].visible),
                        f"scale {scale}: restored stripe {i + 1} visibility")
                    if positive.stripes[i + 1].visible:
                        self.assertTrue(_same_geom(
                            restored.stripes[i + 1].geom,
                            positive.stripes[i + 1].geom),
                            f"scale {scale}: restored stripe {i + 1} geom")
                self.assertTrue(bool(g._identity_ok),
                    f"scale {scale}: custom stripe identity lost at "
                    f"{g._identity_failure}")
                self.assertTrue(bool(g._main_ok),
                    f"scale {scale}: main HP changed at {g._main_failure}")


INPUT_BOUNDARY_SCRIPT = r'''
local G = kyohud.hud.gauge
local parent = _G.panel_double
local e = _KY_scale

local inst = G.new(parent, "input_boundary_" .. tostring(e))
inst:set_geometry(0, 0, 440 * e, 42 * e)

local hp = {current = 60, total = 100, ratio = 0.6, valid = true, provenance = "local"}
local ar = {current = 50, total = 100, ratio = 0.5, valid = true, provenance = "local"}
local effects = {
    stored_health = {known = true, ratio = 0.2, max_ratio = 0.4},
    delayed_damage = {known = true, amount = 60},
    absorption = {known = true, amount = 60},
}

local function geom(p) return {x = p:x(), y = p:y(), w = p:w(), h = p:h()} end

local function same_geom(a, b)
    return math.abs(a.x - b.x) <= 0.05 and math.abs(a.y - b.y) <= 0.05
        and math.abs(a.w - b.w) <= 0.05 and math.abs(a.h - b.h) <= 0.05
end

local function main_snapshot()
    local s = {
        health_text = inst.health_text:text(),
        armor_text = inst.armor_text:text(),
        armor_fill = geom(inst.armor_fill),
        health_fill = geom(inst.health_fill),
        segs = {},
    }
    for i = 1, 4 do
        s.segs[i] = {
            bg = geom(inst.health_segments[i].background),
            fill = geom(inst.health_segments[i].fill),
        }
    end
    return s
end

local function same_main(a, b)
    if a.health_text ~= b.health_text or a.armor_text ~= b.armor_text then
        return false
    end
    if not same_geom(a.armor_fill, b.armor_fill)
        or not same_geom(a.health_fill, b.health_fill) then
        return false
    end
    for i = 1, 4 do
        if not same_geom(a.segs[i].bg, b.segs[i].bg)
            or not same_geom(a.segs[i].fill, b.segs[i].fill) then
            return false
        end
    end
    return true
end

local function family_visible(armor_prim, health_prims)
    if armor_prim and armor_prim:visible() then return true end
    if health_prims then
        for i = 1, #health_prims do
            if health_prims[i] and health_prims[i]:visible() then return true end
        end
    end
    return false
end

inst:render(hp, ar, "percentage", 10, nil, effects)
local baseline = main_snapshot()

_input_cases = {}
local function capture(name)
    _input_cases[name] = {
        verify = inst:verify(),
        reserve = inst._stored_health_bg ~= nil
            and inst._stored_health_bg:visible()
            and inst._stored_health_fill ~= nil
            and inst._stored_health_fill:visible(),
        debt = family_visible(inst._delayed_armor, inst._delayed_health),
        absorb = family_visible(inst._absorb_armor, inst._absorb_health),
        main_ok = same_main(baseline, main_snapshot()),
    }
end

capture("explicit")
inst:set_geometry(0, 0, 440 * e, 42 * e)
capture("relayout")
inst:render(hp, ar, "percentage", 10, nil)
capture("omitted")
'''

RAW_ARMOR_BOUNDS_SCRIPT = r'''
local G = kyohud.hud.gauge
local parent = _G.panel_double
local e = _KY_scale

local inst = G.new(parent, "input_raw_" .. tostring(e))
inst:set_geometry(0, 0, 440 * e, 42 * e)

local hp = {current = 60, total = 100, ratio = 0.6, valid = true, provenance = "local"}
local ar = {current = 200, total = 100, ratio = 1, valid = true, provenance = "local"}
local effects = {
    delayed_damage = {known = true, amount = 200},
    absorption = {known = true, amount = 200},
}

local function geom(p) return {x = p:x(), y = p:y(), w = p:w(), h = p:h()} end

local function same_geom(a, b)
    return math.abs(a.x - b.x) <= 0.05 and math.abs(a.y - b.y) <= 0.05
        and math.abs(a.w - b.w) <= 0.05 and math.abs(a.h - b.h) <= 0.05
end

local function principal()
    local s = {
        health_text = inst.health_text:text(),
        armor_text = inst.armor_text:text(),
        armor_fill = geom(inst.armor_fill),
        health_fill = geom(inst.health_fill),
        segs = {},
    }
    for i = 1, 4 do
        s.segs[i] = {
            bg = geom(inst.health_segments[i].background),
            fill = geom(inst.health_segments[i].fill),
        }
    end
    return s
end

local function same_principal(a, b)
    if a.health_text ~= b.health_text or a.armor_text ~= b.armor_text then
        return false
    end
    if not same_geom(a.armor_fill, b.armor_fill)
        or not same_geom(a.health_fill, b.health_fill) then
        return false
    end
    for i = 1, 4 do
        if not same_geom(a.segs[i].bg, b.segs[i].bg)
            or not same_geom(a.segs[i].fill, b.segs[i].fill) then
            return false
        end
    end
    return true
end

inst:render(hp, ar, "percentage", 10, nil, nil)
local baseline = principal()

inst:render(hp, ar, "percentage", 10, nil, effects)
_bounds = {
    verify = inst:verify(),
    principal_ok = same_principal(baseline, principal()),
    track = geom(inst._armor_bg),
    debt = inst._delayed_armor and geom(inst._delayed_armor) or nil,
    debt_visible = inst._delayed_armor ~= nil and inst._delayed_armor:visible(),
    absorb = inst._absorb_armor and geom(inst._absorb_armor) or nil,
    absorb_visible = inst._absorb_armor ~= nil and inst._absorb_armor:visible(),
    source_ok = ar.current == 200 and ar.total == 100 and ar.ratio == 1
        and hp.current == 60 and hp.total == 100 and hp.ratio == 0.6
        and effects.delayed_damage.amount == 200
        and effects.absorption.amount == 200,
}
'''


def _bounded_within(piece, track, delta=0.05):
    px, pw = float(piece.x), float(piece.w)
    tx, tw = float(track.x), float(track.w)
    return (math.isfinite(px) and math.isfinite(pw)
            and 0.0 <= pw <= tw + delta
            and px >= tx - delta
            and px + pw <= tx + tw + delta)


class GaugeInputBoundaryTests(unittest.TestCase):
    """Optional effects argument and raw out-of-range armor stay bounded.

    Case 1: an explicit effects render must survive a same-geometry relayout
    through ``_layout``, while an ordinary render omitting the sixth argument
    must clear stale effects exactly like an explicit nil.
    Case 2: raw local armor current 200/total 100 with amount 200 must clamp
    debt/absorption overlays inside the armor track instead of drawing 2*bw.
    RED until the gauge fixes vararg retention and raw overlay bounds.
    """

    def test_optional_effects_and_raw_armor_bounds(self):
        for scale in (1.0, 0.672):
            with self.subTest(scale=scale):
                lua, ok = _lua()
                self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
                if not ok:
                    return

                lua.globals()._KY_scale = scale
                lua.execute(INPUT_BOUNDARY_SCRIPT)
                lua.execute(RAW_ARMOR_BOUNDS_SCRIPT)
                g = lua.globals()

                cases = g._input_cases
                for name in ("explicit", "relayout"):
                    case = cases[name]
                    self.assertTrue(bool(case.verify),
                        f"scale {scale}: {name} effects render must verify")
                    self.assertTrue(bool(case.reserve),
                        f"scale {scale}: {name} must keep reserve visible")
                    self.assertTrue(bool(case.debt),
                        f"scale {scale}: {name} must keep debt visible")
                    self.assertTrue(bool(case.absorb),
                        f"scale {scale}: {name} must keep absorption visible")
                    self.assertTrue(bool(case.main_ok),
                        f"scale {scale}: {name} must not alter principal")

                omitted = cases.omitted
                self.assertTrue(bool(omitted.verify),
                    f"scale {scale}: omitted-argument render must verify")
                self.assertFalse(bool(omitted.reserve),
                    f"scale {scale}: omitted argument must clear stale reserve")
                self.assertFalse(bool(omitted.debt),
                    f"scale {scale}: omitted argument must clear stale debt")
                self.assertFalse(bool(omitted.absorb),
                    f"scale {scale}: omitted argument must clear stale absorption")
                self.assertTrue(bool(omitted.main_ok),
                    f"scale {scale}: omitted argument must not alter principal")

                bounds = g._bounds
                self.assertTrue(bool(bounds.verify),
                    f"scale {scale}: raw armor bounds render must verify")
                self.assertTrue(bool(bounds.principal_ok),
                    f"scale {scale}: raw armor must not alter principal fills")
                self.assertTrue(bool(bounds.source_ok),
                    f"scale {scale}: raw armor and amount sources must not be "
                    f"rewritten in place")
                self.assertIsNotNone(bounds.debt,
                    f"scale {scale}: RED missing _delayed_armor")
                self.assertIsNotNone(bounds.absorb,
                    f"scale {scale}: RED missing _absorb_armor")
                if bounds.debt is None or bounds.absorb is None:
                    return
                self.assertTrue(bool(bounds.debt_visible),
                    f"scale {scale}: raw armor debt overlay must remain visible")
                self.assertTrue(bool(bounds.absorb_visible),
                    f"scale {scale}: raw armor absorption overlay must remain "
                    f"visible")
                self.assertTrue(_bounded_within(bounds.debt, bounds.track),
                    f"scale {scale}: raw armor debt must stay within the armor "
                    f"track, width <= track width")
                self.assertTrue(_bounded_within(bounds.absorb, bounds.track),
                    f"scale {scale}: raw armor absorption must stay within the "
                    f"armor track, width <= track width")


if __name__ == "__main__":
    unittest.main()
