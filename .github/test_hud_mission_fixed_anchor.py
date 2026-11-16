"""Mission fixed anchor: the owned row stays at the empty-startup position.

Scope: one minimal slice. The real mission/runtime chunks and HUDManager timer
fixture are reused through test_hud_mission._lua; INSTALL_DISPATCH and
MOUNT_CERTIFY come from the real phase probe. enable_objectives is set BEFORE
MOUNT_CERTIFY, whose constant only enables the foundation and mission.

No native objectives source exists in this fixture, so source absence is the
clear empty startup: the owned root must be anchored at x=40, y=36 for
1920x1080 at scale 1, not at the legacy y=100 native reservation. The current
production code yields y=136 here; that is the intended RED.

The runtime presentation handshake is then driven for real through
set_objectives_covered(true), false, true, with the registered
_dispatch_feed(125) between flips. The anchor must never drop lower than y=36,
x must stay 40, _render_verified must be true after each flip, and the root,
text and background primitives must keep their identity (no recreation).
Native conflict/recovery belongs to a separate subsequent slice.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_mission import _lua
from test_hud_mission_phase_probe import INSTALL_DISPATCH, MOUNT_CERTIFY

INSTALL_PARENT_LINKS = r'''
local make_panel = _make_panel
function _make_panel(name)
    local p = make_panel(name)
    function p:parent() return self._fixture_parent end
    local panel, text = p.panel, p.text
    function p:panel(opts)
        local child = panel(self, opts)
        child._fixture_parent = self
        return child
    end
    function p:text(opts)
        local child = text(self, opts)
        child._fixture_parent = self
        self._children[opts.name] = child
        return child
    end
    return p
end
'''

CAPTURE = r'''
local M = kyohud.hud.mission
local bgs = M._backgrounds or {}
_G._root = M._root_panel
_G._root_x = M._root_panel:x()
_G._root_y = M._root_panel:y()
_G._timer = M._timer_prim
_G._title = M._title_prim
_G._bags = M._bags_prim
_G._bags_label = M._bags_label_prim
_G._bg_timer = bgs.timer
_G._bg_title = bgs.title
_G._bg_bags = bgs.bags
_G._verified = M._render_verified == true
'''

DRIVE = r'''
local RT = kyohud.hud.runtime
local M = kyohud.hud.mission
local bgs = M._backgrounds or {}

_G._snap = function()
    return {
        x = M._root_panel:x(),
        y = M._root_panel:y(),
        verified = M._render_verified == true,
        same = rawequal(M._root_panel, _G._root)
            and rawequal(M._timer_prim, _G._timer)
            and rawequal(M._title_prim, _G._title)
            and rawequal(M._bags_prim, _G._bags)
            and rawequal(M._bags_label_prim, _G._bags_label)
            and rawequal(bgs.timer, _G._bg_timer)
            and rawequal(bgs.title, _G._bg_title)
            and rawequal(bgs.bags, _G._bg_bags),
    }
end

local function flip(covered)
    RT:set_objectives_covered(covered)
    _G._dispatch_feed(125)
    return _G._snap()
end

_G._after_true = flip(true)
_G._after_false = flip(false)
_G._after_true_again = flip(true)
'''


class MissionFixedAnchorTests(unittest.TestCase):
    def _assert_anchor(self, snap, label):
        self.assertEqual(snap.x, 40, f"{label}: root x must stay 40")
        self.assertEqual(snap.y, 36, f"{label}: root y must stay 36, never lower")
        self.assertIs(snap.verified, True, f"{label}: render must verify")
        self.assertIs(snap.same, True, f"{label}: primitives must not be recreated")

    def test_fixed_anchor_survives_objectives_handshake(self):
        lua, ok = _lua()
        self.assertTrue(ok, "lua/hud/mission.lua must exist")
        if not ok:
            return

        lua.execute(INSTALL_PARENT_LINKS)
        lua.execute("kyohud.settings.enable_objectives = true")
        lua.execute(INSTALL_DISPATCH)
        lua.execute(MOUNT_CERTIFY)
        lua.execute(CAPTURE)

        g = lua.globals()
        self.assertIs(g._verified, True,
                      "positive baseline: mounted mission must render verified")
        for name in ("_root", "_timer", "_title", "_bags", "_bags_label",
                     "_bg_timer", "_bg_title", "_bg_bags"):
            self.assertIsNotNone(getattr(g, name),
                                 f"positive baseline: {name} must exist")
        self.assertEqual(g._root_x, 40,
                         "RED: empty startup root x must be 40, not reserved")
        self.assertEqual(g._root_y, 36,
                         "RED: empty startup root y must be 36, not the legacy "
                         "y=100 native reservation (current code yields 136)")

        lua.execute(DRIVE)
        self._assert_anchor(g._after_true, "objectives covered")
        self._assert_anchor(g._after_false, "objectives uncovered")
        self._assert_anchor(g._after_true_again, "objectives covered again")

    def test_fixed_anchor_native_conflict_then_recovery(self):
        lua, ok = _lua()
        self.assertTrue(ok, "lua/hud/mission.lua must exist")
        if not ok:
            return

        lua.execute(INSTALL_PARENT_LINKS)
        lua.execute("kyohud.settings.enable_objectives = true")
        lua.execute(INSTALL_DISPATCH)
        lua.execute(MOUNT_CERTIFY)
        lua.execute(CAPTURE)

        g = lua.globals()
        self.assertIs(g._verified, True,
                      "positive baseline: mounted mission must render verified")
        self.assertEqual(g._root_x, 40,
                         "positive baseline: fixed anchor x must be 40")
        self.assertEqual(g._root_y, 36,
                         "positive baseline: fixed anchor y must be 36")

        lua.execute(r'''
            local parent = _G._phase_parent:panel({
                name = "native_objectives_parent", w = 1920, h = 1080,
            })
            parent:set_shape(0, 0, 1920, 1080)
            local objectives_panel = parent:panel({
                name = "objectives_panel", w = 500, h = 100,
            })
            objectives_panel:set_shape(0, 0, 500, 100)
            objectives_panel:set_visible(false)
            local title = objectives_panel:text({
                name = "objective_text", x = 40, y = 36, w = 180, h = 30,
                text = "Native objective",
            })
            title:set_visible(true)
            local amount_text = objectives_panel:text({
                name = "amount_text", x = 34, y = 60, w = 180, h = 20,
                text = "",
            })
            amount_text:set_visible(false)
            local bg_box = objectives_panel:panel({
                name = "bg_box", w = 500, h = 100,
            })
            bg_box:set_shape(0, 0, 500, 100)
            bg_box:set_visible(false)
            _G._native_parent = objectives_panel
            _G._phase_mgr._hud_objectives = {
                _hud_panel = parent,
                _bg_box = bg_box,
            }
        ''')

        lua.execute(r'''
            local M = kyohud.hud.mission
            _G._native_parent:set_visible(true)
            _G._dispatch_feed(125)
            _G._conflict_verified = M._render_verified == true
            _G._conflict_failed = M._render_failed == true
            _G._conflict_title_visible = M._title_prim and M._title_prim:visible()
            _G._conflict_alpha = _G._phase_mgr._hud_heist_timer._timer_text:alpha()
            _G._conflict_y = M._root_panel and M._root_panel:y()
        ''')

        g = lua.globals()
        self.assertIs(g._conflict_verified, False,
                      "visible native objective must fail Mission verification")
        self.assertIs(g._conflict_failed, True,
                      "visible native objective must enter render_failed")
        self.assertIs(g._conflict_title_visible, False,
                      "conflict must hide the owned Mission title")
        self.assertEqual(g._conflict_alpha, 1,
                         "conflict must restore native timer alpha to 1")
        self.assertEqual(g._conflict_y, 36,
                         "conflict must not shift the fixed anchor y")

        lua.execute(r'''
            local M = kyohud.hud.mission
            _G._native_parent:set_visible(false)
            _G._dispatch_feed(125)
            _G._dispatch_feed(125)
            _G._recovery_verified = M._render_verified == true
            _G._recovery_failed = M._render_failed == true
            _G._recovery_same = rawequal(M._root_panel, _G._root)
                and rawequal(M._timer_prim, _G._timer)
                and rawequal(M._title_prim, _G._title)
                and rawequal(M._bags_prim, _G._bags)
                and rawequal(M._bags_label_prim, _G._bags_label)
            _G._recovery_alpha = _G._phase_mgr._hud_heist_timer._timer_text:alpha()
            _G._recovery_y = M._root_panel and M._root_panel:y()
        ''')

        g = lua.globals()
        self.assertIs(g._recovery_verified, True,
                      "hidden native source must restore verified Mission render")
        self.assertIs(g._recovery_failed, False,
                      "hidden native source must clear render_failed")
        self.assertIs(g._recovery_same, True,
                      "recovery must keep the same Mission identity")
        self.assertEqual(g._recovery_alpha, 0,
                         "recovery must reacquire native timer alpha 0")
        self.assertEqual(g._recovery_y, 36,
                         "recovery must keep the fixed anchor y")
        lua.execute(r'''
            local M = kyohud.hud.mission
            local p = _native_parent:child("objective_text")
            _native_parent:set_visible(true)
            p:set_shape(1000,36,180,30)
            _dispatch_feed(125)
            assert(M:_verify_render(), "disjoint native content must not hide Mission")
            p:set_shape(40,36,180,30)
            p:set_alpha(0)
            _dispatch_feed(125)
            assert(M:_verify_render(), "transparent native content must not hide Mission")
            p:set_alpha(1)
            p:set_text("")
            _dispatch_feed(125)
            assert(M:_verify_render(), "empty native label must not occupy its panel")
            p:set_text("Native objective")
            p:set_alpha(0/0)
            _dispatch_feed(125)
            assert(not M._render_verified and not M._root_panel:visible(),
                "unreadable native visibility must fail closed without moving Mission")
            p:set_alpha(1)
            _native_parent:set_visible(false)
            _dispatch_feed(125)
            _dispatch_feed(125)
            assert(M:_verify_render() and M._root_panel:visible(), "same-object recovery")
            assert(M._root_panel == _root and M._root_panel:y() == 36, "fixed retained root")
        ''')

    def test_completion_and_successor_keep_single_mission_root(self):
        from test_hud_objectives_visibility import _lua_native_ready
        lua, ok = _lua_native_ready()
        self.assertTrue(ok)
        lua.execute(r'''
            local RT, M, O = kyohud.hud.runtime, kyohud.hud.mission, kyohud.hud.objectives
            kyohud.settings.enable_mission = true
            RT:refresh_settings(managers.hud)
            assert(M:_verify_render(), "positive combined rendering")
            local root, title = M._root_panel, M._title_prim
            local function unchanged()
                assert(M._root_panel == root and M._title_prim == title, "no duplicate/replaced Mission")
                assert(root:y() == 36, "Mission never moves during completion")
                local count = 0
                for _, child in pairs(M._parent_panel._children) do
                    if child == root then count = count + 1 end
                end
                assert(count == 1, "single retained Mission root")
            end
            managers.objectives:complete_objective("collect")
            managers.objectives:complete_objective("collect")
            managers.objectives:complete_objective("collect")
            unchanged()
            for i=1,30 do RT:update(managers.hud, 1.1+i*0.05, 0.05); unchanged() end
            local native = managers.hud._hud_objectives
            local panel = native._hud_panel:child("objectives_panel")
            assert(panel._scheduled_fn, "native completion coroutine must be exercised")
            _run_coroutine(panel)
            unchanged()
            assert(native._bg_box._scheduled_fn, "native close coroutine must be exercised")
            _run_coroutine(native._bg_box)
            unchanged()
            RT:update(managers.hud, 3.2, 0.6)
            unchanged()
            managers.objectives:activate_objective("collect", nil, {amount=3})
            for i=1,12 do RT:update(managers.hud, 3.2+i*0.05, 0.05); unchanged() end
            assert(O._mounted and M._mounted, "both modules retain their lifetime")
        ''')


if __name__ == "__main__":
    unittest.main()
