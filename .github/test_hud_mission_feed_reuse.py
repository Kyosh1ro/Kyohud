"""Mission stable-feed reuse: no relayout, no duplicate label verify, no
duplicate title sync, while per-feed certification stays intact.

Scope: healthy stable Mission feeds. The real mission.lua chunk is reused
through the existing test_hud_mission._lua fixture and mounted/certified with
test_hud_mission_phase_probe.INSTALL_DISPATCH/MOUNT_CERTIFY. Test-local
wrappers count real production method invocations (they forward to the real
methods); the Lua VM is disposable, so no restoration is required unless a
scenario needs it.

RED today, verified by reading lua/hud/mission.lua: every stable feed runs
_sync_primitives, which calls _sync_title_prim twice (lines 1353 and 1359) and
calls _update_layout unconditionally (line 1356). _update_layout always calls
_compute_layout and then _verify_labels inside its changed predicate (line
1469); _verify_render calls _verify_labels once more (line 792). Therefore 10
stable feeds currently produce: _compute_layout = 10, _update_layout = 10,
_verify_labels = 20, _verify_render = 10, _sync_title_prim = 20.

GREEN budget after the production pass: _compute_layout = 0,
_update_layout <= 10 (the call may remain without work; not pinned to 0),
_verify_labels = 10 (only the call inside _verify_render), _verify_render = 10
(per-feed certification preserved), _sync_title_prim = 10.

The measured window is steady state. One warmup feed is dispatched after the
counters are installed and before they are reset: the legitimate fit-based
convergence recomputes/writes the layout once right after certification (the
historical order: title sync before layout, then a conditional title re-sync).
That warmup work is excluded from the budget; the 10 measured feeds must not
recompute the layout. The RED contract today is unchanged: even with the
warmup, the current production still computes the layout on all 10 measured
feeds.

The corruption/repair contract test is GREEN today and must stay GREEN after
the production pass: a corrupted owned primitive is detected by _verify_render
on the following feed, releases the native leaf, and is repaired on the SAME
primitive identities before re-certifying and re-acquiring. The fixture has no
separate retry clock path, so successive real feeds are used exactly as in
test_hud_mission_background_cost.REGRESSION_ROUND.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_mission import _lua
from test_hud_mission_phase_probe import INSTALL_DISPATCH, MOUNT_CERTIFY

INSTRUMENT = r'''
local M = kyohud.hud.mission
_G._work = {
    compute_layout = 0,
    update_layout = 0,
    verify_labels = 0,
    verify_render = 0,
    sync_title_prim = 0,
}
_G._work_original = {
    compute_layout = M._compute_layout,
    update_layout = M._update_layout,
    verify_labels = M._verify_labels,
    verify_render = M._verify_render,
    sync_title_prim = M._sync_title_prim,
}
M._compute_layout = function(self, ...)
    _G._work.compute_layout = _G._work.compute_layout + 1
    return _G._work_original.compute_layout(self, ...)
end
M._update_layout = function(self, ...)
    _G._work.update_layout = _G._work.update_layout + 1
    return _G._work_original.update_layout(self, ...)
end
M._verify_labels = function(self, ...)
    _G._work.verify_labels = _G._work.verify_labels + 1
    return _G._work_original.verify_labels(self, ...)
end
M._verify_render = function(self, ...)
    _G._work.verify_render = _G._work.verify_render + 1
    return _G._work_original.verify_render(self, ...)
end
M._sync_title_prim = function(self, ...)
    _G._work.sync_title_prim = _G._work.sync_title_prim + 1
    return _G._work_original.sync_title_prim(self, ...)
end

_G._work_reset = function()
    for key in pairs(_G._work) do
        _G._work[key] = 0
    end
end
'''

DELIVER_STABLE_TEN = r'''
-- Warmup feed: the legitimate fit-based convergence recomputes/writes the
-- layout once right after certification (historical behaviour). Absorb it
-- before resetting the counters so the measured window is steady state.
_G._dispatch_feed(125)
_G._work_reset()
for _ = 1, 10 do
    _G._dispatch_feed(125)
end
_G._work_compute_layout = _G._work.compute_layout
_G._work_update_layout = _G._work.update_layout
_G._work_verify_labels = _G._work.verify_labels
_G._work_verify_render = _G._work.verify_render
_G._work_sync_title_prim = _G._work.sync_title_prim
'''

RETAIN_STABLE = r'''
local M = kyohud.hud.mission
local mgr = _G._phase_mgr
local native_timer = mgr._hud_heist_timer._timer_text

_G._retain_root_before = M._root_panel
_G._retain_timer_before = M._timer_prim
_G._retain_title_before = M._title_prim
_G._retain_bags_before = M._bags_prim
_G._retain_bags_label_before = M._bags_label_prim
_G._retain_bg_timer_before = M._backgrounds.timer
_G._retain_bg_title_before = M._backgrounds.title
_G._retain_bg_bags_before = M._backgrounds.bags
_G._retain_text_before = M._timer_text
_G._retain_native_alpha_before = native_timer:alpha()

for _ = 1, 10 do
    _G._dispatch_feed(125)
end

_G._retain_root_same = rawequal(M._root_panel, _G._retain_root_before)
_G._retain_timer_same = rawequal(M._timer_prim, _G._retain_timer_before)
_G._retain_title_same = rawequal(M._title_prim, _G._retain_title_before)
_G._retain_bags_same = rawequal(M._bags_prim, _G._retain_bags_before)
_G._retain_bags_label_same = rawequal(M._bags_label_prim, _G._retain_bags_label_before)
_G._retain_bg_timer_same = rawequal(M._backgrounds.timer, _G._retain_bg_timer_before)
_G._retain_bg_title_same = rawequal(M._backgrounds.title, _G._retain_bg_title_before)
_G._retain_bg_bags_same = rawequal(M._backgrounds.bags, _G._retain_bg_bags_before)
_G._retain_text_after = M._timer_text
_G._retain_timer_prim_text_after = M._timer_prim and M._timer_prim:text() or nil
_G._retain_native_alpha_after = native_timer:alpha()
_G._retain_render_verified = M._render_verified == true
_G._retain_native_acquired = M._native_acquired == true
'''

CORRUPTION_ROUND = r'''
local M = kyohud.hud.mission
local mgr = _G._phase_mgr
local native_timer = mgr._hud_heist_timer._timer_text
local kind = _G._reg_kind

local p
if kind == "background_color" or kind == "background_alpha"
    or kind == "background_visible" then
    p = M._backgrounds.title
else
    p = M._title_prim
end

local function current_prim()
    if kind == "background_color" or kind == "background_alpha"
        or kind == "background_visible" then
        return M._backgrounds.title
    end
    return M._title_prim
end

_G._reg_prim = p
_G._reg_root = M._root_panel
_G._reg_native_fixture_alpha = 1
_G._reg_baseline_render = M:_verify_render()
_G._reg_alpha_baseline = p:alpha()

if kind == "background_color" then
    _G._reg_setter = p.set_color
    p:set_color(Color(1, 1, 0, 1))
    p:set_alpha(_G._reg_alpha_baseline)
elseif kind == "background_alpha" then
    _G._reg_setter = p.set_alpha
    p:set_alpha(0)
elseif kind == "background_visible" then
    _G._reg_setter = p.set_visible
    p:set_visible(false)
elseif kind == "title_shape" then
    _G._reg_setter = p.set_shape
    p:set_shape(1, 1, 1, 1)
elseif kind == "title_text" then
    _G._reg_setter = p.set_text
    p:set_text("CORRUPTED TITLE")
end

_G._reg_corrupted_render = M:_verify_render()

if kind == "background_color" then
    p.set_color = function(self, c) end
elseif kind == "background_alpha" then
    p.set_alpha = function(self, a) end
elseif kind == "background_visible" then
    p.set_visible = function(self, v) end
elseif kind == "title_shape" then
    p.set_shape = function(self, x, y, w, h) end
elseif kind == "title_text" then
    p.set_text = function(self, s) end
end

_G._dispatch_feed(125)

_G._reg_failed_render_verified = M._render_verified == true
_G._reg_failed_render_failed = M._render_failed == true
_G._reg_failed_native_acquired = M._native_acquired == true
_G._reg_failed_native_alpha = native_timer:alpha()
_G._reg_failed_prim_same = rawequal(current_prim(), p)
_G._reg_failed_root_same = rawequal(M._root_panel, _G._reg_root)

if kind == "background_color" then
    p.set_color = _G._reg_setter
elseif kind == "background_alpha" then
    p.set_alpha = _G._reg_setter
elseif kind == "background_visible" then
    p.set_visible = _G._reg_setter
elseif kind == "title_shape" then
    p.set_shape = _G._reg_setter
elseif kind == "title_text" then
    p.set_text = _G._reg_setter
end

_G._dispatch_feed(125)
_G._dispatch_feed(125)

_G._reg_recovered_render = M:_verify_render()
_G._reg_recovered_render_verified = M._render_verified == true
_G._reg_recovered_render_failed = M._render_failed == true
_G._reg_recovered_prim_same = rawequal(current_prim(), _G._reg_prim)
_G._reg_recovered_root_same = rawequal(M._root_panel, _G._reg_root)
_G._reg_recovered_native_acquired = M._native_acquired == true
_G._reg_recovered_native_alpha = native_timer:alpha()
'''


class MissionFeedReuseTests(unittest.TestCase):
    def _mount_and_certify(self, lua):
        lua.execute(INSTALL_DISPATCH)
        lua.execute(MOUNT_CERTIFY)

        g = lua.globals()
        self.assertEqual(g._feed_hook_count, 1,
                         "fixture must expose exactly one registered "
                         "HUDManager:feed_heist_time callback")
        self.assertIs(g._cert_mounted, True,
                      "positive baseline: mission must be mounted")
        self.assertIs(g._cert_root, True,
                      "positive baseline: mission must own a root panel")
        self.assertIs(g._cert_verified, True,
                      "positive baseline: mission render must be certified")
        self.assertIs(g._cert_timer_prim, True,
                      "positive baseline: mission must own a timer primitive")
        self.assertEqual(g._cert_timer_text, "02:05",
                         "positive baseline: real feed hook must capture 02:05")
        self.assertIs(g._cert_native_acquired, True,
                      "positive baseline: mission must acquire the native timer")
        self.assertEqual(g._cert_native_alpha, 0,
                         "positive baseline: acquired native timer alpha must be 0")

    def test_stable_feed_skips_layout_and_duplicate_label_verify(self):
        lua, ok = _lua()
        self.assertTrue(ok, "lua/hud/mission.lua must exist")
        if not ok:
            return

        self._mount_and_certify(lua)
        lua.execute(INSTRUMENT)
        lua.execute(DELIVER_STABLE_TEN)
        g = lua.globals()

        self.assertEqual(
            g._work_compute_layout, 0,
            "RED: 10 stable feeds must not allocate a new layout "
            f"(observed {g._work_compute_layout}; today 10: line 1456 always "
            "calls _compute_layout)",
        )
        self.assertLessEqual(
            g._work_update_layout, 10,
            "10 stable feeds may call _update_layout at most once per feed "
            f"(observed {g._work_update_layout})",
        )
        self.assertEqual(
            g._work_verify_labels, 10,
            "RED: 10 stable feeds must verify labels exactly once per feed, "
            "inside _verify_render "
            f"(observed {g._work_verify_labels}; today 20: line 1469 adds a "
            "second call inside _update_layout's changed predicate)",
        )
        self.assertEqual(
            g._work_verify_render, 10,
            "per-feed certification must stay intact: one _verify_render per "
            f"stable feed (observed {g._work_verify_render})",
        )
        self.assertEqual(
            g._work_sync_title_prim, 10,
            "RED: 10 stable feeds must sync the title primitive once per feed "
            f"(observed {g._work_sync_title_prim}; today 20: lines 1353 and "
            "1359 both call _sync_title_prim)",
        )

    def test_stable_feed_keeps_primitives_and_native_alpha(self):
        lua, ok = _lua()
        self.assertTrue(ok, "lua/hud/mission.lua must exist")
        if not ok:
            return

        self._mount_and_certify(lua)
        lua.execute(RETAIN_STABLE)
        g = lua.globals()

        self.assertIs(g._retain_root_same, True,
                      "stable feeds must keep the owned root identity")
        self.assertIs(g._retain_timer_same, True,
                      "stable feeds must keep the owned timer identity")
        self.assertIs(g._retain_title_same, True,
                      "stable feeds must keep the owned title identity")
        self.assertIs(g._retain_bags_same, True,
                      "stable feeds must keep the owned bags identity")
        self.assertIs(g._retain_bags_label_same, True,
                      "stable feeds must keep the owned bags label identity")
        self.assertIs(g._retain_bg_timer_same, True,
                      "stable feeds must keep the timer background identity")
        self.assertIs(g._retain_bg_title_same, True,
                      "stable feeds must keep the title background identity")
        self.assertIs(g._retain_bg_bags_same, True,
                      "stable feeds must keep the bags background identity")
        self.assertEqual(g._retain_text_before, "02:05",
                         "baseline timer text must be 02:05")
        self.assertEqual(g._retain_text_after, "02:05",
                         "stable feeds must keep the captured timer text 02:05")
        self.assertEqual(g._retain_timer_prim_text_after, "02:05",
                         "stable feeds must keep the owned timer primitive text 02:05")
        self.assertEqual(g._retain_native_alpha_before, 0,
                         "baseline acquired native timer alpha must be 0")
        self.assertEqual(g._retain_native_alpha_after, 0,
                         "stable feeds must keep the acquired native timer alpha 0")
        self.assertIs(g._retain_render_verified, True,
                      "stable feeds must keep the render certified")
        self.assertIs(g._retain_native_acquired, True,
                      "stable feeds must keep the native leaf acquired")

    def test_corrupted_owned_primitive_repairs_on_same_identity(self):
        for kind in (
            "background_color",
            "background_alpha",
            "background_visible",
            "title_shape",
            "title_text",
        ):
            with self.subTest(corruption=kind):
                lua, ok = _lua()
                self.assertTrue(ok, "lua/hud/mission.lua must exist")
                if not ok:
                    continue

                self._mount_and_certify(lua)
                lua.globals()._reg_kind = kind
                lua.execute(CORRUPTION_ROUND)
                g = lua.globals()

                self.assertIs(g._reg_baseline_render, True,
                              f"{kind}: positive baseline verify must be true")
                self.assertIs(g._reg_corrupted_render, False,
                              f"{kind}: corrupted primitive must fail actual _verify_render")
                self.assertIs(g._reg_failed_render_verified, False,
                              f"{kind}: blocked repair feed must not leave cached success")
                self.assertIs(g._reg_failed_render_failed, True,
                              f"{kind}: blocked repair feed must enter render_failed")
                self.assertIs(g._reg_failed_native_acquired, False,
                              f"{kind}: failed certification must release native")
                self.assertEqual(g._reg_failed_native_alpha,
                                 g._reg_native_fixture_alpha,
                                 f"{kind}: released native alpha must return to fixture 1")
                self.assertIs(g._reg_failed_prim_same, True,
                              f"{kind}: failure must not replace the owned primitive")
                self.assertIs(g._reg_failed_root_same, True,
                              f"{kind}: failure must not replace the owned root")

                self.assertIs(g._reg_recovered_render, True,
                              f"{kind}: ordinary feeds must repair and verify")
                self.assertIs(g._reg_recovered_render_verified, True,
                              f"{kind}: repaired render must stay certified")
                self.assertIs(g._reg_recovered_render_failed, False,
                              f"{kind}: repaired render must leave render_failed")
                self.assertIs(g._reg_recovered_prim_same, True,
                              f"{kind}: repaired primitive identity must be the same")
                self.assertIs(g._reg_recovered_root_same, True,
                              f"{kind}: repaired root identity must be the same")
                self.assertIs(g._reg_recovered_native_acquired, True,
                              f"{kind}: repaired render must reacquire native")
                self.assertEqual(g._reg_recovered_native_alpha, 0,
                                 f"{kind}: reacquired native alpha must be 0")


if __name__ == "__main__":
    unittest.main()
