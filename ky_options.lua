-- ky_options.lua — Menu BLT + sauvegarde/chargement des paramètres
-- Kyosh1ro HUD v1.5.0
-- UN SEUL BuildMenu (SuperBLT limitation), sous-menus par deep_clone

if not Kyosh1roHUD then Kyosh1roHUD = {} end
local KH = Kyosh1roHUD
local MY_MOD_PATH = ModPath

local catalog_ok, catalog_err = pcall(dofile, MY_MOD_PATH .. "ky_buff_catalog.lua")
if not catalog_ok then
    log("[Kyosh1ro HUD] Erreur chargement catalogue buffs (options): " .. tostring(catalog_err))
end

-- ═══════════════════════════════════════════════════
-- 1) Paramètres par défaut & persistence
-- ═══════════════════════════════════════════════════
KH._settings_path = SavePath .. "kyosh1ro_hud_settings.json"

KH._defaults = {
    enable_killfeed = true,
    killfeed_size   = 3,
    enable_buffs    = true,
    circle_radius   = 250,
    angle_start     = 315,
    angle_end       = 90,
    buff_duration   = 5,
    opacity         = 0.9,
    icon_size       = 32,
}

KH._default_categories = {
    mastermind = true, enforcer = true, technician = true,
    ghost = true, fugitive = true, perk = true, debuff = true,
    team = true, player_action = true, gage = true, ai = true,
}

local function build_default_buff_toggles()
    if KH.BuildDefaultBuffToggles then
        return KH.BuildDefaultBuffToggles()
    end

    local t = {}
    if KH.BUFF_MAP then
        for bid, _ in pairs(KH.BUFF_MAP) do
            t[bid] = true
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
            -- PAS de `x and y or z` ici : il renvoie le défaut quand la valeur sauvée est `false`
            for k, dv in pairs(KH._defaults) do
                if data[k] ~= nil then
                    KH.settings[k] = data[k]
                else
                    KH.settings[k] = dv
                end
            end
            if type(data.buff_categories) == "table" then
                for k, v in pairs(KH._default_categories) do
                    if data.buff_categories[k] ~= nil then
                        KH.settings.buff_categories[k] = data.buff_categories[k]
                    else
                        KH.settings.buff_categories[k] = v
                    end
                end
            end
            if type(data.buff_toggles) == "table" then
                KH.settings.buff_toggles = data.buff_toggles
                local defs = build_default_buff_toggles()
                for bid, dv in pairs(defs) do
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
        KH.Save(); if KH.RefreshHUD then KH:RefreshHUD() end
    end
end
local function make_slider_cb(key, is_int)
    return function(self, item)
        local v = tonumber(item:value()) or KH._defaults[key]
        KH.settings[key] = is_int and math.floor(v) or v
        KH.Save(); if KH.RefreshHUD then KH:RefreshHUD() end
    end
end

MenuCallbackHandler.KY_ToggleKillfeed = make_toggle_cb("enable_killfeed")
MenuCallbackHandler.KY_SetKillfeedSize = function(self, item)
    local value = math.floor(tonumber(item:value()) or KH._defaults.killfeed_size)
    KH.settings.killfeed_size = math.max(1, math.min(3, value))

    if type(KH._kills) == "table" then
        while #KH._kills > KH.settings.killfeed_size do
            table.remove(KH._kills, 1)
        end
    end

    KH.Save(); if KH.RefreshHUD then KH:RefreshHUD() end
end
MenuCallbackHandler.KY_ToggleBuffs    = make_toggle_cb("enable_buffs")
MenuCallbackHandler.KY_SetRadius      = make_slider_cb("circle_radius", true)
MenuCallbackHandler.KY_SetAngleStart  = make_slider_cb("angle_start", true)
MenuCallbackHandler.KY_SetAngleEnd    = make_slider_cb("angle_end", true)
MenuCallbackHandler.KY_SetDuration    = make_slider_cb("buff_duration", false)
MenuCallbackHandler.KY_SetOpacity     = make_slider_cb("opacity", false)
MenuCallbackHandler.KY_SetIconSize    = make_slider_cb("icon_size", true)
MenuCallbackHandler.KY_ResetDefaults  = function() KH.ResetDefaults() end
MenuCallbackHandler.KY_DebugSimulate  = function() if KH.DebugSimulate then KH:DebugSimulate(8) end end
MenuCallbackHandler.KY_DebugClear     = function() if KH.DebugClear then KH:DebugClear() end end
MenuCallbackHandler.KY_BackCallback   = function() end

local CAT_ORDER = {
    "mastermind", "enforcer", "technician", "ghost", "fugitive",
    "perk", "debuff", "team", "player_action", "gage", "ai",
}

for _, cat_id in ipairs(CAT_ORDER) do
    local cid = cat_id
    MenuCallbackHandler["KY_ToggleCat_" .. cat_id] = function(self, item)
        KH.settings.buff_categories[cid] = (item:value() == "on")
        KH.Save(); if KH.RefreshHUD then KH:RefreshHUD() end
    end
end

if KH.BUFF_MAP then
    for buff_id, _ in pairs(KH.BUFF_MAP) do
        local bid = buff_id
        MenuCallbackHandler["KY_ToggleBuff_" .. buff_id] = function(self, item)
            KH.settings.buff_toggles[bid] = (item:value() == "on")
            KH.Save(); if KH.RefreshHUD then KH:RefreshHUD() end
        end
    end
end

-- ═══════════════════════════════════════════════════
-- 3) Construction du menu
-- ═══════════════════════════════════════════════════
local MENU_ID = "ky_hud_options"

local CAT_MENU_IDS = {}
for _, cat_id in ipairs(CAT_ORDER) do
    CAT_MENU_IDS[cat_id] = "ky_buffs_" .. cat_id
end

-- ── HOOK 1 : Setup ──
Hooks:Add("MenuManagerSetupCustomMenus", "KY_SetupMenu", function(menu_manager, nodes)
    MenuHelper:NewMenu(MENU_ID)
    -- PAS de NewMenu pour les sous-menus, on les crée par clonage
end)

-- ── HOOK 2 : Populate (items du menu principal uniquement) ──
Hooks:Add("MenuManagerPopulateCustomMenus", "KY_PopulateMenu", function()
    MenuHelper:AddToggle({
        id = "ky_enable_killfeed", title = "ky_opt_enable_killfeed",
        desc = "ky_opt_enable_killfeed_desc", callback = "KY_ToggleKillfeed",
        value = KH.settings.enable_killfeed, menu_id = MENU_ID, priority = 1000,
    })
    MenuHelper:AddSlider({
        id = "ky_killfeed_size", title = "ky_opt_killfeed_size", desc = "ky_opt_killfeed_size_desc",
        callback = "KY_SetKillfeedSize", value = KH.settings.killfeed_size,
        min = 1, max = 3, step = 1, show_value = true,
        menu_id = MENU_ID, priority = 999,
    })
    MenuHelper:AddToggle({
        id = "ky_enable_buffs", title = "ky_opt_enable_buffs",
        desc = "ky_opt_enable_buffs_desc", callback = "KY_ToggleBuffs",
        value = KH.settings.enable_buffs, menu_id = MENU_ID, priority = 998,
    })

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

-- ── Utilitaire : créer un item toggle sur un noeud existant ──
-- Le toggle PD2 a BESOIN des options on/off avec les textures tickbox
local function add_toggle_to_node(node, id, title_id, desc_id, callback_name, value)
    local ok, err = pcall(function()
        local data = {
            type = "CoreMenuItemToggle.ItemToggle",
            {
                _meta    = "option",
                icon     = "guis/textures/menu_tickbox",
                value    = "on",
                x = 24, y = 0, w = 24, h = 24,
                s_icon   = "guis/textures/menu_tickbox",
                s_x = 24, s_y = 24, s_w = 24, s_h = 24,
            },
            {
                _meta    = "option",
                icon     = "guis/textures/menu_tickbox",
                value    = "off",
                x = 0, y = 0, w = 24, h = 24,
                s_icon   = "guis/textures/menu_tickbox",
                s_x = 0, s_y = 24, s_w = 24, s_h = 24,
            },
        }
        local params = {
            name         = id,
            text_id      = title_id,
            help_id      = desc_id,
            callback     = callback_name,
            icon_by_text = true,
        }
        local item = node:create_item(data, params)
        if item then
            item:set_value(value and "on" or "off")
            node:add_item(item)
        end
    end)
    if not ok then
        log("[Kyosh1ro HUD] Erreur ajout toggle " .. id .. ": " .. tostring(err))
    end
end

-- ── HOOK 3 : Build ──
Hooks:Add("MenuManagerBuildCustomMenus", "KY_BuildMenu", function(menu_manager, nodes)

    -- 3a. UN SEUL BuildMenu — le menu principal
    local main_ok, main_err = pcall(function()
        nodes[MENU_ID] = MenuHelper:BuildMenu(MENU_ID, { back_callback = "KY_BackCallback" })
    end)

    if not main_ok then
        log("[Kyosh1ro HUD] ERREUR menu principal: " .. tostring(main_err))
        return
    end

    -- 3b. Créer les sous-menus par CLONAGE du noeud principal
    local sub_count = 0
    for _, cat_id in ipairs(CAT_ORDER) do
        local sub_id = CAT_MENU_IDS[cat_id]

        local clone_ok, clone_err = pcall(function()
            -- Cloner le noeud du menu principal (récupère le renderer, layout, etc.)
            local sub_node = deep_clone(nodes[MENU_ID])
            sub_node:clean_items()

            -- Ajouter le toggle de la catégorie en premier
            add_toggle_to_node(
                sub_node,
                "ky_cat_" .. cat_id,
                "ky_opt_cat_" .. cat_id,
                "ky_opt_cat_" .. cat_id .. "_desc",
                "KY_ToggleCat_" .. cat_id,
                KH.settings.buff_categories[cat_id] ~= false
            )

            -- Ajouter les toggles de buffs individuels
            if KH.BUFF_MAP then
                local sorted = KH.GetSortedBuffIdsForCategory and KH.GetSortedBuffIdsForCategory(cat_id) or {}

                for _, bid in ipairs(sorted) do
                    local val = true
                    if KH.settings.buff_toggles and KH.settings.buff_toggles[bid] ~= nil then
                        val = KH.settings.buff_toggles[bid]
                    end
                    add_toggle_to_node(
                        sub_node,
                        "ky_buff_" .. bid,
                        "ky_opt_buff_" .. bid,
                        "ky_opt_buff_" .. bid .. "_desc",
                        "KY_ToggleBuff_" .. bid,
                        val
                    )
                end
            end

            nodes[sub_id] = sub_node
        end)

        if clone_ok then
            -- Ajouter le lien vers ce sous-menu dans le menu principal
            MenuHelper:AddMenuItem(
                nodes[MENU_ID],
                sub_id,
                "ky_opt_cat_" .. cat_id .. "_buffs",
                "ky_opt_cat_" .. cat_id .. "_buffs_desc"
            )
            sub_count = sub_count + 1
        else
            log("[Kyosh1ro HUD] ERREUR clone sous-menu " .. cat_id .. ": " .. tostring(clone_err))
        end
    end

    -- 3c. Lier au menu BLT Options
    MenuHelper:AddMenuItem(nodes.blt_options, MENU_ID, "ky_menu_title", "ky_menu_desc")

    log("[Kyosh1ro HUD] Menu construit: principal + " .. sub_count .. "/11 sous-menus (deep_clone).")
end)
