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
if S.phase == nil then S.phase = nil end
if S.presenting == nil then S.presenting = false end
if S.client_preparation == nil then S.client_preparation = false end
if S.is_host == nil then S.is_host = false end

A._assault_state_diag_bai_getter_type = A._assault_state_diag_bai_getter_type

A._native_mode = A._native_mode

local REQUIRED_CONTEXT = "lib/managers/hudmanagerpd2"

local function is_finite_nonneg(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    if v < 0 then return false end
    return true
end

local VALID_PHASES = {
    anticipation = true,
    build = true,
    sustain = true,
    fade = true,
}

local function _collect_phase(state, is_host)
    if not is_host then return nil end
    local ok_td, td = pcall(function() return state._task_data end)
    if not ok_td or type(td) ~= "table" then return nil end
    local ok_a, assault = pcall(function() return td.assault end)
    if not ok_a or type(assault) ~= "table" then return nil end
    local ok_active, active = pcall(function() return assault.active end)
    if not ok_active or active ~= true then return nil end
    local ok_p, phase = pcall(function() return assault.phase end)
    if not ok_p or type(phase) ~= "string" then return nil end
    if not VALID_PHASES[phase] then return nil end
    return phase
end

function A:_purge_bai_bridge()
    self._bai_instance = nil
    self._bai_registered = false
    self._bai_bonus_phase = nil
    self._bai_qualified = false
    self._bai_advanced_active = false
    self._bai_show_assault_states = nil
    self._bai_source = nil
    self._bai_manager = nil
    self._bai_corner = nil
    self._bai_heist_id = nil
end

function A:_bai_track_provenance()
    self._bai_source = self._source
    self._bai_manager = self._manager
    self._bai_heist_id = self._heist_manager_id
    if self._manager then
        local ok_c, c = pcall(function() return self._manager._hud_assault_corner end)
        if ok_c then
            self._bai_corner = c
        else
            self._bai_corner = nil
        end
    else
        self._bai_corner = nil
    end
end

function A:_bai_provenance_stale()
    if self._bai_source ~= self._source then return true end
    if self._bai_manager ~= self._manager then return true end
    if self._bai_heist_id ~= self._heist_manager_id then return true end
    if self._manager and self._bai_corner then
        local ok_c, c = pcall(function() return self._manager._hud_assault_corner end)
        if ok_c and c ~= self._bai_corner then return true end
    end
    return false
end

local function _bai_cb_live_valid(self_ref, bai)
    if self_ref._bai_instance ~= bai then return false end
    local lh = false
    local ok_bh, bh = pcall(function() return bai.BAIHost end)
    if ok_bh and bh == true then lh = true end
    if not lh and self_ref._manager then
        local ok_c, c = pcall(function() return self_ref._manager._hud_assault_corner end)
        if ok_c and type(c) == "table" then
            local ok_ch, ch = pcall(function() return c.BAIHost end)
            if ok_ch and ch == true then lh = true end
        end
    end
    local ls = false
    if lh and type(bai.GetOption) == "function" then
        local ok_so, so = pcall(function() return bai:GetOption("show_assault_states") end)
        if ok_so and so == true then ls = true end
    end
    if not (lh and ls) then return false end
    local ok_gs, gs = pcall(function() return managers.groupai:state() end)
    if not ok_gs or not gs then return false end
    if gs ~= self_ref._bai_source then return false end
    if self_ref._manager ~= self_ref._bai_manager then return false end
    if self_ref._heist_manager_id ~= self_ref._bai_heist_id then return false end
    if self_ref._bai_corner then
        local ok_lc, lc = pcall(function() return self_ref._manager._hud_assault_corner end)
        if not ok_lc or lc ~= self_ref._bai_corner then return false end
    end
    local ok_am, am = pcall(function() return gs:get_assault_mode() end)
    if not ok_am or am ~= true then return false end
    if self_ref._state.active ~= true then return false end
    return true
end

function A:_register_bai_callbacks(bai)
    local ok_el, el = pcall(function() return bai.EventList end)
    if not ok_el or type(el) ~= "table" then return end
    local asc_name = el.AssaultStateChange
    local asco_name = el.AssaultStateChangeOverride
    if type(bai.AddEvent) ~= "function" then return end
    local self_ref = self
    if type(asc_name) == "string" then
        local cb = function(state)
            if not _bai_cb_live_valid(self_ref, bai) then return end
            if state ~= "build" and state ~= "sustain" and state ~= "fade" and state ~= "anticipation" then return end
            if self_ref._state.is_host == true and self_ref._state.phase then return end
            self_ref._bai_bonus_phase = state
            self_ref._data_dirty = true
        end
        pcall(function() bai:AddEvent(asc_name, cb, 0, 0, "kyohud_bai_state") end)
    end
    if type(asco_name) == "string" then
        local cb_ov = function(state, override)
            if not _bai_cb_live_valid(self_ref, bai) then return end
            if override ~= true then return end
            if state ~= "build" and state ~= "sustain" and state ~= "fade" and state ~= "anticipation" then return end
            if self_ref._state.is_host == true and self_ref._state.phase then return end
            self_ref._bai_bonus_phase = state
            self_ref._data_dirty = true
        end
        pcall(function() bai:AddEvent(asco_name, cb_ov, 0, 0, "kyohud_bai_override") end)
    end
end

function A:_refresh_bai_bridge()
    local ok_bai, bai = pcall(function() return BAI end)
    if not ok_bai or type(bai) ~= "table" then
        self._assault_state_diag_bai_getter_type = "nil"
        self:_purge_bai_bridge()
        return
    end
    local getter_type = nil
    local advanced = true
    if type(bai.ShowAdvancedAssaultInfo) == "function" then
        getter_type = "function"
        local ok_adv, adv_val = pcall(function() return bai:ShowAdvancedAssaultInfo() end)
        if ok_adv and type(adv_val) == "boolean" then
            advanced = adv_val
        end
    else
        getter_type = "nil"
    end
    self._assault_state_diag_bai_getter_type = getter_type
    if self._bai_instance ~= nil and self._bai_instance ~= bai then
        self:_purge_bai_bridge()
    end
    self._bai_instance = bai
    self._bai_advanced_active = advanced
    local bai_host = false
    local ok_host, host_val = pcall(function() return bai.BAIHost end)
    if ok_host and host_val == true then
        bai_host = true
    end
    if not bai_host and self._manager then
        local ok_corner, corner = pcall(function() return self._manager._hud_assault_corner end)
        if ok_corner and type(corner) == "table" then
            local ok_ch, ch_val = pcall(function() return corner.BAIHost end)
            if ok_ch and ch_val == true then
                bai_host = true
            end
        end
    end
    local show_states = false
    if bai_host then
        if type(bai.GetOption) == "function" then
            local ok_opt, opt_val = pcall(function() return bai:GetOption("show_assault_states") end)
            if ok_opt and opt_val == true then
                show_states = true
            end
        end
    end
    self._bai_show_assault_states = show_states
    local qualified = bai_host and show_states
    if not qualified then
        if self._bai_qualified then
            self._bai_bonus_phase = nil
            self._data_dirty = true
        end
        self._bai_qualified = false
        return
    end
    self._bai_qualified = true
    if not self._bai_registered then
        self:_register_bai_callbacks(bai)
        self._bai_registered = true
        self:_bai_track_provenance()
    else
        if self:_bai_provenance_stale() then
            self._bai_bonus_phase = nil
            self._data_dirty = true
            self:_bai_track_provenance()
        end
    end
end

kyohud.hud._installed_hooks = kyohud.hud._installed_hooks or {}

function A:snapshot(manager)
    local previous_source = self._source
    local first_mount_with_events = (previous_source == nil) and (self._event_manager == self._manager)

    local ok_state, state = pcall(function()
        return managers.groupai:state()
    end)

    if not ok_state or not state then
        self._lull_source, self._lull_manager = nil, nil
        if not first_mount_with_events then
            self._event_manager = nil
            self._event_has_active = false
            self._event_has_endless = false
            self._event_has_number = false
            self._event_has_hostages = false
            self._event_has_client_preparation = false
            self._state.active = false
            self._state.endless = false
            self._state.number = nil
            self._state.hostages = nil
            self._state.converted = nil
            self._state.phase = nil
            self._state.is_host = false
            self._state.client_preparation = false
            self._state.presenting = false
        else
            if not self._event_has_active then self._state.active = false end
            if not self._event_has_endless then self._state.endless = false end
            if not self._event_has_number then self._state.number = nil end
            if not self._event_has_hostages then self._state.hostages = nil end
            self._state.converted = nil
            if not self._event_has_client_preparation then self._state.client_preparation = false end
            self._state.phase = nil
            self._state.is_host = false
        end
        self._source = nil
        self:_apply_event_provenance()
        self:_update_presenting()
        return
    end

    if previous_source ~= nil and previous_source ~= state then
        self._lull_source, self._lull_manager = nil, nil
        self._event_manager = nil
        self._event_has_active = false
        self._event_has_endless = false
        self._event_has_number = false
        self._event_has_hostages = false
        self._event_client_preparation = false
        self._event_has_client_preparation = false
        self._state.client_preparation = false
        self._after_assault_active = false
        self._after_assault_pending = false
        self._after_assault_start = nil
    end

    self._source = state

    local ok1, v1 = pcall(function() return state:get_assault_mode() end)
    self._state.active = (ok1 and v1 == true)

    local ok2, v2 = pcall(function() return state:get_hunt_mode() end)
    self._state.endless = (ok2 and v2 == true)

    local is_server = false
    local net_decided = false
    local ok_net, net_srv = pcall(function() return Network:is_server() end)
    if ok_net then
        is_server = (net_srv == true)
        net_decided = true
    end
    if not net_decided then
        local ok_s, s = pcall(function() return state._is_server end)
        if ok_s and s == true then is_server = true end
    end
    self._state.is_host = is_server

    self._state.phase = _collect_phase(state, is_server)

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
    self:_update_presenting()
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
    if self._event_has_client_preparation then
        self._state.client_preparation = self._event_client_preparation == true
    end
end

function A:_update_presenting()
    if self._state.active == true or self._state.endless == true
        or self._state.phase == "anticipation" or self._state.client_preparation == true then
        self._lull_source, self._lull_manager = nil, nil
    end
    local active = self._state.active == true
    local endless = self._state.endless == true
    local is_host = self._state.is_host == true
    local phase = self._state.phase
    local client_prep = self._state.client_preparation == true
    local after = self._after_assault_active == true
    if endless or active then
        self._state.presenting = true
    elseif after or self:_is_lull() then
        self._state.presenting = true
    elseif is_host and type(phase) == "string" and phase == "anticipation" then
        self._state.presenting = true
    elseif client_prep then
        self._state.presenting = true
    else
        self._state.presenting = false
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
A._native_had_text_panel = A._native_had_text_panel
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
A._event_client_preparation = A._event_client_preparation
A._event_has_client_preparation = A._event_has_client_preparation or false
A._data_dirty = A._data_dirty or false
A._heist_manager_id = A._heist_manager_id
A._bai_instance = A._bai_instance
A._bai_registered = A._bai_registered or false
A._bai_bonus_phase = A._bai_bonus_phase
A._bai_qualified = A._bai_qualified or false
A._bai_advanced_active = A._bai_advanced_active or false
A._bai_show_assault_states = A._bai_show_assault_states
A._bai_source = A._bai_source
A._bai_manager = A._bai_manager
A._bai_corner = A._bai_corner
A._bai_heist_id = A._bai_heist_id

A._transition_active = A._transition_active or false
A._transition_elapsed = A._transition_elapsed or 0
A._transition_duration = 0.15
A._outgoing_ticker_a = A._outgoing_ticker_a
A._outgoing_ticker_b = A._outgoing_ticker_b
A._transition_old_text = A._transition_old_text
A._transition_old_x_a = A._transition_old_x_a
A._transition_old_x_b = A._transition_old_x_b
A._transition_old_w = A._transition_old_w
A._transition_old_color_r = A._transition_old_color_r
A._transition_old_color_g = A._transition_old_color_g
A._transition_old_color_b = A._transition_old_color_b
A._cached_label_key = A._cached_label_key

A._after_assault_active = A._after_assault_active or false
A._after_assault_start = A._after_assault_start
A._after_assault_pending = A._after_assault_pending or false

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
local TRANSITION_DURATION = 0.15
local AFTER_ASSAULT_WINDOW = 1.5

local PHASE_LABEL_KEYS = {
    difficulty = true,
    ky_hud_assault_lull = true,
    ky_hud_assault_preparation = true,
    ky_hud_assault_build = true,
    ky_hud_assault_sustain = true,
    ky_hud_assault_fade = true,
    ky_hud_assault_status = true,
    ky_hud_assault_endless = true,
    ky_hud_assault_after = true,

}

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
local COLOR_STAGE_PALETTES = nil

local function a_init_colors()
    if COLOR_TICKER_BG_NORMAL then return end
    COLOR_TICKER_BG_NORMAL  = a_color(0.949, 0.890, 0.106)
    COLOR_TICKER_BG_ENDLESS = a_color(1.0, 0.165, 0.333)
    COLOR_TICKER_INK_NORMAL = a_color(0.067, 0.067, 0.067)
    COLOR_TICKER_INK_ENDLESS = a_color(1, 1, 1, 1)
    COLOR_CELL_BG           = a_color(0.043, 0.051, 0.067, 0.75)
    COLOR_COUNTER_INK       = a_color(0.788, 0.820, 0.847)
    COLOR_STAGE_PALETTES = {}
    local function palette(key,r,g,b,white)
        COLOR_STAGE_PALETTES[key] = {
            bg=a_color(r,g,b), r=r,g=g,b=b,
            ink=white and COLOR_TICKER_INK_ENDLESS or COLOR_TICKER_INK_NORMAL,
            ir=white and 1 or .067, ig=white and 1 or .067, ib=white and 1 or .067,
        }
    end
    palette("normal",.949,.890,.106,false)
    palette("preparation",1,.68,.12,false)
    palette("sustain",1,.48,.12,false)
    palette("fade",.93,.87,.56,false)
    palette("ended",.30,.40,.49,true)
    palette("endless",1,.165,.333,true)
end

function A:_banner_palette()
    a_init_colors()
    local key = self:_resolve_label_key()
    if self._state.endless == true then return COLOR_STAGE_PALETTES.endless end
    if key == "ky_hud_assault_after" or key == "ky_hud_assault_lull" then
        return COLOR_STAGE_PALETTES.ended
    elseif key == "ky_hud_assault_preparation" then return COLOR_STAGE_PALETTES.preparation
    elseif key == "ky_hud_assault_sustain" then return COLOR_STAGE_PALETTES.sustain
    elseif key == "ky_hud_assault_fade" then return COLOR_STAGE_PALETTES.fade end
    return COLOR_STAGE_PALETTES.normal
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
    -- Keep Alerts' reservation unchanged. Assault owns two distinct regions:
    -- scrolling main title on the left, stationary state next to the logo.
    local es = geom.es
    geom.title = { x = 8 * es, y = 0, w = 174 * es, h = geom.ticker.h }
    geom.ticker = { x = 190 * es, y = 0, w = 142 * es, h = geom.ticker.h }
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

local STATUS_FALLBACKS = {
    ky_hud_assault_lull = "LULL",
    ky_hud_assault_title = "POLICE ASSAULT",
    ky_hud_assault_active_title = "POLICE ASSAULT IN PROGRESS",
    ky_hud_assault_idle_title = "ASSAULT ENDED",
    ky_hud_assault_endless = "ENDLESS",
    ky_hud_assault_preparation = "PREPARATION",
    ky_hud_assault_build = "BUILD",
    ky_hud_assault_sustain = "SUSTAIN",
    ky_hud_assault_fade = "FADE",
    ky_hud_assault_after = "AFTER ASSAULT",
    ky_hud_assault_status = "ASSAULT",
}

function A:_resolve_label_key()
    if self._state.endless == true then
        return "ky_hud_assault_endless"
    elseif self:_is_lull() and not self._after_assault_active then
        return "ky_hud_assault_lull"
    elseif self._after_assault_active == true then
        return "ky_hud_assault_after"
    elseif self._state.is_host == true then
        local phase = self._state.phase
        if phase == "anticipation" then return "ky_hud_assault_preparation"
        elseif phase == "build" then return "ky_hud_assault_build"
        elseif phase == "sustain" then return "ky_hud_assault_sustain"
        elseif phase == "fade" then return "ky_hud_assault_fade"
        else return "ky_hud_assault_status" end
    elseif self._bai_qualified == true and type(self._bai_bonus_phase) == "string" then
        local bp = self._bai_bonus_phase
        if bp == "anticipation" then return "ky_hud_assault_preparation"
        elseif bp == "build" then return "ky_hud_assault_build"
        elseif bp == "sustain" then return "ky_hud_assault_sustain"
        elseif bp == "fade" then return "ky_hud_assault_fade"
        else return "ky_hud_assault_status" end
    elseif self._state.client_preparation == true then
        return "ky_hud_assault_preparation"
    else
        return "ky_hud_assault_status"
    end
end

function A:_resolve_status_label()
    local key = self:_resolve_label_key()
    local ok_loc, loc = pcall(function() return managers.localization end)
    if ok_loc and loc then
        local ok_t, t = pcall(function() return loc:text(key) end)
        if ok_t and type(t) == "string" and t ~= "" and t ~= key
            and not string.find(t, "LOC:", 1, true) then return t end
    end
    return STATUS_FALLBACKS[key] or "ASSAULT"
end

function A:_resolve_ticker_text()
    if self:_resolve_display_key() == "difficulty" then
        return self:_resolve_banner_difficulty() or "--"
    end
    return self:_banner_text(self:_resolve_display_key())
end

function A:_resolve_display_key()
    local key = self:_resolve_label_key()
    if key == "ky_hud_assault_after" or key == "ky_hud_assault_lull" then
        return "difficulty"
    end
    local active = self._state.active == true or self._state.endless == true
    if active and key ~= "ky_hud_assault_preparation" and key ~= "ky_hud_assault_after"
        and key ~= "ky_hud_assault_lull"
        and (not self._display_reminder or key == "ky_hud_assault_build")
        and self:_resolve_banner_difficulty() then return "difficulty" end
    if key == "ky_hud_assault_build" then return "ky_hud_assault_status" end
    return key
end

function A:_update_banner_alternation(dt)
    local old = self._display_reminder == true
    local key = self:_resolve_label_key()
    local active = (self._state.active == true or self._state.endless == true)
        and key ~= "ky_hud_assault_preparation" and key ~= "ky_hud_assault_after"
        and key ~= "ky_hud_assault_lull"
    local source_changed = self._banner_clock_source ~= self._source
        or self._banner_clock_manager ~= self._manager
    if not active or source_changed then self._banner_clock = 0 end
    self._banner_clock_source, self._banner_clock_manager = self._source, self._manager
    if active and a_is_finite(dt) and dt > 0 then
        self._banner_clock = ((self._banner_clock or 0) + dt) % 10
    end
    -- A new qualified phase gets four full presentation seconds. Source
    -- replacement starts a fresh cycle, not an inferred phase event.
    if active and not source_changed and self._banner_phase ~= nil
        and self._banner_phase ~= key
        and (key == "ky_hud_assault_sustain" or key == "ky_hud_assault_fade") then
        self._banner_clock = 6
    end
    self._banner_phase = key
    self._display_reminder = active and (self._banner_clock or 0) >= 6
    if old ~= self._display_reminder then self._data_dirty = true end
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
    local color = self:_banner_palette().bg
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
    local text_color = self:_banner_palette().ink
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
        self._ticker_gap = math.max(REF_TICKER_GAP * (layout.es or 1), layout.ticker.w + 8 * (layout.es or 1))
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
    self:_sync_title()
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
    local palette = self:_banner_palette()
    local color = palette.bg
    local r, g, b, alpha = a_read_color(self._bg_rect)
    local exp_r, exp_g, exp_b = palette.r, palette.g, palette.b
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
    self._ticker_x_a = 0
    local new_key = self:_resolve_display_key()
    local old_key = self._cached_label_key
    local label_key_changed = PHASE_LABEL_KEYS[new_key] and PHASE_LABEL_KEYS[old_key] and new_key ~= old_key
    local snap_text, snap_x_a, snap_x_b, snap_w, snap_r, snap_g, snap_b
    if label_key_changed then
        if self._transition_active then
            if self._ticker_a and a_panel_alive(self._ticker_a) then
                a_safe_call(self._ticker_a, "set_alpha", 1.0)
            end
            if self._ticker_b and a_panel_alive(self._ticker_b) then
                a_safe_call(self._ticker_b, "set_alpha", 1.0)
            end
            if self._outgoing_ticker_a and a_panel_alive(self._outgoing_ticker_a) then
                a_safe_call(self._outgoing_ticker_a, "set_visible", false)
            end
            if self._outgoing_ticker_b and a_panel_alive(self._outgoing_ticker_b) then
                a_safe_call(self._outgoing_ticker_b, "set_visible", false)
            end
            self._transition_active = false
            self._transition_elapsed = 0
            self._transition_old_text = nil
            self._transition_old_color_r = nil
            self._transition_old_color_g = nil
            self._transition_old_color_b = nil
        end
        snap_text = self._cached_ticker_text
        snap_x_a = self._ticker_x_a
        snap_x_b = self._ticker_x_b
        snap_w = self._ticker_measured_w
        local r, g, b = 1, 1, 1
        a_init_colors()
        local endless = self._state.endless == true
        if endless then
            r, g, b = 1, 1, 1
        else
            r, g, b = 0.067, 0.067, 0.067
        end
        local pr, pg, pb = a_read_color(self._ticker_a)
        if pr then r, g, b = pr, pg, pb end
        snap_r, snap_g, snap_b = r, g, b
    end
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
    local desired_gap = math.max(REF_TICKER_GAP * es, self._layout_cache.ticker.w + 8 * es)
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
            local gap = self._ticker_gap or desired_gap
            -- A shorter label must be in its new cycle before certification;
            -- the outgoing pair retains the old position captured above.
            ax = -((-ax) % (mw + gap))
            self._ticker_x_a = ax
            a_safe_call(self._ticker_a, "set_shape", ax, 0, mw, ticker_h)
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
    a_safe_call(self._ticker_a, "set_x", 0)
    self._ticker_x_b = (self._ticker_measured_w or 0) + (self._ticker_gap or desired_gap)
    a_safe_call(self._ticker_b, "set_x", self._ticker_x_b)
    if new_key == "ky_hud_assault_preparation" then
        -- Preparation is a persistent announcement, not a periodic reminder.
        -- Do not leave its sole on-screen label transparent at entry.
        if self._transition_active then self:_settle_transition() end
        a_safe_call(self._ticker_a, "set_alpha", 1.0)
        a_safe_call(self._ticker_b, "set_alpha", 1.0)
    elseif label_key_changed and snap_text and snap_text ~= new_text then
        self:_start_label_transition(snap_text, snap_x_a, snap_x_b, snap_w, snap_r, snap_g, snap_b)
    end
    self._cached_label_key = new_key
end

function A:_hide_outgoing()
    if self._outgoing_ticker_a and a_panel_alive(self._outgoing_ticker_a) then
        a_safe_call(self._outgoing_ticker_a, "set_visible", false)
    end
    if self._outgoing_ticker_b and a_panel_alive(self._outgoing_ticker_b) then
        a_safe_call(self._outgoing_ticker_b, "set_visible", false)
    end
    self._transition_active = false
    self._transition_elapsed = 0
end

function A:_cancel_transition()
    if self._outgoing_ticker_a and a_panel_alive(self._outgoing_ticker_a) then
        a_safe_call(self._outgoing_ticker_a, "set_visible", false)
        if self._ticker_panel and a_panel_alive(self._ticker_panel) then
            a_safe_call(self._ticker_panel, "remove", self._outgoing_ticker_a)
        end
    end
    if self._outgoing_ticker_b and a_panel_alive(self._outgoing_ticker_b) then
        a_safe_call(self._outgoing_ticker_b, "set_visible", false)
        if self._ticker_panel and a_panel_alive(self._ticker_panel) then
            a_safe_call(self._ticker_panel, "remove", self._outgoing_ticker_b)
        end
    end
    self._outgoing_ticker_a = nil
    self._outgoing_ticker_b = nil
    self._transition_active = false
    self._transition_elapsed = 0
    self._transition_old_text = nil
    self._transition_old_x_a = nil
    self._transition_old_x_b = nil
    self._transition_old_w = nil
    self._transition_old_color_r = nil
    self._transition_old_color_g = nil
    self._transition_old_color_b = nil
end

function A:_settle_transition()
    if self._ticker_a and a_panel_alive(self._ticker_a) then
        a_safe_call(self._ticker_a, "set_alpha", 1.0)
    end
    if self._ticker_b and a_panel_alive(self._ticker_b) then
        a_safe_call(self._ticker_b, "set_alpha", 1.0)
    end
    if self._outgoing_ticker_a and a_panel_alive(self._outgoing_ticker_a) then
        a_safe_call(self._outgoing_ticker_a, "set_visible", false)
    end
    if self._outgoing_ticker_b and a_panel_alive(self._outgoing_ticker_b) then
        a_safe_call(self._outgoing_ticker_b, "set_visible", false)
    end
    self._transition_active = false
    self._transition_elapsed = 0
    self._transition_old_text = nil
    self._transition_old_x_a = nil
    self._transition_old_x_b = nil
    self._transition_old_w = nil
    self._transition_old_color_r = nil
    self._transition_old_color_g = nil
    self._transition_old_color_b = nil
    self:_sync_title()
end

function A:_start_label_transition(old_text, old_x_a, old_x_b, old_w, old_r, old_g, old_b)
    if not self._ticker_panel or not a_panel_alive(self._ticker_panel) then return end
    if not self._layout_cache then return end
    if not old_text or old_text == "" then return end
    a_init_colors()
    local font = self:_get_font()
    local layout = self._layout_cache
    local ticker_h = layout.ticker.h
    local old_color = Color(1, old_r or 1, old_g or 1, old_b or 1)
    local ow = old_w and old_w > 0 and old_w or layout.ticker.w
    local old_x_b_val = old_x_b or ((old_x_a or 0) + ow + (self._ticker_gap or REF_TICKER_GAP))
    if self._outgoing_ticker_a and a_panel_alive(self._outgoing_ticker_a) then
        a_safe_call(self._outgoing_ticker_a, "set_text", old_text)
        a_safe_call(self._outgoing_ticker_a, "set_font_size", layout.ticker_font)
        a_safe_call(self._outgoing_ticker_a, "set_color", old_color)
        a_safe_call(self._outgoing_ticker_a, "set_alpha", 1.0)
        a_safe_call(self._outgoing_ticker_a, "set_shape", old_x_a or 0, 0, ow, ticker_h)
        a_safe_call(self._outgoing_ticker_a, "set_layer", 1)
        a_safe_call(self._outgoing_ticker_a, "set_visible", true)
    else
        local sa, pa = a_safe_call(self._ticker_panel, "text", {
            name = "kyohud_assault_outgoing_a",
            text = old_text,
            font = font,
            font_size = layout.ticker_font,
            color = old_color,
            x = old_x_a or 0, y = 0,
            w = ow, h = ticker_h,
            align = "left", vertical = "center",
            wrap = false, word_wrap = false,
            layer = 1,
        })
        if sa == a_call_ok and pa then
            self._outgoing_ticker_a = pa
        end
    end
    if self._outgoing_ticker_b and a_panel_alive(self._outgoing_ticker_b) then
        a_safe_call(self._outgoing_ticker_b, "set_text", old_text)
        a_safe_call(self._outgoing_ticker_b, "set_font_size", layout.ticker_font)
        a_safe_call(self._outgoing_ticker_b, "set_color", old_color)
        a_safe_call(self._outgoing_ticker_b, "set_alpha", 1.0)
        a_safe_call(self._outgoing_ticker_b, "set_shape", old_x_b_val, 0, ow, ticker_h)
        a_safe_call(self._outgoing_ticker_b, "set_layer", 1)
        a_safe_call(self._outgoing_ticker_b, "set_visible", true)
    else
        local sb, pb = a_safe_call(self._ticker_panel, "text", {
            name = "kyohud_assault_outgoing_b",
            text = old_text,
            font = font,
            font_size = layout.ticker_font,
            color = old_color,
            x = old_x_b_val, y = 0,
            w = ow, h = ticker_h,
            align = "left", vertical = "center",
            wrap = false, word_wrap = false,
            layer = 1,
        })
        if sb == a_call_ok and pb then
            self._outgoing_ticker_b = pb
        end
    end
    self._transition_old_text = old_text
    self._transition_old_x_a = old_x_a or 0
    self._transition_old_x_b = old_x_b_val
    self._transition_old_w = old_w or 0
    self._transition_old_color_r = old_r or 1
    self._transition_old_color_g = old_g or 1
    self._transition_old_color_b = old_b or 1
    self._transition_active = true
    self._transition_elapsed = 0
    if self._ticker_a and a_panel_alive(self._ticker_a) then
        a_safe_call(self._ticker_a, "set_alpha", 0)
    end
    if self._ticker_b and a_panel_alive(self._ticker_b) then
        a_safe_call(self._ticker_b, "set_alpha", 0)
    end
end

function A:_update_transition(dt)
    if not self._transition_active then return end
    if not a_is_finite(dt) or dt <= 0 then return end
    self._transition_elapsed = (self._transition_elapsed or 0) + dt
    local dur = self._transition_duration or TRANSITION_DURATION
    local progress = self._transition_elapsed / dur
    if progress >= 1.0 then
        self:_settle_transition()
        return
    end
    if self._ticker_a and a_panel_alive(self._ticker_a) then
        a_safe_call(self._ticker_a, "set_alpha", progress)
    end
    if self._ticker_b and a_panel_alive(self._ticker_b) then
        a_safe_call(self._ticker_b, "set_alpha", progress)
    end
    if self._outgoing_ticker_a and a_panel_alive(self._outgoing_ticker_a) then
        a_safe_call(self._outgoing_ticker_a, "set_alpha", 1.0 - progress)
    end
    if self._outgoing_ticker_b and a_panel_alive(self._outgoing_ticker_b) then
        a_safe_call(self._outgoing_ticker_b, "set_alpha", 1.0 - progress)
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
    local palette = self:_banner_palette()
    local ticker_color = palette.ink
    local exp_tr, exp_tg, exp_tb = palette.ir, palette.ig, palette.ib
    local exp_ta = 1
    local in_transition = self._transition_active == true
    if in_transition then
        local pr, pg, pb = a_read_color(self._ticker_a)
        if pr and (math.abs(pr - exp_tr) > 0.01 or math.abs(pg - exp_tg) > 0.01
            or math.abs(pb - exp_tb) > 0.01) then
            local _, _, _, cur_a = a_read_color(self._ticker_a)
            a_safe_call(self._ticker_a, "set_color", Color(cur_a or 1, exp_tr, exp_tg, exp_tb))
        end
        pr, pg, pb = a_read_color(self._ticker_b)
        if pr and (math.abs(pr - exp_tr) > 0.01 or math.abs(pg - exp_tg) > 0.01
            or math.abs(pb - exp_tb) > 0.01) then
            local _, _, _, cur_a = a_read_color(self._ticker_b)
            a_safe_call(self._ticker_b, "set_color", Color(cur_a or 1, exp_tr, exp_tg, exp_tb))
        end
    else
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
    self:_sync_title()
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
    -- Historical ticker fields now own the fixed state/crossfade pair.
    -- Only the separate main-title pair scrolls.
    self:_update_title(dt)
end

function A:_refresh_counters()
    local ok_state, state = pcall(function() return managers.groupai:state() end)
    if not ok_state or not state then
        self:snapshot(self._manager)
        return
    end
    local source_changed = (state ~= self._source)
    if source_changed then
        if self._bai_bonus_phase ~= nil then
            self._bai_bonus_phase = nil
            self._data_dirty = true
        end
        self:snapshot(self._manager)
        return
    end
    local same_source_event = (self._event_manager == self._manager)
    local ok_active_r, active_r = pcall(function() return state:get_assault_mode() end)
    if ok_active_r then
        if not (same_source_event and self._event_has_active) then
            self._state.active = active_r == true
        end
    end
    local ok_hunt, hunt = pcall(function() return state:get_hunt_mode() end)
    if ok_hunt then
        if not (same_source_event and self._event_has_endless) then
            self._state.endless = hunt == true
        end
    end
    local is_server = false
    local net_decided = false
    local ok_net, net_srv = pcall(function() return Network:is_server() end)
    if ok_net then
        is_server = (net_srv == true)
        net_decided = true
    end
    if not net_decided then
        local ok_s, s = pcall(function() return state._is_server end)
        if ok_s and s == true then is_server = true end
    end
    self._state.is_host = is_server
    self._state.phase = _collect_phase(state, is_server)
    self:_update_presenting()
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
        -- Preserve the measured state/title split when the outer geometry is unchanged.
        self:_repair_layout_shapes(old)
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
    self._ticker_gap = math.max(REF_TICKER_GAP * (new_layout.es or 1), new_layout.ticker.w + 8 * (new_layout.es or 1))
    if self._ticker_a and a_panel_alive(self._ticker_a) then
        local ok_mr, mx, my, mw, mh = pcall(function() return self._ticker_a:text_rect() end)
        if ok_mr and a_is_finite(mw) and mw > 0 then
            self._ticker_measured_w = mw
            local ticker_h = new_layout.ticker.h
            local ax = self._ticker_x_a or 0
            local gap = self._ticker_gap or (REF_TICKER_GAP * (new_layout.es or 1))
            ax = -((-ax) % (mw + gap))
            self._ticker_x_a = ax
            a_safe_call(self._ticker_a, "set_shape", ax, 0, mw, ticker_h)
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
    local function _pred_fail()
        self._render_verified = false
    end
    if not self._layout_cache then
        _pred_fail("no_layout_cache")
        return false
    end
    local geom = self._layout_cache
    if not self:_verify_title() then
        _pred_fail("main_title_readback")
        return false
    end
    if not a_is_finite(geom.root_w) or not a_is_finite(geom.root_h) then
        _pred_fail("root_geom_invalid")
        return false
    end
    if not a_is_finite(geom.ticker_font) or not a_is_finite(geom.counter_font) then
        _pred_fail("font_invalid")
        return false
    end
    if geom.root_w <= 0 or geom.root_h <= 0 or geom.ticker_font <= 0 or geom.counter_font <= 0 then
        _pred_fail("dimension_zero_or_negative")
        return false
    end
    if not self._root_panel or not a_panel_alive(self._root_panel) then
        _pred_fail("root_panel_dead")
        return false
    end
    local ok_parent, owned_parent = pcall(function() return self._root_panel:parent() end)
    if not ok_parent or owned_parent~=self._parent_panel then
        _pred_fail("root_parent_mismatch")
        return false
    end
    if not self._bg_rect or not a_panel_alive(self._bg_rect) then
        _pred_fail("bg_rect_dead")
        return false
    end
    if not self._ticker_panel or not a_panel_alive(self._ticker_panel) then
        _pred_fail("ticker_panel_dead")
        return false
    end
    if not self._ticker_a or not a_panel_alive(self._ticker_a) then
        _pred_fail("ticker_a_dead")
        return false
    end
    if not self._ticker_b or not a_panel_alive(self._ticker_b) then
        _pred_fail("ticker_b_dead")
        return false
    end
    if not self._glyph_prim or not a_panel_alive(self._glyph_prim) then
        _pred_fail("glyph_dead")
        return false
    end
    if not self._hostages_prim or not a_panel_alive(self._hostages_prim) then
        _pred_fail("hostages_prim_dead")
        return false
    end
    if not self._converted_prim or not a_panel_alive(self._converted_prim) then
        _pred_fail("converted_prim_dead")
        return false
    end
    if not self._hostages_bg or not a_panel_alive(self._hostages_bg) then
        _pred_fail("hostages_bg_dead")
        return false
    end
    if not self._converted_bg or not a_panel_alive(self._converted_bg) then
        _pred_fail("converted_bg_dead")
        return false
    end
    if not self._hostages_icon or not a_panel_alive(self._hostages_icon) then
        _pred_fail("hostages_icon_dead")
        return false
    end
    if not self._converted_icon or not a_panel_alive(self._converted_icon) then
        _pred_fail("converted_icon_dead")
        return false
    end
    local tol = 0.5
    local ox_s, ox = a_safe_call(self._root_panel, "x")
    local oy_s, oy = a_safe_call(self._root_panel, "y")
    local ow_s, ow = a_safe_call(self._root_panel, "w")
    local oh_s, oh = a_safe_call(self._root_panel, "h")
    if ox_s ~= a_call_ok or oy_s ~= a_call_ok or ow_s ~= a_call_ok or oh_s ~= a_call_ok then
        _pred_fail("root_x_read_failed")
        return false
    end
    if not a_is_finite(ox) or not a_is_finite(oy) or not a_is_finite(ow) or not a_is_finite(oh) then
        _pred_fail("root_geom_non_finite")
        return false
    end
    if math.abs(ox - geom.root_x) > tol or math.abs(oy - geom.root_y) > tol
        or math.abs(ow - geom.root_w) > tol or math.abs(oh - geom.root_h) > tol then
        _pred_fail("root_geom_drift")
        return false
    end
    local ok_vis, vis = pcall(function() return self._root_panel:visible() end)
    if not ok_vis or vis ~= true then
        _pred_fail("root_visible_false")
        return false
    end
    local bg_geom = geom.bg or geom.ticker
    local bg_x_s, bg_x = a_safe_call(self._bg_rect, "x")
    local bg_y_s, bg_y = a_safe_call(self._bg_rect, "y")
    local bg_w_s, bg_w = a_safe_call(self._bg_rect, "w")
    local bg_h_s, bg_h = a_safe_call(self._bg_rect, "h")
    if bg_x_s ~= a_call_ok or bg_y_s ~= a_call_ok or bg_w_s ~= a_call_ok or bg_h_s ~= a_call_ok then
        _pred_fail("bg_rect_read_failed")
        return false
    end
    if not a_is_finite(bg_x) or not a_is_finite(bg_y) or not a_is_finite(bg_w) or not a_is_finite(bg_h) then
        _pred_fail("bg_rect_non_finite")
        return false
    end
    if math.abs(bg_x - bg_geom.x) > tol or math.abs(bg_y - bg_geom.y) > tol
        or math.abs(bg_w - bg_geom.w) > tol or math.abs(bg_h - bg_geom.h) > tol then
        _pred_fail("bg_rect_drift")
        return false
    end
    local ok_bv, bv = pcall(function() return self._bg_rect:visible() end)
    if not ok_bv or bv ~= true then
        _pred_fail("bg_rect_visible_false")
        return false
    end
    local tp_x_s, tp_x = a_safe_call(self._ticker_panel, "x")
    local tp_y_s, tp_y = a_safe_call(self._ticker_panel, "y")
    local tp_w_s, tp_w = a_safe_call(self._ticker_panel, "w")
    local tp_h_s, tp_h = a_safe_call(self._ticker_panel, "h")
    if tp_x_s ~= a_call_ok or tp_y_s ~= a_call_ok or tp_w_s ~= a_call_ok or tp_h_s ~= a_call_ok then
        _pred_fail("ticker_panel_read_failed")
        return false
    end
    if not a_is_finite(tp_x) or not a_is_finite(tp_y) or not a_is_finite(tp_w) or not a_is_finite(tp_h) then
        _pred_fail("ticker_panel_non_finite")
        return false
    end
    if math.abs(tp_x - geom.ticker.x) > tol or math.abs(tp_y - geom.ticker.y) > tol
        or math.abs(tp_w - geom.ticker.w) > tol or math.abs(tp_h - geom.ticker.h) > tol then
        _pred_fail("ticker_panel_drift")
        return false
    end
    local ok_tv, tv = pcall(function() return self._ticker_panel:visible() end)
    if not ok_tv or tv ~= true then
        _pred_fail("ticker_panel_visible_false")
        return false
    end
    local desired_ticker = self._cached_ticker_text
    if type(desired_ticker) ~= "string" or desired_ticker == "" then
        _pred_fail("no_ticker_text")
        return false
    end
    local function check_text(prim, desired, expected_fs, skip_x, skip_y, region_y, region_h, prim_name)
        local ok_v, v = pcall(function() return prim:visible() end)
        if not ok_v or v ~= true then
            _pred_fail(prim_name .. "_visible_false")
            return false
        end
        local ok_t, t = pcall(function() return prim:text() end)
        if not ok_t or type(t) ~= "string" then
            _pred_fail(prim_name .. "_text_read_failed")
            return false
        end
        if t ~= desired then
            _pred_fail(prim_name .. "_text_mismatch")
            return false
        end
        local ok_fs, fs = pcall(function() return prim:font_size() end)
        if not ok_fs or not a_is_finite(fs) or fs <= 0 then
            _pred_fail(prim_name .. "_font_size_invalid")
            return false
        end
        if math.abs(fs - expected_fs) > 0.5 then
            _pred_fail(prim_name .. "_font_size_drift")
            return false
        end
        local s_px, px = a_safe_call(prim, "x")
        local s_py, py = a_safe_call(prim, "y")
        local s_pw, pw = a_safe_call(prim, "w")
        local s_ph, ph = a_safe_call(prim, "h")
        if s_px ~= a_call_ok or s_py ~= a_call_ok or s_pw ~= a_call_ok or s_ph ~= a_call_ok then
            _pred_fail(prim_name .. "_geom_read_failed")
            return false
        end
        if not a_is_finite(px) or not a_is_finite(py) or not a_is_finite(pw) or not a_is_finite(ph) then
            _pred_fail(prim_name .. "_geom_non_finite")
            return false
        end
        if not skip_y and region_y then
            if math.abs(py - region_y) > tol then
                _pred_fail(prim_name .. "_y_drift")
                return false
            end
        end
        if region_h and math.abs(ph - region_h) > tol then
            _pred_fail(prim_name .. "_h_drift")
            return false
        end
        local ok_mr, mr_x, mr_y, mw, mh = pcall(function() return prim:text_rect() end)
        if not ok_mr then
            _pred_fail(prim_name .. "_text_rect_failed")
            return false
        end
        if not a_is_finite(mw) or not a_is_finite(mh) then
            _pred_fail(prim_name .. "_text_rect_non_finite")
            return false
        end
        if mw <= 0 or mh <= 0 then
            _pred_fail(prim_name .. "_text_rect_zero")
            return false
        end
        if mh > ph + tol then
            _pred_fail(prim_name .. "_text_rect_overflow")
            return false
        end
        return true
    end
    if not check_text(self._ticker_a, desired_ticker, geom.ticker_font, true, false, 0, geom.ticker.h, "ticker_a") then
        return false
    end
    local ok_tax, tax = a_safe_call(self._ticker_a, "x")
    if ok_tax ~= a_call_ok or not a_is_finite(tax) then
        _pred_fail("ticker_a_x_read_failed")
        return false
    end
    local s_taw, taw = a_safe_call(self._ticker_a, "w")
    if s_taw == a_call_ok and a_is_finite(taw) and (self._ticker_measured_w or 0) > 0 then
        if math.abs(taw - self._ticker_measured_w) > 1.5 then
            _pred_fail("ticker_a_width_drift")
            return false
        end
    end
    local cycle = (self._ticker_measured_w or 0) + (self._ticker_gap or (REF_TICKER_GAP * (geom.es or 1)))
    if cycle > 0 then
        local tracked_ax = self._ticker_x_a or 0
        if math.abs(tax - tracked_ax) > 1.5 then
            _pred_fail("ticker_a_x_tracking_drift")
            return false
        end
        if math.abs(tax) > 0.5 then
            _pred_fail("ticker_a_x_bounds")
            return false
        end
    end
    if not check_text(self._ticker_b, desired_ticker, geom.ticker_font, true, false, 0, geom.ticker.h, "ticker_b") then
        return false
    end
    local ok_tbx, tbx = a_safe_call(self._ticker_b, "x")
    if ok_tbx ~= a_call_ok or not a_is_finite(tbx) then
        _pred_fail("ticker_b_x_read_failed")
        return false
    end
    local s_tbw, tbw = a_safe_call(self._ticker_b, "w")
    if s_tbw == a_call_ok and a_is_finite(tbw) and (self._ticker_measured_w or 0) > 0 then
        if math.abs(tbw - self._ticker_measured_w) > 1.5 then
            _pred_fail("ticker_b_width_drift")
            return false
        end
    end
    if cycle > 0 then
        local tracked_bx = self._ticker_x_b or 0
        if math.abs(tbx - tracked_bx) > 1.5 then
            _pred_fail("ticker_b_x_tracking_drift")
            return false
        end
        local expected_bx = tax + cycle
        if math.abs(tbx - expected_bx) > tol then
            _pred_fail("ticker_b_x_gap_drift")
            return false
        end
    end
    local desired_tex = self._cached_status_texture
    if type(desired_tex) ~= "string" or desired_tex == "" then
        _pred_fail("no_status_texture")
        return false
    end
    local ok_gv, gv = pcall(function() return self._glyph_prim:visible() end)
    if not ok_gv or gv ~= true then
        _pred_fail("glyph_visible_false")
        return false
    end
    if geom.status then
        local gx_s, gx = a_safe_call(self._glyph_prim, "x")
        local gy_s, gy = a_safe_call(self._glyph_prim, "y")
        local gw_s, gw = a_safe_call(self._glyph_prim, "w")
        local gh_s, gh = a_safe_call(self._glyph_prim, "h")
        if gx_s ~= a_call_ok or gy_s ~= a_call_ok or gw_s ~= a_call_ok or gh_s ~= a_call_ok then
            _pred_fail("glyph_geom_read_failed")
            return false
        end
        if not a_is_finite(gx) or not a_is_finite(gy) or not a_is_finite(gw) or not a_is_finite(gh) then
            _pred_fail("glyph_geom_non_finite")
            return false
        end
        if math.abs(gx - geom.status.x) > tol or math.abs(gy - geom.status.y) > tol
            or math.abs(gw - geom.status.w) > tol or math.abs(gh - geom.status.h) > tol then
            _pred_fail("glyph_geom_drift")
            return false
        end
    end
    local ok_gt, gt = pcall(function() return self._glyph_prim:texture_name() end)
    if not ok_gt or gt == nil then
        _pred_fail("glyph_texture_read_failed")
        return false
    end
    if not a_texture_matches(gt, desired_tex) then
        _pred_fail("glyph_texture_mismatch")
        return false
    end
    local desired_hostages = self._cached_hostages_text
    if type(desired_hostages) ~= "string" or desired_hostages == "" then
        _pred_fail("no_hostages_text")
        return false
    end
    if not check_text(self._hostages_prim, desired_hostages, geom.counter_font, true, false, geom.counter_y, geom.counter_h, "hostages_prim") then
        return false
    end
    local desired_converted = self._cached_converted_text
    if type(desired_converted) ~= "string" or desired_converted == "" then
        _pred_fail("no_converted_text")
        return false
    end
    if not check_text(self._converted_prim, desired_converted, geom.counter_font, true, false, geom.counter_y, geom.counter_h, "converted_prim") then
        return false
    end
    a_init_colors()
    local function check_color_rgba(prim, exp_r, exp_g, exp_b, exp_a, prim_name)
        if not prim or not a_panel_alive(prim) then
            _pred_fail(prim_name .. "_dead")
            return false
        end
        local r, g, b, a = a_read_color(prim)
        if not r then
            _pred_fail(prim_name .. "_color_read_failed")
            return false
        end
        if math.abs(r - exp_r) > 0.01 then
            _pred_fail(prim_name .. "_color_r", r, exp_r)
            return false
        end
        if math.abs(g - exp_g) > 0.01 then
            _pred_fail(prim_name .. "_color_g", g, exp_g)
            return false
        end
        if math.abs(b - exp_b) > 0.01 then
            _pred_fail(prim_name .. "_color_b", b, exp_b)
            return false
        end
        if math.abs(a - exp_a) > 0.02 then
            _pred_fail(prim_name .. "_color_a", a, exp_a)
            return false
        end
        return true
    end
    local endless = self._state.endless == true
    local palette = self:_banner_palette()
    local exp_bg_r, exp_bg_g, exp_bg_b = palette.r, palette.g, palette.b
    if not check_color_rgba(self._bg_rect, exp_bg_r, exp_bg_g, exp_bg_b, 1, "bg_rect") then
        return false
    end
    if not check_color_rgba(self._hostages_bg, 0.043, 0.051, 0.067, 0.75, "hostages_bg") then
        return false
    end
    if not check_color_rgba(self._converted_bg, 0.043, 0.051, 0.067, 0.75, "converted_bg") then
        return false
    end
    local exp_ticker_r, exp_ticker_g, exp_ticker_b = palette.ir, palette.ig, palette.ib
    local exp_ticker_a = 1
    local exp_outgoing_a = 0
    if self._transition_active then
        local dur = self._transition_duration or TRANSITION_DURATION
        local p = (self._transition_elapsed or 0) / dur
        if p < 0 then p = 0 end
        if p > 1 then p = 1 end
        exp_ticker_a = p
        exp_outgoing_a = 1.0 - p
    end
    if not check_color_rgba(self._ticker_a, exp_ticker_r, exp_ticker_g, exp_ticker_b, exp_ticker_a, "ticker_a") then
        return false
    end
    if not check_color_rgba(self._ticker_b, exp_ticker_r, exp_ticker_g, exp_ticker_b, exp_ticker_a, "ticker_b") then
        return false
    end
    if self._transition_active then
        if not self._outgoing_ticker_a or not a_panel_alive(self._outgoing_ticker_a) then
            _pred_fail("outgoing_a_dead")
            return false
        end
        if not self._outgoing_ticker_b or not a_panel_alive(self._outgoing_ticker_b) then
            _pred_fail("outgoing_b_dead")
            return false
        end
        local snap = self._transition_old_text
        if type(snap) ~= "string" or snap == "" then
            _pred_fail("no_outgoing_text")
            return false
        end
        local out_r = self._transition_old_color_r or exp_ticker_r
        local out_g = self._transition_old_color_g or exp_ticker_g
        local out_b = self._transition_old_color_b or exp_ticker_b
        local out_w = self._transition_old_w or 0
        if out_w <= 0 then out_w = geom.ticker.w end
        local out_ticker_h = geom.ticker.h
        local function check_outgoing(prim, exp_x, prim_name)
            if not prim or not a_panel_alive(prim) then
                _pred_fail(prim_name .. "_dead")
                return false
            end
            local ok_v, v = pcall(function() return prim:visible() end)
            if not ok_v or v ~= true then
                _pred_fail(prim_name .. "_visible_false")
                return false
            end
            local ok_t, t = pcall(function() return prim:text() end)
            if not ok_t or type(t) ~= "string" or t ~= snap then
                _pred_fail(prim_name .. "_text_mismatch")
                return false
            end
            local ok_fs, fs = pcall(function() return prim:font_size() end)
            if not ok_fs or not a_is_finite(fs) or fs <= 0 then
                _pred_fail(prim_name .. "_font_size_invalid")
                return false
            end
            if math.abs(fs - geom.ticker_font) > 0.5 then
                _pred_fail(prim_name .. "_font_size_drift", fs, geom.ticker_font)
                return false
            end
            local ok_y, y = pcall(function() return prim:y() end)
            if not ok_y or not a_is_finite(y) then
                _pred_fail(prim_name .. "_y_read_failed")
                return false
            end
            if math.abs(y - 0) > tol then
                _pred_fail(prim_name .. "_y_drift", y, 0)
                return false
            end
            local ok_w, w = pcall(function() return prim:w() end)
            if not ok_w or not a_is_finite(w) then
                _pred_fail(prim_name .. "_w_read_failed")
                return false
            end
            if math.abs(w - out_w) > 1.5 then
                _pred_fail(prim_name .. "_w_drift", w, out_w)
                return false
            end
            local ok_h, h = pcall(function() return prim:h() end)
            if not ok_h or not a_is_finite(h) then
                _pred_fail(prim_name .. "_h_read_failed")
                return false
            end
            if math.abs(h - out_ticker_h) > tol then
                _pred_fail(prim_name .. "_h_drift", h, out_ticker_h)
                return false
            end
            local ok_l, l = pcall(function() return prim:layer() end)
            if not ok_l or not a_is_finite(l) then
                _pred_fail(prim_name .. "_layer_read_failed")
                return false
            end
            if math.abs(l - 1) > 0.001 then
                _pred_fail(prim_name .. "_layer_drift", l, 1)
                return false
            end
            local ok_p, p = pcall(function() return prim:parent() end)
            if not ok_p or p ~= self._ticker_panel then
                _pred_fail(prim_name .. "_parent_mismatch")
                return false
            end
            local ok_x, x = pcall(function() return prim:x() end)
            if not ok_x or not a_is_finite(x) then
                _pred_fail(prim_name .. "_x_read_failed")
                return false
            end
            if math.abs(x - exp_x) > 1.5 then
                _pred_fail(prim_name .. "_x_drift", x, exp_x)
                return false
            end
            local ok_al, al = pcall(function() return prim:alpha() end)
            if not ok_al or not a_is_finite(al) then
                _pred_fail(prim_name .. "_alpha_read_failed")
                return false
            end
            if math.abs(al - exp_outgoing_a) > 0.05 then
                _pred_fail(prim_name .. "_alpha_drift", al, exp_outgoing_a)
                return false
            end
            local ok_mr, mr_x, mr_y, mw, mh = pcall(function() return prim:text_rect() end)
            if not ok_mr then
                _pred_fail(prim_name .. "_text_rect_failed")
                return false
            end
            if not a_is_finite(mw) or not a_is_finite(mh) then
                _pred_fail(prim_name .. "_text_rect_non_finite")
                return false
            end
            if mw <= 0 or mh <= 0 then
                _pred_fail(prim_name .. "_text_rect_zero")
                return false
            end
            local r, g, b, a = a_read_color(prim)
            if not r then
                _pred_fail(prim_name .. "_color_read_failed")
                return false
            end
            if math.abs(r - out_r) > 0.01 then
                _pred_fail(prim_name .. "_color_r", r, out_r)
                return false
            end
            if math.abs(g - out_g) > 0.01 then
                _pred_fail(prim_name .. "_color_g", g, out_g)
                return false
            end
            if math.abs(b - out_b) > 0.01 then
                _pred_fail(prim_name .. "_color_b", b, out_b)
                return false
            end
            if math.abs(a - exp_outgoing_a) > 0.02 then
                _pred_fail(prim_name .. "_color_a", a, exp_outgoing_a)
                return false
            end
            return true
        end
        local exp_ox_a = self._transition_old_x_a or 0
        if not check_outgoing(self._outgoing_ticker_a, exp_ox_a, "outgoing_a") then
            return false
        end
        local exp_ox_b = self._transition_old_x_b or 0
        if not check_outgoing(self._outgoing_ticker_b, exp_ox_b, "outgoing_b") then
            return false
        end
    end
    if not check_color_rgba(self._hostages_prim, 0.788, 0.820, 0.847, 1, "hostages_prim") then
        return false
    end
    if not check_color_rgba(self._converted_prim, 0.788, 0.820, 0.847, 1, "converted_prim") then
        return false
    end
    if not check_color_rgba(self._glyph_prim,1,1,1,1, "glyph_prim") then
        return false
    end
    if not check_color_rgba(self._hostages_icon,1,1,1,1, "hostages_icon") then
        return false
    end
    if not check_color_rgba(self._converted_icon,1,1,1,1, "converted_icon") then
        return false
    end
    local function check_visible_explicit(prim, prim_name)
        if not prim or not a_panel_alive(prim) then
            _pred_fail(prim_name .. "_dead")
            return false
        end
        local ok_v, v = pcall(function() return prim:visible() end)
        if not ok_v or v ~= true then
            _pred_fail(prim_name .. "_visible_false")
            return false
        end
        return true
    end
    if not check_visible_explicit(self._hostages_bg, "hostages_bg") then
        return false
    end
    if not check_visible_explicit(self._converted_bg, "converted_bg") then
        return false
    end
    if not check_visible_explicit(self._hostages_icon, "hostages_icon") then
        return false
    end
    if not check_visible_explicit(self._converted_icon, "converted_icon") then
        return false
    end
    local hbg_x_s, hbg_x = a_safe_call(self._hostages_bg, "x")
    local hbg_y_s, hbg_y = a_safe_call(self._hostages_bg, "y")
    local hbg_w_s, hbg_w = a_safe_call(self._hostages_bg, "w")
    local hbg_h_s, hbg_h = a_safe_call(self._hostages_bg, "h")
    if hbg_x_s ~= a_call_ok or hbg_y_s ~= a_call_ok or hbg_w_s ~= a_call_ok or hbg_h_s ~= a_call_ok then
        _pred_fail("hostages_bg_geom_read_failed")
        return false
    end
    if not a_is_finite(hbg_x) or not a_is_finite(hbg_y) or not a_is_finite(hbg_w) or not a_is_finite(hbg_h) then
        _pred_fail("hostages_bg_geom_non_finite")
        return false
    end
    local cbg_x_s, cbg_x = a_safe_call(self._converted_bg, "x")
    local cbg_y_s, cbg_y = a_safe_call(self._converted_bg, "y")
    local cbg_w_s, cbg_w = a_safe_call(self._converted_bg, "w")
    local cbg_h_s, cbg_h = a_safe_call(self._converted_bg, "h")
    if cbg_x_s ~= a_call_ok or cbg_y_s ~= a_call_ok or cbg_w_s ~= a_call_ok or cbg_h_s ~= a_call_ok then
        _pred_fail("converted_bg_geom_read_failed")
        return false
    end
    if not a_is_finite(cbg_x) or not a_is_finite(cbg_y) or not a_is_finite(cbg_w) or not a_is_finite(cbg_h) then
        _pred_fail("converted_bg_geom_non_finite")
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
        _pred_fail("converted_bg_x_drift", cbg_x, expected_c_x)
        return false
    end
    if math.abs(cbg_y - expected_counter_y) > tol then
        _pred_fail("converted_bg_y_drift", cbg_y, expected_counter_y)
        return false
    end
    if math.abs(cbg_w - c_cw) > 1.5 then
        _pred_fail("converted_bg_w_drift", cbg_w, c_cw)
        return false
    end
    if math.abs(cbg_h - expected_cell_h) > tol then
        _pred_fail("converted_bg_h_drift", cbg_h, expected_cell_h)
        return false
    end
    if math.abs(hbg_x - expected_h_x) > 1.5 then
        _pred_fail("hostages_bg_x_drift", hbg_x, expected_h_x)
        return false
    end
    if math.abs(hbg_y - expected_counter_y) > tol then
        _pred_fail("hostages_bg_y_drift", hbg_y, expected_counter_y)
        return false
    end
    if math.abs(hbg_w - h_cw) > 1.5 then
        _pred_fail("hostages_bg_w_drift", hbg_w, h_cw)
        return false
    end
    if math.abs(hbg_h - expected_cell_h) > tol then
        _pred_fail("hostages_bg_h_drift", hbg_h, expected_cell_h)
        return false
    end
    local hi_x_s, hi_x = a_safe_call(self._hostages_icon, "x")
    local hi_y_s, hi_y = a_safe_call(self._hostages_icon, "y")
    local hi_w_s, hi_w = a_safe_call(self._hostages_icon, "w")
    local hi_h_s, hi_h = a_safe_call(self._hostages_icon, "h")
    if hi_x_s ~= a_call_ok or hi_y_s ~= a_call_ok or hi_w_s ~= a_call_ok or hi_h_s ~= a_call_ok then
        _pred_fail("hostages_icon_geom_read_failed")
        return false
    end
    if not a_is_finite(hi_x) or not a_is_finite(hi_y) or not a_is_finite(hi_w) or not a_is_finite(hi_h) then
        _pred_fail("hostages_icon_geom_non_finite")
        return false
    end
    local ci_x_s, ci_x = a_safe_call(self._converted_icon, "x")
    local ci_y_s, ci_y = a_safe_call(self._converted_icon, "y")
    local ci_w_s, ci_w = a_safe_call(self._converted_icon, "w")
    local ci_h_s, ci_h = a_safe_call(self._converted_icon, "h")
    if ci_x_s ~= a_call_ok or ci_y_s ~= a_call_ok or ci_w_s ~= a_call_ok or ci_h_s ~= a_call_ok then
        _pred_fail("converted_icon_geom_read_failed")
        return false
    end
    if not a_is_finite(ci_x) or not a_is_finite(ci_y) or not a_is_finite(ci_w) or not a_is_finite(ci_h) then
        _pred_fail("converted_icon_geom_non_finite")
        return false
    end
    local pad = geom.cell_pad or REF_CELL_PAD
    local isz = geom.icon_size or REF_ICON_SIZE
    local expected_icon_y = expected_counter_y + math.floor((expected_cell_h - isz) / 2)
    if expected_icon_y < expected_counter_y then expected_icon_y = expected_counter_y end
    local expected_hi_x = expected_h_x + pad
    local expected_ci_x = expected_c_x + pad
    local function counter_geometry(p, expected_x, width, prim_name)
        local ok, same = pcall(function()
            return math.abs(p:x()-expected_x)<=tol and math.abs(p:w()-width)<=tol
                and p:parent()==self._root_panel
        end)
        if not ok then
            _pred_fail(prim_name .. "_geom_read_failed")
            return false
        end
        if same ~= true then
            _pred_fail(prim_name .. "_geom_drift")
            return false
        end
        return true
    end
    if expected_h_x<0 then
        _pred_fail("hostages_prim_x_negative")
        return false
    end
    if not counter_geometry(self._hostages_prim,
        expected_h_x+pad+isz+(geom.icon_gap or REF_ICON_GAP),h_tw, "hostages_prim") then
        return false
    end
    if not counter_geometry(self._converted_prim,
        expected_c_x+pad+isz+(geom.icon_gap or REF_ICON_GAP),c_tw, "converted_prim") then
        return false
    end
    if math.abs(hi_x - expected_hi_x) > tol then
        _pred_fail("hostages_icon_x_drift", hi_x, expected_hi_x)
        return false
    end
    if math.abs(hi_y - expected_icon_y) > tol then
        _pred_fail("hostages_icon_y_drift", hi_y, expected_icon_y)
        return false
    end
    if math.abs(hi_w - isz) > tol then
        _pred_fail("hostages_icon_w_drift", hi_w, isz)
        return false
    end
    if math.abs(hi_h - isz) > tol then
        _pred_fail("hostages_icon_h_drift", hi_h, isz)
        return false
    end
    if math.abs(ci_x - expected_ci_x) > tol then
        _pred_fail("converted_icon_x_drift", ci_x, expected_ci_x)
        return false
    end
    if math.abs(ci_y - expected_icon_y) > tol then
        _pred_fail("converted_icon_y_drift", ci_y, expected_icon_y)
        return false
    end
    if math.abs(ci_w - isz) > tol then
        _pred_fail("converted_icon_w_drift", ci_w, isz)
        return false
    end
    if math.abs(ci_h - isz) > tol then
        _pred_fail("converted_icon_h_drift", ci_h, isz)
        return false
    end
    local ok_hi_tex, hi_tex = pcall(function() return self._hostages_icon:texture_name() end)
    if not ok_hi_tex or hi_tex == nil then
        _pred_fail("hostages_icon_texture_read_failed")
        return false
    end
    if not a_texture_matches(hi_tex, TEX_HOSTAGE) then
        _pred_fail("hostages_icon_texture_mismatch")
        return false
    end
    local ok_ci_tex, ci_tex = pcall(function() return self._converted_icon:texture_name() end)
    if not ok_ci_tex or ci_tex == nil then
        _pred_fail("converted_icon_texture_read_failed")
        return false
    end
    if not a_texture_matches(ci_tex, TEX_CONVERTED) then
        _pred_fail("converted_icon_texture_mismatch")
        return false
    end

    local function check_layer(prim, expected, prim_name)
        if not prim or not a_panel_alive(prim) then
            _pred_fail(prim_name .. "_dead")
            return false
        end
        local ok_l, l = pcall(function() return prim:layer() end)
        if not ok_l or not a_is_finite(l) then
            _pred_fail(prim_name .. "_layer_read_failed")
            return false
        end
        if math.abs(l - expected) > 0.001 then
            _pred_fail(prim_name .. "_layer_drift", l, expected)
            return false
        end
        return true
    end
    if not check_layer(self._bg_rect, 0, "bg_rect") then
        return false
    end
    if not check_layer(self._ticker_panel, 1, "ticker_panel") then
        return false
    end
    if not check_layer(self._ticker_a, 1, "ticker_a") then
        return false
    end
    if not check_layer(self._ticker_b, 1, "ticker_b") then
        return false
    end
    if not check_layer(self._glyph_prim, 1, "glyph_prim") then
        return false
    end
    if not check_layer(self._hostages_bg, 1, "hostages_bg") then
        return false
    end
    if not check_layer(self._converted_bg, 1, "converted_bg") then
        return false
    end
    if not check_layer(self._hostages_prim, 2, "hostages_prim") then
        return false
    end
    if not check_layer(self._converted_prim, 2, "converted_prim") then
        return false
    end
    if not check_layer(self._hostages_icon, 2, "hostages_icon") then
        return false
    end
    if not check_layer(self._converted_icon, 2, "converted_icon") then
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
    if not ok_tp then return nil end
    local tp_absent = false
    if tp == nil then
        tp_absent = true
    else
        if type(tp) ~= "table" and type(tp) ~= "userdata" then return nil end
        if not a_panel_alive(tp) then return nil end
        if not check_parent(tp, bg) then return nil end
    end
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
    if tp_absent then
        if self._state.active == true then return nil end
        if self._state.endless == true then return nil end
        local host_anticipation = (self._state.is_host == true and self._state.phase == "anticipation")
        local client_prep_known = (self._state.client_preparation == true)
        if not host_anticipation and not client_prep_known then return nil end
        local ok_ca, ca = pcall(function() return corner._assault end)
        if not ok_ca then return nil end
        if ca ~= nil and ca ~= false then return nil end
        return {
            corner = corner,
            hud_panel = hp,
            text_panel = nil,
            text_panel_absent = true,
            bg_leaves = bg_leaves,
            assault_icon = icon,
            hostage_icon = hi,
            hostage_bg = hb,
            hostage_bg_leaves = hostage_bg_leaves,
            num = num,
        }
    end
    return {
        corner = corner,
        hud_panel = hp,
        text_panel = tp,
        text_panel_absent = false,
        bg_leaves = bg_leaves,
        assault_icon = icon,
        hostage_icon = hi,
        hostage_bg = hb,
        hostage_bg_leaves = hostage_bg_leaves,
        num = num,
    }
end

function A:_should_fallback_native()
    if not self._manager then return true, "disabled" end
    local ok_corner, corner = pcall(function() return self._manager._hud_assault_corner end)
    if not ok_corner or not corner then return true, "not_present" end
    local ok_waves, waves = pcall(function() return corner:should_display_waves() end)
    if not ok_waves then return true, "should_display_waves" end
    if waves == true then return true, "should_display_waves" end
    local ok_pnr, pnr = pcall(function() return corner._point_of_no_return end)
    if ok_pnr and pnr == true then return true, "pnr" end
    local ok_cas, cas = pcall(function() return corner._casing end)
    if ok_cas and cas == true then return true, "casing" end
    local AL = kyohud and kyohud.hud and kyohud.hud.alerts
    if type(AL) == "table" and type(AL.blocks_assault) == "function" then
        local ok_ba, ba = pcall(AL.blocks_assault, AL, self._manager)
        if ok_ba then
            if ba == true then return true, "alerts_blocking" end
        else
            return true, "alerts_blocking"
        end
    else
        local ok_hp2, hp2 = pcall(function() return corner._hud_panel end)
        if ok_hp2 and hp2 and a_panel_alive(hp2) then
            local ok_cp, cp = pcall(function() return hp2:child("casing_panel") end)
            if ok_cp and cp and a_panel_alive(cp) then
                local ok_cv, cv = pcall(function() return cp:visible() end)
                if ok_cv and cv == true then return true, "casing" end
            end
        end
    end
    local ok_hp, hp = pcall(function() return corner._hud_panel end)
    if ok_hp and hp and a_panel_alive(hp) then
        local check_panels = { "point_of_no_return_panel", "buffs_panel" }
        for _, name in ipairs(check_panels) do
            local ok_p, pnl = pcall(function() return hp:child(name) end)
            if not ok_p then return true, "alerts_blocking" end
            if pnl and a_panel_alive(pnl) then
                local ok_v, v = pcall(function() return pnl:visible() end)
                if not ok_v then return true, "alerts_blocking" end
                if v == true then return true, "buffs" end
            end
        end
    end
    local ok_am, am = pcall(function() return corner._assault_mode end)
    if ok_am and am == "phalanx" then
        local ok_state, state = pcall(function() return managers.groupai:state() end)
        if not ok_state or not state then return true, "phalanx" end
        local ok_hunt, hunt = pcall(function() return state:get_hunt_mode() end)
        if not ok_hunt then return true, "phalanx" end
        if hunt ~= true then return true, "phalanx" end
    end
    if self._bai_advanced_active == true then
        local gt = self._assault_state_diag_bai_getter_type
        if gt == "function" then
            return true, "bai_advanced_active"
        else
            return true, "bai_advanced_unknown"
        end
    end
    return false
end

function A:_try_acquire_native()
    if not self._render_verified then return false end
    if self._state.presenting ~= true then return false end
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
    local has_text_panel = (targets.text_panel ~= nil) and (not targets.text_panel_absent)
    if self._native_acquired then
        if self._native_corner ~= targets.corner then
            local released = self:_release_native()
            if not released then return false end
        else
            local set_changed = ((self._native_had_text_panel or false) ~= has_text_panel)
            if not set_changed and has_text_panel and self._native_targets then
                if self._native_targets.text_panel ~= targets.text_panel then
                    set_changed = true
                end
            end
            if set_changed then
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
        end
    elseif self._native_corner and self._native_corner ~= targets.corner then
        local released = self:_release_native()
        if not released then return false end
    end
    if has_text_panel then
        nv._whitelist[targets.text_panel] = nv._whitelist[targets.text_panel] or {}
        nv._whitelist[targets.text_panel].alpha = true
    end
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
    local requests = {}
    if has_text_panel then
        requests[#requests + 1] = { id = targets.text_panel, property = "alpha", value = 0 }
    end
    for _, obj in ipairs(visible_objs) do
        requests[#requests + 1] = { id = obj, property = "visible", value = false }
    end
    self._native_requests = requests
    self._native_corner = targets.corner
    self._native_hud_panel = targets.hud_panel
    self._native_targets = targets
    self._native_generation = gen
    self._native_had_text_panel = has_text_panel
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
        if targets.text_panel and nv._whitelist[targets.text_panel] then
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
    self._native_had_text_panel = nil
    self._native_generation = 0
    return true
end

function A:_sync_native_visibility()
    local should_fallback = false
    if self._state.presenting ~= true then
        should_fallback = true
    else
        if self:_should_fallback_native() then
            should_fallback = true
        end
    end
    if not should_fallback and (not self._root_panel or not a_panel_alive(self._root_panel)) then
        should_fallback = true
    end
    if not should_fallback and not self._layout_cache then
        should_fallback = true
    end

    if should_fallback then
        if self._native_acquired or self._native_corner then
            self:_release_native()
        end
        self:_hide_outgoing()
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
            self:_refresh_bai_bridge()
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
    self._title_panel, self._title_a, self._title_b, self._title_divider = nil, nil, nil, nil
    self._parent_panel = parent
    self._mounted = true
    self:_take_initial_snapshot()
    self:_update_layout()
    self:_ensure_primitives()
    self:_refresh_bai_bridge()
    self:_sync_native_visibility()
end

function A:unmount()
    local released = self:_release_native()
    if released then
        self._conflict_corner = nil
    end
    self:_cancel_transition()
    self._after_assault_active = false
    self._after_assault_pending = false
    self._after_assault_start = nil
    self._cached_label_key = nil
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
    self._title_panel, self._title_a, self._title_b, self._title_divider = nil, nil, nil, nil
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
    self._bai_bonus_phase = nil
    self._bai_qualified = false
    self._bai_advanced_active = false
    self._ticker_x_a = 0
    self._ticker_x_b = 0
    self._ticker_measured_w = 0
    self._outgoing_ticker_a = nil
    self._outgoing_ticker_b = nil
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
    if self._after_assault_pending then
        self._after_assault_pending = false
        self._after_assault_active = true
        self._after_assault_start = t
        self:_update_presenting()
        self._data_dirty = true
    end
    if self._after_assault_active and self._after_assault_start and a_is_finite(t) then
        local elapsed = t - self._after_assault_start
        if elapsed >= AFTER_ASSAULT_WINDOW then
            self._after_assault_active = false
            self._after_assault_start = nil
            self:_update_presenting()
            self._data_dirty = true
        end
    end
    local do_refresh = false
    if t and (self._last_counter_time == nil or (t - self._last_counter_time) >= COUNTER_INTERVAL) then
        do_refresh = true
        self._last_counter_time = t
    end
    if do_refresh then
        self:_refresh_bai_bridge()
        self:_refresh_counters()
        self:_update_layout()
        self:_ensure_primitives()
    end
    self:_update_banner_alternation(dt)
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
    if self._transition_active and a_is_finite(dt) and dt > 0 then
        self:_update_transition(dt)
    end
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
    self._lull_source, self._lull_manager = nil, nil
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
    self._event_client_preparation = nil
    self._event_has_client_preparation = false
    self._state.phase = nil
    self._state.is_host = false
    self._state.client_preparation = false
    self._state.presenting = false
    self._after_assault_active = false
    self._after_assault_pending = false
    self._after_assault_start = nil
    self._cached_label_key = nil
    self:_purge_bai_bridge()
    self._manager = mgr
end

local function safe_hook(class, method, id, fn)
    if type(class) ~= "table" then return end
    if kyohud.hud._installed_hooks[id] then return end
    if type(class[method]) ~= "function" then return end
    Hooks:PostHook(class, method, id, fn)
    kyohud.hud._installed_hooks[id] = true
end

function A:_is_lull()
    return self._source ~= nil and self._lull_source == self._source
        and self._lull_manager == self._manager
        and self._state.active ~= true and self._state.endless ~= true
        and self._state.phase ~= "anticipation" and self._state.client_preparation ~= true
end

function A:_banner_text(key)
    local ok, text = pcall(function() return managers.localization:text(key) end)
    if ok and type(text)=="string" and text~="" and text~=key
        and not string.find(text,"LOC:",1,true) then return text end
    return STATUS_FALLBACKS[key] or key
end

function A:_resolve_banner_difficulty()
    local ok, difficulty = pcall(function()
        local name_id = tweak_data.difficulty_name_ids[Global.game_settings.difficulty]
        if not name_id then return nil end
        local text = managers.localization:text(name_id)
        if type(text)~="string" or text=="" or text==name_id then return nil end
        return text
    end)
    if not ok or not difficulty then
        difficulty = self:_resolve_difficulty_text()
    else
        -- Named difficulty replaces the old skull string, not Crime Spree data.
        local ok_cs, level = pcall(function()
            local cs = managers.crime_spree
            if cs and cs:is_active() == true then return cs:server_spree_level() end
        end)
        if ok_cs and is_finite_nonneg(level) then
            difficulty = difficulty .. " [" .. math.floor(level) .. "]"
        end
    end
    if difficulty and difficulty ~= "" and difficulty ~= "--" then return difficulty end
    return nil
end

function A:_resolve_title_text()
    local key = "ky_hud_assault_title"
    if self:_is_lull() or self._after_assault_active then
        key = "ky_hud_assault_idle_title"
    elseif self._state.active == true or self._state.endless == true then
        key = "ky_hud_assault_active_title"
    end
    return self:_banner_text(key)
end

function A:_sync_banner_regions()
    local g = self._layout_cache
    if not g or not a_panel_alive(self._ticker_a) then return false end
    local ok,x,y,w,h = pcall(function() return self._ticker_a:text_rect() end)
    if not ok or not a_is_finite(w) or w<=0 then return false end
    -- Keep both state labels inside the fixed region throughout a crossfade.
    if self._transition_active and a_is_finite(self._transition_old_w) then
        w = math.max(w,self._transition_old_w)
    end
    local es = g.es
    local width = (math.ceil(w/es)+2)*es
    local state_x = 332*es-width
    if state_x-16*es < 80*es then return false end
    g.ticker.x, g.ticker.w = state_x,width
    g.title.w = state_x-16*es
    g.separator_x = state_x-6*es
    a_safe_call(self._ticker_panel,"set_shape",state_x,0,width,g.ticker.h)
    self._ticker_gap = math.max(REF_TICKER_GAP*es,width+8*es)
    self._ticker_x_b = (self._ticker_measured_w or 0)+self._ticker_gap
    a_safe_call(self._ticker_b,"set_x",self._ticker_x_b)
    return true
end

function A:_sync_title()
    if not self._layout_cache or not a_panel_alive(self._root_panel) then return end
    if not self:_sync_banner_regions() then return end
    a_init_colors()
    local g = self._layout_cache
    local t = g.title
    local ink = self:_banner_palette().ink
    if not self._title_panel or not a_panel_alive(self._title_panel) then
        local status, panel = a_safe_call(self._root_panel,"panel",{
            name="kyohud_assault_main_title",x=t.x,y=t.y,w=t.w,h=t.h,clipping=true,layer=1,
        })
        if status~=a_call_ok or not panel then return end
        self._title_panel = panel
        self._title_a, self._title_b, self._title_x = nil, nil, 0
    end
    a_safe_call(self._title_panel,"set_shape",t.x,t.y,t.w,t.h)
    a_safe_call(self._title_panel,"set_visible",true)
    a_safe_call(self._title_panel,"set_alpha",1)
    a_safe_call(self._title_panel,"set_layer",1)
    local base = self:_resolve_title_text()
    local text = base .. " /// "
    for _,field in ipairs({"_title_a","_title_b"}) do
        local p = self[field]
        if not p or not a_panel_alive(p) then
            local status,created = a_safe_call(self._title_panel,"text",{
                name=field,text=text,font=self:_get_font(),font_size=g.ticker_font,
                x=0,y=0,w=t.w,h=t.h,color=ink,layer=1,
                align="left",vertical="center",wrap=false,word_wrap=false,
            })
            if status~=a_call_ok or not created then return end
            self[field],p = created,created
        end
        a_safe_call(p,"set_text",text)
        a_safe_call(p,"set_font_size",g.ticker_font)
        a_safe_call(p,"set_color",ink)
        a_safe_call(p,"set_alpha",1)
        a_safe_call(p,"set_visible",true)
        a_safe_call(p,"set_layer",1)
    end
    local ok,x,y,w,h = pcall(function() return self._title_a:text_rect() end)
    if not ok or not a_is_finite(w) or w<=0 then return end
    -- Fill each retained run before tiling it, even when the title is short.
    local count = math.max(1,math.ceil(t.w/w))
    if count > 32 then return end
    while count <= 32 do
        local run = string.rep(text,count)
        a_safe_call(self._title_a,"set_text",run)
        a_safe_call(self._title_b,"set_text",run)
        ok,x,y,w,h = pcall(function() return self._title_a:text_rect() end)
        if not ok or not a_is_finite(w) or w<=0 then return end
        if w >= t.w then
            self._title_run_base, self._title_run_text = base, run
            break
        end
        count = count + 1
    end
    if count > 32 then return end
    self._title_w = w
    self._title_cycle = w
    self._title_x = -((-(self._title_x or 0)) % self._title_cycle)
    a_safe_call(self._title_a,"set_shape",self._title_x,0,w,t.h)
    a_safe_call(self._title_b,"set_shape",self._title_x+self._title_cycle,0,w,t.h)
    if not self._title_divider or not a_panel_alive(self._title_divider) then
        local status,rect = a_safe_call(self._root_panel,"rect",{
            name="kyohud_assault_state_separator",x=g.separator_x,y=8*g.es,
            w=2*g.es,h=24*g.es,color=ink,layer=2,
        })
        if status==a_call_ok then self._title_divider = rect end
    end
    if self._title_divider then
        a_safe_call(self._title_divider,"set_shape",g.separator_x,8*g.es,2*g.es,24*g.es)
        a_safe_call(self._title_divider,"set_color",ink)
        a_safe_call(self._title_divider,"set_alpha",1)
        a_safe_call(self._title_divider,"set_visible",true)
        a_safe_call(self._title_divider,"set_layer",2)
    end
end

function A:_update_title(dt)
    if not a_is_finite(dt) or dt<=0 or not self._title_cycle then return end
    if not a_panel_alive(self._title_a) or not a_panel_alive(self._title_b) then return end
    local es = self._layout_cache and self._layout_cache.es or 1
    self._title_x = -((-(self._title_x or 0)+REF_TICKER_SPEED*es*dt) % self._title_cycle)
    a_safe_call(self._title_a,"set_x",self._title_x)
    a_safe_call(self._title_b,"set_x",self._title_x+self._title_cycle)
end

function A:_verify_title()
    local g = self._layout_cache
    if not g or not g.title then return false end
    local ok,verified = pcall(function()
        local function shape(p,parent,x,y,w,h,layer)
            return a_panel_alive(p) and p:parent()==parent and p:visible()==true
                and math.abs(p:x()-x)<=.5 and math.abs(p:y()-y)<=.5
                and math.abs(p:w()-w)<=.5 and math.abs(p:h()-h)<=.5
                and p:layer()==layer and math.abs(p:alpha()-1)<=.02
        end
        local t = g.title
        if not shape(self._title_panel,self._root_panel,t.x,t.y,t.w,t.h,1) then return false end
        if not a_panel_alive(self._ticker_a) then return false end
        local sx,sy,sw,sh = self._ticker_a:text_rect()
        if not a_is_finite(sw) or not a_is_finite(sh) or sw>g.ticker.w+.5
            or sh>g.ticker.h+.5 then return false end
        if not self._title_a or not self._title_b then return false end
        if not a_is_finite(self._title_cycle) or not a_is_finite(self._title_x)
            or self._title_cycle<=0 or self._title_x>0 or self._title_x < -self._title_cycle then return false end
        if self._title_run_base ~= self:_resolve_title_text()
            or type(self._title_run_text) ~= "string" or self._title_run_text == ""
            or self._title_w < t.w or math.abs(self._title_cycle-self._title_w)>.5 then return false end
        local text = self._title_run_text
        local ink = self:_banner_palette().ink
        for i,p in ipairs({self._title_a,self._title_b}) do
            if not shape(p,self._title_panel,self._title_x+(i-1)*self._title_cycle,0,self._title_w,t.h,1)
                or p:text()~=text or p:font_size()~=g.ticker_font then return false end
            local x,y,w,h = p:text_rect()
            if not a_is_finite(w) or not a_is_finite(h) or math.abs(w-self._title_w)>1.5 or h>t.h+.5 then return false end
            local r,green,b,alpha = a_read_color(p)
            if not r or math.abs(r-ink.r)>.01 or math.abs(green-ink.g)>.01
                or math.abs(b-ink.b)>.01 or math.abs(alpha-1)>.02 then return false end
        end
        if not shape(self._title_divider,self._root_panel,g.separator_x,8*g.es,2*g.es,24*g.es,2) then return false end
        local r,green,b = a_read_color(self._title_divider)
        return r and math.abs(r-ink.r)<=.01 and math.abs(green-ink.g)<=.01 and math.abs(b-ink.b)<=.01
    end)
    return ok and verified==true
end

if RequiredScript == REQUIRED_CONTEXT then
    local function cb_sync_start(self, assault_number)
        A._banner_clock, A._display_reminder = 0, false
        A._banner_phase = nil
        A._lull_source, A._lull_manager = nil, nil
        local ok_corner, corner = pcall(function() return self._hud_assault_corner end)
        if not ok_corner or not corner then return end
        local ok_pnr, pnr = pcall(function() return corner._point_of_no_return end)
        local ok_cas, cas = pcall(function() return corner._casing end)
        if not ok_pnr or not ok_cas or pnr or cas then return end
        S.active = true
        S.number = assault_number
        S.client_preparation = false
        A._event_manager = self
        A._event_active = true
        A._event_has_active = true
        A._event_client_preparation = false
        A._event_has_client_preparation = true
        if type(assault_number) == "number" and assault_number == assault_number
                and assault_number ~= math.huge and assault_number ~= -math.huge then
            A._event_number = assault_number
            A._event_has_number = true
        end
        if A._after_assault_active or A._after_assault_pending then
            A._after_assault_active = false
            A._after_assault_pending = false
            A._after_assault_start = nil
        end
        A:_update_presenting()
        A._data_dirty = true
    end

    local function cb_sync_end(self, result)
        local was_active = S.active == true
        local was_pnr_or_casing = false
        local ok_corner, corner = pcall(function() return self._hud_assault_corner end)
        if ok_corner and corner then
            local ok_pnr, pnr = pcall(function() return corner._point_of_no_return end)
            local ok_cas, cas = pcall(function() return corner._casing end)
            if (ok_pnr and pnr == true) or (ok_cas and cas == true) then
                was_pnr_or_casing = true
            end
        end
        S.active = false
        A._event_manager = self
        A._event_active = false
        A._event_has_active = true
        A._state.client_preparation = false
        A._event_client_preparation = false
        A._event_has_client_preparation = true
        if was_active and not was_pnr_or_casing then
            A._lull_source = A._source
            A._lull_manager = self
            if not A._after_assault_active and not A._after_assault_pending then
                A._after_assault_pending = true
            end
        else
            if not A._after_assault_active and not A._after_assault_pending then
                A._after_assault_active = false
                A._after_assault_pending = false
                A._after_assault_start = nil
            end
        end
        A:_update_presenting()
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

    local function cb_sync_anticipation_music(self)
        A._event_manager = self
        A._state.client_preparation = true
        A._event_client_preparation = true
        A._event_has_client_preparation = true
        A._state.presenting = true
        if A._after_assault_active or A._after_assault_pending then
            A._after_assault_active = false
            A._after_assault_pending = false
            A._after_assault_start = nil
        end
        A._data_dirty = true
    end

    safe_hook(HUDManager, "sync_start_assault", "KyohHUD_Assault_SyncStart", cb_sync_start)
    safe_hook(HUDManager, "sync_end_assault", "KyohHUD_Assault_SyncEnd", cb_sync_end)
    safe_hook(HUDManager, "sync_assault_number", "KyohHUD_Assault_SyncNumber", cb_sync_number)
    safe_hook(HUDManager, "sync_set_assault_mode", "KyohHUD_Assault_SyncMode", cb_sync_mode)
    safe_hook(HUDManager, "set_control_info", "KyohHUD_Assault_SetControlInfo", cb_set_control)
    safe_hook(HUDManager, "sync_start_anticipation_music", "KyohHUD_Assault_SyncAnticipation", cb_sync_anticipation_music)
end
