-- ky_killscore.lua — Calcul partagé des points du killfeed
-- Kyosh1ro HUD

if not Kyosh1roHUD then Kyosh1roHUD = {} end
local KH = Kyosh1roHUD

-- Le fichier est chargé depuis les contextes PlayerManager, CopDamage et CivilianDamage.
if KH._killscore_catalog_loaded then return end

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
    [100] = {
        "autumn", "biker_boss", "captain", "captain_female", "chavez_boss",
        "deep_boss", "drug_lord_boss", "drug_lord_boss_stealth",
        "fbi_vet_boss", "headless_hatman", "hector_boss",
        "hector_boss_no_armor", "mobster_boss", "phalanx_vip",
        "phalanx_vip_break", "snowman_boss", "spooc_titan", "spring",
        "summers", "triad_boss", "triad_boss_no_armor",
    },
}

local SCORE_BY_UNIT = {}
for score, unit_ids in pairs(SCORE_GROUPS) do
    for _, unit_id in ipairs(unit_ids) do
        SCORE_BY_UNIT[unit_id] = score
    end
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

function KH:GetSpecialEnemyKind(unit_id)
    if not unit_id or self:IsDozerUnitId(unit_id) then return nil end

    -- Prioriser les Cloakers : certaines variantes moddees contiennent aussi
    -- "shield" dans leur identifiant interne (par exemple meme_man_shield).
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

function KH:IsLocalKillAttacker(attacker)
    if not attacker or not alive(attacker) then return false end

    local player = managers.player and managers.player:player_unit()
    if not player or not alive(player) then return false end
    if attacker == player then return true end

    local ok, thrower = pcall(function()
        local base = attacker:base()
        return base and base.thrower_unit and base:thrower_unit()
    end)
    return ok and thrower == player
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

    -- Repli par archétype pour les variantes ajoutées par d'autres mods.
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

function KH:RecordScoredKill(unit, unit_id, display_name, is_civilian)
    if not self.add_kill then return end
    if unit and self._recorded_kill_units[unit] then return end

    if unit then
        self._recorded_kill_units[unit] = true
    end

    local score = self:GetKillScore(unit_id, is_civilian)
    local special_banner = self:IsDozerUnitId(unit_id) and "dozer" or nil
    local special_enemy_kind = not is_civilian and self:GetSpecialEnemyKind(unit_id) or nil
    self:add_kill(display_name, score, not is_civilian, special_banner, special_enemy_kind)
end

KH._killscore_catalog_loaded = true
