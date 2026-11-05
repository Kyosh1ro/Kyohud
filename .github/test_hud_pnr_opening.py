"""LOT3b -- hud/alerts.lua: PNR opening coroutine with exact native function.

Tests the scheduled/suspended opening coroutine behavior when a valid covered
PNR replacement is certifiable BEFORE opening. Verifies that the first resume
of the opening coroutine maintains all 8 exact PNR native leaves suppressed
(visible=false) and the owned root remains visible and certified DURING
suspension and after the native done callback.

Native reference (hudobjectives.lua:92, 143-184):
  - local box_speed = 1000
  - HUDBGBox_animate_open_left(panel, wait_t, target_w, done_cb, config)
  - Uses wait(wait_t) fixture, callback(nil,_G,name) fixture
  - Sets panel visible=false, captures right(), sets w=0, restores right
  - If wait_t: wait(wait_t) (yields while t>0)
  - Sets panel visible=true
  - bg:stop(), bg:animate(callback(nil,_G,"HUDBGBox_animate_bg_attention"), {...})
  - Uses box_speed (1000) for TOTAL_T = target_w / speed
  - While loop yields dt, decrements t, sets w and right
  - Final set_w(target_w), set_right(right), calls done_cb()
"""
import unittest


# Exact native HUDBGBox_animate_open_left from hudobjectives.lua:143-184
# Attribution: PAYDAY 2 decompiled source (Payday-2-LuaJIT-Complete-master)
# NO logic modifications to this copied function.
NATIVE_HUDBGBOX_ANIMATE_OPEN_LEFT = r'''
local box_speed = 1000

function HUDBGBox_animate_open_left(panel, wait_t, target_w, done_cb, config)
	config = config or {}

	panel:set_visible(false)

	local right = panel:right()

	panel:set_w(0)
	panel:set_right(right)

	if wait_t then
		wait(wait_t)
	end

	panel:set_visible(true)

	local speed = box_speed
	local bg = panel:child("bg")

	bg:stop()
	bg:animate(callback(nil, _G, "HUDBGBox_animate_bg_attention"), {
		color = config.attention_color,
		attention_color_function = config.attention_color_function,
		forever = config.attention_forever
	})

	local TOTAL_T = target_w / speed
	local t = TOTAL_T

	while t > 0 do
		local dt = coroutine.yield()

		t = t - dt

		panel:set_w((1 - t / TOTAL_T) * target_w)
		panel:set_right(right)
	end

	panel:set_w(target_w)
	panel:set_right(right)
	done_cb()
end
'''


# Fixture for wait(seconds, fixed_dt) from coreevent.lua:270-277
# Attribution: PAYDAY 2 decompiled source
NATIVE_WAIT_FIXTURE = r'''
function wait(seconds, fixed_dt)
	local t = 0

	while t < seconds do
		local dt = coroutine.yield()

		t = t + (fixed_dt and 0.03333333333333333 or dt)
	end
end
'''


# Fixture for callback(o, base_callback_class, base_callback_func_name, base_callback_param)
# from coreevent.lua:6-36
# Attribution: PAYDAY 2 decompiled source
NATIVE_CALLBACK_FIXTURE = r'''
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
		error("Callback on non-existing function")
	elseif base_callback_func_name then
		error("Callback to function is on a nil class.")
	else
		error("Callback class and function was nil.")
	end
end
'''


# Exact native _animate_show_texts from hudassaultcorner.lua:1229-1252
# Attribution: PAYDAY 2 decompiled source
NATIVE_ANIMATE_SHOW_TEXTS = r'''
function HUDAssaultCorner:_animate_show_texts(anim_object, texts)
	for _, text in ipairs(texts) do
		text:set_visible(true)
	end

	local TOTAL_T = 0.5
	local t = TOTAL_T

	while t > 0 do
		local dt = coroutine.yield()

		t = t - dt

		local alpha = math.round(math.abs((math.sin(t * 360 * 3))))

		for _, text in ipairs(texts) do
			text:set_alpha(alpha)
		end
	end

	for _, text in ipairs(texts) do
		text:set_alpha(1)
	end
end
'''


def _extend_panels_with_animation_methods(lua):
    lua.execute(r'''
        local function add_methods_to_panel(p)
            if not p or type(p) ~= "table" then return end

            if not p.right then
                function p:right()
                    return self._x + self._w
                end
            end
            if not p.set_right then
                function p:set_right(v)
                    self._x = v - self._w
                end
            end
            if not p.set_w then
                function p:set_w(v)
                    self._w = v
                end
            end
            if not p.stop then
                function p:stop()
                end
            end
            if not p.animate then
                function p:animate(cb, config)
                end
            end

            if p._children then
                for _, child in pairs(p._children) do
                    add_methods_to_panel(child)
                end
            end
        end

        if _init_fp then
            add_methods_to_panel(_init_fp)
        end

        local orig_make = _make_panel_extended
        _make_panel_extended = function(name)
            local p = orig_make(name)

            function p:right()
                return self._x + self._w
            end
            function p:set_right(v)
                self._x = v - self._w
            end
            function p:set_w(v)
                self._w = v
            end
            function p:stop()
            end
            function p:animate(cb, config)
            end

            return p
        end
    ''')


def _lua_with_native_opening_before_alerts():
    from test_hud_assault_render import (
        ROOT,
        _read,
        _lua_with_assault_state,
    )
    from test_hud_alerts import NATIVE_PNR_SHOW_FIXTURE
    from test_hud_alerts_casing import NATIVE_CASING_FIXTURE

    ALERTS_PATH = ROOT / "lua" / "hud" / "alerts.lua"

    lua, ok = _lua_with_assault_state(
        difficulty_stars=3, hostages=4, converted_alive=2,
        assault_mode=True, hunt_mode=False, assault_number=3,
    )
    if not ok:
        return lua, ok

    lua.execute('kyohud.settings.enable_alerts = true')
    lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')

    lua.execute(NATIVE_WAIT_FIXTURE)
    lua.execute(NATIVE_CALLBACK_FIXTURE)

    lua.execute(r'''
        function HUDBGBox_animate_bg_attention() end
    ''')

    lua.execute(NATIVE_PNR_SHOW_FIXTURE)
    lua.execute(NATIVE_CASING_FIXTURE)

    _extend_panels_with_animation_methods(lua)

    lua.execute(NATIVE_HUDBGBOX_ANIMATE_OPEN_LEFT)
    lua.execute(NATIVE_ANIMATE_SHOW_TEXTS)

    alerts_src = _read(ALERTS_PATH)
    if alerts_src:
        lua.execute(alerts_src)
    return lua, True


LUA_ASSERT_HELPER = r'''
function _assert_pnr_leaves_all_false(leaves, msg_prefix)
    for i, leaf in ipairs(leaves) do
        assert(leaf:visible() == false,
            msg_prefix .. ": PNR leaf #" .. tostring(i)
            .. " must be visible=false, got " .. tostring(leaf:visible()))
    end
end

function _assert_alerts_state(AL, nv, expected_nv_count, msg_prefix)
    assert(type(AL._root_panel) == "table" and AL._root_panel:visible() == true,
        msg_prefix .. ": AL._root_panel must exist and be visible")
    assert(AL:_verify_render() == true,
        msg_prefix .. ": AL:_verify_render() must be true")

    local alerts_nv = 0
    for _, e in ipairs(nv._entries or {}) do
        if e.owner == "alerts" then alerts_nv = alerts_nv + 1 end
    end
    assert(alerts_nv == expected_nv_count,
        msg_prefix .. ": expected " .. tostring(expected_nv_count)
        .. " NV records for alerts, got " .. tostring(alerts_nv))
end
'''


class PnrOpeningInitialTests(unittest.TestCase):
    """PNR opening without prior RT:update - mount inactive then show/feed."""

    def test_initial_opening_without_prior_update(self):
        lua, ok = _lua_with_native_opening_before_alerts()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute(LUA_ASSERT_HELPER)

        lua.execute(r'''
            kyohud.settings.enable_alerts = true

            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local state = managers.groupai:state()

            RT:mount(managers.hud)

            state._point_of_no_return_timer = 65.9
            state._point_of_no_return_id = 101
            state._point_of_no_return_tweak_id = "noreturn"
            state._is_inside_point_of_no_return = false
            managers.hud:show_point_of_no_return_timer("noreturn")
            managers.hud:feed_point_of_no_return_timer(65.9, false)

            local corner = managers.hud._hud_assault_corner
            local noreturn_bg_box = corner._noreturn_bg_box
            assert(noreturn_bg_box, "noreturn_bg_box must exist on corner")

            local pnr_text = noreturn_bg_box:child("point_of_no_return_text")
            local pnr_timer = noreturn_bg_box:child("point_of_no_return_timer")

            assert(type(noreturn_bg_box.set_right) == "function", "noreturn_bg_box must have set_right")
            assert(type(noreturn_bg_box.right) == "function", "noreturn_bg_box must have right")
            assert(type(noreturn_bg_box.set_w) == "function", "noreturn_bg_box must have set_w")

            local leaves = {_na.icon_noreturnbox, _na.pnr_text, _na.pnr_timer, _na.pnr_bg, _na.pnr_lt, _na.pnr_lb, _na.pnr_rt, _na.pnr_rb}

            local text_co_done = false
            local text_co = nil

            local open_done = function()
                text_co = coroutine.create(function()
                    corner:_animate_show_texts(noreturn_bg_box, {pnr_text, pnr_timer})
                end)
                local ok_resume, err = coroutine.resume(text_co)
                assert(ok_resume, "text coroutine first resume failed: " .. tostring(err))
                text_co_done = true
            end

            local open_co = coroutine.create(function()
                HUDBGBox_animate_open_left(noreturn_bg_box, 0, 242, open_done, {})
            end)

            local ok1, status1 = coroutine.resume(open_co)
            assert(ok1, "open coroutine first resume failed: " .. tostring(status1))

            assert(coroutine.status(open_co) == "suspended",
                "After first resume: open coroutine must be suspended, got "
                .. tostring(coroutine.status(open_co)))

            _assert_alerts_state(AL, nv, 8, "Initial opening suspended")
            _assert_pnr_leaves_all_false(leaves, "Initial opening suspended")

            local max_iters = 100
            local iter = 0
            while coroutine.status(open_co) == "suspended" and iter < max_iters do
                local ok_r, status_r = coroutine.resume(open_co, 0.05)
                assert(ok_r, "open coroutine resume failed: " .. tostring(status_r))

                _assert_alerts_state(AL, nv, 8, "Initial opening step")
                _assert_pnr_leaves_all_false(leaves, "Initial opening step")

                iter = iter + 1
            end

            assert(coroutine.status(open_co) == "dead",
                "open coroutine must be dead after completion, got " .. tostring(coroutine.status(open_co)))
            assert(text_co_done, "open_done callback must have been called")

            _assert_alerts_state(AL, nv, 8, "Initial opening done")
            _assert_pnr_leaves_all_false(leaves, "Initial opening done")

            assert(noreturn_bg_box:w() == 242,
                "After native done: noreturn_bg_box:w() must be 242, got " .. tostring(noreturn_bg_box:w()))

            while text_co and coroutine.status(text_co) == "suspended" do
                coroutine.resume(text_co, 0.05)
            end

            kyohud.settings.enable_alerts = false
            RT:refresh_settings(managers.hud)
        ''')


class PnrOpeningCoroutineCoveredReplacementTests(unittest.TestCase):
    """Valid covered PNR must suppress 8 leaves during opening coroutine."""

    def test_covered_pnr_suppresses_leaves_during_opening_coroutine(self):
        lua, ok = _lua_with_native_opening_before_alerts()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute(LUA_ASSERT_HELPER)

        lua.execute(r'''
            kyohud.settings.enable_alerts = true

            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local state = managers.groupai:state()

            RT:mount(managers.hud)

            state._point_of_no_return_timer = 65.9
            state._point_of_no_return_id = 101
            state._point_of_no_return_tweak_id = "noreturn"
            state._is_inside_point_of_no_return = false
            managers.hud:show_point_of_no_return_timer("noreturn")
            managers.hud:feed_point_of_no_return_timer(65.9, false)

            RT:update(managers.hud, 1.0, 0.05)

            assert(type(AL._root_panel) == "table" and AL._root_panel:visible() == true,
                "Prerequisite: AL._root_panel must exist and be visible after RT:update")
            assert(AL:_verify_render() == true,
                "Prerequisite: AL:_verify_render() must be true BEFORE opening")

            local pre_opening_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then pre_opening_nv = pre_opening_nv + 1 end
            end
            assert(pre_opening_nv == 8,
                "Prerequisite: expected 8 NV records for alerts before opening, got "
                .. tostring(pre_opening_nv))

            local corner = managers.hud._hud_assault_corner
            local noreturn_bg_box = corner._noreturn_bg_box
            local pnr_panel = _na.pnr_panel
            local icon_noreturnbox = _na.icon_noreturnbox
            local pnr_text = noreturn_bg_box:child("point_of_no_return_text")
            local pnr_timer = noreturn_bg_box:child("point_of_no_return_timer")
            local pnr_bg = noreturn_bg_box:child("bg")
            local pnr_lt = noreturn_bg_box:child("left_top")
            local pnr_lb = noreturn_bg_box:child("left_bottom")
            local pnr_rt = noreturn_bg_box:child("right_top")
            local pnr_rb = noreturn_bg_box:child("right_bottom")

            local pnr_leaves = {
                icon_noreturnbox,
                pnr_text,
                pnr_timer,
                pnr_bg,
                pnr_lt,
                pnr_lb,
                pnr_rt,
                pnr_rb,
            }
            for i, leaf in ipairs(pnr_leaves) do
                assert(leaf:visible() == false,
                    "Prerequisite: PNR leaf #" .. tostring(i) .. " must be visible=false before opening")
            end

            local text_co = nil
            local text_co_done = false

            local open_done = function()
                text_co = coroutine.create(function()
                    corner:_animate_show_texts(noreturn_bg_box, {pnr_text, pnr_timer})
                end)
                local ok_resume, err = coroutine.resume(text_co)
                assert(ok_resume, "text coroutine first resume failed: " .. tostring(err))
                text_co_done = true
            end

            local open_co = coroutine.create(function()
                HUDBGBox_animate_open_left(noreturn_bg_box, 0, 242, open_done, {})
            end)

            local ok1, status1 = coroutine.resume(open_co)
            assert(ok1, "open coroutine first resume failed: " .. tostring(status1))
            assert(coroutine.status(open_co) == "suspended",
                "After first resume: open coroutine must be suspended, got "
                .. tostring(coroutine.status(open_co)))

            _assert_alerts_state(AL, nv, 8, "After first resume")
            _assert_pnr_leaves_all_false(pnr_leaves, "After first resume")

            local max_iters = 100
            local iter = 0
            while coroutine.status(open_co) == "suspended" and iter < max_iters do
                local ok_r, status_r = coroutine.resume(open_co, 0.05)
                assert(ok_r, "open coroutine resume failed: " .. tostring(status_r))

                _assert_alerts_state(AL, nv, 8, "After native resume iter " .. tostring(iter))
                _assert_pnr_leaves_all_false(pnr_leaves, "After native resume iter " .. tostring(iter))

                iter = iter + 1
            end

            assert(coroutine.status(open_co) == "dead",
                "After completion: open coroutine must be dead, got "
                .. tostring(coroutine.status(open_co)))
            assert(text_co_done, "open_done callback must have been called")

            _assert_alerts_state(AL, nv, 8, "After native done")
            _assert_pnr_leaves_all_false(pnr_leaves, "After native done")

            assert(pnr_panel:visible() == true, "pnr_panel parent must remain visible")
            assert(noreturn_bg_box:visible() == true,
                "noreturn_bg_box parent must remain visible")
            assert(_na.pnr_third_party:visible() == true,
                "pnr_third_party must remain untouched")

            while text_co and coroutine.status(text_co) == "suspended" do
                coroutine.resume(text_co, 0.05)
            end

            kyohud.settings.enable_alerts = false
            RT:refresh_settings(managers.hud)
        ''')


if __name__ == "__main__":
    unittest.main()
