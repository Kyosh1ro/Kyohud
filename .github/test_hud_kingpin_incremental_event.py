"""RED: a steady native Kingpin radial event must update row 6 without a full
presentation or static row-3 relayout/render. Current production performs at
least one full presentation, so the desired zero budget is RED. Counters wrap
the real fixture methods and delegate; no production method is added, replaced
or skipped.
"""
import unittest

from test_hud_kingpin_active import KINGPIN_ACTIVATE, kingpin_lua


STABILIZE = r'''
_R:update(_m, 3.1, .05)
_m:set_player_ability_radial({current = 5.5, total = 6})
_G._full_present_count = 0
_G._static_calls = 0
_G._t_row6, _G._t_root = _E._rows[6], _E._root

local present = _E._present
assert(type(present) == "function", "fixture must expose _E._present")
_E._present = function(self, ...)
    _G._full_present_count = _G._full_present_count + 1
    return present(self, ...)
end

local row3 = _E._rows[3]
assert(row3 ~= nil, "fixture must expose row 3")
local cell_layout, render = row3.cell_layout, row3.render
assert(type(cell_layout) == "function", "row3.cell_layout must exist")
assert(type(render) == "function", "row3.render must exist")
row3.cell_layout = function(self, ...)
    _G._static_calls = _G._static_calls + 1
    return cell_layout(self, ...)
end
row3.render = function(self, ...)
    _G._static_calls = _G._static_calls + 1
    return render(self, ...)
end
'''

EVENT = r'''
_m:set_player_ability_radial({current = %s, total = 6})
_G._%s = {
    root_visible = (_E._root ~= nil and _E._root:visible() == true),
    meter_hidden = (_ability_meter:visible() == false),
    icon_hidden = (_ability_icon:visible() == false),
    row6_visible = (_E._visible_rows and _E._visible_rows[6] == true),
    row6_label = _E._rows and _E._rows[6] and _E._rows[6]._label:text(),
    row6_value = _E._rows and _E._rows[6] and _E._rows[6]._value:text(),
    row6_progress = _E._rows and _E._rows[6] and _E._rows[6]._progress,
    row6_verify = (_E._rows and _E._rows[6] and _E._rows[6]:verify() == true),
    e_verify = (_E:verify() == true),
    same_row6 = (_E._rows and _E._rows[6] == _G._t_row6),
    same_root = (_E._root == _G._t_root),
}
'''


class LocalKingpinIncrementalEventTests(unittest.TestCase):
    def event(self, lua, name, current):
        lua.execute(EVENT % (current, name))
        return lua.globals()["_" + name]

    def counts(self, lua, name):
        lua.execute("_G._%s_counts = {full = _G._full_present_count, "
                    "static = _G._static_calls}" % name)
        return lua.globals()["_%s_counts" % name]

    def assert_ui(self, obs, value, progress, context):
        self.assertTrue(bool(obs.root_visible), context + ": owned root visible")
        self.assertTrue(bool(obs.meter_hidden), context + ": meter hidden")
        self.assertTrue(bool(obs.icon_hidden), context + ": icon hidden")
        self.assertTrue(bool(obs.row6_visible), context + ": row 6 visible")
        self.assertEqual(obs.row6_label, "ACTIVE", context)
        self.assertEqual(obs.row6_value, value, context)
        self.assertAlmostEqual(float(obs.row6_progress), progress, places=6)
        self.assertTrue(bool(obs.row6_verify), context + ": row verifies")
        self.assertTrue(bool(obs.e_verify), context + ": equipment verifies")
        self.assertTrue(bool(obs.same_row6), context + ": row 6 identity stable")
        self.assertTrue(bool(obs.same_root), context + ": root identity stable")

    def test_steady_native_event_avoids_full_presentation_and_static_cells(self):
        lua = kingpin_lua()
        lua.execute(KINGPIN_ACTIVATE)
        lua.execute(STABILIZE)

        first = self.event(lua, "t1", "4.25")
        self.assert_ui(first, "5s", 4.25 / 6.0, "first event")
        first_counts = self.counts(lua, "t1")
        self.assertEqual(int(first_counts.full), 0,
            "RED: first steady event must not run a full presentation")
        self.assertEqual(int(first_counts.static), 0,
            "RED: first steady event must not relayout/render static row 3")

        second = self.event(lua, "t2", "4")
        self.assert_ui(second, "4s", 4.0 / 6.0, "second event")
        second_counts = self.counts(lua, "t2")
        self.assertEqual(int(second_counts.full), 0,
            "RED: second steady event must not run a full presentation")
        self.assertEqual(int(second_counts.static), 0,
            "RED: second steady event must not relayout/render static row 3")


    def test_corrupted_row3_value_repairs_or_fails_closed(self):
        lua = kingpin_lua()
        lua.execute(KINGPIN_ACTIVATE)

        lua.execute(r'''
_R:update(_m, 3.1, .05)
_m:set_player_ability_radial({current = 5.5, total = 6})
_G._t_root, _G._t_row3 = _E._root, _E._rows[3]
_G._t_row3_value, _G._t_row6 = _E._rows[3]._value, _E._rows[6]
_G._t_row3_good = _E._rows[3]._value:text()

local present = _E._present
assert(type(present) == "function", "fixture must expose _E._present")
_G._full_count = 0
_E._present = function(self, ...)
    _G._full_count = _G._full_count + 1
    return present(self, ...)
end

function _G._snap()
    local row3 = _E._rows[3]
    return {full = _G._full_count, row3_good = _G._t_row3_good,
        row3_value = row3._value:text(), e_verify = (_E:verify() == true),
        meter_visible = (_ability_meter:visible() == true),
        icon_visible = (_ability_icon:visible() == true),
        root_visible = (_E._root ~= nil and _E._root:visible() == true),
        same_root = (_E._root == _G._t_root), same_row3 = (row3 == _G._t_row3),
        same_row3_value = (row3._value == _G._t_row3_value),
        same_row6 = (_E._rows[6] == _G._t_row6)}
end
''')

        lua.execute(r'''
_E._rows[3]._value:set_text("BROKEN")
_G._full_count = 0
_m:set_player_ability_radial({current = 4.25, total = 6})
_G._repair = _G._snap()
''')

        repair = lua.globals()["_repair"]
        self.assertGreater(int(repair.full), 0,
            "corrupted row3 value must trigger a full presentation")
        self.assertEqual(repair.row3_value, repair.row3_good,
            "full presentation must repair row3 value")
        self.assertTrue(bool(repair.e_verify), "equipment must verify after repair")
        self.assertFalse(bool(repair.meter_visible), "native meter hidden after repair")
        self.assertFalse(bool(repair.icon_visible), "native icon hidden after repair")

        lua.execute(r'''
local row3 = _E._rows[3]
local orig_set_text = row3._value.set_text
assert(type(orig_set_text) == "function", "row3 value set_text must exist")
row3._value.set_text = function() end
orig_set_text(row3._value, "BROKEN")
_G._full_count = 0
_m:set_player_ability_radial({current = 4, total = 6})
_G._fail = _G._snap()
row3._value.set_text = orig_set_text
''')

        fail = lua.globals()["_fail"]
        self.assertGreater(int(fail.full), 0,
            "failed repair must still attempt a full presentation")
        self.assertEqual(fail.row3_value, "BROKEN",
            "no-op setter must leave row3 value corrupted")
        self.assertTrue(bool(fail.meter_visible), "native meter visible on fail closed")
        self.assertTrue(bool(fail.icon_visible), "native icon visible on fail closed")
        self.assertFalse(bool(fail.root_visible), "owned root hidden on fail closed")

        lua.execute(r'''
_R:update(_m, 3.4, .05)
_G._full_count = 0
_m:set_player_ability_radial({current = 3.9, total = 6})
_G._recover = _G._snap()
''')

        recover = lua.globals()["_recover"]
        self.assertTrue(bool(recover.e_verify), "equipment must verify after recovery")
        self.assertFalse(bool(recover.meter_visible), "native meter hidden after recovery")
        self.assertFalse(bool(recover.icon_visible), "native icon hidden after recovery")
        self.assertEqual(recover.row3_value, recover.row3_good,
            "row3 value must be restored after recovery")
        self.assertTrue(bool(recover.same_root), "root identity must be stable")
        self.assertTrue(bool(recover.same_row3), "row3 identity must be stable")
        self.assertTrue(bool(recover.same_row3_value), "row3 value identity must be stable")
        self.assertTrue(bool(recover.same_row6), "row6 identity must be stable")


    def test_corrupted_row3_value_repairs_even_when_verify_lies(self):
        lua = kingpin_lua()
        lua.execute(KINGPIN_ACTIVATE)
        lua.execute(r'''
_R:update(_m, 3.1, .05)
_m:set_player_ability_radial({current = 5.5, total = 6})
_G._t_row3_good = _E._rows[3]._value:text()

local present = _E._present
assert(type(present) == "function", "fixture must expose _E._present")
_G._full_count = 0
_E._present = function(self, ...)
    _G._full_count = _G._full_count + 1
    return present(self, ...)
end

_E._rows[3]._value:set_text("BROKEN")
_E.verify = function() return true end

_G._full_count = 0
_m:set_player_ability_radial({current = 4.25, total = 6})
_G._lying = {
    full = _G._full_count,
    row3_good = _G._t_row3_good,
    row3_value = _E._rows[3]._value:text(),
}
''')

        lying = lua.globals()["_lying"]
        self.assertGreater(int(lying.full), 0,
            "corrupted row3 value must trigger a full presentation even when verify lies")
        self.assertEqual(lying.row3_value, lying.row3_good,
            "full presentation must restore row3 value even when verify lies")


if __name__ == "__main__":
    unittest.main()
