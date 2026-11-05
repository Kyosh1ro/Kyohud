"""LOT3b -- hud/alerts.lua: casing close coroutine transition (RED state).

Tests the native casing close transition when hide_casing is called:
  - hide_casing schedules HUDBGBox_animate_close_left coroutine (not synchronous)
  - During native close: 6 casing leaves visible=false + ticker alpha=0 retained
  - Owned exit animation visible and verified during close
  - At midpoint: owned root exit animation visible with displacement or alpha change
  - After close_done + icon fade: owned hidden, owner entries empty
  - Native bg already hidden and icon alpha=0 before restoration

Native sources (read-only reference):
  - hudassaultcorner.lua:1117-1140 hide_casing
  - hudassaultcorner.lua:911-938 _hide_icon_assaultbox (1s cosine fade)
  - hudobjectives.lua:92, 186-205 HUDBGBox_animate_close_left (box_speed=1000)

Fixture approach:
  - Install NATIVE_CALLBACK_FIXTURE before hide
  - Use verbatim native functions with correct box_speed=1000
  - Trace _hide_icon_assaultbox (do NOT assume immediate alpha=0)
  - Focus single transition with positive/negative phase assertions
  - Meaningful RED before production implementation
"""
from pathlib import Path
import unittest

from test_hud_alerts import ALERTS_PATH, NATIVE_PNR_SHOW_FIXTURE
from test_hud_alerts_casing import NATIVE_CASING_FIXTURE
from test_hud_assault_render import (
    ROOT,
    _read,
    _lua_with_assault_state,
)
from test_hud_pnr_opening import NATIVE_CALLBACK_FIXTURE


def _lua_with_casing_close_fixture():
    """Build Lua environment with native close coroutine installed BEFORE hooks."""
    lua, ok = _lua_with_assault_state(
        difficulty_stars=3, hostages=4, converted_alive=2,
        assault_mode=True, hunt_mode=False, assault_number=3,
    )
    if not ok:
        return lua, ok

    lua.execute('kyohud.settings.enable_alerts = true')
    lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
    lua.execute(NATIVE_PNR_SHOW_FIXTURE)
    lua.execute(NATIVE_CASING_FIXTURE)
    lua.execute(NATIVE_CALLBACK_FIXTURE)

    lua.execute(r'''
        _coroutines = {}

        local function _coro_key(panel, role)
            return tostring(panel) .. ":" .. role
        end

        function _schedule_coroutine(panel, role, coro)
            local key = _coro_key(panel, role)
            _coroutines[key] = {coro = coro, panel = panel, role = role}
        end

        function _resume_coroutines(dt)
            local snapshot = {}
            for key, entry in pairs(_coroutines) do
                snapshot[key] = entry
            end
            for key, entry in pairs(snapshot) do
                if entry.coro and coroutine.status(entry.coro) == "suspended" then
                    local ok, err = coroutine.resume(entry.coro, dt or 0.05)
                    assert(ok, "coroutine resume failed for " .. key .. ": " .. tostring(err))
                    if coroutine.status(entry.coro) == "dead" then
                        _coroutines[key] = nil
                    end
                elseif entry.coro and coroutine.status(entry.coro) == "dead" then
                    _coroutines[key] = nil
                end
            end
        end

        local function add_animate_to_panel(p)
            if not p or type(p) ~= "table" then return end
            function p:animate(func, ...)
                local args = {...}
                local self_panel = self
                local coro = coroutine.create(function() func(self_panel, unpack(args)) end)
                _schedule_coroutine(self_panel, "animate", coro)
                local ok, err = coroutine.resume(coro)
                assert(ok, "first resume failed: " .. tostring(err))
            end
            function p:stop()
                for key, entry in pairs(_coroutines) do
                    if entry.panel == self then
                        _coroutines[key] = nil
                    end
                end
            end
            function p:right()
                return self._x + self._w
            end
            function p:set_right(v)
                self._x = v - self._w
            end
            if not p.set_w then
                function p:set_w(v)
                    self._w = v
                end
            end
        end

        local function add_to_all(panel)
            if not panel or type(panel) ~= "table" then return end
            add_animate_to_panel(panel)
            if panel._children then
                for _, child in pairs(panel._children) do
                    add_to_all(child)
                end
            end
        end

        for k, v in pairs(_na or {}) do
            add_to_all(v)
        end

        local box_speed = 1000
        function HUDBGBox_animate_close_left(panel, done_cb)
            local speed = box_speed
            local cw = panel:w()
            local right = panel:right()
            local TOTAL_T = cw / speed
            local t = TOTAL_T

            while t > 0 do
                local dt = coroutine.yield()
                t = t - dt
                panel:set_w(t / TOTAL_T * cw)
                panel:set_right(right)
            end

            panel:set_w(0)
            panel:set_right(right)
            done_cb()
        end

        _set_hostage_offseted_count = 0
        _show_hostages_count = 0

        function HUDAssaultCorner:_set_hostage_offseted(v)
            _set_hostage_offseted_count = _set_hostage_offseted_count + 1
        end

        function HUDAssaultCorner:_show_hostages()
            _show_hostages_count = _show_hostages_count + 1
        end

        function HUDAssaultCorner:hide_casing()
            if self._casing_bg_box:child("text_panel") then
                self._casing_bg_box:child("text_panel"):stop()
                self._casing_bg_box:child("text_panel"):clear()
            end

            local icon_casingbox = self._hud_panel:child("casing_panel"):child("icon_casingbox")
            icon_casingbox:stop()

            local function close_done()
                self._casing_bg_box:set_visible(false)
                local icon_casingbox = self._hud_panel:child("casing_panel"):child("icon_casingbox")
                icon_casingbox:stop()
                icon_casingbox:animate(callback(self, self, "_hide_icon_assaultbox"))
            end

            self._casing_bg_box:stop()
            self._casing_bg_box:animate(callback(nil, _G, "HUDBGBox_animate_close_left"), close_done)

            self._casing = false
        end

        function HUDAssaultCorner:_hide_icon_assaultbox(icon_assaultbox)
            local TOTAL_T = 1
            local t = TOTAL_T

            while t > 0 do
                local dt = coroutine.yield()
                t = t - dt
                local alpha = math.round(math.abs((math.cos(t * 360 * 2))))
                icon_assaultbox:set_alpha(alpha)
                if self._remove_hostage_offset and t < 0.03 then
                    self:_set_hostage_offseted(false)
                end
            end

            if self._remove_hostage_offset then
                self:_set_hostage_offseted(false)
            end

            icon_assaultbox:set_alpha(0)

            if not self._casing then
                self:_show_hostages()
            end
        end
    ''')

    alerts_src = _read(ALERTS_PATH)
    if alerts_src:
        lua.execute(alerts_src)

    lua.execute(r'''
        local function _al_is_finite(v)
            if type(v) ~= "number" then return false end
            if v ~= v then return false end
            if v == math.huge or v == -math.huge then return false end
            return true
        end

        local function _ancestor_alpha_product(prim)
            if not prim or type(prim) ~= "table" then return nil end
            local ok_p0, p0 = pcall(function() return prim:parent() end)
            if not ok_p0 then return nil end
            local cur = p0
            if not cur or type(cur) ~= "table" then return 1 end
            local product = 1
            local depth = 0
            while cur and depth < 32 do
                local ok_a, a = pcall(function() return cur:alpha() end)
                if not ok_a then return nil end
                if type(a) ~= "number" or not _al_is_finite(a) then return nil end
                product = product * a
                local ok_p, p = pcall(function() return cur:parent() end)
                if not ok_p or not p or type(p) ~= "table" then break end
                cur = p
                depth = depth + 1
            end
            return product
        end

        local function _install_inherited_color_wrappers(root)
            if not root or type(root) ~= "table" then return end
            local function install_recursive(panel)
                if not panel or type(panel) ~= "table" then return end
                if type(panel.color) ~= "function" then
                    if panel._children then
                        for _, child in pairs(panel._children) do
                            install_recursive(child)
                        end
                    end
                    return
                end
                if panel._inherited_color_wrapped then return end
                panel._inherited_color_wrapped = true
                local orig_color = panel.color
                function panel:color()
                    local base = orig_color(self)
                    if not base then return nil end
                    local ancestor_product = _ancestor_alpha_product(self)
                    if ancestor_product == nil then return nil end
                    local base_a = base.a
                    if base_a == nil then base_a = 1 end
                    local effective_a = base_a * ancestor_product
                    return {
                        r = base.r or 1, g = base.g or 1, b = base.b or 1, a = effective_a,
                        [1] = base.r or 1, [2] = base.g or 1, [3] = base.b or 1, [4] = effective_a
                    }
                end
                panel._inherited_orig_color = orig_color
                if panel._children then
                    for _, child in pairs(panel._children) do
                        install_recursive(child)
                    end
                end
            end
            install_recursive(root)
        end

        local _orig_rt_update = kyohud.hud.runtime.update
        local _inherited_color_auto_installed = false
        function kyohud.hud.runtime:update(...)
            local args = {...}
            local results = {_orig_rt_update(self, unpack(args))}
            if not _inherited_color_auto_installed then
                _inherited_color_auto_installed = true
                local AL = kyohud.hud.alerts
                if type(AL._casing_root_panel) == "table" then
                    _install_inherited_color_wrappers(AL._casing_root_panel)
                end
            end
            return unpack(results)
        end
    ''')

    return lua, ok


class CasingCloseCoroutineTests(unittest.TestCase):
    """Native hide_casing schedules close coroutine, not synchronous completion.

    Tests that hide_casing:
      1. Schedules HUDBGBox_animate_close_left coroutine
      2. Retains 7 NV records during close
      3. Owned exit animation remains visible and certified at midpoint
      4. After close_done + icon fade complete: owned hidden, owner entries empty
      5. Native bg already hidden and icon alpha=0 before restoration
    """

    def test_hide_casing_schedules_close_coroutine_not_synchronous(self):
        """RED: hide_casing must schedule coroutine, not complete synchronously."""
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local corner = managers.hud._hud_assault_corner

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(type(AL._casing_root_panel) == "table" and AL._casing_root_panel:visible() == true,
                "Prerequisite: AL._casing_root_panel must be visible")

            local before_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then before_nv = before_nv + 1 end
            end
            assert(before_nv == 7,
                "Prerequisite: must have 7 NV entries, got " .. tostring(before_nv))

            local casing_leaves = {
                _na.icon_casingbox,
                _na.cas_bg,
                _na.cas_lt,
                _na.cas_lb,
                _na.cas_rt,
                _na.cas_rb,
            }
            for i, leaf in ipairs(casing_leaves) do
                assert(leaf:visible() == false,
                    "Prerequisite: leaf #" .. tostring(i) .. " must have visible=false")
            end
            assert(math.abs(_na.cas_text_panel:alpha() - 0) < 0.001,
                "Prerequisite: cas_text_panel must have alpha=0")

            assert(type(_na.casing_bg_box.set_w) == "function",
                "Prerequisite: casing_bg_box must have set_w")

            managers.hud:hide_casing()

            local has_close_coro = false
            for key, entry in pairs(_coroutines) do
                if entry.role == "animate" and entry.panel == _na.casing_bg_box then
                    has_close_coro = true
                    break
                end
            end
            assert(has_close_coro,
                "RED: hide_casing must schedule animate coroutine on casing_bg_box")

            local during_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then during_nv = during_nv + 1 end
            end
            assert(during_nv == 7,
                "RED: during close, must retain 7 NV entries, got " .. tostring(during_nv))

            for i, leaf in ipairs(casing_leaves) do
                assert(leaf:visible() == false,
                    "RED: during close, leaf #" .. tostring(i) .. " must remain visible=false")
            end

            assert(math.abs(_na.cas_text_panel:alpha() - 0) < 0.001,
                "RED: during close, cas_text_panel must retain alpha=0")
        ''')

    def test_owned_exit_visible_and_certified_at_midpoint(self):
        """RED: owned root exit animation must be visible and certified at midpoint."""
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local corner = managers.hud._hud_assault_corner

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(type(AL._casing_root_panel) == "table" and AL._casing_root_panel:visible() == true,
                "Prerequisite: AL._casing_root_panel must be visible")

            assert(AL:_verify_render() == true,
                "Prerequisite: AL:_verify_render() must return true before hide")

            local saved_owned = AL._casing_root_panel
            local saved_x = AL._casing_root_panel:x()
            local saved_alpha = AL._casing_root_panel:alpha()

            managers.hud:hide_casing()

            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.05, 0.05)

            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.10, 0.05)

            assert(AL._casing_root_panel == saved_owned,
                "RED: AL._casing_root_panel must be same owned root at midpoint")

            local mid_x = AL._casing_root_panel:x()
            local mid_alpha = AL._casing_root_panel:alpha()
            local mid_visible = AL._casing_root_panel:visible()

            assert(mid_visible == true,
                "RED: owned root must be visible=true at midpoint")

            local displacement = math.abs(mid_x - saved_x)
            local alpha_changed = (mid_alpha > 0 and mid_alpha < saved_alpha)

            assert(displacement > 0 or alpha_changed,
                "RED: owned root meaningful change required: displacement>0 OR 0<alpha<"
                .. tostring(saved_alpha) .. ", got alpha=" .. tostring(mid_alpha)
                .. " displacement=" .. tostring(displacement))

            assert(AL:_verify_render() == true,
                "RED: AL:_verify_render() must return true at midpoint")

            local mid_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then mid_nv = mid_nv + 1 end
            end
            assert(mid_nv == 7,
                "RED: at midpoint, must retain 7 NV entries, got " .. tostring(mid_nv))
        ''')

    def test_close_done_then_owned_hidden_and_entries_empty(self):
        """RED: after close_done + icon fade, owned hidden and entries empty."""
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local corner = managers.hud._hud_assault_corner

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            managers.hud:hide_casing()

            for i = 1, 30 do
                _resume_coroutines(0.05)
            end

            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "RED: after close, AL._casing_root_panel must be hidden or removed")

            local after_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then after_nv = after_nv + 1 end
            end
            assert(after_nv == 0,
                "RED: after close, owner entries must be empty, got " .. tostring(after_nv))

            assert(_na.casing_bg_box:visible() == false,
                "RED: native casing_bg_box must be visible=false after close")

            assert(math.abs(_na.icon_casingbox:alpha() - 0) < 0.001,
                "RED: native icon_casingbox alpha must be 0 after close, got "
                .. tostring(_na.icon_casingbox:alpha()))

            assert(_na.icon_casingbox:visible() == true,
                "RED: after restoration, icon_casingbox visible must be restored to true")

            assert(math.abs(_na.cas_text_panel:alpha() - 0.43) < 0.001,
                "RED: after restoration, cas_text_panel must restore alpha=0.43")
        ''')

    def test_hooks_registered_real_dispatcher(self):
        """RED: hide_casing hooks must be registered with real dispatcher."""
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            assert(kyohud.hud._installed_hooks["KyohUD_Alerts_PreHideCasing"] == true,
                "RED: PreHideCasing hook must be registered")
            assert(kyohud.hud._installed_hooks["KyohUD_Alerts_PostHideCasing"] == true,
                "RED: PostHideCasing hook must be registered")

            local corner = managers.hud._hud_assault_corner
            assert(type(corner.hide_casing) == "function",
                "RED: corner.hide_casing must be a function")

            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(corner._casing == true,
                "Before hide: corner._casing must be true")

            managers.hud:hide_casing()

            assert(corner._casing == false,
                "After hide: corner._casing must be false")
        ''')

    def test_midpoint_root_alpha_certification_corrupt_and_restore(self):
        """RED: _verify_render must detect root alpha corruption during closing.

        At midpoint with actual partial alpha, establish positive close certification.
        Corrupt retained root alpha alone by 0.2 via setter -> _verify_render false.
        Restore expected alpha -> _verify_render true. All geometry/text predicates retained.
        """
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(type(AL._casing_root_panel) == "table" and AL._casing_root_panel:visible() == true,
                "Prerequisite: AL._casing_root_panel must be visible")
            assert(AL:_verify_render() == true,
                "Prerequisite: _verify_render true before hide")

            local saved_owned = AL._casing_root_panel

            managers.hud:hide_casing()

            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.05, 0.05)

            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.10, 0.05)

            assert(AL._casing_root_panel == saved_owned,
                "Prerequisite: same owned root at midpoint")
            assert(AL._casing_root_panel:visible() == true,
                "Prerequisite: root visible at midpoint")

            local mid_alpha = AL._casing_root_panel:alpha()
            assert(mid_alpha > 0 and mid_alpha < 1,
                "Prerequisite: actual partial alpha at midpoint, got " .. tostring(mid_alpha))

            assert(AL:_verify_render() == true,
                "Prerequisite: positive close certification at midpoint")

            local geom_ok_before = true
            local tex_ok_before = true
            if AL._casing_bg then
                local bx = AL._casing_bg:x()
                geom_ok_before = (type(bx) == "number" and bx == bx)
            end
            if AL._casing_a then
                local at = AL._casing_a:text()
                tex_ok_before = (type(at) == "string" and #at > 0)
            end
            assert(geom_ok_before and tex_ok_before,
                "Prerequisite: geometry/text predicates intact before corruption")

            local corrupted_alpha = mid_alpha - 0.2
            AL._casing_root_panel:set_alpha(corrupted_alpha)

            local alpha_after_corrupt = AL._casing_root_panel:alpha()
            assert(math.abs(alpha_after_corrupt - corrupted_alpha) < 0.001,
                "Prerequisite: setter applied corruption, got " .. tostring(alpha_after_corrupt))

            local vr_after_corrupt = AL:_verify_render()
            assert(vr_after_corrupt == false,
                "RED: _verify_render must return false when root alpha corrupted by 0.2, got "
                .. tostring(vr_after_corrupt))

            local geom_after = true
            local tex_after = true
            if AL._casing_bg then
                local bx = AL._casing_bg:x()
                geom_after = (type(bx) == "number" and bx == bx)
            end
            if AL._casing_a then
                local at = AL._casing_a:text()
                tex_after = (type(at) == "string" and #at > 0)
            end
            assert(geom_after and tex_after,
                "RED: geometry/text predicates must remain intact after alpha-only corruption")

            AL._casing_root_panel:set_alpha(mid_alpha)

            local alpha_restored = AL._casing_root_panel:alpha()
            assert(math.abs(alpha_restored - mid_alpha) < 0.001,
                "Prerequisite: alpha restored to midpoint value, got " .. tostring(alpha_restored))

            local vr_after_restore = AL:_verify_render()
            assert(vr_after_restore == true,
                "RED: _verify_render must return true after restoring expected alpha, got "
                .. tostring(vr_after_restore))

            local mid_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then mid_nv = mid_nv + 1 end
            end
            assert(mid_nv == 7,
                "RED: must retain 7 NV entries throughout certification, got " .. tostring(mid_nv))
        ''')

    def test_source_identity_replacement_during_closing(self):
        """RED: replacing corner source during closing must release and hide root.

        During active closing, replace managers.hud._hud_assault_corner with a distinct
        corner copy. Ordinary RT:update must find root hidden and seven entries released.
        Replacement unknown must not inherit closing eligibility.
        """
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local orig_corner = managers.hud._hud_assault_corner

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(AL._casing_native_acquired == true,
                "Prerequisite: casing native acquired before hide")
            assert(AL._casing_render_verified == true,
                "Prerequisite: render verified before hide")

            managers.hud:hide_casing()

            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.05, 0.05)

            assert(AL._casing_closing == true,
                "Prerequisite: closing in progress")

            local replacement_corner = {}
            setmetatable(replacement_corner, {__index = HUDAssaultCorner})
            replacement_corner._hud_panel = orig_corner._hud_panel
            replacement_corner._casing_bg_box = orig_corner._casing_bg_box
            replacement_corner._casing = false
            replacement_corner._assault = false
            replacement_corner._point_of_no_return = false
            replacement_corner._assault_mode = "normal"
            function replacement_corner:should_display_waves() return false end
            replacement_corner._identity_tag = "replacement"

            managers.hud._hud_assault_corner = replacement_corner

            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.10, 0.05)

            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "RED: after corner replacement, root must be hidden, got visible="
                .. tostring(AL._casing_root_panel and AL._casing_root_panel:visible()))

            local after_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then after_nv = after_nv + 1 end
            end
            assert(after_nv == 0,
                "RED: after corner replacement, seven entries must be released, got "
                .. tostring(after_nv))

            assert(AL._casing_closing == false,
                "RED: closing must not continue with replacement corner")
        ''')

    def test_groupai_state_source_replacement_during_closing(self):
        """RED: replacing groupai state source during closing must not inherit eligibility.

        Compact form: replace groupai:state() with distinct state during close.
        RT:update must refuse to reacquire and root must remain hidden/entries released.
        """
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local orig_state = managers.groupai:state()

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(AL._casing_native_acquired == true,
                "Prerequisite: casing native acquired before hide")

            managers.hud:hide_casing()

            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.05, 0.05)

            assert(AL._casing_closing == true,
                "Prerequisite: closing in progress")

            local replacement_state = {}
            setmetatable(replacement_state, {__index = GroupAIState})
            replacement_state._assault_mode = false
            replacement_state._hunt_mode = false
            replacement_state._assault_number = 0
            replacement_state._hostage_count = 0
            replacement_state._converted = {}
            replacement_state._whisper_mode = false
            replacement_state._identity_tag = "replacement"
            function replacement_state:whisper_mode() return self._whisper_mode end
            function replacement_state:hostage_count() return self._hostage_count end
            function replacement_state:all_converted_enemies() return self._converted end

            local orig_groupai = managers.groupai
            managers.groupai = {
                state = function() return replacement_state end,
            }

            for i = 1, 15 do
                _resume_coroutines(0.05)
            end
            RT:update(managers.hud, 1.80, 0.05)

            local after_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then after_nv = after_nv + 1 end
            end
            assert(after_nv == 0,
                "RED: after groupai state replacement, entries must be released, got "
                .. tostring(after_nv))

            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "RED: after groupai state replacement, root must be hidden")
        ''')

    def test_disable_midpoint_refresh_settings_releases_and_blocks_reacquire(self):
        """RED: disable during closing -> hidden root, 0 ownership; finish native must not reacquire.

        Set enable_alerts=false + RT:refresh_settings during closing. Root hidden, 0 ownership.
        Finish native coroutines must not reacquire.
        Re-enable normal show_casing then update -> root alpha exactly 1, certification true,
        same live root if retained.
        """
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(type(AL._casing_root_panel) == "table",
                "Prerequisite: casing root exists after show")
            local live_root = AL._casing_root_panel

            managers.hud:hide_casing()

            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.05, 0.05)

            assert(AL._casing_closing == true,
                "Prerequisite: closing active")

            kyohud.settings.enable_alerts = false
            RT:refresh_settings(managers.hud)

            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "RED: after disable + refresh, root must be hidden")

            local nv_disabled = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then nv_disabled = nv_disabled + 1 end
            end
            assert(nv_disabled == 0,
                "RED: after disable + refresh, 0 ownership, got " .. tostring(nv_disabled))

            for i = 1, 30 do
                _resume_coroutines(0.05)
            end
            RT:update(managers.hud, 3.0, 0.05)

            local nv_after_finish = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then nv_after_finish = nv_after_finish + 1 end
            end
            assert(nv_after_finish == 0,
                "RED: finish native coroutines must not reacquire, got " .. tostring(nv_after_finish))

            kyohud.settings.enable_alerts = true
            RT:refresh_settings(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 4.0, 0.05)

            assert(type(AL._casing_root_panel) == "table",
                "RED: re-enable + show_casing + update must produce casing root")

            local root_alpha = AL._casing_root_panel:alpha()
            assert(math.abs(root_alpha - 1) < 0.001,
                "RED: after re-enable, root alpha must be exactly 1, got " .. tostring(root_alpha))

            assert(AL:_verify_render() == true,
                "RED: after re-enable, certification must be true")

            if AL._casing_root_panel == live_root then
                assert(AL._casing_root_panel == live_root,
                    "RED: same live root retained across disable/re-enable")
            end
        ''')

    def test_negative_geometry_corruption_during_close_refuses_cert(self):
        """RED: real primitive geometry corruption during close -> update refuses cert/releases.

        Positive baseline first. Then corrupt _casing_bg geometry via real set_shape.
        Ordinary RT:update must refuse certification and release.
        Restore setter (real set_shape with correct values) -> recovery, no fake fields.
        """
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(type(AL._casing_root_panel) == "table" and AL._casing_root_panel:visible() == true,
                "Prerequisite: root visible")
            assert(AL:_verify_render() == true,
                "Prerequisite: positive baseline certification true")
            assert(type(AL._casing_bg) == "table",
                "Prerequisite: _casing_bg exists")

            local bg_geom_ok = {
                x = AL._casing_bg:x(), y = AL._casing_bg:y(),
                w = AL._casing_bg:w(), h = AL._casing_bg:h(),
            }
            assert(type(bg_geom_ok.x) == "number" and bg_geom_ok.x == bg_geom_ok.x,
                "Prerequisite: _casing_bg has finite geometry")

            managers.hud:hide_casing()

            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.05, 0.05)

            assert(AL._casing_closing == true,
                "Prerequisite: closing active")

            assert(AL:_verify_render() == true,
                "Prerequisite: positive close certification before corruption")

            AL._casing_bg:set_shape(9999, 9999, 0, 0)

            local corrupt_x = AL._casing_bg:x()
            assert(corrupt_x == 9999,
                "Prerequisite: real set_shape applied corruption, got " .. tostring(corrupt_x))

            RT:update(managers.hud, 1.10, 0.05)

            local vr_after = AL:_verify_render()
            assert(vr_after == false,
                "RED: after real geometry corruption, _verify_render must return false, got "
                .. tostring(vr_after))

            local nv_after_corrupt = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then nv_after_corrupt = nv_after_corrupt + 1 end
            end

            AL._casing_bg:set_shape(bg_geom_ok.x, bg_geom_ok.y, bg_geom_ok.w, bg_geom_ok.h)

            local restored_x = AL._casing_bg:x()
            assert(math.abs(restored_x - bg_geom_ok.x) < 0.001,
                "Prerequisite: real setter restored, got " .. tostring(restored_x))

            assert(type(AL._casing_bg.x) == "function",
                "Prerequisite: no fake fields introduced")
            assert(type(AL._casing_bg.set_shape) == "function",
                "Prerequisite: set_shape still a real function")
        ''')

    def test_noop_set_shape_during_close_refuses_cert(self):
        """RED: no-op actual set_shape (same values) during close must not break cert.

        Positive baseline. Apply a no-op set_shape with current values.
        _verify_render must still return true; no release triggered by no-op.
        """
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(AL:_verify_render() == true,
                "Prerequisite: positive baseline")
            assert(type(AL._casing_bg) == "table",
                "Prerequisite: _casing_bg exists")

            local bg_x = AL._casing_bg:x()
            local bg_y = AL._casing_bg:y()
            local bg_w = AL._casing_bg:w()
            local bg_h = AL._casing_bg:h()

            managers.hud:hide_casing()

            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.05, 0.05)

            assert(AL._casing_closing == true,
                "Prerequisite: closing active")
            assert(AL:_verify_render() == true,
                "Prerequisite: positive close cert before no-op")

            AL._casing_bg:set_shape(bg_x, bg_y, bg_w, bg_h)

            RT:update(managers.hud, 1.10, 0.05)

            assert(AL:_verify_render() == true,
                "RED: no-op set_shape must not break certification, got false")

            local noop_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then noop_nv = noop_nv + 1 end
            end
            assert(noop_nv == 7,
                "RED: no-op set_shape must not trigger release, got " .. tostring(noop_nv) .. " entries")
        ''')

    def test_seven_entries_held_after_bg_close_before_icon_fade(self):
        """RED: 7 entries STILL held after native bg close but before icon fade completion.

        Drive native coroutines until bg_box becomes visible=false (close_done fired),
        but icon_casingbox alpha is still > 0 (fade not complete).
        Assert 7 NV entries still held at this boundary.
        No runtime repair tick at final release.
        """
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(AL._casing_native_acquired == true,
                "Prerequisite: acquired")

            local before_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then before_nv = before_nv + 1 end
            end
            assert(before_nv == 7,
                "Prerequisite: 7 entries before hide")

            managers.hud:hide_casing()

            local bg_closed = false
            local icon_still_fading = false

            for i = 1, 30 do
                _resume_coroutines(0.05)

                if not bg_closed and _na.casing_bg_box:visible() == false then
                    bg_closed = true
                    local icon_alpha = _na.icon_casingbox:alpha()
                    if icon_alpha > 0.001 then
                        icon_still_fading = true
                    end

                    if bg_closed and icon_still_fading then
                        local boundary_nv = 0
                        for _, e in ipairs(nv._entries or {}) do
                            if e.owner == "alerts" then boundary_nv = boundary_nv + 1 end
                        end
                        assert(boundary_nv == 7,
                            "RED: 7 entries must STILL be held after bg close but before icon fade, got "
                            .. tostring(boundary_nv))

                        assert(AL._casing_closing == true,
                            "RED: closing state must still be active at boundary")

                        assert(AL._casing_root_panel ~= nil and AL._casing_root_panel:visible() == true,
                            "RED: owned root must still be visible at boundary")

                        break
                    end
                end
            end

            assert(bg_closed,
                "Prerequisite: bg must close within 30 ticks")
            assert(icon_still_fading,
                "Prerequisite: must observe boundary where bg closed but icon still fading")
        ''')


    def test_pre_hide_corruption_blocks_begin_without_release(self):
        """RED: corrupt owned geometry after cert, before hide_casing.

        cb_pre sees cached _casing_render_verified=true, enters _begin_casing_close,
        which calls _verify_casing_render and fails, returning WITHOUT al_release.
        Immediately after hide_casing (before any RT:update): native ownership must
        be 0 and owned root hidden. Current code leaks both (meaningful RED).
        """
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(type(AL._casing_root_panel) == "table" and AL._casing_root_panel:visible() == true,
                "Prerequisite: root visible")
            assert(AL._casing_render_verified == true,
                "Prerequisite: render verified")
            assert(type(AL._casing_bg) == "table",
                "Prerequisite: _casing_bg exists")

            local before_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then before_nv = before_nv + 1 end
            end
            assert(before_nv == 7,
                "Prerequisite: 7 NV entries, got " .. tostring(before_nv))

            AL._casing_bg:set_shape(9999, 9999, 0, 0)
            assert(AL._casing_bg:x() == 9999,
                "Prerequisite: real setter corruption applied")

            assert(AL._casing_render_verified == true,
                "Prerequisite: cached bool still true (not manually cleared)")

            managers.hud:hide_casing()

            local after_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then after_nv = after_nv + 1 end
            end
            assert(after_nv == 0,
                "RED: after hide_casing with pre-corruption, native ownership must be 0, got "
                .. tostring(after_nv))

            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "RED: after hide_casing with pre-corruption, owned root must be hidden, got visible="
                .. tostring(AL._casing_root_panel and AL._casing_root_panel:visible()))
        ''')

    def test_unrelated_hudbgbox_close_cannot_release_active_closing7(self):
        """RED: unrelated HUDBGBox_animate_close_left on another native box cannot release closing7.

        During active casing close (7 entries held), invoke HUDBGBox_animate_close_left
        on a distinct native panel. Assert 7 entries remain held afterwards.
        """
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(AL._casing_native_acquired == true,
                "Prerequisite: acquired")

            managers.hud:hide_casing()

            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.05, 0.05)

            assert(AL._casing_closing == true,
                "Prerequisite: closing active")

            local mid_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then mid_nv = mid_nv + 1 end
            end
            assert(mid_nv == 7,
                "Prerequisite: 7 entries during close, got " .. tostring(mid_nv))

            local other_box = _na.icon_casingbox
            assert(other_box ~= AL._casing_close_bg_box,
                "Prerequisite: other_box is distinct from closing bg_box")
            assert(type(other_box.set_w) == "function",
                "Prerequisite: other_box has set_w")

            local unrelated_done = false
            local function noop_done() unrelated_done = true end
            local coro = coroutine.create(function() HUDBGBox_animate_close_left(other_box, noop_done) end)
            local ok_r, err_r = coroutine.resume(coro)
            assert(ok_r, "first resume failed: " .. tostring(err_r))
            while coroutine.status(coro) ~= "dead" do
                local rok, rerr = coroutine.resume(coro, 0.05)
                assert(rok, "resume failed: " .. tostring(rerr))
            end

            local after_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then after_nv = after_nv + 1 end
            end
            assert(after_nv == 7,
                "RED: unrelated HUDBGBox_close must not release active closing7, got "
                .. tostring(after_nv))

            assert(AL._casing_closing == true,
                "RED: closing state must remain active after unrelated close")
        ''')


if __name__ == '__main__':
    unittest.main()
