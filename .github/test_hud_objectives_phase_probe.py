"""Objectives residual phase tracer: idle/active animate split and callback aggregation.

One tracer test over the real native-ready objectives fixture and the real
runtime residual capture. It positively activates an objective through the
fixture's ObjectivesManager, mounts the runtime, rearms the opt-in sentinel with
a native-shaped live player, then drives animate through idle, completion
midpoint, finishing frame and a fresh idle frame.

Production must expose three phase buckets recorded through the existing RT
residual probe:
- objectives_anim_idle: animate calls whose actual any_active is false;
- objectives_anim_active: animate calls whose actual any_active is true,
  including the finishing frame that clears the slot;
- objectives_callback: every registered Kyo Objectives pre/post callback
  dispatched through safe_hook/safe_prehook.

No test-side counters or hooks are installed. Real OM:complete_objective is
used so the native hook chain produces the callbacks.
"""
import unittest

from test_hud_objectives_visibility import _lua_native_ready
from test_hud_residual_probe import _rearm_with_sentinel


class ObjectivesPhaseProbeTests(unittest.TestCase):
    def test_objectives_anim_and_callback_buckets_follow_native_dispatch(self):
        lua, ok = _lua_native_ready()
        self.assertTrue(ok, "objectives production chunk missing")

        lua.execute(r'''
            managers.player = managers.player or {}
            _probe_live_unit = {_alive = true}
            managers.player.player_unit = function() return _probe_live_unit end
        ''')
        _rearm_with_sentinel(lua)

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local probe = RT._residual_probe
            assert(type(probe) == "table", "armed residual probe must exist")

            RT:_residual_tick(2)
            RT:_residual_tick(7.1)
            assert(probe.active == true,
                "native-shaped live player must arm the residual capture")

            local phases = probe.phases
            local idle = phases.objectives_anim_idle
            local active = phases.objectives_anim_active
            local callbacks = phases.objectives_callback

            local function shape_ok(record)
                return type(record) == "table"
                    and type(record.count) == "number"
                    and type(record.sum) == "number"
                    and type(record.max) == "number"
            end

            assert(shape_ok(idle),
                "production must expose objectives_anim_idle count/sum/max")
            assert(shape_ok(active),
                "production must expose objectives_anim_active count/sum/max")
            assert(shape_ok(callbacks),
                "production must expose objectives_callback count/sum/max")

            local O = kyohud.hud.objectives
            local slot = O._slot_prims[1]
            assert(slot and slot.text and slot.amount,
                "native-ready fixture must expose owned slot primitives")
            local root_before = O._root_panel
            local slot_before = slot
            local title_before = slot.text
            local amount_before = slot.amount

            local idle_before = idle.count
            local active_before = active.count
            local callback_before = callbacks.count
            local runtime_before = phases.runtime.count

            -- Idle animate: actual any_active is false.
            O:animate(1.10, 0.016)
            assert(idle.count == idle_before + 1,
                "idle O:animate must add exactly one idle phase")
            assert(active.count == active_before,
                "idle O:animate must not add an active phase")
            assert(callbacks.count == callback_before,
                "idle O:animate must not record objectives_callback")

            -- Real native dispatch: three completes finalize collect.
            local OM = managers.objectives
            OM:complete_objective("collect")
            OM:complete_objective("collect")
            OM:complete_objective("collect")

            assert(#O._active == 0,
                "native completion must remove collect from the live snapshot")
            local completion = O._slot_completion[1]
            assert(type(completion) == "table" and completion.active == true,
                "native completion must leave an active completion slot")
            assert(completion.entry_id == "collect",
                "completion slot must retain the collect entry id")
            assert(completion.amount_text == "3/3",
                "completion slot must retain the finalized amount display")
            assert(callbacks.count > callback_before,
                "native hook dispatch must increase objectives_callback")
            assert(phases.runtime.count == runtime_before,
                "callbacks outside RT:update must not record the runtime phase")
            assert(idle.count == idle_before + 1
                and active.count == active_before,
                "completion outside animate must not change the animate split")

            -- Midpoint of the completion pulse: actual any_active is true.
            O:animate(1.20, 0.450)
            assert(active.count == active_before + 1,
                "midpoint O:animate must add exactly one active phase")
            assert(idle.count == idle_before + 1,
                "midpoint O:animate must not add an idle phase")
            completion = O._slot_completion[1]
            assert(type(completion) == "table" and completion.active == true,
                "midpoint completion slot must remain active")
            assert(completion.elapsed > 0 and completion.elapsed < 1.2,
                "midpoint completion elapsed must stay inside the animation")

            -- Finishing frame: actual any_active was true when it cleared.
            O:animate(1.65, 1.2)
            assert(active.count == active_before + 2,
                "the finishing frame must still add an active phase")
            assert(idle.count == idle_before + 1,
                "the finishing frame must not add an idle phase")
            assert(O._slot_completion[1] == nil,
                "settling must clear the completion slot")
            assert(#O._active == 0,
                "settled completion must leave no live objective")

            -- Fresh idle frame after settling.
            O:animate(1.70, 0.016)
            assert(idle.count == idle_before + 2,
                "post-settle O:animate must add exactly one idle phase")
            assert(active.count == active_before + 2,
                "post-settle O:animate must not add an active phase")

            assert(O._root_panel == root_before,
                "settling must retain the owned root panel identity")
            assert(O._slot_prims[1] == slot_before,
                "settling must retain the owned slot identity")
            assert(O._slot_prims[1].text == title_before,
                "settling must retain the title primitive identity")
            assert(O._slot_prims[1].amount == amount_before,
                "settling must retain the amount primitive identity")
            assert(phases.runtime.count == runtime_before,
                "direct animate calls must not record the runtime phase")
        ''')


if __name__ == "__main__":
    unittest.main()
