kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then
    Kyosh1roHUD = kyohud
end

kyohud.hud = kyohud.hud or {}

local FONT = "fonts/font_large_mf"

local SEGMENT_RATIOS = { 0.3, 0.2, 0.25, 0.25 }
-- Flat-color references sampled from the native radial in the user's capture.
-- Do not copy the radial shader's progress-encoding Color(1, 0, 1, 1).
local INK_HEALTH = Color(159 / 255, 208 / 255, 94 / 255)
local INK_ARMOR = Color(1, 1, 1)
local INK_DARK = Color(11 / 255, 12 / 255, 14 / 255)
local INK_TRACK = Color(0.10, 0.10, 0.10)
local INK_STORED_HEALTH = Color(0.20, 0.65, 0.95)
local INK_INFO_BG = Color(0.16, 0.06, 0.26)
local INK_INFO_FILL = Color(0.62, 0.42, 0.92)
local INK_DEBT = Color(1, 0.55, 0.12)
local INK_ABSORB = Color(0.20, 0.85, 0.95)
-- Custom progress ink (Swansong-like). Distinct from HP green and debt orange.
local INK_CUSTOM = Color(0.85, 0.3, 0.9)
local INK_COPR = Color(0.95, 0.90, 0.45)
local INK_OUTER_TRACK = Color(0, 0, 0)
local INK_NUMERIC_BG = Color(1, .03, .035, .043)
local INK_NUMERIC_FRAME = Color(1, 0.35, 0.38, 0.42)
local GEOMETRY_KEYS = {"x", "y", "w", "h"}
local RGB_KEYS = {"r", "g", "b"}

local function safe_get(fn)
    local ok, val = pcall(fn)
    if ok then return val end
    return nil
end

local function isfinite(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    return true
end

local function clamp01(v)
    if not isfinite(v) then return 0 end
    if v < 0 then return 0 end
    if v > 1 then return 1 end
    return v
end

local function copr_marker_x(seg_x, seg_w, threshold, marker_w)
    if type(seg_x) ~= "table" or type(seg_w) ~= "table" then return nil end
    if not isfinite(threshold) or not isfinite(marker_w) then return nil end
    local cursor = 0
    for i = 1, 4 do
        local next_cursor = cursor + SEGMENT_RATIOS[i]
        if threshold >= cursor - 1e-9 and threshold <= next_cursor + 1e-9 then
            local sx = seg_x[i] or 0
            local sw = seg_w[i] or 0
            local frac = (threshold - cursor) / SEGMENT_RATIOS[i]
            if frac < 0 then frac = 0 elseif frac > 1 then frac = 1 end
            local base = sx + sw * frac
            local max_x = sx + sw - marker_w
            if max_x < sx then max_x = sx end
            local mx = base - marker_w / 2
            if mx < sx then mx = sx elseif mx > max_x then mx = max_x end
            return mx
        end
        cursor = next_cursor
    end
    return nil
end

-- Split an absolute effect amount the same way the native radial does: armor
-- first, then residual health. Proven local armor (0, 0) is known absent, while
-- nil current/total stays unknown so no split is invented. Returns
-- armor_part, health_part, armor_total or nil when either channel is unknown.
local function split_effect_amount(health, armor, amount)
    if not (health and health.valid and health.provenance == "local") then return nil end
    if not isfinite(health.current) or health.current < 0 then return nil end
    if not isfinite(health.total) or health.total <= 0 then return nil end
    if not isfinite(amount) or amount < 0 then return nil end
    if not armor or armor.provenance ~= "local" then return nil end
    local armor_part, armor_total
    if armor.valid and isfinite(armor.current) and armor.current >= 0
        and isfinite(armor.total) and armor.total > 0 then
        armor_part = math.min(amount, armor.current)
        armor_total = armor.total
    elseif isfinite(armor.current) and armor.current == 0
        and isfinite(armor.total) and armor.total == 0 then
        armor_part = 0
        armor_total = 0
    else
        return nil
    end
    local health_part = math.min(amount - armor_part, health.current)
    return armor_part, health_part, armor_total
end

local function fmt_pct(m)
    if not m or not m.valid then return "--" end
    local r = m.ratio
    if not isfinite(r) then return "--" end
    return math.round(clamp01(r) * 100) .. "%"
end

local function fmt_real(m, mult)
    if not m or not m.valid then return "--" end
    if m.provenance ~= "local" then return "--" end
    if not isfinite(mult) then return "--" end
    if mult <= 0 then return "--" end
    local c = m.current
    if not isfinite(c) then return "--" end
    local product = c * mult
    if not isfinite(product) then return "--" end
    return tostring(math.round(product))
end

local function safe_remove_owned(parent, root)
    if not parent or not root then return end
    local ok_a, pa, ra = pcall(function()
        if type(alive) ~= "function" then return false, false end
        return not not alive(parent), not not alive(root)
    end)
    if not ok_a or not pa or not ra then return end
    local ok_m, member = pcall(function()
        if type(root.name) ~= "function" or type(parent.child) ~= "function" then
            return true
        end
        return parent:child(root:name()) == root
    end)
    if not ok_m or member == false then return end
    pcall(function() parent:remove(root) end)
end

local G = {}
G.__index = G

local M = {}

function M.new(parent, name)
    if not parent or not name then return nil end

    local existing = nil
    pcall(function()
        if type(parent.child) == "function" then
            existing = parent:child(name)
        end
    end)
    if existing then return nil end

    local self = setmetatable({}, G)
    self._parent = parent
    self._name = name
    self._x = 0
    self._y = 0
    self._w = 0
    self._h = 0
    self._copr_markers = {}
    self._copr_seg_x = { 0, 0, 0, 0 }
    self._copr_seg_w = { 0, 0, 0, 0 }

    local ok = pcall(function()
        self.root = parent:panel({ name = name })
        self.root:set_visible(true)

        self._health_bg = self.root:rect({ name = name .. "_hbg", layer = 2 })
        self._health_bg:set_visible(true)
        pcall(function() self._health_bg:set_color(Color(0.15, 0.15, 0.15)) end)

        -- Owned inner panel, not a second continuous health bar.
        self.health_fill = self.root:panel({ name = name .. "_hfill", layer = 3 })
        self.health_fill:set_visible(true)
        self.health_segments = {}
        for i = 1, 4 do
            self.health_segments[i] = {
                background = self.health_fill:rect({name = name .. "_segment_bg" .. i, layer = 0}),
                fill = self.health_fill:rect({name = name .. "_segment_fill" .. i, layer = 1}),
            }
        end

        -- Delayed-damage debt overlays: layer 2 sits above segment fills and
        -- below the markers so gap/threshold dividers stay uncovered.
        self._delayed_health = {}
        for i = 1, 4 do
            local dh = self.health_fill:rect({ name = name .. "_dhealth" .. i, layer = 2 })
            dh:set_visible(false)
            pcall(function() dh:set_color(INK_DEBT) end)
            self._delayed_health[i] = dh
        end

        -- Absorption overlays: thin cyan lower stripes, independent from debt.
        self._absorb_health = {}
        for i = 1, 4 do
            local ah = self.health_fill:rect({ name = name .. "_habs" .. i, layer = 3 })
            ah:set_visible(false)
            pcall(function() ah:set_color(INK_ABSORB) end)
            self._absorb_health[i] = ah
        end

        -- Custom progress stripes: retained top magenta bands whose prefix
        -- [0, ratio] follows the rendered segments, independent from current HP.
        self._custom_health = {}
        for i = 1, 4 do
            local ch = self.health_fill:rect({ name = name .. "_chealth" .. i, layer = 3 })
            ch:set_visible(false)
            pcall(function() ch:set_color(INK_CUSTOM) end)
            self._custom_health[i] = ch
        end

        self.markers = {}
        for i = 1, 3 do
            local mr = self.health_fill:rect({ name = name .. "_mk" .. i, layer = 2 })
            mr:set_visible(true)
            pcall(function() mr:set_color(INK_DARK) end)
            self.markers[i] = mr
        end

        self.health_text = self.root:text({ name = name .. "_htxt", font = FONT, align = "center", vertical = "center" })
        self.health_text:set_visible(true)
        pcall(function() self.health_text:set_font_size(14) end)

        self._armor_bg = self.root:rect({ name = name .. "_abg" })
        self._armor_bg:set_visible(true)
        pcall(function() self._armor_bg:set_color(Color(0.15, 0.15, 0.15)) end)

        self.armor_fill = self.root:rect({ name = name .. "_afill", layer = 1 })
        self.armor_fill:set_visible(true)
        pcall(function() self.armor_fill:set_color(Color(0.5, 0.5, 0.5)) end)

        -- Delayed-damage debt overlay on the armor track, below health_fill.
        self._delayed_armor = self.root:rect({ name = name .. "_darmor", layer = 2 })
        self._delayed_armor:set_visible(false)
        pcall(function() self._delayed_armor:set_color(INK_DEBT) end)

        -- Absorption overlay on the armor track: a thin lower cyan stripe.
        self._absorb_armor = self.root:rect({ name = name .. "_aabs", layer = 2 })
        self._absorb_armor:set_visible(false)
        pcall(function() self._absorb_armor:set_color(INK_ABSORB) end)

        self.armor_text = self.root:text({ name = name .. "_atxt", font = FONT, align = "center", vertical = "center" })
        self.armor_text:set_visible(true)
        pcall(function() self.armor_text:set_font_size(14) end)

        self._health_value_bg = self.root:rect({ name = name .. "_hvbg", layer = 4 })
        self._health_value_bg:set_visible(true)
        pcall(function() self._health_value_bg:set_color(Color(1, .03, .035, .043)) end)

        self._armor_value_bg = self.root:rect({ name = name .. "_avbg", layer = 4 })
        self._armor_value_bg:set_visible(true)
        pcall(function() self._armor_value_bg:set_color(Color(1, .03, .035, .043)) end)

        self._health_value_frame = {}
        for i = 1, 4 do
            self._health_value_frame[i] = self.root:rect({ name = name .. "_hvfr" .. i, layer = 5 })
            self._health_value_frame[i]:set_visible(true)
            pcall(function() self._health_value_frame[i]:set_color(Color(1, 0.35, 0.38, 0.42)) end)
        end

        self._armor_value_frame = {}
        for i = 1, 4 do
            self._armor_value_frame[i] = self.root:rect({ name = name .. "_avfr" .. i, layer = 5 })
            self._armor_value_frame[i]:set_visible(true)
            pcall(function() self._armor_value_frame[i]:set_color(Color(1, 0.35, 0.38, 0.42)) end)
        end

        -- Ex-President stored-health reserve. Kept below the numeric layers.
        self._stored_health_bg = self.root:rect({ name = name .. "_shbg", layer = 2 })
        self._stored_health_bg:set_visible(false)
        pcall(function() self._stored_health_bg:set_color(INK_DARK) end)

        self._stored_health_fill = self.root:rect({ name = name .. "_shfill", layer = 3 })
        self._stored_health_fill:set_visible(false)
        pcall(function() self._stored_health_fill:set_color(INK_STORED_HEALTH) end)

        -- Cocaine info meter: capacity track and consumed fill share the upper
        -- armor rim, sitting above the armor inks so both stay readable.
        self._info_meter_bg = self.root:rect({ name = name .. "_imbg", layer = 3 })
        self._info_meter_bg:set_visible(false)
        pcall(function() self._info_meter_bg:set_color(INK_INFO_BG) end)

        self._info_meter_fill = self.root:rect({ name = name .. "_imfill", layer = 3 })
        self._info_meter_fill:set_visible(false)
        pcall(function() self._info_meter_fill:set_color(INK_INFO_FILL) end)
    end)

    if not ok or not self.root then
        if self.root and parent then
            safe_remove_owned(parent, self.root)
        end
        return nil
    end

    return self
end

function G:set_geometry(x, y, w, h, reference_scale)
    if not self.root then return end
    self._x = x or 0
    self._y = y or 0
    self._w = w or 0
    self._h = h or 0
    if reference_scale ~= nil and isfinite(reference_scale) and reference_scale > 0 then
        self._reference_scale = reference_scale
    else
        self._reference_scale = nil
    end
    pcall(function()
        self.root:set_shape(self._x, self._y, self._w, self._h)
    end)
    self:_layout()
end

function G:_layout()
    self:render(self._health, self._armor, self._mode, self._multiplier, self._peer_color, self._health_effects)
end

function G:render(health, armor, mode, multiplier, peer_color, health_effects)
    if not self.root then return end
    self._health, self._armor = health, armor
    self._mode, self._multiplier = mode, multiplier
    self._peer_color = peer_color
    self._health_effects = health_effects
    local e = self._reference_scale or math.min(self._w / 440, self._h / 42)
    self._expected = self._expected or {}
    self._primitive_lost = false
    self._render_ok = isfinite(e) and e > 0
    if not self._render_ok then return end
    local ht = mode == "real" and fmt_real(health, multiplier) or fmt_pct(health)
    local at = mode == "real" and fmt_real(armor, multiplier) or fmt_pct(armor)
    local hr = health and health.valid and clamp01(health.ratio) or 0
    local ar = armor and armor.valid and clamp01(armor.ratio) or 0
    local hp_ink = INK_HEALTH
    local pc = peer_color
    if pc ~= nil then
        local pr = safe_get(function() return pc.r end)
        local pg = safe_get(function() return pc.g end)
        local pb = safe_get(function() return pc.b end)
        if isfinite(pr) and isfinite(pg) and isfinite(pb)
            and pr >= 0 and pr <= 1 and pg >= 0 and pg <= 1 and pb >= 0 and pb <= 1 then
            hp_ink = Color(pr, pg, pb)
        end
    end
    local expected, expected_index = self._expected, 0
    local function place(p, x, y, w, h, color, text, fs, layer, alpha, visible)
        expected_index = expected_index + 1
        local d = expected[expected_index] or {}
        d.p, d.x, d.y, d.w, d.h = p, x, y, w, h
        d.color, d.text, d.fs = color, text, fs
        local wanted_alpha = alpha ~= nil and alpha or (color and color.a or 1)
        d.alpha = wanted_alpha
        local wanted_visible = visible
        if wanted_visible == nil then wanted_visible = true end
        d.visible = wanted_visible
        if layer then
            d.layer = layer
        else
            d.layer = nil
        end
        expected[expected_index] = d
        if not p or not alive(p) then
            self._primitive_lost = true
            self._render_ok = false
            return
        end
        local ok = pcall(function()
            p:set_shape(x, y, w, h)
            p:set_visible(wanted_visible)
            if color then
                p:set_color(color)
            end
            p:set_alpha(wanted_alpha)
            if text then p:set_text(text); p:set_font_size(fs) end
            if layer then p:set_layer(layer) end
        end)
        if not ok then self._render_ok = false end
    end
    -- Measurement changes only the numeric budgets, never the ratios or units.
    local function number_width(p, text, fs, nominal)
        if not p or not alive(p) then
            self._primitive_lost = true
            self._render_ok = false
            return nominal
        end
        if type(p.text_rect) ~= "function" then
            self._render_ok = false
            return nominal
        end
        local ok, tw = pcall(function()
            p:set_text(text); p:set_font_size(fs)
            local _, _, measured = p:text_rect()
            return measured
        end)
        if ok and isfinite(tw) and tw >= 0 then return math.max(nominal, math.ceil(tw) + 2 * e) end
        self._render_ok = false
        -- Do not certify a guessed numeric fit if the native measure failed.
        return math.max(nominal, #text * fs * 0.6)
    end
    local hfs, afs = 24 * e, 24 * e
    local hw = number_width(self.health_text, ht, hfs, 40 * e)
    local aw = number_width(self.armor_text, at, afs, 40 * e)
    hw = math.max(hw, number_width(self.health_text, mode == "real" and fmt_pct(health) or fmt_real(health, multiplier), hfs, 40 * e))
    aw = math.max(aw, number_width(self.armor_text, mode == "real" and fmt_pct(armor) or fmt_real(armor, multiplier), afs, 40 * e))
    local bx, by = 14 * e + hw + 12 * e, 3 * e
    local bw = self._w - 28 * e - hw - aw - 24 * e
    if bw <= 16 * e then self._render_ok = false; return end
    -- Cocaine info meter: total/max is the capacity track, current/max the
    -- consumed fill. Unknown or non-finite inputs hide both instead of
    -- inventing ratios; a zero current still keeps the known capacity visible.
    local im = health_effects and health_effects.info_meter
    local im_bg_w, im_fill_w = 0, 0
    local show_im = false
    if im ~= nil and im.known == true
        and isfinite(im.current) and im.current >= 0
        and isfinite(im.total) and im.total >= 0
        and isfinite(im.max) and im.max > 0 then
        local total_ratio = im.total / im.max
        local fill_ratio = im.current / im.max
        if isfinite(total_ratio) and isfinite(fill_ratio) then
            im_bg_w = bw * clamp01(total_ratio)
            im_fill_w = bw * clamp01(fill_ratio)
            show_im = im.total > 0 or im.current > 0
        end
    end
    local ih, iw = 14 * e, bw - 12 * e
    local usable = iw - 6 * e
    -- Delayed-damage debt and absorption share one split: armor first, then
    -- residual health. Proven local (0, 0) armor is known absent, while nil
    -- current/total hides the respective overlay instead of inventing a split.
    local dd = health_effects and health_effects.delayed_damage
    local armor_debt, health_debt, armor_debt_total
    if dd ~= nil and dd.known == true then
        armor_debt, health_debt, armor_debt_total = split_effect_amount(health, armor, dd.amount)
    end
    local debt_ok = armor_debt ~= nil
    local show_armor_debt = debt_ok and armor_debt > 0
    local armor_debt_x, armor_debt_w = bx, 0
    if show_armor_debt then
        armor_debt_w = bw * math.min(clamp01(armor_debt / armor_debt_total), ar)
        armor_debt_x = bx + bw * ar - armor_debt_w
    end
    local show_health_debt = debt_ok and health_debt > 0
    local debt_hi = hr
    local debt_lo = show_health_debt and (hr - health_debt / health.total) or hr
    local ab = health_effects and health_effects.absorption
    local armor_absorb, health_absorb, armor_absorb_total
    if ab ~= nil and ab.known == true then
        armor_absorb, health_absorb, armor_absorb_total = split_effect_amount(health, armor, ab.amount)
    end
    local absorb_ok = armor_absorb ~= nil
    local show_armor_absorb = absorb_ok and armor_absorb > 0
    local armor_absorb_x, armor_absorb_w = bx, 0
    if show_armor_absorb then
        armor_absorb_w = bw * math.min(clamp01(armor_absorb / armor_absorb_total), ar)
        armor_absorb_x = bx + bw * ar - armor_absorb_w
    end
    local show_health_absorb = absorb_ok and health_absorb > 0
    local absorb_hi = hr
    local absorb_lo = show_health_absorb and (hr - health_absorb / health.total) or hr
    -- Custom progress is its own channel: known, finite, in range and consistent
    -- with clamp01(current/total). It never inflates current HP nor adds health.
    local custom = health_effects and health_effects.custom_radial
    local custom_ratio = nil
    if custom ~= nil and custom.known == true
        and isfinite(custom.current) and custom.current >= 0
        and isfinite(custom.total) and custom.total > 0
        and isfinite(custom.ratio) and custom.ratio >= 0 and custom.ratio <= 1 then
        local expected_ratio = clamp01(custom.current / custom.total)
        if math.abs(custom.ratio - expected_ratio) <= 1e-6 then
            custom_ratio = custom.ratio
        end
    end
    place(self.root, self._x, self._y, self._w, self._h)
    -- The opaque black underlay remains on all four sides at zero armor.
    place(self._armor_bg, bx, by, bw, 26 * e, INK_OUTER_TRACK)
    place(self.armor_fill, bx, by, bw * ar, 26 * e, INK_ARMOR)
    place(self._delayed_armor, armor_debt_x, by, armor_debt_w, 26 * e,
        INK_DEBT, nil, nil, 2, nil, show_armor_debt)
    place(self._absorb_armor, armor_absorb_x, 26 * e, armor_absorb_w, 3 * e,
        INK_ABSORB, nil, nil, 2, nil, show_armor_absorb)
    place(self._info_meter_bg, bx, 3 * e, im_bg_w, 2 * e,
        INK_INFO_BG, nil, nil, 3, nil, show_im)
    place(self._info_meter_fill, bx, 3 * e, im_fill_w, 2 * e,
        INK_INFO_FILL, nil, nil, 3, nil, show_im)
    place(self._health_bg, bx + 6 * e, by + 6 * e, iw, ih, INK_DARK)
    place(self.health_fill, bx + 6 * e, by + 6 * e, iw, ih)
    -- Ex-President reserve: value comes from stored stock, never extra current HP.
    local stored = health_effects and health_effects.stored_health
    local stored_known = stored ~= nil and stored.known == true
    local stored_ratio = stored and stored.ratio
    local stored_max = stored and stored.max_ratio
    local show_stored = stored_known
        and isfinite(stored_ratio) and stored_ratio >= 0
        and isfinite(stored_max) and stored_max > 0 and stored_max <= 1
    local stored_fill_ratio = show_stored and clamp01(stored_ratio / stored_max) or 0
    place(self._stored_health_bg, bx, 35 * e, show_stored and bw or 0, 4 * e,
        INK_DARK, nil, nil, 2, nil, show_stored)
    place(self._stored_health_fill, bx, 35 * e, show_stored and bw * stored_fill_ratio or 0, 4 * e,
        INK_STORED_HEALTH, nil, nil, 3, nil, show_stored)
    local x, lo = 0, 0
    for i = 1, 4 do
        local sw = usable * SEGMENT_RATIOS[i]
        if self._copr_seg_x and self._copr_seg_w then
            self._copr_seg_x[i] = x
            self._copr_seg_w[i] = sw
        end
        local fill = clamp01((hr - lo) / SEGMENT_RATIOS[i])
        local s = self.health_segments[i]
        place(s.background, x, 0, sw, ih, INK_TRACK)
        place(s.fill, x, 0, sw * fill, ih, hp_ink)
        -- Segment-local debt interval, clipped to this segment so gaps and
        -- threshold markers stay untouched.
        local da = clamp01((debt_lo - lo) / SEGMENT_RATIOS[i])
        local db = clamp01((debt_hi - lo) / SEGMENT_RATIOS[i])
        local debt_w = sw * (db - da)
        place(self._delayed_health[i], x + sw * da, 0, debt_w, ih,
            INK_DEBT, nil, nil, 2, nil, show_health_debt and db > da)
        -- Absorption uses the same gap-clipped intervals but stays a thin lower
        -- cyan stripe so the underlying orange debt remains visible.
        local aa = clamp01((absorb_lo - lo) / SEGMENT_RATIOS[i])
        local ab_edge = clamp01((absorb_hi - lo) / SEGMENT_RATIOS[i])
        local absorb_w = sw * (ab_edge - aa)
        place(self._absorb_health[i], x + sw * aa, 11 * e, absorb_w, 3 * e,
            INK_ABSORB, nil, nil, 3, nil, show_health_absorb and ab_edge > aa)
        -- Custom prefix [0, ratio] mapped through this segment's real usable
        -- width. Hidden unless the custom channel is known and consistent.
        local custom_fill = custom_ratio ~= nil
            and clamp01((custom_ratio - lo) / SEGMENT_RATIOS[i]) or 0
        place(self._custom_health[i], x, 0, sw * custom_fill, 4 * e,
            INK_CUSTOM, nil, nil, 3, nil, custom_fill > 0)
        if i < 4 then
            -- Equal integer widths and a shared raster phase avoid alternating
            -- thin/thick dividers at fractional proportional segment boundaries.
            -- Overlay the gap and its edges without changing the resource ratios.
            local thickness = math.ceil(3 * e)
            local marker_x = math.floor(x + sw + e - thickness / 2 + 0.5)
            place(self.markers[i], marker_x, 0, thickness, ih, INK_OUTER_TRACK)
        end
        x = x + sw + 2 * e
        lo = lo + SEGMENT_RATIOS[i]
    end
    local copr_markers = self._copr_markers
    local copr_ok = type(copr_markers) == "table"
    if not copr_ok then
        self._render_ok = false
        self._primitive_lost = true
    end
    local copr = health_effects and health_effects.copr
    local copr_n = 0
    local copr_allowed = false
    if copr_ok and copr ~= nil and copr.known == true and copr.active == true
        and health ~= nil and health.valid == true
        and health.provenance == "local"
        and isfinite(health.ratio) and health.ratio > 0 and health.ratio <= 1
        and isfinite(copr.static_damage_ratio)
        and copr.static_damage_ratio > 0 and copr.static_damage_ratio <= 1 then
        local raw_n = 1 / copr.static_damage_ratio
        if isfinite(raw_n) and raw_n >= 1 then
            copr_n = math.ceil(raw_n)
            if copr_n <= 64 then
                copr_allowed = true
            end
        end
    end
    if copr_ok and copr_allowed then
        local i = #copr_markers + 1
        while i <= copr_n do
            local created, marker = pcall(function()
                return self.health_fill:rect({
                    name = self._name .. "_copr" .. i,
                    layer = 4,
                })
            end)
            if not created or not marker or not alive(marker) then
                self._render_ok = false
                self._primitive_lost = true
                break
            end
            pcall(function()
                marker:set_color(INK_COPR)
                marker:set_visible(false)
            end)
            copr_markers[i] = marker
            i = i + 1
        end
    end
    if copr_ok then
        local marker_w = math.ceil(2 * e)
        local marker_h = 14 * e
        local total = #copr_markers
        for i = 1, total do
            local marker = copr_markers[i]
            local visible = false
            local mx = 0
            if copr_allowed and i <= copr_n then
                local threshold = 1 - (i - 1) / copr_n
                visible = threshold <= hr + 0.01
                local mapped = copr_marker_x(self._copr_seg_x, self._copr_seg_w,
                    threshold, marker_w)
                if mapped then mx = mapped end
            end
            place(marker, mx, 0, marker_w, marker_h, INK_COPR,
                nil, nil, 4, nil, visible)
        end
    end
    local htx = 14 * e
    local atx = bx + bw + 12 * e
    place(self.health_text, htx, 4 * e, hw, 24 * e, hp_ink, ht, hfs, 6)
    place(self.armor_text, atx, 4 * e, aw, 24 * e, INK_ARMOR, at, afs, 6)
    local hbg_x = htx - 4 * e
    local hbg_w = hw + 8 * e
    local abg_x = atx - 4 * e
    local abg_w = aw + 8 * e
    local nbg_h = 32 * e
    place(self._health_value_bg, hbg_x, 0, hbg_w, nbg_h, INK_NUMERIC_BG, nil, nil, 4, 0.86)
    place(self._armor_value_bg, abg_x, 0, abg_w, nbg_h, INK_NUMERIC_BG, nil, nil, 4, 0.86)
    if not self._health_value_frame or not self._armor_value_frame then
        self._render_ok = false
        return
    end
    for i = 1, 4 do
        local hf = self._health_value_frame[i]
        local af = self._armor_value_frame[i]
        if not hf or not af then
            self._render_ok = false
            return
        end
        local fx, fy, fw, fh
        if i == 1 then
            fx, fy, fw, fh = hbg_x, 0, hbg_w, e
        elseif i == 2 then
            fx, fy, fw, fh = hbg_x + hbg_w - e, 0, e, nbg_h
        elseif i == 3 then
            fx, fy, fw, fh = hbg_x, nbg_h - e, hbg_w, e
        else
            fx, fy, fw, fh = hbg_x, 0, e, nbg_h
        end
        place(hf, fx, fy, fw, fh, INK_NUMERIC_FRAME, nil, nil, 5)
        if i == 1 then
            fx, fy, fw, fh = abg_x, 0, abg_w, e
        elseif i == 2 then
            fx, fy, fw, fh = abg_x + abg_w - e, 0, e, nbg_h
        elseif i == 3 then
            fx, fy, fw, fh = abg_x, nbg_h - e, abg_w, e
        else
            fx, fy, fw, fh = abg_x, 0, e, nbg_h
        end
        place(af, fx, fy, fw, fh, INK_NUMERIC_FRAME, nil, nil, 5)
    end
    local expected_len = #expected
    if expected_len > expected_index then
        for i = expected_len, expected_index + 1, -1 do
            expected[i] = nil
        end
    end
end

function G:verify()
    if not self._render_ok or not self._expected then return false end
    self._primitive_lost = false
    local ok, result = pcall(function()
        for _, d in ipairs(self._expected) do
            local p = d.p
            if not p or not alive(p) then self._primitive_lost = true; return false end
            for _, key in ipairs(GEOMETRY_KEYS) do
                local value = p[key](p)
                if not isfinite(value) or math.abs(value - d[key]) > 0.01 then return false end
            end
            if p:visible() ~= d.visible then return false end
            local alpha = p:alpha()
            if not isfinite(alpha) or math.abs(alpha - d.alpha) > 0.001 then return false end
            if d.text then
                local fs = p:font_size()
                if p:text() ~= d.text or not isfinite(fs) or math.abs(fs - d.fs) > 0.01 then return false end
                local _, _, tw, th = p:text_rect()
                if not isfinite(tw) or not isfinite(th) or tw < 0 or th < 0 or tw > d.w + 0.5 or th > d.h + 0.5 then return false end
            end
            if d.color then
                if type(p.color) ~= "function" or type(p.alpha) ~= "function" then return false end
                local color = p:color()
                for _, key in ipairs(RGB_KEYS) do
                    if not color or not isfinite(color[key]) or math.abs(color[key] - d.color[key]) > 0.001 then return false end
                end
            end
            if d.layer then
                if type(p.layer) ~= "function" then return false end
                local l = p:layer()
                if not isfinite(l) or math.abs(l - d.layer) > 0.01 then return false end
            end
        end
        return true
    end)
    return ok and result == true
end

function G:destroy()
    if self._parent and self.root then
        safe_remove_owned(self._parent, self.root)
    end
    self.root = nil
    self.health_fill = nil
    self.health_segments = nil
    self._expected = nil
    self.armor_fill = nil
    self.markers = nil
    self.health_text = nil
    self.armor_text = nil
    self._health_bg = nil
    self._armor_bg = nil
    self._health_value_bg = nil
    self._armor_value_bg = nil
    self._health_value_frame = nil
    self._armor_value_frame = nil
    self._stored_health_bg = nil
    self._stored_health_fill = nil
    self._info_meter_bg = nil
    self._info_meter_fill = nil
    self._delayed_armor = nil
    self._delayed_health = nil
    self._absorb_armor = nil
    self._absorb_health = nil
    self._custom_health = nil
    self._copr_markers = nil
    self._copr_seg_x = nil
    self._copr_seg_w = nil
    self._health_effects = nil
    self._parent = nil
end

kyohud.hud.gauge = M
return M
