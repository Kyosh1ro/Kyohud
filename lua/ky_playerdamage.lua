-- ky_playerdamage.lua — Détection autonome de la régénération passive

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud
local MY_MOD_PATH = ModPath

local catalog_ok, catalog_err = pcall(dofile, MY_MOD_PATH .. "lua/ky_buff_catalog.lua")
if not catalog_ok then
    pcall(function()
        log("[KyoHUD][Regen] Erreur chargement catalogue buffs: " .. tostring(catalog_err))
    end)
end

local PASSIVE_REGEN = {
    muscle_regen = { category = "player", upgrade = "passive_health_regen" },
    crew_health_regen = { category = "team", upgrade = "crew_health_regen" },
    hostage_taker = { category = "player", upgrade = "hostage_health_regen_addend", needs_hostage = true },
}

local function has_hostage_or_minion()
    local count = 0

    pcall(function()
        local state = managers.groupai and managers.groupai:state()
        count = count + (state and state:hostage_count() or 0)
    end)
    pcall(function()
        count = count + (managers.player:num_local_minions() or 0)
    end)

    return count > 0 or (managers.player and managers.player._HAS_HOSTAGES == true)
end

local function has_upgrade(category, upgrade)
    local ok, value = pcall(function()
        return managers.player and managers.player:has_category_upgrade(category, upgrade)
    end)
    return ok and value == true
end

local function is_full_health(player_damage)
    local ok, value = pcall(function()
        return player_damage:full_health()
    end)
    -- En cas d'API indisponible, ne pas afficher un faux buff permanent.
    return not ok or value == true
end

local function get_upgrade_value(definition)
    local ok, value = pcall(function()
        return managers.player and managers.player:upgrade_value(
            definition.category,
            definition.upgrade,
            0
        )
    end)
    return ok and tonumber(value) or nil
end

local function emit(event, source_id, duration, value)
    if KH._gameinfo_bridge_active then return end

    if KH.handle_buff_event then
        local data
        if duration ~= nil or value ~= nil then
            data = { duration = duration, value = value }
        end
        KH:handle_buff_event(event, source_id, data, "passive_regen")
        return
    end

    local targets = KH.GetBuffTargets and KH.GetBuffTargets(source_id) or {}
    for _, buff_id in ipairs(targets) do
        if event == "deactivate" then
            if KH.remove_buff then KH:remove_buff(buff_id) end
        elseif KH.add_buff then
            KH:add_buff(buff_id, nil, duration, nil, duration == nil)
        end
    end
end

local function refresh_passive_regen(player_damage)
    if KH._gameinfo_bridge_active or not player_damage then return end

    local injured = not is_full_health(player_damage)
    local duration = tonumber(player_damage._health_regen_update_timer)

    for source_id, definition in pairs(PASSIVE_REGEN) do
        local active = injured and has_upgrade(definition.category, definition.upgrade)
        if active and definition.needs_hostage then
            active = has_hostage_or_minion()
        end

        if active then
            emit("activate", source_id, duration, get_upgrade_value(definition))
        else
            emit("deactivate", source_id)
        end
    end
end

function KH:RefreshPassiveHealthRegen()
    if self._gameinfo_bridge_active then return end

    local ok, player_damage = pcall(function()
        local unit = managers.player and managers.player:player_unit()
        return alive(unit) and unit:character_damage() or nil
    end)
    if ok and player_damage then
        refresh_passive_regen(player_damage)
    end
end

Hooks:PostHook(PlayerDamage, "set_health", "KH_RefreshPassiveRegenOnHealth", function(player_damage)
    refresh_passive_regen(player_damage)
end)

Hooks:PreHook(PlayerDamage, "_upd_health_regen", "KH_RememberPassiveRegenTimer", function(player_damage)
    player_damage._kh_previous_health_regen_timer = player_damage._health_regen_update_timer
end)

Hooks:PostHook(PlayerDamage, "_upd_health_regen", "KH_RefreshPassiveRegenTimer", function(player_damage)
    local previous = tonumber(player_damage._kh_previous_health_regen_timer) or 0
    local current = tonumber(player_damage._health_regen_update_timer)
    player_damage._kh_previous_health_regen_timer = nil

    -- Le HUD fait lui-même le compte à rebours. Une mise à jour n'est donc
    -- nécessaire qu'au redémarrage du cycle de soin.
    if current and current > previous then
        refresh_passive_regen(player_damage)
    end
end)
