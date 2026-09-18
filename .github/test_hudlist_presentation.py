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
            HUDListManager = {BUFFS = {overkill_damage_multiplier = {"overkill"}}}
            local definition = kyohud:GetVanillaHUDBuffDefinition("overkill")
            assert(definition ~= nil and definition.priority == 4)
            local targets = kyohud:GetVanillaHUDBuffTargets("overkill")
            assert(#targets == 1 and targets[1] == "overkill")
        ''')

    def test_partner_in_crime_aced_merges_without_duplicate_stack_badge(self):
        lua = self.make_runtime()
        lua.execute('''
            assert(kyohud:TryRegisterGameInfoBridge() == true)
            local targets = kyohud:GetVanillaHUDBuffTargets("partner_in_crime_aced")
            assert(#targets == 1 and targets[1] == "partner_in_crime")
            kyohud.hudlist:event("buff", "activate", "partner_in_crime", {stack_count = 1})
            kyohud.hudlist:event("buff", "activate", "partner_in_crime_aced", {stack_count = 1})
            assert(kyohud._buffs.partner_in_crime ~= nil)
            assert(kyohud._buffs.partner_in_crime_aced == nil)
            assert(kyohud._buffs.partner_in_crime.stack_text == nil)
        ''')

    def test_composite_damage_icons_use_requested_native_assets(self):
        lua = self.make_runtime()
        lua.execute('''
            local increase = kyohud.hudlist_catalog.definitions.damage_increase
            local reduction = kyohud.hudlist_catalog.definitions.damage_reduction
            assert(increase.hud_tweak == "equipment_chrome_mask")
            assert(reduction.skill_id == "dire_need")
            assert(reduction.skills_new[1] == 10 and reduction.skills_new[2] == 8)
        ''')

    def test_fixed_buff_order_configuration_is_preserved(self):
        lua = self.make_runtime()
        lua.execute('''
            local buffs = kyohud.KYO_BUFF_CONFIG.buffs
            assert(buffs.equipped_perk_deck.fixed_slot == 1)
            assert(buffs.pocket_ecm_jammer_debuff.fixed_slot == 2)
            assert(buffs.passive_health_regen.fixed_slot == 3)
            assert(buffs.standard_armor_regeneration.fixed_slot == 4)
            assert(buffs.armor_break_invulnerable_debuff.fixed_slot == 5)
            assert(buffs.damage_increase.fixed_slot == 6)
            assert(buffs.damage_reduction.fixed_slot == 7)
            assert(buffs.melee_damage_increase.fixed_slot == 8)
            assert(buffs.total_dodge_chance.fixed_slot == 9)
        ''')

    def test_dodge_uses_dark_clover_green_and_health_regen_has_green_frame(self):
        lua = self.make_runtime()
        lua.execute('''
            local config = kyohud.KYO_BUFF_CONFIG
            assert(config.colors.total_dodge_chance == "2E8B57")
            assert(config.colors.passive_health_regen == "4ADE9B")
            assert(config.colors.total_dodge_chance ~= config.colors.passive_health_regen)
            assert(config.buffs.total_dodge_chance.color == "total_dodge_chance")
            assert(config.buffs.passive_health_regen.frame_color == "passive_health_regen")
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


    def test_passive_values_use_semantic_formats_without_neutral_noise(self):
        lua = self.make_runtime()
        lua.execute('''
            assert(kyohud:TryRegisterGameInfoBridge() == true)
            kyohud.hudlist:event("buff", "activate", "berserker", {value = 1.25})
            kyohud.hudlist:event("buff", "activate", "yakuza_recovery", {value = 0.3})
            kyohud.hudlist:event("buff", "activate", "muscle_regen", {
                value = 0.03, interval = 5,
            })
            assert(kyohud._buffs.berserker.value_text == "+125%")
            assert(kyohud._buffs.yakuza_recovery.value_text == "-30%")
            assert(kyohud._buffs.muscle_regen.value_text == "3% / 5s")
            kyohud.hudlist:event("buff", "deactivate", "berserker", {})
            kyohud.hudlist:event("buff", "activate", "berserker_aced", {value = 0.5})
            assert(kyohud._buffs.berserker_aced.value_text == "+50%")
            kyohud.hudlist:event("buff", "deactivate", "berserker_aced", {})
            kyohud.hudlist:event("buff", "activate", "berserker_aced", {value = 0/0})
            assert(kyohud._buffs.berserker_aced == nil)
        ''')

    def test_feature_seven_visuals_have_verified_metadata(self):
        lua = self.make_runtime()
        lua.execute('''
            for _, id in ipairs({"muscle_regen", "hostage_taker", "crew_health_regen",
                    "berserker", "berserker_aced", "yakuza_recovery", "yakuza_speed"}) do
                local definition = kyohud.hudlist_catalog.definitions[id]
                assert(definition and definition.icon_provenance)
                assert(definition.skills_new or definition.perks or definition.hud_tweak)
                assert(definition.value_kind and definition.display_mode)
            end
        ''')


    def test_yakuza_uses_the_verified_base_specialization_atlas(self):
        lua = self.make_runtime()
        lua.execute('''
            for _, id in ipairs({"yakuza_recovery", "yakuza_speed"}) do
                local definition = kyohud.hudlist_catalog.definitions[id]
                assert(definition.texture_bundle_folder == nil)
                assert(definition.perks[1] == 2 and definition.perks[2] == 7)
            end
        ''')

    def test_total_dodge_chance_uses_burglar_perk_icon_without_bundle(self):
        lua = self.make_runtime()
        lua.execute('''
            local def = kyohud.hudlist_catalog.definitions.total_dodge_chance
            assert(def ~= nil, "total_dodge_chance definition missing")
            assert(def.perks ~= nil, "total_dodge_chance must use perks icon")
            assert(def.perks[1] == 7 and def.perks[2] == 3,
                "total_dodge_chance perks must be {7, 3} (Burglar deck 5), got {"
                .. def.perks[1] .. ", " .. def.perks[2] .. "}")
            assert(def.texture_bundle_folder == nil,
                "total_dodge_chance must have no DLC bundle folder")
            assert(def.hud_tweak == nil,
                "total_dodge_chance must not use hud_tweak")
            assert(def.skills_new == nil and def.skills == nil and def.skill_id == nil,
                "total_dodge_chance must not use skill icons")
            assert(type(def.icon_provenance) == "string" and def.icon_provenance ~= "",
                "total_dodge_chance must have explicit provenance")
        ''')

    def test_melee_damage_increase_uses_throwing_axe_hud_icon(self):
        lua = self.make_runtime()
        lua.execute('''
            local def = kyohud.hudlist_catalog.definitions.melee_damage_increase
            assert(def ~= nil, "melee_damage_increase definition missing")
            assert(def.hud_tweak == "throwing_axe",
                "melee_damage_increase must use hud_tweak throwing_axe, got "
                .. tostring(def.hud_tweak))
            assert(def.skills_new == nil and def.skills == nil,
                "melee_damage_increase must not use skill atlas icons")
            assert(def.skill_id == nil,
                "melee_damage_increase must not have a concurrent skill_id")
            assert(def.icon_rotation == -90,
                "melee_damage_increase must have icon_rotation = -90, got "
                .. tostring(def.icon_rotation))
            assert(type(def.icon_provenance) == "string" and def.icon_provenance ~= "",
                "melee_damage_increase must have explicit provenance")
        ''')

    def test_icon_for_buff_carries_rotation_only_when_declared(self):
        lua = self.make_runtime()
        lua.execute('''
            function Idstring(value) return value end
            DB = {has = function() return true end}
            tweak_data = {
                skilltree = {skills = setmetatable({}, {__index = function(t, k)
                    return {icon_xy = {1, 1}}
                end})},
                hud_icons = {get_icon_data = function(self, id)
                    return "native/" .. id, {0, 0, 32, 32}
                end},
            }
        ''')
        lua.execute('''
            local melee = kyohud.hudlist_catalog.definitions.melee_damage_increase
            local dodge = kyohud.hudlist_catalog.definitions.total_dodge_chance
            local overkill = kyohud.hudlist_catalog.definitions.overkill

            kyohud:add_buff("melee_damage_increase", nil, 10, nil, false, false, nil, nil)
            local melee_card = kyohud._buffs.melee_damage_increase
            assert(melee_card ~= nil and melee_card.icon ~= nil)
            assert(melee_card.icon.rotation == -90,
                "melee card icon must carry rotation -90, got "
                .. tostring(melee_card.icon.rotation))

            kyohud:add_buff("total_dodge_chance", nil, 10, nil, false, false, nil, nil)
            local dodge_card = kyohud._buffs.total_dodge_chance
            assert(dodge_card ~= nil and dodge_card.icon ~= nil)
            assert(dodge_card.icon.rotation == nil,
                "dodge card icon must have no rotation, got "
                .. tostring(dodge_card.icon.rotation))

            kyohud:add_buff("overkill", nil, 10, nil, false, false, nil, nil)
            local overkill_card = kyohud._buffs.overkill
            assert(overkill_card ~= nil and overkill_card.icon ~= nil)
            assert(overkill_card.icon.rotation == nil,
                "non-rotated icon must not carry rotation metadata")
        ''')

    def test_icon_provenance_records_exact_source_for_dodge_and_melee(self):
        lua = self.make_runtime()
        lua.execute('''
            local dodge = kyohud.hudlist_catalog.definitions.total_dodge_chance
            local melee = kyohud.hudlist_catalog.definitions.melee_damage_increase
            assert(dodge.icon_provenance:find("Burglar") or dodge.icon_provenance:find("specialization 7"),
                "dodge provenance must reference Burglar / specialization 7")
            assert(dodge.icon_provenance:find("{7, 3}") or dodge.icon_provenance:find("7, 3"),
                "dodge provenance must reference coordinates {7, 3}")
            assert(melee.icon_provenance:find("throwing_axe"),
                "melee provenance must reference throwing_axe")
            assert(melee.icon_provenance:find("equipment_02"),
                "melee provenance must reference the native equipment atlas")
        ''')

    def test_underdog_basic_and_aced_merge_into_single_card(self):
        lua = self.make_runtime()
        lua.execute('''
            assert(kyohud:TryRegisterGameInfoBridge() == true)
            -- The aced dampener routes onto the single Underdog card.
            local targets = kyohud:GetVanillaHUDBuffTargets("underdog_aced")
            assert(#targets == 1 and targets[1] == "underdog",
                "underdog_aced must route to the underdog card")
            local self_targets = kyohud:GetVanillaHUDBuffTargets("underdog")
            assert(#self_targets == 1 and self_targets[1] == "underdog")

            -- Both temporary upgrades activate together with the same timer.
            kyohud.hudlist:event("buff", "activate", "underdog",
                {t = 100, expire_t = 107, value = 1.15})
            kyohud.hudlist:event("buff", "activate", "underdog_aced",
                {t = 100, expire_t = 107, value = 0.9})

            -- One card only; the aced source never gets its own entry.
            assert(kyohud._buffs.underdog ~= nil, "underdog card must exist")
            assert(kyohud._buffs.underdog_aced == nil,
                "underdog_aced must not produce a second card")

            local card = kyohud._buffs.underdog
            assert(card.value_text == "+15% | -10%",
                "expected combined '+15% | -10%', got: " .. tostring(card.value_text))
            assert(card.value_text_split == true,
                "underdog card must request the split colored value line")
            assert(card.icon ~= nil and card.icon.texture ~= nil,
                "underdog card must resolve a real icon")
        ''')

    def test_underdog_shows_lone_half_when_only_one_upgrade_owned(self):
        lua = self.make_runtime()
        lua.execute('''
            assert(kyohud:TryRegisterGameInfoBridge() == true)

            -- Basic only: damage bonus, no reduction.
            kyohud.hudlist:event("buff", "activate", "underdog",
                {t = 100, expire_t = 107, value = 1.15})
            assert(kyohud._buffs.underdog.value_text == "+15%",
                "basic-only underdog must show +15%, got: "
                .. tostring(kyohud._buffs.underdog.value_text))

            -- Aced only: reduction, no bonus.
            kyohud.hudlist:event("buff", "deactivate", "underdog")
            kyohud.hudlist:event("buff", "activate", "underdog_aced",
                {t = 100, expire_t = 107, value = 0.9})
            assert(kyohud._buffs.underdog.value_text == "-10%",
                "aced-only underdog must show -10%, got: "
                .. tostring(kyohud._buffs.underdog.value_text))
        ''')


if __name__ == "__main__":
    unittest.main()
