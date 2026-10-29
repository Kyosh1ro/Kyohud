kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end

kyohud.hud = kyohud.hud or {}

local C = kyohud.hud.crew or {}
kyohud.hud.crew = C

C._root = C._root
C._cards = C._cards or {}
C._mounted = C._mounted or false
C._parent_panel = C._parent_panel
C._manager = C._manager
C._render_verified = C._render_verified or false
C._layout_cache = nil
C._last_poll_time = nil
C._last_present_time = nil

local ROOT_NAME = "kyohud_crew_panel"
local REF_CARD_W = 280
local REF_CARD_H = 120
local REF_GAP = 12
local REF_BOTTOM_RESERVE = 200
local MAX_CARDS = 3
local CREW_POLL_INTERVAL = 0.5
local PRESENT_INTERVAL = 0.05
local MIN_EFF_SCALE = 0.1

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

local function finite(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    return true
end

local function get_runtime_root()
    local rt = kyohud.hud.runtime
    if not rt or not rt._mounted then return nil end
    local root = rt._root_panel
    if not root or not panel_alive(root) then return nil end
    return root
end

local function enabled()
    return kyohud.settings.enable_crew == true
        and kyohud.settings.enable_hud_foundation == true
        and not is_vr()
end

-- Temporary transition trace, capped per Lua session; remove after diagnosis.
function C:_diagnostic(state, detail)
    if self._diag_state == state then return end
    self._diag_state = state
    local count = self._diag_count or 0
    if count >= 12 or type(log) ~= "function" then return end
    self._diag_count = count + 1
    pcall(log, "[KyoHUD][CrewDiag] state=" .. state .. " t=" .. tostring(self._last_time or 0)
        .. " detail=" .. tostring(detail or "none"))
end

function C:_compute_layout(parent_w, parent_h)
    if not finite(parent_w) or not finite(parent_h) then return nil end
    if parent_w <= 0 or parent_h <= 0 then return nil end
    local layout = kyohud.hud.layout
    if not layout or type(layout.resolve) ~= "function" then return nil end
    local scale = kyohud.settings.hud_scale or 1
    local geom = layout.resolve(parent_w, parent_h, scale)
    if not geom or not geom.valid then return nil end
    local us = geom.uniform_scale or 1
    local s = geom.scale or 1
    local eff = us * s
    if eff < MIN_EFF_SCALE then return nil end
    local card_w = REF_CARD_W * eff
    local card_h = REF_CARD_H * eff
    local gap = REF_GAP * us
    local margin_x = geom.margin_x or 0
    local margin_y = margin_x
    local reserve = REF_BOTTOM_RESERVE * us
    local total_w = MAX_CARDS * card_w + (MAX_CARDS - 1) * gap
    if total_w <= 0 or card_h <= 0 then return nil end
    local x = margin_x
    local y = parent_h - margin_y - reserve - card_h
    if y < margin_y then y = margin_y end
    if x + total_w > parent_w - margin_x then return nil end
    if y + card_h > parent_h - margin_y then return nil end
    local equipment_left = parent_w - margin_x - (680 * s + 12) * us
    if x + total_w > equipment_left then return nil end
    return {
        x = x, y = y,
        card_w = card_w, card_h = card_h,
        gap = gap, total_w = total_w,
        parent_w = parent_w, parent_h = parent_h,
    }
end

function C:_create_cards()
    if not self._root or not panel_alive(self._root) then return end
    local cc = kyohud.hud.crew_card
    if not cc or type(cc.new) ~= "function" then return end
    for i = 1, MAX_CARDS do
        local old = self._cards[i]
        if old and not old:_all_live() then
            old:destroy()
            self._cards[i] = nil
        end
        if not self._cards[i] then
            local name = ROOT_NAME .. "_c" .. tostring(i)
            local card = cc.new(self._root, name)
            if card then
                self._cards[i] = card
            end
        end
    end
end

function C:_apply_layout()
    if not self._layout_cache then return end
    local lc = self._layout_cache
    if self._root and panel_alive(self._root) then
        safe_call(self._root, "set_shape", lc.x, lc.y, lc.total_w, lc.card_h)
    end
    for i = 1, MAX_CARDS do
        local card = self._cards[i]
        if card then
            local cx = (i - 1) * (lc.card_w + lc.gap)
            card:set_geometry(cx, 0, lc.card_w, lc.card_h)
        end
    end
end

function C:_present_cards(snap, t)
    if not self._root or not panel_alive(self._root) then return end
    if not self._layout_cache then
        safe_call(self._root, "set_visible", false)
        return
    end
    local by_pos = {}
    if snap then
        for _, entry in ipairs(snap) do
            if entry and finite(entry.position) and entry.position >= 1 and entry.position <= MAX_CARDS then
                by_pos[entry.position] = entry
            end
        end
    end
    local any_visible = false
    self._expected_positions = {}
    for i = 1, MAX_CARDS do
        local card = self._cards[i]
        if card then
            local actor = by_pos[i]
            if actor then
                self._expected_positions[i] = true
                local ok = card:update(actor, t)
                if ok then
                    any_visible = true
                else
                    pcall(function()
                        if card.root and panel_alive(card.root) then
                            card.root:set_visible(false)
                        end
                    end)
                end
            else
                pcall(function()
                    if card.root and panel_alive(card.root) then
                        card.root:set_visible(false)
                    end
                end)
            end
        end
    end
    if any_visible then
        safe_call(self._root, "set_visible", true)
    else
        safe_call(self._root, "set_visible", false)
    end
end

function C:_verify_render()
    self._verify_detail = nil
    local lc = self._layout_cache
    local ok, valid = pcall(function()
        if not lc or not panel_alive(self._root) or not self._expected_positions then return false end
        if not self._root:visible() or self._root:alpha() ~= 1 then return false end
        local function close(a, b) return finite(a) and math.abs(a - b) <= 0.5 end
        if not close(self._root:x(), lc.x) or not close(self._root:y(), lc.y)
            or not close(self._root:w(), lc.total_w) or not close(self._root:h(), lc.card_h) then return false end
        local any = false
        for i = 1, MAX_CARDS do
            local card = self._cards[i]
            if not card or not panel_alive(card.root) then return false end
            if self._expected_positions[i] then
                any = true
                if not card:verify() then
                    self._verify_detail = "card=" .. tostring(i) .. " " .. tostring(card._verify_failure or "unavailable")
                    return false
                end
            elseif card.root:visible() then return false end
        end
        return any
    end)
    self._render_verified = ok and valid == true
    return self._render_verified
end

function C:_combat_conflict()
    self._conflict_detail = nil
    local panel, lc = kyohud._panel, self._layout_cache
    if not lc or not panel_alive(panel) then return false end
    local ok, conflict = pcall(function()
        if not panel:visible() then return false end
        local function overlaps(p)
            if not panel_alive(p) or not p:visible() then return false end
            if type(p.alpha) == "function" and p:alpha() <= 0 then return false end
            local x, y = p:x(), p:y()
            if type(p.world_x) == "function" and type(self._parent_panel.world_x) == "function" then
                x = p:world_x() - self._parent_panel:world_x()
                y = p:world_y() - self._parent_panel:world_y()
            end
            local hit = p:w() > 0 and p:h() > 0 and x < lc.x + lc.total_w and x + p:w() > lc.x
                and y < lc.y + lc.card_h and y + p:h() > lc.y
            if hit then
                self._conflict_detail = string.format("rect=%.1f,%.1f,%.1f,%.1f", x, y, p:w(), p:h())
            end
            return hit
        end
        -- Only our existing drawn combat children, never a native/third-party tree scan.
        if panel:w() < lc.parent_w or panel:h() < lc.parent_h then return overlaps(panel) end
        for _, child in pairs(panel:children()) do
            if overlaps(child) then return true end
        end
        return false
    end)
    return not ok or conflict == true
end

function C:mount(manager)
    if not enabled() then return end
    local mgr = manager or self._manager
    if not mgr then return end
    self._manager = mgr
    local parent = get_runtime_root()
    if not parent then return end
    if self._mounted and self._root and panel_alive(self._root) then
        if self._parent_panel == parent then return end
        self:unmount()
    end
    if self._root and not panel_alive(self._root) then
        self._root = nil
        for i = 1, MAX_CARDS do self._cards[i] = nil end
    end
    local status, existing = safe_call(parent, "child", ROOT_NAME)
    if status == CALL_OK and existing ~= nil and panel_alive(existing) then
        if self._root == existing then
            self._mounted = true
            self._parent_panel = parent
            return
        end
        return
    end
    if status ~= CALL_OK then return end
    local create_status, root = safe_call(parent, "panel", {name = ROOT_NAME})
    if create_status ~= CALL_OK or root == nil then return end
    self._root = root
    self._parent_panel = parent
    self._mounted = true
    self:_create_cards()
    local pw_s, pw = safe_call(parent, "w")
    local ph_s, ph = safe_call(parent, "h")
    if pw_s == CALL_OK and ph_s == CALL_OK and finite(pw) and finite(ph) and pw > 0 and ph > 0 then
        self._layout_cache = self:_compute_layout(pw, ph)
    end
    if self._layout_cache then
        self:_apply_layout()
    else
        safe_call(self._root, "set_visible", false)
    end
end

function C:unmount()
    if not self._mounted and not self._root then return true end
    if self._cards then
        for i = 1, MAX_CARDS do
            local card = self._cards[i]
            if card and type(card.destroy) == "function" then
                pcall(function() card:destroy() end)
            end
            self._cards[i] = nil
        end
    end
    if self._root then
        if panel_alive(self._root) then
            local parent = self._parent_panel
            if parent and panel_alive(parent) then
                local status, child = safe_call(parent, "child", ROOT_NAME)
                if status == CALL_OK and child == self._root then
                    safe_call(parent, "remove", self._root)
                end
            end
        end
        self._root = nil
    end
    self._parent_panel = nil
    self._mounted = false
    self._layout_cache = nil
    self._render_verified = false
    return true
end

function C:refresh_settings(manager)
    if enabled() then
        if not self._mounted or not self._root or not panel_alive(self._root) then
            self:mount(manager)
            return
        end
        local parent = self._parent_panel
        if parent and panel_alive(parent) then
            local pw_s, pw = safe_call(parent, "w")
            local ph_s, ph = safe_call(parent, "h")
            if pw_s == CALL_OK and ph_s == CALL_OK and finite(pw) and finite(ph) and pw > 0 and ph > 0 then
                self._layout_cache = self:_compute_layout(pw, ph)
            else
                self._layout_cache = nil
            end
        end
        if self._layout_cache then
            self:_apply_layout()
            self._last_present_time = nil
            self._last_poll_time = nil
            self:update(manager or self._manager, self._last_time or 0, 0)
        else
            safe_call(self._root, "set_visible", false)
        end
    else
        if self._mounted or self._root then
            self:unmount()
        end
    end
end

function C:on_heist_start(manager)
    self._manager = manager or self._manager
    self._last_poll_time = nil
    self._last_present_time = nil
end

function C:update(manager, t, dt)
    if not finite(t) then return end
    if manager and self._manager and manager ~= self._manager then return end
    self._last_time = t
    if not enabled() then
        if self._mounted or self._root then
            self:unmount()
        end
        return
    end
    if self._mounted and self._root and not panel_alive(self._root) then
        self._root = nil
        self._mounted = false
        self._layout_cache = nil
        self._render_verified = false
        for i = 1, MAX_CARDS do self._cards[i] = nil end
    end
    if not self._mounted then
        self:mount(manager or self._manager)
    end
    if not self._mounted or not self._root then return end
    local mgr = manager or self._manager
    local actors = kyohud.hud.actors
    local poll = self._last_poll_time == nil or t < self._last_poll_time or (t - self._last_poll_time) >= CREW_POLL_INTERVAL
    if actors and type(actors.refresh_crew) == "function" then
        if poll then
            actors:refresh_crew(mgr, t)
            self._last_poll_time = t
        end
    end
    if self._last_present_time ~= nil and t >= self._last_present_time and (t - self._last_present_time) < PRESENT_INTERVAL then
        return
    end
    self._last_present_time = t
    if poll then
        self:_create_cards()
        self._conflict = self:_combat_conflict()
    end
    if self._conflict then
        safe_call(self._root, "set_visible", false)
        self._render_verified = false
        self:_diagnostic("conflict", self._conflict_detail or "read-error")
        return
    end
    if not self._layout_cache then
        safe_call(self._root, "set_visible", false)
        self:_diagnostic("layout")
        return
    end
    local snap = nil
    if actors and type(actors.get_crew_snapshot) == "function" then
        snap = actors:get_crew_snapshot()
    end
    self:_apply_layout()
    safe_call(self._root, "set_alpha", 1)
    self:_present_cards(snap, t)
    if not self:_verify_render() then
        if self._root and panel_alive(self._root) then
            safe_call(self._root, "set_visible", false)
            self:_apply_layout()
            if snap then
                self:_present_cards(snap, t)
            end
            if not self:_verify_render() then
                safe_call(self._root, "set_visible", false)
            end
        end
    end
    if self._render_verified then
        self:_diagnostic("visible")
    elseif not snap or #snap == 0 then
        self:_diagnostic("empty")
    else
        self:_diagnostic("render", self._verify_detail or "root-or-primitive")
    end
end

function C:destroy(manager)
    if manager and self._manager and manager ~= self._manager then
        return
    end
    self:unmount()
end
