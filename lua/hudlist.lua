-- hudlist.lua — autonomous KyoHUD buff-state provider

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud

local KH = kyohud
if not KH.hudlist_catalog then
    dofile(ModPath .. "lua/hudlist_catalog.lua")
end
local Catalog = assert(KH.hudlist_catalog, "KyoHUD HUDList catalog is missing")
local Provider = KH.hudlist or {}
KH.hudlist = Provider

Provider._buffs = Provider._buffs or {}
Provider._listeners = Provider._listeners or {}
Provider._arrival_order = Provider._arrival_order or {}
Provider._team_sources = Provider._team_sources or {}
Provider._sources = Provider._sources or {}
Provider._next_stack_id = Provider._next_stack_id or 0

local function finite_number(value)
    value = tonumber(value)
    if not value or value ~= value or value == math.huge or value == -math.huge then
        return nil
    end
    return value
end

local function current_time()
    local game_ok, game_value = pcall(function()
        return TimerManager:game():time()
    end)
    if game_ok and finite_number(game_value) then return finite_number(game_value) end
    local ok, value = pcall(function()
        return Application:time()
    end)
    return ok and finite_number(value) or 0
end

function Provider:get_buffs()
    return self._buffs
end

local function copy_table(source)
    if type(source) ~= "table" then return source end
    local result = {}
    for key, value in pairs(source) do
        if key == "stacks" and type(value) == "table" then
            result[key] = {}
            for index, stack in ipairs(value) do result[key][index] = copy_table(stack) end
        elseif key ~= "team_sources" then
            result[key] = value
        end
    end
    return result
end

function Provider:get_buff(id)
    return copy_table(self._buffs[id])
end

function Provider:get_arrival_order()
    return self._arrival_order
end

function Provider:resolve_mapping(category, upgrade, level)
    return Catalog:resolve(category, upgrade, level)
end

function Provider:resolve_mapping_info(category, upgrade, level)
    return Catalog:resolve_info(category, upgrade, level)
end

function Provider:resolve_team_mapping(category, upgrade, level)
    return Catalog:resolve_team(category, upgrade, level)
end

function Provider:resolve_team_mapping_info(category, upgrade, level)
    return Catalog:resolve_team_info(category, upgrade, level)
end

function Provider:register_listener(id, source, event, callback)
    if type(event) == "function" and callback == nil then
        callback = event
        event = nil
    end
    if type(id) ~= "string" or type(callback) ~= "function" then return false end
    self._listeners[id .. ":" .. tostring(source) .. ":" .. tostring(event)] = {
        source = source,
        event = event,
        callback = callback,
    }
    return true
end

function Provider:_notify(source, event, id, data)
    for _, listener in pairs(self._listeners) do
        if listener.source == source and (not listener.event or listener.event == event) then
            listener.callback(event, id, data)
        end
    end
end

function Provider:get_player_actions()
    return {}
end

function Provider:reset()
    self._buffs = {}
    self._arrival_order = {}
    self._team_sources = {}
    self._sources = {}
    self._next_stack_id = 0
    self._next_position_buff_check_t = 0
    self._active_grenade_cooldown_id = nil
end

function Provider:get_source_count(id)
    local count = 0
    for _ in pairs(self._sources[id] or {}) do count = count + 1 end
    return count
end

function Provider:_recalculate_sources(id)
    local sources = self._sources[id]
    if not sources or not next(sources) then
        self._sources[id] = nil
        self:_deactivate("buff", id, { reason = "last_source_removed" })
        return
    end

    local count, expire_t, value = 0, nil, nil
    local has_jamming, has_feedback = false, false
    for _, source in pairs(sources) do
        count = count + 1
        expire_t = not expire_t and source.expire_t
            or source.expire_t and math.max(expire_t, source.expire_t) or expire_t
        value = not value and source.value
            or source.value and math.max(value, source.value) or value
        has_jamming = has_jamming or source.mode == "jamming"
        has_feedback = has_feedback or source.mode == "feedback"
    end
    local entry = self._buffs[id]
    if not entry then
        entry = { id = id, source = "buff", active = true }
        self._buffs[id] = entry
        self._arrival_order[#self._arrival_order + 1] = id
    end
    entry.source_count = count
    entry.expire_t = expire_t
    entry.duration = expire_t and math.max(0, expire_t - current_time()) or nil
    entry.value = value
    entry.mode = has_jamming and has_feedback and "mixed"
        or has_jamming and "jamming" or has_feedback and "feedback" or nil
    self:_notify("buff", "activate", id, entry)
end

function Provider:set_source(id, key, data)
    if type(id) ~= "string" or type(key) ~= "string" or type(data) ~= "table" then
        return false
    end
    if not Catalog.definitions[id] then return false end
    local expire_t = finite_number(data.expire_t)
    local t = current_time()
    if not expire_t or expire_t <= t then return false end
    local sources = self._sources[id] or {}
    self._sources[id] = sources
    sources[key] = {
        expire_t = expire_t,
        value = finite_number(data.value),
        mode = (data.mode == "jamming" or data.mode == "feedback") and data.mode or nil,
    }
    self:_recalculate_sources(id)
    return true
end

function Provider:remove_source(id, key)
    local sources = type(id) == "string" and self._sources[id]
    if not sources or type(key) ~= "string" or not sources[key] then return false end
    sources[key] = nil
    self:_recalculate_sources(id)
    return true
end

function Provider:get_team_source_count(id)
    id = Catalog:resolve_alias(id)
    local count = 0
    for _ in pairs(self._team_sources[id] or {}) do
        count = count + 1
    end
    return count
end

local function team_source_key(peer, category, upgrade)
    return tostring(peer) .. ":" .. category .. ":" .. upgrade
end

function Provider:add_timed_stack(id, data)
    if type(id) ~= "string" or id == "" or type(data) ~= "table" then return false end
    local definition = Catalog.definitions[id]
    if not definition or definition.state ~= "timed_stack" then return false end
    local t = finite_number(data.t) or current_time()
    local expire_t = finite_number(data.expire_t)
    local duration = finite_number(data.duration)
    if not expire_t then
        if not duration or duration < 0 then return false end
        expire_t = t + duration
    end
    if expire_t <= t then return false end
    local entry = self._buffs[id]
    local created = entry == nil
    if not entry then
        entry = { id = id, source = "buff", active = true, stacks = {} }
        self._buffs[id] = entry
        self._arrival_order[#self._arrival_order + 1] = id
    end
    self._next_stack_id = self._next_stack_id + 1
    entry.stacks[#entry.stacks + 1] = {
        stack_id = self._next_stack_id, t = t, expire_t = expire_t,
        producer = type(data.producer) == "string" and data.producer or nil,
    }
    table.sort(entry.stacks, function(left, right)
        if left.expire_t == right.expire_t then return left.stack_id < right.stack_id end
        return left.expire_t < right.expire_t
    end)
    entry.stack_count = #entry.stacks
    entry.t = entry.stacks[1].t
    entry.expire_t = entry.stacks[#entry.stacks].expire_t
    entry.duration = entry.expire_t - t
    if created then self:_notify("buff", "activate", id, entry) end
    self:_notify("buff", "set_stack_count", id, entry)
    return true
end

function Provider:_recalculate_team(id)
    local sources = self._team_sources[id]
    if not sources or not next(sources) then
        self._team_sources[id] = nil
        self:_deactivate("buff", id, { reason = "last_team_contributor_removed" })
        return
    end
    local best_level, best_value, count = nil, nil, 0
    for _, contribution in pairs(sources) do
        count = count + 1
        if not best_level or contribution.level > best_level then
            best_level, best_value = contribution.level, contribution.value
        elseif contribution.level == best_level and contribution.value ~= nil
                and (best_value == nil or contribution.value > best_value) then
            best_value = contribution.value
        end
    end
    local entry = self._buffs[id]
    if not entry then
        entry = { id = id, source = "buff", active = true }
        self._buffs[id] = entry
        self._arrival_order[#self._arrival_order + 1] = id
    end
    entry.team_level = best_level
    entry.value = best_value
    entry.contributor_count = count
    entry.stack_count = nil
    self:_notify("buff", "activate", id, entry)
end

function Provider:activate_team_source(peer, category, upgrade, level, value)
    if type(category) ~= "string" or type(upgrade) ~= "string" then return false end
    peer = finite_number(peer)
    level = finite_number(level)
    if not peer or peer < 0 or peer % 1 ~= 0 or not level or level % 1 ~= 0 then
        return false
    end
    local id, event_id = Catalog:resolve_team_public(category, upgrade, level)
    if not id then return false end

    local sources = self._team_sources[id] or {}
    self._team_sources[id] = sources
    sources[team_source_key(peer, category, upgrade)] = {
        peer = peer,
        category = category,
        upgrade = upgrade,
        level = level,
        value = finite_number(value),
        event_id = event_id,
        public_id = id,
        provenance = peer == 0 and "local" or "synchronized",
    }
    self:_recalculate_team(id)
    return true
end

function Provider:deactivate_team_source(peer, category, upgrade, level)
    peer = finite_number(peer)
    level = finite_number(level)
    local id = peer and level and Catalog:resolve_team_public(category, upgrade, level)
    local sources = id and self._team_sources[id]
    if not sources then return false end

    sources[team_source_key(peer, category, upgrade)] = nil
    self:_recalculate_team(id)
    return true
end

function Provider:remove_team_sources_for_peer(peer)
    peer = finite_number(peer)
    if not peer or peer < 0 or peer % 1 ~= 0 then return 0 end
    local removed, affected = 0, {}
    for id, sources in pairs(self._team_sources) do
        for key, contribution in pairs(sources) do
            if contribution.peer == peer then
                sources[key] = nil
                removed = removed + 1
                affected[id] = true
            end
        end
    end
    for id in pairs(affected) do self:_recalculate_team(id) end
    return removed
end

function Provider:_deactivate(source, id, data)
    if not self._buffs[id] then return false end
    self._buffs[id] = nil
    for index, active_id in ipairs(self._arrival_order) do
        if active_id == id then
            table.remove(self._arrival_order, index)
            break
        end
    end
    self:_notify(source, "deactivate", id, data or {})
    return true
end

function Provider:update(t)
    t = tonumber(t) or current_time()
    local source_changes = {}
    for id, sources in pairs(self._sources) do
        for key, source in pairs(sources) do
            if source.expire_t <= t then
                sources[key] = nil
                source_changes[id] = true
            end
        end
    end
    for id in pairs(source_changes) do self:_recalculate_sources(id) end
    local expired = {}
    for id, entry in pairs(self._buffs) do
        if entry.stacks then
            local write = 1
            for read = 1, #entry.stacks do
                local stack = entry.stacks[read]
                if stack.expire_t > t then
                    entry.stacks[write] = stack
                    write = write + 1
                end
            end
            for index = #entry.stacks, write, -1 do entry.stacks[index] = nil end
            entry.stack_count = #entry.stacks
            if entry.stack_count == 0 then
                expired[#expired + 1] = id
            else
                entry.t = entry.stacks[1].t
                entry.expire_t = entry.stacks[#entry.stacks].expire_t
                self:_notify("buff", "set_stack_count", id, entry)
            end
        elseif entry.expire_t and entry.expire_t <= t then
            expired[#expired + 1] = id
        end
    end
    for _, id in ipairs(expired) do
        self:_deactivate("buff", id, { reason = "expired", t = t })
    end
end

function Provider:event(source, event, id, data)
    if source ~= "buff" or type(id) ~= "string" or id == "" then return end

    data = type(data) == "table" and data or {}
    local entry = self._buffs[id]
    if event == "deactivate" then
        self:_deactivate(source, id, data)
        return
    end
    if event ~= "activate" and not entry then return end
    if not entry then
        entry = { id = id, source = source }
        self._buffs[id] = entry
        self._arrival_order[#self._arrival_order + 1] = id
    end

    if event == "set_value" then
        entry.value = finite_number(data.value)
        self:_notify(source, event, id, entry)
        return
    end

    if event == "set_progress" then
        entry.progress = finite_number(data.progress)
        self:_notify(source, event, id, entry)
        return
    end

    if event == "set_stack_count" then
        entry.stack_count = finite_number(data.stack_count)
        self:_notify(source, event, id, entry)
        return
    end

    if event ~= "activate" and event ~= "set_duration" then return end

    local t = finite_number(data.t) or current_time()
    local duration = finite_number(data.duration)
    local expire_t = finite_number(data.expire_t)
    if not expire_t and duration then
        expire_t = t + duration
    elseif expire_t and not duration then
        duration = math.max(0, expire_t - t)
    end

    entry.active = true
    entry.t = t
    entry.duration = duration
    entry.expire_t = expire_t
    if event == "activate" and data.value ~= nil then
        entry.value = finite_number(data.value)
    end
    if event == "activate" then
        entry.category = data.category
        entry.upgrade = data.upgrade
        entry.level = data.level
        entry.progress = finite_number(data.progress)
        entry.best_peer = finite_number(data.best_peer)
        entry.provenance = data.provenance
        entry.source_count = finite_number(data.source_count)
    end
    self:_notify(source, event, id, entry)
end

local function mapped_temporary_id(category, upgrade, level)
    return Catalog:resolve(category, upgrade, level)
end

local function emit_temporary_upgrade(manager, category, upgrade, level)
    level = finite_number(level)
    if not level or level % 1 ~= 0 then return end
    local id = mapped_temporary_id(category, upgrade, level)
    if not id then return end

    local category_state = manager._temporary_upgrades and manager._temporary_upgrades[category]
    local state = category_state and category_state[upgrade]
    local expire_t = state and finite_number(state.expire_time)
    local t = current_time()
    if not expire_t or expire_t <= t then return end

    local ok, value = pcall(function()
        return manager:temporary_upgrade_value(category, upgrade, 0)
    end)
    Provider:event("buff", "activate", id, {
        t = t,
        expire_t = expire_t,
        value = ok and finite_number(value) or nil,
        category = category,
        upgrade = upgrade,
        level = level,
    })

    if id == "copycat_health_invul" then
        local values_ok, values = pcall(function()
            return manager:upgrade_value("temporary", "mrwi_health_invulnerable")
        end)
        local cooldown = values_ok and type(values) == "table"
            and finite_number(values[3]) or nil
        if cooldown and cooldown > 0 then
            Provider:event("buff", "activate", "copycat_health_invul_debuff", {
                t = t, duration = cooldown,
            })
        end
    end
end

local function emit_temporary_property(manager, property)
    local id = Catalog:resolve("property", property, 1)
    if not id then return end

    local state = manager._properties and manager._properties[property]
    local value = state and state[1]
    local expire_t = state and finite_number(state[2])
    local t = current_time()
    if not expire_t or expire_t <= t then return end

    Provider:event("buff", "activate", id, {
        t = t,
        expire_t = expire_t,
        value = finite_number(value),
        category = "property",
        upgrade = property,
        level = 1,
    })
end

local function emit_cooldown_upgrade(manager, category, upgrade)
    local ok, level = pcall(function()
        return manager:upgrade_level(category, upgrade, 1)
    end)
    level = ok and finite_number(level) or 1
    if not level or level % 1 ~= 0 then return end
    local id = Catalog:resolve("cooldown", upgrade, level)
    if not id then return end

    local categories = manager._global and manager._global.cooldown_upgrades
    local category_state = categories and categories[category]
    local state = category_state and category_state[upgrade]
    local expire_t = state and finite_number(state.cooldown_time)
    local t = current_time()
    if not expire_t or expire_t <= t then return end

    Provider:event("buff", "activate", id, {
        t = t,
        expire_t = expire_t,
        category = category,
        upgrade = upgrade,
        level = level,
    })
end

local function emit_player_property(manager, property)
    local id = Catalog:resolve("property", property, 1)
    if not id then return end

    local properties = manager._properties and manager._properties._properties
    local value = properties and finite_number(properties[property])
    if value == nil then return end

    Provider:event("buff", "activate", id, {
        value = value,
        category = "property",
        upgrade = property,
        level = 1,
    })
end

local function team_value(manager, category, upgrade)
    local ok, value = pcall(function()
        return manager:team_upgrade_value(category, upgrade, 0)
    end)
    return ok and finite_number(value) or nil
end

local function direct_id(id)
    local literals = Catalog.direct_ids and Catalog.direct_ids.literals
    return type(id) == "string" and literals and literals[id] and id or nil
end

local function update_partner_in_crime(manager)
    local count = finite_number(manager._local_player_minions) or 0
    local function update(id, upgrade)
        if not direct_id(id) then return end
        local ok, owned = pcall(function()
            return manager:has_category_upgrade("player", upgrade)
        end)
        local event = count > 0 and ok and owned and "activate" or "deactivate"
        Provider:event("buff", event, id, { stack_count = count })
    end
    update("partner_in_crime", "minion_master_speed_multiplier")
    update("partner_in_crime_aced", "minion_master_health_multiplier")
end

local function update_messiah(manager)
    local id = direct_id("messiah")
    local charges = finite_number(manager._messiah_charges)
    if not id or not charges then return end
    if charges <= 0 then
        Provider:event("buff", "deactivate", id)
        return
    end
    Provider:event("buff", "activate", id)
    Provider:event("buff", "set_stack_count", id, { stack_count = charges })
end

local function update_maniac(manager)
    local session = managers and managers.network and managers.network:session()
    local ok, local_peer_id = pcall(function() return session:local_peer():id() end)
    local_peer_id = ok and finite_number(local_peer_id) or nil
    if not local_peer_id then return end

    local best_ok, absorption, best_peer = pcall(function()
        return manager:get_best_cocaine_damage_absorption(local_peer_id)
    end)
    absorption = best_ok and finite_number(absorption) or nil
    best_peer = best_ok and finite_number(best_peer) or nil
    if not absorption then return end

    if absorption > 0 then
        local max_ok, maximum = pcall(function()
            return manager:get_local_cocaine_damage_absorption_max()
        end)
        maximum = max_ok and finite_number(maximum) or nil
        local progress = maximum and maximum > 0
            and math.max(0, math.min(1, absorption / maximum)) or nil
        Provider:event("buff", "activate", "maniac", {
            value = absorption,
            progress = progress,
            best_peer = best_peer,
            provenance = best_peer == local_peer_id and "local" or "synchronized",
        })
    else
        Provider:event("buff", "deactivate", "maniac")
    end

    local expire_t = finite_number(manager._damage_dealt_to_cops_decay_t)
    local t = current_time()
    if expire_t and expire_t > t then
        Provider:event("buff", "activate", "maniac_debuff", { t = t, expire_t = expire_t })
    end
end

local function update_sicario(manager)
    local gain = finite_number(manager._dodge_shot_gain_value)
    if gain == nil then return end
    if gain <= 0 then
        Provider:event("buff", "deactivate", "sicario_dodge")
        return
    end

    local ok, multiplier = pcall(function()
        return manager:upgrade_value("player", "sicario_multiplier", 1)
    end)
    multiplier = ok and finite_number(multiplier) or 1
    Provider:event("buff", "activate", "sicario_dodge", {
        value = gain * (multiplier or 1),
    })

    local values = tweak_data and tweak_data.upgrades and tweak_data.upgrades.values
    local dodge = values and values.player and values.player.dodge_shot_gain
    local duration = finite_number(dodge and dodge[1] and dodge[1][2])
    if duration and duration >= 0 then
        Provider:event("buff", "activate", "sicario_dodge_debuff", {
            t = current_time(), duration = duration,
        })
    end
end

local function update_copycat_headshot(manager)
    local t = current_time()
    local expire_t = finite_number(manager._on_headshot_dealt_t)
    if not expire_t or expire_t <= t then return end
    local ok, value = pcall(function()
        return manager:upgrade_value("player", "headshot_regen_health_bonus", 0)
    end)
    value = ok and finite_number(value) or nil
    if not value or value <= 0 then return end
    Provider:event("buff", "activate", "copycat_health_shot_debuff", {
        t = t, expire_t = expire_t, value = value,
    })
end

local function equipped_grenade_id()
    local ok, id = pcall(function() return managers.blackmarket:equipped_grenade() end)
    return ok and type(id) == "string" and id or nil
end

local function update_grenade_cooldown(manager)
    local public_id = Catalog:resolve_dynamic("grenade", equipped_grenade_id())
    if Provider._active_grenade_cooldown_id
            and Provider._active_grenade_cooldown_id ~= public_id then
        Provider:event("buff", "deactivate", Provider._active_grenade_cooldown_id)
        Provider._active_grenade_cooldown_id = nil
    end
    if not public_id then return end

    local timer = manager._timers and manager._timers.replenish_grenades
    local expire_t = timer and finite_number(timer.t)
    local t = current_time()
    if not expire_t or expire_t <= t then return end
    Provider:event("buff", "activate", public_id, { t = t, expire_t = expire_t })
    Provider._active_grenade_cooldown_id = public_id
end

local function end_grenade_cooldown()
    if Provider._active_grenade_cooldown_id then
        Provider:event("buff", "deactivate", Provider._active_grenade_cooldown_id)
        Provider._active_grenade_cooldown_id = nil
    end
end

local function update_custom_cooldown(manager, category, upgrade)
    local public_id = Catalog:resolve_dynamic("custom", upgrade)
    if not public_id or type(category) ~= "string" then return end
    local timer = manager._timers and manager._timers[category .. "_" .. upgrade]
    local expire_t = timer and finite_number(timer.t)
    local t = current_time()
    if not expire_t or expire_t <= t then return end
    Provider:event("buff", "activate", public_id, { t = t, expire_t = expire_t })
end

local function pocket_ecm_source_key(inventory, mode)
    return tostring(inventory) .. ":" .. mode
end

local function start_pocket_ecm(inventory, expected_mode)
    local data = inventory._jammer_data
    if type(data) ~= "table" or data.effect ~= expected_mode then return end
    Provider:set_source("pocket_ecm_jammer",
        pocket_ecm_source_key(inventory, expected_mode), {
            expire_t = data.t,
            mode = expected_mode,
        })
end

local function stop_pocket_ecm(inventory, expected_mode)
    local data = inventory._jammer_data
    if type(data) ~= "table" or data.effect ~= expected_mode then return end
    Provider:remove_source("pocket_ecm_jammer",
        pocket_ecm_source_key(inventory, expected_mode))
end

local function update_position_buffs(manager, t)
    t = finite_number(t) or current_time()
    if t < (Provider._next_position_buff_check_t or 0) then return end
    Provider._next_position_buff_check_t = t + 0.25

    local unit_ok, unit = pcall(function() return manager:player_unit() end)
    if not unit_ok or not alive(unit) then
        Provider:event("buff", "deactivate", "uppers")
        Provider:event("buff", "deactivate", "smoke_screen_grenade")
        return
    end

    local upgrade_ok, has_uppers = pcall(function()
        return manager:has_category_upgrade("first_aid_kit", "first_aid_kit_auto_recovery")
    end)
    if upgrade_ok and has_uppers and FirstAidKitBase and FirstAidKitBase.GetFirstAidKit then
        local kit_ok, kit = pcall(function()
            return FirstAidKitBase.GetFirstAidKit(unit:position())
        end)
        Provider:event("buff", kit_ok and kit and "activate" or "deactivate", "uppers")
    else
        Provider:event("buff", "deactivate", "uppers")
    end

    local screens_ok, screens = pcall(function() return manager:smoke_screens() end)
    screens = screens_ok and type(screens) == "table" and screens or {}
    local count, value, longest = 0, 0, 0
    local has_local, has_allied = false, false
    for _, smoke in ipairs(screens) do
        local ok, is_active, in_smoke = pcall(function()
            return smoke:alive(), smoke:is_in_smoke(unit)
        end)
        if ok and is_active and in_smoke then
            count = count + 1
            longest = math.max(longest, finite_number(smoke._timer) or 0)
            local dodge_ok, dodge = pcall(function() return smoke:dodge_bonus() end)
            dodge = dodge_ok and finite_number(dodge) or 0
            local mine_ok, mine = pcall(function() return smoke:mine() end)
            if mine_ok and mine then
                has_local = true
            else
                has_allied = true
                value = value + (dodge or 0)
            end
        end
    end
    if count > 0 then
        Provider:event("buff", "activate", "smoke_screen_grenade", {
            t = t,
            expire_t = t + longest,
            value = value,
            source_count = count,
            provenance = has_local and has_allied and "mixed"
                or has_local and "local" or "allied",
        })
    else
        Provider:event("buff", "deactivate", "smoke_screen_grenade")
    end
end

local uppers_snapshots = setmetatable({}, { __mode = "k" })
local function snapshot_uppers(damage)
    uppers_snapshots[damage] = finite_number(damage._uppers_elapsed)
end

local function update_uppers_cooldown(damage)
    local before = uppers_snapshots[damage]
    uppers_snapshots[damage] = nil
    local elapsed = finite_number(damage._uppers_elapsed)
    local duration = finite_number(damage._UPPERS_COOLDOWN)
    if not before or not elapsed or elapsed <= before or not duration or duration <= 0 then return end
    Provider:event("buff", "activate", "uppers_debuff", {
        t = elapsed, duration = duration,
    })
end

local biker_snapshots = setmetatable({}, { __mode = "k" })
local function snapshot_biker(manager)
    local t, counts = current_time(), {}
    for _, deadline in ipairs(manager._wild_kill_triggers or {}) do
        deadline = finite_number(deadline)
        if deadline and deadline > t then counts[deadline] = (counts[deadline] or 0) + 1 end
    end
    biker_snapshots[manager] = { t = t, counts = counts }
end

local function emit_new_biker_stacks(manager)
    local snapshot = biker_snapshots[manager] or { t = current_time(), counts = {} }
    biker_snapshots[manager] = nil
    for _, deadline in ipairs(manager._wild_kill_triggers or {}) do
        deadline = finite_number(deadline)
        if deadline and deadline > snapshot.t then
            local old_count = snapshot.counts[deadline] or 0
            if old_count > 0 then
                snapshot.counts[deadline] = old_count - 1
            else
                Provider:add_timed_stack("biker", { t = snapshot.t, expire_t = deadline,
                    producer = "chk_wild_kill_counter" })
            end
        end
    end
end

local grinder_snapshots = setmetatable({}, { __mode = "k" })
local function snapshot_grinder(damage)
    local entries = {}
    for _, stack in ipairs(damage._damage_to_hot_stack or {}) do entries[stack] = true end
    grinder_snapshots[damage] = entries
end

local function emit_new_grinder_stacks(damage)
    local stacks = damage._damage_to_hot_stack or {}
    local old_entries = grinder_snapshots[damage] or {}
    grinder_snapshots[damage] = nil
    local added = false
    local tick_time = finite_number(damage._doh_data and damage._doh_data.tick_time) or 1
    for _, native in ipairs(stacks) do
        if not old_entries[native] then
        local next_tick = finite_number(native and native.next_tick)
        local ticks_left = finite_number(native and native.ticks_left)
        if next_tick and ticks_left and ticks_left > 0 then
            Provider:add_timed_stack("grinder", { t = current_time(),
                expire_t = next_tick + (ticks_left - 1) * tick_time,
                producer = "add_damage_to_hot" })
            added = true
        end
        end
    end
    if not added then return end
    local data = tweak_data and tweak_data.upgrades and tweak_data.upgrades.damage_to_hot_data
    local cooldown = finite_number(data and data.stacking_cooldown)
    if cooldown and cooldown >= 0 then
        Provider:event("buff", "activate", "grinder_debuff", {
            t = current_time(), duration = cooldown,
        })
    end
end

KH._hudlist_loaded_scripts = KH._hudlist_loaded_scripts or {}
if RequiredScript == "lib/managers/playermanager"
        and not KH._hudlist_loaded_scripts[RequiredScript] then
    KH._hudlist_loaded_scripts[RequiredScript] = true

    Hooks:PreHook(PlayerManager, "chk_wild_kill_counter",
        "KyoHUD_HUDList_BikerSnapshot", snapshot_biker)
    Hooks:PostHook(PlayerManager, "chk_wild_kill_counter",
        "KyoHUD_HUDList_BikerEmit", emit_new_biker_stacks)

    Hooks:PostHook(PlayerManager, "activate_temporary_upgrade",
        "KyoHUD_HUDList_ActivateTemporaryUpgrade", function(manager, category, upgrade)
            local ok, level = pcall(function()
                return manager:upgrade_level(category, upgrade, 1)
            end)
            emit_temporary_upgrade(manager, category, upgrade, ok and level or 1)
        end)

    Hooks:PostHook(PlayerManager, "activate_temporary_upgrade_by_level",
        "KyoHUD_HUDList_ActivateTemporaryUpgradeByLevel", function(manager, category, upgrade, level)
            emit_temporary_upgrade(manager, category, upgrade, level)
        end)

    Hooks:PostHook(PlayerManager, "disable_cooldown_upgrade",
        "KyoHUD_HUDList_DisableCooldownUpgrade", function(manager, category, upgrade)
            emit_cooldown_upgrade(manager, category, upgrade)
        end)

    Hooks:PostHook(PlayerManager, "set_property",
        "KyoHUD_HUDList_SetPlayerProperty", function(manager, property)
            emit_player_property(manager, property)
        end)

    Hooks:PostHook(PlayerManager, "remove_property",
        "KyoHUD_HUDList_RemovePlayerProperty", function(manager, property)
            local id = Catalog:resolve("property", property, 1)
            local properties = manager._properties and manager._properties._properties
            if id and (not properties or properties[property] == nil) then
                Provider:event("buff", "deactivate", id, {
                    category = "property",
                    upgrade = property,
                    level = 1,
                })
            end
        end)

    Hooks:PostHook(PlayerManager, "aquire_team_upgrade",
        "KyoHUD_HUDList_AquireTeamUpgrade", function(manager, upgrade)
            if type(upgrade) ~= "table" then return end
            Provider:activate_team_source(0, upgrade.category, upgrade.upgrade,
                upgrade.value, team_value(manager, upgrade.category, upgrade.upgrade))
        end)

    Hooks:PostHook(PlayerManager, "unaquire_team_upgrade",
        "KyoHUD_HUDList_UnaquireTeamUpgrade", function(manager, upgrade)
            if type(upgrade) ~= "table" then return end
            local categories = manager._global and manager._global.team_upgrades
            local category_state = categories and categories[upgrade.category]
            if not category_state or category_state[upgrade.upgrade] == nil then
                Provider:deactivate_team_source(0, upgrade.category, upgrade.upgrade, upgrade.value)
            end
        end)

    Hooks:PostHook(PlayerManager, "add_synced_team_upgrade",
        "KyoHUD_HUDList_AddSyncedTeamUpgrade",
        function(manager, peer_id, category, upgrade, level)
            Provider:activate_team_source(peer_id, category, upgrade, level,
                team_value(manager, category, upgrade))
        end)

    Hooks:PreHook(PlayerManager, "peer_dropped_out",
        "KyoHUD_HUDList_PeerDroppedOut", function(manager, peer)
            local ok, peer_id = pcall(function() return peer:id() end)
            if ok then Provider:remove_team_sources_for_peer(peer_id) end
        end)

    Hooks:PostHook(PlayerManager, "count_up_player_minions",
        "KyoHUD_HUDList_CountUpPlayerMinions", function(manager)
            update_partner_in_crime(manager)
        end)

    Hooks:PostHook(PlayerManager, "count_down_player_minions",
        "KyoHUD_HUDList_CountDownPlayerMinions", function(manager)
            update_partner_in_crime(manager)
        end)

    Hooks:PostHook(PlayerManager, "check_skills",
        "KyoHUD_HUDList_CheckMessiahCharges", function(manager)
            update_messiah(manager)
        end)

    Hooks:PostHook(PlayerManager, "use_messiah_charge",
        "KyoHUD_HUDList_UseMessiahCharge", function(manager)
            update_messiah(manager)
        end)

    Hooks:PostHook(PlayerManager, "_on_messiah_recharge_event",
        "KyoHUD_HUDList_RechargeMessiah", function(manager)
            update_messiah(manager)
        end)

    Hooks:PostHook(PlayerManager, "set_synced_cocaine_stacks",
        "KyoHUD_HUDList_UpdateManiac", update_maniac)

    Hooks:PostHook(PlayerManager, "_dodge_shot_gain",
        "KyoHUD_HUDList_UpdateSicario", update_sicario)

    Hooks:PostHook(PlayerManager, "on_headshot_dealt",
        "KyoHUD_HUDList_CopycatHeadshot", update_copycat_headshot)

    Hooks:PostHook(PlayerManager, "replenish_grenades",
        "KyoHUD_HUDList_StartGrenadeCooldown", update_grenade_cooldown)

    Hooks:PostHook(PlayerManager, "speed_up_grenade_cooldown",
        "KyoHUD_HUDList_ChangeGrenadeCooldown", update_grenade_cooldown)

    Hooks:PostHook(PlayerManager, "_on_grenade_cooldown_end",
        "KyoHUD_HUDList_EndGrenadeCooldown", end_grenade_cooldown)

    Hooks:PostHook(PlayerManager, "update",
        "KyoHUD_HUDList_UpdatePositionBuffs", update_position_buffs)

    Hooks:PostHook(PlayerManager, "start_custom_cooldown",
        "KyoHUD_HUDList_StartCustomCooldown", update_custom_cooldown)

    Hooks:PreHook(PlayerManager, "deactivate_temporary_upgrade",
        "KyoHUD_HUDList_DeactivateTemporaryUpgrade", function(manager, category, upgrade)
            local ok, level = pcall(function()
                return manager:upgrade_level(category, upgrade, 1)
            end)
            local id = mapped_temporary_id(category, upgrade, ok and level or 1)
            if id then
                Provider:event("buff", "deactivate", id, {
                    category = category,
                    upgrade = upgrade,
                    level = ok and level or 1,
                })
            end
        end)
elseif RequiredScript == "lib/utils/temporarypropertymanager"
        and not KH._hudlist_loaded_scripts[RequiredScript] then
    KH._hudlist_loaded_scripts[RequiredScript] = true

    Hooks:PostHook(TemporaryPropertyManager, "activate_property",
        "KyoHUD_HUDList_ActivateTemporaryProperty", function(manager, property)
            emit_temporary_property(manager, property)
        end)

    Hooks:PostHook(TemporaryPropertyManager, "remove_property",
        "KyoHUD_HUDList_RemoveTemporaryProperty", function(manager, property)
            local id = Catalog:resolve("property", property, 1)
            if id and (not manager._properties or not manager._properties[property]) then
                Provider:event("buff", "deactivate", id, {
                    category = "property",
                    upgrade = property,
                    level = 1,
                })
            end
        end)
elseif RequiredScript == "lib/units/beings/player/playerdamage"
        and not KH._hudlist_loaded_scripts[RequiredScript] then
    KH._hudlist_loaded_scripts[RequiredScript] = true
    Hooks:PreHook(PlayerDamage, "add_damage_to_hot",
        "KyoHUD_HUDList_GrinderSnapshot", snapshot_grinder)
    Hooks:PostHook(PlayerDamage, "add_damage_to_hot",
        "KyoHUD_HUDList_GrinderEmit", emit_new_grinder_stacks)
    Hooks:PreHook(PlayerDamage, "_check_bleed_out",
        "KyoHUD_HUDList_UppersSnapshot", snapshot_uppers)
    Hooks:PostHook(PlayerDamage, "_check_bleed_out",
        "KyoHUD_HUDList_UppersCooldown", update_uppers_cooldown)
elseif RequiredScript == "lib/units/beings/player/playerinventory"
        and not KH._hudlist_loaded_scripts[RequiredScript] then
    KH._hudlist_loaded_scripts[RequiredScript] = true
    Hooks:PostHook(PlayerInventory, "_start_jammer_effect",
        "KyoHUD_HUDList_StartPocketECMJammer", function(inventory)
            start_pocket_ecm(inventory, "jamming")
        end)
    Hooks:PreHook(PlayerInventory, "_stop_jammer_effect",
        "KyoHUD_HUDList_StopPocketECMJammer", function(inventory)
            stop_pocket_ecm(inventory, "jamming")
        end)
    Hooks:PostHook(PlayerInventory, "_start_feedback_effect",
        "KyoHUD_HUDList_StartPocketECMFeedback", function(inventory)
            start_pocket_ecm(inventory, "feedback")
        end)
    Hooks:PreHook(PlayerInventory, "_stop_feedback_effect",
        "KyoHUD_HUDList_StopPocketECMFeedback", function(inventory)
            stop_pocket_ecm(inventory, "feedback")
        end)
end
