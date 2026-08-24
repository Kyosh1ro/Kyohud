-- ky_options.lua — Menu BLT + sauvegarde/chargement des paramètres
-- KyoHUD v1.5.0
-- Structure fixe en JSON ; UN SEUL BuildMenu, sous-menus par deep_clone

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud
local MY_MOD_PATH = ModPath

local catalog_ok, catalog_err = pcall(dofile, MY_MOD_PATH .. "ky_buff_catalog.lua")
if not catalog_ok then
    log("[KyoHUD] Erreur chargement catalogue buffs (options): " .. tostring(catalog_err))
end

-- ═══════════════════════════════════════════════════
-- 1) Paramètres par défaut & persistence
-- ═══════════════════════════════════════════════════
KH._settings_path = SavePath .. "kyohud_settings.json"
KH._legacy_settings_path = SavePath .. "kyosh1ro_hud_settings.json"

KH._defaults = {
    language        = 1,
    enable_killfeed = true,
    killfeed_size   = 3,
    enable_buffs    = true,
    circle_radius   = 250,
    buff_position_x = 50,
    buff_position_y = 83,
    buff_duration   = 5,
    opacity         = 0.9,
    icon_size       = 32,
}

local HUD_DEFAULT_LAYOUTS = {
    {
        id = "void_ui",
        mod_name = "Void UI",
        values = {
            circle_radius   = 280,
            buff_position_x = 50,
            buff_position_y = 98,
        },
    },
    {
        id = "vanillahud_plus",
        mod_name = "VanillaHUDPlus",
        values = {
            -- VanillaHUD+ centre sa liste à H - 125 px sur son panneau 1280 x 720.
            buff_position_x = 50,
            buff_position_y = 83,
        },
    },
}

local function is_blt_mod_enabled(name)
    if not (BLT and BLT.Mods and BLT.Mods.GetModByName) then
        return false
    end

    local found_ok, mod = pcall(function()
        return BLT.Mods:GetModByName(name)
    end)
    if not found_ok or not mod or not mod.IsEnabled then
        return false
    end

    local enabled_ok, enabled = pcall(function()
        return mod:IsEnabled()
    end)
    return enabled_ok and enabled == true
end

KH._default_layout_profile = "standard"
for _, profile in ipairs(HUD_DEFAULT_LAYOUTS) do
    if is_blt_mod_enabled(profile.mod_name) then
        for key, value in pairs(profile.values) do
            KH._defaults[key] = value
        end
        KH._default_layout_profile = profile.id
        break
    end
end

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
    local loaded_legacy_settings = false
    if not f then
        f = io.open(KH._legacy_settings_path, "r")
        loaded_legacy_settings = f ~= nil
    end
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
            if loaded_legacy_settings then
                KH.Save()
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
MenuCallbackHandler.KY_SetLanguage = function(self, item)
    local value = math.floor(tonumber(item:value()) or KH._defaults.language)
    KH.settings.language = math.max(1, math.min(3, value))
    KH.Save()
end
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
MenuCallbackHandler.KY_SetBuffPositionX = make_slider_cb("buff_position_x", true)
MenuCallbackHandler.KY_SetBuffPositionY = make_slider_cb("buff_position_y", true)
MenuCallbackHandler.KY_SetDuration    = make_slider_cb("buff_duration", true)
MenuCallbackHandler.KY_SetOpacity     = function(self, item)
    local percent = math.floor(tonumber(item:value()) or (KH._defaults.opacity * 100))
    KH.settings.opacity = math.max(10, math.min(100, percent)) / 100
    KH.Save(); if KH.RefreshHUD then KH:RefreshHUD() end
end
MenuCallbackHandler.KY_SetIconSize    = make_slider_cb("icon_size", true)
MenuCallbackHandler.KY_ResetDefaults  = function() KH.ResetDefaults() end
MenuCallbackHandler.KY_DebugSimulate  = function() if KH.DebugSimulate then KH:DebugSimulate(8) end end
MenuCallbackHandler.KY_DebugClear     = function() if KH.DebugClear then KH:DebugClear() end end
MenuCallbackHandler.KY_BackCallback   = function() end

local function load_menu_definition(filename)
    local path = MY_MOD_PATH .. "menu/" .. filename
    local file = io.open(path, "r")
    if not file then
        log("[KyoHUD] Impossible d'ouvrir la définition de menu: " .. tostring(path))
        return nil
    end

    local raw = file:read("*all")
    file:close()

    local ok, content = pcall(json.decode, raw)
    if not ok or type(content) ~= "table" then
        log("[KyoHUD] JSON de menu invalide " .. tostring(path) .. ": " .. tostring(content))
        return nil
    end
    if type(content.menu_id) ~= "string" or type(content.items) ~= "table" then
        log("[KyoHUD] Définition de menu incomplète: " .. tostring(path))
        return nil
    end
    return content
end

local MAIN_MENU_DEFINITION = load_menu_definition("menu.json")
local BUFFS_MENU_DEFINITION = load_menu_definition("buffs.json")
local MENU_ID = MAIN_MENU_DEFINITION and MAIN_MENU_DEFINITION.menu_id or "kyohud_options"
local BUFFS_MENU_ID = BUFFS_MENU_DEFINITION and BUFFS_MENU_DEFINITION.menu_id or "kyohud_buffs_menu"

local CAT_ORDER = {}
local CAT_MENU_ITEMS = {}
if BUFFS_MENU_DEFINITION then
    for _, item in ipairs(BUFFS_MENU_DEFINITION.items) do
        if item.type == "button" and type(item.category) == "string" and type(item.next_menu) == "string" then
            table.insert(CAT_ORDER, item.category)
            CAT_MENU_ITEMS[item.category] = item
        end
    end
end

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
local function populate_json_menu(definition)
    if not definition then return end

    local items = definition.items
    local item_count = #items
    for index, item in ipairs(items) do
        local item_type = item.type
        local priority = item.priority or (item_count - index + 1)
        local value = item.default_value
        if item.value and KH.settings[item.value] ~= nil then
            value = KH.settings[item.value]
        end
        if item_type == "slider" and item.display_multiplier then
            value = value * item.display_multiplier
        end

        if item_type == "multiple_choice" then
            MenuHelper:AddMultipleChoice({
                id = item.id, title = item.title, desc = item.description,
                callback = item.callback, items = item.items,
                item_values = item.item_values, value = value,
                localized_items = item.localized_items,
                menu_id = definition.menu_id, priority = priority,
            })
        elseif item_type == "toggle" then
            MenuHelper:AddToggle({
                id = item.id, title = item.title, desc = item.description,
                callback = item.callback, value = value,
                menu_id = definition.menu_id, priority = priority,
            })
        elseif item_type == "slider" then
            MenuHelper:AddSlider({
                id = item.id, title = item.title, desc = item.description,
                callback = item.callback, value = value,
                min = item.min or 0, max = item.max or 1, step = item.step or 1,
                show_value = item.show_value ~= false,
                display_precision = item.display_precision or 0,
                menu_id = definition.menu_id, priority = priority,
            })
        elseif item_type == "button" then
            MenuHelper:AddButton({
                id = item.id, title = item.title, desc = item.description,
                callback = item.callback, next_node = item.next_menu,
                menu_id = definition.menu_id, priority = priority,
            })
        elseif item_type == "divider" then
            MenuHelper:AddDivider({
                id = "ky_divider_" .. tostring(index), size = item.size,
                menu_id = definition.menu_id, priority = priority,
            })
        else
            log("[KyoHUD] Type d'élément de menu JSON inconnu: " .. tostring(item_type))
        end
    end
end

-- ── HOOK 1 : Setup ──
Hooks:Add("MenuManagerSetupCustomMenus", "KY_SetupMenu", function(menu_manager, nodes)
    if not MAIN_MENU_DEFINITION or not BUFFS_MENU_DEFINITION then return end
    MenuHelper:NewMenu(MENU_ID)
    -- PAS de NewMenu pour les sous-menus, on les crée par clonage
end)

-- ── HOOK 2 : Populate (items du menu principal uniquement) ──
Hooks:Add("MenuManagerPopulateCustomMenus", "KY_PopulateMenu", function()
    populate_json_menu(MAIN_MENU_DEFINITION)
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
        log("[KyoHUD] Erreur ajout toggle " .. id .. ": " .. tostring(err))
    end
end

local function add_menu_link_to_node(node, id, title_id, desc_id, next_node)
    local ok, err = pcall(function()
        local item = node:create_item(
            { type = "CoreMenuItem.Item" },
            {
                name = id,
                text_id = title_id,
                help_id = desc_id,
                next_node = next_node,
            }
        )
        if item then node:add_item(item) end
    end)
    if not ok then
        log("[KyoHUD] Erreur ajout lien de menu " .. tostring(id) .. ": " .. tostring(err))
    end
end

-- ── HOOK 3 : Build ──
Hooks:Add("MenuManagerBuildCustomMenus", "KY_BuildMenu", function(menu_manager, nodes)
    if not MAIN_MENU_DEFINITION or not BUFFS_MENU_DEFINITION then return end

    -- 3a. UN SEUL BuildMenu — le menu principal
    local main_ok, main_err = pcall(function()
        nodes[MENU_ID] = MenuHelper:BuildMenu(MENU_ID, {
            back_callback = MAIN_MENU_DEFINITION.back_callback or "KY_BackCallback",
        })
    end)

    if not main_ok then
        log("[KyoHUD] ERREUR menu principal: " .. tostring(main_err))
        return
    end

    -- 3b. Créer le menu Buffs et les sous-menus par CLONAGE du noeud principal
    local buffs_node
    local buffs_ok, buffs_err = pcall(function()
        buffs_node = deep_clone(nodes[MENU_ID])
        buffs_node:clean_items()
        nodes[BUFFS_MENU_ID] = buffs_node
    end)

    if not buffs_ok then
        log("[KyoHUD] ERREUR clone menu Buffs: " .. tostring(buffs_err))
        return
    end

    local sub_count = 0
    for _, cat_id in ipairs(CAT_ORDER) do
        local menu_item = CAT_MENU_ITEMS[cat_id]
        local sub_id = menu_item.next_menu

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
            -- Ajouter le lien vers la catégorie dans le menu Buffs
            add_menu_link_to_node(
                buffs_node,
                menu_item.id,
                menu_item.title,
                menu_item.description,
                sub_id
            )
            sub_count = sub_count + 1
        else
            log("[KyoHUD] ERREUR clone sous-menu " .. cat_id .. ": " .. tostring(clone_err))
        end
    end

    -- 3c. Lier au menu BLT Options
    local parent_id = MAIN_MENU_DEFINITION.parent_menu_id or "blt_options"
    if nodes[parent_id] then
        MenuHelper:AddMenuItem(
            nodes[parent_id],
            MENU_ID,
            MAIN_MENU_DEFINITION.title,
            MAIN_MENU_DEFINITION.description
        )
    else
        log("[KyoHUD] ERREUR menu parent introuvable: " .. tostring(parent_id))
    end

    log("[KyoHUD] Menu JSON construit: principal + Buffs + " .. sub_count .. "/" .. #CAT_ORDER .. " catégories (deep_clone).")
end)
