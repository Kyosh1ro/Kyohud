"""Crew partition sub-phases for the opt-in residual runtime probe.

Scope: the crew block of _coordinate_h5_native_duplicates_unprofiled (the
section that builds the crew coverage signature, collects crew targets and
validates each card position) gains three non-additive sub-phase buckets,
measured with the same opt-in helpers as the existing phases
(RT:_residual_stamp() / RT:_residual_record(name, start)). They are silent
outside an active capture and counted only while the probe is active and not
finished:

- harmony_duplicates_sig: building and comparing the crew coverage signature
  produced by _h5_crew_coverage_signature.
- harmony_duplicates_collect: crew target collection by position plus the local
  collections that run inside the coordination.
- harmony_duplicates_validate: the per-position validation loop, i.e. card
  visible reads, owner_matches and has_pos checks.

These three counters do not exist in production yet; reading them directly is
intentional RED for test 1. Test 2 characterizes the absent-sentinel path (no
bucket, no diagnostic os.clock read, no log). Test 3 is the nesting net on
sums: a phase ``count`` counts spans, and the crew block opens one parent
(``harmony_duplicates``) span while each target group opens its own sub-span,
so a sub-phase count is normally greater than the parent count and the two
counts are not comparable. What is exact is the time: sub-phase spans are
strictly nested inside the parent span and os.clock is monotonically
non-decreasing, hence sum(sub-phase) <= sum(harmony_duplicates). Today the
sub-phases are absent, so the check holds vacuously at 0 <= sum; after
production lands each sub-phase sum must stay <= the enclosing
harmony_duplicates sum.

Fixture reuse: test_hud_local_h5_lifecycle._local_runtime (the real local,
weapons and crew H5 stack) and test_hud_residual_probe._rearm_with_sentinel /
INSTALL_CLOCK_AND_LOG_COUNTERS. No production monkeypatch and no Python copy of
Lua logic. Results are exported through _G and asserted in Python.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_local_h5_lifecycle import _local_runtime
from test_hud_residual_probe import (
    INSTALL_CLOCK_AND_LOG_COUNTERS,
    _positive_baseline,
    _rearm_with_sentinel,
)

PARTITION_PHASES = (
    "harmony_duplicates_sig",
    "harmony_duplicates_collect",
    "harmony_duplicates_validate",
)

INSTALL_BUCKET_COUNT = r'''
_G._bucket_count = function(name)
    local RT = kyohud.hud.runtime
    local probe = RT and RT._residual_probe
    local record = probe and probe.phases and probe.phases[name]
    if type(record) == "table" and type(record.count) == "number" then
        return record.count
    end
    return nil
end
'''

ARM_AND_WARM = r'''
local RT = kyohud.hud.runtime
RT:_residual_tick(2)
RT:_residual_tick(7.1)
_G._partition_armed = (RT._residual_probe ~= nil)
    and (RT._residual_probe.active == true)
'''

CAPTURE_TO_COMPLETION = r'''
local RT = kyohud.hud.runtime
local mgr = managers.hud
local ok, err = pcall(function()
    local t = 8.1
    while t <= 27.1 + 1e-9 do
        RT:update(mgr, t, .05)
        t = t + 1
    end
    RT:update(mgr, 28.1, .05)
end)
_G._partition_capture_ok = ok
_G._partition_capture_err = tostring(err or "")
_G._partition_done = (RT._residual_probe ~= nil)
    and (RT._residual_probe.done == true)
_G._partition_active_after = (RT._residual_probe ~= nil)
    and (RT._residual_probe.active == true)
_G._partition_dup_count = _G._bucket_count("harmony_duplicates")
'''

SHORT_ACTIVE_CAPTURE = r'''
local RT = kyohud.hud.runtime
local mgr = managers.hud
local ok, err = pcall(function()
    for t = 8.1, 12.1, 1.0 do
        RT:update(mgr, t, .05)
    end
end)
_G._partition_short_ok = ok
_G._partition_short_err = tostring(err or "")
_G._partition_still_active = (RT._residual_probe ~= nil)
    and (RT._residual_probe.active == true)
local dup = RT._residual_probe and RT._residual_probe.phases
    and RT._residual_probe.phases.harmony_duplicates
_G._partition_dup_sum = dup and dup.sum or nil
'''

DISABLED_ORDINARY_UPDATES = r'''
local RT = kyohud.hud.runtime
local mgr = managers.hud
_G._partition_probe_is_nil = (RT._residual_probe == nil)
local last = RT._last_recovery_time
if type(last) ~= "number" or last ~= last then last = 1.1 end
_G._partition_disabled_ok, err = pcall(function()
    for i = 1, 4 do
        RT:update(mgr, last + i, .05)
    end
end)
_G._partition_disabled_err = tostring(err or "")
_G._partition_phases_absent = true
for _, name in ipairs({"harmony_duplicates_sig", "harmony_duplicates_collect",
    "harmony_duplicates_validate"}) do
    if _G._bucket_count(name) ~= nil then
        _G._partition_phases_absent = false
    end
end
_G._partition_clock_reads = clock_reads
_G._partition_log_count = #log_texts
'''


def _bucket_count(lua, name):
    return lua.globals()._bucket_count(name)


def _bucket_sum(lua, name):
    return lua.eval(
        "(function(n) local RT = kyohud.hud.runtime;"
        " local probe = RT and RT._residual_probe;"
        " local record = probe and probe.phases and probe.phases[n];"
        " if type(record) == \"table\" and type(record.sum) == \"number\" then"
        " return record.sum end end)"
    )(name)


class H5PartitionProbeTests(unittest.TestCase):
    def test_crew_partition_phases_absent_before_production(self):
        """RED: the crew block must record the three sub-phases during capture.

        The real local/crew/weapons H5 stack is built, the positive crew render
        baseline is checked, then the runtime chunk is re-armed with the opt-in
        sentinel and warmed for five game seconds. Successive genuine R:update
        frames advance a full 20 game second capture and the probe finishes.
        harmony_duplicates itself must be positive (the crew block ran with
        valid cards). The three new buckets must then exist as numeric counts
        greater than zero; today they are nil, which is the intended RED.
        """
        lua = _local_runtime()
        _positive_baseline(self, lua)
        _rearm_with_sentinel(lua)
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(INSTALL_BUCKET_COUNT)
        lua.execute(ARM_AND_WARM)

        g = lua.globals()
        self.assertIs(g._partition_armed, True,
                      "live-player warmup must activate the real residual capture")

        lua.execute(CAPTURE_TO_COMPLETION)
        g = lua.globals()
        self.assertIs(g._partition_capture_ok, True,
                      "capture frames must run through genuine R:update: "
                      f"{g._partition_capture_err}")
        self.assertIs(g._partition_done, True,
                      "20 game seconds of capture must finish the probe")
        self.assertIs(g._partition_active_after, False,
                      "a completed capture must be inactive")
        self.assertIsInstance(g._partition_dup_count, (int, float),
                              "harmony_duplicates must expose a numeric count "
                              "so the crew block provably ran during capture")
        self.assertGreater(float(g._partition_dup_count), 0.0,
                           "the crew block must have recorded harmony_duplicates "
                           "while capture was active and the cards were valid")

        counts = {name: _bucket_count(lua, name) for name in PARTITION_PHASES}
        missing = [name for name in PARTITION_PHASES if counts[name] is None]
        self.assertFalse(
            missing,
            "RED: production is missing the crew partition sub-phase "
            "counters: " + ", ".join(missing),
        )
        for name in PARTITION_PHASES:
            self.assertIsInstance(
                counts[name], (int, float),
                f"RED: {name}.count must be a number once production records it")
            self.assertGreater(
                float(counts[name]), 0.0,
                f"RED: {name}.count must be > 0 during an active capture that "
                "ran the crew block with valid cards",
            )

    def test_partition_phases_silent_when_disabled(self):
        """Absent sentinel: no bucket, no diagnostic clock read, no log.

        This characterizes the disabled path: the raw fixture has no probe, so
        the three partition phases do not exist, ordinary R:update frames read
        no diagnostic os.clock and emit no log.
        """
        lua = _local_runtime()
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(INSTALL_BUCKET_COUNT)
        lua.execute(DISABLED_ORDINARY_UPDATES)

        g = lua.globals()
        self.assertIs(g._partition_probe_is_nil, True,
                      "without the sentinel the residual probe must be nil")
        self.assertIs(g._partition_disabled_ok, True,
                      "ordinary R:update must succeed: "
                      f"{g._partition_disabled_err}")
        self.assertIs(g._partition_phases_absent, True,
                      "the three partition phases must not exist when disabled")
        self.assertEqual(g._partition_clock_reads, 0,
                         "disabled profiling must not read os.clock")
        self.assertEqual(g._partition_log_count, 0,
                         "disabled profiling must not log")

    def test_partition_phases_nested_in_harmony_duplicates(self):
        """Nesting net: each sub-phase sum stays <= the harmony_duplicates sum.

        Capture is armed and a few genuine R:update frames run while it is still
        active (before the 20 second completion). A phase ``count`` counts
        spans, not work: the crew block opens one harmony_duplicates span while
        each target group opens its own sub-span, so a sub-phase count is
        normally greater than the parent count and the counts are not
        comparable. The invariant is on sums: sub-phase spans are strictly
        nested inside the parent span and os.clock is monotonically
        non-decreasing, so sum(sub-phase) <= sum(harmony_duplicates). Today the
        sub-phases are absent, so the check holds vacuously at zero; after
        production it guards against double-counting outside the enclosing
        phase.
        """
        lua = _local_runtime()
        _positive_baseline(self, lua)
        _rearm_with_sentinel(lua)
        lua.execute(INSTALL_CLOCK_AND_LOG_COUNTERS)
        lua.execute(INSTALL_BUCKET_COUNT)
        lua.execute(ARM_AND_WARM)

        g = lua.globals()
        self.assertIs(g._partition_armed, True,
                      "live-player warmup must activate the real residual capture")

        lua.execute(SHORT_ACTIVE_CAPTURE)
        g = lua.globals()
        self.assertIs(g._partition_short_ok, True,
                      "active capture frames must run: "
                      f"{g._partition_short_err}")
        self.assertIs(g._partition_still_active, True,
                      "the capture must still be active before completion")

        parent_sum = _bucket_sum(lua, "harmony_duplicates")
        self.assertIsInstance(parent_sum, (int, float),
                              "harmony_duplicates must expose a numeric sum "
                              "for the nesting invariant")
        self.assertIsNotNone(g._partition_dup_sum,
                             "harmony_duplicates must expose a numeric sum")
        self.assertGreaterEqual(float(g._partition_dup_sum), 0.0,
                                "harmony_duplicates.sum must never be negative")

        for name in PARTITION_PHASES:
            sub_sum = _bucket_sum(lua, name)
            value = 0.0 if sub_sum is None else float(sub_sum)
            self.assertLessEqual(
                value, float(parent_sum),
                f"{name} must stay nested inside harmony_duplicates "
                f"(sum {value} <= sum {float(parent_sum)})",
            )


if __name__ == "__main__":
    unittest.main()
