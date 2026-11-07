kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end

kyohud.hud = kyohud.hud or {}

local P = kyohud.hud.player or {}
kyohud.hud.player = P

P._root = P._root
P._gauge = P._gauge
P._downs_text = P._downs_text
P._condition_text = P._condition_text

P._downs_label = P._downs_label
P._mounted = P._mounted or false
P._parent_panel = P._parent_panel
P._manager = P._manager
P._layout_cache = P._layout_cache
P._last_update_time = P._last_update_time
P._render_verified = P._render_verified or false
P._downs_icon = P._downs_icon
P._downs_icon_available = P._downs_icon_available

P._exp_downs_label_text = P._exp_downs_label_text
P._exp_downs_text = P._exp_downs_text
P._exp_condition_text = P._exp_condition_text

local PLAYER_ROOT_NAME = "kyohud_player_panel"
local GAUGE_NAME = "kyohud_player_gauge"
local DOWNS_NAME = "kyohud_player_downs"
local CONDITION_NAME = "kyohud_player_condition"

local DOWNS_LABEL_NAME = "kyohud_player_downs_label"
local DOWNS_ICON_NAME = "kyohud_player_downs_icon"
local HEART_TEXTURE_PATH = "guis/dlcs/chico/textures/pd2/specialization/icons_atlas"
local HEART_TEXTURE_CROP = {64, 0, 64, 64}
local REF_W = 300
-- Extend only the owned root to the left; the gauge keeps its world geometry.
local DOWNS_RESERVE = 80
local REF_H = 120
local BOTTOM_RESERVE = 200
local UPDATE_INTERVAL = 0.05

local CALL_OK = "ok"
local CALL_MISSING = "missing"
local CALL_ERROR = "error"

local function is_vr()
    return _G.IS_VR == true
end

local function panel_alive(p)
    if p == nil then return false end
    if type(alive) == "function" then
        local ok, a = pcall(alive, p)
        if ok then return a == true end
    end
    if type(p) == "table" and type(p.alive) == "function" then
        local ok, a = pcall(p.alive, p)
        if ok then return a == true end
    end
    return p ~= nil
end

local function safe_call(obj, method_name, ...)
    if obj == nil then return CALL_MISSING, nil end
    local ok_get, method_or_err = pcall(function() return obj[method_name] end)
    if not ok_get then return CALL_ERROR, nil end
    if type(method_or_err) ~= "function" then return CALL_MISSING, nil end
    local ok_call, result = pcall(method_or_err, obj, ...)
    if not ok_call then return CALL_ERROR, nil end
    return CALL_OK, result
end

local function is_finite(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    return true
end

local function loc_text(key)
    local ok, mgr = pcall(function() return managers.localization end)
    if ok and mgr and type(mgr.text) == "function" then
        local ok2, txt = pcall(mgr.text, mgr, key)
        if ok2 and type(txt) == "string" and txt ~= "" and txt ~= key then
            return txt
        end
    end
    return nil
end

local function check_texture_available(path)
    local ok, has = pcall(function()
        if not DB or type(DB.has) ~= "function" then
            return false
        end
        return DB:has(Idstring("texture"), Idstring(path))
    end)
    return ok and has == true
end

local function get_runtime_root()
    local rt = kyohud.hud.runtime
    if not rt or not rt._mounted then return nil end
    local root = rt._root_panel
    if not root or not panel_alive(root) then return nil end
    return root
end

function P:_compute_layout(parent_w, parent_h)
    if not is_finite(parent_w) or not is_finite(parent_h) then return nil end
    if parent_w <= 0 or parent_h <= 0 then return nil end
    local layout = kyohud.hud.layout
    if not layout or type(layout.resolve) ~= "function" then return nil end
    local scale = kyohud.settings.hud_scale or 1
    local geom = layout.resolve(parent_w, parent_h, scale)
    if not geom or not geom.valid then return nil end
    local us = geom.uniform_scale or 1
    local s = geom.scale or 1
    local eff = us * s
    local pw = (REF_W + DOWNS_RESERVE) * eff
    local ph = REF_H * eff
    local reserve = BOTTOM_RESERVE * us
    local margin = geom.margin_x or 0
    if pw <= 0 or ph <= 0 then return nil end
    if pw > geom.available_x or ph > geom.available_y then return nil end
    local x = parent_w - margin - pw
    local y = parent_h - margin - reserve - ph
    if x < margin then x = margin end
    if y < margin then y = margin end
    if x + pw > parent_w - margin then return nil end
    if y + ph > parent_h - margin then return nil end
    return {
        x = x, y = y, w = pw, h = ph,
        parent_w = parent_w, parent_h = parent_h,
    }
end

function P:_create_primitives()
    if not self._root or not panel_alive(self._root) then return end
    if not self._layout_cache then return end
    local gauge_mod = kyohud.hud.gauge
    if gauge_mod and type(gauge_mod.new) == "function" and not self._gauge then
        self._gauge = gauge_mod.new(self._root, GAUGE_NAME)
    end

    self._exp_downs_label_text = loc_text("ky_hud_player_downs") or "DOWNS"
    if not self._downs_bg then
        local ok,prim=pcall(function()
            return self._root:rect({name="kyohud_downs_bg",layer=0,color=Color(.03,.035,.043)})
        end)
        if ok then self._downs_bg=prim end
    end
    if not self._downs_icon then
        local available = check_texture_available(HEART_TEXTURE_PATH)
        self._downs_icon_available = available
        if available then
            local ok, prim = pcall(function()
                return self._root:bitmap({
                    name = DOWNS_ICON_NAME,
                    layer = 1,
                    texture = HEART_TEXTURE_PATH,
                    texture_rect = HEART_TEXTURE_CROP,
                })
            end)
            if ok and prim then
                self._downs_icon = prim
            end
        end
    end
    if not self._downs_label then
        local ok, prim = pcall(function()
            return self._root:text({
                name = DOWNS_LABEL_NAME,
                layer = 1,
                font = "fonts/font_medium_mf",
                text = self._exp_downs_label_text,
            })
        end)
        if ok and prim then self._downs_label = prim end
    end
    if not self._downs_text then
        local ok, prim = pcall(function()
            return self._root:text({
                name = DOWNS_NAME,
                layer = 1,
                align = "center",
                vertical = "center",
                font = "fonts/font_medium_mf",
                text = "",
            })
        end)
        if ok and prim then
            self._downs_text = prim
        end
    end
    if not self._condition_text then
        local ok, prim = pcall(function()
            return self._root:text({
                name = CONDITION_NAME,
                font = "fonts/font_medium_mf",
                text = "",
            })
        end)
        if ok and prim then
            self._condition_text = prim
        end
    end
end

local PLAYER_FONT = "fonts/font_medium_mf"

function P:_desired_layout()
    local lc = self._layout_cache
    if not lc then return nil end
    local w, h = lc.w, lc.h
    if not is_finite(w) or not is_finite(h) or w <= 0 or h <= 0 then return nil end
    local e = w / (REF_W + DOWNS_RESERVE)
    local gauge_w = REF_W * e
    local ge = (360 / 440) * e
    local box_h = 42 * ge
    local text_h = 24*ge
    local metrics = self._downs_metrics
    if metrics and metrics.primitive==self._downs_text and metrics.text==self._exp_downs_text
        and metrics.fs==24*ge then text_h=math.max(text_h,metrics.height) end
    local text_y = 22*e+16*ge-text_h/2
    return {
        root = { x = lc.x, y = lc.y, w = w, h = h },
        gauge = { x = DOWNS_RESERVE * e, y = 22 * e, w = gauge_w, h = box_h },
        gauge_scale = ge,
        downs_box = {x=14*e,y=22*e+3*ge,w=64*e,h=26*ge},
        downs_label = { x = 42*e, y = text_y, w = 32*e, h = text_h },
        downs_icon = { x = 24*e, y = 22*e+16*ge-8*e, w = 16*e, h = 16*e },
        downs_text = { x = 42*e, y = text_y, w = 32*e, h = text_h },
        condition_text = { x = DOWNS_RESERVE*e, y = 90 * e, w = gauge_w, h = 22 * e },
        font = PLAYER_FONT,

        downs_label_fs = 24*ge,
        downs_text_fs = 24*ge,
        condition_text_fs = 22*e,
    }
end

function P:_apply_layout()
    if not self._root or not panel_alive(self._root) then return end
    local dl = self:_desired_layout()
    if not dl then return end
    -- Retain the localized label primitive hidden for lifecycle compatibility.
    -- The visible badge contains only the native remaining-count number.
    self._downs_measure_valid = false
    if self._downs_text and panel_alive(self._downs_text) then
        local ok, measured = pcall(function()
            self._downs_text:set_font_size(dl.downs_text_fs)
            local _, _, width = self._downs_text:text_rect()
            return width
        end)
        if ok and is_finite(measured) and measured >= 0 then
            -- Fit is certified after the fresh snapshot has repaired the text.
            self._downs_measure_valid = true
        end
    end
    local lc = self._layout_cache
    safe_call(self._root, "set_shape", lc.x, lc.y, dl.root.w, dl.root.h)
    if panel_alive(self._downs_bg) then
        local r=dl.downs_box
        safe_call(self._downs_bg,"set_shape",r.x,r.y,r.w,r.h)
        safe_call(self._downs_bg,"set_color",Color(.03,.035,.043))
        safe_call(self._downs_bg,"set_alpha",.86)
        safe_call(self._downs_bg,"set_visible",false)
    end
    if self._downs_icon and panel_alive(self._downs_icon) and self._downs_icon_available then
        local r = dl.downs_icon
        safe_call(self._downs_icon, "set_shape", r.x, r.y, r.w, r.h)
        safe_call(self._downs_icon, "set_color", Color(159/255, 208/255, 94/255))
        safe_call(self._downs_icon, "set_alpha", 1)
        safe_call(self._downs_icon, "set_visible", true)
    end
    if self._gauge then
        self._gauge:set_geometry(dl.gauge.x, dl.gauge.y, dl.gauge.w, dl.gauge.h, dl.gauge_scale)
    end

    if self._downs_label and panel_alive(self._downs_label) then
        local r = dl.downs_label
        safe_call(self._downs_label, "set_shape", r.x, r.y, r.w, r.h)
        safe_call(self._downs_label, "set_font_size", math.max(1, dl.downs_label_fs))
        safe_call(self._downs_label, "set_text", self._exp_downs_label_text or "DOWNS")
        safe_call(self._downs_label,"set_color",Color(.75,.78,.81))
        safe_call(self._downs_label,"set_alpha",1)
        safe_call(self._downs_label,"set_visible",false)
    end
    if self._downs_text and panel_alive(self._downs_text) then
        local r = dl.downs_text
        safe_call(self._downs_text, "set_shape", r.x, r.y, r.w, r.h)
        safe_call(self._downs_text, "set_font_size", math.max(1, dl.downs_text_fs))
        safe_call(self._downs_text,"set_color",Color(1,1,1))
        safe_call(self._downs_text,"set_alpha",1)
    end
    if self._condition_text and panel_alive(self._condition_text) then
        local r = dl.condition_text
        safe_call(self._condition_text, "set_shape", r.x, r.y, r.w, r.h)
        safe_call(self._condition_text, "set_font_size", math.max(1, dl.condition_text_fs))
    end
end

function P:_resolve_downs_str(snapshot)
    local downs = snapshot and snapshot.downs
    if type(downs) == "number" and is_finite(downs) then
        return tostring(math.max(math.floor(downs), 0))
    end
    return "--"
end

function P:_resolve_condition_str(snapshot)
    local actors = kyohud.hud.actors
    local has_local = false
    if actors and actors._local_unit ~= nil then
        has_local = true
    end
    if not has_local then
        return loc_text("ky_hud_player_unknown_condition") or "UNKNOWN"
    end
    local ci = snapshot and snapshot.condition_icon
    local ct = snapshot and snapshot.condition_text
    if ci == "mugshot_normal" then
        return ""
    end
    if ct ~= nil and type(ct) == "string" and ct ~= "" then
        return ct
    end
    if ci ~= nil and type(ci) == "string" and ci ~= "" then
        return ci
    end
    return loc_text("ky_hud_player_unknown_condition") or "UNKNOWN"
end

-- A native font's line height is not necessarily its requested font size.
-- Measure the fresh count, retain its center, and keep the visible badge fixed.
function P:_fit_downs_text()
    self._downs_measure_valid=false
    local p=self._downs_text
    local dl=self:_desired_layout()
    if not dl or not panel_alive(p) then return end
    local fs=dl.downs_text_fs
    safe_call(p,"set_font_size",fs)
    local source=self._exp_downs_text
    local metrics=self._downs_metrics
    if not metrics or metrics.primitive~=p or metrics.text~=source or metrics.fs~=fs then
        local ok,w,h=pcall(function()
            local _,_,iw,ih=p:text_rect()
            return iw,ih
        end)
        if not ok or not is_finite(w) or not is_finite(h) or w<0 or h<0 or w>dl.downs_text.w+.5 then return end
        local height=math.max(fs,math.ceil(h))
        local center=dl.downs_text.y+dl.downs_text.h/2
        if center-height/2<0 or center+height/2>dl.root.h then return end
        self._downs_metrics={primitive=p,text=source,fs=fs,height=height}
        dl=self:_desired_layout()
    end
    local r=dl.downs_text
    safe_call(p,"set_shape",r.x,r.y,r.w,r.h)
    if panel_alive(self._downs_label) then
        local label=dl.downs_label
        safe_call(self._downs_label,"set_shape",label.x,label.y,label.w,label.h)
    end
    -- Setter failures and actual ink bounds are still checked by verify().
    self._downs_measure_valid=true
end

function P:render(snapshot, multiplier)
    if not self._root or not panel_alive(self._root) then return end
    local mode_num = kyohud.settings.player_value_mode or 1
    local mode = (mode_num == 2) and "real" or "percentage"
    local health = snapshot and snapshot.health or nil
    local armor = snapshot and snapshot.armor or nil
    if self._gauge then
        self._gauge:render(health, armor, mode, multiplier)
    end
    if self._downs_text and panel_alive(self._downs_text) then
        local downs_str = self:_resolve_downs_str(snapshot)
        safe_call(self._downs_text, "set_text", downs_str)
        self._exp_downs_text = downs_str
        self:_fit_downs_text()
    end
    if self._condition_text and panel_alive(self._condition_text) then
        local cond_str = self:_resolve_condition_str(snapshot)
        safe_call(self._condition_text, "set_text", cond_str)
        self._exp_condition_text = cond_str
    end
end

function P:verify()
    if self._downs_measure_valid ~= true then
        self._render_verified = false
        return false
    end
    if not self._root or not panel_alive(self._root) then
        self._render_verified = false
        return false
    end
    if not self._parent_panel or not panel_alive(self._parent_panel) then
        self._render_verified = false
        return false
    end
    local dl = self:_desired_layout()
    if not dl then
        self._render_verified = false
        return false
    end
    local function chk_geom(prim, desired)
        local s1, ax = safe_call(prim, "x")
        if s1 ~= CALL_OK or not is_finite(ax) then return false end
        local s2, ay = safe_call(prim, "y")
        if s2 ~= CALL_OK or not is_finite(ay) then return false end
        local s3, aw = safe_call(prim, "w")
        if s3 ~= CALL_OK or not is_finite(aw) then return false end
        local s4, ah = safe_call(prim, "h")
        if s4 ~= CALL_OK or not is_finite(ah) then return false end
        if math.abs(ax - desired.x) > 0.5 then return false end
        if math.abs(ay - desired.y) > 0.5 then return false end
        if math.abs(aw - desired.w) > 0.5 then return false end
        if math.abs(ah - desired.h) > 0.5 then return false end
        return true
    end
    local function chk_visible(prim)
        local s, v = safe_call(prim, "visible")
        if s ~= CALL_OK then return true end
        return v == true
    end
    local function chk_font_size(prim, size)
        local s, f = safe_call(prim, "font_size")
        return s == CALL_OK and is_finite(f) and math.abs(f - size) <= 0.01
    end
    local function chk_text(prim, expected)
        if expected == nil then return true end
        local s, t = safe_call(prim, "text")
        if s ~= CALL_OK then return false end
        return t == expected
    end
    if not chk_geom(self._root, dl.root) then
        self._render_verified = false
        return false
    end
    if not chk_visible(self._root) then
        self._render_verified = false
        return false
    end
    if not panel_alive(self._downs_bg) or not chk_geom(self._downs_bg,dl.downs_box) or chk_visible(self._downs_bg) then
        self._render_verified=false;return false
    end
    if self._downs_icon and self._downs_icon_available then
        if not panel_alive(self._downs_icon) or not chk_geom(self._downs_icon, dl.downs_icon) or not chk_visible(self._downs_icon) then
            self._render_verified=false;return false
        end
    end
    local style_ok,style_valid=pcall(function()
        local c=self._downs_bg:color()
        return math.abs(c.r-.03)<.001 and math.abs(c.g-.035)<.001 and math.abs(c.b-.043)<.001
            and math.abs(self._downs_bg:alpha()-.86)<.001
    end)
    if not style_ok or not style_valid then self._render_verified=false;return false end
    if not self._gauge then
        self._render_verified = false
        return false
    end
    local gauge_ok = self._gauge:verify()
    if not gauge_ok then
        self._render_verified = false
        return false
    end
    local text_checks = {

        { prim = self._downs_label, rect = dl.downs_label, exp_text = self._exp_downs_label_text, fs = dl.downs_label_fs },
        { prim = self._downs_text, rect = dl.downs_text, exp_text = self._exp_downs_text, fs = dl.downs_text_fs },
        { prim = self._condition_text, rect = dl.condition_text, exp_text = self._exp_condition_text, fs = dl.condition_text_fs },
    }
    for _, tc in ipairs(text_checks) do
        if not tc.prim or not panel_alive(tc.prim) then
            self._render_verified = false
            return false
        end
        if not chk_geom(tc.prim, tc.rect) then
            self._render_verified = false
            return false
        end
        local visible=chk_visible(tc.prim)
        if (tc.prim==self._downs_label and visible) or (tc.prim~=self._downs_label and not visible) then
            self._render_verified = false
            return false
        end
        if not chk_font_size(tc.prim, tc.fs) then
            self._render_verified = false
            return false
        end
        if not chk_text(tc.prim, tc.exp_text) then
            self._render_verified = false
            return false
        end
    end
    local fit_ok,fit=pcall(function()
        local _,_,w,h=self._downs_text:text_rect()
        return is_finite(w) and is_finite(h) and w>=0 and h>=0
            and w<=dl.downs_text.w+.5 and h<=dl.downs_text.h+.5
    end)
    if not fit_ok or not fit then self._render_verified=false;return false end
    self._render_verified = true
    return true
end

function P:_capture_and_render(mgr)
    local actors = kyohud.hud.actors
    if not actors or type(actors.refresh) ~= "function" then return end
    if type(actors.get_actor) ~= "function" then return end
    local slot = nil
    if type(HUDManager) == "table" then
        slot = HUDManager.PLAYER_PANEL
    end
    if not slot then return end
    actors:refresh(mgr or self._manager)
    local snapshot = actors:get_actor(slot)
    local mult = nil
    local ok_td, td = pcall(function() return tweak_data end)
    if ok_td and td then
        local ok_gui, gui = pcall(function() return td.gui end)
        if ok_gui and gui then
            local ok_mult, m = pcall(function() return gui.stats_present_multiplier end)
            if ok_mult and is_finite(m) then
                mult = m
            end
        end
    end
    self:render(snapshot, mult)
    -- The new snapshot can fail fitting or a setter after the pre-update
    -- certification succeeded. Do not expose that failed frame until next tick.
    if not self:verify() then
        safe_call(self._root, "set_visible", false)
    end
end

function P:_repair_and_certify(mgr)
    if not self._root or not panel_alive(self._root) then return false end
    safe_call(self._root, "set_visible", true)
    if self._layout_cache then
        self:_apply_layout()
        self:_capture_and_render(mgr or self._manager)
    end
    return self:verify()
end

function P:mount(manager)
    if kyohud.settings.enable_player ~= true then return end
    if kyohud.settings.enable_hud_foundation ~= true then return end
    if is_vr() then return end
    local mgr = manager or self._manager
    if not mgr then return end
    self._manager = mgr
    local parent = get_runtime_root()
    if not parent then return end
    if self._mounted and self._root and panel_alive(self._root) then
        if self._parent_panel == parent then
            return
        end
        self:unmount()
    end
    if self._root and not panel_alive(self._root) then
        self._root = nil
        self._gauge = nil
        self._downs_text = nil
        self._condition_text = nil
        self._downs_label = nil
        self._downs_icon = nil
        self._downs_icon_available = nil
    end
    local status, existing = safe_call(parent, "child", PLAYER_ROOT_NAME)
    if status == CALL_OK and existing ~= nil and panel_alive(existing) then
        if self._root == existing then
            self._mounted = true
            self._parent_panel = parent
            return
        end
        return
    end
    if status ~= CALL_OK then
        return
    end
    local create_status, root = safe_call(parent, "panel", {name = PLAYER_ROOT_NAME})
    if create_status ~= CALL_OK or root == nil then return end
    self._root = root
    self._parent_panel = parent
    self._mounted = true
    local pw_s, pw = safe_call(parent, "w")
    local ph_s, ph = safe_call(parent, "h")
    if pw_s == CALL_OK and ph_s == CALL_OK and is_finite(pw) and is_finite(ph) and pw > 0 and ph > 0 then
        self._layout_cache = self:_compute_layout(pw, ph)
    end
    if self._layout_cache then
        self:_create_primitives()
        self:_apply_layout()
        self:_capture_and_render(mgr)
        self:verify()
    end
end

function P:unmount()
    if not self._mounted and not self._root then return true end
    if self._gauge and type(self._gauge.destroy) == "function" then
        self._gauge:destroy()
    end
    self._gauge = nil
    if self._root then
        if panel_alive(self._root) then
            local parent = self._parent_panel
            if parent and panel_alive(parent) then
                safe_call(parent, "remove", self._root)
            end
        end
        self._root = nil
    end
    self._downs_text = nil
    self._condition_text = nil
    self._downs_label = nil
    self._downs_label_width = nil
    self._downs_bg = nil
    self._downs_icon = nil
    self._downs_icon_available = nil
    self._downs_metrics = nil
    self._downs_measure_valid = false
    self._parent_panel = nil
    self._mounted = false
    self._layout_cache = nil
    self._render_verified = false
    return true
end

function P:rebuild(manager)
    if self._mounted and self._root and panel_alive(self._root) then
        self:_capture_and_render(manager or self._manager)
        self:verify()
    else
        self:mount(manager)
    end
end

function P:refresh_settings(manager)
    if kyohud.settings.enable_player == true
       and kyohud.settings.enable_hud_foundation == true
       and not is_vr() then
        if not self._mounted or not self._root or not panel_alive(self._root) then
            self:mount(manager)
            return
        end
        local parent = self._parent_panel
        if parent and panel_alive(parent) then
            local pw_s, pw = safe_call(parent, "w")
            local ph_s, ph = safe_call(parent, "h")
            if pw_s == CALL_OK and ph_s == CALL_OK and is_finite(pw) and is_finite(ph) and pw > 0 and ph > 0 then
                self._layout_cache = self:_compute_layout(pw, ph)
            end
        end
        if self._layout_cache then
            self:_apply_layout()
            self:_capture_and_render(manager or self._manager)
            self:verify()
        end
    else
        if self._mounted or self._root then
            self:unmount()
        end
    end
end

function P:on_heist_start(manager)
    local actors = kyohud.hud.actors
    if actors and type(actors.on_heist_start) == "function" then
        actors:on_heist_start(manager or self._manager)
    end
end

function P:update(manager, t, dt)
    if not t then return end
    if kyohud.settings.enable_player ~= true
       or kyohud.settings.enable_hud_foundation ~= true
       or is_vr() then
        if self._mounted or self._root then
            self:unmount()
        end
        return
    end
    if self._mounted and self._root and not panel_alive(self._root) then
        self._root = nil
        self._gauge = nil
        self._downs_text = nil
        self._condition_text = nil
        self._downs_label = nil
        self._downs_icon = nil
        self._downs_icon_available = nil
        self._mounted = false
        self._layout_cache = nil
        self._render_verified = false
    end
    if not self._mounted then
        self:mount(manager or self._manager)
    end
    if not self._mounted or not self._root then return end
    if self._last_update_time ~= nil and (t - self._last_update_time) < UPDATE_INTERVAL then
        return
    end
    self._last_update_time = t
    if not self:verify() then
        if self._root and panel_alive(self._root) then
            safe_call(self._root, "set_visible", false)
        end
        local repaired = self:_repair_and_certify(manager or self._manager)
        if repaired then
            safe_call(self._root, "set_visible", true)
            return
        end
        -- A recoverable no-op/throwing setter is not a reason to discard all
        -- live primitives. Keep the owned block hidden and retry next update.
        local lost = not self._gauge or self._gauge._primitive_lost == true
        for _, key in ipairs({"_downs_label", "_downs_text", "_condition_text", "_downs_bg"}) do
            if not panel_alive(self[key]) then lost = true end
        end
        if self._downs_icon_available and not panel_alive(self._downs_icon) then
            lost = true
        end
        if lost then
            self:unmount()
            self:mount(manager or self._manager)
        elseif self._root and panel_alive(self._root) then
            safe_call(self._root, "set_visible", false)
        end
        return
    end
    self:_capture_and_render(manager or self._manager)
end

function P:destroy(manager)
    if manager and self._manager and manager ~= self._manager then
        return
    end
    self:unmount()
end
