-- ky_combat_medals.lua — État des médailles lié aux armes
-- Chargé uniquement dans les contextes SuperBLT déclarés dans mod.txt.

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud

local function local_player_unit()
    local ok, unit = pcall(function()
        return managers and managers.player and managers.player:player_unit()
    end)
    if not ok or not unit then return nil end

    local alive_ok, is_alive = pcall(alive, unit)
    return alive_ok and is_alive and unit or nil
end

if RequiredScript == "lib/units/weapons/newraycastweaponbase" then
    -- Seul le rechargement de l'arme du joueur local ouvre un nouveau chargeur.
    -- Les armes des bots et des autres unités ne touchent jamais à cet état.
    Hooks:PostHook(
        NewRaycastWeaponBase,
        "on_reload",
        "KH_ResetSprayDownOnReload",
        function(self)
            local player = local_player_unit()
            if not player then return end

            local ok, is_local_weapon = pcall(function()
                return self._setup and self._setup.user_unit == player
            end)
            if ok and is_local_weapon and KH.ResetSprayDownMagazine then
                KH:ResetSprayDownMagazine()
            end
        end
    )
end
