"""Opt-in runtime residual profiling: sentinel gate, one capture, permanent stop.

Coverage:
1. No sentinel: the probe must not exist and ordinary R:update frames must not
   read the diagnostic clock or log anything.
2. Sentinel present at runtime chunk load: io.open is exercised exactly once,
   the probe exposes the documented methods, a live player warms up for 5 game
   seconds, a 20 game second capture produces exactly one
   [KyoHUD][ResidualProbe] report with non-zero assault/alerts phase counts,
   and every later frame performs no diagnostic clock read and no log.
3. A missing live player during warmup waits without diagnostics until a live
   player is restored and warms up for five game seconds.
4. Invalid/backward warmup time resets the warmup; active backward time aborts
   permanently with one protected log and no later diagnostic activity.
5. Missing, throwing, NaN, infinite, backward and flat os.clock values keep
   ordinary updates running, never yield negative/non-finite phase values, and
   zero runtime timing is labeled inconclusive.
6. A throwing probe logger is contained on completion and abort paths.
7. Foundation disabled before capture resets warmup; enabling it later starts a
   normal warmup and capture, and completion is not re-armed.

The fixture is the real local H5 runtime stack from
test_hud_local_h5_lifecycle._local_runtime. The runtime chunk is re-executed in
the same Lua VM only after the fixture is built, with a Lua io.open override
that recognises ModPath .. 'KYO_RESIDUAL_PERF' and delegates ordinary file reads.
That re-execution is test setup; production is expected to read the sentinel
once per chunk load.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_local_h5_lifecycle import _local_runtime

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_PATH = ROOT / "lua" / "hud" / "runtime.lua"

SENTINEL_INSTALL = r'''
    _real_io_open = io.open
    _real_io_close = io.close
    _sentinel_handle = nil
    _sentinel_opens = 0
    _sentinel_closes = 0
    io.open = function(path, mode)
        if path == ModPath .. "KYO_RESIDUAL_PERF" then
            _sentinel_opens = _sentinel_opens + 1
            local handle = {
                close = function(self)
                    _sentinel_closes = _sentinel_closes + 1
                    return true
                end,
            }
            _sentinel_handle = handle
            return handle
        end
        return _real_io_open(path, mode)
    end
    io.close = function(handle)
        if handle ~= nil and handle == _sentinel_handle then
            _sentinel_closes = _sentinel_closes + 1
            return true
        end
        return _real_io_close(handle)
    end
    _saved_required_script = RequiredScript
    RequiredScript = "kyohud_residual_probe_test"
'''

SENTINEL_RESTORE = r'''
    io.open = _real_io_open
    io.close = _real_io_close
    RequiredScript = _saved_required_script
'''

INSTALL_CLOCK_AND_LOG_COUNTERS = r'''
    local real_clock = os.clock
    clock_reads = 0
    os.clock = function()
        clock_reads = clock_reads + 1
        return real_clock()
    end
    local real_log = log
    log_texts = {}
    log = function(message, ...)
        log_texts[#log_texts + 1] = tostring(message)
        return real_log(message, ...)
    end
'''


def _rearm_with_sentinel(lua):
    """Re-execute the real runtime chunk once with the sentinel fake installed."""
    lua.execute(SENTINEL_INSTALL)
    try:
        lua.execute(RUNTIME_PATH.read_text(encoding="utf-8-sig"))
    finally:
        lua.execute(SENTINEL_RESTORE)


def _positive_baseline(testcase, lua):
    lua.execute(r'''
        baseline_verify = (kyohud.hud.crew ~= nil)
            and (kyohud.hud.crew:_verify_render() == true)
        baseline_player_root = kyohud.hud.player._root
        baseline_weapons_root = kyohud.hud.weapons._root
        baseline_crew_root = kyohud.hud.crew._root
    ''')
    testcase.assertIs(lua.globals().baseline_verify, True,
                      "positive source baseline must render before diagnostics")


def _roots_preserved(testcase, lua):
    lua.execute(r'''
        roots_preserved = (baseline_player_root ~= nil)
            and (kyohud.hud.player._root == baseline_player_root)
            and (kyohud.hud.weapons._root == baseline_weapons_root)
            and (kyohud.hud.crew._root == baseline_crew_root)
    ''')
    testcase.assertIs(lua.globals().roots_preserved, True,
                      "diagnostic scenarios must not change owned module roots")


class ResidualProbeGateTests(unittest.TestCase):
    def test_absent_sentinel_has_no_probe_and_no_diagnostic_calls(self):
        """No sentinel file: no probe, no os.clock read, no log during R:update."""
        lua = _local_runtime()
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local mgr = managers.hud
            probe_is_nil = (RT._residual_probe == nil)
            local last = RT._last_recovery_time
            if type(last) ~= "number" or last ~= last then last = 1.1 end
            update_ok, update_err = pcall(function()
                for i = 1, 4 do
                    RT:update(mgr, last + i, .05)
                end
            end)
            update_error = tostring(update_err or "")
            clock_reads_after = clock_reads
            log_count_after = #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.probe_is_nil, True,
                      "without the sentinel, kyohud.hud.runtime._residual_probe must be nil")
        self.assertIs(g.update_ok, True,
                      f"ordinary R:update must succeed: {g.update_error}")
        self.assertEqual(g.clock_reads_after, 0,
                         "disabled profiling must not read os.clock during ordinary updates")
        self.assertEqual(g.log_count_after, 0,
                         "disabled profiling must not log during ordinary updates")

    def test_armed_sentinel_captures_once_with_named_phases_then_stops(self):
        """Sentinel at chunk load: one warmup, one report, then permanent silence."""
        lua = _local_runtime()
        _rearm_with_sentinel(lua)

        g = lua.globals()
        self.assertEqual(g._sentinel_opens, 1,
                         "the runtime chunk must open the sentinel exactly once")
        self.assertEqual(g._sentinel_closes, 1,
                         "the runtime chunk must close the sentinel immediately")

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local p = RT._residual_probe
            probe_is_table = (type(p) == "table")
            tick_is_function = (type(RT._residual_tick) == "function")
            stamp_is_function = (type(RT._residual_stamp) == "function")
            record_is_function = (type(RT._residual_record) == "function")
            probe_active_initial = p and p.active
            probe_done_initial = p and p.done
            probe_phases_table = p and (type(p.phases) == "table")
        ''')
        g = lua.globals()
        self.assertIs(g.probe_is_table, True,
                      "armed sentinel must create kyohud.hud.runtime._residual_probe")
        self.assertIs(g.tick_is_function, True,
                      "RT:_residual_tick must be exposed")
        self.assertIs(g.stamp_is_function, True,
                      "RT:_residual_stamp must be exposed")
        self.assertIs(g.record_is_function, True,
                      "RT:_residual_record must be exposed")
        self.assertIs(g.probe_active_initial, False,
                      "the armed probe must start inactive")
        self.assertIs(g.probe_done_initial, False,
                      "the armed probe must start unfinished")
        self.assertIs(g.probe_phases_table, True,
                      "the armed probe must expose a phases table")

        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local mgr = managers.hud
            local p = RT._residual_probe
            update_ok, update_err = pcall(function()
                RT:update(mgr, 2, .05)
                local t = 7.1
                while t <= 27.1 + 1e-9 do
                    RT:update(mgr, t, .05)
                    t = t + 1
                end
                RT:update(mgr, 27.2, .05)
            end)
            update_error = tostring(update_err or "")
            capture_done = p and (p.done == true)
            capture_inactive = p and (p.active == false)

            local reports = 0
            local report_text = ""
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                    reports = reports + 1
                    report_text = message
                end
            end
            probe_report_count = reports
            probe_report_text = report_text

            local assault = p and p.phases and p.phases.assault
            local alerts = p and p.phases and p.phases.alerts
            assault_count = assault and assault.count
            alerts_count = alerts and alerts.count
            phase_shape_ok = (type(assault) == "table") and (type(alerts) == "table")
                and (type(assault.count) == "number")
                and (type(assault.sum) == "number")
                and (type(assault.max) == "number")
                and (type(alerts.count) == "number")
                and (type(alerts.sum) == "number")
                and (type(alerts.max) == "number")

            clock_after_capture = clock_reads
            log_after_capture = #log_texts
            stop_ok, stop_err = pcall(function()
                RT:update(mgr, 28.2, .05)
            end)
            stop_error = tostring(stop_err or "")
            clock_after_stop = clock_reads
            log_after_stop = #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.update_ok, True,
                      f"capture frames must run through genuine R:update: {g.update_error}")
        self.assertIs(g.capture_done, True,
                      "the probe must finish after 20 game seconds of capture")
        self.assertTrue(bool(g.capture_inactive),
                        "the probe must be inactive once capture is complete")
        self.assertEqual(g.probe_report_count, 1,
                         "exactly one [KyoHUD][ResidualProbe] report must be emitted")
        self.assertIn("[KyoHUD][ResidualProbe]", str(g.probe_report_text),
                      "the single report must carry the ResidualProbe prefix")
        self.assertIn("HUD intervals, not GPU; os.clock quantized; runtime inclusive",
                      str(g.probe_report_text),
                      "the report must label its measurement limits explicitly")
        self.assertIs(g.phase_shape_ok, True,
                      "assault/alerts phase records must expose numeric count/sum/max")
        self.assertGreater(float(g.assault_count), 0.0,
                           "genuine R:update must record the assault coordinate phase")
        self.assertGreater(float(g.alerts_count), 0.0,
                           "genuine R:update must record the alerts coordinate phase")
        self.assertIs(g.stop_ok, True,
                      f"post-capture R:update must still succeed: {g.stop_error}")
        self.assertEqual(g.clock_after_stop, g.clock_after_capture,
                         "no diagnostic os.clock read may occur after the capture")
        self.assertEqual(g.log_after_stop, g.log_after_capture,
                         "no report or diagnostic log may occur after the capture")

    def test_no_live_player_waits_then_warmup_activates(self):
        """No live player blocks warmup without diagnostics; restoring it arms."""
        lua = _local_runtime()
        _positive_baseline(self, lua)
        _rearm_with_sentinel(lua)
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            _saved_player_unit = managers.player.player_unit
            managers.player.player_unit = function(self) return nil end
            local ok, err = pcall(function()
                for i = 0, 3 do RT:update(managers.hud, 2 + i, .05) end
            end)
            wait_update_ok = ok
            wait_update_err = tostring(err or "")
            wait_active = RT._residual_probe.active == true
            wait_done = RT._residual_probe.done == true
            wait_clock_reads = clock_reads
            wait_log_count = #log_texts

            managers.player.player_unit = _saved_player_unit
            local ok2, err2 = pcall(function()
                RT:update(managers.hud, 10, .05)
                RT:update(managers.hud, 15.1, .05)
            end)
            restore_update_ok = ok2
            restore_update_err = tostring(err2 or "")
            restored_active = RT._residual_probe.active == true
            restored_clock_reads = clock_reads
        ''')
        g = lua.globals()
        self.assertIs(g.wait_update_ok, True,
                      f"no-player updates must continue: {g.wait_update_err}")
        self.assertIs(g.wait_active, False,
                      "a missing live player must not activate the probe")
        self.assertIs(g.wait_done, False,
                      "a missing live player during warmup must not finish the probe")
        self.assertEqual(g.wait_clock_reads, 0,
                         "warmup without a live player must not read os.clock")
        self.assertEqual(g.wait_log_count, 0,
                         "warmup without a live player must not log")
        self.assertIs(g.restore_update_ok, True,
                      f"restored-player updates must continue: {g.restore_update_err}")
        self.assertIs(g.restored_active, True,
                      "restoring the live player and warming 5s must activate capture")
        self.assertGreater(int(g.restored_clock_reads), 0,
                           "an active capture must attempt the diagnostic clock")
        _roots_preserved(self, lua)

    def test_warmup_reset_and_active_backward_t_abort_permanently(self):
        """Invalid/backward warmup restarts; active backward t aborts once."""
        lua = _local_runtime()
        _positive_baseline(self, lua)
        _rearm_with_sentinel(lua)
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local probe = RT._residual_probe
            RT:_residual_tick(2)
            RT:_residual_tick(4)
            RT:_residual_tick(0/0)
            RT:_residual_tick(3)
            RT:_residual_tick(4)
            RT:_residual_tick(3.5)
            RT:_residual_tick(8.3)
            warm_reset_active = probe.active == true
            RT:_residual_tick(8.6)
            active_before_abort = probe.active == true

            local ok, err = pcall(function()
                RT:update(managers.hud, 8.0, .05)
            end)
            abort_update_ok = ok
            abort_update_err = tostring(err or "")
            abort_done = probe.done == true
            abort_active = probe.active == true
            abort_flag = probe.aborted == true
            local reports = 0
            local aborted_text = ""
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                    reports = reports + 1
                    aborted_text = message
                end
            end
            abort_report_count = reports
            abort_report_text = aborted_text
            abort_clock_reads = clock_reads
            abort_log_count = #log_texts

            local ok2, err2 = pcall(function()
                RT:update(managers.hud, 9.0, .05)
                RT:update(managers.hud, 10.0, .05)
            end)
            later_update_ok = ok2
            later_update_err = tostring(err2 or "")
            later_clock_reads = clock_reads
            later_log_count = #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.warm_reset_active, False,
                      "backward warmup time must reset the 5s warmup window")
        self.assertIs(g.active_before_abort, True,
                      "the fresh 5s warmup must arm capture")
        self.assertIs(g.abort_update_ok, True,
                      f"the abort frame must still run: {g.abort_update_err}")
        self.assertIs(g.abort_done, True,
                      "an active backward t must finish the probe permanently")
        self.assertIs(g.abort_active, False,
                      "an aborted probe must be inactive")
        self.assertIs(g.abort_flag, True,
                      "an active backward t must mark the probe aborted")
        self.assertEqual(g.abort_report_count, 1,
                         "an abort must produce exactly one protected log")
        self.assertIn("aborted", str(g.abort_report_text).lower(),
                      "the single abort log must be the ResidualProbe abort line")
        self.assertEqual(g.later_clock_reads, g.abort_clock_reads,
                         "no diagnostic clock read may occur after an abort")
        self.assertEqual(g.later_log_count, g.abort_log_count,
                         "no further log may occur after an abort")
        self.assertIs(g.later_update_ok, True,
                      f"later updates must continue after abort: {g.later_update_err}")
        _roots_preserved(self, lua)

    def test_broken_clock_table_stays_safe_and_inconclusive(self):
        """nil/throw/NaN/infinity/backward/flat clocks never break updates."""
        cases = {
            "nil": "os.clock = nil; clock_attempts = 0",
            "throw": ("clock_attempts = 0; os.clock = function() "
                      "clock_attempts = clock_attempts + 1; error('clock fail') end"),
            "nan": ("clock_attempts = 0; os.clock = function() "
                    "clock_attempts = clock_attempts + 1; return 0/0 end"),
            "infinity": ("clock_attempts = 0; os.clock = function() "
                         "clock_attempts = clock_attempts + 1; return math.huge end"),
            "backward": ("clock_attempts = 0; clock_value = 1000000; "
                         "os.clock = function() clock_attempts = clock_attempts + 1; "
                         "clock_value = clock_value - 5; return clock_value end"),
            "flat": ("clock_attempts = 0; os.clock = function() "
                     "clock_attempts = clock_attempts + 1; return 0 end"),
        }
        for name, setup in cases.items():
            with self.subTest(clock=name):
                lua = _local_runtime()
                _positive_baseline(self, lua)
                _rearm_with_sentinel(lua)
                lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
                lua.execute(setup)
                lua.execute(r'''
                    local RT = kyohud.hud.runtime
                    local ok, err = pcall(function()
                        RT:update(managers.hud, 2, .05)
                        local t = 7.1
                        while t <= 27.1 + 1e-9 do
                            RT:update(managers.hud, t, .05)
                            t = t + 1
                        end
                        RT:update(managers.hud, 27.2, .05)
                    end)
                    broken_update_ok = ok
                    broken_update_err = tostring(err or "")
                    broken_done = RT._residual_probe.done == true
                    broken_phases_ok = true
                    for _, phase_name in ipairs({"alerts", "assault", "player",
                        "weapons", "equipment", "crew", "harmony",
                        "objectives_anim", "recovery", "runtime"}) do
                        local record = RT._residual_probe.phases[phase_name]
                        if type(record) ~= "table"
                            or type(record.count) ~= "number"
                            or type(record.sum) ~= "number"
                            or type(record.max) ~= "number"
                            or record.count < 0
                            or record.sum < 0 or record.max < 0
                            or record.sum ~= record.sum or record.max ~= record.max
                            or record.sum == math.huge or record.sum == -math.huge
                            or record.max == math.huge or record.max == -math.huge then
                            broken_phases_ok = false
                        end
                    end
                    local reports = 0
                    local text = ""
                    for _, message in ipairs(log_texts) do
                        if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                            reports = reports + 1
                            text = message
                        end
                    end
                    broken_report_count = reports
                    broken_inconclusive = text:find("timing inconclusive", 1, true) ~= nil
                    broken_clock_after_capture = clock_attempts
                    broken_logs_after_capture = #log_texts
                    local stop_ok, stop_err = pcall(function()
                        RT:update(managers.hud, 28.2, .05)
                    end)
                    broken_stop_ok = stop_ok
                    broken_stop_err = tostring(stop_err or "")
                    broken_clock_after_stop = clock_attempts
                    broken_logs_after_stop = #log_texts
                ''')
                g = lua.globals()
                self.assertIs(g.broken_update_ok, True,
                              f"{name}: updates must continue: {g.broken_update_err}")
                self.assertIs(g.broken_done, True,
                              f"{name}: capture must complete")
                self.assertIs(g.broken_phases_ok, True,
                              f"{name}: phase sum/max must stay finite and non-negative")
                self.assertEqual(g.broken_report_count, 1,
                                 f"{name}: exactly one summary must be emitted")
                self.assertIs(g.broken_inconclusive, True,
                              f"{name}: zero runtime timing must be labeled inconclusive")
                self.assertIs(g.broken_stop_ok, True,
                              f"{name}: post-capture update must continue: {g.broken_stop_err}")
                self.assertEqual(g.broken_clock_after_stop, g.broken_clock_after_capture,
                                 f"{name}: no clock attempt after capture")
                self.assertEqual(g.broken_logs_after_stop, g.broken_logs_after_capture,
                                 f"{name}: no log after capture")
                if name != "nil":
                    self.assertGreater(int(g.broken_clock_after_capture), 0,
                                       f"{name}: diagnostic clock must have been attempted")
                _roots_preserved(self, lua)

    def test_throwing_logger_never_escapes_completion_or_abort(self):
        """A throwing probe logger is contained on summary and abort paths."""
        for scenario in ("completion", "player_loss_abort"):
            with self.subTest(scenario=scenario):
                lua = _local_runtime()
                _positive_baseline(self, lua)
                _rearm_with_sentinel(lua)
                lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
                lua.execute(r'''
                    _probe_log_attempts = 0
                    local _delegated_log = log
                    log = function(message, ...)
                        if type(message) == "string"
                            and message:find("[KyoHUD][ResidualProbe]", 1, true) then
                            _probe_log_attempts = _probe_log_attempts + 1
                            error("logger failure")
                        end
                        return _delegated_log(message, ...)
                    end
                ''')
                if scenario == "completion":
                    lua.execute(r'''
                        local RT = kyohud.hud.runtime
                        local ok, err = pcall(function()
                            RT:update(managers.hud, 2, .05)
                            local t = 7.1
                            while t <= 27.1 + 1e-9 do
                                RT:update(managers.hud, t, .05)
                                t = t + 1
                            end
                            RT:update(managers.hud, 27.2, .05)
                        end)
                        logger_update_ok = ok
                        logger_update_err = tostring(err or "")
                        logger_done = RT._residual_probe.done == true
                        logger_attempts_after = _probe_log_attempts
                        logger_clock_after = clock_reads
                        logger_logs_after = #log_texts
                        local stop_ok, stop_err = pcall(function()
                            RT:update(managers.hud, 28.2, .05)
                        end)
                        logger_stop_ok = stop_ok
                        logger_stop_err = tostring(stop_err or "")
                        logger_clock_after_stop = clock_reads
                        logger_attempts_after_stop = _probe_log_attempts
                    ''')
                else:
                    lua.execute(r'''
                        local RT = kyohud.hud.runtime
                        local warm_ok, warm_err = pcall(function()
                            RT:update(managers.hud, 2, .05)
                            RT:update(managers.hud, 7.1, .05)
                        end)
                        logger_warm_ok = warm_ok
                        logger_warm_err = tostring(warm_err or "")
                        logger_armed = RT._residual_probe.active == true
                        managers.player.player_unit = function(self) return nil end
                        local ok, err = pcall(function()
                            RT:update(managers.hud, 8.1, .05)
                        end)
                        logger_update_ok = ok
                        logger_update_err = tostring(err or "")
                        logger_done = RT._residual_probe.done == true
                        logger_attempts_after = _probe_log_attempts
                        logger_clock_after = clock_reads
                        logger_logs_after = #log_texts
                        local stop_ok, stop_err = pcall(function()
                            RT:update(managers.hud, 9.1, .05)
                        end)
                        logger_stop_ok = stop_ok
                        logger_stop_err = tostring(stop_err or "")
                        logger_clock_after_stop = clock_reads
                        logger_attempts_after_stop = _probe_log_attempts
                    ''')
                g = lua.globals()
                if scenario == "player_loss_abort":
                    self.assertIs(g.logger_warm_ok, True,
                                  f"{scenario}: warmup must run: {g.logger_warm_err}")
                    self.assertIs(g.logger_armed, True,
                                  f"{scenario}: warmup must arm the probe")
                self.assertIs(g.logger_update_ok, True,
                              f"{scenario}: update must not propagate logger error: {g.logger_update_err}")
                self.assertIs(g.logger_done, True,
                              f"{scenario}: probe must stop after the event")
                self.assertGreaterEqual(int(g.logger_attempts_after), 1,
                                        f"{scenario}: the probe must attempt the log")
                self.assertEqual(g.logger_clock_after_stop, g.logger_clock_after,
                                 f"{scenario}: no diagnostic clock read after stop")
                self.assertEqual(g.logger_attempts_after_stop, g.logger_attempts_after,
                                 f"{scenario}: no further probe log attempt after stop")
                self.assertIs(g.logger_stop_ok, True,
                              f"{scenario}: later update must still run: {g.logger_stop_err}")
                _roots_preserved(self, lua)

    def test_foundation_disabled_warmup_resets_until_enabled(self):
        """Foundation disabled before capture resets warmup; enabling restarts it."""
        lua = _local_runtime()
        _positive_baseline(self, lua)
        _rearm_with_sentinel(lua)
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            kyohud.settings.enable_hud_foundation = false
            RT:_residual_tick(2)
            RT:_residual_tick(8)
            RT:_residual_tick(30)
            disabled_active = RT._residual_probe.active == true
            disabled_done = RT._residual_probe.done == true
            disabled_clock_reads = clock_reads
            disabled_log_count = #log_texts

            kyohud.settings.enable_hud_foundation = true
            local warm_ok, warm_err = pcall(function()
                RT:update(managers.hud, 31, .05)
                RT:update(managers.hud, 36.1, .05)
            end)
            warm_update_ok = warm_ok
            warm_update_err = tostring(warm_err or "")
            warm_active = RT._residual_probe.active == true
            warm_runtime_count = RT._residual_probe.phases.runtime.count
            warm_runtime_sum = RT._residual_probe.phases.runtime.sum

            local finish_ok, finish_err = pcall(function()
                RT:update(managers.hud, 56.2, .05)
            end)
            finish_update_ok = finish_ok
            finish_update_err = tostring(finish_err or "")
            finish_done = RT._residual_probe.done == true
            finish_active = RT._residual_probe.active == true
            local reports = 0
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                    reports = reports + 1
                end
            end
            finish_report_count = reports
            finish_clock_reads = clock_reads
            finish_log_count = #log_texts

            local later_ok, later_err = pcall(function()
                RT:update(managers.hud, 57.2, .05)
                RT:update(managers.hud, 58.2, .05)
            end)
            later_update_ok = later_ok
            later_update_err = tostring(later_err or "")
            later_done = RT._residual_probe.done == true
            later_active = RT._residual_probe.active == true
            local later_reports = 0
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                    later_reports = later_reports + 1
                end
            end
            later_report_count = later_reports
            later_clock_reads = clock_reads
            later_log_count = #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.disabled_active, False,
                      "foundation disabled before capture must keep the probe inactive")
        self.assertIs(g.disabled_done, False,
                      "foundation disabled before capture must not finish the probe")
        self.assertEqual(g.disabled_clock_reads, 0,
                         "foundation disabled before capture must not read os.clock")
        self.assertEqual(g.disabled_log_count, 0,
                         "foundation disabled before capture must not log")
        self.assertIs(g.warm_update_ok, True,
                      f"enabled foundation updates must run: {g.warm_update_err}")
        self.assertIs(g.warm_active, True,
                      "enabling foundation must allow a fresh 5s warmup to arm capture")
        self.assertGreater(int(g.warm_runtime_count), 0,
                           "an armed foundation frame must record the runtime phase")
        self.assertGreaterEqual(float(g.warm_runtime_sum), 0.0,
                                "the runtime phase must never report a negative sum")
        self.assertIs(g.finish_update_ok, True,
                      f"capture completion must run: {g.finish_update_err}")
        self.assertIs(g.finish_done, True,
                      "20s of enabled capture must finish the probe")
        self.assertIs(g.finish_active, False,
                      "a finished probe must be inactive")
        self.assertEqual(g.finish_report_count, 1,
                         "completion must emit exactly one ResidualProbe report")
        self.assertIs(g.later_update_ok, True,
                      f"later disabled-foundation updates must run: {g.later_update_err}")
        self.assertIs(g.later_done, True,
                      "a finished probe must not be re-armed")
        self.assertIs(g.later_active, False,
                      "a finished probe must stay inactive")
        self.assertEqual(g.later_report_count, 1,
                         "completion must not produce a second report")
        self.assertEqual(g.later_clock_reads, g.finish_clock_reads,
                         "no diagnostic clock read may occur after completion")
        self.assertEqual(g.later_log_count, g.finish_log_count,
                         "no log may occur after completion")
        _roots_preserved(self, lua)


if __name__ == "__main__":
    unittest.main()
