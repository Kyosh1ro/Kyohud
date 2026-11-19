"""One Kingpin publication allocates the qualified source table once.

The real equipment chunk rebuilds `self._kingpin_activity` exactly once per
publication (`_capture_kingpin_activity`). The synchronous event chain that
follows (`sync_local_kingpin_activity_event` -> `sync_local_hacker_activity_event`
-> prepare/chain/priority/post/final) then replays that same unchanged
provenance through many call sites.

`get_kingpin_activity_source` is still invoked repeatedly, but production now
memoizes its successful result keyed on the provenance table identity, so the
extra invocations return the cached table immediately instead of re-reading
getters and re-allocating the ~30-field source table. This suite therefore
measures the number of DISTINCT allocated source tables produced, not the
invocation count.

This suite reuses the existing native-shaped publication fixture
(`test_hud_kingpin_publication_probe.publication_lua`) which owns the real
equipment/runtime chunks, the real capture callbacks, the registered HUDManager
dispatchers and the PlayerManager/Application/timer doubles. It wraps the real
`get_kingpin_activity_source` with a counting closure that preserves receiver
and return, records each non-nil returned source table by identity, drives one
complete publication, and requires exactly one distinct table. Before the
memoization this was 13 distinct tables (RED); now it must be 1 (GREEN).
"""
import unittest

from test_hud_kingpin_publication_probe import publication_lua


COUNT_ONE_PUBLICATION = r'''
local E = _E
local original = E.get_kingpin_activity_source
local seen = {}

local function counting_source(self, ...)
    local source = original(self, ...)
    if source ~= nil then
        seen[source] = true
    end
    return source
end

E.get_kingpin_activity_source = counting_source

-- One complete native-shaped Kingpin publication: the radial relay reaches the
-- registered set_teammate_ability_radial capture and the synchronous event
-- chain, without any intervening runtime tick.
_m:set_player_ability_radial({current = 6, total = 6})

local distinct = 0
for _ in pairs(seen) do
    distinct = distinct + 1
end

_G._kingpin_distinct_sources = distinct
'''


class KingpinSourceQualificationTests(unittest.TestCase):
    def test_publication_qualifies_the_stable_source_once(self):
        lua = publication_lua()

        lua.execute('_R:update(_m, 100, .05)')
        lua.execute(COUNT_ONE_PUBLICATION)

        distinct = int(lua.globals()._kingpin_distinct_sources)
        self.assertEqual(
            distinct, 1,
            "one Kingpin publication must allocate the qualified source table "
            "exactly once (the stable self._kingpin_activity provenance is "
            "rebuilt by _capture_kingpin_activity for that publication and the "
            "memoization replays it for the other call sites); RED before the "
            "memoization: 13 distinct tables")


if __name__ == "__main__":
    unittest.main()
