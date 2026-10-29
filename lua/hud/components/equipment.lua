kyohud = kyohud or {}
Kyosh1roHUD = kyohud
kyohud.hud = kyohud.hud or {}

-- Pure persistent row. Sources, localization and clocks belong to the consumer.
local C = {}
local Row = {}
Row.__index = Row
local FONT = "fonts/font_medium_mf"
local WHITE = Color(1, 1, 1)
local DIM = Color(0.7, 0.7, 0.7)
local ACCENT = Color(1, 0.8, 0.3)

local function finite(v)
    return type(v) == "number" and v == v and v ~= math.huge and v ~= -math.huge
end
local function live(p)
    if p == nil or type(alive) ~= "function" then return false end
    local ok, result = pcall(alive, p)
    return ok and result == true
end
local function shape(p, x, y, w, h)
    if p:x() ~= x or p:y() ~= y or p:w() ~= w or p:h() ~= h then p:set_shape(x, y, w, h) end
end
local function remove(parent, root)
    if not live(parent) or not live(root) then return end
    pcall(function()
        if parent:child(root:name()) == root then parent:remove(root) end
    end)
end
local function near(a, b)
    return finite(a) and finite(b) and math.abs(a-b) <= 0.05
end
local function trim(text)
    local n = #text
    while n > 0 and text:byte(n) >= 128 and text:byte(n) < 192 do n = n-1 end
    return text:sub(1, n-1)
end
local function measure(p)
    if type(p.text_rect) ~= "function" then return nil end
    local _, _, w, h = p:text_rect()
    assert(finite(w) and finite(h), "invalid equipment measurement")
    return w, h
end

function C.new(parent, name)
    if not live(parent) then return nil end
    local ok, existing = pcall(function() return parent:child(name) end)
    if not ok or existing then return nil end
    local self = setmetatable({_parent=parent, _cache={}}, Row)
    ok = pcall(function()
        self._root = parent:panel({name=name, layer=1})
        self._label = self._root:text({name="label",font=FONT,layer=2,text=""})
        self._value = self._root:text({name="value",font=FONT,layer=2,text=""})
        self._track = self._root:rect({name="track",layer=1,color=DIM,alpha=0.2})
        self._fill = self._root:rect({name="fill",layer=2,color=ACCENT})
    end)
    if not ok then remove(parent,self._root); return nil end
    return self
end

function Row:layout(x, y, w, h)
    if not finite(x) or not finite(y) or not finite(w) or not finite(h) or w <= 0 or h <= 0 then
        self._geometry = nil
        return
    end
    self._geometry = {x=x,y=y,w=w,h=h}
end

function Row:_fit(p, key, text, font)
    local cached = self._cache[key]
    local w,h = p:w(),p:h()
    if not cached or cached.source ~= text or cached.font ~= font or cached.w ~= w or cached.h ~= h then
        local fitted,size = text,font
        p:set_text(fitted);p:set_font_size(size)
        local tw,th = measure(p)
        if tw and (tw>w or th>h) then
            size=math.max(6,math.min(size,size*math.min(w/math.max(tw,1),h/math.max(th,1))))
            p:set_font_size(size)
            tw,th=measure(p)
            local remaining=text
            while tw>w and #remaining>0 do
                remaining=trim(remaining);fitted=remaining.."..."
                p:set_text(fitted);tw,th=measure(p)
            end
        end
        cached={source=text,font=font,w=w,h=h,text=fitted,size=size}
        self._cache[key]=cached
    end
    if p:text()~=cached.text then p:set_text(cached.text) end
    if p:font_size()~=cached.size then p:set_font_size(cached.size) end
    return cached
end

function Row:_live()
    return live(self._root) and live(self._label) and live(self._value)
        and live(self._track) and live(self._fill)
end

function Row:render(label, value, progress, selected)
    self._verified = false
    if not self:_live() or not self._geometry then return end
    local g=self._geometry
    self._progress=finite(progress) and math.min(1,math.max(0,progress)) or nil
    self._selected=selected == true
    local ok=pcall(function()
        shape(self._root,g.x,g.y,g.w,g.h)
        shape(self._label,0,0,g.w*.61,g.h-4)
        shape(self._value,g.w*.62,0,g.w*.38,g.h-4)
        shape(self._track,0,g.h-3,g.w,2)
        shape(self._fill,0,g.h-3,g.w*(self._progress or 0),2)
        self._expected_label=self:_fit(self._label,"label",label or "",g.h*.56)
        self._expected_value=self:_fit(self._value,"value",value or "--",g.h*.56)
        self._label:set_color(self._selected and ACCENT or DIM)
        self._value:set_color(WHITE)
        self._label:set_visible(true);self._value:set_visible(true)
        self._track:set_visible(self._progress~=nil);self._fill:set_visible(self._progress~=nil)
        self._root:set_visible(true)
    end)
    self._verified=ok and self:verify()
end

function Row:verify()
    if not self:_live() or not self._geometry or not self._expected_label or not self._expected_value then return false end
    local ok,result=pcall(function()
        local g=self._geometry
        local function geom(p,x,y,w,h)
            return near(p:x(),x) and near(p:y(),y) and near(p:w(),w) and near(p:h(),h)
        end
        if not geom(self._root,g.x,g.y,g.w,g.h) or not self._root:visible() then return false end
        if not geom(self._label,0,0,g.w*.61,g.h-4)
            or not geom(self._value,g.w*.62,0,g.w*.38,g.h-4)
            or not geom(self._track,0,g.h-3,g.w,2)
            or not geom(self._fill,0,g.h-3,g.w*(self._progress or 0),2) then return false end
        for _,pair in ipairs({{self._label,self._expected_label},{self._value,self._expected_value}}) do
            local p,e=pair[1],pair[2]
            if p:text()~=e.text or not near(p:font_size(),e.size) or not p:visible() then return false end
            local tw,th=measure(p)
            if tw and (tw>p:w()+.05 or th>p:h()+.05) then return false end
        end
        return self._fill:visible()==(self._progress~=nil) and self._track:visible()==(self._progress~=nil)
    end)
    return ok and result == true
end

function Row:destroy()
    remove(self._parent,self._root)
    self._root=nil;self._parent=nil
    self._label=nil;self._value=nil;self._track=nil;self._fill=nil
end

kyohud.hud.equipment_component=C
