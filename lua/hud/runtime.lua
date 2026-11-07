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

local function safe_call(obj, method_name, ...)
    if obj == nil then return CALL_MISSING, nil end
    local ok_get, method_or_err = pcall(function() return obj[method_name] end)
    if not ok_get then return CALL_ERROR, nil end
    if type(method_or_err) ~= "function" then return CALL_MISSING, nil end
    local ok_call, result = pcall(method_or_err, obj, ...)
    if not ok_call then return CALL_ERROR, nil end
    return CALL_OK, result
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
        crew[method_name](crew, self._manager, ...)
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
        safe_call(mission._root_panel, "set_visible", false)
        mission:_update_layout()
        mission:_ensure_primitives()
        mission:_sync_primitives()
        if mission:_verify_render() then
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
    if not t then return end

    if kyohud.settings.enable_hud_foundation == true then
        self:_coordinate_alerts("update", t, dt)
        self:_coordinate_assault("update", t, dt)
        self:_coordinate_player("update", t, dt)
        self:_coordinate_weapons("update", t, dt)
        self:_coordinate_equipment("update", t, dt)
        self:_coordinate_crew("update", t, dt)
        self:_sync_local_backdrop(t)
    end

    if kyohud.settings.enable_hud_foundation == true and kyohud.settings.enable_objectives == true then
        local objectives = kyohud.hud.objectives
        if objectives and type(objectives.animate) == "function" and objectives._mounted then
            objectives:animate(t, dt)
        end
    end

    if self._last_recovery_time ~= nil and t >= self._last_recovery_time and (t - self._last_recovery_time) < RECOVERY_INTERVAL then
        return
    end

    local mgr = manager or self._manager
    self._last_recovery_time = t

    if kyohud.settings.enable_hud_foundation ~= true then
        self:unmount()
        return
    end

    if self._needs_refresh and self._root_panel and panel_alive(self._root_panel) then
        self:_do_refresh()
        self:_coordinate_mission("update", t, dt)
        self:_coordinate_objectives("update", t, dt)
        return
    end

    if mgr and not self._manager then
        self._manager = mgr
    end
    self:mount(mgr)
    self:_coordinate_mission("update", t, dt)
    self:_coordinate_objectives("update", t, dt)
end

local function _backdrop_coverage()
    local settings = kyohud.settings
    if settings.enable_player ~= true then return false end
    if settings.enable_weapons ~= true then return false end
    if settings.enable_equipment ~= true then return false end
    local P = kyohud.hud.player
    local W = kyohud.hud.weapons
    local E = kyohud.hud.equipment
    if not P or not W or not E then return false end
    if not P._mounted or not W._mounted or not E._mounted then return false end
    local pok, presult = pcall(P.verify, P)
    if not pok or not presult then return false end
    local wok, wresult = pcall(W.verify, W)
    if not wok or not wresult then return false end
    local eok,eresult = pcall(E.verify, E)
    if not eok or not eresult then return false end
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

function RT:_verify_local_backdrop()
    self._local_backdrop_verified = false
    if not _backdrop_coverage() then return false end
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

function RT:_sync_local_backdrop(t)
    if t ~= nil then
        if self._last_backdrop_sync ~= nil and t >= self._last_backdrop_sync
            and (t - self._last_backdrop_sync) < BG_THROTTLE then
            return
        end
        self._last_backdrop_sync = t
    end
    if not _backdrop_coverage() then
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
    self._local_backdrop_verified = self:_verify_local_backdrop()
    if not self._local_backdrop_verified then
        safe_call(bg, "set_visible", false)
    end
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
