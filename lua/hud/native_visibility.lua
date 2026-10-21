kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end

kyohud.hud = kyohud.hud or {}

local NV = {}
NV.__index = NV

function NV:new(whitelist)
    local inst = setmetatable({}, NV)
    inst._whitelist = whitelist or {}
    inst._entries = {}
    return inst
end

function NV:_is_allowed(obj, property)
    if property ~= "visible" and property ~= "alpha" then return false end
    local wl = self._whitelist[obj]
    if not wl then return false end
    return wl[property] == true
end

local function is_finite(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    return true
end

local function is_valid_value(property, value)
    if property == "visible" then
        return value == true or value == false
    end
    if property == "alpha" then
        return is_finite(value)
    end
    return false
end

local function is_obj_alive(obj)
    if type(alive) == "function" then
        local ok, a = pcall(alive, obj)
        if ok then return a == true end
    end
    return true
end

local function safe_lookup(obj, key)
    local ok_fn, fn = pcall(function() return obj[key] end)
    if not ok_fn then return nil, true end
    return fn, false
end

function NV:_read_value(obj, property)
    local ok, val
    if property == "visible" then
        local fn, lookup_err = safe_lookup(obj, "visible")
        if lookup_err then return nil, true end
        if type(fn) ~= "function" then return nil, false end
        ok, val = pcall(fn, obj)
        if not ok then return nil, true end
        if val ~= true and val ~= false then return nil, false end
        return val, false
    end
    if property == "alpha" then
        local fn, lookup_err = safe_lookup(obj, "alpha")
        if lookup_err then return nil, true end
        if type(fn) ~= "function" then return nil, false end
        ok, val = pcall(fn, obj)
        if not ok then return nil, true end
        if not is_finite(val) then return nil, false end
        return val, false
    end
    return nil, false
end

function NV:_write_value(obj, property, value)
    local setter_key
    if property == "visible" then
        setter_key = "set_visible"
    elseif property == "alpha" then
        setter_key = "set_alpha"
    else
        return false
    end
    local fn, lookup_err = safe_lookup(obj, setter_key)
    if lookup_err then return false end
    if type(fn) ~= "function" then return false end
    local ok, result = pcall(fn, obj, value)
    if not ok then return false end
    if result == false then return false end
    return true
end

function NV:_find_entry(object, property)
    for i, e in ipairs(self._entries) do
        if e.object == object and e.property == property then
            return i, e
        end
    end
    return nil
end

function NV:_restore_one(entry)
    local obj = entry.object

    if not is_obj_alive(obj) then return true end

    local current, getter_errored = self:_read_value(obj, entry.property)
    if getter_errored then return false end
    if current == nil then return false end

    if current == entry.old_value then return true end

    if current ~= entry.applied_value then return true end

    if entry.old_value == nil then return true end

    local written = self:_write_value(obj, entry.property, entry.old_value)
    if not written then return false end

    local readback, rb_err = self:_read_value(obj, entry.property)
    if rb_err then return false end
    if readback == nil then return false end
    if readback == entry.old_value then return true end
    if readback == entry.applied_value then return false end
    return true
end

function NV:_rollback_applied(applied)
    local restored_set = {}
    for i = #applied, 1, -1 do
        local a = applied[i]
        if self:_restore_one(a) then
            restored_set[a] = true
        end
    end
    if next(restored_set) then
        local kept = {}
        for _, e in ipairs(self._entries) do
            if not restored_set[e] then
                table.insert(kept, e)
            end
        end
        self._entries = kept
    end
end

function NV:_restore_old_generations(owner, new_generation)
    local kept = {}
    local failed = {}
    for _, e in ipairs(self._entries) do
        if e.owner == owner and e.generation ~= new_generation then
            if not self:_restore_one(e) then
                table.insert(failed, e)
            end
        else
            table.insert(kept, e)
        end
    end
    for _, f in ipairs(failed) do
        table.insert(kept, f)
    end
    self._entries = kept
    return #failed == 0
end

local function make_record(obj, prop, old, applied, owner, generation)
    return {
        object = obj, property = prop,
        old_value = old,
        applied_value = applied,
        owner = owner, generation = generation,
    }
end

function NV:acquire(owner, generation, requests)
    if type(requests) ~= "table" then return false end

    local batch_map = {}
    for _, req in ipairs(requests) do
        if type(req) ~= "table" then return false end
        local obj = req.id
        local prop = req.property
        local val = req.value
        if not self:_is_allowed(obj, prop) then return false end
        if not is_valid_value(prop, val) then return false end
        if not is_obj_alive(obj) then return false end

        local obj_map = batch_map[obj]
        if not obj_map then
            obj_map = {}
            batch_map[obj] = obj_map
        end
        if obj_map[prop] ~= nil and obj_map[prop] ~= val then
            return false
        end
        obj_map[prop] = val

        local _, existing = self:_find_entry(obj, prop)
        if existing then
            if existing.owner ~= owner then return false end
            if existing.generation == generation and existing.applied_value ~= val then
                return false
            end
        end
    end

    if not self:_restore_old_generations(owner, generation) then
        return false
    end

    local applied = {}
    for _, req in ipairs(requests) do
        local obj = req.id
        local prop = req.property
        local val = req.value

        local _, existing = self:_find_entry(obj, prop)
        if existing and existing.owner == owner and existing.generation == generation then
            if existing.applied_value == val then
                local actual, ae = self:_read_value(obj, prop)
                if not ae and actual == val then
                    goto continue
                end
            end
            self:_rollback_applied(applied)
            return false
        end

        local old, getter_err = self:_read_value(obj, prop)
        if getter_err or old == nil then
            self:_rollback_applied(applied)
            return false
        end

        local record = make_record(obj, prop, old, val, owner, generation)

        local written = self:_write_value(obj, prop, val)
        if written then
            local readback, rb_err = self:_read_value(obj, prop)
            if not rb_err and readback == val then
                table.insert(applied, record)
                table.insert(self._entries, record)
            elseif not rb_err and readback == old then
                self:_rollback_applied(applied)
                return false
            else
                table.insert(self._entries, record)
                self:_rollback_applied(applied)
                return false
            end
        else
            local post, post_err = self:_read_value(obj, prop)
            if post_err or post == nil or post ~= old then
                table.insert(self._entries, record)
            end
            self:_rollback_applied(applied)
            return false
        end
        ::continue::
    end
    return true
end

function NV:release(owner, generation)
    local kept = {}
    for _, e in ipairs(self._entries) do
        if e.owner == owner and e.generation == generation then
            if not self:_restore_one(e) then
                table.insert(kept, e)
            end
        else
            table.insert(kept, e)
        end
    end
    self._entries = kept
end

function NV:release_all()
    local kept = {}
    for _, e in ipairs(self._entries) do
        if not self:_restore_one(e) then
            table.insert(kept, e)
        end
    end
    self._entries = kept
end

kyohud.hud.native_visibility = kyohud.hud.native_visibility or NV:new({})
