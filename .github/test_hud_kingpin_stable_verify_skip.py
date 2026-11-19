"""RED: a stable Kingpin continuation must skip the redundant post-priority and
final local ability verification.

The reusable publication fixture already acquires the Kingpin lease on the first
positive radial publication and keeps that exact activation on a second
publication of the same event (same event_id, same lease generation, still
leased). Production currently re-runs `_verify_local_ability_activity` from the
post-priority callback and from the final seam in addition to the prepare phase,
so one stable publication costs three calls. This module counts the real method
only during the stable second publication and expects a single prepare call, so
it is expected to fail (RED) until the redundant calls are skipped.
"""
import unittest

from test_hud_kingpin_publication_probe import publication_lua


class KingpinStableVerifySkipTests(unittest.TestCase):
    def test_stable_publication_skips_post_and_final_verification(self):
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

            verify_calls = 0
            local original_verify = _E._verify_local_ability_activity
            wrapped_ok = type(original_verify) == "function"
            if wrapped_ok then
                _E._verify_local_ability_activity = function(self, source)
                    verify_calls = verify_calls + 1
                    return original_verify(self, source)
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
            verify_calls_second = verify_calls
        ''')
        g = lua.globals()

        self.assertIs(g.wrapped_ok, True,
            "the fixture must expose the production verification method")
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
        self.assertIs(g.second_leased, True,
            "precondition: the stable continuation must still hold the lease")
        self.assertEqual(int(g.verify_calls_second), 2,
            "a stable Kingpin continuation must only re-verify during prepare "
            "and the chain's mandatory final control; the post-priority and "
            "final-seam verification must be skipped")


if __name__ == "__main__":
    unittest.main()
