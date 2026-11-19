"""Lot 6 safety RED: corrupting the owned row label setter after a positive
Kingpin acquisition must release the native leases without recreating the row;
an ordinary repair must then fix the text on the very same row/value objects."""
import unittest

from test_hud_kingpin_active import KINGPIN_ACTIVATE, kingpin_lua
from test_hud_kingpin_lifecycle import HELPERS, _scan


def _runtime():
    lua = kingpin_lua()
    lua.execute(HELPERS)
    lua.execute(KINGPIN_ACTIVATE)
    return lua


LEASE_EXPORT = r'''
local meter, icon, parent = 0, 0, false
local entries = kyohud.hud.native_visibility._entries
for _, e in ipairs(entries) do
    if e.object == _ability_meter and e.property == "visible" and e.applied_value == false then
        meter = meter + 1
    elseif e.object == _ability_icon and e.property == "visible" and e.applied_value == false then
        icon = icon + 1
    elseif e.object == _ability_parent then
        parent = true
    end
end
_G._lease = {meter = meter, icon = icon, parent = parent, entries = #entries}
'''


class OwnedRowLabelSafetyTests(unittest.TestCase):
    def test_corrupt_owned_setter_releases_then_repairs_same_objects(self):
        lua = _runtime()
        g = lua.globals()
        initial = _scan(lua)
        self.assertTrue(bool(initial.meter_held))
        self.assertTrue(bool(initial.icon_held))
        self.assertTrue(bool(initial.root_visible))

        lua.execute(r'''
local row6 = _E._rows[6]
local value = row6._value
_G._s_row6, _G._s_value = row6, value
_G._s_setter = value.set_text
value:set_text("BROKEN")
value.set_text = function() end
_R:update(_m, 3.001, .001)
''')
        lua.execute(LEASE_EXPORT)
        broken = _scan(lua)
        lease = g._lease
        self.assertTrue(bool(broken.meter_visible))
        self.assertTrue(bool(broken.icon_visible))
        self.assertFalse(bool(broken.meter_held))
        self.assertFalse(bool(broken.icon_held))
        self.assertEqual(int(lease.meter), 0)
        self.assertEqual(int(lease.icon), 0)
        self.assertFalse(bool(lease.parent))
        self.assertEqual(int(lease.entries), 0)
        self.assertFalse(bool(broken.root_visible))
        self.assertFalse(bool(broken.e_verify))

        lua.execute(r'''
_G._s_value.set_text = _G._s_setter
_R:update(_m, 3.1, .1)
_G._s_same_row = (_E._rows[6] == _G._s_row6)
_G._s_same_value = (_E._rows[6]._value == _G._s_value)
_G._s_text = _E._rows[6]._value:text()
_G._s_source_nil = (_E:get_hacker_activity_source() == nil)
''')
        lua.execute(LEASE_EXPORT)
        repaired = _scan(lua)
        lease = g._lease
        self.assertTrue(bool(g._s_same_row))
        self.assertTrue(bool(g._s_same_value))
        self.assertEqual(g._s_text, "6s")
        self.assertFalse(bool(repaired.meter_visible))
        self.assertFalse(bool(repaired.icon_visible))
        self.assertTrue(bool(repaired.meter_held))
        self.assertTrue(bool(repaired.icon_held))
        self.assertEqual(int(lease.meter), 1)
        self.assertEqual(int(lease.icon), 1)
        self.assertFalse(bool(lease.parent))
        self.assertTrue(bool(g._s_source_nil))

    def test_missing_player_timer_cannot_certify(self):
        lua = kingpin_lua()
        lua.execute(HELPERS)
        lua.execute("managers.player.player_timer=function() return nil end")
        lua.execute(KINGPIN_ACTIVATE)

        obs = _scan(lua)
        self.assertTrue(bool(obs.meter_visible))
        self.assertTrue(bool(obs.icon_visible))
        self.assertFalse(bool(obs.meter_held))
        self.assertFalse(bool(obs.icon_held))
        self.assertTrue(bool(lua.eval("_E:get_kingpin_activity_source()==nil")))

        lua.execute("_missing_activity=_E:get_snapshot().activity")
        known = bool(lua.globals()._missing_activity.known)
        active = bool(lua.globals()._missing_activity.active)
        self.assertFalse(known and active)

    def test_failed_positive_publication_never_uses_game_countdown(self):
        lua = kingpin_lua()
        lua.execute(HELPERS)
        lua.execute("_m:set_player_ability_radial({current=4,total=5})")

        lua.execute("_activity=_E:get_snapshot().activity")
        act = lua.globals()._activity
        self.assertFalse(bool(act.known) and bool(act.active))
        self.assertTrue(bool(lua.eval("_E:get_kingpin_activity_source()==nil")))

        obs = _scan(lua)
        self.assertTrue(bool(obs.meter_visible))
        self.assertTrue(bool(obs.icon_visible))
        self.assertFalse(bool(obs.meter_held))
        self.assertFalse(bool(obs.icon_held))
        lua.execute(LEASE_EXPORT)
        self.assertFalse(bool(lua.globals()._lease.meter))
        self.assertFalse(bool(lua.globals()._lease.icon))
        self.assertFalse(bool(lua.globals()._lease.parent))

        lua.execute("_game_clock:set_time(1001)")
        lua.execute("_R:update(_m, 3.1, .1)")
        lua.execute("_activity=_E:get_snapshot().activity")
        act = lua.globals()._activity
        self.assertFalse(bool(act.known) and bool(act.active))
        self.assertTrue(bool(lua.eval("_E:get_kingpin_activity_source()==nil")))

    def test_no_kingpin_provenance_does_no_full_throttle_verify(self):
        from test_hud_hacker_active import hacker_lua, ACTIVATE_AND_OBSERVE
        lua = hacker_lua()
        lua.execute(ACTIVATE_AND_OBSERVE)
        self.assertTrue(bool(lua.globals()._post_e_verify))
        lua.execute(r'''
_G._extra_verifies = 0
local original = _E.verify
_E.verify = function(self, ...)
    _G._extra_verifies = _G._extra_verifies + 1
    return original(self, ...)
end
_E:_throttle_kingpin_activity()
''')
        self.assertEqual(int(lua.globals()._extra_verifies), 0)

    def test_remote_ability_radial_cannot_release_local_kingpin(self):
        lua = kingpin_lua()
        g = lua.globals()
        lua.execute(HELPERS)
        lua.execute(KINGPIN_ACTIVATE)

        local_state = _scan(lua)
        self.assertTrue(bool(local_state.meter_held),
            "precondition: local Kingpin must lease ability_meter")
        self.assertTrue(bool(local_state.icon_held),
            "precondition: local Kingpin must lease ability_icon")
        self.assertTrue(bool(local_state.root_visible),
            "precondition: local Kingpin group must be visible")
        self.assertTrue(bool(lua.eval("_E:verify() == true")),
            "precondition: local Kingpin render must certify")
        self.assertTrue(bool(lua.eval("_E:get_kingpin_activity_source() ~= nil")),
            "precondition: local Kingpin provenance must be active")

        lua.execute(r'''
_G._remote_saved_kingpin_activity = _E._kingpin_activity

local remote_panel = panel_double:panel({name = "remote_teammate"})
remote_panel:set_shape(0, 0, 432, 120)
remote_panel:set_visible(true)
local remote_player = remote_panel:panel({name = "player"})
remote_player:set_shape(0, 0, 432, 120)
remote_player:set_visible(true)
local remote_health = remote_player:panel({name = "radial_health_panel"})
remote_health:set_shape(0, 0, 432, 120)
remote_health:set_visible(true)
local remote_radial = remote_health:panel({name = "radial_ability"})
remote_radial:set_shape(0, 0, 432, 120)
remote_radial:set_visible(false)
local remote_meter = remote_radial:bitmap({name = "ability_meter"})
remote_meter:set_shape(0, 0, 32, 32)
remote_meter:set_visible(true)
local remote_icon = remote_radial:bitmap({name = "ability_icon"})
remote_icon:set_shape(0, 0, 32, 32)
remote_icon:set_visible(true)
_G._remote_meter = remote_meter
_G._remote_icon = remote_icon
_G._remote_radial = remote_radial

managers.hud._teammate_panels[1] = {
    _ai = false,
    _peer_id = 2,
    _panel = remote_panel,
    _radial_health_panel = remote_health,
    set_ability_radial = HUDTeammate.set_ability_radial,
}

_m:set_teammate_ability_radial(1, {current = 2, total = 6})

local nv = kyohud.hud.native_visibility
local local_meter, local_icon, local_parent = 0, 0, 0
local remote_meter, remote_icon, remote_parent = 0, 0, 0
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter and e.property == "visible"
        and e.applied_value == false then
        local_meter = local_meter + 1
    end
    if e.object == _ability_icon and e.property == "visible"
        and e.applied_value == false then
        local_icon = local_icon + 1
    end
    if e.object == _ability_parent then
        local_parent = local_parent + 1
    end
    if e.object == _G._remote_meter then
        remote_meter = remote_meter + 1
    end
    if e.object == _G._remote_icon then
        remote_icon = remote_icon + 1
    end
    if e.object == _G._remote_radial then
        remote_parent = remote_parent + 1
    end
end
_G._r_local_meter_count = local_meter
_G._r_local_icon_count = local_icon
_G._r_local_parent_count = local_parent
_G._r_remote_meter_count = remote_meter
_G._r_remote_icon_count = remote_icon
_G._r_remote_parent_count = remote_parent
_G._r_provenance_same = (_E._kingpin_activity == _G._remote_saved_kingpin_activity)
_G._r_source_valid = (_E:get_kingpin_activity_source() ~= nil)
_G._r_local_meter_hidden = (_ability_meter:visible() == false)
_G._r_local_icon_hidden = (_ability_icon:visible() == false)
_G._r_remote_meter_visible = (_G._remote_meter:visible() == true)
_G._r_remote_icon_visible = (_G._remote_icon:visible() == true)
_G._r_remote_parent_visible = (_G._remote_radial:visible() == true)
_G._r_e_verify = (_E:verify() == true)
_G._r_e_root_visible = (_E._root ~= nil and _E._root:visible() == true)
''')

        self.assertTrue(bool(g._r_provenance_same),
            "remote radial must not replace local Kingpin provenance")
        self.assertTrue(bool(g._r_source_valid),
            "remote radial must not clear the local Kingpin activity source")
        self.assertEqual(int(g._r_local_meter_count), 1,
            "local ability_meter must keep exactly one lease")
        self.assertEqual(int(g._r_local_icon_count), 1,
            "local ability_icon must keep exactly one lease")
        self.assertEqual(int(g._r_local_parent_count), 0,
            "local radial_ability container must never be leased")
        self.assertTrue(bool(g._r_local_meter_hidden),
            "local ability_meter must stay hidden")
        self.assertTrue(bool(g._r_local_icon_hidden),
            "local ability_icon must stay hidden")
        self.assertTrue(bool(g._r_remote_meter_visible),
            "remote ability_meter must stay visible")
        self.assertTrue(bool(g._r_remote_icon_visible),
            "remote ability_icon must stay visible")
        self.assertTrue(bool(g._r_remote_parent_visible),
            "remote radial_ability must stay visible")
        self.assertEqual(int(g._r_remote_meter_count), 0,
            "remote ability_meter must never be leased")
        self.assertEqual(int(g._r_remote_icon_count), 0,
            "remote ability_icon must never be leased")
        self.assertEqual(int(g._r_remote_parent_count), 0,
            "remote radial_ability must never be leased")
        self.assertTrue(bool(g._r_e_verify),
            "local Kingpin render must stay certified")
        self.assertTrue(bool(g._r_e_root_visible),
            "local Kingpin group must stay visible")

    def test_hacker_and_kingpin_share_existing_group_binding(self):
        from test_hud_hacker_active import ACTIVATE_AND_OBSERVE, hacker_lua
        from test_hud_kingpin_active import KINGPIN_OVERLAY

        lua = hacker_lua()
        g = lua.globals()
        lua.execute(ACTIVATE_AND_OBSERVE)

        self.assertTrue(bool(g._post_e_verify),
            "precondition: genuine Hacker activation must certify")
        self.assertTrue(bool(g._post_equipment_visible),
            "precondition: Hacker equipment group must be visible")
        self.assertTrue(bool(g._post_meter_visible),
            "precondition: Hacker must lease ability_meter")
        self.assertTrue(bool(g._post_icon_visible),
            "precondition: Hacker must lease ability_icon")
        self.assertEqual(g._post_row6_label, "ACTIVE")
        self.assertEqual(g._post_row6_value, "6s")
        self.assertAlmostEqual(float(g._post_row6_progress), 1.0, places=5)
        self.assertTrue(bool(g._post_row6_verify),
            "precondition: Hacker ACTIVE row must certify")

        lua.execute(r'''
_G._group_binding_from_hacker = _R._hacker_active_binding
_G._hacker_source_kind_before = _E:get_hacker_activity_source().kind
_G._initial_meter_owner = nil
local nv = kyohud.hud.native_visibility
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter and e.property == "visible"
        and e.applied_value == false then
        _G._initial_meter_owner = e.owner
    end
end
''')
        self.assertEqual(g._hacker_source_kind_before, "pocket_ecm_jammer_local")
        self.assertIsNotNone(g._group_binding_from_hacker)
        self.assertEqual(g._group_binding_from_hacker.source_kind,
            "pocket_ecm_jammer_local")
        self.assertIsNotNone(g._initial_meter_owner)

        lua.execute(KINGPIN_OVERLAY)
        lua.execute(KINGPIN_ACTIVATE)

        lua.execute(r'''
local nv = kyohud.hud.native_visibility
local meter_count, icon_count, parent_count = 0, 0, 0
local meter_owner = nil
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter and e.property == "visible"
        and e.applied_value == false then
        meter_count = meter_count + 1
        meter_owner = e.owner
    end
    if e.object == _ability_icon and e.property == "visible"
        and e.applied_value == false then
        icon_count = icon_count + 1
    end
    if e.object == _ability_parent then
        parent_count = parent_count + 1
    end
end
_G._k1_meter_count = meter_count
_G._k1_icon_count = icon_count
_G._k1_parent_count = parent_count
_G._k1_same_owner = (meter_owner == _G._initial_meter_owner)
_G._k1_binding_source_kind = _R._hacker_active_binding
    and _R._hacker_active_binding.source_kind or nil
_G._k1_hacker_source_nil = (_E:get_hacker_activity_source() == nil)
_G._k1_kingpin_source_valid = (_E:get_kingpin_activity_source() ~= nil)
_G._k1_meter_hidden = (_ability_meter:visible() == false)
_G._k1_icon_hidden = (_ability_icon:visible() == false)
_G._k1_e_verify = (_E:verify() == true)
_G._k1_e_root_visible = (_E._root ~= nil and _E._root:visible() == true)
''')

        self.assertTrue(bool(g._k1_same_owner),
            "Kingpin must keep the existing local_p_hacker_active meter lease owner")
        self.assertEqual(g._k1_binding_source_kind, "chico_injector_local",
            "shared binding must arbitrate the Kingpin source")
        self.assertTrue(bool(g._k1_hacker_source_nil),
            "Kingpin must replace the local Hacker activity source")
        self.assertTrue(bool(g._k1_kingpin_source_valid),
            "Kingpin activity source must be valid")
        self.assertEqual(int(g._k1_meter_count), 1,
            "Kingpin must not duplicate the ability_meter lease")
        self.assertEqual(int(g._k1_icon_count), 1,
            "Kingpin must not duplicate the ability_icon lease")
        self.assertEqual(int(g._k1_parent_count), 0,
            "Kingpin must never lease the native radial_ability container")
        self.assertTrue(bool(g._k1_meter_hidden))
        self.assertTrue(bool(g._k1_icon_hidden))
        self.assertTrue(bool(g._k1_e_verify))
        self.assertTrue(bool(g._k1_e_root_visible))

        lua.execute(r'''
managers.player:_native_set_grenades("pocket_ecm_jammer", 1, 2)
_ability_icon:set_image("guis/dlcs/joy/textures/pd2/hud_pocket_ecm_jammer")
_E._icon_cache = nil
_E:refresh(_m)
_R:refresh_settings(_m)
''')
        lua.execute(ACTIVATE_AND_OBSERVE)

        self.assertTrue(bool(g._post_e_verify),
            "genuine reversed Hacker activation must certify")
        self.assertTrue(bool(g._post_meter_visible),
            "reversed Hacker activation must lease ability_meter")
        self.assertTrue(bool(g._post_icon_visible),
            "reversed Hacker activation must lease ability_icon")
        self.assertEqual(g._post_row6_label, "ACTIVE")
        self.assertEqual(g._post_row6_value, "6s")

        lua.execute(r'''
local nv = kyohud.hud.native_visibility
local meter_count, icon_count, parent_count = 0, 0, 0
local meter_owner = nil
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter and e.property == "visible"
        and e.applied_value == false then
        meter_count = meter_count + 1
        meter_owner = e.owner
    end
    if e.object == _ability_icon and e.property == "visible"
        and e.applied_value == false then
        icon_count = icon_count + 1
    end
    if e.object == _ability_parent then
        parent_count = parent_count + 1
    end
end
local source = _E:get_hacker_activity_source()
_G._k2_meter_count = meter_count
_G._k2_icon_count = icon_count
_G._k2_parent_count = parent_count
_G._k2_source_kind = source and source.kind or nil
_G._k2_same_owner = (meter_owner == _G._initial_meter_owner)
_G._k2_binding_source_kind = _R._hacker_active_binding
    and _R._hacker_active_binding.source_kind or nil
_G._k2_kingpin_source_nil = (_E:get_kingpin_activity_source() == nil)
_G._k2_meter_hidden = (_ability_meter:visible() == false)
_G._k2_icon_hidden = (_ability_icon:visible() == false)
_G._k2_e_verify = (_E:verify() == true)
_G._k2_e_root_visible = (_E._root ~= nil and _E._root:visible() == true)
''')

        self.assertEqual(g._k2_source_kind, "pocket_ecm_jammer_local",
            "reversed Hacker source must be the local pocket ECM")
        self.assertTrue(bool(g._k2_same_owner),
            "reversed Hacker must keep the existing local_p_hacker_active meter lease owner")
        self.assertEqual(g._k2_binding_source_kind, "pocket_ecm_jammer_local",
            "shared binding must arbitrate the Hacker source")
        self.assertEqual(int(g._k2_meter_count), 1,
            "reversed Hacker must keep exactly one ability_meter lease")
        self.assertEqual(int(g._k2_icon_count), 1,
            "reversed Hacker must keep exactly one ability_icon lease")
        self.assertEqual(int(g._k2_parent_count), 0,
            "reversed Hacker must never lease the native radial_ability container")
        self.assertTrue(bool(g._k2_kingpin_source_nil),
            "Kingpin provenance must be cleared after the native reversal")
        self.assertTrue(bool(g._k2_meter_hidden))
        self.assertTrue(bool(g._k2_icon_hidden))
        self.assertTrue(bool(g._k2_e_verify))
        self.assertTrue(bool(g._k2_e_root_visible))


if __name__ == "__main__":
    unittest.main()
