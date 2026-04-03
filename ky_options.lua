-- ky_options.lua — Menu BLT + sauvegarde/chargement des paramètres
-- Kyosh1ro HUD v1.1.0

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
    angle_start   = 315,
    angle_end     = 90,
    buff_duration = 5,
    opacity       = 0.9,
    icon_size     = 32,
}

-- Catégories par défaut (toutes activées)
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

-- Génère les toggles individuels par défaut depuis BUFF_MAP
local function build_default_buff_toggles()
    local t = {}
    if KH.BUFF_MAP then
        for buff_id, def in pairs(KH.BUFF_MAP) do
            t[buff_id] = (def.default_show ~= false)
        end
    end
    return t
end

-- Initialise les settings à partir des defaults si pas encore fait
if not KH.settings then
    KH.settings = {}
    for k, v in pairs(KH._defaults) do
        KH.settings[k] = v
    end
end

-- Initialise buff_categories
if not KH.settings.buff_categories then
    KH.settings.buff_categories = {}
    for k, v in pairs(KH._default_categories) do
        KH.settings.buff_categories[k] = v
    end
end

-- Initialise buff_toggles (sera complété après le chargement de BUFF_MAP)
if not KH.settings.buff_toggles then
    KH.settings.buff_toggles = build_default_buff_toggles()
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
            -- Charger les settings simples
            for k, default_v in pairs(KH._defaults) do
                if data[k] ~= nil then
                    KH.settings[k] = data[k]
                else
                    KH.settings[k] = default_v
                end
            end

            -- Charger buff_categories
            if type(data.buff_categories) == "table" then
                for k, v in pairs(KH._default_categories) do
                    if data.buff_categories[k] ~= nil then
                        KH.settings.buff_categories[k] = data.buff_categories[k]
                    else
                        KH.settings.buff_categories[k] = v
                    end
                end
            end

            -- Charger buff_toggles
            if type(data.buff_toggles) == "table" then
                KH.settings.buff_toggles = data.buff_toggles
                -- Ajouter les nouveaux buffs qui n'existent pas encore dans la sauvegarde
                local defaults = build_default_buff_toggles()
                for buff_id, default_val in pairs(defaults) do
                    if KH.settings.buff_toggles[buff_id] == nil then
                        KH.settings.buff_toggles[buff_id] = default_val
                    end
                end
            else
                KH.settings.buff_toggles = build_default_buff_toggles()
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
    for k, v in pairs(KH._default_categories) do
        KH.settings.buff_categories[k] = v
    end
    KH.settings.buff_toggles = build_default_buff_toggles()
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

-- ── Callbacks dynamiques pour catégories ──
-- Crée un callback par catégorie : KY_ToggleCat_mastermind, KY_ToggleCat_enforcer, etc.
local CAT_ORDER = {
    "mastermind", "enforcer", "technician", "ghost", "fugitive",
    "perk", "debuff", "team", "player_action", "gage", "ai",
}

for _, cat_id in ipairs(CAT_ORDER) do
    local cb_name = "KY_ToggleCat_" .. cat_id
    MenuCallbackHandler[cb_name] = function(self, item)
        KH.settings.buff_categories[cat_id] = (item:value() == "on")
        KH.Save()
        if KH.RefreshHUD then KH:RefreshHUD() end
    end
end

-- ── Callbacks dynamiques pour buffs individuels ──
-- Crée un callback par buff : KY_ToggleBuff_inspire, KY_ToggleBuff_overkill, etc.
local function register_buff_callbacks()
    if not KH.BUFF_MAP then return end
    for buff_id, _ in pairs(KH.BUFF_MAP) do
        local cb_name = "KY_ToggleBuff_" .. buff_id
        local bid = buff_id -- capture locale
        MenuCallbackHandler[cb_name] = function(self, item)
            KH.settings.buff_toggles[bid] = (item:value() == "on")
            KH.Save()
            if KH.RefreshHUD then KH:RefreshHUD() end
        end
    end
end
register_buff_callbacks()

-- ═══════════════════════════════════════════════════
-- 3) Construction du menu BLT
-- ═══════════════════════════════════════════════════
Hooks:Add("MenuManagerBuildCustomMenus", "KY_BuildMenu", function(menu_manager, nodes)
    local MENU_ID = "ky_hud_options"
    local MENU_CATS = "ky_hud_buff_categories"
    local MENU_BUFFS_PREFIX = "ky_hud_buffs_"

    MenuHelper:NewMenu(MENU_ID)
    MenuHelper:NewMenu(MENU_CATS)

    -- ══════════════════════════════════════════════
    -- Menu principal
    -- ══════════════════════════════════════════════

    -- ── Toggles principaux ──
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

    -- ══════════════════════════════════════════════
    -- Sous-menu : Catégories de buffs
    -- ══════════════════════════════════════════════
    local cat_prio = 100
    for _, cat_id in ipairs(CAT_ORDER) do
        local cat_name = (KH.BUFF_CATEGORIES and KH.BUFF_CATEGORIES[cat_id]) or cat_id

        -- Toggle de la catégorie
        MenuHelper:AddToggle({
            id       = "ky_cat_" .. cat_id,
            title    = "ky_opt_cat_" .. cat_id,
            desc     = "ky_opt_cat_" .. cat_id .. "_desc",
            callback = "KY_ToggleCat_" .. cat_id,
            value    = KH.settings.buff_categories[cat_id] ~= false,
            menu_id  = MENU_CATS,
            priority = cat_prio,
        })

        -- Sous-sous-menu pour les buffs individuels de cette catégorie
        local sub_menu_id = MENU_BUFFS_PREFIX .. cat_id
        MenuHelper:NewMenu(sub_menu_id)

        local buff_prio = 100
        if KH.BUFF_MAP then
            -- Trier les buffs par nom pour un menu lisible
            local sorted_buffs = {}
            for buff_id, def in pairs(KH.BUFF_MAP) do
                if def.category == cat_id then
                    table.insert(sorted_buffs, buff_id)
                end
            end
            table.sort(sorted_buffs)

            for _, buff_id in ipairs(sorted_buffs) do
                local toggle_val = true
                if KH.settings.buff_toggles and KH.settings.buff_toggles[buff_id] ~= nil then
                    toggle_val = KH.settings.buff_toggles[buff_id]
                elseif KH.BUFF_MAP[buff_id] then
                    toggle_val = KH.BUFF_MAP[buff_id].default_show ~= false
                end

                MenuHelper:AddToggle({
                    id       = "ky_buff_" .. buff_id,
                    title    = "ky_opt_buff_" .. buff_id,
                    desc     = "ky_opt_buff_" .. buff_id .. "_desc",
                    callback = "KY_ToggleBuff_" .. buff_id,
                    value    = toggle_val,
                    menu_id  = sub_menu_id,
                    priority = buff_prio,
                })
                buff_prio = buff_prio - 1
            end
        end

        -- Construire le sous-sous-menu et l'ajouter à la catégorie
        nodes[sub_menu_id] = MenuHelper:BuildMenu(sub_menu_id)
        MenuHelper:AddMenuItem(
            nodes[MENU_CATS] or MenuHelper:BuildMenu(MENU_CATS),
            sub_menu_id,
            "ky_opt_cat_" .. cat_id .. "_buffs",
            "ky_opt_cat_" .. cat_id .. "_buffs_desc"
        )

        cat_prio = cat_prio - 1
    end

    -- Construire le menu catégories
    nodes[MENU_CATS] = nodes[MENU_CATS] or MenuHelper:BuildMenu(MENU_CATS)

    -- Lien vers le sous-menu catégories depuis le menu principal
    MenuHelper:AddMenuItem(nodes[MENU_ID] or MenuHelper:BuildMenu(MENU_ID),
        MENU_CATS, "ky_opt_buff_filter", "ky_opt_buff_filter_desc", 80)

    -- Construire et enregistrer le menu principal
    nodes[MENU_ID] = MenuHelper:BuildMenu(MENU_ID)
    MenuHelper:AddMenuItem(nodes.blt_options, MENU_ID, "ky_menu_title", "ky_menu_desc")

    log("[Kyosh1ro HUD] Menu BLT construit avec " .. tostring(#CAT_ORDER) .. " catégories.")
end)
