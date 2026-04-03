-- ky_hooks.lua — Hooks sur PlayerManager pour détecter les buffs et les kills
-- Kyosh1ro HUD v1.1.0

if not Kyosh1roHUD then Kyosh1roHUD = {} end
local KH = Kyosh1roHUD

local function HLOG(msg)
    pcall(function() log("[Kyosh1ro HUD][Hooks] " .. tostring(msg)) end)
end

-- ═══════════════════════════════════════════════════
-- Récupération de la durée d'un upgrade temporaire
-- ═══════════════════════════════════════════════════
local function get_temp_duration(pm, upgrade)
    local dur = nil

    -- Méthode 1 : upgrade_value
    local ok1, v1 = pcall(function()
        return pm:upgrade_value("temporary", upgrade, nil)
    end)
    if ok1 and type(v1) == "table" and v1.duration then
        dur = tonumber(v1.duration)
    end

    -- Méthode 2 : temporary_upgrade_value
    if not dur then
        local ok2, v2 = pcall(function()
            return pm:temporary_upgrade_value("temporary", upgrade, nil)
        end)
        if ok2 and type(v2) == "table" and v2.duration then
            dur = tonumber(v2.duration)
        end
    end

    -- Méthode 3 : utiliser la durée par défaut des settings
    if not dur and KH.settings then
        dur = KH.settings.buff_duration
    end

    return dur or 6
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

-- ═══════════════════════════════════════════════════
-- Hook : Détection des kills (KillFeed)
-- ═══════════════════════════════════════════════════
if CopDamage then
    Hooks:PostHook(CopDamage, "die", "KH_OnEnemyDie", function(self, attack_data)
        if not attack_data then return end

        local attacker = attack_data.attacker_unit
        if not attacker or not alive(attacker) then return end

        -- Seuls les kills du joueur local comptent
        local is_local = false
        if attacker == managers.player:player_unit() then
            is_local = true
        elseif attacker:base() and attacker:base().thrower_unit
            and attacker:base():thrower_unit() == managers.player:player_unit() then
            is_local = true
        end

        if not is_local then return end

        -- Récupérer le nom/type de l'ennemi
        local enemy_name = "Enemy"
        local enemy_type = "default"

        if self._unit and alive(self._unit) then
            local ok, tweak = pcall(function()
                return self._unit:base()._tweak_table
            end)
            if ok and tweak then
                enemy_type = tostring(tweak)
                local NAMES = {
                    swat_heavy          = "Heavy SWAT",
                    shield              = "Shield",
                    sniper              = "Sniper",
                    taser               = "Taser",
                    cloaker             = "Cloaker",
                    medic               = "Medic",
                    tank                = "Bulldozer",
                    tank_hw             = "Headless Dozer",
                    spooc               = "Cloaker",
                    city_swat           = "GenSec Elite",
                    fbi                 = "FBI",
                    fbi_heavy_swat      = "FBI Heavy",
                    gangster            = "Gangster",
                    cop                 = "Cop",
                    security            = "Guard",
                    swat                = "SWAT",
                    marshal             = "Marshal",
                }
                enemy_name = NAMES[tweak] or tweak:gsub("_", " "):gsub("^%l", string.upper)
            end
        end

        if KH.add_kill then
            KH:add_kill(enemy_name, enemy_type)
        end
    end)

    HLOG("Hook CopDamage:die() installé pour le killfeed.")
end

HLOG("ky_hooks.lua chargé — hooks buffs et kills actifs.")
