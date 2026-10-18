-- lua/ky_killfeed_render.lua - Killfeed rendering subsystem
-- Extracted from core.lua to separate rendering logic from game state
-- Loaded after core.lua

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud

if RequiredScript == "lib/managers/hudmanagerpd2"
        and not KH._killfeed_render_initialized then
KH._killfeed_render_initialized = true

local RENDER_CACHES = KH.RENDER_CACHES
local now = KH.now
local clamp = KH.clamp
local approximate_text_width = KH.approximate_text_width
local format_kill_score = KH.format_kill_score
local killfeed_size = KH.killfeed_size
local combo_label = KH.combo_label

-- ═══════════════════════════════════════════════════
-- Render-only constants grouped in C table
-- ═══════════════════════════════════════════════════

-- Helper functions (faithfully moved from core.lua)
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

local C = {
    KILL_SCROLL_TIME = 0.2,
    KILLFEED_FRAME_CLEARANCE = 1.5,
    -- Special chevron geometry
    SPECIAL_CHEVRON_SLOTS = 3,
    SPECIAL_CHEVRON_W = 7,
    SPECIAL_CHEVRON_H = 12,
    SPECIAL_CHEVRON_GAP = 3,
    SPECIAL_CHEVRON_MARGIN = 16,
    -- Multikill chevron geometry
    MULTIKILL_CHEVRON_SLOTS = 5,
    MULTIKILL_CHEVRON_W = 6,
    MULTIKILL_CHEVRON_H = 12,
    MULTIKILL_CHEVRON_GAP = 2,
    BANNER_CHEVRON_TEXT_GAP = 5,
    -- Multikill chevron rendering
    MULTIKILL_CHEVRON_GLOW_DX = 1,
    MULTIKILL_CHEVRON_HOLE_INSET = 1,
    MULTIKILL_CHEVRON_OUTLINE_ALPHA = 0.26,
    MULTIKILL_CHEVRON_HOLE_ALPHA = 0.7,
    MULTIKILL_CHEVRON_GLOW_ALPHA = 0.18,
    -- Tables for chevron shapes and text glow
    MULTIKILL_CHEVRON_SHAPES = {},
    TEXT_GLOW_OFFSETS = {
        { -1, 0 }, { 1, 0 }, { 0, -1 }, { 0, 1 },
    },
}
C.SPECIAL_CHEVRON_GROUP_W = C.SPECIAL_CHEVRON_SLOTS * C.SPECIAL_CHEVRON_W
    + (C.SPECIAL_CHEVRON_SLOTS - 1) * C.SPECIAL_CHEVRON_GAP
C.MULTIKILL_CHEVRON_GROUP_W = C.MULTIKILL_CHEVRON_SLOTS * C.MULTIKILL_CHEVRON_W
    + (C.MULTIKILL_CHEVRON_SLOTS - 1) * C.MULTIKILL_CHEVRON_GAP
C.MULTIKILL_CHEVRON_MARGIN = C.SPECIAL_CHEVRON_MARGIN
    + C.SPECIAL_CHEVRON_GROUP_W
    - C.MULTIKILL_CHEVRON_GROUP_W
C.MULTIKILL_CHEVRON_GLOW_W = C.MULTIKILL_CHEVRON_W + 2
C.MULTIKILL_CHEVRON_GLOW_H = C.MULTIKILL_CHEVRON_H + 2

-- Initialize MULTIKILL_CHEVRON_SHAPES using the helpers
for _, direction in ipairs({ 1, -1 }) do
    C.MULTIKILL_CHEVRON_SHAPES[direction] = {
        fill = chevron_triangles(C.MULTIKILL_CHEVRON_W, C.MULTIKILL_CHEVRON_H, direction),
        glow = chevron_triangles(C.MULTIKILL_CHEVRON_GLOW_W, C.MULTIKILL_CHEVRON_GLOW_H, direction),
        hole = inset_chevron_triangles(
            C.MULTIKILL_CHEVRON_W,
            C.MULTIKILL_CHEVRON_H,
            direction,
            C.MULTIKILL_CHEVRON_HOLE_INSET
        ),
    }
end

-- ═══════════════════════════════════════════════════
-- Helper functions (moved from core.lua)
-- ═══════════════════════════════════════════════════

-- Measure killfeed entries (moved from core.lua lines 264-302)
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

-- Combo color (moved from core.lua lines 760-762)
local function combo_color(count)
    return RENDER_CACHES.combo_colors[math.min(math.max(count, 2), 5)]
end

-- Special enemy color (moved from core.lua lines 827-830, adapted to use KH)
local function special_enemy_color(kind)
    local definition = KH.SPECIAL_ENEMY_DEFINITIONS and KH.SPECIAL_ENEMY_DEFINITIONS[kind] or nil
    return definition and definition.color or KH.HUD_ACCENT_COLOR
end

-- Multikill chevron fill (moved from core.lua lines 917-919)
local function multikill_chevron_fill(count)
    return clamp((tonumber(count) or 2) - 1, 1, C.MULTIKILL_CHEVRON_SLOTS)
end

-- Draw multikill chevrons (moved from core.lua lines 924-987)
local function draw_multikill_chevrons(panel, x, y, direction, color, alpha, layer, filled)
    local shapes = C.MULTIKILL_CHEVRON_SHAPES[direction > 0 and 1 or -1]
    local start_x = math.floor(x + 0.5)
    local center_y = math.floor(y + 0.5)
    local top = center_y - C.MULTIKILL_CHEVRON_H * 0.5
    local glow_top = center_y - C.MULTIKILL_CHEVRON_GLOW_H * 0.5

    for slot = 1, C.MULTIKILL_CHEVRON_SLOTS do
        local arrow_x = start_x + (slot - 1) * (C.MULTIKILL_CHEVRON_W + C.MULTIKILL_CHEVRON_GAP)
        local rank = direction > 0 and (C.MULTIKILL_CHEVRON_SLOTS - slot + 1) or slot

        if rank <= filled then
            local prominence = 1 - (rank - 1) / (C.MULTIKILL_CHEVRON_SLOTS - 1)
            local slot_alpha = alpha * (0.72 + 0.28 * prominence)

            panel:polygon({
                x = arrow_x - C.MULTIKILL_CHEVRON_GLOW_DX,
                y = glow_top,
                w = C.MULTIKILL_CHEVRON_GLOW_W,
                h = C.MULTIKILL_CHEVRON_GLOW_H,
                triangles = shapes.glow,
                color = color,
                alpha = slot_alpha * C.MULTIKILL_CHEVRON_GLOW_ALPHA,
                layer = layer,
            })
            panel:polygon({
                x = arrow_x,
                y = top,
                w = C.MULTIKILL_CHEVRON_W,
                h = C.MULTIKILL_CHEVRON_H,
                triangles = shapes.fill,
                color = color,
                alpha = slot_alpha,
                layer = layer + 1,
            })
        else
            panel:polygon({
                x = arrow_x,
                y = top,
                w = C.MULTIKILL_CHEVRON_W,
                h = C.MULTIKILL_CHEVRON_H,
                triangles = shapes.fill,
                color = color,
                alpha = alpha * C.MULTIKILL_CHEVRON_OUTLINE_ALPHA,
                layer = layer,
            })
            panel:polygon({
                x = arrow_x,
                y = top,
                w = C.MULTIKILL_CHEVRON_W,
                h = C.MULTIKILL_CHEVRON_H,
                triangles = shapes.hole,
                color = Color.black,
                alpha = alpha * C.MULTIKILL_CHEVRON_HOLE_ALPHA,
                layer = layer + 1,
            })
        end
    end
end

-- Draw chevrons (moved from core.lua lines 991-1042)
-- Restored parent semantics: count is constant, cache indexed by size_key then dir_key
local function draw_chevrons(panel, x, y, direction, color, alpha, layer, style)
    local count = C.SPECIAL_CHEVRON_SLOTS
    local arrow_w = style and style.arrow_w or C.SPECIAL_CHEVRON_W
    local arrow_h = style and style.arrow_h or C.SPECIAL_CHEVRON_H
    local gap = style and style.gap or C.SPECIAL_CHEVRON_GAP
    local dir_key = direction > 0 and 1 or -1
    local size_key = arrow_w .. ":" .. arrow_h
    local bucket = RENDER_CACHES.chevrons[size_key]
    if not bucket then
        bucket = {}
        RENDER_CACHES.chevrons[size_key] = bucket
    end
    local triangles = bucket[dir_key]
    if not triangles then
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
        bucket[dir_key] = triangles
    end

    for i = 0, count - 1 do
        local arrow_x = x + i * (arrow_w + gap)

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

-- Draw killfeed card frame (moved from core.lua lines 1065-1123)
local function draw_killfeed_card_frame(panel, x, y, w, h, color, alpha, layer)
    local bg_key = math.floor(alpha * 100 + 0.5)
    local bg_gradient = RENDER_CACHES.killfeed_bg[bg_key]
    if not bg_gradient then
        bg_gradient = {
            0, Color.black:with_alpha(alpha * 0.68),
            0.72, Color.black:with_alpha(alpha * 0.42),
            1, Color.black:with_alpha(alpha * 0.05),
        }
        RENDER_CACHES.killfeed_bg[bg_key] = bg_gradient
    end

    panel:gradient({
        x = x,
        y = y + 1,
        w = w,
        h = h - 2,
        orientation = "horizontal",
        gradient_points = bg_gradient,
        layer = layer,
    })

    local color_key = color.r and (color.r * 0x10000 + color.g * 0x100 + color.b) or 0
    local top_edge_key = color_key * 100 + bg_key
    local top_edge_gradient = RENDER_CACHES.killfeed_top_edge[top_edge_key]
    if not top_edge_gradient then
        top_edge_gradient = {
            0, color:with_alpha(alpha * 0.9),
            0.5, color:with_alpha(alpha * 0.5),
            1, color:with_alpha(alpha * 0.9),
        }
        RENDER_CACHES.killfeed_top_edge[top_edge_key] = top_edge_gradient
    end

    panel:gradient({
        x = x + 2,
        y = y + 1,
        w = w - 4,
        h = 1,
        orientation = "horizontal",
        gradient_points = top_edge_gradient,
        layer = layer + 1,
    })

    panel:rect({
        x = x, y = y + 2, w = 2, h = h - 4,
        color = color, alpha = alpha * 0.9, layer = layer + 1,
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

-- Draw glowing text (moved from core.lua lines 1129-1174)
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
    for _, offset in ipairs(C.TEXT_GLOW_OFFSETS) do
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
-- Main render function (moved from core.lua lines 2566-3038)
-- ═══════════════════════════════════════════════════

function KH:render_killfeed(panel, w, h, size, alpha, radius)
    local s = self.settings
    local t = now()

    -- Killfeed rendering (moved from core.lua lines 2566-3038)
    local combo = self._kill_combo
    local special_banner = self._special_kill_banner
    local medal_card = self._medal_card

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
        local headshot_icon_size = clamp(item_h * 0.52, 15, 20)
        local headshot_icon_gap = clamp(size * 0.1, 3, 5)
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
            panel,
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
            local leading_icon = kill.sentry_icon
                or (kill.headshot and kill.headshot_icon)
            local icon_reserved = leading_icon
                and (headshot_icon_size + headshot_icon_gap)
                or 0
            local item_w = math.ceil(
                icon_reserved + name_w + score_w + content_gap + text_padding * 2
            )
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
        local banner_feed_gap = KH.BANNER_FRAME_EXTENSION
            + C.KILLFEED_FRAME_CLEARANCE
        local medal_h = medal_card_active and clamp(item_h + 6, 34, 46) or 0
        local medal_top_gap = medal_card_active and KH.MEDAL_TOP_GAP or 0
        local medal_feed_gap = (medal_card_active and visible_count > 0)
            and KH.MEDAL_ROW_GAP
            or 0
        local block_h = banner_h + banner_feed_gap + medal_top_gap
            + medal_h + medal_feed_gap
            + (visible_count > 0 and item_h or 0)
        local preferred_top = h * 0.5 + clamp(radius * 0.55, 70, 160)
        local block_top = math.max(8, math.min(preferred_top, h - block_h - 16))
        local medal_y = block_top + banner_h + banner_feed_gap + medal_top_gap
        local feed_y = medal_y + medal_h + medal_feed_gap
        local feed_color = KH.HUD_ACCENT_COLOR
        local card_row_w = score_w + score_gap + feed_row_w
        local block_w = math.max(banner_w, card_row_w)
        local block_x = clamp(w * 0.5 - block_w * 0.5, 8, math.max(8, w - 8 - block_w))
        local block_center = block_x + block_w * 0.5
        local card_row_x = block_center - card_row_w * 0.5

        if score_total_text then
            local newest = self._kills[#self._kills]
            local score_intro = newest and newest.start_t
                and clamp((t - newest.start_t) / C.KILL_SCROLL_TIME, 0, 1)
                or 1
            local score_color = (self._killfeed_score_total or 0) < 0
                and KH.KILLFEED_SCORE_PENALTY_COLOR
                or KH.KILLFEED_SCORE_COLOR
            local score_alpha = alpha * score_intro
            draw_killfeed_card_frame(
                panel,
                card_row_x,
                feed_y,
                score_w,
                item_h,
                score_color,
                score_alpha,
                101
            )
            panel:text({
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
                    and KH.SPECIAL_KILL_BANNER_DURATION
                    or special_banner.t_end - t)
                or (combo.preview
                    and KH.KILL_COMBO_WINDOW
                    or combo.last_t + KH.KILL_COMBO_WINDOW - t)
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
                    and (special_banner.color or KH.HUD_ACCENT_COLOR)
                    or combo_color(combo.count)

                KH.DrawTacticalFrame(
                    panel,
                    bx,
                    by,
                    bw,
                    bh,
                    color,
                    banner_alpha,
                    103,
                    KH.BANNER_FRAME_STYLE
                )

                local arrow_group_w = special_banner_active
                    and C.SPECIAL_CHEVRON_GROUP_W
                    or C.MULTIKILL_CHEVRON_GROUP_W
                local arrow_margin = special_banner_active
                    and C.SPECIAL_CHEVRON_MARGIN
                    or C.MULTIKILL_CHEVRON_MARGIN
                local arrow_reserved = arrow_margin + arrow_group_w + C.BANNER_CHEVRON_TEXT_GAP
                local arrow_y = by + bh * 0.5
                local left_arrow_x = bx + arrow_margin
                local right_arrow_x = bx + bw - arrow_margin - arrow_group_w

                if special_banner_active then
                    draw_chevrons(panel, left_arrow_x, arrow_y, 1, color, banner_alpha, 106)
                    draw_chevrons(panel, right_arrow_x, arrow_y, -1, color, banner_alpha, 106)
                else
                    local filled = multikill_chevron_fill(combo.count)
                    draw_multikill_chevrons(
                        panel, left_arrow_x, arrow_y, 1, color, banner_alpha, 106, filled
                    )
                    draw_multikill_chevrons(
                        panel, right_arrow_x, arrow_y, -1, color, banner_alpha, 106, filled
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
                    panel,
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

        if medal_card_active then
            local remaining = medal_card.preview
                and KH.MEDAL_CARD_DURATION
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
                local medal_color = medal_card.color or KH.HUD_ACCENT_COLOR

                KH.DrawMedalFrame(
                    panel, mx, my, mw, mh, medal_color, medal_alpha, 101
                )

                local content_padding = KH.MEDAL_CONTENT_PADDING
                if medal_card.kind == KH.MEDAL_KIND_WEAPON_STREAK then
                    content_padding = KH.MEDAL_CHEVRON_MARGIN
                        + KH.MEDAL_CHEVRON_GROUP_W
                        + KH.MEDAL_CHEVRON_TEXT_GAP
                    local arrow_y = my + mh * 0.5
                    draw_chevrons(
                        panel,
                        mx + KH.MEDAL_CHEVRON_MARGIN,
                        arrow_y,
                        1,
                        medal_color,
                        medal_alpha,
                        104,
                        KH.MEDAL_CHEVRON_STYLE
                    )
                    draw_chevrons(
                        panel,
                        mx + mw - KH.MEDAL_CHEVRON_MARGIN - KH.MEDAL_CHEVRON_GROUP_W,
                        arrow_y,
                        -1,
                        medal_color,
                        medal_alpha,
                        104,
                        KH.MEDAL_CHEVRON_STYLE
                    )
                end

                local font_size = clamp(size * 0.48, 15, 21)
                local text_x = mx + content_padding
                local text_w = math.max(1, mw - content_padding * 2)

                local icon = medal_card.icon
                if icon and icon.texture then
                    local icon_size = clamp(
                        mh * KH.MEDAL_ICON_H_RATIO, KH.MEDAL_ICON_MIN, KH.MEDAL_ICON_MAX
                    )
                    local reserved = icon_size + KH.MEDAL_ICON_TEXT_GAP
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

                    local bmp = panel:bitmap(params)
                    bmp:set_color(medal_card.icon_color or medal_color)
                    bmp:set_alpha(medal_alpha)
                end

                draw_glowing_text(
                    panel,
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
            scroll = clamp((t - newest.start_t) / C.KILL_SCROLL_TIME, 0, 1)
        end

        local feed_x = card_row_x + score_w + score_gap
        for slot = 1, visible_count do
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

            local item_color = kill.sentry and Color.white
                or (kill.special_kind and special_enemy_color(kill.special_kind))
                or feed_color
            draw_killfeed_card_frame(
                panel,
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
            local leading_icon = kill.sentry_icon
                or (kill.headshot and kill.headshot_icon)
            local minimum_text_w = 1 + (score_text and (text_gap + 1) or 0)
            local icon_available_w = math.max(0, inner_w - minimum_text_w)
            local icon_size = leading_icon
                and math.min(
                    headshot_icon_size,
                    math.max(0, icon_available_w - headshot_icon_gap)
                )
                or 0
            local icon_gap = icon_size > 0
                and math.min(headshot_icon_gap, math.max(0, icon_available_w - icon_size))
                or 0
            local icon_reserved = icon_size + icon_gap
            local score_w = score_text
                and math.min(
                    kill._measured_score_w or 0,
                    math.max(1, inner_w - icon_reserved - text_gap - 1)
                )
                or 0
            local name_w = math.min(
                kill._measured_name_w or inner_w,
                math.max(
                    1,
                    inner_w - icon_reserved - score_w - (score_text and text_gap or 0)
                )
            )
            local content_w = icon_reserved + name_w + score_w
                + (score_text and text_gap or 0)
            local content_x = item_x + (item_w - content_w) * 0.5
            local text_x = content_x + icon_reserved

            if icon_size > 0 then
                local params = {
                    layer = 102,
                    w = icon_size,
                    h = icon_size,
                    x = content_x,
                    y = feed_y + (item_h - icon_size) * 0.5,
                    texture = leading_icon.texture,
                }
                if leading_icon.rect then
                    params.texture_rect = leading_icon.rect
                end
                local bitmap = panel:bitmap(params)
                bitmap:set_color(item_color)
                bitmap:set_alpha(item_alpha)
            end

            panel:text({
                text = kill.display_text or kill.name,
                font = kill_font,
                font_size = kill_font_size,
                color = kill.special_kind and item_color or RENDER_CACHES.killfeed_name_color,
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
                    and RENDER_CACHES.killfeed_negative_score_color
                    or item_color
                panel:text({
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
end

end -- if RequiredScript == "lib/managers/hudmanagerpd2" and not KH._killfeed_render_initialized
