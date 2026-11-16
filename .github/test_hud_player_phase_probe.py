"""Bounded local player/crew phase-probe gate (TEST ONLY, RED on current).

The existing sentinel-gated residual probe must gain five nested phases for the
real local runtime updaters: player_capture, player_render, player_verify,
player_native_acquire and crew_native_acquire. The probe is armed only through
the real KYO_RESIDUAL_PERF sentinel re-execution helper; this test never forces
probe.active or fabricates phase records. Genuine R:update calls perform the 5s
warmup and the 20s capture, then must stop permanently after one report.

The fixture is test_hud_local_h5_lifecycle._local_runtime: player, weapons and
crew are enabled, equipment is disabled, and the globals R/mgr are the mounted
runtime and HUD manager produced by that fixture. Without the sentinel, ordinary
updates must not read the diagnostic clock or log anything.
"""
import unittest

from test_hud_local_h5_lifecycle import _local_runtime
from test_hud_residual_probe import (
    INSTALL_CLOCK_AND_LOG_COUNTERS,
    _rearm_with_sentinel,
)

PLAYER_PHASES = (
    "player_capture",
    "player_render",
    "player_verify",
    "player_native_acquire",
    "crew_native_acquire",
)


class PlayerPhaseProbeTests(unittest.TestCase):
    def test_disabled_sentinel_keeps_player_updates_quiet(self):
        """No sentinel: no probe, no os.clock read and no log during R:update."""
        lua = _local_runtime()
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local RT, manager = R, mgr
            probe_is_nil = RT._residual_probe == nil
            settings_ok = kyohud.settings.enable_player == true
                and kyohud.settings.enable_weapons == true
                and kyohud.settings.enable_crew == true
                and kyohud.settings.enable_equipment == false
            modules_ok = kyohud.hud.player._root ~= nil
                and kyohud.hud.weapons._root ~= nil
                and kyohud.hud.crew._root ~= nil
            update_ok, update_err = pcall(function()
                RT:update(manager, 10, .05)
                RT:update(manager, 15, .05)
                RT:update(manager, 15.01, .05)
                RT:update(manager, 15.08, .05)
                RT:update(manager, 35.1, .05)
                RT:update(manager, 36, .05)
            end)
            update_error = tostring(update_err or "")
            clock_reads_after = clock_reads
            log_count_after = #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.probe_is_nil, True,
                      "without the sentinel, the residual probe must be nil")
        self.assertIs(g.settings_ok, True,
                      "the fixture must keep player/weapons/crew on and equipment off")
        self.assertIs(g.modules_ok, True,
                      "the real player/weapons/crew roots must be mounted")
        self.assertIs(g.update_ok, True,
                      f"ordinary R:update must succeed: {g.update_error}")
        self.assertEqual(g.clock_reads_after, 0,
                         "disabled profiling must not read os.clock during updates")
        self.assertEqual(g.log_count_after, 0,
                         "disabled profiling must not log during updates")

    def test_armed_sentinel_reports_player_phases_then_stops(self):
        """Genuine R:update capture must record every player/crew phase once."""
        lua = _local_runtime()
        _rearm_with_sentinel(lua)
        self.assertEqual(lua.globals()._sentinel_opens, 1,
                         "the runtime chunk must open the sentinel exactly once")
        self.assertEqual(lua.globals()._sentinel_closes, 1,
                         "the runtime chunk must close the sentinel immediately")
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local RT, manager = R, mgr
            local probe = RT._residual_probe
            probe_is_table = type(probe) == "table"
            settings_ok = kyohud.settings.enable_player == true
                and kyohud.settings.enable_weapons == true
                and kyohud.settings.enable_crew == true
                and kyohud.settings.enable_equipment == false

            capture_ok, capture_err = pcall(function()
                RT:update(manager, 10, .05)
                RT:update(manager, 15, .05)
                RT:update(manager, 15.01, .05)
                RT:update(manager, 15.08, .05)
                RT:update(manager, 35.1, .05)
            end)
            capture_error = tostring(capture_err or "")
            capture_done = probe ~= nil and probe.done == true
            capture_active = probe ~= nil and probe.active == true

            local function count_of(name)
                local record = probe and probe.phases and probe.phases[name]
                if type(record) ~= "table" then return -1 end
                return record.count
            end

            phase_counts = {}
            phase_shape_ok = true
            for _, name in ipairs({"player_capture", "player_render",
                "player_verify", "player_native_acquire",
                "crew_native_acquire"}) do
                local record = probe and probe.phases and probe.phases[name]
                phase_counts[name] = count_of(name)
                if type(record) ~= "table"
                    or type(record.count) ~= "number"
                    or type(record.sum) ~= "number"
                    or type(record.max) ~= "number"
                    or record.count < 0
                    or record.sum < 0 or record.max < 0
                    or record.sum ~= record.sum or record.max ~= record.max
                    or record.sum == math.huge or record.sum == -math.huge
                    or record.max == math.huge or record.max == -math.huge then
                    phase_shape_ok = false
                end
            end
            old_player_count = count_of("player")
            old_crew_count = count_of("crew")

            local reports, report_text = 0, ""
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                    reports = reports + 1
                    report_text = message
                end
            end
            report_count = reports
            probe_report_text = report_text
            clock_after_capture = clock_reads
            log_after_capture = #log_texts

            later_ok, later_err = pcall(function()
                RT:update(manager, 36, .05)
            end)
            later_error = tostring(later_err or "")
            later_done = probe ~= nil and probe.done == true
            later_active = probe ~= nil and probe.active == true
            clock_after_later = clock_reads
            log_after_later = #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.probe_is_table, True,
                      "the armed sentinel must create the residual probe")
        self.assertIs(g.settings_ok, True,
                      "the fixture must keep player/weapons/crew on and equipment off")
        self.assertIs(g.capture_ok, True,
                      f"capture frames must run through genuine R:update: {g.capture_error}")
        self.assertIs(g.capture_done, True,
                      "20 game seconds of capture must finish the probe")
        self.assertIs(g.capture_active, False,
                      "a completed probe must be inactive")
        self.assertIs(g.phase_shape_ok, True,
                      "RED: player/crew phases must expose finite non-negative count/sum/max")
        self.assertGreater(int(g.old_player_count), 0,
                           "genuine R:update must record the existing player phase")
        self.assertGreater(int(g.old_crew_count), 0,
                           "genuine R:update must record the existing crew phase")

        for name in PLAYER_PHASES:
            self.assertGreater(
                int(g.phase_counts[name]), 0,
                f"RED: genuine R:update must record {name}")

        self.assertEqual(g.report_count, 1,
                         "exactly one ResidualProbe report must be emitted")
        report_text = str(g.probe_report_text)
        self.assertIn("[KyoHUD][ResidualProbe]", report_text,
                      "the single report must carry the ResidualProbe prefix")
        for name in PLAYER_PHASES:
            self.assertIn(name, report_text,
                          f"the single report must name {name}")

        self.assertIs(g.later_ok, True,
                      f"post-capture R:update must still succeed: {g.later_error}")
        self.assertIs(g.later_done, True,
                      "a completed probe must stay done")
        self.assertIs(g.later_active, False,
                      "a completed probe must stay inactive")
        self.assertEqual(g.clock_after_later, g.clock_after_capture,
                         "no diagnostic os.clock read may occur after completion")
        self.assertEqual(g.log_after_later, g.log_after_capture,
                         "no log may occur after completion")

    def test_acquire_group_keeps_void_return_arity(self):
        """A missing local_ group must stay void with profiling off or active."""
        lua = _local_runtime()
        lua.execute(r'''
            local stamp = R._residual_stamp
            inactive_stamp_calls = 0
            R._residual_stamp = function(self)
                inactive_stamp_calls = inactive_stamp_calls + 1
                return stamp(self)
            end
            R:update(mgr, 10, .05)
            R:update(mgr, 15, .05)
            inactive_stamp_calls = 0
            disabled_arity = select("#",
                R:_h5_acquire_group("local_probe_missing", {}, nil))
            disabled_probe = R._residual_probe ~= nil
        ''')
        g = lua.globals()
        self.assertEqual((g.disabled_arity, g.disabled_probe,
                          g.inactive_stamp_calls), (0, False, 0),
                         "RED: unarmed profiling must stay void and un-stamped")
        lua = _local_runtime()
        _rearm_with_sentinel(lua)
        lua.execute(r'''
            R:update(mgr, 10, .05)
            R:update(mgr, 15, .05)
            armed_active = R._residual_probe.active == true
            armed_arity = select("#",
                R:_h5_acquire_group("local_probe_missing", {}, nil))
        ''')
        g = lua.globals()
        self.assertIs(g.armed_active, True, "5s warmup must activate capture")
        self.assertEqual(g.armed_arity, 0,
                         "RED: active capture must preserve void arity")


if __name__ == "__main__":
    unittest.main()
