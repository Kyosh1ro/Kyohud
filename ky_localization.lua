-- ky_localization.lua — Chargement des traductions + fallbacks
-- Kyosh1ro HUD v1.0.0

local MOD_NAME = "Kyosh1ro HUD"

local function logi(msg)
    pcall(function() log("[" .. MOD_NAME .. "][Loc] " .. tostring(msg)) end)
end

-- Fallbacks intégrés pour garantir aucun "ERROR:" dans les menus
local function add_fallbacks(loc)
    loc:add_localized_strings({
        -- Menu principal
        ky_menu_title = "Kyosh1ro HUD",
        ky_menu_desc  = "Circular buff display & killfeed around the crosshair",

        -- Options
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
    })
end

Hooks:Add("LocalizationManagerPostInit", "KH_Localization", function(loc)
    local base = ModPath .. "loc/"
    local loaded = false

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
        if io.file_is_readable and io.file_is_readable(path) then
            loc:load_localization_file(path)
            logi("Chargé: " .. path)
            loaded = true
        elseif file and file.FileExists and file.FileExists(path) then
            loc:load_localization_file(path)
            logi("Chargé: " .. path)
            loaded = true
        end
    end

    if not loaded then
        logi("Aucun fichier de localisation trouvé, utilisation des fallbacks internes.")
    end

    -- Toujours ajouter les fallbacks (ils ne remplacent pas les clés déjà chargées)
    add_fallbacks(loc)
end)
