"""Hacker activity probe: the real synchronous activation event must be counted
by the residual hacker_active phase, the real throttled activity work must be
counted by equipment_present, and the bounded report must expose hacker_active.

The quiet path exercises the same real runtime/event/throttle calls with no
sentinel and requires zero diagnostic clock reads and zero logs. RED while
hacker_active is absent from residual_probe.phases and _throttle_hacker_activity
is missing from the equipment residual phase wrappers.
"""
import unittest

from test_hud_hacker_active import ACTIVATE_AND_OBSERVE, hacker_lua
from test_hud_residual_probe import INSTALL_CLOCK_AND_LOG_COUNTERS, _rearm_with_sentinel

EQUIPMENT_PHASES = (
    "equipment_collect",
    "equipment_snapshot",
    "equipment_present",
    "equipment_verify",
    "equipment_throttled",
)


class HackerProbeTests(unittest.TestCase):
    def test_hacker_active_event_and_activity_throttle_are_bounded(self):
        lua = hacker_lua()
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local RT, mgr = _R, _m
            quiet_probe_nil = RT._residual_probe == nil
            quiet_update_ok, quiet_update_err = pcall(function()
                RT:update(mgr, 3, .05)
            end)
            quiet_update_err = tostring(quiet_update_err or "")
        ''')
        lua.execute("quiet_event_ok, quiet_event_err = pcall(function()\n"
                    + ACTIVATE_AND_OBSERVE + "\nend)")
        lua.execute(r'''
            local RT, mgr = _R, _m
            quiet_event_err = tostring(quiet_event_err or "")
            quiet_throttle_ok, quiet_throttle_err = pcall(function()
                RT:update(mgr, 3.01, .05)
            end)
            quiet_throttle_err = tostring(quiet_throttle_err or "")
            quiet_probe_nil_after = RT._residual_probe == nil
            quiet_clock = clock_reads
            quiet_logs = #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.quiet_probe_nil, True,
                      "no probe without the sentinel")
        self.assertIs(g.quiet_probe_nil_after, True,
                      "no probe after quiet runtime/event/throttle")
        self.assertIs(g.quiet_update_ok, True, g.quiet_update_err)
        self.assertIs(g.quiet_event_ok, True, g.quiet_event_err)
        self.assertIs(g.quiet_throttle_ok, True, g.quiet_throttle_err)
        self.assertEqual(g.quiet_clock, 0,
                         "probeabsent runtime/event/throttle must not read os.clock")
        self.assertEqual(g.quiet_logs, 0,
                         "probeabsent runtime/event/throttle must not log")

        _rearm_with_sentinel(lua)
        self.assertEqual(lua.globals()._sentinel_opens, 1,
                         "the runtime chunk must open the sentinel exactly once")

        lua.execute(r'''
            local RT, mgr = _R, _m
            local p = RT._residual_probe
            warm_ok, warm_err = pcall(function()
                RT:update(mgr, 10, .05)
                RT:update(mgr, 15, .05)
            end)
            warm_err = tostring(warm_err or "")
            warm_active = p ~= nil and p.active == true
            local phase = p and p.phases and p.phases.hacker_active
            event_count_before = phase and phase.count or 0
            game_clock_before = _game_clock:time()
        ''')
        lua.execute("qualified_event_ok, qualified_event_err = pcall(function()\n"
                    + ACTIVATE_AND_OBSERVE + "\nend)")
        lua.execute(r'''
            local RT, E, mgr = _R, _E, _m
            local p = RT._residual_probe
            qualified_event_err = tostring(qualified_event_err or "")
            game_clock_after = _game_clock:time()
            local phase = p and p.phases and p.phases.hacker_active
            hacker_phase_exists = type(phase) == "table"
            hacker_phase_shape_ok = type(phase) == "table"
                and type(phase.count) == "number"
                and type(phase.sum) == "number"
                and type(phase.max) == "number"
            hacker_count = phase and phase.count or 0
            event_count_after = phase and phase.count or 0

            throttled_ok, throttled_err = pcall(function()
                RT:update(mgr, 15.01, .01)
            end)
            throttled_err = tostring(throttled_err or "")

            local wrappers = E._residual_phase_wrappers
            local entry = type(wrappers) == "table"
                and wrappers["_throttle_hacker_activity"] or nil
            throttle_method = type(E._throttle_hacker_activity) == "function"
            throttle_registered = entry ~= nil
            throttle_identity = entry ~= nil
                and entry == E._throttle_hacker_activity

            local present = p and p.phases and p.phases.equipment_present
            present_before = present and present.count or 0
            direct_throttle_ok, direct_throttle_err = false, "missing"
            if throttle_method then
                direct_throttle_ok, direct_throttle_err =
                    pcall(E._throttle_hacker_activity, E)
                direct_throttle_err = tostring(direct_throttle_err or "")
            end
            present_after = present and present.count or 0
        ''')
        g = lua.globals()
        self.assertIs(g.warm_ok, True, g.warm_err)
        self.assertIs(g.warm_active, True,
                      "5s warmup through t=10/15 must arm the capture")
        self.assertIs(g.qualified_event_ok, True, g.qualified_event_err)
        self.assertEqual(int(g.game_clock_before), 1000,
                         "the activation fixture game clock must start at 1000")
        self.assertEqual(int(g.game_clock_after), 1000,
                         "the synchronous activation must not advance game time")
        self.assertIs(g.hacker_phase_exists, True,
                      "residual_probe.phases.hacker_active must exist")
        self.assertIs(g.hacker_phase_shape_ok, True,
                      "hacker_active must expose numeric count/sum/max")
        self.assertGreater(int(g.hacker_count), 0,
                           "the synchronous activation must be counted")
        self.assertGreaterEqual(int(g.event_count_after),
                                int(g.event_count_before) + 1,
                                "ACTIVATE_AND_OBSERVE must increment hacker_active")
        self.assertIs(g.throttled_ok, True, g.throttled_err)
        self.assertIs(g.throttle_method, True,
                      "real E._throttle_hacker_activity must exist")
        self.assertIs(g.throttle_registered, True,
                      "_throttle_hacker_activity must be in residual phase wrappers")
        self.assertIs(g.throttle_identity, True,
                      "throttle wrapper identity must equal E._throttle_hacker_activity")
        self.assertIs(g.direct_throttle_ok, True, g.direct_throttle_err)
        self.assertGreaterEqual(int(g.present_after),
                                int(g.present_before) + 1,
                                "direct throttle must increment equipment_present")

        lua.execute(r'''
            local RT, mgr = _R, _m
            finish_ok, finish_err = pcall(function()
                RT:update(mgr, 35.1, .05)
            end)
            finish_err = tostring(finish_err or "")
            local q = RT._residual_probe
            capture_done = q ~= nil and q.done == true
            capture_active = q ~= nil and q.active == true
            hacker_final_count = q and q.phases and q.phases.hacker_active
                and q.phases.hacker_active.count or 0

            local phase_names = {"equipment_collect", "equipment_snapshot",
                "equipment_present", "equipment_verify", "equipment_throttled"}
            phase_counts, phase_shape_ok = {}, true
            for _, name in ipairs(phase_names) do
                local rec = q and q.phases and q.phases[name]
                phase_counts[name] = rec and rec.count or 0
                phase_shape_ok = phase_shape_ok and type(rec) == "table"
                    and type(rec.count) == "number"
                    and type(rec.sum) == "number"
                    and type(rec.max) == "number"
            end

            local reports, text = 0, ""
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                    reports, text = reports + 1, message
                end
            end
            report_count, report_text = reports, text
            local matched = text:match("hacker_active%s+(%d+)")
            report_hacker_count = tonumber(matched) or 0
            finish_clock, finish_logs = clock_reads, #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.finish_ok, True, g.finish_err)
        self.assertIs(g.capture_done, True,
                      "20s capture must finish the probe")
        self.assertIs(g.capture_active, False,
                      "a finished probe must be inactive")
        self.assertGreater(int(g.hacker_final_count), 0,
                           "the final hacker_active phase count must stay positive")
        self.assertIs(g.phase_shape_ok, True,
                      "known equipment phases must expose numeric count/sum/max")
        for name in EQUIPMENT_PHASES:
            self.assertGreater(int(g.phase_counts[name]), 0, name)
        self.assertEqual(g.report_count, 1,
                         "exactly one [KyoHUD][ResidualProbe] report must be emitted")
        self.assertIn("hacker_active", str(g.report_text),
                      "the single report must contain the hacker_active field")
        self.assertGreater(int(g.report_hacker_count), 0,
                           "the report hacker_active count must be positive")

        lua.execute("later_event_ok, later_event_err = pcall(function()\n"
                    + ACTIVATE_AND_OBSERVE + "\nend)")
        lua.execute(r'''
            local RT, mgr = _R, _m
            later_event_err = tostring(later_event_err or "")
            later_update_ok, later_update_err = pcall(function()
                RT:update(mgr, 36, .05)
            end)
            later_update_err = tostring(later_update_err or "")
            local reports = 0
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                    reports = reports + 1
                end
            end
            later_report_count = reports
            post_clock, post_logs = clock_reads, #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.later_event_ok, True, g.later_event_err)
        self.assertIs(g.later_update_ok, True, g.later_update_err)
        self.assertEqual(g.later_report_count, 1,
                         "a completed probe must not emit a second report")
        self.assertEqual(g.post_clock, g.finish_clock,
                         "no diagnostic clock read may occur after completion")
        self.assertEqual(g.post_logs, g.finish_logs,
                         "no log may occur after completion")


if __name__ == "__main__":
    unittest.main()
