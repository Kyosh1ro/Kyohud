"""Mission diagnostic phase buckets for the opt-in residual runtime probe.

Scope: one tracer bullet for Mission feed capture. The real mission.lua chunk,
the real runtime.lua chunk and the existing HUDManager timer fixture are reused
through test_hud_mission._lua. Mission is mounted and certified before the
runtime chunk is re-armed with the KYO_RESIDUAL_PERF sentinel, then the real
RT:_residual_tick advances a live-player warmup into capture.

During active capture exactly three same-second feed_heist_time dispatches must
grow the production counters: mission_feed (outer feed hook only), mission_sync
(all _sync_primitives callers), mission_layout (all _update_layout callers),
mission_verify (all _verify_render callers), mission_title_sync (all
_sync_title_prim callers) and mission_labels_verify (all _verify_labels
callers). On a healthy stable feed, _sync_title_prim is called once and
_verify_labels is called once (inside _verify_render); the duplicate call
inside _update_layout's changed predicate no longer runs on stable feeds.
Three feeds therefore grow both mission_title_sync and mission_labels_verify
by three. These are inclusive stage times, not pure text_rect timings. Counts
are read after mount/certification and warmup so mount and warmup work is
excluded.

The production buckets do not exist yet. Reading them directly is intentional
RED: no counter, instrumentation method or substitute is defined here.

Absent-sentinel and finished-capture feeds must stay diagnostic-free and must
retain the same owned timer primitive, timer text and native alpha.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_mission import _lua
from test_hud_residual_probe import (
    INSTALL_CLOCK_AND_LOG_COUNTERS,
    _rearm_with_sentinel,
)

BUCKETS = (
    "mission_feed",
    "mission_sync",
    "mission_layout",
    "mission_verify",
    "mission_title_sync",
    "mission_labels_verify",
)

INSTALL_DISPATCH = r'''
_G._feed_hook_count = 0
for _, entry in ipairs(Hooks._all) do
    if entry.method == "feed_heist_time" and entry.class == HUDManager then
        _G._feed_hook_count = _G._feed_hook_count + 1
    end
end

_G._dispatch_feed = function(time)
    local mgr = managers.hud
    mgr:feed_heist_time(time)
    for _, entry in ipairs(Hooks._all) do
        if entry.method == "feed_heist_time" and entry.class == HUDManager then
            entry.fn(mgr, time)
        end
    end
end

_G._bucket_count = function(name)
    local RT = kyohud.hud.runtime
    local probe = RT._residual_probe
    local record = probe and probe.phases and probe.phases[name]
    if type(record) == "table" and type(record.count) == "number" then
        return record.count
    end
    return nil
end
'''

MOUNT_CERTIFY = r'''
kyohud.settings.enable_hud_foundation = true
kyohud.settings.enable_mission = true

_G._phase_parent = _make_parent()
_make_mgr(_G._phase_parent)
_G._phase_mgr = managers.hud
_G._phase_mgr:_create_heist_timer({})

-- The embedded HUDHeistTimer fixture only exposes text/set_text. A native
-- timer text primitive also exposes alpha/set_alpha, which mission acquisition
-- and native-alpha retention are defined against.
local native_timer = _G._phase_mgr._hud_heist_timer._timer_text
native_timer._alpha = 1
native_timer.alpha = function(self) return self._alpha end
native_timer.set_alpha = function(self, value) self._alpha = value end

kyohud.hud.runtime:mount(_G._phase_mgr)
kyohud.hud.mission:mount(_G._phase_mgr)
_G._dispatch_feed(125)

local M = kyohud.hud.mission
local mgr = _G._phase_mgr
_G._cert_mounted = M._mounted == true
_G._cert_root = M._root_panel ~= nil
_G._cert_verified = M._render_verified == true
_G._cert_timer_prim = M._timer_prim ~= nil
_G._cert_timer_text = M._timer_text
_G._cert_native_acquired = M._native_acquired == true
_G._cert_native_alpha = mgr._hud_heist_timer._timer_text:alpha()
'''

LIVE_PLAYER = r'''
managers.player = managers.player or {}
_G._live_player_unit = {_alive = true}
managers.player.player_unit = function(self)
    return _G._live_player_unit
end
'''

ARM_AND_WARM = r'''
local RT = kyohud.hud.runtime
_G._armed_probe_is_table = type(RT._residual_probe) == "table"
RT:_residual_tick(2)
RT:_residual_tick(7.1)
_G._armed_probe_active = RT._residual_probe.active == true
'''

DELIVER_THREE = r'''
local t = 125
_G._dispatch_feed(t)
_G._dispatch_feed(t)
_G._dispatch_feed(t)
'''

FINISH_CAPTURE = r'''
local RT = kyohud.hud.runtime
_G._finish_active_before = RT._residual_probe.active == true
RT:_residual_tick(27.2)
_G._finish_done = RT._residual_probe.done == true
_G._finish_active_after = RT._residual_probe.active == true
'''

RETAIN_AND_DELIVER = r'''
local M = kyohud.hud.mission
local mgr = _G._phase_mgr
local native_timer = mgr._hud_heist_timer._timer_text
local timer_before = M._timer_prim
local text_before = M._timer_text
local alpha_before = native_timer:alpha()

local clock_before = clock_reads
local log_before = #log_texts
_G._dispatch_feed(125)
_G._dispatch_feed(125)
_G._dispatch_feed(125)

_G._retain_clock_delta = clock_reads - clock_before
_G._retain_log_delta = #log_texts - log_before
_G._retain_same_prim = rawequal(M._timer_prim, timer_before)
_G._retain_same_text = M._timer_text == text_before
_G._retain_same_alpha = native_timer:alpha() == alpha_before
_G._retain_text = M._timer_text
_G._retain_alpha = native_timer:alpha()
'''


def _bucket(lua, name):
    return lua.globals()._bucket_count(name)


def _missing(counts):
    return [name for name in BUCKETS if counts[name] is None]


class MissionPhaseProbeTests(unittest.TestCase):
    def _mount_and_certify(self, lua):
        lua.execute(INSTALL_DISPATCH)
        lua.execute(MOUNT_CERTIFY)
        g = lua.globals()

        self.assertEqual(g._feed_hook_count, 1,
                         "the fixture must expose exactly one registered "
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

    def _assert_retained(self, g, prefix):
        self.assertEqual(getattr(g, prefix + "_clock_delta"), 0,
                         f"{prefix}: feeds must not read the diagnostic clock")
        self.assertEqual(getattr(g, prefix + "_log_delta"), 0,
                         f"{prefix}: feeds must not emit diagnostic logs")
        self.assertIs(getattr(g, prefix + "_same_prim"), True,
                      f"{prefix}: timer primitive identity must be retained")
        self.assertIs(getattr(g, prefix + "_same_text"), True,
                      f"{prefix}: timer text must be retained")
        self.assertIs(getattr(g, prefix + "_same_alpha"), True,
                      f"{prefix}: native timer alpha must be retained")
        self.assertEqual(getattr(g, prefix + "_text"), "02:05",
                         f"{prefix}: retained timer text must stay 02:05")
        self.assertEqual(getattr(g, prefix + "_alpha"), 0,
                         f"{prefix}: retained native timer alpha must stay 0")

    def test_active_capture_grows_each_mission_bucket_by_three(self):
        lua, ok = _lua()
        self.assertTrue(ok, "lua/hud/mission.lua must exist")
        if not ok:
            return

        self._mount_and_certify(lua)
        lua.execute(LIVE_PLAYER)
        _rearm_with_sentinel(lua)
        lua.execute(ARM_AND_WARM)

        g = lua.globals()
        self.assertIs(g._armed_probe_is_table, True,
                      "armed sentinel must create the real residual probe")
        self.assertIs(g._armed_probe_active, True,
                      "live-player warmup must arm the real residual capture")

        before = {name: _bucket(lua, name) for name in BUCKETS}
        missing_before = _missing(before)
        self.assertFalse(
            missing_before,
            "RED: production probe phases are missing diagnostic buckets: "
            + ", ".join(missing_before),
        )
        if missing_before:
            return

        lua.execute(DELIVER_THREE)

        after = {name: _bucket(lua, name) for name in BUCKETS}
        missing_after = _missing(after)
        self.assertFalse(
            missing_after,
            "RED: production probe phases are missing diagnostic buckets: "
            + ", ".join(missing_after),
        )

        for name in BUCKETS:
            expected = 3
            self.assertEqual(
                after[name] - before[name],
                expected,
                f"RED: three same-second feeds must grow the {name} bucket by "
                f"exactly {expected} (mission_feed is the outer feed hook only; "
                "mission_sync/mission_layout/mission_verify wrap all callers; "
                "a healthy stable feed calls _sync_title_prim once and "
                "_verify_labels once inside _verify_render, so both "
                "mission_title_sync and mission_labels_verify grow by three); "
                "these are inclusive stage times, not pure text_rect timings",
            )

    def test_absent_sentinel_feeds_have_no_diagnostics_and_retain_timer(self):
        lua, ok = _lua()
        self.assertTrue(ok, "lua/hud/mission.lua must exist")
        if not ok:
            return

        self._mount_and_certify(lua)
        lua.execute('_G._absent_probe_is_nil = kyohud.hud.runtime._residual_probe == nil')
        self.assertIs(lua.globals()._absent_probe_is_nil, True,
                      "without the sentinel the residual probe must be nil")

        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(RETAIN_AND_DELIVER)
        self._assert_retained(lua.globals(), "_retain")

    def test_finished_capture_feeds_have_no_diagnostics_and_retain_timer(self):
        lua, ok = _lua()
        self.assertTrue(ok, "lua/hud/mission.lua must exist")
        if not ok:
            return

        self._mount_and_certify(lua)
        lua.execute(LIVE_PLAYER)
        _rearm_with_sentinel(lua)
        lua.execute(ARM_AND_WARM)
        lua.execute(FINISH_CAPTURE)

        g = lua.globals()
        self.assertIs(g._armed_probe_active, True,
                      "live-player warmup must arm the real residual capture")
        self.assertIs(g._finish_active_before, True,
                      "capture must be active before the finishing tick")
        self.assertIs(g._finish_done, True,
                      "20 game seconds of capture must finish the probe")
        self.assertIs(g._finish_active_after, False,
                      "a finished capture must be inactive")

        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(RETAIN_AND_DELIVER)
        self._assert_retained(lua.globals(), "_retain")


if __name__ == "__main__":
    unittest.main()
