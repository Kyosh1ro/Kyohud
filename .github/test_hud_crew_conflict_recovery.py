"""Client-only conflict recovery for the owned player block.

No engine run is needed to reproduce the seam: the real ``lua/hud/runtime.lua``
and ``lua/hud/player.lua`` chunks are mounted through ``test_hud_player._lua``
with the local native chain from ``test_hud_player_delayed_replacement`` and the
common-parent geometry helpers from ``test_hud_player_priority_trace``.

A visible native leaf (``radial_absorb_shield_active``) overlaps the owned
player union before the first ``RT:update``. The per-frame priority guard hides
``P._root``; the player module and the delayed-damage seam must recover the exact
same primitives once that native obstacle disappears, without showing the block
again while it persists.

CHARACTERIZATION: on the current code both cases hold. (1) The owned block
recovers on the SAME primitives once the obstacle is removed. (2) While the
obstacle persists the block is hidden at the end of EVERY update, i.e. never
visible at render time — there is no visible flicker. The module's per-update
re-show is masked within the same frame by the guard (the anti-flicker
mechanism); that re-show churn is an invisible performance cost, not a
correctness defect, and is deliberately left out of scope here.
"""
import unittest

from test_hud_player import _lua
from test_hud_player_delayed_replacement import PRELIM, SETUP
from test_hud_player_priority_trace import GEOMETRY

STEP = 0.05

MOUNT_AND_OBSTACLE = r'''
local chain, sent = mount_positive()
local P = kyohud.hud.player
local RT = kyohud.hud.runtime
local mgr = managers.hud
local STEP = 0.05

local saved_root = P._root
local saved_gauge = P._gauge and P._gauge.root or nil
local saved_text = P._downs_text
local saved_bg = P._downs_bg
local saved_cond = P._condition_text
local saved_h5 = P._h5_id_label

local RES = {}
_G._KY_RESULTS = RES

local owned = union_bounds(P)
local owned_present = owned ~= nil
local leaf = nil
local leaf_overlaps_owned = false
local leaf_reachable = false
local leaf_bounds = nil

if owned_present then
    local radial_off = bounds_in_common(chain.radial)
    local anchor = P._gauge and bounds_in_common(P._gauge.root) or owned
    if radial_off and anchor then
        local lw = math.min(anchor.w, 68)
        local lh = math.min(anchor.h, 68)
        if lw < 1 then lw = math.max(anchor.w, 1) end
        if lh < 1 then lh = math.max(anchor.h, 1) end
        local lx = anchor.x - radial_off.x + (anchor.w - lw) * 0.5
        local ly = anchor.y - radial_off.y + (anchor.h - lh) * 0.5
        leaf = chain.radial:bitmap({name = "radial_absorb_shield_active"})
        leaf:set_shape(lx, ly, lw, lh)
        leaf:set_visible(true)
        leaf:set_alpha(1)
        leaf_bounds = bounds_in_common(leaf)
        leaf_overlaps_owned = leaf_bounds ~= nil
            and leaf_bounds.x < owned.x + owned.w
            and leaf_bounds.x + leaf_bounds.w > owned.x
            and leaf_bounds.y < owned.y + owned.h
            and leaf_bounds.y + leaf_bounds.h > owned.y
        leaf_reachable = chain.radial:child("radial_absorb_shield_active") == leaf
    end
end

local vis = {show_count = 0, hide_count = 0}
local original_root_set_visible = P._root.set_visible
P._root.set_visible = function(self, v)
    if v == true then
        vis.show_count = vis.show_count + 1
    elseif v == false then
        vis.hide_count = vis.hide_count + 1
    end
    return original_root_set_visible(self, v)
end

RES.owned_present = owned_present
RES.leaf_overlaps_owned = leaf_overlaps_owned
RES.leaf_reachable = leaf_reachable
RES.missing_leaf = (leaf == nil)
RES.pre_show = vis.show_count
RES.pre_hide = vis.hide_count
if leaf then
    RES.leaf_visible = (leaf:visible() == true)
    RES.leaf_alpha = leaf:alpha()
    RES.leaf_chain_visible = chain_visible(leaf)
    RES.leaf_chain_alpha = chain_alpha(leaf)
end
if owned then
    RES.owned_x = owned.x
    RES.owned_y = owned.y
    RES.owned_w = owned.w
    RES.owned_h = owned.h
end
if leaf_bounds then
    RES.native_x = leaf_bounds.x
    RES.native_y = leaf_bounds.y
    RES.native_w = leaf_bounds.w
    RES.native_h = leaf_bounds.h
end
'''

TEST1_BODY = r'''
if leaf == nil then
    RES.test1_aborted_missing_leaf = true
else
    local t = 1.0
    local function tick()
        RT:update(mgr, t, STEP)
        t = t + STEP
    end

    for _ = 1, 16 do tick() end
    RES.yield_root_visible = (P._root:visible() == true)
    RES.during_show = vis.show_count - RES.pre_show
    RES.during_hide = vis.hide_count - RES.pre_hide
    RES.episode_root_same = (P._root == saved_root)

    leaf:set_visible(false)

    local recovered_at = nil
    for i = 1, 16 do
        tick()
        if recovered_at == nil and P._root:visible() == true then
            recovered_at = i
        end
    end

    RES.recovered_at = recovered_at or -1
    RES.recovery_root_visible = (P._root:visible() == true)
    RES.recovery_same_root = (P._root == saved_root)
    RES.recovery_same_gauge = (P._gauge ~= nil and P._gauge.root == saved_gauge)
    RES.recovery_same_text = (P._downs_text == saved_text)
    RES.recovery_same_bg = (P._downs_bg == saved_bg)
    RES.recovery_same_cond = (P._condition_text == saved_cond)
    RES.h5_saved_present = (saved_h5 ~= nil)
    RES.recovery_same_h5 = (saved_h5 == nil) or (P._h5_id_label == saved_h5)

    vis.show_count = 0
    vis.hide_count = 0
    local seq = {}
    for i = 1, 3 do
        tick()
        seq[i] = (P._root:visible() == true)
    end
    RES.post_show = vis.show_count
    RES.post_hide = vis.hide_count
    RES.post_visible_1 = seq[1]
    RES.post_visible_2 = seq[2]
    RES.post_visible_3 = seq[3]
end
'''

TEST2_BODY = r'''
if leaf == nil then
    RES.test2_aborted_missing_leaf = true
else
    local t = 1.0
    RT:update(mgr, t, STEP)
    t = t + STEP
    RES.first_yield_visible = (P._root:visible() == true)

    -- The yield is "maintained without flicker" when the owned root is hidden
    -- at the END of every update (the priority guard hides last in the frame),
    -- i.e. the block is never visible at render time while the obstacle persists.
    local post = {}
    for i = 1, 20 do
        RT:update(mgr, t, STEP)
        t = t + STEP
        post[i] = (P._root:visible() == true)
    end
    RES.persistent_post_visible = post
    RES.persistent_final_visible = (P._root:visible() == true)
    RES.measured_root_same = (P._root == saved_root)
    RES.leaf_still_visible = (leaf ~= nil and leaf:visible() == true)
end
'''


class HudCrewConflictRecoveryTests(unittest.TestCase):
    def _results(self, lua):
        return lua.globals()._KY_RESULTS

    def _assert_obstacle(self, res):
        self.assertIs(res["owned_present"], True,
                      "the owned player union must be derivable before the first update")
        self.assertIs(res["leaf_overlaps_owned"], True,
                      "the absorb leaf bounds must overlap the owned player union")
        self.assertIs(res["leaf_reachable"], True,
                      "the absorb leaf must be reachable through its native parent name")
        self.assertFalse(bool(res["missing_leaf"]),
                         "the absorb leaf must exist before the first runtime update")
        self.assertIs(res["leaf_visible"], True,
                      "the absorb leaf must start visible")
        self.assertAlmostEqual(float(res["leaf_alpha"]), 1.0, places=5,
                               msg="the absorb leaf must start at alpha 1")
        self.assertIs(res["leaf_chain_visible"], True,
                      "every ancestor of the absorb leaf must report visible")
        self.assertAlmostEqual(float(res["leaf_chain_alpha"]), 1.0, places=5,
                               msg="the absorb leaf ancestry must be fully opaque")

    def test_client_join_yield_then_obstacle_removed_recovers_same_primitives(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + GEOMETRY + MOUNT_AND_OBSTACLE + TEST1_BODY)
        res = self._results(lua)

        self._assert_obstacle(res)
        self.assertEqual(int(res["pre_hide"]), 0,
                         "installing the obstacle must not hide the owned root")
        self.assertEqual(int(res["pre_show"]), 0,
                         "installing the obstacle must not show the owned root")

        self.assertIs(res["yield_root_visible"], False,
                      "the overlapping native leaf must yield the owned player block")
        self.assertIs(res["episode_root_same"], True,
                      "yielding must keep the owned root identity")
        self.assertGreater(int(res["during_hide"]), 0,
                           "the priority guard must actually hide the owned root")

        self.assertGreaterEqual(int(res["recovered_at"]), 1,
                                "the block must recover after the native obstacle ends")
        self.assertIs(res["recovery_root_visible"], True,
                      "P._root must be visible after the obstacle is removed")
        self.assertIs(res["recovery_same_root"], True,
                      "recovery must reuse the saved player root")
        self.assertIs(res["recovery_same_gauge"], True,
                      "recovery must reuse the saved gauge root")
        self.assertIs(res["recovery_same_text"], True,
                      "recovery must reuse the saved downs text")
        self.assertIs(res["recovery_same_bg"], True,
                      "recovery must reuse the saved downs background")
        self.assertIs(res["recovery_same_cond"], True,
                      "recovery must reuse the saved condition text")
        self.assertIs(res["recovery_same_h5"], True,
                      "recovery must reuse the saved H5 label when present")

        self.assertIs(res["post_visible_1"], True,
                      "first post-recovery update must keep the root visible")
        self.assertIs(res["post_visible_2"], True,
                      "second post-recovery update must keep the root visible")
        self.assertIs(res["post_visible_3"], True,
                      "third post-recovery update must keep the root visible")
        self.assertEqual(int(res["post_hide"]), 0,
                         "post-recovery window must add zero set_visible(false) calls")

    def test_persistent_leaf_keeps_yield_without_flicker(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + GEOMETRY + MOUNT_AND_OBSTACLE + TEST2_BODY)
        res = self._results(lua)

        self._assert_obstacle(res)
        self.assertIs(res["first_yield_visible"], False,
                      "the first update must already yield the owned root")
        self.assertIs(res["persistent_final_visible"], False,
                      "the owned root must stay hidden while the obstacle persists")
        self.assertIs(res["measured_root_same"], True,
                      "the persistent yield must keep the owned root identity")
        self.assertIs(res["leaf_still_visible"], True,
                      "the obstacle must remain visible for the whole measurement")
        post_values = list(res["persistent_post_visible"].values())
        self.assertEqual(len(post_values), 20,
                         "the window must sample every update")
        self.assertTrue(all(v is False for v in post_values),
                        "the owned root must be hidden at the end of every update "
                        "while the obstacle persists (no visible flicker)")


if __name__ == "__main__":
    unittest.main()
