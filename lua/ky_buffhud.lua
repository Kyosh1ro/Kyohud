-- ky_buffhud.lua — Affichage horizontal des buffs + killfeed
-- Buffs affichés côte à côte sur une rangée horizontale configurable
-- Descripteurs d'icônes locaux inspirés de HUDList/VanillaHUD Plus ; voir CREDITS.md.

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud
local MY_MOD_PATH = ModPath

local catalog_ok, catalog_err = pcall(dofile, MY_MOD_PATH .. "lua/ky_buff_catalog.lua")
if not catalog_ok then
    log("[KyoHUD] Erreur chargement catalogue buffs (HUD): " .. tostring(catalog_err))
end

-- ═══════════════════════════════════════════════════
-- Utilitaires
-- ═══════════════════════════════════════════════════
local function clamp(x, lo, hi)
    if x < lo then return lo end
    if x > hi then return hi end
    return x
end

local function now()
    return TimerManager:game():time()
end

local FALLBACK_TEXTURE = "guis/textures/pd2/hud_timer"

-- ═══════════════════════════════════════════════════
-- État interne
-- ═══════════════════════════════════════════════════
KH._panel       = nil
KH._buffs       = {}           -- { [id] = {id, icon, color, value_text?, stack_text?, start_t, duration, t_end?, is_debuff} }
KH._buff_sources = {}          -- { [buff_id] = { [source_key] = source_data } }
KH._source_targets = {}        -- { [source_key] = { buff_id, ... } }
KH._kills       = {}           -- { {name, score?, score_text?, start_t, t_end?} }
KH._kill_combo  = { count = 0, last_t = nil, updated_t = nil }
KH._killfeed_score_total = 0     -- score de la rafale de killfeed en cours
KH._killfeed_score_has_value = false
KH._heist_score_total = 0
KH._heist_score_best_streak = 0
KH._heist_score_recorded = false
KH._special_kill_banner = nil
KH._banner_queue = {}          -- FIFO bornée : annonces en attente d'affichage
KH._weapon_streaks = {}        -- { [family] = { count, tier_index, last_t } }
KH._heist_kill_count = 0       -- kills ennemis cumulés depuis le début du braquage
KH._heist_kill_medal_index = 0 -- dernier palier de kills cumulés déjà annoncé
KH._medal_card = nil           -- médaille affichée dans la rangée du killfeed
KH._medal_queue = {}           -- FIFO bornée, indépendante du bandeau supérieur
KH._combo_label_variant_index = KH._combo_label_variant_index or 0
KH._dozer_banner_index = KH._dozer_banner_index or 0
KH._debug_banner_preview_index = KH._debug_banner_preview_index or 0
KH._special_enemy_combos = {}
KH._special_enemy_label_indices = KH._special_enemy_label_indices or {}
KH._update_acc  = 0

local MAX_KILLFEED_SIZE = 5
local DEFAULT_TEMPORARY_BUFF_DURATION = 5
local KILLFEED_ENTRY_DURATION = 5
local KILL_COMBO_WINDOW = 3
local KILL_SCROLL_TIME  = 0.2
local KILLFEED_FRAME_CLEARANCE = 1.5
local BANNER_FRAME_EXTENSION = 4
local SPECIAL_KILL_BANNER_DURATION = 1.25
-- La médaille vit dans le killfeed et reste un peu plus longtemps que les
-- annonces prioritaires afin que son palier soit lisible pendant l'action.
local MEDAL_CARD_DURATION = 1.75
local HUD_ACCENT_COLOR  = Color(0.52, 0.88, 0.92)
local PRIORITY_TARGET_COLOR = Color(1, 0.38, 0.08)
local KILLFEED_SCORE_COLOR = Color(1, 0.63, 0.12)
local KILLFEED_SCORE_PENALTY_COLOR = Color(1, 0.22, 0.12)
local AI_BUFF_LABEL     = "[AI]"
local HACKER_SPECIALIZATION_ID = 21
local POCKET_ECM_GRENADE_ID = "pocket_ecm_jammer"
local POCKET_ECM_COOLDOWN_ID = "pocket_ecm_jammer_debuff"

local function killfeed_size(settings)
    local value = tonumber(settings and settings.killfeed_size) or MAX_KILLFEED_SIZE
    return math.floor(clamp(value, 1, MAX_KILLFEED_SIZE))
end

local function format_kill_score(score)
    if type(score) ~= "number" then return nil end

    local rounded = math.floor(score)
    local value = score == rounded
        and tostring(rounded)
        or string.format("%.1f", score)
    return (score > 0 and "+" or "") .. value
end

local function has_active_killfeed_entry(kills, t)
    for _, kill in ipairs(kills or {}) do
        if not kill.t_end or kill.t_end > t then
            return true
        end
    end
    return false
end

local function approximate_text_width(text, font_size)
    return string.len(tostring(text or "")) * font_size * 0.58
end

local function measure_killfeed_entries(panel, kills, first_kill, count, font, font_size)
    local measurer = nil

    local function measure(text)
        if not measurer then
            measurer = panel:text({
                name = "ky_killfeed_text_measurer",
                text = "",
                font = font,
                font_size = font_size,
                visible = false,
                wrap = false,
                word_wrap = false,
            })
        end

        measurer:set_text(tostring(text or ""))
        local ok, _, _, text_w = pcall(function()
            return measurer:text_rect()
        end)
        if ok and type(text_w) == "number" and text_w > 0 then
            return text_w
        end
        return approximate_text_width(text, font_size)
    end

    for slot = 1, count do
        local kill = kills[first_kill + slot - 1]
        if kill and kill._measure_font_size ~= font_size then
            kill._measured_name_w = measure(kill.display_text or kill.name)
            kill._measured_score_w = kill.score_text and measure(kill.score_text) or 0
            kill._measure_font_size = font_size
        end
    end

    if measurer and alive(measurer) then
        panel:remove(measurer)
    end
end
local BANNER_FRAME_STYLE = {
    inset = 2,
    glow_alpha = 0.16,
    brackets = { extension = BANNER_FRAME_EXTENSION },
}
-- ═══════════════════════════════════════════════════
-- Résolution d'icônes — conventions HUDList adaptées localement
-- ═══════════════════════════════════════════════════
local function has_texture(path)
    return path and DB and DB:has(Idstring("texture"), Idstring(path))
end

--- Résout une icône à partir d'une table de description compatible HUDList.
--- Supporte : skills_new, skills, perks, hud_tweak, hud_icons, hudtabs, hudpickups, waypoints, texture direct
local function get_icon_data(icon)
    if not icon then return FALLBACK_TEXTURE, nil end

    local texture = icon.texture
    local texture_rect = icon.texture_rect
    local skills = icon.skills
    local skills_new = icon.skills_new

    -- Les coordonnées de l'atlas ont changé au fil des mises à jour. Quand le
    -- catalogue connaît le nom interne du skill, demander sa position au jeu
    -- et conserver les coordonnées statiques uniquement comme repli.
    if icon.skill_id then
        local ok, icon_xy = pcall(function()
            local skills_tweak = tweak_data and tweak_data.skilltree and tweak_data.skilltree.skills
            local skill = skills_tweak and skills_tweak[icon.skill_id]
            return skill and skill.icon_xy
        end)
        if ok and type(icon_xy) == "table" then
            if icon.skill_atlas == "skills" then
                skills = icon_xy
            else
                skills_new = icon_xy
            end
        end
    end

    if skills then
        texture = "guis/textures/pd2/skilltree/icons_atlas"
        local x, y = unpack(skills)
        texture_rect = { x * 64, y * 64, 64, 64 }
    elseif skills_new then
        texture = "guis/textures/pd2/skilltree_2/icons_atlas_2"
        local x, y = unpack(skills_new)
        texture_rect = { x * 80, y * 80, 80, 80 }
    elseif icon.perks then
        texture = string.format("guis/%stextures/pd2/specialization/icons_atlas",
            icon.texture_bundle_folder and string.format("dlcs/%s/", tostring(icon.texture_bundle_folder)) or "")
        local x, y = unpack(icon.perks)
        texture_rect = { x * 64, y * 64, 64, 64 }
    elseif icon.hud_tweak then
        local ok, tx, rect = pcall(function()
            return tweak_data.hud_icons:get_icon_data(icon.hud_tweak, texture_rect)
        end)
        if ok and tx then
            texture = tx
            texture_rect = rect
        end
    elseif icon.hud_icons then
        texture = "guis/textures/hud_icons"
        texture_rect = icon.hud_icons
    elseif icon.hudtabs then
        texture = "guis/textures/pd2/hud_tabs"
        texture_rect = icon.hudtabs
    elseif icon.hudpickups then
        texture = "guis/textures/pd2/hud_pickups"
        texture_rect = icon.hudpickups
    elseif icon.waypoints then
        texture = "guis/textures/pd2/pd2_waypoints"
        texture_rect = icon.waypoints
    end

    if not texture or not has_texture(texture) then
        texture = FALLBACK_TEXTURE
        texture_rect = nil
    end

    return texture, texture_rect
end

-- Le catalogue partagé des buffs est chargé depuis ky_buff_catalog.lua.

-- ═══════════════════════════════════════════════════
-- Résolution d'icône pour un buff_id
-- ═══════════════════════════════════════════════════
local function icon_for_buff(buff_id)
    local vhud_map = HUDList and HUDList.BuffItemBase and HUDList.BuffItemBase.MAP
    local map_entry = (vhud_map and vhud_map[buff_id])
        or (KH.BUFF_MAP and KH.BUFF_MAP[buff_id])
    if map_entry then
        local tex, rect = get_icon_data(map_entry)
        return { texture = tex, rect = rect }
    end
    return { texture = FALLBACK_TEXTURE }
end

local function current_perk_deck_ids()
    local ok, specialization_id, base_specialization_id = pcall(function()
        local skilltree = managers and managers.skilltree
        local current = skilltree and skilltree:get_specialization_value("current_specialization")
        current = tonumber(current)
        if not current then return nil, nil end

        local skilltree_tweak = tweak_data and tweak_data.skilltree
        local specialization = skilltree_tweak
            and skilltree_tweak.specializations
            and skilltree_tweak.specializations[current]
        return current, tonumber(specialization and specialization.based_on) or current
    end)
    if not ok then return nil, nil end
    return specialization_id, base_specialization_id
end

local function icon_for_equipped_perk_deck()
    local specialization_id = current_perk_deck_ids()
    if not specialization_id then
        return icon_for_buff("equipped_perk_deck")
    end

    if KH._equipped_perk_deck_id == specialization_id and KH._equipped_perk_deck_icon then
        return KH._equipped_perk_deck_icon
    end

    -- Cette API du jeu résout elle-même l'atlas correct, y compris pour les
    -- decks DLC. Conserver l'icône générique du catalogue comme repli.
    local icon_ok, texture, rect = pcall(function()
        local skilltree_tweak = tweak_data and tweak_data.skilltree
        return skilltree_tweak:get_specialization_icon_data(specialization_id)
    end)
    if not (icon_ok and texture and has_texture(texture)) then
        return icon_for_buff("equipped_perk_deck")
    end

    KH._equipped_perk_deck_id = specialization_id
    KH._equipped_perk_deck_icon = { texture = texture, rect = rect }
    return KH._equipped_perk_deck_icon
end

local function color_from_catalog(value)
    if not value then return nil end
    if type(value) ~= "string" then return value end

    local definition = (KH.BUFF_COLORS and KH.BUFF_COLORS[value]) or value
    local ok, color = pcall(function()
        if type(definition) == "table" then
            return Color(unpack(definition))
        end
        return Color(definition)
    end)
    return ok and color or nil
end

-- VanillaHUD+ peut fournir les icônes et les évènements, jamais la teinte.
-- La palette visible reste exclusivement celle du catalogue KyoHUD.
local function color_for_buff(buff_id, is_debuff)
    if is_debuff then
        return color_from_catalog("debuff")
            or Color.white
    end

    local catalog_entry = KH.BUFF_MAP and KH.BUFF_MAP[buff_id]
    return color_from_catalog(catalog_entry and catalog_entry.color)
        or Color.white
end

-- ═══════════════════════════════════════════════════
-- Vérifie si un buff doit être affiché (settings)
-- ═══════════════════════════════════════════════════
function KH:is_buff_visible(buff_id)
    if not self.settings or not self.settings.enable_buffs then return false end

    local map_entry = KH.BUFF_MAP and KH.BUFF_MAP[buff_id]
    if not map_entry then return true end -- buff inconnu, on l'affiche

    -- Vérifier le toggle de catégorie
    local cat = map_entry.category
    if cat and self.settings.buff_categories then
        if self.settings.buff_categories[cat] == false then
            return false
        end
    end

    -- Vérifier le toggle individuel
    if self.settings.buff_toggles then
        if self.settings.buff_toggles[buff_id] == false then
            return false
        end
    end

    return true
end

-- Ces indicateurs actifs conservent toujours le même ordre au début de la
-- rangée. Un indicateur absent ne réserve aucun emplacement vide.
local STATIC_BUFF_SLOTS = {
    "equipped_perk_deck",
    "pocket_ecm_jammer_debuff",
    "passive_health_regen",
    "standard_armor_regeneration",
    "armor_break_invulnerable_debuff",
    "damage_increase",
    "damage_reduction",
    "melee_damage_increase",
}

local STATIC_BUFF_SLOT_SET = {}
for _, buff_id in ipairs(STATIC_BUFF_SLOTS) do
    STATIC_BUFF_SLOT_SET[buff_id] = true
end

local function equipped_perk_deck_entry(hud)
    if not hud._equipped_perk_deck_buff then
        hud._equipped_perk_deck_buff = {
            id = "equipped_perk_deck",
            color = color_for_buff("equipped_perk_deck", false),
            persistent = true,
        }
    end
    hud._equipped_perk_deck_buff.icon = icon_for_equipped_perk_deck()
    return hud._equipped_perk_deck_buff
end

local function active_equipped_perk_buff(hud)
    local _, base_specialization_id = current_perk_deck_ids()
    local candidates = base_specialization_id
        and KH.PERK_DECK_BUFFS
        and KH.PERK_DECK_BUFFS[base_specialization_id]

    for _, buff_id in ipairs(candidates or {}) do
        local buff = hud._buffs[buff_id]
        local definition = KH.BUFF_MAP and KH.BUFF_MAP[buff_id]
        if buff and buff.icon and definition and definition.category == "perk"
                and hud:is_buff_visible(buff_id) then
            return buff, buff_id
        end
    end

    return nil, nil
end

local function localized_text(id, fallback)
    local value = fallback
    pcall(function()
        if managers.localization then
            local translated = managers.localization:text(id)
            if translated and translated ~= "" and translated:find("ERROR:", 1, true) ~= 1 then
                value = translated
            end
        end
    end)
    return value
end

-- Libellé optionnel d'une cellule, sans passer par value_text. Les buffs d'IA
-- conservent leur marqueur historique au-dessus de l'icône ; les autres n'en ont
-- un que si le catalogue déclare `label`, dont le champ `placement` choisit
-- entre BUFF_LABEL_TOP et BUFF_LABEL_TIMER. Le texte et le placement sont
-- renvoyés séparément : KH:draw n'alloue aucune table et la traduction est
-- résolue une seule fois par identifiant, pas à chaque image.
local BUFF_LABEL_TOP = "top"
local BUFF_LABEL_TIMER = "timer"
local buff_label_cache = {}
local function buff_label(buff)
    if buff.category == "ai" then
        return AI_BUFF_LABEL, BUFF_LABEL_TOP
    end

    local definition = KH.BUFF_MAP and KH.BUFF_MAP[buff.id]
    local label = definition and definition.label
    if not label then return nil end

    local placement = label.placement == BUFF_LABEL_TIMER and BUFF_LABEL_TIMER or BUFF_LABEL_TOP

    local cached = buff_label_cache[buff.id]
    if cached then return cached, placement end

    local text = localized_text(label.id, label.fallback)
    if managers and managers.localization then
        buff_label_cache[buff.id] = text
    end
    return text, placement
end

local heist_score_labels_cache = nil
local function heist_score_labels()
    if heist_score_labels_cache then return heist_score_labels_cache end

    local labels = {
        total = localized_text("ky_hud_score_total", "TOTAL SCORE"),
        best_streak = localized_text("ky_hud_score_best_streak", "BEST STREAK"),
        best_short = localized_text("ky_hud_score_best_short", "BEST"),
    }
    if managers and managers.localization then
        heist_score_labels_cache = labels
    end
    return labels
end

local COMBO_LABELS = {
    [2] = {
        { id = "ky_hud_combo_2",   fallback = "CLEAN PAIR" },
        { id = "ky_hud_combo_2_2", fallback = "DOUBLE TAP" },
        { id = "ky_hud_combo_2_3", fallback = "TWO FOR ONE" },
    },
    [3] = {
        { id = "ky_hud_combo_3",   fallback = "EXCELLENT" },
        { id = "ky_hud_combo_3_2", fallback = "TRIPLE THREAT" },
        { id = "ky_hud_combo_3_3", fallback = "THREE OF A KIND" },
    },
    [4] = {
        { id = "ky_hud_combo_4",   fallback = "OVERKILL" },
        { id = "ky_hud_combo_4_2", fallback = "FOUR DOWN" },
        { id = "ky_hud_combo_4_3", fallback = "QUAD STRIKE" },
    },
    [5] = {
        { id = "ky_hud_combo_5",   fallback = "FRENZY" },
        { id = "ky_hud_combo_5_2", fallback = "HIGH FIVE" },
        { id = "ky_hud_combo_5_3", fallback = "FIVEFOLD FURY" },
    },
    [6] = {
        { id = "ky_hud_combo_6",   fallback = "CARNAGE" },
        { id = "ky_hud_combo_6_2", fallback = "SIX FEET UNDER" },
        { id = "ky_hud_combo_6_3", fallback = "SIXFOLD SLAUGHTER" },
    },
    [7] = {
        { id = "ky_hud_combo_7",   fallback = "MASSACRE" },
        { id = "ky_hud_combo_7_2", fallback = "LUCKY SEVEN" },
        { id = "ky_hud_combo_7_3", fallback = "SEVENTH HEAVEN" },
    },
    [8] = {
        { id = "ky_hud_combo_8",   fallback = "EXTERMINATION" },
        { id = "ky_hud_combo_8_2", fallback = "EIGHT COUNT" },
        { id = "ky_hud_combo_8_3", fallback = "OCTUPLE ONSLAUGHT" },
    },
    [9] = {
        { id = "ky_hud_combo_9",   fallback = "APOCALYPSE" },
        { id = "ky_hud_combo_9_2", fallback = "CLOUD NINE" },
        { id = "ky_hud_combo_9_3", fallback = "NINE LIVES DENIED" },
    },
    [10] = {
        { id = "ky_hud_combo_10",   fallback = "PERFECT HEIST" },
        { id = "ky_hud_combo_10_2", fallback = "TEN OUT OF TEN" },
        { id = "ky_hud_combo_10_3", fallback = "DECADE OF DOOM" },
    },
}
local COMBO_LABEL_VARIANT_COUNT = #COMBO_LABELS[2]

local DOZER_BANNER_LABELS = {
    { id = "ky_hud_killdozer",  fallback = "KILLDOZER" },
    { id = "ky_hud_dozer_down", fallback = "DOZER DOWN" },
    { id = "ky_hud_bulldozed",  fallback = "BULLDOZED" },
}

local BOSS_BANNER_LABELS = {
    { id = "ky_hud_boss_eliminated", fallback = "BOSS ELIMINATED" },
}

local SPECIAL_KILL_BANNER_DEFINITIONS = {
    dozer = {
        color = PRIORITY_TARGET_COLOR,
        labels = DOZER_BANNER_LABELS,
    },
    boss = {
        color = PRIORITY_TARGET_COLOR,
        labels = BOSS_BANNER_LABELS,
    },
}

-- ── Séries persistantes par famille de dégâts / d'arme ──
-- Chaque famille possède son propre compteur, indépendant des autres : un kill
-- au fusil à pompe n'interrompt pas une série au sniper. Les paliers sont
-- strictement croissants et chaque palier n'est franchi qu'une seule fois par
-- cycle ; après une pause temporelle, la famille repart de son premier palier.
local WEAPON_STREAK_DEFINITIONS = {
    shotgun = {
        color = Color(1, 0.55, 0.12),               -- orange
        tiers = {
            { count = 5,  id = "ky_hud_streak_shotgun_5",  fallback = "SHOTGUN SPREE" },
            { count = 10, id = "ky_hud_streak_shotgun_10", fallback = "OPEN SEASON" },
            { count = 15, id = "ky_hud_streak_shotgun_15", fallback = "BUCK WILD" },
        },
    },
    sniper = {
        color = Color(0.32, 0.66, 1),               -- bleu froid
        tiers = {
            { count = 5,  id = "ky_hud_streak_sniper_5",  fallback = "SNIPER SPREE" },
            { count = 10, id = "ky_hud_streak_sniper_10", fallback = "SHARPSHOOTER" },
            { count = 15, id = "ky_hud_streak_sniper_15", fallback = "BE THE BULLET" },
        },
    },
    akimbo = {
        color = Color(0.24, 0.9, 0.96),             -- cyan
        tiers = {
            { count = 5,  id = "ky_hud_streak_akimbo_5",  fallback = "DOUBLE TROUBLE" },
            { count = 10, id = "ky_hud_streak_akimbo_10", fallback = "GUNS BLAZING" },
            { count = 15, id = "ky_hud_streak_akimbo_15", fallback = "TWICE THE FIREPOWER" },
        },
    },
    incendiary = {
        color = Color(1, 0.3, 0.06),                -- orange-rouge
        tiers = {
            { count = 3,  id = "ky_hud_streak_incendiary_3",  fallback = "BURN NOTICE" },
            { count = 6,  id = "ky_hud_streak_incendiary_6",  fallback = "INCINERATION" },
            { count = 10, id = "ky_hud_streak_incendiary_10", fallback = "HELLFIRE" },
        },
    },
    poison = {
        color = Color(0.36, 0.85, 0.29),            -- vert toxique
        tiers = {
            { count = 3,  id = "ky_hud_streak_poison_3",  fallback = "TOXIC" },
            { count = 6,  id = "ky_hud_streak_poison_6",  fallback = "VENOMOUS" },
            { count = 10, id = "ky_hud_streak_poison_10", fallback = "BIOHAZARD" },
        },
    },
    melee = {
        color = Color(0.78, 0.28, 1),               -- violet / magenta
        tiers = {
            { count = 2, id = "ky_hud_streak_melee_2", fallback = "ONE-TWO" },
            { count = 3, id = "ky_hud_streak_melee_3", fallback = "BONE CRACKER" },
            { count = 4, id = "ky_hud_streak_melee_4", fallback = "PUMMEL" },
            { count = 5, id = "ky_hud_streak_melee_5", fallback = "WRECKING CREW" },
        },
    },
    explosive = {
        color = Color(1, 0.79, 0.16),               -- jaune ambre
        tiers = {
            { count = 3, id = "ky_hud_streak_explosive_3", fallback = "BOOM" },
            { count = 5, id = "ky_hud_streak_explosive_5", fallback = "DEMOLITION" },
            { count = 8, id = "ky_hud_streak_explosive_8", fallback = "BLAST ZONE" },
        },
    },
}

-- ── Médailles d'évènement ──
-- Les conditions sont lues au kill. Seules Première frappe (verrou par
-- assaut) et les paliers de rappel (fenêtre de 3 s) gardent un état temporaire.
-- Aucun de ces états n'est sauvegardé. Plusieurs médailles peuvent tomber
-- sur le même kill.
--
-- Le descripteur d'icône ne porte qu'un nom `hud_tweak` : `get_icon_data`
-- demande au jeu la texture et la découpe d'atlas correspondantes, exactement
-- comme pour un buff du catalogue. Aucune coordonnée n'est écrite à la main.
local EVENT_MEDAL_DEFINITIONS = {
    first_strike = {
        id       = "ky_hud_event_medal_first_strike",
        fallback = "First Strike",
        color    = Color(1, 0.32, 0.26),             -- rouge orangé
        icon     = { hud_tweak = "pd2_kill" },
    },
    grave = {
        id       = "ky_hud_event_medal_grave",
        fallback = "Grave",
        color    = Color(0.68, 0.44, 0.92),          -- violet
        icon     = { hud_tweak = "mugshot_downed" },
    },
    low_hp = {
        id       = "ky_hud_event_medal_low_hp",
        fallback = "Last Breath",
        color    = Color(1, 0.18, 0.34),             -- rouge sang
        icon     = { hud_tweak = "csb_health" },
    },
    reload = {
        id       = "ky_hud_event_medal_reload",
        fallback = "Reload This",
        color    = Color(0.98, 0.78, 0.22),          -- ambre
        icon     = { hud_tweak = "csb_reload" },
    },
    through_shield = {
        id       = "ky_hud_event_medal_through_shield",
        fallback = "Through the Shield",
        color    = Color(1, 0.72, 0.16),             -- orange bouclier
        icon     = { hud_tweak = "csb_armor" },
    },
    one_shot_two_kills = {
        id       = "ky_hud_event_medal_one_shot_two_kills",
        fallback = "One Shot Two Kills",
        color    = Color(1, 0.48, 0.12),             -- rouge-or
        icon     = { hud_tweak = "pd2_kill" },
    },
    revenge = {
        id       = "ky_hud_event_medal_revenge",
        fallback = "Revenge",
        color    = Color(0.82, 0.28, 1),             -- violet électrique
        icon     = { hud_tweak = "csb_absorb" },
    },
    bulltrue = {
        id       = "ky_hud_event_medal_bulltrue",
        fallback = "Bulltrue",
        color    = Color(0.35, 1, 0.18),             -- vert Cloaker
        icon     = { hud_tweak = "crime_spree_cloaker_smoke" },
    },
    showstopper = {
        id       = "ky_hud_event_medal_showstopper",
        fallback = "Showstopper",
        color    = Color(0.35, 1, 0.18),             -- vert Cloaker
        icon     = { hud_tweak = "crime_spree_cloaker_smoke" },
    },
    rope = {
        id       = "ky_hud_event_medal_rope",
        fallback = "Pull!",
        color    = Color(0.36, 0.72, 1),             -- bleu
        icon     = { hud_tweak = "csb_lives" },
        tiers = {
            { count = 1, id = "ky_hud_event_medal_rope", fallback = "Pull!" },
            { count = 3, id = "ky_hud_event_medal_rope_3", fallback = "Free Fall" },
            { count = 5, id = "ky_hud_event_medal_rope_5", fallback = "Air Sweep" },
        },
    },
}

-- Une table Lua indexée par clé n'a pas d'ordre de parcours stable. Cette liste
-- fige donc l'ordre d'émission : deux kills portant les mêmes évènements
-- produisent toujours exactement la même suite de médailles.
local EVENT_MEDAL_ORDER = {
    "first_strike", "grave", "low_hp", "reload", "revenge", "bulltrue",
    "showstopper", "rope",
}

-- ── Paliers de kills cumulés du braquage ──
-- Compteur unique, indépendant de l'arme, du score et des fenêtres de temps :
-- tout kill ennemi non civil le fait avancer, il survit à une chute et ne
-- retombe à zéro qu'avec `KH:ResetHeistCombatState`. Les paliers sont
-- strictement croissants et chacun n'est annoncé qu'une fois par braquage.
local KILL_MEDAL_THRESHOLDS = { 50, 75, 100, 150, 200, 300, 400, 500 }

-- Or : la médaille cumulée se distingue des couleurs de famille d'arme.
local KILL_MEDAL_COLOR = Color(1, 0.84, 0.35)

-- La médaille cumulée n'écrit pas son nom : elle affiche le pictogramme du buff
-- de dégâts, celui déjà montré sous le libellé « Dmg+ » dans la rangée de buffs.
local KILL_MEDAL_ICON_BUFF = "damage_increase"

-- Familles de médailles partageant la rangée du killfeed. Le `kind` d'une carte
-- décide seulement de ce qu'un reset efface : le rendu, la durée et la file sont
-- identiques pour toutes.
local MEDAL_KIND_WEAPON_STREAK = "weapon_streak"
local MEDAL_KIND_KILL_TOTAL = "kill_total"
local MEDAL_KIND_EVENT = "event"

-- Le bandeau supérieur est exclusivement réservé au multikill, au boss et au
-- Dozer. Priorité d'affichage : boss > dozer. Le multikill n'entre pas dans la
-- file : il reste le repli affiché quand aucune annonce prioritaire n'occupe le
-- bandeau. Les médailles ont leur propre rangée dans le killfeed et
-- n'apparaissent jamais ici.
local BANNER_PRIORITIES = {
    boss  = 2,
    dozer = 1,
}

-- Bornée : quelques annonces suffisent à couvrir une salve, et la file ne doit
-- jamais croître sans limite pendant un assaut.
local MAX_BANNER_QUEUE = 4

-- Toutes les médailles sont de même mérite, quelle que soit leur famille : leur
-- file est strictement FIFO et n'interagit jamais avec celle du bandeau. Une
-- borne courte suffit, les paliers étant rares même pendant une salve.
local MAX_MEDAL_QUEUE = 3

local SPECIAL_ENEMY_DEFINITIONS = {
    dozer = {
        color = PRIORITY_TARGET_COLOR,
        labels = {
            { id = "ky_hud_dozer_tank_buster",          fallback = "TANK BUSTER" },
            { id = "ky_hud_dozer_armor_breaker",        fallback = "ARMOR BREAKER" },
            { id = "ky_hud_dozer_heavy_down",           fallback = "HEAVY DOWN" },
            { id = "ky_hud_dozer_ive_got_the_big_guy", fallback = "I'VE GOT THE BIG GUY" },
        },
    },
    boss = {
        color = PRIORITY_TARGET_COLOR,
        labels = BOSS_BANNER_LABELS,
    },
    medic = {
        color = Color(0.2, 0.95, 0.55),
        labels = {
            { id = "ky_hud_medic_code_blue",    fallback = "CODE BLUE" },
            { id = "ky_hud_medic_bad_medicine", fallback = "BAD MEDICINE" },
            { id = "ky_hud_medic_doctor_down",  fallback = "DOCTOR DOWN" },
        },
    },
    cloaker = {
        color = Color(0.35, 1, 0.18),
        labels = {
            { id = "ky_hud_cloaker_shadow_hunter", fallback = "SHADOW HUNTER" },
            { id = "ky_hud_cloaker_counter_kick",  fallback = "COUNTER-KICK" },
            { id = "ky_hud_cloaker_ambush_broken", fallback = "AMBUSH BROKEN" },
        },
    },
    taser = {
        color = Color(0.35, 0.75, 1),
        labels = {
            { id = "ky_hud_taser_power_outage",    fallback = "POWER OUTAGE" },
            { id = "ky_hud_taser_circuit_breaker", fallback = "CIRCUIT BREAKER" },
            { id = "ky_hud_taser_blackout",        fallback = "BLACKOUT" },
        },
    },
    shield = {
        color = Color(1, 0.72, 0.16),
        labels = {
            { id = "ky_hud_shield_breaker",        fallback = "SHIELD BREAKER" },
            { id = "ky_hud_shield_phalanx_fall",   fallback = "PHALANX FALL" },
            { id = "ky_hud_shield_barrier_down",   fallback = "BARRIER DOWN" },
            { id = "ky_hud_shield_defense_denied", fallback = "DEFENSE DENIED" },
        },
    },
    sniper = {
        color = Color(1, 0.34, 0.3),
        labels = {
            { id = "ky_hud_sniper_counter_sniper",  fallback = "COUNTER-SNIPER" },
            { id = "ky_hud_sniper_scope_breaker",   fallback = "SCOPE BREAKER" },
            { id = "ky_hud_sniper_longshot_denied", fallback = "LONGSHOT DENIED" },
        },
    },
}

local function combo_label(count, variant_index)
    local variants = COMBO_LABELS[count]
    local definition = variants and variants[variant_index or 1]
    if definition then
        return localized_text(definition.id, definition.fallback)
    end
    return localized_text("ky_hud_combo_chain", "KILL CHAIN") .. " x" .. tostring(count)
end

local function combo_color(count)
    if count == 2 then return Color(1, 0.85, 0.2) end
    if count == 3 then return Color(1, 0.55, 0.1) end
    if count == 4 then return Color(1, 0.2, 0.1) end
    return Color(0.9, 0.15, 1)
end

-- Un bandeau porte directement son libellé et sa couleur. `KH:draw` n'a donc
-- aucune table de définitions à parcourir, et une nouvelle famille d'annonce se
-- branche sans toucher au rendu.
local function make_special_kill_banner(kind, label_index)
    local definition = kind and SPECIAL_KILL_BANNER_DEFINITIONS[kind]
    if not definition then return nil end

    local labels = definition.labels
    local label_definition = labels and (labels[label_index] or labels[1])
    if not label_definition then return nil end

    return {
        kind  = kind,
        label = localized_text(label_definition.id, label_definition.fallback),
        color = definition.color or HUD_ACCENT_COLOR,
    }
end

local function weapon_streak_definition(family)
    return family and WEAPON_STREAK_DEFINITIONS[family] or nil
end

--- Médaille de palier : elle porte directement son libellé et sa couleur, comme
--- un bandeau, mais elle est rendue dans le killfeed et n'a ni nom d'unité ni
--- score à afficher.
local function make_weapon_streak_card(family, tier_index)
    local definition = weapon_streak_definition(family)
    local tier = definition and definition.tiers[tier_index]
    if not tier then return nil end

    return {
        kind   = MEDAL_KIND_WEAPON_STREAK,
        family = family,
        label  = localized_text(tier.id, tier.fallback),
        color  = definition.color or HUD_ACCENT_COLOR,
    }
end

--- Médaille de kills cumulés. Le nom de la médaille est porté par l'icône du
--- buff de dégâts ; il ne reste que le palier atteint et une seule clé, commune
--- aux huit paliers. Texture, découpe d'atlas et teinte sont résolues ici, une
--- fois par médaille : `KH:draw` n'a plus qu'à poser la bitmap.
local function make_kill_medal_card(kill_count)
    if type(kill_count) ~= "number" then return nil end

    return {
        kind  = MEDAL_KIND_KILL_TOTAL,
        icon  = icon_for_buff(KILL_MEDAL_ICON_BUFF),
        icon_color = color_for_buff(KILL_MEDAL_ICON_BUFF),
        label = tostring(kill_count) .. " "
            .. localized_text("ky_hud_kill_medal_kills", "KILLS"),
        color = KILL_MEDAL_COLOR,
    }
end

--- Médaille d'évènement. `id` est la clé d'`EVENT_MEDAL_DEFINITIONS`, jamais un
--- libellé. Comme la médaille cumulée, la carte porte un pictogramme : texture,
--- découpe d'atlas, libellé traduit et teinte sont résolus ici, une seule fois
--- par médaille, afin que `KH:draw` n'ait plus qu'à poser la bitmap.
local function make_event_medal_card(id, tier_index)
    local definition = id and EVENT_MEDAL_DEFINITIONS[id]
    if not definition then return nil end
    local label = definition.tiers and definition.tiers[tier_index or 1] or definition
    if not label then return nil end

    local color = definition.color or HUD_ACCENT_COLOR
    local texture, rect = get_icon_data(definition.icon)
    return {
        kind       = MEDAL_KIND_EVENT,
        event      = id,
        tier_index = definition.tiers and (tier_index or 1) or nil,
        icon       = { texture = texture, rect = rect },
        icon_color = color,
        label      = localized_text(label.id, label.fallback),
        color      = color,
    }
end

--- Émet directement une carte d'évènement sans enregistrer de kill ni de score.
--- Réservé aux hooks moteur qui agrègent déjà les victimes d'un même tir.
function KH:ShowEventMedal(id)
    self:_show_medal_card(now(), make_event_medal_card(id), false)
end

local function special_enemy_definition(kind)
    return kind and SPECIAL_ENEMY_DEFINITIONS[kind] or nil
end

local function special_enemy_label(kind, index, count)
    local definition = special_enemy_definition(kind)
    local labels = definition and definition.labels
    local label_definition = labels and (labels[index] or labels[1])
    if not label_definition then return nil end

    local label = localized_text(label_definition.id, label_definition.fallback)
    if count and count >= 2 then
        label = label .. " x" .. tostring(count)
    end
    return label
end

local function special_enemy_color(kind)
    local definition = special_enemy_definition(kind)
    return definition and definition.color or HUD_ACCENT_COLOR
end

-- Cadre tactique inspiré des notifications Battlefield : traits asymétriques,
-- quatre crochets détachés et chevrons qui convergent vers le contenu.
local function draw_corner_brackets(panel, x, y, w, h, color, alpha, layer, style)
    local extension = style and style.extension or 4
    local arm_x = style and style.arm_x or math.min(18, w * 0.08)
    local arm_y = style and style.arm_y or math.min(11, h * 0.3)
    local line_width = style and style.line_width or 1
    local left = x - extension
    local right = x + w + extension
    local top = y - extension
    local bottom = y + h + extension
    local corners = {
        {
            Vector3(left + arm_x, top, 0),
            Vector3(left, top, 0),
            Vector3(left, top + arm_y, 0),
        },
        {
            Vector3(right - arm_x, top, 0),
            Vector3(right, top, 0),
            Vector3(right, top + arm_y, 0),
        },
        {
            Vector3(left, bottom - arm_y, 0),
            Vector3(left, bottom, 0),
            Vector3(left + arm_x, bottom, 0),
        },
        {
            Vector3(right, bottom - arm_y, 0),
            Vector3(right, bottom, 0),
            Vector3(right - arm_x, bottom, 0),
        },
    }

    for _, points in ipairs(corners) do
        panel:polyline({
            points = points,
            line_width = line_width,
            color = color,
            alpha = alpha,
            layer = layer,
        })
    end
end

-- ── Chevrons du bandeau ──
-- Deux banques miroir encadrent le texte. Les annonces spéciales gardent trois
-- flèches purement décoratives ; le multikill utilise une banque compacte et
-- fixe de cinq encoches par côté, remplies d'un cran par kill supplémentaire.
local SPECIAL_CHEVRON_SLOTS = 3
local SPECIAL_CHEVRON_W = 7
local SPECIAL_CHEVRON_H = 12
local SPECIAL_CHEVRON_GAP = 3
local SPECIAL_CHEVRON_GROUP_W = SPECIAL_CHEVRON_SLOTS * SPECIAL_CHEVRON_W
    + (SPECIAL_CHEVRON_SLOTS - 1) * SPECIAL_CHEVRON_GAP
local SPECIAL_CHEVRON_MARGIN = 16

local MULTIKILL_CHEVRON_SLOTS = 5
local MULTIKILL_CHEVRON_W = 6
local MULTIKILL_CHEVRON_H = 12
local MULTIKILL_CHEVRON_GAP = 2
local MULTIKILL_CHEVRON_GROUP_W = MULTIKILL_CHEVRON_SLOTS * MULTIKILL_CHEVRON_W
    + (MULTIKILL_CHEVRON_SLOTS - 1) * MULTIKILL_CHEVRON_GAP
-- La banque multikill est plus large que les trois flèches décoratives : sa
-- marge est réduite d'autant pour que les deux bandeaux réservent exactement la
-- même place et que le texte reste centré, même à la largeur minimale.
local MULTIKILL_CHEVRON_MARGIN = SPECIAL_CHEVRON_MARGIN
    + SPECIAL_CHEVRON_GROUP_W
    - MULTIKILL_CHEVRON_GROUP_W
local BANNER_CHEVRON_TEXT_GAP = 5

-- Dimensions paires et halo entier : les pointes restent sur la grille de
-- pixels au lieu de tomber à 5,5 px ou dans une boîte mise à l'échelle.
local MULTIKILL_CHEVRON_GLOW_W = MULTIKILL_CHEVRON_W + 2
local MULTIKILL_CHEVRON_GLOW_H = MULTIKILL_CHEVRON_H + 2
local MULTIKILL_CHEVRON_GLOW_DX = 1
local MULTIKILL_CHEVRON_HOLE_INSET = 1
local MULTIKILL_CHEVRON_OUTLINE_ALPHA = 0.26
local MULTIKILL_CHEVRON_HOLE_ALPHA = 0.7
local MULTIKILL_CHEVRON_GLOW_ALPHA = 0.18

--- Sommets d'un chevron inscrit dans la boîte `w * h`, pointe vers l'intérieur.
local function chevron_triangles(w, h, direction)
    if direction > 0 then
        return {
            Vector3(0, 0, 0),
            Vector3(0, h, 0),
            Vector3(w, h * 0.5, 0),
        }
    end
    return {
        Vector3(w, 0, 0),
        Vector3(w, h, 0),
        Vector3(0, h * 0.5, 0),
    }
end

--- Chevron intérieur simple. À cette taille, des coordonnées entières donnent
--- un contour plus régulier que la réduction géométrique à base de racine.
local function inset_chevron_triangles(w, h, direction, inset)
    if direction > 0 then
        return {
            Vector3(inset, inset, 0),
            Vector3(inset, h - inset, 0),
            Vector3(w - inset, h * 0.5, 0),
        }
    end
    return {
        Vector3(w - inset, inset, 0),
        Vector3(w - inset, h - inset, 0),
        Vector3(inset, h * 0.5, 0),
    }
end

-- Formes figées une seule fois : `KH:draw` n'alloue aucun point par encoche.
local MULTIKILL_CHEVRON_SHAPES = {}
for _, direction in ipairs({ 1, -1 }) do
    MULTIKILL_CHEVRON_SHAPES[direction] = {
        fill = chevron_triangles(MULTIKILL_CHEVRON_W, MULTIKILL_CHEVRON_H, direction),
        glow = chevron_triangles(MULTIKILL_CHEVRON_GLOW_W, MULTIKILL_CHEVRON_GLOW_H, direction),
        hole = inset_chevron_triangles(
            MULTIKILL_CHEVRON_W,
            MULTIKILL_CHEVRON_H,
            direction,
            MULTIKILL_CHEVRON_HOLE_INSET
        ),
    }
end

--- Nombre d'encoches allumées pour une série : x2 = 1/5 ... x6 et plus = 5/5.
local function multikill_chevron_fill(count)
    return clamp((tonumber(count) or 2) - 1, 1, MULTIKILL_CHEVRON_SLOTS)
end

--- Banque de progression multikill.
--- `direction > 0` dessine le groupe gauche (encoches pointant vers le texte,
--- la plus proche du texte étant la dernière) ; `direction < 0` son miroir.
--- Le remplissage part donc du texte vers l'extérieur, symétriquement.
local function draw_multikill_chevrons(panel, x, y, direction, color, alpha, layer, filled)
    local shapes = MULTIKILL_CHEVRON_SHAPES[direction > 0 and 1 or -1]
    local start_x = math.floor(x + 0.5)
    local center_y = math.floor(y + 0.5)
    local top = center_y - MULTIKILL_CHEVRON_H * 0.5
    local glow_top = center_y - MULTIKILL_CHEVRON_GLOW_H * 0.5

    for slot = 1, MULTIKILL_CHEVRON_SLOTS do
        local arrow_x = start_x + (slot - 1) * (MULTIKILL_CHEVRON_W + MULTIKILL_CHEVRON_GAP)
        -- `rank` = distance au texte, 1 pour l'encoche la plus proche.
        local rank = direction > 0 and (MULTIKILL_CHEVRON_SLOTS - slot + 1) or slot

        if rank <= filled then
            -- Dégradé retenu vers l'extérieur : la progression reste lisible
            -- sans que la banque saturée n'écrase le texte.
            local prominence = 1 - (rank - 1) / (MULTIKILL_CHEVRON_SLOTS - 1)
            local slot_alpha = alpha * (0.72 + 0.28 * prominence)

            panel:polygon({
                x = arrow_x - MULTIKILL_CHEVRON_GLOW_DX,
                y = glow_top,
                w = MULTIKILL_CHEVRON_GLOW_W,
                h = MULTIKILL_CHEVRON_GLOW_H,
                triangles = shapes.glow,
                color = color,
                alpha = slot_alpha * MULTIKILL_CHEVRON_GLOW_ALPHA,
                layer = layer,
            })
            panel:polygon({
                x = arrow_x,
                y = top,
                w = MULTIKILL_CHEVRON_W,
                h = MULTIKILL_CHEVRON_H,
                triangles = shapes.fill,
                color = color,
                alpha = slot_alpha,
                layer = layer + 1,
            })
        else
            -- Encoche libre : chevron évidé, assez discret pour ne pas être
            -- confondu avec un cran acquis, assez net pour rester lisible.
            panel:polygon({
                x = arrow_x,
                y = top,
                w = MULTIKILL_CHEVRON_W,
                h = MULTIKILL_CHEVRON_H,
                triangles = shapes.fill,
                color = color,
                alpha = alpha * MULTIKILL_CHEVRON_OUTLINE_ALPHA,
                layer = layer,
            })
            panel:polygon({
                x = arrow_x,
                y = top,
                w = MULTIKILL_CHEVRON_W,
                h = MULTIKILL_CHEVRON_H,
                triangles = shapes.hole,
                color = Color.black,
                alpha = alpha * MULTIKILL_CHEVRON_HOLE_ALPHA,
                layer = layer + 1,
            })
        end
    end
end

-- Chevrons décoratifs pleins, réservés aux annonces spéciales (dozer, boss).
local function draw_chevrons(panel, x, y, direction, color, alpha, layer, style)
    local count = SPECIAL_CHEVRON_SLOTS
    local arrow_w = style and style.arrow_w or SPECIAL_CHEVRON_W
    local arrow_h = style and style.arrow_h or SPECIAL_CHEVRON_H
    local gap = style and style.gap or SPECIAL_CHEVRON_GAP

    for i = 0, count - 1 do
        local arrow_x = x + i * (arrow_w + gap)
        local triangles
        if direction > 0 then
            triangles = {
                Vector3(0, 0, 0),
                Vector3(0, arrow_h, 0),
                Vector3(arrow_w, arrow_h * 0.5, 0),
            }
        else
            triangles = {
                Vector3(arrow_w, 0, 0),
                Vector3(arrow_w, arrow_h, 0),
                Vector3(0, arrow_h * 0.5, 0),
            }
        end

        local prominence
        if direction > 0 then
            prominence = i / (count - 1)
        else
            prominence = (count - 1 - i) / (count - 1)
        end

        panel:polygon({
            x = arrow_x,
            y = y - arrow_h * 0.5,
            w = arrow_w,
            h = arrow_h,
            triangles = triangles,
            color = color,
            alpha = alpha * (0.55 + 0.45 * prominence),
            layer = layer,
        })
    end
end

local TACTICAL_FRAME_SEGMENTS = {
    { 0.09, 0, 0.2  },
    { 0.37, 0, 0.11 },
    { 0.6,  0, 0.27 },
    { 0.06, 1, 0.13 },
    { 0.27, 1, 0.3  },
    { 0.7,  1, 0.18 },
}

local function draw_tactical_frame(panel, x, y, w, h, color, alpha, layer, style)
    local glow_alpha = style and style.glow_alpha or 0.16
    local inset = style and style.inset or 2

    panel:gradient({
        x = x + inset,
        y = y + inset,
        w = w - inset * 2,
        h = h - inset * 2,
        orientation = "horizontal",
        gradient_points = {
            0, Color.black:with_alpha(alpha * 0.16),
            0.2, Color.black:with_alpha(alpha * 0.62),
            0.5, Color.black:with_alpha(alpha * 0.78),
            0.82, Color.black:with_alpha(alpha * 0.58),
            1, Color.black:with_alpha(alpha * 0.1),
        },
        layer = layer,
    })

    -- Trois segments sur chaque bord, volontairement décalés et inégaux.
    for _, segment in ipairs(TACTICAL_FRAME_SEGMENTS) do
        local segment_x = x + w * segment[1]
        local segment_y = y + (segment[2] == 1 and h - 1 or 0)
        local segment_w = w * segment[3]
        panel:rect({
            x = segment_x, y = segment_y - 1, w = segment_w, h = 3,
            color = color, alpha = alpha * glow_alpha, layer = layer + 1,
        })
        panel:rect({
            x = segment_x, y = segment_y, w = segment_w, h = 1,
            color = color, alpha = alpha, layer = layer + 2,
        })
    end

    draw_corner_brackets(
        panel, x, y, w, h, color, alpha, layer + 2,
        style and style.brackets
    )
end

-- Cellule volontairement sobre pour laisser l'icône et son timer dominer.
-- Le cadre tactique complet reste réservé aux annonces du killfeed.
--
-- Le fond est un dégradé noir vertical : dense en bas, effacé en haut, afin
-- d'asseoir la cellule sans masquer la rangée. Le contour statique n'a que
-- trois côtés — montant gauche, barre inférieure, montant droit — et jamais
-- de bord supérieur. Sa teinte est fixée ici à `HUD_ACCENT_COLOR` et n'est
-- donc volontairement pas paramétrable : aucun état de buff ne peut la
-- modifier. Seule son opacité est modelée, afin que le contour périmétrique
-- animé reste le seul élément du cadre coloré par l'état du buff.
--
-- Un seul pixel suffit : le trait reste net à toutes les tailles de buffs et
-- laisse le contour animé, plus épais, se lire clairement au-dessus.
local BUFF_CELL_LINE_WIDTH = 1

-- Les montants se renforcent doucement du haut vers le bas, dans le sens du
-- dégradé de fond. La barre inférieure ne s'allège qu'à ses extrémités : le
-- bas reste ancré et les deux jonctions avec les montants restent visibles.
local BUFF_CELL_EDGE_ALPHA_TOP    = 0.34
local BUFF_CELL_EDGE_ALPHA_MID    = 0.66
local BUFF_CELL_EDGE_ALPHA_BOTTOM = 1
local BUFF_CELL_FOOTER_ALPHA_END  = 0.8

-- Les positions de rangée sont fractionnaires. Le cadre statique et le
-- contour animé doivent être arrondis exactement de la même façon, sinon les
-- deux tracés se décalent d'un demi-pixel et paraissent délavés.
local function align_buff_cell_rect(x, y, w, h)
    local left = math.floor(x + 0.5)
    local top  = math.floor(y + 0.5)
    local min_size = BUFF_CELL_LINE_WIDTH * 2
    return left,
        top,
        math.max(min_size, math.floor(x + w + 0.5) - left),
        math.max(min_size, math.floor(y + h + 0.5) - top)
end

local function draw_buff_cell_frame(panel, x, y, w, h, alpha, layer)
    local left, top, width, height = align_buff_cell_rect(x, y, w, h)

    panel:gradient({
        x = left,
        y = top,
        w = width,
        h = height,
        orientation = "vertical",
        gradient_points = {
            0, Color.black:with_alpha(0),
            0.45, Color.black:with_alpha(alpha * 0.3),
            1, Color.black:with_alpha(alpha * 0.82),
        },
        layer = layer,
    })

    -- Une seule table de points partagée par les deux montants : ils portent
    -- exactement le même dégradé et `KH:draw` ne doit pas allouer deux fois.
    local edge_points = {
        0,    HUD_ACCENT_COLOR:with_alpha(alpha * BUFF_CELL_EDGE_ALPHA_TOP),
        0.55, HUD_ACCENT_COLOR:with_alpha(alpha * BUFF_CELL_EDGE_ALPHA_MID),
        1,    HUD_ACCENT_COLOR:with_alpha(alpha * BUFF_CELL_EDGE_ALPHA_BOTTOM),
    }
    panel:gradient({
        x = left,
        y = top,
        w = BUFF_CELL_LINE_WIDTH,
        h = height,
        orientation = "vertical",
        gradient_points = edge_points,
        layer = layer + 1,
    })
    panel:gradient({
        x = left + width - BUFF_CELL_LINE_WIDTH,
        y = top,
        w = BUFF_CELL_LINE_WIDTH,
        h = height,
        orientation = "vertical",
        gradient_points = edge_points,
        layer = layer + 1,
    })
    panel:gradient({
        x = left,
        y = top + height - BUFF_CELL_LINE_WIDTH,
        w = width,
        h = BUFF_CELL_LINE_WIDTH,
        orientation = "horizontal",
        gradient_points = {
            0,   HUD_ACCENT_COLOR:with_alpha(alpha * BUFF_CELL_FOOTER_ALPHA_END),
            0.5, HUD_ACCENT_COLOR:with_alpha(alpha * BUFF_CELL_EDGE_ALPHA_BOTTOM),
            1,   HUD_ACCENT_COLOR:with_alpha(alpha * BUFF_CELL_FOOTER_ALPHA_END),
        },
        layer = layer + 1,
    })
end

-- Trace la partie encore active du contour d'un buff temporaire. Le parcours
-- commence au milieu du bord supérieur et avance dans le sens horaire ; son
-- extrémité recule donc continûment à mesure que le timer approche de zéro.
-- Ce contour est le seul trait autorisé à franchir le haut de la cellule :
-- le cadre statique, lui, reste à trois côtés.
local function append_progress_segment(points, remaining_length, x1, y1, x2, y2, segment_length)
    if remaining_length <= 0 or segment_length <= 0 then return remaining_length end

    local visible_length = math.min(remaining_length, segment_length)
    local ratio = visible_length / segment_length
    if #points == 0 then
        points[1] = Vector3(x1, y1, 0)
    end
    points[#points + 1] = Vector3(
        x1 + (x2 - x1) * ratio,
        y1 + (y2 - y1) * ratio,
        0
    )
    return remaining_length - visible_length
end

local function draw_timed_buff_progress(panel, x, y, w, h, progress, color, alpha, layer)
    progress = clamp(tonumber(progress) or 0, 0, 1)
    if progress <= 0 then return end

    -- Même arrondi que le cadre statique : les deux contours se superposent.
    x, y, w, h = align_buff_cell_rect(x, y, w, h)

    local line_width = clamp(math.min(w, h) * 0.055, 2, 3)
    local remaining_length = (w * 2 + h * 2) * progress
    local half_w = w * 0.5
    local points = {}
    remaining_length = append_progress_segment(
        points, remaining_length, x + half_w, y, x + w, y, half_w
    )
    remaining_length = append_progress_segment(
        points, remaining_length, x + w, y, x + w, y + h, h
    )
    remaining_length = append_progress_segment(
        points, remaining_length, x + w, y + h, x, y + h, w
    )
    remaining_length = append_progress_segment(
        points, remaining_length, x, y + h, x, y, h
    )
    append_progress_segment(
        points, remaining_length, x, y, x + half_w, y, half_w
    )

    -- Deux polylignes seulement par buff : un halo discret et le trait net.
    panel:polyline({
        points = points,
        line_width = line_width + 2,
        color = color,
        alpha = alpha * 0.2,
        layer = layer,
    })
    panel:polyline({
        points = points,
        line_width = line_width,
        color = color,
        alpha = alpha,
        layer = layer + 1,
    })
end

-- ═══════════════════════════════════════════════════
-- État visuel adaptatif d'une cellule de buff
-- ═══════════════════════════════════════════════════
-- Quatre états seulement, résolus une seule fois par buff rendu :
--
--   persistent : aucun timer connu. Teinte stable, aucune progression
--                simulée, aucune pulsation.
--   normal     : buff temporaire loin de son expiration. Il conserve sa
--                propre couleur de catalogue, y compris la teinte de debuff.
--   warning    : approche de l'expiration. Ambre, opacité relevée.
--   critical   : expiration imminente. Rouge, opacité relevée et pulsation
--                retenue.
--
-- `accent_color` teinte le contour périmétrique animé et n'est renseigné que
-- pour un buff temporaire : un indicateur permanent n'en reçoit jamais. Le
-- cadre statique de la cellule, lui, ne fait pas partie de cet état — il
-- garde toujours `HUD_ACCENT_COLOR` et sa silhouette à trois côtés.
--
-- Les seuils combinent une fraction de la durée et des bornes en secondes :
-- un buff de 60 s ne devient donc pas ambre pendant vingt secondes, et un
-- buff de 3 s garde malgré tout une phase d'alerte lisible.
local BUFF_WARNING_RATIO        = 0.35
local BUFF_WARNING_MIN_SECONDS  = 1.5
local BUFF_WARNING_MAX_SECONDS  = 5
local BUFF_CRITICAL_RATIO       = 0.15
local BUFF_CRITICAL_MIN_SECONDS = 0.75
local BUFF_CRITICAL_MAX_SECONDS = 2

-- `math.sin` reçoit des radians. Une fréquence de 1,6 Hz reste perceptible
-- sans produire le clignotement agressif d'une alerte à haute fréquence.
local BUFF_CRITICAL_PULSE_HZ    = 1.6
local BUFF_CRITICAL_PULSE_DEPTH = 0.16

local BUFF_WARNING_COLOR  = Color(1, 0.68, 0.16)
local BUFF_CRITICAL_COLOR = Color(1, 0.26, 0.22)

-- Table de travail réutilisée : `KH:draw` reconstruit le panneau vingt fois
-- par seconde et ne doit pas allouer une table par buff affiché. Sa durée de
-- vie se limite à une itération de la boucle de rendu.
local buff_state = {
    remaining    = nil,
    progress     = nil,
    accent_color = nil,
    timer_color  = nil,
    emphasis     = 0,
    alpha_scale  = 1,
}

local function resolve_buff_state(buff, t)
    local state = buff_state
    local duration = tonumber(buff.duration)

    -- L'aperçu de debug fige un temps restant afin de présenter chaque état
    -- assez longtemps pour l'inspecter ; le jeu n'utilise que `t_end`.
    local remaining = tonumber(buff.preview_remaining)
    if not remaining and buff.t_end then
        remaining = math.max(0, buff.t_end - t)
    end

    state.remaining    = remaining
    state.progress     = nil
    state.accent_color = nil
    state.timer_color  = nil
    state.emphasis     = 0
    state.alpha_scale  = 1

    if not remaining or not duration or duration <= 0 then
        -- Indicateur permanent : ni progression, ni contour périmétrique, ni
        -- urgence inventées.
        return state
    end

    state.progress = clamp(remaining / duration, 0, 1)
    -- Un debuff temporaire reste identifiable par sa propre couleur tant
    -- qu'aucune urgence ne doit primer.
    state.accent_color = buff.color or HUD_ACCENT_COLOR

    local critical_at = clamp(
        duration * BUFF_CRITICAL_RATIO,
        BUFF_CRITICAL_MIN_SECONDS,
        BUFF_CRITICAL_MAX_SECONDS
    )
    local warning_at = clamp(
        duration * BUFF_WARNING_RATIO,
        BUFF_WARNING_MIN_SECONDS,
        BUFF_WARNING_MAX_SECONDS
    )

    if remaining <= critical_at then
        state.accent_color = BUFF_CRITICAL_COLOR
        state.timer_color  = BUFF_CRITICAL_COLOR
        state.emphasis     = 1
        local pulse = 0.5 + 0.5 * math.sin(t * math.pi * 2 * BUFF_CRITICAL_PULSE_HZ)
        state.alpha_scale = 1 - BUFF_CRITICAL_PULSE_DEPTH * (1 - pulse)
    elseif remaining <= warning_at then
        state.accent_color = BUFF_WARNING_COLOR
        state.timer_color  = BUFF_WARNING_COLOR
        state.emphasis     = 0.55
    end

    return state
end

local function draw_killfeed_card_frame(panel, x, y, w, h, color, alpha, layer)
    panel:gradient({
        x = x,
        y = y + 1,
        w = w,
        h = h - 2,
        orientation = "horizontal",
        gradient_points = {
            0, Color.black:with_alpha(alpha * 0.68),
            0.72, Color.black:with_alpha(alpha * 0.42),
            1, Color.black:with_alpha(alpha * 0.05),
        },
        layer = layer,
    })
    panel:rect({
        x = x, y = y + 2, w = 2, h = h - 4,
        color = color, alpha = alpha * 0.9, layer = layer + 1,
    })
    panel:rect({
        x = x + 2, y = y + 1, w = w - 4, h = 1,
        color = color, alpha = alpha * 0.5, layer = layer + 1,
    })
    panel:rect({
        x = x + 2, y = y + h - 2, w = w - 4, h = 1,
        color = color, alpha = alpha * 0.5, layer = layer + 1,
    })
    panel:rect({
        x = x + w - 2, y = y + 2, w = 2, h = h - 4,
        color = color, alpha = alpha * 0.9, layer = layer + 1,
    })
end

-- ── Médaille du killfeed ──
-- Silhouette volontairement distincte des cartes de kills et du bandeau
-- supérieur : montants latéraux pleine hauteur et ruban centré sur les deux
-- bords, au lieu des trois segments décalés du cadre tactique. Elle occupe la
-- largeur du bandeau mais reste à la hauteur d'une rangée de killfeed.
-- Ce cadre est partagé par toutes les familles de médailles : seul le contenu de
-- la zone intérieure change, une carte pouvant précéder son texte d'une icône.
local MEDAL_POST_W = 3
local MEDAL_RIBBON_RATIO = 0.52
-- Écart entre la médaille et la rangée des noms qui la suit.
local MEDAL_ROW_GAP = 6
-- Séparer d'un demi-pixel la médaille du prolongement inférieur du bandeau :
-- les deux accents ne se confondent plus lorsque les deux niveaux sont actifs.
local MEDAL_TOP_GAP = 0.5
-- Trois flèches décoratives réduites : elles rappellent les annonces sans
-- reprendre les banques de progression du multikill.
local MEDAL_CHEVRON_STYLE = { arrow_w = 6, arrow_h = 9, gap = 3 }
local MEDAL_CHEVRON_GROUP_W = SPECIAL_CHEVRON_SLOTS
    * MEDAL_CHEVRON_STYLE.arrow_w
    + (SPECIAL_CHEVRON_SLOTS - 1) * MEDAL_CHEVRON_STYLE.gap
local MEDAL_CHEVRON_MARGIN = 13
local MEDAL_CHEVRON_TEXT_GAP = 6
-- Icône optionnelle précédant le texte, dimensionnée sur la hauteur réelle de la
-- carte pour rester à l'intérieur du ruban quelle que soit la taille du HUD.
local MEDAL_ICON_TEXT_GAP = 6
local MEDAL_ICON_H_RATIO = 0.6
local MEDAL_ICON_MIN = 12
local MEDAL_ICON_MAX = 24

--- Un bord de la médaille : ruban lumineux au centre, prolongé par un filet
--- discret jusqu'aux montants. Le contraste centre/bords donne la lecture
--- « ruban » sans refermer la carte comme un cadre plein.
local function draw_medal_edge(panel, x, y, w, color, alpha, layer)
    local ribbon_w = w * MEDAL_RIBBON_RATIO
    local ribbon_x = x + (w - ribbon_w) * 0.5

    panel:rect({
        x = ribbon_x, y = y - 1, w = ribbon_w, h = 3,
        color = color, alpha = alpha * 0.2, layer = layer,
    })
    panel:rect({
        x = ribbon_x, y = y, w = ribbon_w, h = 1,
        color = color, alpha = alpha, layer = layer + 1,
    })
    panel:rect({
        x = x + MEDAL_POST_W,
        y = y,
        w = math.max(0, ribbon_x - x - MEDAL_POST_W),
        h = 1,
        color = color, alpha = alpha * 0.32, layer = layer + 1,
    })
    panel:rect({
        x = ribbon_x + ribbon_w,
        y = y,
        w = math.max(0, x + w - MEDAL_POST_W - ribbon_x - ribbon_w),
        h = 1,
        color = color, alpha = alpha * 0.32, layer = layer + 1,
    })
end

local function draw_medal_frame(panel, x, y, w, h, color, alpha, layer)
    -- Fond symétrique : la médaille se lit d'un bloc, alors que les cartes de
    -- kills gardent leur dégradé asymétrique orienté vers la droite.
    panel:gradient({
        x = x, y = y + 1, w = w, h = h - 2,
        orientation = "horizontal",
        gradient_points = {
            0,    Color.black:with_alpha(alpha * 0.14),
            0.26, Color.black:with_alpha(alpha * 0.7),
            0.5,  Color.black:with_alpha(alpha * 0.82),
            0.74, Color.black:with_alpha(alpha * 0.7),
            1,    Color.black:with_alpha(alpha * 0.14),
        },
        layer = layer,
    })

    panel:rect({
        x = x, y = y, w = MEDAL_POST_W, h = h,
        color = color, alpha = alpha, layer = layer + 1,
    })
    panel:rect({
        x = x + w - MEDAL_POST_W, y = y, w = MEDAL_POST_W, h = h,
        color = color, alpha = alpha, layer = layer + 1,
    })

    draw_medal_edge(panel, x, y, w, color, alpha, layer + 1)
    draw_medal_edge(panel, x, y + h - 1, w, color, alpha, layer + 1)
end

local TEXT_GLOW_OFFSETS = {
    { -1, 0 }, { 1, 0 }, { 0, -1 }, { 0, 1 },
}

local function draw_glowing_text(panel, label, font, font_size, color, x, y, w, h, alpha, layer)
    panel:text({
        text = label,
        font = font,
        font_size = font_size,
        color = Color.black,
        align = "center",
        vertical = "center",
        x = x + 1,
        y = y + 1,
        w = w,
        h = h,
        layer = layer,
        alpha = alpha * 0.9,
    })
    for _, offset in ipairs(TEXT_GLOW_OFFSETS) do
        panel:text({
            text = label,
            font = font,
            font_size = font_size,
            color = color,
            align = "center",
            vertical = "center",
            x = x + offset[1],
            y = y + offset[2],
            w = w,
            h = h,
            layer = layer,
            alpha = alpha * 0.16,
        })
    end
    panel:text({
        text = label,
        font = font,
        font_size = font_size,
        color = color,
        align = "center",
        vertical = "center",
        x = x,
        y = y,
        w = w,
        h = h,
        layer = layer + 1,
        alpha = alpha,
    })
end

-- ═══════════════════════════════════════════════════
-- API publique : ajouter/retirer des buffs
-- ═══════════════════════════════════════════════════
function KH:add_buff(buff_id, icon_data, duration, raw_upgrade_id, persistent, is_debuff, value_text, stack_text)
    if not self.settings or not self.settings.enable_buffs then return end

    -- Résoudre le vrai buff_id depuis l'upgrade
    local resolved_id = buff_id
    if raw_upgrade_id and KH.UPGRADE_TO_BUFF and KH.UPGRADE_TO_BUFF[raw_upgrade_id] then
        resolved_id = KH.UPGRADE_TO_BUFF[raw_upgrade_id]
    end

    -- Vérifier si ce buff est visible dans les settings
    if not self:is_buff_visible(resolved_id) then return end

    local dur = tonumber(duration)
    if not persistent then
        dur = dur or DEFAULT_TEMPORARY_BUFF_DURATION
    end
    local t = now()
    local definition = KH.BUFF_MAP and KH.BUFF_MAP[resolved_id]

    -- Un buff rafraîchi garde sa position dans la rangée (order_t d'origine),
    -- seuls son timer et son fondu (start_t) repartent de zéro
    local existing = self._buffs[resolved_id]

    self._buffs[resolved_id] = {
        id       = resolved_id,
        icon     = icon_data or icon_for_buff(resolved_id),
        color    = color_for_buff(resolved_id, is_debuff),
        category = definition and definition.category,
        value_text = value_text,
        stack_text = stack_text,
        is_debuff = is_debuff == true,
        order_t  = existing and existing.order_t or t,
        start_t  = t,
        duration = dur,
        t_end    = not persistent and dur and (t + dur) or nil,
        persistent = persistent == true,
    }
end

function KH:remove_buff(buff_id)
    -- Essayer aussi le buff résolu
    self._buffs[buff_id] = nil
    if KH.UPGRADE_TO_BUFF and KH.UPGRADE_TO_BUFF[buff_id] then
        self._buffs[KH.UPGRADE_TO_BUFF[buff_id]] = nil
    end
end

-- ═══════════════════════════════════════════════════
-- Sources de buffs et pont optionnel VanillaHUD+
-- ═══════════════════════════════════════════════════
local function application_time()
    local ok, t = pcall(function()
        return Application:time()
    end)
    return ok and tonumber(t) or now()
end

local function source_remaining(data)
    if type(data) ~= "table" then
        return nil, false
    end

    local app_t = application_time()
    local expire_t = tonumber(data.expire_t)
    if expire_t then
        return math.max(0, expire_t - app_t), true
    end

    local duration = tonumber(data.duration)
    if duration then
        local start_t = tonumber(data.t)
        if start_t then
            return math.max(0, start_t + duration - app_t), true
        end
        return math.max(0, duration), true
    end

    if type(data.stacks) == "table" then
        local latest_expire_t
        for _, stack in ipairs(data.stacks) do
            local stack_expire_t = type(stack) == "table" and tonumber(stack.expire_t)
            if stack_expire_t and (not latest_expire_t or stack_expire_t > latest_expire_t) then
                latest_expire_t = stack_expire_t
            end
        end
        if latest_expire_t then
            return math.max(0, latest_expire_t - app_t), true
        end
    end

    return nil, false
end

local function player_upgrade_value(category, upgrade, fallback)
    local ok, value = pcall(function()
        return managers.player and managers.player:upgrade_value(category, upgrade, fallback)
    end)
    return ok and value ~= nil and value or fallback
end

local function largest_source_value(sources)
    local result
    for _, source in pairs(sources) do
        if not source.is_calculated then
            local value = tonumber(source.value)
            if value and (not result or value > result) then
                result = value
            end
        end
    end
    return result
end

local function source_stack_count(source)
    local count = tonumber(source and source.stack_count)
    if count then return math.floor(count) end
    if source and type(source.stacks) == "table" then return #source.stacks end
    return nil
end

local function largest_stack_count(sources)
    local result
    for _, source in pairs(sources) do
        local count = source_stack_count(source)
        if count and (not result or count > result) then
            result = count
        end
    end
    return result
end

local function compact_number(value)
    local text = string.format("%.2f", value)
    text = string.gsub(text, "(%..-)0+$", "%1")
    return string.gsub(text, "%.$", "")
end

local function current_player_damage()
    local ok, player_damage = pcall(function()
        local player = managers.player and managers.player:player_unit()
        return alive(player) and player:character_damage()
    end)
    return ok and player_damage or nil
end

local function passive_health_regen_source_value(source)
    local value = source and tonumber(source.value)
    if not value then return nil end

    -- VanillaHUD+ exprime la régénération de l'équipier en points de santé
    -- internes, contrairement aux autres sources qui utilisent déjà un ratio.
    if source.source_id == "crew_health_regen" then
        local player_damage = current_player_damage()
        local ok, max_health = pcall(function()
            return player_damage and player_damage:_max_health()
        end)
        max_health = ok and tonumber(max_health) or nil
        if not max_health or max_health <= 0 then return nil end
        return value / (max_health * 10)
    end

    return value
end

local function equipped_weapon_context()
    local ok, ignore_upgrades, categories = pcall(function()
        local player = managers.player and managers.player:player_unit()
        local inventory = alive(player) and player:inventory()
        local weapon = inventory and inventory:equipped_unit()
        local base = alive(weapon) and weapon:base()
        local tweak = base and base:weapon_tweak_data()
        return tweak and tweak.ignore_damage_upgrades == true, tweak and tweak.categories
    end)
    if not ok or type(categories) ~= "table" then return nil, nil end

    local category_set = {}
    for _, category in ipairs(categories) do
        category_set[category] = true
    end
    return ignore_upgrades, category_set
end

local function source_applies_to_weapon(source_id, categories)
    if source_id == "overkill" then
        return categories.shotgun or categories.saw
    elseif source_id == "overkill_aced" then
        return not categories.shotgun and not categories.saw
    elseif source_id == "berserker" then
        return categories.saw == true
    elseif source_id == "berserker_aced" then
        return categories.saw ~= true
    end
    return true
end

local function health_ratio_damage_multiplier(source_id, value)
    if source_id == "berserker" then
        return 1 + value * (tonumber(player_upgrade_value(
            "player", "melee_damage_health_ratio_multiplier", 0
        )) or 0)
    elseif source_id == "berserker_aced" then
        return 1 + value * (tonumber(player_upgrade_value(
            "player", "damage_health_ratio_multiplier", 0
        )) or 0)
    end
    return value
end

local function damage_increase_text(sources)
    local ignore_upgrades, categories = equipped_weapon_context()
    if not categories then return nil end
    if ignore_upgrades then return "(0%)" end

    local multiplier = 1
    local has_value = false
    for _, source in pairs(sources) do
        local value = tonumber(source.value)
        if value and source_applies_to_weapon(source.source_id, categories) then
            multiplier = multiplier * health_ratio_damage_multiplier(source.source_id, value)
            has_value = true
        end
    end
    return has_value and string.format("%+.0f%%", (multiplier - 1) * 100) or nil
end

local function melee_damage_increase_text(sources)
    local multiplier = 1
    local has_value = false
    for _, source in pairs(sources) do
        local value = tonumber(source.value)
        if value then
            multiplier = multiplier * health_ratio_damage_multiplier(source.source_id, value)
            has_value = true
        end
    end
    return has_value and ("x" .. compact_number(multiplier)) or nil
end

local function maniac_damage_multiplier(value)
    local player_damage = current_player_damage()
    if not player_damage then return nil end

    local ok, current_armor, max_armor, max_health = pcall(function()
        return player_damage:get_real_armor(), player_damage:_max_armor(), player_damage:_max_health()
    end)
    if not ok then return nil end
    current_armor = tonumber(current_armor)
    if not current_armor then return nil end
    local maximum = current_armor > 0 and tonumber(max_armor) or tonumber(max_health)
    if not maximum or maximum <= 0 then return nil end
    return 1 - value / (maximum * 10)
end

local function damage_reduction_source_multiplier(source)
    local value = tonumber(source.value)
    if not value then return nil end

    if source.source_id == "chico_injector" then
        local player_damage = current_player_damage()
        local ok, health_ratio = pcall(function()
            return player_damage and player_damage:health_ratio()
        end)
        local low_health = player_upgrade_value("player", "chico_injector_low_health_multiplier", nil)
        local threshold = type(low_health) == "table" and tonumber(low_health[1])
        local bonus = type(low_health) == "table" and tonumber(low_health[2])
        if ok and tonumber(health_ratio) and threshold and bonus and health_ratio < threshold then
            value = value + bonus
        end
        return 1 - value
    elseif source.source_id == "frenzy" then
        return 1 - value
    elseif source.source_id == "maniac" then
        return maniac_damage_multiplier(value)
    end

    return value
end

local function damage_reduction_text(sources)
    local multiplier = 1
    local has_value = false
    for _, source in pairs(sources) do
        local value = damage_reduction_source_multiplier(source)
        if value then
            multiplier = multiplier * value
            has_value = true
        end
    end
    local reduction = clamp(1 - multiplier, 0, 1)
    return has_value and string.format("-%.0f%%", reduction * 100) or nil
end

local function calculated_base_dodge(include_sicario)
    local value = tonumber(tweak_data and tweak_data.player
        and tweak_data.player.damage and tweak_data.player.damage.DODGE_INIT) or 0

    local ok, calculated = pcall(function()
        local pm = managers.player
        local armor_id = managers.blackmarket and managers.blackmarket:equipped_armor(true, true)
        local armor_upgrade = armor_id and tostring(armor_id) .. "_dodge_addend"
        local risk_upgrade = pm:upgrade_value("player", "detection_risk_add_dodge_chance", 0)
        return (pm:body_armor_value("dodge") or 0)
            + (pm:upgrade_value("player", "passive_dodge_chance", 0) or 0)
            + (armor_upgrade and pm:upgrade_value("player", armor_upgrade, 0) or 0)
            + (pm:upgrade_value("player", "tier_dodge_chance", 0) or 0)
            + (pm:get_value_from_risk_upgrade(risk_upgrade) or 0)
            + (pm:upgrade_value("team", "crew_add_dodge", 0) or 0)
            + (include_sicario and pm:upgrade_value("player", "sicario_multiplier", 0) or 0)
    end)
    return math.max(0, value + (ok and tonumber(calculated) or 0))
end

local function total_dodge_chance_text(sources)
    local has_sicario_source = false
    local has_smoke_source = false
    for _, source in pairs(sources) do
        has_sicario_source = has_sicario_source or source.source_id == "sicario_dodge"
        has_smoke_source = has_smoke_source or source.source_id == "smoke_screen_grenade"
    end

    local value = calculated_base_dodge(not has_sicario_source)
    for _, source in pairs(sources) do
        if not source.is_calculated then
            value = value + (tonumber(source.value) or 0)
        end
    end

    if has_smoke_source then
        local smoke_dodge = tonumber(tweak_data and tweak_data.projectiles
            and tweak_data.projectiles.smoke_screen_grenade
            and tweak_data.projectiles.smoke_screen_grenade.dodge_chance) or 0
        value = 1 - (1 - value) * (1 - smoke_dodge)
    end

    return string.format("%.0f%%", math.max(value * 100, 0))
end

local BUFF_VALUE_FORMATTERS = {
    percent = function(sources)
        local value = largest_source_value(sources)
        return value and string.format("%.0f%%", value * 100) or nil
    end,
    multiplier_percent = function(sources)
        local value = largest_source_value(sources)
        return value and string.format("%+.0f%%", (value - 1) * 100) or nil
    end,
    multiplier = function(sources)
        local value = largest_source_value(sources)
        return value and ("x" .. compact_number(value)) or nil
    end,
    negative_number = function(sources)
        local value = largest_source_value(sources)
        return value and string.format("-%.0f", math.abs(value)) or nil
    end,
    negative_number_1 = function(sources)
        local value = largest_source_value(sources)
        return value and string.format("-%.1f", math.abs(value)) or nil
    end,
    damage_increase = damage_increase_text,
    damage_reduction = damage_reduction_text,
    melee_damage_increase = melee_damage_increase_text,
    passive_health_regen = function(sources)
        local total = 0
        local has_value = false

        for _, source in pairs(sources) do
            local value = passive_health_regen_source_value(source)
            if value then
                total = total + value
                has_value = true
            end
        end

        return has_value and string.format("%.1f%%", total * 100) or nil
    end,
    total_dodge_chance = total_dodge_chance_text,
}

local function format_buff_value(buff_id, sources)
    local definition = KH.BUFF_MAP and KH.BUFF_MAP[buff_id]
    local formatter = definition and BUFF_VALUE_FORMATTERS[definition.value_format]
    local value_text = formatter and formatter(sources) or nil
    local stack_count = largest_stack_count(sources)
    local stack_text
    if definition and definition.stack_format == "biker_charges" and stack_count then
        local maximum = tonumber(tweak_data and tweak_data.upgrades
            and tweak_data.upgrades.wild_max_triggers_per_time) or 0
        stack_text = "x" .. tostring(math.max(0, maximum - stack_count))
    elseif definition and definition.show_stack_count and stack_count and stack_count > 0 then
        stack_text = "x" .. tostring(stack_count)
    end
    return value_text, stack_text
end

function KH:_refresh_source_target(buff_id)
    local sources = self._buff_sources and self._buff_sources[buff_id]
    if not sources or not next(sources) then
        self:remove_buff(buff_id)
        return
    end

    local has_persistent_source = false
    local persistent_sources_are_debuffs = true
    local max_remaining
    local max_remaining_is_debuff = false
    local value_text, stack_text = format_buff_value(buff_id, sources)
    for _, source in pairs(sources) do
        local remaining, timed = source_remaining(source)
        if timed then
            local source_is_debuff = source.is_debuff == true
            if remaining > 0 and (not max_remaining
                or remaining > max_remaining
                or (remaining == max_remaining and max_remaining_is_debuff and not source_is_debuff)) then
                max_remaining = remaining
                max_remaining_is_debuff = source_is_debuff
            end
        else
            has_persistent_source = true
            if not source.is_debuff then
                persistent_sources_are_debuffs = false
            end
        end
    end

    if has_persistent_source then
        self:add_buff(buff_id, nil, nil, nil, true, persistent_sources_are_debuffs, value_text, stack_text)
    elseif max_remaining and max_remaining > 0 then
        self:add_buff(buff_id, nil, max_remaining, nil, false, max_remaining_is_debuff, value_text, stack_text)
    else
        self:remove_buff(buff_id)
    end
end

local DYNAMIC_VALUE_BUFFS = {
    "damage_increase",
    "damage_reduction",
    "melee_damage_increase",
    "passive_health_regen",
    "total_dodge_chance",
}

local EQUIPPED_SKILL_COUNTER_BUFFS = {}
for buff_id, definition in pairs(KH.BUFF_MAP or {}) do
    if definition.persistent_counter then
        table.insert(EQUIPPED_SKILL_COUNTER_BUFFS, buff_id)
    end
end
table.sort(EQUIPPED_SKILL_COUNTER_BUFFS)

local function equipped_skill_counter_text(definition)
    if not definition or not definition.skill_id or not definition.persistent_counter then
        return false, nil
    end

    local ok_step, skill_step = pcall(function()
        return managers.skilltree and managers.skilltree:skill_step(definition.skill_id)
    end)
    skill_step = ok_step and tonumber(skill_step) or nil
    if skill_step == nil then
        -- L'état n'est pas encore disponible : conserver l'entrée précédente
        -- plutôt que de faire clignoter l'icône pendant le chargement.
        return nil, nil
    end
    if skill_step < 1 then
        return false, nil
    end

    if definition.persistent_counter == "local_minions" then
        local ok_count, count = pcall(function()
            return managers.player and managers.player:num_local_minions()
        end)
        count = ok_count and tonumber(count) or nil
        if count == nil then return nil, nil end

        local maximum_definition = definition.counter_max_upgrade or {}
        local minimum = tonumber(maximum_definition.minimum) or 0
        local ok_maximum, maximum = pcall(function()
            return managers.player and managers.player:upgrade_value(
                maximum_definition.category,
                maximum_definition.upgrade,
                minimum
            )
        end)
        maximum = ok_maximum and tonumber(maximum) or minimum
        maximum = math.max(minimum, math.floor(maximum or minimum))
        return true, tostring(math.max(0, math.floor(count))) .. "/" .. tostring(maximum)
    end

    return false, nil
end

function KH:RefreshEquippedSkillCounters()
    if self._debug_preview_active then return end

    for _, buff_id in ipairs(EQUIPPED_SKILL_COUNTER_BUFFS) do
        local definition = KH.BUFF_MAP and KH.BUFF_MAP[buff_id]
        local visible = self:is_buff_visible(buff_id)
        local equipped, value_text = equipped_skill_counter_text(definition)
        local existing = self._buffs[buff_id]

        if visible and equipped == true then
            if not existing then
                self:add_buff(buff_id, nil, nil, nil, true, false, value_text)
                existing = self._buffs[buff_id]
            end
            if existing then
                -- L'indicateur représente l'état équipé, pas une durée : un
                -- évènement actif ne doit donc pas lui ajouter de timer.
                existing.value_text = value_text
                existing.duration = nil
                existing.t_end = nil
                existing.persistent = true
                existing._equipped_skill_counter = true
            end
        elseif not visible or equipped == false then
            self:remove_buff(buff_id)
        end
    end
end

local function equipped_pocket_ecm_amount()
    local ok, amount = pcall(function()
        local session = managers.network and managers.network:session()
        local peer = session and session:local_peer()
        local peer_id = peer and peer:id()
        return peer_id and managers.player and managers.player:get_grenade_amount(peer_id)
    end)
    amount = ok and tonumber(amount) or nil
    return amount and math.max(0, math.floor(amount)) or nil
end

local function pocket_ecm_cooldown_remaining()
    local ok, remaining = pcall(function()
        local player_manager = managers and managers.player
        if not (player_manager and player_manager.get_timer_remaining) then return nil end
        return player_manager:get_timer_remaining("replenish_grenades")
    end)
    return ok and tonumber(remaining) or nil
end

function KH:RefreshHackerPocketECMStatus()
    if self._debug_preview_active then return end

    local deck_entry = equipped_perk_deck_entry(self)
    local _, base_specialization_id = current_perk_deck_ids()
    local grenade_ok, grenade_id = pcall(function()
        return managers.blackmarket and managers.blackmarket:equipped_grenade()
    end)
    local hacker_equipped = base_specialization_id == HACKER_SPECIALIZATION_ID
        and grenade_ok and grenade_id == POCKET_ECM_GRENADE_ID

    if not hacker_equipped then
        deck_entry.value_text = nil
        self:remove_buff(POCKET_ECM_COOLDOWN_ID)
        return
    end

    local amount = equipped_pocket_ecm_amount()
    deck_entry.value_text = amount and ("x" .. tostring(amount)) or nil

    local remaining = pocket_ecm_cooldown_remaining()
    if not self:is_buff_visible(POCKET_ECM_COOLDOWN_ID)
            or not remaining or remaining <= 0 then
        self:remove_buff(POCKET_ECM_COOLDOWN_ID)
        return
    end

    local t = now()
    local existing = self._buffs[POCKET_ECM_COOLDOWN_ID]
    if not existing then
        self:add_buff(POCKET_ECM_COOLDOWN_ID, nil, remaining, nil, false, true)
        return
    end

    -- Une nouvelle recharge peut démarrer immédiatement après la précédente
    -- lorsqu'il manque encore une charge. Réinitialiser alors la progression,
    -- mais conserver la position fixe de la cellule.
    local previous_remaining = existing.t_end and math.max(0, existing.t_end - t) or 0
    if remaining > previous_remaining + 1 then
        existing.start_t = t
        existing.duration = remaining
    end
    existing.t_end = t + remaining
    existing.is_debuff = true
    existing.color = color_for_buff(POCKET_ECM_COOLDOWN_ID, true)
end

function KH:RefreshCalculatedBuffValues()
    if self._debug_preview_active then return end

    local buff_id = "total_dodge_chance"
    local source_key = "calculated:base_dodge"
    local sources = self._buff_sources[buff_id]
    local base_dodge = calculated_base_dodge(true)
    local has_calculated_source = sources and sources[source_key] ~= nil
    local source_changed = false

    if base_dodge > 0 and not has_calculated_source then
        self._buff_sources[buff_id] = sources or {}
        self._buff_sources[buff_id][source_key] = {
            source_id = "base_dodge",
            is_calculated = true,
            is_debuff = false,
        }
        source_changed = true
    elseif base_dodge <= 0 and has_calculated_source then
        sources[source_key] = nil
        if not next(sources) then self._buff_sources[buff_id] = nil end
        source_changed = true
    end

    if source_changed then
        self:_refresh_source_target(buff_id)
    end

    -- Ces valeurs dépendent aussi de l'arme équipée, de la santé ou de
    -- l'armure. Les recalculer à faible fréquence sans recréer les entrées
    -- conserve leur ordre et leur timer.
    for _, dynamic_buff_id in ipairs(DYNAMIC_VALUE_BUFFS) do
        local dynamic_sources = self._buff_sources[dynamic_buff_id]
        local buff = self._buffs[dynamic_buff_id]
        if dynamic_sources and buff then
            buff.value_text, buff.stack_text = format_buff_value(dynamic_buff_id, dynamic_sources)
        end
    end
end

function KH:handle_buff_event(event, source_id, data, source_type)
    if not source_id or not KH.GetBuffTargets then return end

    local targets = KH.GetBuffTargets(source_id)
    if #targets == 0 then return end

    source_type = source_type or "buff"
    local source_key = tostring(source_type) .. ":" .. tostring(source_id)

    if event == "deactivate" then
        local old_targets = self._source_targets[source_key] or targets
        for _, buff_id in ipairs(old_targets) do
            local sources = self._buff_sources[buff_id]
            if sources then
                sources[source_key] = nil
                if not next(sources) then
                    self._buff_sources[buff_id] = nil
                end
            end
            self:_refresh_source_target(buff_id)
        end
        self._source_targets[source_key] = nil
        return
    end

    local activates = event == "activate"
        or event == "set_duration"
        or event == "add_timed_stack"
        or event == "set_data"

    if not activates and not self._source_targets[source_key] then
        return
    end

    self._source_targets[source_key] = targets
    for _, buff_id in ipairs(targets) do
        self._buff_sources[buff_id] = self._buff_sources[buff_id] or {}
        local source = self._buff_sources[buff_id][source_key] or {}
        if type(data) == "table" then
            for key, value in pairs(data) do
                source[key] = value
            end
            if data.duration and not data.t
                and (event == "activate" or event == "set_duration") then
                source.t = application_time()
            end
        end
        if event == "set_value" and (not data or data.value == nil) then
            source.value = nil
        elseif event == "set_stack_count" and (not data or data.stack_count == nil) then
            source.stack_count = nil
        end
        source.source_id = source_id
        source.is_debuff = string.match(tostring(source_id), "_debuff$") ~= nil
        self._buff_sources[buff_id][source_key] = source
        self:_refresh_source_target(buff_id)
    end
end

function KH:SyncGameInfoBuffs()
    if self._debug_preview_active or not (managers and managers.gameinfo) then return end

    local ok_buffs, buffs = pcall(function()
        return managers.gameinfo:get_buffs()
    end)
    if ok_buffs and type(buffs) == "table" then
        for id, data in pairs(buffs) do
            self:handle_buff_event("activate", id, data, "gameinfo_buff")
        end
    end

    local ok_actions, actions = pcall(function()
        return managers.gameinfo:get_player_actions()
    end)
    if ok_actions and type(actions) == "table" then
        for id, data in pairs(actions) do
            self:handle_buff_event("activate", id, data, "gameinfo_action")
        end
    end
    self:RefreshCalculatedBuffValues()
end

function KH:TryRegisterGameInfoBridge()
    if self._gameinfo_bridge_active then return true end
    if not (managers and managers.gameinfo
        and managers.gameinfo.register_listener
        and managers.gameinfo.get_buffs
        and managers.gameinfo.get_player_actions) then
        return false
    end

    local buff_events = {
        "activate", "deactivate", "set_duration", "set_progress",
        "set_stack_count", "add_timed_stack", "remove_timed_stack", "set_value",
    }
    local action_events = { "activate", "deactivate", "set_duration", "set_value", "set_data" }
    local buff_callback = function(event, id, data)
        KH:handle_buff_event(event, id, data, "gameinfo_buff")
    end
    local action_callback = function(event, id, data)
        KH:handle_buff_event(event, id, data, "gameinfo_action")
    end

    local ok, err = pcall(function()
        for _, event in ipairs(buff_events) do
            managers.gameinfo:register_listener("kyohud_buff_bridge", "buff", event, buff_callback)
        end
        for _, event in ipairs(action_events) do
            managers.gameinfo:register_listener("kyohud_action_bridge", "player_action", event, action_callback)
        end
    end)
    if not ok then
        if not self._gameinfo_bridge_error_logged then
            self._gameinfo_bridge_error_logged = true
            log("[KyoHUD] Pont VanillaHUD+ indisponible: " .. tostring(err))
        end
        return false
    end

    -- Remplacer les sources locales déjà observées par l'état de référence du
    -- gestionnaire afin qu'une désactivation future ne laisse rien bloqué.
    self._buff_sources = {}
    self._source_targets = {}
    self._buffs = {}
    self._gameinfo_bridge_active = true
    self._gameinfo_bridge_callbacks = { buff_callback, action_callback }
    self:SyncGameInfoBuffs()
    log("[KyoHUD] Détection complète reliée au gestionnaire de buffs VanillaHUD+.")
    return true
end

function KH:RefreshDetectedBuffs()
    if self._gameinfo_bridge_active then
        self:SyncGameInfoBuffs()
    end
    for buff_id, _ in pairs(self._buff_sources or {}) do
        self:_refresh_source_target(buff_id)
    end
    self:RefreshCalculatedBuffValues()
    self:RefreshEquippedSkillCounters()
end

-- ═══════════════════════════════════════════════════
-- Bandeau prioritaire : affichage courant et file d'attente
-- ═══════════════════════════════════════════════════
local function banner_priority(banner)
    return banner and BANNER_PRIORITIES[banner.kind] or 0
end

function KH:_start_special_banner(t, banner, preview)
    banner.preview = preview == true
    banner.started_t = t
    banner.t_end = t + SPECIAL_KILL_BANNER_DURATION
    self._special_kill_banner = banner
end

--- Rang d'insertion respectant l'ordre décroissant de priorité : la nouvelle
--- annonce se place derrière toutes celles de priorité supérieure ou égale.
--- À priorité égale l'ordre d'arrivée est donc conservé (FIFO stable).
local function banner_queue_insert_index(queue, priority)
    for index = 1, #queue do
        if banner_priority(queue[index]) < priority then
            return index
        end
    end
    return #queue + 1
end

--- Insertion dans la file bornée, maintenue triée boss > dozer. Quand elle est
--- pleine, seule une annonce plus prioritaire entre, à la place de la dernière
--- des moins prioritaires ; une annonce de priorité inférieure ou égale à la
--- plus faible en attente est simplement abandonnée.
function KH:_enqueue_special_banner(banner)
    if not banner then return end

    local queue = self._banner_queue
    if not queue then
        queue = {}
        self._banner_queue = queue
    end

    local priority = banner_priority(banner)

    while #queue >= MAX_BANNER_QUEUE do
        -- La file reste triée : sa dernière entrée est toujours la moins
        -- prioritaire et, à priorité égale, la plus récemment ajoutée.
        if banner_priority(queue[#queue]) >= priority then return end
        table.remove(queue)
    end

    table.insert(queue, banner_queue_insert_index(queue, priority), banner)
end

--- Présente une annonce. Une cible prioritaire prend immédiatement le bandeau
--- et renvoie l'annonce en cours dans la file : rien n'est perdu.
function KH:_show_special_banner(t, banner, preview)
    if not banner then return end

    if preview then
        self:_start_special_banner(t, banner, true)
        return
    end

    local current = self._special_kill_banner
    -- Un aperçu de debug ne bloque jamais une vraie annonce.
    if current and not current.preview then
        if banner_priority(banner) > banner_priority(current) then
            self:_enqueue_special_banner(current)
        else
            self:_enqueue_special_banner(banner)
            return
        end
    end

    self:_start_special_banner(t, banner, false)
end

function KH:_show_dozer_banner(t, preview)
    self._dozer_banner_index = ((self._dozer_banner_index or 0) % #DOZER_BANNER_LABELS) + 1
    self:_show_special_banner(
        t,
        make_special_kill_banner("dozer", self._dozer_banner_index),
        preview == true
    )
end

function KH:_show_boss_banner(t, preview)
    self:_show_special_banner(t, make_special_kill_banner("boss", 1), preview == true)
end

-- ═══════════════════════════════════════════════════
-- Médailles : rangée dédiée du killfeed
-- ═══════════════════════════════════════════════════
-- État strictement séparé du bandeau supérieur : une médaille n'entre jamais en
-- concurrence avec un boss ou un Dozer, et les deux peuvent être visibles en
-- même temps sur deux niveaux distincts.
--
-- Toutes les familles de médailles — séries d'arme, médailles d'évènement et
-- paliers de kills cumulés — partagent ce même niveau, ce même rendu, cette même
-- durée et cette même file FIFO bornée. Seule la construction de la carte
-- diffère.
function KH:_start_medal_card(t, card, preview)
    card.preview = preview == true
    card.started_t = t
    card.t_end = t + MEDAL_CARD_DURATION
    self._medal_card = card
end

--- Présente une médaille déjà construite. Toutes ont le même mérite : celle déjà
--- affichée garde sa place et les suivantes s'enchaînent dans l'ordre d'arrivée.
--- Une médaille de trop est abandonnée plutôt que d'allonger la file : le palier
--- reste acquis, seule son annonce est perdue.
---
--- Un seul kill peut en produire plusieurs — jusqu'à une série d'arme, quelques
--- évènements et un palier cumulé. La borne reste volontairement basse : carte
--- active plus `MAX_MEDAL_QUEUE` places, soit au plus quatre annonces enchaînées
--- d'environ 1,75 s. Allonger la file ferait défiler la rangée bien après le
--- kill qui l'a déclenchée.
function KH:_show_medal_card(t, card, preview)
    if not card then return end

    local queue = self._medal_queue
    if not queue then
        queue = {}
        self._medal_queue = queue
    end

    local current = self._medal_card
    -- Un aperçu de debug remplace tout et ne s'accumule jamais.
    if preview then
        for index = #queue, 1, -1 do queue[index] = nil end
        self:_start_medal_card(t, card, true)
        return
    end

    -- Un aperçu ne bloque pas une vraie médaille.
    if current and not current.preview then
        if #queue < MAX_MEDAL_QUEUE then
            table.insert(queue, card)
        end
        return
    end

    self:_start_medal_card(t, card, false)
end

--- Efface les médailles de la rangée partagée. Sans `kind`, tout disparaît ;
--- avec un `kind`, les autres familles gardent leur carte active et leur place
--- dans la file. Une médaille cumulée survit donc à un reset de séries d'arme.
function KH:_clear_medal_cards(kind)
    local card = self._medal_card
    if card and (not kind or card.kind == kind) then
        self._medal_card = nil
    end

    local queue = self._medal_queue
    if not queue then
        self._medal_queue = {}
        return
    end

    for index = #queue, 1, -1 do
        if not kind or queue[index].kind == kind then
            table.remove(queue, index)
        end
    end
end

--- Compte un kill pour sa famille et renvoie l'indice du palier franchi.
--- `t` est le temps du kill, déjà calculé par `KH:add_kill` : chaque famille
--- entretient son propre timer, calqué sur celui du multikill, et aucune
--- horloge n'est relue ici.
function KH:_register_weapon_family_kill(family, t)
    local definition = weapon_streak_definition(family)
    if not definition then return nil end

    local tiers = definition.tiers
    if not tiers[1] then return nil end

    local streaks = self._weapon_streaks
    if not streaks then
        streaks = {}
        self._weapon_streaks = streaks
    end

    local streak = streaks[family]
    if not streak then
        streak = { count = 0, tier_index = 0 }
        streaks[family] = streak
    end

    -- Repli défensif : un appelant sans temps ne doit pas figer le timer de la
    -- famille. `add_kill` passe toujours son `t` ; `now()` ne sert qu'à ce repli.
    t = tonumber(t) or now()

    -- Timer strictement propre à cette famille : les kills des autres familles
    -- ne le rafraîchissent ni ne le réinitialisent. La borne reste inclusive,
    -- exactement comme la fenêtre du multikill.
    if streak.last_t and (t - streak.last_t) > KILL_COMBO_WINDOW then
        streak.count = 0
        streak.tier_index = 0
    end
    streak.last_t = t
    streak.count = streak.count + 1

    -- Un seul palier peut tomber par kill : on ne compare qu'au palier suivant.
    -- Une fois le maximum annoncé, `next_tier` est nil et la chaîne reste
    -- silencieuse jusqu'à son expiration, qui réarme le premier palier.
    local next_tier = tiers[streak.tier_index + 1]
    if not next_tier or streak.count < next_tier.count then
        return nil
    end

    streak.tier_index = streak.tier_index + 1
    return streak.tier_index
end

--- Compte un kill ennemi dans le total du braquage et renvoie le palier franchi,
--- ou `nil`. Aucun timer n'intervient : le compteur ne fait qu'augmenter et
--- survit à une chute. Le total avançant d'une unité par kill, chaque palier est
--- atteint exactement, et un seul peut tomber par kill.
function KH:_register_heist_kill()
    local count = (self._heist_kill_count or 0) + 1
    self._heist_kill_count = count

    local next_index = (self._heist_kill_medal_index or 0) + 1
    local threshold = KILL_MEDAL_THRESHOLDS[next_index]
    if not threshold or count < threshold then return nil end

    self._heist_kill_medal_index = next_index
    return threshold
end

--- Remise à zéro des séries d'arme : les compteurs repartent de zéro et toute
--- médaille de série encore affichée ou en attente disparaît, car elle ne
--- récompense plus une série vivante. Les annonces de boss et de Dozer restent
--- intactes : elles saluent un kill déjà acquis, indépendant des séries. Les
--- médailles de kills cumulés aussi : leur palier est définitivement acquis pour
--- le braquage et seul `KH:ResetHeistCombatState` les efface.
function KH:ResetWeaponStreaks()
    self._rope_streak = nil
    self._weapon_streaks = {}
    self:_clear_medal_cards(MEDAL_KIND_WEAPON_STREAK)
end

-- ═══════════════════════════════════════════════════
-- Remise à zéro de l'état de combat d'une partie
-- ═══════════════════════════════════════════════════

--- Vide sur place la table de déduplication des kills tenue par
--- `ky_killfeed.lua`. Elle peut ne pas exister encore selon l'ordre de
--- chargement des scripts. Elle n'est jamais remplacée : son métatable à clés
--- faibles doit survivre au reset, sans quoi les unités enregistrées seraient
--- retenues en mémoire jusqu'au prochain rechargement du mod.
local function clear_recorded_kill_units(hud)
    local recorded = hud._recorded_kill_units
    if type(recorded) ~= "table" then return end

    for unit in pairs(recorded) do
        recorded[unit] = nil
    end
end

--- Remet à zéro tout l'état de combat propre à une partie : buffs affichés et
--- leurs sources, killfeed et son score, multikill, bandeaux prioritaires,
--- séries d'arme et combos de spéciaux. Une partie ne doit jamais hériter de
--- l'état de la précédente, ni d'un aperçu de debug resté affiché.
---
--- Ce qui n'appartient pas à une partie est volontairement conservé : les
--- réglages, le catalogue, le panneau KyoHUD et les listeners du pont
--- VanillaHUD+. Lors d'un nouveau braquage, `rearm_bridge_sync` réarme la
--- synchronisation différée afin de repeupler les buffs réels sans réenregistrer
--- les listeners. Un simple effacement d'aperçu conserve au contraire le latch
--- courant pour ne pas injecter des buffs réels dans les cellules de démo.
function KH:ResetHeistCombatState(rearm_bridge_sync)
    self._debug_preview_active = false
    self._event_assault_active = false
    self._event_assault_number = nil
    self._event_first_strike_awarded = false
    self._revenge_targets = setmetatable({}, { __mode = "k" })

    self._buffs = {}
    self._buff_sources = {}
    self._source_targets = {}
    if self._equipped_perk_deck_buff then
        self._equipped_perk_deck_buff.value_text = nil
    end

    self._kills = {}
    self._killfeed_score_total = 0
    self._killfeed_score_has_value = false
    self._heist_score_total = 0
    self._heist_score_best_streak = 0
    self._heist_score_recorded = false
    self._kill_combo = { count = 0, last_t = nil, updated_t = nil }
    self._special_kill_banner = nil
    self._banner_queue = {}
    self:ResetWeaponStreaks()
    -- Le total de kills du braquage et ses paliers n'appartiennent qu'à la
    -- partie : ils survivent aux chutes, mais jamais à un nouveau braquage.
    self._heist_kill_count = 0
    self._heist_kill_medal_index = 0
    self:_clear_medal_cards()
    self._special_enemy_combos = {}
    clear_recorded_kill_units(self)

    if rearm_bridge_sync then
        self._bridge_delayed_sync_acc = 0
        self._bridge_delayed_sync_done = false
    end
end

function KH:_record_heist_score(score)
    self._heist_score_recorded = true
    self._heist_score_total = (self._heist_score_total or 0) + score

    local streak = self._killfeed_score_total or 0
    if streak > (self._heist_score_best_streak or 0) then
        self._heist_score_best_streak = streak
    end
end

-- ═══════════════════════════════════════════════════
-- API publique : ajouter un kill au killfeed
-- ═══════════════════════════════════════════════════
-- Série de rappel indépendante des familles d'armes. Seuls ses propres kills
-- rafraîchissent la fenêtre ; un palier ne s'annonce qu'une fois par série.
function KH:_register_rope_kill(t)
    local streak = self._rope_streak
    if not streak or t < streak.last_t or t - streak.last_t > KILL_COMBO_WINDOW then
        streak = { count = 0, tier_index = 0, last_t = t }
        self._rope_streak = streak
    end
    streak.count = streak.count + 1
    streak.last_t = t
    local next_index = streak.tier_index + 1
    local tier = EVENT_MEDAL_DEFINITIONS.rope.tiers[next_index]
    if tier and streak.count >= tier.count then
        streak.tier_index = next_index
        return next_index
    end
end

function KH:add_kill(enemy_name, score, contributes_to_combo, special_banner, special_enemy_kind, weapon_family, event_info)
    -- enable_killfeed contrôle uniquement le rendu : scores, séries et états de
    -- médailles continuent d'avancer pendant qu'il est masqué, comme sur dev.
    if not self.settings then return end

    local first_strike = contributes_to_combo ~= false
        and self._event_assault_active and not self._event_first_strike_awarded
    if first_strike then self._event_first_strike_awarded = true end
    local t = now()
    local rope_tier = contributes_to_combo ~= false and event_info and event_info.rope
        and self:_register_rope_kill(t) or nil

    local dur = KILLFEED_ENTRY_DURATION
    if contributes_to_combo ~= false then
        local combo = self._kill_combo or { count = 0 }
        if combo.preview then
            combo = { count = 0 }
        end
        if combo.last_t and (t - combo.last_t) <= KILL_COMBO_WINDOW then
            combo.count = (combo.count or 0) + 1
        else
            combo.count = 1
            self._combo_label_variant_index = ((self._combo_label_variant_index or 0)
                % COMBO_LABEL_VARIANT_COUNT) + 1
            combo.label_variant = self._combo_label_variant_index
        end
        combo.last_t = t
        combo.updated_t = t
        combo.label = combo.count >= 2
            and combo_label(combo.count, combo.label_variant)
            or nil
        self._kill_combo = combo
    end
    if special_banner == "dozer" then
        self:_show_dozer_banner(t, false)
    elseif special_banner == "boss" then
        self:_show_boss_banner(t, false)
    end

    -- Les médailles vivent dans le killfeed : elles ne disputent jamais le
    -- bandeau supérieur à une cible prioritaire, les deux peuvent coexister.
    -- Un même kill peut en produire plusieurs ; l'ordre d'émission ci-dessous
    -- est donc figé, et c'est lui qui décide de la carte affichée en premier et
    -- de l'ordre de la file FIFO commune :
    --   série d'arme -> médailles d'évènement -> palier de kills cumulés.
    local streak_tier_index = weapon_family
        and self:_register_weapon_family_kill(weapon_family, t)
        or nil
    if streak_tier_index then
        self:_show_medal_card(
            t, make_weapon_streak_card(weapon_family, streak_tier_index), false
        )
    end

    -- `event_info` porte les états moteur déjà lus par `ky_killfeed.lua`.
    -- Première frappe et le palier de rappel sont résolus plus haut, même HUD
    -- masqué. Les cartes suivent l'ordre figé d'`EVENT_MEDAL_ORDER`. Au-delà de la
    -- carte active et des `MAX_MEDAL_QUEUE` places de la file, les médailles
    -- suivantes sont abandonnées : elles n'ouvrent aucun palier à rattraper.
    if contributes_to_combo ~= false then
        for _, event_id in ipairs(EVENT_MEDAL_ORDER) do
            local triggered
            if event_id == "first_strike" then
                triggered = first_strike
            elseif event_id == "rope" then
                triggered = rope_tier ~= nil
            else
                triggered = event_info and event_info[event_id]
            end
            if triggered then
                self:_show_medal_card(t, make_event_medal_card(event_id, rope_tier), false)
            end
        end
    end

    -- Kills cumulés du braquage : ils ne dépendent ni de l'arme, ni du score, ni
    -- d'une fenêtre de temps. Seul un kill ennemi compte ; `RecordScoredKill`
    -- marque les civils avec `contributes_to_combo == false`, et sa
    -- déduplication par unité garantit qu'un kill n'est compté qu'une fois.
    -- Le palier passe en dernier : il est rare, et le compteur l'acquiert même
    -- si la file déborde et que son annonce est perdue.
    if contributes_to_combo ~= false then
        local kill_medal_count = self:_register_heist_kill()
        if kill_medal_count then
            self:_show_medal_card(t, make_kill_medal_card(kill_medal_count), false)
        end
    end

    -- Le score représente tous les points produits pendant une apparition
    -- continue du killfeed. Une carte retirée par la limite de 1 à 5 entrées
    -- conserve donc ses points jusqu'à l'expiration de la dernière carte.
    if not has_active_killfeed_entry(self._kills, t) then
        self._killfeed_score_total = 0
        self._killfeed_score_has_value = false
    end
    if type(score) == "number" then
        self._killfeed_score_total = (self._killfeed_score_total or 0) + score
        self._killfeed_score_has_value = true
        self:_record_heist_score(score)
    end

    local special_count
    local special_label_index
    local special_definition = special_enemy_definition(special_enemy_kind)
    if special_definition then
        local special_combo = self._special_enemy_combos[special_enemy_kind]
            or { count = 0 }
        if special_combo.last_t and (t - special_combo.last_t) <= KILL_COMBO_WINDOW then
            special_combo.count = (special_combo.count or 0) + 1
        else
            special_combo.count = 1
        end
        special_combo.last_t = t
        self._special_enemy_combos[special_enemy_kind] = special_combo
        special_count = special_combo.count

        local label_count = #special_definition.labels
        special_label_index = ((self._special_enemy_label_indices[special_enemy_kind] or 0)
            % label_count) + 1
        self._special_enemy_label_indices[special_enemy_kind] = special_label_index
    end

    local entry = {
        name       = enemy_name or "Enemy",
        score      = score,
        score_text = format_kill_score(score),
        special_kind = special_definition and special_enemy_kind or nil,
        display_text = special_enemy_label(
            special_enemy_kind,
            special_label_index,
            special_count
        ),
        start_t    = t,
        t_end      = t + dur,
    }
    table.insert(self._kills, entry)

    while #self._kills > killfeed_size(self.settings) do
        table.remove(self._kills, 1)
    end
end

-- ═══════════════════════════════════════════════════
-- Panneau HUD
-- ═══════════════════════════════════════════════════
local function get_hud_panel()
    if not managers.hud then return nil end

    local ok, script = pcall(function()
        return managers.hud:script(PlayerBase.PLAYER_INFO_HUD_PD2)
    end)
    if ok and script and script.panel then
        return script.panel
    end

    local ok2, script2 = pcall(function()
        return managers.hud:script(PlayerBase.PLAYER_INFO_HUD_FULLSCREEN_PD2)
    end)
    if ok2 and script2 and script2.panel then
        return script2.panel
    end

    return nil
end

function KH:ensure_panel(force)
    local parent = get_hud_panel()
    if not parent then return false end

    if force or not (self._panel and alive(self._panel)) then
        local current_panel = parent:child("kyohud_buff_panel")
        local legacy_panel = parent:child("kyosh1ro_buff_panel")
        if current_panel then
            parent:remove(current_panel)
        end
        if legacy_panel and legacy_panel ~= current_panel then
            parent:remove(legacy_panel)
        end

        self._panel = parent:panel({
            name  = "kyohud_buff_panel",
            layer = 100,
        })
    end
    return true
end

-- ═══════════════════════════════════════════════════
-- Layout : rangée horizontale centrée sur une position en pourcentage d'écran
-- L'espacement se resserre si nécessaire pour ne masquer aucun buff.
-- ═══════════════════════════════════════════════════
local function compute_horizontal_positions(
        count, x_percent, y_percent, panel_w, panel_h, icon_size, frame_pad_x, frame_pad_y,
        top_label_height)
    local positions = {}
    if count == 0 then return positions end

    local edge_margin = 4
    local frame_w = icon_size + frame_pad_x * 2
    local desired_pitch = frame_w + clamp(icon_size * 0.25, 4, 12)
    local available_w = math.max(frame_w, panel_w - edge_margin * 2)
    local pitch = desired_pitch

    if count > 1 and frame_w + pitch * (count - 1) > available_w then
        pitch = math.max(0, (available_w - frame_w) / (count - 1))
    end

    local row_w = frame_w + pitch * (count - 1)
    local anchor_x = panel_w * clamp(x_percent, 0, 100) / 100
    local row_left = clamp(
        anchor_x - row_w * 0.5,
        edge_margin,
        math.max(edge_margin, panel_w - edge_margin - row_w)
    )

    -- Garder la valeur au-dessus, le cadre et le timer sous l'icône dans le panneau.
    local min_y = icon_size * 0.5 + frame_pad_y + (top_label_height or 18) + edge_margin
    local max_y = panel_h - icon_size * 0.5 - 22
    local y = clamp(panel_h * clamp(y_percent, 0, 100) / 100, min_y, max_y)
    local first_x = row_left + frame_w * 0.5

    for i = 0, count - 1 do
        positions[#positions + 1] = { x = first_x + pitch * i, y = y }
    end

    return positions
end

local function compare_buff_arrival(a, b)
    local oa = a.order_t or a.start_t or 0
    local ob = b.order_t or b.start_t or 0
    if oa ~= ob then return oa < ob end
    return a.id < b.id
end

local HEIST_SCORE_LABEL_COLOR = Color(0.86, 0.96, 1)
local HEIST_SCORE_BEST_VALUE_COLOR = Color(1, 1, 1)
local HEIST_SCORE_EDGE_MARGIN = 6

local function draw_heist_score_frame(panel, x, y, w, h, color, alpha, layer)
    panel:gradient({
        x = x,
        y = y + 1,
        w = w,
        h = h - 2,
        orientation = "horizontal",
        gradient_points = {
            0, Color.black:with_alpha(alpha * 0.7),
            0.58, Color.black:with_alpha(alpha * 0.46),
            1, Color.black:with_alpha(0),
        },
        layer = layer,
    })
    panel:rect({
        x = x, y = y + 2, w = 2, h = h - 4,
        color = color, alpha = alpha * 0.9, layer = layer + 1,
    })
    panel:gradient({
        x = x + 2,
        y = y + 1,
        w = w - 2,
        h = 1,
        orientation = "horizontal",
        gradient_points = {
            0, color:with_alpha(alpha * 0.5),
            0.72, color:with_alpha(alpha * 0.2),
            1, color:with_alpha(0),
        },
        layer = layer + 1,
    })
    panel:gradient({
        x = x + 2,
        y = y + h - 2,
        w = w - 2,
        h = 1,
        orientation = "horizontal",
        gradient_points = {
            0, color:with_alpha(alpha * 0.5),
            0.72, color:with_alpha(alpha * 0.2),
            1, color:with_alpha(0),
        },
        layer = layer + 1,
    })
end

local function draw_heist_score_widget(hud, panel, panel_w, panel_h, size, alpha, settings)
    local labels = heist_score_labels()
    local total = hud._heist_score_total or 0
    local best_streak = hud._heist_score_best_streak or 0
    local show_best_streak = settings.show_best_streak ~= false
    local total_text = format_kill_score(total)
    local best_streak_text = format_kill_score(best_streak)
    local font = tweak_data.menu.pd2_small_font or "fonts/font_small_mf"
    local label_font_size = clamp(size * 0.34, 11, 14)
    local value_font_size = 20
    local best_label_font_size = math.max(9, label_font_size - 1)
    local best_value_font_size = label_font_size
    local row_h = math.ceil(value_font_size + 6)
    local pad_x = clamp(size * 0.3, 9, 14)
    local pad_y = 2
    local label_gap = clamp(size * 0.3, 8, 12)
    local best_group_gap = 3
    local value_gap = clamp(size * 0.16, 5, 7)
    local label_w = approximate_text_width(labels.total, label_font_size)
    local value_w = approximate_text_width(total_text, value_font_size)
    local best_label_w = show_best_streak
        and approximate_text_width(labels.best_short, best_label_font_size)
        or 0
    local best_value_w = show_best_streak
        and approximate_text_width(best_streak_text, best_value_font_size)
        or 0
    local best_group_w = best_label_w
        + (show_best_streak and best_group_gap or 0)
        + best_value_w

    local block_w = math.min(
        math.ceil(
            label_w + label_gap + best_group_w
                + (show_best_streak and value_gap or 0)
                + value_w + pad_x * 2
        ),
        math.max(1, panel_w - HEIST_SCORE_EDGE_MARGIN * 2)
    )
    local block_h = math.ceil(row_h + pad_y * 2)
    local anchor_x = panel_w * clamp(tonumber(settings.score_position_x) or 100, 0, 100) / 100
    local anchor_y = panel_h * clamp(tonumber(settings.score_position_y) or 75, 0, 100) / 100
    local x = clamp(
        anchor_x - block_w * 0.5,
        HEIST_SCORE_EDGE_MARGIN,
        math.max(HEIST_SCORE_EDGE_MARGIN, panel_w - HEIST_SCORE_EDGE_MARGIN - block_w)
    )
    local y = clamp(
        anchor_y - block_h * 0.5,
        HEIST_SCORE_EDGE_MARGIN,
        math.max(HEIST_SCORE_EDGE_MARGIN, panel_h - HEIST_SCORE_EDGE_MARGIN - block_h)
    )
    local total_color = total < 0
        and KILLFEED_SCORE_PENALTY_COLOR
        or KILLFEED_SCORE_COLOR

    draw_heist_score_frame(panel, x, y, block_w, block_h, total_color, alpha, 101)

    -- Quand le panneau est plus étroit que la largeur naturelle du bloc,
    -- réduire les zones de texte de droite à gauche plutôt que de les laisser
    -- se chevaucher ou sortir du cadre.
    local content_left = math.min(x + pad_x, x + block_w)
    local content_right = math.max(content_left, x + block_w - pad_x)
    local label_x = content_left

    value_w = math.min(value_w, math.max(0, content_right - content_left))
    local value_x = content_right - value_w
    local cursor_x = value_x
    local best_value_x = cursor_x
    local best_label_x = cursor_x

    if show_best_streak then
        cursor_x = cursor_x - math.min(value_gap, math.max(0, cursor_x - content_left))
        best_value_w = math.min(best_value_w, math.max(0, cursor_x - content_left))
        best_value_x = cursor_x - best_value_w
        cursor_x = best_value_x

        cursor_x = cursor_x - math.min(best_group_gap, math.max(0, cursor_x - content_left))
        best_label_w = math.min(best_label_w, math.max(0, cursor_x - content_left))
        best_label_x = cursor_x - best_label_w
        cursor_x = best_label_x
    end

    cursor_x = cursor_x - math.min(label_gap, math.max(0, cursor_x - content_left))
    label_w = math.min(label_w, math.max(0, cursor_x - label_x))
    local row_y = y + pad_y

    panel:text({
        text = labels.total,
        font = font,
        font_size = label_font_size,
        color = HEIST_SCORE_LABEL_COLOR,
        align = "left",
        vertical = "center",
        x = label_x,
        y = row_y,
        w = label_w,
        h = row_h,
        layer = 103,
        alpha = alpha * 0.85,
    })
    panel:text({
        text = total_text,
        font = font,
        font_size = value_font_size,
        color = total_color,
        align = "right",
        vertical = "center",
        x = value_x,
        y = row_y,
        w = value_w,
        h = row_h,
        layer = 103,
        alpha = alpha,
    })

    if show_best_streak then
        panel:text({
            text = labels.best_short,
            font = font,
            font_size = best_label_font_size,
            color = HEIST_SCORE_LABEL_COLOR,
            align = "right",
            vertical = "center",
            x = best_label_x,
            y = row_y,
            w = best_label_w,
            h = row_h,
            layer = 103,
            alpha = alpha * 0.6,
        })
        panel:text({
            text = best_streak_text,
            font = font,
            font_size = best_value_font_size,
            color = HEIST_SCORE_BEST_VALUE_COLOR,
            align = "right",
            vertical = "center",
            x = best_value_x,
            y = row_y,
            w = best_value_w,
            h = row_h,
            layer = 103,
            alpha = alpha * 0.85,
        })
    end
end

-- ═══════════════════════════════════════════════════
-- Dessin du HUD
-- ═══════════════════════════════════════════════════
function KH:draw()
    if not (self._panel and alive(self._panel)) then return end

    local s = self.settings
    if not s then return end

    local t = now()

    -- Purger les buffs expirés
    for id, b in pairs(self._buffs) do
        if b.t_end and b.t_end <= t then
            self._buffs[id] = nil
        end
    end

    -- Purger les kills expirés
    local i = 1
    while i <= #self._kills do
        if self._kills[i].t_end and self._kills[i].t_end <= t then
            table.remove(self._kills, i)
        else
            i = i + 1
        end
    end
    -- Fin de la rafale continue : le score de la rangée repart de zéro. Le total
    -- et le meilleur total de rafale du braquage, eux, survivent — ils ne sont
    -- effacés que par ResetHeistCombatState.
    if #self._kills == 0 then
        self._killfeed_score_total = 0
        self._killfeed_score_has_value = false
    end

    -- Une série se termine après quelques secondes sans nouveau kill.
    local combo = self._kill_combo
    if combo and not combo.preview and combo.last_t
            and (t - combo.last_t) > KILL_COMBO_WINDOW then
        combo.count = 0
        combo.last_t = nil
        combo.updated_t = nil
        combo.label = nil
    end

    -- L'annonce spéciale masque brièvement le multikill, qui reprend ensuite
    -- tant que sa propre fenêtre de trois secondes reste active. À l'expiration,
    -- l'annonce suivante de la file enchaîne immédiatement.
    local special_banner = self._special_kill_banner
    if special_banner and not special_banner.preview and special_banner.t_end <= t then
        self._special_kill_banner = nil
        special_banner = nil
    end
    if not special_banner then
        local queue = self._banner_queue
        if queue and #queue > 0 then
            self:_start_special_banner(t, table.remove(queue, 1), false)
            special_banner = self._special_kill_banner
        end
    end

    -- La médaille suit le même cycle, sur son propre état : elle expire seule et
    -- laisse la place à la suivante s'il y en a une en attente, quelle que soit
    -- sa famille. La file n'est parcourue qu'à cette expiration.
    local medal_card = self._medal_card
    if medal_card and not medal_card.preview and medal_card.t_end <= t then
        self._medal_card = nil
        medal_card = nil
    end
    if not medal_card then
        local queue = self._medal_queue
        if queue and #queue > 0 then
            self:_start_medal_card(t, table.remove(queue, 1), false)
            medal_card = self._medal_card
        end
    end

    -- Nettoyer le panneau pour redessiner
    self._panel:clear()

    local w = self._panel:w()
    local h = self._panel:h()
    local cx = w * 0.5
    local cy = h * 0.5
    local radius    = clamp(s.circle_radius or 250, 128, 291)
    local size      = clamp(s.icon_size or 32, 32, 40)
    local alpha     = clamp(s.opacity or 0.9, 0.1, 1.0)

    -- ── Dessiner les buffs ──
    if s.enable_buffs then
        local buff_list = {}
        local promoted_perk_buff_id

        -- Les indicateurs prioritaires ouvrent la rangée dans l'ordre choisi,
        -- mais seuls le deck équipé et les buffs réellement actifs apparaissent.
        -- Un buff actif associé au deck remplace son placeholder en position 1.
        for _, buff_id in ipairs(STATIC_BUFF_SLOTS) do
            if self:is_buff_visible(buff_id) then
                local buff
                if buff_id == "equipped_perk_deck" then
                    buff, promoted_perk_buff_id = active_equipped_perk_buff(self)
                    buff = buff or equipped_perk_deck_entry(self)
                else
                    buff = self._buffs[buff_id]
                end
                if buff and buff.icon then
                    table.insert(buff_list, buff)
                end
            end
        end

        local extra_buffs = {}
        for _, b in pairs(self._buffs) do
            if b.icon and b.id ~= promoted_perk_buff_id
                    and not STATIC_BUFF_SLOT_SET[b.id] and self:is_buff_visible(b.id) then
                table.insert(extra_buffs, b)
            end
        end
        -- Tri par ordre d'arrivée : les nouveaux buffs s'ajoutent à la suite
        -- des emplacements fixes, sans réordonner les icônes existantes.
        table.sort(extra_buffs, compare_buff_arrival)
        for _, buff in ipairs(extra_buffs) do
            table.insert(buff_list, buff)
        end

        local frame_pad_x = clamp(size * 0.16, 4, 9)
        local frame_pad_y = clamp(size * 0.08, 2, 4)
        -- Une seule rangée suffit tant qu'un libellé haut et une valeur ne
        -- coexistent pas ; dès qu'une cellule porte les deux, la marge haute
        -- passe à deux lignes. Un libellé placé dans le timer reste sous
        -- l'icône et ne consomme jamais cette marge.
        local top_label_height = 18
        for _, buff in ipairs(buff_list) do
            if buff.value_text then
                local label_text, label_placement = buff_label(buff)
                if label_text and label_placement == BUFF_LABEL_TOP then
                    top_label_height = 35
                    break
                end
            end
        end
        local positions = compute_horizontal_positions(
            #buff_list,
            tonumber(s.buff_position_x) or 50,
            tonumber(s.buff_position_y) or 85,
            w,
            h,
            size,
            frame_pad_x,
            frame_pad_y,
            top_label_height
        )
        for idx, buff in ipairs(buff_list) do
            local pos = positions[idx]
            if pos then
                -- L'état visuel est résolu une seule fois par buff rendu : il
                -- pilote l'opacité de la cellule, le contour périmétrique et
                -- la couleur du timer. Le cadre statique, lui, reste
                -- identique pour tous les états.
                local state = resolve_buff_state(buff, t)

                -- Alpha dynamique : diminue quand le buff expire, mais un état
                -- d'alerte remonte vers l'opacité pleine pour rester visible.
                local buff_alpha = alpha * (0.4 + 0.6 * (state.progress or 1))
                buff_alpha = buff_alpha + (alpha - buff_alpha) * state.emphasis
                buff_alpha = buff_alpha * state.alpha_scale

                -- Chaque buff conserve sa propre cellule, assez discrète pour que
                -- l'icône et le timer restent les informations dominantes.
                local frame_x = pos.x - size * 0.5 - frame_pad_x
                local frame_y = pos.y - size * 0.5 - frame_pad_y
                local frame_w = size + frame_pad_x * 2
                local frame_h = size + frame_pad_y * 2

                draw_buff_cell_frame(
                    self._panel,
                    frame_x,
                    frame_y,
                    frame_w,
                    frame_h,
                    buff_alpha * (0.72 + 0.28 * state.emphasis),
                    98
                )

                -- Contour périmétrique horaire, réservé aux buffs temporaires :
                -- un indicateur permanent n'a pas de `progress` et n'en reçoit
                -- donc jamais.
                if state.progress then
                    draw_timed_buff_progress(
                        self._panel,
                        frame_x,
                        frame_y,
                        frame_w,
                        frame_h,
                        state.progress,
                        state.accent_color or HUD_ACCENT_COLOR,
                        buff_alpha,
                        99
                    )
                end

                local remaining = state.remaining

                local params = {
                    layer = 101,
                    w     = size,
                    h     = size,
                    x     = pos.x - size / 2,
                    y     = pos.y - size / 2,
                }

                if buff.icon.rect then
                    params.texture      = buff.icon.texture
                    params.texture_rect = buff.icon.rect
                else
                    params.texture = buff.icon.texture
                end

                local bmp = self._panel:bitmap(params)
                bmp:set_color(buff.color or Color.white)
                bmp:set_alpha(buff_alpha)

                -- Un libellé haut occupe la ligne juste au-dessus du cadre et
                -- décale la valeur d'une ligne supplémentaire. Un libellé de
                -- placement « timer » descend sous l'icône : la valeur garde
                -- alors sa ligne unique au-dessus du cadre.
                local label_text, label_placement = buff_label(buff)
                local top_label = label_text and label_placement == BUFF_LABEL_TOP and label_text or nil
                local timer_label = label_text and label_placement == BUFF_LABEL_TIMER and label_text or nil
                if buff.value_text then
                    self._panel:text({
                        text      = buff.value_text,
                        font      = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                        font_size = clamp(size * 0.38, 11, 15),
                        color     = buff.color or Color.white,
                        align     = "center",
                        vertical  = "center",
                        x         = frame_x,
                        y         = frame_y - (top_label and 34 or 17),
                        w         = frame_w,
                        h         = 16,
                        layer     = 102,
                        alpha     = buff_alpha,
                    })
                end

                if top_label then
                    self._panel:text({
                        text      = top_label,
                        font      = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                        font_size = clamp(size * 0.3, 9, 12),
                        color     = HUD_ACCENT_COLOR,
                        align     = "center",
                        vertical  = "center",
                        x         = frame_x,
                        y         = frame_y - 17,
                        w         = frame_w,
                        h         = 16,
                        layer     = 102,
                        alpha     = buff_alpha,
                    })
                end

                if buff.stack_text then
                    local badge_w = clamp(size * 0.55, 15, 26)
                    local badge_h = clamp(size * 0.36, 10, 16)
                    local badge_x = pos.x + size * 0.5 - badge_w
                    local badge_y = pos.y + size * 0.5 - badge_h
                    self._panel:rect({
                        x = badge_x,
                        y = badge_y,
                        w = badge_w,
                        h = badge_h,
                        color = Color.black,
                        alpha = buff_alpha * 0.78,
                        layer = 102,
                    })
                    self._panel:text({
                        text = buff.stack_text,
                        font = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                        font_size = clamp(size * 0.3, 9, 12),
                        color = Color.white,
                        align = "center",
                        vertical = "center",
                        x = badge_x,
                        y = badge_y,
                        w = badge_w,
                        h = badge_h,
                        layer = 103,
                        alpha = buff_alpha,
                    })
                end

                -- Sous l'icône : un libellé de placement « timer » occupe seul
                -- l'emplacement et remplace le compte à rebours, dont la durée
                -- n'apporte rien sur ces indicateurs composites. Sinon, timer
                -- texte teinté par l'état d'urgence.
                if timer_label then
                    self._panel:text({
                        text      = timer_label,
                        font      = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                        font_size = clamp(size * 0.3, 9, 12),
                        color     = HUD_ACCENT_COLOR,
                        align     = "center",
                        vertical  = "center",
                        x         = frame_x,
                        y         = pos.y + size / 2 + 2,
                        w         = frame_w,
                        h         = 16,
                        layer     = 102,
                        alpha     = buff_alpha,
                    })
                elseif remaining and remaining > 0 then
                    self._panel:text({
                        text      = string.format("%.1f", remaining),
                        font      = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                        font_size = 14,
                        color     = state.timer_color or Color.white,
                        align     = "center",
                        x         = pos.x - size / 2,
                        y         = pos.y + size / 2 + 2,
                        w         = size,
                        h         = 16,
                        layer     = 102,
                        alpha     = alpha * (0.8 + 0.2 * state.emphasis) * state.alpha_scale,
                    })
                end
            end
        end
    end

    -- ── Dessiner le bandeau de série et le killfeed horizontal ──
    local combo_active = combo and combo.count and combo.count >= 2 and combo.last_t
    local special_banner_active = special_banner ~= nil
    local banner_active = special_banner_active or combo_active
    local medal_card_active = medal_card ~= nil
    if s.enable_killfeed and (#self._kills > 0 or banner_active or medal_card_active) then
        local killfeed_limit = killfeed_size(s)
        local visible_count = math.min(#self._kills, killfeed_limit)
        local item_h = clamp(size * 0.72 + 6, 28, 42)
        local item_gap = clamp(size * 0.3, 8, 14)
        local kill_font = tweak_data.menu.pd2_small_font or "fonts/font_small_mf"
        local kill_font_size = clamp(size * 0.42, 13, 18)
        local text_padding = clamp(size * 0.34, 10, 16)
        local text_gap = clamp(size * 0.14, 4, 7)
        local score_total_text = visible_count > 0
            and self._killfeed_score_has_value
            and format_kill_score(self._killfeed_score_total)
        local score_font_size = kill_font_size
        local score_w = score_total_text
            and math.max(
                item_h,
                math.ceil(
                    approximate_text_width(score_total_text, score_font_size)
                        + text_padding * 2
                )
            )
            or 0
        local score_gap = score_total_text and item_gap or 0
        local available_w = math.max(1, w - 16 - score_w - score_gap)
        local first_kill = #self._kills - visible_count + 1
        local banner_w = math.min(clamp(size * 7.5, 220, 320), math.max(1, w - 16))

        measure_killfeed_entries(
            self._panel,
            self._kills,
            first_kill,
            visible_count,
            kill_font,
            kill_font_size
        )

        local item_widths = {}
        local desired_row_w = 0
        for slot = 1, visible_count do
            local kill = self._kills[first_kill + slot - 1]
            local name_w = kill._measured_name_w
                or approximate_text_width(kill.display_text or kill.name, kill_font_size)
            local score_w = kill.score_text
                and (kill._measured_score_w or approximate_text_width(kill.score_text, kill_font_size))
                or 0
            local content_gap = kill.score_text and text_gap or 0
            local item_w = math.ceil(name_w + score_w + content_gap + text_padding * 2)
            item_w = math.max(item_h, item_w)
            item_widths[slot] = item_w
            desired_row_w = desired_row_w + item_w
        end

        if visible_count > 1 then
            item_gap = math.min(
                item_gap,
                math.max(0, (available_w - desired_row_w) / (visible_count - 1))
            )
        end

        local item_budget = math.max(1, available_w - item_gap * math.max(0, visible_count - 1))
        if desired_row_w > item_budget and desired_row_w > 0 then
            local scale = item_budget / desired_row_w
            desired_row_w = 0
            for slot = 1, visible_count do
                item_widths[slot] = math.max(1, item_widths[slot] * scale)
                desired_row_w = desired_row_w + item_widths[slot]
            end
        end

        local feed_row_w = visible_count > 0
            and desired_row_w + item_gap * (visible_count - 1)
            or 0
        local item_offsets = {}
        local next_offset = 0
        for slot = 1, visible_count do
            item_offsets[slot] = next_offset
            next_offset = next_offset + item_widths[slot] + item_gap
        end
        local banner_h = math.max(38, size + 8)
        local banner_feed_gap = BANNER_FRAME_EXTENSION
            + KILLFEED_FRAME_CLEARANCE
        -- Le bloc conserve l'emplacement historique du bandeau supérieur, puis
        -- ajoute dynamiquement la médaille et la rangée des noms. Seule la
        -- médaille ajoute un niveau : les noms remontent dès qu'elle expire,
        -- sans laisser d'espace vide entre le bandeau et le killfeed.
        local medal_h = medal_card_active and clamp(item_h + 6, 34, 46) or 0
        local medal_top_gap = medal_card_active and MEDAL_TOP_GAP or 0
        local medal_feed_gap = (medal_card_active and visible_count > 0)
            and MEDAL_ROW_GAP
            or 0
        local block_h = banner_h + banner_feed_gap + medal_top_gap
            + medal_h + medal_feed_gap
            + (visible_count > 0 and item_h or 0)
        local preferred_top = cy + clamp(radius * 0.55, 70, 160)
        local block_top = math.max(8, math.min(preferred_top, h - block_h - 16))
        local medal_y = block_top + banner_h + banner_feed_gap + medal_top_gap
        local feed_y = medal_y + medal_h + medal_feed_gap
        local feed_color = HUD_ACCENT_COLOR
        local card_row_w = score_w + score_gap + feed_row_w
        local block_w = math.max(banner_w, card_row_w)
        local block_x = clamp(cx - block_w * 0.5, 8, math.max(8, w - 8 - block_w))
        local block_center = block_x + block_w * 0.5
        local card_row_x = block_center - card_row_w * 0.5

        if score_total_text then
            local newest = self._kills[#self._kills]
            local score_intro = newest and newest.start_t
                and clamp((t - newest.start_t) / KILL_SCROLL_TIME, 0, 1)
                or 1
            local score_color = (self._killfeed_score_total or 0) < 0
                and KILLFEED_SCORE_PENALTY_COLOR
                or KILLFEED_SCORE_COLOR
            local score_alpha = alpha * score_intro
            draw_killfeed_card_frame(
                self._panel,
                card_row_x,
                feed_y,
                score_w,
                item_h,
                score_color,
                score_alpha,
                101
            )
            self._panel:text({
                text = score_total_text,
                font = kill_font,
                font_size = score_font_size,
                color = score_color,
                align = "center",
                vertical = "center",
                x = card_row_x,
                y = feed_y,
                w = score_w,
                h = item_h,
                layer = 103,
                alpha = score_alpha,
            })
        end

        if banner_active then
            local remaining = special_banner_active
                and (special_banner.preview
                    and SPECIAL_KILL_BANNER_DURATION
                    or special_banner.t_end - t)
                or (combo.preview
                    and KILL_COMBO_WINDOW
                    or combo.last_t + KILL_COMBO_WINDOW - t)
            if remaining > 0 then
                local updated_t = special_banner_active
                    and special_banner.started_t
                    or combo.updated_t
                local intro = clamp((t - (updated_t or t)) / 0.15, 0, 1)
                local fade_out = clamp(remaining / 0.35, 0, 1)
                local banner_alpha = alpha * fade_out
                local scale = 1 + (1 - intro) * 0.06
                local bw = banner_w * scale
                local bh = banner_h * scale
                local bx = block_center - bw * 0.5
                local by = block_top - (bh - banner_h) * 0.5
                local color = special_banner_active
                    and (special_banner.color or HUD_ACCENT_COLOR)
                    or combo_color(combo.count)

                draw_tactical_frame(
                    self._panel,
                    bx,
                    by,
                    bw,
                    bh,
                    color,
                    banner_alpha,
                    103,
                    BANNER_FRAME_STYLE
                )

                -- Les deux banques réservent la même largeur, quel que soit le
                -- bandeau : le texte reste centré et ne les chevauche jamais.
                local arrow_group_w = special_banner_active
                    and SPECIAL_CHEVRON_GROUP_W
                    or MULTIKILL_CHEVRON_GROUP_W
                local arrow_margin = special_banner_active
                    and SPECIAL_CHEVRON_MARGIN
                    or MULTIKILL_CHEVRON_MARGIN
                local arrow_reserved = arrow_margin + arrow_group_w + BANNER_CHEVRON_TEXT_GAP
                local arrow_y = by + bh * 0.5
                local left_arrow_x = bx + arrow_margin
                local right_arrow_x = bx + bw - arrow_margin - arrow_group_w

                if special_banner_active then
                    draw_chevrons(self._panel, left_arrow_x, arrow_y, 1, color, banner_alpha, 106)
                    draw_chevrons(self._panel, right_arrow_x, arrow_y, -1, color, banner_alpha, 106)
                else
                    -- Un cran de plus par kill supplémentaire de la série.
                    local filled = multikill_chevron_fill(combo.count)
                    draw_multikill_chevrons(
                        self._panel, left_arrow_x, arrow_y, 1, color, banner_alpha, 106, filled
                    )
                    draw_multikill_chevrons(
                        self._panel, right_arrow_x, arrow_y, -1, color, banner_alpha, 106, filled
                    )
                end

                local text_x = bx + arrow_reserved
                local text_w = math.max(1, bw - arrow_reserved * 2)
                local font_size = clamp(size * 0.65, 17, 27)
                local label = special_banner_active
                    and special_banner.label
                    or combo.label
                    or combo_label(combo.count, combo.label_variant)
                draw_glowing_text(
                    self._panel,
                    label,
                    tweak_data.menu.pd2_large_font or "fonts/font_large_mf",
                    font_size,
                    color,
                    text_x,
                    by,
                    text_w,
                    bh,
                    banner_alpha,
                    106
                )
            end
        end

        -- ── Médaille : rangée propre au killfeed ──
        -- Même largeur que le bandeau, mais hauteur de rangée de killfeed, sans
        -- nom d'unité ni score. Elle pousse simplement les noms d'un cran, quelle
        -- que soit la famille de médaille qui occupe la rangée.
        if medal_card_active then
            local remaining = medal_card.preview
                and MEDAL_CARD_DURATION
                or medal_card.t_end - t
            if remaining > 0 then
                local intro = clamp((t - (medal_card.started_t or t)) / 0.15, 0, 1)
                local fade_out = clamp(remaining / 0.3, 0, 1)
                local medal_alpha = alpha * fade_out
                local scale = 1 + (1 - intro) * 0.05
                local mw = banner_w * scale
                local mh = medal_h * scale
                local mx = block_center - mw * 0.5
                local my = medal_y - (mh - medal_h) * 0.5
                local medal_color = medal_card.color or HUD_ACCENT_COLOR

                draw_medal_frame(
                    self._panel, mx, my, mw, mh, medal_color, medal_alpha, 101
                )

                local arrow_reserved = MEDAL_CHEVRON_MARGIN
                    + MEDAL_CHEVRON_GROUP_W
                    + MEDAL_CHEVRON_TEXT_GAP
                local arrow_y = my + mh * 0.5
                draw_chevrons(
                    self._panel,
                    mx + MEDAL_CHEVRON_MARGIN,
                    arrow_y,
                    1,
                    medal_color,
                    medal_alpha,
                    104,
                    MEDAL_CHEVRON_STYLE
                )
                draw_chevrons(
                    self._panel,
                    mx + mw - MEDAL_CHEVRON_MARGIN - MEDAL_CHEVRON_GROUP_W,
                    arrow_y,
                    -1,
                    medal_color,
                    medal_alpha,
                    104,
                    MEDAL_CHEVRON_STYLE
                )

                local font_size = clamp(size * 0.48, 15, 21)
                local text_x = mx + arrow_reserved
                local text_w = math.max(1, mw - arrow_reserved * 2)

                -- Médaille à icône : le pictogramme remplace le nom écrit et
                -- précède le palier, les deux restant centrés ensemble dans la
                -- zone intérieure. Le texte est simplement décalé de la largeur
                -- réservée à l'icône, ce qui recentre le couple sans dépendre
                -- d'une mesure : seule la position de l'icône suit la largeur
                -- estimée du texte, donc une estimation imprécise la décale un
                -- peu au lieu de tronquer le palier.
                local icon = medal_card.icon
                if icon and icon.texture then
                    local icon_size = clamp(
                        mh * MEDAL_ICON_H_RATIO, MEDAL_ICON_MIN, MEDAL_ICON_MAX
                    )
                    local reserved = icon_size + MEDAL_ICON_TEXT_GAP
                    text_x = text_x + reserved
                    text_w = math.max(1, text_w - reserved)

                    local label_w = approximate_text_width(medal_card.label, font_size)
                    local params = {
                        layer   = 104,
                        w       = icon_size,
                        h       = icon_size,
                        x       = text_x + (text_w - label_w) * 0.5 - reserved,
                        y       = my + (mh - icon_size) * 0.5,
                        texture = icon.texture,
                    }
                    if icon.rect then
                        params.texture_rect = icon.rect
                    end

                    local bmp = self._panel:bitmap(params)
                    bmp:set_color(medal_card.icon_color or medal_color)
                    bmp:set_alpha(medal_alpha)
                end

                draw_glowing_text(
                    self._panel,
                    medal_card.label,
                    tweak_data.menu.pd2_medium_font or "fonts/font_medium_mf",
                    font_size,
                    medal_color,
                    text_x,
                    my,
                    text_w,
                    mh,
                    medal_alpha,
                    104
                )
            end
        end

        local newest = self._kills[#self._kills]
        local scroll = 1
        if newest and newest.start_t then
            scroll = clamp((t - newest.start_t) / KILL_SCROLL_TIME, 0, 1)
        end

        local feed_x = card_row_x + score_w + score_gap
        for slot = 1, visible_count do
            -- Ordre chronologique : le kill le plus ancien est à gauche,
            -- le plus récent s'ajoute à droite.
            local kill = self._kills[first_kill + slot - 1]
            local item_w = item_widths[slot]
            local item_x = feed_x + item_offsets[slot]

            local life = 1
            if kill.start_t and kill.t_end then
                local dur = kill.t_end - kill.start_t
                if dur > 0 then
                    life = clamp(1 - ((t - kill.start_t) / dur), 0, 1)
                end
            end

            local item_alpha = alpha * (0.25 + 0.75 * life)
            if slot == visible_count then
                item_alpha = item_alpha * scroll
                item_x = item_x + 18 * (1 - scroll)
            end

            local item_color = kill.special_kind
                and special_enemy_color(kill.special_kind)
                or feed_color
            draw_killfeed_card_frame(
                self._panel,
                item_x,
                feed_y,
                item_w,
                item_h,
                item_color,
                item_alpha,
                101
            )

            local score_text = kill.score_text
            local inner_w = math.max(1, item_w - text_padding * 2)
            local score_w = score_text
                and math.min(kill._measured_score_w or 0, math.max(1, inner_w - text_gap - 1))
                or 0
            local name_w = math.min(
                kill._measured_name_w or inner_w,
                math.max(1, inner_w - score_w - (score_text and text_gap or 0))
            )
            local content_w = name_w + score_w + (score_text and text_gap or 0)
            local text_x = item_x + (item_w - content_w) * 0.5

            self._panel:text({
                text = kill.display_text or kill.name,
                font = kill_font,
                font_size = kill_font_size,
                color = kill.special_kind and item_color or Color(0.86, 0.96, 1),
                align = score_text and "right" or "center",
                vertical = "center",
                x = text_x,
                y = feed_y,
                w = name_w,
                h = item_h,
                layer = 102,
                alpha = item_alpha,
            })

            if score_text then
                local score_color = kill.score and kill.score < 0
                    and Color(1, 0.36, 0.3)
                    or item_color
                self._panel:text({
                    text = score_text,
                    font = kill_font,
                    font_size = kill_font_size,
                    color = score_color,
                    align = "left",
                    vertical = "center",
                    x = text_x + name_w + text_gap,
                    y = feed_y,
                    w = score_w,
                    h = item_h,
                    layer = 103,
                    alpha = item_alpha,
                })
            end
        end
    end

    if s.enable_killfeed and s.show_total_score ~= false
            and self._heist_score_recorded then
        draw_heist_score_widget(self, self._panel, w, h, size, alpha, s)
    end
end

-- ═══════════════════════════════════════════════════
-- Rafraîchissement
-- ═══════════════════════════════════════════════════
function KH:RefreshHUD()
    self:RefreshDetectedBuffs()
    self:RefreshHackerPocketECMStatus()
    if self:ensure_panel(false) then
        self:draw()
    end
end

-- ═══════════════════════════════════════════════════
-- Debug : simulation
-- ═══════════════════════════════════════════════════
-- Cas parcourus par appels successifs à Debug: Simulate :
--   multikill partiel, 3 encoches allumées sur 5 ;
--   banque saturée et repli dynamique « KILL CHAIN xN » ;
--   annonce de cible prioritaire (chevrons décoratifs pleins) ;
--   médaille de série d'arme dans le killfeed, avec les noms sous celle-ci ;
--   médaille de kills cumulés « icône Dmg+ + 100 KILLS », dans cette même
--   rangée partagée ;
--   les six médailles d'évènement, une par appel, avec leur icône `hud_tweak`.
-- Le premier appel montre directement l'exemple demandé, partiellement rempli.
-- `combo` reste à 0 pour les cas d'annonce afin que seul le bandeau spécial soit
-- visible ; l'aperçu ne compte aucun kill, ni dans les séries d'arme ni dans le
-- total du braquage : chaque carte est construite depuis ces valeurs littérales.
local DEBUG_BANNER_PREVIEWS = {
    { combo = 4 },
    { combo = 11 },
    { combo = 0, banner = "boss" },
    { combo = 0, medal = "weapon_streak", family = "shotgun", tier_index = 2 },
    { combo = 0, medal = "kill_total", kills = 100 },
    { combo = 0, medal = "event", event = "first_strike" },
    { combo = 0, medal = "event", event = "grave" },
    { combo = 0, medal = "event", event = "low_hp" },
    { combo = 0, medal = "event", event = "reload" },
    { combo = 0, medal = "event", event = "through_shield" },
    { combo = 0, medal = "event", event = "one_shot_two_kills" },
    { combo = 0, medal = "event", event = "revenge" },
    { combo = 0, medal = "event", event = "bulltrue" },
    { combo = 0, medal = "event", event = "showstopper" },
    { combo = 0, medal = "event", event = "rope", tier_index = 1 },
    { combo = 0, medal = "event", event = "rope", tier_index = 2 },
    { combo = 0, medal = "event", event = "rope", tier_index = 3 },
}

function KH:DebugSimulate(n)
    -- L'aperçu utilise les tables du HUD : il n'est sûr qu'au menu principal,
    -- jamais pendant un braquage (y compris briefing, garde à vue et pause).
    local ok, in_menu = pcall(function()
        return game_state_machine:last_queued_state_name() == "menu_main"
    end)
    if not ok or not in_menu then
        log("[KyoHUD] Preview is only available from the main menu.")
        return
    end
    self:ResetHeistCombatState()
    self._debug_preview_active = true
    n = n or 8

    local demo_static_buffs = {
        { id = "partner_in_crime", value_text = "0/2" },
        { id = "pocket_ecm_jammer_debuff", is_debuff = true, duration = 45 },
        { id = "passive_health_regen", value_text = "4.5%" },
        { id = "standard_armor_regeneration" },
        { id = "armor_break_invulnerable_debuff", is_debuff = true },
        { id = "damage_increase", value_text = "+35%" },
        { id = "damage_reduction", value_text = "-20%" },
        { id = "melee_damage_increase", value_text = "x1.75" },
    }
    local t_now = now()
    for i, demo in ipairs(demo_static_buffs) do
        self._buffs[demo.id] = {
            id = demo.id,
            icon = icon_for_buff(demo.id),
            color = color_for_buff(demo.id, demo.is_debuff),
            value_text = demo.value_text,
            is_debuff = demo.is_debuff == true,
            order_t = t_now + i * 0.001,
            start_t = t_now,
            duration = demo.duration,
            t_end = demo.duration and (t_now + demo.duration) or nil,
            persistent = demo.duration == nil,
        }
    end

    -- Si le deck équipé possède un buff de deck activé dans les options, la
    -- simulation l'active afin de vérifier le remplacement de la position 1.
    local _, base_specialization_id = current_perk_deck_ids()
    equipped_perk_deck_entry(self).value_text = base_specialization_id == HACKER_SPECIALIZATION_ID
        and "x2" or nil
    local perk_candidates = base_specialization_id
        and KH.PERK_DECK_BUFFS
        and KH.PERK_DECK_BUFFS[base_specialization_id]
    for _, buff_id in ipairs(perk_candidates or {}) do
        if self:is_buff_visible(buff_id) then
            self._buffs[buff_id] = {
                id = buff_id,
                icon = icon_for_buff(buff_id),
                color = color_for_buff(buff_id, false),
                order_t = t_now + 0.0005,
                start_t = t_now,
                persistent = true,
            }
            break
        end
    end

    local demo_buffs = {
        { id = "crew_throwable_regen", stack_text = "x2" },
        { id = "total_dodge_chance", value_text = "45%" },
        { id = "lock_n_load", value_text = "+35%" },
        { id = "delayed_damage", value_text = "-125" },
        { id = "grinder", stack_text = "x3" },
        { id = "overkill" },
        { id = "unseen_strike" },
        { id = "bullet_storm" },
        { id = "second_wind", value_text = "+30%" },
    }

    for i = 1, n do
        local demo = demo_buffs[((i - 1) % #demo_buffs) + 1]
        local base = demo.id
        local icon = icon_for_buff(base)
        self._buffs["demo_" .. base .. "_" .. tostring(i)] = {
            id       = "demo_" .. base .. "_" .. tostring(i),
            icon     = icon,
            color    = color_for_buff(base, demo.is_debuff),
            category = KH.BUFF_MAP and KH.BUFF_MAP[base]
                and KH.BUFF_MAP[base].category,
            value_text = demo.value_text,
            stack_text = demo.stack_text,
            is_debuff = demo.is_debuff == true,
            order_t  = t_now + i * 0.001, -- ordre d'affichage 1..n dans la rangée
            start_t  = t_now,
            duration = 30 + i * 2,
            t_end    = t_now + 30 + i * 2,
        }
    end

    -- Vitrine des états adaptatifs. `preview_remaining` fige le temps restant
    -- pour que les états normal, warning et critical restent affichés côte à
    -- côte jusqu'à Debug: Clear, au lieu d'expirer en quelques secondes.
    -- Avec une durée de 20 s, le seuil warning tombe à 5 s et le seuil
    -- critical à 2 s : les valeurs choisies encadrent donc chaque état.
    local demo_state_buffs = {
        { id = "inspire",        remaining = 14 },
        { id = "uppers",         remaining = 3.4 },
        { id = "swan_song",      remaining = 1.2 },
        { id = "inspire_debuff", remaining = 12, is_debuff = true },
    }
    local demo_state_duration = 20
    for i, demo in ipairs(demo_state_buffs) do
        local demo_id = "demo_state_" .. demo.id
        self._buffs[demo_id] = {
            id       = demo_id,
            icon     = icon_for_buff(demo.id),
            color    = color_for_buff(demo.id, demo.is_debuff),
            category = KH.BUFF_MAP and KH.BUFF_MAP[demo.id]
                and KH.BUFF_MAP[demo.id].category,
            is_debuff = demo.is_debuff == true,
            order_t  = t_now + 0.1 + i * 0.001,
            start_t  = t_now,
            duration = demo_state_duration,
            -- Aucun t_end : l'aperçu ne doit pas être purgé par KH:draw.
            preview_remaining = demo.remaining,
        }
    end

    -- Simuler quelques kills
    local demo_kills = {
        { name = "Medic", score = 6, special_kind = "medic", special_count = 2, label_index = 1 },
        { name = "Captain Winters", score = 100, special_kind = "boss", special_count = 1, label_index = 1 },
        { name = "Shield", score = 5, special_kind = "shield", special_count = 2, label_index = 1 },
        { name = "Cloaker", score = 8, special_kind = "cloaker", special_count = 2, label_index = 1 },
        { name = "Taser", score = 7, special_kind = "taser", special_count = 2, label_index = 1 },
    }
    t_now = now()
    self._killfeed_score_total = 0
    self._killfeed_score_has_value = false
    self._heist_score_total = 0
    self._heist_score_best_streak = 0
    self._heist_score_recorded = false
    for i = 1, killfeed_size(self.settings) do
        local demo = demo_kills[i]
        table.insert(self._kills, {
            name       = demo.name,
            score      = demo.score,
            score_text = format_kill_score(demo.score),
            special_kind = demo.special_kind,
            display_text = special_enemy_label(
                demo.special_kind,
                demo.label_index,
                demo.special_count
            ),
            start_t    = t_now,
            -- Pas de t_end : les kills de debug restent visibles jusqu'à DebugClear.
        })
        if type(demo.score) == "number" then
            self._killfeed_score_total = self._killfeed_score_total + demo.score
            self._killfeed_score_has_value = true
            self:_record_heist_score(demo.score)
        end
    end
    self._heist_score_total = (self._heist_score_total or 0) + 137
    self._heist_score_best_streak = (self._killfeed_score_total or 0) + 50
    -- Une annonce spéciale d'aperçu ne s'éteint jamais et masquerait toujours
    -- le multikill : chaque Debug: Simulate avance donc d'un cas de bandeau,
    -- et chacun reste affiché jusqu'au suivant ou jusqu'à Debug: Clear.
    self._debug_banner_preview_index = (self._debug_banner_preview_index
        % #DEBUG_BANNER_PREVIEWS) + 1
    local preview = DEBUG_BANNER_PREVIEWS[self._debug_banner_preview_index]

    self._kill_combo = {
        count = preview.combo,
        last_t = t_now,
        updated_t = t_now,
        label_variant = 1,
        label = preview.combo >= 2 and combo_label(preview.combo, 1) or nil,
        preview = true,
    }
    self._special_kill_banner = nil
    self._banner_queue = {}
    if preview.banner == "boss" then
        self:_show_boss_banner(t_now, true)
    elseif preview.medal == "weapon_streak" then
        self:_show_medal_card(
            t_now, make_weapon_streak_card(preview.family, preview.tier_index), true
        )
    elseif preview.medal == "kill_total" then
        self:_show_medal_card(t_now, make_kill_medal_card(preview.kills), true)
    elseif preview.medal == "event" then
        self:_show_medal_card(t_now, make_event_medal_card(preview.event, preview.tier_index), true)
    end
end

function KH:DebugClear()
    -- Sans aperçu, ne toucher ni aux compteurs réels ni au panneau courant.
    if not self._debug_preview_active then return end
    self:ResetHeistCombatState()
    if self._panel and alive(self._panel) then
        self._panel:clear()
    end
end

-- ═══════════════════════════════════════════════════
-- Hooks HUD : initialisation et mise à jour
-- ═══════════════════════════════════════════════════
-- HUDManager relaie ces deux évènements sur l'hôte ET le client. Aucun accès
-- à HUDAssaultCorner : un HUD tiers peut remplacer ou masquer ce panneau.
if HUDManager.sync_start_assault then
    Hooks:PostHook(HUDManager, "sync_start_assault", "KH_EventAssaultStart", function(self, assault_number)
        if not KH._event_assault_active or KH._event_assault_number ~= assault_number then
            KH._event_first_strike_awarded = false
        end
        KH._event_assault_active = true
        KH._event_assault_number = assault_number
    end)
end
if HUDManager.sync_end_assault then
    Hooks:PostHook(HUDManager, "sync_end_assault", "KH_EventAssaultEnd", function()
        KH._event_assault_active = false
    end)
end

Hooks:PostHook(HUDManager, "init_finalize", "KH_InitHUD", function()
    -- Un nouveau HUD correspond à une nouvelle partie : aucun buff, kill,
    -- score, bandeau ni série d'arme de la partie précédente ne doit survivre.
    KH:ResetHeistCombatState(true)
    KH:ensure_panel(true)
    KH:TryRegisterGameInfoBridge()
    KH:RefreshDetectedBuffs()
    log("[KyoHUD] Panneau HUD initialisé.")
end)

Hooks:PostHook(HUDManager, "update", "KH_UpdateHUD", function(self, t, dt)
    if not KH._gameinfo_bridge_active then
        KH._bridge_retry_acc = (KH._bridge_retry_acc or 0) + dt
        if KH._bridge_retry_acc >= 1 then
            KH._bridge_retry_acc = 0
            KH:TryRegisterGameInfoBridge()
        end
    elseif not KH._debug_preview_active and not KH._bridge_delayed_sync_done then
        KH._bridge_delayed_sync_acc = (KH._bridge_delayed_sync_acc or 0) + dt
        if KH._bridge_delayed_sync_acc >= 2 then
            KH._bridge_delayed_sync_done = true
            KH:SyncGameInfoBuffs()
        end
    end

    KH._value_refresh_acc = (KH._value_refresh_acc or 0) + dt
    if KH._value_refresh_acc >= 0.5 then
        KH._value_refresh_acc = 0
        KH:RefreshCalculatedBuffValues()
        KH:RefreshEquippedSkillCounters()
        KH:RefreshHackerPocketECMStatus()
    end

    KH._update_acc = (KH._update_acc or 0) + dt
    if KH._update_acc < 0.05 then return end
    KH._update_acc = 0

    if KH:ensure_panel(false) then
        KH:draw()
    end
end)
