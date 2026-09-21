-- core.lua — KyoHUD state, combat HUD and buff rendering
-- Buffs displayed side-by-side on a configurable horizontal row.
-- Buff state and metadata are provided by KyoHUD's namespaced provider.

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud
local MY_MOD_PATH = ModPath

-- ═══════════════════════════════════════════════════
-- Utilities
-- ═══════════════════════════════════════════════════
local function clamp(x, lo, hi)
    if x < lo then return lo end
    if x > hi then return hi end
    return x
end
KH.clamp = clamp

local function now()
    return TimerManager:game():time()
end
KH.now = now

local FALLBACK_TEXTURE = "guis/textures/pd2/hud_timer"
KH.FALLBACK_TEXTURE = FALLBACK_TEXTURE

-- ═══════════════════════════════════════════════════
-- Internal State
-- ═══════════════════════════════════════════════════
KH._panel       = nil
KH._buffs       = {}           -- { [id] = {id, icon, color, value_text?, stack_text?, start_t, duration, t_end?, is_debuff} }
KH._buff_sources = {}          -- { [buff_id] = { [source_key] = source_data } }
KH._source_targets = {}        -- { [source_key] = { buff_id, ... } }
KH._kills       = {}           -- { {name, score?, score_text?, start_t, t_end?} }
KH._kill_combo  = { count = 0, last_t = nil, updated_t = nil }
KH._killfeed_score_total = 0     -- current killfeed burst score
KH._killfeed_score_has_value = false
KH._heist_score_total = 0
KH._heist_score_best_streak = 0
KH._heist_score_recorded = false
KH._special_kill_banner = nil
KH._banner_queue = {}          -- Bounded FIFO: announcements awaiting display
KH._weapon_streaks = {}        -- { [family] = { count, tier_index, last_t } }
KH._heist_kill_count = 0       -- cumulative enemy kills since heist start
KH._heist_kill_medal_index = 0 -- last cumulative kill tier already announced
KH._sentry_kill_count = 0
KH._sentry_kill_medal_index = 0
KH._medal_card = nil           -- medal displayed in the killfeed row
KH._medal_queue = {}           -- Bounded FIFO, independent of the top banner
KH._spray_down_kills = 0       -- bullet kills since last reload
KH._spray_down_awarded = false -- four-kill threshold already announced for this magazine
KH._spray_down_started_t = nil -- start of current four-kill window
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
KH.KILL_COMBO_WINDOW = KILL_COMBO_WINDOW
local SPECIAL_KILL_BANNER_DURATION = 1.25
KH.SPECIAL_KILL_BANNER_DURATION = SPECIAL_KILL_BANNER_DURATION
local HUD_ACCENT_COLOR  = Color(0.52, 0.88, 0.92)
KH.HUD_ACCENT_COLOR = HUD_ACCENT_COLOR
local PRIORITY_TARGET_COLOR = Color(1, 0.38, 0.08)
local KILLFEED_SCORE_COLOR = Color(1, 0.63, 0.12)
local KILLFEED_SCORE_PENALTY_COLOR = Color(1, 0.22, 0.12)
KH.KILLFEED_SCORE_COLOR = KILLFEED_SCORE_COLOR
KH.KILLFEED_SCORE_PENALTY_COLOR = KILLFEED_SCORE_PENALTY_COLOR
dofile(MY_MOD_PATH .. "lua/ky_buff_presentation.lua")
local KYO_BUFF_CONFIG = assert(KH.KYO_BUFF_CONFIG, "KyoHUD buff presentation config is missing")
local KYO_BUFF_COLORS = assert(KYO_BUFF_CONFIG.colors, "KyoHUD buff colors are missing")
local KYO_BUFF_PRESENTATION = assert(KYO_BUFF_CONFIG.buffs, "KyoHUD buff presentation is missing")
KH.KYO_BUFF_PRESENTATION = KYO_BUFF_PRESENTATION
KH.KYO_BUFF_COLORS = KYO_BUFF_COLORS
local EMPTY_BUFF_CANDIDATES = {}

local FRAME_ANIM_CACHE = {}
local RENDER_CACHES = {
    chevrons = {},
    edge_points = {},
    progress = {},
    buff_cell_bg = {},
    buff_cell_footer = {},
    buff_cell_outline = {},
    tactical_bg = {},
    killfeed_bg = {},
    killfeed_top_edge = {},
    frame_colors = {},
    -- Reusable buffers for per-frame allocations; mutated in-place each frame.
    layout = { positions = {} },
    buff_list = {},
    extra_buffs = {},
    extra_buffs_scan = {},
    extra_buff_members = setmetatable({}, { __mode = "k" }),
    extra_buff_generation = 0,
    heist_score_bg_gradient = {},
    heist_score_edge_gradient = {},
    medal_frame_gradient = {},
    -- Pre-allocated color constants to avoid Color() allocations
    combo_colors = {
        [2] = Color(1, 0.85, 0.2),
        [3] = Color(1, 0.55, 0.1),
        [4] = Color(1, 0.2, 0.1),
        [5] = Color(0.208, 0.906, 1), -- 5+
    },
    killfeed_name_color = Color(0.86, 0.96, 1),
    killfeed_negative_score_color = Color(1, 0.36, 0.3)
}
KH.RENDER_CACHES = RENDER_CACHES
do
local function _parse_hex6(hex)
    if type(hex) ~= "string" or #hex ~= 6 then return nil end
    local h = tonumber(hex:sub(1, 2), 16)
    local s = tonumber(hex:sub(3, 4), 16)
    local v = tonumber(hex:sub(5, 6), 16)
    if not (h and s and v) then return nil end
    return h / 255, s / 255, v / 255
end

-- Pre-allocated colors for the Underdog card's split value line: the damage
-- bonus in the damage_increase tint, the damage reduction in the
-- damage_reduction tint. Derived from KYO_BUFF_COLORS so they follow the config.
do
    local br, bg, bb = _parse_hex6(KYO_BUFF_COLORS.damage_increase)
    local rr, rg, rb = _parse_hex6(KYO_BUFF_COLORS.damage_reduction)
    RENDER_CACHES.underdog_bonus_color = br and Color(br, bg, bb) or Color(1, 0.541, 0.239)
    RENDER_CACHES.underdog_reduction_color = rr and Color(rr, rg, rb) or Color(0.424, 0.549, 1)
end

for _buff_id, _pres in pairs(KYO_BUFF_PRESENTATION) do
    local _anim = _pres.frame_animation
    if _anim and _pres.frame_color
        and type(_anim.period) == "number" and _anim.period > 0 then
        local _hex_a = KYO_BUFF_COLORS[_pres.frame_color] or _pres.frame_color
        local _hex_b = KYO_BUFF_COLORS[_anim.color_b] or _anim.color_b
        local r1, g1, b1 = _parse_hex6(_hex_a)
        local r2, g2, b2 = _parse_hex6(_hex_b)
        if r1 and r2 then
            local entry = {
                r1 = r1, g1 = g1, b1 = b1,
                r2 = r2, g2 = g2, b2 = b2,
                period = _anim.period,
                tri = false,
            }
            -- Optional third color for A→B→C→A cycling. If color_c is
            -- declared but unparseable, the whole entry is rejected so the
            -- animation falls back to buff.frame_color instead of silently
            -- degrading to a two-color cycle.
            local entry_ok = true
            if _anim.color_c then
                local _hex_c = KYO_BUFF_COLORS[_anim.color_c] or _anim.color_c
                local r3, g3, b3 = _parse_hex6(_hex_c)
                if r3 then
                    entry.r3 = r3
                    entry.g3 = g3
                    entry.b3 = b3
                    entry.tri = true
                else
                    entry_ok = false
                end
            end
            if entry_ok then
                FRAME_ANIM_CACHE[_buff_id] = entry
            end
        end
    end
end
end
KH._frame_anim_cache = FRAME_ANIM_CACHE

function KH:_compute_frame_color(buff_id, t)
    local anim = FRAME_ANIM_CACHE[buff_id]
    if not anim then return nil end

    if anim.tri then
        -- Three-color cycle: A → B → C → A, linear segments over `period`.
        -- phase ∈ [0, 3): segment 0 = A→B, segment 1 = B→C, segment 2 = C→A.
        local phase = (t % anim.period) / anim.period * 3
        local segment = math.floor(phase)
        local frac = phase - segment
        local r, g, b
        if segment <= 0 then
            r = anim.r1 + (anim.r2 - anim.r1) * frac
            g = anim.g1 + (anim.g2 - anim.g1) * frac
            b = anim.b1 + (anim.b2 - anim.b1) * frac
        elseif segment == 1 then
            r = anim.r2 + (anim.r3 - anim.r2) * frac
            g = anim.g2 + (anim.g3 - anim.g2) * frac
            b = anim.b2 + (anim.b3 - anim.b2) * frac
        else
            r = anim.r3 + (anim.r1 - anim.r3) * frac
            g = anim.g3 + (anim.g1 - anim.g3) * frac
            b = anim.b3 + (anim.b1 - anim.b3) * frac
        end
        -- factor encodes segment + fraction for cache keying
        return r, g, b, phase / 3
    end

    -- Two-color sine oscillation (original behavior)
    local factor = (math.sin(2 * math.pi * t / anim.period) + 1) * 0.5
    local r = anim.r1 + (anim.r2 - anim.r1) * factor
    local g = anim.g1 + (anim.g2 - anim.g1) * factor
    local b = anim.b1 + (anim.b2 - anim.b1) * factor
    return r, g, b, factor
end

local function draw_frame_color(buff, t)
    local anim = FRAME_ANIM_CACHE[buff.id]
    if not anim then return buff.frame_color end
    
    local r, g, b, factor = KH:_compute_frame_color(buff.id, t)
    if not r then return buff.frame_color end
    
    -- Cache par (buff_id, factor_arrondi_2_decimales)
    local factor_key = math.floor(factor * 100)
    local cache_key = buff.id .. ":" .. factor_key
    local cached = RENDER_CACHES.frame_colors[cache_key]
    
    if not cached then
        cached = Color(r, g, b)
        RENDER_CACHES.frame_colors[cache_key] = cached
    end
    
    return cached
end
KH.DrawFrameColor = draw_frame_color

local function killfeed_size(settings)
    local value = tonumber(settings and settings.killfeed_size) or MAX_KILLFEED_SIZE
    return math.floor(clamp(value, 1, MAX_KILLFEED_SIZE))
end
KH.killfeed_size = killfeed_size

local function format_kill_score(score)
    if type(score) ~= "number" then return nil end

    local rounded = math.floor(score)
    local value = score == rounded
        and tostring(rounded)
        or string.format("%.1f", score)
    return (score > 0 and "+" or "") .. value
end
KH.format_kill_score = format_kill_score

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
KH.approximate_text_width = approximate_text_width

-- ═══════════════════════════════════════════════════
-- Icon Resolution — Locally adapted HUDList conventions
-- ═══════════════════════════════════════════════════
local function has_texture(path)
    if not path or not DB then return false end

    local ok, exists = pcall(function()
        return DB:has(Idstring("texture"), Idstring(path))
    end)
    return ok and exists or false
end
KH.has_texture = has_texture

--- Resolves an icon from a HUDList-compatible description table.
--- Supports: skills_new, skills, perks, hud_tweak, hud_icons, hudtabs, hudpickups, waypoints, direct texture
local function get_icon_data(icon)
    if not icon then return FALLBACK_TEXTURE, nil end

    local texture = icon.texture
    local texture_rect = icon.texture_rect
    local skills = icon.skills
    local skills_new = icon.skills_new

    -- Atlas coordinates have changed over updates. When the runtime definition knows the skill's internal name, request its position from the game and keep static coordinates only as a fallback.
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
KH.get_icon_data = get_icon_data

-- Shared descriptor for all Headshot cards. HUD name resolution and atlas cutout occur on the first relevant kill, never in draw.
local HEADSHOT_ICON_DESCRIPTOR
local function headshot_icon_descriptor()
    if not HEADSHOT_ICON_DESCRIPTOR then
        local texture, rect = get_icon_data({ hud_tweak = "pd2_kill" })
        HEADSHOT_ICON_DESCRIPTOR = { texture = texture, rect = rect }
    end
    return HEADSHOT_ICON_DESCRIPTOR
end

-- `sentry_icon_descriptor` is defined in `lua/ky_combat_medals.lua` and
-- exposed via `KH.SentryIconDescriptor`. It is the single source of truth
-- shared by medal cards and killfeed sentry icons.

-- ═══════════════════════════════════════════════════
-- Icon Resolution for a buff_id
-- ═══════════════════════════════════════════════════
function KH:GetVanillaHUDBuffDefinition(buff_id)
    local local_definitions = self.hudlist_catalog and self.hudlist_catalog.definitions
    return local_definitions and local_definitions[buff_id] or nil
end

function KH:GetKyoEquippedPerkBuffCandidates(specialization_id)
    local presentation = KYO_BUFF_PRESENTATION.equipped_perk_deck
    return presentation.perk_deck_buffs[tonumber(specialization_id)] or EMPTY_BUFF_CANDIDATES
end

function KH:HasVanillaHUDBuffProvider()
    return self.hudlist and self.hudlist.register_listener
            and self.hudlist.get_buffs and self.hudlist.get_player_actions
            and self.hudlist_catalog and type(self.hudlist_catalog.definitions) == "table"
            and type(self.hudlist_catalog.routes) == "table"
        or false
end

function KH:GetVanillaHUDBuffTargets(source_id)
    local targets = {}
    local presentation = KYO_BUFF_PRESENTATION[source_id]
    if presentation and presentation.separate_source
            and self:GetVanillaHUDBuffDefinition(source_id) then
        targets[1] = source_id
        return targets
    end
    local groups = self.hudlist_catalog and self.hudlist_catalog.routes
    local mapped = groups and groups[source_id]
    if type(mapped) ~= "table" then
        local composite_parent = groups
            and groups.composite_debuffs
            and groups.composite_debuffs[source_id]
        if composite_parent and self:GetVanillaHUDBuffDefinition(composite_parent) then
            targets[1] = composite_parent
            return targets
        end
        if self:GetVanillaHUDBuffDefinition(source_id) then
            targets[1] = source_id
        end
        return targets
    end

    for _, buff_id in ipairs(mapped) do
        if self:GetVanillaHUDBuffDefinition(buff_id) then
            table.insert(targets, buff_id)
        end
    end
    return targets
end

-- Moved to lua/ky_buff_render.lua (exposed as KH.IconForBuff, KH.ColorForBuff, etc.)

-- ═══════════════════════════════════════════════════
-- KyoHUD's individual toggles take priority over the autonomous catalog for
-- configured IDs; unlisted IDs retain their catalog visibility.
-- ═══════════════════════════════════════════════════
function KH:is_buff_visible(buff_id)
    if not self.settings or not self.settings.enable_buffs then return false end

    -- KyoHUD's individual toggles are authoritative for configured buff IDs.
    if self._BUFF_TOGGLE_SET and self._BUFF_TOGGLE_SET[buff_id] then
        return self.settings[buff_id] ~= false
    end

    -- For unlisted IDs, fall back to the autonomous catalog definition.
    if self._gameinfo_bridge_active then
        local runtime_definition = self:GetVanillaHUDBuffDefinition(buff_id)
        if runtime_definition then
            return runtime_definition.ignore ~= true
        end
    end

    return true
end

-- These active indicators always maintain the same order at the row start. An absent indicator reserves no empty slot.
local STATIC_BUFF_SLOTS = {}
for buff_id, presentation in pairs(KYO_BUFF_PRESENTATION) do
    if presentation.fixed_slot then
        STATIC_BUFF_SLOTS[presentation.fixed_slot] = buff_id
    end
end

local STATIC_BUFF_SLOT_SET = {}
for _, buff_id in ipairs(STATIC_BUFF_SLOTS) do
    STATIC_BUFF_SLOT_SET[buff_id] = true
end

function KH:get_static_buff_slots()
    return STATIC_BUFF_SLOTS
end

function KH:get_static_buff_slot_set()
    return STATIC_BUFF_SLOT_SET
end

-- Moved to lua/ky_buff_render.lua (exposed as KH.EquippedPerkDeckEntry, etc.)

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
KH.localized_text = localized_text

-- Moved to lua/ky_buff_render.lua (exposed as KH.TitleForBuff, KH.PresentationLabelForBuff)

-- Moved to lua/ky_buff_render.lua (exposed as KH.BuffLabel)

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

-- DOZER_BANNER_LABELS and BOSS_BANNER_LABELS remain in core.lua (used by SPECIAL_KILL_BANNER_DEFINITIONS at top level)
local DOZER_BANNER_LABELS = {
    { id = "ky_hud_killdozer",  fallback = "KILLDOZER" },
    { id = "ky_hud_dozer_down", fallback = "DOZER DOWN" },
    { id = "ky_hud_bulldozed",  fallback = "BULLDOZED" },
}

local BOSS_BANNER_LABELS = {
    { id = "ky_hud_boss_eliminated", fallback = "BOSS ELIMINATED" },
}

-- PRIORITY_TARGET_COLOR remains in core.lua (used by SPECIAL_KILL_BANNER_DEFINITIONS and SPECIAL_ENEMY_DEFINITIONS at top level)

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

-- ── Persistent streaks by damage/weapon family ──
-- Each family has its own counter, independent of others: a shotgun kill does not interrupt a sniper streak. Tiers are strictly increasing and each tier is crossed only once per cycle; after a time pause, the family restarts from its first tier.
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
        color = Color(0.32, 0.66, 1),               -- cool blue
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
        color = Color(1, 0.3, 0.06),                -- orange-red
        tiers = {
            { count = 3,  id = "ky_hud_streak_incendiary_3",  fallback = "BURN NOTICE" },
            { count = 6,  id = "ky_hud_streak_incendiary_6",  fallback = "INCINERATION" },
            { count = 10, id = "ky_hud_streak_incendiary_10", fallback = "HELLFIRE" },
        },
    },
    poison = {
        color = Color(0.36, 0.85, 0.29),            -- toxic green
        tiers = {
            { count = 3,  id = "ky_hud_streak_poison_3",  fallback = "TOXIC" },
            { count = 6,  id = "ky_hud_streak_poison_6",  fallback = "VENOMOUS" },
            { count = 10, id = "ky_hud_streak_poison_10", fallback = "BIOHAZARD" },
        },
    },
    melee = {
        color = Color(0.78, 0.28, 1),               -- purple / magenta
        tiers = {
            { count = 2, id = "ky_hud_streak_melee_2", fallback = "ONE-TWO" },
            { count = 3, id = "ky_hud_streak_melee_3", fallback = "BONE CRACKER" },
            { count = 4, id = "ky_hud_streak_melee_4", fallback = "PUMMEL" },
            { count = 5, id = "ky_hud_streak_melee_5", fallback = "WRECKING CREW" },
        },
    },
    explosive = {
        color = Color(1, 0.79, 0.16),               -- amber yellow
        tiers = {
            { count = 3, id = "ky_hud_streak_explosive_3", fallback = "BOOM" },
            { count = 5, id = "ky_hud_streak_explosive_5", fallback = "DEMOLITION" },
            { count = 8, id = "ky_hud_streak_explosive_8", fallback = "BLAST ZONE" },
        },
    },
}


-- Gold: the cumulative medal distinguishes itself from weapon family colors.
function KH:GetKillMedalIconDescriptor()
    if self._kill_medal_icon_descriptor then return self._kill_medal_icon_descriptor end

    local texture = "guis/dlcs/deep/textures/pd2/pre_planning/preplan_icon_types"
    local rect = { 240, 0, 48, 48 }
    pcall(function()
        local preplanning = tweak_data and tweak_data.preplanning
        local gui = preplanning and preplanning.gui
        texture = gui and gui.type_icons_path or texture
        if preplanning and preplanning.get_type_texture_rect then
            rect = preplanning:get_type_texture_rect(61) or rect
        end
    end)

    self._kill_medal_icon_descriptor = { texture = texture, rect = rect }
    return self._kill_medal_icon_descriptor
end

-- Medal constants, medal card constructors, medal rendering helpers,
-- and `KH.SentryIconDescriptor` are defined in `lua/ky_combat_medals.lua`,
-- loaded after core.lua in the hudmanagerpd2 context. They are exposed via
-- KH (KH.EVENT_MEDAL_DEFINITIONS, KH.MakeKillMedalCard, KH.SentryIconDescriptor,
-- KH.DrawMedalFrame, etc.) and referenced through KH in core.lua.

-- Medal families sharing the killfeed row. A card's `kind` decides only what a reset clears: rendering, duration, and queue are identical for all.
-- `KH.MEDAL_KIND_WEAPON_STREAK` lives in ky_combat_medals.lua and is referenced via KH.

-- The top banner is exclusively reserved for multikill, boss, and Dozer. Display priority: boss > dozer. Multikill does not enter the queue: it remains the fallback displayed when no priority announcement occupies the banner. Medals have their own row in the killfeed and never appear here.
-- BANNER_PRIORITIES now provided by ky_hud_banners.lua via KH.BANNER_PRIORITIES

-- Bounded: a few announcements suffice to cover a salvo, and the queue must never grow without limit during an assault.
-- MAX_BANNER_QUEUE now provided by ky_hud_banners.lua via KH.MAX_BANNER_QUEUE

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
KH.SPECIAL_ENEMY_DEFINITIONS = SPECIAL_ENEMY_DEFINITIONS

local function combo_label(count, variant_index)
    local variants = COMBO_LABELS[count]
    local definition = variants and variants[variant_index or 1]
    if definition then
        return localized_text(definition.id, definition.fallback)
    end
    return localized_text("ky_hud_combo_chain", "KILL CHAIN") .. " x" .. tostring(count)
end
KH.combo_label = combo_label

-- Cache combo colors to avoid Color() allocation on every frame
-- Bounded to 4 entries: keys 2,3,4,5 (where 5 represents 5+)

-- A banner directly carries its label and color. `KH:draw` therefore
-- has no definitions table to traverse, and a new announcement family
-- branches without touching the renderer.
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

--- Tier medal: it directly carries its label and color, like a banner,
--- but it is rendered in the killfeed and has neither unit name nor
--- score to display.
local function make_weapon_streak_card(family, tier_index)
    local definition = weapon_streak_definition(family)
    local tier = definition and definition.tiers[tier_index]
    if not tier then return nil end

    return {
        kind   = KH.MEDAL_KIND_WEAPON_STREAK,
        family = family,
        label  = localized_text(tier.id, tier.fallback),
        color  = definition.color or HUD_ACCENT_COLOR,
    }
end

--- A reload opens a new magazine for Spray Down. The caller guarantees it
--- is the local player's weapon.
function KH:ResetSprayDownMagazine()
    self._spray_down_kills = 0
    self._spray_down_awarded = false
    self._spray_down_started_t = nil
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


-- ═══════════════════════════════════════════════════
-- Public API: add/remove buffs
-- ═══════════════════════════════════════════════════
function KH:add_buff(buff_id, icon_data, duration, _raw_upgrade_id, persistent, is_debuff, value_text, stack_text)
    if not self.settings or not self.settings.enable_buffs then return end

    local resolved_id = buff_id

    -- Check if this buff is visible in settings
    if not self:is_buff_visible(resolved_id) then return end

    local dur = tonumber(duration)
    if not persistent then
        dur = dur or DEFAULT_TEMPORARY_BUFF_DURATION
    end
    local t = now()
    local runtime_definition = self:GetVanillaHUDBuffDefinition(resolved_id)

    -- A refreshed buff keeps its row position (original order_t),
    -- only its timer and fade (start_t) restart from zero
    local existing = self._buffs[resolved_id]
    local label_text, label_placement = KH.PresentationLabelForBuff(resolved_id)
    local presentation = KYO_BUFF_PRESENTATION[resolved_id]

    self._buffs[resolved_id] = {
        id       = resolved_id,
        icon     = icon_data or KH.IconForBuff(resolved_id),
        color    = KH.ColorForBuff(resolved_id, is_debuff),
        frame_color = KH.FrameColorForBuff(resolved_id),
        priority = tonumber(runtime_definition and runtime_definition.priority) or 0,
        provider_class = runtime_definition and runtime_definition.class or nil,
        title_text = KH.TitleForBuff(resolved_id),
        label_text = label_text,
        label_placement = label_placement,
        value_text = value_text,
        value_text_split = presentation and presentation.value_text_split == true or nil,
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
    self._buffs[buff_id] = nil
end

-- ═══════════════════════════════════════════════════
-- Buff sources and autonomous provider bridge
-- ═══════════════════════════════════════════════════

function KH:handle_buff_event(event, source_id, data, source_type)
    if not source_id or not self._gameinfo_bridge_active then return end

    local targets = self:GetVanillaHUDBuffTargets(source_id)
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

    local old_targets = self._source_targets[source_key]
    if #targets == 0 and not old_targets then return end

    local activates = event == "activate"
        or event == "set_duration"
        or event == "add_timed_stack"
        or event == "set_data"

    if not activates and not old_targets then
        return
    end

    if old_targets then
        local current_targets = {}
        for _, buff_id in ipairs(targets) do
            current_targets[buff_id] = true
        end
        for _, buff_id in ipairs(old_targets) do
            if not current_targets[buff_id] then
                local sources = self._buff_sources[buff_id]
                if sources then
                    sources[source_key] = nil
                    if not next(sources) then
                        self._buff_sources[buff_id] = nil
                    end
                end
                self:_refresh_source_target(buff_id)
            end
        end
    end

    self._source_targets[source_key] = #targets > 0 and targets or nil
    for _, buff_id in ipairs(targets) do
        self._buff_sources[buff_id] = self._buff_sources[buff_id] or {}
        local source = self._buff_sources[buff_id][source_key] or {}
        if type(data) == "table" then
            for key, value in pairs(data) do
                source[key] = value
            end
            if data.duration and not data.t
                and (event == "activate" or event == "set_duration") then
                source.t = KH.ApplicationTime()
            end
        end
        if event == "set_value" and (not data or data.value == nil) then
            source.value = nil
        elseif event == "set_stack_count" and (not data or data.stack_count == nil) then
            source.stack_count = nil
        end
        if event == "add_timed_stack" or event == "remove_timed_stack" then
            source._timed_stacks = true
        end
        source.source_id = source_id
        source.is_debuff = string.match(tostring(source_id), "_debuff$") ~= nil
        self._buff_sources[buff_id][source_key] = source
        self:_refresh_source_target(buff_id)
    end
end

function KH:SyncGameInfoBuffs()
    local provider = self.hudlist
    if self._debug_preview_active or not provider then return end

    local ok_buffs, buffs = pcall(function()
        return provider:get_buffs()
    end)
    if ok_buffs and type(buffs) == "table" then
        for id, data in pairs(buffs) do
            self:handle_buff_event("activate", id, data, "gameinfo_buff")
        end
    end

    local ok_actions, actions = pcall(function()
        return provider:get_player_actions()
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
    if not self:HasVanillaHUDBuffProvider() then
        return false
    end

    local provider = self.hudlist
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
            provider:register_listener("kyohud_buff_bridge", "buff", event, buff_callback)
        end
        for _, event in ipairs(action_events) do
            provider:register_listener("kyohud_action_bridge", "player_action", event, action_callback)
        end
    end)
    if not ok then
        if not self._gameinfo_bridge_error_logged then
            self._gameinfo_bridge_error_logged = true
            log("[KyoHUD] Buff provider bridge unavailable: " .. tostring(err))
        end
        return false
    end

    -- Replace the already observed local sources with the reference status of the
    -- manager so that future deactivation leaves nothing blocked.
    self._buff_sources = {}
    self._source_targets = {}
    self._buffs = {}
    self._gameinfo_bridge_active = true
    self._gameinfo_bridge_callbacks = { buff_callback, action_callback }
    self:SyncGameInfoBuffs()
    log("[KyoHUD] Buff presentation linked to the available provider.")
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
-- Priority banner: current display and queue
-- ═══════════════════════════════════════════════════
function KH:_start_special_banner(t, banner, preview)
    banner.preview = preview == true
    banner.started_t = t
    banner.t_end = t + SPECIAL_KILL_BANNER_DURATION
    self._special_kill_banner = banner
end

--- Insertion into the bounded queue, kept sorted boss > dozer. When it is
--- full, only a more prioritized announcement enters, replacing the last
--- of the less prioritized ones; an announcement of equal or lower priority than the
--- lowest pending one is simply discarded.
function KH:_enqueue_special_banner(banner)
    if not banner then return end

    local banner_priority = self.BannerPriority
    local banner_queue_insert_index = self.BannerQueueInsertIndex

    local queue = self._banner_queue
    if not queue then
        queue = {}
        self._banner_queue = queue
    end

    local priority = banner_priority(banner)

    while #queue >= KH.MAX_BANNER_QUEUE do
        -- The queue remains sorted: its last entry is always the least
        -- prioritized and, at equal priority, the most recently added.
        if banner_priority(queue[#queue]) >= priority then return end
        table.remove(queue)
    end

    table.insert(queue, banner_queue_insert_index(queue, priority), banner)
end

--- Presents an announcement. A prioritized target immediately takes the banner
--- and returns the current announcement to the queue: nothing is lost.
function KH:_show_special_banner(t, banner, preview)
    if not banner then return end

    if preview then
        self:_start_special_banner(t, banner, true)
        return
    end

    local current = self._special_kill_banner
    -- A debug preview never blocks a real announcement.
    if current and not current.preview then
        local banner_priority = self.BannerPriority
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
-- Medals: dedicated row in the killfeed
-- ═══════════════════════════════════════════════════
-- Strictly separated from the top banner: a medal never competes with a boss or a Dozer, and both can be visible at the same time on two distinct levels.
--
-- All medal families — weapon streak medals, event medals,
--
-- cumulative kill tiers, and sentry tiers — share this same level, this
-- same rendering, this same duration, and this same bounded FIFO queue. Only the
-- card construction differs.
function KH:_start_medal_card(t, card, preview)
    card.preview = preview == true
    card.started_t = t
    card.t_end = t + KH.MEDAL_CARD_DURATION
    self._medal_card = card
end

--- Presents a medal already constructed. All have the same merit: the one already
--- displayed keeps its place and the following ones chain in arrival order.
--- An extra medal is discarded rather than lengthening the queue: the tier
--- remains earned, only its announcement is lost.
---

--- A single kill can produce several — up to one weapon streak medal, a few
--- events, and a cumulative tier. The limit remains intentionally low: active
--- card plus `KH.MAX_MEDAL_QUEUE` places, so at most four chained announcements
--- of about 1.75 s. Lengthening the queue would scroll the row well after the
--- kill that triggered it.
function KH:_show_medal_card(t, card, preview)
    if not card then return end

    local queue = self._medal_queue
    if not queue then
        queue = {}
        self._medal_queue = queue
    end

    local current = self._medal_card
    -- A debug preview replaces everything and never accumulates.
    if preview then
        for index = #queue, 1, -1 do queue[index] = nil end
        self:_start_medal_card(t, card, true)
        return
    end

    -- A preview does not block a real medal.
    if current and not current.preview then
        if #queue < KH.MAX_MEDAL_QUEUE then
            table.insert(queue, card)
        end
        return
    end

    self:_start_medal_card(t, card, false)
end

--- Clears medals from the shared row. Without `kind`, everything disappears;
--- with a `kind`, other families keep their active card and their place
--- in the queue. Cumulative and sentry medals therefore survive a weapon streak reset.
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

--- Counts a kill for its family and returns the index of the tier crossed.
--- `t` is the kill time, already calculated by `KH:add_kill`: each family
--- maintains its own timer, based on the multikill one, and no
--- clock is read here.
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

    -- Defensive fallback: a caller without time should not freeze the family timer. `add_kill` always passes its `t`; `now()` serves only for this fallback.
    t = tonumber(t) or now()

    -- Timer strictly specific to this family: kills from other families
    -- do not refresh nor reset it. The limit remains inclusive,
    -- exactly like the multikill window.
    if streak.last_t and (t - streak.last_t) > KILL_COMBO_WINDOW then
        streak.count = 0
        streak.tier_index = 0
    end
    streak.last_t = t
    streak.count = streak.count + 1

    -- Only one tier can be awarded per kill: compare only with the next tier.
    -- Once the maximum is announced, `next_tier` is nil and the streak remains
    -- silent until its expiration, which rearms the first tier.
    local next_tier = tiers[streak.tier_index + 1]
    if not next_tier or streak.count < next_tier.count then
        return nil
    end

    streak.tier_index = streak.tier_index + 1
    return streak.tier_index
end

--- Counts an enemy kill in the heist total and returns the crossed tier,
--- or `nil`. No timer intervenes: the counter only increases and
--- survives a player down. Since the total advances by one per kill, each tier is
--- reached exactly, and only one can be awarded per kill.
function KH:_register_heist_kill()
    local count = (self._heist_kill_count or 0) + 1
    self._heist_kill_count = count

    local next_index = (self._heist_kill_medal_index or 0) + 1
    local threshold = KH.KILL_MEDAL_THRESHOLDS[next_index]
    if not threshold or count < threshold then return nil end

    self._heist_kill_medal_index = next_index
    return threshold
end

function KH:_register_sentry_kill()
    local count = (self._sentry_kill_count or 0) + 1
    self._sentry_kill_count = count

    local next_index = (self._sentry_kill_medal_index or 0) + 1
    local threshold = KH.SENTRY_KILL_MEDAL_THRESHOLDS[next_index]
    if not threshold or count < threshold then return nil end

    self._sentry_kill_medal_index = next_index
    return threshold
end

--- Weapon streak reset: counters restart from zero and any
--- streak medal still displayed or pending disappears, as it no longer
--- rewards an active streak. Boss and Dozer announcements remain
--- intact: they celebrate an already earned kill, independent of streaks. Cumulative
--- kill medals also remain: their tier is permanently earned for the heist and only `KH:ResetHeistCombatState` clears them.
function KH:ResetWeaponStreaks()
    self._rope_streak = nil
    self._weapon_streaks = {}
    self:_clear_medal_cards(KH.MEDAL_KIND_WEAPON_STREAK)
end

-- ═══════════════════════════════════════════════════
-- Reset of a heist's combat state
-- ═══════════════════════════════════════════════════

--- Clears in place the kill deduplication table held by
--- `ky_killfeed.lua`. It may not exist yet depending on script load order.
--- It is never replaced: its weak-key metatable must survive the reset, otherwise
--- registered units would be retained in memory until the next mod reload.
local function clear_recorded_kill_units(hud)
    local recorded = hud._recorded_kill_units
    if type(recorded) ~= "table" then return end

    for unit in pairs(recorded) do
        recorded[unit] = nil
    end
end

--- Resets all heist-specific combat state: displayed buffs and
--- their sources, killfeed and its score, multikill, priority banners,
--- weapon streaks, sentry tiers, and special combos. A heist should never
--- inherit the state of the previous one, nor a debug preview left
--- displayed.
---

--- What does not belong to a heist is intentionally preserved: settings,
--- presentation config, KyoHUD panel, and VanillaHUD+ bridge listeners. During a new heist,
--- `rearm_bridge_sync` rearms deferred synchronization to repopulate real buffs without
--- re-registering listeners. A simple preview clear instead preserves the current latch
--- to avoid injecting real buffs into demo cells.
function KH:ResetHeistCombatState(rearm_bridge_sync)
    self._debug_preview_active = false
    self._event_assault_active = false
    self._event_assault_number = nil
    self._event_first_strike_awarded = false
    self._first_blood_done = false
    self._last_weapon_switch_t = nil
    self._last_breath_medal_t = nil
    self._revenge_targets = setmetatable({}, { __mode = "k" })

    self._buffs = {}
    self._buff_sources = {}
    self._source_targets = {}
    if rearm_bridge_sync and self.hudlist and self.hudlist.reset then
        self.hudlist:reset()
    end
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
    -- The heist kill total and its tiers belong only to the current heist:
    -- they survive player downs, but never a new heist.
    self._heist_kill_count = 0
    self._heist_kill_medal_index = 0
    self._sentry_kill_count = 0
    self._sentry_kill_medal_index = 0
    self:ResetSprayDownMagazine()
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
-- Public API: add a kill to the killfeed
-- ═══════════════════════════════════════════════════
-- Rappel streak independent of weapon families. Only its own kills
-- refresh the window; a tier is announced only once per streak.
function KH:_register_rope_kill(t)
    local streak = self._rope_streak
    if not streak or t < streak.last_t or t - streak.last_t > KILL_COMBO_WINDOW then
        streak = { count = 0, tier_index = 0, last_t = t }
        self._rope_streak = streak
    end
    streak.count = streak.count + 1
    streak.last_t = t
    local next_index = streak.tier_index + 1
    local tier = KH.EVENT_MEDAL_DEFINITIONS.rope.tiers[next_index]
    if tier and streak.count >= tier.count then
        streak.tier_index = next_index
        return next_index
    end
end

function KH:add_kill(enemy_name, score, contributes_to_combo, special_banner, special_enemy_kind, weapon_family, event_info, kill_source)
    -- enable_killfeed controls rendering only: scores, streaks, and medal states
    -- continue advancing while masked, as on dev.
    if not self.settings then return end

    local is_sentry = kill_source == "sentry"
    local first_strike = not is_sentry and contributes_to_combo ~= false
        and self._event_assault_active and not self._event_first_strike_awarded
    if first_strike then self._event_first_strike_awarded = true end
    local first_blood = not is_sentry and contributes_to_combo ~= false
        and not self._first_blood_done and (self._heist_kill_count or 0) == 0
    if first_blood then self._first_blood_done = true end
    local t = now()
    local rope_tier = not is_sentry and contributes_to_combo ~= false
        and event_info and event_info.rope
        and self:_register_rope_kill(t) or nil

    local dur = KILLFEED_ENTRY_DURATION
    if contributes_to_combo ~= false and not is_sentry then
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
    if not is_sentry and special_banner == "dozer" then
        self:_show_dozer_banner(t, false)
    elseif not is_sentry and special_banner == "boss" then
        self:_show_boss_banner(t, false)
    end

    -- Medals live in the killfeed: they never compete with a prioritized target for the
    -- top banner; both can coexist.
    -- A single kill can produce several; the emission order below
    -- is therefore fixed, and it decides which card is displayed first and
    -- the order of the common FIFO queue:
    --   weapon streak medal -> event medals -> cumulative kill tier.
    local streak_tier_index = not is_sentry and weapon_family
        and self:_register_weapon_family_kill(weapon_family, t)
        or nil
    if streak_tier_index then
        self:_show_medal_card(
            t, make_weapon_streak_card(weapon_family, streak_tier_index), false
        )
    end

    -- `event_info` carries engine states already read by `ky_killfeed.lua`.
    -- First Strike and rappel tiers are resolved above, even while the HUD is hidden.
    -- Cards follow the fixed order of `KH.EVENT_MEDAL_ORDER`. Beyond the
    -- active card and `KH.MAX_MEDAL_QUEUE` queue places, subsequent medals
    -- are discarded: they open no tier to catch up.
    if contributes_to_combo ~= false and not is_sentry then
        if event_info then event_info.spray_down = false end
        if event_info and event_info.magazine_kill and not self._spray_down_awarded then
            local started_t = tonumber(self._spray_down_started_t)
            if started_t == nil or t < started_t or t - started_t > KH.SPRAY_DOWN_WINDOW then
                self._spray_down_started_t = t
                self._spray_down_kills = 1
            else
                self._spray_down_kills = (self._spray_down_kills or 0) + 1
            end
            if self._spray_down_kills >= 4 then
                self._spray_down_awarded = true
                event_info.spray_down = true
            end
        end
        for _, event_id in ipairs(KH.EVENT_MEDAL_ORDER) do
            local triggered
            if event_id == "first_strike" then
                triggered = first_strike
            elseif event_id == "first_blood" then
                triggered = first_blood
            elseif event_id == "rope" then
                triggered = rope_tier ~= nil
            else
                triggered = event_info and event_info[event_id]
            end
            if triggered and event_id == "low_hp" then
                local previous_t = tonumber(self._last_breath_medal_t)
                triggered = previous_t == nil
                    or t < previous_t
                    or t - previous_t >= KH.LAST_BREATH_MEDAL_COOLDOWN
                if triggered then self._last_breath_medal_t = t end
            end
            if triggered then
                self:_show_medal_card(t, KH.MakeEventMedalCard(event_id, rope_tier), false)
            end
        end
    end

    -- Holdup cumulative kills: they depend neither on weapon, nor score, nor
    -- a time window. Only an enemy kill counts; `RecordScoredKill`
    -- marks civilians with `contributes_to_combo == false`, and its
    -- unit deduplication guarantees a kill is counted only once.
    -- The tier comes last: it is rare, and the counter earns it even
    -- if the queue overflows and its announcement is lost.
    if contributes_to_combo ~= false then
        local kill_medal_count = self:_register_heist_kill()
        if kill_medal_count then
            self:_show_medal_card(t, KH.MakeKillMedalCard(kill_medal_count), false)
        end
        if is_sentry then
            local sentry_medal_count = self:_register_sentry_kill()
            if sentry_medal_count then
                self:_show_medal_card(
                    t, KH.MakeSentryKillMedalCard(sentry_medal_count), false
                )
            end
        end
    end

    -- The score represents all points produced during a continuous
    -- killfeed appearance. A card removed by the 1 to 5 entry limit
    -- therefore keeps its points until the last card expires.
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
    local special_definition = not is_sentry
        and special_enemy_definition(special_enemy_kind) or nil
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
        headshot   = not is_sentry and event_info ~= nil and event_info.headshot == true,
        sentry     = is_sentry,
        sentry_icon = is_sentry and KH.SentryIconDescriptor() or nil,
        special_kind = special_definition and special_enemy_kind or nil,
        display_text = special_enemy_label(
            special_enemy_kind,
            special_label_index,
            special_count
        ),
        start_t    = t,
        t_end      = t + dur,
    }
    if entry.headshot then
        entry.headshot_icon = headshot_icon_descriptor()
    end
    table.insert(self._kills, entry)

    while #self._kills > killfeed_size(self.settings) do
        table.remove(self._kills, 1)
    end
end

-- ═══════════════════════════════════════════════════
-- HUD Panel
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
-- Layout: horizontal row centered on a screen percentage position.
-- The gap closes first, then every buff metric scales together. If the row
-- still cannot fit at the readable minimum, its last slot becomes a +N cell.
-- ═══════════════════════════════════════════════════
local BUFF_ROW_EDGE_MARGIN = 4
local BUFF_ROW_MIN_ICON_SIZE = 20

function KH.compute_buff_row_layout(
        count, x_percent, y_percent, panel_w, panel_h, icon_size, frame_pad_x, frame_pad_y,
        top_label_height, layout)
    layout = layout or { positions = {} }
    local positions = layout.positions
    count = math.max(0, math.floor(tonumber(count) or 0))
    panel_w = math.max(0, tonumber(panel_w) or 0)
    panel_h = math.max(0, tonumber(panel_h) or 0)
    icon_size = math.max(1, tonumber(icon_size) or 32)
    frame_pad_x = math.max(0, tonumber(frame_pad_x) or 0)
    frame_pad_y = math.max(0, tonumber(frame_pad_y) or 0)

    local preferred_cell_w = icon_size + frame_pad_x * 2
    local preferred_gap = clamp(icon_size * 0.25, 4, 12)
    local available_w = math.max(0, panel_w - BUFF_ROW_EDGE_MARGIN * 2)
    local effective_size = icon_size
    local scale = 1
    local cell_w = preferred_cell_w
    local gap = preferred_gap
    local visible_count = count
    local hidden_count = 0
    local slot_count = count

    if count == 0 then
        -- Trim any leftover slots from a previous larger frame
        for i = 1, #positions do
            positions[i] = nil
        end
        layout.effective_size = effective_size
        layout.frame_pad_x = frame_pad_x
        layout.frame_pad_y = frame_pad_y
        layout.cell_w = cell_w
        layout.gap = gap
        layout.pitch = cell_w + gap
        layout.scale = scale
        layout.visible_count = 0
        layout.hidden_count = 0
        layout.slot_count = 0
        layout.overflow_text = nil
        return layout
    end

    local preferred_row_w = preferred_cell_w * count
        + preferred_gap * math.max(0, count - 1)
    if preferred_row_w > available_w then
        gap = count > 1
            and math.max(0, (available_w - preferred_cell_w * count) / (count - 1))
            or 0
    end

    if preferred_cell_w * count > available_w then
        local fit_scale = available_w / (preferred_cell_w * count)
        local minimum_scale = math.min(1, BUFF_ROW_MIN_ICON_SIZE / icon_size)

        if fit_scale >= minimum_scale then
            scale = fit_scale
        else
            scale = minimum_scale
            cell_w = preferred_cell_w * scale
            local capacity = math.floor(available_w / cell_w + 0.000001)

            -- A pathologically narrow panel still gets one complete explicit
            -- slot. This emergency branch may go below the readable minimum,
            -- because staying inside KyoHUD's panel is the stronger invariant.
            if capacity < 1 then
                capacity = 1
                scale = available_w / preferred_cell_w
                cell_w = available_w
            end

            slot_count = math.min(count, capacity)
            if slot_count < count then
                visible_count = math.max(0, slot_count - 1)
                hidden_count = count - visible_count
            end
        end

        effective_size = icon_size * scale
        frame_pad_x = frame_pad_x * scale
        frame_pad_y = frame_pad_y * scale
        cell_w = effective_size + frame_pad_x * 2
        gap = 0
    end

    local pitch = cell_w + gap
    local row_w = slot_count > 0
        and cell_w + pitch * (slot_count - 1)
        or 0
    local anchor_x = panel_w * clamp(x_percent, 0, 100) / 100
    local row_left = clamp(
        anchor_x - row_w * 0.5,
        BUFF_ROW_EDGE_MARGIN,
        math.max(BUFF_ROW_EDGE_MARGIN, panel_w - BUFF_ROW_EDGE_MARGIN - row_w)
    )

    -- Keep the value above, the frame and timer below the icon in the panel.
    local min_y = effective_size * 0.5 + frame_pad_y
        + (top_label_height or 18) * scale + BUFF_ROW_EDGE_MARGIN
    local max_y = panel_h - effective_size * 0.5 - 22 * scale
    local y = clamp(panel_h * clamp(y_percent, 0, 100) / 100, min_y, max_y)
    local first_x = row_left + cell_w * 0.5

    -- Reuse the module-level positions buffer to avoid allocating
    -- per-frame {x,y} tables. The consumer only reads positions
    -- during the current frame.
    for i = 1, slot_count do
        local slot = positions[i]
        if not slot then
            slot = { x = 0, y = 0 }
            positions[i] = slot
        end
        slot.x = first_x + pitch * (i - 1)
        slot.y = y
    end
    -- Trim trailing slots left over from a larger previous frame
    for i = slot_count + 1, #positions do
        positions[i] = nil
    end

    layout.effective_size = effective_size
    layout.frame_pad_x = frame_pad_x
    layout.frame_pad_y = frame_pad_y
    layout.cell_w = cell_w
    layout.gap = gap
    layout.pitch = pitch
    layout.scale = scale
    layout.visible_count = visible_count
    layout.hidden_count = hidden_count
    layout.slot_count = slot_count
    layout.overflow_text = hidden_count > 0 and ("+" .. tostring(hidden_count)) or nil
    return layout
end


-- ══════════════════════════════════════════════════
-- Dessin du HUD
-- ═══════════════════════════════════════════════════
function KH:draw()
    if not (self._panel and alive(self._panel)) then return end

    local s = self.settings
    if not s then return end

    local t = now()

    -- Purge expired buffs
    for id, b in pairs(self._buffs) do
        if b.t_end and b.t_end <= t then
            self._buffs[id] = nil
        end
    end

    -- Purge expired kills in a single pass (O(n) instead of O(n²) with table.remove)
    local write = 1
    for read = 1, #self._kills do
        local kill = self._kills[read]
        if not (kill.t_end and kill.t_end <= t) then
            self._kills[write] = kill
            write = write + 1
        end
    end
    for i = write, #self._kills do
        self._kills[i] = nil
    end
    -- End of continuous burst: the row score restarts from zero. The total
    -- and best burst total of the heist, however, survive — they are
    -- cleared only by ResetHeistCombatState.
    if #self._kills == 0 then
        self._killfeed_score_total = 0
        self._killfeed_score_has_value = false
    end

    -- A streak ends after a few seconds without a new kill.
    local combo = self._kill_combo
    if combo and not combo.preview and combo.last_t
            and (t - combo.last_t) > KILL_COMBO_WINDOW then
        combo.count = 0
        combo.last_t = nil
        combo.updated_t = nil
        combo.label = nil
    end

    -- The special announcement briefly masks the multikill, which resumes
    -- as long as its own three-second window remains active. Upon expiration,
    -- the next queue announcement chains immediately.
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

    -- The medal follows the same cycle on its own state: it expires alone and
    -- makes room for the next one if pending, regardless of family. The queue is
    -- scanned only at this expiration.
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

    -- Clean the panel to redraw
    self._panel:clear()

    local w = self._panel:w()
    local h = self._panel:h()
    local cx = w * 0.5
    local cy = h * 0.5
    local radius    = clamp(s.circle_radius or 250, 128, 291)
    local size      = clamp(s.icon_size or 32, 32, 40)
    local alpha     = clamp(s.opacity or 0.9, 0.1, 1.0)

    -- ── Draw buffs ──
    if s.enable_buffs and self._gameinfo_bridge_active then
        -- Reuse module-level buffers to avoid per-frame allocations.
        local buff_list = RENDER_CACHES.buff_list
        for index = #buff_list, 1, -1 do buff_list[index] = nil end
        local promoted_perk_buff_id

        -- Priority indicators open the row in chosen order,
        -- but only the equipped deck and actually active buffs appear.
        -- An active buff associated with the deck replaces its placeholder at position 1.
        for _, buff_id in ipairs(STATIC_BUFF_SLOTS) do
            if self:is_buff_visible(buff_id) then
                local buff
                if buff_id == "equipped_perk_deck" then
                    buff, promoted_perk_buff_id = KH.ActiveEquippedPerkBuff(self)
                    buff = buff or KH.EquippedPerkDeckEntry(self)
                else
                    buff = self._buffs[buff_id]
                end
                if buff and buff.icon then
                    buff_list[#buff_list + 1] = buff
                end
            end
        end

        local extra_buffs = RENDER_CACHES.extra_buffs
        local extra_buffs_scan = RENDER_CACHES.extra_buffs_scan
        for index = #extra_buffs_scan, 1, -1 do extra_buffs_scan[index] = nil end
        RENDER_CACHES.extra_buff_generation = RENDER_CACHES.extra_buff_generation + 1
        local extra_buff_generation = RENDER_CACHES.extra_buff_generation
        for _, b in pairs(self._buffs) do
            if b.icon and b.id ~= promoted_perk_buff_id
                    and not STATIC_BUFF_SLOT_SET[b.id] and self:is_buff_visible(b.id) then
                extra_buffs_scan[#extra_buffs_scan + 1] = b
                RENDER_CACHES.extra_buff_members[b] = extra_buff_generation
            end
        end
        local extra_buffs_changed = #extra_buffs_scan ~= #extra_buffs
        if not extra_buffs_changed then
            for index = 1, #extra_buffs do
                if RENDER_CACHES.extra_buff_members[extra_buffs[index]] ~= extra_buff_generation then
                    extra_buffs_changed = true
                    break
                end
            end
        end
        if extra_buffs_changed then
            for index = #extra_buffs, 1, -1 do extra_buffs[index] = nil end
            for index = 1, #extra_buffs_scan do extra_buffs[index] = extra_buffs_scan[index] end
            -- Sort only when the visible membership changes. Arrival metadata is
            -- stable for the lifetime of an entry.
            table.sort(extra_buffs, KH.CompareBuffArrival)
        end
        for _, buff in ipairs(extra_buffs) do
            buff_list[#buff_list + 1] = buff
        end

        local preferred_frame_pad_x = clamp(size * 0.16, 4, 9)
        local preferred_frame_pad_y = clamp(size * 0.08, 2, 4)
        -- A single row suffices as long as a top label and value do not
        -- coexist; once a cell carries both, the top margin becomes two lines. A label placed in the timer remains under
        -- the icon and never consumes this margin.
        local top_label_height = 18
        for _, buff in ipairs(buff_list) do
            if buff.value_text then
                local label_text, label_placement = KH.BuffLabel(buff)
                if label_text and label_placement == KH.BUFF_LABEL_TOP then
                    top_label_height = 35
                    break
                end
            end
        end
        local layout = self.compute_buff_row_layout(
            #buff_list,
            tonumber(s.buff_position_x) or 50,
            tonumber(s.buff_position_y) or 85,
            w,
            h,
            size,
            preferred_frame_pad_x,
            preferred_frame_pad_y,
            top_label_height,
            RENDER_CACHES.layout
        )
        local buff_size = layout.effective_size
        local frame_pad_x = layout.frame_pad_x
        local frame_pad_y = layout.frame_pad_y
        local buff_text_scale = layout.scale
        local buff_text_h = math.max(10, 16 * buff_text_scale)
        local buff_text_gap = 2 * buff_text_scale

        for idx = 1, layout.visible_count do
            local buff = buff_list[idx]
            local pos = layout.positions[idx]
            if pos then
                -- The visual state is resolved once per rendered buff: it
                -- controls the cell's opacity, perimeter outline, and
                -- timer color. The static frame, however, remains
                -- identical for all states.
                local state = KH.ResolveBuffState(buff, t)

                -- Dynamic alpha: decreases as the buff expires, but an alert state
                -- rises to full opacity to remain visible.
                local buff_alpha = alpha * (0.4 + 0.6 * (state.progress or 1))
                buff_alpha = buff_alpha + (alpha - buff_alpha) * state.emphasis
                buff_alpha = buff_alpha * state.alpha_scale

                -- Each buff retains its own cell, subtle enough that
                -- the icon and timer remain the dominant information.
                local frame_x = pos.x - buff_size * 0.5 - frame_pad_x
                local frame_y = pos.y - buff_size * 0.5 - frame_pad_y
                local frame_w = buff_size + frame_pad_x * 2
                local frame_h = buff_size + frame_pad_y * 2

                KH.DrawBuffCellFrame(
                    self._panel,
                    frame_x,
                    frame_y,
                    frame_w,
                    frame_h,
                    buff_alpha * (0.72 + 0.28 * state.emphasis),
                    98,
                    KH.DrawFrameColor(buff, t)
                )

                -- Hourly perimeter outline, reserved for temporary buffs:
                -- a permanent indicator has no `progress` and thus never receives one.
                if state.progress then
                    KH.DrawTimedBuffProgress(
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
                    w = buff_size,
                    h = buff_size,
                    x = pos.x - buff_size / 2,
                    y = pos.y - buff_size / 2,
                }

                if buff.icon.rect then
                    params.texture = buff.icon.texture
                    params.texture_rect = buff.icon.rect
                else
                    params.texture = buff.icon.texture
                    params.texture_rect = nil
                end

                local bmp = self._panel:bitmap(params)
                bmp:set_color(buff.color or Color.white)
                bmp:set_alpha(buff_alpha)

                if buff.icon.rotation then
                    bmp:set_rotation(buff.icon.rotation)
                end

                -- A top label occupies the line just above the frame and
                -- shifts the value down by an additional line. A placement
                -- label « timer » drops below the icon: the value then keeps
                -- its single line above the frame.
                local label_text, label_placement = KH.BuffLabel(buff)
                local top_label = label_text and label_placement == KH.BUFF_LABEL_TOP and label_text or nil
                local timer_label = label_text and label_placement == KH.BUFF_LABEL_TIMER and label_text or nil
                if buff.value_text and buff.value_text_split then
                    -- Underdog: draw the "+X%|-Y%" line as colored segments —
                    -- bonus in the damage-increase tint, reduction in the
                    -- damage-reduction tint — laid out centered on the frame.
                    local vt_font = tweak_data.menu.pd2_small_font or "fonts/font_small_mf"
                    local vt_font_size = math.max(8, clamp(size * 0.38, 11, 15) * buff_text_scale)
                    local vt_y = frame_y - (top_label and 34 or 17) * buff_text_scale
                    local sep = "|"
                    local bonus_part, reduction_part =
                        string.match(buff.value_text, "^(.-)%" .. sep .. "(.+)$")
                    if bonus_part and reduction_part then
                        -- approximate_text_width assumes a generic 0.58*em glyph
                        -- advance; the digits, sign and "%" here are narrower and
                        -- "|" is narrower still. Use calibrated per-glyph advances
                        -- so the two halves sit tight around the separator instead
                        -- of drifting to the card edges.
                        local seg_adv = vt_font_size * 0.46
                        local sep_adv = vt_font_size * 0.22
                        local bonus_w = #bonus_part * seg_adv
                        local reduction_w = #reduction_part * seg_adv
                        local total_w = bonus_w + sep_adv + reduction_w
                        local seg_x = frame_x + (frame_w - total_w) * 0.5
                        self._panel:text({
                            text = bonus_part, font = vt_font, font_size = vt_font_size,
                            color = RENDER_CACHES.underdog_bonus_color, align = "left",
                            vertical = "center", x = seg_x, y = vt_y,
                            w = bonus_w, h = buff_text_h, layer = 102, alpha = buff_alpha,
                        })
                        self._panel:text({
                            text = sep, font = vt_font, font_size = vt_font_size,
                            color = Color.white, align = "center",
                            vertical = "center", x = seg_x + bonus_w, y = vt_y,
                            w = sep_adv, h = buff_text_h, layer = 102, alpha = buff_alpha,
                        })
                        self._panel:text({
                            text = reduction_part, font = vt_font, font_size = vt_font_size,
                            color = RENDER_CACHES.underdog_reduction_color, align = "left",
                            vertical = "center", x = seg_x + bonus_w + sep_adv, y = vt_y,
                            w = reduction_w, h = buff_text_h, layer = 102, alpha = buff_alpha,
                        })
                    else
                        -- Only one half owned: a lone "+X%" is damage bonus,
                        -- a lone "-Y%" is damage reduction.
                        local lone_color = string.sub(buff.value_text, 1, 1) == "-"
                            and RENDER_CACHES.underdog_reduction_color
                            or RENDER_CACHES.underdog_bonus_color
                        self._panel:text({
                            text = buff.value_text, font = vt_font, font_size = vt_font_size,
                            color = lone_color, align = "center", vertical = "center",
                            x = frame_x, y = vt_y, w = frame_w, h = buff_text_h,
                            layer = 102, alpha = buff_alpha,
                        })
                    end
                elseif buff.value_text then
                    self._panel:text({
                        text      = buff.value_text,
                        font      = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                        font_size = math.max(8, clamp(size * 0.38, 11, 15) * buff_text_scale),
                        color     = buff.color or Color.white,
                        align     = "center",
                        vertical  = "center",
                        x         = frame_x,
                        y         = frame_y - (top_label and 34 or 17) * buff_text_scale,
                        w         = frame_w,
                        h         = buff_text_h,
                        layer     = 102,
                        alpha     = buff_alpha,
                    })
                end

                if top_label then
                    self._panel:text({
                        text      = top_label,
                        font      = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                        font_size = math.max(8, clamp(size * 0.3, 9, 12) * buff_text_scale),
                        color     = HUD_ACCENT_COLOR,
                        align     = "center",
                        vertical  = "center",
                        x         = frame_x,
                        y         = frame_y - 17 * buff_text_scale,
                        w         = frame_w,
                        h         = buff_text_h,
                        layer     = 102,
                        alpha     = buff_alpha,
                    })
                end

                if buff.stack_text then
                    local badge_w = clamp(size * 0.55, 15, 26) * buff_text_scale
                    local badge_h = clamp(size * 0.36, 10, 16) * buff_text_scale
                    local badge_x = pos.x + buff_size * 0.5 - badge_w
                    local badge_y = pos.y + buff_size * 0.5 - badge_h
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
                        font_size = math.max(8, clamp(size * 0.3, 9, 12) * buff_text_scale),
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

                -- Below the icon: a placement label « timer » occupies alone
                -- the slot and replaces the countdown, whose duration
                -- contributes nothing to these composite indicators. Otherwise, timer
                -- text is tinted by the emergency state.
                if timer_label then
                    self._panel:text({
                        text      = timer_label,
                        font      = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                        font_size = math.max(8, clamp(size * 0.3, 9, 12) * buff_text_scale),
                        color     = HUD_ACCENT_COLOR,
                        align     = "center",
                        vertical  = "center",
                        x         = frame_x,
                        y         = pos.y + buff_size / 2 + buff_text_gap,
                        w         = frame_w,
                        h         = buff_text_h,
                        layer     = 102,
                        alpha     = buff_alpha,
                    })
                elseif remaining and remaining > 0 then
                    self._panel:text({
                        text      = string.format("%.1f", remaining),
                        font      = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                        font_size = math.max(8, 14 * buff_text_scale),
                        color     = state.timer_color or Color.white,
                        align     = "center",
                        x         = pos.x - buff_size / 2,
                        y         = pos.y + buff_size / 2 + buff_text_gap,
                        w         = buff_size,
                        h         = buff_text_h,
                        layer     = 102,
                        alpha     = alpha * (0.8 + 0.2 * state.emphasis) * state.alpha_scale,
                    })
                end
            end
        end

        if layout.hidden_count > 0 then
            local pos = layout.positions[layout.slot_count]
            local frame_x = pos.x - buff_size * 0.5 - frame_pad_x
            local frame_y = pos.y - buff_size * 0.5 - frame_pad_y
            local frame_w = buff_size + frame_pad_x * 2
            local frame_h = buff_size + frame_pad_y * 2

            KH.DrawBuffCellFrame(
                self._panel,
                frame_x,
                frame_y,
                frame_w,
                frame_h,
                alpha,
                98
            )
            self._panel:text({
                text = layout.overflow_text,
                font = tweak_data.menu.pd2_small_font or "fonts/font_small_mf",
                font_size = math.max(9, 16 * buff_text_scale),
                color = HUD_ACCENT_COLOR,
                align = "center",
                vertical = "center",
                x = frame_x,
                y = frame_y,
                w = frame_w,
                h = frame_h,
                layer = 102,
                alpha = alpha,
            })
        end
    end

    -- Killfeed rendering delegated to ky_killfeed_render.lua
    KH:render_killfeed(self._panel, w, h, size, alpha, radius)

    if s.enable_killfeed and s.show_total_score ~= false
            and self._heist_score_recorded then
        KH.DrawHeistScoreWidget(self, self._panel, w, h, size, alpha, s)
    end
end

-- ═══════════════════════════════════════════════════
-- Refresh
-- ═══════════════════════════════════════════════════
function KH:RefreshHUD()
    self:RefreshDetectedBuffs()
    self:RefreshHackerPocketECMStatus()
    if self:ensure_panel(false) then
        self:draw()
    end
end

-- ═══════════════════════════════════════════════════
-- Debug: simulation
-- ═══════════════════════════════════════════════════
-- Cases traversed by successive calls to Debug: Simulate :
--   partial multikill, 3 notches lit out of 5;
--   saturated bank and dynamic fallback "KILL CHAIN xN";
--   priority target announcement (solid decorative chevrons);
--   weapon streak medal in the killfeed, with names below it;
--   cumulative kills medal « Dmg+ icon + 100 KILLS », in this same
--   shared row;
--   white sentry card and medal with `equipment_sentry` icon;
--   the twenty-two event medals, including rappel tiers,
--   one per call, with their `hud_tweak` icon.
-- The first call shows the requested example directly, partially filled.
-- `combo` remains at 0 for announcement cases so only the special banner is
-- visible; the preview counts no kills, neither in weapon streaks nor in the
-- heist total: each card is built from these literal values.
function KH:DebugSimulate(n)
    -- The preview uses HUD tables: it is safe only in the main menu,
    -- never during an assault (including briefing, arrest, and pause).
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
        { id = "total_dodge_chance", value_text = "25%" },
    }
    local t_now = now()
    for i, demo in ipairs(demo_static_buffs) do
        self._buffs[demo.id] = {
            id = demo.id,
            icon = KH.IconForBuff(demo.id),
            color = KH.ColorForBuff(demo.id, demo.is_debuff),
            frame_color = KH.FrameColorForBuff(demo.id),
            value_text = demo.value_text,
            is_debuff = demo.is_debuff == true,
            order_t = t_now + i * 0.001,
            start_t = t_now,
            duration = demo.duration,
            t_end = demo.duration and (t_now + demo.duration) or nil,
            persistent = demo.duration == nil,
        }
    end

    -- If the equipped deck has a deck buff enabled in options, the
    -- simulation activates it to verify replacement of position 1.
    local _, base_specialization_id = KH.CurrentPerkDeckIds()
    KH.EquippedPerkDeckEntry(self).value_text = base_specialization_id == KH.HACKER_SPECIALIZATION_ID
        and "x2" or nil
    local perk_candidates = self:GetKyoEquippedPerkBuffCandidates(base_specialization_id)
    for _, buff_id in ipairs(perk_candidates) do
        if self:is_buff_visible(buff_id) then
            self._buffs[buff_id] = {
                id = buff_id,
                icon = KH.IconForBuff(buff_id),
                color = KH.ColorForBuff(buff_id, false),
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
        local icon = KH.IconForBuff(base)
        self._buffs["demo_" .. base .. "_" .. tostring(i)] = {
            id       = "demo_" .. base .. "_" .. tostring(i),
            icon     = icon,
            color    = KH.ColorForBuff(base, demo.is_debuff),
            value_text = demo.value_text,
            stack_text = demo.stack_text,
            is_debuff = demo.is_debuff == true,
            order_t  = t_now + i * 0.001, -- display order 1..n in the row
            start_t  = t_now,
            duration = 30 + i * 2,
            t_end    = t_now + 30 + i * 2,
        }
    end

    -- Adaptive states showcase. `preview_remaining` freezes remaining time
    -- so normal, warning, and critical states remain displayed side by
    -- side until Debug: Clear, instead of expiring in a few seconds.
    -- With a duration of 20 s, the warning threshold drops to 5 s and the
    -- critical threshold to 2 s: chosen values thus frame each state.
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
            icon     = KH.IconForBuff(demo.id),
            color    = KH.ColorForBuff(demo.id, demo.is_debuff),
            is_debuff = demo.is_debuff == true,
            order_t  = t_now + 0.1 + i * 0.001,
            start_t  = t_now,
            duration = demo_state_duration,
            -- No t_end: the preview must not be purged by KH:draw.
            preview_remaining = demo.remaining,
        }
    end

    local DEBUG_BANNER_PREVIEWS = KH.DEBUG_BANNER_PREVIEWS
    local next_preview_index = (self._debug_banner_preview_index
        % #DEBUG_BANNER_PREVIEWS) + 1
    local next_preview = DEBUG_BANNER_PREVIEWS[next_preview_index]
    local third_demo_kill = next_preview.medal == "sentry_kill"
        and { name = "SWAT", score = 1, sentry = true }
        or { name = "Shield", score = 5, special_kind = "shield", special_count = 2, label_index = 1 }

    -- Simulate a few kills. The sentry card temporarily replaces the Shield
    -- only during its own preview case to keep both tests.
    local demo_kills = {
        { name = "Medic", score = 6, headshot = true, special_kind = "medic", special_count = 2, label_index = 1 },
        { name = "Captain Winters", score = 100, special_kind = "boss", special_count = 1, label_index = 1 },
        third_demo_kill,
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
            headshot   = demo.headshot == true,
            headshot_icon = demo.headshot and headshot_icon_descriptor() or nil,
            sentry     = demo.sentry == true,
            sentry_icon = demo.sentry and KH.SentryIconDescriptor() or nil,
            special_kind = demo.special_kind,
            display_text = special_enemy_label(
                demo.special_kind,
                demo.label_index,
                demo.special_count
            ),
            start_t    = t_now,
            -- No t_end: debug kills remain visible until DebugClear.
        })
        if type(demo.score) == "number" then
            self._killfeed_score_total = self._killfeed_score_total + demo.score
            self._killfeed_score_has_value = true
            self:_record_heist_score(demo.score)
        end
    end
    self._heist_score_total = (self._heist_score_total or 0) + 137
    self._heist_score_best_streak = (self._killfeed_score_total or 0) + 50
    -- A special preview announcement never turns off and would always
    -- mask the multikill: each Debug: Simulate advances by one banner case,
    -- and each remains displayed until the next or until Debug: Clear.
    self._debug_banner_preview_index = (self._debug_banner_preview_index
        % #KH.DEBUG_BANNER_PREVIEWS) + 1
    local preview = KH.DEBUG_BANNER_PREVIEWS[self._debug_banner_preview_index]

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
        self:_show_medal_card(t_now, KH.MakeKillMedalCard(preview.kills), true)
    elseif preview.medal == "sentry_kill" then
        self:_show_medal_card(t_now, KH.MakeSentryKillMedalCard(preview.kills), true)
    elseif preview.medal == "event" then
        local card = KH.MakeEventMedalCard(preview.event, preview.tier_index)
        self:_show_medal_card(t_now, KH.SetEventMedalCount(card, preview.event_count), true)
    end
end

function KH:DebugClear()
    -- Without preview, do not touch real counters or the current panel.
    if not self._debug_preview_active then return end
    self:ResetHeistCombatState()
    if self._panel and alive(self._panel) then
        self._panel:clear()
    end
end

-- ═══════════════════════════════════════════════════
-- HUD Hooks: initialization and update
-- ═══════════════════════════════════════════════════
-- HUDManager relays these two events to the host AND client. No access
-- to HUDAssaultCorner: a third-party HUD can replace or hide this panel.
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
    -- A new HUD corresponds to a new heist: no buff, kill,
    -- score, banner, or weapon streak from the previous heist must survive.
    KH:ResetHeistCombatState(true)
    KH:ensure_panel(true)
    KH:TryRegisterGameInfoBridge()
    KH:RefreshDetectedBuffs()
    log("[KyoHUD] HUD panel initialized.")
end)

Hooks:PostHook(HUDManager, "update", "KH_UpdateHUD", function(self, t, dt)
    if KH.hudlist and KH.hudlist.update then
        KH.hudlist:update()
    end
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
