-- ky_options.lua — Menu BLT + sauvegarde/chargement des paramètres
-- Kyosh1ro HUD v1.0.0

if not Kyosh1roHUD then Kyosh1roHUD = {} end
local KH = Kyosh1roHUD

-- ═══════════════════════════════════════════════════
-- 1) Paramètres par défaut & persistence
-- ═══════════════════════════════════════════════════
KH._settings_path = SavePath .. "kyosh1ro_killfeed_settings.txt"

KH._defaults = {
    enable_killfeed = true,
    enable_buffs    = true,

    circle_radius = 250,
    angle_start   = 360,
    angle_end     = 270,
    buff_duration = 5,
    opacity       = 0.9,
    icon_size     = 32,
}

-- Initialise les settings à partir des defaults si pas encore fait
if not KH.settings then
    KH.settings = {}
    for k, v in pairs(KH._defaults) do
        KH.settings[k] = v
    end
end

-- ── Sauvegarde ──
function KH.Save()
    local f = io.open(KH._settings_path, "w")
    if f then
        f:write(json.encode(KH.settings))
        f:close()
    end
end

-- ── Chargement ──
function KH.Load()
    local f = io.open(KH._settings_path, "r")
    if f then
        local raw = f:read("*all")
        f:close()
        local ok, data = pcall(json.decode, raw)
        if ok and type(data) == "table" then
            for k, default_v in pairs(KH._defaults) do
                if data[k] ~= nil then
                    KH.settings[k] = data[k]
                else
                    KH.settings[k] = default_v
                end
            end
        end
    end
end
KH.Load()

-- ── Reset ──
function KH.ResetDefaults()
    for k, v in pairs(KH._defaults) do
        KH.settings[k] = v
    end
    KH.Save()
    if KH.RefreshHUD then KH:RefreshHUD() end
end

-- ═══════════════════════════════════════════════════
-- 2) Callbacks du menu BLT
-- ═══════════════════════════════════════════════════
MenuCallbackHandler.KY_ToggleKillfeed = function(self, item)
    KH.settings.enable_killfeed = (item:value() == "on")
    KH.Save()
    if KH.RefreshHUD then KH:RefreshHUD() end
end

MenuCallbackHandler.KY_ToggleBuffs = function(self, item)
    KH.settings.enable_buffs = (item:value() == "on")
    KH.Save()
    if KH.RefreshHUD then KH:RefreshHUD() end
end

MenuCallbackHandler.KY_SetRadius = function(self, item)
    KH.settings.circle_radius = math.floor(tonumber(item:value()) or KH._defaults.circle_radius)
    KH.Save()
    if KH.RefreshHUD then KH:RefreshHUD() end
end

MenuCallbackHandler.KY_SetAngleStart = function(self, item)
    KH.settings.angle_start = math.floor(tonumber(item:value()) or KH._defaults.angle_start)
    KH.Save()
    if KH.RefreshHUD then KH:RefreshHUD() end
end

MenuCallbackHandler.KY_SetAngleEnd = function(self, item)
    KH.settings.angle_end = math.floor(tonumber(item:value()) or KH._defaults.angle_end)
    KH.Save()
    if KH.RefreshHUD then KH:RefreshHUD() end
end

MenuCallbackHandler.KY_SetDuration = function(self, item)
    KH.settings.buff_duration = tonumber(item:value()) or KH._defaults.buff_duration
    KH.Save()
    if KH.RefreshHUD then KH:RefreshHUD() end
end

MenuCallbackHandler.KY_SetOpacity = function(self, item)
    KH.settings.opacity = tonumber(item:value()) or KH._defaults.opacity
    KH.Save()
    if KH.RefreshHUD then KH:RefreshHUD() end
end

MenuCallbackHandler.KY_SetIconSize = function(self, item)
    KH.settings.icon_size = math.floor(tonumber(item:value()) or KH._defaults.icon_size)
    KH.Save()
    if KH.RefreshHUD then KH:RefreshHUD() end
end

MenuCallbackHandler.KY_ResetDefaults = function()
    KH.ResetDefaults()
end

-- Débogage
MenuCallbackHandler.KY_DebugSimulate = function()
    if KH.DebugSimulate then KH:DebugSimulate(8, 8) end
end

MenuCallbackHandler.KY_DebugClear = function()
    if KH.DebugClear then KH:DebugClear() end
end

-- ═══════════════════════════════════════════════════
-- 3) Construction du menu BLT
-- ═══════════════════════════════════════════════════
Hooks:Add("MenuManagerBuildCustomMenus", "KY_BuildMenu", function(menu_manager, nodes)
    local MENU_ID = "ky_hud_options"
    MenuHelper:NewMenu(MENU_ID)

    -- ── Toggles ──
    MenuHelper:AddToggle({
        id       = "ky_enable_killfeed",
        title    = "ky_opt_enable_killfeed",
        desc     = "ky_opt_enable_killfeed_desc",
        callback = "KY_ToggleKillfeed",
        value    = KH.settings.enable_killfeed,
        menu_id  = MENU_ID,
        priority = 100,
    })

    MenuHelper:AddToggle({
        id       = "ky_enable_buffs",
        title    = "ky_opt_enable_buffs",
        desc     = "ky_opt_enable_buffs_desc",
        callback = "KY_ToggleBuffs",
        value    = KH.settings.enable_buffs,
        menu_id  = MENU_ID,
        priority = 99,
    })

    -- ── Sliders ──
    MenuHelper:AddSlider({
        id         = "ky_circle_radius",
        title      = "ky_opt_radius",
        desc       = "ky_opt_radius_desc",
        callback   = "KY_SetRadius",
        value      = KH.settings.circle_radius,
        min        = 100,
        max        = 500,
        step       = 10,
        show_value = true,
        menu_id    = MENU_ID,
        priority   = 95,
    })

    MenuHelper:AddSlider({
        id         = "ky_angle_start",
        title      = "ky_opt_angle_start",
        desc       = "ky_opt_angle_start_desc",
        callback   = "KY_SetAngleStart",
        value      = KH.settings.angle_start,
        min        = 0,
        max        = 360,
        step       = 5,
        show_value = true,
        menu_id    = MENU_ID,
        priority   = 94,
    })

    MenuHelper:AddSlider({
        id         = "ky_angle_end",
        title      = "ky_opt_angle_end",
        desc       = "ky_opt_angle_end_desc",
        callback   = "KY_SetAngleEnd",
        value      = KH.settings.angle_end,
        min        = 0,
        max        = 360,
        step       = 5,
        show_value = true,
        menu_id    = MENU_ID,
        priority   = 93,
    })

    MenuHelper:AddSlider({
        id         = "ky_buff_duration",
        title      = "ky_opt_duration",
        desc       = "ky_opt_duration_desc",
        callback   = "KY_SetDuration",
        value      = KH.settings.buff_duration,
        min        = 1,
        max        = 10,
        step       = 0.5,
        show_value = true,
        menu_id    = MENU_ID,
        priority   = 92,
    })

    MenuHelper:AddSlider({
        id         = "ky_opacity",
        title      = "ky_opt_opacity",
        desc       = "ky_opt_opacity_desc",
        callback   = "KY_SetOpacity",
        value      = KH.settings.opacity,
        min        = 0.1,
        max        = 1,
        step       = 0.05,
        show_value = true,
        menu_id    = MENU_ID,
        priority   = 91,
    })

    MenuHelper:AddSlider({
        id         = "ky_icon_size",
        title      = "ky_opt_icon_size",
        desc       = "ky_opt_icon_size_desc",
        callback   = "KY_SetIconSize",
        value      = KH.settings.icon_size,
        min        = 16,
        max        = 64,
        step       = 2,
        show_value = true,
        menu_id    = MENU_ID,
        priority   = 90,
    })

    -- ── Boutons ──
    MenuHelper:AddButton({
        id       = "ky_reset_defaults",
        title    = "ky_opt_reset",
        desc     = "ky_opt_reset_desc",
        callback = "KY_ResetDefaults",
        menu_id  = MENU_ID,
        priority = 10,
    })

    MenuHelper:AddButton({
        id       = "ky_debug_sim",
        title    = "ky_opt_debug_sim",
        desc     = "ky_opt_debug_sim_desc",
        callback = "KY_DebugSimulate",
        menu_id  = MENU_ID,
        priority = 5,
    })

    MenuHelper:AddButton({
        id       = "ky_debug_clear",
        title    = "ky_opt_debug_clear",
        desc     = "ky_opt_debug_clear_desc",
        callback = "KY_DebugClear",
        menu_id  = MENU_ID,
        priority = 4,
    })

    -- Construire et enregistrer le nœud du menu
    nodes[MENU_ID] = MenuHelper:BuildMenu(MENU_ID)
    MenuHelper:AddMenuItem(nodes.blt_options, MENU_ID, "ky_menu_title", "ky_menu_desc")

    log("[Kyosh1ro HUD] Menu BLT construit.")
end)
