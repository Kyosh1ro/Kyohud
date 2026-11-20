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

RT._h5_owner = RT._h5_owner or "kyohud_h5"
RT._h5_generation = RT._h5_generation or 0
RT._h5_targets = RT._h5_targets
RT._h5_source_id = RT._h5_source_id

RT._priority_trace_emitted = RT._priority_trace_emitted or 0
RT._priority_trace_episode = RT._priority_trace_episode or false

if RT._stoic_trace_checked == nil then
    RT._stoic_trace_checked = true
    RT._stoic_trace_enabled = false
    RT._stoic_trace_emitted = RT._stoic_trace_emitted or 0
    local trace_path
    if type(ModPath) == "string" then
        trace_path = ModPath .. "KYO_STOIC_TRACE"
    end
    if trace_path ~= nil and type(io) == "table" and type(io.open) == "function" then
        local open_ok, handle = pcall(io.open, trace_path, "r")
        if open_ok and handle ~= nil then
            RT._stoic_trace_enabled = true
            pcall(function() handle:read("*a") end)
            pcall(function() handle:close() end)
        end
    end
end

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
local STOIC_TRACE_LIMIT = 40
local PRIORITY_TRACE_LIMIT = 16
local H5_HACKER_ACTIVE_GROUP = "local_p_hacker_active"
local KINGPIN_LOCAL_SOURCE = "chico_injector_local"
local KINGPIN_TERMINAL_SOURCE = "chico_injector_terminal"
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

-- Temporary opt-in residual diagnostic. It exists only when the runtime chunk
-- finds KYO_RESIDUAL_PERF under ModPath at load. An optional KYO_OBJECTIVES_PERF
-- is probed only after that general sentinel and selects completion capture
-- instead of the general warmup. There is no option, manifest or native field.
function RT:_residual_load()
    self._residual_probe = nil
    if type(ModPath) ~= "string" or ModPath == "" then return end
    if type(io) ~= "table" or type(io.open) ~= "function" then return end
    local ok_open, handle = pcall(io.open, ModPath .. "KYO_RESIDUAL_PERF", "r")
    if not ok_open or not handle then return end
    pcall(function() handle:close() end)
    local completion_mode = false
    local ok_objectives, objectives_handle = pcall(io.open, ModPath .. "KYO_OBJECTIVES_PERF", "r")
    if ok_objectives and objectives_handle then
        pcall(function() objectives_handle:close() end)
        completion_mode = true
    end
    local kingpin_mode = false
    if not completion_mode then
        local ok_kingpin, kingpin_handle = pcall(io.open, ModPath .. "KYO_KINGPIN_PERF", "r")
        if ok_kingpin and kingpin_handle then
            pcall(function() kingpin_handle:close() end)
            kingpin_mode = true
        end
    end
    self._residual_probe = {
        mode = completion_mode and "completion" or (kingpin_mode and "kingpin" or nil),
        active = false,
        done = false,
        aborted = false,
        warm_start = nil,
        capture_start = nil,
        last_t = nil,
        gap_16 = 0,
        gap_33 = 0,
        gap_50 = 0,
        gap_max = 0,
        kingpin_publication_depth = 0,
        kingpin_publication_pending = false,
        kingpin_publication_invalid = false,
        kingpin_publication_start = nil,
        kingpin_publication_manager = nil,
        phases = {
            alerts = {count = 0, sum = 0, max = 0},
            assault = {count = 0, sum = 0, max = 0},
            assault_verify = {count = 0, sum = 0, max = 0},
            assault_verify_full = {count = 0, sum = 0, max = 0},
            assault_verify_light = {count = 0, sum = 0, max = 0},
            assault_native = {count = 0, sum = 0, max = 0},
            assault_animation = {count = 0, sum = 0, max = 0},
            player = {count = 0, sum = 0, max = 0},
            player_capture = {count = 0, sum = 0, max = 0},
            player_render = {count = 0, sum = 0, max = 0},
            player_verify = {count = 0, sum = 0, max = 0},
            player_native_acquire = {count = 0, sum = 0, max = 0},
            crew_native_acquire = {count = 0, sum = 0, max = 0},
            weapons = {count = 0, sum = 0, max = 0},
            equipment = {count = 0, sum = 0, max = 0},
            equipment_collect = {count = 0, sum = 0, max = 0},
            equipment_snapshot = {count = 0, sum = 0, max = 0},
            equipment_present = {count = 0, sum = 0, max = 0},
            equipment_verify = {count = 0, sum = 0, max = 0},
            equipment_throttled = {count = 0, sum = 0, max = 0},
            crew = {count = 0, sum = 0, max = 0},
            harmony = {count = 0, sum = 0, max = 0},
            harmony_delayed_sync = {count = 0, sum = 0, max = 0},
            harmony_priority = {count = 0, sum = 0, max = 0},
            harmony_delayed_post = {count = 0, sum = 0, max = 0},
            reserve = {count = 0, sum = 0, max = 0},
            copr = {count = 0, sum = 0, max = 0},
            hacker_active = {count = 0, sum = 0, max = 0},
            kingpin_active = {count = 0, sum = 0, max = 0},
            kingpin_event_prepare = {count = 0, sum = 0, max = 0},
            kingpin_event_chain = {count = 0, sum = 0, max = 0},
            kingpin_event_priority = {count = 0, sum = 0, max = 0},
            kingpin_event_post = {count = 0, sum = 0, max = 0},
            kingpin_event_final = {count = 0, sum = 0, max = 0},
            kingpin_event_terminal = {count = 0, sum = 0, max = 0},
            kingpin_publication_total = {count = 0, sum = 0, max = 0},
            kingpin_publication_capture = {count = 0, sum = 0, max = 0},
            kingpin_throttle_full = {count = 0, sum = 0, max = 0},
            kingpin_prepare_attempt = {count = 0, sum = 0, max = 0},
            kingpin_prepare_fast = {count = 0, sum = 0, max = 0},
            kingpin_prepare_full = {count = 0, sum = 0, max = 0},
            kingpin_reject_dirty = {count = 0, sum = 0, max = 0},
            kingpin_reject_cache = {count = 0, sum = 0, max = 0},
            kingpin_reject_activation = {count = 0, sum = 0, max = 0},
            kingpin_reject_snapshot = {count = 0, sum = 0, max = 0},
            kingpin_reject_layout = {count = 0, sum = 0, max = 0},
            kingpin_reject_identity = {count = 0, sum = 0, max = 0},
            kingpin_reject_cooldown = {count = 0, sum = 0, max = 0},
            kingpin_reject_verify = {count = 0, sum = 0, max = 0},
            kingpin_reject_render = {count = 0, sum = 0, max = 0},
            kingpin_reject_source = {count = 0, sum = 0, max = 0},
            kingpin_reject_exception = {count = 0, sum = 0, max = 0},
            kingpin_reject_postverify = {count = 0, sum = 0, max = 0},
            kingpin_reject_other = {count = 0, sum = 0, max = 0},
            harmony_duplicates = {count = 0, sum = 0, max = 0},
            harmony_duplicates_sig = {count = 0, sum = 0, max = 0},
            harmony_duplicates_collect = {count = 0, sum = 0, max = 0},
            harmony_duplicates_validate = {count = 0, sum = 0, max = 0},
            combat_draw = {count = 0, sum = 0, max = 0},
            objectives_anim = {count = 0, sum = 0, max = 0},
            objectives_anim_idle = {count = 0, sum = 0, max = 0},
            objectives_anim_active = {count = 0, sum = 0, max = 0},
            objectives_callback = {count = 0, sum = 0, max = 0},
            recovery = {count = 0, sum = 0, max = 0},
            runtime = {count = 0, sum = 0, max = 0},
            mission_feed = {count = 0, sum = 0, max = 0},
            mission_sync = {count = 0, sum = 0, max = 0},
            mission_title_sync = {count = 0, sum = 0, max = 0},
            mission_layout = {count = 0, sum = 0, max = 0},
            mission_verify = {count = 0, sum = 0, max = 0},
            mission_labels_verify = {count = 0, sum = 0, max = 0},
        },
    }
end
RT:_residual_load()

function RT:_residual_player_alive()
    local status, unit = safe_call(managers and managers.player or nil, "player_unit")
    if status ~= CALL_OK or unit == nil then return false end
    if type(alive) ~= "function" then return true end
    local ok_alive, is_alive = pcall(alive, unit)
    return ok_alive and is_alive == true
end

function RT:_residual_stamp()
    local p = self._residual_probe
    if not p or p.done or not p.active then return nil end
    if type(os) ~= "table" then return nil end
    local clock = os.clock
    if type(clock) ~= "function" then return nil end
    local ok, now = pcall(clock)
    if not ok or not finite(now) then return nil end
    return now
end

function RT:_residual_record(name, start)
    local p = self._residual_probe
    if not p or p.done or not p.active then return end
    if type(start) ~= "number" or not finite(start) then return end
    local phase = p.phases[name]
    if not phase then return end
    local now = self:_residual_stamp()
    if now == nil then return end
    local delta = now - start
    if not finite(delta) or delta < 0 then return end
    phase.count = phase.count + 1
    phase.sum = phase.sum + delta
    if delta > phase.max then phase.max = delta end
end

local function kingpin_new_bin()
    return {
        count = 0,
        events = 0,
        heap_drop_count = 0,
        heap_drop_kb = 0,
        clock_missing = 0,
        heap_missing = 0,
        max_gap_ms = nil,
        max_gap_clock_ms = nil,
        max_gap_heap_delta_kb = nil,
        max_gap_runtime_ms = nil,
        max_gap_prepare_ms = nil,
        max_gap_chain_ms = nil,
        max_gap_priority_ms = nil,
        max_gap_post_ms = nil,
        max_gap_final_ms = nil,
        runtime_ms = 0,
        prepare_ms = 0,
        chain_ms = 0,
        priority_ms = 0,
        post_ms = 0,
        final_ms = 0,
        clock_elapsed_ms = 0,
        clock_count = 0,
        heap_rise_kb = 0,
        heap_rise_count = 0,
        heap_drop_gap_max_ms = nil,
        publication_ms = 0,
        capture_ms = 0,
        throttle_ms = 0,
        max_gap_publication_ms = nil,
        max_gap_capture_ms = nil,
        max_gap_throttle_ms = nil,
    }
end

local function kingpin_read_clock()
    if type(os) ~= "table" or type(os.clock) ~= "function" then return nil end
    local ok, value = pcall(os.clock)
    if not ok or not finite(value) or value < 0 then return nil end
    return value
end

local function kingpin_read_heap()
    if type(collectgarbage) ~= "function" then return nil end
    local ok, value = pcall(collectgarbage, "count")
    if not ok or not finite(value) or value < 0 then return nil end
    return value
end

local function kingpin_report_int(value)
    if type(value) ~= "number" or not finite(value) then return "unknown" end
    return string.format("%d", value)
end

local function kingpin_report_num(value)
    if type(value) ~= "number" or not finite(value) then return "unknown" end
    return string.format("%.3f", value)
end

local function kingpin_format_bin(label, bin)
    return string.format(
        "[KyoHUD][KingpinIntervals]: bin=%s count=%s events=%s "
        .. "heap_drop_count=%s heap_drop_kb=%s clock_missing=%s "
        .. "heap_missing=%s max_gap_ms=%s max_gap_clock_ms=%s "
        .. "max_gap_heap_delta_kb=%s max_gap_runtime_ms=%s "
        .. "max_gap_prepare_ms=%s max_gap_chain_ms=%s "
        .. "max_gap_priority_ms=%s max_gap_post_ms=%s "
        .. "max_gap_final_ms=%s runtime_ms=%s prepare_ms=%s chain_ms=%s "
        .. "priority_ms=%s post_ms=%s final_ms=%s clock_elapsed_ms=%s "
        .. "clock_count=%s heap_rise_kb=%s heap_rise_count=%s "
        .. "heap_drop_gap_max_ms=%s publication_ms=%s capture_ms=%s throttle_ms=%s "
        .. "max_gap_publication_ms=%s max_gap_capture_ms=%s max_gap_throttle_ms=%s",
        label,
        kingpin_report_int(bin.count),
        kingpin_report_int(bin.events),
        kingpin_report_int(bin.heap_drop_count),
        kingpin_report_num(bin.heap_drop_kb),
        kingpin_report_int(bin.clock_missing),
        kingpin_report_int(bin.heap_missing),
        kingpin_report_num(bin.max_gap_ms),
        kingpin_report_num(bin.max_gap_clock_ms),
        kingpin_report_num(bin.max_gap_heap_delta_kb),
        kingpin_report_num(bin.max_gap_runtime_ms),
        kingpin_report_num(bin.max_gap_prepare_ms),
        kingpin_report_num(bin.max_gap_chain_ms),
        kingpin_report_num(bin.max_gap_priority_ms),
        kingpin_report_num(bin.max_gap_post_ms),
        kingpin_report_num(bin.max_gap_final_ms),
        kingpin_report_num(bin.runtime_ms),
        kingpin_report_num(bin.prepare_ms),
        kingpin_report_num(bin.chain_ms),
        kingpin_report_num(bin.priority_ms),
        kingpin_report_num(bin.post_ms),
        kingpin_report_num(bin.final_ms),
        kingpin_report_num(bin.clock_elapsed_ms),
        kingpin_report_int(bin.clock_count),
        kingpin_report_num(bin.heap_rise_kb),
        kingpin_report_int(bin.heap_rise_count),
        kingpin_report_num(bin.heap_drop_gap_max_ms),
        kingpin_report_num(bin.publication_ms),
        kingpin_report_num(bin.capture_ms),
        kingpin_report_num(bin.throttle_ms),
        kingpin_report_num(bin.max_gap_publication_ms),
        kingpin_report_num(bin.max_gap_capture_ms),
        kingpin_report_num(bin.max_gap_throttle_ms))
end

local function kingpin_emit(line)
    if type(log) == "function" then pcall(log, line) end
end

function RT:_kingpin_interval_sample(t)
    local p = self._residual_probe
    if not p or p.done or not p.active then return end
    if p.mode ~= "kingpin" then return end
    if type(t) ~= "number" or not finite(t) then return end
    local iv = p.kingpin_intervals
    if iv == nil then
        iv = {
            attempts = 0,
            capped = false,
            reported = false,
            bins = {
                published = kingpin_new_bin(),
                terminal = kingpin_new_bin(),
                no_publication = kingpin_new_bin(),
            },
            prev_t = nil,
            prev_clock = nil,
            prev_heap = nil,
            prev_terminal = 0,
            prev_prepare = 0,
            prev_runtime = 0,
            prev_event_prepare = 0,
            prev_event_chain = 0,
            prev_event_priority = 0,
            prev_event_post = 0,
            prev_event_final = 0,
        }
        p.kingpin_intervals = iv
    end
    if iv.capped then return end

    local clock_now = kingpin_read_clock()
    local heap_now = kingpin_read_heap()

    local attempts = (iv.attempts or 0) + 1
    iv.attempts = attempts
    if attempts >= 4096 then iv.capped = true end

    local ph = p.phases
    local cur_terminal = (ph.kingpin_event_terminal and ph.kingpin_event_terminal.count) or 0
    local cur_prepare = (ph.kingpin_prepare_attempt and ph.kingpin_prepare_attempt.count) or 0
    local cur_runtime = (ph.runtime and ph.runtime.sum) or 0
    local cur_event_prepare = (ph.kingpin_event_prepare and ph.kingpin_event_prepare.sum) or 0
    local cur_event_chain = (ph.kingpin_event_chain and ph.kingpin_event_chain.sum) or 0
    local cur_event_priority = (ph.kingpin_event_priority and ph.kingpin_event_priority.sum) or 0
    local cur_event_post = (ph.kingpin_event_post and ph.kingpin_event_post.sum) or 0
    local cur_event_final = (ph.kingpin_event_final and ph.kingpin_event_final.sum) or 0
    local cur_publication = (ph.kingpin_publication_total and ph.kingpin_publication_total.sum) or 0
    local cur_capture = (ph.kingpin_publication_capture and ph.kingpin_publication_capture.sum) or 0
    local cur_throttle = (ph.kingpin_throttle_full and ph.kingpin_throttle_full.sum) or 0

    if attempts == 1 then
        iv.prev_t = t
        iv.prev_clock = clock_now
        iv.prev_heap = heap_now
        iv.prev_terminal = cur_terminal
        iv.prev_prepare = cur_prepare
        iv.prev_runtime = cur_runtime
        iv.prev_event_prepare = cur_event_prepare
        iv.prev_event_chain = cur_event_chain
        iv.prev_event_priority = cur_event_priority
        iv.prev_event_post = cur_event_post
        iv.prev_event_final = cur_event_final
        iv.prev_publication = cur_publication
        iv.prev_capture = cur_capture
        iv.prev_throttle = cur_throttle
        return
    end

    local terminal_delta = cur_terminal - (iv.prev_terminal or 0)
    local prepare_delta = cur_prepare - (iv.prev_prepare or 0)
    local runtime_delta = cur_runtime - (iv.prev_runtime or 0)
    local event_prepare_delta = cur_event_prepare - (iv.prev_event_prepare or 0)
    local event_chain_delta = cur_event_chain - (iv.prev_event_chain or 0)
    local event_priority_delta = cur_event_priority - (iv.prev_event_priority or 0)
    local event_post_delta = cur_event_post - (iv.prev_event_post or 0)
    local event_final_delta = cur_event_final - (iv.prev_event_final or 0)
    local publication_delta = cur_publication - (iv.prev_publication or 0)
    local capture_delta = cur_capture - (iv.prev_capture or 0)
    local throttle_delta = cur_throttle - (iv.prev_throttle or 0)

    local bin
    if terminal_delta > 0 then
        bin = iv.bins.terminal
    elseif prepare_delta > 0 then
        bin = iv.bins.published
    else
        bin = iv.bins.no_publication
    end

    local gap_ms = nil
    if iv.prev_t ~= nil then
        local gap = (t - iv.prev_t) * 1000
        if finite(gap) and gap >= 0 then gap_ms = gap end
    end

    local clock_delta_ms = nil
    if clock_now ~= nil and iv.prev_clock ~= nil and clock_now >= iv.prev_clock then
        local delta = (clock_now - iv.prev_clock) * 1000
        if finite(delta) then clock_delta_ms = delta end
    end
    if clock_delta_ms == nil then
        bin.clock_missing = bin.clock_missing + 1
    else
        bin.clock_elapsed_ms = bin.clock_elapsed_ms + clock_delta_ms
        bin.clock_count = bin.clock_count + 1
    end

    local heap_delta_kb = nil
    if heap_now ~= nil and iv.prev_heap ~= nil then
        local delta = heap_now - iv.prev_heap
        if finite(delta) then heap_delta_kb = delta end
    end
    if heap_delta_kb == nil then
        bin.heap_missing = bin.heap_missing + 1
    elseif heap_delta_kb > 0 then
        bin.heap_rise_kb = bin.heap_rise_kb + heap_delta_kb
        bin.heap_rise_count = bin.heap_rise_count + 1
    elseif heap_delta_kb < 0 then
        bin.heap_drop_count = bin.heap_drop_count + 1
        bin.heap_drop_kb = bin.heap_drop_kb + (-heap_delta_kb)
        if gap_ms ~= nil and (bin.heap_drop_gap_max_ms == nil or gap_ms > bin.heap_drop_gap_max_ms) then
            bin.heap_drop_gap_max_ms = gap_ms
        end
    end

    bin.count = bin.count + 1
    bin.events = bin.events + terminal_delta + prepare_delta

    local runtime_ms = runtime_delta * 1000
    local event_prepare_ms = event_prepare_delta * 1000
    local event_chain_ms = event_chain_delta * 1000
    local event_priority_ms = event_priority_delta * 1000
    local event_post_ms = event_post_delta * 1000
    local event_final_ms = event_final_delta * 1000
    bin.runtime_ms = bin.runtime_ms + runtime_ms
    bin.prepare_ms = bin.prepare_ms + event_prepare_ms
    bin.chain_ms = bin.chain_ms + event_chain_ms
    bin.priority_ms = bin.priority_ms + event_priority_ms
    bin.post_ms = bin.post_ms + event_post_ms
    bin.final_ms = bin.final_ms + event_final_ms
    local publication_ms = publication_delta * 1000
    local capture_ms = capture_delta * 1000
    local throttle_ms = throttle_delta * 1000
    bin.publication_ms = (bin.publication_ms or 0) + publication_ms
    bin.capture_ms = (bin.capture_ms or 0) + capture_ms
    bin.throttle_ms = (bin.throttle_ms or 0) + throttle_ms

    if gap_ms ~= nil then
        if bin.max_gap_ms == nil or gap_ms > bin.max_gap_ms then
            bin.max_gap_ms = gap_ms
            bin.max_gap_clock_ms = clock_delta_ms
            bin.max_gap_heap_delta_kb = heap_delta_kb
            bin.max_gap_runtime_ms = runtime_ms
            bin.max_gap_prepare_ms = event_prepare_ms
            bin.max_gap_chain_ms = event_chain_ms
            bin.max_gap_priority_ms = event_priority_ms
            bin.max_gap_post_ms = event_post_ms
            bin.max_gap_final_ms = event_final_ms
            bin.max_gap_publication_ms = publication_ms
            bin.max_gap_capture_ms = capture_ms
            bin.max_gap_throttle_ms = throttle_ms
        end
    end

    iv.prev_t = t
    iv.prev_clock = clock_now
    iv.prev_heap = heap_now
    iv.prev_terminal = cur_terminal
    iv.prev_prepare = cur_prepare
    iv.prev_runtime = cur_runtime
    iv.prev_event_prepare = cur_event_prepare
    iv.prev_event_chain = cur_event_chain
    iv.prev_event_priority = cur_event_priority
    iv.prev_event_post = cur_event_post
    iv.prev_event_final = cur_event_final
    iv.prev_publication = cur_publication
    iv.prev_capture = cur_capture
    iv.prev_throttle = cur_throttle
end

function RT:_kingpin_interval_report(status)
    local p = self._residual_probe
    if not p or p.mode ~= "kingpin" then return end
    local iv = p.kingpin_intervals
    if type(iv) ~= "table" or iv.reported then return end
    iv.reported = true
    local bins = iv.bins
    local ok_pub, line_pub = pcall(kingpin_format_bin, "published", bins.published)
    if not ok_pub then line_pub = "[KyoHUD][KingpinIntervals]: bin=published format_failed" end
    local ok_term, line_term = pcall(kingpin_format_bin, "terminal", bins.terminal)
    if not ok_term then line_term = "[KyoHUD][KingpinIntervals]: bin=terminal format_failed" end
    local ok_nop, line_nop = pcall(kingpin_format_bin, "no_publication", bins.no_publication)
    if not ok_nop then line_nop = "[KyoHUD][KingpinIntervals]: bin=no_publication format_failed" end
    local ok_meta, line_meta = pcall(string.format,
        "[KyoHUD][KingpinIntervals]: meta attempts=%s capped=%s status=%s; "
        .. "Lua heap KB net; os.clock wall elapsed not CPU; "
        .. "HUD entry intervals not GPU and not presented frames; no_publication not inactive; "
        .. "publication_ms includes capture and event; throttle_ms includes verification and render; "
        .. "runtime/event scopes may overlap do not add; "
        .. "never add or subtract independent maxima; "
        .. "heap drop not GC cause; first partial and abort partial excluded",
        tostring(iv.attempts), tostring(iv.capped), tostring(status))
    if not ok_meta then line_meta = "[KyoHUD][KingpinIntervals]: meta format_failed" end
    kingpin_emit(line_pub)
    kingpin_emit(line_term)
    kingpin_emit(line_nop)
    kingpin_emit(line_meta)
end

function RT:_residual_abort(reason)
    local p = self._residual_probe
    if not p or p.done then return end
    p.done = true
    p.active = false
    self:_kingpin_interval_report("abort")
    if p.aborted then return end
    p.aborted = true
    pcall(log, "[KyoHUD][ResidualProbe] aborted: " .. (reason or "invalid"))
end

function RT:_residual_finish()
    local p = self._residual_probe
    if not p or p.done then return end
    p.done = true
    p.active = false
    local ph = p.phases
    local label = "HUD intervals, not GPU; os.clock quantized; runtime inclusive; nested under assault; mission_feed outside runtime; mission_sync/layout/verify inclusive all callers incl recovery; mission_title_sync inclusive title sync/fitting nested under mission_sync for all callers and mission_labels_verify is inclusive on all _verify_labels callers; since the layout optimization the _update_layout branch runs only when the state is not verified (_render_verified ~= true), so on stable certified feeds only the _verify_render call counts, neither pure text_rect nor translation time; do not add nested mission totals to module totals; objectives_anim runtime inclusive; objectives_anim_idle/active split eligible animate only (early returns unclassified) and the finishing frame counts active; objectives_callback nested/overlapping, no sum totals"
        .. "; harmony_delayed_sync/priority/delayed_post/duplicates nested under harmony but all callers count (overlaps possible); reserve aggregates pre-priority sync and post-priority release checks, nested under harmony, all callers count; copr aggregates pre-priority sync and post-priority release checks, nested under harmony, all callers count; hacker_active is nested-inclusive around the hacker-active event plus its pre-priority sync and post-priority checks for all callers and stays distinct from the separate harmony_priority checks; kingpin_active is nested-inclusive around the Kingpin activity event plus its pre-priority sync, post-priority checks and terminal/invalid branch for all callers, overlaps generic equipment phases, and is never summed with them; backdrop work unclassified residue; combat_draw outside runtime"
        .. "; equipment_collect/equipment_snapshot/equipment_present/equipment_verify are nested-inclusive overlapping equipment phases (snapshot and verify inside present, H5 certification verify, HUD transition callers included) and equipment_throttled counts equipment update throttle early returns; they overlap each other and the overall equipment bucket, so never sum them"
        .. "; player_capture/player_render/player_verify are nested inclusive overlapping player phases (render and verify nest under capture through the real player path) and player_native_acquire/crew_native_acquire time only the real _h5_acquire_group native acquisition for local_ prefixed and crew_ groups respectively, excluding coordination and target collection; never sum them"
        .. "; kingpin_event_prepare/chain/priority/post/final/terminal are Kingpin event ONLY nested sub-phases counted solely inside the synchronous phase==kingpin_active seam plus its existing terminal/invalid branch; they exclude normal runtime/throttled phase detail (still in the old kingpin_active total), pre-seam native work, source qualification and GPU/GC and are never additive to module or kingpin_active totals; kingpin_event_priority/post/final are recorded only on non-stable events (first acquisition, new activation, re-acquired lease or released binding) and are legitimately zero on a stable continuation because the chain has just re-verified the held lease and the prepare has just certified the owned render, while the generic priority and the per-frame throttle verification still run every frame"
        .. "; kingpin_publication_total is nested-inclusive only around the native HUD set_player_ability_radial relay plus the nested set_teammate_ability_radial capture/seam it triggers; it excludes pre-call PlayerDamage work, later same-method PostHooks and outer wrappers; it is wall elapsed, not CPU or presented frames; overlapping inner scopes do not add"
        .. "; kingpin_publication_capture times only the two publication capture callbacks (_capture_activity and _capture_kingpin_activity), excluding the local rejection fallback, the pre-seam gate and the native setter/event seam; kingpin_throttle_full times the full throttled equipment update including render and all certification but not the equipment_throttled preamble; both are wall elapsed, not CPU or presented frames; publication includes capture/event and throttle includes verification/render; runtime/event scopes overlap and independent maxima must never be added or subtracted"
        .. "; kingpin_prepare_attempt/fast/full and kingpin_reject_dirty/cache/activation/snapshot/layout/identity/cooldown/verify/render/source/exception/postverify/other are count-only counters, not timings; only count is emitted, sum/max remain zero"
        .. "; harmony_duplicates_sig/collect/validate are nested-inclusive sub-phases under harmony_duplicates and are never additive: sig covers the crew coverage signature build, its prev/new compare and the memo store; collect covers every coordination target collection (crew per position plus the local player/weapons/equipment/cooldown collections); validate covers the per-position validation reads (card visibility, seen_slots, has_pos, owner_matches and entry_panel resolution) excluding collection and native acquisition"
    if p.mode == "completion" then
        label = label .. "; mode=completion"
    elseif p.mode == "kingpin" then
        label = label .. "; mode=kingpin; capture anchored to previous validated update time; excludes pre-trigger and native work"
    end
    local inconclusive = ""
    if ph.runtime.sum == 0 then inconclusive = "; timing inconclusive" end
    local ok_format, message = pcall(string.format,
        "[KyoHUD][ResidualProbe] alerts %d %.3f %.3f; assault %d %.3f %.3f; "
        .. "assault_verify %d %.3f %.3f; assault_verify_full %d %.3f %.3f; assault_verify_light %d %.3f %.3f; "
        .. "assault_native %d %.3f %.3f; assault_animation %d %.3f %.3f; "
        .. "player %d %.3f %.3f; "
        .. "player_capture %d %.3f %.3f; player_render %d %.3f %.3f; "
        .. "player_verify %d %.3f %.3f; "
        .. "player_native_acquire %d %.3f %.3f; crew_native_acquire %d %.3f %.3f; "
        .. "weapons %d %.3f %.3f; equipment %d %.3f %.3f; "
        .. "equipment_collect %d %.3f %.3f; equipment_snapshot %d %.3f %.3f; "
        .. "equipment_present %d %.3f %.3f; equipment_verify %d %.3f %.3f; "
        .. "equipment_throttled %d %.3f %.3f; "
        .. "crew %d %.3f %.3f; harmony %d %.3f %.3f; objectives_anim %d %.3f %.3f; "
        .. "objectives_anim_idle %d %.3f %.3f; objectives_anim_active %d %.3f %.3f; "
        .. "objectives_callback %d %.3f %.3f; "
        .. "recovery %d %.3f %.3f; runtime %d %.3f %.3f; "
        .. "mission_feed %d %.3f %.3f; mission_sync %d %.3f %.3f; "
        .. "mission_title_sync %d %.3f %.3f; "
        .. "mission_layout %d %.3f %.3f; mission_verify %d %.3f %.3f; "
        .. "mission_labels_verify %d %.3f %.3f; "
        .. "harmony_delayed_sync %d %.3f %.3f; harmony_priority %d %.3f %.3f; "
        .. "harmony_delayed_post %d %.3f %.3f; reserve %d %.3f %.3f; "
        .. "copr %d %.3f %.3f; hacker_active %d %.3f %.3f; "
        .. "kingpin_active %d %.3f %.3f; "
        .. "kingpin_event_prepare %d %.3f %.3f; kingpin_event_chain %d %.3f %.3f; "
        .. "kingpin_event_priority %d %.3f %.3f; kingpin_event_post %d %.3f %.3f; "
        .. "kingpin_event_final %d %.3f %.3f; kingpin_event_terminal %d %.3f %.3f; "
        .. "kingpin_publication_total %d %.3f %.3f; "
        .. "kingpin_publication_capture %d %.3f %.3f; kingpin_throttle_full %d %.3f %.3f; "
        .. "kingpin_prepare_attempt %d; kingpin_prepare_fast %d; kingpin_prepare_full %d; "
        .. "kingpin_reject_dirty %d; kingpin_reject_cache %d; kingpin_reject_activation %d; "
        .. "kingpin_reject_snapshot %d; kingpin_reject_layout %d; kingpin_reject_identity %d; "
        .. "kingpin_reject_cooldown %d; kingpin_reject_verify %d; kingpin_reject_render %d; "
        .. "kingpin_reject_source %d; kingpin_reject_exception %d; kingpin_reject_postverify %d; "
        .. "kingpin_reject_other %d; "
        .. "harmony_duplicates %d %.3f %.3f; "
        .. "harmony_duplicates_sig %d %.3f %.3f; "
        .. "harmony_duplicates_collect %d %.3f %.3f; "
        .. "harmony_duplicates_validate %d %.3f %.3f; "
        .. "combat_draw %d %.3f %.3f; "
        .. "gaps >16.7ms %d >33.3ms %d >50ms %d max_ms %.3f; %s%s",
        ph.alerts.count, ph.alerts.sum * 1000, ph.alerts.max * 1000,
        ph.assault.count, ph.assault.sum * 1000, ph.assault.max * 1000,
        ph.assault_verify.count, ph.assault_verify.sum * 1000, ph.assault_verify.max * 1000,
        ph.assault_verify_full.count, ph.assault_verify_full.sum * 1000, ph.assault_verify_full.max * 1000,
        ph.assault_verify_light.count, ph.assault_verify_light.sum * 1000, ph.assault_verify_light.max * 1000,
        ph.assault_native.count, ph.assault_native.sum * 1000, ph.assault_native.max * 1000,
        ph.assault_animation.count, ph.assault_animation.sum * 1000, ph.assault_animation.max * 1000,
        ph.player.count, ph.player.sum * 1000, ph.player.max * 1000,
        ph.player_capture.count, ph.player_capture.sum * 1000, ph.player_capture.max * 1000,
        ph.player_render.count, ph.player_render.sum * 1000, ph.player_render.max * 1000,
        ph.player_verify.count, ph.player_verify.sum * 1000, ph.player_verify.max * 1000,
        ph.player_native_acquire.count, ph.player_native_acquire.sum * 1000, ph.player_native_acquire.max * 1000,
        ph.crew_native_acquire.count, ph.crew_native_acquire.sum * 1000, ph.crew_native_acquire.max * 1000,
        ph.weapons.count, ph.weapons.sum * 1000, ph.weapons.max * 1000,
        ph.equipment.count, ph.equipment.sum * 1000, ph.equipment.max * 1000,
        ph.equipment_collect.count, ph.equipment_collect.sum * 1000, ph.equipment_collect.max * 1000,
        ph.equipment_snapshot.count, ph.equipment_snapshot.sum * 1000, ph.equipment_snapshot.max * 1000,
        ph.equipment_present.count, ph.equipment_present.sum * 1000, ph.equipment_present.max * 1000,
        ph.equipment_verify.count, ph.equipment_verify.sum * 1000, ph.equipment_verify.max * 1000,
        ph.equipment_throttled.count, ph.equipment_throttled.sum * 1000, ph.equipment_throttled.max * 1000,
        ph.crew.count, ph.crew.sum * 1000, ph.crew.max * 1000,
        ph.harmony.count, ph.harmony.sum * 1000, ph.harmony.max * 1000,
        ph.objectives_anim.count, ph.objectives_anim.sum * 1000, ph.objectives_anim.max * 1000,
        ph.objectives_anim_idle.count, ph.objectives_anim_idle.sum * 1000, ph.objectives_anim_idle.max * 1000,
        ph.objectives_anim_active.count, ph.objectives_anim_active.sum * 1000, ph.objectives_anim_active.max * 1000,
        ph.objectives_callback.count, ph.objectives_callback.sum * 1000, ph.objectives_callback.max * 1000,
        ph.recovery.count, ph.recovery.sum * 1000, ph.recovery.max * 1000,
        ph.runtime.count, ph.runtime.sum * 1000, ph.runtime.max * 1000,
        ph.mission_feed.count, ph.mission_feed.sum * 1000, ph.mission_feed.max * 1000,
        ph.mission_sync.count, ph.mission_sync.sum * 1000, ph.mission_sync.max * 1000,
        ph.mission_title_sync.count, ph.mission_title_sync.sum * 1000, ph.mission_title_sync.max * 1000,
        ph.mission_layout.count, ph.mission_layout.sum * 1000, ph.mission_layout.max * 1000,
        ph.mission_verify.count, ph.mission_verify.sum * 1000, ph.mission_verify.max * 1000,
        ph.mission_labels_verify.count, ph.mission_labels_verify.sum * 1000, ph.mission_labels_verify.max * 1000,
        ph.harmony_delayed_sync.count, ph.harmony_delayed_sync.sum * 1000, ph.harmony_delayed_sync.max * 1000,
        ph.harmony_priority.count, ph.harmony_priority.sum * 1000, ph.harmony_priority.max * 1000,
        ph.harmony_delayed_post.count, ph.harmony_delayed_post.sum * 1000, ph.harmony_delayed_post.max * 1000,
        ph.reserve.count, ph.reserve.sum * 1000, ph.reserve.max * 1000,
        ph.copr.count, ph.copr.sum * 1000, ph.copr.max * 1000,
        ph.hacker_active.count, ph.hacker_active.sum * 1000, ph.hacker_active.max * 1000,
        ph.kingpin_active.count, ph.kingpin_active.sum * 1000, ph.kingpin_active.max * 1000,
        ph.kingpin_event_prepare.count, ph.kingpin_event_prepare.sum * 1000, ph.kingpin_event_prepare.max * 1000,
        ph.kingpin_event_chain.count, ph.kingpin_event_chain.sum * 1000, ph.kingpin_event_chain.max * 1000,
        ph.kingpin_event_priority.count, ph.kingpin_event_priority.sum * 1000, ph.kingpin_event_priority.max * 1000,
        ph.kingpin_event_post.count, ph.kingpin_event_post.sum * 1000, ph.kingpin_event_post.max * 1000,
        ph.kingpin_event_final.count, ph.kingpin_event_final.sum * 1000, ph.kingpin_event_final.max * 1000,
        ph.kingpin_event_terminal.count, ph.kingpin_event_terminal.sum * 1000, ph.kingpin_event_terminal.max * 1000,
        ph.kingpin_publication_total.count, ph.kingpin_publication_total.sum * 1000, ph.kingpin_publication_total.max * 1000,
        ph.kingpin_publication_capture.count, ph.kingpin_publication_capture.sum * 1000, ph.kingpin_publication_capture.max * 1000,
        ph.kingpin_throttle_full.count, ph.kingpin_throttle_full.sum * 1000, ph.kingpin_throttle_full.max * 1000,
        ph.kingpin_prepare_attempt.count,
        ph.kingpin_prepare_fast.count,
        ph.kingpin_prepare_full.count,
        ph.kingpin_reject_dirty.count,
        ph.kingpin_reject_cache.count,
        ph.kingpin_reject_activation.count,
        ph.kingpin_reject_snapshot.count,
        ph.kingpin_reject_layout.count,
        ph.kingpin_reject_identity.count,
        ph.kingpin_reject_cooldown.count,
        ph.kingpin_reject_verify.count,
        ph.kingpin_reject_render.count,
        ph.kingpin_reject_source.count,
        ph.kingpin_reject_exception.count,
        ph.kingpin_reject_postverify.count,
        ph.kingpin_reject_other.count,
        ph.harmony_duplicates.count, ph.harmony_duplicates.sum * 1000, ph.harmony_duplicates.max * 1000,
        ph.harmony_duplicates_sig.count, ph.harmony_duplicates_sig.sum * 1000, ph.harmony_duplicates_sig.max * 1000,
        ph.harmony_duplicates_collect.count, ph.harmony_duplicates_collect.sum * 1000, ph.harmony_duplicates_collect.max * 1000,
        ph.harmony_duplicates_validate.count, ph.harmony_duplicates_validate.sum * 1000, ph.harmony_duplicates_validate.max * 1000,
        ph.combat_draw.count, ph.combat_draw.sum * 1000, ph.combat_draw.max * 1000,
        p.gap_16, p.gap_33, p.gap_50, p.gap_max,
        label, inconclusive)
    if ok_format then pcall(log, message) end
    self:_kingpin_interval_report("finish")
end

function RT:_residual_tick(t)
    local p = self._residual_probe
    if not p then return end
    -- An incomplete publication pair (including one unwound by a native error)
    -- must never be validated across a later tick.
    p.kingpin_publication_depth = 0
    p.kingpin_publication_pending = false
    p.kingpin_publication_invalid = false
    p.kingpin_publication_start = nil
    p.kingpin_publication_manager = nil
    if p.done then return end

    if not p.active and kyohud.settings.enable_hud_foundation ~= true then
        p.warm_start = nil
        p.last_t = nil
        return
    end

    if type(t) ~= "number" or not finite(t) then
        if p.active then
            self:_residual_abort("invalid_t")
        else
            p.warm_start = nil
            p.last_t = nil
        end
        return
    end

    local live = self:_residual_player_alive()

    if p.active then
        if not live or (p.last_t ~= nil and t < p.last_t) then
            self:_residual_abort(not live and "player_lost" or "backward_t")
            return
        end
        if p.last_t ~= nil then
            local gap_ms = (t - p.last_t) * 1000
            if finite(gap_ms) and gap_ms >= 0 then
                if gap_ms > 16.7 then p.gap_16 = p.gap_16 + 1 end
                if gap_ms > 33.3 then p.gap_33 = p.gap_33 + 1 end
                if gap_ms > 50 then p.gap_50 = p.gap_50 + 1 end
                if gap_ms > p.gap_max then p.gap_max = gap_ms end
            end
        end
        self:_kingpin_interval_sample(t)
        p.last_t = t
        if p.capture_start ~= nil and (t - p.capture_start) >= 20 then
            self:_residual_finish()
        end
        return
    end

    if not live then
        p.warm_start = nil
        p.last_t = nil
        return
    end
    if p.mode == "kingpin" then
        local mgr = self._manager
        local eligible = live
            and kyohud.settings.enable_hud_foundation == true
            and kyohud.settings.enable_equipment == true
            and self._disabled ~= true
            and self._freeflight ~= true
            and not is_vr()
            and mgr ~= nil
            and self._mounted == true
            and managers ~= nil
            and managers.hud == mgr
        if not eligible then
            p.last_t = nil
            return
        end
        if p.last_t ~= nil and t < p.last_t then
            p.last_t = nil
            return
        end
        p.last_t = t
        return
    end
    if p.mode == "completion" then
        local objectives = kyohud.hud.objectives
        local eligible = live
            and kyohud.settings.enable_objectives == true
            and objectives ~= nil
            and objectives._mounted == true
        if not eligible then
            p.last_t = nil
            return
        end
        if p.last_t ~= nil and t < p.last_t then
            p.last_t = t
            return
        end
        p.last_t = t
        return
    end
    if p.warm_start == nil then
        p.warm_start = t
        p.last_t = t
        return
    end
    if p.last_t ~= nil and t < p.last_t then
        p.warm_start = t
        p.last_t = t
        return
    end
    p.last_t = t
    if (t - p.warm_start) >= 5 then
        p.active = true
        p.capture_start = t
    end
end

function RT:_residual_note_completion()
    local p = self._residual_probe
    if not p or p.done or p.active then return end
    if p.mode ~= "completion" then return end
    local settings = kyohud.settings
    if settings.enable_hud_foundation ~= true then return end
    if settings.enable_objectives ~= true then return end
    local objectives = kyohud.hud.objectives
    if not objectives or objectives._mounted ~= true then return end
    if not self:_residual_player_alive() then return end
    local t = p.last_t
    if type(t) ~= "number" or not finite(t) then return end
    p.active = true
    p.capture_start = t
end

function RT:_kingpin_transition(stage, reason, prov)
    local p = self._residual_probe
    if not p then return end
    if p.mode ~= "kingpin" then return end
    if p.active ~= true then return end
    if p.done then return end
    local trace_count = p.trace_count or 0
    if type(trace_count) ~= "number" or trace_count >= 48 then return end

    local function read_field(obj, key)
        if obj == nil then return nil, false end
        local ok, value = pcall(function() return obj[key] end)
        if not ok then return nil, false end
        return value, true
    end

    local function scalar(value)
        if value == nil then return "unknown" end
        local value_type = type(value)
        if value_type == "boolean" then return value and "true" or "false" end
        if value_type == "number" then
            if not finite(value) then return "unknown" end
            return tostring(value)
        end
        if value_type == "string" then return value end
        return "unknown"
    end

    local function read_visible(obj)
        if obj == nil then return "unknown" end
        local method, ok = read_field(obj, "visible")
        if not ok or type(method) ~= "function" then return "unknown" end
        local called, value = pcall(method, obj)
        if not called then return "unknown" end
        if value == true or value == false then return value end
        return "unknown"
    end

    local function emit(record)
        local count = p.trace_count or 0
        if type(count) ~= "number" or count >= 48 then return false end
        p.trace_count = count + 1
        p.seq = (p.seq or 0) + 1
        pcall(function()
            local message = string.format(
                "[KyoHUD][KingpinTransition] seq=%s stage=%s t=%s anchor=%s app=%s publication=%s p_visible=%s p_verified=%s e_visible=%s native_parent_visible=%s meter_visible=%s icon_visible=%s p_ran=%s e_ran=%s reason=%s",
                scalar(p.seq),
                scalar(record.stage),
                scalar(record.t),
                scalar(record.anchor),
                scalar(record.ap),
                scalar(record.publication),
                scalar(record.p_visible),
                scalar(record.p_verified),
                scalar(record.e_visible),
                scalar(record.native_parent_visible),
                scalar(record.meter_visible),
                scalar(record.icon_visible),
                scalar(record.p_ran),
                scalar(record.e_ran),
                scalar(record.reason)
            )
            log(message)
        end)
        return true
    end

    local P = kyohud.hud.player
    local E = kyohud.hud.equipment
    local p_root
    local p_verified
    local p_ran
    if P ~= nil then
        p_root = read_field(P, "_root")
        p_verified = read_field(P, "_render_verified")
        p_ran = read_field(P, "_update_ran_now")
    end
    local e_root
    local e_ran
    if E ~= nil then
        e_root = read_field(E, "_root")
        e_ran = read_field(E, "_update_ran_now")
    end
    local p_visible = read_visible(p_root)
    local e_visible = read_visible(e_root)

    local binding = self._hacker_active_binding
    local binding_kind
    local leased = false
    if type(binding) == "table" then
        binding_kind = read_field(binding, "source_kind")
        local binding_leased = read_field(binding, "leased")
        leased = binding_kind == "chico_injector_local" and binding_leased == true
        if binding_kind == "chico_injector_local" then
            p._kingpin_native_parent = read_field(binding, "parent")
            local leaves = read_field(binding, "leaves")
            if type(leaves) == "table" then
                p._kingpin_native_meter = read_field(leaves, 1)
                p._kingpin_native_icon = read_field(leaves, 2)
            end
        end
    end
    local native_parent_visible = read_visible(p._kingpin_native_parent)
    local meter_visible = read_visible(p._kingpin_native_meter)
    local icon_visible = read_visible(p._kingpin_native_icon)

    local ap = "unknown"
    do
        local ok, value = pcall(function() return Application:time() end)
        if ok then ap = value end
    end

    local has_prov = type(prov) == "table" or type(prov) == "number"
    local raw_publication_stage = stage == "terminal_enter"
        or stage == "terminal_exit"
        or stage == "publication_rejected"
    local raw_remaining
    local raw_total
    if type(prov) == "table" then
        local remaining_value = read_field(prov, "remaining")
        raw_remaining = remaining_value
        if finite(remaining_value) then p._kingpin_remaining = remaining_value end
        local total_value = read_field(prov, "published_total")
        if not finite(total_value) then
            total_value = read_field(prov, "duration")
        end
        raw_total = total_value
        if finite(total_value) then p._kingpin_total = total_value end
    elseif type(prov) == "number" then
        raw_remaining = prov
        if finite(prov) then p._kingpin_remaining = prov end
    end
    local remaining
    local total
    if raw_publication_stage then
        remaining = raw_remaining
        total = raw_total
    else
        remaining = p._kingpin_remaining
        total = p._kingpin_total
    end
    local publication
    if raw_publication_stage then
        local remaining_text = finite(remaining) and tostring(remaining) or "unknown"
        local total_text = finite(total) and tostring(total) or "unknown"
        publication = remaining_text .. "/" .. total_text
    elseif finite(remaining) and finite(total) then
        publication = tostring(remaining) .. "/" .. tostring(total)
    elseif finite(remaining) then
        publication = tostring(remaining) .. "/unknown"
    elseif type(p._kingpin_publication) == "string" then
        publication = p._kingpin_publication
    else
        publication = "unknown"
    end
    if has_prov then
        if raw_publication_stage then
            if finite(raw_remaining) then p._kingpin_publication = publication end
        elseif finite(remaining) then
            p._kingpin_publication = publication
        end
    end

    local record = {
        stage = stage,
        reason = reason,
        t = p.last_t,
        anchor = "last_validated_update",
        ap = ap,
        publication = publication,
        p_visible = p_visible,
        p_verified = p_verified,
        e_visible = e_visible,
        native_parent_visible = native_parent_visible,
        meter_visible = meter_visible,
        icon_visible = icon_visible,
        p_ran = p_ran,
        e_ran = e_ran,
    }

    if stage == "positive" then
        p._kingpin_pending_positive = record
        return
    end

    if stage == "source_reject" or stage == "release_before" or stage == "terminal_enter"
        or stage == "publication_rejected" then
        local pending = p._kingpin_pending_positive
        if pending ~= nil then
            pending.stage = "last_positive"
            emit(pending)
            p._kingpin_pending_positive = nil
        end
    end

    if stage == "runtime_state" then
        local runtime_state = scalar(p_visible)
            .. "|" .. scalar(p_verified)
            .. "|" .. scalar(e_visible)
            .. "|" .. scalar(native_parent_visible)
            .. "|" .. scalar(meter_visible)
            .. "|" .. scalar(icon_visible)
            .. "|" .. scalar(leased)
        if runtime_state ~= p._kingpin_runtime_state then
            p._kingpin_runtime_state = runtime_state
            emit(record)
        end
    else
        emit(record)
    end
end

function RT:_residual_note_kingpin()
    local p = self._residual_probe
    if not p or p.done or p.active then return end
    if p.mode ~= "kingpin" then return end
    local settings = kyohud.settings
    if settings.enable_hud_foundation ~= true then return end
    if settings.enable_equipment ~= true then return end
    if self._disabled == true or self._freeflight == true then return end
    if is_vr() then return end
    local mgr = self._manager
    if not mgr or self._mounted ~= true or not managers or managers.hud ~= mgr then return end
    if not self:_residual_player_alive() then return end
    local E = kyohud.hud.equipment
    if type(E) ~= "table" or type(E.get_kingpin_activity_source) ~= "function" then return end
    local ok_source, source = pcall(E.get_kingpin_activity_source, E)
    if not ok_source or type(source) ~= "table" then return end
    if source.kind ~= "chico_injector_local" or source.active ~= true then return end
    local t = p.last_t
    if type(t) ~= "number" or not finite(t) then return end
    p.active = true
    p.capture_start = t
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
        -- The anchor no longer moves with coverage. Keep the owned root in
        -- place; failure hides its leaves and restores the native timer.
        mission:_update_layout()
        mission:_ensure_primitives()
        mission:_sync_primitives()
        if mission:_verify_render(not covered) then
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
    self:_release_delayed_replacement(true)
    self:_release_reserve_replacement(true)
    self:_release_copr_replacement(true)
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
    self:_release_delayed_replacement(true)
    self:_release_reserve_replacement(true)
    self:_release_copr_replacement(true)
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
    local probe = self._residual_probe
    if probe then
        self:_residual_tick(t)
    end
    local runtime_start
    if probe then
        runtime_start = self:_residual_stamp()
    end
    -- quality split approved 2026-11-10: a module whose update does not run on
    -- this frame must never retain the previous frame's ran/verified state.
    local P = kyohud.hud.player
    local W = kyohud.hud.weapons
    local E = kyohud.hud.equipment
    local C = kyohud.hud.crew
    if P then P._update_ran_now = false; P._verify_ok_now = false end
    if W then W._update_ran_now = false; W._verify_ok_now = false end
    if E then E._update_ran_now = false; E._verify_ok_now = false; E._kingpin_source_cache = nil end
    if C then C._update_ran_now = false; C._verify_ok_now = false end
    if not t then
        self:_residual_record("runtime", runtime_start)
        return
    end

    if kyohud.settings.enable_hud_foundation == true then
        local phase_start = self:_residual_stamp()
        self:_coordinate_alerts("update", t, dt)
        self:_residual_record("alerts", phase_start)
        phase_start = self:_residual_stamp()
        self:_coordinate_assault("update", t, dt)
        self:_residual_record("assault", phase_start)
        phase_start = self:_residual_stamp()
        self:_coordinate_player("update", t, dt)
        self:_residual_record("player", phase_start)
        phase_start = self:_residual_stamp()
        self:_coordinate_weapons("update", t, dt)
        self:_residual_record("weapons", phase_start)
        phase_start = self:_residual_stamp()
        self:_coordinate_equipment("update", t, dt)
        self:_residual_record("equipment", phase_start)
        phase_start = self:_residual_stamp()
        local crew_receipt = self:_coordinate_crew("update", t, dt)
        self:_residual_record("crew", phase_start)
        phase_start = self:_residual_stamp()
        self:_sync_local_backdrop(t, crew_receipt)
        pcall(self._kingpin_transition, self, "runtime_state")
        self:_residual_record("harmony", phase_start)
    end

    if kyohud.settings.enable_hud_foundation == true and kyohud.settings.enable_objectives == true then
        local objectives = kyohud.hud.objectives
        if objectives and type(objectives.animate) == "function" and objectives._mounted then
            local phase_start = self:_residual_stamp()
            objectives:animate(t, dt)
            self:_residual_record("objectives_anim", phase_start)
        end
    end

    local recovery_start = self:_residual_stamp()
    if self._last_recovery_time ~= nil and t >= self._last_recovery_time and (t - self._last_recovery_time) < RECOVERY_INTERVAL then
        self:_residual_record("recovery", recovery_start)
        self:_residual_record("runtime", runtime_start)
        return
    end

    local mgr = manager or self._manager
    self._last_recovery_time = t

    if kyohud.settings.enable_hud_foundation ~= true then
        self:_retry_pending_h5_releases()
        self:unmount()
        self:_residual_record("recovery", recovery_start)
        self:_residual_record("runtime", runtime_start)
        return
    end

    self:_retry_pending_h5_releases()

    if self._needs_refresh and self._root_panel and panel_alive(self._root_panel) then
        self:_do_refresh()
        self:_coordinate_mission("update", t, dt)
        self:_coordinate_objectives("update", t, dt)
        self:_residual_record("recovery", recovery_start)
        self:_residual_record("runtime", runtime_start)
        return
    end

    if mgr and not self._manager then
        self._manager = mgr
    end
    self:mount(mgr)
    self:_coordinate_mission("update", t, dt)
    self:_coordinate_objectives("update", t, dt)
    self:_residual_record("recovery", recovery_start)
    self:_residual_record("runtime", runtime_start)
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
local COPR_CHILD_MAX = 64
local CREW_DECK_MAX = 3
local CREW_DECK_GROUP_PREFIX = "crew_deck_"

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

function RT:_apply_native_priority_unprofiled(t, post_release)
    local trace = self._stoic_trace_enabled == true
        and (self._priority_trace_emitted or 0) < PRIORITY_TRACE_LIMIT
    local collect = trace and self._priority_trace_episode ~= true
    local active_slot = nil
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
    if not any_crew and not any_local then
        if trace and not post_release then
            self._priority_trace_episode = false
        end
        return
    end
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
    local function set_hide_local(cause, leaf, native_bounds, owned_bounds,
        effective_visible, effective_alpha)
        S.hide_local = true
        if not collect or S._priority_first ~= nil then return end
        S._priority_first = {
            cause = cause,
            leaf = leaf,
            native_bounds = native_bounds,
            owned_bounds = owned_bounds,
            slot = active_slot,
            effective_visible = effective_visible,
            effective_alpha = effective_alpha,
        }
    end
    local function known_child(parent, name, fresh, child_path)
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
        set_hide_local("child_lookup", child_path, nil, nil)
        return nil
    end
    -- The COPR binding may replace the legacy container check only while it is
    -- an exact, certified lease of this local dedicated panel: every recreated
    -- numeric notch must still be an immediate child with alpha 0. Anything else
    -- keeps the historical container observation unchanged.
    local function local_copr_replaced_leaves(entry_panel, radial)
        local binding = self._copr_binding
        if not binding or binding.leased ~= true or binding.certified ~= true then
            return nil
        end
        if binding.radial ~= radial or binding.entry_panel ~= entry_panel then
            return nil
        end
        local copr = binding.copr
        if not copr or not panel_alive(copr) then return nil end
        local cps, cparent = _pass_read(reads, copr, "parent")
        if cps ~= CALL_OK or cparent ~= radial then return nil end
        local leaves = binding.leaves
        if type(leaves) ~= "table" then return nil end
        local count = #leaves
        if count < 1 or count > COPR_CHILD_MAX then return nil end
        for i = 1, count do
            local leaf = leaves[i]
            if not leaf or not panel_alive(leaf) then return nil end
            local lps, lparent = _pass_read(reads, leaf, "parent")
            if lps ~= CALL_OK or lparent ~= copr then return nil end
            local als, alpha = _pass_read(reads, leaf, "alpha")
            if als ~= CALL_OK or not finite(alpha) or math.abs(alpha) > 0.0001 then
                return nil
            end
        end
        return leaves
    end
    -- Remote crew COPR: the crew port leases only the numeric notch leaves, so
    -- the container itself stays natively visible. Treat it as replaced only
    -- while the exact crew binding for this slot still holds every numeric
    -- child at alpha 0. Any mismatch falls back to the historical container
    -- observation.
    local function crew_copr_replaced_leaves(entry_panel, radial, copr, slot)
        local decks = self._crew_perkdeck
        local binding = type(decks) == "table" and decks[slot] or nil
        if type(binding) ~= "table" or binding.leased ~= true then return nil end
        if binding.entry_panel ~= entry_panel or binding.radial ~= radial then
            return nil
        end
        local data = binding.data
        if type(data) ~= "table" or type(data.copr) ~= "table"
            or data.copr.active ~= true then
            return nil
        end
        local leaves = binding.leaves
        if type(leaves) ~= "table" then return nil end
        local leased = {}
        for i = 1, #leaves do leased[leaves[i]] = true end
        local replaced = {}
        local leased_any = false
        local index = 0
        while index < COPR_CHILD_MAX do
            local child = known_child(copr, tostring(index), true, nil)
            if not child or not panel_alive(child) then break end
            local ps, parent = safe_call(child, "parent")
            if ps ~= CALL_OK or parent ~= copr then return nil end
            local as, alpha = safe_call(child, "alpha")
            if as ~= CALL_OK or not finite(alpha)
                or math.abs(alpha) > 0.0001 then
                return nil
            end
            if leased[child] == true then leased_any = true end
            replaced[#replaced + 1] = child
            index = index + 1
        end
        if not leased_any then return nil end
        return replaced
    end
    -- Local Hacker ACTIVE: replace only the native radial_ability container
    -- observation with its two owned, held bitmap leaves. Everything is proved
    -- fresh on every call; any invalid proof restores the leaves and falls back
    -- to the original container guard.
    local function local_hacker_replaced_leaves(entry, entry_panel, radial, parent)
        local binding = self._hacker_active_binding
        if not binding or binding.certified ~= true or binding.release_pending == true then
            return nil
        end
        if binding.manager ~= mgr or binding.root_gen ~= self._generation then return nil end
        if binding.entry ~= entry or binding.entry_panel ~= entry_panel
            or binding.radial ~= radial or binding.parent ~= parent then
            return nil
        end
        local E = kyohud.hud.equipment
        if not E then return nil end
        if binding.terminal == true then
            if binding.source_kind ~= KINGPIN_LOCAL_SOURCE then return nil end
            local proof_ok, proved = pcall(self._terminal_proof, self, binding)
            if not proof_ok or proved ~= true then return nil end
            return binding.leaves
        end
        local src_ok, source = pcall(E.get_local_ability_activity_source, E)
        if not src_ok or type(source) ~= "table" or source.active ~= true
            or source.event_id ~= binding.source_event_id
            or source.kind ~= binding.source_kind then
            return nil
        end
        local verify_ok, verified = pcall(E._verify_local_ability_activity, E, source)
        if not verify_ok or verified ~= true then return nil end
        local leaves = binding.leaves
        if type(leaves) ~= "table" or #leaves ~= 2 then return nil end
        local ms, meter = safe_call(parent, "child", "ability_meter")
        local is, icon = safe_call(parent, "child", "ability_icon")
        if ms ~= CALL_OK or is ~= CALL_OK or not meter or not icon
            or not panel_alive(meter) or not panel_alive(icon)
            or meter ~= leaves[1] or icon ~= leaves[2] then
            return nil
        end
        local chs, children = safe_call(parent, "children")
        if chs ~= CALL_OK or type(children) ~= "table" then return nil end
        local count = 0
        local seen = {}
        for _, child in pairs(children) do
            count = count + 1
            if count > 2 then return nil end
            if child ~= meter and child ~= icon then return nil end
            if seen[child] then return nil end
            seen[child] = true
        end
        if count ~= 2 then return nil end
        local parent_visible = _effective_visible(parent, reads)
        local parent_alpha = _effective_alpha(parent, reads)
        if parent_visible ~= true or parent_alpha == nil or parent_alpha <= 0 then
            return nil
        end
        local parent_bounds = _bounds_in_common(parent, common_parent, reads)
        if not parent_bounds or parent_bounds.w <= 0 or parent_bounds.h <= 0 then
            return nil
        end
        for i = 1, 2 do
            local leaf = leaves[i]
            local lp, leaf_parent = _pass_read(reads, leaf, "parent")
            local lv, leaf_visible = _pass_read(reads, leaf, "visible")
            if lp ~= CALL_OK or leaf_parent ~= parent then return nil end
            if lv ~= CALL_OK or leaf_visible ~= false then return nil end
            if self:_h5_group_holds_visible(H5_HACKER_ACTIVE_GROUP, leaf) ~= true then
                return nil
            end
            local leaf_bounds = _bounds_in_common(leaf, common_parent, reads)
            if not leaf_bounds or leaf_bounds.w <= 0 or leaf_bounds.h <= 0 then
                return nil
            end
            local leaf_alpha = _effective_alpha(leaf, reads)
            if leaf_alpha == nil or leaf_alpha <= 0 then return nil end
        end
        local cs, color = safe_call(meter, "color")
        if cs ~= CALL_OK or color == nil then return nil end
        local color_ok, r, g, b, a = pcall(function()
            return color.r, color.g, color.b, color.a
        end)
        if not color_ok then return nil end
        if not finite(r) or r < 0 or r > 1 then return nil end
        if not finite(g) or not finite(b) or not finite(a) then return nil end
        return leaves
    end
    local function check_leaf(leaf_panel, leaf_path)
        if not leaf_panel or not panel_alive(leaf_panel) then return end
        if S.hide_crew and S.hide_local then return end
        local ev = _effective_visible(leaf_panel, reads)
        if ev == false then return end
        local ea = _effective_alpha(leaf_panel, reads)
        if ea == 0 then return end
        if ev == nil or ea == nil then
            S.hide_crew = true
            set_hide_local(ev == nil and "unknown_visibility" or "unknown_alpha",
                leaf_path, nil, nil, ev, ea)
            return
        end
        local nb = _bounds_in_common(leaf_panel, common_parent, reads)
        if not nb then
            S.hide_crew = true
            set_hide_local("unknown_geometry", leaf_path, nil, nil, ev, ea)
            return
        end
        if S.any_crew and not S.hide_crew then
            if not S._cb then
                S._cb = _bounds_in_common(crew_root, common_parent, reads)
            end
            if not S._cb then
                S.hide_crew = true
            elseif _aabb_overlap(nb, S._cb) then
                S.hide_crew = true
            end
        end
        if S.any_local and not S.hide_local then
            if player_root and panel_alive(player_root) then
                if not S._pb then
                    S._pb = _player_visible_union(player, reads)
                end
                if not S._pb then
                    set_hide_local("unknown_player_union", leaf_path, nb, nil, ev, ea)
                elseif _aabb_overlap(nb, S._pb) then
                    set_hide_local("overlap_player_union", leaf_path, nb, S._pb, ev, ea)
                end
            end
            if not S.hide_local and weapons_root and panel_alive(weapons_root) then
                if not S._wb then
                    S._wb = _bounds_in_common(weapons_root, common_parent, reads)
                end
                if not S._wb then
                    set_hide_local("unknown_weapons_bounds", leaf_path, nb, nil, ev, ea)
                elseif _aabb_overlap(nb, S._wb) then
                    set_hide_local("overlap_weapons", leaf_path, nb, S._wb, ev, ea)
                end
            end
            if not S.hide_local and equipment_root and panel_alive(equipment_root) then
                if not S._eb then
                    S._eb = _bounds_in_common(equipment_root, common_parent, reads)
                end
                if not S._eb then
                    set_hide_local("unknown_equipment_bounds", leaf_path, nb, nil, ev, ea)
                elseif _aabb_overlap(nb, S._eb) then
                    set_hide_local("overlap_equipment", leaf_path, nb, S._eb, ev, ea)
                end
            end
        end
    end
    local function inspect_teammate_entry(entry, slot, prefix)
        if type(entry) ~= "table" then return end
        local function path_of(rel)
            if not collect or S._priority_first ~= nil then return nil end
            if prefix == nil then return nil end
            return prefix .. "/" .. rel
        end
        local entry_panel = entry._panel
        if entry_panel and panel_alive(entry_panel) then
            local pp_path = path_of("player")
            local pp = known_child(entry_panel, "player", nil, pp_path)
            if pp and panel_alive(pp) then
                -- Transient utility leaves (carry/interact) no longer yield the
                -- owned block: they are centred on the radial health panel and
                -- their AABB overlap with the bottom block is a false positive;
                -- the radial health-effect leaves below still yield.
                local radial_path = path_of("player/radial_health_panel")
                local radial = known_child(pp, "radial_health_panel", nil, radial_path)
                if radial and panel_alive(radial) then
                    -- radial_custom (dodge indicator) no longer yields the owned
                    -- block: it is transient per-deck info our HUD does not
                    -- replace, and its AABB overlap is a false positive.
                    local ra_path = path_of("player/radial_health_panel/radial_ability")
                    local ra = known_child(radial, "radial_ability", nil, ra_path)
                    if ra and panel_alive(ra) then
                        local replaced = local_hacker_replaced_leaves(entry, entry_panel, radial, ra)
                        if replaced then
                            for i, leaf in ipairs(replaced) do
                                local leaf_path
                                if collect and S._priority_first == nil then
                                    leaf_path = "player/radial_health_panel/radial_ability/"
                                        .. (i == 1 and "ability_meter" or "ability_icon")
                                end
                                check_leaf(leaf, leaf_path)
                            end
                        else
                            local active_binding = self._hacker_active_binding
                            if active_binding and active_binding.manager == mgr
                                and active_binding.entry == entry
                                and active_binding.entry_panel == entry_panel then
                                self:_release_hacker_active(true)
                            end
                            check_leaf(ra, ra_path)
                        end
                    end
                    local rr_path = path_of("player/radial_health_panel/radial_rip")
                    local rr = known_child(radial, "radial_rip", nil, rr_path)
                    if rr and panel_alive(rr) then check_leaf(rr, rr_path) end
                    local rrb_path = path_of("player/radial_health_panel/radial_rip_bg")
                    local rrb = known_child(radial, "radial_rip_bg", nil, rrb_path)
                    if rrb and panel_alive(rrb) then check_leaf(rrb, rrb_path) end
                    local ras_path = path_of("player/radial_health_panel/radial_absorb_shield_active")
                    local ras = known_child(radial, "radial_absorb_shield_active", nil, ras_path)
                    if ras and panel_alive(ras) then check_leaf(ras, ras_path) end
                    local rah_path = path_of("player/radial_health_panel/radial_absorb_health_active")
                    local rah = known_child(radial, "radial_absorb_health_active", nil, rah_path)
                    if rah and panel_alive(rah) then check_leaf(rah, rah_path) end
                    local rim_path = path_of("player/radial_health_panel/radial_info_meter")
                    local rim = known_child(radial, "radial_info_meter", nil, rim_path)
                    if rim and panel_alive(rim) then check_leaf(rim, rim_path) end
                    local rimbg_path = path_of("player/radial_health_panel/radial_info_meter_bg")
                    local rimbg = known_child(radial, "radial_info_meter_bg", nil, rimbg_path)
                    if rimbg and panel_alive(rimbg) then check_leaf(rimbg, rimbg_path) end
                    local rdd_path = path_of("player/radial_health_panel/radial_delayed_damage")
                    local rdd = known_child(radial, "radial_delayed_damage", nil, rdd_path)
                    if rdd and panel_alive(rdd) then
                        local rdda_path = path_of("player/radial_health_panel/radial_delayed_damage/radial_delayed_damage_armor")
                        local rdda = known_child(rdd, "radial_delayed_damage_armor", nil, rdda_path)
                        if rdda and panel_alive(rdda) then check_leaf(rdda, rdda_path) end
                        local rddh_path = path_of("player/radial_health_panel/radial_delayed_damage/radial_delayed_damage_health")
                        local rddh = known_child(rdd, "radial_delayed_damage_health", nil, rddh_path)
                        if rddh and panel_alive(rddh) then check_leaf(rddh, rddh_path) end
                    end
                    local copr_path = path_of("player/radial_health_panel/copr_overlay_panel")
                    local copr = known_child(radial, "copr_overlay_panel", nil, copr_path)
                    if copr and panel_alive(copr) then
                        -- copr_overlay_panel is created visible while empty and the
                        -- native creates/destroys its numeric "0" child: never serve
                        -- this population from the binding index, re-consult the parent.
                        local c0_path = path_of("player/radial_health_panel/copr_overlay_panel/0")
                        local c0 = known_child(copr, "0", true, c0_path)
                        if c0 and panel_alive(c0) then
                            local replaced = local_copr_replaced_leaves(entry_panel, radial)
                            if not replaced then
                                replaced = crew_copr_replaced_leaves(
                                    entry_panel, radial, copr, slot)
                            end
                            if replaced then
                                -- Observe each replaced notch instead of the now-empty
                                -- dedicated parent, which stays natively visible.
                                for i, leaf in ipairs(replaced) do
                                    local leaf_path
                                    if collect and S._priority_first == nil then
                                        leaf_path = "player/radial_health_panel/copr_overlay_panel/"
                                            .. tostring(i - 1)
                                    end
                                    check_leaf(leaf, leaf_path)
                                end
                            else
                                check_leaf(copr, copr_path)
                            end
                        end
                    end
                end
            end
            -- Transient utility leaf (condition_timer) no longer yields the owned
            -- block: it is centred on the radial health panel and its AABB
            -- overlap with the bottom block is a false positive; the radial
            -- health-effect leaves still yield.
        end
        -- Transient utility leaves (special equipment) no longer yield the owned
        -- block: they are centred on the radial health panel and their AABB
        -- overlap with the bottom block is a false positive; the radial
        -- health-effect leaves still yield.
    end
    local teammate_panels = mgr._teammate_panels
    if type(teammate_panels) == "table" then
        for i = 1, 4 do
            active_slot = i
            local prefix = collect and ("teammate_panels[" .. i .. "]") or nil
            inspect_teammate_entry(teammate_panels[i], i, prefix)
        end
        active_slot = nil
    end
    -- Transient utility leaves (_hud_temp: bag_panel/throw_instruction) no longer
    -- yield the owned block: they are centred on the radial health panel and
    -- their AABB overlap with the bottom block is a false positive; the radial
    -- health-effect leaves still yield.
    local hud_interaction = mgr._hud_interaction
    if type(hud_interaction) == "table" then
        local ip = hud_interaction._hud_panel
        if ip and panel_alive(ip) then
            local inames = { hud_interaction._child_name_text, hud_interaction._child_ivalid_name_text }
            for _, cn in ipairs(inames) do
                if type(cn) == "string" then
                    local child_path
                    if collect and S._priority_first == nil then
                        child_path = "_hud_interaction/_hud_panel/" .. cn
                    end
                    local child = known_child(ip, cn, nil, child_path)
                    if child and panel_alive(child) then
                        check_leaf(child, child_path)
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
    local kingpin_probe = self._residual_probe
    if kingpin_probe and kingpin_probe.mode == "kingpin"
        and kingpin_probe.active == true and not kingpin_probe.done then
        if S.hide_local then
            if kingpin_probe._kingpin_hide_latch ~= true then
                kingpin_probe._kingpin_hide_latch = true
                pcall(self._kingpin_transition, self, "priority_hide")
            end
        else
            kingpin_probe._kingpin_hide_latch = nil
        end
    end
    if trace then
        if S.hide_local then
            if self._priority_trace_episode ~= true then
                self._priority_trace_episode = true
                if S._priority_first ~= nil then
                    self:_priority_trace_record(S._priority_first, t)
                end
            end
        elseif not post_release then
            self._priority_trace_episode = false
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
local H5_COOLDOWN_GROUP = "local_p_cooldown"
local H5_DAMAGE_GROUP = "local_p_damage"
local H5_FLASH_GROUP = "local_p_grenade_flash"
local H5_VISIBLE_GROUPS = {
    local_p_cooldown = true,
    local_p_damage = true,
    local_p_grenade_flash = true,
    local_p_hacker_active = true,
}
local DAMAGE_FEEDBACK_ROOT_NAME = "kyohud_damage_feedback"
local DAMAGE_FEEDBACK_EDGE_NAMES = {
    "kyohud_damage_feedback_top",
    "kyohud_damage_feedback_bottom",
    "kyohud_damage_feedback_left",
    "kyohud_damage_feedback_right",
}
local DAMAGE_FEEDBACK_ROOT_LAYER = 40
local DAMAGE_FEEDBACK_EDGE_LAYER = 41
local DAMAGE_FEEDBACK_ALPHA_FACTOR = 0.65
local DAMAGE_FEEDBACK_THICKNESS = 2
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

local function h5_child_verified(parent, name)
    local child = h5_child(parent, name)
    if not child then return nil end
    local status, immediate = safe_call(child, "parent")
    if status ~= CALL_OK or immediate ~= parent then return nil end
    return child
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

local function h5_collect_player_targets(entry_panel, P, rt)
    local targets = {}
    if not entry_panel or not panel_alive(entry_panel) then return targets end
    local label, label_text, id_evidence = nil, nil, nil
    local identity_ok = false
    -- The owned identity certification is stable between source mutations. Its
    -- key is rebuilt every update from fresh reads: the entry leaf text/color
    -- (one each), the owned root width and label primitive, plus the held local
    -- group state. A dead or reparented label misses the cache and repairs.
    local cache = rt and rt._h5_coord_cache
    local cached = cache and cache.identity
    local source_text, root_w = nil, nil
    local r, g, b = nil, nil, nil
    local has_root = P and P._root and panel_alive(P._root)
    if has_root then
        source_text = h5_read_native_name_text(entry_panel)
        r, g, b = h5_read_native_name_color(entry_panel)
        local rws, rw = safe_call(P._root, "w")
        if rws == CALL_OK and finite(rw) and rw > 0 then root_w = rw end
    end
    local label_now = P and P._h5_id_label or nil
    local label_text_ok = false
    if cached and label_now and cached.label == label_now
        and panel_alive(label_now) then
        -- The mirror text is re-read fresh on every update: the native name
        -- leaf stays hidden while we own the identity, so an in-place text
        -- corruption of our label would otherwise survive until the next cache
        -- invalidation. Hostile reparenting of the same live label object is
        -- NOT re-read each frame to stay within the two-getter budget: it is
        -- detected at the latest on the next invalidation (release, event,
        -- structural change), and the label belongs to P._root, which KyoHUD
        -- never moves; p_root/root_gen cover replacement of the root itself.
        local text_status, text_value = safe_call(label_now, "text")
        label_text_ok = text_status == CALL_OK and text_value == cached.text
    end
    local local_group_ok = false
    if rt and rt._h5_groups then
        local state = rt._h5_groups["local_p_p"]
        local_group_ok = state ~= nil and state._release_pending ~= true
    end
    local cache_hit = false
    if cached and has_root and source_text and root_w and label_now
        and panel_alive(label_now)
        and cached.entry_panel == entry_panel
        and cached.root == P._root
        and cached.label == label_now
        and label_text_ok == true
        and cached.source_text == source_text
        and cached.root_w == root_w
        and cached.r == r and cached.g == g and cached.b == b
        and cached.local_group_ok == local_group_ok then
        -- One fresh text() read above is the only label getter on a hit: the
        -- visibility write in _sync_h5_id_label_visibility may read one more.
        cache_hit = true
        label = label_now
        label_text = cached.text
        identity_ok = cached.ok == true
    end
    if not cache_hit then
        if has_root then
            label, label_text, id_evidence = h5_ensure_local_identity(P, entry_panel)
            if label then
                identity_ok = h5_verify_local_identity(P, label, label_text, id_evidence)
            end
        end
        if rt then
            local write_cache = rt._h5_coord_cache
            if write_cache then
                -- A pass that attempted any write is never memoized: the next
                -- update must run the full verifier again before stabilizing.
                if identity_ok and id_evidence ~= nil then
                    write_cache.identity = {
                        entry_panel = entry_panel,
                        root = P._root,
                        label = label,
                        source_text = source_text,
                        root_w = root_w,
                        r = r, g = g, b = b,
                        local_group_ok = local_group_ok,
                        ok = true,
                        text = label_text,
                    }
                else
                    write_cache.identity = nil
                end
            end
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
            -- Read the live actor registry directly instead of re-snapshotting
            -- it: the player module already ran ACT:refresh/get_actor this frame
            -- and these booleans are always observed fresh, never retained.
            local ACT = kyohud.hud.actors
            local actor_reg = ACT and ACT._store and ACT._store[h5_player_slot()] or nil
            local health_valid = actor_reg ~= nil
                and actor_reg.health ~= nil and actor_reg.health.valid == true
            local armor_valid = actor_reg ~= nil
                and actor_reg.armor ~= nil and actor_reg.armor.valid == true
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
                    local fire_mode = slot_data.fire_mode
                    local mode_known = fire_mode == "single"
                        or fire_mode == "auto"
                        or fire_mode == "burst"
                        or fire_mode == "volley"
                    if mode_known then
                        for _, mode_leaf_name in ipairs({"firemode_single", "firemode_auto"}) do
                            local mode_leaf = h5_child(sel_container, mode_leaf_name)
                            if mode_leaf then
                                local ps, parent = safe_call(mode_leaf, "parent")
                                local vs = safe_call(mode_leaf, "visible")
                                if ps == CALL_OK and parent == sel_container
                                    and vs == CALL_OK then
                                    targets[#targets + 1] = mode_leaf
                                end
                            end
                        end
                    end
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

local function h5_collect_cooldown_targets(entry_panel)
    local targets = {}
    if not entry_panel or not panel_alive(entry_panel) then return targets end
    local player = h5_child_verified(entry_panel, "player")
    if not player then return targets end
    local grenades = h5_child_verified(player, "grenades_panel")
    if not grenades then return targets end
    local radial = h5_child_verified(grenades, "grenades_radial")
    if radial then targets[1] = radial end
    return targets
end

local function h5_local_peer_id()
    local status, session = safe_call(managers and managers.network or nil, "session")
    if status ~= CALL_OK or session == nil then return nil end
    local peer_status, peer = safe_call(session, "local_peer")
    if peer_status ~= CALL_OK or peer == nil then return nil end
    local id_status, peer_id = safe_call(peer, "id")
    if id_status ~= CALL_OK then return nil end
    return peer_id
end

local function h5_equipment_integrated_row_ok(E, cooldown, charges)
    if type(E.integrated_recharge_text) ~= "function" then return false end
    local expected_text = E:integrated_recharge_text(cooldown, charges)
    if type(expected_text) ~= "string" then return false end
    local remaining = cooldown.remaining
    local duration = cooldown.duration
    if not finite(remaining) or remaining <= 0 then return false end
    if not finite(duration) or duration <= 0 then return false end
    if remaining > duration then return false end
    if type(E._visible_rows) ~= "table" or E._visible_rows[4] ~= true then return false end
    local row = type(E._rows) == "table" and E._rows[4] or nil
    if not row or row._verified ~= true or not row._value or not row._root then return false end
    local root_status, row_visible = safe_call(row._root, "visible")
    if root_status ~= CALL_OK or row_visible ~= true then return false end
    local text_status, text = safe_call(row._value, "text")
    if text_status ~= CALL_OK or text ~= expected_text then return false end
    local progress = math.min(1, math.max(0, 1 - remaining / duration))
    if not finite(row._progress) or math.abs(row._progress - progress) > 0.02 then return false end
    local reveal = row._recharge_reveal
    if not reveal or not panel_alive(reveal) then return false end
    local parent_status, reveal_parent = safe_call(reveal, "parent")
    if parent_status ~= CALL_OK or reveal_parent ~= row._root then return false end
    local layer_status, layer = safe_call(reveal, "layer")
    if layer_status ~= CALL_OK or not finite(layer) or math.abs(layer - 1) > 0.01 then return false end
    local visible_status, reveal_visible = safe_call(reveal, "visible")
    if visible_status ~= CALL_OK or reveal_visible ~= true then return false end
    local row_w_status, row_w = safe_call(row._root, "w")
    local row_h_status, row_h = safe_call(row._root, "h")
    if row_w_status ~= CALL_OK or row_h_status ~= CALL_OK then return false end
    if not finite(row_w) or not finite(row_h) then return false end
    local rx_status, rx = safe_call(reveal, "x")
    local ry_status, ry = safe_call(reveal, "y")
    local rw_status, rw = safe_call(reveal, "w")
    local rh_status, rh = safe_call(reveal, "h")
    if rx_status ~= CALL_OK or ry_status ~= CALL_OK
        or rw_status ~= CALL_OK or rh_status ~= CALL_OK then return false end
    if not finite(rx) or not finite(ry) or not finite(rw) or not finite(rh) then return false end
    if math.abs(rx) > 0.05 or math.abs(ry - row_h * (1 - progress)) > 0.05 then return false end
    if math.abs(rw - row_w) > 0.05 or math.abs(rh - row_h * progress) > 0.05 then return false end
    return true
end

local function h5_equipment_cooldown_ok(E)
    if not E or type(E.verify) ~= "function" or type(E.get_snapshot) ~= "function" then return false end
    if E._player_manager ~= (managers and managers.player) then return false end
    local local_peer_id = h5_local_peer_id()
    if local_peer_id == nil or E._peer_id ~= local_peer_id then return false end
    local snap_ok, snap = pcall(E.get_snapshot, E)
    if not snap_ok or type(snap) ~= "table" then return false end
    if snap.source_known ~= true or snap.unsupported == true then return false end
    if snap.source_generation ~= E._source_generation then return false end
    local projectile = snap.projectile
    if type(projectile) ~= "table" then return false end
    if type(projectile.projectile_id) ~= "string" or projectile.projectile_id == "" then return false end
    if projectile.kind ~= "ability" and projectile.kind ~= "throwable" then return false end
    if not (projectile.charges and projectile.charges.known == true) then return false end
    local cooldown = snap.cooldown
    if type(cooldown) ~= "table" or cooldown.known ~= true or cooldown.active ~= true then return false end
    if not finite(cooldown.remaining) or cooldown.remaining <= 0 then return false end
    if cooldown.integrated == true then
        if not h5_equipment_integrated_row_ok(E, cooldown, projectile.charges) then return false end
    else
        if type(E._visible_rows) ~= "table" or E._visible_rows[5] ~= true then return false end
        local row = type(E._rows) == "table" and E._rows[5] or nil
        if not row or row._verified ~= true or not row._label or not row._root then return false end
        local root_status, row_visible = safe_call(row._root, "visible")
        if root_status ~= CALL_OK or row_visible ~= true then return false end
        local expected_text = E._texts and E._texts.cooldown or "RECHARGE"
        local text_status, text = safe_call(row._label, "text")
        if text_status ~= CALL_OK or text ~= expected_text then return false end
    end
    local verify_ok, verified = pcall(E.verify, E)
    if not verify_ok or verified ~= true then return false end
    return true
end

local function h5_equipment_grenade_flash_ok(E, mgr)
    if not E or type(E._verify_grenade_flash) ~= "function" then return false, nil end
    if E._grenade_flash_ok ~= true then return false, nil end
    local source = E._grenade_flash_source
    if type(source) ~= "table" then return false, nil end
    if source.manager ~= mgr then return false, nil end
    if type(source.targets) ~= "table" or #source.targets ~= 2 then return false, nil end
    if type(source.bases) ~= "table" or #source.bases ~= 2 then return false, nil end
    local verify_ok, verified = pcall(E._verify_grenade_flash, E)
    if not verify_ok or verified ~= true then return false, nil end
    return true, source
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

function RT:_h5_group_holds_visible(group_key, obj)
    if type(group_key) ~= "string" or obj == nil then return false end
    local state = self._h5_groups and self._h5_groups[group_key]
    if not state or state._release_pending or state.property ~= "visible" then return false end
    if type(state.targets) ~= "table" then return false end
    local target = false
    for i = 1, #state.targets do
        if state.targets[i] == obj then target = true; break end
    end
    if not target then return false end
    local nv = kyohud.hud.native_visibility
    if not nv or type(nv._entries) ~= "table" then return false end
    for _, entry in ipairs(nv._entries) do
        if entry.object == obj and entry.property == "visible"
            and entry.owner == state.owner and entry.generation == state.generation then
            return entry.old_value == true and entry.applied_value == false
        end
    end
    return false
end

local function h5_cooldown_handoff_keep(rt, E, mgr, entry_panel, e_ok, e_vis, flash_source)
    local state = rt._h5_groups and rt._h5_groups[H5_COOLDOWN_GROUP]
    if not state then return false end
    local base = nil
    if type(state.targets) == "table" and #state.targets == 1 then
        base = state.targets[1]
    end
    local function trace(reason, handoff_eligible)
        if not E or type(E._grenade_flash_trace_ready) ~= "function" then return end
        if not E:_grenade_flash_trace_ready("cooldown_handoff", reason) then return end
        local visible_text, progress_text = "unknown", "unknown"
        if base then
            local v_ok, visible = safe_call(base, "visible")
            if v_ok == CALL_OK and (visible == true or visible == false) then
                visible_text = tostring(visible)
            end
            local r_ok, progress = pcall(function() return base:color().r end)
            if r_ok and finite(progress) then
                progress_text = string.format("%.17g", progress)
            end
        end
        E:_trace_grenade_flash("cooldown_handoff", reason,
            "native_progress_r=" .. progress_text
            .. " base_visible=" .. visible_text
            .. " handoff_eligible=" .. (handoff_eligible and "true" or "false"))
    end
    local function fail(reason)
        if state._cooldown_handoff == true then
            trace(reason, false)
            state._cooldown_handoff = nil
        end
        return false
    end
    if not base then return fail("coverage_lost") end
    if e_ok ~= true or e_vis ~= true then return fail("coverage_lost") end
    if not E or E._manager ~= mgr or E._hud_manager ~= mgr then
        return fail("coverage_lost")
    end
    if type(flash_source) ~= "table" or flash_source.event_mode ~= true then
        return fail("coverage_lost")
    end
    local bases = flash_source.bases
    local targets = flash_source.targets
    if type(bases) ~= "table" or #bases ~= 2 or bases[1] ~= base
        or type(targets) ~= "table" or #targets ~= 2 then
        return fail("coverage_lost")
    end
    local cooldown_targets = h5_collect_cooldown_targets(entry_panel)
    if #cooldown_targets ~= 1 or cooldown_targets[1] ~= base then
        return fail("coverage_lost")
    end
    if state.manager ~= mgr or state.entry_panel ~= entry_panel
        or state.root_gen ~= rt._generation
        or (state.property or "alpha") ~= "visible"
        or state._release_pending then
        return fail("coverage_lost")
    end
    local visible_ok, visible = safe_call(base, "visible")
    if visible_ok ~= CALL_OK or visible ~= false then
        return fail("coverage_lost")
    end
    if rt:_h5_group_holds_visible(H5_COOLDOWN_GROUP, base) ~= true then
        return fail("coverage_lost")
    end
    local color_ok, progress, green, blue, tint = pcall(function()
        local color = base:color()
        return color.r, color.g, color.b, color.a
    end)
    if color_ok ~= true or not finite(progress) then
        return fail("coverage_lost")
    end
    if progress == 0 then return fail("native_reset") end
    if progress < 0 or progress > 1
        or not finite(green) or math.abs(green - 1) > .001
        or not finite(blue) or math.abs(blue - 1) > .001
        or not finite(tint) or math.abs(tint - .5) > .001 then
        return fail("coverage_lost")
    end
    local alpha_ok, base_alpha = pcall(function() return base:alpha() end)
    if alpha_ok ~= true or not finite(base_alpha) or base_alpha <= 0 then
        return fail("coverage_lost")
    end
    local flash_state = rt._h5_groups and rt._h5_groups[H5_FLASH_GROUP]
    if not flash_state or flash_state._release_pending
        or (flash_state.property or "alpha") ~= "visible"
        or not h5_same_targets(flash_state.targets, targets) then
        return fail("coverage_lost")
    end
    for i = 1, 2 do
        local ghost = targets[i]
        if not panel_alive(ghost) then return fail("coverage_lost") end
        local ghost_ok, ghost_visible = safe_call(ghost, "visible")
        if ghost_ok ~= CALL_OK or ghost_visible ~= false then
            return fail("coverage_lost")
        end
        if rt:_h5_group_holds_visible(H5_FLASH_GROUP, ghost) ~= true then
            return fail("coverage_lost")
        end
    end
    local verify_ok, verified = pcall(E.verify, E)
    if verify_ok ~= true or verified ~= true then return fail("coverage_lost") end
    local flash_verify_ok, flash_verified = pcall(E._verify_grenade_flash, E)
    if flash_verify_ok ~= true or flash_verified ~= true then
        return fail("coverage_lost")
    end
    local snap_ok, snap = pcall(E.get_snapshot, E)
    if snap_ok ~= true or type(snap) ~= "table" or snap.source_known ~= true
        or snap.unsupported == true then
        return fail("coverage_lost")
    end
    local cooldown = snap.cooldown
    if type(cooldown) ~= "table" or cooldown.known ~= true
        or cooldown.active == true then
        return fail("coverage_lost")
    end
    local event = E._grenade_flash_event
    if type(event) ~= "table" or event.invalid == true
        or event.expired == true then
        return fail("coverage_lost")
    end
    local fresh_ok, fresh = pcall(E._read_grenade_flash_event_source, E, snap)
    if fresh_ok ~= true or type(fresh) ~= "table" or fresh.event_mode ~= true
        or type(fresh.bases) ~= "table" or fresh.bases[1] ~= base
        or not h5_same_targets(fresh.targets, targets) then
        return fail("coverage_lost")
    end
    state._cooldown_handoff = true
    trace("held", true)
    return true
end

local function h5_flash_bounds(panel)
    local xs, x = safe_call(panel, "x")
    local ys, y = safe_call(panel, "y")
    local ws, w = safe_call(panel, "w")
    local hs, h = safe_call(panel, "h")
    if xs ~= CALL_OK or ys ~= CALL_OK or ws ~= CALL_OK or hs ~= CALL_OK then return nil end
    if not finite(x) or not finite(y) or not finite(w) or not finite(h) then return nil end
    return x, y, w, h
end

local function h5_flash_trace_bool(value)
    if value == true then return "true" end
    if value == false then return "false" end
    return "unknown"
end

local function h5_flash_lease_detail(rt, group_gen, targets, visible, held, failure, E,
    owned_root_visible, owned_flash_ok, fallback_phase)
    local detail = "groupgen="
        .. (finite(group_gen) and string.format("%.17g", group_gen) or "unknown")
        .. " failure=" .. tostring(failure or "none")
    for i = 1, 2 do
        local ghost = type(targets) == "table" and targets[i] or nil
        local vis = visible and visible[i]
        local hold = held and held[i]
        local vis_from = vis == nil and fallback_phase or "acquisition_readback"
        local held_from = hold == nil and fallback_phase or "acquisition_readback"
        if ghost ~= nil and vis == nil then
            local vs, actual = safe_call(ghost, "visible")
            if vs == CALL_OK and (actual == true or actual == false) then
                vis = actual
            end
        end
        if ghost ~= nil and hold == nil then
            local vs, actual = safe_call(ghost, "visible")
            if vs == CALL_OK and actual == false then
                local ok_held, value = pcall(rt._h5_group_holds_visible, rt,
                    H5_FLASH_GROUP, ghost)
                hold = ok_held and value == true
            else
                hold = false
            end
        end
        detail = detail .. " ghost" .. i .. "_visible=" .. h5_flash_trace_bool(vis)
            .. " ghost" .. i .. "_visible_observation=" .. tostring(vis_from)
            .. " ghost" .. i .. "_held=" .. h5_flash_trace_bool(hold)
            .. " ghost" .. i .. "_held_observation=" .. tostring(held_from)
    end
    if E then
        local owned_value = owned_flash_ok
        if owned_value == nil then owned_value = E._grenade_flash_ok end
        detail = detail .. " owned_ok=" .. h5_flash_trace_bool(owned_value)
            .. " owned_root_visible=" .. h5_flash_trace_bool(owned_root_visible)
            .. " owned_source=" .. tostring(type(E._grenade_flash_source) == "table")
        local row = type(E._rows) == "table" and E._rows[4] or nil
        if row then
            detail = detail .. " flash_active=" .. h5_flash_trace_bool(row._flash_active)
        end
    end
    return detail
end

-- Terminal completion is only recognized when both exact leased ghosts are
-- alpha 0 at the baseline geometry and native has written visible=false. This
-- rewrites only this group's held restore intent before release; a timeout or a
-- bare lease value never qualifies.
local function h5_flash_terminal(state)
    local source = state and state.flash_source
    if type(source) ~= "table" then return false end
    local parent = source.parent
    local targets = state.targets
    local bases = source.bases
    local ghost_names = source.ghost_names
    local base_names = source.base_names
    if not panel_alive(parent) or type(targets) ~= "table" or #targets ~= 2
        or type(bases) ~= "table" or #bases ~= 2
        or type(ghost_names) ~= "table" or #ghost_names ~= 2
        or type(base_names) ~= "table" or #base_names ~= 2 then return false end
    for i = 1, 2 do
        local ghost = targets[i]
        local base = bases[i]
        if not panel_alive(ghost) or not panel_alive(base) then return false end
        local gps, ghost_parent = safe_call(ghost, "parent")
        local bps, base_parent = safe_call(base, "parent")
        if gps ~= CALL_OK or ghost_parent ~= parent
            or bps ~= CALL_OK or base_parent ~= parent then return false end
        local gcs, ghost_child = safe_call(parent, "child", ghost_names[i])
        local bcs, base_child = safe_call(parent, "child", base_names[i])
        if gcs ~= CALL_OK or ghost_child ~= ghost
            or bcs ~= CALL_OK or base_child ~= base then return false end
        local vs, visible = safe_call(ghost, "visible")
        local as, alpha = safe_call(ghost, "alpha")
        if vs ~= CALL_OK or visible ~= false
            or as ~= CALL_OK or not finite(alpha) then
            return false
        end
        local cs, color = safe_call(ghost, "color")
        if cs ~= CALL_OK or color == nil then return false end
        if not finite(color.r) or math.abs(color.r - 1) > 0.001
            or not finite(color.g) or math.abs(color.g - 1) > 0.001
            or not finite(color.b) or math.abs(color.b - 1) > 0.001 then
            return false
        end
        if not finite(color.a) or math.abs(color.a) > 0.0001 then return false end
        local gx, gy, gw, gh = h5_flash_bounds(ghost)
        local bx, by, bw, bh = h5_flash_bounds(base)
        if gx == nil or bx == nil then return false end
        if math.abs(gx - bx) > 0.05 or math.abs(gy - by) > 0.05
            or math.abs(gw - bw) > 0.05 or math.abs(gh - bh) > 0.05 then
            return false
        end
    end
    return true
end

local function h5_reconcile_flash_terminal(state)
    if not state or state.property ~= "visible" then return end
    if not h5_flash_terminal(state) then return end
    local nv = kyohud.hud.native_visibility
    if not nv or type(nv._entries) ~= "table" then return end
    for _, entry in ipairs(nv._entries) do
        if entry.owner == state.owner and entry.generation == state.generation
            and entry.property == "visible" and entry.old_value == true then
            for i = 1, #state.targets do
                if entry.object == state.targets[i] then
                    entry.old_value = false
                    break
                end
            end
        end
    end
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
    -- Any real release (or failed acquisition, which funnels here) invalidates
    -- the coordination memo so the next pass re-collects fresh targets instead
    -- of reusing a cached leaf set that may contain a dead primitive.
    self._h5_coord_cache = nil
    if group_key == H5_FLASH_GROUP then h5_reconcile_flash_terminal(state) end
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
            local allowed = nv._whitelist[leaf]
            if allowed then
                local property = previous.property
                if property == nil then
                    property = "alpha"
                    allowed[property] = previous.alpha
                else
                    allowed[property] = previous.allowed
                end
                if not next(allowed) then
                    nv._whitelist[leaf] = nil
                end
            end
        end
    end
    self._h5_groups[group_key] = nil
    if group_key == H5_HACKER_ACTIVE_GROUP then
        self._hacker_active_binding = nil
    end
    return true
end

function RT:_h5_acquire_group(group_key, targets, source_id, property)
    property = property or "alpha"
    if property ~= "alpha" and property ~= "visible" then return end
    if property == "visible" and H5_VISIBLE_GROUPS[group_key] ~= true then return end
    local value = 0
    if property == "visible" then
        value = false
    end
    if not targets or #targets == 0 then return end
    local nv = kyohud.hud.native_visibility
    if not nv or type(nv.acquire) ~= "function" then return end
    local old = self._h5_groups and self._h5_groups[group_key]
    if old then
        local same_source = h5_same_targets(old.targets, targets)
            and old.entry_panel == source_id.entry_panel
            and old.manager == source_id.manager
            and old.root_gen == source_id.root_gen
            and (old.property or "alpha") == property
        if same_source then
            if group_key == H5_FLASH_GROUP then old.flash_source = source_id end
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
            local allowed = nv._whitelist[leaf]
            if not allowed then allowed = {}; nv._whitelist[leaf] = allowed end
            if allowed[property] ~= true then
                added[leaf] = {property = property, allowed = allowed[property]}
                allowed[property] = true
            end
        end
        requests[i] = {id = leaf, property = property, value = value}
    end
    local state = {
        owner = owner,
        generation = new_gen,
        targets = targets,
        entry_panel = source_id.entry_panel,
        manager = source_id.manager,
        root_gen = source_id.root_gen,
        property = property,
        added = added,
        requests = requests,
        flash_source = group_key == H5_FLASH_GROUP and source_id or nil,
    }
    self._h5_groups[group_key] = state
    local ok = nv:acquire(owner, new_gen, requests)
    if ok then
        return
    end
    self:_h5_release_group(group_key)
end

-- Opt-in residual phase probe: time the real native H5 group acquisition only.
-- The wrapper is reinstalled after each fresh definition and never wraps twice.
if RT._h5_acquire_group ~= RT._residual_h5_acquire_wrapper then
    local raw_acquire_group = RT._h5_acquire_group
    local function h5_acquire_phase(group_key)
        if type(group_key) ~= "string" then return nil end
        if group_key:sub(1, 6) == "local_" then return "player_native_acquire" end
        if group_key:sub(1, 5) == "crew_" then return "crew_native_acquire" end
        return nil
    end
    local wrapped = function(self, group_key, targets, source_id, property)
        local probe = self._residual_probe
        if not probe or probe.done or not probe.active then
            raw_acquire_group(self, group_key, targets, source_id, property)
            return
        end
        local phase = h5_acquire_phase(group_key)
        local start
        if phase ~= nil and type(self._residual_stamp) == "function" then
            start = self:_residual_stamp()
        end
        raw_acquire_group(self, group_key, targets, source_id, property)
        if phase ~= nil and start ~= nil and type(self._residual_record) == "function" then
            self:_residual_record(phase, start)
        end
    end
    RT._residual_h5_acquire_wrapper = wrapped
    RT._h5_acquire_group = wrapped
end

local function df_bounds(prim)
    if not prim or not panel_alive(prim) then return nil end
    local xs, x = safe_call(prim, "x")
    local ys, y = safe_call(prim, "y")
    local ws, w = safe_call(prim, "w")
    local hs, h = safe_call(prim, "h")
    if xs ~= CALL_OK or ys ~= CALL_OK or ws ~= CALL_OK or hs ~= CALL_OK then return nil end
    if not finite(x) or not finite(y) or not finite(w) or not finite(h) then return nil end
    return {x = x, y = y, w = w, h = h}
end

local function df_shape_matches(prim, x, y, w, h)
    local b = df_bounds(prim)
    if not b then return false end
    return math.abs(b.x - x) <= 0.51 and math.abs(b.y - y) <= 0.51
        and math.abs(b.w - w) <= 0.51 and math.abs(b.h - h) <= 0.51
end

local function df_edge_ok(root, edge, name, sx, sy, sw, sh, expected_alpha)
    if not edge or not panel_alive(edge) then return false end
    local ps, parent = safe_call(edge, "parent")
    if ps ~= CALL_OK or parent ~= root then return false end
    local cs, child = safe_call(root, "child", name)
    if cs ~= CALL_OK or child ~= edge then return false end
    if not df_shape_matches(edge, sx, sy, sw, sh) then return false end
    local ls, layer = safe_call(edge, "layer")
    if ls ~= CALL_OK or not finite(layer)
        or math.abs(layer - DAMAGE_FEEDBACK_EDGE_LAYER) > 0.01 then return false end
    local vs, visible = safe_call(edge, "visible")
    if vs ~= CALL_OK or visible ~= true then return false end
    local ks, color = safe_call(edge, "color")
    if ks ~= CALL_OK or color == nil then return false end
    if not finite(color.r) or math.abs(color.r - 1) > 0.001 then return false end
    if not finite(color.g) or math.abs(color.g) > 0.001 then return false end
    if not finite(color.b) or math.abs(color.b) > 0.001 then return false end
    local as, alpha = safe_call(edge, "alpha")
    if as ~= CALL_OK or not finite(alpha)
        or math.abs(alpha - expected_alpha) > 0.001 then return false end
    return true
end

local function df_root_ok(P, root, x, y, w, h, expected_alpha)
    if not root or not panel_alive(root) then return false end
    local ps, parent = safe_call(root, "parent")
    if ps ~= CALL_OK or parent ~= P._root then return false end
    local cs, child = safe_call(P._root, "child", DAMAGE_FEEDBACK_ROOT_NAME)
    if cs ~= CALL_OK or child ~= root then return false end
    if not df_shape_matches(root, x, y, w, h) then return false end
    local ls, layer = safe_call(root, "layer")
    if ls ~= CALL_OK or not finite(layer)
        or math.abs(layer - DAMAGE_FEEDBACK_ROOT_LAYER) > 0.01 then return false end
    local vs, visible = safe_call(root, "visible")
    if vs ~= CALL_OK or visible ~= (expected_alpha > 0) then return false end
    return true
end

local function damage_feedback_hide_owned()
    local P = kyohud.hud.player
    local feedback = P and P._damage_feedback
    local root = feedback and feedback.root
    if root and panel_alive(root) then
        safe_call(root, "set_visible", false)
    end
end

function RT:_sync_damage_feedback(p_ok, p_vis, mgr, entry, handled_keys)
    local P = kyohud.hud.player
    local function release()
        damage_feedback_hide_owned()
        self:_h5_release_group(H5_DAMAGE_GROUP)
        handled_keys[H5_DAMAGE_GROUP] = true
    end
    if not P or not P._root or not panel_alive(P._root) then release(); return end
    if not (p_ok and p_vis) then release(); return end
    if type(entry) ~= "table" or entry._ai == true then release(); return end
    local panels = mgr and mgr._teammate_panels
    if type(panels) ~= "table" or panels[h5_player_slot()] ~= entry then release(); return end
    local entry_panel = entry._panel
    if not entry_panel or not panel_alive(entry_panel) then release(); return end
    local player = h5_child_verified(entry_panel, "player")
    if not player then release(); return end
    local radial = h5_child_verified(player, "radial_health_panel")
    if not radial then release(); return end
    local indicator = h5_child_verified(radial, "damage_indicator")
    if not indicator then release(); return end
    local reads = {}
    if _effective_visible(entry_panel, reads) ~= true
        or _effective_visible(player, reads) ~= true
        or _effective_visible(radial, reads) ~= true then release(); return end
    local entry_alpha = _effective_alpha(entry_panel, reads)
    local player_alpha = _effective_alpha(player, reads)
    local radial_alpha = _effective_alpha(radial, reads)
    if not finite(entry_alpha) or entry_alpha <= 0
        or not finite(player_alpha) or player_alpha <= 0
        or not finite(radial_alpha) or radial_alpha <= 0 then release(); return end
    local als, native_alpha = safe_call(indicator, "alpha")
    if als ~= CALL_OK or not finite(native_alpha)
        or native_alpha < 0 or native_alpha > 1 then release(); return end
    if type(P.verify) ~= "function" then release(); return end
    local verify_ok, verified = pcall(P.verify, P)
    if not verify_ok or verified ~= true then release(); return end
    local gauge = P._gauge
    local gauge_root = gauge and gauge.root
    local gps, gauge_parent = safe_call(gauge_root, "parent")
    if gps ~= CALL_OK or gauge_parent ~= P._root then release(); return end
    local gauge_bounds = df_bounds(gauge_root)
    if not gauge_bounds or gauge_bounds.w <= 0 or gauge_bounds.h <= 0 then release(); return end
    local armor_bg = gauge._armor_bg
    if not armor_bg or not panel_alive(armor_bg) then release(); return end
    local aps, armor_parent = safe_call(armor_bg, "parent")
    if aps ~= CALL_OK or armor_parent ~= gauge_root then release(); return end
    local armor_bounds = df_bounds(armor_bg)
    if not armor_bounds or armor_bounds.w <= 0 or armor_bounds.h <= 0 then release(); return end
    local bounds = {
        x = gauge_bounds.x + armor_bounds.x,
        y = gauge_bounds.y + armor_bounds.y,
        w = armor_bounds.w,
        h = armor_bounds.h,
    }
    local rws, root_w = safe_call(P._root, "w")
    if rws ~= CALL_OK or not finite(root_w) or root_w <= 0 then release(); return end
    local thickness = DAMAGE_FEEDBACK_THICKNESS * root_w / 380
    if thickness <= 0 or thickness > bounds.w or thickness > bounds.h then release(); return end
    local shapes = {
        {0, 0, bounds.w, thickness},
        {0, bounds.h - thickness, bounds.w, thickness},
        {0, 0, thickness, bounds.h},
        {bounds.w - thickness, 0, thickness, bounds.h},
    }
    local expected_alpha = native_alpha * DAMAGE_FEEDBACK_ALPHA_FACTOR
    local feedback = P._damage_feedback
    local root = feedback and feedback.root
    local edges = feedback and feedback.edges
    local reusable = false
    if root and type(edges) == "table" and #edges == 4 and panel_alive(root) then
        local rp_s, rp = safe_call(root, "parent")
        local rc_s, rc = safe_call(P._root, "child", DAMAGE_FEEDBACK_ROOT_NAME)
        if rp_s == CALL_OK and rp == P._root and rc_s == CALL_OK and rc == root then
            reusable = true
            for i = 1, 4 do
                local edge = edges[i]
                if not edge or not panel_alive(edge) then reusable = false; break end
                local ep_s, ep = safe_call(edge, "parent")
                local ec_s, ec = safe_call(root, "child", DAMAGE_FEEDBACK_EDGE_NAMES[i])
                if ep_s ~= CALL_OK or ep ~= root
                    or ec_s ~= CALL_OK or ec ~= edge then
                    reusable = false
                    break
                end
            end
        end
    end
    if not reusable then
        local existing_s, existing = safe_call(P._root, "child", DAMAGE_FEEDBACK_ROOT_NAME)
        if existing_s ~= CALL_OK or existing ~= nil then release(); return end
        if feedback and feedback.root and panel_alive(feedback.root) then
            safe_call(feedback.root, "set_visible", false)
        end
        P._damage_feedback = nil
        local build_ok, built = pcall(function()
            local new_root = P._root:panel({
                name = DAMAGE_FEEDBACK_ROOT_NAME,
                layer = DAMAGE_FEEDBACK_ROOT_LAYER,
            })
            new_root:set_shape(bounds.x, bounds.y, bounds.w, bounds.h)
            new_root:set_layer(DAMAGE_FEEDBACK_ROOT_LAYER)
            new_root:set_visible(false)
            local new_edges = {}
            for i = 1, 4 do
                local shape = shapes[i]
                local edge = new_root:rect({
                    name = DAMAGE_FEEDBACK_EDGE_NAMES[i],
                    layer = DAMAGE_FEEDBACK_EDGE_LAYER,
                })
                edge:set_shape(shape[1], shape[2], shape[3], shape[4])
                edge:set_color(Color(1, 1, 0, 0))
                edge:set_alpha(0)
                edge:set_visible(true)
                new_edges[i] = edge
            end
            return {root = new_root, edges = new_edges}
        end)
        if not build_ok or type(built) ~= "table" or not built.root
            or type(built.edges) ~= "table" or #built.edges ~= 4 then
            if type(built) == "table" and built.root and panel_alive(built.root) then
                safe_call(built.root, "set_visible", false)
            end
            release()
            return
        end
        local check_s, check = safe_call(P._root, "child", DAMAGE_FEEDBACK_ROOT_NAME)
        if check_s ~= CALL_OK or check ~= built.root then
            safe_call(built.root, "set_visible", false)
            release()
            return
        end
        P._damage_feedback = built
        feedback = built
        root = built.root
        edges = built.edges
    end
    safe_call(root, "set_shape", bounds.x, bounds.y, bounds.w, bounds.h)
    safe_call(root, "set_layer", DAMAGE_FEEDBACK_ROOT_LAYER)
    safe_call(root, "set_visible", expected_alpha > 0)
    for i = 1, 4 do
        local shape = shapes[i]
        local edge = edges[i]
        safe_call(edge, "set_shape", shape[1], shape[2], shape[3], shape[4])
        safe_call(edge, "set_layer", DAMAGE_FEEDBACK_EDGE_LAYER)
        safe_call(edge, "set_alpha", expected_alpha)
        safe_call(edge, "set_visible", true)
    end
    local certified = df_root_ok(P, root, bounds.x, bounds.y, bounds.w, bounds.h, expected_alpha)
    if certified then
        for i = 1, 4 do
            local shape = shapes[i]
            if not df_edge_ok(root, edges[i], DAMAGE_FEEDBACK_EDGE_NAMES[i],
                shape[1], shape[2], shape[3], shape[4], expected_alpha) then
                certified = false
                break
            end
        end
    end
    if not certified then
        safe_call(root, "set_visible", false)
        self:_h5_release_group(H5_DAMAGE_GROUP)
        handled_keys[H5_DAMAGE_GROUP] = true
        return
    end
    local targets = {indicator}
    self:_h5_acquire_group(H5_DAMAGE_GROUP, targets, {
        entry_panel = entry_panel,
        manager = mgr,
        root_gen = self._generation,
    }, "visible")
    local state = self._h5_groups and self._h5_groups[H5_DAMAGE_GROUP]
    if not state or state._release_pending or not h5_same_targets(state.targets, targets) then
        safe_call(root, "set_visible", false)
        self:_h5_release_group(H5_DAMAGE_GROUP)
    end
    handled_keys[H5_DAMAGE_GROUP] = true
end

-- Crew coverage memo key. Rebuilt from fresh live fields on every update: the
-- roster entries, the actor registry generations and the publication records
-- that write_crew_native_coverage consumes. Equal signatures mean the cached
-- row set is still authoritative for this update.
function RT:_h5_crew_coverage_signature()
    local nil_token = self._h5_sig_nil
    if not nil_token then
        nil_token = {}
        self._h5_sig_nil = nil_token
    end
    local sig_a = self._h5_sig_a
    if not sig_a then
        sig_a = {}
        self._h5_sig_a = sig_a
    end
    local sig_b = self._h5_sig_b
    if not sig_b then
        sig_b = {}
        self._h5_sig_b = sig_b
    end
    local prev = self._h5_coord_cache and self._h5_coord_cache.crew_sig or nil
    local sig
    if prev == sig_a then
        sig = sig_b
    elseif prev == sig_b then
        sig = sig_a
    else
        local alt = not self._h5_sig_alt
        self._h5_sig_alt = alt
        sig = alt and sig_b or sig_a
    end
    local n = 0
    local function push(value)
        if value == nil then value = nil_token end
        n = n + 1
        sig[n] = value
    end
    local ACT = kyohud.hud.actors
    local C = kyohud.hud.crew
    push(ACT)
    push(C)
    push(self._manager)
    if not ACT then
        local tail = #sig
        for i = n + 1, tail do sig[i] = nil end
        return sig
    end
    push(ACT._crew_source_session)
    push(ACT._crew_source_criminals)
    push(ACT._crew_source_mgr)
    local net = managers and managers.network or nil
    local session_ok, live_session = safe_call(net, "session")
    if session_ok ~= CALL_OK then live_session = nil end
    push(live_session)
    push(managers and managers.criminals)
    push(managers and managers.hud)
    local entries = ACT._crew_entries
    local reg = ACT._store
    local player_mgr = managers and managers.player or nil
    local pm_global = nil
    if type(player_mgr) == "table" or type(player_mgr) == "userdata" then
        pm_global = player_mgr._global
    end
    -- Wholesale replacement of the live sources consumed by
    -- crew_publication_current must change this key even when the per-peer
    -- records are kept: the player manager itself and the four live registry
    -- tables it exposes. push() maps nil to the shared nil token.
    push(player_mgr)
    push(pm_global)
    push(pm_global and pm_global.synced_deployables)
    push(pm_global and pm_global.synced_cable_ties)
    push(pm_global and pm_global.synced_grenades)
    push(pm_global and pm_global.synced_ammo_info)
    for pos = 1, 3 do
        local live = entries and entries[pos]
        if not live then
            push(false)
        else
            push(true)
            push(live.occupant_token)
            push(live.slot)
            push(live.peer_id)
            push(live.ai == true)
            push(live.name ~= nil)
            push(live.position)
            push(live._identity_key)
            push(live.phase)
            push(live.health and live.health.valid == true)
            push(live.bleedout and live.bleedout.valid == true)
            local w = live.weapon
            push(w and w.selection_index)
            push(w and w.unit_id)
            local ammo = w and w.ammo
            push(ammo and ammo.current_clip)
            push(ammo and ammo.total_raw)
            push(ammo and ammo.reserve)
            local slots = live.ammo_slots
            for si = 1, 2 do
                local sa = slots and slots[si]
                push(sa and sa.current_clip)
                push(sa and sa.total_raw)
                push(sa and sa.reserve)
            end
            local eq = live.equipment
            local dep = eq and eq.deployable
            push(dep and dep.id)
            push(dep and dep.amount)
            local ties = eq and eq.cable_ties
            push(ties and ties.amount)
            local proj = eq and eq.projectile
            push(proj and proj.id)
            push(proj and proj.amount)
            push(proj and proj.kind)
            local r = reg and reg[live.slot]
            if r then
                push(r.generation)
                push(r.peer_id)
                push(r.ai == true)
                push(r.health and r.health.valid == true)
                push(r.health and r.health.provenance)
                push(r.armor and r.armor.valid == true)
                push(r.armor and r.armor.provenance)
                push(r.downs)
            else
                for _ = 1, 8 do push(false) end
            end
            if live.ai ~= true and type(live.peer_id) == "number" then
                local peer_id = live.peer_id
                local peer_ok, live_peer = safe_call(live_session, "peer", peer_id)
                if peer_ok ~= CALL_OK then live_peer = nil end
                push(live_peer)
                local published = ACT._pm_published
                for _, channel in ipairs({"deployable", "cable_ties", "grenade"}) do
                    local rec = published and published[channel] and published[channel][peer_id]
                    push(rec and rec.record)
                    push(rec and rec.registry_source)
                    push(rec and rec.session)
                    push(rec and rec.pm)
                    push(rec and rec.peer_obj)
                end
                for si = 1, 2 do
                    local rec = published and published.ammo
                        and published.ammo[peer_id * 1000 + si]
                    push(rec and rec.record)
                    push(rec and rec.registry_source)
                    push(rec and rec.session)
                    push(rec and rec.pm)
                    push(rec and rec.peer_obj)
                end
                if pm_global then
                    push(pm_global.synced_deployables and pm_global.synced_deployables[peer_id])
                    push(pm_global.synced_cable_ties and pm_global.synced_cable_ties[peer_id])
                    push(pm_global.synced_grenades and pm_global.synced_grenades[peer_id])
                    local ammo_info = pm_global.synced_ammo_info and pm_global.synced_ammo_info[peer_id]
                    push(ammo_info and ammo_info[1])
                    push(ammo_info and ammo_info[2])
                else
                    for _ = 1, 5 do push(false) end
                end
            end
        end
    end
    local tail = #sig
    for i = n + 1, tail do sig[i] = nil end
    return sig
end

function RT:_coordinate_h5_native_duplicates_unprofiled(crew_receipt)
    local probe = self._residual_probe
    local sub = probe and not probe.done and probe.active
        and type(self._residual_stamp) == "function"
        and type(self._residual_record) == "function"
    local mgr = self._manager
    if not mgr then return {} end
    if self._disabled or self._freeflight then
        self:_release_all_h5()
        return {}
    end
    local nv = kyohud.hud.native_visibility
    if not nv or type(nv.acquire) ~= "function" then
        damage_feedback_hide_owned()
        return {}
    end

    local cache_pass = self._h5_coord_cache_pass == true
    if not cache_pass then
        self._h5_coord_cache = nil
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

    -- Coordination memo: only ever reused while every structural source keeps
    -- the identity it had when the memo was taken. Real group releases (and
    -- failed acquisitions, which release) clear it unconditionally.
    local coord_cache = cache_pass and self._h5_coord_cache or nil
    if coord_cache then
        if coord_cache.manager ~= mgr
            or coord_cache.disabled ~= (self._disabled == true)
            or coord_cache.freeflight ~= (self._freeflight == true)
            or coord_cache.p_enabled ~= p_enabled
            or coord_cache.w_enabled ~= w_enabled
            or coord_cache.e_enabled ~= e_enabled
            or coord_cache.c_enabled ~= c_enabled
            or coord_cache.root_gen ~= self._generation
            or coord_cache.p_root ~= (P and P._root)
            or coord_cache.p_manager ~= (P and P._manager)
            or coord_cache.p_mounted ~= (P ~= nil and P._mounted == true)
            or coord_cache.w_root ~= (W and W._root)
            or coord_cache.w_manager ~= (W and W._manager)
            or coord_cache.w_mounted ~= (W ~= nil and W._mounted == true)
            or coord_cache.e_root ~= (E and E._root)
            or coord_cache.e_manager ~= (E and E._manager)
            or coord_cache.e_mounted ~= (E ~= nil and E._mounted == true)
            or coord_cache.c_root ~= (C and C._root)
            or coord_cache.c_manager ~= (C and C._manager)
            or coord_cache.c_mounted ~= (C ~= nil and C._mounted == true)
        then
            coord_cache = nil
            self._h5_coord_cache = nil
        end
    end
    if cache_pass and not coord_cache then
        coord_cache = {
            manager = mgr,
            disabled = self._disabled == true,
            freeflight = self._freeflight == true,
            p_enabled = p_enabled,
            w_enabled = w_enabled,
            e_enabled = e_enabled,
            c_enabled = c_enabled,
            root_gen = self._generation,
            p_root = P and P._root,
            p_manager = P and P._manager,
            p_mounted = P ~= nil and P._mounted == true,
            w_root = W and W._root,
            w_manager = W and W._manager,
            w_mounted = W ~= nil and W._mounted == true,
            e_root = E and E._root,
            e_manager = E and E._manager,
            e_mounted = E ~= nil and E._mounted == true,
            c_root = C and C._root,
            c_manager = C and C._manager,
            c_mounted = C ~= nil and C._mounted == true,
        }
        self._h5_coord_cache = coord_cache
    end

    -- Receipts belong only to this synchronous H5 -> backdrop pass. They are
    -- never retained across frames. Backdrop writes do not mutate P/W/E content.
    -- quality split approved 2026-11-10: a module that already ran in this same
    -- synchronous pass certifies with its own result. A throttled module gets a
    -- live light root read. The damage-feedback mirror separately requires the
    -- real player verifier before it leases the native indicator visibility.
    local certifications = {}
    if p_ok then
        local ok
        if P._update_ran_now == true then
            ok = P._verify_ok_now == true
        else
            ok = h5_light_root_ok(P)
        end
        certifications[P] = {root = P._root, manager = P._manager, verify = P.verify, ok = ok}
        if not ok then p_ok = false end
    end
    if w_ok then
        local ok
        if W._update_ran_now == true then
            ok = W._verify_ok_now == true
        else
            ok = h5_light_root_ok(W)
        end
        certifications[W] = {root = W._root, manager = W._manager, verify = W.verify, ok = ok}
        if not ok then w_ok = false end
    end
    if e_ok then
        local ok
        if E._update_ran_now == true then
            ok = E._verify_ok_now == true
        else
            ok = h5_light_root_ok(E)
        end
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
            local ok
            if C._update_ran_now == true then
                ok = C._verify_ok_now == true
            else
                ok = h5_light_crew_ok(C)
            end
            if not ok then c_ok = false end
        end
    end

    -- All four visibility queries precede target acquisition and any H5 writes.
    -- Share their common ancestors, never this cache with priority or acquisition.
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
    local cooldown_ok = false
    local flash_ok, flash_source = false, nil
    if e_ok and e_vis then
        cooldown_ok = h5_equipment_cooldown_ok(E)
        flash_ok, flash_source = h5_equipment_grenade_flash_ok(E, mgr)
    end

    local teammate_panels = mgr._teammate_panels
    if type(teammate_panels) ~= "table" then
        self:_release_all_h5()
        return certifications
    end

    local player_slot = h5_player_slot()
    local handled_keys = {}
    local local_entry = teammate_panels[player_slot]
    self:_sync_damage_feedback(p_ok, p_vis, mgr, local_entry, handled_keys)

    if p_ok or w_ok or e_ok then
        local entry = local_entry
        if type(entry) == "table" then
            local entry_panel = entry._panel
            if entry_panel and panel_alive(entry_panel) then
                local key = "local_p"
                if p_ok and p_vis then
                    local s0 = sub and self:_residual_stamp() or nil
                    local p_targets = h5_collect_player_targets(entry_panel, P, self)
                    if s0 then self:_residual_record("harmony_duplicates_collect", s0) end
                    if #p_targets > 0 then
                        self:_h5_acquire_group(key .. "_p", p_targets, {
                            entry_panel = entry_panel,
                            manager = mgr,
                            root_gen = self._generation,
                        })
                    else
                        self:_h5_release_group(key .. "_p")
                    end
                else
                    self:_h5_release_group(key .. "_p")
                end
                handled_keys[key .. "_p"] = true
                if w_ok and w_vis then
                    local s0 = sub and self:_residual_stamp() or nil
                    local w_targets = h5_collect_weapon_targets(entry_panel, W)
                    if s0 then self:_residual_record("harmony_duplicates_collect", s0) end
                    if #w_targets > 0 then
                        self:_h5_acquire_group(key .. "_w", w_targets, {
                            entry_panel = entry_panel,
                            manager = mgr,
                            root_gen = self._generation,
                        })
                    else
                        self:_h5_release_group(key .. "_w")
                    end
                else
                    self:_h5_release_group(key .. "_w")
                end
                handled_keys[key .. "_w"] = true
                if e_ok and e_vis then
                    local s0 = sub and self:_residual_stamp() or nil
                    local e_targets = h5_collect_equipment_targets(entry_panel, E)
                    if s0 then self:_residual_record("harmony_duplicates_collect", s0) end
                    if #e_targets > 0 then
                        self:_h5_acquire_group(key .. "_e", e_targets, {
                            entry_panel = entry_panel,
                            manager = mgr,
                            root_gen = self._generation,
                        })
                    else
                        self:_h5_release_group(key .. "_e")
                    end
                else
                    self:_h5_release_group(key .. "_e")
                end
                handled_keys[key .. "_e"] = true
                if cooldown_ok then
                    local s0 = sub and self:_residual_stamp() or nil
                    local cooldown_targets = h5_collect_cooldown_targets(entry_panel)
                    if s0 then self:_residual_record("harmony_duplicates_collect", s0) end
                    if #cooldown_targets > 0 then
                        self:_h5_acquire_group(H5_COOLDOWN_GROUP, cooldown_targets, {
                            entry_panel = entry_panel,
                            manager = mgr,
                            root_gen = self._generation,
                        }, "visible")
                        handled_keys[H5_COOLDOWN_GROUP] = true
                    else
                        self:_h5_release_group(H5_COOLDOWN_GROUP)
                    end
                else
                    handled_keys[H5_COOLDOWN_GROUP] = true
                end
                if flash_ok and flash_source then
                    local flash_targets = flash_source.targets
                    local flash_acquired = false
                    local flash_failure = nil
                    local lease_generation = nil
                    local flash_visible1, flash_visible2
                    local flash_held1, flash_held2
                    if type(flash_targets) == "table" and #flash_targets == 2 then
                        self:_h5_acquire_group(H5_FLASH_GROUP, flash_targets, {
                            entry_panel = entry_panel,
                            manager = mgr,
                            root_gen = self._generation,
                            parent = flash_source.parent,
                            bases = flash_source.bases,
                            ghost_names = flash_source.ghost_names,
                            base_names = flash_source.base_names,
                        }, "visible")
                        local state = self._h5_groups and self._h5_groups[H5_FLASH_GROUP]
                        lease_generation = state and state.generation or nil
                        if state and not state._release_pending
                            and state.property == "visible"
                            and h5_same_targets(state.targets, flash_targets) then
                            flash_acquired = true
                            for i = 1, 2 do
                                local ghost = flash_targets[i]
                                local vs, visible = safe_call(ghost, "visible")
                                local held = false
                                if vs == CALL_OK and visible == false then
                                    held = self:_h5_group_holds_visible(H5_FLASH_GROUP, ghost)
                                end
                                if vs == CALL_OK and (visible == true or visible == false) then
                                    if i == 1 then
                                        flash_visible1 = visible
                                    else
                                        flash_visible2 = visible
                                    end
                                end
                                if i == 1 then
                                    flash_held1 = held
                                else
                                    flash_held2 = held
                                end
                                if vs ~= CALL_OK or visible ~= false or not held then
                                    if vs ~= CALL_OK then
                                        flash_failure = "ghost_visible_unknown"
                                    elseif visible ~= false then
                                        flash_failure = "ghost_visible"
                                    else
                                        flash_failure = "ghost_not_held"
                                    end
                                    flash_acquired = false
                                    break
                                end
                            end
                        elseif not state then
                            flash_failure = "state_missing"
                        elseif state._release_pending then
                            flash_failure = "release_pending"
                        elseif state.property ~= "visible" then
                            flash_failure = "property"
                        else
                            flash_failure = "targets_changed"
                        end
                    else
                        flash_failure = "targets_invalid"
                    end
                    if not flash_acquired then
                        local had_lease = self._h5_groups
                            and self._h5_groups[H5_FLASH_GROUP] ~= nil
                        self:_h5_release_group(H5_FLASH_GROUP)
                        local row = E and type(E._rows) == "table" and E._rows[4] or nil
                        if row and type(row._hide_grenade_flash) == "function" then
                            row:_hide_grenade_flash()
                        end
                        if E then
                            E._grenade_flash_ok = false
                            E._grenade_flash_source = nil
                        end
                        if E and type(E._grenade_flash_trace_ready) == "function"
                            and E:_grenade_flash_trace_ready("lease", "acquire_failed") then
                            local flash_visible = {flash_visible1, flash_visible2}
                            local flash_held = {flash_held1, flash_held2}
                            E:_trace_grenade_flash("lease", "acquire_failed",
                                h5_flash_lease_detail(self, lease_generation,
                                    flash_targets, flash_visible, flash_held,
                                    flash_failure, E, e_vis, flash_ok,
                                    "post_release"))
                        end
                        if had_lease and E
                            and type(E._grenade_flash_trace_ready) == "function"
                            and E:_grenade_flash_trace_ready("lease", "released") then
                            E:_trace_grenade_flash("lease", "released",
                                "from=acquire_failed")
                        end
                    elseif E and type(E._grenade_flash_trace_ready) == "function"
                        and E:_grenade_flash_trace_ready("lease", "acquired") then
                        local flash_visible = {flash_visible1, flash_visible2}
                        local flash_held = {flash_held1, flash_held2}
                        E:_trace_grenade_flash("lease", "acquired",
                            h5_flash_lease_detail(self, lease_generation,
                                flash_targets, flash_visible, flash_held,
                                flash_failure, E, e_vis, flash_ok,
                                "post_acquire"))
                    end
                else
                    local had_lease = self._h5_groups
                        and self._h5_groups[H5_FLASH_GROUP] ~= nil
                    self:_h5_release_group(H5_FLASH_GROUP)
                    if had_lease and E
                        and type(E._grenade_flash_trace_ready) == "function"
                        and E:_grenade_flash_trace_ready("lease", "released") then
                        E:_trace_grenade_flash("lease", "released",
                            "from=source_unavailable")
                    end
                end
                handled_keys[H5_FLASH_GROUP] = true
                if not cooldown_ok then
                    if not h5_cooldown_handoff_keep(self, E, mgr, entry_panel,
                        e_ok, e_vis, flash_source) then
                        self:_h5_release_group(H5_COOLDOWN_GROUP)
                    end
                    handled_keys[H5_COOLDOWN_GROUP] = true
                end
            end
        end
    else
        self:_h5_release_group("local_p_p")
        self:_h5_release_group("local_p_w")
        self:_h5_release_group("local_p_e")
        self:_h5_release_group(H5_COOLDOWN_GROUP)
        self:_h5_release_group(H5_FLASH_GROUP)
    end

    if c_ok and c_vis and ACT and type(ACT.write_crew_native_coverage) == "function" then
        -- Recompute the row set only when the fresh signature differs from the
        -- one that produced the memoized rows. The per-position validation,
        -- card visibility and acquisition loop below always runs.
        local s0 = sub and self:_residual_stamp() or nil
        local crew_cache = self._h5_coord_cache
        local crew_sig = self:_h5_crew_coverage_signature()
        local rows = crew_cache and crew_cache.crew_rows
        local crew_hit = false
        if crew_cache and rows and self._h5_crew_coverage == rows then
            local previous = crew_cache.crew_sig
            if type(previous) == "table" and #previous == #crew_sig then
                crew_hit = true
                for i = 1, #crew_sig do
                    if previous[i] ~= crew_sig[i] then crew_hit = false; break end
                end
            end
        end
        if not crew_hit then
            self._h5_crew_coverage = self._h5_crew_coverage or {}
            local snap_ok, written = pcall(ACT.write_crew_native_coverage, ACT, self._h5_crew_coverage)
            if snap_ok and type(written) == "table" then
                rows = written
                if crew_cache then
                    crew_cache.crew_sig = crew_sig
                    crew_cache.crew_rows = written
                end
            else
                rows = nil
                if crew_cache then
                    crew_cache.crew_sig = nil
                    crew_cache.crew_rows = nil
                end
            end
        end
        if s0 then self:_residual_record("harmony_duplicates_sig", s0) end
        if type(rows) == "table" then
            local seen_slots = {}
            for pos = 1, 3 do
                local current = rows[pos]
                local shown = C._native_coverage and C._native_coverage[pos]
                local s0 = sub and self:_residual_stamp() or nil
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
                                    if s0 then self:_residual_record("harmony_duplicates_validate", s0) end
                                    local s0 = sub and self:_residual_stamp() or nil
                                    local targets = h5_collect_crew_targets(entry_panel, current, shown)
                                    if s0 then self:_residual_record("harmony_duplicates_collect", s0) end
                                    if #targets > 0 then
                                        self:_h5_acquire_group(key, targets, {
                                            entry_panel = entry_panel, manager = mgr, root_gen = self._generation,
                                        })
                                    else
                                        self:_h5_release_group(key)
                                    end
                                end
                            end
                        end
                    end
                end
            end
        end
    end

    if self._h5_groups and self._h5_groups[H5_HACKER_ACTIVE_GROUP] then
        local hacker_state = self._h5_groups[H5_HACKER_ACTIVE_GROUP]
        local hacker_binding = self._hacker_active_binding
        if hacker_binding and hacker_binding.leased == true
            and hacker_state._release_pending ~= true
            and hacker_state.generation == hacker_binding.lease_gen
            and h5_same_targets(hacker_state.targets, hacker_binding.leaves) then
            handled_keys[H5_HACKER_ACTIVE_GROUP] = true
        end
    end
    if self._h5_groups then
        local crew_decks = self._crew_perkdeck
        if crew_decks then
            for slot = 1, CREW_DECK_MAX do
                local binding = crew_decks[slot]
                if binding and binding.leased == true and binding.group_key then
                    handled_keys[binding.group_key] = true
                end
            end
        end
        for key, state in pairs(self._h5_groups) do
            if not handled_keys[key] then
                self:_h5_release_group(key)
            end
        end
    end
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
    local delayed = self._delayed_binding
    if delayed and delayed.release_pending then
        self:_release_delayed_replacement(false)
    end
    local reserve = self._reserve_binding
    if reserve and reserve.release_pending then
        self:_release_reserve_replacement(false)
    end
    local copr = self._copr_binding
    if copr and copr.release_pending then
        self:_release_copr_replacement(false)
    end
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
    damage_feedback_hide_owned()
    self:_release_crew_perkdeck()
    if not self._h5_groups then
        local hacker_binding = self._hacker_active_binding
        if not hacker_binding or hacker_binding.release_pending ~= true then
            self._hacker_active_binding = nil
        end
        self._hacker_active_conflict_event = nil
        self._hacker_active_conflict_targets = nil
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
    if not (self._h5_groups and self._h5_groups[H5_HACKER_ACTIVE_GROUP]) then
        local hacker_binding = self._hacker_active_binding
        if not hacker_binding or hacker_binding.release_pending ~= true then
            self._hacker_active_binding = nil
        end
    end
    self._hacker_active_conflict_event = nil
    self._hacker_active_conflict_targets = nil
    self:_sync_h5_id_label_visibility()
end

function RT:_release_h5()
    self:_release_all_h5()
end

-- Local native delayed-damage replacement. Native update_delayed_damage owns
-- visible/color; native_visibility owns only the alpha leases on these exact
-- two local leaves. Priority stays unchanged and naturally stops blocking once
-- the qualified duplicates are alpha 0.
local DELAYED_OWNER = "kyohud_delayed_replacement"
local DELAYED_DEPTH = 16
local RESERVE_OWNER = "kyohud_reserve_replacement"
local COPR_OWNER = "kyohud_copr_replacement"

local function dr_near(a, b, eps)
    return finite(a) and finite(b) and math.abs(a - b) <= (eps or 0.001)
end

local function dr_ratio(current, maximum)
    if not finite(current) or not finite(maximum) or maximum < 0 then return nil end
    if maximum == 0 then
        if current == 0 then return 0 end
        return nil
    end
    if current < 0 then return nil end
    if current > maximum then
        -- Presentation-only envelope: tolerate a positive maximum exceeded by
        -- at most a relative single-precision-sized bound (maximum * 2^-23),
        -- capped by the existing absolute receipt comparison tolerance used by
        -- dr_near. Raw health/armor values stay untouched; this does not claim
        -- a digest implementation nor prove an actual engine cause.
        local envelope = math.min(0.001, maximum * 2^-23)
        if current - maximum <= envelope then return 1 end
        return nil
    end
    return current / maximum
end

local function dr_read_number(obj, method)
    local status, value = safe_call(obj, method)
    if status ~= CALL_OK or not finite(value) then return nil end
    return value
end

local function dr_read_ratio_color(panel)
    if not panel_alive(panel) then return nil end
    local ok, color = pcall(function() return panel:color() end)
    if not ok or color == nil then return nil end
    local rok, r = pcall(function() return color.r end)
    if not rok or not finite(r) or r < 0 or r > 1 then return nil end
    return r
end

local function dr_root_visible(P)
    if not P or not P._root or not panel_alive(P._root) then return false end
    local status, visible = safe_call(P._root, "visible")
    return status == CALL_OK and visible == true
end

-- Read only a valid local active debt whose source identity still matches the
-- owned receipt. Direct source replacement, unknown/NaN live data and inactive
-- debt deliberately return nil so the caller keeps the existing refusal path.
local function dr_live_source(P, mgr)
    local receipt = P and P._delayed_source_receipt
    if type(receipt) ~= "table" then return nil end
    if receipt.manager ~= mgr or receipt.root ~= P._root
        or receipt.runtime_root ~= RT._root_panel
        or receipt.generation ~= RT._generation then
        return nil
    end
    local us, unit = safe_call(managers and managers.player or nil, "player_unit")
    if us ~= CALL_OK or unit == nil then return nil end
    local cds, damage = safe_call(unit, "character_damage")
    if cds ~= CALL_OK or damage == nil then return nil end
    if receipt.unit ~= unit or receipt.damage ~= damage then return nil end
    local health = dr_read_number(damage, "get_real_health")
    local health_max = dr_read_number(damage, "_max_health")
    local armor = dr_read_number(damage, "get_real_armor")
    local armor_max = dr_read_number(damage, "_max_armor")
    local debt = dr_read_number(damage, "remaining_delayed_damage")
    local health_ratio = dr_ratio(health, health_max)
    local armor_ratio = dr_ratio(armor, armor_max)
    if health_ratio == nil or armor_ratio == nil then return nil end
    if debt == nil or debt <= 0 then return nil end
    return {
        health = health,
        health_max = health_max,
        health_ratio = health_ratio,
        armor = armor,
        armor_max = armor_max,
        armor_ratio = armor_ratio,
        debt = debt,
    }
end

local function dr_receipt_stale(P, live)
    local receipt = P and P._delayed_source_receipt
    if type(receipt) ~= "table" then return true end
    local armor_ratio_ok
    if live.armor_max == 0 then
        armor_ratio_ok = receipt.armor_ratio == nil
            or dr_near(receipt.armor_ratio, 0)
    else
        armor_ratio_ok = dr_near(receipt.armor_ratio, live.armor_ratio)
    end
    return not dr_near(receipt.health_current, live.health)
        or not dr_near(receipt.health_total, live.health_max)
        or not dr_near(receipt.health_ratio, live.health_ratio)
        or not dr_near(receipt.armor_current, live.armor)
        or not dr_near(receipt.armor_total, live.armor_max)
        or not armor_ratio_ok
        or receipt.delayed_known ~= true
        or not dr_near(receipt.delayed_amount, live.debt)
end

-- Local Ex-President reserve replacement. The native set_stored_health_max /
-- set_stored_health paths only write visible/color, never alpha, so the two
-- duplicate radial leaves are hidden through alpha leases only. Reservation
-- reads use the same bounded common ancestry helpers as the delayed replacement.
local function reserve_ratio(current, maximum)
    if not finite(current) or not finite(maximum) or maximum < 0 then return nil end
    if current < 0 then return nil end
    if maximum == 0 then
        if current == 0 then return 0 end
        return nil
    end
    local ratio = current / maximum
    if ratio < 0 then return nil end
    if ratio > 1 then ratio = 1 end
    return ratio
end

local function reserve_live_source(P, mgr)
    local receipt = P and P._reserve_source_receipt
    if type(receipt) ~= "table" then return nil end
    if receipt.manager ~= mgr or receipt.root ~= P._root
        or receipt.runtime_root ~= RT._root_panel
        or receipt.generation ~= RT._generation then
        return nil
    end
    local us, unit = safe_call(managers and managers.player or nil, "player_unit")
    if us ~= CALL_OK or unit == nil then return nil end
    local cds, damage = safe_call(unit, "character_damage")
    if cds ~= CALL_OK or damage == nil then return nil end
    if receipt.unit ~= unit or receipt.damage ~= damage then return nil end
    local max_health = dr_read_number(damage, "_max_health")
    local stored = dr_read_number(damage, "armor_stored_health")
    local max_stored = dr_read_number(damage, "max_armor_stored_health")
    if max_health == nil or max_health <= 0 then return nil end
    if stored == nil or max_stored == nil then return nil end
    local stock_ratio = reserve_ratio(stored, max_health)
    local capacity_ratio = reserve_ratio(max_stored, max_health)
    if stock_ratio == nil or capacity_ratio == nil then return nil end
    return {
        stored = stored,
        max_stored = max_stored,
        max_health = max_health,
        stock_ratio = stock_ratio,
        capacity_ratio = capacity_ratio,
    }
end

local function reserve_receipt_stale(P, live)
    local receipt = P and P._reserve_source_receipt
    if type(receipt) ~= "table" or receipt.stored_known ~= true then return true end
    return not dr_near(receipt.stored_ratio, live.stock_ratio)
        or not dr_near(receipt.stored_max_ratio, live.capacity_ratio)
end

-- Local COPR replacement source. The native overlay exposes an effective
-- temporary upgrade flag plus the real static damage ratio; the owned gauge
-- markers also derive from that ratio and the real local health. Unknown or
-- unsupported sources stay native instead of being masked.
local function copr_live_source(P, mgr)
    local receipt = P and P._copr_source_receipt
    if type(receipt) ~= "table" then return nil end
    if receipt.manager ~= mgr or receipt.root ~= P._root
        or receipt.runtime_root ~= RT._root_panel
        or receipt.generation ~= RT._generation then
        return nil
    end
    local pm = managers and managers.player or nil
    local as, active = safe_call(pm, "has_activate_temporary_upgrade",
        "temporary", "copr_ability")
    if as ~= CALL_OK or active ~= true then return nil end
    local rs, ratio = safe_call(pm, "upgrade_value",
        "player", "copr_static_damage_ratio", 0)
    if rs ~= CALL_OK or not finite(ratio) or ratio <= 0 or ratio > 1 then
        return nil
    end
    local us, unit = safe_call(managers and managers.player or nil, "player_unit")
    if us ~= CALL_OK or unit == nil then return nil end
    local cds, damage = safe_call(unit, "character_damage")
    if cds ~= CALL_OK or damage == nil then return nil end
    if receipt.unit ~= unit or receipt.damage ~= damage then return nil end
    local health = dr_read_number(damage, "get_real_health")
    local health_max = dr_read_number(damage, "_max_health")
    if health == nil or health_max == nil or health_max <= 0 then return nil end
    local health_ratio = dr_ratio(health, health_max)
    if health_ratio == nil then return nil end
    local raw_n = 1 / ratio
    if not finite(raw_n) or raw_n < 1 then return nil end
    local n = math.ceil(raw_n)
    if n < 1 or n > COPR_CHILD_MAX then return nil end
    return {
        active = true,
        ratio = ratio,
        n = n,
        health = health,
        health_max = health_max,
        health_ratio = health_ratio,
        unit = unit,
        damage = damage,
    }
end

local function copr_receipt_stale(P, live)
    local receipt = P and P._copr_source_receipt
    if type(receipt) ~= "table" or receipt.copr_active ~= true then return true end
    return not dr_near(receipt.copr_ratio, live.ratio)
        or not dr_near(receipt.health_current, live.health)
        or not dr_near(receipt.health_total, live.health_max)
        or not dr_near(receipt.health_ratio, live.health_ratio)
end

function RT:_stoic_trace_record()
    if self._stoic_trace_enabled ~= true then return end
    local reason = self._stoic_trace_stage_override_reason
        or self._stoic_trace_stage_reason or "unknown"
    local detail = self._stoic_trace_stage_override_detail
        or self._stoic_trace_stage_detail
    if self._stoic_trace_last_reason == nil then
        self._stoic_trace_last_reason = reason
        return
    end
    if reason == self._stoic_trace_last_reason then
        return
    end
    if (self._stoic_trace_emitted or 0) >= STOIC_TRACE_LIMIT then return end
    self._stoic_trace_last_reason = reason
    local label
    if reason == "covered" then
        label = "COVERED"
    elseif reason == "inactive" or reason == "unknown" then
        label = "STATE"
    elseif self._stoic_trace_first_fail_emitted ~= true then
        self._stoic_trace_first_fail_emitted = true
        label = "FIRSTFAIL"
    else
        label = "REFUSAL"
    end
    self._stoic_trace_emitted = (self._stoic_trace_emitted or 0) + 1
    pcall(function()
        local parts = {"[KyoHUD][StoicTrace]", label, "reason=" .. tostring(reason)}
        if type(detail) == "table" then
            local order = {
                "hp", "hp_max", "armor", "armor_max", "debt",
                "real_hp_ratio", "real_armor_ratio",
                "native_hp", "native_hp_max", "native_armor", "native_armor_max",
                "native_entry_hp_ratio", "native_entry_armor_ratio",
                "native_hp_ratio", "native_armor_ratio",
                "health_color", "shield_color",
            }
            for i = 1, #order do
                local key = order[i]
                local value = detail[key]
                if type(value) == "number" and value == value
                    and value ~= math.huge and value ~= -math.huge then
                    parts[#parts + 1] = key .. "=" .. string.format("%.17g", value)
                end
            end
        end
        local log_fn = _G.log
        if type(log_fn) == "function" then
            log_fn(table.concat(parts, " "))
        end
    end)
end

function RT:_priority_trace_record(first, t)
    if self._stoic_trace_enabled ~= true then return end
    if type(first) ~= "table" then return end
    if (self._priority_trace_emitted or 0) >= PRIORITY_TRACE_LIMIT then return end
    self._priority_trace_emitted = (self._priority_trace_emitted or 0) + 1
    local function tuple(bounds)
        if type(bounds) ~= "table" then return "unknown" end
        if not (finite(bounds.x) and finite(bounds.y)
            and finite(bounds.w) and finite(bounds.h)) then
            return "unknown"
        end
        return string.format("%.6f,%.6f,%.6f,%.6f",
            bounds.x, bounds.y, bounds.w, bounds.h)
    end
    local function visible_text(value)
        if value == true then return "true" end
        if value == false then return "false" end
        return "unknown"
    end
    local function alpha_text(value)
        if finite(value) then return tostring(value) end
        return "unknown"
    end
    local function local_text(slot)
        if type(HUDManager) == "table"
            and type(HUDManager.PLAYER_PANEL) == "number"
            and type(slot) == "number" then
            if slot == HUDManager.PLAYER_PANEL then return "true" end
            return "false"
        end
        return "unknown"
    end
    pcall(function()
        local slot = first.slot
        if slot == nil then slot = "?" end
        local line = "[KyoHUD][StoicTrace] PRIORITY cause="
            .. tostring(first.cause or "unknown")
            .. " leaf=" .. tostring(first.leaf or "unknown")
            .. " native_bounds=" .. tuple(first.native_bounds)
            .. " owned_bounds=" .. tuple(first.owned_bounds)
            .. " slot=" .. tostring(slot)
            .. " local=true"
            .. " effective_visible=" .. visible_text(first.effective_visible)
            .. " effective_alpha=" .. alpha_text(first.effective_alpha)
            .. " source_local=" .. local_text(first.slot)
        line = line .. " coord_space=runtime_parent"
        if finite(t) then
            line = line .. " time=" .. tostring(t)
        end
        local log_fn = _G.log
        if type(log_fn) == "function" then
            log_fn(line)
        end
    end)
end

local function dr_active_container(panel)
    if not panel_alive(panel) then return false end
    local vs, visible = safe_call(panel, "visible")
    if vs ~= CALL_OK or visible ~= true then return false end
    local as, alpha = safe_call(panel, "alpha")
    return as == CALL_OK and finite(alpha) and alpha > 0
end

local function dr_leaf_readable(leaf)
    if not panel_alive(leaf) then return false end
    for _, method in ipairs({"x", "y", "w", "h", "alpha"}) do
        local status, value = safe_call(leaf, method)
        if status ~= CALL_OK or not finite(value) then return false end
    end
    local vs, visible = safe_call(leaf, "visible")
    return vs == CALL_OK and (visible == true or visible == false)
end

local function dr_reaches(panel, common)
    if not panel_alive(panel) or not panel_alive(common) then return false end
    if panel == common then return true end
    local current = panel
    local depth = 0
    while depth < DELAYED_DEPTH do
        local status, parent = safe_call(current, "parent")
        if status ~= CALL_OK or parent == nil or not panel_alive(parent) then
            return false
        end
        if parent == common then return true end
        current = parent
        depth = depth + 1
    end
    return false
end

local function dr_reaches_exposed(panel, common)
    if not panel_alive(panel) or not panel_alive(common) then return false end
    local current = panel
    local depth = 0
    while depth < DELAYED_DEPTH do
        if not dr_active_container(current) then return false end
        local status, parent = safe_call(current, "parent")
        if status ~= CALL_OK or parent == nil or not panel_alive(parent) then
            return false
        end
        if parent == common then return true end
        current = parent
        depth = depth + 1
    end
    return false
end

local function dr_pending(nv, owner, generation)
    if not nv or type(nv._entries) ~= "table" then return false end
    for _, entry in ipairs(nv._entries) do
        if entry.owner == owner and entry.generation == generation then
            return true
        end
    end
    return false
end

local function dr_restore_added(binding, nv)
    if not binding.added or not nv or type(nv._whitelist) ~= "table" then return end
    for leaf, previous in pairs(binding.added) do
        local entry = nv._whitelist[leaf]
        if entry then
            entry.alpha = previous.alpha
            if not next(entry) then nv._whitelist[leaf] = nil end
        end
    end
    binding.added = nil
end

function RT:_release_delayed_replacement(clear_binding)
    local binding = self._delayed_binding
    if not binding then return end
    local nv = kyohud.hud.native_visibility
    if binding.leased or binding.release_pending then
        if nv and type(nv.release) == "function" then
            nv:release(DELAYED_OWNER, binding.lease_gen)
        end
        if dr_pending(nv, DELAYED_OWNER, binding.lease_gen) then
            binding.release_pending = true
            if clear_binding then binding.clear_on_release = true end
            return
        end
        binding.release_pending = false
        dr_restore_added(binding, nv)
        binding.leased = false
        binding.lease_gen = nil
    end
    if clear_binding or binding.clear_on_release then
        binding.clear_on_release = nil
        if not dr_pending(nv, DELAYED_OWNER, binding.lease_gen) then
            self._delayed_binding = nil
        end
    end
end

function RT:_delayed_native_chain(mgr)
    if not mgr or type(mgr._teammate_panels) ~= "table" then return nil end
    local entry = mgr._teammate_panels[h5_player_slot()]
    if type(entry) ~= "table" then return nil end
    local entry_panel = entry._panel
    if not entry_panel or not panel_alive(entry_panel) then return nil end
    local common = self._parent_panel
    if not common or not panel_alive(common) then return nil end
    if not dr_reaches_exposed(entry_panel, common) then return nil end

    local js, player_panel = safe_call(entry_panel, "child", "player")
    if js ~= CALL_OK or not player_panel or not panel_alive(player_panel) then return nil end
    local ps, player_parent = safe_call(player_panel, "parent")
    if ps ~= CALL_OK or player_parent ~= entry_panel then return nil end

    local rs, radial = safe_call(player_panel, "child", "radial_health_panel")
    if rs ~= CALL_OK or not radial or not panel_alive(radial) then return nil end
    local rp, radial_parent = safe_call(radial, "parent")
    if rp ~= CALL_OK or radial_parent ~= player_panel then return nil end

    local ds, delayed = safe_call(radial, "child", "radial_delayed_damage")
    if ds ~= CALL_OK or not delayed or not panel_alive(delayed) then return nil end
    local dp, delayed_parent = safe_call(delayed, "parent")
    if dp ~= CALL_OK or delayed_parent ~= radial then return nil end

    local as, armor_leaf = safe_call(delayed, "child", "radial_delayed_damage_armor")
    if as ~= CALL_OK or not armor_leaf or not panel_alive(armor_leaf) then return nil end
    local hs, health_leaf = safe_call(delayed, "child", "radial_delayed_damage_health")
    if hs ~= CALL_OK or not health_leaf or not panel_alive(health_leaf) then return nil end
    local ap, armor_parent = safe_call(armor_leaf, "parent")
    local hp, health_parent = safe_call(health_leaf, "parent")
    if ap ~= CALL_OK or armor_parent ~= delayed then return nil end
    if hp ~= CALL_OK or health_parent ~= delayed then return nil end

    local rhs, radial_health = safe_call(radial, "child", "radial_health")
    if rhs ~= CALL_OK or not radial_health or not panel_alive(radial_health) then return nil end
    local shs, radial_shield = safe_call(radial, "child", "radial_shield")
    if shs ~= CALL_OK or not radial_shield or not panel_alive(radial_shield) then return nil end
    local rhp, radial_health_parent = safe_call(radial_health, "parent")
    local shp, radial_shield_parent = safe_call(radial_shield, "parent")
    if rhp ~= CALL_OK or radial_health_parent ~= radial then return nil end
    if shp ~= CALL_OK or radial_shield_parent ~= radial then return nil end

    if not dr_active_container(entry_panel) or not dr_active_container(player_panel)
        or not dr_active_container(radial) or not dr_active_container(delayed) then
        return nil
    end
    if not dr_leaf_readable(armor_leaf) or not dr_leaf_readable(health_leaf) then
        return nil
    end
    for _, node in ipairs({player_panel, radial, delayed, armor_leaf, health_leaf}) do
        if not dr_reaches(node, common) then return nil end
    end

    return {
        entry = entry,
        entry_panel = entry_panel,
        player = player_panel,
        radial = radial,
        delayed = delayed,
        armor_leaf = armor_leaf,
        health_leaf = health_leaf,
        radial_health = radial_health,
        radial_shield = radial_shield,
    }
end

function RT:_delayed_source_state(mgr, chain)
    local trace = self._stoic_trace_enabled == true
    local P = kyohud.hud.player
    if not P or not P._root or not P._gauge or not panel_alive(P._root) then
        return nil, "unknown", nil
    end
    local receipt = P._delayed_source_receipt
    if type(receipt) ~= "table" then return nil, "receipt_stale", nil end
    if receipt.manager ~= mgr or receipt.root ~= P._root
        or receipt.runtime_root ~= self._root_panel
        or receipt.generation ~= self._generation then
        return nil, "source_changed", nil
    end

    local us, unit = safe_call(managers and managers.player or nil, "player_unit")
    if us ~= CALL_OK or unit == nil then return nil, "live_data_invalid", nil end
    local cds, damage = safe_call(unit, "character_damage")
    if cds ~= CALL_OK or damage == nil then return nil, "live_data_invalid", nil end
    if receipt.unit ~= unit or receipt.damage ~= damage then
        return nil, "source_changed", nil
    end

    local health = dr_read_number(damage, "get_real_health")
    local health_max = dr_read_number(damage, "_max_health")
    local armor = dr_read_number(damage, "get_real_armor")
    local armor_max = dr_read_number(damage, "_max_armor")
    local debt = dr_read_number(damage, "remaining_delayed_damage")
    local health_ratio = dr_ratio(health, health_max)
    local armor_ratio = dr_ratio(armor, armor_max)
    if armor_ratio == nil and finite(armor) and finite(armor_max)
        and armor_max > 0 and armor > armor_max then
        -- Client transient armor overshoot above its max is not corruption:
        -- clamp the ratio to full instead of rejecting the delayed source.
        armor_ratio = 1
    end
    local detail
    if trace then
        detail = {
            hp = health,
            hp_max = health_max,
            armor = armor,
            armor_max = armor_max,
            debt = debt,
            real_hp_ratio = health_ratio,
            real_armor_ratio = armor_ratio,
        }
    end
    if health_ratio == nil or armor_ratio == nil then
        return nil, "live_data_invalid", detail
    end
    if debt == nil or debt <= 0 then return nil, "inactive", detail end

    local receipt_armor_ratio_ok
    if armor_max == 0 then
        receipt_armor_ratio_ok = receipt.armor_ratio == nil
            or dr_near(receipt.armor_ratio, 0)
    else
        receipt_armor_ratio_ok = dr_near(receipt.armor_ratio, armor_ratio)
    end
    if not dr_near(receipt.health_current, health)
        or not dr_near(receipt.health_total, health_max)
        or not dr_near(receipt.health_ratio, health_ratio)
        or not dr_near(receipt.armor_current, armor)
        or not dr_near(receipt.armor_total, armor_max)
        or not receipt_armor_ratio_ok
        or receipt.delayed_known ~= true
        or not dr_near(receipt.delayed_amount, debt) then
        return nil, "receipt_stale", detail
    end

    local gauge = P._gauge
    local guage_health = gauge._health
    local gauge_armor = gauge._armor
    local effects = gauge._health_effects
    local gd = effects and effects.delayed_damage or nil
    if type(guage_health) ~= "table" or guage_health.valid ~= true
        or not dr_near(guage_health.current, health)
        or not dr_near(guage_health.total, health_max)
        or not dr_near(guage_health.ratio, health_ratio) then
        return nil, "rendered_data_mismatch", detail
    end
    if type(gauge_armor) ~= "table" or not dr_near(gauge_armor.current, armor)
        or not dr_near(gauge_armor.total, armor_max) then
        return nil, "rendered_data_mismatch", detail
    end
    if armor_max > 0 then
        if gauge_armor.valid ~= true or not dr_near(gauge_armor.ratio, armor_ratio) then
            return nil, "rendered_data_mismatch", detail
        end
    end
    if type(gd) ~= "table" or gd.known ~= true or not dr_near(gd.amount, debt) then
        return nil, "rendered_data_mismatch", detail
    end

    local common = self._parent_panel
    if not common or not panel_alive(common) then
        return nil, "owned_ancestry", detail
    end
    local prs, root_parent = safe_call(P._root, "parent")
    if prs ~= CALL_OK or root_parent ~= self._root_panel then
        return nil, "owned_ancestry", detail
    end
    if not dr_reaches_exposed(P._root, common) then
        return nil, "owned_exposure", detail
    end
    local gauge_root = gauge.root
    if not gauge_root or not panel_alive(gauge_root) then
        return nil, "owned_ancestry", detail
    end
    local grs, gauge_parent = safe_call(gauge_root, "parent")
    if grs ~= CALL_OK or gauge_parent ~= P._root then
        return nil, "owned_ancestry", detail
    end
    if not dr_reaches_exposed(gauge_root, common) then
        return nil, "owned_exposure", detail
    end
    local health_fill = gauge.health_fill
    if not health_fill or not panel_alive(health_fill) then
        return nil, "owned_ancestry", detail
    end
    local hrs, fill_parent = safe_call(health_fill, "parent")
    if hrs ~= CALL_OK or fill_parent ~= gauge_root then
        return nil, "owned_ancestry", detail
    end
    if not dr_reaches_exposed(health_fill, common) then
        return nil, "owned_exposure", detail
    end
    local delayed_armor = gauge._delayed_armor
    if not delayed_armor or not panel_alive(delayed_armor) then
        return nil, "owned_ancestry", detail
    end
    local das, armor_parent = safe_call(delayed_armor, "parent")
    if das ~= CALL_OK or armor_parent ~= gauge_root then
        return nil, "owned_ancestry", detail
    end
    if not dr_reaches(delayed_armor, common) then
        return nil, "owned_ancestry", detail
    end
    for i = 1, 4 do
        local rect = gauge._delayed_health and gauge._delayed_health[i]
        if not rect or not panel_alive(rect) then
            return nil, "owned_ancestry", detail
        end
        local rps, rect_parent = safe_call(rect, "parent")
        if rps ~= CALL_OK or rect_parent ~= health_fill then
            return nil, "owned_ancestry", detail
        end
        if not dr_reaches(rect, common) then
            return nil, "owned_ancestry", detail
        end
    end

    local entry_health = chain.entry._health_data
    local entry_armor = chain.entry._armor_data
    if type(entry_health) ~= "table" or type(entry_armor) ~= "table" then
        return nil, "native_data_unknown", detail
    end
    local native_health_ratio = dr_ratio(entry_health.current, entry_health.total)
    local native_armor_ratio = dr_ratio(entry_armor.current, entry_armor.total)
    if native_health_ratio == nil or native_armor_ratio == nil then
        return nil, "native_data_unknown", detail
    end
    if trace then
        detail.native_hp = entry_health.current
        detail.native_hp_max = entry_health.total
        detail.native_armor = entry_armor.current
        detail.native_armor_max = entry_armor.total
        detail.native_entry_hp_ratio = native_health_ratio
        detail.native_entry_armor_ratio = native_armor_ratio
    end
    -- Native presentation may be smoothed independently of the real source.
    -- It must stay numeric/coherent and share the real maxima, but its current
    -- values and color animation are not required to equal the real source.
    if not dr_near(entry_health.total, health_max)
        or not dr_near(entry_armor.total, armor_max) then
        return nil, "native_split_mismatch", detail
    end
    local health_color = dr_read_ratio_color(chain.radial_health)
    local shield_color = dr_read_ratio_color(chain.radial_shield)
    if trace then
        detail.health_color = health_color
        detail.shield_color = shield_color
        detail.native_hp_ratio = health_color
        detail.native_armor_ratio = shield_color
    end
    if health_color == nil or shield_color == nil then
        return nil, "native_color_unknown", detail
    end

    local vs, visible = safe_call(P._root, "visible")
    if vs ~= CALL_OK or visible ~= true then
        return nil, "owned_exposure", detail
    end
    if _effective_visible(P._root, {}) ~= true then
        return nil, "owned_exposure", detail
    end
    local alpha = _effective_alpha(P._root, {})
    if alpha == nil or alpha <= 0 then
        return nil, "owned_exposure", detail
    end

    return {health_ratio = health_ratio, armor_ratio = armor_ratio, debt = debt},
        "covered", detail
end

function RT:_delayed_acquire(binding)
    local nv = kyohud.hud.native_visibility
    if not nv or type(nv.acquire) ~= "function" then return false end
    local added = binding.added
    if not binding.leased or type(added) ~= "table" then
        added = {}
        if type(nv._whitelist) == "table" then
            for _, leaf in ipairs({binding.armor_leaf, binding.health_leaf}) do
                local entry = nv._whitelist[leaf]
                if not entry then entry = {}; nv._whitelist[leaf] = entry end
                if entry.alpha ~= true then
                    added[leaf] = {alpha = entry.alpha}
                    entry.alpha = true
                end
            end
        end
    end
    local generation = binding.lease_gen
    if not binding.leased or generation == nil then
        self._delayed_lease_generation = (self._delayed_lease_generation or 0) + 1
        generation = self._delayed_lease_generation
    end
    -- Record the attempted lease ownership before the call so a partial or
    -- failed acquire can release/retry the exact generation and retain the
    -- whitelist markers while any NV entry remains.
    binding.lease_gen = generation
    binding.added = added
    binding.release_pending = true
    local requests = {
        {id = binding.armor_leaf, property = "alpha", value = 0},
        {id = binding.health_leaf, property = "alpha", value = 0},
    }
    local ok = nv:acquire(DELAYED_OWNER, generation, requests)
    if ok then
        binding.leased = true
        binding.release_pending = false
        return true
    end
    binding.leased = false
    binding.release_pending = true
    return false
end

function RT:_sync_delayed_replacement_unprofiled(mgr)
    local trace = self._stoic_trace_enabled == true
    if trace then
        self._stoic_trace_stage_reason = nil
        self._stoic_trace_stage_detail = nil
        self._stoic_trace_stage_override_reason = nil
        self._stoic_trace_stage_override_detail = nil
    end
    local P = kyohud.hud.player
    local settings = kyohud.settings
    if not mgr or kyohud.settings.enable_hud_foundation ~= true
        or settings.enable_player ~= true or is_vr()
        or self._disabled or self._freeflight or not self._mounted
        or not P or not P._mounted or P._manager ~= mgr then
        if trace then self._stoic_trace_stage_reason = "runtime_inactive" end
        self:_release_delayed_replacement(true)
        return
    end

    local binding = self._delayed_binding
    if binding and binding.release_pending then
        if trace then self._stoic_trace_stage_reason = "pending_release" end
        self:_release_delayed_replacement(false)
        binding = self._delayed_binding
        if binding and binding.release_pending then return end
    end

    local panels = mgr._teammate_panels
    local entry = type(panels) == "table" and panels[h5_player_slot()] or nil
    local entry_panel = type(entry) == "table" and entry._panel or nil
    if binding and (binding.manager ~= mgr or binding.entry ~= entry
        or binding.entry_panel ~= entry_panel
        or binding.root_gen ~= self._generation) then
        if trace then
            if binding.manager ~= mgr or binding.entry ~= entry
                or binding.entry_panel ~= entry_panel then
                self._stoic_trace_stage_reason = "source_changed"
            else
                self._stoic_trace_stage_reason = "generation_changed"
            end
        end
        self:_release_delayed_replacement(true)
        binding = self._delayed_binding
        if binding then return end
    end

    local chain = self:_delayed_native_chain(mgr)
    if not chain then
        if trace then self._stoic_trace_stage_reason = "chain_invalid" end
        if binding then self:_release_delayed_replacement(false) end
        return
    end
    if binding then
        if binding.armor_leaf ~= chain.armor_leaf
            or binding.health_leaf ~= chain.health_leaf
            or binding.delayed ~= chain.delayed
            or binding.radial ~= chain.radial
            or binding.player ~= chain.player
            or binding.entry_panel ~= chain.entry_panel then
            if trace then self._stoic_trace_stage_reason = "chain_changed" end
            self:_release_delayed_replacement(false)
            return
        end
    end

    local fresh_ok = P._update_ran_now == true
        and P._verify_ok_now == true and P._render_verified == true
    if not fresh_ok then
        local live = dr_live_source(P, mgr)
        local stale = live ~= nil and dr_receipt_stale(P, live)
        local hidden = not dr_root_visible(P)
        if stale then
            -- A throttled player frame lagged behind a valid live source change.
            -- Capture and certify through the existing player seam before any
            -- native mask is authorized; the repair seam also restores a root
            -- hidden by a prior native-priority pass.
            local repair_ok, repaired = pcall(P._repair_and_certify, P, mgr)
            if not repair_ok or repaired ~= true then
                if trace then
                    self._stoic_trace_stage_reason = "uncertified_owned_render"
                end
                if binding then self:_release_delayed_replacement(false) end
                return
            end
        elseif not (hidden and P._render_verified == true) then
            local verify_ok, verified = pcall(P.verify, P)
            if not verify_ok or verified ~= true then
                if trace then
                    self._stoic_trace_stage_reason = "uncertified_owned_render"
                end
                if binding then self:_release_delayed_replacement(false) end
                return
            end
        end
    end

    local state, reason, detail = self:_delayed_source_state(mgr, chain)
    if not state and reason == "owned_exposure"
        and P._render_verified == true and not dr_root_visible(P)
        and dr_live_source(P, mgr) ~= nil then
        -- Only the exposure failed and the root is hidden by a prior native
        -- priority pass. Reuse the certified repair seam once; ancestry,
        -- alpha, primitive and corruption failures are not repaired here.
        local repair_ok, repaired = pcall(P._repair_and_certify, P, mgr)
        if repair_ok and repaired == true then
            state, reason, detail = self:_delayed_source_state(mgr, chain)
        end
    end
    if trace then
        self._stoic_trace_stage_reason = reason or "unknown"
        self._stoic_trace_stage_detail = detail
    end
    if not state then
        if binding then self:_release_delayed_replacement(false) end
        return
    end

    if not binding then
        binding = {
            manager = mgr,
            entry = entry,
            entry_panel = chain.entry_panel,
            root_gen = self._generation,
            player = chain.player,
            radial = chain.radial,
            delayed = chain.delayed,
            armor_leaf = chain.armor_leaf,
            health_leaf = chain.health_leaf,
            leased = false,
        }
        self._delayed_binding = binding
    end

    if not self:_delayed_acquire(binding) then
        if trace then
            self._stoic_trace_stage_reason = "acquisition_failed"
            self._stoic_trace_stage_detail = nil
        end
        self:_release_delayed_replacement(false)
    end
end

function RT:_delayed_replacement_post_priority_unprofiled(t)
    local trace = self._stoic_trace_enabled == true
    local binding = self._delayed_binding
    if not binding or not binding.leased then return end
    local released = false
    local release_reason
    local function release(reason)
        if released then return end
        released = true
        release_reason = reason
        self:_release_delayed_replacement(false)
    end
    local P = kyohud.hud.player
    if not P or not P._root or not panel_alive(P._root) then
        release("released_by_visibility")
    else
        local vs, visible = safe_call(P._root, "visible")
        if vs ~= CALL_OK or visible ~= true then
            release("released_by_visibility")
        end
    end
    if not released then
        local as, armor_alpha = safe_call(binding.armor_leaf, "alpha")
        local hs, health_alpha = safe_call(binding.health_leaf, "alpha")
        local ap, armor_parent = safe_call(binding.armor_leaf, "parent")
        local hp, health_parent = safe_call(binding.health_leaf, "parent")
        if ap ~= CALL_OK or armor_parent ~= binding.delayed
            or hp ~= CALL_OK or health_parent ~= binding.delayed
            or as ~= CALL_OK or not dr_near(armor_alpha, 0, 0.0001)
            or hs ~= CALL_OK or not dr_near(health_alpha, 0, 0.0001) then
            if ap ~= CALL_OK or hp ~= CALL_OK
                or armor_parent ~= binding.delayed
                or health_parent ~= binding.delayed then
                release("released_by_parent")
            else
                release("released_by_alpha")
            end
        end
    end
    if not released then
        local alpha = _effective_alpha(P._root, {})
        if _effective_visible(P._root, {}) ~= true
            or alpha == nil or alpha <= 0 then
            release("released_by_exposure")
        end
    end
    if trace and released then
        local stage_reason = self._stoic_trace_stage_reason
        if stage_reason == nil or stage_reason == "covered" then
            self._stoic_trace_stage_override_reason = release_reason or "released"
            self._stoic_trace_stage_override_detail = nil
        end
    end
    if released and t ~= nil
        and kyohud.settings.enable_hud_foundation == true then
        -- Restored native leaves must participate in this same frame's priority
        -- decision instead of waiting for the next harmony pass.
        self:_apply_native_priority(t, true)
    end
end

function RT:_release_reserve_replacement(clear_binding)
    local binding = self._reserve_binding
    if not binding then return end
    local nv = kyohud.hud.native_visibility
    if binding.leased or binding.release_pending then
        if nv and type(nv.release) == "function" then
            nv:release(RESERVE_OWNER, binding.lease_gen)
        end
        if dr_pending(nv, RESERVE_OWNER, binding.lease_gen) then
            binding.release_pending = true
            if clear_binding then binding.clear_on_release = true end
            return
        end
        binding.release_pending = false
        dr_restore_added(binding, nv)
        binding.leased = false
        binding.lease_gen = nil
    end
    if clear_binding or binding.clear_on_release then
        binding.clear_on_release = nil
        if not dr_pending(nv, RESERVE_OWNER, binding.lease_gen) then
            self._reserve_binding = nil
        end
    end
end

function RT:_reserve_native_chain(mgr)
    if not mgr or type(mgr._teammate_panels) ~= "table" then return nil end
    local entry = mgr._teammate_panels[h5_player_slot()]
    if type(entry) ~= "table" then return nil end
    local entry_panel = entry._panel
    if not entry_panel or not panel_alive(entry_panel) then return nil end
    local common = self._parent_panel
    if not common or not panel_alive(common) then return nil end
    if not dr_reaches_exposed(entry_panel, common) then return nil end

    local js, player_panel = safe_call(entry_panel, "child", "player")
    if js ~= CALL_OK or not player_panel or not panel_alive(player_panel) then return nil end
    local ps, player_parent = safe_call(player_panel, "parent")
    if ps ~= CALL_OK or player_parent ~= entry_panel then return nil end

    local rs, radial = safe_call(player_panel, "child", "radial_health_panel")
    if rs ~= CALL_OK or not radial or not panel_alive(radial) then return nil end
    local rp, radial_parent = safe_call(radial, "parent")
    if rp ~= CALL_OK or radial_parent ~= player_panel then return nil end

    local irs, rip = safe_call(radial, "child", "radial_rip")
    if irs ~= CALL_OK or not rip or not panel_alive(rip) then return nil end
    local ibs, rip_bg = safe_call(radial, "child", "radial_rip_bg")
    if ibs ~= CALL_OK or not rip_bg or not panel_alive(rip_bg) then return nil end
    local irp, rip_parent = safe_call(rip, "parent")
    local ibp, rip_bg_parent = safe_call(rip_bg, "parent")
    if irp ~= CALL_OK or rip_parent ~= radial then return nil end
    if ibp ~= CALL_OK or rip_bg_parent ~= radial then return nil end

    if not dr_active_container(entry_panel) or not dr_active_container(player_panel)
        or not dr_active_container(radial) then
        return nil
    end
    if not dr_leaf_readable(rip) or not dr_leaf_readable(rip_bg) then
        return nil
    end
    for _, node in ipairs({player_panel, radial, rip, rip_bg}) do
        if not dr_reaches(node, common) then return nil end
    end

    -- Publish these freshly verified handles before priority runs: a replaced
    -- but still-alive leaf keeps its old immediate parent, so a stale binding
    -- would otherwise make priority inspect the previous named child.
    h5_child_index_set(entry_panel, "player", player_panel)
    h5_child_index_set(player_panel, "radial_health_panel", radial)
    h5_child_index_set(radial, "radial_rip", rip)
    h5_child_index_set(radial, "radial_rip_bg", rip_bg)

    return {
        entry = entry,
        entry_panel = entry_panel,
        player = player_panel,
        radial = radial,
        rip = rip,
        rip_bg = rip_bg,
    }
end

function RT:_reserve_source_state(mgr, chain)
    local P = kyohud.hud.player
    if not P or not P._root or not P._gauge or not panel_alive(P._root) then
        return nil, "unknown"
    end
    local live = reserve_live_source(P, mgr)
    if not live then return nil, "live_data_invalid" end
    if live.capacity_ratio <= 0 then return nil, "capacity_loss" end
    if reserve_receipt_stale(P, live) then return nil, "receipt_stale" end

    local gauge = P._gauge
    local effects = gauge._health_effects
    local stored = type(effects) == "table" and effects.stored_health or nil
    if type(stored) ~= "table" or stored.known ~= true then
        return nil, "rendered_data_mismatch"
    end
    if not dr_near(stored.ratio, live.stock_ratio)
        or not dr_near(stored.max_ratio, live.capacity_ratio) then
        return nil, "rendered_data_mismatch"
    end

    local common = self._parent_panel
    if not common or not panel_alive(common) then return nil, "owned_ancestry" end
    local prs, root_parent = safe_call(P._root, "parent")
    if prs ~= CALL_OK or root_parent ~= self._root_panel then
        return nil, "owned_ancestry"
    end
    if not dr_reaches_exposed(P._root, common) then
        return nil, "owned_exposure"
    end
    local gauge_root = gauge.root
    if not gauge_root or not panel_alive(gauge_root) then
        return nil, "owned_ancestry"
    end
    local grs, gauge_parent = safe_call(gauge_root, "parent")
    if grs ~= CALL_OK or gauge_parent ~= P._root then
        return nil, "owned_ancestry"
    end
    if not dr_reaches_exposed(gauge_root, common) then
        return nil, "owned_exposure"
    end
    local bg = gauge._stored_health_bg
    local fill = gauge._stored_health_fill
    for _, prim in ipairs({bg, fill}) do
        if not prim or not panel_alive(prim) then return nil, "owned_ancestry" end
        local ps, parent = safe_call(prim, "parent")
        if ps ~= CALL_OK or parent ~= gauge_root then
            return nil, "owned_ancestry"
        end
        if not dr_reaches(prim, common) then return nil, "owned_ancestry" end
        local vs, visible = safe_call(prim, "visible")
        if vs ~= CALL_OK or visible ~= true then
            return nil, "rendered_data_mismatch"
        end
    end

    local vs, visible = safe_call(P._root, "visible")
    if vs ~= CALL_OK or visible ~= true then
        return nil, "owned_exposure"
    end
    if _effective_visible(P._root, {}) ~= true then
        return nil, "owned_exposure"
    end
    local alpha = _effective_alpha(P._root, {})
    if alpha == nil or alpha <= 0 then
        return nil, "owned_exposure"
    end

    return {stock_ratio = live.stock_ratio, capacity_ratio = live.capacity_ratio},
        "covered"
end

function RT:_reserve_acquire(binding)
    local nv = kyohud.hud.native_visibility
    if not nv or type(nv.acquire) ~= "function" then return false end
    local added = binding.added
    if not binding.leased or type(added) ~= "table" then
        added = {}
        if type(nv._whitelist) == "table" then
            for _, leaf in ipairs({binding.rip, binding.rip_bg}) do
                local entry = nv._whitelist[leaf]
                if not entry then entry = {}; nv._whitelist[leaf] = entry end
                if entry.alpha ~= true then
                    added[leaf] = {alpha = entry.alpha}
                    entry.alpha = true
                end
            end
        end
    end
    local generation = binding.lease_gen
    if not binding.leased or generation == nil then
        self._reserve_lease_generation = (self._reserve_lease_generation or 0) + 1
        generation = self._reserve_lease_generation
    end
    binding.lease_gen = generation
    binding.added = added
    binding.release_pending = true
    local requests = {
        {id = binding.rip, property = "alpha", value = 0},
        {id = binding.rip_bg, property = "alpha", value = 0},
    }
    local ok = nv:acquire(RESERVE_OWNER, generation, requests)
    if ok then
        binding.leased = true
        binding.release_pending = false
        return true
    end
    binding.leased = false
    binding.release_pending = true
    return false
end

function RT:_sync_reserve_replacement_unprofiled(mgr)
    local P = kyohud.hud.player
    local settings = kyohud.settings
    if not mgr or kyohud.settings.enable_hud_foundation ~= true
        or settings.enable_player ~= true or is_vr()
        or self._disabled or self._freeflight or not self._mounted
        or not P or not P._mounted or P._manager ~= mgr then
        self:_release_reserve_replacement(true)
        return
    end

    local binding = self._reserve_binding
    if binding and binding.release_pending then
        self:_release_reserve_replacement(false)
        binding = self._reserve_binding
        if binding and binding.release_pending then return end
    end

    local panels = mgr._teammate_panels
    local entry = type(panels) == "table" and panels[h5_player_slot()] or nil
    local entry_panel = type(entry) == "table" and entry._panel or nil
    if binding and (binding.manager ~= mgr or binding.entry ~= entry
        or binding.entry_panel ~= entry_panel
        or binding.root_gen ~= self._generation) then
        self:_release_reserve_replacement(true)
        binding = self._reserve_binding
        if binding then return end
    end

    local chain = self:_reserve_native_chain(mgr)
    if not chain then
        if binding then self:_release_reserve_replacement(false) end
        return
    end
    if binding then
        if binding.rip ~= chain.rip or binding.rip_bg ~= chain.rip_bg
            or binding.radial ~= chain.radial
            or binding.player ~= chain.player
            or binding.entry_panel ~= chain.entry_panel then
            self:_release_reserve_replacement(true)
            return
        end
    end

    local fresh_ok = P._update_ran_now == true
        and P._verify_ok_now == true and P._render_verified == true
    if not fresh_ok then
        local live = reserve_live_source(P, mgr)
        local stale = live ~= nil and reserve_receipt_stale(P, live)
        local hidden = not dr_root_visible(P)
        if stale then
            local repair_ok, repaired = pcall(P._repair_and_certify, P, mgr)
            if not repair_ok or repaired ~= true then
                if binding then self:_release_reserve_replacement(false) end
                return
            end
        elseif not (hidden and P._render_verified == true) then
            local verify_ok, verified = pcall(P.verify, P)
            if not verify_ok or verified ~= true then
                if binding then self:_release_reserve_replacement(false) end
                return
            end
        end
    end

    local state, reason = self:_reserve_source_state(mgr, chain)
    if not state and reason == "owned_exposure"
        and P._render_verified == true and not dr_root_visible(P)
        and reserve_live_source(P, mgr) ~= nil then
        local repair_ok, repaired = pcall(P._repair_and_certify, P, mgr)
        if repair_ok and repaired == true then
            state, reason = self:_reserve_source_state(mgr, chain)
        end
    end
    if not state then
        if binding then self:_release_reserve_replacement(false) end
        return
    end

    if not binding then
        binding = {
            manager = mgr,
            entry = entry,
            entry_panel = chain.entry_panel,
            root_gen = self._generation,
            player = chain.player,
            radial = chain.radial,
            rip = chain.rip,
            rip_bg = chain.rip_bg,
            leased = false,
        }
        self._reserve_binding = binding
    end

    if not self:_reserve_acquire(binding) then
        self:_release_reserve_replacement(false)
        return
    end
    -- The lease is only authorized for a render that still certifies after the
    -- native alpha writes; otherwise fail closed and let priority take over.
    local verify_ok, verified = pcall(P.verify, P)
    if not verify_ok or verified ~= true then
        self:_release_reserve_replacement(false)
    end
end

function RT:_reserve_replacement_post_priority_unprofiled(t)
    local binding = self._reserve_binding
    if not binding or not binding.leased then return end
    local released = false
    local function release()
        if released then return end
        released = true
        self:_release_reserve_replacement(false)
    end
    local P = kyohud.hud.player
    if not P or not P._root or not panel_alive(P._root) then
        release()
    else
        local vs, visible = safe_call(P._root, "visible")
        if vs ~= CALL_OK or visible ~= true then
            release()
        end
    end
    if not released then
        local ar, rip_alpha = safe_call(binding.rip, "alpha")
        local ab, rip_bg_alpha = safe_call(binding.rip_bg, "alpha")
        local pr, rip_parent = safe_call(binding.rip, "parent")
        local pbg, rip_bg_parent = safe_call(binding.rip_bg, "parent")
        local vr, rip_visible = safe_call(binding.rip, "visible")
        local vbg, rip_bg_visible = safe_call(binding.rip_bg, "visible")
        if pr ~= CALL_OK or rip_parent ~= binding.radial
            or pbg ~= CALL_OK or rip_bg_parent ~= binding.radial
            or ar ~= CALL_OK or not dr_near(rip_alpha, 0, 0.0001)
            or ab ~= CALL_OK or not dr_near(rip_bg_alpha, 0, 0.0001)
            or vr ~= CALL_OK or (rip_visible ~= true and rip_visible ~= false)
            or vbg ~= CALL_OK or (rip_bg_visible ~= true and rip_bg_visible ~= false) then
            release()
        end
    end
    if not released then
        local alpha = _effective_alpha(P._root, {})
        if _effective_visible(P._root, {}) ~= true
            or alpha == nil or alpha <= 0 then
            release()
        end
    end
    if released and t ~= nil
        and kyohud.settings.enable_hud_foundation == true then
        self:_apply_native_priority(t, true)
    end
end

function RT:_release_copr_replacement(clear_binding)
    local binding = self._copr_binding
    if not binding then return end
    local nv = kyohud.hud.native_visibility
    if binding.leased or binding.release_pending then
        if nv and type(nv.release) == "function" then
            nv:release(COPR_OWNER, binding.lease_gen)
        end
        if dr_pending(nv, COPR_OWNER, binding.lease_gen) then
            binding.release_pending = true
            binding.certified = false
            if clear_binding then binding.clear_on_release = true end
            return
        end
        binding.release_pending = false
        dr_restore_added(binding, nv)
        binding.leased = false
        binding.certified = false
        binding.lease_gen = nil
    end
    if clear_binding or binding.clear_on_release then
        binding.clear_on_release = nil
        if not dr_pending(nv, COPR_OWNER, binding.lease_gen) then
            self._copr_binding = nil
        end
    end
end

function RT:_copr_native_chain(mgr, n)
    if not mgr or type(mgr._teammate_panels) ~= "table" then return nil end
    if type(n) ~= "number" or n < 1 or n > COPR_CHILD_MAX then return nil end
    local entry = mgr._teammate_panels[h5_player_slot()]
    if type(entry) ~= "table" then return nil end
    local entry_panel = entry._panel
    if not entry_panel or not panel_alive(entry_panel) then return nil end
    local common = self._parent_panel
    if not common or not panel_alive(common) then return nil end
    if not dr_reaches_exposed(entry_panel, common) then return nil end

    local js, player_panel = safe_call(entry_panel, "child", "player")
    if js ~= CALL_OK or not player_panel or not panel_alive(player_panel) then return nil end
    local ps, player_parent = safe_call(player_panel, "parent")
    if ps ~= CALL_OK or player_parent ~= entry_panel then return nil end

    local rs, radial = safe_call(player_panel, "child", "radial_health_panel")
    if rs ~= CALL_OK or not radial or not panel_alive(radial) then return nil end
    local rp, radial_parent = safe_call(radial, "parent")
    if rp ~= CALL_OK or radial_parent ~= player_panel then return nil end

    local cs, copr = safe_call(radial, "child", "copr_overlay_panel")
    if cs ~= CALL_OK or not copr or not panel_alive(copr) then return nil end
    local cp, copr_parent = safe_call(copr, "parent")
    if cp ~= CALL_OK or copr_parent ~= radial then return nil end

    if not dr_active_container(entry_panel) or not dr_active_container(player_panel)
        or not dr_active_container(radial) or not dr_active_container(copr) then
        return nil
    end
    if not dr_reaches(copr, common) then return nil end

    -- Recreate the native population from the parent every update: the native
    -- panel clears and rebuilds exactly the numeric children 0..n-1.
    local leaves = {}
    for i = 0, n - 1 do
        local name = tostring(i)
        local ls, leaf = safe_call(copr, "child", name)
        if ls ~= CALL_OK or not leaf or not panel_alive(leaf) then return nil end
        local lp, leaf_parent = safe_call(leaf, "parent")
        if lp ~= CALL_OK or leaf_parent ~= copr then return nil end
        if not dr_leaf_readable(leaf) then return nil end
        if not dr_reaches(leaf, common) then return nil end
        leaves[i + 1] = leaf
    end

    -- The census is required and must contain exactly the individually
    -- qualified leaves, matched by object identity, with no duplicate or extra
    -- child. This holds for table and Diesel userdata leaves, and for both
    -- string-key maps and native arrays.
    local chs, children = safe_call(copr, "children")
    if chs ~= CALL_OK or type(children) ~= "table" then return nil end
    local leaf_set = {}
    for i = 1, n do
        leaf_set[leaves[i]] = true
    end
    local seen = {}
    local count = 0
    for _, child in pairs(children) do
        count = count + 1
        if count > n then return nil end
        if not leaf_set[child] then return nil end
        if seen[child] then return nil end
        seen[child] = true
    end
    if count ~= n then return nil end

    return {
        entry = entry,
        entry_panel = entry_panel,
        player = player_panel,
        radial = radial,
        copr = copr,
        leaves = leaves,
    }
end

function RT:_copr_source_state(mgr, chain, live)
    local P = kyohud.hud.player
    if not P or not P._root or not P._gauge or not panel_alive(P._root) then
        return nil, "unknown"
    end
    live = live or copr_live_source(P, mgr)
    if not live then return nil, "live_data_invalid" end
    if type(chain) ~= "table" or type(chain.leaves) ~= "table"
        or #chain.leaves ~= live.n then
        return nil, "native_count_mismatch"
    end
    if copr_receipt_stale(P, live) then return nil, "receipt_stale" end

    local gauge = P._gauge
    local health_state = gauge._health
    if type(health_state) ~= "table" or health_state.valid ~= true
        or not dr_near(health_state.current, live.health)
        or not dr_near(health_state.total, live.health_max)
        or not dr_near(health_state.ratio, live.health_ratio) then
        return nil, "rendered_data_mismatch"
    end
    local effects = gauge._health_effects
    local copr = type(effects) == "table" and effects.copr or nil
    if type(copr) ~= "table" or copr.known ~= true or copr.active ~= true
        or not dr_near(copr.static_damage_ratio, live.ratio) then
        return nil, "rendered_data_mismatch"
    end

    local common = self._parent_panel
    if not common or not panel_alive(common) then return nil, "owned_ancestry" end
    local prs, root_parent = safe_call(P._root, "parent")
    if prs ~= CALL_OK or root_parent ~= self._root_panel then
        return nil, "owned_ancestry"
    end
    if not dr_reaches_exposed(P._root, common) then
        return nil, "owned_exposure"
    end
    local gauge_root = gauge.root
    if not gauge_root or not panel_alive(gauge_root) then
        return nil, "owned_ancestry"
    end
    local grs, gauge_parent = safe_call(gauge_root, "parent")
    if grs ~= CALL_OK or gauge_parent ~= P._root then
        return nil, "owned_ancestry"
    end
    if not dr_reaches_exposed(gauge_root, common) then
        return nil, "owned_exposure"
    end
    local health_fill = gauge.health_fill
    if not health_fill or not panel_alive(health_fill) then
        return nil, "owned_ancestry"
    end
    local hrs, fill_parent = safe_call(health_fill, "parent")
    if hrs ~= CALL_OK or fill_parent ~= gauge_root then
        return nil, "owned_ancestry"
    end
    if not dr_reaches(health_fill, common) then return nil, "owned_ancestry" end
    local markers = gauge._copr_markers
    if type(markers) ~= "table" then return nil, "owned_ancestry" end
    for i = 1, #markers do
        local marker = markers[i]
        if not marker or not panel_alive(marker) then
            return nil, "owned_ancestry"
        end
        local mps, marker_parent = safe_call(marker, "parent")
        if mps ~= CALL_OK or marker_parent ~= health_fill then
            return nil, "owned_ancestry"
        end
        if not dr_reaches(marker, common) then return nil, "owned_ancestry" end
    end

    local vs, visible = safe_call(P._root, "visible")
    if vs ~= CALL_OK or visible ~= true then
        return nil, "owned_exposure"
    end
    if _effective_visible(P._root, {}) ~= true then
        return nil, "owned_exposure"
    end
    local alpha = _effective_alpha(P._root, {})
    if alpha == nil or alpha <= 0 then
        return nil, "owned_exposure"
    end

    return {ratio = live.ratio, n = live.n, health_ratio = live.health_ratio},
        "covered"
end

function RT:_copr_acquire(binding)
    local nv = kyohud.hud.native_visibility
    if not nv or type(nv.acquire) ~= "function" then return false end
    local leaves = binding.leaves
    if type(leaves) ~= "table" or #leaves < 1 or #leaves > COPR_CHILD_MAX then
        return false
    end
    local added = binding.added
    if not binding.leased or type(added) ~= "table" then
        added = {}
        if type(nv._whitelist) == "table" then
            for i = 1, #leaves do
                local leaf = leaves[i]
                local entry = nv._whitelist[leaf]
                if not entry then entry = {}; nv._whitelist[leaf] = entry end
                if entry.alpha ~= true then
                    added[leaf] = {alpha = entry.alpha}
                    entry.alpha = true
                end
            end
        end
    end
    local generation = binding.lease_gen
    if not binding.leased or generation == nil then
        self._copr_lease_generation = (self._copr_lease_generation or 0) + 1
        generation = self._copr_lease_generation
    end
    binding.lease_gen = generation
    binding.added = added
    binding.release_pending = true
    local requests = {}
    for i = 1, #leaves do
        requests[i] = {id = leaves[i], property = "alpha", value = 0}
    end
    local ok = nv:acquire(COPR_OWNER, generation, requests)
    if ok then
        binding.leased = true
        binding.release_pending = false
        return true
    end
    binding.leased = false
    binding.release_pending = true
    return false
end

function RT:_sync_copr_replacement_unprofiled(mgr)
    local P = kyohud.hud.player
    local settings = kyohud.settings
    if not mgr or kyohud.settings.enable_hud_foundation ~= true
        or settings.enable_player ~= true or is_vr()
        or self._disabled or self._freeflight or not self._mounted
        or not P or not P._mounted or P._manager ~= mgr then
        self:_release_copr_replacement(true)
        return
    end

    local binding = self._copr_binding
    if binding and binding.release_pending then
        self:_release_copr_replacement(false)
        binding = self._copr_binding
        if binding and binding.release_pending then return end
    end

    local panels = mgr._teammate_panels
    local entry = type(panels) == "table" and panels[h5_player_slot()] or nil
    local entry_panel = type(entry) == "table" and entry._panel or nil
    if binding and (binding.manager ~= mgr or binding.entry ~= entry
        or binding.entry_panel ~= entry_panel
        or binding.root_gen ~= self._generation) then
        self:_release_copr_replacement(true)
        binding = self._copr_binding
        if binding then return end
    end

    local live = copr_live_source(P, mgr)
    if not live then
        if binding then self:_release_copr_replacement(false) end
        return
    end

    local fresh_ok = P._update_ran_now == true
        and P._verify_ok_now == true and P._render_verified == true
    if not fresh_ok then
        local stale = copr_receipt_stale(P, live)
        local hidden = not dr_root_visible(P)
        if stale then
            local repair_ok, repaired = pcall(P._repair_and_certify, P, mgr)
            if not repair_ok or repaired ~= true then
                if binding then self:_release_copr_replacement(false) end
                return
            end
            live = copr_live_source(P, mgr)
            if not live then
                if binding then self:_release_copr_replacement(false) end
                return
            end
        elseif not (hidden and P._render_verified == true) then
            local verify_ok, verified = pcall(P.verify, P)
            if not verify_ok or verified ~= true then
                if binding then self:_release_copr_replacement(false) end
                return
            end
        end
    end

    if binding and (binding.source_unit ~= live.unit
        or binding.source_damage ~= live.damage) then
        -- The effective source object changed: restore every exact notch first,
        -- then reacquire only on a later certified update.
        self:_release_copr_replacement(true)
        return
    end
    local chain = self:_copr_native_chain(mgr, live.n)
    if not chain then
        if binding then self:_release_copr_replacement(false) end
        return
    end
    if binding then
        local same = binding.copr == chain.copr
            and binding.radial == chain.radial
            and binding.player == chain.player
            and binding.entry_panel == chain.entry_panel
            and type(binding.leaves) == "table"
            and #binding.leaves == #chain.leaves
        if same then
            for i = 1, #chain.leaves do
                if binding.leaves[i] ~= chain.leaves[i] then same = false; break end
            end
        end
        if not same then
            self:_release_copr_replacement(true)
            binding = self._copr_binding
            if binding then return end
        end
    end

    local state, reason = self:_copr_source_state(mgr, chain, live)
    if not state and reason == "owned_exposure"
        and P._render_verified == true and not dr_root_visible(P)
        and copr_live_source(P, mgr) ~= nil then
        local repair_ok, repaired = pcall(P._repair_and_certify, P, mgr)
        if repair_ok and repaired == true then
            state, reason = self:_copr_source_state(mgr, chain, live)
            chain = self:_copr_native_chain(mgr, live.n)
            if chain and binding then
                local same = binding.copr == chain.copr
                    and binding.radial == chain.radial
                    and binding.player == chain.player
                    and binding.entry_panel == chain.entry_panel
                    and type(binding.leaves) == "table"
                    and #binding.leaves == #chain.leaves
                if same then
                    for i = 1, #chain.leaves do
                        if binding.leaves[i] ~= chain.leaves[i] then same = false; break end
                    end
                end
                if not same then state = nil end
            elseif not chain then
                state = nil
            end
        end
    end
    if not state then
        if binding then self:_release_copr_replacement(false) end
        return
    end

    if not binding then
        binding = {
            manager = mgr,
            entry = entry,
            entry_panel = chain.entry_panel,
            root_gen = self._generation,
            player = chain.player,
            radial = chain.radial,
            copr = chain.copr,
            leaves = chain.leaves,
            source_unit = live.unit,
            source_damage = live.damage,
            leased = false,
            certified = false,
        }
        self._copr_binding = binding
    else
        binding.leaves = chain.leaves
        binding.copr = chain.copr
        binding.player = chain.player
        binding.radial = chain.radial
        binding.entry_panel = chain.entry_panel
    end
    binding.certified = false

    if not self:_copr_acquire(binding) then
        self:_release_copr_replacement(false)
        return
    end
    -- The lease is only authorized for a render that still certifies after the
    -- native alpha writes; otherwise fail closed and let priority take over.
    local verify_ok, verified = pcall(P.verify, P)
    if not verify_ok or verified ~= true then
        self:_release_copr_replacement(false)
        return
    end
    binding.certified = true
end

function RT:_copr_replacement_post_priority_unprofiled(t)
    local binding = self._copr_binding
    if not binding or not binding.leased then return end
    local released = false
    local function release()
        if released then return end
        released = true
        self:_release_copr_replacement(false)
    end
    local P = kyohud.hud.player
    if not P or not P._root or not panel_alive(P._root) then
        release()
    else
        local vs, visible = safe_call(P._root, "visible")
        if vs ~= CALL_OK or visible ~= true then
            release()
        end
    end
    if not released then
        local copr = binding.copr
        local cp, copr_parent = safe_call(copr, "parent")
        local leaves = binding.leaves
        if cp ~= CALL_OK or copr_parent ~= binding.radial
            or type(leaves) ~= "table"
            or #leaves < 1 or #leaves > COPR_CHILD_MAX then
            release()
        else
            for i = 1, #leaves do
                local leaf = leaves[i]
                local ap, leaf_parent = safe_call(leaf, "parent")
                local aa, alpha = safe_call(leaf, "alpha")
                local av, vis = safe_call(leaf, "visible")
                if ap ~= CALL_OK or leaf_parent ~= copr
                    or aa ~= CALL_OK or not dr_near(alpha, 0, 0.0001)
                    or av ~= CALL_OK or (vis ~= true and vis ~= false) then
                    release()
                    break
                end
            end
        end
    end
    if not released then
        local alpha = _effective_alpha(P._root, {})
        if _effective_visible(P._root, {}) ~= true
            or alpha == nil or alpha <= 0 then
            release()
        end
    end
    if released and t ~= nil
        and kyohud.settings.enable_hud_foundation == true then
        self:_apply_native_priority(t, true)
    end
end

function RT:_hacker_active_allowed(mgr, E)
    if kyohud.settings.enable_hud_foundation ~= true
        or kyohud.settings.enable_equipment ~= true then return false end
    if is_vr() or self._disabled == true or self._freeflight == true
        or self._mounted ~= true then return false end
    if not mgr or not managers or managers.hud ~= mgr then return false end
    if type(E) ~= "table" or E._mounted ~= true
        or E._manager ~= mgr or E._hud_manager ~= mgr then return false end
    if not E._root or not panel_alive(E._root) then return false end
    return true
end

function RT:_hacker_native_bounds(panel)
    if not panel_alive(panel) then return nil end
    local x, y, w, h = h5_flash_bounds(panel)
    if x == nil or w <= 0 or h <= 0 then return nil end
    return x, y, w, h
end

function RT:_hacker_native_color(panel)
    local cs, color = safe_call(panel, "color")
    if cs ~= CALL_OK or color == nil then return nil end
    local ok, r, g, b, a = pcall(function()
        return color.r, color.g, color.b, color.a
    end)
    if not ok then return nil end
    if not finite(r) or r < 0 or r > 1 then return nil end
    if not finite(g) or not finite(b) or not finite(a) then return nil end
    return r, g, b, a
end

function RT:_hacker_foreign_conflict(leaves)
    local nv = kyohud.hud.native_visibility
    if not nv or type(nv._entries) ~= "table" then return false end
    local owner = self._h5_owner .. "_" .. H5_HACKER_ACTIVE_GROUP
    for i = 1, 2 do
        local leaf = leaves[i]
        for _, entry in ipairs(nv._entries) do
            if entry.object == leaf and entry.property == "visible"
                and entry.owner ~= owner then
                return true
            end
        end
    end
    return false
end

local function h5_idstring_key(value)
    if value == nil then return nil end
    if type(value) == "string" then return value end
    local ok, key = pcall(function() return value:key() end)
    if ok and key ~= nil then return key end
    return nil
end

local function h5_texture_matches(actual, expected)
    if type(expected) ~= "string" or expected == "" then return false end
    if type(actual) == "string" then
        if actual == expected then return true end
        local ok_actual, actual_id = pcall(Idstring, actual)
        local ok_expected, expected_id = pcall(Idstring, expected)
        if not ok_actual or not ok_expected
            or actual_id == nil or expected_id == nil then return false end
        local actual_key = h5_idstring_key(actual_id)
        local expected_key = h5_idstring_key(expected_id)
        return actual_key ~= nil and actual_key == expected_key
    end
    local ok_expected, expected_id = pcall(Idstring, expected)
    if not ok_expected or expected_id == nil then return false end
    local actual_key = h5_idstring_key(actual)
    local expected_key = h5_idstring_key(expected_id)
    return actual_key ~= nil and actual_key == expected_key
end

-- The terminal path trusts a render verifier only while it is still the exact
-- aggregate wrapper installed by the module itself. A replaced or missing
-- verifier fails closed; it is never called to fabricate a proof.
local function h5_equipment_verifier_identity(E)
    if type(E) ~= "table" then return false end
    local wrappers = E._residual_phase_wrappers
    if type(wrappers) ~= "table" then return false end
    local installed = wrappers.verify
    if type(installed) ~= "function" then return false end
    return type(E.verify) == "function" and E.verify == installed
end

local function h5_player_verifier_identity(P)
    if type(P) ~= "table" then return false end
    local installed = P._residual_phase_player_verify
    if type(installed) ~= "function" then return false end
    return type(P.verify) == "function" and P.verify == installed
end

-- Read-only terminal Kingpin proof shared by the priority scanner and the
-- post-priority check. It never presents, repairs, acquires or releases anything:
-- it only re-proves the terminal source, the exact native subtree/census, the
-- last published meter ratio and icon, the held two-leaf lease and the fresh
-- inactive P/E renders. Any uncertainty is false.
function RT:_terminal_proof(binding, allow_unset)
    if type(binding) ~= "table" then return false end
    if binding.terminal ~= true and allow_unset ~= true then return false end
    if binding.leased ~= true or binding.release_pending == true then return false end
    if binding.source_kind ~= KINGPIN_LOCAL_SOURCE then return false end
    if type(binding.leaves) ~= "table" or #binding.leaves ~= 2 then return false end
    local mgr = self._manager
    local E = kyohud.hud.equipment
    if not self:_hacker_active_allowed(mgr, E) then return false end
    if not h5_equipment_verifier_identity(E) then return false end
    if binding.manager ~= mgr or binding.root_gen ~= self._generation then return false end
    if binding.entry_panel == nil or not panel_alive(binding.entry_panel) then return false end
    if kyohud.settings.enable_player ~= true then return false end
    local src_ok, source = pcall(E.get_kingpin_terminal_source, E)
    if not src_ok or type(source) ~= "table"
        or source.kind ~= KINGPIN_TERMINAL_SOURCE
        or source.active ~= false then return false end
    if binding.source_event_id ~= source.event_id then return false end
    if self._hacker_active_conflict_event == source.event_id
        and h5_same_targets(self._hacker_active_conflict_targets, binding.leaves) then
        return false
    end
    if self:_hacker_foreign_conflict(binding.leaves) then return false end
    local state = self._h5_groups and self._h5_groups[H5_HACKER_ACTIVE_GROUP]
    if not state or state._release_pending == true
        or state.property ~= "visible"
        or state.generation ~= binding.lease_gen
        or not h5_same_targets(state.targets, binding.leaves) then
        return false
    end
    local panels = mgr._teammate_panels
    local entry = type(panels) == "table" and panels[h5_player_slot()] or nil
    if type(entry) ~= "table" or entry._ai == true then return false end
    if entry ~= binding.entry then return false end
    local entry_panel = entry._panel
    if entry_panel ~= binding.entry_panel or not panel_alive(entry_panel) then return false end
    local common = self._parent_panel
    if not common or not panel_alive(common) then return false end
    if not dr_reaches_exposed(entry_panel, common) then return false end
    local ps, player = safe_call(entry_panel, "child", "player")
    if ps ~= CALL_OK or player ~= binding.player or not panel_alive(player) then return false end
    local pp, player_parent = safe_call(player, "parent")
    if pp ~= CALL_OK or player_parent ~= entry_panel then return false end
    local rs, radial = safe_call(player, "child", "radial_health_panel")
    if rs ~= CALL_OK or radial ~= binding.radial or not panel_alive(radial) then return false end
    local rp, radial_parent = safe_call(radial, "parent")
    if rp ~= CALL_OK or radial_parent ~= player then return false end
    local abs, parent = safe_call(radial, "child", "radial_ability")
    if abs ~= CALL_OK or parent ~= binding.parent or not panel_alive(parent) then return false end
    local ap, ability_parent = safe_call(parent, "parent")
    if ap ~= CALL_OK or ability_parent ~= radial then return false end
    local ms, meter = safe_call(parent, "child", "ability_meter")
    local is, icon = safe_call(parent, "child", "ability_icon")
    if ms ~= CALL_OK or is ~= CALL_OK or meter ~= binding.leaves[1]
        or icon ~= binding.leaves[2]
        or not panel_alive(meter) or not panel_alive(icon) then return false end
    local mp, meter_parent = safe_call(meter, "parent")
    local ip, icon_parent = safe_call(icon, "parent")
    if mp ~= CALL_OK or meter_parent ~= parent then return false end
    if ip ~= CALL_OK or icon_parent ~= parent then return false end
    local chs, children = safe_call(parent, "children")
    if chs ~= CALL_OK or type(children) ~= "table" then return false end
    local count = 0
    local seen = {}
    for _, child in pairs(children) do
        count = count + 1
        if count > 2 then return false end
        if child ~= meter and child ~= icon then return false end
        if seen[child] then return false end
        seen[child] = true
    end
    if count ~= 2 then return false end
    if not dr_active_container(entry_panel) or not dr_active_container(player)
        or not dr_active_container(radial) or not dr_active_container(parent) then
        return false
    end
    if not dr_reaches(parent, common) or not dr_reaches(meter, common)
        or not dr_reaches(icon, common) then return false end
    if not self:_hacker_native_bounds(parent) then return false end
    if not self:_hacker_native_bounds(meter) then return false end
    if not self:_hacker_native_bounds(icon) then return false end
    local pv, parent_visible = safe_call(parent, "visible")
    if pv ~= CALL_OK or parent_visible ~= true then return false end
    local pa, parent_alpha = safe_call(parent, "alpha")
    if pa ~= CALL_OK or not finite(parent_alpha) or parent_alpha <= 0 then return false end
    local published_remaining = source.published_remaining
    local published_total = source.published_total
    if not finite(published_remaining) or not finite(published_total)
        or published_remaining <= 0 or published_total <= 0 then return false end
    if published_remaining > published_total + 0.001 then return false end
    local ratio = published_remaining / published_total
    local meter_r, meter_g, meter_b, meter_a = self:_hacker_native_color(meter)
    if not finite(meter_r) or math.abs(meter_r - ratio) > 0.001 then return false end
    if not finite(meter_g) or math.abs(meter_g - 1) > 0.001 then return false end
    if not finite(meter_b) or math.abs(meter_b - 1) > 0.001 then return false end
    if not finite(meter_a) or math.abs(meter_a - 1) > 0.001 or meter_a <= 0 then
        return false
    end
    local tex_ok, texture = safe_call(icon, "texture_name")
    local expected_texture = type(source.icon) == "table" and source.icon.texture or nil
    if tex_ok ~= CALL_OK or not h5_texture_matches(texture, expected_texture) then
        return false
    end
    for i = 1, 2 do
        local leaf = binding.leaves[i]
        local v_ok, visible = safe_call(leaf, "visible")
        if v_ok ~= CALL_OK or visible ~= false then return false end
        if self:_h5_group_holds_visible(H5_HACKER_ACTIVE_GROUP, leaf) ~= true then
            return false
        end
        local leaf_alpha = _effective_alpha(leaf, {})
        if not finite(leaf_alpha) or leaf_alpha <= 0 then return false end
    end
    local P = kyohud.hud.player
    if type(P) ~= "table" or P._mounted ~= true or P._manager ~= mgr
        or not P._root or not panel_alive(P._root) then return false end
    if not h5_player_verifier_identity(P) then return false end
    local p_verify_ok, p_verified = pcall(P.verify, P)
    if not p_verify_ok or p_verified ~= true then return false end
    if _effective_visible(P._root, {}) ~= true then return false end
    local p_alpha = _effective_alpha(P._root, {})
    if p_alpha == nil or p_alpha <= 0 then return false end
    if not E._root or not panel_alive(E._root) then return false end
    if _effective_visible(E._root, {}) ~= true then return false end
    local e_alpha = _effective_alpha(E._root, {})
    if e_alpha == nil or e_alpha <= 0 then return false end
    local e_verify_ok, e_verified = pcall(E._verify_kingpin_terminal, E, source)
    if not e_verify_ok or e_verified ~= true then return false end
    return true
end

function RT:_hacker_active_chain()
    local mgr = self._manager
    local E = kyohud.hud.equipment
    if not self:_hacker_active_allowed(mgr, E) then return nil end
    local source = E:get_local_ability_activity_source()
    if type(source) ~= "table" or source.active ~= true then return nil end
    local source_kind = source.kind
    if source.manager ~= mgr or source.hud_manager ~= mgr then return nil end
    if source.generation ~= E._source_generation then return nil end
    local panels = mgr._teammate_panels
    local entry = type(panels) == "table" and panels[h5_player_slot()] or nil
    if type(entry) ~= "table" or entry._ai == true then return nil end
    local entry_panel = entry._panel
    if not entry_panel or not panel_alive(entry_panel) then return nil end
    local common = self._parent_panel
    if not common or not panel_alive(common) then return nil end
    if not dr_reaches_exposed(entry_panel, common) then return nil end
    local ps, player = safe_call(entry_panel, "child", "player")
    if ps ~= CALL_OK or not player or not panel_alive(player) then return nil end
    local pp, player_parent = safe_call(player, "parent")
    if pp ~= CALL_OK or player_parent ~= entry_panel then return nil end
    local rs, radial = safe_call(player, "child", "radial_health_panel")
    if rs ~= CALL_OK or not radial or not panel_alive(radial) then return nil end
    local rp, radial_parent = safe_call(radial, "parent")
    if rp ~= CALL_OK or radial_parent ~= player then return nil end
    local abs, parent = safe_call(radial, "child", "radial_ability")
    if abs ~= CALL_OK or not parent or not panel_alive(parent) then return nil end
    local ap, parent_parent = safe_call(parent, "parent")
    if ap ~= CALL_OK or parent_parent ~= radial then return nil end
    local ms, meter = safe_call(parent, "child", "ability_meter")
    local is, icon = safe_call(parent, "child", "ability_icon")
    if ms ~= CALL_OK or is ~= CALL_OK or not meter or not icon
        or not panel_alive(meter) or not panel_alive(icon) then return nil end
    local mp, meter_parent = safe_call(meter, "parent")
    local ip, icon_parent = safe_call(icon, "parent")
    if mp ~= CALL_OK or meter_parent ~= parent then return nil end
    if ip ~= CALL_OK or icon_parent ~= parent then return nil end
    local chs, children = safe_call(parent, "children")
    if chs ~= CALL_OK or type(children) ~= "table" then return nil end
    local count = 0
    local seen = {}
    for _, child in pairs(children) do
        count = count + 1
        if count > 2 then return nil end
        if child ~= meter and child ~= icon then return nil end
        if seen[child] then return nil end
        seen[child] = true
    end
    if count ~= 2 then return nil end
    if not dr_active_container(entry_panel) or not dr_active_container(player)
        or not dr_active_container(radial) or not dr_active_container(parent) then
        return nil
    end
    if not dr_reaches(parent, common) or not dr_reaches(meter, common)
        or not dr_reaches(icon, common) then return nil end
    if not self:_hacker_native_bounds(parent) then return nil end
    if not self:_hacker_native_bounds(meter) then return nil end
    if not self:_hacker_native_bounds(icon) then return nil end
    local meter_r, meter_g, meter_b, meter_a = self:_hacker_native_color(meter)
    if not finite(meter_r) then return nil end
    if source_kind == "chico_injector_local" then
        local progress = source.remaining / source.duration
        if not finite(progress) or progress < 0 or progress > 1 then return nil end
        local ratio_ok = math.abs(meter_r - progress) <= .001
            and math.abs(meter_g - 1) <= .001
        if not ratio_ok or math.abs(meter_b - 1) > .001
            or math.abs(meter_a - 1) > .001 or meter_a <= 0 then
            return nil
        end
        local tex_ok, texture = safe_call(icon, "texture_name")
        local expected_texture = type(source.icon) == "table" and source.icon.texture or nil
        if tex_ok ~= CALL_OK or not h5_texture_matches(texture, expected_texture) then
            return nil
        end
    end
    local defer_full_verify = false
    if source_kind == KINGPIN_LOCAL_SOURCE
        and h5_equipment_verifier_identity(E) then
        local exposed_ok, exposed = pcall(E._hacker_root_exposed, E)
        defer_full_verify = exposed_ok and exposed == true
    end
    -- Defer the initial full render check to the FINAL full check below, which
    -- runs on a fresh source read; this reuses no cached result or prior proof.
    if not defer_full_verify then
        local verify_ok, verified = pcall(E._verify_local_ability_activity, E, source)
        if not verify_ok or verified ~= true then
            local recover = false
            if E._update_ran_now == true then
                local exposed_ok, exposed = pcall(E._hacker_root_exposed, E)
                recover = exposed_ok and exposed == false
            end
            if not recover then return nil end
            local prep_ok, prepared = pcall(E.prepare_local_ability_activity_event, E)
            if not prep_ok or prepared ~= true then return nil end
        end
    end
    local fresh = E:get_local_ability_activity_source()
    if type(fresh) ~= "table" or fresh.event_id ~= source.event_id
        or fresh.kind ~= source_kind then return nil end
    local fresh_ok, fresh_verified = pcall(E._verify_local_ability_activity, E, fresh)
    if not fresh_ok or fresh_verified ~= true then return nil end
    return {
        entry = entry,
        entry_panel = entry_panel,
        player = player,
        radial = radial,
        parent = parent,
        meter = meter,
        icon = icon,
        leaves = {meter, icon},
        source = fresh,
    }
end

function RT:_release_hacker_active(clear_binding)
    local binding = self._hacker_active_binding
    local trace_kingpin = type(binding) == "table"
        and binding.source_kind == "chico_injector_local"
        and (binding.leased == true or binding.release_pending == true)
    if trace_kingpin then
        pcall(self._kingpin_transition, self, "release_before")
    end
    local released = self:_h5_release_group(H5_HACKER_ACTIVE_GROUP)
    if not binding then return released end
    if not released then
        binding.release_pending = true
        binding.certified = false
        binding.terminal = nil
        binding.terminal_event_id = nil
        binding.terminal_receipt = nil
        if clear_binding then binding.clear_on_release = true end
        if trace_kingpin then
            pcall(self._kingpin_transition, self, "release_after", "restore_failed")
        end
        return false
    end
    binding.leased = false
    binding.lease_gen = nil
    binding.certified = false
    binding.release_pending = false
    binding.terminal = nil
    binding.terminal_event_id = nil
    binding.terminal_receipt = nil
    if clear_binding or binding.clear_on_release then
        binding.clear_on_release = nil
        self._hacker_active_binding = nil
    end
    if trace_kingpin then
        pcall(self._kingpin_transition, self, "release_after")
    end
    return true
end

function RT:_acquire_hacker_active(mgr, chain)
    if type(chain) ~= "table" or type(chain.leaves) ~= "table"
        or #chain.leaves ~= 2 then return false end
    local binding = self._hacker_active_binding
    if binding and binding.release_pending == true then
        self:_release_hacker_active(false)
        binding = self._hacker_active_binding
        if binding and binding.release_pending == true then return false end
    end
    if self._hacker_active_conflict_event == chain.source.event_id
        and h5_same_targets(self._hacker_active_conflict_targets, chain.leaves) then
        return false
    end
    if self:_hacker_foreign_conflict(chain.leaves) then
        self._hacker_active_conflict_event = chain.source.event_id
        self._hacker_active_conflict_targets = {chain.leaves[1], chain.leaves[2]}
        self:_release_hacker_active(true)
        return false
    end
    self:_h5_acquire_group(H5_HACKER_ACTIVE_GROUP, chain.leaves, {
        entry_panel = chain.entry_panel,
        manager = mgr,
        root_gen = self._generation,
    }, "visible")
    local state = self._h5_groups and self._h5_groups[H5_HACKER_ACTIVE_GROUP]
    local lease_gen = state and state.generation or nil
    local acquired = state ~= nil and state._release_pending ~= true
        and state.property == "visible"
        and h5_same_targets(state.targets, chain.leaves)
    if acquired then
        for i = 1, 2 do
            local leaf = chain.leaves[i]
            local v_ok, visible = safe_call(leaf, "visible")
            local held = false
            if v_ok == CALL_OK and visible == false then
                held = self:_h5_group_holds_visible(H5_HACKER_ACTIVE_GROUP, leaf)
            end
            if v_ok ~= CALL_OK or visible ~= false or held ~= true then
                acquired = false
                break
            end
        end
    end
    if not acquired then
        self:_release_hacker_active(true)
        return false
    end
    self._hacker_active_conflict_event = nil
    self._hacker_active_conflict_targets = nil
    binding = self._hacker_active_binding
    if not binding or binding.source_event_id ~= chain.source.event_id
        or binding.source_kind ~= chain.source.kind
        or binding.lease_gen ~= lease_gen
        or binding.entry_panel ~= chain.entry_panel
        or binding.parent ~= chain.parent then
        binding = {
            manager = mgr,
            entry = chain.entry,
            entry_panel = chain.entry_panel,
            root_gen = self._generation,
            player = chain.player,
            radial = chain.radial,
            parent = chain.parent,
            leaves = {chain.leaves[1], chain.leaves[2]},
            source_event_id = chain.source.event_id,
            source_kind = chain.source.kind,
            lease_gen = lease_gen,
            leased = true,
            certified = true,
            release_pending = false,
            clear_on_release = false,
        }
        self._hacker_active_binding = binding
    else
        binding.manager = mgr
        binding.entry = chain.entry
        binding.entry_panel = chain.entry_panel
        binding.root_gen = self._generation
        binding.player = chain.player
        binding.radial = chain.radial
        binding.parent = chain.parent
        binding.leaves = {chain.leaves[1], chain.leaves[2]}
        binding.lease_gen = lease_gen
        binding.leased = true
        binding.certified = true
        binding.release_pending = false
    end
    return true
end

-- Qualified Kingpin terminal continuation. It can only continue the already-held
-- exact local binding/group/lease; it never acquires a missing lease or
-- reacquires after release. The inactive owned equipment is prepared and both
-- renders are freshly certified before the terminal receipt is marked.
function RT:_continue_kingpin_terminal(mgr, E)
    local binding = self._hacker_active_binding
    if type(binding) ~= "table" or binding.leased ~= true
        or binding.release_pending == true then return false end
    if binding.source_kind ~= KINGPIN_LOCAL_SOURCE then return false end
    if type(binding.leaves) ~= "table" or #binding.leaves ~= 2 then return false end
    if not self:_hacker_active_allowed(mgr, E) then return false end
    if binding.manager ~= mgr or binding.root_gen ~= self._generation then return false end
    if kyohud.settings.enable_player ~= true then return false end
    local src_ok, source = pcall(E.get_kingpin_terminal_source, E)
    if not src_ok or type(source) ~= "table"
        or source.kind ~= KINGPIN_TERMINAL_SOURCE then return false end
    if source.event_id ~= binding.source_event_id then return false end
    if self._hacker_active_conflict_event == source.event_id
        and h5_same_targets(self._hacker_active_conflict_targets, binding.leaves) then
        return false
    end
    if self:_hacker_foreign_conflict(binding.leaves) then
        self._hacker_active_conflict_event = source.event_id
        self._hacker_active_conflict_targets = {binding.leaves[1], binding.leaves[2]}
        return false
    end
    if binding.terminal ~= true then
        local P = kyohud.hud.player
        if type(P) ~= "table" or P._mounted ~= true or P._manager ~= mgr
            or not P._root or not panel_alive(P._root) then return false end
        if not E._root or not panel_alive(E._root) then return false end
        if not h5_player_verifier_identity(P) then return false end
        if not h5_equipment_verifier_identity(E) then return false end
        -- No P repair/show here: a render loss must release, not be hidden by a
        -- repair that makes the terminal qualification pass.
        local p_ok, p_verified = pcall(P.verify, P)
        if not p_ok or p_verified ~= true then return false end
        if _effective_visible(P._root, {}) ~= true then return false end
        local p_alpha = _effective_alpha(P._root, {})
        if p_alpha == nil or p_alpha <= 0 then return false end
        local e_ok, e_verified = pcall(E.verify, E)
        if not e_ok or e_verified ~= true then return false end
        if _effective_visible(E._root, {}) ~= true then return false end
        local e_alpha = _effective_alpha(E._root, {})
        if e_alpha == nil or e_alpha <= 0 then return false end
        local prep_ok, prepared = pcall(E._prepare_kingpin_terminal_event, E, source)
        if not prep_ok or prepared ~= true then return false end
        local fresh_ok, fresh = pcall(E.get_kingpin_terminal_source, E)
        if not fresh_ok or type(fresh) ~= "table"
            or fresh.kind ~= KINGPIN_TERMINAL_SOURCE
            or fresh.event_id ~= source.event_id then return false end
        source = fresh
    end
    local proof_ok, proved = pcall(self._terminal_proof, self, binding,
        binding.terminal ~= true)
    if not proof_ok or proved ~= true then return false end
    if binding.terminal ~= true then
        binding.terminal = true
        binding.terminal_event_id = source.event_id
        binding.terminal_receipt = {
            event_id = source.event_id,
            generation = source.generation,
            lease_gen = binding.lease_gen,
            expire_time = source.expire_time,
            published_remaining = source.published_remaining,
            published_total = source.published_total,
        }
        binding.certified = true
        pcall(self._kingpin_transition, self, "terminal_hold", "qualified", {
            remaining = source.published_remaining,
            published_total = source.published_total,
        })
    end
    return true
end

function RT:_sync_hacker_active()
    local mgr = self._manager
    local E = kyohud.hud.equipment
    if not self:_hacker_active_allowed(mgr, E) then
        self:_release_hacker_active(true)
        self._hacker_active_conflict_event = nil
        self._hacker_active_conflict_targets = nil
        return false
    end
    local binding = self._hacker_active_binding
    if binding and binding.release_pending == true then
        self:_release_hacker_active(false)
        binding = self._hacker_active_binding
        if binding and binding.release_pending == true then return false end
    end
    local source = E:get_local_ability_activity_source()
    if type(source) ~= "table" then
        if self:_continue_kingpin_terminal(mgr, E) then return true end
        self:_release_hacker_active(true)
        return false
    end
    if binding and binding.terminal == true then
        binding.terminal = nil
        binding.terminal_event_id = nil
        binding.terminal_receipt = nil
    end
    if self._hacker_active_conflict_event ~= source.event_id then
        self._hacker_active_conflict_event = nil
        self._hacker_active_conflict_targets = nil
    end
    if binding and binding.leased == true and source.active == true
        and binding.source_kind ~= source.kind then
        self:_release_hacker_active(true)
        binding = self._hacker_active_binding
    end
    if binding and binding.leased == true and source.active == true
        and binding.source_event_id == source.event_id
        and binding.source_kind == source.kind
        and type(binding.leaves) == "table" and #binding.leaves == 2 then
        local state = self._h5_groups and self._h5_groups[H5_HACKER_ACTIVE_GROUP]
        local lost = state == nil or state._release_pending == true
            or state.property ~= "visible"
            or state.generation ~= binding.lease_gen
            or not h5_same_targets(state.targets, binding.leaves)
        if not lost then
            for i = 1, 2 do
                local leaf = binding.leaves[i]
                local v_ok, visible = safe_call(leaf, "visible")
                if v_ok ~= CALL_OK or visible ~= false
                    or self:_h5_group_holds_visible(H5_HACKER_ACTIVE_GROUP, leaf) ~= true then
                    lost = true
                    break
                end
            end
        end
        if lost then
            self._hacker_active_conflict_event = binding.source_event_id
            self._hacker_active_conflict_targets = {binding.leaves[1], binding.leaves[2]}
            self:_release_hacker_active(true)
            return false
        end
    end
    local chain = self:_hacker_active_chain()
    if not chain then
        self:_release_hacker_active(true)
        return false
    end
    return self:_acquire_hacker_active(mgr, chain)
end

function RT:_hacker_active_post_priority(t)
    local binding = self._hacker_active_binding
    if not binding or binding.leased ~= true then return end
    local mgr = self._manager
    local E = kyohud.hud.equipment
    local ok = false
    local terminal_hold = false
    if binding.terminal == true then
        local proof_ok, proved = pcall(self._terminal_proof, self, binding)
        terminal_hold = proof_ok and proved == true
        ok = terminal_hold
    elseif self:_hacker_active_allowed(mgr, E) then
        local src_ok, source = pcall(E.get_local_ability_activity_source, E)
        if src_ok and type(source) == "table"
            and source.event_id == binding.source_event_id
            and source.kind == binding.source_kind then
            local verify_ok, verified = pcall(E._verify_local_ability_activity, E, source)
            local fresh_ok, fresh = pcall(E.get_local_ability_activity_source, E)
            ok = verify_ok and verified == true
                and fresh_ok and type(fresh) == "table"
                and fresh.event_id == source.event_id
                and fresh.kind == source.kind
                and _effective_visible(E._root, {}) == true
                and (_effective_alpha(E._root, {}) or 0) > 0
        end
    end
    if terminal_hold then return end
    if ok then
        local state = self._h5_groups and self._h5_groups[H5_HACKER_ACTIVE_GROUP]
        if state and state._release_pending ~= true
            and state.generation == binding.lease_gen
            and state.property == "visible"
            and h5_same_targets(state.targets, binding.leaves) then
            local held = true
            for i = 1, 2 do
                local leaf = binding.leaves[i]
                local v_ok, visible = safe_call(leaf, "visible")
                if v_ok ~= CALL_OK or visible ~= false
                    or self:_h5_group_holds_visible(H5_HACKER_ACTIVE_GROUP, leaf) ~= true then
                    held = false
                    break
                end
            end
            if held then return end
        end
    end
    self:_release_hacker_active(true)
    if t ~= nil and kyohud.settings.enable_hud_foundation == true then
        self:_apply_native_priority(t, true)
    end
end

local function crew_deck_clamp01(v)
    if not finite(v) then return 1 end
    if v < 0 then return 0 end
    if v > 1 then return 1 end
    return v
end

-- Read one remote native leaf without mutating it. The color red channel is the
-- native radial progress for meter-shaped leaves; it stays readable while the
-- alpha lease hides the leaf.
local function crew_deck_leaf_read(leaf)
    if not leaf or not panel_alive(leaf) then return nil end
    local vs, visible = safe_call(leaf, "visible")
    local as, alpha = safe_call(leaf, "alpha")
    if vs ~= CALL_OK or as ~= CALL_OK then return nil end
    local ratio
    local cs, color = safe_call(leaf, "color")
    if cs == CALL_OK and color ~= nil then
        local ok, r = pcall(function() return color.r end)
        if ok and finite(r) and r >= 0 and r <= 1 then ratio = r end
    end
    return {
        visible = visible == true,
        alpha = finite(alpha) and alpha or 0,
        ratio = ratio,
    }
end

local function crew_deck_leaf_active(state, held)
    if type(state) ~= "table" then return false end
    if state.visible ~= true then return false end
    if finite(state.alpha) and state.alpha > 0 then return true end
    return held == true
end

local function crew_deck_held(binding, leaf)
    if type(binding) ~= "table" or binding.leased ~= true
        or type(binding.leaves) ~= "table" or leaf == nil then
        return false
    end
    for i = 1, #binding.leaves do
        if binding.leaves[i] == leaf then return true end
    end
    return false
end

local function crew_deck_child_fresh(parent, name)
    if not parent or not panel_alive(parent) then return nil end
    local st, child = safe_call(parent, "child", name)
    if st ~= CALL_OK or not child or not panel_alive(child) then return nil end
    local ps, immediate = safe_call(child, "parent")
    if ps ~= CALL_OK or immediate ~= parent then return nil end
    return child
end

local function crew_deck_push(leaves, seen, leaf)
    if leaf == nil or not panel_alive(leaf) then return false end
    if seen[leaf] then return false end
    seen[leaf] = true
    leaves[#leaves + 1] = leaf
    return true
end

function RT:_release_crew_perkdeck(slot)
    local decks = self._crew_perkdeck
    if not decks then return end
    if slot ~= nil then
        local binding = decks[slot]
        if binding then
            if binding.group_key then self:_h5_release_group(binding.group_key) end
            decks[slot] = nil
        end
        return
    end
    for key, binding in pairs(decks) do
        if binding and binding.group_key then
            self:_h5_release_group(binding.group_key)
        end
        decks[key] = nil
    end
    self._crew_perkdeck = nil
end

-- Port the local per-deck H5 replacement subsystems to every remote crew card.
-- Native leaves are read first, the owned deck primitives are rendered and
-- certified on the exact card, and only then is their alpha leased through the
-- H5 group. The priority guard is unchanged: it still inspects the same leaves,
-- but a certified alpha-0 lease makes them non-blocking exactly like the local
-- delayed/reserve/COPR groups. Any proof failure releases and fails closed.
function RT:_sync_crew_perkdeck(mgr, t)
    if t ~= nil and self._crew_deck_last_t == t then return end
    if t ~= nil then self._crew_deck_last_t = t end
    local C = kyohud.hud.crew
    local settings = kyohud.settings
    if not mgr or settings.enable_hud_foundation ~= true
        or settings.enable_crew ~= true or is_vr()
        or self._disabled or self._freeflight or not self._mounted
        or not C or C._mounted ~= true or C._manager ~= mgr then
        self:_release_crew_perkdeck()
        return
    end
    local panels = mgr._teammate_panels
    if type(panels) ~= "table" then
        self:_release_crew_perkdeck()
        return
    end
    for slot = 1, CREW_DECK_MAX do
        local card = C._cards and C._cards[slot]
        local binding = self._crew_perkdeck and self._crew_perkdeck[slot] or nil
        local group_key = CREW_DECK_GROUP_PREFIX .. slot
        local card_ready = false
        if card ~= nil and type(card._all_live) == "function" then
            local live_ok, live_now = pcall(card._all_live, card)
            card_ready = live_ok and live_now == true
        end
        -- The local player's dedicated panel is owned by the local per-deck
        -- subsystems and is never treated as a remote crew slot.
        if slot == h5_player_slot() then card_ready = false end
        if not card_ready then
            if binding then self:_release_crew_perkdeck(slot) end
            if card and type(card.set_perkdeck) == "function" then
                card:set_perkdeck(nil)
                pcall(card._render_perkdeck, card)
            end
        else
            local entry = panels[slot]
            local entry_panel = type(entry) == "table" and entry._panel or nil
            local player_panel
            local radial
            if entry_panel and panel_alive(entry_panel) then
                player_panel = h5_child_verified(entry_panel, "player")
                if player_panel then
                    radial = h5_child_verified(player_panel, "radial_health_panel")
                end
            end
            local data = {active = false}
            local leaves = {}
            local seen = {}
            -- Only a positively identified remote human is replaced. Unknown
            -- occupancy (nil AI flag) and bots keep the native leaf untouched,
            -- so the existing fail-closed guard behavior is preserved.
            local eligible = type(entry) == "table" and entry._ai == false
            if not eligible or not radial or not panel_alive(radial) then
                if binding then self:_release_crew_perkdeck(slot) end
                card:set_perkdeck(data)
                pcall(card._render_perkdeck, card)
            else
                -- Hacker ACTIVE / Kingpin ACTIVE container.
                local ability = h5_child_verified(radial, "radial_ability")
                local hacker_active = false
                local hacker_ratio = 1
                if ability then
                    local state = crew_deck_leaf_read(ability)
                    hacker_active = crew_deck_leaf_active(state, crew_deck_held(binding, ability))
                    local meter = h5_child_verified(ability, "ability_meter")
                    local meter_state = crew_deck_leaf_read(meter)
                    if type(meter_state) == "table" and finite(meter_state.ratio) then
                        hacker_ratio = meter_state.ratio
                    elseif type(state) == "table" and finite(state.ratio) then
                        hacker_ratio = state.ratio
                    end
                    if hacker_active then
                        crew_deck_push(leaves, seen, ability)
                        data.active = true
                    end
                end
                data.hacker = {
                    active = hacker_active,
                    ratio = crew_deck_clamp01(hacker_ratio),
                    text = hacker_active
                        and (math.floor(crew_deck_clamp01(hacker_ratio) * 100 + 0.5) .. "%")
                        or "",
                }

                -- Kingpin absorb shield/health bitmaps.
                local shield = h5_child_verified(radial, "radial_absorb_shield_active")
                local shield_state = crew_deck_leaf_read(shield)
                local shield_active = crew_deck_leaf_active(shield_state,
                    crew_deck_held(binding, shield))
                if shield_active then
                    crew_deck_push(leaves, seen, shield)
                    data.active = true
                end
                local absorb_health = h5_child_verified(radial, "radial_absorb_health_active")
                local absorb_state = crew_deck_leaf_read(absorb_health)
                local absorb_active = crew_deck_leaf_active(absorb_state,
                    crew_deck_held(binding, absorb_health))
                if absorb_active then
                    crew_deck_push(leaves, seen, absorb_health)
                    data.active = true
                end
                data.kingpin = {
                    active = shield_active or absorb_active,
                    shield = shield_active,
                    health = absorb_active,
                }

                -- Dodge indicator (radial_custom).
                local custom = h5_child_verified(radial, "radial_custom")
                local custom_state = crew_deck_leaf_read(custom)
                local dodge_active = crew_deck_leaf_active(custom_state,
                    crew_deck_held(binding, custom))
                if dodge_active then
                    crew_deck_push(leaves, seen, custom)
                    data.active = true
                end
                data.dodge = {active = dodge_active}

                -- Maniac damage stacks (radial_info_meter foreground/background).
                local info_meter = h5_child_verified(radial, "radial_info_meter")
                local info_meter_bg = h5_child_verified(radial, "radial_info_meter_bg")
                local info_state = crew_deck_leaf_read(info_meter)
                local info_bg_state = crew_deck_leaf_read(info_meter_bg)
                local maniac_active = crew_deck_leaf_active(info_state,
                        crew_deck_held(binding, info_meter))
                    or crew_deck_leaf_active(info_bg_state,
                        crew_deck_held(binding, info_meter_bg))
                if crew_deck_leaf_active(info_state, crew_deck_held(binding, info_meter)) then
                    crew_deck_push(leaves, seen, info_meter)
                end
                if crew_deck_leaf_active(info_bg_state, crew_deck_held(binding, info_meter_bg)) then
                    crew_deck_push(leaves, seen, info_meter_bg)
                end
                if maniac_active then data.active = true end
                local maniac_ratio = 1
                if type(info_state) == "table" and finite(info_state.ratio) then
                    maniac_ratio = info_state.ratio
                end
                data.maniac = {
                    active = maniac_active,
                    ratio = crew_deck_clamp01(maniac_ratio),
                    text = maniac_active
                        and (math.floor(crew_deck_clamp01(maniac_ratio) * 100 + 0.5) .. "%")
                        or "",
                }

                -- Stoic stored-health reserve (radial_rip / radial_rip_bg).
                local rip = h5_child_verified(radial, "radial_rip")
                local rip_bg = h5_child_verified(radial, "radial_rip_bg")
                local rip_state = crew_deck_leaf_read(rip)
                local rip_bg_state = crew_deck_leaf_read(rip_bg)
                local stoic_active = crew_deck_leaf_active(rip_state,
                        crew_deck_held(binding, rip))
                    or crew_deck_leaf_active(rip_bg_state,
                        crew_deck_held(binding, rip_bg))
                if crew_deck_leaf_active(rip_state, crew_deck_held(binding, rip)) then
                    crew_deck_push(leaves, seen, rip)
                end
                if crew_deck_leaf_active(rip_bg_state, crew_deck_held(binding, rip_bg)) then
                    crew_deck_push(leaves, seen, rip_bg)
                end
                if stoic_active then data.active = true end
                local stoic_ratio = 1
                if type(rip_state) == "table" and finite(rip_state.ratio) then
                    stoic_ratio = rip_state.ratio
                end
                data.stoic = {
                    active = stoic_active,
                    ratio = crew_deck_clamp01(stoic_ratio),
                    text = stoic_active
                        and (math.floor(crew_deck_clamp01(stoic_ratio) * 100 + 0.5) .. "%")
                        or "",
                }

                -- COPR ratio (copr_overlay_panel numeric notches).
                local copr = h5_child_verified(radial, "copr_overlay_panel")
                local copr_active = false
                local copr_ratio = 1
                local copr_count = 0
                if copr then
                    for i = 0, COPR_CHILD_MAX - 1 do
                        local notch = crew_deck_child_fresh(copr, tostring(i))
                        if not notch then break end
                        copr_count = copr_count + 1
                        local notch_state = crew_deck_leaf_read(notch)
                        if crew_deck_leaf_active(notch_state,
                            crew_deck_held(binding, notch)) then
                            copr_active = true
                            crew_deck_push(leaves, seen, notch)
                            if type(notch_state) == "table" and finite(notch_state.ratio) then
                                copr_ratio = notch_state.ratio
                            end
                        end
                    end
                    if copr_active then data.active = true end
                end
                data.copr = {
                    active = copr_active,
                    ratio = crew_deck_clamp01(copr_ratio),
                    count = copr_count,
                    text = copr_active
                        and (math.floor(crew_deck_clamp01(copr_ratio) * 100 + 0.5) .. "%")
                        or "",
                }

                -- Delayed damage armor/health leaves.
                local delayed = h5_child_verified(radial, "radial_delayed_damage")
                local delayed_armor_ratio
                local delayed_health_ratio
                local delayed_active = false
                local armor_state
                local health_state
                if delayed then
                    local armor_leaf = h5_child_verified(delayed, "radial_delayed_damage_armor")
                    local health_leaf = h5_child_verified(delayed, "radial_delayed_damage_health")
                    armor_state = crew_deck_leaf_read(armor_leaf)
                    health_state = crew_deck_leaf_read(health_leaf)
                    local armor_active = crew_deck_leaf_active(armor_state,
                        crew_deck_held(binding, armor_leaf))
                    local health_active = crew_deck_leaf_active(health_state,
                        crew_deck_held(binding, health_leaf))
                    if armor_active then
                        delayed_active = true
                        crew_deck_push(leaves, seen, armor_leaf)
                        delayed_armor_ratio = crew_deck_clamp01(
                            type(armor_state) == "table" and armor_state.alpha or 1)
                    end
                    if health_active then
                        delayed_active = true
                        crew_deck_push(leaves, seen, health_leaf)
                        delayed_health_ratio = crew_deck_clamp01(
                            type(health_state) == "table" and health_state.alpha or 1)
                    end
                end
                if delayed_active then data.active = true end
                if binding and type(binding.data) == "table"
                    and type(binding.data.delayed) == "table" then
                    if type(armor_state) == "table" and armor_state.alpha <= 0.0001
                        and finite(binding.data.delayed.armor) then
                        delayed_armor_ratio = crew_deck_clamp01(binding.data.delayed.armor)
                    end
                    if type(health_state) == "table" and health_state.alpha <= 0.0001
                        and finite(binding.data.delayed.health) then
                        delayed_health_ratio = crew_deck_clamp01(binding.data.delayed.health)
                    end
                end
                data.delayed = {
                    active = delayed_active,
                    armor = delayed_armor_ratio,
                    health = delayed_health_ratio,
                }

                -- Damage feedback rim (damage_indicator alpha). The native
                -- leaf can stay visible while its alpha animates, so a bounded
                -- retention avoids leaving a permanent remote edge.
                local indicator = h5_child_verified(radial, "damage_indicator")
                local indicator_state = crew_deck_leaf_read(indicator)
                local indicator_held = crew_deck_held(binding, indicator)
                local native_alpha = type(indicator_state) == "table"
                    and indicator_state.alpha or nil
                local damage_active = crew_deck_leaf_active(indicator_state, indicator_held)
                local damage_alpha = 1
                local damage_until = binding and binding.damage_until or nil
                local damage_last_alpha = binding and binding.damage_alpha or nil
                if type(indicator_state) == "table" and finite(native_alpha)
                    and native_alpha > 0 then
                    damage_alpha = crew_deck_clamp01(native_alpha)
                    if finite(t) then
                        damage_until = t + 0.5
                        damage_last_alpha = damage_alpha
                    end
                elseif damage_active and indicator_held then
                    if finite(t) and finite(damage_until) and t <= damage_until
                        and finite(damage_last_alpha) then
                        damage_alpha = crew_deck_clamp01(damage_last_alpha)
                    elseif not finite(t) and finite(damage_last_alpha) then
                        damage_alpha = crew_deck_clamp01(damage_last_alpha)
                    else
                        damage_active = false
                        damage_until = nil
                        damage_last_alpha = nil
                    end
                end
                if damage_active then
                    crew_deck_push(leaves, seen, indicator)
                    data.active = true
                end
                data.damage = {
                    active = damage_active,
                    alpha = damage_alpha,
                }

                card:set_perkdeck(data)
                local render_ok = pcall(card._render_perkdeck, card)
                local certified = render_ok
                    and type(card.verify_deck) == "function"
                    and card:verify_deck() == true

                local acquired = false
                if certified and #leaves > 0 then
                    self:_h5_acquire_group(group_key, leaves, {
                        entry_panel = entry_panel,
                        manager = mgr,
                        root_gen = self._generation,
                    })
                    local state = self._h5_groups and self._h5_groups[group_key]
                    acquired = state ~= nil and state._release_pending ~= true
                        and state.property == "alpha"
                        and h5_same_targets(state.targets, leaves)
                    if acquired then
                        for i = 1, #leaves do
                            local as, alpha = safe_call(leaves[i], "alpha")
                            if as ~= CALL_OK or not finite(alpha) or alpha > 0.0001 then
                                acquired = false
                                break
                            end
                        end
                    end
                    if not acquired then
                        self:_h5_release_group(group_key)
                    end
                else
                    if binding then self:_h5_release_group(group_key) end
                end

                if acquired then
                    self._crew_perkdeck = self._crew_perkdeck or {}
                    self._crew_perkdeck[slot] = {
                        manager = mgr,
                        entry_panel = entry_panel,
                        player = player_panel,
                        radial = radial,
                        leaves = leaves,
                        group_key = group_key,
                        data = data,
                        damage_until = damage_until,
                        damage_alpha = damage_last_alpha,
                        leased = true,
                    }
                else
                    if self._crew_perkdeck then self._crew_perkdeck[slot] = nil end
                end
            end
        end
    end
end

function RT:_sync_local_backdrop(t, crew_receipt)
    self:_sync_delayed_replacement(self._manager)
    self:_sync_reserve_replacement(self._manager)
    self:_sync_copr_replacement(self._manager)
    local probe = self._residual_probe
    local timed = probe and not probe.done and probe.active
        and type(self._residual_stamp) == "function"
        and type(self._residual_record) == "function"
    local E = kyohud.hud.equipment
    local binding = self._hacker_active_binding
    local active_phase = "hacker_active"
    if (type(E) == "table" and E._projectile_id == "chico_injector")
        or (binding and binding.source_kind == "chico_injector_local") then
        active_phase = "kingpin_active"
    end
    local hacker_start = timed and self:_residual_stamp() or nil
    self:_sync_hacker_active()
    if timed then self:_residual_record(active_phase, hacker_start) end
    self:_sync_crew_perkdeck(self._manager, t)
    self:_apply_native_priority(t)
    self:_delayed_replacement_post_priority(t)
    self:_reserve_replacement_post_priority(t)
    self:_copr_replacement_post_priority(t)
    local hacker_post_start = timed and self:_residual_stamp() or nil
    self:_hacker_active_post_priority(t)
    if timed then self:_residual_record(active_phase, hacker_post_start) end
    if self._stoic_trace_enabled == true then self:_stoic_trace_record() end
    -- Only a real timed update pass may reuse the coordination memo. Direct or
    -- event-driven coordination invocations keep the full fresh certification.
    self._h5_coord_cache_pass = t ~= nil
    local certifications = self:_coordinate_h5_native_duplicates(crew_receipt)
    self._h5_coord_cache_pass = false
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

-- Synchronous local grenade-flash event seam. The native PostHook calls this
-- after the unchanged original, once the owned event is captured. It only runs
-- on a mounted, enabled, non-VR, non-disabled foundation with a live matching
-- equipment source. It presents and certifies the owned bitmap first, then
-- reuses the ordinary native-priority -> backdrop -> H5 order with a freshly
-- observed equipment verification (never a stale receipt). The reentrancy
-- latch is always released; native original/returns are never touched.
function RT:sync_local_grenade_flash_event()
    if kyohud.settings.enable_hud_foundation ~= true
        or kyohud.settings.enable_equipment ~= true then return false end
    if _G.IS_VR == true or self._disabled == true or self._freeflight == true then
        return false
    end
    local mgr = self._manager
    if not mgr or self._mounted ~= true
        or not managers or managers.hud ~= mgr then return false end
    local E = kyohud.hud.equipment
    if type(E) ~= "table" or E._mounted ~= true
        or E._manager ~= mgr or E._hud_manager ~= mgr then return false end
    if not E._root or not panel_alive(E._root) then return false end
    local event = E._grenade_flash_event
    if type(event) ~= "table" or event.invalid == true or event.expired == true
        or event.generation ~= E._source_generation
        or event.manager ~= mgr then return false end
    if self._local_flash_event_sync == true then return false end
    self._local_flash_event_sync = true
    local prev_ran = E._update_ran_now
    local prev_ok = E._verify_ok_now
    local probe = self._residual_probe
    local timed = probe and not probe.done and probe.active
        and type(self._residual_stamp) == "function"
        and type(self._residual_record) == "function"
    local start = timed and self:_residual_stamp() or nil
    local ok, result = pcall(function()
        self:_h5_release_group(H5_FLASH_GROUP)
        E:_present()
        local verified = E:verify() == true
        E._update_ran_now = true
        E._verify_ok_now = verified
        if not verified or E._grenade_flash_ok ~= true
            or type(E._grenade_flash_source) ~= "table" then
            self:_sync_local_backdrop(nil)
            return false
        end
        self:_sync_local_backdrop(nil)
        return E._grenade_flash_ok == true
            and E:_verify_grenade_flash() == true
    end)
    self._local_flash_event_sync = false
    E._update_ran_now = prev_ran
    E._verify_ok_now = prev_ok
    if timed and start ~= nil then self:_residual_record("harmony", start) end
    if not ok or result ~= true then
        self:_h5_release_group(H5_FLASH_GROUP)
        local row = type(E._rows) == "table" and E._rows[4] or nil
        if row and type(row._hide_grenade_flash) == "function" then
            row:_hide_grenade_flash()
        end
        E._grenade_flash_ok = false
        E._grenade_flash_source = nil
        return false
    end
    return true
end

-- Kingpin shares the one exclusive lease arbiter and synchronous seam while its
-- source is valid. A terminal/invalid publication releases only a Kingpin-owned
-- lease, republishes the inactive owned equipment and restores the original
-- native priority for any visible remaining container. A Hacker binding is never
-- disturbed here and no native parent is written.
function RT:sync_local_kingpin_activity_event(terminal_zero, publication_current, publication_total)
    local terminal_prov
    if terminal_zero == true then
        local probe = self._residual_probe
        local trace_count = probe and probe.trace_count or 0
        if probe and probe.mode == "kingpin" and probe.active == true and not probe.done
            and type(trace_count) == "number" and trace_count < 48 then
            terminal_prov = { remaining = publication_current, published_total = publication_total }
        end
        pcall(self._kingpin_transition, self, "terminal_enter", nil, terminal_prov)
    end
    local E = kyohud.hud.equipment
    local source
    if type(E) == "table" and type(E.get_local_ability_activity_source) == "function" then
        local ok, got = pcall(E.get_local_ability_activity_source, E)
        if ok then source = got end
    end
    if type(source) == "table" and source.kind == "chico_injector_local"
        and source.active == true then
        self:_residual_note_kingpin()
        pcall(self._kingpin_transition, self, "positive", nil, source)
        local result = self:sync_local_hacker_activity_event("kingpin_active")
        if result ~= true and self:_hacker_active_allowed(self._manager, E) then
            pcall(self._apply_native_priority, self, nil)
        end
        return result
    end
    local probe = self._residual_probe
    local timed = probe and not probe.done and probe.active
        and type(self._residual_stamp) == "function"
        and type(self._residual_record) == "function"
    local start = timed and self:_residual_stamp() or nil
    if publication_current ~= nil and publication_current ~= 0 then
        local trace_count = probe and probe.trace_count or 0
        if probe and probe.mode == "kingpin" and probe.active == true and not probe.done
            and type(trace_count) == "number" and trace_count < 48 then
            local reject_prov = { remaining = publication_current, published_total = publication_total }
            pcall(self._kingpin_transition, self, "publication_rejected", "source_unqualified", reject_prov)
        end
    end
    local binding = self._hacker_active_binding
    if binding and binding.source_kind == "chico_injector_local" then
        self:_release_hacker_active(true)
    end
    local mgr = self._manager
    if type(E) ~= "table" or not self:_hacker_active_allowed(mgr, E) then
        if timed then
            self:_residual_record("kingpin_active", start)
            self:_residual_record("kingpin_event_terminal", start)
        end
        if terminal_zero == true then
            pcall(self._kingpin_transition, self, "terminal_exit", "runtime_ineligible", terminal_prov)
        end
        return false
    end
    local prev_ran = E._update_ran_now
    local prev_ok = E._verify_ok_now
    local ok, result = pcall(function()
        E:_present()
        local repaired = false
        if terminal_zero == true and kyohud.settings.enable_player == true then
            local P = kyohud.hud.player
            if type(P) == "table" and P._mounted == true and P._manager == mgr
                and P._root and panel_alive(P._root) and P._render_verified == true then
                local vs, visible = safe_call(P._root, "visible")
                if vs == CALL_OK and visible == false then
                    local repair_ok, repair_result = pcall(P._repair_and_certify, P, mgr)
                    repaired = repair_ok and repair_result == true
                    if not repaired then
                        safe_call(P._root, "set_visible", false)
                    end
                end
            end
        end
        self:_apply_native_priority(nil)
        if repaired then
            self:_sync_local_backdrop(nil)
        end
        return true
    end)
    E._update_ran_now = prev_ran
    E._verify_ok_now = prev_ok
    if timed then
        self:_residual_record("kingpin_active", start)
        self:_residual_record("kingpin_event_terminal", start)
    end
    if terminal_zero == true then
        pcall(self._kingpin_transition, self, "terminal_exit", nil, terminal_prov)
    end
    return ok and result == true
end

-- Synchronous local Hacker ACTIVE seam. Runs after the unchanged native
-- activation original and after the equipment event capture. It presents and
-- certifies the owned ACTIVE row, proves the exact two native bitmap leaves,
-- then acquires only those two visible leaves. No parent write and no global
-- radial_ability bypass; failures release and keep the original priority.
function RT:sync_local_hacker_activity_event(phase)
    if kyohud.settings.enable_hud_foundation ~= true
        or kyohud.settings.enable_equipment ~= true then return false end
    if is_vr() or self._disabled == true or self._freeflight == true then return false end
    local mgr = self._manager
    if not mgr or self._mounted ~= true or not managers or managers.hud ~= mgr then
        return false
    end
    local E = kyohud.hud.equipment
    if not self:_hacker_active_allowed(mgr, E) then return false end
    local source = E:get_local_ability_activity_source()
    if type(source) ~= "table" then return false end
    if self._local_hacker_activity_sync == true then return false end
    self._local_hacker_activity_sync = true
    local prev_ran = E._update_ran_now
    local prev_ok = E._verify_ok_now
    local probe = self._residual_probe
    local timed = probe and not probe.done and probe.active
        and type(self._residual_stamp) == "function"
        and type(self._residual_record) == "function"
    local start = timed and self:_residual_stamp() or nil
    -- Timed event sub-phases only for the Kingpin seam. An exception inside the
    -- protected closure may omit later sub-phase records; pcall handling, call
    -- order, return values and early returns stay unchanged.
    local event_timed = timed and phase == "kingpin_active"
    local ok, result = pcall(function()
        local ev_start = event_timed and self:_residual_stamp() or nil
        local prepared = E:prepare_local_ability_activity_event()
        if event_timed then self:_residual_record("kingpin_event_prepare", ev_start) end
        if prepared ~= true then return false end
        local binding_before = self._hacker_active_binding
        local stable_before = binding_before ~= nil
            and binding_before.leased == true
            and binding_before.release_pending ~= true
            and binding_before.source_event_id ~= nil
            and type(binding_before.lease_gen) == "number"
        ev_start = event_timed and self:_residual_stamp() or nil
        local chained = self:_sync_hacker_active()
        if event_timed then self:_residual_record("kingpin_event_chain", ev_start) end
        if chained ~= true then return false end
        local binding_after = self._hacker_active_binding
        local stable_lease = stable_before
            and binding_after ~= nil and binding_after.leased == true
            and binding_after.source_event_id == binding_before.source_event_id
            and binding_after.lease_gen == binding_before.lease_gen
        if stable_lease then
            -- Throttle-skip marker, paired with M:_throttle_kingpin_activity in
            -- lua/hud/equipment.lua (E is the kyohud.hud.equipment singleton).
            E._kingpin_stable_event_seq = (E._kingpin_stable_event_seq or 0) + 1
            return true
        end
        ev_start = event_timed and self:_residual_stamp() or nil
        self:_apply_native_priority(nil)
        if event_timed then self:_residual_record("kingpin_event_priority", ev_start) end
        ev_start = event_timed and self:_residual_stamp() or nil
        self:_hacker_active_post_priority(nil)
        if event_timed then self:_residual_record("kingpin_event_post", ev_start) end
        ev_start = event_timed and self:_residual_stamp() or nil
        local binding = self._hacker_active_binding
        local src_ok, current = pcall(E.get_local_ability_activity_source, E)
        local exposed = false
        if src_ok and type(current) == "table" and current.active == true
            and binding and binding.leased == true
            and binding.release_pending ~= true
            and binding.source_event_id == current.event_id
            and binding.source_kind == current.kind
            and type(binding.leaves) == "table" and #binding.leaves == 2
            and _effective_visible(E._root, {}) == true
            and (_effective_alpha(E._root, {}) or 0) > 0 then
            local verify_ok, verified = pcall(E._verify_local_ability_activity, E, current)
            if verify_ok and verified == true then
                exposed = true
                for i = 1, 2 do
                    local leaf = binding.leaves[i]
                    local v_ok, visible = safe_call(leaf, "visible")
                    if v_ok ~= CALL_OK or visible ~= false
                        or self:_h5_group_holds_visible(H5_HACKER_ACTIVE_GROUP, leaf) ~= true then
                        exposed = false
                        break
                    end
                end
            end
        end
        if event_timed then self:_residual_record("kingpin_event_final", ev_start) end
        if exposed then return true end
        local hidden = _effective_visible(E._root, {}) ~= true
            or (_effective_alpha(E._root, {}) or 0) <= 0
        self:_release_hacker_active(true)
        if hidden then self:_apply_native_priority(nil) end
        return false
    end)
    self._local_hacker_activity_sync = false
    E._update_ran_now = prev_ran
    E._verify_ok_now = prev_ok
    if timed and start ~= nil then
        self:_residual_record(phase or "hacker_active", start)
    end
    if not ok or result ~= true then
        self:_release_hacker_active(true)
        return false
    end
    return true
end

-- Opt-in timing wrappers for the four harmony scopes. Each original body was
-- renamed with the _unprofiled suffix and left byte-for-byte intact; these
-- public methods only add the probe stamp/record around it. A public scope
-- called outside harmony still counts (overlaps possible), and backdrop work
-- after _coordinate_h5_native_duplicates remains unclassified residue. Errors
-- from the original body propagate unchanged.
function RT:_sync_delayed_replacement(mgr)
    local probe = self._residual_probe
    if not probe or probe.done or not probe.active
        or type(self._residual_stamp) ~= "function"
        or type(self._residual_record) ~= "function" then
        return self:_sync_delayed_replacement_unprofiled(mgr)
    end
    local start = self:_residual_stamp()
    self:_sync_delayed_replacement_unprofiled(mgr)
    self:_residual_record("harmony_delayed_sync", start)
end

function RT:_apply_native_priority(t, post_release)
    local probe = self._residual_probe
    if not probe or probe.done or not probe.active
        or type(self._residual_stamp) ~= "function"
        or type(self._residual_record) ~= "function" then
        return self:_apply_native_priority_unprofiled(t, post_release)
    end
    local start = self:_residual_stamp()
    self:_apply_native_priority_unprofiled(t, post_release)
    self:_residual_record("harmony_priority", start)
end

function RT:_delayed_replacement_post_priority(t)
    local probe = self._residual_probe
    if not probe or probe.done or not probe.active
        or type(self._residual_stamp) ~= "function"
        or type(self._residual_record) ~= "function" then
        return self:_delayed_replacement_post_priority_unprofiled(t)
    end
    local start = self:_residual_stamp()
    self:_delayed_replacement_post_priority_unprofiled(t)
    self:_residual_record("harmony_delayed_post", start)
end

-- Aggregate reserve phase: pre-priority acquisition and post-priority release
-- checks share one bounded counter; both calls are nested under harmony.
function RT:_sync_reserve_replacement(mgr)
    local probe = self._residual_probe
    if not probe or probe.done or not probe.active
        or type(self._residual_stamp) ~= "function"
        or type(self._residual_record) ~= "function" then
        return self:_sync_reserve_replacement_unprofiled(mgr)
    end
    local start = self:_residual_stamp()
    self:_sync_reserve_replacement_unprofiled(mgr)
    self:_residual_record("reserve", start)
end

function RT:_reserve_replacement_post_priority(t)
    local probe = self._residual_probe
    if not probe or probe.done or not probe.active
        or type(self._residual_stamp) ~= "function"
        or type(self._residual_record) ~= "function" then
        return self:_reserve_replacement_post_priority_unprofiled(t)
    end
    local start = self:_residual_stamp()
    self:_reserve_replacement_post_priority_unprofiled(t)
    self:_residual_record("reserve", start)
end

-- Aggregate COPR phase: pre-priority acquisition and post-priority release
-- checks share one bounded counter; both calls are nested under harmony.
function RT:_sync_copr_replacement(mgr)
    local probe = self._residual_probe
    if not probe or probe.done or not probe.active
        or type(self._residual_stamp) ~= "function"
        or type(self._residual_record) ~= "function" then
        return self:_sync_copr_replacement_unprofiled(mgr)
    end
    local start = self:_residual_stamp()
    self:_sync_copr_replacement_unprofiled(mgr)
    self:_residual_record("copr", start)
end

function RT:_copr_replacement_post_priority(t)
    local probe = self._residual_probe
    if not probe or probe.done or not probe.active
        or type(self._residual_stamp) ~= "function"
        or type(self._residual_record) ~= "function" then
        return self:_copr_replacement_post_priority_unprofiled(t)
    end
    local start = self:_residual_stamp()
    self:_copr_replacement_post_priority_unprofiled(t)
    self:_residual_record("copr", start)
end

function RT:_coordinate_h5_native_duplicates(crew_receipt)
    local probe = self._residual_probe
    if not probe or probe.done or not probe.active
        or type(self._residual_stamp) ~= "function"
        or type(self._residual_record) ~= "function" then
        return self:_coordinate_h5_native_duplicates_unprofiled(crew_receipt)
    end
    local start = self:_residual_stamp()
    local certifications = self:_coordinate_h5_native_duplicates_unprofiled(crew_receipt)
    self:_residual_record("harmony_duplicates", start)
    return certifications
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
