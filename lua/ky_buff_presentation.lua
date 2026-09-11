-- ky_buff_presentation.lua — KyoHUD-owned buff presentation overrides
--
-- VanillaHUD+ remains the source of runtime state and general buff metadata.
-- This module contains only KyoHUD-specific colors, labels, aggregate formats,
-- fixed row placement, and equipped-deck presentation behavior.

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud

if kyohud.KYO_BUFF_CONFIG then return end

kyohud.KYO_BUFF_CONFIG = {
    colors = {
        debuff = "FF5F78",
        team = "52D6FF",
        damage_increase = "FF8A3D",
        damage_reduction = "6C8CFF",
        melee_damage_increase = "D66BFF",
        passive_health_regen = "4ADE9B",
        total_dodge_chance = "F5D547",
    },
    buffs = {
        inspire_debuff = {
            label = {
                id = "ky_hud_buff_label_inspire_cooldown",
                fallback = "Boost+",
                placement = "top",
            },
        },
        inspire_revive_debuff = {
            label = {
                id = "ky_hud_buff_label_inspire_revive",
                fallback = "Revive",
                placement = "top",
            },
        },
        crew_inspire_debuff = {
            label = { fallback = "[AI]", placement = "top" },
        },
        crew_throwable_regen = {
            label = { fallback = "[AI]", placement = "top" },
        },
        crew_health_regen = {
            label = { fallback = "[AI]", placement = "top" },
        },
        damage_increase = {
            fixed_slot = 6,
            color = "damage_increase",
            value_format = "damage_increase",
            label = {
                id = "ky_hud_buff_label_damage_increase",
                fallback = "Dmg+",
                placement = "timer",
            },
        },
        damage_reduction = {
            fixed_slot = 7,
            color = "damage_reduction",
            value_format = "damage_reduction",
            label = {
                id = "ky_hud_buff_label_damage_reduction",
                fallback = "Dmg-",
                placement = "timer",
            },
        },
        melee_damage_increase = {
            fixed_slot = 8,
            color = "melee_damage_increase",
            value_format = "melee_damage_increase",
            label = {
                id = "ky_hud_buff_label_melee_damage",
                fallback = "M.Dmg+",
                placement = "timer",
            },
        },
        passive_health_regen = {
            fixed_slot = 3,
            color = "passive_health_regen",
            value_format = "passive_health_regen",
            label = {
                id = "ky_hud_buff_label_health_regen",
                fallback = "HP+",
                placement = "timer",
            },
        },
        total_dodge_chance = {
            color = "total_dodge_chance",
            value_format = "total_dodge_chance",
            label = {
                id = "ky_hud_buff_label_dodge_chance",
                fallback = "Dodge",
                placement = "timer",
            },
        },
        biker = {
            stack_format = "biker_charges",
        },
        partner_in_crime = {
            persistent_counter = "local_minions",
            skill_id = "control_freak",
            counter_max_upgrade = {
                category = "player",
                upgrade = "convert_enemies_max_minions",
                minimum = 1,
            },
        },
        equipped_perk_deck = {
            fixed_slot = 1,
            equipped_deck = true,
            perk_deck_buffs = {
                [1] = { "hostage_situation" },
                [2] = { "muscle_regen" },
                [3] = { "armor_break_invulnerable" },
                [8] = { "close_contact", "tooth_and_claw" },
                [9] = { "overdog", "melee_stack_damage" },
                [11] = { "grinder" },
                [12] = { "yakuza" },
                [14] = { "maniac" },
                [15] = { "armor_break_invulnerable" },
                [16] = { "biker" },
                [17] = { "chico_injector" },
                [18] = { "smoke_screen_grenade", "sicario_dodge" },
                [19] = { "delayed_damage" },
                [20] = { "tag_team" },
                [22] = { "copr_ability" },
                [23] = {
                    "copycat_health_invul",
                    "copycat_health_shot",
                    "hostage_situation",
                    "muscle_regen",
                    "armor_break_invulnerable",
                    "close_contact",
                    "tooth_and_claw",
                    "overdog",
                    "melee_stack_damage",
                    "grinder",
                    "yakuza",
                    "maniac",
                    "biker",
                    "chico_injector",
                    "smoke_screen_grenade",
                    "sicario_dodge",
                    "delayed_damage",
                    "tag_team",
                    "pocket_ecm_jammer",
                    "pocket_ecm_kill_dodge",
                    "copr_ability",
                },
            },
        },
        pocket_ecm_jammer_debuff = {
            fixed_slot = 2,
            separate_source = true,
        },
        standard_armor_regeneration = {
            fixed_slot = 4,
        },
        armor_break_invulnerable_debuff = {
            fixed_slot = 5,
        },
    },
}
