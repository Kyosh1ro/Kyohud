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

local _mgr_txn_depth = ACT._mgr_txn_depth
if not _mgr_txn_depth then
    _mgr_txn_depth = setmetatable({}, {__mode = "k"})
    ACT._mgr_txn_depth = _mgr_txn_depth
end

local _crew_entries = ACT._crew_entries or {}
ACT._crew_entries = _crew_entries
local _crew_identity_tokens = ACT._crew_identity_tokens or {}
ACT._crew_identity_tokens = _crew_identity_tokens
local _crew_next_token = ACT._crew_next_token or 1
local _crew_source_session = ACT._crew_source_session
local _crew_source_criminals = ACT._crew_source_criminals
local _crew_source_mgr = ACT._crew_source_mgr
local _crew_poll_deadline = ACT._crew_poll_deadline

local _crew_by_peer_id = ACT._crew_by_peer_id or {}
ACT._crew_by_peer_id = _crew_by_peer_id

local _slot_color_explicit = ACT._slot_color_explicit or {}
ACT._slot_color_explicit = _slot_color_explicit

local _pm_published = ACT._pm_published
if not _pm_published then
    _pm_published = {
        deployable = {},
        cable_ties = {},
        grenade = {},
        ammo = {},
    }
    ACT._pm_published = _pm_published
end

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

local function safe_invoke(obj, method_name, ...)
    if type(obj) ~= "table" and type(obj) ~= "userdata" then
        return nil, false
    end
    local method_lookup_ok, method = pcall(function()
        return obj[method_name]
    end)
    if not method_lookup_ok or type(method) ~= "function" then
        return nil, false
    end
    local args = {...}
    local nargs = select("#", ...)
    local ok, result = pcall(method, obj, unpack(args, 1, nargs))
    if ok then return result, true end
    return nil, false
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

local function snapshot_color(src)
    if type(src) ~= "table" and type(src) ~= "userdata" then
        return nil
    end
    local r = safe_get(function() return src.r end)
    local g = safe_get(function() return src.g end)
    local b = safe_get(function() return src.b end)
    if type(r) ~= "number" or not finite(r) or r < 0 or r > 1 then return nil end
    if type(g) ~= "number" or not finite(g) or g < 0 or g > 1 then return nil end
    if type(b) ~= "number" or not finite(b) or b < 0 or b > 1 then return nil end
    return {r = r, g = g, b = b, a = 1}
end

local function resolve_native_color(color_id)
    if not finite(color_id) then return nil end
    if color_id < 1 or color_id ~= math.floor(color_id) then return nil end
    local colors = safe_get(function()
        return tweak_data.chat_colors
    end)
    if type(colors) ~= "table" then return nil end
    local col = colors[color_id]
    if col == nil then
        col = colors[#colors]
    end
    if col == nil then return nil end
    return snapshot_color(col)
end

local function resolve_color_for_id(peer_id, is_ai)
    if is_ai then
        local mp = safe_get(function()
            return tweak_data.max_players
        end)
        if type(mp) == "number" and finite(mp) then
            return resolve_native_color(mp + 1)
        end
        return nil
    end
    if type(peer_id) == "number" then
        return resolve_native_color(peer_id)
    end
    return nil
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

local function resolve_local_peer_id()
    local peer_id = safe_get(function()
        if type(managers) ~= "table" or type(managers.network) ~= "table" then
            return nil
        end
        local session = managers.network:session()
        if type(session) ~= "table" then return nil end
        local peer = session:local_peer()
        if type(peer) ~= "table" then return nil end
        return peer:id()
    end)
    if type(peer_id) == "number" then return peer_id end
    return nil
end

local function collect_equipped_weapon(unit)
    local unit_alive = safe_get(function()
        return alive(unit)
    end)
    if not unit_alive then return nil end

    local inventory = safe_invoke(unit, "inventory")
    if type(inventory) ~= "table" and type(inventory) ~= "userdata" then
        return nil
    end

    local equipped_selection = safe_invoke(inventory, "equipped_selection")
    if type(equipped_selection) ~= "number" then return nil end
    if equipped_selection ~= 1 and equipped_selection ~= 2 then return nil end

    local equipped_unit = safe_invoke(inventory, "equipped_unit")
    if not equipped_unit then return nil end
    local eq_alive = safe_get(function()
        return alive(equipped_unit)
    end)
    if not eq_alive then return nil end

    local unit_by_sel = safe_invoke(inventory, "unit_by_selection", equipped_selection)
    if unit_by_sel ~= equipped_unit then return nil end

    local base = safe_invoke(equipped_unit, "base")
    if type(base) ~= "table" and type(base) ~= "userdata" then
        return nil
    end

    local weapon_id = safe_invoke(base, "get_name_id")
    if type(weapon_id) ~= "string" then return nil end

    local name_id = nil
    local wtd = safe_invoke(base, "weapon_tweak_data")
    if type(wtd) == "table" then
        local wtd_name = wtd.name_id
        if type(wtd_name) == "string" then
            name_id = wtd_name
        end
    end

    local weapon_unit_id = resolve_unit_token(equipped_unit)

    return {
        selection_index = equipped_selection,
        weapon_id = weapon_id,
        name_id = name_id,
        unit_id = weapon_unit_id,
        _unit = equipped_unit,
    }
end

local function _snapshot_equality(a, b)
    if a == b then return true end
    if type(a) ~= "table" or type(b) ~= "table" then return false end
    for k, v in pairs(a) do
        if b[k] ~= v then return false end
    end
    for k, _ in pairs(b) do
        if a[k] == nil then return false end
    end
    return true
end

local function _snapshot_shallow(t)
    if type(t) ~= "table" then return t end
    local copy = {}
    for k, v in pairs(t) do
        copy[k] = v
    end
    return copy
end

local function _resolve_pm_context(channel)
    local session = safe_get(function()
        if type(managers) ~= "table" or type(managers.network) ~= "table" then
            return nil
        end
        return managers.network:session()
    end)
    local pm = safe_get(function()
        if type(managers) ~= "table" then return nil end
        return managers.player
    end)
    local registry_source = nil
    if type(pm) == "table" or type(pm) == "userdata" then
        if channel == "deployable" then
            registry_source = safe_get(function() return pm._global and pm._global.synced_deployables end)
        elseif channel == "cable_ties" then
            registry_source = safe_get(function() return pm._global and pm._global.synced_cable_ties end)
        elseif channel == "grenade" then
            registry_source = safe_get(function() return pm._global and pm._global.synced_grenades end)
        elseif channel == "ammo" then
            registry_source = safe_get(function() return pm._global and pm._global.synced_ammo_info end)
        end
    end
    return session, pm, registry_source
end

local function _qualify_pm_publication(channel, peer_id, peer_obj, current_data, certified)
    if type(peer_id) ~= "number" then return false end
    if current_data == nil then return false end
    local session, pm, registry_source = _resolve_pm_context(channel)
    local tracker = _pm_published[channel]
    if not tracker then return false end
    local slot_key = peer_id
    local prev = tracker[slot_key]
    local data_snapshot = _snapshot_shallow(current_data)
    if not prev then
        tracker[slot_key] = {
            session = session,
            peer_obj = peer_obj,
            pm = pm,
            registry_source = registry_source,
            data = data_snapshot,
            record = current_data,
        }
        return true
    end
    if certified then
        prev.session = session
        prev.peer_obj = peer_obj
        prev.pm = pm
        prev.registry_source = registry_source
        prev.data = data_snapshot
        prev.record = current_data
        return true
    end
    if prev.session ~= session then return false end
    if prev.pm ~= pm then return false end
    if prev.registry_source ~= registry_source then return false end
    if prev.peer_obj ~= peer_obj then
        if prev.record == current_data then
            return false
        end
        prev.session = session
        prev.peer_obj = peer_obj
        prev.pm = pm
        prev.registry_source = registry_source
        prev.data = data_snapshot
        prev.record = current_data
        return true
    end
    prev.data = data_snapshot
    prev.record = current_data
    return true
end

local function _clear_pm_published_for_peer(peer_id)
    if type(peer_id) ~= "number" then return end
    for _, channel in pairs({"deployable", "cable_ties", "grenade", "ammo"}) do
        local tracker = _pm_published[channel]
        if tracker then
            local keys_to_clear = {}
            for k, v in pairs(tracker) do
                if type(k) == "number" and k == peer_id then
                    keys_to_clear[#keys_to_clear + 1] = k
                elseif type(v) == "table" and v.peer_id == peer_id then
                    keys_to_clear[#keys_to_clear + 1] = k
                end
            end
            for _, k in ipairs(keys_to_clear) do
                tracker[k] = nil
            end
        end
    end
end

local function collect_human_ammo(peer_id, selection_index, ammo_unknown, peer_obj, certified)
    if ammo_unknown then return nil end
    if type(peer_id) ~= "number" then return nil end
    if type(selection_index) ~= "number" then return nil end

    local pm = safe_get(function()
        if type(managers) ~= "table" then return nil end
        return managers.player
    end)
    if type(pm) ~= "table" and type(pm) ~= "userdata" then return nil end

    local synced = safe_invoke(pm, "get_synced_ammo_info", peer_id)
    if type(synced) ~= "table" then return nil end

    local sel_data = synced[selection_index]
    if type(sel_data) ~= "table" then return nil end

    if peer_obj ~= nil then
        if not _qualify_pm_publication("ammo", peer_id * 1000 + selection_index, peer_obj, sel_data, certified) then
            return nil
        end
    end

    local max_clip = capture_num(sel_data, 1)
    if max_clip ~= nil and (not finite(max_clip) or max_clip < 0) then
        max_clip = nil
    end

    local current_clip = capture_num(sel_data, 2)
    if current_clip ~= nil and (not finite(current_clip) or current_clip < 0) then
        current_clip = nil
    end

    local total_raw = capture_num(sel_data, 3)
    if total_raw ~= nil and (not finite(total_raw) or total_raw < 0) then
        total_raw = nil
    end

    local max_total = capture_num(sel_data, 4)
    if max_total ~= nil and (not finite(max_total) or max_total < 0) then
        max_total = nil
    end

    local reserve = nil
    if current_clip ~= nil and total_raw ~= nil then
        local diff = total_raw - current_clip
        if diff > 0 then
            reserve = diff
        else
            reserve = 0
        end
    end

    return {
        max_clip = max_clip,
        current_clip = current_clip,
        total_raw = total_raw,
        max = max_total,
        reserve = reserve,
        provenance = "network_synced",
    }
end

local function digest_to_number(value)
    if type(value) == "number" then
        if finite(value) then return value end
        return nil
    end
    local app = safe_get(function() return Application end)
    if not app then return nil end
    local result, called = safe_invoke(app, "digest_value", value, false)
    if not called then return nil end
    if type(result) == "number" and finite(result) then return result end
    return nil
end

local function resolve_deployable_name_id(dep_id)
    if type(dep_id) ~= "string" or dep_id == "" then return nil end
    local eq_td = safe_get(function()
        if type(tweak_data) ~= "table" then return nil end
        return tweak_data.equipments
    end)
    if type(eq_td) ~= "table" then return nil end
    local entry = eq_td[dep_id]
    if type(entry) ~= "table" then return nil end
    local text_id = entry.text_id
    if type(text_id) == "string" then return text_id end
    return nil
end

local function resolve_projectile_meta(gren_id)
    if type(gren_id) ~= "string" or gren_id == "" then return nil end
    local proj = safe_get(function()
        if type(tweak_data) ~= "table" then return nil end
        if type(tweak_data.blackmarket) ~= "table" then return nil end
        return tweak_data.blackmarket.projectiles
    end)
    if type(proj) ~= "table" then return nil end
    local entry = proj[gren_id]
    if type(entry) ~= "table" then return nil end
    local name_id = nil
    if type(entry.name_id) == "string" then name_id = entry.name_id end
    local kind = nil
    local ability = entry.ability
    if ability == true then
        kind = "ability"
    elseif type(ability) == "string" and ability ~= "" then
        kind = "ability"
    elseif entry.throwable == true or entry.is_a_grenade == true then
        kind = "throwable"
    end
    return {name_id = name_id, kind = kind}
end

local function collect_human_equipment(peer_id, peer_obj, certified)
    if type(peer_id) ~= "number" then return nil end
    local pm = safe_get(function()
        if type(managers) ~= "table" then return nil end
        return managers.player
    end)
    if type(pm) ~= "table" and type(pm) ~= "userdata" then return nil end

    local result = nil

    local dep_data, dep_ok = safe_invoke(pm, "get_synced_deployable_equipment", peer_id)
    if dep_ok and type(dep_data) == "table" then
        local dep_qualified = true
        if peer_obj ~= nil then
            dep_qualified = _qualify_pm_publication("deployable", peer_id, peer_obj, dep_data, certified == "deployable")
        end
        if dep_qualified then
            local dep_id = nil
            if type(dep_data.deployable) == "string" and dep_data.deployable ~= "" then
                dep_id = dep_data.deployable
            end
            local amt_num = nil
            local raw_amt = dep_data.amount
            if finite(raw_amt) and raw_amt >= 0 then
                amt_num = raw_amt
            end
            if dep_id and amt_num ~= nil then
                local name_id = resolve_deployable_name_id(dep_id)
                result = result or {}
                result.deployable = {id = dep_id, amount = amt_num, name_id = name_id}
            end
        end
    end

    local cable_data, cable_ok = safe_invoke(pm, "get_synced_cable_ties", peer_id)
    if cable_ok and type(cable_data) == "table" then
        local cable_qualified = true
        if peer_obj ~= nil then
            cable_qualified = _qualify_pm_publication("cable_ties", peer_id, peer_obj, cable_data, certified == "cable_ties")
        end
        if cable_qualified then
            local raw_amt = cable_data.amount
            if finite(raw_amt) then
                if raw_amt >= 0 or raw_amt == -1 then
                    result = result or {}
                    result.cable_ties = {amount = raw_amt}
                end
            end
        end
    end

    local gren_data, gren_ok = safe_invoke(pm, "get_synced_grenades", peer_id)
    if gren_ok and type(gren_data) == "table" then
        local gren_qualified = true
        if peer_obj ~= nil then
            gren_qualified = _qualify_pm_publication("grenade", peer_id, peer_obj, gren_data, certified == "grenade")
        end
        if gren_qualified then
            local gren_id = nil
            if type(gren_data.grenade) == "string" and gren_data.grenade ~= "" then
                gren_id = gren_data.grenade
            end
            local amt_num = nil
            local digested = digest_to_number(gren_data.amount)
            if digested ~= nil and finite(digested) and digested >= 0 then
                amt_num = digested
            end
            if gren_id and amt_num ~= nil then
                local meta = resolve_projectile_meta(gren_id)
                local name_id = nil
                local kind = nil
                if meta then
                    name_id = meta.name_id
                    kind = meta.kind
                end
                result = result or {}
                result.projectile = {id = gren_id, amount = amt_num, name_id = name_id, kind = kind}
            end
        end
    end

    return result
end

local function _is_panel_local(self, i)
    local local_unit = resolve_local_unit()
    if not local_unit then return false end
    local pp = player_panel_slot()
    if type(pp) ~= "number" or i ~= pp then return false end
    local panel = get_panel(self, i)
    if type(panel) ~= "table" then return false end
    if panel._ai == true then return false end
    local panel_peer = panel._peer_id
    if panel_peer == nil then
        return true
    end
    if type(panel_peer) == "number" then
        local local_peer_id = resolve_local_peer_id()
        if type(local_peer_id) == "number" and panel_peer == local_peer_id then
            return true
        end
        return false
    end
    return false
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
        _reg[i].interaction = nil
    end
    _slot_color_explicit[i] = nil
end

local function _invalidate_crew_slot_metrics(s)
    local pp = player_panel_slot()
    if s == pp then
        local r = _reg[s]
        if r and r.health and r.health.provenance == "local" then
            return
        end
    end
    clear_slot_metrics(s)
    if _reg[s] then
        _reg[s].generation = (_reg[s].generation or 0) + 1
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
        for k in pairs(_slot_color_explicit) do _slot_color_explicit[k] = nil end
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
    local depth = _mgr_txn_depth[self] or 0
    if depth > 0 and not _is_panel_local(self, i) then
        clear_slot_metrics(i)
        return
    end
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
    local depth = _mgr_txn_depth[self] or 0
    if depth > 0 and not _is_panel_local(self, i) then
        clear_slot_metrics(i)
        return
    end
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
    local depth = _mgr_txn_depth[self] or 0
    if depth > 0 and not _is_panel_local(self, i) then
        clear_slot_metrics(i)
        return
    end
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
    local depth = _mgr_txn_depth[self] or 0
    if depth > 0 and not _is_panel_local(self, i) then
        clear_slot_metrics(i)
        return
    end
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

local function _reset_crew_roster()
    for k in pairs(_crew_entries) do _crew_entries[k] = nil end
    for k in pairs(_crew_identity_tokens) do _crew_identity_tokens[k] = nil end
    for k in pairs(_crew_by_peer_id) do _crew_by_peer_id[k] = nil end
    _crew_source_session = nil
    ACT._crew_source_session = nil
    _crew_source_criminals = nil
    ACT._crew_source_criminals = nil
    _crew_source_mgr = nil
    ACT._crew_source_mgr = nil
end

local function _crew_resolve_token(identity_key)
    local tok = _crew_identity_tokens[identity_key]
    if tok then return tok end
    tok = _crew_next_token
    _crew_next_token = _crew_next_token + 1
    ACT._crew_next_token = _crew_next_token
    _crew_identity_tokens[identity_key] = tok
    return tok
end

local function _refresh_crew_roster(manager)
    local session = safe_get(function()
        if type(managers) ~= "table" or type(managers.network) ~= "table" then
            return nil
        end
        return managers.network:session()
    end)
    local criminals = safe_get(function()
        if type(managers) ~= "table" or type(managers.criminals) ~= "table" then
            return nil
        end
        return managers.criminals
    end)

    local source_changed = (_crew_source_session ~= session)
        or (_crew_source_criminals ~= criminals)
        or (_crew_source_mgr ~= manager)

    if source_changed then
        for k in pairs(_crew_identity_tokens) do _crew_identity_tokens[k] = nil end
        for k in pairs(_crew_by_peer_id) do _crew_by_peer_id[k] = nil end
        _crew_source_session = session
        ACT._crew_source_session = session
        _crew_source_criminals = criminals
        ACT._crew_source_criminals = criminals
        _crew_source_mgr = manager
        ACT._crew_source_mgr = manager
    end

    local prev_entries = {}
    for k, v in pairs(_crew_entries) do
        prev_entries[k] = v
    end

    if source_changed then
        for _, prev in pairs(prev_entries) do
            local s = prev.slot
            if type(s) == "number" then
                _invalidate_crew_slot_metrics(s)
            end
        end
    end

    local function abort_roster_qualify()
        if source_changed then return end
        for k in pairs(_crew_identity_tokens) do _crew_identity_tokens[k] = nil end
        for k in pairs(_crew_by_peer_id) do _crew_by_peer_id[k] = nil end
        for _, prev in pairs(prev_entries) do
            local s = prev.slot
            if type(s) == "number" then
                _invalidate_crew_slot_metrics(s)
            end
        end
    end

    for k in pairs(_crew_entries) do _crew_entries[k] = nil end
    for k in pairs(_crew_by_peer_id) do _crew_by_peer_id[k] = nil end

    if type(session) ~= "table" or type(criminals) ~= "table" then
        abort_roster_qualify()
        return
    end

    local local_peer = safe_get(function()
        return session:local_peer()
    end)
    local local_peer_id = nil
    if type(local_peer) == "table" then
        local_peer_id = safe_get(function()
            return local_peer:id()
        end)
    end

    if type(local_peer) ~= "table" or type(local_peer_id) ~= "number" then
        abort_roster_qualify()
        return
    end

    local characters = safe_get(function()
        return criminals:characters()
    end)
    if type(characters) ~= "table" then
        abort_roster_qualify()
        return
    end

    local candidates = {}
    local n = #characters
    for i = 1, n do
        local rec = characters[i]
        if type(rec) == "table" and rec.taken == true and type(rec.name) == "string" then
            local peer_id = rec.peer_id
            local data = rec.data
            local is_ai = false
            local slot = nil
            if type(data) == "table" then
                is_ai = (data.ai == true)
                local pid = data.panel_id
                if finite(pid) and pid >= 1 and pid <= 4 and pid == math.floor(pid) then
                    slot = pid
                end
            end

            local is_local = false
            if type(peer_id) == "number" and peer_id == local_peer_id then
                is_local = true
            end

            if not is_local and slot then
                local identity_key
                local peer_obj = nil
                if is_ai then
                    identity_key = "b" .. tostring(rec.name)
                else
                    if type(peer_id) == "number" then
                        local peer = safe_get(function()
                            return session:peer(peer_id)
                        end)
                        if type(peer) == "table" then
                            identity_key = peer
                            peer_obj = peer
                        end
                    end
                end

                if identity_key ~= nil then
                    local candidate_peer_id = peer_id
                    if is_ai then
                        candidate_peer_id = nil
                    end
                    table.insert(candidates, {
                        rec = rec,
                        slot = slot,
                        identity_key = identity_key,
                        is_ai = is_ai,
                        peer_id = candidate_peer_id,
                        _peer_obj = peer_obj,
                    })
                end
            end
        end
    end

    local current_by_slot = {}
    for _, c in ipairs(candidates) do
        current_by_slot[c.slot] = c
    end

    if not source_changed then
        for _, prev in pairs(prev_entries) do
            local s = prev.slot
            if type(s) == "number" then
                local cur = current_by_slot[s]
            if not cur or cur.identity_key ~= prev._identity_key then
                _invalidate_crew_slot_metrics(s)
            else
                    local live_token = nil
                    if cur.rec and cur.rec.unit then
                        local unit_alive = safe_get(function()
                            return alive(cur.rec.unit)
                        end)
                        if unit_alive then
                            live_token = resolve_unit_token(cur.rec.unit)
                        end
                    end
                    if live_token ~= prev.unit_id then
                        _invalidate_crew_slot_metrics(s)
                    end
                end
            end
        end
    end

    table.sort(candidates, function(a, b) return a.slot < b.slot end)

    local current_keys = {}
    local current_peer_ids = {}
    for _, c in ipairs(candidates) do
        current_keys[c.identity_key] = true
        if type(c.peer_id) == "number" then
            current_peer_ids[c.peer_id] = true
        end
    end

    for k in pairs(_crew_identity_tokens) do
        if not current_keys[k] then
            _crew_identity_tokens[k] = nil
        end
    end

    -- Keep the last publication's owner across departure. A retained PM record
    -- is not a bootstrap publication for the next occupant of the same peer ID.
    -- These bounded peer/selection records are cleared on heist reset.

    local prev_pos_by_key = {}
    for _, entry in pairs(prev_entries) do
        if entry._identity_key ~= nil then
            prev_pos_by_key[entry._identity_key] = entry.position
        end
    end

    local used_positions = {}
    local new_occupants = {}

    for _, c in ipairs(candidates) do
        local prev_pos = prev_pos_by_key[c.identity_key]
        if prev_pos ~= nil then
            c.position = prev_pos
            used_positions[prev_pos] = true
        else
            table.insert(new_occupants, c)
        end
    end

    local free_positions = {}
    for pos = 1, 3 do
        if not used_positions[pos] then
            table.insert(free_positions, pos)
        end
    end

    for i, c in ipairs(new_occupants) do
        if i <= #free_positions then
            c.position = free_positions[i]
        end
    end

    for _, c in ipairs(candidates) do
        if c.position then
            local token = _crew_resolve_token(c.identity_key)

            local entry = {
                occupant_token = token,
                position = c.position,
                slot = c.slot,
                character_name = c.rec.name,
                peer_id = c.peer_id,
                ai = c.is_ai,
                _identity_key = c.identity_key,
                _unit = c.rec.unit,
            }

            if not c.is_ai then
                local peer = safe_get(function()
                    return session:peer(c.rec.peer_id)
                end)
                if type(peer) == "table" then
                    local n_val = safe_get(function()
                        return peer:name()
                    end)
                    if n_val ~= nil then entry.name = n_val end
                    local lvl = safe_get(function()
                        return peer:level()
                    end)
                    if type(lvl) == "number" and finite(lvl) and lvl >= 0 and lvl == math.floor(lvl) then
                        entry.level = lvl
                    end
                    local rnk = safe_get(function()
                        return peer:rank()
                    end)
                    if type(rnk) == "number" and finite(rnk) and rnk >= 0 and rnk == math.floor(rnk) then
                        entry.rank = rnk
                    end
                end
            else
                local loc_name = safe_get(function()
                    if type(managers) ~= "table"
                        or type(managers.localization) ~= "table" then
                        return nil
                    end
                    return managers.localization:text("menu_" .. c.rec.name)
                end)
                entry.name = loc_name or c.rec.name

                local unit = c.rec.unit
                local unit_alive = safe_get(function()
                    return alive(unit)
                end)
                if unit_alive then
                    local cd = safe_get(function()
                        if type(unit.character_damage) ~= "function" then
                            return nil
                        end
                        return unit:character_damage()
                    end)
                    if type(cd) == "table" then
                        local dead_ok = true
                        local dead_val = nil
                        if type(cd.dead) == "function" then
                            local ok, val = pcall(function() return cd:dead() end)
                            if ok then
                                dead_val = val
                            else
                                dead_ok = false
                            end
                        else
                            dead_ok = false
                        end

                        local fatal_ok = true
                        local fatal_val = nil
                        if type(cd.fatal) == "function" then
                            local ok, val = pcall(function() return cd:fatal() end)
                            if ok then
                                fatal_val = val
                            else
                                fatal_ok = false
                            end
                        else
                            fatal_ok = false
                        end

                        local bleed_ok = true
                        local bleed_val = nil
                        if type(cd.bleed_out) == "function" then
                            local ok, val = pcall(function() return cd:bleed_out() end)
                            if ok then
                                bleed_val = val
                            else
                                bleed_ok = false
                            end
                        else
                            bleed_ok = false
                        end

                        local arrest_ok = true
                        local arrest_val = nil
                        if type(cd.arrested) == "function" then
                            local ok, val = pcall(function() return cd:arrested() end)
                            if ok then
                                arrest_val = val
                            else
                                arrest_ok = false
                            end
                        else
                            arrest_ok = false
                        end

                        local phase = nil
                        if dead_val then
                            phase = "dead"
                        elseif fatal_val then
                            phase = "fatal"
                        elseif bleed_val then
                            phase = "bleedout"
                        elseif arrest_val ~= nil then
                            phase = "arrested"
                        elseif dead_ok and fatal_ok and bleed_ok and arrest_ok then
                            phase = "normal"
                        end

                        if phase then
                            entry.phase = phase

                            local is_host = safe_get(function()
                                if Network == nil then return false end
                                if type(Network.is_server) ~= "function" then return false end
                                return Network:is_server() == true
                            end)

                            if is_host and (phase == "normal" or phase == "bleedout") then
                                local ratio_ok = true
                                local ratio_val = nil
                                if type(cd.health_ratio) == "function" then
                                    local ok, val = pcall(function() return cd:health_ratio() end)
                                    if ok then
                                        ratio_val = val
                                    else
                                        ratio_ok = false
                                    end
                                else
                                    ratio_ok = false
                                end

                                if ratio_ok and type(ratio_val) == "number" and finite(ratio_val) and ratio_val >= 0 then
                                    local clamped = ratio_val
                                    if clamped > 1 then clamped = 1.0 end
                                    local bar = {
                                        ratio = clamped,
                                        valid = true,
                                        provenance = "bot_host",
                                    }
                                    if phase == "normal" then
                                        entry.health = bar
                                    else
                                        entry.bleedout = bar
                                    end
                                end
                            end
                        end
                    end
                end
            end

            if not c.is_ai and type(c.peer_id) == "number" then
                entry.equipment = collect_human_equipment(c.peer_id, c._peer_obj, false)
            end

            if c.rec.unit then
                local unit_alive = safe_get(function()
                    return alive(c.rec.unit)
                end)
                if unit_alive then
                    entry.unit_id = resolve_unit_token(c.rec.unit)

                    local weapon_data = collect_equipped_weapon(c.rec.unit)
                    if weapon_data then
                        local turret_hidden = false
                        local turret_unknown = false
                        if not c.is_ai and type(c.peer_id) == "number" then
                            local pm = safe_get(function()
                                if type(managers) ~= "table" then return nil end
                                return managers.player
                            end)
                            if type(pm) == "table" or type(pm) == "userdata" then
                                local turret, getter_ok = safe_invoke(pm, "get_player_turret_for_peer", c.peer_id)
                                if getter_ok then
                                    if turret then
                                        local alive_ok, turret_alive = pcall(function()
                                            return alive(turret)
                                        end)
                                        if not alive_ok then
                                            turret_unknown = true
                                        elseif turret_alive then
                                            turret_hidden = true
                                        end
                                    end
                                else
                                    turret_unknown = true
                                end
                            else
                                turret_unknown = true
                            end
                        end

                        if not turret_hidden then
                            local ammo_data = nil
                            if not c.is_ai and type(c.peer_id) == "number" then
                                ammo_data = collect_human_ammo(c.peer_id, weapon_data.selection_index, turret_unknown, c._peer_obj, false)
                            end

                            entry.weapon = {
                                selection_index = weapon_data.selection_index,
                                weapon_id = weapon_data.weapon_id,
                                name_id = weapon_data.name_id,
                                unit_id = weapon_data.unit_id,
                                ammo = ammo_data,
                                _weapon_unit = weapon_data._unit,
                            }
                        end
                    end
                end
            end

            local default_color = resolve_color_for_id(c.peer_id, c.is_ai)
            if default_color then
                entry.default_color = default_color
            end

            _crew_entries[c.position] = entry
        end
    end

    for k in pairs(_crew_by_peer_id) do _crew_by_peer_id[k] = nil end
    for pos = 1, 3 do
        local e = _crew_entries[pos]
        if e and type(e.peer_id) == "number" then
            _crew_by_peer_id[e.peer_id] = pos
        end
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

function ACT:refresh_crew(manager, t)
    if type(manager) ~= "table" then return end
    if not finite(t) then return end
    local depth = _mgr_txn_depth[manager] or 0
    if depth > 0 then return end
    if _crew_poll_deadline and t < _crew_poll_deadline then return end
    _refresh_crew_roster(manager)
    _crew_poll_deadline = t + 0.5
    ACT._crew_poll_deadline = _crew_poll_deadline
end

function ACT:on_heist_start(manager)
    if type(manager) == "table" then
        _mgr_txn_depth[manager] = nil
    end
    for k in pairs(_reg) do _reg[k] = nil end
    for k in pairs(_slot_panels) do _slot_panels[k] = nil end
    for k in pairs(_slot_color_explicit) do _slot_color_explicit[k] = nil end
    for _, channel in pairs({"deployable", "cable_ties", "grenade", "ammo"}) do
        local tracker = _pm_published[channel]
        if tracker then
            for k in pairs(tracker) do tracker[k] = nil end
        end
    end
    ACT._mgr = nil
    ACT._local_unit = nil
    ACT._local_unit_id = nil
    _reset_crew_roster()
    _crew_poll_deadline = nil
    ACT._crew_poll_deadline = nil
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

local function crew_owner_current(src)
    local session = safe_get(function() return managers.network:session() end)
    if session ~= ACT._crew_source_session then return false end
    if safe_get(function() return managers.criminals end) ~= ACT._crew_source_criminals then return false end
    if safe_get(function() return managers.hud end) ~= ACT._crew_source_mgr then return false end
    if not src.ai then
        return safe_invoke(session, "peer", src.peer_id) == src._identity_key
    end
    return true
end

function ACT:get_crew_snapshot()
    local snap = {}
    for i = 1, 3 do
        local src = _crew_entries[i]
        if src and crew_owner_current(src) then
            local copy = {
                occupant_token = src.occupant_token,
                position = src.position,
                slot = src.slot,
                character_name = src.character_name,
                peer_id = src.peer_id,
                ai = src.ai,
            }
            if src.name ~= nil then copy.name = src.name end
            if src.level ~= nil then copy.level = src.level end
            if src.rank ~= nil then copy.rank = src.rank end
            if src.unit_id ~= nil then copy.unit_id = src.unit_id end

            if src.weapon then
                local w = src.weapon
                local weapon_copy = {
                    selection_index = w.selection_index,
                    weapon_id = w.weapon_id,
                    name_id = w.name_id,
                    unit_id = w.unit_id,
                }
                if w.ammo then
                    local a = w.ammo
                    weapon_copy.ammo = {
                        max_clip = a.max_clip,
                        current_clip = a.current_clip,
                        total_raw = a.total_raw,
                        max = a.max,
                        reserve = a.reserve,
                        provenance = a.provenance,
                    }
                end
                copy.weapon = weapon_copy
            end

            if src.equipment then
                local eq = src.equipment
                local eq_copy = {}
                if eq.deployable then
                    eq_copy.deployable = {
                        id = eq.deployable.id,
                        amount = eq.deployable.amount,
                        name_id = eq.deployable.name_id,
                    }
                end
                if eq.cable_ties then
                    eq_copy.cable_ties = {
                        amount = eq.cable_ties.amount,
                    }
                end
                if eq.projectile then
                    eq_copy.projectile = {
                        id = eq.projectile.id,
                        amount = eq.projectile.amount,
                        name_id = eq.projectile.name_id,
                        kind = eq.projectile.kind,
                    }
                end
                copy.equipment = eq_copy
            end

            local color_to_export = nil
            local s = src.slot
            if type(s) == "number" then
                local explicit = _slot_color_explicit[s]
                local reg_entry = _reg[s]
                if explicit and reg_entry
                    and explicit.manager == _crew_source_mgr
                    and explicit.panel == _slot_panels[s]
                    and explicit.peer_id == src.peer_id
                    and explicit.ai == src.ai
                    and explicit.generation == reg_entry.generation then
                    color_to_export = explicit.color
                end
            end
            if not color_to_export then
                color_to_export = src.default_color
            end
            if color_to_export then
                copy.color = {
                    r = color_to_export.r,
                    g = color_to_export.g,
                    b = color_to_export.b,
                    a = color_to_export.a,
                }
            end

            if src.ai == false then
                local s = src.slot
                if type(s) == "number" then
                    local r = _reg[s]
                    if r and r.peer_id == src.peer_id and r.ai == false then
                        local h_net = r.health and r.health.provenance == "network_quantized"
                        local a_net = r.armor and r.armor.provenance == "network_quantized"
                        if h_net then
                            copy.health = {
                                current = r.health.current,
                                total = r.health.total,
                                ratio = r.health.ratio,
                                valid = r.health.valid,
                                provenance = r.health.provenance,
                            }
                        end
                        if a_net then
                            copy.armor = {
                                current = r.armor.current,
                                total = r.armor.total,
                                ratio = r.armor.ratio,
                                valid = r.armor.valid,
                                provenance = r.armor.provenance,
                            }
                        end
                        if r.revives ~= nil then copy.revives = r.revives end
                        if r.downs ~= nil then copy.downs = r.downs end
                        if r.condition_icon ~= nil then copy.condition_icon = r.condition_icon end
                        if r.condition_text ~= nil then copy.condition_text = r.condition_text end
                        if r.interaction then
                            local int = r.interaction
                            copy.interaction = {
                                type_index = int.type_index,
                                tweak_data_id = int.tweak_data_id,
                                enabled = int.enabled,
                                duration = int.duration,
                                started_t = int.started_t,
                                success = int.success,
                            }
                        end
                    end
                end
            else
                if src.phase ~= nil then copy.phase = src.phase end
                if src.health then
                    copy.health = {
                        ratio = src.health.ratio,
                        valid = src.health.valid,
                        provenance = src.health.provenance,
                    }
                end
                if src.bleedout then
                    copy.bleedout = {
                        ratio = src.bleedout.ratio,
                        valid = src.bleedout.valid,
                        provenance = src.bleedout.provenance,
                    }
                end
            end

            snap[#snap + 1] = copy
        end
    end
    return snap
end

local function on_remove_panel_pre(self, id)
    local depth = _mgr_txn_depth[self] or 0
    _mgr_txn_depth[self] = depth + 1
    if _reg[id] then
        clear_slot_metrics(id)
    end
end

local function on_add_panel_pre(self, id)
    local depth = _mgr_txn_depth[self] or 0
    _mgr_txn_depth[self] = depth + 1
end

local function on_add_panel_post(self, id)
    local depth = _mgr_txn_depth[self] or 0
    if depth > 0 then
        depth = depth - 1
        _mgr_txn_depth[self] = depth
    end
    if depth == 0 then
        _crew_poll_deadline = nil
        ACT._crew_poll_deadline = nil
    end
end

local function on_remove_panel_post(self, id)
    local depth = _mgr_txn_depth[self] or 0
    if depth > 0 then
        depth = depth - 1
        _mgr_txn_depth[self] = depth
    end
    if depth == 0 then
        _crew_poll_deadline = nil
        ACT._crew_poll_deadline = nil
    end
end

local function on_set_callsign_post(self, i, id)
    reconcile(self, i)
    local depth = _mgr_txn_depth[self] or 0
    if depth > 0 then return end
    if not finite(id) then return end
    local panel = get_panel(self, i)
    local peer_id, ai = read_panel_identity(panel)
    if ai then peer_id = nil end
    local entry = ensure_entry(i)
    local col = resolve_native_color(id)
    if col then
        _slot_color_explicit[i] = {
            color = col,
            peer_id = peer_id,
            ai = ai,
            generation = entry.generation,
            manager = self,
            panel = panel,
        }
    else
        _slot_color_explicit[i] = nil
    end
end

local function on_progress(self, peer_id, type_index, enabled, tweak_data_id, timer, success)
    if type(peer_id) ~= "number" then return end
    if not finite(peer_id) then return end
    if peer_id < 1 or peer_id ~= math.floor(peer_id) then return end

    local local_peer_id = resolve_local_peer_id()
    if type(local_peer_id) == "number" and peer_id == local_peer_id then return end

    local criminals = safe_get(function()
        if type(managers) ~= "table" or type(managers.criminals) ~= "table" then
            return nil
        end
        return managers.criminals
    end)
    if type(criminals) ~= "table" and type(criminals) ~= "userdata" then return end

    local char_data = safe_get(function()
        return criminals:character_data_by_peer_id(peer_id)
    end)
    if type(char_data) ~= "table" then return end
    if char_data.ai == true then return end

    local slot = char_data.panel_id
    if not finite(slot) then return end
    if slot < 1 or slot > 4 then return end
    if slot ~= math.floor(slot) then return end

    local panel = get_panel(self, slot)
    if type(panel) ~= "table" then return end
    if panel._ai == true then return end
    if panel._peer_id ~= peer_id then return end

    local depth = _mgr_txn_depth[self] or 0
    if depth > 0 then return end

    if type(type_index) ~= "number" then return end
    if not finite(type_index) then return end
    if type_index ~= 1 and type_index ~= 2 and type_index ~= 3 then return end

    if type(tweak_data_id) ~= "string" then return end
    if type(enabled) ~= "boolean" then return end

    local duration = nil
    if type(timer) == "number" and finite(timer) and timer >= 0 then
        duration = timer
    end

    local now = nil
    local gt = safe_invoke(TimerManager, "game")
    if type(gt) == "table" or type(gt) == "userdata" then
        local t = safe_invoke(gt, "time")
        if type(t) == "number" and finite(t) then
            now = t
        end
    end

    local success_val = nil
    if type(success) == "boolean" then
        success_val = success
    end

    reconcile(self, slot)

    local entry = ensure_entry(slot)
    local int = entry.interaction
    if type(int) ~= "table" then
        int = {}
        entry.interaction = int
    end
    int.type_index = type_index
    int.tweak_data_id = tweak_data_id
    int.enabled = enabled
    int.duration = duration
    int.success = success_val
    if enabled == true then
        int.started_t = nil
        if type(now) == "number" and finite(now) then
            int.started_t = now
        end
    end
end

local REQUIRED_CONTEXT_PM = "lib/managers/playermanager"

local function _pm_verify_context(peer_obj)
    if peer_obj == nil then return false end
    local pm = safe_get(function()
        if type(managers) ~= "table" then return nil end
        return managers.player
    end)
    if type(pm) ~= "table" and type(pm) ~= "userdata" then return false end
    if peer_obj ~= nil then
        local peer_in_session = safe_get(function()
            if type(managers) ~= "table" or type(managers.network) ~= "table" then
                return false
            end
            local session = managers.network:session()
            if type(session) ~= "table" then return false end
            local peer_id = safe_get(function() return peer_obj:id() end)
            if type(peer_id) ~= "number" then return false end
            local session_peer = session:peer(peer_id)
            return session_peer == peer_obj
        end)
        if not peer_in_session then return false end
    end
    return true
end

local function _pm_check_turret(peer_id)
    local pm = safe_get(function()
        if type(managers) ~= "table" then return nil end
        return managers.player
    end)
    if type(pm) ~= "table" and type(pm) ~= "userdata" then
        return false, true
    end
    local turret, getter_ok = safe_invoke(pm, "get_player_turret_for_peer", peer_id)
    if getter_ok then
        if turret then
            local alive_ok, turret_alive = pcall(function()
                return alive(turret)
            end)
            if not alive_ok then
                return false, true
            elseif turret_alive then
                return true, false
            end
        end
        return false, false
    end
    return false, true
end

local function _pm_resolve_peer_obj(peer_id)
    if type(peer_id) ~= "number" then return nil end
    return safe_get(function()
        if type(managers) ~= "table" or type(managers.network) ~= "table" then
            return nil
        end
        local session = managers.network:session()
        if type(session) ~= "table" then return nil end
        return session:peer(peer_id)
    end)
end

local function _pm_update_crew_equipment(peer_id, peer_obj, certified)
    local position = _crew_by_peer_id[peer_id]
    if not position then return end
    local entry = _crew_entries[position]
    if not entry then return end
    local equipment = collect_human_equipment(peer_id, peer_obj, certified)
    if entry._identity_key == peer_obj and crew_owner_current(entry) then entry.equipment = equipment end
end

local function _pm_update_crew_ammo(peer_id, selection_index, peer_obj, certified)
    local position = _crew_by_peer_id[peer_id]
    if not position then return end
    local entry = _crew_entries[position]
    if not entry then return end
    if not entry.weapon or entry.weapon.selection_index ~= selection_index then return end
    local turret_hidden, turret_unknown = _pm_check_turret(peer_id)
    if turret_hidden then entry.weapon = nil; return end
    local ammo_data = collect_human_ammo(peer_id, selection_index, turret_unknown, peer_obj, certified)
    entry.weapon.ammo = ammo_data
end

local function on_crew_weapon_selected(self, slot, selection_index)
    if (_mgr_txn_depth[self] or 0) > 0 then return end
    if selection_index ~= 1 and selection_index ~= 2 then return end
    for _, entry in pairs(_crew_entries) do
        if entry.slot == slot and crew_owner_current(entry) then
            local weapon = collect_equipped_weapon(entry._unit)
            if weapon and weapon.selection_index == selection_index then
                local hidden, unknown = false, false
                if not entry.ai then hidden, unknown = _pm_check_turret(entry.peer_id) end
                if not hidden then
                    weapon.ammo = not entry.ai and collect_human_ammo(entry.peer_id, selection_index, unknown, entry._identity_key) or nil
                    entry.weapon = weapon
                else entry.weapon = nil end
            else entry.weapon = nil end
            return
        end
    end
end

local function on_pm_synced_deployable_equipment(self, peer, deployable, amount)
    local mgr = ACT._mgr
    if mgr then
        local depth = _mgr_txn_depth[mgr] or 0
        if depth > 0 then return end
    end
    local pm = safe_get(function()
        if type(managers) ~= "table" then return nil end
        return managers.player
    end)
    if self ~= pm then return end
    local peer_id = nil
    if type(peer) == "table" or type(peer) == "userdata" then
        peer_id = safe_get(function() return peer:id() end)
    end
    if type(peer_id) ~= "number" then return end
    local peer_obj = peer
    if not _pm_verify_context(peer_obj) then return end
    _pm_update_crew_equipment(peer_id, peer_obj, "deployable")
end

local function on_pm_synced_ammo_info(self, peer_id, selection_index, max_clip, current_clip, current_left, max)
    local mgr = ACT._mgr
    if mgr then
        local depth = _mgr_txn_depth[mgr] or 0
        if depth > 0 then return end
    end
    local pm = safe_get(function()
        if type(managers) ~= "table" then return nil end
        return managers.player
    end)
    if self ~= pm then return end
    if type(peer_id) ~= "number" then return end
    if type(selection_index) ~= "number" then return end
    local peer_obj = _pm_resolve_peer_obj(peer_id)
    if not _pm_verify_context(peer_obj) then return end
    _pm_update_crew_ammo(peer_id, selection_index, peer_obj, true)
end

local function on_pm_synced_cable_ties(self, peer_id, ...)
    local mgr = ACT._mgr
    if mgr then
        local depth = _mgr_txn_depth[mgr] or 0
        if depth > 0 then return end
    end
    local pm = safe_get(function()
        if type(managers) ~= "table" then return nil end
        return managers.player
    end)
    if self ~= pm then return end
    if type(peer_id) ~= "number" then return end
    local peer_obj = _pm_resolve_peer_obj(peer_id)
    if not _pm_verify_context(peer_obj) then return end
    _pm_update_crew_equipment(peer_id, peer_obj, "cable_ties")
end

local function on_pm_synced_grenades(self, ...)
    local mgr = ACT._mgr
    if mgr then
        local depth = _mgr_txn_depth[mgr] or 0
        if depth > 0 then return end
    end
    local pm = safe_get(function()
        if type(managers) ~= "table" then return nil end
        return managers.player
    end)
    if self ~= pm then return end
    local args = {...}
    if #args < 1 then return end
    local peer_id = args[1]
    if type(peer_id) ~= "number" then return end
    local peer_obj = _pm_resolve_peer_obj(peer_id)
    if not _pm_verify_context(peer_obj) then return end
    _pm_update_crew_equipment(peer_id, peer_obj, "grenade")
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
    safe_pre(HUDManager, "add_teammate_panel", "KyohHUD_Actors_AddPanel_Pre", on_add_panel_pre)
    safe_post(HUDManager, "add_teammate_panel", "KyohHUD_Actors_AddPanel_Post", on_add_panel_post)
    safe_post(HUDManager, "set_teammate_health", "KyohHUD_Actors_Health", on_health)
    safe_post(HUDManager, "set_teammate_armor", "KyohHUD_Actors_Armor", on_armor)
    safe_post(HUDManager, "set_teammate_revives", "KyohHUD_Actors_Revives", on_revives)
    safe_post(HUDManager, "set_teammate_condition", "KyohHUD_Actors_Condition", on_condition)
    safe_post(HUDManager, "set_teammate_callsign", "KyohHUD_Actors_Callsign", on_set_callsign_post)
    safe_post(HUDManager, "teammate_progress", "KyohHUD_Actors_Progress", on_progress)
    safe_post(HUDManager, "_set_teammate_weapon_selected", "KyohHUD_Actors_WeaponSelected", on_crew_weapon_selected)
    safe_pre(HUDManager, "remove_teammate_panel", "KyohHUD_Actors_RemovePanel", on_remove_panel_pre)
    safe_post(HUDManager, "remove_teammate_panel", "KyohHUD_Actors_RemovePanel_Post", on_remove_panel_post)
end

if RequiredScript == REQUIRED_CONTEXT_PM then
    local PlayerManager = PlayerManager
    if type(PlayerManager) ~= "table" and type(managers) == "table" and type(managers.player) == "table" then
        PlayerManager = getmetatable(managers.player)
    end
    if type(PlayerManager) == "table" then
        safe_post(PlayerManager, "set_synced_deployable_equipment", "KyohHUD_Actors_PM_Deployable", on_pm_synced_deployable_equipment)
        safe_post(PlayerManager, "set_synced_ammo_info", "KyohHUD_Actors_PM_Ammo", on_pm_synced_ammo_info)
        safe_post(PlayerManager, "set_synced_cable_ties", "KyohHUD_Actors_PM_CableTies", on_pm_synced_cable_ties)
        safe_post(PlayerManager, "set_synced_grenades", "KyohHUD_Actors_PM_Grenades", on_pm_synced_grenades)
    end
end
