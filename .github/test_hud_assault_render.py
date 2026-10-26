"""LOT3a -- hud/assault.lua: bounded slice renderer (RED state).

Scope: one visible-render transition for the assault HUD renderer.
The renderer creates owned primitives under RT._root_panel:
  _root_panel named kyohud_assault_panel
  _ticker_panel (clipping) containing _ticker_a and _ticker_b
  _hostages_prim, _converted_prim

RED state: assault.lua does not yet implement A:mount or A:update renderer
methods. Tests that depend on these methods must fail with a Lua assertion
error, not FileNotFoundError or skip.

Required DIESEL fixture methods (from test_hud_objectives + extensions):
  _panel_id           -- global creation counter (in DIESEL)
  panel:rect(opts)    -- child rect with optional clipping (EXTENSION)
  panel:set_x(v)      -- set x position (EXTENSION)
  panel:x()           -- read x position (in DIESEL)
  text:font_size()    -- read font size (in DIESEL)
  text:text_rect()    -- measure natural text bounds (in DIESEL, no clamp)
  panel:parent()      -- read parent identity (in DIESEL)

Required native managers (fixture):
  managers.groupai:state():hostage_count()        -> integer
  managers.groupai:state():all_converted_enemies() -> table of alive units
  managers.job:current_difficulty_stars()          -> integer (3)
  managers.localization:text(key)                  -> deterministic map

No police crest image. No visibility acquisition asserts.
No manifest/options/runtime edits. No test-side production implementation.
Immutable snapshots READ ONLY.
"""
from pathlib import Path
import json
import unittest
from lupa.luajit21 import LuaRuntime

from test_hud_assault import (
    STUBS,
    NATIVE_ASSAULT_CORNER_FIXTURE,
    HUDMANAGER_ASSAULT_FIXTURE,
    GROUPAI_STATE_FIXTURE,
)
from test_hud_objectives import DIESEL as DIESEL_BASE

ROOT = Path(__file__).resolve().parents[1]
ASSAULT_PATH = ROOT / "lua" / "hud" / "assault.lua"
LAYOUT_PATH = ROOT / "lua" / "hud" / "layout.lua"
RUNTIME_PATH = ROOT / "lua" / "hud" / "runtime.lua"
NATIVE_VIS_PATH = ROOT / "lua" / "hud" / "native_visibility.lua"

DIESEL = DIESEL_BASE + '''
function _make_panel_extended(name)
    _panel_id = _panel_id + 1
    local p = {
        _alive = true, _visible = true, _alpha = 1,
        _children = {}, _name = name or ("p" .. _panel_id),
        _x = 0, _y = 0, _w = 1920, _h = 1080,
        _layer = 0,
        _layer_explicit = false,
    }
    function p:x() return self._x end
    function p:y() return self._y end
    function p:w() return self._w end
    function p:h() return self._h end
    function p:set_x(v) self._x = v end
    function p:set_y(v) self._y = v end
    function p:set_shape(x,y,w,h) self._x=x; self._y=y; self._w=w; self._h=h end
    function p:set_visible(v) self._visible = v end
    function p:visible() return self._visible end
    function p:set_alpha(a) self._alpha = a end
    function p:alpha() return self._alpha end
    function p:set_layer(v) self._layer = v end
    function p:layer() return self._layer end
    function p:set_color(c) self._color = c end
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
        local ch = _make_panel_extended(opts and opts.name)
        ch._parent = self
        if opts then
            if opts.x then ch._x = opts.x end
            if opts.y then ch._y = opts.y end
            if opts.w then ch._w = opts.w end
            if opts.h then ch._h = opts.h end
            if opts.clipping ~= nil then ch._clipping = opts.clipping end
            if opts.visible ~= nil then ch._visible = opts.visible end
            if opts.alpha ~= nil then ch._alpha = opts.alpha end
            if opts.layer ~= nil then ch._layer = opts.layer; ch._layer_explicit = true end
        end
        self._children[ch._name] = ch
        return ch
    end
    function p:rect(opts)
        local ch = _make_panel_extended(opts and opts.name)
        ch._parent = self
        ch._is_rect = true
        if opts then
            if opts.x then ch._x = opts.x end
            if opts.y then ch._y = opts.y end
            if opts.w then ch._w = opts.w end
            if opts.h then ch._h = opts.h end
            if opts.clipping ~= nil then ch._clipping = opts.clipping end
            if opts.visible ~= nil then ch._visible = opts.visible end
            if opts.alpha ~= nil then ch._alpha = opts.alpha end
            if opts and opts.color then ch._color = opts.color end
            if opts.layer ~= nil then ch._layer = opts.layer; ch._layer_explicit = true end
        end
        self._children[ch._name] = ch
        return ch
    end
    function p:text(opts)
        local t = _make_panel_extended(opts and opts.name)
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
            if opts and opts.color then t._color = opts.color end
            if opts.layer ~= nil then t._layer = opts.layer; t._layer_explicit = true end
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
'''


HUD_RELAY_FIXTURE = r'''
managers.job = managers.job or {}
function managers.job:current_difficulty_stars()
    return managers.job._difficulty_stars or 0
end

local _loc_map = {
    ky_hud_assault_status = "ASSAULT",
    ky_hud_assault_endless = "ENDLESS",
    ky_hud_hostages_label = "HOSTAGES",
    ky_hud_converted_label = "CONVERTED",
}
managers.localization = managers.localization or {}
function managers.localization:text(key)
    return _loc_map[key] or ("LOC:" .. tostring(key))
end
function managers.localization:get_default_macro(key)
    if key == "BTN_SKULL" then return "S" end
    return "?"
end
'''


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute('_G.Color=function(a1,a2,a3,a4) if a4==nil then return{r=a1,g=a2,b=a3,a=1} else return{a=a1,r=a2,g=a3,b=a4} end end')
    lua.execute('tweak_data.hud = tweak_data.hud or {}; tweak_data.hud.medium_font_noshadow = "fonts/font_medium_mf"')
    lua.execute(NATIVE_ASSAULT_CORNER_FIXTURE)
    lua.execute(HUDMANAGER_ASSAULT_FIXTURE)
    lua.execute(GROUPAI_STATE_FIXTURE)
    lua.execute('''
        function GroupAIState:hostage_count() return self._hostage_count end
        function GroupAIState:all_converted_enemies() return self._converted end
    ''')
    lua.execute(DIESEL)
    lua.execute(HUD_RELAY_FIXTURE)
    lua.execute("_init_fp = _make_panel_extended('safe_hud_parent'); _init_fp._w=1920; _init_fp._h=1080")
    lua.execute("_init_mgr_safe = {panel = _init_fp}; _G.managers.hud = setmetatable({script = function(self, name) return _init_mgr_safe end, disabled = function() return false end}, {__index = HUDManager})")
    lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
    for path in [LAYOUT_PATH, NATIVE_VIS_PATH, RUNTIME_PATH]:
        src = _read(path)
        if src:
            lua.execute(src)
    assault_src = _read(ASSAULT_PATH)
    if assault_src:
        lua.execute(assault_src)
    return lua, assault_src is not None


def attach_native(lua):
    lua.execute(r'''
        managers.hud:_create_assault_corner()
        local corner = managers.hud._hud_assault_corner
        corner._hud_panel = _init_fp
        local assault_panel = _init_fp:panel({
            name = "assault_panel", x = 1520, y = 0, w = 400, h = 100, visible = false,
        })
        local icon_assaultbox = assault_panel:rect({
            name = "icon_assaultbox", x = 376, y = 0, w = 24, h = 24, visible = true,
        })
        icon_assaultbox._alpha = 1
        local bg_box = assault_panel:panel({
            x = 30, y = 0, w = 200, h = 38, visible = true,
        })
        corner._bg_box = bg_box
        local bg_leaf = bg_box:rect({name = "bg", x = 0, y = 0, w = 200, h = 38, visible = true})
        bg_leaf._alpha = 0.37
        local left_top = bg_box:rect({name = "left_top", x = 0, y = 0, w = 8, h = 8, visible = true})
        left_top._alpha = 0.37
        local left_bottom = bg_box:rect({name = "left_bottom", x = 0, y = 30, w = 8, h = 8, visible = true})
        left_bottom._alpha = 0.37
        local right_top = bg_box:rect({name = "right_top", x = 192, y = 0, w = 8, h = 8, visible = true})
        right_top._alpha = 0.37
        local right_bottom = bg_box:rect({name = "right_bottom", x = 192, y = 30, w = 8, h = 8, visible = false})
        right_bottom._alpha = 0.37
        local text_panel = bg_box:panel({name = "text_panel", x = 0, y = 0, w = 200, h = 38})
        text_panel._alpha = 0.37
        local third_party = assault_panel:panel({
            name = "third_party", x = 0, y = 50, w = 100, h = 20, visible = true,
        })
        third_party._alpha = 1
        local ap_text_panel = assault_panel:panel({
            name = "text_panel", x = 100, y = 50, w = 200, h = 24, visible = true,
        })
        ap_text_panel._alpha = 1
        local hostages_panel = _init_fp:panel({
            name = "hostages_panel", x = 1700, y = 0, w = 70, h = 38,
        })
        local hostages_icon = hostages_panel:rect({
            name = "hostages_icon", x = 0, y = 0, w = 24, h = 24, visible = true,
        })
        hostages_icon._alpha = 1
        local hostages_bg_box = hostages_panel:panel({
            x = 30, y = 0, w = 38, h = 38, visible = true,
        })
        corner._hostages_bg_box = hostages_bg_box
        local h_bg = hostages_bg_box:rect({name = "bg", x = 0, y = 0, w = 38, h = 38, visible = true})
        h_bg._alpha = 0.37
        local h_lt = hostages_bg_box:rect({name = "left_top", x = 0, y = 0, w = 6, h = 6, visible = true})
        h_lt._alpha = 0.37
        local h_lb = hostages_bg_box:rect({name = "left_bottom", x = 0, y = 32, w = 6, h = 6, visible = true})
        h_lb._alpha = 0.37
        local h_rt = hostages_bg_box:rect({name = "right_top", x = 32, y = 0, w = 6, h = 6, visible = true})
        h_rt._alpha = 0.37
        local h_rb = hostages_bg_box:rect({name = "right_bottom", x = 32, y = 32, w = 6, h = 6, visible = true})
        h_rb._alpha = 0.37
        local num_hostages = hostages_bg_box:text({
            name = "num_hostages", x = 0, y = 0, w = 38, h = 38, text = "0", visible = true,
        })
        num_hostages._alpha = 0.37
        local pnr_panel = _init_fp:panel({
            name = "point_of_no_return_panel", x = 0, y = 100, w = 300, h = 40, visible = false,
        })
        local casing_panel = _init_fp:panel({
            name = "casing_panel", x = 0, y = 200, w = 300, h = 40, visible = false,
        })
        local buffs_panel = _init_fp:panel({
            name = "buffs_panel", x = 0, y = 300, w = 200, h = 38, visible = false,
        })
        corner._point_of_no_return = false
        corner._casing = false
        corner._assault_mode = "normal"
        function corner:should_display_waves() return false end
        _na = {
            hud_panel = _init_fp,
            assault_panel = assault_panel,
            icon_assaultbox = icon_assaultbox,
            bg_box = bg_box,
            bg_leaf = bg_leaf,
            left_top = left_top,
            left_bottom = left_bottom,
            right_top = right_top,
            right_bottom = right_bottom,
            text_panel = text_panel,
            third_party = third_party,
            ap_text_panel = ap_text_panel,
            hostages_panel = hostages_panel,
            hostages_icon = hostages_icon,
            hostages_bg_box = hostages_bg_box,
            h_bg = h_bg, h_lt = h_lt, h_lb = h_lb, h_rt = h_rt, h_rb = h_rb,
            num_hostages = num_hostages,
            pnr_panel = pnr_panel,
            casing_panel = casing_panel,
            buffs_panel = buffs_panel,
        }
    ''')


def _lua_with_assault_state(difficulty_stars=3, hostages=4, converted_alive=2,
                            assault_mode=True, hunt_mode=False, assault_number=3):
    lua, ok = _lua()
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


class AssaultRenderProductionChunkTests(unittest.TestCase):
    def test_assault_file_exists_for_render(self):
        self.assertTrue(ASSAULT_PATH.is_file(), "RED: lua/hud/assault.lua must exist")
        src = _read(ASSAULT_PATH)
        self.assertIsNotNone(src)
        self.assertGreater(len(src), 0, "RED: assault.lua must not be empty")


class AssaultRenderEnabledTransitionTests(unittest.TestCase):
    """RED: enabled foundation+enable_assault renders visible root top right.

    Native groupAI: assault_mode=true, hunt_mode=false, assault_number=3,
    hostages=4 alive, converted=2 alive.

    After A:mount + A:update:
      - A._root_panel exists, named kyohud_assault_panel, visible
      - A._root_panel parent is RT._root_panel
      - A._ticker_panel exists (clipping) with _ticker_a and _ticker_b
      - A._hostages_prim and A._converted_prim exist
      - ticker text nonempty: status label + difficulty 3
      - hostages_prim text contains "4", converted_prim text contains "2"
      - root fully inside parent bounds
      - root outside objectives region (0,0,500,100)
      - combat sentinel unchanged
    After tick from t=10 to t=10.05:
      - ticker x moves left (decreases)
      - same primitive identities (no new creations, _panel_id unchanged)
    """

    def test_enabled_mount_update_visible_render(self):
        lua, ok = _lua_with_assault_state(
            difficulty_stars=3, hostages=4, converted_alive=2,
            assault_mode=True, hunt_mode=False, assault_number=3,
        )
        self.assertTrue(ok, "RED: assault.lua must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            assert(RT._root_panel, "RT._root_panel must exist after mount")
            assert(RT._mounted == true, "RT._mounted must be true")

            local A = kyohud.hud.assault
            assert(A, "A must exist")
            assert(type(A.mount) == "function",
                "RED: A:mount must be a function, got " .. tostring(type(A.mount)))

            A:mount(managers.hud)

            assert(type(A._root_panel) == "table",
                "RED: A._root_panel must exist after mount")
            assert(A._root_panel._name == "kyohud_assault_panel",
                "RED: A._root_panel name must be kyohud_assault_panel, got "
                .. tostring(A._root_panel._name))

            local root_vis = A._root_panel:visible()
            assert(root_vis == true,
                "RED: A._root_panel must be visible, got " .. tostring(root_vis))

            assert(A._root_panel:parent() == RT._root_panel,
                "RED: A._root_panel parent must be RT._root_panel")

            assert(type(A._ticker_panel) == "table",
                "RED: A._ticker_panel must exist")
            assert(A._ticker_panel._clipping == true,
                "RED: A._ticker_panel must have clipping=true")

            assert(type(A._ticker_a) == "table",
                "RED: A._ticker_a must exist")
            assert(type(A._ticker_b) == "table",
                "RED: A._ticker_b must exist")
            assert(A._ticker_a:parent() == A._ticker_panel,
                "RED: A._ticker_a parent must be A._ticker_panel")
            assert(A._ticker_b:parent() == A._ticker_panel,
                "RED: A._ticker_b parent must be A._ticker_panel")

            assert(type(A._hostages_prim) == "table",
                "RED: A._hostages_prim must exist")
            assert(type(A._converted_prim) == "table",
                "RED: A._converted_prim must exist")

            local ticker_a_text = A._ticker_a:text()
            assert(type(ticker_a_text) == "string" and #ticker_a_text > 0,
                "RED: ticker_a text must be nonempty, got " .. tostring(ticker_a_text))

            local hostages_text = A._hostages_prim:text()
            assert(type(hostages_text) == "string",
                "RED: hostages_prim text must be string, got " .. tostring(hostages_text))
            assert(hostages_text:find("4") ~= nil,
                "RED: hostages_prim text must contain '4', got " .. tostring(hostages_text))

            local converted_text = A._converted_prim:text()
            assert(type(converted_text) == "string",
                "RED: converted_prim text must be string, got " .. tostring(converted_text))
            assert(converted_text:find("2") ~= nil,
                "RED: converted_prim text must contain '2', got " .. tostring(converted_text))

            local macro_s = managers.localization:get_default_macro("BTN_SKULL")
            local ticker_text = A._ticker_a:text()
            local found_sss = ticker_text:find(macro_s .. macro_s .. macro_s) ~= nil
            local found_3 = ticker_text:find("3") ~= nil
            assert(found_sss or found_3,
                "RED: ticker must contain SSS (from BTN_SKULL macro) or explicit '3', got " .. tostring(ticker_text))

            local parent = RT._root_panel
            local rx = A._root_panel:x()
            local ry = A._root_panel:y()
            local rw = A._root_panel:w()
            local rh = A._root_panel:h()
            local pw = parent:w()
            local ph = parent:h()
            assert(rx >= 0 and ry >= 0,
                "RED: root must be inside parent (x>=0,y>=0), got x=" .. rx .. " y=" .. ry)
            assert(rx + rw <= pw and ry + rh <= ph,
                "RED: root must be inside parent bounds, got x+w="
                .. (rx+rw) .. " y+h=" .. (ry+rh) .. " pw=" .. pw .. " ph=" .. ph)

            assert(rx >= 500 or ry >= 100,
                "RED: root must be outside objectives region (0,0,500,100), got x="
                .. rx .. " y=" .. ry)

            local panel_id_after_mount = _panel_id

            local clip_x = A._ticker_panel:x()
            local ticker_x_before = A._ticker_a:x()
            local a_before = A._ticker_a
            local b_before = A._ticker_b

            A:update(managers.hud, 10.05, 0.05)

            local ticker_x_after = A._ticker_a:x()
            assert(ticker_x_after < ticker_x_before,
                "RED: ticker_a x must move left after tick, before="
                .. ticker_x_before .. " after=" .. ticker_x_after)

            assert(A._ticker_panel:x() == clip_x,
                "RED: _ticker_panel x must remain fixed at clip_x="
                .. clip_x .. " got=" .. A._ticker_panel:x())

            assert(rawequal(a_before, A._ticker_a),
                "RED: ticker_a identity must be preserved (rawequal)")
            assert(rawequal(b_before, A._ticker_b),
                "RED: ticker_b identity must be preserved (rawequal)")

            assert(_panel_id == panel_id_after_mount,
                "RED: no new panel creations after tick, before="
                .. panel_id_after_mount .. " after=" .. _panel_id)

            assert(A._hostages_prim:text():find("4") ~= nil,
                "RED: hostages_prim must still contain '4' after tick")
            assert(A._converted_prim:text():find("2") ~= nil,
                "RED: converted_prim must still contain '2' after tick")

            assert(kyohud.killstreak == _sentinel_before,
                "RED: combat sentinel must be unchanged, got "
                .. tostring(kyohud.killstreak) .. " expected " .. tostring(_sentinel_before))
        ''')


class AssaultRenderDisabledGateTests(unittest.TestCase):
    """RED: disabled gate -> root absent, no native mutation.

    With enable_assault=false (default), A:mount must not create any panel.
    A._root_panel must be nil. No native state mutation.
    """

    def test_disabled_no_root_no_native_mutation(self):
        lua, ok = _lua_with_assault_state(
            difficulty_stars=3, hostages=4, converted_alive=2,
            assault_mode=True, hunt_mode=False, assault_number=3,
        )
        self.assertTrue(ok, "RED: assault.lua must exist")

        lua.execute('''
            kyohud.settings.enable_assault = false

            local state_before_active = managers.groupai:state():get_assault_mode()
            local state_before_number = managers.groupai:state():get_assault_number()

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            assert(RT._root_panel, "RT._root_panel must exist")

            local A = kyohud.hud.assault
            assert(A, "A must exist")
            assert(type(A.mount) == "function",
                "RED: A:mount must be a function")

            A:mount(managers.hud)

            assert(A._root_panel == nil,
                "RED: disabled enable_assault must not create A._root_panel, got "
                .. tostring(A._root_panel))

            local state_after_active = managers.groupai:state():get_assault_mode()
            local state_after_number = managers.groupai:state():get_assault_number()
            assert(state_before_active == state_after_active,
                "RED: native groupAI assault_mode must not be mutated")
            assert(state_before_number == state_after_number,
                "RED: native groupAI assault_number must not be mutated")
        ''')


class AssaultVisualCorrectnessTests(unittest.TestCase):
    def test_visual_french_phalanx_crimespree(self):
        with open(ROOT / "loc" / "french.json", encoding="utf-8-sig") as f:
            fr = json.load(f)
        fr_status = fr["ky_hud_assault_status"]
        lua, ok = _lua_with_assault_state(
            difficulty_stars=0, hostages=4, converted_alive=2,
            assault_mode=True, hunt_mode=False, assault_number=3,
        )
        self.assertTrue(ok)
        lua.execute(f'''
            local _lm = {{ ky_hud_assault_status = "{fr_status}", ky_hud_assault_endless = "SANS FIN", ky_hud_hostages_label = "OTAGES", ky_hud_converted_label = "CONVERTIS" }}
            function managers.localization:text(k) return _lm[k] or ("LOC:"..tostring(k)) end
            kyohud.hud.runtime:mount(managers.hud)
            local A = kyohud.hud.assault; A:mount(managers.hud); A:update(managers.hud, 10.0, 0.05)
            local _,_,tw,_ = A._ticker_a:text_rect()
            assert(tw == A._ticker_a:w(), "ticker natural w must equal _ticker_a:w(), got "..tw.." vs "..A._ticker_a:w())
            local tc = A._ticker_a._color
            assert(tc and tc.a == 1, "text color alpha must be 1")
            assert(tc.r < 0.5 and tc.g < 0.5 and tc.b < 0.5, "text color must be dark RGB")
            managers.groupai:state()._hunt_mode = true; managers.hud:sync_set_assault_mode("phalanx")
            A:update(managers.hud, 10.1, 0.05)
            local tc2 = A._ticker_a._color
            assert(tc2 and tc2.a==1 and tc2.r==1 and tc2.g==1 and tc2.b==1, "phalanx text must be white RGB1 alpha1")
            assert(A._ticker_a:text():find("SANS FIN") ~= nil, "endless label must be present")
            local pid = _panel_id; local cx = A._ticker_panel:x()
            A:update(managers.hud, 1000, 1000)
            local ax = A._ticker_a:x(); local cy = A._ticker_measured_w + A._ticker_gap
            assert(ax >= -cy and ax <= 0, "ticker x must be in [-cycle,0], got "..ax.." cycle="..cy)
            assert(A._ticker_panel:x() == cx, "clip x must be fixed")
            assert(_panel_id == pid, "no new primitives")
            assert(A:_verify_render(), "root must be verified")
            local d = A:_resolve_difficulty_text()
            assert(d ~= "3", "difficulty must not be forged '3', got "..d)
        ''')
        lua.execute('''
            managers.crime_spree = managers.crime_spree or {}
            function managers.crime_spree:is_active() return true end
            function managers.crime_spree:server_spree_level() return 321 end
            local d = kyohud.hud.assault:_resolve_difficulty_text()
            assert(d:find("321") ~= nil, "CrimeSpree text must include 321, got "..d)
        ''')


class AssaultLayerContractRegressionTests(unittest.TestCase):
    """SOL regression: foreground siblings must have strictly higher layer than
    bg rect. When bg rect and sibling ticker panel/glyph/hostages/converted use
    equal layers, ordering is left unspecified by the engine and the actual
    Diesel cause of any observed occlusion is unproven. This test asserts the
    layer contract without simulating GPU occlusion. Through actual RT mount +
    A:update: foreground siblings strictly above bg, ticker text layers
    explicit, stable ordering over repeated normal updates, primitive
    identities preserved, render verified, native ownership stable.
    """

    def test_foreground_siblings_strictly_above_bg_layer(self):
        lua, ok = _lua_with_assault_state(
            difficulty_stars=3, hostages=4, converted_alive=2,
            assault_mode=True, hunt_mode=False, assault_number=3,
        )
        self.assertTrue(ok, "RED: assault.lua must exist")

        lua.execute('''
            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)

            local A = kyohud.hud.assault
            A:mount(managers.hud)
            A:update(managers.hud, 10.0, 0.05)

            local bg = A._bg_rect
            assert(bg, "bg_rect must exist")
            assert(type(bg.layer) == "function",
                "bg must expose native layer()")
            assert(type(bg.set_layer) == "function",
                "bg must expose native set_layer()")
            local bg_layer = bg:layer()
            assert(type(bg_layer) == "number",
                "bg layer must be number, got " .. type(bg_layer))

            local tp = A._ticker_panel
            assert(tp, "ticker_panel must exist")
            assert(type(tp.layer) == "function",
                "ticker_panel must expose native layer()")
            local tp_layer = tp:layer()
            assert(type(tp_layer) == "number",
                "ticker_panel layer must be number, got " .. type(tp_layer))
            assert(tp_layer > bg_layer,
                "ticker_panel layer must be strictly above bg, got tp="
                .. tostring(tp_layer) .. " bg=" .. tostring(bg_layer))

            local glyph = A._glyph_prim
            assert(glyph, "glyph_prim must exist")
            assert(type(glyph.layer) == "function",
                "glyph must expose native layer()")
            local glyph_layer = glyph:layer()
            assert(type(glyph_layer) == "number",
                "glyph layer must be number, got " .. type(glyph_layer))
            assert(glyph_layer > bg_layer,
                "glyph layer must be strictly above bg, got glyph="
                .. tostring(glyph_layer) .. " bg=" .. tostring(bg_layer))

            local hostages = A._hostages_prim
            assert(hostages, "hostages_prim must exist")
            assert(type(hostages.layer) == "function",
                "hostages must expose native layer()")
            local hostages_layer = hostages:layer()
            assert(type(hostages_layer) == "number",
                "hostages layer must be number, got " .. type(hostages_layer))
            assert(hostages_layer > bg_layer,
                "hostages layer must be strictly above bg, got h="
                .. tostring(hostages_layer) .. " bg=" .. tostring(bg_layer))

            local converted = A._converted_prim
            assert(converted, "converted_prim must exist")
            assert(type(converted.layer) == "function",
                "converted must expose native layer()")
            local converted_layer = converted:layer()
            assert(type(converted_layer) == "number",
                "converted layer must be number, got " .. type(converted_layer))
            assert(converted_layer > bg_layer,
                "converted layer must be strictly above bg, got c="
                .. tostring(converted_layer) .. " bg=" .. tostring(bg_layer))

            local ta = A._ticker_a
            local tb = A._ticker_b
            assert(ta, "ticker_a must exist")
            assert(tb, "ticker_b must exist")
            assert(type(ta.layer) == "function",
                "ticker_a must expose native layer()")
            assert(type(tb.layer) == "function",
                "ticker_b must expose native layer()")
            local ta_layer = ta:layer()
            local tb_layer = tb:layer()
            assert(type(ta_layer) == "number",
                "ticker_a layer must be explicit number, got " .. type(ta_layer))
            assert(type(tb_layer) == "number",
                "ticker_b layer must be explicit number, got " .. type(tb_layer))

            local bg_id = bg
            local tp_id = tp
            local glyph_id = glyph
            local hostages_id = hostages
            local converted_id = converted
            local ta_id = ta
            local tb_id = tb
            local bg_l0 = bg_layer
            local tp_l0 = tp_layer
            local gl_l0 = glyph_layer
            local ho_l0 = hostages_layer
            local co_l0 = converted_layer
            local ta_l0 = ta_layer
            local tb_l0 = tb_layer

            assert(A._ticker_a._layer_explicit == true,
                "ticker_a must have been created with explicit layer")
            assert(A._ticker_b._layer_explicit == true,
                "ticker_b must have been created with explicit layer")

            assert(A._native_acquired == true,
                "native must be acquired before stability comparison")
            local native_acquired_before = A._native_acquired

            for _i = 1, 10 do
                A:update(managers.hud, 10.05 + _i * 0.05, 0.05)
            end

            assert(rawequal(A._bg_rect, bg_id),
                "bg identity must be preserved after repeated updates")
            assert(rawequal(A._ticker_panel, tp_id),
                "ticker_panel identity must be preserved")
            assert(rawequal(A._glyph_prim, glyph_id),
                "glyph identity must be preserved")
            assert(rawequal(A._hostages_prim, hostages_id),
                "hostages identity must be preserved")
            assert(rawequal(A._converted_prim, converted_id),
                "converted identity must be preserved")
            assert(rawequal(A._ticker_a, ta_id),
                "ticker_a identity must be preserved")
            assert(rawequal(A._ticker_b, tb_id),
                "ticker_b identity must be preserved")

            assert(A._bg_rect:layer() == bg_l0,
                "bg layer must be stable after repeated updates")
            assert(A._ticker_panel:layer() == tp_l0,
                "ticker_panel layer must be stable")
            assert(A._glyph_prim:layer() == gl_l0,
                "glyph layer must be stable")
            assert(A._hostages_prim:layer() == ho_l0,
                "hostages layer must be stable")
            assert(A._converted_prim:layer() == co_l0,
                "converted layer must be stable")
            assert(A._ticker_a:layer() == ta_l0,
                "ticker_a layer must be stable")
            assert(A._ticker_b:layer() == tb_l0,
                "ticker_b layer must be stable")

            assert(A._ticker_panel:layer() > A._bg_rect:layer(),
                "ticker_panel ordering must remain strictly above bg")
            assert(A._glyph_prim:layer() > A._bg_rect:layer(),
                "glyph ordering must remain strictly above bg")
            assert(A._hostages_prim:layer() > A._bg_rect:layer(),
                "hostages ordering must remain strictly above bg")
            assert(A._converted_prim:layer() > A._bg_rect:layer(),
                "converted ordering must remain strictly above bg")

            assert(A._native_acquired == native_acquired_before,
                "native ownership must be stable, before="
                .. tostring(native_acquired_before) .. " after="
                .. tostring(A._native_acquired))

            assert(A:_verify_render(),
                "render must be verified after repeated updates")
        ''')
