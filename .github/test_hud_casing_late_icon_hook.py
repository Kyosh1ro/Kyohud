"""LOT3b -- Late BAI replacement of _hide_icon_assaultbox after KyoHUD hooks.

Tests that when Better Assault Indicator replaces HUDAssaultCorner._hide_icon_assaultbox
AFTER KyoHUD installs its PostHook on hide_casing, the casing close transition still
completes correctly with proper ownership release and BAI's hostage branches preserved.

BAI source (read-only reference):
  - Better Assault Indicator/lua/hudassaultcorner.lua:504-527

Fixture approach:
  - Reuse _lua_with_casing_close_fixture (faithful scheduler, inherited alpha)
  - Embed literal BAI function from read-only source
  - Install BAI AFTER mount/show/update (late replacement)
  - Three bounded tests, no skips/TODO/new production methods
"""
import unittest

from test_hud_assault_render import ROOT, _read
from test_hud_alerts import ALERTS_PATH
from test_hud_casing_close import _lua_with_casing_close_fixture


BAI_HIDE_ICON_FIXTURE = r'''
    local math_round = math.round
    local math_abs = math.abs
    local math_cos = math.cos

    BAI = BAI or {}
    function BAI:IsHostagePanelVisible()
        return BAI._hostage_panel_visible or false
    end

    _set_hostages_offseted_count = _set_hostages_offseted_count or 0
    function HUDAssaultCorner:_set_hostages_offseted(v)
        _set_hostages_offseted_count = _set_hostages_offseted_count + 1
    end

    function HUDAssaultCorner:_hide_icon_assaultbox(icon_assaultbox)
        local TOTAL_T = 1
        local t = TOTAL_T
        while t > 0 do
            local dt = coroutine.yield()
            t = t - dt
            local alpha = math_round(math_abs(math_cos(t * 360 * 2)))
            icon_assaultbox:set_alpha(alpha)
            if self._remove_hostage_offset and t < 0.03 then
                self:_set_hostages_offseted(false)
            end
        end
        if self._remove_hostage_offset then
            self:_set_hostages_offseted(false)
        end
        icon_assaultbox:set_alpha(0)
        if self._casing_show_hostages then
            self._casing_show_hostages = false
            self:_show_hostages()
        end
        if BAI:IsHostagePanelVisible() and not self._casing then
            self:_show_hostages(true)
        end
    end
'''


class LateBAIReplacementTests(unittest.TestCase):
    """Late BAI method replacement after KyoHUD hooks installed.

    BAI replaces HUDAssaultCorner._hide_icon_assaultbox after KyoHUD's PostHook
    on hide_casing is already installed. The fix must rebind at hide_casing entry
    (bounded, not per frame) and preserve BAI's hostage branches.
    """

    def test_late_bai_replacement_close_completes_and_hostage_branches(self):
        """Late BAI assignment after mount/show; close completes with hostage branches."""
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

            corner._casing_show_hostages = true
            corner._remove_hostage_offset = true

            _show_hostages_count = 0
            _set_hostages_offseted_count = 0
        ''')

        lua.execute(BAI_HIDE_ICON_FIXTURE)

        lua.execute('BAI._hostage_panel_visible = true')

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local corner = managers.hud._hud_assault_corner

            managers.hud:hide_casing()

            local prehide_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then prehide_nv = prehide_nv + 1 end
            end
            assert(prehide_nv == 7,
                "Prehide must retain 7 NV entries, got " .. tostring(prehide_nv))

            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.05, 0.05)
            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.10, 0.05)

            assert(AL._casing_root_panel ~= nil and AL._casing_root_panel:visible() == true,
                "Midpoint: owned root must be visible")
            local mid_alpha = AL._casing_root_panel:alpha()
            assert(mid_alpha > 0 and mid_alpha < 1,
                "Midpoint: owned root must have partial alpha, got " .. tostring(mid_alpha))
            assert(AL:_verify_casing_render() == true,
                "Midpoint: certification must be true")

            local mid_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then mid_nv = mid_nv + 1 end
            end
            assert(mid_nv == 7,
                "Midpoint: must retain 7 NV entries, got " .. tostring(mid_nv))

            for i = 1, 30 do
                _resume_coroutines(0.05)
            end

            assert(AL._casing_closing == false,
                "After finish: _casing_closing must be false")

            local after_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then after_nv = after_nv + 1 end
            end
            assert(after_nv == 0,
                "After finish: zero alerts entries, got " .. tostring(after_nv))

            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "After finish: owned root must be hidden")

            assert(_na.casing_bg_box:visible() == false,
                "After finish: native bg must be hidden")

            assert(math.abs(_na.icon_casingbox:alpha() - 0) < 0.001,
                "After finish: icon alpha must be 0, got " .. tostring(_na.icon_casingbox:alpha()))

            assert(_show_hostages_count == 2,
                "BAI hostage branches: _show_hostages called exactly 2 times, got "
                .. tostring(_show_hostages_count))

            assert(corner._casing_show_hostages == false,
                "BAI hostage branch: _casing_show_hostages must be cleared to false")
        ''')

    def test_idempotence_repeated_hide_with_late_replacement(self):
        """Idempotence: repeated hide/reload with late replacement retains method identity and return tuple."""
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local corner = managers.hud._hud_assault_corner

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)
        ''')

        lua.execute(BAI_HIDE_ICON_FIXTURE)

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local corner = managers.hud._hud_assault_corner
            local icon = _na.icon_casingbox

            _call_count = 0
            local orig_bai = HUDAssaultCorner._hide_icon_assaultbox
            function HUDAssaultCorner:_hide_icon_assaultbox(...)
                _call_count = _call_count + 1
                orig_bai(self, ...)
                return true, nil, 37, nil
            end

            _captured_return = nil
            local orig_animate = icon.animate
            function icon:animate(func, ...)
                local args = {...}
                local function wrapped_func(receiver, ...)
                    local inner_args = {...}
                    local function pack(...)
                        return {n = select("#", ...), ...}
                    end
                    _captured_return = pack(func(receiver, unpack(inner_args)))
                    return unpack(_captured_return, 1, _captured_return.n)
                end
                orig_animate(self, wrapped_func, unpack(args))
            end

            managers.hud:hide_casing()

            for i = 1, 30 do _resume_coroutines(0.05) end

            assert(_captured_return ~= nil, "Captured return must exist")
            assert(_captured_return.n == 4,
                "Captured return must have 4 values, got " .. tostring(_captured_return.n))
            assert(_captured_return[1] == true,
                "Captured [1] must be true")
            assert(_captured_return[2] == nil,
                "Captured [2] must be nil")
            assert(_captured_return[3] == 37,
                "Captured [3] must be 37, got " .. tostring(_captured_return[3]))
            assert(_captured_return[4] == nil,
                "Captured [4] must be nil")

            _first_method = HUDAssaultCorner._hide_icon_assaultbox
            assert(type(_first_method) == "function",
                "Prerequisite: method must be a function after first hide")

            assert(AL._casing_closing == false,
                "After finish: _casing_closing must be false")
            assert(_call_count == 1,
                "After first hide: counter must be 1, got " .. tostring(_call_count))
        ''')

        alerts_src = _read(ALERTS_PATH)
        if alerts_src:
            lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
            lua.execute(alerts_src)

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            managers.hud:show_casing(nil)
            RT:update(managers.hud, 2.0, 0.05)

            managers.hud:hide_casing()
            for i = 1, 30 do _resume_coroutines(0.05) end

            local second_method = HUDAssaultCorner._hide_icon_assaultbox
            assert(second_method == _first_method,
                "After second hide: method identity must be retained (no new third-party assignment)")

            assert(_call_count == 2,
                "After second hide: counter must be 2 exactly, got " .. tostring(_call_count))

            local after_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then after_nv = after_nv + 1 end
            end
            assert(after_nv == 0,
                "After second hide: zero entries, got " .. tostring(after_nv))
        ''')

    def test_disabled_alert_with_late_bai_replacement(self):
        """Disabled alerts with late BAI: zero entries, no owned transition, native preserved."""
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            kyohud.settings.enable_alerts = false
            RT:refresh_settings(managers.hud)

            local before_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then before_nv = before_nv + 1 end
            end
            assert(before_nv == 0,
                "Prerequisite: disabled must have 0 NV entries, got " .. tostring(before_nv))
            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "Prerequisite: no visible owned root when disabled")
        ''')

        lua.execute(BAI_HIDE_ICON_FIXTURE)

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            managers.hud:hide_casing()

            for i = 1, 30 do
                _resume_coroutines(0.05)
            end

            local after_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then after_nv = after_nv + 1 end
            end
            assert(after_nv == 0,
                "After hide disabled: zero entries, got " .. tostring(after_nv))

            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "After hide disabled: no owned transition")

            assert(_na.casing_bg_box:visible() == false,
                "After hide: native bg must be hidden")

            assert(math.abs(_na.icon_casingbox:alpha() - 0) < 0.001,
                "After hide: native icon alpha must be 0")
        ''')


    def test_wrapper_preserves_all_arguments_and_returns(self):
        """SOL probe: wrapper(self,icon,...) preserves every argument and return including trailing nil."""
        lua, ok = _lua_with_casing_close_fixture()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local corner = managers.hud._hud_assault_corner

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)
        ''')

        lua.execute('''
            _captured_args = nil
            function HUDAssaultCorner:_hide_icon_assaultbox(icon, ...)
                local function pack(...)
                    return {n = select("#", ...), ...}
                end
                _captured_args = pack(icon, ...)
                icon:set_alpha(0)
                return true, nil, 37, nil
            end
        ''')

        lua.execute('''
            local RT = kyohud.hud.runtime
            local corner = managers.hud._hud_assault_corner

            managers.hud:hide_casing()
            for i = 1, 30 do _resume_coroutines(0.05) end

            assert(kyohud.hud.alerts._casing_closing == false,
                "After finish: _casing_closing must be false")
        ''')

        lua.execute('''
            local corner = managers.hud._hud_assault_corner
            local icon = _na.icon_casingbox
            local installed = HUDAssaultCorner._hide_icon_assaultbox

            local function pack(...)
                return {n = select("#", ...), ...}
            end
            local sentinel = newproxy(false)
            local ret = pack(installed(corner, icon, sentinel, nil, 4, nil))

            assert(_captured_args ~= nil, "Third-party must have captured args")
            assert(_captured_args.n == 5,
                "Captured args count must be 5, got " .. tostring(_captured_args.n))
            assert(_captured_args[1] == icon,
                "Captured [1] must be icon")
            assert(_captured_args[2] == sentinel,
                "Captured [2] must be sentinel")
            assert(_captured_args[3] == nil,
                "Captured [3] must be nil")
            assert(_captured_args[4] == 4,
                "Captured [4] must be 4, got " .. tostring(_captured_args[4]))
            assert(_captured_args[5] == nil,
                "Captured [5] must be nil")

            assert(ret.n == 4,
                "Returned arity must be 4, got " .. tostring(ret.n))
            assert(ret[1] == true,
                "Returned [1] must be true")
            assert(ret[2] == nil,
                "Returned [2] must be nil")
            assert(ret[3] == 37,
                "Returned [3] must be 37, got " .. tostring(ret[3]))
            assert(ret[4] == nil,
                "Returned [4] must be nil")
        ''')


if __name__ == '__main__':
    unittest.main()
