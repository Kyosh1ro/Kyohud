kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end

kyohud.hud = kyohud.hud or {}

local AL = kyohud.hud.alerts or {}
kyohud.hud.alerts = AL

AL._state = AL._state or {}
local S = AL._state
if S.active == nil then S.active = false end

local REQUIRED_CONTEXT = "lib/managers/hudmanagerpd2"

local ALERTS_ROOT_NAME = "kyohud_alerts_panel"
local PNR_TIMER_NAME = "pnr_timer"
local PNR_STATUS_NAME = "pnr_status"
local PNR_TITLE_NAME = "pnr_title"
local PNR_BG_NAME = "pnr_bg"
local PNR_ICON_NAME = "pnr_icon"
local PNR_STATUS_BG_NAME = "pnr_status_bg"

local REF_MARGIN_RIGHT = 40
local REF_TOP = 36
local REF_FONT_SIZE = 20
local MIN_FONT_SIZE = 12
local POLL_INTERVAL = 0.5
local REF_PNR_TITLE_X = 12
local REF_PNR_TIMER_RIGHT = 328
local REF_PNR_TITLE_GAP = 10
local REF_PNR_STATUS_FONT = 16
local REF_PNR_STATUS_PAD = 10

local CASING_ROOT_NAME = "kyohud_casing_panel"
local CASING_TICKER_NAME = "kyohud_casing_ticker"
local CASING_A_NAME = "kyohud_casing_a"
local CASING_B_NAME = "kyohud_casing_b"
local CASING_BG_NAME = "kyohud_casing_bg"
local CASING_ICON_NAME = "kyohud_casing_icon"
local REF_CASING_TICKER_W = 340
local REF_CASING_TICKER_SPEED = 60
local REF_CASING_TICKER_GAP = 40

local CALL_OK = "ok"
local CALL_MISSING = "missing"
local CALL_ERROR = "error"

kyohud.hud._installed_hooks = kyohud.hud._installed_hooks or {}

AL._mounted = AL._mounted or false
AL._root_panel = AL._root_panel
AL._parent_panel = AL._parent_panel
AL._manager = AL._manager
AL._timer_prim = AL._timer_prim
AL._status_prim = AL._status_prim
AL._title_prim = AL._title_prim
AL._layout_cache = AL._layout_cache
AL._render_verified = AL._render_verified or false
AL._render_failed = AL._render_failed or false
AL._last_poll_time = AL._last_poll_time
AL._snapshot_taken = AL._snapshot_taken or false
AL._cached_timer_text = AL._cached_timer_text
AL._cached_status_text = AL._cached_status_text
AL._cached_title_text = AL._cached_title_text
AL._cached_font = AL._cached_font
AL._cached_font_size = AL._cached_font_size

AL._native_corner = AL._native_corner
AL._native_bg_box = AL._native_bg_box
AL._native_hud_panel = AL._native_hud_panel
AL._native_targets = AL._native_targets
AL._native_requests = AL._native_requests
AL._native_acquired = AL._native_acquired or false
AL._native_generation = AL._native_generation or 0
AL._conflict_corner = AL._conflict_corner
AL._casing_conflict_corner = AL._casing_conflict_corner

AL._opening_identity = AL._opening_identity

AL._source = AL._source
AL._source_corner = AL._source_corner
AL._event_manager = AL._event_manager
AL._event_corner = AL._event_corner
AL._event_source = AL._event_source
AL._event_active = AL._event_active
AL._event_tweak_id = AL._event_tweak_id
AL._event_timer = AL._event_timer
AL._event_inside = AL._event_inside
AL._event_state_tweak = AL._event_state_tweak
AL._event_state_timer = AL._event_state_timer
AL._event_state_inside = AL._event_state_inside
AL._event_has_active = AL._event_has_active or false
AL._event_has_tweak = AL._event_has_tweak or false
AL._event_has_timer = AL._event_has_timer or false
AL._event_has_inside = AL._event_has_inside or false
AL._data_dirty = AL._data_dirty or false
AL._heist_manager_id = AL._heist_manager_id

AL._casing_root_panel = AL._casing_root_panel
AL._casing_ticker_panel = AL._casing_ticker_panel
AL._casing_a = AL._casing_a
AL._casing_b = AL._casing_b
AL._casing_mode = AL._casing_mode
AL._casing_active = AL._casing_active or false
AL._casing_layout_cache = AL._casing_layout_cache
AL._casing_render_verified = AL._casing_render_verified or false
AL._casing_render_failed = AL._casing_render_failed or false
AL._casing_cached_ticker_text = AL._casing_cached_ticker_text
AL._casing_cached_font = AL._casing_cached_font
AL._casing_cached_font_size = AL._casing_cached_font_size
AL._casing_x_a = AL._casing_x_a or 0
AL._casing_x_b = AL._casing_x_b or 0
AL._casing_measured_w = AL._casing_measured_w or 0
AL._casing_gap = AL._casing_gap
AL._casing_native_corner = AL._casing_native_corner
AL._casing_native_hud_panel = AL._casing_native_hud_panel
AL._casing_native_targets = AL._casing_native_targets
AL._casing_native_requests = AL._casing_native_requests
AL._casing_native_acquired = AL._casing_native_acquired or false
AL._casing_native_generation = AL._casing_native_generation or 0
AL._whisper_mode = AL._whisper_mode

AL._casing_bg = AL._casing_bg
AL._casing_icon = AL._casing_icon
AL._pnr_bg = AL._pnr_bg
AL._pnr_icon = AL._pnr_icon
AL._pnr_status_bg = AL._pnr_status_bg
AL._pnr_timer_measured_w = AL._pnr_timer_measured_w or 0

AL._casing_closing = AL._casing_closing or false
AL._casing_close_manager = AL._casing_close_manager
AL._casing_close_corner = AL._casing_close_corner
AL._casing_close_state = AL._casing_close_state
AL._casing_close_bg_box = AL._casing_close_bg_box
AL._casing_close_icon = AL._casing_close_icon
AL._casing_close_bg_done = AL._casing_close_bg_done or false
AL._casing_close_icon_done = AL._casing_close_icon_done or false
AL._casing_close_exit_alpha = AL._casing_close_exit_alpha
AL._casing_close_generation = AL._casing_close_generation
AL._casing_hide_icon_observer = AL._casing_hide_icon_observer

local function al_is_vr()
    return _G.IS_VR == true
end

local function al_is_finite(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    return true
end

local function is_finite_nonneg(v)
    if not al_is_finite(v) then return false end
    if v < 0 then return false end
    return true
end

local function al_panel_alive(p)
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

local function al_safe_call(obj, method_name, ...)
    if obj == nil then return CALL_MISSING, nil end
    local ok_get, method_or_err = pcall(function() return obj[method_name] end)
    if not ok_get then return CALL_ERROR, nil end
    if type(method_or_err) ~= "function" then return CALL_MISSING, nil end
    local ok_call, result = pcall(method_or_err, obj, ...)
    if not ok_call then return CALL_ERROR, nil end
    return CALL_OK, result
end

local function al_create_bitmap(parent, opts)
    if not parent or not al_panel_alive(parent) then return CALL_MISSING, nil end
    local texture_path = opts and opts.texture
    if texture_path and DB~=nil then
        AL._presentation_textures = AL._presentation_textures or {}
        local available = AL._presentation_textures[texture_path]
        if available==nil then
            local ok, found = pcall(function()
                local has = DB.has
                if type(has)~="function" then return false end
                return has(DB,Idstring("texture"),Idstring(texture_path))
            end)
            available = ok and found==true
            AL._presentation_textures[texture_path] = available
        end
        if not available then return CALL_ERROR,nil end
    end
    return al_safe_call(parent, "bitmap", opts)
end

local function al_read_color(prim)
    if not prim or not al_panel_alive(prim) then return nil end
    local ok_c, c = pcall(function() return prim:color() end)
    if not ok_c or c == nil then return nil end
    local ok_r, r = pcall(function() return c.r end)
    local ok_g, g = pcall(function() return c.g end)
    local ok_b, b = pcall(function() return c.b end)
    local ok_a, a = pcall(function() return c.a end)
    local ok_alpha, alpha = pcall(function() return prim:alpha() end)
    if not ok_r or not ok_g or not ok_b or not ok_a or not ok_alpha
        or not al_is_finite(r) or not al_is_finite(g) or not al_is_finite(b)
        or not al_is_finite(a) or not al_is_finite(alpha) then return nil end
    return c
end

local function al_texture_matches(actual, expected)
    if type(actual) == "string" then return actual == expected end
    local ok, same = pcall(function() return actual:key() == Idstring(expected):key() end)
    return ok and same == true
end

local function al_shape(p, x, y, w, h)
    if not p or not al_panel_alive(p) then return end
    local ok, same = pcall(function()
        return p:x() == x and p:y() == y and p:w() == w and p:h() == h
    end)
    if not ok or not same then al_safe_call(p, "set_shape", x, y, w, h) end
end

local function al_style_matches(p, r, g, b, a, layer, expected_color_alpha)
    local c = al_read_color(p)
    if not c then return false end
    local color_a_expected = expected_color_alpha
    if color_a_expected == nil then color_a_expected = a end
    local ok, same = pcall(function()
        return math.abs(c.r-r)<.01 and math.abs(c.g-g)<.01 and math.abs(c.b-b)<.01
            and math.abs(c.a-color_a_expected)<.01 and math.abs(p:alpha()-a)<.01
            and p:layer()==layer and p:visible()==true
    end)
    return ok and same == true
end

local function al_style(p, r, g, b, a, layer)
    if not p or not al_panel_alive(p) then return end
    if not al_style_matches(p, r, g, b, a, layer) then
        -- Opaque tint avoids multiplying opacity twice in Diesel (a*a observed otherwise).
        al_safe_call(p, "set_color", Color(1, r, g, b))
        al_safe_call(p, "set_alpha", a)
        al_safe_call(p, "set_layer", layer)
        al_safe_call(p, "set_visible", true)
    end
end

local function al_font_size(p, size)
    if not p or not al_panel_alive(p) then return end
    local status, actual = al_safe_call(p, "font_size")
    if status ~= CALL_OK or actual ~= size then al_safe_call(p, "set_font_size", size) end
end

local function al_text_width(p)
    if not p or not al_panel_alive(p) then return nil end
    local ok, _, _, w, h = pcall(function() return p:text_rect() end)
    if ok and al_is_finite(w) and al_is_finite(h) and w>0 and h>0 then
        return math.ceil(w)+1
    end
end

local DARK_R = 0x0B / 255
local DARK_G = 0x0D / 255
local DARK_B = 0x11 / 255
local CYAN_R = 0x7F / 255
local CYAN_G = 0xCD / 255
local CYAN_B = 0xE3 / 255
local AMBER_R = 0.8
local AMBER_G = 0.6
local AMBER_B = 0.2

local CASING_TEXTURE_STEALTH = "guis/textures/pd2/hud_icon_stealthbox"
local PNR_TEXTURE_NORETURN = "guis/textures/pd2/hud_icon_noreturnbox"

local function al_get_runtime_root()
    local rt = kyohud.hud.runtime
    if not rt then return nil end
    if not rt._mounted then return nil end
    local root = rt._root_panel
    if not root or not al_panel_alive(root) then return nil end
    return root
end

local function format_pnr_timer(seconds)
    if not is_finite_nonneg(seconds) then return nil end
    local floored = math.floor(seconds)
    local m = math.floor(floored / 60)
    local s = floored - m * 60
    return string.format("%02d:%02d", m, s)
end

local function read_state_fields(state)
    if not state then return nil, nil, nil, nil end
    local s_timer, s_id, s_tweak, s_inside = nil, nil, nil, nil
    local ok_gt, gt_timer, gt_id = pcall(function()
        return state:get_point_of_no_return_timer()
    end)
    if ok_gt and is_finite_nonneg(gt_timer) then
        s_timer = gt_timer
        s_id = gt_id
    else
        local ok_t, raw_t = pcall(function() return state._point_of_no_return_timer end)
        if ok_t and is_finite_nonneg(raw_t) then
            s_timer = raw_t
        end
        local ok_i, raw_id = pcall(function() return state._point_of_no_return_id end)
        if ok_i then
            s_id = raw_id
        end
    end
    local ok_tw, raw_tw = pcall(function() return state._point_of_no_return_tweak_id end)
    if ok_tw and type(raw_tw) == "string" and raw_tw ~= "" then
        s_tweak = raw_tw
    end
    local ok_in, raw_in = pcall(function() return state._is_inside_point_of_no_return end)
    if ok_in and type(raw_in) == "boolean" then
        s_inside = raw_in
    end
    return s_timer, s_id, s_tweak, s_inside
end

function AL:_clear_event_provenance()
    self._event_manager = nil
    self._event_corner = nil
    self._event_source = nil
    self._event_active = nil
    self._event_tweak_id = nil
    self._event_timer = nil
    self._event_inside = nil
    self._event_state_tweak = nil
    self._event_state_timer = nil
    self._event_state_inside = nil
    self._event_has_active = false
    self._event_has_tweak = false
    self._event_has_timer = false
    self._event_has_inside = false
end

function AL:_bind_event_context(mgr)
    local corner = nil
    if mgr then
        local ok_c, c = pcall(function() return mgr._hud_assault_corner end)
        if ok_c then corner = c end
    end
    local state = nil
    local ok_s, s = pcall(function() return managers.groupai and managers.groupai:state() end)
    if ok_s then state = s end

    if (self._event_manager ~= nil and mgr ~= nil and self._event_manager ~= mgr)
        or (self._event_corner ~= nil and corner ~= nil and self._event_corner ~= corner)
        or (self._event_source ~= nil and state ~= nil and self._event_source ~= state) then
        self:_clear_event_provenance()
    end

    self._event_manager = mgr
    if corner ~= nil then self._event_corner = corner end
    if state ~= nil then self._event_source = state end
    return corner, state
end

function AL:snapshot(manager)
    local mgr = manager or self._manager
    local corner = nil
    if mgr then
        local ok_c, c = pcall(function() return mgr._hud_assault_corner end)
        if ok_c then corner = c end
    end
    local state = nil
    local ok_s, s = pcall(function() return managers.groupai and managers.groupai:state() end)
    if ok_s then state = s end

    if (self._source ~= nil and state ~= self._source)
        or (self._source_corner ~= nil and corner ~= self._source_corner)
        or (self._event_manager ~= nil and mgr ~= nil and self._event_manager ~= mgr)
        or (self._event_corner ~= nil and corner ~= nil and self._event_corner ~= corner)
        or (self._event_source ~= nil and state ~= nil and self._event_source ~= state) then
        self:_clear_event_provenance()
        self._casing_active = false
        self._casing_mode = nil
    end

    self._source = state
    self._source_corner = corner

    local corner_pnr = false
    if corner then
        local ok_p, p = pcall(function() return corner._point_of_no_return end)
        if ok_p and p == true then
            corner_pnr = true
        end
    end

    if corner and not corner_pnr then
        local ok_cc, cc = pcall(function() return corner._casing end)
        if ok_cc and cc == true then
            if not self._casing_active then
                local inferred_mode = nil
                local known_found = false
                local ok_bg, bg = pcall(function() return corner._casing_bg_box end)
                if ok_bg and bg then
                    local ok_sd, sd = pcall(function() return bg:script() end)
                    if ok_sd and type(sd) == "table" and type(sd.text_list) == "table" then
                        for _, text_id in ipairs(sd.text_list) do
                            if text_id == "hud_casing_mode_ticker_clean" then
                                inferred_mode = "civilian"
                                known_found = true
                                break
                            elseif text_id == "hud_casing_mode_ticker" then
                                inferred_mode = "normal"
                                known_found = true
                                break
                            end
                        end
                    end
                end
                if not known_found then
                    inferred_mode = nil
                end
                self._casing_mode = inferred_mode
                self._casing_active = true
                self._data_dirty = true
            end
        else
            if self._casing_active and not self._casing_mode then
                -- native casing closed, clear if we captured it
            end
        end
    end

    local s_timer, s_id, s_tweak, s_inside = read_state_fields(state)

    self._state.active = corner_pnr
    self._state.timer = s_timer
    self._state.id = s_id
    self._state.tweak_id = s_tweak
    self._state.inside = s_inside

    local event_valid = (self._event_manager ~= nil)
        and (mgr == nil or self._event_manager == mgr)
        and (self._event_corner == nil or corner == nil or self._event_corner == corner)
        and (self._event_source == nil or state == nil or self._event_source == state)

    if event_valid then
        if self._event_has_active then
            if self._event_active == false and not corner_pnr then
                self._state.active = false
            elseif self._event_active == true and corner_pnr then
                self._state.active = true
            end
        end
        if self._event_has_tweak then
            if s_tweak ~= self._event_state_tweak then
                self._state.tweak_id = s_tweak
                self._event_tweak_id = s_tweak
                self._event_state_tweak = s_tweak
            else
                self._state.tweak_id = self._event_tweak_id
            end
        end
        if self._event_has_timer then
            if s_timer ~= self._event_state_timer and s_timer ~= nil then
                self._state.timer = s_timer
                self._event_timer = s_timer
                self._event_state_timer = s_timer
            else
                self._state.timer = self._event_timer
            end
        end
        if self._event_has_inside then
            if s_inside ~= self._event_state_inside then
                self._state.inside = s_inside
                self._event_inside = s_inside
                self._event_state_inside = s_inside
            else
                self._state.inside = self._event_inside
            end
        end
    end
end

function AL:_is_standard_tweak(tweak_id, corner)
    local normalized_tweak = tweak_id
    if normalized_tweak == nil then
        normalized_tweak = "noreturn"
    end
    if normalized_tweak ~= "noreturn" then return false end
    local ok_td, td = pcall(function() return tweak_data end)
    if ok_td and type(td) == "table" then
        local ok_ptd, pnr_td = pcall(function() return td.point_of_no_returns end)
        if not ok_ptd then return false end
        if type(pnr_td) == "table" then
            local ok_entry, entry = pcall(function() return pnr_td[normalized_tweak] end)
            if not ok_entry or type(entry) ~= "table" then return false end
            if entry.scale_box == true then return false end
            local tr = entry.texture_rect
            if tr ~= nil and (tr[1] ~= 0 or tr[2] ~= 0 or tr[3] ~= 32 or tr[4] ~= 32) then
                return false
            end
        end
    end
    if corner then
        local ok_nd, nd = pcall(function() return corner._noreturn_data end)
        if not ok_nd then return false end
        if type(nd) == "table" then
            if nd.scale_box == true then return false end
            local itr = nd.icon_texture_rect
            if itr ~= nil and (itr[1] ~= 0 or itr[2] ~= 0 or itr[3] ~= 32 or itr[4] ~= 32) then
                return false
            end
        end
    end
    return true
end

function AL:_is_pnr_covered(corner)
    if self._state.active ~= true then return false end
    if not self:_is_standard_tweak(self._state.tweak_id, corner) then return false end
    if self._state.inside ~= true and self._state.inside ~= false then return false end
    if not is_finite_nonneg(self._state.timer) then return false end
    return true
end

function AL:blocks_assault(manager)
    local mgr = manager
    if self ~= AL and mgr == nil then
        mgr = self
    end
    mgr = mgr or AL._manager
    if not mgr then return false end
    local ok_corner, corner = pcall(function() return mgr._hud_assault_corner end)
    if ok_corner and corner then
        local ok_pnr, pnr = pcall(function() return corner._point_of_no_return end)
        if ok_pnr and pnr == true then
            return true
        end
        if AL:_native_casing_active(corner) then
            return true
        end
        local ok_hp, hp = pcall(function() return corner._hud_panel end)
        if ok_hp and hp and al_panel_alive(hp) then
            local ok_p, pnr_panel = pcall(function() return hp:child("point_of_no_return_panel") end)
            if ok_p and pnr_panel and al_panel_alive(pnr_panel) then
                local ok_v, v = pcall(function() return pnr_panel:visible() end)
                if ok_v and v == true then
                    return true
                end
            end
        end
    end
    if AL._manager == mgr then
        if AL._native_acquired == true then return true end
        if AL._casing_native_acquired == true then return true end
        if AL._root_panel and al_panel_alive(AL._root_panel) then
            local ok_rv, rv = pcall(function() return AL._root_panel:visible() end)
            if ok_rv and rv == true then return true end
        end
        if AL._casing_root_panel and al_panel_alive(AL._casing_root_panel) then
            local ok_cv, cv = pcall(function() return AL._casing_root_panel:visible() end)
            if ok_cv and cv == true then return true end
        end
    end
    return false
end

function AL:_get_font()
    local ok_td, td = pcall(function() return tweak_data end)
    if ok_td and td then
        local ok_hud, hud = pcall(function() return td.hud end)
        if ok_hud and hud then
            local ok_font, f = pcall(function() return hud.medium_font_noshadow end)
            if ok_font and type(f) == "string" and f ~= "" then return f end
        end
        local ok_hc, hc = pcall(function() return td.hud_corner end)
        if ok_hc and hc then
            local ok_af, af = pcall(function() return hc.assault_font end)
            if ok_af and type(af) == "string" and af ~= "" then return af end
        end
    end
    return "fonts/font_medium_mf"
end

function AL:_compute_layout(parent_w, parent_h)
    if not al_is_finite(parent_w) or not al_is_finite(parent_h) then return nil end
    if parent_w <= 0 or parent_h <= 0 then return nil end
    local layout = kyohud.hud.layout
    if not layout or type(layout.assault_alerts) ~= "function" then return nil end
    local scale = (kyohud.settings and kyohud.settings.hud_scale) or 1
    local geom = layout.assault_alerts(parent_w, parent_h, scale)
    if not geom or not geom.valid then return nil end
    local es = geom.es or 1
    if type(layout.objectives_region) == "function" then
        local obj = layout.objectives_region(parent_w, parent_h)
        if obj and geom.root_x < obj.w and geom.root_y < obj.h then return nil end
    end
    local title_x = REF_PNR_TITLE_X * es
    local timer_right = REF_PNR_TIMER_RIGHT * es
    local status_font = math.max(MIN_FONT_SIZE, math.floor(REF_PNR_STATUS_FONT * es))
    return {
        es = es,
        root_x = geom.root_x,
        root_y = geom.root_y,
        root_w = geom.root_w,
        root_h = geom.root_h,
        font_size = geom.ticker_font,
        bg = geom.bg,
        icon = geom.status,
        title_x = title_x,
        timer_right = timer_right,
        title = { x = title_x, y = 0, w = 0, h = geom.ticker.h },
        timer = { x = 0, y = 0, w = 0, h = geom.ticker.h },
        status_font = status_font,
        status = { x = 0, y = geom.counter_y, w = geom.root_w, h = geom.counter_h },
    }
end

local function resolve_loc_text(key, fallback)
    local ok_loc, loc = pcall(function() return managers.localization end)
    if ok_loc and loc then
        local ok_t, t = pcall(function() return loc:text(key) end)
        if ok_t and type(t) == "string" and t ~= "" and not t:find("^LOC:") and not t:find("^ERROR:") then
            return t
        end
    end
    return fallback
end

function AL:_resolve_title_text()
    return resolve_loc_text("ky_hud_pnr_title", "POINT OF NO RETURN")
end

function AL:_resolve_status_text()
    if self._state.inside == true then
        return resolve_loc_text("ky_hud_pnr_inside", "INSIDE")
    end
    return resolve_loc_text("ky_hud_pnr_outside", "OUTSIDE")
end

function AL:_resolve_timer_text()
    return format_pnr_timer(self._state.timer) or "00:00"
end

function AL:_ensure_pnr_bg()
    if self._pnr_bg and al_panel_alive(self._pnr_bg) then return end
    if not self._root_panel or not al_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    local layout = self._layout_cache
    local bg = layout.bg
    if not bg then return end
    local status, prim = al_safe_call(self._root_panel, "rect", {
        name = PNR_BG_NAME,
        x = bg.x, y = bg.y, w = bg.w, h = bg.h,
        color = Color(1, CYAN_R, CYAN_G, CYAN_B),
        visible = true,
        layer = 0,
    })
    if status == CALL_OK and prim then
        self._pnr_bg = prim
    end
end

function AL:_ensure_pnr_icon()
    if self._pnr_icon and al_panel_alive(self._pnr_icon) then return end
    if not self._root_panel or not al_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    local layout = self._layout_cache
    local icon = layout.icon
    if not icon then return end
    local status, prim = al_create_bitmap(self._root_panel, {
        name = PNR_ICON_NAME,
        texture = PNR_TEXTURE_NORETURN,
        x = icon.x, y = icon.y, w = icon.w, h = icon.h,
        visible = true,
        layer = 1,
    })
    if status == CALL_OK and prim then
        self._pnr_icon = prim
    end
end

function AL:_measure_and_place_timer()
    if not self._timer_prim or not al_panel_alive(self._timer_prim) then return end
    if not self._layout_cache then return end
    local layout = self._layout_cache
    local ok_mr, _, _, mw, mh = pcall(function() return self._timer_prim:text_rect() end)
    if not ok_mr or not al_is_finite(mw) or mw <= 0 then return end
    local measured_w = math.ceil(mw)
    local timer_x = layout.timer_right - measured_w
    if timer_x < 0 then timer_x = 0 end
    al_safe_call(self._timer_prim, "set_shape", timer_x, 0, measured_w, layout.timer.h)
    self._pnr_timer_measured_w = measured_w
end

function AL:_compute_title_available_w()
    if not self._layout_cache then return 0 end
    local layout = self._layout_cache
    local timer_x = 0
    if self._timer_prim and al_panel_alive(self._timer_prim) then
        local ok_tx, tx = al_safe_call(self._timer_prim, "x")
        if ok_tx == CALL_OK and al_is_finite(tx) then
            timer_x = tx
        end
    end
    if timer_x <= 0 then
        timer_x = layout.timer_right - (self._pnr_timer_measured_w or 0)
    end
    local available = timer_x - REF_PNR_TITLE_GAP * (layout.es or 1) - layout.title_x
    if available < 0 then available = 0 end
    return available
end

function AL:_ensure_title_prim()
    if self._title_prim and al_panel_alive(self._title_prim) then return end
    if not self._root_panel or not al_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    local font = self:_get_font()
    local layout = self._layout_cache
    local text = self:_resolve_title_text()
    local available_w = self:_compute_title_available_w()
    if available_w <= 0 then available_w = layout.root_w end
    local status, prim = al_safe_call(self._root_panel, "text", {
        name = PNR_TITLE_NAME,
        text = text,
        font = font,
        font_size = layout.font_size,
        color = Color(1, 1, 0, 0),
        x = layout.title_x, y = 0,
        w = available_w, h = layout.timer.h,
        align = "left", vertical = "center",
        wrap = false, word_wrap = false,
        visible = true,
        layer = 1,
    })
    if status == CALL_OK and prim then
        self._title_prim = prim
        self._cached_title_text = text
        self._cached_font = font
        self._cached_font_size = layout.font_size
    end
end

function AL:_ensure_status_bg_prim()
    if self._pnr_status_bg and al_panel_alive(self._pnr_status_bg) then return end
    if not self._root_panel or not al_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    local layout = self._layout_cache
    local status, prim = al_safe_call(self._root_panel, "rect", {
        name = PNR_STATUS_BG_NAME,
        x = 0, y = layout.status.y, w = layout.root_w, h = layout.status.h,
        color = Color(0.75, DARK_R, DARK_G, DARK_B),
        visible = true,
        layer = 0,
    })
    if status == CALL_OK and prim then
        self._pnr_status_bg = prim
    end
end

function AL:_ensure_status_prim()
    if self._status_prim and al_panel_alive(self._status_prim) then return end
    if not self._root_panel or not al_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    local font = self:_get_font()
    local layout = self._layout_cache
    local text = self:_resolve_status_text()
    local status_x = layout.root_w - REF_PNR_STATUS_PAD * (layout.es or 1)
    local status, prim = al_safe_call(self._root_panel, "text", {
        name = PNR_STATUS_NAME,
        text = text,
        font = font,
        font_size = layout.status_font,
        color = Color(1, 1, 1, 1),
        x = 0, y = layout.status.y,
        w = status_x, h = layout.status.h,
        align = "right", vertical = "center",
        wrap = false, word_wrap = false,
        visible = true,
        layer = 1,
    })
    if status == CALL_OK and prim then
        self._status_prim = prim
        self._cached_status_text = text
    end
end

function AL:_ensure_timer_prim()
    if self._timer_prim and al_panel_alive(self._timer_prim) then return end
    if not self._root_panel or not al_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    local font = self:_get_font()
    local layout = self._layout_cache
    local text = self:_resolve_timer_text()
    local status, prim = al_safe_call(self._root_panel, "text", {
        name = PNR_TIMER_NAME,
        text = text,
        font = font,
        font_size = layout.font_size,
        color = Color(1, 1, 0, 0),
        x = 0, y = 0,
        w = layout.root_w, h = layout.timer.h,
        align = "right", vertical = "center",
        wrap = false, word_wrap = false,
        visible = true,
        layer = 1,
    })
    if status == CALL_OK and prim then
        self._timer_prim = prim
        self._cached_timer_text = text
        self:_measure_and_place_timer()
    end
end

function AL:_ensure_primitives()
    self:_ensure_pnr_bg()
    self:_ensure_pnr_icon()
    self:_ensure_timer_prim()
    self:_ensure_title_prim()
    self:_ensure_status_bg_prim()
    self:_ensure_status_prim()
end

local function sync_text_prim(prim, new_text, cached_text)
    if not prim or not al_panel_alive(prim) then return cached_text, false end
    local changed = false
    if new_text ~= cached_text then
        al_safe_call(prim, "set_text", new_text)
        local ok_r, r = pcall(function() return prim:text() end)
        if ok_r and r == new_text then
            cached_text = new_text
            changed = true
        end
    else
        local ok_a, actual = pcall(function() return prim:text() end)
        if ok_a and type(actual) == "string" and actual ~= new_text then
            al_safe_call(prim, "set_text", new_text)
            changed = true
        end
    end
    local ok_v, v = pcall(function() return prim:visible() end)
    if ok_v and v ~= true then
        al_safe_call(prim, "set_visible", true)
    end
    return cached_text, changed
end

function AL:_sync_primitives()
    local g = self._layout_cache
    if not g then return end
    al_font_size(self._timer_prim, g.font_size)
    al_font_size(self._title_prim, g.font_size)
    al_font_size(self._status_prim, g.status_font)
    self._cached_timer_text = sync_text_prim(self._timer_prim, self:_resolve_timer_text(), self._cached_timer_text)
    self._cached_status_text = sync_text_prim(self._status_prim, self:_resolve_status_text(), self._cached_status_text)
    local timer_w, status_w = al_text_width(self._timer_prim), al_text_width(self._status_prim)
    if not timer_w or not status_w then return end
    local pad, gap = REF_PNR_STATUS_PAD*g.es, REF_PNR_TITLE_GAP*g.es
    local budget = g.timer_right-timer_w-gap-g.title_x
    if budget<=0 or status_w+2*pad>g.root_w then return end
    local source = self:_resolve_title_text()
    local _, actual_title = al_safe_call(self._title_prim,"text")
    local actual_width = al_text_width(self._title_prim)
    if self._pnr_title_source~=source or self._pnr_title_budget~=budget
        or self._pnr_title_font~=g.font_size or not self._cached_title_text
        or actual_title~=self._cached_title_text or not actual_width or actual_width>budget then
        local fitted, display = source, source
        al_safe_call(self._title_prim, "set_text", display)
        local width = al_text_width(self._title_prim)
        while width and width>budget and #fitted>0 do
            -- Remove a complete UTF-8 codepoint, including continuation bytes.
            local cut = #fitted
            while cut>1 and fitted:byte(cut)>=128 and fitted:byte(cut)<192 do cut=cut-1 end
            fitted = fitted:sub(1, cut-1)
            display = fitted .. "..."
            al_safe_call(self._title_prim, "set_text", display)
            width = al_text_width(self._title_prim)
        end
        if not width or width>budget or fitted=="" then return end
        self._cached_title_text = display
        self._pnr_title_source, self._pnr_title_budget, self._pnr_title_font = source, budget, g.font_size
    end
    sync_text_prim(self._title_prim, self._cached_title_text, self._cached_title_text)
    self._pnr_timer_region = {x=g.timer_right-timer_w,y=0,w=timer_w,h=g.timer.h}
    self._pnr_title_region = {x=g.title_x,y=0,w=budget,h=g.timer.h}
    self._pnr_status_region = {x=g.root_w-status_w-pad,y=g.status.y,w=status_w,h=g.status.h}
    self._pnr_status_bg_region = {x=g.root_w-status_w-2*pad,y=g.status.y,w=status_w+2*pad,h=g.status.h}
    local t, title, s, bg = self._pnr_timer_region, self._pnr_title_region, self._pnr_status_region, self._pnr_status_bg_region
    al_shape(self._timer_prim, t.x,t.y,t.w,t.h)
    al_shape(self._title_prim, title.x,title.y,title.w,title.h)
    al_shape(self._status_prim, s.x,s.y,s.w,s.h)
    al_shape(self._pnr_status_bg, bg.x,bg.y,bg.w,bg.h)
    al_style(self._pnr_bg, CYAN_R,CYAN_G,CYAN_B,1,0)
    al_style(self._pnr_status_bg, DARK_R,DARK_G,DARK_B,.75,0)
    al_style(self._title_prim, 17/255,17/255,17/255,1,1)
    al_style(self._timer_prim, 17/255,17/255,17/255,1,1)
    al_style(self._status_prim, 201/255,209/255,216/255,1,1)
    al_style(self._pnr_icon, 1,1,1,1,1)
end

function AL:_update_layout()
    if not self._root_panel or not al_panel_alive(self._root_panel) then return end
    if not self._parent_panel or not al_panel_alive(self._parent_panel) then return end
    local pw_s, pw = al_safe_call(self._parent_panel, "w")
    local ph_s, ph = al_safe_call(self._parent_panel, "h")
    if pw_s ~= CALL_OK or ph_s ~= CALL_OK then return end
    if not al_is_finite(pw) or not al_is_finite(ph) then return end
    if pw <= 0 or ph <= 0 then return end
    local new_layout = self:_compute_layout(pw, ph)
    if not new_layout then
        self._layout_cache = nil
        return
    end
    local changed = not self._layout_cache
        or self._layout_cache.root_x ~= new_layout.root_x
        or self._layout_cache.root_y ~= new_layout.root_y
        or self._layout_cache.root_w ~= new_layout.root_w
        or self._layout_cache.root_h ~= new_layout.root_h
        or self._layout_cache.font_size ~= new_layout.font_size
    self._layout_cache = new_layout
    if not changed then
        al_shape(self._root_panel, new_layout.root_x,new_layout.root_y,new_layout.root_w,new_layout.root_h)
        al_shape(self._pnr_bg, new_layout.bg.x,new_layout.bg.y,new_layout.bg.w,new_layout.bg.h)
        al_shape(self._pnr_icon, new_layout.icon.x,new_layout.icon.y,new_layout.icon.w,new_layout.icon.h)
        return
    end
    local rs = al_safe_call(self._root_panel, "set_shape", new_layout.root_x, new_layout.root_y, new_layout.root_w, new_layout.root_h)
    if rs ~= CALL_OK then
        self._layout_cache = nil
        return
    end
    if self._pnr_bg and al_panel_alive(self._pnr_bg) and new_layout.bg then
        al_safe_call(self._pnr_bg, "set_shape", new_layout.bg.x, new_layout.bg.y, new_layout.bg.w, new_layout.bg.h)
    end
    if self._pnr_icon and al_panel_alive(self._pnr_icon) and new_layout.icon then
        al_safe_call(self._pnr_icon, "set_shape", new_layout.icon.x, new_layout.icon.y, new_layout.icon.w, new_layout.icon.h)
    end
    if self._pnr_status_bg and al_panel_alive(self._pnr_status_bg) then
        al_safe_call(self._pnr_status_bg, "set_shape", 0, new_layout.status.y, new_layout.root_w, new_layout.status.h)
    end
    if self._title_prim and al_panel_alive(self._title_prim) then
        al_safe_call(self._title_prim, "set_font_size", new_layout.font_size)
    end
    if self._timer_prim and al_panel_alive(self._timer_prim) then
        al_safe_call(self._timer_prim, "set_font_size", new_layout.font_size)
        self:_measure_and_place_timer()
    end
    if self._status_prim and al_panel_alive(self._status_prim) then
        al_safe_call(self._status_prim, "set_shape", 0, new_layout.status.y, new_layout.root_w - REF_PNR_STATUS_PAD * (new_layout.es or 1), new_layout.status.h)
        al_safe_call(self._status_prim, "set_font_size", new_layout.status_font)
    end
    if self._timer_prim and al_panel_alive(self._timer_prim) then
        local available_w = self:_compute_title_available_w()
        if self._title_prim and al_panel_alive(self._title_prim) and available_w > 0 then
            al_safe_call(self._title_prim, "set_shape", new_layout.title_x, 0, available_w, new_layout.timer.h)
        end
    end
    self._cached_font_size = new_layout.font_size
    self._layout_cache = new_layout
end

function AL:_verify_render()
    local mode = self:_determine_active_mode()
    if mode == "pnr" then
        return self:_verify_pnr_render()
    elseif mode == "casing" or mode == "casing_closing" then
        return self:_verify_casing_render()
    end
    self._render_verified = false
    self._casing_render_verified = false
    return false
end

function AL:_verify_pnr_render()
    if not self._layout_cache then
        self._render_verified = false
        return false
    end
    local geom = self._layout_cache
    if not al_is_finite(geom.root_w) or not al_is_finite(geom.root_h) or not al_is_finite(geom.font_size) then
        self._render_verified = false
        return false
    end
    if geom.root_w <= 0 or geom.root_h <= 0 or geom.font_size <= 0 then
        self._render_verified = false
        return false
    end
    if not self._root_panel or not al_panel_alive(self._root_panel) then
        self._render_verified = false
        return false
    end
    if self._parent_panel then
        local ok_p, p = pcall(function() return self._root_panel:parent() end)
        if not ok_p or p ~= self._parent_panel then
            self._render_verified = false
            return false
        end
    end
    local tol = 0.5
    local ox_s, ox = al_safe_call(self._root_panel, "x")
    local oy_s, oy = al_safe_call(self._root_panel, "y")
    local ow_s, ow = al_safe_call(self._root_panel, "w")
    local oh_s, oh = al_safe_call(self._root_panel, "h")
    if ox_s ~= CALL_OK or oy_s ~= CALL_OK or ow_s ~= CALL_OK or oh_s ~= CALL_OK then
        self._render_verified = false
        return false
    end
    if not al_is_finite(ox) or not al_is_finite(oy) or not al_is_finite(ow) or not al_is_finite(oh) then
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

    if not self:_verify_decoration(self._pnr_bg, PNR_BG_NAME, geom.bg, CYAN_R, CYAN_G, CYAN_B, 1)
        or not al_style_matches(self._pnr_bg,CYAN_R,CYAN_G,CYAN_B,1,0) then
        self._render_verified = false
        return false
    end
    if not self:_verify_icon(self._pnr_icon, PNR_ICON_NAME, geom.icon, PNR_TEXTURE_NORETURN)
        or not al_style_matches(self._pnr_icon,1,1,1,1,1) then
        self._render_verified = false
        return false
    end
    if not self._pnr_status_bg_region or not self:_verify_decoration(self._pnr_status_bg, PNR_STATUS_BG_NAME, self._pnr_status_bg_region, DARK_R, DARK_G, DARK_B, 0.75)
        or not al_style_matches(self._pnr_status_bg,DARK_R,DARK_G,DARK_B,.75,0) then
        self._render_verified = false
        return false
    end

    local function check_leaf(prim, child_name, desired_text, region, expected_font_size)
        if not prim or not al_panel_alive(prim) then return false end
        if type(desired_text) ~= "string" or desired_text == "" or desired_text:find("^LOC:") then
            return false
        end
        local ok_ch, ch = pcall(function() return self._root_panel:child(child_name) end)
        if not ok_ch or ch ~= prim then return false end
        local ok_pr, pr = pcall(function() return prim:parent() end)
        if not ok_pr or pr ~= self._root_panel then return false end
        local ok_v, v = pcall(function() return prim:visible() end)
        if not ok_v or v ~= true then return false end
        local ok_t, t = pcall(function() return prim:text() end)
        if not ok_t or type(t) ~= "string" or t ~= desired_text then return false end
        local ok_fs, fs = pcall(function() return prim:font_size() end)
        if not ok_fs or not al_is_finite(fs) or fs <= 0 then return false end
        local ref_fs = expected_font_size or geom.font_size
        if math.abs(fs - ref_fs) > tol then return false end
        local s_px, px = al_safe_call(prim, "x")
        local s_py, py = al_safe_call(prim, "y")
        local s_pw, pw = al_safe_call(prim, "w")
        local s_ph, ph = al_safe_call(prim, "h")
        if s_px ~= CALL_OK or s_py ~= CALL_OK or s_pw ~= CALL_OK or s_ph ~= CALL_OK then
            return false
        end
        if not al_is_finite(px) or not al_is_finite(py) or not al_is_finite(pw) or not al_is_finite(ph) then
            return false
        end
        if pw <= 0 or ph <= 0 then return false end
        if not region or math.abs(px-region.x)>tol or math.abs(pw-region.w)>tol
            or math.abs(py - region.y) > tol or math.abs(ph - region.h) > tol then
            return false
        end
        local ok_mr, _, _, mw, mh = pcall(function() return prim:text_rect() end)
        if not ok_mr or not al_is_finite(mw) or not al_is_finite(mh) then return false end
        if mw <= 0 or mh <= 0 then return false end
        if mw > pw + tol or mh > ph + tol then return false end
        return true
    end

    if not check_leaf(self._title_prim, PNR_TITLE_NAME, self._cached_title_text, self._pnr_title_region)
        or not al_style_matches(self._title_prim,17/255,17/255,17/255,1,1) then
        self._render_verified = false
        return false
    end
    if not check_leaf(self._status_prim, PNR_STATUS_NAME, self._cached_status_text, self._pnr_status_region, geom.status_font)
        or not al_style_matches(self._status_prim,201/255,209/255,216/255,1,1) then
        self._render_verified = false
        return false
    end
    if not self._timer_prim or not al_panel_alive(self._timer_prim) then
        self._render_verified = false
        return false
    end
    local ok_tc, tc = pcall(function() return self._root_panel:child(PNR_TIMER_NAME) end)
    if not ok_tc or tc ~= self._timer_prim then
        self._render_verified = false
        return false
    end
    if not check_leaf(self._timer_prim, PNR_TIMER_NAME, self._cached_timer_text, self._pnr_timer_region)
        or not al_style_matches(self._timer_prim,17/255,17/255,17/255,1,1) then
        self._render_verified = false
        return false
    end
    local ok_trx, trx = al_safe_call(self._timer_prim, "x")
    local ok_trw, trw = al_safe_call(self._timer_prim, "w")
    if ok_trx ~= CALL_OK or ok_trw ~= CALL_OK then
        self._render_verified = false
        return false
    end
    if not al_is_finite(trx) or not al_is_finite(trw) then
        self._render_verified = false
        return false
    end
    if math.abs((trx + trw) - geom.timer_right) > tol then
        self._render_verified = false
        return false
    end

    self._render_verified = true
    return true
end

function AL:_verify_decoration(prim, child_name, region, er, eg, eb, ea)
    if not prim or not al_panel_alive(prim) then return false end
    local ok_ch, ch = pcall(function() return self._root_panel:child(child_name) end)
    if not ok_ch or ch ~= prim then return false end
    local ok_pr, pr = pcall(function() return prim:parent() end)
    if not ok_pr or pr ~= self._root_panel then return false end
    local ok_v, v = pcall(function() return prim:visible() end)
    if not ok_v or v ~= true then return false end
    local tol = 0.5
    local s_px, px = al_safe_call(prim, "x")
    local s_py, py = al_safe_call(prim, "y")
    local s_pw, pw = al_safe_call(prim, "w")
    local s_ph, ph = al_safe_call(prim, "h")
    if s_px ~= CALL_OK or s_py ~= CALL_OK or s_pw ~= CALL_OK or s_ph ~= CALL_OK then
        return false
    end
    if not al_is_finite(px) or not al_is_finite(py) or not al_is_finite(pw) or not al_is_finite(ph) then
        return false
    end
    if region then
        if math.abs(px - region.x) > tol or math.abs(py - region.y) > tol
            or math.abs(pw - region.w) > tol or math.abs(ph - region.h) > tol then
            return false
        end
    end
    if er then
        local c = al_read_color(prim)
        if not c then return false end
        if math.abs(c.r - er) > 0.02 or math.abs(c.g - eg) > 0.02 or math.abs(c.b - eb) > 0.02 then
            return false
        end
        if ea ~= nil and math.abs(c.a - ea) > 0.05 then
            return false
        end
    end
    return true
end

function AL:_verify_icon(prim, child_name, region, expected_texture)
    if not prim or not al_panel_alive(prim) then return false end
    local ok_ch, ch = pcall(function() return self._root_panel:child(child_name) end)
    if not ok_ch or ch ~= prim then return false end
    local ok_pr, pr = pcall(function() return prim:parent() end)
    if not ok_pr or pr ~= self._root_panel then return false end
    local ok_v, v = pcall(function() return prim:visible() end)
    if not ok_v or v ~= true then return false end
    local ok_tex, tex = pcall(function() return prim:texture_name() end)
    if not ok_tex or not al_texture_matches(tex, expected_texture) then
        return false
    end
    local tol = 0.5
    local s_px, px = al_safe_call(prim, "x")
    local s_py, py = al_safe_call(prim, "y")
    local s_pw, pw = al_safe_call(prim, "w")
    local s_ph, ph = al_safe_call(prim, "h")
    if s_px ~= CALL_OK or s_py ~= CALL_OK or s_pw ~= CALL_OK or s_ph ~= CALL_OK then
        return false
    end
    if not al_is_finite(px) or not al_is_finite(py) or not al_is_finite(pw) or not al_is_finite(ph) then
        return false
    end
    if region then
        if math.abs(px - region.x) > tol or math.abs(py - region.y) > tol
            or math.abs(pw - region.w) > tol or math.abs(ph - region.h) > tol then
            return false
        end
    end
    return true
end

function AL:_handle_render_failure()
    self._render_failed = true
    self._render_verified = false
    if self._root_panel and al_panel_alive(self._root_panel) then
        al_safe_call(self._root_panel, "set_visible", false)
    end
    self:_release_native()
end

function AL:_is_supported_casing_mode(mode)
    if mode == "normal" then return true end
    if mode == "civilian" then return true end
    return false
end

function AL:_native_casing_active(corner)
    if not corner then return true end
    local ok_cas, cas = pcall(function() return corner._casing end)
    if not ok_cas then return true end
    if cas == true then return true end
    local ok_hp, hp = pcall(function() return corner._hud_panel end)
    if not ok_hp or not hp or not al_panel_alive(hp) then return true end
    local ok_cp, cp = pcall(function() return hp:child("casing_panel") end)
    if not ok_cp or not cp or not al_panel_alive(cp) then return true end
    local ok_cv, cv = pcall(function() return cp:visible() end)
    if not ok_cv or cv ~= true then return false end
    local ok_bg, bg = pcall(function() return corner._casing_bg_box end)
    if ok_bg and bg and al_panel_alive(bg) then
        local ok_bv, bv = pcall(function() return bg:visible() end)
        if ok_bv and bv == true then return true end
    end
    local ok_ic, ic = pcall(function() return cp:child("icon_casingbox") end)
    if ok_ic and ic and al_panel_alive(ic) then
        local ok_iv, iv = pcall(function() return ic:visible() end)
        local ok_ia, ia = pcall(function() return ic:alpha() end)
        if ok_iv and iv == true and ok_ia and al_is_finite(ia) and ia > 0 then
            return true
        end
    end
    return false
end

function AL:_resolve_casing_ticker_text()
    local key = (self._casing_mode == "civilian") and "hud_casing_mode_ticker_clean" or "hud_casing_mode_ticker"
    local label
    local ok_loc, loc = pcall(function() return managers.localization end)
    if ok_loc and loc then
        local ok_t, t = pcall(function() return loc:text(key) end)
        if ok_t and type(t) == "string" and t ~= "" and not t:find("^LOC:") and not t:find("^ERROR:") then
            label = t
        end
    end
    if not label then
        label = (self._casing_mode == "civilian") and "CIVILIAN MODE" or "CASING MODE"
    end
    local sep
    if ok_loc and loc then
        local ok_s, s = pcall(function() return loc:text("hud_assault_end_line") end)
        if ok_s and type(s) == "string" and s ~= "" and not s:find("^LOC:") then
            sep = s
        end
    end
    if not sep then sep = "------------------------" end
    return label .. "  " .. sep
end

function AL:_resolve_native_targets()
    if not self._manager then return nil end
    local function check_parent(child, expected_parent)
        if not child or not al_panel_alive(child) then return false end
        local ok, p = pcall(function() return child:parent() end)
        if not ok then return false end
        return p == expected_parent
    end
    local ok_corner, corner = pcall(function() return self._manager._hud_assault_corner end)
    if not ok_corner or not corner then return nil end
    local ok_hp, hp = pcall(function() return corner._hud_panel end)
    if not ok_hp or not hp or not al_panel_alive(hp) then return nil end
    local ok_pp, pnr_panel = pcall(function() return hp:child("point_of_no_return_panel") end)
    if not ok_pp or not pnr_panel or not al_panel_alive(pnr_panel) then return nil end
    if not check_parent(pnr_panel, hp) then return nil end
    local ok_icon, icon = pcall(function() return pnr_panel:child("icon_noreturnbox") end)
    if not ok_icon or not icon or not al_panel_alive(icon) then return nil end
    if not check_parent(icon, pnr_panel) then return nil end
    local ok_bg, bg = pcall(function() return corner._noreturn_bg_box end)
    if not ok_bg or not bg or not al_panel_alive(bg) then return nil end
    if not check_parent(bg, pnr_panel) then return nil end
    local ok_ptxt, pnr_text = pcall(function() return bg:child("point_of_no_return_text") end)
    if not ok_ptxt or not pnr_text or not al_panel_alive(pnr_text) then return nil end
    if not check_parent(pnr_text, bg) then return nil end
    local ok_ptmr, pnr_timer = pcall(function() return bg:child("point_of_no_return_timer") end)
    if not ok_ptmr or not pnr_timer or not al_panel_alive(pnr_timer) then return nil end
    if not check_parent(pnr_timer, bg) then return nil end

    local leaves = { icon, pnr_text, pnr_timer }
    local bg_leaf_names = { "bg", "left_top", "left_bottom", "right_top", "right_bottom" }
    for _, name in ipairs(bg_leaf_names) do
        local ok_l, leaf = pcall(function() return bg:child(name) end)
        if not ok_l or not leaf or not al_panel_alive(leaf) then return nil end
        if not check_parent(leaf, bg) then return nil end
        leaves[#leaves + 1] = leaf
    end
    return {
        corner = corner,
        hud_panel = hp,
        pnr_panel = pnr_panel,
        noreturn_bg_box = bg,
        leaves = leaves,
    }
end

function AL:_should_fallback_native()
    if not self._manager then return true end
    local ok_corner, corner = pcall(function() return self._manager._hud_assault_corner end)
    if not ok_corner or not corner then return true end
    local ok_pnr, pnr = pcall(function() return corner._point_of_no_return end)
    if not ok_pnr or pnr ~= true then return true end
    if self:_native_casing_active(corner) then return true end
    local ok_am, am = pcall(function() return corner._assault_mode end)
    if not ok_am or am == "phalanx" then return true end
    local ok_wfn, wfn = pcall(function() return corner.should_display_waves end)
    if not ok_wfn then return true end
    if type(wfn) == "function" then
        local ok_waves, waves = pcall(wfn, corner)
        if not ok_waves or waves == true then return true end
    end
    local ok_hp, hp = pcall(function() return corner._hud_panel end)
    if not ok_hp or not hp or not al_panel_alive(hp) then return true end
    local ok_pp, pnr_panel = pcall(function() return hp:child("point_of_no_return_panel") end)
    if not ok_pp or not pnr_panel or not al_panel_alive(pnr_panel) then return true end
    local ok_pv, pv = pcall(function() return pnr_panel:visible() end)
    if not ok_pv or pv ~= true then return true end

    local veto_panels = { "buffs_panel" }
    for _, name in ipairs(veto_panels) do
        local ok_vp, vp = pcall(function() return hp:child(name) end)
        if not ok_vp then return true end
        if vp and al_panel_alive(vp) then
            local ok_v, v = pcall(function() return vp:visible() end)
            if not ok_v or v == true then return true end
        end
    end

    if not self:_is_pnr_covered(corner) then return true end
    return false
end

function AL:_try_acquire_native()
    if not self._render_verified then return false end
    if al_is_vr() then return false end
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
        local same_targets = (self._native_corner == targets.corner)
            and (self._native_bg_box == targets.noreturn_bg_box)
            and (self._native_targets ~= nil)
        if same_targets and self._native_targets.leaves then
            for i, leaf in ipairs(targets.leaves) do
                if self._native_targets.leaves[i] ~= leaf then
                    same_targets = false
                    break
                end
            end
        else
            same_targets = false
        end
        if not same_targets then
            local released = self:_release_native()
            if not released then return false end
        else
            local requests = self._native_requests
            if requests then
                for _, req in ipairs(requests) do
                    local actual, err = nv:_read_value(req.id, req.property)
                    if err or actual == nil or actual ~= req.value then
                        self._conflict_corner = self._native_corner
                        self:_release_native()
                        return false
                    end
                end
            end
            return true
        end
    elseif self._native_corner or self._native_targets then
        local released = self:_release_native()
        if not released then return false end
    end

    local requests = {}
    for _, obj in ipairs(targets.leaves) do
        nv._whitelist[obj] = nv._whitelist[obj] or {}
        nv._whitelist[obj].visible = true
        requests[#requests + 1] = { id = obj, property = "visible", value = false }
    end

    self._native_requests = requests
    self._native_corner = targets.corner
    self._native_bg_box = targets.noreturn_bg_box
    self._native_hud_panel = targets.hud_panel
    self._native_targets = targets
    self._native_generation = gen
    local acquired = nv:acquire("alerts", gen, requests)
    if acquired then
        self._native_acquired = true
        return true
    end
    self._native_acquired = false
    return false
end

function AL:_release_native()
    if not self._native_acquired and not self._native_corner and not self._native_targets then
        return true
    end
    local nv = kyohud.hud.native_visibility
    if not nv then return false end
    local gen = self._native_generation
    if gen and self._native_requests then
        nv:release("alerts", gen)
    end
    local pending = false
    for _, e in ipairs(nv._entries or {}) do
        if e.owner == "alerts" and (gen == nil or e.generation == gen) then
            pending = true
            break
        end
    end
    if pending then
        self._native_acquired = false
        return false
    end
    local targets = self._native_targets
    if targets and targets.leaves then
        for _, obj in ipairs(targets.leaves) do
            if nv._whitelist[obj] then
                nv._whitelist[obj].visible = nil
                if not next(nv._whitelist[obj]) then
                    nv._whitelist[obj] = nil
                end
            end
        end
    end
    self._native_corner = nil
    self._native_bg_box = nil
    self._native_hud_panel = nil
    self._native_targets = nil
    self._native_requests = nil
    self._native_acquired = false
    self._native_generation = 0
    return true
end

function AL:_sync_native_visibility()
    local mode = self:_determine_active_mode()
    if mode == "pnr" then
        return self:_sync_pnr_native_visibility()
    elseif mode == "casing" then
        return self:_sync_casing_native_visibility()
    elseif mode == "casing_closing" then
        return self:_sync_casing_closing()
    else
        if self._native_acquired or self._native_corner or self._native_targets then
            self:_release_native()
        end
        if self._casing_native_acquired or self._casing_native_corner or self._casing_native_targets then
            self:_release_casing_native()
        end
        if self._root_panel and al_panel_alive(self._root_panel) then
            al_safe_call(self._root_panel, "set_visible", false)
        end
        if self._casing_root_panel and al_panel_alive(self._casing_root_panel) then
            al_safe_call(self._casing_root_panel, "set_visible", false)
        end
        self._render_verified = false
        self._casing_render_verified = false
        return false
    end
end

function AL:_determine_active_mode()
    if self._casing_closing then
        return "casing_closing"
    end
    if self._casing_active and self:_is_supported_casing_mode(self._casing_mode) then
        local ok_corner, corner = pcall(function() return self._manager._hud_assault_corner end)
        if ok_corner and corner then
            local ok_pnr, pnr = pcall(function() return corner._point_of_no_return end)
            if ok_pnr and pnr == true then
                return "fallback"
            end
        end
        return "casing"
    end
    if self._state.active == true then
        return "pnr"
    end
    return "fallback"
end

function AL:_sync_pnr_native_visibility()
    if self._casing_native_acquired or self._casing_native_corner or self._casing_native_targets then
        self:_release_casing_native()
    end
    if self._casing_root_panel and al_panel_alive(self._casing_root_panel) then
        al_safe_call(self._casing_root_panel, "set_visible", false)
    end
    self._casing_render_verified = false

    local should_fallback = self:_should_fallback_native()
        or not self._root_panel
        or not al_panel_alive(self._root_panel)
        or not self._layout_cache

    if should_fallback then
        if self._native_acquired or self._native_corner or self._native_targets then
            self:_release_native()
        end
        if self._root_panel and al_panel_alive(self._root_panel) then
            al_safe_call(self._root_panel, "set_visible", false)
        end
        self._render_verified = false
        return false
    end

    al_safe_call(self._root_panel, "set_visible", true)

    if not self:_verify_pnr_render() then
        self:_handle_render_failure()
        return false
    end

    if not self:_try_acquire_native() then
        self:_release_native()
        al_safe_call(self._root_panel, "set_visible", false)
        self._render_verified = false
        return false
    end

    return true
end

function AL:_resolve_casing_native_targets()
    if not self._manager then return nil end
    local function check_parent(child, expected_parent)
        if not child or not al_panel_alive(child) then return false end
        local ok, p = pcall(function() return child:parent() end)
        if not ok then return false end
        return p == expected_parent
    end
    local ok_corner, corner = pcall(function() return self._manager._hud_assault_corner end)
    if not ok_corner or not corner then return nil end
    local ok_hp, hp = pcall(function() return corner._hud_panel end)
    if not ok_hp or not hp or not al_panel_alive(hp) then return nil end
    local ok_cp, cp = pcall(function() return hp:child("casing_panel") end)
    if not ok_cp or not cp or not al_panel_alive(cp) then return nil end
    if not check_parent(cp, hp) then return nil end
    local ok_icon, icon = pcall(function() return cp:child("icon_casingbox") end)
    if not ok_icon or not icon or not al_panel_alive(icon) then return nil end
    if not check_parent(icon, cp) then return nil end
    local ok_bg, bg = pcall(function() return corner._casing_bg_box end)
    if not ok_bg or not bg or not al_panel_alive(bg) then return nil end
    if not check_parent(bg, cp) then return nil end
    local ok_tp, tp = pcall(function() return bg:child("text_panel") end)
    if not ok_tp or not tp or not al_panel_alive(tp) then return nil end
    if not check_parent(tp, bg) then return nil end
    local bg_leaf_names = { "bg", "left_top", "left_bottom", "right_top", "right_bottom" }
    local bg_leaves = {}
    for _, name in ipairs(bg_leaf_names) do
        local ok_l, leaf = pcall(function() return bg:child(name) end)
        if not ok_l or not leaf or not al_panel_alive(leaf) then return nil end
        if not check_parent(leaf, bg) then return nil end
        bg_leaves[#bg_leaves + 1] = leaf
    end
    return {
        corner = corner,
        hud_panel = hp,
        casing_panel = cp,
        casing_bg_box = bg,
        text_panel = tp,
        icon = icon,
        bg_leaves = bg_leaves,
    }
end

function AL:_should_fallback_casing_native()
    if not self._casing_active then return true end
    if not self:_is_supported_casing_mode(self._casing_mode) then return true end
    if al_is_vr() then return true end
    if not self._manager then return true end
    local ok_corner, corner = pcall(function() return self._manager._hud_assault_corner end)
    if not ok_corner or not corner then return true end
    local ok_cas, cas = pcall(function() return corner._casing end)
    if not ok_cas or cas ~= true then return true end
    local ok_pnr, pnr = pcall(function() return corner._point_of_no_return end)
    if ok_pnr and pnr == true then return true end
    local ok_am, am = pcall(function() return corner._assault_mode end)
    if ok_am and am == "phalanx" then return true end
    local ok_wfn, wfn = pcall(function() return corner.should_display_waves end)
    if ok_wfn and type(wfn) == "function" then
        local ok_waves, waves = pcall(wfn, corner)
        if ok_waves and waves == true then return true end
    end
    if not self._casing_root_panel or not al_panel_alive(self._casing_root_panel) then return true end
    if not self._casing_layout_cache then return true end
    return false
end

function AL:_try_acquire_casing_native()
    if not self._casing_render_verified then return false end
    if al_is_vr() then return false end
    if self:_should_fallback_casing_native() then return false end
    local targets = self:_resolve_casing_native_targets()
    if not targets then return false end
    if self._casing_conflict_corner == targets.corner then
        return false
    end
    if self._casing_conflict_corner ~= nil then
        self._casing_conflict_corner = nil
    end
    local rt = kyohud.hud.runtime
    if not rt then return false end
    local gen = rt._generation or 0
    local nv = kyohud.hud.native_visibility
    if not nv then return false end

    if self._casing_native_acquired then
        local same_targets = (self._casing_native_corner == targets.corner)
            and (self._casing_native_targets ~= nil)
        if same_targets and self._casing_native_targets.icon and targets.icon then
            if self._casing_native_targets.icon ~= targets.icon then same_targets = false end
        else
            same_targets = false
        end
        if not same_targets then
            local released = self:_release_casing_native()
            if not released then return false end
        else
            local requests = self._casing_native_requests
            if requests then
                for _, req in ipairs(requests) do
                    local actual, err = nv:_read_value(req.id, req.property)
                    if err or actual == nil or actual ~= req.value then
                        self._casing_conflict_corner = self._casing_native_corner
                        self:_release_casing_native()
                        return false
                    end
                end
            end
            return true
        end
    elseif self._casing_native_corner or self._casing_native_targets then
        local released = self:_release_casing_native()
        if not released then return false end
    end

    local visible_objs = { targets.icon }
    for _, leaf in ipairs(targets.bg_leaves) do
        visible_objs[#visible_objs + 1] = leaf
    end
    for _, obj in ipairs(visible_objs) do
        nv._whitelist[obj] = nv._whitelist[obj] or {}
        nv._whitelist[obj].visible = true
    end
    nv._whitelist[targets.text_panel] = nv._whitelist[targets.text_panel] or {}
    nv._whitelist[targets.text_panel].alpha = true

    local requests = {}
    for _, obj in ipairs(visible_objs) do
        requests[#requests + 1] = { id = obj, property = "visible", value = false }
    end
    requests[#requests + 1] = { id = targets.text_panel, property = "alpha", value = 0 }

    self._casing_native_requests = requests
    self._casing_native_corner = targets.corner
    self._casing_native_hud_panel = targets.hud_panel
    self._casing_native_targets = targets
    self._casing_native_generation = gen
    local acquired = nv:acquire("alerts", gen, requests)
    if acquired then
        self._casing_native_acquired = true
        return true
    end
    self._casing_native_acquired = false
    return false
end

function AL:_release_casing_native()
    if not self._casing_native_acquired and not self._casing_native_corner and not self._casing_native_targets then
        return true
    end
    local nv = kyohud.hud.native_visibility
    if not nv then return false end
    local gen = self._casing_native_generation
    if gen and self._casing_native_requests then
        nv:release("alerts", gen)
    end
    local pending = false
    for _, e in ipairs(nv._entries or {}) do
        if e.owner == "alerts" and (gen == nil or e.generation == gen) then
            pending = true
            break
        end
    end
    if pending then
        self._casing_native_acquired = false
        return false
    end
    local targets = self._casing_native_targets
    if targets then
        local visible_objs = { targets.icon }
        for _, leaf in ipairs(targets.bg_leaves) do
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
    self._casing_native_corner = nil
    self._casing_native_hud_panel = nil
    self._casing_native_targets = nil
    self._casing_native_requests = nil
    self._casing_native_acquired = false
    self._casing_native_generation = 0
    return true
end

function AL:_compute_casing_layout(parent_w, parent_h)
    if not al_is_finite(parent_w) or not al_is_finite(parent_h) then return nil end
    if parent_w <= 0 or parent_h <= 0 then return nil end
    local layout = kyohud.hud.layout
    if not layout or type(layout.assault_alerts) ~= "function" then return nil end
    local scale = (kyohud.settings and kyohud.settings.hud_scale) or 1
    local geom = layout.assault_alerts(parent_w, parent_h, scale, "casing")
    if not geom or not geom.valid then return nil end
    local es = geom.es or 1
    if type(layout.objectives_region) == "function" then
        local obj = layout.objectives_region(parent_w, parent_h)
        if obj and geom.root_x < obj.w and geom.root_y < obj.h then return nil end
    end
    local ticker_w = REF_CASING_TICKER_W * es
    local ticker_h = geom.ticker.h
    local font_size = geom.ticker_font
    return {
        es = es,
        root_x = geom.root_x, root_y = geom.root_y,
        root_w = geom.root_w, root_h = geom.root_h,
        font_size = font_size,
        ticker = { x = 0, y = 0, w = ticker_w, h = ticker_h },
        bg = geom.bg,
        icon = geom.status,
    }
end

function AL:_update_casing_layout()
    if not self._casing_root_panel or not al_panel_alive(self._casing_root_panel) then return end
    if not self._parent_panel or not al_panel_alive(self._parent_panel) then return end
    local pw_s, pw = al_safe_call(self._parent_panel, "w")
    local ph_s, ph = al_safe_call(self._parent_panel, "h")
    if pw_s ~= CALL_OK or ph_s ~= CALL_OK then return end
    if not al_is_finite(pw) or not al_is_finite(ph) then return end
    if pw <= 0 or ph <= 0 then return end
    local new_layout = self:_compute_casing_layout(pw, ph)
    if not new_layout then
        self._casing_layout_cache = nil
        return
    end
    local changed = not self._casing_layout_cache
        or self._casing_layout_cache.root_x ~= new_layout.root_x
        or self._casing_layout_cache.root_y ~= new_layout.root_y
        or self._casing_layout_cache.root_w ~= new_layout.root_w
        or self._casing_layout_cache.root_h ~= new_layout.root_h
        or self._casing_layout_cache.font_size ~= new_layout.font_size
    if not changed then return end
    al_safe_call(self._casing_root_panel, "set_shape", new_layout.root_x, new_layout.root_y, new_layout.root_w, new_layout.root_h)
    if self._casing_ticker_panel and al_panel_alive(self._casing_ticker_panel) then
        al_safe_call(self._casing_ticker_panel, "set_shape", new_layout.ticker.x, new_layout.ticker.y, new_layout.ticker.w, new_layout.ticker.h)
    end
    if self._casing_bg and al_panel_alive(self._casing_bg) and new_layout.bg then
        al_safe_call(self._casing_bg, "set_shape", new_layout.bg.x, new_layout.bg.y, new_layout.bg.w, new_layout.bg.h)
    end
    if self._casing_icon and al_panel_alive(self._casing_icon) and new_layout.icon then
        al_safe_call(self._casing_icon, "set_shape", new_layout.icon.x, new_layout.icon.y, new_layout.icon.w, new_layout.icon.h)
    end
    if self._casing_a and al_panel_alive(self._casing_a) then
        al_safe_call(self._casing_a, "set_font_size", new_layout.font_size)
    end
    if self._casing_b and al_panel_alive(self._casing_b) then
        al_safe_call(self._casing_b, "set_font_size", new_layout.font_size)
    end
    if self._casing_a and al_panel_alive(self._casing_a) then
        local ok_mr, mx, my, mw, mh = pcall(function() return self._casing_a:text_rect() end)
        if ok_mr and al_is_finite(mw) and mw > 0 then
            self._casing_measured_w = mw
            local ticker_h = new_layout.ticker.h
            local ax = self._casing_x_a or 0
            al_safe_call(self._casing_a, "set_shape", ax, 0, mw, ticker_h)
            local gap = self._casing_gap or (REF_CASING_TICKER_GAP * (new_layout.es or 1))
            local bx = self._casing_x_b or (mw + gap)
            al_safe_call(self._casing_b, "set_shape", bx, 0, mw, ticker_h)
        end
    end
    self._casing_layout_cache = new_layout
end

function AL:_ensure_casing_ticker_panel()
    if self._casing_ticker_panel and al_panel_alive(self._casing_ticker_panel) then return end
    if not self._casing_root_panel or not al_panel_alive(self._casing_root_panel) then return end
    if not self._casing_layout_cache then return end
    local layout = self._casing_layout_cache
    local status, pnl = al_safe_call(self._casing_root_panel, "panel", {
        name = CASING_TICKER_NAME,
        x = layout.ticker.x, y = layout.ticker.y,
        w = layout.ticker.w, h = layout.ticker.h,
        clipping = true,
        layer = 1,
    })
    if status == CALL_OK and pnl then
        self._casing_ticker_panel = pnl
    end
end

function AL:_ensure_casing_ticker_texts()
    if self._casing_a and al_panel_alive(self._casing_a)
        and self._casing_b and al_panel_alive(self._casing_b) then return end
    if not self._casing_ticker_panel or not al_panel_alive(self._casing_ticker_panel) then return end
    if not self._casing_layout_cache then return end
    local font = self:_get_font()
    local layout = self._casing_layout_cache
    local text_color = Color(1, AMBER_R, AMBER_G, AMBER_B)
    local ticker_text = self:_resolve_casing_ticker_text()
    local sa, pa = al_safe_call(self._casing_ticker_panel, "text", {
        name = CASING_A_NAME,
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
    if sa == CALL_OK and pa then
        self._casing_a = pa
        self._casing_cached_ticker_text = ticker_text
        self._casing_cached_font = font
        self._casing_cached_font_size = layout.font_size
        self._casing_x_a = 0
        self._casing_gap = REF_CASING_TICKER_GAP * (layout.es or 1)
        local ok_mr, mx, my, mw, mh = pcall(function() return pa:text_rect() end)
        if ok_mr and al_is_finite(mw) and mw > 0 then
            self._casing_measured_w = mw
            al_safe_call(pa, "set_shape", 0, 0, mw, layout.ticker.h)
        end
    end
    local mw = self._casing_measured_w or 0
    local gap = self._casing_gap or (REF_CASING_TICKER_GAP * ((self._casing_layout_cache and self._casing_layout_cache.es) or 1))
    local bx = mw + gap
    local ticker_w = mw > 0 and mw or layout.ticker.w
    local sb, pb = al_safe_call(self._casing_ticker_panel, "text", {
        name = CASING_B_NAME,
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
    if sb == CALL_OK and pb then
        self._casing_b = pb
        self._casing_x_b = bx
    end
end

function AL:_ensure_casing_bg()
    if self._casing_bg and al_panel_alive(self._casing_bg) then return end
    if not self._casing_root_panel or not al_panel_alive(self._casing_root_panel) then return end
    if not self._casing_layout_cache then return end
    local layout = self._casing_layout_cache
    local bg = layout.bg
    if not bg then return end
    local status, prim = al_safe_call(self._casing_root_panel, "rect", {
        name = CASING_BG_NAME,
        x = bg.x, y = bg.y, w = bg.w, h = bg.h,
        color = Color(0.80, DARK_R, DARK_G, DARK_B),
        visible = true,
        layer = 0,
    })
    if status == CALL_OK and prim then
        self._casing_bg = prim
    end
end

function AL:_ensure_casing_icon()
    if self._casing_icon and al_panel_alive(self._casing_icon) then return end
    if not self._casing_root_panel or not al_panel_alive(self._casing_root_panel) then return end
    if not self._casing_layout_cache then return end
    local layout = self._casing_layout_cache
    local icon = layout.icon
    if not icon then return end
    local status, prim = al_create_bitmap(self._casing_root_panel, {
        name = CASING_ICON_NAME,
        texture = CASING_TEXTURE_STEALTH,
        x = icon.x, y = icon.y, w = icon.w, h = icon.h,
        visible = true,
        layer = 1,
    })
    if status == CALL_OK and prim then
        self._casing_icon = prim
    end
end

function AL:_ensure_casing_primitives()
    self:_ensure_casing_bg()
    self:_ensure_casing_icon()
    self:_ensure_casing_ticker_panel()
    self:_ensure_casing_ticker_texts()
end

function AL:_sync_casing_ticker_text()
    if not self._casing_a or not al_panel_alive(self._casing_a) then return end
    if not self._casing_b or not al_panel_alive(self._casing_b) then return end
    local new_text = self:_resolve_casing_ticker_text()
    local needs_measure = false
    if new_text ~= self._casing_cached_ticker_text then
        al_safe_call(self._casing_a, "set_text", new_text)
        al_safe_call(self._casing_b, "set_text", new_text)
        local ok_ra, ra = pcall(function() return self._casing_a:text() end)
        local ok_rb, rb = pcall(function() return self._casing_b:text() end)
        if ok_ra and ra == new_text and ok_rb and rb == new_text then
            self._casing_cached_ticker_text = new_text
        end
        needs_measure = true
    else
        local ok_a, actual_a = pcall(function() return self._casing_a:text() end)
        if ok_a and type(actual_a) == "string" and actual_a ~= new_text then
            al_safe_call(self._casing_a, "set_text", new_text)
            needs_measure = true
        end
        local ok_b, actual_b = pcall(function() return self._casing_b:text() end)
        if ok_b and type(actual_b) == "string" and actual_b ~= new_text then
            al_safe_call(self._casing_b, "set_text", new_text)
            needs_measure = true
        end
    end
    if needs_measure then
        local ok_mr, mx, my, mw, mh = pcall(function() return self._casing_a:text_rect() end)
        if ok_mr and al_is_finite(mw) and mw > 0 then
            self._casing_measured_w = mw
            local ticker_h = (self._casing_layout_cache and self._casing_layout_cache.ticker and self._casing_layout_cache.ticker.h) or REF_CASING_TICKER_H
            local ax = self._casing_x_a or 0
            al_safe_call(self._casing_a, "set_shape", ax, 0, mw, ticker_h)
            local bx = self._casing_x_b or (mw + (self._casing_gap or REF_CASING_TICKER_GAP))
            al_safe_call(self._casing_b, "set_shape", bx, 0, mw, ticker_h)
        end
    end
end

function AL:_sync_casing_primitives()
    self:_sync_casing_ticker_text()
    local g = self._casing_layout_cache
    if not g then return end
    al_shape(self._casing_root_panel,g.root_x,g.root_y,g.root_w,g.root_h)
    al_shape(self._casing_ticker_panel,g.ticker.x,g.ticker.y,g.ticker.w,g.ticker.h)
    al_shape(self._casing_bg,g.bg.x,g.bg.y,g.bg.w,g.bg.h)
    al_shape(self._casing_icon,g.icon.x,g.icon.y,g.icon.w,g.icon.h)
    al_font_size(self._casing_a,g.font_size)
    al_font_size(self._casing_b,g.font_size)
    local ok, _, _, w = pcall(function() return self._casing_a:text_rect() end)
    if ok and al_is_finite(w) and w>0 then
        self._casing_measured_w = w
        self._casing_gap = REF_CASING_TICKER_GAP*g.es
        local cycle = w+self._casing_gap
        self._casing_x_a = -((-(self._casing_x_a or 0))%cycle)
        self._casing_x_b = self._casing_x_a+cycle
        al_shape(self._casing_a,self._casing_x_a,0,w,g.ticker.h)
        al_shape(self._casing_b,self._casing_x_b,0,w,g.ticker.h)
    end
    al_style(self._casing_bg,DARK_R,DARK_G,DARK_B,.8,0)
    al_style(self._casing_icon,1,1,1,1,1)
    al_style(self._casing_a,AMBER_R,AMBER_G,AMBER_B,1,1)
    al_style(self._casing_b,AMBER_R,AMBER_G,AMBER_B,1,1)
end

function AL:_update_casing_ticker(dt)
    if not self._casing_a or not al_panel_alive(self._casing_a) then return end
    if not self._casing_b or not al_panel_alive(self._casing_b) then return end
    if not self._casing_ticker_panel or not al_panel_alive(self._casing_ticker_panel) then return end
    if not al_is_finite(dt) or dt <= 0 then return end
    local es = (self._casing_layout_cache and self._casing_layout_cache.es) or 1
    local speed = REF_CASING_TICKER_SPEED * es
    local dx = speed * dt
    local ax = self._casing_x_a - dx
    local cycle = (self._casing_measured_w or 0) + (self._casing_gap or (REF_CASING_TICKER_GAP * es))
    if cycle > 0 then
        ax = -(((-ax) % cycle))
    end
    local bx = ax + cycle
    al_safe_call(self._casing_a, "set_x", ax)
    self._casing_x_a = ax
    al_safe_call(self._casing_b, "set_x", bx)
    self._casing_x_b = bx
end

function AL:_verify_casing_render()
    if not self._casing_layout_cache then
        self._casing_render_verified = false
        return false
    end
    local geom = self._casing_layout_cache
    if not al_is_finite(geom.root_w) or not al_is_finite(geom.root_h) or not al_is_finite(geom.font_size) then
        self._casing_render_verified = false
        return false
    end
    if geom.root_w <= 0 or geom.root_h <= 0 or geom.font_size <= 0 then
        self._casing_render_verified = false
        return false
    end
    if not self._casing_root_panel or not al_panel_alive(self._casing_root_panel) then
        self._casing_render_verified = false
        return false
    end
    if not self._casing_ticker_panel or not al_panel_alive(self._casing_ticker_panel) then
        self._casing_render_verified = false
        return false
    end
    if not self._casing_a or not al_panel_alive(self._casing_a) then
        self._casing_render_verified = false
        return false
    end
    if not self._casing_b or not al_panel_alive(self._casing_b) then
        self._casing_render_verified = false
        return false
    end
    local tol = 0.5
    local ox_s, ox = al_safe_call(self._casing_root_panel, "x")
    local oy_s, oy = al_safe_call(self._casing_root_panel, "y")
    local ow_s, ow = al_safe_call(self._casing_root_panel, "w")
    local oh_s, oh = al_safe_call(self._casing_root_panel, "h")
    if ox_s ~= CALL_OK or oy_s ~= CALL_OK or ow_s ~= CALL_OK or oh_s ~= CALL_OK then
        self._casing_render_verified = false
        return false
    end
    if not al_is_finite(ox) or not al_is_finite(oy) or not al_is_finite(ow) or not al_is_finite(oh) then
        self._casing_render_verified = false
        return false
    end
    if math.abs(ox - geom.root_x) > tol or math.abs(oy - geom.root_y) > tol
        or math.abs(ow - geom.root_w) > tol or math.abs(oh - geom.root_h) > tol then
        self._casing_render_verified = false
        return false
    end
    local ok_vis, vis = pcall(function() return self._casing_root_panel:visible() end)
    if not ok_vis or vis ~= true then
        self._casing_render_verified = false
        return false
    end
    local expected_root_alpha = 1
    if self._casing_closing and self._casing_close_exit_alpha ~= nil then
        expected_root_alpha = self._casing_close_exit_alpha
    end
    local ok_ra, ra = pcall(function() return self._casing_root_panel:alpha() end)
    if not ok_ra or not al_is_finite(ra) then
        self._casing_render_verified = false
        return false
    end
    local alpha_tol = 0.05
    if math.abs(ra - expected_root_alpha) > alpha_tol then
        self._casing_render_verified = false
        return false
    end
    local closing_root_alpha = nil
    if self._casing_closing and self._casing_close_exit_alpha ~= nil then
        closing_root_alpha = self._casing_close_exit_alpha
    end
    local bg_eff_color_alpha = nil
    local icon_eff_color_alpha = nil
    local ticker_eff_color_alpha = nil
    if closing_root_alpha ~= nil then
        bg_eff_color_alpha = 0.80 * closing_root_alpha
        icon_eff_color_alpha = closing_root_alpha
        ticker_eff_color_alpha = closing_root_alpha
    end
    local ok_pr, pr = pcall(function() return self._casing_root_panel:parent() end)
    local rt = kyohud.hud.runtime
    if not ok_pr or pr ~= (rt and rt._root_panel) then
        self._casing_render_verified = false
        return false
    end
    local ok_cv, cv = pcall(function() return self._casing_ticker_panel:visible() end)
    if not ok_cv or cv ~= true then
        self._casing_render_verified = false
        return false
    end
    local ok_geometry, geometry = pcall(function()
        local p, t = self._casing_ticker_panel, geom.ticker
        if p:parent() ~= self._casing_root_panel then return false end
        local px, py, pw, ph = p:x(), p:y(), p:w(), p:h()
        if not al_is_finite(px) or not al_is_finite(py) or not al_is_finite(pw) or not al_is_finite(ph) then return false end
        if math.abs(px - t.x) > tol or math.abs(py - t.y) > tol
            or math.abs(pw - t.w) > tol or math.abs(ph - t.h) > tol then return false end
        if p:alpha() ~= 1 then return false end
        if p:layer() ~= 1 then return false end
        return true
    end)
    if not ok_geometry or not geometry then
        self._casing_render_verified = false
        return false
    end
    if not self:_verify_casing_decoration(self._casing_bg, CASING_BG_NAME, geom.bg, DARK_R, DARK_G, DARK_B, 0.80, "_casing_bg", bg_eff_color_alpha)
        or not al_style_matches(self._casing_bg,DARK_R,DARK_G,DARK_B,.8,0,bg_eff_color_alpha) then
        self._casing_render_verified = false
        return false
    end
    if not self:_verify_casing_icon(self._casing_icon, CASING_ICON_NAME, geom.icon, CASING_TEXTURE_STEALTH)
        or not al_style_matches(self._casing_icon,1,1,1,1,1,icon_eff_color_alpha) then
        self._casing_render_verified = false
        return false
    end
    local desired_ticker = self._casing_cached_ticker_text
    if type(desired_ticker) ~= "string" or desired_ticker == "" then
        self._casing_render_verified = false
        return false
    end
    local function check_text(prim, desired, region, skip_x, width_override)
        local ok_v, v = pcall(function() return prim:visible() end)
        if not ok_v or v ~= true then return false end
        local ok_t, t = pcall(function() return prim:text() end)
        if not ok_t or type(t) ~= "string" then return false end
        if t ~= desired then return false end
        local ok_fs, fs = pcall(function() return prim:font_size() end)
        if not ok_fs or not al_is_finite(fs) or fs <= 0 then return false end
        if math.abs(fs - geom.font_size) > 0.5 then return false end
        local s_px, px = al_safe_call(prim, "x")
        local s_py, py = al_safe_call(prim, "y")
        local s_pw, pw = al_safe_call(prim, "w")
        local s_ph, ph = al_safe_call(prim, "h")
        if s_px ~= CALL_OK or s_py ~= CALL_OK or s_pw ~= CALL_OK or s_ph ~= CALL_OK then
            return false
        end
        if not al_is_finite(px) or not al_is_finite(py) or not al_is_finite(pw) or not al_is_finite(ph) then
            return false
        end
        if not skip_x and math.abs(px - region.x) > tol then return false end
        if math.abs(py - region.y) > tol then return false end
        local expected_w = width_override or region.w
        if math.abs(pw - expected_w) > tol then return false end
        if math.abs(ph - region.h) > tol then return false end
        if not al_style_matches(prim,AMBER_R,AMBER_G,AMBER_B,1,1,ticker_eff_color_alpha) then return false end
        local ok_parent, parent = pcall(function() return prim:parent() end)
        if not ok_parent or parent~=self._casing_ticker_panel then return false end
        local expected_x = prim==self._casing_a and self._casing_x_a or self._casing_x_b
        if not al_is_finite(expected_x) or math.abs(px-expected_x)>tol then return false end
        local ok_measure, _, _, mw, mh = pcall(function() return prim:text_rect() end)
        if not ok_measure or not al_is_finite(mw) or not al_is_finite(mh)
            or mw<=0 or mh<=0 or mh>ph+tol or math.abs(mw-pw)>tol then return false end
        return true
    end
    if not check_text(self._casing_a, desired_ticker, geom.ticker, true, self._casing_measured_w) then
        self._casing_render_verified = false
        return false
    end
    if not check_text(self._casing_b, desired_ticker, geom.ticker, true, self._casing_measured_w) then
        self._casing_render_verified = false
        return false
    end
    self._casing_render_verified = true
    return true
end

function AL:_verify_casing_decoration(prim, child_name, region, er, eg, eb, ea, _, expected_color_alpha)
    if not prim or not al_panel_alive(prim) then return false end
    local ok_ch, ch = pcall(function() return self._casing_root_panel:child(child_name) end)
    if not ok_ch or ch ~= prim then return false end
    local ok_pr, pr = pcall(function() return prim:parent() end)
    if not ok_pr or pr ~= self._casing_root_panel then return false end
    local ok_v, v = pcall(function() return prim:visible() end)
    if not ok_v or v ~= true then return false end
    local tol = 0.5
    local s_px, px = al_safe_call(prim, "x")
    local s_py, py = al_safe_call(prim, "y")
    local s_pw, pw = al_safe_call(prim, "w")
    local s_ph, ph = al_safe_call(prim, "h")
    if s_px ~= CALL_OK or s_py ~= CALL_OK or s_pw ~= CALL_OK or s_ph ~= CALL_OK then
        return false
    end
    if not al_is_finite(px) or not al_is_finite(py) or not al_is_finite(pw) or not al_is_finite(ph) then
        return false
    end
    if region then
        if math.abs(px - region.x) > tol or math.abs(py - region.y) > tol
            or math.abs(pw - region.w) > tol or math.abs(ph - region.h) > tol then
            return false
        end
    end
    if er then
        local c = al_read_color(prim)
        if not c then return false end
        if math.abs(c.r - er) > 0.02 or math.abs(c.g - eg) > 0.02 or math.abs(c.b - eb) > 0.02 then
            return false
        end
        local color_a_desired = expected_color_alpha
        if color_a_desired == nil then color_a_desired = ea end
        if color_a_desired ~= nil and math.abs(c.a - color_a_desired) > 0.05 then
            return false
        end
    end
    return true
end

function AL:_verify_casing_icon(prim, child_name, region, expected_texture)
    if not prim or not al_panel_alive(prim) then return false end
    local ok_ch, ch = pcall(function() return self._casing_root_panel:child(child_name) end)
    if not ok_ch or ch ~= prim then return false end
    local ok_pr, pr = pcall(function() return prim:parent() end)
    if not ok_pr or pr ~= self._casing_root_panel then return false end
    local ok_v, v = pcall(function() return prim:visible() end)
    if not ok_v or v ~= true then return false end
    local ok_tex, tex = pcall(function() return prim:texture_name() end)
    if not ok_tex or not al_texture_matches(tex, expected_texture) then
        return false
    end
    local tol = 0.5
    local s_px, px = al_safe_call(prim, "x")
    local s_py, py = al_safe_call(prim, "y")
    local s_pw, pw = al_safe_call(prim, "w")
    local s_ph, ph = al_safe_call(prim, "h")
    if s_px ~= CALL_OK or s_py ~= CALL_OK or s_pw ~= CALL_OK or s_ph ~= CALL_OK then
        return false
    end
    if not al_is_finite(px) or not al_is_finite(py) or not al_is_finite(pw) or not al_is_finite(ph) then
        return false
    end
    if region then
        if math.abs(px - region.x) > tol or math.abs(py - region.y) > tol
            or math.abs(pw - region.w) > tol or math.abs(ph - region.h) > tol then
            return false
        end
    end
    return true
end

function AL:_handle_casing_render_failure()
    self._casing_render_failed = true
    self._casing_render_verified = false
    if self._casing_root_panel and al_panel_alive(self._casing_root_panel) then
        al_safe_call(self._casing_root_panel, "set_visible", false)
    end
    self:_release_casing_native()
end

function AL:_sync_casing_native_visibility()
    if self._native_acquired or self._native_corner or self._native_targets then
        self:_release_native()
    end
    if self._root_panel and al_panel_alive(self._root_panel) then
        al_safe_call(self._root_panel, "set_visible", false)
    end
    self._render_verified = false

    local should_fallback = self:_should_fallback_casing_native()

    if should_fallback then
        if self._casing_native_acquired or self._casing_native_corner or self._casing_native_targets then
            self:_release_casing_native()
        end
        if self._casing_root_panel and al_panel_alive(self._casing_root_panel) then
            al_safe_call(self._casing_root_panel, "set_visible", false)
        end
        self._casing_render_verified = false
        return false
    end

    al_safe_call(self._casing_root_panel, "set_visible", true)

    if not self:_verify_casing_render() then
        self:_handle_casing_render_failure()
        return false
    end

    if not self:_try_acquire_casing_native() then
        self:_release_casing_native()
        al_safe_call(self._casing_root_panel, "set_visible", false)
        self._casing_render_verified = false
        return false
    end

    return true
end

function AL:_begin_casing_close()
    if self._casing_closing then return end
    if not self._mounted then return end
    if not kyohud.settings or kyohud.settings.enable_hud_foundation ~= true or kyohud.settings.enable_alerts ~= true then return end
    if al_is_vr() then return end
    if not self._manager then return end
    if not self._casing_native_acquired then return end
    if self:_should_fallback_casing_native() then return end
    if not self:_verify_casing_render() then return end
    local ok_corner, corner = pcall(function() return self._manager._hud_assault_corner end)
    if not ok_corner or not corner then return end
    local ok_pnr, pnr = pcall(function() return corner._point_of_no_return end)
    if ok_pnr and pnr == true then return end
    local ok_am, am = pcall(function() return corner._assault_mode end)
    if ok_am and am == "phalanx" then return end
    local ok_wfn, wfn = pcall(function() return corner.should_display_waves end)
    if ok_wfn and type(wfn) == "function" then
        local ok_waves, waves = pcall(wfn, corner)
        if ok_waves and waves == true then return end
    end
    local ok_state, state = pcall(function() return managers.groupai and managers.groupai:state() end)
    if not ok_state then state = nil end
    if state == nil then return end
    local bg, icon
    local ok_bg, bg_val = pcall(function() return corner._casing_bg_box end)
    if ok_bg and bg_val and al_panel_alive(bg_val) then bg = bg_val end
    local ok_hp, hp = pcall(function() return corner._hud_panel end)
    if ok_hp and hp and al_panel_alive(hp) then
        local ok_cp, cp = pcall(function() return hp:child("casing_panel") end)
        if ok_cp and cp and al_panel_alive(cp) then
            local ok_ic, ic = pcall(function() return cp:child("icon_casingbox") end)
            if ok_ic and ic and al_panel_alive(ic) then icon = ic end
        end
    end
    if not bg or not icon then return end
    if not self._casing_root_panel or not al_panel_alive(self._casing_root_panel) then return end
    local rt = kyohud.hud.runtime
    if not rt then return end
    local gen = rt._generation or 0
    self._casing_closing = true
    self._casing_close_manager = self._manager
    self._casing_close_corner = corner
    self._casing_close_state = state
    self._casing_close_bg_box = bg
    self._casing_close_icon = icon
    self._casing_close_bg_done = false
    self._casing_close_icon_done = false
    self._casing_close_exit_alpha = 1
    self._casing_close_generation = gen
end

function AL:_check_casing_close_complete()
    return self._casing_close_bg_done == true
        and self._casing_close_icon_done == true
end

function AL:_complete_casing_close()
    self:_release_casing_native()
    if self._casing_root_panel and al_panel_alive(self._casing_root_panel) then
        al_safe_call(self._casing_root_panel, "set_alpha", 1)
        al_safe_call(self._casing_root_panel, "set_visible", false)
    end
    self._casing_closing = false
    self._casing_close_manager = nil
    self._casing_close_corner = nil
    self._casing_close_state = nil
    self._casing_close_bg_box = nil
    self._casing_close_icon = nil
    self._casing_close_bg_done = false
    self._casing_close_icon_done = false
    self._casing_close_exit_alpha = nil
    self._casing_close_generation = nil
    self._casing_mode = nil
    self._casing_active = false
    self._casing_render_verified = false
end

function AL:_validate_casing_close_identity()
    if not self._casing_closing then return false end
    if not self._mounted then return false end
    if not kyohud.settings or kyohud.settings.enable_hud_foundation ~= true or kyohud.settings.enable_alerts ~= true then return false end
    if al_is_vr() then return false end
    local ok_manager, current_manager = pcall(function() return self._manager end)
    if not ok_manager or current_manager ~= self._casing_close_manager then return false end
    local rt = kyohud.hud.runtime
    if not rt or not rt._mounted then return false end
    local current_gen = rt._generation or 0
    if self._casing_close_generation ~= nil and current_gen ~= self._casing_close_generation then return false end
    if not self._casing_root_panel or not al_panel_alive(self._casing_root_panel) then return false end
    local ok_corner, current_corner = pcall(function() return self._manager._hud_assault_corner end)
    if not ok_corner or current_corner ~= self._casing_close_corner then return false end
    local ok_pnr, pnr = pcall(function() return current_corner._point_of_no_return end)
    if ok_pnr and pnr == true then return false end
    local ok_am, am = pcall(function() return current_corner._assault_mode end)
    if ok_am and am == "phalanx" then return false end
    local ok_wfn, wfn = pcall(function() return current_corner.should_display_waves end)
    if ok_wfn and type(wfn) == "function" then
        local ok_waves, waves = pcall(wfn, current_corner)
        if ok_waves and waves == true then return false end
    end
    local ok_state, current_state = pcall(function() return managers.groupai and managers.groupai:state() end)
    if not ok_state then current_state = nil end
    if self._casing_close_state ~= nil and current_state ~= self._casing_close_state then return false end
    if self._casing_close_state == nil then return false end
    local ok_bg, current_bg = pcall(function() return self._casing_close_corner._casing_bg_box end)
    if not ok_bg or current_bg ~= self._casing_close_bg_box then return false end
    local ok_icon, current_icon = pcall(function()
        local hp = self._casing_close_corner._hud_panel
        if not hp then return nil end
        local cp = hp:child("casing_panel")
        if not cp then return nil end
        return cp:child("icon_casingbox")
    end)
    if not ok_icon or current_icon ~= self._casing_close_icon then return false end
    return true
end

function AL:_sync_casing_closing()
    if not self:_validate_casing_close_identity() then
        self:_complete_casing_close()
        return false
    end
    if self._casing_native_acquired and self._casing_native_requests then
        local nv = kyohud.hud.native_visibility
        if nv then
            for _, req in ipairs(self._casing_native_requests) do
                local actual, err = nv:_read_value(req.id, req.property)
                if err or actual == nil or actual ~= req.value then
                    self:_complete_casing_close()
                    return false
                end
            end
        end
    end
    if self:_check_casing_close_complete() then
        self:_complete_casing_close()
        return false
    end
    if self._casing_root_panel and al_panel_alive(self._casing_root_panel) then
        al_safe_call(self._casing_root_panel, "set_visible", true)
    end
    if self._casing_close_exit_alpha ~= nil
        and self._casing_root_panel and al_panel_alive(self._casing_root_panel) then
        al_safe_call(self._casing_root_panel, "set_alpha", self._casing_close_exit_alpha)
    end
    if not self:_verify_casing_render() then
        self:_complete_casing_close()
        return false
    end
    return true
end

function AL:_update_casing_close_exit(dt)
    if not self._casing_closing then return end
    if not al_is_finite(dt) or dt <= 0 then return end
    local exit_alpha = self._casing_close_exit_alpha
    if exit_alpha == nil then exit_alpha = 1 end
    exit_alpha = exit_alpha - dt * 3
    if exit_alpha < 0 then exit_alpha = 0 end
    self._casing_close_exit_alpha = exit_alpha
    if self._casing_root_panel and al_panel_alive(self._casing_root_panel) then
        al_safe_call(self._casing_root_panel, "set_alpha", exit_alpha)
    end
end

function AL:_ensure_casing_root()
    if not self._parent_panel or not al_panel_alive(self._parent_panel) then return end
    if self._casing_root_panel and al_panel_alive(self._casing_root_panel) then return end
    local rt = kyohud.hud.runtime
    if not rt or not rt._mounted then return end
    local parent = rt._root_panel
    if not parent or not al_panel_alive(parent) then return end
    self._parent_panel = parent
    local status, existing = al_safe_call(parent, "child", CASING_ROOT_NAME)
    if status == CALL_OK and existing ~= nil and al_panel_alive(existing) then
        if self._casing_root_panel == existing then return end
        return
    end
    if status ~= CALL_OK then return end
    local cs, root = al_safe_call(parent, "panel", { name = CASING_ROOT_NAME, visible = false })
    if cs ~= CALL_OK or root == nil then return end
    self._casing_root_panel = root
end

function AL:_destroy_casing_root()
    if not self._casing_root_panel then return true end
    if al_panel_alive(self._casing_root_panel) then
        al_safe_call(self._casing_root_panel, "set_visible", false)
        local parent = self._parent_panel
        if parent and al_panel_alive(parent) then
            al_safe_call(parent, "remove", self._casing_root_panel)
        end
    end
    self._casing_root_panel = nil
    self._casing_ticker_panel = nil
    self._casing_a = nil
    self._casing_b = nil
    self._casing_bg = nil
    self._casing_icon = nil
    self._casing_layout_cache = nil
    self._casing_render_verified = false
    self._casing_render_failed = false
    self._casing_cached_ticker_text = nil
    self._casing_cached_font = nil
    self._casing_cached_font_size = nil
    self._casing_x_a = 0
    self._casing_x_b = 0
    self._casing_measured_w = 0
    self._casing_gap = nil
    return true
end

function AL:_take_initial_snapshot()
    if not self._snapshot_taken then
        self:snapshot(self._manager)
        self._snapshot_taken = true
    end
end

function AL:mount(manager)
    if not kyohud.settings or kyohud.settings.enable_hud_foundation ~= true then
        return
    end
    if kyohud.settings.enable_alerts ~= true then
        return
    end
    if al_is_vr() then
        return
    end
    local mgr = manager or self._manager
    if not mgr then
        return
    end
    self._manager = mgr
    local parent = al_get_runtime_root()
    if not parent then
        return
    end

    if self._mounted and self._root_panel and al_panel_alive(self._root_panel) then
        if self._parent_panel == parent then
            self:_update_layout()
            return
        end
        local removed = self:unmount()
        if not removed then return end
    end

    if self._root_panel and not al_panel_alive(self._root_panel) then
        self._root_panel = nil
        self._title_prim = nil
        self._status_prim = nil
        self._timer_prim = nil
        self._pnr_bg = nil
        self._pnr_icon = nil
        self._pnr_status_bg = nil
        self._pnr_timer_measured_w = 0
    end

    local status, existing = al_safe_call(parent, "child", ALERTS_ROOT_NAME)
    if status == CALL_OK and existing ~= nil and al_panel_alive(existing) then
        if self._root_panel == existing then
            self._mounted = true
            self._parent_panel = parent
            self:_take_initial_snapshot()
            self:_update_layout()
            self:_ensure_primitives()
            self:_ensure_casing_root()
            self:_sync_primitives()
            self:_sync_native_visibility()
            return
        end
        return
    end
    if status ~= CALL_OK then
        return
    end

    local cs, root = al_safe_call(parent, "panel", { name = ALERTS_ROOT_NAME, visible = false })
    if cs ~= CALL_OK or root == nil then
        return
    end
    self._root_panel = root
    self._parent_panel = parent
    self._mounted = true
    self:_take_initial_snapshot()
    self:_update_layout()
    self:_ensure_primitives()
    self:_ensure_casing_root()
    self:_sync_primitives()
    self:_sync_native_visibility()
end

function AL:unmount()
    local released = self:_release_native()
    if released then
        self._conflict_corner = nil
    end
    if self._casing_closing then
        self._casing_closing = false
        self._casing_close_manager = nil
        self._casing_close_corner = nil
        self._casing_close_state = nil
        self._casing_close_bg_box = nil
        self._casing_close_icon = nil
        self._casing_close_bg_done = false
        self._casing_close_icon_done = false
        self._casing_close_exit_alpha = nil
        self._casing_close_generation = nil
    end
    self:_release_casing_native()
    self._casing_conflict_corner = nil
    self:_destroy_casing_root()
    if not self._mounted and not self._root_panel then return released end
    if self._root_panel then
        if al_panel_alive(self._root_panel) then
            al_safe_call(self._root_panel, "set_visible", false)
            local parent = self._parent_panel
            if parent and al_panel_alive(parent) then
                local status, result = al_safe_call(parent, "remove", self._root_panel)
                if status == CALL_OK and result ~= false then
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
    self._title_prim = nil
    self._status_prim = nil
    self._timer_prim = nil
    self._pnr_bg = nil
    self._pnr_icon = nil
    self._pnr_status_bg = nil
    self._pnr_timer_measured_w = 0
    self._parent_panel = nil
    self._mounted = false
    self._layout_cache = nil
    self._render_verified = false
    self._render_failed = false
    self._cached_timer_text = nil
    self._cached_status_text = nil
    self._cached_title_text = nil
    self._cached_font = nil
    self._cached_font_size = nil
    return released
end

function AL:rebuild(manager)
    self:unmount()
    self:mount(manager)
end

function AL:refresh_settings(manager)
    if kyohud.settings and kyohud.settings.enable_hud_foundation == true and kyohud.settings.enable_alerts == true then
        self._conflict_corner = nil
        self._casing_conflict_corner = nil
        if not self._mounted or not self._root_panel or not al_panel_alive(self._root_panel) then
            self:mount(manager)
            return
        end
        self:_update_layout()
        self:_update_casing_layout()
        self._render_failed = false
        self._casing_render_failed = false
        self:_ensure_primitives()
        self:_ensure_casing_root()
        self:_ensure_casing_primitives()
        self:_sync_primitives()
        self:_sync_casing_primitives()
        self:_sync_native_visibility()
    else
        if self._mounted or self._root_panel or self._native_acquired or self._native_corner or self._native_targets
            or self._casing_native_acquired or self._casing_root_panel then
            self:unmount()
        end
    end
end

function AL:update(manager, t, dt)
    if not kyohud.settings or kyohud.settings.enable_hud_foundation ~= true or kyohud.settings.enable_alerts ~= true then
        if self._mounted or self._root_panel or self._native_acquired or self._native_corner or self._native_targets
            or self._casing_native_acquired or self._casing_root_panel then
            self:unmount()
        end
        return
    end
    if al_is_vr() then
        if self._mounted or self._root_panel or self._native_acquired or self._native_corner or self._native_targets
            or self._casing_native_acquired or self._casing_root_panel then
            self:unmount()
        end
        return
    end
    if self._mounted and self._root_panel and not al_panel_alive(self._root_panel) then
        self:_release_native()
        self._root_panel = nil
        self._parent_panel = nil
        self._title_prim = nil
        self._status_prim = nil
        self._timer_prim = nil
        self._pnr_bg = nil
        self._pnr_icon = nil
        self._pnr_status_bg = nil
        self._pnr_timer_measured_w = 0
        self._mounted = false
        self._layout_cache = nil
        self._render_verified = false
    end
    if self._casing_root_panel and not al_panel_alive(self._casing_root_panel) then
        self:_release_casing_native()
        self._casing_root_panel = nil
        self._casing_ticker_panel = nil
        self._casing_a = nil
        self._casing_b = nil
        self._casing_bg = nil
        self._casing_icon = nil
        self._casing_layout_cache = nil
        self._casing_render_verified = false
        if self._casing_closing then
            self._casing_closing = false
            self._casing_close_manager = nil
            self._casing_close_corner = nil
            self._casing_close_state = nil
            self._casing_close_bg_box = nil
            self._casing_close_icon = nil
            self._casing_close_bg_done = false
            self._casing_close_icon_done = false
            self._casing_close_exit_alpha = nil
            self._casing_close_generation = nil
        end
    end
    if not self._mounted then
        self:mount(manager or self._manager)
        if not self._mounted then return end
    end

    if self._casing_closing then
        self:_update_casing_close_exit(dt)
    end

    local do_poll = false
    if t and (self._last_poll_time == nil or (t - self._last_poll_time) >= POLL_INTERVAL) then
        do_poll = true
        self._last_poll_time = t
    end

    if do_poll then
        self:snapshot(self._manager)
        self:_update_layout()
        self:_update_casing_layout()
    end

    local mode = self:_determine_active_mode()

    if mode == "casing" then
        if do_poll or self._data_dirty then
            self:_ensure_casing_root()
            self:_update_casing_layout()
            self:_ensure_casing_primitives()
            self:_sync_casing_primitives()
        end
    elseif do_poll or self._data_dirty then
        self:_ensure_primitives()
        self:_sync_primitives()
    end
    self._data_dirty = false

    local sync_ok = self:_sync_native_visibility()
    if not sync_ok then
        if mode == "casing" then
            if self._casing_render_failed and do_poll then
                self._casing_render_failed = false
                self:_update_casing_layout()
                self:_ensure_casing_root()
                self:_ensure_casing_primitives()
                self:_sync_casing_primitives()
                if self._casing_root_panel and al_panel_alive(self._casing_root_panel) then
                    al_safe_call(self._casing_root_panel, "set_visible", true)
                end
                if not self:_verify_casing_render() then
                    self:_handle_casing_render_failure()
                end
            end
        elseif self._render_failed and do_poll then
            self._render_failed = false
            self:_update_layout()
            self:_ensure_primitives()
            self:_sync_primitives()
            self:_sync_native_visibility()
        end
        return
    end
    if mode == "casing" then
        self._casing_render_failed = false
    elseif mode == "casing_closing" then
        self._casing_render_failed = false
    else
        self._render_failed = false
    end
    if mode == "casing" and al_is_finite(dt) and dt > 0 then
        self:_update_casing_ticker(dt)
    end
    if mode == "casing" or mode == "casing_closing" then
        if not self:_verify_casing_render() then
            if mode == "casing_closing" then
                self:_complete_casing_close()
            else
                self:_handle_casing_render_failure()
            end
        end
    elseif not self:_verify_render() then
        self:_handle_render_failure()
    end
end

function AL:destroy(manager)
    if manager and self._manager and manager ~= self._manager then return end
    self:unmount()
end

function AL:on_heist_start(manager)
    local mgr = manager or self._manager
    if not mgr then return end
    if self._heist_manager_id == mgr then return end
    self._heist_manager_id = mgr
    if self._mounted or self._root_panel or self._native_acquired or self._native_corner or self._native_targets then
        self:unmount()
    end
    self._snapshot_taken = false
    self._last_poll_time = nil
    self._source = nil
    self._source_corner = nil
    self:_clear_event_provenance()
    self._casing_active = false
    self._casing_mode = nil
    self._state.active = false
    self._state.timer = nil
    self._state.id = nil
    self._state.tweak_id = nil
    self._state.inside = nil
    self._data_dirty = false
    self._manager = mgr
end

local function safe_prehook(class, method, id, fn)
    if type(class) ~= "table" then return end
    if kyohud.hud._installed_hooks[id] then return end
    if type(class[method]) ~= "function" then return end
    if type(Hooks) ~= "table" or type(Hooks.PreHook) ~= "function" then return end
    Hooks:PreHook(class, method, id, fn)
    kyohud.hud._installed_hooks[id] = true
end

local function safe_posthook(class, method, id, fn)
    if type(class) ~= "table" then return end
    if kyohud.hud._installed_hooks[id] then return end
    if type(class[method]) ~= "function" then return end
    if type(Hooks) ~= "table" or type(Hooks.PostHook) ~= "function" then return end
    Hooks:PostHook(class, method, id, fn)
    kyohud.hud._installed_hooks[id] = true
end

if RequiredScript == REQUIRED_CONTEXT then
    local function al_release_all_owned()
        local A = kyohud and kyohud.hud and kyohud.hud.assault
        if type(A) == "table" then
            if type(A._release_native) == "function" then
                pcall(A._release_native, A)
            end
            if A._root_panel and al_panel_alive(A._root_panel) then
                al_safe_call(A._root_panel, "set_visible", false)
            end
        end
        if AL._opening_identity then
            AL._opening_identity = nil
        end
        AL:_release_native()
        if AL._root_panel and al_panel_alive(AL._root_panel) then
            al_safe_call(AL._root_panel, "set_visible", false)
        end
        AL._render_verified = false
        if AL._casing_closing then
            AL._casing_closing = false
            AL._casing_close_manager = nil
            AL._casing_close_corner = nil
            AL._casing_close_state = nil
            AL._casing_close_bg_box = nil
            AL._casing_close_icon = nil
            AL._casing_close_bg_done = false
            AL._casing_close_icon_done = false
            AL._casing_close_exit_alpha = nil
            AL._casing_close_generation = nil
        end
        AL:_release_casing_native()
        if AL._casing_root_panel and al_panel_alive(AL._casing_root_panel) then
            al_safe_call(AL._casing_root_panel, "set_alpha", 1)
            al_safe_call(AL._casing_root_panel, "set_visible", false)
        end
        AL._casing_render_verified = false
    end

    local function cb_pre_show_pnr(self, tweak_id)
        al_release_all_owned()
    end

    local function cb_post_show_pnr(self, tweak_id)
        local _, state = AL:_bind_event_context(self)
        local s_timer, s_id, s_tweak, s_inside = read_state_fields(state)
        AL._event_has_active = true
        AL._event_active = true
        if tweak_id ~= nil then
            AL._event_has_tweak = true
            AL._event_tweak_id = tweak_id
            AL._event_state_tweak = s_tweak
        else
            AL._event_has_tweak = false
            AL._event_tweak_id = nil
            AL._event_state_tweak = nil
        end
        AL._conflict_corner = nil
        AL:snapshot(self)
        AL._snapshot_taken = true
        AL._data_dirty = true
    end

    local function cb_pre_hide_pnr(self)
        al_release_all_owned()
    end

    local function cb_post_hide_pnr(self)
        AL:_bind_event_context(self)
        AL._event_has_active = true
        AL._event_active = false
        AL._event_has_timer = false
        AL._event_timer = nil
        AL._event_has_inside = false
        AL._event_inside = nil
        AL._state.active = false
        AL._state.timer = nil
        AL._state.inside = nil
        AL._data_dirty = true
    end

    local function cb_post_feed_pnr(self, time, is_inside)
        local _, state = AL:_bind_event_context(self)
        local s_timer, _, _, s_inside = read_state_fields(state)
        AL._event_has_timer = true
        AL._event_timer = is_finite_nonneg(time) and time or nil
        AL._event_state_timer = s_timer
        AL._event_has_inside = true
        if type(is_inside) == "boolean" then
            AL._event_inside = is_inside
        else
            AL._event_inside = nil
        end
        AL._event_state_inside = s_inside
        AL._state.timer = AL._event_timer
        AL._state.inside = AL._event_inside
        AL._data_dirty = true
    end

    safe_prehook(
        HUDManager,
        "show_point_of_no_return_timer",
        "KyohHUD_Alerts_PreShowPNR",
        cb_pre_show_pnr
    )
    safe_posthook(
        HUDManager,
        "show_point_of_no_return_timer",
        "KyohHUD_Alerts_PostShowPNR",
        cb_post_show_pnr
    )
    safe_prehook(
        HUDManager,
        "hide_point_of_no_return_timer",
        "KyohHUD_Alerts_PreHidePNR",
        cb_pre_hide_pnr
    )
    safe_posthook(
        HUDManager,
        "hide_point_of_no_return_timer",
        "KyohHUD_Alerts_PostHidePNR",
        cb_post_hide_pnr
    )
    safe_posthook(
        HUDManager,
        "feed_point_of_no_return_timer",
        "KyohUD_Alerts_PostFeedPNR",
        cb_post_feed_pnr
    )

    local function resolve_open_identity(panel)
        local manager = AL._manager
        if not manager then return nil end
        local ok_corner, corner = pcall(function() return manager._hud_assault_corner end)
        if not ok_corner or not corner then return nil end
        local ok_bg, bg = pcall(function() return corner._noreturn_bg_box end)
        if not ok_bg or not bg then return nil end
        if panel ~= bg then return nil end
        return { manager = manager, corner = corner, bg_box = bg }
    end

    local function cb_pre_open_left(panel, wait_t, target_w, done_cb, config)
        local identity = resolve_open_identity(panel)
        if not identity then return end
        if AL._opening_identity then
            if AL._opening_identity.bg_box ~= identity.bg_box then
                AL:_release_native()
                AL._opening_identity = nil
            end
        end
        local certified = false
        if kyohud.settings and kyohud.settings.enable_hud_foundation == true
           and kyohud.settings.enable_alerts == true
           and AL._mounted
           and AL._manager == identity.manager then
            local ok_cc, current_corner = pcall(function() return AL._manager._hud_assault_corner end)
            if ok_cc and current_corner == identity.corner then
                AL:snapshot(AL._manager)
                AL:_update_layout()
                AL:_ensure_primitives()
                AL:_sync_primitives()
                if AL._root_panel and al_panel_alive(AL._root_panel) then
                    al_safe_call(AL._root_panel, "set_visible", true)
                end
                if AL:_verify_pnr_render() then
                    if AL:_try_acquire_native() then
                        certified = true
                    end
                end
            end
        end
        if not certified then
            AL:_release_native()
            if AL._root_panel and al_panel_alive(AL._root_panel) then
                al_safe_call(AL._root_panel, "set_visible", false)
            end
            AL._render_verified = false
        end
        AL._opening_identity = identity
    end

    local function cb_post_open_left(panel, wait_t, target_w, done_cb, config)
        local identity = AL._opening_identity
        if not identity then return end
        if panel ~= identity.bg_box then return end
        AL._opening_identity = nil
        if not kyohud.settings or kyohud.settings.enable_hud_foundation ~= true or kyohud.settings.enable_alerts ~= true then
            AL:_release_native()
            if AL._root_panel and al_panel_alive(AL._root_panel) then
                al_safe_call(AL._root_panel, "set_visible", false)
            end
            return
        end
        if AL._manager ~= identity.manager then
            AL:_release_native()
            if AL._root_panel and al_panel_alive(AL._root_panel) then
                al_safe_call(AL._root_panel, "set_visible", false)
            end
            return
        end
        local ok_current_corner, current_corner = pcall(function() return AL._manager._hud_assault_corner end)
        if not ok_current_corner or current_corner ~= identity.corner then
            AL:_release_native()
            if AL._root_panel and al_panel_alive(AL._root_panel) then
                al_safe_call(AL._root_panel, "set_visible", false)
            end
            return
        end
        if not AL._mounted then
            AL:_release_native()
            if AL._root_panel and al_panel_alive(AL._root_panel) then
                al_safe_call(AL._root_panel, "set_visible", false)
            end
            return
        end
        if not AL._root_panel or not al_panel_alive(AL._root_panel) then
            AL:_release_native()
            return
        end
        if not AL._layout_cache then
            AL:_release_native()
            if AL._root_panel and al_panel_alive(AL._root_panel) then
                al_safe_call(AL._root_panel, "set_visible", false)
            end
            return
        end
        if AL._native_acquired then
            AL:_release_native()
            if AL._root_panel and al_panel_alive(AL._root_panel) then
                al_safe_call(AL._root_panel, "set_visible", true)
            end
            if AL:_verify_pnr_render() then
                if not AL:_try_acquire_native() then
                    AL:_release_native()
                    if AL._root_panel and al_panel_alive(AL._root_panel) then
                        al_safe_call(AL._root_panel, "set_visible", false)
                    end
                    AL._render_verified = false
                end
            else
                AL:_release_native()
                if AL._root_panel and al_panel_alive(AL._root_panel) then
                    al_safe_call(AL._root_panel, "set_visible", false)
                end
                AL._render_verified = false
            end
        else
            AL:_ensure_primitives()
            AL:_sync_primitives()
            AL:_sync_native_visibility()
        end
    end

    local function safe_global_prehook(global_name, id, fn)
        if kyohud.hud._installed_hooks[id] then return end
        if type(_G[global_name]) ~= "function" then return end
        if type(Hooks) ~= "table" or type(Hooks.PreHook) ~= "function" then return end
        Hooks:PreHook(_G, global_name, id, fn)
        kyohud.hud._installed_hooks[id] = true
    end

    local function safe_global_posthook(global_name, id, fn)
        if kyohud.hud._installed_hooks[id] then return end
        if type(_G[global_name]) ~= "function" then return end
        if type(Hooks) ~= "table" or type(Hooks.PostHook) ~= "function" then return end
        Hooks:PostHook(_G, global_name, id, fn)
        kyohud.hud._installed_hooks[id] = true
    end

    safe_global_prehook(
        "HUDBGBox_animate_open_left",
        "KyohUD_Alerts_PreOpenLeft",
        cb_pre_open_left
    )
    safe_global_posthook(
        "HUDBGBox_animate_open_left",
        "KyohUD_Alerts_PostOpenLeft",
        cb_post_open_left
    )

    local function cb_pre_show_casing(self, mode)
        al_release_all_owned()
    end

    local function cb_post_show_casing(self, mode)
        AL:_bind_event_context(self)
        if mode == nil then
            AL._casing_mode = "normal"
        else
            AL._casing_mode = mode
        end
        AL._casing_active = true
        AL._conflict_corner = nil
        local ok_state, state = pcall(function() return managers.groupai and managers.groupai:state() end)
        if ok_state and state then
            local ok_w, w = pcall(function() return state:whisper_mode() end)
            if ok_w and type(w) == "boolean" then
                AL._whisper_mode = w
            end
        end
        AL._data_dirty = true
    end

    local ensure_hide_icon_observer

    local function cb_pre_hide_casing(self)
        local ensured = ensure_hide_icon_observer and ensure_hide_icon_observer()
        if ensured and AL._casing_native_acquired and AL._casing_render_verified then
            AL:_begin_casing_close()
        end
        if not AL._casing_closing then
            al_release_all_owned()
        end
    end

    local function cb_post_hide_casing(self)
        AL:_bind_event_context(self)
        if not AL._casing_closing then
            AL._casing_mode = nil
            AL._casing_active = false
        else
            local close_left_installed = kyohud.hud._installed_hooks["KyohUD_Alerts_PostCloseLeft"] == true
            local hide_icon_installed = kyohud.hud._installed_hooks["KyohUD_Alerts_PostHideIconAssaultbox"] == true
            if not close_left_installed and not hide_icon_installed then
                if AL:_validate_casing_close_identity() then
                    local bg = AL._casing_close_bg_box
                    local icon = AL._casing_close_icon
                    local bg_ok = false
                    local icon_ok = false
                    if bg and al_panel_alive(bg) then
                        local ok_v, v = pcall(function() return bg:visible() end)
                        if ok_v and v == false then bg_ok = true end
                    end
                    if icon and al_panel_alive(icon) then
                        local ok_a, a = pcall(function() return icon:alpha() end)
                        if ok_a and al_is_finite(a) and a <= 0.001 then icon_ok = true end
                    end
                    if bg_ok then AL._casing_close_bg_done = true end
                    if icon_ok then AL._casing_close_icon_done = true end
                    if AL:_check_casing_close_complete() then
                        AL:_complete_casing_close()
                    end
                end
            else
                if AL:_validate_casing_close_identity() and AL:_check_casing_close_complete() then
                    AL:_complete_casing_close()
                end
            end
        end
        AL._data_dirty = true
    end

    safe_prehook(
        HUDManager,
        "show_casing",
        "KyohUD_Alerts_PreShowCasing",
        cb_pre_show_casing
    )
    safe_posthook(
        HUDManager,
        "show_casing",
        "KyohUD_Alerts_PostShowCasing",
        cb_post_show_casing
    )
    safe_prehook(
        HUDManager,
        "hide_casing",
        "KyohUD_Alerts_PreHideCasing",
        cb_pre_hide_casing
    )
    safe_posthook(
        HUDManager,
        "hide_casing",
        "KyohUD_Alerts_PostHideCasing",
        cb_post_hide_casing
    )

    local function cb_post_close_left(panel, done_cb)
        if not AL._casing_closing then return end
        if AL._casing_close_bg_box and panel == AL._casing_close_bg_box then
            AL._casing_close_bg_done = true
            if AL:_validate_casing_close_identity() and AL:_check_casing_close_complete() then
                AL:_complete_casing_close()
            end
        end
    end

    local function cb_post_hide_icon_assaultbox(self_corner, icon_assaultbox)
        if not AL._casing_closing then return end
        if AL._casing_close_corner and self_corner == AL._casing_close_corner
            and AL._casing_close_icon and icon_assaultbox == AL._casing_close_icon then
            local ok_a, a = pcall(function() return icon_assaultbox:alpha() end)
            if ok_a and al_is_finite(a) and a <= 0.001 then
                AL._casing_close_icon_done = true
                if AL:_validate_casing_close_identity() and AL:_check_casing_close_complete() then
                    AL:_complete_casing_close()
                end
            end
        end
    end

    ensure_hide_icon_observer = function()
        if type(HUDAssaultCorner) ~= "table" then return false end
        local current = HUDAssaultCorner._hide_icon_assaultbox
        if type(current) ~= "function" then return false end
        if current == AL._casing_hide_icon_observer then return true end
        local wrapped = current
        local function wrapper(self, icon, ...)
            local function after(...)
                cb_post_hide_icon_assaultbox(self, icon)
                return ...
            end
            return after(wrapped(self, icon, ...))
        end
        HUDAssaultCorner._hide_icon_assaultbox = wrapper -- direct late reassignment bypasses SuperBLT cached hook tables; rebind only on hide event
        AL._casing_hide_icon_observer = wrapper
        return true
    end

    safe_global_posthook(
        "HUDBGBox_animate_close_left",
        "KyohUD_Alerts_PostCloseLeft",
        cb_post_close_left
    )

    if type(HUDAssaultCorner) == "table" and type(HUDAssaultCorner._hide_icon_assaultbox) == "function" then
        safe_posthook(
            HUDAssaultCorner,
            "_hide_icon_assaultbox",
            "KyohUD_Alerts_PostHideIconAssaultbox",
            cb_post_hide_icon_assaultbox
        )
        if AL._casing_hide_icon_observer == nil then
            AL._casing_hide_icon_observer = HUDAssaultCorner._hide_icon_assaultbox
        end
    end
end
