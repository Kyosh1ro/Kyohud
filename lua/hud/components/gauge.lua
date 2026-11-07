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
local INK_OUTER_TRACK = Color(0, 0, 0)
local INK_NUMERIC_BG = Color(1, .03, .035, .043)
local INK_NUMERIC_FRAME = Color(1, 0.35, 0.38, 0.42)
local GEOMETRY_KEYS = {"x", "y", "w", "h"}
local RGB_KEYS = {"r", "g", "b"}

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
    self:render(self._health, self._armor, self._mode, self._multiplier)
end

function G:render(health, armor, mode, multiplier)
    if not self.root then return end
    self._health, self._armor = health, armor
    self._mode, self._multiplier = mode, multiplier
    local e = self._reference_scale or math.min(self._w / 440, self._h / 42)
    self._expected = self._expected or {}
    self._primitive_lost = false
    self._render_ok = isfinite(e) and e > 0
    if not self._render_ok then return end
    local ht = mode == "real" and fmt_real(health, multiplier) or fmt_pct(health)
    local at = mode == "real" and fmt_real(armor, multiplier) or fmt_pct(armor)
    local hr = health and health.valid and clamp01(health.ratio) or 0
    local ar = armor and armor.valid and clamp01(armor.ratio) or 0
    local expected, expected_index = self._expected, 0
    local function place(p, x, y, w, h, color, text, fs, layer, alpha)
        expected_index = expected_index + 1
        local d = expected[expected_index] or {}
        d.p, d.x, d.y, d.w, d.h = p, x, y, w, h
        d.color, d.text, d.fs = color, text, fs
        local wanted_alpha = alpha ~= nil and alpha or (color and color.a or 1)
        d.alpha = wanted_alpha
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
            p:set_visible(true)
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
    local ih, iw = 14 * e, bw - 12 * e
    local usable = iw - 6 * e
    place(self.root, self._x, self._y, self._w, self._h)
    -- The opaque black underlay remains on all four sides at zero armor.
    place(self._armor_bg, bx, by, bw, 26 * e, INK_OUTER_TRACK)
    place(self.armor_fill, bx, by, bw * ar, 26 * e, INK_ARMOR)
    place(self._health_bg, bx + 6 * e, by + 6 * e, iw, ih, INK_DARK)
    place(self.health_fill, bx + 6 * e, by + 6 * e, iw, ih)
    local x, lo = 0, 0
    for i = 1, 4 do
        local sw = usable * SEGMENT_RATIOS[i]
        local fill = clamp01((hr - lo) / SEGMENT_RATIOS[i])
        local s = self.health_segments[i]
        place(s.background, x, 0, sw, ih, INK_TRACK)
        place(s.fill, x, 0, sw * fill, ih, INK_HEALTH)
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
    local htx = 14 * e
    local atx = bx + bw + 12 * e
    place(self.health_text, htx, 4 * e, hw, 24 * e, INK_HEALTH, ht, hfs, 6)
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
            if p:visible() ~= true then return false end
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
    self._parent = nil
end

kyohud.hud.gauge = M
return M
