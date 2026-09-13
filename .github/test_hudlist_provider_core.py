"""Autonomous HUDList provider core regressions against real Lua chunks."""
from pathlib import Path
import json
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class HUDListProviderCoreTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + "/"
        self.lua.execute('''
            kyohud = {}
            Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/hudmanagerpd2"
            Hooks = {}
            Application = {time = function() return 100 end}
        ''')
        self.lua.execute((ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig"))

    def test_activation_creates_one_normalized_entry_and_refreshes_in_place(self):
        self.lua.execute('''
            local provider = assert(kyohud.hudlist)
            provider:event("buff", "activate", "inspire", {
                t = 100,
                duration = 5,
                value = 1.2,
            })

            local first = provider:get_buffs().inspire
            assert(first ~= nil)
            assert(first.id == "inspire" and first.source == "buff")
            assert(first.active == true and first.t == 100)
            assert(first.duration == 5 and first.expire_t == 105)
            assert(first.value == 1.2)

            provider:event("buff", "activate", "inspire", {
                t = 102,
                duration = 8,
                value = 1.3,
            })

            local refreshed = provider:get_buffs().inspire
            assert(refreshed == first, "refresh duplicated or replaced normalized state")
            assert(refreshed.t == 102 and refreshed.expire_t == 110)
            assert(refreshed.value == 1.3)
        ''')

    def test_value_and_duration_events_mutate_existing_state(self):
        self.lua.execute('''
            local provider = kyohud.hudlist
            provider:event("buff", "activate", "overkill", {t = 100})
            provider:event("buff", "set_value", "overkill", {value = 1.75})
            provider:event("buff", "set_duration", "overkill", {
                t = 101,
                duration = 6,
            })

            local buff = provider:get_buffs().overkill
            assert(buff.value == 1.75)
            assert(buff.t == 101 and buff.duration == 6 and buff.expire_t == 107)
        ''')

    def test_expiration_and_deactivation_remove_state_and_notify_listeners(self):
        self.lua.execute('''
            local provider = kyohud.hudlist
            local events = {}
            provider:register_listener("test", "buff", function(event, id, data)
                events[#events + 1] = {event, id, data}
            end)

            provider:event("buff", "activate", "short", {t = 100, duration = 2})
            provider:update(101.99)
            assert(provider:get_buffs().short ~= nil)
            provider:update(102)
            assert(provider:get_buffs().short == nil)
            assert(events[#events][1] == "deactivate")
            assert(events[#events][2] == "short")
            assert(events[#events][3].reason == "expired")

            provider:event("buff", "activate", "manual", {})
            provider:event("buff", "deactivate", "manual")
            assert(provider:get_buffs().manual == nil)
            assert(events[#events][1] == "deactivate")
            assert(events[#events][2] == "manual")
        ''')

    def test_temporary_upgrade_posthooks_feed_the_verified_catalog_mapping(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/playermanager"
            Application = {time = function() return 200 end}
            PlayerManager = {}
            Hooks = {callbacks = {}, pre_callbacks = {}}
            function Hooks:PostHook(class, method, id, callback)
                self.callbacks[method] = callback
            end
            function Hooks:PreHook(class, method, id, callback)
                self.pre_callbacks[method] = callback
            end
        ''')
        lua.execute((ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig"))
        lua.execute('''
            assert(HUDList == nil and HUDListManager == nil)
            assert(kyohud.hudlist_catalog.provenance.official_commit
                == "94f10a0bb6d23ab25d0636222378f1755ae6a5b7")

            local manager = {
                _temporary_upgrades = {
                    temporary = {
                        overkill_damage_multiplier = {expire_time = 212},
                    },
                },
            }
            function manager:upgrade_level() return 1 end
            function manager:temporary_upgrade_value() return 1.75 end

            Hooks.callbacks.activate_temporary_upgrade(
                manager, "temporary", "overkill_damage_multiplier"
            )

            local buff = kyohud.hudlist:get_buffs().overkill
            assert(buff ~= nil)
            assert(buff.t == 200 and buff.expire_t == 212 and buff.duration == 12)
            assert(buff.value == 1.75)

            Hooks.pre_callbacks.deactivate_temporary_upgrade(
                manager, "temporary", "overkill_damage_multiplier"
            )
            assert(kyohud.hudlist:get_buffs().overkill == nil)
        ''')

    def test_core_presentation_consumes_the_namespaced_provider(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
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
            local function color()
                return {with_alpha = function(self) return self end}
            end
            Color = setmetatable({white = color(), black = color()}, {
                __call = function(...) return color() end
            })
            TimerManager = {game = function()
                return {time = function() return 100 end}
            end}
            Application = {time = function() return 100 end}
        ''')
        lua.execute((ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig"))
        lua.execute((ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig"))
        lua.execute('''
            kyohud.settings = {enable_buffs = true}
            assert(kyohud:TryRegisterGameInfoBridge() == true)
            kyohud.hudlist:event("buff", "activate", "overkill", {
                t = 100, duration = 7, value = 1.75,
            })

            local visible = kyohud._buffs.overkill
            assert(visible ~= nil and visible.duration == 7)
            assert(kyohud:GetVanillaHUDBuffDefinition("overkill")
                == kyohud.hudlist_catalog.definitions.overkill)
            assert(HUDList == nil and HUDListManager == nil)
        ''')

    def test_superblt_loads_provider_before_consumers_in_both_contexts(self):
        metadata = json.loads((ROOT / "mod.txt").read_text(encoding="utf-8-sig"))
        hooks = metadata["hooks"]
        provider_contexts = [
            hook["hook_id"] for hook in hooks
            if hook["script_path"] == "lua/hudlist.lua"
        ]
        self.assertEqual(provider_contexts, [
            "lib/managers/hudmanagerpd2",
            "lib/managers/playermanager",
            "lib/units/beings/player/playerdamage",
            "lib/units/beings/player/playerinventory",
            "lib/utils/temporarypropertymanager",
        ])
        self.assertLess(
            next(i for i, hook in enumerate(hooks) if hook["script_path"] == "lua/hudlist.lua"),
            next(i for i, hook in enumerate(hooks) if hook["script_path"] == "lua/core.lua"),
        )


if __name__ == "__main__":
    unittest.main()
