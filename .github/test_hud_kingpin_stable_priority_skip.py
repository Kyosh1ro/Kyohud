"""RED: a stable Kingpin publication must not re-run the full generic native
priority arbitration.

The reusable publication fixture already acquires the Kingpin lease on the first
positive radial publication. A second publication of the same activation (same
event_id, same lease generation, lease re-verified by the chain phase) is a
stable continuation; production currently still calls
`self:_apply_native_priority(nil)` from the `sync_local_hacker_activity_event`
pcall body, duplicating the generic per-frame priority pass. This module counts
that method only during the stable publication. It is expected to fail (RED)
with a count of 1 until the call is skipped for the stable case.
"""
import unittest

from test_hud_kingpin_publication_probe import publication_lua


class KingpinStablePrioritySkipTests(unittest.TestCase):
    def test_stable_publication_skips_native_priority(self):
        lua = publication_lua()
        lua.execute(r'''
            local RT, mgr = _R, _m

            RT:update(mgr, 100, .05)
            mgr:set_player_ability_radial({current = 6, total = 6})

            local p = RT._residual_probe
            first_priority_count = p and p.phases
                and p.phases.kingpin_event_priority
                and p.phases.kingpin_event_priority.count or -1

            local binding = RT._hacker_active_binding
            first_leased = type(binding) == "table"
                and binding.leased == true
                and binding.release_pending ~= true
            first_event_id = binding and binding.source_event_id or nil
            first_lease_gen = binding and binding.lease_gen or nil
            first_kind = binding and binding.source_kind or nil

            priority_calls = 0
            local original_priority = RT._apply_native_priority
            wrapped_ok = type(original_priority) == "function"
            if wrapped_ok then
                RT._apply_native_priority = function(self, t, post_release)
                    priority_calls = priority_calls + 1
                    return original_priority(self, t, post_release)
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
            priority_calls_second = priority_calls
        ''')
        g = lua.globals()

        self.assertIs(g.wrapped_ok, True,
            "the fixture must expose the production priority method")
        self.assertIs(g.first_leased, True,
            "precondition: the first publication must acquire the lease")
        self.assertEqual(g.first_kind, "chico_injector_local",
            "precondition: the lease must be the local Kingpin source")
        self.assertGreaterEqual(g.first_priority_count, 1,
            "precondition: the first publication must run the generic priority; "
            "only stable continuations skip it")
        self.assertIs(g.stable_event, True,
            "precondition: the second publication must keep the activation event_id")
        self.assertIs(g.stable_generation, True,
            "precondition: the second publication must keep the lease generation")
        self.assertIs(g.second_leased, True,
            "precondition: the stable continuation must still hold the lease")
        self.assertEqual(int(g.priority_calls_second), 0,
            "a stable Kingpin continuation must not re-run _apply_native_priority")


if __name__ == "__main__":
    unittest.main()
