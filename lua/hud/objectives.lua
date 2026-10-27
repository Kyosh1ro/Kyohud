kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end

kyohud.hud = kyohud.hud or {}

local O = kyohud.hud.objectives or {}
kyohud.hud.objectives = O

O._active = O._active or {}
O._by_id = O._by_id or {}
O._snapshot_manager = O._snapshot_manager or nil
O._load_order_sentinel = O._load_order_sentinel or {value = 17}

O._mounted = O._mounted or false
O._root_panel = O._root_panel
O._panel = O._panel
O._parent_panel = O._parent_panel
O._manager = O._manager
O._layout_cache = O._layout_cache
O._slot_prims = O._slot_prims or {}
O._slot_text_cache = O._slot_text_cache or {}
O._slot_amount_cache = O._slot_amount_cache or {}
O._slot_visible_cache = O._slot_visible_cache or {}
O._slot_fit_cache = O._slot_fit_cache or {}
O._slot_completion = O._slot_completion or {}
O._completion_history = O._completion_history or {}
O._coordinated_slide_extra = O._coordinated_slide_extra
O._coordinated_slide_slots = O._coordinated_slide_slots

O._native_leaves = O._native_leaves
O._native_generation = O._native_generation or 0
O._native_acquired = O._native_acquired or false
O._native_active_id = O._native_active_id
O._native_fallback = O._native_fallback or false
O._native_conflict_identity = O._native_conflict_identity or nil
O._native_conflict_leaf = O._native_conflict_leaf
O._native_completion_pending = O._native_completion_pending or false
O._native_completion_pending_self = O._native_completion_pending_self
O._native_completion_pending_panel = O._native_completion_pending_panel
O._sync_in_progress = O._sync_in_progress or false

local function copy_sub_objectives(src)
    if type(src) ~= "table" then return nil end
    local out = {}
    for _, sub in pairs(src) do
        if type(sub) == "table" and sub.id then
            out[sub.id] = {
                id = sub.id,
                text = sub.text,
                completed = sub.completed == true,
            }
        end
    end
    if next(out) == nil then return nil end
    return out
end

local function copy_objective_scalar(objective)
    if type(objective) ~= "table" or not objective.id then
        return nil
    end
    local current_amount = objective.current_amount
    if objective.countdown == true and type(objective.amount) == "number"
        and type(objective.current_amount) == "number" then
        current_amount = objective.amount - objective.current_amount
    end
    return {
        id = objective.id,
        text = objective.text,
        amount = objective.amount,
        current_amount = current_amount,
        countdown = objective.countdown == true,
        sub_objectives = copy_sub_objectives(objective.sub_objectives),
    }
end

function O:snapshot(manager)
    if type(manager) ~= "table" then return false end

    local ok, registry = pcall(function() return manager:get_active_objectives() end)
    if not ok or type(registry) ~= "table" then return false end

    local ids = {}
    for id in pairs(registry) do
        ids[#ids + 1] = id
    end

    local active_id = nil
    if managers and managers.hud and managers.hud._hud_objectives then
        active_id = managers.hud._hud_objectives._active_objective_id
    end

    if O._snapshot_manager ~= manager then
        O:_cancel_all_completion_animations()
        O._snapshot_manager = manager
        O._active = {}
        O._by_id = {}
        O:_clear_completion_history()

        table.sort(ids)

        if active_id then
            for i, id in ipairs(ids) do
                if id == active_id then
                    table.remove(ids, i)
                    ids[#ids + 1] = active_id
                    break
                end
            end
        end

        for _, id in ipairs(ids) do
            local scalar = copy_objective_scalar(registry[id])
            if scalar then
                local pending = false
                if manager._delayed_presentation and manager._delayed_presentation.activate_params
                    and manager._delayed_presentation.activate_params.id == id then
                    pending = true
                end
                scalar.pending = pending
                O._active[#O._active + 1] = scalar
                O._by_id[id] = #O._active
            end
        end
    else
        local old_pending = {}
        local known = {}
        local retained_ids = {}
        for _, entry in ipairs(O._active) do
            old_pending[entry.id] = entry.pending
            if registry[entry.id] then
                retained_ids[#retained_ids + 1] = entry.id
                known[entry.id] = true
            end
        end

        local new_ids = {}
        for _, id in ipairs(ids) do
            if not known[id] then
                new_ids[#new_ids + 1] = id
            end
        end
        table.sort(new_ids)

        if active_id then
            for i, id in ipairs(new_ids) do
                if id == active_id then
                    table.remove(new_ids, i)
                    new_ids[#new_ids + 1] = active_id
                    break
                end
            end
        end

        O._active = {}
        O._by_id = {}

        local build = function(id)
            local scalar = copy_objective_scalar(registry[id])
            if not scalar then return end
            local p = old_pending[id]
            if p == nil then
                p = false
                if manager._delayed_presentation and manager._delayed_presentation.activate_params
                    and manager._delayed_presentation.activate_params.id == id then
                    p = true
                end
            end
            scalar.pending = p
            O._active[#O._active + 1] = scalar
            O._by_id[id] = #O._active
        end

        for _, id in ipairs(retained_ids) do
            build(id)
        end
        for _, id in ipairs(new_ids) do
            build(id)
        end
        self:_cancel_orphan_successor_slots()
    end

    return true
end

function O:select_visible(limit)
    local ok, result = pcall(function()
        local n = limit
        if n == nil then
            n = kyohud.settings and kyohud.settings.objectives_visible_limit
        end
        if n == nil then n = 1 end
        if type(n) ~= "number" then return nil end
        if n ~= n then return nil end
        if n == math.huge or n == -math.huge then return nil end
        if math.floor(n) ~= n then return nil end
        n = math.floor(n)
        if n < 1 then n = 1 end
        if n > 3 then n = 3 end

        local native_current_id = nil
        local native_instance_exists = false
        if managers and managers.hud and managers.hud._hud_objectives then
            native_instance_exists = true
            local ok_aid, aid = pcall(function()
                return managers.hud._hud_objectives._active_objective_id
            end)
            if ok_aid and aid ~= nil then
                native_current_id = aid
            end
        end

        local chosen_id = nil
        if native_instance_exists then
            if native_current_id and O._by_id[native_current_id] then
                chosen_id = native_current_id
            end
        else
            if O._last_hud_presented_id and O._by_id[O._last_hud_presented_id] then
                chosen_id = O._last_hud_presented_id
            else
                for i = #O._active, 1, -1 do
                    local entry = O._active[i]
                    if not entry.pending then
                        chosen_id = entry.id
                        break
                    end
                end
            end
        end

        if not chosen_id then return {} end

        local idx = O._by_id[chosen_id]
        if not idx or not O._active[idx] then return {} end
        local entry = O._active[idx]
        return {entry}
    end)

    if not ok then return nil end
    return result
end

local OBJECTIVES_ROOT_NAME = "kyohud_objectives_panel"
local MAX_SLOTS = 3
local REF_OBJ_FONT_SIZE = 20
local MIN_OBJ_FONT_SIZE = 12

local COMPLETION_PULSE_T = 0.900
local COMPLETION_EXIT_T = 0.300
local COMPLETION_TOTAL_T = COMPLETION_PULSE_T + COMPLETION_EXIT_T
local COMPLETION_RISE = 4
local COMPLETION_AMOUNT_DIM = 0.45
local COMPLETION_HISTORY_ALPHA = 0.45
local COMPLETION_PULSE_MIN = 0.45
local COMPLETION_PULSE_MAX = 1.0
local COMPLETION_HISTORY_MAX = 2
local HUD_ACCENT_COLOR = Color(0.52, 0.88, 0.92)
local HUD_DEFAULT_COLOR = Color(1, 1, 1, 1)

local function o_smoothstep(t)
    if t <= 0 then return 0 end
    if t >= 1 then return 1 end
    return t * t * (3 - 2 * t)
end

local function o_pulse_alpha(elapsed)
    if elapsed <= 0 then return COMPLETION_PULSE_MAX end
    if elapsed >= COMPLETION_PULSE_T then return COMPLETION_PULSE_MAX end
    return COMPLETION_PULSE_MAX
end

local MOUNT_CALL_OK = "ok"
local MOUNT_CALL_MISSING = "missing"
local MOUNT_CALL_ERROR = "error"

local function mount_is_vr()
    return _G.IS_VR == true
end

local function mount_panel_alive(p)
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

local function mount_safe_call(obj, method_name, ...)
    if obj == nil then return MOUNT_CALL_MISSING, nil end
    local ok_get, method_or_err = pcall(function() return obj[method_name] end)
    if not ok_get then return MOUNT_CALL_ERROR, nil end
    if type(method_or_err) ~= "function" then return MOUNT_CALL_MISSING, nil end
    local ok_call, result = pcall(method_or_err, obj, ...)
    if not ok_call then return MOUNT_CALL_ERROR, nil end
    return MOUNT_CALL_OK, result
end

local function mount_is_finite(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    return true
end

local function mount_ensure_root_visible_bounded(self)
    if not self._root_panel or not mount_panel_alive(self._root_panel) then
        return false
    end
    local desired = not self._native_fallback
    local ok_read, actual = pcall(function() return self._root_panel:visible() end)
    if not ok_read or type(actual) ~= "boolean" then
        return false
    end
    if actual == desired then
        return true
    end
    local st, _ = mount_safe_call(self._root_panel, "set_visible", desired)
    if st ~= MOUNT_CALL_OK then
        return false
    end
    local ok_read2, actual2 = pcall(function() return self._root_panel:visible() end)
    if not ok_read2 or type(actual2) ~= "boolean" then
        return false
    end
    return actual2 == desired
end

local function mount_get_font()
    local ok_td, td = pcall(function() return tweak_data end)
    if not ok_td or not td then return nil end
    local ok_hud, hud = pcall(function() return td.hud end)
    if not ok_hud or not hud then return nil end
    local ok_font, f = pcall(function() return hud.medium_font_noshadow end)
    if not ok_font or type(f) ~= "string" or f == "" then return nil end
    return f
end

local function mount_get_runtime_root()
    local rt = kyohud.hud.runtime
    if not rt then return nil end
    if not rt._mounted then return nil end
    local root = rt._root_panel
    if not root or not mount_panel_alive(root) then return nil end
    return root
end

local function mount_format_amount(entry)
    if type(entry) ~= "table" then return nil end
    local current = entry.current_amount
    local total = entry.amount
    if mount_is_finite(current) and mount_is_finite(total) then
        return math.floor(current) .. "/" .. math.floor(total)
    end
    if mount_is_finite(current) then
        return tostring(math.floor(current))
    end
    return nil
end

local O_FIT_ELLIPSIS = "..."

local function o_utf8_codepoint_offsets(s)
    local offs = {1}
    local i = 1
    local n = #s
    while i <= n do
        local b = string.byte(s, i)
        if b == nil then break end
        local step
        if b < 0x80 then step = 1
        elseif b < 0xC0 then step = 1
        elseif b < 0xE0 then step = 2
        elseif b < 0xF0 then step = 3
        else step = 4 end
        i = i + step
        offs[#offs + 1] = i
    end
    return offs
end

local function o_measure_text_rect_body(prim)
    return prim:text_rect()
end

local function o_measure_text_rect(prim)
    if not prim or not mount_panel_alive(prim) then return false, 0, 0 end
    local ok, x, y, w, h = pcall(o_measure_text_rect_body, prim)
    if ok and mount_is_finite(w) and mount_is_finite(h) and w >= 0 and h >= 0 then
        return true, w, h
    end
    return false, 0, 0
end

local function o_prim_shape_body(prim)
    return prim:x(), prim:y(), prim:w(), prim:h()
end

local function o_read_prim_shape(prim)
    if not prim or not mount_panel_alive(prim) then return false, 0, 0, 0, 0 end
    local ok, x, y, w, h = pcall(o_prim_shape_body, prim)
    if ok and mount_is_finite(x) and mount_is_finite(y)
        and mount_is_finite(w) and mount_is_finite(h) then
        return true, x, y, w, h
    end
    return false, 0, 0, 0, 0
end

local function o_prim_font_size_body(prim)
    return prim:font_size()
end

local function o_read_prim_font_size(prim)
    if not prim or not mount_panel_alive(prim) then return false, 0 end
    local ok, fs = pcall(o_prim_font_size_body, prim)
    if ok and mount_is_finite(fs) then
        return true, fs
    end
    return false, 0
end

local function o_read_color_rgba(c)
    if c == nil then return false, 0, 0, 0, 0 end
    local ok_r, r = pcall(function() return c.r end)
    if ok_r and type(r) == "number" then
        local ok_g, g = pcall(function() return c.g end)
        local ok_b, b = pcall(function() return c.b end)
        local ok_a, a = pcall(function() return c.a end)
        if ok_g and type(g) == "number"
            and ok_b and type(b) == "number"
            and ok_a and type(a) == "number" then
            if not mount_is_finite(r) or not mount_is_finite(g)
                or not mount_is_finite(b) or not mount_is_finite(a) then
                return false, 0, 0, 0, 0
            end
            return true, r, g, b, a
        end
    end
    if type(c) == "table" then
        local c2 = c[2]
        local c3 = c[3]
        local c4 = c[4]
        if type(c2) == "number" and type(c3) == "number" and type(c4) == "number" then
            local c1 = c[1]
            if type(c1) ~= "number" then c1 = 1 end
            if not mount_is_finite(c1) or not mount_is_finite(c2)
                or not mount_is_finite(c3) or not mount_is_finite(c4) then
                return false, 0, 0, 0, 0
            end
            return true, c2, c3, c4, c1
        end
    end
    return false, 0, 0, 0, 0
end

local function o_color_matches_ref(c, ref)
    if not ref then return false end
    local ok_c, cr, cg, cb, ca = o_read_color_rgba(c)
    if not ok_c then return false end
    local ok_r, rr, rg, rb, ra = o_read_color_rgba(ref)
    if not ok_r then return false end
    if math.abs(cr - rr) > 0.01 then return false end
    if math.abs(cg - rg) > 0.01 then return false end
    if math.abs(cb - rb) > 0.01 then return false end
    return true
end

local function o_shape_matches(ax, ay, aw, ah, bx, by, bw, bh, tol)
    if not mount_is_finite(ax) or not mount_is_finite(ay)
        or not mount_is_finite(aw) or not mount_is_finite(ah) then
        return false
    end
    if not mount_is_finite(bx) or not mount_is_finite(by)
        or not mount_is_finite(bw) or not mount_is_finite(bh) then
        return false
    end
    if math.abs(ax - bx) > tol then return false end
    if math.abs(ay - by) > tol then return false end
    if math.abs(aw - bw) > tol then return false end
    if math.abs(ah - bh) > tol then return false end
    return true
end

local function o_verify_geometry_after_apply(self, new_layout, tol)
    local root_ok, rx, ry, rw, rh = o_read_prim_shape(self._root_panel)
    if not root_ok or not o_shape_matches(rx, ry, rw, rh,
        new_layout.root_x, new_layout.root_y, new_layout.root_w, new_layout.root_h, tol) then
        return false
    end
    for i = 1, MAX_SLOTS do
        local slot = self._slot_prims[i]
        if slot then
            if self._slot_completion[i] then
                -- Skip geometry checks for completion-animated slots
            elseif self._coordinated_slide_slots and self._coordinated_slide_slots[i] then
                -- Skip geometry checks for coordinated slide slots (they are moving)
            else
                local y = (i - 1) * new_layout.row_h
                local text_w = new_layout.root_w * 0.7
                local amount_w = new_layout.root_w - text_w
                if slot.text and mount_panel_alive(slot.text) then
                    local ok, sx, sy, sw, sh = o_read_prim_shape(slot.text)
                    if not ok or not o_shape_matches(sx, sy, sw, sh, 0, y, text_w, new_layout.row_h, tol) then
                        return false
                    end
                    local ok_fs, fs = o_read_prim_font_size(slot.text)
                    if not ok_fs or math.abs(fs - new_layout.font_size) > 0.5 then
                        return false
                    end
                end
                if slot.amount and mount_panel_alive(slot.amount) then
                    local ok, sx, sy, sw, sh = o_read_prim_shape(slot.amount)
                    if not ok or not o_shape_matches(sx, sy, sw, sh, text_w, y, amount_w, new_layout.row_h, tol) then
                        return false
                    end
                    local ok_fs, fs = o_read_prim_font_size(slot.amount)
                    if not ok_fs or math.abs(fs - new_layout.font_size) > 0.5 then
                        return false
                    end
                end
            end
        end
    end
    return true
end

local function o_layout_fit_sig(layout)
    if not layout then return "" end
    return tostring(layout.root_w) .. "|" .. tostring(layout.font_size) .. "|" .. tostring(layout.row_h)
end

function O:_compute_fitted_display(prim, source, max_w, max_h)
    if source == nil or source == "" then
        if prim and mount_panel_alive(prim) then
            mount_safe_call(prim, "set_text", "")
        end
        return "", 0, 0
    end
    if not prim or not mount_panel_alive(prim) then return source, 0, 0 end
    if not mount_is_finite(max_w) or not mount_is_finite(max_h) then return source, 0, 0 end
    if max_w <= 0 or max_h <= 0 then return O_FIT_ELLIPSIS, 0, 0 end

    mount_safe_call(prim, "set_text", source)
    local ok, tw, th = o_measure_text_rect(prim)
    if ok and tw <= max_w and th <= max_h then
        return source, tw, th
    end

    local offs = o_utf8_codepoint_offsets(source)
    local N = #offs - 1
    if N == 0 then
        mount_safe_call(prim, "set_text", O_FIT_ELLIPSIS)
        return O_FIT_ELLIPSIS, 0, 0
    end

    mount_safe_call(prim, "set_text", O_FIT_ELLIPSIS)
    local eok, ew, eh = o_measure_text_rect(prim)
    if not eok or ew > max_w or eh > max_h then
        return O_FIT_ELLIPSIS, ew, eh
    end

    local lo, hi = 1, N
    local best_k = 0
    local best_w, best_h = ew, eh
    while lo <= hi do
        local mid = math.floor((lo + hi) / 2)
        local cut_byte = offs[mid + 1]
        local candidate = source:sub(1, cut_byte - 1) .. O_FIT_ELLIPSIS
        mount_safe_call(prim, "set_text", candidate)
        local mok, mw, mh = o_measure_text_rect(prim)
        if mok and mw <= max_w and mh <= max_h then
            best_k = mid
            best_w = mw
            best_h = mh
            lo = mid + 1
        else
            hi = mid - 1
        end
    end

    local display
    if best_k == 0 then
        display = O_FIT_ELLIPSIS
    elseif best_k >= N then
        display = source
    else
        display = source:sub(1, offs[best_k + 1] - 1) .. O_FIT_ELLIPSIS
    end
    mount_safe_call(prim, "set_text", display)
    return display, best_w, best_h
end

function O:_add_to_completion_history(entry)
    if type(entry) ~= "table" or not entry.id then return end
    local history_entry = {
        id = entry.id,
        text = entry.text,
        is_history = true,
    }
    table.insert(self._completion_history, 1, history_entry)
    while #self._completion_history > COMPLETION_HISTORY_MAX do
        table.remove(self._completion_history, #self._completion_history)
    end
end

function O:_clear_completion_history()
    self._completion_history = {}
end

function O:_any_completion_active()
    for i = 1, MAX_SLOTS do
        local c = self._slot_completion[i]
        if c and c.active then
            return true
        end
    end
    return false
end

function O:_compute_displayed_entries()
    local limit = kyohud.settings and kyohud.settings.objectives_visible_limit
    if limit == nil then limit = 1 end
    if type(limit) ~= "number" then limit = 1 end
    if limit ~= limit then limit = 1 end
    if limit == math.huge or limit == -math.huge then limit = 1 end
    if math.floor(limit) ~= limit then limit = 1 end
    limit = math.floor(limit)
    if limit < 1 then limit = 1 end
    if limit > 3 then limit = 3 end
    local entries = O:select_visible()
    if not entries then entries = {} end
    local displayed = {}
    local history_slots = {}
    local used_slots = {}
    local used_entries = {}
    for i = 1, limit do
        local c = self._slot_completion[i]
        if c and (c.active or c.successor_entry) then
            used_slots[i] = true
            if c.successor_entry then
                if c.successor_entry_id then
                    used_entries[c.successor_entry_id] = true
                end
            elseif c.entry_id then
                used_entries[c.entry_id] = true
            end
            if c.displayed_snapshot then
                for si, snap_e in pairs(c.displayed_snapshot) do
                    if type(snap_e) == "table" and snap_e.id then
                        used_entries[snap_e.id] = true
                        used_slots[si] = true
                    end
                end
            end
            if c.successor_pending_entry and c.successor_pending_entry.id then
                used_entries[c.successor_pending_entry.id] = true
            end
        end
    end
    for i = 1, limit do
        if used_slots[i] then
            displayed[i] = nil
        end
    end
    local suppress_remaining = self:_any_completion_active()
    local has_current = false
    if not suppress_remaining then
        local remaining = {}
        for _, entry in ipairs(entries) do
            if not used_entries[entry.id] then
                remaining[#remaining + 1] = entry
            end
        end
        local r_idx = 1
        for i = 1, limit do
            if not used_slots[i] then
                if r_idx <= #remaining then
                    displayed[i] = remaining[r_idx]
                    r_idx = r_idx + 1
                else
                    displayed[i] = nil
                end
            end
        end
        has_current = r_idx > 1
    end
    if has_current then
        local h_idx = 1
        for i = 1, limit do
            if not displayed[i] and not used_slots[i] then
                if h_idx <= #self._completion_history then
                    displayed[i] = self._completion_history[h_idx]
                    history_slots[i] = true
                    h_idx = h_idx + 1
                end
            end
        end
    end
    return displayed, history_slots
end

function O:_compute_layout(parent_w, parent_h)
    if not mount_is_finite(parent_w) or not mount_is_finite(parent_h) then return nil end
    if parent_w <= 0 or parent_h <= 0 then return nil end
    local layout = kyohud.hud.layout
    if not layout or type(layout.resolve) ~= "function" then return nil end
    local scale = kyohud.settings.hud_scale or 1
    local geom = layout.resolve(parent_w, parent_h, scale)
    if not geom or not geom.valid then return nil end
    local us = geom.uniform_scale or 1
    local sc = geom.scale or 1
    local effective_scale = us * sc
    local region = nil
    if type(layout.objectives_region) == "function" then
        region = layout.objectives_region(parent_w, parent_h)
    end
    if not region then return nil end
    local root_x = region.x
    local root_y = region.y
    local root_w = region.w
    local root_h = region.h
    local row_h = root_h / MAX_SLOTS
    local font_size = math.floor(REF_OBJ_FONT_SIZE * effective_scale)
    local max_font = math.floor(row_h)
    if font_size > max_font then
        font_size = max_font
    end
    if font_size < MIN_OBJ_FONT_SIZE then
        font_size = MIN_OBJ_FONT_SIZE
    end
    return {
        root_x = root_x,
        root_y = root_y,
        root_w = root_w,
        root_h = root_h,
        font_size = font_size,
        row_h = row_h,
        parent_w = parent_w,
        parent_h = parent_h,
    }
end

function O:_clear_completion_slot(i)
    local c = self._slot_completion[i]
    if not c then return end
    local slot = self._slot_prims[i]
    if slot then
        if slot.text and mount_panel_alive(slot.text) then
            mount_safe_call(slot.text, "set_text", "")
            mount_safe_call(slot.text, "set_color", HUD_DEFAULT_COLOR)
            mount_safe_call(slot.text, "set_alpha", 1)
            local ly = self._layout_cache
            if ly then mount_safe_call(slot.text, "set_y", (i - 1) * ly.row_h) end
            mount_safe_call(slot.text, "set_visible", false)
        end
        if slot.amount and mount_panel_alive(slot.amount) then
            mount_safe_call(slot.amount, "set_text", "")
            mount_safe_call(slot.amount, "set_color", HUD_DEFAULT_COLOR)
            mount_safe_call(slot.amount, "set_alpha", 1)
            local ly = self._layout_cache
            if ly then mount_safe_call(slot.amount, "set_y", (i - 1) * ly.row_h) end
            mount_safe_call(slot.amount, "set_visible", false)
        end
        if slot.strike and mount_panel_alive(slot.strike) then
            local ok_w, aw = pcall(function() return slot.strike:w() end)
            if not ok_w or aw ~= 0 then
                mount_safe_call(slot.strike, "set_w", 0)
            end
            mount_safe_call(slot.strike, "set_visible", false)
        end
    end
    if c.coordinated_slide_active or (c.displayed_snapshot and next(c.displayed_snapshot)) then
        self._coordinated_slide_slots = nil
        if self._coordinated_slide_extra then
            local extra = self._coordinated_slide_extra
            if extra.text and mount_panel_alive(extra.text) then
                mount_safe_call(extra.text, "set_visible", false)
                mount_safe_call(extra.text, "set_text", "")
            end
            if extra.amount and mount_panel_alive(extra.amount) then
                mount_safe_call(extra.amount, "set_visible", false)
                mount_safe_call(extra.amount, "set_text", "")
            end
        end
    end
    self._slot_completion[i] = nil
end

function O:_cancel_all_completion_animations()
    for i = 1, MAX_SLOTS do
        self:_clear_completion_slot(i)
    end
end

function O:_cancel_orphan_successor_slots()
    for i = 1, MAX_SLOTS do
        local c = self._slot_completion[i]
        if c and c.successor_entry == true and c.successor_entry_id then
            if not self._by_id[c.successor_entry_id] then
                self:_clear_completion_slot(i)
            end
        end
    end
end

function O:_capture_completion(entry_id)
    if not self._mounted then return end
    if not self._root_panel or not mount_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    local idx = self._by_id[entry_id]
    if not idx or not self._active[idx] then return end
    local entry = self._active[idx]
    local displayed_pre, history_slots_pre = self:_compute_displayed_entries()
    if not displayed_pre then displayed_pre = {} end
    if not history_slots_pre then history_slots_pre = {} end
    local slot_idx = nil
    for si, e in pairs(displayed_pre) do
        if type(e) == "table" and e.id == entry.id then slot_idx = si; break end
    end
    if not slot_idx then return end
    local slot = self._slot_prims[slot_idx]
    if not slot then return end
    local ly = self._layout_cache
    local text_w = ly.root_w * 0.7
    local row_h = ly.row_h
    local source_text = (entry and type(entry.text) == "string") and entry.text or ""
    local display_text = source_text
    local fitted_w = 0
    if slot.text and mount_panel_alive(slot.text) then
        display_text, fitted_w = self:_compute_fitted_display(slot.text, source_text, text_w, row_h)
        if not mount_is_finite(fitted_w) then fitted_w = 0 end
    end
    local amount_text = nil
    if entry.amount and type(entry.amount) == "number" then
        if entry.countdown then
            amount_text = "0/" .. math.floor(entry.amount)
        else
            amount_text = math.floor(entry.amount) .. "/" .. math.floor(entry.amount)
        end
    end
    local title_y_base = (slot_idx - 1) * ly.row_h
    if slot.text and mount_panel_alive(slot.text) then
        local ok, ty = pcall(function() return slot.text:y() end)
        if ok and mount_is_finite(ty) then title_y_base = ty end
    end
    local amount_y_base = (slot_idx - 1) * ly.row_h
    if slot.amount and mount_panel_alive(slot.amount) then
        local ok, ay = pcall(function() return slot.amount:y() end)
        if ok and mount_is_finite(ay) then amount_y_base = ay end
    end
    local strike_h = 1
    local strike_y_base = title_y_base + (row_h - strike_h) / 2
    if not slot.strike or not mount_panel_alive(slot.strike) then
        slot.strike = nil
        local status, prim = mount_safe_call(self._root_panel, "rect", {
            name = "objective_" .. slot_idx .. "_strike",
            x = 0,
            y = strike_y_base,
            w = 0,
            h = strike_h,
            color = HUD_ACCENT_COLOR,
            visible = false,
            layer = 2,
        })
        if status == MOUNT_CALL_OK and prim then
            slot.strike = prim
        end
    else
        mount_safe_call(slot.strike, "set_y", strike_y_base)
        mount_safe_call(slot.strike, "set_w", 0)
        mount_safe_call(slot.strike, "set_visible", false)
    end
    local siblings_displayed = {}
    for si, e in pairs(displayed_pre) do
        if si ~= slot_idx and type(e) == "table" then
            siblings_displayed[si] = e.id
        end
    end
    local displayed_snapshot = {}
    local history_slots_snapshot = {}
    for si, e in pairs(displayed_pre) do
        if type(e) == "table" then
            displayed_snapshot[si] = {
                id = e.id,
                text = e.text,
                amount = e.amount,
                current_amount = e.current_amount,
                countdown = e.countdown,
            }
            if history_slots_pre[si] then
                history_slots_snapshot[si] = true
            end
        end
    end
    local fit_sig = o_layout_fit_sig(ly)
    self._slot_completion[slot_idx] = {
        active = true,
        elapsed = 0,
        source_text = source_text,
        display_text = display_text,
        fitted_w = fitted_w,
        amount_text = amount_text,
        title_y_base = title_y_base,
        amount_y_base = amount_y_base,
        strike_y_base = strike_y_base,
        fit_sig = fit_sig,
        strike_required = false,
        entry_id = entry.id,
        siblings_displayed = siblings_displayed,
        displayed_snapshot = displayed_snapshot,
        history_slots_snapshot = history_slots_snapshot,
        has_successor_pending = false,
    }
    if next(displayed_snapshot) then
        self._coordinated_slide_slots = self._coordinated_slide_slots or {}
        for si in pairs(displayed_snapshot) do
            self._coordinated_slide_slots[si] = true
        end
    end
    self:_render_completion_slot(slot_idx)
end

function O:animate(t, dt)
    if not self._mounted then return end
    if not self._root_panel or not mount_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    if type(dt) ~= "number" or dt ~= dt or dt == math.huge or dt == -math.huge or dt < 0 then dt = 0 end
    if dt > COMPLETION_TOTAL_T then dt = COMPLETION_TOTAL_T end
    local any_active = false
    local needs_sync = false
    for i = 1, MAX_SLOTS do
        local c = self._slot_completion[i]
        if c then
            if c.active then
                any_active = true
                c.elapsed = c.elapsed + dt
                if c.elapsed + 1e-6 >= COMPLETION_PULSE_T and not c.has_successor_pending then
                    local entries = self:select_visible()
                    if entries then
                        local snapshot = c.displayed_snapshot or {}
                        local has_new_entry = false
                        for _, e in ipairs(entries) do
                            if not snapshot[e.id] then
                                local found = false
                                for _, snap_e in pairs(snapshot) do
                                    if snap_e.id == e.id then
                                        found = true
                                        break
                                    end
                                end
                                if not found and self._by_id[e.id] then
                                    has_new_entry = true
                                    c.successor_pending_entry = e
                                    break
                                end
                            end
                        end
                        if has_new_entry then
                            c.has_successor_pending = true
                            c.coordinated_slide_active = true
                        end
                    end
                end
                if c.has_successor_pending and c.successor_pending_entry then
                    if not self._by_id[c.successor_pending_entry.id] then
                        c.has_successor_pending = false
                        c.successor_pending_entry = nil
                        c.coordinated_slide_active = false
                    end
                end
                if c.elapsed + 1e-6 >= COMPLETION_TOTAL_T then
                    if self._coordinated_slide_extra then
                        local extra = self._coordinated_slide_extra
                        if extra.text and mount_panel_alive(extra.text) then
                            mount_safe_call(extra.text, "set_visible", false)
                            mount_safe_call(extra.text, "set_text", "")
                        end
                        if extra.amount and mount_panel_alive(extra.amount) then
                            mount_safe_call(extra.amount, "set_visible", false)
                            mount_safe_call(extra.amount, "set_text", "")
                        end
                    end
                    self:_clear_completion_slot(i)
                    self._coordinated_slide_slots = nil
                    needs_sync = true
                else
                    self:_render_completion_slot(i)
                end
            elseif c.successor_entry then
                any_active = true
                c.entry_elapsed = (c.entry_elapsed or 0) + dt
                if c.entry_elapsed >= COMPLETION_EXIT_T then
                    c.entry_elapsed = COMPLETION_EXIT_T
                    c.successor_entry = false
                    needs_sync = true
                end
                self:_render_completion_slot(i)
            end
        end
    end
    if needs_sync and not self._sync_in_progress then
        self._sync_in_progress = true
        self:_update_layout()
        self:_sync_primitives()
        self._sync_in_progress = false
    end
    if any_active then
        if not self:_verify_render() then
            self:_release_native()
        end
    end
end

function O:_was_entry_in_siblings(entry_id, siblings_displayed)
    if not entry_id or type(siblings_displayed) ~= "table" then return false end
    for _, sib_id in pairs(siblings_displayed) do
        if sib_id == entry_id then return true end
    end
    return false
end

function O:_compact_successor(i, entry)
    local c = self._slot_completion[i]
    local slot = self._slot_prims[i]
    if not slot then
        if c then self._slot_completion[i] = nil end
        return
    end
    local ly = self._layout_cache
    if not ly then
        if c then self._slot_completion[i] = nil end
        return
    end
    local source_text = (entry and type(entry.text) == "string") and entry.text or ""
    local text_w = ly.root_w * 0.7
    local row_h = ly.row_h
    local display_text = source_text
    local fitted_w = 0
    local fitted_h = 0
    if slot.text and mount_panel_alive(slot.text) then
        display_text, fitted_w, fitted_h = self:_compute_fitted_display(slot.text, source_text, text_w, row_h)
        if not mount_is_finite(fitted_w) then fitted_w = 0 end
        if not mount_is_finite(fitted_h) then fitted_h = 0 end
    end
    local amount_text = mount_format_amount(entry)
    local sig = o_layout_fit_sig(ly)
    if slot.text and mount_panel_alive(slot.text) then
        self._slot_fit_cache[i] = {
            source = source_text,
            sig = sig,
            prim = slot.text,
            display = display_text,
            measured_w = fitted_w,
            measured_h = fitted_h,
        }
    end
    local title_y = (i - 1) * row_h
    if slot.text and mount_panel_alive(slot.text) then
        mount_safe_call(slot.text, "set_text", display_text)
        mount_safe_call(slot.text, "set_visible", true)
        mount_safe_call(slot.text, "set_color", HUD_DEFAULT_COLOR)
        mount_safe_call(slot.text, "set_alpha", 1)
        mount_safe_call(slot.text, "set_y", title_y)
    end
    if slot.amount and mount_panel_alive(slot.amount) then
        local amt = amount_text or ""
        mount_safe_call(slot.amount, "set_text", amt)
        mount_safe_call(slot.amount, "set_visible", amt ~= "")
        mount_safe_call(slot.amount, "set_color", HUD_DEFAULT_COLOR)
        mount_safe_call(slot.amount, "set_alpha", 1)
        mount_safe_call(slot.amount, "set_y", title_y)
    end
    if slot.strike and mount_panel_alive(slot.strike) then
        local ok_w, aw = pcall(function() return slot.strike:w() end)
        if not ok_w or aw ~= 0 then
            mount_safe_call(slot.strike, "set_w", 0)
        end
        mount_safe_call(slot.strike, "set_visible", false)
    end
    self._slot_completion[i] = nil
end

function O:_start_successor_entry(i, entry)
    local c = self._slot_completion[i]
    if not c then return end
    local slot = self._slot_prims[i]
    if not slot then return end
    local ly = self._layout_cache
    if not ly then return end
    local source_text = (entry and type(entry.text) == "string") and entry.text or ""
    local text_w = ly.root_w * 0.7
    local row_h = ly.row_h
    local display_text = source_text
    local fitted_w = 0
    local fitted_h = 0
    if slot.text and mount_panel_alive(slot.text) then
        display_text, fitted_w, fitted_h = self:_compute_fitted_display(slot.text, source_text, text_w, row_h)
        if not mount_is_finite(fitted_w) then fitted_w = 0 end
        if not mount_is_finite(fitted_h) then fitted_h = 0 end
    end
    local amount_text = mount_format_amount(entry)
    c.successor_entry = true
    c.successor_entry_id = entry and entry.id or nil
    c.entry_elapsed = 0
    c.successor_text = source_text
    c.successor_display = display_text
    c.successor_fitted_w = fitted_w
    c.successor_fitted_h = fitted_h
    c.successor_amount = amount_text
    local sig = o_layout_fit_sig(ly)
    if slot.text and mount_panel_alive(slot.text) then
        self._slot_fit_cache[i] = {
            source = source_text,
            sig = sig,
            prim = slot.text,
            display = display_text,
            measured_w = fitted_w,
            measured_h = fitted_h,
        }
    end
    if slot.text and mount_panel_alive(slot.text) then
        mount_safe_call(slot.text, "set_text", display_text)
        mount_safe_call(slot.text, "set_visible", true)
        mount_safe_call(slot.text, "set_alpha", 0)
        mount_safe_call(slot.text, "set_y", c.title_y_base + COMPLETION_RISE)
    end
    if slot.amount and mount_panel_alive(slot.amount) then
        local amt = amount_text or ""
        mount_safe_call(slot.amount, "set_text", amt)
        mount_safe_call(slot.amount, "set_visible", amt ~= "")
        mount_safe_call(slot.amount, "set_alpha", 0)
        mount_safe_call(slot.amount, "set_y", c.amount_y_base + COMPLETION_RISE)
    end
    if slot.strike and mount_panel_alive(slot.strike) then
        mount_safe_call(slot.strike, "set_visible", false)
    end
end

function O:_ensure_coordinated_slide_extra()
    if not self._root_panel or not mount_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    local font = mount_get_font()
    if not font then return end
    local layout = self._layout_cache
    local text_w = layout.root_w * 0.7
    local amount_w = layout.root_w - text_w
    local extra = self._coordinated_slide_extra
    if extra then
        local needs_relayout = false
        if extra._layout_sig ~= o_layout_fit_sig(layout) then
            needs_relayout = true
        end
        if needs_relayout then
            if extra.text and mount_panel_alive(extra.text) then
                mount_safe_call(extra.text, "set_shape", 0, -layout.row_h, text_w, layout.row_h)
                mount_safe_call(extra.text, "set_font_size", layout.font_size)
            end
            if extra.amount and mount_panel_alive(extra.amount) then
                mount_safe_call(extra.amount, "set_shape", text_w, -layout.row_h, amount_w, layout.row_h)
                mount_safe_call(extra.amount, "set_font_size", layout.font_size)
            end
            extra._layout_sig = o_layout_fit_sig(layout)
        end
        return
    end
    extra = {}
    local status, prim = mount_safe_call(self._root_panel, "text", {
        name = "objective_extra_text",
        text = "",
        font = font,
        font_size = layout.font_size,
        color = Color(1, 1, 1, 1),
        x = 0,
        y = -layout.row_h,
        w = text_w,
        h = layout.row_h,
        align = "left",
        vertical = "center",
        wrap = false,
        word_wrap = false,
        layer = 1,
        visible = false,
    })
    if status == MOUNT_CALL_OK and prim then
        extra.text = prim
    end
    status, prim = mount_safe_call(self._root_panel, "text", {
        name = "objective_extra_amount",
        text = "",
        font = font,
        font_size = layout.font_size,
        color = Color(1, 1, 1, 1),
        x = text_w,
        y = -layout.row_h,
        w = amount_w,
        h = layout.row_h,
        align = "right",
        vertical = "center",
        wrap = false,
        word_wrap = false,
        layer = 1,
        visible = false,
    })
    if status == MOUNT_CALL_OK and prim then
        extra.amount = prim
    end
    extra._layout_sig = o_layout_fit_sig(layout)
    self._coordinated_slide_extra = extra
end

function O:_render_coordinated_slide_history(completion_slot_idx, c, eased_exit)
    if not c.displayed_snapshot then return end
    local ly = self._layout_cache
    if not ly then return end
    local snapshot = c.displayed_snapshot
    local history_snapshot = c.history_slots_snapshot or {}
    local _vis_limit = kyohud.settings and kyohud.settings.objectives_visible_limit
    if _vis_limit == nil then _vis_limit = 1 end
    if type(_vis_limit) ~= "number" then _vis_limit = 1 end
    if _vis_limit ~= _vis_limit then _vis_limit = 1 end
    if _vis_limit == math.huge or _vis_limit == -math.huge then _vis_limit = 1 end
    if math.floor(_vis_limit) ~= _vis_limit then _vis_limit = 1 end
    _vis_limit = math.floor(_vis_limit)
    if _vis_limit < 1 then _vis_limit = 1 end
    if _vis_limit > MAX_SLOTS then _vis_limit = MAX_SLOTS end
    for si = 1, MAX_SLOTS do
        if si == completion_slot_idx then goto continue end
        local snap_entry = snapshot[si]
        if not snap_entry then goto continue end
        local slot = self._slot_prims[si]
        if not slot then goto continue end
        local is_history = history_snapshot[si] == true
        local should_fade = is_history and (si + 1 > _vis_limit)
        local source_text = snap_entry.text or ""
        local text_w = ly.root_w * 0.7
        local row_h = ly.row_h
        local display_text = source_text
        if slot.text and mount_panel_alive(slot.text) then
            display_text = select(1, self:_compute_fitted_display(slot.text, source_text, text_w, row_h))
            local ok_r, actual = pcall(function() return slot.text:text() end)
            if not ok_r or actual ~= display_text then
                mount_safe_call(slot.text, "set_text", display_text)
            end
            mount_safe_call(slot.text, "set_visible", true)
            local base_y = (si - 1) * row_h
            local target_y = base_y + row_h * eased_exit
            local ok_y, act_y = pcall(function() return slot.text:y() end)
            if not ok_y or math.abs(act_y - target_y) > 0.5 then
                mount_safe_call(slot.text, "set_y", target_y)
            end
            local t_alpha = COMPLETION_HISTORY_ALPHA
            if should_fade then
                t_alpha = COMPLETION_HISTORY_ALPHA * (1.0 - eased_exit)
            end
            local ok_a, act_a = pcall(function() return slot.text:alpha() end)
            if not ok_a or math.abs(act_a - t_alpha) > 0.01 then
                mount_safe_call(slot.text, "set_alpha", t_alpha)
            end
            local ok_c, cc = pcall(function() return slot.text:color() end)
            if not ok_c or not o_color_matches_ref(cc, HUD_DEFAULT_COLOR) then
                mount_safe_call(slot.text, "set_color", HUD_DEFAULT_COLOR)
            end
        end
        if slot.amount and mount_panel_alive(slot.amount) then
            local amt_text = ""
            if not is_history and snap_entry.amount then
                if snap_entry.countdown then
                    amt_text = math.floor(snap_entry.amount - (snap_entry.current_amount or 0)) .. "/" .. math.floor(snap_entry.amount)
                else
                    amt_text = math.floor(snap_entry.current_amount or 0) .. "/" .. math.floor(snap_entry.amount)
                end
            end
            local ok_r, actual = pcall(function() return slot.amount:text() end)
            if not ok_r or actual ~= amt_text then
                mount_safe_call(slot.amount, "set_text", amt_text)
            end
            local should_show = amt_text ~= ""
            local ok_vs, act_vs = pcall(function() return slot.amount:visible() end)
            if ok_vs and act_vs ~= should_show then
                mount_safe_call(slot.amount, "set_visible", should_show)
            end
            local base_y = (si - 1) * row_h
            local target_y = base_y + row_h * eased_exit
            local ok_y, act_y = pcall(function() return slot.amount:y() end)
            if not ok_y or math.abs(act_y - target_y) > 0.5 then
                mount_safe_call(slot.amount, "set_y", target_y)
            end
            local a_alpha = COMPLETION_HISTORY_ALPHA
            if should_fade then
                a_alpha = COMPLETION_HISTORY_ALPHA * (1.0 - eased_exit)
            end
            local ok_a, act_a = pcall(function() return slot.amount:alpha() end)
            if not ok_a or math.abs(act_a - a_alpha) > 0.01 then
                mount_safe_call(slot.amount, "set_alpha", a_alpha)
            end
        end
        ::continue::
    end
end

function O:_render_coordinated_slide_new_current(completion_slot_idx, c, eased_exit)
    if not c.successor_pending_entry then return end
    self:_ensure_coordinated_slide_extra()
    local extra = self._coordinated_slide_extra
    if not extra then return end
    local ly = self._layout_cache
    if not ly then return end
    local entry = c.successor_pending_entry
    local source_text = entry.text or ""
    local text_w = ly.root_w * 0.7
    local row_h = ly.row_h
    local display_text = source_text
    if extra.text and mount_panel_alive(extra.text) then
        display_text = select(1, self:_compute_fitted_display(extra.text, source_text, text_w, row_h))
        extra._fit_source = source_text
        extra._fit_sig = o_layout_fit_sig(ly)
        extra._fit_display = display_text
    end
    local amount_text = mount_format_amount(entry) or ""
    if extra.text and mount_panel_alive(extra.text) then
        local ok_r, actual = pcall(function() return extra.text:text() end)
        if not ok_r or actual ~= display_text then
            mount_safe_call(extra.text, "set_text", display_text)
        end
        mount_safe_call(extra.text, "set_visible", true)
        local start_y = -row_h
        local end_y = 0
        local target_y = start_y + (end_y - start_y) * eased_exit
        local ok_y, act_y = pcall(function() return extra.text:y() end)
        if not ok_y or math.abs(act_y - target_y) > 0.5 then
            mount_safe_call(extra.text, "set_y", target_y)
        end
        local t_alpha = eased_exit
        local ok_a, act_a = pcall(function() return extra.text:alpha() end)
        if not ok_a or math.abs(act_a - t_alpha) > 0.01 then
            mount_safe_call(extra.text, "set_alpha", t_alpha)
        end
        local ok_c, cc = pcall(function() return extra.text:color() end)
        if not ok_c or not o_color_matches_ref(cc, HUD_DEFAULT_COLOR) then
            mount_safe_call(extra.text, "set_color", HUD_DEFAULT_COLOR)
        end
    end
    if extra.amount and mount_panel_alive(extra.amount) then
        local ok_r, actual = pcall(function() return extra.amount:text() end)
        if not ok_r or actual ~= amount_text then
            mount_safe_call(extra.amount, "set_text", amount_text)
        end
        local should_show = amount_text ~= ""
        local ok_vs, act_vs = pcall(function() return extra.amount:visible() end)
        if ok_vs and act_vs ~= should_show then
            mount_safe_call(extra.amount, "set_visible", should_show)
        end
        local start_y = -row_h
        local end_y = 0
        local target_y = start_y + (end_y - start_y) * eased_exit
        local ok_y, act_y = pcall(function() return extra.amount:y() end)
        if not ok_y or math.abs(act_y - target_y) > 0.5 then
            mount_safe_call(extra.amount, "set_y", target_y)
        end
        local a_alpha = eased_exit
        local ok_a, act_a = pcall(function() return extra.amount:alpha() end)
        if not ok_a or math.abs(act_a - a_alpha) > 0.01 then
            mount_safe_call(extra.amount, "set_alpha", a_alpha)
        end
    end
end

function O:_render_completion_slot(i)
    local c = self._slot_completion[i]
    if not c then return false end
    local slot = self._slot_prims[i]
    if not slot then
        if not c.active then self._slot_completion[i] = nil end
        return true
    end
    if not c.active then
        if c.successor_entry == nil then
            local displayed, history_slots = self:_compute_displayed_entries()
            if not displayed then displayed = {} end
            if not history_slots then history_slots = {} end
            local entry = displayed[i]
            local is_history = history_slots[i] == true
            if entry then
                if is_history then
                    self:_clear_completion_slot(i)
                    return true
                elseif self:_was_entry_in_siblings(entry.id, c.siblings_displayed) then
                    self:_compact_successor(i, entry)
                    return true
                else
                    self:_start_successor_entry(i, entry)
                end
            else
                self:_clear_completion_slot(i)
                return true
            end
        elseif not c.successor_entry then
            local slot = self._slot_prims[i]
            if slot then
                if slot.text and mount_panel_alive(slot.text) then
                    local display = c.successor_display or c.successor_text or ""
                    local ok_r, actual = pcall(function() return slot.text:text() end)
                    if not ok_r or actual ~= display then
                        mount_safe_call(slot.text, "set_text", display)
                    end
                    mount_safe_call(slot.text, "set_color", HUD_DEFAULT_COLOR)
                    mount_safe_call(slot.text, "set_alpha", 1)
                    mount_safe_call(slot.text, "set_y", c.title_y_base)
                    mount_safe_call(slot.text, "set_visible", true)
                end
                if slot.amount and mount_panel_alive(slot.amount) then
                    local amt = c.successor_amount or ""
                    local ok_r, actual = pcall(function() return slot.amount:text() end)
                    if not ok_r or actual ~= amt then
                        mount_safe_call(slot.amount, "set_text", amt)
                    end
                    local should_show = amt ~= ""
                    local ok_vs, act_vs = pcall(function() return slot.amount:visible() end)
                    if ok_vs and act_vs ~= should_show then
                        mount_safe_call(slot.amount, "set_visible", should_show)
                    end
                    mount_safe_call(slot.amount, "set_color", HUD_DEFAULT_COLOR)
                    mount_safe_call(slot.amount, "set_alpha", 1)
                    mount_safe_call(slot.amount, "set_y", c.amount_y_base)
                end
                if slot.strike and mount_panel_alive(slot.strike) then
                    local ok_w, aw = pcall(function() return slot.strike:w() end)
                    if not ok_w or aw ~= 0 then
                        mount_safe_call(slot.strike, "set_w", 0)
                    end
                    mount_safe_call(slot.strike, "set_visible", false)
                end
            end
            self._slot_completion[i] = nil
            return true
        end
    end
    if c.successor_entry then
        local progress = (c.entry_elapsed or 0) / COMPLETION_EXIT_T
        if progress < 0 then progress = 0 end
        if progress > 1 then progress = 1 end
        local eased = o_smoothstep(progress)
        local alpha = eased
        local y_offset = COMPLETION_RISE * (1.0 - eased)
        if slot.text and mount_panel_alive(slot.text) then
            local display = c.successor_display or c.successor_text or ""
            local ok_r, actual = pcall(function() return slot.text:text() end)
            if not ok_r or actual ~= display then
                mount_safe_call(slot.text, "set_text", display)
            end
            mount_safe_call(slot.text, "set_visible", true)
            local ok_a, act_a = pcall(function() return slot.text:alpha() end)
            if not ok_a or math.abs(act_a - alpha) > 0.01 then
                mount_safe_call(slot.text, "set_alpha", alpha)
            end
            local t_y = c.title_y_base + y_offset
            local ok_y, act_y = pcall(function() return slot.text:y() end)
            if not ok_y or math.abs(act_y - t_y) > 0.5 then
                mount_safe_call(slot.text, "set_y", t_y)
            end
        end
        if slot.amount and mount_panel_alive(slot.amount) then
            local amt = c.successor_amount or ""
            local ok_r, actual = pcall(function() return slot.amount:text() end)
            if not ok_r or actual ~= amt then
                mount_safe_call(slot.amount, "set_text", amt)
            end
            local should_show = amt ~= ""
            local ok_vs, act_vs = pcall(function() return slot.amount:visible() end)
            if ok_vs and act_vs ~= should_show then
                mount_safe_call(slot.amount, "set_visible", should_show)
            end
            local ok_a, act_a = pcall(function() return slot.amount:alpha() end)
            if not ok_a or math.abs(act_a - alpha) > 0.01 then
                mount_safe_call(slot.amount, "set_alpha", alpha)
            end
            local a_y = c.amount_y_base + y_offset
            local ok_y, act_y = pcall(function() return slot.amount:y() end)
            if not ok_y or math.abs(act_y - a_y) > 0.5 then
                mount_safe_call(slot.amount, "set_y", a_y)
            end
        end
        if slot.strike and mount_panel_alive(slot.strike) then
            local ok_vs, act_vs = pcall(function() return slot.strike:visible() end)
            if ok_vs and act_vs ~= false then
                mount_safe_call(slot.strike, "set_visible", false)
            end
        end
        return true
    end
    local ly = self._layout_cache
    if not ly then return false end
    local sig = o_layout_fit_sig(ly)
    if c.fit_sig ~= sig and slot.text and mount_panel_alive(slot.text) then
        local text_w = ly.root_w * 0.7
        local row_h = ly.row_h
        local display, fw = self:_compute_fitted_display(slot.text, c.source_text, text_w, row_h)
        c.display_text = display
        if mount_is_finite(fw) then c.fitted_w = fw else c.fitted_w = 0 end
        c.fit_sig = sig
        c.title_y_base = (i - 1) * row_h
        c.amount_y_base = (i - 1) * row_h
        local strike_h = 1
        c.strike_y_base = c.title_y_base + (row_h - strike_h) / 2
    end
    local elapsed = c.elapsed
    local p1 = elapsed + 1e-6 < COMPLETION_PULSE_T
    local p2_progress = 0
    if not p1 then
        p2_progress = (elapsed - COMPLETION_PULSE_T) / COMPLETION_EXIT_T
        if p2_progress < 0 then p2_progress = 0 end
        if p2_progress > 1 then p2_progress = 1 end
    end
    local eased_exit = o_smoothstep(p2_progress)
    local pulse_a = o_pulse_alpha(elapsed)
    local is_coordinated = c.coordinated_slide_active == true
    local current_color = HUD_ACCENT_COLOR
    if slot.text and mount_panel_alive(slot.text) then
        local display = c.display_text or c.source_text or ""
        local ok_r, actual = pcall(function() return slot.text:text() end)
        if not ok_r or actual ~= display then
            mount_safe_call(slot.text, "set_text", display)
        end
        mount_safe_call(slot.text, "set_visible", true)
        local ok_c, cc = pcall(function() return slot.text:color() end)
        if not ok_c or not o_color_matches_ref(cc, current_color) then
            mount_safe_call(slot.text, "set_color", current_color)
        end
        local t_alpha = 1.0
        if is_coordinated and not p1 then
            t_alpha = 1.0 - (1.0 - COMPLETION_HISTORY_ALPHA) * eased_exit
        elseif not p1 then
            t_alpha = pulse_a * (1.0 - eased_exit)
        end
        local ok_a, act_a = pcall(function() return slot.text:alpha() end)
        if not ok_a or math.abs(act_a - t_alpha) > 0.01 then
            mount_safe_call(slot.text, "set_alpha", t_alpha)
        end
        local t_y = c.title_y_base
        if is_coordinated and not p1 then
            t_y = c.title_y_base + ly.row_h * eased_exit
        elseif not p1 then
            t_y = c.title_y_base - COMPLETION_RISE * eased_exit
        end
        local ok_y, act_y = pcall(function() return slot.text:y() end)
        if not ok_y or math.abs(act_y - t_y) > 0.5 then
            mount_safe_call(slot.text, "set_y", t_y)
        end
    end
    if slot.amount and mount_panel_alive(slot.amount) then
        local amt = c.amount_text or ""
        local ok_r, actual = pcall(function() return slot.amount:text() end)
        if not ok_r or actual ~= amt then
            mount_safe_call(slot.amount, "set_text", amt)
        end
        local should_show = amt ~= ""
        local ok_vs, act_vs = pcall(function() return slot.amount:visible() end)
        if ok_vs and act_vs ~= should_show then
            mount_safe_call(slot.amount, "set_visible", should_show)
        end
        local ok_c, cc = pcall(function() return slot.amount:color() end)
        if not ok_c or not o_color_matches_ref(cc, current_color) then
            mount_safe_call(slot.amount, "set_color", current_color)
        end
        local a_alpha = COMPLETION_AMOUNT_DIM
        if is_coordinated and not p1 then
            a_alpha = COMPLETION_AMOUNT_DIM * (1.0 - (1.0 - COMPLETION_HISTORY_ALPHA) * eased_exit)
        elseif not p1 then
            a_alpha = pulse_a * COMPLETION_AMOUNT_DIM * (1.0 - eased_exit)
        end
        local ok_a, act_a = pcall(function() return slot.amount:alpha() end)
        if not ok_a or math.abs(act_a - a_alpha) > 0.01 then
            mount_safe_call(slot.amount, "set_alpha", a_alpha)
        end
        local a_y = c.amount_y_base
        if is_coordinated and not p1 then
            a_y = c.amount_y_base + ly.row_h * eased_exit
        elseif not p1 then
            a_y = c.amount_y_base - COMPLETION_RISE * eased_exit
        end
        local ok_y, act_y = pcall(function() return slot.amount:y() end)
        if not ok_y or math.abs(act_y - a_y) > 0.5 then
            mount_safe_call(slot.amount, "set_y", a_y)
        end
    end
    if slot.strike and mount_panel_alive(slot.strike) then
        local ok_w, aw = pcall(function() return slot.strike:w() end)
        if not ok_w or aw ~= 0 then
            mount_safe_call(slot.strike, "set_w", 0)
        end
        local ok_vs, act_vs = pcall(function() return slot.strike:visible() end)
        if ok_vs and act_vs ~= false then
            mount_safe_call(slot.strike, "set_visible", false)
        end
    end
    if c.displayed_snapshot and next(c.displayed_snapshot) then
        if is_coordinated and not p1 then
            self:_render_coordinated_slide_history(i, c, eased_exit)
            self:_render_coordinated_slide_new_current(i, c, eased_exit)
        else
            self:_render_coordinated_slide_history(i, c, 0)
        end
        self._coordinated_slide_slots = {}
        local snapshot = c.displayed_snapshot or {}
        for si = 1, MAX_SLOTS do
            if snapshot[si] then
                self._coordinated_slide_slots[si] = true
            end
        end
    else
        self._coordinated_slide_slots = nil
    end
    return true
end

function O:_clear_slot_prims()
    for i = 1, MAX_SLOTS do
        self._slot_prims[i] = nil
        self._slot_text_cache[i] = nil
        self._slot_amount_cache[i] = nil
        self._slot_fit_cache[i] = nil
        self._slot_visible_cache[i .. "_text"] = nil
        self._slot_visible_cache[i .. "_amount"] = nil
        self._slot_completion[i] = nil
    end
    if self._coordinated_slide_extra then
        local extra = self._coordinated_slide_extra
        if extra.text and mount_panel_alive(extra.text) then
            local parent = extra.text:parent()
            if parent and mount_panel_alive(parent) then
                mount_safe_call(parent, "remove", extra.text)
            end
        end
        if extra.amount and mount_panel_alive(extra.amount) then
            local parent = extra.amount:parent()
            if parent and mount_panel_alive(parent) then
                mount_safe_call(parent, "remove", extra.amount)
            end
        end
        self._coordinated_slide_extra = nil
    end
end

function O:_ensure_slot_prims()
    if not self._root_panel or not mount_panel_alive(self._root_panel) then return end
    if not self._layout_cache then return end
    local font = mount_get_font()
    if not font then return end
    local layout = self._layout_cache

    for i = 1, MAX_SLOTS do
        local slot = self._slot_prims[i]
        if not slot then
            slot = {}
            self._slot_prims[i] = slot
        end

        local y = (i - 1) * layout.row_h
        local text_w = layout.root_w * 0.7
        local amount_w = layout.root_w - text_w

        if not slot.text or not mount_panel_alive(slot.text) then
            slot.text = nil
            self._slot_text_cache[i] = nil
            local status, prim = mount_safe_call(self._root_panel, "text", {
                name = "objective_" .. i .. "_text",
                text = "",
                font = font,
                font_size = layout.font_size,
                color = Color(1, 1, 1, 1),
                x = 0,
                y = y,
                w = text_w,
                h = layout.row_h,
                align = "left",
                vertical = "center",
                wrap = false,
                word_wrap = false,
                layer = 1,
            })
            if status == MOUNT_CALL_OK and prim then
                slot.text = prim
            end
        end

        if not slot.amount or not mount_panel_alive(slot.amount) then
            slot.amount = nil
            self._slot_amount_cache[i] = nil
            local status, prim = mount_safe_call(self._root_panel, "text", {
                name = "objective_" .. i .. "_amount",
                text = "",
                font = font,
                font_size = layout.font_size,
                color = Color(1, 1, 1, 1),
                x = text_w,
                y = y,
                w = amount_w,
                h = layout.row_h,
                align = "right",
                vertical = "center",
                wrap = false,
                word_wrap = false,
                layer = 1,
            })
            if status == MOUNT_CALL_OK and prim then
                slot.amount = prim
            end
        end
    end
end

function O:_sync_primitives()
    if not self._root_panel or not mount_panel_alive(self._root_panel) then
        self:_release_native()
        return
    end
    if not self._layout_cache then
        self:_release_native()
        return
    end

    local displayed, history_slots = self:_compute_displayed_entries()
    if not displayed then displayed = {} end
    if not history_slots then history_slots = {} end

    local layout = self._layout_cache
    local sig = o_layout_fit_sig(layout)

    for i = 1, MAX_SLOTS do
        local entry = displayed[i]
        local slot = self._slot_prims[i]
        if not slot then goto sync_continue end
        if self._slot_completion[i] then
            goto sync_continue
        end
        if self._coordinated_slide_slots and self._coordinated_slide_slots[i] then
            goto sync_continue
        end

        local is_history = history_slots[i] == true
        local text_str = (entry and type(entry.text) == "string") and entry.text or ""
        local amount_str = nil
        if not is_history then
            amount_str = entry and mount_format_amount(entry) or nil
        end

        if slot.text and mount_panel_alive(slot.text) then
            local text_w = layout.root_w * 0.7
            local row_h = layout.row_h

            local fit = self._slot_fit_cache[i]
            local need_fit = not fit
                or fit.source ~= text_str
                or fit.sig ~= sig
                or fit.prim ~= slot.text

            if need_fit then
                local display, mw, mh = self:_compute_fitted_display(slot.text, text_str, text_w, row_h)
                local ok_read, actual = pcall(function() return slot.text:text() end)
                if ok_read and actual == display then
                    self._slot_fit_cache[i] = {
                        source = text_str,
                        sig = sig,
                        prim = slot.text,
                        display = display,
                        measured_w = mw,
                        measured_h = mh,
                    }
                    self._slot_text_cache[i] = display
                    fit = self._slot_fit_cache[i]
                end
            end

            if fit then
                local display = fit.display

                local ok_read_text, actual_text = pcall(function() return slot.text:text() end)
                if ok_read_text and actual_text == display then
                    self._slot_text_cache[i] = display
                else
                    local st, _ = mount_safe_call(slot.text, "set_text", display)
                    if st == MOUNT_CALL_OK then
                        local ok_read2, actual2 = pcall(function() return slot.text:text() end)
                        if ok_read2 and actual2 == display then
                            self._slot_text_cache[i] = display
                        end
                    end
                end
                local should_show = entry ~= nil and text_str ~= ""
                local cache_key = i .. "_text"
                local ok_read, actual = pcall(function() return slot.text:visible() end)
                if ok_read and type(actual) == "boolean" and actual == should_show then
                    self._slot_visible_cache[cache_key] = should_show
                else
                    local st, _ = mount_safe_call(slot.text, "set_visible", should_show)
                    if st == MOUNT_CALL_OK then
                        local ok_read2, actual2 = pcall(function() return slot.text:visible() end)
                        if ok_read2 and type(actual2) == "boolean" and actual2 == should_show then
                            self._slot_visible_cache[cache_key] = should_show
                        end
                    end
                end
                local target_alpha = is_history and COMPLETION_HISTORY_ALPHA or 1.0
                local ok_a, act_a = pcall(function() return slot.text:alpha() end)
                if ok_a and mount_is_finite(act_a) and math.abs(act_a - target_alpha) < 0.01 then
                else
                    mount_safe_call(slot.text, "set_alpha", target_alpha)
                end
                local ok_c, cc = pcall(function() return slot.text:color() end)
                if not ok_c or not o_color_matches_ref(cc, HUD_DEFAULT_COLOR) then
                    mount_safe_call(slot.text, "set_color", HUD_DEFAULT_COLOR)
                end
            end
        end

        if slot.amount and mount_panel_alive(slot.amount) then
            local amt_text = amount_str or ""
            local ok_read_amt, actual_amt = pcall(function() return slot.amount:text() end)
            if ok_read_amt and actual_amt == amt_text then
                self._slot_amount_cache[i] = amt_text
            else
                local st, _ = mount_safe_call(slot.amount, "set_text", amt_text)
                if st == MOUNT_CALL_OK then
                    local ok_read2, actual2 = pcall(function() return slot.amount:text() end)
                    if ok_read2 and actual2 == amt_text then
                        self._slot_amount_cache[i] = amt_text
                    end
                end
            end
            local should_show = amount_str ~= nil
            local cache_key = i .. "_amount"
            local ok_read, actual = pcall(function() return slot.amount:visible() end)
            if ok_read and type(actual) == "boolean" and actual == should_show then
                self._slot_visible_cache[cache_key] = should_show
            else
                local st, _ = mount_safe_call(slot.amount, "set_visible", should_show)
                if st == MOUNT_CALL_OK then
                    local ok_read2, actual2 = pcall(function() return slot.amount:visible() end)
                    if ok_read2 and type(actual2) == "boolean" and actual2 == should_show then
                        self._slot_visible_cache[cache_key] = should_show
                    end
                end
            end
            local ok_c, cc = pcall(function() return slot.amount:color() end)
            if not ok_c or not o_color_matches_ref(cc, HUD_DEFAULT_COLOR) then
                mount_safe_call(slot.amount, "set_color", HUD_DEFAULT_COLOR)
            end
        end

        ::sync_continue::
    end
    self:_sync_native_visibility()
end

function O:_update_layout()
    if not self._root_panel or not mount_panel_alive(self._root_panel) then
        self._layout_cache = nil
        return
    end
    if not self._parent_panel or not mount_panel_alive(self._parent_panel) then
        self._layout_cache = nil
        return
    end
    local pw_s, pw = mount_safe_call(self._parent_panel, "w")
    local ph_s, ph = mount_safe_call(self._parent_panel, "h")
    if pw_s ~= MOUNT_CALL_OK or ph_s ~= MOUNT_CALL_OK then
        self._layout_cache = nil
        return
    end
    if not mount_is_finite(pw) or not mount_is_finite(ph) then
        self._layout_cache = nil
        return
    end
    if pw <= 0 or ph <= 0 then
        self._layout_cache = nil
        return
    end
    local new_layout = self:_compute_layout(pw, ph)
    if not new_layout then
        self._layout_cache = nil
        return
    end
    local tol = 0.5
    local desired_changed = not self._layout_cache or
        self._layout_cache.root_x ~= new_layout.root_x or
        self._layout_cache.root_y ~= new_layout.root_y or
        self._layout_cache.root_w ~= new_layout.root_w or
        self._layout_cache.root_h ~= new_layout.root_h or
        self._layout_cache.font_size ~= new_layout.font_size

    local primitives_match = true
    if not desired_changed then
        local root_ok, rx, ry, rw, rh = o_read_prim_shape(self._root_panel)
        if not root_ok or not o_shape_matches(rx, ry, rw, rh,
            new_layout.root_x, new_layout.root_y, new_layout.root_w, new_layout.root_h, tol) then
            primitives_match = false
        else
            for i = 1, MAX_SLOTS do
                local slot = self._slot_prims[i]
                if slot then
                    if self._slot_completion[i] then
                        -- Skip geometry checks for completion-animated slots
                    elseif self._coordinated_slide_slots and self._coordinated_slide_slots[i] then
                        -- Skip geometry checks for coordinated slide slots (they are moving)
                    else
                        local y = (i - 1) * new_layout.row_h
                        local text_w = new_layout.root_w * 0.7
                        local amount_w = new_layout.root_w - text_w
                        if slot.text and mount_panel_alive(slot.text) then
                            local ok, sx, sy, sw, sh = o_read_prim_shape(slot.text)
                            if not ok or not o_shape_matches(sx, sy, sw, sh, 0, y, text_w, new_layout.row_h, tol) then
                                primitives_match = false
                                break
                            end
                            local ok_fs, fs = o_read_prim_font_size(slot.text)
                            if not ok_fs or math.abs(fs - new_layout.font_size) > 0.5 then
                                primitives_match = false
                                break
                            end
                        end
                        if slot.amount and mount_panel_alive(slot.amount) then
                            local ok, sx, sy, sw, sh = o_read_prim_shape(slot.amount)
                            if not ok or not o_shape_matches(sx, sy, sw, sh, text_w, y, amount_w, new_layout.row_h, tol) then
                                primitives_match = false
                                break
                            end
                            local ok_fs, fs = o_read_prim_font_size(slot.amount)
                            if not ok_fs or math.abs(fs - new_layout.font_size) > 0.5 then
                                primitives_match = false
                                break
                            end
                        end
                    end
                end
            end
        end
    end

    if not desired_changed and primitives_match then return end

    local rs = mount_safe_call(self._root_panel, "set_shape",
        new_layout.root_x, new_layout.root_y, new_layout.root_w, new_layout.root_h)
    if rs ~= MOUNT_CALL_OK then
        self._layout_cache = nil
        return
    end
    for i = 1, MAX_SLOTS do
        local slot = self._slot_prims[i]
        if slot then
            if self._slot_completion[i] then
                -- Completion slots handle their own layout via fit refit in _render_completion_slot
            elseif self._coordinated_slide_slots and self._coordinated_slide_slots[i] then
                -- Coordinated slide slots are animating; skip their layout mutation here
            else
                local y = (i - 1) * new_layout.row_h
                local text_w = new_layout.root_w * 0.7
                local amount_w = new_layout.root_w - text_w
                if slot.text and mount_panel_alive(slot.text) then
                    mount_safe_call(slot.text, "set_shape", 0, y, text_w, new_layout.row_h)
                    mount_safe_call(slot.text, "set_font_size", new_layout.font_size)
                end
                if slot.amount and mount_panel_alive(slot.amount) then
                    mount_safe_call(slot.amount, "set_shape", text_w, y, amount_w, new_layout.row_h)
                    mount_safe_call(slot.amount, "set_font_size", new_layout.font_size)
                end
            end
        end
    end

    if o_verify_geometry_after_apply(self, new_layout, tol) then
        self._layout_cache = new_layout
    else
        self._layout_cache = nil
    end
end

function O:_verify_render()
    if not self._layout_cache then return false end
    if not self._root_panel or not mount_panel_alive(self._root_panel) then return false end
    local geom = self._layout_cache
    if geom.root_w <= 0 or geom.root_h <= 0 or geom.font_size <= 0 then return false end

    local _vis_limit = kyohud.settings and kyohud.settings.objectives_visible_limit
    if _vis_limit == nil then _vis_limit = 1 end
    if type(_vis_limit) ~= "number" then _vis_limit = 1 end
    if _vis_limit ~= _vis_limit then _vis_limit = 1 end
    if _vis_limit == math.huge or _vis_limit == -math.huge then _vis_limit = 1 end
    if math.floor(_vis_limit) ~= _vis_limit then _vis_limit = 1 end
    _vis_limit = math.floor(_vis_limit)
    if _vis_limit < 1 then _vis_limit = 1 end
    if _vis_limit > MAX_SLOTS then _vis_limit = MAX_SLOTS end

    local ox_s, ox = mount_safe_call(self._root_panel, "x")
    local oy_s, oy = mount_safe_call(self._root_panel, "y")
    local ow_s, ow = mount_safe_call(self._root_panel, "w")
    local oh_s, oh = mount_safe_call(self._root_panel, "h")
    if ox_s ~= MOUNT_CALL_OK or oy_s ~= MOUNT_CALL_OK
        or ow_s ~= MOUNT_CALL_OK or oh_s ~= MOUNT_CALL_OK then
        return false
    end
    if not mount_is_finite(ox) or not mount_is_finite(oy)
        or not mount_is_finite(ow) or not mount_is_finite(oh) then
        return false
    end
    local tol = 0.5
    if math.abs(ox - geom.root_x) > tol or math.abs(oy - geom.root_y) > tol
        or math.abs(ow - geom.root_w) > tol or math.abs(oh - geom.root_h) > tol then
        return false
    end

    local ok_vis, vis = pcall(function() return self._root_panel:visible() end)
    if not ok_vis or type(vis) ~= "boolean" then
        return false
    end
    if vis ~= true then
        return false
    end

    local entries = O:select_visible()
    if not entries then entries = {} end
    for i = 1, MAX_SLOTS do
        local slot = self._slot_prims[i]
        if not slot then return false end
        if not slot.text or not mount_panel_alive(slot.text) then return false end
        if not slot.amount or not mount_panel_alive(slot.amount) then return false end
        local completion = self._slot_completion[i]
        if completion and completion.active then
            local elapsed = completion.elapsed
            local p1 = elapsed + 1e-6 < COMPLETION_PULSE_T
            local p2_progress = 0
            if not p1 then
                p2_progress = (elapsed - COMPLETION_PULSE_T) / COMPLETION_EXIT_T
                if p2_progress < 0 then p2_progress = 0 end
                if p2_progress > 1 then p2_progress = 1 end
            end
            local eased_exit = o_smoothstep(p2_progress)
            local expected_pulse = o_pulse_alpha(elapsed)
            local is_coordinated = completion.coordinated_slide_active == true
            local expected_color = HUD_ACCENT_COLOR

            local expected_display = completion.display_text or completion.source_text or ""
            local ok_t, t = pcall(function() return slot.text:text() end)
            if not ok_t or type(t) ~= "string" then return false end
            if t ~= expected_display then return false end
            local ok_v, v = pcall(function() return slot.text:visible() end)
            if not ok_v or type(v) ~= "boolean" then return false end
            if v ~= true then return false end
            local ok_fs, fs = pcall(function() return slot.text:font_size() end)
            if not ok_fs or not (mount_is_finite(fs) and fs > 0) then return false end
            if math.abs(fs - geom.font_size) > 0.5 then return false end
            local ok_c, c = pcall(function() return slot.text:color() end)
            if not ok_c or not o_color_matches_ref(c, expected_color) then return false end
            local text_w = geom.root_w * 0.7
            local expected_text_y = completion.title_y_base
            if is_coordinated and not p1 then
                expected_text_y = completion.title_y_base + geom.row_h * eased_exit
            elseif not p1 then
                expected_text_y = completion.title_y_base - COMPLETION_RISE * eased_exit
            end
            local tok, tx, ty, tw, th = o_read_prim_shape(slot.text)
            if not tok then return false end
            if math.abs(ty - expected_text_y) > tol then return false end
            if math.abs(tx) > tol then return false end
            if math.abs(tw - text_w) > tol then return false end
            if math.abs(th - geom.row_h) > tol then return false end
            local mok, mw, mh = o_measure_text_rect(slot.text)
            if not mok then return false end
            if mw > text_w + 1.0 then return false end
            if mh > geom.row_h + 1.0 then return false end
            local expected_t_alpha = 1.0
            if is_coordinated and not p1 then
                expected_t_alpha = 1.0 - (1.0 - COMPLETION_HISTORY_ALPHA) * eased_exit
            elseif not p1 then
                expected_t_alpha = expected_pulse * (1.0 - eased_exit)
            end
            local ok_ta, ta = pcall(function() return slot.text:alpha() end)
            if not ok_ta or not mount_is_finite(ta) then return false end
            if math.abs(ta - expected_t_alpha) > 0.05 then return false end

            local expected_amount = completion.amount_text or ""
            local ok_at, at = pcall(function() return slot.amount:text() end)
            if not ok_at or type(at) ~= "string" then return false end
            if at ~= expected_amount then return false end
            local ok_av, av = pcall(function() return slot.amount:visible() end)
            if not ok_av or type(av) ~= "boolean" then return false end
            local expected_amt_vis = expected_amount ~= ""
            if av ~= expected_amt_vis then return false end
            local ok_afs, afs = pcall(function() return slot.amount:font_size() end)
            if not ok_afs or not (mount_is_finite(afs) and afs > 0) then return false end
            if math.abs(afs - geom.font_size) > 0.5 then return false end
            local ok_ac, ac = pcall(function() return slot.amount:color() end)
            if not ok_ac or not o_color_matches_ref(ac, expected_color) then return false end
            local amount_w = geom.root_w - text_w
            local expected_amt_y = completion.amount_y_base
            if is_coordinated and not p1 then
                expected_amt_y = completion.amount_y_base + geom.row_h * eased_exit
            elseif not p1 then
                expected_amt_y = completion.amount_y_base - COMPLETION_RISE * eased_exit
            end
            local aok, ax, ay, aw, ah = o_read_prim_shape(slot.amount)
            if not aok then return false end
            if math.abs(ay - expected_amt_y) > tol then return false end
            if math.abs(ax - text_w) > tol then return false end
            if math.abs(aw - amount_w) > tol then return false end
            if math.abs(ah - geom.row_h) > tol then return false end
            local amok, amw, amh = o_measure_text_rect(slot.amount)
            if not amok then return false end
            if amw > amount_w + 1.0 then return false end
            if amh > geom.row_h + 1.0 then return false end
            local expected_a_alpha = COMPLETION_AMOUNT_DIM
            if is_coordinated and not p1 then
                expected_a_alpha = COMPLETION_AMOUNT_DIM * (1.0 - (1.0 - COMPLETION_HISTORY_ALPHA) * eased_exit)
            elseif not p1 then
                expected_a_alpha = expected_pulse * COMPLETION_AMOUNT_DIM * (1.0 - eased_exit)
            end
            local ok_aa, aa = pcall(function() return slot.amount:alpha() end)
            if not ok_aa or not mount_is_finite(aa) then return false end
            if math.abs(aa - expected_a_alpha) > 0.05 then return false end

            if slot.strike and mount_panel_alive(slot.strike) then
                local ok_sv, sv = pcall(function() return slot.strike:visible() end)
                if not ok_sv or type(sv) ~= "boolean" then return false end
                if sv ~= false then return false end
                local ok_sw, sw = pcall(function() return slot.strike:w() end)
                if not ok_sw or not mount_is_finite(sw) then return false end
                if math.abs(sw) > 1.0 then return false end
            end
            if is_coordinated and not p1 then
                if eased_exit > 0 then
                    local extra = self._coordinated_slide_extra
                    if not extra then return false end
                    if not extra.text or not mount_panel_alive(extra.text) then return false end
                    local ok_ev, ev = pcall(function() return extra.text:visible() end)
                    if not ok_ev or type(ev) ~= "boolean" then return false end
                    if ev ~= true then return false end
                    local ok_et, et = pcall(function() return extra.text:text() end)
                    if not ok_et or type(et) ~= "string" then return false end
                    local expected_extra_text = completion.successor_pending_entry and (completion.successor_pending_entry.text or "") or ""
                    if extra._fit_source == expected_extra_text and extra._fit_sig == o_layout_fit_sig(geom) then
                        expected_extra_text = extra._fit_display or expected_extra_text
                    end
                    if et ~= expected_extra_text then return false end
                    local ok_efs, efs = pcall(function() return extra.text:font_size() end)
                    if not ok_efs or not (mount_is_finite(efs) and efs > 0) then return false end
                    if math.abs(efs - geom.font_size) > 0.5 then return false end
                    local ok_ea, ea = pcall(function() return extra.text:alpha() end)
                    if not ok_ea or not mount_is_finite(ea) then return false end
                    if math.abs(ea - eased_exit) > 0.05 then return false end
                    local ok_ey, ey = pcall(function() return extra.text:y() end)
                    if not ok_ey or not mount_is_finite(ey) then return false end
                    local expected_extra_y = -geom.row_h + (0 - (-geom.row_h)) * eased_exit
                    if math.abs(ey - expected_extra_y) > 0.5 then return false end
                    local text_w = geom.root_w * 0.7
                    local eok, ex, ey, ew, eh = o_read_prim_shape(extra.text)
                    if not eok then return false end
                    if math.abs(ex) > tol then return false end
                    if math.abs(ew - text_w) > tol then return false end
                    if math.abs(eh - geom.row_h) > tol then return false end
                    local emok, emw, emh = o_measure_text_rect(extra.text)
                    if not emok then return false end
                    if emw > text_w + 1.0 then return false end
                    if emh > geom.row_h + 1.0 then return false end
                    if not extra.amount or not mount_panel_alive(extra.amount) then return false end
                    local ok_eav, eav = pcall(function() return extra.amount:visible() end)
                    if not ok_eav or type(eav) ~= "boolean" then return false end
                    local expected_amt = completion.successor_pending_entry and mount_format_amount(completion.successor_pending_entry) or ""
                    local should_show = expected_amt ~= ""
                    if eav ~= should_show then return false end
                    local ok_eat, eat = pcall(function() return extra.amount:text() end)
                    if not ok_eat or type(eat) ~= "string" then return false end
                    if eat ~= expected_amt then return false end
                    local ok_eafs, eafs = pcall(function() return extra.amount:font_size() end)
                    if not ok_eafs or not (mount_is_finite(eafs) and eafs > 0) then return false end
                    if math.abs(eafs - geom.font_size) > 0.5 then return false end
                    if should_show then
                        local ok_eaa, eaa = pcall(function() return extra.amount:alpha() end)
                        if not ok_eaa or not mount_is_finite(eaa) then return false end
                        if math.abs(eaa - eased_exit) > 0.05 then return false end
                    end
                    local amount_w = geom.root_w - text_w
                    local eaok, eax, eay, eaw, eah = o_read_prim_shape(extra.amount)
                    if not eaok then return false end
                    if math.abs(eax - text_w) > tol then return false end
                    if math.abs(eay - ey) > tol then return false end
                    if math.abs(eaw - amount_w) > tol then return false end
                    if math.abs(eah - geom.row_h) > tol then return false end
                end
            end
            if completion.displayed_snapshot and next(completion.displayed_snapshot) then
                local snapshot = completion.displayed_snapshot or {}
                local hist_snap = completion.history_slots_snapshot or {}
                for si = 1, MAX_SLOTS do
                    if si ~= i and snapshot[si] then
                        local hist_slot = self._slot_prims[si]
                        if not hist_slot then return false end
                        if not hist_slot.text or not mount_panel_alive(hist_slot.text) then return false end
                        if not hist_slot.amount or not mount_panel_alive(hist_slot.amount) then return false end
                        local snap_entry = snapshot[si]
                        local is_hist = hist_snap[si] == true
                        local snap_source = snap_entry.text or ""
                        local snap_text_w = geom.root_w * 0.7
                        local snap_row_h = geom.row_h
                        local snap_display = snap_source
                        local snap_fit = self._slot_fit_cache[si]
                        if snap_fit and snap_fit.source == snap_source and snap_fit.sig == o_layout_fit_sig(geom) then
                            snap_display = snap_fit.display
                        end
                        local ok_ht, ht = pcall(function() return hist_slot.text:text() end)
                        if not ok_ht or type(ht) ~= "string" then return false end
                        if ht ~= snap_display then return false end
                        local ok_hv, hv = pcall(function() return hist_slot.text:visible() end)
                        if not ok_hv or type(hv) ~= "boolean" then return false end
                        if hv ~= true then return false end
                        local ok_hfs, hfs = pcall(function() return hist_slot.text:font_size() end)
                        if not ok_hfs or not (mount_is_finite(hfs) and hfs > 0) then return false end
                        if math.abs(hfs - geom.font_size) > 0.5 then return false end
                        local expected_y
                        if is_coordinated and not p1 then
                            expected_y = (si - 1) * geom.row_h + geom.row_h * eased_exit
                        else
                            expected_y = (si - 1) * geom.row_h
                        end
                        local hok, hx, hy, hw, hh = o_read_prim_shape(hist_slot.text)
                        if not hok then return false end
                        if math.abs(hx) > tol then return false end
                        if math.abs(hy - expected_y) > 0.5 then return false end
                        if math.abs(hw - snap_text_w) > tol then return false end
                        if math.abs(hh - geom.row_h) > tol then return false end
                        local hmok, hmw, hmh = o_measure_text_rect(hist_slot.text)
                        if not hmok then return false end
                        if hmw > snap_text_w + 1.0 then return false end
                        if hmh > geom.row_h + 1.0 then return false end
                        local ok_hc, hc = pcall(function() return hist_slot.text:color() end)
                        if not ok_hc or not o_color_matches_ref(hc, HUD_DEFAULT_COLOR) then return false end
                        local expected_ha = COMPLETION_HISTORY_ALPHA
                        if is_coordinated and not p1 and is_hist and (si + 1 > _vis_limit) then
                            expected_ha = COMPLETION_HISTORY_ALPHA * (1.0 - eased_exit)
                        end
                        local ok_ha, ha = pcall(function() return hist_slot.text:alpha() end)
                        if not ok_ha or not mount_is_finite(ha) then return false end
                        if math.abs(ha - expected_ha) > 0.05 then return false end
                        local snap_amt = ""
                        if not is_hist and snap_entry.amount then
                            if snap_entry.countdown then
                                snap_amt = math.floor(snap_entry.amount - (snap_entry.current_amount or 0)) .. "/" .. math.floor(snap_entry.amount)
                            else
                                snap_amt = math.floor(snap_entry.current_amount or 0) .. "/" .. math.floor(snap_entry.amount)
                            end
                        end
                        local ok_hat, hat = pcall(function() return hist_slot.amount:text() end)
                        if not ok_hat or type(hat) ~= "string" then return false end
                        if hat ~= snap_amt then return false end
                        local snap_amt_show = snap_amt ~= ""
                        local ok_hav, hav = pcall(function() return hist_slot.amount:visible() end)
                        if not ok_hav or type(hav) ~= "boolean" then return false end
                        if hav ~= snap_amt_show then return false end
                        local ok_hafs, hafs = pcall(function() return hist_slot.amount:font_size() end)
                        if not ok_hafs or not (mount_is_finite(hafs) and hafs > 0) then return false end
                        if math.abs(hafs - geom.font_size) > 0.5 then return false end
                        local snap_amount_w = geom.root_w - snap_text_w
                        local haok, hax, hay, haw, hah = o_read_prim_shape(hist_slot.amount)
                        if not haok then return false end
                        if math.abs(hax - snap_text_w) > tol then return false end
                        if math.abs(hay - expected_y) > 0.5 then return false end
                        if math.abs(haw - snap_amount_w) > tol then return false end
                        if math.abs(hah - geom.row_h) > tol then return false end
                        local hamok, hamw, hamh = o_measure_text_rect(hist_slot.amount)
                        if not hamok then return false end
                        if hamw > snap_amount_w + 1.0 then return false end
                        if hamh > geom.row_h + 1.0 then return false end
                        local ok_haa, haa = pcall(function() return hist_slot.amount:alpha() end)
                        if not ok_haa or not mount_is_finite(haa) then return false end
                        local expected_a_ha = COMPLETION_HISTORY_ALPHA
                        if is_coordinated and not p1 and is_hist and (si + 1 > _vis_limit) then
                            expected_a_ha = COMPLETION_HISTORY_ALPHA * (1.0 - eased_exit)
                        end
                        if math.abs(haa - expected_a_ha) > 0.05 then return false end
                    end
                end
            end
        elseif completion and completion.successor_entry then
            local progress = (completion.entry_elapsed or 0) / COMPLETION_EXIT_T
            if progress < 0 then progress = 0 end
            if progress > 1 then progress = 1 end
            local eased = o_smoothstep(progress)
            local expected_alpha = eased
            local expected_y_offset = COMPLETION_RISE * (1.0 - eased)
            local expected_display = completion.successor_display or completion.successor_text or ""
            local text_w = geom.root_w * 0.7
            local ok_t, t = pcall(function() return slot.text:text() end)
            if not ok_t or type(t) ~= "string" then return false end
            if t ~= expected_display then return false end
            local ok_v, v = pcall(function() return slot.text:visible() end)
            if not ok_v or type(v) ~= "boolean" then return false end
            if v ~= true then return false end
            local ok_fs, fs = pcall(function() return slot.text:font_size() end)
            if not ok_fs or not (mount_is_finite(fs) and fs > 0) then return false end
            if math.abs(fs - geom.font_size) > 0.5 then return false end
            local expected_text_y = completion.title_y_base + expected_y_offset
            local tok, tx, ty, tw, th = o_read_prim_shape(slot.text)
            if not tok then return false end
            if math.abs(ty - expected_text_y) > tol then return false end
            if math.abs(tx) > tol then return false end
            if math.abs(tw - text_w) > tol then return false end
            if math.abs(th - geom.row_h) > tol then return false end
            local fit = self._slot_fit_cache[i]
            if fit and fit.source == (completion.successor_text or "") and fit.sig == o_layout_fit_sig(geom) then
                local ok_w, w = pcall(function() return slot.text:w() end)
                local ok_h, h = pcall(function() return slot.text:h() end)
                if ok_w and ok_h and mount_is_finite(w) and mount_is_finite(h) then
                    if w > text_w + 1.0 then return false end
                    if h > geom.row_h + 1.0 then return false end
                end
            end
            local mok, mw, mh = o_measure_text_rect(slot.text)
            if not mok then return false end
            if mw > text_w + 1.0 then return false end
            if mh > geom.row_h + 1.0 then return false end
            local ok_ta, ta = pcall(function() return slot.text:alpha() end)
            if not ok_ta or not mount_is_finite(ta) then return false end
            if math.abs(ta - expected_alpha) > 0.05 then return false end

            local expected_amount = completion.successor_amount or ""
            local ok_at, at = pcall(function() return slot.amount:text() end)
            if not ok_at or type(at) ~= "string" then return false end
            if at ~= expected_amount then return false end
            local ok_av, av = pcall(function() return slot.amount:visible() end)
            if not ok_av or type(av) ~= "boolean" then return false end
            local expected_amt_vis = expected_amount ~= ""
            if av ~= expected_amt_vis then return false end
            local ok_afs, afs = pcall(function() return slot.amount:font_size() end)
            if not ok_afs or not (mount_is_finite(afs) and afs > 0) then return false end
            if math.abs(afs - geom.font_size) > 0.5 then return false end
            local amount_w = geom.root_w - text_w
            local expected_amt_y = completion.amount_y_base + expected_y_offset
            local aok, ax, ay, aw, ah = o_read_prim_shape(slot.amount)
            if not aok then return false end
            if math.abs(ay - expected_amt_y) > tol then return false end
            if math.abs(ax - text_w) > tol then return false end
            if math.abs(aw - amount_w) > tol then return false end
            if math.abs(ah - geom.row_h) > tol then return false end
            local amok, amw, amh = o_measure_text_rect(slot.amount)
            if not amok then return false end
            if amw > amount_w + 1.0 then return false end
            if amh > geom.row_h + 1.0 then return false end
            local ok_aa, aa = pcall(function() return slot.amount:alpha() end)
            if not ok_aa or not mount_is_finite(aa) then return false end
            if math.abs(aa - expected_alpha) > 0.05 then return false end

            if slot.strike and mount_panel_alive(slot.strike) then
                local ok_sv, sv = pcall(function() return slot.strike:visible() end)
                if not ok_sv or type(sv) ~= "boolean" then return false end
                if sv ~= false then return false end
            end
        else
            if self._coordinated_slide_slots and self._coordinated_slide_slots[i] then
                -- Slot is owned by another completion's coordinated slide snapshot;
                -- fully validated by that completion's active branch above.
            else
            local displayed, history_slots = self:_compute_displayed_entries()
            if not displayed then displayed = {} end
            if not history_slots then history_slots = {} end
            local entry = displayed[i]
            local is_history = history_slots[i] == true
            local source_text = (entry and type(entry.text) == "string") and entry.text or ""
            local fit = self._slot_fit_cache[i]
            local expected_display
            if fit and fit.source == source_text and fit.sig == o_layout_fit_sig(geom) then
                expected_display = fit.display
            else
                expected_display = source_text
            end
            local expected_amount = ""
            if not is_history then
                expected_amount = entry and mount_format_amount(entry) or ""
            end

            if slot.text and mount_panel_alive(slot.text) then
                local ok_t, t = pcall(function() return slot.text:text() end)
                if not ok_t or type(t) ~= "string" then return false end
                if t ~= expected_display then return false end
                local ok_v, v = pcall(function() return slot.text:visible() end)
                if not ok_v or type(v) ~= "boolean" then return false end
                local expected_vis = entry ~= nil and source_text ~= ""
                if v ~= expected_vis then return false end
                local ok_fs, fs = pcall(function() return slot.text:font_size() end)
                if not ok_fs or not (mount_is_finite(fs) and fs > 0) then return false end
                if math.abs(fs - geom.font_size) > 0.5 then return false end
                local text_y = (i - 1) * geom.row_h
                local text_w = geom.root_w * 0.7
                local tok, tx, ty, tw, th = o_read_prim_shape(slot.text)
                if not tok then return false end
                if not o_shape_matches(tx, ty, tw, th, 0, text_y, text_w, geom.row_h, tol) then return false end
                if fit and fit.source == source_text and fit.sig == o_layout_fit_sig(geom) then
                    local ok_w, w = pcall(function() return slot.text:w() end)
                    local ok_h, h = pcall(function() return slot.text:h() end)
                    if ok_w and ok_h and mount_is_finite(w) and mount_is_finite(h) then
                        if w > text_w + 1.0 then return false end
                        if h > geom.row_h + 1.0 then return false end
                    end
                end
                local mok, mw, mh = o_measure_text_rect(slot.text)
                if not mok then return false end
                if mw > text_w + 1.0 then return false end
                if mh > geom.row_h + 1.0 then return false end
                local expected_alpha = is_history and COMPLETION_HISTORY_ALPHA or 1.0
                local ok_ta, ta = pcall(function() return slot.text:alpha() end)
                if not ok_ta or not mount_is_finite(ta) then return false end
                if math.abs(ta - expected_alpha) > 0.05 then return false end
            end

            if slot.amount and mount_panel_alive(slot.amount) then
                local ok_t, t = pcall(function() return slot.amount:text() end)
                if not ok_t or type(t) ~= "string" then return false end
                if t ~= expected_amount then return false end
                local ok_v, v = pcall(function() return slot.amount:visible() end)
                if not ok_v or type(v) ~= "boolean" then return false end
                local expected_vis = entry ~= nil and mount_format_amount(entry) ~= nil
                if v ~= expected_vis then return false end
                local ok_fs, fs = pcall(function() return slot.amount:font_size() end)
                if not ok_fs or not (mount_is_finite(fs) and fs > 0) then return false end
                if math.abs(fs - geom.font_size) > 0.5 then return false end
                local amount_y = (i - 1) * geom.row_h
                local text_w = geom.root_w * 0.7
                local amount_w = geom.root_w - text_w
                local aok, ax, ay, aw, ah = o_read_prim_shape(slot.amount)
                if not aok then return false end
                if not o_shape_matches(ax, ay, aw, ah, text_w, amount_y, amount_w, geom.row_h, tol) then return false end
                local amok, amw, amh = o_measure_text_rect(slot.amount)
                if not amok then return false end
                if amw > amount_w + 1.0 then return false end
                if amh > geom.row_h + 1.0 then return false end
            end
            end
        end
    end
    return true
end

function O:_resolve_native_leaves()
    if not self._manager then return nil end
    local ok_ho, ho = pcall(function() return self._manager._hud_objectives end)
    if not ok_ho or not ho then return nil end
    local ok_hp, hp = pcall(function() return ho._hud_panel end)
    if not ok_hp or not hp then return nil end
    if not mount_panel_alive(hp) then return nil end
    local sp, panel = mount_safe_call(hp, "child", "objectives_panel")
    if sp ~= MOUNT_CALL_OK or not panel then return nil end
    if not mount_panel_alive(panel) then return nil end
    local ok_box, box = pcall(function() return ho._bg_box end)
    if not ok_box or not box then return nil end
    if not mount_panel_alive(box) then return nil end
    local sbp, box_parent = mount_safe_call(box, "parent")
    if sbp ~= MOUNT_CALL_OK or box_parent ~= panel then return nil end
    local leaves = {}
    local panel_names = {"objective_text", "amount_text", "icon_objectivebox"}
    for i = 1, 3 do
        local sc, child = mount_safe_call(panel, "child", panel_names[i])
        if sc ~= MOUNT_CALL_OK or not child then return nil end
        if not mount_panel_alive(child) then return nil end
        local scp, cp = mount_safe_call(child, "parent")
        if scp ~= MOUNT_CALL_OK or cp ~= panel then return nil end
        leaves[i] = child
    end
    local box_names = {"bg", "left_top", "left_bottom", "right_top", "right_bottom"}
    for i = 1, 5 do
        local sc, child = mount_safe_call(box, "child", box_names[i])
        if sc ~= MOUNT_CALL_OK or not child then return nil end
        if not mount_panel_alive(child) then return nil end
        local scp, cp = mount_safe_call(child, "parent")
        if scp ~= MOUNT_CALL_OK or cp ~= box then return nil end
        leaves[3 + i] = child
    end
    return leaves
end

function O:_resolve_selected_active_id()
    if not self._manager then return nil end
    local ok_ho, ho = pcall(function() return self._manager._hud_objectives end)
    if not ok_ho or not ho then return nil end
    local ok_aid, aid = pcall(function() return ho._active_objective_id end)
    if not ok_aid or aid == nil then return nil end
    local entries = self:select_visible()
    if not entries then return nil end
    for i = 1, #entries do
        local e = entries[i]
        if e.id == aid and not e.pending then
            return aid
        end
    end
    return nil
end

function O:_release_native()
    local had = self._native_acquired or self._native_leaves or self._native_active_id or self._native_completion_pending
    if not had then return true end
    local nv = kyohud.hud.native_visibility
    if not nv then
        self._native_completion_pending = false
        self._native_completion_pending_self = nil
        self._native_completion_pending_panel = nil
        return false
    end
    local gen = self._native_generation
    if gen and gen > 0 then
        nv:release(self, gen)
    end
    local remaining = false
    for _, e in ipairs(nv._entries) do
        if e.owner == self then
            remaining = true
            break
        end
    end
    self._native_acquired = false
    self._native_active_id = nil
    self._native_completion_pending = false
    self._native_completion_pending_self = nil
    self._native_completion_pending_panel = nil
    if not remaining then
        if self._native_leaves then
            for _, leaf in ipairs(self._native_leaves) do
                if nv._whitelist[leaf] then
                    nv._whitelist[leaf].visible = nil
                    if not next(nv._whitelist[leaf]) then
                        nv._whitelist[leaf] = nil
                    end
                end
            end
        end
        self._native_leaves = nil
        return true
    end
    return false
end

function O:_reconcile_native_completion_values()
    if not self._native_leaves then return end
    local nv = kyohud.hud.native_visibility
    if not nv then return end
    local title_leaf = self._native_leaves[1]
    local amount_leaf = self._native_leaves[2]
    for _, e in ipairs(nv._entries) do
        if e.owner == self and e.generation == self._native_generation then
            if e.property == "visible" and (e.object == title_leaf or e.object == amount_leaf) then
                e.old_value = false
            end
        end
    end
end

function O:_sync_native_visibility()
    if not self._mounted then self:_release_native(); return end
    if kyohud.settings.enable_hud_foundation ~= true then self:_release_native(); return end
    if kyohud.settings.enable_objectives ~= true then self:_release_native(); return end
    if mount_is_vr() then self:_release_native(); return end
    if self._manager ~= managers.hud then self:_release_native(); return end
    if self._native_fallback then
        if self._native_conflict_leaf then
            local current_leaves = self:_resolve_native_leaves()
            if current_leaves and #current_leaves == 8 then
                local still_present = false
                for ci = 1, #current_leaves do
                    if current_leaves[ci] == self._native_conflict_leaf then
                        still_present = true
                        break
                    end
                end
                if not still_present then
                    local aid = self:_resolve_selected_active_id()
                    if aid then
                        local released = self:_release_native()
                        if released then
                            self._native_fallback = false
                            if mount_ensure_root_visible_bounded(self) then
                                self._native_conflict_identity = nil
                                self._native_conflict_leaf = nil
                            else
                                self._native_fallback = true
                                mount_safe_call(self._root_panel, "set_visible", false)
                                return
                            end
                        else
                            mount_safe_call(self._root_panel, "set_visible", false)
                            return
                        end
                    else
                        self:_release_native()
                        mount_safe_call(self._root_panel, "set_visible", false)
                        return
                    end
                else
                    self:_release_native()
                    mount_safe_call(self._root_panel, "set_visible", false)
                    return
                end
            else
                self:_release_native()
                mount_safe_call(self._root_panel, "set_visible", false)
                return
            end
        else
            self:_release_native()
            mount_safe_call(self._root_panel, "set_visible", false)
            return
        end
    end
    if not self:_verify_render() then self:_release_native(); return end
    local active_id = self:_resolve_selected_active_id()
    if not active_id then
        local pending_valid = false
        if self._native_completion_pending
            and self._native_acquired
            and self._native_active_id
            and self._native_leaves and #self._native_leaves == 8
            and self._native_completion_pending_self
            and self._native_completion_pending_panel then
            local hud_obj = self._manager and self._manager._hud_objectives
            if hud_obj and self._native_completion_pending_self == hud_obj then
                pending_valid = true
            end
        end
        if not pending_valid then
            self._native_completion_pending = false
            self._native_completion_pending_self = nil
            self._native_completion_pending_panel = nil
            self:_release_native()
            return
        end
        active_id = self._native_active_id
    end
    local leaves = self:_resolve_native_leaves()
    if not leaves then self:_release_native(); return end
    local rt = kyohud.hud.runtime
    if not rt then self:_release_native(); return end
    local gen = rt._generation
    if not gen or gen == 0 then self:_release_native(); return end
    local nv = kyohud.hud.native_visibility
    if not nv then self:_release_native(); return end
    local changed = false
    if not self._native_leaves or #self._native_leaves ~= #leaves then
        changed = true
    else
        for i = 1, #leaves do
            if self._native_leaves[i] ~= leaves[i] then
                changed = true
                break
            end
        end
    end
    if self._native_generation ~= gen then changed = true end
    if changed then
        local released = self:_release_native()
        if not released then
            mount_safe_call(self._root_panel, "set_visible", false)
            return
        end
    end
    if self._native_acquired then
        local held_leaves = self._native_leaves
        if held_leaves then
            local conflict_detected = false
            local offending_leaf
            for i = 1, #held_leaves do
                local ok, val = pcall(function() return held_leaves[i]:visible() end)
                if not ok or type(val) ~= "boolean" or val ~= false then
                    conflict_detected = true
                    offending_leaf = held_leaves[i]
                    break
                end
            end
            if conflict_detected then
                self._native_conflict_leaf = offending_leaf
                self._native_conflict_identity = {}
                for i = 1, #held_leaves do
                    self._native_conflict_identity[i] = held_leaves[i]
                end
                self:_release_native()
                self._native_fallback = true
                mount_safe_call(self._root_panel, "set_visible", false)
                return
            end
        end
        return
    end
    for i = 1, #leaves do
        nv._whitelist[leaves[i]] = nv._whitelist[leaves[i]] or {}
        nv._whitelist[leaves[i]].visible = true
    end
    local requests = {}
    for i = 1, #leaves do
        requests[i] = { id = leaves[i], property = "visible", value = false }
    end
    local acquired = nv:acquire(self, gen, requests)
    self._native_leaves = leaves
    self._native_generation = gen
    self._native_active_id = active_id
    self._native_acquired = acquired == true
    if acquired ~= true then
        mount_safe_call(self._root_panel, "set_visible", false)
    end
end

function O:mount(manager)
    if kyohud.settings.enable_hud_foundation ~= true then return end
    if kyohud.settings.enable_objectives ~= true then return end
    if mount_is_vr() then return end
    local mgr = manager or self._manager
    if not mgr then return end
    self._manager = mgr

    local parent = mount_get_runtime_root()
    if not parent then return end

    local ok_om, om = pcall(function() return managers.objectives end)
    if ok_om and type(om) == "table" then
        self:snapshot(om)
    end

    if self._mounted and self._root_panel and mount_panel_alive(self._root_panel) then
        if self._parent_panel == parent then
            if not mount_ensure_root_visible_bounded(self) then
                self:_release_native()
                return
            end
            self._panel = self._root_panel
            self:_update_layout()
            self:_ensure_slot_prims()
            self:_sync_primitives()
            return
        end
        self:unmount()
    end

    if self._root_panel and not mount_panel_alive(self._root_panel) then
        self._root_panel = nil
        self._panel = nil
        self:_clear_slot_prims()
    end

    local status, existing = mount_safe_call(parent, "child", OBJECTIVES_ROOT_NAME)
    if status == MOUNT_CALL_OK and existing ~= nil and mount_panel_alive(existing) then
        if self._root_panel == existing then
            if not mount_ensure_root_visible_bounded(self) then
                self:_release_native()
                return
            end
            self._mounted = true
            self._panel = self._root_panel
            self._parent_panel = parent
            self:_update_layout()
            self:_ensure_slot_prims()
            self:_sync_primitives()
            return
        end
        return
    end
    if status ~= MOUNT_CALL_OK then return end

    local cs, root = mount_safe_call(parent, "panel", {name = OBJECTIVES_ROOT_NAME})
    if cs ~= MOUNT_CALL_OK or root == nil then return end

    self._root_panel = root
    self._panel = self._root_panel
    self._parent_panel = parent
    self._mounted = true

    self:_update_layout()
    self:_ensure_slot_prims()
    self:_sync_primitives()
end

function O:unmount()
    local released = self:_release_native()
    if released == true then
        self._native_fallback = false
        self._native_conflict_identity = nil
        self._native_conflict_leaf = nil
    end
    if not self._mounted and not self._root_panel then return true end
    if self._root_panel then
        if mount_panel_alive(self._root_panel) then
            local parent = self._parent_panel
            if parent and mount_panel_alive(parent) then
                local status, result = mount_safe_call(parent, "remove", self._root_panel)
                if status == MOUNT_CALL_OK and result ~= false then
                    self._root_panel = nil
                    self._panel = nil
                else
                    self._mounted = false
                    return false
                end
            else
                self._root_panel = nil
                self._panel = nil
            end
        else
            self._root_panel = nil
            self._panel = nil
        end
    end
    self:_clear_slot_prims()
    self._parent_panel = nil
    self._mounted = false
    self._layout_cache = nil
    return true
end

function O:rebuild(manager)
    self:unmount()
    self:mount(manager)
end

function O:refresh_settings(manager)
    if kyohud.settings.enable_hud_foundation == true and kyohud.settings.enable_objectives == true then
        if not self._mounted or not self._root_panel or not mount_panel_alive(self._root_panel) then
            self:mount(manager)
            return
        end
        if not mount_ensure_root_visible_bounded(self) then
            self:_release_native()
            return
        end
        self:_update_layout()
        self:_ensure_slot_prims()
        self:_sync_primitives()
    else
        self:_release_native()
        if self._mounted or self._root_panel then
            self:unmount()
        end
    end
end

function O:on_heist_start(manager)
    local mgr = manager or self._manager
    if not mgr then return end
    if self._mounted or self._root_panel then
        self:unmount()
    end
    self._active = {}
    self._by_id = {}
    self._snapshot_manager = nil
    self._manager = mgr
    self:_clear_completion_history()
end

function O:update(manager, t, dt)
    if kyohud.settings.enable_hud_foundation ~= true or kyohud.settings.enable_objectives ~= true then
        self:_release_native()
        if self._mounted then
            self:unmount()
        end
        return
    end
    if not self._mounted then
        self:mount(manager or self._manager)
        return
    end
    if not self._root_panel or not mount_panel_alive(self._root_panel) then
        self:_release_native()
        self._mounted = false
        return
    end
    if not mount_ensure_root_visible_bounded(self) then
        self:_release_native()
        return
    end
    local ok_om, om = pcall(function() return managers.objectives end)
    if ok_om and type(om) == "table" then
        self:snapshot(om)
    end
    self:_update_layout()
    self:_ensure_slot_prims()
    self:_sync_primitives()
end

function O:destroy(manager)
    if manager and self._manager and manager ~= self._manager then
        return
    end
    self:unmount()
end

local OM_CONTEXT = "lib/managers/objectivesmanager"
local HUD_CONTEXT = "lib/managers/hudmanagerpd2"
local HUD_OBJ_CONTEXT = "lib/managers/hud/hudobjectives"

kyohud.hud._installed_hooks = kyohud.hud._installed_hooks or {}

local function safe_hook(class, method, id, fn)
    if type(class) ~= "table" then return end
    if kyohud.hud._installed_hooks[id] then return end
    if type(class[method]) ~= "function" then return end
    Hooks:PostHook(class, method, id, fn)
    kyohud.hud._installed_hooks[id] = true
end

local function safe_pre_hook(class, method, id, fn)
    if type(class) ~= "table" then return end
    if kyohud.hud._installed_hooks[id] then return end
    if type(class[method]) ~= "function" then return end
    Hooks:PreHook(class, method, id, fn)
    kyohud.hud._installed_hooks[id] = true
end

local function sync_if_mounted()
    if O._mounted and O._root_panel and mount_panel_alive(O._root_panel) then
        O:_sync_primitives()
    end
end

if RequiredScript == OM_CONTEXT then
    local function on_om_activate(self, id, load_data, data)
        if not id then return end
        if managers and managers.objectives and self ~= managers.objectives then return end
        if O._snapshot_manager ~= self then
            O:_cancel_all_completion_animations()
            O._snapshot_manager = self
            O._active = {}
            O._by_id = {}
            O._last_hud_presented_id = nil
            O._last_hud_completed_id = nil
            O:_clear_completion_history()
        end
        local ok, registry = pcall(function() return self:get_active_objectives() end)
        if not ok or type(registry) ~= "table" then return end
        local objective = registry[id]
        if not objective then return end
        if O._by_id[id] then
            local idx = O._by_id[id]
            table.remove(O._active, idx)
            O._by_id[id] = nil
            for i = idx, #O._active do
                O._by_id[O._active[i].id] = i
            end
        end
        local snapshot = copy_objective_scalar(objective)
        if not snapshot then return end
        local pending = false
        if self._delayed_presentation and self._delayed_presentation.activate_params
            and self._delayed_presentation.activate_params.id == id then
            pending = true
        end
        snapshot.pending = pending
        table.insert(O._active, snapshot)
        O._by_id[id] = #O._active
        sync_if_mounted()
    end

    local function on_om_remove(self, id, load_data)
        if not id then return end
        local auth = (managers and managers.objectives) or O._snapshot_manager
        if auth and self ~= auth then return end
        local idx = O._by_id[id]
        if not idx then return end
        table.remove(O._active, idx)
        O._by_id[id] = nil
        for i = idx, #O._active do
            O._by_id[O._active[i].id] = i
        end
        for i = 1, MAX_SLOTS do
            local c = O._slot_completion[i]
            if c and c.successor_entry == true and c.successor_entry_id == id then
                O:_clear_completion_slot(i)
            end
        end
        sync_if_mounted()
    end

    local function on_om_complete(self, id, load_data)
        if not id then return end
        local auth = (managers and managers.objectives) or O._snapshot_manager
        if auth and self ~= auth then return end
        local ok, registry = pcall(function() return self:get_active_objectives() end)
        if not ok or type(registry) ~= "table" then return end
        local objective = registry[id]
        if not objective then
            O:_capture_completion(id)
            local idx = O._by_id[id]
            if idx and O._active[idx] then
                O:_add_to_completion_history(O._active[idx])
            end
            on_om_remove(self, id, load_data)
            return
        end
        local idx = O._by_id[id]
        if not idx or not O._active[idx] then return end
        local entry = O._active[idx]
        local updated = copy_objective_scalar(objective)
        if not updated then return end
        local was_pending = entry.pending
        entry.text = updated.text
        entry.amount = updated.amount
        entry.current_amount = updated.current_amount
        entry.countdown = updated.countdown
        entry.sub_objectives = updated.sub_objectives
        entry.pending = was_pending
        sync_if_mounted()
    end

    local function on_om_reset(self)
        if managers and managers.objectives and self ~= managers.objectives then return end
        O:_cancel_all_completion_animations()
        O._snapshot_manager = self
        O._active = {}
        O._by_id = {}
        O._last_hud_presented_id = nil
        O._last_hud_completed_id = nil
        O:_clear_completion_history()
        sync_if_mounted()
    end

    safe_hook(ObjectivesManager, "activate_objective", "KyohUD_OM_ActivateObjective", on_om_activate)
    safe_hook(ObjectivesManager, "activate_objective_countdown", "KyohUD_OM_ActivateObjectiveCountdown", on_om_activate)
    safe_hook(ObjectivesManager, "remove_objective", "KyohUD_OM_RemoveObjective", on_om_remove)
    safe_hook(ObjectivesManager, "complete_objective", "KyohUD_OM_CompleteObjective", on_om_complete)
    safe_hook(ObjectivesManager, "complete_objective_countdown", "KyohUD_OM_CompleteObjectiveCountdown", on_om_complete)
    safe_hook(ObjectivesManager, "complete_sub_objective", "KyohUD_OM_CompleteSubObjective", on_om_complete)
    safe_hook(ObjectivesManager, "reset", "KyohUD_OM_Reset", on_om_reset)
end

if RequiredScript == HUD_CONTEXT then
    local function on_hud_activate(self, data)
        if type(data) ~= "table" then return end
        if managers and managers.hud and self ~= managers.hud then return end
        O._last_hud_presented_id = data.id
        local idx = O._by_id[data.id]
        if idx and O._active[idx] then
            O._active[idx].pending = false
        end
        sync_if_mounted()
    end

    local function on_hud_complete(self, data)
        if type(data) ~= "table" then return end
        if managers and managers.hud and self ~= managers.hud then return end
        O._last_hud_completed_id = data.id
        sync_if_mounted()
    end

    safe_hook(HUDManager, "activate_objective", "KyohUD_HUD_ActivateObjective", on_hud_activate)
    safe_hook(HUDManager, "complete_objective", "KyohUD_HUD_CompleteObjective", on_hud_complete)
end

if RequiredScript == HUD_OBJ_CONTEXT then
    if type(HUDObjectives) == "table" and type(HUDObjectives.activate_objective) == "function" then
        local function on_hud_obj_activate_pre(self, data)
            if not (managers and managers.hud and managers.hud._hud_objectives == self) then return end
            if O._manager ~= managers.hud then return end
            O:_release_native()
        end

        safe_pre_hook(HUDObjectives, "activate_objective", "KyohUD_HUDObj_ActivateObjective_Pre", on_hud_obj_activate_pre)
    end

    if type(HUDObjectives) == "table" and type(HUDObjectives.open_right_done) == "function" then
        local open_right_done_pre_release_ok = false

        local function on_hud_obj_open_right_done_pre(self)
            open_right_done_pre_release_ok = false
            if not (managers and managers.hud and managers.hud._hud_objectives == self) then return end
            if O._manager ~= managers.hud then return end
            local ok = O:_release_native()
            open_right_done_pre_release_ok = (ok == true)
        end

        local function on_hud_obj_open_right_done_post(self)
            if not open_right_done_pre_release_ok then return end
            open_right_done_pre_release_ok = false
            if not (managers and managers.hud and managers.hud._hud_objectives == self) then return end
            if O._manager ~= managers.hud then return end
            O:_sync_native_visibility()
        end

        safe_pre_hook(HUDObjectives, "open_right_done", "KyohUD_HUDObj_OpenRightDone_Pre", on_hud_obj_open_right_done_pre)
        safe_hook(HUDObjectives, "open_right_done", "KyohUD_HUDObj_OpenRightDone_Post", on_hud_obj_open_right_done_post)
    end

    if type(HUDObjectives) == "table" and type(HUDObjectives.complete_objective) == "function" then
        local function on_hud_obj_complete_pre(self, data)
            if type(data) ~= "table" then return end
            if not (managers and managers.hud and managers.hud._hud_objectives == self) then return end
            if O._manager ~= managers.hud then return end
            if data.id ~= self._active_objective_id then return end
            if not O._native_acquired then return end
            if not O._native_leaves or #O._native_leaves ~= 8 then return end
            local ok_hp, hp = pcall(function() return self._hud_panel end)
            if not ok_hp or not hp then return end
            if not mount_panel_alive(hp) then return end
            local ok_op, op = mount_safe_call(hp, "child", "objectives_panel")
            if ok_op ~= MOUNT_CALL_OK or not op then return end
            if not mount_panel_alive(op) then return end
            O._native_completion_pending = true
            O._native_completion_pending_self = self
            O._native_completion_pending_panel = op
        end

        safe_pre_hook(HUDObjectives, "complete_objective", "KyohUD_HUDObj_CompleteObjective_Pre", on_hud_obj_complete_pre)
    end

    if type(HUDObjectives) == "table" and type(HUDObjectives._animate_complete_objective) == "function" then
        local function on_hud_obj_animate_complete_post(self, objectives_panel)
            if not (managers and managers.hud and managers.hud._hud_objectives == self) then return end
            if O._manager ~= managers.hud then return end
            if not O._native_completion_pending then return end
            if O._native_completion_pending_self ~= self then return end
            if not objectives_panel or not mount_panel_alive(objectives_panel) then return end
            if O._native_completion_pending_panel ~= objectives_panel then return end
            O:_reconcile_native_completion_values()
        end

        safe_hook(HUDObjectives, "_animate_complete_objective", "KyohUD_HUDObj_AnimateComplete_Post", on_hud_obj_animate_complete_post)
    end

    if type(_G.HUDBGBox_animate_close_right) == "function" then
        local function on_hud_obj_close_right_post(panel, done_cb)
            if not O._native_completion_pending then return end
            if not (managers and managers.hud) then return end
            if O._manager ~= managers.hud then return end
            local hud_obj = managers.hud._hud_objectives
            if not hud_obj then return end
            if O._native_completion_pending_self ~= hud_obj then return end
            local ok_box, box = pcall(function() return hud_obj._bg_box end)
            if not ok_box or not box then return end
            if panel ~= box then return end
            O._native_completion_pending = false
            O._native_completion_pending_self = nil
            O._native_completion_pending_panel = nil
            O:_release_native()
        end

        safe_hook(_G, "HUDBGBox_animate_close_right", "KyohUD_HUDObj_CloseRight_Post", on_hud_obj_close_right_post)
    end
end
