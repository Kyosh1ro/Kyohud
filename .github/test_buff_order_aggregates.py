"""Buff static ordering, native stat-card computation, no double-counting."""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

LUA_STUBS = '''
    kyohud = {}; Kyosh1roHUD = kyohud
    RequiredScript = "lib/managers/hudmanagerpd2"
    Hooks = {callbacks = {}}
    function Hooks:PostHook(class, method, id, fn) self.callbacks[id] = fn end
    function Hooks:PreHook(class, method, id, fn) self.callbacks[id] = fn end
    function Hooks:Add(...) end
    HUDManager = {}; PlayerManager = {}; managers = {}; tweak_data = {}
    function Vector3(...) return {...} end
    function log(...) end
    function alive(value) return value ~= nil end
    function Idstring(value) return value end
    DB = {has = function() return true end}
    local function color() return {with_alpha = function(self) return self end} end
    Color = setmetatable({white = color(), black = color()}, {
        __call = function(...) return color() end,
    })
    TimerManager = {game = function()
        return {time = function() return 100 end}
    end}
    Application = {time = function() return 100 end}
'''


def make_runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(LUA_STUBS)
    lua.execute((ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig"))
    lua.execute((ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig"))
    lua.execute((ROOT / "lua" / "ky_buff_render.lua").read_text(encoding="utf-8-sig"))
    lua.execute('kyohud.settings = {enable_buffs = true}')
    return lua


class BuffStaticOrderTests(unittest.TestCase):
    def test_static_slot_order_is_exact_and_compact(self):
        lua = make_runtime()
        lua.execute('''
            local STATIC_BUFF_SLOTS = kyohud:get_static_buff_slots()
            local expected = {
                [1] = "equipped_perk_deck",
                [2] = "pocket_ecm_jammer_debuff",
                [3] = "passive_health_regen",
                [4] = "standard_armor_regeneration",
                [5] = "armor_break_invulnerable_debuff",
                [6] = "damage_increase",
                [7] = "damage_reduction",
                [8] = "melee_damage_increase",
                [9] = "total_dodge_chance",
            }
            for slot = 1, 9 do
                assert(STATIC_BUFF_SLOTS[slot] == expected[slot],
                    "slot " .. slot .. ": expected " .. tostring(expected[slot])
                    .. " got " .. tostring(STATIC_BUFF_SLOTS[slot]))
            end
            local count = 0
            for _, _ in ipairs(STATIC_BUFF_SLOTS) do count = count + 1 end
            assert(count == 9, "expected 9 contiguous slots, got " .. count)
        ''')

    def test_passive_health_regen_has_a_static_slot(self):
        lua = make_runtime()
        lua.execute('''
            local presentation = kyohud.KYO_BUFF_CONFIG.buffs.passive_health_regen
            assert(presentation and presentation.fixed_slot == 3)
            assert(kyohud.KYO_BUFF_CONFIG.colors.passive_health_regen ~= nil)
        ''')

    def test_absent_buff_leaves_no_gap_in_render_list(self):
        lua = make_runtime()
        lua.execute('''
            assert(kyohud:TryRegisterGameInfoBridge() == true)
            kyohud._buffs = {}
            kyohud._buffs.damage_increase = {
                id = "damage_increase", icon = {texture = "t"}, color = Color.white,
            }
            kyohud._buffs.damage_reduction = {
                id = "damage_reduction", icon = {texture = "t"}, color = Color.white,
            }
            local buff_list = {}
            local STATIC_BUFF_SLOTS = kyohud:get_static_buff_slots()
            for _, buff_id in ipairs(STATIC_BUFF_SLOTS) do
                local buff = kyohud._buffs[buff_id]
                if buff and buff.icon then
                    table.insert(buff_list, buff)
                end
            end
            assert(#buff_list == 2, "expected 2 buffs, got " .. #buff_list)
            assert(buff_list[1].id == "damage_increase")
            assert(buff_list[2].id == "damage_reduction")
        ''')

    def test_static_order_is_stable_across_refreshes(self):
        lua = make_runtime()
        lua.execute('''
            assert(kyohud:TryRegisterGameInfoBridge() == true)
            local function collect_order()
                local result = {}
                local STATIC_BUFF_SLOTS = kyohud:get_static_buff_slots()
                for _, buff_id in ipairs(STATIC_BUFF_SLOTS) do
                    if kyohud._buffs[buff_id] then
                        result[#result + 1] = buff_id
                    end
                end
                return result
            end
            kyohud._buffs = {}
            kyohud._buffs.equipped_perk_deck = {id = "equipped_perk_deck", icon = {texture = "t"}, color = Color.white}
            kyohud._buffs.damage_increase = {id = "damage_increase", icon = {texture = "t"}, color = Color.white}
            kyohud._buffs.melee_damage_increase = {id = "melee_damage_increase", icon = {texture = "t"}, color = Color.white}
            local first = collect_order()
            for _ = 1, 10 do
                local again = collect_order()
                assert(#first == #again)
                for i = 1, #first do
                    assert(first[i] == again[i], "order instability at " .. i)
                end
            end
            assert(first[1] == "equipped_perk_deck")
            assert(first[2] == "damage_increase")
            assert(first[3] == "melee_damage_increase")
        ''')


class StatCardNativeComputationTests(unittest.TestCase):
    def test_damage_reduction_skips_unsafe_passive_branch_without_player_unit(self):
        lua = make_runtime()
        lua.execute('''
            local native_calls = 0
            managers.player = {
                has_category_upgrade = function(self, category, upgrade)
                    return category == "player" and upgrade == "passive_damage_reduction"
                end,
                player_unit = function() return nil end,
                damage_reduction_skill_multiplier = function()
                    native_calls = native_calls + 1
                    error("native passive branch must not run without a live player")
                end,
            }
            kyohud:RefreshCalculatedBuffValues()
            assert(native_calls == 0)
            assert(kyohud._buffs.damage_reduction == nil)
        ''')

    def test_damage_reduction_uses_native_multiplier(self):
        lua = make_runtime()
        lua.execute('''
            managers.player = {
                player_unit = function() return nil end,
                damage_reduction_skill_multiplier = function(self, damage_type)
                    assert(damage_type == "bullet", "must query bullet type")
                    return 0.8
                end,
            }
            kyohud:RefreshCalculatedBuffValues()
            local buff = kyohud._buffs.damage_reduction
            assert(buff ~= nil, "damage_reduction must always be visible")
            assert(buff.value_text == "-20%",
                "expected -20% reduction, got: " .. tostring(buff.value_text))
        ''')

    def test_damage_reduction_neutral_is_hidden(self):
        lua = make_runtime()
        lua.execute('''
            managers.player = {
                player_unit = function() return nil end,
                damage_reduction_skill_multiplier = function() return 1 end,
            }
            kyohud:RefreshCalculatedBuffValues()
            assert(kyohud._buffs.damage_reduction == nil,
                "neutral damage reduction must be hidden")
        ''')

    def test_passive_health_regen_combines_native_ratio_and_fixed_regen(self):
        lua = make_runtime()
        lua.execute('''
            local damage = {
                _healing_reduction = 0.8,
                _max_health = function() return 40 end,
                health_ratio = function() return 0.5 end,
            }
            managers.player = {
                player_unit = function() return {
                    character_damage = function() return damage end,
                } end,
                health_regen = function() return 0.075 end,
                fixed_health_regen = function(self, ratio)
                    assert(ratio == 0.5)
                    return 1
                end,
                damage_reduction_skill_multiplier = function() return 1 end,
                temporary_upgrade_value = function(self, c, u, d) return d end,
                get_property = function(self, p, d) return d end,
                upgrade_value = function(self, c, u, d) return d end,
                has_category_upgrade = function() return false end,
                get_melee_dmg_multiplier = function() return 1 end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
                _smoke_screen_effects = {},
            }
            managers.blackmarket = {equipped_melee_weapon = function() return nil end}
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            tweak_data.blackmarket = {melee_weapons = {}}
            kyohud:RefreshCalculatedBuffValues()
            -- (7.5% + 1/40 = 2.5%) * 80% healing effectiveness = 8%.
            assert(kyohud._buffs.passive_health_regen.value_text == "8.0%")
        ''')

    def test_passive_health_regen_includes_active_grinder_stacks(self):
        lua = make_runtime()
        lua.execute('''
            local damage = {
                _damage_to_hot_stack = {{}, {}, {}},
                _doh_data = {tick_time = 0.5},
                _healing_reduction = 0.8,
                _max_health = function() return 40 end,
                health_ratio = function() return 0.5 end,
            }
            managers.player = {
                player_unit = function() return {
                    character_damage = function() return damage end,
                } end,
                health_regen = function() return 0.025 end,
                fixed_health_regen = function() return 0 end,
                damage_reduction_skill_multiplier = function() return 1 end,
                temporary_upgrade_value = function(self, c, u, d) return d end,
                get_property = function(self, p, d) return d end,
                upgrade_value = function(self, category, upgrade, default)
                    if category == "player" and upgrade == "damage_to_hot" then
                        return 0.4
                    end
                    return default
                end,
                has_category_upgrade = function() return false end,
                get_melee_dmg_multiplier = function() return 1 end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
                _smoke_screen_effects = {},
            }
            managers.blackmarket = {equipped_melee_weapon = function() return nil end}
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            tweak_data.blackmarket = {melee_weapons = {}}
            kyohud:RefreshCalculatedBuffValues()
            -- Passive: 2.5% * 80% = 2%. Grinder over five seconds:
            -- 3 * 0.4 HP * (5 / 0.5) / 40 HP * 80% = 24%.
            assert(kyohud._buffs.passive_health_regen.value_text == "26.0%")
        ''')

    def test_passive_health_regen_ignores_grinder_without_active_stacks(self):
        lua = make_runtime()
        lua.execute('''
            local damage = {
                _damage_to_hot_stack = {},
                _doh_data = {tick_time = 0.3},
                _max_health = function() return 100 end,
                health_ratio = function() return 0.5 end,
            }
            managers.player = {
                player_unit = function() return {
                    character_damage = function() return damage end,
                } end,
                health_regen = function() return 0 end,
                fixed_health_regen = function() return 0 end,
                damage_reduction_skill_multiplier = function() return 1 end,
                temporary_upgrade_value = function(self, c, u, d) return d end,
                get_property = function(self, p, d) return d end,
                upgrade_value = function(self, category, upgrade, default)
                    if upgrade == "damage_to_hot" then return 0.4 end
                    return default
                end,
                has_category_upgrade = function() return false end,
                get_melee_dmg_multiplier = function() return 1 end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
                _smoke_screen_effects = {},
            }
            managers.blackmarket = {equipped_melee_weapon = function() return nil end}
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            tweak_data.blackmarket = {melee_weapons = {}}
            kyohud:RefreshCalculatedBuffValues()
            assert(kyohud._buffs.passive_health_regen == nil,
                "neutral passive health regeneration must be hidden")
        ''')

    def test_damage_increase_uses_native_temporaries(self):
        lua = make_runtime()
        lua.execute('''
            local player_state = {
                _overkill_all_weapons = false,
                _damage_health_ratio_mul = 0,
                _damage_health_ratio_mul_melee = 0,
            }
            local weapon_base = {
                weapon_tweak_data = function()
                    return {categories = {"rifle"}}
                end,
                damage_multiplier = function() return 1 end,
                is_category = function(self, ...)
                    local args = {...}
                    local cats = {"rifle"}
                    for _, a in ipairs(args) do
                        for _, c in ipairs(cats) do
                            if a == c then return true end
                        end
                    end
                    return false
                end,
            }
            local player_unit = {
                inventory = function() return {
                    equipped_unit = function() return {
                        base = function() return weapon_base end
                    } end
                } end,
                character_damage = function() return {
                    health_ratio = function() return 1 end
                } end,
                movement = function() return {
                    running = function() return false end,
                    crouching = function() return false end,
                    zipline_unit = function() return nil end,
                    _current_state = player_state,
                } end,
            }
            managers.player = {
                player_unit = function() return player_unit end,
                get_current_state = function() return player_state end,
                temporary_upgrade_value = function(self, cat, upgrade, default)
                    if upgrade == "dmg_multiplier_outnumbered" then return 1.15 end
                    if upgrade == "berserker_damage_multiplier" then return 1 end
                    if upgrade == "combat_medic_damage_multiplier" then return 1 end
                    if upgrade == "overkill_damage_multiplier" then return 1 end
                    return default
                end,
                get_damage_health_ratio = function() return 0 end,
                get_property = function(self, prop, default) return default end,
                upgrade_value = function(self, cat, upg, default) return default end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
            }
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            kyohud:RefreshCalculatedBuffValues()
            local buff = kyohud._buffs.damage_increase
            assert(buff ~= nil, "damage_increase must always be visible")
            assert(buff.value_text == "+15%",
                "expected +15% from underdog, got: " .. tostring(buff.value_text))
        ''')

    def test_melee_damage_uses_native_non_special(self):
        lua = make_runtime()
        lua.execute('''
            managers.blackmarket = {
                equipped_melee_weapon = function() return "test_melee" end,
            }
            tweak_data.blackmarket = {melee_weapons = {
                test_melee = {stats = {weapon_type = "knife"}},
            }}
            local player_state = {
                _damage_health_ratio_mul_melee = 0,
            }
            local movement_state = {
                _state_data = {},
                _current_state = player_state,
            }
            local player_unit = {
                inventory = function() return {equipped_unit = function() return nil end} end,
                character_damage = function() return {
                    health_ratio = function() return 1 end
                } end,
                movement = function() return movement_state end,
            }
            movement_state.running = function() return false end
            movement_state.crouching = function() return false end
            movement_state.zipline_unit = function() return nil end
            managers.player = {
                player_unit = function() return player_unit end,
                get_current_state = function() return player_state end,
                upgrade_value = function(self, cat, upg, default)
                    if cat == "player" and upg == "non_special_melee_multiplier" then return 1.25 end
                    if cat == "player" and upg == "melee_knife_damage_multiplier" then return 1.1 end
                    return default
                end,
                has_category_upgrade = function() return false end,
                temporary_upgrade_value = function(self, cat, upg, default)
                    if upg == "berserker_damage_multiplier" then return 1 end
                    return default
                end,
                get_damage_health_ratio = function() return 0 end,
                get_melee_dmg_multiplier = function() return 1 end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
            }
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            kyohud:RefreshCalculatedBuffValues()
            local buff = kyohud._buffs.melee_damage_increase
            assert(buff ~= nil, "melee_damage_increase must always be visible")
            local expected = 1.25 * 1.1
            local expected_text = "x" .. string.format("%.2f", expected)
            expected_text = string.gsub(expected_text, "(%..-)0+$", "%1")
            expected_text = string.gsub(expected_text, "%.$", "")
            assert(buff.value_text == expected_text,
                "expected " .. expected_text .. " (1.25*1.1), got: " .. tostring(buff.value_text))
        ''')

    def test_dodge_uses_skill_dodge_chance_without_double_counting(self):
        lua = make_runtime()
        lua.execute('''
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            local player_unit = {
                character_damage = function() return {} end,
                movement = function() return {
                    running = function() return false end,
                    crouching = function() return false end,
                    zipline_unit = function() return nil end,
                } end,
            }
            managers.player = {
                player_unit = function() return player_unit end,
                body_armor_value = function(self, attr)
                    assert(attr == "dodge")
                    return 0.10
                end,
                skill_dodge_chance = function(self, running, crouching, zipline)
                    return 0.15
                end,
                _smoke_screen_effects = {},
            }
            kyohud:RefreshCalculatedBuffValues()
            local buff = kyohud._buffs.total_dodge_chance
            assert(buff ~= nil, "total_dodge_chance must always be visible")
            assert(buff.value_text == "25%",
                "expected 25% (0+10+15), got: " .. tostring(buff.value_text))
        ''')

    def test_dodge_no_separate_sicario_addition(self):
        lua = make_runtime()
        lua.execute('''
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            local player_unit = {
                character_damage = function() return {} end,
                movement = function() return {
                    running = function() return false end,
                    crouching = function() return false end,
                    zipline_unit = function() return nil end,
                } end,
            }
            managers.player = {
                player_unit = function() return player_unit end,
                body_armor_value = function() return 0.05 end,
                skill_dodge_chance = function()
                    return 0.20
                end,
                _smoke_screen_effects = {},
            }
            kyohud:RefreshCalculatedBuffValues()
            local buff = kyohud._buffs.total_dodge_chance
            assert(buff.value_text == "25%",
                "skill_dodge_chance already includes sicario; expected 25%, got: "
                .. tostring(buff.value_text))
        ''')

    def test_dodge_smoke_applied_as_final_multiplicative_layer(self):
        lua = make_runtime()
        lua.execute('''
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0.5}}
            local smoke = {
                is_in_smoke = function() return true end,
            }
            local player_unit = {
                character_damage = function() return {} end,
                movement = function() return {
                    running = function() return false end,
                    crouching = function() return false end,
                    zipline_unit = function() return nil end,
                } end,
            }
            managers.player = {
                player_unit = function() return player_unit end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
                _smoke_screen_effects = {smoke},
            }
            kyohud:RefreshCalculatedBuffValues()
            local buff = kyohud._buffs.total_dodge_chance
            assert(buff.value_text == "50%",
                "1-(1-0)*(1-0.5) = 0.5 = 50%, got: " .. tostring(buff.value_text))
        ''')

    def test_dodge_temporary_dodge_added(self):
        lua = make_runtime()
        lua.execute('''
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            local player_unit = {
                character_damage = function() return {
                    _temporary_dodge_t = 200,
                    _temporary_dodge = 0.10,
                } end,
                movement = function() return {
                    running = function() return false end,
                    crouching = function() return false end,
                    zipline_unit = function() return nil end,
                } end,
            }
            managers.player = {
                player_unit = function() return player_unit end,
                body_armor_value = function() return 0.05 end,
                skill_dodge_chance = function() return 0.05 end,
                _smoke_screen_effects = {},
            }
            kyohud:RefreshCalculatedBuffValues()
            local buff = kyohud._buffs.total_dodge_chance
            assert(buff.value_text == "20%",
                "0+5+5+10 = 20%, got: " .. tostring(buff.value_text))
        ''')

    def test_stat_cards_are_persistent(self):
        lua = make_runtime()
        lua.execute('''
            local player_state = {
                _overkill_all_weapons = false,
                _damage_health_ratio_mul = 0,
                _damage_health_ratio_mul_melee = 0,
            }
            local player_unit = {
                inventory = function() return {
                    equipped_unit = function() return nil end
                } end,
                character_damage = function() return {
                    _max_health = function() return 100 end,
                    health_ratio = function() return 1 end,
                } end,
                movement = function() return {
                    running = function() return false end,
                    crouching = function() return false end,
                    zipline_unit = function() return nil end,
                    _current_state = player_state,
                } end,
            }
            managers.player = {
                player_unit = function() return player_unit end,
                get_current_state = function() return player_state end,
                damage_reduction_skill_multiplier = function() return 0.8 end,
                temporary_upgrade_value = function(s,c,u,d)
                    if u == "dmg_multiplier_outnumbered" then return 1.15 end
                    return d
                end,
                get_damage_health_ratio = function() return 0 end,
                get_property = function(s,p,d) return d end,
                upgrade_value = function(s,c,u,d)
                    if u == "non_special_melee_multiplier" then return 1.25 end
                    return d
                end,
                health_regen = function() return 0.02 end,
                fixed_health_regen = function() return 0 end,
                body_armor_value = function() return 0.1 end,
                skill_dodge_chance = function() return 0.1 end,
                has_category_upgrade = function() return false end,
                get_melee_dmg_multiplier = function() return 1 end,
                _smoke_screen_effects = {},
            }
            managers.blackmarket = {equipped_melee_weapon = function() return nil end}
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            tweak_data.blackmarket = {melee_weapons = {}}
            kyohud:RefreshCalculatedBuffValues()
            for _, id in ipairs({"passive_health_regen", "damage_increase",
                    "damage_reduction", "melee_damage_increase", "total_dodge_chance"}) do
                local buff = kyohud._buffs[id]
                assert(buff ~= nil, id .. " must be visible")
                assert(buff.persistent == true, id .. " must be persistent")
            end
        ''')

    def test_neutral_stat_cards_are_removed(self):
        lua = make_runtime()
        lua.execute('''
            managers.player = {
                player_unit = function() return nil end,
                damage_reduction_skill_multiplier = function() return 1 end,
                temporary_upgrade_value = function(s,c,u,d) return d end,
                get_damage_health_ratio = function() return 0 end,
                get_property = function(s,p,d) return d end,
                upgrade_value = function(s,c,u,d) return d end,
                health_regen = function() return 0 end,
                fixed_health_regen = function() return 0 end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
                has_category_upgrade = function() return false end,
                get_melee_dmg_multiplier = function() return 1 end,
                get_current_state = function() return nil end,
                _smoke_screen_effects = {},
            }
            managers.blackmarket = {equipped_melee_weapon = function() return nil end}
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            tweak_data.blackmarket = {melee_weapons = {}}
            for _, id in ipairs({"passive_health_regen", "damage_increase",
                    "damage_reduction", "melee_damage_increase", "total_dodge_chance"}) do
                kyohud._buffs[id] = {id = id, persistent = true}
            end
            kyohud:RefreshCalculatedBuffValues()
            for _, id in ipairs({"passive_health_regen", "damage_increase",
                    "damage_reduction", "melee_damage_increase", "total_dodge_chance"}) do
                assert(kyohud._buffs[id] == nil, id .. " must be hidden at its neutral value")
            end
        ''')

    def test_damage_increase_hidden_at_5_percent_baseline(self):
        """Damage+ buff must be hidden at 5% (perk deck tier 8 baseline)"""
        lua = make_runtime()
        lua.execute('''
            local player_state = {
                _overkill_all_weapons = false,
                _damage_health_ratio_mul = 0,
                _damage_health_ratio_mul_melee = 0,
            }
            local player_unit = {
                inventory = function() return {
                    equipped_unit = function() return nil end
                } end,
                character_damage = function() return {
                    _max_health = function() return 100 end,
                    health_ratio = function() return 1 end,
                } end,
                movement = function() return {
                    running = function() return false end,
                    crouching = function() return false end,
                    zipline_unit = function() return nil end,
                    _current_state = player_state,
                } end,
            }
            managers.player = {
                player_unit = function() return player_unit end,
                get_current_state = function() return player_state end,
                damage_reduction_skill_multiplier = function() return 1 end,
                temporary_upgrade_value = function(s,c,u,d)
                    if u == "dmg_multiplier_outnumbered" then return 1.05 end
                    if u == "berserker_damage_multiplier" then return 1.0 end
                    return d
                end,
                get_damage_health_ratio = function() return 0 end,
                get_property = function(s,p,d) return d end,
                upgrade_value = function(s,c,u,d) return d end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
                has_category_upgrade = function() return false end,
                get_melee_dmg_multiplier = function() return 1 end,
                _smoke_screen_effects = {},
            }
            managers.blackmarket = {equipped_melee_weapon = function() return nil end}
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            tweak_data.blackmarket = {melee_weapons = {}}
            kyohud:RefreshCalculatedBuffValues()
            assert(kyohud._buffs.damage_increase == nil,
                "damage_increase must be hidden at 5% baseline (perk deck tier 8)")
        ''')

    def test_damage_increase_visible_above_5_percent(self):
        """Damage+ buff must be visible above the 5% baseline."""
        lua = make_runtime()
        lua.execute('''
            local player_state = {
                _overkill_all_weapons = false,
                _damage_health_ratio_mul = 0,
                _damage_health_ratio_mul_melee = 0,
            }
            local player_unit = {
                inventory = function() return {
                    equipped_unit = function() return nil end
                } end,
                character_damage = function() return {
                    _max_health = function() return 100 end,
                    health_ratio = function() return 1 end,
                } end,
                movement = function() return {
                    running = function() return false end,
                    crouching = function() return false end,
                    zipline_unit = function() return nil end,
                    _current_state = player_state,
                } end,
            }
            managers.player = {
                player_unit = function() return player_unit end,
                get_current_state = function() return player_state end,
                damage_reduction_skill_multiplier = function() return 1 end,
                temporary_upgrade_value = function(s,c,u,d)
                    if u == "dmg_multiplier_outnumbered" then return 1.06 end
                    if u == "berserker_damage_multiplier" then return 1.0 end
                    return d
                end,
                get_damage_health_ratio = function() return 0 end,
                get_property = function(s,p,d) return d end,
                upgrade_value = function(s,c,u,d) return d end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
                has_category_upgrade = function() return false end,
                get_melee_dmg_multiplier = function() return 1 end,
                _smoke_screen_effects = {},
            }
            managers.blackmarket = {equipped_melee_weapon = function() return nil end}
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            tweak_data.blackmarket = {melee_weapons = {}}
            kyohud:RefreshCalculatedBuffValues()
            assert(kyohud._buffs.damage_increase ~= nil,
                "damage_increase must be visible above 5% baseline")
            assert(kyohud._buffs.damage_increase.value_text == "+6%",
                "expected +6%, got: " .. tostring(kyohud._buffs.damage_increase.value_text))
        ''')

    def test_no_composite_routes_for_stat_cards(self):
        lua = make_runtime()
        lua.execute('''
            local catalog = kyohud.hudlist_catalog
            for source_id, targets in pairs(catalog.routes) do
                for _, target in ipairs(targets) do
                    assert(target ~= "damage_increase",
                        source_id .. " must not route to damage_increase")
                    assert(target ~= "damage_reduction",
                        source_id .. " must not route to damage_reduction")
                    assert(target ~= "melee_damage_increase",
                        source_id .. " must not route to melee_damage_increase")
                    assert(target ~= "total_dodge_chance",
                        source_id .. " must not route to total_dodge_chance")
                    assert(target ~= "passive_health_regen",
                        source_id .. " must not route to passive_health_regen")
                end
            end
        ''')

    def test_damage_increase_respects_ignore_damage_multipliers(self):
        lua = make_runtime()
        lua.execute('''
            local player_state = {
                _overkill_all_weapons = false,
                _damage_health_ratio_mul = 0,
                _damage_health_ratio_mul_melee = 0,
            }
            local weapon_base = {
                weapon_tweak_data = function()
                    return {categories = {"rifle"}, ignore_damage_multipliers = true}
                end,
                damage_multiplier = function() return 1.5 end,
                is_category = function() return false end,
            }
            local player_unit = {
                inventory = function() return {
                    equipped_unit = function() return {
                        base = function() return weapon_base end
                    } end
                } end,
                character_damage = function() return {
                    health_ratio = function() return 1 end
                } end,
                movement = function() return {
                    running = function() return false end,
                    crouching = function() return false end,
                    zipline_unit = function() return nil end,
                    _current_state = player_state,
                } end,
            }
            managers.player = {
                player_unit = function() return player_unit end,
                get_current_state = function() return player_state end,
                temporary_upgrade_value = function(self, cat, upgrade, default)
                    if upgrade == "dmg_multiplier_outnumbered" then return 1.25 end
                    return default
                end,
                get_damage_health_ratio = function() return 0 end,
                get_property = function() return 1 end,
                upgrade_value = function(self, cat, upg, default) return default end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
            }
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            kyohud:RefreshCalculatedBuffValues()
            local buff = kyohud._buffs.damage_increase
            assert(buff ~= nil)
            assert(buff.value_text == "+50%",
                "ignore_damage_multipliers should only show static weapon mul, got: "
                .. tostring(buff.value_text))
        ''')

    def test_damage_increase_includes_combat_medic_multiplier(self):
        lua = make_runtime()
        lua.execute('''
            local player_state = {
                _overkill_all_weapons = false,
                _damage_health_ratio_mul = 0,
                _damage_health_ratio_mul_melee = 0,
            }
            local weapon_base = {
                weapon_tweak_data = function()
                    return {categories = {"rifle"}}
                end,
                damage_multiplier = function() return 1 end,
                is_category = function() return false end,
            }
            local player_unit = {
                inventory = function() return {
                    equipped_unit = function() return {
                        base = function() return weapon_base end
                    } end
                } end,
                character_damage = function() return {
                    health_ratio = function() return 1 end
                } end,
                movement = function() return {
                    running = function() return false end,
                    crouching = function() return false end,
                    zipline_unit = function() return nil end,
                    _current_state = player_state,
                } end,
            }
            managers.player = {
                player_unit = function() return player_unit end,
                get_current_state = function() return player_state end,
                temporary_upgrade_value = function(self, cat, upgrade, default)
                    if upgrade == "combat_medic_damage_multiplier" then return 1.35 end
                    return default
                end,
                get_damage_health_ratio = function() return 0 end,
                get_property = function() return 1 end,
                upgrade_value = function(self, cat, upg, default) return default end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
            }
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            kyohud:RefreshCalculatedBuffValues()
            local buff = kyohud._buffs.damage_increase
            assert(buff ~= nil)
            assert(buff.value_text == "+35%",
                "combat_medic should contribute, got: " .. tostring(buff.value_text))
        ''')

    def test_damage_increase_counts_trigger_happy_once(self):
        lua = make_runtime()
        lua.execute('''
            local trigger_mul = 2
            local state = {_overkill_all_weapons = false,
                _damage_health_ratio_mul = 0, _damage_health_ratio_mul_melee = 0}
            local base = {
                weapon_tweak_data = function() return {categories = {"pistol"}} end,
                -- Fresh native value: x1.5 static and x2 Trigger Happy.
                damage_multiplier = function() return 3 end,
                is_category = function() return false end,
            }
            local player = {
                inventory = function() return {equipped_unit = function()
                    return {base = function() return base end}
                end} end,
                character_damage = function() return {health_ratio = function() return 1 end} end,
            }
            managers.player = {
                player_unit = function() return player end,
                get_current_state = function() return state end,
                temporary_upgrade_value = function(self, c, u, d) return d end,
                get_damage_health_ratio = function() return 0 end,
                get_property = function(self, name, default)
                    return name == "trigger_happy" and trigger_mul or default
                end,
                upgrade_value = function(self, c, u, d) return d end,
                has_category_upgrade = function() return false end,
                get_melee_dmg_multiplier = function() return 1 end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
                damage_reduction_skill_multiplier = function() return 1 end,
                _smoke_screen_effects = {},
            }
            managers.blackmarket = {equipped_melee_weapon = function() return nil end}
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            tweak_data.blackmarket = {melee_weapons = {}}
            kyohud:RefreshCalculatedBuffValues()
            assert(kyohud._buffs.damage_increase.value_text == "+200%",
                "Trigger Happy must be counted once")
        ''')

    def test_ignored_weapon_still_uses_combat_medic(self):
        lua = make_runtime()
        lua.execute('''
            local base = {
                weapon_tweak_data = function()
                    return {categories = {"special"}, ignore_damage_multipliers = true}
                end,
                damage_multiplier = function() return 1 end,
            }
            local player = {
                inventory = function() return {equipped_unit = function()
                    return {base = function() return base end}
                end} end,
                character_damage = function() return {health_ratio = function() return 1 end} end,
            }
            managers.player = {
                player_unit = function() return player end,
                get_property = function(self, name, default) return default end,
                temporary_upgrade_value = function(self, c, upgrade, default)
                    if upgrade == "combat_medic_damage_multiplier" then return 1.5 end
                    if upgrade == "dmg_multiplier_outnumbered" then return 9 end
                    return default
                end,
                upgrade_value = function(self, c, u, d) return d end,
                has_category_upgrade = function() return false end,
                get_melee_dmg_multiplier = function() return 1 end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
                damage_reduction_skill_multiplier = function() return 1 end,
                _smoke_screen_effects = {},
            }
            managers.blackmarket = {equipped_melee_weapon = function() return nil end}
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            tweak_data.blackmarket = {melee_weapons = {}}
            kyohud:RefreshCalculatedBuffValues()
            assert(kyohud._buffs.damage_increase.value_text == "+50%",
                "ignored weapon should skip shot upgrades but retain Combat Medic")
        ''')

    def test_overkill_uses_is_category_for_saw(self):
        lua = make_runtime()
        lua.execute('''
            local player_state = {
                _overkill_all_weapons = false,
                _damage_health_ratio_mul = 0,
                _damage_health_ratio_mul_melee = 0,
            }
            local weapon_base = {
                weapon_tweak_data = function()
                    return {categories = {"rifle"}}
                end,
                damage_multiplier = function() return 1 end,
                is_category = function(self, ...)
                    local args = {...}
                    for _, a in ipairs(args) do
                        if a == "shotgun" or a == "saw" then return true end
                    end
                    return false
                end,
            }
            local player_unit = {
                inventory = function() return {
                    equipped_unit = function() return {
                        base = function() return weapon_base end
                    } end
                } end,
                character_damage = function() return {
                    health_ratio = function() return 1 end
                } end,
                movement = function() return {
                    running = function() return false end,
                    crouching = function() return false end,
                    zipline_unit = function() return nil end,
                    _current_state = player_state,
                } end,
            }
            managers.player = {
                player_unit = function() return player_unit end,
                get_current_state = function() return player_state end,
                temporary_upgrade_value = function(self, cat, upgrade, default)
                    if upgrade == "overkill_damage_multiplier" then return 1.5 end
                    return default
                end,
                get_damage_health_ratio = function() return 0 end,
                get_property = function() return 1 end,
                upgrade_value = function(self, cat, upg, default) return default end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
            }
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            kyohud:RefreshCalculatedBuffValues()
            local buff = kyohud._buffs.damage_increase
            assert(buff ~= nil)
            assert(buff.value_text == "+50%",
                "is_category('shotgun','saw') should trigger overkill, got: "
                .. tostring(buff.value_text))
        ''')

    def test_melee_damage_includes_bloodthirst_multiplier(self):
        lua = make_runtime()
        lua.execute('''
            managers.blackmarket = {
                equipped_melee_weapon = function() return "test_melee" end,
            }
            tweak_data.blackmarket = {melee_weapons = {
                test_melee = {stats = {weapon_type = "knife"}},
            }}
            local player_state = {
                _damage_health_ratio_mul_melee = 0,
            }
            local movement_state = {
                _state_data = {},
                _current_state = player_state,
            }
            local player_unit = {
                inventory = function() return {equipped_unit = function() return nil end} end,
                character_damage = function() return {
                    health_ratio = function() return 1 end
                } end,
                movement = function() return movement_state end,
            }
            movement_state.running = function() return false end
            movement_state.crouching = function() return false end
            movement_state.zipline_unit = function() return nil end
            managers.player = {
                player_unit = function() return player_unit end,
                get_current_state = function() return player_state end,
                upgrade_value = function(self, cat, upg, default)
                    if cat == "player" and upg == "non_special_melee_multiplier" then return 1 end
                    return default
                end,
                has_category_upgrade = function() return false end,
                temporary_upgrade_value = function(self, cat, upg, default)
                    if upg == "berserker_damage_multiplier" then return 1 end
                    return default
                end,
                get_damage_health_ratio = function() return 0 end,
                get_melee_dmg_multiplier = function() return 1.5 end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
            }
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            kyohud:RefreshCalculatedBuffValues()
            local buff = kyohud._buffs.melee_damage_increase
            assert(buff ~= nil)
            assert(buff.value_text == "x1.5",
                "Bloodthirst should contribute 1.5x, got: " .. tostring(buff.value_text))
        ''')

    def test_refresh_calculated_removes_hidden_stat_cards(self):
        lua = make_runtime()
        lua.execute('''
            managers.player = {
                player_unit = function() return nil end,
                damage_reduction_skill_multiplier = function() return 0.8 end,
                temporary_upgrade_value = function(s,c,u,d) return d end,
                get_damage_health_ratio = function() return 0 end,
                get_property = function(s,p,d) return d end,
                upgrade_value = function(s,c,u,d) return d end,
                body_armor_value = function() return 0 end,
                skill_dodge_chance = function() return 0 end,
                has_category_upgrade = function() return false end,
                get_melee_dmg_multiplier = function() return 1 end,
                get_current_state = function() return nil end,
                _smoke_screen_effects = {},
            }
            managers.blackmarket = {equipped_melee_weapon = function() return nil end}
            tweak_data.player = {damage = {DODGE_INIT = 0}}
            tweak_data.projectiles = {smoke_screen_grenade = {dodge_chance = 0}}
            tweak_data.blackmarket = {melee_weapons = {}}
            kyohud:RefreshCalculatedBuffValues()
            assert(kyohud._buffs.damage_reduction ~= nil)
            kyohud.settings = {enable_buffs = false}
            kyohud:RefreshCalculatedBuffValues()
            assert(kyohud._buffs.damage_increase == nil,
                "stat card must be removed when buff is hidden")
            assert(kyohud._buffs.damage_reduction == nil)
            assert(kyohud._buffs.melee_damage_increase == nil)
            assert(kyohud._buffs.total_dodge_chance == nil)
        ''')


if __name__ == "__main__":
    unittest.main()
