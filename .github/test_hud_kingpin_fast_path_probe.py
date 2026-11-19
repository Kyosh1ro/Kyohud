"""RED: steady Kingpin radial events must use a count-only fast prepare path.

The residual probe must expose kingpin_prepare_fast, kingpin_prepare_full and
kingpin_reject_dirty as count-only phase counters. A clean steady event must
grow only prepare_fast while a dirty retained surface must force prepare_full
and reject_dirty. Current production has no such counters, so the fast-count
and report-label assertions are RED. The test calls the real fixture methods
and records scalar observations only; it installs no profiler.
"""
import re
import unittest

from test_hud_kingpin_active import KINGPIN_ACTIVATE, kingpin_lua
from test_hud_residual_probe import (INSTALL_CLOCK_AND_LOG_COUNTERS,
                                     _rearm_with_sentinel)


NEW_COUNTERS = ("kingpin_prepare_fast", "kingpin_prepare_full",
                "kingpin_reject_dirty")


class KingpinFastPathProbeTests(unittest.TestCase):
    def counts(self, lua):
        lua.execute(r'''
            local p = _R._residual_probe
            local function count(name)
                local record = p and p.phases and p.phases[name]
                return record and record.count or 0
            end
            _G._c_fast = count("kingpin_prepare_fast")
            _G._c_full = count("kingpin_prepare_full")
            _G._c_reject = count("kingpin_reject_dirty")
        ''')
        g = lua.globals()
        return int(g._c_fast), int(g._c_full), int(g._c_reject)

    def test_fast_path_counts_and_report_are_count_only(self):
        lua = kingpin_lua()
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute("quiet_ok, quiet_err = pcall(function()\n"
                    + KINGPIN_ACTIVATE + "\n_R:update(_m, 3.1, .05)\nend)")
        lua.execute("quiet_clock, quiet_logs = clock_reads, #log_texts")
        g = lua.globals()
        self.assertIs(g.quiet_ok, True, g.quiet_err)
        self.assertEqual(g.quiet_clock, 0, "quiet work must not read os.clock")
        self.assertEqual(g.quiet_logs, 0, "quiet work must not log")

        _rearm_with_sentinel(lua)
        self.assertEqual(lua.globals()._sentinel_opens, 1,
                         "the runtime chunk must open the sentinel once")
        lua.execute(r'''
            warm_ok, warm_err = pcall(function()
                _R:update(_m, 10, .05)
                _R:update(_m, 15, .05) end)
            seed_ok, seed_err = pcall(function()
                _m:set_player_ability_radial({current = 5.5, total = 6}) end)
            seed_active = (_R._residual_probe ~= nil
                and _R._residual_probe.active == true)
        ''')
        g = lua.globals()
        self.assertIs(g.warm_ok, True, g.warm_err)
        self.assertIs(g.seed_ok, True, g.seed_err)
        self.assertIs(g.seed_active, True,
                      "t=10/15 plus the seed event must arm the capture")

        before_fast, before_full, before_reject = self.counts(lua)
        lua.execute(r'''
            fast_ok, fast_err = pcall(function()
                _m:set_player_ability_radial({current = 4.25, total = 6}) end)
            fast_verify = (_E:verify() == true)
            fast_meter_hidden = (_ability_meter:visible() == false)
            fast_icon_hidden = (_ability_icon:visible() == false)
        ''')
        g = lua.globals()
        self.assertIs(g.fast_ok, True, g.fast_err)
        self.assertIs(g.fast_verify, True, "clean event must stay certified")
        self.assertIs(g.fast_meter_hidden, True,
                      "clean event must keep the meter hidden")
        self.assertIs(g.fast_icon_hidden, True,
                      "clean event must keep the icon hidden")
        fast_fast, fast_full, fast_reject = self.counts(lua)
        self.assertGreater(fast_fast, before_fast,
                           "RED: clean steady event must grow prepare_fast")
        self.assertEqual(fast_full, before_full,
                         "clean steady event must not grow prepare_full")
        self.assertEqual(fast_reject, before_reject,
                         "clean steady event must not grow reject_dirty")

        lua.execute(r'''
            _E._dirty = true
            dirty_ok, dirty_err = pcall(function()
                _m:set_player_ability_radial({current = 4, total = 6}) end)
            dirty_verify = (_E:verify() == true)
            dirty_meter_hidden = (_ability_meter:visible() == false)
            dirty_icon_hidden = (_ability_icon:visible() == false)
        ''')
        g = lua.globals()
        self.assertIs(g.dirty_ok, True, g.dirty_err)
        self.assertIs(g.dirty_verify, True, "dirty event must stay certified")
        self.assertIs(g.dirty_meter_hidden, True,
                      "dirty event must keep the meter hidden")
        self.assertIs(g.dirty_icon_hidden, True,
                      "dirty event must keep the icon hidden")
        dirty_fast, dirty_full, dirty_reject = self.counts(lua)
        self.assertGreater(dirty_full, fast_full,
                           "RED: dirty steady event must grow prepare_full")
        self.assertGreater(dirty_reject, fast_reject,
                           "RED: dirty steady event must grow reject_dirty")

        lua.execute(r'''
            finish_ok, finish_err = pcall(function()
                _R:update(_m, 35.1, .05) end)
            _G._reports, _G._report_text = 0, ""
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                    _G._reports = _G._reports + 1
                    _G._report_text = message
                end
            end
            _G._done_clock, _G._done_logs = clock_reads, #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.finish_ok, True, g.finish_err)
        self.assertEqual(g._reports, 1, "exactly one bounded report")
        text = g._report_text
        for name in NEW_COUNTERS:
            match = re.search(re.escape(name) + r"\s+(\d+)(?![\d.])", text)
            self.assertIsNotNone(
                match, "RED: report must emit count-only %s" % name)
            self.assertGreaterEqual(int(match.group(1)), 0, name)

        lua.execute(r'''
            after_ok, after_err = pcall(function()
                _m:set_player_ability_radial({current = 3.5, total = 6}) end)
            after_clock, after_logs = clock_reads, #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.after_ok, True, g.after_err)
        self.assertEqual(g.after_clock, g._done_clock,
                         "no diagnostic clock read after completion")
        self.assertEqual(g.after_logs, g._done_logs,
                         "no log after completion")


if __name__ == "__main__":
    unittest.main()
