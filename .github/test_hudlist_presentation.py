"""Autonomous presentation regressions for KyoHUD's HUDList provider."""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class HUDListPresentationTests(unittest.TestCase):
    def make_runtime(self):
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
        ''')
        lua.execute((ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig"))
        lua.execute((ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig"))
        lua.execute('kyohud.settings = {enable_buffs = true}')
        return lua

    def test_shipping_core_has_no_external_provider_fallback(self):
        source = (ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig")
        for token in ("managers.gameinfo", "HUDListManager", "HUDList.BuffItemBase"):
            self.assertNotIn(token, source)

    def test_external_hud_globals_cannot_override_local_definition_or_route(self):
        lua = self.make_runtime()
        lua.execute('''
            HUDList = {BuffItemBase = {MAP = {
                overkill = {texture = "external/wrong", priority = 99},
            }}}
            HUDListManager = {BUFFS = {overkill = {"external_target"}}}
            local definition = kyohud:GetVanillaHUDBuffDefinition("overkill")
            assert(definition ~= nil and definition.priority == 4)
            local targets = kyohud:GetVanillaHUDBuffTargets("overkill")
            assert(#targets == 2 and targets[1] == "overkill" and targets[2] == "damage_increase")
        ''')

    def test_produced_modern_buffs_have_local_visual_metadata(self):
        lua = self.make_runtime()
        lua.execute('''
            local required = {
                "overkill", "biker", "grinder", "crew_chief", "maniac",
                "maniac_debuff", "sicario_dodge", "sicario_dodge_debuff",
                "chico_injector", "chico_injector_debuff", "copr_ability",
                "copr_ability_debuff", "copycat_health_invul",
                "copycat_health_invul_debuff", "copycat_health_invul_passive",
                "copycat_health_shot_debuff", "pocket_ecm_jammer",
                "pocket_ecm_jammer_debuff", "uppers", "uppers_debuff",
                "smoke_screen_grenade", "crew_inspire_debuff",
                "partner_in_crime", "messiah",
            }
            for _, id in ipairs(required) do
                local definition = kyohud.hudlist_catalog.definitions[id]
                assert(definition ~= nil, "missing definition: " .. id)
                assert(definition.priority ~= nil, "missing priority: " .. id)
                assert(definition.skills_new or definition.perks or definition.hud_tweak,
                    "missing icon: " .. id)
            end
        ''')

    def test_every_catalogued_literal_and_mapping_has_a_local_definition(self):
        lua = self.make_runtime()
        lua.execute('''
            local catalog = kyohud.hudlist_catalog
            local function require_definition(id)
                if type(id) == "string" then
                    assert(catalog.definitions[catalog:resolve_alias(id)] ~= nil,
                        "missing autonomous definition: " .. id)
                elseif type(id) == "table" and type(id.id) == "string" then
                    require_definition(id.id)
                elseif type(id) == "table" then
                    for _, value in pairs(id) do require_definition(value) end
                end
            end
            for category, mappings in pairs(catalog.mappings) do
                if category ~= "team" then
                    for _, mapping in pairs(mappings) do require_definition(mapping) end
                else
                    for _, upgrades in pairs(mappings) do
                        for _, mapping in pairs(upgrades) do require_definition(mapping) end
                    end
                end
            end
            for id in pairs(catalog.direct_ids.literals) do require_definition(id) end
        ''')

    def test_namespaced_provider_bootstrap_syncs_and_deactivates_visible_state(self):
        lua = self.make_runtime()
        lua.execute('''
            assert(kyohud:TryRegisterGameInfoBridge() == true)
            kyohud.hudlist:event("buff", "activate", "biker", {
                t = 100, duration = 8, stack_count = 2,
            })
            assert(kyohud._buffs.biker ~= nil)
            assert(kyohud._buffs.biker.stack_text == "x2")
            kyohud.hudlist:event("buff", "deactivate", "biker", {})
            assert(kyohud._buffs.biker == nil)
            assert(HUDList == nil and HUDListManager == nil and GameInfoManager == nil)
        ''')


if __name__ == "__main__":
    unittest.main()
