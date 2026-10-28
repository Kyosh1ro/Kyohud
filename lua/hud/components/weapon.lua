kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then
    Kyosh1roHUD = kyohud
end

kyohud.hud = kyohud.hud or {}

local FONT = "fonts/font_medium_mf"

local function isfinite(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    return true
end

local function live(p)
    if p == nil or type(alive) ~= "function" then return false end
    local ok, result = pcall(alive, p)
    return ok and result == true
end

local function shape(p, x, y, w, h)
    if p:x() ~= x or p:y() ~= y or p:w() ~= w or p:h() ~= h then
        p:set_shape(x, y, w, h)
    end
end

local ALLOWED_MODES = {single = true, auto = true, burst = true, volley = true}

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

local W = {}
W.__index = W

local M = {}

function M.new(parent, name)
    if not parent or not name then return nil end

    if not live(parent) then return nil end

    local existing = nil
    local child_ok = pcall(function()
        assert(type(parent.child) == "function", "collision lookup unavailable")
        existing = parent:child(name)
    end)
    if not child_ok or existing then return nil end

    local self = setmetatable({}, W)
    self._parent = parent
    self._name = name
    self._x = 0
    self._y = 0
    self._w = 0
    self._h = 0

    local ok = pcall(function()
        self._root = parent:panel({ name = name, layer = 1 })
        self._root:set_visible(true)

        self._name_text = self._root:text({ name = name .. "_name", font = FONT, layer = 1 })
        self._name_text:set_visible(true)
        pcall(function() self._name_text:set_font_size(16) end)

        self._ammo_text = self._root:text({ name = name .. "_ammo", font = FONT, layer = 1 })
        self._ammo_text:set_visible(true)
        pcall(function() self._ammo_text:set_font_size(14) end)

        self._mode_text = self._root:text({ name = name .. "_mode", font = FONT, layer = 1 })
        self._mode_text:set_visible(true)
        pcall(function() self._mode_text:set_font_size(14) end)
    end)

    if not ok or not self._root then
        if self._root and parent then
            safe_remove_owned(parent, self._root)
        end
        return nil
    end

    self._last_name = nil
    self._last_ammo = nil
    self._last_mode = nil
    self._last_selected = nil

    return self
end

function W:layout(x, y, w, h)
    if not self._root then return end

    local alive_ok = pcall(function()
        if type(alive) ~= "function" then error("no alive") end
        if not alive(self._root) then error("dead root") end
    end)
    if not alive_ok then return end

    local ax, ay, aw, ah = x or 0, y or 0, w or 0, h or 0
    if not (isfinite(ax) and isfinite(ay) and isfinite(aw) and isfinite(ah)) then return end
    if aw <= 0 or ah <= 0 then return end

    self._x = ax
    self._y = ay
    self._w = aw
    self._h = ah

    pcall(function()
        shape(self._root, self._x, self._y, self._w, self._h)
    end)

    self:_layout_texts()
end

function W:_layout_texts()
    local w = self._w
    local h = self._h
    if not (isfinite(w) and isfinite(h) and w > 0 and h > 0) then return end

    local alive_ok = pcall(function()
        if type(alive) ~= "function" then error("no alive") end
        if not alive(self._root) then error("dead root") end
        if self._name_text and not alive(self._name_text) then error("dead name_text") end
        if self._ammo_text and not alive(self._ammo_text) then error("dead ammo_text") end
        if self._mode_text and not alive(self._mode_text) then error("dead mode_text") end
    end)
    if not alive_ok then return end

    local half_h = h / 2

    pcall(function()
        if self._name_text then
            shape(self._name_text, 0, 0, w, half_h)
        end

        if self._ammo_text then
            shape(self._ammo_text, 0, half_h, w / 2, half_h)
        end

        if self._mode_text then
            shape(self._mode_text, w / 2, half_h, w / 2, half_h)
        end
    end)
end

-- Only native measurement is used for fitting. Geometry-only fixtures may omit it.
local function measured(p)
    if type(p.text_rect) ~= "function" then return nil end
    local _, _, w, h = p:text_rect()
    assert(isfinite(w) and isfinite(h), "invalid weapon text measurement")
    return w, h
end

local function trim_utf8(text)
    local last = #text
    while last > 0 and text:byte(last) >= 128 and text:byte(last) < 192 do last = last - 1 end
    return text:sub(1, last - 1)
end

function W:_fit_text(p, key, source, size)
    self._fit_cache = self._fit_cache or {}
    local cached = self._fit_cache[key]
    local width, height = p:w(), p:h()
    if not cached or cached.source ~= source or cached.size ~= size
        or cached.w ~= width or cached.h ~= height then
        local fitted, font = source, size
        if p:font_size() ~= font then p:set_font_size(font) end
        if p:text() ~= fitted then p:set_text(fitted) end
        local tw, th = measured(p)
        if tw and (tw > width or th > height) then
            font = math.max(6, math.min(font, font * math.min(width / math.max(tw, 1), height / math.max(th, 1))))
            if p:font_size() ~= font then p:set_font_size(font) end
            tw, th = measured(p)
            local remaining = source
            while tw > width and #remaining > 0 do
                remaining = trim_utf8(remaining)
                fitted = remaining .. "..."
                p:set_text(fitted)
                tw, th = measured(p)
            end
        end
        cached = {source=source, size=size, w=width, h=height, text=fitted, font=font}
        self._fit_cache[key] = cached
    end
    if p:text() ~= cached.text then p:set_text(cached.text) end
    if p:font_size() ~= cached.font then p:set_font_size(cached.font) end
    return cached.text, cached.font
end

function W:render(slot, selected, texts)
    if not self._root then return end

    local alive_ok = pcall(function()
        if type(alive) ~= "function" then error("no alive") end
        if not alive(self._root) then error("dead root") end
        if self._name_text and not alive(self._name_text) then error("dead name_text") end
        if self._ammo_text and not alive(self._ammo_text) then error("dead ammo_text") end
        if self._mode_text and not alive(self._mode_text) then error("dead mode_text") end
    end)
    if not alive_ok then return end

    local texts = texts or {}
    local slot = slot or {}

    local name_str = texts.name or ""

    local clip = slot.current_clip
    local res = slot.reserve

    local ammo_str
    if clip == nil then
        ammo_str = "-- / " .. (res ~= nil and tostring(res) or "--")
    elseif res == nil then
        ammo_str = tostring(clip) .. " / --"
    else
        ammo_str = tostring(clip) .. " / " .. tostring(res)
    end

    local mode_key = slot.fire_mode
    local mode_str = ""
    if mode_key and ALLOWED_MODES[mode_key] and texts[mode_key] then
        mode_str = texts[mode_key]
    else
        mode_str = "--"
    end

    if slot.alt_fire then
        mode_str = mode_str .. " " .. (texts.alt or "ALT")
    end

    pcall(function()
        self:_layout_texts()

        shape(self._root, self._x, self._y, self._w, self._h)

        local scale = self._h / 60
        self._last_name, self._name_size = self:_fit_text(self._name_text, "name", name_str, math.max(6, (selected and 18 or 16) * scale))
        self._last_ammo, self._ammo_size = self:_fit_text(self._ammo_text, "ammo", ammo_str, math.max(6, (selected and 16 or 14) * scale))
        self._last_mode, self._mode_size = self:_fit_text(self._mode_text, "mode", mode_str, math.max(6, (selected and 16 or 14) * scale))

        self._name_text:set_visible(true)
        self._ammo_text:set_visible(true)
        self._mode_text:set_visible(true)

        if selected ~= self._last_selected then
            if selected then
                pcall(function() self._name_text:set_color(Color(1, 1, 0)) end)
                pcall(function() self._ammo_text:set_color(Color(1, 1, 1)) end)
                pcall(function() self._mode_text:set_color(Color(1, 1, 1)) end)
            else
                pcall(function() self._name_text:set_color(Color(0.8, 0.8, 0.8)) end)
                pcall(function() self._ammo_text:set_color(Color(0.7, 0.7, 0.7)) end)
                pcall(function() self._mode_text:set_color(Color(0.7, 0.7, 0.7)) end)
            end
            self._last_selected = selected
        end
    end)
end

function W:verify()
    if not live(self._root) or not live(self._name_text)
        or not live(self._ammo_text) or not live(self._mode_text) then return false end
    local result = true
    local function chk(cond)
        if not cond then result = false end
    end

    local worked = pcall(function()
        chk(alive(self._root))
        chk(alive(self._name_text))
        chk(alive(self._ammo_text))
        chk(alive(self._mode_text))

        local rx = self._root:x()
        local ry = self._root:y()
        local rw = self._root:w()
        local rh = self._root:h()
        chk(isfinite(rx) and rx >= 0)
        chk(isfinite(ry) and ry >= 0)
        chk(isfinite(rw) and rw >= 0)
        chk(isfinite(rh) and rh >= 0)

        local TOL = 0.5
        chk(math.abs(rx - self._x) <= TOL)
        chk(math.abs(ry - self._y) <= TOL)
        chk(math.abs(rw - self._w) <= TOL)
        chk(math.abs(rh - self._h) <= TOL)

        local w = self._w
        local h = self._h
        local half_h = h / 2
        local half_w = w / 2

        local nx = self._name_text:x()
        local ny = self._name_text:y()
        local nw = self._name_text:w()
        local nh = self._name_text:h()
        chk(isfinite(nx) and math.abs(nx - 0) <= TOL)
        chk(isfinite(ny) and math.abs(ny - 0) <= TOL)
        chk(isfinite(nw) and math.abs(nw - w) <= TOL)
        chk(isfinite(nh) and math.abs(nh - half_h) <= TOL)

        local ax = self._ammo_text:x()
        local ay = self._ammo_text:y()
        local aw = self._ammo_text:w()
        local ah = self._ammo_text:h()
        chk(isfinite(ax) and math.abs(ax - 0) <= TOL)
        chk(isfinite(ay) and math.abs(ay - half_h) <= TOL)
        chk(isfinite(aw) and math.abs(aw - half_w) <= TOL)
        chk(isfinite(ah) and math.abs(ah - half_h) <= TOL)

        local mx = self._mode_text:x()
        local my = self._mode_text:y()
        local mw = self._mode_text:w()
        local mh = self._mode_text:h()
        chk(isfinite(mx) and math.abs(mx - half_w) <= TOL)
        chk(isfinite(my) and math.abs(my - half_h) <= TOL)
        chk(isfinite(mw) and math.abs(mw - half_w) <= TOL)
        chk(isfinite(mh) and math.abs(mh - half_h) <= TOL)

        chk(self._root:visible() == true)

        local nt = self._name_text:text()
        chk(type(nt) == "string")
        if self._last_name ~= nil then
            chk(nt == self._last_name)
        end

        local at = self._ammo_text:text()
        chk(type(at) == "string")
        if self._last_ammo ~= nil then
            chk(at == self._last_ammo)
        end

        local mt = self._mode_text:text()
        chk(type(mt) == "string")
        if self._last_mode ~= nil then
            chk(mt == self._last_mode)
        end

        chk(self._name_text:visible() == true)
        chk(self._ammo_text:visible() == true)
        chk(self._mode_text:visible() == true)

        local ok_ns, ns = pcall(function() return self._name_text:font_size() end)
        chk(ok_ns and isfinite(ns) and self._name_size ~= nil and math.abs(ns-self._name_size) <= 0.05)
        local ok_as, as = pcall(function() return self._ammo_text:font_size() end)
        chk(ok_as and isfinite(as) and self._ammo_size ~= nil and math.abs(as-self._ammo_size) <= 0.05)
        local ok_ms, ms = pcall(function() return self._mode_text:font_size() end)
        chk(ok_ms and isfinite(ms) and self._mode_size ~= nil and math.abs(ms-self._mode_size) <= 0.05)
        for _, p in ipairs({self._name_text, self._ammo_text, self._mode_text}) do
            local tw, th = measured(p)
            if tw then chk(tw <= p:w()+0.5 and th <= p:h()+0.5) end
        end
    end)

    if not worked then return false end
    return result
end

function W:destroy()
    if self._parent and self._root then
        safe_remove_owned(self._parent, self._root)
    end
    self._root = nil
    self._name_text = nil
    self._ammo_text = nil
    self._mode_text = nil
    self._parent = nil
end

kyohud.hud.weapon_component = M
return M
