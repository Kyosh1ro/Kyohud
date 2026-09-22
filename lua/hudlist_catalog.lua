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
            mrwi_health_invulnerable = { "copycat_health_invul_passive" },
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
            copr_ability = { source = "direct" },
            copycat_health_invul_debuff = { source = "direct" },
            copycat_health_invul_passive = { source = "direct" },
            copycat_health_shot_debuff = { source = "direct" },
            crew_chief_1 = { source = "direct" },
            crew_throwable_regen = { source = "direct" },
            crew_inspire_debuff = { source = "direct", provenance = "modern_verified" },
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
            muscle_regen = { source = "direct", provenance = "current_game" },
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
            hostage_taker = { source = "direct", provenance = "current_game" },
            crew_health_regen = { source = "direct", provenance = "current_game" },
            berserker = { source = "direct", provenance = "current_game" },
            berserker_aced = { source = "direct", provenance = "current_game" },
            yakuza_recovery = { source = "direct", provenance = "current_game" },
            yakuza_speed = { source = "direct", provenance = "current_game" },
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

    -- Minimal autonomous presentation metadata. Static coordinates mirror the
    -- verified HUDList lineage; skill_id lets current game data override them.
    definitions = {
        overkill = { skills_new = { 3, 2 }, skill_id = "overkill", class = "TimedBuffItem", priority = 4 },
        biker = { perks = { 0, 0 }, texture_bundle_folder = "wild", class = "TimedBuffItem", priority = 4, state = "timed_stack", show_stack_count = true },
        grinder = { perks = { 4, 6 }, class = "TimedBuffItem", priority = 4, state = "timed_stack", show_stack_count = true },
        grinder_debuff = { perks = { 4, 6 }, class = "TimedBuffItem", priority = 8, state = "timed" },
        crew_chief = { perks = { 0, 0 }, class = "TeamBuffItem", priority = 4, state = "team", show_team_level = true },
        maniac = { perks = { 0, 0 }, texture_bundle_folder = "coco", class = "BuffItem", priority = 4, state = "progress", show_value = "-%.1f" },
        maniac_debuff = { perks = { 0, 0 }, texture_bundle_folder = "coco", class = "TimedBuffItem", priority = 8, state = "timed" },
        sicario_dodge = { perks = { 1, 0 }, texture_bundle_folder = "max", class = "BuffItem", priority = 4, state = "value", show_value = true },
        sicario_dodge_debuff = { perks = { 1, 0 }, texture_bundle_folder = "max", class = "TimedBuffItem", priority = 8, state = "timed" },
        chico_injector = { perks = { 0, 0 }, texture_bundle_folder = "chico", class = "TimedBuffItem", priority = 4, state = "timed" },
        chico_injector_debuff = { perks = { 0, 0 }, texture_bundle_folder = "chico", class = "TimedBuffItem", priority = 8, state = "timed" },
        copr_ability = { perks = { 0, 0 }, texture_bundle_folder = "copr", class = "TimedBuffItem", priority = 4, state = "timed" },
        copr_ability_debuff = { perks = { 0, 0 }, texture_bundle_folder = "copr", class = "TimedBuffItem", priority = 8, state = "timed" },
        copycat_health_invul = { perks = { 3, 0 }, texture_bundle_folder = "mrwi", class = "TimedBuffItem", priority = 4, state = "timed" },
        copycat_health_invul_debuff = { perks = { 3, 0 }, texture_bundle_folder = "mrwi", class = "TimedBuffItem", priority = 8, state = "timed" },
        copycat_health_invul_passive = { perks = { 3, 0 }, texture_bundle_folder = "mrwi", class = "TimedBuffItem", priority = 8, state = "timed" },
        copycat_health_shot_debuff = { perks = { 1, 0 }, texture_bundle_folder = "mrwi", class = "TimedBuffItem", priority = 8, state = "timed" },
        pocket_ecm_jammer = { perks = { 0, 0 }, texture_bundle_folder = "joy", class = "TimedBuffItem", priority = 4, state = "sources" },
        pocket_ecm_jammer_debuff = { perks = { 0, 0 }, texture_bundle_folder = "joy", class = "TimedBuffItem", priority = 8, state = "timed" },
        uppers = { skills_new = { 0, 0 }, skill_id = "tea_cookies", class = "BuffItem", priority = 4, state = "persistent" },
        uppers_debuff = { skills_new = { 0, 0 }, skill_id = "tea_cookies", class = "TimedBuffItem", priority = 8, state = "timed" },
        smoke_screen_grenade = {
            perks = { 0, 0 }, texture_bundle_folder = "max", class = "TimedBuffItem",
            priority = 4, state = "sources", show_stack_count = false,
        },
        -- Underdog basic (dmg_multiplier_outnumbered) and aced
        -- (dmg_dampener_outnumbered) share one skill, one timer and one icon.
        -- They are merged into this single timed card; the aced dampener is
        -- routed here below so both temporary upgrades feed the same cell.
        underdog = { skills_new = { 2, 1 }, skill_id = "underdog",
            class = "TimedBuffItem", priority = 4, state = "timed" },
        inspire = { skills_new = { 0, 0 }, skill_id = "inspire", class = "TimedBuffItem", priority = 4, state = "timed" },
        crew_inspire_debuff = { skills_new = { 0, 0 }, skill_id = "inspire", class = "TimedBuffItem", priority = 8, state = "timed" },
        partner_in_crime = { skills_new = { 1, 10 }, skill_id = "control_freak", class = "BuffItemBase", priority = 3, show_stack_count = false },
        partner_in_crime_aced = { skills_new = { 1, 10 }, skill_id = "control_freak", class = "BuffItemBase", priority = 3, show_stack_count = false },
        messiah = { skills_new = { 0, 0 }, skill_id = "messiah", class = "BuffItemBase", priority = 3 },
        muscle_regen = { perks = { 4, 1 }, class = "TimedBuffItem", priority = 4,
            state = "passive_regen", value_kind = "health_ratio_per_tick",
            display_mode = "health_per_interval", show_value = true,
            icon_provenance = "skilltreetweakdata specialization 2 tier 9 icon_xy" },
        hostage_taker = { skills_new = { 2, 10 }, skill_id = "black_marketeer",
            class = "TimedBuffItem", priority = 4, state = "passive_regen",
            value_kind = "health_ratio_per_tick", display_mode = "health_per_interval",
            show_value = true, icon_provenance = "skilltree skill black_marketeer icon_xy" },
        crew_health_regen = { hud_tweak = "equipment_doctor_bag", class = "TimedBuffItem",
            priority = 4, state = "passive_regen", value_kind = "health_points_per_tick",
            display_mode = "health_per_interval", show_value = true,
            icon_provenance = "verified native equipment_doctor_bag fallback" },
        berserker = { skills_new = { 2, 2 }, skill_id = "wolverine",
            class = "BuffItem", priority = 4, state = "value",
            value_kind = "melee_bonus_fraction", display_mode = "bonus_percent",
            show_value = true, icon_provenance = "skilltree skill wolverine icon_xy" },
        berserker_aced = { skills_new = { 2, 2 }, skill_id = "wolverine",
            class = "BuffItem", priority = 4, state = "value",
            value_kind = "weapon_bonus_fraction", display_mode = "bonus_percent",
            show_value = true, icon_provenance = "skilltree skill wolverine icon_xy" },
        yakuza_recovery = { perks = { 2, 7 },
            class = "BuffItem", priority = 4, state = "value",
            value_kind = "armor_recovery_time_reduction_fraction",
            display_mode = "reduction_percent", show_value = true,
            icon_provenance = "skilltreetweakdata specialization 12 tier 9 icon_xy" },
        yakuza_speed = { perks = { 2, 7 },
            class = "BuffItem", priority = 4, state = "value",
            value_kind = "movement_speed_bonus_fraction", display_mode = "bonus_percent",
            show_value = true,
            icon_provenance = "skilltreetweakdata specialization 12 tier 9 icon_xy" },
        passive_health_regen = { perks = { 1, 0 }, texture_bundle_folder = "chico",
            class = "BuffItemBase", priority = 2, state = "stat_card",
            value_kind = "health_ratio_per_tick", display_mode = "percent",
            show_value = true,
            icon_provenance = "skilltreetweakdata specialization 17 tier 3 chico icon_xy {1, 0}" },
        damage_increase = { hud_tweak = "equipment_chrome_mask", class = "BuffItemBase",
            priority = 2, state = "stat_card", value_kind = "final_multiplier",
            display_mode = "bonus_percent", show_value = true },
        damage_reduction = { skills_new = { 10, 8 }, skill_id = "dire_need",
            class = "BuffItemBase", priority = 2, state = "stat_card",
            value_kind = "damage_taken_multiplier", display_mode = "reduction_percent",
            show_value = true },
        melee_damage_increase = { hud_tweak = "throwing_axe",
            class = "BuffItemBase", priority = 2, state = "stat_card",
            value_kind = "final_multiplier", display_mode = "multiplier",
            show_value = true, icon_rotation = -90,
            icon_provenance = "tweak_data.hud_icons.throwing_axe guis/textures/pd2/equipment_02 {0,0,32,32}" },
        total_dodge_chance = { perks = { 7, 3 }, class = "BuffItemBase",
            priority = 2, state = "stat_card", value_kind = "final_fraction",
            display_mode = "percent", show_value = true,
            icon_provenance = "skilltreetweakdata specialization 7 (Burglar) tier 5 icon_xy {7, 3}" },
        equipped_perk_deck = { hud_tweak = "pd2_generic_tickbox", class = "BuffItemBase", priority = 1, ignore = true },
    },
    routes = {
        partner_in_crime_aced = { "partner_in_crime" },
        biker = { "biker" },
        grinder = { "grinder" },
        grinder_debuff = { "grinder_debuff" },
        maniac = { "maniac" },
        maniac_debuff = { "maniac_debuff" },
        sicario_dodge_debuff = { "sicario_dodge_debuff" },
        chico_injector_debuff = { "chico_injector_debuff" },
        copr_ability = { "copr_ability" },
        copr_ability_debuff = { "copr_ability_debuff" },
        copycat_health_invul = { "copycat_health_invul" },
        copycat_health_invul_debuff = { "copycat_health_invul_debuff" },
        copycat_health_shot_debuff = { "copycat_health_shot" },
        pocket_ecm_jammer_debuff = { "pocket_ecm_jammer_debuff" },
        smoke_screen_grenade_debuff = { "smoke_screen_grenade_debuff" },
        tag_team_debuff = { "tag_team_debuff" },
        uppers = { "uppers" },
        uppers_debuff = { "uppers_debuff" },
        crew_inspire_debuff = { "crew_inspire_debuff" },
        -- Fold the Underdog aced dampener into the single Underdog card so the
        -- basic damage bonus and the aced damage reduction share one icon.
        underdog_aced = { "underdog" },
    },
}

-- Visual descriptors reconstructed from the HUDList lineage and checked against
-- current PAYDAY 2 skill/perk identifiers.  Keeping this inventory explicit
-- prevents ensure_definition() from silently turning a missed producer into an
-- indistinguishable generic tickbox.
local function skill_icon(skill_id, atlas)
    return {
        skill_id = skill_id,
        skill_atlas = atlas,
        icon_provenance = "current skilltree skill " .. skill_id .. " icon_xy",
    }
end

local function perk_icon(x, y, folder, source)
    return {
        perks = { x, y },
        texture_bundle_folder = folder,
        icon_provenance = source or "verified HUDList specialization icon coordinates",
    }
end

local function hud_icon(id, source)
    return {
        hud_tweak = id,
        icon_provenance = source or "verified native hud icon " .. id,
    }
end

local function intentional_fallback(reason)
    return {
        hud_tweak = "pd2_generic_tickbox",
        intentional_fallback = true,
        fallback_reason = reason,
        icon_provenance = "reviewed generic fallback; no verified dedicated asset",
    }
end


local VISUALS = {
    aggressive_reload_aced = skill_icon("speedy_reload"),
    ammo_efficiency = skill_icon("single_shot_ammo_return"),
    ammo_give_out_debuff = perk_icon(5, 5),
    anarchist_armor_recovery_debuff = perk_icon(0, 1, "opera"),
    armor_break_invulnerable = perk_icon(6, 1),
    armor_break_invulnerable_debuff = perk_icon(6, 1),
    armorer = perk_icon(6, 0),
    berserker = skill_icon("wolverine"),
    berserker_aced = skill_icon("wolverine"),
    biker = perk_icon(0, 0, "wild"),
    bloodthirst_aced = skill_icon("bloodthirst"),
    bloodthirst_basic = skill_icon("bloodthirst"),
    bullet_storm = skill_icon("ammo_reservoir"),
    bulletproof = perk_icon(6, 2),
    bullseye_debuff = skill_icon("prison_wife"),
    chico_injector = perk_icon(0, 0, "chico"),
    chico_injector_debuff = perk_icon(0, 0, "chico"),
    close_contact = perk_icon(5, 4),
    combat_medic_interaction = skill_icon("combat_medic"),
    copr_ability = perk_icon(0, 0, "copr"),
    copr_ability_debuff = perk_icon(0, 0, "copr"),
    copycat_health_invul = perk_icon(3, 0, "mrwi"),
    copycat_health_invul_debuff = perk_icon(3, 0, "mrwi"),
    copycat_health_invul_passive = perk_icon(3, 0, "mrwi"),
    copycat_health_shot = perk_icon(1, 0, "mrwi"),
    copycat_health_shot_debuff = perk_icon(1, 0, "mrwi"),
    crew_chief = perk_icon(2, 0),
    crew_health_regen = hud_icon("skill_5", "verified native AI skill icon skill_5"),
    crew_inspire_debuff = hud_icon("ability_1", "verified native AI ability icon ability_1"),
    crew_throwable_regen = hud_icon("skill_7", "verified native AI skill icon skill_7"),
    delayed_damage = perk_icon(3, 0, "myh"),
    delayed_damage_debuff = perk_icon(3, 0, "myh"),
    desperado = skill_icon("expert_handling"),
    die_hard = skill_icon("show_of_force"),
    dire_need = skill_icon("dire_need"),
    endurance = skill_icon("triathlete"),
    forced_friendship = skill_icon("triathlete", "skills"),
    frenzy = skill_icon("frenzy"),
    grinder = perk_icon(4, 6),
    grinder_debuff = perk_icon(4, 6),
    hostage_situation = perk_icon(0, 1),
    hostage_taker = skill_icon("black_marketeer"),
    inspire = skill_icon("inspire"),
    inspire_debuff = skill_icon("inspire"),
    inspire_revive_debuff = skill_icon("inspire"),
    invulnerable_buff = hud_icon("csb_melee"),
    life_drain_debuff = perk_icon(7, 4),
    life_steal_debuff = hud_icon("csb_lifesteal"),
    lock_n_load = skill_icon("shock_and_awe"),
    maniac = perk_icon(0, 0, "coco"),
    maniac_debuff = perk_icon(0, 0, "coco"),
    medical_supplies_debuff = perk_icon(4, 5),
    melee_stack_damage = perk_icon(5, 4),
    messiah = skill_icon("messiah"),
    muscle_regen = perk_icon(4, 1),
    overdog = perk_icon(6, 4),
    overkill = skill_icon("overkill"),
    overkill_aced = skill_icon("overkill"),
    passive_health_regen = perk_icon(1, 0, "chico",
        "skilltreetweakdata specialization 17 tier 3 chico icon_xy {1, 0}"),
    painkiller = skill_icon("fast_learner"),
    partner_in_crime = skill_icon("control_freak"),
    partner_in_crime_aced = skill_icon("control_freak"),
    pocket_ecm_jammer = perk_icon(0, 0, "joy"),
    pocket_ecm_jammer_debuff = perk_icon(0, 0, "joy"),
    pocket_ecm_kill_dodge = perk_icon(3, 0, "joy"),
    quick_fix = skill_icon("tea_time"),
    running_from_death = skill_icon("running_from_death"),
    second_wind = skill_icon("scavenger"),
    sicario_dodge = perk_icon(1, 0, "max"),
    sicario_dodge_debuff = perk_icon(1, 0, "max"),
    sixth_sense = skill_icon("chameleon"),
    smoke_screen_grenade = perk_icon(0, 0, "max"),
    smoke_screen_grenade_debuff = perk_icon(0, 0, "max"),
    sociopath_debuff = perk_icon(3, 5),
    swan_song = skill_icon("perseverance"),
    swan_song_aced = skill_icon("perseverance"),
    tag_team = perk_icon(0, 0, "ecp"),
    tag_team_debuff = perk_icon(0, 0, "ecp"),
    tooth_and_claw = perk_icon(0, 3),
    trigger_happy = skill_icon("trigger_happy"),
    underdog = skill_icon("underdog"),
    underdog_aced = skill_icon("underdog"),
    unseen_strike = skill_icon("unseen_strike"),
    unseen_strike_debuff = skill_icon("unseen_strike"),
    up_you_go = skill_icon("up_you_go"),
    uppers = skill_icon("tea_cookies"),
    uppers_debuff = skill_icon("tea_cookies"),
    yakuza_recovery = perk_icon(2, 7),
    yakuza_speed = perk_icon(2, 7),

    damage_increase = hud_icon("equipment_chrome_mask"),
    damage_reduction = skill_icon("dire_need"),
    melee_damage_increase = { hud_tweak = "throwing_axe", icon_rotation = -90,
        icon_provenance = "tweak_data.hud_icons.throwing_axe guis/textures/pd2/equipment_02 {0,0,32,32}" },
    total_dodge_chance = perk_icon(7, 3, nil,
        "skilltreetweakdata specialization 7 (Burglar) tier 5 icon_xy {7, 3}"),
    equipped_perk_deck = hud_icon("pd2_generic_tickbox",
        "intentional bootstrap icon replaced by the equipped specialization icon"),

    calm = intentional_fallback("official producer has no dedicated HUDList visual"),
    cc_passive_damage_reduction = intentional_fallback("legacy direct ID has no verified dedicated asset"),
    movement_dodge = intentional_fallback("source value is represented by the total dodge composite"),
    self_healer_debuff = intentional_fallback("legacy direct ID has no verified dedicated asset"),
    some_invulnerability_debuff = intentional_fallback("dynamic invulnerability source has no stable native icon"),
    virtue_debuff = intentional_fallback("legacy direct ID has no verified dedicated asset"),
}

for id, visual in pairs(VISUALS) do
    local definition = Catalog.definitions[id] or {
        class = "BuffItemBase",
        priority = string.match(id, "_debuff$") and 8 or 4,
    }
    Catalog.definitions[id] = definition
    if visual.skill_id or visual.skills_new or visual.skills or visual.perks or visual.texture then
        definition.hud_tweak = nil
    end
    for key, value in pairs(visual) do definition[key] = value end
    if definition.hud_tweak == "pd2_generic_tickbox" and id == "equipped_perk_deck" then
        definition.intentional_fallback = true
        definition.fallback_reason = "replaced at runtime by the equipped specialization icon"
    end
end

local DYNAMIC_IDS = {
    grenade = {
        chico_injector = { public_id = "chico_injector_debuff", type = "ability",
            suffix = "_debuff", presentation = true, provenance = "modern_verified" },
        copr_ability = { public_id = "copr_ability_debuff", type = "ability",
            suffix = "_debuff", presentation = true, provenance = "modern_verified" },
        pocket_ecm_jammer = { public_id = "pocket_ecm_jammer_debuff", type = "ability",
            suffix = "_debuff", presentation = true, provenance = "modern_verified" },
        smoke_screen_grenade = { public_id = "smoke_screen_grenade_debuff", type = "ability",
            suffix = "_debuff", presentation = true, provenance = "modern_verified" },
        tag_team = { public_id = "tag_team_debuff", type = "ability",
            suffix = "_debuff", presentation = true, provenance = "modern_verified" },
    },
    custom = {
        crew_inspire = { public_id = "crew_inspire_debuff", type = "team_ability",
            suffix = "_debuff", presentation = true, provenance = "current_game" },
    },
}

local function ensure_definition(id)
    if type(id) ~= "string" then return end
    id = Catalog.aliases[id] or id
    if not Catalog.definitions[id] then
        Catalog.definitions[id] = {
            hud_tweak = "pd2_generic_tickbox",
            class = "BuffItemBase",
            priority = string.match(id, "_debuff$") and 8 or 4,
        }
    end
end

local function collect_mapping_definitions(mapping)
    if type(mapping) == "string" then
        ensure_definition(mapping)
    elseif type(mapping) == "table" and type(mapping.id) == "string" then
        ensure_definition(mapping.id)
    elseif type(mapping) == "table" then
        for _, value in pairs(mapping) do collect_mapping_definitions(value) end
    end
end

for _, mappings in pairs(Catalog.mappings) do
    collect_mapping_definitions(mappings)
end
for id in pairs(Catalog.direct_ids.literals) do
    ensure_definition(id)
end

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

function Catalog:resolve_dynamic(kind, native_id)
    local domain = type(kind) == "string" and DYNAMIC_IDS[kind]
    local data = domain and type(native_id) == "string" and domain[native_id]
    return type(data) == "table" and type(data.public_id) == "string"
        and data.public_id or nil
end

kyohud.hudlist_catalog = Catalog