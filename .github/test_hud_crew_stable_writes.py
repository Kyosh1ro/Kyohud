"""RED contract: stabilized crew updates must stop redundant native writes/allocs.

Transition under test (crew presentation, not collection)
--------------------------------------------------------
The crew snapshot is collected at 0.5 s (CREW_POLL_INTERVAL) while presentation
runs at 0.05 s (PRESENT_INTERVAL). On a STABILIZED non-poll update (no snapshot
change, identical layout geometry, identical cards, regular increasing t) the
real `CREW:update` still redoes the whole presentation today:

1. `CREW:_apply_layout` calls `set_shape` on the owned crew root and
   `card:set_geometry(...)` for the three cards without an equality guard.
2. `Card:set_geometry` rebuilds `self._geo` (fresh table) on every call and
   runs the local equality-guarded `shape(self.root, ...)` helper.
3. `CREW:update` calls `set_alpha(1)` on the crew root without a guard.
4. `Card:update` calls `shape(self.root, ...)`, `self.root:set_visible(true)`
   and `self.root:set_alpha(1)` without guards at the start of its pcall block
   (the rest of that block is already guarded).
5. `Card:_rows` allocates a fresh table once per card per update.

RED observed today, measured by static reading of `lua/hud/crew.lua` and
`lua/hud/components/crew_card.lua` (no Lua interpreter is available in this
test-only pass), on one stabilized non-poll update:

* crew root native writes: `set_shape` x1 (`_apply_layout`) + `set_alpha` x1
  (`CREW:update`) + `set_visible` x1 (`_present_cards`) = 3.
* each card root: `set_visible` x1 + `set_alpha` x1 from `Card:update` = 2 per
  card, so 6 for the three cards. The native `set_shape` calls made by
  `Card:set_geometry` and `Card:update` go through the local equality-guarded
  `shape` helper: when the geometry already matches they perform no native
  write, but `_geo` is nevertheless rebuilt.
* therefore root + card-root native writes are >= 9 per stabilized update
  (3 root + 6 card roots); the card part is >= 6 and never 0.
* `_geo`: 3 fresh tables per update.
* `_rows`: one invocation and one fresh table per card per update (3 tables);
  the returned identities change between updates.

GREEN budgets required after the pending production work
--------------------------------------------------------
* 0 crew-root + card-root native writes on a stabilized update.
* the same `_geo` table identity across two consecutive stabilized updates.
* at most 1 `_rows` invocation per card per update and the same returned table
  identity (reuse when `h`/`body_offset` are unchanged).
* `CREW:_verify_render` still runs exactly once per measured update and stays
  true: certification is per-frame by design and is never memoized/skipped.

Fixture
-------
`test_hud_local_h5_lifecycle._local_runtime` is reused because it mounts the
real player/weapons/crew consumers, acquires the H5 groups (positive baseline)
and installs the genuine native `HUDManager:set_teammate_revives` channel used
by the snapshot-change contract. Measurement calls target `CREW:update`
directly, after a real collection poll and warm-up frames, so poll/present
sentinel fields are the real production ones and are only read (never
reimplemented).

Observability notes
-------------------
* `Card:_rows` is a local function reachable only through the `Card` metatable
  as an instance method. It is wrapped per card to count real production
  invocations and record the actual returned table. If future production reuses
  a table without re-invoking `_rows`, the previous identity is retained, so
  reuse is still observable.
* `Card:set_geometry` is likewise counted through the real instance method;
  native geometry writes are counted by wrapping `set_shape` on the primitive.
* The fixture exposes no native clearance event. The real driver used for the
  geometry contract is `CREW._layout_cache.state_h`, the exact field consumed
  by `_apply_layout` for root height and card y; changing it is the closest
  genuine geometry change available without unrelated mount churn.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_local_h5_lifecycle import _local_runtime


PREPARE = r'''
local CREW = kyohud.hud.crew
local mgr = managers.hud
local RT = kyohud.hud.runtime

assert(CREW and CREW._root and CREW._root:visible() == true,
    "crew root must be mounted and visible")
_G._baseline_verify = CREW:_verify_render() == true
_G._baseline_visible = CREW._root:visible() == true

local all_cards = true
for i = 1, 3 do
    local card = CREW._cards[i]
    if not (card and card.root and card.root:visible() == true) then
        all_cards = false
    end
end
_G._baseline_cards = all_cards
_G._baseline_crew_group = RT._h5_groups ~= nil and RT._h5_groups["crew_2"] ~= nil

local last_poll = CREW._last_poll_time or 0
local t_poll = last_poll + 0.6
CREW:update(mgr, t_poll, 0.05)
CREW:update(mgr, t_poll + 0.1, 0.05)
CREW:update(mgr, t_poll + 0.2, 0.05)
_G._warm_t_poll = t_poll
'''


class CrewStableWriteTests(unittest.TestCase):

    def test_stabilized_update_has_zero_native_writes_and_reuses_tables(self):
        """RED: two stabilized presents must not rewrite native state.

        A real collection poll and two warm-up presents settle the cards. The
        native `set_shape`/`set_alpha`/`set_visible` setters of the crew root
        and of each card root are then wrapped, and two consecutive non-poll
        presents (t+0.3, t+0.4, both above PRESENT_INTERVAL) are measured. The
        second present must perform 0 root/card-root native writes, keep the
        same `_geo` table per card, invoke `_rows` at most once per card and
        reuse the same returned table, while `_verify_render` runs exactly once
        per present and stays true. Today the writes are >= 9, `_geo` is
        rebuilt and `_rows` returns fresh tables, so this test is RED.
        """
        lua = _local_runtime()
        lua.execute(PREPARE + r'''
local CREW = kyohud.hud.crew
local mgr = managers.hud
local t_poll = _G._warm_t_poll
local t_a = t_poll + 0.3
local t_b = t_poll + 0.4

local probe = {
    root_shape = 0, root_alpha = 0, root_visible = 0,
    card_shape = 0, card_alpha = 0, card_visible = 0,
    verify_calls = 0, verify_result = false,
    rows_count = {}, rows_out = {},
}
_G._stable_probe = probe

local function wrap_setter(obj, name, field)
    local original = obj[name]
    assert(type(original) == "function", "missing primitive setter " .. name)
    obj[name] = function(self, ...)
        probe[field] = probe[field] + 1
        return original(self, ...)
    end
end

wrap_setter(CREW._root, "set_shape", "root_shape")
wrap_setter(CREW._root, "set_alpha", "root_alpha")
wrap_setter(CREW._root, "set_visible", "root_visible")
for i = 1, 3 do
    local card = CREW._cards[i]
    assert(card and card.root, "card root missing at position " .. tostring(i))
    wrap_setter(card.root, "set_shape", "card_shape")
    wrap_setter(card.root, "set_alpha", "card_alpha")
    wrap_setter(card.root, "set_visible", "card_visible")
end

for i = 1, 3 do
    local card = CREW._cards[i]
    local original_rows = card._rows
    assert(type(original_rows) == "function", "Card:_rows must exist")
    local index = i
    card._rows = function(self, ...)
        probe.rows_count[index] = (probe.rows_count[index] or 0) + 1
        local out = original_rows(self, ...)
        probe.rows_out[index] = out
        return out
    end
end

local original_verify = CREW._verify_render
CREW._verify_render = function(self, ...)
    probe.verify_calls = probe.verify_calls + 1
    local result = original_verify(self, ...)
    probe.verify_result = result == true
    return result
end

local function reset_counters()
    probe.root_shape = 0; probe.root_alpha = 0; probe.root_visible = 0
    probe.card_shape = 0; probe.card_alpha = 0; probe.card_visible = 0
    probe.verify_calls = 0; probe.verify_result = false
    probe.rows_count = {}
end

probe.rows_out = {}
reset_counters()
local poll_before_a = CREW._last_poll_time
CREW:update(mgr, t_a, 0.05)
_G._meas_a_polled = CREW._last_poll_time ~= poll_before_a
_G._meas_a_ran = CREW._update_ran_now == true
_G._writes_a_root = probe.root_shape + probe.root_alpha + probe.root_visible
_G._writes_a_card = probe.card_shape + probe.card_alpha + probe.card_visible
_G._verify_calls_a = probe.verify_calls
_G._verify_ok_a = probe.verify_result

local geo_a, rows_a = {}, {}
for i = 1, 3 do
    geo_a[i] = CREW._cards[i]._geo
    rows_a[i] = probe.rows_out[i]
end
_G._rows_a_present = rows_a[1] ~= nil and rows_a[2] ~= nil and rows_a[3] ~= nil

reset_counters()
local poll_before_b = CREW._last_poll_time
CREW:update(mgr, t_b, 0.05)
_G._meas_b_polled = CREW._last_poll_time ~= poll_before_b
_G._meas_b_ran = CREW._update_ran_now == true
_G._writes_b_root = probe.root_shape + probe.root_alpha + probe.root_visible
_G._writes_b_card = probe.card_shape + probe.card_alpha + probe.card_visible
_G._verify_calls_b = probe.verify_calls
_G._verify_ok_b = probe.verify_result

_G._geo_same_1 = CREW._cards[1]._geo == geo_a[1]
_G._geo_same_2 = CREW._cards[2]._geo == geo_a[2]
_G._geo_same_3 = CREW._cards[3]._geo == geo_a[3]
_G._rows_same_1 = probe.rows_out[1] == rows_a[1]
_G._rows_same_2 = probe.rows_out[2] == rows_a[2]
_G._rows_same_3 = probe.rows_out[3] == rows_a[3]
_G._rows_count_b_1 = probe.rows_count[1] or 0
_G._rows_count_b_2 = probe.rows_count[2] or 0
_G._rows_count_b_3 = probe.rows_count[3] or 0
_G._rows_b_present = probe.rows_out[1] ~= nil
    and probe.rows_out[2] ~= nil and probe.rows_out[3] ~= nil
''')
        g = lua.globals()
        self.assertIs(g._baseline_verify, True,
                      "baseline: crew render must start certified")
        self.assertIs(g._baseline_visible, True,
                      "baseline: crew root must start visible")
        self.assertIs(g._baseline_cards, True,
                      "baseline: all three card roots must start visible")
        self.assertIs(g._baseline_crew_group, True,
                      "baseline: crew_2 H5 group must start acquired")
        self.assertIs(g._meas_a_polled, False,
                      "measurement A must not be a collection poll")
        self.assertIs(g._meas_b_polled, False,
                      "measurement B must not be a collection poll")
        self.assertIs(g._meas_a_ran, True,
                      "measurement A must pass the presentation throttle")
        self.assertIs(g._meas_b_ran, True,
                      "measurement B must pass the presentation throttle")

        root_writes = int(g._writes_b_root)
        card_writes = int(g._writes_b_card)
        self.assertEqual(
            root_writes, 0,
            "GREEN needs 0 crew-root native writes on a stabilized present; "
            f"RED observed {root_writes} set_shape/set_alpha/set_visible calls")
        self.assertEqual(
            card_writes, 0,
            "GREEN needs 0 card-root native writes on a stabilized present; "
            f"RED observed {card_writes} set_shape/set_alpha/set_visible calls")

        for index in (1, 2, 3):
            self.assertIs(
                getattr(g, f"_geo_same_{index}"), True,
                f"card {index} must keep the same _geo table across stabilized "
                "presents; RED rebuilt it on every set_geometry call")
        self.assertIs(g._rows_a_present, True,
                      "measured update A must expose the real _rows result")
        self.assertIs(g._rows_b_present, True,
                      "measured update B must expose the real _rows result")
        for index in (1, 2, 3):
            self.assertLessEqual(
                int(getattr(g, f"_rows_count_b_{index}")), 1,
                f"card {index} may invoke Card:_rows at most once per "
                "stabilized present")
            self.assertIs(
                getattr(g, f"_rows_same_{index}"), True,
                f"card {index} must reuse the same _rows table across "
                "stabilized presents when h/body_offset are unchanged")

        self.assertEqual(int(g._verify_calls_a), 1,
                         "CREW:_verify_render must run exactly once per measured present A")
        self.assertEqual(int(g._verify_calls_b), 1,
                         "CREW:_verify_render must run exactly once per measured present B")
        self.assertIs(g._verify_ok_a, True,
                      "certification must stay true on measured present A")
        self.assertIs(g._verify_ok_b, True,
                      "certification must stay true on measured present B")

    def test_real_snapshot_change_rewrites_and_stays_certified(self):
        """Contract: a genuine occupant change must still rewrite and certify.

        After a real poll and warm-up, the genuine native
        `HUDManager:set_teammate_revives` channel changes the human occupant's
        downs (3 -> 4). The next non-poll present must re-render the card
        content (native writes > 0 on owned primitives), update the downs text,
        keep the same owned primitives and stay certified. This must hold both
        today and after the pending write-suppression work. Geometry is
        unchanged by this content-only change, so `_geo` reuse is expected and
        not treated as a rewrite; the geometry contract is covered separately.
        """
        lua = _local_runtime()
        lua.execute(PREPARE + r'''
local CREW = kyohud.hud.crew
local ACT = kyohud.hud.actors
local mgr = managers.hud
local t_poll = _G._warm_t_poll
local t_change = t_poll + 0.3

local snapshot = ACT:get_crew_snapshot()
local human
for _, entry in ipairs(snapshot) do
    if entry.ai == false then human = entry end
end
assert(human and human.position and human.slot,
    "the human crew occupant must be published with position and slot")
local human_position = human.position
local human_slot = human.slot

local probe = { writes = 0 }
_G._content_probe = probe

local setter_names = {
    "set_shape", "set_color", "set_alpha", "set_visible",
    "set_text", "set_font_size", "set_image", "set_align",
}
local function wrap_primitive(primitive)
    for _, name in ipairs(setter_names) do
        local original = primitive[name]
        if type(original) == "function" then
            primitive[name] = function(self, ...)
                probe.writes = probe.writes + 1
                return original(self, ...)
            end
        end
    end
end

local primitive_keys = {
    "_backdrop", "_name_text", "_peer_dot", "_rank_text",
    "_hp_bg", "_health_fill", "_health_text",
    "_ar_bg", "_armor_fill", "_armor_text",
    "_weapon_text", "_reserve_text", "_inactive_ammo_text",
    "_equipment_text", "_cables_text", "_projectile_text",
    "_deployable_icon", "_cables_icon", "_projectile_icon",
    "_interaction_text", "_status_text",
    "_downs_icon", "_downs_text", "_downs_label",
    "_state_bg", "_condition_icon",
    "_down_top", "_down_bottom", "_down_left", "_down_right",
}
wrap_primitive(CREW._root)
for i = 1, 3 do
    local card = CREW._cards[i]
    wrap_primitive(card.root)
    for _, key in ipairs(primitive_keys) do
        local primitive = card[key]
        if type(primitive) == "table" then wrap_primitive(primitive) end
    end
end

local function find_by_slot(snapshot, slot)
    for _, entry in ipairs(snapshot) do
        if entry.slot == slot then return entry end
    end
    return nil
end

local crew_root_before = CREW._root
local card = CREW._cards[human_position]
assert(card and card.root, "human card must exist")
local card_root_before = card.root
local downs_primitive_before = card._downs_text
local downs_text_before = downs_primitive_before:text()
local before_entry = find_by_slot(snapshot, human_slot)
assert(before_entry, "the human slot must exist in the initial snapshot")
local downs_before = before_entry.downs

mgr:set_teammate_revives(human_slot, 5)

local after_entry = find_by_slot(ACT:get_crew_snapshot(), human_slot)
assert(after_entry, "the human slot must exist after the genuine revives event")
local downs_after = after_entry.downs

probe.writes = 0
local poll_before = CREW._last_poll_time
CREW:update(mgr, t_change, 0.05)
_G._change_polled = CREW._last_poll_time ~= poll_before
_G._change_ran = CREW._update_ran_now == true
_G._change_writes = probe.writes
_G._snapshot_downs_before = downs_before
_G._snapshot_downs_after = downs_after
_G._down_text_before = downs_text_before
_G._down_text_after = CREW._cards[human_position]._downs_text:text()
_G._same_crew_root = CREW._root == crew_root_before
_G._same_card_root = CREW._cards[human_position].root == card_root_before
_G._same_downs_primitive =
    CREW._cards[human_position]._downs_text == downs_primitive_before
_G._verify_after_change = CREW:_verify_render() == true
''')
        g = lua.globals()
        self.assertIs(g._baseline_verify, True,
                      "baseline: crew render must start certified")
        self.assertIs(g._baseline_visible, True,
                      "baseline: crew root must start visible")
        self.assertIs(g._baseline_cards, True,
                      "baseline: all three card roots must start visible")
        self.assertIs(g._change_polled, False,
                      "the measured change present must not be a collection poll")
        self.assertIs(g._change_ran, True,
                      "the measured change present must pass the throttle")

        self.assertEqual(float(g._snapshot_downs_before), 3.0,
                         "baseline: the human occupant must publish downs 3")
        self.assertEqual(float(g._snapshot_downs_after), 4.0,
                         "the genuine revives channel must publish downs 4")
        self.assertEqual(g._down_text_before, "3",
                         "baseline: the human card must show downs 3")
        self.assertEqual(g._down_text_after, "4",
                         "a real snapshot change must be rendered as downs 4")
        self.assertGreater(
            int(g._change_writes), 0,
            "a real occupant change must still perform native writes")
        self.assertIs(g._verify_after_change, True,
                      "the crew must stay certified after a real change")
        self.assertIs(g._same_crew_root, True,
                      "the crew root identity must be preserved across changes")
        self.assertIs(g._same_card_root, True,
                      "the card root identity must be preserved across changes")
        self.assertIs(g._same_downs_primitive, True,
                      "the downs text primitive identity must be preserved")

    def test_real_layout_change_rewrites_geometry(self):
        """Contract: a real geometry change must not be frozen by caching.

        A real state-height change is applied to the production layout cache
        (`_layout_cache.state_h`, consumed by `_apply_layout` for root height
        and each card y). The next non-poll present must run the geometry
        setters again: native `set_shape` on the crew root and on the card
        roots, plus `Card:set_geometry` per card. Root and card y must actually
        move and the render must stay certified.
        """
        lua = _local_runtime()
        lua.execute(PREPARE + r'''
local CREW = kyohud.hud.crew
local mgr = managers.hud
local t_poll = _G._warm_t_poll
local t_geom = t_poll + 0.3

assert(CREW._layout_cache and CREW._layout_cache.state_h,
    "layout cache must expose state_h")
local probe = { root_shape = 0, card_shape = 0, geometry_calls = 0 }
_G._geometry_probe = probe

local root_shape_original = CREW._root.set_shape
CREW._root.set_shape = function(self, ...)
    probe.root_shape = probe.root_shape + 1
    return root_shape_original(self, ...)
end
for i = 1, 3 do
    local card = CREW._cards[i]
    assert(card and card.root, "card root missing at position " .. tostring(i))
    local shape_original = card.root.set_shape
    card.root.set_shape = function(self, ...)
        probe.card_shape = probe.card_shape + 1
        return shape_original(self, ...)
    end
    local geometry_original = card.set_geometry
    assert(type(geometry_original) == "function", "Card:set_geometry must exist")
    card.set_geometry = function(self, ...)
        probe.geometry_calls = probe.geometry_calls + 1
        return geometry_original(self, ...)
    end
end

local root_y_before = CREW._root:y()
local card_y_before = CREW._cards[2].root:y()
local old_state_h = CREW._layout_cache.state_h
CREW._layout_cache.state_h = old_state_h + 5

probe.root_shape = 0; probe.card_shape = 0; probe.geometry_calls = 0
local poll_before = CREW._last_poll_time
CREW:update(mgr, t_geom, 0.05)
_G._geom_polled = CREW._last_poll_time ~= poll_before
_G._geom_ran = CREW._update_ran_now == true
_G._geom_root_writes = probe.root_shape
_G._geom_card_writes = probe.card_shape
_G._geom_set_geometry_calls = probe.geometry_calls
_G._geom_state_h_before = old_state_h
_G._geom_state_h_after = CREW._layout_cache.state_h
_G._geom_root_y_changed = CREW._root:y() ~= root_y_before
_G._geom_card_y_changed = CREW._cards[2].root:y() ~= card_y_before
_G._geom_verify = CREW:_verify_render() == true
''')
        g = lua.globals()
        self.assertIs(g._baseline_verify, True,
                      "baseline: crew render must start certified")
        self.assertIs(g._baseline_visible, True,
                      "baseline: crew root must start visible")
        self.assertIs(g._baseline_cards, True,
                      "baseline: all three card roots must start visible")
        self.assertIs(g._geom_polled, False,
                      "the measured geometry present must not be a collection poll")
        self.assertIs(g._geom_ran, True,
                      "the measured geometry present must pass the throttle")

        self.assertEqual(float(g._geom_state_h_after),
                         float(g._geom_state_h_before) + 5.0,
                         "the real state-height change must be applied")
        self.assertGreaterEqual(
            int(g._geom_root_writes), 1,
            "a real root geometry change must still write the crew root shape")
        self.assertGreaterEqual(
            int(g._geom_card_writes), 3,
            "a real card geometry change must still write all three card roots")
        self.assertGreaterEqual(
            int(g._geom_set_geometry_calls), 3,
            "a real geometry change must still run Card:set_geometry on each card")
        self.assertIs(g._geom_root_y_changed, True,
                      "the crew root y must actually move after the change")
        self.assertIs(g._geom_card_y_changed, True,
                      "the card root y must actually move after the change")
        self.assertIs(g._geom_verify, True,
                      "the crew must stay certified after a real geometry change")

    def test_verify_render_runs_once_per_measured_present(self):
        """Invariant: per-frame certification is never memoized or skipped.

        On two stabilized non-poll presents, the real `CREW:_verify_render`
        wrapper must see exactly one invocation per present, each returning
        true, with the production `_render_verified` flag true. This passes
        today and must keep passing after write suppression.
        """
        lua = _local_runtime()
        lua.execute(PREPARE + r'''
local CREW = kyohud.hud.crew
local mgr = managers.hud
local t_poll = _G._warm_t_poll
local t_a = t_poll + 0.3
local t_b = t_poll + 0.4

local probe = { calls = 0, result = false }
local original_verify = CREW._verify_render
CREW._verify_render = function(self, ...)
    probe.calls = probe.calls + 1
    local result = original_verify(self, ...)
    probe.result = result == true
    return result
end

probe.calls = 0
local poll_before_a = CREW._last_poll_time
CREW:update(mgr, t_a, 0.05)
_G._verify_a_calls = probe.calls
_G._verify_a_result = probe.result
_G._verify_a_flag = CREW._render_verified == true
_G._verify_a_polled = CREW._last_poll_time ~= poll_before_a
_G._verify_a_ran = CREW._update_ran_now == true

probe.calls = 0
local poll_before_b = CREW._last_poll_time
CREW:update(mgr, t_b, 0.05)
_G._verify_b_calls = probe.calls
_G._verify_b_result = probe.result
_G._verify_b_flag = CREW._render_verified == true
_G._verify_b_polled = CREW._last_poll_time ~= poll_before_b
_G._verify_b_ran = CREW._update_ran_now == true
''')
        g = lua.globals()
        self.assertIs(g._baseline_verify, True,
                      "baseline: crew render must start certified")
        self.assertIs(g._verify_a_polled, False,
                      "measured present A must not be a collection poll")
        self.assertIs(g._verify_b_polled, False,
                      "measured present B must not be a collection poll")
        self.assertIs(g._verify_a_ran, True,
                      "measured present A must pass the throttle")
        self.assertIs(g._verify_b_ran, True,
                      "measured present B must pass the throttle")
        self.assertEqual(int(g._verify_a_calls), 1,
                         "CREW:_verify_render must run exactly once on present A")
        self.assertEqual(int(g._verify_b_calls), 1,
                         "CREW:_verify_render must run exactly once on present B")
        self.assertIs(g._verify_a_result, True,
                      "CREW:_verify_render must stay true on present A")
        self.assertIs(g._verify_b_result, True,
                      "CREW:_verify_render must stay true on present B")
        self.assertIs(g._verify_a_flag, True,
                      "_render_verified must be true after present A")
        self.assertIs(g._verify_b_flag, True,
                      "_render_verified must be true after present B")


if __name__ == '__main__':
    unittest.main()
