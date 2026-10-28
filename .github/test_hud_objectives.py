"""LOT2b -- hud/objectives.lua: bounded behavioral tests (RED state).

Seven behavioral tests against native-shaped ObjectivesManager:
1. Activation after registry insertion
2. Detached scalar snapshot immune to source mutation
3. Removal after registry deletion retaining second active
4. Reactivate moves to end with updated text
5. select_visible returns last N
6. Delayed-presentation transition (RED)
7. complete_objective increments amount (RED)
8. Native OM:reset clears active, preserves panel identity

Native notification order (objectivesmanager.lua):
  activate_objective: _delayed_presentation=nil (line 192) then either
                      {t=1,activate_params=...} (line 195-198) or
                      HUDManager:activate_objective (line 200),
                      BEFORE _active_objectives[id]=objective (line 224)
  update:             decrement _delayed_presentation.t (line 82),
                      HUDManager:activate_objective when t<=0 (line 85),
                      clear _delayed_presentation (line 91)
  remove_objective:   HUDManager:complete_objective (line 309) BEFORE
                      _active_objectives[id] = nil (line 315)

Test dispatches PostHooks AFTER corresponding originals (no silent dedup).
Loads objectives chunk under objectivesmanager AND hudmanagerpd2 contexts.
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
OBJECTIVES_PATH = ROOT / "lua" / "hud" / "objectives.lua"
LAYOUT_PATH = ROOT / "lua" / "hud" / "layout.lua"
RUNTIME_PATH = ROOT / "lua" / "hud" / "runtime.lua"
NATIVE_VIS_PATH = ROOT / "lua" / "hud" / "native_visibility.lua"
MISSION_PATH = ROOT / "lua" / "hud" / "mission.lua"

STUBS = '''
kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end
PlayerBase = {PLAYER_INFO_HUD_PD2 = "player_info_hud_pd2"}
kyohud.settings = kyohud.settings or {}
if kyohud.settings.enable_hud_foundation == nil then
    kyohud.settings.enable_hud_foundation = false
end
if kyohud.settings.hud_scale == nil then
    kyohud.settings.hud_scale = 1.0
end
kyohud.settings.enable_mission = false
if kyohud.settings.enable_objectives == nil then
    kyohud.settings.enable_objectives = false
end
if kyohud.settings.objectives_visible_limit == nil then
    kyohud.settings.objectives_visible_limit = 1
end

if not math.round then
    function math.round(v) return math.floor(v + 0.5) end
end

Hooks = {_all = {}}
function Hooks:PostHook(class, method, id, fn)
    table.insert(self._all, {kind="post", class=class, method=method, id=id, fn=fn})
    local orig = class[method]
    if orig then
        class[method] = function(self, ...)
            local r = {orig(self, ...)}
            fn(self, ...)
            return unpack(r)
        end
    end
end
function Hooks:PreHook(class, method, id, fn)
    table.insert(self._all, {kind="pre", class=class, method=method, id=id, fn=fn})
    local orig = class[method]
    if orig then
        class[method] = function(self, ...)
            fn(self, ...)
            return orig(self, ...)
        end
    end
end
function Hooks:Add(id, event, fn) end
function log(...) end
function alive(x) return x ~= nil and x._alive ~= false end
Color = setmetatable({}, {__call = function(...) return {} end})

Application = Application or {}
function Application:editor() return false end
function Application:time() return Application._time or 0 end

HUDManager = {}
HUDManager.update = function() end
HUDManager.init_finalize = function() end
HUDManager._setup_player_info_hud_pd2 = function() end
HUDManager.resolution_changed = function() end
HUDManager.destroy = function() end
HUDManager.activate_objective = function(self, data) end
HUDManager.present_mid_text = function(self, data) end
HUDManager.update_amount_objective = function(self, data) end
HUDManager.complete_objective = function(self, data) end
HUDManager.complete_sub_objective = function(self, data) end
HUDManager.remind_objective = function(self, id) end

function clone(t)
    local c = {}
    for k, v in pairs(t) do c[k] = v end
    return c
end

ObjectivesManager = {}
ObjectivesManager.REMINDER_INTERVAL = 240
function ObjectivesManager:_remind_objetive(id, title_id)
    if not Application:editor() and managers.platform:presence() ~= "Playing" then
        return
    end
    if self._remind_objectives[id] then
        self._remind_objectives[id].next_t = Application:time() + self.REMINDER_INTERVAL
    end
    if managers.user:get_setting("objective_reminder") then
        title_id = title_id or "hud_objective_reminder"
        local objective = self._objectives[id]
        local title_message = managers.localization:text(title_id)
        local text = objective.text
        managers.hud:present_mid_text({
            time = 4,
            text = text,
            title = title_message,
        })
    end
    managers.hud:remind_objective(id)
end
function ObjectivesManager:get_active_objectives()
    return self._active_objectives
end
function ObjectivesManager:activate_objective(id, load_data, data)
    if not id or not self._objectives[id] then return end
    local objective = self._objectives[id]
    for _,sub in pairs(objective.sub_objectives) do sub.completed=false end
    objective.current_amount = load_data and load_data.current_amount or data and data.amount and 0 or objective.current_amount
    objective.amount = load_data and load_data.amount or data and data.amount or objective.amount
    local activate_params = {
        id = id,
        text = objective.text,
        amount = objective.amount,
        current_amount = objective.current_amount,
    }
    self._delayed_presentation = nil
    if data and data.delay_presentation then
        self._delayed_presentation = {
            t = 1,
            activate_params = activate_params,
        }
    else
        managers.hud:activate_objective(activate_params)
    end
    self._active_objectives[id] = objective
end
function ObjectivesManager:activate_objective_countdown(id, load_data, data)
    if not id or not self._objectives[id] then return end
    local objective = self._objectives[id]
    for _, sub_objective in pairs(objective.sub_objectives) do
        sub_objective.completed = false
    end
    objective.current_amount = load_data and load_data.current_amount or data and data.amount and 0 or objective.current_amount
    objective.amount = load_data and load_data.amount or data and data.amount or objective.amount
    objective.countdown = true
    local activate_params = {
        id = id,
        text = objective.text,
        sub_objectives = objective.sub_objectives,
        amount = objective.amount,
        current_amount = objective.amount - objective.current_amount,
        amount_text = objective.amount_text
    }
    self._delayed_presentation = nil
    if data and data.delay_presentation then
        self._delayed_presentation = {
            t = 1,
            activate_params = activate_params,
        }
    else
        managers.hud:activate_objective(activate_params)
    end
    self._active_objectives[id] = objective
end
function ObjectivesManager:update(t, dt)
    for id, data in pairs(self._remind_objectives) do
        if t > data.next_t then
            self:_remind_objetive(id)
        end
    end
    if self._delayed_presentation then
        self._delayed_presentation.t = self._delayed_presentation.t - dt
        if self._delayed_presentation.t <= 0 then
            managers.hud:activate_objective(self._delayed_presentation.activate_params)
            if self._delayed_presentation.mid_text_params then
                managers.hud:present_mid_text(self._delayed_presentation.mid_text_params)
            end
            self._delayed_presentation = nil
        end
    end
end
function ObjectivesManager:remove_objective(id, load_data)
    if not id or not self._objectives[id] then return end
    if not self._active_objectives[id] then return end
    local objective = self._objectives[id]
    managers.hud:complete_objective({remove = true, id = id, text = objective.text})
    self._active_objectives[id] = nil
end
function ObjectivesManager:complete_objective(id, load_data)
    if not id or not self._objectives[id] then return end
    if not self._active_objectives[id] then return end
    local objective = self._active_objectives[id]
    if objective.amount then
        objective.current_amount = objective.current_amount + 1
        managers.hud:update_amount_objective({id=id, text=objective.text, amount=objective.amount, current_amount=objective.current_amount})
        if objective.current_amount < objective.amount then return end
        objective.current_amount = 0
    end
    managers.hud:complete_objective({id=id, text=objective.text})
    self._active_objectives[id] = nil
end
function ObjectivesManager:complete_objective_countdown(id, load_data)
    if not id or not self._objectives[id] then return end
    if not self._active_objectives[id] then return end
    local objective = self._active_objectives[id]
    if objective.amount then
        objective.current_amount = objective.current_amount + 1
        managers.hud:update_amount_objective({id=id, text=objective.text, amount=objective.amount, current_amount=objective.amount - objective.current_amount})
        if objective.current_amount < objective.amount then return end
        objective.current_amount = 0
    end
    managers.hud:complete_objective({id=id, text=objective.text})
    self._active_objectives[id] = nil
end
function ObjectivesManager:complete_sub_objective(id, sub_id, load_data)
    if not id or not self._objectives[id] then return end
    if not self._active_objectives[id] then return end
    local objective = self._active_objectives[id]
    local sub = objective.sub_objectives and objective.sub_objectives[sub_id]
    if not sub then return end
    sub.completed = true
    managers.hud:complete_sub_objective({text = objective.text, sub_id = sub_id})
    local all_done = true
    for _, s in pairs(objective.sub_objectives) do
        if not s.completed then
            all_done = false
            break
        end
    end
    if all_done then
        self:complete_objective(id)
    end
end
function ObjectivesManager:load(data)
    local state = data.ObjectivesManager
    if state then
        self._completed_objectives_ordered = state.completed_objectives_ordered
        for name, save_data in pairs(state.objective_map) do
            local objective_data = self._objectives[name]
            if save_data.active then
                if save_data.countdown then
                    self:activate_objective_countdown(name, {
                        current_amount = save_data.current_amount,
                        amount = save_data.amount
                    })
                else
                    self:activate_objective(name, {
                        current_amount = save_data.current_amount,
                        amount = save_data.amount
                    })
                end
                for sub_id, completed in pairs(save_data.sub_objective) do
                    if completed then
                        self:complete_sub_objective(name, sub_id, {})
                    end
                end
            end
            if save_data.complete then
                self._completed_objectives[name] = objective_data
            end
            if save_data.read then
                self._read_objectives[name] = true
            end
        end
    end
end
function ObjectivesManager:reset()
    self._active_objectives = {}
    self._completed_objectives = {}
    self._completed_objectives_ordered = {}
    self._read_objectives = {}
    self._remind_objectives = {}
    self:_parse_objectives()
end
function ObjectivesManager:_parse_objectives()
end
function ObjectivesManager:remove_and_activate_objective(id, load_data, data)
    local delay_presentation = next(self._active_objectives) and true or nil
    for name, data in pairs(clone(self._active_objectives)) do
        self:remove_objective(name)
    end
    data = data or {}
    data.delay_presentation = delay_presentation or nil
    self:activate_objective(id, nil, data)
end

managers = {}
managers.platform = managers.platform or {}
function managers.platform:presence() return "Playing" end
managers.user = managers.user or {}
function managers.user:get_setting(key) return true end
managers.localization = managers.localization or {}
function managers.localization:text(key) return "Loc:" .. tostring(key) end

tweak_data = tweak_data or {}
tweak_data.hud = tweak_data.hud or {}
if tweak_data.hud.medium_font_noshadow == nil then
    tweak_data.hud.medium_font_noshadow = "fonts/font_medium_mf"
end
'''

DIESEL = '''
_panel_id = 0
function _make_panel(name)
    _panel_id = _panel_id + 1
    local p = {
        _alive = true, _visible = true, _alpha = 1,
        _children = {}, _name = name or ("p" .. _panel_id),
        _x = 0, _y = 0, _w = 1920, _h = 1080,
    }
    function p:x() return self._x end
    function p:y() return self._y end
    function p:w() return self._w end
    function p:h() return self._h end
    function p:set_shape(x,y,w,h) self._x=x; self._y=y; self._w=w; self._h=h end
    function p:set_visible(v) self._visible = v end
    function p:visible() return self._visible end
    function p:set_alpha(a) self._alpha = a end
    function p:alpha() return self._alpha end
    function p:child(n) return self._children[n] end
    function p:parent() return self._parent end
    function p:remove(c)
        if c then
            for k, v in pairs(self._children) do
                if v == c then self._children[k] = nil; c._alive = false; return end
            end
        end
    end
    function p:panel(opts)
        local ch = _make_panel(opts and opts.name)
        ch._parent = self
        if opts then
            if opts.x then ch._x = opts.x end
            if opts.y then ch._y = opts.y end
            if opts.w then ch._w = opts.w end
            if opts.h then ch._h = opts.h end
        end
        self._children[ch._name] = ch
        return ch
    end
    function p:text(opts)
        local t = _make_panel(opts and opts.name)
        t._parent = self
        t._text = opts and opts.text or ""
        t._font = opts and opts.font
        t._font_size = opts and opts.font_size or 16
        if opts then
            if opts.x then t._x = opts.x end
            if opts.y then t._y = opts.y end
            if opts.w then t._w = opts.w end
            if opts.h then t._h = opts.h end
            if opts.visible ~= nil then t._visible = opts.visible end
            if opts.alpha ~= nil then t._alpha = opts.alpha end
        end
        self._children[t._name] = t
        function t:set_text(str) self._text = str end
        function t:text() return self._text end
        function t:font_size() return self._font_size end
        function t:set_font_size(s) self._font_size = s end
        function t:text_rect()
            local natural_w = #self._text * self._font_size * 0.5
            return 0, 0, natural_w, self._font_size
        end
        function t:parent() return self._parent end
        return t
    end
    return p
end

function _make_parent()
    local p = _make_panel("safe_hud_parent")
    p._w = 1920; p._h = 1080
    return p
end

function _make_mgr(parent)
    local safe = {panel = parent}
    _G.managers.hud = setmetatable({
        script = function(self, name) return safe end,
        disabled = function() return false end,
    }, {__index = HUDManager})
    return safe
end

function _make_om()
    local OM = setmetatable({
        _objectives = {},
        _active_objectives = {},
        _remind_objectives = {},
        _delayed_presentation = nil,
    }, {__index = ObjectivesManager})
    managers.objectives = OM
    return OM
end
'''


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute(DIESEL)
    lua.execute("_init_fp = _make_parent(); _make_mgr(_init_fp)")
    lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
    for path in [LAYOUT_PATH, NATIVE_VIS_PATH, RUNTIME_PATH, MISSION_PATH]:
        src = _read(path)
        if src:
            lua.execute(src)
    obj_src = _read(OBJECTIVES_PATH)
    if obj_src:
        lua.execute('RequiredScript = "lib/managers/objectivesmanager"')
        lua.execute(obj_src)
        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        lua.execute(obj_src)
    return lua, obj_src is not None


class ObjectivesBehavioralTests(unittest.TestCase):
    """Bounded behavioral tests against native-shaped ObjectivesManager."""

    def test_activation_after_registry_insertion(self):
        """After native activate_objective completes, O._active contains the objective.

        HUD relay fires BEFORE registry insertion (line 200 before 224).
        PostHook dispatches AFTER original HUDManager:activate_objective.
        Final O._active must reflect the activation.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            _obs = {}
            Hooks:PostHook(HUDManager, "activate_objective", "obs_act", function(self, data)
                _obs.activation = managers.objectives._active_objectives[data.id]
            end)
            local OM = _make_om()
            OM._objectives["hack"] = {
                id = "hack",
                text = "Hack the computer",
                amount = nil,
                current_amount = nil,
                sub_objectives = {},
            }

            OM:activate_objective("hack", nil, {})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O._active) == "table", "O._active must be table")
            _count = #O._active
            assert(_count == 1, "O._active must have 1 entry, got " .. _count)
            _found_id = O._active[1].id
            _found_text = O._active[1].text
            assert(_found_id == "hack", "id must be hack")
            assert(_found_text == "Hack the computer", "text must match")

            -- Registry has it now (after native call)
            assert(OM._active_objectives["hack"] ~= nil, "registry must contain hack")
        ''')
        activation_state = lua.eval("_obs.activation")
        self.assertIsNone(activation_state, "activation must see nil in registry at HUD relay")

    def test_detached_scalar_snapshot_immutable(self):
        """Scalar snapshot must be immune to subsequent source mutation.

        After activation, capture scalars. Then mutate source registry.
        O._active entry must remain unchanged (detached copy).
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect",
                text = "Collect bags",
                amount = 4,
                current_amount = 0,
                sub_objectives = {},
            }

            OM:activate_objective("collect", nil, {amount = 4})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            _captured_amount = O._active[1].amount
            _captured_current = O._active[1].current_amount
            assert(_captured_amount == 4, "initial amount must be 4")
            assert(_captured_current == 0, "initial current must be 0")

            -- Mutate source registry
            OM._objectives["collect"].current_amount = 2
            OM._active_objectives["collect"].current_amount = 2

            -- O._active must be immune
            _after_amount = O._active[1].amount
            _after_current = O._active[1].current_amount
            assert(_after_amount == 4, "amount must remain 4")
            assert(_after_current == 0, "current must remain 0 (detached)")
        ''')

    def test_removal_retains_second_active(self):
        """After native remove_objective, O._active retains second objective.

        Activate two objectives. Remove first. HUD completion fires BEFORE
        registry deletion (line 309 before 315). PostHook dispatches AFTER
        original HUDManager:complete_objective. Final O._active must contain
        only the second objective.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            _obs = {}
            Hooks:PostHook(HUDManager, "complete_objective", "obs_rem", function(self, data)
                _obs.removal = managers.objectives._active_objectives[data.id]
            end)
            local OM = _make_om()
            OM._objectives["first"] = {
                id = "first",
                text = "First objective",
                amount = nil,
                current_amount = nil,
                sub_objectives = {},
            }
            OM._objectives["second"] = {
                id = "second",
                text = "Second objective",
                amount = nil,
                current_amount = nil,
                sub_objectives = {},
            }

            OM:activate_objective("first", nil, {})
            OM:activate_objective("second", nil, {})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            _before_count = #O._active
            assert(_before_count == 2, "must have 2 active before removal")

            OM:remove_objective("first", nil)

            _after_count = #O._active
            assert(_after_count == 1, "must have 1 active after removal")
            _remaining_id = O._active[1].id
            assert(_remaining_id == "second", "remaining must be second")

            -- Registry no longer has first
            assert(OM._active_objectives["first"] == nil, "registry must not contain first")
            assert(OM._active_objectives["second"] ~= nil, "registry must contain second")
        ''')
        removal_state = lua.eval("_obs.removal")
        self.assertIsNotNone(removal_state, "removal must see entry in registry at HUD relay")

    def test_reactivate_moves_to_end_with_updated_text(self):
        """Reactivating first objective after changing its text places it last
        in O._active with ids second,first and text Updated."""
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local OM = _make_om()
            OM._objectives["first"] = {
                id = "first",
                text = "First objective",
                amount = nil,
                current_amount = nil,
                sub_objectives = {},
            }
            OM._objectives["second"] = {
                id = "second",
                text = "Second objective",
                amount = nil,
                current_amount = nil,
                sub_objectives = {},
            }

            OM:activate_objective("first", nil, {})
            OM:activate_objective("second", nil, {})

            OM._objectives["first"].text = "Updated"
            OM:activate_objective("first", nil, {})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O._active) == "table", "O._active must be table")
            _count = #O._active
            assert(_count == 2, "O._active must have 2 entries, got " .. _count)
            _id1 = O._active[1].id
            _id2 = O._active[2].id
            assert(_id1 == "second", "first slot must be second, got " .. tostring(_id1))
            assert(_id2 == "first", "second slot must be first, got " .. tostring(_id2))
            _text = O._active[2].text
            assert(_text == "Updated", "first text must be Updated, got " .. tostring(_text))
        ''')

    def test_select_visible_returns_single_current(self):
        """select_visible() returns only the latest current objective regardless of limit.

        Activate 4 objectives a,b,c,d. Verify:
        - select_visible() returns [d] (default)
        - select_visible(2) returns [d] (still only latest)
        - select_visible(3) returns [d] (still only latest)
        - O._active still has length 4 (no mutation)
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local OM = _make_om()
            OM._objectives["a"] = {
                id = "a", text = "Objective A", amount = nil, current_amount = nil, sub_objectives = {},
            }
            OM._objectives["b"] = {
                id = "b", text = "Objective B", amount = nil, current_amount = nil, sub_objectives = {},
            }
            OM._objectives["c"] = {
                id = "c", text = "Objective C", amount = nil, current_amount = nil, sub_objectives = {},
            }
            OM._objectives["d"] = {
                id = "d", text = "Objective D", amount = nil, current_amount = nil, sub_objectives = {},
            }

            OM:activate_objective("a", nil, {})
            OM:activate_objective("b", nil, {})
            OM:activate_objective("c", nil, {})
            OM:activate_objective("d", nil, {})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O._active) == "table", "O._active must be table")
            assert(#O._active == 4, "O._active must have 4 entries")

            local sel1 = O:select_visible()
            assert(type(sel1) == "table", "select_visible() must return table")
            assert(#sel1 == 1, "select_visible() must return 1 entry, got " .. #sel1)
            assert(sel1[1].id == "d", "select_visible() must return d, got " .. tostring(sel1[1].id))

            local sel2 = O:select_visible(2)
            assert(type(sel2) == "table", "select_visible(2) must return table")
            assert(#sel2 == 1, "select_visible(2) must return 1 entry, got " .. #sel2)
            assert(sel2[1].id == "d", "select_visible(2)[1] must be d, got " .. tostring(sel2[1].id))

            local sel3 = O:select_visible(3)
            assert(type(sel3) == "table", "select_visible(3) must return table")
            assert(#sel3 == 1, "select_visible(3) must return 1 entry, got " .. #sel3)
            assert(sel3[1].id == "d", "select_visible(3)[1] must be d, got " .. tostring(sel3[1].id))

            assert(#O._active == 4, "O._active must still have 4 entries after select_visible calls")
        ''')

    def test_delayed_presentation_transition(self):
        """RED: delayed activation defers HUD relay until update timer expires.

        After activate_objective with delay_presentation=true, O._active has 1
        entry (OM PostHook reads registry) but select_visible() returns 0 (HUD
        relay not yet fired). OM:update(0, 0.5) decrements t to 0.5 > 0, still
        0 visible. OM:update(0.5, 0.5) decrements t to 0.0, fires HUD relay,
        select_visible() returns the objective.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local OM = _make_om()
            OM._objectives["hack"] = {
                id = "hack",
                text = "Hack the computer",
                amount = nil,
                current_amount = nil,
                sub_objectives = {},
            }

            OM:activate_objective("hack", nil, {delay_presentation = true})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O._active) == "table", "O._active must be table")
            assert(#O._active == 1, "O._active must have 1 entry, got " .. #O._active)

            local sel0 = O:select_visible()
            assert(type(sel0) == "table", "select_visible() must return table")
            assert(#sel0 == 0, "select_visible() must return 0 before HUD relay, got " .. #sel0)

            OM:update(0, 0.5)
            local sel1 = O:select_visible()
            assert(#sel1 == 0, "select_visible() must still return 0 at t=0.5, got " .. #sel1)

            OM:update(0.5, 0.5)
            local sel2 = O:select_visible()
            assert(#sel2 == 1, "select_visible() must return 1 after full delay, got " .. #sel2)
            assert(sel2[1].id == "hack", "returned objective must be hack")
        ''')

    def test_complete_objective_increments_amount(self):
        """Calling complete_objective once on amount=3/current=0 increments to
        current=1 and keeps the objective active in O._active."""
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect",
                text = "Collect bags",
                amount = 3,
                current_amount = 0,
                sub_objectives = {},
            }

            OM:activate_objective("collect", nil, {amount = 3})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O._active) == "table", "O._active must be table")
            assert(#O._active == 1, "O._active must have 1 entry before complete, got " .. #O._active)

            OM:complete_objective("collect", nil)

            assert(#O._active == 1, "O._active must still have 1 entry after partial complete, got " .. #O._active)
            local entry = O._active[1]
            assert(entry.id == "collect", "id must still be collect")
            assert(entry.amount == 3, "amount must remain 3, got " .. tostring(entry.amount))
            assert(entry.current_amount == 1, "current_amount must be 1, got " .. tostring(entry.current_amount))
        ''')


    def test_complete_final_removes_keeps_other(self):
        """Calling complete_objective once on amount=1/current=0 finalizes the
        objective: native registry no longer holds it and O._active contains
        only the second (non-amount) objective."""
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect",
                text = "Collect bags",
                amount = 1,
                current_amount = 0,
                sub_objectives = {},
            }
            OM._objectives["other"] = {
                id = "other",
                text = "Other objective",
                amount = nil,
                current_amount = nil,
                sub_objectives = {},
            }

            OM:activate_objective("collect", nil, {amount = 1})
            OM:activate_objective("other", nil, {})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O._active) == "table", "O._active must be table")
            assert(#O._active == 2, "O._active must have 2 entries before complete, got " .. #O._active)

            OM:complete_objective("collect", nil)

            assert(OM._active_objectives["collect"] == nil, "registry must not contain collect after final complete")
            assert(OM._active_objectives["other"] ~= nil, "registry must still contain other")

            assert(#O._active == 1, "O._active must have 1 entry after complete, got " .. #O._active)
            local remaining = O._active[1]
            assert(remaining.id == "other", "remaining active must be other, got " .. tostring(remaining.id))
        ''')

    def test_activate_objective_countdown_snapshot(self):
        """activate_objective_countdown(amount=3,current=0): native stores
        current_amount=0 (completed units), O._active entry has
        current_amount=3 (display remaining = amount - current_amount) and
        countdown=true."""
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local OM = _make_om()
            OM._objectives["defuse"] = {
                id = "defuse",
                text = "Defuse the bomb",
                amount = 3,
                current_amount = 0,
                sub_objectives = {},
            }

            OM:activate_objective_countdown("defuse", nil, {amount = 3})

            assert(OM._objectives["defuse"].current_amount == 0, "native current_amount must be 0")
            assert(OM._objectives["defuse"].amount == 3, "native amount must be 3")
            assert(OM._objectives["defuse"].countdown == true, "native countdown must be true")

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O._active) == "table", "O._active must be table")
            assert(#O._active == 1, "O._active must have 1 entry, got " .. #O._active)
            local entry = O._active[1]
            assert(entry.id == "defuse", "entry id must be defuse")
            assert(entry.current_amount == 3, "entry current_amount must be 3 (display remaining), got " .. tostring(entry.current_amount))
            assert(entry.countdown == true, "entry countdown must be true")
        ''')


    def test_complete_objective_countdown(self):
        """activate_objective_countdown(amount=3,current=0); complete once:
        snapshot remaining=2, countdown=true, native current=1; complete 2 more:
        snapshot absent."""
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local OM = _make_om()
            OM._objectives["defuse"] = {
                id = "defuse",
                text = "Defuse the bomb",
                amount = 3,
                current_amount = 0,
                sub_objectives = {},
            }

            OM:activate_objective_countdown("defuse", nil, {amount = 3})

            assert(OM._objectives["defuse"].current_amount == 0, "native current_amount must be 0 before any complete")

            OM:complete_objective_countdown("defuse", nil)

            assert(OM._objectives["defuse"].current_amount == 1, "native current_amount must be 1 after first complete, got " .. tostring(OM._objectives["defuse"].current_amount))
            assert(OM._objectives["defuse"].countdown == true, "native countdown must remain true")
            assert(OM._objectives["defuse"].amount == 3, "native amount must remain 3")

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O._active) == "table", "O._active must be table")
            assert(#O._active == 1, "O._active must have 1 entry after first complete, got " .. #O._active)
            local entry = O._active[1]
            assert(entry.id == "defuse", "entry id must be defuse")
            assert(entry.current_amount == 2, "entry current_amount (remaining) must be 2, got " .. tostring(entry.current_amount))
            assert(entry.countdown == true, "entry countdown must be true, got " .. tostring(entry.countdown))

            OM:complete_objective_countdown("defuse", nil)
            OM:complete_objective_countdown("defuse", nil)

            assert(OM._active_objectives["defuse"] == nil, "registry must not contain defuse after 3 completes")

            assert(type(O._active) == "table", "O._active must still be table")
            assert(#O._active == 0, "O._active must have 0 entries after 3 completes, got " .. #O._active)
        ''')


    def test_complete_sub_objective_transitions(self):
        """ONE objective with sub ids a,b: activate snapshot includes detached
        scalar sub_objectives map entries id/text/completed. Complete a ->
        O entry.sub_objectives.a.completed true, b false; completing b removes
        parent. No invented numeric progress."""
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local OM = _make_om()
            OM._objectives["secure"] = {
                id = "secure",
                text = "Secure the area",
                amount = nil,
                current_amount = nil,
                sub_objectives = {
                    a = {id = "a", text = "Clear room A", completed = false},
                    b = {id = "b", text = "Clear room B", completed = false},
                },
            }

            OM:activate_objective("secure", nil, {})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O._active) == "table", "O._active must be table")
            assert(#O._active == 1, "O._active must have 1 entry, got " .. #O._active)
            local entry = O._active[1]
            assert(entry.id == "secure", "entry id must be secure")
            assert(type(entry.sub_objectives) == "table", "entry must have sub_objectives table")

            local sub_a = entry.sub_objectives.a
            local sub_b = entry.sub_objectives.b
            assert(sub_a, "sub_objectives must have key a")
            assert(sub_b, "sub_objectives must have key b")
            assert(sub_a.id == "a", "sub a id must be a")
            assert(sub_a.text == "Clear room A", "sub a text must match")
            assert(sub_a.completed == false, "sub a completed must be false")
            assert(sub_b.id == "b", "sub b id must be b")
            assert(sub_b.text == "Clear room B", "sub b text must match")
            assert(sub_b.completed == false, "sub b completed must be false")

            OM:complete_sub_objective("secure", "a", nil)

            assert(#O._active == 1, "O._active must still have 1 entry after completing a, got " .. #O._active)
            local entry2 = O._active[1]
            assert(entry2.sub_objectives.a.completed == true, "sub a must be completed, got " .. tostring(entry2.sub_objectives.a.completed))
            assert(entry2.sub_objectives.b.completed == false, "sub b must still be false")

            OM:complete_sub_objective("secure", "b", nil)

            assert(OM._active_objectives["secure"] == nil, "registry must not contain secure after all subs complete")
            assert(#O._active == 0, "O._active must have 0 entries after all subs complete, got " .. #O._active)
        ''')

    def test_late_snapshot_preexisting_registry(self):
        """Late snapshot with preexisting keyed registry (no activation calls):
        O._active sorts ids a,z,m with currently-displayed id promoted to last;
        select_visible() returns the displayed id; snapshot is detached from
        subsequent source text mutations."""
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local OM = _make_om()
            OM._objectives["z"] = {
                id = "z", text = "Zebra objective", amount = nil, current_amount = nil, sub_objectives = {},
            }
            OM._objectives["a"] = {
                id = "a", text = "Alpha objective", amount = nil, current_amount = nil, sub_objectives = {},
            }
            OM._objectives["m"] = {
                id = "m", text = "Mike objective", amount = nil, current_amount = nil, sub_objectives = {},
            }
            OM._active_objectives["z"] = OM._objectives["z"]
            OM._active_objectives["a"] = OM._objectives["a"]
            OM._active_objectives["m"] = OM._objectives["m"]
            managers.hud._hud_objectives = {_active_objective_id = "m"}

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            O:snapshot(OM)

            assert(type(O._active) == "table", "O._active must be table")
            assert(#O._active == 3, "O._active must have 3 entries, got " .. #O._active)
            assert(O._active[1].id == "a", "first slot must be a, got " .. tostring(O._active[1].id))
            assert(O._active[2].id == "z", "second slot must be z, got " .. tostring(O._active[2].id))
            assert(O._active[3].id == "m", "third slot must be m, got " .. tostring(O._active[3].id))

            local sel = O:select_visible()
            assert(type(sel) == "table", "select_visible() must return table")
            assert(#sel == 1, "select_visible() must return 1 entry, got " .. #sel)
            assert(sel[1].id == "m", "select_visible() must return m, got " .. tostring(sel[1].id))

            local captured_text = O._active[2].text
            OM._objectives["z"].text = "Mutated"
            OM._active_objectives["z"].text = "Mutated"
            local after_text = O._active[2].text
            assert(after_text == captured_text, "snapshot text must remain intact after source mutation, got " .. tostring(after_text))
        ''')

    def test_snapshot_reconciliation_preserves_activation_history(self):
        """Preexisting registry a,b,c (no activation). First snapshot with
        current=c asserts a,b,c. Then modify b (text=Updated, current_amount=2,
        amount=3), delete a from registry, set current=b. Second snapshot on
        same OM asserts _active length 2 with b,c in preserved order (b NOT
        reordered to end despite becoming current), b.text=Updated,
        b.current_amount=2."""
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local OM = _make_om()
            OM._objectives["a"] = {
                id = "a", text = "Alpha objective", amount = nil, current_amount = nil, sub_objectives = {},
            }
            OM._objectives["b"] = {
                id = "b", text = "Bravo objective", amount = nil, current_amount = nil, sub_objectives = {},
            }
            OM._objectives["c"] = {
                id = "c", text = "Charlie objective", amount = nil, current_amount = nil, sub_objectives = {},
            }
            OM._active_objectives["a"] = OM._objectives["a"]
            OM._active_objectives["b"] = OM._objectives["b"]
            OM._active_objectives["c"] = OM._objectives["c"]
            managers.hud._hud_objectives = {_active_objective_id = "c"}

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            O:snapshot(OM)

            assert(type(O._active) == "table", "O._active must be table")
            assert(#O._active == 3, "O._active must have 3 entries after first snapshot, got " .. #O._active)
            local ids1 = {}
            for i, entry in ipairs(O._active) do ids1[i] = entry.id end
            assert(ids1[1] == "a", "first slot must be a, got " .. tostring(ids1[1]))
            assert(ids1[2] == "b", "second slot must be b, got " .. tostring(ids1[2]))
            assert(ids1[3] == "c", "third slot must be c, got " .. tostring(ids1[3]))

            OM._objectives["b"].text = "Updated"
            OM._objectives["b"].current_amount = 2
            OM._objectives["b"].amount = 3
            OM._active_objectives["a"] = nil
            OM._objectives["a"] = nil
            managers.hud._hud_objectives = {_active_objective_id = "b"}

            O:snapshot(OM)

            assert(type(O._active) == "table", "O._active must still be table")
            assert(#O._active == 2, "O._active must have 2 entries after second snapshot, got " .. #O._active)
            local ids2 = {}
            for i, entry in ipairs(O._active) do ids2[i] = entry.id end
            assert(ids2[1] == "b", "first slot must remain b (preserved order), got " .. tostring(ids2[1]))
            assert(ids2[2] == "c", "second slot must remain c (preserved order), got " .. tostring(ids2[2]))
            assert(O._active[1].text == "Updated", "b.text must be Updated, got " .. tostring(O._active[1].text))
            assert(O._active[1].current_amount == 2, "b.current_amount must be 2, got " .. tostring(O._active[1].current_amount))
        ''')

    def test_manager_rebind_transition(self):
        """Manager rebind: OM1 activates old_id, OM2=_make_om() rebinds, OM2
        activates fresh_id; O._active contains only fresh_id. Subsequent
        O:snapshot(OM2) retains fresh_id without reordering."""
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            -- OM1: activate old objective
            local OM1 = _make_om()
            OM1._objectives["old_id"] = {
                id = "old_id",
                text = "Old objective",
                amount = nil,
                current_amount = nil,
                sub_objectives = {},
            }
            OM1:activate_objective("old_id", nil, {})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O._active) == "table", "O._active must be table")
            assert(#O._active == 1, "O._active must have 1 entry after OM1 activation, got " .. #O._active)
            assert(O._active[1].id == "old_id", "first entry must be old_id, got " .. tostring(O._active[1].id))

            -- OM2: rebind managers.objectives
            local OM2 = _make_om()
            OM2._objectives["fresh_id"] = {
                id = "fresh_id",
                text = "Fresh objective",
                amount = nil,
                current_amount = nil,
                sub_objectives = {},
            }
            OM2:activate_objective("fresh_id", nil, {})

            -- Assert only fresh_id is active, no old_id
            assert(#O._active == 1, "O._active must have 1 entry after OM2 activation, got " .. #O._active)
            assert(O._active[1].id == "fresh_id", "only entry must be fresh_id, got " .. tostring(O._active[1].id))

            -- Snapshot OM2: retains fresh_id, not reordering
            O:snapshot(OM2)
            assert(#O._active == 1, "O._active must have 1 entry after snapshot, got " .. #O._active)
            assert(O._active[1].id == "fresh_id", "snapshot must retain fresh_id, got " .. tostring(O._active[1].id))
        ''')

    def test_stale_manager_activate_same_id_no_rebind(self):
        """OM1 activate same id oldtext; OM2 activate same id freshtext
        (managers.objectives points OM2); then OM1:activate_objective same id
        again. Assert O._active still only freshtext, O._snapshot_manager==OM2.
        Tests stale callback not rebind."""
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local OM1 = _make_om()
            OM1._objectives["test"] = {
                id = "test",
                text = "oldtext",
                amount = nil,
                current_amount = nil,
                sub_objectives = {},
            }
            OM1:activate_objective("test", nil, {})

            local OM2 = _make_om()
            OM2._objectives["test"] = {
                id = "test",
                text = "freshtext",
                amount = nil,
                current_amount = nil,
                sub_objectives = {},
            }
            OM2:activate_objective("test", nil, {})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O._active) == "table", "O._active must be table")
            assert(#O._active == 1, "O._active must have 1 entry after OM2 activation, got " .. #O._active)
            assert(O._active[1].text == "freshtext", "text must be freshtext before stale call, got " .. tostring(O._active[1].text))
            assert(O._snapshot_manager == OM2, "_snapshot_manager must be OM2 before stale call")

            OM1:activate_objective("test", nil, {})

            assert(#O._active == 1, "O._active must still have 1 entry after stale call, got " .. #O._active)
            assert(O._active[1].text == "freshtext", "text must remain freshtext after stale call, got " .. tostring(O._active[1].text))
            assert(O._snapshot_manager == OM2, "_snapshot_manager must remain OM2 after stale call")
        ''')


    def test_stale_hud_activate_must_not_release_pending(self):
        """RED: Stale HUD manager callback must not release pending objective for current manager.

        Current managers.hud is the real one (captured by _lua fixture). Create oldHud via
        setmetatable({}, {__index=HUDManager}) WITHOUT rebinding managers.hud. Activate OM with
        delay_presentation=true: O._active has 1 entry with pending=true, select_visible() returns 0,
        _last_hud_presented_id is nil. Call oldHud:activate_objective({id=same,text=...,amount=...}):
        must NOT change pending, selection, or _last_hud_presented_id. Then OM:update native timer
        expiry fires real managers.hud:activate_objective callback, releasing pending: select_visible()
        returns 1 with correct id/text; _last_hud_presented_id == id; pending == false.
        Production on_hud_activate lacks identity guard (no check that self == managers.hud),
        so the stale callback incorrectly clears pending and sets _last_hud_presented_id: RED.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local OM = _make_om()
            OM._objectives["hack"] = {
                id = "hack",
                text = "Hack the computer",
                amount = 3,
                current_amount = 0,
                sub_objectives = {},
            }

            OM:activate_objective("hack", nil, {delay_presentation = true, amount = 3})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O._active) == "table", "O._active must be table")
            assert(#O._active == 1, "O._active must have 1 entry, got " .. #O._active)
            assert(O._active[1].pending == true,
                "entry must be pending after delayed activation, got " .. tostring(O._active[1].pending))

            local sel0 = O:select_visible()
            assert(type(sel0) == "table", "select_visible() must return table")
            assert(#sel0 == 0,
                "select_visible() must return 0 before HUD relay, got " .. #sel0)

            local last_presented_before = O._last_hud_presented_id
            assert(last_presented_before == nil,
                "_last_hud_presented_id must be nil before stale call, got " .. tostring(last_presented_before))

            local oldHud = setmetatable({}, {__index = HUDManager})
            oldHud:activate_objective({id = "hack", text = "Hack the computer", amount = 3})

            assert(O._active[1].pending == true,
                "entry must still be pending after stale HUD call, got " .. tostring(O._active[1].pending))

            local sel1 = O:select_visible()
            assert(type(sel1) == "table", "select_visible() must return table after stale call")
            assert(#sel1 == 0,
                "select_visible() must still return 0 after stale HUD call, got " .. #sel1)

            local last_presented_after_stale = O._last_hud_presented_id
            assert(last_presented_after_stale == nil,
                "_last_hud_presented_id must remain nil after stale HUD call, got " .. tostring(last_presented_after_stale))

            OM:update(0, 0.5)
            local sel2 = O:select_visible()
            assert(#sel2 == 0,
                "select_visible() must still return 0 at t=0.5, got " .. #sel2)

            OM:update(0.5, 0.5)
            local sel3 = O:select_visible()
            assert(#sel3 == 1,
                "select_visible() must return 1 after full delay, got " .. #sel3)
            assert(sel3[1].id == "hack",
                "returned objective must be hack, got " .. tostring(sel3[1].id))
            assert(sel3[1].text == "Hack the computer",
                "returned text must match, got " .. tostring(sel3[1].text))
            assert(O._active[1].pending == false,
                "entry must no longer be pending after real HUD relay, got " .. tostring(O._active[1].pending))
            assert(O._last_hud_presented_id == "hack",
                "_last_hud_presented_id must be hack after real HUD relay, got " .. tostring(O._last_hud_presented_id))
        ''')


    def test_first_render_transition(self):
        """RED: O:mount renders under RT._root_panel after activation.

        Enable objectives. RT:mount creates root panel. Activate objective with
        text, accent, amount=1, current_amount=0. O:mount creates owned child
        panel named kyohud_objectives_panel under RT._root_panel. Verify text
        primitive objective_1_text equals original text, quantity primitive
        objective_1_amount equals "0/1". Assert bounds y+h <= 100 (Mission
        reserved zone). Assert rendered root parent is RT root.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local parent = _init_fp
            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            assert(RT._root_panel, "RT._root_panel must exist after mount")
            assert(RT._mounted == true, "RT._mounted must be true")

            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect",
                text = "Sécurisez les sacs",
                amount = 1,
                current_amount = 0,
                sub_objectives = {},
            }

            OM:activate_objective("collect", nil, {amount = 1})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O.mount) == "function", "O:mount must be a function")

            O:mount(managers.hud)

            assert(type(O._panel) == "table", "O._panel must exist after mount")
            assert(O._panel._name == "kyohud_objectives_panel",
                "O._panel name must be kyohud_objectives_panel, got " .. tostring(O._panel._name))

            local obj_text_prim = O._panel:child("objective_1_text")
            assert(obj_text_prim, "objective_1_text primitive must exist")
            local obj_text = obj_text_prim:text()
            assert(obj_text == "Sécurisez les sacs",
                "objective_1_text must equal 'Sécurisez les sacs', got " .. tostring(obj_text))

            local obj_amount_prim = O._panel:child("objective_1_amount")
            assert(obj_amount_prim, "objective_1_amount primitive must exist")
            local obj_amount = obj_amount_prim:text()
            assert(obj_amount == "0/1",
                "objective_1_amount must equal '0/1', got " .. tostring(obj_amount))

            local panel_y = O._panel:y()
            local panel_h = O._panel:h()
            assert(type(panel_y) == "number", "panel y must be number")
            assert(type(panel_h) == "number", "panel h must be number")
            assert(panel_y + panel_h <= 100,
                "panel y+h must be <= 100 (Mission reserved zone), got " .. tostring(panel_y + panel_h))

            assert(O._panel._parent == RT._root_panel,
                "O._panel parent must be RT._root_panel")
        ''')


    def test_long_text_geometry_transition(self):
        """Long UTF-8 text geometry stays bounded after parent resize.

        Enable foundation/objectives, RT mount, activate with string.rep("Évacuation ",80),
        amount=10, current=2, O mount. Assert text:text_rect width<=text:w and height<=text:h,
        amount text="2/10", no overlap (text right <= amount.x). Resize parent to 640x480,
        RT refresh settings, O mount, reassert bounds and same root+primitive identity.
        UTF-8 truncation must remain valid (Python str decode).
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local parent = _init_fp
            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            assert(RT._root_panel, "RT._root_panel must exist after mount")
            assert(RT._mounted == true, "RT._mounted must be true")

            local long_text = string.rep("Évacuation ", 80)
            local OM = _make_om()
            OM._objectives["evac"] = {
                id = "evac",
                text = long_text,
                amount = 10,
                current_amount = 2,
                sub_objectives = {},
            }

            OM:activate_objective("evac", {amount=10,current_amount=2}, {})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O.mount) == "function", "O:mount must be a function")

            O:mount(managers.hud)

            assert(type(O._panel) == "table", "O._panel must exist after mount")
            assert(O._panel._name == "kyohud_objectives_panel",
                "O._panel name must be kyohud_objectives_panel, got " .. tostring(O._panel._name))

            local obj_text_prim = O._panel:child("objective_1_text")
            assert(obj_text_prim, "objective_1_text primitive must exist")
            local text_x, text_y, text_w, text_h = obj_text_prim:text_rect()
            local obj_text_w = obj_text_prim:w()
            local obj_text_h = obj_text_prim:h()
            assert(type(text_w) == "number", "text_rect width must be number")
            assert(type(text_h) == "number", "text_rect height must be number")
            assert(text_w <= obj_text_w,
                "text_rect width (" .. tostring(text_w) .. ") must be <= text:w() (" .. tostring(obj_text_w) .. ")")
            assert(text_h <= obj_text_h,
                "text_rect height (" .. tostring(text_h) .. ") must be <= text:h() (" .. tostring(obj_text_h) .. ")")

            local obj_amount_prim = O._panel:child("objective_1_amount")
            assert(obj_amount_prim, "objective_1_amount primitive must exist")
            local obj_amount = obj_amount_prim:text()
            assert(obj_amount == "2/10",
                "objective_1_amount must equal '2/10', got " .. tostring(obj_amount))

            local amount_x = obj_amount_prim:x()
            local text_right = text_x + text_w
            assert(type(amount_x) == "number", "amount x must be number")
            assert(text_right <= amount_x,
                "text right (" .. tostring(text_right) .. ") must be <= amount.x (" .. tostring(amount_x) .. ")")

            local root_before = RT._root_panel
            local text_prim_before = obj_text_prim

            parent._w = 640
            parent._h = 480

            RT:refresh_settings(managers.hud)
            O:mount(managers.hud)

            assert(RT._root_panel == root_before,
                "RT._root_panel must remain same instance after resize")

            local obj_text_prim_after = O._panel:child("objective_1_text")
            assert(obj_text_prim_after == text_prim_before,
                "text primitive must remain same instance after resize")

            local text_x2, text_y2, text_w2, text_h2 = obj_text_prim_after:text_rect()
            local obj_text_w2 = obj_text_prim_after:w()
            local obj_text_h2 = obj_text_prim_after:h()
            assert(text_w2 <= obj_text_w2,
                "text_rect width after resize (" .. tostring(text_w2) .. ") must be <= text:w() (" .. tostring(obj_text_w2) .. ")")
            assert(text_h2 <= obj_text_h2,
                "text_rect height after resize (" .. tostring(text_h2) .. ") must be <= text:h() (" .. tostring(obj_text_h2) .. ")")

            local obj_amount_prim_after = O._panel:child("objective_1_amount")
            local obj_amount_after = obj_amount_prim_after:text()
            assert(obj_amount_after == "2/10",
                "objective_1_amount must remain '2/10' after resize, got " .. tostring(obj_amount_after))

            local amount_x2 = obj_amount_prim_after:x()
            local text_right2 = text_x2 + text_w2
            assert(text_right2 <= amount_x2,
                "text right after resize (" .. tostring(text_right2) .. ") must be <= amount.x (" .. tostring(amount_x2) .. ")")

            _rendered_text = obj_text_prim_after:text()
        ''')

        rendered_text = lua.eval("_rendered_text")
        self.assertIsInstance(rendered_text, str, "rendered text must be Python str")
        try:
            rendered_text.encode('utf-8').decode('utf-8')
        except UnicodeError as e:
            self.fail(f"Rendered text is not valid UTF-8: {e}")

    def test_runtime_lifecycle_transition(self):
        """Runtime lifecycle: init_finalize -> rebuild -> refresh_settings.

        Enable foundation/objectives, seed OM with active objective before HUD init.
        managers.hud:init_finalize() triggers hooks that populate RT root and O panel
        automatically (no direct O:mount). Set killstreak=7. RT:rebuild creates new root
        and re-parents O panel under new root; state/text/sentinel retained.
        Set enable_objectives=false; RT:refresh_settings coordinates unmount;
        O panel removed, active snapshot retained, RT root unchanged.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local OM = _make_om()
            OM._objectives["secure"] = {
                id = "secure",
                text = "Secure the area",
                amount = nil,
                current_amount = nil,
                sub_objectives = {},
            }
            OM._active_objectives["secure"] = OM._objectives["secure"]
            managers.hud._hud_objectives = {_active_objective_id = "secure"}

            managers.hud:init_finalize()

            local RT = kyohud.hud.runtime
            assert(RT._root_panel, "RT._root_panel must exist after init_finalize")
            assert(RT._mounted == true, "RT._mounted must be true after init_finalize")

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(O._mounted == true, "O._mounted must be true after init_finalize")
            assert(O._root_panel, "O._root_panel must exist after init_finalize")
            assert(O._root_panel._parent == RT._root_panel,
                "O._root_panel parent must be RT._root_panel after init_finalize")

            kyohud.killstreak = 7
            local text_before = O._active[1].text
            local root_before_rebuild = RT._root_panel

            RT:rebuild(managers.hud)

            local root_after_rebuild = RT._root_panel
            assert(root_after_rebuild, "RT._root_panel must exist after rebuild")
            assert(root_after_rebuild ~= root_before_rebuild,
                "RT._root_panel must be new instance after rebuild")

            assert(O._root_panel, "O._root_panel must exist after remount")
            assert(O._root_panel._parent == RT._root_panel,
                "O._root_panel parent must be new RT._root_panel after remount")
            assert(kyohud.killstreak == 7, "killstreak must be retained after rebuild")
            assert(O._active[1].text == text_before,
                "objective text must be retained after rebuild")

            kyohud.settings.enable_objectives = false
            local rt_root_before_refresh = RT._root_panel

            RT:refresh_settings(managers.hud)

            assert(O._mounted == false, "O._mounted must be false after refresh transition")
            assert(O._root_panel == nil, "O._root_panel must be nil after refresh transition")
            assert(#O._active == 1, "O._active must retain snapshot after unmount")
            assert(O._active[1].id == "secure", "snapshot must retain objective id")
            assert(O._active[1].text == text_before, "snapshot must retain objective text")
            assert(RT._root_panel == rt_root_before_refresh,
                "RT._root_panel must remain unchanged after refresh transition")
        ''')


    def test_render_readback_recovery_transition(self):
        """Render readback recovery: _verify_render detects geometry corruption,
        recovery, and text_rect corruption while geometry is unchanged.

        Enable foundation/objectives, mount RT root, activate one objective with
        normal text and amount. Assert _verify_render baseline true. Corrupt the
        owned text primitive geometry via set_shape(0,0,9999,9999) and assert
        _verify_render false. Restore the original x/y/w/h and assert true.
        Replace text:text_rect to return (0,0,99999,9999) and assert _verify_render
        false while primitive geometry remains at restored values.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local OM = _make_om()
            OM._objectives["readback"] = {
                id = "readback",
                text = "Normal objective text",
                amount = 1,
                current_amount = 0,
                sub_objectives = {},
            }
            OM:activate_objective("readback", nil, {amount = 1})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            O:mount(managers.hud)

            assert(type(O._panel) == "table", "O._panel must exist after mount")

            local baseline = O:_verify_render()
            assert(baseline == true,
                "baseline _verify_render must be true, got " .. tostring(baseline))

            local text_prim = O._panel:child("objective_1_text")
            assert(text_prim, "objective_1_text primitive must exist")

            local orig_x = text_prim:x()
            local orig_y = text_prim:y()
            local orig_w = text_prim:w()
            local orig_h = text_prim:h()

            text_prim:set_shape(0, 0, 9999, 9999)

            local after_corrupt = O:_verify_render()
            assert(after_corrupt == false,
                "_verify_render must be false after geometry corruption, got " .. tostring(after_corrupt))

            text_prim:set_shape(orig_x, orig_y, orig_w, orig_h)

            local after_restore = O:_verify_render()
            assert(after_restore == true,
                "_verify_render must be true after geometry restore, got " .. tostring(after_restore))

            local geom_w_after = text_prim:w()
            local geom_h_after = text_prim:h()
            assert(geom_w_after == orig_w,
                "text w must remain restored (" .. tostring(orig_w) .. "), got " .. tostring(geom_w_after))
            assert(geom_h_after == orig_h,
                "text h must remain restored (" .. tostring(orig_h) .. "), got " .. tostring(geom_h_after))

            function text_prim:text_rect()
                return 0, 0, 99999, 9999
            end

            local after_textrect = O:_verify_render()
            assert(after_textrect == false,
                "_verify_render must be false after text_rect corruption, got " .. tostring(after_textrect))
        ''')


    def test_stale_setter_cache_recovery_transition(self):
        """RED: Stale setter cache recovery through actual lifecycle.

        Enable foundation/objectives, mount RT and O, activate objective with
        amount=3, current=0. Verify initial _verify_render true. Replace amount
        primitive set_text with no-op. Native OM:complete_objective increments
        current to 1; _sync_primitives updates cache to "1/3" but primitive
        text remains "0/3". Assert _verify_render false and readback "0/3".
        Restore setter. Invoke RT:update at fresh bounded time (not manual
        _sync_primitives or mount repair); require primitive now "1/3" and
        _verify_render true.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect",
                text = "Collect bags",
                amount = 3,
                current_amount = 0,
                sub_objectives = {},
            }
            OM:activate_objective("collect", nil, {amount = 3})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            O:mount(managers.hud)

            assert(type(O._panel) == "table", "O._panel must exist after mount")

            local baseline = O:_verify_render()
            assert(baseline == true,
                "baseline _verify_render must be true, got " .. tostring(baseline))

            local amount_prim = O._panel:child("objective_1_amount")
            assert(amount_prim, "objective_1_amount primitive must exist")
            local initial_text = amount_prim:text()
            assert(initial_text == "0/3",
                "initial amount text must be '0/3', got " .. tostring(initial_text))

            local original_set_text = amount_prim.set_text
            function amount_prim:set_text(str) end

            OM:complete_objective("collect", nil)

            local after_stale = O:_verify_render()
            assert(after_stale == false,
                "_verify_render must be false after stale setter, got " .. tostring(after_stale))

            local stale_readback = amount_prim:text()
            assert(stale_readback == "0/3",
                "readback must still be '0/3', got " .. tostring(stale_readback))

            amount_prim.set_text = original_set_text

            RT:update(managers.hud, 1.0, 0.05)

            local recovered_text = amount_prim:text()
            assert(recovered_text == "1/3",
                "recovered amount text must be '1/3', got " .. tostring(recovered_text))

            local after_recovery = O:_verify_render()
            assert(after_recovery == true,
                "_verify_render must be true after recovery, got " .. tostring(after_recovery))
        ''')


    def test_owned_title_noop_setter_fit_cache_recovery(self):
        """RED: Owned title text no-op setter with previous fit cache.

        Enable foundation/objectives, mount RT and O, activate objective with
        text="First title", amount=3, current=0. Replace text primitive set_text
        with no-op. Update native source objective.text to "Second title". Invoke
        actual OM:complete_objective (amount 3 remains active, current increments
        to 1). Assert text primitive still shows "First title" (setter was no-op)
        and _verify_render false even though an old fit cache exists. Restore
        setter. Invoke RT:update at fresh bounded time. Assert primitive now
        shows "Second title" and _verify_render true. Same primitive identity
        throughout.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect",
                text = "First title",
                amount = 3,
                current_amount = 0,
                sub_objectives = {},
            }
            OM:activate_objective("collect", nil, {amount = 3})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            O:mount(managers.hud)

            assert(type(O._panel) == "table", "O._panel must exist after mount")

            local text_prim = O._panel:child("objective_1_text")
            assert(text_prim, "objective_1_text primitive must exist")
            local initial_text = text_prim:text()
            assert(initial_text == "First title",
                "initial text must be 'First title', got " .. tostring(initial_text))

            local baseline = O:_verify_render()
            assert(baseline == true,
                "baseline _verify_render must be true, got " .. tostring(baseline))

            local original_set_text = text_prim.set_text
            function text_prim:set_text(str) end

            OM._objectives["collect"].text = "Second title"

            OM:complete_objective("collect", nil)

            local after_stale = text_prim:text()
            assert(after_stale == "First title",
                "text primitive must still show 'First title' after no-op setter, got " .. tostring(after_stale))

            local stale_render = O:_verify_render()
            assert(stale_render == false,
                "_verify_render must be false after no-op setter, got " .. tostring(stale_render))

            text_prim.set_text = original_set_text

            RT:update(managers.hud, 1.0, 0.05)

            local recovered_text = text_prim:text()
            assert(recovered_text == "Second title",
                "recovered text must be 'Second title', got " .. tostring(recovered_text))

            local after_recovery = O:_verify_render()
            assert(after_recovery == true,
                "_verify_render must be true after recovery, got " .. tostring(after_recovery))

            local final_text_prim = O._panel:child("objective_1_text")
            assert(final_text_prim == text_prim,
                "text primitive must remain same instance throughout")
        ''')


    def test_dead_owned_amount_verify_render_fail_closed(self):
        """RED: Dead owned amount primitive must fail _verify_render closed.

        Enable foundation/objectives, mount RT and O, activate objective with
        text and amount=3, current=0. Verify _verify_render true and amount
        text "0/3". Remove objective_1_amount via its owned parent remove
        (fixture marks dead). Verify _verify_render false while dead/missing
        amount replacement. Invoke RT:update at fresh bounded time (no manual
        O mount or ensure repair). Verify amount recreated, same objective
        panel, amount text "0/3", _verify_render true.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect",
                text = "Collect bags",
                amount = 3,
                current_amount = 0,
                sub_objectives = {},
            }
            OM:activate_objective("collect", nil, {amount = 3})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            O:mount(managers.hud)

            assert(type(O._panel) == "table", "O._panel must exist after mount")

            local baseline = O:_verify_render()
            assert(baseline == true,
                "baseline _verify_render must be true, got " .. tostring(baseline))

            local amount_prim = O._panel:child("objective_1_amount")
            assert(amount_prim, "objective_1_amount primitive must exist")
            local initial_text = amount_prim:text()
            assert(initial_text == "0/3",
                "initial amount text must be '0/3', got " .. tostring(initial_text))

            local panel_before = O._panel

            O._panel:remove(amount_prim)

            assert(amount_prim._alive == false,
                "removed amount primitive must be marked dead")

            local after_dead = O:_verify_render()
            assert(after_dead == false,
                "_verify_render must be false while amount dead/missing, got " .. tostring(after_dead))

            RT:update(managers.hud, 1.0, 0.05)

            assert(O._panel == panel_before,
                "objective panel must remain same instance after RT:update")

            local recreated_prim = O._panel:child("objective_1_amount")
            assert(recreated_prim, "objective_1_amount must be recreated after RT:update")
            local recovered_text = recreated_prim:text()
            assert(recovered_text == "0/3",
                "recovered amount text must be '0/3', got " .. tostring(recovered_text))

            local after_recovery = O:_verify_render()
            assert(after_recovery == true,
                "_verify_render must be true after recovery, got " .. tostring(after_recovery))
        ''')


    def test_stale_visibility_cache_noop_setter_recovery(self):
        """RED: Stale visibility cache accepts no-op set_visible and never retries.

        Enable foundation/objectives, mount RT and O, activate objective with
        amount=1, current=0. Assert _verify_render true and amount visible() true.
        Replace amount primitive set_visible with no-op. Native OM:complete_objective
        finalizes (amount reaches current): O._active slot becomes empty, desired
        amount visibility becomes false. _sync_primitives calls no-op set_visible,
        updates cache to false, but primitive _visible remains true. Assert
        _verify_render false and primitive still visible. Restore original setter.
        Call RT:update at eligible time (t>=0.5, no direct O mount/sync/repair).
        Assert same panel and primitive identity, amount visible() false,
        _verify_render true. Current code does not re-apply visibility because
        cache already matches desired value, so this test fails (RED).
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect",
                text = "Collect bags",
                amount = 1,
                current_amount = 0,
                sub_objectives = {},
            }
            OM:activate_objective("collect", nil, {amount = 1})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            O:mount(managers.hud)

            assert(type(O._panel) == "table", "O._panel must exist after mount")

            local baseline = O:_verify_render()
            assert(baseline == true,
                "baseline _verify_render must be true, got " .. tostring(baseline))

            local amount_prim = O._panel:child("objective_1_amount")
            assert(amount_prim, "objective_1_amount primitive must exist")
            local initial_visible = amount_prim:visible()
            assert(initial_visible == true,
                "initial amount visible must be true, got " .. tostring(initial_visible))

            local panel_before = O._panel
            local prim_before = amount_prim

            local original_set_visible = amount_prim.set_visible
            function amount_prim:set_visible(v) end

            OM:remove_objective("collect", nil)

            local after_verify = O:_verify_render()
            assert(after_verify == false,
                "_verify_render must be false after no-op set_visible, got " .. tostring(after_verify))

            local stale_visible = amount_prim:visible()
            assert(stale_visible == true,
                "amount primitive must still be visible after no-op setter, got " .. tostring(stale_visible))

            amount_prim.set_visible = original_set_visible

            RT:update(managers.hud, 1.0, 0.05)

            assert(O._panel == panel_before,
                "objective panel must remain same instance after RT:update")

            local prim_after = O._panel:child("objective_1_amount")
            assert(prim_after == prim_before,
                "amount primitive must remain same instance after RT:update")

            local recovered_visible = amount_prim:visible()
            assert(recovered_visible == false,
                "recovered amount visible must be false, got " .. tostring(recovered_visible))

            local after_recovery = O:_verify_render()
            assert(after_recovery == true,
                "_verify_render must be true after recovery, got " .. tostring(after_recovery))
        ''')


    def test_set_font_size_noop_retry_via_update(self):
        """RED: set_font_size no-op -> retry via RT:update.

        Enable foundation/objectives, mount RT/O, seed active objective amount=1,
        at 1920x1080 scale=1.0. Assert _verify_render true and amount font_size 20.
        Replace amount primitive set_font_size with no-op. Change hud_scale to 1.05,
        RT:refresh_settings triggers _update_layout which attempts set_font_size(21)
        but no-op keeps it at 20. Assert amount font_size still 20, _verify_render
        false. Restore original setter, RT:update(managers.hud, 1.0, 0.05) with no
        O manual repair. Assert same primitive/root, amount font_size 21 and
        _verify_render true.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect",
                text = "Collect bags",
                amount = 1,
                current_amount = 0,
                sub_objectives = {},
            }
            OM:activate_objective("collect", nil, {amount = 1})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            O:mount(managers.hud)

            assert(type(O._panel) == "table", "O._panel must exist after mount")

            local baseline = O:_verify_render()
            assert(baseline == true,
                "baseline _verify_render must be true, got " .. tostring(baseline))

            local amount_prim = O._panel:child("objective_1_amount")
            assert(amount_prim, "objective_1_amount primitive must exist")
            local initial_fs = amount_prim:font_size()
            assert(initial_fs == 20,
                "initial amount font_size must be 20, got " .. tostring(initial_fs))

            local root_before = RT._root_panel
            local panel_before = O._panel
            local prim_before = amount_prim

            local original_set_font_size = amount_prim.set_font_size
            function amount_prim:set_font_size(s) end

            kyohud.settings.hud_scale = 1.05
            RT:refresh_settings(managers.hud)

            local stale_fs = amount_prim:font_size()
            assert(stale_fs == 20,
                "amount font_size must still be 20 after no-op setter, got " .. tostring(stale_fs))

            local after_stale = O:_verify_render()
            assert(after_stale == false,
                "_verify_render must be false after no-op set_font_size, got " .. tostring(after_stale))

            amount_prim.set_font_size = original_set_font_size

            RT:update(managers.hud, 1.0, 0.05)

            assert(RT._root_panel == root_before,
                "RT._root_panel must remain same instance after RT:update")
            assert(O._panel == panel_before,
                "objective panel must remain same instance after RT:update")

            local prim_after = O._panel:child("objective_1_amount")
            assert(prim_after == prim_before,
                "amount primitive must remain same instance after RT:update")

            local recovered_fs = amount_prim:font_size()
            assert(recovered_fs == 21,
                "recovered amount font_size must be 21, got " .. tostring(recovered_fs))

            local after_recovery = O:_verify_render()
            assert(after_recovery == true,
                "_verify_render must be true after recovery, got " .. tostring(after_recovery))
        ''')


    def test_invalid_font_readback_recovery_transition(self):
        """RED: Invalid font_size readback with runtime recovery.

        Enable foundation/objectives, mount RT and O, activate objective with
        amount=1, current=0. For each invalid font_size case (NaN, +infinity,
        missing getter, throwing getter): fresh _lua fixture, verify baseline
        _verify_render true and amount font_size 20. Override amount primitive
        font_size getter to return invalid value. Assert _verify_render false.
        Restore original getter. Invoke RT:update at t=1.0. Assert same panel
        and primitive identity, amount font_size 20, _verify_render true.
        NaN case: baseline code permits NaN through type/fs<=0 check (RED).
        """
        for invalid_case in ["nan", "inf", "missing", "throwing"]:
            with self.subTest(invalid_case=invalid_case):
                lua, ok = _lua()
                self.assertTrue(ok, "objectives production chunk missing")

                lua.execute(f'''
                    kyohud.settings.enable_hud_foundation = true
                    kyohud.settings.enable_objectives = true

                    local RT = kyohud.hud.runtime
                    RT:mount(managers.hud)

                    local OM = _make_om()
                    OM._objectives["collect"] = {{
                        id = "collect",
                        text = "Collect bags",
                        amount = 1,
                        current_amount = 0,
                        sub_objectives = {{}},
                    }}
                    OM:activate_objective("collect", nil, {{amount = 1}})

                    local O = kyohud.hud.objectives
                    assert(O, "O must exist")
                    O:mount(managers.hud)

                    assert(type(O._panel) == "table", "O._panel must exist after mount")

                    local baseline = O:_verify_render()
                    assert(baseline == true,
                        "baseline _verify_render must be true, got " .. tostring(baseline))

                    local amount_prim = O._panel:child("objective_1_amount")
                    assert(amount_prim, "objective_1_amount primitive must exist")
                    local initial_fs = amount_prim:font_size()
                    assert(initial_fs == 20,
                        "initial amount font_size must be 20, got " .. tostring(initial_fs))

                    local panel_before = O._panel
                    local prim_before = amount_prim

                    local original_font_size = amount_prim.font_size

                    if "{invalid_case}" == "nan" then
                        function amount_prim:font_size()
                            return 0/0
                        end
                    elseif "{invalid_case}" == "inf" then
                        function amount_prim:font_size()
                            return math.huge
                        end
                    elseif "{invalid_case}" == "missing" then
                        amount_prim.font_size = nil
                    elseif "{invalid_case}" == "throwing" then
                        function amount_prim:font_size()
                            error("getter fault")
                        end
                    end

                    local after_invalid = O:_verify_render()
                    assert(after_invalid == false,
                        "_verify_render must be false for {invalid_case} font_size, got " .. tostring(after_invalid))

                    amount_prim.font_size = original_font_size

                    RT:update(managers.hud, 1.0, 0.05)

                    assert(O._panel == panel_before,
                        "objective panel must remain same instance after RT:update")

                    local prim_after = O._panel:child("objective_1_amount")
                    assert(prim_after == prim_before,
                        "amount primitive must remain same instance after RT:update")

                    local recovered_fs = amount_prim:font_size()
                    assert(recovered_fs == 20,
                        "recovered amount font_size must be 20, got " .. tostring(recovered_fs))

                    local after_recovery = O:_verify_render()
                    assert(after_recovery == true,
                        "_verify_render must be true after recovery, got " .. tostring(after_recovery))
                ''')


    def test_amount_geometry_corrupt_noop_setter_recovery(self):
        """RED: Amount geometry corruption detected by _verify_render, no-op set_shape
        blocks repair, runtime retry recovery.

        Enable foundation/objectives, mount RT and O, activate objective with amount=1,
        current=0. For each axis (x, y, w, h): fresh fixture, verify baseline true,
        save original amount shape. Corrupt one axis (+40) via set_shape. Assert
        _verify_render false with axis in message (RED: current code doesn't verify
        amount geometry). Override amount set_shape to no-op. RT:refresh_settings
        attempts repair but fails (no-op). Assert amount geometry still corrupted and
        _verify_render false. Restore setter. RT:update at t=1.0 attempts repair.
        Assert same panel and primitive identity, exact original x/y/w/h, _verify_render
        true. Current production does not verify amount geometry, expected RED.
        """
        for axis in ["x", "y", "w", "h"]:
            with self.subTest(axis=axis):
                lua, ok = _lua()
                self.assertTrue(ok, "objectives production chunk missing")

                lua.execute(f'''
                    kyohud.settings.enable_hud_foundation = true
                    kyohud.settings.enable_objectives = true

                    local RT = kyohud.hud.runtime
                    RT:mount(managers.hud)

                    local OM = _make_om()
                    OM._objectives["collect"] = {{
                        id = "collect",
                        text = "Collect bags",
                        amount = 1,
                        current_amount = 0,
                        sub_objectives = {{}},
                    }}
                    OM:activate_objective("collect", nil, {{amount = 1}})

                    local O = kyohud.hud.objectives
                    assert(O, "O must exist")
                    O:mount(managers.hud)

                    assert(type(O._panel) == "table", "O._panel must exist after mount")

                    local baseline = O:_verify_render()
                    assert(baseline == true,
                        "baseline _verify_render must be true, got " .. tostring(baseline))

                    local amount_prim = O._panel:child("objective_1_amount")
                    assert(amount_prim, "objective_1_amount primitive must exist")

                    local orig_x = amount_prim:x()
                    local orig_y = amount_prim:y()
                    local orig_w = amount_prim:w()
                    local orig_h = amount_prim:h()

                    local panel_before = O._panel
                    local prim_before = amount_prim

                    local corrupt_x = orig_x
                    local corrupt_y = orig_y
                    local corrupt_w = orig_w
                    local corrupt_h = orig_h

                    if "{axis}" == "x" then
                        corrupt_x = orig_x + 40
                    elseif "{axis}" == "y" then
                        corrupt_y = orig_y + 40
                    elseif "{axis}" == "w" then
                        corrupt_w = orig_w + 40
                    elseif "{axis}" == "h" then
                        corrupt_h = orig_h + 40
                    end

                    amount_prim:set_shape(corrupt_x, corrupt_y, corrupt_w, corrupt_h)

                    local after_corrupt = O:_verify_render()
                    assert(after_corrupt == false,
                        "_verify_render must be false after {axis} geometry corruption, got " .. tostring(after_corrupt))

                    local original_set_shape = amount_prim.set_shape
                    function amount_prim:set_shape(x, y, w, h) end

                    RT:refresh_settings(managers.hud)

                    local after_noop_x = amount_prim:x()
                    local after_noop_y = amount_prim:y()
                    local after_noop_w = amount_prim:w()
                    local after_noop_h = amount_prim:h()
                    assert(after_noop_x == corrupt_x,
                        "amount x must still be corrupted after no-op, expected " .. tostring(corrupt_x) .. " got " .. tostring(after_noop_x))
                    assert(after_noop_y == corrupt_y,
                        "amount y must still be corrupted after no-op, expected " .. tostring(corrupt_y) .. " got " .. tostring(after_noop_y))
                    assert(after_noop_w == corrupt_w,
                        "amount w must still be corrupted after no-op, expected " .. tostring(corrupt_w) .. " got " .. tostring(after_noop_w))
                    assert(after_noop_h == corrupt_h,
                        "amount h must still be corrupted after no-op, expected " .. tostring(corrupt_h) .. " got " .. tostring(after_noop_h))

                    local after_noop_verify = O:_verify_render()
                    assert(after_noop_verify == false,
                        "_verify_render must be false after no-op repair attempt, got " .. tostring(after_noop_verify))

                    amount_prim.set_shape = original_set_shape

                    RT:update(managers.hud, 1.0, 0.05)

                    assert(O._panel == panel_before,
                        "objective panel must remain same instance after RT:update")

                    local prim_after = O._panel:child("objective_1_amount")
                    assert(prim_after == prim_before,
                        "amount primitive must remain same instance after RT:update")

                    local recovered_x = amount_prim:x()
                    local recovered_y = amount_prim:y()
                    local recovered_w = amount_prim:w()
                    local recovered_h = amount_prim:h()
                    assert(recovered_x == orig_x,
                        "recovered amount x must be " .. tostring(orig_x) .. ", got " .. tostring(recovered_x))
                    assert(recovered_y == orig_y,
                        "recovered amount y must be " .. tostring(orig_y) .. ", got " .. tostring(recovered_y))
                    assert(recovered_w == orig_w,
                        "recovered amount w must be " .. tostring(orig_w) .. ", got " .. tostring(recovered_w))
                    assert(recovered_h == orig_h,
                        "recovered amount h must be " .. tostring(orig_h) .. ", got " .. tostring(recovered_h))

                    local after_recovery = O:_verify_render()
                    assert(after_recovery == true,
                        "_verify_render must be true after recovery, got " .. tostring(after_recovery))
                ''')


    def test_amount_invalid_text_rect_recovery(self):
        """RED: Invalid amount text_rect readback with runtime recovery.

        Enable foundation/objectives, mount RT and O, activate objective with
        amount=3, current=0. For each invalid text_rect case (width99999,
        height99999, negative width, NaN width, inf height, throw): fresh _lua
        fixture, verify baseline _verify_render true and amount text "0/3".
        Override amount primitive text_rect getter to return invalid value.
        Assert _verify_render false. Restore original getter. Invoke RT:update
        at t=1.0. Assert same panel and primitive identity, amount text "0/3",
        _verify_render true. Natural fixture measurements must not clamp.
        """
        for invalid_case in ["width99999", "height99999", "neg_width", "nan_width", "inf_height", "throw"]:
            with self.subTest(invalid_case=invalid_case):
                lua, ok = _lua()
                self.assertTrue(ok, "objectives production chunk missing")

                lua.execute(f'''
                    kyohud.settings.enable_hud_foundation = true
                    kyohud.settings.enable_objectives = true

                    local RT = kyohud.hud.runtime
                    RT:mount(managers.hud)

                    local OM = _make_om()
                    OM._objectives["collect"] = {{
                        id = "collect",
                        text = "Collect bags",
                        amount = 3,
                        current_amount = 0,
                        sub_objectives = {{}},
                    }}
                    OM:activate_objective("collect", nil, {{amount = 3}})

                    local O = kyohud.hud.objectives
                    assert(O, "O must exist")
                    O:mount(managers.hud)

                    assert(type(O._panel) == "table", "O._panel must exist after mount")

                    local baseline = O:_verify_render()
                    assert(baseline == true,
                        "baseline _verify_render must be true, got " .. tostring(baseline))

                    local amount_prim = O._panel:child("objective_1_amount")
                    assert(amount_prim, "objective_1_amount primitive must exist")
                    local initial_text = amount_prim:text()
                    assert(initial_text == "0/3",
                        "initial amount text must be '0/3', got " .. tostring(initial_text))

                    local panel_before = O._panel
                    local prim_before = amount_prim

                    local original_text_rect = amount_prim.text_rect

                    if "{invalid_case}" == "width99999" then
                        function amount_prim:text_rect()
                            return 0, 0, 99999, 20
                        end
                    elseif "{invalid_case}" == "height99999" then
                        function amount_prim:text_rect()
                            return 0, 0, 100, 99999
                        end
                    elseif "{invalid_case}" == "neg_width" then
                        function amount_prim:text_rect()
                            return 0, 0, -50, 20
                        end
                    elseif "{invalid_case}" == "nan_width" then
                        function amount_prim:text_rect()
                            return 0, 0, 0/0, 20
                        end
                    elseif "{invalid_case}" == "inf_height" then
                        function amount_prim:text_rect()
                            return 0, 0, 100, math.huge
                        end
                    elseif "{invalid_case}" == "throw" then
                        function amount_prim:text_rect()
                            error("text_rect fault")
                        end
                    end

                    local after_invalid = O:_verify_render()
                    assert(after_invalid == false,
                        "_verify_render must be false for {invalid_case} text_rect, got " .. tostring(after_invalid))

                    amount_prim.text_rect = original_text_rect

                    RT:update(managers.hud, 1.0, 0.05)

                    assert(O._panel == panel_before,
                        "objective panel must remain same instance after RT:update")

                    local prim_after = O._panel:child("objective_1_amount")
                    assert(prim_after == prim_before,
                        "amount primitive must remain same instance after RT:update")

                    local recovered_text = amount_prim:text()
                    assert(recovered_text == "0/3",
                        "recovered amount text must be '0/3', got " .. tostring(recovered_text))

                    local after_recovery = O:_verify_render()
                    assert(after_recovery == true,
                        "_verify_render must be true after recovery, got " .. tostring(after_recovery))
                ''')


    def test_invalid_parent_dimensions_recovery_transition(self):
        """RED: Invalid parent dimensions recovery through runtime update.

        Enable foundation/objectives, mount RT and O, activate objective with
        amount=1, current=0. Verify baseline _verify_render true. Corrupt
        O._parent_panel (RT root, same parent) dimensions or w() method.
        Invoke RT:update at t=1.0. Assert _verify_render false (RED: baseline
        _update_layout returns early at pw<=0/non-finite/missing/throwing
        without invalidating old _layout_cache, so stale cache survives and
        _verify_render still reads valid primitives). Restore same parent
        dimension/getter. Invoke RT:update at t=2.0. Assert same O._panel,
        O._root_panel, text and amount primitive identities, _verify_render
        true. No O manual repair, no fixture logic/production methods.
        For numeric cases set parent._w; runtime mount early-returns so no
        automatic root repair masks the boundary.
        """
        for invalid_case in ["width_0", "width_neg1", "width_nan", "width_inf", "missing_w_getter", "throwing_w_getter"]:
            with self.subTest(invalid_case=invalid_case):
                lua, ok = _lua()
                self.assertTrue(ok, "objectives production chunk missing")

                lua.execute(f'''
                    kyohud.settings.enable_hud_foundation = true
                    kyohud.settings.enable_objectives = true

                    local RT = kyohud.hud.runtime
                    RT:mount(managers.hud)

                    local OM = _make_om()
                    OM._objectives["collect"] = {{
                        id = "collect",
                        text = "Collect bags",
                        amount = 1,
                        current_amount = 0,
                        sub_objectives = {{}},
                    }}
                    OM:activate_objective("collect", nil, {{amount = 1}})

                    local O = kyohud.hud.objectives
                    assert(O, "O must exist")
                    O:mount(managers.hud)

                    assert(type(O._panel) == "table", "O._panel must exist after mount")

                    local baseline = O:_verify_render()
                    assert(baseline == true,
                        "baseline _verify_render must be true, got " .. tostring(baseline))

                    local panel_before = O._panel
                    local root_before = O._root_panel
                    local text_prim_before = O._panel:child("objective_1_text")
                    local amount_prim_before = O._panel:child("objective_1_amount")
                    assert(text_prim_before, "objective_1_text primitive must exist")
                    assert(amount_prim_before, "objective_1_amount primitive must exist")

                    local parent = O._parent_panel
                    assert(parent, "O._parent_panel must exist")
                    assert(parent == RT._root_panel,
                        "O._parent_panel must be the RT-owned root (same parent)")

                    local original_w = parent._w

                    if "{invalid_case}" == "width_0" then
                        parent._w = 0
                    elseif "{invalid_case}" == "width_neg1" then
                        parent._w = -1
                    elseif "{invalid_case}" == "width_nan" then
                        parent._w = 0/0
                    elseif "{invalid_case}" == "width_inf" then
                        parent._w = math.huge
                    elseif "{invalid_case}" == "missing_w_getter" then
                        parent.w = nil
                    elseif "{invalid_case}" == "throwing_w_getter" then
                        function parent:w()
                            error("getter fault")
                        end
                    end

                    RT:update(managers.hud, 1.0, 0.05)

                    assert(O._panel == panel_before,
                        "objective panel must remain same instance after corrupt RT:update")
                    assert(O._root_panel == root_before,
                        "objective root panel must remain same instance after corrupt RT:update")

                    local text_prim_after = O._panel:child("objective_1_text")
                    local amount_prim_after = O._panel:child("objective_1_amount")
                    assert(text_prim_after == text_prim_before,
                        "text primitive must remain same instance after corrupt RT:update")
                    assert(amount_prim_after == amount_prim_before,
                        "amount primitive must remain same instance after corrupt RT:update")

                    local after_corrupt = O:_verify_render()
                    assert(after_corrupt == false,
                        "_verify_render must be false for {invalid_case} parent dimensions, got " .. tostring(after_corrupt))

                    if "{invalid_case}" == "missing_w_getter" or "{invalid_case}" == "throwing_w_getter" then
                        function parent:w() return self._w end
                    else
                        parent._w = original_w
                    end

                    RT:update(managers.hud, 2.0, 0.05)

                    assert(O._panel == panel_before,
                        "objective panel must remain same instance after recovery RT:update")
                    assert(O._root_panel == root_before,
                        "objective root panel must remain same instance after recovery RT:update")

                    local text_prim_recovered = O._panel:child("objective_1_text")
                    local amount_prim_recovered = O._panel:child("objective_1_amount")
                    assert(text_prim_recovered == text_prim_before,
                        "text primitive must remain same instance after recovery RT:update")
                    assert(amount_prim_recovered == amount_prim_before,
                        "amount primitive must remain same instance after recovery RT:update")

                    local after_recovery = O:_verify_render()
                    assert(after_recovery == true,
                        "_verify_render must be true after recovery, got " .. tostring(after_recovery))
                ''')


    def test_font_size_mutation_recovery_transition(self):
        """Font size mutation recovery through runtime update.

        Enable foundation/objectives, mount RT and O, activate objective with
        amount=3, current=0. For each primitive (title, amount): fresh fixture,
        verify baseline _verify_render true and font_size 20. Mutate font size
        to 99 (parent dimensions, settings, texts and layout unchanged). Assert
        _verify_render false. Call RT:update at t=1.0. Assert same panel and
        primitive identities, font_size 20, _verify_render true.
        """
        for prim_name in ["title", "amount"]:
            with self.subTest(prim_name=prim_name):
                lua, ok = _lua()
                self.assertTrue(ok, "objectives production chunk missing")

                lua.execute(f'''
                    kyohud.settings.enable_hud_foundation = true
                    kyohud.settings.enable_objectives = true

                    local RT = kyohud.hud.runtime
                    RT:mount(managers.hud)

                    local OM = _make_om()
                    OM._objectives["collect"] = {{
                        id = "collect",
                        text = "Collect bags",
                        amount = 3,
                        current_amount = 0,
                        sub_objectives = {{}},
                    }}
                    OM:activate_objective("collect", nil, {{amount = 3}})

                    local O = kyohud.hud.objectives
                    assert(O, "O must exist")
                    O:mount(managers.hud)

                    assert(type(O._panel) == "table", "O._panel must exist after mount")

                    local baseline = O:_verify_render()
                    assert(baseline == true,
                        "baseline _verify_render must be true, got " .. tostring(baseline))

                    local root_before = RT._root_panel
                    local panel_before = O._panel

                    local prim
                    if "{prim_name}" == "title" then
                        prim = O._panel:child("objective_1_text")
                    else
                        prim = O._panel:child("objective_1_amount")
                    end
                    assert(prim, "objective_1_{prim_name} primitive must exist")

                    local initial_fs = prim:font_size()
                    assert(initial_fs == 20,
                        "initial {prim_name} font_size must be 20, got " .. tostring(initial_fs))

                    prim:set_font_size(99)

                    local after_mutate_fs = prim:font_size()
                    assert(after_mutate_fs == 99,
                        "{prim_name} font_size must be 99 after mutation, got " .. tostring(after_mutate_fs))

                    local after_mutate = O:_verify_render()
                    assert(after_mutate == false,
                        "_verify_render must be false after font size mutation, got " .. tostring(after_mutate))

                    RT:update(managers.hud, 1.0, 0.05)

                    assert(RT._root_panel == root_before,
                        "RT._root_panel must remain same instance after RT:update")
                    assert(O._panel == panel_before,
                        "objective panel must remain same instance after RT:update")

                    local prim_after
                    if "{prim_name}" == "title" then
                        prim_after = O._panel:child("objective_1_text")
                    else
                        prim_after = O._panel:child("objective_1_amount")
                    end
                    assert(prim_after == prim,
                        "{prim_name} primitive must remain same instance after RT:update")

                    local recovered_fs = prim:font_size()
                    assert(recovered_fs == 20,
                        "recovered {prim_name} font_size must be 20, got " .. tostring(recovered_fs))

                    local after_recovery = O:_verify_render()
                    assert(after_recovery == true,
                        "_verify_render must be true after recovery, got " .. tostring(after_recovery))
                ''')


    def test_text_mutation_recovery_transition(self):
        """Text mutation recovery through runtime update.

        Enable foundation/objectives, mount RT and O, activate objective with
        amount=3, current=0. For each primitive (title, amount): fresh fixture,
        verify baseline _verify_render true and text content. Mutate text to
        "WRONG" via set_text (parent dimensions, settings, and layout unchanged).
        Assert _verify_render false. Call RT:update at t=1.0. Assert same panel
        and primitive identities, original expected text restored, _verify_render
        true.
        """
        for prim_name in ["title", "amount"]:
            with self.subTest(prim_name=prim_name):
                lua, ok = _lua()
                self.assertTrue(ok, "objectives production chunk missing")

                lua.execute(f'''
                    kyohud.settings.enable_hud_foundation = true
                    kyohud.settings.enable_objectives = true

                    local RT = kyohud.hud.runtime
                    RT:mount(managers.hud)

                    local OM = _make_om()
                    OM._objectives["collect"] = {{
                        id = "collect",
                        text = "Collect bags",
                        amount = 3,
                        current_amount = 0,
                        sub_objectives = {{}},
                    }}
                    OM:activate_objective("collect", nil, {{amount = 3}})

                    local O = kyohud.hud.objectives
                    assert(O, "O must exist")
                    O:mount(managers.hud)

                    assert(type(O._panel) == "table", "O._panel must exist after mount")

                    local baseline = O:_verify_render()
                    assert(baseline == true,
                        "baseline _verify_render must be true, got " .. tostring(baseline))

                    local root_before = RT._root_panel
                    local panel_before = O._panel

                    local prim
                    local expected_text
                    if "{prim_name}" == "title" then
                        prim = O._panel:child("objective_1_text")
                        expected_text = "Collect bags"
                    else
                        prim = O._panel:child("objective_1_amount")
                        expected_text = "0/3"
                    end
                    assert(prim, "objective_1_{prim_name} primitive must exist")

                    local initial_text = prim:text()
                    assert(initial_text == expected_text,
                        "initial {prim_name} text must be '" .. expected_text .. "', got " .. tostring(initial_text))

                    prim:set_text("WRONG")

                    local after_mutate_text = prim:text()
                    assert(after_mutate_text == "WRONG",
                        "{prim_name} text must be 'WRONG' after mutation, got " .. tostring(after_mutate_text))

                    local after_mutate = O:_verify_render()
                    assert(after_mutate == false,
                        "_verify_render must be false after text mutation, got " .. tostring(after_mutate))

                    RT:update(managers.hud, 1.0, 0.05)

                    assert(RT._root_panel == root_before,
                        "RT._root_panel must remain same instance after RT:update")
                    assert(O._panel == panel_before,
                        "objective panel must remain same instance after RT:update")

                    local prim_after
                    if "{prim_name}" == "title" then
                        prim_after = O._panel:child("objective_1_text")
                    else
                        prim_after = O._panel:child("objective_1_amount")
                    end
                    assert(prim_after == prim,
                        "{prim_name} primitive must remain same instance after RT:update")

                    local recovered_text = prim:text()
                    assert(recovered_text == expected_text,
                        "recovered {prim_name} text must be '" .. expected_text .. "', got " .. tostring(recovered_text))

                    local after_recovery = O:_verify_render()
                    assert(after_recovery == true,
                        "_verify_render must be true after recovery, got " .. tostring(after_recovery))
                ''')


    def test_visibility_mutation_recovery_transition(self):
        """Visibility mutation recovery through runtime update.

        Enable foundation/objectives, mount RT and O, activate objective with
        amount=3, current=0. For each primitive (title, amount): fresh fixture,
        verify baseline _verify_render true and visible() true. Mutate visibility
        to false via set_visible (parent dimensions, settings, and layout unchanged).
        Assert _verify_render false. Call RT:update at t=1.0. Assert same panel
        and primitive identities, visible() restored to true, _verify_render true.
        """
        for prim_name in ["title", "amount"]:
            with self.subTest(prim_name=prim_name):
                lua, ok = _lua()
                self.assertTrue(ok, "objectives production chunk missing")

                lua.execute(f'''
                    kyohud.settings.enable_hud_foundation = true
                    kyohud.settings.enable_objectives = true

                    local RT = kyohud.hud.runtime
                    RT:mount(managers.hud)

                    local OM = _make_om()
                    OM._objectives["collect"] = {{
                        id = "collect",
                        text = "Collect bags",
                        amount = 3,
                        current_amount = 0,
                        sub_objectives = {{}},
                    }}
                    OM:activate_objective("collect", nil, {{amount = 3}})

                    local O = kyohud.hud.objectives
                    assert(O, "O must exist")
                    O:mount(managers.hud)

                    assert(type(O._panel) == "table", "O._panel must exist after mount")

                    local baseline = O:_verify_render()
                    assert(baseline == true,
                        "baseline _verify_render must be true, got " .. tostring(baseline))

                    local root_before = RT._root_panel
                    local panel_before = O._panel

                    local prim
                    if "{prim_name}" == "title" then
                        prim = O._panel:child("objective_1_text")
                    else
                        prim = O._panel:child("objective_1_amount")
                    end
                    assert(prim, "objective_1_{prim_name} primitive must exist")

                    local initial_visible = prim:visible()
                    assert(initial_visible == true,
                        "initial {prim_name} visible must be true, got " .. tostring(initial_visible))

                    prim:set_visible(false)

                    local after_mutate_visible = prim:visible()
                    assert(after_mutate_visible == false,
                        "{prim_name} visible must be false after mutation, got " .. tostring(after_mutate_visible))

                    local after_mutate = O:_verify_render()
                    assert(after_mutate == false,
                        "_verify_render must be false after visibility mutation, got " .. tostring(after_mutate))

                    RT:update(managers.hud, 1.0, 0.05)

                    assert(RT._root_panel == root_before,
                        "RT._root_panel must remain same instance after RT:update")
                    assert(O._panel == panel_before,
                        "objective panel must remain same instance after RT:update")

                    local prim_after
                    if "{prim_name}" == "title" then
                        prim_after = O._panel:child("objective_1_text")
                    else
                        prim_after = O._panel:child("objective_1_amount")
                    end
                    assert(prim_after == prim,
                        "{prim_name} primitive must remain same instance after RT:update")

                    local recovered_visible = prim:visible()
                    assert(recovered_visible == true,
                        "recovered {prim_name} visible must be true, got " .. tostring(recovered_visible))

                    local after_recovery = O:_verify_render()
                    assert(after_recovery == true,
                        "_verify_render must be true after recovery, got " .. tostring(after_recovery))
                ''')


    def test_load_saved_active_quantitative_objective(self):
        """Characterization: OM:load with saved active quantitative objective.

        Seed OM with objective. Call OM:load with objective_map containing
        active=true, current_amount=1, amount=3, sub_objective={}, completed_ordered={}.
        Assert O._active has 1 entry with current_amount=1, amount=3. RT:update lifecycle
        verifies rendered quantity "1/3" and _verify_render true; no duplicate active entries.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local OM = _make_om()
            OM._completed_objectives = {}
            OM._read_objectives = {}
            OM._objectives["collect"] = {
                id = "collect",
                text = "Collect bags",
                amount = 3,
                current_amount = 0,
                sub_objectives = {},
            }

            local load_data = {
                ObjectivesManager = {
                    completed_objectives_ordered = {},
                    objective_map = {
                        collect = {
                            active = true,
                            current_amount = 1,
                            amount = 3,
                            sub_objective = {},
                        },
                    },
                },
            }
            OM:load(load_data)

            assert(OM._active_objectives["collect"] ~= nil, "registry must contain collect")
            assert(OM._objectives["collect"].current_amount == 1, "native current_amount must be 1")
            assert(OM._objectives["collect"].amount == 3, "native amount must be 3")

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O._active) == "table", "O._active must be table")
            assert(#O._active == 1, "O._active must have 1 entry, got " .. #O._active)
            local entry = O._active[1]
            assert(entry.id == "collect", "entry id must be collect")
            assert(entry.current_amount == 1, "entry current_amount must be 1, got " .. tostring(entry.current_amount))
            assert(entry.amount == 3, "entry amount must be 3, got " .. tostring(entry.amount))

            RT:update(managers.hud, 1.0, 0.05)

            assert(type(O._panel) == "table", "O._panel must exist after mount")
            local amount_prim = O._panel:child("objective_1_amount")
            assert(amount_prim, "objective_1_amount primitive must exist")
            local amount_text = amount_prim:text()
            assert(amount_text == "1/3", "amount text must be '1/3', got " .. tostring(amount_text))

            local vr1 = O:_verify_render()
            assert(vr1 == true, "_verify_render must be true, got " .. tostring(vr1))

            local count = #O._active
            assert(count == 1, "no duplicate active entries, got " .. count)
        ''')

    def test_load_saved_countdown_objective(self):
        """Characterization: OM:load with saved countdown objective.

        Seed OM with objective. Call OM:load with objective_map containing
        active=true, countdown=true, current_amount=1, amount=3, sub_objective={},
        completed_ordered={}. Assert O._active has 1 entry with current_amount=2
        (display remaining = amount - current_amount = 3-1), amount=3, countdown=true.
        RT:update lifecycle verifies rendered quantity "2/3" and _verify_render true;
        no duplicate active entries.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local OM = _make_om()
            OM._completed_objectives = {}
            OM._read_objectives = {}
            OM._objectives["defuse"] = {
                id = "defuse",
                text = "Defuse the bomb",
                amount = 3,
                current_amount = 0,
                sub_objectives = {},
            }

            local load_data = {
                ObjectivesManager = {
                    completed_objectives_ordered = {},
                    objective_map = {
                        defuse = {
                            active = true,
                            countdown = true,
                            current_amount = 1,
                            amount = 3,
                            sub_objective = {},
                        },
                    },
                },
            }
            OM:load(load_data)

            assert(OM._active_objectives["defuse"] ~= nil, "registry must contain defuse")
            assert(OM._objectives["defuse"].current_amount == 1, "native current_amount must be 1")
            assert(OM._objectives["defuse"].amount == 3, "native amount must be 3")
            assert(OM._objectives["defuse"].countdown == true, "native countdown must be true")

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(type(O._active) == "table", "O._active must be table")
            assert(#O._active == 1, "O._active must have 1 entry, got " .. #O._active)
            local entry = O._active[1]
            assert(entry.id == "defuse", "entry id must be defuse")
            assert(entry.current_amount == 2, "entry current_amount must be 2 (3-1), got " .. tostring(entry.current_amount))
            assert(entry.amount == 3, "entry amount must be 3, got " .. tostring(entry.amount))
            assert(entry.countdown == true, "entry countdown must be true")

            RT:update(managers.hud, 1.0, 0.05)

            assert(type(O._panel) == "table", "O._panel must exist after mount")
            local amount_prim = O._panel:child("objective_1_amount")
            assert(amount_prim, "objective_1_amount primitive must exist")
            local amount_text = amount_prim:text()
            assert(amount_text == "2/3", "amount text must be '2/3', got " .. tostring(amount_text))

            local vr2 = O:_verify_render()
            assert(vr2 == true, "_verify_render must be true, got " .. tostring(vr2))

            local count = #O._active
            assert(count == 1, "no duplicate active entries, got " .. count)
        ''')


    def test_root_visibility_regression(self):
        """RED: Root visibility regression.

        Enable foundation/objectives, mount RT and O, activate objective with
        amount=3, current=0. Verify baseline _verify_render true. Save O._root_panel
        identity. Set O._root_panel:set_visible(false). Assert _verify_render false.
        Invoke RT:update at eligible time (t>=0.5). Assert root visible() true, same
        instance, _verify_render true. Production _verify_render currently omits root
        visible readback, so this test fails (RED).
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect",
                text = "Collect bags",
                amount = 3,
                current_amount = 0,
                sub_objectives = {},
            }
            OM:activate_objective("collect", nil, {amount = 3})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            O:mount(managers.hud)

            assert(type(O._panel) == "table", "O._panel must exist after mount")

            local baseline = O:_verify_render()
            assert(baseline == true,
                "baseline _verify_render must be true, got " .. tostring(baseline))

            local root_before = O._root_panel
            assert(root_before, "O._root_panel must exist")

            root_before:set_visible(false)

            local root_visible = root_before:visible()
            assert(root_visible == false,
                "root visible must be false after set_visible(false), got " .. tostring(root_visible))

            local after_hide = O:_verify_render()
            assert(after_hide == false,
                "_verify_render must be false after root hidden, got " .. tostring(after_hide))

            RT:update(managers.hud, 1.0, 0.05)

            local root_after = O._root_panel
            assert(root_after == root_before,
                "O._root_panel must remain same instance after RT:update")

            local recovered_visible = root_after:visible()
            assert(recovered_visible == true,
                "root visible must be true after RT:update, got " .. tostring(recovered_visible))

            local after_recovery = O:_verify_render()
            assert(after_recovery == true,
                "_verify_render must be true after recovery, got " .. tostring(after_recovery))
        ''')


    def test_native_reset_clears_active_preserves_panel_identity(self):
        """Native OM:reset clears registry; immediately O._active is empty,
        owned title/amount are empty/hidden, owned panel identity remains,
        O._manager remains HUDManager identity, RT generations and sentinel
        unchanged. No O manual reset/snapshot/update/mount called.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect",
                text = "Collect bags",
                amount = 1,
                current_amount = 0,
                sub_objectives = {},
            }
            OM:activate_objective("collect", nil, {amount = 1})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            O:mount(managers.hud)

            assert(type(O._panel) == "table", "O._panel must exist after mount")
            assert(#O._active == 1, "O._active must have 1 entry before reset")

            local title_prim = O._panel:child("objective_1_text")
            local amount_prim = O._panel:child("objective_1_amount")
            assert(title_prim, "objective_1_text primitive must exist")
            assert(amount_prim, "objective_1_amount primitive must exist")
            local title_before = title_prim:text()
            local amount_before = amount_prim:text()
            assert(title_before == "Collect bags",
                "title text must be 'Collect bags' before reset, got " .. tostring(title_before))
            assert(amount_before == "0/1",
                "amount text must be '0/1' before reset, got " .. tostring(amount_before))
            assert(title_prim:visible() == true,
                "title must be visible before reset")
            assert(amount_prim:visible() == true,
                "amount must be visible before reset")

            local hud_mgr = managers.hud
            local root_identity = O._root_panel
            local panel_identity = O._panel
            local rt_gen_before = RT._generation
            local heist_gen_before = RT._heist_generation
            kyohud.killstreak = 42
            local sentinel_before = kyohud.killstreak

            OM:reset()

            local active_count = 0
            for _ in pairs(OM._active_objectives) do active_count = active_count + 1 end
            assert(active_count == 0,
                "registry must be empty after reset, got " .. active_count)

            assert(#O._active == 0,
                "O._active must be empty immediately after reset, got " .. #O._active)

            assert(O._panel == panel_identity,
                "O._panel must remain same instance after reset")
            assert(O._root_panel == root_identity,
                "O._root_panel must remain same instance after reset")

            assert(O._manager == hud_mgr,
                "O._manager must remain HUDManager identity, got " .. tostring(O._manager))

            assert(RT._generation == rt_gen_before,
                "RT._generation must remain " .. tostring(rt_gen_before) ..
                ", got " .. tostring(RT._generation))
            assert(RT._heist_generation == heist_gen_before,
                "RT._heist_generation must remain " .. tostring(heist_gen_before) ..
                ", got " .. tostring(RT._heist_generation))

            assert(kyohud.killstreak == sentinel_before,
                "sentinel must remain " .. tostring(sentinel_before) ..
                ", got " .. tostring(kyohud.killstreak))

            local title_prim_after = O._panel:child("objective_1_text")
            local amount_prim_after = O._panel:child("objective_1_amount")
            assert(title_prim_after == title_prim,
                "title primitive must remain same instance")
            assert(amount_prim_after == amount_prim,
                "amount primitive must remain same instance")

            local title_after = title_prim_after:text()
            assert(title_after == "",
                "title text must be empty after reset, got " .. tostring(title_after))
            assert(title_prim_after:visible() == false,
                "title must be hidden after reset, got " .. tostring(title_prim_after:visible()))

            local amount_after = amount_prim_after:text()
            assert(amount_after == "",
                "amount text must be empty after reset, got " .. tostring(amount_after))
            assert(amount_prim_after:visible() == false,
                "amount must be hidden after reset, got " .. tostring(amount_prim_after:visible()))
        ''')


    def test_manager_identity_reset_rebind(self):
        """Manager identity on reset: OM1 activates, OM2 rebinds (empty),
        OM2:reset clears O._active/_by_id, binds _snapshot_manager==OM2,
        clears/hides texts, keeps identities/generations/sentinel. OM2 then
        activates fresh objective; assert positive fresh state. Stale OM1:reset
        must not change fresh snapshot/render/binding. No manual repair/update.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local OM1 = _make_om()
            OM1._objectives["old_obj"] = {
                id = "old_obj",
                text = "Old objective text",
                amount = 1,
                current_amount = 0,
                sub_objectives = {},
            }
            OM1:activate_objective("old_obj", nil, {amount = 1})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            O:mount(managers.hud)

            assert(type(O._panel) == "table", "O._panel must exist after mount")
            assert(#O._active == 1, "O._active must have 1 entry before OM2 rebind")

            local panel_before = O._panel
            local title_prim_before = O._panel:child("objective_1_text")
            local amount_prim_before = O._panel:child("objective_1_amount")
            assert(title_prim_before, "objective_1_text primitive must exist")
            assert(amount_prim_before, "objective_1_amount primitive must exist")
            local title_before = title_prim_before:text()
            local amount_before = amount_prim_before:text()
            assert(title_before == "Old objective text",
                "title text must match before OM2 rebind, got " .. tostring(title_before))
            assert(amount_before == "0/1",
                "amount text must be '0/1' before OM2 rebind, got " .. tostring(amount_before))

            local hud_mgr_before = managers.hud
            local rt_gen_before = RT._generation
            local heist_gen_before = RT._heist_generation
            kyohud.killstreak = 99
            local sentinel_before = kyohud.killstreak

            local OM2 = _make_om()

            OM2:reset()

            local active_count = 0
            for _ in pairs(O._active) do active_count = active_count + 1 end
            assert(active_count == 0,
                "O._active must be empty after OM2:reset, got " .. active_count)

            local by_id_count = 0
            for _ in pairs(O._by_id) do by_id_count = by_id_count + 1 end
            assert(by_id_count == 0,
                "O._by_id must be empty after OM2:reset, got " .. by_id_count)

            assert(O._snapshot_manager == OM2,
                "O._snapshot_manager must be OM2 after OM2:reset, got " .. tostring(O._snapshot_manager))

            assert(O._panel == panel_before,
                "O._panel must remain same instance after OM2:reset")

            local title_prim_after_reset = O._panel:child("objective_1_text")
            local amount_prim_after_reset = O._panel:child("objective_1_amount")
            assert(title_prim_after_reset == title_prim_before,
                "title primitive must remain same instance after OM2:reset")
            assert(amount_prim_after_reset == amount_prim_before,
                "amount primitive must remain same instance after OM2:reset")

            local title_after_reset = title_prim_after_reset:text()
            assert(title_after_reset == "",
                "title text must be empty after OM2:reset, got " .. tostring(title_after_reset))
            assert(title_prim_after_reset:visible() == false,
                "title must be hidden after OM2:reset, got " .. tostring(title_prim_after_reset:visible()))

            local amount_after_reset = amount_prim_after_reset:text()
            assert(amount_after_reset == "",
                "amount text must be empty after OM2:reset, got " .. tostring(amount_after_reset))
            assert(amount_prim_after_reset:visible() == false,
                "amount must be hidden after OM2:reset, got " .. tostring(amount_prim_after_reset:visible()))

            assert(managers.hud == hud_mgr_before,
                "managers.hud identity must remain after OM2:reset")
            assert(RT._generation == rt_gen_before,
                "RT._generation must remain " .. tostring(rt_gen_before) ..
                " after OM2:reset, got " .. tostring(RT._generation))
            assert(RT._heist_generation == heist_gen_before,
                "RT._heist_generation must remain " .. tostring(heist_gen_before) ..
                " after OM2:reset, got " .. tostring(RT._heist_generation))
            assert(kyohud.killstreak == sentinel_before,
                "sentinel must remain " .. tostring(sentinel_before) ..
                " after OM2:reset, got " .. tostring(kyohud.killstreak))

            OM2._objectives["fresh_obj"] = {
                id = "fresh_obj",
                text = "Fresh objective text",
                amount = 2,
                current_amount = 0,
                sub_objectives = {},
            }
            OM2:activate_objective("fresh_obj", nil, {amount = 2})

            assert(#O._active == 1,
                "O._active must have 1 entry after OM2 activate, got " .. #O._active)
            assert(O._active[1].id == "fresh_obj",
                "O._active[1] id must be fresh_obj, got " .. tostring(O._active[1].id))
            assert(O._active[1].text == "Fresh objective text",
                "O._active[1] text must match, got " .. tostring(O._active[1].text))
            assert(O._active[1].amount == 2,
                "O._active[1] amount must be 2, got " .. tostring(O._active[1].amount))
            assert(O._active[1].current_amount == 0,
                "O._active[1] current_amount must be 0, got " .. tostring(O._active[1].current_amount))

            local title_prim_before_stale = O._panel:child("objective_1_text")
            local amount_prim_before_stale = O._panel:child("objective_1_amount")
            assert(title_prim_before_stale == title_prim_before,
                "title primitive must remain same instance before stale OM1:reset")
            assert(amount_prim_before_stale == amount_prim_before,
                "amount primitive must remain same instance before stale OM1:reset")

            local snapshot_mgr_before_stale = O._snapshot_manager
            local active_id_before_stale = O._active[1].id
            local active_text_before_stale = O._active[1].text

            OM1:reset()

            assert(O._snapshot_manager == snapshot_mgr_before_stale,
                "O._snapshot_manager must remain OM2 after stale OM1:reset, got " .. tostring(O._snapshot_manager))
            assert(#O._active == 1,
                "O._active must still have 1 entry after stale OM1:reset, got " .. #O._active)
            assert(O._active[1].id == active_id_before_stale,
                "O._active[1] id must remain fresh_obj after stale OM1:reset, got " .. tostring(O._active[1].id))
            assert(O._active[1].text == active_text_before_stale,
                "O._active[1] text must remain unchanged after stale OM1:reset, got " .. tostring(O._active[1].text))

            local title_prim_after_stale = O._panel:child("objective_1_text")
            local amount_prim_after_stale = O._panel:child("objective_1_amount")
            assert(title_prim_after_stale == title_prim_before,
                "title primitive must remain same instance after stale OM1:reset")
            assert(amount_prim_after_stale == amount_prim_before,
                "amount primitive must remain same instance after stale OM1:reset")

            local title_after_stale = title_prim_after_stale:text()
            assert(title_after_stale == "Fresh objective text",
                "title text must remain 'Fresh objective text' after stale OM1:reset, got " .. tostring(title_after_stale))
            local amount_after_stale = amount_prim_after_stale:text()
            assert(amount_after_stale == "0/2",
                "amount text must remain '0/2' after stale OM1:reset, got " .. tostring(amount_after_stale))

            local vr = O:_verify_render()
            assert(vr == true,
                "_verify_render must be true after stale OM1:reset, got " .. tostring(vr))

            assert(O._panel == panel_before,
                "O._panel must remain same instance throughout")
            assert(managers.hud == hud_mgr_before,
                "managers.hud identity must remain throughout")
            assert(RT._generation == rt_gen_before,
                "RT._generation must remain throughout")
            assert(RT._heist_generation == heist_gen_before,
                "RT._heist_generation must remain throughout")
            assert(kyohud.killstreak == sentinel_before,
                "sentinel must remain throughout")
        ''')


    def test_remove_and_activate_objective_transition(self):
        """Characterization: native OM:remove_and_activate_objective with two
        preexisting active objectives. New objective replaces both with delayed
        presentation. Previous titles/quantities cleared and hidden immediately.
        After delay expires, new objective ready with same panels/primitives.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local OM = _make_om()
            OM._objectives["old1"] = {
                id = "old1",
                text = "First objective",
                amount = 1,
                current_amount = 0,
                sub_objectives = {},
            }
            OM._objectives["old2"] = {
                id = "old2",
                text = "Second objective",
                amount = 2,
                current_amount = 0,
                sub_objectives = {},
            }
            OM._objectives["new_id"] = {
                id = "new_id",
                text = "New objective title",
                amount = 3,
                current_amount = 0,
                sub_objectives = {},
            }

            OM:activate_objective("old1", nil, {amount = 1})
            OM:activate_objective("old2", nil, {amount = 2})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            O:mount(managers.hud)

            assert(type(O._panel) == "table", "O._panel must exist after mount")
            assert(#O._active == 2, "O._active must have 2 entries before replacement, got " .. #O._active)

            local panel_before = O._panel
            local title_prim_before = O._panel:child("objective_1_text")
            local amount_prim_before = O._panel:child("objective_1_amount")
            assert(title_prim_before, "objective_1_text primitive must exist")
            assert(amount_prim_before, "objective_1_amount primitive must exist")

            local baseline_title_text = title_prim_before:text()
            assert(baseline_title_text == "Second objective",
                "baseline title must be 'Second objective', got " .. tostring(baseline_title_text))
            assert(title_prim_before:visible() == true,
                "baseline title must be visible, got " .. tostring(title_prim_before:visible()))

            local baseline_amount_text = amount_prim_before:text()
            assert(baseline_amount_text == "0/2",
                "baseline amount must be '0/2', got " .. tostring(baseline_amount_text))
            assert(amount_prim_before:visible() == true,
                "baseline amount must be visible, got " .. tostring(amount_prim_before:visible()))

            local baseline_vr = O:_verify_render()
            assert(baseline_vr == true,
                "baseline _verify_render must be true, got " .. tostring(baseline_vr))

            OM:remove_and_activate_objective("new_id", nil, {amount = 3})

            assert(#O._active == 1, "O._active must have 1 entry after replacement, got " .. #O._active)
            assert(O._active[1].id == "new_id", "only active must be new_id, got " .. tostring(O._active[1].id))
            assert(O._active[1].pending == true, "new_id must be pending, got " .. tostring(O._active[1].pending))

            assert(OM._delayed_presentation, "OM._delayed_presentation must exist")
            assert(OM._delayed_presentation.activate_params.id == "new_id",
                "delayed payload id must be new_id, got " .. tostring(OM._delayed_presentation.activate_params.id))

            local title_prim_after = O._panel:child("objective_1_text")
            local amount_prim_after = O._panel:child("objective_1_amount")
            assert(title_prim_after == title_prim_before, "title primitive must remain same instance")
            assert(amount_prim_after == amount_prim_before, "amount primitive must remain same instance")

            local title_text = title_prim_after:text()
            assert(title_text == "", "title text must be empty after replacement, got " .. tostring(title_text))
            assert(title_prim_after:visible() == false, "title must be hidden after replacement, got " .. tostring(title_prim_after:visible()))

            local amount_text = amount_prim_after:text()
            assert(amount_text == "", "amount text must be empty after replacement, got " .. tostring(amount_text))
            assert(amount_prim_after:visible() == false, "amount must be hidden after replacement, got " .. tostring(amount_prim_after:visible()))

            OM:update(0, 0.5)
            assert(O._active[1].pending == true, "new_id must still be pending after first update, got " .. tostring(O._active[1].pending))
            local sel1 = O:select_visible()
            assert(#sel1 == 0, "select_visible must return 0 after first update, got " .. #sel1)

            OM:update(1, 0.6)

            assert(O._active[1].pending == false, "new_id must no longer be pending after delay expires, got " .. tostring(O._active[1].pending))
            local sel2 = O:select_visible()
            assert(#sel2 == 1, "select_visible must return 1 after delay expires, got " .. #sel2)
            assert(sel2[1].id == "new_id", "returned objective must be new_id, got " .. tostring(sel2[1].id))

            local title_after_relay = title_prim_after:text()
            assert(title_after_relay == "New objective title",
                "title text must be 'New objective title' after relay, got " .. tostring(title_after_relay))
            assert(title_prim_after:visible() == true, "title must be visible after relay, got " .. tostring(title_prim_after:visible()))

            local amount_after_relay = amount_prim_after:text()
            assert(amount_after_relay == "0/3",
                "amount text must be '0/3' after relay, got " .. tostring(amount_after_relay))
            assert(amount_prim_after:visible() == true, "amount must be visible after relay, got " .. tostring(amount_prim_after:visible()))

            assert(O._panel == panel_before, "O._panel must remain same instance throughout")

            local vr = O:_verify_render()
            assert(vr == true, "_verify_render must be true after relay, got " .. tostring(vr))
        ''')


    def test_native_reminder_delivers_both_hud_calls(self):
        """Characterization: native _remind_objetive fires both
        HUDManager:present_mid_text and HUDManager:remind_objective with
        correct id/text/title. Native next_t updated. O order a,b and
        selected b unchanged. Rendered b unchanged, same primitives.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true
            kyohud.settings.objectives_visible_limit = 1

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local OM = _make_om()
            OM._objectives["a"] = {
                id = "a", text = "Older objective", amount = nil, current_amount = nil, sub_objectives = {},
            }
            OM._objectives["b"] = {
                id = "b", text = "Newer objective", amount = nil, current_amount = nil, sub_objectives = {},
            }

            OM:activate_objective("a", nil, {})
            OM:activate_objective("b", nil, {})

            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            O:mount(managers.hud)

            assert(type(O._panel) == "table", "O._panel must exist after mount")
            assert(#O._active == 2, "O._active must have 2 entries, got " .. #O._active)
            assert(O._active[1].id == "a", "first must be a, got " .. tostring(O._active[1].id))
            assert(O._active[2].id == "b", "second must be b, got " .. tostring(O._active[2].id))

            local sel_before = O:select_visible()
            assert(#sel_before == 1, "select_visible must return 1 (limit 1), got " .. #sel_before)
            assert(sel_before[1].id == "b", "selected must be b (newer), got " .. tostring(sel_before[1].id))

            local panel_before = O._panel
            local title_prim_before = O._panel:child("objective_1_text")
            assert(title_prim_before, "objective_1_text primitive must exist")
            local title_text_before = title_prim_before:text()
            assert(title_text_before == "Newer objective",
                "rendered title must be 'Newer objective', got " .. tostring(title_text_before))

            local baseline_vr = O:_verify_render()
            assert(baseline_vr == true,
                "baseline _verify_render must be true, got " .. tostring(baseline_vr))

            _obs_remind = {}
            _obs_mid = {}
            Hooks:PostHook(HUDManager, "remind_objective", "test_obs_remind", function(self, id)
                _obs_remind.id = id
            end)
            Hooks:PostHook(HUDManager, "present_mid_text", "test_obs_mid", function(self, data)
                _obs_mid.time = data.time
                _obs_mid.text = data.text
                _obs_mid.title = data.title
            end)

            OM._remind_objectives["a"] = {next_t = 0}

            Application._time = 100
            OM:update(1, 0.05)

            assert(_obs_remind.id == "a",
                "remind_objective must fire with id=a, got " .. tostring(_obs_remind.id))
            assert(_obs_mid.text == "Older objective",
                "present_mid_text text must be 'Older objective', got " .. tostring(_obs_mid.text))
            assert(_obs_mid.title == "Loc:hud_objective_reminder",
                "present_mid_text title must be 'Loc:hud_objective_reminder', got " .. tostring(_obs_mid.title))
            assert(_obs_mid.time == 4,
                "present_mid_text time must be 4, got " .. tostring(_obs_mid.time))

            assert(OM._remind_objectives["a"].next_t == 100 + OM.REMINDER_INTERVAL,
                "next_t must be updated to Application:time() + REMINDER_INTERVAL, got " .. tostring(OM._remind_objectives["a"].next_t))

            assert(#O._active == 2, "O._active must still have 2 entries, got " .. #O._active)
            assert(O._active[1].id == "a", "first must still be a, got " .. tostring(O._active[1].id))
            assert(O._active[2].id == "b", "second must still be b, got " .. tostring(O._active[2].id))

            local sel_after = O:select_visible()
            assert(#sel_after == 1, "select_visible must still return 1, got " .. #sel_after)
            assert(sel_after[1].id == "b", "selected must still be b, got " .. tostring(sel_after[1].id))

            assert(O._panel == panel_before,
                "O._panel must remain same instance, got " .. tostring(O._panel))
            local title_prim_after = O._panel:child("objective_1_text")
            assert(title_prim_after == title_prim_before,
                "title primitive must remain same instance")
            local title_text_after = title_prim_after:text()
            assert(title_text_after == title_text_before,
                "rendered title must remain '" .. title_text_before .. "', got " .. tostring(title_text_after))

            local vr = O:_verify_render()
            assert(vr == true,
                "_verify_render must remain true, got " .. tostring(vr))
        ''')


    def test_registration_context_characterization(self):
        """Registration/context characterization: exact hook triples per RequiredScript.

        Fresh LuaRuntime with STUBS/DIESEL only (no _lua which pre-installs).
        1. Load objectives.lua with unknown RequiredScript: no hooks registered,
           O state (kyohud.hud.objectives) initialized.
        2. Load with hudmanagerpd2 twice: exactly 2 HUD hook triples
           (HUDManager/activate_objective/KyohUD_HUD_ActivateObjective,
           HUDManager/complete_objective/KyohUD_HUD_CompleteObjective) each once,
           same O state identity across both loads.
        3. Load with objectivesmanager twice: exactly 7 OM hook triples each once
           (ObjectivesManager/method/KyohUD_OM_* for activate, activate_countdown,
           remove, complete, complete_countdown, complete_sub, reset), plus HUD
           hooks from step 2 still present, no duplication across all loads.
        4. Negative: no unrelated hook IDs in Hooks._all.
        """
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute(STUBS)
        lua.execute(DIESEL)

        obj_src = _read(OBJECTIVES_PATH)
        self.assertIsNotNone(obj_src, "objectives production chunk missing")

        # Step 1: unknown context
        lua.execute('RequiredScript = "lib/units/unknown_context"')
        lua.execute(obj_src)
        lua.execute('''
            _unknown_hooks = 0
            for _, e in ipairs(Hooks._all) do
                if e.id and string.sub(e.id, 1, 7) == "KyohUD_" then
                    _unknown_hooks = _unknown_hooks + 1
                end
            end
            _o_initialized = (kyohud.hud.objectives ~= nil)
            _o_identity_1 = kyohud.hud.objectives
            kyohud.hud.objectives._sentinel_registration = {}
            _sentinel_1 = kyohud.hud.objectives._sentinel_registration
        ''')
        self.assertEqual(lua.globals()._unknown_hooks, 0,
            "unknown RequiredScript must not register any KyohUD_ hooks")
        self.assertTrue(bool(lua.globals()._o_initialized),
            "O state must be initialized even under unknown context")

        # Step 2: hudmanagerpd2 twice
        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        lua.execute(obj_src)
        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        lua.execute(obj_src)
        lua.execute('''
            _hud_triples = {}
            _hud_count = 0
            _hud_dupes = 0
            _hud_seen = {}
            for _, e in ipairs(Hooks._all) do
                if e.class == HUDManager and (e.method == "activate_objective" or e.method == "complete_objective") then
                    _hud_count = _hud_count + 1
                    local key = e.method .. "." .. e.id
                    table.insert(_hud_triples, key)
                    if _hud_seen[e.id] then _hud_dupes = _hud_dupes + 1 end
                    _hud_seen[e.id] = true
                end
            end
            _o_identity_2 = kyohud.hud.objectives
            _o_same_identity_1_2 = (_o_identity_1 == _o_identity_2)
            _sentinel_2 = kyohud.hud.objectives._sentinel_registration
            _sentinel_same_1_2 = (_sentinel_1 == _sentinel_2)
        ''')
        g = lua.globals()
        self.assertEqual(g._hud_count, 2, "exactly 2 HUD hooks after two loads")
        self.assertEqual(g._hud_dupes, 0, "no duplicate HUD hook IDs")
        self.assertTrue(bool(g._o_same_identity_1_2),
            "O state identity must be preserved across hudmanagerpd2 loads")
        self.assertTrue(bool(g._sentinel_same_1_2),
            "sentinel table must be preserved across hudmanagerpd2 loads")
        hud_triples = list(g._hud_triples.values())
        self.assertIn("activate_objective.KyohUD_HUD_ActivateObjective", hud_triples,
            "missing HUDManager/activate_objective/KyohUD_HUD_ActivateObjective")
        self.assertIn("complete_objective.KyohUD_HUD_CompleteObjective", hud_triples,
            "missing HUDManager/complete_objective/KyohUD_HUD_CompleteObjective")

        # Step 3: objectivesmanager twice
        lua.execute('RequiredScript = "lib/managers/objectivesmanager"')
        lua.execute(obj_src)
        lua.execute('RequiredScript = "lib/managers/objectivesmanager"')
        lua.execute(obj_src)
        lua.execute('''
            _om_triples = {}
            _om_count = 0
            _om_dupes = 0
            _om_seen = {}
            for _, e in ipairs(Hooks._all) do
                if e.class == ObjectivesManager then
                    _om_count = _om_count + 1
                    local key = e.method .. "." .. e.id
                    table.insert(_om_triples, key)
                    if _om_seen[e.id] then _om_dupes = _om_dupes + 1 end
                    _om_seen[e.id] = true
                end
            end
            _hud_still_count = 0
            for _, e in ipairs(Hooks._all) do
                if e.class == HUDManager and (e.method == "activate_objective" or e.method == "complete_objective") then
                    _hud_still_count = _hud_still_count + 1
                end
            end
            _o_identity_3 = kyohud.hud.objectives
            _o_same_identity_2_3 = (_o_identity_2 == _o_identity_3)
            _sentinel_3 = kyohud.hud.objectives._sentinel_registration
            _sentinel_same_2_3 = (_sentinel_2 == _sentinel_3)
        ''')
        g = lua.globals()
        self.assertEqual(g._om_count, 7, "exactly 7 OM hooks after two loads")
        self.assertEqual(g._om_dupes, 0, "no duplicate OM hook IDs")
        self.assertEqual(g._hud_still_count, 2,
            "HUD hooks must still be present after OM loads, no duplication")
        self.assertTrue(bool(g._o_same_identity_2_3),
            "O state identity must be preserved across objectivesmanager loads")
        self.assertTrue(bool(g._sentinel_same_2_3),
            "sentinel table must be preserved across objectivesmanager loads")
        om_triples = list(g._om_triples.values())
        expected_om_ids = [
            ("activate_objective", "KyohUD_OM_ActivateObjective"),
            ("activate_objective_countdown", "KyohUD_OM_ActivateObjectiveCountdown"),
            ("remove_objective", "KyohUD_OM_RemoveObjective"),
            ("complete_objective", "KyohUD_OM_CompleteObjective"),
            ("complete_objective_countdown", "KyohUD_OM_CompleteObjectiveCountdown"),
            ("complete_sub_objective", "KyohUD_OM_CompleteSubObjective"),
            ("reset", "KyohUD_OM_Reset"),
        ]
        for method, hook_id in expected_om_ids:
            key = f"{method}.{hook_id}"
            self.assertIn(key, om_triples, f"missing OM hook {method}/{hook_id}")

        # Step 4: negative - no unrelated hooks in Hooks._all
        lua.execute('''
            _total_hooks = 0
            _expected_kyohud_ids = {
                KyohUD_HUD_ActivateObjective = true,
                KyohUD_HUD_CompleteObjective = true,
                KyohUD_OM_ActivateObjective = true,
                KyohUD_OM_ActivateObjectiveCountdown = true,
                KyohUD_OM_RemoveObjective = true,
                KyohUD_OM_CompleteObjective = true,
                KyohUD_OM_CompleteObjectiveCountdown = true,
                KyohUD_OM_CompleteSubObjective = true,
                KyohUD_OM_Reset = true,
            }
            _unexpected_ids = {}
            for _, e in ipairs(Hooks._all) do
                _total_hooks = _total_hooks + 1
                if not _expected_kyohud_ids[e.id] then
                    table.insert(_unexpected_ids, e.id or "(nil)")
                end
            end
        ''')
        g = lua.globals()
        self.assertEqual(g._total_hooks, 9,
            "exactly 9 total hooks (2 HUD + 7 OM)")
        self.assertEqual(list(g._unexpected_ids.values()), [],
            "no unexpected hook IDs registered")

    def test_shared_objectives_region_consumer_integration(self):
        """Integration (DESIRED, must fail before production): M and O
        _compute_layout must each call L.objectives_region exactly once.

        Instrument L.objectives_region with transparent recording wrapper that
        delegates to real function unchanged. Call M:_compute_layout(1920,1080,1.0)
        and O:_compute_layout(1920,1080). Record consumer count after Mission call
        and after Objectives call separately so that one consumer calling twice
        cannot conceal a missing other. DESIRED: count==1 after Mission, count==2
        after both. Verify numeric geometry preserved: O root equals region
        {x=0,y=0,w=500,h=100}; Mission root_y = region.y + region.h + margin_x =
        0 + 100 + 38.4 = 138.4. At scale 1.5: reserved region logical 500x100
        unchanged (not scaled); DESIRED consumer count 2 with each consumer
        calling exactly once; no overlap between Mission and Objectives panels.
        Modules independently share kyohud state; no Mission->Objectives or
        reverse calls.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local L = kyohud.hud.layout
            assert(L, "layout must exist")
            assert(type(L.objectives_region) == "function", "objectives_region must be function")

            local original_objectives_region = L.objectives_region
            local call_count = 0
            local call_log = {}

            function L.objectives_region(w, h)
                call_count = call_count + 1
                local result = original_objectives_region(w, h)
                table.insert(call_log, {w=w, h=h, result=result})
                return result
            end

            local M = kyohud.hud.mission
            local O = kyohud.hud.objectives
            assert(M, "Mission must exist")
            assert(O, "Objectives must exist")

            local m_layout = M:_compute_layout(1920, 1080, 1.0)
            local consumer_count_after_mission = call_count

            local o_layout = O:_compute_layout(1920, 1080)
            local consumer_count_after_both = call_count

            local geom = L.resolve(1920, 1080, 1.0)
            local region = original_objectives_region(1920, 1080)

            _consumer_count_after_mission = consumer_count_after_mission
            _consumer_count_after_both = consumer_count_after_both
            _call_log_len = #call_log

            if o_layout then
                _o_root_x = o_layout.root_x
                _o_root_y = o_layout.root_y
                _o_root_w = o_layout.root_w
                _o_root_h = o_layout.root_h
                _o_font_size = o_layout.font_size
            end

            if region then
                _region_x = region.x
                _region_y = region.y
                _region_w = region.w
                _region_h = region.h
            end

            if m_layout then
                _m_root_x = m_layout.root_x
                _m_root_y = m_layout.root_y
                _m_root_w = m_layout.root_w
                _m_root_h = m_layout.root_h
                _m_font_size = m_layout.font_size
                _margin_x = geom.margin_x
                _expected_m_root_y = region.y + region.h + geom.margin_x
            end

            call_count = 0
            call_log = {}

            kyohud.settings.hud_scale = 1.5
            local m_layout_15 = M:_compute_layout(1920, 1080, 1.5)
            local consumer_count_after_mission_15 = call_count

            local o_layout_15 = O:_compute_layout(1920, 1080)
            local consumer_count_after_both_15 = call_count

            local region_15 = original_objectives_region(1920, 1080)

            _consumer_count_after_mission_15 = consumer_count_after_mission_15
            _consumer_count_after_both_15 = consumer_count_after_both_15

            if o_layout_15 then
                _o_root_w_15 = o_layout_15.root_w
                _o_root_h_15 = o_layout_15.root_h
            end

            if region_15 then
                _region_w_15 = region_15.w
                _region_h_15 = region_15.h
            end

            if m_layout_15 then
                _m_root_y_15 = m_layout_15.root_y
                _margin_x_15 = L.resolve(1920, 1080, 1.5).margin_x
                _expected_m_root_y_15 = region_15.y + region_15.h + _margin_x_15
            end
        ''')

        consumer_after_mission = lua.eval("_consumer_count_after_mission")
        consumer_after_both = lua.eval("_consumer_count_after_both")
        self.assertEqual(consumer_after_mission, 1,
            "DESIRED: exactly 1 consumer call after Mission _compute_layout "
            "(Mission must call L.objectives_region once), got " + str(consumer_after_mission))
        self.assertEqual(consumer_after_both, 2,
            "DESIRED: exactly 2 consumer calls after Mission + Objectives "
            "_compute_layout (each consumer calls L.objectives_region once), got " + str(consumer_after_both))

        o_root_x = lua.eval("_o_root_x")
        o_root_y = lua.eval("_o_root_y")
        o_root_w = lua.eval("_o_root_w")
        o_root_h = lua.eval("_o_root_h")
        region_x = lua.eval("_region_x")
        region_y = lua.eval("_region_y")
        region_w = lua.eval("_region_w")
        region_h = lua.eval("_region_h")

        self.assertEqual(o_root_x, region_x,
            "O root_x must equal region.x (both 0)")
        self.assertEqual(o_root_y, region_y,
            "O root_y must equal region.y (both 0)")
        self.assertEqual(o_root_w, region_w,
            "O root_w must equal region.w (both 500)")
        self.assertEqual(o_root_h, region_h,
            "O root_h must equal region.h (both 100)")

        m_root_y = lua.eval("_m_root_y")
        expected_m_root_y = lua.eval("_expected_m_root_y")
        self.assertAlmostEqual(m_root_y, expected_m_root_y, places=1,
            msg="Mission root_y must equal region.y + region.h + margin_x")

        consumer_after_mission_15 = lua.eval("_consumer_count_after_mission_15")
        consumer_after_both_15 = lua.eval("_consumer_count_after_both_15")
        self.assertEqual(consumer_after_mission_15, 1,
            "DESIRED: exactly 1 consumer call after Mission _compute_layout "
            "at scale 1.5 (Mission must call L.objectives_region once), got " + str(consumer_after_mission_15))
        self.assertEqual(consumer_after_both_15, 2,
            "DESIRED: exactly 2 consumer calls after Mission + Objectives "
            "_compute_layout at scale 1.5 (each consumer calls once), got " + str(consumer_after_both_15))

        region_w_15 = lua.eval("_region_w_15")
        region_h_15 = lua.eval("_region_h_15")
        self.assertEqual(region_w_15, 500,
            "Region width must remain 500 (logical, unscaled) at scale 1.5")
        self.assertEqual(region_h_15, 100,
            "Region height must remain 100 (logical, unscaled) at scale 1.5")

        m_root_y_15 = lua.eval("_m_root_y_15")
        expected_m_root_y_15 = lua.eval("_expected_m_root_y_15")
        self.assertAlmostEqual(m_root_y_15, expected_m_root_y_15, places=1,
            msg="Mission root_y at scale 1.5 must equal region.y + region.h + margin_x")

        o_root_h = lua.eval("_o_root_h")
        o_root_h_15 = lua.eval("_o_root_h_15")
        m_root_y = lua.eval("_m_root_y")
        m_root_y_15 = lua.eval("_m_root_y_15")

        o_bottom = o_root_y + o_root_h
        m_top = m_root_y
        self.assertLessEqual(o_bottom, m_top,
            "No overlap: Objectives bottom (0+100=100) must be <= Mission top (138.4)")

        o_bottom_15 = o_root_y + o_root_h_15
        m_top_15 = m_root_y_15
        self.assertLessEqual(o_bottom_15, m_top_15,
            "No overlap at scale 1.5: Objectives bottom must be <= Mission top")


if __name__ == "__main__":
    unittest.main()
