"""Contextual PAYDAY 2 producer regressions for the autonomous HUDList provider."""
from pathlib import Path
import json
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
HUDLIST = (ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig")


class HUDListGameHookTests(unittest.TestCase):
    def runtime_for(self, required_script, class_setup):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute(f'''
            kyohud = {{}}
            Kyosh1roHUD = kyohud
            RequiredScript = "{required_script}"
            Application = {{time = function() return 100 end}}
            Hooks = {{installed = {{}}, callbacks = {{}}}}
            function Hooks:PostHook(class, method, id, callback)
                self.installed[#self.installed + 1] = {{"post", method, id}}
                self.callbacks[method] = callback
            end
            function Hooks:PreHook(class, method, id, callback)
                self.installed[#self.installed + 1] = {{"pre", method, id}}
                self.callbacks[method] = callback
            end
            {class_setup}
        ''')
        lua.execute(HUDLIST)
        return lua

    def test_temporary_property_activation_reads_native_state_after_success(self):
        lua = self.runtime_for(
            "lib/utils/temporarypropertymanager",
            "TemporaryPropertyManager = {}",
        )
        lua.execute('''
            assert(#Hooks.installed == 2)
            assert(Hooks.installed[1][1] == "post")
            assert(Hooks.installed[1][2] == "activate_property")
            assert(Hooks.installed[2][2] == "remove_property")

            local manager = {_properties = {}}
            -- A rejected/failed native operation leaves no state for the PostHook.
            Hooks.callbacks.activate_property(manager, "bloodthirst_reload_speed", 8, 1.5)
            assert(kyohud.hudlist:get_buffs().bloodthirst_aced == nil)

            manager._properties.bloodthirst_reload_speed = {1.5, 108}
            Hooks.callbacks.activate_property(manager, "bloodthirst_reload_speed", 8, 1.5)
            local buff = kyohud.hudlist:get_buffs().bloodthirst_aced
            assert(buff ~= nil)
            assert(buff.t == 100 and buff.expire_t == 108 and buff.duration == 8)
            assert(buff.value == 1.5)
            assert(buff.category == "property")
            assert(buff.upgrade == "bloodthirst_reload_speed" and buff.level == 1)

            manager._properties.bloodthirst_reload_speed = nil
            Hooks.callbacks.remove_property(manager, "bloodthirst_reload_speed")
            assert(kyohud.hudlist:get_buffs().bloodthirst_aced == nil)
        ''')

    def test_cooldown_uses_native_absolute_deadline_and_strict_catalog_mapping(self):
        lua = self.runtime_for(
            "lib/managers/playermanager",
            "PlayerManager = {}",
        )
        lua.execute('''
            local manager = {
                _global = {cooldown_upgrades = {cooldown = {
                    long_dis_revive = {cooldown_time = 120},
                }}},
            }
            function manager:upgrade_level(category, upgrade, default) return 1 end

            Hooks.callbacks.disable_cooldown_upgrade(
                manager, "cooldown", "long_dis_revive"
            )
            local buff = kyohud.hudlist:get_buffs().inspire_revive_debuff
            assert(buff ~= nil)
            assert(buff.t == 100 and buff.expire_t == 120 and buff.duration == 20)
            assert(buff.category == "cooldown" and buff.upgrade == "long_dis_revive")

            manager._global.cooldown_upgrades.cooldown.unknown = {cooldown_time = 130}
            Hooks.callbacks.disable_cooldown_upgrade(manager, "cooldown", "unknown")
            assert(kyohud.hudlist:get_buffs().unknown == nil)

            kyohud.hudlist:update(120)
            assert(kyohud.hudlist:get_buffs().inspire_revive_debuff == nil)
        ''')

    def test_player_properties_activate_update_and_remove_only_catalogued_names(self):
        lua = self.runtime_for(
            "lib/managers/playermanager",
            "PlayerManager = {}",
        )
        lua.execute('''
            local manager = {_properties = {_properties = {}}}
            manager._properties._properties.trigger_happy = 1.4
            Hooks.callbacks.set_property(manager, "trigger_happy", 1.4)
            local buff = kyohud.hudlist:get_buffs().trigger_happy
            assert(buff ~= nil and buff.value == 1.4)
            assert(buff.category == "property" and buff.upgrade == "trigger_happy")

            manager._properties._properties.trigger_happy = 1.6
            Hooks.callbacks.set_property(manager, "trigger_happy", 1.6)
            assert(kyohud.hudlist:get_buffs().trigger_happy == buff)
            assert(buff.value == 1.6)

            manager._properties._properties.not_catalogued = 9
            Hooks.callbacks.set_property(manager, "not_catalogued", 9)
            assert(kyohud.hudlist:get_buffs().not_catalogued == nil)

            manager._properties._properties.trigger_happy = nil
            Hooks.callbacks.remove_property(manager, "trigger_happy")
            assert(kyohud.hudlist:get_buffs().trigger_happy == nil)
        ''')

    def test_team_sources_are_kept_per_peer_until_the_last_source_disappears(self):
        lua = self.runtime_for(
            "lib/managers/playermanager",
            "PlayerManager = {}",
        )
        lua.execute('''
            local manager = {_global = {
                team_upgrades = {damage_dampener = {team_damage_reduction = 1}},
                synced_team_upgrades = {},
            }}
            function manager:team_upgrade_value() return 0.92 end

            local upgrade = {
                category = "damage_dampener",
                upgrade = "team_damage_reduction",
                value = 1,
            }
            Hooks.callbacks.aquire_team_upgrade(manager, upgrade)
            local buff = kyohud.hudlist:get_buffs().crew_chief
            assert(buff ~= nil and buff.value == 0.92)
            assert(kyohud.hudlist:get_team_source_count("crew_chief") == 1)

            manager._global.synced_team_upgrades[7] = {
                damage_dampener = {team_damage_reduction = 1},
            }
            Hooks.callbacks.add_synced_team_upgrade(
                manager, 7, "damage_dampener", "team_damage_reduction", 1
            )
            manager._global.synced_team_upgrades[8] = {
                damage_dampener = {team_damage_reduction = 1},
            }
            Hooks.callbacks.add_synced_team_upgrade(
                manager, 8, "damage_dampener", "team_damage_reduction", 1
            )
            assert(kyohud.hudlist:get_team_source_count("crew_chief") == 3)
            assert(kyohud.hudlist:get_buffs().crew_chief == buff)

            manager._global.team_upgrades.damage_dampener.team_damage_reduction = nil
            Hooks.callbacks.unaquire_team_upgrade(manager, upgrade)
            assert(kyohud.hudlist:get_buffs().crew_chief ~= nil)
            assert(kyohud.hudlist:get_team_source_count("crew_chief") == 2)

            local peer7 = {id = function() return 7 end}
            Hooks.callbacks.peer_dropped_out(manager, peer7)
            manager._global.synced_team_upgrades[7] = nil
            assert(kyohud.hudlist:get_buffs().crew_chief ~= nil)
            assert(kyohud.hudlist:get_team_source_count("crew_chief") == 1)

            local peer8 = {id = function() return 8 end}
            Hooks.callbacks.peer_dropped_out(manager, peer8)
            assert(kyohud.hudlist:get_buffs().crew_chief == nil)
            assert(kyohud.hudlist:get_team_source_count("crew_chief") == 0)
        ''')

    def test_partner_in_crime_follows_native_minion_count_boundaries(self):
        lua = self.runtime_for(
            "lib/managers/playermanager",
            "PlayerManager = {}",
        )
        lua.execute('''
            local manager = {_local_player_minions = 1}
            function manager:has_category_upgrade(category, upgrade)
                return category == "player" and (
                    upgrade == "minion_master_speed_multiplier"
                    or upgrade == "minion_master_health_multiplier"
                )
            end

            Hooks.callbacks.count_up_player_minions(manager)
            assert(kyohud.hudlist:get_buffs().partner_in_crime ~= nil)
            assert(kyohud.hudlist:get_buffs().partner_in_crime_aced ~= nil)

            manager._local_player_minions = 0
            Hooks.callbacks.count_down_player_minions(manager)
            assert(kyohud.hudlist:get_buffs().partner_in_crime == nil)
            assert(kyohud.hudlist:get_buffs().partner_in_crime_aced == nil)
        ''')

    def test_messiah_counter_follows_post_mutation_charge_state(self):
        lua = self.runtime_for(
            "lib/managers/playermanager",
            "PlayerManager = {}",
        )
        lua.execute('''
            local manager = {_messiah_charges = 2}
            Hooks.callbacks.check_skills(manager)
            local buff = kyohud.hudlist:get_buffs().messiah
            assert(buff ~= nil and buff.stack_count == 2)

            manager._messiah_charges = 1
            Hooks.callbacks.use_messiah_charge(manager)
            assert(kyohud.hudlist:get_buffs().messiah == buff)
            assert(buff.stack_count == 1)

            manager._messiah_charges = 2
            Hooks.callbacks._on_messiah_recharge_event(manager)
            assert(buff.stack_count == 2)

            manager._messiah_charges = 0
            Hooks.callbacks.use_messiah_charge(manager)
            assert(kyohud.hudlist:get_buffs().messiah == nil)
        ''')

    def test_received_inspire_basic_uses_player_morale_boost_lifetime(self):
        lua = self.runtime_for(
            "lib/units/beings/player/playermovement",
            "PlayerMovement = {}; tweak_data = {upgrades = {morale_boost_time = 10}}",
        )
        lua.execute('''
            assert(#Hooks.installed == 2)
            assert(Hooks.installed[1][2] == "on_morale_boost")
            assert(Hooks.installed[2][2] == "clbk_morale_boost_expire")

            Hooks.callbacks.on_morale_boost({})
            local buff = kyohud.hudlist:get_buffs().inspire
            assert(buff ~= nil)
            assert(buff.t == 100 and buff.expire_t == 110 and buff.duration == 10)

            Application.time = function() return 104 end
            Hooks.callbacks.on_morale_boost({})
            local refreshed = kyohud.hudlist:get_buffs().inspire
            assert(refreshed == buff, "refresh must reuse the existing buff entry")
            assert(refreshed.t == 104 and refreshed.expire_t == 114
                and refreshed.duration == 10)

            Hooks.callbacks.clbk_morale_boost_expire({})
            assert(kyohud.hudlist:get_buffs().inspire == nil)
        ''')

    def test_sent_inspire_basic_starts_boost_cooldown_only_for_inspire_shouts(self):
        lua = self.runtime_for(
            "lib/units/beings/player/states/playerstandard",
            """
            PlayerStandard = {}
            tweak_data = {upgrades = {morale_boost_base_cooldown = 3.5}}
            managers = {player = {
                upgrade_value = function(self, category, upgrade, default)
                    assert(category == "player")
                    assert(upgrade == "morale_boost_cooldown_multiplier")
                    return 0.5
                end,
            }}
            """,
        )
        lua.execute('''
            assert(#Hooks.installed == 1)
            assert(Hooks.installed[1][2] == "_do_action_intimidate")

            Hooks.callbacks._do_action_intimidate({}, 100, "cmd_come")
            assert(kyohud.hudlist:get_buffs().inspire_debuff == nil)

            Hooks.callbacks._do_action_intimidate({}, 100, "cmd_gogo")
            local buff = kyohud.hudlist:get_buffs().inspire_debuff
            assert(buff ~= nil)
            assert(buff.t == 100 and buff.expire_t == 101.75 and buff.duration == 1.75)

            Application.time = function() return 101 end
            Hooks.callbacks._do_action_intimidate({}, 101, "cmd_get_up")
            local refreshed = kyohud.hudlist:get_buffs().inspire_debuff
            assert(refreshed == buff, "refresh must reuse the existing cooldown entry")
            assert(refreshed.t == 101 and refreshed.expire_t == 102.75
                and refreshed.duration == 1.75,
                "the current game clock must renew the cooldown deadline")
        ''')

    def test_contexts_are_explicit_idempotent_and_keep_shared_state(self):
        lua = self.runtime_for("lib/unknown/context", "PlayerManager = {}; TemporaryPropertyManager = {}")
        lua.execute('assert(#Hooks.installed == 0)')
        lua.execute('''
            kyohud.hudlist:event("buff", "activate", "keep_me", {})
            RequiredScript = "lib/managers/playermanager"
        ''')
        lua.execute(HUDLIST)
        lua.execute('assert(#Hooks.installed == 25)')
        lua.execute(HUDLIST)
        lua.execute('assert(#Hooks.installed == 25)')
        lua.execute('RequiredScript = "lib/utils/temporarypropertymanager"')
        lua.execute(HUDLIST)
        lua.execute('''
            assert(#Hooks.installed == 27)
            assert(kyohud.hudlist:get_buffs().keep_me ~= nil)
            assert(HUDList == nil and HUDListManager == nil and GameInfoManager == nil)
        ''')

    def test_mod_registers_only_the_required_provider_contexts(self):
        metadata = json.loads((ROOT / "mod.txt").read_text(encoding="utf-8-sig"))
        contexts = [
            hook["hook_id"] for hook in metadata["hooks"]
            if hook["script_path"] == "lua/hudlist.lua"
        ]
        self.assertEqual(contexts, [
            "lib/managers/hudmanagerpd2",
            "lib/managers/playermanager",
            "lib/units/beings/player/playerdamage",
            "lib/units/beings/player/playerinventory",
            "lib/utils/temporarypropertymanager",
            "lib/units/beings/player/playermovement",
            "lib/units/beings/player/states/playerstandard",
        ])

    def test_non_finite_native_deadlines_are_ignored(self):
        lua = self.runtime_for(
            "lib/managers/playermanager",
            "PlayerManager = {}",
        )
        lua.execute('''
            local manager = {
                _temporary_upgrades = {temporary = {
                    overkill_damage_multiplier = {expire_time = math.huge},
                }},
                _global = {cooldown_upgrades = {cooldown = {
                    long_dis_revive = {cooldown_time = math.huge},
                }}},
            }
            function manager:upgrade_level() return 1 end
            function manager:temporary_upgrade_value() return 1.75 end
            Hooks.callbacks.activate_temporary_upgrade(
                manager, "temporary", "overkill_damage_multiplier"
            )
            Hooks.callbacks.disable_cooldown_upgrade(
                manager, "cooldown", "long_dis_revive"
            )
            assert(kyohud.hudlist:get_buffs().overkill == nil)
            assert(kyohud.hudlist:get_buffs().inspire_revive_debuff == nil)
        ''')

    def test_temporary_upgrade_level_refresh_and_unknown_mapping_boundaries(self):
        lua = self.runtime_for("lib/managers/playermanager", "PlayerManager = {}")
        lua.execute('''
            local manager = {_temporary_upgrades = {temporary = {
                passive_revive_damage_reduction = {
                    expire_time = 110, upgrade_value = 0.8,
                },
            }}}
            function manager:upgrade_level() return 2 end
            function manager:temporary_upgrade_value() return 0.8 end
            Hooks.callbacks.activate_temporary_upgrade_by_level(
                manager, "temporary", "passive_revive_damage_reduction", 2
            )
            local buff = kyohud.hudlist:get_buffs().pain_killer_aced
            assert(buff ~= nil and buff.level == 2 and buff.value == 0.8)
            assert(kyohud.hudlist:get_arrival_order()[1] == "pain_killer_aced")
            manager._temporary_upgrades.temporary.passive_revive_damage_reduction.expire_time = 115
            Hooks.callbacks.activate_temporary_upgrade_by_level(
                manager, "temporary", "passive_revive_damage_reduction", 2
            )
            assert(kyohud.hudlist:get_buffs().pain_killer_aced == buff)
            assert(buff.expire_t == 115 and #kyohud.hudlist:get_arrival_order() == 1)
            Hooks.callbacks.activate_temporary_upgrade_by_level(
                manager, "temporary", "unknown_upgrade", 1
            )
            assert(#kyohud.hudlist:get_arrival_order() == 1)
            Hooks.callbacks.deactivate_temporary_upgrade(
                manager, "temporary", "passive_revive_damage_reduction"
            )
            assert(kyohud.hudlist:get_buffs().pain_killer_aced == nil)
        ''')

    def test_real_chunk_survives_nil_dofile_and_does_not_touch_external_hud(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/playermanager"
            Application = {time = function() return 100 end}
            PlayerManager = {}
            Hooks = {count = 0}
            function Hooks:PostHook(...) self.count = self.count + 1 end
            function Hooks:PreHook(...) self.count = self.count + 1 end
            HUDList = {BuffItemBase = {MAP = {external = {keep = true}}}}
            HUDListManager = {BUFFS = {external = true}}
            GameInfoManager = {external = true}
            local native_dofile = dofile
            dofile = function(path)
                native_dofile(path)
                return nil
            end
        ''')
        lua.execute(HUDLIST)
        lua.execute('''
            assert(kyohud.hudlist ~= nil and kyohud.hudlist_catalog ~= nil)
            assert(Hooks.count == 25)
            assert(HUDList.BuffItemBase.MAP.external.keep == true)
            assert(HUDListManager.BUFFS.external == true)
            assert(GameInfoManager.external == true)
        ''')


if __name__ == "__main__":
    unittest.main()
