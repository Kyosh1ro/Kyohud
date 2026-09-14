"""HUDList catalog regressions against the real Lua chunks."""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class HUDListCatalogTests(unittest.TestCase):
    def make_runtime(self, nil_returning_dofile=False):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            kyohud = {}
            Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/hudmanagerpd2"
            Hooks = {}
            Application = {time = function() return 100 end}
            HUDList = { untouched = true }
            HUDListManager = { BUFFS = { untouched = true } }
        ''')
        if nil_returning_dofile:
            catalog_path = (ROOT / "lua" / "hudlist_catalog.lua").as_posix()
            lua.globals().catalog_chunk = (
                ROOT / "lua" / "hudlist_catalog.lua"
            ).read_text(encoding="utf-8-sig")
            lua.execute(f'''
                function dofile(path)
                    assert(path == "{catalog_path}")
                    assert(loadstring(catalog_chunk))()
                    return nil
                end
            ''')
        lua.execute((ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig"))
        return lua

    def test_real_catalog_load_survives_nil_dofile_return(self):
        lua = self.make_runtime(nil_returning_dofile=True)
        lua.execute('''
            assert(kyohud.hudlist_catalog ~= nil)
            assert(kyohud.hudlist ~= nil)
        ''')

    def test_scalar_and_multilevel_temporary_mappings(self):
        lua = self.make_runtime()
        lua.execute('''
            local provider = kyohud.hudlist
            assert(provider:resolve_mapping("temporary", "overkill_damage_multiplier", 99)
                == "overkill")
            assert(provider:resolve_mapping("temporary", "berserker_damage_multiplier", 1)
                == "swan_song")
            assert(provider:resolve_mapping("temporary", "berserker_damage_multiplier", 2)
                == "swan_song_aced")
            assert(provider:resolve_mapping("temporary", "dmg_dampener_close_contact", 1)
                == "close_contact_1")
            assert(provider:resolve_mapping("temporary", "dmg_dampener_close_contact", 3)
                == "close_contact_3")
            assert(provider:resolve_mapping("temporary", "unseen_strike", 1)
                == "unseen_strike")
            assert(provider:resolve_mapping("temporary", "unseen_strike", 2)
                == "unseen_strike")
        ''')

    def test_copycat_and_pain_killer_levels_are_preserved(self):
        lua = self.make_runtime()
        lua.execute('''
            local provider = kyohud.hudlist
            assert(provider:resolve_mapping("temporary", "passive_revive_damage_reduction", 1)
                == "pain_killer")
            assert(provider:resolve_mapping("temporary", "passive_revive_damage_reduction", 2)
                == "pain_killer_aced")
            assert(provider:resolve_mapping("temporary", "mrwi_health_invulnerable", 1)
                == "copycat_health_invul")
            assert(provider:resolve_mapping("temporary", "mrwi_health_invulnerable", 2)
                == "copycat_health_invul_passive")
        ''')

    def test_missing_invalid_unknown_and_false_sentinel_are_ignored(self):
        lua = self.make_runtime()
        lua.execute('''
            local provider = kyohud.hudlist
            assert(provider:resolve_mapping("temporary", "berserker_damage_multiplier") == nil)
            assert(provider:resolve_mapping("temporary", "berserker_damage_multiplier", 3) == nil)
            assert(provider:resolve_mapping("property", "bipod_deploy_multiplier", 1) == nil)
            assert(provider:resolve_mapping("temporary", "not_real", 1) == nil)
            assert(provider:resolve_mapping("not_real", "anything", 1) == nil)
        ''')

    def test_team_mapping_requires_category_upgrade_and_explicit_level(self):
        lua = self.make_runtime()
        lua.execute('''
            local provider = kyohud.hudlist
            assert(provider:resolve_team_mapping("damage_dampener", "hostage_multiplier", 9)
                == "crew_chief_9")
            assert(provider:resolve_team_mapping("stamina", "hostage_multiplier", 9)
                == "crew_chief_9")
            assert(provider:resolve_team_mapping("health", "hostage_multiplier", 9)
                == "crew_chief_9")
            assert(provider:resolve_team_mapping("damage_dampener", "hostage_multiplier", 1) == nil)
            assert(provider:resolve_team_mapping("damage_dampener", "hostage_multiplier") == nil)
        ''')

    def test_converging_mappings_refresh_one_entry_without_reordering(self):
        lua = self.make_runtime()
        lua.execute('''
            local provider = kyohud.hudlist
            provider:event("buff", "activate", "first", {t = 100})
            local id_a = provider:resolve_team_mapping("damage_dampener", "hostage_multiplier", 9)
            local id_b = provider:resolve_team_mapping("stamina", "hostage_multiplier", 9)
            provider:event("buff", "activate", id_a, {t = 101})
            local first_entry = provider:get_buffs()[id_a]
            provider:event("buff", "activate", id_b, {t = 102})
            assert(provider:get_buffs()[id_a] == first_entry)
            assert(first_entry.t == 102)
            assert(provider:get_arrival_order()[1] == "first")
            assert(provider:get_arrival_order()[2] == "crew_chief_9")
            assert(provider:get_arrival_order()[3] == nil)
        ''')

    def test_aliases_and_provenance_are_explicit_and_deterministic(self):
        lua = self.make_runtime()
        lua.execute('''
            local catalog = kyohud.hudlist_catalog
            assert(catalog:resolve_alias("pain_killer") == "painkiller")
            assert(catalog:resolve_alias("pain_killer_aced") == "painkiller")
            assert(catalog:resolve_alias("overkill") == "overkill")
            assert(catalog.provenance.families.official ~= nil)
            assert(catalog.provenance.families.current_game ~= nil)
            assert(catalog.provenance.families.modern_verified ~= nil)
            assert(catalog.provenance.families.direct ~= nil)
            assert(catalog.provenance.families.uncertain ~= nil)
            assert(catalog.direct_ids.literals.messiah.source == "direct")
            assert(catalog.direct_ids.literals.calm.provenance == "official")
            assert(catalog.direct_ids.literals.tag_team.provenance == "modern_verified")
            assert(catalog.direct_ids.dynamic.grenade_debuff.expression == 'id .. "_debuff"')
            assert(catalog.direct_ids.dynamic.grenade_debuff.possible_ids == nil)
        ''')

    def test_resolution_metadata_keeps_mapping_identity_and_provenance(self):
        lua = self.make_runtime()
        lua.execute('''
            local provider = kyohud.hudlist
            local temporary = provider:resolve_mapping_info(
                "temporary", "mrwi_health_invulnerable", 2
            )
            assert(temporary.id == "copycat_health_invul_passive")
            assert(temporary.category == "temporary")
            assert(temporary.upgrade == "mrwi_health_invulnerable")
            assert(temporary.level == 2)
            assert(temporary.source == "upgrade_mapping")
            assert(temporary.provenance == "modern_verified")

            local team = provider:resolve_team_mapping_info(
                "stamina", "hostage_multiplier", 9
            )
            assert(team.id == "crew_chief_9")
            assert(team.category == "stamina")
            assert(team.upgrade == "hostage_multiplier")
            assert(team.level == 9)
            assert(team.source == "team_mapping")
            assert(team.provenance == "modern_verified")
        ''')

    def test_passive_health_regen_uses_specialization_17_tier_3_icon(self):
        lua = self.make_runtime()
        lua.execute('''
            local def = kyohud.hudlist_catalog.definitions.passive_health_regen
            assert(def.perks ~= nil, "passive_health_regen must have perks")
            assert(def.perks[1] == 1, "perks[1] must be 1")
            assert(def.perks[2] == 0, "perks[2] must be 0")
            assert(def.texture_bundle_folder == "chico",
                "texture_bundle_folder must be chico, got " .. tostring(def.texture_bundle_folder))
            assert(def.hud_tweak == nil,
                "passive_health_regen must not have hud_tweak, got " .. tostring(def.hud_tweak))
            assert(def.icon_provenance == "skilltreetweakdata specialization 17 tier 3 chico icon_xy {1, 0}",
                "unexpected provenance: " .. tostring(def.icon_provenance))
        ''')

    def test_external_hud_tables_are_not_mutated_or_replaced(self):
        lua = self.make_runtime()
        lua.execute('''
            assert(HUDList.untouched == true)
            assert(HUDListManager.BUFFS.untouched == true)
            assert(HUDList.hudlist_catalog == nil)
            assert(HUDListManager.hudlist_catalog == nil)
            assert(_G.GameInfoManager == nil)
        ''')


if __name__ == "__main__":
    unittest.main()