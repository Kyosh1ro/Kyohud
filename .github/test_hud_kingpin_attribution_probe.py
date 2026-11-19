"""RED: Kingpin interval attribution must expose the real production phase
deltas for publication capture and throttle.

The fixture is the real Hacker/Kingpin runtime and HUDManager publication
method; only the diagnostics clock and heap getters are deterministic doubles.
Production currently has no kingpin_publication_capture or
kingpin_throttle_full phase, so these assertions are expected to fail (RED).
"""
import re
import unittest

from test_hud_kingpin_publication_probe import publication_lua


CLOCK_AND_HEAP = r'''
os.clock = function()
    _pub_clock_reads = _pub_clock_reads + 1
    _pub_clock = _pub_clock + .0001
    return _pub_clock
end
collectgarbage = function(mode, ...)
    if mode ~= "count" then
        error("unexpected collectgarbage mode: " .. tostring(mode))
    end
    return 1000
end
'''


class KingpinAttributionProbeTests(unittest.TestCase):
    def _assert_number(self, actual, expected, delta=1e-3, msg=None):
        if actual is None:
            self.fail(msg or "expected a numeric diagnostic field, got nil")
        self.assertAlmostEqual(float(actual), float(expected), delta=delta,
                               msg=msg)

    def test_capture_and_throttle_phases_are_attributed_to_published_bin(self):
        lua = publication_lua()
        lua.execute(CLOCK_AND_HEAP)
        lua.execute(r'''
            local RT, mgr = _R, _m
            local p = RT._residual_probe

            local function phase_sum(name)
                local phase = p and p.phases and p.phases[name]
                return phase and phase.sum
            end

            local function phase_count(name)
                local phase = p and p.phases and p.phases[name]
                return phase and phase.count
            end

            wait_ok, wait_err = pcall(function()
                RT:update(mgr, 100, .05)
            end)
            arm_ok, arm_err = pcall(function()
                mgr:set_player_ability_radial({current = 6, total = 6})
            end)
            armed = p and p.active == true
            last_ui = _E and _E._last_ui

            base_publication = phase_sum("kingpin_publication_total") or 0
            base_capture = phase_sum("kingpin_publication_capture") or 0
            base_throttle = phase_sum("kingpin_throttle_full") or 0

            baseline_ok, baseline_err = pcall(function()
                RT:update(mgr, 100.001, .001)
            end)

            meter_hidden = (_ability_meter:visible() == false)
            icon_hidden = (_ability_icon:visible() == false)
            equipment_verified = kyohud.hud.equipment ~= nil
                and kyohud.hud.equipment:verify() == true

            publish_ok, publish_err = pcall(function()
                mgr:set_player_ability_radial({current = 5.9, total = 6})
            end)

            publication_sum = phase_sum("kingpin_publication_total")
            capture_sum = phase_sum("kingpin_publication_capture")
            throttle_sum = phase_sum("kingpin_throttle_full")
            publication_count = phase_count("kingpin_publication_total")
            capture_count = phase_count("kingpin_publication_capture")
            throttle_count = phase_count("kingpin_throttle_full")
            publication_present = publication_sum ~= nil
            capture_present = capture_sum ~= nil
            throttle_present = throttle_sum ~= nil

            meter_hidden_after = (_ability_meter:visible() == false)
            icon_hidden_after = (_ability_icon:visible() == false)
            equipment_verified_after = kyohud.hud.equipment ~= nil
                and kyohud.hud.equipment:verify() == true

            expected_publication_ms = nil
            expected_capture_ms = nil
            expected_throttle_ms = nil
            expected_publication_text = nil
            expected_capture_text = nil
            expected_throttle_text = nil
            if publication_present and capture_present and throttle_present then
                expected_publication_ms =
                    (publication_sum - base_publication) * 1000
                expected_capture_ms = (capture_sum - base_capture) * 1000
                expected_throttle_ms = (throttle_sum - base_throttle) * 1000
                expected_publication_text =
                    string.format("%.3f", expected_publication_ms)
                expected_capture_text =
                    string.format("%.3f", expected_capture_ms)
                expected_throttle_text =
                    string.format("%.3f", expected_throttle_ms)
            end

            next_ok, next_err = pcall(function()
                RT:update(mgr, 100.011, .01)
            end)

            local pub = p and p.kingpin_intervals
                and p.kingpin_intervals.bins
                and p.kingpin_intervals.bins.published
            bin_count = pub and pub.count
            bin_publication_ms = pub and pub.publication_ms
            bin_capture_ms = pub and pub.capture_ms
            bin_throttle_ms = pub and pub.throttle_ms
            bin_max_publication_ms = pub and pub.max_gap_publication_ms
            bin_max_capture_ms = pub and pub.max_gap_capture_ms
            bin_max_throttle_ms = pub and pub.max_gap_throttle_ms

            finish_ok, finish_err = pcall(function()
                RT:update(mgr, 120.1, .05)
            end)
            done = p and p.done == true

            local reports, published_line, residual_reports = 0, "", 0
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][KingpinIntervals]", 1, true) then
                    reports = reports + 1
                    if message:lower():find("published", 1, true)
                        and message:find("publication_ms", 1, true) then
                        published_line = message
                    end
                elseif message:find("[KyoHUD]", 1, true)
                    and message:lower():find("residual", 1, true) then
                    residual_reports = residual_reports + 1
                end
            end
            interval_reports = reports
            residual_report_count = residual_reports
            published_report = published_line
        ''')
        g = lua.globals()

        self.assertIs(g.wait_ok, True, g.wait_err)
        self.assertIs(g.arm_ok, True, g.arm_err)
        self.assertIs(g.armed, True, "a positive event must arm the mode")
        self.assertIsNotNone(g.last_ui, "_E._last_ui must be set")
        self.assertAlmostEqual(float(g.last_ui), 100.0, delta=1e-6,
            msg="the baseline must start from the ordinary 100 clock")
        self.assertIs(g.baseline_ok, True, g.baseline_err)

        self.assertIs(g.meter_hidden, True,
                      "the positive ability_meter lease must be hidden")
        self.assertIs(g.icon_hidden, True,
                      "the positive ability_icon lease must be hidden")
        self.assertIs(g.equipment_verified, True,
                      "owned equipment must verify before observations")
        self.assertIs(g.publish_ok, True, g.publish_err)
        self.assertIs(g.meter_hidden_after, True)
        self.assertIs(g.icon_hidden_after, True)
        self.assertIs(g.equipment_verified_after, True)

        missing = [name for name in ("publication_present", "capture_present",
                                     "throttle_present")
                   if not getattr(g, name)]
        if missing:
            self.fail("missing required production phases: "
                      "kingpin_publication_total, "
                      "kingpin_publication_capture, "
                      "kingpin_throttle_full")

        for name in ("publication_count", "capture_count", "throttle_count"):
            self.assertIsNotNone(getattr(g, name), f"{name} must be recorded")
            self.assertGreater(int(getattr(g, name)), 0,
                               f"{name} must be positive")
        self.assertGreater(float(g.capture_sum), float(g.base_capture))
        self.assertGreater(float(g.throttle_sum), float(g.base_throttle))

        delta_publication = float(g.publication_sum) - float(g.base_publication)
        self.assertGreater(delta_publication, 0.0,
                           "kingpin_publication_total must advance")
        self.assertGreaterEqual(delta_publication, 0.0069,
            "kingpin_publication_total must include the .007 native cost")

        self.assertIs(g.next_ok, True, g.next_err)
        self.assertIsNotNone(g.bin_count, "the published bin must exist")
        self.assertEqual(int(g.bin_count), 1,
            "the baseline attempt must be excluded; one published interval")

        for name in ("bin_publication_ms", "bin_capture_ms",
                     "bin_throttle_ms"):
            self.assertIsNotNone(getattr(g, name), f"{name} must be recorded")
        self._assert_number(g.bin_publication_ms, g.expected_publication_ms,
                            msg="publication_ms must match the real phase delta")
        self._assert_number(g.bin_capture_ms, g.expected_capture_ms,
                            msg="capture_ms must match the real phase delta")
        self._assert_number(g.bin_throttle_ms, g.expected_throttle_ms,
                            msg="throttle_ms must match the real phase delta")
        self._assert_number(g.bin_max_publication_ms, g.bin_publication_ms,
                            msg="max_gap_publication_ms must match this interval")
        self._assert_number(g.bin_max_capture_ms, g.bin_capture_ms,
                            msg="max_gap_capture_ms must match this interval")
        self._assert_number(g.bin_max_throttle_ms, g.bin_throttle_ms,
                            msg="max_gap_throttle_ms must match this interval")

        self.assertIs(g.finish_ok, True, g.finish_err)
        self.assertIs(g.done, True)
        self.assertEqual(int(g.interval_reports), 4,
                         "finish must emit three bin rows plus one meta line")
        self.assertEqual(int(g.residual_report_count), 1,
                         "the residual probe must emit exactly one report")

        report = str(g.published_report)
        self.assertIn("[KyoHUD][KingpinIntervals]", report)
        for name, expected in (
            ("publication_ms", g.expected_publication_text),
            ("capture_ms", g.expected_capture_text),
            ("throttle_ms", g.expected_throttle_text),
            ("max_gap_publication_ms", g.expected_publication_text),
            ("max_gap_capture_ms", g.expected_capture_text),
            ("max_gap_throttle_ms", g.expected_throttle_text),
        ):
            self.assertRegex(
                report,
                r"(?:^| )" + re.escape(name) + "="
                + re.escape(str(expected)) + r"(?: |$)",
                f"the published line must carry {name}={expected}",
            )

    def test_absent_and_done_wrappers_do_not_read_clock(self):
        lua = publication_lua()
        lua.execute(CLOCK_AND_HEAP)
        lua.execute(r'''
            local RT, mgr = _R, _m
            local p = RT._residual_probe

            throttle_exists = _E ~= nil
                and type(_E._throttle_kingpin_activity) == "function"

            RT._residual_probe = nil
            absent_probe_nil = RT._residual_probe == nil

            local absent_before = _pub_clock_reads
            local absent_event_ok, absent_event_err = pcall(function()
                mgr:set_player_ability_radial({current = 6, total = 6})
            end)
            local absent_event_after = _pub_clock_reads
            local absent_throttle_ok, absent_throttle_err = pcall(function()
                _E:_throttle_kingpin_activity(100.001, .001)
            end)
            local absent_after = _pub_clock_reads
            absent_event_clocks = absent_event_after - absent_before
            absent_throttle_clocks = absent_after - absent_event_after

            RT._residual_probe = p

            local mount_ok, mount_err = pcall(function()
                RT:update(mgr, 10, .05)
            end)
            local arm_ok, arm_err = pcall(function()
                mgr:set_player_ability_radial({current = 6, total = 6})
            end)
            local baseline_ok, baseline_err = pcall(function()
                RT:update(mgr, 100, .05)
            end)
            local finish_ok, finish_err = pcall(function()
                RT:update(mgr, 120.1, .05)
            end)
            done = p and p.done == true

            local done_before = _pub_clock_reads
            local done_event_ok, done_event_err = pcall(function()
                mgr:set_player_ability_radial({current = 5.9, total = 6})
            end)
            local done_event_after = _pub_clock_reads
            local done_throttle_ok, done_throttle_err = pcall(function()
                _E:_throttle_kingpin_activity(120.101, .001)
            end)
            local done_after = _pub_clock_reads
            done_event_clocks = done_event_after - done_before
            done_throttle_clocks = done_after - done_event_after

            absent_ok = absent_event_ok and absent_throttle_ok
            done_ok = mount_ok and arm_ok and baseline_ok and finish_ok
                and done_event_ok and done_throttle_ok
            path_err = tostring(absent_event_err or absent_throttle_err
                or mount_err or arm_err or baseline_err or finish_err
                or done_event_err or done_throttle_err or "")
        ''')
        g = lua.globals()

        self.assertIs(g.throttle_exists, True,
                      "_E:_throttle_kingpin_activity must exist")
        self.assertIs(g.absent_probe_nil, True,
                      "the absent path must really remove the probe")
        self.assertIs(g.absent_ok, True, g.path_err)
        self.assertIs(g.done_ok, True, g.path_err)
        self.assertIs(g.done, True)
        self.assertEqual(int(g.absent_event_clocks), 0,
            "an absent probe publication wrapper must not read os.clock")
        self.assertEqual(int(g.absent_throttle_clocks), 0,
            "an absent probe throttle wrapper must not read os.clock")
        self.assertEqual(int(g.done_event_clocks), 0,
            "a done probe publication wrapper must not read os.clock")
        self.assertEqual(int(g.done_throttle_clocks), 0,
            "a done probe throttle wrapper must not read os.clock")


if __name__ == "__main__":
    unittest.main()
