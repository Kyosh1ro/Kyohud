-- ky_localization.lua — Chargement des traductions + fallbacks
-- Kyosh1ro HUD v1.1.1

local MOD_NAME = "Kyosh1ro HUD"

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
        ky_menu_title = "Kyosh1ro HUD",
        ky_menu_desc  = "Circular buff display & killfeed around the crosshair",

        -- Options de base
        ky_opt_enable_killfeed      = "Enable KillFeed",
        ky_opt_enable_killfeed_desc = "Show eliminated enemies in an arc below the crosshair",
        ky_opt_enable_buffs         = "Enable Buffs",
        ky_opt_enable_buffs_desc    = "Show active buffs in a circle around the crosshair",
        ky_opt_radius               = "Circle Radius",
        ky_opt_radius_desc          = "Distance from crosshair center (100-500 px)",
        ky_opt_angle_start          = "Start Angle",
        ky_opt_angle_start_desc     = "Starting angle of the arc (degrees, 0-360)",
        ky_opt_angle_end            = "End Angle",
        ky_opt_angle_end_desc       = "Ending angle of the arc (degrees, 0-360)",
        ky_opt_duration             = "Display Duration",
        ky_opt_duration_desc        = "How long buffs/kills stay visible (seconds)",
        ky_opt_opacity              = "Opacity",
        ky_opt_opacity_desc         = "HUD element opacity (0.1 to 1.0)",
        ky_opt_icon_size            = "Icon Size",
        ky_opt_icon_size_desc       = "Size of buff/kill icons in pixels",
        ky_opt_reset                = "Reset to Defaults",
        ky_opt_reset_desc           = "Reset all settings to their default values",
        ky_opt_debug_sim            = "Debug: Simulate",
        ky_opt_debug_sim_desc       = "Show 8 demo buffs + 5 demo kills for 8 seconds",
        ky_opt_debug_clear          = "Debug: Clear",
        ky_opt_debug_clear_desc     = "Remove all active buffs and kills from the HUD",

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
    if Kyosh1roHUD and Kyosh1roHUD.BUFF_MAP then
        local buff_fallbacks = {}
        for buff_id, _ in pairs(Kyosh1roHUD.BUFF_MAP) do
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

    if blt_lang == "fr" or blt_lang == "french" or game_french then
        table.insert(try_files, base .. "french.json")
    end
    table.insert(try_files, base .. "english.json") -- Toujours en fallback

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

    -- Toujours ajouter les fallbacks (ils ne remplacent pas les clés déjà chargées)
    add_fallbacks(loc)
end)
