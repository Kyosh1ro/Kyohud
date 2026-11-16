kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end

kyohud.hud = kyohud.hud or {}

local M = kyohud.hud.mission or {}
kyohud.hud.mission = M

M._timer_text = M._timer_text
M._timer_known = M._timer_known or false
M._mounted = M._mounted or false
M._root_panel = M._root_panel
M._parent_panel = M._parent_panel
M._timer_prim = M._timer_prim
M._title_prim = M._title_prim
M._bags_prim = M._bags_prim
M._bags_label_prim = M._bags_label_prim
M._bags_label_text = M._bags_label_text
M._manager = M._manager
M._mounted_manager_id = M._mounted_manager_id
M._heist_generation = M._heist_generation or 0
M._bags_known = M._bags_known or false
M._title_text = M._title_text
M._title_needs_retry = M._title_needs_retry or false
M._snapshot_taken = M._snapshot_taken or false
M._last_retry_time = M._last_retry_time

M._gpc_snapshot = M._gpc_snapshot
M._gpc_snapshot_valid = M._gpc_snapshot_valid or false
M._gpc_generation = M._gpc_generation or 0
M._gpc_source = M._gpc_source
M._bound_gpc = M._bound_gpc

M._native_timer_text = M._native_timer_text
M._native_acquired = M._native_acquired or false
M._native_generation = M._native_generation or 0
M._native_tainted_leaf = M._native_tainted_leaf
M._render_verified = M._render_verified or false
M._render_failed = M._render_failed or false
M._layout_cache = M._layout_cache
M._cached_timer_text = M._cached_timer_text
M._cached_title_text = M._cached_title_text
M._cached_bags_text = M._cached_bags_text
M._cached_bags_label_text = M._cached_bags_label_text
M._cached_font = M._cached_font
M._cached_font_size = M._cached_font_size
M._cached_timer_visible = M._cached_timer_visible
M._cached_title_visible = M._cached_title_visible
M._cached_bags_visible = M._cached_bags_visible
M._cached_bags_label_visible = M._cached_bags_label_visible
M._trace_checked = M._trace_checked or false
M._trace_enabled = M._trace_enabled or false
M._trace_state = M._trace_state
M._trace_native_reason = M._trace_native_reason

local REQUIRED_CONTEXT = "lib/managers/hudmanagerpd2"
local LOOT_CONTEXT = "lib/managers/lootmanager"
local GPC_CONTEXT = "lib/managers/gameplaycentralmanager"
local MISSION_ROOT_NAME = "kyohud_mission_panel"
local TIMER_PRIM_NAME = "kyohud_mission_timer"
local TITLE_PRIM_NAME = "kyohud_mission_title"
local BAGS_PRIM_NAME = "kyohud_mission_bags"
local BAGS_LABEL_PRIM_NAME = "kyohud_mission_bags_label"

local CALL_OK = "ok"
local CALL_MISSING = "missing"
local CALL_ERROR = "error"

local MIN_FONT_SIZE = 12
local TIMER_COLOR = Color(242/255, 194/255, 48/255)
local TITLE_COLOR = Color(238/255, 241/255, 244/255)
local LABEL_COLOR = Color(1, 1, 1)

local TRACE_SENTINEL = "KYO_MISSION_TRACE"
local TRACE_PREFIX = "[KyoHUD][MissionTrace]"
local TRACE_LINE_CAP = 24
local OBJECTIVE_LEAF_SPECS = {
    {"objective_text", "title"},
    {"amount_text", "amount"}
}
local FRAME_LEAF_SPECS = {
    {"bg", "bg"},
    {"left_top", "framecorners"},
    {"left_bottom", "framecorners"},
    {"right_top", "framecorners"},
    {"right_bottom", "framecorners"}
}

if not M._trace_checked then
    M._trace_checked = true
    local open_ok, handle = pcall(function()
        if type(ModPath) ~= "string" then return nil end
        return io.open(ModPath .. TRACE_SENTINEL, "r")
    end)
    if open_ok and handle ~= nil then
        M._trace_enabled = true
        pcall(function()
            if type(handle) == "table" and type(handle.close) == "function" then
                handle:close()
            elseif type(handle) == "userdata" then
                io.close(handle)
            end
        end)
    end
end

local function is_valid_time_value(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    return true
end

local function is_finite_num(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    return true
end

local function format_timer_seconds(total_seconds)
    if not is_valid_time_value(total_seconds) then return nil end
    local abs_seconds = math.abs(total_seconds)
    local floored = math.floor(abs_seconds)
    local h = math.floor(floored / 3600)
    local remaining = floored - h * 3600
    local m = math.floor(remaining / 60)
    local s = remaining - m * 60
    if h > 0 then
        return string.format("%02d:%02d:%02d", h, m, s)
    else
        return string.format("%02d:%02d", m, s)
    end
end

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

local function trace_scalar(v)
    if v == nil then return "nil" end
    local kind = type(v)
    if kind == "boolean" then return v and "true" or "false" end
    if kind == "number" then
        if v ~= v then return "nan" end
        if v == math.huge then return "inf" end
        if v == -math.huge then return "-inf" end
        return string.format("%.17g", v)
    end
    return kind
end

local function trace_read(obj, method_name)
    local status, value = safe_call(obj, method_name)
    if status ~= CALL_OK then return nil end
    return value
end

local function mission_trace_line(self, reason)
    local want = self._layout_cache
    local root = panel_alive(self._root_panel) and self._root_panel or nil
    local parts = {
        TRACE_PREFIX,
        "reason=" .. tostring(reason),
        "render_failed=" .. trace_scalar(self._render_failed),
        "native_acquired=" .. trace_scalar(self._native_acquired),
        "root_visible=" .. trace_scalar(trace_read(root, "visible")),
        "root_x=" .. trace_scalar(trace_read(root, "x")),
        "root_y=" .. trace_scalar(trace_read(root, "y")),
        "root_w=" .. trace_scalar(trace_read(root, "w")),
        "root_h=" .. trace_scalar(trace_read(root, "h")),
        "want_x=" .. trace_scalar(want and want.root_x or nil),
        "want_y=" .. trace_scalar(want and want.root_y or nil),
        "want_w=" .. trace_scalar(want and want.root_w or nil),
        "want_h=" .. trace_scalar(want and want.root_h or nil),
    }
    return table.concat(parts, " ")
end

function M:_mission_trace_verdict(ok, reason)
    local result = ok == true
    if not self._trace_enabled then return result end
    local early_state = self._trace_state
    if early_state and early_state.total >= TRACE_LINE_CAP then return result end
    pcall(function()
        local state = self._trace_state
        if not state then
            state = { last_reason = nil, total = 0 }
            self._trace_state = state
        end
        local verdict_reason = result and "ok" or tostring(reason)
        local should_emit = false
        if result then
            if state.last_reason ~= nil and state.last_reason ~= "ok" then
                should_emit = true
            end
        elseif state.last_reason ~= verdict_reason then
            should_emit = true
        end
        state.last_reason = verdict_reason
        if not should_emit or state.total >= TRACE_LINE_CAP then return end
        state.total = state.total + 1
        local format_ok, line = pcall(mission_trace_line, self, verdict_reason)
        if not format_ok or type(line) ~= "string" then return end
        pcall(log, line)
    end)
    return result
end

local function get_title_fallback()
    local ok_loc, loc = pcall(function() return managers.localization end)
    if ok_loc and loc then
        local ok_text, result = pcall(function() return loc:text("ky_hud_mission_title") end)
        if ok_text and type(result) == "string" and result ~= "" then
            return result
        end
    end
    return "HEIST IN PROGRESS"
end

function M:_is_timer_enabled()
    if not self._manager then return true end
    local ok_ht, ht = pcall(function() return self._manager._hud_heist_timer end)
    if not ok_ht or not ht then return true end
    local ok_en, en = pcall(function() return ht._enabled end)
    if ok_en and en == false then return false end
    return true
end

local function measured_width(prim, text, size)
    if panel_alive(prim) then
        local ok, width = pcall(function()
            if prim:text() ~= text or math.abs(prim:font_size()-size) > 0.01 then return nil end
            local _,_,w,h = prim:text_rect()
            if is_finite_num(w) and is_finite_num(h) then return w end
        end)
        if ok and width then return math.ceil(width) + 1 end
    end
    return #text * size * 0.6
end

function M:_compute_layout(parent_w, parent_h, scale)
    local layout = kyohud.hud.layout
    if not layout then return nil end
    -- The legacy native reservation is deliberately not rescaled or repurposed.
    local region = layout.objectives_region(parent_w,parent_h)
    if not region then return nil end
    local reserve = kyohud.settings.enable_objectives ~= true
    local g = layout.mission_objectives(parent_w,parent_h,scale,true,
        kyohud.settings.enable_objectives == true,reserve)
    if not g then return nil end
    local e = g.e
    local fs = math.max(MIN_FONT_SIZE,math.floor(28*e))
    local timer_text = self._timer_text or "00:00"
    local timer_w = measured_width(self._timer_prim,timer_text,fs) + 24*e
    local label = self._bags_label_text or "BAGS"
    local count = self._bags_known and tostring(self._bags_count) or "--"
    local bags_w = math.max(64*e, measured_width(self._bags_label_prim,label,14*e)+24*e,
        measured_width(self._bags_prim,count,18*e)+24*e)
    local title = self._title_text or "HEIST IN PROGRESS"
    local fit = self._title_fit
    local title_width = #title*fs*0.6
    if fit and fit.source == title and fit.fs == fs then title_width = fit.natural_w end
    -- Intrinsic cells must not refit to an epsilon below the measured text
    -- after adding/subtracting fractional padding. Keep one logical pixel spare.
    title_width = math.ceil(title_width) + 1
    local row_w = math.min(g.w,timer_w+title_width+32*e+3*e+bags_w)
    local title_w = row_w-timer_w-3*e-bags_w
    if title_w <= 32*e or g.mission_h < fs then return nil end
    return {
        font_size=fs, e=e, root_x=g.x, root_y=g.y, root_w=row_w, root_h=g.mission_h,
        timer_bg={x=0,y=0,w=timer_w,h=g.mission_h},
        title_bg={x=timer_w,y=0,w=title_w,h=g.mission_h},
        bags_bg={x=row_w-bags_w,y=0,w=bags_w,h=g.mission_h},
        timer={x=12*e,y=0,w=timer_w-24*e,h=g.mission_h},
        title={x=timer_w+14*e,y=0,w=title_w-32*e,h=g.mission_h},
        bags_label={x=row_w-bags_w+12*e,y=3*e,w=bags_w-24*e,h=17*e},
        bags={x=row_w-bags_w+12*e,y=20*e,w=bags_w-24*e,h=24*e},
        row_y=g.y,row_h=g.mission_h,parent_w=parent_w,parent_h=parent_h
    }
end

function M:_try_acquire_native()
    if self._native_acquired then return true end
    if not self._manager then return false end
    if not self._render_verified then return false end
    if is_vr() then return false end
    if kyohud.settings.enable_mission ~= true then return false end
    local ok_ht, ht = pcall(function() return self._manager._hud_heist_timer end)
    if not ok_ht or not ht then return false end
    local ok_en, en = pcall(function() return ht._enabled end)
    if ok_en and en == false then return false end
    if not self._timer_known then return false end
    local ok_tt, tt = pcall(function() return ht._timer_text end)
    if not ok_tt or not tt then return false end
    if not panel_alive(tt) then return false end
    if self._native_timer_text and self._native_timer_text ~= tt then return false end
    if self._native_tainted_leaf == tt then return false end
    local nv = kyohud.hud.native_visibility
    if not nv then return false end
    nv._whitelist[tt] = nv._whitelist[tt] or {}
    nv._whitelist[tt].alpha = true
    local gen = self._heist_generation
    self._native_timer_text = tt
    self._native_generation = gen
    local requests = {
        { id = tt, property = "alpha", value = 0 }
    }
    local acquired = nv:acquire(self, gen, requests)
    if acquired then
        self._native_acquired = true
        return true
    end
    self._native_acquired = false
    return false
end

function M:_release_native()
    if not self._native_acquired and not self._native_timer_text then return true end
    local nv = kyohud.hud.native_visibility
    if not nv then return true end
    if self._native_timer_text and panel_alive(self._native_timer_text) then
        local ok_a, current_alpha = pcall(function() return self._native_timer_text:alpha() end)
        if ok_a and type(current_alpha) == "number" and current_alpha ~= 0 then
            self._native_tainted_leaf = self._native_timer_text
            if self._native_generation then
                nv:release(self, self._native_generation)
            end
            if nv._whitelist[self._native_timer_text] then
                nv._whitelist[self._native_timer_text].alpha = nil
                if not next(nv._whitelist[self._native_timer_text]) then
                    nv._whitelist[self._native_timer_text] = nil
                end
            end
            self._native_timer_text = nil
            self._native_acquired = false
            return true
        end
    end
    if self._native_generation then
        nv:release(self, self._native_generation)
    end
    local has_remaining = false
    if self._native_timer_text then
        for _, e in ipairs(nv._entries) do
            if e.owner == self and e.object == self._native_timer_text then
                has_remaining = true
                break
            end
        end
    end
    if has_remaining then
        self._native_acquired = false
        return false
    end
    if self._native_timer_text and nv._whitelist[self._native_timer_text] then
        nv._whitelist[self._native_timer_text].alpha = nil
        if not next(nv._whitelist[self._native_timer_text]) then
            nv._whitelist[self._native_timer_text] = nil
        end
    end
    self._native_timer_text = nil
    self._native_acquired = false
    return true
end

function M:_check_native_leaf()
    if not self._native_timer_text then
        if self._native_tainted_leaf then
            local ok_ht, ht = pcall(function() return self._manager and self._manager._hud_heist_timer end)
            if ok_ht and ht then
                local ok_tt, tt = pcall(function() return ht._timer_text end)
                if ok_tt and tt ~= self._native_tainted_leaf then
                    self._native_tainted_leaf = nil
                end
            end
        end
        return
    end
    if not self._manager then return end
    local ok_ht, ht = pcall(function() return self._manager._hud_heist_timer end)
    if not ok_ht or not ht then return end
    local ok_tt, tt = pcall(function() return ht._timer_text end)
    if not ok_tt or not tt then return end
    if tt == self._native_timer_text then return end
    self:_release_native()
    self._render_verified = false
end

local function actual_shape_matches(obj, desired)
    if not obj or not desired then return false end
    local ox_s, ox = safe_call(obj, "x")
    local oy_s, oy = safe_call(obj, "y")
    local ow_s, ow = safe_call(obj, "w")
    local oh_s, oh = safe_call(obj, "h")
    if ox_s ~= CALL_OK or oy_s ~= CALL_OK or ow_s ~= CALL_OK or oh_s ~= CALL_OK then
        return false
    end
    if not is_finite_num(ox) or not is_finite_num(oy)
        or not is_finite_num(ow) or not is_finite_num(oh) then
        return false
    end
    if not is_finite_num(desired.x) or not is_finite_num(desired.y)
        or not is_finite_num(desired.w) or not is_finite_num(desired.h) then
        return false
    end
    local tol = 0.5
    if math.abs(ox - desired.x) > tol or math.abs(oy - desired.y) > tol
        or math.abs(ow - desired.w) > tol or math.abs(oh - desired.h) > tol then
        return false
    end
    return true
end

local function ink_matches(prim, expected)
    if not panel_alive(prim) then return false end
    local ok, result = pcall(function()
        local c = prim:color()
        return math.abs(c.r-expected.r) < 0.001
            and math.abs(c.g-expected.g) < 0.001
            and math.abs(c.b-expected.b) < 0.001
    end)
    return ok and result
end

function M:_sync_inks()
    for _, item in ipairs({
        {self._timer_prim, TIMER_COLOR}, {self._title_prim, TITLE_COLOR},
        {self._bags_label_prim, LABEL_COLOR}, {self._bags_prim, LABEL_COLOR}
    }) do
        local p = item[1]
        if panel_alive(p) and not ink_matches(p, item[2]) then
            local status, alpha = safe_call(p, "alpha")
            safe_call(p, "set_color", item[2])
            if status == CALL_OK then safe_call(p, "set_alpha", alpha) end
        end
    end
end

local function bg_color_channels(prim)
    local c = prim:color()
    return c.r, c.g, c.b
end

local function bg_color_matches(prim, r, g, b)
    if not panel_alive(prim) then return false end
    local ok, cr, cg, cb = pcall(bg_color_channels, prim)
    if not ok or not is_finite_num(cr) or not is_finite_num(cg) or not is_finite_num(cb) then
        return false
    end
    return math.abs(cr - r) < 0.001
        and math.abs(cg - g) < 0.001
        and math.abs(cb - b) < 0.001
end

function M:_sync_backgrounds()
    local g = self._layout_cache
    if not g or not panel_alive(self._root_panel) then return end
    if self._background_root ~= self._root_panel then self._backgrounds = {}; self._background_root = self._root_panel end
    self._backgrounds = self._backgrounds or {}
    for _, key in ipairs({"timer", "title", "bags"}) do
        local shape = g[key .. "_bg"]
        local p = self._backgrounds[key]
        local expected_r = key == "timer" and 0 or 11/255
        local expected_g = key == "timer" and 0 or 13/255
        local expected_b = key == "timer" and 0 or 17/255
        local alpha = key == "timer" and 0.86 or 0.80
        local visible = not self._render_failed and (key ~= "timer" or (self._timer_known and self:_is_timer_enabled()))
        if not panel_alive(p) then
            local status, created = safe_call(self._root_panel, "rect", {
                name = "mission_" .. key .. "_bg", x = shape.x, y = shape.y,
                w = shape.w, h = shape.h, color = Color(expected_r, expected_g, expected_b),
                alpha = alpha, visible = visible, layer = -1
            })
            if status == CALL_OK then p = created; self._backgrounds[key] = p end
        end
        if panel_alive(p) then
            if not actual_shape_matches(p, shape) then safe_call(p, "set_shape", shape.x, shape.y, shape.w, shape.h) end
            if not bg_color_matches(p, expected_r, expected_g, expected_b) then
                safe_call(p, "set_color", Color(expected_r, expected_g, expected_b))
            end
            local alpha_status, actual_alpha = safe_call(p, "alpha")
            if alpha_status ~= CALL_OK or not is_finite_num(actual_alpha)
                or math.abs(actual_alpha - alpha) >= 0.001 then
                safe_call(p, "set_alpha", alpha)
            end
            local visible_status, actual_visible = safe_call(p, "visible")
            if visible_status ~= CALL_OK or actual_visible ~= (visible == true) then
                safe_call(p, "set_visible", visible == true)
            end
        end
    end
end

function M:_verify_backgrounds()
    local g = self._layout_cache
    if not g then return false end
    for _, key in ipairs({"timer", "title", "bags"}) do
        local p = self._backgrounds and self._backgrounds[key]
        if not panel_alive(p) or not actual_shape_matches(p, g[key .. "_bg"]) then return false end
        local ok, valid = pcall(function()
            local c = p:color()
            local expected = key == "timer" and 0 or 1
            local visible = not self._render_failed and (key ~= "timer" or (self._timer_known and self:_is_timer_enabled()))
            return math.abs(c.r - expected * 11/255) < 0.001
                and math.abs(c.g - expected * 13/255) < 0.001
                and math.abs(c.b - expected * 17/255) < 0.001
                and math.abs(p:alpha() - (key == "timer" and 0.86 or 0.80)) < 0.001
                and p:visible() == (visible == true)
        end)
        if not ok or not valid then return false end
    end
    return true
end

function M:_verify_labels()
    local g = self._layout_cache
    if not g then return false end
    local fit = self._title_fit
    local labels = {
        {self._title_prim, g.title, fit and fit.text, g.font_size, true},
        {self._bags_label_prim, g.bags_label, self._bags_label_text, 14*g.e, true},
        {self._bags_prim, g.bags, self._bags_known and tostring(self._bags_count) or "--", 18*g.e, true}
    }
    if self._timer_known and self:_is_timer_enabled() then
        labels[#labels+1] = {self._timer_prim,g.timer,self._timer_text,g.font_size,true}
    end
    if not ink_matches(self._title_prim, TITLE_COLOR)
        or not ink_matches(self._bags_label_prim, LABEL_COLOR)
        or not ink_matches(self._bags_prim, LABEL_COLOR) then return false end
    if self._timer_known and self:_is_timer_enabled()
        and not ink_matches(self._timer_prim, TIMER_COLOR) then return false end
    if not fit or fit.source ~= (self._title_text or "") or fit.w ~= g.title.w or fit.fs ~= g.font_size then return false end
    for _, item in ipairs(labels) do
        local p, shape, text, fs = item[1],item[2],item[3],item[4]
        if not panel_alive(p) or not actual_shape_matches(p,shape) then return false end
        local ok, valid = pcall(function()
            local _,_,w,h = p:text_rect()
            return p:text() == text and p:visible() == (not self._render_failed)
                and math.abs(p:font_size()-fs) <= 0.5
                and is_finite_num(w) and is_finite_num(h)
                and w <= shape.w+0.5 and h <= shape.h+0.5
        end)
        if not ok or not valid then return false end
    end
    return true
end

local function trace_native_reject(self, diag, failure, role, stage, depth)
    if not diag then return end
    local reason = "native:" .. tostring(failure or "reject")
    if role then reason = reason .. ":" .. role end
    if stage then reason = reason .. ":" .. stage end
    if depth ~= nil then reason = reason .. "@" .. tostring(depth) end
    self._trace_native_reason = reason
end

local function reject_native(self, diag, failure, role, stage, depth)
    trace_native_reject(self, diag, failure, role, stage, depth)
    return true
end

local function reject_bounds(self, diag)
    if not diag then return true end
    return reject_native(self, diag, diag.failure or "bounds", diag.role,
        diag.stage, diag.depth)
end

-- Native objective observations are read-only and bounded to known leaves.
-- During a release handshake, observe the values about to be restored, not
-- merely the still-masked values. This prevents a one-frame overlap.
local function objective_node_state(node, restoring, owner, entries, diag, common)
    if diag then diag.stage = "visible" end
    local visible = node:visible()
    if diag then diag.stage = "alpha" end
    local alpha = node:alpha()
    if restoring and owner and entries then
        for _, entry in ipairs(entries) do
            if entry.owner == owner and entry.generation == owner._native_generation and entry.object == node then
                if entry.property == "visible" then visible = entry.old_value end
                if entry.property == "alpha" then alpha = entry.old_value end
            end
        end
    end
    if diag then diag.stage = "x" end
    local x = node:x()
    if diag then diag.stage = "y" end
    local y = node:y()
    if diag then diag.stage = "w" end
    local w = node:w()
    if diag then diag.stage = "h" end
    local h = node:h()
    if diag then diag.stage = "parent" end
    local parent = nil
    if node ~= common then
        parent = node:parent()
    end
    return visible, alpha, x, y, w, h, parent
end

local function objective_bounds(node, restoring, owner, entries, diag, common)
    local x, y, w, h = 0, 0, nil, nil
    local shown = true
    for depth = 1, 16 do
        if not panel_alive(node) then
            if diag then diag.failure = "missing"; diag.stage = nil; diag.depth = depth end
            return nil
        end
        local ok, visible, alpha, nx, ny, nw, nh, parent =
            pcall(objective_node_state, node, restoring, owner, entries, diag, common)
        if not ok then
            if diag then diag.failure = "read_error"; diag.depth = depth end
            return nil
        end
        if type(visible) ~= "boolean" then
            if diag then diag.failure = "visible_type"; diag.stage = nil; diag.depth = depth end
            return nil
        end
        if not is_finite_num(alpha) then
            if diag then diag.failure = "alpha_invalid"; diag.stage = nil; diag.depth = depth end
            return nil
        end
        if not is_finite_num(nx) then
            if diag then diag.failure = "x_invalid"; diag.stage = nil; diag.depth = depth end
            return nil
        end
        if not is_finite_num(ny) then
            if diag then diag.failure = "y_invalid"; diag.stage = nil; diag.depth = depth end
            return nil
        end
        if not is_finite_num(nw) then
            if diag then diag.failure = "w_invalid"; diag.stage = nil; diag.depth = depth end
            return nil
        end
        if not is_finite_num(nh) then
            if diag then diag.failure = "h_invalid"; diag.stage = nil; diag.depth = depth end
            return nil
        end
        if nw < 0 or nh < 0 then
            if diag then diag.failure = "negative_size"; diag.stage = nil; diag.depth = depth end
            return nil
        end
        if not visible or alpha <= 0 or nw == 0 or nh == 0 then shown = false end
        x, y = x + nx, y + ny
        if not is_finite_num(x) then
            if diag then diag.failure = "coordinate_overflow_x"; diag.stage = nil; diag.depth = depth end
            return nil
        end
        if not is_finite_num(y) then
            if diag then diag.failure = "coordinate_overflow_y"; diag.stage = nil; diag.depth = depth end
            return nil
        end
        if depth == 1 then w, h = nw, nh end
        if node == common then return x, y, w, h, node, shown end
        if parent == nil then
            if diag then diag.failure = "root_mismatch"; diag.stage = nil; diag.depth = depth end
            return nil
        end
        node = parent
    end
    if diag then diag.failure = "depth_limit"; diag.stage = nil; diag.depth = 16 end
    return nil
end

local function observed_bounds(node, restoring, owner, entries, diag, role, common)
    if diag then
        diag.role = role
        diag.stage = nil
        diag.depth = nil
        diag.failure = nil
    end
    return objective_bounds(node, restoring, owner, entries, diag, common)
end

local function objective_source(manager)
    local source = manager and manager._hud_objectives
    if not source then return nil end
    return source, source._hud_panel, source._bg_box,
        kyohud.hud.runtime and kyohud.hud.runtime._parent_panel or nil
end

function M:_native_objectives_conflict(restoring)
    if kyohud.settings.enable_objectives ~= true then return false end
    local diag = nil
    local trace_state = self._trace_state
    if self._trace_enabled and not (trace_state and trace_state.total >= TRACE_LINE_CAP) then
        diag = { role = nil, stage = nil, depth = nil, failure = nil }
        self._trace_native_reason = nil
    end
    local ok, source, hud_panel, box, common = pcall(objective_source, self._manager)
    if not ok then return reject_native(self, diag, "source_read_error") end
    if not source then return false end
    if not common or not panel_alive(common) then
        return reject_native(self, diag, "root_mismatch")
    end
    local owner = kyohud.hud.objectives
    local nv = kyohud.hud.native_visibility
    local entries = nv and nv._entries
    local _, _, _, _, _, hud_shown = observed_bounds(hud_panel, restoring, owner, entries, diag, "hud", common)
    if hud_shown == false then return false end
    if hud_shown == nil then return reject_bounds(self, diag) end
    local status, panel = safe_call(hud_panel, "child", "objectives_panel")
    if status ~= CALL_OK or not panel then
        return reject_native(self, diag,
            status == CALL_ERROR and "leaf_read_error" or "leaf_missing", "panel")
    end
    local _, _, _, _, _, panel_shown = observed_bounds(panel, restoring, owner, entries, diag, "panel", common)
    if panel_shown == false then return false end
    if panel_shown == nil then return reject_bounds(self, diag) end
    local mx, my, mw, mh = observed_bounds(self._root_panel, nil, nil, nil, diag, "missionroot", common)
    if mx == nil then return reject_bounds(self, diag) end
    for _, spec in ipairs(OBJECTIVE_LEAF_SPECS) do
        local name, role = spec[1], spec[2]
        local leaf_status, leaf = safe_call(panel, "child", name)
        if leaf_status ~= CALL_OK or not leaf then
            return reject_native(self, diag,
                leaf_status == CALL_ERROR and "leaf_read_error" or "leaf_missing", role)
        end
        local x, y, w, h, root, shown = observed_bounds(leaf, restoring, owner, entries, diag, role, common)
        if shown == nil then return reject_bounds(self, diag) end
        if shown then
            local text_status, text = safe_call(leaf, "text")
            if text_status ~= CALL_OK or type(text) ~= "string" then
                return reject_native(self, diag,
                    text_status == CALL_ERROR and "text_read_error" or "text_type", role)
            end
            if text ~= "" then
                if root ~= common then return reject_native(self, diag, "root_mismatch", role) end
                if x < mx + mw and mx < x + w and y < my + mh and my < y + h then
                    return reject_native(self, diag, "overlap", role)
                end
            end
        end
    end
    -- An opening/closing frame can remain after its text has disappeared.
    if not box then return reject_native(self, diag, "frame_box_missing", "frame") end
    local x, y, w, h, root, shown = observed_bounds(box, restoring, owner, entries, diag, "frame", common)
    if shown == nil then return reject_bounds(self, diag) end
    if shown then
        for _, spec in ipairs(FRAME_LEAF_SPECS) do
            local name, role = spec[1], spec[2]
            local leaf_status, leaf = safe_call(box, "child", name)
            if leaf_status ~= CALL_OK or not leaf then
                return reject_native(self, diag,
                    leaf_status == CALL_ERROR and "leaf_read_error" or "leaf_missing", role)
            end
            local _, _, _, _, _, leaf_shown = observed_bounds(leaf, restoring, owner, entries, diag, role, common)
            if leaf_shown == nil then return reject_bounds(self, diag) end
            if leaf_shown and (root ~= common
                or (x < mx + mw and mx < x + w and y < my + mh and my < y + h)) then
                return reject_native(self, diag,
                    root ~= common and "root_mismatch" or "overlap", role)
            end
        end
    end
    return false
end

function M:_verify_render(restoring_objectives)
    if not self._layout_cache then
        self._render_verified = false
        return self:_mission_trace_verdict(false, "layout_missing")
    end
    if not self:_verify_backgrounds() then
        self._render_verified = false
        return self:_mission_trace_verdict(false, "backgrounds")
    end
    if not self:_verify_labels() then
        self._render_verified = false
        return self:_mission_trace_verdict(false, "labels")
    end
    local root_geom = self._layout_cache
    if not panel_alive(self._root_panel) then
        self._render_verified = false
        return self:_mission_trace_verdict(false, "root_missing")
    end
    local visible_status, root_visible = safe_call(self._root_panel, "visible")
    if visible_status ~= CALL_OK or root_visible ~= true then
        self._render_verified = false
        return self:_mission_trace_verdict(false, "root_visible")
    end
    if not panel_alive(self._root_panel) or not actual_shape_matches(self._root_panel, {
        x=root_geom.root_x, y=root_geom.root_y, w=root_geom.root_w, h=root_geom.root_h
    }) then
        self._render_verified = false
        return self:_mission_trace_verdict(false, "root_shape")
    end
    local timer_enabled = self:_is_timer_enabled()
    if not self._timer_known or not timer_enabled then
        if self:_native_objectives_conflict(restoring_objectives) then
            self._render_verified = false
            return self:_mission_trace_verdict(false,
                self._trace_native_reason or "native_conflict")
        end
        self._render_verified = true
        return self:_mission_trace_verdict(true, "ok")
    end
    if not self._timer_prim or not panel_alive(self._timer_prim) then
        self._render_verified = false
        return self:_mission_trace_verdict(false, "timer_missing")
    end
    local geom = self._layout_cache
    if geom.timer.w <= 0 or geom.timer.h <= 0 or geom.font_size <= 0 then
        self._render_verified = false
        return self:_mission_trace_verdict(false, "timer_geometry")
    end
    if self._root_panel and panel_alive(self._root_panel) then
        if not actual_shape_matches(self._root_panel, {
            x = geom.root_x, y = geom.root_y,
            w = geom.root_w, h = geom.root_h
        }) then
            self._render_verified = false
            return self:_mission_trace_verdict(false, "root_shape")
        end
    end
    if not actual_shape_matches(self._timer_prim, geom.timer) then
        self._render_verified = false
        return self:_mission_trace_verdict(false, "timer_shape")
    end
    local ok_text, text = pcall(function() return self._timer_prim:text() end)
    if not ok_text or type(text) ~= "string" then
        self._render_verified = false
        return self:_mission_trace_verdict(false, "timer_text_read")
    end
    local expected = self._timer_text or ""
    if text ~= expected then
        self._render_verified = false
        return self:_mission_trace_verdict(false, "timer_text")
    end
    local ok_vis, vis = pcall(function() return self._timer_prim:visible() end)
    if not ok_vis or vis ~= true then
        self._render_verified = false
        return self:_mission_trace_verdict(false, "timer_visible")
    end
    local ok_fs, fs = pcall(function() return self._timer_prim:font_size() end)
    if not ok_fs or type(fs) ~= "number" or fs <= 0 then
        self._render_verified = false
        return self:_mission_trace_verdict(false, "timer_font_size")
    end
    if math.abs(fs - geom.font_size) > 0.5 then
        self._render_verified = false
        return self:_mission_trace_verdict(false, "timer_font_size")
    end
    if self._title_prim and panel_alive(self._title_prim) then
        if not actual_shape_matches(self._title_prim, geom.title) then
            self._render_verified = false
            return self:_mission_trace_verdict(false, "title_shape")
        end
    end
    if self._bags_prim and panel_alive(self._bags_prim) then
        if not actual_shape_matches(self._bags_prim, geom.bags) then
            self._render_verified = false
            return self:_mission_trace_verdict(false, "bags_shape")
        end
    end
    if self._bags_label_prim and panel_alive(self._bags_label_prim) then
        if not actual_shape_matches(self._bags_label_prim, geom.bags_label) then
            self._render_verified = false
            return self:_mission_trace_verdict(false, "bags_label_shape")
        end
    end
    if self:_native_objectives_conflict(restoring_objectives) then
        self._render_verified = false
        return self:_mission_trace_verdict(false,
            self._trace_native_reason or "native_conflict")
    end
    self._render_verified = true
    return self:_mission_trace_verdict(true, "ok")
end

function M:_handle_render_failure()
    self._render_failed = true
    self._render_verified = false
    if panel_alive(self._root_panel) then safe_call(self._root_panel, "set_visible", false) end
    self._layout_cache = nil
    if self._backgrounds then
        for _, p in pairs(self._backgrounds) do
            if panel_alive(p) then safe_call(p, "set_visible", false) end
        end
    end
    if self._timer_prim and panel_alive(self._timer_prim) then
        safe_call(self._timer_prim, "set_visible", false)
        self._cached_timer_visible = false
    end
    if self._title_prim and panel_alive(self._title_prim) then
        safe_call(self._title_prim, "set_visible", false)
        self._cached_title_visible = false
    end
    if self._bags_prim and panel_alive(self._bags_prim) then
        safe_call(self._bags_prim, "set_visible", false)
        self._cached_bags_visible = false
    end
    if self._bags_label_prim and panel_alive(self._bags_label_prim) then
        safe_call(self._bags_label_prim, "set_visible", false)
        self._cached_bags_label_visible = false
    end
    self:_release_native()
end

function M:_recover_primitives()
    if not self._render_failed then return end
    self._render_failed = false
    self:_sync_primitives()
end

local function capture_timer(mgr, is_realfeed)
    if not mgr then return end
    local ok_ht, ht = pcall(function() return mgr._hud_heist_timer end)
    if not ok_ht or ht == nil then return end
    local ok_en, enabled = pcall(function() return ht._enabled end)
    if ok_en and enabled == false then
        M._timer_known = false
        M._timer_text = nil
        if M._timer_prim and panel_alive(M._timer_prim) then
            safe_call(M._timer_prim, "set_visible", false)
            M._cached_timer_visible = false
        end
        return
    end
    local ok_tt, tt = pcall(function() return ht._timer_text end)
    if not ok_tt or tt == nil then return end
    local ok_text, text = pcall(function() return tt:text() end)
    if not ok_text or type(text) ~= "string" then return end
    if is_realfeed then
        M._timer_text = text
        M._timer_known = true
        M._gpc_snapshot_valid = false
        M._gpc_snapshot = nil
        return
    end
    local gpc_ok, gpc = pcall(function() return managers.game_play_central end)
    if M._gpc_snapshot_valid and M._gpc_snapshot ~= nil
        and gpc_ok and gpc == M._gpc_source then
        local formatted = format_timer_seconds(M._gpc_snapshot)
        if formatted then
            M._timer_text = formatted
            M._timer_known = true
            return
        end
    end
    M._timer_text = text
    M._timer_known = true
end

local function get_runtime_root()
    local rt = kyohud.hud.runtime
    if not rt then return nil end
    if not rt._mounted then return nil end
    local root = rt._root_panel
    if not root or not panel_alive(root) then return nil end
    return root
end

function M:_get_font()
    local ok_td, td = pcall(function() return tweak_data end)
    if not ok_td or not td then return nil end
    local ok_hud, hud = pcall(function() return td.hud end)
    if not ok_hud or not hud then return nil end
    local ok_font, f = pcall(function() return hud.medium_font_noshadow end)
    if not ok_font or type(f) ~= "string" or f == "" then return nil end
    return f
end

function M:_resolve_title()
    local ok_job, job = pcall(function() return managers.job end)
    if not ok_job or not job then return nil end
    local ok_clid, level_id = pcall(function() return job:current_level_id() end)
    if not ok_clid or type(level_id) ~= "string" or level_id == "" then return nil end
    local ok_td, td = pcall(function() return tweak_data end)
    if not ok_td or not td then return nil end
    local ok_levels, levels = pcall(function() return td.levels end)
    if not ok_levels or not levels then return nil end
    local ok_level, level = pcall(function() return levels[level_id] end)
    if not ok_level or type(level) ~= "table" then return nil end
    local ok_nid, name_id = pcall(function() return level.name_id end)
    if not ok_nid or type(name_id) ~= "string" or name_id == "" then return nil end
    local ok_loc, loc = pcall(function() return managers.localization end)
    if not ok_loc or not loc then return nil end
    local ok_text, result = pcall(function() return loc:text(name_id) end)
    if not ok_text or type(result) ~= "string" or result == "" then return nil end
    return result
end

function M:_resolve_bags()
    local ok_lm, lm = pcall(function() return managers.loot end)
    if not ok_lm or not lm then
        self._bags_known = false
        self._bags_count = nil
        return nil
    end
    local ok_get, getter = pcall(function() return lm.get_secured_bags_amount end)
    if not ok_get or type(getter) ~= "function" then
        self._bags_known = false
        self._bags_count = nil
        return nil
    end
    local ok_call, amount = pcall(lm.get_secured_bags_amount, lm, false)
    if not ok_call then
        self._bags_known = false
        self._bags_count = nil
        return nil
    end
    if type(amount) ~= "number" or amount ~= amount or amount < 0 or amount == math.huge or math.floor(amount) ~= amount then
        self._bags_known = false
        self._bags_count = nil
        return nil
    end
    self._bags_known = true
    self._bags_count = amount
    return amount
end

function M:_update_title_display()
    local resolved = self:_resolve_title()
    if resolved then
        self._title_text = resolved
        self._title_needs_retry = false
    elseif not self._snapshot_taken then
        self._title_text = get_title_fallback()
        self._title_needs_retry = true
    end
end

function M:_ensure_timer_prim()
    if self._timer_prim and panel_alive(self._timer_prim) then return end
    if not self._root_panel or not panel_alive(self._root_panel) then return end
    if not self._timer_known then return end
    local font = self:_get_font()
    if not font then return end
    if not self._layout_cache then return end
    local geom = self._layout_cache.timer
    local timer_enabled = self:_is_timer_enabled()
    local should_show = self._timer_known and timer_enabled
    local opts = {
        name = TIMER_PRIM_NAME,
        text = self._timer_text or "",
        font = "fonts/font_large_mf",
        font_size = self._layout_cache.font_size,
        color = TIMER_COLOR,
        x = geom.x,
        y = geom.y,
        w = geom.w,
        h = geom.h,
        align = "left",
        vertical = "center",
        wrap = false,
        word_wrap = false,
    }
    local status, prim = safe_call(self._root_panel, "text", opts)
    if status == CALL_OK and prim then
        self._timer_prim = prim
        self._cached_timer_text = self._timer_text or ""
        self._cached_font = font
        self._cached_font_size = self._layout_cache.font_size
        if not should_show then
            safe_call(prim, "set_visible", false)
            self._cached_timer_visible = false
        else
            self._cached_timer_visible = true
        end
    end
end

function M:_ensure_title_prim()
    if self._title_prim and panel_alive(self._title_prim) then return end
    if not self._root_panel or not panel_alive(self._root_panel) then return end
    if not self._title_text then return end
    local font = self:_get_font()
    if not font then return end
    if not self._layout_cache then return end
    local geom = self._layout_cache.title
    local opts = {
        name = TITLE_PRIM_NAME,
        text = self._title_text,
        font = font,
        font_size = self._layout_cache.font_size,
        color = TITLE_COLOR,
        x = geom.x,
        y = geom.y,
        w = geom.w,
        h = geom.h,
        align = "left",
        vertical = "center",
        wrap = false,
        word_wrap = false,
    }
    local status, prim = safe_call(self._root_panel, "text", opts)
    if status == CALL_OK and prim then
        self._title_prim = prim
        self._cached_title_text = self._title_text or ""
        self._cached_title_visible = true
    end
end

function M:_ensure_bags_prim()
    if self._bags_prim and panel_alive(self._bags_prim) then return end
    if not self._root_panel or not panel_alive(self._root_panel) then return end
    local font = self:_get_font()
    if not font then return end
    if not self._layout_cache then return end
    local geom = self._layout_cache.bags
    local opts = {
        name = BAGS_PRIM_NAME,
        text = self._bags_known and tostring(self._bags_count) or "--",
        font = font,
        font_size = 18 * self._layout_cache.e,
        color = Color(1, 1, 1, 1),
        x = geom.x,
        y = geom.y,
        w = geom.w,
        h = geom.h,
        align = "right",
        vertical = "center",
        wrap = false,
        word_wrap = false,
    }
    local status, prim = safe_call(self._root_panel, "text", opts)
    if status == CALL_OK and prim then
        self._bags_prim = prim
        self._cached_bags_text = self._bags_known and tostring(self._bags_count) or "--"
        self._cached_bags_visible = true
    end
end

function M:_resolve_bags_label()
    local ok_loc, loc = pcall(function() return managers.localization end)
    if ok_loc and loc then
        local ok_text, result = pcall(function() return loc:text("ky_hud_mission_bags") end)
        if ok_text and type(result) == "string" and result ~= "" then
            return result
        end
    end
    return "BAGS"
end

function M:_ensure_bags_label_prim()
    if self._bags_label_prim and panel_alive(self._bags_label_prim) then return end
    if not self._root_panel or not panel_alive(self._root_panel) then return end
    local font = self:_get_font()
    if not font then return end
    if not self._layout_cache then return end
    if not self._bags_label_text then
        self._bags_label_text = self:_resolve_bags_label()
    end
    local geom = self._layout_cache.bags_label
    local opts = {
        name = BAGS_LABEL_PRIM_NAME,
        text = self._bags_label_text,
        font = font,
        font_size = 14 * self._layout_cache.e,
        color = Color(1, 1, 1, 1),
        x = geom.x,
        y = geom.y,
        w = geom.w,
        h = geom.h,
        align = "right",
        vertical = "top",
        wrap = false,
        word_wrap = false,
    }
    local status, prim = safe_call(self._root_panel, "text", opts)
    if status == CALL_OK and prim then
        self._bags_label_prim = prim
        self._cached_bags_label_text = self._bags_label_text or ""
        self._cached_bags_label_visible = true
    end
end

function M:_ensure_primitives()
    self:_update_layout()
    self:_ensure_timer_prim()
    self:_ensure_title_prim()
    self:_ensure_bags_label_prim()
    self:_ensure_bags_prim()
    self:_sync_primitives()
end

function M:_sync_timer_prim()
    if not self._timer_prim then return end
    if not panel_alive(self._timer_prim) then return end
    local text = self._timer_text or ""
    local read_status, actual_text = safe_call(self._timer_prim, "text")
    if read_status ~= CALL_OK or actual_text ~= text then
        local status, _ = safe_call(self._timer_prim, "set_text", text)
        if status == CALL_OK then
            local ok_rb, rb = pcall(function() return self._timer_prim:text() end)
            if ok_rb and rb == text then
                self._cached_timer_text = text
            end
        end
    end
    local timer_enabled = self:_is_timer_enabled()
    local should_show = self._timer_known and timer_enabled and not self._render_failed
    if should_show ~= self._cached_timer_visible then
        local status, _ = safe_call(self._timer_prim, "set_visible", should_show)
        if status == CALL_OK then
            local ok_rb, rb = pcall(function() return self._timer_prim:visible() end)
            if ok_rb and rb == should_show then
                self._cached_timer_visible = should_show
            end
        end
    end
end

function M:_sync_title_prim()
    if not self._title_prim then return end
    if not panel_alive(self._title_prim) then return end
    local geom = self._layout_cache
    if not geom then return end
    local source = self._title_text or ""
    local fit = self._title_fit
    if not fit or fit.prim ~= self._title_prim or fit.source ~= source or fit.w ~= geom.title.w or fit.fs ~= geom.font_size then
        local p = self._title_prim
        safe_call(p, "set_text", source)
        local ok, _, _, w, h = pcall(function() return p:text_rect() end)
        if not ok or not is_finite_num(w) or not is_finite_num(h) then self._title_fit = nil; return end
        local text = source
        if w > geom.title.w then
            local ends = {0}
            for pos in source:gmatch("()[%z\1-\127\194-\244][\128-\191]*") do
                if pos > 1 then ends[#ends+1] = pos-1 end
            end
            ends[#ends+1] = #source
            local lo, hi, best = 1, #ends, ""
            while lo <= hi do
                local mid = math.floor((lo+hi)/2)
                local candidate = source:sub(1, ends[mid]) .. "..."
                safe_call(p, "set_text", candidate)
                local status, _, _, mw, mh = pcall(function() return p:text_rect() end)
                if status and is_finite_num(mw) and is_finite_num(mh)
                    and mw <= geom.title.w and mh <= geom.title.h then
                    best = candidate; lo = mid+1
                else hi = mid-1 end
            end
            text = best
        end
        self._title_fit = {prim=p, source=source, w=geom.title.w, fs=geom.font_size, natural_w=w, text=text}
        fit = self._title_fit
        safe_call(p, "set_text", text)
        self._cached_title_text = text
    end
    local text = fit.text
    local read_status, actual_text = safe_call(self._title_prim, "text")
    if read_status ~= CALL_OK or actual_text ~= text then
        local status, _ = safe_call(self._title_prim, "set_text", text)
        if status == CALL_OK then
            local ok_rb, rb = pcall(function() return self._title_prim:text() end)
            if ok_rb and rb == text then
                self._cached_title_text = text
            end
        end
    end
    local should_show = not self._render_failed
    if should_show ~= self._cached_title_visible then
        local status, _ = safe_call(self._title_prim, "set_visible", should_show)
        if status == CALL_OK then
            local ok_rb, rb = pcall(function() return self._title_prim:visible() end)
            if ok_rb and rb == should_show then
                self._cached_title_visible = should_show
            end
        end
    end
end

function M:_sync_bags_prim()
    if not self._bags_prim then return end
    if not panel_alive(self._bags_prim) then return end
    local text = self._bags_known and tostring(self._bags_count) or "--"
    local read_status, actual_text = safe_call(self._bags_prim, "text")
    if read_status ~= CALL_OK or actual_text ~= text then
        local status, _ = safe_call(self._bags_prim, "set_text", text)
        if status == CALL_OK then
            local ok_rb, rb = pcall(function() return self._bags_prim:text() end)
            if ok_rb and rb == text then
                self._cached_bags_text = text
            end
        end
    end
    local should_show = not self._render_failed
    if should_show ~= self._cached_bags_visible then
        local status, _ = safe_call(self._bags_prim, "set_visible", should_show)
        if status == CALL_OK then
            local ok_rb, rb = pcall(function() return self._bags_prim:visible() end)
            if ok_rb and rb == should_show then
                self._cached_bags_visible = should_show
            end
        end
    end
end

function M:_sync_bags_label_prim()
    if not self._bags_label_prim then return end
    if not panel_alive(self._bags_label_prim) then return end
    if not self._bags_label_text then
        self._bags_label_text = self:_resolve_bags_label()
    end
    local text = self._bags_label_text
    local read_status, actual_text = safe_call(self._bags_label_prim, "text")
    if read_status ~= CALL_OK or actual_text ~= text then
        local status, _ = safe_call(self._bags_label_prim, "set_text", text)
        if status == CALL_OK then
            local ok_rb, rb = pcall(function() return self._bags_label_prim:text() end)
            if ok_rb and rb == text then
                self._cached_bags_label_text = text
            end
        end
    end
    local should_show = not self._render_failed
    if should_show ~= self._cached_bags_label_visible then
        local status, _ = safe_call(self._bags_label_prim, "set_visible", should_show)
        if status == CALL_OK then
            local ok_rb, rb = pcall(function() return self._bags_label_prim:visible() end)
            if ok_rb and rb == should_show then
                self._cached_bags_label_visible = should_show
            end
        end
    end
end

function M:_sync_primitives()
    if not self._render_failed and panel_alive(self._root_panel) then
        local status, visible = safe_call(self._root_panel, "visible")
        if status ~= CALL_OK or visible ~= true then safe_call(self._root_panel, "set_visible", true) end
    end
    self:_sync_timer_prim()
    self:_sync_title_prim()
    self:_sync_bags_label_prim()
    self:_sync_bags_prim()
    self:_update_layout()
    self:_sync_title_prim()
    self:_sync_backgrounds()
    self:_sync_inks()
end

function M:_take_snapshot(mgr)
    capture_timer(mgr or self._manager)
    self:_update_title_display()
    self:_resolve_bags()
    self._snapshot_taken = true
end

function M:_reset_heist_state()
    self._timer_text = nil
    self._timer_known = false
    self._title_text = nil
    self._title_needs_retry = false
    self._bags_count = nil
    self._bags_known = false
    self._snapshot_taken = false
    self._render_failed = false
    self._render_verified = false
    self._gpc_snapshot = nil
    self._gpc_snapshot_valid = false
    self._gpc_source = nil
    self._native_tainted_leaf = nil
end

function M:_capture_gpc_snapshot(seconds)
    if not is_valid_time_value(seconds) then return end
    self._gpc_snapshot = seconds
    self._gpc_snapshot_valid = true
    local formatted = format_timer_seconds(seconds)
    if formatted then
        self._timer_text = formatted
        self._timer_known = true
    end
end

function M:_update_gpc_display()
    if not self._gpc_snapshot_valid or self._gpc_snapshot == nil then return end
    local formatted = format_timer_seconds(self._gpc_snapshot)
    if formatted then
        self._timer_text = formatted
        self._timer_known = true
    end
end

function M:_update_layout()
    if not self._root_panel or not panel_alive(self._root_panel) then return end
    if not self._parent_panel or not panel_alive(self._parent_panel) then return end
    local pw_s, pw = safe_call(self._parent_panel, "w")
    local ph_s, ph = safe_call(self._parent_panel, "h")
    if pw_s ~= CALL_OK or ph_s ~= CALL_OK then return end
    if not is_finite_num(pw) or not is_finite_num(ph) then return end
    if pw <= 0 or ph <= 0 then return end
    local scale = kyohud.settings.hud_scale or 1
    local new_layout = self:_compute_layout(pw, ph, scale)
    if not new_layout then
        self._layout_cache = nil
        return
    end
    local changed = not self._layout_cache or
        self._layout_cache.root_x ~= new_layout.root_x or
        self._layout_cache.root_y ~= new_layout.root_y or
        self._layout_cache.root_w ~= new_layout.root_w or
        self._layout_cache.root_h ~= new_layout.root_h or
        self._layout_cache.font_size ~= new_layout.font_size or not self:_verify_labels()
    if not changed then return end
    local rs = safe_call(self._root_panel, "set_shape", new_layout.root_x, new_layout.root_y, new_layout.root_w, new_layout.root_h)
    if rs ~= CALL_OK then
        self._layout_cache = nil
        return
    end
    if self._timer_prim and panel_alive(self._timer_prim) then
        safe_call(self._timer_prim, "set_shape", new_layout.timer.x, new_layout.timer.y, new_layout.timer.w, new_layout.timer.h)
        safe_call(self._timer_prim, "set_font_size", new_layout.font_size)
    end
    if self._title_prim and panel_alive(self._title_prim) then
        safe_call(self._title_prim, "set_shape", new_layout.title.x, new_layout.title.y, new_layout.title.w, new_layout.title.h)
        safe_call(self._title_prim, "set_font_size", new_layout.font_size)
    end
    if self._bags_label_prim and panel_alive(self._bags_label_prim) then
        safe_call(self._bags_label_prim, "set_shape", new_layout.bags_label.x, new_layout.bags_label.y, new_layout.bags_label.w, new_layout.bags_label.h)
        safe_call(self._bags_label_prim, "set_font_size", 14 * new_layout.e)
    end
    if self._bags_prim and panel_alive(self._bags_prim) then
        safe_call(self._bags_prim, "set_shape", new_layout.bags.x, new_layout.bags.y, new_layout.bags.w, new_layout.bags.h)
        safe_call(self._bags_prim, "set_font_size", 18 * new_layout.e)
    end
    self._cached_font_size = new_layout.font_size
    self._layout_cache = new_layout
end

function M:mount(manager)
    if kyohud.settings.enable_mission ~= true then return end
    if is_vr() then return end
    local mgr = manager or self._manager
    if not mgr then return end
    local gpc_ok, gpc = pcall(function() return managers.game_play_central end)
    if gpc_ok and M._gpc_source and M._gpc_source ~= gpc then
        M._gpc_snapshot = nil
        M._gpc_snapshot_valid = false
        M._gpc_source = nil
    end
    self._manager = mgr
    if gpc_ok and gpc then
        self._bound_gpc = gpc
    end

    local parent = get_runtime_root()
    if not parent then return end

    if self._mounted and self._root_panel and panel_alive(self._root_panel) then
        if self._parent_panel == parent then
            self:_update_layout()
            return
        end
        local removed = self:unmount()
        if not removed then return end
    end

    if self._root_panel and not panel_alive(self._root_panel) then
        self._root_panel = nil
        self._timer_prim = nil
        self._title_prim = nil
        self._bags_prim = nil
        self._bags_label_prim = nil
    end

    local status, existing = safe_call(parent, "child", MISSION_ROOT_NAME)
    if status == CALL_OK and existing ~= nil and panel_alive(existing) then
        if self._root_panel == existing then
            self._mounted = true
            self._parent_panel = parent
            self:_update_layout()
            self:_ensure_primitives()
            self:_verify_render()
            if self._render_verified then
                self:_try_acquire_native()
            end
            return
        end
        return
    end
    if status ~= CALL_OK then
        return
    end

    local create_status, root = safe_call(parent, "panel", {name = MISSION_ROOT_NAME})
    if create_status ~= CALL_OK or root == nil then return end
    self._root_panel = root
    self._parent_panel = parent
    self._mounted = true
    self:_take_snapshot(mgr)
    self:_update_layout()
    self:_ensure_primitives()
    self:_verify_render()
    if self._render_verified then
        self:_try_acquire_native()
    end
end

function M:unmount()
    self:_release_native()
    self._render_verified = false
    if not self._mounted and not self._root_panel then return true end
    if self._root_panel then
        if panel_alive(self._root_panel) then
            local parent = self._parent_panel
            if parent and panel_alive(parent) then
                local status, result = safe_call(parent, "remove", self._root_panel)
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
    self._timer_prim = nil
    self._title_prim = nil
    self._bags_prim = nil
    self._bags_label_prim = nil
    self._parent_panel = nil
    self._mounted = false
    self._layout_cache = nil
    self._cached_timer_text = nil
    self._cached_title_text = nil
    self._cached_bags_text = nil
    self._cached_bags_label_text = nil
    self._cached_font = nil
    self._cached_font_size = nil
    self._cached_timer_visible = nil
    self._cached_title_visible = nil
    self._cached_bags_visible = nil
    self._cached_bags_label_visible = nil
    return true
end

function M:rebuild(manager)
    self:_release_native()
    self._render_verified = false
    local s_timer_text = self._timer_text
    local s_timer_known = self._timer_known
    local s_title_text = self._title_text
    local s_title_needs_retry = self._title_needs_retry
    local s_snapshot = self._snapshot_taken

    self:unmount()
    self:mount(manager)

    if not self._timer_known and s_timer_known then
        self._timer_text = s_timer_text
        self._timer_known = s_timer_known
    end
    if (not self._title_text or self._title_text == "") and s_title_text then
        self._title_text = s_title_text
        self._title_needs_retry = s_title_needs_retry
    end
    self._snapshot_taken = self._snapshot_taken or s_snapshot
    self:_sync_primitives()
end

function M:refresh_settings(manager)
    if kyohud.settings.enable_mission == true then
        if not self._mounted or not self._root_panel or not panel_alive(self._root_panel) then
            self:mount(manager)
            if self._mounted then
                if not self:_verify_render() then
                    self:_handle_render_failure()
                    self:_release_native()
                elseif not self._native_acquired then
                    self:_try_acquire_native()
                end
            end
            return
        end
        self:_update_layout()
        self._render_failed = false
        self:_ensure_primitives()
        self:_sync_primitives()
        if not self:_verify_render() then
            self:_handle_render_failure()
            self:_release_native()
        elseif not self._native_acquired then
            self:_try_acquire_native()
        end
    else
        if self._mounted or self._root_panel then
            self:_release_native()
            self:unmount()
        end
    end
end

function M:on_heist_start(manager)
    local mgr = manager or self._manager
    if not mgr then return end

    local gpc_ok, current_gpc = pcall(function() return managers.game_play_central end)

    local same_manager = (self._mounted_manager_id == mgr) or
                         (self._mounted_manager_id == nil and self._manager == mgr)

    if same_manager then
        self._manager = mgr
        self._mounted_manager_id = mgr
        if gpc_ok and current_gpc then
            self._bound_gpc = current_gpc
        end
        return
    end

    local is_initial_binding = (self._manager == nil)
    local preserve_snapshot = false
    local preserved_gpc_snapshot
    local preserved_gpc_valid
    local preserved_gpc_gen
    local preserved_gpc_source

    if self._gpc_snapshot_valid and self._gpc_snapshot ~= nil and self._gpc_source ~= nil then
        local source_matches_current = gpc_ok and current_gpc and self._gpc_source == current_gpc
        local source_differs_from_bound = (self._bound_gpc == nil) or (self._gpc_source ~= self._bound_gpc)
        if source_matches_current and (is_initial_binding or source_differs_from_bound) then
            preserve_snapshot = true
            preserved_gpc_snapshot = self._gpc_snapshot
            preserved_gpc_valid = self._gpc_snapshot_valid
            preserved_gpc_gen = self._gpc_generation
            preserved_gpc_source = self._gpc_source
        end
    end

    if self._mounted or self._root_panel then
        self:_release_native()
        self:unmount()
    end

    self:_reset_heist_state()

    if preserve_snapshot then
        self._gpc_snapshot = preserved_gpc_snapshot
        self._gpc_snapshot_valid = preserved_gpc_valid
        self._gpc_generation = preserved_gpc_gen
        self._gpc_source = preserved_gpc_source
    end

    if gpc_ok and current_gpc then
        self._bound_gpc = current_gpc
    else
        self._bound_gpc = nil
    end

    self._last_retry_time = nil
    self._manager = mgr
    self._mounted_manager_id = mgr
    self._heist_generation = (self._heist_generation or 0) + 1
end

function M:destroy(manager)
    if manager and self._manager and manager ~= self._manager then
        return
    end
    self:_release_native()
    self:unmount()
end

function M:update(manager, t, dt)
    if self._mounted and self._root_panel and not panel_alive(self._root_panel) then
        self:_release_native()
        self._root_panel = nil
        self._parent_panel = nil
        self._timer_prim = nil
        self._title_prim = nil
        self._bags_prim = nil
        self._bags_label_prim = nil
        self._mounted = false
        self._layout_cache = nil
        self._render_verified = false
    end

    if kyohud.settings.enable_mission ~= true then
        if self._mounted or self._root_panel then
            self:_release_native()
            self:unmount()
        elseif self._native_timer_text then
            self:_release_native()
        end
        return
    end

    if self._native_timer_text and not self._native_acquired then
        self:_release_native()
    end

    if not self._mounted then
        self:mount(manager or self._manager)
    end

    if self._native_timer_text then
        self:_check_native_leaf()
    end

    if self._render_failed then
        local can_retry = false
        if t and (self._last_retry_time == nil or (t - self._last_retry_time) >= 0.5) then
            can_retry = true
        end
        if can_retry then
            if not self._layout_cache then
                self:_update_layout()
            end
            self._render_failed = false
            self:_ensure_primitives()
            self:_sync_primitives()
            if not self:_verify_render() then
                self._render_failed = true
                self:_handle_render_failure()
            else
                safe_call(self._root_panel, "set_visible", true)
                self:_try_acquire_native()
            end
        end
        return
    end

    if self._timer_prim and panel_alive(self._timer_prim) then
        self:_sync_timer_prim()
    end

    if not self._mounted or not self._root_panel or not panel_alive(self._root_panel) then
        return
    end

    local do_retry = false
    if t and (self._last_retry_time == nil or (t - self._last_retry_time) >= 0.5) then
        do_retry = true
        self._last_retry_time = t
    end

    if do_retry then
        if self._title_needs_retry then
            local resolved = self:_resolve_title()
            if resolved then
                self._title_text = resolved
                self._title_needs_retry = false
                if self._title_prim and panel_alive(self._title_prim) then
                    if resolved ~= self._cached_title_text then
                        local status, _ = safe_call(self._title_prim, "set_text", self._title_text)
                        if status == CALL_OK then
                            local ok_rb, rb = pcall(function() return self._title_prim:text() end)
                            if ok_rb and rb == self._title_text then
                                self._cached_title_text = self._title_text
                            end
                        end
                    end
                end
            end
        end
        if not self._bags_known then
            local ok_lm, lm = pcall(function() return managers.loot end)
            if ok_lm and lm then
                self:_resolve_bags()
                if self._bags_prim and panel_alive(self._bags_prim) then
                    local new_text = self._bags_known and tostring(self._bags_count) or "--"
                    if new_text ~= self._cached_bags_text then
                        local status, _ = safe_call(self._bags_prim, "set_text", new_text)
                        if status == CALL_OK then
                            local ok_rb, rb = pcall(function() return self._bags_prim:text() end)
                            if ok_rb and rb == new_text then
                                self._cached_bags_text = new_text
                            end
                        end
                    end
                end
            end
        end
        self:_update_layout()
        self:_ensure_primitives()
        self:_sync_primitives()
        if not self:_verify_render() then
            self:_handle_render_failure()
            return
        end
        if not self._native_acquired and self._render_verified then
            self:_try_acquire_native()
        end
    end
end

kyohud.hud._installed_hooks = kyohud.hud._installed_hooks or {}

local function safe_hook(class, method, id, fn)
    if type(class) ~= "table" then return end
    if kyohud.hud._installed_hooks[id] then return end
    if type(class[method]) ~= "function" then return end
    Hooks:PostHook(class, method, id, fn)
    kyohud.hud._installed_hooks[id] = true
end

if RequiredScript == REQUIRED_CONTEXT then
    local function cb_feed(self, time)
        M:_check_native_leaf()
        capture_timer(self, true)
        if not M._layout_cache then
            M:_update_layout()
        end
        if M._render_failed then
            M._render_failed = false
        end
        M:_ensure_timer_prim()
        if M._timer_prim and panel_alive(M._timer_prim) then
            M:_sync_primitives()
            if not M:_verify_render() then
                M:_handle_render_failure()
            elseif not M._native_acquired then
                M:_try_acquire_native()
            end
        end
    end

    local function cb_modify(self, time)
        M:_check_native_leaf()
        capture_timer(self, true)
        if not M._layout_cache then
            M:_update_layout()
        end
        if M._render_failed then
            M._render_failed = false
        end
        M:_ensure_timer_prim()
        if M._timer_prim and panel_alive(M._timer_prim) then
            M:_sync_primitives()
            if not M:_verify_render() then
                M:_handle_render_failure()
            elseif not M._native_acquired then
                M:_try_acquire_native()
            end
        end
    end

    local function cb_loot_value(self)
        M:_resolve_bags()
        M:_sync_bags_prim()
    end

    local function cb_create_timer(self)
        M:_check_native_leaf()
        M:_release_native()
        capture_timer(self)
        if not M._layout_cache then
            M:_update_layout()
        end
        if M._render_failed then
            M._render_failed = false
        end
        M:_ensure_timer_prim()
        if M._timer_prim and panel_alive(M._timer_prim) then
            M:_sync_primitives()
            if not M:_verify_render() then
                M:_handle_render_failure()
            elseif not M._native_acquired then
                M:_try_acquire_native()
            end
        end
    end

    local function wrapped_feed(self, time)
        local rt = kyohud.hud.runtime
        if not rt or type(rt._residual_stamp) ~= "function"
            or type(rt._residual_record) ~= "function" then
            cb_feed(self, time)
            return
        end
        local probe = rt._residual_probe
        if not probe or probe.done or not probe.active then
            cb_feed(self, time)
            return
        end
        local start = rt:_residual_stamp()
        cb_feed(self, time)
        rt:_residual_record("mission_feed", start)
    end

    safe_hook(HUDManager, "feed_heist_time", "KyohHUD_Mission_FeedHeistTime", wrapped_feed)
    safe_hook(HUDManager, "modify_heist_time", "KyohHUD_Mission_ModifyHeistTime", cb_modify)
    safe_hook(HUDManager, "loot_value_updated", "KyohHUD_Mission_LootValueUpdated", cb_loot_value)
    safe_hook(HUDManager, "_create_heist_timer", "KyohHUD_Mission_CreateHeistTimer", cb_create_timer)
end

if RequiredScript == LOOT_CONTEXT then
    safe_hook(LootManager, "sync_load", "KyohHUD_Mission_SyncLoad", function(self, data)
        M:_resolve_bags()
        M:_sync_bags_prim()
    end)
end

if RequiredScript == GPC_CONTEXT then
    local function cb_gpc_load(self, data)
        if type(data) ~= "table" then return end
        local state = data.GamePlayCentralManager
        if type(state) ~= "table" then return end
        local heist_timer = state.heist_timer
        if is_valid_time_value(heist_timer) then
            M._gpc_source = self
            M._gpc_generation = (M._gpc_generation or 0) + 1
            M:_capture_gpc_snapshot(heist_timer)
        end
    end

    local function cb_gpc_sync(self, time, id)
        if type(id) ~= "number" or id ~= 1 then return end
        if is_valid_time_value(time) then
            M._gpc_source = self
            M:_capture_gpc_snapshot(time)
            M:_ensure_timer_prim()
            if M._timer_prim and panel_alive(M._timer_prim) then
                M:_sync_primitives()
                if not M:_verify_render() then
                    M:_handle_render_failure()
                elseif not M._native_acquired then
                    M:_try_acquire_native()
                end
            end
        end
    end

    safe_hook(GamePlayCentralManager, "load", "KyohUD_Mission_GPCLoad", cb_gpc_load)
    safe_hook(GamePlayCentralManager, "sync_heist_time", "KyohUD_Mission_GPCSync", cb_gpc_sync)
end

local function install_residual_phase_wrappers()
    local wrappers = M._residual_phase_wrappers
    if type(wrappers) ~= "table" then
        wrappers = {}
        M._residual_phase_wrappers = wrappers
    end
    local function install(name, phase, returns_value)
        local current = M[name]
        if type(current) ~= "function" then return end
        if current == wrappers[name] then return end
        local original = current
        local wrapper
        if returns_value then
            wrapper = function(self, ...)
                local rt = kyohud.hud.runtime
                if not rt or type(rt._residual_stamp) ~= "function"
                    or type(rt._residual_record) ~= "function" then
                    return original(self, ...)
                end
                local probe = rt._residual_probe
                if not probe or probe.done or not probe.active then
                    return original(self, ...)
                end
                local start = rt:_residual_stamp()
                local result = original(self, ...)
                rt:_residual_record(phase, start)
                return result
            end
        else
            wrapper = function(self, ...)
                local rt = kyohud.hud.runtime
                if not rt or type(rt._residual_stamp) ~= "function"
                    or type(rt._residual_record) ~= "function" then
                    original(self, ...)
                    return
                end
                local probe = rt._residual_probe
                if not probe or probe.done or not probe.active then
                    original(self, ...)
                    return
                end
                local start = rt:_residual_stamp()
                original(self, ...)
                rt:_residual_record(phase, start)
            end
        end
        wrappers[name] = wrapper
        M[name] = wrapper
    end
    install("_sync_primitives", "mission_sync", false)
    install("_sync_title_prim", "mission_title_sync", false)
    install("_update_layout", "mission_layout", false)
    install("_verify_render", "mission_verify", true)
    install("_verify_labels", "mission_labels_verify", true)
end
install_residual_phase_wrappers()
