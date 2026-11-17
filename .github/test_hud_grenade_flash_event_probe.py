"""RED contract for the grenade flash event residual phase wrapper.

A real local ``_emit_flash`` must contribute the certified event capture to the
``equipment_collect`` phase on top of the notify refresh that already records.
The probe stays silent while the sentinel is absent, opens once on rearm,
reports exactly once after the unchanged 5 s warmup / 20 s capture lifecycle,
and then stops reading the diagnostic clock or logging.  Phase timings are
inclusive runtime buckets, not FPS measurements.
"""
import unittest

from test_hud_grenade_flash_event import _event_lua
from test_hud_residual_probe import (
    INSTALL_CLOCK_AND_LOG_COUNTERS,
    _rearm_with_sentinel,
)


class GrenadeFlashEventProbeTests(unittest.TestCase):
    def test_event_capture_is_phase_wrapped_and_probe_is_bounded(self):
        lua = _event_lua()
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local RT = _R
            local function probe() return RT._residual_probe end
            quiet_ok, quiet_err = pcall(function()
                _emit_flash(HUDManager.PLAYER_PANEL)
            end)
            quiet_err = tostring(quiet_err or "")
            quiet_probe_nil = probe() == nil
            quiet_clock, quiet_logs = clock_reads, #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.quiet_ok, True, g.quiet_err)
        self.assertIs(g.quiet_probe_nil, True, "no probe without sentinel")
        self.assertEqual(g.quiet_clock, 0, "no os.clock read without sentinel")
        self.assertEqual(g.quiet_logs, 0, "no log without sentinel")

        _rearm_with_sentinel(lua)
        self.assertEqual(lua.globals()._sentinel_opens, 1,
                         "the sentinel rearm must open once")

        lua.execute(r'''
            local RT, M, E, mgr = _R, _E, _E, _m
            local function probe() return RT._residual_probe end
            local function collect()
                local p = probe()
                local rec = p and p.phases and p.phases.equipment_collect
                return rec and rec.count or 0
            end
            warm_ok, warm_err = pcall(function()
                RT:update(mgr, 10, .05)
                RT:update(mgr, 15, .05)
            end)
            warm_err = tostring(warm_err or "")
            probe_active = probe() ~= nil and probe().active == true
            collect_before = collect()

            emit_ok, emit_err = pcall(function()
                _emit_flash(HUDManager.PLAYER_PANEL)
            end)
            emit_err = tostring(emit_err or "")
            collect_after = collect()
            collect_delta = collect_after - collect_before

            local wrappers = M._residual_phase_wrappers
            local entry = type(wrappers) == "table"
                and wrappers._capture_grenade_flash_event or nil
            capture_method = type(E._capture_grenade_flash_event) == "function"
            capture_registered = entry ~= nil
            capture_identity = entry ~= nil
                and entry == E._capture_grenade_flash_event

            finish_ok, finish_err = pcall(function()
                RT:update(mgr, 35.1, .05)
            end)
            finish_err = tostring(finish_err or "")
            probe_done = probe() ~= nil and probe().done == true
            local reports = 0
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                    reports = reports + 1
                end
            end
            report_count = reports
            finish_clock, finish_logs = clock_reads, #log_texts

            post_emit_ok, post_emit_err = pcall(function()
                _emit_flash(HUDManager.PLAYER_PANEL)
            end)
            post_emit_err = tostring(post_emit_err or "")
            later_ok, later_err = pcall(function()
                RT:update(mgr, 36, .05)
            end)
            later_err = tostring(later_err or "")
            post_clock, post_logs = clock_reads, #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.warm_ok, True, g.warm_err)
        self.assertIs(g.probe_active, True, "10s/15s warmup must arm capture")
        self.assertIs(g.emit_ok, True, g.emit_err)
        self.assertGreaterEqual(g.collect_delta, 2,
            "RED: a real local event must add the event capture record on top "
            "of the already-recorded notify refresh")
        self.assertIs(g.capture_method, True, "the event capture method must exist")
        self.assertIs(g.capture_registered, True,
            "RED: _capture_grenade_flash_event must be in the phase wrappers")
        self.assertIs(g.capture_identity, True,
            "RED: the wrapper entry must be E._capture_grenade_flash_event")
        self.assertIs(g.finish_ok, True, g.finish_err)
        self.assertIs(g.probe_done, True, "the unchanged 20s capture must finish")
        self.assertEqual(g.report_count, 1,
            "exactly one [KyoHUD][ResidualProbe] report")
        self.assertIs(g.post_emit_ok, True, g.post_emit_err)
        self.assertIs(g.later_ok, True, g.later_err)
        self.assertEqual(g.post_clock, g.finish_clock,
            "no diagnostic os.clock read after the probe is done")
        self.assertEqual(g.post_logs, g.finish_logs,
            "no log after the probe is done")


if __name__ == "__main__":
    unittest.main()
