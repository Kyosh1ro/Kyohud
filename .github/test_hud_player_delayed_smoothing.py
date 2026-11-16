"""RED contract: native delayed-damage smoothing must not block the owned gauge.

The local real source is health 41.4/100 and armor 8.75/9 with 60 delayed
damage. The native duplicate is published independently: health 41.4/100,
armor 8.9567632289405/9 with radial colors .414/.995, then native armor moves
to 8.760037819014/9 while the delayed debt stays live.

Desired behavior: finite native data/color drift never re-authorizes the native
duplicate. The owned player stays visible, both native leaves stay at alpha 0,
and the actual rendered gauge plus the source receipt still describe the real
41.4/8.75/60 source. Clearing the live debt must restore the exact .65/.85
third-party alphas on the same two leaves.

RED: the runtime currently treats the smoothed native split as a mismatch,
releases the replacement, and restores the native duplicates.
"""
import unittest

from test_hud_player_delayed_replacement import PRELIM, SETUP, _lua

CASE = r'''
local chain, sent = mount_positive()
RT:update(mgr, 1.0, 0.1)

cd._health = 41.4
cd._health_max = 100
cd._armor = 8.75
cd._armor_max = 9
cd._remaining_delayed = 60
local entry = mgr._teammate_panels[PP]
entry._health_data = {current = 41.4, total = 100}
entry._armor_data = {current = 8.9567632289405, total = 9}
chain.radial_health:set_color(Color(1, 0.414, 0, 0))
chain.radial_shield:set_color(Color(1, 0.995, 0, 0))

local function capture(prefix)
    local gauge = P._gauge
    local effects = gauge and gauge._health_effects or nil
    local debt = effects and effects.delayed_damage or nil
    _G[prefix .. "_visible"] = P._root ~= nil and P._root:visible() == true
    _G[prefix .. "_armor_zero"] = near(chain.armor:alpha(), 0, 0.0001)
    _G[prefix .. "_health_zero"] = near(chain.health:alpha(), 0, 0.0001)
    _G[prefix .. "_gauge_health"] = gauge ~= nil
        and near(gauge._health.current, 41.4)
    _G[prefix .. "_gauge_health_max"] = gauge ~= nil
        and near(gauge._health.total, 100)
    _G[prefix .. "_gauge_armor"] = gauge ~= nil
        and near(gauge._armor.current, 8.75)
    _G[prefix .. "_gauge_armor_max"] = gauge ~= nil
        and near(gauge._armor.total, 9)
    _G[prefix .. "_gauge_debt"] = debt ~= nil and debt.known == true
        and near(debt.amount, 60)
    _G[prefix .. "_verify"] = P:verify() == true
    _G[prefix .. "_same_armor"] =
        chain.armor == chain.delayed:child("radial_delayed_damage_armor")
    _G[prefix .. "_same_health"] =
        chain.health == chain.delayed:child("radial_delayed_damage_health")
end

RT:update(mgr, 1.1, 0.1)
capture("smoothing_first")

entry._armor_data = {current = 8.760037819014, total = 9}
RT:update(mgr, 1.2, 0.1)
capture("smoothing_second")

RT:update(mgr, 1.3, 0.1)
capture("smoothing_third")

cd._remaining_delayed = 0
RT:update(mgr, 1.4, 0.1)
_smoothing_purge_armor = near(chain.armor:alpha(), 0.65, 0.0001)
_smoothing_purge_health = near(chain.health:alpha(), 0.85, 0.0001)
_smoothing_purge_same_armor =
    chain.armor == chain.delayed:child("radial_delayed_damage_armor")
_smoothing_purge_same_health =
    chain.health == chain.delayed:child("radial_delayed_damage_health")
'''

FRAMES = ("smoothing_first", "smoothing_second", "smoothing_third")

SAFETY_CASE = r'''
local chain, sent = mount_positive()
local entry = mgr._teammate_panels[PP]
local t = 1.0

local function leaves_same()
    return chain.armor == chain.delayed:child("radial_delayed_damage_armor")
        and chain.health == chain.delayed:child("radial_delayed_damage_health")
end

local function publish_positive()
    cd._health = 50
    cd._health_max = 100
    cd._armor = 20
    cd._armor_max = 50
    cd._remaining_delayed = 30
    entry._health_data = {current = 50, total = 100}
    entry._armor_data = {current = 20, total = 50}
    chain.radial_health:set_color(Color(1, 0.5, 0, 0))
    chain.radial_shield:set_color(Color(1, 0.4, 0, 0))
end

local nan_color = newproxy(true)
getmetatable(nan_color).__index = function(_, key)
    if key == "r" then return 0 / 0 end
    return 0
end

local saved_health_data
local saved_armor_data
local saved_shield_color
local saved_health_color
local saved_get_health

local cases = {
    {
        name = "unknown_native_health_data",
        apply = function()
            saved_health_data = entry._health_data
            entry._health_data = nil
        end,
        restore = function()
            entry._health_data = saved_health_data
        end,
    },
    {
        name = "nan_native_armor",
        apply = function()
            saved_armor_data = entry._armor_data
            entry._armor_data = {current = 0 / 0, total = 50}
        end,
        restore = function()
            entry._armor_data = saved_armor_data
        end,
    },
    {
        name = "throwing_native_color",
        apply = function()
            saved_shield_color = chain.radial_shield.color
            chain.radial_shield.color = function() error("native color failed") end
        end,
        restore = function()
            chain.radial_shield.color = saved_shield_color
        end,
    },
    {
        name = "nan_native_color",
        apply = function()
            saved_health_color = chain.radial_health.color
            chain.radial_health.color = function() return nan_color end
        end,
        restore = function()
            chain.radial_health.color = saved_health_color
        end,
    },
    {
        name = "throwing_live_getter",
        apply = function()
            saved_get_health = cd.get_real_health
            cd.get_real_health = function() error("live getter failed") end
        end,
        restore = function()
            cd.get_real_health = saved_get_health
        end,
    },
    {
        name = "max_mismatch",
        apply = function()
            saved_armor_data = entry._armor_data
            entry._armor_data = {current = 20, total = 51}
        end,
        restore = function()
            entry._armor_data = saved_armor_data
        end,
    },
}

_safety_results = {}
for _, case in ipairs(cases) do
    publish_positive()
    RT:update(mgr, t, 0.1)
    t = t + 0.1
    local result = {
        positive_armor = near(chain.armor:alpha(), 0, 0.0001),
        positive_health = near(chain.health:alpha(), 0, 0.0001),
        positive_visible = P._root ~= nil and P._root:visible() == true,
    }
    case.apply()
    RT:update(mgr, t, 0.1)
    t = t + 0.1
    result.released_armor = near(chain.armor:alpha(), 0.65, 0.0001)
    result.released_health = near(chain.health:alpha(), 0.85, 0.0001)
    result.released_same = leaves_same()
    case.restore()
    RT:update(mgr, t, 0.1)
    t = t + 0.1
    result.recovered_armor = near(chain.armor:alpha(), 0, 0.0001)
    result.recovered_health = near(chain.health:alpha(), 0, 0.0001)
    result.recovered_visible = P._root ~= nil and P._root:visible() == true
    result.recovered_same = leaves_same()
    _safety_results[case.name] = result
end
'''

SAFETY_CASES = (
    "unknown_native_health_data",
    "nan_native_armor",
    "throwing_native_color",
    "nan_native_color",
    "throwing_live_getter",
    "max_mismatch",
)

THROTTLED_CASE = r'''
local chain, sent = mount_positive()
RT:update(mgr, 1.0, 0.1)
local owned_root = P._root
local owned_gauge = P._gauge

cd._health = 55
cd._health_max = 100
cd._armor = 20
cd._armor_max = 50
cd._remaining_delayed = 40
local entry = mgr._teammate_panels[PP]
entry._health_data = {current = 55, total = 100}
entry._armor_data = {current = 20.2, total = 50}
chain.radial_health:set_color(Color(1, 0.551, 0, 0))
chain.radial_shield:set_color(Color(1, 0.405, 0, 0))

local function leaves_same()
    return chain.armor == chain.delayed:child("radial_delayed_damage_armor")
        and chain.health == chain.delayed:child("radial_delayed_damage_health")
end

RT:update(mgr, 1.01, 0.01)
_thr_visible = P._root ~= nil and P._root:visible() == true
_thr_armor_zero = near(chain.armor:alpha(), 0, 0.0001)
_thr_health_zero = near(chain.health:alpha(), 0, 0.0001)
_thr_gauge_health = P._gauge ~= nil and near(P._gauge._health.current, 55)
_thr_gauge_armor = P._gauge ~= nil and near(P._gauge._armor.current, 20)
_thr_gauge_debt = P._gauge ~= nil and P._gauge._health_effects ~= nil
    and P._gauge._health_effects.delayed_damage ~= nil
    and P._gauge._health_effects.delayed_damage.known == true
    and near(P._gauge._health_effects.delayed_damage.amount, 40)
local thr_receipt = P._delayed_source_receipt or {}
_thr_receipt = near(thr_receipt.health_current, 55)
    and near(thr_receipt.armor_current, 20)
    and near(thr_receipt.delayed_amount, 40)
_thr_verify = P:verify() == true
_thr_same = rawequal(P._root, owned_root) and rawequal(P._gauge, owned_gauge)
    and leaves_same()

cd._health = 54
cd._health_max = 100
cd._armor = 0
cd._armor_max = 0
cd._remaining_delayed = 30
entry._health_data = {current = 55, total = 100}
entry._armor_data = {current = 0, total = 0}
chain.radial_shield:set_color(Color(1, 0, 0, 0))

RT:update(mgr, 1.02, 0.01)
_zero_visible = P._root ~= nil and P._root:visible() == true
_zero_armor_alpha = near(chain.armor:alpha(), 0, 0.0001)
_zero_health_alpha = near(chain.health:alpha(), 0, 0.0001)
_zero_gauge_health = P._gauge ~= nil and near(P._gauge._health.current, 54)
_zero_gauge_armor = P._gauge ~= nil and near(P._gauge._armor.current, 0)
_zero_gauge_armor_max = P._gauge ~= nil and near(P._gauge._armor.total, 0)
_zero_gauge_debt = P._gauge ~= nil and P._gauge._health_effects ~= nil
    and P._gauge._health_effects.delayed_damage ~= nil
    and P._gauge._health_effects.delayed_damage.known == true
    and near(P._gauge._health_effects.delayed_damage.amount, 30)
local zero_receipt = P._delayed_source_receipt or {}
_zero_receipt = near(zero_receipt.health_current, 54)
    and near(zero_receipt.armor_current, 0)
    and near(zero_receipt.armor_total, 0)
    and near(zero_receipt.delayed_amount, 30)
_zero_verify = P:verify() == true
_zero_same = rawequal(P._root, owned_root) and rawequal(P._gauge, owned_gauge)
    and leaves_same()

cd._remaining_delayed = 0
RT:update(mgr, 1.03, 0.01)
_purge_armor = near(chain.armor:alpha(), 0.65, 0.0001)
_purge_health = near(chain.health:alpha(), 0.85, 0.0001)
_purge_same = leaves_same()
'''


class DelayedSmoothingTests(unittest.TestCase):
    def test_native_smoothing_keeps_owned_gauge_until_exact_purge(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + CASE)
        g = lua.globals()

        for frame in FRAMES:
            with self.subTest(frame=frame):
                self.assertTrue(
                    bool(getattr(g, frame + "_visible")),
                    f"{frame}: the owned player must stay visible")
                self.assertTrue(
                    bool(getattr(g, frame + "_armor_zero")),
                    f"{frame}: the native armor duplicate must stay alpha 0")
                self.assertTrue(
                    bool(getattr(g, frame + "_health_zero")),
                    f"{frame}: the native health duplicate must stay alpha 0")
                self.assertTrue(
                    bool(getattr(g, frame + "_gauge_health")),
                    f"{frame}: the rendered gauge must show real health 41.4")
                self.assertTrue(
                    bool(getattr(g, frame + "_gauge_health_max")),
                    f"{frame}: the rendered gauge must show real health max 100")
                self.assertTrue(
                    bool(getattr(g, frame + "_gauge_armor")),
                    f"{frame}: the rendered gauge must show real armor 8.75")
                self.assertTrue(
                    bool(getattr(g, frame + "_gauge_armor_max")),
                    f"{frame}: the rendered gauge must show real armor max 9")
                self.assertTrue(
                    bool(getattr(g, frame + "_gauge_debt")),
                    f"{frame}: the rendered gauge must show real debt 60")
                self.assertTrue(
                    bool(getattr(g, frame + "_verify")),
                    f"{frame}: the owned render must remain certified")
                self.assertTrue(
                    bool(getattr(g, frame + "_same_armor")),
                    f"{frame}: the same native armor leaf must be reused")
                self.assertTrue(
                    bool(getattr(g, frame + "_same_health")),
                    f"{frame}: the same native health leaf must be reused")

        self.assertTrue(
            bool(g._smoothing_purge_armor),
            "purge must restore the exact native armor alpha .65")
        self.assertTrue(
            bool(g._smoothing_purge_health),
            "purge must restore the exact native health alpha .85")
        self.assertTrue(
            bool(g._smoothing_purge_same_armor),
            "purge must keep the same native armor leaf")
        self.assertTrue(
            bool(g._smoothing_purge_same_health),
            "purge must keep the same native health leaf")

    def test_throttled_player_frame_renders_fresh_values_before_native_mask(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + THROTTLED_CASE)
        g = lua.globals()

        self.assertTrue(
            bool(g._thr_visible),
            "throttled frame: the owned player must stay visible")
        self.assertTrue(
            bool(g._thr_armor_zero),
            "throttled frame: the native armor duplicate must stay alpha 0")
        self.assertTrue(
            bool(g._thr_health_zero),
            "throttled frame: the native health duplicate must stay alpha 0")
        self.assertTrue(
            bool(g._thr_gauge_health),
            "throttled frame: the gauge must render the fresh health 55")
        self.assertTrue(
            bool(g._thr_gauge_armor),
            "throttled frame: the gauge must render the fresh armor 20")
        self.assertTrue(
            bool(g._thr_gauge_debt),
            "throttled frame: the gauge must render the fresh debt 40")
        self.assertTrue(
            bool(g._thr_receipt),
            "throttled frame: the receipt must match the fresh real source")
        self.assertTrue(
            bool(g._thr_verify),
            "throttled frame: the owned render must be certified")
        self.assertTrue(
            bool(g._thr_same),
            "throttled frame: the owned root, gauge and leaves must be reused")

        self.assertTrue(
            bool(g._zero_visible),
            "zero max: the owned player must stay visible")
        self.assertTrue(
            bool(g._zero_armor_alpha),
            "zero max: the native armor duplicate must stay alpha 0")
        self.assertTrue(
            bool(g._zero_health_alpha),
            "zero max: the native health duplicate must stay alpha 0")
        self.assertTrue(
            bool(g._zero_gauge_health),
            "zero max: the gauge must render the fresh health 54")
        self.assertTrue(
            bool(g._zero_gauge_armor),
            "zero max: the gauge must render the known zero armor current")
        self.assertTrue(
            bool(g._zero_gauge_armor_max),
            "zero max: the gauge must render the known zero armor max")
        self.assertTrue(
            bool(g._zero_gauge_debt),
            "zero max: the gauge must render the fresh debt 30")
        self.assertTrue(
            bool(g._zero_receipt),
            "zero max: the receipt must match the zero-max real source")
        self.assertTrue(
            bool(g._zero_verify),
            "zero max: the owned render must be certified")
        self.assertTrue(
            bool(g._zero_same),
            "zero max: the owned root, gauge and leaves must be reused")

        self.assertTrue(
            bool(g._purge_armor),
            "purge must restore the exact native armor alpha .65")
        self.assertTrue(
            bool(g._purge_health),
            "purge must restore the exact native health alpha .85")
        self.assertTrue(
            bool(g._purge_same),
            "purge must keep the same native leaves")

    def test_positive_replacement_fails_closed_and_recovers_for_each_safety_case(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + SAFETY_CASE)
        g = lua.globals()

        for name in SAFETY_CASES:
            with self.subTest(case=name):
                result = g._safety_results[name]
                self.assertTrue(
                    bool(result["positive_armor"]),
                    f"{name}: a positive replacement must precede the mutation")
                self.assertTrue(
                    bool(result["positive_health"]),
                    f"{name}: a positive replacement must precede the mutation")
                self.assertTrue(
                    bool(result["positive_visible"]),
                    f"{name}: the owned player must be visible before the mutation")
                self.assertTrue(
                    bool(result["released_armor"]),
                    f"{name}: failure must restore the exact .65 armor alpha")
                self.assertTrue(
                    bool(result["released_health"]),
                    f"{name}: failure must restore the exact .85 health alpha")
                self.assertTrue(
                    bool(result["released_same"]),
                    f"{name}: failure must keep the same native leaves")
                self.assertTrue(
                    bool(result["recovered_armor"]),
                    f"{name}: recovery must reacquire the armor leaf")
                self.assertTrue(
                    bool(result["recovered_health"]),
                    f"{name}: recovery must reacquire the health leaf")
                self.assertTrue(
                    bool(result["recovered_visible"]),
                    f"{name}: recovery must keep the owned player visible")
                self.assertTrue(
                    bool(result["recovered_same"]),
                    f"{name}: recovery must reuse the same native leaves")


if __name__ == "__main__":
    unittest.main()
