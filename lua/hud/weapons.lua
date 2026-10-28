-- weapons.lua — KyoHUD two-slot weapons snapshot via refresh/get_snapshot
-- Local two-slot snapshot manager for weapons inventory state.

if not kyohud then kyohud = Kyosh1roHUD or {} end
Kyosh1roHUD = kyohud

kyohud.hud = kyohud.hud or {}

local weapons = kyohud.hud.weapons or {}
kyohud.hud.weapons = weapons

local function sanitize_number(value)
    if type(value) ~= "number" then return nil end
    if value ~= value then return nil end
    if value == math.huge or value == -math.huge then return nil end
    if value < 0 then return nil end
    return value
end

local function safe_method(obj, name, ...)
    local t = type(obj)
    if t ~= "table" and t ~= "userdata" then return false end
    local ok_fn, fn = pcall(function() return obj[name] end)
    if not ok_fn or type(fn) ~= "function" then return false end
    local ok, r1, r2, r3, r4 = pcall(fn, obj, ...)
    if not ok then return false end
    return true, r1, r2, r3, r4
end

local function check_alive(unit)
    if unit == nil then return false end
    local ok, result = pcall(alive, unit)
    if not ok then return false end
    return result
end

local function get_weapon_base(unit)
    if not check_alive(unit) then return nil end
    local ok, base = safe_method(unit, "base")
    if not ok or not base then return nil end
    return base
end

local function get_ammo_info(base)
    if not base then return nil end
    local ok, max_clip, current_clip, total, maximum = safe_method(base, "ammo_info")
    if not ok then return nil end
    return {
        max_clip = sanitize_number(max_clip),
        current_clip = sanitize_number(current_clip),
        total_raw = sanitize_number(total),
        max_total = sanitize_number(maximum),
    }
end

local function get_fire_mode(base)
    if not base then return nil end
    local ok, mode = safe_method(base, "fire_mode")
    if not ok then return nil end
    return mode
end

local function get_alt_fire_info(base)
    if not base then return nil, false end
    local ok, alt = safe_method(base, "alt_fire_active")
    if not ok then return nil, false end
    if alt == nil then return false, true end
    if type(alt) ~= "boolean" then return nil, false end
    return alt, true
end

local function get_ammo_base_ref(base)
    if not base then return nil end
    local ok, ab = safe_method(base, "ammo_base")
    if not ok or not ab then return nil end
    return ab
end

local function normalize_fire_mode(raw_mode)
    if type(raw_mode) ~= "string" then return "--" end
    local mode = raw_mode:lower()
    if mode == "single" or mode == "auto" or mode == "burst" or mode == "volley" then
        return mode
    end
    return "--"
end

local function compute_reserve(total_raw, current_clip)
    if total_raw == nil or current_clip == nil then return nil end
    local diff = total_raw - current_clip
    if diff < 0 then return 0 end
    return diff
end

local function refs_equal(a, b)
    if not a or not b then return false end
    return a.manager == b.manager
        and a.player == b.player
        and a.inventory == b.inventory
        and a.unit1 == b.unit1
        and a.unit2 == b.unit2
        and a.ab1 == b.ab1
        and a.ab2 == b.ab2
end

local function snapshot_slot(slot_data)
    if not slot_data or not slot_data.unit then
        return {present = false}
    end

    local unit = slot_data.unit
    if not check_alive(unit) then
        return {present = false}
    end

    local base = get_weapon_base(unit)
    if not base then
        return {present = false}
    end

    local ammo = get_ammo_info(base)
    local fire_mode_raw = get_fire_mode(base)
    local alt_fire, alt_known = get_alt_fire_info(base)
    local name_ok, weapon_id = safe_method(base, "get_name_id")
    local tweak_ok, data = safe_method(base, "weapon_tweak_data")
    local name_id = tweak_ok and type(data) == "table" and data.name_id or nil
    if type(name_id) ~= "string" then name_id = nil end
    if not name_ok or type(weapon_id) ~= "string" then weapon_id = nil end
    if type(fire_mode_raw) ~= "string" then fire_mode_raw = nil end

    local fire_mode = normalize_fire_mode(fire_mode_raw)

    local reserve = nil
    local coherent = true
    if ammo then
        reserve = compute_reserve(ammo.total_raw, ammo.current_clip)
        if ammo.total_raw ~= nil and ammo.current_clip ~= nil then
            coherent = ammo.total_raw >= ammo.current_clip
        end
    end

    return {
        present = true,
        weapon_id = weapon_id,
        name_id = name_id,
        current_clip = ammo and ammo.current_clip or nil,
        total_raw = ammo and ammo.total_raw or nil,
        max_clip = ammo and ammo.max_clip or nil,
        max_total = ammo and ammo.max_total or nil,
        reserve = reserve,
        coherent = coherent,
        fire_mode = fire_mode,
        fire_mode_raw = fire_mode_raw,
        alt_fire = alt_fire,
        alt_known = alt_known,
    }
end

local function get_player_unit()
    local ok, player_unit = pcall(function()
        return managers.player and managers.player:player_unit()
    end)
    if not ok or not player_unit then return nil end
    if not check_alive(player_unit) then return nil end
    return player_unit
end

local function get_inventory(player_unit)
    if not check_alive(player_unit) then return nil end
    local ok, inventory = safe_method(player_unit, "inventory")
    if not ok or not inventory then return nil end
    return inventory
end

local function get_current_state()
    local ok, state = pcall(function()
        return managers.player and managers.player:current_state()
    end)
    if not ok or not state then return nil end
    if type(state) == "table" then
        return state.name
    end
    return state
end

local function is_supported_state(state_name)
    if type(state_name) ~= "string" then return true end
    if state_name == "turret" then return false end
    return true
end

local function clear_state()
    weapons._current_snapshot = nil
    weapons._identity_refs = nil
end

local function collect_identity(player_unit, inventory, selections, manager)
    local units = {}
    local ammo_bases = {}
    for i = 1, 2 do
        local sd = selections[i]
        if sd and sd.unit and check_alive(sd.unit) then
            units[i] = sd.unit
            local b = get_weapon_base(sd.unit)
            if b then
                ammo_bases[i] = get_ammo_base_ref(b)
            end
        end
    end
    return {
        manager = manager,
        player = player_unit,
        inventory = inventory,
        unit1 = units[1],
        unit2 = units[2],
        ab1 = ammo_bases[1],
        ab2 = ammo_bases[2],
    }
end

local function build_snapshot(inventory)
    local ok, selections = safe_method(inventory, "available_selections")
    if not ok or type(selections) ~= "table" then
        return nil
    end

    local ok2, equipped_sel = safe_method(inventory, "equipped_selection")
    if not ok2 or type(equipped_sel) ~= "number" then
        equipped_sel = nil
    end

    local ok3, equipped_unit = safe_method(inventory, "equipped_unit")
    if not ok3 then
        equipped_unit = nil
    end

    if equipped_sel ~= 1 and equipped_sel ~= 2 then
        equipped_sel = nil
    end

    if not equipped_unit or not check_alive(equipped_unit) then
        equipped_sel = nil
    elseif equipped_sel then
        local sd = selections[equipped_sel]
        if not sd or sd.unit ~= equipped_unit then
            equipped_sel = nil
        end
    end

    local slots = {}
    for i = 1, 2 do
        local sd = selections[i]
        slots[i] = snapshot_slot(sd)
    end

    return {
        selected = equipped_sel,
        slots = slots,
    }
end

function weapons:refresh(manager)
    if manager ~= managers.hud then return end

    local player_unit = get_player_unit()
    if not player_unit then
        clear_state()
        return
    end

    local state_name = get_current_state()
    if not is_supported_state(state_name) then
        clear_state()
        return
    end

    local inventory = get_inventory(player_unit)
    if not inventory then
        clear_state()
        return
    end

    local ok_peek, selections_peek = safe_method(inventory, "available_selections")
    if not ok_peek or type(selections_peek) ~= "table" then
        clear_state()
        return
    end

    local new_refs = collect_identity(player_unit, inventory, selections_peek, manager)

    weapons._source_generation = weapons._source_generation or 0

    local identity_changed = not refs_equal(new_refs, weapons._identity_refs)

    local snapshot = build_snapshot(inventory)
    if not snapshot then
        clear_state()
        return
    end

    if identity_changed then
        weapons._source_generation = weapons._source_generation + 1
    end
    snapshot.source_generation = weapons._source_generation
    weapons._identity_refs = new_refs
    weapons._current_snapshot = snapshot
end

function weapons:get_snapshot()
    if not weapons._current_snapshot then
        return nil
    end

    local src = weapons._current_snapshot
    local detached_slots = {}
    for i = 1, 2 do
        local slot = src.slots[i]
        if slot then
            detached_slots[i] = {
                present = slot.present,
                weapon_id = slot.weapon_id,
                name_id = slot.name_id,
                current_clip = slot.current_clip,
                total_raw = slot.total_raw,
                max_clip = slot.max_clip,
                max_total = slot.max_total,
                reserve = slot.reserve,
                coherent = slot.coherent,
                fire_mode = slot.fire_mode,
                fire_mode_raw = slot.fire_mode_raw,
                alt_fire = slot.alt_fire,
                alt_known = slot.alt_known,
            }
        else
            detached_slots[i] = {present = false}
        end
    end

    return {
        selected = src.selected,
        slots = detached_slots,
        source_generation = src.source_generation,
    }
end

kyohud.hud._installed_hooks = kyohud.hud._installed_hooks or {}

local function install_hook(key, class, method, tag, fn)
    if kyohud.hud._installed_hooks[key] then return end
    local ct = type(class)
    if ct ~= "table" and ct ~= "userdata" then return end
    local ok_fn, fnv = pcall(function() return class[method] end)
    if not ok_fn or type(fnv) ~= "function" then return end
    Hooks:PostHook(class, method, tag, fn)
    kyohud.hud._installed_hooks[key] = true
end

local function try_refresh()
    local w = kyohud.hud.weapons
    if not w or type(w.refresh) ~= "function" then return end
    if not managers or not managers.hud then return end
    w:refresh(managers.hud)
end

local function is_player_panel(id)
    if not HUDManager then return false end
    local ok, pp = pcall(function() return HUDManager.PLAYER_PANEL end)
    if not ok then return false end
    return id == pp
end

local function hud_hook(method, key)
    install_hook(key, HUDManager, method, "kh_weapons_hud_" .. method, function(self, id, selection_index, ...)
        if self ~= managers.hud then return end
        if not is_player_panel(id) then return end
        if selection_index ~= 1 and selection_index ~= 2 then return end
        try_refresh()
    end)
end

if RequiredScript == "lib/managers/hudmanagerpd2" then
    hud_hook("set_teammate_ammo_amount", "weapons_set_teammate_ammo_amount")
    hud_hook("_set_teammate_weapon_selected", "weapons_set_teammate_weapon_selected")
    hud_hook("set_teammate_weapon_firemode", "weapons_set_teammate_weapon_firemode")
end

local function inv_hook(method, key)
    local ok_cls, cls = pcall(function() return PlayerInventory end)
    if not ok_cls or not cls then return end
    install_hook(key, cls, method, "kh_weapons_inv_" .. method, function(self, ...)
        local ok_check, is_live = pcall(function()
            if not managers or not managers.player then return false end
            local pu = managers.player:player_unit()
            if not pu then return false end
            if not alive(pu) then return false end
            return self._unit == pu and pu:inventory() == self
        end)
        if not ok_check or not is_live then return end
        try_refresh()
    end)
end

if RequiredScript == "lib/units/beings/player/playerinventory" then
    inv_hook("add_unit", "weapons_add_unit")
    inv_hook("equip_selection", "weapons_equip_selection")
    inv_hook("unequip_selection", "weapons_unequip_selection")
    inv_hook("remove_selection", "weapons_remove_selection")
end

-- Presentation lifecycle --------------------------------------------------

local WROOT = "kyohud_weapons_panel"
local CNAMES = {"weapon_card1", "weapon_card2"}
local RW, RH = 360, 120
local UI = 0.05
local LKEYS = {"ky_hud_weapon_secondary", "ky_hud_weapon_primary"}
local MKEYS = {single="ky_hud_weapon_single", auto="ky_hud_weapon_auto", burst="ky_hud_weapon_burst", volley="ky_hud_weapon_volley"}
local AKEY = "ky_hud_weapon_alt"
local FALLBACKS = {
    ky_hud_weapon_secondary = "SECONDARY", ky_hud_weapon_primary = "PRIMARY",
    ky_hud_weapon_single = "SINGLE", ky_hud_weapon_auto = "AUTO",
    ky_hud_weapon_burst = "BURST", ky_hud_weapon_volley = "VOLLEY", ky_hud_weapon_alt = "ALT"
}

local function near(a, b)
    return type(a) == "number" and a == a and math.abs(a - b) <= 0.5
end

local function loc(k)
    local ok, l = pcall(function() return managers.localization end)
    if not ok or not l then return FALLBACKS[k] or k end
    local ok2, r = pcall(function() return l:text(k) end)
    return (ok2 and type(r)=="string" and r~="" and r~=k) and r or FALLBACKS[k] or k
end

local function btexts()
    local t = {}
    for _, k in ipairs(LKEYS) do t[k] = loc(k) end
    for m, k in pairs(MKEYS) do t[m] = loc(k) end
    t.alt = loc(AKEY)
    return t
end

function weapons:mount(manager)
    if kyohud.settings.enable_hud_foundation ~= true then return end
    if kyohud.settings.enable_weapons ~= true then return end
    if _G.IS_VR == true then return end
    local mgr = manager or self._manager
    if not mgr or mgr ~= managers.hud then return end
    self._manager = mgr
    local rt = kyohud.hud.runtime
    if not rt or not rt._mounted then return end
    local parent = rt._root_panel
    if not parent or not check_alive(parent) then return end
    if self._mounted and self._root and check_alive(self._root) and self._parent == parent then return end
    if self._root and not check_alive(self._root) then self._root = nil; self._cards = nil end
    local cs, ex = pcall(function() return parent:child(WROOT) end)
    if not cs then return end
    if cs and ex and check_alive(ex) then
        if self._root == ex then self._parent = parent; self._mounted = true; return end
        return
    end
    local wc = kyohud.hud.weapon_component
    if type(wc) ~= "table" or type(wc.new) ~= "function" then self._cards = nil; return end
    local rs, root = pcall(function() return parent:panel({name=WROOT}) end)
    if not rs or not root then return end
    self._root = root; self._parent = parent; self._mounted = true
    local cards = {}
    for i = 1, 2 do
        local c = wc.new(root, CNAMES[i])
        if not c then
            self._cards = cards
            self:unmount()
            return
        end
        cards[i] = c
    end
    self._cards = cards
    self._texts = btexts()
    self:refresh(mgr)
    self:_apply()
    self:_render()
end

function weapons:unmount()
    if self._cards then
        for i = 1, #self._cards do if self._cards[i] then self._cards[i]:destroy() end end
        self._cards = nil
    end
    if self._root and check_alive(self._root) and self._parent and check_alive(self._parent) then
        pcall(function() self._parent:remove(self._root) end)
    end
    self._root = nil; self._parent = nil; self._mounted = false; self._layout_cache = nil
    self._last_poll = nil
    self._last_mount_attempt = nil
    self._wua = 0
end

function weapons:_geom()
    if not self._parent or not check_alive(self._parent) then return nil end
    local wok, pw = safe_method(self._parent, "w")
    local hok, ph = safe_method(self._parent, "h")
    if not wok or not hok then return nil end
    if type(pw) ~= "number" or type(ph) ~= "number" or pw <= 0 or ph <= 0 then return nil end
    local L = kyohud.hud.layout
    if not L or type(L.resolve) ~= "function" then return nil end
    local g = L.resolve(pw, ph, kyohud.settings.hud_scale or 1)
    if not g or not g.valid then return nil end
    local us, s = g.uniform_scale or 1, g.scale or 1
    local eff = us * s
    if eff < 0.35 then return nil end
    local w, h = RW * eff, RH * eff
    if w > (g.available_x or 0) or h > (g.available_y or 0) then return nil end
    local x = pw - (g.margin_x or 0) - w
    -- Reserve the accepted player block (200 bottom + 120 scaled height),
    -- including its horizontal safe margin, with a 12-unit separation.
    local y = ph - (g.margin_x or 0) - (200 + 120 * s + 12) * us - h
    if x < (g.margin_x or 0) or y < (g.margin_y or 0) or x+w > pw or y+h > ph then return nil end
    return {x=x, y=y, w=w, h=h, ch=h/2}
end

function weapons:_apply()
    if not self._root or not check_alive(self._root) then return end
    local g = self:_geom()
    if not g then self._layout_cache = nil; return end
    local _, x = safe_method(self._root, "x")
    local _, y = safe_method(self._root, "y")
    local _, w = safe_method(self._root, "w")
    local _, h = safe_method(self._root, "h")
    if not near(x, g.x) or not near(y, g.y) or not near(w, g.w) or not near(h, g.h) then
        pcall(function() self._root:set_shape(g.x, g.y, g.w, g.h) end)
    end
    self._layout_cache = g
    if self._cards then
        for i = 1, #self._cards do
            if self._cards[i] then self._cards[i]:layout(0, (i-1)*g.ch, g.w, g.ch) end
        end
    end
end

function weapons:_render()
    local snap = weapons._current_snapshot
    if not self._layout_cache or not snap or not snap.slots then
        if self._root and check_alive(self._root) then pcall(function() self._root:set_visible(false) end) end
        return
    end
    if not self._cards then return end
    local texts = self._texts or btexts()
    for i = 1, 2 do
        local card_texts = {}
        for k, v in pairs(texts) do card_texts[k] = v end
        local slot = snap.slots[i] or {present=false}
        local name = slot.name_id and loc(slot.name_id) or nil
        card_texts.name = (name and name ~= slot.name_id) and name or loc(LKEYS[i])
        if self._cards[i] then self._cards[i]:render(slot, snap.selected==i, card_texts) end
    end
    local valid = self:verify()
    if self._root and check_alive(self._root) then
        pcall(function() if self._root:visible() ~= valid then self._root:set_visible(valid) end end)
    end
end

function weapons:verify()
    if not self._mounted or not self._root or not check_alive(self._root) then return false end
    if not self._layout_cache then return false end
    local lc = self._layout_cache
    local ok_x, ax = safe_method(self._root, "x")
    local ok_y, ay = safe_method(self._root, "y")
    local ok_w, aw = safe_method(self._root, "w")
    local ok_h, ah = safe_method(self._root, "h")
    if not ok_x or not ok_y or not ok_w or not ok_h then return false end
    if not near(ax, lc.x) or not near(ay, lc.y) or not near(aw, lc.w) or not near(ah, lc.h) then return false end
    if not self._cards or #self._cards ~= 2 then return false end
    for i = 1, 2 do
        if not self._cards[i] then return false end
        if type(self._cards[i].verify) ~= "function" then return false end
        if not self._cards[i]:verify() then return false end
    end
    return true
end

function weapons:refresh_settings(manager)
    if kyohud.settings.enable_hud_foundation == true and kyohud.settings.enable_weapons == true and _G.IS_VR ~= true then
        if not self._mounted or not self._root or not check_alive(self._root) then self:mount(manager); return end
        self:refresh(manager or self._manager)
        self._texts = btexts()
        self:_apply()
        self:_render()
    else
        if self._mounted or self._root then self:unmount() end
    end
end

function weapons:rebuild(manager)
    self:unmount(); self:mount(manager)
end

function weapons:on_heist_start(manager)
    if not (manager or self._manager) then return end
    self._manager = manager or self._manager
    clear_state()
end

function weapons:destroy(manager)
    if manager and self._manager and manager ~= self._manager then return end
    self:unmount(); self._manager = nil
end

function weapons:update(manager, t, dt)
    if manager ~= managers.hud then return end
    if type(t) ~= "number" or t ~= t or t == math.huge or t == -math.huge then return end
    if kyohud.settings.enable_hud_foundation ~= true or kyohud.settings.enable_weapons ~= true or _G.IS_VR == true then
        if self._mounted or self._root then self:unmount() end
        return
    end
    if self._mounted and self._root and not check_alive(self._root) then
        self._root = nil; self._cards = nil; self._parent = nil; self._mounted = false; self._layout_cache = nil
    end
    if not self._mounted then
        if self._last_mount_attempt ~= nil and t >= self._last_mount_attempt
            and t - self._last_mount_attempt < 0.5 then return end
        self:mount(manager or self._manager)
        self._last_mount_attempt = t
    end
    if not self._mounted then return end
    self._wua = (self._wua or 0) + (dt or 0)
    if self._wua < UI then return end
    self._wua = 0
    if type(t) ~= "number" or t ~= t then return end
    if self._last_poll == nil or t < self._last_poll or t - self._last_poll >= 0.5 then
        self._last_poll = t
        self:refresh(manager or self._manager)
    end
    if self._root and check_alive(self._root) and self._parent and check_alive(self._parent) then
        self:_apply()
        self:_render()
    end
end
