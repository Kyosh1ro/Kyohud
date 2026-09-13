"""Timed-stack and advanced team-state regressions against real Lua chunks."""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
HUDLIST = (ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig")


class HUDListStacksTeamTests(unittest.TestCase):
    def runtime(self, context="lib/managers/hudmanagerpd2"):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute(f'''
            kyohud = {{}}; Kyosh1roHUD = kyohud
            RequiredScript = "{context}"
            Application = {{time = function() return 100 end}}
            TimerManager = {{game = function() return {{time = function() return 100 end}} end}}
            Hooks = {{installed = {{}}, pre = {{}}, post = {{}}}}
            function Hooks:PreHook(class, method, id, fn)
                self.installed[#self.installed + 1] = {{"pre", method, id}}
                self.pre[method] = fn
            end
            function Hooks:PostHook(class, method, id, fn)
                self.installed[#self.installed + 1] = {{"post", method, id}}
                self.post[method] = fn
            end
            PlayerManager = {{}}; PlayerDamage = {{}}
            managers = {{player = {{upgrade_value = function() return 0 end}}}}
            tweak_data = {{upgrades = {{damage_to_hot_data = {{stacking_cooldown = 1.5}}}}}}
        ''')
        lua.execute(HUDLIST)
        return lua

    def test_timed_stacks_normalize_expire_independently_and_reset(self):
        lua = self.runtime()
        lua.execute('''
            local p = kyohud.hudlist
            local events = {}
            p:register_listener("stack-test", "buff", function(event)
                events[#events + 1] = event
            end)
            assert(p:add_timed_stack("biker", {duration = 5, t = 100}) == true)
            assert(p:add_timed_stack("biker", {t = 100, expire_t = 108}) == true)
            local state = p:get_buff("biker")
            assert(state.stack_count == 2 and state.expire_t == 108)
            assert(events[1] == "activate" and events[2] == "set_stack_count")
            assert(state.stacks[1].expire_t == 105 and state.stacks[2].expire_t == 108)
            local first_order = p:get_arrival_order()[1]
            p:update(105)
            state = p:get_buff("biker")
            assert(state.stack_count == 1 and state.stacks[1].expire_t == 108)
            assert(events[#events] == "set_stack_count")
            assert(p:get_arrival_order()[1] == first_order)
            p:update(108)
            assert(p:get_buff("biker") == nil)
            assert(p:add_timed_stack("biker", {duration = -1, t = 100}) == false)
            assert(p:add_timed_stack("biker", {duration = 0/0, t = 100}) == false)
            p:add_timed_stack("biker", {duration = 5, t = 100})
            p:reset()
            assert(p:get_buff("biker") == nil)
        ''')

    def test_catalog_controls_visible_stack_count(self):
        lua = self.runtime()
        lua.execute('''
            local p = kyohud.hudlist
            p:add_timed_stack("biker", {duration = 5, t = 100})
            p:add_timed_stack("grinder", {duration = 5, t = 100})
            assert(p:get_buff("biker").stack_count == 1)
            assert(kyohud.hudlist_catalog.definitions.biker.show_stack_count == true)
            assert(kyohud.hudlist_catalog.definitions.grinder.show_stack_count == true)
            p:activate_team_source(2, "damage_dampener", "team_damage_reduction", 1, 0.9)
            local team = p:get_buff("crew_chief")
            assert(team.stack_count == nil and team.team_level == 1 and team.contributor_count == 1)
        ''')

    def test_biker_uses_native_trigger_diff(self):
        lua = self.runtime("lib/managers/playermanager")
        lua.execute('''
            local manager = {_wild_kill_triggers = {99, 110}}
            Hooks.pre.chk_wild_kill_counter(manager)
            manager._wild_kill_triggers = {110, 115, 120}
            Hooks.post.chk_wild_kill_counter(manager)
            local state = kyohud.hudlist:get_buff("biker")
            assert(state.stack_count == 2)
            assert(state.stacks[1].expire_t == 115 and state.stacks[2].expire_t == 120)
            Hooks.pre.chk_wild_kill_counter(manager)
            Hooks.post.chk_wild_kill_counter(manager)
            assert(state.stack_count == 2)
        ''')

    def test_grinder_uses_new_native_entries_and_keeps_cooldown_distinct(self):
        lua = self.runtime("lib/units/beings/player/playerdamage")
        lua.execute('''
            managers.player.upgrade_value = function() return 2 end
            local damage = {
                _damage_to_hot_stack = {},
                _doh_data = {total_ticks = 3, tick_time = 2},
            }
            Hooks.pre.add_damage_to_hot(damage)
            damage._damage_to_hot_stack = {
                {next_tick = 102, ticks_left = 5},
                {next_tick = 103, ticks_left = 4},
            }
            Hooks.post.add_damage_to_hot(damage)
            local grinder = kyohud.hudlist:get_buff("grinder")
            local cooldown = kyohud.hudlist:get_buff("grinder_debuff")
            assert(grinder.stack_count == 2)
            assert(grinder.stacks[1].expire_t == 109)
            assert(grinder.stacks[2].expire_t == 110)
            assert(cooldown ~= nil and cooldown.expire_t == 101.5)
            assert(grinder ~= cooldown)
        ''')

    def test_grinder_detects_new_entry_after_native_reordering(self):
        lua = self.runtime("lib/units/beings/player/playerdamage")
        lua.execute('''
            local old = {next_tick = 104, ticks_left = 2}
            local damage = {_damage_to_hot_stack = {old}, _doh_data = {tick_time = 2}}
            Hooks.pre.add_damage_to_hot(damage)
            local new = {next_tick = 102, ticks_left = 3}
            damage._damage_to_hot_stack = {new, old}
            Hooks.post.add_damage_to_hot(damage)
            local grinder = kyohud.hudlist:get_buff("grinder")
            assert(grinder.stack_count == 1 and grinder.stacks[1].expire_t == 106)
        ''')

    def test_team_contributors_converge_select_max_and_remove_by_peer(self):
        lua = self.runtime()
        lua.execute('''
            local p = kyohud.hudlist
            assert(p:activate_team_source(2, "damage_dampener", "team_damage_reduction", 1, 0.9))
            assert(p:activate_team_source(3, "health", "hostage_multiplier", 9, 0.8))
            assert(p:activate_team_source(4, "stamina", "hostage_multiplier", 9, 0.7))
            local chief = p:get_buff("crew_chief")
            assert(chief.team_level == 9 and chief.value == 0.8)
            assert(chief.contributor_count == 3 and chief.stack_count == nil)
            assert(p:remove_team_sources_for_peer(3) == 1)
            chief = p:get_buff("crew_chief")
            assert(chief.team_level == 9 and chief.value == 0.7 and chief.contributor_count == 2)
            assert(p:remove_team_sources_for_peer(4) == 1)
            chief = p:get_buff("crew_chief")
            assert(chief.team_level == 1 and chief.value == 0.9)
            assert(p:remove_team_sources_for_peer(2) == 1)
            assert(p:get_buff("crew_chief") == nil)
            assert(p:activate_team_source(-1, "health", "hostage_multiplier", 9, 1) == false)
            assert(p:activate_team_source(2, "unknown", "unknown", 1, 1) == false)
        ''')

    def test_contexts_are_isolated_idempotent_and_nil_dofile_safe(self):
        player = self.runtime("lib/managers/playermanager")
        player.execute('''
            saved_hook_count = #Hooks.installed
            assert(Hooks.pre.chk_wild_kill_counter and Hooks.post.chk_wild_kill_counter)
            assert(Hooks.pre.add_damage_to_hot == nil)
        ''')
        player.execute(HUDLIST)
        player.execute('assert(#Hooks.installed == saved_hook_count)')
        damage = self.runtime("lib/units/beings/player/playerdamage")
        damage.execute('''
            assert(Hooks.pre.add_damage_to_hot and Hooks.post.add_damage_to_hot)
            assert(Hooks.pre.chk_wild_kill_counter == nil)
            assert(HUDList == nil and HUDListManager == nil and GameInfoManager == nil)
            assert(managers.gameinfo == nil)
        ''')


if __name__ == "__main__":
    unittest.main()
