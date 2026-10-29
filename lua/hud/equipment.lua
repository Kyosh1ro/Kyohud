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
    if self._projectile_id ~= projectile.projectile_id or self._gpc ~= gpc or self._grenade_registry ~= registry then
        self._activity = nil
        self._cooldown_event = nil
        self._projectile_id = projectile.projectile_id
        self._gpc = gpc
        self._grenade_registry = registry
    end
    local cooldown = {known = false, active = false, clock_kind = "game"}
    if projectile.projectile_id then
        local good, remaining = safe_call(pm, "get_timer_remaining", "replenish_grenades")
        if good and (remaining == nil or is_valid_known_quantity(remaining)) then
            cooldown.known = true
            cooldown.active = remaining ~= nil and remaining > 0
            cooldown.remaining = remaining
        end
        if td and is_valid_positive_quantity(td.base_cooldown) then cooldown.duration = td.base_cooldown end
    end
    snap.cooldown = cooldown
    local clock_ok, timer = safe_call(TimerManager, "game")
    local time_ok, now = safe_call(clock_ok and timer or nil, "time")
    if time_ok and is_valid_known_quantity(now) then
        cooldown.sampled_at = now
        local event = self._cooldown_event
        if event and is_valid_positive_quantity(event.duration) then cooldown.duration = event.duration end
    end
    if self._cooldown_event and self._cooldown_event.cancelled then
        cooldown.known=true;cooldown.active=false;cooldown.remaining=nil
    end
    snap.activity = self._activity or {known = false, active = false}
end

local function detached(value)
    if type(value) ~= "table" then return value end
    local result = {}
    for k, v in pairs(value) do result[k] = detached(v) end
    return result
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
        cooldown = self:_timed_snapshot(self._snapshot.cooldown),
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
    self._cable_zero = nil
    self._equipment_table = nil
    self._projectile_id = nil
    self._amount_text = nil
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
    local g=layout.resolve(pw,ph,kyohud.settings.hud_scale)
    if not g or not g.valid then return nil end
    local us,scale=g.uniform_scale,g.scale
    if us*scale < .35 then return nil end
    local w,h=320*us*scale,168*us*scale
    local x=pw-g.margin_x-360*us*scale-12*us-w
    local y=ph-g.margin_x-200*us-h
    if x<g.margin_x or y<g.margin_y or x+w>pw-g.margin_x or y+h>ph-g.margin_y then return nil end
    return {x=x,y=y,w=w,h=h}
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
    self._root=nil;self._rows=nil;self._parent=nil;self._mounted=false;self._layout=nil
    self._last_ui=nil;self._last_poll=nil
end

function M:_name(id, key, fallback)
    if not id or not key then return fallback end
    local cached=self._names[id]
    if not cached or cached.key~=key then
        cached={key=key,text=loc(key,fallback)};self._names[id]=cached
    end
    return cached.text
end

function M:_present()
    if not live(self._root) or not self._rows then return end
    local geom=self:_geometry()
    self._layout=geom
    local snap=self:get_snapshot()
    if not geom or not snap.source_known or snap.unsupported then
        safe_call(self._root,"set_visible",false);return
    end
    local _,x=safe_call(self._root,"x");local _,y=safe_call(self._root,"y")
    local _,w=safe_call(self._root,"w");local _,h=safe_call(self._root,"h")
    if x~=geom.x or y~=geom.y or w~=geom.w or h~=geom.h then
        safe_call(self._root,"set_shape",geom.x,geom.y,geom.w,geom.h)
    end
    local texts=self._texts
    for i=1,6 do self._rows[i]:layout(0,(i-1)*geom.h/6,geom.w,geom.h/6) end
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
            value=entry.amount_text or (#counts>0 and table.concat(counts," | ") or "--")
        end
        self._rows[i]:render(label,value,nil,entry~=nil and snap.selected_effective==entry.equipment_id)
    end
    self._rows[3]:render(texts.cables,count_text(snap.cables,texts.unlimited))
    local projectile=snap.projectile
    local kind=projectile.kind=="ability" and texts.ability or projectile.kind=="throwable" and texts.throwable or "--"
    local label=self:_name(projectile.projectile_id,projectile.name_id,kind)
    self._rows[4]:render(label,count_text(projectile.charges).." / "..count_text(projectile.maximum))
    for i,channel in ipairs({snap.cooldown,snap.activity}) do
        local text="--"
        local progress
        if channel and channel.known then
            text=channel.active and string.format("%ds",math.ceil(channel.remaining)) or ""
            if channel.active and is_valid_positive_quantity(channel.duration) then progress=channel.remaining/channel.duration end
        end
        self._rows[4+i]:render(i==1 and texts.cooldown or texts.active,text,progress)
    end
    safe_call(self._root,"set_visible",true)
    if not self:verify() then safe_call(self._root,"set_visible",false) end
end

function M:verify()
    if not live(self._root) or not live(self._parent) or not self._layout or not self._rows then return false end
    local shown,visible=safe_call(self._root,"visible")
    if not shown or visible~=true then return false end
    local g=self._layout
    for _,key in ipairs({"x","y","w","h"}) do
        local ok,value=safe_call(self._root,key)
        if not ok or type(value)~="number" or value~=value or math.abs(value-g[key])>.05 then return false end
    end
    for _,row in ipairs(self._rows) do if not row:verify() then return false end end
    return #self._rows==6
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

function M:update(manager,t,dt)
    if not managers or manager~=managers.hud or not is_valid_known_quantity(t) then return end
    if not enabled() then self:unmount();return end
    if not live(self._root) then
        if self._last_mount and t>=self._last_mount and t-self._last_mount<.5 then return end
        self._last_mount=t;self:mount(manager)
    end
    if not live(self._root) then return end
    if self._last_ui and t>=self._last_ui and t-self._last_ui<.05 then return end
    self._last_ui=t
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
        M._cooldown_event = type(data) == "table" and {duration = data.duration} or {cancelled = true}
        M._dirty = true
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
