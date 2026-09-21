"""Feature 9 — final hardening regressions for the autonomous HUDList provider.

Covers:
  (1) end-to-end traceability: producer -> catalog -> presentation
  (2) orphan detection: product IDs, routes, catalog definitions
  (3) reset correctness: heist, bleedout, custody, menu return
  (4) peer drop: immediate recalculation of team buffs
  (5) host / client / offline coverage
  (6) no VanillaHUD+ globals created or consulted
  (7) hook audit: idempotent install, no double wraps, hot-path clean
  (8) expiration / cooldown boundaries, replacement, retrigger
  (9) SuperBLT log: bounded diagnostics, no spam
 (10) documented limits match reality
"""
from pathlib import Path
import json
import re
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
HUDLIST = (ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig")
CATALOG = (ROOT / "lua" / "hudlist_catalog.lua").read_text(encoding="utf-8-sig")
CORE = (ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig")
PRESENTATION = (ROOT / "lua" / "ky_buff_presentation.lua").read_text(encoding="utf-8-sig")


def _catalog_runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute('''
        kyohud = {}; Kyosh1roHUD = kyohud
        RequiredScript = "lib/managers/hudmanagerpd2"
        Application = {time = function() return 100 end}
        Hooks = {callbacks = {}, pre_callbacks = {}}
        function Hooks:PostHook(class, method, id, callback)
            self.callbacks[id] = callback
            self.callbacks[method] = callback
        end
        function Hooks:PreHook(class, method, id, callback)
            self.pre_callbacks[id] = callback
            self.pre_callbacks[method] = callback
        end
        function Hooks:Add(...) end
        HUDManager = {}; PlayerManager = {}; managers = {}; tweak_data = {}
        function Vector3(...) return {...} end
        function log(...) end
        function alive(value) return value ~= nil end
        local function color()
            return {with_alpha = function(self) return self end}
        end
        Color = setmetatable({white = color(), black = color()}, {
            __call = function(...) return color() end
        })
        TimerManager = {game = function()
            return {time = function() return 100 end}
        end}
    ''')
    return lua


class TraceabilityAuditTests(unittest.TestCase):
    def test_every_direct_literal_resolves_to_a_definition_with_visual_metadata(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute(CORE)
        lua.execute((ROOT / "lua" / "ky_combat_medals.lua").read_text(encoding="utf-8-sig"))
        lua.execute('''
            local catalog = kyohud.hudlist_catalog
            for id in pairs(catalog.direct_ids.literals) do
                local resolved = catalog:resolve_alias(id)
                local def = catalog.definitions[resolved]
                assert(def ~= nil, "direct literal " .. id
                    .. " (resolved: " .. resolved .. ") has no definition")
            end
        ''')

    def test_every_mapping_output_resolves_to_a_definition(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local catalog = kyohud.hudlist_catalog
            local function check(value)
                if type(value) == "string" then
                    local resolved = catalog:resolve_alias(value)
                    assert(catalog.definitions[resolved] ~= nil,
                        "mapping target " .. value
                        .. " (resolved: " .. resolved .. ") has no definition")
                elseif type(value) == "table" then
                    if type(value.id) == "string" then
                        local resolved = catalog:resolve_alias(value.id)
                        assert(catalog.definitions[resolved] ~= nil,
                            "team mapping target " .. value.id
                            .. " (resolved: " .. resolved .. ") has no definition")
                    else
                        for _, inner in pairs(value) do check(inner) end
                    end
                end
            end
            for _, group in pairs(catalog.mappings) do
                for _, mapping in pairs(group) do check(mapping) end
            end
        ''')

    def test_every_route_target_resolves_to_a_definition(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local catalog = kyohud.hudlist_catalog
            for source_id, targets in pairs(catalog.routes) do
                for _, target_id in ipairs(targets) do
                    local resolved = catalog:resolve_alias(target_id)
                    assert(catalog.definitions[resolved] ~= nil,
                        "route target " .. target_id
                        .. " (from " .. source_id
                        .. ", resolved: " .. resolved .. ") has no definition")
                end
            end
        ''')

    def test_every_alias_target_is_a_known_definition(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local catalog = kyohud.hudlist_catalog
            for from_id, to_id in pairs(catalog.aliases) do
                assert(catalog.definitions[to_id] ~= nil,
                    "alias " .. from_id .. " -> " .. to_id .. " has no definition")
            end
        ''')

    def test_every_dynamic_id_resolves_to_a_known_public_id(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local catalog = kyohud.hudlist_catalog
            for kind, entries in pairs(catalog.direct_ids.dynamic) do
                for native_id, data in pairs(entries) do
                    if type(data) == "table" and type(data.public_id) == "string" then
                        local public_id = catalog:resolve_dynamic(kind, native_id)
                        assert(public_id ~= nil,
                            "dynamic " .. kind .. "/" .. native_id
                            .. " has no public_id")
                        local resolved = catalog:resolve_alias(public_id)
                        assert(catalog.definitions[resolved] ~= nil,
                            "dynamic public_id " .. public_id
                            .. " (resolved: " .. resolved .. ") has no definition")
                    end
                end
            end
        ''')

    def test_no_orphan_definitions_are_referenced_by_routes_but_undefined(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local catalog = kyohud.hudlist_catalog
            for _, targets in pairs(catalog.routes) do
                for _, target_id in ipairs(targets) do
                    local resolved = catalog:resolve_alias(target_id)
                    assert(catalog.definitions[resolved] ~= nil,
                        "route target " .. target_id
                        .. " (resolved: " .. resolved .. ") is orphan (no definition)")
                end
            end
        ''')


class OrphanDetectionTests(unittest.TestCase):
    def test_no_route_references_a_nonexistent_source(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local catalog = kyohud.hudlist_catalog
            for source_id, targets in pairs(catalog.routes) do
                assert(type(targets) == "table" and #targets > 0,
                    "route " .. source_id .. " has no targets")
                for _, target_id in ipairs(targets) do
                    local resolved = catalog:resolve_alias(target_id)
                    assert(catalog.definitions[resolved] ~= nil,
                        "route " .. source_id .. " -> " .. target_id
                        .. " (resolved: " .. resolved .. ") is orphan")
                end
            end
        ''')

    def test_no_team_mapping_references_an_unknown_upgrade_category(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local catalog = kyohud.hudlist_catalog
            for category, upgrades in pairs(catalog.mappings.team) do
                for upgrade, mapping in pairs(upgrades) do
                    assert(type(mapping) == "table" and type(mapping.id) == "string",
                        "team mapping " .. category .. "." .. upgrade
                        .. " has no valid id")
                end
            end
        ''')

    def test_no_duplicate_production_for_same_temporary_upgrade(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/playermanager"
            Application = {time = function() return 100 end}
            PlayerManager = {}
            Hooks = {callbacks = {}, pre_callbacks = {}}
            function Hooks:PostHook(class, method, id, callback)
                self.callbacks[method] = callback
            end
            function Hooks:PreHook(class, method, id, callback)
                self.pre_callbacks[method] = callback
            end
        ''')
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            local manager = {
                _temporary_upgrades = {temporary = {
                    overkill_damage_multiplier = {expire_time = 110},
                }},
            }
            function manager:upgrade_level() return 1 end
            function manager:temporary_upgrade_value() return 1.75 end

            Hooks.callbacks.activate_temporary_upgrade(
                manager, "temporary", "overkill_damage_multiplier"
            )
            Hooks.callbacks.activate_temporary_upgrade(
                manager, "temporary", "overkill_damage_multiplier"
            )

            local order = provider:get_arrival_order()
            local count = 0
            for _, id in ipairs(order) do
                if id == "overkill" then count = count + 1 end
            end
            assert(count == 1, "duplicate production detected for overkill")
        ''')

    def test_no_duplicate_production_for_property_upgrade(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/playermanager"
            Application = {time = function() return 100 end}
            PlayerManager = {}
            Hooks = {callbacks = {}, pre_callbacks = {}}
            function Hooks:PostHook(class, method, id, callback)
                self.callbacks[method] = callback
            end
            function Hooks:PreHook(class, method, id, callback)
                self.pre_callbacks[method] = callback
            end
        ''')
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            local manager = {_properties = {_properties = {}}}
            manager._properties._properties.trigger_happy = 1.4

            Hooks.callbacks.set_property(manager, "trigger_happy", 1.4)
            Hooks.callbacks.set_property(manager, "trigger_happy", 1.4)

            local order = provider:get_arrival_order()
            local count = 0
            for _, id in ipairs(order) do
                if id == "trigger_happy" then count = count + 1 end
            end
            assert(count == 1, "duplicate production detected for trigger_happy")
        ''')

    def test_no_duplicate_production_for_cooldown_upgrade(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/playermanager"
            Application = {time = function() return 100 end}
            PlayerManager = {}
            Hooks = {callbacks = {}, pre_callbacks = {}}
            function Hooks:PostHook(class, method, id, callback)
                self.callbacks[method] = callback
            end
            function Hooks:PreHook(class, method, id, callback)
                self.pre_callbacks[method] = callback
            end
        ''')
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            local manager = {
                _global = {cooldown_upgrades = {cooldown = {
                    long_dis_revive = {cooldown_time = 120},
                }}},
            }
            function manager:upgrade_level() return 1 end

            Hooks.callbacks.disable_cooldown_upgrade(
                manager, "cooldown", "long_dis_revive"
            )
            Hooks.callbacks.disable_cooldown_upgrade(
                manager, "cooldown", "long_dis_revive"
            )

            local order = provider:get_arrival_order()
            local count = 0
            for _, id in ipairs(order) do
                if id == "inspire_revive_debuff" then count = count + 1 end
            end
            assert(count == 1, "duplicate production detected for inspire_revive_debuff")
        ''')


class ResetCorrectnessTests(unittest.TestCase):
    def _full_runtime(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute(CORE)
        lua.execute((ROOT / "lua" / "ky_combat_medals.lua").read_text(encoding="utf-8-sig"))
        return lua

    def test_provider_reset_clears_all_state(self):
        lua = self._full_runtime()
        lua.execute('''
            local provider = kyohud.hudlist
            provider:event("buff", "activate", "overkill", {t = 100, duration = 5})
            provider:event("buff", "activate", "inspire", {t = 100, duration = 7})
            provider:set_source("pocket_ecm_jammer", "src1", {
                expire_t = 110, mode = "jamming",
            })
            provider:activate_team_source(0, "damage_dampener",
                "team_damage_reduction", 1, 0.92)
            provider:add_timed_stack("biker", {t = 100, expire_t = 110})
            provider:set_composite_contribution("damage_increase", "src1",
                "multiply", 1.5)

            assert(next(provider:get_buffs()) ~= nil)
            assert(#provider:get_arrival_order() > 0)

            provider:reset()

            assert(next(provider:get_buffs()) == nil)
            assert(#provider:get_arrival_order() == 0)
            assert(provider:get_source_count("pocket_ecm_jammer") == 0)
            assert(provider:get_team_source_count("crew_chief") == 0)
            assert(provider._next_stack_id == 0)
        ''')

    def test_heist_reset_rearms_bridge_sync(self):
        lua = self._full_runtime()
        lua.execute('''
            kyohud.settings = {enable_buffs = true}
            assert(kyohud:TryRegisterGameInfoBridge() == true)

            kyohud.hudlist:event("buff", "activate", "overkill", {
                t = 100, duration = 7,
            })
            kyohud:SyncGameInfoBuffs()
            assert(kyohud._buffs.overkill ~= nil)

            kyohud:ResetHeistCombatState(true)
            assert(kyohud._buffs.overkill == nil)
            assert(kyohud._bridge_delayed_sync_done == false)
            assert(kyohud._bridge_delayed_sync_acc == 0)
            assert(next(kyohud.hudlist:get_buffs()) == nil)
        ''')

    def test_hudmanager_init_finalize_triggers_real_heist_reset(self):
        lua = self._full_runtime()
        lua.execute('''
            kyohud.settings = {enable_buffs = true}
            kyohud:TryRegisterGameInfoBridge()
            kyohud.hudlist:event("buff", "activate", "overkill", {
                t = 100, duration = 7,
            })
            kyohud:SyncGameInfoBuffs()
            assert(kyohud._buffs.overkill ~= nil)

            local hud_manager = {}
            local init_callback = Hooks.callbacks["KH_InitHUD"]
            assert(init_callback ~= nil, "KH_InitHUD callback should be registered")
            init_callback(hud_manager)

            assert(kyohud._buffs.overkill == nil,
                "HUDManager:init_finalize should trigger real heist reset")
            assert(kyohud._bridge_delayed_sync_done == false)
            assert(next(kyohud.hudlist:get_buffs()) == nil)
        ''')

    def test_bleedout_clears_passive_values_but_preserves_provider_state(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/units/beings/player/playerdamage"
            Application = {time = function() return 100 end}
            Hooks = {callbacks = {}, pre_callbacks = {}}
            function Hooks:PostHook(class, method, id, callback)
                self.callbacks[method] = callback
            end
            function Hooks:PreHook(class, method, id, callback)
                self.pre_callbacks[method] = callback
            end
            PlayerDamage = {}
            function alive(value) return value ~= nil end
        ''')
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            provider:event("buff", "activate", "overkill", {t = 100, duration = 5})

            local damage = {
                _uppers_elapsed = 0,
                get_real_health = function() return 0 end,
                _max_health = function() return 200 end,
                health_ratio = function() return 0.1 end,
                _max_health_reduction = 1,
                _health_regen_update_timer = 0,
                _damage_to_hot_stack = {},
            }

            Hooks.pre_callbacks._check_bleed_out(damage)

            assert(provider:get_buffs().berserker == nil)
            assert(provider:get_buffs().berserker_aced == nil)
            assert(provider:get_buffs().muscle_regen == nil)
            assert(provider:get_buffs().hostage_taker == nil)
            assert(provider:get_buffs().crew_health_regen == nil)
            assert(provider:get_buffs().overkill ~= nil,
                "non-passive buff should survive bleedout")
        ''')

    def test_custody_and_menu_return_clear_combat_state(self):
        lua = self._full_runtime()
        lua.execute('''
            kyohud.settings = {enable_buffs = true}
            kyohud:TryRegisterGameInfoBridge()
            kyohud.hudlist:event("buff", "activate", "overkill", {
                t = 100, duration = 7,
            })
            kyohud:SyncGameInfoBuffs()
            kyohud:add_kill("Enemy", 10, true, nil, nil, nil, nil, "player")
            assert(kyohud._buffs.overkill ~= nil)
            assert(#kyohud._kills > 0)

            local hud_manager = {}
            local init_callback = Hooks.callbacks["KH_InitHUD"]
            assert(init_callback ~= nil, "KH_InitHUD callback should be registered")
            init_callback(hud_manager)

            assert(kyohud._buffs.overkill == nil)
            assert(#kyohud._kills == 0)
            assert(kyohud._heist_kill_count == 0)
            assert(kyohud._sentry_kill_count == 0)
        ''')


class PeerDropTests(unittest.TestCase):
    def test_peer_drop_immediately_recalculates_team_buff(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            local manager = {_global = {
                team_upgrades = {},
                synced_team_upgrades = {},
            }}
            function manager:team_upgrade_value() return 0.92 end

            provider:activate_team_source(3, "damage_dampener",
                "team_damage_reduction", 1, 0.92)
            provider:activate_team_source(7, "damage_dampener",
                "team_damage_reduction", 1, 0.92)
            assert(provider:get_team_source_count("crew_chief") == 2)
            assert(provider:get_buffs().crew_chief ~= nil)
            assert(provider:get_buffs().crew_chief.contributor_count == 2)

            provider:remove_team_sources_for_peer(3)
            assert(provider:get_team_source_count("crew_chief") == 1)
            assert(provider:get_buffs().crew_chief ~= nil)
            assert(provider:get_buffs().crew_chief.contributor_count == 1)

            provider:remove_team_sources_for_peer(7)
            assert(provider:get_team_source_count("crew_chief") == 0)
            assert(provider:get_buffs().crew_chief == nil)
        ''')

    def test_peer_drop_with_multiple_buffs_only_affects_that_peer(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist

            provider:activate_team_source(3, "damage_dampener",
                "team_damage_reduction", 1, 0.92)
            provider:activate_team_source(3, "stamina", "multiplier", 0, 1.0)
            provider:activate_team_source(7, "damage_dampener",
                "team_damage_reduction", 1, 0.92)

            assert(provider:get_team_source_count("crew_chief") == 2)
            assert(provider:get_team_source_count("endurance") == 1)

            provider:remove_team_sources_for_peer(3)

            assert(provider:get_team_source_count("crew_chief") == 1)
            assert(provider:get_team_source_count("endurance") == 0)
            assert(provider:get_buffs().endurance == nil)
            assert(provider:get_buffs().crew_chief ~= nil)
        ''')

    def test_real_peer_dropped_out_hook_removes_team_sources(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/playermanager"
            Application = {time = function() return 100 end}
            PlayerManager = {}
            Hooks = {callbacks = {}, pre_callbacks = {}}
            function Hooks:PostHook(class, method, id, callback)
                self.callbacks[method] = callback
            end
            function Hooks:PreHook(class, method, id, callback)
                self.pre_callbacks[method] = callback
            end
        ''')
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            local manager = {_global = {
                team_upgrades = {},
                synced_team_upgrades = {},
            }}
            function manager:team_upgrade_value() return 0.92 end

            provider:activate_team_source(3, "damage_dampener",
                "team_damage_reduction", 1, 0.92)
            provider:activate_team_source(7, "damage_dampener",
                "team_damage_reduction", 1, 0.92)
            assert(provider:get_team_source_count("crew_chief") == 2)

            local peer3 = {id = function() return 3 end}
            Hooks.pre_callbacks.peer_dropped_out(manager, peer3)

            assert(provider:get_team_source_count("crew_chief") == 1)
            assert(provider:get_buffs().crew_chief ~= nil)

            local peer7 = {id = function() return 7 end}
            Hooks.pre_callbacks.peer_dropped_out(manager, peer7)

            assert(provider:get_team_source_count("crew_chief") == 0)
            assert(provider:get_buffs().crew_chief == nil)
        ''')


class HostClientOfflineTests(unittest.TestCase):
    def test_provider_works_offline_without_network(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            provider:event("buff", "activate", "overkill", {
                t = 100, duration = 5, value = 1.75,
            })
            local buff = provider:get_buffs().overkill
            assert(buff ~= nil and buff.value == 1.75)
            assert(buff.expire_t == 105)
        ''')

    def test_local_peer_team_source_is_tracked(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            provider:activate_team_source(0, "damage_dampener",
                "team_damage_reduction", 1, 0.92)
            local buff = provider:get_buffs().crew_chief
            assert(buff ~= nil)
            assert(buff.contributor_count == 1)
        ''')

    def test_remote_peer_team_source_is_tracked(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            provider:activate_team_source(4, "stamina", "multiplier", 0, 1.0)
            local buff = provider:get_buffs().endurance
            assert(buff ~= nil)
            assert(buff.contributor_count == 1)
        ''')


class NoExternalGlobalsTests(unittest.TestCase):
    def test_no_lua_file_creates_hudlist_or_gameinfomanager_global(self):
        forbidden = {"HUDList", "HUDListManager", "GameInfoManager"}
        for lua_file in (ROOT / "lua").glob("*.lua"):
            source = lua_file.read_text(encoding="utf-8-sig")
            for name in forbidden:
                assignments = re.findall(
                    r'(?:^|[^.\w])' + re.escape(name) + r'\s*=',
                    source, re.MULTILINE
                )
                self.assertEqual(
                    len(assignments), 0,
                    f"{lua_file.name} assigns to forbidden global {name}"
                )

    def test_core_does_not_read_external_hud_globals(self):
        source = CORE
        for name in ("HUDList", "HUDListManager", "GameInfoManager"):
            reads = re.findall(
                r'(?:^|[^.\w])' + re.escape(name) + r'(?:\s*[.\[]|\s*\()',
                source
            )
            self.assertEqual(
                len(reads), 0,
                f"core.lua reads forbidden global {name}"
            )

    def test_external_vanillahud_globals_coexist_without_interference(self):
        lua = _catalog_runtime()
        lua.execute('''
            HUDList = {BuffItemBase = {MAP = {external = {keep = true}}}}
            HUDListManager = {BUFFS = {external = true}}
            GameInfoManager = {external = true}
        ''')
        lua.execute(HUDLIST)
        lua.execute(CORE)
        lua.execute('''
            assert(HUDList.BuffItemBase.MAP.external.keep == true,
                "external HUDList should not be mutated")
            assert(HUDListManager.BUFFS.external == true,
                "external HUDListManager should not be mutated")
            assert(GameInfoManager.external == true,
                "external GameInfoManager should not be mutated")

            kyohud.settings = {enable_buffs = true}
            assert(kyohud:TryRegisterGameInfoBridge() == true)
            kyohud.hudlist:event("buff", "activate", "overkill", {
                t = 100, duration = 7,
            })
            kyohud:SyncGameInfoBuffs()

            assert(kyohud._buffs.overkill ~= nil)
            assert(HUDList.BuffItemBase.MAP.external.keep == true)
            assert(HUDListManager.BUFFS.external == true)
            assert(GameInfoManager.external == true)
        ''')

    def test_provider_does_not_consult_external_globals_even_when_present(self):
        lua = _catalog_runtime()
        lua.execute('''
            HUDList = {BuffItemBase = {MAP = {should_not_be_read = true}}}
            HUDListManager = {BUFFS = {should_not_be_read = true}}
            GameInfoManager = {should_not_be_read = true}
        ''')
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            provider:event("buff", "activate", "overkill", {
                t = 100, duration = 5,
            })
            local buff = provider:get_buffs().overkill
            assert(buff ~= nil and buff.duration == 5)
            assert(HUDList.BuffItemBase.MAP.should_not_be_read == true)
            assert(HUDListManager.BUFFS.should_not_be_read == true)
            assert(GameInfoManager.should_not_be_read == true)
        ''')


class HookAuditTests(unittest.TestCase):
    def test_hooks_are_idempotent_across_reload(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/playermanager"
            Application = {time = function() return 100 end}
            PlayerManager = {}
            Hooks = {installed = {}}
            function Hooks:PostHook(class, method, id, callback)
                self.installed[#self.installed + 1] = {"post", method, id}
            end
            function Hooks:PreHook(class, method, id, callback)
                self.installed[#self.installed + 1] = {"pre", method, id}
            end
        ''')
        lua.execute(HUDLIST)
        lua.execute(HUDLIST)
        lua.execute('''
            local count = #Hooks.installed
            assert(count == 25,
                "reloading hudlist.lua installed duplicate hooks: got " .. count)
        ''')

    def test_script_guard_prevents_double_install(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/playermanager"
            Application = {time = function() return 100 end}
            PlayerManager = {}
            Hooks = {installed = {}}
            function Hooks:PostHook(class, method, id, callback)
                self.installed[#self.installed + 1] = {"post", method, id}
            end
            function Hooks:PreHook(class, method, id, callback)
                self.installed[#self.installed + 1] = {"pre", method, id}
            end
        ''')
        lua.execute(HUDLIST)
        lua.execute(HUDLIST)
        lua.execute('''
            assert(kyohud._hudlist_loaded_scripts["lib/managers/playermanager"] == true)
            local count = #Hooks.installed
            assert(count == 25,
                "script guard failed: got " .. count .. " hooks instead of 25")
        ''')

    def test_same_callback_reference_across_reloads(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/playermanager"
            Application = {time = function() return 100 end}
            PlayerManager = {}
            Hooks = {callbacks = {}, call_count = 0}
            function Hooks:PostHook(class, method, id, callback)
                self.call_count = self.call_count + 1
                self.callbacks[id] = callback
            end
            function Hooks:PreHook(class, method, id, callback)
                self.call_count = self.call_count + 1
                self.callbacks[id] = callback
            end
        ''')
        lua.execute(HUDLIST)
        lua.execute('''
            local first_count = Hooks.call_count
            assert(first_count == 25)
        ''')
        lua.execute(HUDLIST)
        lua.execute('''
            assert(Hooks.call_count == 25,
                "reloading hudlist.lua should not call Hooks:PostHook again, got " .. Hooks.call_count)
        ''')

    def test_draw_has_no_permanent_allocations_or_logs(self):
        source = CORE
        draw_start = source.find("function KH:draw()")
        draw_end = source.find("\nfunction KH:", draw_start + 1)
        draw_body = source[draw_start:draw_end]
        self.assertNotIn("log(", draw_body,
            "KH:draw() contains a log() call")
        self.assertNotIn("table.insert", draw_body.split("local buff_list")[0]
            if "local buff_list" in draw_body else draw_body,
            "KH:draw() allocates tables before buff_list")

    def test_all_contexts_install_hooks_exactly_once(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            Application = {time = function() return 100 end}
            PlayerManager = {}
            TemporaryPropertyManager = {}
            PlayerDamage = {}
            PlayerInventory = {}
            function alive(value) return value ~= nil end
            Hooks = {installed = {}}
            function Hooks:PostHook(class, method, id, callback)
                self.installed[#self.installed + 1] = {"post", method, id}
            end
            function Hooks:PreHook(class, method, id, callback)
                self.installed[#self.installed + 1] = {"pre", method, id}
            end
        ''')
        contexts = [
            "lib/managers/hudmanagerpd2",
            "lib/managers/playermanager",
            "lib/units/beings/player/playerdamage",
            "lib/units/beings/player/playerinventory",
            "lib/utils/temporarypropertymanager",
        ]
        for context in contexts:
            lua.execute(f'RequiredScript = "{context}"')
            lua.execute(HUDLIST)
        lua.execute('''
            local total = #Hooks.installed
            assert(total == 37,
                "expected 37 total hooks across all contexts, got " .. total)
        ''')


class ExpirationBoundaryTests(unittest.TestCase):
    def test_expire_at_exact_boundary_removes_buff(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            provider:event("buff", "activate", "short", {
                t = 100, duration = 5,
            })
            assert(provider:get_buffs().short ~= nil)
            provider:update(105)
            assert(provider:get_buffs().short == nil,
                "buff should expire at exact expire_t")
        ''')

    def test_expire_just_before_boundary_keeps_buff(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            provider:event("buff", "activate", "short", {
                t = 100, duration = 5,
            })
            provider:update(104.999)
            assert(provider:get_buffs().short ~= nil,
                "buff should survive just before expire_t")
        ''')

    def test_retrigger_after_expiry_creates_new_entry(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            local events = {}
            provider:register_listener("test", "buff", function(event, id, data)
                events[#events + 1] = {event, id}
            end)

            provider:event("buff", "activate", "retrigger", {
                t = 100, duration = 2,
            })
            provider:update(102)
            assert(provider:get_buffs().retrigger == nil)

            provider:event("buff", "activate", "retrigger", {
                t = 105, duration = 3,
            })
            local buff = provider:get_buffs().retrigger
            assert(buff ~= nil and buff.t == 105 and buff.expire_t == 108)

            local activate_count = 0
            for _, e in ipairs(events) do
                if e[1] == "activate" and e[2] == "retrigger" then
                    activate_count = activate_count + 1
                end
            end
            assert(activate_count == 2, "retrigger should produce two activations")
        ''')

    def test_source_expire_at_boundary_removes_source_and_recalculates(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            provider:set_source("pocket_ecm_jammer", "src1", {
                expire_t = 110, mode = "jamming",
            })
            assert(provider:get_source_count("pocket_ecm_jammer") == 1)
            provider:update(110)
            assert(provider:get_source_count("pocket_ecm_jammer") == 0)
            assert(provider:get_buffs().pocket_ecm_jammer == nil)
        ''')

    def test_replacement_refreshes_timer_without_new_arrival(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            provider:event("buff", "activate", "overkill", {
                t = 100, duration = 5,
            })
            local order_before = {unpack(provider:get_arrival_order())}

            provider:event("buff", "activate", "overkill", {
                t = 103, duration = 8,
            })
            local buff = provider:get_buffs().overkill
            assert(buff.expire_t == 111)
            assert(#provider:get_arrival_order() == #order_before)
        ''')

    def test_timed_stack_expire_at_exact_boundary(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            provider:add_timed_stack("biker", {t = 100, expire_t = 105})
            provider:add_timed_stack("biker", {t = 100, expire_t = 108})
            assert(provider:get_buffs().biker ~= nil)
            assert(provider:get_buffs().biker.stack_count == 2)

            provider:update(105)
            assert(provider:get_buffs().biker ~= nil)
            assert(provider:get_buffs().biker.stack_count == 1)

            provider:update(108)
            assert(provider:get_buffs().biker == nil,
                "all stacks should expire at exact boundary")
        ''')

    def test_multiple_sources_expire_independently(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute('''
            local provider = kyohud.hudlist
            provider:set_source("pocket_ecm_jammer", "src1", {
                expire_t = 105, mode = "jamming",
            })
            provider:set_source("pocket_ecm_jammer", "src2", {
                expire_t = 110, mode = "feedback",
            })
            assert(provider:get_source_count("pocket_ecm_jammer") == 2)

            provider:update(105)
            assert(provider:get_source_count("pocket_ecm_jammer") == 1)
            assert(provider:get_buffs().pocket_ecm_jammer ~= nil)

            provider:update(110)
            assert(provider:get_source_count("pocket_ecm_jammer") == 0)
            assert(provider:get_buffs().pocket_ecm_jammer == nil)
        ''')


class LogBoundednessTests(unittest.TestCase):
    def test_bridge_error_is_logged_at_most_once(self):
        lua = _catalog_runtime()
        lua.execute(HUDLIST)
        lua.execute(CORE)
        lua.execute('''
            local log_count = 0
            local original_log = log
            log = function(msg)
                if type(msg) == "string" and msg:find("bridge") then
                    log_count = log_count + 1
                end
            end

            kyohud.settings = {enable_buffs = true}
            kyohud.hudlist = nil
            kyohud.hudlist_catalog = nil

            for i = 1, 10 do
                kyohud:TryRegisterGameInfoBridge()
            end

            assert(log_count <= 1,
                "bridge error should be logged at most once, got " .. log_count)
            log = original_log
        ''')


class DocumentedLimitsTests(unittest.TestCase):
    def test_mod_txt_hook_order_matches_codex(self):
        metadata = json.loads((ROOT / "mod.txt").read_text(encoding="utf-8-sig"))
        hooks = metadata["hooks"]
        hudlist_first = next(
            i for i, h in enumerate(hooks) if h["script_path"] == "lua/hudlist.lua"
        )
        core_first = next(
            i for i, h in enumerate(hooks) if h["script_path"] == "lua/core.lua"
        )
        self.assertLess(hudlist_first, core_first)

    def test_killfeed_preserves_one_to_five_cards(self):
        lua = _catalog_runtime()
        lua.execute(CORE)
        lua.execute((ROOT / "lua" / "ky_combat_medals.lua").read_text(encoding="utf-8-sig"))
        lua.execute('''
            kyohud.settings = {
                enable_buffs = false,
                enable_killfeed = true,
                killfeed_size = 5,
                opacity = 1,
                circle_radius = 250,
                icon_size = 32,
                show_total_score = true,
            }
            kyohud._kills = {}
            local t = 100
            for i = 1, 7 do
                kyohud:add_kill("Enemy " .. i, 10, true, nil, nil, nil, nil, "player")
            end
            assert(#kyohud._kills == 5,
                "killfeed should cap at 5 entries, got " .. #kyohud._kills)
        ''')

    def test_codex_documents_autonomous_provider(self):
        codex = (ROOT / "CODEX.md").read_text(encoding="utf-8-sig")
        self.assertIn("hudlist.lua", codex)
        self.assertIn("hudlist_catalog.lua", codex)
        self.assertIn("ky_buff_presentation.lua", codex)
        self.assertIn("HUDList", codex)
        self.assertIn("GameInfoManager", codex)
        self.assertIn("provider autonome", codex)
        self.assertIn("API natives", codex)
        self.assertNotIn("managers.gameinfo", codex)
        self.assertNotIn("HUDListManager.BUFFS", codex)


if __name__ == "__main__":
    unittest.main()
