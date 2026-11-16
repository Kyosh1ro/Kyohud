"""Grenade flash probe: the real sync/throttle methods must be registered in
the residual phase wrappers, increment equipment_present when invoked during
the active 5s warmup, keep wrapper identity, and stay silent after the bounded
20s capture. RED while both methods remain uninstrumented.
"""
import unittest

from test_hud_grenade_flash_replacement import _flash_lua
from test_hud_residual_probe import INSTALL_CLOCK_AND_LOG_COUNTERS, _rearm_with_sentinel


class GrenadeFlashProbeTests(unittest.TestCase):
    def test_sync_and_throttle_are_phase_wrapped_and_bounded(self):
        lua = _flash_lua()
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(r'''
            local RT, E = _R, _E
            local function call(name)
                local fn = E[name]
                if type(fn) ~= "function" then return false, "missing" end
                local ok, err = pcall(fn, E)
                return ok, tostring(err or "")
            end
            quiet_sync_ok, quiet_sync_err = call("_sync_grenade_flash")
            quiet_throttle_ok, quiet_throttle_err = call("_throttle_grenade_flash")
            quiet_probe_nil = RT._residual_probe == nil
            quiet_clock, quiet_logs = clock_reads, #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.quiet_probe_nil, True, "no probe without sentinel")
        self.assertEqual(g.quiet_clock, 0, "no os.clock read without sentinel")
        self.assertEqual(g.quiet_logs, 0, "no log without sentinel")

        _rearm_with_sentinel(lua)
        self.assertEqual(lua.globals()._sentinel_opens, 1)
        lua.execute(r'''
            local RT, E, mgr = _R, _E, _m
            local function probe() return RT._residual_probe end
            local function present()
                local p = probe()
                local rec = p and p.phases and p.phases.equipment_present
                return rec and rec.count or 0
            end
            probe_mode = probe() and probe().mode

            warmup_ok, warmup_err = pcall(function()
                RT:update(mgr, 10, .05)
                RT:update(mgr, 15, .05)
                RT:update(mgr, 15.01, .01)
            end)
            warmup_err = tostring(warmup_err or "")

            local wrappers = E._residual_phase_wrappers
            local function entry_info(name)
                local entry = type(wrappers) == "table" and wrappers[name] or nil
                return entry ~= nil, type(E[name]) == "function",
                    entry ~= nil and entry == E[name]
            end

            sync_registered, sync_method, sync_identity =
                entry_info("_sync_grenade_flash")
            throttle_registered, throttle_method, throttle_identity =
                entry_info("_throttle_grenade_flash")

            sync_present_before = present()
            sync_ok, sync_verify = false, false
            sync_err = "missing"
            if sync_method then
                sync_err = ""
                local ok, result = pcall(E._sync_grenade_flash, E)
                sync_ok = ok
                if ok then
                    sync_verify = E:_verify_grenade_flash() == true
                else
                    sync_err = tostring(result or "")
                end
            end
            sync_present_after = present()

            throttle_present_before = present()
            throttle_ok, throttle_verify = false, false
            throttle_err = "missing"
            if throttle_method then
                throttle_err = ""
                local ok, result = pcall(E._throttle_grenade_flash, E)
                throttle_ok = ok
                if ok then
                    throttle_verify = E:_verify_grenade_flash() == true
                else
                    throttle_err = tostring(result or "")
                end
            end
            throttle_present_after = present()

            finish_ok, finish_err = pcall(function()
                RT:update(mgr, 35.1, .05)
            end)
            finish_err = tostring(finish_err or "")
            local q = probe()
            capture_done = q ~= nil and q.done == true
            capture_active = q ~= nil and q.active == true
            finish_clock, finish_logs = clock_reads, #log_texts

            local phase_names = {"equipment_collect", "equipment_snapshot",
                "equipment_present", "equipment_verify", "equipment_throttled"}
            phase_counts, phase_shape_ok = {}, true
            for _, name in ipairs(phase_names) do
                local rec = q and q.phases and q.phases[name]
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

            post_ok = true
            local function post_call(name)
                local fn = E[name]
                if type(fn) ~= "function" then return end
                post_ok = post_ok and pcall(fn, E)
            end
            post_call("_sync_grenade_flash")
            post_call("_throttle_grenade_flash")
            later_ok, later_err = pcall(function()
                RT:update(mgr, 36, .05)
            end)
            later_err = tostring(later_err or "")
            post_clock, post_logs = clock_reads, #log_texts
        ''')
        g = lua.globals()
        self.assertIs(g.probe_mode, None, "KYO_OBJECTIVES_PERF must be absent")
        self.assertIs(g.warmup_ok, True, g.warmup_err)

        self.assertIs(g.sync_method, True, "real _sync_grenade_flash")
        self.assertIs(g.throttle_method, True, "real _throttle_grenade_flash")
        self.assertIs(g.sync_registered, True,
            "_sync_grenade_flash in residual phase wrappers")
        self.assertIs(g.throttle_registered, True,
            "_throttle_grenade_flash in residual phase wrappers")
        self.assertIs(g.sync_identity, True,
            "sync wrapper identity must equal E._sync_grenade_flash")
        self.assertIs(g.throttle_identity, True,
            "throttle wrapper identity must equal E._throttle_grenade_flash")

        self.assertIs(g.sync_ok, True, g.sync_err)
        self.assertIs(g.throttle_ok, True, g.throttle_err)
        self.assertIs(g.sync_verify, True,
            "E:_verify_grenade_flash must pass after direct sync")
        self.assertIs(g.throttle_verify, True,
            "E:_verify_grenade_flash must pass after direct throttle")
        self.assertGreaterEqual(
            int(g.sync_present_after), int(g.sync_present_before) + 1,
            "direct sync must increment equipment_present")
        self.assertGreaterEqual(
            int(g.throttle_present_after), int(g.throttle_present_before) + 1,
            "direct throttle must increment equipment_present")

        self.assertIs(g.finish_ok, True, g.finish_err)
        self.assertIs(g.capture_done, True, "20s capture must finish")
        self.assertIs(g.capture_active, False, "finished probe inactive")
        self.assertIs(g.phase_shape_ok, True, "existing equipment phases numeric")
        for name in ("equipment_collect", "equipment_snapshot",
                     "equipment_present", "equipment_verify",
                     "equipment_throttled"):
            self.assertGreater(int(g.phase_counts[name]), 0, name)
            self.assertIn(name, str(g.report_text), name)
        self.assertEqual(g.report_count, 1, "exactly one report")

        self.assertIs(g.post_ok, True, "post-capture direct methods stay safe")
        self.assertIs(g.later_ok, True, g.later_err)
        self.assertEqual(g.post_clock, g.finish_clock, "done stops os.clock")
        self.assertEqual(g.post_logs, g.finish_logs, "done stops logs")


if __name__ == "__main__":
    unittest.main()
