kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end

kyohud.hud = kyohud.hud or {}

local ACT = kyohud.hud.actors or {}
kyohud.hud.actors = ACT

ACT._store = ACT._store or {}
local _reg = ACT._store

ACT._mgr = ACT._mgr
ACT._local_unit = ACT._local_unit
ACT._local_unit_id = ACT._local_unit_id

local _slot_panels = ACT._slot_panels or {}
ACT._slot_panels = _slot_panels

local _unit_tokens = ACT._unit_tokens
if not _unit_tokens then
    _unit_tokens = setmetatable({}, {__mode = "k"})
    ACT._unit_tokens = _unit_tokens
end
local _next_unit_token = ACT._next_unit_token or 1

local REQUIRED_CONTEXT = "lib/managers/hudmanagerpd2"

local function finite(v)
    if type(v) ~= "number" then return false end
    if v ~= v then return false end
    if v == math.huge or v == -math.huge then return false end
    return true
end

local function capture_num(t, k)
    local v = t[k]
    if type(v) == "number" then return v end
    return nil
end

local function build_entry(cur, tot)
    local cur_ok = finite(cur)
    local tot_ok = finite(tot) and tot > 0
    local valid = cur_ok and tot_ok
    local ratio = nil
    if valid then
        ratio = cur / tot
        if ratio < 0 then ratio = 0.0 end
        if ratio > 1 then ratio = 1.0 end
    end
    return {current = cur, total = tot, ratio = ratio, valid = valid}
end

local function capture_bar(data)
    if type(data) ~= "table" then return nil end
    local cur = capture_num(data, "current")
    local tot = capture_num(data, "total")
    if cur == nil and tot == nil then return nil end
    return build_entry(cur, tot)
end

local function player_panel_slot()
    if type(HUDManager) == "table" then
        return HUDManager.PLAYER_PANEL
    end
    return nil
end

local function safe_get(fn)
    local ok, val = pcall(fn)
    if ok then return val end
    return nil
end

local function get_panel(mgr, i)
    if type(mgr) ~= "table" then return nil end
    if type(mgr._teammate_panels) ~= "table" then return nil end
    return mgr._teammate_panels[i]
end

local function resolve_provenance(panel)
    if type(panel) ~= "table" then return "unknown" end
    if panel._ai == true then return "bot" end
    if type(panel._peer_id) == "number" then return "network_quantized" end
    return "unknown"
end

local function read_panel_identity(panel)
    if type(panel) ~= "table" then return nil, false end
    local peer_id = nil
    if type(panel._peer_id) == "number" then peer_id = panel._peer_id end
    local ai = (panel._ai == true)
    return peer_id, ai
end

local function resolve_unit_token(unit)
    if not unit then return nil end
    local tok = _unit_tokens[unit]
    if tok then return tok end
    tok = _next_unit_token
    _next_unit_token = _next_unit_token + 1
    ACT._next_unit_token = _next_unit_token
    _unit_tokens[unit] = tok
    return tok
end

local function resolve_local_unit()
    local unit = safe_get(function()
        local pm = managers and managers.player
        if not pm then return nil end
        return pm:player_unit()
    end)
    if unit and alive(unit) then
        return unit
    end
    return nil
end

local function clear_slot_metrics(i)
    if _reg[i] then
        _reg[i].health = nil
        _reg[i].armor = nil
        _reg[i].revives = nil
        _reg[i].downs = nil
        _reg[i].condition_icon = nil
        _reg[i].condition_text = nil
        _reg[i]._condition_inferred = nil
    end
end

local function ensure_entry(i)
    if not _reg[i] then _reg[i] = {} end
    if not _reg[i].generation then _reg[i].generation = 0 end
    return _reg[i]
end

local function reconcile(mgr, i)
    if type(mgr) ~= "table" then return end

    if ACT._mgr ~= nil and ACT._mgr ~= mgr then
        for k in pairs(_reg) do _reg[k] = nil end
        for k in pairs(_slot_panels) do _slot_panels[k] = nil end
        ACT._local_unit = nil
        ACT._local_unit_id = nil
    end
    ACT._mgr = mgr

    if i ~= nil then
        local panel = get_panel(mgr, i)
        local new_peer, new_ai = read_panel_identity(panel)

        local entry = ensure_entry(i)
        local old_peer = entry.peer_id
        local old_ai = entry.ai

        local identity_changed = false
        if entry._identity_initialized then
            if old_peer ~= new_peer or old_ai ~= new_ai then
                identity_changed = true
            end
        end

        if identity_changed then
            clear_slot_metrics(i)
            entry.generation = (entry.generation or 0) + 1
        end

        entry.peer_id = new_peer
        entry.ai = new_ai
        entry.slot = i
        entry._identity_initialized = true

        if panel then
            _slot_panels[i] = panel
        end
    end
end

local function reconcile_unit_at_slot(i)
    local slot = player_panel_slot()
    if i ~= slot then return end
    local unit = resolve_local_unit()
    if not unit then
        if ACT._local_unit ~= nil then
            ACT._local_unit = nil
            ACT._local_unit_id = nil
            clear_slot_metrics(i)
            if _reg[i] then _reg[i].unit_id = nil end
        end
        return
    end
    if ACT._local_unit ~= unit then
        if ACT._local_unit ~= nil then
            clear_slot_metrics(i)
        end
        ACT._local_unit = unit
        ACT._local_unit_id = resolve_unit_token(unit)
        local entry = ensure_entry(i)
        entry.unit_id = ACT._local_unit_id
        entry.generation = (entry.generation or 0) + 1
    end
end

local function on_health(self, i, data)
    reconcile(self, i)
    reconcile_unit_at_slot(i)
    local panel = get_panel(self, i)
    local prov = resolve_provenance(panel)
    local entry = ensure_entry(i)
    local bar = capture_bar(data)
    if bar then
        bar.provenance = prov
        entry.health = bar
    else
        entry.health = nil
    end
end

local function on_armor(self, i, data)
    reconcile(self, i)
    reconcile_unit_at_slot(i)
    local panel = get_panel(self, i)
    local prov = resolve_provenance(panel)
    local entry = ensure_entry(i)
    local bar = capture_bar(data)
    if bar then
        bar.provenance = prov
        entry.armor = bar
    else
        entry.armor = nil
    end
end

local function on_revives(self, i, amount)
    reconcile(self, i)
    reconcile_unit_at_slot(i)
    if type(amount) ~= "number" then return end
    if not finite(amount) then return end
    local entry = ensure_entry(i)
    entry.revives = amount
    entry.downs = math.max(amount - 1, 0)
end

local function read_native_condition(panel)
    if type(panel) ~= "table" then return nil end
    local ok, visible = pcall(function()
        local icon = panel._condition_icon
        if not icon or not alive(icon) or type(icon.visible) ~= "function" then
            return nil
        end
        return icon:visible()
    end)
    if ok then return visible end
    return nil
end

local function on_condition(self, i, icon, text)
    reconcile(self, i)
    reconcile_unit_at_slot(i)
    local entry = ensure_entry(i)
    entry._condition_inferred = nil
    local ti = type(icon)
    if icon == nil or ti == "string" or ti == "number" or ti == "boolean" then
        entry.condition_icon = icon
    end
    local tt = type(text)
    if text == nil or tt == "string" or tt == "number" or tt == "boolean" then
        entry.condition_text = text
    end
end

function ACT:refresh(manager)
    if type(manager) ~= "table" then return end

    reconcile(manager, nil)

    local slot = player_panel_slot()
    if not slot then return end

    reconcile_unit_at_slot(slot)

    local unit = resolve_local_unit()
    if not unit then return end

    local entry = ensure_entry(slot)

    local panel = get_panel(manager, slot)
    local native_visible = read_native_condition(panel)

    if entry._condition_inferred == true then
        entry.condition_icon = nil
        entry.condition_text = nil
    end

    if entry.condition_icon == nil and entry.condition_text == nil and native_visible == false then
        entry.condition_icon = "mugshot_normal"
        entry.condition_text = ""
        entry._condition_inferred = true
    end

    local cd = safe_get(function() return unit:character_damage() end)
    if type(cd) ~= "table" then
        entry.health = nil
        entry.armor = nil
        entry.revives = nil
        entry.downs = nil
        return
    end

    local h = safe_get(function() return cd:get_real_health() end)
    local mh = safe_get(function() return cd:_max_health() end)
    if h ~= nil or mh ~= nil then
        entry.health = build_entry(h, mh)
        entry.health.provenance = "local"
    else
        entry.health = nil
    end

    local a = safe_get(function() return cd:get_real_armor() end)
    local ma = safe_get(function() return cd:_max_armor() end)
    if a ~= nil or ma ~= nil then
        entry.armor = build_entry(a, ma)
        entry.armor.provenance = "local"
    else
        entry.armor = nil
    end

    local r = safe_get(function() return cd:get_revives() end)
    if type(r) == "number" and finite(r) then
        entry.revives = r
        entry.downs = math.max(r - 1, 0)
    else
        entry.revives = nil
        entry.downs = nil
    end
end

function ACT:on_heist_start(manager)
    for k in pairs(_reg) do _reg[k] = nil end
    for k in pairs(_slot_panels) do _slot_panels[k] = nil end
    ACT._mgr = nil
    ACT._local_unit = nil
    ACT._local_unit_id = nil
end

function ACT:get_actor(slot)
    local r = _reg[slot]
    if not r then return nil end
    if not r.health and not r.armor and r.revives == nil and r.downs == nil
        and r.condition_icon == nil and r.condition_text == nil then
        return nil
    end
    local snap = {}
    if r.health then
        snap.health = {
            current = r.health.current,
            total = r.health.total,
            ratio = r.health.ratio,
            valid = r.health.valid,
            provenance = r.health.provenance,
        }
    end
    if r.armor then
        snap.armor = {
            current = r.armor.current,
            total = r.armor.total,
            ratio = r.armor.ratio,
            valid = r.armor.valid,
            provenance = r.armor.provenance,
        }
    end
    if r.revives ~= nil then snap.revives = r.revives end
    if r.downs ~= nil then snap.downs = r.downs end
    if r.condition_icon ~= nil then snap.condition_icon = r.condition_icon end
    if r.condition_text ~= nil then snap.condition_text = r.condition_text end
    if r.slot ~= nil then snap.slot = r.slot end
    if r.peer_id ~= nil then snap.peer_id = r.peer_id end
    snap.ai = (r.ai == true)
    if r.generation ~= nil then snap.generation = r.generation end
    if r.unit_id ~= nil then snap.unit_id = r.unit_id end
    return snap
end

local function on_remove_panel_pre(self, id)
    if _reg[id] then
        clear_slot_metrics(id)
    end
end

kyohud.hud._installed_hooks = kyohud.hud._installed_hooks or {}

local function safe_post(class, method, id, fn)
    if type(class) ~= "table" then return end
    if kyohud.hud._installed_hooks[id] then return end
    if type(class[method]) ~= "function" then return end
    Hooks:PostHook(class, method, id, fn)
    kyohud.hud._installed_hooks[id] = true
end

local function safe_pre(class, method, id, fn)
    if type(class) ~= "table" then return end
    if kyohud.hud._installed_hooks[id] then return end
    if type(class[method]) ~= "function" then return end
    Hooks:PreHook(class, method, id, fn)
    kyohud.hud._installed_hooks[id] = true
end

if RequiredScript == REQUIRED_CONTEXT then
    safe_post(HUDManager, "set_teammate_health", "KyohHUD_Actors_Health", on_health)
    safe_post(HUDManager, "set_teammate_armor", "KyohHUD_Actors_Armor", on_armor)
    safe_post(HUDManager, "set_teammate_revives", "KyohHUD_Actors_Revives", on_revives)
    safe_post(HUDManager, "set_teammate_condition", "KyohHUD_Actors_Condition", on_condition)
    safe_pre(HUDManager, "remove_teammate_panel", "KyohHUD_Actors_RemovePanel", on_remove_panel_pre)
end
