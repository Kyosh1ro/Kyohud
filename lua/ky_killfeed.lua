-- ky_killfeed.lua — Killfeed: scoring, attribution, and kill detection
-- KyoHUD
-- This file is loaded in PlayerManager, CopDamage, and
-- HuskCopDamage contexts (mod.txt), and also by dofile from
-- ky_civilian_killfeed.lua (CivilianDamage).
-- Hooks are installed conditionally via RequiredScript to only
-- target the class present in each loading context.

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud
local HOTSWAP_WINDOW = 2.5

-- ═══════════════════════════════════════════════════
-- Scoring catalog (separate initialization guard)
-- ═══════════════════════════════════════════════════
-- Concept and initial values are inspired by Joy's Score Counter
-- by Offyerrocker, himself based on in-game score replays by Joy.
-- Detection, attribution, and rendering are specific to KyoHUD; see
-- CREDITS.md for full lineage and link to the source project.
--

-- The catalog can be loaded multiple times (PlayerManager, CopDamage,
-- CivilianDamage); the guard prevents unnecessary reconstruction while
-- allowing each context to install its own hooks afterward.

if not KH._killscore_catalog_loaded then

local BOSS_UNIT_IDS = {
    "autumn", "biker_boss", "captain", "captain_female", "chavez_boss",
    "deep_boss", "drug_lord_boss", "drug_lord_boss_stealth",
    "fbi_vet_boss", "headless_hatman", "hector_boss",
    "hector_boss_no_armor", "mobster_boss", "phalanx_vip",
    "phalanx_vip_break", "snowman_boss", "spooc_titan", "spring",
    "summers", "triad_boss", "triad_boss_no_armor",
}

local SCORE_GROUPS = {
    [-1000] = {
        "mute_security_undominatable",
        "security_undominatable",
    },
    [2] = {
        "dave", "fbi_vet", "meme_man", "omnia_lpf", "vetlod",
    },
    [3] = {
        "heavy_swat_sniper", "marshal_marksman", "sniper", "deathvox_sniper",
    },
    [5] = {
        "marshal_shield", "marshal_shield_break", "shield", "deathvox_shield",
    },
    [6] = {
        "medic", "deathvox_medic",
    },
    [7] = {
        "boom", "taser", "deathvox_taser", "deathvox_grenadier",
    },
    [10] = {
        "meme_man_shield", "phalanx_minion", "spooc", "spooc_gangster",
        "deathvox_cloaker",
    },
    [12] = {
        "city_swat_titan", "hrt_titan", "medic_summers", "piggydozer",
        "tank", "tank_hw", "tank_hw_black", "tank_medic", "tank_mini",
        "tank_titan", "deathvox_tank", "deathvox_greendozer",
        "deathvox_blackdozer", "deathvox_lmgdozer", "deathvox_medicdozer",
        "deathvox_guarddozer",
    },
    [14] = {
        "boom_summers", "boom_titan", "taser_summers", "taser_titan",
        "taser_titan_reaper",
    },
    [20] = {
        "shadow_spooc",
    },
    [100] = BOSS_UNIT_IDS,
}

local SCORE_BY_UNIT = {}
for score, unit_ids in pairs(SCORE_GROUPS) do
    for _, unit_id in ipairs(unit_ids) do
        SCORE_BY_UNIT[unit_id] = score
    end
end

local BOSS_UNIT_ID_SET = {}
for _, unit_id in ipairs(BOSS_UNIT_IDS) do
    BOSS_UNIT_ID_SET[unit_id] = true
end

local DIFFICULTY_MULTIPLIERS = {
    easy         = 0.5,
    normal       = 1,
    hard         = 2,
    overkill     = 4,
    overkill_145 = 6,
    easy_wish    = 7,
    overkill_290 = 10,
    sm_wish      = 14,
}

local DISPLAY_NAMES = {
    swat_heavy     = "Heavy SWAT",
    heavy_swat     = "Heavy SWAT",
    shield         = "Shield",
    sniper         = "Sniper",
    taser          = "Taser",
    cloaker        = "Cloaker",
    spooc          = "Cloaker",
    medic          = "Medic",
    tank           = "Bulldozer",
    tank_hw        = "Headless Dozer",
    city_swat      = "GenSec Elite",
    fbi            = "FBI",
    fbi_heavy_swat = "FBI Heavy",
    gangster       = "Gangster",
    cop            = "Cop",
    security       = "Guard",
    swat           = "SWAT",
    marshal        = "Marshal",
}

local function contains(value, pattern)
    return value and string.find(value, pattern, 1, true) ~= nil
end

-- ── Damage/weapon families ──
-- The final cause of death decides alone the credited family. Order is
-- exclusive: damage variant (fire, poison, explosion, melee) first,
-- then only weapon category.
-- A kill deferred by fire never credits the shotgun that lit the target,
-- and a direct-fire incendiary blast remains explosive.
local WEAPON_FAMILY_BY_VARIANT = {
    fire      = "incendiary",
    poison    = "poison",
    explosion = "explosive",
    melee     = "melee",
}

local WEAPON_FAMILY_BY_CATEGORY = {
    akimbo  = "akimbo",
    shotgun = "shotgun",
    snp     = "sniper",
}

-- `akimbo` is a cumulative qualifier to the base weapon category
-- (`{ "pistol", "akimbo" }`, `{ "shotgun", "akimbo" }`, …). It thus takes precedence over
-- any other match, regardless of its position in the list.
local PRIORITY_WEAPON_FAMILY = "akimbo"

local function family_from_categories(categories)
    if type(categories) == "string" then
        return WEAPON_FAMILY_BY_CATEGORY[categories]
    end
    if type(categories) ~= "table" then return nil end

    local first_family = nil
    for _, category in ipairs(categories) do
        local family = type(category) == "string"
            and WEAPON_FAMILY_BY_CATEGORY[category]
        if family == PRIORITY_WEAPON_FAMILY then return family end
        if family and not first_family then first_family = family end
    end
    return first_family
end

local function family_from_weapon_tweak(weapon_tweak)
    if type(weapon_tweak) ~= "table" then return nil end
    -- `categories` is the modern form; `category` remains used by
    -- old definitions and weapons added by other mods.
    return family_from_categories(weapon_tweak.categories)
        or family_from_categories(weapon_tweak.category)
end

local function family_from_weapon_id(weapon_id)
    if type(weapon_id) ~= "string" or weapon_id == "" then return nil end

    local ok, weapon_tweak = pcall(function()
        return tweak_data and tweak_data.weapon and tweak_data.weapon[weapon_id]
    end)
    return ok and family_from_weapon_tweak(weapon_tweak) or nil
end

local function family_from_weapon_unit(weapon_unit)
    if not weapon_unit then return nil end

    local alive_ok, is_alive = pcall(alive, weapon_unit)
    if not alive_ok or not is_alive then return nil end

    local base_ok, base = pcall(function() return weapon_unit:base() end)
    if not base_ok or not base then return nil end

    local tweak_ok, weapon_tweak = pcall(function()
        return base.weapon_tweak_data and base:weapon_tweak_data() or nil
    end)
    if tweak_ok then
        local family = family_from_weapon_tweak(weapon_tweak)
        if family then return family end
    end

    -- Fallback: some modded weapon bases expose only the identifier.
    local name_ok, name_id = pcall(function()
        if base.get_name_id then return base:get_name_id() end
        return base._name_id
    end)
    return name_ok and family_from_weapon_id(name_id) or nil
end

--- Credit family by a kill, or `nil` if the actual cause is unknown.
--- `attack_info` can carry `variant`, `weapon_unit`, and `weapon_id`. The currently equipped weapon is never consulted: a DOT or projectile should not credit a weapon the player is holding at death.
function KH:GetKillWeaponFamily(attack_info)
    if type(attack_info) ~= "table" then return nil end

    local variant = attack_info.variant
    local variant_family = type(variant) == "string"
        and WEAPON_FAMILY_BY_VARIANT[variant]
    if variant_family then return variant_family end

    return family_from_weapon_unit(attack_info.weapon_unit)
        or family_from_weapon_id(attack_info.weapon_id)
end

-- ── Kill Events ──
-- Engine signals are read at kill time, with no inter-kill state in this module.
-- The HUD separately manages the per-assault lock and rappel tiers after
-- deduplication. Fragile reads are protected by `pcall`: a failed read means
-- an absent event, never a signal from the previous kill.

-- « Last Breath »: below this health ratio, the kill is decorated.
local LOW_HEALTH_RATIO = 0.1
local FLASHBANG_INTENSITY_THRESHOLD = 0.05
-- PAYDAY 2 expresses positions in centimeters: 3000 units = 30 meters.
local LONG_SHOT_DISTANCE = 3000

local function local_player_unit()
    local ok, unit = pcall(function()
        return managers and managers.player and managers.player:player_unit()
    end)
    if not ok or not unit then return nil end

    local alive_ok, is_alive = pcall(alive, unit)
    return (alive_ok and is_alive) and unit or nil
end

--- `true` if the local player is down at the moment of the kill.
--- `PlayerManager:current_state()` returns the name of the current state
--- (`"bleed_out"`, `"standard"`, …); `PlayerMovement:current_state_name()` serves
--- as a fallback, as the manager may not have followed the transition yet.
function KH:IsLocalPlayerDowned()
    local ok, state = pcall(function()
        return managers and managers.player and managers.player:current_state()
    end)
    if ok and state == "bleed_out" then return true end

    local unit = local_player_unit()
    if not unit then return false end

    local move_ok, move_state = pcall(function()
        local movement = unit:movement()
        if not movement or not movement.current_state_name then return nil end
        return movement:current_state_name()
    end)
    return move_ok and move_state == "bleed_out"
end

--- `true` if the local player's health is below the critical threshold.
function KH:IsLocalPlayerLowHealth()
    local unit = local_player_unit()
    if not unit then return false end

    local ok, ratio = pcall(function()
        local damage = unit:character_damage()
        if not damage or not damage.health_ratio then return nil end
        return damage:health_ratio()
    end)
    ratio = ok and tonumber(ratio) or nil
    -- `ratio ~= ratio` filters out a NaN from a zero maximum health.
    if not ratio or ratio ~= ratio or ratio < 0 then return false end
    return ratio < LOW_HEALTH_RATIO
end

--- `true` if the current blindness intensity exceeds visually negligible decay.
--- The controller and its field are private: any engine absence or error thus simply means « not blinded ».
function KH:IsLocalPlayerFlashbanged()
    local ok, intensity = pcall(function()
        local controller = managers and managers.environment_controller
        return controller and controller._current_flashbang
    end)
    intensity = ok and tonumber(intensity) or nil
    return intensity ~= nil and intensity == intensity
        and intensity > FLASHBANG_INTENSITY_THRESHOLD
end

--- `true` if the local player has both feet in the air at the moment of the kill.
--- The flag belongs to the current player state (`PlayerStandard:in_air()`);
--- states that do not expose it — handcuffed, down, civilian — have no
--- jump notion. The entire engine chain is fragile: only a strictly
--- positive `true` counts; any absence or error means « on the ground ».
function KH:IsLocalPlayerAirborne()
    local unit = local_player_unit()
    if not unit then return false end

    local ok, in_air = pcall(function()
        local movement = unit:movement()
        local state = movement and movement.current_state and movement:current_state()
        if not state or not state.in_air then return nil end
        return state:in_air()
    end)
    return ok and in_air == true
end

--- `true` if the target is more than 30 meters from the local player.
--- Positions and `mvector3` are fragile engine boundaries: an impossible read or
--- invalid distance simply means « no Long Shot ».
function KH:IsLongDistanceKill(unit)
    local player = local_player_unit()
    if not player or not unit then return false end

    local ok, distance = pcall(function()
        return mvector3.distance(player:position(), unit:position())
    end)
    distance = ok and tonumber(distance) or nil
    return distance ~= nil and distance == distance and distance > LONG_SHOT_DISTANCE
end

--- Populates `out` with useful pre-death enemy states: animation,
--- suspension on a rope, and carrying a bag. Call **before** `CopDamage:die`,
--- which triggers the death animation and may drop loot.
--- `CopMovement` accessors all have a fallback of `false`.
function KH:ReadEnemyKillState(unit, out)
    out.reload = false
    out.run = false
    out.rope = false
    out.loot_carrier = false
    out.bulltrue = false
    out.showstopper = false
    if not unit then return out end

    local alive_ok, is_alive = pcall(alive, unit)
    if not alive_ok or not is_alive then return out end

    local anim_ok, reload, run = pcall(function()
        local anim = unit.anim_data and unit:anim_data()
        if not anim then return false, false end
        return anim.reload and true or false, anim.run and true or false
    end)
    if anim_ok then
        out.reload = reload == true
        out.run = run == true
    end

    local rope_ok, rope = pcall(function()
        local movement = unit:movement()
        if not movement or not movement.rope_unit then return nil end
        return movement:rope_unit()
    end)
    out.rope = rope_ok and rope and true or false

    local carry_ok, carrying_bag = pcall(function()
        local movement = unit:movement()
        if not movement or not movement.carrying_bag then return false end
        return movement:carrying_bag()
    end)
    out.loot_carrier = carry_ok and carrying_bag == true

    -- The game reads ActionSpooc itself in `_active_actions[1]` for its
    -- Cloaker achievements. On a husk or modified implementation that does not expose
    -- it, an impossible read remains intentionally an absent event.
    local spooc_ok, attacking, flying = pcall(function()
        local movement = unit:movement()
        local action = movement and movement._active_actions
            and movement._active_actions[1]
        if not action or not action.type or action:type() ~= "spooc"
                or not action.is_flying_strike then
            return false, false
        end
        return true, action:is_flying_strike() == true
    end)
    if spooc_ok and attacking then
        out.bulltrue = flying == true
        out.showstopper = flying ~= true
    end

    return out
end

function KH:GetKillUnitId(unit)
    if not unit or not alive(unit) then return nil end

    local ok, unit_id = pcall(function()
        local base = unit:base()
        return base and base._tweak_table
    end)
    return ok and unit_id or nil
end

function KH:GetKillDisplayName(unit_id, is_civilian)
    if is_civilian and (not unit_id or unit_id == "civilian" or unit_id == "civilian_female") then
        return "Civilian"
    end
    if not unit_id then
        return is_civilian and "Civilian" or "Enemy"
    end
    return DISPLAY_NAMES[unit_id]
        or unit_id:gsub("_", " "):gsub("^%l", string.upper)
end

function KH:IsDozerUnitId(unit_id)
    return contains(unit_id, "tank") or contains(unit_id, "dozer")
end

function KH:IsBossUnitId(unit_id)
    return unit_id and BOSS_UNIT_ID_SET[unit_id] == true
end

function KH:GetSpecialEnemyKind(unit_id)
    if not unit_id then return nil end
    if self:IsDozerUnitId(unit_id) then return "dozer" end
    if self:IsBossUnitId(unit_id) then return "boss" end

    -- Prioritize Cloakers: certain modded variants also contain
    -- "shield" in their internal identifier (e.g., meme_man_shield).
    if contains(unit_id, "spooc") or contains(unit_id, "cloaker")
            or unit_id == "meme_man_shield" then
        return "cloaker"
    end
    if contains(unit_id, "taser") or contains(unit_id, "grenadier")
            or unit_id == "boom" or contains(unit_id, "boom_") then
        return "taser"
    end
    if contains(unit_id, "medic") then return "medic" end
    if contains(unit_id, "shield") or unit_id == "phalanx_minion" then return "shield" end
    if contains(unit_id, "sniper") or contains(unit_id, "marksman") then return "sniper" end
    return nil
end

--- Resolves the local source without confusing the player and its sentry. The fallback
--- `is_owner()` preserves attribution when the player unit is unavailable.
function KH:GetLocalKillSource(attacker)
    if not attacker then return nil end

    local player = local_player_unit()
    if player and attacker == player then return "player" end

    local base_ok, base = pcall(function()
        if not alive(attacker) then return nil end
        return attacker:base()
    end)
    if not base_ok or not base then return nil end

    if player and base.thrower_unit then
        local thrower_ok, thrower = pcall(function() return base:thrower_unit() end)
        if thrower_ok and thrower == player then return "player" end
    end

    if not base.sentry_gun then return nil end
    if player and base.get_owner then
        local owner_ok, owner = pcall(function() return base:get_owner() end)
        if owner_ok and owner == player then return "sentry" end
    end
    if base.is_owner then
        local owner_ok, is_owner = pcall(function() return base:is_owner() end)
        if owner_ok and is_owner == true then return "sentry" end
    end
    return nil
end

function KH:IsLocalKillAttacker(attacker)
    return self:GetLocalKillSource(attacker) ~= nil
end

function KH:GetKillBaseScore(unit_id, is_civilian)
    local exact_score = unit_id and SCORE_BY_UNIT[unit_id]
    if exact_score ~= nil then return exact_score end

    if is_civilian then
        local character_data = tweak_data
            and tweak_data.character
            and unit_id
            and tweak_data.character[unit_id]
        if character_data and character_data.no_civ_penalty then
            return nil
        end
        return -25
    end

    -- Fallback by archetype for variants added by other mods.
    if contains(unit_id, "_boss") or contains(unit_id, "phalanx_vip") then return 100 end
    if contains(unit_id, "tank") or contains(unit_id, "dozer") then return 12 end
    if contains(unit_id, "spooc") or contains(unit_id, "cloaker") then return 10 end
    if contains(unit_id, "taser") or contains(unit_id, "grenadier") then return 7 end
    if contains(unit_id, "medic") then return 6 end
    if contains(unit_id, "shield") then return 5 end
    if contains(unit_id, "sniper") or contains(unit_id, "marksman") then return 3 end
    return 1
end

function KH:GetKillScore(unit_id, is_civilian)
    local base_score = self:GetKillBaseScore(unit_id, is_civilian)
    if base_score == nil then return nil end

    local difficulty = Global
        and Global.game_settings
        and Global.game_settings.difficulty
    local multiplier = DIFFICULTY_MULTIPLIERS[difficulty] or 1
    return base_score * multiplier
end

KH._recorded_kill_units = KH._recorded_kill_units
    or setmetatable({}, { __mode = "k" })

function KH:RecordScoredKill(unit, unit_id, display_name, is_civilian, attack_info, event_info, kill_source)
    if not self.add_kill then return end
    if unit and self._recorded_kill_units[unit] then return end

    if unit then
        self._recorded_kill_units[unit] = true
    end

    local is_sentry = kill_source == "sentry"
    local special_enemy_kind = not is_civilian and not is_sentry
        and self:GetSpecialEnemyKind(unit_id) or nil
    local score = self:GetKillScore(unit_id, is_civilian)
    local special_banner = (special_enemy_kind == "dozer" or special_enemy_kind == "boss")
        and special_enemy_kind or nil
    -- A civilian advances no weapon streak.
    local weapon_family = not is_civilian and not is_sentry
        and self:GetKillWeaponFamily(attack_info)
        or nil
    -- A civilian awards no event medal, just as it advances no weapon streak.
    local kill_events = not is_civilian and not is_sentry and event_info or nil
    if kill_events then
        kill_events.overwatch = special_enemy_kind == "sniper"
            and weapon_family == "sniper"
    end
    self:add_kill(
        display_name,
        score,
        not is_civilian,
        special_banner,
        special_enemy_kind,
        weapon_family,
        kill_events,
        kill_source
    )
end

KH._killscore_catalog_loaded = true

end -- end of guard _killscore_catalog_loaded

-- ═══════════════════════════════════════════════════
-- Kill detection hooks (contextual)
-- ═══════════════════════════════════════════════════

-- Single working table: the kill cause is read only for the duration of
-- attribution, without allocating a table per death.
local ATTACK_INFO = { variant = nil, weapon_unit = nil, weapon_id = nil }

local function attack_info(variant, weapon_unit, weapon_id)
    ATTACK_INFO.variant = variant
    ATTACK_INFO.weapon_unit = weapon_unit
    ATTACK_INFO.weapon_id = weapon_id
    return ATTACK_INFO
end

-- Second single working table: kill events live only for the duration of their
-- attribution, without allocating a table per death.
local EVENT_INFO = {
    headshot = false,
    reload   = false,
    run      = false,
    rope     = false,
    loot_carrier = false,
    grave    = false,
    low_hp   = false,
    revenge  = false,
    bulltrue = false,
    showstopper = false,
    blindfire = false,
    hotswap = false,
    overwatch = false,
    long_shot = false,
    air_kill = false,
    magazine_kill = false,
    spray_down = false,
}

-- The PreHook and PostHook of `CopDamage:die` belong to the same script load
-- and share this local weak-keyed table. Each capture is consumed by the
-- corresponding PostHook; an engine error thus cannot retain a dead unit nor
-- contaminate the next kill.
local PRE_DIE_ENEMY_STATES = setmetatable({}, { __mode = "k" })

local function consume_enemy_kill_state(unit, out)
    local state = unit and PRE_DIE_ENEMY_STATES[unit]
    if state then
        PRE_DIE_ENEMY_STATES[unit] = nil
        out.reload = state.reload
        out.run = state.run
        out.rope = state.rope
        out.loot_carrier = state.loot_carrier
        out.bulltrue = state.bulltrue
        out.showstopper = state.showstopper
        return out
    end

    if KH.ReadEnemyKillState then
        return KH:ReadEnemyKillState(unit, out)
    end
    return out
end

--- Composes kill events, or `nil` for a civilian. Enemy states come from the
--- capture made before `CopDamage:die` if it exists; player states are read here,
--- at the moment of the kill. The capture is consumed even for a civilian to
--- retain no dead unit.
---

--- The working table is reset at entry, on **all** paths:
--- a civilian, an impossible engine read, or a partial load thus cannot
--- leave a previous kill's boolean decorating the next kill.
local function event_info(unit, headshot, is_civilian, info)
    EVENT_INFO.headshot = false
    EVENT_INFO.reload   = false
    EVENT_INFO.run      = false
    EVENT_INFO.rope     = false
    EVENT_INFO.loot_carrier = false
    EVENT_INFO.grave    = false
    EVENT_INFO.low_hp   = false
    EVENT_INFO.revenge  = false
    EVENT_INFO.bulltrue = false
    EVENT_INFO.showstopper = false
    EVENT_INFO.blindfire = false
    EVENT_INFO.hotswap = false
    EVENT_INFO.overwatch = false
    EVENT_INFO.long_shot = false
    EVENT_INFO.air_kill = false
    EVENT_INFO.magazine_kill = false
    EVENT_INFO.spray_down = false

    consume_enemy_kill_state(unit, EVENT_INFO)
    if is_civilian then return nil end

    EVENT_INFO.headshot = headshot == true
    EVENT_INFO.grave = KH.IsLocalPlayerDowned and KH:IsLocalPlayerDowned() or false
    -- Conditions remain independent: a downed kill can thus also
    -- meet the low health criterion if the engine reports a ratio < 10%.
    EVENT_INFO.low_hp = KH.IsLocalPlayerLowHealth
        and KH:IsLocalPlayerLowHealth()
        or false
    EVENT_INFO.blindfire = KH.IsLocalPlayerFlashbanged
        and KH:IsLocalPlayerFlashbanged()
        or false
    EVENT_INFO.long_shot = KH.IsLongDistanceKill
        and KH:IsLongDistanceKill(unit)
        or false
    EVENT_INFO.air_kill = KH.IsLocalPlayerAirborne
        and KH:IsLocalPlayerAirborne()
        or false
    EVENT_INFO.magazine_kill = info and info.variant == "bullet" or false
    local time_ok, kill_t = pcall(function()
        return TimerManager:game():time()
    end)
    kill_t = time_ok and tonumber(kill_t) or nil
    local switch_t = tonumber(KH._last_weapon_switch_t)
    local elapsed = kill_t and switch_t and (kill_t - switch_t) or nil
    EVENT_INFO.hotswap = elapsed ~= nil and elapsed >= 0 and elapsed < HOTSWAP_WINDOW
    local revenge_targets = KH._revenge_targets
    EVENT_INFO.revenge = revenge_targets and revenge_targets[unit] == true or false
    if EVENT_INFO.revenge then revenge_targets[unit] = nil end
    return EVENT_INFO
end

local function record_kill(unit, is_civilian, info, headshot, kill_source)
    local unit_id = KH.GetKillUnitId and KH:GetKillUnitId(unit)
    local enemy_name = KH.GetKillDisplayName
        and KH:GetKillDisplayName(unit_id, is_civilian)
        or "Enemy"
    local events = kill_source ~= "sentry"
        and event_info(unit, headshot, is_civilian, info)
        or nil

    if KH.RecordScoredKill then
        KH:RecordScoredKill(
            unit, unit_id, enemy_name, is_civilian, info, events, kill_source
        )
    elseif KH.add_kill then
        KH:add_kill(enemy_name)
    end
end

if RequiredScript == "lib/managers/playermanager" then
    -- ── Anti-Flash ──
    -- `FlashGrenadeUnitDamage` broadcasts `flash_grenade_destroyed` with the unit that
    -- destroyed the grenade, on host as well as client. The message describes
    -- no death: the medal is thus emitted directly, without a kill, without score
    -- and without touching any breach state.
    --

    -- The registration key is a table living in `KH`: it remains stable
    -- for the entire session, even if SuperBLT re-executes this chunk, and cannot
    -- collide with another mod's key.
    KH._flash_grenade_listener_uid = KH._flash_grenade_listener_uid or {}

    local function on_flash_grenade_destroyed(attacker_unit)
        local kill_source = KH.GetLocalKillSource
            and KH:GetLocalKillSource(attacker_unit)
        if kill_source ~= "player" then
            return
        end
        if KH.ShowEventMedal then
            KH:ShowEventMedal("no_flashbang")
        end
    end

    -- `managers.player` does not exist yet when this chunk is loaded: the first attempt fails as expected. Only a genuinely successful registration sets the flag, and the flag lives on `KH` so that a script reload never produces a second registration — the game's message system would then call the same medal twice.
    local function ensure_flash_grenade_listener()
        if KH._flash_grenade_listener_registered then return true end

        local ok, registered = pcall(function()
            local player_manager = managers and managers.player
            if not player_manager or not player_manager.register_message then
                return false
            end
            player_manager:register_message(
                "flash_grenade_destroyed",
                KH._flash_grenade_listener_uid,
                on_flash_grenade_destroyed
            )
            return true
        end)

        if ok and registered == true then
            KH._flash_grenade_listener_registered = true
            return true
        end
        return false
    end

    ensure_flash_grenade_listener()

    -- Fallback: `spawned_player` is called once each time the local player spawns,
    -- when `managers.player` has necessarily been constructed. The flag makes
    -- the next call immediately inert.
    Hooks:PostHook(PlayerManager, "spawned_player", "KH_RegisterFlashGrenadeListener", function()
        ensure_flash_grenade_listener()
    end)

    Hooks:PostHook(PlayerManager, "on_killshot", "KH_OnLocalPlayerKillshot", function(self, killed_unit, variant, headshot, weapon_id)
        if not Network:is_client() then return end

        local unit_id = KH.GetKillUnitId and KH:GetKillUnitId(killed_unit)
        local civilian_ok, is_civilian = pcall(function()
            return unit_id and CopDamage.is_civilian(unit_id) or false
        end)

        -- On the client side, the headshot is carried by the `headshot` argument of `on_killshot`: `attack_data` does not exist on this path.
        record_kill(
            killed_unit,
            civilian_ok and is_civilian == true,
            attack_info(variant, nil, weapon_id),
            headshot == true,
            "player"
        )
    end)

elseif RequiredScript == "lib/units/enemies/cop/copdamage" then
    -- Reload, sprint, and rope suspension are animation states that `CopDamage:die` overwrites by triggering the death animation. They are therefore captured before the original call, never after. This PreHook only reads: it does not modify either `attack_data`, the unit, or the flow of `die`.
    Hooks:PreHook(CopDamage, "die", "KH_OnEnemyDiePre", function(self, attack_data)
        if not attack_data then return end
        local kill_source = KH.GetLocalKillSource
            and KH:GetLocalKillSource(attack_data.attacker_unit)
        if kill_source ~= "player" then
            return
        end
        if KH.ReadEnemyKillState then
            local unit = self._unit
            if not unit then return end
            local state = {}
            KH:ReadEnemyKillState(unit, state)
            PRE_DIE_ENEMY_STATES[unit] = state
        end
    end)

    Hooks:PostHook(CopDamage, "die", "KH_OnEnemyDie", function(self, attack_data)
        if not attack_data then return end

        local unit = self._unit
        local attacker = attack_data.attacker_unit
        local kill_source = KH.GetLocalKillSource and KH:GetLocalKillSource(attacker)
        if not kill_source then
            -- A revenge target killed by someone else must not remain in the set until pickup by the GC.
            if unit and KH._revenge_targets then
                KH._revenge_targets[unit] = nil
            end
            return
        end

        local unit_id = KH.GetKillUnitId and KH:GetKillUnitId(unit)
        local civilian_ok, is_civilian = pcall(function()
            return unit_id and CopDamage.is_civilian(unit_id) or false
        end)
        is_civilian = civilian_ok and is_civilian == true

        -- `weapon_id` is not standard in `attack_data`; it is read only as a fallback for mods that add it, never replacing the actual cause carried by `variant` and `weapon_unit`.
        local id_ok, weapon_id = pcall(function()
            return attack_data.weapon_id or attack_data.name_id
        end)
        record_kill(unit, is_civilian, attack_info(
            attack_data.variant,
            attack_data.weapon_unit,
            id_ok and weapon_id or nil
        ), attack_data.headshot == true, kill_source)
    end)
elseif RequiredScript == "lib/units/enemies/cop/huskcopdamage" then
    Hooks:PostHook(HuskCopDamage, "die", "KH_OnClientSentryEnemyDie", function(self, attack_data)
        if not Network:is_client() or not attack_data then return end

        local kill_source = KH.GetLocalKillSource
            and KH:GetLocalKillSource(attack_data.attacker_unit)
        if kill_source ~= "sentry" then return end

        local unit = self._unit
        -- The sentry protocol does not maintain a reliable headshot on the client side.
        record_kill(unit, false, attack_info(
            attack_data.variant,
            attack_data.weapon_unit,
            nil
        ), false, kill_source)
    end)
end
-- When this file is loaded via dofile from ky_civilian_killfeed.lua (CivilianDamage context), no RequiredScript branch matches: only the scoring catalog is initialized, without installing an enemy hook.
