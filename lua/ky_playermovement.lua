-- ky_playermovement.lua — Cloaker kick attacker for Vengeance

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud

KH._revenge_targets = KH._revenge_targets
    or setmetatable({}, { __mode = "k" })

-- `PlayerMovement:on_SPOOCed(enemy_unit)` is the only verified path carrying the Cloaker unit. Checking the state after the original call excludes countered kicks and kicks ignored or blocked by invulnerability.
Hooks:PostHook(PlayerMovement, "on_SPOOCed", "KH_RevengeRememberSpooc", function(movement, enemy_unit)
    local ok, state = pcall(function() return movement:current_state_name() end)
    if not ok or state ~= "incapacitated" or not enemy_unit then return end

    local alive_ok, is_alive = pcall(alive, enemy_unit)
    if alive_ok and is_alive then
        KH._revenge_targets[enemy_unit] = true
    end
end)
