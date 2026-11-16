"""Mission common-reference contract.

RED: with Objectives enabled, native objectives_panel installed directly under
the real shared script parent (runtime._parent_panel), the conflict walk must
stay at that shared reference. Reading common.parent is forbidden, even when a
20-ancestor chain (and a self-parent at its top) exists above it. Mission must
stay verified, retain its primitives, and keep y=36. The same fixture then
drives compact fault/recovery and permissive cases.

The fixture primitives ignore constructor visibility for text, so every hidden
text leaf is hidden through its real set_visible method.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_mission import _lua
from test_hud_mission_fixed_anchor import INSTALL_PARENT_LINKS
from test_hud_mission_phase_probe import INSTALL_DISPATCH, MOUNT_CERTIFY

SETUP = r'''
local RT = kyohud.hud.runtime
local M = kyohud.hud.mission
local mgr = managers.hud
_G._common = RT._parent_panel
_G._mgr = mgr

local panel = _G._common:panel({
    name = "objectives_panel", x = 0, y = 0, w = 500, h = 100,
})
panel:set_shape(0, 0, 500, 100)
panel:set_visible(true)
panel:set_alpha(1)

local title = panel:text({
    name = "objective_text", x = 1000, y = 36, w = 180, h = 30,
    text = "Native objective",
})
title:set_visible(true)
title:set_alpha(1)

local amount = panel:text({
    name = "amount_text", x = 34, y = 60, w = 180, h = 20,
    text = "0/3",
})
amount:set_visible(false)
amount:set_alpha(1)

local box = panel:panel({
    name = "bg_box", x = 0, y = 0, w = 500, h = 100,
})
box:set_shape(0, 0, 500, 100)
box:set_visible(false)
box:set_alpha(1)

_G._native_panel = panel
_G._native_title = title
_G._native_amount = amount
_G._native_box = box
_G._native_timer = mgr._hud_heist_timer._timer_text
_G._owned = {
    root = M._root_panel,
    timer = M._timer_prim,
    title = M._title_prim,
    bags = M._bags_prim,
    bags_label = M._bags_label_prim,
    bg_timer = (M._backgrounds or {}).timer,
    bg_title = (M._backgrounds or {}).title,
    bg_bags = (M._backgrounds or {}).bags,
}

_G._source_uses_common = rawequal(panel:parent(), _G._common)
_G._panel_parents_common = rawequal(panel:parent(), RT._parent_panel)
_G._native_title_text = title:text()
_G._native_title_visible = title:visible()
_G._native_amount_hidden = amount:visible() == false
_G._native_box_hidden = box:visible() == false
_G._source = {_hud_panel = _G._common, _bg_box = box}
mgr._hud_objectives = _G._source

_G._snapshot = function()
    local m = kyohud.hud.mission
    local o = _G._owned
    local bgs = m._backgrounds or {}
    return {
        verified = m._render_verified == true,
        failed = m._render_failed == true,
        root_visible = m._root_panel and m._root_panel:visible() == true,
        x = m._root_panel and m._root_panel:x() or -1,
        y = m._root_panel and m._root_panel:y() or -1,
        same = rawequal(m._root_panel, o.root)
            and rawequal(m._timer_prim, o.timer)
            and rawequal(m._title_prim, o.title)
            and rawequal(m._bags_prim, o.bags)
            and rawequal(m._bags_label_prim, o.bags_label)
            and rawequal(bgs.timer, o.bg_timer)
            and rawequal(bgs.title, o.bg_title)
            and rawequal(bgs.bags, o.bg_bags),
        native_alpha = _G._native_timer:alpha(),
    }
end

_G._feed = function(count)
    for _ = 1, (count or 1) do
        _G._dispatch_feed(125)
    end
    return _G._snapshot()
end
'''

FAULTS_AND_PERMISSIVE = r'''
local title = _G._native_title
local saved_parent = title.parent

title:set_visible(true)
title:set_alpha(1)
title:set_text("Native objective")
title:set_shape(1000, 36, 180, 30)

title.parent = function() error("leaf parent fault") end
_G._fault_parent = _G._feed(1)
title.parent = saved_parent
_G._recover_parent = _G._feed(2)

title:set_shape(0/0, 36, 180, 30)
_G._fault_nan_x = _G._feed(1)
title:set_shape(1000, 36, 180, 30)
_G._recover_nan_x = _G._feed(2)

title:set_alpha(0/0)
_G._fault_nan_alpha = _G._feed(1)
title:set_alpha(1)
_G._recover_nan_alpha = _G._feed(2)

local foreign = _make_panel("foreign_objective_root")
foreign:set_shape(0, 0, 500, 100)
foreign:set_visible(true)
foreign:set_alpha(1)
title.parent = function() return foreign end
_G._fault_foreign = _G._feed(1)
title.parent = saved_parent
_G._recover_foreign = _G._feed(2)

title:set_text("")
_G._permit_empty = _G._feed(1)
title:set_text("Native objective")
title:set_alpha(0)
_G._permit_transparent = _G._feed(1)
title:set_alpha(1)
title:set_visible(false)
_G._permit_hidden = _G._feed(1)
title:set_visible(true)
title:set_shape(1000, 36, 180, 30)
_G._permit_disjoint = _G._feed(1)
'''

COMMON_REFERENCE = r'''
local common = _G._common
local previous = common
local ancestors = {}
for i = 1, 20 do
    local ancestor = _make_panel("shared_ancestor_" .. i)
    ancestor:set_shape(0, 0, 1920, 1080)
    ancestor:set_visible(true)
    ancestor:set_alpha(1)
    previous._fixture_parent = ancestor
    ancestors[i] = ancestor
    previous = ancestor
end
previous._fixture_parent = previous
_G._ancestor_count = #ancestors

_G._common_parent_calls = 0
common.parent = function(self)
    _G._common_parent_calls = _G._common_parent_calls + 1
    error("common.parent must never be called")
end

_G._reference = _G._feed(2)
_G._reference_common_calls = _G._common_parent_calls

local M = kyohud.hud.mission
local title = _G._native_title
title:set_visible(true)
title:set_alpha(1)
title:set_text("Native objective")
title:set_shape(M._root_panel:x(), M._root_panel:y(), 180, 30)
_G._overlap = _G._feed(1)
_G._overlap_common_calls = _G._common_parent_calls

title:set_shape(1000, 36, 180, 30)
_G._recovery = _G._feed(2)
_G._recovery_common_calls = _G._common_parent_calls
'''


class MissionCommonReferenceTests(unittest.TestCase):
    def _assert_healthy(self, snap, label):
        self.assertIs(snap.verified, True, f"{label}: Mission must verify")
        self.assertIs(snap.failed, False,
                      f"{label}: Mission must not stay failed")
        self.assertIs(snap.root_visible, True,
                      f"{label}: owned Mission root must stay visible")
        self.assertEqual(snap.x, 40, f"{label}: fixed anchor x must be 40")
        self.assertEqual(snap.y, 36, f"{label}: fixed anchor y must be 36")
        self.assertIs(snap.same, True,
                      f"{label}: owned primitives must be retained")
        self.assertEqual(snap.native_alpha, 0,
                         f"{label}: native timer alpha must stay 0")

    def _assert_conflict(self, snap, label):
        self.assertIs(snap.verified, False,
                      f"{label}: Mission must fail closed")
        self.assertIs(snap.failed, True,
                      f"{label}: Mission must enter render_failed")
        self.assertIs(snap.root_visible, False,
                      f"{label}: owned Mission root must be hidden")
        self.assertIs(snap.same, True,
                      f"{label}: conflict must retain owned primitives")
        self.assertEqual(snap.native_alpha, 1,
                         f"{label}: native timer alpha must be restored to 1")

    def test_common_reference_contract(self):
        lua, ok = _lua()
        self.assertTrue(ok, "lua/hud/mission.lua must exist")

        lua.execute(INSTALL_PARENT_LINKS)
        lua.execute("kyohud.settings.enable_objectives = true")
        lua.execute(INSTALL_DISPATCH)
        lua.execute(MOUNT_CERTIFY)
        lua.execute(SETUP)

        g = lua.globals()
        self.assertIs(g._cert_verified, True,
                      "positive baseline: mounted Mission must certify")
        self.assertIs(g._source_uses_common, True,
                      "native objectives_panel must sit directly on the shared "
                      "runtime._parent_panel")
        self.assertIs(g._panel_parents_common, True,
                      "script parent must stay the real shared handle")
        self.assertEqual(g._native_title_text, "Native objective",
                         "native title must stay nonempty")
        self.assertIs(g._native_title_visible, True,
                      "native title must be explicitly visible")
        self.assertIs(g._native_amount_hidden, True,
                      "native amount must be explicitly hidden")
        self.assertIs(g._native_box_hidden, True,
                      "native bg_box must be explicitly hidden")

        lua.execute(FAULTS_AND_PERMISSIVE)
        g = lua.globals()
        for prefix, label in (
            ("_fault_parent", "throwing leaf parent"),
            ("_fault_nan_x", "NaN leaf x"),
            ("_fault_nan_alpha", "NaN leaf alpha"),
            ("_fault_foreign", "foreign leaf ancestry"),
        ):
            self._assert_conflict(getattr(g, prefix), label)
            self._assert_healthy(getattr(g, prefix.replace("fault", "recover")),
                                 label + " recovery")
        for name in ("_permit_empty", "_permit_transparent",
                     "_permit_hidden", "_permit_disjoint"):
            self._assert_healthy(getattr(g, name), name)

        lua.execute(COMMON_REFERENCE)
        g = lua.globals()
        self.assertEqual(g._ancestor_count, 20,
                         "the shared script parent must carry 20 ancestors")
        self.assertEqual(g._reference_common_calls, 0,
                         "RED: common.parent must never be called above the "
                         "shared script reference")
        self._assert_healthy(g._reference,
                             "shared reference with 20 ancestors")
        self.assertEqual(g._overlap_common_calls, 0,
                         "RED: common.parent must not be called during overlap")
        self._assert_conflict(g._overlap, "actual native overlap")
        self.assertEqual(g._recovery_common_calls, 0,
                         "RED: common.parent must not be called during recovery")
        self._assert_healthy(g._recovery, "disjoint recovery")


if __name__ == "__main__":
    unittest.main()
