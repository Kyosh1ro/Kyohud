-- ky_civilian_killfeed.lua — Ajout des civils au killfeed avec pénalité
-- KyoHUD

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud
local MY_MOD_PATH = ModPath

local score_ok, score_err = pcall(dofile, MY_MOD_PATH .. "lua/ky_killfeed.lua")
if not score_ok then
    log("[KyoHUD] Erreur chargement du calcul des scores civils : " .. tostring(score_err))
end

Hooks:PostHook(CivilianDamage, "_on_damage_received", "KH_OnCivilianDamageReceived", function(self, attack_data)
    local result = attack_data and attack_data.result
    if not result or result.type ~= "death" then return end
    if not KH.IsLocalKillAttacker or not KH:IsLocalKillAttacker(attack_data.attacker_unit) then return end

    local unit = self._unit
    local unit_id = KH.GetKillUnitId and KH:GetKillUnitId(unit)
    local civilian_name = KH.GetKillDisplayName
        and KH:GetKillDisplayName(unit_id, true)
        or "Civilian"

    if KH.RecordScoredKill then
        KH:RecordScoredKill(unit, unit_id, civilian_name, true)
    end
end)
