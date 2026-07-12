-- ky_killfeed.lua — Hook sur CopDamage pour détecter les kills
-- Kyosh1ro HUD
-- Ce fichier DOIT être accroché à lib/units/enemies/cop/copdamage (mod.txt) :
-- au moment où lib/managers/playermanager se charge, CopDamage n'existe pas encore.

if not Kyosh1roHUD then Kyosh1roHUD = {} end
local KH = Kyosh1roHUD

local function HLOG(msg)
    pcall(function() log("[Kyosh1ro HUD][KillFeed] " .. tostring(msg)) end)
end

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
            enemy_name = NAMES[tweak] or tweak:gsub("_", " "):gsub("^%l", string.upper)
        end
    end

    if KH.add_kill then
        KH:add_kill(enemy_name, enemy_type)
    end
end)

HLOG("Hook CopDamage:die() installé pour le killfeed.")
