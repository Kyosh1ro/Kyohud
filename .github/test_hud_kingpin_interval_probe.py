"""RED: Kingpin interval diagnostics must record bounded active-tick bins.

The upcoming runtime-only instrumentation must sample once per valid active
_residual_tick at HUD update entry, establish one baseline sample without
attributing the partial trigger interval, classify each later interval as
terminal / published / no_publication from existing phase deltas, and retain
the t-gap, elapsed os.clock delta and net Lua heap delta of the same interval.
It must never force a garbage collection, never sample while inactive, waiting,
done or capped, and must emit at most four KingpinIntervals lines once on
finish/abort.

Production currently has no p.kingpin_intervals recorder, so these assertions
are expected to fail (RED). The native-shaped trigger fixture below is the real
Hacker/Kingpin runtime and event hooks; only the diagnostics clock and heap
getters are deterministic test doubles.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_kingpin_active import kingpin_lua
from test_hud_kingpin_trigger_probe import _kingpin_probe_lua


INSTALL_INTERVAL_DOUBLES = r'''
_interval_clock = 0
_interval_heap = 1000
_heap_reads = 0
_interval_clock_reads = 0
os.clock = function()
    _interval_clock_reads = _interval_clock_reads + 1
    return _interval_clock
end
collectgarbage = function(mode, ...)
    if mode ~= "count" then
        error("unexpected collectgarbage mode: " .. tostring(mode))
    end
    _heap_reads = _heap_reads + 1
    return _interval_heap
end
'''


def _ability_leases_lua():
    return r'''
function ability_leases()
    local count = 0
    local nv = kyohud.hud.native_visibility
    if nv and nv._entries then
        for _, entry in ipairs(nv._entries) do
            if entry.object == _ability_meter or entry.object == _ability_icon then
                count = count + 1
            end
        end
    end
    return count
end
'''


class KingpinIntervalProbeTests(unittest.TestCase):
    def _assert_number(self, actual, expected, delta=1e-3, msg=None):
        if actual is None:
            self.fail(msg or "expected a numeric diagnostic field, got nil")
        self.assertAlmostEqual(float(actual), float(expected), delta=delta,
                               msg=msg)

    def test_real_event_capture_publishes_terminal_and_no_publication_bins(self):
        lua = _kingpin_probe_lua()
        lua.execute(INSTALL_INTERVAL_DOUBLES)
        lua.execute(r'''
            local RT, mgr = _R, _m
            local p = RT._residual_probe

            wait_ok, wait_err = pcall(function()
                RT:update(mgr, 100, .05)
            end)
            waiting_heap = _heap_reads

            activation_ok, activation_err = pcall(function()
                mgr:set_player_ability_radial({current = 6, total = 6})
            end)
            active_after_event = p and p.active == true

            baseline_ok, baseline_err = pcall(function()
                RT:update(mgr, 100.01, .05)
            end)
            baseline_active = p and p.active == true
            recorder_present = p ~= nil
                and type(p.kingpin_intervals) == "table"

            meter_hidden = (_ability_meter:visible() == false)
            icon_hidden = (_ability_icon:visible() == false)
            equipment_verified = kyohud.hud.equipment ~= nil
                and kyohud.hud.equipment:verify() == true

            _interval_clock = .004
            _interval_heap = 936
            publish_ok, publish_err = pcall(function()
                mgr:set_player_ability_radial({current = 5.9, total = 6})
            end)
            gap_ok, gap_err = pcall(function()
                RT:update(mgr, 100.05, .05)
            end)

            local function bin(name)
                local iv = p and p.kingpin_intervals
                local bins = iv and iv.bins
                return bins and bins[name] or nil
            end

            local pub = bin("published")
            published_count = pub and pub.count
            published_events = pub and pub.events
            published_heap_drop_count = pub and pub.heap_drop_count
            published_heap_drop_kb = pub and pub.heap_drop_kb
            published_max_gap_ms = pub and pub.max_gap_ms
            published_max_gap_clock_ms = pub and pub.max_gap_clock_ms
            published_max_gap_heap_delta_kb = pub
                and pub.max_gap_heap_delta_kb

            _interval_clock = .005
            _interval_heap = 940
            terminal_event_ok, terminal_event_err = pcall(function()
                mgr:set_player_ability_radial({current = 0, total = 1})
            end)
            terminal_ok, terminal_err = pcall(function()
                RT:update(mgr, 100.06, .05)
            end)
            local term = bin("terminal")
            terminal_count = term and term.count

            _interval_clock = .006
            _interval_heap = 950
            noevent_ok, noevent_err = pcall(function()
                RT:update(mgr, 100.07, .05)
            end)
            local nop = bin("no_publication")
            no_publication_count = nop and nop.count

            _interval_clock = .02
            _interval_heap = 900
            finish_ok, finish_err = pcall(function()
                RT:update(mgr, 120.1, .05)
            end)
            finish_done = p and p.done == true
            finish_active = p and p.active == true
            local iv = p and p.kingpin_intervals
            reported = iv ~= nil and iv.reported == true

            local reports, text = 0, ""
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][KingpinIntervals]", 1, true) then
                    reports = reports + 1
                    text = text .. message .. "\n"
                end
            end
            interval_report_count = reports
            interval_report_text = text

            after_finish_heap = _heap_reads
            after_finish_logs = #log_texts
            late_event_ok, late_event_err = pcall(function()
                mgr:set_player_ability_radial({current = 6, total = 6})
            end)
            late_update_ok, late_update_err = pcall(function()
                RT:update(mgr, 121, .05)
            end)
            late_heap = _heap_reads
            late_logs = #log_texts
            late_done = p and p.done == true
            late_reported = iv ~= nil and iv.reported == true
        ''')
        g = lua.globals()

        self.assertIs(g.wait_ok, True, g.wait_err)
        self.assertEqual(g.waiting_heap, 0,
                         "waiting inactive updates must not read Lua heap")
        self.assertIs(g.activation_ok, True, g.activation_err)
        self.assertIs(g.active_after_event, True,
                      "the real native positive event must arm the mode")
        self.assertIs(g.baseline_ok, True, g.baseline_err)
        self.assertIs(g.baseline_active, True)
        self.assertIs(g.recorder_present, True,
                      "the first active sample must create p.kingpin_intervals")
        self.assertIs(g.meter_hidden, True,
                      "positive native ability_meter lease must stay hidden")
        self.assertIs(g.icon_hidden, True,
                      "positive native ability_icon lease must stay hidden")
        self.assertIs(g.equipment_verified, True,
                      "owned equipment must stay certified during capture")

        self.assertIs(g.publish_ok, True, g.publish_err)
        self.assertIs(g.gap_ok, True, g.gap_err)
        self.assertEqual(g.published_count, 1)
        self.assertEqual(g.published_events, 1)
        self.assertEqual(g.published_heap_drop_count, 1)
        self._assert_number(g.published_heap_drop_kb, 64,
                            msg="net heap drop must be 64 KB")
        self._assert_number(g.published_max_gap_ms, 40,
                            msg="the published interval t-gap is 40 ms")
        self._assert_number(g.published_max_gap_clock_ms, 4,
                            msg="the same interval elapsed delta is 4 ms")
        self._assert_number(g.published_max_gap_heap_delta_kb, -64,
                            msg="the same interval net Lua heap delta is -64 KB")

        self.assertIs(g.terminal_event_ok, True, g.terminal_event_err)
        self.assertIs(g.terminal_ok, True, g.terminal_err)
        self.assertEqual(g.terminal_count, 1,
                         "a terminal event delta must fill the terminal bin")
        self.assertIs(g.noevent_ok, True, g.noevent_err)
        self.assertEqual(g.no_publication_count, 1,
                         "an interval without terminal/publication is "
                         "no_publication, not proof of inactivity")

        self.assertIs(g.finish_ok, True, g.finish_err)
        self.assertIs(g.finish_done, True)
        self.assertIs(g.finish_active, False)
        self.assertIs(g.reported, True)
        self.assertEqual(g.interval_report_count, 4,
                         "finish must emit three bin rows plus one meta line")
        report = str(g.interval_report_text).lower()
        for token in ("published", "terminal", "no_publication"):
            self.assertIn(token, report,
                          "the finish report must carry all three bin rows")
        for token in ("heap", "elapsed", "gpu"):
            self.assertIn(token, report,
                          "the finish report must state Lua heap, elapsed and "
                          "non-GPU disclaimers")

        self.assertIs(g.late_event_ok, True, g.late_event_err)
        self.assertIs(g.late_update_ok, True, g.late_update_err)
        self.assertIs(g.late_done, True)
        self.assertIs(g.late_reported, True)
        self.assertEqual(g.late_heap, g.after_finish_heap,
                         "no heap read after the single finish report")
        self.assertEqual(g.late_logs, g.after_finish_logs,
                         "no log after the single finish report")

    def test_off_waiting_and_capped_paths_never_sample_heap(self):
        off = kingpin_lua()
        off.execute(INSTALL_INTERVAL_DOUBLES)
        off.execute(r'''
            local RT, mgr = _R, _m
            local update_ok, update_err = pcall(function()
                RT:update(mgr, 10, .05)
            end)
            local activation_ok, activation_err = pcall(function()
                mgr:set_player_ability_radial({current = 6, total = 6})
            end)
            local after_ok, after_err = pcall(function()
                RT:update(mgr, 11, .05)
            end)
            off_ok = update_ok and activation_ok and after_ok
            off_err = tostring(update_err or activation_err or after_err or "")
            off_heap = _heap_reads
        ''')
        g = off.globals()
        self.assertIs(g.off_ok, True, g.off_err)
        self.assertEqual(g.off_heap, 0,
                         "without the sentinel no heap may be sampled")

        lua = _kingpin_probe_lua()
        lua.execute(INSTALL_INTERVAL_DOUBLES)
        lua.execute(r'''
            local RT, mgr = _R, _m
            local p = RT._residual_probe

            mount_ok, mount_err = pcall(function()
                RT:update(mgr, 1, .05)
            end)
            wait_ok, wait_err = pcall(function()
                for i = 0, 50 do
                    RT:_residual_tick(2 + i * .001)
                end
            end)
            waiting_heap = _heap_reads
            waiting_active = p and p.active == true

            activation_ok, activation_err = pcall(function()
                mgr:set_player_ability_radial({current = 6, total = 6})
            end)
            activation_heap = _heap_reads
            active_after_event = p and p.active == true
            local start_t = p and p.last_t

            loop_ok, loop_err = pcall(function()
                for i = 1, 4096 do
                    RT:_residual_tick(start_t + i * .001)
                end
            end)

            local iv = p and p.kingpin_intervals
            recorder_present = type(iv) == "table"
            attempts = iv and iv.attempts
            capped = iv ~= nil and iv.capped == true
            local bins = iv and iv.bins
            published_count = (bins and bins.published
                and bins.published.count) or 0
            terminal_count = (bins and bins.terminal
                and bins.terminal.count) or 0
            no_publication_count = (bins and bins.no_publication
                and bins.no_publication.count) or 0
            bins_sum = published_count + terminal_count + no_publication_count
            heap_after_loop = _heap_reads

            extra_ok, extra_err = pcall(function()
                RT:_residual_tick(start_t + 4097 * .001)
            end)
            attempts_after_extra = iv and iv.attempts
            heap_after_extra = _heap_reads

            local capture_start = p and p.capture_start
            finish_ok, finish_err = pcall(function()
                RT:_residual_tick(capture_start + 20.1)
            end)
            local iv2 = p and p.kingpin_intervals
            reported = iv2 ~= nil and iv2.reported == true
            done = p and p.done == true
            attempts_after_finish = iv2 and iv2.attempts

            local reports, text = 0, ""
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][KingpinIntervals]", 1, true) then
                    reports = reports + 1
                    text = text .. message .. "\n"
                end
            end
            finish_report_count = reports
            finish_report_text = text
            heap_after_finish = _heap_reads
            logs_after_finish = #log_texts

            later_ok, later_err = pcall(function()
                RT:_residual_tick(capture_start + 21)
            end)
            later_heap = _heap_reads
            later_logs = #log_texts
            later_reported = iv2 ~= nil and iv2.reported == true
        ''')
        g = lua.globals()

        self.assertIs(g.mount_ok, True, g.mount_err)
        self.assertIs(g.wait_ok, True, g.wait_err)
        self.assertIs(g.waiting_active, False)
        self.assertEqual(g.waiting_heap, 0,
                         "waiting ticks must not sample historical heap")
        self.assertIs(g.activation_ok, True, g.activation_err)
        self.assertIs(g.active_after_event, True)
        self.assertEqual(g.activation_heap, 0,
                         "the native event itself must not sample heap")
        self.assertIs(g.loop_ok, True, g.loop_err)
        self.assertIs(g.recorder_present, True,
                      "the recorder must exist once active sampling starts")
        self.assertEqual(g.attempts, 4096)
        self.assertIs(g.capped, True)
        self.assertEqual(g.heap_after_loop, 4096,
                         "one protected heap read per attempt, never a force GC")
        self.assertEqual(g.bins_sum, 4095,
                         "the baseline attempt is excluded from the bins")
        self.assertIs(g.extra_ok, True, g.extra_err)
        self.assertEqual(g.attempts_after_extra, 4096,
                         "a capped recorder must not iterate attempts")
        self.assertEqual(g.heap_after_extra, 4096,
                         "a capped recorder must not sample heap")
        self.assertIs(g.finish_ok, True, g.finish_err)
        self.assertIs(g.done, True)
        self.assertIs(g.reported, True)
        self.assertGreaterEqual(g.finish_report_count, 1)
        self.assertLessEqual(g.finish_report_count, 4,
                             "finish emits at most 4 KingpinIntervals lines")
        report = str(g.finish_report_text).lower()
        for token in ("published", "terminal", "no_publication"):
            self.assertIn(token, report)
        self.assertEqual(g.attempts_after_finish, 4096)
        self.assertIs(g.later_ok, True, g.later_err)
        self.assertIs(g.later_reported, True)
        self.assertEqual(g.later_heap, g.heap_after_finish,
                         "no heap read after the finish report")
        self.assertEqual(g.later_logs, g.logs_after_finish,
                         "no log after the finish report")

    def test_phase_deltas_match_recorded_interval_and_max_gap(self):
        lua = _kingpin_probe_lua()
        lua.execute(INSTALL_INTERVAL_DOUBLES)
        lua.execute(r'''
            _interval_clock = 0
            os.clock = function()
                _interval_clock_reads = _interval_clock_reads + 1
                _interval_clock = _interval_clock + .0001
                return _interval_clock
            end
        ''')
        lua.execute(r'''
            local RT, mgr = _R, _m
            local p = RT._residual_probe
            local names = {"runtime", "prepare", "chain", "priority",
                           "post", "final"}

            local function phase_totals()
                local phases = p and p.phases or {}
                local totals = {}
                for _, name in ipairs(names) do
                    local key = name == "runtime" and "runtime"
                        or ("kingpin_event_" .. name)
                    local phase = phases[key]
                    if not phase then
                        error("missing phase table: " .. key)
                    end
                    totals[name] = phase.sum
                end
                return totals
            end

            phase_before = {}
            wait_ok, wait_err = pcall(function()
                RT:update(mgr, 100, .05)
                mgr:set_player_ability_radial({current = 6, total = 6})
                phase_before = phase_totals()
            end)

            baseline_ok, baseline_err = pcall(function()
                RT:update(mgr, 100.01, .05)
            end)

            phase_current = {}
            publish_ok, publish_err = pcall(function()
                mgr:set_player_ability_radial({current = 5.9, total = 6})
                local snapshot = phase_totals()
                for _, name in ipairs(names) do
                    phase_current[name] = snapshot[name]
                end
            end)

            gap_ok, gap_err = pcall(function()
                RT:update(mgr, 100.05, .05)
            end)

            local pub = p and p.kingpin_intervals and p.kingpin_intervals.bins
                and p.kingpin_intervals.bins.published
            phase_ms = {}
            max_gap_ms = {}
            for _, name in ipairs(names) do
                phase_ms[name] = pub and pub[name .. "_ms"]
                max_gap_ms[name] = pub and pub["max_gap_" .. name .. "_ms"]
            end
            phase_expected = {}
            local stable_skipped = {priority = true, post = true, final = true}
            phase_all_positive = true
            for _, name in ipairs(names) do
                local expected = 1000 * (phase_current[name]
                    - phase_before[name])
                phase_expected[name] = expected
                if not stable_skipped[name] and not (expected > 0) then
                    phase_all_positive = false
                end
            end
            priority_zero = phase_expected.priority ~= nil
                and math.abs(phase_expected.priority) < 1e-9
            post_zero = phase_expected.post ~= nil
                and math.abs(phase_expected.post) < 1e-9
            final_zero = phase_expected.final ~= nil
                and math.abs(phase_expected.final) < 1e-9
        ''')
        g = lua.globals()

        self.assertIs(g.wait_ok, True, g.wait_err)
        self.assertIs(g.baseline_ok, True, g.baseline_err)
        self.assertIs(g.publish_ok, True, g.publish_err)
        self.assertIs(g.gap_ok, True, g.gap_err)
        self.assertIs(g.phase_all_positive, True,
                      "every runtime/prepare/chain phase delta must be "
                      "strictly positive")
        self.assertIs(g.priority_zero, True,
                      "a stable continuation must leave the priority phase "
                      "delta at zero")
        self.assertIs(g.post_zero, True,
                      "a stable continuation must leave the post phase "
                      "delta at zero")
        self.assertIs(g.final_zero, True,
                      "a stable continuation must leave the final phase "
                      "delta at zero")
        for name in ("runtime", "prepare", "chain", "priority", "post",
                     "final"):
            self._assert_number(
                g.phase_ms[name], g.phase_expected[name],
                msg=f"{name}_ms must equal 1000*phase delta")
            if name in ("priority", "post", "final"):
                self.assertEqual(float(g.phase_expected[name]), 0.0,
                                 f"{name} phase must not advance on a stable "
                                 "continuation")
                self.assertEqual(float(g.phase_ms[name]), 0.0,
                                 f"{name}_ms must be zero")
                self.assertEqual(float(g.max_gap_ms[name]), 0.0,
                                 f"max_gap_{name}_ms must be zero")
            else:
                self.assertGreater(float(g.phase_expected[name]), 0,
                                   f"{name} phase must have advanced")
            self._assert_number(
                g.max_gap_ms[name], g.phase_ms[name],
                msg=f"max_gap_{name}_ms must match the same interval")

    def test_missing_clock_heap_and_abort_stay_bounded(self):
        lua = _kingpin_probe_lua()
        lua.execute(INSTALL_INTERVAL_DOUBLES)
        lua.execute(_ability_leases_lua())
        lua.execute(r'''
            local RT, mgr = _R, _m
            local p = RT._residual_probe

            mount_ok, mount_err = pcall(function()
                RT:update(mgr, 100, .05)
            end)
            activation_ok, activation_err = pcall(function()
                mgr:set_player_ability_radial({current = 6, total = 6})
            end)
            baseline_ok, baseline_err = pcall(function()
                RT:update(mgr, 100.01, .05)
            end)
            baseline_active = p and p.active == true

            lease_before = ability_leases()
            meter_hidden_before = (_ability_meter:visible() == false)
            icon_hidden_before = (_ability_icon:visible() == false)
            equipment_verified_before = kyohud.hud.equipment ~= nil
                and kyohud.hud.equipment:verify() == true

            collectgarbage = function(mode, ...)
                if mode ~= "count" then
                    error("unexpected collectgarbage mode: "
                        .. tostring(mode))
                end
                _heap_reads = _heap_reads + 1
                error("heap read failure")
            end
            os.clock = function()
                _interval_clock_reads = _interval_clock_reads + 1
                return 0/0
            end

            publish_ok, publish_err = pcall(function()
                mgr:set_player_ability_radial({current = 5.9, total = 6})
            end)
            sample_ok, sample_err = pcall(function()
                RT:update(mgr, 100.05, .05)
            end)

            local iv = p and p.kingpin_intervals
            local pub = iv and iv.bins and iv.bins.published
            recorder_present = type(iv) == "table"
            published_count = pub and pub.count
            clock_missing = pub and pub.clock_missing
            heap_missing = pub and pub.heap_missing
            max_gap_ms = pub and pub.max_gap_ms
            max_gap_clock_is_nil = pub ~= nil
                and pub.max_gap_clock_ms == nil
            max_gap_heap_is_nil = pub ~= nil
                and pub.max_gap_heap_delta_kb == nil

            lease_after = ability_leases()
            meter_hidden_after = (_ability_meter:visible() == false)
            icon_hidden_after = (_ability_icon:visible() == false)
            equipment_verified_after = kyohud.hud.equipment ~= nil
                and kyohud.hud.equipment:verify() == true

            abort_ok, abort_err = pcall(function()
                RT:_residual_tick(100.0)
            end)
            abort_done = p and p.done == true
            local reports, text = 0, ""
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][KingpinIntervals]", 1, true) then
                    reports = reports + 1
                    text = text .. message .. "\n"
                end
            end
            abort_report_count = reports
            abort_report_text = text
            local iv_after = p and p.kingpin_intervals
            reported = iv_after ~= nil and iv_after.reported == true
            after_abort_heap = _heap_reads
            after_abort_logs = #log_texts

            later_ok, later_err = pcall(function()
                RT:_residual_tick(100.06)
                mgr:set_player_ability_radial({current = 6, total = 6})
                RT:update(mgr, 100.07, .05)
            end)
            later_heap = _heap_reads
            later_logs = #log_texts
        ''')
        g = lua.globals()

        self.assertIs(g.mount_ok, True, g.mount_err)
        self.assertIs(g.activation_ok, True, g.activation_err)
        self.assertIs(g.baseline_ok, True, g.baseline_err)
        self.assertIs(g.baseline_active, True)
        self.assertIs(g.recorder_present, True,
                      "the baseline must create p.kingpin_intervals")
        self.assertIs(g.publish_ok, True, g.publish_err)
        self.assertIs(g.sample_ok, True, g.sample_err)
        self.assertEqual(g.published_count, 1)
        self.assertEqual(g.clock_missing, 1,
                         "NaN os.clock must be missing, not coerced to zero")
        self.assertEqual(g.heap_missing, 1,
                         "a throwing collectgarbage must be missing")
        self._assert_number(g.max_gap_ms, 40,
                            msg="the known t-gap must still be retained")
        self.assertIs(g.max_gap_clock_is_nil, True,
                      "missing elapsed must not fabricate a zero maximum")
        self.assertIs(g.max_gap_heap_is_nil, True,
                      "missing heap must not fabricate a zero maximum")

        self.assertEqual(g.lease_before, g.lease_after,
                         "positive native leases must be unchanged")
        self.assertIs(g.meter_hidden_before, True)
        self.assertIs(g.icon_hidden_before, True)
        self.assertIs(g.meter_hidden_after, True)
        self.assertIs(g.icon_hidden_after, True)
        self.assertIs(g.equipment_verified_before, True)
        self.assertIs(g.equipment_verified_after, True)

        self.assertIs(g.abort_ok, True, g.abort_err)
        self.assertIs(g.abort_done, True)
        self.assertIs(g.reported, True)
        self.assertGreaterEqual(g.abort_report_count, 1)
        self.assertLessEqual(g.abort_report_count, 4,
                             "abort emits at most 4 KingpinIntervals lines")
        self.assertIs(g.later_ok, True, g.later_err)
        self.assertEqual(g.later_heap, g.after_abort_heap,
                         "an aborted recorder must not read heap later")
        self.assertEqual(g.later_logs, g.after_abort_logs,
                         "an aborted recorder must not log later")


if __name__ == "__main__":
    unittest.main()
