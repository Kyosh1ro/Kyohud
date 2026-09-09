-- ky_playerdamage.lua — Autonomous detection of passive regeneration

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud
local MY_MOD_PATH = ModPath

KH._revenge_targets = KH._revenge_targets
    or setmetatable({}, { __mode = "k" })

local function remember_revenge_target(unit)
    if not unit then return end
    local ok, is_alive = pcall(alive, unit)
    if ok and is_alive then
        KH._revenge_targets[unit] = true
    end
end

local function remember_pending_attacker(player_damage)
    remember_revenge_target(player_damage and player_damage._kh_revenge_attacker)
end

-- Damage that downs the player calls `on_downed` during execution. The candidate is stored before the engine call and removed afterward so non-fatal damage cannot contaminate a later down.
for _, method in ipairs({
    "damage_bullet", "damage_melee", "damage_explosion", "damage_fire",
    "damage_fire_hit", "damage_simple", "damage_killzone",
}) do
    if type(PlayerDamage[method]) == "function" then
        Hooks:PreHook(PlayerDamage, method, "KH_RevengeRemember_" .. method, function(player_damage, attack_data)
            player_damage._kh_revenge_attacker = attack_data and attack_data.attacker_unit
        end)
        Hooks:PostHook(PlayerDamage, method, "KH_RevengeForget_" .. method, function(player_damage)
            player_damage._kh_revenge_attacker = nil
        end)
    end
end

-- `damage_tase` officially retains the attack in `tase_data()`.
if type(PlayerDamage.damage_tase) == "function" then
    Hooks:PostHook(PlayerDamage, "damage_tase", "KH_RevengeRememberTase", function(player_damage)
        local ok, data = pcall(function() return player_damage:tase_data() end)
        if ok then remember_revenge_target(data and data.attacker_unit) end
    end)
end

local catalog_ok, catalog_err = pcall(dofile, MY_MOD_PATH .. "lua/ky_buff_catalog.lua")
if not catalog_ok then
    pcall(function()
        log("[KyoHUD][Regen] Buff catalog load error: " .. tostring(catalog_err))
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

    return count > 0
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
    -- If the API is unavailable, do not display a fake permanent buff.
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

-- Private KyoHUD field carried by the PlayerDamage instance: last health state actually observed by passive regeneration. `nil` until any refresh has occurred, so that the first observation always emits.
local HEALTH_STATE_FIELD = "_kh_passive_regen_injured"

local function refresh_passive_regen(player_damage, injured)
    if KH._gameinfo_bridge_active or not player_damage then return end

    if injured == nil then
        injured = not is_full_health(player_damage)
    end
    -- Any explicit refresh path updates the cached state: a subsequent set_health on the same state will therefore not redo the work.
    player_damage[HEALTH_STATE_FIELD] = injured

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

-- ── Player down: reset weapon streaks ──
-- Medal counters do not survive a player down. Only PlayerDamage events are used, never state accessors: `bleed_out()`, `incapacitated()` and `arrested()` simply return the current state and are queried in a loop, which would trigger a permanent reset. `on_downed`, `on_incapacitated` and `on_arrested` are called once upon entering each state (see annotations of
-- `lib/units/beings/player/playerdamage`).
local PLAYER_DOWN_EVENTS = { "on_downed", "on_incapacitated", "on_arrested" }

local function reset_weapon_streaks(player_damage)
    remember_pending_attacker(player_damage)
    if not KH.ResetWeaponStreaks then return end
    KH:ResetWeaponStreaks()
end

for _, event in ipairs(PLAYER_DOWN_EVENTS) do
    -- Do not wrap anything if the method does not exist in this game version: a PostHook on an absent method would create a ghost function.
    if type(PlayerDamage[event]) == "function" then
        Hooks:PostHook(
            PlayerDamage,
            event,
            "KH_ResetWeaponStreaks_" .. event,
            reset_weapon_streaks
        )
    else
        pcall(function()
            log("[KyoHUD][Streak] PlayerDamage:" .. event .. "() missing, reset not installed.")
        end)
    end
end

-- `set_health` is called in a loop (healing, damage, regeneration). Refresh only when the injured/full state actually changes: passive regeneration indicators depend only on that boolean, and the HUD handles its own countdown. The cycle restart remains covered by
-- `_upd_health_regen`, and hostages by `PlayerManager:update_hostage_situation`.
Hooks:PostHook(PlayerDamage, "set_health", "KH_RefreshPassiveRegenOnHealth", function(player_damage)
    if KH._gameinfo_bridge_active or not player_damage then return end

    local injured = not is_full_health(player_damage)
    if player_damage[HEALTH_STATE_FIELD] == injured then return end

    refresh_passive_regen(player_damage, injured)
end)

Hooks:PreHook(PlayerDamage, "_upd_health_regen", "KH_RememberPassiveRegenTimer", function(player_damage)
    player_damage._kh_previous_health_regen_timer = player_damage._health_regen_update_timer
end)

Hooks:PostHook(PlayerDamage, "_upd_health_regen", "KH_RefreshPassiveRegenTimer", function(player_damage)
    local previous = tonumber(player_damage._kh_previous_health_regen_timer) or 0
    local current = tonumber(player_damage._health_regen_update_timer)
    player_damage._kh_previous_health_regen_timer = nil

    -- The HUD handles its own countdown. Therefore, an update is only necessary upon restarting the healing cycle.
    if current and current > previous then
        refresh_passive_regen(player_damage)
    end
end)
