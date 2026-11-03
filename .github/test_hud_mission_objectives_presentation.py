"""Mission presentation geometry regressions.

Scope: Mission-first geometry and mount decor under enable_mission=true,
enable_objectives=true. No objectives module, no assault/alerts/player/crew.

Two regressions:
  1. _compute_layout at 1920x1080 scale 1: desired position (x=40, y=36),
     mission row h=44.
  2. Real mount through runtime+mission: owned primitives exist with
     actual rect/color/alpha, desired visible contract.
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime
from test_hud_mission import (
    _lua as _base_lua,
    _read,
    ROOT,
    MISSION_PATH,
    LAYOUT_PATH,
    RUNTIME_PATH,
    NATIVE_VIS_PATH,
)

COLOR_FIXTURE = '''
Color = setmetatable({}, {
    __call = function(_, ...)
        local args = {...}
        if #args == 3 then
            return {r = args[1] or 0, g = args[2] or 0, b = args[3] or 0, a = 1, _is_color = true}
        elseif #args == 4 then
            return {a = args[1] or 1, r = args[2] or 0, g = args[3] or 0, b = args[4] or 0, _is_color = true}
        else
            return {r = 0, g = 0, b = 0, a = 1, _is_color = true}
        end
    end
})
'''

EXTENDED_DIESEL = '''
function _make_panel(name)
    _panel_id = _panel_id + 1
    local p = {
        _alive = true, _visible = true, _alpha = 1,
        _children = {}, _name = name or ("p" .. _panel_id),
        _w = 1920, _h = 1080,
    }
    function p:x() return self._x or 0 end
    function p:y() return self._y or 0 end
    function p:w() return self._w end
    function p:h() return self._h end
    function p:set_shape(x,y,w,h) self._x=x; self._y=y; self._w=w; self._h=h end
    function p:set_visible(v) self._visible = v end
    function p:visible() return self._visible end
    function p:set_alpha(a) self._alpha = a end
    function p:alpha() return self._alpha end
    function p:child(n) return self._children[n] end
    function p:remove(c)
        if c then
            for k, v in pairs(self._children) do
                if v == c then self._children[k] = nil; c._alive = false; return end
            end
        end
    end
    function p:panel(opts)
        local ch = _make_panel(opts and opts.name)
        if opts then
            if opts.x then ch._x = opts.x end
            if opts.y then ch._y = opts.y end
            if opts.w then ch._w = opts.w end
            if opts.h then ch._h = opts.h end
            if opts.color then ch._color = opts.color end
            if opts.alpha ~= nil then ch._alpha = opts.alpha end
            if opts.visible ~= nil then ch._visible = opts.visible end
            if opts.layer then ch._layer = opts.layer end
        end
        self._children[ch._name] = ch
        return ch
    end
    function p:text(opts)
        local t = _make_panel(opts and opts.name)
        if opts then
            if opts.x then t._x = opts.x end
            if opts.y then t._y = opts.y end
            if opts.w then t._w = opts.w end
            if opts.h then t._h = opts.h end
            if opts.visible ~= nil then t._visible = opts.visible end
            t._text = opts.text or ""
            t._font = opts.font
            t._font_size = opts.font_size
            t._color = opts.color
            t._align = opts.align
            t._vertical = opts.vertical
        end
        function t:set_text(str) self._text = str end
        function t:text() return self._text end
        function t:set_font(f) self._font = f end
        function t:font() return self._font end
        function t:set_font_size(sz) self._font_size = sz end
        function t:font_size() return self._font_size end
        function t:set_color(c) self._color = c end
        function t:color() return self._color end
        self._children[t._name] = t
        return t
    end
    function p:rect(opts)
        local r = self:panel(opts)
        function r:color() return self._color end
        function r:set_color(c) self._color = c end
        return r
    end
    function p:text_rect()
        local fs = self._font_size or 16
        return 0, 0, #(self._text or "") * fs * 0.6, fs
    end
    return p
end
'''

def _lua():
    """Create Lua runtime with extended fixtures."""
    lua, mission_exists = _base_lua(with_mission=True)
    lua.execute(COLOR_FIXTURE)
    lua.execute(EXTENDED_DIESEL)
    return lua, mission_exists


class MissionComputeLayoutGeometryTests(unittest.TestCase):
    """RED: Mission._compute_layout desired geometry at 1920x1080 scale 1."""

    def test_compute_layout_geometry_enabled_options(self):
        """_compute_layout with enable_mission/enable_objectives=true must return
        x=40, y=36, h=44 at 1920x1080 scale 1."""
        lua, ok = _lua()
        self.assertTrue(ok, "mission.lua must exist")
        if not ok:
            return

        lua.execute('''
            kyohud.settings.enable_mission = true
            kyohud.settings.enable_objectives = true
            _layout = kyohud.hud.mission:_compute_layout(1920, 1080, 1.0)
            _root_x = _layout and _layout.root_x or -1
            _root_y = _layout and _layout.root_y or -1
            _root_h = _layout and _layout.root_h or -1
        ''')
        g = lua.globals()
        rx = float(g._root_x)
        ry = float(g._root_y)
        rh = float(g._root_h)

        self.assertAlmostEqual(rx, 40.0, delta=1.0,
            msg="root_x must be near 40 at 1920x1080 scale 1")
        self.assertAlmostEqual(ry, 36.0, delta=1.0,
            msg="root_y must be near 36 at 1920x1080 scale 1")
        self.assertAlmostEqual(rh, 44.0, delta=1.0,
            msg="root_h must be near 44 at 1920x1080 scale 1")


class MissionMountPresentationTests(unittest.TestCase):
    """RED: real mount with enable_mission=true creates owned primitives."""

    def test_mission_mount_real_runtime_integration(self):
        """Real mount through runtime+mission with data before mount and
        registered actual feed callback. Assert root y>=100 (native reservation),
        h=44, three named owned dark rects plus timer yellow exact rgb and
        bags label SACS plus count 3."""
        lua, ok = _lua()
        self.assertTrue(ok, "mission.lua must exist")
        if not ok:
            return

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            kyohud.settings.enable_objectives = false
            kyohud.settings.hud_scale = 1.0

            local fp = _make_parent()
            local safe = _make_mgr(fp)
            local mgr = _G.managers.hud

            tweak_data = {
                hud = {medium_font_noshadow = "fonts/font_medium_mf"},
                carry = {small_loot = {}, gold = {is_vehicle = false}},
                levels = {firestarter_1 = {name_id = "heist_firestarter"}}
            }
            managers.job = {current_level_id = function() return "firestarter_1" end}
            managers.localization = {text = function(self, key)
                if key == "heist_firestarter" then return "Firestarter" end
                if key == "ky_hud_mission_title" then return "HEIST IN PROGRESS" end
                if key == "ky_hud_mission_bags" then return "SACS" end
                return key
            end}
            managers.loot = {
                _global = {secured = {{carry_id = "gold"}, {carry_id = "gold"}, {carry_id = "gold"}}}
            }
            function managers.loot:get_secured_bags_amount(is_vehicle)
                local n = 0
                for _, d in ipairs(self._global.secured) do
                    if not tweak_data.carry.small_loot[d.carry_id] then n = n + 1 end
                end
                return n
            end

            mgr:_create_heist_timer({})
            mgr:feed_heist_time(45)

            for _, e in ipairs(Hooks._all) do
                if e.method == "feed_heist_time" then e.fn(mgr, 45) end
            end

            kyohud.hud.runtime:mount(mgr)

            _root = kyohud.hud.mission._root_panel
            _root_x = _root and _root:x() or -1
            _root_y = _root and _root:y() or -1
            _root_h = _root and _root:h() or -1

            _timer_bg = _root and _root:child("mission_timer_bg") or nil
            _title_bg = _root and _root:child("mission_title_bg") or nil
            _bags_bg = _root and _root:child("mission_bags_bg") or nil

            _timer_bg_alpha = _timer_bg and _timer_bg:alpha() or -1
            _title_bg_alpha = _title_bg and _title_bg:alpha() or -1
            _bags_bg_alpha = _bags_bg and _bags_bg:alpha() or -1

            _timer_bg_w = _timer_bg and _timer_bg:w() or -1
            _timer_bg_h = _timer_bg and _timer_bg:h() or -1
            _title_bg_x = _title_bg and _title_bg:x() or -1
            _title_bg_w = _title_bg and _title_bg:w() or -1
            _title_bg_h = _title_bg and _title_bg:h() or -1
            _bags_bg_x = _bags_bg and _bags_bg:x() or -1
            _bags_bg_w = _bags_bg and _bags_bg:w() or -1
            _bags_bg_h = _bags_bg and _bags_bg:h() or -1
            _timer_bg_x = _timer_bg and _timer_bg:x() or -1

            _timer_bg_color = _timer_bg and _timer_bg._color or nil
            _timer_bg_r = _timer_bg_color and _timer_bg_color.r or -1
            _timer_bg_g = _timer_bg_color and _timer_bg_color.g or -1
            _timer_bg_b = _timer_bg_color and _timer_bg_color.b or -1
            _title_bg_color = _title_bg and _title_bg._color or nil
            _title_bg_r = _title_bg_color and _title_bg_color.r or -1
            _title_bg_g = _title_bg_color and _title_bg_color.g or -1
            _title_bg_b = _title_bg_color and _title_bg_color.b or -1
            _bags_bg_color = _bags_bg and _bags_bg._color or nil
            _bags_bg_r = _bags_bg_color and _bags_bg_color.r or -1
            _bags_bg_g = _bags_bg_color and _bags_bg_color.g or -1
            _bags_bg_b = _bags_bg_color and _bags_bg_color.b or -1

            _timer_prim = kyohud.hud.mission._timer_prim
            _timer_color = _timer_prim and _timer_prim:color() or nil
            _timer_r = _timer_color and _timer_color.r or -1
            _timer_g = _timer_color and _timer_color.g or -1
            _timer_b = _timer_color and _timer_color.b or -1

            _bags_label_prim = kyohud.hud.mission._bags_label_prim
            _bags_label_text = _bags_label_prim and _bags_label_prim:text() or nil
            _bags_prim = kyohud.hud.mission._bags_prim
            _bags_count_text = _bags_prim and _bags_prim:text() or nil
        ''')

        g = lua.globals()

        self.assertIsNotNone(g._root, "mounted mission must create root panel")
        root_x = float(g._root_x)
        root_y = float(g._root_y)
        root_h = float(g._root_h)

        self.assertAlmostEqual(root_x, 40.0, delta=1.0,
            msg="root_x must be near 40 at 1920x1080 scale 1")
        self.assertGreaterEqual(root_y, 100.0,
            "root y must be >= 100 (native reservation)")
        self.assertAlmostEqual(root_h, 44.0, delta=1.0,
            msg="root h must be near 44")

        self.assertIsNotNone(g._timer_bg, "mission_timer_bg rect must exist")
        self.assertIsNotNone(g._title_bg, "mission_title_bg rect must exist")
        self.assertIsNotNone(g._bags_bg, "mission_bags_bg rect must exist")

        timer_bg_w = float(g._timer_bg_w)
        timer_bg_h = float(g._timer_bg_h)
        title_bg_x = float(g._title_bg_x)
        title_bg_w = float(g._title_bg_w)
        title_bg_h = float(g._title_bg_h)
        bags_bg_x = float(g._bags_bg_x)
        bags_bg_w = float(g._bags_bg_w)
        bags_bg_h = float(g._bags_bg_h)
        timer_bg_x = float(g._timer_bg_x)

        self.assertGreater(timer_bg_w, 0, "timer bg w must be positive")
        self.assertGreater(title_bg_w, 0, "title bg w must be positive")
        self.assertGreater(bags_bg_w, 0, "bags bg w must be positive")
        self.assertAlmostEqual(timer_bg_h, 44.0, delta=1.0,
            msg="timer bg h must be near 44")
        self.assertAlmostEqual(title_bg_h, 44.0, delta=1.0,
            msg="title bg h must be near 44")
        self.assertAlmostEqual(bags_bg_h, 44.0, delta=1.0,
            msg="bags bg h must be near 44")
        self.assertAlmostEqual(title_bg_x, timer_bg_x + timer_bg_w, delta=1.0,
            msg="title x must equal timer x + timer w (joint)")
        self.assertAlmostEqual(bags_bg_x, title_bg_x + title_bg_w + 3, delta=1.0,
            msg="bags x must equal title x + title w + 3 (gap)")

        self.assertAlmostEqual(float(g._timer_bg_alpha), 0.86, delta=0.01,
            msg="timer bg alpha must be 0.86")
        self.assertAlmostEqual(float(g._title_bg_alpha), 0.80, delta=0.01,
            msg="title bg alpha must be 0.80")
        self.assertAlmostEqual(float(g._bags_bg_alpha), 0.80, delta=0.01,
            msg="bags bg alpha must be 0.80")

        self.assertAlmostEqual(float(g._timer_bg_r), 0.0, delta=0.01,
            msg="timer bg R must be black (0)")
        self.assertAlmostEqual(float(g._timer_bg_g), 0.0, delta=0.01,
            msg="timer bg G must be black (0)")
        self.assertAlmostEqual(float(g._timer_bg_b), 0.0, delta=0.01,
            msg="timer bg B must be black (0)")
        self.assertAlmostEqual(float(g._title_bg_r), 11/255, delta=0.01,
            msg="title bg R must be 11/255")
        self.assertAlmostEqual(float(g._title_bg_g), 13/255, delta=0.01,
            msg="title bg G must be 13/255")
        self.assertAlmostEqual(float(g._title_bg_b), 17/255, delta=0.01,
            msg="title bg B must be 17/255")
        self.assertAlmostEqual(float(g._bags_bg_r), 11/255, delta=0.01,
            msg="bags bg R must be 11/255")
        self.assertAlmostEqual(float(g._bags_bg_g), 13/255, delta=0.01,
            msg="bags bg G must be 13/255")
        self.assertAlmostEqual(float(g._bags_bg_b), 17/255, delta=0.01,
            msg="bags bg B must be 17/255")

        self.assertAlmostEqual(float(g._timer_r), 242/255, delta=0.01,
            msg="timer accent R must be 242/255")
        self.assertAlmostEqual(float(g._timer_g), 194/255, delta=0.01,
            msg="timer accent G must be 194/255")
        self.assertAlmostEqual(float(g._timer_b), 48/255, delta=0.01,
            msg="timer accent B must be 48/255")

        self.assertEqual(g._bags_label_text, "SACS",
            "bags label must be 'SACS'")
        self.assertEqual(g._bags_count_text, "3",
            "bags count must be '3'")


class ObjectivesEPresentationTests(unittest.TestCase):
    def test_combined_order_and_immediate_native_fallback(self):
        from test_hud_objectives_visibility import _lua_native_ready
        lua, ok = _lua_native_ready()
        self.assertTrue(ok)
        lua.execute('''
            local RT, M, O = kyohud.hud.runtime, kyohud.hud.mission, kyohud.hud.objectives
            local loc = managers.localization.text
            function managers.localization:text(id)
                if id == "ky_hud_mission_bags" then return "SACS" end
                if id == "ky_hud_mission_title" then return "HEIST IN PROGRESS" end
                return loc(self,id)
            end
            kyohud.settings.enable_mission = true
            RT:refresh_settings(managers.hud)
            assert(O._native_acquired, "positive objectives replacement")
            assert(M._root_panel and M:_verify_render(), "positive Mission rendering")
            assert(math.abs(M._root_panel:y()-36)<0.5, "Mission above objectives")
            assert(math.abs(O._root_panel:y()-83)<0.5, "objectives immediately below")
            local nv = kyohud.hud.native_visibility
            local release = nv.release
            function nv:release(owner, gen)
                if owner == O then
                    assert(M._root_panel:y() >= 100 or not M._root_panel:visible(),
                        "Mission vacates before native leaves are restored")
                end
                return release(self, owner, gen)
            end
            O._slot_prims[1].bg:set_alpha(0.1)
            O:_sync_native_visibility()
            assert(not O._native_acquired, "native returned on invalid render")
            assert(M._root_panel:y() >= 100 or not M._root_panel:visible(), "safe fallback")
            kyohud.settings.enable_objectives = false
            RT:refresh_settings(managers.hud)
            assert(M._mounted and not O._mounted, "Mission only")
            assert(M._root_panel:y() >= 100, "native reservation retained")
            kyohud.settings.enable_mission = false
            RT:refresh_settings(managers.hud)
            assert(not M._mounted and not O._mounted, "both off")
            kyohud.settings.enable_objectives = true
            RT:refresh_settings(managers.hud)
            assert(not M._mounted and O._mounted, "objectives only")
            assert(math.abs(O._root_panel:y()-36)<0.5, "no empty Mission row")
        ''')

    def test_objective_cell_and_secondary_progress(self):
        from test_hud_objectives_visibility import _lua_native_ready
        lua, ok = _lua_native_ready()
        self.assertTrue(ok)
        lua.execute('''
            local O = kyohud.hud.objectives
            local g = O._layout_cache
            assert(math.abs(g.root_x-40)<0.5 and math.abs(g.root_y-36)<0.5, "E objective-only anchor")
            local slot = O._slot_prims[1]
            assert(slot.bg and slot.marker, "owned objective decorations")
            assert(math.abs(slot.bg:h()-38)<0.5, "E cell height")
            assert(slot.bg:w() < 400, "short objective uses an intrinsic cell width")
            assert(math.abs(slot.marker:w()-6)<0.5 and math.abs(slot.marker:h()-6)<0.5, "small yellow marker")
            assert(slot.amount:font_size() == slot.text:font_size(), "progression matches title size")
            assert(O:_verify_render(), "decorated objective certified")
            local bg = slot.bg
            bg:set_alpha(0.1)
            assert(not O:_verify_render(), "background alpha corruption rejected")
            kyohud.hud.runtime:update(managers.hud, 2, 0.05)
            assert(O:_verify_render() and slot.bg == bg, "same-background recovery")
        ''')


class MissionMeasuredPresentationTests(unittest.TestCase):
    def test_owned_labels_are_certified_and_repaired(self):
        from test_hud_mission_acceptance import _lua_acc
        lua, ok = _lua_acc()
        self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local mgr = managers.hud
            mgr:_create_heist_timer({}); mgr:feed_heist_time(45)
            kyohud.hud.runtime:mount(mgr)
            local M = kyohud.hud.mission
            assert(M:_verify_render(), "initial rendering")
            local title, bags = M._title_prim, M._bags_prim
            title:set_text("CORRUPTED")
            assert(not M:_verify_render(), "actual title readback required")
            kyohud.hud.runtime:update(mgr, 1, 0.05)
            assert(M:_verify_render() and M._title_prim == title, "title repaired")
            bags:set_text("99999")
            assert(not M:_verify_render(), "actual bags readback required")
            kyohud.hud.runtime:update(mgr, 2, 0.05)
            assert(M:_verify_render() and M._bags_prim == bags, "bags repaired")
        ''')

    def test_long_title_fits_and_background_recovers_without_allocation(self):
        from test_hud_mission_acceptance import _lua_acc
        lua, ok = _lua_acc()
        self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            local mgr = managers.hud
            mgr:_create_heist_timer({})
            mgr:feed_heist_time(3661)
            managers.job = {current_level_id=function() return "test" end}
            tweak_data.levels.test.name_id = "heist_test"
            managers.localization = {text=function(_, id)
                if id == "ky_hud_mission_bags" then return "SACS" end
                return string.rep("Évasion longue ", 30)
            end}
            kyohud.hud.runtime:mount(mgr)
            local M = kyohud.hud.mission
            assert(M:_verify_render(), "initial mission certification")
            local title = M._title_prim
            local _, _, tw, th = title:text_rect()
            assert(tw <= title:w()+0.5 and th <= title:h()+0.5, "long title must fit")
            assert(M._timer_prim:text() == "01:01:01", "complete time preserved")
            local bg = M._backgrounds.title
            local creations = _create_count
            bg:set_shape(999,999,1,1)
            assert(not M:_verify_render(), "background corruption rejected")
            kyohud.hud.runtime:update(mgr, 1, 0.05)
            assert(M:_verify_render(), "ordinary update repairs background")
            assert(M._backgrounds.title == bg and M._title_prim == title, "same primitives")
            assert(_create_count == creations, "no allocations on recovery")
        ''')


class PresentationQualificationTests(unittest.TestCase):
    def test_history_frames_keep_own_width_when_current_refreshes(self):
        from test_hud_objectives_animation import _lua_native_ready_animation
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok)
        lua.execute('''
            local O,RT,OM=kyohud.hud.objectives,kyohud.hud.runtime,managers.objectives
            kyohud.settings.objectives_visible_limit=3
            OM:remove_objective("collect")
            local names={"Avancez dans le complexe","Piratez la base de données principale","Allez au laboratoire d'armement"}
            for i,name in ipairs(names) do
                OM._objectives["width"..i]={id="width"..i,text=name,sub_objectives={}}
            end
            local t=1
            local function step(dt) t=t+dt; RT:update(managers.hud,t,dt) end
            local function find(name)
                local found,n=nil,0
                for i=1,4 do
                    local s=i<=3 and O._slot_prims[i] or O._coordinated_slide_extra
                    if s and s.text:visible() and s.text:text()==name then found=s; n=n+1 end
                end
                assert(n==1,"exactly one displayed occurrence: "..name)
                return found
            end
            OM:activate_objective("width1",nil,{delay_presentation=false})
            local first_width=find(names[1]).bg:w()
            OM:complete_objective("width1")
            OM:activate_objective("width2",nil,{delay_presentation=false})
            for i=1,13 do step(0.1) end
            assert(O:_verify_render(),"first completion settled")
            local first,second=find(names[1]),find(names[2])
            local second_width=second.bg:w()
            assert(math.abs(first.bg:w()-first_width)<0.5,"older history does not inherit longer current width")
            assert(first.bg:w()<second_width,"different content keeps independent frame widths")
            OM:complete_objective("width2")
            OM:activate_objective("width3",nil,{delay_presentation=false})
            local elapsed=0
            for _,dt in ipairs({0.45,0.45,0.15,0.14,0.02}) do
                elapsed=elapsed+dt; step(dt)
                assert(O:_verify_render(),"history refresh certified")
                local a,b=find(names[1]),find(names[2])
                assert(math.abs(a.bg:w()-first_width)<0.5,"old history frame width stable through refresh")
                assert(math.abs(b.bg:w()-second_width)<0.5,"completed current frame width stable through refresh")
                if elapsed<1.2 then assert(a==first and b==second,"retained occurrence primitives") end
            end
            for i=1,5 do
                step(0.5)
                assert(O:_verify_render(),"ordinary refresh certified")
                assert(math.abs(find(names[1]).bg:w()-first_width)<0.5,"history width stable after polling")
                assert(math.abs(find(names[2]).bg:w()-second_width)<0.5,"second history width stable after polling")
            end
        ''')

    def test_completion_without_successor_keeps_its_frame_width(self):
        from test_hud_objectives_animation import _lua_native_ready_animation
        for quantitative in (False, True):
            with self.subTest(quantitative=quantitative):
                lua, ok = _lua_native_ready_animation()
                self.assertTrue(ok)
                lua.globals().quantitative=quantitative
                lua.execute('''
                    local O,RT,OM=kyohud.hud.objectives,kyohud.hud.runtime,managers.objectives
                    kyohud.settings.objectives_visible_limit=3
                    if not quantitative then
                        OM:remove_objective("collect")
                        OM._objectives.short={id="short",text="Piratez la base de données principale",sub_objectives={}}
                        OM:activate_objective("short",nil,{delay_presentation=false})
                    end
                    RT:refresh_settings(managers.hud)
                    local slot=O._slot_prims[1]
                    local bg=slot.bg
                    local before=bg:w()
                    assert(before<600,"initial frame is intrinsic")
                    if quantitative then
                        OM:complete_objective("collect"); OM:complete_objective("collect"); OM:complete_objective("collect")
                    else OM:complete_objective("short") end
                    for _,t in ipairs({1,1.45,1.9,2.05}) do
                        RT:update(managers.hud,t,0.15)
                        assert(O:_verify_render(),"completion still certified")
                        assert(slot.bg==bg,"same frame primitive")
                        assert(math.abs(bg:w()-before)<0.5,"completion alone must not widen frame")
                    end
                ''')

    def test_short_mission_title_with_fractional_measurement_is_not_truncated(self):
        from test_hud_mission_acceptance import _lua_acc
        lua, ok = _lua_acc()
        self.assertTrue(ok)
        lua.execute('''
            local original=_make_panel
            function _make_panel(name)
                local p=original(name)
                local text=p.text
                function p:text(opts)
                    local t=text(self,opts)
                    function t:text_rect()
                        return 0,0,#self:text()*self:font_size()*0.43+0.1,self:font_size()
                    end
                    return t
                end
                return p
            end
            kyohud.settings.enable_hud_foundation=true
            kyohud.settings.enable_mission=true
            managers.job={current_level_id=function() return "test" end}
            tweak_data.levels.test.name_id="heist_test"
            managers.localization={text=function(_,id)
                if id=="ky_hud_mission_bags" then return "BAGS" end
                return "Bijouterie"
            end}
            local mgr=managers.hud
            mgr:_create_heist_timer({}); mgr:feed_heist_time(41)
            kyohud.hud.runtime:mount(mgr)
            local M=kyohud.hud.mission
            assert(M._title_prim:text()=="Bijouterie","short Mission title must not receive ellipsis")
            assert(M:_verify_render(),"fractional measured title certified")
        ''')

    def test_short_objective_with_fractional_measurement_is_not_truncated(self):
        from test_hud_objectives_visibility import _lua_native_ready
        for factor in (0.20, 0.37, 0.42, 0.43, 0.51, 0.63, 0.69):
            with self.subTest(factor=factor):
                lua, ok = _lua_native_ready()
                self.assertTrue(ok)
                lua.globals().measurement_factor=factor
                lua.execute('''
                    local O=kyohud.hud.objectives
                    for i=1,3 do
                        for _,key in ipairs({"text","amount"}) do
                            local p=O._slot_prims[i][key]
                            function p:text_rect()
                                return 0,0,#self:text()*self:font_size()*measurement_factor+0.1,self:font_size()
                            end
                        end
                    end
                    local OM=managers.objectives
                    OM._objectives.jewels={id="jewels",text="Volez les bijoux",amount=8,current_amount=0,sub_objectives={}}
                    OM:activate_objective("jewels",nil,{delay_presentation=false})
                    kyohud.hud.runtime:update(managers.hud,2,0.05)
                    assert(O._slot_prims[1].text:text()=="Volez les bijoux","short objective must not receive ellipsis")
                    assert(O:_verify_render(),"fractional measured objective certified")
                ''')

    def test_background_noop_setter_fails_closed_then_recovers_same_objects(self):
        from test_hud_mission_acceptance import _lua_acc
        lua, ok = _lua_acc()
        self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation=true
            kyohud.settings.enable_mission=true
            local mgr=managers.hud
            mgr:_create_heist_timer({}); mgr:feed_heist_time(45)
            kyohud.hud.runtime:mount(mgr)
            local M=kyohud.hud.mission
            assert(M:_verify_render(),"baseline")
            local bg=M._backgrounds.title
            local setter=bg.set_shape
            bg:set_shape(999,999,1,1)
            function bg:set_shape() end
            kyohud.hud.runtime:update(mgr,1,0.05)
            assert(not M:_verify_render() and not M._native_acquired,"noop fails closed")
            bg.set_shape=setter
            kyohud.hud.runtime:update(mgr,2,0.05)
            assert(M:_verify_render() and M._backgrounds.title==bg,"same-object recovery")
        ''')

    def test_mission_palette_readback_and_recovery(self):
        from test_hud_mission_acceptance import _lua_acc
        lua, ok = _lua_acc()
        self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation=true
            kyohud.settings.enable_mission=true
            local mgr=managers.hud
            mgr:_create_heist_timer({}); mgr:feed_heist_time(45)
            kyohud.hud.runtime:mount(mgr)
            local M=kyohud.hud.mission
            assert(M:_verify_render(),"baseline")
            local t=M._title_prim
            local c=t:color()
            assert(math.abs(c.r-238/255)<0.001 and math.abs(c.g-241/255)<0.001
                and math.abs(c.b-244/255)<0.001,"Mission title E ink")
            t:set_color(Color(1,0,0))
            assert(not M:_verify_render(),"Mission ink corruption rejected")
            kyohud.hud.runtime:update(mgr,2,0.05)
            assert(M:_verify_render() and M._title_prim==t,"Mission same-text ink recovery")
        ''')

    def test_animation_decorations_follow_occurrences_and_reject_corruption(self):
        from test_hud_objectives_animation import _lua_native_ready_animation
        lua, ok = _lua_native_ready_animation()
        self.assertTrue(ok)
        lua.execute('''
            local O,RT,OM = kyohud.hud.objectives,kyohud.hud.runtime,managers.objectives
            kyohud.settings.objectives_visible_limit=3
            RT:refresh_settings(managers.hud)
            local outgoing = O._slot_prims[1]
            OM:complete_objective("collect"); OM:complete_objective("collect"); OM:complete_objective("collect")
            OM._objectives.next_obj={id="next_obj",text=string.rep("Évasion longue ",20),sub_objectives={}}
            OM:activate_objective("next_obj",nil,{delay_presentation=false})
            local t=1
            for _,dt in ipairs({0.45,0.45,0.15,0.14,0.02}) do
                t=t+dt; RT:update(managers.hud,t,dt)
                assert(O:_verify_render(), "animated rendering remains certified")
                for i=1,4 do
                    local s=i<=3 and O._slot_prims[i] or O._coordinated_slide_extra
                    if s and s.text and s.text:visible() and s.text:text()~="" then
                        assert(s.bg:visible() and s.marker:visible(), "no undecorated occurrence")
                        assert(math.abs(s.bg:y()-s.text:y())<0.01, "background follows text")
                        local a=s.bg:alpha()
                        assert(math.abs(a-s.text:alpha()*0.72)<0.01,"background follows animated alpha")
                        s.bg:set_alpha(0.123)
                        assert(not O:_verify_render(),"animated background alpha corruption rejected")
                        s.bg:set_alpha(a)
                        local y=s.marker:y(); s.marker:set_y(y+10)
                        assert(not O:_verify_render(),"animated marker position corruption rejected")
                        s.marker:set_y(y)
                        local marker_y = s.marker:y()
                        local marker_h = s.marker:h()
                        local bg_y = s.bg:y()
                        local bg_h = s.bg:h()
                        local marker_center = marker_y + marker_h * 0.5
                        local bg_center = bg_y + bg_h * 0.5
                        assert(math.abs(marker_center - bg_center) < 0.01 * O._layout_cache.e,
                            string.format("marker must be vertically centered in background: marker_center=%.2f bg_center=%.2f tolerance=%.4f",
                                marker_center, bg_center, 0.01 * O._layout_cache.e))
                        assert(O:_verify_render(),"restored decorations certified")
                    end
                end
                if t<2.2 then assert(O._slot_prims[1]==outgoing,"outgoing primitives retained") end
            end
            assert(O._slot_prims[2].text:text()=="Collect bags", "completed history retained")
            assert(math.abs(O._slot_prims[2].bg:alpha()-0.45*0.72)<0.01,"history background dimmed")
            local extra=O._coordinated_slide_extra
            if extra then assert(not extra.bg:visible() and not extra.marker:visible(),"extra decorations cleared") end
        ''')

    def test_measurement_cache_does_not_retain_destroyed_primitives(self):
        from test_hud_objectives_visibility import _lua_native_ready
        lua, ok = _lua_native_ready()
        self.assertTrue(ok)
        lua.execute('''
            local O,RT=kyohud.hud.objectives,kyohud.hud.runtime
            for i=1,4 do
                RT:rebuild(managers.hud)
                assert(O:_verify_render(),"rebuilt presentation certified")
                for p in pairs(O._natural_measurements or {}) do
                    local current=false
                    for j=1,3 do
                        if O._slot_prims[j].text==p then current=true end
                    end
                    if O._coordinated_slide_extra and O._coordinated_slide_extra.text==p then current=true end
                    assert(current,"measurement cache must only retain current primitives")
                end
            end
        ''')

    def test_objective_palette_is_secondary_and_certified(self):
        from test_hud_objectives_visibility import _lua_native_ready
        lua, ok = _lua_native_ready()
        self.assertTrue(ok)
        lua.execute('''
            local O = kyohud.hud.objectives
            local s = O._slot_prims[1]
            local function rgb(p,r,g,b)
                local c = p:color()
                assert(math.abs(c.r-r/255)<0.001 and math.abs(c.g-g/255)<0.001
                    and math.abs(c.b-b/255)<0.001, "desired E text palette")
            end
            rgb(s.text,211,218,224)
            rgb(s.amount,127,137,148)
            assert(O:_verify_render(), "initial palette certified")
            s.amount:set_color(Color(1,0,0))
            assert(not O:_verify_render(), "wrong progression RGB rejected")
            kyohud.hud.runtime:update(managers.hud,2,0.05)
            assert(O:_verify_render(), "progression palette repaired")
            rgb(s.amount,127,137,148)
        ''')

    def test_reference_geometry_matrix_and_native_reservation_unchanged(self):
        lua, ok = _lua()
        self.assertTrue(ok)
        lua.execute('''
            local L = kyohud.hud.layout
            for _, size in ipairs({{1920,1080},{1680,1050},{1280,720}}) do
                for _, scale in ipairs({0.95,1,1.05}) do
                    local w,h = size[1],size[2]
                    local e = math.min(w/1920,h/1080)*scale
                    local g = L.mission_objectives(w,h,scale,true,true,false)
                    assert(math.abs(g.x-40*e)<0.001 and math.abs(g.y-36*e)<0.001)
                    assert(math.abs(g.mission_h-44*e)<0.001)
                    assert(math.abs(g.objectives_y-(36+44+3)*e)<0.001)
                    assert(math.abs(g.content_h-38*e)<0.001 and math.abs(g.row_h-41*e)<0.001)
                    local fallback = L.mission_objectives(w,h,scale,true,false,true)
                    assert(fallback.y >= 100, "native logical reservation not scaled")
                    local solo = L.mission_objectives(w,h,scale,false,true,false)
                    assert(solo.x+solo.w <= w/2-80*e+0.001, "native timer budget")
                    local native = L.objectives_region(w,h)
                    assert(native.x==0 and native.y==0 and native.w==500 and native.h==100,
                        "Assault/Alerts legacy reservation unchanged")
                end
            end
        ''')


class ObjectiveReferenceFontSizeTests(unittest.TestCase):
    def test_default_objective_font_size_reference_28(self):
        """Objective default font_size must equal floor(28 * effective_scale).

        Tests at 1920x1080 and 1280x720 with scales 0.95, 1.0, 1.05.
        Current plus two histories must all use desired size after successive
        completion and settling. Title must fit row. Render certification true.
        Exact displayed order: obj3, obj2, obj1.
        """
        from test_hud_objectives_animation import _lua_native_ready_animation

        cases = [
            (1920, 1080, 0.95),
            (1920, 1080, 1.0),
            (1920, 1080, 1.05),
            (1280, 720, 0.95),
            (1280, 720, 1.0),
            (1280, 720, 1.05),
        ]

        for w, h, scale in cases:
            with self.subTest(w=w, h=h, scale=scale):
                lua, ok = _lua_native_ready_animation()
                self.assertTrue(ok, "animation-ready runtime required")
                if not ok:
                    return

                lua.globals()._test_w = w
                lua.globals()._test_h = h
                lua.globals()._test_scale = scale

                lua.execute('''
                    local O, RT, OM = kyohud.hud.objectives, kyohud.hud.runtime, managers.objectives
                    local w, h, scale = _test_w, _test_h, _test_scale

                    kyohud.settings.objectives_visible_limit = 3
                    kyohud.settings.enable_mission = false
                    kyohud.settings.hud_scale = scale

                    local rt_parent = RT._parent_panel
                    if rt_parent then
                        rt_parent._w = w
                        rt_parent._h = h
                    end

                    RT:rebuild(managers.hud)

                    local ly = O._layout_cache
                    assert(ly, "layout cache must exist after rebuild")

                    local effective_scale = ly.e
                    assert(math.abs(effective_scale - math.min(w/1920, h/1080)*scale) < 0.001,
                        string.format("ly.e must equal math.min(w/1920,h/1080)*scale: got %.6f, expected %.6f",
                            effective_scale, math.min(w/1920, h/1080)*scale))
                    local expected_fs = math.floor(28 * effective_scale)
                    assert(ly.font_size == expected_fs,
                        string.format("font_size at %dx%d scale %.2f: expected %d, got %d (effective_scale=%.3f)",
                            w, h, scale, expected_fs, ly.font_size, effective_scale))

                    local row_h = ly.row_h
                    assert(math.abs(row_h - 41 * effective_scale) < 0.5,
                        "row height (pitch) must be 41 * effective_scale")

                    local content_h = ly.content_h
                    assert(math.abs(content_h - 38 * effective_scale) < 0.5,
                        "content height must be 38 * effective_scale")

                    assert(content_h <= row_h,
                        "content_h must be <= row_h (pitch includes spacing)")

                    assert(ly.amount_font_size == ly.font_size,
                        "amount font size must equal title font_size")

                    OM:remove_objective("collect")
                    OM._objectives.obj1 = {id="obj1", text="Premier objectif", amount=3, current_amount=2, sub_objectives={}}
                    OM._objectives.obj2 = {id="obj2", text="Deuxième objectif", sub_objectives={}}
                    OM._objectives.obj3 = {id="obj3", text="Troisième objectif", amount=8, current_amount=3, sub_objectives={}}

                    OM:activate_objective("obj1", nil, {delay_presentation=false})
                    RT:update(managers.hud, 1, 0.05)
                    assert(O:_verify_render(), "initial render certified")

                    ly = O._layout_cache
                    local slot1 = O._slot_prims[1]
                    local fs1 = slot1.text:font_size()
                    assert(fs1 == expected_fs,
                        string.format("current text font_size %d != expected %d", fs1, expected_fs))

                    local _,_,tw,th = slot1.text:text_rect()
                    assert(tw <= ly.text_w + 0.5 and th <= content_h + 0.5,
                        string.format("title must fit content_h: tw=%.1f text_w=%.1f th=%.1f content_h=%.1f",
                            tw, ly.text_w, th, content_h))

                    OM:complete_objective("obj1")
                    OM:activate_objective("obj2", nil, {delay_presentation=false})
                    local t = 1
                    for _ = 1, 15 do
                        t = t + 0.1
                        RT:update(managers.hud, t, 0.1)
                    end
                    assert(O:_verify_render(), "first completion settled")

                    OM:complete_objective("obj2")
                    OM:activate_objective("obj3", nil, {delay_presentation=false})
                    for _ = 1, 15 do
                        t = t + 0.1
                        RT:update(managers.hud, t, 0.1)
                    end
                    assert(O:_verify_render(), "second completion settled")

                    ly = O._layout_cache
                    local texts = {}
                    for i = 1, 3 do
                        local slot = O._slot_prims[i]
                        if slot and slot.text:visible() and slot.text:text() ~= "" then
                            table.insert(texts, slot.text:text())
                            local fs = slot.text:font_size()
                            assert(fs == expected_fs,
                                string.format("slot %d text font_size %d != expected %d", i, fs, expected_fs))
                            local _,_,sw,sh = slot.text:text_rect()
                            assert(sw <= ly.text_w + 0.5 and sh <= content_h + 0.5,
                                string.format("slot %d title must fit content_h", i))
                            local amt_fs = slot.amount:font_size()
                            assert(amt_fs == expected_fs,
                                string.format("slot %d amount font_size %d != expected %d", i, amt_fs, expected_fs))
                            local amt_text = slot.amount:text()
                            if i == 1 then
                                assert(slot.amount:visible(), "current slot amount must be visible")
                                assert(amt_text == "3/8",
                                    "current slot amount text must be '3/8', got " .. tostring(amt_text))
                            elseif slot.amount:visible() then
                                assert(amt_text ~= "", "visible amount must display nonempty progress")
                            end
                        end
                    end
                    assert(#texts == 3, "current plus two histories must all be displayed")
                    assert(texts[1] == "Troisième objectif", "slot 1 must be obj3 (current)")
                    assert(texts[2] == "Deuxième objectif", "slot 2 must be obj2 (first history)")
                    assert(texts[3] == "Premier objectif", "slot 3 must be obj1 (second history)")

                    for i = 1, 3 do
                        local slot = O._slot_prims[i]
                        if slot and slot.text:visible() and slot.text:text() ~= "" then
                            local bg = slot.bg
                            local bg_y = bg:y()
                            local bg_h = bg:h()
                            local text_y = slot.text:y()
                            local text_h = slot.text:h()
                            local _,_,_,ink_h = slot.text:text_rect()

                            local bg_center = bg_y + bg_h * 0.5
                            local ink_center = text_y + (text_h - ink_h) * 0.5 + ink_h * 0.5

                            assert(math.abs(ink_center - bg_center) < 2 * effective_scale,
                                string.format("slot %d text ink must be vertically centered in background: ink_center=%.2f bg_center=%.2f tolerance=%.2f",
                                    i, ink_center, bg_center, 2 * effective_scale))

                            local ink_top = text_y + (text_h - ink_h) * 0.5
                            local ink_bottom = ink_top + ink_h
                            local bg_top = bg_y
                            local bg_bottom = bg_y + bg_h

                            assert(ink_top >= bg_top - 0.5 and ink_bottom <= bg_bottom + 0.5,
                                string.format("slot %d text ink bounds must be inside background: ink=[%.2f,%.2f] bg=[%.2f,%.2f]",
                                    i, ink_top, ink_bottom, bg_top, bg_bottom))

                            if slot.amount:visible() then
                                local amt_y = slot.amount:y()
                                local amt_h = slot.amount:h()
                                local _,_,_,amt_ink_h = slot.amount:text_rect()

                                local amt_ink_center = amt_y + (amt_h - amt_ink_h) * 0.5 + amt_ink_h * 0.5
                                assert(math.abs(amt_ink_center - bg_center) < 2 * effective_scale,
                                    string.format("slot %d amount ink must be vertically centered in background: amt_center=%.2f bg_center=%.2f",
                                        i, amt_ink_center, bg_center))
                            end

                            local marker = slot.marker
                            assert(marker, "required marker")
                            local marker_y = marker:y()
                            local marker_h = marker:h()
                            local marker_center = marker_y + marker_h * 0.5
                            assert(math.abs(marker_center - bg_center) < 0.01 * effective_scale,
                                string.format("slot %d marker must be vertically centered in background: marker_center=%.2f bg_center=%.2f tolerance=%.4f",
                                    i, marker_center, bg_center, 0.01 * effective_scale))
                        end
                    end

                    local bgs = {}
                    for i = 1, 3 do
                        local slot = O._slot_prims[i]
                        if slot and slot.bg and slot.text:visible() then
                            table.insert(bgs, slot.bg)
                        end
                    end
                    assert(#bgs == 3, "three backgrounds required for gap matrix, got " .. #bgs)
                    if #bgs >= 2 then
                        for i = 1, #bgs - 1 do
                            local bg_a = bgs[i]
                            local bg_b = bgs[i + 1]
                            local a_bottom = bg_a:y() + bg_a:h()
                            local b_top = bg_b:y()
                            local gap = b_top - a_bottom
                            assert(gap >= 3 * effective_scale - 0.5,
                                string.format("history backgrounds gap must be >= 3*e: got %.2f, expected >= %.2f",
                                    gap, 3 * effective_scale))
                        end
                    end

                    assert(O:_verify_render(), "final render fitting true")
                ''')


if __name__ == "__main__":
    unittest.main()
