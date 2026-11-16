"""Local Ex-President reserve native replacement, bounded RED characterization.

Scope: the local player native radial reserve leaves only. The real runtime,
player, actors, gauge and native_visibility chunks are loaded through
test_hud_player._lua and the shared delayed-replacement fixture SETUP/PRELIM.
The native local teammate chain is built at the owned player rectangle and the
exact native reserve leaves are added under player/radial_health_panel:

  mgr._teammate_panels[HUDManager.PLAYER_PANEL]._panel
    -> player -> radial_health_panel
       -> radial_rip      (original alpha .63, visible)
       -> radial_rip_bg   (original alpha .81, visible)

Native set_stored_health/set_stored_health_max change visible and color, never
alpha. KyoHUD must therefore hide the two duplicate reserve leaves through alpha
0, preserve their native visibility and every parent property, and restore the
differing original alphas exactly when the owned reserve coverage disappears or
the replacement cannot be certified. None of the tests write production
snapshots or monkeypatch certification helpers; they only drive ordinary
RT:update calls and mutate the live source.

The reserve assertions count only RESERVE-owned native_visibility alpha entries
on the two rip leaves. The approved H5 path may independently zero the ordinary
radial_health and radial_shield leaves, so that coexistence is not a reserve leak.
"""
import unittest

from test_hud_player import _lua
from test_hud_player_delayed_replacement import PRELIM, SETUP

RESERVE_PRELIM = PRELIM + r'''
local function install_reserve_rips(chain)
    local pw, ph = chain.pw, chain.ph
    local rip = chain.radial:bitmap({name = "radial_rip", layer = 3})
    rip:set_shape(0, 0, pw, ph)
    rip:set_visible(true)
    rip:set_alpha(0.63)
    local rip_bg = chain.radial:bitmap({name = "radial_rip_bg", layer = 1})
    rip_bg:set_shape(0, 0, pw, ph)
    rip_bg:set_visible(true)
    rip_bg:set_alpha(0.81)
    return rip, rip_bg
end

local function mount_reserve()
    local chain, sent = mount_positive()
    cd._health = 100
    cd._health_max = 100
    cd._armor = 50
    cd._armor_max = 50
    cd._remaining_delayed = 0
    cd._stored_health_amount = 20
    cd._max_stored_health_amount = 40
    chain.armor:set_visible(false)
    chain.health:set_visible(false)
    sync_native(chain)
    local rip, rip_bg = install_reserve_rips(chain)
    return chain, sent, rip, rip_bg
end

local NV = kyohud.hud.native_visibility
local RESERVE_OWNER = "kyohud_reserve_replacement"

local function reserve_entries()
    local out = {}
    for _, entry in ipairs(NV._entries or {}) do
        if entry.owner == RESERVE_OWNER then out[#out + 1] = entry end
    end
    return out
end

local function reserve_count()
    return #reserve_entries()
end

-- Exactly two RESERVE-owned alpha leases, on the two rip leaves, no extra leaf.
-- The approved H5 path may independently zero the ordinary radial_health and
-- radial_shield leaves, so their alpha is deliberately not counted here.
local function reserve_is_exact(rip, rip_bg)
    local entries = reserve_entries()
    if #entries ~= 2 then return false end
    local seen_rip, seen_rip_bg = false, false
    for _, entry in ipairs(entries) do
        if entry.property ~= "alpha" then return false end
        if not near(entry.applied_value, 0, 0.0001) then return false end
        if entry.object == rip then
            if seen_rip then return false end
            seen_rip = true
        elseif entry.object == rip_bg then
            if seen_rip_bg then return false end
            seen_rip_bg = true
        else
            return false
        end
    end
    return seen_rip and seen_rip_bg
end

local function reserve_marker(rip)
    local entry = NV._whitelist[rip]
    return entry ~= nil and entry.alpha == true
end

local function sentinel_snapshot(sent)
    return {
        leaf = sent.leaf:alpha(),
        panel = props(sent.panel),
        rarmor = sent.rarmor:alpha(),
        rhealth = sent.rhealth:alpha(),
        remote = props(sent.remote),
    }
end

local function same_sentinel(sent, saved)
    return near(sent.leaf:alpha(), saved.leaf)
        and same_props(props(sent.panel), saved.panel)
        and near(sent.rarmor:alpha(), saved.rarmor)
        and near(sent.rhealth:alpha(), saved.rhealth)
        and same_props(props(sent.remote), saved.remote)
end
'''

RESERVE_POSITIVE = r'''
local chain, sent, rip, rip_bg = mount_reserve()
local parents = chain_props(chain)
local sentinel = sentinel_snapshot(sent)
local owned_root = P._root
local gauge_root = P._gauge.root

RT:update(mgr, 1.0, 0.1)

_positive_visible = P._root:visible()
_positive_verify = P:verify() == true
_positive_rip_alpha = rip:alpha()
_positive_rip_bg_alpha = rip_bg:alpha()
_positive_rip_visible = rip:visible()
_positive_rip_bg_visible = rip_bg:visible()
_positive_reserve_exact = reserve_is_exact(rip, rip_bg)
_positive_reserve_count = reserve_count()
_positive_same_primitives = rip == chain.radial:child("radial_rip")
    and rip_bg == chain.radial:child("radial_rip_bg")
    and rip:parent() == chain.radial
    and rip_bg:parent() == chain.radial
_positive_owned_identity = P._root == owned_root
    and P._gauge.root == gauge_root
_positive_parents_unchanged = same_chain_props(chain, parents)
_positive_sentinels_unchanged = same_sentinel(sent, sentinel)
_positive_bg_visible = P._gauge._stored_health_bg ~= nil
    and P._gauge._stored_health_bg:visible()
_positive_bg_w = P._gauge._stored_health_bg and P._gauge._stored_health_bg:w() or 0
_positive_fill_w = P._gauge._stored_health_fill
    and P._gauge._stored_health_fill:w() or 0

cd._stored_health_amount = 0
cd._max_stored_health_amount = 40
RT:update(mgr, 1.1, 0.1)

_zero_visible = P._root:visible()
_zero_verify = P:verify() == true
_zero_rip_alpha = rip:alpha()
_zero_rip_bg_alpha = rip_bg:alpha()
_zero_rip_visible = rip:visible()
_zero_rip_bg_visible = rip_bg:visible()
_zero_reserve_exact = reserve_is_exact(rip, rip_bg)
_zero_reserve_count = reserve_count()
_zero_bg_visible = P._gauge._stored_health_bg ~= nil
    and P._gauge._stored_health_bg:visible()
_zero_bg_w = P._gauge._stored_health_bg and P._gauge._stored_health_bg:w() or 0
_zero_fill_visible = P._gauge._stored_health_fill ~= nil
    and P._gauge._stored_health_fill:visible()
_zero_fill_w = P._gauge._stored_health_fill
    and P._gauge._stored_health_fill:w() or 0

kyohud.settings.enable_player = false
RT:refresh_settings(mgr)
RT:update(mgr, 1.2, 0.1)

_off_root = P._root
_off_rip_alpha = rip:alpha()
_off_rip_bg_alpha = rip_bg:alpha()
_off_rip_visible = rip:visible()
_off_rip_bg_visible = rip_bg:visible()
_off_same_primitives = rip == chain.radial:child("radial_rip")
    and rip_bg == chain.radial:child("radial_rip_bg")
_off_reserve_count = reserve_count()
'''

RESERVE_NEGATIVE = r'''
local chain, sent, rip, rip_bg = mount_reserve()
local owned_root = P._root
local gauge_root = P._gauge.root

RT:update(mgr, 1.0, 0.1)
_negative_positive_visible = P._root:visible()
_negative_positive_rip = rip:alpha()
_negative_positive_rip_bg = rip_bg:alpha()

local original_max_stored = cd.max_armor_stored_health
cd.max_armor_stored_health = nil
RT:update(mgr, 1.1, 0.1)
_missing_rip = rip:alpha()
_missing_rip_bg = rip_bg:alpha()
_missing_visible = P._root:visible()
_missing_same_primitives = rip == chain.radial:child("radial_rip")
    and rip_bg == chain.radial:child("radial_rip_bg")
_missing_native_visible = rip:visible() and rip_bg:visible()

cd.max_armor_stored_health = original_max_stored
RT:update(mgr, 1.2, 0.1)
_recovered_rip = rip:alpha()
_recovered_rip_bg = rip_bg:alpha()
_recovered_visible = P._root:visible()
_recovered_same_primitives = P._root == owned_root
    and P._gauge.root == gauge_root
    and rip == chain.radial:child("radial_rip")
    and rip_bg == chain.radial:child("radial_rip_bg")

cd.max_armor_stored_health = function(self) return 0 / 0 end
RT:update(mgr, 1.3, 0.1)
_nan_rip = rip:alpha()
_nan_rip_bg = rip_bg:alpha()
_nan_visible = P._root:visible()
_nan_native_visible = rip:visible() and rip_bg:visible()

cd.max_armor_stored_health = original_max_stored
RT:update(mgr, 1.4, 0.1)
_nan_recovered_rip = rip:alpha()
_nan_recovered_rip_bg = rip_bg:alpha()
_nan_recovered_visible = P._root:visible()
_nan_recovered_same_primitives = P._root == owned_root
    and P._gauge.root == gauge_root
    and rip == chain.radial:child("radial_rip")
    and rip_bg == chain.radial:child("radial_rip_bg")
'''

RESERVE_THROTTLE = r'''
local chain, sent, rip, rip_bg = mount_reserve()
local parents = chain_props(chain)
local sentinel = sentinel_snapshot(sent)

RT:update(mgr, 1.0, 0.1)
_thr_positive_exact = reserve_is_exact(rip, rip_bg)

-- Stock changes on a throttled player frame (< 0.05 s). The reserve lease must
-- be re-certified from the fresh live stock instead of a cached render.
cd._stored_health_amount = 40
cd._max_stored_health_amount = 40
RT:update(mgr, 1.01, 0.01)

_thr_verify = P:verify() == true
_thr_same_primitives = rip == chain.radial:child("radial_rip")
    and rip_bg == chain.radial:child("radial_rip_bg")
_thr_reserve_exact = reserve_is_exact(rip, rip_bg)
_thr_reserve_count = reserve_count()
_thr_bg_w = P._gauge._stored_health_bg and P._gauge._stored_health_bg:w() or 0
_thr_fill_w = P._gauge._stored_health_fill and P._gauge._stored_health_fill:w() or 0
local thr_stored = P._gauge._health_effects and P._gauge._health_effects.stored_health or nil
_thr_stored_ratio = thr_stored and thr_stored.ratio or -1
_thr_max_ratio = thr_stored and thr_stored.max_ratio or -1
_thr_parents_unchanged = same_chain_props(chain, parents)
_thr_sentinel_unchanged = same_sentinel(sent, sentinel)
'''

RESERVE_FILL_CORRUPTION = r'''
local chain, sent, rip, rip_bg = mount_reserve()
RT:update(mgr, 1.0, 0.1)
_cor_positive_rip = rip:alpha()
_cor_positive_rip_bg = rip_bg:alpha()
_cor_positive_exact = reserve_is_exact(rip, rip_bg)

local fill = P._gauge._stored_health_fill
local gauge_root = P._gauge.root
local fill_key = fill:name()
local original_set_shape = fill.set_shape
local mode = "__MODE__"
if mode == "geometry" then
    fill:set_shape(fill:x() + 30, fill:y(), fill:w(), fill:h())
else
    gauge_root._children[fill_key] = nil
    fill._parent = panel_double
    panel_double._children["foreign_reserve_fill"] = fill
end
-- The owned render cannot repair this corrupt fill in the same frame.
fill.set_shape = function() end

RT:update(mgr, 1.01, 0.01)
_cor_failed_rip = rip:alpha()
_cor_failed_rip_bg = rip_bg:alpha()
_cor_failed_count = reserve_count()
_cor_failed_same_primitives = rip == chain.radial:child("radial_rip")
    and rip_bg == chain.radial:child("radial_rip_bg")

if mode == "parent" then
    panel_double._children["foreign_reserve_fill"] = nil
    fill._parent = gauge_root
    gauge_root._children[fill_key] = fill
end
fill.set_shape = original_set_shape

RT:update(mgr, 1.1, 0.1)
_cor_repair_rip = rip:alpha()
_cor_repair_rip_bg = rip_bg:alpha()
_cor_repair_exact = reserve_is_exact(rip, rip_bg)
_cor_repair_count = reserve_count()
_cor_repair_same_primitives = rip == chain.radial:child("radial_rip")
    and rip_bg == chain.radial:child("radial_rip_bg")
_cor_repair_p_visible = P._root ~= nil and P._root:visible()
_cor_repair_verify = P:verify() == true
'''

RESERVE_FAIL_CLOSED = r'''
local chain, sent, rip, rip_bg = mount_reserve()
local sentinel = sentinel_snapshot(sent)
RT:update(mgr, 1.0, 0.1)
_fc_positive_rip = rip:alpha()
_fc_positive_rip_bg = rip_bg:alpha()
_fc_positive_exact = reserve_is_exact(rip, rip_bg)

local mode = "__MODE__"
local original_character_damage = unit.character_damage
local original_entry = mgr._teammate_panels[PP]

if mode == "source" then
    local replacement = {
        _health = 100, _health_max = 100,
        _armor = 50, _armor_max = 50,
        _revives = 1,
        get_real_health = function(self) return self._health end,
        _max_health = function(self) return self._health_max end,
        get_real_armor = function(self) return self._armor end,
        _max_armor = function(self) return self._armor_max end,
        get_revives = function(self) return self._revives end,
        remaining_delayed_damage = function(self) return 0 end,
        armor_stored_health = function(self) return 0 end,
        max_armor_stored_health = function(self) return 0 end,
    }
    unit.character_damage = function(self) return replacement end
    sync_native(chain, replacement)
else
    mgr._teammate_panels[PP] = {
        _ai = __AI__,
        _peer_id = __PEER__,
        _panel = sent.panel,
        _special_equipment = {},
    }
end

RT:update(mgr, 1.1, 0.1)
_fc_off_rip = rip:alpha()
_fc_off_rip_bg = rip_bg:alpha()
_fc_off_count = reserve_count()
_fc_off_same_primitives = rip == chain.radial:child("radial_rip")
    and rip_bg == chain.radial:child("radial_rip_bg")
_fc_off_sentinel_unchanged = same_sentinel(sent, sentinel)

if mode == "source" then
    unit.character_damage = original_character_damage
    sync_native(chain)
else
    mgr._teammate_panels[PP] = original_entry
end

RT:update(mgr, 1.2, 0.1)
_fc_on_rip = rip:alpha()
_fc_on_rip_bg = rip_bg:alpha()
_fc_on_exact = reserve_is_exact(rip, rip_bg)
_fc_on_count = reserve_count()
_fc_on_same_primitives = rip == chain.radial:child("radial_rip")
    and rip_bg == chain.radial:child("radial_rip_bg")
'''

RESERVE_UNMOUNT_RETRY = r'''
local chain, sent, rip, rip_bg = mount_reserve()
RT:update(mgr, 1.0, 0.1)
_um_positive_rip = rip:alpha()
_um_positive_rip_bg = rip_bg:alpha()
_um_positive_exact = reserve_is_exact(rip, rip_bg)

local original_rip_setter = rip.set_alpha
local original_rip_bg_setter = rip_bg.set_alpha
local fail_restore = true
rip.set_alpha = function(self, value)
    if fail_restore then error("reserve restore setter failed") end
    return original_rip_setter(self, value)
end
rip_bg.set_alpha = function(self, value)
    if fail_restore then error("reserve restore setter failed") end
    return original_rip_bg_setter(self, value)
end

P:unmount()
_um_root = P._root
_um_failed_rip = rip:alpha()
_um_failed_rip_bg = rip_bg:alpha()
_um_failed_count = reserve_count()
_um_failed_marker = reserve_marker(rip)
_um_failed_same_primitives = rip == chain.radial:child("radial_rip")
    and rip_bg == chain.radial:child("radial_rip_bg")

-- Still failing: the pending restoration must retain entries and applied alpha.
RT:update(mgr, 1.1, 0.1)
_um_pending_rip = rip:alpha()
_um_pending_rip_bg = rip_bg:alpha()
_um_pending_count = reserve_count()
_um_pending_marker = reserve_marker(rip)

-- Remove source coverage so the repaired release cannot immediately reacquire.
cd.max_armor_stored_health = nil
fail_restore = false
rip.set_alpha = original_rip_setter
rip_bg.set_alpha = original_rip_bg_setter
RT:update(mgr, 1.2, 0.1)
_um_restored_rip = rip:alpha()
_um_restored_rip_bg = rip_bg:alpha()
_um_restored_count = reserve_count()
_um_restored_marker = reserve_marker(rip)
'''

RESERVE_LEAF_SWAP = r'''
local chain, sent, rip, rip_bg = mount_reserve()
local parents = chain_props(chain)
local owned_root = P._root
local gauge_root = P._gauge.root

local function reserve_pair_is_exact(a, b)
    local entries = reserve_entries()
    if #entries ~= 2 then return false end
    local seen_a, seen_b = false, false
    for _, entry in ipairs(entries) do
        if entry.property ~= "alpha" then return false end
        if not near(entry.applied_value, 0, 0.0001) then return false end
        if entry.object == a then
            if seen_a then return false end
            seen_a = true
        elseif entry.object == b then
            if seen_b then return false end
            seen_b = true
        else
            return false
        end
    end
    return seen_a and seen_b
end

RT:update(mgr, 1.0, 0.1)
_sw_positive_rip = rip:alpha()
_sw_positive_rip_bg = rip_bg:alpha()
_sw_positive_gauge = P._gauge.root == gauge_root

-- The game swaps the native radial_rip leaf under the same radial while the
-- RESERVE lease is active: the old primitive leaves the radial children.
chain.radial._children["radial_rip"] = nil
local new_rip = chain.radial:bitmap({name = "radial_rip", layer = 3})
new_rip:set_shape(0, 0, chain.pw, chain.ph)
new_rip:set_visible(true)
new_rip:set_alpha(0.47)

RT:update(mgr, 1.1, 0.1)
_sw_old_rip = rip:alpha()
_sw_old_detached = rip ~= chain.radial:child("radial_rip")
_sw_new_present = chain.radial:child("radial_rip") == new_rip

RT:update(mgr, 1.2, 0.1)
_sw_new_rip = new_rip:alpha()
_sw_new_visible = new_rip:visible()
_sw_new_exact = reserve_pair_is_exact(new_rip, rip_bg)
_sw_new_count = reserve_count()
_sw_new_gauge = P._gauge.root == gauge_root
_sw_new_owned = P._root == owned_root
_sw_parents_unchanged = same_chain_props(chain, parents)

-- Releasing the stock must restore the new leaf's own original alpha, proving
-- the stale binding to the removed primitive was dropped and not reused.
cd.max_armor_stored_health = nil
RT:update(mgr, 1.3, 0.1)
_sw_released_new = new_rip:alpha()
_sw_released_bg = rip_bg:alpha()
_sw_released_count = reserve_count()
_sw_released_gauge = P._gauge.root == gauge_root
'''


class ReserveReplacementPositiveTests(unittest.TestCase):
    def test_positive_reserve_replaces_two_leaves_and_restores_on_player_off(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(RESERVE_PRELIM + RESERVE_POSITIVE)
        g = lua.globals()

        self.assertTrue(bool(g._positive_visible),
                        "live reserve stock must keep the owned player visible")
        self.assertTrue(bool(g._positive_verify),
                        "the owned player render must be certified")
        self.assertAlmostEqual(float(g._positive_rip_alpha), 0.0, places=5,
                               msg="reserve stock must set radial_rip alpha to 0")
        self.assertAlmostEqual(float(g._positive_rip_bg_alpha), 0.0, places=5,
                               msg="reserve stock must set radial_rip_bg alpha to 0")
        self.assertTrue(bool(g._positive_rip_visible),
                        "replacement must not rewrite native radial_rip visibility")
        self.assertTrue(bool(g._positive_rip_bg_visible),
                        "replacement must not rewrite native radial_rip_bg visibility")
        self.assertTrue(bool(g._positive_reserve_exact),
                        "replacement must hold exactly the two RESERVE-owned rip alpha leases")
        self.assertEqual(int(g._positive_reserve_count), 2,
                         "no extra RESERVE-owned native_visibility leaf may be hidden")
        self.assertTrue(bool(g._positive_same_primitives),
                        "replacement must keep the exact two native reserve leaves")
        self.assertTrue(bool(g._positive_owned_identity),
                        "replacement must not replace the owned player primitives")
        self.assertTrue(bool(g._positive_parents_unchanged),
                        "replacement must not mutate any native parent property")
        self.assertTrue(bool(g._positive_sentinels_unchanged),
                        "unrelated and remote sentinels must remain unchanged")
        self.assertTrue(bool(g._positive_bg_visible),
                        "the owned reserve capacity track must be visible")
        self.assertGreater(float(g._positive_bg_w), 0.0,
                           "the owned reserve capacity track must have width")
        self.assertAlmostEqual(
            float(g._positive_fill_w) / float(g._positive_bg_w), 0.5, places=5,
            msg="stock 20 over capacity 40 must fill half the owned track")

        self.assertTrue(bool(g._zero_visible),
                        "empty stock must keep the owned player visible")
        self.assertTrue(bool(g._zero_verify),
                        "empty stock coverage must stay certified")
        self.assertAlmostEqual(float(g._zero_rip_alpha), 0.0, places=5,
                               msg="empty stock must keep radial_rip alpha at 0")
        self.assertAlmostEqual(float(g._zero_rip_bg_alpha), 0.0, places=5,
                               msg="empty stock must keep radial_rip_bg alpha at 0")
        self.assertTrue(bool(g._zero_rip_visible),
                        "empty stock must not rewrite native radial_rip visibility")
        self.assertTrue(bool(g._zero_rip_bg_visible),
                        "empty stock must not rewrite native radial_rip_bg visibility")
        self.assertTrue(bool(g._zero_reserve_exact),
                        "empty stock must keep exactly the two RESERVE-owned rip alpha leases")
        self.assertEqual(int(g._zero_reserve_count), 2,
                         "empty stock must not add a RESERVE-owned native_visibility leaf")
        self.assertTrue(bool(g._zero_bg_visible),
                        "empty stock must keep the owned capacity track visible")
        self.assertGreater(float(g._zero_bg_w), 0.0,
                           "empty stock must keep the capacity track width")
        self.assertTrue(bool(g._zero_fill_visible),
                        "empty stock must keep the owned reserve fill primitive visible")
        self.assertAlmostEqual(float(g._zero_fill_w), 0.0, places=5,
                               msg="empty stock must render an empty owned reserve fill")

        self.assertIsNone(g._off_root,
                          "player option off must unmount the owned root")
        self.assertAlmostEqual(float(g._off_rip_alpha), 0.63, places=5,
                               msg="player option off must restore the exact radial_rip alpha")
        self.assertAlmostEqual(float(g._off_rip_bg_alpha), 0.81, places=5,
                               msg="player option off must restore the exact radial_rip_bg alpha")
        self.assertTrue(bool(g._off_rip_visible),
                        "player option off must leave native radial_rip visibility unchanged")
        self.assertTrue(bool(g._off_rip_bg_visible),
                        "player option off must leave native radial_rip_bg visibility unchanged")
        self.assertTrue(bool(g._off_same_primitives),
                        "player option off must not replace the native reserve leaves")
        self.assertEqual(int(g._off_reserve_count), 0,
                         "player option off must release every RESERVE-owned NV entry")


class ReserveReplacementLossTests(unittest.TestCase):
    def test_missing_max_or_nan_stored_releases_exact_alphas_and_recovers(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(RESERVE_PRELIM + RESERVE_NEGATIVE)
        g = lua.globals()

        self.assertTrue(bool(g._negative_positive_visible),
                        "precondition: live reserve stock must keep the player visible")
        self.assertAlmostEqual(float(g._negative_positive_rip), 0.0, places=5)
        self.assertAlmostEqual(float(g._negative_positive_rip_bg), 0.0, places=5)

        self.assertAlmostEqual(float(g._missing_rip), 0.63, places=5,
                               msg="missing max stored getter must restore the exact radial_rip alpha")
        self.assertAlmostEqual(float(g._missing_rip_bg), 0.81, places=5,
                               msg="missing max stored getter must restore the exact radial_rip_bg alpha")
        self.assertFalse(bool(g._missing_visible),
                         "missing max stored getter must fall back to native blocker priority")
        self.assertTrue(bool(g._missing_same_primitives),
                        "missing max stored getter must not replace the native reserve leaves")
        self.assertTrue(bool(g._missing_native_visible),
                        "missing max stored getter must not rewrite native visibility")
        self.assertAlmostEqual(float(g._recovered_rip), 0.0, places=5,
                               msg="restored max stored getter must reacquire radial_rip")
        self.assertAlmostEqual(float(g._recovered_rip_bg), 0.0, places=5,
                               msg="restored max stored getter must reacquire radial_rip_bg")
        self.assertTrue(bool(g._recovered_visible),
                        "restored max stored getter must keep the owned player visible")
        self.assertTrue(bool(g._recovered_same_primitives),
                        "restored max stored getter must reuse the exact owned primitives")

        self.assertAlmostEqual(float(g._nan_rip), 0.63, places=5,
                               msg="NaN max stored getter must restore the exact radial_rip alpha")
        self.assertAlmostEqual(float(g._nan_rip_bg), 0.81, places=5,
                               msg="NaN max stored getter must restore the exact radial_rip_bg alpha")
        self.assertFalse(bool(g._nan_visible),
                         "NaN max stored getter must fall back to native blocker priority")
        self.assertTrue(bool(g._nan_native_visible),
                        "NaN max stored getter must not rewrite native visibility")
        self.assertAlmostEqual(float(g._nan_recovered_rip), 0.0, places=5,
                               msg="restored max stored getter after NaN must reacquire radial_rip")
        self.assertAlmostEqual(float(g._nan_recovered_rip_bg), 0.0, places=5,
                               msg="restored max stored getter after NaN must reacquire radial_rip_bg")
        self.assertTrue(bool(g._nan_recovered_visible),
                        "restored max stored getter after NaN must keep the player visible")
        self.assertTrue(bool(g._nan_recovered_same_primitives),
                        "recovery after NaN must reuse the exact owned primitives")


class ReserveReplacementThrottleTests(unittest.TestCase):
    def test_throttled_stock_change_renders_fresh_owned_fill(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(RESERVE_PRELIM + RESERVE_THROTTLE)
        g = lua.globals()

        self.assertTrue(bool(g._thr_positive_exact),
                        "precondition: the two RESERVE rip leases must be active")
        self.assertTrue(bool(g._thr_verify),
                        "the throttled fresh stock render must be certified")
        self.assertTrue(bool(g._thr_same_primitives),
                        "the throttled stock change must keep the exact native rip leaves")
        self.assertTrue(bool(g._thr_reserve_exact),
                        "the throttled stock change must keep exactly the two RESERVE leases")
        self.assertEqual(int(g._thr_reserve_count), 2,
                         "the throttled stock change must not add RESERVE-owned leaves")
        self.assertGreater(float(g._thr_bg_w), 0.0,
                           "the owned reserve capacity track must keep its width")
        self.assertAlmostEqual(
            float(g._thr_fill_w) / float(g._thr_bg_w), 1.0, places=5,
            msg="fresh stock 40 over capacity 40 must fill the whole owned track")
        self.assertAlmostEqual(float(g._thr_stored_ratio), 0.4, places=5,
                               msg="the owned receipt must use the fresh stored ratio")
        self.assertAlmostEqual(float(g._thr_max_ratio), 0.4, places=5,
                               msg="the owned receipt must keep the stored capacity ratio")
        self.assertTrue(bool(g._thr_parents_unchanged),
                        "the throttled stock change must not mutate native parents")
        self.assertTrue(bool(g._thr_sentinel_unchanged),
                        "the throttled stock change must not touch unrelated sentinels")


class ReserveReplacementOwnedFillCorruptionTests(unittest.TestCase):
    def test_corrupt_owned_fill_releases_exact_alphas_then_repairs_same_primitives(self):
        for mode in ("geometry", "parent"):
            with self.subTest(mode=mode):
                lua, ok = _lua(setup=SETUP)
                self.assertTrue(ok, "lua/hud/player.lua must exist")
                if not ok:
                    continue

                script = RESERVE_FILL_CORRUPTION.replace("__MODE__", mode)
                lua.execute(RESERVE_PRELIM + script)
                g = lua.globals()

                self.assertAlmostEqual(float(g._cor_positive_rip), 0.0, places=5)
                self.assertAlmostEqual(float(g._cor_positive_rip_bg), 0.0, places=5)
                self.assertTrue(bool(g._cor_positive_exact))
                self.assertAlmostEqual(
                    float(g._cor_failed_rip), 0.63, places=5,
                    msg=f"{mode} fill corruption must restore the exact rip alpha")
                self.assertAlmostEqual(
                    float(g._cor_failed_rip_bg), 0.81, places=5,
                    msg=f"{mode} fill corruption must restore the exact rip_bg alpha")
                self.assertEqual(int(g._cor_failed_count), 0,
                                 f"{mode} fill corruption must release every RESERVE lease")
                self.assertTrue(bool(g._cor_failed_same_primitives),
                                f"{mode} fill corruption must not replace the native leaves")
                self.assertAlmostEqual(
                    float(g._cor_repair_rip), 0.0, places=5,
                    msg=f"{mode} repair must reacquire the rip leaf")
                self.assertAlmostEqual(
                    float(g._cor_repair_rip_bg), 0.0, places=5,
                    msg=f"{mode} repair must reacquire the rip_bg leaf")
                self.assertTrue(bool(g._cor_repair_exact),
                                f"{mode} repair must reacquire exactly two RESERVE leases")
                self.assertEqual(int(g._cor_repair_count), 2,
                                 f"{mode} repair must not add RESERVE-owned leaves")
                self.assertTrue(bool(g._cor_repair_same_primitives),
                                f"{mode} repair must reuse the exact native leaves")
                self.assertTrue(bool(g._cor_repair_p_visible),
                                f"{mode} repair must keep the owned player visible")
                self.assertTrue(bool(g._cor_repair_verify),
                                f"{mode} repair must certify the owned render")


class ReserveReplacementFailClosedTests(unittest.TestCase):
    def test_source_replacement_and_foreign_entry_identity_fail_closed(self):
        cases = (
            ("source", "false", "nil"),
            ("wrong_ai", "true", "nil"),
            ("wrong_peer", "false", "2"),
        )
        for mode, ai, peer in cases:
            with self.subTest(mode=mode):
                lua, ok = _lua(setup=SETUP)
                self.assertTrue(ok, "lua/hud/player.lua must exist")
                if not ok:
                    continue

                script = (RESERVE_FAIL_CLOSED
                          .replace("__MODE__", mode)
                          .replace("__AI__", ai)
                          .replace("__PEER__", peer))
                lua.execute(RESERVE_PRELIM + script)
                g = lua.globals()

                self.assertAlmostEqual(float(g._fc_positive_rip), 0.0, places=5)
                self.assertAlmostEqual(float(g._fc_positive_rip_bg), 0.0, places=5)
                self.assertTrue(bool(g._fc_positive_exact))
                self.assertAlmostEqual(
                    float(g._fc_off_rip), 0.63, places=5,
                    msg=f"{mode} must fail closed and restore the exact rip alpha")
                self.assertAlmostEqual(
                    float(g._fc_off_rip_bg), 0.81, places=5,
                    msg=f"{mode} must fail closed and restore the exact rip_bg alpha")
                self.assertEqual(int(g._fc_off_count), 0,
                                 f"{mode} must release every RESERVE lease")
                self.assertTrue(bool(g._fc_off_same_primitives),
                                f"{mode} must not replace the native leaves")
                self.assertTrue(bool(g._fc_off_sentinel_unchanged),
                                f"{mode} must not touch unrelated sentinels")
                self.assertAlmostEqual(
                    float(g._fc_on_rip), 0.0, places=5,
                    msg=f"{mode} recovery must reacquire the rip leaf")
                self.assertAlmostEqual(
                    float(g._fc_on_rip_bg), 0.0, places=5,
                    msg=f"{mode} recovery must reacquire the rip_bg leaf")
                self.assertTrue(bool(g._fc_on_exact),
                                f"{mode} recovery must reacquire exactly two RESERVE leases")
                self.assertEqual(int(g._fc_on_count), 2,
                                 f"{mode} recovery must not add RESERVE-owned leaves")
                self.assertTrue(bool(g._fc_on_same_primitives),
                                f"{mode} recovery must reuse the exact native leaves")


class ReserveReplacementUnmountRetryTests(unittest.TestCase):
    def test_failed_restoration_on_direct_unmount_retries_exactly(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(RESERVE_PRELIM + RESERVE_UNMOUNT_RETRY)
        g = lua.globals()

        self.assertAlmostEqual(float(g._um_positive_rip), 0.0, places=5)
        self.assertAlmostEqual(float(g._um_positive_rip_bg), 0.0, places=5)
        self.assertTrue(bool(g._um_positive_exact))
        self.assertIsNone(g._um_root,
                          "direct P:unmount must leave the owned root removed")
        self.assertAlmostEqual(
            float(g._um_failed_rip), 0.0, places=5,
            msg="failed restoration must leave the applied rip alpha pending")
        self.assertAlmostEqual(
            float(g._um_failed_rip_bg), 0.0, places=5,
            msg="failed restoration must leave the applied rip_bg alpha pending")
        self.assertEqual(int(g._um_failed_count), 2,
                         "failed restoration must retain both RESERVE entries")
        self.assertTrue(bool(g._um_failed_marker),
                        "failed restoration must keep the whitelist alpha marker")
        self.assertTrue(bool(g._um_failed_same_primitives),
                        "failed restoration must not replace the native leaves")
        self.assertAlmostEqual(float(g._um_pending_rip), 0.0, places=5,
                               msg="a still-failing retry must keep the applied rip alpha")
        self.assertAlmostEqual(float(g._um_pending_rip_bg), 0.0, places=5,
                               msg="a still-failing retry must keep the applied rip_bg alpha")
        self.assertEqual(int(g._um_pending_count), 2,
                         "a still-failing retry must retain both RESERVE entries")
        self.assertTrue(bool(g._um_pending_marker),
                        "a still-failing retry must keep the whitelist alpha marker")
        self.assertAlmostEqual(float(g._um_restored_rip), 0.63, places=5,
                               msg="a repaired retry must restore the exact rip alpha")
        self.assertAlmostEqual(float(g._um_restored_rip_bg), 0.81, places=5,
                               msg="a repaired retry must restore the exact rip_bg alpha")
        self.assertEqual(int(g._um_restored_count), 0,
                         "a repaired retry must drop every RESERVE entry")
        self.assertFalse(bool(g._um_restored_marker),
                         "a repaired retry must not leave an orphan whitelist marker")


class ReserveReplacementLeafSwapTests(unittest.TestCase):
    def test_active_lease_replacement_restores_old_then_reacquires_new_rip(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(RESERVE_PRELIM + RESERVE_LEAF_SWAP)
        g = lua.globals()

        self.assertAlmostEqual(float(g._sw_positive_rip), 0.0, places=5)
        self.assertAlmostEqual(float(g._sw_positive_rip_bg), 0.0, places=5)
        self.assertTrue(bool(g._sw_positive_gauge))

        self.assertAlmostEqual(
            float(g._sw_old_rip), 0.63, places=5,
            msg="the removed lease target must get its exact original alpha back")
        self.assertTrue(bool(g._sw_old_detached),
                        "the old native rip leaf must no longer be the radial child")
        self.assertTrue(bool(g._sw_new_present),
                        "the replacement native rip leaf must sit under the same radial")

        self.assertAlmostEqual(
            float(g._sw_new_rip), 0.0, places=5,
            msg="normal updates must reacquire the replacement rip leaf")
        self.assertTrue(bool(g._sw_new_visible),
                        "reacquiring the replacement must not rewrite its visibility")
        self.assertTrue(bool(g._sw_new_exact),
                        "the replacement lease must move to the new rip leaf")
        self.assertEqual(int(g._sw_new_count), 2,
                         "the swap must not accumulate RESERVE-owned entries")
        self.assertTrue(bool(g._sw_new_gauge),
                        "the swap must keep the same owned gauge root")
        self.assertTrue(bool(g._sw_new_owned),
                        "the swap must keep the same owned player root")
        self.assertTrue(bool(g._sw_parents_unchanged),
                        "the swap must not mutate native parent properties")

        self.assertAlmostEqual(
            float(g._sw_released_new), 0.47, places=5,
            msg="release must restore the new rip leaf's own original alpha")
        self.assertAlmostEqual(
            float(g._sw_released_bg), 0.81, places=5,
            msg="release must still restore the untouched rip_bg alpha")
        self.assertEqual(int(g._sw_released_count), 0,
                         "release after the swap must drop every RESERVE entry")
        self.assertTrue(bool(g._sw_released_gauge),
                        "release after the swap must keep the same owned gauge root")


if __name__ == "__main__":
    unittest.main()
