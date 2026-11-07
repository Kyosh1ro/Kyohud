kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then
    Kyosh1roHUD = kyohud
end

kyohud.hud = kyohud.hud or {}

local FONT = "fonts/font_medium_mf"
local INK = Color(1, 1, 1)
local DIM = Color(.43, .47, .51)
local SECONDARY = Color(.73, .75, .78)

local function style(p, color, alpha)
    local c = p:color()
    return c and math.abs(c.r-color.r)<.001 and math.abs(c.g-color.g)<.001
        and math.abs(c.b-color.b)<.001 and math.abs(p:alpha()-alpha)<.001
end

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

local function near(a, b)
    return isfinite(a) and isfinite(b) and math.abs(a-b) <= 0.05
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
        self._background = self._root:rect({name="background",layer=0,color=Color(.03,.035,.043)})
        self._mode_bg = self._root:rect({name="mode_bg",layer=0,color=Color(.91,.93,.94)})

        self._name_text = self._root:text({ name = name .. "_name", font = FONT, layer = 1 })
        self._name_text:set_visible(true)
        pcall(function() self._name_text:set_font_size(16) end)

        self._ammo_text = self._root:text({ name = name .. "_clip", font = "fonts/font_large_mf", layer = 1 })
        self._clip_text = self._ammo_text
        self._reserve_text = self._root:text({ name = name .. "_reserve", font = "fonts/font_large_mf", layer = 1 })
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
    self._compact_selected = false

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
    if self._compact then
        local g=self:_compact_shapes()
        pcall(function()
            for key,r in pairs(g) do shape(self[key],r[1],r[2],r[3],r[4]) end
        end)
        return
    end
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

    local half_h = h * .25

    pcall(function()
        if self._name_text then
            shape(self._name_text, 0, 0, w * .63, half_h)
        end

        if self._ammo_text then
            shape(self._ammo_text, 0, half_h, w * .65, h - half_h)
            shape(self._reserve_text, w * .67, half_h, w * .33, h - half_h)
        end

        if self._mode_text then
            shape(self._mode_text, w * .65, 0, w * .35, half_h)
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
            while key == "name" and tw > width and #remaining > 0 do
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
    if not live(self._reserve_text) or not live(self._background) or not live(self._mode_bg) then
        if live(self._root) then pcall(function() self._root:set_visible(false) end) end
        return
    end

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

    local ammo_str = clip ~= nil and tostring(clip) or "--"
    local reserve_str = res ~= nil and tostring(res) or "--"
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
        self._compact_selected = selected == true
        self:_layout_texts()

        shape(self._root, self._x, self._y, self._w, self._h)

        local scale = self._compact or self._h / 120

        if self._compact then
            self._last_name = ""
            self._name_size = 16 * scale
            self._name_text:set_text("")
            self._name_text:set_font_size(self._name_size)
        else
            self._last_name, self._name_size = self:_fit_text(self._name_text, "name", name_str, math.max(6, self._compact_header_font or 16 * scale))
        end

        local clip_fs, res_fs
        if self._compact then
            clip_fs = math.max(6, (selected and 60 or 24) * scale)
            res_fs = math.max(6, (selected and 22 or 15) * scale)
        else
            clip_fs = math.max(6, (selected and 60 or 36) * scale)
            res_fs = math.max(6, (selected and 22 or 16) * scale)
        end
        self._last_ammo, self._ammo_size = self:_fit_text(self._ammo_text, "ammo", ammo_str, clip_fs)
        self._last_reserve, self._reserve_size = self:_fit_text(self._reserve_text, "reserve", reserve_str, res_fs)

        local mode_fs = math.max(6, self._compact_header_font or 12 * scale)
        if self._compact and not selected then
            self._last_mode = mode_str
            self._mode_size = mode_fs
        else
            self._last_mode, self._mode_size = self:_fit_text(self._mode_text, "mode", mode_str, mode_fs)
        end

        if self._compact then
            self._reserve_text:set_color(INK)
            self._reserve_text:set_alpha(selected and 1 or .7)
        else
            self._reserve_text:set_color(DIM)
            self._reserve_text:set_alpha(1)
        end

        if self._compact then
            local e=self._compact
            shape(self._background, 0, 12*e, self._w, 80*e)
            self._background:set_visible(false)
        else
            shape(self._background, 0, 0, self._w, self._h)
            self._background:set_color(Color(.03,.035,.043))
            self._background:set_alpha(.86)
            self._background:set_visible(true)
        end

        if not self._compact then
            shape(self._mode_bg, self._w*.65, 0, self._w*.35, self._h*.25)
            self._mode_bg:set_color(Color(.91,.93,.94))
            self._mode_bg:set_alpha(1)
            self._mode_bg:set_visible(true)
        elseif selected then
            local r = self:_compact_shapes()._mode_text
            shape(self._mode_bg, r[1]-4*scale, r[2], r[3]+8*scale, r[4])
            self._mode_bg:set_color(Color(.91,.93,.94))
            self._mode_bg:set_alpha(1)
            self._mode_bg:set_visible(true)
        else
            self._mode_bg:set_visible(false)
        end

        self._mode_text:set_color(Color(.04,.04,.04))
        self._mode_text:set_alpha(1)
        self._name_text:set_color((self._compact or selected) and INK or SECONDARY)
        self._name_text:set_alpha(1)
        if self._compact then
            self._ammo_text:set_color(INK)
            self._ammo_text:set_alpha(selected and 1 or .7)
        else
            self._ammo_text:set_color(selected and INK or SECONDARY)
            self._ammo_text:set_alpha(1)
        end
        self._selected = selected == true

        self._ammo_text:set_visible(true)
        self._reserve_text:set_visible(true)
        if self._compact then
            self._name_text:set_visible(false)
            self._mode_text:set_visible(selected == true)
        else
            self._name_text:set_visible(true)
            self._mode_text:set_visible(true)
        end
    end)
end

function W:verify()
    if self._compact then return self:_verify_compact() end
    if not live(self._reserve_text) or not live(self._root) or not live(self._name_text)
        or not live(self._ammo_text) or not live(self._mode_text) then return false end
    local result = true
    local function chk(cond)
        if not cond then result = false end
    end

    local worked = pcall(function()
        chk(live(self._background) and live(self._mode_bg))
        chk(self._background:visible() and self._mode_bg:visible())
        chk(style(self._name_text,self._selected and INK or SECONDARY,1))
        chk(style(self._ammo_text,self._selected and INK or SECONDARY,1))
        chk(style(self._reserve_text,DIM,1))
        chk(style(self._mode_text,Color(.04,.04,.04),1))
        chk(style(self._background,Color(.03,.035,.043),.86))
        chk(style(self._mode_bg,Color(.91,.93,.94),1))
        chk(math.abs(self._background:x())<=.05 and math.abs(self._background:y())<=.05)
        chk(math.abs(self._background:w()-self._w)<=.05 and math.abs(self._background:h()-self._h)<=.05)
        chk(math.abs(self._mode_bg:x()-self._w*.65)<=.05 and math.abs(self._mode_bg:y())<=.05)
        chk(math.abs(self._mode_bg:w()-self._w*.35)<=.05 and math.abs(self._mode_bg:h()-self._h*.25)<=.05)
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
        local half_h = h * .25
        local half_w = w * .65

        local nx = self._name_text:x()
        local ny = self._name_text:y()
        local nw = self._name_text:w()
        local nh = self._name_text:h()
        chk(isfinite(nx) and math.abs(nx - 0) <= TOL)
        chk(isfinite(ny) and math.abs(ny - 0) <= TOL)
        chk(isfinite(nw) and math.abs(nw - w * .63) <= TOL)
        chk(isfinite(nh) and math.abs(nh - half_h) <= TOL)

        local ax = self._ammo_text:x()
        local ay = self._ammo_text:y()
        local aw = self._ammo_text:w()
        local ah = self._ammo_text:h()
        chk(isfinite(ax) and math.abs(ax - 0) <= TOL)
        chk(isfinite(ay) and math.abs(ay - half_h) <= TOL)
        chk(isfinite(aw) and math.abs(aw - half_w) <= TOL)
        chk(isfinite(ah) and math.abs(ah - (h - half_h)) <= TOL)

        local mx = self._mode_text:x()
        local my = self._mode_text:y()
        local mw = self._mode_text:w()
        local mh = self._mode_text:h()
        chk(isfinite(mx) and math.abs(mx - half_w) <= TOL)
        chk(isfinite(my) and math.abs(my) <= TOL)
        chk(isfinite(mw) and math.abs(mw - w * .35) <= TOL)
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
        chk(self._reserve_text:text() == self._last_reserve)
        chk(math.abs(self._reserve_text:font_size() - self._reserve_size) <= .05)
        chk(self._reserve_text:visible() == true)
        chk(math.abs(self._reserve_text:x() - w * .67) <= TOL)
        chk(math.abs(self._reserve_text:y() - half_h) <= TOL)
        chk(math.abs(self._reserve_text:w() - w * .33) <= TOL)
        chk(math.abs(self._reserve_text:h() - (h-half_h)) <= TOL)
        for _, p in ipairs({self._name_text, self._ammo_text, self._mode_text, self._reserve_text}) do
            local tw, th = measured(p)
            if tw then chk(tw <= p:w()+0.5 and th <= p:h()+0.5) end
        end
    end)

    if not worked then return false end
    return result
end

-- Measure native text once per changed snapshot/layout. Maxima reserve enough
-- space for ordinary shots without making columns breathe on every digit.
function W:preferred_width(slot,selected,texts,e)
    if not live(self._clip_text) or not live(self._reserve_text) or not live(self._name_text) or not live(self._mode_text) then return nil end
    self._compact=e
    local key=table.concat({tostring(e),tostring(selected),tostring(slot.current_clip),tostring(slot.max_clip),
        tostring(slot.reserve),tostring(slot.max_total),tostring(slot.fire_mode),tostring(slot.alt_fire),
        tostring(texts.name),tostring(texts[slot.fire_mode]),tostring(texts.alt)},"\31")
    local cached=self._width_cache and self._width_cache[selected and 2 or 1]
    if cached and cached.key==key then
        self._compact_clip_w=cached.clip;self._compact_reserve_w=cached.reserve;self._compact_mode_w=cached.mode
        self._compact_name_w=cached.name
        return cached.width
    end
    local function width(p,text,size)
        p:set_text(tostring(text));p:set_font_size(size)
        local w,h=measured(p)
        assert(isfinite(w) and isfinite(h),"missing compact weapon measurement")
        return math.ceil(w)+e
    end
    local ok,result=pcall(function()
        local clip_fs=(selected and 60 or 24)*e
        local res_fs=(selected and 22 or 15)*e
        self._compact_clip_w=math.max(width(self._clip_text,slot.current_clip or "--",clip_fs),width(self._clip_text,slot.max_clip or "--",clip_fs))
        self._compact_reserve_w=math.max(width(self._reserve_text,slot.reserve or "--",res_fs),width(self._reserve_text,slot.max_total or "--",res_fs))
        local mode=texts[slot.fire_mode] or "--"
        if slot.alt_fire then mode=mode.." "..(texts.alt or "ALT") end
        self._compact_mode_w=width(self._mode_text,mode,16*e)
        self._compact_name_w=0
        if selected then
            local header=self._compact_mode_w+8*e
            return math.max(header,self._compact_clip_w+5*e+self._compact_reserve_w)+12*e
        else
            return math.max(self._compact_clip_w,self._compact_reserve_w)+12*e
        end
    end)
    if ok then
        self._width_cache=self._width_cache or {}
        self._width_cache[selected and 2 or 1]={key=key,width=result,clip=self._compact_clip_w,reserve=self._compact_reserve_w,mode=self._compact_mode_w,name=0}
    end
    return ok and result or nil
end

function W:_compact_shapes()
    local e=self._compact
    local mode_w=self._compact_mode_w or 0
    self._compact_header_font=16*e
    local mode_h=self._compact_header_font
    local mode_rect={self._w-mode_w-4*e,0,mode_w,mode_h}
    local clip_fs=(self._compact_selected and 60 or 24)*e
    local res_fs=(self._compact_selected and 22 or 15)*e
    if self._compact_selected then
        local bottom=self._h-2*e
        return {
            _name_text={0,0,0,0},
            _mode_text=mode_rect,
            _ammo_text={0,18*e,self._compact_clip_w,clip_fs},
            _reserve_text={self._compact_clip_w+5*e,bottom-res_fs,self._compact_reserve_w,res_fs},
        }
    else
        local res_w=self._compact_reserve_w or 0
        local clip_w=self._compact_clip_w or 0
        local reserve_x=(self._w-res_w)/2
        local bottom=self._h-2*e
        local reserve_y=bottom-res_fs
        local clip_x=(self._w-clip_w)/2
        local clip_y=reserve_y-3*e-clip_fs
        return {
            _name_text={0,0,0,0},
            _mode_text=mode_rect,
            _ammo_text={clip_x,clip_y,clip_w,clip_fs},
            _reserve_text={reserve_x,reserve_y,res_w,res_fs},
        }
    end
end

function W:_verify_compact()
    local ok,result=pcall(function()
        local function rect(p,r)
            return live(p) and p:visible() and isfinite(p:x()) and isfinite(p:y())
                and isfinite(p:w()) and isfinite(p:h()) and math.abs(p:x()-r[1])<.5
                and math.abs(p:y()-r[2])<.5 and math.abs(p:w()-r[3])<.5 and math.abs(p:h()-r[4])<.5
        end
        if not rect(self._root,{self._x,self._y,self._w,self._h}) then return false end
        if not live(self._name_text) then return false end
        if self._name_text:visible() then return false end
        local shapes=self:_compact_shapes()
        local ammo_p=self._ammo_text
        if not rect(ammo_p,shapes._ammo_text) or ammo_p:text()~=self._last_ammo or not isfinite(self._ammo_size)
            or math.abs(ammo_p:font_size()-self._ammo_size)>.05 or not style(ammo_p,INK,self._selected and 1 or .7) then return false end
        local aw,ah=measured(ammo_p)
        if not aw or aw>ammo_p:w()+.5 or ah>ammo_p:h()+.5 then return false end
        local res_p=self._reserve_text
        if not rect(res_p,shapes._reserve_text) or res_p:text()~=self._last_reserve or not isfinite(self._reserve_size)
            or math.abs(res_p:font_size()-self._reserve_size)>.05 or not style(res_p,INK,self._selected and 1 or .7) then return false end
        local rw,rh=measured(res_p)
        if not rw or rw>res_p:w()+.5 or rh>res_p:h()+.5 then return false end
        if self._selected then
            local mode_p=self._mode_text
            if not rect(mode_p,shapes._mode_text) or mode_p:text()~=self._last_mode or not isfinite(self._mode_size)
                or math.abs(mode_p:font_size()-self._mode_size)>.05 or not style(mode_p,Color(.04,.04,.04),1) then return false end
            local mw,mh=measured(mode_p)
            if not mw or mw>mode_p:w()+.5 or mh>mode_p:h()+.5 then return false end
            local r=shapes._mode_text
            if not rect(self._mode_bg,{r[1]-4*self._compact,r[2],r[3]+8*self._compact,r[4]})
                or not style(self._mode_bg,Color(.91,.93,.94),1) then return false end
        else
            if not live(self._mode_text) then return false end
            if self._mode_text:visible() then return false end
            if not live(self._mode_bg) then return false end
            if self._mode_bg:visible() then return false end
        end
        if not live(self._background) then return false end
        if self._background:visible() then return false end
        local e=self._compact
        return near(self._background:x(),0) and near(self._background:y(),12*e)
            and near(self._background:w(),self._w) and near(self._background:h(),80*e)
    end)
    return ok and result==true
end

function W:destroy()
    if self._parent and self._root then
        safe_remove_owned(self._parent, self._root)
    end
    self._root = nil
    self._name_text = nil
    self._ammo_text = nil
    self._clip_text = nil
    self._reserve_text = nil
    self._background = nil
    self._mode_bg = nil
    self._mode_text = nil
    self._parent = nil
end

kyohud.hud.weapon_component = M
return M
