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
local ORANGE = Color(1, 0.63, 0.12)
local REVEAL_NAME = "recharge_reveal"
local REVEAL_ALPHA = .4
local FLASH_NAME = "grenade_flash"
local FLASH_LAYER = 3

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
local function clamp(v, lo, hi)
    if v < lo then return lo end
    if v > hi then return hi end
    return v
end
local function style(p,color,alpha)
    local c=p:color()
    local function s(a,b) return finite(a) and finite(b) and math.abs(a-b) <= 0.005 end
    return c and s(c.r,color.r) and s(c.g,color.g) and s(c.b,color.b) and s(p:alpha(),alpha)
end
local function set_static(v,x,y,z)
    local fn=mvector3 and mvector3.set_static
    if type(fn)~="function" then
        error("mvector3.set_static unavailable")
    end
    fn(v,x,y,z)
    return true
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
        self._value = self._root:text({name="value",font=FONT,layer=2,text="",align="center"})
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
    if self._tile then return self:_render_cell(label,value,progress,selected,icon) end
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
        if type(self._value.set_align)=="function" then self._value:set_align("center") end
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
        if type(self._value.align)=="function" and self._value:align()~="center" then return false end
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
    local both=self._cell_both==true
    local progress=self._progress
    local icon_w=icon and icon.rect[3] or nil
    local icon_h=icon and icon.rect[4] or nil
    local cached=self._cell_shapes_cache
    if cached and cached.w==g.w and cached.h==g.h and cached.e==e and cached.both==both
        and cached.value_w==self._cell_value_w and cached.progress==progress
        and cached.icon==(icon~=nil) and cached.icon_w==icon_w and cached.icon_h==icon_h then
        return cached.shapes
    end
    local left=both and 8*e or 0
    local body_w=g.w-8*e-left
    local center=both and g.w/2 or (g.w-4*e)/2
    local iw,ih=0,0
    if icon then
        local k=math.min(34*e/icon.rect[3],29*e/icon.rect[4],body_w/icon.rect[3])
        iw,ih=icon.rect[3]*k,icon.rect[4]*k
    end
    local image_h=icon and ih or 29*e
    local top=(g.h-image_h-4*e-24*e)/2
    local value_w=progress~=nil and body_w or math.min(body_w,self._cell_value_w or body_w)
    local track_h=math.max(1,2*e)
    local track_y=g.h-3*e
    local shapes={label={center-body_w/2,top,body_w,29*e},value={center-value_w/2,top+image_h+4*e,value_w,24*e},
        icon={center-iw/2,top,iw,ih},background={left,0,body_w,g.h},cut={g.w-8*e,0,8*e,g.h},left={0,0,8*e,g.h},
        track={left,track_y,body_w,track_h},fill={left,track_y,body_w*(progress or 0),track_h}}
    self._cell_shapes_cache={w=g.w,h=g.h,e=e,both=both,value_w=self._cell_value_w,
        progress=progress,icon=icon~=nil,icon_w=icon_w,icon_h=icon_h,shapes=shapes}
    return shapes
end

function Row:_reveal_vectors(key,count)
    local store=self._reveal_vectors_cache
    if not store then store={};self._reveal_vectors_cache=store end
    local vectors=store[key]
    if not vectors then
        vectors={}
        for i=1,count do
            local v=Vector3()
            set_static(v,0,0,0)
            vectors[i]=v
        end
        store[key]=vectors
    end
    return vectors
end

-- Bottom-up fill clipped analytically. The owned reveal is only a window at
-- global y=H*(1-p); every child bbox and mesh stays inside its local 0..fillH
-- box, so nothing depends on parent clipping. Meshes are persistent and are
-- rewritten in place only when their inputs change.
function Row:_sync_reveal(s,p,repair_style)
    if repair_style==nil then repair_style=true end
    local reveal=self._recharge_reveal
    local g=self._geometry
    if not live(reveal) or not g then return false end
    p=math.min(1,math.max(0,p or 0))
    local both=self._cell_both==true
    local need_left=both and s.left[3]>0 and s.left[4]>0
    local fill_h=g.h*p
    local left_w=s.left[3]
    local cut_full=s.cut[3]
    local cut_w=cut_full*p
    local body=s.background
    local paint
    if repair_style then
        paint=function(prim)
            prim:set_color(ORANGE);prim:set_alpha(REVEAL_ALPHA);prim:set_layer(1)
        end
    end
    if not (live(self._reveal_bg) and live(self._reveal_cut)
        and ((need_left and live(self._reveal_left)) or (not need_left and not live(self._reveal_left)))
        and self._reveal_w==g.w and self._reveal_h==g.h
        and self._reveal_e==self._tile and self._reveal_both==both) then
        remove(reveal,self._reveal_bg);remove(reveal,self._reveal_left);remove(reveal,self._reveal_cut)
        self._reveal_bg=nil;self._reveal_left=nil;self._reveal_cut=nil
        self._reveal_bg=reveal:rect({name="reveal_background",layer=1,color=ORANGE})
        if need_left then
            self._reveal_left=reveal:polygon({name="reveal_left",layer=1,x=0,y=0,w=left_w,h=0,
                triangles=self:_reveal_vectors("left",6),color=ORANGE})
        end
        self._reveal_cut=reveal:polygon({name="reveal_cut",layer=1,x=s.cut[1],y=0,w=0,h=0,
            triangles=self:_reveal_vectors("cut",3),color=ORANGE})
        self._reveal_w=g.w;self._reveal_h=g.h;self._reveal_e=self._tile;self._reveal_both=both
        self._reveal_mesh_p=nil;self._reveal_mesh_left=nil
        self._reveal_mesh_cut=nil;self._reveal_mesh_h=nil
        self._reveal_shown=nil
    end
    shape(self._reveal_bg,body[1],0,body[3],fill_h)
    if need_left then shape(self._reveal_left,0,0,left_w,fill_h) end
    shape(self._reveal_cut,s.cut[1],0,cut_w,fill_h)
    if self._reveal_mesh_p~=p or self._reveal_mesh_left~=left_w
        or self._reveal_mesh_cut~=cut_full or self._reveal_mesh_h~=fill_h then
        if need_left then
            local v=self:_reveal_vectors("left",6)
            set_static(v[1],left_w*p,0,0);set_static(v[2],left_w,0,0);set_static(v[3],left_w,fill_h,0)
            set_static(v[4],left_w*p,0,0);set_static(v[5],left_w,fill_h,0);set_static(v[6],0,fill_h,0)
            self._reveal_left:clear()
            self._reveal_left:add_triangles(v)
        end
        local v=self:_reveal_vectors("cut",3)
        set_static(v[1],0,0,0);set_static(v[2],cut_w,0,0);set_static(v[3],0,fill_h,0)
        self._reveal_cut:clear()
        self._reveal_cut:add_triangles(v)
        self._reveal_mesh_p=p;self._reveal_mesh_left=left_w
        self._reveal_mesh_cut=cut_full;self._reveal_mesh_h=fill_h
    end
    local shown=p>0
    if repair_style then
        paint(self._reveal_bg);paint(self._reveal_cut)
        if need_left then paint(self._reveal_left) end
        reveal:set_alpha(1);reveal:set_layer(1)
    end
    if repair_style or self._reveal_shown~=shown then
        self._reveal_bg:set_visible(shown)
        self._reveal_cut:set_visible(shown)
        if need_left then self._reveal_left:set_visible(shown) end
        self._reveal_shown=shown
    end
    return true
end

function Row:_render_cell(label,value,progress,selected,icon)
    if not self:_live() or not self._geometry then return end
    self._progress=finite(progress) and math.min(1,math.max(0,progress)) or nil
    self._selected=selected==true
    self._icon_descriptor=icon
    local ok=pcall(function()
        local g=self._geometry
        shape(self._root,g.x,g.y,g.w,g.h)
        if not live(self._cell_bg) then
            self._cell_bg=self._root:rect({name="cell_background",layer=0,color=WHITE})
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
                triangles={Vector3(0,0,0),Vector3(s.cut[3],0,0),Vector3(0,s.cut[4],0)},color=WHITE})
            self._cell_cut_size={w=s.cut[3],h=s.cut[4]}
        end
        shape(self._cell_bg,unpack(s.background));shape(self._cell_cut,unpack(s.cut))
        local ls=self._cell_left_size
        if self._cell_both then
            if not live(self._cell_left_cut) or not ls or ls.w~=s.left[3] or ls.h~=s.left[4] then
                remove(self._root,self._cell_left_cut)
                local w,h=s.left[3],s.left[4]
                self._cell_left_cut=self._root:polygon({name="cell_left_cut",layer=0,x=0,y=0,w=w,h=h,
                    triangles={Vector3(w,0,0),Vector3(w,h,0),Vector3(0,h,0)},color=WHITE})
                self._cell_left_size={w=w,h=h}
            end
            shape(self._cell_left_cut,unpack(s.left))
            self._cell_left_cut:set_color(WHITE);self._cell_left_cut:set_alpha(.05);self._cell_left_cut:set_visible(true)
        elseif self._cell_left_cut then
            remove(self._root,self._cell_left_cut);self._cell_left_cut=nil;self._cell_left_size=nil
        end
        for _,p in ipairs({self._cell_bg,self._cell_cut}) do
            p:set_color(WHITE);p:set_alpha(.05);p:set_visible(true)
        end
        if self._progress~=nil then
            if not live(self._recharge_reveal) then
                self._recharge_reveal=self._root:panel({name=REVEAL_NAME,layer=1})
            end
            shape(self._recharge_reveal,0,g.h*(1-self._progress),g.w,g.h*self._progress)
            self:_sync_reveal(s,self._progress)
            self._recharge_reveal:set_visible(true)
        elseif live(self._recharge_reveal) then
            self._recharge_reveal:set_visible(false)
        end
        shape(self._label,unpack(s.label));shape(self._value,unpack(s.value))
        self._expected_label=self:_fit(self._label,"label",label or "",12*self._tile)
        self._expected_value=self:_fit(self._value,"value",value or "--",20*self._tile)
        self._label:set_visible(icon==nil)
        self._label:set_color(self._selected and ACCENT or DIM);self._label:set_alpha(1)
        if type(self._value.set_align)=="function" then self._value:set_align("center") end
        self._value:set_visible(true);self._value:set_color(WHITE);self._value:set_alpha(1)
        if live(self._icon) then
            if icon then
                self._icon:set_image(icon.texture,unpack(icon.rect))
                shape(self._icon,unpack(s.icon))
                self._icon:set_color(self._selected and ACCENT or WHITE);self._icon:set_alpha(1)
            end
            self._icon:set_visible(icon~=nil)
        end
        shape(self._track,unpack(s.track));shape(self._fill,unpack(s.fill))
        self._track:set_color(DIM);self._track:set_alpha(.2)
        self._fill:set_color(ACCENT);self._fill:set_alpha(1)
        self._track:set_visible(false);self._fill:set_visible(false)
        self._root:set_visible(true)
    end)
    self._verified=ok and self:verify()
end

-- Owned pulse mirror. The source alpha/scale belong to the consumer; this pure
-- row only places a distinct bitmap over the equipped icon and certifies it.
function Row:render_grenade_flash(alpha, scale)
    if not self:_live() or not self._geometry or not self._tile then return false end
    if not finite(alpha) or alpha < 0 or alpha > 1 then return false end
    local icon = self._icon_descriptor
    if type(icon) ~= "table" or type(icon.texture) ~= "string" or type(icon.rect) ~= "table" then
        return self:_hide_grenade_flash()
    end
    local s = self:_cell_shapes(icon)
    local base = s.icon
    if not base or base[3] <= 0 or base[4] <= 0 then return self:_hide_grenade_flash() end
    local k = finite(scale) and clamp(scale * .5, .5, 1) or 1
    local w, h = base[3] * k, base[4] * k
    if w <= 0 or h <= 0 then return self:_hide_grenade_flash() end
    local x = base[1] + (base[3] - w) * .5
    local y = base[2] + (base[4] - h) * .5
    local ok = pcall(function()
        if not live(self._grenade_flash) then
            self._grenade_flash = self._root:bitmap({name=FLASH_NAME, layer=FLASH_LAYER})
        end
        local flash = self._grenade_flash
        flash:set_shape(x, y, w, h)
        flash:set_image(icon.texture, unpack(icon.rect))
        flash:set_color(WHITE)
        flash:set_alpha(alpha)
        flash:set_layer(FLASH_LAYER)
        flash:set_visible(true)
    end)
    if not ok then
        self._flash_active = false
        return false
    end
    self._flash_texture = icon.texture
    self._flash_rect = {icon.rect[1], icon.rect[2], icon.rect[3], icon.rect[4]}
    self._flash_shape = {x, y, w, h}
    self._flash_alpha = alpha
    self._flash_active = true
    return true
end

function Row:_hide_grenade_flash()
    self._flash_active = false
    local flash = self._grenade_flash
    if live(flash) then
        pcall(function() flash:set_visible(false) end)
    end
    return true
end

function Row:_verify_grenade_flash()
    local flash = self._grenade_flash
    if not self._flash_active then
        if live(flash) then
            local ok, visible = pcall(function() return flash:visible() end)
            return ok and visible == false
        end
        return true
    end
    if not live(flash) or not self._root then return false end
    local ok, result = pcall(function()
        if flash:parent() ~= self._root then return false end
        if self._root:child(FLASH_NAME) ~= flash then return false end
        local shape = self._flash_shape
        if type(shape) ~= "table" or #shape ~= 4 then return false end
        if not near(flash:x(), shape[1]) or not near(flash:y(), shape[2])
            or not near(flash:w(), shape[3]) or not near(flash:h(), shape[4]) then return false end
        local ok_v, visible = pcall(function() return flash:visible() end)
        if not ok_v or visible ~= true then return false end
        local ok_a, alpha = pcall(function() return flash:alpha() end)
        if not ok_a or not finite(alpha) or math.abs(alpha - self._flash_alpha) > .005 then return false end
        local ok_c, color = pcall(function() return flash:color() end)
        if not ok_c or not color then return false end
        if not finite(color.r) or math.abs(color.r - 1) > .001
            or not finite(color.g) or math.abs(color.g - 1) > .001
            or not finite(color.b) or math.abs(color.b - 1) > .001 then return false end
        local ok_l, layer = pcall(function() return flash:layer() end)
        if not ok_l or not finite(layer) or layer ~= FLASH_LAYER then return false end
        local ok_t, texture = pcall(function() return flash:texture_name() end)
        if not ok_t then return false end
        local expected = self._flash_texture
        if texture ~= expected then
            local ok_id, desired = pcall(Idstring, expected)
            if not ok_id or not desired then return false end
            local ok_key, key = pcall(function() return texture:key() end)
            local ok_want, want = pcall(function() return desired:key() end)
            if not ok_key or not ok_want or key ~= want then return false end
        end
        local rect = self._flash_rect
        if type(rect) ~= "table" or #rect ~= 4 then return false end
        local getter = flash.texture_rect
        if type(getter) == "function" then
            local ok_r, rx, ry, rw, rh = pcall(getter, flash)
            if not ok_r or not finite(rx) or not finite(ry)
                or not finite(rw) or not finite(rh) then return false end
            if not near(rx, rect[1]) or not near(ry, rect[2])
                or not near(rw, rect[3]) or not near(rh, rect[4]) then return false end
        end
        -- Native Bitmap exposes no texture_rect getter, so the atlas crop cannot be
        -- read back or certified here. The crop remains bound by the set_image
        -- producer in render_grenade_flash; the verifier never rewrites it and
        -- certifies only texture_name plus actual geometry/style/parent/visibility.
        return true
    end)
    return ok and result == true
end

function Row:animate_recharge(value,progress)
    if not self._tile or not finite(progress) then return false end
    local g=self._geometry
    if not g or self._progress==nil or not self._expected_value then return false end
    local reveal=self._recharge_reveal
    if not live(reveal) or not live(self._value) then return false end
    if not self:_verify_cell() then return false end
    progress=math.min(1,math.max(0,progress))
    local text=value or "--"
    local ok=pcall(function()
        self._progress=progress
        local s=self:_cell_shapes(self._icon_descriptor)
        shape(reveal,0,g.h*(1-progress),g.w,g.h*progress)
        self:_sync_reveal(s,progress,false)
        local expected=self._expected_value
        if not expected or expected.source~=text then
            self._expected_value=self:_fit(self._value,"value",text,20*self._tile)
        end
        reveal:set_visible(true)
    end)
    if not ok then return false end
    return self:_verify_cell()
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
                or not rect(self._cell_left_cut,s.left) or not style(self._cell_left_cut,WHITE,.05) then return false end
        elseif live(self._cell_left_cut) then return false end
        if not live(self._cell_bg) or not live(self._cell_cut)
            or not self._cell_bg:visible() or not self._cell_cut:visible()
            or not rect(self._cell_bg,s.background) or not rect(self._cell_cut,s.cut)
            or not style(self._cell_bg,WHITE,.05)
            or not style(self._cell_cut,WHITE,.05) then return false end
        if not self._root:visible() or not rect(self._root,{g.x,g.y,g.w,g.h})
            or not rect(self._label,s.label) or not rect(self._value,s.value) then return false end
        for _,pair in ipairs({{self._label,self._expected_label},{self._value,self._expected_value}}) do
            local p,v=pair[1],pair[2]
            if not v or p:text()~=v.text or not near(p:font_size(),v.size) then return false end
            local w,h=measure(p)
            if not w or w>p:w()+.5 or h>p:h()+.5 then return false end
        end
        if not self._value:visible() or not style(self._value,WHITE,1) then return false end
        if type(self._value.align)~="function" or self._value:align()~="center" then return false end
        if self._track:visible() or self._fill:visible() then return false end
        if self._progress~=nil then
            local progress=self._progress
            local fill_h=g.h*progress
            local shown=progress>0
            local rv=self._recharge_reveal
            if not live(rv) or rv:parent()~=self._root then return false end
            if rv:layer()~=1 or not rv:visible() then return false end
            local ra=rv:alpha()
            if not finite(ra) or math.abs(ra-1)>.005 then return false end
            if not near(rv:x(),0) or not near(rv:y(),g.h*(1-progress))
                or not near(rv:w(),g.w) or not near(rv:h(),fill_h) then return false end
            local need_left=self._cell_both==true and s.left[3]>0 and s.left[4]>0
            local body={s.background[1],0,s.background[3],fill_h}
            local cut={s.cut[1],0,s.cut[3]*progress,fill_h}
            local left={0,0,s.left[3],fill_h}
            local known={}
            local function check(p,name,r)
                if not live(p) or p:parent()~=rv or p:name()~=name then return false end
                if not rect(p,r) or not style(p,ORANGE,REVEAL_ALPHA) then return false end
                if p:visible()~=shown or p:layer()~=1 then return false end
                known[p]=true
                return true
            end
            if not check(self._reveal_bg,"reveal_background",body) then return false end
            if not check(self._reveal_cut,"reveal_cut",cut) then return false end
            if need_left then
                if not check(self._reveal_left,"reveal_left",left) then return false end
            elseif live(self._reveal_left) then
                return false
            end
            local count=0
            local seen={}
            for _,child in pairs(rv:children()) do
                count=count+1
                if seen[child] or not known[child] then return false end
                seen[child]=true
            end
            local expected_count=2
            if need_left then expected_count=3 end
            if count~=expected_count then return false end
        elseif live(self._recharge_reveal) and self._recharge_reveal:visible() then
            return false
        end
        if self._icon_descriptor then
            local p=self._icon
            if not live(p) or not p:visible() or self._label:visible() or not rect(p,s.icon)
                or not style(p,self._selected and ACCENT or WHITE,1) then return false end
            local texture=p:texture_name()
            if texture~=self._icon_descriptor.texture and texture:key()~=Idstring(self._icon_descriptor.texture):key() then return false end
        elseif self._label:visible()~=true or (live(self._icon) and self._icon:visible()) then return false end
        if not self:_verify_grenade_flash() then return false end
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
    self._recharge_reveal=nil
    self._reveal_bg=nil;self._reveal_left=nil;self._reveal_cut=nil
    self._reveal_w=nil;self._reveal_h=nil;self._reveal_e=nil;self._reveal_both=nil
    self._reveal_vectors_cache=nil
    self._reveal_mesh_p=nil;self._reveal_mesh_left=nil
    self._reveal_mesh_cut=nil;self._reveal_mesh_h=nil
    self._reveal_shown=nil
    self._cell_shapes_cache=nil
    self._grenade_flash=nil
    self._flash_texture=nil;self._flash_rect=nil
    self._flash_shape=nil;self._flash_alpha=nil;self._flash_active=nil
end

kyohud.hud.equipment_component=C
