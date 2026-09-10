"""VanillaHUD+ provider regressions against the real KyoHUD core chunk.

Run: uv run --with lupa python -B -m unittest discover -s .github -p test_vanillahud_provider.py -v
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class VanillaHUDBuffProviderTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + "/"
        self.lua.execute('''
            Hooks = {callbacks = {}}
            function Hooks:PostHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:PreHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:Add(...) end
            HUDManager = {}; PlayerManager = {}; managers = {}; tweak_data = {}
            function Vector3(...) return {...} end
            function log(...) end
            function alive(x) return x ~= nil end
            Color = setmetatable({white = {}, black = {}}, {
                __call = function(...) return {} end
            })
            TimerManager = {
                game = function()
                    return {time = function() return 100 end}
                end
            }
        ''')
        self.lua.execute((ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig"))
        self.lua.execute('kyohud.settings = {enable_buffs = true}')

    def test_definition_is_resolved_lazily_from_vanillahud_map(self):
        self.lua.execute('''
            HUDList = nil
            assert(kyohud:GetVanillaHUDBuffDefinition("overkill") == nil)

            local definition = {skills_new = {2, 0}, class = "TimedBuffItem"}
            HUDList = {BuffItemBase = {MAP = {overkill = definition}}}

            assert(kyohud:GetVanillaHUDBuffDefinition("overkill") == definition)
        ''')

    def test_source_targets_are_filtered_through_vanillahud_map(self):
        self.lua.execute('''
            HUDList = {BuffItemBase = {MAP = {
                berserker = {},
                damage_increase = {},
            }}}
            HUDListManager = {BUFFS = {
                berserker_aced = {
                    "berserker", "damage_increase", "missing_entry"
                }
            }}

            local targets = kyohud:GetVanillaHUDBuffTargets("berserker_aced")
            assert(#targets == 2)
            assert(targets[1] == "berserker")
            assert(targets[2] == "damage_increase")
        ''')

    def test_unmapped_source_uses_matching_vanillahud_definition(self):
        self.lua.execute('''
            HUDList = {BuffItemBase = {MAP = {inspire = {}}}}
            HUDListManager = {BUFFS = {}}

            local targets = kyohud:GetVanillaHUDBuffTargets("inspire")
            assert(#targets == 1)
            assert(targets[1] == "inspire")
        ''')

    def test_composite_debuff_uses_vanillahud_parent_definition(self):
        self.lua.execute('''
            HUDList = {BuffItemBase = {MAP = {grinder = {}}}}
            HUDListManager = {BUFFS = {
                composite_debuffs = {grinder_debuff = "grinder"},
            }}

            local targets = kyohud:GetVanillaHUDBuffTargets("grinder_debuff")
            assert(#targets == 1)
            assert(targets[1] == "grinder")
        ''')

    def test_bridge_waits_until_vanillahud_metadata_is_available(self):
        self.lua.execute('''
            local registrations = 0
            managers.gameinfo = {
                register_listener = function() registrations = registrations + 1 end,
                get_buffs = function() return {} end,
                get_player_actions = function() return {} end,
            }
            HUDList = nil
            HUDListManager = nil

            assert(kyohud:TryRegisterGameInfoBridge() == false)
            assert(registrations == 0)
            assert(kyohud._gameinfo_bridge_active ~= true)
        ''')

    def test_bridge_uses_vanillahud_targets_for_unknown_sources(self):
        self.lua.execute('''
            local listeners = {}
            managers.gameinfo = {
                register_listener = function(self, listener_id, source, event, callback)
                    listeners[source .. ":" .. event] = callback
                end,
                get_buffs = function() return {} end,
                get_player_actions = function() return {} end,
            }
            HUDList = {BuffItemBase = {MAP = {
                future_buff = {skills_new = {1, 2}, class = "TimedBuffItem"},
            }}}
            HUDListManager = {BUFFS = {
                future_source = {"future_buff"},
            }}
            kyohud.GetBuffTargets = nil

            assert(kyohud:TryRegisterGameInfoBridge() == true)
            listeners["buff:activate"]("activate", "future_source", {duration = 8})

            assert(kyohud._buffs.future_buff ~= nil, "mapped buff was not created")
            assert(kyohud._buffs.future_buff.duration == 8, "mapped duration was not preserved")
        ''')

    def test_successful_bridge_registration_is_idempotent(self):
        self.lua.execute('''
            local registrations = 0
            managers.gameinfo = {
                register_listener = function() registrations = registrations + 1 end,
                get_buffs = function() return {} end,
                get_player_actions = function() return {} end,
            }
            HUDList = {BuffItemBase = {MAP = {}}}
            HUDListManager = {BUFFS = {}}

            assert(kyohud:TryRegisterGameInfoBridge() == true)
            local first_count = registrations
            assert(first_count > 0)
            assert(kyohud:TryRegisterGameInfoBridge() == true)
            assert(registrations == first_count)
        ''')


if __name__ == "__main__":
    unittest.main()
