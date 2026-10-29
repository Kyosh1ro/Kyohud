"""Crew composition -- hud/crew.lua: mount/update/verify/destroy for 3 crew cards (RED tracer).

Three tests for proposed real crew.lua at kyohud.hud.crew.
Runtime foundation (real mounted root), actors source (real roster via preferred
import), validated crew fixtures. No production actor method replacement.

Interface under test:
  kyohud.hud.crew singleton module
    mount(manager), unmount(manager), update(manager, t, dt),
    refresh_settings(manager), on_heist_start(manager), destroy(manager)
    _root, _cards[1..3], _render_verified, _verify_render()

Budget: 280x120 per card, gap 12, bottom reserve 200. Up to 3 cards.
Sources: real actors:get_crew_snapshot() only; no fabricated metrics.
Actors must not be reset by crew toggle.

RED: lua/hud/crew.lua does not exist yet. Tests that need it fail with
assertTrue(path.exists()), not FileNotFoundError.
"""
from pathlib import Path
import sys
import unittest

from lupa.luajit21 import LuaRuntime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hud_player import STUBS as _PLAYER_STUBS
from test_hud_actors_crew import (
    NATIVE_CRIMINALS_FIXTURE,
    NATIVE_SESSION_FIXTURE,
    NATIVE_LOCALIZATION_FIXTURE,
)
from test_hud_actors import (
    NATIVE_HEALTH_ARMOR_FIXTURE,
    NATIVE_REVIVES_CONDITION_FIXTURE,
)

ROOT = Path(__file__).resolve().parents[1]
CREW_PATH = ROOT / "lua" / "hud" / "crew.lua"
LAYOUT_PATH = ROOT / "lua" / "hud" / "layout.lua"
NATIVE_VIS_PATH = ROOT / "lua" / "hud" / "native_visibility.lua"
RUNTIME_PATH = ROOT / "lua" / "hud" / "runtime.lua"
ACTORS_PATH = ROOT / "lua" / "hud" / "actors.lua"
GAUGE_PATH = ROOT / "lua" / "hud" / "components" / "gauge.lua"
PLAYER_PATH = ROOT / "lua" / "hud" / "player.lua"
CREW_CARD_PATH = ROOT / "lua" / "hud" / "components" / "crew_card.lua"

COLOR_AUGMENT = r'''
local _OrigColor = Color
Color = function(arg1, arg2, arg3, arg4)
    if arg4 == nil then
        return { r = arg1 or 0, g = arg2 or 0, b = arg3 or 0, a = 1 }
    else
        return { r = arg2 or 0, g = arg3 or 0, b = arg4 or 0, a = arg1 or 1 }
    end
end
local _mt = getmetatable(_G.panel_double)
function _mt.__index:color() return self._color end
function _mt.__index:alpha() return self._alpha or (self._color and self._color.a) or 1 end
function _mt.__index:font() return self._font or 'fonts/font_medium_mf' end
function _mt.__index:set_font(font) self._font=font end
function _mt.__index:text_rect()
    local n=0
    for byte in self:text():gmatch('.') do if byte:byte()<128 or byte:byte()>=192 then n=n+1 end end
    return 0,0,n*self:font_size()*.45,self:font_size()
end
function _mt.__index:set_alpha(a)
    self._alpha=a
    if self._color then self._color.a = a
    else self._color = Color(a, 0, 0, 0) end
end
local _orig_set_color = _mt.__index.set_color
function _mt.__index:set_color(c)
    if _orig_set_color then _orig_set_color(self, c) end
    if c and c.a then self._color = Color(c.a, c.r, c.g, c.b)
    else self._color = c end
end
'''

STUBS = _PLAYER_STUBS + "\n" + COLOR_AUGMENT + r'''
if kyohud.settings.enable_crew == nil then
    kyohud.settings.enable_crew = false
end
'''

ROSTER_SETUP = (
    NATIVE_HEALTH_ARMOR_FIXTURE
    + NATIVE_REVIVES_CONDITION_FIXTURE
    + NATIVE_CRIMINALS_FIXTURE
    + NATIVE_SESSION_FIXTURE
    + NATIVE_LOCALIZATION_FIXTURE
    + r'''
local Peer = getmetatable(managers.network:session():local_peer())
local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
local Session = getmetatable(managers.network:session())
local session = Session:new(local_peer)
session:_register_peer(local_peer)
managers.network._session = session

local remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
session:_register_peer(remote_peer)

managers.criminals:_set_character(1, {
    name = "american", taken = true, unit = nil,
    peer_id = 1, data = {ai = false, panel_id = 4},
})
managers.criminals:_set_character(2, {
    name = "spanish", taken = true, unit = nil,
    peer_id = 2, data = {ai = false, panel_id = 2},
})
managers.criminals:_set_character(3, {
    name = "russian", taken = true, unit = nil,
    peer_id = nil, data = {ai = true, panel_id = 1},
})
managers.criminals:_set_character(4, {
    name = "german", taken = true, unit = nil,
    peer_id = nil, data = {ai = true, panel_id = 3},
})

local mgr = managers.hud
mgr._teammate_panels = {}
mgr._teammate_panels[1] = {_peer_id = nil, _ai = true}
mgr._teammate_panels[2] = {_peer_id = 2, _ai = false}
mgr._teammate_panels[3] = {_peer_id = nil, _ai = true}
mgr._teammate_panels[4] = {_peer_id = nil, _ai = false}
mgr._hud = mgr._hud or {}
mgr._hud.teammate_panels_data = {}
for i = 1, 4 do
    mgr._hud.teammate_panels_data[i] = {taken = true}
end
mgr._safe_script = {panel = _G.panel_double}

local damage = {
    _health = 50, _health_max = 100, _armor = 25, _armor_max = 50, _revives = 1,
    get_real_health = function(self) return self._health end,
    _max_health = function(self) return self._health_max end,
    get_real_armor = function(self) return self._armor end,
    _max_armor = function(self) return self._armor_max end,
    get_revives = function(self) return self._revives end,
}
local unit = {
    _alive = true,
    character_damage = function(self) return damage end,
}
managers.player = managers.player or {}
managers.player.player_unit = function(self) return unit end
'''
)

_PROD_PATHS = (
    LAYOUT_PATH,
    NATIVE_VIS_PATH,
    RUNTIME_PATH,
    ACTORS_PATH,
    GAUGE_PATH,
    PLAYER_PATH,
    CREW_CARD_PATH,
)


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua(setup=None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute(ROSTER_SETUP)
    if setup:
        lua.execute(setup)
    for path in _PROD_PATHS:
        src = _read(path)
        if src:
            lua.execute(src)
    crew_src = _read(CREW_PATH)
    exists = crew_src is not None
    if exists:
        lua.execute(crew_src)
    return lua, exists


class CrewFileExistsTests(unittest.TestCase):
    def test_crew_chunk_exists(self):
        self.assertTrue(CREW_PATH.is_file(),
            "RED: lua/hud/crew.lua must exist")


class CrewMountLayoutAndSourceTests(unittest.TestCase):
    def test_mount_three_actors_stable_positions_sources_unknown_and_toggle(self):
        """Three roster actors via real refresh_crew; mount/update at 1920x1080.
        Budget 280x120, gap 12, bottom 200. Stable positions with holes.
        Repeated updates preserve primitive refs. Sources UNKNOWN not fake.
        Toggle crew false hides/removes only own visuals, no actors reset.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/crew.lua must exist")
        if not ok:
            return
        lua.execute(r'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_crew = true
            kyohud.settings.hud_scale = 1.0
            _G.panel_double:set_shape(0, 0, 1920, 1080)

            local mgr = managers.hud
            local ACT = kyohud.hud.actors
            ACT:refresh_crew(mgr, 0)
            local snap = ACT:get_crew_snapshot()
            _snap_len = #snap

            local C = kyohud.hud.crew
            assert(C and type(C.mount) == "function", "RED: crew.mount must exist")
            kyohud.hud.runtime:mount(mgr)
            C:mount(mgr)
            _root_alive = alive(C._root)
            _root_parent_is_rt = C._root and C._root:parent() == kyohud.hud.runtime._root_panel

            _card_count = 0
            if C._cards then
                for _ in pairs(C._cards) do _card_count = _card_count + 1 end
            end

            C:update(mgr, 1.0, 0.05)
            _ok_after_update = C:_verify_render()

            _card_roots = {}
            _card_name_texts = {}
            for i = 1, 3 do
                if C._cards[i] then
                    _card_roots[i] = C._cards[i].root or C._cards[i]._root
                    if C._cards[i]._name_text then
                        _card_name_texts[i] = C._cards[i]._name_text
                    end
                end
            end

            for _ = 1, 5 do
                C:update(mgr, 1.5, 0.05)
            end
            _same_refs = true
            for i = 1, 3 do
                if C._cards[i] then
                    local r = C._cards[i].root or C._cards[i]._root
                    if r ~= _card_roots[i] then _same_refs = false end
                    if C._cards[i]._name_text and _card_name_texts[i] then
                        if C._cards[i]._name_text ~= _card_name_texts[i] then
                            _same_refs = false
                        end
                    end
                end
            end

            _pos1_x = nil; _pos2_x = nil; _pos3_x = nil
            _pos1_y = nil
            for i = 1, 3 do
                if C._cards[i] then
                    local r = C._cards[i].root or C._cards[i]._root
                    if r then
                        if i == 1 then _pos1_x = r:x(); _pos1_y = r:y() end
                        if i == 2 then _pos2_x = r:x() end
                        if i == 3 then _pos3_x = r:x() end
                    end
                end
            end

            _has_unknown_source = false
            for i = 1, _snap_len do
                local e = snap[i]
                if e and e.health == nil then _has_unknown_source = true end
            end

            local old_actors_snap = ACT:get_crew_snapshot()
            _old_actors_len = #old_actors_snap

            kyohud.settings.enable_crew = false
            C:refresh_settings(mgr)
            _root_after_toggle = C._root
            _root_visible_after_toggle = nil
            if C._root and alive(C._root) then
                _root_visible_after_toggle = C._root:visible()
            end

            local new_actors_snap = ACT:get_crew_snapshot()
            _new_actors_len = #new_actors_snap
        ''')
        g = lua.globals()
        self.assertEqual(float(g._snap_len), 3.0,
            "RED: crew snapshot must have 3 non-local occupants")
        self.assertTrue(bool(g._root_alive),
            "RED: crew root must be alive after mount")
        self.assertTrue(bool(g._root_parent_is_rt),
            "RED: crew root parent must be runtime._root_panel")
        self.assertEqual(float(g._card_count), 3.0,
            "RED: crew must have 3 cards for 3 roster occupants")
        self.assertTrue(bool(g._ok_after_update),
            "RED: _verify_render must pass after update")
        self.assertTrue(bool(g._same_refs),
            "RED: repeated updates must preserve primitive references")
        self.assertIsNotNone(g._pos1_x, "RED: card 1 must have position")
        self.assertIsNotNone(g._pos2_x, "RED: card 2 must have position")
        self.assertIsNotNone(g._pos3_x, "RED: card 3 must have position")
        self.assertLess(float(g._pos1_x), float(g._pos2_x),
            "RED: card positions must be ordered left to right")
        self.assertLess(float(g._pos2_x), float(g._pos3_x),
            "RED: card positions must be ordered left to right")
        gap_12 = float(g._pos2_x) - float(g._pos1_x) - 280.0
        self.assertAlmostEqual(gap_12, 12.0, places=1,
            msg="RED: gap between cards must be 12")
        self.assertTrue(bool(g._has_unknown_source),
            "RED: at least one crew member must have unknown health (no posthook dispatch)")
        self.assertEqual(float(g._old_actors_len), float(g._new_actors_len),
            "RED: toggle crew false must not reset actors roster")
        self.assertFalse(bool(g._root_visible_after_toggle),
            "RED: toggle crew false must hide or remove own root")


class CrewLayoutParentsAndDriftTests(unittest.TestCase):
    def test_layout_parents_no_overlap_aba_drift_and_tiny_budget(self):
        """Layout parents 1280x1024/958x748/1920x1080 at scales .95/1/1.05.
        No overlap player using actual _compute_layout. A-B-A no drift.
        Invalid tiny budget only owned hidden.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/crew.lua must exist")
        if not ok:
            return
        lua.execute(r'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            kyohud.settings.enable_crew = true
            local mgr = managers.hud
            local ACT = kyohud.hud.actors
            ACT:refresh_crew(mgr, 0)

            local C = kyohud.hud.crew
            local P = kyohud.hud.player
            kyohud.hud.runtime:mount(mgr)
            C:mount(mgr)
            P:mount(mgr)

            _no_overlap_count = 0
            _total_combos = 0
            local sizes = {{1280, 1024}, {958, 748}, {1920, 1080}}
            local scales = {0.95, 1.0, 1.05}
            for _, size in ipairs(sizes) do
                for _, scale in ipairs(scales) do
                    _G.panel_double:set_shape(0, 0, size[1], size[2])
                    kyohud.settings.hud_scale = scale
                    mgr:resolution_changed()
                    kyohud.hud.runtime:_do_refresh()
                    C:refresh_settings(mgr)
                    P:refresh_settings(mgr)
                    if C._root and alive(C._root) and C._root:visible() then
                        _total_combos = _total_combos + 1
                        local p = P:_compute_layout(size[1], size[2])
                        if p then
                            local cr = C._root
                            local crew_right = cr:x() + cr:w()
                            local crew_bottom = cr:y() + cr:h()
                            local no_h_overlap = (crew_right <= p.x) or (cr:x() >= p.x + p.w)
                            local no_v_overlap = (crew_bottom <= p.y) or (cr:y() >= p.y + p.h)
                            if no_h_overlap or no_v_overlap then
                                _no_overlap_count = _no_overlap_count + 1
                            end
                        end
                    end
                end
            end

            _G.panel_double:set_shape(0, 0, 1920, 1080)
            kyohud.settings.hud_scale = 1.0
            mgr:resolution_changed()
            C:refresh_settings(mgr)
            _aba_pos1_x = nil
            kyohud.hud.runtime:_do_refresh()
            C:refresh_settings(mgr)
            if C._cards and C._cards[1] then
                local r = C._cards[1].root or C._cards[1]._root
                if r then _aba_pos1_x = r:x() end
            end

            kyohud.settings.enable_crew = false
            C:refresh_settings(mgr)
            kyohud.settings.enable_crew = true
            C:refresh_settings(mgr)
            _aba_pos1_x_after = nil
            if C._cards and C._cards[1] then
                local r = C._cards[1].root or C._cards[1]._root
                if r then _aba_pos1_x_after = r:x() end
            end
            _aba_no_drift = (_aba_pos1_x == _aba_pos1_x_after)

            _G.panel_double:set_shape(0, 0, 100, 50)
            kyohud.settings.hud_scale = 1.0
            mgr:resolution_changed()
            C:refresh_settings(mgr)
            _tiny_root_hidden = false
            kyohud.hud.runtime:_do_refresh()
            C:refresh_settings(mgr)
            if C._root then
                if not alive(C._root) then
                    _tiny_root_hidden = true
                elseif not C._root:visible() then
                    _tiny_root_hidden = true
                end
            else
                _tiny_root_hidden = true
            end

            local sibling = _G.panel_double:panel({name="crew_sibling_test"})
            sibling:set_shape(13, 14, 15, 16)
            sibling:set_visible(true)
            _sibling_alive_after = alive(sibling)
            _sibling_x = sibling:x()
            _sibling_w = sibling:w()
            _sibling_vis = sibling:visible()
        ''')
        g = lua.globals()
        self.assertEqual(float(g._total_combos), 9,
            "all nine layout combinations must render")
        self.assertEqual(float(g._no_overlap_count), float(g._total_combos),
            "RED: crew must not overlap player region in any size/scale combo")
        self.assertTrue(bool(g._aba_no_drift),
            "RED: A-B-A toggle must not drift card positions")
        self.assertTrue(bool(g._tiny_root_hidden),
            "RED: tiny budget must hide or remove only owned crew root")
        self.assertTrue(bool(g._sibling_alive_after),
            "RED: sibling must survive tiny budget")
        self.assertEqual(float(g._sibling_x), 13.0)
        self.assertEqual(float(g._sibling_w), 15.0)
        self.assertTrue(bool(g._sibling_vis))


class CrewDeadRootDestroyTests(unittest.TestCase):
    def test_dead_root_destroy_no_dead_methods_sibling_unchanged(self):
        """Dead root: destroy must not call dead-object methods. Sibling unchanged."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/crew.lua must exist")
        if not ok:
            return
        lua.execute(r'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_crew = true
            kyohud.settings.hud_scale = 1.0
            _G.panel_double:set_shape(0, 0, 1920, 1080)

            local mgr = managers.hud
            local ACT = kyohud.hud.actors
            ACT:refresh_crew(mgr, 0)

            local C = kyohud.hud.crew
            C:mount(mgr)
            C:update(mgr, 1.0, 0.05)
            kyohud.hud.runtime:mount(mgr)
            C:mount(mgr)
            C:update(mgr, 1.1, 0.05)

            local sibling = _G.panel_double:panel({name="crew_dead_sibling"})
            sibling:set_shape(50, 60, 70, 80)
            sibling:set_visible(true)
            _sib_x_before = sibling:x()
            _sib_vis_before = sibling:visible()

            local own_root = C._root
            if own_root then
                own_root._alive = false
            end

            _destroy_ok = pcall(function() C:destroy(mgr) end)

            _sib_x_after = sibling:x()
            _sib_vis_after = sibling:visible()
            _sib_alive_after = alive(sibling)

            _double_destroy_ok = pcall(function() C:destroy(mgr) end)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._destroy_ok),
            "RED: destroy on dead root must not error")
        self.assertEqual(float(g._sib_x_after), float(g._sib_x_before),
            "RED: sibling x must be unchanged after dead root destroy")
        self.assertEqual(bool(g._sib_vis_after), bool(g._sib_vis_before),
            "RED: sibling visibility must be unchanged after dead root destroy")
        self.assertTrue(bool(g._sib_alive_after),
            "RED: sibling must remain alive after dead root destroy")
        self.assertTrue(bool(g._double_destroy_ok),
            "RED: double destroy must not error")


if __name__ == "__main__":
    unittest.main()
