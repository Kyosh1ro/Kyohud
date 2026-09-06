-- ky_playerinventory.lua — Horodatage des changements d'arme locaux
if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud

-- Une première sélection correspond à l'équipement initial au spawn et ne doit
-- pas ouvrir la fenêtre Hot Swap. Les clés faibles évitent de retenir les
-- inventaires détruits lors d'un changement de niveau.
local equipped_selections = setmetatable({}, { __mode = "k" })

if RequiredScript == "lib/units/beings/player/playerinventory"
        and PlayerInventory and PlayerInventory.equip_selection then
    Hooks:PostHook(PlayerInventory, "equip_selection", "KH_OnWeaponSwap", function(inventory, selection_index)
        local ok, equipped = pcall(function()
            return inventory and inventory._equipped_selection
        end)
        if not ok or not equipped or equipped ~= selection_index then return end

        local previous = equipped_selections[inventory]
        equipped_selections[inventory] = equipped
        if previous == nil or previous == equipped then return end

        local time_ok, t = pcall(function()
            return TimerManager:game():time()
        end)
        if time_ok and tonumber(t) then
            KH._last_weapon_switch_t = tonumber(t)
        end
    end)
end
