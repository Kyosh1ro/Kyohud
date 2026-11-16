"""Opt-in residual phase coverage for the harmony pass and combat draw.

The four harmony scopes are static wrappers around the genuine runtime methods
(_sync_delayed_replacement, _apply_native_priority,
_delayed_replacement_post_priority, _coordinate_h5_native_duplicates). Their
original bodies must stay untouched. combat_draw is covered at the real
KH:draw entry: the literal core chunk runs on the fixture KH table and the
probe must record active draw entries only.

The fixture is the real local H5 runtime stack and the sentinel-gated probe
helpers from test_hud_residual_probe, so this file adds no production
substitute: ordinary R:update frames run warmup and a full 20 game second
capture. The absent and completed cases must perform no diagnostic os.clock
read and no log.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_crew_online_disappearance import _online_disappearance_runtime
from test_hud_local_h5_lifecycle import _local_runtime
from test_hud_residual_probe import (
    INSTALL_CLOCK_AND_LOG_COUNTERS,
    _positive_baseline,
    _rearm_with_sentinel,
    _roots_preserved,
)

HARMONY_PHASES = (
    "harmony_delayed_sync",
    "harmony_priority",
    "harmony_delayed_post",
    "harmony_duplicates",
)
DRAW_PHASE = "combat_draw"


class HarmonyPhaseProbeTests(unittest.TestCase):
    def test_armed_harmony_and_combat_phases_report_then_stop(self):
        """Ordinary R:update capture must time every harmony scope, then stop."""
        lua = _local_runtime()
        _positive_baseline(self, lua)
        _rearm_with_sentinel(lua)
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local mgr = managers.hud
            local probe = RT._residual_probe
            probe_is_table = (type(probe) == "table")

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
            capture_done = probe ~= nil and probe.done == true
            capture_inactive = probe ~= nil and probe.active == false

            local function count_of(name)
                local record = probe and probe.phases and probe.phases[name]
                if type(record) ~= "table" then return -1 end
                return record.count
            end
            delayed_sync_count = count_of("harmony_delayed_sync")
            priority_count = count_of("harmony_priority")
            delayed_post_count = count_of("harmony_delayed_post")
            duplicates_count = count_of("harmony_duplicates")
            draw_count = count_of("combat_draw")

            phase_shape_ok = true
            for _, name in ipairs({"harmony_delayed_sync", "harmony_priority",
                "harmony_delayed_post", "harmony_duplicates", "combat_draw"}) do
                local record = probe and probe.phases and probe.phases[name]
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
        self.assertIs(g.probe_is_table, True,
                      "armed sentinel must create the residual probe")
        self.assertIs(g.update_ok, True,
                      f"capture frames must run through genuine R:update: {g.update_error}")
        self.assertIs(g.capture_done, True,
                      "20 game seconds of capture must finish the probe")
        self.assertTrue(bool(g.capture_inactive),
                        "a completed probe must be inactive")
        self.assertIs(g.phase_shape_ok, True,
                      "harmony/combat phase records must expose finite non-negative count/sum/max")

        for name, count_attr in (
            ("harmony_delayed_sync", "delayed_sync_count"),
            ("harmony_priority", "priority_count"),
            ("harmony_delayed_post", "delayed_post_count"),
            ("harmony_duplicates", "duplicates_count"),
        ):
            self.assertGreater(
                int(getattr(g, count_attr)), 0,
                f"genuine R:update capture must record {name}")
        self.assertGreaterEqual(
            int(g.draw_count), 0,
            "combat_draw must exist and may stay zero until the core wrapper pass")

        self.assertEqual(g.probe_report_count, 1,
                         "exactly one [KyoHUD][ResidualProbe] report must be emitted")
        report_text = str(g.probe_report_text)
        self.assertIn("[KyoHUD][ResidualProbe]", report_text,
                      "the single report must carry the ResidualProbe prefix")
        for name in HARMONY_PHASES + (DRAW_PHASE,):
            self.assertIn(
                name, report_text,
                f"the single ResidualProbe report must name {name}")

        self.assertIs(g.stop_ok, True,
                      f"post-capture R:update must still succeed: {g.stop_error}")
        self.assertEqual(g.clock_after_stop, g.clock_after_capture,
                         "no diagnostic os.clock read may occur after completion")
        self.assertEqual(g.log_after_stop, g.log_after_capture,
                         "no report or diagnostic log may occur after completion")
        _roots_preserved(self, lua)

    def test_absent_sentinel_has_no_probe_and_no_diagnostic_calls(self):
        """No sentinel: no probe, no os.clock read and no log during R:update."""
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
                      "without the sentinel, the residual probe must be nil")
        self.assertIs(g.update_ok, True,
                      f"ordinary R:update must succeed: {g.update_error}")
        self.assertEqual(g.clock_reads_after, 0,
                         "disabled profiling must not read os.clock")
        self.assertEqual(g.log_count_after, 0,
                         "disabled profiling must not log")

    def test_combat_draw_entry_counts_only_while_probe_active(self):
        """Real KH:draw entry must record three calls, then stop silently.

        The literal lua/core.lua runs on the fixture KH table with
        kyohud._panel=nil, so the genuine KH:draw body returns at its first
        guard. The probe is warmed up and active before the diagnostic clock
        and log counters are installed. Three real kyohud:draw calls must add
        exactly three combat_draw records and read os.clock. Marking the probe
        done/inactive must make the next real draw read no clock and log
        nothing. This checks wrapper entry only; the full positive draw path is
        separate.
        """
        lua = _local_runtime()
        root = Path(__file__).resolve().parents[1]
        lua.execute("dofile = function() end")
        lua.execute((root / "lua" / "ky_buff_presentation.lua").read_text(
            encoding="utf-8-sig"))
        lua.execute((root / "lua" / "core.lua").read_text(
            encoding="utf-8-sig"))
        lua.execute("kyohud._panel = nil")
        _rearm_with_sentinel(lua)
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local mgr = managers.hud
            RT:update(mgr, 2, .05)
            RT:update(mgr, 7.1, .05)
            local probe = RT._residual_probe
            probe_active = (probe ~= nil) and (probe.active == true)
        ''')
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local probe = kyohud.hud.runtime._residual_probe
            draw_count_before = probe and probe.phases.combat_draw.count or -1
            draw_entry_ok = true
            draw_entry_error = ""
            for i = 1, 3 do
                local ok, err = pcall(function() kyohud:draw() end)
                if not ok then
                    draw_entry_ok = false
                    draw_entry_error = tostring(err or "")
                end
            end
            draw_count_after = probe and probe.phases.combat_draw.count or -1
            draw_count_delta = draw_count_after - draw_count_before
            clock_reads_after_draw = clock_reads
            log_count_after_draw = #log_texts

            probe.done = true
            probe.active = false
            clock_before_stop = clock_reads
            log_before_stop = #log_texts
            stop_draw_ok, stop_draw_err = pcall(function() kyohud:draw() end)
            stop_draw_error = tostring(stop_draw_err or "")
            clock_after_stop = clock_reads
            log_after_stop = #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.probe_active, True,
                      "the probe must be active before the draw calls")
        self.assertIs(g.draw_entry_ok, True,
                      f"real KH:draw must run: {g.draw_entry_error}")
        self.assertEqual(int(g.draw_count_before), 0,
                         "combat_draw must start at zero before the draw calls")
        self.assertEqual(int(g.draw_count_delta), 3,
                         "RED: three real kyohud:draw calls must record combat_draw")
        self.assertEqual(int(g.draw_count_after), 3,
                         "the real combat_draw phase must count exactly three entries")
        self.assertGreater(int(g.clock_reads_after_draw), 0,
                           "active draw entries must read the diagnostic clock")
        self.assertIs(g.stop_draw_ok, True,
                      f"a completed probe draw must still run: {g.stop_draw_error}")
        self.assertEqual(g.clock_after_stop, g.clock_before_stop,
                         "a completed probe draw must not read os.clock")
        self.assertEqual(g.log_after_stop, g.log_before_stop,
                         "a completed probe draw must not log")

    def test_positive_online_draw_records_and_bypasses_safely(self):
        """Real online-fixture draw records combat_draw, then bypasses safely.

        The existing online disappearance fixture already builds the real
        core/buff/killfeed stack and runs real draws. After a sentinel rearm,
        runtime advances monotonically from RT._last_recovery_time + 1 with a
        5.1s warmup before the diagnostic clock/log counters are installed.
        The real kyohud:draw must record a positive combat_draw phase and
        produce owned panel children. Missing runtime, stamp/record helpers and
        inactive probes must bypass with no clock/log. A real panel:clear error
        must propagate without recording; restoring the same panel getter must
        allow the next real draw to succeed.
        """
        lua = _online_disappearance_runtime(1920, 1080)
        _rearm_with_sentinel(lua)
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local mgr = managers.hud
            local base = RT._last_recovery_time
            if type(base) ~= "number" or base ~= base then base = 1.1 end
            local t0 = base + 1
            RT:update(mgr, t0, .05)
            RT:update(mgr, t0 + 5.1, .05)
            local probe = RT._residual_probe
            positive_probe_active = (probe ~= nil) and (probe.active == true)

            -- The real init_finalize callback cleared the fixture buffs; keep
            -- the real draw workload non-empty without replacing any KH method.
            kyohud.settings.enable_buffs = true
            kyohud.settings.enable_killfeed = false
            kyohud._gameinfo_bridge_active = true
            kyohud.is_buff_visible = function(_, id) return id == "test" end
            kyohud._buffs.test = {
                id = "test",
                icon = {texture = "guis/textures/pd2/hud_timer"},
                color = Color.white,
                start_t = 0,
                duration = 30,
                t_end = 30,
            }
        ''')
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local probe = RT._residual_probe
            local panel = kyohud._panel
            positive_panel_ready = (panel ~= nil) and alive(panel)

            local function child_count()
                local n = 0
                if panel and panel._children then
                    for _ in pairs(panel._children) do n = n + 1 end
                end
                return n
            end

            local count_before = probe.phases.combat_draw.count
            positive_draw_ok, positive_draw_err = pcall(function()
                kyohud:draw()
            end)
            positive_draw_error = tostring(positive_draw_err or "")
            local count_after_positive = probe.phases.combat_draw.count
            positive_draw_delta = count_after_positive - count_before
            probe_draw_count = count_after_positive
            positive_clock_reads = clock_reads
            positive_panel_children = child_count()
            positive_panel_same = (kyohud._panel == panel)

            local before = probe.phases.combat_draw.count
            local function delta()
                local clock_before = clock_reads
                local log_before = #log_texts
                local ok, err = pcall(function() kyohud:draw() end)
                return ok, tostring(err or ""), clock_reads - clock_before,
                    #log_texts - log_before
            end

            local saved_runtime = kyohud.hud.runtime
            kyohud.hud.runtime = nil
            missing_runtime_ok, missing_runtime_error,
                missing_runtime_clock, missing_runtime_log = delta()
            missing_runtime_count_same = (probe.phases.combat_draw.count == before)
            kyohud.hud.runtime = saved_runtime

            local saved_stamp = RT._residual_stamp
            RT._residual_stamp = nil
            missing_stamp_ok, missing_stamp_error,
                missing_stamp_clock, missing_stamp_log = delta()
            missing_stamp_count_same = (probe.phases.combat_draw.count == before)
            RT._residual_stamp = saved_stamp

            local saved_record = RT._residual_record
            RT._residual_record = nil
            missing_record_ok, missing_record_error,
                missing_record_clock, missing_record_log = delta()
            missing_record_count_same = (probe.phases.combat_draw.count == before)
            RT._residual_record = saved_record

            local saved_active = probe.active
            probe.active = false
            inactive_ok, inactive_error, inactive_clock, inactive_log = delta()
            inactive_count_same = (probe.phases.combat_draw.count == before)
            probe.active = saved_active

            local before_error = probe.phases.combat_draw.count
            panel.clear = function() error("kyohud_positive_draw_clear_failure") end
            error_draw_ok, error_draw_err = pcall(function() kyohud:draw() end)
            panel.clear = nil
            error_draw_error = tostring(error_draw_err or "")
            error_phase_same = (probe.phases.combat_draw.count == before_error)

            recovery_ok, recovery_err = pcall(function() kyohud:draw() end)
            recovery_error = tostring(recovery_err or "")
            recovery_count_delta = probe.phases.combat_draw.count - before_error
            recovery_panel_same = (kyohud._panel == panel)
        ''')
        g = lua.globals()
        self.assertIs(g.positive_panel_ready, True,
                      "the online fixture must expose a real owned panel")
        self.assertIs(g.positive_probe_active, True,
                      "the monotonic warmup must activate the probe")
        self.assertIs(g.positive_draw_ok, True,
                      f"the real positive draw must succeed: {g.positive_draw_error}")
        self.assertGreater(int(g.positive_draw_delta), 0,
                           "RED: the real draw must add a combat_draw record")
        self.assertGreater(int(g.probe_draw_count), 0,
                           "the real combat_draw phase must be positive")
        self.assertGreater(int(g.positive_panel_children), 0,
                           "the real draw must produce owned panel children")
        self.assertIs(g.positive_panel_same, True,
                      "the real draw must keep the same owned panel")
        self.assertGreater(int(g.positive_clock_reads), 0,
                           "the active draw must read the diagnostic clock")

        for prefix in ("missing_runtime", "missing_stamp", "missing_record",
                       "inactive"):
            self.assertIs(getattr(g, prefix + "_ok"), True,
                          f"{prefix} draw must still succeed: "
                          f"{getattr(g, prefix + '_error')}")
            self.assertEqual(getattr(g, prefix + "_clock"), 0,
                             f"{prefix} draw must not read os.clock")
            self.assertEqual(getattr(g, prefix + "_log"), 0,
                             f"{prefix} draw must not log")
            self.assertIs(getattr(g, prefix + "_count_same"), True,
                          f"{prefix} draw must not record combat_draw")

        self.assertIs(g.error_draw_ok, False,
                      "the injected panel clear error must propagate")
        self.assertIn("kyohud_positive_draw_clear_failure",
                      str(g.error_draw_error),
                      "the original panel clear error must be retained")
        self.assertIs(g.error_phase_same, True,
                      "an errored draw must not record combat_draw")
        self.assertIs(g.recovery_ok, True,
                      f"the same panel must draw after getter restore: {g.recovery_error}")
        self.assertIs(g.recovery_panel_same, True,
                      "recovery must reuse the same owned panel")
        self.assertGreater(int(g.recovery_count_delta), 0,
                           "the recovered real draw must record combat_draw")


if __name__ == "__main__":
    unittest.main()
