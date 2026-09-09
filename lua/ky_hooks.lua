-- ky_hooks.lua — Hooks on PlayerManager to detect buffs and kills
if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud
local MY_MOD_PATH = ModPath

local catalog_ok, catalog_err = pcall(dofile, MY_MOD_PATH .. "lua/ky_buff_catalog.lua")
if not catalog_ok then
    pcall(function()
        log("[KyoHUD][Hooks] Buff catalog load error: " .. tostring(catalog_err))
    end)
end

local function HLOG(msg)
    pcall(function() log("[KyoHUD][Hooks] " .. tostring(msg)) end)
end

local DEFAULT_TEMPORARY_BUFF_DURATION = 5

KH._unknown_temp_upgrades = KH._unknown_temp_upgrades or {}

-- ═══════════════════════════════════════════════════
-- Retrieve duration of a temporary upgrade
-- ═══════════════════════════════════════════════════
local function get_temp_duration(pm, upgrade)
    -- Method 1: read expire_time written by activate_temporary_upgrade
    -- (we are in PostHook, the entry already exists) → exact remaining time
    local ok1, remaining = pcall(function()
        local entry = pm._temporary_upgrades
            and pm._temporary_upgrades.temporary
            and pm._temporary_upgrades.temporary[upgrade]
        if entry and entry.expire_time then
            -- PlayerManager writes this expiration with Application:time().
            -- Only the resulting duration is then converted to a HUD timer.
            return entry.expire_time - Application:time()
        end
        return nil
    end)
    if ok1 and remaining and remaining > 0 then
        return remaining
    end

    -- Method 2: upgrade_value returns an array { value, duration }
    local ok2, v2 = pcall(function()
        return pm:upgrade_value("temporary", upgrade, nil)
    end)
    if ok2 and type(v2) == "table" and tonumber(v2[2]) then
        return tonumber(v2[2])
    end

    -- Method 3: internal fallback duration
    return DEFAULT_TEMPORARY_BUFF_DURATION
end

local function get_temp_value(pm, category, upgrade)
    local ok1, value = pcall(function()
        if pm.temporary_upgrade_value then
            return pm:temporary_upgrade_value(category, upgrade, nil)
        end
    end)
    if ok1 and tonumber(value) then return tonumber(value) end

    -- Fallback for versions where upgrade_value exposes directly the
    -- { value, duration } definition of the temporary upgrade.
    local ok2, definition = pcall(function()
        return pm:upgrade_value(category, upgrade, nil)
    end)
    if ok2 and type(definition) == "table" then
        return tonumber(definition[1])
    end
    return ok2 and tonumber(definition) or nil
end

-- ═══════════════════════════════════════════════════
-- Hook: Temporary buff activation
-- ═══════════════════════════════════════════════════
local function on_temporary_upgrade_activated(pm, category, upgrade)
    if category ~= "temporary" or not upgrade then return end
    if KH._gameinfo_bridge_active then return end

    local targets = KH.GetBuffTargets and KH.GetBuffTargets(upgrade) or {}
    if #targets == 0 then
        if not KH._unknown_temp_upgrades[upgrade] then
            KH._unknown_temp_upgrades[upgrade] = true
            HLOG("Uncatalogued temporary buff (ignored once): " .. tostring(upgrade))
        end
        return
    end

    local dur = get_temp_duration(pm, upgrade)
    local value = get_temp_value(pm, category, upgrade)
    if KH.handle_buff_event then
        KH:handle_buff_event("activate", upgrade, { duration = dur, value = value }, "temporary")
    elseif KH.add_buff then
        for _, buff_id in ipairs(targets) do
            KH:add_buff(buff_id, nil, dur)
        end
    end
end

Hooks:PostHook(PlayerManager, "activate_temporary_upgrade", "KH_OnBuffOn", function(pm, category, upgrade)
    on_temporary_upgrade_activated(pm, category, upgrade)
end)

if PlayerManager.activate_temporary_upgrade_by_level then
    Hooks:PostHook(PlayerManager, "activate_temporary_upgrade_by_level", "KH_OnBuffOnByLevel", function(pm, category, upgrade)
        on_temporary_upgrade_activated(pm, category, upgrade)
    end)
end

if PlayerManager.disable_cooldown_upgrade then
    Hooks:PostHook(PlayerManager, "disable_cooldown_upgrade", "KH_OnCooldownStarted", function(pm, category, upgrade)
        if not upgrade or KH._gameinfo_bridge_active then return end
        local targets = KH.GetBuffTargets and KH.GetBuffTargets(upgrade) or {}
        if #targets == 0 then return end

        local duration
        pcall(function()
            local entry = pm._global
                and pm._global.cooldown_upgrades
                and pm._global.cooldown_upgrades[category]
                and pm._global.cooldown_upgrades[category][upgrade]
            if entry and entry.cooldown_time then
                duration = entry.cooldown_time - Application:time()
            end
        end)
        duration = tonumber(duration) or DEFAULT_TEMPORARY_BUFF_DURATION

        if KH.handle_buff_event then
            KH:handle_buff_event("activate", upgrade, { duration = duration }, "cooldown")
        elseif KH.add_buff then
            for _, buff_id in ipairs(targets) do
                KH:add_buff(buff_id, nil, duration)
            end
        end
    end)
end

-- ═══════════════════════════════════════════════════
-- Hook: Deactivation of temporary buff
-- ═══════════════════════════════════════════════════
Hooks:PostHook(PlayerManager, "deactivate_temporary_upgrade", "KH_OnBuffOff", function(pm, category, upgrade)
    if category ~= "temporary" or not upgrade then return end
    if KH._gameinfo_bridge_active then return end

    if KH.handle_buff_event then
        KH:handle_buff_event("deactivate", upgrade, nil, "temporary")
    elseif KH.remove_buff then
        local targets = KH.GetBuffTargets and KH.GetBuffTargets(upgrade) or {}
        for _, buff_id in ipairs(targets) do
            KH:remove_buff(buff_id)
        end
    end
end)

if PlayerManager.update_hostage_situation then
    Hooks:PostHook(PlayerManager, "update_hostage_situation", "KH_RefreshHostageRegen", function()
        if KH.RefreshPassiveHealthRegen then
            KH:RefreshPassiveHealthRegen()
        end
    end)
end

-- The killfeed (hook CopDamage:die) lives in ky_killfeed.lua, hooked to
-- lib/units/enemies/cop/copdamage: CopDamage does not exist here yet.
