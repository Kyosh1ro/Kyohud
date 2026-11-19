"""Lot 6 lifecycle: local Hacker ACTIVE holds only the two native ability bitmap
leaves while the real native animation runs, then restores those leaves exactly
to visible and drops both native_visibility entries when the native animation
finishes and the local jammer record disappears before one ordinary runtime
update. Recharge stays native and intact throughout.

Reuses the existing Hacker runtime (real equipment fixture + native ability
panel + native-shaped activation dispatcher) and its synchronous ACTIVE
observation. No fixture is cloned here.
"""
import unittest

from test_hud_hacker_active import ACTIVATE_AND_OBSERVE, hacker_lua


class LocalHackerLifecycleTests(unittest.TestCase):
    def assert_bound(self, meter_hidden, icon_hidden, meter_lease, icon_lease,
            context):
        self.assertTrue(bool(meter_hidden),
            f"{context}: ability_meter must be leased hidden")
        self.assertTrue(bool(icon_hidden),
            f"{context}: ability_icon must be leased hidden")
        self.assertTrue(bool(meter_lease),
            f"{context}: ability_meter must hold one native_visibility entry")
        self.assertTrue(bool(icon_lease),
            f"{context}: ability_icon must hold one native_visibility entry")

    def assert_released(self, meter_visible, icon_visible, meter_lease,
            icon_lease, context):
        self.assertTrue(bool(meter_visible),
            f"{context}: ability_meter must be restored exactly visible")
        self.assertTrue(bool(icon_visible),
            f"{context}: ability_icon must be restored exactly visible")
        self.assertFalse(bool(meter_lease),
            f"{context}: ability_meter must have no native_visibility entry")
        self.assertFalse(bool(icon_lease),
            f"{context}: ability_icon must have no native_visibility entry")

    def test_native_end_releases_leaves_and_keeps_recharge(self):
        lua = hacker_lua()
        g = lua.globals()

        lua.execute(ACTIVATE_AND_OBSERVE)

        self.assertTrue(bool(g._post_e_verify),
            "positive activation must certify the owned equipment render")
        self.assert_bound(g._post_meter_visible, g._post_icon_visible,
            g._post_meter_entry_ok, g._post_icon_entry_ok, "activation")
        self.assertFalse(bool(g._post_parent_leased),
            "the native radial_ability parent must never be leased")

        lua.execute(r'''
_G._life_row6_value = _E._rows[6]._value
''')

        lua.execute(r'''
_game_clock:set_time(1003)
local anim = _ability_parent._ky_animation
_G._life_anim = anim
_G._life_mid_resume_ok = false
if anim ~= nil and coroutine.status(anim) == "suspended" then
    local ok = coroutine.resume(anim, 3)
    _G._life_mid_resume_ok = (ok == true)
end

_R:update(_m, 3.1, .1)

local nv = kyohud.hud.native_visibility
local meter_lease, icon_lease
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_lease = true end
    if e.object == _ability_icon then icon_lease = true end
end

_G._life_same_value = (_E._rows[6]._value == _life_row6_value)
_G._life_mid_row6_visible = (_E._visible_rows[6] == true)
_G._life_mid_row6_value = _E._rows[6]._value:text()
_G._life_mid_row6_progress = _E._rows[6]._progress
_G._life_mid_row6_verify = (_E._rows[6]:verify() == true)
_G._life_mid_e_verify = (_E:verify() == true)
_G._life_mid_meter_hidden = (_ability_meter:visible() == false)
_G._life_mid_icon_hidden = (_ability_icon:visible() == false)
_G._life_mid_meter_lease = (meter_lease == true)
_G._life_mid_icon_lease = (icon_lease == true)
''')

        self.assertTrue(bool(g._life_mid_resume_ok),
            "real native ability animation must resume for three seconds")
        self.assertTrue(bool(g._life_same_value),
            "ordinary update must reuse the same ACTIVE row primitive")
        self.assertTrue(bool(g._life_mid_row6_visible),
            "ACTIVE row must stay visible mid-ability")
        self.assertEqual(g._life_mid_row6_value, "3s",
            "ACTIVE row must show the 3s native remainder")
        self.assertAlmostEqual(float(g._life_mid_row6_progress), 0.5,
            places=6,
            msg="ACTIVE row progress must be remaining/duration = 0.5")
        self.assertTrue(bool(g._life_mid_row6_verify),
            "mid-life ACTIVE row must pass its real verifier")
        self.assertTrue(bool(g._life_mid_e_verify),
            "owned equipment render must stay certified mid-ability")
        self.assert_bound(g._life_mid_meter_hidden, g._life_mid_icon_hidden,
            g._life_mid_meter_lease, g._life_mid_icon_lease, "mid-life")

        lua.execute(r'''
_game_clock:set_time(1006)
local anim = _life_anim
_G._life_same_co = (anim ~= nil and _ability_parent._ky_animation == anim)
_G._life_final_resume_ok = false
if anim ~= nil and coroutine.status(anim) == "suspended" then
    local ok = coroutine.resume(anim, 3)
    _G._life_final_resume_ok = (ok == true)
end

_G._life_dead = (anim ~= nil and coroutine.status(anim) == "dead")
_G._life_parent_hidden = (_ability_parent:visible() == false)
local c = _ability_meter:color()
_G._life_meter_r = c and c.r
_G._life_leaf_hidden_before = (_ability_meter:visible() == false
    and _ability_icon:visible() == false)

inventory._jammer_data = nil

_R:update(_m, 3.2, .1)

local nv = kyohud.hud.native_visibility
local meter_entry, icon_entry
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_entry = e end
    if e.object == _ability_icon then icon_entry = e end
end

local snap = _E:get_snapshot()
_G._life_end_meter_visible = (_ability_meter:visible() == true)
_G._life_end_icon_visible = (_ability_icon:visible() == true)
_G._life_end_meter_lease = (meter_entry ~= nil)
_G._life_end_icon_lease = (icon_entry ~= nil)
_G._life_active_hidden = not (_E._visible_rows
    and _E._visible_rows[6] == true)
_G._life_e_root_visible = (_E._root ~= nil and _E._root:visible() == true)
_G._life_e_verify = (_E:verify() == true)
_G._life_end_remaining = snap.cooldown and snap.cooldown.remaining
_G._life_end_charges = snap.projectile and snap.projectile.charges
    and snap.projectile.charges.raw
''')

        self.assertTrue(bool(g._life_same_co),
            "second native resume must reuse the same coroutine")
        self.assertTrue(bool(g._life_final_resume_ok),
            "real native ability animation must resume to its end")
        self.assertTrue(bool(g._life_dead),
            "native ability coroutine must be dead before the runtime update")
        self.assertTrue(bool(g._life_parent_hidden),
            "native animation must leave radial_ability hidden")
        self.assertEqual(float(g._life_meter_r), 0.0,
            msg="native animation must finish with the meter red channel at 0")
        self.assertTrue(bool(g._life_leaf_hidden_before),
            "both leaves must still be leased hidden before the runtime update")
        self.assertTrue(bool(g._life_e_verify),
            "owned equipment render must certify after the native end")
        self.assertTrue(bool(g._life_e_root_visible),
            "owned equipment root must stay visible after the release")
        self.assertTrue(bool(g._life_active_hidden),
            "ACTIVE row must be hidden once the native ability ends")
        self.assert_released(g._life_end_meter_visible,
            g._life_end_icon_visible, g._life_end_meter_lease,
            g._life_end_icon_lease, "native end")
        self.assertEqual(float(g._life_end_remaining), 11.0,
            msg="native recharge must continue with 11s remaining")
        self.assertEqual(float(g._life_end_charges), 1.0,
            msg="native projectile charges must remain 1 of 2")

    def test_external_leaf_conflict_persists_across_updates(self):
        lua = hacker_lua()
        g = lua.globals()

        lua.execute(ACTIVATE_AND_OBSERVE)

        self.assertTrue(bool(g._post_e_verify),
            "positive activation must certify the owned equipment render")
        self.assert_bound(g._post_meter_visible, g._post_icon_visible,
            g._post_meter_entry_ok, g._post_icon_entry_ok, "activation")
        self.assertFalse(bool(g._post_parent_leased),
            "the native radial_ability parent must never be leased")

        lua.execute(r'''
_G._conflict_parent_before = (_ability_parent:visible() == true)
_ability_meter:set_visible(true)
_R:update(_m, 2.001, .001)

local nv = kyohud.hud.native_visibility
_G._conflict_first_meter_lease = false
_G._conflict_first_icon_lease = false
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then _G._conflict_first_meter_lease = true end
    if e.object == _ability_icon then _G._conflict_first_icon_lease = true end
end
_G._conflict_first_meter_visible = (_ability_meter:visible() == true)
_G._conflict_first_icon_visible = (_ability_icon:visible() == true)
_G._conflict_first_root_visible = (_E._root ~= nil
    and _E._root:visible() == true)
''')

        self.assertTrue(bool(g._conflict_first_meter_visible),
            "external conflict must leave ability_meter visible")
        self.assertTrue(bool(g._conflict_first_icon_visible),
            "external conflict must preserve the ability_icon sibling")
        self.assertFalse(bool(g._conflict_first_meter_lease),
            "external conflict must drop the ability_meter lease")
        self.assertFalse(bool(g._conflict_first_icon_lease),
            "external conflict must drop the ability_icon lease")
        self.assertFalse(bool(g._conflict_first_root_visible),
            "original parent guard must hide the owned equipment root")

        lua.execute(r'''
_R:update(_m, 2.1, .1)

local nv = kyohud.hud.native_visibility
_G._conflict_next_meter_lease = false
_G._conflict_next_icon_lease = false
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then _G._conflict_next_meter_lease = true end
    if e.object == _ability_icon then _G._conflict_next_icon_lease = true end
end
_G._conflict_next_meter_visible = (_ability_meter:visible() == true)
_G._conflict_next_icon_visible = (_ability_icon:visible() == true)
_G._conflict_next_root_visible = (_E._root ~= nil
    and _E._root:visible() == true)
_G._conflict_parent_after = (_ability_parent:visible() == true)
''')

        self.assertTrue(bool(g._conflict_next_meter_visible),
            "ordinary update must keep the conflict's ability_meter visible")
        self.assertTrue(bool(g._conflict_next_icon_visible),
            "ordinary update must keep the ability_icon sibling visible")
        self.assertFalse(bool(g._conflict_next_meter_lease),
            "ordinary update must not re-lease ability_meter on the conflict")
        self.assertFalse(bool(g._conflict_next_icon_lease),
            "ordinary update must not re-lease ability_icon on the conflict")
        self.assertFalse(bool(g._conflict_next_root_visible),
            "ordinary update must keep the owned equipment root hidden")
        self.assertEqual(bool(g._conflict_parent_after),
            bool(g._conflict_parent_before),
            "the native radial_ability parent must be preserved")

    def test_off_on_retained_event_reacquires_until_window_expires(self):
        lua = hacker_lua()
        g = lua.globals()

        lua.execute(r'''
kyohud.settings.enable_equipment = false
_R:refresh_settings(_m)
inventory._jammer_data = {effect = "feedback", t = 1006}
HUDManager.activate_teammate_ability_radial(
    _m, HUDManager.PLAYER_PANEL, 6, nil)

local nv = kyohud.hud.native_visibility
_G._off_meter_entry = false
_G._off_icon_entry = false
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then _G._off_meter_entry = true end
    if e.object == _ability_icon then _G._off_icon_entry = true end
end
_G._off_meter_visible = (_ability_meter:visible() == true)
_G._off_icon_visible = (_ability_icon:visible() == true)
''')

        self.assertFalse(bool(g._off_meter_entry),
            "disabled equipment must not lease ability_meter at activation")
        self.assertFalse(bool(g._off_icon_entry),
            "disabled equipment must not lease ability_icon at activation")
        self.assertTrue(bool(g._off_meter_visible),
            "disabled equipment must leave ability_meter visible")
        self.assertTrue(bool(g._off_icon_visible),
            "disabled equipment must leave ability_icon visible")

        lua.execute(r'''
_game_clock:set_time(1001)
kyohud.settings.enable_equipment = true
_R:refresh_settings(_m)
_R:update(_m, 2.1, .1)

local nv = kyohud.hud.native_visibility
local meter_entry, icon_entry
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_entry = e end
    if e.object == _ability_icon then icon_entry = e end
end

_G._on_row6_visible = (_E._visible_rows and _E._visible_rows[6] == true)
    or false
_G._on_row6_label = _E._rows and _E._rows[6] and _E._rows[6]._label:text()
    or nil
_G._on_row6_value = _E._rows and _E._rows[6] and _E._rows[6]._value:text()
    or nil
_G._on_meter_entry = (meter_entry ~= nil)
_G._on_icon_entry = (icon_entry ~= nil)
_G._on_meter_hidden = (_ability_meter:visible() == false)
_G._on_icon_hidden = (_ability_icon:visible() == false)
_G._on_e_verify = (_E:verify() == true)
''')

        self.assertTrue(bool(g._on_row6_visible),
            "retained ACTIVE event must render row 6 once equipment is enabled")
        self.assertEqual(g._on_row6_label, "ACTIVE")
        self.assertEqual(g._on_row6_value, "5s",
            "retained ACTIVE event must show the 5s remainder")
        self.assertTrue(bool(g._on_meter_entry),
            "re-enabled equipment must lease ability_meter")
        self.assertTrue(bool(g._on_icon_entry),
            "re-enabled equipment must lease ability_icon")
        self.assertTrue(bool(g._on_meter_hidden),
            "re-enabled equipment must hide ability_meter")
        self.assertTrue(bool(g._on_icon_hidden),
            "re-enabled equipment must hide ability_icon")
        self.assertTrue(bool(g._on_e_verify),
            "owned equipment render must certify after re-acquisition")

        lua.execute(r'''
kyohud.settings.enable_equipment = false
_R:refresh_settings(_m)
_R:update(_m, 2.2, .1)

local nv = kyohud.hud.native_visibility
_G._ended_meter_entry = false
_G._ended_icon_entry = false
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then _G._ended_meter_entry = true end
    if e.object == _ability_icon then _G._ended_icon_entry = true end
end
_G._ended_meter_visible = (_ability_meter:visible() == true)
_G._ended_icon_visible = (_ability_icon:visible() == true)
''')

        self.assertFalse(bool(g._ended_meter_entry),
            "disabling equipment must release the ability_meter lease")
        self.assertFalse(bool(g._ended_icon_entry),
            "disabling equipment must release the ability_icon lease")
        self.assertTrue(bool(g._ended_meter_visible),
            "disabling equipment must restore ability_meter exactly visible")
        self.assertTrue(bool(g._ended_icon_visible),
            "disabling equipment must restore ability_icon exactly visible")

        lua.execute(r'''
_game_clock:set_time(1007)
kyohud.settings.enable_equipment = true
_R:refresh_settings(_m)
_R:update(_m, 2.3, .1)

local nv = kyohud.hud.native_visibility
_G._expired_meter_entry = false
_G._expired_icon_entry = false
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then _G._expired_meter_entry = true end
    if e.object == _ability_icon then _G._expired_icon_entry = true end
end
''')

        self.assertFalse(bool(g._expired_meter_entry),
            "expired retained event must not re-acquire ability_meter")
        self.assertFalse(bool(g._expired_icon_entry),
            "expired retained event must not re-acquire ability_icon")

    def test_source_failclosed_releases_activation_leases(self):
        cases = [
            ("jammer_cleared", "inventory._jammer_data = nil", False),
            ("jammer_replaced",
             'inventory._jammer_data = {effect = "feedback", t = 1006}',
             False),
            ("grenades_cloned",
             "local s = managers.player._global.synced_grenades; "
             "local c = {}; for k, v in pairs(s or {}) do c[k] = v end; "
             "managers.player._global.synced_grenades = c", False),
            ("timer_frozen",
             "TimerManager.game = function() return "
             "{time = function() return 1000 end} end", False),
            ("meter_nan",
             "_ability_meter:set_color(Color(1, 0/0, 1, 1))", False),
            ("clock_backward", None, True),
        ]
        for name, mutation, backward in cases:
            with self.subTest(case=name):
                lua = hacker_lua()
                g = lua.globals()
                lua.execute(ACTIVATE_AND_OBSERVE)
                self.assertTrue(bool(g._post_e_verify),
                    "activation must certify the owned equipment render")
                self.assert_bound(g._post_meter_visible, g._post_icon_visible,
                    g._post_meter_entry_ok, g._post_icon_entry_ok, "activation")
                if backward:
                    lua.execute(r'''
_game_clock:set_time(1001)
_R:update(_m, 2.06, .06)
local nv = kyohud.hud.native_visibility
local meter_lease, icon_lease = false, false
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_lease = true end
    if e.object == _ability_icon then icon_lease = true end
end
_G._back_meter_lease = meter_lease
_G._back_icon_lease = icon_lease
_game_clock:set_time(1000.5)
_R:update(_m, 2.061, .001)
''')
                    self.assertTrue(bool(g._back_meter_lease),
                        "first backward-clock update must keep the meter lease")
                    self.assertTrue(bool(g._back_icon_lease),
                        "first backward-clock update must keep the icon lease")
                else:
                    lua.execute(mutation)
                    lua.execute(r'''
_R:update(_m, 2.001, .001)
''')
                lua.execute(r'''
local nv = kyohud.hud.native_visibility
local meter_lease, icon_lease = false, false
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_lease = true end
    if e.object == _ability_icon then icon_lease = true end
end
_G._fail_meter_visible = (_ability_meter:visible() == true)
_G._fail_icon_visible = (_ability_icon:visible() == true)
_G._fail_meter_lease = meter_lease
_G._fail_icon_lease = icon_lease
_G._fail_root_visible = (_E._root ~= nil and _E._root:visible() == true)
''')
                self.assertTrue(bool(g._fail_meter_visible),
                    f"{name}: lost source must restore ability_meter visible")
                self.assertTrue(bool(g._fail_icon_visible),
                    f"{name}: lost source must restore ability_icon visible")
                self.assertFalse(bool(g._fail_meter_lease),
                    f"{name}: lost source must drop the ability_meter lease")
                self.assertFalse(bool(g._fail_icon_lease),
                    f"{name}: lost source must drop the ability_icon lease")
                self.assertFalse(bool(g._fail_root_visible),
                    f"{name}: overlapping native parent must hide the owned root")

    def test_two_charge_recovery_keeps_cooldown_active(self):
        lua = hacker_lua()
        g = lua.globals()

        lua.execute(ACTIVATE_AND_OBSERVE)

        self.assertTrue(bool(g._post_e_verify),
            "positive activation must certify the owned equipment render")
        self.assert_bound(g._post_meter_visible, g._post_icon_visible,
            g._post_meter_entry_ok, g._post_icon_entry_ok, "activation")
        self.assertEqual(float(g._post_charges), 1.0,
            "activation must start from one remaining charge")
        self.assertEqual(float(g._post_cooldown), 17.0,
            "activation must keep the 17s native recharge")
        self.assertEqual(g._post_row6_value, "6s",
            "activation must render the 6s ACTIVE row")

        lua.execute(r'''
_game_clock:set_time(1006)
local anim = _ability_parent._ky_animation
_G._life2_first_anim = anim
_G._life2_first_suspended = (anim ~= nil
    and coroutine.status(anim) == "suspended")
_G._life2_first_resume_ok = false
if _life2_first_suspended then
    _G._life2_first_resume_ok = (coroutine.resume(anim, 6) == true)
end
inventory._jammer_data = nil
_R:update(_m, 3.0, .1)

local snap = _E:get_snapshot()
_G._life2_first_dead = (anim ~= nil and coroutine.status(anim) == "dead")
_G._life2_first_active_hidden = not (_E._visible_rows
    and _E._visible_rows[6] == true)
_G._life2_first_recharge = snap.cooldown and snap.cooldown.remaining
_G._life2_first_e_verify = (_E:verify() == true)
''')

        self.assertTrue(bool(g._life2_first_suspended),
            "first native ability coroutine must start suspended")
        self.assertTrue(bool(g._life2_first_resume_ok),
            "first native ability coroutine must resume to its end")
        self.assertTrue(bool(g._life2_first_dead),
            "first native ability coroutine must be dead")
        self.assertTrue(bool(g._life2_first_active_hidden),
            "ACTIVE row must hide after the first native end")
        self.assertTrue(bool(g._life2_first_e_verify),
            "equipment render must certify after the first release")
        self.assertEqual(float(g._life2_first_recharge), 11.0,
            msg="existing recharge must continue at 11s after the first end")

        lua.execute(r'''
managers.player:_native_set_grenades("pocket_ecm_jammer", 0, 2)
dispatch(HUDManager, "set_teammate_grenades_amount",
    managers.hud, HUDManager.PLAYER_PANEL, 0)

_G._life2_spend_recharge = managers.player:get_timer_remaining(
    "replenish_grenades")
inventory._jammer_data = {effect = "feedback", t = 1012}
_G._life2_second_emit = HUDManager.activate_teammate_ability_radial(
    _m, HUDManager.PLAYER_PANEL, 6, nil)
local anim = _ability_parent._ky_animation
_G._life2_second_anim = anim
_G._life2_second_suspended = (anim ~= nil
    and coroutine.status(anim) == "suspended")

local nv = kyohud.hud.native_visibility
local meter_lease, icon_lease = false, false
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_lease = true end
    if e.object == _ability_icon then icon_lease = true end
end
local snap = _E:get_snapshot()
_G._life2_second_source = (_E:get_hacker_activity_source() ~= nil)
_G._life2_second_meter_hidden = (_ability_meter:visible() == false)
_G._life2_second_icon_hidden = (_ability_icon:visible() == false)
_G._life2_second_meter_lease = meter_lease
_G._life2_second_icon_lease = icon_lease
_G._life2_second_e_verify = (_E:verify() == true)
_G._life2_second_active_value = _E._rows[6]._value:text()
_G._life2_second_recharge = snap.cooldown and snap.cooldown.remaining
_G._life2_second_charges = snap.projectile and snap.projectile.charges
    and snap.projectile.charges.raw
''')

        self.assertEqual(float(g._life2_spend_recharge), 11.0,
            msg="spending the second charge must not touch the native timer")
        self.assertTrue(bool(g._life2_second_suspended),
            "second activation must start a suspended native coroutine")
        self.assertTrue(bool(g._life2_second_source),
            "second activation must retain its existing fresh source")
        self.assert_bound(g._life2_second_meter_hidden,
            g._life2_second_icon_hidden, g._life2_second_meter_lease,
            g._life2_second_icon_lease, "second activation")
        self.assertTrue(bool(g._life2_second_e_verify),
            "equipment render must certify on the second activation")
        self.assertEqual(g._life2_second_active_value, "6s",
            "second ACTIVE row must show the 6s native duration")
        self.assertEqual(float(g._life2_second_recharge), 11.0,
            msg="the untouched native timer must stay at 11s")
        self.assertEqual(float(g._life2_second_charges), 0.0,
            msg="second activation must read zero remaining charges")

        lua.execute(r'''
_game_clock:set_time(1012)
local anim = _life2_second_anim
_G._life2_second_same_co = (anim ~= nil
    and _ability_parent._ky_animation == anim)
_G._life2_second_resume_ok = false
if anim ~= nil and coroutine.status(anim) == "suspended" then
    _G._life2_second_resume_ok = (coroutine.resume(anim, 6) == true)
end
_G._life2_second_dead = (anim ~= nil and coroutine.status(anim) == "dead")
inventory._jammer_data = nil
_R:update(_m, 3.2, .1)

local nv = kyohud.hud.native_visibility
local meter_lease, icon_lease = false, false
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_lease = true end
    if e.object == _ability_icon then icon_lease = true end
end
_G._life2_end_meter_visible = (_ability_meter:visible() == true)
_G._life2_end_icon_visible = (_ability_icon:visible() == true)
_G._life2_end_meter_lease = meter_lease
_G._life2_end_icon_lease = icon_lease
_G._life2_end_active_hidden = not (_E._visible_rows
    and _E._visible_rows[6] == true)
''')

        self.assertTrue(bool(g._life2_second_same_co),
            "second native resume must target the same activation coroutine")
        self.assertTrue(bool(g._life2_second_resume_ok),
            "second native activation must resume to its end")
        self.assertTrue(bool(g._life2_second_dead),
            "second native activation must be dead before the release")
        self.assert_released(g._life2_end_meter_visible,
            g._life2_end_icon_visible, g._life2_end_meter_lease,
            g._life2_end_icon_lease, "second native end")
        self.assertTrue(bool(g._life2_end_active_hidden),
            "ACTIVE row must hide after the second native end")

        lua.execute(r'''
_game_clock:set_time(1017)
managers.player:_native_set_grenades("pocket_ecm_jammer", 1, 2)
managers.player:_native_set_replenish_timer(1117)
dispatch(HUDManager, "set_teammate_grenade_cooldown", managers.hud,
    HUDManager.PLAYER_PANEL, {duration = 100, end_time = 1117})
dispatch(HUDManager, "set_teammate_grenades_amount",
    managers.hud, HUDManager.PLAYER_PANEL, 1)
_R:update(_m, 3.4, .1)

local snap = _E:get_snapshot()
_G._life2_recovered_known = (snap.cooldown
    and snap.cooldown.known == true)
_G._life2_recovered_active = (snap.cooldown
    and snap.cooldown.active == true)
_G._life2_recovered_remaining = snap.cooldown and snap.cooldown.remaining
_G._life2_recovered_duration = snap.cooldown and snap.cooldown.duration
_G._life2_recovered_integrated = (snap.cooldown
    and snap.cooldown.integrated == true)
_G._life2_recovered_charges = snap.projectile and snap.projectile.charges
    and snap.projectile.charges.raw
_G._life2_recovered_active_hidden = not (_E._visible_rows
    and _E._visible_rows[6] == true)
_G._life2_recovered_root_visible = (_E._root ~= nil
    and _E._root:visible() == true)
_G._life2_recovered_e_verify = (_E:verify() == true)
''')

        self.assertTrue(bool(g._life2_recovered_known),
            "recovered cooldown must stay a known native source")
        self.assertTrue(bool(g._life2_recovered_active),
            "one recovered charge must not end the active native recharge")
        self.assertEqual(float(g._life2_recovered_remaining), 100.0,
            msg="recovered native recharge must show 100s remaining")
        self.assertEqual(float(g._life2_recovered_duration), 100.0,
            msg="accepted cooldown event must provide the 100s duration")
        self.assertTrue(bool(g._life2_recovered_integrated),
            "recovered cooldown must integrate into the grenade cell")
        self.assertEqual(float(g._life2_recovered_charges), 1.0,
            msg="recovery event must restore exactly one charge")
        self.assertTrue(bool(g._life2_recovered_active_hidden),
            "ACTIVE row must stay hidden through the recovery")
        self.assertTrue(bool(g._life2_recovered_root_visible),
            "owned equipment root must stay visible after recovery")
        self.assertTrue(bool(g._life2_recovered_e_verify),
            "equipment render must certify after recovery")


if __name__ == "__main__":
    unittest.main()
