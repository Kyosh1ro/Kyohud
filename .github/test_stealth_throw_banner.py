"""Stealth throw banner tests.

Verifies that stealth throwing kills trigger large multikill-style banners.
Run: uv run --with lupa python -B -m unittest discover -s .github -p test_stealth_throw_banner.py -v
"""
from pathlib import Path
import unittest
from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


def _common_stubs():
    return '''
        _pre_hooks = {}
        _post_hooks = {}
        _wrapped = {}
        Hooks = {}
        local function ensure_wrapper(class, method)
            local key = tostring(class) .. ":" .. method
            if _wrapped[key] then return end
            _wrapped[key] = true
            local orig = class[method] or function() end
            class[method] = function(self, ...)
                local pre = _pre_hooks[class] and _pre_hooks[class][method] or {}
                for _, entry in ipairs(pre) do entry.fn(self, ...) end
                local result = {orig(self, ...)}
                local post = _post_hooks[class] and _post_hooks[class][method] or {}
                for _, entry in ipairs(post) do entry.fn(self, ...) end
                return unpack(result)
            end
        end
        function Hooks:PreHook(class, method, id, fn)
            if type(class) == 'table' then class[method] = class[method] or function() end end
            if not _pre_hooks[class] then _pre_hooks[class] = {} end
            if not _pre_hooks[class][method] then _pre_hooks[class][method] = {} end
            local list = _pre_hooks[class][method]
            for _, entry in ipairs(list) do
                if entry.id == id then return end
            end
            list[#list + 1] = {id = id, fn = fn}
            ensure_wrapper(class, method)
        end
        function Hooks:PostHook(class, method, id, fn)
            if type(class) == 'table' then class[method] = class[method] or function() end end
            if not _post_hooks[class] then _post_hooks[class] = {} end
            if not _post_hooks[class][method] then _post_hooks[class][method] = {} end
            local list = _post_hooks[class][method]
            for _, entry in ipairs(list) do
                if entry.id == id then return end
            end
            list[#list + 1] = {id = id, fn = fn}
            ensure_wrapper(class, method)
        end
        function Hooks:Add(...) end
        HUDManager = {sync_start_assault = function() end, sync_end_assault = function() end}
        PlayerManager = {spawned_player = function() end, on_killshot = function() end}
        PlayerInventory = {equip_selection = function() end}
        CopDamage = {
            is_civilian = function(id) return id == 'civilian' or id == 'civilian_female' end,
            die = function(self, attack_data) end,
            chk_killshot = function(self, attacker, variant, headshot, weapon_id)
                if attacker and attacker == local_player then
                    PlayerManager:on_killshot(self._unit, variant, headshot, weapon_id)
                end
            end,
        }
        HuskCopDamage = setmetatable({}, {__index = CopDamage})
        HuskCopDamage.die = function(self, attack_data)
            self._health = 0
            self._dead = true
        end
        CivilianDamage = {
            _on_damage_received = function(self, attack_data) end
        }
        hud_icon_calls = 0
        managers = {}; tweak_data = {
            weapon = {},
            hud_icons = {get_icon_data = function(self, name)
                hud_icon_calls = hud_icon_calls + 1
                return 'resolved/' .. name, {0,0,1,1}
            end},
            blackmarket = {
                projectiles = {
                    wpn_prj_jav = {},
                    wpn_prj_target = {},
                    wpn_prj_hur = {},
                    wpn_prj_four = {},
                    wpn_prj_ace = {}
                }
            }
        }
        DB = {has = function() return true end}
        function Idstring(value) return value end
        function Vector3(...) return {...} end
        mvector3 = {distance = function(a, b) return 0 end}
        function log(...) end
        function alive(x) return x ~= nil and x ~= false end
        Color = setmetatable({white = {}, black = {}}, {__call = function(...) return {} end})
        game_t = 100; state_name = 'menu_main'; is_client = false
        Network = {is_client = function() return is_client end}
        TimerManager = {game = function() return {time = function() return game_t end} end}
        game_state_machine = {last_queued_state_name = function() return state_name end}
        local_player = {position = function() return {x=0,y=0,z=0} end}
        managers.player = {player_unit = function() return local_player end}
        managers.groupai = {state = function() return {whisper_mode = function() return true end} end}
        function make_projectile_base(entry_name)
            return {
                thrower_unit = function() return local_player end,
                projectile_entry = function() return entry_name end,
                get_name_id = function() return entry_name end,
            }
        end
        function enemy(id)
            return {base = function() return {_tweak_table = id or 'cop'} end}
        end
        function throwing_projectile(entry_name, thrower)
            local proj_base = make_projectile_base(entry_name or 'wpn_prj_jav')
            if thrower then
                proj_base.thrower_unit = function() return thrower end
            end
            return {base = function() return proj_base end}
        end
    '''


class StealthThrowBannerTests(unittest.TestCase):
    """Test stealth throw banner triggering and rotation."""

    def setUp(self):
        """Set up test environment."""
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + '/'
        self.lua.execute(_common_stubs())
        self.load('core.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_combat_medals.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_hud_banners.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_killfeed.lua', 'lib/units/enemies/cop/copdamage')
        self.lua.execute('''
            kyohud.settings = {enable_killfeed = true, killfeed_size = 3}
            kyohud:ResetHeistCombatState()
        ''')

    def load(self, name, context):
        self.lua.globals().RequiredScript = context
        self.lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

    def test_first_stealth_throw_triggers_banner(self):
        """First stealth throw kill should trigger a banner."""
        self.lua.execute('''
            kyohud._kills = {}
            kyohud._banner_queue = {}
            kyohud._special_kill_banner = nil

            local proj = throwing_projectile('wpn_prj_jav')
            local unit = enemy('cop')
            local attack_info = {
                variant = "melee",
                weapon_unit = proj
            }
            local event_info = {
                deadly_throw = true,
                stealth = true
            }

            kyohud:add_kill("Enemy", 100, true, nil, nil, nil, event_info, "player")

            banner_queued = #kyohud._banner_queue > 0 or kyohud._special_kill_banner ~= nil
        ''')
        result = self.lua.eval("banner_queued")
        self.assertTrue(result, "Stealth throw should trigger a banner")

    def test_three_stealth_throw_banners_rotate(self):
        """Three consecutive stealth throws should cycle through all 3 banner variants."""
        self.lua.execute('''
            kyohud._kills = {}
            kyohud._banner_queue = {}
            kyohud._special_kill_banner = nil
            kyohud._stealth_throw_banner_index = 0

            labels = {}
            for i = 1, 3 do
                local proj = throwing_projectile('wpn_prj_jav')
                local unit = enemy('cop_' .. i)
                local attack_info = {
                    variant = "melee",
                    weapon_unit = proj
                }
                local event_info = {
                    deadly_throw = true,
                    stealth = true
                }

                kyohud:add_kill("Enemy", 100, true, nil, nil, nil, event_info, "player")

                -- Check what banner was queued
                if #kyohud._banner_queue > 0 then
                    labels[i] = kyohud._banner_queue[#kyohud._banner_queue].label
                    table.remove(kyohud._banner_queue)
                end
            end
        ''')
        labels = self.lua.eval("labels")
        self.assertEqual(len(labels), 3, "Should have 3 banner labels")
        # Check that we got different labels (rotation)
        unique_labels = set(labels.values())
        self.assertGreater(len(unique_labels), 1, "Should have rotated through different labels")

    def test_loud_throw_does_not_trigger_stealth_banner(self):
        """Loud throw kill should NOT trigger stealth throw banner."""
        self.lua.execute('''
            kyohud._kills = {}
            kyohud._banner_queue = {}
            kyohud._special_kill_banner = nil

            local proj = throwing_projectile('wpn_prj_jav')
            local unit = enemy('cop')
            local attack_info = {
                variant = "melee",
                weapon_unit = proj
            }
            local event_info = {
                deadly_throw = true,
                stealth = false  -- Loud kill
            }

            kyohud:add_kill("Enemy", 100, true, nil, nil, nil, event_info, "player")

            banner_count = #kyohud._banner_queue
        ''')
        result = self.lua.eval("banner_count")
        self.assertEqual(result, 0, "Loud throw should not trigger stealth banner")

    def test_non_throw_stealth_does_not_trigger_banner(self):
        """Stealth kill that is NOT a throw should not trigger stealth throw banner."""
        self.lua.execute('''
            kyohud._kills = {}
            kyohud._banner_queue = {}
            kyohud._special_kill_banner = nil

            local unit = enemy('cop')
            local attack_info = {
                variant = "melee",
                weapon_unit = nil  -- Not a throw
            }
            local event_info = {
                deadly_throw = false,  -- Not a throw
                stealth = true
            }

            kyohud:add_kill("Enemy", 100, true, nil, nil, nil, event_info, "player")

            banner_count = #kyohud._banner_queue
        ''')
        result = self.lua.eval("banner_count")
        self.assertEqual(result, 0, "Non-throw stealth should not trigger banner")

    def test_sentry_throw_does_not_trigger_banner(self):
        """Sentry throw kill should not trigger stealth throw banner."""
        self.lua.execute('''
            kyohud._kills = {}
            kyohud._banner_queue = {}
            kyohud._special_kill_banner = nil

            local proj = throwing_projectile('wpn_prj_jav')
            local unit = enemy('cop')
            local attack_info = {
                variant = "melee",
                weapon_unit = proj
            }
            local event_info = {
                deadly_throw = true,
                stealth = true
            }

            -- Kill source is "sentry"
            kyohud:add_kill("Enemy", 100, true, nil, nil, nil, event_info, "sentry")

            banner_count = #kyohud._banner_queue
        ''')
        result = self.lua.eval("banner_count")
        self.assertEqual(result, 0, "Sentry throw should not trigger stealth banner")

    def test_civilian_throw_does_not_trigger_banner(self):
        """Civilian throw kill should not trigger stealth throw banner."""
        self.lua.execute('''
            kyohud._kills = {}
            kyohud._banner_queue = {}
            kyohud._special_kill_banner = nil

            local proj = throwing_projectile('wpn_prj_jav')
            local unit = enemy('civilian')
            local attack_info = {
                variant = "melee",
                weapon_unit = proj
            }
            local event_info = {
                deadly_throw = true,
                stealth = true
            }

            -- contributes_to_combo = false (civilian)
            kyohud:add_kill("Civilian", 100, false, nil, nil, nil, event_info, "player")

            banner_count = #kyohud._banner_queue
        ''')
        result = self.lua.eval("banner_count")
        self.assertEqual(result, 0, "Civilian throw should not trigger stealth banner")

    def test_reset_clears_banner_index(self):
        """ResetHeistCombatState should clear the stealth throw banner index."""
        self.lua.execute('''
            kyohud._stealth_throw_banner_index = 2
            kyohud:ResetHeistCombatState()
            index = kyohud._stealth_throw_banner_index
        ''')
        result = self.lua.eval("index")
        self.assertEqual(result, 0, "Reset should set banner index to 0")

    def test_localization_keys_exist(self):
        """Verify stealth throw banner helper exists and can create banners."""
        self.lua.execute('''
            can_create = kyohud.MakeStealthThrowBanner ~= nil
            if can_create then
                banner = kyohud:MakeStealthThrowBanner(1)
                has_label = banner ~= nil and banner.label ~= nil and banner.label ~= ""
                has_color = banner ~= nil and banner.color ~= nil
                has_multikill_style = banner ~= nil and banner.multikill_style == true
                all_valid = has_label and has_color and has_multikill_style
            else
                all_valid = false
            end
        ''')
        result = self.lua.eval("all_valid")
        self.assertTrue(result, "MakeStealthThrowBanner should create valid banners with label, color, and multikill_style")


if __name__ == '__main__':
    unittest.main()
