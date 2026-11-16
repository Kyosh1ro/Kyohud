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
-- quality split approved 2026-11-10
M._update_ran_now = M._update_ran_now or false
M._verify_ok_now = M._verify_ok_now or false

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

local function safe_call(obj, method, ...)
    if obj == nil then return false, nil end
    local ok_get, fn = pcall(function() return obj[method] end)
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

function M:refresh(manager)
    self._invalidated = true
    self._snapshot = nil

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
        self._cable_zero = nil
        self._cooldown_event = nil
        self._amount_text = nil
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

    return {
        deployables = detached_deployables,
        selected_index = self._snapshot.selected_index,
        selected_effective = self._snapshot.selected_effective,
        source_generation = self._snapshot.source_generation,
        source_known = self._snapshot.source_known,
        unsupported = self._snapshot.unsupported,
        cables = detached(self._snapshot.cables),
        projectile = detached(self._snapshot.projectile),
        cooldown = self:_fresh_cooldown(),
        activity = self:_timed_snapshot(self._snapshot.activity)
    }
end

function M:_timed_snapshot(value)
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
    self._dirty = true
end

function M:_capture_activity(left, total)
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
    if self._invalidated then return end
    if total == nil then total = left end
    if left == 0 then
        self._activity = {known = true, active = false, remaining = 0}
    elseif is_valid_positive_quantity(left) and is_valid_positive_quantity(total) then
        local ok, timer = safe_call(TimerManager, "game")
        local good, now = safe_call(ok and timer or nil, "time")
        if not good or not is_valid_known_quantity(now) then self._activity = nil; return end
        self._activity = {known = true, active = true, remaining = left, duration = total,
            sampled_at = now, clock_kind = "game"}
    else
        self._activity = nil
    end
    self._snapshot.activity = self._activity or {known = false, active = false}
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
    if not live(panel) then return nil end
    local ok_visible, visible = safe_call(panel, "visible")
    if not ok_visible or (visible ~= true and visible ~= false) then return nil end
    if visible ~= true and not flash_group_holds_visible(lease_group, panel) then return nil end
    local ok_alpha, alpha = safe_call(panel, "alpha")
    if not ok_alpha or not finite(alpha) or alpha < 0 or alpha > 1 then return nil end
    local ok_x, x = safe_call(panel, "x")
    local ok_y, y = safe_call(panel, "y")
    local ok_w, w = safe_call(panel, "w")
    local ok_h, h = safe_call(panel, "h")
    if not ok_x or not ok_y or not ok_w or not ok_h then return nil end
    if not finite(x) or not finite(y) or not finite(w) or not finite(h) then return nil end
    if w <= 0 or h <= 0 then return nil end
    local phase_alpha = alpha
    if require_white then
        local ok_color, color = safe_call(panel, "color")
        if not ok_color or not color then return nil end
        if not finite(color.r) or not finite(color.g) or not finite(color.b) then return nil end
        if math.abs(color.r - 1) > 0.001 or math.abs(color.g - 1) > 0.001
            or math.abs(color.b - 1) > 0.001 then return nil end
        if not finite(color.a) or color.a < 0 or color.a > 1 then return nil end
        phase_alpha = color.a
    end
    return {alpha = phase_alpha, x = x, y = y, w = w, h = h}
end

local function flash_centered_scaled(ghost, base, scale)
    local function close(a, b) return finite(a) and finite(b) and math.abs(a - b) <= 0.05 end
    return close(ghost.w, base.w * scale) and close(ghost.h, base.h * scale)
        and close(ghost.x + ghost.w * .5, base.x + base.w * .5)
        and close(ghost.y + ghost.h * .5, base.y + base.h * .5)
end

function M:_grenade_flash_chain()
    local mgr = self._hud_manager or (managers and managers.hud)
    local panels = mgr and mgr._teammate_panels
    local slot = HUDManager and HUDManager.PLAYER_PANEL or nil
    if not finite(slot) then return nil end
    local entry = type(panels) == "table" and panels[slot] or nil
    local entry_panel = type(entry) == "table" and entry._panel or nil
    if not live(entry_panel) then return nil end
    local player = flash_child(entry_panel, "player")
    if not player then return nil end
    local grenades = flash_child(player, "grenades_panel")
    if not grenades then return nil end
    local base1 = flash_child(grenades, FLASH_SOURCES[1].base)
    local ghost1 = flash_child(grenades, FLASH_SOURCES[1].ghost)
    local base2 = flash_child(grenades, FLASH_SOURCES[2].base)
    local ghost2 = flash_child(grenades, FLASH_SOURCES[2].ghost)
    if not base1 or not ghost1 or not base2 or not ghost2 then return nil end
    return entry_panel, grenades, {base1, base2}, {ghost1, ghost2}
end

function M:_grenade_flash_fresh(snap, projectile)
    local pm = managers and managers.player
    if not pm or self._player_manager ~= pm or self._hud_manager ~= (managers and managers.hud) then
        return false
    end
    local ok_unit, unit = safe_call(pm, "player_unit")
    if not ok_unit or unit == nil or unit ~= self._player_unit then return false end
    if type(alive) == "function" then
        local ok_alive, is_alive = pcall(alive, unit)
        if not ok_alive or is_alive ~= true then return false end
    end
    local ok_session, session = safe_call(managers.network, "session")
    if not ok_session or session == nil or session ~= self._session then return false end
    local ok_peer, peer = safe_call(session, "local_peer")
    if not ok_peer or peer == nil then return false end
    local ok_id, peer_id = safe_call(peer, "id")
    if not ok_id or peer_id ~= self._peer_id then return false end
    local equipment = pm._equipment
    if not equipment or equipment ~= self._equipment_table then return false end
    if equipment.selections ~= self._selections_table then return false end
    local registry = pm._global and pm._global.synced_grenades
    if not registry or registry ~= self._grenade_registry then return false end
    if managers.game_play_central ~= self._gpc then return false end
    local got, entry = safe_call(pm, "get_synced_grenades", peer_id)
    if not got or type(entry) ~= "table" or type(entry.grenade) ~= "string" then return false end
    if entry.grenade ~= self._projectile_id
        or projectile.projectile_id ~= self._projectile_id then return false end
    local amount_ok, amount = safe_call(pm, "get_grenade_amount", peer_id)
    if not amount_ok or not is_valid_known_quantity(amount) then return false end
    local maximum_ok, maximum = safe_call(pm, "get_max_grenades", entry.grenade)
    if not maximum_ok or not is_valid_known_quantity(maximum) then return false end
    if type(snap) ~= "table" or type(snap.projectile) ~= "table" then return false end
    local snapshot = snap.projectile
    local charges = snapshot.charges
    local snapshot_maximum = snapshot.maximum
    if type(charges) ~= "table" or charges.known ~= true or charges.raw ~= amount then return false end
    if type(snapshot_maximum) ~= "table" or snapshot_maximum.known ~= true
        or snapshot_maximum.raw ~= maximum then return false end
    local projectiles = tweak_data and tweak_data.blackmarket and tweak_data.blackmarket.projectiles
    local td = projectiles and projectiles[entry.grenade]
    if type(td) ~= "table" then return false end
    local ability = td.ability == true or (type(td.ability) == "string" and td.ability ~= "")
    local throwable = td.throwable == true or td.is_a_grenade == true
    local kind
    if ability and not throwable then kind = "ability"
    elseif throwable and not ability then kind = "throwable" end
    if kind ~= projectile.kind then return false end
    return true
end

function M:_read_grenade_flash_source(snap)
    local row = type(self._rows) == "table" and self._rows[4] or nil
    if not row or not row._tile or type(row._icon_descriptor) ~= "table" then return nil end
    local entry_panel, grenades, bases, ghosts = self:_grenade_flash_chain()
    if not entry_panel then return nil end
    snap = snap or self:get_snapshot()
    if type(snap) ~= "table" or snap.source_known ~= true or snap.unsupported then return nil end
    if snap.source_generation ~= self._source_generation then return nil end
    local projectile = snap.projectile
    if type(projectile) ~= "table" then return nil end
    if projectile.kind ~= "ability" and projectile.kind ~= "throwable" then return nil end
    if not (projectile.charges and projectile.charges.known == true) then return nil end
    if not self:_grenade_flash_fresh(snap, projectile) then return nil end
    local states = {}
    for i = 1, 2 do
        local ghost = flash_leaf_state(ghosts[i], true, FLASH_GROUP)
        local base = flash_leaf_state(bases[i], false, FLASH_BASE_LEASE)
        if not ghost or not base then return nil end
        states[i] = {ghost = ghost, base = base}
    end
    local alpha = states[1].ghost.alpha
    if math.abs(alpha - states[2].ghost.alpha) > 0.005 then return nil end
    local scale = 1 + (1 - alpha)
    if not flash_centered_scaled(states[1].ghost, states[1].base, scale)
        or not flash_centered_scaled(states[2].ghost, states[2].base, scale) then
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
        return false
    end
    local source = self:_read_grenade_flash_source(snap)
    self._grenade_flash_source = source
    if not source or source.alpha <= 0 then
        row:_hide_grenade_flash()
        self._grenade_flash_ok = false
        self._grenade_flash_source = nil
        return false
    end
    local pcall_ok, rendered = pcall(function() return row:render_grenade_flash(source.alpha, source.scale) end)
    self._grenade_flash_ok = pcall_ok and rendered == true and row:_verify_grenade_flash() == true
    if not self._grenade_flash_ok then
        row:_hide_grenade_flash()
        self._grenade_flash_source = nil
    end
    return self._grenade_flash_ok
end

function M:_throttle_grenade_flash()
    local row = type(self._rows) == "table" and self._rows[4] or nil
    if not row or not row._tile then
        self._grenade_flash_ok = false
        self._grenade_flash_source = nil
        return false
    end
    if self._grenade_flash_rejected == true then
        return false
    end
    if self._grenade_flash_ok == true then
        if not row:_verify_grenade_flash() then
            self._grenade_flash_ok = false
            self._grenade_flash_source = nil
            self._grenade_flash_rejected = true
            return false
        end
    elseif not row:_verify_grenade_flash() then
        self._grenade_flash_rejected = true
        return false
    end
    local source = self:_read_grenade_flash_source()
    self._grenade_flash_source = source
    if not source or source.alpha <= 0 then
        row:_hide_grenade_flash()
        self._grenade_flash_ok = false
        self._grenade_flash_source = nil
        return false
    end
    local pcall_ok, rendered = pcall(function() return row:render_grenade_flash(source.alpha, source.scale) end)
    self._grenade_flash_ok = pcall_ok and rendered == true and row:_verify_grenade_flash() == true
    if not self._grenade_flash_ok then
        row:_hide_grenade_flash()
        self._grenade_flash_source = nil
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

function M:_present()
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
        local remaining=cooldown.remaining
        if is_valid_positive_quantity(remaining) and is_valid_positive_quantity(cooldown.duration)
            and remaining<=cooldown.duration then
            grenade_value=string.format("%ds",math.ceil(remaining))
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
    if not self:verify() then safe_call(self._root,"set_visible",false) end
end

function M:verify()
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
    local progress=math.min(1,math.max(0,1-remaining/cooldown.duration))
    local value=string.format("%ds",math.ceil(remaining))
    if not row:animate_recharge(value,progress) then
        safe_call(self._root,"set_visible",false)
    end
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

local function install(class, method, fn)
    if not class or not Hooks then return end
    local ok, target = pcall(function() return class[method] end)
    if not ok or type(target) ~= "function" then return end
    M._hooks = M._hooks or {}
    local id = "KyoHUD_Equipment_" .. tostring(RequiredScript) .. "_" .. method
    if M._hooks[id] then return end
    Hooks:PostHook(class, method, id, fn)
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
    install(HUDManager, "set_teammate_ability_radial", function(self, i, data)
        if local_panel(self, i) then M:_capture_activity(data and data.current, data and data.total) end
    end)
    install(HUDManager, "activate_teammate_ability_radial", function(self, i, left, total)
        if local_panel(self, i) then M:_capture_activity(left, total) end
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
            wrapper = function(self, ...)
                local rt = residual_context()
                if not rt then return original(self, ...) end
                local start = rt:_residual_stamp()
                local result = original(self, ...)
                rt:_residual_record(phase, start)
                return result
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
    install("_fresh_cooldown", "equipment_snapshot", true)
    install("_present", "equipment_present", false)
    install("_animate_recharge", "equipment_present", true)
    install("_sync_grenade_flash", "equipment_present", true)
    install("_throttle_grenade_flash", "equipment_present", true)
    install("verify", "equipment_verify", true)
end
install_residual_phase_wrappers()
