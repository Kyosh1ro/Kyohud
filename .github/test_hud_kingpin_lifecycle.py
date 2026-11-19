"""Lot 6 lifecycle RED: local Kingpin ACTIVE must follow the last local native
publication, never extrapolate from the game clock, and release exactly on a
terminal, expired or conflicted source. Only scalar observations from
native_visibility are compared; no production method, snapshot or lease is
inserted here.
"""
import unittest

from test_hud_kingpin_active import KINGPIN_ACTIVATE, kingpin_lua


HELPERS = r'''
function _ky_scan()
    local nv = kyohud.hud.native_visibility
    local meter_entry, icon_entry, parent_entry, extra_entry
    local meter_leases, icon_leases = 0, 0
    for _, e in ipairs(nv._entries) do
        if e.object == _ability_meter then
            meter_entry = meter_entry or e
            meter_leases = meter_leases + 1
        elseif e.object == _ability_icon then
            icon_entry = icon_entry or e
            icon_leases = icon_leases + 1
        elseif e.object == _ability_parent then
            parent_entry = e
        elseif _G._ability_extra ~= nil and e.object == _G._ability_extra then
            extra_entry = e
        end
    end
    local row6 = _E._rows and _E._rows[6]
    local snap = _E:get_snapshot()
    return {
        meter_visible = (_ability_meter:visible() == true),
        icon_visible = (_ability_icon:visible() == true),
        meter_held = meter_entry ~= nil
            and meter_entry.property == "visible"
            and meter_entry.applied_value == false,
        icon_held = icon_entry ~= nil
            and icon_entry.property == "visible"
            and icon_entry.applied_value == false,
        meter_leases = meter_leases,
        icon_leases = icon_leases,
        parent_lease = (parent_entry ~= nil),
        extra_lease = (extra_entry ~= nil),
        extra_visible = (_G._ability_extra ~= nil
            and _G._ability_extra:visible() == true),
        row6_visible = (((row6 ~= nil)
            and (row6._root ~= nil and row6._root:visible() == true)
            and (_E._root ~= nil and _E._root:visible() == true)
            and (_E._visible_rows and _E._visible_rows[6] == true))
            or false),
        row6_label = row6 and row6._label and row6._label:text() or "",
        row6_value = row6 and row6._value and row6._value:text() or "",
        row6_progress = (row6 and row6._progress) or -1,
        row6_verify = (row6 and row6:verify() == true) or false,
        e_verify = (_E:verify() == true),
        root_visible = (_E._root ~= nil and _E._root:visible() == true),
        parent_visible = (_ability_parent:visible() == true),
        parent_alpha = _ability_parent:alpha(),
        charges = (snap.projectile and snap.projectile.charges
            and snap.projectile.charges.raw) or -1,
        cooldown = (snap.cooldown and snap.cooldown.remaining) or -1,
        snapshot_active = snap.activity and snap.activity.active,
    }
end
'''


def _runtime():
    lua = kingpin_lua()
    lua.execute(HELPERS)
    return lua


def _scan(lua):
    lua.execute("_G._scan = _ky_scan()")
    return lua.globals()._scan


class LocalKingpinLifecycleTests(unittest.TestCase):
    def assert_held(self, obs, context):
        self.assertTrue(bool(obs.meter_held),
            f"{context}: ability_meter must be leased visible=false")
        self.assertTrue(bool(obs.icon_held),
            f"{context}: ability_icon must be leased visible=false")
        self.assertFalse(bool(obs.parent_lease),
            f"{context}: native radial_ability parent must never be leased")

    def assert_released(self, obs, context):
        self.assertTrue(bool(obs.meter_visible),
            f"{context}: ability_meter must be restored exactly visible")
        self.assertTrue(bool(obs.icon_visible),
            f"{context}: ability_icon must be restored exactly visible")
        self.assertFalse(bool(obs.meter_held),
            f"{context}: ability_meter must hold no lease")
        self.assertFalse(bool(obs.icon_held),
            f"{context}: ability_icon must hold no lease")
        self.assertFalse(bool(obs.parent_lease),
            f"{context}: native radial_ability parent must never be leased")

    def test_published_current_drives_row_without_game_extrapolation(self):
        lua = _runtime()
        g = lua.globals()
        lua.execute(KINGPIN_ACTIVATE)
        obs = _scan(lua)
        self.assert_held(obs, "initial publication")
        self.assertTrue(bool(obs.row6_visible))
        self.assertEqual(obs.row6_value, "6s")

        lua.execute(r'''
local row6 = _E._rows[6]
local value = row6._value
_G._t1_row, _G._t1_value = row6, value
_app_now = 1001
_player_clock._time = 1001
_game_clock:set_time(1001)
_m:set_player_ability_radial({current = 4.25, total = 6})
_G._t1_same_row = (_E._rows[6] == row6)
_G._t1_same_value = (_E._rows[6]._value == value)
''')
        obs = _scan(lua)
        self.assert_held(obs, "4.25/6 publication")
        self.assertTrue(bool(g._t1_same_row))
        self.assertTrue(bool(g._t1_same_value))
        self.assertTrue(bool(obs.row6_visible))
        self.assertEqual(obs.row6_label, "ACTIVE")
        self.assertEqual(obs.row6_value, "5s")
        self.assertAlmostEqual(float(obs.row6_progress), 4.25 / 6.0, places=6)
        self.assertTrue(bool(obs.e_verify))
        self.assertTrue(bool(obs.root_visible))
        self.assertTrue(bool(obs.parent_visible))

        lua.execute(r'''
_app_now = 1001.01
_player_clock._time = 1001.01
_game_clock:set_time(1010)
_R:update(_m, 3.01, .001)
_G._t1_throttled_same_row = (_E._rows[6] == _t1_row)
_G._t1_throttled_same_value = (_E._rows[6]._value == _t1_value)
''')
        obs = _scan(lua)
        self.assert_held(obs, "throttled update")
        self.assertTrue(bool(g._t1_throttled_same_row))
        self.assertTrue(bool(g._t1_throttled_same_value))
        self.assertEqual(obs.row6_value, "5s")
        self.assertAlmostEqual(float(obs.row6_progress), 4.25 / 6.0, places=6)

        lua.execute(r'''
_m:set_player_ability_radial({current = 0, total = 1})
_G._t1_terminal_alpha = _ability_parent:alpha()
''')
        obs = _scan(lua)
        self.assert_released(obs, "terminal 0/1")
        self.assertFalse(bool(obs.row6_visible))
        self.assertFalse(bool(obs.parent_visible))
        self.assertFalse(bool(obs.parent_lease))
        self.assertAlmostEqual(float(obs.parent_alpha), .73, places=5)
        self.assertAlmostEqual(float(obs.charges), 0.0)
        self.assertAlmostEqual(float(obs.cooldown), 7.0)

    def test_source_identity_or_native_mismatch_releases_and_guards(self):
        cases = [
            ("player_timer", "managers.player.player_timer = function() "
                "return {time = function() return 1001 end} end"),
            ("timer_game", "local game = {time = function() return 1000 end}; "
                "TimerManager.game = function() return game end"),
            ("character_damage", "player_unit.character_damage = function() "
                "return {} end"),
            ("record_same_values", "managers.player._temporary_upgrades."
                "temporary.chico_injector = {expire_time = 1006}"),
            ("category_same_record", "local r = managers.player."
                "_temporary_upgrades.temporary.chico_injector; managers.player."
                "_temporary_upgrades.temporary = {chico_injector = r}"),
            ("temporary_root", "local r = managers.player."
                "_temporary_upgrades.temporary.chico_injector; managers.player."
                "_temporary_upgrades = {temporary = {chico_injector = r}}"),
            ("grenade_registry", "local clone = {}; for k, v in pairs("
                "managers.player._global.synced_grenades) do clone[k] = v end; "
                "managers.player._global.synced_grenades = clone"),
            ("application_replaced", "Application = {time = function() "
                "return 1000 end}"),
            ("application_time_throws", "Application = {time = function() "
                "error('kingpin application') end}"),
            ("duration_nan", "managers.player.upgrade_value = function() "
                "return {.75, 0/0} end"),
            ("ratio_mismatch", "_ability_meter:set_color(Color(1, .25, 1, 1))"),
            ("extra_child", "local e = _ability_parent:bitmap("
                "{name = 'ky_test_extra'}); e:set_shape(0, 0, 2, 2); "
                "e:set_visible(true); _G._ability_extra = e"),
            ("icon_wrong_substring", "_ability_icon:set_image("
                "'chico_injector_impostor')"),
        ]
        for name, mutation in cases:
            with self.subTest(case=name):
                lua = _runtime()
                g = lua.globals()
                lua.execute(KINGPIN_ACTIVATE)
                self.assert_held(_scan(lua), f"{name} acquisition")
                lua.execute(mutation)
                lua.execute(r'''
_G._t2_ok, _G._t2_err = pcall(function()
    _R:update(_m, 3.001, .001)
end)
''')
                obs = _scan(lua)
                self.assertTrue(bool(g._t2_ok), f"{name}: update must not throw")
                self.assertTrue(bool(obs.meter_visible), f"{name}: meter restored")
                self.assertTrue(bool(obs.icon_visible), f"{name}: icon restored")
                self.assertFalse(bool(obs.meter_held), f"{name}: no meter lease")
                self.assertFalse(bool(obs.icon_held), f"{name}: no icon lease")
                self.assertFalse(bool(obs.parent_lease),
                    f"{name}: no parent lease")
                self.assertFalse(bool(obs.extra_lease),
                    f"{name}: no extra lease")
                self.assertFalse(bool(obs.root_visible),
                    f"{name}: overlapping native parent must hide owned root")

    def test_clock_repair_does_not_resurrect_and_expiry_releases(self):
        lua = _runtime()
        g = lua.globals()
        lua.execute(KINGPIN_ACTIVATE)
        self.assert_held(_scan(lua), "initial")

        lua.execute(r'''
_app_now = 1001
_player_clock._time = 1001
_game_clock:set_time(1001)
_R:update(_m, 3.001, .001)
_G._t3_forward = _ky_scan()
_app_now = 1000.5
_player_clock._time = 1000.5
_game_clock:set_time(1000.5)
_R:update(_m, 3.002, .001)
_G._t3_backward = _ky_scan()
_app_now = 1001
_player_clock._time = 1001
_game_clock:set_time(1001)
_R:update(_m, 3.1, .1)
_G._t3_repaired = _ky_scan()
''')
        self.assert_held(g._t3_forward, "forward clock")
        self.assert_released(g._t3_backward, "backward clock")
        repaired = g._t3_repaired
        self.assert_released(repaired, "clock repair")
        self.assertFalse(bool(repaired.root_visible))

        lua.execute(r'''
_m:set_player_ability_radial({current = 6, total = 6})
_G._t3_reacquired = _ky_scan()
_app_now = 1006
_player_clock._time = 1006
_game_clock:set_time(1006)
_R:update(_m, 3.2, .001)
_G._t3_expired = _ky_scan()
''')
        self.assert_held(g._t3_reacquired, "genuine new publication")
        expired = g._t3_expired
        self.assert_released(expired, "expiry without zero")
        self.assertFalse(bool(expired.row6_visible))
        self.assertTrue(expired.snapshot_active is False,
            "expired ACTIVE must be false in the snapshot")

    def test_conflict_is_not_remasked_by_same_record_publication(self):
        lua = _runtime()
        g = lua.globals()
        lua.execute(KINGPIN_ACTIVATE)
        self.assert_held(_scan(lua), "initial")

        lua.execute(r'''
_app_now = 1000.1
_player_clock._time = 1000.1
_game_clock:set_time(1000.1)
_ability_meter:set_visible(true)
_R:update(_m, 3.001, .001)
_G._t4_conflict = _ky_scan()
_m:set_player_ability_radial({current = 5.9, total = 6})
_G._t4_same_record = _ky_scan()
_m:set_player_ability_radial({current = 0, total = 1})
managers.player._temporary_upgrades.temporary.chico_injector = {
    expire_time = 1006}
_m:set_player_ability_radial({current = 6, total = 6})
_G._t4_new_record = _ky_scan()
''')
        conflict = g._t4_conflict
        self.assertTrue(bool(conflict.meter_visible))
        self.assertTrue(bool(conflict.icon_visible))
        self.assertFalse(bool(conflict.meter_held))
        self.assertFalse(bool(conflict.icon_held))
        self.assertFalse(bool(conflict.parent_lease))
        self.assertFalse(bool(conflict.root_visible))

        same = g._t4_same_record
        self.assertTrue(bool(same.meter_visible))
        self.assertTrue(bool(same.icon_visible))
        self.assertFalse(bool(same.meter_held))
        self.assertFalse(bool(same.icon_held))
        self.assertFalse(bool(same.root_visible))

        recovered = g._t4_new_record
        self.assert_held(recovered, "new record activation")
        self.assertTrue(bool(recovered.row6_visible))
        self.assertTrue(bool(recovered.root_visible))
        self.assertEqual(int(recovered.meter_leases), 1)
        self.assertEqual(int(recovered.icon_leases), 1)

    def test_disabled_retained_publication_and_record_only(self):
        lua = _runtime()
        g = lua.globals()
        lua.execute(KINGPIN_ACTIVATE)
        self.assert_held(_scan(lua), "initial")

        lua.execute(r'''
kyohud.settings.enable_equipment = false
_R:refresh_settings(_m)
_G._t5_off = _ky_scan()
_app_now = 1001
_player_clock._time = 1001
_game_clock:set_time(1001)
_m:set_player_ability_radial({current = 5, total = 6})
_G._t5_off_event = _ky_scan()
_game_clock:set_time(1010)
kyohud.settings.enable_equipment = true
_R:refresh_settings(_m)
_R:update(_m, 3.0, .1)
_G._t5_on = _ky_scan()
''')
        off = g._t5_off
        self.assert_released(off, "equipment off")
        self.assertFalse(bool(off.row6_visible))
        off_event = g._t5_off_event
        self.assert_released(off_event, "event while off")
        self.assertFalse(bool(off_event.row6_visible))
        on = g._t5_on
        self.assert_held(on, "re-enabled retained publication")
        self.assertTrue(bool(on.row6_visible))
        self.assertEqual(on.row6_label, "ACTIVE")
        self.assertEqual(on.row6_value, "5s")
        self.assertAlmostEqual(float(on.row6_progress), 5.0 / 6.0, places=6)
        self.assertTrue(bool(on.e_verify))

        fresh = _runtime()
        fresh.execute("_R:update(_m, 3.0, .1)")
        obs = _scan(fresh)
        self.assert_released(obs, "record without event")
        self.assertFalse(bool(obs.row6_visible))
        self.assertEqual(int(obs.meter_leases), 0)
        self.assertEqual(int(obs.icon_leases), 0)


if __name__ == "__main__":
    unittest.main()
