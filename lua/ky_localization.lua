-- ky_localization.lua — Chargement des traductions + fallbacks
local MOD_NAME = "KyoHUD"

-- IMPORTANT : capturer ModPath immédiatement à l'exécution du fichier,
-- car le global ModPath sera écrasé par BLT quand d'autres mods se chargent.
local MY_MOD_PATH = ModPath

local catalog_ok, catalog_err = pcall(dofile, MY_MOD_PATH .. "lua/ky_buff_catalog.lua")
if not catalog_ok then
    pcall(function()
        log("[" .. MOD_NAME .. "][Loc] Erreur chargement catalogue buffs: " .. tostring(catalog_err))
    end)
end

local function logi(msg)
    pcall(function() log("[" .. MOD_NAME .. "][Loc] " .. tostring(msg)) end)
end

-- Fallbacks intégrés pour garantir aucun "ERROR:" dans les menus
local function add_fallbacks(loc)
    loc:add_localized_strings({
        -- Menu principal
        ky_menu_title = "KyoHUD - Killfeed & Combat Score",
        ky_menu_desc  = "Customizable buffs, killfeed, kill streaks and combat score",

        -- Options de base
        ky_opt_language           = "Language",
        ky_opt_language_desc      = "Choose the mod language. Reload the level to apply the change.",
        ky_opt_language_auto      = "Detection AUTO",
        ky_opt_language_english   = "English",
        ky_opt_language_french    = "Français",
        ky_opt_enable_killfeed      = "Enable KillFeed",
        ky_opt_enable_killfeed_desc = "Show eliminated enemies beneath the crosshair; scores and counters continue while the killfeed is hidden",
        ky_opt_killfeed_size        = "Killfeed Size",
        ky_opt_killfeed_size_desc   = "Number of kills shown in the killfeed (1-5). Default: 3",
        ky_opt_enable_buffs         = "Enable Buffs",
        ky_opt_enable_buffs_desc    = "Show the equipped perk deck and active buffs in a horizontal row",
        ky_opt_buffs_menu           = "Buffs Menu",
        ky_opt_buffs_menu_desc      = "Choose which buff categories and individual buffs are displayed",
        ky_opt_radius               = "Killfeed Vertical Offset",
        ky_opt_radius_desc          = "Vertical distance of the killfeed from the crosshair (128-291). Default: 250",
        ky_opt_buff_position_x      = "Buff Position X (%)",
        ky_opt_buff_position_x_desc = "Horizontal center of the buff row (0-100%). Default: 50%",
        ky_opt_buff_position_y      = "Buff Position Y (%)",
        ky_opt_buff_position_y_desc = "Vertical center of the buff row (0-100%). The default adapts to the active HUD.",
        ky_opt_show_total_score      = "Show Total Score",
        ky_opt_show_total_score_desc = "Show the heist total score widget. Disabling it also disables the Best Streak option.",
        ky_opt_show_best_streak      = "Show Best Streak",
        ky_opt_show_best_streak_desc = "Show the best continuous scoring streak below the total score.",
        ky_opt_score_position_x      = "Score Position X (%)",
        ky_opt_score_position_x_desc = "Horizontal center of the total score widget (0-100%). Default: 100%",
        ky_opt_score_position_y      = "Score Position Y (%)",
        ky_opt_score_position_y_desc = "Vertical center of the total score widget (0-100%). Default: 75%",
        ky_opt_opacity              = "Opacity",
        ky_opt_opacity_desc         = "HUD element opacity (10-100%). Default: 90%",
        ky_opt_icon_size            = "Icon Size",
        ky_opt_icon_size_desc       = "Size of buff/kill icons in pixels (32-40). Default: 32",
        ky_opt_reset                = "Reset to Defaults",
        ky_opt_reset_desc           = "Reset all settings to their default values",
        ky_opt_debug_sim            = "Preview Buffs & Kills",
        ky_opt_debug_sim_desc       = "Main menu only: preview buffs, special-enemy kill cards and priority-target banners; unavailable during a heist",
        ky_opt_debug_clear          = "Clear Preview",
        ky_opt_debug_clear_desc     = "Remove preview buffs and kills; the equipped perk deck remains visible",

        ky_hud_score_total       = "TOTAL SCORE",
        ky_hud_score_best_streak = "BEST STREAK",
        ky_hud_score_best_short  = "BEST",

        -- Libellés dessinés au-dessus de l'icône d'un buff
        ky_hud_buff_label_inspire_cooldown = "Boost+",
        ky_hud_buff_label_inspire_revive   = "Revive",
        ky_hud_buff_label_damage_increase  = "Dmg+",
        ky_hud_buff_label_damage_reduction = "Dmg-",
        ky_hud_buff_label_melee_damage     = "M.Dmg+",
        ky_hud_buff_label_health_regen     = "HP+",
        ky_hud_buff_label_dodge_chance     = "Dodge",

        -- Bandeau des séries de kills
        ky_hud_combo_2     = "CLEAN PAIR",
        ky_hud_combo_2_2   = "DOUBLE TAP",
        ky_hud_combo_2_3   = "TWO FOR ONE",
        ky_hud_combo_3     = "EXCELLENT",
        ky_hud_combo_3_2   = "TRIPLE THREAT",
        ky_hud_combo_3_3   = "THREE OF A KIND",
        ky_hud_combo_4     = "OVERKILL",
        ky_hud_combo_4_2   = "FOUR DOWN",
        ky_hud_combo_4_3   = "QUAD STRIKE",
        ky_hud_combo_5     = "FRENZY",
        ky_hud_combo_5_2   = "HIGH FIVE",
        ky_hud_combo_5_3   = "FIVEFOLD FURY",
        ky_hud_combo_6     = "CARNAGE",
        ky_hud_combo_6_2   = "SIX FEET UNDER",
        ky_hud_combo_6_3   = "SIXFOLD SLAUGHTER",
        ky_hud_combo_7     = "MASSACRE",
        ky_hud_combo_7_2   = "LUCKY SEVEN",
        ky_hud_combo_7_3   = "SEVENTH HEAVEN",
        ky_hud_combo_8     = "EXTERMINATION",
        ky_hud_combo_8_2   = "EIGHT COUNT",
        ky_hud_combo_8_3   = "OCTUPLE ONSLAUGHT",
        ky_hud_combo_9     = "APOCALYPSE",
        ky_hud_combo_9_2   = "CLOUD NINE",
        ky_hud_combo_9_3   = "NINE LIVES DENIED",
        ky_hud_combo_10    = "PERFECT HEIST",
        ky_hud_combo_10_2  = "TEN OUT OF TEN",
        ky_hud_combo_10_3  = "DECADE OF DOOM",
        ky_hud_combo_chain = "KILL CHAIN",
        ky_hud_killdozer   = "KILLDOZER",
        ky_hud_dozer_down  = "DOZER DOWN",
        ky_hud_bulldozed   = "BULLDOZED",
        ky_hud_boss_eliminated = "BOSS ELIMINATED",
        ky_hud_dozer_tank_buster          = "TANK BUSTER",
        ky_hud_dozer_armor_breaker        = "ARMOR BREAKER",
        ky_hud_dozer_heavy_down           = "HEAVY DOWN",
        ky_hud_dozer_ive_got_the_big_guy = "I'VE GOT THE BIG GUY",
        ky_hud_medic_code_blue       = "CODE BLUE",
        ky_hud_medic_bad_medicine    = "BAD MEDICINE",
        ky_hud_medic_doctor_down     = "DOCTOR DOWN",
        ky_hud_cloaker_shadow_hunter = "SHADOW HUNTER",
        ky_hud_cloaker_counter_kick  = "COUNTER-KICK",
        ky_hud_cloaker_ambush_broken = "AMBUSH BROKEN",
        ky_hud_taser_power_outage    = "POWER OUTAGE",
        ky_hud_taser_circuit_breaker = "CIRCUIT BREAKER",
        ky_hud_taser_blackout        = "BLACKOUT",
        ky_hud_shield_breaker        = "SHIELD BREAKER",
        ky_hud_shield_phalanx_fall   = "PHALANX FALL",
        ky_hud_shield_barrier_down   = "BARRIER DOWN",
        ky_hud_shield_defense_denied = "DEFENSE DENIED",
        ky_hud_sniper_counter_sniper = "COUNTER-SNIPER",
        ky_hud_sniper_scope_breaker  = "SCOPE BREAKER",
        ky_hud_sniper_longshot_denied = "LONGSHOT DENIED",

        -- Paliers des séries par famille d'arme. Comme les autres libellés de
        -- bandeau, ces médailles restent en anglais dans les deux langues.
        ky_hud_streak_shotgun_5      = "SHOTGUN SPREE",
        ky_hud_streak_shotgun_10     = "OPEN SEASON",
        ky_hud_streak_shotgun_15     = "BUCK WILD",
        ky_hud_streak_sniper_5       = "SNIPER SPREE",
        ky_hud_streak_sniper_10      = "SHARPSHOOTER",
        ky_hud_streak_sniper_15      = "BE THE BULLET",
        ky_hud_streak_akimbo_5       = "DOUBLE TROUBLE",
        ky_hud_streak_akimbo_10      = "GUNS BLAZING",
        ky_hud_streak_akimbo_15      = "TWICE THE FIREPOWER",
        ky_hud_streak_incendiary_3   = "BURN NOTICE",
        ky_hud_streak_incendiary_6   = "INCINERATION",
        ky_hud_streak_incendiary_10  = "HELLFIRE",
        ky_hud_streak_poison_3       = "TOXIC",
        ky_hud_streak_poison_6       = "VENOMOUS",
        ky_hud_streak_poison_10      = "BIOHAZARD",
        ky_hud_streak_melee_2        = "ONE-TWO",
        ky_hud_streak_melee_3        = "BONE CRACKER",
        ky_hud_streak_melee_4        = "PUMMEL",
        ky_hud_streak_melee_5        = "WRECKING CREW",
        ky_hud_streak_explosive_3    = "BOOM",
        ky_hud_streak_explosive_5    = "DEMOLITION",
        ky_hud_streak_explosive_8    = "BLAST ZONE",

        -- Médaille des kills cumulés du braquage. Une seule clé : l'icône du
        -- buff de dégâts tient lieu de nom et le palier atteint la précède.
        ky_hud_kill_medal_kills      = "KILLS",

        -- Médailles d'évènement, décernées sur les conditions du kill lui-même.
        ky_hud_event_medal_first_strike = "First Strike",
        ky_hud_event_medal_grave     = "Grave",
        ky_hud_event_medal_low_hp    = "Last Breath",
        ky_hud_event_medal_reload    = "Reload This",
        ky_hud_event_medal_through_shield = "Through the Shield",
        ky_hud_event_medal_one_shot_two_kills = "One Shot Two Kills",
        ky_hud_event_medal_revenge   = "Revenge",
        ky_hud_event_medal_bulltrue  = "Bulltrue",
        ky_hud_event_medal_showstopper = "Showstopper",
        ky_hud_event_medal_rope      = "Pull!",
        ky_hud_event_medal_rope_3    = "Free Fall",
        ky_hud_event_medal_rope_5    = "Air Sweep",

        -- Catégories
        ky_opt_cat_mastermind           = "Mastermind",
        ky_opt_cat_mastermind_desc      = "Show/hide all Mastermind buffs",
        ky_opt_cat_mastermind_buffs     = "Mastermind Buffs",
        ky_opt_cat_mastermind_buffs_desc = "Toggle individual Mastermind buffs",

        ky_opt_cat_enforcer             = "Enforcer",
        ky_opt_cat_enforcer_desc        = "Show/hide all Enforcer buffs",
        ky_opt_cat_enforcer_buffs       = "Enforcer Buffs",
        ky_opt_cat_enforcer_buffs_desc  = "Toggle individual Enforcer buffs",

        ky_opt_cat_technician           = "Technician",
        ky_opt_cat_technician_desc      = "Show/hide all Technician buffs",
        ky_opt_cat_technician_buffs     = "Technician Buffs",
        ky_opt_cat_technician_buffs_desc = "Toggle individual Technician buffs",

        ky_opt_cat_ghost                = "Ghost",
        ky_opt_cat_ghost_desc           = "Show/hide all Ghost buffs",
        ky_opt_cat_ghost_buffs          = "Ghost Buffs",
        ky_opt_cat_ghost_buffs_desc     = "Toggle individual Ghost buffs",

        ky_opt_cat_fugitive             = "Fugitive",
        ky_opt_cat_fugitive_desc        = "Show/hide all Fugitive buffs",
        ky_opt_cat_fugitive_buffs       = "Fugitive Buffs",
        ky_opt_cat_fugitive_buffs_desc  = "Toggle individual Fugitive buffs",

        ky_opt_cat_perk                 = "Perk Decks",
        ky_opt_cat_perk_desc            = "Show/hide all Perk Deck buffs",
        ky_opt_cat_perk_buffs           = "Perk Deck Buffs",
        ky_opt_cat_perk_buffs_desc      = "Toggle individual Perk Deck buffs",

        ky_opt_cat_debuff               = "Debuffs",
        ky_opt_cat_debuff_desc          = "Show/hide all debuffs",
        ky_opt_cat_debuff_buffs         = "Debuffs List",
        ky_opt_cat_debuff_buffs_desc    = "Toggle individual debuffs",

        ky_opt_cat_team                 = "Team Buffs",
        ky_opt_cat_team_desc            = "Show/hide all team buffs",
        ky_opt_cat_team_buffs           = "Team Buffs List",
        ky_opt_cat_team_buffs_desc      = "Toggle individual team buffs",

        ky_opt_cat_player_action            = "Player Actions",
        ky_opt_cat_player_action_desc       = "Show/hide player action buffs",
        ky_opt_cat_player_action_buffs      = "Player Action Buffs",
        ky_opt_cat_player_action_buffs_desc = "Toggle individual player action buffs",

        ky_opt_cat_gage                 = "Gage Boosts",
        ky_opt_cat_gage_desc            = "Show/hide Gage boosts",
        ky_opt_cat_gage_buffs           = "Gage Boosts List",
        ky_opt_cat_gage_buffs_desc      = "Toggle individual Gage boosts",

        ky_opt_cat_ai                   = "AI Skills",
        ky_opt_cat_ai_desc              = "Show/hide AI crew skill buffs",
        ky_opt_cat_ai_buffs             = "AI Skill Buffs",
        ky_opt_cat_ai_buffs_desc        = "Toggle individual AI skill buffs",
    })

    -- Fallbacks dynamiques pour les buffs individuels
    if kyohud and kyohud.BUFF_MAP then
        local buff_fallbacks = {}
        for buff_id, _ in pairs(kyohud.BUFF_MAP) do
            local nice_name = buff_id:gsub("_", " "):gsub("(%a)([%w_']*)", function(a, b)
                return string.upper(a) .. b
            end)
            buff_fallbacks["ky_opt_buff_" .. buff_id] = nice_name
            buff_fallbacks["ky_opt_buff_" .. buff_id .. "_desc"] = "Toggle " .. nice_name
        end
        loc:add_localized_strings(buff_fallbacks)
    end
end

Hooks:Add("LocalizationManagerPostInit", "KH_Localization", function(loc)
    -- Utiliser MY_MOD_PATH (capturé au chargement) et PAS le global ModPath
    local base = MY_MOD_PATH .. "loc/"
    local loaded = false

    logi("Recherche des fichiers dans: " .. tostring(base))

    -- Fallbacks EN PREMIER : add_localized_strings ÉCRASE les clés existantes,
    -- donc les fichiers chargés ensuite (english puis french) ont priorité.
    add_fallbacks(loc)

    -- Lire ce réglage ici car le hook de localisation précède ky_options.lua.
    local language = 1
    local settings_paths = {
        SavePath .. "kyohud_settings.json",
        SavePath .. "kyosh1ro_hud_settings.json",
    }
    for _, settings_path in ipairs(settings_paths) do
        local settings_file = io.open(settings_path, "r")
        if settings_file then
            local raw = settings_file:read("*all")
            settings_file:close()
            local ok, data = pcall(json.decode, raw)
            if ok and type(data) == "table" then
                local saved_language = math.floor(tonumber(data.language) or 1)
                if saved_language >= 1 and saved_language <= 3 then
                    language = saved_language
                end
            end
            break
        end
    end

    -- Détecter la langue BLT pour le mode automatique.
    local blt_lang = ""
    if BLT and BLT.Localization and BLT.Localization._current then
        blt_lang = tostring(BLT.Localization._current):lower()
    end

    -- Détecter la langue du jeu
    local game_french = false
    pcall(function()
        game_french = (SystemInfo:language():key() == Idstring("french"):key())
    end)

    -- Charger le fichier de langue approprié
    local try_files = {}
    local auto_french = blt_lang:match("^fr") or blt_lang:match("french") or game_french
    local wants_french = language == 3 or (language == 1 and auto_french)

    table.insert(try_files, base .. "english.json")
    if wants_french then
        table.insert(try_files, base .. "french.json")
    end

    for _, path in ipairs(try_files) do
        local readable = false
        if io.file_is_readable then
            readable = io.file_is_readable(path)
        elseif file and file.FileExists then
            readable = file.FileExists(path)
        else
            -- Tenter d'ouvrir pour vérifier
            local test = io.open(path, "r")
            if test then
                test:close()
                readable = true
            end
        end

        if readable then
            loc:load_localization_file(path)
            logi("Chargé: " .. path)
            loaded = true
        else
            logi("Non trouvé: " .. path)
        end
    end

    if not loaded then
        logi("Aucun fichier de localisation trouvé, utilisation des fallbacks internes.")
    end
end)
