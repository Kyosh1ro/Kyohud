-- ky_options.lua — BLT Menu + settings save/load
-- Fixed JSON structure with a single MenuHelper:BuildMenu call.

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud
local MY_MOD_PATH = ModPath
local KILLFEED_OFFSET_MIN = 128
local KILLFEED_OFFSET_MAX = 291
local best_streak_menu_item = nil
local buff_position_menu_items = {}
local update_buff_position_menu_enabled

local function update_best_streak_menu_enabled()
    if best_streak_menu_item and best_streak_menu_item.set_enabled then
        best_streak_menu_item:set_enabled(KH.settings.show_total_score ~= false)
    end
end

-- ═══════════════════════════════════════════════════
-- 1) Default settings & persistence
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
    score_position_x = 100,
    score_position_y = 75,
    show_total_score = true,
    show_best_streak = true,
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
            -- VanillaHUD+ centers its list at H - 125 px on its 1280 x 720 panel.
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

if not KH.settings then
    KH.settings = {}
    for k, v in pairs(KH._defaults) do KH.settings[k] = v end
end
KH.settings.buff_categories = nil
KH.settings.buff_toggles = nil

function KH.Save()
    local encoded_ok, encoded = pcall(json.encode, KH.settings)
    if not encoded_ok or type(encoded) ~= "string" then return false end

    local temp_path = KH._settings_path .. ".tmp"
    local f = io.open(temp_path, "w")
    if not f then return false end

    local write_ok, write_result = pcall(f.write, f, encoded)
    local close_ok, close_result = pcall(f.close, f)
    if not write_ok or not write_result or not close_ok or not close_result then
        os.remove(temp_path)
        return false
    end

    -- os.rename replaces atomically where supported. On Windows, preserve the
    -- current save through a backup while replacing an existing destination.
    if os.rename(temp_path, KH._settings_path) then return true end

    local backup_path = KH._settings_path .. ".bak"
    os.remove(backup_path)
    if not os.rename(KH._settings_path, backup_path) then
        os.remove(temp_path)
        return false
    end
    if not os.rename(temp_path, KH._settings_path) then
        os.rename(backup_path, KH._settings_path)
        os.remove(temp_path)
        return false
    end

    os.remove(backup_path)
    return true
end

function KH.Load()
    local f = io.open(KH._settings_path, "r")
    local loaded_legacy_settings = false
    if not f then
        local backup_path = KH._settings_path .. ".bak"
        os.rename(backup_path, KH._settings_path)
        f = io.open(KH._settings_path, "r") or io.open(backup_path, "r")
    end
    if not f then
        f = io.open(KH._legacy_settings_path, "r")
        loaded_legacy_settings = f ~= nil
    end
    if f then
        local raw = f:read("*all"); f:close()
        local ok, data = pcall(json.decode, raw)
        if ok and type(data) == "table" then
            -- NO `x and y or z` here: it returns the default when the saved value is `false`
            for k, dv in pairs(KH._defaults) do
                if data[k] ~= nil then
                    KH.settings[k] = data[k]
                else
                    KH.settings[k] = dv
                end
            end

            -- The old range 100-500 was visually bounded to 70-160 px.
            -- 128-291 covers the same useful area without retaining an inert portion.
            local saved_radius = KH.settings.circle_radius
            local normalized_radius = math.max(
                KILLFEED_OFFSET_MIN,
                math.min(
                    KILLFEED_OFFSET_MAX,
                    math.floor(tonumber(saved_radius) or KH._defaults.circle_radius)
                )
            )
            KH.settings.circle_radius = normalized_radius
            -- Rewrite old saved settings to remove obsolete buff filters and
            -- `buff_duration`, and normalize the old vertical offset range.
            if loaded_legacy_settings or data.buff_duration ~= nil
                    or data.buff_categories ~= nil or data.buff_toggles ~= nil
                    or saved_radius ~= normalized_radius then
                KH.Save()
            end
        end
    end
end
KH.Load()

function KH.ResetDefaults()
    for k, v in pairs(KH._defaults) do KH.settings[k] = v end
    KH.settings.buff_categories = nil
    KH.settings.buff_toggles = nil
    KH.Save()
    update_best_streak_menu_enabled()
    if update_buff_position_menu_enabled then update_buff_position_menu_enabled() end
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
MenuCallbackHandler.KY_ToggleTotalScore = function(self, item)
    KH.settings.show_total_score = (item:value() == "on")
    update_best_streak_menu_enabled()
    KH.Save(); if KH.RefreshHUD then KH:RefreshHUD() end
end
MenuCallbackHandler.KY_ToggleBestStreak = make_toggle_cb("show_best_streak")
MenuCallbackHandler.KY_SetLanguage = function(self, item)
    local value = math.floor(tonumber(item:value()) or KH._defaults.language)
    KH.settings.language = math.max(1, math.min(3, value))
    KH.Save()
end
MenuCallbackHandler.KY_SetKillfeedSize = function(self, item)
    local value = math.floor(tonumber(item:value()) or KH._defaults.killfeed_size)
    KH.settings.killfeed_size = math.max(1, math.min(5, value))

    if type(KH._kills) == "table" then
        while #KH._kills > KH.settings.killfeed_size do
            table.remove(KH._kills, 1)
        end
    end

    KH.Save(); if KH.RefreshHUD then KH:RefreshHUD() end
end
MenuCallbackHandler.KY_ToggleBuffs = function(self, item)
    KH.settings.enable_buffs = (item:value() == "on")
    if update_buff_position_menu_enabled then update_buff_position_menu_enabled() end
    KH.Save(); if KH.RefreshHUD then KH:RefreshHUD() end
end
MenuCallbackHandler.KY_SetRadius      = make_slider_cb("circle_radius", true)
MenuCallbackHandler.KY_SetBuffPositionX = make_slider_cb("buff_position_x", true)
MenuCallbackHandler.KY_SetBuffPositionY = make_slider_cb("buff_position_y", true)
MenuCallbackHandler.KY_SetScorePositionX = make_slider_cb("score_position_x", true)
MenuCallbackHandler.KY_SetScorePositionY = make_slider_cb("score_position_y", true)
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
        log("[KyoHUD] Unable to open menu definition: " .. tostring(path))
        return nil
    end

    local raw = file:read("*all")
    file:close()

    local ok, content = pcall(json.decode, raw)
    if not ok or type(content) ~= "table" then
        log("[KyoHUD] Invalid menu JSON " .. tostring(path) .. ": " .. tostring(content))
        return nil
    end
    if type(content.menu_id) ~= "string" or type(content.items) ~= "table" then
        log("[KyoHUD] Incomplete menu definition: " .. tostring(path))
        return nil
    end
    return content
end

local function buff_provider_available()
    local gameinfo = managers and managers.gameinfo
    local runtime_available = gameinfo ~= nil
        and type(gameinfo.register_listener) == "function"
        and type(gameinfo.get_buffs) == "function"
        and type(gameinfo.get_player_actions) == "function"
        and HUDList ~= nil
        and HUDList.BuffItemBase ~= nil
        and type(HUDList.BuffItemBase.MAP) == "table"
        and HUDListManager ~= nil
        and type(HUDListManager.BUFFS) == "table"
    if runtime_available then return true end

    -- The main menu can be built before VanillaHUD+ initializes its runtime
    -- globals. SuperBLT's enabled-mod registry is already available there.
    return is_blt_mod_enabled("VanillaHUDPlus")
end

update_buff_position_menu_enabled = function()
    local enabled = KH.settings.enable_buffs ~= false and buff_provider_available()
    for _, item in ipairs(buff_position_menu_items) do
        if item and item.set_enabled then item:set_enabled(enabled) end
    end
end

local MAIN_MENU_DEFINITION = load_menu_definition("menu.json")
local MENU_ID = MAIN_MENU_DEFINITION and MAIN_MENU_DEFINITION.menu_id or "kyohud_options"

-- ═══════════════════════════════════════════════════
-- 3) Menu construction
-- ═══════════════════════════════════════════════════
local function populate_json_menu(definition)
    if not definition then return end

    buff_position_menu_items = {}
    local items = definition.items
    local item_count = #items
    for index, item in ipairs(items) do
        local item_type = item.type
        local priority = item.priority or (item_count - index + 1)
        local value = item.default_value
        local description = item.description
        local provider_unavailable = item.provider_required and not buff_provider_available()
        if provider_unavailable then
            description = item.unavailable_description or description
        end
        if item.value and KH.settings[item.value] ~= nil then
            value = KH.settings[item.value]
        end
        if item_type == "slider" and item.display_multiplier then
            value = value * item.display_multiplier
        end

        if item_type == "multiple_choice" then
            MenuHelper:AddMultipleChoice({
                id = item.id, title = item.title, desc = description,
                callback = item.callback, items = item.items,
                item_values = item.item_values, value = value,
                localized_items = item.localized_items,
                menu_id = definition.menu_id, priority = priority,
            })
        elseif item_type == "toggle" then
            local created_item = MenuHelper:AddToggle({
                id = item.id, title = item.title, desc = description,
                callback = item.callback, value = value,
                disabled = provider_unavailable
                    or (item.enabled_by and KH.settings[item.enabled_by] == false),
                menu_id = definition.menu_id, priority = priority,
            })
            if item.id == "ky_show_best_streak" then
                best_streak_menu_item = created_item
            end
        elseif item_type == "slider" then
            local created_item = MenuHelper:AddSlider({
                id = item.id, title = item.title, desc = description,
                callback = item.callback, value = value,
                min = item.min or 0, max = item.max or 1, step = item.step or 1,
                show_value = item.show_value ~= false,
                display_precision = item.display_precision or 0,
                disabled = provider_unavailable
                    or (item.enabled_by and KH.settings[item.enabled_by] == false),
                menu_id = definition.menu_id, priority = priority,
            })
            if item.enabled_by == "enable_buffs" and created_item then
                table.insert(buff_position_menu_items, created_item)
            end
        elseif item_type == "button" then
            MenuHelper:AddButton({
                id = item.id, title = item.title, desc = description,
                callback = item.callback, next_node = item.next_menu,
                menu_id = definition.menu_id, priority = priority,
            })
        elseif item_type == "divider" then
            MenuHelper:AddDivider({
                id = "ky_divider_" .. tostring(index), size = item.size,
                menu_id = definition.menu_id, priority = priority,
            })
        else
            log("[KyoHUD] Unknown JSON menu element type: " .. tostring(item_type))
        end
    end
    update_best_streak_menu_enabled()
    update_buff_position_menu_enabled()
end

-- ── HOOK 1 : Setup ──
Hooks:Add("MenuManagerSetupCustomMenus", "KY_SetupMenu", function(menu_manager, nodes)
    if not MAIN_MENU_DEFINITION then return end
    MenuHelper:NewMenu(MENU_ID)
end)

-- ── HOOK 2: Populate (main menu items only) ──
Hooks:Add("MenuManagerPopulateCustomMenus", "KY_PopulateMenu", function()
    populate_json_menu(MAIN_MENU_DEFINITION)
end)

-- ── HOOK 3 : Build ──
Hooks:Add("MenuManagerBuildCustomMenus", "KY_BuildMenu", function(menu_manager, nodes)
    if not MAIN_MENU_DEFINITION then return end

    local main_ok, main_err = pcall(function()
        nodes[MENU_ID] = MenuHelper:BuildMenu(MENU_ID, {
            back_callback = MAIN_MENU_DEFINITION.back_callback or "KY_BackCallback",
        })
    end)

    if not main_ok then
        log("[KyoHUD] Main menu error: " .. tostring(main_err))
        return
    end

    local parent_id = MAIN_MENU_DEFINITION.parent_menu_id or "blt_options"
    if nodes[parent_id] then
        MenuHelper:AddMenuItem(
            nodes[parent_id],
            MENU_ID,
            MAIN_MENU_DEFINITION.title,
            MAIN_MENU_DEFINITION.description
        )
    else
        log("[KyoHUD] Parent menu not found: " .. tostring(parent_id))
    end

    log("[KyoHUD] JSON menu built.")
end)
