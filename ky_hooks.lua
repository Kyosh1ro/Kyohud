-- ky_hooks.lua — Hooks sur PlayerManager pour détecter les buffs et les kills
-- Kyosh1ro HUD v1.1.0

if not Kyosh1roHUD then Kyosh1roHUD = {} end
local KH = Kyosh1roHUD
local MY_MOD_PATH = ModPath

local catalog_ok, catalog_err = pcall(dofile, MY_MOD_PATH .. "ky_buff_catalog.lua")
if not catalog_ok then
    pcall(function()
        log("[Kyosh1ro HUD][Hooks] Erreur chargement catalogue buffs: " .. tostring(catalog_err))
    end)
end

local function HLOG(msg)
    pcall(function() log("[Kyosh1ro HUD][Hooks] " .. tostring(msg)) end)
end

KH._unknown_temp_upgrades = KH._unknown_temp_upgrades or {}

-- ═══════════════════════════════════════════════════
-- Récupération de la durée d'un upgrade temporaire
-- ═══════════════════════════════════════════════════
local function get_temp_duration(pm, upgrade)
    -- Méthode 1 : lire l'expire_time écrit par activate_temporary_upgrade
    -- (on est en PostHook, l'entrée existe déjà) → temps restant exact
    local ok1, remaining = pcall(function()
        local entry = pm._temporary_upgrades
            and pm._temporary_upgrades.temporary
            and pm._temporary_upgrades.temporary[upgrade]
        if entry and entry.expire_time then
            return entry.expire_time - TimerManager:game():time()
        end
        return nil
    end)
    if ok1 and remaining and remaining > 0 then
        return remaining
    end

    -- Méthode 2 : upgrade_value retourne un tableau { valeur, durée }
    local ok2, v2 = pcall(function()
        return pm:upgrade_value("temporary", upgrade, nil)
    end)
    if ok2 and type(v2) == "table" and tonumber(v2[2]) then
        return tonumber(v2[2])
    end

    -- Méthode 3 : durée par défaut des settings
    return (KH.settings and KH.settings.buff_duration) or 5
end

-- ═══════════════════════════════════════════════════
-- Hook : Activation de buff temporaire
-- ═══════════════════════════════════════════════════
local function on_temporary_upgrade_activated(pm, category, upgrade)
    if category ~= "temporary" or not upgrade then return end
    if KH._gameinfo_bridge_active then return end

    local targets = KH.GetBuffTargets and KH.GetBuffTargets(upgrade) or {}
    if #targets == 0 then
        if not KH._unknown_temp_upgrades[upgrade] then
            KH._unknown_temp_upgrades[upgrade] = true
            HLOG("Buff temporaire non catalogué (ignoré une seule fois): " .. tostring(upgrade))
        end
        return
    end

    local dur = get_temp_duration(pm, upgrade)
    if KH.handle_buff_event then
        KH:handle_buff_event("activate", upgrade, { duration = dur }, "temporary")
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
        duration = tonumber(duration) or ((KH.settings and KH.settings.buff_duration) or 5)

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
-- Hook : Désactivation de buff temporaire
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

-- Le killfeed (hook CopDamage:die) vit dans ky_killfeed.lua, accroché à
-- lib/units/enemies/cop/copdamage : CopDamage n'existe pas encore ici.

HLOG("ky_hooks.lua chargé — hooks buffs actifs.")
