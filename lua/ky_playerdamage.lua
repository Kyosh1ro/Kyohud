-- ky_playerdamage.lua — Player damage events for combat medals and streak resets

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud

KH._revenge_targets = KH._revenge_targets
    or setmetatable({}, { __mode = "k" })

local function remember_revenge_target(unit)
    if not unit then return end
    local ok, is_alive = pcall(alive, unit)
    if ok and is_alive then
        KH._revenge_targets[unit] = true
    end
end

local function remember_pending_attacker(player_damage)
    remember_revenge_target(player_damage and player_damage._kh_revenge_attacker)
end

-- Damage that downs the player calls `on_downed` during execution. The candidate is stored before the engine call and removed afterward so non-fatal damage cannot contaminate a later down.
for _, method in ipairs({
    "damage_bullet", "damage_melee", "damage_explosion", "damage_fire",
    "damage_fire_hit", "damage_simple", "damage_killzone",
}) do
    if type(PlayerDamage[method]) == "function" then
        Hooks:PreHook(PlayerDamage, method, "KH_RevengeRemember_" .. method, function(player_damage, attack_data)
            player_damage._kh_revenge_attacker = attack_data and attack_data.attacker_unit
        end)
        Hooks:PostHook(PlayerDamage, method, "KH_RevengeForget_" .. method, function(player_damage)
            player_damage._kh_revenge_attacker = nil
        end)
    end
end

-- `damage_tase` officially retains the attack in `tase_data()`.
if type(PlayerDamage.damage_tase) == "function" then
    Hooks:PostHook(PlayerDamage, "damage_tase", "KH_RevengeRememberTase", function(player_damage)
        local ok, data = pcall(function() return player_damage:tase_data() end)
        if ok then remember_revenge_target(data and data.attacker_unit) end
    end)
end

-- ── Player down: reset weapon streaks ──
-- Medal counters do not survive a player down. Only PlayerDamage events are used, never state accessors: `bleed_out()`, `incapacitated()` and `arrested()` simply return the current state and are queried in a loop, which would trigger a permanent reset. `on_downed`, `on_incapacitated` and `on_arrested` are called once upon entering each state (see annotations of
-- `lib/units/beings/player/playerdamage`).
local PLAYER_DOWN_EVENTS = { "on_downed", "on_incapacitated", "on_arrested" }

local function reset_weapon_streaks(player_damage)
    remember_pending_attacker(player_damage)
    if not KH.ResetWeaponStreaks then return end
    KH:ResetWeaponStreaks()
end

for _, event in ipairs(PLAYER_DOWN_EVENTS) do
    -- Do not wrap anything if the method does not exist in this game version: a PostHook on an absent method would create a ghost function.
    if type(PlayerDamage[event]) == "function" then
        Hooks:PostHook(
            PlayerDamage,
            event,
            "KH_ResetWeaponStreaks_" .. event,
            reset_weapon_streaks
        )
    else
        pcall(function()
            log("[KyoHUD][Streak] PlayerDamage:" .. event .. "() missing, reset not installed.")
        end)
    end
end
