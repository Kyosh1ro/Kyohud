-- ky_hooks.lua — Hooks sur PlayerManager pour détecter les buffs et les kills
-- Kyosh1ro HUD v1.0.0

if not Kyosh1roHUD then Kyosh1roHUD = {} end
local KH = Kyosh1roHUD

local function HLOG(msg)
    pcall(function() log("[Kyosh1ro HUD][Hooks] " .. tostring(msg)) end)
end

-- ═══════════════════════════════════════════════════
-- Résolution d'icônes depuis le skilltree
-- ═══════════════════════════════════════════════════
local TILE = 64
local ICON_ATLAS = "guis/textures/pd2/skilltree/icons_atlas"

local function has_texture(path)
    return path and DB and DB:has(Idstring("texture"), Idstring(path))
end

-- Tente de récupérer l'icône depuis le skilltree (plus fiable pour le rect)
local function icon_from_skill(skill_id)
    local skills = tweak_data and tweak_data.skilltree and tweak_data.skilltree.skills
    local s = skills and skills[skill_id]
    if s and s.icon_xy and type(s.icon_xy) == "table" then
        local x, y = s.icon_xy[1], s.icon_xy[2]
        if x and y and has_texture(ICON_ATLAS) then
            return { texture = ICON_ATLAS, rect = { x * TILE, y * TILE, TILE, TILE } }
        end
    end
    return nil
end

-- Tente de récupérer depuis hud_icons
local function icon_from_hud(icon_name)
    if not icon_name then return nil end
    local ok, tx, rect = pcall(function()
        return tweak_data.hud_icons:get_icon_data(icon_name)
    end)
    if ok and tx and has_texture(tx) and rect and type(rect) == "table" and #rect >= 4 then
        return { texture = tx, rect = rect }
    end
    return nil
end

-- ═══════════════════════════════════════════════════
-- Mapping upgrade → skill/icon pour meilleure résolution
-- ═══════════════════════════════════════════════════
local UPGRADE_TO_SKILL = {
    unseen_strike               = "unseen_strike",
    second_wind                 = "second_wind",
    damage_speed_multiplier     = "duck_and_cover",
    movement_speed_multiplier   = "duck_and_cover",
    overkill_damage_multiplier  = "overkill",
    dmg_multiplier_outnumbered  = "underdog",
    bullet_storm                = "bullet_storm",
    iron_man                    = "iron_man",
    inspire                     = "inspire",
    inspire_cooldown            = "inspire",
    ammo_efficiency             = "ammo_efficiency",
    hostage_taker               = "hostage_taker",
    berserker_damage_multiplier = "berserker",
    swan_song                   = "swan_song",
    bloodthirst                 = "bloodthirst",
    armor_break_invulnerable    = "armorer",
    crew_inspire_debuff         = "inspire",
}

local UPGRADE_TO_HUDICON = {
    unseen_strike               = "skill_unseen_strike",
    overkill_damage_multiplier  = "skill_overkill",
    berserker_damage_multiplier = "skill_berserker",
    swan_song                   = "skill_swan_song",
    inspire                     = "skill_inspire",
    bullet_storm                = "skill_bullet_storm",
    hostage_taker               = "skill_hostage_taker",
    iron_man                    = "skill_iron_man",
    second_wind                 = "skill_second_wind",
    bloodthirst                 = "skill_bloodthirst",
}

local FALLBACK_TEX = "guis/textures/pd2/skilltree/drillgui_icon_faster"

local function pick_icon(upgrade_id)
    -- 1) Skilltree (meilleur rect)
    local sk = UPGRADE_TO_SKILL[upgrade_id]
    if sk then
        local ico = icon_from_skill(sk)
        if ico then return ico end
    end
    -- 2) hud_icons
    local hid = UPGRADE_TO_HUDICON[upgrade_id]
    if hid then
        local ico2 = icon_from_hud(hid)
        if ico2 then return ico2 end
    end
    -- 3) Fallback
    return { texture = has_texture(FALLBACK_TEX) and FALLBACK_TEX or "guis/textures/pd2/hud_timer" }
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

    local icon = pick_icon(upgrade)
    local dur = get_temp_duration(pm, upgrade)
    local buff_id = "temp_" .. tostring(upgrade)

    if KH.add_buff then
        KH:add_buff(buff_id, icon, dur, upgrade)
    end

    HLOG(string.format("BUFF ON: %s (dur=%.1fs)", tostring(upgrade), dur))
end)

-- ═══════════════════════════════════════════════════
-- Hook : Désactivation de buff temporaire
-- ═══════════════════════════════════════════════════
Hooks:PostHook(PlayerManager, "deactivate_temporary_upgrade", "KH_OnBuffOff", function(pm, category, upgrade)
    if category ~= "temporary" or not upgrade then return end

    local buff_id = "temp_" .. tostring(upgrade)
    if KH.remove_buff then
        KH:remove_buff(buff_id)
    end

    HLOG(string.format("BUFF OFF: %s", tostring(upgrade)))
end)

-- ═══════════════════════════════════════════════════
-- Hook : Détection des kills (KillFeed)
-- ═══════════════════════════════════════════════════
-- On hook CopDamage:die() pour intercepter les morts d'ennemis
if CopDamage then
    Hooks:PostHook(CopDamage, "die", "KH_OnEnemyDie", function(self, attack_data)
        -- Vérifier que c'est le joueur local qui a tué
        if not attack_data then return end

        local attacker = attack_data.attacker_unit
        if not attacker or not alive(attacker) then return end

        -- Seuls les kills du joueur local comptent
        local local_peer_id = managers.network and managers.network:session()
            and managers.network:session():local_peer()
            and managers.network:session():local_peer():id()

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
            -- Essayer de récupérer le tweak_table (nom interne)
            local ok, tweak = pcall(function()
                return self._unit:base()._tweak_table
            end)
            if ok and tweak then
                enemy_type = tostring(tweak)
                -- Noms plus lisibles
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
