"""Objectives completion residual probe: wait for the first qualified completion.

This tracer uses the real native-ready objectives fixture and the real runtime
chunk. Both sentinel files are installed in the local io.open fake: the existing
KYO_RESIDUAL_PERF general sentinel and the new KYO_OBJECTIVES_PERF objectives
sentinel. When the objectives sentinel is present alongside the general one, the
same kyohud.hud.runtime._residual_probe must select mode="completion".

Completion mode must wait indefinitely past the five second general warmup while
the player is live and foundation/objectives are enabled. It captures no
diagnostic clock and writes no log before the first qualified completion. The
latest validated gameplay time is retained in p.last_t.

Three real ObjectivesManager:complete_objective("collect") calls must drive the
existing _capture_completion slot and arm that same probe before render work:
p.active becomes true and p.capture_start equals the last validated gameplay t.
No test-side trigger method is called directly.

After arming, real RT:update frames at monotonic times must grow the actual
objectives_anim_active phase, produce exactly one ResidualProbe report after
twenty game seconds, and leave p.done true. Later real objective activation and
completion must not rearm the probe or produce further diagnostic clocks/logs.
The owned objectives root and slot primitives must keep their identities, and
the initial render certification must be valid.
"""
import unittest

from test_hud_objectives_visibility import _lua_native_ready
from test_hud_residual_probe import (
    INSTALL_CLOCK_AND_LOG_COUNTERS,
    RUNTIME_PATH,
    SENTINEL_INSTALL,
    SENTINEL_RESTORE,
)

OBJECTIVES_SENTINEL_EXTEND = r'''
    _objectives_real_io_open = io.open
    _objectives_sentinel_handle = nil
    _objectives_sentinel_opens = 0
    _objectives_sentinel_closes = 0
    io.open = function(path, mode)
        if path == ModPath .. "KYO_OBJECTIVES_PERF" then
            _objectives_sentinel_opens = _objectives_sentinel_opens + 1
            local handle = {
                close = function(self)
                    _objectives_sentinel_closes = _objectives_sentinel_closes + 1
                    return true
                end,
            }
            _objectives_sentinel_handle = handle
            return handle
        end
        return _objectives_real_io_open(path, mode)
    end
'''


def _arm(lua):
    """Load the real runtime chunk once with both sentinel files recognised."""
    lua.execute(SENTINEL_INSTALL)
    lua.execute(OBJECTIVES_SENTINEL_EXTEND)
    try:
        lua.execute(RUNTIME_PATH.read_text(encoding="utf-8-sig"))
    finally:
        lua.execute(SENTINEL_RESTORE)


class ObjectivesCompletionProbeTests(unittest.TestCase):
    def test_completion_mode_waits_then_arms_once_from_real_completion(self):
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute(r'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_objectives = true
            managers.player = managers.player or {}
            _probe_live_unit = {_alive = true}
            managers.player.player_unit = function(self) return _probe_live_unit end
        ''')
        _arm(lua)

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local O = kyohud.hud.objectives
            assert(RT and O, "native-ready fixture must expose runtime and objectives")
            initial_root = O._root_panel
            initial_slot = O._slot_prims[1]
            assert(initial_slot and initial_slot.text and initial_slot.amount,
                "native-ready fixture must expose owned slot primitives")
            initial_title = initial_slot.text
            initial_amount = initial_slot.amount
            initial_cert = (O:_verify_render() == true)
        ''')
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local mgr = managers.hud
            local p = RT._residual_probe
            local wait_ok, wait_err = pcall(function()
                for t = 2, 10 do
                    RT:update(mgr, t, .05)
                end
            end)
            waiting_update_ok = wait_ok
            waiting_update_err = tostring(wait_err or "")
            waiting_probe_present = (type(p) == "table")
            waiting_active = waiting_probe_present and (p.active == true)
            waiting_done = waiting_probe_present and (p.done == true)
            waiting_last_t = waiting_probe_present and p.last_t
            waiting_mode = waiting_probe_present and p.mode
            waiting_clock_reads = clock_reads
            waiting_log_count = #log_texts
            objectives_sentinel_opens = _objectives_sentinel_opens
            objectives_sentinel_closes = _objectives_sentinel_closes
        ''')
        g = lua.globals()
        self.assertIs(g.waiting_update_ok, True,
                      f"completion-mode updates must run: {g.waiting_update_err}")
        self.assertIs(g.waiting_active, False,
                      "completion mode must wait past five seconds instead of auto-arming")
        self.assertIs(g.waiting_done, False,
                      "waiting for the first completion must not finish the probe")
        self.assertEqual(g.waiting_last_t, 10,
                         "completion mode must retain the latest validated gameplay t")
        self.assertEqual(g.waiting_clock_reads, 0,
                         "waiting must not read the diagnostic clock")
        self.assertEqual(g.waiting_log_count, 0,
                         "waiting must not log")
        self.assertEqual(g.waiting_mode, "completion",
                         "the objectives sentinel must select the completion probe mode")
        self.assertIs(g.waiting_probe_present, True,
                      "the objectives sentinel must keep the shared residual probe")
        self.assertEqual(g.objectives_sentinel_opens, 1,
                         "the runtime chunk must open the objectives sentinel exactly once")
        self.assertEqual(g.objectives_sentinel_closes, 1,
                         "the runtime chunk must close the objectives sentinel immediately")
        self.assertIs(g.initial_cert, True,
                      "the owned objectives render must certify before the capture")

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local O = kyohud.hud.objectives
            local OM = managers.objectives
            local p = RT._residual_probe
            local completion_ok, completion_err = pcall(function()
                OM:complete_objective("collect")
                OM:complete_objective("collect")
                OM:complete_objective("collect")
            end)
            completion_update_ok = completion_ok
            completion_update_err = tostring(completion_err or "")
            completion_slot = O._slot_completion[1]
            completion_slot_active = type(completion_slot) == "table"
                and completion_slot.active == true
            completion_slot_entry = completion_slot and completion_slot.entry_id
            completion_slot_amount = completion_slot and completion_slot.amount_text
            completion_probe_active = (p.active == true)
            completion_capture_start = p.capture_start
            completion_last_t = p.last_t
            completion_mode = p.mode
        ''')
        g = lua.globals()
        self.assertIs(g.completion_update_ok, True,
                      f"real objective completion must run: {g.completion_update_err}")
        self.assertIs(g.completion_slot_active, True,
                      "three real completes must leave an active completion slot")
        self.assertEqual(g.completion_slot_entry, "collect",
                         "the completion slot must retain the collect entry id")
        self.assertEqual(g.completion_slot_amount, "3/3",
                         "the completion slot must retain the finalized amount")
        self.assertIs(g.completion_probe_active, True,
                      "a qualified completion must arm the shared completion probe")
        self.assertEqual(g.completion_capture_start, 10,
                         "the capture must start at the last validated gameplay t")
        self.assertEqual(g.completion_last_t, 10,
                         "arming the capture must not invent a different gameplay t")
        self.assertEqual(g.completion_mode, "completion",
                         "the armed probe must keep the completion mode")

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local mgr = managers.hud
            local p = RT._residual_probe
            local active_before = p.phases.objectives_anim_active.count
            local capture_ok, capture_err = pcall(function()
                local t = 10.05
                while t <= 11.5 + 1e-9 do
                    RT:update(mgr, t, .05)
                    t = t + .05
                end
                RT:update(mgr, 30.1, .05)
            end)
            capture_update_ok = capture_ok
            capture_update_err = tostring(capture_err or "")
            capture_anim_active_before = active_before
            capture_anim_active_after = p.phases.objectives_anim_active.count
            capture_done = (p.done == true)
            capture_active = (p.active == true)
            local reports = 0
            local report_text = ""
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                    reports = reports + 1
                    report_text = message
                end
            end
            capture_report_count = reports
            capture_report_text = report_text
            capture_clock_reads = clock_reads
            capture_log_count = #log_texts
            capture_capture_start = p.capture_start
        ''')
        g = lua.globals()
        self.assertIs(g.capture_update_ok, True,
                      f"capture-mode updates must run: {g.capture_update_err}")
        self.assertGreater(float(g.capture_anim_active_after),
                           float(g.capture_anim_active_before),
                           "real animate frames must grow the active phase bucket")
        self.assertIs(g.capture_done, True,
                      "twenty game seconds after arming must finish the capture")
        self.assertIs(g.capture_active, False,
                      "a finished completion capture must be inactive")
        self.assertEqual(g.capture_report_count, 1,
                         "completion must emit exactly one ResidualProbe report")
        self.assertIn("[KyoHUD][ResidualProbe]", str(g.capture_report_text),
                      "the single report must carry the ResidualProbe prefix")
        self.assertEqual(g.capture_capture_start, 10,
                         "the capture start must remain the validated gameplay t")

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local O = kyohud.hud.objectives
            local OM = managers.objectives
            local p = RT._residual_probe
            local clock_before = clock_reads
            local logs_before = #log_texts
            local future_ok, future_err = pcall(function()
                OM:activate_objective("collect", nil, {amount = 3})
                OM:complete_objective("collect")
                OM:complete_objective("collect")
                OM:complete_objective("collect")
                RT:update(managers.hud, 31.1, .05)
            end)
            future_update_ok = future_ok
            future_update_err = tostring(future_err or "")
            future_done = (p.done == true)
            future_active = (p.active == true)
            future_clock_reads = clock_reads
            future_log_count = #log_texts
            local reports = 0
            for _, message in ipairs(log_texts) do
                if message:find("[KyoHUD][ResidualProbe]", 1, true) then
                    reports = reports + 1
                end
            end
            future_report_count = reports
            retained_root = (O._root_panel == initial_root)
            retained_slot = (O._slot_prims[1] == initial_slot)
            retained_title = (O._slot_prims[1].text == initial_title)
            retained_amount = (O._slot_prims[1].amount == initial_amount)
        ''')
        g = lua.globals()
        self.assertIs(g.future_update_ok, True,
                      f"future objective events must run: {g.future_update_err}")
        self.assertIs(g.future_done, True,
                      "a finished completion probe must stay finished")
        self.assertIs(g.future_active, False,
                      "future objective activation/completion must not rearm the probe")
        self.assertEqual(g.future_report_count, 1,
                         "future objective activity must not produce another report")
        self.assertEqual(g.future_clock_reads, g.capture_clock_reads,
                         "future objective activity must not read the diagnostic clock")
        self.assertEqual(g.future_log_count, g.capture_log_count,
                         "future objective activity must not log")
        self.assertIs(g.retained_root, True,
                      "the owned objectives root panel identity must be retained")
        self.assertIs(g.retained_slot, True,
                      "the owned objectives slot identity must be retained")
        self.assertIs(g.retained_title, True,
                      "the owned objectives title primitive identity must be retained")
        self.assertIs(g.retained_amount, True,
                      "the owned objectives amount primitive identity must be retained")

    def test_completion_probe_stays_inactive_when_one_eligibility_is_lost(self):
        cases = (
            ("missing_validated_time", "missingtime"),
            ("foundation_off", "foundation"),
            ("objectives_off", "objectives"),
            ("player_lost", "player"),
        )
        for label, loss in cases:
            with self.subTest(case=label):
                lua, ok = _lua_native_ready()
                self.assertTrue(ok, f"{label}: objectives production chunk missing")
                lua.execute(r'''
                    kyohud.settings.enable_hud_foundation = true
                    kyohud.settings.enable_objectives = true
                    managers.player = managers.player or {}
                    _probe_live_unit = {_alive = true}
                    managers.player.player_unit = function(self) return _probe_live_unit end
                ''')
                _arm(lua)
                lua.execute(r'''
                    local O = kyohud.hud.objectives
                    assert(O and O._mounted == true, "native-ready fixture must mount objectives")
                    initial_cert = (O:_verify_render() == true)
                ''')
                lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
                lua.execute(f'_case_loss = "{loss}"')
                lua.execute(r'''
                    local RT = kyohud.hud.runtime
                    local O = kyohud.hud.objectives
                    local OM = managers.objectives
                    if _case_loss ~= "missingtime" then
                        RT:_residual_tick(10)
                    end
                    if _case_loss == "foundation" then
                        kyohud.settings.enable_hud_foundation = false
                    elseif _case_loss == "objectives" then
                        kyohud.settings.enable_objectives = false
                    elseif _case_loss == "player" then
                        managers.player.player_unit = function(self) return nil end
                    end
                    local p = RT._residual_probe
                    seed_last_t = p and p.last_t
                    local completion_ok, completion_err = pcall(function()
                        OM:complete_objective("collect")
                        OM:complete_objective("collect")
                        OM:complete_objective("collect")
                    end)
                    local slot = O._slot_completion[1]
                    slot_active = type(slot) == "table" and slot.active == true
                    slot_entry = slot and slot.entry_id
                    probe_present = (type(p) == "table")
                    probe_active = probe_present and (p.active == true)
                    probe_done = probe_present and (p.done == true)
                    negative_clock_reads = clock_reads
                    negative_log_count = #log_texts
                    completion_call_ok = completion_ok
                    completion_call_err = tostring(completion_err or "")
                ''')
                g = lua.globals()
                self.assertIs(g.completion_call_ok, True,
                              f"{label}: real objective completion must run: {g.completion_call_err}")
                self.assertIs(g.initial_cert, True,
                              f"{label}: owned objectives render must certify before completion")
                self.assertIs(g.probe_present, True,
                              f"{label}: sentinel must keep the shared residual probe")
                self.assertIs(g.slot_active, True,
                              f"{label}: three real completes must reach the capture slot")
                self.assertEqual(g.slot_entry, "collect",
                                 f"{label}: the capture slot must retain the collect entry")
                if loss == "missingtime":
                    self.assertIsNone(g.seed_last_t,
                                      f"{label}: no validated gameplay time may be seeded")
                else:
                    self.assertEqual(g.seed_last_t, 10,
                                     f"{label}: the eligibility tick must seed the gameplay time")
                self.assertIs(g.probe_active, False,
                              f"{label}: incomplete eligibility must not arm the probe")
                self.assertIs(g.probe_done, False,
                              f"{label}: the unarmed probe must remain unfinished")
                self.assertEqual(g.negative_clock_reads, 0,
                                 f"{label}: no diagnostic clock may be read")
                self.assertEqual(g.negative_log_count, 0,
                                 f"{label}: no diagnostic log may be written")


if __name__ == "__main__":
    unittest.main()
