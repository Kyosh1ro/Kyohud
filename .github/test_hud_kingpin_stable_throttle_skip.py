"""RED: a throttled frame right after a stable Kingpin event must not re-run
the full verification tail.

The reusable publication fixture acquires the Kingpin lease on the first
positive radial publication and keeps that activation (same event_id, same
lease generation) on a second publication of the same event. Production's
``M:_throttle_kingpin_activity`` still calls ``M:verify``, ``row6:render`` and
``_verify_kingpin_activity`` on every frame, even though the stable event was
already certified by the publication seam. This module counts those three real
methods: the first throttled frame after the stable event is expected to skip
the tail (RED: it currently re-verifies everything), while a following frame
without a new stable event must still verify fully because the throttle remains
the sole verifier there.
"""
import unittest

from test_hud_kingpin_publication_probe import publication_lua


class KingpinStableThrottleSkipTests(unittest.TestCase):
    def test_stable_event_skips_throttle_tail_then_verifies_without_event(self):
        lua = publication_lua()
        lua.execute(r'''
            local RT, mgr = _R, _m

            RT:update(mgr, 100, .05)
            mgr:set_player_ability_radial({current = 6, total = 6})

            local first = RT._hacker_active_binding
            first_leased = type(first) == "table"
                and first.leased == true
                and first.release_pending ~= true
            first_event_id = first and first.source_event_id or nil
            first_lease_gen = first and first.lease_gen or nil
            first_kind = first and first.source_kind or nil

            original_full_verify = _E.verify
            full_verify_calls = 0
            original_render = type(_E._rows) == "table"
                and type(_E._rows[6]) == "table"
                and _E._rows[6].render or nil
            render_calls = 0
            original_kverify = _E._verify_kingpin_activity
            kverify_calls = 0
            wrapped_ok = type(original_full_verify) == "function"
                and type(original_render) == "function"
                and type(original_kverify) == "function"
            if type(original_full_verify) == "function" then
                _E.verify = function(self, ...)
                    full_verify_calls = full_verify_calls + 1
                    return original_full_verify(self, ...)
                end
            end
            if type(original_render) == "function" then
                _E._rows[6].render = function(self, ...)
                    render_calls = render_calls + 1
                    return original_render(self, ...)
                end
            end
            if type(original_kverify) == "function" then
                _E._verify_kingpin_activity = function(self, ...)
                    kverify_calls = kverify_calls + 1
                    return original_kverify(self, ...)
                end
            end

            mgr:set_player_ability_radial({current = 5.9, total = 6})

            local second = RT._hacker_active_binding
            second_leased = type(second) == "table"
                and second.leased == true
                and second.release_pending ~= true
            second_event_id = second and second.source_event_id or nil
            second_lease_gen = second and second.lease_gen or nil
            stable_event = first_event_id ~= nil
                and first_event_id == second_event_id
            stable_generation = first_lease_gen ~= nil
                and first_lease_gen == second_lease_gen

            -- Isolate the throttle's own work from the stable publication seam,
            -- which already certified the event before the first throttled frame.
            full_verify_calls = 0
            render_calls = 0
            kverify_calls = 0

            first_throttle_ok = _E:_throttle_kingpin_activity()
            counts_a = {full_verify_calls, render_calls, kverify_calls}
            throttle_work_after_stable = full_verify_calls + render_calls
                + kverify_calls

            second_throttle_ok = _E:_throttle_kingpin_activity()
            throttle_work_no_event = (full_verify_calls - counts_a[1])
                + (render_calls - counts_a[2])
                + (kverify_calls - counts_a[3])
        ''')
        g = lua.globals()

        self.assertIs(g.wrapped_ok, True,
            "the fixture must expose the full verify, row6 render and Kingpin "
            "activity verifier targets")
        self.assertIs(g.first_leased, True,
            "precondition: the first publication must acquire the lease")
        self.assertEqual(g.first_kind, "chico_injector_local",
            "precondition: the lease must be the local Kingpin source")
        self.assertIs(g.stable_event, True,
            "precondition: the second publication must keep the activation "
            "event_id")
        self.assertIs(g.stable_generation, True,
            "precondition: the second publication must keep the lease "
            "generation")
        self.assertEqual(int(g.throttle_work_after_stable), 0,
            "the first throttled frame after a stable event must skip the full "
            "verify/render/_verify_kingpin_activity tail")
        self.assertGreaterEqual(int(g.throttle_work_no_event), 3,
            "without a new stable event the throttle must remain the sole "
            "verifier and run the full tail")


if __name__ == "__main__":
    unittest.main()
