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
Hooks:PostHook(PlayerManager, "activate_temporary_upgrade", "KH_OnBuffOn", function(pm, category, upgrade)
    if category ~= "temporary" or not upgrade then return end

    -- Résoudre le buff_id via la table de mapping
    local buff_id = upgrade
    if KH.UPGRADE_TO_BUFF and KH.UPGRADE_TO_BUFF[upgrade] then
        buff_id = KH.UPGRADE_TO_BUFF[upgrade]
    end

    -- Vérifier que ce buff existe dans BUFF_MAP
    local map_entry = KH.BUFF_MAP and KH.BUFF_MAP[buff_id]
    if not map_entry then
        HLOG(string.format("BUFF ON ignoré (pas dans BUFF_MAP): %s → %s", tostring(upgrade), tostring(buff_id)))
        return
    end

    local dur = get_temp_duration(pm, upgrade)

    if KH.add_buff then
        KH:add_buff(buff_id, nil, dur, upgrade)
    end

    HLOG(string.format("BUFF ON: %s → %s (dur=%.1fs)", tostring(upgrade), tostring(buff_id), dur))
end)

-- ═══════════════════════════════════════════════════
-- Hook : Désactivation de buff temporaire
-- ═══════════════════════════════════════════════════
Hooks:PostHook(PlayerManager, "deactivate_temporary_upgrade", "KH_OnBuffOff", function(pm, category, upgrade)
    if category ~= "temporary" or not upgrade then return end

    -- Résoudre le buff_id via la table de mapping
    local buff_id = upgrade
    if KH.UPGRADE_TO_BUFF and KH.UPGRADE_TO_BUFF[upgrade] then
        buff_id = KH.UPGRADE_TO_BUFF[upgrade]
    end

    if KH.remove_buff then
        KH:remove_buff(buff_id)
    end

    HLOG(string.format("BUFF OFF: %s → %s", tostring(upgrade), tostring(buff_id)))
end)

-- Le killfeed (hook CopDamage:die) vit dans ky_killfeed.lua, accroché à
-- lib/units/enemies/cop/copdamage : CopDamage n'existe pas encore ici.

HLOG("ky_hooks.lua chargé — hooks buffs actifs.")
