-- ky_playerinventory.lua — Timestamping of local weapon changes
if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud

-- A first selection corresponds to initial spawn equipment and must not open the Hot Swap window. Weak keys avoid retaining inventories destroyed during a level change.
local equipped_selections = setmetatable({}, { __mode = "k" })

if RequiredScript == "lib/units/beings/player/playerinventory"
        and PlayerInventory and PlayerInventory.equip_selection then
    Hooks:PostHook(PlayerInventory, "equip_selection", "KH_OnWeaponSwap", function(inventory, selection_index)
        local owner_ok, owner, local_player = pcall(function()
            return inventory and inventory._unit,
                managers and managers.player and managers.player:player_unit()
        end)
        if not owner_ok or not owner or owner ~= local_player then return end

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
