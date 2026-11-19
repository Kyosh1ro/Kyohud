kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end

kyohud.hud = kyohud.hud or {}

local M = kyohud.hud.equipment or {}
kyohud.hud.equipment = M

M._hud_manager = M._hud_manager
M._player_manager = M._player_manager
M._player_unit = M._player_unit
M._peer_id = M._peer_id
M._session = M._session
M._equipment_table = M._equipment_table
M._selections_table = M._selections_table
M._source_generation = M._source_generation or 0
M._invalidated = M._invalidated or true
M._snapshot = M._snapshot
M._hacker_activity = M._hacker_activity
M._hacker_activity_ok = M._hacker_activity_ok or false
-- quality split approved 2026-11-10
M._update_ran_now = M._update_ran_now or false
M._verify_ok_now = M._verify_ok_now or false
M._kingpin_terminal_ok = M._kingpin_terminal_ok or false

local GRENADE_FLASH_TRACE_LIMIT = 16
local HACKER_PROJECTILE_ID = "pocket_ecm_jammer"
local HACKER_ACTIVITY_SOURCE = "pocket_ecm_jammer_local"
local KINGPIN_PROJECTILE_ID = "chico_injector"
local KINGPIN_ACTIVITY_SOURCE = "chico_injector_local"
local KINGPIN_TERMINAL_SOURCE = "chico_injector_terminal"
local KINGPIN_TERMINAL_REASONS = {
    upgrade_inactive = true,
    expired = true,
}
local KINGPIN_VERIFY_RECEIPT = {}

local KINGPIN_PROBE_TARGETS = {
    _capture_activity = "kingpin_publication_capture",
    _capture_kingpin_activity = "kingpin_publication_capture",
    _throttle_kingpin_activity = "kingpin_throttle_full",
}

local function kingpin_probe_wrap(original, phase)
    return function(self, ...)
        local rt = kyohud.hud.runtime
        local probe = rt and rt._residual_probe
        local start
        if self ~= nil and probe ~= nil and probe.mode == "kingpin"
            and probe.active == true and probe.done ~= true
            and self._projectile_id == KINGPIN_PROJECTILE_ID then
            start = rt:_residual_stamp()
        end
        local result = original(self, ...)
        if start ~= nil then
            rt:_residual_record(phase, start)
        end
        return result
    end
end

do
    for key in pairs(KINGPIN_PROBE_TARGETS) do rawset(M, key, nil) end
    local mt = getmetatable(M)
    if type(mt) ~= "table" then
        mt = {}
        setmetatable(M, mt)
    end
    local previous_newindex = rawget(mt, "__newindex")
    rawset(mt, "__newindex", function(t, name, value)
        local phase = type(name) == "string" and KINGPIN_PROBE_TARGETS[name] or nil
        if phase ~= nil and type(value) == "function" then
            rawset(t, name, kingpin_probe_wrap(value, phase))
            return
        end
        if type(previous_newindex) == "function" then
            return previous_newindex(t, name, value)
        end
        rawset(t, name, value)
    end)
end

local function grenade_flash_trace_key(stage, reason)
    return tostring(stage) .. "|" .. tostring(reason)
end

if M._grenade_flash_trace_state == nil then
    local state = {enabled = false, count = 0, seen = {}}
    local trace_path
    if type(ModPath) == "string" then
        trace_path = ModPath .. "KYO_GRENADE_FLASH_TRACE"
    end
    if trace_path ~= nil and type(io) == "table" and type(io.open) == "function" then
        local ok_open, handle = pcall(io.open, trace_path, "r")
        if ok_open and handle ~= nil then
            state.enabled = true
            pcall(function() handle:close() end)
        end
    end
    M._grenade_flash_trace_state = state
end

function M:_grenade_flash_trace_ready(stage, reason)
    local state = self._grenade_flash_trace_state
    if not state or state.enabled ~= true then return false end
    if (state.count or 0) >= GRENADE_FLASH_TRACE_LIMIT then return false end
    local seen = state.seen
    if seen and seen[grenade_flash_trace_key(stage, reason)] then return false end
    return true
end

function M:_trace_grenade_flash(stage, reason, detail)
    if not self:_grenade_flash_trace_ready(stage, reason) then return false end
    local state = self._grenade_flash_trace_state
    state.count = (state.count or 0) + 1
    state.seen = state.seen or {}
    state.seen[grenade_flash_trace_key(stage, reason)] = true
    local ok_format, message = pcall(function()
        local text = "[KyoHUD][GrenadeFlashTrace] stage=" .. tostring(stage)
            .. " reason=" .. tostring(reason)
        if type(detail) == "string" and detail ~= "" then
            text = text .. " " .. detail
        elseif type(detail) == "table" then
            local keys = {}
            for key in pairs(detail) do keys[#keys + 1] = key end
            table.sort(keys, function(a, b) return tostring(a) < tostring(b) end)
            for i = 1, #keys do
                local key = keys[i]
                local value = detail[key]
                if value ~= nil then
                    text = text .. " " .. tostring(key) .. "=" .. tostring(value)
                end
            end
        end
        return text
    end)
    if not ok_format then return false end
    if type(log) ~= "function" then return false end
    pcall(log, message)
    return true
end

local function is_valid_positive_quantity(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    if v <= 0 then return false end
    return true
end

local function is_valid_known_quantity(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    if v < 0 then return false end
    return true
end

local function finite(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    return true
end

local function is_finite_positive_integer(v, max)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    if v < 1 then return false end
    if v > max then return false end
    if math.floor(v) ~= v then return false end
    return true
end

local function lookup_method(obj, method)
    return obj[method]
end

local function safe_call(obj, method, ...)
    if obj == nil then return false, nil end
    local ok_get, fn = pcall(lookup_method, obj, method)
    if not ok_get or type(fn) ~= "function" then return false, nil end
    return pcall(fn, obj, ...)
end

local function residual_context()
    local rt = kyohud.hud.runtime
    if not rt then return nil end
    if type(rt._residual_stamp) ~= "function"
        or type(rt._residual_record) ~= "function" then
        return nil
    end
    local probe = rt._residual_probe
    if not probe or probe.done or not probe.active then return nil end
    return rt
end

local KINGPIN_REJECT_PHASE = {
    dirty = "kingpin_reject_dirty",
    cache = "kingpin_reject_cache",
    activation = "kingpin_reject_activation",
    snapshot = "kingpin_reject_snapshot",
    layout = "kingpin_reject_layout",
    identity = "kingpin_reject_identity",
    cooldown = "kingpin_reject_cooldown",
    verify = "kingpin_reject_verify",
    render = "kingpin_reject_render",
    source = "kingpin_reject_source",
    exception = "kingpin_reject_exception",
    postverify = "kingpin_reject_postverify",
    other = "kingpin_reject_other",
}

local function residual_count(name)
    local rt = kyohud.hud.runtime
    local probe = rt and rt._residual_probe
    if not probe or probe.done or not probe.active then return end
    local phase = probe.phases[name]
    if phase then phase.count = phase.count + 1 end
end

local function residual_count_kingpin_reject(reason)
    local rt = kyohud.hud.runtime
    local probe = rt and rt._residual_probe
    if not probe or probe.done or not probe.active then return end
    local name = KINGPIN_REJECT_PHASE[reason]
    if name == nil then name = KINGPIN_REJECT_PHASE.other end
    local phase = probe.phases[name]
    if phase then phase.count = phase.count + 1 end
end

function M:refresh(manager)
    self._invalidated = true
    self._snapshot = nil
    self._detached_cache = nil

    if type(managers) ~= "table" or manager == nil or manager ~= managers.hud then
        self._hud_manager = nil
        self._player_manager = nil
        self._player_unit = nil
        self._peer_id = nil
        self._session = nil
        self._equipment_table = nil
        self._selections_table = nil
        return
    end

    local pm = managers.player
    if not pm then
        self._hud_manager = nil
        self._player_manager = nil
        self._player_unit = nil
        self._peer_id = nil
        self._session = nil
        self._equipment_table = nil
        self._selections_table = nil
        return
    end

    local ok_unit, unit = safe_call(pm, "player_unit")
    if not ok_unit or not unit or not alive(unit) then
        self._hud_manager = nil
        self._player_manager = nil
        self._player_unit = nil
        self._peer_id = nil
        self._session = nil
        self._equipment_table = nil
        self._selections_table = nil
        return
    end

    local ok_session, session = safe_call(managers.network, "session")
    if not ok_session or not session then
        self._hud_manager = nil
        self._player_manager = nil
        self._player_unit = nil
        self._peer_id = nil
        self._session = nil
        self._equipment_table = nil
        self._selections_table = nil
        return
    end

    local ok_peer, peer = safe_call(session, "local_peer")
    if not ok_peer or not peer then
        self._hud_manager = nil
        self._player_manager = nil
        self._player_unit = nil
        self._peer_id = nil
        self._session = nil
        self._equipment_table = nil
        self._selections_table = nil
        return
    end

    local ok_id, peer_id = safe_call(peer, "id")
    if not ok_id then
        self._hud_manager = nil
        self._player_manager = nil
        self._player_unit = nil
        self._peer_id = nil
        self._session = nil
        self._equipment_table = nil
        self._selections_table = nil
        return
    end

    local equipment = pm._equipment
    if not equipment then
        self._hud_manager = nil
        self._player_manager = nil
        self._player_unit = nil
        self._peer_id = nil
        self._session = nil
        self._equipment_table = nil
        self._selections_table = nil
        return
    end

    local selections = equipment.selections
    if not selections then
        self._hud_manager = nil
        self._player_manager = nil
        self._player_unit = nil
        self._peer_id = nil
        self._session = nil
        self._equipment_table = nil
        self._selections_table = nil
        return
    end

    local identity_changed = false
    if self._hud_manager ~= manager then
        self._hud_manager = manager
        identity_changed = true
    end
    if self._player_manager ~= pm then
        self._player_manager = pm
        identity_changed = true
    end
    if self._player_unit ~= unit then
        self._player_unit = unit
        identity_changed = true
    end
    if self._peer_id ~= peer_id then
        self._peer_id = peer_id
        identity_changed = true
    end
    if self._session ~= session then
        self._session = session
        identity_changed = true
    end
    if self._equipment_table ~= equipment then
        self._equipment_table = equipment
        identity_changed = true
    end
    if self._selections_table ~= selections then
        self._selections_table = selections
        identity_changed = true
    end

    if identity_changed then
        self._source_generation = self._source_generation + 1
        self._activity = nil
        self._hacker_activity = nil
        self._hacker_activity_ok = false
        self._cable_zero = nil
        self._cooldown_event = nil
        self._amount_text = nil
        self._grenade_flash_event = nil
    end

    local deployables = {}
    for i, sel in ipairs(selections) do
        local eq_id = sel.equipment
        if eq_id then
            local quantities = {}
            if sel.amount then
                for j, token in ipairs(sel.amount) do
                    local ok_digest, raw = safe_call(Application, "digest_value", token, false)
                    if not ok_digest then
                        return
                    end
                    local known = is_valid_known_quantity(raw)
                    table.insert(quantities, {raw = raw, known = known})
                end
            end
            deployables[eq_id] = {
                equipment_id = eq_id,
                quantities = quantities,
                selection_index = i
            }
            local text = self._amount_text and self._amount_text[i]
            if text and text.record == sel then
                local any_known = false
                for _, q in ipairs(quantities) do any_known = any_known or q.known end
                if not any_known then deployables[eq_id].amount_text = text.value
                else self._amount_text[i] = nil end
            end
        end
    end

    local selected_index = equipment.selected_index
    local selected_effective = nil

    if is_finite_positive_integer(selected_index, #selections) then
        local ok_native, native_sel = safe_call(pm, "selected_equipment")
        if ok_native and native_sel then
            local sel_record = selections[selected_index]
            if sel_record and native_sel == sel_record then
                local entry = deployables[sel_record.equipment]
                local has_usable = false
                if entry then
                    for _, q in ipairs(entry.quantities) do
                        if q.known and is_valid_positive_quantity(q.raw) then
                            has_usable = true
                            break
                        end
                    end
                end
                if has_usable then
                    selected_effective = native_sel.equipment
                end
            end
        end
    else
        selected_index = nil
    end

    local unsupported = #selections > 2

    self._snapshot = {
        deployables = deployables,
        selected_index = selected_index,
        selected_effective = selected_effective,
        source_generation = self._source_generation,
        source_known = true,
        unsupported = unsupported or nil
    }

    self:_capture_consumables(pm, peer_id)
    self._invalidated = false
end

local function quantity(raw)
    return {raw = type(raw) == "number" and raw or nil, known = is_valid_known_quantity(raw)}
end

local function current_game_time()
    local clock_ok, timer = safe_call(TimerManager, "game")
    local time_ok, now = safe_call(clock_ok and timer or nil, "time")
    if not time_ok or not is_valid_known_quantity(now) then return nil, clock_ok and timer or nil end
    return now, timer
end

local function observe_game_time(self)
    local now, timer = current_game_time()
    if now == nil then return nil, timer end
    local guard = self._cooldown_clock_guard
    if type(guard) ~= "table" or guard.clock ~= timer or guard.generation ~= self._source_generation then
        self._cooldown_clock_guard = {clock = timer, generation = self._source_generation, last = now}
        return now, timer
    end
    if now < guard.last then return nil, timer end
    if now > guard.last then guard.last = now end
    return now, timer
end

local function establish_clock_epoch(self, timer, now)
    if timer == nil or not is_valid_known_quantity(now) then return end
    self._cooldown_clock_guard = {clock = timer, generation = self._source_generation, last = now}
end

local function unknown_cooldown()
    return {known = false, active = false, clock_kind = "game"}
end

function M:_capture_consumables(pm, peer_id)
    local snap = self._snapshot
    local specials = self._equipment_table.specials
    self._specials_table = specials
    local cable = type(specials) == "table" and specials.cable_tie
    local ok, raw = false, nil
    if cable and cable.amount ~= nil then ok, raw = safe_call(Application, "digest_value", cable.amount, false) end
    snap.cables = quantity(cable and ok and raw or nil)
    snap.cables.unlimited = cable ~= nil and ok and raw == -1
    if snap.cables.unlimited then snap.cables.known = true end
    if not cable and self._cable_zero == specials and type(specials) == "table" then
        snap.cables = {raw = 0, known = true, unlimited = false}
    end

    local projectile = {kind = "unknown", charges = quantity(nil), maximum = quantity(nil)}
    local got, entry = safe_call(pm, "get_synced_grenades", peer_id)
    local td
    if got and type(entry) == "table" and type(entry.grenade) == "string" then
        projectile.projectile_id = entry.grenade
        local good, count = safe_call(pm, "get_grenade_amount", peer_id)
        projectile.charges = quantity(good and count or nil)
        local max_ok, maximum = safe_call(pm, "get_max_grenades", entry.grenade)
        projectile.maximum = quantity(max_ok and maximum or nil)
        td = tweak_data and tweak_data.blackmarket and tweak_data.blackmarket.projectiles
        td = td and td[entry.grenade]
        if type(td) == "table" then
            local ability = td.ability == true or (type(td.ability) == "string" and td.ability ~= "")
            local throwable = td.throwable == true or td.is_a_grenade == true
            if ability and not throwable then projectile.kind = "ability"
            elseif throwable and not ability then projectile.kind = "throwable" end
            projectile.name_id = td.name_id
        end
    end
    snap.projectile = projectile
    local gpc = managers.game_play_central
    local registry = pm._global and pm._global.synced_grenades
    local timers = pm._timers
    local record = timers and timers.replenish_grenades
    if self._projectile_id ~= projectile.projectile_id or self._gpc ~= gpc or self._grenade_registry ~= registry then
        self._activity = nil
        self._hacker_activity = nil
        self._hacker_activity_ok = false
        local event = self._cooldown_event
        local keep_event = type(event) == "table" and not event.cancelled
            and event.manager == pm and event.timers == timers and record ~= nil
            and event.record == record and event.registry == registry and event.gpc == gpc
            and event.projectile_id == projectile.projectile_id
        if not keep_event then self._cooldown_event = nil end
        self._projectile_id = projectile.projectile_id
        self._gpc = gpc
        self._grenade_registry = registry
    end
    local cooldown = {known = false, active = false, clock_kind = "game"}
    local base_duration
    if projectile.projectile_id then
        local good, value = safe_call(pm, "get_timer_remaining", "replenish_grenades")
        if good and (value == nil or is_valid_known_quantity(value)) then
            cooldown.known = true
            cooldown.active = value ~= nil and value > 0
            cooldown.remaining = value
        end
        if td and is_valid_positive_quantity(td.base_cooldown) then
            base_duration = td.base_cooldown
            cooldown.duration = base_duration
        end
    end
    cooldown.base_duration = base_duration
    snap.cooldown = cooldown
    local now, clock = observe_game_time(self)
    local event = self._cooldown_event
    if type(event) == "table" and event.cancelled then
        cooldown.known = true
        cooldown.active = false
        cooldown.remaining = nil
    elseif now == nil then
        cooldown.known = false
        cooldown.active = false
        cooldown.remaining = nil
    else
        cooldown.sampled_at = now
        if type(event) == "table" and is_valid_positive_quantity(event.duration)
            and event.manager == pm and event.timers == timers and record ~= nil
            and event.record == record and event.registry == registry and event.gpc == gpc
            and event.projectile_id == projectile.projectile_id
            and event.clock == clock and event.generation == self._source_generation
            and (projectile.kind == "ability" or projectile.kind == "throwable")
            and projectile.charges and projectile.charges.known == true then
            cooldown.duration = event.duration
            if cooldown.known and cooldown.active and is_valid_positive_quantity(cooldown.remaining)
                and event.duration >= cooldown.remaining then
                cooldown.integrated = true
            end
        end
    end
    snap.activity = self._activity or {known = false, active = false}
end

local function detached(value)
    if type(value) ~= "table" then return value end
    local result = {}
    for k, v in pairs(value) do result[k] = detached(v) end
    return result
end

function M:_fresh_cooldown()
    local snap = self._snapshot
    if not snap then return unknown_cooldown() end
    local stored = snap.cooldown
    local projectile = snap.projectile
    if type(stored) ~= "table" or type(projectile) ~= "table" then return unknown_cooldown() end

    local pm = managers and managers.player
    if not pm or self._player_manager ~= pm or self._hud_manager ~= (managers and managers.hud) then
        return unknown_cooldown()
    end
    local ok_unit, unit = safe_call(pm, "player_unit")
    if not ok_unit or unit == nil or unit ~= self._player_unit then return unknown_cooldown() end
    if type(alive) == "function" then
        local ok_alive, is_alive = pcall(alive, unit)
        if not ok_alive or is_alive ~= true then return unknown_cooldown() end
    end
    local ok_session, session = safe_call(managers.network, "session")
    if not ok_session or session == nil or session ~= self._session then return unknown_cooldown() end
    local ok_peer, peer = safe_call(session, "local_peer")
    if not ok_peer or peer == nil then return unknown_cooldown() end
    local ok_id, peer_id = safe_call(peer, "id")
    if not ok_id or peer_id ~= self._peer_id then return unknown_cooldown() end
    local equipment = pm._equipment
    if not equipment or equipment ~= self._equipment_table then return unknown_cooldown() end
    if equipment.selections ~= self._selections_table then return unknown_cooldown() end
    local registry = pm._global and pm._global.synced_grenades
    if not registry or registry ~= self._grenade_registry then return unknown_cooldown() end
    if managers.game_play_central ~= self._gpc then return unknown_cooldown() end
    local got, entry = safe_call(pm, "get_synced_grenades", peer_id)
    if not got or type(entry) ~= "table" or type(entry.grenade) ~= "string" then
        return unknown_cooldown()
    end
    if entry.grenade ~= self._projectile_id or projectile.projectile_id ~= self._projectile_id then
        return unknown_cooldown()
    end

    local event = self._cooldown_event
    local cooldown = {known = true, active = false, clock_kind = "game"}
    if is_valid_positive_quantity(stored.base_duration) then
        cooldown.duration = stored.base_duration
    end
    if type(event) == "table" and event.cancelled then
        cooldown.remaining = nil
        return cooldown
    end

    local now, clock = observe_game_time(self)
    if now == nil then return unknown_cooldown() end
    if stored.sampled_at ~= nil and now < stored.sampled_at then return unknown_cooldown() end

    local value_ok, value = safe_call(pm, "get_timer_remaining", "replenish_grenades")
    if not value_ok or not (value == nil or is_valid_known_quantity(value)) then
        return unknown_cooldown()
    end
    cooldown.sampled_at = now
    if value ~= nil then
        cooldown.remaining = value
        cooldown.active = value > 0
    end

    local timers = pm._timers
    local record = timers and timers.replenish_grenades
    if type(event) == "table" and is_valid_positive_quantity(event.duration)
        and event.manager == pm and event.timers == timers and record ~= nil
        and event.record == record and event.registry == registry
        and event.gpc == managers.game_play_central
        and event.projectile_id == self._projectile_id
        and event.clock == clock and event.generation == self._source_generation
        and (projectile.kind == "ability" or projectile.kind == "throwable")
        and projectile.charges and projectile.charges.known == true then
        cooldown.duration = event.duration
        if cooldown.active and is_valid_positive_quantity(value)
            and event.duration >= value then
            cooldown.integrated = true
        end
    end
    return cooldown
end

function M:get_snapshot()
    if not self._snapshot or self._invalidated then
        return {
            deployables = {},
            selected_index = nil,
            selected_effective = nil,
            source_known = false,
            source_generation = self._source_generation
        }
    end

    local cache = self._detached_cache
    if cache == nil or cache.snapshot ~= self._snapshot then
        local detached_deployables = {}
        for eq_id, entry in pairs(self._snapshot.deployables) do
            local detached_quantities = {}
            for _, q in ipairs(entry.quantities) do
                table.insert(detached_quantities, {raw = q.raw, known = q.known})
            end
            detached_deployables[eq_id] = {
                equipment_id = entry.equipment_id,
                quantities = detached_quantities,
                selection_index = entry.selection_index,
                amount_text = entry.amount_text
            }
        end
        cache = {
            snapshot = self._snapshot,
            deployables = detached_deployables,
            selected_index = self._snapshot.selected_index,
            selected_effective = self._snapshot.selected_effective,
            source_generation = self._snapshot.source_generation,
            source_known = self._snapshot.source_known,
            unsupported = self._snapshot.unsupported,
            cables = detached(self._snapshot.cables),
            projectile = detached(self._snapshot.projectile)
        }
        self._detached_cache = cache
    end

    return {
        deployables = cache.deployables,
        selected_index = cache.selected_index,
        selected_effective = cache.selected_effective,
        source_generation = cache.source_generation,
        source_known = cache.source_known,
        unsupported = cache.unsupported,
        cables = cache.cables,
        projectile = cache.projectile,
        cooldown = self:_fresh_cooldown(),
        activity = self:_timed_snapshot(self._snapshot.activity)
    }
end

function M:_timed_snapshot(value)
    if type(value) == "table" and value.source == KINGPIN_ACTIVITY_SOURCE then
        local source = self:get_kingpin_activity_source()
        if type(source) ~= "table" then
            return {known = false, active = false}
        end
        return detached(value)
    end
    local result = detached(value or {known = false, active = false})
    if result.known and result.active and result.sampled_at and result.remaining then
        local ok, timer = safe_call(TimerManager, "game")
        local good, now = safe_call(ok and timer or nil, "time")
        if not good or not is_valid_known_quantity(now) or now < result.sampled_at then
            return {known = false, active = false}
        end
        result.remaining = math.max(0, result.remaining - (now - result.sampled_at))
        result.active = result.remaining > 0
    end
    return result
end

function M:invalidate()
    self._snapshot = nil
    self._detached_cache = nil
    self._invalidated = true
    self._activity = nil
    self._cooldown_event = nil
    self._cooldown_clock_guard = nil
    self._cable_zero = nil
    self._equipment_table = nil
    self._projectile_id = nil
    self._amount_text = nil
    self._grenade_flash_ok = false
    self._grenade_flash_source = nil
    self._grenade_flash_rejected = nil
    self._grenade_flash_event = nil
    self._hacker_activity = nil
    self._hacker_activity_ok = false
    self._kingpin_activity = nil
    self._kingpin_activity_ok = false
    self._kingpin_terminal_ok = false
    self._kingpin_present_cache = nil
    self._kingpin_source_cache = nil
    self._kingpin_stable_event_seq = nil
    self._throttle_seen_seq = nil
    self._dirty = true
end

function M:_read_local_jammer_record(unit)
    if unit == nil then return nil end
    local inv_ok, inventory = safe_call(unit, "inventory")
    if not inv_ok or inventory == nil then return nil end
    local data_ok, data = pcall(function() return inventory._jammer_data end)
    if not data_ok or type(data) ~= "table" then return nil end
    local effect = data.effect
    if effect ~= "jamming" and effect ~= "feedback" then return nil end
    if not is_valid_known_quantity(data.t) then return nil end
    return {inventory = inventory, data = data, effect = effect, t = data.t}
end

function M:_capture_activity(left, total)
    self._kingpin_activity = nil
    self._kingpin_activity_ok = false
    local pm = managers and managers.player
    local ok, unit = safe_call(pm, "player_unit")
    local equipment = pm and pm._equipment
    local registry = pm and pm._global and pm._global.synced_grenades
    local got, entry = safe_call(pm, "get_synced_grenades", self._peer_id)
    local projectile_id = got and type(entry) == "table" and entry.grenade or nil
    if self._invalidated or not ok or self._player_unit ~= unit or self._player_manager ~= pm
        or self._hud_manager ~= managers.hud or self._equipment_table ~= equipment
        or self._grenade_registry ~= registry or self._gpc ~= managers.game_play_central
        or not got or self._projectile_id ~= projectile_id then
        self:refresh(managers and managers.hud)
    end
    if self._invalidated then
        self._hacker_activity = nil
        self._hacker_activity_ok = false
        return
    end
    if total == nil then total = left end
    local now, clock
    if left == 0 then
        self._activity = {known = true, active = false, remaining = 0}
    elseif is_valid_positive_quantity(left) and is_valid_positive_quantity(total) then
        local clock_ok, timer = safe_call(TimerManager, "game")
        local good, current = safe_call(clock_ok and timer or nil, "time")
        if not good or not is_valid_known_quantity(current) then
            self._activity = nil
            self._hacker_activity = nil
            self._hacker_activity_ok = false
            return
        end
        clock = timer
        now = current
        self._activity = {known = true, active = true, remaining = left, duration = total,
            sampled_at = now, clock_kind = "game"}
    else
        self._activity = nil
    end
    self._hacker_activity = nil
    self._hacker_activity_ok = false
    if self._activity and self._activity.known and self._activity.active
        and self._projectile_id == HACKER_PROJECTILE_ID
        and projectile_id == HACKER_PROJECTILE_ID and now ~= nil and clock ~= nil then
        local jammer = self:_read_local_jammer_record(self._player_unit)
        if jammer then
            self._hacker_activity_serial = (self._hacker_activity_serial or 0) + 1
            local generation = self._source_generation
            local event_id = tostring(generation) .. ":" .. tostring(self._hacker_activity_serial)
            self._activity.source = HACKER_ACTIVITY_SOURCE
            self._hacker_activity = {
                kind = HACKER_ACTIVITY_SOURCE,
                event_id = event_id,
                serial = self._hacker_activity_serial,
                activity = self._activity,
                projectile_id = HACKER_PROJECTILE_ID,
                manager = managers and managers.hud or nil,
                hud_manager = self._hud_manager,
                player_manager = pm,
                player_unit = unit,
                session = self._session,
                peer_id = self._peer_id,
                equipment = self._equipment_table,
                selections = self._selections_table,
                registry = self._grenade_registry,
                gpc = self._gpc,
                generation = generation,
                clock = clock,
                start = now,
                last_seen = now,
                deadline = now + left,
                remaining = left,
                duration = total,
                inventory = jammer.inventory,
                jammer = jammer.data,
                jammer_effect = jammer.effect,
                jammer_t = jammer.t,
            }
        end
    end
    self._snapshot.activity = self._activity or {known = false, active = false}
end

-- Kingpin is a distinct local source: the radial publication carries the real
-- current/total, while the exact temporary record is read against Application's
-- own expiry. No game/player clock is subtracted from that expiry and no ratio
-- is converted to seconds.
function M:_capture_kingpin_activity(left, total)
    self._kingpin_activity = nil
    self._kingpin_activity_ok = false
    if self._invalidated or type(self._snapshot) ~= "table" then return false end
    local pm = managers and managers.player
    local ok, unit = safe_call(pm, "player_unit")
    if not ok or unit == nil or unit ~= self._player_unit or pm ~= self._player_manager then
        return false
    end
    if self._hud_manager ~= managers.hud or self._projectile_id ~= KINGPIN_PROJECTILE_ID then
        return false
    end
    local got, entry = safe_call(pm, "get_synced_grenades", self._peer_id)
    if not got or type(entry) ~= "table" or entry.grenade ~= KINGPIN_PROJECTILE_ID then
        return false
    end
    if self._equipment_table ~= pm._equipment then return false end
    if self._grenade_registry ~= (pm._global and pm._global.synced_grenades) then return false end
    if self._gpc ~= managers.game_play_central then return false end
    if total == nil then total = left end
    if not is_valid_positive_quantity(left) or not is_valid_positive_quantity(total) then
        return false
    end
    if left > total + 0.001 then return false end
    local upgrades = pm._temporary_upgrades
    local category = type(upgrades) == "table" and upgrades.temporary or nil
    local record = type(category) == "table" and category.chico_injector or nil
    if type(record) ~= "table" or not is_valid_positive_quantity(record.expire_time) then
        return false
    end
    local active_ok, active = safe_call(pm, "has_activate_temporary_upgrade",
        "temporary", KINGPIN_PROJECTILE_ID)
    if not active_ok or active ~= true then return false end
    local uv_ok, upgrade = safe_call(pm, "upgrade_value", "temporary", KINGPIN_PROJECTILE_ID)
    local duration = uv_ok and type(upgrade) == "table" and upgrade[2] or nil
    if not is_valid_positive_quantity(duration) then return false end
    if math.abs(duration - total) > 0.001 then return false end
    local app = _G.Application
    if app == nil then return false end
    local app_ok, app_now = safe_call(app, "time")
    if not app_ok or not is_valid_known_quantity(app_now) then return false end
    if not (record.expire_time > app_now) then return false end
    local cd_ok, character_damage = safe_call(unit, "character_damage")
    if not cd_ok or character_damage == nil then return false end
    local pt_ok, player_timer = safe_call(pm, "player_timer")
    local gt_ok, game_timer = safe_call(TimerManager, "game")
    if not pt_ok or player_timer == nil or not gt_ok or game_timer == nil then
        return false
    end
    local pt_ok_time, player_time = safe_call(player_timer, "time")
    local gt_ok_time, game_time = safe_call(game_timer, "time")
    if not pt_ok_time or not is_valid_known_quantity(player_time)
        or not gt_ok_time or not is_valid_known_quantity(game_time) then
        return false
    end
    local session = self._session
    local peer_id = self._peer_id
    self._activity = {
        known = true,
        active = true,
        remaining = left,
        duration = duration,
        sampled_at = nil,
        clock_kind = "application",
        source = KINGPIN_ACTIVITY_SOURCE,
    }
    self._snapshot.activity = self._activity
    local generation = self._source_generation
    local identity = {
        record = record,
        root = upgrades,
        category = category,
        application = app,
        player_manager = pm,
        player_unit = unit,
        session = session,
        peer_id = peer_id,
        generation = generation,
    }
    local previous = self._kingpin_activation_identity
    local same_activation = type(previous) == "table"
        and previous.record == identity.record
        and previous.root == identity.root
        and previous.category == identity.category
        and previous.application == identity.application
        and previous.player_manager == identity.player_manager
        and previous.player_unit == identity.player_unit
        and previous.session == identity.session
        and previous.peer_id == identity.peer_id
        and previous.generation == identity.generation
    if same_activation then
        if type(self._kingpin_activity_serial) ~= "number" then
            self._kingpin_activity_serial = 1
        end
    else
        self._kingpin_activation_identity = identity
        self._kingpin_activity_serial = (self._kingpin_activity_serial or 0) + 1
    end
    local event_id = "kingpin:" .. tostring(generation) .. ":" .. tostring(self._kingpin_activity_serial)
    self._kingpin_activity = {
        kind = KINGPIN_ACTIVITY_SOURCE,
        event_id = event_id,
        serial = self._kingpin_activity_serial,
        activity = self._activity,
        projectile_id = KINGPIN_PROJECTILE_ID,
        manager = managers.hud,
        hud_manager = self._hud_manager,
        player_manager = pm,
        player_unit = unit,
        character_damage = character_damage,
        session = session,
        peer_id = peer_id,
        equipment = self._equipment_table,
        selections = self._selections_table,
        registry = self._grenade_registry,
        gpc = self._gpc,
        generation = generation,
        temporary_root = upgrades,
        temporary_category = category,
        temporary_record = record,
        expire_time = record.expire_time,
        duration = duration,
        remaining = left,
        published_total = total,
        application = app,
        application_now = app_now,
        start_application = app_now,
        last_application = app_now,
        player_timer = pt_ok and player_timer or nil,
        game_timer = gt_ok and game_timer or nil,
        player_time = player_time,
        game_time = game_time,
    }
    return true
end

-- Additive local composition; native visibility is never acquired.
local function live(p)
    if p == nil or type(alive) ~= "function" then return false end
    local ok, result = pcall(alive, p)
    return ok and result == true
end

local function enabled()
    return kyohud.settings and kyohud.settings.enable_hud_foundation == true
        and kyohud.settings.enable_equipment == true and _G.IS_VR ~= true
end

local function loc(key, fallback)
    local ok, text = safe_call(managers and managers.localization, "text", key)
    return ok and type(text) == "string" and text ~= "" and text ~= key and text or fallback
end

local function count_text(q, unlimited)
    if q and q.unlimited and q.known then return unlimited end
    return q and q.known and tostring(q.raw) or "--"
end

function M:integrated_recharge_text(cooldown, charges)
    if type(cooldown) ~= "table" or type(charges) ~= "table" then return nil end
    if charges.known ~= true or not is_valid_known_quantity(charges.raw) then return nil end
    local remaining = cooldown.remaining
    local duration = cooldown.duration
    if not is_valid_positive_quantity(remaining) then return nil end
    if not is_valid_positive_quantity(duration) then return nil end
    if remaining > duration then return nil end
    if charges.raw > 0 then return tostring(charges.raw) end
    if charges.raw == 0 then return string.format("%ds", math.ceil(remaining)) end
    return nil
end

function M:_geometry()
    if not live(self._parent) then return nil end
    local a,pw = safe_call(self._parent,"w")
    local b,ph = safe_call(self._parent,"h")
    local layout=kyohud.hud.layout
    if not a or not b or not layout then return nil end
    local g=layout.local_loadout(pw,ph,kyohud.settings.hud_scale)
    if not g then return nil end
    local weapons=kyohud.hud.weapons
    local used=0
    if kyohud.settings.enable_weapons and weapons and weapons._mounted and weapons._layout_cache then
        used=(weapons._used_width or 0)+4*g.e
    end
    local width=used>0 and g.w-used-14*g.e or (self._required_width or g.w-28*g.e)
    if width<=0 or width+.5<(self._required_width or 0) then return nil end
    local th=self._temporal_height or 0
    return {x=g.x+g.w-14*g.e-width,y=g.y-th,w=width,h=g.h+th,e=g.e}
end

function M:mount(manager)
    if not enabled() or not managers or manager ~= managers.hud then return end
    local rt=kyohud.hud.runtime
    local parent=rt and rt._mounted and rt._root_panel
    if not live(parent) then return end
    if live(self._root) and self._parent==parent then return end
    if self._root then self:unmount() end
    local component=kyohud.hud.equipment_component
    if not component then return end
    local ok,existing=safe_call(parent,"child","kyohud_equipment_panel")
    if not ok or existing then return end
    local made,root=safe_call(parent,"panel",{name="kyohud_equipment_panel",layer=1})
    if not made or not root then return end
    self._root=root;self._parent=parent;self._manager=manager;self._rows={}

    for i=1,6 do
        local row=component.new(root,"equipment_row"..i)
        if not row then self:unmount();return end
        self._rows[i]=row
    end
    self._mounted=true
    self._texts={
        deployable=loc("ky_hud_equipment_deployable","EQUIPMENT"),
        cables=loc("ky_hud_equipment_cables","CABLE TIES"),
        throwable=loc("ky_hud_equipment_throwable","THROWABLE"),
        ability=loc("ky_hud_equipment_ability","ABILITY"),
        cooldown=loc("ky_hud_equipment_cooldown","RECHARGE"),
        active=loc("ky_hud_equipment_active","ACTIVE"),
        unlimited=loc("ky_hud_equipment_unlimited","UNLIMITED")}
    self._names={}
    self:refresh(manager)
    self:_present()
end

function M:unmount()
    if self._rows then for _,row in ipairs(self._rows) do row:destroy() end end
    if live(self._parent) and live(self._root) then
        local ok,child=safe_call(self._parent,"child","kyohud_equipment_panel")
        if ok and child==self._root then safe_call(self._parent,"remove",self._root) end
    end
    self._root=nil;self._rows=nil;self._parent=nil;self._mounted=false;self._layout=nil;self._temporal_height=nil
    self._last_ui=nil;self._last_poll=nil
    self._icon_cache=nil
    self._required_width=nil;self._required_scale=nil
    self._kingpin_present_cache=nil
    self._kingpin_source_cache=nil
    self._grenade_flash_ok=false
    self._grenade_flash_source=nil
    self._grenade_flash_rejected=nil
end

function M:_name(id, key, fallback)
    if not id or not key then return fallback end
    local cached=self._names[id]
    if not cached or cached.key~=key then
        cached={key=key,text=loc(key,fallback)};self._names[id]=cached
    end
    return cached.text
end

local PROJECTILE_ICON_DEFAULT = {0, 0, 32, 32}
local FLASH_GROUP = "local_p_grenade_flash"
local FLASH_BASE_LEASE = "local_p_cooldown"
local FLASH_SOURCES = {
    {base = "grenades_radial", ghost = "grenades_radial_ghost"},
    {base = "grenades_icon", ghost = "grenades_icon_ghost"},
}
-- The accepted owned pulse fades 1 -> 0 over the first 0.6 game-seconds.
-- Past that deadline it may continue only while both exact retained native
-- ghosts still expose a positively observed, correctly scaled white phase;
-- the extension keeps a perceptible cyan floor. The finite watchdog cancels
-- a stalled positive native source after 2.0 extension seconds. It never
-- authorizes a mask on its own and is never reset by ordinary reads.
local EVENT_NATIVE_EXTENSION_ALPHA = .5
local EVENT_NATIVE_EXTENSION_LIMIT = 2.0

-- Resource lookup is bounded to a new icon identifier, never repeated per draw.
-- The projectile channel forwards the native 32x32 default rect and keeps its
-- own cache bucket so it never aliases an ordinary default-rect lookup.
function M:_icon(id, projectile_default)
    if type(id)~="string" then return nil end
    self._icon_cache=self._icon_cache or {}
    local bucket_key=projectile_default and "projectile32" or "default"
    local bucket=self._icon_cache[bucket_key]
    if type(bucket)~="table" then bucket={};self._icon_cache[bucket_key]=bucket end
    if bucket[id]~=nil then return bucket[id] or nil end
    local default_rect
    if projectile_default then
        default_rect={projectile_default[1],projectile_default[2],projectile_default[3],projectile_default[4]}
    end
    local ok,result=pcall(function()
        local texture,rect=tweak_data.hud_icons:get_icon_data(id,default_rect)
        if type(texture)~="string" or type(rect)~="table" then return nil end
        for i=1,4 do if type(rect[i])~="number" or rect[i]~=rect[i] or math.abs(rect[i])==math.huge then return nil end end
        if rect[3]<=0 or rect[4]<=0 then return nil end
        if not DB:has(Idstring("texture"),Idstring(texture)) then return nil end
        return {texture=texture,rect={rect[1],rect[2],rect[3],rect[4]}}
    end)
    bucket[id]=ok and result or false
    return ok and result or nil
end

local function hacker_idstring_key(value)
    if value == nil then return nil end
    if type(value) == "string" then return value end
    local ok, key = pcall(function() return value:key() end)
    if ok and key ~= nil then return key end
    return nil
end

local function hacker_texture_matches(actual, expected)
    if type(expected) ~= "string" or expected == "" then return false end
    if type(actual) == "string" then
        if actual == expected then return true end
        local ok_actual, actual_id = pcall(Idstring, actual)
        local ok_expected, expected_id = pcall(Idstring, expected)
        if not ok_actual or not ok_expected
            or actual_id == nil or expected_id == nil then return false end
        local actual_key = hacker_idstring_key(actual_id)
        local expected_key = hacker_idstring_key(expected_id)
        return actual_key ~= nil and actual_key == expected_key
    end
    local ok_expected, expected_id = pcall(Idstring, expected)
    if not ok_expected or expected_id == nil then return false end
    local actual_key = hacker_idstring_key(actual)
    local expected_key = hacker_idstring_key(expected_id)
    return actual_key ~= nil and actual_key == expected_key
end

local function hacker_root_exposed(equipment)
    local root = equipment._root
    local parent = equipment._parent
    if not live(root) or not live(parent) then return false end
    local vs, visible = safe_call(root, "visible")
    if not vs or visible ~= true then return false end
    local as, alpha = safe_call(root, "alpha")
    if not as or not finite(alpha) or alpha <= 0 then return false end
    local current = root
    local depth = 0
    while current ~= parent and depth < 8 do
        local ps, up = safe_call(current, "parent")
        if not ps or not live(up) then return false end
        local pvs, pvisible = safe_call(up, "visible")
        if not pvs or pvisible ~= true then return false end
        local pas, palpha = safe_call(up, "alpha")
        if not pas or not finite(palpha) or palpha <= 0 then return false end
        current = up
        depth = depth + 1
    end
    return current == parent
end

function M:_hacker_root_exposed()
    return hacker_root_exposed(self)
end

-- Silent, non-mutating source read. Returns a fresh table only while the exact
-- retained local event, its identity chain, its inventory record and the game
-- clock still agree. Non-Hacker activity is never reported here.
function M:get_hacker_activity_source()
    local prov = self._hacker_activity
    if type(prov) ~= "table" then return nil end
    if type(prov.activity) ~= "table" or prov.activity ~= self._activity
        or prov.activity.source ~= HACKER_ACTIVITY_SOURCE
        or prov.activity.known ~= true or prov.activity.active ~= true then
        return nil
    end
    local pm = managers and managers.player
    if not managers or not pm then return nil end
    if prov.manager ~= managers.hud or prov.hud_manager ~= self._hud_manager then return nil end
    if prov.player_manager ~= self._player_manager or prov.player_manager ~= pm then return nil end
    if prov.player_unit ~= self._player_unit then return nil end
    local unit_ok, unit = safe_call(pm, "player_unit")
    if not unit_ok or unit == nil or unit ~= prov.player_unit then return nil end
    if type(alive) == "function" then
        local alive_ok, is_alive = pcall(alive, unit)
        if not alive_ok or is_alive ~= true then return nil end
    end
    if prov.session ~= self._session or prov.peer_id ~= self._peer_id then return nil end
    if self._session ~= prov.session then return nil end
    local session_ok, session = safe_call(managers.network, "session")
    if not session_ok or session ~= prov.session then return nil end
    local peer_ok, peer = safe_call(session, "local_peer")
    if not peer_ok or not peer then return nil end
    local id_ok, peer_id = safe_call(peer, "id")
    if not id_ok or peer_id ~= prov.peer_id then return nil end
    if prov.equipment ~= self._equipment_table or prov.selections ~= self._selections_table then
        return nil
    end
    if pm._equipment ~= prov.equipment or pm._equipment.selections ~= prov.selections then
        return nil
    end
    if prov.registry ~= self._grenade_registry or prov.gpc ~= self._gpc then return nil end
    if pm._global and pm._global.synced_grenades ~= prov.registry then return nil end
    if managers.game_play_central ~= prov.gpc then return nil end
    if prov.generation ~= self._source_generation then return nil end
    if prov.projectile_id ~= HACKER_PROJECTILE_ID then return nil end
    if self._projectile_id ~= HACKER_PROJECTILE_ID then return nil end
    local got, entry = safe_call(pm, "get_synced_grenades", prov.peer_id)
    if not got or type(entry) ~= "table" or entry.grenade ~= HACKER_PROJECTILE_ID then
        return nil
    end
    if not is_valid_positive_quantity(prov.duration) or not is_valid_known_quantity(prov.deadline) then
        return nil
    end
    local now, clock = current_game_time()
    if now == nil or clock == nil or clock ~= prov.clock then return nil end
    if now < prov.start then return nil end
    local last = prov.last_seen
    if not is_valid_known_quantity(last) then last = prov.start end
    if now < last then return nil end
    prov.last_seen = now
    if now >= prov.deadline then return nil end
    local jammer = self:_read_local_jammer_record(prov.player_unit)
    if not jammer or jammer.inventory ~= prov.inventory or jammer.data ~= prov.jammer then
        return nil
    end
    if now >= jammer.t then return nil end
    prov.jammer_effect = jammer.effect
    prov.jammer_t = jammer.t
    local remaining = prov.deadline - now
    if not is_valid_positive_quantity(remaining) then return nil end
    local projectiles = tweak_data and tweak_data.blackmarket and tweak_data.blackmarket.projectiles
    local td = projectiles and projectiles[HACKER_PROJECTILE_ID]
    local icon_id = type(td) == "table" and td.icon or nil
    local icon = self:_icon(icon_id, PROJECTILE_ICON_DEFAULT)
    return {
        kind = prov.kind,
        event_id = prov.event_id,
        event_serial = prov.serial,
        activity = prov.activity,
        projectile_id = HACKER_PROJECTILE_ID,
        manager = prov.manager,
        hud_manager = prov.hud_manager,
        player_manager = prov.player_manager,
        player_unit = prov.player_unit,
        session = prov.session,
        peer_id = prov.peer_id,
        equipment = prov.equipment,
        selections = prov.selections,
        registry = prov.registry,
        gpc = prov.gpc,
        generation = prov.generation,
        source_generation = prov.generation,
        clock = prov.clock,
        start = prov.start,
        last_seen = now,
        deadline = prov.deadline,
        duration = prov.duration,
        remaining = remaining,
        active = true,
        local_inventory = prov.inventory,
        jammer = prov.jammer,
        jammer_effect = jammer.effect,
        jammer_t = jammer.t,
        icon_id = icon_id,
        icon = icon,
    }
end

function M:_verify_hacker_activity(source)
    self._hacker_activity_ok = false
    source = source or self:get_hacker_activity_source()
    if type(source) ~= "table" or source.active ~= true then return false end
    local ok, result = pcall(function()
        if not enabled() then return false end
        if not live(self._root) or not live(self._parent) or type(self._rows) ~= "table" then
            return false
        end
        if not hacker_root_exposed(self) then return false end
        if self:verify() ~= true then return false end
        if type(self._texts) ~= "table" then return false end
        if not is_valid_positive_quantity(source.duration)
            or not is_valid_positive_quantity(source.remaining) then return false end
        local row6 = self._rows[6]
        if not row6 or not live(row6._root) or not live(row6._label)
            or not live(row6._value) then return false end
        if type(self._visible_rows) ~= "table" or self._visible_rows[6] ~= true then
            return false
        end
        local expected_value = string.format("%ds", math.ceil(source.remaining))
        local expected_progress = math.min(1, math.max(0, source.remaining / source.duration))
        local label_ok, label = safe_call(row6._label, "text")
        local value_ok, value = safe_call(row6._value, "text")
        if not label_ok or label ~= self._texts.active then return false end
        if not value_ok or value ~= expected_value then return false end
        if not finite(row6._progress)
            or math.abs(row6._progress - expected_progress) > 0.001 then return false end
        if row6:verify() ~= true then return false end
        local row4 = self._rows[4]
        if not row4 or not live(row4._root) or not live(row4._icon) then return false end
        if type(self._visible_rows) ~= "table" or self._visible_rows[4] ~= true then
            return false
        end
        if row4._icon:visible() ~= true then return false end
        local descriptor = row4._icon_descriptor
        local expected_texture = type(source.icon) == "table" and source.icon.texture or nil
        if type(source.icon_id) ~= "string" or type(expected_texture) ~= "string"
            or type(descriptor) ~= "table" or descriptor.texture ~= expected_texture then
            return false
        end
        local texture = row4._icon:texture_name()
        if not hacker_texture_matches(texture, expected_texture) then return false end
        if row4:verify() ~= true then return false end
        return true
    end)
    self._hacker_activity_ok = ok and result == true
    return self._hacker_activity_ok
end

function M:prepare_hacker_activity_event()
    self._hacker_activity_ok = false
    if not live(self._root) or not live(self._parent) or type(self._rows) ~= "table" then
        return false
    end
    self:_present()
    return self:_verify_hacker_activity(self:get_hacker_activity_source())
end

-- Kingpin source read. The retained publication scalar stays frozen between
-- publications; Application is only compared with its own record expiry and is
-- required to be monotonic for the same exact record.
function M:get_kingpin_activity_source()
    local prov = self._kingpin_activity
    if type(prov) ~= "table" then return nil end
    if prov.invalid == true then return nil end
    local cached = self._kingpin_source_cache
    if cached ~= nil and cached.prov == prov then
        return cached.source
    end
    local function reject(reason)
        reason = reason or "source_guard"
        local RT = kyohud.hud.runtime
        if type(RT) == "table" and type(RT._kingpin_transition) == "function" then
            pcall(RT._kingpin_transition, RT, "source_reject", reason, prov)
        end
        prov.invalid = true
        if KINGPIN_TERMINAL_REASONS[reason] == true then
            prov.terminal_candidate = reason
            if is_valid_positive_quantity(prov.remaining) then
                prov.terminal_remaining = prov.remaining
            end
            if is_valid_positive_quantity(prov.published_total) then
                prov.terminal_total = prov.published_total
            end
        end
        if type(prov.activity) == "table" then
            prov.activity.known = false
            prov.activity.active = false
        end
        return nil
    end
    if type(prov.activity) ~= "table" or prov.activity ~= self._activity
        or prov.activity.source ~= KINGPIN_ACTIVITY_SOURCE
        or prov.activity.known ~= true or prov.activity.active ~= true then
        return reject()
    end
    local pm = managers and managers.player
    if not managers or not pm then return reject() end
    if prov.manager ~= managers.hud or prov.hud_manager ~= self._hud_manager then return reject() end
    if prov.player_manager ~= self._player_manager or prov.player_manager ~= pm then return reject() end
    if prov.player_unit ~= self._player_unit then return reject() end
    local unit_ok, unit = safe_call(pm, "player_unit")
    if not unit_ok or unit == nil or unit ~= prov.player_unit then return reject() end
    if type(alive) == "function" then
        local alive_ok, is_alive = pcall(alive, unit)
        if not alive_ok or is_alive ~= true then return reject() end
    end
    local cd_ok, character_damage = safe_call(unit, "character_damage")
    if not cd_ok or character_damage ~= prov.character_damage then return reject() end
    if prov.session ~= self._session or prov.peer_id ~= self._peer_id then return reject() end
    if self._session ~= prov.session then return reject() end
    local session_ok, session = safe_call(managers.network, "session")
    if not session_ok or session ~= prov.session then return reject() end
    local peer_ok, peer = safe_call(session, "local_peer")
    if not peer_ok or not peer then return reject() end
    local id_ok, peer_id = safe_call(peer, "id")
    if not id_ok or peer_id ~= prov.peer_id then return reject() end
    if prov.equipment ~= self._equipment_table or prov.selections ~= self._selections_table then
        return reject()
    end
    if pm._equipment ~= prov.equipment or pm._equipment.selections ~= prov.selections then
        return reject()
    end
    if prov.registry ~= self._grenade_registry or prov.gpc ~= self._gpc then return reject() end
    if pm._global and pm._global.synced_grenades ~= prov.registry then return reject() end
    if managers.game_play_central ~= prov.gpc then return reject() end
    if prov.generation ~= self._source_generation then return reject() end
    if prov.projectile_id ~= KINGPIN_PROJECTILE_ID then return reject() end
    if self._projectile_id ~= KINGPIN_PROJECTILE_ID then return reject() end
    local got, entry = safe_call(pm, "get_synced_grenades", prov.peer_id)
    if not got or type(entry) ~= "table" or entry.grenade ~= KINGPIN_PROJECTILE_ID then
        return reject()
    end
    local upgrades = pm._temporary_upgrades
    local category = type(upgrades) == "table" and upgrades.temporary or nil
    local record = type(category) == "table" and category.chico_injector or nil
    if upgrades ~= prov.temporary_root or category ~= prov.temporary_category
        or record ~= prov.temporary_record then return reject() end
    if type(record) ~= "table" or not is_valid_positive_quantity(record.expire_time) then
        return reject()
    end
    local active_ok, active = safe_call(pm, "has_activate_temporary_upgrade",
        "temporary", KINGPIN_PROJECTILE_ID)
    if not active_ok then return reject("upgrade_unreadable") end
    if active ~= true then return reject("upgrade_inactive") end
    local uv_ok, upgrade = safe_call(pm, "upgrade_value", "temporary", KINGPIN_PROJECTILE_ID)
    local duration = uv_ok and type(upgrade) == "table" and upgrade[2] or nil
    if not is_valid_positive_quantity(duration)
        or math.abs(duration - prov.duration) > 0.001 then return reject() end
    local app = _G.Application
    if app == nil or app ~= prov.application then return reject() end
    local app_ok, app_now = safe_call(app, "time")
    if not app_ok or not is_valid_known_quantity(app_now) then return reject() end
    if app_now < prov.last_application then return reject() end
    prov.last_application = app_now
    if not (record.expire_time > app_now) then return reject("expired") end
    if prov.player_timer ~= nil then
        local ptm_ok, player_timer = safe_call(pm, "player_timer")
        if not ptm_ok or player_timer == nil or player_timer ~= prov.player_timer then return reject() end
        local pt_ok, player_time = safe_call(prov.player_timer, "time")
        if not pt_ok or not is_valid_known_quantity(player_time) then return reject() end
        if prov.player_time ~= nil and player_time < prov.player_time then return reject() end
        prov.player_time = player_time
    end
    if prov.game_timer ~= nil then
        local gtm_ok, game_timer = safe_call(TimerManager, "game")
        if not gtm_ok or game_timer == nil or game_timer ~= prov.game_timer then return reject() end
        local gt_ok, game_time = safe_call(prov.game_timer, "time")
        if not gt_ok or not is_valid_known_quantity(game_time) then return reject() end
        if prov.game_time ~= nil and game_time < prov.game_time then return reject() end
        prov.game_time = game_time
    end
    if not is_valid_positive_quantity(prov.remaining) or not (prov.remaining > 0) then
        return reject()
    end
    if prov.remaining > duration + 0.001 then return reject() end
    local projectiles = tweak_data and tweak_data.blackmarket and tweak_data.blackmarket.projectiles
    local td = projectiles and projectiles[KINGPIN_PROJECTILE_ID]
    local icon_id = type(td) == "table" and td.icon or nil
    local icon = self:_icon(icon_id, PROJECTILE_ICON_DEFAULT)
    local result = {
        kind = KINGPIN_ACTIVITY_SOURCE,
        event_id = prov.event_id,
        event_serial = prov.serial,
        activity = prov.activity,
        projectile_id = KINGPIN_PROJECTILE_ID,
        manager = prov.manager,
        hud_manager = prov.hud_manager,
        player_manager = prov.player_manager,
        player_unit = prov.player_unit,
        character_damage = prov.character_damage,
        session = prov.session,
        peer_id = prov.peer_id,
        equipment = prov.equipment,
        selections = prov.selections,
        registry = prov.registry,
        gpc = prov.gpc,
        generation = prov.generation,
        source_generation = prov.generation,
        temporary_root = prov.temporary_root,
        temporary_category = prov.temporary_category,
        temporary_record = prov.temporary_record,
        expire_time = record.expire_time,
        application = app,
        application_now = app_now,
        clock = app,
        start = prov.start_application,
        last_seen = app_now,
        duration = duration,
        remaining = prov.remaining,
        published_total = prov.published_total,
        active = true,
        icon_id = icon_id,
        icon = icon,
    }
    self._kingpin_source_cache = { prov = prov, source = result }
    return result
end

-- Terminal Kingpin proof. This getter is never used by the generic ACTIVE
-- dispatch: it only reads an invalidated positive provenance whose natural end
-- reason was an inactive/expired temporary upgrade. Every retained identity is
-- re-proved independently, the exact record must already be past its own
-- Application deadline and the same publication is preserved without inventing
-- remaining seconds. Any loss of proof latches this provenance terminal-invalid.
function M:get_kingpin_terminal_source()
    local prov = self._kingpin_activity
    if type(prov) ~= "table" then return nil end
    if prov.invalid ~= true then return nil end
    local reason = prov.terminal_candidate
    if KINGPIN_TERMINAL_REASONS[reason] ~= true then return nil end
    if prov.terminal_invalid == true then return nil end
    local function reject()
        prov.terminal_invalid = true
        return nil
    end
    if type(prov.activity) ~= "table" or prov.activity ~= self._activity
        or prov.activity.source ~= KINGPIN_ACTIVITY_SOURCE then
        return reject()
    end
    local pm = managers and managers.player
    if not managers or not pm then return reject() end
    if prov.manager ~= managers.hud or prov.hud_manager ~= self._hud_manager then return reject() end
    if prov.player_manager ~= self._player_manager or prov.player_manager ~= pm then return reject() end
    if prov.player_unit ~= self._player_unit then return reject() end
    local unit_ok, unit = safe_call(pm, "player_unit")
    if not unit_ok or unit == nil or unit ~= prov.player_unit then return reject() end
    if type(alive) == "function" then
        local alive_ok, is_alive = pcall(alive, unit)
        if not alive_ok or is_alive ~= true then return reject() end
    end
    local cd_ok, character_damage = safe_call(unit, "character_damage")
    if not cd_ok or character_damage ~= prov.character_damage then return reject() end
    if prov.session ~= self._session or prov.peer_id ~= self._peer_id then return reject() end
    if self._session ~= prov.session then return reject() end
    local session_ok, session = safe_call(managers.network, "session")
    if not session_ok or session ~= prov.session then return reject() end
    local peer_ok, peer = safe_call(session, "local_peer")
    if not peer_ok or not peer then return reject() end
    local id_ok, peer_id = safe_call(peer, "id")
    if not id_ok or peer_id ~= prov.peer_id then return reject() end
    if prov.equipment ~= self._equipment_table or prov.selections ~= self._selections_table then
        return reject()
    end
    if pm._equipment ~= prov.equipment or pm._equipment.selections ~= prov.selections then
        return reject()
    end
    if prov.registry ~= self._grenade_registry or prov.gpc ~= self._gpc then return reject() end
    if pm._global and pm._global.synced_grenades ~= prov.registry then return reject() end
    if managers.game_play_central ~= prov.gpc then return reject() end
    if prov.generation ~= self._source_generation then return reject() end
    if prov.projectile_id ~= KINGPIN_PROJECTILE_ID then return reject() end
    if self._projectile_id ~= KINGPIN_PROJECTILE_ID then return reject() end
    local got, entry = safe_call(pm, "get_synced_grenades", prov.peer_id)
    if not got or type(entry) ~= "table" or entry.grenade ~= KINGPIN_PROJECTILE_ID then
        return reject()
    end
    local upgrades = pm._temporary_upgrades
    local category = type(upgrades) == "table" and upgrades.temporary or nil
    local record = type(category) == "table" and category.chico_injector or nil
    if upgrades ~= prov.temporary_root or category ~= prov.temporary_category
        or record ~= prov.temporary_record then return reject() end
    if type(record) ~= "table" or not is_valid_positive_quantity(record.expire_time) then
        return reject()
    end
    if not finite(prov.expire_time) or record.expire_time ~= prov.expire_time then
        return reject()
    end
    local active_ok, active = safe_call(pm, "has_activate_temporary_upgrade",
        "temporary", KINGPIN_PROJECTILE_ID)
    if not active_ok then return reject() end
    if active ~= false then return reject() end
    local uv_ok, upgrade = safe_call(pm, "upgrade_value", "temporary", KINGPIN_PROJECTILE_ID)
    local duration = uv_ok and type(upgrade) == "table" and upgrade[2] or nil
    if not is_valid_positive_quantity(duration)
        or not is_valid_positive_quantity(prov.duration)
        or math.abs(duration - prov.duration) > 0.001 then return reject() end
    local app = _G.Application
    if app == nil or app ~= prov.application then return reject() end
    local app_ok, app_now = safe_call(app, "time")
    if not app_ok or not is_valid_known_quantity(app_now) then return reject() end
    if not is_valid_known_quantity(prov.last_application) then return reject() end
    if app_now < prov.last_application then return reject() end
    prov.last_application = app_now
    if not (record.expire_time <= app_now) then return reject() end
    if prov.player_timer ~= nil then
        local ptm_ok, player_timer = safe_call(pm, "player_timer")
        if not ptm_ok or player_timer == nil or player_timer ~= prov.player_timer then return reject() end
        local pt_ok, player_time = safe_call(prov.player_timer, "time")
        if not pt_ok or not is_valid_known_quantity(player_time) then return reject() end
        if prov.player_time ~= nil and player_time < prov.player_time then return reject() end
        prov.player_time = player_time
    end
    if prov.game_timer ~= nil then
        local gtm_ok, game_timer = safe_call(TimerManager, "game")
        if not gtm_ok or game_timer == nil or game_timer ~= prov.game_timer then return reject() end
        local gt_ok, game_time = safe_call(prov.game_timer, "time")
        if not gt_ok or not is_valid_known_quantity(game_time) then return reject() end
        if prov.game_time ~= nil and game_time < prov.game_time then return reject() end
        prov.game_time = game_time
    end
    local published_remaining = prov.terminal_remaining
    if not is_valid_positive_quantity(published_remaining) then
        published_remaining = prov.remaining
    end
    local published_total = prov.terminal_total
    if not is_valid_positive_quantity(published_total) then
        published_total = prov.published_total
    end
    if not is_valid_positive_quantity(published_remaining)
        or not is_valid_positive_quantity(published_total) then return reject() end
    if published_remaining > published_total + 0.001 then return reject() end
    local projectiles = tweak_data and tweak_data.blackmarket and tweak_data.blackmarket.projectiles
    local td = projectiles and projectiles[KINGPIN_PROJECTILE_ID]
    local icon_id = type(td) == "table" and td.icon or nil
    if type(icon_id) ~= "string" then return reject() end
    local icon = self:_icon(icon_id, PROJECTILE_ICON_DEFAULT)
    if type(icon) ~= "table" or type(icon.texture) ~= "string" then return reject() end
    return {
        kind = KINGPIN_TERMINAL_SOURCE,
        event_id = prov.event_id,
        event_serial = prov.serial,
        projectile_id = KINGPIN_PROJECTILE_ID,
        manager = prov.manager,
        hud_manager = prov.hud_manager,
        player_manager = prov.player_manager,
        player_unit = prov.player_unit,
        character_damage = prov.character_damage,
        session = prov.session,
        peer_id = prov.peer_id,
        equipment = prov.equipment,
        selections = prov.selections,
        registry = prov.registry,
        gpc = prov.gpc,
        generation = prov.generation,
        source_generation = prov.generation,
        temporary_root = prov.temporary_root,
        temporary_category = prov.temporary_category,
        temporary_record = prov.temporary_record,
        expire_time = record.expire_time,
        application = app,
        application_now = app_now,
        clock = app,
        duration = duration,
        published_remaining = published_remaining,
        published_total = published_total,
        published_ratio = published_remaining / published_total,
        terminal = true,
        terminal_reason = reason,
        active = false,
        icon_id = icon_id,
        icon = icon,
    }
end

function M:_verify_kingpin_activity(source)
    self._kingpin_activity_ok = false
    source = source or self:get_kingpin_activity_source()
    if type(source) ~= "table" or source.active ~= true then return false end
    local ok, result = pcall(function()
        if not enabled() then return false end
        if not live(self._root) or not live(self._parent) or type(self._rows) ~= "table" then
            return false
        end
        if not hacker_root_exposed(self) then return false end
        local verifier = self.verify
        local verified, receipt = verifier(self, KINGPIN_VERIFY_RECEIPT)
        if verified ~= true then return false end
        local receipt_ok = receipt == KINGPIN_VERIFY_RECEIPT
            and type(self._residual_phase_wrappers) == "table"
            and self.verify == verifier
            and self.verify == self._residual_phase_wrappers.verify
        if type(self._texts) ~= "table" then return false end
        if not is_valid_positive_quantity(source.duration)
            or not is_valid_positive_quantity(source.remaining) then return false end
        local row6 = self._rows[6]
        if not row6 or not live(row6._root) or not live(row6._label)
            or not live(row6._value) then return false end
        if type(self._visible_rows) ~= "table" or self._visible_rows[6] ~= true then
            return false
        end
        local expected_value = string.format("%ds", math.ceil(source.remaining))
        local expected_progress = math.min(1, math.max(0, source.remaining / source.duration))
        local label_ok, label = safe_call(row6._label, "text")
        local value_ok, value = safe_call(row6._value, "text")
        if not label_ok or label ~= self._texts.active then return false end
        if not value_ok or value ~= expected_value then return false end
        if not finite(row6._progress)
            or math.abs(row6._progress - expected_progress) > 0.001 then return false end
        if not receipt_ok and row6:verify() ~= true then return false end
        local row4 = self._rows[4]
        if not row4 or not live(row4._root) or not live(row4._icon) then return false end
        if type(self._visible_rows) ~= "table" or self._visible_rows[4] ~= true then
            return false
        end
        if row4._icon:visible() ~= true then return false end
        local descriptor = row4._icon_descriptor
        local expected_texture = type(source.icon) == "table" and source.icon.texture or nil
        if type(source.icon_id) ~= "string" or type(expected_texture) ~= "string"
            or type(descriptor) ~= "table" or descriptor.texture ~= expected_texture then
            return false
        end
        local texture = row4._icon:texture_name()
        if not hacker_texture_matches(texture, expected_texture) then return false end
        if not receipt_ok and row4:verify() ~= true then return false end
        return true
    end)
    self._kingpin_activity_ok = ok and result == true
    return self._kingpin_activity_ok
end

function M:prepare_kingpin_activity_event()
    self._kingpin_activity_ok = false
    if not live(self._root) or not live(self._parent) or type(self._rows) ~= "table" then
        return false
    end
    self:_present()
    return self:_verify_kingpin_activity(self:get_kingpin_activity_source())
end

-- Terminal-owned rendering has no ACTIVE row. It certifies the current inactive
-- snapshot actually produced by _present: fresh full equipment verification,
-- exposed owned root, absent row 6 root/visible-row and the exact row 4 icon
-- descriptor/resource. No native value is written.
function M:_verify_kingpin_terminal(source)
    self._kingpin_terminal_ok = false
    source = source or self:get_kingpin_terminal_source()
    if type(source) ~= "table" or source.kind ~= KINGPIN_TERMINAL_SOURCE
        or source.active ~= false then return false end
    local ok, result = pcall(function()
        if not enabled() then return false end
        if not live(self._root) or not live(self._parent) or type(self._rows) ~= "table" then
            return false
        end
        local wrappers = self._residual_phase_wrappers
        if type(wrappers) ~= "table" or type(wrappers.verify) ~= "function"
            or self.verify ~= wrappers.verify then
            return false
        end
        if not hacker_root_exposed(self) then return false end
        if self:verify() ~= true then return false end
        if type(self._texts) ~= "table" then return false end
        local visible_rows = self._visible_rows
        if type(visible_rows) ~= "table" then return false end
        local row6 = self._rows[6]
        if not row6 or not live(row6._root) then return false end
        if visible_rows[6] == true then return false end
        local r6_ok, r6_visible = safe_call(row6._root, "visible")
        if not r6_ok or r6_visible ~= false then return false end
        local row4 = self._rows[4]
        if not row4 or not live(row4._root) or not live(row4._icon) then return false end
        if visible_rows[4] ~= true then return false end
        local icon_ok, icon_visible = safe_call(row4._icon, "visible")
        if not icon_ok or icon_visible ~= true then return false end
        local descriptor = row4._icon_descriptor
        local expected_texture = type(source.icon) == "table" and source.icon.texture or nil
        if type(source.icon_id) ~= "string" or type(expected_texture) ~= "string"
            or type(descriptor) ~= "table" or descriptor.texture ~= expected_texture then
            return false
        end
        local texture = row4._icon:texture_name()
        if not hacker_texture_matches(texture, expected_texture) then return false end
        if row4:verify() ~= true then return false end
        return true
    end)
    self._kingpin_terminal_ok = ok and result == true
    return self._kingpin_terminal_ok
end

function M:_prepare_kingpin_terminal_event(source)
    self._kingpin_terminal_ok = false
    if not live(self._root) or not live(self._parent) or type(self._rows) ~= "table" then
        return false
    end
    self:_present()
    local fresh = self:get_kingpin_terminal_source()
    if type(fresh) ~= "table"
        or (type(source) == "table" and fresh.event_id ~= source.event_id) then
        return false
    end
    return self:_verify_kingpin_terminal(fresh)
end

-- Narrow internal dispatch used by the single exclusive lease. Hacker keeps its
-- strict public getter; only the selected positive source is exposed here.
function M:get_local_ability_activity_source()
    local source = self:get_hacker_activity_source()
    if type(source) == "table" and source.kind == HACKER_ACTIVITY_SOURCE then
        return source
    end
    local kingpin = self:get_kingpin_activity_source()
    if type(kingpin) == "table" and kingpin.kind == KINGPIN_ACTIVITY_SOURCE then
        return kingpin
    end
    return nil
end

function M:_verify_local_ability_activity(source)
    self._hacker_activity_ok = false
    self._kingpin_activity_ok = false
    if type(source) ~= "table" then return false end
    if source.kind == HACKER_ACTIVITY_SOURCE then
        return self:_verify_hacker_activity(source)
    end
    if source.kind == KINGPIN_ACTIVITY_SOURCE then
        return self:_verify_kingpin_activity(source)
    end
    return false
end

function M:prepare_local_ability_activity_event()
    self._hacker_activity_ok = false
    self._kingpin_activity_ok = false
    if not live(self._root) or not live(self._parent) or type(self._rows) ~= "table" then
        return false
    end
    local kingpin_attempt = self._projectile_id == KINGPIN_PROJECTILE_ID
    local incremental = false
    local fast_reason
    if kingpin_attempt then
        residual_count("kingpin_prepare_attempt")
        local source = self:get_local_ability_activity_source()
        if type(source) == "table" and source.kind == KINGPIN_ACTIVITY_SOURCE then
            local ok, presented, reason = pcall(self._present_kingpin_activity_event, self, source)
            if ok then
                incremental = presented == true
                fast_reason = reason
            else
                fast_reason = "exception"
            end
        else
            fast_reason = "source"
        end
    end
    if not incremental then
        if kingpin_attempt then
            residual_count_kingpin_reject(fast_reason or "other")
            residual_count("kingpin_prepare_full")
        end
        self:_present()
    end
    local fresh = self:get_local_ability_activity_source()
    local verified = self:_verify_local_ability_activity(fresh)
    if incremental and verified ~= true then
        if kingpin_attempt then
            residual_count_kingpin_reject("postverify")
            residual_count("kingpin_prepare_full")
        end
        self:_present()
        fresh = self:get_local_ability_activity_source()
        verified = self:_verify_local_ability_activity(fresh)
        incremental = false
    end
    if kingpin_attempt and incremental and verified == true then
        residual_count("kingpin_prepare_fast")
    end
    return verified
end

local function flash_child(parent, name)
    if not live(parent) then return nil end
    local ok, child = safe_call(parent, "child", name)
    if not ok or not live(child) then return nil end
    local ok_parent, immediate = safe_call(child, "parent")
    if not ok_parent or immediate ~= parent then return nil end
    return child
end

local function flash_group_holds_visible(group_key, panel)
    local rt = kyohud.hud.runtime
    if not rt or type(rt._h5_group_holds_visible) ~= "function" then return false end
    local ok, held = pcall(rt._h5_group_holds_visible, rt, group_key, panel)
    return ok and held == true
end

local function flash_leaf_state(panel, require_white, lease_group)
    if not live(panel) then return nil, "not_live" end
    local ok_visible, visible = safe_call(panel, "visible")
    if not ok_visible or (visible ~= true and visible ~= false) then return nil, "visible_unknown" end
    if visible ~= true and not flash_group_holds_visible(lease_group, panel) then
        return nil, "hidden_unleased"
    end
    local ok_alpha, alpha = safe_call(panel, "alpha")
    if not ok_alpha or not finite(alpha) or alpha < 0 or alpha > 1 then
        return nil, "alpha_unknown"
    end
    local ok_x, x = safe_call(panel, "x")
    local ok_y, y = safe_call(panel, "y")
    local ok_w, w = safe_call(panel, "w")
    local ok_h, h = safe_call(panel, "h")
    if not ok_x or not ok_y or not ok_w or not ok_h then return nil, "geometry_unknown" end
    if not finite(x) or not finite(y) or not finite(w) or not finite(h) then
        return nil, "geometry_invalid"
    end
    if w <= 0 or h <= 0 then return nil, "geometry_nonpositive" end
    local phase_alpha = alpha
    if require_white then
        local ok_color, color = safe_call(panel, "color")
        if not ok_color or not color then return nil, "color_unknown" end
        if not finite(color.r) or not finite(color.g) or not finite(color.b) then
            return nil, "color_channels_unknown"
        end
        if math.abs(color.r - 1) > 0.001 or math.abs(color.g - 1) > 0.001
            or math.abs(color.b - 1) > 0.001 then return nil, "color_not_white" end
        if not finite(color.a) or color.a < 0 or color.a > 1 then
            return nil, "color_alpha_unknown"
        end
        phase_alpha = color.a
    end
    return {alpha = phase_alpha, x = x, y = y, w = w, h = h}
end

local function flash_trace_number(value)
    if finite(value) then return string.format("%.17g", value) end
    return "unknown"
end

local function flash_trace_bool(value)
    if value == true then return "true" end
    if value == false then return "false" end
    return "unknown"
end

local function flash_trace_visible(ok, value)
    if ok == true and (value == true or value == false) then return value end
    return nil
end

local function flash_panel_observation(label, panel)
    local ok, text = pcall(function()
        if not panel then return label .. "_missing" end
        local vs, visible = safe_call(panel, "visible")
        local as, alpha = safe_call(panel, "alpha")
        local cs, color = safe_call(panel, "color")
        local xs, x = safe_call(panel, "x")
        local ys, y = safe_call(panel, "y")
        local ws, w = safe_call(panel, "w")
        local hs, h = safe_call(panel, "h")
        local color_text = "unknown"
        if cs == true and color ~= nil
            and finite(color.r) and finite(color.g) and finite(color.b) and finite(color.a) then
            color_text = string.format("%.17g,%.17g,%.17g,%.17g",
                color.r, color.g, color.b, color.a)
        end
        return label .. "_visible=" .. flash_trace_bool(flash_trace_visible(vs, visible))
            .. " " .. label .. "_alpha=" .. flash_trace_number(as == true and alpha or nil)
            .. " " .. label .. "_color=" .. color_text
            .. " " .. label .. "_shape=("
            .. flash_trace_number(xs == true and x or nil) .. ","
            .. flash_trace_number(ys == true and y or nil) .. ","
            .. flash_trace_number(ws == true and w or nil) .. ","
            .. flash_trace_number(hs == true and h or nil) .. ")"
    end)
    if not ok then return label .. "_observation_error=true" end
    return text
end

local function flash_owned_observation(row, source, pcall_ok, rendered, verified)
    local ok, text = pcall(function()
        local flash = type(row) == "table" and row._grenade_flash or nil
        local vs, visible = safe_call(flash, "visible")
        local as, alpha = safe_call(flash, "alpha")
        local ns, name = safe_call(flash, "name")
        local xs, x = safe_call(flash, "x")
        local ys, y = safe_call(flash, "y")
        local ws, w = safe_call(flash, "w")
        local hs, h = safe_call(flash, "h")
        local ps, parent = safe_call(flash, "parent")
        local parent_owned = "unknown"
        if ps == true and row and row._root then
            parent_owned = flash_trace_bool(parent == row._root)
        end
        local child_owned = "unknown"
        if ns == true and type(name) == "string" and row and row._root then
            local cs, child = safe_call(row._root, "child", name)
            if cs == true then child_owned = flash_trace_bool(child == flash) end
        end
        return "source_alpha=" .. flash_trace_number(type(source) == "table" and source.alpha or nil)
            .. " source_scale=" .. flash_trace_number(type(source) == "table" and source.scale or nil)
            .. " render_pcall=" .. flash_trace_bool(pcall_ok)
            .. " render_return=" .. flash_trace_bool(rendered)
            .. " verify=" .. flash_trace_bool(verified)
            .. " flash_present=" .. flash_trace_bool(flash ~= nil)
            .. " flash_visible=" .. flash_trace_bool(flash_trace_visible(vs, visible))
            .. " flash_alpha=" .. flash_trace_number(as == true and alpha or nil)
            .. " flash_name=" .. (ns == true and type(name) == "string" and name or "unknown")
            .. " flash_shape=("
            .. flash_trace_number(xs == true and x or nil) .. ","
            .. flash_trace_number(ys == true and y or nil) .. ","
            .. flash_trace_number(ws == true and w or nil) .. ","
            .. flash_trace_number(hs == true and h or nil) .. ")"
            .. " parent_owned=" .. parent_owned
            .. " child_owned=" .. child_owned
            .. " flash_active=" .. flash_trace_bool(type(row) == "table" and row._flash_active or nil)
    end)
    if not ok then return "owned_observation_error=true" end
    return text
end

local function flash_centered_scaled(ghost, base, scale)
    local function close(a, b) return finite(a) and finite(b) and math.abs(a - b) <= 0.05 end
    return close(ghost.w, base.w * scale) and close(ghost.h, base.h * scale)
        and close(ghost.x + ghost.w * .5, base.x + base.w * .5)
        and close(ghost.y + ghost.h * .5, base.y + base.h * .5)
end

local function flash_event_retained_leaf(event, index)
    local parent = event and event.parent
    local ghosts = event and event.ghosts
    local bases = event and event.bases
    local ghost_names = event and event.ghost_names
    local base_names = event and event.base_names
    if not live(parent) or type(ghosts) ~= "table" or type(bases) ~= "table"
        or type(ghost_names) ~= "table" or type(base_names) ~= "table" then
        return nil, nil
    end
    local ghost, base = ghosts[index], bases[index]
    local ghost_name, base_name = ghost_names[index], base_names[index]
    if not live(ghost) or not live(base)
        or type(ghost_name) ~= "string" or type(base_name) ~= "string" then
        return nil, nil
    end
    local gp_ok, ghost_parent = safe_call(ghost, "parent")
    local bp_ok, base_parent = safe_call(base, "parent")
    if gp_ok ~= true or ghost_parent ~= parent
        or bp_ok ~= true or base_parent ~= parent then
        return nil, nil
    end
    local gc_ok, ghost_child = safe_call(parent, "child", ghost_name)
    local bc_ok, base_child = safe_call(parent, "child", base_name)
    if gc_ok ~= true or ghost_child ~= ghost
        or bc_ok ~= true or base_child ~= base then
        return nil, nil
    end
    return ghost, base
end

local function flash_event_color_reads(color)
    if color == nil then return nil end
    local ok, r, g, b, a = pcall(function()
        return color.r, color.g, color.b, color.a
    end)
    if not ok then return nil end
    return r, g, b, a
end

local function flash_event_native_terminal(event)
    for i = 1, 2 do
        local ghost, base = flash_event_retained_leaf(event, i)
        if not ghost then return false end
        local vis_ok, visible = safe_call(ghost, "visible")
        local color_ok, color = safe_call(ghost, "color")
        if vis_ok ~= true or visible ~= false or color_ok ~= true then
            return false
        end
        local r, gc, bl, ca = flash_event_color_reads(color)
        if not finite(r) or math.abs(r - 1) > .001
            or not finite(gc) or math.abs(gc - 1) > .001
            or not finite(bl) or math.abs(bl - 1) > .001
            or not finite(ca) or math.abs(ca) > .0001 then
            return false
        end
        local gx_ok, gx = safe_call(ghost, "x")
        local gy_ok, gy = safe_call(ghost, "y")
        local gw_ok, gw = safe_call(ghost, "w")
        local gh_ok, gh = safe_call(ghost, "h")
        local bx_ok, bx = safe_call(base, "x")
        local by_ok, by = safe_call(base, "y")
        local bw_ok, bw = safe_call(base, "w")
        local bh_ok, bh = safe_call(base, "h")
        if gx_ok ~= true or gy_ok ~= true or gw_ok ~= true or gh_ok ~= true
            or bx_ok ~= true or by_ok ~= true or bw_ok ~= true or bh_ok ~= true
            or not finite(gx) or not finite(gy) or not finite(gw) or not finite(gh)
            or not finite(bx) or not finite(by) or not finite(bw) or not finite(bh) then
            return false
        end
        if math.abs(gx - bx) > .05 or math.abs(gy - by) > .05
            or math.abs(gw - bw) > .05 or math.abs(gh - bh) > .05 then
            return false
        end
    end
    return true
end

local function flash_event_native_phase(event)
    for i = 1, 2 do
        local ghost, base = flash_event_retained_leaf(event, i)
        if not ghost then return false end
        local ghost_state = flash_leaf_state(ghost, true, FLASH_GROUP)
        if not ghost_state or ghost_state.alpha <= 0 then return false end
        local base_state = flash_leaf_state(base, false, FLASH_BASE_LEASE)
        if not base_state then return false end
        local scale = 1 + (1 - ghost_state.alpha)
        if not flash_centered_scaled(ghost_state, base_state, scale) then
            return false
        end
    end
    return true
end

function M:_grenade_flash_chain()
    local mgr = self._hud_manager or (managers and managers.hud)
    local panels = mgr and mgr._teammate_panels
    local slot = HUDManager and HUDManager.PLAYER_PANEL or nil
    if not finite(slot) then return nil, nil, nil, nil, "chain_slot" end
    local entry = type(panels) == "table" and panels[slot] or nil
    local entry_panel = type(entry) == "table" and entry._panel or nil
    if not live(entry_panel) then return nil, nil, nil, nil, "chain_entry_panel" end
    local player = flash_child(entry_panel, "player")
    if not player then return nil, nil, nil, nil, "chain_player" end
    local grenades = flash_child(player, "grenades_panel")
    if not grenades then return nil, nil, nil, nil, "chain_grenades" end
    local base1 = flash_child(grenades, FLASH_SOURCES[1].base)
    local ghost1 = flash_child(grenades, FLASH_SOURCES[1].ghost)
    local base2 = flash_child(grenades, FLASH_SOURCES[2].base)
    local ghost2 = flash_child(grenades, FLASH_SOURCES[2].ghost)
    if not base1 then return nil, nil, nil, nil, "chain_radial_base" end
    if not ghost1 then return nil, nil, nil, nil, "chain_radial_ghost" end
    if not base2 then return nil, nil, nil, nil, "chain_icon_base" end
    if not ghost2 then return nil, nil, nil, nil, "chain_icon_ghost" end
    return entry_panel, grenades, {base1, base2}, {ghost1, ghost2}
end

function M:_grenade_flash_fresh(snap, projectile)
    local pm = managers and managers.player
    if not pm or self._player_manager ~= pm or self._hud_manager ~= (managers and managers.hud) then
        return false, "fresh_manager"
    end
    local ok_unit, unit = safe_call(pm, "player_unit")
    if not ok_unit or unit == nil or unit ~= self._player_unit then
        return false, "fresh_unit"
    end
    if type(alive) == "function" then
        local ok_alive, is_alive = pcall(alive, unit)
        if not ok_alive or is_alive ~= true then return false, "fresh_alive" end
    end
    local ok_session, session = safe_call(managers.network, "session")
    if not ok_session or session == nil or session ~= self._session then
        return false, "fresh_session"
    end
    local ok_peer, peer = safe_call(session, "local_peer")
    if not ok_peer or peer == nil then return false, "fresh_peer" end
    local ok_id, peer_id = safe_call(peer, "id")
    if not ok_id or peer_id ~= self._peer_id then return false, "fresh_peer_id" end
    local equipment = pm._equipment
    if not equipment or equipment ~= self._equipment_table then
        return false, "fresh_equipment"
    end
    if equipment.selections ~= self._selections_table then
        return false, "fresh_selections"
    end
    local registry = pm._global and pm._global.synced_grenades
    if not registry or registry ~= self._grenade_registry then
        return false, "fresh_registry"
    end
    if managers.game_play_central ~= self._gpc then return false, "fresh_gpc" end
    local got, entry = safe_call(pm, "get_synced_grenades", peer_id)
    if not got or type(entry) ~= "table" or type(entry.grenade) ~= "string" then
        return false, "fresh_synced"
    end
    if entry.grenade ~= self._projectile_id
        or projectile.projectile_id ~= self._projectile_id then
        return false, "fresh_projectile"
    end
    local amount_ok, amount = safe_call(pm, "get_grenade_amount", peer_id)
    if not amount_ok or not is_valid_known_quantity(amount) then
        return false, "fresh_amount"
    end
    local maximum_ok, maximum = safe_call(pm, "get_max_grenades", entry.grenade)
    if not maximum_ok or not is_valid_known_quantity(maximum) then
        return false, "fresh_maximum"
    end
    if type(snap) ~= "table" or type(snap.projectile) ~= "table" then
        return false, "fresh_snapshot"
    end
    local snapshot = snap.projectile
    local charges = snapshot.charges
    local snapshot_maximum = snapshot.maximum
    if type(charges) ~= "table" or charges.known ~= true or charges.raw ~= amount then
        return false, "fresh_charges"
    end
    if type(snapshot_maximum) ~= "table" or snapshot_maximum.known ~= true
        or snapshot_maximum.raw ~= maximum then
        return false, "fresh_snapshot_maximum"
    end
    local projectiles = tweak_data and tweak_data.blackmarket and tweak_data.blackmarket.projectiles
    local td = projectiles and projectiles[entry.grenade]
    if type(td) ~= "table" then return false, "fresh_tweak" end
    local ability = td.ability == true or (type(td.ability) == "string" and td.ability ~= "")
    local throwable = td.throwable == true or td.is_a_grenade == true
    local kind
    if ability and not throwable then kind = "ability"
    elseif throwable and not ability then kind = "throwable" end
    if kind ~= projectile.kind then return false, "fresh_kind" end
    return true
end

function M:_read_grenade_flash_source(snap)
    if type(self._grenade_flash_event) == "table" then
        return self:_read_grenade_flash_event_source(snap)
    end
    local row = type(self._rows) == "table" and self._rows[4] or nil
    if not row or not row._tile or type(row._icon_descriptor) ~= "table" then
        if self:_grenade_flash_trace_ready("source", "row_missing") then
            self:_trace_grenade_flash("source", "row_missing",
                "row=" .. tostring(row ~= nil)
                .. " tile=" .. tostring(row ~= nil and row._tile ~= nil)
                .. " icon_descriptor=" .. type(row and row._icon_descriptor))
        end
        return nil
    end
    local entry_panel, grenades, bases, ghosts, chain_reason = self:_grenade_flash_chain()
    if not entry_panel then
        if self:_grenade_flash_trace_ready("source", chain_reason or "chain_missing") then
            self:_trace_grenade_flash("source", chain_reason or "chain_missing",
                "manager=" .. tostring(self._hud_manager ~= nil)
                .. " generation=" .. tostring(self._source_generation))
        end
        return nil
    end
    snap = snap or self:get_snapshot()
    if type(snap) ~= "table" or snap.source_known ~= true or snap.unsupported then
        if self:_grenade_flash_trace_ready("source", "snapshot_invalid") then
            local detail = "snap_type=" .. type(snap)
            if type(snap) == "table" then
                detail = detail .. " source_known=" .. tostring(snap.source_known)
                    .. " unsupported=" .. tostring(snap.unsupported)
                    .. " generation=" .. tostring(snap.source_generation)
            end
            detail = detail .. " current_generation=" .. tostring(self._source_generation)
            self:_trace_grenade_flash("source", "snapshot_invalid", detail)
        end
        return nil
    end
    if snap.source_generation ~= self._source_generation then
        if self:_grenade_flash_trace_ready("source", "generation_stale") then
            self:_trace_grenade_flash("source", "generation_stale",
                "snap_generation=" .. tostring(snap.source_generation)
                .. " current_generation=" .. tostring(self._source_generation))
        end
        return nil
    end
    local projectile = snap.projectile
    if type(projectile) ~= "table" then
        if self:_grenade_flash_trace_ready("source", "projectile_missing") then
            self:_trace_grenade_flash("source", "projectile_missing",
                "projectile_type=" .. type(projectile)
                .. " generation=" .. tostring(snap.source_generation))
        end
        return nil
    end
    if projectile.kind ~= "ability" and projectile.kind ~= "throwable" then
        if self:_grenade_flash_trace_ready("source", "projectile_kind") then
            self:_trace_grenade_flash("source", "projectile_kind",
                "projectile_id=" .. tostring(projectile.projectile_id)
                .. " kind=" .. tostring(projectile.kind)
                .. " charges_known=" .. tostring(projectile.charges and projectile.charges.known)
                .. " charges_raw=" .. tostring(projectile.charges and projectile.charges.raw))
        end
        return nil
    end
    if not (projectile.charges and projectile.charges.known == true) then
        if self:_grenade_flash_trace_ready("source", "projectile_charges") then
            self:_trace_grenade_flash("source", "projectile_charges",
                "projectile_id=" .. tostring(projectile.projectile_id)
                .. " kind=" .. tostring(projectile.kind)
                .. " charges_known=" .. tostring(projectile.charges and projectile.charges.known)
                .. " charges_raw=" .. tostring(projectile.charges and projectile.charges.raw))
        end
        return nil
    end
    local fresh_ok, fresh_reason = self:_grenade_flash_fresh(snap, projectile)
    if not fresh_ok then
        local reason = fresh_reason or "fresh_failed"
        if self:_grenade_flash_trace_ready("source", reason) then
            self:_trace_grenade_flash("source", reason,
                "projectile_id=" .. tostring(projectile.projectile_id)
                .. " kind=" .. tostring(projectile.kind)
                .. " charges_known=" .. tostring(projectile.charges and projectile.charges.known)
                .. " charges_raw=" .. tostring(projectile.charges and projectile.charges.raw)
                .. " generation=" .. tostring(self._source_generation))
        end
        return nil
    end
    local states = {}
    for i = 1, 2 do
        local ghost, ghost_reason = flash_leaf_state(ghosts[i], true, FLASH_GROUP)
        local base, base_reason = flash_leaf_state(bases[i], false, FLASH_BASE_LEASE)
        if not ghost or not base then
            local trace_state = self._grenade_flash_trace_state
            if trace_state and trace_state.enabled == true
                and (trace_state.count or 0) < GRENADE_FLASH_TRACE_LIMIT then
                local reason
                if not ghost then reason = "ghost_" .. tostring(ghost_reason)
                else reason = "base_" .. tostring(base_reason) end
                if self:_grenade_flash_trace_ready("source", reason) then
                    self:_trace_grenade_flash("source", reason,
                        "leaf=" .. tostring(FLASH_SOURCES[i] and FLASH_SOURCES[i].ghost or "unknown")
                        .. " " .. flash_panel_observation("ghost", ghosts[i])
                        .. " " .. flash_panel_observation("base", bases[i]))
                end
            end
            return nil
        end
        states[i] = {ghost = ghost, base = base}
    end
    local alpha = states[1].ghost.alpha
    if math.abs(alpha - states[2].ghost.alpha) > 0.005 then
        if self:_grenade_flash_trace_ready("source", "ghost_phase_mismatch") then
            self:_trace_grenade_flash("source", "ghost_phase_mismatch",
                string.format("ghost1_alpha=%.17g ghost2_alpha=%.17g leaf1=%s leaf2=%s",
                    states[1].ghost.alpha, states[2].ghost.alpha,
                    FLASH_SOURCES[1].ghost, FLASH_SOURCES[2].ghost))
        end
        return nil
    end
    local scale = 1 + (1 - alpha)
    if not flash_centered_scaled(states[1].ghost, states[1].base, scale) then
        if self:_grenade_flash_trace_ready("source", "radial_shape") then
            local native_alpha = "unknown"
            local ok_native, value = safe_call(ghosts[1], "alpha")
            if ok_native and finite(value) then native_alpha = string.format("%.17g", value) end
            self:_trace_grenade_flash("source", "radial_shape",
                string.format("leaf=%s ghost_shape=(%.17g,%.17g,%.17g,%.17g) base_shape=(%.17g,%.17g,%.17g,%.17g) native_alpha=%s tint_alpha=%.17g",
                    FLASH_SOURCES[1].ghost,
                    states[1].ghost.x, states[1].ghost.y, states[1].ghost.w, states[1].ghost.h,
                    states[1].base.x, states[1].base.y, states[1].base.w, states[1].base.h,
                    native_alpha, states[1].ghost.alpha))
        end
        return nil
    end
    if not flash_centered_scaled(states[2].ghost, states[2].base, scale) then
        if self:_grenade_flash_trace_ready("source", "icon_shape") then
            local native_alpha = "unknown"
            local ok_native, value = safe_call(ghosts[2], "alpha")
            if ok_native and finite(value) then native_alpha = string.format("%.17g", value) end
            self:_trace_grenade_flash("source", "icon_shape",
                string.format("leaf=%s ghost_shape=(%.17g,%.17g,%.17g,%.17g) base_shape=(%.17g,%.17g,%.17g,%.17g) native_alpha=%s tint_alpha=%.17g",
                    FLASH_SOURCES[2].ghost,
                    states[2].ghost.x, states[2].ghost.y, states[2].ghost.w, states[2].ghost.h,
                    states[2].base.x, states[2].base.y, states[2].base.w, states[2].base.h,
                    native_alpha, states[2].ghost.alpha))
        end
        return nil
    end
    return {
        entry_panel = entry_panel,
        parent = grenades,
        manager = self._hud_manager or (managers and managers.hud),
        targets = {ghosts[1], ghosts[2]},
        bases = {bases[1], bases[2]},
        ghost_names = {FLASH_SOURCES[1].ghost, FLASH_SOURCES[2].ghost},
        base_names = {FLASH_SOURCES[1].base, FLASH_SOURCES[2].base},
        alpha = alpha,
        scale = scale,
    }
end

function M:_sync_grenade_flash(snap)
    self._grenade_flash_rejected = false
    local row = type(self._rows) == "table" and self._rows[4] or nil
    if not row or not row._tile then
        self._grenade_flash_ok = false
        self._grenade_flash_source = nil
        if self:_grenade_flash_trace_ready("owned", "row_missing") then
            self:_trace_grenade_flash("owned", "row_missing",
                "row=" .. tostring(row ~= nil)
                .. " tile=" .. tostring(row ~= nil and row._tile ~= nil))
        end
        return false
    end
    local source = self:_read_grenade_flash_source(snap)
    self._grenade_flash_source = source
    if not source or source.alpha <= 0 then
        local reason = source and "source_alpha_nonpositive" or "source_missing"
        if self:_grenade_flash_trace_ready("owned", reason) then
            self:_trace_grenade_flash("owned", reason,
                "source=" .. tostring(source ~= nil)
                .. " alpha=" .. flash_trace_number(source and source.alpha or nil))
        end
        row:_hide_grenade_flash()
        self._grenade_flash_ok = false
        self._grenade_flash_source = nil
        return false
    end
    local pcall_ok, rendered = pcall(function() return row:render_grenade_flash(source.alpha, source.scale, source.event_mode) end)
    local verified = false
    if pcall_ok and rendered == true then
        verified = row:_verify_grenade_flash() == true
    end
    self._grenade_flash_ok = pcall_ok and rendered == true and verified
    if not self._grenade_flash_ok then
        local reason = (not pcall_ok) and "render_error"
            or (rendered ~= true and "render_returned_false" or "verify_failed")
        if self:_grenade_flash_trace_ready("owned", reason) then
            self:_trace_grenade_flash("owned", reason,
                flash_owned_observation(row, source, pcall_ok, rendered, verified))
        end
        row:_hide_grenade_flash()
        self._grenade_flash_source = nil
    elseif self:_grenade_flash_trace_ready("owned", "certified") then
        self:_trace_grenade_flash("owned", "certified",
            flash_owned_observation(row, source, pcall_ok, rendered, verified))
    end
    return self._grenade_flash_ok
end

function M:_throttle_grenade_flash()
    local row = type(self._rows) == "table" and self._rows[4] or nil
    if not row or not row._tile then
        self._grenade_flash_ok = false
        self._grenade_flash_source = nil
        if self:_grenade_flash_trace_ready("owned", "row_missing") then
            self:_trace_grenade_flash("owned", "row_missing",
                "row=" .. tostring(row ~= nil)
                .. " tile=" .. tostring(row ~= nil and row._tile ~= nil))
        end
        return false
    end
    if self._grenade_flash_rejected == true then
        if self:_grenade_flash_trace_ready("owned", "rejected") then
            self:_trace_grenade_flash("owned", "rejected",
                flash_owned_observation(row, self._grenade_flash_source, nil, nil, nil))
        end
        return false
    end
    if self._grenade_flash_ok == true then
        if not row:_verify_grenade_flash() then
            local stale_source = self._grenade_flash_source
            self._grenade_flash_ok = false
            self._grenade_flash_source = nil
            self._grenade_flash_rejected = true
            if self:_grenade_flash_trace_ready("owned", "throttle_verify_failed") then
                self:_trace_grenade_flash("owned", "throttle_verify_failed",
                    flash_owned_observation(row, stale_source, nil, nil, false))
            end
            row:_hide_grenade_flash(true)
            return false
        end
    elseif not row:_verify_grenade_flash() then
        self._grenade_flash_rejected = true
        if self:_grenade_flash_trace_ready("owned", "throttle_not_certified") then
            self:_trace_grenade_flash("owned", "throttle_not_certified",
                flash_owned_observation(row, self._grenade_flash_source, nil, nil, false))
        end
        row:_hide_grenade_flash(true)
        return false
    end
    local source = self:_read_grenade_flash_source()
    self._grenade_flash_source = source
    if not source or source.alpha <= 0 then
        local reason = source and "source_alpha_nonpositive" or "source_missing"
        if self:_grenade_flash_trace_ready("owned", reason) then
            self:_trace_grenade_flash("owned", reason,
                "source=" .. tostring(source ~= nil)
                .. " alpha=" .. flash_trace_number(source and source.alpha or nil))
        end
        row:_hide_grenade_flash()
        self._grenade_flash_ok = false
        self._grenade_flash_source = nil
        return false
    end
    local pcall_ok, rendered = pcall(function() return row:render_grenade_flash(source.alpha, source.scale, source.event_mode) end)
    local verified = false
    if pcall_ok and rendered == true then
        verified = row:_verify_grenade_flash() == true
    end
    self._grenade_flash_ok = pcall_ok and rendered == true and verified
    if not self._grenade_flash_ok then
        local reason = (not pcall_ok) and "render_error"
            or (rendered ~= true and "render_returned_false" or "verify_failed")
        if self:_grenade_flash_trace_ready("owned", reason) then
            self:_trace_grenade_flash("owned", reason,
                flash_owned_observation(row, source, pcall_ok, rendered, verified))
        end
        row:_hide_grenade_flash()
        self._grenade_flash_source = nil
    elseif self:_grenade_flash_trace_ready("owned", "certified") then
        self:_trace_grenade_flash("owned", "certified",
            flash_owned_observation(row, source, pcall_ok, rendered, verified))
    end
    return self._grenade_flash_ok
end

function M:_verify_grenade_flash()
    local row = type(self._rows) == "table" and self._rows[4] or nil
    if not row or not row._tile or self._grenade_flash_ok ~= true then return false end
    if row._flash_active ~= true then return false end
    local ok_visible, visible = safe_call(row._grenade_flash, "visible")
    if not ok_visible or visible ~= true then return false end
    local source = self._grenade_flash_source
    if type(source) ~= "table" or not finite(source.alpha) or source.alpha <= 0 then return false end
    if type(source.targets) ~= "table" or #source.targets ~= 2 then return false end
    return row:_verify_grenade_flash() == true
end

local function temporal_eligible(channel, projectile_kind, channel_index)
    if not channel then return false end
    if channel.known ~= true then return false end
    if channel.active ~= true then return false end
    if not is_valid_positive_quantity(channel.remaining) then return false end
    if projectile_kind == "ability" then return true end
    if channel_index == 1 and projectile_kind == "throwable" then return true end
    return false
end

function M:_record_kingpin_present_cache(snap, cooldown)
    self._kingpin_present_cache = nil
    if self._invalidated or type(snap) ~= "table" or type(self._snapshot) ~= "table" then
        return
    end
    if self._projectile_id ~= KINGPIN_PROJECTILE_ID then return end
    local projectile = snap.projectile
    if type(projectile) ~= "table"
        or projectile.projectile_id ~= KINGPIN_PROJECTILE_ID then return end
    if type(self._visible_rows) ~= "table" or self._visible_rows[6] ~= true then return end
    local activity = snap.activity
    if type(activity) ~= "table" or activity.source ~= KINGPIN_ACTIVITY_SOURCE
        or activity.known ~= true or activity.active ~= true then return end
    local prov = self._kingpin_activity
    if type(prov) ~= "table" or prov.invalid == true
        or prov.kind ~= KINGPIN_ACTIVITY_SOURCE or type(prov.event_id) ~= "string"
        or type(prov.activity) ~= "table" or prov.activity ~= self._activity
        or prov.activity.source ~= KINGPIN_ACTIVITY_SOURCE
        or prov.activity.known ~= true or prov.activity.active ~= true
        or prov.generation ~= self._source_generation
        or prov.projectile_id ~= KINGPIN_PROJECTILE_ID then return end
    local wrappers = self._residual_phase_wrappers
    if type(wrappers) ~= "table" or self.verify ~= wrappers.verify then return end
    local rows = self._rows
    local row1 = type(rows) == "table" and rows[1] or nil
    local row2 = type(rows) == "table" and rows[2] or nil
    local row3 = type(rows) == "table" and rows[3] or nil
    local row4 = type(rows) == "table" and rows[4] or nil
    local row5 = type(rows) == "table" and rows[5] or nil
    local row6 = type(rows) == "table" and rows[6] or nil
    if not row1 or not row2 or not row3
        or not row4 or not row5 or not row6 then return end
    local charges = projectile.charges
    self._kingpin_present_cache = {
        event_id = prov.event_id,
        verifier = self.verify,
        root = self._root,
        parent = self._parent,
        manager = self._manager,
        hud_manager = self._hud_manager,
        rows = rows,
        row1 = row1,
        row2 = row2,
        row3 = row3,
        row4 = row4,
        row5 = row5,
        row6 = row6,
        snapshot = self._snapshot,
        generation = self._source_generation,
        projectile_id = self._projectile_id,
        texts = self._texts,
        layout = self._layout,
        hud_scale = kyohud.settings and kyohud.settings.hud_scale,
        required_width = self._required_width,
        required_scale = self._required_scale,
        temporal_height = self._temporal_height,
        cooldown_event = self._cooldown_event,
        charges_known = type(charges) == "table" and charges.known == true,
        charges_raw = type(charges) == "table" and charges.raw or nil,
        cooldown_known = type(cooldown) == "table" and cooldown.known == true,
        cooldown_active = type(cooldown) == "table" and cooldown.active == true,
        cooldown_integrated = type(cooldown) == "table"
            and cooldown.integrated == true and cooldown.active == true,
        cooldown_duration = type(cooldown) == "table" and cooldown.duration or nil,
        row5_visible = self._visible_rows[5] == true,
    }
end

function M:_present_kingpin_activity_event(source)
    self._kingpin_activity_ok = false
    if not enabled() then return false, "source" end
    if self._invalidated or self._dirty then return false, "dirty" end
    if type(source) ~= "table" or source.kind ~= KINGPIN_ACTIVITY_SOURCE
        or source.active ~= true or source.projectile_id ~= KINGPIN_PROJECTILE_ID
        or source.generation ~= self._source_generation then
        return false, "source"
    end
    local cache = self._kingpin_present_cache
    if type(cache) ~= "table" then return false, "cache" end
    local wrappers = self._residual_phase_wrappers
    if type(wrappers) ~= "table" or self.verify ~= wrappers.verify
        or cache.verifier ~= self.verify then
        self._kingpin_present_cache = nil
        return false, "identity"
    end
    if cache.event_id ~= source.event_id then
        self._kingpin_present_cache = nil
        return false, "activation"
    end
    local rows = self._rows
    if type(rows) ~= "table" then
        self._kingpin_present_cache = nil
        return false, "identity"
    end
    if cache.root ~= self._root or cache.parent ~= self._parent
        or cache.manager ~= self._manager or cache.hud_manager ~= self._hud_manager
        or cache.rows ~= rows or cache.row1 ~= rows[1]
        or cache.row2 ~= rows[2] or cache.row3 ~= rows[3]
        or cache.row4 ~= rows[4]
        or cache.row5 ~= rows[5] or cache.row6 ~= rows[6] then
        self._kingpin_present_cache = nil
        return false, "identity"
    end
    if cache.snapshot ~= self._snapshot then
        self._kingpin_present_cache = nil
        return false, "snapshot"
    end
    if cache.generation ~= self._source_generation
        or cache.projectile_id ~= self._projectile_id then
        self._kingpin_present_cache = nil
        return false, "identity"
    end
    if cache.texts ~= self._texts then
        self._kingpin_present_cache = nil
        return false, "identity"
    end
    if cache.layout ~= self._layout then
        self._kingpin_present_cache = nil
        return false, "layout"
    end
    if cache.hud_scale ~= (kyohud.settings and kyohud.settings.hud_scale) then
        self._kingpin_present_cache = nil
        return false, "identity"
    end
    if cache.required_width ~= self._required_width then
        self._kingpin_present_cache = nil
        return false, "layout"
    end
    if cache.required_scale ~= self._required_scale then
        self._kingpin_present_cache = nil
        return false, "identity"
    end
    if cache.temporal_height ~= self._temporal_height then
        self._kingpin_present_cache = nil
        return false, "layout"
    end
    if cache.cooldown_event ~= self._cooldown_event then
        self._kingpin_present_cache = nil
        return false, "cooldown"
    end
    if type(self._visible_rows) ~= "table" or self._visible_rows[6] ~= true
        or self._visible_rows[5] ~= cache.row5_visible then
        self._kingpin_present_cache = nil
        return false, "layout"
    end
    local snapshot = self._snapshot
    local projectile = snapshot.projectile
    local charges = type(projectile) == "table" and projectile.charges or nil
    if type(projectile) ~= "table"
        or projectile.projectile_id ~= KINGPIN_PROJECTILE_ID
        or type(charges) ~= "table" or charges.known ~= cache.charges_known
        or charges.raw ~= cache.charges_raw then
        self._kingpin_present_cache = nil
        return false, "snapshot"
    end
    local cooldown = self:_fresh_cooldown()
    if type(cooldown) ~= "table" or cooldown.known ~= true then
        self._kingpin_present_cache = nil
        return false, "cooldown"
    end
    local integrated = cooldown.active == true and cooldown.integrated == true
    local row5_shown = not integrated
        and temporal_eligible(cooldown, projectile.kind, 1) == true
    if cache.cooldown_known ~= true
        or cache.cooldown_active ~= (cooldown.active == true)
        or cache.cooldown_integrated ~= integrated
        or cache.row5_visible ~= row5_shown then
        self._kingpin_present_cache = nil
        return false, "cooldown"
    end
    local cached_duration, current_duration = cache.cooldown_duration, cooldown.duration
    if cached_duration ~= nil or current_duration ~= nil then
        if not is_valid_positive_quantity(cached_duration)
            or not is_valid_positive_quantity(current_duration)
            or math.abs(cached_duration - current_duration) > 0.001 then
            self._kingpin_present_cache = nil
            return false, "cooldown"
        end
    end
    local remaining, duration = source.remaining, source.duration
    if not is_valid_positive_quantity(remaining)
        or not is_valid_positive_quantity(duration) then
        self._kingpin_present_cache = nil
        return false, "source"
    end
    local texts = self._texts
    local label = type(texts) == "table" and texts.active or nil
    local cooldown_label = type(texts) == "table" and texts.cooldown or nil
    if type(label) ~= "string" or type(cooldown_label) ~= "string" then
        return false, "identity"
    end
    if self:verify() ~= true or not hacker_root_exposed(self) then
        return false, "verify"
    end
    local row6 = cache.row6
    local value = string.format("%ds", math.ceil(remaining))
    local progress = math.min(1, math.max(0, remaining / duration))
    local row6_ok, row6_rendered = pcall(function()
        row6:render(label, value, progress)
        return row6:verify() == true
    end)
    if not row6_ok or row6_rendered ~= true then return false, "render" end
    if cache.row5_visible then
        local row5 = cache.row5
        local cooldown_remaining = cooldown.remaining
        if not is_valid_positive_quantity(cooldown_remaining)
            or not is_valid_positive_quantity(cooldown.duration) then
            return false, "render"
        end
        local cooldown_value = string.format("%ds", math.ceil(cooldown_remaining))
        local cooldown_progress = math.min(1, math.max(0, cooldown_remaining / cooldown.duration))
        local row5_ok, row5_rendered = pcall(function()
            row5:render(cooldown_label, cooldown_value, cooldown_progress)
            return row5:verify() == true
        end)
        if not row5_ok or row5_rendered ~= true then return false, "render" end
    end
    self:_animate_recharge()
    self:_sync_grenade_flash(self._snapshot)
    local shown, visible = safe_call(self._root, "visible")
    if shown == true and visible == true then return true end
    return false, "render"
end

function M:_present()
    self._kingpin_present_cache = nil
    if not live(self._root) or not self._rows then return end

    local snap=self:get_snapshot()
    local _,pw=safe_call(self._parent,"w");local _,ph=safe_call(self._parent,"h")
    local base=kyohud.hud.layout.local_loadout(pw,ph,kyohud.settings.hud_scale)
    if not base or not snap.source_known or snap.unsupported then
        safe_call(self._root,"set_visible",false);return
    end
    local texts=self._texts
    self._visible_rows={}
    local cells={}
    local by_index={}
    for _,entry in pairs(snap.deployables) do by_index[entry.selection_index]=entry end
    for i=1,2 do
        local entry=by_index[i]
        local label,value="",""
        if entry then
            local td=tweak_data and tweak_data.equipments and tweak_data.equipments[entry.equipment_id]
            label=self:_name(entry.equipment_id,td and td.text_id,texts.deployable.." "..i)
            local counts={}
            for _,q in ipairs(entry.quantities) do counts[#counts+1]=count_text(q,texts.unlimited) end
            value=entry.amount_text or (#counts>0 and table.concat(counts,"|") or "--")
        end
        if entry then
            local td=tweak_data and tweak_data.equipments and tweak_data.equipments[entry.equipment_id]
            cells[#cells+1]={i=i,label=label,value=value,selected=snap.selected_effective==entry.equipment_id,icon=self:_icon(td and td.icon)}
        end
    end
    cells[#cells+1]={i=3,label=texts.cables,value=count_text(snap.cables,texts.unlimited),icon=self:_icon("equipment_cable_ties")}
    local projectile=snap.projectile
    local kind=projectile.kind=="ability" and texts.ability or projectile.kind=="throwable" and texts.throwable or "--"
    local label=self:_name(projectile.projectile_id,projectile.name_id,kind)
    local td=tweak_data and tweak_data.blackmarket and tweak_data.blackmarket.projectiles and tweak_data.blackmarket.projectiles[projectile.projectile_id]
    local cooldown=snap.cooldown
    local integrated=cooldown and cooldown.integrated==true and cooldown.active==true
    local grenade_value=count_text(projectile.charges)
    local grenade_progress
    if integrated then
        local recharge_text=self:integrated_recharge_text(cooldown,projectile.charges)
        if recharge_text then
            local remaining=cooldown.remaining
            grenade_value=recharge_text
            grenade_progress=math.min(1,math.max(0,1-remaining/cooldown.duration))
        else
            integrated=false
        end
    end
    cells[#cells+1]={i=4,label=label,value=grenade_value,width_value=count_text(projectile.charges),progress=grenade_progress,icon=self:_icon(td and td.icon,PROJECTILE_ICON_DEFAULT)}
    local required=math.max(0,#cells-1)*2*base.e
    for position,cell in ipairs(cells) do
        cell.both=true
        cell.w=self._rows[cell.i]:cell_width(cell.width_value or cell.value,base.e,cell.both)
        if not cell.w then safe_call(self._root,"set_visible",false);return end
        required=required+cell.w
    end
    local changed=self._required_width~=required or self._required_scale~=base.e
    self._required_width=required
    self._required_scale=base.e
    local weapons=kyohud.hud.weapons
    if changed and kyohud.settings.enable_weapons and weapons and weapons._mounted then
        weapons:_apply();weapons:_render()
    end
    local temporal_count=0
    for i,ch in ipairs({snap.cooldown,snap.activity}) do
        if not (i==1 and integrated) and temporal_eligible(ch,projectile.kind,i) then
            temporal_count=temporal_count+1
        end
    end
    self._temporal_height=temporal_count*18*base.e
    local geom=self:_geometry()
    self._layout=geom
    if not geom then safe_call(self._root,"set_visible",false);return end
    safe_call(self._root,"set_shape",geom.x,geom.y,geom.w,geom.h)

    local x=0
    for _,cell in ipairs(cells) do
        local row=self._rows[cell.i]
        row:cell_layout(x,self._temporal_height+12*base.e,cell.w,base.h-22*base.e,geom.e,cell.both)
        row:render(cell.label,cell.value,cell.progress,cell.selected,cell.icon)
        self._visible_rows[cell.i]=true
        x=x+cell.w+2*geom.e
    end
    for i=1,4 do if not self._visible_rows[i] then safe_call(self._rows[i]._root,"set_visible",false) end end
    local temporal_y=0
    for i,channel in ipairs({snap.cooldown,snap.activity}) do
        local text="--"
        local progress
        if channel and channel.known then
            text=channel.active and string.format("%ds",math.ceil(channel.remaining)) or ""
            if channel.active and is_valid_positive_quantity(channel.duration) then progress=channel.remaining/channel.duration end
        end
        local shown=temporal_eligible(channel,projectile.kind,i)
        if i==1 and integrated then shown=false end
        self._visible_rows[4+i]=shown==true
        if shown then
            self._rows[4+i]:layout(0,temporal_y,geom.w,18*geom.e)
            self._rows[4+i]:render(i==1 and texts.cooldown or texts.active,text,progress)
            temporal_y=temporal_y+18*geom.e
        else safe_call(self._rows[4+i]._root,"set_visible",false) end
    end
    safe_call(self._root,"set_visible",true)
    self:_sync_grenade_flash(snap)
    if not self:verify() then
        safe_call(self._root,"set_visible",false)
    else
        self:_record_kingpin_present_cache(snap, cooldown)
    end
end

function M:verify(optional_receipt_request)
    -- quality split approved 2026-11-10
    self._verify_ok_now = false
    if not live(self._root) or not live(self._parent) or not self._layout or not self._rows then return false end
    local shown,visible=safe_call(self._root,"visible")
    if not shown or visible~=true then return false end
    local g=self._layout

    for _,key in ipairs({"x","y","w","h"}) do
        local ok,value=safe_call(self._root,key)
        if not ok or type(value)~="number" or value~=value or math.abs(value-g[key])>.05 then return false end
    end
    for i,row in ipairs(self._rows) do
        if self._visible_rows and self._visible_rows[i] then
            if not row:verify() then return false end
        else
            local ok,visible=safe_call(row._root,"visible")
            if not ok or visible~=false then return false end
        end
    end
    if #self._rows~=6 then return false end
    -- quality split approved 2026-11-10
    self._verify_ok_now = true
    if optional_receipt_request == KINGPIN_VERIFY_RECEIPT then
        return true, KINGPIN_VERIFY_RECEIPT
    end
    return true
end

function M:refresh_settings(manager)
    if not enabled() then self:unmount();return end
    if not live(self._root) then self:mount(manager);return end
    self:refresh(manager);self:_present()
end

function M:rebuild(manager)
    self:unmount();self:mount(manager)
end

function M:on_heist_start(manager)
    self._manager=manager;self:invalidate()
end

function M:destroy(manager)
    if manager and self._manager and self._manager~=manager then return end
    self:unmount();self:invalidate();self._manager=nil
end

function M:_animate_recharge()
    if not enabled() then return end
    if not live(self._root) or type(self._rows)~="table" then return end
    local shown,visible=safe_call(self._root,"visible")
    if not shown or visible~=true then return end
    local row=self._rows[4]
    if not row or not row._tile or not live(row._recharge_reveal) or row._progress==nil then return end
    local cooldown=self:_fresh_cooldown()
    if type(cooldown)~="table" or cooldown.known~=true then
        safe_call(self._root,"set_visible",false)
        return
    end
    if cooldown.integrated~=true or cooldown.active~=true then return end
    local remaining=cooldown.remaining
    if not (is_valid_positive_quantity(remaining) and is_valid_positive_quantity(cooldown.duration)
        and remaining<=cooldown.duration) then return end
    local projectile=type(self._snapshot)=="table" and self._snapshot.projectile or nil
    local charges=type(projectile)=="table" and projectile.charges or nil
    local value=self:integrated_recharge_text(cooldown,charges)
    if not value then return end
    local progress=math.min(1,math.max(0,1-remaining/cooldown.duration))
    if not row:animate_recharge(value,progress) then
        safe_call(self._root,"set_visible",false)
    end
end

function M:_throttle_hacker_activity()
    if not enabled() then
        self._hacker_activity_ok = false
        return false
    end
    -- A selected Kingpin source has its own fresh throttle checks; the Hacker
    -- source can never qualify chico_injector, so skip the full verifier here.
    if self._projectile_id == KINGPIN_PROJECTILE_ID then
        self._hacker_activity_ok = false
        return false
    end
    local row6 = type(self._rows) == "table" and self._rows[6] or nil
    if not row6 or not live(row6._root) or not live(row6._label)
        or not live(row6._value) then
        self._hacker_activity_ok = false
        return false
    end
    if type(self._visible_rows) ~= "table" or self._visible_rows[6] ~= true then
        self._hacker_activity_ok = false
        return false
    end
    if self:verify() ~= true or row6:verify() ~= true then
        self._hacker_activity_ok = false
        return false
    end
    local source = self:get_hacker_activity_source()
    if type(source) ~= "table" or source.active ~= true then
        self._hacker_activity_ok = false
        return false
    end
    local remaining, duration = source.remaining, source.duration
    if not is_valid_positive_quantity(remaining)
        or not is_valid_positive_quantity(duration) then
        self._hacker_activity_ok = false
        return false
    end
    local label = type(self._texts) == "table" and self._texts.active or nil
    if type(label) ~= "string" then
        self._hacker_activity_ok = false
        return false
    end
    local value = string.format("%ds", math.ceil(remaining))
    local progress = math.min(1, math.max(0, remaining / duration))
    local render_ok, rendered = pcall(function()
        row6:render(label, value, progress)
        return row6:verify() == true
    end)
    if not render_ok or rendered ~= true then
        self._hacker_activity_ok = false
        return false
    end
    local fresh = self:get_hacker_activity_source()
    if type(fresh) ~= "table" or fresh.active ~= true
        or fresh.event_id ~= source.event_id then
        self._hacker_activity_ok = false
        return false
    end
    local verify_ok, verified = pcall(self._verify_hacker_activity, self, fresh)
    if not verify_ok or verified ~= true then
        self._hacker_activity_ok = false
        return false
    end
    return true
end

function M:_throttle_kingpin_activity()
    if not enabled() then
        self._kingpin_activity_ok = false
        return false
    end
    local selected = type(self._snapshot) == "table"
        and type(self._snapshot.projectile) == "table"
        and self._snapshot.projectile.projectile_id or nil
    if type(self._kingpin_activity) ~= "table"
        or self._projectile_id ~= KINGPIN_PROJECTILE_ID
        or (selected ~= nil and selected ~= KINGPIN_PROJECTILE_ID) then
        self._kingpin_activity_ok = false
        return false
    end
    local row6 = type(self._rows) == "table" and self._rows[6] or nil
    if not row6 or not live(row6._root) or not live(row6._label)
        or not live(row6._value) then
        self._kingpin_activity_ok = false
        return false
    end
    if type(self._visible_rows) ~= "table" or self._visible_rows[6] ~= true then
        self._kingpin_activity_ok = false
        return false
    end
    local stable_seq = self._kingpin_stable_event_seq or 0
    local seen_seq = self._throttle_seen_seq or 0
    -- Skip the expensive tail once per stable event: the seam's prepare+chain
    -- already certified render, lease and source this frame. Non-stable frames
    -- (acquisition, transition, conflict, terminal, no publication) and frames
    -- after the consumed skip keep the full verification below. The residual
    -- probe phase kingpin_throttle_full aggregates both skip and full frames.
    if stable_seq > 0 and stable_seq ~= seen_seq then
        self._throttle_seen_seq = stable_seq
        self._kingpin_activity_ok = true
        return true
    end
    self._throttle_seen_seq = stable_seq
    if self:verify() ~= true or row6:verify() ~= true then
        self._kingpin_activity_ok = false
        return false
    end
    local source = self:get_kingpin_activity_source()
    if type(source) ~= "table" or source.active ~= true then
        self._kingpin_activity_ok = false
        return false
    end
    local remaining, duration = source.remaining, source.duration
    if not is_valid_positive_quantity(remaining)
        or not is_valid_positive_quantity(duration) then
        self._kingpin_activity_ok = false
        return false
    end
    local label = type(self._texts) == "table" and self._texts.active or nil
    if type(label) ~= "string" then
        self._kingpin_activity_ok = false
        return false
    end
    local value = string.format("%ds", math.ceil(remaining))
    local progress = math.min(1, math.max(0, remaining / duration))
    local render_ok, rendered = pcall(function()
        row6:render(label, value, progress)
        return row6:verify() == true
    end)
    if not render_ok or rendered ~= true then
        self._kingpin_activity_ok = false
        return false
    end
    local fresh = self:get_kingpin_activity_source()
    if type(fresh) ~= "table" or fresh.active ~= true
        or fresh.event_id ~= source.event_id then
        self._kingpin_activity_ok = false
        return false
    end
    local verify_ok, verified = pcall(self._verify_kingpin_activity, self, fresh)
    if not verify_ok or verified ~= true then
        self._kingpin_activity_ok = false
        return false
    end
    return true
end

function M:update(manager,t,dt)
    -- quality split approved 2026-11-10
    self._update_ran_now = false
    self._verify_ok_now = false
    local residual_rt, residual_start
    local runtime = kyohud.hud.runtime
    local probe = runtime and runtime._residual_probe
    if probe and probe.active and not probe.done
        and type(runtime._residual_stamp) == "function" then
        residual_rt = runtime
        residual_start = runtime:_residual_stamp()
    end
    if not managers or manager~=managers.hud or not is_valid_known_quantity(t) then return end
    if not enabled() then self:unmount();return end
    if not live(self._root) then
        if self._last_mount and t>=self._last_mount and t-self._last_mount<.5 then return end
        self._last_mount=t;self:mount(manager)
    end
    if not live(self._root) then return end
    if self._last_ui and t>=self._last_ui and t-self._last_ui<.05 then
        if residual_rt and residual_start ~= nil
            and type(residual_rt._residual_record) == "function" then
            residual_rt:_residual_record("equipment_throttled", residual_start)
        end
        self:_throttle_grenade_flash()
        self:_throttle_hacker_activity()
        self:_throttle_kingpin_activity()
        self:_animate_recharge()
        return
    end
    self._last_ui=t
    -- quality split approved 2026-11-10: main block ran, not a throttle return.
    self._update_ran_now = true
    if self._dirty or not self._last_poll or t<self._last_poll or t-self._last_poll>=.5 then
        self:refresh(manager);self._last_poll=t;self._dirty=false
    end
    self:_present()
end

local function notify()
    M._dirty = true
    if managers and managers.hud then M:refresh(managers.hud) end
end

function M:_read_grenade_flash_event_source(snap)
    local event = self._grenade_flash_event
    if type(event) ~= "table" or event.invalid == true
        or event.expired == true then return nil end
    if event.generation ~= self._source_generation then
        self._grenade_flash_event = nil
        return nil
    end
    if event.manager ~= self._hud_manager
        or event.player_manager ~= self._player_manager
        or event.player_unit ~= self._player_unit
        or event.session ~= self._session
        or event.peer_id ~= self._peer_id
        or event.equipment ~= self._equipment_table
        or event.selections ~= self._selections_table
        or event.registry ~= self._grenade_registry
        or event.gpc ~= self._gpc then
        event.invalid = true
        return nil
    end
    if not enabled() then return nil end
    local row = type(self._rows) == "table" and self._rows[4] or nil
    if not row or not row._tile or type(row._icon_descriptor) ~= "table" then return nil end
    local now, clock = current_game_time()
    if now == nil or clock == nil or clock ~= event.clock then
        event.invalid = true
        return nil
    end
    if now < event.start then
        event.invalid = true
        return nil
    end
    if type(event.last_seen) ~= "number" or now < event.last_seen then
        event.invalid = true
        return nil
    end
    event.last_seen = now
    local elapsed = now - event.start
    local extended = elapsed >= .6
    if extended then
        if flash_event_native_terminal(event) then
            event.expired = true
            return nil
        end
        if not flash_event_native_phase(event) then
            event.invalid = true
            return nil
        end
        if now > event.start + .6 + EVENT_NATIVE_EXTENSION_LIMIT then
            event.expired = true
            return nil
        end
    end
    snap = snap or self:get_snapshot()
    if type(snap) ~= "table" or snap.source_known ~= true or snap.unsupported then
        event.invalid = true
        return nil
    end
    if snap.source_generation ~= self._source_generation then
        event.invalid = true
        return nil
    end
    local projectile = snap.projectile
    if type(projectile) ~= "table" then
        event.invalid = true
        return nil
    end
    if projectile.kind ~= "ability" and projectile.kind ~= "throwable" then
        event.invalid = true
        return nil
    end
    if not (projectile.charges and projectile.charges.known == true) then
        event.invalid = true
        return nil
    end
    if projectile.projectile_id ~= event.projectile_id
        or self._projectile_id ~= event.projectile_id then
        event.invalid = true
        return nil
    end
    if not self:_grenade_flash_fresh(snap, projectile) then
        event.invalid = true
        return nil
    end
    local entry_panel, grenades, bases, ghosts = self:_grenade_flash_chain()
    if not entry_panel or not grenades or not bases or not ghosts
        or entry_panel ~= event.entry_panel or grenades ~= event.parent
        or bases[1] ~= event.bases[1] or bases[2] ~= event.bases[2]
        or ghosts[1] ~= event.ghosts[1] or ghosts[2] ~= event.ghosts[2] then
        event.invalid = true
        return nil
    end
    return {
        entry_panel = entry_panel,
        parent = grenades,
        manager = self._hud_manager or (managers and managers.hud),
        targets = {ghosts[1], ghosts[2]},
        bases = {bases[1], bases[2]},
        ghost_names = {FLASH_SOURCES[1].ghost, FLASH_SOURCES[2].ghost},
        base_names = {FLASH_SOURCES[1].base, FLASH_SOURCES[2].base},
        alpha = extended and EVENT_NATIVE_EXTENSION_ALPHA or (1 - elapsed / .6),
        scale = 2,
        event_mode = true,
        extended = extended or nil,
    }
end

function M:_capture_grenade_flash_event()
    if not enabled() then return end
    notify()
    local snap = self:get_snapshot()
    if type(snap) ~= "table" or snap.source_known ~= true or snap.unsupported then return end
    if snap.source_generation ~= self._source_generation then return end
    local projectile = snap.projectile
    if type(projectile) ~= "table" then return end
    if projectile.kind ~= "ability" and projectile.kind ~= "throwable" then return end
    if not (projectile.charges and projectile.charges.known == true) then return end
    if not self:_grenade_flash_fresh(snap, projectile) then return end
    local entry_panel, grenades, bases, ghosts = self:_grenade_flash_chain()
    if not entry_panel or not grenades or not bases or not ghosts then return end
    local now, clock = current_game_time()
    if now == nil or clock == nil then return end
    self._grenade_flash_event = {
        generation = self._source_generation,
        projectile_id = self._projectile_id,
        manager = self._hud_manager or (managers and managers.hud),
        player_manager = self._player_manager or (managers and managers.player),
        player_unit = self._player_unit,
        session = self._session,
        peer_id = self._peer_id,
        equipment = self._equipment_table,
        selections = self._selections_table,
        registry = self._grenade_registry,
        gpc = self._gpc,
        entry_panel = entry_panel,
        parent = grenades,
        bases = {bases[1], bases[2]},
        ghosts = {ghosts[1], ghosts[2]},
        ghost_names = {FLASH_SOURCES[1].ghost, FLASH_SOURCES[2].ghost},
        base_names = {FLASH_SOURCES[1].base, FLASH_SOURCES[2].base},
        clock = clock,
        start = now,
        last_seen = now,
        expired = false,
    }
end

local function install(class, method, fn, kind)
    if not class or not Hooks then return end
    local ok, target = pcall(function() return class[method] end)
    if not ok or type(target) ~= "function" then return end
    M._hooks = M._hooks or {}
    local id = "KyoHUD_Equipment_" .. tostring(RequiredScript) .. "_" .. method
    if kind == "pre" then id = id .. "_pre" end
    if M._hooks[id] then return end
    if kind == "pre" then
        Hooks:PreHook(class, method, id, fn)
    else
        Hooks:PostHook(class, method, id, fn)
    end
    M._hooks[id] = true
end

if RequiredScript == "lib/managers/playermanager" then
    for _, method in ipairs({"_add_equipment", "add_equipment_amount", "set_equipment_amount",
        "remove_equipment", "from_server_equipment_place_result", "select_next_item",
        "select_previous_item", "clear_equipment", "add_cable_ties", "add_special",
        "_on_grenade_cooldown_end", "clear_timers"}) do
        install(PlayerManager, method, function(self)
            if managers and self == managers.player then notify() end
        end)
    end
    install(PlayerManager, "remove_special", function(self, name)
        if not managers or self ~= managers.player then return end
        local previous=M._snapshot and M._snapshot.cables
        local source=M._specials_table
        local generation=M._source_generation
        notify()
        if name == "cable_tie" and not M._invalidated and generation==M._source_generation
            and previous and previous.known and previous.raw==1 then
            local specials = self._equipment and self._equipment.specials
            if type(specials) == "table" and specials==source and not specials.cable_tie then
                M._cable_zero = specials
                notify()
            end
        end
    end)
    for _,method in ipairs({"replenish_grenades","speed_up_grenade_cooldown"}) do
        install(PlayerManager,method,function(self)
            if managers and self==managers.player then
                if M._cooldown_event and M._cooldown_event.cancelled then M._cooldown_event=nil end
                notify()
            end
        end)
    end
    install(PlayerManager, "set_synced_grenades", function(self, peer_id)
        if managers and self == managers.player and peer_id == M._peer_id then notify() end
    end)
    for _, method in ipairs({"reset", "soft_reset", "player_destroyed"}) do
        install(PlayerManager, method, function(self)
            if managers and self == managers.player then M:invalidate(); notify() end
        end)
    end
elseif RequiredScript == "lib/managers/hudmanagerpd2" then
    local function local_panel(self, i)
        return managers and self == managers.hud and HUDManager and i == HUDManager.PLAYER_PANEL
    end
    -- Opt-in Kingpin publication diagnostic: one paired Pre/Post sample around
    -- the native HUD relay only. An incomplete, nested, foreign or capture-ended
    -- chain is dropped instead of being counted twice or reported as valid.
    local KINGPIN_PUBLICATION_PHASE = "kingpin_publication_total"
    local function kingpin_publication_state()
        local rt = kyohud.hud.runtime
        if type(rt) ~= "table" then return nil, nil end
        local probe = rt._residual_probe
        if type(probe) ~= "table" then return nil, nil end
        return rt, probe
    end
    local function kingpin_publication_ready(probe)
        return probe.mode == "kingpin" and probe.active == true and probe.done ~= true
    end
    local function kingpin_publication_source_ok(self)
        if type(managers) ~= "table" or managers.hud ~= self then return false end
        local equipment = kyohud.hud.equipment
        return type(equipment) == "table"
            and equipment._projectile_id == KINGPIN_PROJECTILE_ID
    end
    local function kingpin_publication_enter(self)
        local rt, probe = kingpin_publication_state()
        if not rt or not probe then return end
        local depth = probe.kingpin_publication_depth or 0
        if depth > 0 then
            probe.kingpin_publication_invalid = true
            probe.kingpin_publication_depth = depth + 1
            return
        end
        if not kingpin_publication_ready(probe) then return end
        if not kingpin_publication_source_ok(self) then return end
        if type(rt._residual_stamp) ~= "function" then return end
        local start = rt:_residual_stamp()
        if start == nil then return end
        probe.kingpin_publication_depth = 1
        probe.kingpin_publication_invalid = false
        probe.kingpin_publication_pending = true
        probe.kingpin_publication_start = start
        probe.kingpin_publication_manager = self
    end
    local function kingpin_publication_exit(self)
        local rt, probe = kingpin_publication_state()
        if not rt or not probe then return end
        local depth = probe.kingpin_publication_depth or 0
        if depth <= 0 then return end
        if not kingpin_publication_ready(probe) then
            probe.kingpin_publication_depth = 0
            probe.kingpin_publication_pending = false
            probe.kingpin_publication_invalid = false
            probe.kingpin_publication_start = nil
            probe.kingpin_publication_manager = nil
            return
        end
        if depth > 1 then
            probe.kingpin_publication_depth = depth - 1
            return
        end
        local valid = probe.kingpin_publication_pending == true
            and probe.kingpin_publication_invalid ~= true
            and probe.kingpin_publication_manager == self
        local start = probe.kingpin_publication_start
        local source_ok = valid and kingpin_publication_source_ok(self)
        probe.kingpin_publication_depth = 0
        probe.kingpin_publication_pending = false
        probe.kingpin_publication_invalid = false
        probe.kingpin_publication_start = nil
        probe.kingpin_publication_manager = nil
        if valid and source_ok and type(start) == "number"
            and type(rt._residual_record) == "function" then
            rt:_residual_record(KINGPIN_PUBLICATION_PHASE, start)
        end
    end
    install(HUDManager, "set_player_ability_radial", function(self)
        pcall(kingpin_publication_enter, self)
    end, "pre")
    install(HUDManager, "set_player_ability_radial", function(self)
        pcall(kingpin_publication_exit, self)
    end)
    install(HUDManager, "animate_grenade_flash", function(self, i)
        if not local_panel(self, i) then return end
        M:_capture_grenade_flash_event()
        local rt = kyohud.hud.runtime
        if rt and type(rt.sync_local_grenade_flash_event) == "function" then
            pcall(rt.sync_local_grenade_flash_event, rt)
        end
    end)
    install(HUDManager, "set_teammate_ability_radial", function(self, i, data)
        if not local_panel(self, i) then return end
        M:_capture_activity(data and data.current, data and data.total)
        local kingpin_ok = type(data) == "table"
            and M:_capture_kingpin_activity(data.current, data.total)
        if M._projectile_id == KINGPIN_PROJECTILE_ID and kingpin_ok ~= true then
            local current = data and data.current
            if current ~= 0 then
                M._activity = {known = false, active = false}
                if type(M._snapshot) == "table" then
                    M._snapshot.activity = M._activity
                end
            end
        end
        if kingpin_ok or M._projectile_id == KINGPIN_PROJECTILE_ID then
            local rt = kyohud.hud.runtime
            local terminal_zero = type(data) == "table" and data.current == 0
            local publication_current = data and data.current
            local publication_total = data and data.total
            if rt and type(rt.sync_local_kingpin_activity_event) == "function" then
                pcall(rt.sync_local_kingpin_activity_event, rt, terminal_zero, publication_current, publication_total)
            end
        end
    end)
    install(HUDManager, "activate_teammate_ability_radial", function(self, i, left, total)
        if not local_panel(self, i) then return end
        M:_capture_activity(left, total)
        local kingpin_ok
        if M._projectile_id == KINGPIN_PROJECTILE_ID then
            kingpin_ok = M:_capture_kingpin_activity(left, total)
            if kingpin_ok ~= true and left ~= 0 then
                M._activity = {known = false, active = false}
                if type(M._snapshot) == "table" then
                    M._snapshot.activity = M._activity
                end
            end
        end
        local rt = kyohud.hud.runtime
        if M._projectile_id == KINGPIN_PROJECTILE_ID then
            if rt and type(rt.sync_local_kingpin_activity_event) == "function" then
                pcall(rt.sync_local_kingpin_activity_event, rt, left == 0, left, total)
            end
        elseif rt and type(rt.sync_local_hacker_activity_event) == "function" then
            pcall(rt.sync_local_hacker_activity_event, rt)
        end
    end)
    install(HUDManager, "set_teammate_grenade_cooldown", function(self, i, data)
        if not local_panel(self, i) then return end
        notify()
        local pm = managers.player
        local timers = pm and pm._timers
        local registry = pm and pm._global and pm._global.synced_grenades
        local got, entry = safe_call(pm, "get_synced_grenades", M._peer_id)
        local projectile_id = got and type(entry) == "table" and entry.grenade or nil
        if type(data) == "table" then
            local now, clock = current_game_time()
            if is_valid_positive_quantity(data.duration) and now ~= nil then
                establish_clock_epoch(M, clock, now)
            end
            M._cooldown_event = {duration = data.duration, manager = pm, timers = timers,
                record = timers and timers.replenish_grenades,
                registry = registry, gpc = managers.game_play_central,
                projectile_id = projectile_id, clock = clock,
                generation = M._source_generation}
        else
            M._cooldown_event = {cancelled = true}
        end
        notify()
    end)
    for _, method in ipairs({"set_cable_tie", "set_cable_ties_amount", "set_deployable_equipment",
        "set_teammate_deployable_equipment_amount", "set_teammate_grenades",
        "set_teammate_grenades_amount"}) do
        install(HUDManager, method, function(self, i)
            if local_panel(self, i) then notify() end
        end)
    end
    local function capture_text(self, i, index, data)
        if not local_panel(self, i) then return end
        notify()
        local selections = M._selections_table
        local record = type(selections) == "table" and selections[index]
        if M._invalidated or not record or type(data) ~= "table" or type(data.amount_str) ~= "string" then return end
        M._amount_text = M._amount_text or {}
        M._amount_text[index] = {record = record, value = data.amount_str}
        notify()
    end
    install(HUDManager, "set_teammate_deployable_equipment_amount_from_string", capture_text)
    install(HUDManager, "set_deployable_equipment_from_string", function(self, i, data)
        local pm = managers and managers.player
        local index = pm and pm._equipment and pm._equipment.selected_index
        if index then capture_text(self, i, index, data) end
    end)
end

-- Opt-in residual instrumentation only: the wrappers resolve the runtime probe
-- on each call, add no diagnostics when it is absent/done, and are reinstalled
-- over the fresh method definitions on each chunk load. Phases are inclusive;
-- snapshot/verify nest inside present and must never be summed.
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
            if name == "verify" or name == "_present_kingpin_activity_event" then
                wrapper = function(self, ...)
                    local rt = residual_context()
                    if not rt then return original(self, ...) end
                    local start = rt:_residual_stamp()
                    local result, receipt = original(self, ...)
                    rt:_residual_record(phase, start)
                    return result, receipt
                end
            else
                wrapper = function(self, ...)
                    local rt = residual_context()
                    if not rt then return original(self, ...) end
                    local start = rt:_residual_stamp()
                    local result = original(self, ...)
                    rt:_residual_record(phase, start)
                    return result
                end
            end
        else
            wrapper = function(self, ...)
                local rt = residual_context()
                if not rt then original(self, ...); return end
                local start = rt:_residual_stamp()
                original(self, ...)
                rt:_residual_record(phase, start)
            end
        end
        wrappers[name] = wrapper
        M[name] = wrapper
    end
    install("refresh", "equipment_collect", false)
    install("_capture_grenade_flash_event", "equipment_collect", false)
    install("_fresh_cooldown", "equipment_snapshot", true)
    install("_present", "equipment_present", false)
    install("_present_kingpin_activity_event", "equipment_present", true)
    install("_animate_recharge", "equipment_present", true)
    install("_sync_grenade_flash", "equipment_present", true)
    install("_throttle_grenade_flash", "equipment_present", true)
    install("verify", "equipment_verify", true)
    install("_capture_activity", "equipment_collect", false)
    install("_capture_kingpin_activity", "equipment_collect", true)
    install("get_hacker_activity_source", "equipment_snapshot", true)
    install("get_kingpin_activity_source", "equipment_snapshot", true)
    install("get_kingpin_terminal_source", "equipment_snapshot", true)
    install("get_local_ability_activity_source", "equipment_snapshot", true)
    install("_verify_hacker_activity", "equipment_verify", true)
    install("_verify_kingpin_activity", "equipment_verify", true)
    install("_verify_kingpin_terminal", "equipment_verify", true)
    install("_verify_local_ability_activity", "equipment_verify", true)
    install("prepare_kingpin_activity_event", "equipment_present", true)
    install("_prepare_kingpin_terminal_event", "equipment_present", true)
    install("prepare_local_ability_activity_event", "equipment_present", true)
    install("_throttle_hacker_activity", "equipment_present", true)
    install("_throttle_kingpin_activity", "equipment_present", true)
end
install_residual_phase_wrappers()
