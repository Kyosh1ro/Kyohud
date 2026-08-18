-- ky_killfeed.lua — Hook sur CopDamage pour détecter les kills
-- Kyosh1ro HUD
-- Ce fichier DOIT être accroché à lib/units/enemies/cop/copdamage (mod.txt) :
-- au moment où lib/managers/playermanager se charge, CopDamage n'existe pas encore.

if not Kyosh1roHUD then Kyosh1roHUD = {} end
local KH = Kyosh1roHUD
local MY_MOD_PATH = ModPath

local score_ok, score_err = pcall(dofile, MY_MOD_PATH .. "ky_killscore.lua")
if not score_ok then
    log("[Kyosh1ro HUD] Erreur chargement du calcul des scores : " .. tostring(score_err))
end

local function HLOG(msg)
    pcall(function() log("[Kyosh1ro HUD][KillFeed] " .. tostring(msg)) end)
end

Hooks:PostHook(CopDamage, "die", "KH_OnEnemyDie", function(self, attack_data)
    if not attack_data then return end

    local attacker = attack_data.attacker_unit
    if not KH.IsLocalKillAttacker or not KH:IsLocalKillAttacker(attacker) then return end

    local unit = self._unit
    local unit_id = KH.GetKillUnitId and KH:GetKillUnitId(unit)
    local civilian_ok, is_civilian = pcall(function()
        return unit_id and CopDamage.is_civilian(unit_id) or false
    end)
    is_civilian = civilian_ok and is_civilian == true
    local enemy_name = KH.GetKillDisplayName
        and KH:GetKillDisplayName(unit_id, is_civilian)
        or "Enemy"

    if KH.RecordScoredKill then
        KH:RecordScoredKill(unit, unit_id, enemy_name, is_civilian)
    elseif KH.add_kill then
        KH:add_kill(enemy_name)
    end
end)

HLOG("Hook CopDamage:die() installé pour le killfeed.")
