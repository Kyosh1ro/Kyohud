-- ky_killfeed.lua — Détection des kills locaux côté hôte et client
-- KyoHUD
-- Ce fichier est chargé dans les contextes PlayerManager et CopDamage (mod.txt).
-- CopDamage:die reste le chemin hôte historique ; PlayerManager:on_killshot
-- fournit au client rejoignant une partie sa notification locale de kill.

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud
local MY_MOD_PATH = ModPath

local score_ok, score_err = pcall(dofile, MY_MOD_PATH .. "ky_killscore.lua")
if not score_ok then
    log("[KyoHUD] Erreur chargement du calcul des scores : " .. tostring(score_err))
end

local function HLOG(msg)
    pcall(function() log("[KyoHUD][KillFeed] " .. tostring(msg)) end)
end

local function record_kill(unit, is_civilian)
    local unit_id = KH.GetKillUnitId and KH:GetKillUnitId(unit)
    local enemy_name = KH.GetKillDisplayName
        and KH:GetKillDisplayName(unit_id, is_civilian)
        or "Enemy"

    if KH.RecordScoredKill then
        KH:RecordScoredKill(unit, unit_id, enemy_name, is_civilian)
    elseif KH.add_kill then
        KH:add_kill(enemy_name)
    end
end

if RequiredScript == "lib/managers/playermanager" then
    Hooks:PostHook(PlayerManager, "on_killshot", "KH_OnLocalPlayerKillshot", function(self, killed_unit)
        if not Network:is_client() then return end

        local unit_id = KH.GetKillUnitId and KH:GetKillUnitId(killed_unit)
        local civilian_ok, is_civilian = pcall(function()
            return unit_id and CopDamage.is_civilian(unit_id) or false
        end)

        record_kill(killed_unit, civilian_ok and is_civilian == true)
    end)

    HLOG("Hook PlayerManager:on_killshot() installé pour le killfeed client.")
    return
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
    record_kill(unit, is_civilian)
end)

HLOG("Hook CopDamage:die() installé pour le killfeed.")
