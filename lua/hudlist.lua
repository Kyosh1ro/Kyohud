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

local function finite_number(value)
    value = tonumber(value)
    if not value or value ~= value or value == math.huge or value == -math.huge then
        return nil
    end
    return value
end

local function current_time()
    local ok, value = pcall(function()
        return Application:time()
    end)
    return ok and finite_number(value) or 0
end

function Provider:get_buffs()
    return self._buffs
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
end

function Provider:get_team_source_count(id)
    local count = 0
    for _ in pairs(self._team_sources[id] or {}) do
        count = count + 1
    end
    return count
end

local function team_source_key(peer, category, upgrade)
    return tostring(peer) .. ":" .. category .. ":" .. upgrade
end

function Provider:activate_team_source(peer, category, upgrade, level, value)
    if type(category) ~= "string" or type(upgrade) ~= "string" then return false end
    peer = finite_number(peer)
    level = finite_number(level)
    if not peer or peer < 0 or peer % 1 ~= 0 or not level or level % 1 ~= 0 then
        return false
    end
    local id = Catalog:resolve_team(category, upgrade, level)
    if not id then return false end

    local sources = self._team_sources[id] or {}
    self._team_sources[id] = sources
    sources[team_source_key(peer, category, upgrade)] = {
        peer = peer,
        category = category,
        upgrade = upgrade,
        level = level,
        value = finite_number(value),
    }
    self:event("buff", "activate", id, {
        peer = peer,
        category = category,
        upgrade = upgrade,
        level = level,
        value = finite_number(value),
    })
    self._buffs[id].team_sources = sources
    return true
end

function Provider:deactivate_team_source(peer, category, upgrade, level)
    peer = finite_number(peer)
    level = finite_number(level)
    local id = peer and level and Catalog:resolve_team(category, upgrade, level)
    local sources = id and self._team_sources[id]
    if not sources then return false end

    sources[team_source_key(peer, category, upgrade)] = nil
    if next(sources) then return true end
    self._team_sources[id] = nil
    self:event("buff", "deactivate", id, {
        peer = peer,
        category = category,
        upgrade = upgrade,
        level = level,
    })
    return true
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
    local expired = {}
    for id, entry in pairs(self._buffs) do
        if entry.expire_t and entry.expire_t <= t then
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
        entry.value = data.value
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
        entry.value = data.value
    end
    if event == "activate" then
        entry.category = data.category
        entry.upgrade = data.upgrade
        entry.level = data.level
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

KH._hudlist_loaded_scripts = KH._hudlist_loaded_scripts or {}
if RequiredScript == "lib/managers/playermanager"
        and not KH._hudlist_loaded_scripts[RequiredScript] then
    KH._hudlist_loaded_scripts[RequiredScript] = true

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
            local peers = ok and manager._global and manager._global.synced_team_upgrades
            for category, upgrades in pairs(peers and peers[peer_id] or {}) do
                for upgrade, level in pairs(upgrades) do
                    Provider:deactivate_team_source(peer_id, category, upgrade, level)
                end
            end
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
end
