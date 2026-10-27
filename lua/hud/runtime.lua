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
    self:_coordinate_mission("unmount")
    self:_coordinate_objectives("unmount")
    self:_coordinate_alerts("unmount")
    self:_coordinate_assault("unmount")
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
    self:_coordinate_mission("unmount")
    self:_coordinate_objectives("unmount")
    self:_coordinate_alerts("unmount")
    self:_coordinate_assault("unmount")
    if self._root_panel then
        local removed = self:_try_remove_root()
        if not removed then
            self:_coordinate_mission("mount", manager)
            self:_coordinate_objectives("mount", manager)
            self:_coordinate_alerts("mount", manager)
            self:_coordinate_assault("mount", manager)
            return
        end
    end
    self._mounted = false
    self:mount(manager)
    self:_coordinate_mission("rebuild", manager)
    self:_coordinate_objectives("rebuild", manager)
    self:_coordinate_alerts("rebuild", manager)
    self:_coordinate_assault("rebuild", manager)
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
    else
        if self._mounted or self._root_panel then
            self:unmount()
        end
    end
end

function RT:on_heist_start(manager)
    local mgr = manager or self._manager
    if not mgr then return end
    if self._mounted_manager_id == mgr then return end
    self._heist_generation = self._heist_generation + 1
    self._mounted_manager_id = mgr
end

function RT:destroy(manager)
    if manager and self._manager and manager ~= self._manager then
        return
    end
    self:_coordinate_mission("destroy", manager)
    self:_coordinate_objectives("destroy", manager)
    self:_coordinate_alerts("destroy", manager)
    self:_coordinate_assault("destroy", manager)
    self:unmount()
    self._mounted_manager_id = nil
end

function RT:update(manager, t, dt)
    if not t then return end

    if kyohud.settings.enable_hud_foundation == true then
        self:_coordinate_alerts("update", t, dt)
        self:_coordinate_assault("update", t, dt)
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
        if mission then
            mission:on_heist_start(self)
        end
        local objectives = kyohud.hud.objectives
        if objectives then
            objectives:on_heist_start(self)
        end
        local alerts = kyohud.hud.alerts
        if alerts and type(alerts.on_heist_start) == "function" then
            alerts:on_heist_start(self)
        end
        local assault = kyohud.hud.assault
        if assault then
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
