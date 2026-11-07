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
local function style(p,color,alpha)
    local c=p:color()
    local function s(a,b) return finite(a) and finite(b) and math.abs(a-b) <= 0.005 end
    return c and s(c.r,color.r) and s(c.g,color.g) and s(c.b,color.b) and s(p:alpha(),alpha)
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
    self._tile=nil
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
            while key=="label" and tw>w and #remaining>0 do
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

function Row:render(label, value, progress, selected, icon)
    if self._tile then return self:_render_cell(label,value,selected,icon) end
    self._verified = false
    if not self:_live() or not self._geometry then return end
    local g=self._geometry
    self._progress=finite(progress) and math.min(1,math.max(0,progress)) or nil
    self._selected=selected == true
    local ok=pcall(function()
        self._icon_descriptor = icon
        if icon and not live(self._icon) then
            self._icon = self._root:bitmap({name="icon",layer=2,texture=icon.texture,texture_rect=icon.rect})
        end
        self._icon_offset = icon and g.h or 0
        if live(self._icon) then
            if icon then
                self._icon:set_image(icon.texture,unpack(icon.rect))
                local iw = (g.h-6) * icon.rect[3] / icon.rect[4]
                iw = math.min(g.h-6,iw)
                shape(self._icon,0,2,iw,iw*icon.rect[4]/icon.rect[3])
                self._icon:set_color(WHITE)
                self._icon:set_alpha(1)
            end
            self._icon:set_visible(icon~=nil)
        end
        shape(self._root,g.x,g.y,g.w,g.h)
        shape(self._label,self._icon_offset,0,g.w*.61-self._icon_offset,g.h-4)
        shape(self._value,g.w*.62,0,g.w*.38,g.h-4)
        shape(self._track,0,g.h-3,g.w,2)
        shape(self._fill,0,g.h-3,g.w*(self._progress or 0),2)
        self._expected_label=self:_fit(self._label,"label",label or "",g.h*.56)
        self._expected_value=self:_fit(self._value,"value",value or "--",g.h*.56)
        self._label:set_color(self._selected and ACCENT or DIM)
        self._value:set_color(WHITE)
        self._label:set_alpha(1);self._value:set_alpha(1)
        self._track:set_color(DIM);self._track:set_alpha(.2)
        self._fill:set_color(ACCENT);self._fill:set_alpha(1)
        self._label:set_visible(true);self._value:set_visible(true)
        self._track:set_visible(self._progress~=nil);self._fill:set_visible(self._progress~=nil)
        self._root:set_visible(true)
    end)
    self._verified=ok and self:verify()
end

function Row:verify()
    if self._tile then return self:_verify_cell() end
    if not self:_live() or not self._geometry or not self._expected_label or not self._expected_value then return false end
    local ok,result=pcall(function()
        local g=self._geometry
        local function geom(p,x,y,w,h)
            return near(p:x(),x) and near(p:y(),y) and near(p:w(),w) and near(p:h(),h)
        end
        if not geom(self._root,g.x,g.y,g.w,g.h) or not self._root:visible() then return false end
        if not style(self._label,self._selected and ACCENT or DIM,1) or not style(self._value,WHITE,1)
            or not style(self._track,DIM,.2) or not style(self._fill,ACCENT,1) then return false end
        if not geom(self._label,self._icon_offset or 0,0,g.w*.61-(self._icon_offset or 0),g.h-4)
            or not geom(self._value,g.w*.62,0,g.w*.38,g.h-4)
            or not geom(self._track,0,g.h-3,g.w,2)
            or not geom(self._fill,0,g.h-3,g.w*(self._progress or 0),2) then return false end
        for _,pair in ipairs({{self._label,self._expected_label},{self._value,self._expected_value}}) do
            local p,e=pair[1],pair[2]
            if p:text()~=e.text or not near(p:font_size(),e.size) or not p:visible() then return false end
            local tw,th=measure(p)
            if tw and (tw>p:w()+.05 or th>p:h()+.05) then return false end
        end
        if self._icon_descriptor then
            if not live(self._icon) or not self._icon:visible() then return false end
            local r=self._icon_descriptor.rect
            local iw=math.min(g.h-6,(g.h-6)*r[3]/r[4])
            if not geom(self._icon,0,2,iw,iw*r[4]/r[3]) or not style(self._icon,WHITE,1) then return false end
            local texture=self._icon:texture_name()
            local desired=Idstring(self._icon_descriptor.texture)
            if texture~=self._icon_descriptor.texture and texture:key()~=desired:key() then return false end
        end
        return self._fill:visible()==(self._progress~=nil) and self._track:visible()==(self._progress~=nil)
    end)
    return ok and result == true
end

function Row:cell_width(value,e,both)
    if not live(self._value) then return nil end
    local cache=self._cell_width_cache
    if cache and cache.value==value and cache.e==e and cache.both==both then self._cell_value_w=cache.ink;return cache.width end
    local ok,width=pcall(function()
        self._value:set_text(value);self._value:set_font_size(20*e)
        local w,h=measure(self._value)
        assert(finite(w) and finite(h),"missing equipment cell measurement")
        self._cell_value_w=math.ceil(w)+.5*e
        return math.max(34*e,self._cell_value_w+(both and 8*e or 0))+8*e
    end)
    if ok then self._cell_width_cache={value=value,e=e,width=width,ink=self._cell_value_w,both=both} end
    return ok and width or nil
end

function Row:cell_layout(x,y,w,h,e,both)
    self:layout(x,y,w,h)
    self._tile=e
    self._cell_both=both==true
end

function Row:_cell_shapes(icon)
    local e,g=self._tile,self._geometry
    local left=self._cell_both and 8*e or 0
    local body_w=g.w-8*e-left
    local center=self._cell_both and g.w/2 or (g.w-4*e)/2
    local iw,ih=0,0
    if icon then
        local k=math.min(34*e/icon.rect[3],29*e/icon.rect[4],body_w/icon.rect[3])
        iw,ih=icon.rect[3]*k,icon.rect[4]*k
    end
    local image_h=icon and ih or 29*e
    local top=(g.h-image_h-4*e-24*e)/2
    local value_w=math.min(body_w,self._cell_value_w or body_w)
    return {label={center-body_w/2,top,body_w,29*e},value={center-value_w/2,top+image_h+4*e,value_w,24*e},
        icon={center-iw/2,top,iw,ih},background={left,0,body_w,g.h},cut={g.w-8*e,0,8*e,g.h},left={0,0,8*e,g.h}}
end

function Row:_render_cell(label,value,selected,icon)
    if not self:_live() or not self._geometry then return end
    self._selected=selected==true
    self._icon_descriptor=icon
    local ok=pcall(function()
        local g=self._geometry
        shape(self._root,g.x,g.y,g.w,g.h)
        if not live(self._cell_bg) then
            self._cell_bg=self._root:rect({name="cell_background",layer=0,color=Color(1,1,1)})
        end
        if icon and not live(self._icon) then
            self._icon=self._root:bitmap({name="icon",layer=2,texture=icon.texture,texture_rect=icon.rect})
        end
        local s=self:_cell_shapes(icon)
        local size=self._cell_cut_size
        if not live(self._cell_cut) or not size or size.w~=s.cut[3] or size.h~=s.cut[4] then
            remove(self._root,self._cell_cut)
            self._cell_cut=nil;self._cell_cut_size=nil
            self._cell_cut=self._root:polygon({name="cell_cut",layer=0,x=s.cut[1],y=0,w=s.cut[3],h=s.cut[4],
                triangles={Vector3(0,0,0),Vector3(s.cut[3],0,0),Vector3(0,s.cut[4],0)},color=Color(1,1,1)})
            self._cell_cut_size={w=s.cut[3],h=s.cut[4]}
        end
        shape(self._cell_bg,unpack(s.background));shape(self._cell_cut,unpack(s.cut))
        local ls=self._cell_left_size
        if self._cell_both then
            if not live(self._cell_left_cut) or not ls or ls.w~=s.left[3] or ls.h~=s.left[4] then
                remove(self._root,self._cell_left_cut)
                local w,h=s.left[3],s.left[4]
                self._cell_left_cut=self._root:polygon({name="cell_left_cut",layer=0,x=0,y=0,w=w,h=h,
                    triangles={Vector3(w,0,0),Vector3(w,h,0),Vector3(0,h,0)},color=Color(1,1,1)})
                self._cell_left_size={w=w,h=h}
            end
            shape(self._cell_left_cut,unpack(s.left))
            self._cell_left_cut:set_color(Color(1,1,1));self._cell_left_cut:set_alpha(.05);self._cell_left_cut:set_visible(true)
        elseif self._cell_left_cut then
            remove(self._root,self._cell_left_cut);self._cell_left_cut=nil;self._cell_left_size=nil
        end
        for _,p in ipairs({self._cell_bg,self._cell_cut}) do
            p:set_color(Color(1,1,1));p:set_alpha(.05);p:set_visible(true)
        end
        shape(self._label,unpack(s.label));shape(self._value,unpack(s.value))
        self._expected_label=self:_fit(self._label,"label",label or "",12*self._tile)
        self._expected_value=self:_fit(self._value,"value",value or "--",20*self._tile)
        self._label:set_visible(icon==nil)
        self._label:set_color(self._selected and ACCENT or DIM);self._label:set_alpha(1)
        self._value:set_visible(true);self._value:set_color(WHITE);self._value:set_alpha(1)
        if live(self._icon) then
            if icon then
                self._icon:set_image(icon.texture,unpack(icon.rect))
                shape(self._icon,unpack(s.icon))
                self._icon:set_color(self._selected and ACCENT or WHITE);self._icon:set_alpha(1)
            end
            self._icon:set_visible(icon~=nil)
        end
        self._track:set_visible(false);self._fill:set_visible(false)
        self._root:set_visible(true)
    end)
    self._verified=ok and self:verify()
end

function Row:_verify_cell()
    local ok,result=pcall(function()
        if not self:_live() or not self._geometry then return false end
        local g=self._geometry
        local function rect(p,r)
            return near(p:x(),r[1]) and near(p:y(),r[2]) and near(p:w(),r[3]) and near(p:h(),r[4])
        end
        local s=self:_cell_shapes(self._icon_descriptor)
        if self._cell_both then
            if not live(self._cell_left_cut) or not self._cell_left_cut:visible()
                or not rect(self._cell_left_cut,s.left) or not style(self._cell_left_cut,Color(1,1,1),.05) then return false end
        elseif live(self._cell_left_cut) then return false end
        if not live(self._cell_bg) or not live(self._cell_cut)
            or not self._cell_bg:visible() or not self._cell_cut:visible()
            or not rect(self._cell_bg,s.background) or not rect(self._cell_cut,s.cut)
            or not style(self._cell_bg,Color(1,1,1),.05)
            or not style(self._cell_cut,Color(1,1,1),.05) then return false end
        if not self._root:visible() or not rect(self._root,{g.x,g.y,g.w,g.h})
            or not rect(self._label,s.label) or not rect(self._value,s.value) then return false end
        for _,pair in ipairs({{self._label,self._expected_label},{self._value,self._expected_value}}) do
            local p,v=pair[1],pair[2]
            if not v or p:text()~=v.text or not near(p:font_size(),v.size) then return false end
            local w,h=measure(p)
            if not w or w>p:w()+.5 or h>p:h()+.5 then return false end
        end
        if not self._value:visible() or not style(self._value,WHITE,1)
            or self._track:visible() or self._fill:visible() then return false end
        if self._icon_descriptor then
            local p=self._icon
            if not live(p) or not p:visible() or self._label:visible() or not rect(p,s.icon)
                or not style(p,self._selected and ACCENT or WHITE,1) then return false end
            local texture=p:texture_name()
            if texture~=self._icon_descriptor.texture and texture:key()~=Idstring(self._icon_descriptor.texture):key() then return false end
        elseif self._label:visible()~=true or (live(self._icon) and self._icon:visible()) then return false end
        return true
    end)
    return ok and result==true
end

function Row:destroy()
    remove(self._parent,self._root)
    self._root=nil;self._parent=nil
    self._label=nil;self._value=nil;self._track=nil;self._fill=nil
    self._cell_bg=nil;self._cell_cut=nil;self._cell_cut_size=nil
    self._cell_left_cut=nil;self._cell_left_size=nil
end

kyohud.hud.equipment_component=C
