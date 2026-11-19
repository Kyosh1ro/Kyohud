"""RED: KYO_KINGPIN_PERF must select an event-triggered Kingpin probe mode.

With both KYO_RESIDUAL_PERF and an empty KYO_KINGPIN_PERF present, the probe
must never auto-capture on ordinary RT:update frames, however long they run.
It activates only on a real positive Kingpin radial event, keeps the existing
prepare/chain/priority/post/final sub-phases and the throttled active phase,
releases the two native ability leaves on a terminal event, emits exactly one
bounded report carrying mode=kingpin, and never re-arms afterwards. A second
fresh VM checks that an ineligible equipment source or a terminal event before
any positive event cannot activate the mode. Current production has no Kingpin
mode, so these assertions are expected to fail (RED).

The runtime chunk is re-executed in the real kingpin_lua fixture with the
existing residual sentinel helper; before that, io.open is wrapped so only the
exact ModPath .. "KYO_KINGPIN_PERF" path yields a closeable fake handle and
every other path is delegated to the previous io.open.
"""
import unittest

from test_hud_kingpin_active import kingpin_lua
from test_hud_residual_probe import (INSTALL_CLOCK_AND_LOG_COUNTERS,
                                     _rearm_with_sentinel)

INSTALL_KINGPIN_SENTINEL = r'''
    _kingpin_real_io_open = io.open
    _kingpin_opens = 0
    io.open = function(path, mode)
        if path == ModPath .. "KYO_KINGPIN_PERF" then
            _kingpin_opens = _kingpin_opens + 1
            return {close = function(self) return true end}
        end
        return _kingpin_real_io_open(path, mode)
    end
'''

EVENT_PHASES = ('"kingpin_event_prepare", "kingpin_event_chain", '
                '"kingpin_event_priority", "kingpin_event_post", '
                '"kingpin_event_final"')


def _kingpin_probe_lua():
    lua = kingpin_lua()
    lua.execute(INSTALL_KINGPIN_SENTINEL)
    lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
    _rearm_with_sentinel(lua)
    return lua


class KingpinTriggerProbeTests(unittest.TestCase):
    def test_event_arms_kingpin_mode_and_completes_once(self):
        lua = _kingpin_probe_lua()
        g = lua.globals()
        self.assertEqual(g._sentinel_opens, 1)
        self.assertEqual(g._kingpin_opens, 1,
                         "the runtime must probe KYO_KINGPIN_PERF once")

        lua.execute(r'''
            local RT, mgr = _R, _m
            local p = RT._residual_probe
            local names = {''' + EVENT_PHASES + r'''}
            local function count(name)
                local record = p and p.phases and p.phases[name]
                return record and record.count or 0
            end
            mode_field = p and p.mode
            idle_ok, idle_err = pcall(function()
                RT:update(mgr, 10, .05)
                RT:update(mgr, 100, .05)
                RT:update(mgr, 110, .05)
            end)
            idle_active = p.active == true
            idle_done = p.done == true
            idle_clock = clock_reads
            idle_logs = #log_texts

            event_ok, event_err = pcall(function()
                mgr:set_player_ability_radial({current = 6, total = 6}) end)
            active_after_event = p.active == true
            capture_start_after_event = p.capture_start
            meter_hidden = (_ability_meter:visible() == false)
            icon_hidden = (_ability_icon:visible() == false)
            first5_positive = true
            for _, name in ipairs(names) do
                if count(name) < 1 then first5_positive = false end
            end

            throttle_ok, throttle_err = pcall(function()
                RT:update(mgr, 110.01, .01) end)
            throttle_active = p.active == true
            local terminal_before = count("kingpin_event_terminal")
            terminal_ok, terminal_err = pcall(function()
                mgr:set_player_ability_radial({current = 0, total = 1}) end)
            terminal_increased =
                count("kingpin_event_terminal") > terminal_before
            meter_restored = (_ability_meter:visible() == true)
            icon_restored = (_ability_icon:visible() == true)

            finish_ok, finish_err = pcall(function()
                RT:update(mgr, 130.1, .05) end)
            local reports, report_text = 0, ""
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                    reports, report_text = reports + 1, message
                end
            end
            report_count = reports
            report_mode_ok = report_text:find("mode=kingpin", 1, true) ~= nil
            report_phases_ok = true
            for _, name in ipairs({"kingpin_event_prepare",
                "kingpin_event_chain", "kingpin_event_priority",
                "kingpin_event_post", "kingpin_event_final",
                "kingpin_event_terminal"}) do
                if not report_text:find(name, 1, true) then
                    report_phases_ok = false
                end
            end
            done_after_finish = p.done == true
            active_after_finish = p.active == true
            post_clock = clock_reads
            post_logs = #log_texts

            late_event_ok, late_event_err = pcall(function()
                mgr:set_player_ability_radial({current = 6, total = 6}) end)
            late_update_ok, late_update_err = pcall(function()
                RT:update(mgr, 140, .05) end)
            late_clock = clock_reads
            late_logs = #log_texts
            late_done = p.done == true
            late_active = p.active == true
        ''')
        g = lua.globals()
        self.assertEqual(g.mode_field, "kingpin")
        self.assertIs(g.idle_ok, True, g.idle_err)
        self.assertIs(g.idle_active, False,
                      "kingpin mode must not auto-capture on RT:update")
        self.assertIs(g.idle_done, False)
        self.assertEqual(g.idle_clock, 0,
                         "an unarmed kingpin mode must not read os.clock")
        self.assertEqual(g.idle_logs, 0)
        self.assertIs(g.event_ok, True, g.event_err)
        self.assertIs(g.active_after_event, True,
                      "a positive native event must arm the probe")
        self.assertIsNotNone(g.capture_start_after_event)
        self.assertAlmostEqual(float(g.capture_start_after_event), 110.0,
                               delta=1e-6)
        self.assertIs(g.first5_positive, True,
                      "positive event must increment prepare/chain/priority/post/final")
        self.assertIs(g.meter_hidden, True)
        self.assertIs(g.icon_hidden, True)
        self.assertIs(g.throttle_ok, True, g.throttle_err)
        self.assertIs(g.throttle_active, True,
                      "a throttled update must keep the capture active")
        self.assertIs(g.terminal_ok, True, g.terminal_err)
        self.assertIs(g.terminal_increased, True)
        self.assertIs(g.meter_restored, True)
        self.assertIs(g.icon_restored, True)
        self.assertIs(g.finish_ok, True, g.finish_err)
        self.assertEqual(g.report_count, 1)
        self.assertIs(g.report_mode_ok, True,
                      "the single report must expose mode=kingpin")
        self.assertIs(g.report_phases_ok, True,
                      "the single report must expose the Kingpin event phases")
        self.assertIs(g.done_after_finish, True)
        self.assertIs(g.active_after_finish, False)
        self.assertIs(g.late_event_ok, True, g.late_event_err)
        self.assertIs(g.late_update_ok, True, g.late_update_err)
        self.assertIs(g.late_done, True)
        self.assertIs(g.late_active, False)
        self.assertEqual(g.late_clock, g.post_clock,
                         "no clock read after the single report")
        self.assertEqual(g.late_logs, g.post_logs,
                         "no log after the single report")

    def test_eligibility_and_terminal_events_do_not_arm(self):
        lua = _kingpin_probe_lua()
        lua.execute(r'''
            local RT, mgr = _R, _m
            local p = RT._residual_probe
            mode_field = p and p.mode
            base_ok, base_err = pcall(function()
                RT:update(mgr, 10, .05)
                RT:update(mgr, 100, .05) end)
            inactive_before = p.active == true

            terminal_ok, terminal_err = pcall(function()
                mgr:set_player_ability_radial({current = 0, total = 1}) end)
            terminal_inactive = p.active == true
            not_done_yet = p.done == true

            kyohud.settings.enable_equipment = false
            absent_ok, absent_err = pcall(function()
                mgr:set_player_ability_radial({current = 6, total = 6}) end)
            absent_active = p.active == true

            kyohud.settings.enable_equipment = true
            RT:update(mgr, 101, .05)
            restore_ok, restore_err = pcall(function()
                mgr:set_player_ability_radial({current = 6, total = 6}) end)
            restored_active = p.active == true
            restored_capture = p.capture_start
        ''')
        g = lua.globals()
        self.assertEqual(g.mode_field, "kingpin")
        self.assertIs(g.base_ok, True, g.base_err)
        self.assertIs(g.inactive_before, False)
        self.assertIs(g.terminal_ok, True, g.terminal_err)
        self.assertIs(g.terminal_inactive, False,
                      "a terminal event before any positive must not arm")
        self.assertIs(g.not_done_yet, False)
        self.assertIs(g.absent_ok, True, g.absent_err)
        self.assertIs(g.absent_active, False,
                      "a positive event without an equipment source must not arm")
        self.assertIs(g.restore_ok, True, g.restore_err)
        self.assertIs(g.restored_active, True,
                      "restoring the source and a fresh positive event must arm")
        self.assertIsNotNone(g.restored_capture)
        self.assertAlmostEqual(float(g.restored_capture), 101.0, delta=1e-6)

    def test_invalid_backward_and_expired_sources_need_a_repaired_update(self):
        cases = ("invalid_time", "backward_time", "expired_source")
        for case in cases:
            with self.subTest(case=case):
                lua = _kingpin_probe_lua()
                lua.execute('case = "' + case + '"\n' + r'''
                    local RT, mgr = _R, _m
                    local p = RT._residual_probe
                    if case == "invalid_time" then
                        reject_update_ok, reject_update_err = pcall(function()
                            RT:update(mgr, 0/0, .05) end)
                    elseif case == "backward_time" then
                        RT:update(mgr, 120, .05)
                        reject_update_ok, reject_update_err = pcall(function()
                            RT:update(mgr, 90, .05) end)
                    else
                        _app_now = 1007
                        reject_update_ok, reject_update_err = pcall(function()
                            RT:update(mgr, 100, .05) end)
                    end
                    reject_active = p.active == true
                    reject_done = p.done == true
                    reject_clock = clock_reads
                    reject_logs = #log_texts

                    native_ok, native_err = pcall(function()
                        mgr:set_player_ability_radial({current = 6, total = 6}) end)
                    after_native_active = p.active == true
                    after_native_done = p.done == true
                    after_native_clock = clock_reads
                    after_native_logs = #log_texts

                    _app_now = 1000
                    repair_ok, repair_err = pcall(function()
                        RT:update(mgr, 101, .05) end)
                    repaired_active = p.active == true
                    repaired_capture = p.capture_start
                    positive_ok, positive_err = pcall(function()
                        mgr:set_player_ability_radial({current = 6, total = 6}) end)
                    armed_active = p.active == true
                    armed_capture = p.capture_start
                    armed_prepare = p.phases.kingpin_event_prepare.count
                ''')
                g = lua.globals()
                self.assertEqual(g.case, case)
                self.assertIs(g.reject_update_ok, True, g.reject_update_err)
                self.assertIs(g.reject_active, False,
                              "a rejected source/update must not arm the probe")
                self.assertIs(g.reject_done, False)
                self.assertEqual(g.reject_clock, 0,
                                 "an unarmed rejected update must not read os.clock")
                self.assertEqual(g.reject_logs, 0)
                self.assertIs(g.native_ok, True, g.native_err)
                self.assertIs(g.after_native_active, False,
                              "the real native positive must not arm without a "
                              "valid previous update")
                self.assertIs(g.after_native_done, False)
                self.assertEqual(g.after_native_clock, 0)
                self.assertEqual(g.after_native_logs, 0)
                self.assertIs(g.repair_ok, True, g.repair_err)
                self.assertIs(g.repaired_active, False,
                              "the repairing update alone must not arm")
                self.assertIsNone(g.repaired_capture)
                self.assertIs(g.positive_ok, True, g.positive_err)
                self.assertIs(g.armed_active, True,
                              "a repaired update plus the real native source must arm")
                self.assertAlmostEqual(float(g.armed_capture), 101.0, delta=1e-6)
                self.assertGreater(int(g.armed_prepare), 0,
                                   "the seeded event must record prepare")


if __name__ == "__main__":
    unittest.main()
