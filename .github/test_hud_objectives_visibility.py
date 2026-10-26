"""LOT2b integration -- objectives native visibility acquisition cycle.

Tests objectives module acquires native visibility for 8 HUDObjectives leaves,
hides them during render, restores when disabled. Exposes missing acquisition.
"""
import unittest

from test_hud_objectives import _lua


NATIVE_HUD_OBJECTIVES_FIXTURE = r'''
utf8 = utf8 or {}
if not utf8.to_upper then
    function utf8.to_upper(s)
        return s:upper()
    end
end

HUDObjectives = HUDObjectives or {}
HUDObjectives.__index = HUDObjectives

function HUDObjectives:init(hud)
    self._hud_panel = hud.panel
end

function HUDObjectives:activate_objective(data)
    self._active_objective_id = data.id
    local objectives_panel = self._hud_panel:child("objectives_panel")
    local objective_text = objectives_panel:child("objective_text")
    objective_text:set_text(utf8.to_upper(data.text))
    local _, _, w, _ = objective_text:text_rect()
    objectives_panel:set_visible(true)
    self._bg_box:set_h(data.amount and 60 or 38)
    objective_text:set_visible(false)
    self._bg_box:stop()
    self._bg_box:animate(callback(nil, _G, "HUDBGBox_animate_open_right"), 0.66, w + 16, callback(self, self, "open_right_done", data.amount and true or false))
    objectives_panel:stop()
    objectives_panel:animate(callback(self, self, "_animate_activate_objective"))
    objectives_panel:child("amount_text"):set_visible(false)
    if data.amount then
        self:update_amount_objective(data)
    end
end

function HUDObjectives:update_amount_objective(data)
    if data.id == self._active_objective_id then
        local current = data.current_amount or 0
        local amount = data.amount
        local objectives_panel = self._hud_panel:child("objectives_panel")
        local amount_text = objectives_panel:child("amount_text")
        if alive(amount_text) then
            amount_text:set_text(current .. "/" .. amount)
        end
    end
end

function HUDObjectives:open_right_done(uses_amount)
    local objectives_panel = self._hud_panel:child("objectives_panel")
    local objective_text = objectives_panel:child("objective_text")

    objective_text:set_visible(true)
    objective_text:stop()

    local amount_text = objectives_panel:child("amount_text")

    if alive(amount_text) then
        amount_text:set_visible(uses_amount)
    end

    objective_text:animate(callback(self, self, "_animate_show_text"), amount_text)
end

function HUDObjectives:complete_objective(data)
	if data.id == self._active_objective_id then
		local objectives_panel = self._hud_panel:child("objectives_panel")
		objectives_panel:stop()
		objectives_panel:animate(callback(self, self, "_animate_complete_objective"))
	end
end

function HUDObjectives:_animate_show_text(objective_text, amount_text)
	local TOTAL_T = 0.5
	local t = TOTAL_T
	while t > 0 do
		local dt = coroutine.yield()
		t = t - dt
		local alpha = math.round(math.abs((math.sin(t * 360 * 3))))
		objective_text:set_alpha(alpha)
		if alive(amount_text) then
			amount_text:set_alpha(alpha)
		end
	end
	objective_text:set_alpha(1)
	if alive(amount_text) then
		amount_text:set_alpha(1)
	end
end

function HUDObjectives:_animate_complete_objective(objectives_panel)
	local objective_text = objectives_panel:child("objective_text")
	local amount_text = objectives_panel:child("amount_text")
	local icon_objectivebox = objectives_panel:child("icon_objectivebox")
	icon_objectivebox:set_y(0)
	local TOTAL_T = 0.5
	local t = TOTAL_T
	while t > 0 do
		local dt = coroutine.yield()
		t = t - dt
		local vis = math.round(math.abs((math.cos(t * 360 * 3))))
		objective_text:set_alpha(vis)
		if alive(amount_text) then
			amount_text:set_alpha(vis)
		end
	end
	objective_text:set_alpha(1)
	objective_text:set_visible(false)
	if alive(amount_text) then
		amount_text:set_alpha(1)
		amount_text:set_visible(false)
	end
	local function done_cb()
		objectives_panel:child("objective_text"):set_text(utf8.to_upper(""))
		objectives_panel:set_visible(false)
	end
	self._bg_box:stop()
	self._bg_box:animate(callback(nil, _G, "HUDBGBox_animate_close_right"), done_cb)
end

function HUDObjectives:_animate_activate_objective(objectives_panel)
end

local box_speed = 1000

function HUDBGBox_animate_open_right(panel, wait_t, target_w, done_cb)
    panel:set_visible(false)
    panel:set_w(0)

    if wait_t then
        wait(wait_t)
    end

    panel:set_visible(true)

    local speed = box_speed
    local bg = panel:child("bg")

    bg:stop()
    bg:animate(callback(nil, _G, "HUDBGBox_animate_bg_attention"))

    local TOTAL_T = target_w / speed
    local t = TOTAL_T

    while t > 0 do
        local dt = coroutine.yield()

        t = t - dt

        panel:set_w((1 - t / TOTAL_T) * target_w)
    end

    panel:set_w(target_w)
    done_cb()
end

function HUDBGBox_animate_close_right(panel, done_cb)
	local speed = box_speed
	local cw = panel:w()
	local TOTAL_T = cw / speed
	local t = TOTAL_T
	while t > 0 do
		local dt = coroutine.yield()
		t = t - dt
		panel:set_w(t / TOTAL_T * cw)
	end
	panel:set_w(0)
	done_cb()
end

function HUDBGBox_animate_bg_attention(bg, config)
    local color = config and config.color or Color.white
    local attention_color_function = config and config.attention_color_function
    local forever = config and config.forever or false
    local TOTAL_T = 3
    local t = TOTAL_T

    while t > 0 or forever do
        local dt = coroutine.yield()

        t = t - dt

        local cv = math.abs((math.sin(t * 180 * 1)))
        local mod_color = attention_color_function and attention_color_function() or color

        bg:set_color(Color(1, mod_color.red * cv, mod_color.green * cv, mod_color.blue * cv))
    end

    bg:set_color(Color(1, 0, 0, 0))
end

function callback(o, base_callback_class, base_callback_func_name, base_callback_param)
    if base_callback_class and base_callback_func_name and base_callback_class[base_callback_func_name] then
        if base_callback_param ~= nil then
            if o then
                return function(...)
                    return base_callback_class[base_callback_func_name](o, base_callback_param, ...)
                end
            else
                return function(...)
                    return base_callback_class[base_callback_func_name](base_callback_param, ...)
                end
            end
        elseif o then
            return function(...)
                return base_callback_class[base_callback_func_name](o, ...)
            end
        else
            return function(...)
                return base_callback_class[base_callback_func_name](...)
            end
        end
    elseif base_callback_class then
        error("Callback on class refers to a non-existing function \"" .. tostring(base_callback_func_name) .. "\".")
    elseif base_callback_func_name then
        error("Callback to function \"" .. tostring(base_callback_func_name) .. "\" is on a nil class.")
    else
        error("Callback class and function was nil.")
    end
end
'''


def _lua_with_native_hud_objectives():
    """Create Lua runtime with HUDObjectives native class defined before loading objectives."""
    from lupa.luajit21 import LuaRuntime
    from test_hud_objectives import (
        STUBS, DIESEL, ROOT, OBJECTIVES_PATH,
        LAYOUT_PATH, NATIVE_VIS_PATH, RUNTIME_PATH, MISSION_PATH
    )

    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute('''
Color = function(...)
    local args = {...}
    if #args == 3 then
        return {1, args[1], args[2], args[3]}
    elseif #args == 4 then
        return {args[1], args[2], args[3], args[4]}
    end
    return {1, 1, 1, 1}
end
''')
    lua.execute(DIESEL)

    # Define HUDObjectives native class and callback helper before loading objectives
    lua.execute(NATIVE_HUD_OBJECTIVES_FIXTURE)

    # Extend panel text to support stop/animate recording
    # Extend all panels to support stop/animate/set_h/set_w/set_y recording
    lua.execute('''
        local orig_make_panel = _make_panel
        function _make_panel(name)
            local p = orig_make_panel(name)
            p._stopped = false
            p._animated = false
            p._set_h_calls = {}
            p._animate_calls = {}
            p._scheduled_fn = nil
            p._scheduled_args = nil
            local orig_stop = p.stop
            local orig_animate = p.animate
            function p:stop()
                self._stopped = true
                self._scheduled_fn = nil
                self._scheduled_args = nil
            end
            function p:animate(fn, ...)
                self._animated = true
                self._scheduled_fn = fn
                self._scheduled_args = {...}
                table.insert(self._animate_calls, fn)
            end
            function p:set_h(h) self._h = h; table.insert(self._set_h_calls, h) end
            function p:set_w(w) self._w = w end
            function p:set_y(y) self._y = y end
            local orig_text = p.text
            p.text = function(self, opts)
                local t = orig_text(self, opts)
                t._stopped = false
                t._animated = false
                t._scheduled_fn = nil
                t._scheduled_args = nil
                function t:stop()
                    self._stopped = true
                    self._scheduled_fn = nil
                    self._scheduled_args = nil
                end
                function t:animate(fn, ...)
                    self._animated = true
                    self._scheduled_fn = fn
                    self._scheduled_args = {...}
                end
                function t:set_w(w) self._w = w end
                function t:set_y(y) self._y = y end
                return t
            end
            return p
        end
        function _run_coroutine(obj, max_steps)
            max_steps = max_steps or 1000
            assert(obj._scheduled_fn, "no scheduled animation on object")
            local fn = obj._scheduled_fn
            local args = obj._scheduled_args or {}
            local co = coroutine.create(fn)
            local ok, err = coroutine.resume(co, obj, unpack(args))
            assert(ok, "coroutine first resume failed: " .. tostring(err))
            local steps = 0
            while coroutine.status(co) ~= "dead" do
                steps = steps + 1
                assert(steps <= max_steps, "coroutine exceeded budget of " .. max_steps)
                local ok2, err2 = coroutine.resume(co, 0.016)
                assert(ok2, "coroutine resume failed at step " .. steps .. ": " .. tostring(err2))
            end
            obj._scheduled_fn = nil
            obj._scheduled_args = nil
            return steps
        end
    ''')

    lua.execute("_init_fp = _make_parent(); _make_mgr(_init_fp)")

    lua.execute('''
        local _orig_hud_activate = HUDManager.activate_objective
        HUDManager.activate_objective = function(self, data)
            _orig_hud_activate(self, data)
            if self._hud_objectives and type(self._hud_objectives.activate_objective) == "function" then
                self._hud_objectives:activate_objective(data)
            end
        end
        local _orig_hud_update_amount = HUDManager.update_amount_objective
        HUDManager.update_amount_objective = function(self, data)
            _orig_hud_update_amount(self, data)
            if self._hud_objectives and type(self._hud_objectives.update_amount_objective) == "function" then
                self._hud_objectives:update_amount_objective(data)
            end
        end
        local _orig_hud_complete = HUDManager.complete_objective
        HUDManager.complete_objective = function(self, data)
            _orig_hud_complete(self, data)
            if self._hud_objectives and type(self._hud_objectives.complete_objective) == "function" then
                self._hud_objectives:complete_objective(data)
            end
        end
    ''')

    lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')

    def _read(p):
        return p.read_text(encoding="utf-8-sig") if p.is_file() else None

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
        lua.execute('RequiredScript = "lib/managers/hud/hudobjectives"')
        lua.execute(obj_src)

    return lua, obj_src is not None


def _lua_native_ready():
    """Create Lua runtime with native source tree, OM, runtime mounted, and baseline established.

    Does NOT inject any O state/whitelist or call NV.acquire/release directly.
    """
    lua, ok = _lua_with_native_hud_objectives()
    if not ok:
        return None, False

    lua.execute('''
        kyohud.settings.enable_hud_foundation = true
        kyohud.settings.enable_objectives = true

        local OM = _make_om()
        OM._objectives["collect"] = {
            id = "collect", text = "Collect bags", amount = 3,
            current_amount = 0, sub_objectives = {},
        }
        OM:activate_objective("collect", nil, {amount = 3})

        local source_hud_panel = _make_panel("source_hud_panel")
        source_hud_panel._w = 1920; source_hud_panel._h = 1080
        local objectives_panel = source_hud_panel:panel({
            name = "objectives_panel", x = 0, y = 0, w = 500, h = 100, visible = true,
        })
        objectives_panel._alpha = 1

        local icon_objectivebox = objectives_panel:text({
            name = "icon_objectivebox", x = 0, y = 0, w = 24, h = 24, visible = true,
        })
        icon_objectivebox._alpha = 0.37

        local objective_text = objectives_panel:text({
            name = "objective_text", x = 34, y = 6, w = 180, h = 20,
            text = "Collect bags", visible = true,
        })
        objective_text._alpha = 0.37

        local amount_text = objectives_panel:text({
            name = "amount_text", x = 34, y = 24, w = 180, h = 20,
            text = "0/3", visible = true,
        })
        amount_text._alpha = 0.37

        local sentinel = objectives_panel:text({
            name = "sentinel_label", x = 0, y = 50, w = 100, h = 20,
            text = "sentinel", visible = true,
        })
        sentinel._alpha = 1

        local bg_box = objectives_panel:panel({
            name = "test_bg_box", x = 26, y = 0, w = 200, h = 38, visible = true,
        })
        bg_box._alpha = 1

        local bg = bg_box:text({name = "bg", x = 0, y = 0, w = 200, h = 38, visible = true})
        bg._alpha = 0.37
        local left_top = bg_box:text({name = "left_top", x = 0, y = 0, w = 8, h = 8, visible = true})
        left_top._alpha = 0.37
        local left_bottom = bg_box:text({name = "left_bottom", x = 0, y = 30, w = 8, h = 8, visible = true})
        left_bottom._alpha = 0.37
        local right_top = bg_box:text({name = "right_top", x = 192, y = 0, w = 8, h = 8, visible = true})
        right_top._alpha = 0.37
        local right_bottom = bg_box:text({name = "right_bottom", x = 192, y = 30, w = 8, h = 8, visible = true})
        right_bottom._alpha = 0.37

        local leaves = {
            icon_objectivebox, objective_text, amount_text,
            bg, left_top, left_bottom, right_top, right_bottom,
        }

        local native_obj = setmetatable({}, HUDObjectives)
        native_obj:init({panel = source_hud_panel})
        native_obj._bg_box = bg_box
        managers.hud._hud_objectives = native_obj
        managers.hud._hud_objectives._active_objective_id = "collect"

        local RT = kyohud.hud.runtime
        RT:mount(managers.hud)

        RT:update(managers.hud, 1.0, 0.016)

        native_obj:open_right_done(true)

        _test_refs = {
            objectives_panel = objectives_panel,
            objective_text = objective_text,
            amount_text = amount_text,
            icon_objectivebox = icon_objectivebox,
            sentinel = sentinel,
            bg_box = bg_box,
            bg = bg,
            left_top = left_top,
            left_bottom = left_bottom,
            right_top = right_top,
            right_bottom = right_bottom,
            leaves = leaves,
            native_obj = native_obj,
            RT = RT,
            O = kyohud.hud.objectives,
            nv = kyohud.hud.native_visibility,
        }

        local function extend_prim_with_color(p)
            if p._color_extended then return end
            p._color_extended = true
            if not p._color then
                p._color = {1, 1, 1, 1}
            end
            function p:set_color(c)
                if type(c) == "table" then
                    if #c == 3 then
                        self._color = {1, c[1], c[2], c[3]}
                    else
                        self._color = c
                    end
                end
            end
            function p:color()
                return self._color
            end
        end

        local O = kyohud.hud.objectives
        if O._root_panel then
            extend_prim_with_color(O._root_panel)
            local orig_rect = O._root_panel.rect
            if not orig_rect then
                function O._root_panel:rect(opts)
                    local ch = _make_panel(opts and opts.name)
                    ch._parent = self
                    if opts then
                        if opts.x then ch._x = opts.x end
                        if opts.y then ch._y = opts.y end
                        if opts.w then ch._w = opts.w end
                        if opts.h then ch._h = opts.h end
                        if opts.visible ~= nil then ch._visible = opts.visible end
                        if opts.alpha ~= nil then ch._alpha = opts.alpha end
                        if opts.color ~= nil then ch._color = opts.color end
                    end
                    self._children[ch._name] = ch
                    return ch
                end
                orig_rect = O._root_panel.rect
            end
            function O._root_panel:rect(...)
                local r = orig_rect(self, ...)
                extend_prim_with_color(r)
                return r
            end
            for name, child in pairs(O._root_panel._children) do
                extend_prim_with_color(child)
            end
        end
        if O._slot_prims then
            for i = 1, 3 do
                local slot = O._slot_prims[i]
                if slot then
                    if slot.text then extend_prim_with_color(slot.text) end
                    if slot.amount then extend_prim_with_color(slot.amount) end
                end
            end
        end
    ''')

    return lua, True


class ObjectivesVisibilityIntegrationTests(unittest.TestCase):
    """Integration test for objectives native visibility acquisition cycle."""

    def test_objectives_native_visibility_acquisition_cycle(self):
        """Objectives must acquire native visibility for 8 HUDObjectives leaves,
        hide them during render, and restore when disabled.

        This test exposes that objectives module does NOT currently acquire
        native visibility for the 8 leaves of HUDObjectives tree.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true
            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect", text = "Collect bags", amount = 3,
                current_amount = 0, sub_objectives = {},
            }
            OM:activate_objective("collect", nil, {amount = 3})
            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local O = kyohud.hud.objectives
            assert(O, "O must exist")
            assert(O._mounted == true, "O must be mounted via RT:mount coordination")
            assert(O._root_panel and O._root_panel._alive, "O._root_panel must be alive")
            local baseline_verify = O:_verify_render()
            assert(baseline_verify == true, "baseline verify_render must be true, got " .. tostring(baseline_verify))
            local title_prim = O._slot_prims[1] and O._slot_prims[1].text
            assert(title_prim, "title primitive must exist")
            local orig_text_rect = title_prim.text_rect
            function title_prim:text_rect() return 0, 0, 99999, 99999 end
            local source_hud_panel = _make_panel("source_hud_panel")
            source_hud_panel._w = 1920; source_hud_panel._h = 1080
            local objectives_panel = source_hud_panel:panel({
                name = "objectives_panel", x = 0, y = 0, w = 500, h = 100, visible = true,
            })
            objectives_panel._alpha = 1
            local icon_objectivebox = objectives_panel:text({
                name = "icon_objectivebox", x = 0, y = 0, w = 24, h = 24, visible = true,
            })
            icon_objectivebox._alpha = 0.37
            local objective_text = objectives_panel:text({
                name = "objective_text", x = 34, y = 6, w = 180, h = 20,
                text = "Collect bags", visible = false,
            })
            objective_text._alpha = 0.37
            local amount_text = objectives_panel:text({
                name = "amount_text", x = 34, y = 24, w = 180, h = 20,
                text = "0/3", visible = true,
            })
            amount_text._alpha = 0.37
            local sentinel = objectives_panel:text({
                name = "sentinel_label", x = 0, y = 50, w = 100, h = 20,
                text = "sentinel", visible = true,
            })
            sentinel._alpha = 1
            local bg_box = objectives_panel:panel({
                name = "test_bg_box", x = 26, y = 0, w = 200, h = 38, visible = true,
            })
            bg_box._alpha = 1
            local bg = bg_box:text({name = "bg", x = 0, y = 0, w = 200, h = 38, visible = false})
            bg._alpha = 0.37
            local left_top = bg_box:text({name = "left_top", x = 0, y = 0, w = 8, h = 8, visible = true})
            left_top._alpha = 0.37
            local left_bottom = bg_box:text({name = "left_bottom", x = 0, y = 30, w = 8, h = 8, visible = false})
            left_bottom._alpha = 0.37
            local right_top = bg_box:text({name = "right_top", x = 192, y = 0, w = 8, h = 8, visible = true})
            right_top._alpha = 0.37
            local right_bottom = bg_box:text({name = "right_bottom", x = 192, y = 30, w = 8, h = 8, visible = false})
            right_bottom._alpha = 0.37
            local leaves = {
                icon_objectivebox, objective_text, amount_text,
                bg, left_top, left_bottom, right_top, right_bottom,
            }
            local originals = {}
            for i, leaf in ipairs(leaves) do
                originals[i] = {visible = leaf:visible(), alpha = leaf:alpha()}
            end
            local nv = kyohud.hud.native_visibility
            -- Assert initially whitelist has no native leaves/parents
            for _, leaf in ipairs(leaves) do
                assert(nv._whitelist[leaf] == nil, "whitelist must not contain leaf initially")
            end
            assert(nv._whitelist[objectives_panel] == nil, "whitelist must not contain objectives_panel initially")
            assert(nv._whitelist[bg_box] == nil, "whitelist must not contain bg_box initially")
            assert(nv._whitelist[sentinel] == nil, "whitelist must not contain sentinel initially")
            managers.hud._hud_objectives = {
                _hud_panel = source_hud_panel, _bg_box = bg_box, _active_objective_id = "collect",
            }
            RT:update(managers.hud, 1.0, 0.016)
            local verify_fail = O:_verify_render()
            assert(verify_fail == false, "verify_render must be false with corrupted text_rect, got " .. tostring(verify_fail))
            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == originals[i].visible,
                    "leaf " .. i .. " must remain original visible, got " .. tostring(leaf:visible()))
                assert(leaf:alpha() == originals[i].alpha, "leaf " .. i .. " must remain original alpha")
            end
            local nv_entries_before = 0
            for _, e in ipairs(nv._entries) do
                for _, leaf in ipairs(leaves) do
                    if e.object == leaf then nv_entries_before = nv_entries_before + 1 end
                end
            end
            assert(nv_entries_before == 0, "NV must have no entries for leaves before recovery, got " .. nv_entries_before)
            assert(objectives_panel:visible() == true, "objectives_panel must remain visible after fail")
            assert(bg_box:visible() == true, "bg_box must remain visible after fail")
            assert(sentinel:visible() == true, "sentinel must remain visible after fail")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after fail")
            title_prim.text_rect = orig_text_rect
            RT:update(managers.hud, 2.0, 0.016)
            local verify_recover = O:_verify_render()
            assert(verify_recover == true, "verify_render must be true after restore, got " .. tostring(verify_recover))
            -- After production hide: assert each of 8 whitelist entries has visible=true only (no alpha)
            for _, leaf in ipairs(leaves) do
                local wl_entry = nv._whitelist[leaf]
                assert(wl_entry ~= nil, "whitelist must contain leaf after hide")
                assert(wl_entry.visible == true, "whitelist entry must have visible=true")
                assert(wl_entry.alpha == nil or wl_entry.alpha == false, "whitelist entry must not have alpha")
            end
            -- Assert parent/bgbox/sentinel not whitelisted
            assert(nv._whitelist[objectives_panel] == nil, "whitelist must not contain objectives_panel")
            assert(nv._whitelist[bg_box] == nil, "whitelist must not contain bg_box")
            assert(nv._whitelist[sentinel] == nil, "whitelist must not contain sentinel")
            -- Assert each leaf has exactly one NV entry with owner==O
            for i, leaf in ipairs(leaves) do
                local count = 0
                for _, e in ipairs(nv._entries) do
                    if e.owner == O and e.object == leaf and e.property == "visible" then
                        count = count + 1
                    end
                end
                assert(count == 1, "leaf " .. i .. " must have exactly one NV entry with owner==O, object==leaf, property==visible, got " .. count)
            end
            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must be visible=false via NV, got " .. tostring(leaf:visible()) .. " (MISSING ACQUISITION)")
                assert(leaf:alpha() == originals[i].alpha, "leaf " .. i .. " alpha must remain " .. originals[i].alpha)
            end
            local nv_entries_after = 0
            for _, e in ipairs(nv._entries) do
                for _, leaf in ipairs(leaves) do
                    if e.object == leaf and e.property == "visible" then nv_entries_after = nv_entries_after + 1 end
                end
            end
            assert(nv_entries_after == 8, "NV must have exactly 8 visible entries for leaves, got " .. nv_entries_after)
            assert(objectives_panel:visible() == true, "objectives_panel must remain visible after hide")
            assert(bg_box:visible() == true, "bg_box must remain visible after hide")
            assert(sentinel:visible() == true, "sentinel must remain visible after hide")
            assert(objectives_panel:alpha() == 1, "objectives_panel alpha must remain 1 after hide")
            assert(bg_box:alpha() == 1, "bg_box alpha must remain 1 after hide")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after hide")
            kyohud.settings.enable_objectives = false
            RT:refresh_settings(managers.hud)
            local owned_panel_gone = O._root_panel == nil or not O._root_panel._alive
            assert(owned_panel_gone == true, "owned panel must be gone after disable")
            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == originals[i].visible,
                    "leaf " .. i .. " must be restored to original visible, got " .. tostring(leaf:visible()))
                assert(leaf:alpha() == originals[i].alpha,
                    "leaf " .. i .. " alpha must remain " .. originals[i].alpha .. " after disable")
            end
            local nv_entries_final = 0
            for _, e in ipairs(nv._entries) do
                for _, leaf in ipairs(leaves) do
                    if e.object == leaf then nv_entries_final = nv_entries_final + 1 end
                end
            end
            assert(nv_entries_final == 0, "NV must have no entries for leaves after disable, got " .. nv_entries_final)
            local registry_preserved = #O._active == 1 and O._active[1].id == "collect"
            assert(registry_preserved == true, "O._active registry must be preserved")
            assert(objectives_panel:visible() == true, "objectives_panel must remain visible after disable")
            assert(bg_box:visible() == true, "bg_box must remain visible after disable")
            assert(sentinel:visible() == true, "sentinel must remain visible after disable")
            assert(objectives_panel:alpha() == 1, "objectives_panel alpha must remain 1 after disable")
            assert(bg_box:alpha() == 1, "bg_box alpha must remain 1 after disable")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after disable")
        ''')

    def test_open_right_done_native_transition(self):
        """RED: Native open_right_done sets title visible=true, O NV should mask
        but currently has no hook for HUDObjectives:open_right_done.

        Enable foundation/objectives, mount RT and O. Build native HUDObjectives tree
        with 8 leaves (icon_objectivebox, objective_text, amount_text, bg, left_top,
        left_bottom, right_top, right_bottom). Pre-open state: objective_text=false,
        amount_text=false, other 6 leaves=true. RT mount acquires NV, sets all 8
        leaves visible=false. Call native HUDObjectives:open_right_done(false) which
        sets objective_text visible=true, amount_text visible=false(uses_amount).
        Since no hooks are registered for open_right_done, native call directly
        changes visibility bypassing NV. Assert objective_text visible=false (masked
        by NV) -- FAILS because native sets it to true. Verify animation scheduled.
        Disable via settings RT.refresh_settings: NV release restores native values
        (title=true, amount=false from open_right_done), other 6 originals, parents/
        sentinel untouched. No manual O/NV repair calls or whitelist edits.
        """
        lua, ok = _lua_with_native_hud_objectives()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            -- Activate objective first to populate O._active
            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect", text = "Collect bags", amount = nil,
                current_amount = nil, sub_objectives = {},
            }
            OM:activate_objective("collect", nil, {})

            -- Build native HUDObjectives tree (8 leaves via existing builder pattern)
            local source_hud_panel = _make_panel("source_hud_panel")
            source_hud_panel._w = 1920; source_hud_panel._h = 1080
            local objectives_panel = source_hud_panel:panel({
                name = "objectives_panel", x = 0, y = 0, w = 500, h = 100, visible = true,
            })
            objectives_panel._alpha = 1

            local icon_objectivebox = objectives_panel:text({
                name = "icon_objectivebox", x = 0, y = 0, w = 24, h = 24, visible = true,
            })
            icon_objectivebox._alpha = 0.37

            local objective_text = objectives_panel:text({
                name = "objective_text", x = 34, y = 6, w = 180, h = 20,
                text = "Collect bags", visible = false,
            })
            objective_text._alpha = 0.37

            local amount_text = objectives_panel:text({
                name = "amount_text", x = 34, y = 24, w = 180, h = 20,
                text = "0/3", visible = false,
            })
            amount_text._alpha = 0.37

            local sentinel = objectives_panel:text({
                name = "sentinel_label", x = 0, y = 50, w = 100, h = 20,
                text = "sentinel", visible = true,
            })
            sentinel._alpha = 1

            local bg_box = objectives_panel:panel({
                name = "test_bg_box", x = 26, y = 0, w = 200, h = 38, visible = true,
            })
            bg_box._alpha = 1

            local bg = bg_box:text({name = "bg", x = 0, y = 0, w = 200, h = 38, visible = true})
            bg._alpha = 0.37
            local left_top = bg_box:text({name = "left_top", x = 0, y = 0, w = 8, h = 8, visible = true})
            left_top._alpha = 0.37
            local left_bottom = bg_box:text({name = "left_bottom", x = 0, y = 30, w = 8, h = 8, visible = true})
            left_bottom._alpha = 0.37
            local right_top = bg_box:text({name = "right_top", x = 192, y = 0, w = 8, h = 8, visible = true})
            right_top._alpha = 0.37
            local right_bottom = bg_box:text({name = "right_bottom", x = 192, y = 30, w = 8, h = 8, visible = true})
            right_bottom._alpha = 0.37

            local leaves = {
                icon_objectivebox, objective_text, amount_text,
                bg, left_top, left_bottom, right_top, right_bottom,
            }

            -- Create native HUDObjectives instance (setmetatable class identity)
            local native_obj = setmetatable({}, HUDObjectives)
            native_obj:init({panel = source_hud_panel})
            native_obj._bg_box = bg_box
            managers.hud._hud_objectives = native_obj
            managers.hud._hud_objectives._active_objective_id = "collect"

            -- Record original visibility (pre-open state)
            local originals = {}
            for i, leaf in ipairs(leaves) do
                originals[i] = {visible = leaf:visible(), alpha = leaf:alpha()}
            end

            -- Verify pre-open state: title and amount false, others true
            assert(objective_text:visible() == false, "title must be false pre-open")
            assert(amount_text:visible() == false, "amount must be false pre-open")
            assert(icon_objectivebox:visible() == true, "icon must be true pre-open")
            assert(bg:visible() == true, "bg must be true pre-open")
            assert(left_top:visible() == true, "left_top must be true pre-open")

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local O = kyohud.hud.objectives
            assert(O, "O must exist")

            -- Trigger mount and native visibility acquisition via RT:update
            RT:update(managers.hud, 1.0, 0.016)

            assert(O._mounted == true, "O must be mounted")

            -- Verify all 8 leaves are hidden via NV
            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must be visible=false via NV, got " .. tostring(leaf:visible()))
            end

            -- Verify NV whitelist contains all 8 leaves
            local nv = kyohud.hud.native_visibility
            for i, leaf in ipairs(leaves) do
                local wl_entry = nv._whitelist[leaf]
                assert(wl_entry ~= nil, "whitelist must contain leaf " .. i)
                assert(wl_entry.visible == true, "whitelist entry must have visible=true")
            end

            -- Parents/sentinel not whitelisted
            assert(nv._whitelist[objectives_panel] == nil, "whitelist must not contain objectives_panel")
            assert(nv._whitelist[bg_box] == nil, "whitelist must not contain bg_box")
            assert(nv._whitelist[sentinel] == nil, "whitelist must not contain sentinel")

            -- Call native open_right_done(false) through real registered pre/post hooks
            -- (currently absent, so native method runs directly)
            native_obj:open_right_done(false)

            -- Native sets title visible=true, amount visible=false (uses_amount=false)
            -- Native also calls stop() and animate() on title
            -- Since no hooks registered, native directly changes visibility bypassing NV
            -- O NV should mask title to false, but currently has no hook -> RED

            -- Verify animation scheduling preserved (native stop/animate called)
            assert(objective_text._stopped == true, "title stop must be called")
            assert(objective_text._animated == true, "title animate must be called")

            -- Title/amount should remain masked false immediately after callback
            -- while O verify true -- FAILS because native title becomes true
            assert(objective_text:visible() == false,
                "title must remain masked false after open_right_done, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must remain masked false after open_right_done, got " .. tostring(amount_text:visible()))

            -- Verify other 6 leaves still masked false
            assert(icon_objectivebox:visible() == false, "icon must remain masked false")
            assert(bg:visible() == false, "bg must remain masked false")
            assert(left_top:visible() == false, "left_top must remain masked false")
            assert(left_bottom:visible() == false, "left_bottom must remain masked false")
            assert(right_top:visible() == false, "right_top must remain masked false")
            assert(right_bottom:visible() == false, "right_bottom must remain masked false")

            -- O verify_render should still be true (NV entries intact)
            local vr = O:_verify_render()
            assert(vr == true, "_verify_render must be true after open_right_done, got " .. tostring(vr))

            -- Parents/sentinel untouched
            assert(objectives_panel:visible() == true, "objectives_panel must remain visible")
            assert(bg_box:visible() == true, "bg_box must remain visible")
            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")

            -- Disable via settings
            kyohud.settings.enable_objectives = false
            RT:refresh_settings(managers.hud)

            -- After NV release: title restored true, amount false (NEW native values
            -- from open_right_done, not old false/false), other 6 originals,
            -- parents/sentinel untouched
            assert(objective_text:visible() == true,
                "title must be true after disable (native value from open_right_done), got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must be false after disable (native value uses_amount=false), got " .. tostring(amount_text:visible()))

            -- Other 6 leaves restored to originals
            for i, leaf in ipairs(leaves) do
                if leaf ~= objective_text and leaf ~= amount_text then
                    assert(leaf:visible() == originals[i].visible,
                        "leaf " .. i .. " must be restored to original visible, got " .. tostring(leaf:visible()))
                    assert(leaf:alpha() == originals[i].alpha,
                        "leaf " .. i .. " alpha must remain " .. originals[i].alpha)
                end
            end

            -- Parents/sentinel untouched after disable
            assert(objectives_panel:visible() == true, "objectives_panel must remain visible after disable")
            assert(bg_box:visible() == true, "bg_box must remain visible after disable")
            assert(sentinel:visible() == true, "sentinel must remain visible after disable")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after disable")

            -- O panel gone after disable
            local owned_panel_gone = O._root_panel == nil or not O._root_panel._alive
            assert(owned_panel_gone == true, "owned panel must be gone after disable")
        ''')

    def test_parent_width_zero_nv_release_gap(self):
        """RED: _sync_primitives early return on nil layout does not release NV.

        Enable foundation/objectives, mount RT and O. Build native tree with
        8 leaves (3+5: objective_text, amount_text, icon_objectivebox from
        objectives_panel; bg, left_top, left_bottom, right_top, right_bottom
        from bg_box), all original visible=true. Source active "collect"
        quantity=3 current=0. Native fixture: managers.hud._hud_objectives
        with _hud_panel, _bg_box, _active_objective_id.

        RT:mount + RT:update: O mounted, _verify_render true, all 8 hidden
        via real NV, 8 owner entries. Save owned panel/primitive identities
        and parent width.

        Set O._parent_panel._w=0 (same owned runtime parent, no native
        geometry change). RT:update: _update_layout clears _layout_cache
        (pw<=0), _sync_primitives early returns at nil layout (line 609),
        never calls _sync_native_visibility. Assert _verify_render false,
        all 8 native originals restored (visible=true), NV owner entries
        gone -- FAILS because early return skips NV release.

        Restore parent width. RT:update2: _verify_render true, same owned
        panel/primitive identities preserved, all 8 hidden again via NV,
        8 NV owner entries present. No manual O layout/cache repair, no NV
        calls/whitelist writes. Assert native parents/sentinel unchanged
        throughout.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect", text = "Collect bags", amount = 3,
                current_amount = 0, sub_objectives = {},
            }
            OM:activate_objective("collect", nil, {amount = 3})

            local source_hud_panel = _make_panel("source_hud_panel")
            source_hud_panel._w = 1920; source_hud_panel._h = 1080
            local objectives_panel = source_hud_panel:panel({
                name = "objectives_panel", x = 0, y = 0, w = 500, h = 100, visible = true,
            })
            objectives_panel._alpha = 1

            local objective_text = objectives_panel:text({
                name = "objective_text", x = 34, y = 6, w = 180, h = 20,
                text = "Collect bags", visible = true,
            })
            objective_text._alpha = 0.37

            local amount_text = objectives_panel:text({
                name = "amount_text", x = 34, y = 24, w = 180, h = 20,
                text = "0/3", visible = true,
            })
            amount_text._alpha = 0.37

            local icon_objectivebox = objectives_panel:text({
                name = "icon_objectivebox", x = 0, y = 0, w = 24, h = 24, visible = true,
            })
            icon_objectivebox._alpha = 0.37

            local sentinel = objectives_panel:text({
                name = "sentinel_label", x = 0, y = 50, w = 100, h = 20,
                text = "sentinel", visible = true,
            })
            sentinel._alpha = 1

            local bg_box = objectives_panel:panel({
                name = "test_bg_box", x = 26, y = 0, w = 200, h = 38, visible = true,
            })
            bg_box._alpha = 1

            local bg = bg_box:text({name = "bg", x = 0, y = 0, w = 200, h = 38, visible = true})
            bg._alpha = 0.37
            local left_top = bg_box:text({name = "left_top", x = 0, y = 0, w = 8, h = 8, visible = true})
            left_top._alpha = 0.37
            local left_bottom = bg_box:text({name = "left_bottom", x = 0, y = 30, w = 8, h = 8, visible = true})
            left_bottom._alpha = 0.37
            local right_top = bg_box:text({name = "right_top", x = 192, y = 0, w = 8, h = 8, visible = true})
            right_top._alpha = 0.37
            local right_bottom = bg_box:text({name = "right_bottom", x = 192, y = 30, w = 8, h = 8, visible = true})
            right_bottom._alpha = 0.37

            local leaves = {
                objective_text, amount_text, icon_objectivebox,
                bg, left_top, left_bottom, right_top, right_bottom,
            }

            local originals = {}
            for i, leaf in ipairs(leaves) do
                originals[i] = {visible = leaf:visible(), alpha = leaf:alpha()}
            end
            for i, leaf in ipairs(leaves) do
                assert(originals[i].visible == true, "leaf " .. i .. " original must be visible=true")
            end

            managers.hud._hud_objectives = {
                _hud_panel = source_hud_panel, _bg_box = bg_box, _active_objective_id = "collect",
            }

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local O = kyohud.hud.objectives
            assert(O, "O must exist")

            RT:update(managers.hud, 1.0, 0.016)

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verify_render must be true, got " .. tostring(vr_base))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must be visible=false via NV, got " .. tostring(leaf:visible()))
            end

            local nv = kyohud.hud.native_visibility
            for i, leaf in ipairs(leaves) do
                local wl = nv._whitelist[leaf]
                assert(wl ~= nil, "whitelist must contain leaf " .. i)
                assert(wl.visible == true, "whitelist entry must have visible=true")
            end
            assert(nv._whitelist[objectives_panel] == nil, "whitelist must not contain objectives_panel")
            assert(nv._whitelist[bg_box] == nil, "whitelist must not contain bg_box")
            assert(nv._whitelist[sentinel] == nil, "whitelist must not contain sentinel")

            local owner_count = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count = owner_count + 1
                end
            end
            assert(owner_count == 8, "NV must have 8 owner entries, got " .. owner_count)

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible")
            assert(bg_box:visible() == true, "bg_box must remain visible")
            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")

            local saved_root = O._root_panel
            local saved_slot1_text = O._slot_prims[1] and O._slot_prims[1].text
            local saved_slot1_amount = O._slot_prims[1] and O._slot_prims[1].amount
            local saved_parent_w = O._parent_panel._w

            O._parent_panel._w = 0

            RT:update(managers.hud, 2.0, 0.016)

            local vr_fail = O:_verify_render()
            assert(vr_fail == false, "verify_render must be false with zero parent width, got " .. tostring(vr_fail))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == originals[i].visible,
                    "leaf " .. i .. " must be restored to original visible=true, got " .. tostring(leaf:visible()) .. " (NV NOT RELEASED)")
            end

            local owner_count_fail = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_fail = owner_count_fail + 1
                end
            end
            assert(owner_count_fail == 0, "NV owner entries must be gone, got " .. owner_count_fail)

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible after fail")
            assert(bg_box:visible() == true, "bg_box must remain visible after fail")
            assert(sentinel:visible() == true, "sentinel must remain visible after fail")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after fail")

            O._parent_panel._w = saved_parent_w

            RT:update(managers.hud, 3.0, 0.016)

            local vr_recover = O:_verify_render()
            assert(vr_recover == true, "verify_render must be true after restore, got " .. tostring(vr_recover))

            assert(O._root_panel == saved_root, "root panel identity must be preserved")
            assert(O._slot_prims[1].text == saved_slot1_text, "slot1 text identity must be preserved")
            assert(O._slot_prims[1].amount == saved_slot1_amount, "slot1 amount identity must be preserved")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must be visible=false via NV after recovery, got " .. tostring(leaf:visible()))
            end

            local owner_count_recover = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_recover = owner_count_recover + 1
                end
            end
            assert(owner_count_recover == 8, "NV must have 8 owner entries after recovery, got " .. owner_count_recover)

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible after recovery")
            assert(bg_box:visible() == true, "bg_box must remain visible after recovery")
            assert(sentinel:visible() == true, "sentinel must remain visible after recovery")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after recovery")
        ''')

    def test_reactivate_during_opening_transition(self):
        """RED: Reactivate same objective id during opening transition.

        Source OM quantitative objective (amount=3, current=0) with native
        HUDObjectives tree attached. RT mount + actual OM activate triggers
        HUDManager:activate_objective -> HUDObjectives:activate_objective,
        which sets title/amount visible=false and schedules open_right_done
        callback via bg_box:animate.

        Call native open_right_done(true) -> sets title=true, amount=true.
        With hooks installed: pre-release NV (restores native values), native
        runs, post re-acquire NV (hides all 8 again, stores old_value=true for
        all 8 including title/amount).

        Expected: rendered valid (_verify_render true), all 8 masked (visible=false),
        NV originals title=true, amount=true.

        Reactivate SAME objective id via OM -> triggers HUDObjectives:activate_objective
        again, which sets title=false, amount=false (new opening state). NV entries still
        have old_value=true for all 8. Disable via settings+RT.refresh immediately BEFORE
        open_right_done callback fires.

        Expected: native title=false, amount=false (new native opening state from
        activate_objective). But actual: NV release restores stale old_value=true,
        not the current false. Test expected RED: stale restore gives true/true.

        Other 6 leaves: original values (true). Parents/sentinel preserved.
        No owner NV entries after disable. No manual O/NV repair/whitelist edits.
        """
        lua, ok = _lua_with_native_hud_objectives()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true

            local source_hud_panel = _make_panel("source_hud_panel")
            source_hud_panel._w = 1920; source_hud_panel._h = 1080
            local objectives_panel = source_hud_panel:panel({
                name = "objectives_panel", x = 0, y = 0, w = 500, h = 100, visible = true,
            })
            objectives_panel._alpha = 1

            local icon_objectivebox = objectives_panel:text({
                name = "icon_objectivebox", x = 0, y = 0, w = 24, h = 24, visible = true,
            })
            icon_objectivebox._alpha = 0.37

            local objective_text = objectives_panel:text({
                name = "objective_text", x = 34, y = 6, w = 180, h = 20,
                text = "Collect bags", visible = false,
            })
            objective_text._alpha = 0.37

            local amount_text = objectives_panel:text({
                name = "amount_text", x = 34, y = 24, w = 180, h = 20,
                text = "0/3", visible = false,
            })
            amount_text._alpha = 0.37

            local sentinel = objectives_panel:text({
                name = "sentinel_label", x = 0, y = 50, w = 100, h = 20,
                text = "sentinel", visible = true,
            })
            sentinel._alpha = 1

            local bg_box = objectives_panel:panel({
                name = "test_bg_box", x = 26, y = 0, w = 200, h = 38, visible = true,
            })
            bg_box._alpha = 1

            local bg = bg_box:text({name = "bg", x = 0, y = 0, w = 200, h = 38, visible = true})
            bg._alpha = 0.37
            local left_top = bg_box:text({name = "left_top", x = 0, y = 0, w = 8, h = 8, visible = true})
            left_top._alpha = 0.37
            local left_bottom = bg_box:text({name = "left_bottom", x = 0, y = 30, w = 8, h = 8, visible = true})
            left_bottom._alpha = 0.37
            local right_top = bg_box:text({name = "right_top", x = 192, y = 0, w = 8, h = 8, visible = true})
            right_top._alpha = 0.37
            local right_bottom = bg_box:text({name = "right_bottom", x = 192, y = 30, w = 8, h = 8, visible = true})
            right_bottom._alpha = 0.37

            local leaves = {
                icon_objectivebox, objective_text, amount_text,
                bg, left_top, left_bottom, right_top, right_bottom,
            }

            local originals = {}
            for i, leaf in ipairs(leaves) do
                originals[i] = {visible = leaf:visible(), alpha = leaf:alpha()}
            end

            local native_obj = setmetatable({}, HUDObjectives)
            native_obj:init({panel = source_hud_panel})
            native_obj._bg_box = bg_box
            managers.hud._hud_objectives = native_obj
            managers.hud._hud_objectives._active_objective_id = "collect"

            local OM = _make_om()
            OM._objectives["collect"] = {
                id = "collect", text = "Collect bags", amount = 3,
                current_amount = 0, sub_objectives = {},
            }
            OM:activate_objective("collect", nil, {amount = 3})

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local O = kyohud.hud.objectives
            assert(O, "O must exist")

            RT:update(managers.hud, 1.0, 0.016)

            assert(O._mounted == true, "O must be mounted")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must be visible=false via NV after mount, got " .. tostring(leaf:visible()))
            end

            local nv = kyohud.hud.native_visibility
            for i, leaf in ipairs(leaves) do
                local wl_entry = nv._whitelist[leaf]
                assert(wl_entry ~= nil, "whitelist must contain leaf " .. i)
                assert(wl_entry.visible == true, "whitelist entry must have visible=true")
            end

            assert(nv._whitelist[objectives_panel] == nil, "whitelist must not contain objectives_panel")
            assert(nv._whitelist[bg_box] == nil, "whitelist must not contain bg_box")
            assert(nv._whitelist[sentinel] == nil, "whitelist must not contain sentinel")

            native_obj:open_right_done(true)

            assert(objective_text._stopped == true, "title stop must be called")
            assert(objective_text._animated == true, "title animate must be called")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must remain masked false after open_right_done, got " .. tostring(leaf:visible()))
            end

            local vr1 = O:_verify_render()
            assert(vr1 == true, "_verify_render must be true after open_right_done, got " .. tostring(vr1))

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible")
            assert(bg_box:visible() == true, "bg_box must remain visible")
            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")

            OM:activate_objective("collect", nil, {amount = 3})

            kyohud.settings.enable_objectives = false
            RT:refresh_settings(managers.hud)

            assert(objective_text:visible() == false,
                "title must be false after disable (new opening state), got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must be false after disable (new opening state), got " .. tostring(amount_text:visible()))

            for i, leaf in ipairs(leaves) do
                if leaf ~= objective_text and leaf ~= amount_text then
                    assert(leaf:visible() == originals[i].visible,
                        "leaf " .. i .. " must be restored to original visible, got " .. tostring(leaf:visible()))
                    assert(leaf:alpha() == originals[i].alpha,
                        "leaf " .. i .. " alpha must remain " .. originals[i].alpha)
                end
            end

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible after disable")
            assert(bg_box:visible() == true, "bg_box must remain visible after disable")
            assert(sentinel:visible() == true, "sentinel must remain visible after disable")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after disable")

            local owner_count = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count = owner_count + 1
                end
            end
            assert(owner_count == 0, "NV must have no owner entries after disable, got " .. owner_count)

            local owned_panel_gone = O._root_panel == nil or not O._root_panel._alive
            assert(owned_panel_gone == true, "owned panel must be gone after disable")
        ''')


    def test_third_party_conflict_detection(self):
        """Third-party sets native title visible=true bypassing callback.

        Source OM quantitative objective (amount=3, current=0) with native
        HUDObjectives tree attached (8 leaves all visible=true). RT mount +
        actual OM activate + native open_right_done(true) establishes baseline:
        O:_verify_render true, all 8 leaves hidden via NV, 8 NV owner entries.

        Simulate third-party by calling native objective_text:set_visible(true)
        directly, bypassing the callback chain. RT:update multiple times.

        Expected: title visible=true (preserve third-party change), other 7
        restored to original true, NV owner entries=0, O root visible=false,
        O:_verify_render false. No manual O/NV repair calls. Parents/alpha/
        sentinel unchanged throughout.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")

            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verify_render must be true, got " .. tostring(vr_base))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must be visible=false via NV at baseline, got " .. tostring(leaf:visible()))
                assert(leaf:alpha() == 0.37, "leaf " .. i .. " alpha must be .37 at baseline")
            end

            local owner_count_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_base = owner_count_base + 1
                end
            end
            assert(owner_count_base == 8, "NV must have 8 owner entries at baseline, got " .. owner_count_base)

            local root_visible_base = O._root_panel and O._root_panel:visible()
            assert(root_visible_base == true, "O root must be visible at baseline, got " .. tostring(root_visible_base))

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible at baseline")
            assert(bg_box:visible() == true, "bg_box must remain visible at baseline")
            assert(sentinel:visible() == true, "sentinel must remain visible at baseline")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 at baseline")

            objective_text:set_visible(true)

            assert(objective_text:visible() == true, "title must be true after third-party set_visible")

            RT:update(managers.hud, 2.0, 0.016)

            assert(objective_text:visible() == true,
                "title must be true after update 2, got " .. tostring(objective_text:visible()))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == true,
                    "leaf " .. i .. " must be visible=true after update 2, got " .. tostring(leaf:visible()))
                assert(leaf:alpha() == 0.37, "leaf " .. i .. " alpha must remain .37 after update 2")
            end

            local activecollect_retained_2 = #O._active == 1 and O._active[1].id == "collect"
            assert(activecollect_retained_2 == true, "activecollect must be retained after update 2")

            local owner_count_conflict = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_conflict = owner_count_conflict + 1
                end
            end
            assert(owner_count_conflict == 0,
                "NV owner entries must be 0 after update 2, got " .. owner_count_conflict)

            local root_visible_conflict = O._root_panel and O._root_panel:visible()
            assert(root_visible_conflict == false,
                "O root must be visible=false after update 2, got " .. tostring(root_visible_conflict))

            local vr_conflict = O:_verify_render()
            assert(vr_conflict == false,
                "verify_render must be false after update 2, got " .. tostring(vr_conflict))

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible after update 2")
            assert(bg_box:visible() == true, "bg_box must remain visible after update 2")
            assert(sentinel:visible() == true, "sentinel must remain visible after update 2")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after update 2")

            RT:update(managers.hud, 3.0, 0.016)

            assert(objective_text:visible() == true,
                "title must remain true on update 3, got " .. tostring(objective_text:visible()))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == true,
                    "leaf " .. i .. " must remain visible=true on update 3, got " .. tostring(leaf:visible()))
                assert(leaf:alpha() == 0.37, "leaf " .. i .. " alpha must remain .37 on update 3")
            end

            local activecollect_retained_3 = #O._active == 1 and O._active[1].id == "collect"
            assert(activecollect_retained_3 == true, "activecollect must be retained on update 3")

            local owner_count_update3 = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_update3 = owner_count_update3 + 1
                end
            end
            assert(owner_count_update3 == 0,
                "NV owner entries must be 0 on update 3, got " .. owner_count_update3)

            local root_visible_update3 = O._root_panel and O._root_panel:visible()
            assert(root_visible_update3 == false,
                "O root must remain visible=false on update 3, got " .. tostring(root_visible_update3))

            local vr_update3 = O:_verify_render()
            assert(vr_update3 == false,
                "verify_render must be false on update 3, got " .. tostring(vr_update3))

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible on update 3")
            assert(bg_box:visible() == true, "bg_box must remain visible on update 3")
            assert(sentinel:visible() == true, "sentinel must remain visible on update 3")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 on update 3")

            RT:update(managers.hud, 4.0, 0.016)

            assert(objective_text:visible() == true,
                "title must remain true on update 4, got " .. tostring(objective_text:visible()))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == true,
                    "leaf " .. i .. " must remain visible=true on update 4, got " .. tostring(leaf:visible()))
                assert(leaf:alpha() == 0.37, "leaf " .. i .. " alpha must remain .37 on update 4")
            end

            local activecollect_retained_4 = #O._active == 1 and O._active[1].id == "collect"
            assert(activecollect_retained_4 == true, "activecollect must be retained on update 4")

            local owner_count_update4 = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_update4 = owner_count_update4 + 1
                end
            end
            assert(owner_count_update4 == 0,
                "NV owner entries must be 0 on update 4, got " .. owner_count_update4)

            local root_visible_update4 = O._root_panel and O._root_panel:visible()
            assert(root_visible_update4 == false,
                "O root must remain visible=false on update 4, got " .. tostring(root_visible_update4))

            local vr_update4 = O:_verify_render()
            assert(vr_update4 == false,
                "verify_render must be false on update 4, got " .. tostring(vr_update4))

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible after updates")
            assert(bg_box:visible() == true, "bg_box must remain visible after updates")
            assert(sentinel:visible() == true, "sentinel must remain visible after updates")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after updates")
        ''')

    def test_tainted_native_leaf_replacement_recovery(self):
        """One tainted native leaf replacement recovery.

        Baseline via _lua_native_ready: owner=8, nativeHidden=true, rootVisible=true,
        verifier=true. Mutate native title visible=true; RTupdate2 -> established
        fallback: root=false, allnative originals=true, owner=0.

        Native SOURCE replace unrelated bg leaf first: box:remove(oldbg);
        box:text same name bg visible=true alpha=.37; update r.leaves reference
        only test fixture SOURCE table, not O. RTupdate3 -> MUST stay fallback:
        root=false, owner=0, allnative originals=true, because conflicting title
        same identity.

        Native SOURCE replace offending title leaf: parent:remove(oldtitle);
        parent:text name=objective_text text="Collect bags" visible=true alpha=.37,
        update source fixture leaves reference index for title. RTupdate4 -> MUST
        recover: SAME owned root/primitives visible=TRUE, verifier=TRUE, all current
        8 native leaves=false, owner=8, whitelist correct refs, old native title
        dead and no entries.

        This tests desired outcomes (NEVER assert current broken state as expected).
        No manual O/NV repair/cache clearing/whitelist mutation. Preserve parent/
        sentinel/alpha and activecollect unchanged.

        Expected failure: current unconditional fallback early-return prevents
        recovery at RTupdate4 even after title replacement.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel
            local bg = r.bg
            local icon_objectivebox = r.icon_objectivebox
            local amount_text = r.amount_text
            local left_top = r.left_top
            local left_bottom = r.left_bottom
            local right_top = r.right_top
            local right_bottom = r.right_bottom

            -- Baseline: owner=8, nativeHidden=true, rootVisible=true, verifier=true
            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true, got " .. tostring(vr_base))

            local root_visible_base = O._root_panel and O._root_panel:visible()
            assert(root_visible_base == true, "baseline rootVisible must be true, got " .. tostring(root_visible_base))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "baseline nativeHidden: leaf " .. i .. " must be false, got " .. tostring(leaf:visible()))
                assert(leaf:alpha() == 0.37, "baseline leaf " .. i .. " alpha must be .37")
            end

            local owner_count_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_base = owner_count_base + 1
                end
            end
            assert(owner_count_base == 8, "baseline owner must be 8, got " .. owner_count_base)

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible at baseline")
            assert(bg_box:visible() == true, "bg_box must remain visible at baseline")
            assert(sentinel:visible() == true, "sentinel must remain visible at baseline")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 at baseline")

            local activecollect_base = #O._active == 1 and O._active[1].id == "collect"
            assert(activecollect_base == true, "activecollect must be retained at baseline")

            local saved_root = O._root_panel
            local saved_slot1_text = O._slot_prims[1] and O._slot_prims[1].text
            local saved_slot1_amount = O._slot_prims[1] and O._slot_prims[1].amount

            -- Mutate native title visible=true
            objective_text:set_visible(true)
            assert(objective_text:visible() == true, "title must be true after mutation")

            -- RTupdate2
            RT:update(managers.hud, 2.0, 0.016)

            -- Fallback established: root=false, allnative originals=true, owner=0
            local root_visible_u2 = O._root_panel and O._root_panel:visible()
            assert(root_visible_u2 == false,
                "RTupdate2 rootVisible must be false (fallback), got " .. tostring(root_visible_u2))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == true,
                    "RTupdate2 allnative originals: leaf " .. i .. " must be true, got " .. tostring(leaf:visible()))
                assert(leaf:alpha() == 0.37, "RTupdate2 leaf " .. i .. " alpha must remain .37")
            end

            local owner_count_u2 = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_u2 = owner_count_u2 + 1
                end
            end
            assert(owner_count_u2 == 0, "RTupdate2 owner must be 0, got " .. owner_count_u2)

            local activecollect_u2 = #O._active == 1 and O._active[1].id == "collect"
            assert(activecollect_u2 == true, "activecollect must be retained at RTupdate2")

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible at RTupdate2")
            assert(bg_box:visible() == true, "bg_box must remain visible at RTupdate2")
            assert(sentinel:visible() == true, "sentinel must remain visible at RTupdate2")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 at RTupdate2")

            -- Native SOURCE replace unrelated bg leaf first
            local old_bg = r.bg
            bg_box:remove(old_bg)
            local new_bg = bg_box:text({name = "bg", x = 0, y = 0, w = 200, h = 38, visible = true})
            new_bg._alpha = 0.37
            r.leaves[4] = new_bg
            r.bg = new_bg

            -- Update local reference
            bg = new_bg

            -- RTupdate3
            RT:update(managers.hud, 3.0, 0.016)

            -- MUST stay fallback: root=false, owner=0, allnative originals=true
            local root_visible_u3 = O._root_panel and O._root_panel:visible()
            assert(root_visible_u3 == false,
                "RTupdate3 rootVisible must be false (fallback), got " .. tostring(root_visible_u3))

            for i, leaf in ipairs(r.leaves) do
                assert(leaf:visible() == true,
                    "RTupdate3 allnative originals: leaf " .. i .. " must be true, got " .. tostring(leaf:visible()))
                assert(leaf:alpha() == 0.37, "RTupdate3 leaf " .. i .. " alpha must remain .37")
            end

            local owner_count_u3 = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_u3 = owner_count_u3 + 1
                end
            end
            assert(owner_count_u3 == 0, "RTupdate3 owner must be 0 (fallback), got " .. owner_count_u3)

            local activecollect_u3 = #O._active == 1 and O._active[1].id == "collect"
            assert(activecollect_u3 == true, "activecollect must be retained at RTupdate3")

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible at RTupdate3")
            assert(bg_box:visible() == true, "bg_box must remain visible at RTupdate3")
            assert(sentinel:visible() == true, "sentinel must remain visible at RTupdate3")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 at RTupdate3")

            -- Native SOURCE replace offending title leaf
            local old_title = r.objective_text
            objectives_panel:remove(old_title)
            assert(alive(old_title) == false, "old native title must not be alive after source remove")
            local new_title = objectives_panel:text({
                name = "objective_text", x = 34, y = 6, w = 180, h = 20,
                text = "Collect bags", visible = true,
            })
            new_title._alpha = 0.37
            r.leaves[2] = new_title
            r.objective_text = new_title

            -- Update local reference
            objective_text = new_title

            -- RTupdate4
            RT:update(managers.hud, 4.0, 0.016)

            -- DESIRED recovery: SAME owned root/primitives visible=TRUE
            local root_visible_u4 = O._root_panel and O._root_panel:visible()
            assert(root_visible_u4 == true,
                "RTupdate4 DESIRED: rootVisible must be true (recovered), got " .. tostring(root_visible_u4))

            -- verifier=TRUE
            local vr_u4 = O:_verify_render()
            assert(vr_u4 == true,
                "RTupdate4 DESIRED: verifier must be true, got " .. tostring(vr_u4))

            -- All current 8 native leaves=false
            for i, leaf in ipairs(r.leaves) do
                assert(leaf:visible() == false,
                    "RTupdate4 DESIRED: leaf " .. i .. " must be false (hidden), got " .. tostring(leaf:visible()))
                assert(leaf:alpha() == 0.37, "RTupdate4 leaf " .. i .. " alpha must remain .37")
            end

            -- Owner=8, whitelist correct refs
            local owner_count_u4 = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_u4 = owner_count_u4 + 1
                end
            end
            assert(owner_count_u4 == 8, "RTupdate4 DESIRED: owner must be 8, got " .. owner_count_u4)

            -- Whitelist correct refs: all 8 current leaves in whitelist
            for i, leaf in ipairs(r.leaves) do
                local wl_entry = nv._whitelist[leaf]
                assert(wl_entry ~= nil, "RTupdate4 whitelist must contain current leaf " .. i)
                assert(wl_entry.visible == true, "RTupdate4 whitelist entry must have visible=true")
            end

            -- Old native title dead and no entries
            local old_title_entry = false
            for _, e in ipairs(nv._entries) do
                if e.object == old_title then
                    old_title_entry = true
                end
            end
            assert(old_title_entry == false, "RTupdate4 old native title must have no entries")

            assert(O._root_panel == saved_root, "RTupdate4 DESIRED: root panel identity must be preserved")
            assert(O._slot_prims[1].text == saved_slot1_text, "RTupdate4 DESIRED: slot1 text identity must be preserved")
            assert(O._slot_prims[1].amount == saved_slot1_amount, "RTupdate4 DESIRED: slot1 amount identity must be preserved")

            -- Also check old bg has no entries
            local old_bg_entry = false
            for _, e in ipairs(nv._entries) do
                if e.object == old_bg then
                    old_bg_entry = true
                end
            end
            assert(old_bg_entry == false, "RTupdate4 old bg leaf must have no entries")

            -- Preserve parent/sentinel/alpha and activecollect unchanged
            local activecollect_u4 = #O._active == 1 and O._active[1].id == "collect"
            assert(activecollect_u4 == true, "activecollect must be retained at RTupdate4")

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible at RTupdate4")
            assert(bg_box:visible() == true, "bg_box must remain visible at RTupdate4")
            assert(sentinel:visible() == true, "sentinel must remain visible at RTupdate4")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 at RTupdate4")
        ''')

    def test_rebuild_generation_retained_until_restore(self):
        """RED: RT:rebuild with broken title setter must retain old generation.

        Baseline via _lua_native_ready: 8 native hidden, owner=8, root visible=true,
        verifier=true. Save old_generation = O._native_generation.

        Break title setter (set_visible returns false). RT:rebuild(managers.hud) with
        same native 8-leaf source => RT._generation increments but O._native_generation
        MUST remain old (DESIRED). No new-generation NV entries created. Other 7 leaves
        restored to original true (setter OK). Title stays false (setter broken, restore
        fails). New owned root hidden to avoid overlay (DESIRED).

        Disable settings + RT:refresh while setter still broken => pending old-gen entry
        retained in NV.

        Repair setter. RT:update(3) while STILL DISABLED => title restored true, all 8
        native originals true, owner=0 whitelist cleared, source active retained.
        Parents/sentinel/alpha unchanged throughout. No manual O/NV repair calls.

        Expected current defect: O._native_generation overwritten to new gen after
        acquire fails, preventing subsequent restore of pending old entry.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            -- Baseline: 8 native hidden, owner=8, root visible=true, verifier=true
            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true, got " .. tostring(vr_base))
            local root_visible_base = O._root_panel and O._root_panel:visible()
            assert(root_visible_base == true, "baseline rootVisible must be true")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "baseline leaf " .. i .. " must be false, got " .. tostring(leaf:visible()))
            end

            local owner_count_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_base = owner_count_base + 1
                end
            end
            assert(owner_count_base == 8, "baseline owner must be 8, got " .. owner_count_base)

            local old_gen = O._native_generation
            assert(old_gen > 0, "old_gen must be > 0, got " .. tostring(old_gen))

            assert(objectives_panel:visible() == true, "objectives_panel must be visible at baseline")
            assert(bg_box:visible() == true, "bg_box must be visible at baseline")
            assert(sentinel:visible() == true, "sentinel must be visible at baseline")
            assert(sentinel:alpha() == 1, "sentinel alpha must be 1 at baseline")

            -- Break title setter (returns false only when v==true, delegates for false)
            local orig_set_visible = objective_text.set_visible
            objective_text.set_visible = function(self, v)
                if v == true then return false end
                return orig_set_visible(self, v)
            end

            -- RT:rebuild with same native 8-leaf source
            RT:rebuild(managers.hud)

            -- Prove graphical generation changed
            assert(RT._generation ~= old_gen,
                "RT._generation must have changed after rebuild, got " .. tostring(RT._generation))

            -- DESIRED: O._native_generation remains old (not overwritten to new gen)
            assert(O._native_generation == old_gen,
                "DESIRED: O._native_generation must remain " .. old_gen .. ", got " .. tostring(O._native_generation))

            -- No new-generation NV entries
            local new_gen_entries = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.generation ~= old_gen then
                    new_gen_entries = new_gen_entries + 1
                end
            end
            assert(new_gen_entries == 0,
                "DESIRED: no new-gen entries, got " .. new_gen_entries)

            -- Other 7 leaves restored to original true (setter OK for them)
            for i, leaf in ipairs(leaves) do
                if leaf ~= objective_text then
                    assert(leaf:visible() == true,
                        "leaf " .. i .. " must be restored true, got " .. tostring(leaf:visible()))
                end
            end

            -- Title stays false (setter broken, restore fails)
            assert(objective_text:visible() == false,
                "title must remain false (setter broken), got " .. tostring(objective_text:visible()))

            -- DESIRED: new owned root hidden to avoid overlay
            local root_visible_rebuild = O._root_panel and O._root_panel:visible()
            assert(root_visible_rebuild == false,
                "DESIRED: new owned root must be hidden after rebuild, got " .. tostring(root_visible_rebuild))

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible after rebuild")
            assert(bg_box:visible() == true, "bg_box must remain visible after rebuild")
            assert(sentinel:visible() == true, "sentinel must remain visible after rebuild")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after rebuild")

            -- Pending old-gen entry retained in NV (title)
            local pending_count = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.generation == old_gen then
                    pending_count = pending_count + 1
                end
            end
            assert(pending_count == 1,
                "pending old-gen entry must be retained, got " .. pending_count)

            -- Disable settings + RT:refresh while setter still broken
            kyohud.settings.enable_objectives = false
            RT:refresh_settings(managers.hud)

            -- Pending old-gen entry still retained
            local pending_after_disable = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.generation == old_gen then
                    pending_after_disable = pending_after_disable + 1
                end
            end
            assert(pending_after_disable == 1,
                "pending old-gen entry must be retained after disable, got " .. pending_after_disable)

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible after disable")
            assert(bg_box:visible() == true, "bg_box must remain visible after disable")
            assert(sentinel:visible() == true, "sentinel must remain visible after disable")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after disable")

            -- Repair setter
            objective_text.set_visible = orig_set_visible

            -- RT:update(3) while STILL DISABLED
            RT:update(managers.hud, 3.0, 0.016)

            -- DESIRED: title restored true, all 8 native originals true
            assert(objective_text:visible() == true,
                "DESIRED: title must be true after repair+update, got " .. tostring(objective_text:visible()))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == true,
                    "DESIRED: leaf " .. i .. " must be true after repair+update, got " .. tostring(leaf:visible()))
                assert(leaf:alpha() == 0.37, "leaf " .. i .. " alpha must remain .37")
            end

            -- Owner=0 whitelist cleared
            local owner_count_final = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_final = owner_count_final + 1
                end
            end
            assert(owner_count_final == 0,
                "DESIRED: owner must be 0 after repair+update, got " .. owner_count_final)

            -- Whitelist cleared for all 8 leaves
            for i, leaf in ipairs(leaves) do
                assert(nv._whitelist[leaf] == nil,
                    "DESIRED: whitelist must be cleared for leaf " .. i)
            end

            -- Source active retained
            local activecollect = #O._active == 1 and O._active[1].id == "collect"
            assert(activecollect == true, "activecollect must be retained")

            -- Parents/sentinel/alpha unchanged
            assert(objectives_panel:visible() == true, "objectives_panel must remain visible")
            assert(bg_box:visible() == true, "bg_box must remain visible")
            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")
        ''')

    def test_native_completion_coroutine_characterization(self):
        """Native completion coroutine characterization.

        Baseline via _lua_native_ready: owner=8, nativeHidden=true, valid.

        Execute scheduled native show_text coroutine on title -> native title/amount
        alpha=1 but stay masked false, NV properties visible ONLY.

        Through real OM complete_objective calls reach final completion (3 steps for
        quantity 3): update_amount(1) -> "1/3", update_amount(2) -> "2/3",
        remove_objective -> native complete_objective schedules _animate_complete_objective.
        Assert intermediate values, completion callback scheduled.

        Execute actual scheduled completion coroutine on native objectives_panel ->
        title/amount visible=false alpha=1, bg_box close_right scheduled.
        Execute actual close-right coroutine on bg_box -> bg_box w=0, done_cb ->
        title text="", objectives_panel visible=false.

        Assert: NV owner=0, source empty, owned texts cleared.

        Disable O via settings+RT.refresh AFTER native coroutine end -> native stays
        false, no stale restoration true, parents/sentinel values changed only by
        native original and sibling visible property untouched, no NV owner entries.

        This is a characterization test - no fabricated RED.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local amount_text = r.amount_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel
            local native_obj = r.native_obj

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "baseline leaf " .. i .. " must be false, got " .. tostring(leaf:visible()))
            end

            local owner_count_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_base = owner_count_base + 1
                end
            end
            assert(owner_count_base == 8, "baseline owner must be 8")

            assert(objective_text._scheduled_fn ~= nil, "show_text must be scheduled on title")
            _run_coroutine(objective_text, 200)

            assert(objective_text:alpha() == 1,
                "title alpha must be 1 after show_text, got " .. tostring(objective_text:alpha()))
            assert(amount_text:alpha() == 1,
                "amount alpha must be 1 after show_text, got " .. tostring(amount_text:alpha()))
            assert(objective_text:visible() == false,
                "title must remain masked false after show_text, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must remain masked false after show_text, got " .. tostring(amount_text:visible()))

            local alpha_entry_count = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "alpha" then
                    alpha_entry_count = alpha_entry_count + 1
                end
            end
            assert(alpha_entry_count == 0,
                "NV must have no alpha entries, got " .. alpha_entry_count)

            local OM = managers.objectives

            OM:complete_objective("collect")
            assert(O._slot_prims[1].amount:text() == "1/3",
                "owned amount must be 1/3 after call 1, got " .. tostring(O._slot_prims[1].amount:text()))
            assert(amount_text:text() == "1/3",
                "native amount must be 1/3 after call 1, got " .. tostring(amount_text:text()))

            OM:complete_objective("collect")
            assert(O._slot_prims[1].amount:text() == "2/3",
                "owned amount must be 2/3 after call 2, got " .. tostring(O._slot_prims[1].amount:text()))
            assert(amount_text:text() == "2/3",
                "native amount must be 2/3 after call 2, got " .. tostring(amount_text:text()))

            OM:complete_objective("collect")
            assert(managers.objectives._active_objectives["collect"] == nil,
                "OM registry must be cleared after call 3")
            assert(#O._active == 0,
                "O._active must be empty after call 3, got " .. #O._active)
            assert(O._slot_prims[1].text:text() == "Collect bags",
                "owned title must be retained after call 3, got " .. tostring(O._slot_prims[1].text:text()))
            assert(O._slot_prims[1].amount:text() == "3/3",
                "owned amount must be retained after call 3, got " .. tostring(O._slot_prims[1].amount:text()))
            assert(O._slot_prims[1].text:visible() == true,
                "owned title must be visible after call 3")
            assert(O._slot_prims[1].amount:visible() == true,
                "owned amount must be visible after call 3")

            RT:update(managers.hud, 1.600, .600)
            RT:update(managers.hud, 1.900, .300)
            RT:update(managers.hud, 2.200, .300)

            assert(O._slot_prims[1].text:text() == "",
                "owned title must be empty after RT:update, got " .. tostring(O._slot_prims[1].text:text()))
            assert(O._slot_prims[1].amount:text() == "",
                "owned amount must be empty after RT:update, got " .. tostring(O._slot_prims[1].amount:text()))
            assert(O._slot_prims[1].text:visible() == false,
                "owned title must be hidden after RT:update")
            assert(O._slot_prims[1].amount:visible() == false,
                "owned amount must be hidden after RT:update")

            local owner_count_immediate = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_immediate = owner_count_immediate + 1
                end
            end
            assert(owner_count_immediate == 8,
                "NV owner must be 8 during native completion, got " .. owner_count_immediate)

            assert(objectives_panel._scheduled_fn ~= nil,
                "completion callback must be scheduled on objectives_panel")

            _run_coroutine(objectives_panel, 200)

            assert(objective_text:visible() == false,
                "title must be false after completion coroutine")
            assert(amount_text:visible() == false,
                "amount must be false after completion coroutine")
            assert(objective_text:alpha() == 1,
                "title alpha must be 1 after completion coroutine")
            assert(amount_text:alpha() == 1,
                "amount alpha must be 1 after completion coroutine")
            assert(bg_box._scheduled_fn ~= nil,
                "close_right must be scheduled on bg_box")

            _run_coroutine(bg_box, 200)

            assert(bg_box:w() == 0,
                "bg_box w must be 0 after close_right, got " .. tostring(bg_box:w()))
            assert(objective_text:text() == "",
                "title text must be empty after close_right, got " .. tostring(objective_text:text()))
            assert(objectives_panel:visible() == false,
                "objectives_panel must be false after close_right")

            local owner_count_after = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_after = owner_count_after + 1
                end
            end
            assert(owner_count_after == 0,
                "NV owner must be 0 after completion, got " .. owner_count_after)

            kyohud.settings.enable_objectives = false
            RT:refresh_settings(managers.hud)

            assert(objective_text:visible() == false,
                "title must stay false after disable, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must stay false after disable, got " .. tostring(amount_text:visible()))
            assert(objectives_panel:visible() == false,
                "objectives_panel must stay false after disable")

            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")

            local owner_count_final = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_final = owner_count_final + 1
                end
            end
            assert(owner_count_final == 0,
                "NV owner must be 0 after disable, got " .. owner_count_final)
        ''')


    def test_owned_root_engine_destruction_recovery(self):
        """RED: Owned root destroyed by engine without NV release.

        Baseline via _lua_native_ready: owner=8, nativeHidden=true, valid.
        Record owned root/slot primitives, runtime generation, heist generation,
        source active/collect.

        Simulate engine destroying owned root: O._root_panel._alive=false (no manual repair).

        RT:update(2) DESIRED: _verify_render false, all 8 native originals TRUE (released),
        owner=0; runtime generation/heist generation/source unchanged.

        Next eligible RT:update(3) DESIRED: owned root alive DIFFERENT from dead root,
        actual valid render/selected source preserved, native all FALSE, owner=8,
        fresh owned primitives not dead originals.

        No manual O.mount/update or NV calls/whitelist modifications.
        Native parent/sentinel/alpha unchanged.

        Current broken: O:update dead root branch sets _mounted=false and returns without
        release, so native stays false after tick 2 (meaningful failure).
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "baseline leaf " .. i .. " must be false")
            end

            local owner_count_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_base = owner_count_base + 1
                end
            end
            assert(owner_count_base == 8, "baseline owner must be 8")

            local saved_root = O._root_panel
            local saved_slot1_text = O._slot_prims[1] and O._slot_prims[1].text
            local saved_slot1_amount = O._slot_prims[1] and O._slot_prims[1].amount
            local saved_rt_gen = RT._generation
            local saved_heist_gen = RT._heist_generation
            local activecollect_base = #O._active == 1 and O._active[1].id == "collect"
            assert(activecollect_base == true, "activecollect must be retained")

            assert(objectives_panel:visible() == true, "objectives_panel must be visible")
            assert(bg_box:visible() == true, "bg_box must be visible")
            assert(sentinel:visible() == true, "sentinel must be visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must be 1")

            O._root_panel._alive = false

            RT:update(managers.hud, 2.0, 0.016)

            local vr_u2 = O:_verify_render()
            assert(vr_u2 == false,
                "DESIRED tick2: verifier must be false, got " .. tostring(vr_u2))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == true,
                    "DESIRED tick2: leaf " .. i .. " must be true (released), got " .. tostring(leaf:visible()))
            end

            local owner_count_u2 = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_u2 = owner_count_u2 + 1
                end
            end
            assert(owner_count_u2 == 0,
                "DESIRED tick2: owner must be 0, got " .. owner_count_u2)

            assert(RT._generation == saved_rt_gen,
                "DESIRED tick2: RT generation must be unchanged")
            assert(RT._heist_generation == saved_heist_gen,
                "DESIRED tick2: heist generation must be unchanged")

            local activecollect_u2 = #O._active == 1 and O._active[1].id == "collect"
            assert(activecollect_u2 == true, "activecollect must be retained at tick2")

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible at tick2")
            assert(bg_box:visible() == true, "bg_box must remain visible at tick2")
            assert(sentinel:visible() == true, "sentinel must remain visible at tick2")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 at tick2")

            RT:update(managers.hud, 3.0, 0.016)

            local new_root = O._root_panel
            assert(new_root ~= nil, "DESIRED tick3: owned root must exist")
            assert(new_root ~= saved_root,
                "DESIRED tick3: owned root must be DIFFERENT from dead root")
            assert(new_root._alive == true,
                "DESIRED tick3: new owned root must be alive")

            local vr_u3 = O:_verify_render()
            assert(vr_u3 == true,
                "DESIRED tick3: verifier must be true, got " .. tostring(vr_u3))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "DESIRED tick3: leaf " .. i .. " must be false (hidden), got " .. tostring(leaf:visible()))
            end

            local owner_count_u3 = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_u3 = owner_count_u3 + 1
                end
            end
            assert(owner_count_u3 == 8,
                "DESIRED tick3: owner must be 8, got " .. owner_count_u3)

            local new_slot1_text = O._slot_prims[1] and O._slot_prims[1].text
            local new_slot1_amount = O._slot_prims[1] and O._slot_prims[1].amount
            assert(new_slot1_text ~= saved_slot1_text,
                "DESIRED tick3: slot1 text must be DIFFERENT from dead original")
            assert(new_slot1_amount ~= saved_slot1_amount,
                "DESIRED tick3: slot1 amount must be DIFFERENT from dead original")

            local activecollect_u3 = #O._active == 1 and O._active[1].id == "collect"
            assert(activecollect_u3 == true, "activecollect must be retained at tick3")

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible at tick3")
            assert(bg_box:visible() == true, "bg_box must remain visible at tick3")
            assert(sentinel:visible() == true, "sentinel must remain visible at tick3")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 at tick3")
        ''')

    def test_restitution_getter_throw_characterization(self):
        """Characterize restitution getter throw on title leaf.

        Baseline via _lua_native_ready: owner=8, nativeHidden=true, valid render.
        Save original title visible getter, override to throw.
        Disable via settings + RT:refresh_settings.
        Pending entry for title with original generation retained, O._native_leaves
        reference present, whitelist entry present.
        Other 7 restored true, owned root gone, parents/sentinel/alpha untouched.
        Restore getter. RT:update while still disabled.
        Title true, owner=0, whitelist removed, source active preserved.
        No direct O/NV repair/cache/whitelist injection.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true")

            local owner_count_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_base = owner_count_base + 1
                end
            end
            assert(owner_count_base == 8, "baseline owner must be 8")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "baseline leaf " .. i .. " must be false")
            end

            local old_gen = O._native_generation
            assert(old_gen > 0, "old_gen must be > 0")

            assert(objectives_panel:visible() == true, "objectives_panel must be visible")
            assert(bg_box:visible() == true, "bg_box must be visible")
            assert(sentinel:visible() == true, "sentinel must be visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must be 1")

            local orig_visible = objective_text.visible
            objective_text.visible = function(self)
                error("getter throw test")
            end

            kyohud.settings.enable_objectives = false
            RT:refresh_settings(managers.hud)

            local pending_title = false
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.object == objective_text and e.generation == old_gen then
                    pending_title = true
                end
            end
            assert(pending_title == true, "pending title entry must be retained")

            assert(O._native_leaves ~= nil, "O._native_leaves must exist")
            local native_leaves_ref = false
            for _, leaf in ipairs(O._native_leaves) do
                if leaf == objective_text then
                    native_leaves_ref = true
                    break
                end
            end
            assert(native_leaves_ref == true, "O._native_leaves must reference title")

            assert(nv._whitelist[objective_text] ~= nil, "whitelist must contain title")

            for i, leaf in ipairs(leaves) do
                if leaf ~= objective_text then
                    assert(leaf:visible() == true,
                        "leaf " .. i .. " must be restored true, got " .. tostring(leaf:visible()))
                end
            end

            local owned_root_gone = O._root_panel == nil or not O._root_panel._alive
            assert(owned_root_gone == true, "owned root must be gone")

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible")
            assert(bg_box:visible() == true, "bg_box must remain visible")
            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")

            objective_text.visible = orig_visible

            RT:update(managers.hud, 2.0, 0.016)

            assert(objective_text:visible() == true,
                "title must be true after restore, got " .. tostring(objective_text:visible()))

            for i, leaf in ipairs(leaves) do
                assert(leaf:alpha() == 0.37,
                    "after repair leaf " .. i .. " alpha must remain .37, got " .. tostring(leaf:alpha()))
            end

            assert(objectives_panel:alpha() == 1, "objectives_panel alpha must remain 1 after repair")
            assert(bg_box:alpha() == 1, "bg_box alpha must remain 1 after repair")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after repair")

            local owner_count_final = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_final = owner_count_final + 1
                end
            end
            assert(owner_count_final == 0, "owner must be 0 after restore")

            for i, leaf in ipairs(leaves) do
                assert(nv._whitelist[leaf] == nil,
                    "whitelist must be cleared for leaf " .. i .. " after repair")
            end

            assert(nv._whitelist[objective_text] == nil, "whitelist must be cleared for title")

            local activecollect = #O._active == 1 and O._active[1].id == "collect"
            assert(activecollect == true, "activecollect must be retained")
        ''')

    def test_source_replace_transition_characterization(self):
        """Source replace transition characterization.

        Baseline via _lua_native_ready: 8 hidden, owner=8, valid. Build new
        3+5 native tree with new HUDObjectives instance (same active collect).
        Keep old leaves alive. RT:update: old 8 restored, whitelist cleared,
        new 8 hidden with exactly one record each, owned primitive identity
        and objective data preserved. Disable via RT refresh: new originals
        restored, no owner records, native parent/sibling/alpha preserved.

        This is characterization - no fabricated RED.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local old_leaves = r.leaves
            local old_objectives_panel = r.objectives_panel
            local old_bg_box = r.bg_box
            local old_sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true")

            for i, leaf in ipairs(old_leaves) do
                assert(leaf:visible() == false,
                    "baseline leaf " .. i .. " must be false")
            end

            local owner_count_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_base = owner_count_base + 1
                end
            end
            assert(owner_count_base == 8, "baseline owner must be 8")

            local saved_root = O._root_panel
            local saved_slot1_text = O._slot_prims[1] and O._slot_prims[1].text
            local saved_slot1_amount = O._slot_prims[1] and O._slot_prims[1].amount

            local function build_new_tree()
                local new_hud_panel = _make_panel("new_hud_panel")
                new_hud_panel._w = 1920; new_hud_panel._h = 1080
                local new_obj_panel = new_hud_panel:panel({
                    name = "objectives_panel", x = 0, y = 0, w = 500, h = 100, visible = true,
                })
                new_obj_panel._alpha = 1

                local new_icon = new_obj_panel:text({
                    name = "icon_objectivebox", x = 0, y = 0, w = 24, h = 24, visible = true,
                })
                new_icon._alpha = 0.37

                local new_title = new_obj_panel:text({
                    name = "objective_text", x = 34, y = 6, w = 180, h = 20,
                    text = "Collect bags", visible = true,
                })
                new_title._alpha = 0.37

                local new_amount = new_obj_panel:text({
                    name = "amount_text", x = 34, y = 24, w = 180, h = 20,
                    text = "0/3", visible = true,
                })
                new_amount._alpha = 0.37

                local new_sentinel = new_obj_panel:text({
                    name = "sentinel_label", x = 0, y = 50, w = 100, h = 20,
                    text = "sentinel", visible = true,
                })
                new_sentinel._alpha = 1

                local new_bg_box = new_obj_panel:panel({
                    name = "test_bg_box", x = 26, y = 0, w = 200, h = 38, visible = true,
                })
                new_bg_box._alpha = 1

                local new_bg = new_bg_box:text({name = "bg", x = 0, y = 0, w = 200, h = 38, visible = true})
                new_bg._alpha = 0.37
                local new_lt = new_bg_box:text({name = "left_top", x = 0, y = 0, w = 8, h = 8, visible = true})
                new_lt._alpha = 0.37
                local new_lb = new_bg_box:text({name = "left_bottom", x = 0, y = 30, w = 8, h = 8, visible = true})
                new_lb._alpha = 0.37
                local new_rt = new_bg_box:text({name = "right_top", x = 192, y = 0, w = 8, h = 8, visible = true})
                new_rt._alpha = 0.37
                local new_rb = new_bg_box:text({name = "right_bottom", x = 192, y = 30, w = 8, h = 8, visible = true})
                new_rb._alpha = 0.37

                local new_leaves = {
                    new_icon, new_title, new_amount,
                    new_bg, new_lt, new_lb, new_rt, new_rb,
                }

                local new_native = setmetatable({}, HUDObjectives)
                new_native:init({panel = new_hud_panel})
                new_native._bg_box = new_bg_box
                new_native._active_objective_id = "collect"

                return new_hud_panel, new_obj_panel, new_bg_box, new_sentinel, new_leaves, new_native
            end

            local new_hud_panel, new_obj_panel, new_bg_box, new_sentinel, new_leaves, new_native = build_new_tree()

            managers.hud._hud_objectives = new_native

            RT:update(managers.hud, 2.0, 0.016)

            for i, leaf in ipairs(old_leaves) do
                assert(leaf:visible() == true,
                    "old leaf " .. i .. " must be restored true, got " .. tostring(leaf:visible()))
            end

            for i, leaf in ipairs(old_leaves) do
                assert(nv._whitelist[leaf] == nil,
                    "whitelist must be cleared for old leaf " .. i)
            end

            for i, leaf in ipairs(new_leaves) do
                assert(leaf:visible() == false,
                    "new leaf " .. i .. " must be hidden, got " .. tostring(leaf:visible()))
            end

            for i, leaf in ipairs(new_leaves) do
                local count = 0
                for _, e in ipairs(nv._entries) do
                    if e.owner == O and e.object == leaf and e.property == "visible" then
                        count = count + 1
                    end
                end
                assert(count == 1, "new leaf " .. i .. " must have exactly one record, got " .. count)
            end

            assert(O._root_panel == saved_root, "root panel identity must be preserved")
            assert(O._slot_prims[1].text == saved_slot1_text, "slot1 text identity must be preserved")
            assert(O._slot_prims[1].amount == saved_slot1_amount, "slot1 amount identity must be preserved")

            local activecollect = #O._active == 1 and O._active[1].id == "collect"
            assert(activecollect == true, "activecollect must be retained")

            assert(old_objectives_panel:visible() == true, "old objectives_panel must remain visible")
            assert(old_bg_box:visible() == true, "old bg_box must remain visible")
            assert(old_sentinel:visible() == true, "old sentinel must remain visible")
            assert(old_sentinel:alpha() == 1, "old sentinel alpha must remain 1")

            kyohud.settings.enable_objectives = false
            RT:refresh_settings(managers.hud)

            for i, leaf in ipairs(new_leaves) do
                assert(leaf:visible() == true,
                    "new leaf " .. i .. " must be restored true, got " .. tostring(leaf:visible()))
            end

            local owner_count_final = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_final = owner_count_final + 1
                end
            end
            assert(owner_count_final == 0, "owner must be 0 after disable")

            assert(new_obj_panel:visible() == true, "new objectives_panel must remain visible")
            assert(new_bg_box:visible() == true, "new bg_box must remain visible")
            assert(new_sentinel:visible() == true, "new sentinel must remain visible")
            assert(new_sentinel:alpha() == 1, "new sentinel alpha must remain 1")
        ''')

    def test_native_acquisition_failure_safe_fallback_retry(self):
        """Native acquisition failure -> safe fallback -> retry.

        Baseline via _lua_native_ready: owner=8, leaves hidden, verify=true,
        root visible=true. Disable via settings+RT:refresh -> restored native
        originals (true), owner=0. Save native title set_visible, replace setter
        to return false ONLY when requested false (when true delegate original),
        native leaf stays true. Re-enable via settings+RT:refresh: actual NV
        acquisition must fail and rollback any preceding writes; require native
        leaves true/no owner records, owned root visible FALSE, _verify_render
        FALSE (no overlay of restored native). Preserve source and native
        parents/alphas/sibling. Repair setter then RT:update: require same owned
        root/text primitives visible true and valid, all8 native hidden with 8
        records. Final disable restores leaves. No manual O/NV repair/cache/
        whitelist changes.

        Current suspected defect: _sync_native_visibility stores acquired false
        but never hides owned root on acquire failure; desired assertion owned
        root false must fail (exposing defect), not an inverted baseline.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "baseline leaf " .. i .. " must be false")
            end

            local owner_count_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_base = owner_count_base + 1
                end
            end
            assert(owner_count_base == 8, "baseline owner must be 8")

            local root_visible_base = O._root_panel and O._root_panel:visible()
            assert(root_visible_base == true, "baseline root must be visible")

            assert(objectives_panel:visible() == true, "objectives_panel must be visible")
            assert(bg_box:visible() == true, "bg_box must be visible")
            assert(sentinel:visible() == true, "sentinel must be visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must be 1")

            kyohud.settings.enable_objectives = false
            RT:refresh_settings(managers.hud)

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == true,
                    "after disable leaf " .. i .. " must be true")
            end

            local owner_count_disable = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_disable = owner_count_disable + 1
                end
            end
            assert(owner_count_disable == 0, "after disable owner must be 0")

            local orig_set_visible = objective_text.set_visible
            objective_text.set_visible = function(self, v)
                if v == false then return false end
                return orig_set_visible(self, v)
            end

            assert(objective_text:visible() == true, "title must stay true after break")

            kyohud.settings.enable_objectives = true
            RT:refresh_settings(managers.hud)

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == true,
                    "DESIRED after re-enable leaf " .. i .. " must be true, got " .. tostring(leaf:visible()))
            end

            local owner_count_reenable = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_reenable = owner_count_reenable + 1
                end
            end
            assert(owner_count_reenable == 0,
                "DESIRED after re-enable owner must be 0, got " .. owner_count_reenable)

            local root_visible_reenable = O._root_panel and O._root_panel:visible()
            assert(root_visible_reenable == false,
                "DESIRED after re-enable owned root must be hidden (false), got " .. tostring(root_visible_reenable))

            local saved_root_fail = O._root_panel
            local saved_title_fail = O._slot_prims[1] and O._slot_prims[1].text
            local saved_amount_fail = O._slot_prims[1] and O._slot_prims[1].amount

            for i, leaf in ipairs(leaves) do
                assert(leaf:alpha() == 0.37,
                    "after re-enable leaf " .. i .. " alpha must be .37, got " .. tostring(leaf:alpha()))
            end

            assert(objectives_panel:alpha() == 1, "objectives_panel alpha must remain 1 after re-enable")
            assert(bg_box:alpha() == 1, "bg_box alpha must remain 1 after re-enable")

            local vr_reenable = O:_verify_render()
            assert(vr_reenable == false,
                "DESIRED after re-enable verifier must be false, got " .. tostring(vr_reenable))

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible after re-enable")
            assert(bg_box:visible() == true, "bg_box must remain visible after re-enable")
            assert(sentinel:visible() == true, "sentinel must remain visible after re-enable")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after re-enable")

            objective_text.set_visible = orig_set_visible

            RT:update(managers.hud, 2.0, 0.016)

            local root_visible_update = O._root_panel and O._root_panel:visible()
            assert(root_visible_update == true,
                "after update owned root must be visible, got " .. tostring(root_visible_update))

            assert(O._root_panel == saved_root_fail,
                "root panel identity must survive failure+recovery")
            assert(O._slot_prims[1].text == saved_title_fail,
                "slot1 text identity must survive failure+recovery")
            assert(O._slot_prims[1].amount == saved_amount_fail,
                "slot1 amount identity must survive failure+recovery")

            for i, leaf in ipairs(leaves) do
                assert(leaf:alpha() == 0.37,
                    "after update leaf " .. i .. " alpha must be .37, got " .. tostring(leaf:alpha()))
            end

            assert(objectives_panel:alpha() == 1, "objectives_panel alpha must remain 1 after update")
            assert(bg_box:alpha() == 1, "bg_box alpha must remain 1 after update")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after update")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "after update leaf " .. i .. " must be false, got " .. tostring(leaf:visible()))
            end

            local owner_count_update = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_update = owner_count_update + 1
                end
            end
            assert(owner_count_update == 8,
                "after update owner must be 8, got " .. owner_count_update)

            local vr_update = O:_verify_render()
            assert(vr_update == true,
                "after update verifier must be true, got " .. tostring(vr_update))

            kyohud.settings.enable_objectives = false
            RT:refresh_settings(managers.hud)

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == true,
                    "after final disable leaf " .. i .. " must be true, got " .. tostring(leaf:visible()))
            end

            local owner_count_final = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then
                    owner_count_final = owner_count_final + 1
                end
            end
            assert(owner_count_final == 0,
                "after final disable owner must be 0, got " .. owner_count_final)

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible after final disable")
            assert(bg_box:visible() == true, "bg_box must remain visible after final disable")
            assert(sentinel:visible() == true, "sentinel must remain visible after final disable")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after final disable")
        ''')


    def test_immediate_objective_announcement_transition(self):
        """Immediate objective announcement transition characterization.

        Baseline via _lua_native_ready: "collect" acquired, rendered, 8 masked.
        Remove "collect" via OM:remove_objective to allow immediate activation.
        (Removal legitimately releases NV because no selected active id remains.)
        Introduce NEW "escape" via OM:activate_objective immediate (no active objs).
        Native OM path: HUD notify BEFORE registry insertion.
        Production on_om_activate updates O._active, sync_if_mounted.
        Native HUDManager:activate_objective -> HUDObjectives:activate_objective.
        HUDObjectives PRE hook: releases NV (8 leaves restored to originals).
        Native body: sets title=false, amount=false, schedules open_right_done.
        After OM:activate_objective returns:
          - Owned text shows "Escape" (sync_if_mounted updated primitives)
          - 8 native leaves masked, owner=8, verifier true (desired)
        Run native open_right_done(false):
          - PRE hook: releases NV (already released)
          - Native body: sets title=true, amount=false (uses_amount=false)
          - POST hook: re-acquires NV (hides all 8)
        After open_right_done:
          - 8 native leaves masked, owner=8
          - Owned text still shows "Escape"
        Preserve parent/sentinel/alpha throughout.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local amount_text = r.amount_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel
            local native_obj = r.native_obj
            local OM = managers.objectives

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "baseline leaf " .. i .. " must be false")
            end

            local owner_count_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_base = owner_count_base + 1
                end
            end
            assert(owner_count_base == 8, "baseline owner must be 8")

            OM:remove_objective("collect", nil)

            assert(#O._active == 0, "O._active must be empty after remove")
            assert(O._slot_prims[1].text:text() == "",
                "owned title must be empty after remove")

            OM._objectives["escape"] = {
                id = "escape", text = "Escape the area", amount = nil,
                current_amount = nil, sub_objectives = {},
            }
            OM:activate_objective("escape", nil, {})

            assert(#O._active == 1, "O._active must have 1 entry")
            assert(O._active[1].id == "escape", "active must be escape")
            assert(O._active[1].pending == false, "escape must not be pending")
            assert(O._slot_prims[1].text:text() == "Escape the area",
                "owned title must show escape text")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must be masked on callback return, got " .. tostring(leaf:visible()))
            end

            local owner_count_immediate = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_immediate = owner_count_immediate + 1
                end
            end
            assert(owner_count_immediate == 8, "owner must be 8 on callback return")

            local vr_immediate = O:_verify_render()
            assert(vr_immediate == true, "verifier must be true on callback return")

            native_obj:open_right_done(false)

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must be masked after open_right_done, got " .. tostring(leaf:visible()))
            end

            local owner_count_after = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_after = owner_count_after + 1
                end
            end
            assert(owner_count_after == 8, "owner must be 8 after open_right_done")

            assert(O._slot_prims[1].text:text() == "Escape the area",
                "owned title must still show escape after open_right_done")

            local vr_after = O:_verify_render()
            assert(vr_after == true, "verifier must be true after open_right_done")

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible")
            assert(bg_box:visible() == true, "bg_box must remain visible")
            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")
        ''')

    def test_delayed_objective_announcement_transition(self):
        """Delayed objective announcement transition characterization.

        Baseline via _lua_native_ready: "collect" acquired, rendered, 8 masked.
        Introduce NEW "escape" via OM:activate_objective with explicit
        {delay_presentation = true}. Native OM path: registry insertion, set
        _delayed_presentation (because active objectives exist).
        Production on_om_activate: sees delayed_presentation, sets pending=true.
        After OM:activate_objective returns:
          - O._active has "escape" with pending=true
          - select_visible filters pending, so owned text still shows "collect"
          - 8 native leaves still masked (NV not touched, no HUD notify yet)
        OM:update with dt=2 expires timer, triggers HUD notify.
        Native OM update: managers.hud:activate_objective.
        Production on_hud_activate: clears pending flag, sync_if_mounted.
        Native HUDManager:activate_objective -> HUDObjectives:activate_objective.
        HUDObjectives PRE hook: releases NV (8 leaves restored).
        Native body: sets title=false, amount=false, schedules open_right_done.
        After OM:update returns:
          - O._active "escape" pending=false
          - Owned text shows "Escape" (sync_if_mounted updated)
          - 8 native leaves masked, owner=8, verifier true (desired)
        Run native open_right_done(false):
          - PRE hook: releases NV (already released)
          - Native body: sets title=true, amount=false
          - POST hook: re-acquires NV (hides all 8)
        After open_right_done:
          - 8 native leaves masked, owner=8
          - Owned text still shows "Escape"
        Preserve parent/sentinel/alpha throughout.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local amount_text = r.amount_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel
            local native_obj = r.native_obj
            local OM = managers.objectives

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "baseline leaf " .. i .. " must be false")
            end

            local owner_count_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_base = owner_count_base + 1
                end
            end
            assert(owner_count_base == 8, "baseline owner must be 8")

            assert(O._slot_prims[1].text:text() == "Collect bags",
                "baseline owned title must show collect")

            OM._objectives["escape"] = {
                id = "escape", text = "Escape the area", amount = nil,
                current_amount = nil, sub_objectives = {},
            }
            OM:activate_objective("escape", nil, {delay_presentation = true})

            assert(#O._active == 2, "O._active must have 2 entries")
            assert(O._active[2].id == "escape", "second active must be escape")
            assert(O._active[2].pending == true, "escape must be pending")

            assert(O._slot_prims[1].text:text() == "Collect bags",
                "owned title must still show collect (escape pending)")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must still be masked (no HUD notify yet)")
            end

            OM:update(2.0, 2.0)

            assert(OM._delayed_presentation == nil, "delayed_presentation must be cleared")
            assert(O._active[2].pending == false, "escape must not be pending after update")
            assert(O._slot_prims[1].text:text() == "Escape the area",
                "owned title must show escape after update")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must be masked on callback return, got " .. tostring(leaf:visible()))
            end

            local owner_count_immediate = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_immediate = owner_count_immediate + 1
                end
            end
            assert(owner_count_immediate == 8, "owner must be 8 on callback return")

            local vr_immediate = O:_verify_render()
            assert(vr_immediate == true, "verifier must be true on callback return")

            native_obj:open_right_done(false)

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must be masked after open_right_done, got " .. tostring(leaf:visible()))
            end

            local owner_count_after = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_after = owner_count_after + 1
                end
            end
            assert(owner_count_after == 8, "owner must be 8 after open_right_done")

            assert(O._slot_prims[1].text:text() == "Escape the area",
                "owned title must still show escape after open_right_done")

            local vr_after = O:_verify_render()
            assert(vr_after == true, "verifier must be true after open_right_done")

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible")
            assert(bg_box:visible() == true, "bg_box must remain visible")
            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")
        ''')

    def test_desired_no_flash_during_native_completion(self):
        """Desired contract regression: no native flash during completion coroutine.

        Baseline via _lua_native_ready: 8 masked, owner=8, verifier true.
        Complete "collect" 3 times via real OM:complete_objective. After 3rd,
        O._active empty, completion pre-hook sets pending (owner=8, NOT released),
        native complete_objective schedules _animate_complete_objective on
        objectives_panel.

        Create coroutine from objectives_panel._scheduled_fn with _scheduled_args.
        Resume once initially (first resume yields and ownership remains8
        until ORIGINAL finishes),
        then 10 times with dt=0.016 (total ~0.176s, well within 0.5s blink window).
        Assert coroutine is "suspended" (not dead).

        DESIRED: objective_text:visible()==false (no flash), all 8 leaves
        visible==false, even though alpha may be 1 from blink.

        CURRENT RED: release at final OM removal (not first-resume PostHook)
        sets all 8 to visible=true; the assertion on
        objective_text:visible()==false fails because leaves are restored to
        original visible=true before the coroutine finishes.

        Preserve parents/sentinel/alpha throughout. No manual O/NV repair.
        This is a desired-contract regression -- not a characterization.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local amount_text = r.amount_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "baseline leaf " .. i .. " must be false")
            end

            local owner_count_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_count_base = owner_count_base + 1
                end
            end
            assert(owner_count_base == 8, "baseline owner must be 8")

            local OM = managers.objectives
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            assert(#O._active == 0, "O._active must be empty after 3 completes")

            assert(objectives_panel._scheduled_fn ~= nil,
                "native completion coroutine must be scheduled on objectives_panel")

            local fn = objectives_panel._scheduled_fn
            local args = objectives_panel._scheduled_args or {}
            local co = coroutine.create(fn)
            local ok_r, err_r = coroutine.resume(co, objectives_panel, unpack(args))
            assert(ok_r, "first resume failed: " .. tostring(err_r))

            for i = 1, 10 do
                if i == 5 then
                    RT:update(managers.hud, 2.0, 0.016)
                    local owner_mid = 0
                    for _, e in ipairs(nv._entries) do
                        if e.owner == O and e.property == "visible" then
                            owner_mid = owner_mid + 1
                        end
                    end
                    assert(owner_mid == 8,
                        "DESIRED: owner must be 8 after mid-blink RT:update, got " .. owner_mid)
                    for j, l in ipairs(leaves) do
                        assert(l:visible() == false,
                            "DESIRED: leaf " .. j .. " must remain masked after mid-blink RT:update, got " .. tostring(l:visible()))
                    end
                    assert(objective_text:alpha() == 1,
                        "DESIRED: title alpha must be 1 after mid-blink RT:update, got " .. tostring(objective_text:alpha()))
                    assert(amount_text:alpha() == 1,
                        "DESIRED: amount alpha must be 1 after mid-blink RT:update, got " .. tostring(amount_text:alpha()))
                end
                assert(coroutine.status(co) == "suspended",
                    "coroutine should be suspended at step " .. i .. ", got " .. coroutine.status(co))
                local ok2, err2 = coroutine.resume(co, 0.016)
                assert(ok2, "resume failed at step " .. i .. ": " .. tostring(err2))
            end

            assert(coroutine.status(co) == "suspended",
                "coroutine should still be suspended after 11 resumes, got " .. coroutine.status(co))

            assert(objective_text:alpha() == 1,
                "title alpha must be 1 at observed midpoint, got " .. tostring(objective_text:alpha()))
            assert(amount_text:alpha() == 1,
                "amount alpha must be 1 at observed midpoint, got " .. tostring(amount_text:alpha()))

            assert(objective_text:visible() == false,
                "DESIRED: title must remain masked false during blink, got " .. tostring(objective_text:visible()))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "DESIRED: leaf " .. i .. " must remain masked during blink, got " .. tostring(leaf:visible()))
            end

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible")
            assert(bg_box:visible() == true, "bg_box must remain visible")
            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")
        ''')

    def test_disable_before_native_completion_start(self):
        """Disable before native completion coroutine starts.

        Baseline via _lua_native_ready. Complete collect 3 times via real OM ->
        completion pre-hook sets pending (owner=8), native coroutine scheduled on
        objectives_panel. BEFORE running any coroutine step, disable O via
        settings+RT.refresh. Owned panel gone, pending cleared, NV releases
        (owner=0), native leaves restored to originals.

        Run native completion coroutine to completion via _run_coroutine
        (blinks, sets title/amount visible=false alpha=1, schedules close_right).
        Run close_right via _run_coroutine (bg_box w=0, text="", panel false).

        Assert: title/amount visible==false after native finish (native set them,
        not stale NV restore). No manual O/NV repair. Parents/sentinel untouched.
        NV owner=0 throughout.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local amount_text = r.amount_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")

            local OM = managers.objectives
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            assert(#O._active == 0, "O._active must be empty after 3 completes")
            assert(objectives_panel._scheduled_fn ~= nil,
                "native completion coroutine must be scheduled")

            kyohud.settings.enable_objectives = false
            RT:refresh_settings(managers.hud)

            local owned_gone = O._root_panel == nil or not O._root_panel._alive
            assert(owned_gone == true, "owned panel must be gone after disable")

            assert(objective_text:visible() == true,
                "title must restore native true immediately on disable, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == true,
                "amount must restore native true immediately on disable, got " .. tostring(amount_text:visible()))

            _run_coroutine(objectives_panel, 200)

            assert(objective_text:visible() == false,
                "title must be false after native completion, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must be false after native completion, got " .. tostring(amount_text:visible()))
            assert(objective_text:alpha() == 1,
                "title alpha must be 1 after completion, got " .. tostring(objective_text:alpha()))
            assert(amount_text:alpha() == 1,
                "amount alpha must be 1 after completion, got " .. tostring(amount_text:alpha()))

            assert(bg_box._scheduled_fn ~= nil,
                "close_right must be scheduled after completion coroutine")
            _run_coroutine(bg_box, 200)

            assert(bg_box:w() == 0,
                "bg_box w must be 0 after close_right, got " .. tostring(bg_box:w()))
            assert(objective_text:text() == "",
                "title text must be empty after close_right, got " .. tostring(objective_text:text()))
            assert(objectives_panel:visible() == false,
                "objectives_panel must be false after close_right")

            assert(objective_text:visible() == false,
                "title must remain false after full native finish, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must remain false after full native finish, got " .. tostring(amount_text:visible()))

            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")

            local owner_final = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_final = owner_final + 1 end
            end
            assert(owner_final == 0,
                "NV owner must be 0 after native finish, got " .. owner_final)
        ''')

    def test_disable_during_partial_native_completion(self):
        """Disable during partial native completion coroutine.

        Baseline via _lua_native_ready. Complete collect 3 times -> completion
        pre-hook sets pending (owner=8), native coroutine scheduled. Create
        coroutine from objectives_panel. Resume initially then 4 more times with
        dt=0.016 (partial blink, ~0.08s of 0.5s total). Assert suspended.

        Disable O via settings+RT.refresh. Owned panel gone.

        Resume remaining coroutine steps until dead (native finishes blink,
        sets title/amount visible=false, schedules close_right).
        Run close_right via _run_coroutine to completion.

        Assert: title/amount visible==false after native finish. No stale true
        restoration. Parents/sentinel untouched. NV owner=0.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local amount_text = r.amount_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")

            local OM = managers.objectives
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            assert(#O._active == 0, "O._active must be empty after 3 completes")
            assert(objectives_panel._scheduled_fn ~= nil,
                "native completion coroutine must be scheduled")

            local fn = objectives_panel._scheduled_fn
            local args = objectives_panel._scheduled_args or {}
            local co = coroutine.create(fn)
            local ok_r, err_r = coroutine.resume(co, objectives_panel, unpack(args))
            assert(ok_r, "first resume failed: " .. tostring(err_r))

            for i = 1, 4 do
                assert(coroutine.status(co) == "suspended",
                    "coroutine should be suspended at partial step " .. i)
                local ok2, err2 = coroutine.resume(co, 0.016)
                assert(ok2, "resume failed at partial step " .. i .. ": " .. tostring(err2))
            end
            assert(coroutine.status(co) == "suspended",
                "coroutine should be suspended after 5 resumes")

            assert(objective_text:visible() == false,
                "title must remain masked false during partial blink, got " .. tostring(objective_text:visible()))
            assert(objective_text:alpha() == 1,
                "title alpha must be 1 at observed midpoint, got " .. tostring(objective_text:alpha()))

            kyohud.settings.enable_objectives = false
            RT:refresh_settings(managers.hud)

            local owned_gone = O._root_panel == nil or not O._root_panel._alive
            assert(owned_gone == true, "owned panel must be gone after disable")

            assert(objective_text:visible() == true,
                "title must restore native true immediately on disable, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == true,
                "amount must restore native true immediately on disable, got " .. tostring(amount_text:visible()))

            while coroutine.status(co) ~= "dead" do
                local ok2, err2 = coroutine.resume(co, 0.016)
                assert(ok2, "resume failed during drain: " .. tostring(err2))
            end

            assert(objective_text:visible() == false,
                "title must be false after native completion, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must be false after native completion, got " .. tostring(amount_text:visible()))
            assert(objective_text:alpha() == 1,
                "title alpha must be 1 after completion, got " .. tostring(objective_text:alpha()))
            assert(amount_text:alpha() == 1,
                "amount alpha must be 1 after completion, got " .. tostring(amount_text:alpha()))

            assert(bg_box._scheduled_fn ~= nil,
                "close_right must be scheduled after completion coroutine")
            _run_coroutine(bg_box, 200)

            assert(bg_box:w() == 0,
                "bg_box w must be 0 after close_right, got " .. tostring(bg_box:w()))
            assert(objective_text:text() == "",
                "title text must be empty after close_right")
            assert(objectives_panel:visible() == false,
                "objectives_panel must be false after close_right")

            assert(objective_text:visible() == false,
                "title must remain false after full native finish, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must remain false after full native finish, got " .. tostring(amount_text:visible()))

            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")

            local owner_final = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_final = owner_final + 1 end
            end
            assert(owner_final == 0,
                "NV owner must be 0 after native finish, got " .. owner_final)
        ''')

    def test_disable_after_native_completion(self):
        """Disable after native completion fully finished.

        Baseline via _lua_native_ready. Complete collect 3 times -> completion
        pre-hook sets pending (owner=8), native coroutine scheduled. Run coroutine
        to completion via _run_coroutine (PostHook fires after native blink
        finishes and visible=false written: release owner=0; blink finishes,
        sets title/amount visible=false, schedules
        close_right). Run close_right via _run_coroutine (bg_box w=0, text="",
        panel false).

        THEN disable O via settings+RT.refresh. Owned panel gone.

        Assert: title/amount visible==false after disable (native set them false,
        no stale true restoration). Parents/sentinel untouched. NV owner=0.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local amount_text = r.amount_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")

            local OM = managers.objectives
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            assert(#O._active == 0, "O._active must be empty after 3 completes")
            assert(objectives_panel._scheduled_fn ~= nil,
                "native completion coroutine must be scheduled")

            _run_coroutine(objectives_panel, 200)

            assert(objective_text:visible() == false,
                "title must be false after native completion, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must be false after native completion, got " .. tostring(amount_text:visible()))

            assert(bg_box._scheduled_fn ~= nil,
                "close_right must be scheduled")
            _run_coroutine(bg_box, 200)

            assert(bg_box:w() == 0,
                "bg_box w must be 0 after close_right, got " .. tostring(bg_box:w()))
            assert(objective_text:text() == "",
                "title text must be empty after close_right")
            assert(objectives_panel:visible() == false,
                "objectives_panel must be false after close_right")

            assert(objective_text:visible() == false,
                "title must be false before disable, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must be false before disable, got " .. tostring(amount_text:visible()))

            kyohud.settings.enable_objectives = false
            RT:refresh_settings(managers.hud)

            local owned_gone = O._root_panel == nil or not O._root_panel._alive
            assert(owned_gone == true, "owned panel must be gone after disable")

            assert(objective_text:visible() == false,
                "title must remain false after disable, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must remain false after disable, got " .. tostring(amount_text:visible()))

            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")
            assert(objectives_panel:visible() == false,
                "objectives_panel must remain false after disable")

            local owner_final = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_final = owner_final + 1 end
            end
            assert(owner_final == 0,
                "NV owner must be 0 after disable, got " .. owner_final)
        ''')

    def test_disable_after_blink_before_close(self):
        """Disable after blink completed but before close_right runs.

        Baseline via _lua_native_ready. Complete collect 3 times via real OM.
        PreHook on complete_objective bound pending; _sync_native_visibility
        retains ownership (no active_id, pending valid, fallback). Native
        _animate_complete_objective coroutine scheduled on objectives_panel.

        Run blink coroutine to completion via _run_coroutine (title/amount
        visible=false alpha=1, close_right scheduled but NOT run). PostHook
        on _animate_complete_objective reconciled title/amount old_value=false,
        retained pending and ownership (release deferred to close_right).

        RT:update: title/amount remain false, owner=8 (pending retained).
        Disable O via settings+RT.refresh: owned panel gone, pending cleared,
        NV releases reconciled values (title/amount false, other 6 true).
        Assert: title/amount remain false after disable, owner=0. NV owner=0.
        Parents/sentinel untouched.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local amount_text = r.amount_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")

            local OM = managers.objectives
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            assert(#O._active == 0, "O._active must be empty after 3 completes")
            assert(objectives_panel._scheduled_fn ~= nil,
                "native completion coroutine must be scheduled")

            _run_coroutine(objectives_panel, 200)

            assert(objective_text:visible() == false,
                "title must be false after blink, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must be false after blink, got " .. tostring(amount_text:visible()))
            assert(objective_text:alpha() == 1,
                "title alpha must be 1 after blink, got " .. tostring(objective_text:alpha()))
            assert(amount_text:alpha() == 1,
                "amount alpha must be 1 after blink, got " .. tostring(amount_text:alpha()))

            assert(bg_box._scheduled_fn ~= nil,
                "close_right must be scheduled but not run")

            local owner_after_blink = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_after_blink = owner_after_blink + 1 end
            end
            assert(owner_after_blink == 8,
                "NV owner must be 8 after blink (reconciled, release deferred), got " .. owner_after_blink)

            RT:update(managers.hud, 5.0, 0.016)

            assert(objective_text:visible() == false,
                "title must remain false immediately on RT:update, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must remain false immediately on RT:update, got " .. tostring(amount_text:visible()))

            local owner_after_update = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_after_update = owner_after_update + 1 end
            end
            assert(owner_after_update == 8,
                "NV owner must be 8 after RT:update (pending retained), got " .. owner_after_update)

            kyohud.settings.enable_objectives = false
            RT:refresh_settings(managers.hud)

            local owned_gone = O._root_panel == nil or not O._root_panel._alive
            assert(owned_gone == true, "owned panel must be gone after disable")

            assert(objective_text:visible() == false,
                "title must remain false after disable, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must remain false after disable, got " .. tostring(amount_text:visible()))

            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")

            local owner_final = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_final = owner_final + 1 end
            end
            assert(owner_final == 0,
                "NV owner must be 0 after disable, got " .. owner_final)
        ''')

    def test_render_failure_during_blink_release_no_stale_restore(self):
        """Regression: render failure during blink -> release -> no stale restore.

        Baseline via _lua_native_ready: owner=8, 8 masked, verifier true.
        Complete collect 3 times via real OM -> completion pre-hook sets pending
        (owner=8). Native coroutine scheduled on objectives_panel.

        Create coroutine from objectives_panel._scheduled_fn. First resume:
        coroutine yields (suspended), PostHook has NOT fired yet because the
        original coroutine has not finished. Assert: suspended, owner=8, all 8
        leaves hidden false.

        Corrupt OWNED primitive O._slot_prims[1].text.text_rect to return huge
        extents (NOT native objective_text.text_rect). RT:update: _verify_render
        false -> release triggers -> owner=0, all 8 native leaves restored to
        original true.

        Restore owned primitive text_rect. Drain the ACTUAL same coroutine
        until dead. Coroutine body sets title/amount visible=false alpha=1 via
        direct native calls (no NV involved since owner=0).

        Assert: title=false, amount=false (native set them, not stale restore).
        Other 6 leaves true (restored by release, not touched by coroutine).
        NV owner=0. No re-acquisition. Parents/sentinel untouched.
        No manual O/NV repair. Do NOT assert release before render failure.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local amount_text = r.amount_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "baseline leaf " .. i .. " must be false")
            end

            local owner_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_base = owner_base + 1
                end
            end
            assert(owner_base == 8, "baseline owner must be 8")

            local OM = managers.objectives
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            assert(#O._active == 0, "O._active must be empty after 3 completes")
            assert(objectives_panel._scheduled_fn ~= nil,
                "native completion coroutine must be scheduled")

            local owner_after_complete = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_after_complete = owner_after_complete + 1 end
            end
            assert(owner_after_complete == 8,
                "owner must be 8 after 3 completes (pending set, not released), got " .. owner_after_complete)

            local fn = objectives_panel._scheduled_fn
            local args = objectives_panel._scheduled_args or {}
            local co = coroutine.create(fn)
            local ok_r, err_r = coroutine.resume(co, objectives_panel, unpack(args))
            assert(ok_r, "first resume failed: " .. tostring(err_r))

            assert(coroutine.status(co) == "suspended",
                "coroutine must be suspended after first resume, got " .. coroutine.status(co))

            local owner_after_first_resume = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_after_first_resume = owner_after_first_resume + 1 end
            end
            assert(owner_after_first_resume == 8,
                "owner must remain 8 after first resume (PostHook not yet fired), got " .. owner_after_first_resume)

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must remain hidden false after first resume, got " .. tostring(leaf:visible()))
            end

            local owned_title = O._slot_prims[1] and O._slot_prims[1].text
            assert(owned_title, "owned title primitive must exist")
            local orig_text_rect = owned_title.text_rect
            function owned_title:text_rect() return 0, 0, 99999, 99999 end

            RT:update(managers.hud, 2.0, 0.016)

            local vr_fail = O:_verify_render()
            assert(vr_fail == false,
                "verifier must be false with corrupted text_rect, got " .. tostring(vr_fail))

            local owner_after_fail = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_after_fail = owner_after_fail + 1 end
            end
            assert(owner_after_fail == 0,
                "owner must be 0 after failed RT:update (release triggered), got " .. owner_after_fail)

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == true,
                    "leaf " .. i .. " must be restored true after release, got " .. tostring(leaf:visible()))
            end

            owned_title.text_rect = orig_text_rect

            while coroutine.status(co) ~= "dead" do
                local ok2, err2 = coroutine.resume(co, 0.016)
                assert(ok2, "resume failed during drain: " .. tostring(err2))
            end

            assert(objective_text:visible() == false,
                "title must be false after coroutine finish, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must be false after coroutine finish, got " .. tostring(amount_text:visible()))
            assert(objective_text:alpha() == 1,
                "title alpha must be 1 after coroutine finish, got " .. tostring(objective_text:alpha()))
            assert(amount_text:alpha() == 1,
                "amount alpha must be 1 after coroutine finish, got " .. tostring(amount_text:alpha()))

            for i, leaf in ipairs(leaves) do
                if leaf ~= objective_text and leaf ~= amount_text then
                    assert(leaf:visible() == true,
                        "non-title/amount leaf " .. i .. " must stay true, got " .. tostring(leaf:visible()))
                end
            end

            local owner_final = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_final = owner_final + 1 end
            end
            assert(owner_final == 0,
                "NV owner must be 0 after coroutine finish, got " .. owner_final)

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible")
            assert(bg_box:visible() == true, "bg_box must remain visible")
            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")
        ''')

    def test_native_frame_remains_hidden_through_close(self):
        """DESIRED contract: native frame stays hidden through close sequence.

        Baseline via _lua_native_ready: owner=8, 8 masked, verifier true.
        Complete collect 3 times via real OM:completion pre-hook sets pending
        (owner=8). Native _animate_complete_objective coroutine scheduled on
        objectives_panel.

        Run blink coroutine to completion via _run_coroutine (title/amount
        visible=false alpha=1, close_right scheduled). PostHook on
        _animate_complete_objective reconciles title/amount old_value=false,
        retains pending and ownership (release deferred to close_right).

        After blink: owner=8, all 8 leaves still masked false, objectives_panel
        visible true, bg_box w>0, close_right coroutine scheduled.

        Create coroutine from bg_box._scheduled_fn (close_right). Resume
        initially + one dt=0.016: still suspended, bg_box w>0, all leaves
        still masked false, owner=8.

        RT:update: all leaves still masked, owner=8.

        Drain same close coroutine until dead: done_cb fires -> panel=false,
        text="", bg_box w=0. PostHook on HUDBGBox_animate_close_right fires
        after native coroutine returns (w=0, done_cb called): clears pending,
        releases NV.

        After close: owner=0 (event boundary), original leaf visibilities
        restored EXCEPT title/amount native false (reconciled, not stale
        restore). Parent/alpha/sentinel untouched throughout.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local amount_text = r.amount_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "baseline leaf " .. i .. " must be false")
            end

            local owner_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_base = owner_base + 1
                end
            end
            assert(owner_base == 8, "baseline owner must be 8")

            local OM = managers.objectives
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            assert(#O._active == 0, "O._active must be empty after 3 completes")
            assert(objectives_panel._scheduled_fn ~= nil,
                "native completion coroutine must be scheduled")

            _run_coroutine(objectives_panel, 200)

            assert(objective_text:visible() == false,
                "title must be false after blink, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must be false after blink, got " .. tostring(amount_text:visible()))
            assert(objective_text:alpha() == 1,
                "title alpha must be 1 after blink, got " .. tostring(objective_text:alpha()))
            assert(amount_text:alpha() == 1,
                "amount alpha must be 1 after blink, got " .. tostring(amount_text:alpha()))

            assert(bg_box._scheduled_fn ~= nil,
                "close_right must be scheduled after blink")

            local bg_box_w_before = bg_box:w()
            assert(bg_box_w_before > 0,
                "bg_box w must be > 0 before close, got " .. tostring(bg_box_w_before))

            assert(objectives_panel:visible() == true,
                "objectives_panel must remain visible after blink")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "DESIRED: leaf " .. i .. " must remain masked false after blink, got " .. tostring(leaf:visible()))
            end

            local owner_after_blink = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_after_blink = owner_after_blink + 1 end
            end
            assert(owner_after_blink == 8,
                "DESIRED: NV owner must be 8 after blink (not released), got " .. owner_after_blink)

            local fn = bg_box._scheduled_fn
            local args = bg_box._scheduled_args or {}
            local co = coroutine.create(fn)
            local ok_r, err_r = coroutine.resume(co, bg_box, unpack(args))
            assert(ok_r, "first resume of close_right failed: " .. tostring(err_r))

            assert(coroutine.status(co) == "suspended",
                "close_right must be suspended after first resume, got " .. coroutine.status(co))

            local ok2, err2 = coroutine.resume(co, 0.016)
            assert(ok2, "second resume of close_right failed: " .. tostring(err2))

            assert(coroutine.status(co) == "suspended",
                "close_right must still be suspended after 2 resumes, got " .. coroutine.status(co))

            local bg_box_w_after_2 = bg_box:w()
            assert(bg_box_w_after_2 > 0,
                "DESIRED: bg_box w must be > 0 after 2 resumes, got " .. tostring(bg_box_w_after_2))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "DESIRED: leaf " .. i .. " must remain masked during close, got " .. tostring(leaf:visible()))
            end

            local owner_during_close = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_during_close = owner_during_close + 1 end
            end
            assert(owner_during_close == 8,
                "DESIRED: NV owner must be 8 during close, got " .. owner_during_close)

            RT:update(managers.hud, 2.0, 0.016)

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "DESIRED: leaf " .. i .. " must remain masked after RT:update, got " .. tostring(leaf:visible()))
            end

            local owner_after_update = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_after_update = owner_after_update + 1 end
            end
            assert(owner_after_update == 8,
                "DESIRED: NV owner must be 8 after RT:update, got " .. owner_after_update)

            while coroutine.status(co) ~= "dead" do
                local ok3, err3 = coroutine.resume(co, 0.016)
                assert(ok3, "resume failed during drain: " .. tostring(err3))
            end

            assert(bg_box:w() == 0,
                "bg_box w must be 0 after close_right, got " .. tostring(bg_box:w()))
            assert(objective_text:text() == "",
                "title text must be empty after close_right, got " .. tostring(objective_text:text()))
            assert(objectives_panel:visible() == false,
                "objectives_panel must be false after close_right")

            local owner_after_close = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_after_close = owner_after_close + 1 end
            end
            assert(owner_after_close == 0,
                "DESIRED: NV owner must be 0 after close (event boundary), got " .. owner_after_close)

            assert(objective_text:visible() == false,
                "title must remain false after close (native set), got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must remain false after close (native set), got " .. tostring(amount_text:visible()))

            for i, leaf in ipairs(leaves) do
                if leaf ~= objective_text and leaf ~= amount_text then
                    assert(leaf:visible() == true,
                        "DESIRED: leaf " .. i .. " must be restored true after close, got " .. tostring(leaf:visible()))
                end
            end

            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")
            assert(objectives_panel:alpha() == 1, "objectives_panel alpha must remain 1")
            assert(bg_box:alpha() == 1, "bg_box alpha must remain 1")
        ''')

    def test_disable_during_partial_close_unrelated_box_no_release(self):
        """Disable during partial close with unrelated close_right box.

        Baseline via _lua_native_ready: owner=8, 8 masked, verifier true.
        Complete collect 3 times via real OM: pending set, blink scheduled.
        Run blink coroutine to completion: PostHook reconciles title/amount
        old_value=false, retains pending and ownership (owner=8).

        Create coroutine from bg_box._scheduled_fn (close_right). Resume
        initially + one dt=0.016: still suspended, bg_box w>0, all leaves
        still masked false, owner=8 (no flash through partial close).

        Create unrelated box, schedule HUDBGBox_animate_close_right on it,
        run to completion via _run_coroutine. PostHook fires but panel check
        fails (unrelated box != pending bg_box). Assert ownership NOT released
        (owner still 8), all leaves still masked false.

        Disable O via settings+RT.refresh. Owned panel gone, pending cleared,
        NV releases reconciled values (title/amount false, other 6 true).
        Assert: title/amount false after disable, owner=0. Parents/sentinel
        untouched throughout.
        """
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute('''
            local r = _test_refs
            local O = r.O
            local nv = r.nv
            local RT = r.RT
            local leaves = r.leaves
            local objective_text = r.objective_text
            local amount_text = r.amount_text
            local objectives_panel = r.objectives_panel
            local bg_box = r.bg_box
            local sentinel = r.sentinel

            assert(O._mounted == true, "O must be mounted")
            local vr_base = O:_verify_render()
            assert(vr_base == true, "baseline verifier must be true")

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "baseline leaf " .. i .. " must be false")
            end

            local owner_base = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O and e.property == "visible" then
                    owner_base = owner_base + 1
                end
            end
            assert(owner_base == 8, "baseline owner must be 8")

            local OM = managers.objectives
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            assert(#O._active == 0, "O._active must be empty after 3 completes")
            assert(objectives_panel._scheduled_fn ~= nil,
                "native completion coroutine must be scheduled")

            _run_coroutine(objectives_panel, 200)

            assert(objective_text:visible() == false,
                "title must be false after blink, got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must be false after blink, got " .. tostring(amount_text:visible()))

            assert(bg_box._scheduled_fn ~= nil,
                "close_right must be scheduled after blink")

            local owner_after_blink = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_after_blink = owner_after_blink + 1 end
            end
            assert(owner_after_blink == 8,
                "NV owner must be 8 after blink (reconciled, release deferred), got " .. owner_after_blink)

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must remain masked false after blink, got " .. tostring(leaf:visible()))
            end

            local fn = bg_box._scheduled_fn
            local args = bg_box._scheduled_args or {}
            local co = coroutine.create(fn)
            local ok_r, err_r = coroutine.resume(co, bg_box, unpack(args))
            assert(ok_r, "first resume of close_right failed: " .. tostring(err_r))

            assert(coroutine.status(co) == "suspended",
                "close_right must be suspended after first resume, got " .. coroutine.status(co))

            local ok2, err2 = coroutine.resume(co, 0.016)
            assert(ok2, "second resume of close_right failed: " .. tostring(err2))

            assert(coroutine.status(co) == "suspended",
                "close_right must still be suspended after 2 resumes, got " .. coroutine.status(co))

            local bg_box_w_after_2 = bg_box:w()
            assert(bg_box_w_after_2 > 0,
                "bg_box w must be > 0 after 2 resumes, got " .. tostring(bg_box_w_after_2))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must remain masked during partial close, got " .. tostring(leaf:visible()))
            end

            local owner_during_close = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_during_close = owner_during_close + 1 end
            end
            assert(owner_during_close == 8,
                "NV owner must be 8 during partial close, got " .. owner_during_close)

            local unrelated_box = _make_panel("unrelated_close_box")
            unrelated_box._w = 100
            unrelated_box._h = 38
            unrelated_box._alpha = 1
            unrelated_box._scheduled_fn = HUDBGBox_animate_close_right
            unrelated_box._scheduled_args = {function() end}
            _run_coroutine(unrelated_box, 200)

            assert(unrelated_box:w() == 0,
                "unrelated box w must be 0 after its close_right, got " .. tostring(unrelated_box:w()))

            for i, leaf in ipairs(leaves) do
                assert(leaf:visible() == false,
                    "leaf " .. i .. " must remain masked after unrelated close_right, got " .. tostring(leaf:visible()))
            end

            local owner_after_unrelated = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_after_unrelated = owner_after_unrelated + 1 end
            end
            assert(owner_after_unrelated == 8,
                "NV owner must remain 8 after unrelated close_right (panel check failed), got " .. owner_after_unrelated)

            assert(objectives_panel:visible() == true, "objectives_panel must remain visible")
            assert(sentinel:visible() == true, "sentinel must remain visible")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1")

            kyohud.settings.enable_objectives = false
            RT:refresh_settings(managers.hud)

            local owned_gone = O._root_panel == nil or not O._root_panel._alive
            assert(owned_gone == true, "owned panel must be gone after disable")

            assert(objective_text:visible() == false,
                "title must remain false after disable (reconciled), got " .. tostring(objective_text:visible()))
            assert(amount_text:visible() == false,
                "amount must remain false after disable (reconciled), got " .. tostring(amount_text:visible()))

            for i, leaf in ipairs(leaves) do
                if leaf ~= objective_text and leaf ~= amount_text then
                    assert(leaf:visible() == true,
                        "leaf " .. i .. " must be restored true after disable, got " .. tostring(leaf:visible()))
                end
            end

            assert(sentinel:visible() == true, "sentinel must remain visible after disable")
            assert(sentinel:alpha() == 1, "sentinel alpha must remain 1 after disable")

            local owner_final = 0
            for _, e in ipairs(nv._entries) do
                if e.owner == O then owner_final = owner_final + 1 end
            end
            assert(owner_final == 0,
                "NV owner must be 0 after disable, got " .. owner_final)
        ''')


if __name__ == "__main__":
    unittest.main()
