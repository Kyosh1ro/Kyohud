"""Lot 6 RED: local Kingpin ACTIVE must synchronously substitute only the two
native ability bitmap leaves after the real native radial setter and the
registered event hook, with no runtime tick between activation and assertions.

The reusable Hacker runtime owns the real equipment fixture, the overlapping
native radial subtree and the registered hooks. Kingpin only layers native
shaped sources (temporary upgrade, cooldowns, character damage) on top.
"""
import unittest

from test_hud_hacker_active import hacker_lua


KINGPIN_OVERLAY = r'''
-- Native shaped sources layered on the reusable fixture. No production method,
-- snapshot or lease is inserted here.
_G._app_now = 1000
Application = Application or {}
function Application:time() return _app_now end

local original_upgrade_value = managers.player.upgrade_value
local original_has_activate =
    managers.player.has_activate_temporary_upgrade
local original_expire_time = managers.player.get_activate_temporary_expire_time

_G._character_damage = {}
player_unit.character_damage = function() return _character_damage end

_G._player_clock = {_time = 1000}
function _player_clock:time() return self._time end
managers.player.player_timer = function() return _player_clock end

managers.player._temporary_upgrades = {
    temporary = {chico_injector = {expire_time = 1006}},
}

local function chico_record()
    local upgrades = managers.player._temporary_upgrades
    upgrades = upgrades and upgrades.temporary
    return upgrades and upgrades.chico_injector or nil
end

managers.player.upgrade_value = function(self, category, upgrade)
    if category == "temporary" and upgrade == "chico_injector" then
        return {.75, 6}
    end
    if original_upgrade_value then
        return original_upgrade_value(self, category, upgrade)
    end
end

managers.player.has_activate_temporary_upgrade = function(self, category,
        upgrade)
    if category == "temporary" and upgrade == "chico_injector" then
        local record = chico_record()
        return record ~= nil and record.expire_time > Application:time()
    end
    if original_has_activate then
        return original_has_activate(self, category, upgrade)
    end
    return false
end

managers.player.get_activate_temporary_expire_time = function(self, category,
        upgrade)
    if category == "temporary" and upgrade == "chico_injector" then
        local record = chico_record()
        return record and record.expire_time
    end
    if original_expire_time then
        return original_expire_time(self, category, upgrade)
    end
end

_game_clock:set_time(1000)
managers.player:_native_set_grenades("chico_injector", 0, 1)
_native_set_projectile_tweak("chico_injector", {
    ability = true, base_cooldown = 30, icon = "chico_injector"})
managers.player:_native_set_replenish_timer(1017)
_ability_icon:set_image("chico_injector")
_E._icon_cache = nil

-- Exact native radial setter: progress only drives the meter color and the
-- parent visibility, never the two leaves.
local entry = managers.hud._teammate_panels[HUDManager.PLAYER_PANEL]
function HUDTeammate:set_ability_radial(data)
    local p = self._radial_health_panel:child("radial_ability")
    local meter = p:child("ability_meter")
    local progress = data.current / data.total
    meter:set_color(Color(1, progress, 1, 1))
    p:set_visible(progress > 0)
end
entry.set_ability_radial = HUDTeammate.set_ability_radial

function HUDManager:set_teammate_ability_radial(i, data)
    local target = self._teammate_panels[i]
    target:set_ability_radial(data)
    _G._kingpin_native_meter_alpha = _ability_meter:alpha()
    _G._kingpin_native_icon_alpha = _ability_icon:alpha()
    _G._kingpin_native_parent_alpha = _ability_parent:alpha()
    dispatch(HUDManager, "set_teammate_ability_radial", self, i, data)
end

function HUDManager:set_player_ability_radial(data)
    self:set_teammate_ability_radial(HUDManager.PLAYER_PANEL, data)
end

_ability_parent:set_visible(false)
_E:refresh(_m)
_R:refresh_settings(_m)
_R:update(_m, 3.0, 0.1)

_G._pre_kingpin_e_verify = (_E:verify() == true)
_G._pre_kingpin_root_visible = (_E._root ~= nil and _E._root:visible() == true)
_G._pre_kingpin_row4_icon = _E._rows and _E._rows[4] and _E._rows[4]._icon
    and _E._rows[4]._icon:texture_name() or nil
_G._pre_kingpin_row4_visible = (_E._visible_rows and _E._visible_rows[4] == true)
    or false
_G._pre_kingpin_row4_verify = (_E._rows and _E._rows[4]
    and _E._rows[4]:verify() == true) or false
_G._pre_kingpin_parent_hidden = (_ability_parent:visible() == false)
'''

KINGPIN_ACTIVATE = r'''
_m:set_player_ability_radial({current = 6, total = 6})

local nv = kyohud.hud.native_visibility
local meter_entry, icon_entry, parent_entry
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_entry = e end
    if e.object == _ability_icon then icon_entry = e end
    if e.object == _ability_parent then parent_entry = e end
end

_G._post_kingpin_meter_r = _ability_meter:color().r
local registered_set_ability_radial = 0
for _, h in ipairs(Hooks._all) do
    if h.class == HUDManager and h.method == "set_teammate_ability_radial"
        and h.kind == "post" then
        registered_set_ability_radial = registered_set_ability_radial + 1
    end
end
_G._post_kingpin_set_radial_hooks = registered_set_ability_radial

local snap = _E:get_snapshot()
_G._post_kingpin_meter_visible = (_ability_meter:visible() == false)
_G._post_kingpin_icon_visible = (_ability_icon:visible() == false)
_G._post_kingpin_meter_entry_ok = meter_entry ~= nil
    and meter_entry.property == "visible"
    and meter_entry.applied_value == false
_G._post_kingpin_icon_entry_ok = icon_entry ~= nil
    and icon_entry.property == "visible"
    and icon_entry.applied_value == false
_G._post_kingpin_parent_entry = (parent_entry ~= nil)
_G._post_kingpin_e_verify = (_E:verify() == true)
_G._post_kingpin_root_visible = (_E._root ~= nil and _E._root:visible() == true)
_G._post_kingpin_row6_visible = (_E._visible_rows and _E._visible_rows[6] == true)
    or false
_G._post_kingpin_row6_label = _E._rows and _E._rows[6] and _E._rows[6]._label:text()
    or nil
_G._post_kingpin_row6_value = _E._rows and _E._rows[6] and _E._rows[6]._value:text()
    or nil
_G._post_kingpin_row6_progress = _E._rows and _E._rows[6] and _E._rows[6]._progress
_G._post_kingpin_row6_verify = (_E._rows and _E._rows[6]
    and _E._rows[6]:verify() == true) or false
_G._post_kingpin_charges = snap.projectile and snap.projectile.charges
    and snap.projectile.charges.raw
_G._post_kingpin_recharge = snap.cooldown and snap.cooldown.remaining

_G._post_kingpin_parent_visible = (_ability_parent:visible() == true)
_G._post_kingpin_parent_alpha = _ability_parent:alpha()
_G._post_kingpin_meter_alpha = _ability_meter:alpha()
_G._post_kingpin_icon_alpha = _ability_icon:alpha()
_G._post_kingpin_meter_parent = (_ability_meter:parent() == _ability_parent)
_G._post_kingpin_icon_parent = (_ability_icon:parent() == _ability_parent)
_G._post_kingpin_sentinel_visible = (_ability_sentinel:visible() == true)
_G._post_kingpin_sentinel_alpha = _ability_sentinel:alpha()
_G._post_kingpin_sentinel_parent = (_ability_sentinel:parent()
    == _ability_health_parent)
'''


def kingpin_lua():
    """Reusable local Kingpin runtime: the reusable Hacker fixture plus the
    Kingpin-only native shaped overlay (temporary upgrade, cooldowns, damage).
    """
    lua = hacker_lua()
    lua.execute(KINGPIN_OVERLAY)
    return lua


class LocalKingpinActiveTests(unittest.TestCase):
    def test_local_kingpin_activation_leases_only_ability_leaves(self):
        lua = kingpin_lua()
        g = lua.globals()

        self.assertTrue(bool(g._pre_kingpin_e_verify),
            "precondition: equipment render must certify with Kingpin active")
        self.assertTrue(bool(g._pre_kingpin_root_visible),
            "precondition: owned equipment root must be visible")
        self.assertTrue(bool(g._pre_kingpin_row4_visible))
        self.assertTrue(bool(g._pre_kingpin_row4_verify))
        self.assertEqual(g._pre_kingpin_row4_icon, "chico_injector",
            "precondition: equipped Kingpin cell must render chico_injector")
        self.assertTrue(bool(g._pre_kingpin_parent_hidden),
            "precondition: native radial_ability must start hidden")

        lua.execute(KINGPIN_ACTIVATE)

        self.assertAlmostEqual(float(g._post_kingpin_meter_r), 1.0, places=5,
            msg="real native setter must execute: meter red channel == full progress")
        self.assertTrue(bool(g._post_kingpin_parent_visible),
            "real native setter must execute: radial_ability parent visible")
        self.assertEqual(int(g._post_kingpin_set_radial_hooks), 1,
            "exactly one registered set_teammate_ability_radial PostHook")

        self.assertTrue(bool(g._post_kingpin_meter_visible),
            "RED: ACTIVE must hide radial_ability/ability_meter")
        self.assertTrue(bool(g._post_kingpin_icon_visible),
            "RED: ACTIVE must hide radial_ability/ability_icon")
        self.assertTrue(bool(g._post_kingpin_meter_entry_ok),
            "RED: ability_meter needs one visible=false native_visibility entry")
        self.assertTrue(bool(g._post_kingpin_icon_entry_ok),
            "RED: ability_icon needs one visible=false native_visibility entry")
        self.assertFalse(bool(g._post_kingpin_parent_entry),
            "native radial_ability container must never be leased")
        self.assertTrue(bool(g._post_kingpin_e_verify),
            "RED: equipment render must stay certified after synchronous ACTIVE")
        self.assertTrue(bool(g._post_kingpin_root_visible),
            "owned equipment group must stay visible")
        self.assertTrue(bool(g._post_kingpin_row6_visible),
            "RED: ACTIVE row 6 must be visible without a runtime tick")
        self.assertEqual(g._post_kingpin_row6_label, "ACTIVE")
        self.assertEqual(g._post_kingpin_row6_value, "6s")
        self.assertAlmostEqual(float(g._post_kingpin_row6_progress), 1.0,
            places=5, msg="RED: ACTIVE progress must be remaining/duration = 1")
        self.assertTrue(bool(g._post_kingpin_row6_verify),
            "RED: ACTIVE row 6 must pass the real row verifier")
        self.assertEqual(float(g._post_kingpin_charges), 0.0,
            "real projectile charges must be 0 of 1")
        self.assertEqual(float(g._post_kingpin_recharge), 17.0,
            "existing recharge cooldown must stay 17s")

        self.assertTrue(bool(g._post_kingpin_parent_visible),
            "native radial_ability parent must stay visible")
        self.assertAlmostEqual(float(g._post_kingpin_parent_alpha), .73,
            places=5, msg="native parent alpha must be preserved")
        self.assertAlmostEqual(float(g._post_kingpin_meter_alpha),
            float(g._kingpin_native_meter_alpha), places=5,
            msg="native meter alpha observed before hooks must be preserved")
        self.assertAlmostEqual(float(g._post_kingpin_icon_alpha), .67,
            places=5, msg="native icon alpha must be preserved")
        self.assertTrue(bool(g._post_kingpin_meter_parent))
        self.assertTrue(bool(g._post_kingpin_icon_parent))
        self.assertTrue(bool(g._post_kingpin_sentinel_visible),
            "third-party sibling sentinel must stay visible")
        self.assertAlmostEqual(float(g._post_kingpin_sentinel_alpha), .55,
            places=5)
        self.assertTrue(bool(g._post_kingpin_sentinel_parent))


if __name__ == "__main__":
    unittest.main()
