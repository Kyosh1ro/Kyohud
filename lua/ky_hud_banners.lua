-- lua/ky_hud_banners.lua -- Center banner priority/queue + tactical frame + corner brackets
-- Loaded in the hudmanagerpd2 context declared in mod.txt.
-- Must be loaded after core.lua so that KH utilities are available.

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud

if RequiredScript == "lib/managers/hudmanagerpd2"
        and not KH._hud_banners_initialized then

    -- Resolve shared utilities from core.lua (exposed on KH for cross-chunk use).
    local RENDER_CACHES = KH.RENDER_CACHES

    -- Banner constants grouped into one module table to keep top-level locals low.
    local C = {
        BANNER_FRAME_EXTENSION = 4,
        BANNER_PRIORITIES = {
            boss  = 2,
            dozer = 1,
        },
        -- Bounded: a few announcements suffice to cover a salvo, and the queue
        -- must never grow without limit during an assault.
        MAX_BANNER_QUEUE = 4,
        TACTICAL_FRAME_SEGMENTS = {
            { 0.09, 0, 0.2  },
            { 0.37, 0, 0.11 },
            { 0.6,  0, 0.27 },
            { 0.06, 1, 0.13 },
            { 0.27, 1, 0.3  },
            { 0.7,  1, 0.18 },
        },
    }

    -- BANNER_FRAME_STYLE depends on BANNER_FRAME_EXTENSION; built after C.
    C.BANNER_FRAME_STYLE = {
        inset = 2,
        glow_alpha = 0.16,
        brackets = { extension = C.BANNER_FRAME_EXTENSION },
    }

    -- Debug: simulation cases traversed by successive calls to KH:DebugSimulate.
    -- `combo` remains at 0 for announcement cases so only the special banner is
    -- visible; the preview counts no kills, neither in weapon streaks nor in the
    -- heist total: each card is built from these literal values.
    local DEBUG_BANNER_PREVIEWS = {
        { combo = 4 },
        { combo = 11 },
        { combo = 0, banner = "boss" },
        { combo = 0, medal = "weapon_streak", family = "shotgun", tier_index = 2 },
        { combo = 0, medal = "kill_total", kills = 100 },
        { combo = 0, medal = "sentry_kill", kills = 100 },
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
        { combo = 0, medal = "event", event = "blindfire" },
        { combo = 0, medal = "event", event = "first_blood" },
        { combo = 0, medal = "event", event = "hotswap" },
        { combo = 0, medal = "event", event = "overwatch" },
        { combo = 0, medal = "event", event = "long_shot" },
        { combo = 0, medal = "event", event = "spray_down" },
        { combo = 0, medal = "event", event = "no_flashbang" },
        { combo = 0, medal = "event", event = "air_kill" },
        { combo = 0, medal = "event", event = "wall_bang", event_count = 3 },
        { combo = 0, medal = "event", event = "loot_carrier" },
    }

    -- Expose values consumed by core.lua; module-private values stay in C.
    KH.BANNER_FRAME_EXTENSION = C.BANNER_FRAME_EXTENSION
    KH.BANNER_FRAME_STYLE = C.BANNER_FRAME_STYLE
    KH.MAX_BANNER_QUEUE = C.MAX_BANNER_QUEUE
    KH.DEBUG_BANNER_PREVIEWS = DEBUG_BANNER_PREVIEWS

    -- Tactical frame inspired by Battlefield notifications: asymmetric strokes,
    -- four detached brackets, and chevrons converging toward the content.
    -- Each bracket is drawn as two filled rectangles (one horizontal arm, one
    -- vertical arm) instead of a polyline: `panel:rect` takes relative coords
    -- and allocates no Vector3, sparing the twelve Vector3 + four tables that
    -- the previous polyline path produced per call.
    local function draw_corner_brackets(panel, x, y, w, h, color, alpha, layer, style)
        local extension = style and style.extension or 4
        local arm_x = style and style.arm_x or math.min(18, w * 0.08)
        local arm_y = style and style.arm_y or math.min(11, h * 0.3)
        local lw = style and style.line_width or 1
        local left = x - extension
        local right = x + w + extension
        local top = y - extension
        local bottom = y + h + extension
        local v_bar_h = math.max(0, arm_y - lw)

        -- Top-left
        panel:rect({ x = left, y = top, w = arm_x, h = lw, color = color, alpha = alpha, layer = layer })
        panel:rect({ x = left, y = top + lw, w = lw, h = v_bar_h, color = color, alpha = alpha, layer = layer })
        -- Top-right
        panel:rect({ x = right - arm_x, y = top, w = arm_x, h = lw, color = color, alpha = alpha, layer = layer })
        panel:rect({ x = right - lw, y = top + lw, w = lw, h = v_bar_h, color = color, alpha = alpha, layer = layer })
        -- Bottom-left
        panel:rect({ x = left, y = bottom - lw, w = arm_x, h = lw, color = color, alpha = alpha, layer = layer })
        panel:rect({ x = left, y = bottom - arm_y, w = lw, h = v_bar_h, color = color, alpha = alpha, layer = layer })
        -- Bottom-right
        panel:rect({ x = right - arm_x, y = bottom - lw, w = arm_x, h = lw, color = color, alpha = alpha, layer = layer })
        panel:rect({ x = right - lw, y = bottom - arm_y, w = lw, h = v_bar_h, color = color, alpha = alpha, layer = layer })
    end

    local function draw_tactical_frame(panel, x, y, w, h, color, alpha, layer, style)
        local glow_alpha = style and style.glow_alpha or 0.16
        local inset = style and style.inset or 2

        -- P4+P6: clé numérique bornée (2 décimales = 100 valeurs max)
        local bg_key = math.floor(alpha * 100 + 0.5)
        local bg_gradient = RENDER_CACHES.tactical_bg[bg_key]
        if not bg_gradient then
            bg_gradient = {
                0,    Color.black:with_alpha(alpha * 0.16),
                0.2,  Color.black:with_alpha(alpha * 0.62),
                0.5,  Color.black:with_alpha(alpha * 0.78),
                0.82, Color.black:with_alpha(alpha * 0.58),
                1,    Color.black:with_alpha(alpha * 0.1),
            }
            RENDER_CACHES.tactical_bg[bg_key] = bg_gradient
        end

        panel:gradient({
            x = x + inset,
            y = y + inset,
            w = w - inset * 2,
            h = h - inset * 2,
            orientation = "horizontal",
            gradient_points = bg_gradient,
            layer = layer,
        })

        -- Three segments per edge, deliberately offset and unequal.
        for _, segment in ipairs(C.TACTICAL_FRAME_SEGMENTS) do
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
    KH.DrawTacticalFrame = draw_tactical_frame

    -- ═══════════════════════════════════════════════════
    -- Priority banner: queue ordering helpers
    -- ═══════════════════════════════════════════════════
    local function banner_priority(banner)
        return banner and C.BANNER_PRIORITIES[banner.kind] or 0
    end
    KH.BannerPriority = banner_priority

    --- Insertion rank respecting descending priority order: the new
    --- announcement is placed behind all those of equal or higher priority.
    --- At equal priority, arrival order is therefore preserved (stable FIFO).
    local function banner_queue_insert_index(queue, priority)
        for index = 1, #queue do
            if banner_priority(queue[index]) < priority then
                return index
            end
        end
        return #queue + 1
    end
    KH.BannerQueueInsertIndex = banner_queue_insert_index

    KH._hud_banners_initialized = true
end
