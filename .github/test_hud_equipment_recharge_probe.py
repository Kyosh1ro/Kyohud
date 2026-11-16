"""Equipment recharge probe: sentinel gating and genuine R:update phases.

Disabled: source-qualified HUD cooldown event plus ordinary updates must not
create a probe, read os.clock or log. Enabled via the real residual helper:
5s warmup, 20s capture, one report with equipment_* phases, then silence. RED.
"""
import unittest

from test_hud_native_cooldown_replacement import _runtime
from test_hud_residual_probe import INSTALL_CLOCK_AND_LOG_COUNTERS, _rearm_with_sentinel

class EquipmentRechargeProbeTests(unittest.TestCase):
    def test_disabled_sentinel_keeps_ordinary_updates_quiet(self):
        lua = _runtime()
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local RT, E, mgr = _R, _E, _m
            dispatch(HUDManager, "set_teammate_grenade_cooldown", mgr,
                HUDManager.PLAYER_PANEL, {duration = 20, end_time = 1017})
            local snap = E:get_snapshot()
            cooldown_known = snap.cooldown.known == true
                and snap.cooldown.active == true
            disabled_update_ok, disabled_update_err = pcall(function()
                for i = 1, 3 do RT:update(mgr, 1 + i, .05) end
            end)
            disabled_update_err = tostring(disabled_update_err or "")
            disabled_probe_nil = RT._residual_probe == nil
            disabled_clock_reads = clock_reads
            disabled_log_count = #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.cooldown_known, True, "source-qualified HUD cooldown")
        self.assertIs(g.disabled_update_ok, True, g.disabled_update_err)
        self.assertIs(g.disabled_probe_nil, True, "no probe without sentinel")
        self.assertEqual(g.disabled_clock_reads, 0, "no os.clock read")
        self.assertEqual(g.disabled_log_count, 0, "no log")

    def test_enabled_sentinel_records_equipment_phases_then_stops(self):
        lua = _runtime()
        _rearm_with_sentinel(lua)
        self.assertEqual(lua.globals()._sentinel_opens, 1)
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local RT, E, mgr = _R, _E, _m
            local p = RT._residual_probe
            probe_mode = p and p.mode
            dispatch(HUDManager, "set_teammate_grenade_cooldown", mgr,
                HUDManager.PLAYER_PANEL, {duration = 20, end_time = 1017})
            capture_ok, capture_err = pcall(function()
                RT:update(mgr, 10, .05)
                RT:update(mgr, 15, .05)
                RT:update(mgr, 15.01, .05)
                RT:update(mgr, 15.08, .05)
                RT:update(mgr, 35.1, .05)
            end)
            capture_err = tostring(capture_err or "")
            capture_done = p.done == true
            capture_active = p.active == true
            local names = {"equipment_collect", "equipment_snapshot",
                "equipment_present", "equipment_verify", "equipment_throttled"}
            phase_counts, phase_shape_ok = {}, true
            for _, name in ipairs(names) do
                local rec = p.phases and p.phases[name]
                phase_counts[name] = rec and rec.count or 0
                phase_shape_ok = phase_shape_ok and type(rec) == "table"
                    and type(rec.count) == "number"
            end
            local reports, text = 0, ""
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                    reports, text = reports + 1, message
                end
            end
            report_count, report_text = reports, text
            clock_after, logs_after = clock_reads, #log_texts
            later_update_ok, later_update_err = pcall(function()
                RT:update(mgr, 36, .05)
            end)
            later_update_err = tostring(later_update_err or "")
            later_clock, later_logs = clock_reads, #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.probe_mode, None, "KYO_OBJECTIVES_PERF must be absent")
        self.assertIs(g.capture_ok, True, g.capture_err)
        self.assertIs(g.capture_done, True, "20s capture must finish")
        self.assertIs(g.capture_active, False, "finished probe inactive")
        self.assertIs(g.phase_shape_ok, True, "equipment phases numeric")
        for name in ("equipment_collect", "equipment_snapshot", "equipment_present",
                     "equipment_verify", "equipment_throttled"):
            self.assertGreater(int(g.phase_counts[name]), 0, name)
            self.assertIn(name, str(g.report_text), name)
        self.assertEqual(g.report_count, 1, "exactly one report")
        self.assertIs(g.later_update_ok, True, g.later_update_err)
        self.assertEqual(g.later_clock, g.clock_after, "done stops os.clock")
        self.assertEqual(g.later_logs, g.logs_after, "done stops logs")


if __name__ == "__main__":
    unittest.main()
