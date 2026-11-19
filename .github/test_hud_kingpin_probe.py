"""Kingpin activity probe: the real native positive radial publication must be
counted by residual kingpin_active and certified, throttled runtime work must add
kingpin_active plus equipment_present/generic phases, the native terminal zero
publication must count kingpin_active too and release the leased leaves, and the
bounded report must expose a positive kingpin_active. The quiet path runs the
same real runtime/event/throttle calls without a sentinel and requires zero
diagnostic clock reads and zero logs. RED while the coordinator hardcodes
hacker_active in _sync_local_backdrop and ignores ordinary/terminal Kingpin work.
"""
import unittest

from test_hud_kingpin_active import KINGPIN_ACTIVATE, kingpin_lua
from test_hud_residual_probe import (INSTALL_CLOCK_AND_LOG_COUNTERS,
                                     _rearm_with_sentinel)


class KingpinProbeTests(unittest.TestCase):
    def test_kingpin_active_ordinary_terminal_and_throttle_are_bounded(self):
        lua = kingpin_lua()
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local RT, mgr = _R, _m
            quiet_nil = RT._residual_probe == nil
            quiet_update_ok, quiet_update_err = pcall(function()
                RT:update(mgr, 3, .05) end)
        ''')
        lua.execute("quiet_event_ok, quiet_event_err = pcall(function()\n"
                    + KINGPIN_ACTIVATE + "\nend)")
        lua.execute(r'''
            local RT, mgr = _R, _m
            quiet_throttle_ok, quiet_throttle_err = pcall(function()
                RT:update(mgr, 3.01, .05) end)
            quiet_nil_after = RT._residual_probe == nil
            quiet_clock, quiet_logs = clock_reads, #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.quiet_nil, True, "no probe without the sentinel")
        self.assertIs(g.quiet_nil_after, True, "no probe after quiet work")
        self.assertIs(g.quiet_update_ok, True, g.quiet_update_err)
        self.assertIs(g.quiet_event_ok, True, g.quiet_event_err)
        self.assertIs(g.quiet_throttle_ok, True, g.quiet_throttle_err)
        self.assertEqual(g.quiet_clock, 0, "quiet work must not read os.clock")
        self.assertEqual(g.quiet_logs, 0, "quiet work must not log")

        _rearm_with_sentinel(lua)
        self.assertEqual(lua.globals()._sentinel_opens, 1,
                         "the runtime chunk must open the sentinel once")

        lua.execute(r'''
            local RT, E, mgr = _R, _E, _m
            warm_ok, warm_err = pcall(function()
                RT:update(mgr, 10, .05)
                RT:update(mgr, 15, .05) end)
            local p = RT._residual_probe
            warm_active = p ~= nil and p.active == true
            local function count(n)
                local r = p and p.phases and p.phases[n]
                return r and r.count or 0
            end
            event_before = count("kingpin_active")
            positive_ok, positive_err = pcall(function()
                mgr:set_player_ability_radial({current = 6, total = 6}) end)
            local kp = p and p.phases and p.phases.kingpin_active
            kingpin_phase_ok = type(kp) == "table"
                and type(kp.count) == "number"
                and type(kp.sum) == "number"
                and type(kp.max) == "number"
            event_after = count("kingpin_active")
            positive_verified = (E:verify() == true)
            positive_row = (E._visible_rows and E._visible_rows[6] == true)
                or false
            throttled_ok, throttled_err = pcall(function()
                RT:update(mgr, 15.01, .01) end)
            throttle_after = count("kingpin_active")
            present_after = count("equipment_present")
            runtime_after = count("runtime")
            terminal_before = count("kingpin_active")
            terminal_ok, terminal_err = pcall(function()
                mgr:set_player_ability_radial({current = 0, total = 6}) end)
            terminal_after = count("kingpin_active")
            terminal_verified = (E:verify() == true)
            terminal_released = (_ability_meter:visible() == true)
                and (_ability_icon:visible() == true)
            terminal_row_hidden = not ((E._visible_rows
                and E._visible_rows[6] == true) or false)
            source_app = Application:time()
            source_active = managers.player:has_activate_temporary_upgrade(
                "temporary", "chico_injector") == true
            source_expire = managers.player:get_activate_temporary_expire_time(
                "temporary", "chico_injector")
            finish_ok, finish_err = pcall(function()
                RT:update(mgr, 35.1, .05) end)
            local q = RT._residual_probe
            capture_done = q ~= nil and q.done == true
            capture_active = q ~= nil and q.active == true
            kingpin_final = count("kingpin_active")
            local reports, text = 0, ""
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                    reports, text = reports + 1, message
                end
            end
            report_count, report_text = reports, text
            report_kingpin = tonumber(text:match("kingpin_active%s+(%d+)")) or 0
            finish_clock, finish_logs = clock_reads, #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.warm_ok, True, g.warm_err)
        self.assertIs(g.warm_active, True, "t=10/15 must arm the capture")
        self.assertIs(g.positive_ok, True, g.positive_err)
        self.assertIs(g.kingpin_phase_ok, True,
                      "phases.kingpin_active must exist with numeric count/sum/max")
        self.assertGreaterEqual(int(g.event_after), int(g.event_before) + 1,
                                "positive native publication must count kingpin_active")
        self.assertIs(g.positive_verified, True,
                      "positive native publication must certify the render")
        self.assertIs(g.positive_row, True,
                      "positive native publication must show the ACTIVE row")
        self.assertIs(g.throttled_ok, True, g.throttled_err)
        self.assertGreaterEqual(int(g.throttle_after), int(g.event_after) + 1,
                                "throttled work must count kingpin_active again")
        self.assertGreater(int(g.present_after), 0,
                           "throttled work must record equipment_present")
        self.assertGreater(int(g.runtime_after), 0,
                           "throttled work must record the runtime phase")
        self.assertIs(g.terminal_ok, True, g.terminal_err)
        self.assertGreaterEqual(int(g.terminal_after),
                                int(g.terminal_before) + 1,
                                "terminal zero publication must count kingpin_active")
        self.assertIs(g.terminal_verified, True,
                      "terminal zero publication must keep the render certified")
        self.assertIs(g.terminal_released, True,
                      "terminal zero publication must release the leased leaves")
        self.assertIs(g.terminal_row_hidden, True,
                      "terminal zero publication must hide the ACTIVE row")
        self.assertEqual(int(g.source_app), 1000, "app clock must stay at 1000")
        self.assertIs(g.source_active, True,
                      "Kingpin source must stay active without expiry")
        self.assertEqual(float(g.source_expire), 1006.0,
                         "Kingpin source expiry must stay unchanged")
        self.assertIs(g.finish_ok, True, g.finish_err)
        self.assertIs(g.capture_done, True, "20s capture must finish the probe")
        self.assertIs(g.capture_active, False, "finished probe must be inactive")
        self.assertGreater(int(g.kingpin_final), 0,
                           "final kingpin_active count must stay positive")
        self.assertEqual(g.report_count, 1, "exactly one bounded report")
        self.assertIn("kingpin_active", str(g.report_text),
                      "the single report must contain kingpin_active")
        self.assertGreater(int(g.report_kingpin), 0,
                           "the report kingpin_active count must be positive")

        lua.execute("later_event_ok, later_event_err = pcall(function()\n"
                    + KINGPIN_ACTIVATE + "\nend)")
        lua.execute(r'''
            local RT, mgr = _R, _m
            later_update_ok, later_update_err = pcall(function()
                RT:update(mgr, 36, .05) end)
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
                         "completed probe must not emit a second report")
        self.assertEqual(g.post_clock, g.finish_clock,
                         "no diagnostic clock read after completion")
        self.assertEqual(g.post_logs, g.finish_logs,
                         "no log after completion")


if __name__ == "__main__":
    unittest.main()
