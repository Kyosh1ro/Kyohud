if not Kyosh1roHUD then
    Kyosh1roHUD = {}
end

local KH = Kyosh1roHUD

if KH.BUFF_CATEGORIES and KH.BUFF_MAP and KH.UPGRADE_TO_BUFF
    and KH.BuildDefaultBuffToggles and KH.GetSortedBuffIdsForCategory then
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

KH.BUFF_MAP = {
    single_shot_fast_reload = { skills_new = { 1, 0 }, category = "mastermind", default_show = true },
    aggressive_reload_aced = { skills_new = { 1, 1 }, category = "mastermind", default_show = true },
    inspire = { skills_new = { 0, 9 }, category = "mastermind", default_show = true },
    inspire_cooldown = { skills_new = { 0, 9 }, category = "mastermind", default_show = true },
    inspire_debuff = { skills_new = { 0, 9 }, category = "debuff", default_show = true },
    inspire_revive_debuff = { skills_new = { 0, 9 }, category = "debuff", default_show = true },
    combat_medic = { skills_new = { 0, 0 }, category = "mastermind", default_show = true },
    combat_medic_passive = { skills_new = { 0, 0 }, category = "mastermind", default_show = false },
    quick_fix = { skills_new = { 1, 3 }, category = "mastermind", default_show = false },
    uppers = { skills_new = { 1, 2 }, category = "mastermind", default_show = true },
    painkiller = { skills_new = { 0, 4 }, category = "mastermind", default_show = false },
    hostage_taker = { skills_new = { 1, 5 }, category = "mastermind", default_show = false },
    partner_in_crime = { skills_new = { 0, 6 }, category = "mastermind", default_show = false },
    forced_friendship = { skills_new = { 0, 7 }, category = "team", default_show = true },
    ammo_efficiency = { skills_new = { 0, 8 }, category = "mastermind", default_show = true },

    overkill = { skills_new = { 2, 0 }, category = "enforcer", default_show = false },
    bullet_storm = { skills_new = { 2, 3 }, category = "enforcer", default_show = true },
    die_hard = { skills_new = { 2, 4 }, category = "enforcer", default_show = false },
    iron_man = { skills_new = { 2, 6 }, category = "enforcer", default_show = true },
    underdog = { skills_new = { 2, 1 }, category = "enforcer", default_show = false },
    bullseye_debuff = { skills_new = { 2, 8 }, category = "debuff", default_show = true },
    bulletproof = { perks = { 6, 2 }, category = "team", default_show = true },

    lock_n_load = { skills_new = { 3, 0 }, category = "technician", default_show = true },

    second_wind = { skills_new = { 4, 1 }, category = "ghost", default_show = true },
    unseen_strike = { skills_new = { 4, 5 }, category = "ghost", default_show = true },
    sixth_sense = { skills_new = { 4, 7 }, category = "ghost", default_show = true },
    dire_need = { skills_new = { 4, 8 }, category = "ghost", default_show = true },

    berserker = { skills_new = { 5, 0 }, category = "fugitive", default_show = true },
    swan_song = { skills_new = { 5, 3 }, category = "fugitive", default_show = false },
    trigger_happy = { skills_new = { 5, 4 }, category = "fugitive", default_show = false },
    desperado = { skills_new = { 5, 5 }, category = "fugitive", default_show = true },
    bloodthirst_basic = { skills_new = { 5, 6 }, category = "fugitive", default_show = false },
    bloodthirst_aced = { skills_new = { 5, 6 }, category = "fugitive", default_show = true },
    up_you_go = { skills_new = { 5, 7 }, category = "fugitive", default_show = false },
    running_from_death = { skills_new = { 5, 8 }, category = "fugitive", default_show = true },
    messiah = { skills_new = { 5, 9 }, category = "fugitive", default_show = true },
    frenzy = { skills_new = { 5, 10 }, category = "fugitive", default_show = false },

    armor_break_invulnerable = { perks = { 6, 1 }, category = "perk", default_show = true },
    armorer = { perks = { 6, 0 }, category = "team", default_show = true },
    crew_chief = { perks = { 2, 0 }, category = "team", default_show = true },
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

    anarchist_armor_recovery_debuff = { perks = { 0, 1 }, texture_bundle_folder = "opera", category = "debuff", default_show = true },
    ammo_give_out_debuff = { perks = { 5, 5 }, category = "debuff", default_show = true },
    armor_break_invulnerable_debuff = { perks = { 6, 1 }, category = "debuff", default_show = true },
    sociopath_debuff = { perks = { 3, 5 }, category = "debuff", default_show = true },
    life_drain_debuff = { perks = { 7, 4 }, category = "debuff", default_show = true },
    medical_supplies_debuff = { perks = { 4, 5 }, category = "debuff", default_show = true },
    damage_control_debuff = { perks = { 2, 0 }, texture_bundle_folder = "myh", category = "debuff", default_show = false },

    anarchist_armor_regeneration = { perks = { 0, 0 }, texture_bundle_folder = "opera", category = "player_action", default_show = true },
    standard_armor_regeneration = { perks = { 6, 0 }, category = "player_action", default_show = true },
    weapon_charge = { texture = "guis/textures/weapon_charge", texture_rect = { 1984, 0, 64, 64 }, category = "player_action", default_show = true },
    melee_charge = { skills = { 4, 5 }, category = "player_action", default_show = true },
    reload = { skills = { 0, 9 }, category = "player_action", default_show = true },
    interact = { texture = "guis/textures/pd2/skilltree/drillgui_icon_faster", category = "player_action", default_show = true },

    invulnerable_buff = { hud_tweak = "csb_melee", category = "gage", default_show = true },
    life_steal_debuff = { hud_tweak = "csb_lifesteal", category = "gage", default_show = true },

    crew_inspire_debuff = { hud_tweak = "ability_1", category = "ai", default_show = true },
    crew_throwable_regen = { hud_tweak = "skill_7", category = "ai", default_show = true },
    crew_health_regen = { hud_tweak = "skill_5", category = "ai", default_show = true },

    damage_increase = { skills_new = { 2, 8 }, category = "fugitive", default_show = true },
    damage_reduction = { skills_new = { 5, 2 }, category = "fugitive", default_show = true },
    melee_damage_increase = { skills_new = { 4, 3 }, category = "fugitive", default_show = true },
    passive_health_regen = { skills_new = { 1, 11 }, category = "mastermind", default_show = true },
    total_dodge_chance = { skills_new = { 1, 12 }, category = "ghost", default_show = true },
}

KH.UPGRADE_TO_BUFF = {
    unseen_strike = "unseen_strike",
    second_wind = "second_wind",
    overkill_damage_multiplier = "overkill",
    dmg_multiplier_outnumbered = "underdog",
    bullet_storm = "bullet_storm",
    inspire = "inspire",
    inspire_cooldown = "inspire_debuff",
    ammo_efficiency = "ammo_efficiency",
    hostage_taker = "hostage_taker",
    berserker_damage_multiplier = "berserker",
    swan_song = "swan_song",
    bloodthirst = "bloodthirst_aced",
    armor_break_invulnerable = "armor_break_invulnerable",
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
    iron_man = "iron_man",
    die_hard = "die_hard",
    frenzy = "frenzy",
    messiah = "messiah",
    crew_inspire_debuff = "crew_inspire_debuff",
    invulnerable_buff = "invulnerable_buff",

    single_shot_fast_reload = "single_shot_fast_reload",
    dmg_dampener_close_contact = "close_contact",
}

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
