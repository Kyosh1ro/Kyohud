"""RED: the Kingpin publication phase must accumulate the native
set_player_ability_radial publication cost.

The reusable Kingpin probe fixture already owns the real equipment/ability
panels and the registered dispatchers. This module only defines a native-shaped
set_player_ability_radial in the test fixture, reloads the production equipment
chunk once so its hooks see that method, and measures the publication phase
through the real residual-probe records. Production has no such phase yet.
"""
import unittest

from test_hud_hacker_active import EQUIPMENT_PATH
from test_hud_kingpin_trigger_probe import _kingpin_probe_lua


PUBLICATION_FIXTURE = r'''
_pub_clock = 0
_pub_clock_reads = 0
os.clock = function()
    _pub_clock_reads = _pub_clock_reads + 1
    return _pub_clock
end

local function dispatch_publication_hooks(kind, self, data)
    for _, record in ipairs(Hooks._all) do
        if record.class == HUDManager
            and record.method == "set_player_ability_radial"
            and record.kind == kind then
            record.fn(self, data)
        end
    end
end

function HUDManager:set_player_ability_radial(data)
    dispatch_publication_hooks("pre", self, data)
    _pub_clock = _pub_clock + 0.007
    if _pub_native_action then _pub_native_action(self, data) end
    local result = self:set_teammate_ability_radial(
        HUDManager.PLAYER_PANEL, data)
    dispatch_publication_hooks("post", self, data)
    return nil
end
'''


def publication_lua():
    lua = _kingpin_probe_lua()
    lua.execute(PUBLICATION_FIXTURE)
    lua.globals().RequiredScript = "lib/managers/hudmanagerpd2"
    lua.execute(EQUIPMENT_PATH.read_text(encoding="utf-8-sig"))
    return lua


class KingpinPublicationProbeTests(unittest.TestCase):
    def test_publication_phase_records_native_publication_time(self):
        lua = publication_lua()
        lua.execute(r'''
            local RT, mgr = _R, _m
            local p = RT._residual_probe

            RT:update(mgr, 100, .05)
            waiting_active = p.active == true
            waiting_done = p.done == true

            mgr:set_player_ability_radial({current = 6, total = 6})
            first_active = p.active == true
            first_color_r = _ability_meter:color().r
            first_meter_hidden = (_ability_meter:visible() == false)
            first_icon_hidden = (_ability_icon:visible() == false)

            local phase_before = p.phases
                and p.phases.kingpin_publication_total
            phase_before_count = phase_before and phase_before.count or 0

            mgr:set_player_ability_radial({current = 5.9, total = 6})
            local phase = p.phases and p.phases.kingpin_publication_total
            phase_exists = phase ~= nil
            phase_count = phase and phase.count or 0
            phase_sum = phase and phase.sum or 0
            second_color_r = _ability_meter:color().r
        ''')
        g = lua.globals()

        self.assertIs(g.waiting_active, False,
                      "the probe must wait before a positive event")
        self.assertIs(g.waiting_done, False)
        self.assertIs(g.first_active, True,
                      "a positive event must arm the capture")
        self.assertAlmostEqual(float(g.first_color_r), 1.0, places=5,
            msg="the native setter must publish full progress")
        self.assertIs(g.first_meter_hidden, True,
                      "the production callback must lease ability_meter")
        self.assertIs(g.first_icon_hidden, True,
                      "the production callback must lease ability_icon")
        self.assertEqual(int(g.phase_before_count), 0,
                      "the incomplete capture entry must be excluded")
        self.assertIs(g.phase_exists, True,
                      "kingpin_publication_total must exist after a capture")
        self.assertEqual(int(g.phase_count), 1,
                         "exactly one publication sample must be recorded")
        self.assertAlmostEqual(float(g.phase_sum), .007, places=6,
            msg="the publication phase must accumulate the .007 native cost")
        self.assertAlmostEqual(float(g.second_color_r), 5.9 / 6.0, places=5)

    def test_publication_phase_stays_silent_after_capture_done(self):
        lua = publication_lua()
        lua.execute(r'''
            local RT, mgr = _R, _m
            local p = RT._residual_probe

            RT:update(mgr, 10, .05)
            RT:update(mgr, 100, .05)
            mgr:set_player_ability_radial({current = 6, total = 6})
            mgr:set_player_ability_radial({current = 0, total = 1})
            RT:update(mgr, 130.1, .05)

            done_before = p.done == true
            active_before = p.active == true
            reads_before = _pub_clock_reads
            clock_before = _pub_clock
            color_before = _ability_meter:color().r

            mgr:set_player_ability_radial({current = 6, total = 6})
            reads_after = _pub_clock_reads
            clock_after = _pub_clock
            color_after = _ability_meter:color().r
            done_after = p.done == true
            active_after = p.active == true
        ''')
        g = lua.globals()

        self.assertIs(g.done_before, True,
                      "precondition: the capture must be finished")
        self.assertIs(g.active_before, False)
        self.assertEqual(int(g.reads_after), int(g.reads_before),
                         "no os.clock read may happen after the single report")
        self.assertAlmostEqual(float(g.clock_after),
            float(g.clock_before) + .007, places=6,
            msg="the native fixture must still advance its clock")
        self.assertAlmostEqual(float(g.color_before), 0.0, places=5)
        self.assertAlmostEqual(float(g.color_after), 1.0, places=5,
            msg="the native setter must still mutate the meter color")
        self.assertIs(g.done_after, True)
        self.assertIs(g.active_after, False)

    def test_publication_phase_rejects_reentrancy_and_recovers(self):
        lua = publication_lua()
        lua.execute(r'''
            local RT, mgr = _R, _m
            local p = RT._residual_probe
            local seen = 0

            RT:update(mgr, 100, .05)
            mgr:set_player_ability_radial({current = 6, total = 6})
            armed = p.active == true

            _pub_native_action = function(self, data)
                if seen == 0 then
                    seen = 1
                    mgr:set_player_ability_radial(
                        {current = 5.9, total = 6})
                end
            end
            mgr:set_player_ability_radial({current = 5.9, total = 6})
            nested_calls = seen
            local phase_nested = p.phases
                and p.phases.kingpin_publication_total
            count_after_nested = phase_nested and phase_nested.count or 0

            _pub_native_action = nil
            mgr:set_player_ability_radial({current = 5.9, total = 6})
            local phase_clean = p.phases
                and p.phases.kingpin_publication_total
            count_after_clean = phase_clean and phase_clean.count or 0

            local sentinel = {}
            _pub_native_action = function(self, data)
                error(sentinel)
            end
            local ok, err = pcall(function()
                mgr:set_player_ability_radial(
                    {current = 5.9, total = 6})
            end)
            error_ok = ok
            error_same = (err == sentinel)
            local phase_error = p.phases
                and p.phases.kingpin_publication_total
            count_after_error = phase_error and phase_error.count or 0

            _pub_native_action = nil
            RT:update(mgr, 100.01, .05)
            mgr:set_player_ability_radial({current = 5.9, total = 6})
            local phase_recovered = p.phases
                and p.phases.kingpin_publication_total
            count_after_recovery = phase_recovered
                and phase_recovered.count or 0
        ''')
        g = lua.globals()

        self.assertIs(g.armed, True)
        self.assertEqual(int(g.nested_calls), 1,
                         "the native action must recurse exactly once")
        self.assertEqual(int(g.count_after_nested), 0,
                         "a re-entrant publication must record no sample")
        self.assertEqual(int(g.count_after_clean), 1,
                         "the next clean publication must record one sample")
        self.assertIs(g.error_ok, False,
                      "a failing native action must propagate its error")
        self.assertIs(g.error_same, True,
                      "the original error object identity must be preserved")
        self.assertEqual(int(g.count_after_error), 1,
                         "an interrupted publication must not record a sample")
        self.assertEqual(int(g.count_after_recovery), 2,
                         "a clean publication after the reset must record")

    def test_publication_hooks_install_once_per_context(self):
        lua = publication_lua()
        equipment = EQUIPMENT_PATH.read_text(encoding="utf-8-sig")

        def counts():
            lua.execute(r'''
                local pre, post = 0, 0
                for _, record in ipairs(Hooks._all) do
                    if record.class == HUDManager
                        and record.method == "set_player_ability_radial" then
                        if record.kind == "pre" then pre = pre + 1 end
                        if record.kind == "post" then post = post + 1 end
                    end
                end
                _hook_pre = pre
                _hook_post = post
            ''')
            g = lua.globals()
            return int(g._hook_pre), int(g._hook_post)

        lua.globals().RequiredScript = "lib/managers/hudmanagerpd2"
        lua.execute(equipment)

        pre, post = counts()
        self.assertEqual(pre, 1,
            "reloading equipment under the same context must not double-wrap")
        self.assertEqual(post, 1)

        lua.globals().RequiredScript = "lib/managers/__kyohud_unrelated_context__"
        lua.execute(equipment)

        pre_unknown, post_unknown = counts()
        self.assertEqual(pre_unknown, 1,
            "an unrelated RequiredScript context must not install hooks")
        self.assertEqual(post_unknown, 1)


if __name__ == "__main__":
    unittest.main()
