"""Modern dynamic buff producers executed against the real Lua provider chunk."""
from pathlib import Path
import json
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
HUDLIST = (ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig")


class HUDListModernBuffTests(unittest.TestCase):
    def runtime(self, context="lib/managers/playermanager", class_setup="PlayerManager = {}"):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute(f'''
            kyohud = {{}}; Kyosh1roHUD = kyohud
            RequiredScript = "{context}"
            app_time = 100
            Application = {{time = function() return app_time end}}
            TimerManager = {{game = function() return {{time = function() return app_time end}} end}}
            Hooks = {{installed = {{}}, pre = {{}}, post = {{}}}}
            function Hooks:PreHook(class, method, id, fn)
                self.installed[#self.installed + 1] = {{"pre", method, id}}
                self.pre[method] = fn
            end
            function Hooks:PostHook(class, method, id, fn)
                self.installed[#self.installed + 1] = {{"post", method, id}}
                self.post[method] = fn
            end
            alive = function(unit) return unit ~= nil and unit.alive ~= false end
            managers = {{
                network = {{session = function() return {{local_peer = function() return {{id = function() return 1 end}} end}} end}},
                blackmarket = {{equipped_grenade = function() return "chico_injector" end}},
                player = nil,
            }}
            tweak_data = {{upgrades = {{
                max_total_cocaine_stacks = 600,
                cocaine_stacks_decay_t = 8,
                values = {{player = {{dodge_shot_gain = {{{{0.2, 4}}}}}}}},
            }}}}
            {class_setup}
        ''')
        lua.execute(HUDLIST)
        return lua

    def test_maniac_uses_native_best_stack_progress_and_separate_decay(self):
        lua = self.runtime()
        lua.execute('''
            local manager = {
                _global = {synced_cocaine_stacks = {
                    [1] = {amount = 120, in_use = true, power_level = 1},
                    [2] = {amount = 300, in_use = true, power_level = 1},
                    [3] = {amount = 500, in_use = false, power_level = 1},
                }},
                _damage_dealt_to_cops_decay_t = 108,
            }
            function manager:get_best_cocaine_damage_absorption(peer_id)
                assert(peer_id == 1)
                return 3, 2
            end
            function manager:get_local_cocaine_damage_absorption_max() return 6 end
            Hooks.post.set_synced_cocaine_stacks(manager, 2, 300, true, 1, 1)
            local buff = kyohud.hudlist:get_buff("maniac")
            assert(buff and buff.value == 3 and buff.progress == 0.5)
            assert(buff.best_peer == 2 and buff.provenance == "synchronized")
            local decay = kyohud.hudlist:get_buff("maniac_debuff")
            assert(decay and decay.expire_t == 108 and decay ~= buff)
            local first = kyohud.hudlist:get_buffs().maniac

            manager.get_best_cocaine_damage_absorption = function() return 2, 1 end
            manager.get_local_cocaine_damage_absorption_max = function() return 4 end
            manager._damage_dealt_to_cops_decay_t = 110
            Hooks.post.set_synced_cocaine_stacks(manager, 1, 120, true, 1, 1)
            assert(kyohud.hudlist:get_buffs().maniac == first)
            assert(first.progress == 0.5 and first.best_peer == 1)
            assert(#kyohud.hudlist:get_arrival_order() == 2)

            manager.get_best_cocaine_damage_absorption = function() return 0, 0 end
            Hooks.post.set_synced_cocaine_stacks(manager, 2, 0, true, 1, 1)
            assert(kyohud.hudlist:get_buff("maniac") == nil)
            assert(kyohud.hudlist:get_buff("maniac_debuff") ~= nil)
        ''')

    def test_maniac_ignores_missing_network_data(self):
        lua = self.runtime()
        lua.execute('''
            managers.network = nil
            local manager = {_global = {synced_cocaine_stacks = {}}}
            Hooks.post.set_synced_cocaine_stacks(manager, 2, 10, true, 1, 1)
            assert(kyohud.hudlist:get_buff("maniac") == nil)
        ''')

    def test_sicario_uses_post_state_and_verified_cooldown(self):
        lua = self.runtime()
        lua.execute('''
            local manager = {_dodge_shot_gain_value = 0.2}
            function manager:upgrade_value(category, upgrade, default)
                if category == "player" and upgrade == "sicario_multiplier" then return 2 end
                return default
            end
            Hooks.post._dodge_shot_gain(manager, 0.2)
            local dodge = kyohud.hudlist:get_buff("sicario_dodge")
            local cooldown = kyohud.hudlist:get_buff("sicario_dodge_debuff")
            assert(dodge and dodge.value == 0.4)
            assert(cooldown and cooldown.duration == 4 and cooldown.expire_t == 104)
            local first = kyohud.hudlist:get_buffs().sicario_dodge_debuff
            app_time = 101
            manager._dodge_shot_gain_value = 0.4
            Hooks.post._dodge_shot_gain(manager, 0.4)
            assert(kyohud.hudlist:get_buffs().sicario_dodge_debuff == first)
            assert(first.expire_t == 105)
            manager._dodge_shot_gain_value = 0
            Hooks.post._dodge_shot_gain(manager, 0)
            assert(kyohud.hudlist:get_buff("sicario_dodge") == nil)
            assert(kyohud.hudlist:get_buff("sicario_dodge_debuff") ~= nil)
        ''')

    def test_sicario_ignores_invalid_duration(self):
        lua = self.runtime()
        lua.execute('''
            tweak_data.upgrades.values.player.dodge_shot_gain[1][2] = 0/0
            local manager = {_dodge_shot_gain_value = 0.2}
            function manager:upgrade_value() return 1 end
            Hooks.post._dodge_shot_gain(manager, 0.2)
            assert(kyohud.hudlist:get_buff("sicario_dodge") ~= nil)
            assert(kyohud.hudlist:get_buff("sicario_dodge_debuff") == nil)
        ''')

    def test_copycat_paths_are_distinct_and_headshots_refresh_once(self):
        lua = self.runtime()
        lua.execute('''
            local manager = {
                _temporary_upgrades = {temporary = {mrwi_health_invulnerable = {expire_time = 102}}},
                _properties = {_properties = {}},
                _on_headshot_dealt_t = 102,
            }
            function manager:upgrade_level(category, upgrade, default) return 1 end
            function manager:temporary_upgrade_value() return 0.5 end
            function manager:upgrade_value(category, upgrade, default)
                if category == "temporary" and upgrade == "mrwi_health_invulnerable" then
                    return {0.5, 2, 15}
                end
                if category == "player" and upgrade == "headshot_regen_health_bonus" then return 1 end
                return default
            end
            Hooks.post.activate_temporary_upgrade(manager, "temporary", "mrwi_health_invulnerable")
            local active = kyohud.hudlist:get_buff("copycat_health_invul")
            local debuff = kyohud.hudlist:get_buff("copycat_health_invul_debuff")
            assert(active and active.expire_t == 102)
            assert(debuff and debuff.expire_t == 115 and debuff ~= active)

            TemporaryPropertyManager = {}
            RequiredScript = "lib/utils/temporarypropertymanager"
            dofile(ModPath .. "lua/hudlist.lua")
            local temporary = {_properties = {mrwi_health_invulnerable = {true, 115}}}
            Hooks.post.activate_property(temporary, "mrwi_health_invulnerable", 15, true)
            local passive = kyohud.hudlist:get_buff("copycat_health_invul_passive")
            assert(passive and passive.expire_t == 115 and passive ~= active)

            local refreshes = 0
            kyohud.hudlist:register_listener("copycat-headshot", "buff", "activate", function(_, id)
                if id == "copycat_health_shot_debuff" then refreshes = refreshes + 1 end
            end)
            Hooks.post.on_headshot_dealt(manager)
            local shot = kyohud.hudlist:get_buff("copycat_health_shot_debuff")
            assert(shot and shot.expire_t == 102 and refreshes == 1)
            Hooks.post.on_headshot_dealt(manager)
            assert(refreshes == 2 and #kyohud.hudlist:get_arrival_order() == 4)

            temporary._properties.mrwi_health_invulnerable = nil
            Hooks.post.remove_property(temporary, "mrwi_health_invulnerable")
            assert(kyohud.hudlist:get_buff("copycat_health_invul_passive") == nil)
            Hooks.pre.deactivate_temporary_upgrade(manager, "temporary", "mrwi_health_invulnerable")
            assert(kyohud.hudlist:get_buff("copycat_health_invul") == nil)
            assert(kyohud.hudlist:get_buff("copycat_health_invul_debuff") ~= nil)
        ''')

    def test_dynamic_cooldowns_are_allowlisted_accelerated_and_switched(self):
        lua = self.runtime()
        lua.execute('''
            local equipped = "chico_injector"
            managers.blackmarket.equipped_grenade = function() return equipped end
            local manager = {_timers = {replenish_grenades = {t = 130}}}
            Hooks.post.replenish_grenades(manager, 30)
            local kingpin = kyohud.hudlist:get_buff("chico_injector_debuff")
            assert(kingpin and kingpin.expire_t == 130 and kingpin.duration == 30)
            local first = kyohud.hudlist:get_buffs().chico_injector_debuff

            app_time = 105
            manager._timers.replenish_grenades.t = 120
            Hooks.post.speed_up_grenade_cooldown(manager, 10)
            assert(kyohud.hudlist:get_buffs().chico_injector_debuff == first)
            assert(first.expire_t == 120 and first.duration == 15)

            equipped = "copr_ability"
            manager._timers.replenish_grenades.t = 140
            Hooks.post.replenish_grenades(manager, 35)
            assert(kyohud.hudlist:get_buff("chico_injector_debuff") == nil)
            assert(kyohud.hudlist:get_buff("copr_ability_debuff") ~= nil)
            Hooks.post._on_grenade_cooldown_end(manager)
            assert(kyohud.hudlist:get_buff("copr_ability_debuff") == nil)

            equipped = "unknown_modded_ability"
            manager._timers.replenish_grenades.t = 150
            Hooks.post.replenish_grenades(manager, 45)
            assert(kyohud.hudlist:get_buff("unknown_modded_ability_debuff") == nil)
            assert(kyohud.hudlist_catalog:resolve_dynamic("grenade", equipped) == nil)
            assert(kyohud.hudlist_catalog.dynamic_ids == nil)
        ''')

    def test_custom_cooldown_domain_accepts_only_catalogued_native_upgrades(self):
        lua = self.runtime()
        lua.execute('''
            local manager = {_timers = {
                team_crew_inspire = {t = 160},
                team_unknown = {t = 170},
            }}
            Hooks.post.start_custom_cooldown(manager, "team", "crew_inspire", 60)
            local cooldown = kyohud.hudlist:get_buff("crew_inspire_debuff")
            assert(cooldown and cooldown.t == 100 and cooldown.expire_t == 160)
            Hooks.post.start_custom_cooldown(manager, "team", "unknown", 70)
            assert(kyohud.hudlist:get_buff("unknown_debuff") == nil)
        ''')

    def test_leech_and_kingpin_active_states_remain_separate_from_cooldowns(self):
        lua = self.runtime()
        lua.execute('''
            local manager = {_temporary_upgrades = {temporary = {
                copr_ability = {expire_time = 106},
                chico_injector = {expire_time = 110},
            }}}
            function manager:upgrade_level() return 1 end
            function manager:temporary_upgrade_value(category, upgrade)
                return upgrade == "copr_ability" and 1 or 0.75
            end
            Hooks.post.activate_temporary_upgrade(manager, "temporary", "copr_ability")
            Hooks.post.activate_temporary_upgrade(manager, "temporary", "chico_injector")
            assert(kyohud.hudlist:get_buff("copr_ability").expire_t == 106)
            assert(kyohud.hudlist:get_buff("chico_injector").expire_t == 110)
            Hooks.pre.deactivate_temporary_upgrade(manager, "temporary", "copr_ability")
            Hooks.pre.deactivate_temporary_upgrade(manager, "temporary", "copr_ability")
            assert(kyohud.hudlist:get_buff("copr_ability") == nil)
            assert(kyohud.hudlist:get_buff("chico_injector") ~= nil)
        ''')

    def test_pocket_ecm_tracks_jammer_and_feedback_sources_without_early_removal(self):
        lua = self.runtime(
            "lib/units/beings/player/playerinventory",
            "PlayerManager = {}; PlayerInventory = {}",
        )
        lua.execute('''
            local jammer = {_jammer_data = {effect = "jamming", t = 106}}
            local feedback = {_jammer_data = {effect = "feedback", t = 109}}
            Hooks.post._start_jammer_effect(jammer, 6)
            local buff = kyohud.hudlist:get_buff("pocket_ecm_jammer")
            assert(buff and buff.expire_t == 106 and buff.source_count == 1)
            assert(buff.mode == "jamming")

            Hooks.post._start_feedback_effect(feedback, 9)
            buff = kyohud.hudlist:get_buff("pocket_ecm_jammer")
            assert(buff.expire_t == 109 and buff.source_count == 2)
            assert(buff.mode == "mixed")

            Hooks.pre._stop_jammer_effect(jammer, false)
            jammer._jammer_data = nil
            buff = kyohud.hudlist:get_buff("pocket_ecm_jammer")
            assert(buff and buff.expire_t == 109 and buff.source_count == 1)
            assert(buff.mode == "feedback")
            Hooks.pre._stop_jammer_effect(jammer, false)
            assert(kyohud.hudlist:get_buff("pocket_ecm_jammer") ~= nil)

            Hooks.pre._stop_feedback_effect(feedback, false)
            feedback._jammer_data = nil
            assert(kyohud.hudlist:get_buff("pocket_ecm_jammer") == nil)
            assert(PlayerInventory.get_jammer_time == nil)
        ''')

    def test_pocket_ecm_ignores_failed_or_expired_starts_and_reset_clears_sources(self):
        lua = self.runtime(
            "lib/units/beings/player/playerinventory",
            "PlayerManager = {}; PlayerInventory = {}",
        )
        lua.execute('''
            local inventory = {_jammer_data = nil}
            Hooks.post._start_jammer_effect(inventory, 0)
            assert(kyohud.hudlist:get_buff("pocket_ecm_jammer") == nil)
            inventory._jammer_data = {effect = "jamming", t = 99}
            Hooks.post._start_jammer_effect(inventory, -1)
            assert(kyohud.hudlist:get_buff("pocket_ecm_jammer") == nil)
            inventory._jammer_data.t = 106
            Hooks.post._start_jammer_effect(inventory, 6)
            assert(kyohud.hudlist:get_buff("pocket_ecm_jammer") ~= nil)
            kyohud.hudlist:reset()
            assert(kyohud.hudlist:get_buff("pocket_ecm_jammer") == nil)
            assert(kyohud.hudlist:get_source_count("pocket_ecm_jammer") == 0)
        ''')

    def test_uppers_and_smoke_polling_is_bounded_and_multi_zone_safe(self):
        lua = self.runtime()
        lua.execute('''
            local scans = 0
            FirstAidKitBase = {GetFirstAidKit = function()
                scans = scans + 1
                return scans == 1 and {} or nil
            end}
            local unit = {position = function() return {} end}
            local smoke1 = {
                _timer = 5,
                alive = function() return true end,
                is_in_smoke = function() return true end,
                dodge_bonus = function() return 0.1 end,
                mine = function() return false end,
            }
            local smoke2 = {
                _timer = 8,
                alive = function() return true end,
                is_in_smoke = function() return true end,
                dodge_bonus = function() return 0.2 end,
                mine = function() return false end,
            }
            local manager = {screens = {smoke1, smoke2}}
            function manager:player_unit() return unit end
            function manager:has_category_upgrade(category, upgrade)
                return category == "first_aid_kit" and upgrade == "first_aid_kit_auto_recovery"
            end
            function manager:smoke_screens() return self.screens end

            Hooks.post.update(manager, 100, 0.01)
            assert(scans == 1 and kyohud.hudlist:get_buff("uppers") ~= nil)
            local smoke = kyohud.hudlist:get_buff("smoke_screen_grenade")
            assert(smoke and smoke.source_count == 2 and math.abs(smoke.value - 0.3) < 0.000001)
            assert(smoke.expire_t == 108)
            assert(kyohud.hudlist_catalog.definitions.smoke_screen_grenade.show_stack_count ~= true)
            Hooks.post.update(manager, 100.1, 0.1)
            assert(scans == 1)

            manager.screens = {smoke2}
            Hooks.post.update(manager, 100.3, 0.2)
            assert(kyohud.hudlist:get_buff("uppers") == nil)
            assert(kyohud.hudlist:get_buff("smoke_screen_grenade") ~= nil)
            manager.screens = {}
            Hooks.post.update(manager, 100.6, 0.3)
            assert(kyohud.hudlist:get_buff("smoke_screen_grenade") == nil)

            manager.has_category_upgrade = function() return false end
            Hooks.post.update(manager, 100.9, 0.3)
            assert(scans == 3)
        ''')

    def test_uppers_cooldown_requires_a_real_native_transition(self):
        lua = self.runtime(
            "lib/units/beings/player/playerdamage",
            "PlayerManager = {}; PlayerDamage = {}",
        )
        lua.execute('''
            local damage = {_uppers_elapsed = 20, _UPPERS_COOLDOWN = 20}
            Hooks.pre._check_bleed_out(damage)
            Hooks.post._check_bleed_out(damage)
            assert(kyohud.hudlist:get_buff("uppers_debuff") == nil)
            Hooks.pre._check_bleed_out(damage)
            damage._uppers_elapsed = 100
            Hooks.post._check_bleed_out(damage)
            local cooldown = kyohud.hudlist:get_buff("uppers_debuff")
            assert(cooldown and cooldown.expire_t == 120 and cooldown.duration == 20)
        ''')

    def test_contexts_install_exact_non_destructive_hooks_and_no_tag_team_listener(self):
        expected = {
            "lib/managers/playermanager": 25,
            "lib/units/beings/player/playerdamage": 4,
            "lib/units/beings/player/playerinventory": 4,
            "lib/utils/temporarypropertymanager": 2,
            "lib/player_actions/skills/playeractiontagteam": 0,
            "lib/unknown/context": 0,
        }
        setups = {
            "lib/managers/playermanager": "PlayerManager = {}",
            "lib/units/beings/player/playerdamage": "PlayerManager = {}; PlayerDamage = {}",
            "lib/units/beings/player/playerinventory": "PlayerManager = {}; PlayerInventory = {}",
            "lib/utils/temporarypropertymanager": "PlayerManager = {}; TemporaryPropertyManager = {}",
            "lib/player_actions/skills/playeractiontagteam": "PlayerManager = {}; PlayerAction = {TagTeam = {}, TagTeamTagged = {}}",
            "lib/unknown/context": "PlayerManager = {}",
        }
        for context, count in expected.items():
            with self.subTest(context=context):
                lua = self.runtime(context, setups[context])
                self.assertEqual(count, len(lua.globals().Hooks.installed))
                lua.execute(HUDLIST)
                self.assertEqual(count, len(lua.globals().Hooks.installed))

        source = HUDLIST
        self.assertNotIn("PlayerAction.TagTeam.Function =", source)
        self.assertNotIn("PlayerAction.TagTeamTagged.Function =", source)
        self.assertNotIn("CopDamage.register_listener", source)
        self.assertNotIn("get_jammer_time =", source)
        self.assertNotIn("managers.gameinfo", source)

    def test_mod_contexts_and_script_paths_are_exact(self):
        metadata = json.loads((ROOT / "mod.txt").read_text(encoding="utf-8-sig"))
        contexts = [
            hook["hook_id"] for hook in metadata["hooks"]
            if hook["script_path"] == "lua/hudlist.lua"
        ]
        self.assertEqual([
            "lib/managers/hudmanagerpd2",
            "lib/managers/playermanager",
            "lib/units/beings/player/playerdamage",
            "lib/units/beings/player/playerinventory",
            "lib/utils/temporarypropertymanager",
        ], contexts)
        for hook in metadata["hooks"]:
            self.assertTrue((ROOT / hook["script_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
