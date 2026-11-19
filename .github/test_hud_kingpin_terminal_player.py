"""Lot 6 RED: when the native Kingpin radial reaches terminal zero progress,
the KyoHUD player panel must be visible and certified again, reusing the same
root and gauge objects, with the native parent hidden and its leaves visible.
"""
import unittest

from test_hud_kingpin_active import KINGPIN_ACTIVATE, kingpin_lua


SETUP = r'''
kyohud.settings.enable_player = true

local cd = _character_damage
function cd:get_real_health() return 100 end
function cd:_max_health() return 100 end
function cd:get_real_armor() return 50 end
function cd:_max_armor() return 50 end
function cd:need_revive() return false end
function cd:revives() return 4 end
function cd:get_revives() return 4 end
function cd:health_ratio() return 1 end
function cd:armor_ratio() return 1 end
function cd:dead() return false end

_R:refresh_settings(_m)
_R:update(_m, 3.2, 0.1)
_P = kyohud.hud.player
assert(_P._root:visible() and _P:verify())
_G._pre_p_visible = (_P._root:visible() == true)
_G._pre_p_verify = (_P:verify() == true)
'''

SAVE_AND_EXPIRE = r'''
_G._p_root = _P._root
_G._p_gauge = _P._gauge
assert(_G._p_root ~= nil and _G._p_gauge ~= nil)

-- Newly invalidated-render precondition: corrupt the actual owned E row3 value
-- so terminal qualification fails on missing valid owned rendering, not natural
-- expiry alone, preserving the historical fallback/repair coverage.
_E._rows[3]._value:set_text("BROKEN")

_app_now = 1006.01
_R:update(_m, 3.21, 0.01)

_G._expiry_p_hidden = (_P._root:visible() == false)
_G._expiry_native_parent_visible = (_ability_parent:visible() == true)
_G._expiry_leaves_visible = (_ability_meter:visible() == true)
    and (_ability_icon:visible() == true)
assert(_G._expiry_p_hidden)
assert(_G._expiry_native_parent_visible)
assert(_G._expiry_leaves_visible)
'''

TERMINAL = r'''
_m:set_player_ability_radial({current = 0, total = 1})

_G._final_p_visible = (_P._root:visible() == true)
_G._final_p_verify = (_P:verify() == true)
_G._final_e_visible = (_E._root ~= nil and _E._root:visible() == true)
_G._final_native_parent_hidden = (_ability_parent:visible() == false)
_G._final_leaves_visible = (_ability_meter:visible() == true)
    and (_ability_icon:visible() == true)
_G._final_same_root = (_P._root == _G._p_root)
_G._final_same_gauge = (_P._gauge == _G._p_gauge)
'''


class KingpinTerminalPlayerTests(unittest.TestCase):
    def test_terminal_zero_progress_restores_player_panel(self):
        lua = kingpin_lua()
        g = lua.globals()

        lua.execute(SETUP)
        self.assertTrue(bool(g._pre_p_visible),
            "precondition: owned player panel must start visible")
        self.assertTrue(bool(g._pre_p_verify),
            "precondition: owned player panel must start certified")

        lua.execute(KINGPIN_ACTIVATE)
        lua.execute(SAVE_AND_EXPIRE)
        lua.execute(TERMINAL)

        self.assertTrue(bool(g._final_p_visible),
            "RED: terminal zero native radial must leave the player panel visible")
        self.assertTrue(bool(g._final_p_verify),
            "RED: restored player panel must stay certified")
        self.assertTrue(bool(g._final_e_visible),
            "equipment panel must stay visible")
        self.assertTrue(bool(g._final_native_parent_hidden),
            "native radial_ability parent must be hidden at zero progress")
        self.assertTrue(bool(g._final_leaves_visible),
            "native ability leaves must be restored to visible")
        self.assertTrue(bool(g._final_same_root),
            "player panel root identity must be preserved")
        self.assertTrue(bool(g._final_same_gauge),
            "player panel gauge identity must be preserved")

    def test_verification_failure_fails_closed(self):
        lua = kingpin_lua()
        g = lua.globals()

        lua.execute(SETUP)
        lua.execute(KINGPIN_ACTIVATE)
        lua.execute(SAVE_AND_EXPIRE)

        lua.execute(r'''
local original_text = _P._condition_text.text
_P._condition_text.text = function() return "BROKEN" end

_m:set_player_ability_radial({current = 0, total = 1})
_R:update(_m, 3.3, 0.05)

_G._bad_p_hidden = (_P._root:visible() == false)
_G._bad_p_not_verified = (_P._render_verified == false)
_G._bad_native_parent_hidden = (_ability_parent:visible() == false)
_G._bad_native_leaves_visible = (_ability_meter:visible() == true)
    and (_ability_icon:visible() == true)

_P._condition_text.text = original_text
_R:update(_m, 3.4, 0.05)

_G._recovered_p_visible = (_P._root:visible() == true)
_G._recovered_p_verify = (_P:verify() == true)
_G._recovered_same_root = (_P._root == _G._p_root)
_G._recovered_same_gauge = (_P._gauge == _G._p_gauge)
''')

        self.assertTrue(bool(g._bad_p_hidden),
            "failed condition-text verification must keep the owned panel hidden")
        self.assertTrue(bool(g._bad_p_not_verified),
            "failed condition-text verification must never certify the owned panel")
        self.assertTrue(bool(g._bad_native_parent_hidden),
            "native radial parent must stay hidden at terminal zero")
        self.assertTrue(bool(g._bad_native_leaves_visible),
            "native ability leaves must stay visible at terminal zero")
        self.assertTrue(bool(g._recovered_p_visible),
            "restored condition text must restore the player panel")
        self.assertTrue(bool(g._recovered_p_verify),
            "restored player panel must be certified")
        self.assertTrue(bool(g._recovered_same_root),
            "player panel root identity must be preserved")
        self.assertTrue(bool(g._recovered_same_gauge),
            "player panel gauge identity must be preserved")


if __name__ == "__main__":
    unittest.main()
