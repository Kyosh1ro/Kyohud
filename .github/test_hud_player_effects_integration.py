"""Bounded player/gauge integration for the Ex-President stored-health reserve.

The real runtime, player, actors and gauge chunks are loaded through
test_hud_player._lua. A live local damage source (health 100, stored 20/40) is
installed before runtime, mounted through runtime:refresh_settings, then driven
only through ordinary runtime:update calls.

RED: player.lua currently calls gauge:render with five arguments and omits the
sixth health_effects table, so the reserve never becomes visible downstream
even though the gauge component and actors capture already work.
"""
import unittest

from test_hud_actors_lifecycle import DISPATCH
from test_hud_player import _lua
from test_hud_player_health_effects import (
    LOCAL_SOURCE_SETUP_EXPORTED,
    NATIVE_EFFECTS_RELAY_FIXTURE,
    NATIVE_HEALTH_EFFECTS_FIXTURE,
    NATIVE_RADIAL_FIXTURE,
)

SETUP = NATIVE_HEALTH_EFFECTS_FIXTURE + LOCAL_SOURCE_SETUP_EXPORTED + r'''
mgr._safe_script = {panel = _G.panel_double}
'''

COMBINED_SETUP = (
    NATIVE_EFFECTS_RELAY_FIXTURE
    + NATIVE_RADIAL_FIXTURE
    + LOCAL_SOURCE_SETUP_EXPORTED
    + r'''
mgr._safe_script = {panel = _G.panel_double}
'''
)

SCRIPT = r'''
local RT = kyohud.hud.runtime
local P = kyohud.hud.player
local ACT = kyohud.hud.actors
local mgr = managers.hud
local cd = _KY_test_damage
local PP = HUDManager.PLAYER_PANEL

kyohud.settings.enable_hud_foundation = true
kyohud.settings.enable_player = true
kyohud.settings.player_value_mode = 1

RT:refresh_settings(mgr)
_mount_player_verify = P:verify()
_mount_gauge_verify = P._gauge ~= nil and P._gauge:verify()

RT:update(mgr, 1.0, 0.1)

local gauge = P._gauge
_positive_player_verify = P:verify()
_positive_gauge_verify = gauge ~= nil and gauge:verify()

local bg = gauge and gauge._stored_health_bg
local fill = gauge and gauge._stored_health_fill
_reserve_present = bg ~= nil and fill ~= nil
if not _reserve_present then return end

local snap = ACT:get_actor(PP)
local stored = snap and snap.health_effects and snap.health_effects.stored_health
_positive_stored_known = stored ~= nil and stored.known == true
_positive_stored_ratio = stored and stored.ratio or nil
_positive_stored_max = stored and stored.max_ratio or nil
_positive_track_visible = bg:visible()
_positive_fill_visible = fill:visible()
_positive_track_w = bg:w()
_positive_fill_w = fill:w()

local function geom(p)
    return {p:x(), p:y(), p:w(), p:h()}
end

local function same_geom(p, saved)
    return p ~= nil
        and math.abs(p:x() - saved[1]) <= 0.01
        and math.abs(p:y() - saved[2]) <= 0.01
        and math.abs(p:w() - saved[3]) <= 0.01
        and math.abs(p:h() - saved[4]) <= 0.01
end

local baseline = {
    root = P._root,
    gauge = gauge,
    health_text = gauge.health_text,
    armor_text = gauge.armor_text,
    health_fill = gauge.health_fill,
    armor_fill = gauge.armor_fill,
    health_bg = gauge._health_bg,
    armor_bg = gauge._armor_bg,
    health_text_str = gauge.health_text:text(),
    armor_text_str = gauge.armor_text:text(),
    health_fill_geom = geom(gauge.health_fill),
    armor_fill_geom = geom(gauge.armor_fill),
    health_bg_geom = geom(gauge._health_bg),
    armor_bg_geom = geom(gauge._armor_bg),
}

local function main_unchanged()
    local g = P._gauge
    return P._root == baseline.root and g == baseline.gauge
        and g.health_text == baseline.health_text
        and g.armor_text == baseline.armor_text
        and g.health_fill == baseline.health_fill
        and g.armor_fill == baseline.armor_fill
        and g._health_bg == baseline.health_bg
        and g._armor_bg == baseline.armor_bg
        and g.health_text:text() == baseline.health_text_str
        and g.armor_text:text() == baseline.armor_text_str
        and same_geom(g.health_fill, baseline.health_fill_geom)
        and same_geom(g.armor_fill, baseline.armor_fill_geom)
        and same_geom(g._health_bg, baseline.health_bg_geom)
        and same_geom(g._armor_bg, baseline.armor_bg_geom)
end

cd._stored_health_amount = 0
RT:update(mgr, 1.6, 0.1)
_zero_player_verify = P:verify()
_zero_gauge_verify = P._gauge:verify()
_zero_track_visible = bg:visible()
_zero_fill_visible = fill:visible()
_zero_track_w = bg:w()
_zero_fill_w = fill:w()
_zero_same_reserve = P._gauge._stored_health_bg == bg
    and P._gauge._stored_health_fill == fill
_zero_main_unchanged = main_unchanged()
local zero_snap = ACT:get_actor(PP)
local zero_stored = zero_snap and zero_snap.health_effects
    and zero_snap.health_effects.stored_health
_zero_stored_ratio = zero_stored and zero_stored.ratio or nil

cd._max_stored_health_amount = 0
RT:update(mgr, 2.2, 0.1)
_maxzero_player_verify = P:verify()
_maxzero_gauge_verify = P._gauge:verify()
_maxzero_track_visible = bg:visible()
_maxzero_fill_visible = fill:visible()
_maxzero_same_reserve = P._gauge._stored_health_bg == bg
    and P._gauge._stored_health_fill == fill
_maxzero_main_unchanged = main_unchanged()

cd._stored_health_amount = 20
cd._max_stored_health_amount = 40
RT:update(mgr, 2.8, 0.1)
_restored_player_verify = P:verify()
_restored_gauge_verify = P._gauge:verify()
_restored_track_visible = bg:visible()
_restored_fill_visible = fill:visible()
_restored_track_w = bg:w()
_restored_fill_w = fill:w()
_restored_same_reserve = P._gauge._stored_health_bg == bg
    and P._gauge._stored_health_fill == fill
_restored_main_unchanged = main_unchanged()
_restored_root_identity = P._root == baseline.root
'''


class PlayerStoredHealthRuntimeIntegrationTests(unittest.TestCase):
    def test_runtime_forwards_live_stored_health_to_reserve(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "RED: lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(SCRIPT)
        g = lua.globals()

        self.assertTrue(bool(g._mount_player_verify),
            "mounted player panel must verify")
        self.assertTrue(bool(g._mount_gauge_verify),
            "mounted gauge must verify")
        self.assertTrue(bool(g._reserve_present),
            "RED: gauge must own stored-health reserve primitives")
        self.assertTrue(bool(g._positive_player_verify),
            "positive runtime update must leave the player panel verified")
        self.assertTrue(bool(g._positive_gauge_verify),
            "positive runtime update must leave the gauge verified")
        self.assertTrue(bool(g._positive_stored_known),
            "actors must expose known stored health from the live damage source")
        self.assertAlmostEqual(float(g._positive_stored_ratio), 0.2, places=5,
            msg="live stored health ratio must be 20/100")
        self.assertAlmostEqual(float(g._positive_stored_max), 0.4, places=5,
            msg="live stored health max ratio must be 40/100")
        self.assertTrue(bool(g._positive_track_visible),
            "RED: P:render must forward snapshot.health_effects as the sixth "
            "gauge argument; reserve track is hidden")
        self.assertTrue(bool(g._positive_fill_visible),
            "RED: positive stored health must make the reserve fill visible")
        self.assertAlmostEqual(float(g._positive_fill_w),
            float(g._positive_track_w) * 0.5, delta=0.01,
            msg="positive reserve fill must be half the track")

        self.assertTrue(bool(g._zero_player_verify),
            "zero-stock runtime update must leave the player panel verified")
        self.assertTrue(bool(g._zero_gauge_verify),
            "zero-stock runtime update must leave the gauge verified")
        self.assertTrue(bool(g._zero_track_visible),
            "zero stored health must keep the reserve track visible")
        self.assertTrue(bool(g._zero_fill_visible),
            "zero stored health must keep the reserve fill visible")
        self.assertGreater(float(g._zero_track_w), 0.0,
            "zero stored health must keep a positive track width")
        self.assertAlmostEqual(float(g._zero_fill_w), 0.0, delta=0.01,
            msg="zero stored health must collapse the reserve fill width")
        self.assertTrue(bool(g._zero_same_reserve),
            "zero stored health must preserve reserve primitive identities")
        self.assertTrue(bool(g._zero_main_unchanged),
            "zero stored health must not alter primary health/armor geometry or text")
        self.assertAlmostEqual(float(g._zero_stored_ratio), 0.0, places=5,
            msg="actors must refresh the live stored-health ratio to zero")

        self.assertTrue(bool(g._maxzero_player_verify),
            "zero-max runtime update must leave the player panel verified")
        self.assertTrue(bool(g._maxzero_gauge_verify),
            "zero-max runtime update must leave the gauge verified")
        self.assertFalse(bool(g._maxzero_track_visible),
            "zero stored max must hide the reserve track")
        self.assertFalse(bool(g._maxzero_fill_visible),
            "zero stored max must hide the reserve fill")
        self.assertTrue(bool(g._maxzero_same_reserve),
            "zero stored max must preserve reserve primitive identities")
        self.assertTrue(bool(g._maxzero_main_unchanged),
            "zero stored max must not alter primary health/armor geometry or text")

        self.assertTrue(bool(g._restored_player_verify),
            "restored runtime update must leave the player panel verified")
        self.assertTrue(bool(g._restored_gauge_verify),
            "restored runtime update must leave the gauge verified")
        self.assertTrue(bool(g._restored_track_visible),
            "restored stored health must make the reserve track visible")
        self.assertTrue(bool(g._restored_fill_visible),
            "restored stored health must make the reserve fill visible")
        self.assertAlmostEqual(float(g._restored_fill_w),
            float(g._restored_track_w) * 0.5, delta=0.01,
            msg="restored reserve fill must be half the track")
        self.assertTrue(bool(g._restored_same_reserve),
            "restored stored health must preserve reserve primitive identities")
        self.assertTrue(bool(g._restored_main_unchanged),
            "restored stored health must not alter primary health/armor geometry or text")
        self.assertTrue(bool(g._restored_root_identity),
            "restored stored health must preserve the player root identity")


COMBINED_SCRIPT = r'''
local RT = kyohud.hud.runtime
local P = kyohud.hud.player
local mgr = managers.hud
local PP = HUDManager.PLAYER_PANEL
local cd = _KY_test_damage
local pm = managers.player

cd._health = 60
cd._health_max = 100
cd._armor = 25
cd._armor_max = 50
cd._remaining_delayed = 60
cd._stored_health_amount = 20
cd._max_stored_health_amount = 40

local function install_positive_pm()
    pm.damage_absorption = function(self) return 60 end
    pm.has_category_upgrade = function(self, category, upgrade)
        return category == "player" and upgrade == "cocaine_stacking"
    end
    pm.get_local_cocaine_damage_absorption_ratio = function(self) return 0.2 end
    pm.get_local_cocaine_damage_absorption_max_ratio = function(self) return 0.8 end
    pm.has_activate_temporary_upgrade = function(self, category, upgrade)
        return category == "temporary" and upgrade == "copr_ability"
    end
    pm.upgrade_value = function(self, category, upgrade, default)
        if category == "player" and upgrade == "copr_static_damage_ratio" then
            return 0.2
        end
        return default
    end
end

install_positive_pm()

kyohud.settings.enable_hud_foundation = true
kyohud.settings.enable_player = true
kyohud.settings.player_value_mode = 1

RT:refresh_settings(mgr)

local function publish_custom(current, total)
    local data = {current = current, total = total}
    mgr:set_player_custom_radial(data)
    _KY_dispatch("set_teammate_custom_radial", PP, data)
end

publish_custom(60, 100)

RT:update(mgr, 1.0, 0.1)

local function capture(gauge)
    local function prim(p)
        return {p = p, x = p:x(), y = p:y(), w = p:w(), h = p:h(), v = p:visible()}
    end
    local function text(p)
        local c = prim(p)
        c.t = p:text()
        return c
    end
    local function list(items)
        local out = {}
        for i = 1, #items do out[i] = prim(items[i]) end
        return out
    end
    return {
        root = prim(P._root),
        gauge = prim(gauge.root),
        health_text = text(gauge.health_text),
        armor_text = text(gauge.armor_text),
        health_fill = prim(gauge.health_fill),
        armor_fill = prim(gauge.armor_fill),
        health_bg = prim(gauge._health_bg),
        armor_bg = prim(gauge._armor_bg),
        reserve_bg = prim(gauge._stored_health_bg),
        reserve_fill = prim(gauge._stored_health_fill),
        delayed_armor = prim(gauge._delayed_armor),
        delayed_health = list(gauge._delayed_health),
        absorb_armor = prim(gauge._absorb_armor),
        absorb_health = list(gauge._absorb_health),
        info_bg = prim(gauge._info_meter_bg),
        info_fill = prim(gauge._info_meter_fill),
        copr = list(gauge._copr_markers),
        custom = list(gauge._custom_health),
    }
end

local function same_geom(a, b)
    return math.abs(a.x - b.x) <= 0.01
        and math.abs(a.y - b.y) <= 0.01
        and math.abs(a.w - b.w) <= 0.01
        and math.abs(a.h - b.h) <= 0.01
end

local function same_prim(a, b)
    return a.p == b.p and same_geom(a, b)
end

local function same_list(a, b)
    if #a ~= #b then return false end
    for i = 1, #a do
        if not same_prim(a[i], b[i]) then return false end
    end
    return true
end

local function same_main(a, b)
    return same_geom(a.health_fill, b.health_fill)
        and same_geom(a.armor_fill, b.armor_fill)
        and same_geom(a.health_bg, b.health_bg)
        and same_geom(a.armor_bg, b.armor_bg)
        and a.health_text.t == b.health_text.t
        and a.armor_text.t == b.armor_text.t
        and same_geom(a.health_text, b.health_text)
        and same_geom(a.armor_text, b.armor_text)
end

local function same_capture(a, b)
    return same_prim(a.root, b.root)
        and same_prim(a.gauge, b.gauge)
        and same_prim(a.health_text, b.health_text)
        and same_prim(a.armor_text, b.armor_text)
        and same_prim(a.health_fill, b.health_fill)
        and same_prim(a.armor_fill, b.armor_fill)
        and same_prim(a.health_bg, b.health_bg)
        and same_prim(a.armor_bg, b.armor_bg)
        and same_prim(a.reserve_bg, b.reserve_bg)
        and same_prim(a.reserve_fill, b.reserve_fill)
        and same_prim(a.delayed_armor, b.delayed_armor)
        and same_list(a.delayed_health, b.delayed_health)
        and same_prim(a.absorb_armor, b.absorb_armor)
        and same_list(a.absorb_health, b.absorb_health)
        and same_prim(a.info_bg, b.info_bg)
        and same_prim(a.info_fill, b.info_fill)
        and same_list(a.copr, b.copr)
        and same_list(a.custom, b.custom)
end

local function has_visible(items)
    for i = 1, #items do
        if items[i].v == true then return true end
    end
    return false
end

local function count_visible(items)
    local n = 0
    for i = 1, #items do
        if items[i].v == true then n = n + 1 end
    end
    return n
end

local gauge = P._gauge
local pos = capture(gauge)
_pos = pos
_positive = {
    player_verify = P:verify(),
    gauge_verify = gauge:verify(),
    reserve_track_visible = pos.reserve_bg.v == true,
    reserve_track_w = pos.reserve_bg.w,
    reserve_fill_visible = pos.reserve_fill.v == true,
    reserve_fill_w = pos.reserve_fill.w,
    reserve_half = pos.reserve_bg.w > 0
        and math.abs(pos.reserve_fill.w - pos.reserve_bg.w * 0.5) <= 0.01,
    debt_armor_visible = pos.delayed_armor.v == true,
    debt_health_visible = has_visible(pos.delayed_health),
    absorb_armor_visible = pos.absorb_armor.v == true,
    absorb_health_visible = has_visible(pos.absorb_health),
    info_bg_visible = pos.info_bg.v == true,
    info_fill_visible = pos.info_fill.v == true,
    info_distinct = pos.info_bg.w > pos.info_fill.w,
    copr_total = #pos.copr,
    copr_visible = count_visible(pos.copr),
    custom_visible = has_visible(pos.custom),
}

cd._remaining_delayed = 0
cd._stored_health_amount = 0
cd._max_stored_health_amount = 40
pm.damage_absorption = function(self) return 0 end
pm.has_category_upgrade = function(self, category, upgrade) return false end
pm.get_local_cocaine_damage_absorption_ratio = function(self) return 0 end
pm.get_local_cocaine_damage_absorption_max_ratio = function(self) return 0 end
pm.has_activate_temporary_upgrade = function(self, category, upgrade) return false end
pm.upgrade_value = function(self, category, upgrade, default) return default end

publish_custom(0, 100)
RT:update(mgr, 1.6, 0.1)

local zero = capture(gauge)
_zero = zero
_zero_summary = {
    player_verify = P:verify(),
    gauge_verify = gauge:verify(),
    same_root = P._root == pos.root.p,
    same_gauge = P._gauge == gauge,
    reserve_track_visible = zero.reserve_bg.v == true,
    reserve_track_w = zero.reserve_bg.w,
    reserve_fill_w = zero.reserve_fill.w,
    debt_hidden = zero.delayed_armor.v == false and not has_visible(zero.delayed_health),
    absorb_hidden = zero.absorb_armor.v == false and not has_visible(zero.absorb_health),
    info_hidden = zero.info_bg.v == false and zero.info_fill.v == false,
    copr_total = #zero.copr,
    copr_visible = count_visible(zero.copr),
    custom_hidden = not has_visible(zero.custom),
    main_unchanged = same_main(zero, pos),
}

cd._remaining_delayed = 60
cd._stored_health_amount = 20
cd._max_stored_health_amount = 40
install_positive_pm()
publish_custom(60, 100)
RT:update(mgr, 2.2, 0.1)

local rec = capture(gauge)
_rec = rec
_recovery = {
    player_verify = P:verify(),
    gauge_verify = gauge:verify(),
    reserve_half = rec.reserve_bg.w > 0
        and math.abs(rec.reserve_fill.w - rec.reserve_bg.w * 0.5) <= 0.01,
    debt_armor_visible = rec.delayed_armor.v == true,
    debt_health_visible = has_visible(rec.delayed_health),
    absorb_armor_visible = rec.absorb_armor.v == true,
    absorb_health_visible = has_visible(rec.absorb_health),
    info_bg_visible = rec.info_bg.v == true,
    info_fill_visible = rec.info_fill.v == true,
    info_distinct = rec.info_bg.w > rec.info_fill.w,
    copr_total = #rec.copr,
    copr_visible = count_visible(rec.copr),
    custom_visible = has_visible(rec.custom),
    same_primitives = same_capture(rec, pos),
}
'''


class PlayerCombinedHealthEffectsRuntimeIntegrationTests(unittest.TestCase):
    def test_combined_runtime_health_effects_characterization(self):
        lua, ok = _lua(setup=COMBINED_SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(DISPATCH)
        lua.execute(COMBINED_SCRIPT)
        g = lua.globals()

        positive = g._positive
        self.assertTrue(bool(positive.player_verify),
            "positive update must leave the player panel verified")
        self.assertTrue(bool(positive.gauge_verify),
            "positive update must leave the gauge verified")
        self.assertTrue(bool(positive.reserve_track_visible),
            "stored stock must make the reserve track visible")
        self.assertTrue(bool(positive.reserve_fill_visible),
            "stored stock must make the reserve fill visible")
        self.assertTrue(bool(positive.reserve_half),
            "stored stock 20/40 must fill half the reserve track")
        self.assertTrue(bool(positive.debt_armor_visible),
            "delayed damage must show the armor debt overlay")
        self.assertTrue(bool(positive.debt_health_visible),
            "delayed damage must show a health debt overlay")
        self.assertTrue(bool(positive.absorb_armor_visible),
            "absorption must show the armor stripe")
        self.assertTrue(bool(positive.absorb_health_visible),
            "absorption must show a health stripe")
        self.assertTrue(bool(positive.info_bg_visible),
            "cocaine info meter capacity must be visible")
        self.assertTrue(bool(positive.info_fill_visible),
            "cocaine info meter fill must be visible")
        self.assertTrue(bool(positive.info_distinct),
            "cocaine info meter background and fill must be distinct")
        self.assertEqual(int(positive.copr_total), 5,
            "COPR ratio 0.2 must create five markers")
        self.assertEqual(int(positive.copr_visible), 3,
            "COPR at 60% health must expose three of five markers")
        self.assertTrue(bool(positive.custom_visible),
            "custom radial progress must be visible")

        zero = g._zero_summary
        self.assertTrue(bool(zero.player_verify),
            "zero update must leave the player panel verified")
        self.assertTrue(bool(zero.gauge_verify),
            "zero update must leave the gauge verified")
        self.assertTrue(bool(zero.same_root),
            "zero update must preserve the player root identity")
        self.assertTrue(bool(zero.same_gauge),
            "zero update must preserve the gauge identity")
        self.assertTrue(bool(zero.reserve_track_visible),
            "zero stock with max 40 must keep the reserve track visible")
        self.assertGreater(float(zero.reserve_track_w), 0.0,
            "zero stock with max 40 must keep a positive reserve track width")
        self.assertAlmostEqual(float(zero.reserve_fill_w), 0.0, delta=0.01,
            msg="zero stock must collapse the reserve fill width")
        self.assertTrue(bool(zero.debt_hidden),
            "zero delayed damage must hide the debt overlays")
        self.assertTrue(bool(zero.absorb_hidden),
            "zero absorption must hide the absorption stripes")
        self.assertTrue(bool(zero.info_hidden),
            "inactive cocaine must hide the info meter")
        self.assertEqual(int(zero.copr_total), 5,
            "zero update must retain the five COPR markers")
        self.assertEqual(int(zero.copr_visible), 0,
            "inactive COPR must hide every marker")
        self.assertTrue(bool(zero.custom_hidden),
            "zero custom progress must hide the custom stripes")
        self.assertTrue(bool(zero.main_unchanged),
            "zero update must not alter primary health/armor geometry or text")

        recovery = g._recovery
        self.assertTrue(bool(recovery.player_verify),
            "recovery update must leave the player panel verified")
        self.assertTrue(bool(recovery.gauge_verify),
            "recovery update must leave the gauge verified")
        self.assertTrue(bool(recovery.reserve_half),
            "recovery must restore the half reserve fill")
        self.assertTrue(bool(recovery.debt_armor_visible),
            "recovery must restore the armor debt overlay")
        self.assertTrue(bool(recovery.debt_health_visible),
            "recovery must restore a health debt overlay")
        self.assertTrue(bool(recovery.absorb_armor_visible),
            "recovery must restore the armor absorption stripe")
        self.assertTrue(bool(recovery.absorb_health_visible),
            "recovery must restore a health absorption stripe")
        self.assertTrue(bool(recovery.info_bg_visible),
            "recovery must restore the info meter capacity")
        self.assertTrue(bool(recovery.info_fill_visible),
            "recovery must restore the info meter fill")
        self.assertTrue(bool(recovery.info_distinct),
            "recovery must restore distinct info meter background and fill")
        self.assertEqual(int(recovery.copr_total), 5,
            "recovery must retain five COPR markers")
        self.assertEqual(int(recovery.copr_visible), 3,
            "recovery must expose three of five COPR markers")
        self.assertTrue(bool(recovery.custom_visible),
            "recovery must restore the custom progress stripes")
        self.assertTrue(bool(recovery.same_primitives),
            "recovery must reuse the saved primitive identities and geometry")


if __name__ == "__main__":
    unittest.main()
