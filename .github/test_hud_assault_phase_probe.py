"""Bounded assault phase-probe contract tests (test-only, RED on current).

Test 1 expects the existing KYO_RESIDUAL_PERF state to gain three nested
per-verifier assault phases when a real A:update runs while the probe is active:
assault_verify (both full _verify_render calls), assault_native (only
_try_acquire_native), and assault_animation (banner/title/ticker/transition
writes). The phases are characterization only and are nested under the existing
assault total.

Test 2 proves that without the sentinel, ordinary A:update performs no
diagnostic os.clock read and no log, while the real same-frame title set_x
corruption guard still fails closed and releases native ownership.

No fixture is copied. The real _lua_with_assault_state fixture and mount/warm
pattern are reused; _rearm_with_sentinel comes from test_hud_residual_probe.
Identities are compared in Lua; Python reads only scalar snapshots.
"""
import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_assault_render import _lua_with_assault_state
from test_hud_residual_probe import _rearm_with_sentinel

DT = 1.0 / 60.0

MOUNT_WARM = r'''
local RT = kyohud.hud.runtime
RT:mount(managers.hud)
local A = kyohud.hud.assault
A:mount(managers.hud)

local t = 1.0
for i = 1, 3 do
    A:update(managers.hud, t, 1 / 60)
    t = t + 1 / 60
end
_G._t = t
'''

PROFILE = r'''
local RT = kyohud.hud.runtime
local A = kyohud.hud.assault
_G._phase = {
    before_cert = A._render_verified == true,
    before_acquired = A._native_acquired == true,
}
local title_a_before = A._title_a
local title_b_before = A._title_b
local root_before = A._root_panel

managers.player = managers.player or {}
_G._probe_player_unit = {_alive = true}
managers.player.player_unit = function(self) return _G._probe_player_unit end

_G._probe_clock = {reads = 0, value = 0, delta = 0.0001}
os.clock = function()
    _G._probe_clock.reads = _G._probe_clock.reads + 1
    _G._probe_clock.value = _G._probe_clock.value + _G._probe_clock.delta
    return _G._probe_clock.value
end

_G._probe_logs = {}
log = function(message, ...)
    _G._probe_logs[#_G._probe_logs + 1] = tostring(message)
    return nil
end

RT:_residual_tick(2)
RT:_residual_tick(7.1)
_G._phase.active = RT._residual_probe and RT._residual_probe.active == true

local t = _G._t
for i = 1, 10 do
    A:update(managers.hud, t, 1 / 60)
    t = t + 1 / 60
end

_G._phase.after_cert = A._render_verified == true
_G._phase.after_acquired = A._native_acquired == true
_G._phase.same_title_a = A._title_a == title_a_before
_G._phase.same_title_b = A._title_b == title_b_before
_G._phase.same_root = A._root_panel == root_before

local function snap(name)
    local p = RT._residual_probe and RT._residual_probe.phases[name]
    if not p then return nil end
    return {count = p.count, sum = p.sum, max = p.max}
end
_G._phase.assault_verify = snap("assault_verify")
_G._phase.assault_verify_full = snap("assault_verify_full")
_G._phase.assault_verify_light = snap("assault_verify_light")
_G._phase.assault_native = snap("assault_native")
_G._phase.assault_animation = snap("assault_animation")

local clock_before_finish = _G._probe_clock.reads
local logs_before_finish = #_G._probe_logs
RT:_residual_tick(27.2)
_G._phase.done = RT._residual_probe and RT._residual_probe.done == true
_G._phase.finish_clock_delta = _G._probe_clock.reads - clock_before_finish
_G._phase.finish_log_delta = #_G._probe_logs - logs_before_finish

_G._phase.summary = nil
_G._phase.summary_count = 0
for _, text in ipairs(_G._probe_logs) do
    if text:find("[KyoHUD][ResidualProbe]", 1, true) then
        _G._phase.summary_count = _G._phase.summary_count + 1
        _G._phase.summary = _G._phase.summary or text
    end
end

local clock_before_later = _G._probe_clock.reads
local logs_before_later = #_G._probe_logs
A:update(managers.hud, t, 1 / 60)
_G._phase.extra_clock_delta = _G._probe_clock.reads - clock_before_later
_G._phase.extra_log_delta = #_G._probe_logs - logs_before_later
'''

NO_SENTINEL = r'''
local A = kyohud.hud.assault
_G._nosentinel = {
    before_cert = A._render_verified == true,
    before_acquired = A._native_acquired == true,
}

local real_clock = os.clock
local clock_reads = 0
os.clock = function()
    clock_reads = clock_reads + 1
    return real_clock()
end

local real_log = log
local logs = 0
log = function(message, ...)
    logs = logs + 1
    return real_log(message, ...)
end

local clock_before = clock_reads
local logs_before = logs
local t = _G._t
for i = 1, 10 do
    A:update(managers.hud, t, 1 / 60)
    t = t + 1 / 60
end
_G._nosentinel.clock_delta = clock_reads - clock_before
_G._nosentinel.log_delta = logs - logs_before
_G._nosentinel.after_cert = A._render_verified == true
_G._nosentinel.after_acquired = A._native_acquired == true

local title_a = A._title_a
local original_set_x = title_a.set_x
title_a.set_x = function(self, value)
    return original_set_x(self, value + 1000)
end
A:update(managers.hud, t, 1 / 60)
_G._nosentinel.corrupt_cert = A._render_verified == true
_G._nosentinel.corrupt_render_failed = A._render_failed == true
_G._nosentinel.corrupt_acquired = A._native_acquired == true
_G._nosentinel.corrupt_corner_nil = A._native_corner == nil
_G._nosentinel.corrupt_root_visible = A._root_panel and A._root_panel:visible() == true
local entries = 0
local nv = kyohud.hud.native_visibility
if nv and nv._entries then
    for _, entry in ipairs(nv._entries) do
        if entry.owner == "assault" then entries = entries + 1 end
    end
end
_G._nosentinel.assault_entries = entries
title_a.set_x = original_set_x
'''


def to_py(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "items"):
        return {str(k): to_py(v) for k, v in value.items()}
    return value


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(value)


class AssaultPhaseProbeTests(unittest.TestCase):
    def test_active_probe_records_three_nested_assault_phases(self):
        lua, ok = _lua_with_assault_state()
        self.assertTrue(ok, "assault fixture must exist")
        lua.execute(MOUNT_WARM)
        lua.execute(r'''
            _G._positive = {
                cert = kyohud.hud.assault._render_verified == true,
                acquired = kyohud.hud.assault._native_acquired == true,
            }
        ''')
        positive = to_py(lua.globals()._positive)
        self.assertTrue(positive["cert"], "render must be positive before arming")
        self.assertTrue(positive["acquired"],
                        "native ownership must be positive before arming")

        _rearm_with_sentinel(lua)
        lua.execute(PROFILE)
        phase = to_py(lua.globals()._phase)

        self.assertTrue(phase["before_cert"], "render must stay positive")
        self.assertTrue(phase["before_acquired"],
                        "native ownership must stay positive")
        self.assertTrue(phase["active"], "sentinel warmup must arm the probe")

        self.assertIsNotNone(
            phase.get("assault_verify"),
            "RED: active probe must expose the assault_verify phase table")
        verify = phase["assault_verify"]
        self.assertEqual(verify["count"], 20,
                         "ten updates must record twenty total verifier dispatches")
        self.assertTrue(finite(verify["sum"]) and verify["sum"] >= 0,
                        "assault_verify sum must be finite and non-negative")

        self.assertIsNotNone(
            phase.get("assault_verify_full"),
            "active probe must expose the assault_verify_full phase table")
        full = phase["assault_verify_full"]
        self.assertGreater(full["count"], 0,
                           "the measured window must include full dispatches")
        self.assertTrue(finite(full["sum"]) and full["sum"] >= 0,
                        "assault_verify_full sum must be finite and non-negative")

        self.assertIsNotNone(
            phase.get("assault_verify_light"),
            "active probe must expose the assault_verify_light phase table")
        light = phase["assault_verify_light"]
        self.assertGreater(light["count"], 0,
                           "the measured window must include light dispatches")
        self.assertTrue(finite(light["sum"]) and light["sum"] >= 0,
                        "assault_verify_light sum must be finite and non-negative")

        self.assertEqual(full["count"] + light["count"], verify["count"],
                         "full plus light dispatches must equal the aggregate count")
        self.assertEqual(full["count"] + light["count"], 20,
                         "the measured window must contain twenty dispatches")

        self.assertIsNotNone(
            phase.get("assault_native"),
            "RED: active probe must expose the assault_native phase table")
        native = phase["assault_native"]
        self.assertEqual(native["count"], 10,
                         "RED: ten updates must record one native acquisition pass")
        self.assertTrue(finite(native["sum"]) and native["sum"] >= 0,
                        "assault_native sum must be finite and non-negative")

        self.assertIsNotNone(
            phase.get("assault_animation"),
            "RED: active probe must expose the assault_animation phase table")
        animation = phase["assault_animation"]
        self.assertGreater(animation["count"], 0,
                           "RED: animation records must be observable")
        self.assertTrue(finite(animation["sum"]) and animation["sum"] >= 0,
                        "assault_animation sum must be finite and non-negative")

        self.assertTrue(phase["after_cert"],
                        "render must remain certified after profiling")
        self.assertTrue(phase["after_acquired"],
                        "native ownership must remain acquired after profiling")
        self.assertTrue(phase["same_title_a"],
                        "profiling must not replace owned title_a")
        self.assertTrue(phase["same_title_b"],
                        "profiling must not replace owned title_b")
        self.assertTrue(phase["same_root"],
                        "profiling must not replace the owned root")
        self.assertTrue(phase["done"], "finish tick must complete the probe")
        self.assertEqual(phase["summary_count"], 1,
                         "completion must emit exactly one ResidualProbe summary")
        self.assertIsNotNone(phase.get("summary"),
                             "completion summary must be captured")
        summary = phase["summary"]
        self.assertIn("assault_verify", summary,
                      "RED: summary must name the assault_verify phase")
        self.assertIn("assault_native", summary,
                      "RED: summary must name the assault_native phase")
        self.assertIn("assault_animation", summary,
                      "RED: summary must name the assault_animation phase")
        self.assertIn("nested", summary,
                      "RED: summary must label the phases nested")
        self.assertEqual(phase["extra_clock_delta"], 0,
                         "a completed probe must not read os.clock")
        self.assertEqual(phase["extra_log_delta"], 0,
                         "a completed probe must not log")

    def test_without_sentinel_no_diagnostics_and_title_guard_still_fails_closed(self):
        lua, ok = _lua_with_assault_state()
        self.assertTrue(ok, "assault fixture must exist")
        lua.execute(MOUNT_WARM)
        lua.execute(NO_SENTINEL)
        nosentinel = to_py(lua.globals()._nosentinel)

        self.assertTrue(nosentinel["before_cert"],
                        "render must be positive without sentinel")
        self.assertTrue(nosentinel["before_acquired"],
                        "native ownership must be positive without sentinel")
        self.assertEqual(nosentinel["clock_delta"], 0,
                         "no diagnostic os.clock read without sentinel")
        self.assertEqual(nosentinel["log_delta"], 0,
                         "no diagnostic log without sentinel")
        self.assertTrue(nosentinel["after_cert"],
                        "ordinary updates must keep render certified")
        self.assertTrue(nosentinel["after_acquired"],
                        "ordinary updates must keep native ownership")

        self.assertFalse(nosentinel["corrupt_cert"],
                         "corrupted title x must fail the same-frame verifier")
        self.assertTrue(nosentinel["corrupt_render_failed"],
                        "corrupted title x must flag render failure")
        self.assertFalse(nosentinel["corrupt_acquired"],
                         "corrupted title x must release native ownership")
        self.assertTrue(nosentinel["corrupt_corner_nil"],
                        "corrupted title x must clear the native corner")
        self.assertFalse(nosentinel["corrupt_root_visible"],
                         "corrupted title x must hide the owned root")
        self.assertEqual(nosentinel["assault_entries"], 0,
                         "corrupted title x must release assault native entries")


if __name__ == "__main__":
    unittest.main()
