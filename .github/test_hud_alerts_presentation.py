"""LOT3b -- hud/alerts.lua: E banner presentation for casing and PNR (RED state).

E composition at 1920x1080 scale=1 (e=1):
  Casing: root 383x40 at right40/top36; ticker 340x40; _casing_bg rect
    x0/y0/w340/h40 dark #0B0D11 alpha 0.80; _casing_icon bitmap
    guis/textures/pd2/hud_icon_stealthbox at x343/y0/w40/h40; amber text.
  PNR: root 383x70 at right40/top36; _pnr_bg rect x0/y0/w340/h40 cyan
    #7FCDE3; _pnr_icon bitmap hud_icon_noreturnbox at x343/y0/w40/h40;
    title font 20e at x12, timer font 20e right edge 328, status font 16e
    in compact dark cell y44/h26 right-aligned.

RED: production uses old 380x38 (casing) and 380x76 (PNR) geometry,
no _casing_bg/_casing_icon/_pnr_bg/_pnr_icon primitives.
"""
import unittest

from test_hud_alerts_casing import _lua_with_assault_and_alerts_casing_slice

LUA_SHARED_HELPERS = r'''
    local TOL = 0.5

    local function al_is_finite(v)
        if type(v) ~= "number" then return false end
        if v ~= v then return false end
        if v == math.huge or v == -math.huge then return false end
        return true
    end

    local function assert_rect(label, prim, ex, ey, ew, eh)
        assert(type(prim) == "table", label .. " must exist as table")
        assert(math.abs(prim:x() - ex) < TOL,
            label .. " x expected " .. ex .. " got " .. tostring(prim:x()))
        assert(math.abs(prim:y() - ey) < TOL,
            label .. " y expected " .. ey .. " got " .. tostring(prim:y()))
        assert(math.abs(prim:w() - ew) < TOL,
            label .. " w expected " .. ew .. " got " .. tostring(prim:w()))
        assert(math.abs(prim:h() - eh) < TOL,
            label .. " h expected " .. eh .. " got " .. tostring(prim:h()))
    end

    local function assert_color(label, prim, er, eg, eb, ea)
        local c = prim._color
        assert(c ~= nil, label .. " must have _color")
        assert(math.abs(c.r - er) < 0.01,
            label .. " r expected " .. er .. " got " .. tostring(c.r))
        assert(math.abs(c.g - eg) < 0.01,
            label .. " g expected " .. eg .. " got " .. tostring(c.g))
        assert(math.abs(c.b - eb) < 0.01,
            label .. " b expected " .. eb .. " got " .. tostring(c.b))
        if ea ~= nil then
            assert(math.abs(c.a - ea) < 0.02,
                label .. " a expected " .. ea .. " got " .. tostring(c.a))
        end
    end

    local function assert_bitmap(label, prim, etex, ex, ey, ew, eh)
        assert(type(prim) == "table", label .. " must exist as table")
        assert(type(prim.texture_name) == "function",
            label .. " must be bitmap with texture_name() getter")
        assert(prim:texture_name() == etex,
            label .. " texture expected " .. etex .. " got " .. tostring(prim:texture_name()))
        assert_rect(label, prim, ex, ey, ew, eh)
    end

    local function snap_rect(p)
        return {x=p:x(), y=p:y(), w=p:w(), h=p:h()}
    end

    local function corrupt_restore_x(label, prim, verify_fn)
        local s = snap_rect(prim)
        prim:set_shape(s.x + 30, s.y, s.w, s.h)
        assert(not verify_fn(),
            label .. " corrupt x+30 must fail _verify_render")
        prim:set_shape(s.x, s.y, s.w, s.h)
        assert(verify_fn(),
            label .. " restore x must pass _verify_render")
    end

    local DARK_R = 0x0B / 255
    local DARK_G = 0x0D / 255
    local DARK_B = 0x11 / 255
    local CYAN_R = 0x7F / 255
    local CYAN_G = 0xCD / 255
    local CYAN_B = 0xE3 / 255
'''


def _fresh_lua():
    lua, ok = _lua_with_assault_and_alerts_casing_slice(True)
    return lua, ok


class CasingEBannerPresentationTests(unittest.TestCase):
    """Casing E banner: 383x40 root, dark bg rect, stealth icon, amber text (RED)."""

    def test_casing_e_banner_geometry_primitives_and_corruption(self):
        lua, ok = _fresh_lua()
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")
        lua.execute(LUA_SHARED_HELPERS + r'''
            kyohud.settings.enable_alerts = true
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            local pw = RT._root_panel:w()

            assert_rect("casing_root", AL._casing_root_panel,
                pw - 40 - 383, 36, 383, 40)
            assert(AL._casing_root_panel:visible() == true,
                "casing_root must be visible")

            assert(AL._casing_ticker_panel._clipping == true,
                "ticker_panel must have clipping=true")
            assert_rect("ticker_panel", AL._casing_ticker_panel,
                AL._casing_ticker_panel:x(), AL._casing_ticker_panel:y(), 340, 40)

            assert_rect("_casing_bg", AL._casing_bg, 0, 0, 340, 40)
            assert_color("_casing_bg", AL._casing_bg,
                DARK_R, DARK_G, DARK_B, 0.80)

            assert_bitmap("_casing_icon", AL._casing_icon,
                "guis/textures/pd2/hud_icon_stealthbox", 343, 0, 40, 40)

            local a_text = AL._casing_a:text()
            assert(type(a_text) == "string" and a_text:find("CASING MODE") ~= nil,
                "normal casing text must contain CASING MODE, got " .. tostring(a_text))

            assert_color("casing_a", AL._casing_a, 0.8, 0.6, 0.2, nil)

            local root_w = AL._casing_root_panel:w()
            assert(math.abs(root_w - 383) < TOL,
                "casing_root w must fit right edge 383, got " .. tostring(root_w))

            assert(AL:_verify_render() == true,
                "RED: _verify_render must be true for casing E banner")

            corrupt_restore_x("_casing_bg", AL._casing_bg, function()
                return AL:_verify_render()
            end)

            local ax0 = AL._casing_a:x()
            local id_a, id_b = AL._casing_a, AL._casing_b
            RT:update(managers.hud, 1.05, 0.05)
            assert(AL._casing_a:x() < ax0,
                "ticker_a must move left after tick")
            assert(rawequal(id_a, AL._casing_a) and rawequal(id_b, AL._casing_b),
                "ticker identities preserved")

            managers.hud:show_casing("civilian")
            RT:update(managers.hud, 1.10, 0.05)
            local civ = AL._casing_a:text()
            assert(type(civ) == "string" and civ:find("CIVILIAN MODE") ~= nil,
                "civilian text must contain CIVILIAN MODE, got " .. tostring(civ))

            assert(kyohud.killstreak == _sentinel_before,
                "combat sentinel preserved")
        ''')


class PnrEBannerPresentationTests(unittest.TestCase):
    """PNR E banner: 383x70 root, cyan bg rect, noreturn icon, title+timer+status (RED)."""

    def test_pnr_e_banner_geometry_primitives_and_corruption(self):
        lua, ok = _fresh_lua()
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")
        lua.execute(LUA_SHARED_HELPERS + r'''
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

            local pw = RT._root_panel:w()

            assert_rect("pnr_root", AL._root_panel,
                pw - 40 - 383, 36, 383, 70)
            assert(AL._root_panel:visible() == true,
                "pnr_root must be visible")

            local root_w = AL._root_panel:w()
            assert(math.abs(root_w - 383) < TOL,
                "pnr_root w must fit right edge 383, got " .. tostring(root_w))

            assert_rect("_pnr_bg", AL._pnr_bg, 0, 0, 340, 40)
            assert_color("_pnr_bg", AL._pnr_bg,
                CYAN_R, CYAN_G, CYAN_B, nil)

            assert_bitmap("_pnr_icon", AL._pnr_icon,
                "guis/textures/pd2/hud_icon_noreturnbox", 343, 0, 40, 40)

            local pnr_timer = AL._root_panel:child("pnr_timer")
            local pnr_title = AL._root_panel:child("pnr_title")
            local pnr_status = AL._root_panel:child("pnr_status")
            local pnr_status_bg = AL._root_panel:child("pnr_status_bg")
            assert(type(pnr_timer) == "table", "pnr_timer must exist")
            assert(type(pnr_title) == "table", "pnr_title must exist")
            assert(type(pnr_status) == "table", "pnr_status must exist")
            assert(type(pnr_status_bg) == "table", "pnr_status_bg must exist")

            assert(pnr_timer:text() == "01:05",
                "timer text must be 01:05, got " .. tostring(pnr_timer:text()))
            assert(math.abs(pnr_timer:font_size() - 20) < TOL,
                "timer font must be 20e")

            local timer_x = pnr_timer:x()
            local timer_w = pnr_timer:w()
            assert(math.abs((timer_x + timer_w) - 328) < TOL,
                "timer right edge x+w must be 328, got " .. tostring(timer_x + timer_w))

            assert(math.abs(pnr_title:x() - 12) < TOL,
                "title x must be 12e")
            assert(math.abs(pnr_title:font_size() - 20) < TOL,
                "title font must be 20e")

            local title_x = pnr_title:x()
            local available_w = timer_x - 10 - title_x
            local ok_tr, _, _, t_ink_w, _ = pcall(function() return pnr_title:text_rect() end)
            assert(ok_tr and al_is_finite(t_ink_w),
                "title text_rect must be measurable")
            assert(t_ink_w <= available_w + TOL,
                "title measured ink " .. tostring(t_ink_w) .. " must fit available width " .. tostring(available_w))

            local ok_tm, _, _, tm_ink_w, _ = pcall(function() return pnr_timer:text_rect() end)
            assert(ok_tm and al_is_finite(tm_ink_w),
                "timer text_rect must be measurable")
            assert(tm_ink_w <= timer_w + TOL,
                "timer measured ink " .. tostring(tm_ink_w) .. " must fit timer width " .. tostring(timer_w))

            local st = pnr_status:text()
            assert(type(st) == "string" and st:upper():find("OUTSIDE") ~= nil,
                "status must contain OUTSIDE, got " .. tostring(st))
            assert(math.abs(pnr_status:y() - 44) < TOL,
                "status y must be 44e")
            assert(math.abs(pnr_status:h() - 26) < TOL,
                "status h must be 26e")
            assert(math.abs(pnr_status:font_size() - 16) < TOL,
                "status font must be 16e")

            assert_color("pnr_status_bg", pnr_status_bg,
                DARK_R, DARK_G, DARK_B, 0.75)

            assert(AL:_verify_render() == true,
                "RED: _verify_render must be true for PNR E banner")

            corrupt_restore_x("_pnr_bg", AL._pnr_bg, function()
                return AL:_verify_render()
            end)

            state._point_of_no_return_timer = 65.1
            state._is_inside_point_of_no_return = true
            managers.hud:feed_point_of_no_return_timer(65.1, true)
            RT:update(managers.hud, 1.05, 0.05)
            local st2 = pnr_status:text()
            assert(type(st2) == "string" and st2:upper():find("INSIDE") ~= nil,
                "status must contain INSIDE after feed")

            local alerts_nv = 0
            for _, ent in ipairs(nv._entries or {}) do
                if ent.owner == "alerts" then alerts_nv = alerts_nv + 1 end
            end
            assert(alerts_nv == 8,
                "expected 8 alerts NV records, got " .. tostring(alerts_nv))

            assert(kyohud.killstreak == _sentinel_before,
                "combat sentinel preserved")
        ''')


if __name__ == "__main__":
    unittest.main()
