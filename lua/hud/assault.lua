kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end

kyohud.hud = kyohud.hud or {}

local A = kyohud.hud.assault or {}
kyohud.hud.assault = A

A._state = A._state or {}
local S = A._state
if S.active == nil then S.active = false end
if S.endless == nil then S.endless = false end

A._native_mode = A._native_mode

local REQUIRED_CONTEXT = "lib/managers/hudmanagerpd2"

local function is_finite_nonneg(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    if v < 0 then return false end
    return true
end

kyohud.hud._installed_hooks = kyohud.hud._installed_hooks or {}

function A:snapshot(manager)
    local previous_source = self._source
    local first_mount_with_events = (previous_source == nil) and (self._event_manager == self._manager)

    local ok_state, state = pcall(function()
        return managers.groupai:state()
    end)

    if not ok_state or not state then
        if not first_mount_with_events then
            self._event_manager = nil
            self._event_has_active = false
            self._event_has_endless = false
            self._event_has_number = false
            self._event_has_hostages = false
            self._state.active = false
            self._state.endless = false
            self._state.number = nil
            self._state.hostages = nil
            self._state.converted = nil
        else
            if not self._event_has_active then self._state.active = false end
            if not self._event_has_endless then self._state.endless = false end
            if not self._event_has_number then self._state.number = nil end
            if not self._event_has_hostages then self._state.hostages = nil end
            self._state.converted = nil
        end
        self._source = nil
        self:_apply_event_provenance()
        return
    end

    if previous_source ~= nil and previous_source ~= state then
        self._event_manager = nil
        self._event_has_active = false
        self._event_has_endless = false
        self._event_has_number = false
        self._event_has_hostages = false
    end

    self._source = state

    local ok1, v1 = pcall(function() return state:get_assault_mode() end)
    self._state.active = (ok1 and v1 == true)

    local ok2, v2 = pcall(function() return state:get_hunt_mode() end)
    self._state.endless = (ok2 and v2 == true)

    local ok3, v3 = pcall(function() return state:get_assault_number() end)
    if ok3 and is_finite_nonneg(v3) then
        self._state.number = v3
    else
        self._state.number = nil
    end

    local ok4, hc = pcall(function() return state:hostage_count() end)
    if ok4 and is_finite_nonneg(hc) then
        self._state.hostages = hc
    else
        self._state.hostages = nil
    end

    local ok5, registry = pcall(function() return state:all_converted_enemies() end)
    if ok5 and type(registry) == "table" then
        local count = 0
        local all_ok = true
        for _, unit in pairs(registry) do
            local ok_alive, is_alive = pcall(function() return alive(unit) end)
            if not ok_alive or type(is_alive) ~= "boolean" then all_ok = false; break end
            if is_alive then
                local ok_cd, cd = pcall(function() return unit:character_damage() end)
                if not ok_cd or (type(cd) ~= "table" and type(cd) ~= "userdata") then
                    all_ok = false
                    break
                end
                local ok_dead, is_dead = pcall(function() return cd:dead() end)
                if not ok_dead or (is_dead ~= nil and is_dead ~= false and is_dead ~= true) then
                    all_ok = false
                    break
                end
                if is_dead ~= true then
                    count = count + 1
                end
            end
        end
        if all_ok then
            self._state.converted = count
        else
            self._state.converted = nil
        end
    else
        self._state.converted = nil
    end

    self:_apply_event_provenance()
end

function A:_apply_event_provenance()
    if self._event_manager ~= self._manager then return end
    if self._event_has_active then
        self._state.active = self._event_active == true
    end
    if self._event_has_endless then
        self._state.endless = self._event_endless == true
    end
    if self._event_has_number then
        self._state.number = self._event_number
    end
    if self._event_has_hostages then
        self._state.hostages = self._event_hostages
    end
end

A._mounted = A._mounted or false
A._root_panel = A._root_panel
A._parent_panel = A._parent_panel
A._manager = A._manager
A._bg_rect = A._bg_rect
A._ticker_panel = A._ticker_panel
A._ticker_a = A._ticker_a
A._ticker_b = A._ticker_b
A._glyph_prim = A._glyph_prim
A._hostages_prim = A._hostages_prim
A._converted_prim = A._converted_prim
A._layout_cache = A._layout_cache
A._render_verified = A._render_verified or false
A._render_failed = A._render_failed or false
A._ticker_x_a = A._ticker_x_a or 0
A._ticker_x_b = A._ticker_x_b or 0
A._ticker_measured_w = A._ticker_measured_w or 0
A._ticker_gap = A._ticker_gap
A._last_counter_time = A._last_counter_time
A._snapshot_taken = A._snapshot_taken or false
A._cached_ticker_text = A._cached_ticker_text
A._cached_glyph_text = A._cached_glyph_text
A._cached_hostages_text = A._cached_hostages_text
A._cached_converted_text = A._cached_converted_text
A._cached_font = A._cached_font
A._cached_font_size = A._cached_font_size
A._cached_bg_key = A._cached_bg_key
A._cached_text_color_key = A._cached_text_color_key

A._native_corner = A._native_corner
A._native_hud_panel = A._native_hud_panel
A._native_targets = A._native_targets
A._native_acquired = A._native_acquired or false
A._native_generation = A._native_generation or 0
A._native_requests = A._native_requests
A._conflict_corner = A._conflict_corner

A._event_manager = A._event_manager
A._event_active = A._event_active
A._event_endless = A._event_endless
A._event_number = A._event_number
A._event_hostages = A._event_hostages
A._event_has_active = A._event_has_active or false
A._event_has_number = A._event_has_number or false
A._event_has_endless = A._event_has_endless or false
A._event_has_hostages = A._event_has_hostages or false
A._data_dirty = A._data_dirty or false
A._heist_manager_id = A._heist_manager_id

local ASSAULT_ROOT_NAME = "kyohud_assault_panel"
local BG_RECT_NAME = "kyohud_assault_bg"
local TICKER_PANEL_NAME = "kyohud_assault_ticker"
local TICKER_A_NAME = "kyohud_assault_ticker_a"
local TICKER_B_NAME = "kyohud_assault_ticker_b"
local GLYPH_NAME = "kyohud_assault_glyph"
local HOSTAGES_NAME = "kyohud_assault_hostages"
local CONVERTED_NAME = "kyohud_assault_converted"

local REF_MARGIN_RIGHT = 40
local REF_TOP = 36
local REF_WIDTH = 380
local REF_HEIGHT = 76
local REF_TICKER_W = 340
local REF_TICKER_H = 40
local REF_FONT_SIZE = 20
local MIN_FONT_SIZE = 12
local REF_TICKER_SPEED = 60
local REF_TICKER_GAP = 40
local COUNTER_INTERVAL = 0.5

local function a_panel_alive(p)
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

local a_call_ok = "ok"
local a_call_missing = "missing"
local a_call_error = "error"

local function a_safe_call(obj, method_name, ...)
    if obj == nil then return a_call_missing, nil end
    local ok_get, method_or_err = pcall(function() return obj[method_name] end)
    if not ok_get then return a_call_error, nil end
    if type(method_or_err) ~= "function" then return a_call_missing, nil end
    local ok_call, result = pcall(method_or_err, obj, ...)
    if not ok_call then return a_call_error, nil end
    return a_call_ok, result
end

local function a_is_finite(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    return true
end

local function a_is_vr()
    return _G.IS_VR == true
end

local function a_get_runtime_root()
    local rt = kyohud.hud.runtime
    if not rt then return nil end
    if not rt._mounted then return nil end
    local root = rt._root_panel
    if not root or not a_panel_alive(root) then return nil end
    return root
end

function A:_get_font()
    local ok_td, td = pcall(function() return tweak_data end)
    if ok_td and td then
        local ok_hud, hud = pcall(function() return td.hud end)
        if ok_hud and hud then
            local ok_font, f = pcall(function() return hud.medium_font_noshadow end)
            if ok_font and type(f) == "string" and f ~= "" then return f end
        end
    end
    return "fonts/font_medium_mf"
end

function A:_compute_layout(parent_w, parent_h)
    if not a_is_finite(parent_w) or not a_is_finite(parent_h) then return nil end
    if parent_w <= 0 or parent_h <= 0 then return nil end
    local layout = kyohud.hud.layout
    if not layout or type(layout.resolve) ~= "function" then return nil end
    local scale = kyohud.settings.hud_scale or 1
    local geom = layout.resolve(parent_w, parent_h, scale)
    if not geom or not geom.valid then return nil end
    local us = geom.uniform_scale or 1
    local s = geom.scale or 1
    local es = us * s
    local root_w = REF_WIDTH * es
    local root_h = REF_HEIGHT * es
    local margin_right = REF_MARGIN_RIGHT * es
    local top = REF_TOP * es
    local root_x = parent_w - margin_right - root_w
    local root_y = top
    if root_x < 0 or root_y < 0 then return nil end
    if root_x + root_w > parent_w or root_y + root_h > parent_h then return nil end
    if type(layout.objectives_region) == "function" then
        local obj = layout.objectives_region(parent_w, parent_h)
        if obj and root_x < obj.w and root_y < obj.h then return nil end
    end
    local ticker_w = REF_TICKER_W * es
    local ticker_h = REF_TICKER_H * es
    local glyph_w = root_w - ticker_w
    if glyph_w < 0 then glyph_w = 0 end
    local counts_h = root_h - ticker_h
    if counts_h < 0 then counts_h = 0 end
    local font_size = math.max(MIN_FONT_SIZE, math.floor(REF_FONT_SIZE * es))
    return {
        es = es,
        root_x = root_x, root_y = root_y,
        root_w = root_w, root_h = root_h,
        font_size = font_size,
        ticker = { x = 0, y = 0, w = ticker_w, h = ticker_h },
        glyph = { x = ticker_w, y = 0, w = glyph_w, h = ticker_h },
        hostages = { x = 0, y = ticker_h, w = root_w * 0.5, h = counts_h },
        converted = { x = root_w * 0.5, y = ticker_h, w = root_w * 0.5, h = counts_h },
    }
end

function A:_resolve_difficulty_text()
    local ok_job, job = pcall(function() return managers.job end)
    local stars_available = false
    local stars = 0
    if ok_job and job then
        local ok_s, s = pcall(function() return job:current_difficulty_stars() end)
        if ok_s and type(s) == "number" and is_finite_nonneg(s) then
            stars = math.floor(s)
            stars_available = true
        end
    end
    local skull
    local ok_loc, loc = pcall(function() return managers.localization end)
    if ok_loc and loc then
        local ok_m, m = pcall(function() return loc:get_default_macro("BTN_SKULL") end)
        if ok_m and type(m) == "string" and m ~= "" then skull = m end
    end
    local diff_text
    if not stars_available then
        diff_text = "--"
    elseif stars == 0 then
        diff_text = ""
    elseif skull then
        diff_text = string.rep(skull, stars)
    else
        diff_text = tostring(stars)
    end
    local ok_cs, cs = pcall(function() return managers.crime_spree end)
    if ok_cs and cs then
        local ok_active, active = pcall(function() return cs:is_active() end)
        if ok_active and active == true then
            local ok_level, level = pcall(function() return cs:server_spree_level() end)
            if ok_level and type(level) == "number" and is_finite_nonneg(level) then
                local cs_level = math.floor(level)
                if diff_text ~= "" then
                    diff_text = diff_text .. " [" .. cs_level .. "]"
                else
                    diff_text = "[" .. cs_level .. "]"
                end
            end
        end
    end
    return diff_text
end

function A:_resolve_status_label()
    local endless = self._state.endless == true
    local key = endless and "ky_hud_assault_endless" or "ky_hud_assault_status"
    local ok_loc, loc = pcall(function() return managers.localization end)
    if ok_loc and loc then
        local ok_t, t = pcall(function() return loc:text(key) end)
        if ok_t and type(t) == "string" and t ~= "" then return t end
    end
    return endless and "ENDLESS" or "ASSAULT"
end

function A:_resolve_ticker_text()
    local status = self:_resolve_status_label()
    local diff = self:_resolve_difficulty_text()
    if diff == "" then
        return status
    end
    return status .. " " .. diff
end

function A:_resolve_glyph_text()
    return self._state.endless == true and "!!" or "!"
end

function A:_resolve_hostages_text()
    local label = "HOSTAGES"
    local ok_loc, loc = pcall(function() return managers.localization end)
    if ok_loc and loc then
        local ok_t, t = pcall(function() return loc:text("ky_hud_hostages_label") end)
        if ok_t and type(t) == "string" and t ~= "" then label = t end
    end
    local h = self._state.hostages
    if h == nil then
        return label .. ": --"
    end
    return label .. ": " .. tostring(h)
end

function A:_resolve_converted_text()
    local label = "CONVERTED"
    local ok_loc, loc = pcall(function() return managers.localization end)
    if ok_loc and loc then
        local ok_t, t = pcall(function() return loc:text("ky_hud_converted_label") end)
        if ok_t and type(t) == "string" and t ~= "" then label = t end
    end
    local c = self._state.converted
    if c == nil then
        return label .. ": --"
    end
    return label .. ": " .. tostring(c)
end

function A:_ensure_bg_rect()
    if self._bg_rect and a_panel_alive(self._bg_rect) then return end
    if not self._root_panel or not a_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    local layout = self._layout_cache
    local endless = self._state.endless == true
    local color = endless
        and Color(1.0, 0.165, 0.333)
        or Color(0.949, 0.890, 0.106)
    local status, rect = a_safe_call(self._root_panel, "rect", {
        name = BG_RECT_NAME,
        x = 0, y = 0,
        w = layout.root_w, h = layout.root_h,
        color = color,
        layer = 0,
    })
    if status == a_call_ok and rect then
        self._bg_rect = rect
        self._cached_bg_key = endless and "endless" or "normal"
    end
end

function A:_ensure_ticker_panel()
    if self._ticker_panel and a_panel_alive(self._ticker_panel) then return end
    if not self._root_panel or not a_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    local layout = self._layout_cache
    local status, pnl = a_safe_call(self._root_panel, "panel", {
        name = TICKER_PANEL_NAME,
        x = layout.ticker.x, y = layout.ticker.y,
        w = layout.ticker.w, h = layout.ticker.h,
        clipping = true,
        layer = 1,
    })
    if status == a_call_ok and pnl then
        self._ticker_panel = pnl
    end
end

function A:_ensure_ticker_texts()
    if self._ticker_a and a_panel_alive(self._ticker_a)
        and self._ticker_b and a_panel_alive(self._ticker_b) then return end
    if not self._ticker_panel or not a_panel_alive(self._ticker_panel) then return end
    if not self._layout_cache then return end
    local font = self:_get_font()
    local layout = self._layout_cache
    local endless = self._state.endless == true
    local text_color = endless and Color(1, 1, 1, 1) or Color(1, 0.1, 0.1, 0.1)
    local ticker_text = self:_resolve_ticker_text()
    local sa, pa = a_safe_call(self._ticker_panel, "text", {
        name = TICKER_A_NAME,
        text = ticker_text,
        font = font,
        font_size = layout.font_size,
        color = text_color,
        x = 0, y = 0,
        w = layout.ticker.w, h = layout.ticker.h,
        align = "left", vertical = "center",
        wrap = false, word_wrap = false,
        layer = 1,
    })
    if sa == a_call_ok and pa then
        self._ticker_a = pa
        self._cached_ticker_text = ticker_text
        self._cached_font = font
        self._cached_font_size = layout.font_size
        self._ticker_x_a = 0
        self._ticker_gap = REF_TICKER_GAP * (layout.es or 1)
        local ok_mr, mx, my, mw, mh = pcall(function() return pa:text_rect() end)
        if ok_mr and a_is_finite(mw) and mw > 0 then
            self._ticker_measured_w = mw
            a_safe_call(pa, "set_shape", 0, 0, mw, layout.ticker.h)
        end
    end
    local mw = self._ticker_measured_w or 0
    local gap = self._ticker_gap or (REF_TICKER_GAP * ((self._layout_cache and self._layout_cache.es) or 1))
    local bx = mw + gap
    local ticker_w = mw > 0 and mw or layout.ticker.w
    local sb, pb = a_safe_call(self._ticker_panel, "text", {
        name = TICKER_B_NAME,
        text = ticker_text,
        font = font,
        font_size = layout.font_size,
        color = text_color,
        x = bx, y = 0,
        w = ticker_w, h = layout.ticker.h,
        align = "left", vertical = "center",
        wrap = false, word_wrap = false,
        layer = 1,
    })
    if sb == a_call_ok and pb then
        self._ticker_b = pb
        self._ticker_x_b = bx
    end
end

function A:_ensure_glyph_prim()
    if self._glyph_prim and a_panel_alive(self._glyph_prim) then return end
    if not self._root_panel or not a_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    local font = self:_get_font()
    local layout = self._layout_cache
    local endless = self._state.endless == true
    local text_color = endless and Color(1, 1, 1, 1) or Color(1, 0.1, 0.1, 0.1)
    local glyph_text = self:_resolve_glyph_text()
    local status, prim = a_safe_call(self._root_panel, "text", {
        name = GLYPH_NAME,
        text = glyph_text,
        font = font,
        font_size = layout.font_size,
        color = text_color,
        x = layout.glyph.x, y = layout.glyph.y,
        w = layout.glyph.w, h = layout.glyph.h,
        align = "center", vertical = "center",
        wrap = false, word_wrap = false,
        layer = 1,
    })
    if status == a_call_ok and prim then
        self._glyph_prim = prim
        self._cached_glyph_text = glyph_text
    end
end

function A:_ensure_hostages_prim()
    if self._hostages_prim and a_panel_alive(self._hostages_prim) then return end
    if not self._root_panel or not a_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    local font = self:_get_font()
    local layout = self._layout_cache
    local endless = self._state.endless == true
    local text_color = endless and Color(1, 1, 1, 1) or Color(1, 0.1, 0.1, 0.1)
    local text = self:_resolve_hostages_text()
    local status, prim = a_safe_call(self._root_panel, "text", {
        name = HOSTAGES_NAME,
        text = text,
        font = font,
        font_size = layout.font_size,
        color = text_color,
        x = layout.hostages.x, y = layout.hostages.y,
        w = layout.hostages.w, h = layout.hostages.h,
        align = "left", vertical = "center",
        wrap = false, word_wrap = false,
        layer = 1,
    })
    if status == a_call_ok and prim then
        self._hostages_prim = prim
        self._cached_hostages_text = text
    end
end

function A:_ensure_converted_prim()
    if self._converted_prim and a_panel_alive(self._converted_prim) then return end
    if not self._root_panel or not a_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    local font = self:_get_font()
    local layout = self._layout_cache
    local endless = self._state.endless == true
    local text_color = endless and Color(1, 1, 1, 1) or Color(1, 0.1, 0.1, 0.1)
    local text = self:_resolve_converted_text()
    local status, prim = a_safe_call(self._root_panel, "text", {
        name = CONVERTED_NAME,
        text = text,
        font = font,
        font_size = layout.font_size,
        color = text_color,
        x = layout.converted.x, y = layout.converted.y,
        w = layout.converted.w, h = layout.converted.h,
        align = "right", vertical = "center",
        wrap = false, word_wrap = false,
        layer = 1,
    })
    if status == a_call_ok and prim then
        self._converted_prim = prim
        self._cached_converted_text = text
    end
end

function A:_ensure_primitives()
    self:_ensure_bg_rect()
    self:_ensure_ticker_panel()
    self:_ensure_ticker_texts()
    self:_ensure_glyph_prim()
    self:_ensure_hostages_prim()
    self:_ensure_converted_prim()
end

function A:_sync_bg_rect()
    if not self._bg_rect or not a_panel_alive(self._bg_rect) then return end
    local endless = self._state.endless == true
    local key = endless and "endless" or "normal"
    if key ~= self._cached_bg_key then
        local color = endless
            and Color(1.0, 0.165, 0.333)
            or Color(0.949, 0.890, 0.106)
        a_safe_call(self._bg_rect, "set_color", color)
        self._cached_bg_key = key
    end
end

function A:_sync_ticker_text()
    if not self._ticker_a or not a_panel_alive(self._ticker_a) then return end
    if not self._ticker_b or not a_panel_alive(self._ticker_b) then return end
    local new_text = self:_resolve_ticker_text()
    local needs_measure = false
    if new_text ~= self._cached_ticker_text then
        a_safe_call(self._ticker_a, "set_text", new_text)
        a_safe_call(self._ticker_b, "set_text", new_text)
        local ok_ra, ra = pcall(function() return self._ticker_a:text() end)
        local ok_rb, rb = pcall(function() return self._ticker_b:text() end)
        if ok_ra and ra == new_text and ok_rb and rb == new_text then
            self._cached_ticker_text = new_text
        end
        needs_measure = true
    else
        local ok_a, actual_a = pcall(function() return self._ticker_a:text() end)
        if ok_a and type(actual_a) == "string" and actual_a ~= new_text then
            a_safe_call(self._ticker_a, "set_text", new_text)
            needs_measure = true
        end
        local ok_b, actual_b = pcall(function() return self._ticker_b:text() end)
        if ok_b and type(actual_b) == "string" and actual_b ~= new_text then
            a_safe_call(self._ticker_b, "set_text", new_text)
            needs_measure = true
        end
    end
    if needs_measure then
        local ok_mr, mx, my, mw, mh = pcall(function() return self._ticker_a:text_rect() end)
        if ok_mr and a_is_finite(mw) and mw > 0 then
            self._ticker_measured_w = mw
            local ticker_h = (self._layout_cache and self._layout_cache.ticker and self._layout_cache.ticker.h) or REF_TICKER_H
            local ax = self._ticker_x_a or 0
            a_safe_call(self._ticker_a, "set_shape", ax, 0, mw, ticker_h)
            local bx = self._ticker_x_b or (mw + (self._ticker_gap or REF_TICKER_GAP))
            a_safe_call(self._ticker_b, "set_shape", bx, 0, mw, ticker_h)
        end
    end
end

function A:_sync_glyph_text()
    if not self._glyph_prim or not a_panel_alive(self._glyph_prim) then return end
    local new_text = self:_resolve_glyph_text()
    if new_text ~= self._cached_glyph_text then
        a_safe_call(self._glyph_prim, "set_text", new_text)
        local ok_r, r = pcall(function() return self._glyph_prim:text() end)
        if ok_r and r == new_text then
            self._cached_glyph_text = new_text
        end
    else
        local ok_a, actual = pcall(function() return self._glyph_prim:text() end)
        if ok_a and type(actual) == "string" and actual ~= new_text then
            a_safe_call(self._glyph_prim, "set_text", new_text)
        end
    end
end

function A:_sync_hostages_text()
    if not self._hostages_prim or not a_panel_alive(self._hostages_prim) then return end
    local new_text = self:_resolve_hostages_text()
    if new_text ~= self._cached_hostages_text then
        a_safe_call(self._hostages_prim, "set_text", new_text)
        local ok_r, r = pcall(function() return self._hostages_prim:text() end)
        if ok_r and r == new_text then
            self._cached_hostages_text = new_text
        end
    else
        local ok_a, actual = pcall(function() return self._hostages_prim:text() end)
        if ok_a and type(actual) == "string" and actual ~= new_text then
            a_safe_call(self._hostages_prim, "set_text", new_text)
        end
    end
end

function A:_sync_converted_text()
    if not self._converted_prim or not a_panel_alive(self._converted_prim) then return end
    local new_text = self:_resolve_converted_text()
    if new_text ~= self._cached_converted_text then
        a_safe_call(self._converted_prim, "set_text", new_text)
        local ok_r, r = pcall(function() return self._converted_prim:text() end)
        if ok_r and r == new_text then
            self._cached_converted_text = new_text
        end
    else
        local ok_a, actual = pcall(function() return self._converted_prim:text() end)
        if ok_a and type(actual) == "string" and actual ~= new_text then
            a_safe_call(self._converted_prim, "set_text", new_text)
        end
    end
end

function A:_sync_text_colors()
    local endless = self._state.endless == true
    local key = endless and "endless" or "normal"
    if key == self._cached_text_color_key then return end
    local color = endless and Color(1, 1, 1, 1) or Color(1, 0.1, 0.1, 0.1)
    if self._ticker_a and a_panel_alive(self._ticker_a) then
        a_safe_call(self._ticker_a, "set_color", color)
    end
    if self._ticker_b and a_panel_alive(self._ticker_b) then
        a_safe_call(self._ticker_b, "set_color", color)
    end
    if self._glyph_prim and a_panel_alive(self._glyph_prim) then
        a_safe_call(self._glyph_prim, "set_color", color)
    end
    if self._hostages_prim and a_panel_alive(self._hostages_prim) then
        a_safe_call(self._hostages_prim, "set_color", color)
    end
    if self._converted_prim and a_panel_alive(self._converted_prim) then
        a_safe_call(self._converted_prim, "set_color", color)
    end
    self._cached_text_color_key = key
end

function A:_sync_primitives()
    self:_sync_bg_rect()
    self:_sync_ticker_text()
    self:_sync_glyph_text()
    self:_sync_hostages_text()
    self:_sync_converted_text()
    self:_sync_text_colors()
end

function A:_update_ticker(dt)
    if not self._ticker_a or not a_panel_alive(self._ticker_a) then return end
    if not self._ticker_b or not a_panel_alive(self._ticker_b) then return end
    if not self._ticker_panel or not a_panel_alive(self._ticker_panel) then return end
    if not a_is_finite(dt) or dt <= 0 then return end
    local es = (self._layout_cache and self._layout_cache.es) or 1
    local speed = REF_TICKER_SPEED * es
    local dx = speed * dt
    local ax = self._ticker_x_a - dx
    local cycle = (self._ticker_measured_w or 0) + (self._ticker_gap or (REF_TICKER_GAP * es))
    if cycle > 0 then
        ax = -(((-ax) % cycle))
    end
    local bx = ax + cycle
    a_safe_call(self._ticker_a, "set_x", ax)
    self._ticker_x_a = ax
    a_safe_call(self._ticker_b, "set_x", bx)
    self._ticker_x_b = bx
end

function A:_refresh_counters()
    local ok_state, state = pcall(function() return managers.groupai:state() end)
    if not ok_state or not state then
        self:snapshot(self._manager)
        return
    end
    local source_changed = (state ~= self._source)
    if source_changed then
        self:snapshot(self._manager)
        return
    end
    local same_source_event = (self._event_manager == self._manager)
    local ok_hunt, hunt = pcall(function() return state:get_hunt_mode() end)
    if ok_hunt then
        if not (same_source_event and self._event_has_endless) then
            self._state.endless = hunt == true
        end
    end
    local ok_h, hc = pcall(function() return state:hostage_count() end)
    if same_source_event and self._event_has_hostages then
        self._state.hostages = self._event_hostages
    elseif ok_h and is_finite_nonneg(hc) then
        self._state.hostages = hc
    else
        self._state.hostages = nil
    end
    local ok_reg, registry = pcall(function() return state:all_converted_enemies() end)
    if ok_reg and type(registry) == "table" then
        local count = 0
        local all_ok = true
        for _, unit in pairs(registry) do
            local ok_alive, is_alive = pcall(function() return alive(unit) end)
            if not ok_alive or type(is_alive) ~= "boolean" then all_ok = false; break end
            if is_alive then
                local ok_cd, cd = pcall(function() return unit:character_damage() end)
                if not ok_cd or (type(cd) ~= "table" and type(cd) ~= "userdata") then all_ok = false; break end
                local ok_dead, is_dead = pcall(function() return cd:dead() end)
                if not ok_dead or (is_dead ~= nil and is_dead ~= false and is_dead ~= true) then all_ok = false; break end
                if is_dead ~= true then count = count + 1 end
            end
        end
        if all_ok then
            self._state.converted = count
        else
            self._state.converted = nil
        end
    else
        self._state.converted = nil
    end
end

function A:_update_layout()
    if not self._root_panel or not a_panel_alive(self._root_panel) then return end
    if not self._parent_panel or not a_panel_alive(self._parent_panel) then return end
    local pw_s, pw = a_safe_call(self._parent_panel, "w")
    local ph_s, ph = a_safe_call(self._parent_panel, "h")
    if pw_s ~= a_call_ok or ph_s ~= a_call_ok then return end
    if not a_is_finite(pw) or not a_is_finite(ph) then return end
    if pw <= 0 or ph <= 0 then return end
    local new_layout = self:_compute_layout(pw, ph)
    if not new_layout then
        self._layout_cache = nil
        return
    end
    local changed = not self._layout_cache or
        self._layout_cache.root_x ~= new_layout.root_x or
        self._layout_cache.root_y ~= new_layout.root_y or
        self._layout_cache.root_w ~= new_layout.root_w or
        self._layout_cache.root_h ~= new_layout.root_h or
        self._layout_cache.font_size ~= new_layout.font_size
    if not changed then return end
    a_safe_call(self._root_panel, "set_shape", new_layout.root_x, new_layout.root_y, new_layout.root_w, new_layout.root_h)
    if self._bg_rect and a_panel_alive(self._bg_rect) then
        a_safe_call(self._bg_rect, "set_shape", 0, 0, new_layout.root_w, new_layout.root_h)
    end
    if self._ticker_panel and a_panel_alive(self._ticker_panel) then
        a_safe_call(self._ticker_panel, "set_shape", new_layout.ticker.x, new_layout.ticker.y, new_layout.ticker.w, new_layout.ticker.h)
    end
    if self._glyph_prim and a_panel_alive(self._glyph_prim) then
        a_safe_call(self._glyph_prim, "set_shape", new_layout.glyph.x, new_layout.glyph.y, new_layout.glyph.w, new_layout.glyph.h)
        a_safe_call(self._glyph_prim, "set_font_size", new_layout.font_size)
    end
    if self._hostages_prim and a_panel_alive(self._hostages_prim) then
        a_safe_call(self._hostages_prim, "set_shape", new_layout.hostages.x, new_layout.hostages.y, new_layout.hostages.w, new_layout.hostages.h)
        a_safe_call(self._hostages_prim, "set_font_size", new_layout.font_size)
    end
    if self._converted_prim and a_panel_alive(self._converted_prim) then
        a_safe_call(self._converted_prim, "set_shape", new_layout.converted.x, new_layout.converted.y, new_layout.converted.w, new_layout.converted.h)
        a_safe_call(self._converted_prim, "set_font_size", new_layout.font_size)
    end
    if self._ticker_a and a_panel_alive(self._ticker_a) then
        a_safe_call(self._ticker_a, "set_font_size", new_layout.font_size)
    end
    if self._ticker_b and a_panel_alive(self._ticker_b) then
        a_safe_call(self._ticker_b, "set_font_size", new_layout.font_size)
    end
    if self._ticker_a and a_panel_alive(self._ticker_a) then
        local ok_mr, mx, my, mw, mh = pcall(function() return self._ticker_a:text_rect() end)
        if ok_mr and a_is_finite(mw) and mw > 0 then
            self._ticker_measured_w = mw
            local ticker_h = new_layout.ticker.h
            local ax = self._ticker_x_a or 0
            a_safe_call(self._ticker_a, "set_shape", ax, 0, mw, ticker_h)
            local gap = self._ticker_gap or (REF_TICKER_GAP * (new_layout.es or 1))
            local bx = self._ticker_x_b or (mw + gap)
            a_safe_call(self._ticker_b, "set_shape", bx, 0, mw, ticker_h)
        end
    end
    self._layout_cache = new_layout
end

function A:_verify_render()
    if not self._layout_cache then
        self._render_verified = false
        return false
    end
    local geom = self._layout_cache
    if not a_is_finite(geom.root_w) or not a_is_finite(geom.root_h) or not a_is_finite(geom.font_size) then
        self._render_verified = false
        return false
    end
    if geom.root_w <= 0 or geom.root_h <= 0 or geom.font_size <= 0 then
        self._render_verified = false
        return false
    end
    if not self._root_panel or not a_panel_alive(self._root_panel) then
        self._render_verified = false
        return false
    end
    if not self._bg_rect or not a_panel_alive(self._bg_rect) then
        self._render_verified = false
        return false
    end
    if not self._ticker_panel or not a_panel_alive(self._ticker_panel) then
        self._render_verified = false
        return false
    end
    if not self._ticker_a or not a_panel_alive(self._ticker_a) then
        self._render_verified = false
        return false
    end
    if not self._ticker_b or not a_panel_alive(self._ticker_b) then
        self._render_verified = false
        return false
    end
    if not self._glyph_prim or not a_panel_alive(self._glyph_prim) then
        self._render_verified = false
        return false
    end
    if not self._hostages_prim or not a_panel_alive(self._hostages_prim) then
        self._render_verified = false
        return false
    end
    if not self._converted_prim or not a_panel_alive(self._converted_prim) then
        self._render_verified = false
        return false
    end
    local tol = 0.5
    local ox_s, ox = a_safe_call(self._root_panel, "x")
    local oy_s, oy = a_safe_call(self._root_panel, "y")
    local ow_s, ow = a_safe_call(self._root_panel, "w")
    local oh_s, oh = a_safe_call(self._root_panel, "h")
    if ox_s ~= a_call_ok or oy_s ~= a_call_ok or ow_s ~= a_call_ok or oh_s ~= a_call_ok then
        self._render_verified = false
        return false
    end
    if not a_is_finite(ox) or not a_is_finite(oy) or not a_is_finite(ow) or not a_is_finite(oh) then
        self._render_verified = false
        return false
    end
    if math.abs(ox - geom.root_x) > tol or math.abs(oy - geom.root_y) > tol
        or math.abs(ow - geom.root_w) > tol or math.abs(oh - geom.root_h) > tol then
        self._render_verified = false
        return false
    end
    local ok_vis, vis = pcall(function() return self._root_panel:visible() end)
    if not ok_vis or vis ~= true then
        self._render_verified = false
        return false
    end
    local bg_x_s, bg_x = a_safe_call(self._bg_rect, "x")
    local bg_y_s, bg_y = a_safe_call(self._bg_rect, "y")
    local bg_w_s, bg_w = a_safe_call(self._bg_rect, "w")
    local bg_h_s, bg_h = a_safe_call(self._bg_rect, "h")
    if bg_x_s ~= a_call_ok or bg_y_s ~= a_call_ok or bg_w_s ~= a_call_ok or bg_h_s ~= a_call_ok then
        self._render_verified = false
        return false
    end
    if not a_is_finite(bg_x) or not a_is_finite(bg_y) or not a_is_finite(bg_w) or not a_is_finite(bg_h) then
        self._render_verified = false
        return false
    end
    if math.abs(bg_x) > tol or math.abs(bg_y) > tol
        or math.abs(bg_w - geom.root_w) > tol or math.abs(bg_h - geom.root_h) > tol then
        self._render_verified = false
        return false
    end
    local ok_bv, bv = pcall(function() return self._bg_rect:visible() end)
    if not ok_bv or bv ~= true then
        self._render_verified = false
        return false
    end
    local tp_x_s, tp_x = a_safe_call(self._ticker_panel, "x")
    local tp_y_s, tp_y = a_safe_call(self._ticker_panel, "y")
    local tp_w_s, tp_w = a_safe_call(self._ticker_panel, "w")
    local tp_h_s, tp_h = a_safe_call(self._ticker_panel, "h")
    if tp_x_s ~= a_call_ok or tp_y_s ~= a_call_ok or tp_w_s ~= a_call_ok or tp_h_s ~= a_call_ok then
        self._render_verified = false
        return false
    end
    if not a_is_finite(tp_x) or not a_is_finite(tp_y) or not a_is_finite(tp_w) or not a_is_finite(tp_h) then
        self._render_verified = false
        return false
    end
    if math.abs(tp_x - geom.ticker.x) > tol or math.abs(tp_y - geom.ticker.y) > tol
        or math.abs(tp_w - geom.ticker.w) > tol or math.abs(tp_h - geom.ticker.h) > tol then
        self._render_verified = false
        return false
    end
    local ok_tv, tv = pcall(function() return self._ticker_panel:visible() end)
    if not ok_tv or tv ~= true then
        self._render_verified = false
        return false
    end
    local desired_ticker = self._cached_ticker_text
    if type(desired_ticker) ~= "string" or desired_ticker == "" then
        self._render_verified = false
        return false
    end
    local function check_text(prim, desired, region, skip_x, width_override)
        local ok_v, v = pcall(function() return prim:visible() end)
        if not ok_v or v ~= true then return false end
        local ok_t, t = pcall(function() return prim:text() end)
        if not ok_t or type(t) ~= "string" then return false end
        if t ~= desired then return false end
        local ok_fs, fs = pcall(function() return prim:font_size() end)
        if not ok_fs or not a_is_finite(fs) or fs <= 0 then return false end
        if math.abs(fs - geom.font_size) > 0.5 then return false end
        local s_px, px = a_safe_call(prim, "x")
        local s_py, py = a_safe_call(prim, "y")
        local s_pw, pw = a_safe_call(prim, "w")
        local s_ph, ph = a_safe_call(prim, "h")
        if s_px ~= a_call_ok or s_py ~= a_call_ok or s_pw ~= a_call_ok or s_ph ~= a_call_ok then
            return false
        end
        if not a_is_finite(px) or not a_is_finite(py) or not a_is_finite(pw) or not a_is_finite(ph) then
            return false
        end
        if not skip_x and math.abs(px - region.x) > tol then return false end
        if math.abs(py - region.y) > tol then return false end
        local expected_w = width_override or region.w
        if math.abs(pw - expected_w) > tol then return false end
        if math.abs(ph - region.h) > tol then return false end
        local ok_mr, mr_x, mr_y, mw, mh = pcall(function() return prim:text_rect() end)
        if not ok_mr then return false end
        if not a_is_finite(mw) or not a_is_finite(mh) then return false end
        if mw <= 0 or mh <= 0 then return false end
        if mh > ph + tol then return false end
        return true
    end
    if not check_text(self._ticker_a, desired_ticker, geom.ticker, true, self._ticker_measured_w) then
        self._render_verified = false
        return false
    end
    local ok_tax, tax = a_safe_call(self._ticker_a, "x")
    if ok_tax ~= a_call_ok or not a_is_finite(tax) then
        self._render_verified = false
        return false
    end
    if not check_text(self._ticker_b, desired_ticker, geom.ticker, true, self._ticker_measured_w) then
        self._render_verified = false
        return false
    end
    local ok_tbx, tbx = a_safe_call(self._ticker_b, "x")
    if ok_tbx ~= a_call_ok or not a_is_finite(tbx) then
        self._render_verified = false
        return false
    end
    local desired_glyph = self._cached_glyph_text
    if type(desired_glyph) ~= "string" or desired_glyph == "" then
        self._render_verified = false
        return false
    end
    if not check_text(self._glyph_prim, desired_glyph, geom.glyph, false) then
        self._render_verified = false
        return false
    end
    local desired_hostages = self._cached_hostages_text
    if type(desired_hostages) ~= "string" or desired_hostages == "" then
        self._render_verified = false
        return false
    end
    if not check_text(self._hostages_prim, desired_hostages, geom.hostages, false) then
        self._render_verified = false
        return false
    end
    local desired_converted = self._cached_converted_text
    if type(desired_converted) ~= "string" or desired_converted == "" then
        self._render_verified = false
        return false
    end
    if not check_text(self._converted_prim, desired_converted, geom.converted, false) then
        self._render_verified = false
        return false
    end
    self._render_verified = true
    return true
end

function A:_handle_render_failure()
    self._render_failed = true
    self._render_verified = false
    if self._root_panel and a_panel_alive(self._root_panel) then
        a_safe_call(self._root_panel, "set_visible", false)
    end
    self:_release_native()
end

function A:_resolve_native_targets()
    if not self._manager then return nil end
    local function check_parent(child, expected_parent)
        if not child or not a_panel_alive(child) then return false end
        local ok, p = pcall(function() return child:parent() end)
        if not ok then return false end
        return p == expected_parent
    end
    local ok_corner, corner = pcall(function() return self._manager._hud_assault_corner end)
    if not ok_corner or not corner then return nil end
    local ok_pnr, pnr = pcall(function() return corner._point_of_no_return end)
    if ok_pnr and pnr == true then return nil end
    local ok_cas, cas = pcall(function() return corner._casing end)
    if ok_cas and cas == true then return nil end
    local ok_hp, hp = pcall(function() return corner._hud_panel end)
    if not ok_hp or not hp then return nil end
    if not a_panel_alive(hp) then return nil end
    local ok_ap, ap = pcall(function() return hp:child("assault_panel") end)
    if not ok_ap or not ap then return nil end
    if not a_panel_alive(ap) then return nil end
    if not check_parent(ap, hp) then return nil end
    local ok_icon, icon = pcall(function() return ap:child("icon_assaultbox") end)
    if not ok_icon or not icon then return nil end
    if not a_panel_alive(icon) then return nil end
    if not check_parent(icon, ap) then return nil end
    local ok_bg, bg = pcall(function() return corner._bg_box end)
    if not ok_bg or not bg then return nil end
    if not a_panel_alive(bg) then return nil end
    if not check_parent(bg, ap) then return nil end
    local ok_tp, tp = pcall(function() return bg:child("text_panel") end)
    if not ok_tp or not tp then return nil end
    if not a_panel_alive(tp) then return nil end
    if not check_parent(tp, bg) then return nil end
    local bg_leaf_names = { "bg", "left_top", "left_bottom", "right_top", "right_bottom" }
    local bg_leaves = {}
    for _, name in ipairs(bg_leaf_names) do
        local ok_l, leaf = pcall(function() return bg:child(name) end)
        if not ok_l or not leaf then return nil end
        if not a_panel_alive(leaf) then return nil end
        if not check_parent(leaf, bg) then return nil end
        bg_leaves[#bg_leaves + 1] = leaf
    end
    local ok_hpnl, hostages_panel = pcall(function() return hp:child("hostages_panel") end)
    if not ok_hpnl or not hostages_panel then return nil end
    if not a_panel_alive(hostages_panel) then return nil end
    if not check_parent(hostages_panel, hp) then return nil end
    local ok_hi, hi = pcall(function() return hostages_panel:child("hostages_icon") end)
    if not ok_hi or not hi then return nil end
    if not a_panel_alive(hi) then return nil end
    if not check_parent(hi, hostages_panel) then return nil end
    local ok_hb, hb = pcall(function() return corner._hostages_bg_box end)
    if not ok_hb or not hb then return nil end
    if not a_panel_alive(hb) then return nil end
    if not check_parent(hb, hostages_panel) then return nil end
    local ok_num, num = pcall(function() return hb:child("num_hostages") end)
    if not ok_num or not num then return nil end
    if not a_panel_alive(num) then return nil end
    if not check_parent(num, hb) then return nil end
    local hostage_bg_leaf_names = { "bg", "left_top", "left_bottom", "right_top", "right_bottom" }
    local hostage_bg_leaves = {}
    for _, name in ipairs(hostage_bg_leaf_names) do
        local ok_l, leaf = pcall(function() return hb:child(name) end)
        if not ok_l or not leaf then return nil end
        if not a_panel_alive(leaf) then return nil end
        if not check_parent(leaf, hb) then return nil end
        hostage_bg_leaves[#hostage_bg_leaves + 1] = leaf
    end
    return {
        corner = corner,
        hud_panel = hp,
        text_panel = tp,
        bg_leaves = bg_leaves,
        assault_icon = icon,
        hostage_icon = hi,
        hostage_bg = hb,
        hostage_bg_leaves = hostage_bg_leaves,
        num = num,
    }
end

function A:_should_fallback_native()
    if not self._manager then return true end
    local ok_corner, corner = pcall(function() return self._manager._hud_assault_corner end)
    if not ok_corner or not corner then return true end
    local ok_waves, waves = pcall(function() return corner:should_display_waves() end)
    if not ok_waves then return true end
    if waves == true then return true end
    local ok_pnr, pnr = pcall(function() return corner._point_of_no_return end)
    if ok_pnr and pnr == true then return true end
    local ok_cas, cas = pcall(function() return corner._casing end)
    if ok_cas and cas == true then return true end
    local AL = kyohud and kyohud.hud and kyohud.hud.alerts
    if type(AL) == "table" and type(AL.blocks_assault) == "function" then
        local ok_ba, ba = pcall(AL.blocks_assault, AL, self._manager)
        if ok_ba then
            if ba == true then return true end
        else
            return true
        end
    else
        local ok_hp2, hp2 = pcall(function() return corner._hud_panel end)
        if ok_hp2 and hp2 and a_panel_alive(hp2) then
            local ok_cp, cp = pcall(function() return hp2:child("casing_panel") end)
            if ok_cp and cp and a_panel_alive(cp) then
                local ok_cv, cv = pcall(function() return cp:visible() end)
                if ok_cv and cv == true then return true end
            end
        end
    end
    local ok_hp, hp = pcall(function() return corner._hud_panel end)
    if ok_hp and hp and a_panel_alive(hp) then
        local check_panels = { "point_of_no_return_panel", "buffs_panel" }
        for _, name in ipairs(check_panels) do
            local ok_p, pnl = pcall(function() return hp:child(name) end)
            if not ok_p then return true end
            if pnl and a_panel_alive(pnl) then
                local ok_v, v = pcall(function() return pnl:visible() end)
                if not ok_v then return true end
                if v == true then return true end
            end
        end
    end
    local ok_am, am = pcall(function() return corner._assault_mode end)
    if ok_am and am == "phalanx" then
        local ok_state, state = pcall(function() return managers.groupai:state() end)
        if not ok_state or not state then return true end
        local ok_hunt, hunt = pcall(function() return state:get_hunt_mode() end)
        if not ok_hunt then return true end
        if hunt ~= true then return true end
    end
    return false
end

function A:_try_acquire_native()
    if not self._render_verified then return false end
    if self._state.active ~= true then return false end
    if a_is_vr() then return false end
    if self:_should_fallback_native() then return false end
    local targets = self:_resolve_native_targets()
    if not targets then return false end
    if self._conflict_corner and self._conflict_corner == targets.corner then
        return false
    end
    local rt = kyohud.hud.runtime
    if not rt then return false end
    local gen = rt._generation or 0
    local nv = kyohud.hud.native_visibility
    if not nv then return false end
    if self._native_acquired then
        if self._native_corner ~= targets.corner then
            local released = self:_release_native()
            if not released then return false end
        else
            local requests = self._native_requests
            if requests then
                for _, req in ipairs(requests) do
                    local actual, err = nv:_read_value(req.id, req.property)
                    if err or actual == nil or actual ~= req.value then
                        self._conflict_corner = self._native_corner
                        nv:release("assault", self._native_generation)
                        self._native_acquired = false
                        return false
                    end
                end
            end
            return true
        end
    elseif self._native_corner and self._native_corner ~= targets.corner then
        local released = self:_release_native()
        if not released then return false end
    end
    nv._whitelist[targets.text_panel] = nv._whitelist[targets.text_panel] or {}
    nv._whitelist[targets.text_panel].alpha = true
    local visible_objs = {
        targets.assault_icon,
        targets.hostage_icon,
        targets.num,
    }
    for _, leaf in ipairs(targets.bg_leaves) do
        visible_objs[#visible_objs + 1] = leaf
    end
    for _, leaf in ipairs(targets.hostage_bg_leaves) do
        visible_objs[#visible_objs + 1] = leaf
    end
    for _, obj in ipairs(visible_objs) do
        nv._whitelist[obj] = nv._whitelist[obj] or {}
        nv._whitelist[obj].visible = true
    end
    local requests = {
        { id = targets.text_panel, property = "alpha", value = 0 },
    }
    for _, obj in ipairs(visible_objs) do
        requests[#requests + 1] = { id = obj, property = "visible", value = false }
    end
    self._native_requests = requests
    self._native_corner = targets.corner
    self._native_hud_panel = targets.hud_panel
    self._native_targets = targets
    self._native_generation = gen
    local acquired = nv:acquire("assault", gen, requests)
    if acquired then
        self._native_acquired = true
        return true
    end
    self._native_acquired = false
    return false
end

function A:_release_native()
    if not self._native_acquired and not self._native_corner then return true end
    local nv = kyohud.hud.native_visibility
    if not nv then return false end
    local gen = self._native_generation
    if gen and self._native_requests then
        nv:release("assault", gen)
    end
    local pending = false
    if gen then
        for _, e in ipairs(nv._entries) do
            if e.owner == "assault" and e.generation == gen then
                pending = true
                break
            end
        end
    end
    if pending then
        return false
    end
    local targets = self._native_targets
    if targets then
        local visible_objs = {
            targets.assault_icon,
            targets.hostage_icon,
            targets.num,
        }
        for _, leaf in ipairs(targets.bg_leaves) do
            visible_objs[#visible_objs + 1] = leaf
        end
        for _, leaf in ipairs(targets.hostage_bg_leaves) do
            visible_objs[#visible_objs + 1] = leaf
        end
        for _, obj in ipairs(visible_objs) do
            if nv._whitelist[obj] then
                nv._whitelist[obj].visible = nil
                if not next(nv._whitelist[obj]) then
                    nv._whitelist[obj] = nil
                end
            end
        end
        if nv._whitelist[targets.text_panel] then
            nv._whitelist[targets.text_panel].alpha = nil
            if not next(nv._whitelist[targets.text_panel]) then
                nv._whitelist[targets.text_panel] = nil
            end
        end
    end
    self._native_corner = nil
    self._native_hud_panel = nil
    self._native_targets = nil
    self._native_requests = nil
    self._native_acquired = false
    self._native_generation = 0
    return true
end

function A:_sync_native_visibility()
    local should_fallback = (self._state.active ~= true)
        or self:_should_fallback_native()
        or not self._root_panel
        or not a_panel_alive(self._root_panel)
        or not self._layout_cache

    if should_fallback then
        if self._native_acquired or self._native_corner then
            self:_release_native()
        end
        if self._root_panel and a_panel_alive(self._root_panel) then
            a_safe_call(self._root_panel, "set_visible", false)
        end
        return false
    end

    a_safe_call(self._root_panel, "set_visible", true)

    if not self:_verify_render() then
        self:_handle_render_failure()
        return false
    end

    if not self:_try_acquire_native() then
        self:_release_native()
        a_safe_call(self._root_panel, "set_visible", false)
        return false
    end

    return true
end

function A:_check_native_corner()
    if not self._native_corner then return end
    if not self._manager then return end
    local ok_corner, corner = pcall(function() return self._manager._hud_assault_corner end)
    if not ok_corner or not corner then return end
    if corner == self._native_corner then return end
    self:_release_native()
    self._render_verified = false
end

function A:_take_initial_snapshot()
    if not self._snapshot_taken then
        self:snapshot(self._manager)
        if self._event_manager == self._manager then
            if self._event_has_active then
                self._state.active = self._event_active == true
            end
            if self._event_has_endless then
                self._state.endless = self._event_endless == true
            end
            if self._event_has_number then
                self._state.number = self._event_number
            end
            if self._event_has_hostages then
                self._state.hostages = self._event_hostages
            end
        end
        self._snapshot_taken = true
    end
end

function A:mount(manager)
    if kyohud.settings.enable_hud_foundation ~= true then return end
    if kyohud.settings.enable_assault ~= true then return end
    if a_is_vr() then return end
    local mgr = manager or self._manager
    if not mgr then return end
    self._manager = mgr
    local parent = a_get_runtime_root()
    if not parent then return end
    if self._mounted and self._root_panel and a_panel_alive(self._root_panel) then
        if self._parent_panel == parent then
            self:_update_layout()
            return
        end
        self:unmount()
    end
    if self._root_panel and not a_panel_alive(self._root_panel) then
        self._root_panel = nil
        self._bg_rect = nil
        self._ticker_panel = nil
        self._ticker_a = nil
        self._ticker_b = nil
        self._glyph_prim = nil
        self._hostages_prim = nil
        self._converted_prim = nil
    end
    local status, existing = a_safe_call(parent, "child", ASSAULT_ROOT_NAME)
    if status == a_call_ok and existing ~= nil and a_panel_alive(existing) then
        if self._root_panel == existing then
            self._mounted = true
            self._parent_panel = parent
            self:_take_initial_snapshot()
            self:_update_layout()
            self:_ensure_primitives()
            self:_sync_native_visibility()
            return
        end
        return
    end
    if status ~= a_call_ok then return end
    local cs, root = a_safe_call(parent, "panel", {name = ASSAULT_ROOT_NAME})
    if cs ~= a_call_ok or root == nil then return end
    self._root_panel = root
    self._parent_panel = parent
    self._mounted = true
    self:_take_initial_snapshot()
    self:_update_layout()
    self:_ensure_primitives()
    self:_sync_native_visibility()
end

function A:unmount()
    local released = self:_release_native()
    if released then
        self._conflict_corner = nil
    end
    if not self._mounted and not self._root_panel then return true end
    if self._root_panel then
        if a_panel_alive(self._root_panel) then
            local parent = self._parent_panel
            if parent and a_panel_alive(parent) then
                local status, result = a_safe_call(parent, "remove", self._root_panel)
                if status == a_call_ok and result ~= false then
                    self._root_panel = nil
                else
                    self._mounted = false
                    return false
                end
            else
                self._root_panel = nil
            end
        else
            self._root_panel = nil
        end
    end
    self._bg_rect = nil
    self._ticker_panel = nil
    self._ticker_a = nil
    self._ticker_b = nil
    self._glyph_prim = nil
    self._hostages_prim = nil
    self._converted_prim = nil
    self._parent_panel = nil
    self._mounted = false
    self._layout_cache = nil
    self._render_verified = false
    self._render_failed = false
    self._cached_ticker_text = nil
    self._cached_glyph_text = nil
    self._cached_hostages_text = nil
    self._cached_converted_text = nil
    self._cached_font = nil
    self._cached_font_size = nil
    self._cached_bg_key = nil
    self._cached_text_color_key = nil
    self._ticker_x_a = 0
    self._ticker_x_b = 0
    self._ticker_measured_w = 0
    return true
end

function A:rebuild(manager)
    self:unmount()
    self:mount(manager)
end

function A:refresh_settings(manager)
    if kyohud.settings.enable_hud_foundation == true and kyohud.settings.enable_assault == true then
        self._conflict_corner = nil
        if not self._mounted or not self._root_panel or not a_panel_alive(self._root_panel) then
            self:mount(manager)
            return
        end
        self:_update_layout()
        self._render_failed = false
        self:_ensure_primitives()
        self:_sync_primitives()
        if not self:_verify_render() then
            self._render_failed = true
        end
        self:_sync_native_visibility()
    else
        if self._mounted or self._root_panel then
            self:unmount()
        end
    end
end

function A:update(manager, t, dt)
    if kyohud.settings.enable_hud_foundation ~= true or kyohud.settings.enable_assault ~= true then
        self:unmount()
        return
    end
    if a_is_vr() then
        self:unmount()
        return
    end
    if self._mounted and self._root_panel and not a_panel_alive(self._root_panel) then
        self._root_panel = nil
        self._parent_panel = nil
        self._bg_rect = nil
        self._ticker_panel = nil
        self._ticker_a = nil
        self._ticker_b = nil
        self._glyph_prim = nil
        self._hostages_prim = nil
        self._converted_prim = nil
        self._mounted = false
        self._layout_cache = nil
        self._render_verified = false
    end
    if not self._mounted then
        self:mount(manager or self._manager)
        if not self._mounted then return end
    end
    local do_refresh = false
    if t and (self._last_counter_time == nil or (t - self._last_counter_time) >= COUNTER_INTERVAL) then
        do_refresh = true
        self._last_counter_time = t
    end
    if do_refresh then
        self:_refresh_counters()
        self:_update_layout()
    end
    if do_refresh or self._data_dirty then
        self:_sync_primitives()
        self._data_dirty = false
    end
    local sync_ok = self:_sync_native_visibility()
    if not sync_ok then
        if self._render_failed then
            if t and (self._last_counter_time == nil or (t - self._last_counter_time) >= COUNTER_INTERVAL) then
                self._last_counter_time = t
                self._render_failed = false
                self:_update_layout()
                self:_ensure_primitives()
                self:_sync_primitives()
                a_safe_call(self._root_panel, "set_visible", true)
                if not self:_verify_render() then
                    self:_handle_render_failure()
                end
            end
        end
        return
    end
    self._render_failed = false
    if a_is_finite(dt) and dt > 0 then
        self:_update_ticker(dt)
    end
    if not self:_verify_render() then
        self:_handle_render_failure()
    end
end

function A:destroy(manager)
    if manager and self._manager and manager ~= self._manager then return end
    self:unmount()
end

function A:on_heist_start(manager)
    local mgr = manager or self._manager
    if not mgr then return end
    if self._heist_manager_id == mgr then return end
    self._heist_manager_id = mgr
    if self._mounted or self._root_panel then
        self:unmount()
    end
    self._snapshot_taken = false
    self._last_counter_time = nil
    self._event_manager = nil
    self._event_active = nil
    self._event_endless = nil
    self._event_number = nil
    self._event_hostages = nil
    self._event_has_active = false
    self._event_has_endless = false
    self._event_has_number = false
    self._event_has_hostages = false
    self._manager = mgr
end

local function safe_hook(class, method, id, fn)
    if type(class) ~= "table" then return end
    if kyohud.hud._installed_hooks[id] then return end
    if type(class[method]) ~= "function" then return end
    Hooks:PostHook(class, method, id, fn)
    kyohud.hud._installed_hooks[id] = true
end

if RequiredScript == REQUIRED_CONTEXT then
    local function cb_sync_start(self, assault_number)
        local ok_corner, corner = pcall(function() return self._hud_assault_corner end)
        if not ok_corner or not corner then return end
        local ok_pnr, pnr = pcall(function() return corner._point_of_no_return end)
        local ok_cas, cas = pcall(function() return corner._casing end)
        if not ok_pnr or not ok_cas or pnr or cas then return end
        S.active = true
        S.number = assault_number
        A._event_manager = self
        A._event_active = true
        A._event_has_active = true
        if type(assault_number) == "number" and assault_number == assault_number
                and assault_number ~= math.huge and assault_number ~= -math.huge then
            A._event_number = assault_number
            A._event_has_number = true
        end
        A._data_dirty = true
    end

    local function cb_sync_end(self, result)
        S.active = false
        A._event_manager = self
        A._event_active = false
        A._event_has_active = true
        A._data_dirty = true
    end

    local function cb_sync_number(self, assault_number)
        S.number = assault_number
        A._event_manager = self
        if type(assault_number) == "number" and assault_number == assault_number
                and assault_number ~= math.huge and assault_number ~= -math.huge then
            A._event_number = assault_number
            A._event_has_number = true
            A._data_dirty = true
        end
    end

    local function cb_sync_mode(self, mode)
        A._native_mode = mode
        local ok_state, state = pcall(function()
            return managers.groupai:state()
        end)
        if not ok_state or not state then return end
        local ok_hunt, hunt = pcall(function()
            return state:get_hunt_mode()
        end)
        if ok_hunt then
            S.endless = hunt == true
            A._event_manager = self
            A._event_endless = hunt == true
            A._event_has_endless = true
            A._data_dirty = true
        end
    end

    local function cb_set_control(self, data)
        if type(data) ~= "table" then return end
        local ok_h, h = pcall(function() return data.nr_hostages end)
        if ok_h and is_finite_nonneg(h) then
            S.hostages = h
            A._event_manager = self
            A._event_hostages = h
            A._event_has_hostages = true
            A._data_dirty = true
        end
    end

    safe_hook(HUDManager, "sync_start_assault", "KyohHUD_Assault_SyncStart", cb_sync_start)
    safe_hook(HUDManager, "sync_end_assault", "KyohHUD_Assault_SyncEnd", cb_sync_end)
    safe_hook(HUDManager, "sync_assault_number", "KyohHUD_Assault_SyncNumber", cb_sync_number)
    safe_hook(HUDManager, "sync_set_assault_mode", "KyohHUD_Assault_SyncMode", cb_sync_mode)
    safe_hook(HUDManager, "set_control_info", "KyohHUD_Assault_SetControlInfo", cb_set_control)
end
