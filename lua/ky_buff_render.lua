-- lua/ky_buff_render.lua -- Buff rendering, value resolution, and autonomous refresh
-- Loaded in the hudmanagerpd2 context declared in mod.txt.
-- Must be loaded after core.lua so that KH utilities are available.
-- This module owns all buff value/text resolution and the autonomous refresh
-- methods that feed KH:draw with presentation data.

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud
local KH = kyohud

if RequiredScript == "lib/managers/hudmanagerpd2"
        and not KH._buff_render_initialized then

    -- Resolve shared utilities from core.lua (exposed on KH for cross-chunk use).
    local clamp                    = KH.clamp
    local now                      = KH.now
    local HUD_ACCENT_COLOR         = KH.HUD_ACCENT_COLOR
    local RENDER_CACHES            = KH.RENDER_CACHES
    local FALLBACK_TEXTURE         = KH.FALLBACK_TEXTURE
    local KYO_BUFF_CONFIG          = KH.KYO_BUFF_CONFIG
    local KYO_BUFF_COLORS          = KYO_BUFF_CONFIG and KYO_BUFF_CONFIG.colors
    local KYO_BUFF_PRESENTATION    = KYO_BUFF_CONFIG and KYO_BUFF_CONFIG.buffs

    -- Buff constants grouped into one module table to keep top-level locals low.
    local C = {
        -- ── Autonomous-refresh identifiers ──
        PASSIVE_REGEN_INTERVAL = 5,
        HACKER_SPECIALIZATION_ID = 21,
        POCKET_ECM_GRENADE_ID = "pocket_ecm_jammer",
        POCKET_ECM_COOLDOWN_ID = "pocket_ecm_jammer_debuff",

        -- ── Cell frame geometry ──
        BUFF_CELL_LINE_WIDTH = 1,
        -- Risers reinforce gently from top to bottom, following the background
        -- gradient. The bottom bar lightens only at its ends: the base remains
        -- anchored and both junctions with the risers stay visible.
        BUFF_CELL_EDGE_ALPHA_TOP    = 0.34,
        BUFF_CELL_EDGE_ALPHA_MID    = 0.66,
        BUFF_CELL_EDGE_ALPHA_BOTTOM = 1,
        BUFF_CELL_FOOTER_ALPHA_END  = 0.8,

        -- ── Adaptive visual state thresholds ──
        BUFF_WARNING_RATIO        = 0.35,
        BUFF_WARNING_MIN_SECONDS  = 1.5,
        BUFF_WARNING_MAX_SECONDS  = 5,
        BUFF_CRITICAL_RATIO       = 0.15,
        BUFF_CRITICAL_MIN_SECONDS = 0.75,
        BUFF_CRITICAL_MAX_SECONDS = 2,
        -- `math.sin` receives radians. A frequency of 1.6 Hz remains perceptible
        -- without producing the aggressive flicker of a high-frequency alert.
        BUFF_CRITICAL_PULSE_HZ    = 1.6,
        BUFF_CRITICAL_PULSE_DEPTH = 0.16,
        BUFF_WARNING_COLOR  = Color(1, 0.68, 0.16),
        BUFF_CRITICAL_COLOR = Color(1, 0.26, 0.22),

        -- ── Label placement ──
        BUFF_LABEL_TOP = "top",
        BUFF_LABEL_TIMER = "timer",
    }

    -- Expose label constants
    KH.BUFF_LABEL_TOP = C.BUFF_LABEL_TOP
    KH.BUFF_LABEL_TIMER = C.BUFF_LABEL_TIMER

    -- Expose hacker specialization ID for DebugSimulate in core.lua
    KH.HACKER_SPECIALIZATION_ID = C.HACKER_SPECIALIZATION_ID

    -- Reused work table: `KH:draw` rebuilds the panel twenty times per second
    -- and must not allocate a table per displayed buff. Its lifetime limits to
    -- one render loop iteration.
    local buff_state = {
        remaining    = nil,
        progress     = nil,
        accent_color = nil,
        timer_color  = nil,
        emphasis     = 0,
        alpha_scale  = 1,
    }

    -- ═══════════════════════════════════════════════════
    -- Cross-chunk helper used by core.lua's handle_buff_event
    -- ═══════════════════════════════════════════════════

    -- Application:time() is the monotonic clock used to stamp buff source
    -- activation moments. Exposed on KH so core.lua can call it without
    -- redefining the wrapper.
    local function application_time()
        local ok, t = pcall(function()
            return Application:time()
        end)
        return ok and tonumber(t) or nil
    end
    KH.ApplicationTime = application_time

    -- ═══════════════════════════════════════════════════
    -- Buff cell frame rendering
    -- ═══════════════════════════════════════════════════

    -- Row positions are fractional. The static frame and animated outline must
    -- be rounded exactly the same way, or the two traces offset by half a pixel
    -- and appear washed out.
    local function align_buff_cell_rect(x, y, w, h)
        local left = math.floor(x + 0.5)
        local top  = math.floor(y + 0.5)
        local min_size = C.BUFF_CELL_LINE_WIDTH * 2
        return left,
            top,
            math.max(min_size, math.floor(x + w + 0.5) - left),
            math.max(min_size, math.floor(y + h + 0.5) - top)
    end

    -- `edge_points` is built once per (color, alpha) pair: buff cells share the same
    -- riser gradient, and KH:draw may render several per frame. The cache key is a
    -- plain string — color reference plus alpha rounded to three digits — so a
    -- repeated alpha during the same frame reuses the existing table instead of
    -- allocating a new one. Inlined in draw_buff_cell_frame to avoid a top-level local.
    local function draw_buff_cell_frame(panel, x, y, w, h, alpha, layer, color)
        local left, top, width, height = align_buff_cell_rect(x, y, w, h)
        local has_custom_outline = color ~= nil
        color = color or HUD_ACCENT_COLOR

        -- P4+P6: clé numérique bornée (2 décimales = 100 valeurs max)
        local bg_key = math.floor(alpha * 100 + 0.5)
        local bg_gradient = RENDER_CACHES.buff_cell_bg[bg_key]
        if not bg_gradient then
            bg_gradient = {
                0, Color.black:with_alpha(0),
                0.45, Color.black:with_alpha(alpha * 0.3),
                1, Color.black:with_alpha(alpha * 0.82),
            }
            RENDER_CACHES.buff_cell_bg[bg_key] = bg_gradient
        end

        panel:gradient({
            x = left,
            y = top,
            w = width,
            h = height,
            orientation = "vertical",
            gradient_points = bg_gradient,
            layer = layer,
        })

        -- Risers share the same gradient points table; `panel:gradient` accepts the
        -- same reference for both without modification.
        -- P4+P6: clé numérique pour color+alpha (pas de string concat)
        local color_key = color.r and (color.r * 0x10000 + color.g * 0x100 + color.b) or 0
        local edge_key = color_key * 100 + bg_key
        local edge_points = RENDER_CACHES.edge_points[edge_key]
        if not edge_points then
            edge_points = {
                0, color:with_alpha(alpha * C.BUFF_CELL_EDGE_ALPHA_TOP),
                0.55, color:with_alpha(alpha * C.BUFF_CELL_EDGE_ALPHA_MID),
                1, color:with_alpha(alpha * C.BUFF_CELL_EDGE_ALPHA_BOTTOM),
            }
            RENDER_CACHES.edge_points[edge_key] = edge_points
        end
        panel:gradient({
            x = left,
            y = top,
            w = C.BUFF_CELL_LINE_WIDTH,
            h = height,
            orientation = "vertical",
            gradient_points = edge_points,
            layer = layer + 1,
        })
        panel:gradient({
            x = left + width - C.BUFF_CELL_LINE_WIDTH,
            y = top,
            w = C.BUFF_CELL_LINE_WIDTH,
            h = height,
            orientation = "vertical",
            gradient_points = edge_points,
            layer = layer + 1,
        })

        -- Cache footer gradient par color+alpha
        local footer_key = color_key * 100 + bg_key
        local footer_gradient = RENDER_CACHES.buff_cell_footer[footer_key]
        if not footer_gradient then
            footer_gradient = {
                0,   color:with_alpha(alpha * C.BUFF_CELL_FOOTER_ALPHA_END),
                0.5, color:with_alpha(alpha * C.BUFF_CELL_EDGE_ALPHA_BOTTOM),
                1,   color:with_alpha(alpha * C.BUFF_CELL_FOOTER_ALPHA_END),
            }
            RENDER_CACHES.buff_cell_footer[footer_key] = footer_gradient
        end

        panel:gradient({
            x = left,
            y = top + height - C.BUFF_CELL_LINE_WIDTH,
            w = width,
            h = C.BUFF_CELL_LINE_WIDTH,
            orientation = "horizontal",
            gradient_points = footer_gradient,
            layer = layer + 1,
        })

        if has_custom_outline then
            local stroke = 2
            -- Cache outline_color par color+alpha
            local outline_key = footer_key
            local outline_color = RENDER_CACHES.buff_cell_outline[outline_key]
            if not outline_color then
                outline_color = color:with_alpha(math.min(1, alpha * 1.15))
                RENDER_CACHES.buff_cell_outline[outline_key] = outline_color
            end
            local outline_layer = layer + 1
            panel:rect({
                x = left,
                y = top,
                w = width,
                h = stroke,
                color = outline_color,
                layer = outline_layer,
            })
            panel:rect({
                x = left,
                y = top + height - stroke,
                w = width,
                h = stroke,
                color = outline_color,
                layer = outline_layer,
            })
            panel:rect({
                x = left,
                y = top + stroke,
                w = stroke,
                h = height - stroke * 2,
                color = outline_color,
                layer = outline_layer,
            })
            panel:rect({
                x = left + width - stroke,
                y = top + stroke,
                w = stroke,
                h = height - stroke * 2,
                color = outline_color,
                layer = outline_layer,
            })
        end
    end
    KH.DrawBuffCellFrame = draw_buff_cell_frame

    -- ═══════════════════════════════════════════════════
    -- Timed buff progress perimeter outline
    -- ═══════════════════════════════════════════════════

    -- Traces the still-active part of a temporary buff's outline. The path
    -- starts at the top edge midpoint and advances clockwise; its end thus
    -- recedes continuously as the timer approaches zero.
    -- Generic static frames stay at three sides. A buff with an explicit frame
    -- color may use a complete static outline instead.
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

    -- Shared progress-points buffer. `append_progress_segment` only reads/writes
    -- `points[n]` for n up to the current count, and `draw_timed_buff_progress`
    -- is the sole consumer. A per-draw clear is achieved by resetting the length
    -- to zero in-place without allocating a new table.
    local function draw_timed_buff_progress(panel, x, y, w, h, progress, color, alpha, layer)
        progress = clamp(tonumber(progress) or 0, 0, 1)
        if progress <= 0 then return end

        -- Same rounding as the static frame: the two outlines overlap.
        x, y, w, h = align_buff_cell_rect(x, y, w, h)

        local line_width = clamp(math.min(w, h) * 0.055, 2, 3)
        local remaining_length = (w * 2 + h * 2) * progress
        local half_w = w * 0.5

        -- Reuse the buffer in place: clear it without allocating a new table.
        local points = RENDER_CACHES.progress
        for i = #points, 1, -1 do
            points[i] = nil
        end
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

        -- Only two polylines per buff: a subtle halo and the crisp stroke.
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
    KH.DrawTimedBuffProgress = draw_timed_buff_progress

    -- ═══════════════════════════════════════════════════
    -- Adaptive visual state of a buff cell
    -- ═══════════════════════════════════════════════════
    -- Only four states, resolved once per rendered buff:

    --   persistent: no known timer. Stable tint, no simulated progression,
    --                no pulsing.
    --   normal     : temporary buff far from expiry. It keeps its presentation
    --                color, including debuff tint.
    --   warning    : approaching expiry. Amber, increased opacity.
    --   critical   : imminent expiry. Red, increased opacity and retained
    --                pulsing.

    -- `accent_color` tints the animated perimeter outline and is set only for
    -- a temporary buff: a permanent indicator never receives it. The cell's
    -- static frame is not part of this state — it always keep `HUD_ACCENT_COLOR`
    -- and its three-sided silhouette.

    -- Thresholds combine a fraction of duration and second bounds:
    -- a 60 s buff thus does not turn amber for twenty seconds, and a
    -- 3 s buff still retains a readable warning phase.

    local function resolve_buff_state(buff, t)
        local state = buff_state
        local duration = tonumber(buff.duration)

        -- Debug preview freezes remaining time to present each state long enough
        -- to inspect; the game uses only `t_end`.
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
            -- Permanent indicator: no progression, no perimeter outline, no
            -- invented urgency.
            return state
        end

        state.progress = clamp(remaining / duration, 0, 1)
        -- A temporary debuff remains identifiable by its own color as long as
        -- no urgency must take precedence.
        state.accent_color = buff.color or HUD_ACCENT_COLOR

        local critical_at = clamp(
            duration * C.BUFF_CRITICAL_RATIO,
            C.BUFF_CRITICAL_MIN_SECONDS,
            C.BUFF_CRITICAL_MAX_SECONDS
        )
        local warning_at = clamp(
            duration * C.BUFF_WARNING_RATIO,
            C.BUFF_WARNING_MIN_SECONDS,
            C.BUFF_WARNING_MAX_SECONDS
        )

        if remaining <= critical_at then
            state.accent_color = C.BUFF_CRITICAL_COLOR
            state.timer_color  = C.BUFF_CRITICAL_COLOR
            state.emphasis     = 1
            local pulse = 0.5 + 0.5 * math.sin(t * math.pi * 2 * C.BUFF_CRITICAL_PULSE_HZ)
            state.alpha_scale = 1 - C.BUFF_CRITICAL_PULSE_DEPTH * (1 - pulse)
        elseif remaining <= warning_at then
            state.accent_color = C.BUFF_WARNING_COLOR
            state.timer_color  = C.BUFF_WARNING_COLOR
            state.emphasis     = 0.55
        end

        return state
    end
    KH.ResolveBuffState = resolve_buff_state

    -- ═══════════════════════════════════════════════════
    -- Buff metadata and icon resolution
    -- ═══════════════════════════════════════════════════

    -- Optional cell label, bypassing value_text. AI buffs retain their historical marker above the icon; others have one only if KyoHUD presentation declares `label`, whose `placement` field chooses between BUFF_LABEL_TOP and BUFF_LABEL_TIMER. Text and placement are returned separately: KH:draw allocates no table and translation is resolved once per identifier, not per frame.
    local function buff_label(buff)
        if buff.label_text then
            return buff.label_text, buff.label_placement or C.BUFF_LABEL_TOP
        elseif buff.title_text then
            return buff.title_text, C.BUFF_LABEL_TOP
        end
        return nil, C.BUFF_LABEL_TOP
    end
    KH.BuffLabel = buff_label

    local function icon_for_buff(buff_id)
        local map_entry = KH:GetVanillaHUDBuffDefinition(buff_id)
        if map_entry then
            local tex, rect = KH.get_icon_data(map_entry)
            local descriptor = { texture = tex, rect = rect }
            if map_entry.icon_rotation then
                descriptor.rotation = map_entry.icon_rotation
            end
            return descriptor
        end
        return { texture = FALLBACK_TEXTURE }
    end
    KH.IconForBuff = icon_for_buff

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
    KH.CurrentPerkDeckIds = current_perk_deck_ids

    local function color_from_presentation(value)
        if not value then return nil end
        if type(value) ~= "string" then return value end

        local definition = KYO_BUFF_COLORS[value] or value
        local ok, color = pcall(function()
            if type(definition) == "table" then
                return Color(unpack(definition))
            end
            return Color(definition)
        end)
        return ok and color or nil
    end

    -- Provider metadata never owns the KyoHUD-specific tint.
    local function color_for_buff(buff_id, is_debuff)
        if is_debuff then
            return color_from_presentation("debuff")
                or Color.white
        end

        local presentation = KYO_BUFF_PRESENTATION[buff_id]
        return color_from_presentation(presentation and presentation.color)
            or Color.white
    end
    KH.ColorForBuff = color_for_buff

    local function frame_color_for_buff(buff_id)
        local presentation = KYO_BUFF_PRESENTATION[buff_id]
        return color_from_presentation(presentation and presentation.frame_color)
    end
    KH.FrameColorForBuff = frame_color_for_buff

    local function icon_for_equipped_perk_deck()
        local specialization_id = current_perk_deck_ids()
        if not specialization_id then
            return icon_for_buff("equipped_perk_deck")
        end

        if KH._equipped_perk_deck_id == specialization_id and KH._equipped_perk_deck_icon then
            return KH._equipped_perk_deck_icon
        end

        -- This game API resolves the correct atlas itself, including for DLC decks. Keep the generic provider icon as a fallback.
        local icon_ok, texture, rect = pcall(function()
            local skilltree_tweak = tweak_data and tweak_data.skilltree
            return skilltree_tweak:get_specialization_icon_data(specialization_id)
        end)
        if not (icon_ok and texture and KH.has_texture(texture)) then
            return icon_for_buff("equipped_perk_deck")
        end

        KH._equipped_perk_deck_id = specialization_id
        KH._equipped_perk_deck_icon = { texture = texture, rect = rect }
        return KH._equipped_perk_deck_icon
    end
    KH.IconForEquippedPerkDeck = icon_for_equipped_perk_deck

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
    KH.EquippedPerkDeckEntry = equipped_perk_deck_entry

    local function active_equipped_perk_buff(hud)
        local _, base_specialization_id = current_perk_deck_ids()
        local candidates = KH:GetKyoEquippedPerkBuffCandidates(base_specialization_id)

        for _, buff_id in ipairs(candidates) do
            local buff = hud._buffs[buff_id]
            if buff and buff.icon and hud:is_buff_visible(buff_id) then
                return buff, buff_id
            end
        end

        return nil, nil
    end
    KH.ActiveEquippedPerkBuff = active_equipped_perk_buff

    local function title_for_buff(buff_id)
        local definition = KH:GetVanillaHUDBuffDefinition(buff_id)
        local title = definition and definition.title
        if title == nil then return nil end
        title = tostring(title)
        return definition.localized and KH.localized_text(title, title) or title
    end
    KH.TitleForBuff = title_for_buff

    local function presentation_label_for_buff(buff_id)
        local presentation = KYO_BUFF_PRESENTATION[buff_id]
        local label = presentation and presentation.label
        if not label then return nil, nil end
        local text = label.id and KH.localized_text(label.id, label.fallback) or label.fallback
        return text, label.placement == "timer" and "timer" or "top"
    end
    KH.PresentationLabelForBuff = presentation_label_for_buff

    local function compare_buff_arrival(a, b)
        local pa = tonumber(a.priority) or 0
        local pb = tonumber(b.priority) or 0
        if pa ~= pb then return pa < pb end
        local oa = a.order_t or a.start_t or 0
        local ob = b.order_t or b.start_t or 0
        if oa ~= ob then return oa < ob end
        return a.id < b.id
    end
    KH.CompareBuffArrival = compare_buff_arrival

    -- ═══════════════════════════════════════════════════
    -- Buff source timing and value resolution
    -- ═══════════════════════════════════════════════════
    -- Moved from core.lua: these helpers are only consumed by the autonomous
    -- refresh methods and format_buff_value, both now owned by this module.

    local function source_remaining(data)
        if type(data) ~= "table" then
            return nil, false
        end

        local app_t = application_time()
        local expire_t = tonumber(data.expire_t)
        if expire_t then
            if app_t then
                return math.max(0, expire_t - app_t), true
            end
            local duration = tonumber(data.duration)
            return duration and math.max(0, duration) or 0, true
        end

        local duration = tonumber(data.duration)
        if duration then
            local start_t = tonumber(data.t)
            if start_t and app_t then
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
                return app_t and math.max(0, latest_expire_t - app_t) or 0, true
            end
            if data._timed_stacks then
                return 0, true
            end
        end

        return nil, false
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

    -- ═══════════════════════════════════════════════════
    -- Native game-state multipliers (moved from core.lua)
    -- ═══════════════════════════════════════════════════
    -- These wrap PD2 manager calls and return the multiplier/fraction used
    -- by the stat-card text formatters below.

    local function current_player_damage()
        local ok, player_damage = pcall(function()
            local player = managers.player and managers.player:player_unit()
            return alive(player) and player:character_damage()
        end)
        return ok and player_damage or nil
    end

    local function native_damage_increase_multiplier()
        local ok, multiplier = pcall(function()
            local pm = managers.player
            if not pm then return 1 end
            local player = pm:player_unit()
            local damage = alive(player) and player:character_damage()
            local inventory = alive(player) and player:inventory()
            local weapon = inventory and inventory:equipped_unit()
            local base = alive(weapon) and weapon:base()
            local tweak = base and base:weapon_tweak_data()
            local categories = tweak and tweak.categories or {}
            local primary_category = categories[1]

            -- BlackMarketManager:damage_multiplier() includes Trigger Happy even
            -- though PlayerStandard applies that property to each shot. Remove it
            -- from this fresh static query, then apply it once below.
            local trigger_mul = tonumber(pm:get_property("trigger_happy", 1)) or 1

            local static_mul = 1
            local ok_static, base_mul = pcall(function()
                return base and base:damage_multiplier() or 1
            end)
            if ok_static and base_mul then static_mul = static_mul * base_mul end
            if trigger_mul ~= 0 then static_mul = static_mul / trigger_mul end

            local ignore = tweak and tweak.ignore_damage_multipliers
            local combat_medic_mul = pm:temporary_upgrade_value(
                "temporary", "combat_medic_damage_multiplier", 1)
            if ignore then return static_mul * combat_medic_mul end

            local state = pm:get_current_state()
            local overkill_all = state and state._overkill_all_weapons or false
            local health_ratio_mul = state and state._damage_health_ratio_mul or 0
            local health_ratio_mul_melee = state and state._damage_health_ratio_mul_melee or 0

            local mul = 1
            mul = mul * pm:temporary_upgrade_value("temporary", "dmg_multiplier_outnumbered", 1)
            if overkill_all or (base and base:is_category("shotgun", "saw")) then
                mul = mul * pm:temporary_upgrade_value("temporary", "overkill_damage_multiplier", 1)
            end
            if damage then
                local health_ratio = damage:health_ratio()
                local damage_health_ratio = pm:get_damage_health_ratio(health_ratio, primary_category or "primary")
                if damage_health_ratio > 0 then
                    local upgrade = (base and base:is_category("saw") and health_ratio_mul_melee)
                        or health_ratio_mul or 0
                    mul = mul * (1 + upgrade * damage_health_ratio)
                end
            end
            mul = mul * pm:temporary_upgrade_value("temporary", "berserker_damage_multiplier", 1)
            mul = mul * trigger_mul
            mul = mul * combat_medic_mul
            return static_mul * mul
        end)
        return ok and tonumber(multiplier) or 1
    end

    local function native_damage_reduction_multiplier()
        local ok, multiplier = pcall(function()
            local pm = managers.player
            if not pm or not pm.damage_reduction_skill_multiplier then return 1 end
            -- Only the native passive_damage_reduction branch indexes
            -- player_unit():character_damage() without guarding. When that
            -- upgrade is owned but no live player unit exists (custody,
            -- pre-spawn, spectating), skip the native call to avoid a
            -- per-frame engine nil-index error; every other case is safe.
            if pm.has_category_upgrade
                and pm:has_category_upgrade("player", "passive_damage_reduction")
                and not alive(pm:player_unit()) then
                return 1
            end
            return pm:damage_reduction_skill_multiplier("bullet")
        end)
        return ok and tonumber(multiplier) or 1
    end

    local function native_passive_health_regen_fraction()
        local ok, fraction = pcall(function()
            local pm = managers.player
            local damage = current_player_damage()
            if not pm or not damage then return 0 end

            local maximum = tonumber(damage:_max_health())
            if not maximum or maximum <= 0 then return 0 end

            -- health_regen() is a max-health ratio (Muscle/Gorilla,
            -- Hostage Taker and temporary ratio sources). fixed_health_regen()
            -- is a health-point amount (crew regeneration), normalized here.
            local ratio = tonumber(pm:health_regen()) or 0
            local fixed = tonumber(pm:fixed_health_regen(damage:health_ratio())) or 0
            local healing_mul = tonumber(damage._healing_reduction) or 1
            local base_fraction = (ratio + fixed / maximum) * healing_mul

            -- Grinder heals a fixed amount per stack and tick. Normalize its
            -- active throughput to the same five-second interval as PV+.
            local grinder_fraction = 0
            local grinder_stacks = damage._damage_to_hot_stack
            if grinder_stacks and #grinder_stacks > 0 then
                local grinder_value = tonumber(pm:upgrade_value(
                    "player", "damage_to_hot", 0)) or 0
                local grinder_tick_time = tonumber(damage._doh_data
                    and damage._doh_data.tick_time) or 1
                if grinder_tick_time > 0 then
                    local hp_per_interval = #grinder_stacks * grinder_value
                        * C.PASSIVE_REGEN_INTERVAL / grinder_tick_time
                    grinder_fraction = hp_per_interval / maximum * healing_mul
                end
            end

            return math.max(0, base_fraction + grinder_fraction)
        end)
        return ok and tonumber(fraction) or 0
    end

    local function native_melee_damage_multiplier()
        local ok, multiplier = pcall(function()
            local pm = managers.player
            if not pm then return 1 end
            local player = pm:player_unit()
            local damage = alive(player) and player:character_damage()
            local mul = 1
            mul = mul * pm:upgrade_value("player", "non_special_melee_multiplier", 1)
            local melee_entry = managers.blackmarket and managers.blackmarket:equipped_melee_weapon()
            local melee_tweak = melee_entry and tweak_data.blackmarket.melee_weapons[melee_entry]
            if melee_tweak and melee_tweak.stats then
                local weapon_type = melee_tweak.stats.weapon_type
                if weapon_type then
                    mul = mul * pm:upgrade_value("player",
                        "melee_" .. tostring(weapon_type) .. "_damage_multiplier", 1)
                end
            end
            if pm:has_category_upgrade("melee", "stacking_hit_damage_multiplier") then
                local movement = alive(player) and player:movement()
                local stack_state = movement and movement._state_data
                    and movement._state_data.stacking_dmg_mul
                    and movement._state_data.stacking_dmg_mul.melee
                if stack_state and stack_state[1] then
                    local t = TimerManager:game():time()
                    if t < stack_state[1] then
                        mul = mul * (1 + pm:upgrade_value("melee", "stacking_hit_damage_multiplier", 0)
                            * (stack_state[2] or 0))
                    end
                end
            end
            local state = pm:get_current_state()
            local health_ratio_mul_melee = state and state._damage_health_ratio_mul_melee or 0
            if damage then
                local health_ratio = damage:health_ratio()
                local damage_health_ratio = pm:get_damage_health_ratio(health_ratio, "melee")
                if damage_health_ratio > 0 then
                    mul = mul * (1 + health_ratio_mul_melee * damage_health_ratio)
                end
            end
            mul = mul * pm:temporary_upgrade_value("temporary", "berserker_damage_multiplier", 1)
            mul = mul * pm:get_melee_dmg_multiplier()
            return mul
        end)
        return ok and tonumber(multiplier) or 1
    end

    -- ═══════════════════════════════════════════════════
    -- Stat-card text formatters (moved from core.lua)
    -- ═══════════════════════════════════════════════════

    local function damage_increase_text()
        local multiplier = native_damage_increase_multiplier()
        local bonus = (multiplier - 1) * 100
        if bonus <= 5 then return "+5%" end
        return string.format("%+.0f%%", bonus)
    end

    local function damage_reduction_text()
        local multiplier = native_damage_reduction_multiplier()
        local reduction = clamp(1 - multiplier, 0, 1)
        if reduction < 0.005 then return "-0%" end
        return string.format("-%.0f%%", reduction * 100)
    end

    local function passive_health_regen_text()
        return string.format("%.1f%%", native_passive_health_regen_fraction() * 100)
    end

    local function melee_damage_increase_text()
        local multiplier = native_melee_damage_multiplier()
        return "x" .. compact_number(multiplier)
    end

    local function calculated_base_dodge()
        local dodge_init = tonumber(tweak_data and tweak_data.player
            and tweak_data.player.damage and tweak_data.player.damage.DODGE_INIT) or 0

        local ok, value = pcall(function()
            local pm = managers.player
            local player = pm:player_unit()
            local movement = alive(player) and player:movement()
            local running = movement and movement:running() or false
            local crouching = movement and movement:crouching() or false
            local zipline = movement and movement:zipline_unit() or nil

            local result = dodge_init
                + (pm:body_armor_value("dodge") or 0)
                + (pm:skill_dodge_chance(running, crouching, zipline) or 0)

            local damage = alive(player) and player:character_damage()
            if damage and damage._temporary_dodge_t
                    and damage._temporary_dodge_t > TimerManager:game():time() then
                result = result + (damage._temporary_dodge or 0)
            end

            local smoke_dodge = 0
            for _, smoke_screen in ipairs(pm._smoke_screen_effects or {}) do
                if smoke_screen:is_in_smoke(player) then
                    smoke_dodge = tweak_data.projectiles.smoke_screen_grenade.dodge_chance or 0
                    break
                end
            end
            result = 1 - (1 - result) * (1 - smoke_dodge)

            return math.max(0, result)
        end)
        return ok and tonumber(value) or dodge_init
    end

    local function total_dodge_chance_text()
        local value = calculated_base_dodge()
        return string.format("%.0f%%", math.max(value * 100, 0))
    end

    -- ═══════════════════════════════════════════════════
    -- BUFF_VALUE_FORMATTERS: dispatch table for value_format strings
    -- ═══════════════════════════════════════════════════

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
        bonus_fraction = function(sources)
            local value = largest_source_value(sources)
            return value and value > 0 and string.format("%+.0f%%", value * 100) or nil
        end,
        reduction_fraction = function(sources)
            local value = largest_source_value(sources)
            return value and value > 0 and string.format("-%.0f%%", value * 100) or nil
        end,
        health_per_interval = function(sources)
            local source
            for _, candidate in pairs(sources) do
                if tonumber(candidate.value) and tonumber(candidate.interval) then
                    source = candidate
                    break
                end
            end
            if not source or source.value <= 0 or source.interval <= 0 then return nil end
            local suffix = source.value_kind == "health_points_per_tick" and " HP" or "%"
            local value = source.value_kind == "health_points_per_tick"
                and source.value or source.value * 100
            return compact_number(value) .. suffix .. " / " .. compact_number(source.interval) .. "s"
        end,
        damage_increase = damage_increase_text,
        damage_reduction = damage_reduction_text,
        melee_damage_increase = melee_damage_increase_text,
        passive_health_regen = passive_health_regen_text,
        total_dodge_chance = total_dodge_chance_text,
        -- Underdog merged card: the basic upgrade (dmg_multiplier_outnumbered) is a
        -- damage multiplier (e.g. 1.15 -> "+15%"), the aced upgrade
        -- (dmg_dampener_outnumbered) is a damage-taken multiplier (e.g. 0.9 ->
        -- "-10%"). Both sources feed this one buff via the catalog route; each is
        -- identified by its source_id. Returns "+15%|-10%" when both are owned.
        underdog_combined = function(sources)
            local bonus_text, reduction_text
            for _, source in pairs(sources) do
                local value = tonumber(source.value)
                if value then
                    if source.source_id == "underdog" then
                        local bonus = (value - 1) * 100
                        if math.abs(bonus) >= 0.5 then
                            bonus_text = string.format("+%.0f%%", bonus)
                        end
                    elseif source.source_id == "underdog_aced" then
                        local reduction = clamp(1 - value, 0, 1) * 100
                        if reduction >= 0.5 then
                            reduction_text = string.format("-%.0f%%", reduction)
                        end
                    end
                end
            end
            if bonus_text and reduction_text then
                return bonus_text .. "|" .. reduction_text
            end
            return bonus_text or reduction_text
        end,
    }

    local function format_vanillahud_value(definition, sources)
        local show_value = definition and definition.show_value
        if show_value == nil or show_value == false then return nil end

        local value = largest_source_value(sources)
        if value == nil then return nil end

        local ok, text = pcall(function()
            if type(show_value) == "function" then
                return show_value(value)
            elseif type(show_value) == "string" then
                return string.format(show_value, value)
            end
            return tostring(value)
        end)
        return ok and text ~= nil and tostring(text) or nil
    end

    local function format_buff_value(buff_id, sources)
        local runtime_definition = KH:GetVanillaHUDBuffDefinition(buff_id)
        local presentation = KYO_BUFF_PRESENTATION[buff_id]
        local value_format = presentation and presentation.value_format
        local formatter = value_format and BUFF_VALUE_FORMATTERS[value_format]
        local value_text
        if presentation and presentation.value_format then
            value_text = formatter and formatter(sources) or nil
        elseif runtime_definition and runtime_definition.show_value ~= nil then
            value_text = format_vanillahud_value(runtime_definition, sources)
        else
            value_text = formatter and formatter(sources) or nil
        end
        local stack_count = largest_stack_count(sources)
        local stack_text
        local stack_format = presentation and presentation.stack_format
        if stack_format == "biker_charges" and stack_count then
            local maximum = tonumber(tweak_data and tweak_data.upgrades
                and tweak_data.upgrades.wild_max_triggers_per_time) or 0
            stack_text = "x" .. tostring(math.max(0, maximum - stack_count))
        elseif runtime_definition and runtime_definition.show_stack_count ~= false
                and stack_count and stack_count > 0 then
            stack_text = "x" .. tostring(stack_count)
        end
        return value_text, stack_text
    end

    -- ═══════════════════════════════════════════════════
    -- Autonomous refresh methods (moved from core.lua)
    -- ═══════════════════════════════════════════════════
    -- These feed KH:draw with presentation data derived from live game state.

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

    local EQUIPPED_SKILL_COUNTER_BUFFS = {}
    for buff_id, presentation in pairs(KYO_BUFF_PRESENTATION) do
        if presentation.persistent_counter then
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
            -- The status is not yet available: keep the previous entry
            -- instead of flashing the icon during loading.
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
            local definition = KYO_BUFF_PRESENTATION[buff_id]
            local visible = self:is_buff_visible(buff_id)
            local equipped, value_text = equipped_skill_counter_text(definition)
            local existing = self._buffs[buff_id]

            if visible and equipped == true then
                if not existing then
                    self:add_buff(buff_id, nil, nil, nil, true, false, value_text)
                    existing = self._buffs[buff_id]
                end
                if existing then
                    -- The indicator represents equipped status, not a duration: an
                    -- active event should therefore not add a timer to it.
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
            local player_manager = peer_id and managers.player
            if not player_manager then return nil end
            -- Les grenades synchronisées peuvent ne pas encore exister pour ce
            -- peer en tout début de partie : get_grenade_amount indexe alors
            -- synced_grenades[peer_id].amount sur nil et provoque une FATAL ERROR.
            -- On garde d'abord l'existence de l'entrée synchronisée.
            local synced = player_manager.get_synced_grenades
                and player_manager:get_synced_grenades(peer_id)
            if not (synced and synced.amount ~= nil) then return nil end
            return player_manager:get_grenade_amount(peer_id)
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

        local deck_entry = KH.EquippedPerkDeckEntry(self)
        local _, base_specialization_id = KH.CurrentPerkDeckIds()
        local grenade_ok, grenade_id = pcall(function()
            return managers.blackmarket and managers.blackmarket:equipped_grenade()
        end)
        local hacker_equipped = base_specialization_id == C.HACKER_SPECIALIZATION_ID
            and grenade_ok and grenade_id == C.POCKET_ECM_GRENADE_ID

        if not hacker_equipped then
            deck_entry.value_text = nil
            self:remove_buff(C.POCKET_ECM_COOLDOWN_ID)
            return
        end

        local amount = equipped_pocket_ecm_amount()
        deck_entry.value_text = amount and ("x" .. tostring(amount)) or nil

        local remaining = pocket_ecm_cooldown_remaining()
        if not self:is_buff_visible(C.POCKET_ECM_COOLDOWN_ID)
                or not remaining or remaining <= 0 then
            self:remove_buff(C.POCKET_ECM_COOLDOWN_ID)
            return
        end

        local t = now()
        local existing = self._buffs[C.POCKET_ECM_COOLDOWN_ID]
        if not existing then
            self:add_buff(C.POCKET_ECM_COOLDOWN_ID, nil, remaining, nil, false, true)
            return
        end

        -- A new recharge can start immediately after the previous one
        -- if there is still charge remaining. Reset the progression,
        -- but keep the fixed position of the cell.
        local previous_remaining = existing.t_end and math.max(0, existing.t_end - t) or 0
        if remaining > previous_remaining + 1 then
            existing.start_t = t
            existing.duration = remaining
        end
        existing.t_end = t + remaining
        existing.is_debuff = true
        existing.color = KH.ColorForBuff(C.POCKET_ECM_COOLDOWN_ID, true)
    end

    local STAT_CARD_BUFF_IDS = {
        "passive_health_regen",
        "damage_increase",
        "damage_reduction",
        "melee_damage_increase",
        "total_dodge_chance",
    }

    local STAT_CARD_VALUE_TEXT = {
        passive_health_regen = { formatter = passive_health_regen_text, neutral = "0.0%" },
        damage_increase = { formatter = damage_increase_text, neutral = "+5%" },
        damage_reduction = { formatter = damage_reduction_text, neutral = "-0%" },
        melee_damage_increase = { formatter = melee_damage_increase_text, neutral = "x1" },
        total_dodge_chance = { formatter = total_dodge_chance_text, neutral = "0%" },
    }

    function KH:RefreshCalculatedBuffValues()
        if self._debug_preview_active then return end

        for _, buff_id in ipairs(STAT_CARD_BUFF_IDS) do
            if self:is_buff_visible(buff_id) then
                local presentation = STAT_CARD_VALUE_TEXT[buff_id]
                local value_text = presentation.formatter()
                if value_text == presentation.neutral then
                    self:remove_buff(buff_id)
                else
                    local existing = self._buffs[buff_id]
                    if not existing then
                        self:add_buff(buff_id, nil, nil, nil, true, false, value_text)
                    else
                        existing.value_text = value_text
                        existing.persistent = true
                    end
                end
            else
                self:remove_buff(buff_id)
            end
        end
    end

    KH._buff_render_initialized = true
end
