"""LOT2 background dedup cost: healthy stable Mission feeds must not resync.

Scope: backgrounds only. The real mission.lua chunk is mounted through the
existing test_hud_mission._lua fixture and certified with
test_hud_mission_phase_probe.INSTALL_DISPATCH/MOUNT_CERTIFY. Test-local
wrappers observe the real Color factory and the real owned background
setters without changing their behavior; the real _verify_render and
_verify_labels production methods are wrapped the same way.

RED contract: 20 identical feeds at 02:05 must not construct Color values
and must not call set_color/set_alpha/set_visible/set_shape on the owned
backgrounds. The panels, roots and verify counts (20 render, 20 labels)
must stay stable. Production currently rewrites all three backgrounds on
every feed, so the zero-setter assertions fail RED.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_mission import _lua
from test_hud_mission_phase_probe import INSTALL_DISPATCH, MOUNT_CERTIFY

INSTRUMENT = r'''
_G._bg_keys = {"timer", "title", "bags"}

_G._bg_color_calls = 0
_G._bg_color_original = Color
Color = setmetatable({}, {__call = function(_, ...)
    _G._bg_color_calls = _G._bg_color_calls + 1
    return _G._bg_color_original(...)
end})

_G._bg_setter_calls = {color = 0, alpha = 0, visible = 0, shape = 0}
_G._bg_panels = {}
_G._bg_originals = {}
_G._bg_instrumented = 0

local function instrument(key)
    local M = kyohud.hud.mission
    local prim = M._backgrounds and M._backgrounds[key]
    if not prim then return end
    _G._bg_panels[key] = prim
    local originals = {
        set_color = prim.set_color,
        set_alpha = prim.set_alpha,
        set_visible = prim.set_visible,
        set_shape = prim.set_shape,
    }
    _G._bg_originals[key] = originals
    _G._bg_instrumented = _G._bg_instrumented + 1
    prim.set_color = function(self, c)
        _G._bg_setter_calls.color = _G._bg_setter_calls.color + 1
        return originals.set_color(self, c)
    end
    prim.set_alpha = function(self, a)
        _G._bg_setter_calls.alpha = _G._bg_setter_calls.alpha + 1
        return originals.set_alpha(self, a)
    end
    prim.set_visible = function(self, v)
        _G._bg_setter_calls.visible = _G._bg_setter_calls.visible + 1
        return originals.set_visible(self, v)
    end
    prim.set_shape = function(self, x, y, w, h)
        _G._bg_setter_calls.shape = _G._bg_setter_calls.shape + 1
        return originals.set_shape(self, x, y, w, h)
    end
end

for _, key in ipairs(_G._bg_keys) do instrument(key) end

local M = kyohud.hud.mission
_G._verify_render_calls = 0
_G._verify_labels_calls = 0
_G._verify_render_original = M._verify_render
_G._verify_labels_original = M._verify_labels
M._verify_render = function(self, ...)
    _G._verify_render_calls = _G._verify_render_calls + 1
    return _G._verify_render_original(self, ...)
end
M._verify_labels = function(self, ...)
    _G._verify_labels_calls = _G._verify_labels_calls + 1
    return _G._verify_labels_original(self, ...)
end

_G._bg_roots_before = {
    root = M._root_panel,
    background_root = M._background_root,
}
_G._bg_identity_before = {}
for _, key in ipairs(_G._bg_keys) do
    _G._bg_identity_before[key] = M._backgrounds[key]
end
'''

DELIVER_STABLE = r'''
_G._bg_color_calls = 0
_G._bg_setter_calls = {color = 0, alpha = 0, visible = 0, shape = 0}
_G._verify_render_calls = 0
_G._verify_labels_calls = 0

for _ = 1, 20 do
    _G._dispatch_feed(125)
end

local M = kyohud.hud.mission
_G._bg_color_observed = _G._bg_color_calls
_G._bg_set_color_observed = _G._bg_setter_calls.color
_G._bg_set_alpha_observed = _G._bg_setter_calls.alpha
_G._bg_set_visible_observed = _G._bg_setter_calls.visible
_G._bg_set_shape_observed = _G._bg_setter_calls.shape
_G._verify_render_observed = _G._verify_render_calls
_G._verify_labels_observed = _G._verify_labels_calls

_G._bg_roots_same = rawequal(M._root_panel, _G._bg_roots_before.root)
    and rawequal(M._background_root, _G._bg_roots_before.background_root)
_G._bg_identities_same = true
_G._bg_identity_diff = nil
for _, key in ipairs(_G._bg_keys) do
    if not rawequal(M._backgrounds[key], _G._bg_identity_before[key]) then
        _G._bg_identities_same = false
        _G._bg_identity_diff = key
    end
end
'''

REGRESSION_ROUND = r'''
local M = kyohud.hud.mission
local mgr = _G._phase_mgr
local native_timer = mgr._hud_heist_timer._timer_text
local key = "title"
local p = M._backgrounds[key]
local kind = _G._reg_kind

_G._reg_baseline_render = M:_verify_render()
_G._reg_prim = p
_G._reg_root = M._root_panel
_G._reg_native_fixture_alpha = 1
_G._reg_alpha_baseline = p:alpha()

if kind == "color" then
    _G._reg_setter = p.set_color
    p:set_color(Color(1, 1, 0, 1))
    p:set_alpha(_G._reg_alpha_baseline)
elseif kind == "alpha" then
    _G._reg_setter = p.set_alpha
    p:set_alpha(0)
elseif kind == "visible" then
    _G._reg_setter = p.set_visible
    p:set_visible(false)
end

_G._reg_corrupted_render = M:_verify_render()

if kind == "color" then
    p.set_color = function(self, c) end
elseif kind == "alpha" then
    p.set_alpha = function(self, a) end
elseif kind == "visible" then
    p.set_visible = function(self, v) end
end

_G._dispatch_feed(125)

_G._reg_failed_render_verified = M._render_verified == true
_G._reg_failed_render_failed = M._render_failed == true
_G._reg_failed_native_acquired = M._native_acquired == true
_G._reg_failed_native_alpha = native_timer:alpha()

if kind == "color" then
    p.set_color = _G._reg_setter
elseif kind == "alpha" then
    p.set_alpha = _G._reg_setter
elseif kind == "visible" then
    p.set_visible = _G._reg_setter
end

_G._dispatch_feed(125)
_G._dispatch_feed(125)

_G._reg_recovered_render = M:_verify_render()
_G._reg_recovered_prim_same = rawequal(M._backgrounds[key], _G._reg_prim)
_G._reg_recovered_root_same = rawequal(M._root_panel, _G._reg_root)
_G._reg_recovered_native_acquired = M._native_acquired == true
_G._reg_recovered_native_alpha = native_timer:alpha()
'''


class MissionBackgroundCostTests(unittest.TestCase):
    def test_stable_feeds_do_not_recolor_or_retouch_backgrounds(self):
        lua, ok = _lua()
        self.assertTrue(ok, "lua/hud/mission.lua must exist")
        if not ok:
            return

        lua.execute(INSTALL_DISPATCH)
        lua.execute(MOUNT_CERTIFY)

        g = lua.globals()
        self.assertEqual(g._feed_hook_count, 1,
                         "fixture must expose exactly one "
                         "HUDManager:feed_heist_time callback")
        self.assertIs(g._cert_mounted, True,
                      "positive baseline: mission must be mounted")
        self.assertIs(g._cert_root, True,
                      "positive baseline: mission must own a root panel")
        self.assertIs(g._cert_verified, True,
                      "positive baseline: mission render must be certified")
        self.assertIs(g._cert_timer_prim, True,
                      "positive baseline: mission must own a timer primitive")
        self.assertIs(g._cert_native_acquired, True,
                      "positive baseline: native timer must be acquired")
        self.assertEqual(g._cert_native_alpha, 0,
                         "positive baseline: acquired native timer alpha must be 0")

        lua.execute(INSTRUMENT)

        g = lua.globals()
        self.assertEqual(g._bg_instrumented, 3,
                         "positive baseline: timer/title/bags backgrounds "
                         "must exist and be instrumented")

        lua.execute(DELIVER_STABLE)
        g = lua.globals()

        self.assertEqual(g._verify_render_observed, 20,
                         "20 stable feeds must verify the render 20 times")
        self.assertEqual(g._verify_labels_observed, 20,
                         "20 stable feeds must verify labels 20 times "
                         "(once per feed, inside _verify_render)")
        self.assertIs(g._bg_roots_same, True,
                      "stable feeds must keep the same root and background root")
        self.assertTrue(
            bool(g._bg_identities_same),
            "stable feeds must keep the same background primitive identities"
            + (f" (changed: {g._bg_identity_diff})" if g._bg_identity_diff else ""),
        )

        self.assertEqual(g._bg_color_observed, 0,
                         "RED: stable feeds must not construct Color values "
                         f"(observed {g._bg_color_observed})")
        self.assertEqual(g._bg_set_color_observed, 0,
                         "RED: stable feeds must not call background set_color "
                         f"(observed {g._bg_set_color_observed})")
        self.assertEqual(g._bg_set_alpha_observed, 0,
                         "RED: stable feeds must not call background set_alpha "
                         f"(observed {g._bg_set_alpha_observed})")
        self.assertEqual(g._bg_set_visible_observed, 0,
                         "RED: stable feeds must not call background set_visible "
                         f"(observed {g._bg_set_visible_observed})")
        self.assertEqual(g._bg_set_shape_observed, 0,
                         "RED: stable feeds must not call background set_shape "
                         f"(observed {g._bg_set_shape_observed})")

    def test_noop_property_setter_blocks_repair_then_recovers(self):
        for kind in ("color", "alpha", "visible"):
            with self.subTest(property=kind):
                lua, ok = _lua()
                self.assertTrue(ok, "lua/hud/mission.lua must exist")
                if not ok:
                    continue

                lua.execute(INSTALL_DISPATCH)
                lua.execute(MOUNT_CERTIFY)

                g = lua.globals()
                self.assertIs(g._cert_mounted, True,
                              f"{kind}: positive baseline mission must be mounted")
                self.assertIs(g._cert_verified, True,
                              f"{kind}: positive baseline render must be certified")
                self.assertIs(g._cert_native_acquired, True,
                              f"{kind}: positive baseline native must be acquired")
                self.assertEqual(g._cert_native_alpha, 0,
                                 f"{kind}: positive baseline native alpha must be 0")

                lua.globals()._reg_kind = kind
                lua.execute(REGRESSION_ROUND)
                g = lua.globals()

                self.assertIs(g._reg_baseline_render, True,
                              f"{kind}: positive baseline actual verify must be true")
                self.assertIs(g._reg_corrupted_render, False,
                              f"{kind}: corrupted primitive must fail actual _verify_render")
                self.assertIs(g._reg_failed_render_verified, False,
                              f"{kind}: no-op setter must not leave cached success")
                self.assertIs(g._reg_failed_render_failed, True,
                              f"{kind}: blocked repair must enter render_failed")
                self.assertIs(g._reg_failed_native_acquired, False,
                              f"{kind}: failed certification must release native")
                self.assertEqual(g._reg_failed_native_alpha,
                                 g._reg_native_fixture_alpha,
                                 f"{kind}: released native alpha must return to fixture 1")

                self.assertIs(g._reg_recovered_render, True,
                              f"{kind}: ordinary feeds must repair and verify")
                self.assertIs(g._reg_recovered_prim_same, True,
                              f"{kind}: repaired background primitive identity must be stable")
                self.assertIs(g._reg_recovered_root_same, True,
                              f"{kind}: repaired root identity must be stable")
                self.assertIs(g._reg_recovered_native_acquired, True,
                              f"{kind}: repaired render must reacquire native")
                self.assertEqual(g._reg_recovered_native_alpha, 0,
                                 f"{kind}: reacquired native alpha must be 0")


if __name__ == "__main__":
    unittest.main()
