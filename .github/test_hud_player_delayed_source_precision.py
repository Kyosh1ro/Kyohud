"""RED: within-band source/native overflow keeps the leased Stoic replacement.

Real health is just above 48.3 by .5*48.3*2^-23, max 48.3; real armor is
8.75/9. Native hp 48.3/48.3, armor 8.760037819014/9 and colors 1/.973337535
are published independently. Ordinary 1.1 and throttled 1.11 frames must keep
the certified player, same roots and both leases at 0, with raw gauge health
exact and its rendered ratio clamped to 1. Numeric failures must release and
restore the exact .65/.85 alphas, then recover the same primitives.
"""
import unittest

from test_hud_player_delayed_replacement import PRELIM, SETUP, _lua

SCENARIO = r'''
local chain, sent = mount_positive()
RT:update(mgr, 1.0, 0.1)
local root0, gauge0 = P._root, P._gauge
local hmax, amax = 48.3, 9
local hband = math.min(0.001, hmax * 2^-23)
local health = hmax + 0.5 * hband
local armor = amax + 0.5 * math.min(0.001, amax * 2^-23)
local entry = mgr._teammate_panels[PP]
local saved_debt = cd.remaining_delayed_damage

local function publish(h, a)
    cd._health, cd._health_max = h, hmax
    cd._armor, cd._armor_max = a, amax
    cd._remaining_delayed = 60
    entry._health_data = {current = hmax, total = hmax}
    entry._armor_data = {current = 8.760037819014, total = amax}
    chain.radial_health:set_color(Color(1, 1, 0, 0))
    chain.radial_shield:set_color(Color(1, 0.973337535, 0, 0))
end

local function capture()
    local g = P._gauge
    local dd = g and g._health_effects and g._health_effects.delayed_damage
    return {
        vis = P._root ~= nil and P._root:visible() == true,
        ver = P:verify() == true,
        same = rawequal(P._root, root0) and rawequal(P._gauge, gauge0)
            and chain.armor == chain.delayed:child("radial_delayed_damage_armor")
            and chain.health == chain.delayed:child("radial_delayed_damage_health"),
        a0 = near(chain.armor:alpha(), 0, 0.0001),
        h0 = near(chain.health:alpha(), 0, 0.0001),
        a65 = near(chain.armor:alpha(), 0.65, 0.0001),
        h85 = near(chain.health:alpha(), 0.85, 0.0001),
        hp = g and g._health.current,
        hpt = g and g._health.total,
        hpr = g and g._health.ratio,
        ar = g and g._armor.current,
        art = g and g._armor.total,
        arr = g and g._armor.ratio,
        debt = dd and dd.known == true and dd.amount,
    }
end

publish(health, 8.75)
RT:update(mgr, 1.1, 0.1)
local frames = {ordinary = capture()}
RT:update(mgr, 1.11, 0.1)
frames.throttled = capture()
publish(hmax, armor)
RT:update(mgr, 1.2, 0.1)
frames.armor = capture()

local cases = {
    {"overflow_beyond_2_band", function() cd._health = hmax + 2.5 * hband end,
        function() cd._health = hmax end},
    {"zero_max_nonzero", function() cd._armor = 1; cd._armor_max = 0 end,
        function() cd._armor = 8.75; cd._armor_max = 9 end},
    {"negative", function() cd._armor = -0.1 end,
        function() cd._armor = 8.75 end},
    {"nan", function() cd._health = 0 / 0 end,
        function() cd._health = hmax end},
    {"infinity", function() cd._armor = math.huge end,
        function() cd._armor = 8.75 end},
    {"source_nil", function() cd.remaining_delayed_damage = nil end,
        function() cd.remaining_delayed_damage = saved_debt end},
}
local results = {}
local t = 1.3
for _, case in ipairs(cases) do
    publish(hmax, 8.75)
    RT:update(mgr, t, 0.1); t = t + 0.1
    local result = {positive = capture()}
    case[2]()
    RT:update(mgr, t, 0.1); t = t + 0.1
    result.rejected = capture()
    case[3]()
    RT:update(mgr, t, 0.1); t = t + 0.1
    result.recovered = capture()
    results[case[1]] = result
end
_frames, _safety, _health, _armor = frames, results, health, armor
'''

CASES = ("overflow_beyond_2_band", "zero_max_nonzero", "negative",
         "nan", "infinity", "source_nil")


class DelayedSourcePrecisionTests(unittest.TestCase):
    def test_within_band_overflow_keeps_lease_and_safety_cases_recover(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return
        lua.execute(PRELIM + SCENARIO)
        g = lua.globals()
        health, armor = float(g._health), float(g._armor)
        expected = {"ordinary": (health, 8.75), "throttled": (health, 8.75),
                    "armor": (48.3, armor)}
        for name, (hp, ar) in expected.items():
            with self.subTest(frame=name):
                f = g._frames[name]
                self.assertTrue(all(bool(f[k]) for k in
                                    ("vis", "ver", "same", "a0", "h0")),
                                f"{name}: certified owned lease")
                self.assertEqual(
                    tuple(float(f[k]) for k in
                          ("hp", "hpt", "hpr", "ar", "art", "arr", "debt")),
                    (hp, 48.3, 1.0, ar, 9.0, min(ar / 9.0, 1.0), 60.0),
                    f"{name}: exact raw values and clamped ratios")
        for name in CASES:
            with self.subTest(case=name):
                r = g._safety[name]
                for phase, keys in (
                        ("positive", ("vis", "ver", "a0", "h0", "same")),
                        ("rejected", ("a65", "h85", "same")),
                        ("recovered", ("vis", "ver", "a0", "h0", "same"))):
                    self.assertTrue(all(bool(r[phase][k]) for k in keys),
                                    f"{name}: {phase} state")
