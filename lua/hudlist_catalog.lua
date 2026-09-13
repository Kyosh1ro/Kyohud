-- hudlist_catalog.lua — verified mappings for KyoHUD's HUDList provider

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud

if kyohud.hudlist_catalog then return end

local Catalog = {
    provenance = {
        official_project = "HUDList / GameInfoManager",
        official_commit = "94f10a0bb6d23ab25d0636222378f1755ae6a5b7",
        modern_reference = "VanillaHUD+ 3.4.17 (behavioral comparison only)",
        families = {
            official = "GIM_Buff_Plugin.lua:19-107",
            current_game = "PAYDAY 2 upgradestweakdata.lua; identifiers and levels only",
            modern_verified = "VanillaHUD+ GameInfoManager.lua:575-674, checked against current game data",
            direct = "Verified producer inventory outside GameInfoManager._BUFFS",
            uncertain = "Dynamic producer expressions retained without enumerating possible results",
        },
    },

    -- Strings apply at every level. Arrays preserve exact level-indexed mappings.
    -- false is an intentional historical sentinel and never resolves to a buff ID.
    mappings = {
        temporary = {
            bullet_storm = "bullet_storm",
            chico_injector = "chico_injector",
            damage_speed_multiplier = "second_wind",
            team_damage_speed_multiplier_received = "second_wind",
            dmg_multiplier_outnumbered = "underdog",
            dmg_dampener_outnumbered = "underdog_aced",
            dmg_dampener_outnumbered_strong = "overdog",
            dmg_dampener_close_contact = {
                "close_contact_1", "close_contact_2", "close_contact_3",
            },
            overkill_damage_multiplier = "overkill",
            passive_revive_damage_reduction = { "pain_killer", "pain_killer_aced" },
            berserker_damage_multiplier = { "swan_song", "swan_song_aced" },
            first_aid_damage_reduction = "quick_fix",
            increased_movement_speed = "running_from_death_aced",
            reload_weapon_faster = "running_from_death_basic",
            revive_damage_reduction = "combat_medic",
            revived_damage_resist = "up_you_go",
            swap_weapon_faster = "running_from_death_basic",
            melee_life_leech = "life_drain_debuff",
            loose_ammo_restore_health = "medical_supplies_debuff",
            loose_ammo_give_team = "ammo_give_out_debuff",
            armor_break_invulnerable = "armor_break_invulnerable_debuff",
            single_shot_fast_reload = "aggressive_reload_aced",
            unseen_strike = { "unseen_strike", "unseen_strike" },
            pocket_ecm_kill_dodge = "pocket_ecm_kill_dodge",
            copr_ability = "copr_ability",
            mrwi_health_invulnerable = {
                "copycat_health_invul", "copycat_health_invul_passive",
            },
            bloodthirst_reload_speed = "bloodthirst_aced",
            revived_damage_reduction = "pain_killer",
        },
        property = {
            bloodthirst_reload_speed = { "bloodthirst_aced" },
            revived_damage_reduction = { "pain_killer" },
            revive_damage_reduction = { "combat_medic_interaction" },
            bullet_storm = { "bullet_storm" },
            shock_and_awe_reload_multiplier = { "lock_n_load" },
            trigger_happy = { "trigger_happy" },
            desperado = { "desperado" },
            bipod_deploy_multiplier = false,
        },
        cooldown = {
            long_dis_revive = "inspire_revive_debuff",
        },
        team = {
            damage_dampener = {
                hostage_multiplier = { id = "crew_chief_9", level = 9 },
                team_damage_reduction = { id = "crew_chief_1", level = 1 },
            },
            stamina = {
                multiplier = { id = "endurance", level = 0 },
                passive_multiplier = { id = "crew_chief_3", level = 3 },
                hostage_multiplier = { id = "crew_chief_9", level = 9 },
            },
            health = {
                passive_multiplier = { id = "crew_chief_5", level = 5 },
                hostage_multiplier = { id = "crew_chief_9", level = 9 },
            },
            armor = {
                multiplier = { id = "crew_chief_7", level = 7 },
                regen_time_multiplier = { id = "bulletproof", level = 0 },
                passive_regen_time_multiplier = { id = "armorer_9", level = 9 },
            },
            damage = {
                hostage_absorption = { id = "forced_friendship", level = 0 },
            },
        },
    },

    -- Lineage is adjacent to the mappings so their scalar/array/record shapes stay intact.
    mapping_provenance = {
        temporary = {
            bullet_storm = "modern_verified",
            dmg_dampener_close_contact = "modern_verified",
            passive_revive_damage_reduction = "modern_verified",
            increased_movement_speed = "modern_verified",
            reload_weapon_faster = "modern_verified",
            revive_damage_reduction = "modern_verified",
            swap_weapon_faster = "modern_verified",
            copr_ability = "modern_verified",
            mrwi_health_invulnerable = "modern_verified",
            bloodthirst_reload_speed = "modern_verified",
            revived_damage_reduction = "modern_verified",
        },
        property = {},
        cooldown = {},
        team = {
            damage_dampener = {
                hostage_multiplier = "modern_verified",
                team_damage_reduction = "modern_verified",
            },
            stamina = {
                multiplier = "modern_verified",
                passive_multiplier = "modern_verified",
                hostage_multiplier = "modern_verified",
            },
            health = {
                passive_multiplier = "modern_verified",
                hostage_multiplier = "modern_verified",
            },
            armor = {
                multiplier = "modern_verified",
                regen_time_multiplier = "modern_verified",
                passive_regen_time_multiplier = "modern_verified",
            },
            damage = { hostage_absorption = "modern_verified" },
        },
    },

    aliases = {
        pain_killer = "painkiller",
        pain_killer_aced = "painkiller",
        close_contact_1 = "close_contact",
        close_contact_2 = "close_contact",
        close_contact_3 = "close_contact",
        running_from_death_basic = "running_from_death",
        running_from_death_aced = "running_from_death",
        crew_chief_1 = "crew_chief",
        crew_chief_3 = "crew_chief",
        crew_chief_5 = "crew_chief",
        crew_chief_7 = "crew_chief",
        crew_chief_9 = "crew_chief",
        armorer_9 = "armorer",
    },

    -- These are producer outputs, not upgrade mappings. Producers are added later.
    direct_ids = {
        literals = {
            ammo_efficiency = { source = "direct" },
            anarchist_armor_recovery_debuff = { source = "direct" },
            armor_break_invulnerable = { source = "direct" },
            biker = { source = "direct" },
            bloodthirst_basic = { source = "direct" },
            bullseye_debuff = { source = "direct" },
            calm = { source = "direct", provenance = "official" },
            cc_passive_damage_reduction = { source = "direct" },
            combat_medic_passive = { source = "direct" },
            copr_ability = { source = "direct" },
            copycat_health_invul_debuff = { source = "direct" },
            copycat_health_invul_passive = { source = "direct" },
            copycat_health_shot_debuff = { source = "direct" },
            crew_chief_1 = { source = "direct" },
            crew_throwable_regen = { source = "direct" },
            delayed_damage = { source = "direct" },
            delayed_damage_debuff = { source = "direct" },
            desperado = { source = "direct" },
            die_hard = { source = "direct" },
            dire_need = { source = "direct" },
            frenzy = { source = "direct" },
            grinder = { source = "direct" },
            grinder_debuff = { source = "direct" },
            hostage_situation = { source = "direct" },
            inspire = { source = "direct" },
            inspire_debuff = { source = "direct" },
            invulnerable_buff = { source = "direct" },
            life_steal_debuff = { source = "direct" },
            lock_n_load = { source = "direct" },
            maniac = { source = "direct" },
            maniac_debuff = { source = "direct" },
            melee_stack_damage = { source = "direct" },
            messiah = { source = "direct" },
            movement_dodge = { source = "direct" },
            overkill_aced = { source = "direct" },
            partner_in_crime = { source = "direct" },
            partner_in_crime_aced = { source = "direct" },
            pocket_ecm_jammer = { source = "direct" },
            self_healer_debuff = { source = "direct" },
            sicario_dodge = { source = "direct" },
            sicario_dodge_debuff = { source = "direct" },
            sixth_sense = { source = "direct" },
            smoke_screen_grenade = { source = "direct" },
            sociopath_debuff = { source = "direct" },
            some_invulnerability_debuff = { source = "direct" },
            tag_team = { source = "direct", provenance = "modern_verified" },
            tooth_and_claw = { source = "direct" },
            trigger_happy = { source = "direct" },
            unseen_strike_debuff = { source = "direct" },
            uppers = { source = "direct" },
            uppers_debuff = { source = "direct" },
            virtue_debuff = { source = "direct" },
        },
        dynamic = {
            grenade_use = { expression = 'id .. "_use"', provenance = "official" },
            grenade_debuff = { expression = 'id .. "_debuff"', provenance = "modern_verified" },
            equipped_grenade_debuff = {
                expression = 'equipped_grenade .. "_debuff"',
                provenance = "modern_verified",
            },
            custom_cooldown_debuff = {
                expression = 'upgrade .. "_debuff"',
                provenance = "modern_verified",
            },
            health_ratio = { expression = "data.buff_id", provenance = "official" },
            passive_regen = { expression = "buff_id", provenance = "official" },
        },
    },

    -- Compatibility metadata consumed by the existing KyoHUD presentation bridge.
    definitions = {
        overkill = { class = "TimedBuffItem", priority = 0 },
        biker = { class = "TimedBuffItem", priority = 0, state = "timed_stack", show_stack_count = true },
        grinder = { class = "TimedBuffItem", priority = 0, state = "timed_stack", show_stack_count = true },
        grinder_debuff = { class = "TimedBuffItem", priority = 0, state = "timed" },
        crew_chief = { class = "TeamBuffItem", priority = 0, state = "team", show_team_level = true },
    },
    routes = {
        overkill = { "overkill" },
        biker = { "biker" },
        grinder = { "grinder" },
        grinder_debuff = { "grinder_debuff" },
        crew_chief = { "crew_chief" },
    },
}

function Catalog:resolve(category, upgrade, level)
    if category == "team" then return nil end
    local group = self.mappings[category]
    local mapping = group and group[upgrade]
    if type(mapping) == "string" then return mapping end
    if type(mapping) ~= "table" then return nil end
    local numeric_level = tonumber(level)
    if not numeric_level or numeric_level % 1 ~= 0 then return nil end
    local id = mapping[numeric_level]
    return type(id) == "string" and id or nil
end

function Catalog:resolve_info(category, upgrade, level)
    local id = self:resolve(category, upgrade, level)
    if not id then return nil end
    local sources = self.mapping_provenance[category]
    return {
        id = id,
        category = category,
        upgrade = upgrade,
        level = tonumber(level),
        source = "upgrade_mapping",
        provenance = sources and sources[upgrade] or "official",
    }
end

function Catalog:resolve_team(category, upgrade, level)
    local categories = self.mappings.team
    local mapping = categories[category] and categories[category][upgrade]
    local numeric_level = tonumber(level)
    if type(mapping) ~= "table" or not numeric_level then return nil end
    if mapping.level ~= numeric_level then return nil end
    return type(mapping.id) == "string" and mapping.id or nil
end

function Catalog:resolve_team_info(category, upgrade, level)
    local id = self:resolve_team(category, upgrade, level)
    if not id then return nil end
    local category_sources = self.mapping_provenance.team[category]
    return {
        id = id,
        category = category,
        upgrade = upgrade,
        level = tonumber(level),
        source = "team_mapping",
        provenance = category_sources and category_sources[upgrade] or "official",
    }
end

function Catalog:resolve_alias(id)
    return self.aliases[id] or id
end

function Catalog:resolve_team_public(category, upgrade, level)
    local event_id = self:resolve_team(category, upgrade, level)
    return event_id and self:resolve_alias(event_id) or nil, event_id
end

kyohud.hudlist_catalog = Catalog