-- lua/ky_heist_score.lua -- Heist score widget rendering
-- Loaded in the hudmanagerpd2 context declared in mod.txt.
-- Must be loaded after core.lua so that KH utilities are available.

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud

if RequiredScript == "lib/managers/hudmanagerpd2"
        and not KH._heist_score_initialized then

    -- Resolve shared utilities from core.lua (exposed on KH for cross-chunk use).
    local clamp                 = KH.clamp
    local format_kill_score     = KH.format_kill_score
    local approximate_text_width = KH.approximate_text_width
    local localized_text        = KH.localized_text
    local RENDER_CACHES         = KH.RENDER_CACHES
    local KILLFEED_SCORE_COLOR  = KH.KILLFEED_SCORE_COLOR
    local KILLFEED_SCORE_PENALTY_COLOR = KH.KILLFEED_SCORE_PENALTY_COLOR

    -- Heist score constants grouped into one module table to keep top-level locals low.
    local C = {
        HEIST_SCORE_LABEL_COLOR = Color(0.86, 0.96, 1),
        HEIST_SCORE_BEST_VALUE_COLOR = Color(1, 1, 1),
        HEIST_SCORE_EDGE_MARGIN = 6,
    }

    -- Labels resolved once and cached. The cache is populated only when
    -- managers.localization is available, matching the original behavior.
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

    -- Cache heist score frame gradient points to avoid per-frame allocations.
    function RENDER_CACHES.heist_score_bg_gradient_for(alpha)
        local alpha_key = math.floor(alpha * 100 + 0.5)
        local cached = RENDER_CACHES.heist_score_bg_gradient[alpha_key]
        if cached then return cached end
        cached = {
            0, Color.black:with_alpha(alpha * 0.7),
            0.58, Color.black:with_alpha(alpha * 0.46),
            1, Color.black:with_alpha(0),
        }
        RENDER_CACHES.heist_score_bg_gradient[alpha_key] = cached
        return cached
    end

    function RENDER_CACHES.heist_score_edge_gradient_for(color, alpha)
        local alpha_key = math.floor(alpha * 100 + 0.5)
        local color_cache = RENDER_CACHES.heist_score_edge_gradient[color]
        if not color_cache then
            color_cache = {}
            RENDER_CACHES.heist_score_edge_gradient[color] = color_cache
        end
        local cached = color_cache[alpha_key]
        if cached then return cached end
        cached = {
            0, color:with_alpha(alpha * 0.5),
            0.72, color:with_alpha(alpha * 0.2),
            1, color:with_alpha(0),
        }
        color_cache[alpha_key] = cached
        return cached
    end

    -- Draws the heist score widget frame: background gradient, left accent bar,
    -- and top/bottom edge gradients.
    local function draw_heist_score_frame(panel, x, y, w, h, color, alpha, layer)
        panel:gradient({
            x = x,
            y = y + 1,
            w = w,
            h = h - 2,
            orientation = "horizontal",
            gradient_points = RENDER_CACHES.heist_score_bg_gradient_for(alpha),
            layer = layer,
        })
        panel:rect({
            x = x, y = y + 2, w = 2, h = h - 4,
            color = color, alpha = alpha * 0.9, layer = layer + 1,
        })
        local edge_gradient = RENDER_CACHES.heist_score_edge_gradient_for(color, alpha)
        panel:gradient({
            x = x + 2,
            y = y + 1,
            w = w - 2,
            h = 1,
            orientation = "horizontal",
            gradient_points = edge_gradient,
            layer = layer + 1,
        })
        panel:gradient({
            x = x + 2,
            y = y + h - 2,
            w = w - 2,
            h = 1,
            orientation = "horizontal",
            gradient_points = edge_gradient,
            layer = layer + 1,
        })
    end

    -- Renders the full heist score widget: total score, best streak (if enabled),
    -- and all supporting text elements. Called from KH:draw when the score is recorded.
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
            math.max(1, panel_w - C.HEIST_SCORE_EDGE_MARGIN * 2)
        )
        local block_h = math.ceil(row_h + pad_y * 2)
        local anchor_x = panel_w * clamp(tonumber(settings.score_position_x) or 100, 0, 100) / 100
        local anchor_y = panel_h * clamp(tonumber(settings.score_position_y) or 75, 0, 100) / 100
        local x = clamp(
            anchor_x - block_w * 0.5,
            C.HEIST_SCORE_EDGE_MARGIN,
            math.max(C.HEIST_SCORE_EDGE_MARGIN, panel_w - C.HEIST_SCORE_EDGE_MARGIN - block_w)
        )
        local y = clamp(
            anchor_y - block_h * 0.5,
            C.HEIST_SCORE_EDGE_MARGIN,
            math.max(C.HEIST_SCORE_EDGE_MARGIN, panel_h - C.HEIST_SCORE_EDGE_MARGIN - block_h)
        )
        local total_color = total < 0
            and KILLFEED_SCORE_PENALTY_COLOR
            or KILLFEED_SCORE_COLOR

        draw_heist_score_frame(panel, x, y, block_w, block_h, total_color, alpha, 101)

        -- When the panel is narrower than the block's natural width,
        -- reduce right-to-left text areas rather than letting them
        -- overlap or exit the frame.
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
            color = C.HEIST_SCORE_LABEL_COLOR,
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
                color = C.HEIST_SCORE_LABEL_COLOR,
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
                color = C.HEIST_SCORE_BEST_VALUE_COLOR,
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
    KH.DrawHeistScoreWidget = draw_heist_score_widget

    KH._heist_score_initialized = true
end
