-- ky_localization.lua — Chargement des traductions + fallbacks
-- KyoHUD v1.1.1

local MOD_NAME = "KyoHUD"

-- IMPORTANT : capturer ModPath immédiatement à l'exécution du fichier,
-- car le global ModPath sera écrasé par BLT quand d'autres mods se chargent.
local MY_MOD_PATH = ModPath

local catalog_ok, catalog_err = pcall(dofile, MY_MOD_PATH .. "ky_buff_catalog.lua")
if not catalog_ok then
    pcall(function()
        log("[" .. MOD_NAME .. "][Loc] Erreur chargement catalogue buffs: " .. tostring(catalog_err))
    end)
end

local function logi(msg)
    pcall(function() log("[" .. MOD_NAME .. "][Loc] " .. tostring(msg)) end)
end

logi("ModPath capturé: " .. tostring(MY_MOD_PATH))

-- Fallbacks intégrés pour garantir aucun "ERROR:" dans les menus
local function add_fallbacks(loc)
    loc:add_localized_strings({
        -- Menu principal
        ky_menu_title = "KyoHUD - Killfeed & Combat Score",
        ky_menu_desc  = "Customizable buffs, killfeed, kill streaks and combat score",

        -- Options de base
        ky_opt_enable_killfeed      = "Enable KillFeed",
        ky_opt_enable_killfeed_desc = "Show kill streaks and a horizontal tactical killfeed below the crosshair",
        ky_opt_killfeed_size        = "Killfeed Size",
        ky_opt_killfeed_size_desc   = "Number of kills shown in the killfeed (1-3)",
        ky_opt_enable_buffs         = "Enable Buffs",
        ky_opt_enable_buffs_desc    = "Show the equipped perk deck and active buffs in a horizontal row",
        ky_opt_buffs_menu           = "Buffs Menu",
        ky_opt_buffs_menu_desc      = "Choose which buff categories and individual buffs are displayed",
        ky_opt_radius               = "Killfeed Vertical Offset",
        ky_opt_radius_desc          = "Vertical distance of the killfeed from the crosshair (100-500)",
        ky_opt_buff_position_x      = "Buff Position X (%)",
        ky_opt_buff_position_x_desc = "Horizontal center of the buff row (0-100%). Default: 50%",
        ky_opt_buff_position_y      = "Buff Position Y (%)",
        ky_opt_buff_position_y_desc = "Vertical center of the buff row (0-100%). The default adapts to the active HUD.",
        ky_opt_duration             = "Display Duration",
        ky_opt_duration_desc        = "How long buffs/kills stay visible (seconds)",
        ky_opt_opacity              = "Opacity",
        ky_opt_opacity_desc         = "HUD element opacity (0.1 to 1.0)",
        ky_opt_icon_size            = "Icon Size",
        ky_opt_icon_size_desc       = "Size of buff/kill icons in pixels",
        ky_opt_reset                = "Reset to Defaults",
        ky_opt_reset_desc           = "Reset all settings to their default values",
        ky_opt_debug_sim            = "Debug: Simulate",
        ky_opt_debug_sim_desc       = "Simulate active buffs, special-enemy kill cards and Killdozer banners",
        ky_opt_debug_clear          = "Debug: Clear",
        ky_opt_debug_clear_desc     = "Remove active buffs and kills; the equipped perk deck remains visible",

        -- Bandeau des séries de kills
        ky_hud_combo_2     = "CLEAN PAIR",
        ky_hud_combo_3     = "EXCELLENT",
        ky_hud_combo_4     = "OVERKILL",
        ky_hud_combo_5     = "FRENZY",
        ky_hud_combo_6     = "CARNAGE",
        ky_hud_combo_7     = "MASSACRE",
        ky_hud_combo_8     = "EXTERMINATION",
        ky_hud_combo_9     = "APOCALYPSE",
        ky_hud_combo_10    = "PERFECT HEIST",
        ky_hud_combo_chain = "KILL CHAIN",
        ky_hud_killdozer   = "KILLDOZER",
        ky_hud_dozer_down  = "DOZER DOWN",
        ky_hud_bulldozed   = "BULLDOZED",
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

        -- Sous-menu filtres
        ky_opt_buff_filter          = "Buff Filters",
        ky_opt_buff_filter_desc     = "Toggle buff categories and individual buffs",

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

    -- Détecter la langue BLT
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
    local wants_french = blt_lang:match("^fr") or blt_lang:match("french") or game_french

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
