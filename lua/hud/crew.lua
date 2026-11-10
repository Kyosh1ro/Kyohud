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
-- quality split approved 2026-11-10
C._update_ran_now = C._update_ran_now or false
C._verify_ok_now = C._verify_ok_now or false
C._layout_cache = nil
C._last_poll_time = nil
C._last_present_time = nil
C._clearance_y = nil

local ROOT_NAME = "kyohud_crew_panel"
local REF_CARD_W = 432
local REF_CARD_H = 120
local REF_GAP = 20
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
    local e = us * s
    if e < MIN_EFF_SCALE then return nil end
    local lp = type(layout.local_player) == "function" and layout.local_player(parent_w, parent_h, scale) or nil
    if not lp then return nil end
    local boundary = lp.x - 12 * e
    local gap = REF_GAP * e
    local card_h = REF_CARD_H * e
    local state_h = 30 * e
    local x = 44 * e
    local y = parent_h - 144 * e
    local slack = 1e-6 * us
    local card_w = math.min(REF_CARD_W * e, (boundary - x - (MAX_CARDS - 1) * gap - slack) / MAX_CARDS)
    if card_w <= 0 or card_h <= 0 then return nil end
    local total_w = MAX_CARDS * card_w + (MAX_CARDS - 1) * gap
    if total_w <= 0 then return nil end
    if x + total_w > boundary then return nil end
    if y - state_h < 0 then return nil end
    if y + card_h > parent_h then return nil end
    return {
        x = x, y = y,
        state_h = state_h,
        card_w = card_w, card_h = card_h,
        gap = gap, total_w = total_w,
        parent_w = parent_w, parent_h = parent_h,
    }
end

function C:_create_cards()
    if not self._root or not panel_alive(self._root) then return end
    self:_refresh_pixel_mapping()
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

function C:_refresh_pixel_mapping()
    self._pixel_mapping = nil
    -- Read only the native screen workspace that owns this script GUI.
    -- Foreign/linked workspaces retain the approved logical gauge geometry.
    local ok, mapping = pcall(function()
        local mgr = self._manager
        local ws = mgr:workspace("saferect")
        local key = ws:key()
        local gd = managers.gui_data
        local cfg = gd._workspace_configuration[key]
        local data = gd._ws_size_data[key]
        if not cfg or cfg.workspace_object ~= "screen" or not data then return nil end
        local script = mgr:script(PlayerBase.PLAYER_INFO_HUD_PD2)
        local ws_root = ws:panel()
        if not script or not panel_alive(script.panel) or not panel_alive(ws_root)
            or script.panel:parent() ~= ws_root then return nil end
        if not panel_alive(self._parent_panel) or self._parent_panel:parent() ~= script.panel then return nil end
        if not finite(data.w) or data.w <= 0 or not finite(data.h) or data.h <= 0
            or not finite(data.on_screen_width) or data.on_screen_width <= 0
            or not finite(data.x) or not finite(data.y) then return nil end
        if math.abs(ws_root:w() - data.w) > 0.5 or math.abs(ws_root:h() - data.h) > 0.5 then return nil end
        local scale = data.on_screen_width / data.w
        if not finite(scale) or scale <= 0 then return nil end
        return {scale = scale, x = data.x, y = data.y}
    end)
    if ok then self._pixel_mapping = mapping end
end

function C:_apply_layout()
    if not self._layout_cache then return end
    local lc = self._layout_cache
    local state_h = lc.state_h or 0
    local y = self._clearance_y or lc.y
    if self._root and panel_alive(self._root) then
        safe_call(self._root, "set_shape", lc.x, y - state_h, lc.total_w, lc.card_h + state_h)
    end
    for i = 1, MAX_CARDS do
        local card = self._cards[i]
        if card then
            local cx = (i - 1) * (lc.card_w + lc.gap)
            card:set_geometry(cx, state_h + (card._bottom_offset or 0), lc.card_w, lc.card_h, self._pixel_mapping)
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
                    local measured, height = pcall(function() return card._backdrop:h() end)
                    if not measured or not finite(height) or height <= 0 or height > self._layout_cache.card_h then
                        ok = false
                    else
                        local lc = self._layout_cache
                        local offset = lc.card_h - height
                        if not finite(card._bottom_offset) or math.abs(card._bottom_offset - offset) > 0.01 then
                            card._bottom_offset = offset
                            card:set_geometry((i - 1) * (lc.card_w + lc.gap),
                                (lc.state_h or 0) + offset, lc.card_w, lc.card_h, self._pixel_mapping)
                            ok = card:update(actor, t)
                        end
                    end
                end
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
    local actors = kyohud.hud.actors
    if actors and type(actors.write_crew_native_coverage) == "function" then
        self._native_coverage = self._native_coverage or {}
        actors:write_crew_native_coverage(self._native_coverage, by_pos)
    end
    if any_visible then
        safe_call(self._root, "set_visible", true)
    else
        safe_call(self._root, "set_visible", false)
    end
end

function C:_verify_render()
    local lc = self._layout_cache
    local ok, valid = pcall(function()
        if not lc or not panel_alive(self._root) or not self._expected_positions then return false end
        if not self._root:visible() or self._root:alpha() ~= 1 then return false end
        local function close(a, b) return finite(a) and math.abs(a - b) <= 0.5 end
        local state_h = lc.state_h or 0
        local y = self._clearance_y or lc.y
        if not close(self._root:x(), lc.x) or not close(self._root:y(), y - state_h)
            or not close(self._root:w(), lc.total_w) or not close(self._root:h(), lc.card_h + state_h) then return false end
        local any = false
        for i = 1, MAX_CARDS do
            local card = self._cards[i]
            if not card or not panel_alive(card.root) then return false end
            if self._expected_positions[i] then
                any = true
                if not card:verify() then
                    return false
                end
            elseif card.root:visible() then return false end
        end
        return any
    end)
    self._render_verified = ok and valid == true
    -- quality split approved 2026-11-10
    self._verify_ok_now = self._render_verified
    return self._render_verified
end

function C:_occupied_top_offset()
    local top = nil
    for i = 1, MAX_CARDS do
        local card = self._cards[i]
        if card and panel_alive(card.root) then
            local ok, visible = pcall(function() return card.root:visible() end)
            if not ok or type(visible) ~= "boolean" then return nil end
            if visible then
                if not panel_alive(card._state_bg) then return nil end
                local header_ok, header = pcall(function() return card._state_bg:visible() end)
                if not header_ok or type(header) ~= "boolean" then return nil end
                local offset = card._bottom_offset or 0
                if header then offset = offset - (self._layout_cache.state_h or 0) end
                top = top and math.min(top, offset) or offset
            end
        end
    end
    return top or 0
end

function C:_combat_conflict()
    local panel, lc = kyohud._panel, self._layout_cache
    if not lc or not panel_alive(panel) then return false end
    local ok, conflict = pcall(function()
        if not panel:visible() then return false end
        local panel_alpha = 1
        if type(panel.alpha) == "function" then
            panel_alpha = panel:alpha() or 1
        end
        if not finite(panel_alpha) then return true end
        if panel_alpha <= 0 then return false end
        local state_h = lc.state_h or 0
        local effective_y = self._clearance_y or lc.y
        local occupied_top = self:_occupied_top_offset()
        if occupied_top == nil then return true end
        local root_top = effective_y + occupied_top
        local root_bottom = effective_y + lc.card_h
        local function overlaps(p)
            if not panel_alive(p) or not p:visible() then return false end
            if type(p.alpha) == "function" and p:alpha() <= 0 then return false end
            local x, y = panel:x() + p:x(), panel:y() + p:y()
            if type(p.world_x) == "function" and type(self._parent_panel.world_x) == "function" then
                x = p:world_x() - self._parent_panel:world_x()
                y = p:world_y() - self._parent_panel:world_y()
            end
            if not finite(x) or not finite(y) then return true end
            local pw, ph = p:w(), p:h()
            if not finite(pw) or not finite(ph) then return true end
            if pw <= 0 or ph <= 0 then return false end
            local hit = x < lc.x + lc.total_w and x + pw > lc.x
                and y < root_bottom and y + ph > root_top
            return hit
        end
        for _, child in pairs(panel:children()) do
            if overlaps(child) then return true end
        end
        return false
    end)
    return not ok or conflict == true
end

-- Nominal occupied rectangles, independent of buff-induced visibility fallback.
-- Only three owned cards are considered; never inspect a native subtree.
function C:get_buff_exclusions(panel)
    if not enabled() or not self._mounted or not self._layout_cache
        or not panel_alive(self._root) or not panel_alive(panel) then return nil end
    local ok, result = pcall(function()
        local function origin(p)
            local x, y = 0, 0
            for _ = 1, 8 do
                if not panel_alive(p) then return nil end
                local px, py = p:x(), p:y()
                if not finite(px) or not finite(py) then return nil end
                x, y = x + px, y + py
                local parent = p:parent()
                if not parent then return x, y, p end
                p = parent
            end
        end
        local px, py, pr = origin(self._parent_panel)
        local bx, by, br = origin(panel)
        if not px or not bx or pr ~= br then return nil end
        local lc = self._layout_cache
        local rows = self._buff_exclusions or {}
        self._buff_exclusions = rows
        local band = rows.band or {}
        rows.band = band
        band.valid = false
        local band_top = nil
        for i = 1, MAX_CARDS do
            local row = rows[i] or {}
            rows[i] = row
            row.valid = false
            local card = self._cards[i]
            if self._expected_positions and self._expected_positions[i] and card and card._exp then
                local offset = card._bottom_offset or 0
                local header = card._exp.state_bg_visible and (lc.state_h or 0) or 0
                row.x = px - bx + lc.x + (i - 1) * (lc.card_w + lc.gap)
                row.y = py - by + lc.y + offset - header
                row.w, row.h = lc.card_w, lc.card_h - offset + header
                row.gap = 12 * lc.card_h / 120
                row.valid = finite(row.x) and finite(row.y) and finite(row.w)
                    and finite(row.h) and row.w > 0 and row.h > 0
                if row.valid and (band_top == nil or row.y < band_top) then
                    band_top = row.y
                end
            end
        end
        -- Mirror the full-width union band used by _combat_conflict so the
        -- buff row yields above the actual scanned area, not per-card rows.
        if band_top ~= nil then
            band.x = px - bx + lc.x
            band.w = lc.total_w
            band.y = band_top
            band.h = (py - by + lc.y + lc.card_h) - band_top
            band.gap = 12 * lc.card_h / 120
            band.valid = band.w > 0 and band.h > 0
        end
        return rows
    end)
    return ok and result or nil
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
    self._pixel_mapping = nil
    self._native_coverage = nil
    self._buff_exclusions = nil
    self._expected_positions = nil
    self._render_verified = false
    self._clearance_y = nil
    return true
end

function C:refresh_settings(manager)
    if enabled() then
        if not self._mounted or not self._root or not panel_alive(self._root) then
            self:mount(manager)
            return
        end
        self:_refresh_pixel_mapping()
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
    -- quality split approved 2026-11-10
    self._update_ran_now = false
    self._verify_ok_now = false
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
    -- Poll frames must never be consumed by the presentation throttle, else conflict stays stale.
    if not poll and self._last_present_time ~= nil and t >= self._last_present_time and (t - self._last_present_time) < PRESENT_INTERVAL then
        return
    end
    self._last_present_time = t
    -- quality split approved 2026-11-10: main block ran, not a throttle return.
    self._update_ran_now = true
    local snap = nil
    if actors and type(actors.get_crew_snapshot) == "function" then
        snap = actors:get_crew_snapshot()
    end
    local presented = false
    if poll then
        self:_create_cards()
        self._clearance_y = nil
        self:_apply_layout()
        safe_call(self._root, "set_alpha", 1)
        self:_present_cards(snap, t)
        self._conflict = self:_combat_conflict()
        presented = true
    end
    if self._conflict then
        safe_call(self._root, "set_visible", false)
        self._render_verified = false
        return
    end
    if not self._layout_cache then
        safe_call(self._root, "set_visible", false)
        return
    end
    if not presented then
        self:_apply_layout()
        safe_call(self._root, "set_alpha", 1)
        self:_present_cards(snap, t)
    end
    local verifier = self._verify_render
    if not verifier(self) then
        if self._root and panel_alive(self._root) then
            safe_call(self._root, "set_visible", false)
            self:_apply_layout()
            if snap then
                self:_present_cards(snap, t)
            end
            verifier = self._verify_render
            if not verifier(self) then
                safe_call(self._root, "set_visible", false)
                return
            end
        else
            return
        end
    end
    return {
        module = self,
        root = self._root,
        manager = self._manager,
        verifier = verifier,
        ok = true,
    }
end

function C:destroy(manager)
    if manager and self._manager and manager ~= self._manager then
        return
    end
    self:unmount()
end
