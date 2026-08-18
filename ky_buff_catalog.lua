if not Kyosh1roHUD then
    Kyosh1roHUD = {}
end

local KH = Kyosh1roHUD

if KH.BUFF_CATEGORIES and KH.BUFF_COLORS and KH.BUFF_MAP and KH.UPGRADE_TO_BUFF and KH.BUFF_SOURCE_TARGETS
    and KH.BuildDefaultBuffToggles and KH.GetSortedBuffIdsForCategory and KH.GetBuffTargets then
    return
end

KH.BUFF_CATEGORIES = {
    mastermind = "Mastermind",
    enforcer = "Enforcer",
    technician = "Technician",
    ghost = "Ghost",
    fugitive = "Fugitive",
    perk = "Perk Decks",
    debuff = "Debuffs",
    team = "Team Buffs",
    player_action = "Player Actions",
    gage = "Gage Boosts",
    ai = "AI Skills",
}

-- Palette néon tactique propre à Kyosh1ro HUD. Les entrées de BUFF_MAP
-- référencent ces rôles par leur nom afin que le catalogue ne dépende pas
-- des objets Color du moteur au moment de son chargement.
KH.BUFF_COLORS = {
    debuff = "FF5F78",
    team = "52D6FF",
    damage_increase = "FF8A3D",
    damage_reduction = "6C8CFF",
    melee_damage_increase = "D66BFF",
    passive_health_regen = "4ADE9B",
    total_dodge_chance = "F5D547",
}

KH.BUFF_MAP = {
    aggressive_reload_aced = { skill_id = "speedy_reload", skills_new = { 1, 1 }, category = "mastermind", default_show = true },
    inspire = { skill_id = "inspire", skills_new = { 0, 9 }, category = "mastermind", default_show = true },
    inspire_debuff = { skill_id = "inspire", skills_new = { 0, 9 }, category = "debuff", color = "debuff", default_show = true },
    inspire_revive_debuff = { skill_id = "inspire", skills_new = { 0, 9 }, category = "debuff", color = "debuff", default_show = true },
    combat_medic = { skill_id = "combat_medic", skills_new = { 0, 0 }, category = "mastermind", default_show = true },
    combat_medic_passive = { skill_id = "combat_medic", skills_new = { 0, 0 }, category = "mastermind", default_show = false },
    quick_fix = { skill_id = "tea_time", skills_new = { 1, 3 }, category = "mastermind", default_show = false },
    uppers = { skill_id = "tea_cookies", skills_new = { 1, 2 }, category = "mastermind", default_show = true },
    painkiller = { skill_id = "fast_learner", skills_new = { 0, 4 }, category = "mastermind", default_show = false },
    hostage_taker = { skill_id = "black_marketeer", skills_new = { 1, 5 }, category = "mastermind", default_show = false },
    partner_in_crime = { skill_id = "control_freak", skills_new = { 0, 6 }, category = "mastermind", default_show = false },
    forced_friendship = { skill_id = "triathlete", skill_atlas = "skills", skills = { 0, 7 }, category = "team", color = "team", default_show = true },
    endurance = { skill_id = "triathlete", skills_new = { 0, 7 }, category = "team", color = "team", default_show = false },
    ammo_efficiency = { skill_id = "single_shot_ammo_return", skills_new = { 0, 8 }, category = "mastermind", default_show = true },

    overkill = { skill_id = "overkill", skills_new = { 2, 0 }, category = "enforcer", default_show = false },
    bullet_storm = { skill_id = "ammo_reservoir", skills_new = { 2, 3 }, category = "enforcer", default_show = true },
    die_hard = { skill_id = "show_of_force", skills_new = { 2, 4 }, category = "enforcer", default_show = false },
    underdog = { skill_id = "underdog", skills_new = { 2, 1 }, category = "enforcer", default_show = false },
    bullseye_debuff = { skill_id = "prison_wife", skills_new = { 2, 8 }, category = "debuff", color = "debuff", default_show = true },
    bulletproof = { perks = { 6, 2 }, category = "team", default_show = true },

    lock_n_load = { skill_id = "shock_and_awe", skills_new = { 3, 0 }, category = "technician", default_show = true },

    second_wind = { skill_id = "scavenger", skills_new = { 4, 1 }, category = "ghost", default_show = true },
    unseen_strike = { skill_id = "unseen_strike", skills_new = { 4, 5 }, category = "ghost", default_show = true },
    sixth_sense = { skill_id = "chameleon", skills_new = { 4, 7 }, category = "ghost", default_show = true },
    dire_need = { skill_id = "dire_need", skills_new = { 4, 8 }, category = "ghost", default_show = true },

    berserker = { skill_id = "wolverine", skills_new = { 5, 0 }, category = "fugitive", default_show = true },
    swan_song = { skill_id = "perseverance", skills_new = { 5, 3 }, category = "fugitive", default_show = false },
    trigger_happy = { skill_id = "trigger_happy", skills_new = { 5, 4 }, category = "fugitive", default_show = false },
    desperado = { skill_id = "expert_handling", skills_new = { 5, 5 }, category = "fugitive", default_show = true },
    bloodthirst_basic = { skill_id = "bloodthirst", skills_new = { 5, 6 }, category = "fugitive", default_show = false },
    bloodthirst_aced = { skill_id = "bloodthirst", skills_new = { 5, 6 }, category = "fugitive", default_show = true },
    up_you_go = { skill_id = "up_you_go", skills_new = { 5, 7 }, category = "fugitive", default_show = false },
    running_from_death = { skill_id = "running_from_death", skills_new = { 5, 8 }, category = "fugitive", default_show = true },
    messiah = { skill_id = "messiah", skills_new = { 5, 9 }, category = "fugitive", default_show = true },
    frenzy = { skill_id = "frenzy", skills_new = { 5, 10 }, category = "fugitive", default_show = false },

    armor_break_invulnerable = { perks = { 6, 1 }, category = "perk", default_show = true },
    armorer = { perks = { 6, 0 }, category = "team", color = "team", default_show = true },
    crew_chief = { perks = { 2, 0 }, category = "team", color = "team", default_show = true },
    muscle_regen = { perks = { 4, 1 }, category = "perk", default_show = false },
    grinder = { perks = { 4, 6 }, category = "perk", default_show = true },
    sicario_dodge = { perks = { 1, 0 }, texture_bundle_folder = "max", category = "perk", default_show = true },
    smoke_screen_grenade = { perks = { 0, 0 }, texture_bundle_folder = "max", category = "perk", default_show = true },
    biker = { perks = { 0, 0 }, texture_bundle_folder = "wild", category = "perk", default_show = true },
    maniac = { perks = { 0, 0 }, texture_bundle_folder = "coco", category = "perk", default_show = false },
    tag_team = { perks = { 0, 0 }, texture_bundle_folder = "ecp", category = "perk", default_show = true },
    chico_injector = { perks = { 0, 0 }, texture_bundle_folder = "chico", category = "perk", default_show = false },
    pocket_ecm_jammer = { perks = { 0, 0 }, texture_bundle_folder = "joy", category = "perk", default_show = true },
    pocket_ecm_kill_dodge = { perks = { 3, 0 }, texture_bundle_folder = "joy", category = "perk", default_show = false },
    copr_ability = { perks = { 0, 0 }, texture_bundle_folder = "copr", category = "perk", default_show = true },
    copycat_health_invul = { perks = { 3, 0 }, texture_bundle_folder = "mrwi", category = "perk", default_show = true },
    copycat_health_shot = { perks = { 1, 0 }, texture_bundle_folder = "mrwi", category = "perk", default_show = true },
    delayed_damage = { perks = { 3, 0 }, texture_bundle_folder = "myh", category = "perk", default_show = true },
    close_contact = { perks = { 5, 4 }, category = "perk", default_show = true },
    overdog = { perks = { 6, 4 }, category = "perk", default_show = false },
    melee_stack_damage = { perks = { 5, 4 }, category = "perk", default_show = false },
    tooth_and_claw = { perks = { 0, 3 }, category = "perk", default_show = true },
    hostage_situation = { perks = { 0, 1 }, category = "perk", default_show = false },
    yakuza = { perks = { 2, 7 }, category = "perk", default_show = false },

    anarchist_armor_recovery_debuff = { perks = { 0, 1 }, texture_bundle_folder = "opera", category = "debuff", color = "debuff", default_show = true },
    ammo_give_out_debuff = { perks = { 5, 5 }, category = "debuff", color = "debuff", default_show = true },
    armor_break_invulnerable_debuff = { perks = { 6, 1 }, category = "debuff", color = "debuff", default_show = true },
    sociopath_debuff = { perks = { 3, 5 }, category = "debuff", color = "debuff", default_show = true },
    life_drain_debuff = { perks = { 7, 4 }, category = "debuff", color = "debuff", default_show = true },
    medical_supplies_debuff = { perks = { 4, 5 }, category = "debuff", color = "debuff", default_show = true },
    damage_control_debuff = { perks = { 2, 0 }, texture_bundle_folder = "myh", category = "debuff", color = "debuff", default_show = false },

    anarchist_armor_regeneration = { perks = { 0, 0 }, texture_bundle_folder = "opera", category = "player_action", default_show = true },
    standard_armor_regeneration = { perks = { 6, 0 }, category = "player_action", default_show = true },
    weapon_charge = { texture = "guis/textures/weapon_charge", texture_rect = { 1984, 0, 64, 64 }, category = "player_action", default_show = true },
    melee_charge = { skill_id = "hidden_blade", skill_atlas = "skills", skills = { 4, 5 }, category = "player_action", default_show = true },
    reload = { skills = { 0, 9 }, category = "player_action", default_show = true },
    interact = { texture = "guis/textures/pd2/skilltree/drillgui_icon_faster", category = "player_action", default_show = true },

    invulnerable_buff = { hud_tweak = "csb_melee", category = "gage", default_show = true },
    life_steal_debuff = { hud_tweak = "csb_lifesteal", category = "gage", color = "debuff", default_show = true },

    crew_inspire_debuff = { hud_tweak = "ability_1", category = "ai", color = "debuff", default_show = true },
    crew_throwable_regen = { hud_tweak = "skill_7", category = "ai", default_show = true },
    crew_health_regen = { hud_tweak = "skill_5", category = "ai", default_show = true },

    damage_increase = { skill_id = "prison_wife", skills_new = { 2, 8 }, category = "fugitive", color = "damage_increase", default_show = true },
    damage_reduction = { skill_id = "disguise", skills_new = { 5, 2 }, category = "fugitive", color = "damage_reduction", default_show = true },
    melee_damage_increase = { skill_id = "hidden_blade", skills_new = { 4, 3 }, category = "fugitive", color = "melee_damage_increase", default_show = true },
    passive_health_regen = { skills_new = { 1, 11 }, category = "mastermind", color = "passive_health_regen", value_format = "passive_health_regen", default_show = true },
    total_dodge_chance = { skills_new = { 1, 12 }, category = "ghost", color = "total_dodge_chance", default_show = true },
}

KH.UPGRADE_TO_BUFF = {
    unseen_strike = "unseen_strike",
    second_wind = "second_wind",
    damage_speed_multiplier = "second_wind",
    team_damage_speed_multiplier_received = "second_wind",
    overkill_damage_multiplier = "overkill",
    dmg_multiplier_outnumbered = "underdog",
    dmg_dampener_outnumbered = "underdog",
    dmg_dampener_outnumbered_strong = "overdog",
    bullet_storm = "bullet_storm",
    inspire = "inspire",
    inspire_cooldown = "inspire_debuff",
    ammo_efficiency = "ammo_efficiency",
    hostage_taker = "hostage_taker",
    berserker_damage_multiplier = "swan_song",
    swan_song = "swan_song",
    bloodthirst = "bloodthirst_aced",
    sicario_dodge = "sicario_dodge",
    combat_medic = "combat_medic",
    quick_fix = "quick_fix",
    up_you_go = "up_you_go",
    running_from_death = "running_from_death",
    trigger_happy = "trigger_happy",
    desperado = "desperado",
    dire_need = "dire_need",
    sixth_sense = "sixth_sense",
    aggressive_reload_aced = "aggressive_reload_aced",
    lock_n_load = "lock_n_load",
    close_contact = "close_contact",
    overdog = "overdog",
    tooth_and_claw = "tooth_and_claw",
    painkiller = "painkiller",
    passive_revive_damage_reduction = "painkiller",
    die_hard = "die_hard",
    frenzy = "frenzy",
    messiah = "messiah",
    crew_inspire_debuff = "crew_inspire_debuff",
    invulnerable_buff = "invulnerable_buff",

    single_shot_fast_reload = "aggressive_reload_aced",
    dmg_dampener_close_contact = "close_contact",
    first_aid_damage_reduction = "quick_fix",
    increased_movement_speed = "running_from_death",
    reload_weapon_faster = "running_from_death",
    swap_weapon_faster = "running_from_death",
    revive_damage_reduction = "combat_medic",
    revived_damage_resist = "up_you_go",
    bloodthirst_reload_speed = "bloodthirst_aced",
    revived_damage_reduction = "painkiller",
    melee_life_leech = "life_drain_debuff",
    loose_ammo_restore_health = "medical_supplies_debuff",
    loose_ammo_give_team = "ammo_give_out_debuff",
    armor_break_invulnerable = "armor_break_invulnerable_debuff",
    mrwi_health_invulnerable = "copycat_health_invul",
    long_dis_revive = "inspire_revive_debuff",
}

-- Un évènement source peut alimenter son icône propre et un indicateur
-- composite. Cette table reprend les regroupements de VanillaHUD+ sans rendre
-- ce mod dépendant de ses classes de rendu.
KH.BUFF_SOURCE_TARGETS = {
    damage_speed_multiplier = { "second_wind" },
    team_damage_speed_multiplier_received = { "second_wind" },
    dmg_multiplier_outnumbered = { "underdog", "damage_increase" },
    dmg_dampener_outnumbered = { "underdog", "damage_reduction" },
    dmg_dampener_outnumbered_strong = { "overdog", "damage_reduction" },
    dmg_dampener_close_contact = { "close_contact", "damage_reduction" },
    berserker = { "berserker", "damage_increase", "melee_damage_increase" },
    berserker_aced = { "berserker", "damage_increase" },
    bloodthirst_basic = { "bloodthirst_basic", "melee_damage_increase" },
    chico_injector = { "chico_injector", "damage_reduction" },
    close_contact_1 = { "close_contact", "damage_reduction" },
    close_contact_2 = { "close_contact", "damage_reduction" },
    close_contact_3 = { "close_contact", "damage_reduction" },
    combat_medic = { "combat_medic", "damage_reduction" },
    combat_medic_passive = { "combat_medic_passive", "damage_reduction" },
    crew_health_regen = { "crew_health_regen", "passive_health_regen" },
    die_hard = { "die_hard", "damage_reduction" },
    frenzy = { "frenzy", "damage_reduction" },
    hostage_situation = { "hostage_situation", "damage_reduction" },
    hostage_taker = { "hostage_taker", "passive_health_regen" },
    copycat_health_invul = { "copycat_health_invul", "damage_reduction" },
    copycat_health_invul_passive = { "copycat_health_invul", "damage_reduction" },
    maniac = { "maniac", "damage_reduction" },
    melee_stack_damage = { "melee_stack_damage", "melee_damage_increase" },
    movement_dodge = { "total_dodge_chance" },
    muscle_regen = { "muscle_regen", "passive_health_regen" },
    overdog = { "overdog", "damage_reduction" },
    overkill = { "overkill", "damage_increase" },
    overkill_aced = { "overkill", "damage_increase" },
    pain_killer = { "painkiller", "damage_reduction" },
    pain_killer_aced = { "painkiller", "damage_reduction" },
    partner_in_crime_aced = { "partner_in_crime" },
    pocket_ecm_kill_dodge = { "pocket_ecm_kill_dodge", "total_dodge_chance" },
    quick_fix = { "quick_fix", "damage_reduction" },
    running_from_death_basic = { "running_from_death" },
    running_from_death_aced = { "running_from_death" },
    sicario_dodge = { "sicario_dodge", "total_dodge_chance" },
    smoke_screen_grenade = { "smoke_screen_grenade", "total_dodge_chance" },
    swan_song_aced = { "swan_song" },
    trigger_happy = { "trigger_happy", "damage_increase" },
    underdog = { "underdog", "damage_increase" },
    underdog_aced = { "underdog", "damage_reduction" },
    up_you_go = { "up_you_go", "damage_reduction" },
    yakuza_recovery = { "yakuza" },
    yakuza_speed = { "yakuza" },

    armorer_9 = { "armorer" },
    crew_chief_1 = { "crew_chief", "damage_reduction" },
    crew_chief_3 = { "crew_chief" },
    crew_chief_5 = { "crew_chief" },
    crew_chief_9 = { "crew_chief" },

    grinder_debuff = { "grinder" },
    chico_injector_debuff = { "chico_injector" },
    copr_ability_debuff = { "copr_ability" },
    copycat_health_invul_debuff = { "copycat_health_invul" },
    copycat_health_shot_debuff = { "copycat_health_shot" },
    delayed_damage_debuff = { "delayed_damage" },
    maniac_debuff = { "maniac" },
    pocket_ecm_jammer_debuff = { "pocket_ecm_jammer" },
    sicario_dodge_debuff = { "sicario_dodge" },
    smoke_screen_grenade_debuff = { "smoke_screen_grenade" },
    tag_team_debuff = { "tag_team" },
    unseen_strike_debuff = { "unseen_strike" },
    uppers_debuff = { "uppers" },
    interact_debuff = { "interact" },
}

function KH.GetBuffTargets(source_id)
    -- Si VanillaHUD+ expose sa table de regroupement, la consulter à chaque
    -- évènement. Cela garde le pont compatible avec de nouveaux alias ajoutés
    -- par VanillaHUD+ sans casser le fonctionnement autonome.
    local vhud_buffs = HUDListManager and HUDListManager.BUFFS
    local vhud_targets = vhud_buffs and vhud_buffs[source_id]
    if type(vhud_targets) == "table" then
        local supported = {}
        for _, buff_id in ipairs(vhud_targets) do
            if KH.BUFF_MAP and KH.BUFF_MAP[buff_id] then
                table.insert(supported, buff_id)
            end
        end
        if #supported > 0 then
            return supported
        end
    end

    local composite_parent = vhud_buffs
        and vhud_buffs.composite_debuffs
        and vhud_buffs.composite_debuffs[source_id]
    if composite_parent and KH.BUFF_MAP and KH.BUFF_MAP[composite_parent] then
        return { composite_parent }
    end

    local targets = KH.BUFF_SOURCE_TARGETS and KH.BUFF_SOURCE_TARGETS[source_id]
    if targets then
        return targets
    end

    local resolved = KH.UPGRADE_TO_BUFF and KH.UPGRADE_TO_BUFF[source_id]
    if resolved and KH.BUFF_MAP and KH.BUFF_MAP[resolved] then
        return { resolved }
    end

    if KH.BUFF_MAP and KH.BUFF_MAP[source_id] then
        return { source_id }
    end

    return {}
end

function KH.BuildDefaultBuffToggles()
    local toggles = {}

    for buff_id, buff_def in pairs(KH.BUFF_MAP or {}) do
        toggles[buff_id] = buff_def.default_show ~= false
    end

    return toggles
end

function KH.GetSortedBuffIdsForCategory(category_id)
    local buff_ids = {}

    for buff_id, buff_def in pairs(KH.BUFF_MAP or {}) do
        if buff_def.category == category_id then
            table.insert(buff_ids, buff_id)
        end
    end

    table.sort(buff_ids)

    return buff_ids
end
