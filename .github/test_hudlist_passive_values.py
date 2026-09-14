"""Passive values and composites against the real HUDList Lua chunk."""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class HUDListPassiveValueTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + "/"
        self.lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/hudmanagerpd2"
            Hooks = {}
            Application = {time = function() return 100 end}
        ''')
        self.lua.execute((ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig"))

    def test_composite_contributions_update_without_duplication_and_preserve_order(self):
        self.lua.execute('''
            local provider = kyohud.hudlist
            assert(provider:set_composite_contribution(
                "damage_increase", "overkill", "multiply", 1.75
            ))
            local first = provider:get_buffs().damage_increase
            assert(first and first.value == 1.75)
            assert(provider:get_composite_source_count("damage_increase") == 1)
            assert(provider:get_arrival_order()[1] == "damage_increase")

            assert(provider:set_composite_contribution(
                "damage_increase", "overkill", "multiply", 1.5
            ))
            assert(provider:get_buffs().damage_increase == first)
            assert(first.value == 1.5)
            assert(provider:get_composite_source_count("damage_increase") == 1)
            assert(provider:get_arrival_order()[1] == "damage_increase")

            assert(provider:set_composite_contribution(
                "damage_increase", "underdog", "multiply", 1.15
            ))
            assert(math.abs(first.value - 1.725) < 0.000001)
            assert(provider:remove_composite_contribution("damage_increase", "overkill"))
            assert(provider:get_buffs().damage_increase.value == 1.15)
            assert(provider:remove_composite_contribution("damage_increase", "underdog"))
            assert(provider:get_buffs().damage_increase == nil)
        ''')

    def test_composite_operations_are_explicit_and_invalid_values_are_ignored(self):
        self.lua.execute('''
            local provider = kyohud.hudlist
            assert(provider:set_composite_contribution(
                "damage_reduction", "frenzy", "multiply", 0.75
            ))
            assert(provider:set_composite_contribution(
                "damage_reduction", "underdog_aced", "multiply", 0.9
            ))
            assert(math.abs(provider:get_buff("damage_reduction").value - 0.675) < 0.000001)
            assert(provider:set_composite_contribution(
                "total_dodge_chance", "native_final", "replace", 0.35
            ))
            assert(provider:get_buff("total_dodge_chance").value == 0.35)
            assert(not provider:set_composite_contribution(
                "damage_reduction", "bad", "multiply", 0/0
            ))
            assert(not provider:set_composite_contribution(
                "damage_reduction", "wrong", "sum", 0.1
            ))
            assert(provider:get_composite_source_count("damage_reduction") == 2)
        ''')

    def test_composite_internal_contributions_are_not_exposed(self):
        self.lua.execute('''
            local provider = kyohud.hudlist
            provider:set_composite_contribution(
                "damage_increase", "overkill", "multiply", 1.75
            )
            local public = provider:get_buff("damage_increase")
            assert(public.contributions == nil)
            public.value = 99
            assert(provider:get_buff("damage_increase").value == 1.75)
        ''')


    def test_damage_reduction_routes_exclude_absorption_and_invulnerability(self):
        self.lua.execute('''
            local routes = kyohud.hudlist_catalog.routes
            assert(#routes.maniac == 1 and routes.maniac[1] == "maniac")
            assert(#routes.copycat_health_invul == 1
                and routes.copycat_health_invul[1] == "copycat_health_invul")
            assert(routes.copycat_health_invul_passive == nil)
            assert(#routes.chico_injector == 2
                and routes.chico_injector[2] == "damage_reduction")
        ''')


    def test_berserker_routes_melee_and_weapon_damage_without_duplicate_basic_card(self):
        self.lua.execute('''
            local routes = kyohud.hudlist_catalog.routes
            assert(#routes.berserker == 1 and routes.berserker[1] == "melee_damage_increase")
            assert(#routes.berserker_aced == 2)
            assert(routes.berserker_aced[1] == "berserker_aced")
            assert(routes.berserker_aced[2] == "damage_increase")
        ''')


class HUDListNativePassiveProducerTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + "/"
        self.lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/units/beings/player/playerdamage"
            PlayerDamage = {}
            Hooks = {post = {}, pre = {}}
            function Hooks:PostHook(class, method, id, fn) self.post[method] = fn end
            function Hooks:PreHook(class, method, id, fn) self.pre[method] = fn end
            TimerManager = {game = function() return {time = function() return 100 end} end}
            Application = {time = function() return 100 end}
            alive = function(unit) return unit ~= nil end
            upgrades = {}
            local pm = {ratio_calls = 0}
            function pm:has_category_upgrade(category, upgrade)
                return upgrades[category .. ":" .. upgrade] == true
            end
            function pm:upgrade_value(category, upgrade, default)
                local value = upgrades[category .. ":" .. upgrade .. ":value"]
                return value == nil and default or value
            end
            function pm:get_damage_health_ratio(ratio, category)
                self.ratio_calls = self.ratio_calls + 1
                local threshold = category == "armor_regen" and 1 or 0.5
                return math.max(1 - ratio / threshold, 0)
            end
            function pm:get_hostage_bonus_addend() return self.hostage_regen or 0 end
            function pm:team_upgrade_value(category, upgrade, default)
                if category == "team" and upgrade == "crew_health_regen" then
                    return self.crew_regen or default
                end
                return default
            end
            managers = {player = pm}
            damage = {_health_regen_update_timer = nil, health = 100, maximum = 100}
            function damage:health_ratio() return self.health / self.maximum end
            function damage:get_real_health() return self.health end
            function damage:_max_health() return self.maximum end
        ''')
        self.lua.execute((ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig"))

    def test_health_ratio_buffs_are_distinct_normalized_and_deduplicated(self):
        self.lua.execute('''
            upgrades["player:melee_damage_health_ratio_multiplier"] = true
            upgrades["player:melee_damage_health_ratio_multiplier:value"] = 2.5
            upgrades["player:damage_health_ratio_multiplier"] = true
            upgrades["player:damage_health_ratio_multiplier:value"] = 1
            upgrades["player:armor_regen_damage_health_ratio_multiplier"] = true
            upgrades["player:armor_regen_damage_health_ratio_multiplier:value"] = 0.4
            upgrades["player:movement_speed_damage_health_ratio_multiplier"] = true
            upgrades["player:movement_speed_damage_health_ratio_multiplier:value"] = 0.2
            damage.health = 25
            Hooks.post.set_health(damage)
            local provider = kyohud.hudlist
            assert(provider:get_buff("berserker").value == 1.25)
            assert(provider:get_buff("berserker_aced").value == 0.5)
            assert(math.abs(provider:get_buff("yakuza_recovery").value - 0.3) < 0.000001)
            assert(math.abs(provider:get_buff("yakuza_speed").value - 0.1) < 0.000001)
            local calls = managers.player.ratio_calls
            Hooks.post.set_health(damage)
            assert(managers.player.ratio_calls == calls)
            damage.health = 100
            Hooks.post.set_health(damage)
            assert(provider:get_buff("berserker") == nil)
            assert(provider:get_buff("berserker_aced") == nil)
            assert(provider:get_buff("yakuza_recovery") == nil)
            assert(provider:get_buff("yakuza_speed") == nil)
        ''')

    def test_passive_regen_sources_share_native_tick_and_clear_at_full_health(self):
        self.lua.execute('''
            local provider = kyohud.hudlist
            upgrades["player:passive_health_regen"] = true
            upgrades["player:passive_health_regen:value"] = 0.03
            upgrades["player:hostage_health_regen_addend"] = true
            managers.player.hostage_regen = 0.045
            managers.player.crew_regen = 0.5
            damage.health = 50
            damage._health_regen_update_timer = 3
            Hooks.post._upd_health_regen(damage)
            assert(provider:get_buff("muscle_regen").value == 0.03)
            assert(provider:get_buff("muscle_regen").interval == 5)
            assert(provider:get_buff("muscle_regen").expire_t == 103)
            assert(provider:get_buff("hostage_taker").value == 0.045)
            assert(provider:get_buff("crew_health_regen").value == 0.5)
            damage.health = 100
            Hooks.post.set_health(damage)
            assert(provider:get_buff("muscle_regen") == nil)
            assert(provider:get_buff("hostage_taker") == nil)
            assert(provider:get_buff("crew_health_regen") == nil)
        ''')

    def test_reduced_maximum_health_counts_as_full_for_passive_regen(self):
        self.lua.execute('''
            upgrades["player:passive_health_regen"] = true
            upgrades["player:passive_health_regen:value"] = 0.03
            damage._max_health_reduction = 0.3
            damage.health = 30
            damage._health_regen_update_timer = 3
            Hooks.post._upd_health_regen(damage)
            assert(kyohud.hudlist:get_buff("muscle_regen") == nil)
        ''')

    def test_full_health_tolerance_hides_passive_regen(self):
        self.lua.execute('''
            upgrades["player:passive_health_regen"] = true
            upgrades["player:passive_health_regen:value"] = 0.03
            damage._max_health_reduction = 0.3
            damage.health = 29.999999
            damage._health_regen_update_timer = 3
            Hooks.post._upd_health_regen(damage)
            assert(kyohud.hudlist:get_buff("muscle_regen") == nil)
        ''')

    def test_regen_deadline_jitter_does_not_restart_the_visible_timer(self):
        self.lua.execute('''
            upgrades["player:passive_health_regen"] = true
            upgrades["player:passive_health_regen:value"] = 0.03
            damage.health = 50
            damage._health_regen_update_timer = 3
            local activations = 0
            kyohud.hudlist:register_listener("regen_count", "buff", "activate",
                function(event, id) if id == "muscle_regen" then activations = activations + 1 end end)
            Hooks.post._upd_health_regen(damage)
            damage._health_regen_update_timer = 3.000001
            Hooks.post._upd_health_regen(damage)
            assert(activations == 1)
            assert(kyohud.hudlist:get_buff("muscle_regen").expire_t == 103)
        ''')

    def test_bleedout_and_reset_remove_passive_state_and_timers(self):
        self.lua.execute('''
            upgrades["player:passive_health_regen"] = true
            upgrades["player:passive_health_regen:value"] = 0.03
            damage.health = 50
            damage._health_regen_update_timer = 4
            Hooks.post._upd_health_regen(damage)
            assert(kyohud.hudlist:get_buff("muscle_regen"))
            damage.health = 0
            Hooks.pre._check_bleed_out(damage)
            assert(kyohud.hudlist:get_buff("muscle_regen") == nil)
            kyohud.hudlist:reset()
            assert(next(kyohud.hudlist:get_buffs()) == nil)
        ''')


    def test_skill_change_recalculates_at_an_unchanged_health_ratio(self):
        self.lua.execute('''
            upgrades["player:damage_health_ratio_multiplier"] = true
            upgrades["player:damage_health_ratio_multiplier:value"] = 1
            damage.health = 25
            Hooks.post.set_health(damage)
            assert(kyohud.hudlist:get_buff("berserker_aced"))
            function managers.player:player_unit()
                return {character_damage = function() return damage end}
            end
            PlayerManager = {}
            RequiredScript = "lib/managers/playermanager"
        ''')
        self.lua.execute((ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig"))
        self.lua.execute('''
            upgrades["player:damage_health_ratio_multiplier"] = nil
            Hooks.post.check_skills(managers.player)
            assert(kyohud.hudlist:get_buff("berserker_aced") == nil)
        ''')


if __name__ == "__main__":
    unittest.main()