-- ky_options.lua — Menu BLT + sauvegarde/chargement des paramètres
-- Kyosh1ro HUD v1.3.0
-- Utilise le pattern 3-hooks BLT (Setup → Populate → Build)

if not Kyosh1roHUD then Kyosh1roHUD = {} end
local KH = Kyosh1roHUD

-- ═══════════════════════════════════════════════════
-- 1) Paramètres par défaut & persistence
-- ═══════════════════════════════════════════════════
KH._settings_path = SavePath .. "kyosh1ro_hud_settings.json"

KH._defaults = {
    enable_killfeed = true,
    enable_buffs    = true,

    circle_radius = 250,
    angle_start   = 315,
    angle_end     = 90,
    buff_duration = 5,
    opacity       = 0.9,
    icon_size     = 32,
}

KH._default_categories = {
    mastermind    = true,
    enforcer      = true,
    technician    = true,
    ghost         = true,
    fugitive      = true,
    perk          = true,
    debuff        = true,
    team          = true,
    player_action = true,
    gage          = true,
    ai            = true,
}

local function build_default_buff_toggles()
    local t = {}
    if KH.BUFF_MAP then
        for buff_id, _ in pairs(KH.BUFF_MAP) do
            t[buff_id] = true  -- Tout activé par défaut pour le debug
        end
    end
    return t
end

if not KH.settings then
    KH.settings = {}
    for k, v in pairs(KH._defaults) do KH.settings[k] = v end
end
if not KH.settings.buff_categories then
    KH.settings.buff_categories = {}
    for k, v in pairs(KH._default_categories) do KH.settings.buff_categories[k] = v end
end
if not KH.settings.buff_toggles then
    KH.settings.buff_toggles = build_default_buff_toggles()
end

function KH.Save()
    local f = io.open(KH._settings_path, "w")
    if f then f:write(json.encode(KH.settings)); f:close() end
end

function KH.Load()
    local f = io.open(KH._settings_path, "r")
    if f then
        local raw = f:read("*all"); f:close()
        local ok, data = pcall(json.decode, raw)
        if ok and type(data) == "table" then
            for k, dv in pairs(KH._defaults) do
                KH.settings[k] = (data[k] ~= nil) and data[k] or dv
            end
            if type(data.buff_categories) == "table" then
                for k, v in pairs(KH._default_categories) do
                    KH.settings.buff_categories[k] = (data.buff_categories[k] ~= nil) and data.buff_categories[k] or v
                end
            end
            if type(data.buff_toggles) == "table" then
                KH.settings.buff_toggles = data.buff_toggles
                local defaults = build_default_buff_toggles()
                for bid, dv in pairs(defaults) do
                    if KH.settings.buff_toggles[bid] == nil then KH.settings.buff_toggles[bid] = dv end
                end
            else
                KH.settings.buff_toggles = build_default_buff_toggles()
            end
        end
    end
end
KH.Load()

function KH.ResetDefaults()
    for k, v in pairs(KH._defaults) do KH.settings[k] = v end
    for k, v in pairs(KH._default_categories) do KH.settings.buff_categories[k] = v end
    KH.settings.buff_toggles = build_default_buff_toggles()
    KH.Save()
    if KH.RefreshHUD then KH:RefreshHUD() end
end

-- ═══════════════════════════════════════════════════
-- 2) Callbacks BLT
-- ═══════════════════════════════════════════════════
local function make_toggle_cb(key)
    return function(self, item)
        KH.settings[key] = (item:value() == "on")
        KH.Save()
        if KH.RefreshHUD then KH:RefreshHUD() end
    end
end

local function make_slider_cb(key, is_int)
    return function(self, item)
        local v = tonumber(item:value()) or KH._defaults[key]
        KH.settings[key] = is_int and math.floor(v) or v
        KH.Save()
        if KH.RefreshHUD then KH:RefreshHUD() end
    end
end

MenuCallbackHandler.KY_ToggleKillfeed = make_toggle_cb("enable_killfeed")
MenuCallbackHandler.KY_ToggleBuffs    = make_toggle_cb("enable_buffs")
MenuCallbackHandler.KY_SetRadius      = make_slider_cb("circle_radius", true)
MenuCallbackHandler.KY_SetAngleStart  = make_slider_cb("angle_start", true)
MenuCallbackHandler.KY_SetAngleEnd    = make_slider_cb("angle_end", true)
MenuCallbackHandler.KY_SetDuration    = make_slider_cb("buff_duration", false)
MenuCallbackHandler.KY_SetOpacity     = make_slider_cb("opacity", false)
MenuCallbackHandler.KY_SetIconSize    = make_slider_cb("icon_size", true)

MenuCallbackHandler.KY_ResetDefaults = function() KH.ResetDefaults() end
MenuCallbackHandler.KY_DebugSimulate = function()
    if KH.DebugSimulate then KH:DebugSimulate(8, 8) end
end
MenuCallbackHandler.KY_DebugClear = function()
    if KH.DebugClear then KH:DebugClear() end
end
MenuCallbackHandler.KY_BackCallback = function() end

-- Catégories
local CAT_ORDER = {
    "mastermind", "enforcer", "technician", "ghost", "fugitive",
    "perk", "debuff", "team", "player_action", "gage", "ai",
}
for _, cat_id in ipairs(CAT_ORDER) do
    local cid = cat_id
    MenuCallbackHandler["KY_ToggleCat_" .. cat_id] = function(self, item)
        KH.settings.buff_categories[cid] = (item:value() == "on")
        KH.Save()
        if KH.RefreshHUD then KH:RefreshHUD() end
    end
end

-- ═══════════════════════════════════════════════════
-- 3) Construction du menu — pattern 3 hooks
-- ═══════════════════════════════════════════════════
local MENU_ID = "ky_hud_options"

-- HOOK 1 : Créer le menu vide
Hooks:Add("MenuManagerSetupCustomMenus", "KY_SetupMenu", function(menu_manager, nodes)
    MenuHelper:NewMenu(MENU_ID)
end)

-- HOOK 2 : Remplir le menu d'items
Hooks:Add("MenuManagerPopulateCustomMenus", "KY_PopulateMenu", function()
    -- ── Toggles principaux ──
    MenuHelper:AddToggle({
        id = "ky_enable_killfeed", title = "ky_opt_enable_killfeed",
        desc = "ky_opt_enable_killfeed_desc", callback = "KY_ToggleKillfeed",
        value = KH.settings.enable_killfeed, menu_id = MENU_ID, priority = 1000,
    })
    MenuHelper:AddToggle({
        id = "ky_enable_buffs", title = "ky_opt_enable_buffs",
        desc = "ky_opt_enable_buffs_desc", callback = "KY_ToggleBuffs",
        value = KH.settings.enable_buffs, menu_id = MENU_ID, priority = 999,
    })

    -- ── Sliders ──
    MenuHelper:AddSlider({
        id = "ky_circle_radius", title = "ky_opt_radius", desc = "ky_opt_radius_desc",
        callback = "KY_SetRadius", value = KH.settings.circle_radius,
        min = 100, max = 500, step = 10, show_value = true,
        menu_id = MENU_ID, priority = 950,
    })
    MenuHelper:AddSlider({
        id = "ky_angle_start", title = "ky_opt_angle_start", desc = "ky_opt_angle_start_desc",
        callback = "KY_SetAngleStart", value = KH.settings.angle_start,
        min = 0, max = 360, step = 5, show_value = true,
        menu_id = MENU_ID, priority = 949,
    })
    MenuHelper:AddSlider({
        id = "ky_angle_end", title = "ky_opt_angle_end", desc = "ky_opt_angle_end_desc",
        callback = "KY_SetAngleEnd", value = KH.settings.angle_end,
        min = 0, max = 360, step = 5, show_value = true,
        menu_id = MENU_ID, priority = 948,
    })
    MenuHelper:AddSlider({
        id = "ky_buff_duration", title = "ky_opt_duration", desc = "ky_opt_duration_desc",
        callback = "KY_SetDuration", value = KH.settings.buff_duration,
        min = 1, max = 10, step = 0.5, show_value = true,
        menu_id = MENU_ID, priority = 947,
    })
    MenuHelper:AddSlider({
        id = "ky_opacity", title = "ky_opt_opacity", desc = "ky_opt_opacity_desc",
        callback = "KY_SetOpacity", value = KH.settings.opacity,
        min = 0.1, max = 1, step = 0.05, show_value = true,
        menu_id = MENU_ID, priority = 946,
    })
    MenuHelper:AddSlider({
        id = "ky_icon_size", title = "ky_opt_icon_size", desc = "ky_opt_icon_size_desc",
        callback = "KY_SetIconSize", value = KH.settings.icon_size,
        min = 16, max = 64, step = 2, show_value = true,
        menu_id = MENU_ID, priority = 945,
    })

    -- ── Toggles catégories de buffs ──
    local prio = 800
    for _, cat_id in ipairs(CAT_ORDER) do
        MenuHelper:AddToggle({
            id       = "ky_cat_" .. cat_id,
            title    = "ky_opt_cat_" .. cat_id,
            desc     = "ky_opt_cat_" .. cat_id .. "_desc",
            callback = "KY_ToggleCat_" .. cat_id,
            value    = KH.settings.buff_categories[cat_id] ~= false,
            menu_id  = MENU_ID,
            priority = prio,
        })
        prio = prio - 1
    end

    -- ── Boutons utilitaires ──
    MenuHelper:AddButton({
        id = "ky_reset_defaults", title = "ky_opt_reset", desc = "ky_opt_reset_desc",
        callback = "KY_ResetDefaults", menu_id = MENU_ID, priority = 10,
    })
    MenuHelper:AddButton({
        id = "ky_debug_sim", title = "ky_opt_debug_sim", desc = "ky_opt_debug_sim_desc",
        callback = "KY_DebugSimulate", menu_id = MENU_ID, priority = 5,
    })
    MenuHelper:AddButton({
        id = "ky_debug_clear", title = "ky_opt_debug_clear", desc = "ky_opt_debug_clear_desc",
        callback = "KY_DebugClear", menu_id = MENU_ID, priority = 4,
    })
end)

-- HOOK 3 : Construire et enregistrer le menu
Hooks:Add("MenuManagerBuildCustomMenus", "KY_BuildMenu", function(menu_manager, nodes)
    local ok, err = pcall(function()
        nodes[MENU_ID] = MenuHelper:BuildMenu(MENU_ID, { back_callback = "KY_BackCallback" })
        MenuHelper:AddMenuItem(nodes.blt_options, MENU_ID, "ky_menu_title", "ky_menu_desc")
    end)

    if ok then
        log("[Kyosh1ro HUD] Menu BLT construit avec succès.")
    else
        log("[Kyosh1ro HUD] ERREUR construction menu: " .. tostring(err))
        log("[Kyosh1ro HUD] Tentative de construction manuelle du menu...")

        -- Fallback : cloner le noeud blt_options et le vider
        local fallback_ok, fallback_err = pcall(function()
            if nodes.blt_options then
                local node = deep_clone(nodes.blt_options)
                node:clean_items()
                nodes[MENU_ID] = node
                MenuHelper:AddMenuItem(nodes.blt_options, MENU_ID, "ky_menu_title", "ky_menu_desc")
                log("[Kyosh1ro HUD] Menu fallback créé (sans items configurables).")
            end
        end)

        if not fallback_ok then
            log("[Kyosh1ro HUD] Fallback menu échoué: " .. tostring(fallback_err))
        end
    end
end)
