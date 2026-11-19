"""Lot 6 RED: the approved Kingpin terminal contract.

After a real positive publication near the expiry, the temporary effect becomes
inactive while the native radial parent is still visible. At that point the
owned player/equipment groups must stay visible and certified, the two native
ability leaves must stay held hidden by the existing lease, the ACTIVE row must
be absent, and the saved primitives must be reused. A later native zero
publication must restore the two leaves, hide the parent and keep the same owned
primitives certified with no remaining ability lease.
"""
import unittest

from test_hud_kingpin_active import KINGPIN_ACTIVATE, kingpin_lua
from test_hud_kingpin_terminal_player import SETUP

# Safety characterization, not a fabricated RED: the positive terminal contract
# is already independently green. This file adds negative dependency-loss cases.



NEAR_TERMINAL = r'''
_app_now = 1005.99
_m:set_player_ability_radial({current = .000560760498, total = 6})

local nv = kyohud.hud.native_visibility
local meter_entry, icon_entry, parent_entry
local ability_entries = 0
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_entry = e end
    if e.object == _ability_icon then icon_entry = e end
    if e.object == _ability_parent then parent_entry = e end
    if e.object == _ability_meter or e.object == _ability_icon then
        ability_entries = ability_entries + 1
    end
end

_G._near_p_visible = (_P._root:visible() == true)
_G._near_p_verify = (_P:verify() == true)
_G._near_e_visible = (_E._root ~= nil and _E._root:visible() == true)
_G._near_e_verify = (_E:verify() == true)
_G._near_native_parent_visible = (_ability_parent:visible() == true)
_G._near_meter_hidden = (_ability_meter:visible() == false)
_G._near_icon_hidden = (_ability_icon:visible() == false)
_G._near_row6_visible = (_E._visible_rows and _E._visible_rows[6] == true) or false
_G._near_ability_entries = ability_entries
_G._near_meter_entry_ok = meter_entry ~= nil
    and meter_entry.property == "visible"
    and meter_entry.old_value == true
    and meter_entry.applied_value == false
_G._near_icon_entry_ok = icon_entry ~= nil
    and icon_entry.property == "visible"
    and icon_entry.old_value == true
    and icon_entry.applied_value == false
_G._near_owner_equal = meter_entry ~= nil and icon_entry ~= nil
    and meter_entry.owner ~= nil and meter_entry.owner == icon_entry.owner
    and meter_entry.generation == icon_entry.generation
_G._near_parent_entry = (parent_entry ~= nil)

_G._p_root = _P._root
_G._p_gauge = _P._gauge
_G._e_root = _E._root
'''

EXPIRE = r'''
_app_now = 1006.01
_R:update(_m, 3.21, 0.01)

local nv = kyohud.hud.native_visibility
local meter_entry, icon_entry, parent_entry
local ability_entries = 0
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_entry = e end
    if e.object == _ability_icon then icon_entry = e end
    if e.object == _ability_parent then parent_entry = e end
    if e.object == _ability_meter or e.object == _ability_icon then
        ability_entries = ability_entries + 1
    end
end

_G._expiry_effect_inactive = (managers.player:has_activate_temporary_upgrade(
    "temporary", "chico_injector") == false)
_G._expiry_p_visible = (_P._root:visible() == true)
_G._expiry_p_verify = (_P:verify() == true)
_G._expiry_e_visible = (_E._root ~= nil and _E._root:visible() == true)
_G._expiry_e_verify = (_E:verify() == true)
_G._expiry_native_parent_visible = (_ability_parent:visible() == true)
_G._expiry_meter_hidden = (_ability_meter:visible() == false)
_G._expiry_icon_hidden = (_ability_icon:visible() == false)
_G._expiry_row6_visible = (_E._visible_rows and _E._visible_rows[6] == true) or false
_G._expiry_row6_root_visible = (_E._rows and _E._rows[6]
    and _E._rows[6]._root:visible() == true) or false
_G._expiry_ability_entries = ability_entries
_G._expiry_meter_entry_ok = meter_entry ~= nil
    and meter_entry.property == "visible"
    and meter_entry.old_value == true
    and meter_entry.applied_value == false
_G._expiry_icon_entry_ok = icon_entry ~= nil
    and icon_entry.property == "visible"
    and icon_entry.old_value == true
    and icon_entry.applied_value == false
_G._expiry_owner_equal = meter_entry ~= nil and icon_entry ~= nil
    and meter_entry.owner ~= nil and meter_entry.owner == icon_entry.owner
    and meter_entry.generation == icon_entry.generation
_G._expiry_parent_entry = (parent_entry ~= nil)
_G._expiry_same_p_root = (_P._root == _G._p_root)
_G._expiry_same_p_gauge = (_P._gauge == _G._p_gauge)
_G._expiry_same_e_root = (_E._root == _G._e_root)
'''

HOLD_TERMINAL = r'''
local nv = kyohud.hud.native_visibility
local meter_entry, icon_entry
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_entry = e end
    if e.object == _ability_icon then icon_entry = e end
end
_G._hold_meter_entry = meter_entry
_G._hold_icon_entry = icon_entry
_G._hold_generation = meter_entry and meter_entry.generation or nil
_G._hold_owner = meter_entry and meter_entry.owner or nil
local before_binding = kyohud.hud.runtime._hacker_active_binding
_G._hold_binding = before_binding
_G._hold_before_terminal = type(before_binding) == "table"
    and before_binding.terminal == true
_G._hold_before_lease_gen = type(before_binding) == "table"
    and before_binding.lease_gen or nil
local group = kyohud.hud.runtime._h5_groups
    and kyohud.hud.runtime._h5_groups.local_p_hacker_active
_G._hold_before_group_gen = group and group.generation or nil

_app_now = 1006.02
_R:update(_m, 3.22, 0.01)

local after_nv = kyohud.hud.native_visibility
local after_meter, after_icon, after_parent
local ability_entries = 0
for _, e in ipairs(after_nv._entries) do
    if e.object == _ability_meter then after_meter = e end
    if e.object == _ability_icon then after_icon = e end
    if e.object == _ability_parent then after_parent = e end
    if e.object == _ability_meter or e.object == _ability_icon then
        ability_entries = ability_entries + 1
    end
end
local after_binding = kyohud.hud.runtime._hacker_active_binding
local after_group = kyohud.hud.runtime._h5_groups
    and kyohud.hud.runtime._h5_groups.local_p_hacker_active

_G._hold_p_visible = (_P._root:visible() == true)
_G._hold_p_verify = (_P:verify() == true)
_G._hold_e_visible = (_E._root ~= nil and _E._root:visible() == true)
_G._hold_e_verify = (_E:verify() == true)
_G._hold_native_parent_visible = (_ability_parent:visible() == true)
_G._hold_meter_hidden = (_ability_meter:visible() == false)
_G._hold_icon_hidden = (_ability_icon:visible() == false)
_G._hold_row6_visible = (_E._visible_rows and _E._visible_rows[6] == true)
    or false
_G._hold_ability_entries = ability_entries
_G._hold_parent_entry = (after_parent ~= nil)
_G._hold_terminal_qualified = _G._hold_before_terminal
    and after_binding == before_binding
    and type(after_binding) == "table"
    and after_binding.terminal == true and after_binding.leased == true
_G._hold_lease_unchanged = after_meter == _G._hold_meter_entry
    and after_icon == _G._hold_icon_entry
    and after_meter ~= nil and after_icon ~= nil
    and after_meter.generation == _G._hold_generation
    and after_icon.generation == _G._hold_generation
    and after_meter.owner == _G._hold_owner
    and after_icon.owner == _G._hold_owner
_G._hold_lease_gen_unchanged = type(after_binding) == "table"
    and after_binding.lease_gen == _G._hold_before_lease_gen
_G._hold_group_gen_unchanged = after_group ~= nil
    and after_group.generation == _G._hold_before_group_gen
_G._hold_same_p_root = (_P._root == _G._p_root)
_G._hold_same_p_gauge = (_P._gauge == _G._p_gauge)
_G._hold_same_e_root = (_E._root == _G._e_root)
'''

TERMINAL = r'''
_m:set_player_ability_radial({current = 0, total = 1})

local nv = kyohud.hud.native_visibility
local ability_entries = 0
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter or e.object == _ability_icon
        or e.object == _ability_parent then
        ability_entries = ability_entries + 1
    end
end

_G._final_p_visible = (_P._root:visible() == true)
_G._final_p_verify = (_P:verify() == true)
_G._final_e_visible = (_E._root ~= nil and _E._root:visible() == true)
_G._final_e_verify = (_E:verify() == true)
_G._final_native_parent_hidden = (_ability_parent:visible() == false)
_G._final_leaves_visible = (_ability_meter:visible() == true)
    and (_ability_icon:visible() == true)
_G._final_row6_visible = (_E._visible_rows and _E._visible_rows[6] == true) or false
_G._final_ability_entries = ability_entries
_G._final_same_p_root = (_P._root == _G._p_root)
_G._final_same_p_gauge = (_P._gauge == _G._p_gauge)
_G._final_same_e_root = (_E._root == _G._e_root)
'''

TERMINAL_BASELINE = r'''
local nv = kyohud.hud.native_visibility
local meter_entry, icon_entry, parent_entry
local ability_entries = 0
for _, e in ipairs(nv._entries) do
    if e.object == _ability_meter then meter_entry = e end
    if e.object == _ability_icon then icon_entry = e end
    if e.object == _ability_parent then parent_entry = e end
    if e.object == _ability_meter or e.object == _ability_icon then
        ability_entries = ability_entries + 1
    end
end
_G._t_meter = _ability_meter
_G._t_icon = _ability_icon
_G._t_parent = _ability_parent
_G._t_meter_entry = meter_entry
_G._t_icon_entry = icon_entry
_G._t_owner = meter_entry and meter_entry.owner or nil
_G._t_generation = meter_entry and meter_entry.generation or nil
_G._t_parent_visible = (_ability_parent:visible() == true)
_G._t_parent_alpha = _ability_parent:alpha()
_G._t_p_root = _P._root
_G._t_p_gauge = _P._gauge
_G._t_e_root = _E._root
_G._t_ability_entries = ability_entries
local binding = kyohud.hud.runtime._hacker_active_binding
_G._t_binding_terminal = type(binding) == "table" and binding.terminal == true
_G._t_binding_leased = type(binding) == "table" and binding.leased == true

function _G._kyo_terminal_state(prefix)
    local nv = kyohud.hud.native_visibility
    local meter_entry, icon_entry, parent_entry
    local ability_entries = 0
    for _, e in ipairs(nv._entries) do
        if e.object == _ability_meter then meter_entry = e end
        if e.object == _ability_icon then icon_entry = e end
        if e.object == _ability_parent then parent_entry = e end
        if e.object == _ability_meter or e.object == _ability_icon then
            ability_entries = ability_entries + 1
        end
    end
    local P = kyohud.hud.player
    local E = kyohud.hud.equipment
    local binding = kyohud.hud.runtime._hacker_active_binding
    _G[prefix .. "_meter_visible"] = (_ability_meter:visible() == true)
    _G[prefix .. "_icon_visible"] = (_ability_icon:visible() == true)
    _G[prefix .. "_ability_entries"] = ability_entries
    _G[prefix .. "_parent_entry"] = (parent_entry ~= nil)
    _G[prefix .. "_parent_visible"] = (_ability_parent:visible() == true)
    _G[prefix .. "_parent_alpha"] = _ability_parent:alpha()
    _G[prefix .. "_p_visible"] = (P._root:visible() == true)
    _G[prefix .. "_p_verify"] = (P:verify() == true)
    _G[prefix .. "_e_visible"] = (E._root ~= nil and E._root:visible() == true)
    _G[prefix .. "_e_verify"] = (E:verify() == true)
    _G[prefix .. "_row6_visible"] = (E._visible_rows
        and E._visible_rows[6] == true) or false
    _G[prefix .. "_row6_root_visible"] = (E._rows and E._rows[6]
        and E._rows[6]._root:visible() == true) or false
    _G[prefix .. "_p_root_same"] = (P._root == _G._t_p_root)
    _G[prefix .. "_p_gauge_same"] = (P._gauge == _G._t_p_gauge)
    _G[prefix .. "_e_root_same"] = (E._root == _G._t_e_root)
    _G[prefix .. "_leaf_identity_same"] = (_ability_meter == _G._t_meter
        and _ability_icon == _G._t_icon)
    _G[prefix .. "_binding_terminal"] = type(binding) == "table"
        and binding.terminal == true
    _G[prefix .. "_binding_leased"] = type(binding) == "table"
        and binding.leased == true
end
'''

# Safety characterization of already-green fail-closed behavior, not a
# fabricated RED. Each case loses exactly one terminal dependency.
TERMINAL_NEGATIVE_CASES = [
    {
        "name": "same_value_replacement_record",
        "loss": r'''
local category = managers.player._temporary_upgrades.temporary
_G._replacement_record = {expire_time = 1006}
category.chico_injector = _G._replacement_record
''',
        "aftermath": r'''
_G._replacement_still = (managers.player._temporary_upgrades.temporary
    .chico_injector == _G._replacement_record)
''',
    },
    {
        "name": "application_backward",
        "app_before": "1005.98",
        "loss": "",
        "restore": "_app_now = 1006.02",
    },
    {
        "name": "owned_row3_text_corruption",
        "loss": r'''
local value = _E._rows[3]._value
local saved_text = value:text()
_G._saved_row3_text = saved_text
value:set_text("BROKEN")
''',
        "restore": "value:set_text(saved_text)",
        "aftermath": r'''
_m:set_player_ability_radial({current = 0, total = 1})
_app_now = 1006.03
_R:update(_m, 3.27, 0.05)
_G._text_recovered_p_visible = (_P._root:visible() == true)
_G._text_recovered_p_verify = (_P:verify() == true)
_G._text_recovered_e_visible = (_E._root ~= nil and _E._root:visible() == true)
_G._text_recovered_e_verify = (_E:verify() == true)
_G._text_recovered_same_p_root = (_P._root == _G._t_p_root)
_G._text_recovered_same_p_gauge = (_P._gauge == _G._t_p_gauge)
_G._text_recovered_same_e_root = (_E._root == _G._t_e_root)
_G._text_recovered_row6 = (_E._visible_rows
    and _E._visible_rows[6] == true) or false
_G._text_restored = (_E._rows[3]._value:text() == _G._saved_row3_text)
''',
    },
    {
        "name": "native_icon_foreign_visible",
        "loss": r'''
_ability_icon:set_visible(true)
_G._foreign_icon_value = _ability_icon:visible()
''',
        "aftermath": r'''
_G._icon_value_preserved = (_ability_icon:visible() == _G._foreign_icon_value)
''',
    },
    {
        "name": "foreign_extra_child",
        "loss": r'''
local extra = _ability_parent:rect({name = "ky_test_foreign_rect"})
extra:set_shape(0, 0, 3, 3)
extra:set_visible(true)
_G._foreign_child = extra
''',
        "aftermath": r'''
_G._foreign_child_alive = (alive(_G._foreign_child) == true)
_G._foreign_child_parent = (_G._foreign_child:parent() == _ability_parent)
_G._foreign_child_visible = (_G._foreign_child:visible() == true)
_G._foreign_child_shape = (_G._foreign_child:x() == 0
    and _G._foreign_child:y() == 0
    and _G._foreign_child:w() == 3
    and _G._foreign_child:h() == 3)
''',
    },
    {
        "name": "wrong_player_ancestry",
        "loss": r'''
local player = _m._teammate_panels[HUDManager.PLAYER_PANEL]
    ._panel:child("player")
_G._wrong_ancestry_player = player
function player.parent() return _R._parent_panel end
''',
        "aftermath": r'''
_G._wrong_ancestry_lookup = (_m._teammate_panels[HUDManager.PLAYER_PANEL]
    ._panel:child("player") == _G._wrong_ancestry_player)
_G._wrong_ancestry_reachable = (_G._wrong_ancestry_player:parent()
    == _R._parent_panel)
''',
    },
    {
        "name": "replaced_equipment_verifier",
        "loss": r'''
function _E.verify() return true end
_E._rows[3]._value:set_text("BROKEN")
''',
        "aftermath": r'''
_G._replaced_verify_returns_true = (_E:verify() == true)
_G._replaced_row3_broken = (_E._rows[3]._value:text() == "BROKEN")
''',
    },
]


def _negative_script(case):
    return (
        case.get("loss", "") + "\n"
        + "_app_now = " + case.get("app_before", "1006.02") + "\n"
        + "_R:update(_m, 3.22, 0.01)\n"
        + '_kyo_terminal_state("_fail")\n'
        + case.get("restore", "") + "\n"
        + "_R:update(_m, 3.23, 0.01)\n"
        + '_kyo_terminal_state("_repeat")\n'
        + case.get("aftermath", "")
    )


class KingpinTerminalContractTests(unittest.TestCase):
    def test_inactive_native_parent_keeps_owned_panels_and_held_leaves(self):
        lua = kingpin_lua()
        g = lua.globals()

        lua.execute(SETUP)
        self.assertTrue(bool(g._pre_p_visible),
            "precondition: owned player panel must start visible")
        self.assertTrue(bool(g._pre_p_verify),
            "precondition: owned player panel must start certified")

        lua.execute(KINGPIN_ACTIVATE)
        lua.execute(NEAR_TERMINAL)

        self.assertTrue(bool(g._near_p_visible),
            "precondition: near-terminal positive publication must keep P visible")
        self.assertTrue(bool(g._near_p_verify),
            "precondition: near-terminal positive publication must keep P certified")
        self.assertTrue(bool(g._near_e_visible),
            "precondition: near-terminal positive publication must keep E visible")
        self.assertTrue(bool(g._near_e_verify),
            "precondition: near-terminal positive publication must keep E certified")
        self.assertTrue(bool(g._near_native_parent_visible),
            "precondition: positive native radial must keep its parent visible")
        self.assertTrue(bool(g._near_meter_hidden),
            "precondition: positive publication must hold ability_meter hidden")
        self.assertTrue(bool(g._near_icon_hidden),
            "precondition: positive publication must hold ability_icon hidden")
        self.assertTrue(bool(g._near_row6_visible),
            "precondition: positive publication must render ACTIVE row 6")
        self.assertEqual(int(g._near_ability_entries), 2,
            "precondition: exactly the two ability leaves are leased")
        self.assertTrue(bool(g._near_meter_entry_ok),
            "precondition: ability_meter lease must be visible=false")
        self.assertTrue(bool(g._near_icon_entry_ok),
            "precondition: ability_icon lease must be visible=false")
        self.assertTrue(bool(g._near_owner_equal),
            "precondition: both leaves share one lease owner/generation")
        self.assertFalse(bool(g._near_parent_entry),
            "precondition: native radial_ability parent must never be leased")

        lua.execute(EXPIRE)

        self.assertTrue(bool(g._expiry_effect_inactive),
            "real temporary effect must be inactive after its expiry")
        self.assertTrue(bool(g._expiry_native_parent_visible),
            "inactive effect must leave the native radial parent visible")
        self.assertTrue(bool(g._expiry_p_visible),
            "RED: inactive native parent must keep the player panel visible")
        self.assertTrue(bool(g._expiry_p_verify),
            "RED: inactive native parent must keep the player panel certified")
        self.assertTrue(bool(g._expiry_e_visible),
            "RED: inactive native parent must keep the equipment panel visible")
        self.assertTrue(bool(g._expiry_e_verify),
            "RED: inactive native parent must keep the equipment panel certified")
        self.assertTrue(bool(g._expiry_meter_hidden),
            "RED: ability_meter must remain held hidden while parent is visible")
        self.assertTrue(bool(g._expiry_icon_hidden),
            "RED: ability_icon must remain held hidden while parent is visible")
        self.assertFalse(bool(g._expiry_row6_visible),
            "RED: inactive effect must not keep an artificial ACTIVE row")
        self.assertFalse(bool(g._expiry_row6_root_visible),
            "RED: the ACTIVE row primitive must be visually absent")
        self.assertEqual(int(g._expiry_ability_entries), 2,
            "RED: both ability leaves must remain the only leased ability objects")
        self.assertTrue(bool(g._expiry_meter_entry_ok),
            "RED: ability_meter must keep its visible=false native lease")
        self.assertTrue(bool(g._expiry_icon_entry_ok),
            "RED: ability_icon must keep its visible=false native lease")
        self.assertTrue(bool(g._expiry_owner_equal),
            "RED: both leaves must keep one lease owner/generation")
        self.assertFalse(bool(g._expiry_parent_entry),
            "native radial_ability parent must never acquire a lease entry")
        self.assertTrue(bool(g._expiry_same_p_root),
            "player panel root identity must be preserved")
        self.assertTrue(bool(g._expiry_same_p_gauge),
            "player panel gauge identity must be preserved")
        self.assertTrue(bool(g._expiry_same_e_root),
            "equipment panel root identity must be preserved")

        lua.execute(HOLD_TERMINAL)

        self.assertTrue(bool(g._hold_before_terminal),
            "precondition: expiry must have established the terminal hold")
        self.assertTrue(bool(g._hold_terminal_qualified),
            "throttled terminal update must stay qualified without reacquiring")
        self.assertTrue(bool(g._hold_lease_unchanged),
            "throttled terminal update must keep the same two lease identities")
        self.assertTrue(bool(g._hold_lease_gen_unchanged),
            "throttled terminal update must keep the same lease generation")
        self.assertTrue(bool(g._hold_group_gen_unchanged),
            "throttled terminal update must keep the same group generation")
        self.assertTrue(bool(g._hold_p_visible),
            "throttled terminal update must keep the player panel visible")
        self.assertTrue(bool(g._hold_p_verify),
            "throttled terminal update must keep the player panel certified")
        self.assertTrue(bool(g._hold_e_visible),
            "throttled terminal update must keep the equipment panel visible")
        self.assertTrue(bool(g._hold_e_verify),
            "throttled terminal update must keep the equipment panel certified")
        self.assertTrue(bool(g._hold_native_parent_visible),
            "throttled terminal update must keep the native parent visible")
        self.assertTrue(bool(g._hold_meter_hidden),
            "throttled terminal update must keep ability_meter held")
        self.assertTrue(bool(g._hold_icon_hidden),
            "throttled terminal update must keep ability_icon held")
        self.assertFalse(bool(g._hold_row6_visible),
            "throttled terminal update must not fabricate an ACTIVE row")
        self.assertEqual(int(g._hold_ability_entries), 2,
            "throttled terminal update must keep exactly the two held leaves")
        self.assertFalse(bool(g._hold_parent_entry),
            "throttled terminal update must never lease the native parent")
        self.assertTrue(bool(g._hold_same_p_root),
            "throttled terminal update must reuse the player panel root")
        self.assertTrue(bool(g._hold_same_p_gauge),
            "throttled terminal update must reuse the player panel gauge")
        self.assertTrue(bool(g._hold_same_e_root),
            "throttled terminal update must reuse the equipment panel root")

        lua.execute(TERMINAL)

        self.assertTrue(bool(g._final_native_parent_hidden),
            "native zero publication must hide the radial parent")
        self.assertTrue(bool(g._final_leaves_visible),
            "native zero publication must restore both ability leaves")
        self.assertFalse(bool(g._final_row6_visible),
            "terminal zero must not render an artificial ACTIVE row")
        self.assertTrue(bool(g._final_p_visible),
            "terminal zero must keep the player panel visible")
        self.assertTrue(bool(g._final_p_verify),
            "terminal zero must keep the player panel certified")
        self.assertTrue(bool(g._final_e_visible),
            "terminal zero must keep the equipment panel visible")
        self.assertTrue(bool(g._final_e_verify),
            "terminal zero must keep the equipment panel certified")
        self.assertTrue(bool(g._final_same_p_root),
            "terminal zero must reuse the player panel root")
        self.assertTrue(bool(g._final_same_p_gauge),
            "terminal zero must reuse the player panel gauge")
        self.assertTrue(bool(g._final_same_e_root),
            "terminal zero must reuse the equipment panel root")
        self.assertEqual(int(g._final_ability_entries), 0,
            "terminal zero must leave no ability leaf/parent lease entry; "
            "unrelated leases remain permitted")

    def test_terminal_dependency_loss_fails_closed(self):
        """Already-green safety characterization: one terminal dependency is
        lost at a throttled update, then the unchanged loss is repeated.
        """
        def assert_failed_closed(g, case):
            self.assertTrue(bool(g._fail_meter_visible),
                f"{case}: released ability_meter must be visible again")
            self.assertTrue(bool(g._fail_icon_visible),
                f"{case}: released ability_icon must be visible again")
            self.assertEqual(int(g._fail_ability_entries), 0,
                f"{case}: no ability leaf lease entry may remain")
            self.assertFalse(bool(g._fail_parent_entry),
                f"{case}: native parent must never be leased")
            self.assertTrue(bool(g._fail_parent_visible),
                f"{case}: native parent visibility must stay untouched")
            self.assertAlmostEqual(float(g._fail_parent_alpha),
                float(g._t_parent_alpha), places=5,
                msg=f"{case}: native parent alpha must stay untouched")
            self.assertFalse(bool(g._fail_row6_visible),
                f"{case}: no ACTIVE visible row may be fabricated")
            self.assertFalse(bool(g._fail_row6_root_visible),
                f"{case}: the ACTIVE row primitive must stay absent")
            self.assertFalse(bool(g._fail_binding_terminal),
                f"{case}: terminal hold must not survive the dependency loss")
            self.assertFalse(bool(g._fail_binding_leased),
                f"{case}: terminal lease must not survive the dependency loss")
            self.assertFalse(bool(g._fail_e_visible),
                f"{case}: equipment must hide where the native overlap persists")
            self.assertFalse(bool(g._fail_p_visible),
                f"{case}: player must hide where the native overlap persists")
            self.assertTrue(bool(g._fail_p_root_same),
                f"{case}: player root identity must be preserved")
            self.assertTrue(bool(g._fail_p_gauge_same),
                f"{case}: player gauge identity must be preserved")
            self.assertTrue(bool(g._fail_e_root_same),
                f"{case}: equipment root identity must be preserved")
            self.assertTrue(bool(g._fail_leaf_identity_same),
                f"{case}: the exact native leaves must be preserved")

        def assert_no_reacquisition(g, case):
            self.assertTrue(bool(g._repeat_meter_visible),
                f"{case}: repeated update must not re-hide ability_meter")
            self.assertTrue(bool(g._repeat_icon_visible),
                f"{case}: repeated update must not re-hide ability_icon")
            self.assertEqual(int(g._repeat_ability_entries), 0,
                f"{case}: repeated update must not reacquire any ability lease")
            self.assertFalse(bool(g._repeat_parent_entry),
                f"{case}: repeated update must never lease the native parent")
            self.assertTrue(bool(g._repeat_parent_visible),
                f"{case}: repeated update must leave the native parent visible")
            self.assertAlmostEqual(float(g._repeat_parent_alpha),
                float(g._t_parent_alpha), places=5,
                msg=f"{case}: repeated update must not write the native parent")
            self.assertFalse(bool(g._repeat_row6_visible),
                f"{case}: repeated update must not fabricate an ACTIVE row")
            self.assertFalse(bool(g._repeat_row6_root_visible),
                f"{case}: repeated update must leave the ACTIVE row absent")
            self.assertFalse(bool(g._repeat_binding_terminal),
                f"{case}: repeated update must not re-acquire the terminal hold")
            self.assertFalse(bool(g._repeat_binding_leased),
                f"{case}: repeated update must not re-acquire any terminal lease")
            self.assertFalse(bool(g._repeat_e_visible),
                f"{case}: equipment must stay hidden while overlap persists")
            self.assertFalse(bool(g._repeat_p_visible),
                f"{case}: player must stay hidden while overlap persists")
            self.assertTrue(bool(g._repeat_p_root_same),
                f"{case}: repeated update must reuse the player root")
            self.assertTrue(bool(g._repeat_p_gauge_same),
                f"{case}: repeated update must reuse the player gauge")
            self.assertTrue(bool(g._repeat_e_root_same),
                f"{case}: repeated update must reuse the equipment root")
            self.assertTrue(bool(g._repeat_leaf_identity_same),
                f"{case}: repeated update must reuse the exact native leaves")

        for case in TERMINAL_NEGATIVE_CASES:
            with self.subTest(case=case["name"]):
                lua = kingpin_lua()
                g = lua.globals()

                lua.execute(SETUP)
                lua.execute(KINGPIN_ACTIVATE)
                lua.execute(NEAR_TERMINAL)
                lua.execute(EXPIRE)
                lua.execute(TERMINAL_BASELINE)

                self.assertTrue(bool(g._pre_p_visible),
                    f"{case['name']}: precondition player panel visible")
                self.assertTrue(bool(g._pre_p_verify),
                    f"{case['name']}: precondition player panel certified")
                self.assertTrue(bool(g._expiry_effect_inactive),
                    f"{case['name']}: precondition temporary effect inactive")
                self.assertTrue(bool(g._expiry_native_parent_visible),
                    f"{case['name']}: precondition native parent visible")
                self.assertTrue(bool(g._expiry_p_visible),
                    f"{case['name']}: precondition terminal P visible")
                self.assertTrue(bool(g._expiry_p_verify),
                    f"{case['name']}: precondition terminal P certified")
                self.assertTrue(bool(g._expiry_e_visible),
                    f"{case['name']}: precondition terminal E visible")
                self.assertTrue(bool(g._expiry_e_verify),
                    f"{case['name']}: precondition terminal E certified")
                self.assertTrue(bool(g._expiry_meter_hidden),
                    f"{case['name']}: precondition meter held hidden")
                self.assertTrue(bool(g._expiry_icon_hidden),
                    f"{case['name']}: precondition icon held hidden")
                self.assertFalse(bool(g._expiry_row6_visible),
                    f"{case['name']}: precondition ACTIVE row absent")
                self.assertEqual(int(g._t_ability_entries), 2,
                    f"{case['name']}: precondition exactly two held leaves")
                self.assertTrue(bool(g._t_binding_terminal),
                    f"{case['name']}: precondition terminal hold established")
                self.assertTrue(bool(g._t_binding_leased),
                    f"{case['name']}: precondition terminal lease established")
                self.assertIsNotNone(g._t_meter_entry,
                    f"{case['name']}: precondition meter lease entry exists")
                self.assertIsNotNone(g._t_icon_entry,
                    f"{case['name']}: precondition icon lease entry exists")

                lua.execute(_negative_script(case))

                assert_failed_closed(g, case["name"])
                assert_no_reacquisition(g, case["name"])

                name = case["name"]
                if name == "same_value_replacement_record":
                    self.assertTrue(bool(g._replacement_still),
                        "the replacement record must remain replaced")
                elif name == "application_backward":
                    self.assertEqual(float(g._app_now), 1006.02,
                        "the restored clock must be the repeated-update clock")
                elif name == "owned_row3_text_corruption":
                    self.assertTrue(bool(g._text_restored),
                        "the saved actual row3 text must be restored before retry")
                    self.assertTrue(bool(g._text_recovered_p_visible),
                        "ordinary recovery must restore the player panel")
                    self.assertTrue(bool(g._text_recovered_p_verify),
                        "ordinary recovery must recertify the player panel")
                    self.assertTrue(bool(g._text_recovered_e_visible),
                        "ordinary recovery must restore the equipment panel")
                    self.assertTrue(bool(g._text_recovered_e_verify),
                        "ordinary recovery must recertify the equipment panel")
                    self.assertTrue(bool(g._text_recovered_same_p_root),
                        "ordinary recovery must reuse the player root")
                    self.assertTrue(bool(g._text_recovered_same_p_gauge),
                        "ordinary recovery must reuse the player gauge")
                    self.assertTrue(bool(g._text_recovered_same_e_root),
                        "ordinary recovery must reuse the equipment root")
                    self.assertFalse(bool(g._text_recovered_row6),
                        "ordinary recovery must not fabricate an ACTIVE row")
                elif name == "native_icon_foreign_visible":
                    self.assertTrue(bool(g._icon_value_preserved),
                        "the exact foreign icon visibility must be preserved")
                elif name == "foreign_extra_child":
                    self.assertTrue(bool(g._foreign_child_alive),
                        "the foreign extra child must stay alive")
                    self.assertTrue(bool(g._foreign_child_parent),
                        "the foreign extra child must stay under the native parent")
                    self.assertTrue(bool(g._foreign_child_visible),
                        "the foreign extra child visibility intent must be preserved")
                    self.assertTrue(bool(g._foreign_child_shape),
                        "the foreign extra child shape must stay untouched")


if __name__ == "__main__":
    unittest.main()
