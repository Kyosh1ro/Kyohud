-- ky_playermovement.lua — Attaquant du kick Cloaker pour Vengeance

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud

KH._revenge_targets = KH._revenge_targets
    or setmetatable({}, { __mode = "k" })

-- `PlayerMovement:on_SPOOCed(enemy_unit)` est l'unique chemin vérifié qui porte
-- l'unité du Cloaker. Contrôler l'état après l'appel original exclut les kicks
-- contrés, ignorés ou bloqués par l'invulnérabilité.
Hooks:PostHook(PlayerMovement, "on_SPOOCed", "KH_RevengeRememberSpooc", function(movement, enemy_unit)
    local ok, state = pcall(function() return movement:current_state_name() end)
    if not ok or state ~= "incapacitated" or not enemy_unit then return end

    local alive_ok, is_alive = pcall(alive, enemy_unit)
    if alive_ok and is_alive then
        KH._revenge_targets[enemy_unit] = true
    end
end)
