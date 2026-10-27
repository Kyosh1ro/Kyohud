kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then
    Kyosh1roHUD = kyohud
end

kyohud.hud = kyohud.hud or {}

local FONT = "fonts/font_medium_mf"
local MARKER_RATIOS = { 0.3, 0.5, 0.75 }

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

        self._health_bg = self.root:rect({ name = name .. "_hbg" })
        self._health_bg:set_visible(true)
        pcall(function() self._health_bg:set_color(Color(0.15, 0.15, 0.15)) end)

        self.health_fill = self.root:rect({ name = name .. "_hfill" })
        self.health_fill:set_visible(true)
        pcall(function() self.health_fill:set_color(Color(0.2, 0.8, 0.2)) end)

        self.markers = {}
        for i = 1, 3 do
            local mr = self.root:rect({ name = name .. "_mk" .. i })
            mr:set_visible(true)
            pcall(function() mr:set_color(Color(1, 1, 1)) end)
            self.markers[i] = mr
        end

        self.health_text = self.root:text({ name = name .. "_htxt", font = FONT })
        self.health_text:set_visible(true)
        pcall(function() self.health_text:set_font_size(14) end)

        self._armor_bg = self.root:rect({ name = name .. "_abg" })
        self._armor_bg:set_visible(true)
        pcall(function() self._armor_bg:set_color(Color(0.15, 0.15, 0.15)) end)

        self.armor_fill = self.root:rect({ name = name .. "_afill" })
        self.armor_fill:set_visible(true)
        pcall(function() self.armor_fill:set_color(Color(0.5, 0.5, 0.5)) end)

        self.armor_text = self.root:text({ name = name .. "_atxt", font = FONT })
        self.armor_text:set_visible(true)
        pcall(function() self.armor_text:set_font_size(14) end)
    end)

    if not ok or not self.root then
        if self.root and parent then
            safe_remove_owned(parent, self.root)
        end
        return nil
    end

    return self
end

function G:set_geometry(x, y, w, h)
    if not self.root then return end
    self._x = x or 0
    self._y = y or 0
    self._w = w or 0
    self._h = h or 0
    pcall(function()
        self.root:set_shape(self._x, self._y, self._w, self._h)
    end)
    self:_layout()
end

function G:_layout()
    local w = self._w
    local h = self._h
    local rh = h / 4

    pcall(function()
        if self._health_bg then
            self._health_bg:set_shape(0, 0, w, rh)
        end

        if self.health_fill then
            local curw = self.health_fill:w() or 0
            self.health_fill:set_shape(0, 0, curw, rh)
        end

        for i = 1, 3 do
            local mx = MARKER_RATIOS[i] * w
            self.markers[i]:set_shape(mx, 0, 1, rh)
        end

        if self.health_text then
            self.health_text:set_shape(0, rh, w, rh)
            self.health_text:set_font_size(math.max(1, rh))
        end

        if self._armor_bg then
            self._armor_bg:set_shape(0, rh * 2, w, rh)
        end

        if self.armor_fill then
            local curw = self.armor_fill:w() or 0
            self.armor_fill:set_shape(0, rh * 2, curw, rh)
        end

        if self.armor_text then
            self.armor_text:set_shape(0, rh * 3, w, rh)
            self.armor_text:set_font_size(math.max(1, rh))
        end
    end)
end

function G:render(health, armor, mode, multiplier)
    if not self.root then return end

    local w = self._w
    local h = self._h
    local rh = h / 4

    local h_ratio = 0
    if health and health.valid and isfinite(health.ratio) then
        h_ratio = clamp01(health.ratio)
    end
    local hfw = h_ratio * w

    local a_ratio = 0
    if armor and armor.valid and isfinite(armor.ratio) then
        a_ratio = clamp01(armor.ratio)
    end
    local afw = a_ratio * w

    local ht, at
    if mode == "real" then
        ht = fmt_real(health, multiplier)
        at = fmt_real(armor, multiplier)
    else
        ht = fmt_pct(health)
        at = fmt_pct(armor)
    end

    pcall(function()
        self.root:set_shape(self._x, self._y, w, h)

        if self._health_bg then
            self._health_bg:set_shape(0, 0, w, rh)
            self._health_bg:set_visible(true)
        end

        self.health_fill:set_shape(0, 0, hfw, rh)
        self.health_fill:set_visible(true)

        for i = 1, 3 do
            local mx = MARKER_RATIOS[i] * w
            self.markers[i]:set_shape(mx, 0, 1, rh)
            self.markers[i]:set_visible(true)
        end

        self.health_text:set_text(ht)
        self.health_text:set_shape(0, rh, w, rh)
        self.health_text:set_font_size(math.max(1, rh))
        self.health_text:set_visible(true)

        if self._armor_bg then
            self._armor_bg:set_shape(0, rh * 2, w, rh)
            self._armor_bg:set_visible(true)
        end

        self.armor_fill:set_shape(0, rh * 2, afw, rh)
        self.armor_fill:set_visible(true)

        self.armor_text:set_text(at)
        self.armor_text:set_shape(0, rh * 3, w, rh)
        self.armor_text:set_font_size(math.max(1, rh))
        self.armor_text:set_visible(true)
    end)

    self._exp_rx = self._x
    self._exp_ry = self._y
    self._exp_rw = w
    self._exp_rh = h
    self._exp_hfw = hfw
    self._exp_afw = afw
    self._exp_ht = ht
    self._exp_at = at
    self._exp_fsz = math.max(1, rh)
    self._exp_afsz = math.max(1, rh)
    self._exp_mx = {}
    for i = 1, 3 do
        self._exp_mx[i] = MARKER_RATIOS[i] * w
    end
end

function G:verify()
    local result = true
    local function chk(cond)
        if not cond then result = false end
    end

    local worked = pcall(function()
        chk(alive(self.root))
        chk(alive(self.health_fill))
        chk(alive(self.armor_fill))
        for i = 1, 3 do
            chk(alive(self.markers[i]))
        end
        chk(alive(self.health_text))
        chk(alive(self.armor_text))
        if self._health_bg then chk(alive(self._health_bg)) end
        if self._armor_bg then chk(alive(self._armor_bg)) end

        local rx = self.root:x()
        local ry = self.root:y()
        local rw = self.root:w()
        local rh = self.root:h()
        chk(isfinite(rx) and rx >= 0)
        chk(isfinite(ry) and ry >= 0)
        chk(isfinite(rw) and rw >= 0)
        chk(isfinite(rh) and rh >= 0)
        if self._exp_rx ~= nil then chk(rx == self._exp_rx) end
        if self._exp_ry ~= nil then chk(ry == self._exp_ry) end
        if self._exp_rw ~= nil then chk(rw == self._exp_rw) end
        if self._exp_rh ~= nil then chk(rh == self._exp_rh) end

        chk(self.root:visible() == true)

        local hfw = self.health_fill:w()
        chk(isfinite(hfw) and hfw >= 0)
        if self._exp_hfw ~= nil then
            chk(hfw == self._exp_hfw)
        end

        local afw = self.armor_fill:w()
        chk(isfinite(afw) and afw >= 0)
        if self._exp_afw ~= nil then
            chk(afw == self._exp_afw)
        end

        for i = 1, 3 do
            local mx = self.markers[i]:x()
            chk(isfinite(mx) and mx >= 0)
            if self._exp_mx ~= nil and self._exp_mx[i] ~= nil then
                chk(mx == self._exp_mx[i])
            end
        end

        local ht = self.health_text:text()
        chk(type(ht) == "string")
        if self._exp_ht ~= nil then
            chk(ht == self._exp_ht)
        end

        local at = self.armor_text:text()
        chk(type(at) == "string")
        if self._exp_at ~= nil then
            chk(at == self._exp_at)
        end

        chk(self.health_fill:visible() == true)
        chk(self.armor_fill:visible() == true)
        chk(self.health_text:visible() == true)
        chk(self.armor_text:visible() == true)
        for i = 1, 3 do
            chk(self.markers[i]:visible() == true)
        end
        if self._health_bg then chk(self._health_bg:visible() == true) end
        if self._armor_bg then chk(self._armor_bg:visible() == true) end

        local hfs = self.health_text:font_size()
        chk(isfinite(hfs) and hfs > 0)
        if self._exp_fsz ~= nil then
            chk(hfs == self._exp_fsz)
        end

        local afs = self.armor_text:font_size()
        chk(isfinite(afs) and afs > 0)
        if self._exp_afsz ~= nil then
            chk(afs == self._exp_afsz)
        end
    end)

    if not worked then return false end
    return result
end

function G:destroy()
    if self._parent and self.root then
        safe_remove_owned(self._parent, self.root)
    end
    self.root = nil
    self.health_fill = nil
    self.armor_fill = nil
    self.markers = nil
    self.health_text = nil
    self.armor_text = nil
    self._health_bg = nil
    self._armor_bg = nil
    self._parent = nil
end

kyohud.hud.gauge = M
return M
