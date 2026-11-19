"""RED: Kingpin active/terminal events must emit the six dedicated probe phases.

The quiet path runs the real activation and two real runtime updates without the
sentinel and must stay free of diagnostic clock reads and logs. With the sentinel
armed, a real positive radial event must increment prepare/chain only, while the
generic priority, the post-priority verification and the final verification are
skipped on a stable continuation, the real throttle
must only grow the existing kingpin_active phase, a real
terminal event must increment kingpin_event_terminal and release both leaves, and
the single bounded report must expose the six new names with finite counts. The
phases are absent from the current probe, so the emitted counters make this RED.
"""
import unittest

from test_hud_kingpin_active import KINGPIN_ACTIVATE, kingpin_lua
from test_hud_residual_probe import (INSTALL_CLOCK_AND_LOG_COUNTERS,
                                     _rearm_with_sentinel)


class KingpinPhaseProbeTests(unittest.TestCase):
    def test_kingpin_event_phases_are_emitted_and_bounded(self):
        lua = kingpin_lua()
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute("quiet_event_ok, quiet_event_err = pcall(function()\n"
                    + KINGPIN_ACTIVATE + "\nend)")
        lua.execute(r'''
            local RT, mgr = _R, _m
            quiet_nil = RT._residual_probe == nil
            quiet_update_ok, quiet_update_err = pcall(function()
                RT:update(mgr, 3, .05)
                RT:update(mgr, 3.01, .01) end)
            quiet_nil_after = RT._residual_probe == nil
            quiet_clock, quiet_logs = clock_reads, #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.quiet_nil, True, "no probe without the sentinel")
        self.assertIs(g.quiet_nil_after, True, "no probe after quiet work")
        self.assertIs(g.quiet_event_ok, True, g.quiet_event_err)
        self.assertIs(g.quiet_update_ok, True, g.quiet_update_err)
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
            local names = {"kingpin_event_prepare", "kingpin_event_chain",
                "kingpin_event_priority", "kingpin_event_post",
                "kingpin_event_final", "kingpin_event_terminal"}
            local function count(name)
                local record = p and p.phases and p.phases[name]
                return record and record.count or 0
            end
            local before = {}
            for i, name in ipairs(names) do before[i] = count(name) end
            event_ok, event_err = pcall(function()
                mgr:set_player_ability_radial({current = 6, total = 6}) end)
            local after = {}
            for i, name in ipairs(names) do after[i] = count(name) end
            first2_increased = true
            for i = 1, 2 do
                if after[i] < before[i] + 1 then first2_increased = false end
            end
            priority_unchanged = (after[3] == before[3])
            post_unchanged = (after[4] == before[4])
            final_unchanged = (after[5] == before[5])
            event_verified = (E:verify() == true)
            meter_hidden = (_ability_meter:visible() == false)
            icon_hidden = (_ability_icon:visible() == false)
            local active_before = count("kingpin_active")
            throttle_ok, throttle_err = pcall(function()
                RT:update(mgr, 15.01, .01) end)
            active_increased = count("kingpin_active") >= active_before + 1
            event_unchanged = true
            for i, name in ipairs(names) do
                if count(name) ~= after[i] then event_unchanged = false end
            end
            local terminal_before = count("kingpin_event_terminal")
            terminal_ok, terminal_err = pcall(function()
                mgr:set_player_ability_radial({current = 0, total = 1}) end)
            terminal_increased =
                count("kingpin_event_terminal") >= terminal_before + 1
            meter_visible = (_ability_meter:visible() == true)
            icon_visible = (_ability_icon:visible() == true)
            finish_ok, finish_err = pcall(function()
                RT:update(mgr, 35.1, .05) end)
            local reports, text = 0, ""
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                    reports, text = reports + 1, message
                end
            end
            local function finite(v)
                return type(v) == "number" and v == v
                    and v ~= math.huge and v ~= -math.huge
            end
            local names_ok, counts_ok = true, true
            for _, name in ipairs(names) do
                local value = tonumber(text:match(name .. "%s+(%d+)"))
                if value == nil then
                    names_ok, counts_ok = false, false
                elseif not finite(value) or value < 0 then
                    counts_ok = false
                end
            end
            report_count, report_names_ok, report_counts_ok =
                reports, names_ok, counts_ok
            post_clock, post_logs = clock_reads, #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.warm_ok, True, g.warm_err)
        self.assertIs(g.warm_active, True, "t=10/15 must arm the capture")
        self.assertIs(g.event_ok, True, g.event_err)
        self.assertIs(g.first2_increased, True,
                      "positive event must increment prepare/chain")
        self.assertIs(g.priority_unchanged, True,
                      "the generic priority must be skipped on a stable "
                      "continuation")
        self.assertIs(g.post_unchanged, True,
                      "the post-priority verification must be skipped on a "
                      "stable continuation")
        self.assertIs(g.final_unchanged, True,
                      "the final verification must be skipped on a stable "
                      "continuation")
        self.assertIs(g.event_verified, True,
                      "positive native event must keep the render certified")
        self.assertIs(g.meter_hidden, True,
                      "positive event must hide the meter leaf")
        self.assertIs(g.icon_hidden, True,
                      "positive event must hide the icon leaf")
        self.assertIs(g.throttle_ok, True, g.throttle_err)
        self.assertIs(g.active_increased, True,
                      "throttled update must grow existing kingpin_active")
        self.assertIs(g.event_unchanged, True,
                      "throttled update must not grow event buckets")
        self.assertIs(g.terminal_ok, True, g.terminal_err)
        self.assertIs(g.terminal_increased, True,
                      "terminal event must increment kingpin_event_terminal")
        self.assertIs(g.meter_visible, True,
                      "terminal event must release the meter leaf")
        self.assertIs(g.icon_visible, True,
                      "terminal event must release the icon leaf")
        self.assertIs(g.finish_ok, True, g.finish_err)
        self.assertEqual(g.report_count, 1, "exactly one bounded report")
        self.assertIs(g.report_names_ok, True,
                      "the report must include all six event names")
        self.assertIs(g.report_counts_ok, True,
                      "the report event counts must be finite and >= 0")

        lua.execute("late_event_ok, late_event_err = pcall(function()\n"
                    + KINGPIN_ACTIVATE + "\nend)")
        lua.execute(r'''
            local RT, mgr = _R, _m
            late_terminal_ok, late_terminal_err = pcall(function()
                mgr:set_player_ability_radial({current = 0, total = 1}) end)
            late_update_ok, late_update_err = pcall(function()
                RT:update(mgr, 36, .05) end)
            late_clock, late_logs = clock_reads, #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.late_event_ok, True, g.late_event_err)
        self.assertIs(g.late_terminal_ok, True, g.late_terminal_err)
        self.assertIs(g.late_update_ok, True, g.late_update_err)
        self.assertEqual(g.late_clock, g.post_clock,
                         "no diagnostic clock read after completion")
        self.assertEqual(g.late_logs, g.post_logs,
                         "no log after completion")


if __name__ == "__main__":
    unittest.main()
