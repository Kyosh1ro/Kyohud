-- lua/ky_combat_medals.lua -- Combat medal cards, thresholds, rendering helpers
-- Loaded in two SuperBLT contexts declared in mod.txt:
--   hudmanagerpd2         -> registers medal construction + rendering helpers on KH
--   newraycastweaponbase  -> installs the on_reload hook for Spray Down
-- Each context uses its own idempotence guard so the second context still runs
-- even if the first was already executed.

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

-- ============================================================
-- HUDManager context: medal construction + rendering helpers
-- ============================================================
if RequiredScript == "lib/managers/hudmanagerpd2"
        and not KH._combat_medals_initialized then

    local now                = KH.now
    local get_icon_data      = KH.get_icon_data
    local localized_text     = KH.localized_text
    local HUD_ACCENT_COLOR   = KH.HUD_ACCENT_COLOR
    local RENDER_CACHES      = KH.RENDER_CACHES

    -- Medal constants grouped into one module table to keep top-level locals low.
    local C = {
        -- ── Event Medals ──
        -- Conditions are read on kill. Only First Strike (assault lock) and
        -- rappel tiers (3 s window) retain temporary state.
        -- None of these states is saved. Multiple medals can be awarded for the same kill.
        --
        -- The icon descriptor carries only a `hud_tweak` name: `get_icon_data`
        -- requests the corresponding texture and atlas cutout from the game,
        -- exactly like a catalog buff. No coordinates are written by hand.
        EVENT_MEDAL_DEFINITIONS = {
            first_strike = {
                id       = "ky_hud_event_medal_first_strike",
                fallback = "First Strike",
                color    = Color(1, 0.32, 0.26),             -- orange-red
                icon     = { hud_tweak = "pd2_kill" },
            },
            grave = {
                id       = "ky_hud_event_medal_grave",
                fallback = "Grave",
                color    = Color(0.68, 0.44, 0.92),          -- purple
                icon     = { hud_tweak = "mugshot_downed" },
            },
            low_hp = {
                id       = "ky_hud_event_medal_low_hp",
                fallback = "Last Breath",
                color    = Color(1, 0.18, 0.34),             -- blood red
                icon     = { hud_tweak = "csb_health" },
            },
            reload = {
                id       = "ky_hud_event_medal_reload",
                fallback = "Reload This",
                color    = Color(0.98, 0.78, 0.22),          -- amber
                icon     = { hud_tweak = "csb_reload" },
            },
            through_shield = {
                id       = "ky_hud_event_medal_through_shield",
                fallback = "Through the Shield",
                color    = Color(1, 0.72, 0.16),             -- shield orange
                icon     = { hud_tweak = "csb_armor" },
            },
            one_shot_two_kills = {
                id       = "ky_hud_event_medal_one_shot_two_kills",
                fallback = "Collateral",
                color    = Color(1, 0.48, 0.12),             -- red-gold
                icon     = { hud_tweak = "pd2_kill" },
            },
            revenge = {
                id       = "ky_hud_event_medal_revenge",
                fallback = "Revenge",
                color    = Color(0.82, 0.28, 1),             -- electric violet
                icon     = { hud_tweak = "csb_absorb" },
            },
            bulltrue = {
                id       = "ky_hud_event_medal_bulltrue",
                fallback = "Bulltrue",
                color    = Color(0.35, 1, 0.18),             -- Cloaker green
                icon     = { hud_tweak = "crime_spree_cloaker_smoke" },
            },
            showstopper = {
                id       = "ky_hud_event_medal_showstopper",
                fallback = "Showstopper",
                color    = Color(0.35, 1, 0.18),             -- Cloaker green
                icon     = { hud_tweak = "crime_spree_cloaker_smoke" },
            },
            rope = {
                id       = "ky_hud_event_medal_rope",
                fallback = "Pull!",
                color    = Color(0.36, 0.72, 1),             -- blue
                icon     = { hud_tweak = "csb_lives" },
                tiers = {
                    { count = 1, id = "ky_hud_event_medal_rope", fallback = "Pull!" },
                    { count = 3, id = "ky_hud_event_medal_rope_3", fallback = "Free Fall" },
                    { count = 5, id = "ky_hud_event_medal_rope_5", fallback = "Air Sweep" },
                },
            },
            blindfire = {
                id       = "ky_hud_event_medal_blindfire",
                fallback = "BlindFire",
                color    = Color(1, 0.95, 0.6),              -- yellow-white flash
                icon     = { hud_tweak = "csb_panic" },
            },
            first_blood = {
                id       = "ky_hud_event_medal_first_blood",
                fallback = "First Blood",
                color    = Color(0.85, 0.1, 0.12),           -- blood red
                icon     = { hud_tweak = "pd2_kill" },
            },
            hotswap = {
                id       = "ky_hud_event_medal_hotswap",
                fallback = "Hot Swap",
                color    = Color(0.3, 0.85, 0.8),            -- blue-green
                icon     = { hud_tweak = "csb_switch" },
            },
            overwatch = {
                id       = "ky_hud_event_medal_overwatch",
                fallback = "Overwatch",
                color    = Color(0.4, 0.72, 1),
                icon     = { hud_tweak = "crime_spree_heavy_sniper" },
            },
            long_shot = {
                id       = "ky_hud_event_medal_long_shot",
                fallback = "Long Shot",
                color    = Color(0.45, 0.84, 1),
                icon     = { hud_tweak = "csb_ammo" },
            },
            spray_down = {
                id       = "ky_hud_event_medal_spray_down",
                fallback = "Spray Down",
                color    = Color(1, 0.48, 0.16),
                icon     = { hud_tweak = "csb_switch" },
            },
            no_flashbang = {
                id       = "ky_hud_event_medal_no_flashbang",
                fallback = "No Flashbang",
                color    = Color(1, 0.9, 0.4),                -- flash yellow
                icon     = { hud_tweak = "csb_throwables" },
            },
            air_kill = {
                id       = "ky_hud_event_medal_air_kill",
                fallback = "Air Kill",
                color    = Color(0.5, 0.8, 1),                -- sky blue
                icon     = { hud_tweak = "csb_stamina" },
            },
            wall_bang = {
                id       = "ky_hud_event_medal_wall_bang",
                fallback = "Wallbang",
                color    = Color(0.7, 0.72, 0.75),            -- concrete gray
                icon     = { hud_tweak = "pd2_kill" },
            },
            loot_carrier = {
                id       = "ky_hud_event_medal_loot_carrier",
                fallback = "Hands Off",
                color    = Color(0.95, 0.8, 0.3),             -- gold/loot green
                icon     = { hud_tweak = "pd2_lootdrop" },
            },
        },
        -- A Lua table indexed by key has no stable iteration order. This list freezes the emission order: two kills with the same events always produce exactly the same medal sequence.
        --
        -- Only medals carried by `event_info` appear here. `no_flashbang` and `wall_bang` are emitted directly via their engine hook through `KH:ShowEventMedal`, bypassing the kill path; listing them here would only search for a boolean that never exists.
        EVENT_MEDAL_ORDER = {
            "first_strike", "grave", "low_hp", "reload", "revenge", "bulltrue",
            "showstopper", "rope", "blindfire", "first_blood", "hotswap",
            "overwatch", "long_shot", "air_kill", "loot_carrier", "spray_down",
        },
        -- Last Breath remains a critical signal but must not fill the queue during a low-health kill burst. The first card is immediate and the bound is inclusive: a new card is allowed exactly at 30 s.
        LAST_BREATH_MEDAL_COOLDOWN = 30,
        SPRAY_DOWN_WINDOW = 4,
        MAX_MEDAL_QUEUE = 3,
        MEDAL_CARD_DURATION = 1.75,
        -- ── Cumulative Heist Kill Tiers ──
        KILL_MEDAL_THRESHOLDS = { 50, 75, 100, 150, 200, 300, 400, 500 },
        SENTRY_KILL_MEDAL_THRESHOLDS = { 50, 100, 150 },
        -- Gold: the cumulative medal distinguishes itself from weapon family colors.
        KILL_MEDAL_COLOR = Color(1, 0.84, 0.35),
        MEDAL_KIND_WEAPON_STREAK = "weapon_streak",
        MEDAL_KIND_KILL_TOTAL = "kill_total",
        MEDAL_KIND_EVENT = "event",
        MEDAL_KIND_SENTRY_KILL = "sentry_kill",
        MEDAL_POST_W = 3,
        MEDAL_RIBBON_RATIO = 0.52,
        -- Gap between the medal and the name row following it.
        MEDAL_ROW_GAP = 6,
        -- Separate the medal from the banner's bottom extension by half a pixel:
        -- the two accents no longer merge when both levels are active.
        MEDAL_TOP_GAP = 0.5,
        -- Weapon streak medals keep their three arrows per side. Other medal families use
        -- only an inner margin so their content does not overflow the frame during animation.
        MEDAL_CHEVRON_STYLE = { arrow_w = 6, arrow_h = 9, gap = 3 },
        -- Duplicated from core.lua's SPECIAL_CHEVRON_SLOTS to avoid cross-file coupling.
        -- Medal chevrons use the same 3-arrow bank as banner chevrons.
        MEDAL_CHEVRON_SLOTS = 3,
        MEDAL_CHEVRON_MARGIN = 13,
        MEDAL_CHEVRON_TEXT_GAP = 6,
        MEDAL_CONTENT_PADDING = 13,
        -- Optional icon preceding text, sized to the card's actual height to stay
        -- inside the ribbon regardless of HUD size.
        MEDAL_ICON_TEXT_GAP = 6,
        MEDAL_ICON_H_RATIO = 0.6,
        MEDAL_ICON_MIN = 12,
        MEDAL_ICON_MAX = 24,
    }

    -- Derived constant computed once at module init.
    C.MEDAL_CHEVRON_GROUP_W = C.MEDAL_CHEVRON_SLOTS * C.MEDAL_CHEVRON_STYLE.arrow_w
        + (C.MEDAL_CHEVRON_SLOTS - 1) * C.MEDAL_CHEVRON_STYLE.gap

    -- Expose only values consumed by core.lua; module-private values stay in C.
    KH.EVENT_MEDAL_DEFINITIONS = C.EVENT_MEDAL_DEFINITIONS
    KH.EVENT_MEDAL_ORDER = C.EVENT_MEDAL_ORDER
    KH.LAST_BREATH_MEDAL_COOLDOWN = C.LAST_BREATH_MEDAL_COOLDOWN
    KH.SPRAY_DOWN_WINDOW = C.SPRAY_DOWN_WINDOW
    KH.MAX_MEDAL_QUEUE = C.MAX_MEDAL_QUEUE
    KH.MEDAL_CARD_DURATION = C.MEDAL_CARD_DURATION
    KH.KILL_MEDAL_THRESHOLDS = C.KILL_MEDAL_THRESHOLDS
    KH.SENTRY_KILL_MEDAL_THRESHOLDS = C.SENTRY_KILL_MEDAL_THRESHOLDS
    KH.MEDAL_KIND_WEAPON_STREAK = C.MEDAL_KIND_WEAPON_STREAK
    KH.MEDAL_ROW_GAP = C.MEDAL_ROW_GAP
    KH.MEDAL_TOP_GAP = C.MEDAL_TOP_GAP
    KH.MEDAL_CHEVRON_STYLE = C.MEDAL_CHEVRON_STYLE
    KH.MEDAL_CHEVRON_GROUP_W = C.MEDAL_CHEVRON_GROUP_W
    KH.MEDAL_CHEVRON_MARGIN = C.MEDAL_CHEVRON_MARGIN
    KH.MEDAL_CHEVRON_TEXT_GAP = C.MEDAL_CHEVRON_TEXT_GAP
    KH.MEDAL_CONTENT_PADDING = C.MEDAL_CONTENT_PADDING
    KH.MEDAL_ICON_TEXT_GAP = C.MEDAL_ICON_TEXT_GAP
    KH.MEDAL_ICON_H_RATIO = C.MEDAL_ICON_H_RATIO
    KH.MEDAL_ICON_MIN = C.MEDAL_ICON_MIN
    KH.MEDAL_ICON_MAX = C.MEDAL_ICON_MAX

    -- Sentry icon descriptor: shared between medal cards and killfeed entries.
    -- Cached on KH so all call sites resolve the same texture/rect once.
    local SENTRY_ICON_DESCRIPTOR
    local function sentry_icon_descriptor()
        if not SENTRY_ICON_DESCRIPTOR then
            local texture, rect = get_icon_data({ hud_tweak = "equipment_sentry" })
            SENTRY_ICON_DESCRIPTOR = { texture = texture, rect = rect }
        end
        return SENTRY_ICON_DESCRIPTOR
    end
    KH.SentryIconDescriptor = sentry_icon_descriptor

    -- ── Medal card constructors ──

    --- Cumulative kills medal. The medal's name is carried by a vanilla
    --- preplanning icon; only the tier reached and a single key remain, common to all eight
    --- tiers. Texture, atlas cutout, and tint are resolved here once per medal:
    --- `KH:draw` then just places the bitmap.
    local function make_kill_medal_card(kill_count)
        if type(kill_count) ~= "number" then return nil end

        return {
            kind  = C.MEDAL_KIND_KILL_TOTAL,
            icon  = KH:GetKillMedalIconDescriptor(),
            icon_color = C.KILL_MEDAL_COLOR,
            label = tostring(kill_count) .. " "
                .. localized_text("ky_hud_kill_medal_kills", "KILLS"),
            color = C.KILL_MEDAL_COLOR,
        }
    end
    KH.MakeKillMedalCard = make_kill_medal_card

    local function make_sentry_kill_medal_card(kill_count)
        if type(kill_count) ~= "number" then return nil end

        return {
            kind = C.MEDAL_KIND_SENTRY_KILL,
            icon = sentry_icon_descriptor(),
            icon_color = Color.white,
            label = tostring(kill_count) .. " "
                .. localized_text("ky_hud_kill_medal_kills", "KILLS"),
            color = Color.white,
        }
    end
    KH.MakeSentryKillMedalCard = make_sentry_kill_medal_card

    --- Event medal. `id` is the key of `EVENT_MEDAL_DEFINITIONS`, never a
    --- label. Like the cumulative medal, the card carries a pictogram: texture,
    --- atlas cutout, translated label, and tint are resolved here once per
    --- medal so that `KH:draw` only needs to place the bitmap.
    local function make_event_medal_card(id, tier_index)
        local definition = id and C.EVENT_MEDAL_DEFINITIONS[id]
        if not definition then return nil end
        local label = definition.tiers and definition.tiers[tier_index or 1] or definition
        if not label then return nil end

        local color = definition.color or HUD_ACCENT_COLOR
        local texture, rect = get_icon_data(definition.icon)
        return {
            kind       = C.MEDAL_KIND_EVENT,
            event      = id,
            tier_index = definition.tiers and (tier_index or 1) or nil,
            icon       = { texture = texture, rect = rect },
            icon_color = color,
            label      = localized_text(label.id, label.fallback),
            color      = color,
        }
    end
    KH.MakeEventMedalCard = make_event_medal_card

    local function set_event_medal_count(card, count)
        count = tonumber(count)
        if not card or not count then return card end

        count = math.max(1, math.floor(count))
        card._count_label_base = card._count_label_base or card.label
        card.label = count > 1
            and card._count_label_base .. " x" .. tostring(count)
            or card._count_label_base
        return card
    end
    KH.SetEventMedalCount = set_event_medal_count

    --- Directly emits an event card without recording a kill or score.
    --- Reserved for engine hooks that already aggregate victims from the same shot.
    function KH:ShowEventMedal(id, count)
        local card = set_event_medal_count(make_event_medal_card(id), count)
        self:_show_medal_card(now(), card, false)
        return card
    end

    --- Updates the counter of a card already emitted during the same shot. The
    --- active or FIFO-placed card is the same table: the visible label evolves
    --- up to the final total without adding a second medal.
    function KH:UpdateEventMedalCount(card, count)
        return set_event_medal_count(card, count)
    end

    -- ── Medal frame rendering helpers ──

    --- One medal edge: luminous ribbon at center, extended by a subtle line to
    --- the risers. Center/edge contrast yields the «ribbon» readout without
    --- closing the card like a solid frame.
    local function draw_medal_edge(panel, x, y, w, color, alpha, layer)
        local ribbon_w = w * C.MEDAL_RIBBON_RATIO
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
            x = x + C.MEDAL_POST_W,
            y = y,
            w = math.max(0, ribbon_x - x - C.MEDAL_POST_W),
            h = 1,
            color = color, alpha = alpha * 0.32, layer = layer + 1,
        })
        panel:rect({
            x = ribbon_x + ribbon_w,
            y = y,
            w = math.max(0, x + w - C.MEDAL_POST_W - ribbon_x - ribbon_w),
            h = 1,
            color = color, alpha = alpha * 0.32, layer = layer + 1,
        })
    end
    -- Cache medal frame gradient colors by alpha to avoid per-frame allocations
    function RENDER_CACHES.medal_frame_gradient_for(alpha)
        -- Round alpha to 2 decimal places for cache key
        local alpha_key = math.floor(alpha * 100 + 0.5)
        local cached = RENDER_CACHES.medal_frame_gradient[alpha_key]
        if cached then return cached end
        cached = {
            0,    Color.black:with_alpha(alpha * 0.14),
            0.26, Color.black:with_alpha(alpha * 0.7),
            0.5,  Color.black:with_alpha(alpha * 0.82),
            0.74, Color.black:with_alpha(alpha * 0.7),
            1,    Color.black:with_alpha(alpha * 0.14),
        }
        RENDER_CACHES.medal_frame_gradient[alpha_key] = cached
        return cached
    end

    local function draw_medal_frame(panel, x, y, w, h, color, alpha, layer)
        -- Symmetric background: the medal reads as a block, while kill cards keep
        -- their right-oriented asymmetric gradient.
        panel:gradient({
            x = x, y = y + 1, w = w, h = h - 2,
            orientation = "horizontal",
            gradient_points = RENDER_CACHES.medal_frame_gradient_for(alpha),
            layer = layer,
        })

        panel:rect({
            x = x, y = y, w = C.MEDAL_POST_W, h = h,
            color = color, alpha = alpha, layer = layer + 1,
        })
        panel:rect({
            x = x + w - C.MEDAL_POST_W, y = y, w = C.MEDAL_POST_W, h = h,
            color = color, alpha = alpha, layer = layer + 1,
        })

        draw_medal_edge(panel, x, y, w, color, alpha, layer + 1)
        draw_medal_edge(panel, x, y + h - 1, w, color, alpha, layer + 1)
    end
    KH.DrawMedalFrame = draw_medal_frame

    KH._combat_medals_initialized = true
end

-- ============================================================
-- NewRaycastWeaponBase context: on_reload hook for Spray Down
-- ============================================================
if RequiredScript == "lib/units/weapons/newraycastweaponbase"
        and not KH._spray_down_reload_hook_installed then

    -- Only reloading the local player's weapon opens a new magazine.
    -- Bots' and other units' weapons never touch this state.
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

    KH._spray_down_reload_hook_installed = true
end
