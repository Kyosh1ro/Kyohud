"""Bounded ownership safety tests for hud/alerts.lua casing."""
import unittest

from test_hud_alerts_casing import _lua_with_assault_and_alerts_casing_slice, NATIVE_CASING_FIXTURE
from test_hud_alerts import ALERTS_PATH, NATIVE_PNR_SHOW_FIXTURE
from test_hud_assault_render import _read, _lua_with_assault_state, ROOT


ASSAULT_PATH = ROOT / "lua" / "hud" / "assault.lua"


def _lua_with_assault_only():
    lua, ok = _lua_with_assault_state(
        difficulty_stars=3, hostages=4, converted_alive=2,
        assault_mode=True, hunt_mode=False, assault_number=3,
    )
    if not ok:
        return lua, ok
    lua.execute('kyohud.settings.enable_alerts = false')
    lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
    lua.execute(NATIVE_PNR_SHOW_FIXTURE)
    lua.execute(NATIVE_CASING_FIXTURE)
    assault_src = _read(ASSAULT_PATH)
    if assault_src:
        lua.execute(assault_src)
    return lua, ok


class BoundedOwnershipSafetyTests(unittest.TestCase):
    def test_legacy_safety_without_alerts_arbiter(self):
        lua, ok = _lua_with_assault_only()
        self.assertTrue(ok, "assault.lua must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local A = kyohud.hud.assault
            local nv = kyohud.hud.native_visibility
            local corner = managers.hud._hud_assault_corner

            RT:mount(managers.hud)
            RT:update(managers.hud, 1.0, 0.05)

            assert(A._root_panel ~= nil and A._root_panel:visible() == true,
                "Before: A._root_panel must be visible during active assault")

            local before_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "assault" then before_nv = before_nv + 1 end
            end
            assert(before_nv == 14,
                "Before: expected 14 assault NV records, got " .. tostring(before_nv))

            assert(corner._casing == false,
                "Before: native corner._casing must be false")

            _na.casing_panel:set_visible(true)

            RT:update(managers.hud, 1.05, 0.05)

            assert(A._root_panel == nil or A._root_panel:visible() == false,
                "After: A._root_panel must be hidden when native casing_panel closes despite corner._casing=false")

            local after_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "assault" then after_nv = after_nv + 1 end
            end
            assert(after_nv == 0,
                "After: all 14 assault NV records must be released, got " .. tostring(after_nv))

            assert(kyohud.killstreak == _sentinel_before,
                "Combat sentinel must be preserved")
        ''')

    def test_collision_guard_foreign_casing_panel(self):
        lua, ok = _lua_with_assault_and_alerts_casing_slice(False)
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            RT:update(managers.hud, 1.0, 0.05)

            assert(AL._casing_root_panel == nil,
                "Before: AL._casing_root_panel must be nil when enable_alerts=false")

            local foreign = RT._root_panel:panel({
                name = "kyohud_casing_panel",
                x = 999, y = 888, w = 77, h = 66,
                visible = true,
            })
            foreign:set_alpha(0.73)
            local foreign_sentinel = foreign:rect({
                name = "sentinel", x = 10, y = 20, w = 30, h = 40, visible = true,
            })
            foreign_sentinel:set_alpha(0.91)

            local foreign_x = foreign:x()
            local foreign_y = foreign:y()
            local foreign_w = foreign:w()
            local foreign_h = foreign:h()
            local foreign_alpha = foreign:alpha()
            local foreign_vis = foreign:visible()
            local sentinel_alpha = foreign_sentinel:alpha()

            kyohud.settings.enable_alerts = true
            RT:refresh_settings(managers.hud)

            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.05, 0.05)

            assert(AL._casing_root_panel ~= foreign,
                "RED: AL._casing_root_panel must NOT adopt foreign panel")

            assert(RT._root_panel:child("kyohud_casing_panel") == foreign,
                "RED: foreign panel must remain as RT._root_panel child by name lookup")
            assert(foreign:child("sentinel") == foreign_sentinel,
                "RED: sentinel child must remain under foreign by name lookup")
            assert(foreign._alive == true,
                "RED: foreign panel must remain alive")
            assert(foreign_sentinel._alive == true,
                "RED: sentinel child must remain alive")

            assert(foreign:x() == foreign_x,
                "RED: foreign panel x must be unchanged")
            assert(foreign:y() == foreign_y,
                "RED: foreign panel y must be unchanged")
            assert(foreign:w() == foreign_w,
                "RED: foreign panel w must be unchanged")
            assert(foreign:h() == foreign_h,
                "RED: foreign panel h must be unchanged")
            assert(math.abs(foreign:alpha() - foreign_alpha) < 0.001,
                "RED: foreign panel alpha must be unchanged")
            assert(foreign:visible() == foreign_vis,
                "RED: foreign panel visible must be unchanged")

            assert(math.abs(foreign_sentinel:alpha() - sentinel_alpha) < 0.001,
                "RED: sentinel child alpha must be unchanged")

            local casing_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then casing_nv = casing_nv + 1 end
            end
            assert(casing_nv == 0,
                "RED: no casing NV records must be acquired when foreign panel present, got "
                .. tostring(casing_nv))

            assert(kyohud.killstreak == _sentinel_before,
                "Combat sentinel must be preserved")
        ''')

    def test_external_write_conflict_detection(self):
        lua, ok = _lua_with_assault_and_alerts_casing_slice(True)
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")

        lua.execute('''
            kyohud.settings.enable_alerts = true

            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(type(AL._casing_root_panel) == "table" and AL._casing_root_panel:visible() == true,
                "Before: AL._casing_root_panel must be visible during casing")

            local pos_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then pos_nv = pos_nv + 1 end
            end
            assert(pos_nv == 7,
                "Before: expected 7 casing NV records, got " .. tostring(pos_nv))

            _na.cas_text_panel:set_alpha(0.8)
            local external_alpha = _na.cas_text_panel:alpha()

            RT:update(managers.hud, 1.05, 0.05)

            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "After: AL._casing_root_panel must be hidden after external write conflict")

            local after_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then after_nv = after_nv + 1 end
            end
            assert(after_nv == 0,
                "After: all alerts NV records must be released after conflict, got " .. tostring(after_nv))

            assert(math.abs(_na.cas_text_panel:alpha() - external_alpha) < 0.001,
                "After: external alpha 0.8 must be preserved, got " .. tostring(_na.cas_text_panel:alpha()))

            RT:update(managers.hud, 2.0, 0.05)

            local poll_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then poll_nv = poll_nv + 1 end
            end
            assert(poll_nv == 0,
                "Poll: no NV records must be reacquired after conflict, got " .. tostring(poll_nv))

            assert(math.abs(_na.cas_text_panel:alpha() - external_alpha) < 0.001,
                "Poll: external alpha must remain preserved at poll")

            assert(_na.hud_panel:visible() == true,
                "Parent hud_panel must remain visible")
            assert(_na.casing_panel:visible() == true,
                "Casing panel parent must remain visible")
            assert(_na.cas_third_party:visible() == true
                and math.abs(_na.cas_third_party:alpha() - 0.59) < 0.001,
                "Third-party child must remain untouched")

            assert(kyohud.killstreak == _sentinel_before,
                "Combat sentinel must be preserved")
        ''')

    def test_late_native_casing_before_show_event(self):
        lua, ok = _lua_with_assault_and_alerts_casing_slice(True)
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")

        lua.execute('''
            kyohud.settings.enable_alerts = true

            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local corner = managers.hud._hud_assault_corner

            corner._casing = true
            _na.casing_panel:set_visible(true)
            _na.casing_bg_box:script().text_list = {"custom_unknown"}

            RT:mount(managers.hud)
            RT:update(managers.hud, 1.0, 0.05)

            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "RED: unsupported late casing must not show owned root")

            local late_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then late_nv = late_nv + 1 end
            end
            assert(late_nv == 0,
                "RED: unsupported late casing must not acquire NV records, got " .. tostring(late_nv))

            assert(_na.casing_panel:visible() == true,
                "Native casing_panel must remain visible")
            assert(_na.casing_bg_box:visible() == true,
                "Native casing_bg_box must remain visible")
        ''')

        lua2, ok2 = _lua_with_assault_and_alerts_casing_slice(True)
        self.assertTrue(ok2, "assault.lua fixture prerequisite must exist (fresh runtime)")

        lua2.execute('''
            kyohud.settings.enable_alerts = true

            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local corner = managers.hud._hud_assault_corner

            corner._casing = true
            _na.casing_panel:set_visible(true)
            _na.casing_bg_box:script().text_list = {"hud_casing_mode_ticker_clean", "hud_assault_end_line"}

            RT:mount(managers.hud)
            RT:update(managers.hud, 1.0, 0.05)

            assert(type(AL._casing_root_panel) == "table" and AL._casing_root_panel:visible() == true,
                "Positive: supported civilian late casing must show owned root")

            local civ_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then civ_nv = civ_nv + 1 end
            end
            assert(civ_nv == 7,
                "Positive: supported civilian late casing must acquire 7 NV records, got " .. tostring(civ_nv))

            local ticker_text = AL._casing_a:text()
            assert(ticker_text:find("CIVILIAN MODE") ~= nil,
                "Positive: ticker must contain CIVILIAN MODE, got " .. tostring(ticker_text))

            assert(kyohud.killstreak == _sentinel_before,
                "Combat sentinel must be preserved")
        ''')


if __name__ == '__main__':
    unittest.main()
