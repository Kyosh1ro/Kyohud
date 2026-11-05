"""LOT3a -- hud/assault.lua: Assault E composition presentation (RED state).

E composition spec at 1920x1080 scale=1 (e=1):
  - Ticker 340e x 40e, gap 3e, status bitmap 40e, upper row 383e
  - Right margin 40e, top 36e
  - Background ONLY behind ticker (not full root)
  - Two dark intrinsic counter cells below, top gap 4e, height 26e
  - Root height 70e (40+4+26)
  - Counter ink #C9D1D8, cell bg #0B0D11 alpha 0.75
  - Ticker ink #111111, ticker bg #F2E31B
  - Status bitmap texture: guis/textures/pd2/hud_icon_assaultbox
  - Counter icons: hostages=guis/textures/pd2/hud_icon_hostage; converted=nonempty native texture (chosen later)
  - Numeric values "4" and "2" exact
  - Cell width = text_rect_w + 20e padding + 16e icon + 6e gap
  - Cells right-aligned in root with 3e gap

RED: production uses old 380x76 layout with glyph text, not E composition.
"""
from pathlib import Path
import unittest
from lupa.luajit21 import LuaRuntime

from test_hud_assault import (
    STUBS,
    NATIVE_ASSAULT_CORNER_FIXTURE,
    HUDMANAGER_ASSAULT_FIXTURE,
    GROUPAI_STATE_FIXTURE,
)
from test_hud_assault_render import (
    DIESEL,
    HUD_RELAY_FIXTURE,
    ASSAULT_PATH,
    LAYOUT_PATH,
    RUNTIME_PATH,
    NATIVE_VIS_PATH,
    attach_native,
)

ROOT = Path(__file__).resolve().parents[1]

BITMAP_ENHANCEMENT = r'''
local _orig_make = _make_panel_extended
function _make_panel_extended(name)
    local p = _orig_make(name)
    function p:color() return self._color end
    local _base_set_color = p.set_color
    function p:set_color(c)
        if _base_set_color then _base_set_color(self, c) end
        if c then
            if c.a ~= nil then self._alpha = c.a end
            self._color = {r=c.r, g=c.g, b=c.b, a=c.a}
        end
    end
    local _base_set_alpha = p.set_alpha
    function p:set_alpha(a)
        if _base_set_alpha then _base_set_alpha(self, a) end
        if self._color then self._color = {r=self._color.r, g=self._color.g, b=self._color.b, a=a} end
    end
    function p:bitmap(opts)
        local ch = _make_panel_extended(opts and opts.name)
        ch._parent = self
        ch._is_bitmap = true
        ch._texture = opts and opts.texture
        if opts then
            if opts.x then ch._x = opts.x end
            if opts.y then ch._y = opts.y end
            if opts.w then ch._w = opts.w end
            if opts.h then ch._h = opts.h end
            if opts.visible ~= nil then ch._visible = opts.visible end
            if opts.alpha ~= nil then ch._alpha = opts.alpha end
            if opts.color then
                ch._color = {r=opts.color.r, g=opts.color.g, b=opts.color.b, a=opts.color.a}
            else
                ch._color = {r=1, g=1, b=1, a=1}
            end
            if opts.layer ~= nil then ch._layer = opts.layer; ch._layer_explicit = true end
        end
        local _tr_x, _tr_y, _tr_w, _tr_h = 0, 0, ch._w, ch._h
        if opts and opts.texture_rect then
            _tr_x = opts.texture_rect[1]
            _tr_y = opts.texture_rect[2]
            _tr_w = opts.texture_rect[3]
            _tr_h = opts.texture_rect[4]
        end
        function ch:set_texture_rect(x, y, w, h)
            _tr_x, _tr_y, _tr_w, _tr_h = x, y, w, h
            self._texture_rect = {x,y,w,h}
        end
        ch._texture_rect = {_tr_x,_tr_y,_tr_w,_tr_h}
        function ch:texture_name() return self._texture end
        function ch:set_image(t,x,y,w,h)
            self._texture = t
            if x~=nil then self:set_texture_rect(x,y,w,h) end
        end
        function ch:set_shape(x, y, w, h)
            self._x = x
            self._y = y
            self._w = w
            self._h = h
        end
        self._children[ch._name] = ch
        return ch
    end
    function p:set_shape(x, y, w, h)
        self._x = x
        self._y = y
        self._w = w
        self._h = h
    end
    return p
end
'''


def _lua_presentation():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute(
        '_G.Color=function(a1,a2,a3,a4)'
        ' if a4==nil then return{r=a1,g=a2,b=a3,a=1}'
        ' else return{a=a1,r=a2,g=a3,b=a4} end end'
    )
    lua.execute(
        'tweak_data.hud = tweak_data.hud or {};'
        ' tweak_data.hud.medium_font_noshadow = "fonts/font_medium_mf"'
    )
    lua.execute(NATIVE_ASSAULT_CORNER_FIXTURE)
    lua.execute(HUDMANAGER_ASSAULT_FIXTURE)
    lua.execute(GROUPAI_STATE_FIXTURE)
    lua.execute('''
        function GroupAIState:hostage_count() return self._hostage_count end
        function GroupAIState:all_converted_enemies() return self._converted end
    ''')
    lua.execute(DIESEL)
    lua.execute(BITMAP_ENHANCEMENT)
    lua.execute(HUD_RELAY_FIXTURE)
    lua.execute(
        "_init_fp = _make_panel_extended('safe_hud_parent');"
        " _init_fp._w=1920; _init_fp._h=1080"
    )
    lua.execute(
        "_init_mgr_safe = {panel = _init_fp};"
        " _G.managers.hud = setmetatable({"
        " script = function(self, name) return _init_mgr_safe end,"
        " disabled = function() return false end"
        " }, {__index = HUDManager})"
    )
    lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
    for path in [LAYOUT_PATH, NATIVE_VIS_PATH, RUNTIME_PATH]:
        lua.execute(path.read_text(encoding="utf-8-sig"))
    lua.execute(ASSAULT_PATH.read_text(encoding="utf-8-sig"))
    return lua, True


def _lua_with_presentation_state(difficulty_stars=3, hostages=4,
                                 converted_alive=2, assault_mode=True,
                                 hunt_mode=False, assault_number=3):
    lua, ok = _lua_presentation()
    if not ok:
        return lua, ok
    attach_native(lua)
    lua.execute(f'''
        managers.job._difficulty_stars = {difficulty_stars}
        local state = managers.groupai:state()
        state._assault_mode = {str(assault_mode).lower()}
        state._hunt_mode = {str(hunt_mode).lower()}
        state._assault_number = {assault_number}
        state._hostage_count = {hostages}
        state._converted = {{}}
        for _i = 1, {converted_alive} do
            local u = {{
                _alive = true,
                character_damage = function(self)
                    return {{dead = function() return false end}}
                end,
            }}
            table.insert(state._converted, u)
        end
        kyohud.settings.enable_hud_foundation = true
        kyohud.settings.enable_assault = true
        kyohud.killstreak = 17
        _sentinel_before = kyohud.killstreak
    ''')
    return lua, ok


class AssaultECompositionRegressionTests(unittest.TestCase):
    """Assault E composition: ticker+bitmap upper row, dark counter cells (RED)."""

    def test_presentation_primitives_certified_state(self):
        """Each required primitive must pass negative corruption then restore positive."""
        lua, ok = _lua_with_presentation_state(
            difficulty_stars=3, hostages=4, converted_alive=2,
            assault_mode=True, hunt_mode=False, assault_number=3,
        )
        self.assertTrue(ok, "assault.lua must exist")

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local A = kyohud.hud.assault
            A:mount(managers.hud)
            A:update(managers.hud, 1.0, 0.05)

            assert(A:_verify_render(), "initial render must verify")

            local function snap(p)
                return {
                    x=p:x(), y=p:y(), w=p:w(), h=p:h(),
                    c=p._color and {r=p._color.r, g=p._color.g, b=p._color.b, a=p._color.a},
                    v=p._visible, t=p._texture
                }
            end

            local function restore(p, s)
                p:set_shape(s.x, s.y, s.w, s.h)
                if s.c then p:set_color(Color(s.c.a, s.c.r, s.c.g, s.c.b)) end
                if s.v ~= nil then p:set_visible(s.v) end
            end

            local function test_geom(f, p)
                local s = snap(p)
                p:set_shape(s.x+30, s.y, s.w, s.h)
                assert(not A:_verify_render(), f.."_x rejected")
                p:set_shape(s.x, s.y, s.w, s.h)
                assert(A:_verify_render(), f.."_x restore")

                p:set_shape(s.x, s.y+30, s.w, s.h)
                assert(not A:_verify_render(), f.."_y rejected")
                p:set_shape(s.x, s.y, s.w, s.h)
                assert(A:_verify_render(), f.."_y restore")

                p:set_shape(s.x, s.y, s.w+30, s.h)
                assert(not A:_verify_render(), f.."_w rejected")
                p:set_shape(s.x, s.y, s.w, s.h)
                assert(A:_verify_render(), f.."_w restore")

                p:set_shape(s.x, s.y, s.w, s.h+30)
                assert(not A:_verify_render(), f.."_h rejected")
                p:set_shape(s.x, s.y, s.w, s.h)
                assert(A:_verify_render(), f.."_h restore")
            end

            local function test_vis(f, p)
                local s = snap(p)
                p:set_visible(false)
                assert(not A:_verify_render(), f.."_vis rejected")
                p:set_visible(s.v)
                assert(A:_verify_render(), f.."_vis restore")
            end

            local function test_col(f, p)
                local s = snap(p)
                p:set_color(Color(1, .2, .3, .4))
                assert(not A:_verify_render(), f.."_col rejected")
                if s.c then p:set_color(Color(s.c.a, s.c.r, s.c.g, s.c.b)) end
                assert(A:_verify_render(), f.."_col restore")
            end

            local function test_alpha(f, p)
                local s = snap(p)
                p:set_alpha(0)
                assert(not A:_verify_render(), f.."_alpha rejected")
                if s.c then p:set_color(Color(s.c.a, s.c.r, s.c.g, s.c.b)) end
                assert(A:_verify_render(), f.."_alpha restore")
            end

            local function test_tex(f, p)
                local s = snap(p)
                local orig_method = p.texture_name
                p.texture_name = nil
                assert(not A:_verify_render(), f.."_tex_method rejected")
                p.texture_name = orig_method
                assert(A:_verify_render(), f.."_tex_method restore")

                p:set_image("wrong/path")
                assert(not A:_verify_render(), f.."_tex_path rejected")
                p:set_image(s.t)
                assert(A:_verify_render(), f.."_tex_path restore")
            end

            test_geom("hostages_bg", A._hostages_bg)
            test_vis("hostages_bg", A._hostages_bg)
            test_col("hostages_bg", A._hostages_bg)
            test_alpha("hostages_bg", A._hostages_bg)

            test_geom("converted_bg", A._converted_bg)
            test_vis("converted_bg", A._converted_bg)
            test_col("converted_bg", A._converted_bg)
            test_alpha("converted_bg", A._converted_bg)

            test_geom("hostages_icon", A._hostages_icon)
            test_vis("hostages_icon", A._hostages_icon)
            test_tex("hostages_icon", A._hostages_icon)

            test_geom("converted_icon", A._converted_icon)
            test_vis("converted_icon", A._converted_icon)
            test_tex("converted_icon", A._converted_icon)

            test_geom("glyph_prim", A._glyph_prim)
            test_vis("glyph_prim", A._glyph_prim)
            test_tex("glyph_prim", A._glyph_prim)

            test_geom("ticker_a", A._ticker_a)
            test_vis("ticker_a", A._ticker_a)
            test_col("ticker_a", A._ticker_a)
            test_alpha("ticker_a", A._ticker_a)

            if A._ticker_b then
                local s = snap(A._ticker_b)
                A._ticker_b:set_shape(s.x+30, s.y, s.w, s.h)
                assert(not A:_verify_render(), "ticker_b_x rejected")
                A._ticker_b:set_shape(s.x, s.y, s.w, s.h)
                assert(A:_verify_render(), "ticker_b_x restore")
            end

            assert(A:_verify_render(), "final render must verify")
        ''')

    def test_e_composition_geometry_and_colors(self):
        """E composition layout with dark cells, bitmap status, exact numerics.

        RED: production uses old 380x76 root with glyph text, not E composition.
        """
        lua, ok = _lua_with_presentation_state(
            difficulty_stars=3, hostages=4, converted_alive=2,
            assault_mode=True, hunt_mode=False, assault_number=3,
        )
        self.assertTrue(ok, "RED: assault.lua must exist")

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local A = kyohud.hud.assault
            assert(A, "A must exist")
            assert(type(A.mount) == "function",
                "RED: A:mount must be a function")

            A:mount(managers.hud)
            assert(A._root_panel,
                "RED: A._root_panel must exist after mount")

            A:update(managers.hud, 1.0, 0.05)

            local parent_w = RT._root_panel:w()
            local parent_h = RT._root_panel:h()
            assert(parent_w == 1920 and parent_h == 1080,
                "test parent must be 1920x1080")

            local scale = kyohud.settings.hud_scale or 1
            local e = math.min(parent_w / 1920, parent_h / 1080) * scale
            assert(math.abs(e - 1) < 0.001,
                "e must be 1 at 1920x1080 scale=1, got " .. tostring(e))

            local expected_ticker_w = 340 * e
            local expected_ticker_h = 40 * e
            local expected_gap = 3 * e
            local expected_icon_w = 40 * e
            local expected_icon_h = 40 * e
            local expected_upper_row_w = 383 * e
            local expected_right_margin = 40 * e
            local expected_top = 36 * e
            local expected_counter_gap = 4 * e
            local expected_cell_h = 26 * e
            local expected_root_h = 70 * e
            local expected_ticker_font = 20 * e
            local expected_counter_font = 16 * e

            assert(type(A._ticker_panel) == "table",
                "RED: A._ticker_panel must exist")
            local ticker_w = A._ticker_panel:w()
            local ticker_h = A._ticker_panel:h()
            local sx,sy,state_ink,sh=A._ticker_a:text_rect()
            assert(ticker_w >= state_ink and ticker_w-state_ink <= 3*e+.001,
                "state panel must fit measured ink with minimal padding")
            assert(math.abs(A._ticker_panel:x()+ticker_w - 332*e) < 0.5)
            assert(math.abs(A._title_panel:w()+ticker_w - 316*e) < 0.5)
            assert(A._title_panel:x()+A._title_panel:w() < A._ticker_panel:x())
            assert(math.abs(ticker_h - expected_ticker_h) < 0.5,
                "RED: ticker_panel h must be 40e=" .. expected_ticker_h
                .. " got " .. ticker_h)

            local root_w = A._root_panel:w()
            local root_h = A._root_panel:h()
            assert(math.abs(root_w - expected_upper_row_w) < 0.5,
                "RED: root w must be 383e (upper row) got " .. root_w
                .. " expected " .. expected_upper_row_w)
            assert(math.abs(root_h - expected_root_h) < 0.5,
                "RED: root h must be 70e (40+4+26) got " .. root_h
                .. " expected " .. expected_root_h)
            local root_x = A._root_panel:x()
            local root_y = A._root_panel:y()
            local expected_root_x = parent_w - expected_right_margin - expected_upper_row_w
            assert(math.abs(root_x - expected_root_x) < 0.5,
                "RED: root x must be parent_w-margin-upper_row=" .. expected_root_x
                .. " got " .. root_x)
            assert(math.abs(root_y - expected_top) < 0.5,
                "RED: root y must be 36e=" .. expected_top
                .. " got " .. root_y)

            assert(type(A._glyph_prim) == "table",
                "RED: A._glyph_prim (status bitmap) must exist")
            assert(type(A._glyph_prim.texture_name) == "function",
                "RED: glyph_prim must be a bitmap with texture_name() getter")
            local glyph_tex = A._glyph_prim:texture_name()
            assert(glyph_tex == "guis/textures/pd2/hud_icon_assaultbox",
                "RED: glyph texture must be guis/textures/pd2/hud_icon_assaultbox"
                .. " got " .. tostring(glyph_tex))
            local glyph_x = A._glyph_prim:x()
            local glyph_w = A._glyph_prim:w()
            local glyph_h = A._glyph_prim:h()
            assert(math.abs(glyph_w - expected_icon_w) < 0.5,
                "RED: glyph w must be 40e=" .. expected_icon_w
                .. " got " .. glyph_w)
            assert(math.abs(glyph_h - expected_icon_h) < 0.5,
                "RED: glyph h must be 40e=" .. expected_icon_h
                .. " got " .. glyph_h)
            local expected_glyph_x = expected_ticker_w + expected_gap
            assert(math.abs(glyph_x - expected_glyph_x) < 0.5,
                "RED: glyph x must be ticker_w+gap=" .. expected_glyph_x
                .. " got " .. glyph_x)

            assert(type(A._bg_rect) == "table",
                "RED: A._bg_rect must exist")
            local bg_w = A._bg_rect:w()
            local bg_h = A._bg_rect:h()
            assert(math.abs(bg_w - expected_ticker_w) < 0.5,
                "RED: bg_rect w must match ticker w=340e=" .. expected_ticker_w
                .. " got " .. bg_w)
            assert(math.abs(bg_h - expected_ticker_h) < 0.5,
                "RED: bg_rect h must match ticker h=40e=" .. expected_ticker_h
                .. " got " .. bg_h)

            assert(type(A._hostages_bg) == "table",
                "RED: A._hostages_bg (dark cell rect) must exist")
            assert(type(A._converted_bg) == "table",
                "RED: A._converted_bg (dark cell rect) must exist")

            local hostages_bg_y = A._hostages_bg:y()
            local converted_bg_y = A._converted_bg:y()
            local expected_counter_y = expected_ticker_h + expected_counter_gap
            assert(math.abs(hostages_bg_y - expected_counter_y) < 0.5,
                "RED: hostages_bg y must be ticker_h+gap=" .. expected_counter_y
                .. " got " .. hostages_bg_y)
            assert(math.abs(converted_bg_y - expected_counter_y) < 0.5,
                "RED: converted_bg y must be ticker_h+gap=" .. expected_counter_y
                .. " got " .. converted_bg_y)

            local hostages_bg_h = A._hostages_bg:h()
            local converted_bg_h = A._converted_bg:h()
            assert(math.abs(hostages_bg_h - expected_cell_h) < 0.5,
                "RED: hostages_bg h must be 26e=" .. expected_cell_h
                .. " got " .. hostages_bg_h)
            assert(math.abs(converted_bg_h - expected_cell_h) < 0.5,
                "RED: converted_bg h must be 26e=" .. expected_cell_h
                .. " got " .. converted_bg_h)

            local hbg_color = A._hostages_bg._color
            assert(hbg_color ~= nil,
                "RED: hostages_bg must have color")
            local expected_dark_r = 0.043
            local expected_dark_g = 0.051
            local expected_dark_b = 0.067
            assert(math.abs(hbg_color.a - 0.75) < 0.02,
                "RED: hostages_bg color alpha must be 0.75, got " .. tostring(hbg_color.a))
            assert(math.abs(hbg_color.r - expected_dark_r) < 0.01,
                "RED: hostages_bg r must be #0B0D11 r=" .. expected_dark_r
                .. " got " .. tostring(hbg_color.r))
            assert(math.abs(hbg_color.g - expected_dark_g) < 0.01,
                "RED: hostages_bg g must be #0B0D11 g=" .. expected_dark_g
                .. " got " .. tostring(hbg_color.g))
            assert(math.abs(hbg_color.b - expected_dark_b) < 0.01,
                "RED: hostages_bg b must be #0B0D11 b=" .. expected_dark_b
                .. " got " .. tostring(hbg_color.b))

            local cbg_color = A._converted_bg._color
            assert(cbg_color ~= nil,
                "RED: converted_bg must have color")
            assert(math.abs(cbg_color.a - 0.75) < 0.02,
                "RED: converted_bg color alpha must be 0.75, got " .. tostring(cbg_color.a))
            assert(math.abs(cbg_color.r - expected_dark_r) < 0.01,
                "RED: converted_bg r must be #0B0D11 r=" .. expected_dark_r
                .. " got " .. tostring(cbg_color.r))

            assert(type(A._hostages_prim) == "table",
                "RED: A._hostages_prim must exist")
            assert(type(A._converted_prim) == "table",
                "RED: A._converted_prim must exist")

            local hostages_text = A._hostages_prim:text()
            local converted_text = A._converted_prim:text()
            assert(hostages_text == "4",
                "RED: hostages text must be exactly '4', got " .. tostring(hostages_text))
            assert(converted_text == "2",
                "RED: converted text must be exactly '2', got " .. tostring(converted_text))

            local hfont = A._hostages_prim:font_size()
            local cfont = A._converted_prim:font_size()
            assert(math.abs(hfont - expected_counter_font) < 0.5,
                "RED: hostages font must be 16e=" .. expected_counter_font
                .. " got " .. hfont)
            assert(math.abs(cfont - expected_counter_font) < 0.5,
                "RED: converted font must be 16e=" .. expected_counter_font
                .. " got " .. cfont)

            local tfont = A._ticker_a:font_size()
            assert(math.abs(tfont - expected_ticker_font) < 0.5,
                "RED: ticker font must be 20e=" .. expected_ticker_font
                .. " got " .. tfont)

            local counter_ink_r = 0.788
            local counter_ink_g = 0.820
            local counter_ink_b = 0.847
            local htext_color = A._hostages_prim._color
            assert(htext_color ~= nil,
                "RED: hostages_prim must have color")
            assert(math.abs(htext_color.a - 1) < 0.01,
                "RED: counter text alpha must be 1, got " .. tostring(htext_color.a))
            assert(math.abs(htext_color.r - counter_ink_r) < 0.01,
                "RED: counter text r must be #C9D1D8 r=" .. counter_ink_r
                .. " got " .. tostring(htext_color.r))
            assert(math.abs(htext_color.g - counter_ink_g) < 0.01,
                "RED: counter text g must be #C9D1D8 g=" .. counter_ink_g
                .. " got " .. tostring(htext_color.g))
            assert(math.abs(htext_color.b - counter_ink_b) < 0.01,
                "RED: counter text b must be #C9D1D8 b=" .. counter_ink_b
                .. " got " .. tostring(htext_color.b))

            local ctext_color = A._converted_prim._color
            assert(ctext_color ~= nil,
                "RED: converted_prim must have color")
            assert(math.abs(ctext_color.a - 1) < 0.01,
                "RED: converted text alpha must be 1")
            assert(math.abs(ctext_color.r - counter_ink_r) < 0.01,
                "RED: converted text r must be #C9D1D8 r=" .. counter_ink_r
                .. " got " .. tostring(ctext_color.r))

            local htext_y = A._hostages_prim:y()
            local htext_h = A._hostages_prim:h()
            assert(htext_y >= hostages_bg_y - 0.5,
                "RED: hostages text y must be >= cell y, got text_y="
                .. htext_y .. " cell_y=" .. hostages_bg_y)
            assert(htext_y + htext_h <= hostages_bg_y + hostages_bg_h + 0.5,
                "RED: hostages text must fit inside cell, got text_bottom="
                .. (htext_y + htext_h) .. " cell_bottom=" .. (hostages_bg_y + hostages_bg_h))

            local ctext_y = A._converted_prim:y()
            local ctext_h = A._converted_prim:h()
            assert(ctext_y >= converted_bg_y - 0.5,
                "RED: converted text y must be >= cell y")
            assert(ctext_y + ctext_h <= converted_bg_y + converted_bg_h + 0.5,
                "RED: converted text must fit inside cell")

            local _, _, htext_natural_w, _ = A._hostages_prim:text_rect()
            local _, _, ctext_natural_w, _ = A._converted_prim:text_rect()
            local pad_h = 20 * e
            local icon_w = 16 * e
            local ig_gap = 6 * e
            local expected_h_cell_w = htext_natural_w + pad_h + icon_w + ig_gap
            local expected_c_cell_w = ctext_natural_w + pad_h + icon_w + ig_gap
            local hbg_w = A._hostages_bg:w()
            local cbg_w = A._converted_bg:w()
            assert(math.abs(hbg_w - expected_h_cell_w) < 1.5,
                "RED: hostages_bg w must be text_w+pad+icon+gap="
                .. expected_h_cell_w .. " got " .. hbg_w)
            assert(math.abs(cbg_w - expected_c_cell_w) < 1.5,
                "RED: converted_bg w must be text_w+pad+icon+gap="
                .. expected_c_cell_w .. " got " .. cbg_w)

            local converted_bg_x = A._converted_bg:x()
            local converted_bg_right = converted_bg_x + cbg_w
            assert(math.abs(converted_bg_right - root_w) < 1.5,
                "RED: converted cell right must align at root_w="
                .. root_w .. " got " .. converted_bg_right)
            local hostages_bg_x = A._hostages_bg:x()
            local hostages_bg_right = hostages_bg_x + hbg_w
            assert(math.abs(hostages_bg_right - (converted_bg_x - expected_gap)) < 1.5,
                "RED: hostages cell right must be converted_x-gap="
                .. (converted_bg_x - expected_gap) .. " got " .. hostages_bg_right)

            assert(type(A._hostages_icon) == "table",
                "RED: A._hostages_icon (bitmap) must exist")
            assert(type(A._converted_icon) == "table",
                "RED: A._converted_icon (bitmap) must exist")
            assert(type(A._hostages_icon.texture_name) == "function",
                "RED: hostages_icon must be bitmap with texture_name()")
            assert(type(A._converted_icon.texture_name) == "function",
                "RED: converted_icon must be bitmap with texture_name()")
            local hi_tex = A._hostages_icon:texture_name()
            local ci_tex = A._converted_icon:texture_name()
            assert(hi_tex == "guis/textures/pd2/hud_icon_hostage",
                "RED: hostages_icon texture must be hud_icon_hostage got "
                .. tostring(hi_tex))
            assert(type(ci_tex) == "string" and #ci_tex > 0,
                "RED: converted_icon texture must be a nonempty native texture path got "
                .. tostring(ci_tex))

            local bg_color = A._bg_rect._color
            assert(bg_color ~= nil, "RED: bg_rect must have color")
            assert(math.abs(bg_color.a - 1) < 0.01,
                "RED: bg_rect color alpha must be 1")
            local expected_yellow_r = 0.949
            local expected_yellow_g = 0.890
            local expected_yellow_b = 0.106
            assert(math.abs(bg_color.r - expected_yellow_r) < 0.01,
                "RED: bg_rect r must be #F2E31B r=" .. expected_yellow_r
                .. " got " .. tostring(bg_color.r))
            assert(math.abs(bg_color.g - expected_yellow_g) < 0.01,
                "RED: bg_rect g must be #F2E31B g=" .. expected_yellow_g
                .. " got " .. tostring(bg_color.g))
            assert(math.abs(bg_color.b - expected_yellow_b) < 0.01,
                "RED: bg_rect b must be #F2E31B b=" .. expected_yellow_b
                .. " got " .. tostring(bg_color.b))

            local text_color = A._ticker_a._color
            assert(text_color ~= nil, "RED: ticker_a must have color")
            assert(math.abs(text_color.a - 1) < 0.01,
                "RED: ticker text alpha must be 1")
            local expected_ink_r = 0.067
            local expected_ink_g = 0.067
            local expected_ink_b = 0.067
            assert(math.abs(text_color.r - expected_ink_r) < 0.01,
                "RED: ticker text r must be #111111 r=" .. expected_ink_r
                .. " got " .. tostring(text_color.r))
            assert(math.abs(text_color.g - expected_ink_g) < 0.01,
                "RED: ticker text g must be #111111 g=" .. expected_ink_g
                .. " got " .. tostring(text_color.g))
            assert(math.abs(text_color.b - expected_ink_b) < 0.01,
                "RED: ticker text b must be #111111 b=" .. expected_ink_b
                .. " got " .. tostring(text_color.b))

            assert(A:_verify_render(),
                "RED: render must be verified for E composition")
        ''')


if __name__ == "__main__":
    unittest.main()
