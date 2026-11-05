"""Real-chunk presentation recovery and native userdata boundaries."""
import unittest

from test_hud_assault_alerts_presentation import _lua_with_presentation_state
from test_hud_alerts_casing import _lua_with_assault_and_alerts_casing_slice


def runtime(mode, before=""):
    if mode == "assault":
        lua, ok = _lua_with_presentation_state()
    else:
        lua, ok = _lua_with_assault_and_alerts_casing_slice(True)
    assert ok
    lua.globals().presentation_mode = mode
    lua.execute(before)
    lua.execute(r'''
        local rt = kyohud.hud.runtime
        rt:mount(managers.hud)
        if presentation_mode == "assault" then
            subject = kyohud.hud.assault
            root_field = "_root_panel"
        else
            subject = kyohud.hud.alerts
            if presentation_mode == "casing" then
                managers.hud:show_casing(nil)
                root_field = "_casing_root_panel"
            else
                local s = managers.groupai:state()
                s._point_of_no_return_timer = 65.9
                s._point_of_no_return_id = 101
                s._point_of_no_return_tweak_id = "noreturn"
                s._is_inside_point_of_no_return = false
                managers.hud:show_point_of_no_return_timer("noreturn")
                managers.hud:feed_point_of_no_return_timer(65.9, false)
                root_field = "_root_panel"
            end
        end
        rt:update(managers.hud, 1, .05)
        assert(subject:_verify_render(), "positive initial render")
    ''')
    return lua


FIELDS = {
    "assault": ["_root_panel", "_ticker_panel", "_ticker_a", "_ticker_b",
                "_glyph_prim", "_hostages_bg", "_converted_bg",
                "_hostages_icon", "_converted_icon", "_hostages_prim"],
    "casing": ["_casing_root_panel", "_casing_ticker_panel", "_casing_a",
               "_casing_b", "_casing_bg", "_casing_icon"],
    "pnr": ["_root_panel", "_pnr_bg", "_pnr_icon", "_pnr_status_bg",
            "_timer_prim", "_title_prim", "_status_prim"],
}
DECORATION = {"assault": "_hostages_bg", "casing": "_casing_bg", "pnr": "_pnr_bg"}
ICON = {"assault": "_glyph_prim", "casing": "_casing_icon", "pnr": "_pnr_icon"}
TEXT = {"assault": "_ticker_a", "casing": "_casing_a", "pnr": "_timer_prim"}


class GeometryRecoveryTests(unittest.TestCase):
    def test_dead_status_icon_recreated_without_rebuilding_live_root(self):
        for mode, field in ICON.items():
            with self.subTest(mode=mode):
                lua = runtime(mode)
                lua.globals().field = field
                lua.execute(r'''
                    local p, root = subject[field], subject[root_field]
                    p._alive = false
                    assert(not subject:_verify_render(), "dead required icon rejected")
                    kyohud.hud.runtime:update(managers.hud,1.6,.05)
                    kyohud.hud.runtime:update(managers.hud,2.2,.05)
                    assert(subject:_verify_render(), "dead icon recovered")
                    assert(subject[field]~=p and subject[root_field]==root,
                        "only dead primitive recreated")
                ''')

    def test_noop_shape_setter_restores_native_then_recovers(self):
        for mode, field in DECORATION.items():
            with self.subTest(mode=mode):
                lua = runtime(mode)
                lua.globals().field = field
                lua.execute(r'''
                    local p, root = subject[field], subject[root_field]
                    local n, setter = _panel_id, p.set_shape
                    p:set_shape(p:x()+30,p:y(),p:w(),p:h())
                    p.set_shape = function() end
                    kyohud.hud.runtime:update(managers.hud,1.6,.05)
                    assert(not subject:_verify_render(), "no-op setter not certified")
                    assert(not root:visible(), "owned invalid presentation hidden")
                    local owner = presentation_mode=="assault" and "assault" or "alerts"
                    for _,entry in ipairs(kyohud.hud.native_visibility._entries) do
                        assert(entry.owner~=owner, "native intervention released")
                    end
                    p.set_shape = setter
                    kyohud.hud.runtime:update(managers.hud,2.2,.05)
                    assert(subject:_verify_render() and root:visible(), "recovery after setter repair")
                    assert(subject[field]==p and subject[root_field]==root and _panel_id==n,
                        "repair retains primitives without allocation")
                ''')

    def test_style_corruption_and_ordinary_update_recovery(self):
        for mode, field in DECORATION.items():
            with self.subTest(mode=mode):
                lua = runtime(mode)
                lua.globals().field = field
                lua.execute(r'''
                    local p, n = subject[field], _panel_id
                    p:set_color(Color(1,.42,.43,.44))
                    assert(not subject:_verify_render(), "corrupt decoration palette rejected")
                    kyohud.hud.runtime:update(managers.hud,1.6,.05)
                    assert(subject:_verify_render(), "decoration palette repaired")
                    assert(subject[field]==p and _panel_id==n, "same decoration retained")
                ''')

    def test_text_x_only_corruption_rejected(self):
        for mode, field in {"assault":"_hostages_prim", "casing":"_casing_a",
                            "pnr":"_title_prim"}.items():
            with self.subTest(mode=mode):
                lua = runtime(mode)
                lua.globals().field = field
                lua.execute(r'''
                    local p = subject[field]
                    p:set_shape(p:x()+30,p:y(),p:w(),p:h())
                    assert(not subject:_verify_render(), "text X corruption rejected")
                ''')

    def test_same_primitive_geometry_recovery(self):
        for mode, fields in FIELDS.items():
            for field in fields:
                with self.subTest(mode=mode, field=field):
                    lua = runtime(mode)
                    lua.globals().field = field
                    lua.execute(r'''
                        local p, root = subject[field], subject[root_field]
                        assert(p, field .. " required")
                        local n = _panel_id
                        p:set_shape(p:x()+30, p:y()+30, p:w()+30, p:h()+30)
                        assert(not subject:_verify_render(), field .. " corruption rejected")
                        kyohud.hud.runtime:update(managers.hud, 1.6, .05)
                        kyohud.hud.runtime:update(managers.hud, 2.2, .05)
                        assert(subject:_verify_render(), field .. " ordinary-update recovery")
                        assert(subject[field] == p and subject[root_field] == root,
                            "same actual primitive and root retained")
                        assert(_panel_id == n, "no allocations during repair")
                    ''')


class NativeUserdataAcceptanceTests(unittest.TestCase):
    def test_native_bitmap_api_and_converted_atlas_repair(self):
        for mode, field in ICON.items():
            with self.subTest(mode=mode):
                lua = runtime(mode)
                lua.globals().field = field
                lua.execute(r'''
                    local p = subject[field]
                    assert(type(p.texture_name)=="function" and type(p.set_image)=="function")
                    assert(p.texture==nil and p.set_texture==nil and p.texture_rect==nil,
                        "fixture must not invent unsupported Diesel bitmap methods")
                    if presentation_mode=="assault" then
                        local icon, n = subject._converted_icon, _panel_id
                        icon:set_texture_rect(0,0,1,1)
                        kyohud.hud.runtime:update(managers.hud,1.6,.05)
                        -- Inspect fixture setter output, not an invented native getter.
                        local rect = icon._texture_rect
                        assert(rect[1]==384 and rect[2]==512 and rect[3]==64 and rect[4]==64,
                            "bounded sync reapplies the native converted icon atlas crop")
                        assert(subject._converted_icon==icon and _panel_id==n)
                        assert(subject:_verify_render())
                    end
                ''')

    def test_missing_texture_keeps_native_visible(self):
        for mode in FIELDS:
            for throwing in [False, True]:
                with self.subTest(mode=mode, throwing=throwing):
                    if mode=="assault":
                        lua, ok = _lua_with_presentation_state()
                    else:
                        lua, ok = _lua_with_assault_and_alerts_casing_slice(True)
                    self.assertTrue(ok)
                    lua.globals().test_throw = throwing
                    lua.globals().presentation_mode = mode
                    lua.execute(r'''
                        function Idstring(path) return path end
                        DB = {has=function()
                            if test_throw then error("unavailable DB") end
                            return false
                        end}
                        local rt = kyohud.hud.runtime
                        rt:mount(managers.hud)
                        if presentation_mode=="casing" then
                            managers.hud:show_casing(nil)
                        elseif presentation_mode=="pnr" then
                            local s = managers.groupai:state()
                            s._point_of_no_return_timer,s._point_of_no_return_id=65.9,101
                            s._point_of_no_return_tweak_id="noreturn"
                            s._is_inside_point_of_no_return=false
                            managers.hud:show_point_of_no_return_timer("noreturn")
                            managers.hud:feed_point_of_no_return_timer(65.9,false)
                        end
                        rt:update(managers.hud,1,.05)
                        rt:update(managers.hud,1.6,.05)
                        assert(#kyohud.hud.native_visibility._entries==0,
                            "missing replacement texture cannot mask native HUD")
                    ''')

    def test_color_userdata_positive_and_negative(self):
        for mode, field in DECORATION.items():
            with self.subTest(mode=mode):
                lua = runtime(mode)
                lua.globals().field = field
                lua.execute(r'''
                    local p = subject[field]
                    local c = p:color()
                    local channels = {r=c.r, g=c.g, b=c.b, a=c.a}
                    local proxy = newproxy(true)
                    getmetatable(proxy).__index = channels
                    p.color = function() return proxy end
                    assert(subject:_verify_render(), "native Color userdata accepted")
                    channels.r = .42
                    assert(not subject:_verify_render(), "wrong native Color rejected")
                    channels.r = c.r
                    assert(subject:_verify_render(), "native Color restored")
                ''')

    def test_idstring_userdata_positive_and_negative(self):
        for mode, field in ICON.items():
            with self.subTest(mode=mode):
                lua = runtime(mode)
                lua.globals().field = field
                lua.execute(r'''
                    function Idstring(path)
                        local proxy = newproxy(true)
                        getmetatable(proxy).__index = {
                            key = function() return "HASH:" .. path end
                        }
                        return proxy
                    end
                    local p = subject[field]
                    local path = p:texture_name()
                    local actual = Idstring(path)
                    p.texture_name = function() return actual end
                    assert(subject:_verify_render(), "native texture Idstring accepted")
                    actual = Idstring("wrong/texture")
                    assert(not subject:_verify_render(), "wrong native texture rejected")
                    actual = Idstring(path)
                    assert(subject:_verify_render(), "native texture restored")
                ''')

    def test_missing_alpha_fails_closed(self):
        for mode, field in TEXT.items():
            with self.subTest(mode=mode):
                lua = runtime(mode)
                lua.globals().field = field
                lua.execute(r'''
                    local p = subject[field]
                    local alpha = p.alpha
                    p.alpha = nil
                    assert(not subject:_verify_render(), "missing alpha readback rejected")
                    p.alpha = alpha
                    assert(subject:_verify_render(), "alpha readback restored")
                ''')


class LayoutScaleMatrixTests(unittest.TestCase):
    def test_scale_matrix(self):
        for mode in FIELDS:
            for w, h in [(1920, 1080), (1280, 720), (1680, 1050)]:
                for scale in [.95, 1, 1.05]:
                    with self.subTest(mode=mode, w=w, h=h, scale=scale):
                        lua = runtime(mode)
                        lua.globals().requested_scale = scale
                        lua.globals().requested_w = w
                        lua.globals().requested_h = h
                        lua.execute(r'''
                            _init_fp._w, _init_fp._h = requested_w, requested_h
                            kyohud.settings.hud_scale = requested_scale
                            local rt = kyohud.hud.runtime
                            rt:rebuild(managers.hud)
                            rt:update(managers.hud, 1.6, .05)
                            local p = subject[root_field]
                            local e = math.min(requested_w/1920, requested_h/1080)*requested_scale
                            local rh = presentation_mode == "casing" and 40 or 70
                            assert(math.abs(p:w()-383*e)<.01, "reference width")
                            assert(math.abs(p:h()-rh*e)<.01, "reference height")
                            assert(math.abs(p:y()-36*e)<.01, "reference top")
                            assert(math.abs(p:x()+p:w()+40*e-requested_w)<.01,
                                "reference right margin")
                            assert(subject:_verify_render(), "scaled render certified")
                        ''')

    def test_long_french_pnr_title(self):
        lua = runtime("pnr", r'''
            local original = managers.localization.text
            function managers.localization:text(key, macros)
                if key == "ky_hud_pnr_title" then
                    return "POINT DE NON-RETOUR : ÉVACUEZ IMMÉDIATEMENT LA ZONE DANGEREUSE"
                end
                return original(self, key, macros)
            end
        ''')
        lua.execute(r'''
            local title, timer = subject._title_prim, subject._timer_prim
            assert(timer:text()=="01:05", "complete real timer")
            local _,_,tw,th = title:text_rect()
            assert(title:text()~="" and tw<=title:w()+.5, "fitted title ink")
            assert(title:x()+title:w()+10 <= timer:x()+.5, "title/timer gap")
            assert(subject:_verify_render(), "long UTF8 title certified")
        ''')


if __name__ == "__main__":
    unittest.main()