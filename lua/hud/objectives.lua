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

O._native_leaves = O._native_leaves
O._native_generation = O._native_generation or 0
O._native_acquired = O._native_acquired or false
O._native_active_id = O._native_active_id
O._native_fallback = O._native_fallback or false
O._native_conflict_identity = O._native_conflict_identity or nil
O._native_conflict_leaf = O._native_conflict_leaf

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
        O._snapshot_manager = manager
        O._active = {}
        O._by_id = {}

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

        local ready = {}
        for i = 1, #O._active do
            local entry = O._active[i]
            if not entry.pending then
                ready[#ready + 1] = entry
            end
        end

        local total = #ready
        if total == 0 then return {} end

        local start_idx = total - n + 1
        if start_idx < 1 then start_idx = 1 end

        local out = {}
        for i = start_idx, total do
            out[#out + 1] = ready[i]
        end
        return out
    end)

    if not ok then return nil end
    return result
end

local OBJECTIVES_ROOT_NAME = "kyohud_objectives_panel"
local MAX_SLOTS = 3
local REF_OBJ_FONT_SIZE = 20
local MIN_OBJ_FONT_SIZE = 12

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

function O:_clear_slot_prims()
    for i = 1, MAX_SLOTS do
        self._slot_prims[i] = nil
        self._slot_text_cache[i] = nil
        self._slot_amount_cache[i] = nil
        self._slot_fit_cache[i] = nil
        self._slot_visible_cache[i .. "_text"] = nil
        self._slot_visible_cache[i .. "_amount"] = nil
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

    local entries = O:select_visible()
    if not entries then entries = {} end

    local layout = self._layout_cache
    local sig = o_layout_fit_sig(layout)

    for i = 1, MAX_SLOTS do
        local entry = entries[i]
        local slot = self._slot_prims[i]
        if not slot then goto sync_continue end

        local text_str = (entry and type(entry.text) == "string") and entry.text or ""
        local amount_str = entry and mount_format_amount(entry) or nil

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
        local entry = entries[i]
        local source_text = (entry and type(entry.text) == "string") and entry.text or ""
        local fit = self._slot_fit_cache[i]
        local expected_display
        if fit and fit.source == source_text and fit.sig == o_layout_fit_sig(geom) then
            expected_display = fit.display
        else
            expected_display = source_text
        end
        local expected_amount = entry and mount_format_amount(entry) or ""

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

        ::verify_continue::
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
    local had = self._native_acquired or self._native_leaves or self._native_active_id
    if not had then return true end
    local nv = kyohud.hud.native_visibility
    if not nv then
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
    if not active_id then self:_release_native(); return end
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
            O._snapshot_manager = self
            O._active = {}
            O._by_id = {}
            O._last_hud_presented_id = nil
            O._last_hud_completed_id = nil
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
        O._snapshot_manager = self
        O._active = {}
        O._by_id = {}
        O._last_hud_presented_id = nil
        O._last_hud_completed_id = nil
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
end
