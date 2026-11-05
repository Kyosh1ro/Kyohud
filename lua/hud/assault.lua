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
A._hostages_bg = A._hostages_bg
A._converted_bg = A._converted_bg
A._hostages_icon = A._hostages_icon
A._converted_icon = A._converted_icon
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
A._cached_status_texture = A._cached_status_texture
A._texture_avail_cache = A._texture_avail_cache or {}

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
local HOSTAGES_BG_NAME = "kyohud_assault_hostages_bg"
local CONVERTED_BG_NAME = "kyohud_assault_converted_bg"
local HOSTAGES_ICON_NAME = "kyohud_assault_hostages_icon"
local CONVERTED_ICON_NAME = "kyohud_assault_converted_icon"

local TEX_ASSAULT = "guis/textures/pd2/hud_icon_assaultbox"
local TEX_PADLOCK = "guis/textures/pd2/hud_icon_padlockbox"
local TEX_HOSTAGE = "guis/textures/pd2/hud_icon_hostage"
local TEX_CONVERTED = "guis/textures/pd2/skilltree/icons_atlas"
local TEX_CONVERTED_RECT = { 384, 512, 64, 64 }

local REF_MARGIN_RIGHT = 40
local REF_TOP = 36
local REF_WIDTH = 383
local REF_HEIGHT = 70
local REF_TICKER_W = 340
local REF_TICKER_H = 40
local REF_STATUS_W = 40
local REF_STATUS_H = 40
local REF_GAP = 3
local REF_COUNTER_VGAP = 4
local REF_COUNTER_H = 26
local REF_FONT_SIZE = 20
local REF_COUNTER_FONT = 16
local MIN_FONT_SIZE = 12
local MIN_COUNTER_FONT = 10
local REF_TICKER_SPEED = 60
local REF_TICKER_GAP = 40
local REF_CELL_PAD = 10
local REF_ICON_SIZE = 16
local REF_ICON_GAP = 6
local REF_CELL_GAP = 3
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

local function a_texture_available(path)
    if type(path) ~= "string" or path == "" then return false end
    if A._texture_avail_cache[path] ~= nil then
        return A._texture_avail_cache[path]
    end
    local result = true
    if DB ~= nil then
        local ok, res = pcall(function()
            local has = DB.has
            if type(has)~="function" then return false end
            return has(DB,Idstring("texture"),Idstring(path))
        end)
        if not ok then
            result = false
        else
            result = res == true
        end
    end
    A._texture_avail_cache[path] = result
    return result
end

local function a_texture_matches(actual, expected_path)
    if type(expected_path) ~= "string" or expected_path == "" then return false end
    if actual == nil then return false end
    if type(actual) == "string" then return actual == expected_path end
    local ok, matches = pcall(function()
        return actual:key() == Idstring(expected_path):key()
    end)
    return ok and matches == true
end

local function a_read_color(prim)
    if not prim or not a_panel_alive(prim) then return nil end
    local ok_c, c = pcall(function() return prim:color() end)
    if not ok_c or c == nil then return nil end
    local r, g, b
    if type(c) == "table" then
        r = c.r; g = c.g; b = c.b
    elseif type(c) == "userdata" then
        local ok_r, rv = pcall(function() return c.r end)
        local ok_g, gv = pcall(function() return c.g end)
        local ok_b, bv = pcall(function() return c.b end)
        if ok_r then r = rv end
        if ok_g then g = gv end
        if ok_b then b = bv end
    end
    if not a_is_finite(r) or not a_is_finite(g) or not a_is_finite(b) then return nil end
    local ok_a, a = pcall(function() return prim:alpha() end)
    if not ok_a or not a_is_finite(a) then return nil end
    return r, g, b, a
end

local function a_resolve_status_texture(endless)
    if endless then
        if a_texture_available(TEX_PADLOCK) then return TEX_PADLOCK end
        if a_texture_available(TEX_ASSAULT) then return TEX_ASSAULT end
        return nil
    else
        if a_texture_available(TEX_ASSAULT) then return TEX_ASSAULT end
        return nil
    end
end

local function a_color(r, g, b, a)
    if a ~= nil then
        return Color(a, r, g, b)
    end
    return Color(1, r, g, b)
end

local COLOR_TICKER_BG_NORMAL = nil
local COLOR_TICKER_BG_ENDLESS = nil
local COLOR_TICKER_INK_NORMAL = nil
local COLOR_TICKER_INK_ENDLESS = nil
local COLOR_CELL_BG = nil
local COLOR_COUNTER_INK = nil

local function a_init_colors()
    if COLOR_TICKER_BG_NORMAL then return end
    COLOR_TICKER_BG_NORMAL  = a_color(0.949, 0.890, 0.106)
    COLOR_TICKER_BG_ENDLESS = a_color(1.0, 0.165, 0.333)
    COLOR_TICKER_INK_NORMAL = a_color(0.067, 0.067, 0.067)
    COLOR_TICKER_INK_ENDLESS = a_color(1, 1, 1, 1)
    COLOR_CELL_BG           = a_color(0.043, 0.051, 0.067, 0.75)
    COLOR_COUNTER_INK       = a_color(0.788, 0.820, 0.847)
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
    if not layout or type(layout.assault_alerts) ~= "function" then return nil end
    local scale = kyohud.settings.hud_scale or 1
    local geom = layout.assault_alerts(parent_w, parent_h, scale)
    if not geom or not geom.valid then return nil end
    return geom
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
    return status .. " /// " .. diff
end

function A:_resolve_hostages_text()
    local h = self._state.hostages
    if h == nil then
        return "--"
    end
    return tostring(h)
end

function A:_resolve_converted_text()
    local c = self._state.converted
    if c == nil then
        return "--"
    end
    return tostring(c)
end

function A:_ensure_bg_rect()
    if self._bg_rect and a_panel_alive(self._bg_rect) then return end
    if not self._root_panel or not a_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    a_init_colors()
    local layout = self._layout_cache
    local endless = self._state.endless == true
    local color = endless and COLOR_TICKER_BG_ENDLESS or COLOR_TICKER_BG_NORMAL
    local bg = layout.bg or layout.ticker
    local status, rect = a_safe_call(self._root_panel, "rect", {
        name = BG_RECT_NAME,
        x = bg.x, y = bg.y,
        w = bg.w, h = bg.h,
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
    a_init_colors()
    local font = self:_get_font()
    local layout = self._layout_cache
    local endless = self._state.endless == true
    local text_color = endless and COLOR_TICKER_INK_ENDLESS or COLOR_TICKER_INK_NORMAL
    local ticker_text = self:_resolve_ticker_text()
    local sa, pa = a_safe_call(self._ticker_panel, "text", {
        name = TICKER_A_NAME,
        text = ticker_text,
        font = font,
        font_size = layout.ticker_font,
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
        self._cached_font_size = layout.ticker_font
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
        font_size = layout.ticker_font,
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
    local layout = self._layout_cache
    local endless = self._state.endless == true
    local tex = a_resolve_status_texture(endless)
    if not tex then return end
    local st = layout.status
    if not st then return end
    local status, prim = a_safe_call(self._root_panel, "bitmap", {
        name = GLYPH_NAME,
        texture = tex,
        x = st.x, y = st.y,
        w = st.w, h = st.h,
        layer = 1,
    })
    if status == a_call_ok and prim then
        self._glyph_prim = prim
        self._cached_status_texture = tex
    end
end

function A:_ensure_hostages_prim()
    if self._hostages_prim and a_panel_alive(self._hostages_prim) then return end
    if not self._root_panel or not a_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    a_init_colors()
    local font = self:_get_font()
    local layout = self._layout_cache
    local text = self:_resolve_hostages_text()
    local status, prim = a_safe_call(self._root_panel, "text", {
        name = HOSTAGES_NAME,
        text = text,
        font = font,
        font_size = layout.counter_font,
        color = COLOR_COUNTER_INK,
        x = 0, y = layout.counter_y,
        w = 1, h = layout.counter_h,
        align = "left", vertical = "center",
        wrap = false, word_wrap = false,
        layer = 2,
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
    a_init_colors()
    local font = self:_get_font()
    local layout = self._layout_cache
    local text = self:_resolve_converted_text()
    local status, prim = a_safe_call(self._root_panel, "text", {
        name = CONVERTED_NAME,
        text = text,
        font = font,
        font_size = layout.counter_font,
        color = COLOR_COUNTER_INK,
        x = 0, y = layout.counter_y,
        w = 1, h = layout.counter_h,
        align = "left", vertical = "center",
        wrap = false, word_wrap = false,
        layer = 2,
    })
    if status == a_call_ok and prim then
        self._converted_prim = prim
        self._cached_converted_text = text
    end
end

function A:_measure_text_w(prim)
    if not prim or not a_panel_alive(prim) then return 0 end
    local ok, mx, my, mw, mh = pcall(function() return prim:text_rect() end)
    if ok and a_is_finite(mw) and mw > 0 then return mw end
    return 0
end

function A:_cell_width(text_w)
    local layout = self._layout_cache
    if not layout then return 0 end
    local pad = (layout.cell_pad or REF_CELL_PAD) * 2
    local icon = layout.icon_size or REF_ICON_SIZE
    local gap = layout.icon_gap or REF_ICON_GAP
    return text_w + pad + icon + gap
end

function A:_position_counters()
    if not self._layout_cache then return end
    local layout = self._layout_cache
    local h_tw = self:_measure_text_w(self._hostages_prim)
    local c_tw = self:_measure_text_w(self._converted_prim)
    local h_cw = self:_cell_width(h_tw)
    local c_cw = self:_cell_width(c_tw)
    local cg = layout.cell_gap or REF_CELL_GAP
    local cy = layout.counter_y
    local ch = layout.counter_h
    local rw = layout.root_w
    local pad = layout.cell_pad or REF_CELL_PAD
    local isz = layout.icon_size or REF_ICON_SIZE
    local igap = layout.icon_gap or REF_ICON_GAP

    local c_x = rw - c_cw
    local h_x = c_x - cg - h_cw

    if self._converted_bg and a_panel_alive(self._converted_bg) then
        a_safe_call(self._converted_bg, "set_shape", c_x, cy, c_cw, ch)
    end
    if self._hostages_bg and a_panel_alive(self._hostages_bg) then
        a_safe_call(self._hostages_bg, "set_shape", h_x, cy, h_cw, ch)
    end

    local text_y = cy
    local text_h = ch

    if self._converted_prim and a_panel_alive(self._converted_prim) then
        local tx = c_x + pad + isz + igap
        a_safe_call(self._converted_prim, "set_shape", tx, text_y, c_tw, text_h)
    end
    if self._hostages_prim and a_panel_alive(self._hostages_prim) then
        local tx = h_x + pad + isz + igap
        a_safe_call(self._hostages_prim, "set_shape", tx, text_y, h_tw, text_h)
    end

    local icon_y = cy + math.floor((ch - isz) / 2)
    if icon_y < cy then icon_y = cy end

    if self._converted_icon and a_panel_alive(self._converted_icon) then
        a_safe_call(self._converted_icon, "set_shape", c_x + pad, icon_y, isz, isz)
    end
    if self._hostages_icon and a_panel_alive(self._hostages_icon) then
        a_safe_call(self._hostages_icon, "set_shape", h_x + pad, icon_y, isz, isz)
    end
end

function A:_ensure_hostages_bg()
    if self._hostages_bg and a_panel_alive(self._hostages_bg) then return end
    if not self._root_panel or not a_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    a_init_colors()
    local layout = self._layout_cache
    local h_tw = self:_measure_text_w(self._hostages_prim)
    local cw = self:_cell_width(h_tw)
    local status, rect = a_safe_call(self._root_panel, "rect", {
        name = HOSTAGES_BG_NAME,
        x = 0, y = layout.counter_y,
        w = cw, h = layout.counter_h,
        color = COLOR_CELL_BG,
        layer = 1,
    })
    if status == a_call_ok and rect then
        self._hostages_bg = rect
    end
end

function A:_ensure_converted_bg()
    if self._converted_bg and a_panel_alive(self._converted_bg) then return end
    if not self._root_panel or not a_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    a_init_colors()
    local layout = self._layout_cache
    local c_tw = self:_measure_text_w(self._converted_prim)
    local cw = self:_cell_width(c_tw)
    local status, rect = a_safe_call(self._root_panel, "rect", {
        name = CONVERTED_BG_NAME,
        x = layout.root_w - cw, y = layout.counter_y,
        w = cw, h = layout.counter_h,
        color = COLOR_CELL_BG,
        layer = 1,
    })
    if status == a_call_ok and rect then
        self._converted_bg = rect
    end
end

function A:_ensure_hostages_icon()
    if self._hostages_icon and a_panel_alive(self._hostages_icon) then return end
    if not self._root_panel or not a_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    if not a_texture_available(TEX_HOSTAGE) then return end
    local layout = self._layout_cache
    local isz = layout.icon_size or REF_ICON_SIZE
    local status, prim = a_safe_call(self._root_panel, "bitmap", {
        name = HOSTAGES_ICON_NAME,
        texture = TEX_HOSTAGE,
        x = 0, y = layout.counter_y,
        w = isz, h = isz,
        layer = 2,
    })
    if status == a_call_ok and prim then
        self._hostages_icon = prim
    end
end

function A:_ensure_converted_icon()
    if self._converted_icon and a_panel_alive(self._converted_icon) then return end
    if not self._root_panel or not a_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    if not a_texture_available(TEX_CONVERTED) then return end
    local layout = self._layout_cache
    local isz = layout.icon_size or REF_ICON_SIZE
    local status, prim = a_safe_call(self._root_panel, "bitmap", {
        name = CONVERTED_ICON_NAME,
        texture = TEX_CONVERTED,
        texture_rect = TEX_CONVERTED_RECT,
        x = 0, y = layout.counter_y,
        w = isz, h = isz,
        layer = 2,
    })
    if status == a_call_ok and prim then
        self._converted_icon = prim
    end
end

function A:_ensure_primitives()
    self:_ensure_bg_rect()
    self:_ensure_ticker_panel()
    self:_ensure_ticker_texts()
    self:_ensure_glyph_prim()
    self:_ensure_hostages_prim()
    self:_ensure_converted_prim()
    self:_ensure_hostages_bg()
    self:_ensure_converted_bg()
    self:_ensure_hostages_icon()
    self:_ensure_converted_icon()
    self:_position_counters()
end

function A:_sync_bg_rect()
    if not self._bg_rect or not a_panel_alive(self._bg_rect) then return end
    if not self._layout_cache then return end
    a_init_colors()
    local endless = self._state.endless == true
    local key = endless and "endless" or "normal"
    local bg = self._layout_cache.bg or self._layout_cache.ticker
    local s_x, ax = a_safe_call(self._bg_rect, "x")
    local s_y, ay = a_safe_call(self._bg_rect, "y")
    local s_w, aw = a_safe_call(self._bg_rect, "w")
    local s_h, ah = a_safe_call(self._bg_rect, "h")
    if s_x == a_call_ok and s_y == a_call_ok and s_w == a_call_ok and s_h == a_call_ok
        and a_is_finite(ax) and a_is_finite(ay) and a_is_finite(aw) and a_is_finite(ah) then
        if math.abs(ax - bg.x) > 0.5 or math.abs(ay - bg.y) > 0.5
            or math.abs(aw - bg.w) > 0.5 or math.abs(ah - bg.h) > 0.5 then
            a_safe_call(self._bg_rect, "set_shape", bg.x, bg.y, bg.w, bg.h)
        end
    end
    local color = endless and COLOR_TICKER_BG_ENDLESS or COLOR_TICKER_BG_NORMAL
    local r, g, b, alpha = a_read_color(self._bg_rect)
    local exp_r = endless and 1.0 or 0.949
    local exp_g = endless and 0.165 or 0.890
    local exp_b = endless and 0.333 or 0.106
    if r and (math.abs(r - exp_r) > 0.01 or math.abs(g - exp_g) > 0.01
        or math.abs(b - exp_b) > 0.01 or math.abs(alpha - 1) > 0.02) then
        a_safe_call(self._bg_rect, "set_color", color)
    end
    local ok_v, vis = pcall(function() return self._bg_rect:visible() end)
    if ok_v and vis ~= true then
        a_safe_call(self._bg_rect, "set_visible", true)
    end
    self._cached_bg_key = key
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
    local es = (self._layout_cache and self._layout_cache.es) or 1
    local desired_gap = REF_TICKER_GAP * es
    if not self._ticker_gap or math.abs(self._ticker_gap - desired_gap) > 0.5 then
        self._ticker_gap = desired_gap
        needs_measure = true
    end
    if needs_measure then
        local ok_mr, mx, my, mw, mh = pcall(function() return self._ticker_a:text_rect() end)
        if ok_mr and a_is_finite(mw) and mw > 0 then
            self._ticker_measured_w = mw
            local ticker_h = (self._layout_cache and self._layout_cache.ticker and self._layout_cache.ticker.h) or REF_TICKER_H
            local ax = self._ticker_x_a or 0
            a_safe_call(self._ticker_a, "set_shape", ax, 0, mw, ticker_h)
            local gap = self._ticker_gap or desired_gap
            local bx = ax + mw + gap
            self._ticker_x_b = bx
            a_safe_call(self._ticker_b, "set_shape", bx, 0, mw, ticker_h)
        end
    end
    local ticker_h = (self._layout_cache and self._layout_cache.ticker and self._layout_cache.ticker.h) or REF_TICKER_H
    local mw = self._ticker_measured_w or 0
    local s_ax, rax = a_safe_call(self._ticker_a, "x")
    local s_ay, ray = a_safe_call(self._ticker_a, "y")
    local s_aw, raw = a_safe_call(self._ticker_a, "w")
    local s_ah, rah = a_safe_call(self._ticker_a, "h")
    if s_ax == a_call_ok and s_ay == a_call_ok and s_aw == a_call_ok and s_ah == a_call_ok
        and a_is_finite(rax) and a_is_finite(ray) and a_is_finite(raw) and a_is_finite(rah) then
        if math.abs(ray - 0) > 0.5 or math.abs(rah - ticker_h) > 0.5
            or (mw > 0 and math.abs(raw - mw) > 0.5) then
            a_safe_call(self._ticker_a, "set_shape", rax, 0, mw > 0 and mw or raw, ticker_h)
        end
    end
    local s_bx, rbx = a_safe_call(self._ticker_b, "x")
    local s_by, rby = a_safe_call(self._ticker_b, "y")
    local s_bw, rbw = a_safe_call(self._ticker_b, "w")
    local s_bh, rbh = a_safe_call(self._ticker_b, "h")
    if s_bx == a_call_ok and s_by == a_call_ok and s_bw == a_call_ok and s_bh == a_call_ok
        and a_is_finite(rbx) and a_is_finite(rby) and a_is_finite(rbw) and a_is_finite(rbh) then
        if math.abs(rby - 0) > 0.5 or math.abs(rbh - ticker_h) > 0.5
            or (mw > 0 and math.abs(rbw - mw) > 0.5) then
            local desired_bx = self._ticker_x_b or ((rax or 0) + mw + (self._ticker_gap or REF_TICKER_GAP))
            a_safe_call(self._ticker_b, "set_shape", desired_bx, 0, mw > 0 and mw or rbw, ticker_h)
        end
    end
end

function A:_sync_glyph_texture()
    if not self._glyph_prim or not a_panel_alive(self._glyph_prim) then return end
    local endless = self._state.endless == true
    local tex = a_resolve_status_texture(endless)
    if not tex then return end
    local needs_set = (tex ~= self._cached_status_texture)
    if not needs_set then
        local ok_gt, gt = pcall(function() return self._glyph_prim:texture_name() end)
        if ok_gt and not a_texture_matches(gt, tex) then
            needs_set = true
        end
    end
    if needs_set then
        local ok_set = pcall(function() self._glyph_prim:set_image(tex) end)
        if ok_set then
            local ok_r, actual = pcall(function() return self._glyph_prim:texture_name() end)
            if ok_r and a_texture_matches(actual, tex) then
                self._cached_status_texture = tex
            end
        end
    end
    local ok_v, vis = pcall(function() return self._glyph_prim:visible() end)
    if ok_v and vis ~= true then
        a_safe_call(self._glyph_prim, "set_visible", true)
    end
end

function A:_sync_hostages_text()
    if not self._hostages_prim or not a_panel_alive(self._hostages_prim) then return end
    local new_text = self:_resolve_hostages_text()
    local changed = false
    if new_text ~= self._cached_hostages_text then
        a_safe_call(self._hostages_prim, "set_text", new_text)
        local ok_r, r = pcall(function() return self._hostages_prim:text() end)
        if ok_r and r == new_text then
            self._cached_hostages_text = new_text
            changed = true
        end
    else
        local ok_a, actual = pcall(function() return self._hostages_prim:text() end)
        if ok_a and type(actual) == "string" and actual ~= new_text then
            a_safe_call(self._hostages_prim, "set_text", new_text)
            changed = true
        end
    end
    if changed then self:_position_counters() end
end

function A:_sync_converted_text()
    if not self._converted_prim or not a_panel_alive(self._converted_prim) then return end
    local new_text = self:_resolve_converted_text()
    local changed = false
    if new_text ~= self._cached_converted_text then
        a_safe_call(self._converted_prim, "set_text", new_text)
        local ok_r, r = pcall(function() return self._converted_prim:text() end)
        if ok_r and r == new_text then
            self._cached_converted_text = new_text
            changed = true
        end
    else
        local ok_a, actual = pcall(function() return self._converted_prim:text() end)
        if ok_a and type(actual) == "string" and actual ~= new_text then
            a_safe_call(self._converted_prim, "set_text", new_text)
            changed = true
        end
    end
    if changed then self:_position_counters() end
end

function A:_sync_text_colors()
    a_init_colors()
    local endless = self._state.endless == true
    local key = endless and "endless" or "normal"
    local ticker_color = endless and COLOR_TICKER_INK_ENDLESS or COLOR_TICKER_INK_NORMAL
    local exp_tr, exp_tg, exp_tb = endless and 1 or 0.067, endless and 1 or 0.067, endless and 1 or 0.067
    local exp_ta = 1
    local pr, pg, pb, pa = a_read_color(self._ticker_a)
    if pr and (math.abs(pr - exp_tr) > 0.01 or math.abs(pg - exp_tg) > 0.01
        or math.abs(pb - exp_tb) > 0.01 or math.abs(pa - exp_ta) > 0.02) then
        a_safe_call(self._ticker_a, "set_color", ticker_color)
    end
    pr, pg, pb, pa = a_read_color(self._ticker_b)
    if pr and (math.abs(pr - exp_tr) > 0.01 or math.abs(pg - exp_tg) > 0.01
        or math.abs(pb - exp_tb) > 0.01 or math.abs(pa - exp_ta) > 0.02) then
        a_safe_call(self._ticker_b, "set_color", ticker_color)
    end
    local exp_cr, exp_cg, exp_cb = 0.788, 0.820, 0.847
    pr, pg, pb, pa = a_read_color(self._converted_prim)
    if pr and (math.abs(pr - exp_cr) > 0.01 or math.abs(pg - exp_cg) > 0.01
        or math.abs(pb - exp_cb) > 0.01 or math.abs(pa - 1) > 0.02) then
        a_safe_call(self._converted_prim, "set_color", COLOR_COUNTER_INK)
    end
    pr, pg, pb, pa = a_read_color(self._hostages_prim)
    if pr and (math.abs(pr - exp_cr) > 0.01 or math.abs(pg - exp_cg) > 0.01
        or math.abs(pb - exp_cb) > 0.01 or math.abs(pa - 1) > 0.02) then
        a_safe_call(self._hostages_prim, "set_color", COLOR_COUNTER_INK)
    end
    self._cached_text_color_key = key
end

function A:_sync_primitives()
    self:_sync_bg_rect()
    self:_sync_ticker_text()
    self:_sync_glyph_texture()
    self:_sync_hostages_text()
    self:_sync_converted_text()
    self:_sync_text_colors()
    self:_position_counters()
    self:_sync_icon_states()
end

function A:_sync_icon_states()
    a_init_colors()
    local function restore_style(p, color, layer)
        if not p or not a_panel_alive(p) then return end
        local r,g,b,alpha = a_read_color(p)
        local ok, same = pcall(function()
            return r and math.abs(r-color.r)<.001 and math.abs(g-color.g)<.001
                and math.abs(b-color.b)<.001 and math.abs(alpha-color.a)<.001
                and p:layer()==layer and p:visible()==true
        end)
        if not ok or not same then
            a_safe_call(p,"set_color",color)
            a_safe_call(p,"set_alpha",color.a)
            a_safe_call(p,"set_layer",layer)
            a_safe_call(p,"set_visible",true)
        end
    end
    restore_style(self._hostages_bg,COLOR_CELL_BG,1)
    restore_style(self._converted_bg,COLOR_CELL_BG,1)
    restore_style(self._hostages_icon,COLOR_TICKER_INK_ENDLESS,2)
    restore_style(self._converted_icon,COLOR_TICKER_INK_ENDLESS,2)
    restore_style(self._glyph_prim,COLOR_TICKER_INK_ENDLESS,1)
    if self._hostages_icon and a_panel_alive(self._hostages_icon) then
        local ok_v, v = pcall(function() return self._hostages_icon:visible() end)
        if ok_v and v ~= true then
            a_safe_call(self._hostages_icon, "set_visible", true)
        end
        local ok_tex, tex = pcall(function() return self._hostages_icon:texture_name() end)
        if ok_tex and not a_texture_matches(tex, TEX_HOSTAGE) then
            a_safe_call(self._hostages_icon, "set_image", TEX_HOSTAGE)
        end
    end
    if self._converted_icon and a_panel_alive(self._converted_icon) then
        local ok_v, v = pcall(function() return self._converted_icon:visible() end)
        if ok_v and v ~= true then
            a_safe_call(self._converted_icon, "set_visible", true)
        end
        local ok_tex, tex = pcall(function() return self._converted_icon:texture_name() end)
        if ok_tex and not a_texture_matches(tex, TEX_CONVERTED) then
            a_safe_call(self._converted_icon, "set_image", TEX_CONVERTED)
        end
        -- Native Bitmap has no texture_rect getter. Reapply the atlas crop at
        -- the existing bounded poll instead of certifying a fictional readback.
        a_safe_call(self._converted_icon,"set_texture_rect",TEX_CONVERTED_RECT[1],
            TEX_CONVERTED_RECT[2],TEX_CONVERTED_RECT[3],TEX_CONVERTED_RECT[4])
    end
    if self._hostages_bg and a_panel_alive(self._hostages_bg) then
        local ok_v, v = pcall(function() return self._hostages_bg:visible() end)
        if ok_v and v ~= true then
            a_safe_call(self._hostages_bg, "set_visible", true)
        end
    end
    if self._converted_bg and a_panel_alive(self._converted_bg) then
        local ok_v, v = pcall(function() return self._converted_bg:visible() end)
        if ok_v and v ~= true then
            a_safe_call(self._converted_bg, "set_visible", true)
        end
    end
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
    if cycle <= 0 then return end
    ax = -(((-ax) % cycle))
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
    local old = self._layout_cache
    local changed = not old or
        old.root_x ~= new_layout.root_x or
        old.root_y ~= new_layout.root_y or
        old.root_w ~= new_layout.root_w or
        old.root_h ~= new_layout.root_h or
        old.ticker_font ~= new_layout.ticker_font or
        old.counter_font ~= new_layout.counter_font
    if not changed then
        self:_repair_layout_shapes(new_layout)
        return
    end
    a_safe_call(self._root_panel, "set_shape", new_layout.root_x, new_layout.root_y, new_layout.root_w, new_layout.root_h)
    local bg = new_layout.bg or new_layout.ticker
    if self._bg_rect and a_panel_alive(self._bg_rect) then
        a_safe_call(self._bg_rect, "set_shape", bg.x, bg.y, bg.w, bg.h)
    end
    if self._ticker_panel and a_panel_alive(self._ticker_panel) then
        a_safe_call(self._ticker_panel, "set_shape", new_layout.ticker.x, new_layout.ticker.y, new_layout.ticker.w, new_layout.ticker.h)
    end
    if self._glyph_prim and a_panel_alive(self._glyph_prim) and new_layout.status then
        a_safe_call(self._glyph_prim, "set_shape", new_layout.status.x, new_layout.status.y, new_layout.status.w, new_layout.status.h)
    end
    if self._ticker_a and a_panel_alive(self._ticker_a) then
        a_safe_call(self._ticker_a, "set_font_size", new_layout.ticker_font)
    end
    if self._ticker_b and a_panel_alive(self._ticker_b) then
        a_safe_call(self._ticker_b, "set_font_size", new_layout.ticker_font)
    end
    if self._hostages_prim and a_panel_alive(self._hostages_prim) then
        a_safe_call(self._hostages_prim, "set_font_size", new_layout.counter_font)
    end
    if self._converted_prim and a_panel_alive(self._converted_prim) then
        a_safe_call(self._converted_prim, "set_font_size", new_layout.counter_font)
    end
    self._layout_cache = new_layout
    self._ticker_gap = REF_TICKER_GAP * (new_layout.es or 1)
    if self._ticker_a and a_panel_alive(self._ticker_a) then
        local ok_mr, mx, my, mw, mh = pcall(function() return self._ticker_a:text_rect() end)
        if ok_mr and a_is_finite(mw) and mw > 0 then
            self._ticker_measured_w = mw
            local ticker_h = new_layout.ticker.h
            local ax = self._ticker_x_a or 0
            a_safe_call(self._ticker_a, "set_shape", ax, 0, mw, ticker_h)
            local gap = self._ticker_gap or (REF_TICKER_GAP * (new_layout.es or 1))
            local bx = ax + mw + gap
            self._ticker_x_b = bx
            a_safe_call(self._ticker_b, "set_shape", bx, 0, mw, ticker_h)
        end
    end
    self:_position_counters()
    self:_repair_layout_shapes(new_layout)
end

function A:_repair_layout_shapes(layout)
    if not layout then return end
    local function repair(p, x, y, w, h)
        if not p or not a_panel_alive(p) then return end
        local ok, same = pcall(function()
            return p:x() == x and p:y() == y and p:w() == w and p:h() == h
        end)
        if not ok or not same then a_safe_call(p, "set_shape", x, y, w, h) end
    end
    repair(self._root_panel, layout.root_x, layout.root_y, layout.root_w, layout.root_h)
    repair(self._ticker_a, self._ticker_x_a, 0, self._ticker_measured_w, layout.ticker.h)
    repair(self._ticker_b, self._ticker_x_b, 0, self._ticker_measured_w, layout.ticker.h)
    local bg = layout.bg or layout.ticker
    if self._bg_rect and a_panel_alive(self._bg_rect) then
        local s_x, ax = a_safe_call(self._bg_rect, "x")
        local s_y, ay = a_safe_call(self._bg_rect, "y")
        local s_w, aw = a_safe_call(self._bg_rect, "w")
        local s_h, ah = a_safe_call(self._bg_rect, "h")
        if s_x == a_call_ok and s_y == a_call_ok and s_w == a_call_ok and s_h == a_call_ok
            and a_is_finite(ax) and a_is_finite(ay) and a_is_finite(aw) and a_is_finite(ah) then
            if math.abs(ax - bg.x) > 0.5 or math.abs(ay - bg.y) > 0.5
                or math.abs(aw - bg.w) > 0.5 or math.abs(ah - bg.h) > 0.5 then
                a_safe_call(self._bg_rect, "set_shape", bg.x, bg.y, bg.w, bg.h)
            end
        end
    end
    if self._ticker_panel and a_panel_alive(self._ticker_panel) then
        local s_x, tx = a_safe_call(self._ticker_panel, "x")
        local s_y, ty = a_safe_call(self._ticker_panel, "y")
        local s_w, tw = a_safe_call(self._ticker_panel, "w")
        local s_h, th = a_safe_call(self._ticker_panel, "h")
        if s_x == a_call_ok and s_y == a_call_ok and s_w == a_call_ok and s_h == a_call_ok
            and a_is_finite(tx) and a_is_finite(ty) and a_is_finite(tw) and a_is_finite(th) then
            if math.abs(tx - layout.ticker.x) > 0.5 or math.abs(ty - layout.ticker.y) > 0.5
                or math.abs(tw - layout.ticker.w) > 0.5 or math.abs(th - layout.ticker.h) > 0.5 then
                a_safe_call(self._ticker_panel, "set_shape", layout.ticker.x, layout.ticker.y, layout.ticker.w, layout.ticker.h)
            end
        end
    end
    if self._glyph_prim and a_panel_alive(self._glyph_prim) and layout.status then
        local s_x, gx = a_safe_call(self._glyph_prim, "x")
        local s_y, gy = a_safe_call(self._glyph_prim, "y")
        local s_w, gw = a_safe_call(self._glyph_prim, "w")
        local s_h, gh = a_safe_call(self._glyph_prim, "h")
        if s_x == a_call_ok and s_y == a_call_ok and s_w == a_call_ok and s_h == a_call_ok
            and a_is_finite(gx) and a_is_finite(gy) and a_is_finite(gw) and a_is_finite(gh) then
            if math.abs(gx - layout.status.x) > 0.5 or math.abs(gy - layout.status.y) > 0.5
                or math.abs(gw - layout.status.w) > 0.5 or math.abs(gh - layout.status.h) > 0.5 then
                a_safe_call(self._glyph_prim, "set_shape", layout.status.x, layout.status.y, layout.status.w, layout.status.h)
            end
        end
    end
    local ticker_h = layout.ticker.h
    local mw = self._ticker_measured_w or 0
    if self._ticker_a and a_panel_alive(self._ticker_a) then
        local s_y, ay = a_safe_call(self._ticker_a, "y")
        local s_h, ah = a_safe_call(self._ticker_a, "h")
        local s_w, aw = a_safe_call(self._ticker_a, "w")
        if s_y == a_call_ok and s_h == a_call_ok and a_is_finite(ay) and a_is_finite(ah) then
            if math.abs(ay - 0) > 0.5 or math.abs(ah - ticker_h) > 0.5
                or (mw > 0 and a_is_finite(aw) and math.abs(aw - mw) > 0.5) then
                local s_x, ax = a_safe_call(self._ticker_a, "x")
                local cax = (s_x == a_call_ok and a_is_finite(ax)) and ax or (self._ticker_x_a or 0)
                a_safe_call(self._ticker_a, "set_shape", cax, 0, mw > 0 and mw or (a_is_finite(aw) and aw or layout.ticker.w), ticker_h)
            end
        end
    end
    if self._ticker_b and a_panel_alive(self._ticker_b) then
        local s_y, by = a_safe_call(self._ticker_b, "y")
        local s_h, bh = a_safe_call(self._ticker_b, "h")
        local s_w, bw = a_safe_call(self._ticker_b, "w")
        if s_y == a_call_ok and s_h == a_call_ok and a_is_finite(by) and a_is_finite(bh) then
            if math.abs(by - 0) > 0.5 or math.abs(bh - ticker_h) > 0.5
                or (mw > 0 and a_is_finite(bw) and math.abs(bw - mw) > 0.5) then
                local desired_bx = self._ticker_x_b or 0
                a_safe_call(self._ticker_b, "set_shape", desired_bx, 0, mw > 0 and mw or (a_is_finite(bw) and bw or layout.ticker.w), ticker_h)
            end
        end
    end
end

function A:_verify_render()
    if not self._layout_cache then
        self._render_verified = false
        return false
    end
    local geom = self._layout_cache
    if not a_is_finite(geom.root_w) or not a_is_finite(geom.root_h) then
        self._render_verified = false
        return false
    end
    if not a_is_finite(geom.ticker_font) or not a_is_finite(geom.counter_font) then
        self._render_verified = false
        return false
    end
    if geom.root_w <= 0 or geom.root_h <= 0 or geom.ticker_font <= 0 or geom.counter_font <= 0 then
        self._render_verified = false
        return false
    end
    if not self._root_panel or not a_panel_alive(self._root_panel) then
        self._render_verified = false
        return false
    end
    local ok_parent, owned_parent = pcall(function() return self._root_panel:parent() end)
    if not ok_parent or owned_parent~=self._parent_panel then
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
    if not self._hostages_bg or not a_panel_alive(self._hostages_bg) then
        self._render_verified = false
        return false
    end
    if not self._converted_bg or not a_panel_alive(self._converted_bg) then
        self._render_verified = false
        return false
    end
    if not self._hostages_icon or not a_panel_alive(self._hostages_icon) then
        self._render_verified = false
        return false
    end
    if not self._converted_icon or not a_panel_alive(self._converted_icon) then
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
    local bg_geom = geom.bg or geom.ticker
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
    if math.abs(bg_x - bg_geom.x) > tol or math.abs(bg_y - bg_geom.y) > tol
        or math.abs(bg_w - bg_geom.w) > tol or math.abs(bg_h - bg_geom.h) > tol then
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
    local function check_text(prim, desired, expected_fs, skip_x, skip_y, region_y, region_h)
        local ok_v, v = pcall(function() return prim:visible() end)
        if not ok_v or v ~= true then return false end
        local ok_t, t = pcall(function() return prim:text() end)
        if not ok_t or type(t) ~= "string" then return false end
        if t ~= desired then return false end
        local ok_fs, fs = pcall(function() return prim:font_size() end)
        if not ok_fs or not a_is_finite(fs) or fs <= 0 then return false end
        if math.abs(fs - expected_fs) > 0.5 then return false end
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
        if not skip_y and region_y then
            if math.abs(py - region_y) > tol then return false end
        end
        if region_h and math.abs(ph - region_h) > tol then return false end
        local ok_mr, mr_x, mr_y, mw, mh = pcall(function() return prim:text_rect() end)
        if not ok_mr then return false end
        if not a_is_finite(mw) or not a_is_finite(mh) then return false end
        if mw <= 0 or mh <= 0 then return false end
        if mh > ph + tol then return false end
        return true
    end
    if not check_text(self._ticker_a, desired_ticker, geom.ticker_font, true, false, 0, geom.ticker.h) then
        self._render_verified = false
        return false
    end
    local ok_tax, tax = a_safe_call(self._ticker_a, "x")
    if ok_tax ~= a_call_ok or not a_is_finite(tax) then
        self._render_verified = false
        return false
    end
    local s_taw, taw = a_safe_call(self._ticker_a, "w")
    if s_taw == a_call_ok and a_is_finite(taw) and (self._ticker_measured_w or 0) > 0 then
        if math.abs(taw - self._ticker_measured_w) > 1.5 then
            self._render_verified = false
            return false
        end
    end
    local cycle = (self._ticker_measured_w or 0) + (self._ticker_gap or (REF_TICKER_GAP * (geom.es or 1)))
    if cycle > 0 then
        local tracked_ax = self._ticker_x_a or 0
        if math.abs(tax - tracked_ax) > 1.5 then
            self._render_verified = false
            return false
        end
        if tax > 0.5 or tax < -cycle - 0.5 then
            self._render_verified = false
            return false
        end
    end
    if not check_text(self._ticker_b, desired_ticker, geom.ticker_font, true, false, 0, geom.ticker.h) then
        self._render_verified = false
        return false
    end
    local ok_tbx, tbx = a_safe_call(self._ticker_b, "x")
    if ok_tbx ~= a_call_ok or not a_is_finite(tbx) then
        self._render_verified = false
        return false
    end
    local s_tbw, tbw = a_safe_call(self._ticker_b, "w")
    if s_tbw == a_call_ok and a_is_finite(tbw) and (self._ticker_measured_w or 0) > 0 then
        if math.abs(tbw - self._ticker_measured_w) > 1.5 then
            self._render_verified = false
            return false
        end
    end
    if cycle > 0 then
        local tracked_bx = self._ticker_x_b or 0
        if math.abs(tbx - tracked_bx) > 1.5 then
            self._render_verified = false
            return false
        end
        local expected_bx = tax + cycle
        if math.abs(tbx - expected_bx) > tol then
            self._render_verified = false
            return false
        end
    end
    local desired_tex = self._cached_status_texture
    if type(desired_tex) ~= "string" or desired_tex == "" then
        self._render_verified = false
        return false
    end
    local ok_gv, gv = pcall(function() return self._glyph_prim:visible() end)
    if not ok_gv or gv ~= true then
        self._render_verified = false
        return false
    end
    if geom.status then
        local gx_s, gx = a_safe_call(self._glyph_prim, "x")
        local gy_s, gy = a_safe_call(self._glyph_prim, "y")
        local gw_s, gw = a_safe_call(self._glyph_prim, "w")
        local gh_s, gh = a_safe_call(self._glyph_prim, "h")
        if gx_s ~= a_call_ok or gy_s ~= a_call_ok or gw_s ~= a_call_ok or gh_s ~= a_call_ok then
            self._render_verified = false
            return false
        end
        if not a_is_finite(gx) or not a_is_finite(gy) or not a_is_finite(gw) or not a_is_finite(gh) then
            self._render_verified = false
            return false
        end
        if math.abs(gx - geom.status.x) > tol or math.abs(gy - geom.status.y) > tol
            or math.abs(gw - geom.status.w) > tol or math.abs(gh - geom.status.h) > tol then
            self._render_verified = false
            return false
        end
    end
    local ok_gt, gt = pcall(function() return self._glyph_prim:texture_name() end)
    if not ok_gt or gt == nil then
        self._render_verified = false
        return false
    end
    if not a_texture_matches(gt, desired_tex) then
        self._render_verified = false
        return false
    end
    local desired_hostages = self._cached_hostages_text
    if type(desired_hostages) ~= "string" or desired_hostages == "" then
        self._render_verified = false
        return false
    end
    if not check_text(self._hostages_prim, desired_hostages, geom.counter_font, true, false, geom.counter_y, geom.counter_h) then
        self._render_verified = false
        return false
    end
    local desired_converted = self._cached_converted_text
    if type(desired_converted) ~= "string" or desired_converted == "" then
        self._render_verified = false
        return false
    end
    if not check_text(self._converted_prim, desired_converted, geom.counter_font, true, false, geom.counter_y, geom.counter_h) then
        self._render_verified = false
        return false
    end
    a_init_colors()
    local function check_color_rgba(prim, exp_r, exp_g, exp_b, exp_a)
        if not prim or not a_panel_alive(prim) then return false end
        local r, g, b, a = a_read_color(prim)
        if not r then return false end
        if math.abs(r - exp_r) > 0.01 then return false end
        if math.abs(g - exp_g) > 0.01 then return false end
        if math.abs(b - exp_b) > 0.01 then return false end
        if math.abs(a - exp_a) > 0.02 then return false end
        return true
    end
    local endless = self._state.endless == true
    local exp_bg_r = endless and 1.0 or 0.949
    local exp_bg_g = endless and 0.165 or 0.890
    local exp_bg_b = endless and 0.333 or 0.106
    if not check_color_rgba(self._bg_rect, exp_bg_r, exp_bg_g, exp_bg_b, 1) then
        self._render_verified = false
        return false
    end
    if not check_color_rgba(self._hostages_bg, 0.043, 0.051, 0.067, 0.75) then
        self._render_verified = false
        return false
    end
    if not check_color_rgba(self._converted_bg, 0.043, 0.051, 0.067, 0.75) then
        self._render_verified = false
        return false
    end
    local exp_ticker_r = endless and 1 or 0.067
    local exp_ticker_g = endless and 1 or 0.067
    local exp_ticker_b = endless and 1 or 0.067
    local exp_ticker_a = endless and 1 or 1
    if not check_color_rgba(self._ticker_a, exp_ticker_r, exp_ticker_g, exp_ticker_b, exp_ticker_a) then
        self._render_verified = false
        return false
    end
    if not check_color_rgba(self._ticker_b, exp_ticker_r, exp_ticker_g, exp_ticker_b, exp_ticker_a) then
        self._render_verified = false
        return false
    end
    if not check_color_rgba(self._hostages_prim, 0.788, 0.820, 0.847, 1) then
        self._render_verified = false
        return false
    end
    if not check_color_rgba(self._converted_prim, 0.788, 0.820, 0.847, 1) then
        self._render_verified = false
        return false
    end
    if not check_color_rgba(self._glyph_prim,1,1,1,1) then
        self._render_verified = false
        return false
    end
    if not check_color_rgba(self._hostages_icon,1,1,1,1) then
        self._render_verified = false
        return false
    end
    if not check_color_rgba(self._converted_icon,1,1,1,1) then
        self._render_verified = false
        return false
    end
    local function check_visible_explicit(prim)
        if not prim or not a_panel_alive(prim) then return false end
        local ok_v, v = pcall(function() return prim:visible() end)
        if not ok_v or v ~= true then return false end
        return true
    end
    if not check_visible_explicit(self._hostages_bg) then
        self._render_verified = false
        return false
    end
    if not check_visible_explicit(self._converted_bg) then
        self._render_verified = false
        return false
    end
    if not check_visible_explicit(self._hostages_icon) then
        self._render_verified = false
        return false
    end
    if not check_visible_explicit(self._converted_icon) then
        self._render_verified = false
        return false
    end
    local hbg_x_s, hbg_x = a_safe_call(self._hostages_bg, "x")
    local hbg_y_s, hbg_y = a_safe_call(self._hostages_bg, "y")
    local hbg_w_s, hbg_w = a_safe_call(self._hostages_bg, "w")
    local hbg_h_s, hbg_h = a_safe_call(self._hostages_bg, "h")
    if hbg_x_s ~= a_call_ok or hbg_y_s ~= a_call_ok or hbg_w_s ~= a_call_ok or hbg_h_s ~= a_call_ok then
        self._render_verified = false
        return false
    end
    if not a_is_finite(hbg_x) or not a_is_finite(hbg_y) or not a_is_finite(hbg_w) or not a_is_finite(hbg_h) then
        self._render_verified = false
        return false
    end
    local cbg_x_s, cbg_x = a_safe_call(self._converted_bg, "x")
    local cbg_y_s, cbg_y = a_safe_call(self._converted_bg, "y")
    local cbg_w_s, cbg_w = a_safe_call(self._converted_bg, "w")
    local cbg_h_s, cbg_h = a_safe_call(self._converted_bg, "h")
    if cbg_x_s ~= a_call_ok or cbg_y_s ~= a_call_ok or cbg_w_s ~= a_call_ok or cbg_h_s ~= a_call_ok then
        self._render_verified = false
        return false
    end
    if not a_is_finite(cbg_x) or not a_is_finite(cbg_y) or not a_is_finite(cbg_w) or not a_is_finite(cbg_h) then
        self._render_verified = false
        return false
    end
    local h_tw = self:_measure_text_w(self._hostages_prim)
    local c_tw = self:_measure_text_w(self._converted_prim)
    local h_cw = self:_cell_width(h_tw)
    local c_cw = self:_cell_width(c_tw)
    local cg = geom.cell_gap or REF_CELL_GAP
    local rw = geom.root_w
    local expected_c_x = rw - c_cw
    local expected_h_x = expected_c_x - cg - h_cw
    local expected_counter_y = geom.counter_y
    local expected_cell_h = geom.counter_h
    if math.abs(cbg_x - expected_c_x) > 1.5 then
        self._render_verified = false
        return false
    end
    if math.abs(cbg_y - expected_counter_y) > tol then
        self._render_verified = false
        return false
    end
    if math.abs(cbg_w - c_cw) > 1.5 then
        self._render_verified = false
        return false
    end
    if math.abs(cbg_h - expected_cell_h) > tol then
        self._render_verified = false
        return false
    end
    if math.abs(hbg_x - expected_h_x) > 1.5 then
        self._render_verified = false
        return false
    end
    if math.abs(hbg_y - expected_counter_y) > tol then
        self._render_verified = false
        return false
    end
    if math.abs(hbg_w - h_cw) > 1.5 then
        self._render_verified = false
        return false
    end
    if math.abs(hbg_h - expected_cell_h) > tol then
        self._render_verified = false
        return false
    end
    local hi_x_s, hi_x = a_safe_call(self._hostages_icon, "x")
    local hi_y_s, hi_y = a_safe_call(self._hostages_icon, "y")
    local hi_w_s, hi_w = a_safe_call(self._hostages_icon, "w")
    local hi_h_s, hi_h = a_safe_call(self._hostages_icon, "h")
    if hi_x_s ~= a_call_ok or hi_y_s ~= a_call_ok or hi_w_s ~= a_call_ok or hi_h_s ~= a_call_ok then
        self._render_verified = false
        return false
    end
    if not a_is_finite(hi_x) or not a_is_finite(hi_y) or not a_is_finite(hi_w) or not a_is_finite(hi_h) then
        self._render_verified = false
        return false
    end
    local ci_x_s, ci_x = a_safe_call(self._converted_icon, "x")
    local ci_y_s, ci_y = a_safe_call(self._converted_icon, "y")
    local ci_w_s, ci_w = a_safe_call(self._converted_icon, "w")
    local ci_h_s, ci_h = a_safe_call(self._converted_icon, "h")
    if ci_x_s ~= a_call_ok or ci_y_s ~= a_call_ok or ci_w_s ~= a_call_ok or ci_h_s ~= a_call_ok then
        self._render_verified = false
        return false
    end
    if not a_is_finite(ci_x) or not a_is_finite(ci_y) or not a_is_finite(ci_w) or not a_is_finite(ci_h) then
        self._render_verified = false
        return false
    end
    local pad = geom.cell_pad or REF_CELL_PAD
    local isz = geom.icon_size or REF_ICON_SIZE
    local expected_icon_y = expected_counter_y + math.floor((expected_cell_h - isz) / 2)
    if expected_icon_y < expected_counter_y then expected_icon_y = expected_counter_y end
    local expected_hi_x = expected_h_x + pad
    local expected_ci_x = expected_c_x + pad
    local function counter_geometry(p, expected_x, width)
        local ok, same = pcall(function()
            return math.abs(p:x()-expected_x)<=tol and math.abs(p:w()-width)<=tol
                and p:parent()==self._root_panel
        end)
        return ok and same == true
    end
    if expected_h_x<0 or not counter_geometry(self._hostages_prim,
        expected_h_x+pad+isz+(geom.icon_gap or REF_ICON_GAP),h_tw)
        or not counter_geometry(self._converted_prim,
        expected_c_x+pad+isz+(geom.icon_gap or REF_ICON_GAP),c_tw) then
        self._render_verified = false
        return false
    end
    if math.abs(hi_x - expected_hi_x) > tol then
        self._render_verified = false
        return false
    end
    if math.abs(hi_y - expected_icon_y) > tol then
        self._render_verified = false
        return false
    end
    if math.abs(hi_w - isz) > tol then
        self._render_verified = false
        return false
    end
    if math.abs(hi_h - isz) > tol then
        self._render_verified = false
        return false
    end
    if math.abs(ci_x - expected_ci_x) > tol then
        self._render_verified = false
        return false
    end
    if math.abs(ci_y - expected_icon_y) > tol then
        self._render_verified = false
        return false
    end
    if math.abs(ci_w - isz) > tol then
        self._render_verified = false
        return false
    end
    if math.abs(ci_h - isz) > tol then
        self._render_verified = false
        return false
    end
    local ok_hi_tex, hi_tex = pcall(function() return self._hostages_icon:texture_name() end)
    if not ok_hi_tex or hi_tex == nil then
        self._render_verified = false
        return false
    end
    if not a_texture_matches(hi_tex, TEX_HOSTAGE) then
        self._render_verified = false
        return false
    end
    local ok_ci_tex, ci_tex = pcall(function() return self._converted_icon:texture_name() end)
    if not ok_ci_tex or ci_tex == nil then
        self._render_verified = false
        return false
    end
    if not a_texture_matches(ci_tex, TEX_CONVERTED) then
        self._render_verified = false
        return false
    end

    local function check_layer(prim, expected)
        if not prim or not a_panel_alive(prim) then return false end
        local ok_l, l = pcall(function() return prim:layer() end)
        if not ok_l or not a_is_finite(l) then return false end
        if math.abs(l - expected) > 0.001 then return false end
        return true
    end
    if not check_layer(self._bg_rect, 0) then
        self._render_verified = false
        return false
    end
    if not check_layer(self._ticker_panel, 1) then
        self._render_verified = false
        return false
    end
    if not check_layer(self._ticker_a, 1) then
        self._render_verified = false
        return false
    end
    if not check_layer(self._ticker_b, 1) then
        self._render_verified = false
        return false
    end
    if not check_layer(self._glyph_prim, 1) then
        self._render_verified = false
        return false
    end
    if not check_layer(self._hostages_bg, 1) then
        self._render_verified = false
        return false
    end
    if not check_layer(self._converted_bg, 1) then
        self._render_verified = false
        return false
    end
    if not check_layer(self._hostages_prim, 2) then
        self._render_verified = false
        return false
    end
    if not check_layer(self._converted_prim, 2) then
        self._render_verified = false
        return false
    end
    if not check_layer(self._hostages_icon, 2) then
        self._render_verified = false
        return false
    end
    if not check_layer(self._converted_icon, 2) then
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
    if kyohud.settings.enable_hud_foundation ~= true then
        return
    end
    if kyohud.settings.enable_assault ~= true then
        return
    end
    if a_is_vr() then
        return
    end
    local mgr = manager or self._manager
    if not mgr then
        return
    end
    self._manager = mgr
    local parent = a_get_runtime_root()
    if not parent then
        return
    end
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
        self._hostages_bg = nil
        self._converted_bg = nil
        self._hostages_icon = nil
        self._converted_icon = nil
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
    if status ~= a_call_ok then
        return
    end
    local cs, root = a_safe_call(parent, "panel", {name = ASSAULT_ROOT_NAME})
    if cs ~= a_call_ok or root == nil then
        return
    end
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
    self._hostages_bg = nil
    self._converted_bg = nil
    self._hostages_icon = nil
    self._converted_icon = nil
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
    self._cached_status_texture = nil
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
        self._hostages_bg = nil
        self._converted_bg = nil
        self._hostages_icon = nil
        self._converted_icon = nil
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
        self:_ensure_primitives()
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
