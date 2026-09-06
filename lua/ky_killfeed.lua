-- ky_killfeed.lua — Killfeed : scoring, attribution et détection des kills
-- KyoHUD
-- Ce fichier est chargé dans les contextes PlayerManager et CopDamage (mod.txt)
-- et également par dofile depuis ky_civilian_killfeed.lua (CivilianDamage).
-- Les hooks sont installés conditionnellement via RequiredScript afin de ne
-- cibler que la classe présente dans chaque contexte de chargement.

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud
local HOTSWAP_WINDOW = 2.5

-- ═══════════════════════════════════════════════════
-- Catalogue de scoring (garde d'initialisation séparée)
-- ═══════════════════════════════════════════════════
-- Le concept et les valeurs initiales sont inspirés de Joy's Score Counter
-- par Offyerrocker, lui-même fondé sur les répliques de score de Joy en jeu.
-- La détection, l'attribution et le rendu sont propres à KyoHUD ; voir
-- CREDITS.md pour la filiation complète et le lien vers le projet source.
--
-- Le catalogue peut être chargé plusieurs fois (PlayerManager, CopDamage,
-- CivilianDamage) ; la garde empêche une reconstruction inutile tout en
-- permettant à chaque contexte d'installer ses propres hooks ensuite.

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

-- ── Familles de dégâts / d'armes ──
-- La cause finale de la mort décide seule de la famille créditée. L'ordre est
-- exclusif : la variante de dégâts (feu, poison, explosion, mêlée) d'abord,
-- puis seulement la catégorie de l'arme.
-- Un kill différé par le feu ne crédite donc jamais le fusil à pompe qui a
-- allumé la cible, et un souffle incendiaire qui tue directement reste explosif.
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

-- `akimbo` est un qualificatif cumulé à la catégorie de base de l'arme
-- (`{ "pistol", "akimbo" }`, `{ "shotgun", "akimbo" }`, …). Il prime donc sur
-- toute autre correspondance, quelle que soit sa position dans la liste.
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
    -- `categories` est la forme moderne ; `category` reste utilisée par
    -- d'anciennes définitions et par des armes ajoutées par d'autres mods.
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

    -- Repli : certaines bases d'armes moddées n'exposent que l'identifiant.
    local name_ok, name_id = pcall(function()
        if base.get_name_id then return base:get_name_id() end
        return base._name_id
    end)
    return name_ok and family_from_weapon_id(name_id) or nil
end

--- Famille créditée par un kill, ou `nil` si la cause réelle est inconnue.
--- `attack_info` peut porter `variant`, `weapon_unit` et `weapon_id`. L'arme
--- actuellement équipée n'est jamais consultée : un DOT ou un projectile ne
--- doit pas créditer une arme que le joueur tient au moment de la mort.
function KH:GetKillWeaponFamily(attack_info)
    if type(attack_info) ~= "table" then return nil end

    local variant = attack_info.variant
    local variant_family = type(variant) == "string"
        and WEAPON_FAMILY_BY_VARIANT[variant]
    if variant_family then return variant_family end

    return family_from_weapon_unit(attack_info.weapon_unit)
        or family_from_weapon_id(attack_info.weapon_id)
end

-- ── Évènements de kill ──
-- Les signaux moteur sont lus au kill, sans état inter-kills dans ce module.
-- Le HUD gère séparément le verrou par assaut et les paliers de rappel, après
-- déduplication. Les lectures fragiles sont protégées par `pcall` : une lecture
-- impossible vaut « évènement absent », jamais un signal du kill précédent.

-- « Dernier souffle » : sous ce ratio de santé, le kill est décoré.
local LOW_HEALTH_RATIO = 0.1
local FLASHBANG_INTENSITY_THRESHOLD = 0.05

local function local_player_unit()
    local ok, unit = pcall(function()
        return managers and managers.player and managers.player:player_unit()
    end)
    if not ok or not unit then return nil end

    local alive_ok, is_alive = pcall(alive, unit)
    return (alive_ok and is_alive) and unit or nil
end

--- `true` si le joueur local est à terre au moment du kill.
--- `PlayerManager:current_state()` renvoie le nom de l'état courant
--- (`"bleed_out"`, `"standard"`, …) ; `PlayerMovement:current_state_name()` sert
--- de repli, car le manager peut ne pas encore avoir suivi la transition.
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

--- `true` si la santé du joueur local est sous le seuil critique.
function KH:IsLocalPlayerLowHealth()
    local unit = local_player_unit()
    if not unit then return false end

    local ok, ratio = pcall(function()
        local damage = unit:character_damage()
        if not damage or not damage.health_ratio then return nil end
        return damage:health_ratio()
    end)
    ratio = ok and tonumber(ratio) or nil
    -- `ratio ~= ratio` écarte un NaN issu d'une santé maximale nulle.
    if not ratio or ratio ~= ratio or ratio < 0 then return false end
    return ratio < LOW_HEALTH_RATIO
end

--- `true` si l'intensité d'aveuglement courante dépasse la fin de décroissance
--- visuellement négligeable. Le contrôleur et son champ sont privés : toute
--- absence ou erreur moteur vaut donc simplement « pas aveuglé ».
function KH:IsLocalPlayerFlashbanged()
    local ok, intensity = pcall(function()
        local controller = managers and managers.environment_controller
        return controller and controller._current_flashbang
    end)
    intensity = ok and tonumber(intensity) or nil
    return intensity ~= nil and intensity == intensity
        and intensity > FLASHBANG_INTENSITY_THRESHOLD
end

--- Renseigne dans `out` l'état d'animation de l'ennemi : rechargement, course
--- et suspension à une corde. À appeler **avant** `CopDamage:die`, qui lance
--- l'animation de mort et écrase `reload` et `run`.
--- `rope_unit()` n'existe que sur `CopMovement` : le repli husk laisse `false`.
function KH:ReadEnemyKillState(unit, out)
    out.reload = false
    out.run = false
    out.rope = false
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

    -- Le jeu lit lui-même l'ActionSpooc dans `_active_actions[1]` pour ses
    -- succès Cloaker. Sur un husk ou une implémentation moddée qui ne l'expose
    -- pas, une lecture impossible reste volontairement un évènement absent.
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

function KH:RecordScoredKill(unit, unit_id, display_name, is_civilian, attack_info, event_info)
    if not self.add_kill then return end
    if unit and self._recorded_kill_units[unit] then return end

    if unit then
        self._recorded_kill_units[unit] = true
    end

    local special_enemy_kind = not is_civilian and self:GetSpecialEnemyKind(unit_id) or nil
    local score = self:GetKillScore(unit_id, is_civilian)
    local special_banner = (special_enemy_kind == "dozer" or special_enemy_kind == "boss")
        and special_enemy_kind or nil
    -- Un civil ne fait progresser aucune série d'arme.
    local weapon_family = not is_civilian
        and self:GetKillWeaponFamily(attack_info)
        or nil
    -- Un civil ne décerne aucune médaille d'évènement, comme il ne fait
    -- progresser aucune série d'arme.
    local kill_events = not is_civilian and event_info or nil
    self:add_kill(
        display_name,
        score,
        not is_civilian,
        special_banner,
        special_enemy_kind,
        weapon_family,
        kill_events
    )
end

KH._killscore_catalog_loaded = true

end -- fin de la garde _killscore_catalog_loaded

-- ═══════════════════════════════════════════════════
-- Hooks de détection des kills (contextuels)
-- ═══════════════════════════════════════════════════

-- Table de travail unique : la cause du kill n'est lue que le temps de
-- l'attribution, sans allouer une table par mort.
local ATTACK_INFO = { variant = nil, weapon_unit = nil, weapon_id = nil }

local function attack_info(variant, weapon_unit, weapon_id)
    ATTACK_INFO.variant = variant
    ATTACK_INFO.weapon_unit = weapon_unit
    ATTACK_INFO.weapon_id = weapon_id
    return ATTACK_INFO
end

-- Seconde table de travail unique : les évènements d'un kill ne vivent que le
-- temps de son attribution, sans allouer une table par mort.
local EVENT_INFO = {
    headshot = false,
    reload   = false,
    run      = false,
    rope     = false,
    grave    = false,
    low_hp   = false,
    revenge  = false,
    bulltrue = false,
    showstopper = false,
    blindfire = false,
    hotswap = false,
}

-- Le PreHook et le PostHook de `CopDamage:die` appartiennent au même chargement
-- du script et partagent cette table locale à clés faibles. Chaque capture est
-- consommée par le PostHook correspondant ; une erreur moteur ne peut donc ni
-- retenir une unité morte ni contaminer le kill suivant.
local PRE_DIE_ENEMY_STATES = setmetatable({}, { __mode = "k" })

local function consume_enemy_kill_state(unit, out)
    local state = unit and PRE_DIE_ENEMY_STATES[unit]
    if state then
        PRE_DIE_ENEMY_STATES[unit] = nil
        out.reload = state.reload
        out.run = state.run
        out.rope = state.rope
        out.bulltrue = state.bulltrue
        out.showstopper = state.showstopper
        return out
    end

    if KH.ReadEnemyKillState then
        return KH:ReadEnemyKillState(unit, out)
    end
    return out
end

--- Compose les évènements d'un kill, ou `nil` pour un civil. Les états ennemis
--- viennent de la capture faite avant `CopDamage:die` lorsqu'elle existe ; les
--- états joueur sont lus ici, à l'instant du kill. La capture est consommée même
--- pour un civil afin de ne retenir aucune unité morte.
---
--- La table de travail est remise à zéro en entrée, sur **tous** les chemins :
--- un civil, une lecture moteur impossible ou un chargement partiel ne peut donc
--- pas laisser le booléen d'un kill précédent décorer le kill suivant.
local function event_info(unit, headshot, is_civilian)
    EVENT_INFO.headshot = false
    EVENT_INFO.reload   = false
    EVENT_INFO.run      = false
    EVENT_INFO.rope     = false
    EVENT_INFO.grave    = false
    EVENT_INFO.low_hp   = false
    EVENT_INFO.revenge  = false
    EVENT_INFO.bulltrue = false
    EVENT_INFO.showstopper = false
    EVENT_INFO.blindfire = false
    EVENT_INFO.hotswap = false

    consume_enemy_kill_state(unit, EVENT_INFO)
    if is_civilian then return nil end

    EVENT_INFO.headshot = headshot == true
    EVENT_INFO.grave = KH.IsLocalPlayerDowned and KH:IsLocalPlayerDowned() or false
    -- Les conditions restent indépendantes : un kill à terre peut donc aussi
    -- remplir le critère de santé basse si le moteur rapporte un ratio < 10 %.
    EVENT_INFO.low_hp = KH.IsLocalPlayerLowHealth
        and KH:IsLocalPlayerLowHealth()
        or false
    EVENT_INFO.blindfire = KH.IsLocalPlayerFlashbanged
        and KH:IsLocalPlayerFlashbanged()
        or false
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

local function record_kill(unit, is_civilian, info, headshot)
    local unit_id = KH.GetKillUnitId and KH:GetKillUnitId(unit)
    local enemy_name = KH.GetKillDisplayName
        and KH:GetKillDisplayName(unit_id, is_civilian)
        or "Enemy"
    local events = event_info(unit, headshot, is_civilian)

    if KH.RecordScoredKill then
        KH:RecordScoredKill(unit, unit_id, enemy_name, is_civilian, info, events)
    elseif KH.add_kill then
        KH:add_kill(enemy_name)
    end
end

if RequiredScript == "lib/managers/playermanager" then
    Hooks:PostHook(PlayerManager, "on_killshot", "KH_OnLocalPlayerKillshot", function(self, killed_unit, variant, headshot, weapon_id)
        if not Network:is_client() then return end

        local unit_id = KH.GetKillUnitId and KH:GetKillUnitId(killed_unit)
        local civilian_ok, is_civilian = pcall(function()
            return unit_id and CopDamage.is_civilian(unit_id) or false
        end)

        -- Côté client, le tir à la tête est porté par l'argument `headshot` de
        -- `on_killshot` : `attack_data` n'existe pas sur ce chemin.
        record_kill(
            killed_unit,
            civilian_ok and is_civilian == true,
            attack_info(variant, nil, weapon_id),
            headshot == true
        )
    end)

elseif RequiredScript == "lib/units/enemies/cop/copdamage" then
    -- Le rechargement, la course et la suspension à une corde sont des états
    -- d'animation que `CopDamage:die` écrase en lançant l'animation de mort. Ils
    -- sont donc capturés avant l'appel original, jamais après. Ce PreHook ne
    -- fait que lire : il ne modifie ni `attack_data`, ni l'unité, ni le
    -- déroulement de `die`.
    Hooks:PreHook(CopDamage, "die", "KH_OnEnemyDiePre", function(self, attack_data)
        if not attack_data then return end
        if not KH.IsLocalKillAttacker
                or not KH:IsLocalKillAttacker(attack_data.attacker_unit) then
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
        if not KH.IsLocalKillAttacker or not KH:IsLocalKillAttacker(attacker) then
            -- Une cible de vengeance tuée par quelqu'un d'autre ne doit pas
            -- rester dans le set jusqu'au ramassage par le GC.
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

        -- `weapon_id` n'est pas standard dans `attack_data` ; il n'est lu que
        -- comme repli pour les mods qui l'ajoutent, sans jamais remplacer la
        -- cause réelle portée par `variant` et `weapon_unit`.
        local id_ok, weapon_id = pcall(function()
            return attack_data.weapon_id or attack_data.name_id
        end)
        record_kill(unit, is_civilian, attack_info(
            attack_data.variant,
            attack_data.weapon_unit,
            id_ok and weapon_id or nil
        ), attack_data.headshot == true)
    end)
end
-- Lorsque ce fichier est chargé par dofile depuis ky_civilian_killfeed.lua
-- (contexte CivilianDamage), aucune branche RequiredScript ne correspond :
-- seul le catalogue de scoring est initialisé, sans installer de hook ennemi.
