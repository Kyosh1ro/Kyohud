kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end

kyohud.hud = kyohud.hud or {}

local RT = kyohud.hud.runtime or {}
kyohud.hud.runtime = RT

RT._generation = RT._generation or 0
RT._heist_generation = RT._heist_generation or 0
RT._mounted = RT._mounted or false
RT._disabled = RT._disabled or false
RT._freeflight = RT._freeflight or false

-- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE: session-wide line cap.
RT._diag_lines = RT._diag_lines or 0

RT._h5_owner = RT._h5_owner or "kyohud_h5"
RT._h5_generation = RT._h5_generation or 0
RT._h5_targets = RT._h5_targets
RT._h5_source_id = RT._h5_source_id
-- TEMPORARY DIAGNOSTIC REMOVE BEFORE RELEASE: cumulative H5 phase costs, in
-- seconds, split per module. Mutated in place during a capture; allocated once
-- here, never per frame.
local H5_PHASE_KEYS = {
    "verify_p", "verify_w", "verify_e", "verify_c",
    "collect_p", "collect_w", "collect_e", "collect_c",
    "acq_p", "acq_w", "acq_e", "acq_c",
    "vis",
}

local function h5_phase_reset(phase)
    if type(phase) ~= "table" then return end
    for i = 1, #H5_PHASE_KEYS do
        phase[H5_PHASE_KEYS[i]] = 0
    end
end

local function h5_phase_init(phase)
    if type(phase) ~= "table" then phase = {} end
    for i = 1, #H5_PHASE_KEYS do
        if phase[H5_PHASE_KEYS[i]] == nil then phase[H5_PHASE_KEYS[i]] = 0 end
    end
    return phase
end

RT._h5_diag_phase = h5_phase_init(RT._h5_diag_phase)

local ROOT_NAME = "kyohud_root_panel"
local RECOVERY_INTERVAL = 0.5
local REQUIRED_CONTEXT = "lib/managers/hudmanagerpd2"

local BG_ROOT_NAME = "kyohud_shared_bg_panel"
local BG_BODY_NAME = "kyohud_shared_bg_body"
local BG_CUT_NAME = "kyohud_shared_bg_cut"
local BG_RADIUS = 6
local BG_R = 8 / 255
local BG_G = 9 / 255
local BG_B = 11 / 255
local BG_A = 0.86
local BG_THROTTLE = 0.05
local BG_TINT

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

local function finite(v)
    return type(v) == "number" and v == v and v ~= math.huge and v ~= -math.huge
end

-- TEMPORARY, user-authorized diagnostic. No menu/persistence, native writes,
-- forced GC or per-frame logging. One capture per process; remove after diagnosis.
-- Application time is for update intervals only: it may be cached within a frame.
-- os.clock measures block durations, but its platform-dependent granularity means
-- that a zero duration is NOT proof of a free operation. Instrumentation is included.
local PERF_KEYS = {
    "other", "player", "weapons", "equipment", "crew",
    "native_priority", "native_replace", "backdrop", "runtime",
    "combat",
}

local function perf_heap()
    if type(collectgarbage) ~= "function" then return nil end
    local ok, value = pcall(collectgarbage, "count")
    if ok and finite(value) then return value end
end

local function perf_wall_time()
    return Application:time()
end

local function perf_player_unit()
    return managers.player:player_unit()
end

local function perf_flags()
    local s = kyohud.settings or {}
    return string.format("player=%s crew=%s weapons=%s equipment=%s",
        tostring(s.enable_player == true), tostring(s.enable_crew == true),
        tostring(s.enable_weapons == true), tostring(s.enable_equipment == true))
end

-- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE. Record-only helpers: no native
-- writes, no font access, and no allocation outside an actual emission.
local DIAG_PREFIX = "[KyoHUD][H4Diag] "
local DIAG_MAX_LINES = 60
local DIAG_PERSIST_INTERVAL = 5.0
local H4DIAG = "h4diag"

-- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE: opt-in via sentinel file only.
-- Read once when this chunk loads. If the file is absent, every diagnostic stays
-- silent and neither the line counter nor the log is touched.
if RT._diag_armed == nil then
    RT._diag_armed = false
    if type(ModPath) == "string" and type(io) == "table" and type(io.open) == "function" then
        local ok, handle = pcall(io.open, ModPath .. H4DIAG, "r")
        if ok and handle then
            RT._diag_armed = true
            pcall(handle.close, handle)
        end
    end
end

local function diag_emit(line)
    if RT._diag_armed ~= true then return false end
    local count = RT._diag_lines or 0
    if count >= DIAG_MAX_LINES then return false end
    RT._diag_lines = count + 1
    if type(log) == "function" then pcall(log, DIAG_PREFIX .. line) end
    return true
end

local function diag_panel_name(panel)
    if not panel then return "nil" end
    if not panel_alive(panel) then return "dead" end
    local ok, name = pcall(function() return panel:name() end)
    if ok and type(name) == "string" and name ~= "" then return name end
    return "?"
end

local function diag_reason(leaf, parent, child_name)
    if not leaf and not parent and not child_name then return "-" end
    local child = child_name or diag_panel_name(leaf)
    local par = parent
    if not par and leaf then
        local ok, value = pcall(function() return leaf:parent() end)
        if ok then par = value end
    end
    return child .. "@" .. diag_panel_name(par)
end

local function diag_value(value)
    return value == nil and "-" or tostring(value)
end

local function diag_now(t)
    if finite(t) then return t end
    local ok, now = pcall(perf_wall_time)
    if ok and finite(now) then return now end
    return nil
end

-- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE: H5 group state transitions only.
local function h5_diag_local(state, p_ok, p_vis, targets, verify)
    local record = RT._h5_diag_state
    if not record then record = {}; RT._h5_diag_state = record end
    if record.local_flag == state then return end
    local first = record.local_flag == nil
    record.local_flag = state
    if first then return end
    diag_emit(string.format("group=local_p state=%s p_ok=%s p_vis=%s targets=%d verify=%s",
        state, tostring(p_ok == true), tostring(p_vis == true),
        targets or 0, tostring(verify == true)))
end

local function h5_diag_crew(reason, c_ok, verify, c_vis, targets)
    local record = RT._h5_diag_state
    if not record then record = {}; RT._h5_diag_state = record end
    targets = targets or 0
    if record.crew_reason == reason and record.crew_targets == targets then return end
    local first = record.crew_reason == nil
    record.crew_reason = reason
    record.crew_targets = targets
    if first then return end
    diag_emit(string.format("group=crew reason=%s c_ok=%s verify=%s c_vis=%s targets=%d",
        reason, tostring(c_ok == true), tostring(verify == true),
        tostring(c_vis == true), targets))
end

function RT:_perf_emit(s, reason)
    self._perf_done = true
    self._perf_diagnostic = nil
    self._perf_result = s
    local prefix = "[KyoHUD][Perf] "
    local frames = s.frames or 0
    local elapsed = s.started and ((s.now or s.started) - s.started) or 0
    local intervals = math.max(0, frames - 1)
    local lines = {
        prefix .. string.format("%s capture=%.2fs frames=%d; clock=os.clock, quantifie: zero non concluant; overhead inclus",
            reason, elapsed, frames),
        prefix .. string.format("Intervalles HUD update (pas GPU): mean=%.3fms max=%.3fms >16.7=%d >33.3=%d >50=%d",
            intervals > 0 and (s.gap_sum or 0) * 1000 / intervals or 0,
            (s.gap_max or 0) * 1000, s.over16 or 0, s.over33 or 0, s.over50 or 0),
        prefix .. "Debut: " .. (s.flags or "n/a") .. "; fin: " .. perf_flags(),
    }
    for _, key in ipairs(PERF_KEYS) do
        local m = s.metrics and s.metrics[key]
        if m then
            lines[#lines + 1] = prefix .. string.format("%s calls=%d mean=%.3fms max=%.3fms sum=%.3fms",
                key, m.calls, m.calls > 0 and m.total * 1000 / m.calls or 0,
                m.peak * 1000, m.total * 1000)
        end
    end
    -- TEMPORARY DIAGNOSTIC REMOVE BEFORE RELEASE: H5 phase breakdown in the
    -- COMPLETE report only, as cumulative milliseconds over the capture.
    if reason == "COMPLETE" then
        local phase = self._h5_diag_phase
        if type(phase) == "table" then
            local function ms(key) return (tonumber(phase[key]) or 0) * 1000 end
            lines[#lines + 1] = string.format(
                "[KyoHUD][Perf][H5] verify P=%.3f W=%.3f E=%.3f C=%.3f collect P=%.3f W=%.3f E=%.3f C=%.3f acq P=%.3f W=%.3f E=%.3f C=%.3f vis=%.3f",
                ms("verify_p"), ms("verify_w"), ms("verify_e"), ms("verify_c"),
                ms("collect_p"), ms("collect_w"), ms("collect_e"), ms("collect_c"),
                ms("acq_p"), ms("acq_w"), ms("acq_e"), ms("acq_c"), ms("vis"))
        end
    end
    local heap_end = perf_heap()
    local heap = s.heap_start and heap_end and string.format("%.1f -> %.1f KiB", s.heap_start, heap_end) or "n/a"
    lines[#lines + 1] = prefix .. "Tas Lua=" .. heap .. "; instantanes, pas pauses GC. runtime inclusif; autres lignes exclusives. Combat/buffs: ligne dediee hors runtime; hooks acteurs non mesures. STOP."
    self._perf_report = table.concat(lines, "\n")
    if type(log) == "function" then pcall(log, self._perf_report) end
    -- TEMPORARY DIAGNOSTIC REMOVE BEFORE RELEASE: zero the H5 phase sums once
    -- the COMPLETE report has consumed them.
    if reason == "COMPLETE" then
        h5_phase_reset(self._h5_diag_phase)
    end
end

local function perf_record(s, key, elapsed)
    local m = s.metrics[key]
    m.calls = m.calls + 1
    m.total = m.total + elapsed
    m.peak = math.max(m.peak, elapsed)
end

-- TEMPORARY DIAGNOSTIC REMOVE BEFORE RELEASE: guarded phase clocks. A missing
-- os.clock or a negative delta is ignored, matching the existing perf clocks.
local function h5_phase_begin(phase)
    if not phase then return nil end
    if type(os) ~= "table" or type(os.clock) ~= "function" then return nil end
    local ok, now = pcall(os.clock)
    if not ok or not finite(now) then return nil end
    return now
end

local function h5_phase_end(phase, key, started)
    if not phase or not started or not key then return end
    local ok, now = pcall(os.clock)
    if not ok or not finite(now) then return end
    local delta = now - started
    if delta < 0 then return end
    phase[key] = (phase[key] or 0) + delta
end

-- TEMPORARY DIAGNOSTIC REMOVE BEFORE RELEASE: map an H5 group key to the
-- owning module counter without allocating. Local groups end with _p/_w/_e;
-- crew groups are the only keys starting with "c".
local function h5_phase_acq_key(group_key)
    if type(group_key) ~= "string" then return nil end
    local len = #group_key
    if len < 2 then return nil end
    if string.byte(group_key, 1) == 99 then return "acq_c" end
    local last = string.byte(group_key, len)
    if last == 112 then return "acq_p" end
    if last == 119 then return "acq_w" end
    if last == 101 then return "acq_e" end
    return nil
end

function RT:_perf_begin()
    if self._perf_done or self._perf_enabled == false then return nil end
    if kyohud.settings.enable_hud_foundation ~= true or not self._mounted
        or self._disabled or self._freeflight then
        if self._perf_diagnostic and self._perf_diagnostic.started then
            self:_perf_emit(self._perf_diagnostic, "INTERRUPTED (HUD inactive)")
        else
            self._perf_diagnostic = nil
        end
        return nil
    end
    if not Application or not os or type(os.clock) ~= "function" then return nil end
    if not self._perf_diagnostic then
        -- Do not spend the single capture in level loading before player spawn.
        local unit_ok, unit = pcall(perf_player_unit)
        if not unit_ok or not panel_alive(unit) then return nil end
    end
    local ok, now = pcall(perf_wall_time)
    local s = self._perf_diagnostic or {born = now}
    if not ok or not finite(now) or now < s.born or (s.now and now < s.now) then
        self:_perf_emit(s, "ABORTED (Application clock invalid)")
        return nil
    end
    self._perf_diagnostic = s
    if not s.started then
        if now - s.born < 5 then return nil end
        s.started = now
        s.frames, s.gap_sum, s.gap_max = 0, 0, 0
        s.over16, s.over33, s.over50 = 0, 0, 0
        s.metrics = {}
        for _, key in ipairs(PERF_KEYS) do
            s.metrics[key] = {calls = 0, total = 0, peak = 0}
        end
        s.heap_start, s.flags = perf_heap(), perf_flags()
        -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE: reset the combat draw
        -- counters with the other accumulators so this capture starts from zero.
        local draw_diag = kyohud._draw_diag
        if type(draw_diag) == "table" then
            draw_diag.calls, draw_diag.sum, draw_diag.max = 0, 0, 0
        end
        -- TEMPORARY DIAGNOSTIC REMOVE BEFORE RELEASE: start the H5 phase sums
        -- from zero with the other capture accumulators.
        h5_phase_reset(RT._h5_diag_phase)
    end
    if s.now then
        local gap = now - s.now
        s.gap_sum = s.gap_sum + gap
        s.gap_max = math.max(s.gap_max, gap)
        if gap > 1 / 60 then s.over16 = s.over16 + 1 end
        if gap > 1 / 30 then s.over33 = s.over33 + 1 end
        if gap > 0.05 then s.over50 = s.over50 + 1 end
    end
    s.now = now
    local cpu_ok, cpu = pcall(os.clock)
    if not cpu_ok or not finite(cpu) or (s.marker and cpu < s.marker) then
        self:_perf_emit(s, "ABORTED (os.clock invalid)")
        return nil
    end
    s.frame_cpu, s.marker = cpu, cpu
    return s
end

function RT:_perf_mark(s, key)
    if self._perf_done then return end
    local ok, now = pcall(os.clock)
    if not ok or not finite(now) or now < s.marker then
        self:_perf_emit(s, "ABORTED (os.clock invalid)")
        return
    end
    perf_record(s, key, now - s.marker)
    s.marker = now
end

function RT:_perf_finish(s)
    self:_perf_mark(s, "other")
    if self._perf_done then return end
    perf_record(s, "runtime", s.marker - s.frame_cpu)
    s.frames = s.frames + 1
    -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE: include the combat draw
    -- counters in the report; only the capture-start block resets them.
    local combat = s.metrics and s.metrics.combat
    if combat then
        local draw_diag = kyohud._draw_diag
        if type(draw_diag) == "table" then
            combat.calls = tonumber(draw_diag.calls) or 0
            combat.total = tonumber(draw_diag.sum) or 0
            combat.peak = tonumber(draw_diag.max) or 0
        else
            combat.calls, combat.total, combat.peak = 0, 0, 0
        end
    end
    if s.now - s.started >= 20 then self:_perf_emit(s, "COMPLETE") end
end

local function lookup_method(obj, method_name)
    return obj[method_name]
end

local function safe_call(obj, method_name, ...)
    if obj == nil then return CALL_MISSING, nil end
    local ok_get, method_or_err = pcall(lookup_method, obj, method_name)
    if not ok_get then return CALL_ERROR, nil end
    if type(method_or_err) ~= "function" then return CALL_MISSING, nil end
    local ok_call, result = pcall(method_or_err, obj, ...)
    if not ok_call then return CALL_ERROR, nil end
    return CALL_OK, result
end

local function get_parent_panel(manager)
    if not manager then return nil end
    local ok, access = pcall(function()
        return manager:script(PlayerBase.PLAYER_INFO_HUD_PD2)
    end)
    if not ok or type(access) ~= "table" then return nil end
    local p = access.panel
    if p == nil then return nil end
    if not panel_alive(p) then return nil end
    return p
end

local function create_root(parent)
    if not parent then return nil end
    local status, root = safe_call(parent, "panel", {name = ROOT_NAME})
    if status ~= CALL_OK or root == nil then return nil end
    return root
end

local function apply_visibility()
    local root = RT._root_panel
    if root == nil then return end
    if not panel_alive(root) then return end
    local should_show = (not RT._disabled) and (not RT._freeflight)
    local status, _ = safe_call(root, "set_visible", should_show)
    if status ~= CALL_OK then
        RT._needs_refresh = true
    end
end

function RT:_try_remove_root()
    local root = self._root_panel
    if not root then return true end
    if not panel_alive(root) then
        self._root_panel = nil
        return true
    end
    local parent = self._parent_panel
    if not parent or not panel_alive(parent) then return false end
    local status, result = safe_call(parent, "remove", root)
    if status ~= CALL_OK then return false end
    if result == false then return false end
    self._root_panel = nil
    return true
end

function RT:mount(manager)
    if kyohud.settings.enable_hud_foundation ~= true then return end
    if is_vr() then return end
    local mgr = manager or self._manager
    if not mgr then return end
    self._manager = mgr

    local parent = get_parent_panel(mgr)
    if not parent then return end

    if self._mounted and self._root_panel and panel_alive(self._root_panel) and self._parent_panel == parent then
        return
    end

    if self._root_panel and not panel_alive(self._root_panel) then
        self._root_panel = nil
    end

    local child_status, existing = safe_call(parent, "child", ROOT_NAME)
    if child_status ~= CALL_OK then
        return
    end
    if existing ~= nil and panel_alive(existing) then
        if self._root_panel ~= nil and existing == self._root_panel then
            self._parent_panel = parent
            self._mounted = true
            self:_do_refresh()
            self:_coordinate_mission("mount")
            self:_coordinate_objectives("mount")
            self:_coordinate_alerts("mount")
            self:_coordinate_assault("mount")
            self:_coordinate_player("mount")
            self:_coordinate_weapons("mount")
            self:_coordinate_equipment("mount")
            self:_coordinate_crew("mount")
            self:_sync_local_backdrop()
            return
        end
        return
    end

    if self._root_panel then
        if self._parent_panel ~= parent then
            local removed = self:_try_remove_root()
            if not removed then
                return
            end
        end
    end

    local root = create_root(parent)
    if not root then return end
    self._root_panel = root
    self._parent_panel = parent
    self._mounted = true
    self._generation = self._generation + 1
    if type(mgr.disabled) == "function" then
        local dok, dval = pcall(mgr.disabled, mgr)
        if dok then self._disabled = (dval == true) end
    end
    self:_do_refresh()
    self:_coordinate_mission("mount")
    self:_coordinate_objectives("mount")
    self:_coordinate_alerts("mount")
    self:_coordinate_assault("mount")
    self:_coordinate_player("mount")
    self:_coordinate_weapons("mount")
    self:_coordinate_equipment("mount")
    self:_coordinate_crew("mount")
    self:_sync_local_backdrop()
end

function RT:_coordinate_crew(method_name, ...)
    local crew = kyohud.hud.crew
    if crew and type(crew[method_name]) == "function" and self._manager then
        return crew[method_name](crew, self._manager, ...)
    end
end

-- Presentation-only handshake: vacate the native objective reservation before
-- any leaf is restored. No polling, source collection or new hook is involved.
function RT:set_objectives_covered(covered)
    covered = covered == true
    if self._objectives_covered == covered then return end
    self._objectives_covered = covered
    local mission = kyohud.hud.mission
    if mission and mission._mounted and panel_alive(mission._root_panel) then
        safe_call(mission._root_panel, "set_visible", false)
        mission:_update_layout()
        mission:_ensure_primitives()
        mission:_sync_primitives()
        if mission:_verify_render() then
            safe_call(mission._root_panel, "set_visible", true)
        else
            mission:_handle_render_failure()
        end
    end
end

function RT:_coordinate_mission(method_name, ...)
    local mission = kyohud.hud.mission
    if mission and type(mission[method_name]) == "function" and self._manager then
        mission[method_name](mission, self._manager, ...)
    end
end

function RT:_coordinate_objectives(method_name, ...)
    local objectives = kyohud.hud.objectives
    if objectives and type(objectives[method_name]) == "function" and self._manager then
        objectives[method_name](objectives, self._manager, ...)
    end
end

function RT:_coordinate_alerts(method_name, ...)
    local alerts = kyohud.hud.alerts
    if alerts and type(alerts[method_name]) == "function" and self._manager then
        alerts[method_name](alerts, self._manager, ...)
    end
end

function RT:_coordinate_assault(method_name, ...)
    local assault = kyohud.hud.assault
    if assault and type(assault[method_name]) == "function" and self._manager then
        assault[method_name](assault, self._manager, ...)
    end
end

function RT:_coordinate_player(method_name, ...)
    local player = kyohud.hud.player
    if player and type(player[method_name]) == "function" and self._manager then
        player[method_name](player, self._manager, ...)
    end
end

function RT:_coordinate_weapons(method_name, ...)
    local weapons = kyohud.hud.weapons
    if weapons and type(weapons[method_name]) == "function" and self._manager then
        weapons[method_name](weapons, self._manager, ...)
    end
end

function RT:_coordinate_equipment(method_name, ...)
    local equipment = kyohud.hud.equipment
    if equipment and type(equipment[method_name]) == "function" and self._manager then
        equipment[method_name](equipment, self._manager, ...)
    end
end

function RT:_do_refresh()
    if not self._root_panel then return end
    if not panel_alive(self._root_panel) then return end
    local parent = self._parent_panel
    if not parent then return end
    local failed = false
    local w_status, w = safe_call(parent, "w")
    local h_status, h = safe_call(parent, "h")
    if w_status ~= CALL_OK or h_status ~= CALL_OK then
        failed = true
    end
    if w and h then
        local shape_status, _ = safe_call(self._root_panel, "set_shape", 0, 0, w, h)
        if shape_status ~= CALL_OK then
            failed = true
        end
    end
    local layout = kyohud.hud.layout
    if layout and type(layout.resolve) == "function" then
        local scale = kyohud.settings.hud_scale or 1
        self._layout = layout.resolve(w or 0, h or 0, scale)
    end
    local should_show = (not self._disabled) and (not self._freeflight)
    local vis_status, _ = safe_call(self._root_panel, "set_visible", should_show)
    if vis_status ~= CALL_OK then
        failed = true
    end
    self._needs_refresh = failed or nil
end

function RT:unmount()
    self:_release_h5()
    self:_coordinate_crew("unmount")
    self:_coordinate_mission("unmount")
    self:_coordinate_objectives("unmount")
    self:_coordinate_alerts("unmount")
    self:_coordinate_assault("unmount")
    self:_coordinate_player("unmount")
    self:_coordinate_weapons("unmount")
    self:_coordinate_equipment("unmount")
    self:_clear_local_backdrop()
    if not self._mounted and not self._root_panel then return true end
    if self._root_panel then
        local removed = self:_try_remove_root()
        if not removed then
            self._mounted = false
            return false
        end
    end
    self._parent_panel = nil
    self._mounted = false
    self._layout = nil
    return true
end

function RT:rebuild(manager)
    self:_release_h5()
    self:_coordinate_crew("unmount")
    self:_coordinate_mission("unmount")
    self:_coordinate_objectives("unmount")
    self:_coordinate_alerts("unmount")
    self:_coordinate_assault("unmount")
    self:_coordinate_player("unmount")
    self:_coordinate_weapons("unmount")
    self:_coordinate_equipment("unmount")
    self:_clear_local_backdrop()
    if self._root_panel then
        local removed = self:_try_remove_root()
        if not removed then
            self:_coordinate_mission("mount", manager)
            self:_coordinate_objectives("mount", manager)
            self:_coordinate_alerts("mount", manager)
            self:_coordinate_assault("mount", manager)
            self:_coordinate_player("mount", manager)
            self:_coordinate_weapons("mount", manager)
            self:_coordinate_equipment("mount", manager)
            self:_coordinate_crew("mount")
            self:_sync_local_backdrop()
            return
        end
    end
    self._mounted = false
    self:mount(manager)
    self:_coordinate_mission("rebuild", manager)
    self:_coordinate_objectives("rebuild", manager)
    self:_coordinate_alerts("rebuild", manager)
    self:_coordinate_assault("rebuild", manager)
    self:_coordinate_player("rebuild", manager)
    self:_coordinate_weapons("rebuild", manager)
    self:_coordinate_equipment("rebuild", manager)
    self:_coordinate_crew("rebuild")
    self:_sync_local_backdrop()
end

function RT:refresh_settings(manager)
    if kyohud.settings.enable_hud_foundation == true then
        if not self._mounted or not self._root_panel or not panel_alive(self._root_panel) then
            self:mount(manager)
            return
        end
        self:_do_refresh()
        self:_coordinate_mission("refresh_settings")
        self:_coordinate_objectives("refresh_settings")
        self:_coordinate_alerts("refresh_settings")
        self:_coordinate_assault("refresh_settings")
        self:_coordinate_player("refresh_settings")
        self:_coordinate_weapons("refresh_settings")
        self:_coordinate_equipment("refresh_settings")
        self:_coordinate_crew("refresh_settings")
        self:_sync_local_backdrop()
    else
        if self._mounted or self._root_panel then
            self:unmount()
        end
    end
end

function RT:on_heist_start(manager)
    local mgr = manager or self._manager
    if not mgr then return end
    self._manager = mgr
    if self._mounted_manager_id == mgr then return end
    self._heist_generation = self._heist_generation + 1
    self._mounted_manager_id = mgr
    self:_coordinate_player("on_heist_start")
    self:_coordinate_weapons("on_heist_start")
    self:_coordinate_equipment("on_heist_start")
    self:_coordinate_crew("on_heist_start")
end

function RT:destroy(manager)
    if manager and self._manager and manager ~= self._manager then
        return
    end
    self:_coordinate_mission("destroy", manager)
    self:_coordinate_objectives("destroy", manager)
    self:_coordinate_alerts("destroy", manager)
    self:_coordinate_assault("destroy", manager)
    self:_coordinate_player("destroy", manager)
    self:_coordinate_weapons("destroy", manager)
    self:_coordinate_equipment("destroy", manager)
    self:_coordinate_crew("destroy")
    self:unmount()
    self._mounted_manager_id = nil
end

function RT:update(manager, t, dt)
    -- quality split approved 2026-11-10: a module whose update does not run on
    -- this frame must never retain the previous frame's ran/verified state.
    local P = kyohud.hud.player
    local W = kyohud.hud.weapons
    local E = kyohud.hud.equipment
    local C = kyohud.hud.crew
    if P then P._update_ran_now = false; P._verify_ok_now = false end
    if W then W._update_ran_now = false; W._verify_ok_now = false end
    if E then E._update_ran_now = false; E._verify_ok_now = false end
    if C then C._update_ran_now = false; C._verify_ok_now = false end
    if not t then return end
    local perf = self:_perf_begin()

    if kyohud.settings.enable_hud_foundation == true then
        self:_coordinate_alerts("update", t, dt)
        self:_coordinate_assault("update", t, dt)
        if perf then self:_perf_mark(perf, "other") end
        self:_coordinate_player("update", t, dt)
        if perf then self:_perf_mark(perf, "player") end
        self:_coordinate_weapons("update", t, dt)
        if perf then self:_perf_mark(perf, "weapons") end
        self:_coordinate_equipment("update", t, dt)
        if perf then self:_perf_mark(perf, "equipment") end
        local crew_receipt = self:_coordinate_crew("update", t, dt)
        if perf then self:_perf_mark(perf, "crew") end
        self:_sync_local_backdrop(t, perf, crew_receipt)
        if perf then self:_perf_mark(perf, "backdrop") end
    end

    if kyohud.settings.enable_hud_foundation == true and kyohud.settings.enable_objectives == true then
        local objectives = kyohud.hud.objectives
        if objectives and type(objectives.animate) == "function" and objectives._mounted then
            objectives:animate(t, dt)
        end
    end

    if self._last_recovery_time ~= nil and t >= self._last_recovery_time and (t - self._last_recovery_time) < RECOVERY_INTERVAL then
        if perf then self:_perf_finish(perf) end
        return
    end

    local mgr = manager or self._manager
    self._last_recovery_time = t

    if kyohud.settings.enable_hud_foundation ~= true then
        self:_retry_pending_h5_releases()
        self:unmount()
        if perf then self:_perf_finish(perf) end
        return
    end

    self:_retry_pending_h5_releases()

    if self._needs_refresh and self._root_panel and panel_alive(self._root_panel) then
        self:_do_refresh()
        self:_coordinate_mission("update", t, dt)
        self:_coordinate_objectives("update", t, dt)
        if perf then self:_perf_finish(perf) end
        return
    end

    if mgr and not self._manager then
        self._manager = mgr
    end
    self:mount(mgr)
    self:_coordinate_mission("update", t, dt)
    self:_coordinate_objectives("update", t, dt)
    if perf then self:_perf_finish(perf) end
end

-- quality split approved 2026-11-10: throttled frames read the live root
-- instead of running the full verifier. No value is cached across frames.
local function h5_light_root_ok(module)
    if not module then return false end
    local root = module._root
    if not root or not panel_alive(root) then return false end
    local vs, visible = safe_call(root, "visible")
    if vs ~= CALL_OK or visible ~= true then return false end
    local as, alpha = safe_call(root, "alpha")
    if as ~= CALL_OK or not finite(alpha) or alpha <= 0 then return false end
    return true
end

local function h5_light_crew_ok(module)
    if not h5_light_root_ok(module) then return false end
    local expected = module._expected_positions
    if type(expected) ~= "table" then return false end
    local cards = module._cards
    if type(cards) ~= "table" then return false end
    for i = 1, 3 do
        if expected[i] then
            local card = cards[i]
            local root = type(card) == "table" and card.root or nil
            return root ~= nil and panel_alive(root)
        end
    end
    return false
end

local function _module_verified(module, certifications)
    local c = certifications and certifications[module]
    if c then
        if c.root == module._root and c.manager == module._manager
            and c.verify == module.verify then
            return c.ok
        end
        -- A replaced verifier invalidates the same-pass receipt only.
        local ok, result = pcall(module.verify, module)
        return ok and result == true
    end
    -- quality split approved 2026-11-10: a completed H5 pass without a receipt
    -- for this module fails closed instead of starting a new full verify.
    if certifications ~= nil then return false end
    local ok, result = pcall(module.verify, module)
    return ok and result == true
end

local function _backdrop_coverage(certifications)
    local settings = kyohud.settings
    if settings.enable_player ~= true then return false end
    if settings.enable_weapons ~= true then return false end
    if settings.enable_equipment ~= true then return false end
    local P = kyohud.hud.player
    local W = kyohud.hud.weapons
    local E = kyohud.hud.equipment
    if not P or not W or not E then return false end
    if not P._mounted or not W._mounted or not E._mounted then return false end
    if not _module_verified(P, certifications) then return false end
    if not _module_verified(W, certifications) then return false end
    if not _module_verified(E, certifications) then return false end
    local pv, pvis = safe_call(P._root, "visible")
    if pv ~= CALL_OK or pvis ~= true then return false end
    local wv, wvis = safe_call(W._root, "visible")
    if wv ~= CALL_OK or wvis ~= true then return false end
    local ev, evis = safe_call(E._root, "visible")
    if ev ~= CALL_OK or evis ~= true then return false end
    return true
end

function RT:_clear_local_backdrop()
    self._local_bg_panel = nil
    self._local_bg_body = nil
    self._local_bg_cut = nil
    self._local_bg_layout = nil
    self._local_backdrop_verified = false
    self._local_bg_verts_cache = nil
    self._last_backdrop_sync = nil
end

function RT:_backdrop_cut_verts(geom)
    local w = geom.w
    local h = geom.h
    local r = geom.radius
    local cache = self._local_bg_verts_cache
    if cache and cache.key_w == w and cache.key_h == h and cache.key_r == r then
        return cache.verts
    end
    local verts = {}
    local n = 6
    local pi = math.pi
    local half_pi = pi / 2
    local step = half_pi / n
    local cos = math.cos
    local sin = math.sin
    local function fan(cx, cy, a0)
        for i = 0, n - 1 do
            local ai = a0 + i * step
            local aj = a0 + (i + 1) * step
            verts[#verts + 1] = Vector3(cx, cy, 0)
            verts[#verts + 1] = Vector3(cx + r * cos(ai), cy + r * sin(ai), 0)
            verts[#verts + 1] = Vector3(cx + r * cos(aj), cy + r * sin(aj), 0)
        end
    end
    fan(r, r, pi)
    fan(r, h - r, half_pi)
    fan(w - r, r, pi + half_pi)
    fan(w - r, h - r, 0)
    verts[#verts + 1] = Vector3(0, r, 0)
    verts[#verts + 1] = Vector3(r, r, 0)
    verts[#verts + 1] = Vector3(r, h - r, 0)
    verts[#verts + 1] = Vector3(0, r, 0)
    verts[#verts + 1] = Vector3(r, h - r, 0)
    verts[#verts + 1] = Vector3(0, h - r, 0)
    verts[#verts + 1] = Vector3(w - r, r, 0)
    verts[#verts + 1] = Vector3(w, r, 0)
    verts[#verts + 1] = Vector3(w, h - r, 0)
    verts[#verts + 1] = Vector3(w - r, r, 0)
    verts[#verts + 1] = Vector3(w, h - r, 0)
    verts[#verts + 1] = Vector3(w - r, h - r, 0)
    self._local_bg_verts_cache = {key_w = w, key_h = h, key_r = r, verts = verts}
    return verts
end

function RT:_local_backdrop_geometry()
    local P = kyohud.hud.player
    local W = kyohud.hud.weapons
    local E = kyohud.hud.equipment
    if not P or not W or not E then return nil end
    local parent = self._parent_panel
    if not parent or not panel_alive(parent) then return nil end
    local pw_s, pw = safe_call(parent, "w")
    local ph_s, ph = safe_call(parent, "h")
    if pw_s ~= CALL_OK or ph_s ~= CALL_OK then return nil end
    if type(pw) ~= "number" or type(ph) ~= "number" or pw <= 0 or ph <= 0 then return nil end
    local layout = kyohud.hud.layout
    if not layout or type(layout.local_loadout) ~= "function" then return nil end
    local scale = kyohud.settings.hud_scale or 1
    local g = layout.local_loadout(pw, ph, scale)
    if not g then return nil end
    local bottom_ok, bottom = pcall(function()
        if not P._layout_cache then return nil end
        local dl = P:_desired_layout()
        if not dl then return nil end
        return P._layout_cache.y + dl.gauge.y + 32 * dl.gauge_scale + 14 * g.e
    end)
    if not bottom_ok or type(bottom) ~= "number" then return nil end
    local e_root_y = g.y
    if E and E._mounted and E._root and panel_alive(E._root) then
        local ey_s, ey = safe_call(E._root, "y")
        if ey_s == CALL_OK and finite(ey) then
            e_root_y = math.min(g.y, ey)
        end
    end
    local hg = bottom - e_root_y
    if type(hg) ~= "number" or hg ~= hg or hg <= 0 then return nil end
    local radius = BG_RADIUS * g.e
    local background_w = g.w + 2 * g.e
    local body_w = background_w - 2 * radius
    if body_w <= 0 then return nil end
    if hg < 2 * radius then return nil end
    return {
        x = g.x, y = e_root_y, w = background_w, h = hg,
        e = g.e, radius = radius, cut_w = background_w, body_x = radius, body_w = body_w,
    }
end

function RT:_verify_local_backdrop(certifications)
    self._local_backdrop_verified = false
    if not _backdrop_coverage(certifications) then return false end
    local bg = self._local_bg_panel
    if not bg or not panel_alive(bg) then return false end
    local root = self._root_panel
    if not root or not panel_alive(root) then return false end
    local bp_s, bp = safe_call(bg, "parent")
    if bp_s ~= CALL_OK or bp ~= root then return false end
    local cs, child = safe_call(root, "child", BG_ROOT_NAME)
    if cs ~= CALL_OK or child ~= bg then return false end
    local ls, layer = safe_call(bg, "layer")
    if ls ~= CALL_OK or not finite(layer) or math.abs(layer - (-1)) > 0.01 then return false end
    local vs, vis = safe_call(bg, "visible")
    if vs ~= CALL_OK or vis ~= true then return false end
    local als, alpha = safe_call(bg, "alpha")
    if als ~= CALL_OK or not finite(alpha) or math.abs(alpha - 1) > 0.01 then return false end
    local geom = self:_local_backdrop_geometry()
    if not geom then return false end
    local function chk_geom(prim, dx, dy, dw, dh)
        local sx, ax = safe_call(prim, "x")
        local sy, ay = safe_call(prim, "y")
        local sw, aw = safe_call(prim, "w")
        local sh, ah = safe_call(prim, "h")
        if sx ~= CALL_OK or sy ~= CALL_OK or sw ~= CALL_OK or sh ~= CALL_OK then return false end
        if not finite(ax) or not finite(ay) or not finite(aw) or not finite(ah) then return false end
        if not finite(dx) or not finite(dy) or not finite(dw) or not finite(dh) then return false end
        if math.abs(ax - dx) > 0.5 then return false end
        if math.abs(ay - dy) > 0.5 then return false end
        if math.abs(aw - dw) > 0.5 then return false end
        if math.abs(ah - dh) > 0.5 then return false end
        return true
    end
    if not chk_geom(bg, geom.x, geom.y, geom.w, geom.h) then return false end
    local body = self._local_bg_body
    if not body or not panel_alive(body) then return false end
    local bdp_s, bdp = safe_call(body, "parent")
    if bdp_s ~= CALL_OK or bdp ~= bg then return false end
    local bs, bchild = safe_call(bg, "child", BG_BODY_NAME)
    if bs ~= CALL_OK or bchild ~= body then return false end
    local bvs, bvis = safe_call(body, "visible")
    if bvs ~= CALL_OK or bvis ~= true then return false end
    local bls, blayer = safe_call(body, "layer")
    if bls ~= CALL_OK or not finite(blayer) or math.abs(blayer) > 0.01 then return false end
    if not chk_geom(body, geom.body_x, 0, geom.body_w, geom.h) then return false end
    local bc_ok, bc = pcall(function() return body:color() end)
    if not bc_ok or not bc then return false end
    if not finite(bc.r) or math.abs(bc.r - BG_R) >= 0.005 then return false end
    if not finite(bc.g) or math.abs(bc.g - BG_G) >= 0.005 then return false end
    if not finite(bc.b) or math.abs(bc.b - BG_B) >= 0.005 then return false end
    local ba_ok, ba = pcall(function() return body:alpha() end)
    if not ba_ok or not finite(ba) or math.abs(ba - BG_A) >= 0.005 then return false end
    local cut = self._local_bg_cut
    if not cut or not panel_alive(cut) then return false end
    local cdp_s, cdp = safe_call(cut, "parent")
    if cdp_s ~= CALL_OK or cdp ~= bg then return false end
    local cs2, cchild = safe_call(bg, "child", BG_CUT_NAME)
    if cs2 ~= CALL_OK or cchild ~= cut then return false end
    local cvs, cvis = safe_call(cut, "visible")
    if cvs ~= CALL_OK or cvis ~= true then return false end
    local cls, clayer = safe_call(cut, "layer")
    if cls ~= CALL_OK or not finite(clayer) or math.abs(clayer) > 0.01 then return false end
    if not chk_geom(cut, 0, 0, geom.w, geom.h) then return false end
    local cc_ok, cc = pcall(function() return cut:color() end)
    if not cc_ok or not cc then return false end
    if not finite(cc.r) or math.abs(cc.r - BG_R) >= 0.005 then return false end
    if not finite(cc.g) or math.abs(cc.g - BG_G) >= 0.005 then return false end
    if not finite(cc.b) or math.abs(cc.b - BG_B) >= 0.005 then return false end
    local ca_ok, ca = pcall(function() return cut:alpha() end)
    if not ca_ok or not finite(ca) or math.abs(ca - BG_A) >= 0.005 then return false end
    self._local_backdrop_verified = true
    return true
end

local NATIVE_DEPTH = 6
local SPECIAL_EQUIP_MAX = 64

local READ_SLOTS = {visible = 1, alpha = 3, parent = 5, x = 7, y = 9, w = 11, h = 13, text = 15}

-- Priority reads share ancestry only during this read-only pass. Discard before
-- owned visibility writes and H5; nothing is retained between frames.
local function _pass_read(cache, obj, method)
    local slot = READ_SLOTS[method]
    if not cache or not obj or not slot then return safe_call(obj, method) end
    local entry = cache[obj]
    if not entry then entry = {}; cache[obj] = entry end
    if entry[slot] ~= nil then return entry[slot], entry[slot + 1] end
    local status, value = safe_call(obj, method)
    entry[slot], entry[slot + 1] = status, value
    return status, value
end

local function _effective_visible(panel, cache)
    if not panel_alive(panel) then return false end
    local vis_s, vis = _pass_read(cache, panel, "visible")
    if vis_s ~= CALL_OK then return nil end
    if vis ~= true then return false end
    local depth = 0
    local current = panel
    while depth < NATIVE_DEPTH do
        local ps, parent = _pass_read(cache, current, "parent")
        if ps ~= CALL_OK then return nil end
        if not parent then break end
        if not panel_alive(parent) then return false end
        local pvs, pvis = _pass_read(cache, parent, "visible")
        if pvs ~= CALL_OK then return nil end
        if pvis ~= true then return false end
        current = parent
        depth = depth + 1
    end
    return true
end

local function _effective_alpha(panel, cache)
    if not panel_alive(panel) then return 0 end
    local als, alpha = _pass_read(cache, panel, "alpha")
    if als ~= CALL_OK then return nil end
    if not finite(alpha) then return nil end
    if alpha <= 0 then return 0 end
    local cumulative = alpha
    local depth = 0
    local current = panel
    while depth < NATIVE_DEPTH and cumulative > 0 do
        local ps, parent = _pass_read(cache, current, "parent")
        if ps ~= CALL_OK then return nil end
        if not parent then break end
        if not panel_alive(parent) then return 0 end
        local pas, palpha = _pass_read(cache, parent, "alpha")
        if pas ~= CALL_OK then return nil end
        if not finite(palpha) then return nil end
        cumulative = cumulative * palpha
        current = parent
        depth = depth + 1
    end
    if not finite(cumulative) then return nil end
    if cumulative <= 0 then return 0 end
    return cumulative
end

local function _bounds_in_common(panel, common_parent, cache)
    if not panel_alive(panel) or not panel_alive(common_parent) then return nil end
    if panel == common_parent then
        local ws, w = _pass_read(cache, panel, "w")
        local hs, h = _pass_read(cache, panel, "h")
        if ws ~= CALL_OK or hs ~= CALL_OK then return nil end
        if not finite(w) or not finite(h) then return nil end
        return { x = 0, y = 0, w = w, h = h }
    end
    local depth = 0
    local current = panel
    local ox, oy = 0, 0
    while depth < NATIVE_DEPTH do
        local xs, x = _pass_read(cache, current, "x")
        local ys, y = _pass_read(cache, current, "y")
        if xs ~= CALL_OK or ys ~= CALL_OK then return nil end
        if not finite(x) or not finite(y) then return nil end
        ox = ox + x
        oy = oy + y
        local ps, parent = _pass_read(cache, current, "parent")
        if ps ~= CALL_OK then return nil end
        if not parent then return nil end
        if not panel_alive(parent) then return nil end
        if parent == common_parent then
            local ws, w = _pass_read(cache, panel, "w")
            local hs, h = _pass_read(cache, panel, "h")
            if ws ~= CALL_OK or hs ~= CALL_OK then return nil end
            if not finite(w) or not finite(h) then return nil end
            return { x = ox, y = oy, w = w, h = h }
        end
        current = parent
        depth = depth + 1
    end
    return nil
end

local function _aabb_overlap(a, b)
    return a.x < b.x + b.w and a.x + a.w > b.x
       and a.y < b.y + b.h and a.y + a.h > b.y
end

local function _player_visible_union(P, cache)
    if not P then return nil end
    local common_parent = kyohud.hud.runtime._parent_panel
    if not common_parent or not panel_alive(common_parent) then return nil end
    local union = nil
    local unknown = false
    local function try_add(prim, text_only)
        if not prim or not panel_alive(prim) then return end
        local ev = _effective_visible(prim, cache)
        if ev == false then return end
        if ev ~= true then unknown = true; return end
        local ea = _effective_alpha(prim, cache)
        if ea == nil then unknown = true; return end
        if ea <= 0 then return end
        if text_only then
            local st, text = _pass_read(cache, prim, "text")
            if st ~= CALL_OK or type(text) ~= "string" then unknown = true; return end
            if text == "" then return end
        end
        local b = _bounds_in_common(prim, common_parent, cache)
        if not b then unknown = true; return end
        if union == nil then
            union = { x = b.x, y = b.y, w = b.w, h = b.h }
        else
            local x1 = math.min(union.x, b.x)
            local y1 = math.min(union.y, b.y)
            local x2 = math.max(union.x + union.w, b.x + b.w)
            local y2 = math.max(union.y + union.h, b.y + b.h)
            union = { x = x1, y = y1, w = x2 - x1, h = y2 - y1 }
        end
    end
    local gauge = P._gauge
    if gauge then
        try_add(gauge.root)
    end
    for _, fname in ipairs({"_downs_bg", "_downs_text", "_downs_icon", "_h5_id_label", "_condition_text"}) do
        try_add(P[fname], fname == "_condition_text" or fname == "_h5_id_label")
    end
    if unknown then return nil end
    return union
end

local H5_CHILD_INDEX_MAX = 128

local function h5_child_index_reset()
    RT._h5_child_index = nil
end

local function h5_child_index_current()
    local index = RT._h5_child_index
    if index and index.generation ~= RT._generation then
        RT._h5_child_index = nil
        index = nil
    end
    return index
end

-- Bind only (parent, name) -> child lookups, never native values. A binding is
-- reused only while the child is alive and its immediate parent is still the
-- requested panel; any other outcome falls back to the existing fresh lookup.
local function h5_child_index_get(parent, name)
    if parent == nil or name == nil then return nil end
    local index = h5_child_index_current()
    if not index then return nil end
    local by_name = index.parents[parent]
    if not by_name then return nil end
    local child = by_name[name]
    if not child then return nil end
    if not panel_alive(child) then return nil end
    local status, immediate = safe_call(child, "parent")
    if status ~= CALL_OK or immediate ~= parent then return nil end
    return child
end

local function h5_child_index_set(parent, name, child)
    if parent == nil or name == nil then return end
    local index = h5_child_index_current()
    if child == nil then
        if not index then return end
        local by_name = index.parents[parent]
        if not by_name then return end
        if by_name[name] ~= nil then
            by_name[name] = nil
            index.count = index.count - 1
            if index.count <= 0 then h5_child_index_reset() end
        end
        return
    end
    if not index then
        index = {generation = RT._generation, parents = {}, count = 0}
        RT._h5_child_index = index
    end
    local by_name = index.parents[parent]
    if not by_name then
        by_name = {}
        index.parents[parent] = by_name
    end
    if by_name[name] == nil then
        if index.count >= H5_CHILD_INDEX_MAX then
            h5_child_index_reset()
            index = {generation = RT._generation, parents = {}, count = 0}
            RT._h5_child_index = index
            by_name = {}
            index.parents[parent] = by_name
        end
        index.count = index.count + 1
    end
    by_name[name] = child
end

function RT:_apply_native_priority(t)
    local mgr = self._manager
    if not mgr then return end
    local common_parent = self._parent_panel
    if not common_parent or not panel_alive(common_parent) then return end
    local crew = kyohud.hud.crew
    local player = kyohud.hud.player
    local weapons = kyohud.hud.weapons
    local equipment = kyohud.hud.equipment
    local crew_root = crew and crew._root
    local player_root = player and player._root
    local weapons_root = weapons and weapons._root
    local equipment_root = equipment and equipment._root
    local any_crew = crew_root and panel_alive(crew_root)
    local any_local = (player_root and panel_alive(player_root))
        or (weapons_root and panel_alive(weapons_root))
        or (equipment_root and panel_alive(equipment_root))
    if not any_crew and not any_local then return end
    local reads = {}
    local S = {
        any_crew = any_crew,
        any_local = any_local,
        crew_root = crew_root,
        player_root = player_root,
        weapons_root = weapons_root,
        equipment_root = equipment_root,
        hide_crew = false,
        hide_local = false,
    }
    local function known_child(parent, name, fresh)
        if not parent or not panel_alive(parent) then return nil end
        if not fresh then
            local cached = h5_child_index_get(parent, name)
            if cached then return cached end
        end
        local st, child = safe_call(parent, "child", name)
        if st == CALL_OK then
            if child and panel_alive(child) then
                if not fresh then h5_child_index_set(parent, name, child) end
                return child
            end
            if not fresh then h5_child_index_set(parent, name, nil) end
            return nil
        end
        if not fresh then h5_child_index_set(parent, name, nil) end
        S.hide_crew = true
        S.hide_local = true
        -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE.
        if not S._diag_crew_leaf and not S._diag_crew_parent and not S._diag_crew_name then
            S._diag_crew_parent, S._diag_crew_name = parent, name
        end
        if not S._diag_local_leaf and not S._diag_local_parent and not S._diag_local_name then
            S._diag_local_parent, S._diag_local_name = parent, name
        end
        return nil
    end
    local function check_leaf(leaf_panel)
        if not leaf_panel or not panel_alive(leaf_panel) then return end
        if S.hide_crew and S.hide_local then return end
        local ev = _effective_visible(leaf_panel, reads)
        if ev == false then return end
        local ea = _effective_alpha(leaf_panel, reads)
        if ea == 0 then return end
        if ev == nil or ea == nil then
            S.hide_crew = true
            S.hide_local = true
            -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE.
            if not S._diag_crew_leaf and not S._diag_crew_parent and not S._diag_crew_name then
                S._diag_crew_leaf, S._diag_crew_vis, S._diag_crew_alpha = leaf_panel, ev, ea
            end
            if not S._diag_local_leaf and not S._diag_local_parent and not S._diag_local_name then
                S._diag_local_leaf, S._diag_local_vis, S._diag_local_alpha = leaf_panel, ev, ea
            end
            return
        end
        local nb = _bounds_in_common(leaf_panel, common_parent, reads)
        if not nb then
            S.hide_crew = true
            S.hide_local = true
            -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE.
            if not S._diag_crew_leaf and not S._diag_crew_parent and not S._diag_crew_name then
                S._diag_crew_leaf, S._diag_crew_vis, S._diag_crew_alpha = leaf_panel, ev, ea
            end
            if not S._diag_local_leaf and not S._diag_local_parent and not S._diag_local_name then
                S._diag_local_leaf, S._diag_local_vis, S._diag_local_alpha = leaf_panel, ev, ea
            end
            return
        end
        if S.any_crew and not S.hide_crew then
            if not S._cb then
                S._cb = _bounds_in_common(crew_root, common_parent, reads)
            end
            if not S._cb then
                S.hide_crew = true
                -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE.
                if not S._diag_crew_leaf and not S._diag_crew_parent and not S._diag_crew_name then
                    S._diag_crew_leaf, S._diag_crew_vis, S._diag_crew_alpha = leaf_panel, ev, ea
                end
            elseif _aabb_overlap(nb, S._cb) then
                S.hide_crew = true
                -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE.
                if not S._diag_crew_leaf and not S._diag_crew_parent and not S._diag_crew_name then
                    S._diag_crew_leaf, S._diag_crew_vis, S._diag_crew_alpha = leaf_panel, ev, ea
                end
            end
        end
        if S.any_local and not S.hide_local then
            if player_root and panel_alive(player_root) then
                if not S._pb then
                    S._pb = _player_visible_union(player, reads)
                end
                if not S._pb or _aabb_overlap(nb, S._pb) then
                    S.hide_local = true
                    -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE.
                    if not S._diag_local_leaf and not S._diag_local_parent and not S._diag_local_name then
                        S._diag_local_leaf, S._diag_local_vis, S._diag_local_alpha = leaf_panel, ev, ea
                    end
                end
            end
            if not S.hide_local and weapons_root and panel_alive(weapons_root) then
                if not S._wb then
                    S._wb = _bounds_in_common(weapons_root, common_parent, reads)
                end
                if not S._wb or _aabb_overlap(nb, S._wb) then
                    S.hide_local = true
                    -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE.
                    if not S._diag_local_leaf and not S._diag_local_parent and not S._diag_local_name then
                        S._diag_local_leaf, S._diag_local_vis, S._diag_local_alpha = leaf_panel, ev, ea
                    end
                end
            end
            if not S.hide_local and equipment_root and panel_alive(equipment_root) then
                if not S._eb then
                    S._eb = _bounds_in_common(equipment_root, common_parent, reads)
                end
                if not S._eb or _aabb_overlap(nb, S._eb) then
                    S.hide_local = true
                    -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE.
                    if not S._diag_local_leaf and not S._diag_local_parent and not S._diag_local_name then
                        S._diag_local_leaf, S._diag_local_vis, S._diag_local_alpha = leaf_panel, ev, ea
                    end
                end
            end
        end
    end
    local function inspect_teammate_entry(entry)
        if type(entry) ~= "table" then return end
        local entry_panel = entry._panel
        if entry_panel and panel_alive(entry_panel) then
            local pp = known_child(entry_panel, "player")
            if pp and panel_alive(pp) then
                local carry = known_child(pp, "carry_panel")
                if carry and panel_alive(carry) then check_leaf(carry) end
                local interact = known_child(pp, "interact_panel")
                if interact and panel_alive(interact) then check_leaf(interact) end
                local radial = known_child(pp, "radial_health_panel")
                if radial and panel_alive(radial) then
                    local rc = known_child(radial, "radial_custom")
                    if rc and panel_alive(rc) then check_leaf(rc) end
                    local ra = known_child(radial, "radial_ability")
                    if ra and panel_alive(ra) then check_leaf(ra) end
                    local rr = known_child(radial, "radial_rip")
                    if rr and panel_alive(rr) then check_leaf(rr) end
                    local rrb = known_child(radial, "radial_rip_bg")
                    if rrb and panel_alive(rrb) then check_leaf(rrb) end
                    local ras = known_child(radial, "radial_absorb_shield_active")
                    if ras and panel_alive(ras) then check_leaf(ras) end
                    local rah = known_child(radial, "radial_absorb_health_active")
                    if rah and panel_alive(rah) then check_leaf(rah) end
                    local rim = known_child(radial, "radial_info_meter")
                    if rim and panel_alive(rim) then check_leaf(rim) end
                    local rimbg = known_child(radial, "radial_info_meter_bg")
                    if rimbg and panel_alive(rimbg) then check_leaf(rimbg) end
                    local rdd = known_child(radial, "radial_delayed_damage")
                    if rdd and panel_alive(rdd) then
                        local rdda = known_child(rdd, "radial_delayed_damage_armor")
                        if rdda and panel_alive(rdda) then check_leaf(rdda) end
                        local rddh = known_child(rdd, "radial_delayed_damage_health")
                        if rddh and panel_alive(rddh) then check_leaf(rddh) end
                    end
                    local copr = known_child(radial, "copr_overlay_panel")
                    if copr and panel_alive(copr) then
                        -- copr_overlay_panel is created visible while empty and the
                        -- native creates/destroys its numeric "0" child: never serve
                        -- this population from the binding index, re-consult the parent.
                        local c0 = known_child(copr, "0", true)
                        if c0 and panel_alive(c0) then check_leaf(copr) end
                    end
                end
            end
            local ct = known_child(entry_panel, "condition_timer")
            if ct and panel_alive(ct) then check_leaf(ct) end
        end
        local special_equip = entry._special_equipment
        if type(special_equip) == "table" then
            for j = 1, SPECIAL_EQUIP_MAX do
                local se = special_equip[j]
                if se == nil then break end
                check_leaf(se)
            end
            if special_equip[SPECIAL_EQUIP_MAX + 1] ~= nil then
                S.hide_crew = true
                S.hide_local = true
                -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE.
                if not S._diag_crew_leaf and not S._diag_crew_parent and not S._diag_crew_name then
                    S._diag_crew_name = "special_equip"
                end
                if not S._diag_local_leaf and not S._diag_local_parent and not S._diag_local_name then
                    S._diag_local_name = "special_equip"
                end
            end
        end
    end
    local teammate_panels = mgr._teammate_panels
    if type(teammate_panels) == "table" then
        for i = 1, 4 do
            inspect_teammate_entry(teammate_panels[i])
        end
    end
    local hud_temp = mgr._hud_temp
    if type(hud_temp) == "table" then
        local temp_panel = hud_temp._temp_panel
        if temp_panel and panel_alive(temp_panel) then
            local temp_names = { "bag_panel", "throw_instruction" }
            for _, cn in ipairs(temp_names) do
                local child = known_child(temp_panel, cn)
                if child and panel_alive(child) then
                    check_leaf(child)
                end
            end
        end
    end
    local hud_interaction = mgr._hud_interaction
    if type(hud_interaction) == "table" then
        local ip = hud_interaction._hud_panel
        if ip and panel_alive(ip) then
            local inames = { hud_interaction._child_name_text, hud_interaction._child_ivalid_name_text }
            for _, cn in ipairs(inames) do
                if type(cn) == "string" then
                    local child = known_child(ip, cn)
                    if child and panel_alive(child) then
                        check_leaf(child)
                    end
                end
            end
        end
    end
    if S.hide_crew and crew_root and panel_alive(crew_root) then
        safe_call(crew_root, "set_visible", false)
    end
    if S.hide_local then
        if player_root and panel_alive(player_root) then
            safe_call(player_root, "set_visible", false)
        end
        if weapons_root and panel_alive(weapons_root) then
            safe_call(weapons_root, "set_visible", false)
        end
        if equipment_root and panel_alive(equipment_root) then
            safe_call(equipment_root, "set_visible", false)
        end
        if self._local_bg_panel and panel_alive(self._local_bg_panel) then
            safe_call(self._local_bg_panel, "set_visible", false)
        end
    end

    -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE: priority hide transitions and
    -- a 5.0 s persistent reading while either hide flag remains true.
    local diag_prev = RT._h4_diag_state
    local diag_changed = false
    if diag_prev == nil then
        diag_prev = {crew = S.hide_crew, local_flag = S.hide_local}
        RT._h4_diag_state = diag_prev
    elseif diag_prev.crew ~= S.hide_crew or diag_prev.local_flag ~= S.hide_local then
        diag_prev.crew = S.hide_crew
        diag_prev.local_flag = S.hide_local
        diag_changed = true
    end
    local diag_time = diag_now(t)
    local diag_persist = false
    if not diag_changed and (S.hide_crew or S.hide_local) and diag_time ~= nil
        and RT._h4_diag_last_time ~= nil and diag_time >= RT._h4_diag_last_time
        and (diag_time - RT._h4_diag_last_time) >= DIAG_PERSIST_INTERVAL then
        diag_persist = true
    end
    if diag_changed or diag_persist then
        local reason_crew = diag_reason(S._diag_crew_leaf, S._diag_crew_parent, S._diag_crew_name)
        local reason_local = diag_reason(S._diag_local_leaf, S._diag_local_parent, S._diag_local_name)
        local line = string.format("%screw=%s local=%s reason_crew=%s reason_local=%s vis_crew=%s alpha_crew=%s vis_local=%s alpha_local=%s",
            diag_persist and "PERSIST " or "",
            tostring(S.hide_crew == true), tostring(S.hide_local == true),
            reason_crew, reason_local,
            diag_value(S._diag_crew_vis), diag_value(S._diag_crew_alpha),
            diag_value(S._diag_local_vis), diag_value(S._diag_local_alpha))
        if diag_emit(line) and diag_time ~= nil then
            RT._h4_diag_last_time = diag_time
        end
    end
end

local H5_PLAYER_ID_LEAVES = {"name", "name_bg", "callsign", "callsign_bg"}
local H5_RADIAL_LEAVES = {"radial_bg", "radial_health", "radial_shield"}
local H5_REVIVE_LEAVES = {"revive_bg", "revive_amount", "revive_arrow"}
local H5_WEAPON_BG_LEAVES = {"bg", "ammo_clip", "ammo_total"}
local H5_WEAPON_SEL_BITMAP = "weapon_selection"
local H5_EQUIP_DEPLOY_LEAVES = {"bg", "equipment", "amount"}
local H5_EQUIP_TIES_LEAVES = {"bg", "cable_ties", "amount"}
local H5_EQUIP_GREN_LEAVES = {"bg", "grenades_icon", "amount"}
local MAX_H5_SLOTS = 4
local H5_LOCAL_ID_NAME = "kyohud_local_id_text"
local H5_LOCAL_ID_FONT = "fonts/font_medium_mf"


local function h5_child(panel, name)
    if not panel or not panel_alive(panel) then return nil end
    local cached = h5_child_index_get(panel, name)
    if cached then return cached end
    local ok, child = pcall(function() return panel:child(name) end)
    if ok and child and panel_alive(child) then
        h5_child_index_set(panel, name, child)
        return child
    end
    h5_child_index_set(panel, name, nil)
    return nil
end

local function h5_player_slot()
    if type(HUDManager) == "table" and type(HUDManager.PLAYER_PANEL) == "number" then
        return HUDManager.PLAYER_PANEL
    end
    return 4
end

local function h5_read_native_name_text(entry_panel)
    if not entry_panel or not panel_alive(entry_panel) then return nil end
    local name_leaf = h5_child(entry_panel, "name")
    if not name_leaf then return nil end
    local ok, text = pcall(function() return name_leaf:text() end)
    if ok and type(text) == "string" and #text > 0 then return text end
    return nil
end

local function h5_read_native_name_color(entry_panel)
    if not entry_panel or not panel_alive(entry_panel) then return nil end
    local name_leaf = h5_child(entry_panel, "name")
    if not name_leaf then return nil end
    local ok, r, g, b = pcall(function()
        local c = name_leaf:color()
        return c.r, c.g, c.b
    end)
    if not ok then return nil end
    r, g, b = tonumber(r), tonumber(g), tonumber(b)
    if not (r and g and b and finite(r) and finite(g) and finite(b)) then return nil end
    return r, g, b
end

local function h5_set_if_changed(label, getter, setter, desired)
    local status, actual = safe_call(label, getter)
    if status ~= CALL_OK or actual ~= desired then
        safe_call(label, setter, desired)
        return true
    end
    return false
end

local function h5_color_matches(label, r, g, b)
    local c = label:color()
    return c and finite(c.r) and finite(c.g) and finite(c.b) and finite(c.a)
        and math.abs(c.r - r) < 0.005 and math.abs(c.g - g) < 0.005
        and math.abs(c.b - b) < 0.005 and math.abs(c.a - 1) < 0.01
end

local function h5_shape_matches(label, x, y, w, h)
    local ax, ay, aw, ah = label:x(), label:y(), label:w(), label:h()
    local matches = finite(ax) and finite(ay) and finite(aw) and finite(ah)
        and math.abs(ax - x) <= 0.01 and math.abs(ay - y) <= 0.01
        and math.abs(aw - w) <= 0.01 and math.abs(ah - h) <= 0.01
    return matches, ax, ay, aw, ah
end

local function h5_text_ink(label)
    if not label then return CALL_ERROR end
    local ok, tw, th = pcall(function()
        local _, _, w, h = label:text_rect()
        return w, h
    end)
    if not ok then return CALL_ERROR end
    if not finite(tw) or not finite(th) or tw < 0 or th < 0 then return CALL_ERROR end
    return CALL_OK, tw, th
end

local function h5_ensure_local_identity(P, entry_panel)
    if not P or not P._root or not panel_alive(P._root) then return nil, nil end
    if not entry_panel or not panel_alive(entry_panel) then return nil, nil end
    local source_text = h5_read_native_name_text(entry_panel)
    local r, g, b = h5_read_native_name_color(entry_panel)
    if not source_text then return nil, nil end

    local rws, root_w = safe_call(P._root, "w")
    if rws ~= CALL_OK or not finite(root_w) or root_w <= 0 then return nil, nil end
    local e = root_w / 380
    local target_x = 14 * e
    local target_y = 170 * e
    local target_w = 352 * e
    local target_h = 20 * e
    local font_size_initial = 16 * e
    local font_size_min = 10 * e

    local label = P._h5_id_label
    local needs_repair = false
    if not label or not panel_alive(label) then
        needs_repair = true
    else
        local ps, parent = safe_call(label, "parent")
        if ps ~= CALL_OK or parent ~= P._root then needs_repair = true end
    end

    local lookup_ok, existing = pcall(function() return P._root:child(H5_LOCAL_ID_NAME) end)
    if not lookup_ok or (existing and not panel_alive(existing)) then return nil, nil end
    if existing and existing ~= label then
        return nil, nil
    end

    if needs_repair then
        if existing then
            safe_call(P._root, "remove", existing)
        end
        local cs, new_label = safe_call(P._root, "text", {
            name = H5_LOCAL_ID_NAME,
            text = source_text,
            font = H5_LOCAL_ID_FONT,
            font_size = font_size_initial,
            x = target_x, y = target_y, w = target_w, h = target_h,
            layer = 10,
        })
        if cs ~= CALL_OK or not new_label then
            P._h5_id_label = nil
            return nil, nil
        end
        label = new_label
        P._h5_id_label = label
    end

    -- Same-call evidence boundary: the geometry and ink measured below may be
    -- reused by the immediately adjacent h5_verify_local_identity only when
    -- this pass attempted no write at all (no creation, repair, setter, refit,
    -- shrink or truncation) and the warmed fit already matches. Evidence is
    -- returned as a third value only, never stored on P/R, and never survives
    -- this synchronous call; any write attempt forces the fresh full verifier.
    local write_attempted = needs_repair
    write_attempted = h5_set_if_changed(label, "visible", "set_visible", true) or write_attempted
    write_attempted = h5_set_if_changed(label, "alpha", "set_alpha", 1) or write_attempted

    local fit = P._h5_id_fit
    local fit_matches = fit and fit.label == label and fit.source_text == source_text
        and fit.root_w == root_w
    local display_text = fit_matches and fit.text or source_text
    local desired_fs = fit_matches and fit.font_size or font_size_initial
    local ts, cur_text = safe_call(label, "text")
    if ts ~= CALL_OK or cur_text ~= display_text then
        safe_call(label, "set_text", display_text)
        write_attempted = true
    end

    if r then
        local ok, matches = pcall(h5_color_matches, label, r, g, b)
        if not ok or not matches then
            safe_call(label, "set_color", Color(1, r, g, b))
            write_attempted = true
        end
    end

    -- Font is fixed by our constructor. Live font getter/setter bindings
    -- previously caused native access violations; pcall cannot protect those.
    local fss, cur_fs = safe_call(label, "font_size")
    if fss ~= CALL_OK or not finite(cur_fs) or math.abs(cur_fs - desired_fs) > 0.01 then
        safe_call(label, "set_font_size", desired_fs)
        write_attempted = true
    end

    local shape_ok, shape_matches, ax, ay, aw, ah = pcall(h5_shape_matches, label, target_x, target_y, target_w, target_h)
    if not shape_ok or not shape_matches then
        safe_call(label, "set_shape", target_x, target_y, target_w, target_h)
        write_attempted = true
    end

    local trs, tw, th = h5_text_ink(label)
    if fit_matches and trs == CALL_OK and tw <= target_w and th <= target_h then
        local evidence = nil
        if not write_attempted then
            evidence = {label = label, root = P._root, root_w = root_w,
                x = ax, y = ay, w = aw, h = ah, ink_w = tw, ink_h = th}
        end
        return label, display_text, evidence
    end
    if fit_matches then
        display_text = source_text
        safe_call(label, "set_text", source_text)
        safe_call(label, "set_font_size", font_size_initial)
        trs, tw, th = h5_text_ink(label)
    end
    local fs = font_size_initial
    if trs == CALL_OK then
        local shrink_steps = 0
        while (th > target_h or tw > target_w) and fs > font_size_min and shrink_steps < 6 do
            fs = math.max(fs - e, font_size_min)
            shrink_steps = shrink_steps + 1
            safe_call(label, "set_font_size", fs)
            trs, tw, th = h5_text_ink(label)
            if trs ~= CALL_OK then break end
        end
        if trs == CALL_OK and tw > target_w then
            local prefix = source_text
            local iterations = 0
            while #prefix > 0 and iterations < 512 do
                iterations = iterations + 1
                local n = #prefix
                while n > 1 and prefix:byte(n) >= 128 and prefix:byte(n) < 192 do
                    n = n - 1
                end
                prefix = prefix:sub(1, n - 1)
                local candidate = prefix .. "..."
                safe_call(label, "set_text", candidate)
                display_text = candidate
                trs, tw, th = h5_text_ink(label)
                if trs ~= CALL_OK then break end
                if tw <= target_w then break end
            end
            safe_call(label, "set_text", display_text)
        end
    end

    if trs == CALL_OK and tw <= target_w and th <= target_h then
        P._h5_id_fit = {label = label, source_text = source_text, root_w = root_w,
            text = display_text, font_size = fs}
    else
        P._h5_id_fit = nil
    end
    return label, display_text
end

local function h5_verify_local_identity(P, label, expected_text, evidence)
    if not label or not panel_alive(label) then return false end
    if not P or not P._root or not panel_alive(P._root) then return false end
    local ps, parent = safe_call(label, "parent")
    if ps ~= CALL_OK or parent ~= P._root then return false end
    local vs, vis = safe_call(label, "visible")
    if vs ~= CALL_OK or vis ~= true then return false end
    local als, alpha = safe_call(label, "alpha")
    if als ~= CALL_OK or not finite(alpha) or math.abs(alpha - 1) > 0.01 then return false end
    local fss, font_size = safe_call(label, "font_size")
    if fss ~= CALL_OK or not finite(font_size) or font_size <= 0 then return false end
    if expected_text then
        local ts, text = safe_call(label, "text")
        if ts ~= CALL_OK or text ~= expected_text then return false end
    end
    local rws, root_w = safe_call(P._root, "w")
    if rws ~= CALL_OK or not finite(root_w) or root_w <= 0 then return false end
    local e = root_w / 380
    -- Same-call evidence reuse: exact measured geometry and ink handed over by
    -- the adjacent write-free h5_ensure_local_identity pass, guarded by label,
    -- root and root-width identity. Anything else falls back to fresh reads.
    local reuse = type(evidence) == "table" and evidence.label == label
        and evidence.root == P._root and evidence.root_w == root_w
        and finite(evidence.x) and finite(evidence.y)
        and finite(evidence.w) and finite(evidence.h)
        and finite(evidence.ink_w) and finite(evidence.ink_h)
    local lx, ly, lw, lh
    if reuse then
        lx, ly, lw, lh = evidence.x, evidence.y, evidence.w, evidence.h
    else
        local ok_shape, sx, sy, sw, sh = pcall(function() return label:x(), label:y(), label:w(), label:h() end)
        if not ok_shape then return false end
        lx, ly, lw, lh = sx, sy, sw, sh
    end
    if not (finite(lx) and finite(ly) and finite(lw) and finite(lh)) then return false end
    local exp_x, exp_y, exp_w, exp_h = 14 * e, 170 * e, 352 * e, 20 * e
    if math.abs(lx - exp_x) > 1 or math.abs(ly - exp_y) > 1 then return false end
    if math.abs(lw - exp_w) > 1 or math.abs(lh - exp_h) > 1 then return false end
    local fs_lo, fs_hi = 10 * e, 16 * e
    if font_size < fs_lo - 0.01 or font_size > fs_hi + 0.01 then return false end
    local trs, tw, th
    if reuse then
        trs, tw, th = CALL_OK, evidence.ink_w, evidence.ink_h
    else
        trs, tw, th = h5_text_ink(label)
    end
    if trs ~= CALL_OK then return false end
    if not finite(tw) or not finite(th) then return false end
    if tw > lw or th > lh then return false end
    return true
end

local function h5_player_downs_known(P)
    if not P then return false end
    local exp = P._exp_downs_text
    if not finite(tonumber(exp)) then return false end
    local dt = P._downs_text
    if not dt then return false end
    local vis_s, vis = safe_call(dt, "visible")
    return vis_s == CALL_OK and vis == true
end

local function h5_collect_player_targets(entry_panel, P)
    local targets = {}
    if not entry_panel or not panel_alive(entry_panel) then return targets end
    local label, label_text, id_evidence = nil, nil, nil
    local identity_ok = false
    if P and P._root and panel_alive(P._root) then
        label, label_text, id_evidence = h5_ensure_local_identity(P, entry_panel)
        if label then
            identity_ok = h5_verify_local_identity(P, label, label_text, id_evidence)
        end
    end
    if P then P._h5_identity_verified = identity_ok end
    if identity_ok then
        for _, name in ipairs(H5_PLAYER_ID_LEAVES) do
            local leaf = h5_child(entry_panel, name)
            if leaf then targets[#targets + 1] = leaf end
        end
    end
    local player = h5_child(entry_panel, "player")
    if player then
        local radial = h5_child(player, "radial_health_panel")
        if radial then
            local ACT = kyohud.hud.actors
            local actor_snap = nil
            if ACT and type(ACT.get_actor) == "function" then
                local slot = h5_player_slot()
                if slot then
                    local snap_ok, snap = pcall(ACT.get_actor, ACT, slot)
                    if snap_ok and type(snap) == "table" then
                        actor_snap = snap
                    end
                end
            end
            local health_valid = actor_snap and actor_snap.health and actor_snap.health.valid == true
            local armor_valid = actor_snap and actor_snap.armor and actor_snap.armor.valid == true
            for _, name in ipairs(H5_RADIAL_LEAVES) do
                if name == "radial_health" and not health_valid then
                elseif name == "radial_shield" and not armor_valid then
                elseif name == "radial_bg" and not (health_valid and armor_valid) then
                else
                    local leaf = h5_child(radial, name)
                    if leaf then targets[#targets + 1] = leaf end
                end
            end
        end
        if P and P._root and panel_alive(P._root) and h5_player_downs_known(P) then
            local revive = h5_child(player, "revive_panel")
            if revive then
                for _, name in ipairs(H5_REVIVE_LEAVES) do
                    local leaf = h5_child(revive, name)
                    if leaf then targets[#targets + 1] = leaf end
                end
            end
        end
    end
    return targets, identity_ok
end

local function h5_collect_weapon_targets(entry_panel, W)
    local targets = {}
    if not entry_panel or not panel_alive(entry_panel) then return targets end
    local player = h5_child(entry_panel, "player")
    if not player then return targets end
    local weapons = h5_child(player, "weapons_panel")
    if not weapons then return targets end
    local snap = W and W._current_snapshot
    local snap_slots = snap and snap.slots
    local native_to_slot = {
        secondary_weapon_panel = 1,
        primary_weapon_panel = 2,
    }
    for slot_name, slot_idx in pairs(native_to_slot) do
        local slot_data = snap_slots and snap_slots[slot_idx]
        local data_ok = slot_data
            and slot_data.present == true
            and finite(slot_data.current_clip)
            and finite(slot_data.total_raw)
            and slot_data.coherent ~= false
        if data_ok then
            local slot_panel = h5_child(weapons, slot_name)
            if slot_panel then
                for _, name in ipairs(H5_WEAPON_BG_LEAVES) do
                    local leaf = h5_child(slot_panel, name)
                    if leaf then targets[#targets + 1] = leaf end
                end
                local sel_container = h5_child(slot_panel, H5_WEAPON_SEL_BITMAP)
                if sel_container and panel_alive(sel_container) then
                    local sel_bitmap = h5_child(sel_container, H5_WEAPON_SEL_BITMAP)
                    if sel_bitmap then targets[#targets + 1] = sel_bitmap end
                end
            end
        end
    end
    return targets
end

local function h5_collect_equipment_targets(entry_panel, E)
    local targets = {}
    if not entry_panel or not panel_alive(entry_panel) then return targets end
    local player = h5_child(entry_panel, "player")
    if not player then return targets end
    local snap = E and E._snapshot
    local snap_valid = snap and snap.source_known == true and not snap.unsupported
    local deploy = h5_child(player, "deployable_equipment_panel")
    if deploy then
        local deploy_ok = false
        if snap_valid and snap.selected_effective then
            local sel_entry = snap.deployables and snap.deployables[snap.selected_effective]
            if sel_entry then
                local quantities = sel_entry.quantities or {}
                local all_known_qty = #quantities > 0
                for _, q in ipairs(quantities) do
                    if q.known ~= true then all_known_qty = false; break end
                end
                if all_known_qty or (sel_entry.amount_text and sel_entry.amount_text ~= "") then
                    deploy_ok = true
                end
            end
        end
        if deploy_ok then
            for _, name in ipairs(H5_EQUIP_DEPLOY_LEAVES) do
                local leaf = h5_child(deploy, name)
                if leaf then targets[#targets + 1] = leaf end
            end
        end
    end
    local ties = h5_child(player, "cable_ties_panel")
    if ties then
        local ties_ok = snap_valid and snap.cables and snap.cables.known == true
        if ties_ok then
            for _, name in ipairs(H5_EQUIP_TIES_LEAVES) do
                local leaf = h5_child(ties, name)
                if leaf then targets[#targets + 1] = leaf end
            end
        end
    end
    local gren = h5_child(player, "grenades_panel")
    if gren then
        local gren_ok = false
        if snap_valid and snap.projectile then
            local proj = snap.projectile
            local kind_ok = proj.kind == "ability" or proj.kind == "throwable"
            local charges_ok = proj.charges and proj.charges.known == true
            if kind_ok and charges_ok then gren_ok = true end
        end
        if gren_ok then
            for _, name in ipairs(H5_EQUIP_GREN_LEAVES) do
                local leaf = h5_child(gren, name)
                if leaf then targets[#targets + 1] = leaf end
            end
        end
    end
    return targets
end

local H5_CREW_WEAPONS = {"secondary_weapon_panel", "primary_weapon_panel"}
local H5_CREW_CHANNELS = {
    {"revive_panel", "downs", H5_REVIVE_LEAVES},
    {"deployable_equipment_panel", "deployable", H5_EQUIP_DEPLOY_LEAVES},
    {"cable_ties_panel", "cables", H5_EQUIP_TIES_LEAVES},
    {"grenades_panel", "projectile", H5_EQUIP_GREN_LEAVES},
}

local function h5_collect_crew_targets(entry_panel, current, shown)
    local targets = {}
    local function append(parent, names)
        if not parent then return end
        for _, name in ipairs(names) do
            local leaf = h5_child(parent, name)
            if leaf then targets[#targets + 1] = leaf end
        end
    end
    if current.name and shown.name then append(entry_panel, H5_PLAYER_ID_LEAVES) end
    local player = h5_child(entry_panel, "player")
    if not player then return targets end
    local radial = h5_child(player, "radial_health_panel")
    local health = current.health and shown.health
    local armor = current.armor and shown.armor
    if radial then
        if health then
            local leaf = h5_child(radial, "radial_health")
            if leaf then targets[#targets + 1] = leaf end
        end
        if armor then
            local leaf = h5_child(radial, "radial_shield")
            if leaf then targets[#targets + 1] = leaf end
        end
        if health and (current.ai or armor) then
            local leaf = h5_child(radial, "radial_bg")
            if leaf then targets[#targets + 1] = leaf end
        end
    end
    if not current.ai then
        local weapons = h5_child(player, "weapons_panel")
        if weapons then
            for i = 1, 2 do
                local key = i == 1 and "ammo1" or "ammo2"
                if current[key] and shown[key] then
                    local weapon = h5_child(weapons, H5_CREW_WEAPONS[i])
                    append(weapon, H5_WEAPON_BG_LEAVES)
                    local selector = weapon and h5_child(weapon, H5_WEAPON_SEL_BITMAP)
                    local bitmap = selector and h5_child(selector, H5_WEAPON_SEL_BITMAP)
                    if bitmap then targets[#targets + 1] = bitmap end
                end
            end
        end
        for _, channel in ipairs(H5_CREW_CHANNELS) do
            if current[channel[2]] and shown[channel[2]] then
                append(h5_child(player, channel[1]), channel[3])
            end
        end
    end
    return targets
end

local function h5_same_targets(a, b)
    if a == b then return true end
    if not a or not b then return false end
    if #a ~= #b then return false end
    for i = 1, #a do
        if a[i] ~= b[i] then return false end
    end
    return true
end

local function h5_group_pending(nv, owner, generation)
    if not nv or not nv._entries then return false end
    for _, entry in pairs(nv._entries) do
        if type(entry) == "table" and entry.owner == owner and entry.generation == generation then
            return true
        end
    end
    return false
end

function RT:_h5_release_group(group_key)
    local state = self._h5_groups and self._h5_groups[group_key]
    if not state then return true end
    local nv = kyohud.hud.native_visibility
    if state.generation > 0 and nv and type(nv.release) == "function" then
        nv:release(state.owner, state.generation)
    end
    if h5_group_pending(nv, state.owner, state.generation) then
        state._release_pending = true
        return false
    end
    local added = state.added
    if added and nv and nv._whitelist then
        for leaf, previous in pairs(added) do
            if nv._whitelist[leaf] then
                nv._whitelist[leaf].alpha = previous.alpha
                if not next(nv._whitelist[leaf]) then
                    nv._whitelist[leaf] = nil
                end
            end
        end
    end
    self._h5_groups[group_key] = nil
    return true
end

function RT:_h5_acquire_group(group_key, targets, source_id)
    if not targets or #targets == 0 then return end
    local nv = kyohud.hud.native_visibility
    if not nv or type(nv.acquire) ~= "function" then return end
    local old = self._h5_groups and self._h5_groups[group_key]
    if old then
        local same_source = h5_same_targets(old.targets, targets)
            and old.entry_panel == source_id.entry_panel
            and old.manager == source_id.manager
            and old.root_gen == source_id.root_gen
        if same_source then
            if not old._release_pending then
                local ok = nv:acquire(old.owner, old.generation, old.requests)
                if not ok then
                    self:_h5_release_group(group_key)
                end
                return
            end
        end
        if old._release_pending then
            old._source_changed = true
            return
        end
        local released = self:_h5_release_group(group_key)
        if not released then
            old = self._h5_groups and self._h5_groups[group_key]
            if old then old._source_changed = true end
            return
        end
    end
    self._h5_groups = self._h5_groups or {}
    self._h5_generation = self._h5_generation + 1
    local new_gen = self._h5_generation
    local owner = self._h5_owner .. "_" .. group_key
    local requests = {}
    local added = {}
    for i, leaf in ipairs(targets) do
        if nv._whitelist then
            if not nv._whitelist[leaf] then nv._whitelist[leaf] = {} end
            if nv._whitelist[leaf].alpha ~= true then
                added[leaf] = {alpha = nv._whitelist[leaf].alpha}
                nv._whitelist[leaf].alpha = true
            end
        end
        requests[i] = {id = leaf, property = "alpha", value = 0}
    end
    local state = {
        owner = owner,
        generation = new_gen,
        targets = targets,
        entry_panel = source_id.entry_panel,
        manager = source_id.manager,
        root_gen = source_id.root_gen,
        added = added,
        requests = requests,
    }
    self._h5_groups[group_key] = state
    local ok = nv:acquire(owner, new_gen, requests)
    if ok then
        return
    end
    self:_h5_release_group(group_key)
end

function RT:_coordinate_h5_native_duplicates(crew_receipt)
    local mgr = self._manager
    if not mgr then return {} end
    -- TEMPORARY DIAGNOSTIC REMOVE BEFORE RELEASE: time only during an active
    -- capture; the accumulators are reused in place, never reallocated.
    local diag_perf = self._perf_diagnostic
    local phase = nil
    if diag_perf and diag_perf.started and not self._perf_done
        and self._perf_enabled ~= false then
        phase = self._h5_diag_phase
    end
    if self._disabled or self._freeflight then
        self:_release_all_h5()
        -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE.
        h5_diag_local("p_ok_false", false, false, 0, false)
        h5_diag_crew("c_ok", false, false, false, 0)
        return {}
    end
    local nv = kyohud.hud.native_visibility
    if not nv or type(nv.acquire) ~= "function" then
        -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE.
        h5_diag_local("p_ok_false", false, false, 0, false)
        h5_diag_crew("c_ok", false, false, false, 0)
        return {}
    end

    local P = kyohud.hud.player
    local W = kyohud.hud.weapons
    local E = kyohud.hud.equipment
    local C = kyohud.hud.crew
    local ACT = kyohud.hud.actors

    local p_enabled = kyohud.settings.enable_player == true
    local w_enabled = kyohud.settings.enable_weapons == true
    local e_enabled = kyohud.settings.enable_equipment == true
    local c_enabled = kyohud.settings.enable_crew == true

    local p_ok = p_enabled and P and P._mounted and P._manager == mgr
        and self._mounted and panel_alive(P._root)
    local w_ok = w_enabled and W and W._mounted and W._manager == mgr
        and self._mounted and panel_alive(W._root)
    local e_ok = e_enabled and E and E._mounted and E._manager == mgr
        and self._mounted and panel_alive(E._root)
    local c_ok = c_enabled and C and C._mounted and C._manager == mgr
        and self._mounted and panel_alive(C._root)

    -- Receipts belong only to this synchronous H5 -> backdrop pass. They are
    -- never retained across frames. Backdrop writes do not mutate P/W/E content.
    -- quality split approved 2026-11-10: a module that already ran in this same
    -- synchronous pass certifies with its own result. A throttled module gets a
    -- live light root read. H5 never adds a full verifier pcall.
    local certifications = {}
    if p_ok then
        local verify_start = h5_phase_begin(phase)
        local ok
        if P._update_ran_now == true then
            ok = P._verify_ok_now == true
        else
            ok = h5_light_root_ok(P)
        end
        h5_phase_end(phase, "verify_p", verify_start)
        certifications[P] = {root = P._root, manager = P._manager, verify = P.verify, ok = ok}
        if not ok then p_ok = false end
    end
    if w_ok then
        local verify_start = h5_phase_begin(phase)
        local ok
        if W._update_ran_now == true then
            ok = W._verify_ok_now == true
        else
            ok = h5_light_root_ok(W)
        end
        h5_phase_end(phase, "verify_w", verify_start)
        certifications[W] = {root = W._root, manager = W._manager, verify = W.verify, ok = ok}
        if not ok then w_ok = false end
    end
    if e_ok then
        local verify_start = h5_phase_begin(phase)
        local ok
        if E._update_ran_now == true then
            ok = E._verify_ok_now == true
        else
            ok = h5_light_root_ok(E)
        end
        h5_phase_end(phase, "verify_e", verify_start)
        certifications[E] = {root = E._root, manager = E._manager, verify = E.verify, ok = ok}
        if not ok then e_ok = false end
    end
    if c_ok then
        local receipt_valid = false
        if type(crew_receipt) == "table" and crew_receipt.ok == true
            and crew_receipt.module == C and crew_receipt.root == C._root
            and crew_receipt.manager == C._manager
            and crew_receipt.verifier == C._verify_render then
            local rv_s, rv = safe_call(C._root, "visible")
            local ra_s, ra = safe_call(C._root, "alpha")
            if rv_s == CALL_OK and rv == true and ra_s == CALL_OK and ra == 1 then
                receipt_valid = true
            end
        end
        if not receipt_valid then
            local verify_start = h5_phase_begin(phase)
            local ok
            if C._update_ran_now == true then
                ok = C._verify_ok_now == true
            else
                ok = h5_light_crew_ok(C)
            end
            h5_phase_end(phase, "verify_c", verify_start)
            if not ok then c_ok = false end
        end
    end

    -- All four visibility queries precede target acquisition and any H5 writes.
    -- Share their common ancestors, never this cache with priority or acquisition.
    local vis_start = h5_phase_begin(phase)
    local visibility_reads = {}
    local p_vis = false
    if p_ok then
        p_vis = _effective_visible(P._root, visibility_reads) == true and (_effective_alpha(P._root, visibility_reads) or 0) > 0
    end
    local w_vis = false
    if w_ok then
        w_vis = _effective_visible(W._root, visibility_reads) == true and (_effective_alpha(W._root, visibility_reads) or 0) > 0
    end
    local e_vis = false
    if e_ok then
        e_vis = _effective_visible(E._root, visibility_reads) == true and (_effective_alpha(E._root, visibility_reads) or 0) > 0
    end
    local c_vis = false
    if c_ok then
        c_vis = _effective_visible(C._root, visibility_reads) == true and (_effective_alpha(C._root, visibility_reads) or 0) > 0
    end
    h5_phase_end(phase, "vis", vis_start)

    -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE.
    local local_p_state = p_ok and "released" or "p_ok_false"
    local local_p_targets = 0
    local local_p_verify = false
    local crew_reason = "c_ok"
    local crew_verify = false
    local crew_targets = 0
    if c_ok then
        if not c_vis then
            crew_reason = "c_vis"
        else
            crew_verify = C and C._render_verified == true
            crew_reason = crew_verify and "targets" or "verify"
        end
    end

    local teammate_panels = mgr._teammate_panels
    if type(teammate_panels) ~= "table" then
        self:_release_all_h5()
        -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE.
        h5_diag_local(local_p_state, p_ok, p_vis, local_p_targets, local_p_verify)
        h5_diag_crew(crew_reason, c_ok, crew_verify, c_vis, crew_targets)
        return certifications
    end

    local player_slot = h5_player_slot()
    local handled_keys = {}

    if p_ok or w_ok or e_ok then
        local entry = teammate_panels[player_slot]
        if type(entry) == "table" then
            local entry_panel = entry._panel
            if entry_panel and panel_alive(entry_panel) then
                local key = "local_p"
                if p_ok and p_vis then
                    local collect_start = h5_phase_begin(phase)
                    local p_targets, identity_ok = h5_collect_player_targets(entry_panel, P)
                    h5_phase_end(phase, "collect_p", collect_start)
                    local_p_targets = #p_targets
                    local_p_verify = identity_ok == true
                    local acq_start = h5_phase_begin(phase)
                    if #p_targets > 0 then
                        local_p_state = "acquired"
                        self:_h5_acquire_group(key .. "_p", p_targets, {
                            entry_panel = entry_panel,
                            manager = mgr,
                            root_gen = self._generation,
                        })
                    else
                        local_p_state = "no_targets"
                        self:_h5_release_group(key .. "_p")
                    end
                    h5_phase_end(phase, "acq_p", acq_start)
                else
                    local_p_state = p_ok and "released" or "p_ok_false"
                    local acq_start = h5_phase_begin(phase)
                    self:_h5_release_group(key .. "_p")
                    h5_phase_end(phase, "acq_p", acq_start)
                end
                handled_keys[key .. "_p"] = true
                if w_ok and w_vis then
                    local collect_start = h5_phase_begin(phase)
                    local w_targets = h5_collect_weapon_targets(entry_panel, W)
                    h5_phase_end(phase, "collect_w", collect_start)
                    local acq_start = h5_phase_begin(phase)
                    if #w_targets > 0 then
                        self:_h5_acquire_group(key .. "_w", w_targets, {
                            entry_panel = entry_panel,
                            manager = mgr,
                            root_gen = self._generation,
                        })
                    else
                        self:_h5_release_group(key .. "_w")
                    end
                    h5_phase_end(phase, "acq_w", acq_start)
                else
                    local acq_start = h5_phase_begin(phase)
                    self:_h5_release_group(key .. "_w")
                    h5_phase_end(phase, "acq_w", acq_start)
                end
                handled_keys[key .. "_w"] = true
                if e_ok and e_vis then
                    local collect_start = h5_phase_begin(phase)
                    local e_targets = h5_collect_equipment_targets(entry_panel, E)
                    h5_phase_end(phase, "collect_e", collect_start)
                    local acq_start = h5_phase_begin(phase)
                    if #e_targets > 0 then
                        self:_h5_acquire_group(key .. "_e", e_targets, {
                            entry_panel = entry_panel,
                            manager = mgr,
                            root_gen = self._generation,
                        })
                    else
                        self:_h5_release_group(key .. "_e")
                    end
                    h5_phase_end(phase, "acq_e", acq_start)
                else
                    local acq_start = h5_phase_begin(phase)
                    self:_h5_release_group(key .. "_e")
                    h5_phase_end(phase, "acq_e", acq_start)
                end
                handled_keys[key .. "_e"] = true
            end
        end
    else
        local acq_start = h5_phase_begin(phase)
        self:_h5_release_group("local_p_p")
        h5_phase_end(phase, "acq_p", acq_start)
        acq_start = h5_phase_begin(phase)
        self:_h5_release_group("local_p_w")
        h5_phase_end(phase, "acq_w", acq_start)
        acq_start = h5_phase_begin(phase)
        self:_h5_release_group("local_p_e")
        h5_phase_end(phase, "acq_e", acq_start)
    end

    if c_ok and c_vis and ACT and type(ACT.write_crew_native_coverage) == "function" then
        self._h5_crew_coverage = self._h5_crew_coverage or {}
        local snap_ok, rows = pcall(ACT.write_crew_native_coverage, ACT, self._h5_crew_coverage)
        if snap_ok and type(rows) == "table" then
            local seen_slots = {}
            for pos = 1, 3 do
                local current = rows[pos]
                local shown = C._native_coverage and C._native_coverage[pos]
                if current and current.valid and shown and shown.valid
                    and current.occupant_token == shown.occupant_token and current.slot == shown.slot then
                    local slot = current.slot
                    if finite(slot) and slot == math.floor(slot) and slot >= 1 and slot <= 4
                        and slot ~= player_slot and not seen_slots[slot] then
                        seen_slots[slot] = true
                        local has_pos = C._expected_positions and C._expected_positions[pos] == true
                        local card = has_pos and C._cards and C._cards[pos]
                        if card and card.root and panel_alive(card.root) then
                            local status, visible = safe_call(card.root, "visible")
                            if status == CALL_OK and visible == true and C._render_verified == true then
                                local native = teammate_panels[slot]
                                local owner_matches = type(native) == "table"
                                    and ((current.ai and native._ai == true)
                                        or (not current.ai and native._ai ~= true and native._peer_id == current.peer_id))
                                local entry_panel = owner_matches and native._panel
                                if entry_panel and panel_alive(entry_panel) then
                                    local key = "crew_" .. pos
                                    handled_keys[key] = true
                                    local collect_start = h5_phase_begin(phase)
                                    local targets = h5_collect_crew_targets(entry_panel, current, shown)
                                    h5_phase_end(phase, "collect_c", collect_start)
                                    local acq_start = h5_phase_begin(phase)
                                    if #targets > 0 then
                                        crew_targets = crew_targets + #targets
                                        self:_h5_acquire_group(key, targets, {
                                            entry_panel = entry_panel, manager = mgr, root_gen = self._generation,
                                        })
                                    else
                                        self:_h5_release_group(key)
                                    end
                                    h5_phase_end(phase, "acq_c", acq_start)
                                end
                            end
                        end
                    end
                end
            end
        end
    end

    if self._h5_groups then
        for key, state in pairs(self._h5_groups) do
            if not handled_keys[key] then
                local acq_start = h5_phase_begin(phase)
                self:_h5_release_group(key)
                h5_phase_end(phase, h5_phase_acq_key(key), acq_start)
            end
        end
    end
    -- TEMPORARY DIAGNOSTIC, REMOVE BEFORE RELEASE: H5 group transitions only.
    local local_group = self._h5_groups and self._h5_groups["local_p_p"]
    if local_group and not local_group._release_pending then
        local_p_state = "acquired"
    elseif local_p_state == "acquired" then
        local_p_state = "released"
    end
    h5_diag_local(local_p_state, p_ok, p_vis, local_p_targets, local_p_verify)
    h5_diag_crew(crew_reason, c_ok, crew_verify, c_vis, crew_targets)
    self:_sync_h5_id_label_visibility()
    return certifications
end

function RT:_sync_h5_id_label_visibility()
    local P = kyohud.hud.player
    if not P then return end
    local label = P._h5_id_label
    if not label or not panel_alive(label) then return end
    local identity_verified = P._h5_identity_verified == true
    local eligible_local_player_group = false
    if self._h5_groups then
        local state = self._h5_groups["local_p_p"]
        if state and not state._release_pending then
            eligible_local_player_group = true
        end
    end
    local should_hide = not identity_verified
        or not eligible_local_player_group
        or self._disabled
        or self._freeflight
        or kyohud.settings.enable_hud_foundation ~= true
    h5_set_if_changed(label, "visible", "set_visible", not should_hide)
end

function RT:_retry_pending_h5_releases()
    if not self._h5_groups then return end
    local any_remaining = false
    for key, state in pairs(self._h5_groups) do
        if state._release_pending then
            local released = self:_h5_release_group(key)
            if not released then
                any_remaining = true
            end
        end
    end
    if not any_remaining then
        local has_any = false
        for _ in pairs(self._h5_groups) do
            has_any = true
            break
        end
        if not has_any then
            self._h5_groups = nil
        end
    end
    self:_sync_h5_id_label_visibility()
end

function RT:_release_all_h5()
    h5_child_index_reset()
    if not self._h5_groups then
        self:_sync_h5_id_label_visibility()
        return
    end
    local any_pending = false
    for key, state in pairs(self._h5_groups) do
        if state._release_pending then
            any_pending = true
        else
            local released = self:_h5_release_group(key)
            if not released then any_pending = true end
        end
    end
    if not any_pending then
        self._h5_groups = nil
    end
    self:_sync_h5_id_label_visibility()
end

function RT:_release_h5()
    self:_release_all_h5()
end

function RT:_sync_local_backdrop(t, perf, crew_receipt)
    self:_apply_native_priority(t)
    if perf then self:_perf_mark(perf, "native_priority") end
    local certifications = self:_coordinate_h5_native_duplicates(crew_receipt)
    if perf then self:_perf_mark(perf, "native_replace") end
    if t ~= nil then
        if self._last_backdrop_sync ~= nil and t >= self._last_backdrop_sync
            and (t - self._last_backdrop_sync) < BG_THROTTLE then
            return
        end
        self._last_backdrop_sync = t
    end
    if not _backdrop_coverage(certifications) then
        if self._local_bg_panel and panel_alive(self._local_bg_panel) then
            safe_call(self._local_bg_panel, "set_visible", false)
        end
        self._local_backdrop_verified = false
        return
    end
    local geom = self:_local_backdrop_geometry()
    if not geom then
        if self._local_bg_panel and panel_alive(self._local_bg_panel) then
            safe_call(self._local_bg_panel, "set_visible", false)
        end
        self._local_backdrop_verified = false
        return
    end
    local root = self._root_panel
    if not root or not panel_alive(root) then
        self._local_backdrop_verified = false
        return
    end
    local bg = self._local_bg_panel
    if not bg or not panel_alive(bg) then
        local cs, existing = safe_call(root, "child", BG_ROOT_NAME)
        if cs ~= CALL_OK then
            self._local_backdrop_verified = false
            return
        end
        if existing ~= nil and panel_alive(existing) then
            self._local_backdrop_verified = false
            return
        end
        local ps, new_bg = safe_call(root, "panel", {name = BG_ROOT_NAME, layer = -1, x = geom.x, y = geom.y, w = geom.w, h = geom.h})
        if ps ~= CALL_OK or not new_bg then
            self._local_backdrop_verified = false
            return
        end
        bg = new_bg
        self._local_bg_body = nil
        self._local_bg_cut = nil
        self._local_bg_verts_cache = nil
        self._local_bg_panel = bg
    end
    local body = self._local_bg_body
    if not body or not panel_alive(body) then
        local bs, existing = safe_call(bg, "child", BG_BODY_NAME)
        if bs ~= CALL_OK then
            safe_call(bg, "set_visible", false)
            self._local_backdrop_verified = false
            return
        end
        if existing ~= nil and panel_alive(existing) then
            safe_call(bg, "set_visible", false)
            self._local_backdrop_verified = false
            return
        end
        local rs, new_body = safe_call(bg, "rect", {name = BG_BODY_NAME, layer = 0})
        if rs ~= CALL_OK or not new_body then
            safe_call(bg, "set_visible", false)
            self._local_backdrop_verified = false
            return
        end
        body = new_body
        self._local_bg_body = body
    end
    local cut = self._local_bg_cut
    local cached_w = self._local_bg_layout and self._local_bg_layout.w
    local cached_h = self._local_bg_layout and self._local_bg_layout.h
    local cached_r = self._local_bg_layout and self._local_bg_layout.radius
    local dims_changed = not self._local_bg_layout
        or not finite(cached_w) or not finite(cached_h) or not finite(cached_r)
        or not finite(geom.w) or not finite(geom.h) or not finite(geom.radius)
        or math.abs(cached_w - geom.w) > 0.01
        or math.abs(cached_h - geom.h) > 0.01
        or math.abs(cached_r - geom.radius) > 0.01
    local cut_alive = cut and panel_alive(cut)
    if not cut_alive or dims_changed then
        if cut_alive then
            safe_call(bg, "remove", cut)
            self._local_bg_cut = nil
        else
            local ls, cut_existing = safe_call(bg, "child", BG_CUT_NAME)
            if ls ~= CALL_OK then
                safe_call(bg, "set_visible", false)
                self._local_backdrop_verified = false
                return
            end
            if cut_existing ~= nil and panel_alive(cut_existing) then
                safe_call(bg, "set_visible", false)
                self._local_backdrop_verified = false
                return
            end
        end
        local verts = self:_backdrop_cut_verts(geom)
        local rs, new_cut = safe_call(bg, "polygon", {name = BG_CUT_NAME, layer = 0, x = 0, y = 0, w = geom.cut_w, h = geom.h, triangles = verts})
        if rs ~= CALL_OK or not new_cut then
            safe_call(bg, "set_visible", false)
            self._local_backdrop_verified = false
            return
        end
        cut = new_cut
        self._local_bg_cut = cut
    end
    local fail = false
    local s1 = safe_call(bg, "set_shape", geom.x, geom.y, geom.w, geom.h)
    if s1 ~= CALL_OK then fail = true end
    safe_call(bg, "set_layer", -1)
    safe_call(bg, "set_alpha", 1)
    if not fail then
        local s2 = safe_call(body, "set_shape", geom.body_x, 0, geom.body_w, geom.h)
        if s2 ~= CALL_OK then fail = true end
    end
    if not BG_TINT then BG_TINT = Color(1, BG_R, BG_G, BG_B) end
    if not fail then
        local s3 = safe_call(body, "set_color", BG_TINT)
        if s3 ~= CALL_OK then fail = true end
        local s4 = safe_call(body, "set_alpha", BG_A)
        if s4 ~= CALL_OK then fail = true end
    end
    if not fail then
        local s5 = safe_call(cut, "set_shape", 0, 0, geom.w, geom.h)
        if s5 ~= CALL_OK then fail = true end
    end
    if not fail then
        local s6 = safe_call(cut, "set_color", BG_TINT)
        if s6 ~= CALL_OK then fail = true end
        local s7 = safe_call(cut, "set_alpha", BG_A)
        if s7 ~= CALL_OK then fail = true end
    end
    if fail then
        safe_call(bg, "set_visible", false)
        self._local_backdrop_verified = false
        return
    end
    safe_call(body, "set_visible", true)
    safe_call(body, "set_layer", 0)
    safe_call(cut, "set_visible", true)
    safe_call(cut, "set_layer", 0)
    safe_call(bg, "set_visible", true)
    self._local_bg_layout = {
        x = geom.x, y = geom.y, w = geom.w, h = geom.h,
        cut_w = geom.cut_w, body_x = geom.body_x, body_w = geom.body_w,
        radius = geom.radius, e = geom.e,
    }
    self._local_backdrop_verified = self:_verify_local_backdrop(certifications)
    if not self._local_backdrop_verified then
        safe_call(bg, "set_visible", false)
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

local function safe_pre_hook(class, method, id, fn)
    if type(class) ~= "table" then return end
    if kyohud.hud._installed_hooks[id] then return end
    if type(class[method]) ~= "function" then return end
    Hooks:PreHook(class, method, id, fn)
    kyohud.hud._installed_hooks[id] = true
end

if RequiredScript == REQUIRED_CONTEXT then
    local function cb_mount(self)
        local mission = kyohud.hud.mission
        if mission then mission:on_heist_start(self) end
        local objectives = kyohud.hud.objectives
        if objectives then objectives:on_heist_start(self) end
        local alerts = kyohud.hud.alerts
        if type(alerts) == "table" and type(alerts.on_heist_start) == "function" then
            alerts:on_heist_start(self)
        end
        local assault = kyohud.hud.assault
        if type(assault) == "table" then
            assault:on_heist_start(self)
        end
        kyohud.hud.runtime:on_heist_start(self)
        kyohud.hud.runtime:mount(self)
    end
    local function cb_rebuild(self)
        if kyohud.hud.runtime._mounted and kyohud.hud.runtime._manager == self then
            kyohud.hud.runtime:rebuild(self)
        end
    end
    local function cb_refresh(self)
        if kyohud.hud.runtime._manager == self then
            kyohud.hud.runtime:refresh_settings(self)
        end
    end
    local function cb_disabled(self)
        if kyohud.hud.runtime._manager == self then
            kyohud.hud.runtime._disabled = true
            apply_visibility()
        end
    end
    local function cb_enabled(self)
        if kyohud.hud.runtime._manager == self then
            kyohud.hud.runtime._disabled = false
            apply_visibility()
        end
    end
    local function cb_ff_disabled(self)
        if kyohud.hud.runtime._manager == self then
            kyohud.hud.runtime._freeflight = true
            apply_visibility()
        end
    end
    local function cb_ff_enabled(self)
        if kyohud.hud.runtime._manager == self then
            kyohud.hud.runtime._freeflight = false
            apply_visibility()
        end
    end
    local function cb_update(self, t, dt)
        if kyohud.hud.runtime._manager == self then
            kyohud.hud.runtime:update(self, t, dt)
        end
    end
    local function cb_destroy(self)
        kyohud.hud.runtime:destroy(self)
    end

    safe_hook(HUDManager, "init_finalize", "KyohHUD_Runtime_InitFinalize", cb_mount)
    safe_hook(HUDManager, "_setup_player_info_hud_pd2", "KyohHUD_Runtime_SetupPlayerInfo", cb_rebuild)
    safe_hook(HUDManager, "resolution_changed", "KyohHUD_Runtime_ResolutionChanged", cb_refresh)
    safe_hook(HUDManager, "set_disabled", "KyohHUD_Runtime_SetDisabled", cb_disabled)
    safe_hook(HUDManager, "set_enabled", "KyohHUD_Runtime_SetEnabled", cb_enabled)
    safe_hook(HUDManager, "set_freeflight_disabled", "KyohUD_Runtime_FFDisabled", cb_ff_disabled)
    safe_hook(HUDManager, "set_freeflight_enabled", "KyohUD_Runtime_FFEnabled", cb_ff_enabled)
    safe_hook(HUDManager, "update", "KyohHUD_Runtime_Update", cb_update)
    safe_pre_hook(HUDManager, "destroy", "KyohHUD_Runtime_Destroy", cb_destroy)
end
