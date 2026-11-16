"""Local COPR native overlay replacement, bounded RED characterization.

Scope: the local player native ``copr_overlay_panel`` notches only. The real
runtime, player, actors, gauge and native_visibility chunks are loaded through
test_hud_player._lua and the shared reserve/delayed fixture SETUP/PRELIM.

The native panel is created under the owned player radial rectangle, visible,
alpha .73, with five polygon leaves named "0".."4" whose alpha stays .6 while
native visibility follows ``1 - i / 5 <= .6 + .01`` (child "0" is therefore
hidden but still present, exactly like HUDTeammate:set_copr_indicator).

The desired replacement is alpha-only and per notch: the native container,
its parent and every notch visibility must stay untouched. The owned gauge
keeps its own five COPR thresholds. Unsupported ratios (100 notches, NaN) and a
corrupt owned marker setter must fail closed to the native overlay instead of
masking it.
"""
import unittest

from test_hud_player import _lua
from test_hud_player_reserve_replacement import RESERVE_PRELIM, SETUP

COPR_PRELIM = RESERVE_PRELIM + r'''
local NOTCH_COUNT = 5
local COPR_NAME = "copr_overlay_panel"
local COPR_ALPHA = 0.73
local NOTCH_ALPHA = 0.6
local HEALTH_RATIO = 0.6

local function notch_visible(i)
    return (1 - i / NOTCH_COUNT) <= HEALTH_RATIO + 0.01
end

local function expected_notch_visibility()
    local out = {}
    for i = 0, NOTCH_COUNT - 1 do out[i + 1] = notch_visible(i) end
    return out
end

local function add_notches(copr, chain)
    local out = {}
    for i = 0, NOTCH_COUNT - 1 do
        local notch = copr:polygon({
            name = tostring(i),
            layer = 0,
            triangles = {Vector3(0, 0, 0), Vector3(5, 0, 0), Vector3(2.5, 5, 0)},
        })
        notch:set_shape(0, 0, chain.pw, chain.ph)
        notch:set_alpha(NOTCH_ALPHA)
        notch:set_visible(notch_visible(i))
        out[i + 1] = notch
    end
    return out
end

local function build_copr(chain)
    local copr = chain.radial:panel({name = COPR_NAME})
    copr:set_shape(0, 0, chain.pw, chain.ph)
    copr:set_visible(true)
    copr:set_alpha(COPR_ALPHA)
    return copr, add_notches(copr, chain)
end

local function mount_copr(active, ratio)
    _KY_copr_active = active
    _KY_copr_ratio = ratio
    managers.player.has_activate_temporary_upgrade = function(self, category, upgrade)
        if category == "temporary" and upgrade == "copr_ability" then
            return _KY_copr_active == true
        end
        return false
    end
    managers.player.upgrade_value = function(self, category, upgrade, default)
        if category == "player" and upgrade == "copr_static_damage_ratio" then
            return _KY_copr_ratio
        end
        return default
    end
    local chain, sent = mount_positive()
    cd._health = 60
    cd._health_max = 100
    cd._remaining_delayed = 0
    sync_native(chain)
    -- Suppress the delayed duplicate leaves; no reserve leaves are built.
    chain.radial._children["radial_delayed_damage"] = nil
    chain.armor:set_visible(false)
    chain.health:set_visible(false)
    local copr, notches = build_copr(chain)
    return chain, sent, copr, notches
end

local function copr_lease_entries(objects)
    local wanted = {}
    for _, obj in ipairs(objects) do wanted[obj] = true end
    local out = {}
    for _, entry in ipairs(NV._entries or {}) do
        if wanted[entry.object] then out[#out + 1] = entry end
    end
    return out
end

local function lease_count(objects)
    return #copr_lease_entries(objects)
end

local function leases_exact(notches)
    local entries = copr_lease_entries(notches)
    if #entries ~= #notches then return false end
    local seen = {}
    for _, entry in ipairs(entries) do
        if entry.property ~= "alpha" then return false end
        if not near(entry.applied_value, 0, 0.0001) then return false end
        if seen[entry.object] then return false end
        seen[entry.object] = true
    end
    for _, notch in ipairs(notches) do
        if not seen[notch] then return false end
    end
    return true
end

local function alphas_are(notches, value)
    for _, notch in ipairs(notches) do
        if not near(notch:alpha(), value, 0.0001) then return false end
    end
    return true
end

local function visibility_are(notches, expected)
    for i, notch in ipairs(notches) do
        if notch:visible() ~= expected[i] then return false end
    end
    return true
end

local function marker_map(gauge, expected)
    local markers = gauge and gauge._copr_markers
    if type(markers) ~= "table" or #markers ~= #expected then return false end
    for i = 1, #expected do
        local marker = markers[i]
        if not marker or marker:visible() ~= expected[i] then return false end
    end
    return true
end

local function marker_count(gauge)
    local markers = gauge and gauge._copr_markers
    if type(markers) ~= "table" then return -1 end
    return #markers
end

local function container_intact(copr, radial)
    return copr ~= nil and copr:parent() == radial
        and near(copr:alpha(), COPR_ALPHA, 0.0001)
        and copr:visible() == true
end

local function no_foreign_leases(copr, chain)
    return lease_count({copr, chain.radial, chain.player, chain.entry}) == 0
end
'''

COPR_ACTIVE = r'''
local chain, sent, copr, notches = mount_copr(true, 0.2)
local parents = chain_props(chain)
local expected_visibility = expected_notch_visibility()
local owned_root = P._root
local gauge_root = P._gauge.root
local child0 = copr:child("0")

_copr_child0_exists = child0 ~= nil
_copr_child0_hidden = child0 ~= nil and child0:visible() == false
_copr_no_reserve = chain.radial:child("radial_rip") == nil
    and chain.radial:child("radial_rip_bg") == nil

RT:update(mgr, 1.0, 0.1)

_copr_positive_leases = leases_exact(notches)
_copr_positive_lease_count = lease_count(notches)
_copr_positive_alphas = alphas_are(notches, 0)
_copr_positive_visible = P._root ~= nil and P._root:visible() == true
_copr_positive_verify = P:verify() == true
_copr_positive_container = container_intact(copr, chain.radial)
_copr_positive_no_foreign = no_foreign_leases(copr, chain)
_copr_positive_parents = same_chain_props(chain, parents)
_copr_positive_owned = P._root == owned_root and P._gauge.root == gauge_root
_copr_positive_markers = marker_map(P._gauge, {false, false, true, true, true})
_copr_positive_marker_count = marker_count(P._gauge)
_copr_positive_notch_visibility = visibility_are(notches, expected_visibility)

_KY_copr_active = false
copr:clear()
RT:update(mgr, 1.1, 0.1)

_copr_off_restored = alphas_are(notches, NOTCH_ALPHA)
_copr_off_no_lease = lease_count(notches) == 0
_copr_off_visible = P._root ~= nil and P._root:visible() == true
_copr_off_verify = P:verify() == true
_copr_off_markers = marker_map(P._gauge, {false, false, false, false, false})
_copr_off_container = container_intact(copr, chain.radial)
_copr_off_alive = true
for _, notch in ipairs(notches) do
    if not alive(notch) then _copr_off_alive = false end
end

_KY_copr_active = true
_KY_copr_ratio = 0.2
local new_notches = add_notches(copr, chain)
RT:update(mgr, 1.2, 0.1)

_copr_recover_leases = leases_exact(new_notches)
_copr_recover_alphas = alphas_are(new_notches, 0)
_copr_recover_visible = P._root ~= nil and P._root:visible() == true
_copr_recover_verify = P:verify() == true
_copr_recover_owned = P._root == owned_root and P._gauge.root == gauge_root
_copr_recover_markers = marker_map(P._gauge, {false, false, true, true, true})
_copr_recover_container = container_intact(copr, chain.radial)
_copr_recover_no_old_lease = lease_count(notches) == 0
_copr_recover_child0 = copr:child("0") == new_notches[1]
_copr_recover_notch_visibility = visibility_are(new_notches, expected_visibility)
'''

COPR_FALLBACK = r'''
local chain, sent, copr, notches = mount_copr(true, 0.2)
local owned_root = P._root
local gauge_root = P._gauge.root

RT:update(mgr, 1.0, 0.1)
_u_valid_leases = leases_exact(notches)
_u_valid_visible = P._root ~= nil and P._root:visible() == true
_u_valid_verify = P:verify() == true

-- 1 / .01 = 100 notches, above the gauge's 64-notch bound: unsupported.
_KY_copr_ratio = 1 / 100
RT:update(mgr, 1.1, 0.1)
_u_wide_restored = alphas_are(notches, NOTCH_ALPHA)
_u_wide_no_lease = lease_count(notches) == 0
_u_wide_hidden = P._root ~= nil and P._root:visible() == false
_u_wide_markers = marker_map(P._gauge, {false, false, false, false, false})
_u_wide_container = container_intact(copr, chain.radial)
_u_wide_same = copr:child("0") == notches[1]

_KY_copr_ratio = 0 / 0
RT:update(mgr, 1.2, 0.1)
_u_nan_restored = alphas_are(notches, NOTCH_ALPHA)
_u_nan_no_lease = lease_count(notches) == 0
_u_nan_hidden = P._root ~= nil and P._root:visible() == false
_u_nan_markers = marker_map(P._gauge, {false, false, false, false, false})
_u_nan_container = container_intact(copr, chain.radial)
_u_nan_same = copr:child("0") == notches[1]

_KY_copr_ratio = 0.2
RT:update(mgr, 1.3, 0.1)
_u_recover_leases = leases_exact(notches)
_u_recover_visible = P._root ~= nil and P._root:visible() == true
_u_recover_verify = P:verify() == true
_u_recover_markers = marker_map(P._gauge, {false, false, true, true, true})
_u_recover_owned = P._root == owned_root and P._gauge.root == gauge_root

local marker = P._gauge._copr_markers and P._gauge._copr_markers[1]
_u_marker_present = marker ~= nil
if marker then
    local original_set_shape = marker.set_shape
    marker:set_shape(marker:x() + 30, marker:y(), marker:w(), marker:h())
    marker.set_shape = function() end
    RT:update(mgr, 1.4, 0.1)
    _u_corrupt_restored = alphas_are(notches, NOTCH_ALPHA)
    _u_corrupt_no_lease = lease_count(notches) == 0
    _u_corrupt_hidden = P._root ~= nil and P._root:visible() == false
    marker.set_shape = original_set_shape
    RT:update(mgr, 1.5, 0.1)
    _u_repair_leases = leases_exact(notches)
    _u_repair_visible = P._root ~= nil and P._root:visible() == true
    _u_repair_verify = P:verify() == true
    _u_repair_owned = P._root == owned_root and P._gauge.root == gauge_root
else
    _u_corrupt_restored = false
    _u_corrupt_no_lease = false
    _u_corrupt_hidden = false
    _u_repair_leases = false
    _u_repair_visible = false
    _u_repair_verify = false
    _u_repair_owned = false
end
'''

COPR_USERDATA_BOUNDARY = r'''
local function userdata_notch(original, key)
    local proxy = newproxy(true)
    local mt = getmetatable(proxy)
    mt.__index = function(_, member)
        if member == "name" then
            return function() return key end
        end
        local value = original[member]
        if type(value) == "function" then
            return function(_, ...)
                return value(original, ...)
            end
        end
        return value
    end
    mt.__newindex = function(_, member, value)
        original[member] = value
    end
    mt.__tostring = function()
        return tostring(original)
    end
    return proxy
end

local function replace_children(copr, originals, proxies)
    if type(copr._children) ~= "table" then return end
    local map = {}
    for i, original in ipairs(originals) do map[original] = proxies[i] end
    for key, child in pairs(copr._children) do
        if map[child] then copr._children[key] = map[child] end
    end
end

local function drop_child(copr, target)
    if type(copr._children) ~= "table" then return end
    for key, child in pairs(copr._children) do
        if child == target then copr._children[key] = nil end
    end
end

local function children_contain(copr, proxies)
    local children = copr:children()
    if type(children) ~= "table" then return false end
    local seen = {}
    for _, child in pairs(children) do seen[child] = true end
    for _, proxy in ipairs(proxies) do
        if not seen[proxy] then return false end
    end
    return true
end

local chain, sent, copr, notches = mount_copr(true, 0.2)
local originals = notches
local owned_root = P._root
local gauge_root = P._gauge.root
local expected_visibility = expected_notch_visibility()

originals[1]._alive = true
RT:update(mgr, 1.0, 0.1)
_tbl_ready_leases = leases_exact(originals)
_tbl_ready_visible = P._root ~= nil and P._root:visible() == true
_tbl_ready_markers = marker_map(P._gauge, {false, false, true, true, true})

local proxies = {}
for i, original in ipairs(originals) do
    proxies[i] = userdata_notch(original, original:name())
end
replace_children(copr, originals, proxies)

_ud_child_same = copr:child("0") == proxies[1]
_ud_child_userdata = type(copr:child("0")) == "userdata"
_ud_children_same = children_contain(copr, proxies)
_ud_alive_index = proxies[1]._alive == true
_ud_name_index = proxies[1]:name() == "0"

RT:update(mgr, 1.1, 0.1)
_ud_valid_leases = leases_exact(proxies)
_ud_valid_lease_count = lease_count(proxies)
_ud_valid_no_original_lease = lease_count(originals) == 0
_ud_valid_alphas = alphas_are(originals, 0)
_ud_valid_visible = P._root ~= nil and P._root:visible() == true
_ud_valid_verify = P:verify() == true
_ud_valid_owned = P._root == owned_root and P._gauge.root == gauge_root
_ud_valid_markers = marker_map(P._gauge, {false, false, true, true, true})
_ud_valid_marker_count = marker_count(P._gauge)
_ud_valid_container = container_intact(copr, chain.radial)
_ud_valid_no_foreign = no_foreign_leases(copr, chain)
_ud_valid_visibility = visibility_are(originals, expected_visibility)

local extra = copr:polygon({
    name = "99",
    layer = 0,
    triangles = {Vector3(0, 0, 0), Vector3(5, 0, 0), Vector3(2.5, 5, 0)},
})
extra:set_alpha(NOTCH_ALPHA)
RT:update(mgr, 1.2, 0.1)
_ud_extra_no_proxy_lease = lease_count(proxies) == 0
_ud_extra_no_original_lease = lease_count(originals) == 0
_ud_extra_no_extra_lease = lease_count({extra}) == 0
_ud_extra_restored = alphas_are(originals, NOTCH_ALPHA)
_ud_extra_hidden = P._root ~= nil and P._root:visible() == false
_ud_extra_markers = marker_map(P._gauge, {false, false, true, true, true})
_ud_extra_marker_count = marker_count(P._gauge)
_ud_extra_container = container_intact(copr, chain.radial)
_ud_extra_no_foreign = no_foreign_leases(copr, chain)
_ud_extra_visibility = visibility_are(originals, expected_visibility)

drop_child(copr, extra)
RT:update(mgr, 1.3, 0.1)
_ud_recover_leases = leases_exact(proxies)
_ud_recover_lease_count = lease_count(proxies)
_ud_recover_no_original_lease = lease_count(originals) == 0
_ud_recover_alphas = alphas_are(originals, 0)
_ud_recover_visible = P._root ~= nil and P._root:visible() == true
_ud_recover_verify = P:verify() == true
_ud_recover_owned = P._root == owned_root and P._gauge.root == gauge_root
_ud_recover_markers = marker_map(P._gauge, {false, false, true, true, true})
_ud_recover_marker_count = marker_count(P._gauge)
_ud_recover_container = container_intact(copr, chain.radial)
_ud_recover_child_same = copr:child("0") == proxies[1]
_ud_recover_visibility = visibility_are(originals, expected_visibility)

local original_children = rawget(copr, "children")
rawset(copr, "children", function()
    error("copr children unavailable")
end)
_ud_throw_survived = pcall(function() RT:update(mgr, 1.4, 0.1) end)
_ud_throw_no_proxy_lease = lease_count(proxies) == 0
_ud_throw_no_original_lease = lease_count(originals) == 0
_ud_throw_restored = alphas_are(originals, NOTCH_ALPHA)
_ud_throw_hidden = P._root ~= nil and P._root:visible() == false
_ud_throw_markers = marker_map(P._gauge, {false, false, true, true, true})
_ud_throw_marker_count = marker_count(P._gauge)
_ud_throw_container = container_intact(copr, chain.radial)
_ud_throw_no_foreign = no_foreign_leases(copr, chain)
_ud_throw_visibility = visibility_are(originals, expected_visibility)
rawset(copr, "children", original_children)

RT:update(mgr, 1.5, 0.1)
_ud_restore_leases = leases_exact(proxies)
_ud_restore_lease_count = lease_count(proxies)
_ud_restore_no_original_lease = lease_count(originals) == 0
_ud_restore_alphas = alphas_are(originals, 0)
_ud_restore_visible = P._root ~= nil and P._root:visible() == true
_ud_restore_verify = P:verify() == true
_ud_restore_owned = P._root == owned_root and P._gauge.root == gauge_root
_ud_restore_markers = marker_map(P._gauge, {false, false, true, true, true})
_ud_restore_marker_count = marker_count(P._gauge)
_ud_restore_container = container_intact(copr, chain.radial)
_ud_restore_child_same = copr:child("0") == proxies[1]
_ud_restore_visibility = visibility_are(originals, expected_visibility)
'''


class CoprReplacementActiveTests(unittest.TestCase):
    def test_active_copr_leases_each_notch_then_restores_and_reacquires(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(COPR_PRELIM + COPR_ACTIVE)
        g = lua.globals()

        self.assertTrue(bool(g._copr_child0_exists),
                        "hidden native child 0 must still exist")
        self.assertTrue(bool(g._copr_child0_hidden),
                        "native child 0 must stay hidden before replacement")
        self.assertTrue(bool(g._copr_no_reserve),
                        "fixture must not build reserve native leaves")

        self.assertTrue(bool(g._copr_positive_leases),
                        "runtime must lease each individual native notch alpha")
        self.assertEqual(int(g._copr_positive_lease_count), 5,
                         "exactly the five native notches must be leased")
        self.assertTrue(bool(g._copr_positive_alphas),
                        "every native notch alpha must be replaced with 0")
        self.assertTrue(bool(g._copr_positive_visible),
                        "replaced native COPR must keep the owned player visible")
        self.assertTrue(bool(g._copr_positive_verify),
                        "the owned player render must be certified")
        self.assertTrue(bool(g._copr_positive_container),
                        "the native COPR container must not be mutated")
        self.assertTrue(bool(g._copr_positive_no_foreign),
                        "no container or parent may receive an alpha lease")
        self.assertTrue(bool(g._copr_positive_parents),
                        "replacement must not mutate native parent properties")
        self.assertTrue(bool(g._copr_positive_owned),
                        "replacement must not replace the owned player primitives")
        self.assertTrue(bool(g._copr_positive_markers),
                        "the owned gauge must expose the five COPR thresholds")
        self.assertEqual(int(g._copr_positive_marker_count), 5,
                         "the owned gauge must keep exactly five COPR markers")
        self.assertTrue(bool(g._copr_positive_notch_visibility),
                        "replacement must not rewrite native notch visibility")

        self.assertTrue(bool(g._copr_off_restored),
                        "deactivation must restore every old notch alpha to .6")
        self.assertTrue(bool(g._copr_off_no_lease),
                        "deactivation must release every old notch lease")
        self.assertTrue(bool(g._copr_off_visible),
                        "deactivation must keep the owned player visible")
        self.assertTrue(bool(g._copr_off_verify),
                        "deactivation must keep the owned render certified")
        self.assertTrue(bool(g._copr_off_markers),
                        "inactive COPR must hide every owned marker")
        self.assertTrue(bool(g._copr_off_container),
                        "deactivation must not mutate the native container")
        self.assertTrue(bool(g._copr_off_alive),
                        "old notches must remain alive for exact restoration")

        self.assertTrue(bool(g._copr_recover_leases),
                        "reactivation must lease the recreated notches")
        self.assertTrue(bool(g._copr_recover_alphas),
                        "reactivation must replace every recreated notch alpha")
        self.assertTrue(bool(g._copr_recover_visible),
                        "reactivation must keep the owned player visible")
        self.assertTrue(bool(g._copr_recover_verify),
                        "reactivation must certify the owned render")
        self.assertTrue(bool(g._copr_recover_owned),
                        "recovery must reuse the same owned player primitives")
        self.assertTrue(bool(g._copr_recover_markers),
                        "recovery must restore the five COPR thresholds")
        self.assertTrue(bool(g._copr_recover_container),
                        "recovery must reuse the same native container")
        self.assertTrue(bool(g._copr_recover_no_old_lease),
                        "recovery must not keep stale old-notch leases")
        self.assertTrue(bool(g._copr_recover_child0),
                        "recovery must use the recreated numeric child 0")
        self.assertTrue(bool(g._copr_recover_notch_visibility),
                        "recovery must not rewrite recreated notch visibility")


class CoprReplacementFallbackTests(unittest.TestCase):
    def test_unsupported_ratio_nan_and_corrupt_marker_fail_closed_then_recover(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(COPR_PRELIM + COPR_FALLBACK)
        g = lua.globals()

        self.assertTrue(bool(g._u_valid_leases),
                        "precondition: valid .2 must lease the native notches")
        self.assertTrue(bool(g._u_valid_visible),
                        "precondition: valid .2 must keep the player visible")
        self.assertTrue(bool(g._u_valid_verify),
                        "precondition: valid .2 must certify the owned render")

        self.assertTrue(bool(g._u_wide_restored),
                        "unsupported 1/100 must restore every notch alpha")
        self.assertTrue(bool(g._u_wide_no_lease),
                        "unsupported 1/100 must not mask the native notches")
        self.assertTrue(bool(g._u_wide_hidden),
                        "unsupported 1/100 must fall back to native priority")
        self.assertTrue(bool(g._u_wide_markers),
                        "unsupported 1/100 must hide every owned marker")
        self.assertTrue(bool(g._u_wide_container),
                        "unsupported 1/100 must not mutate the native container")
        self.assertTrue(bool(g._u_wide_same),
                        "unsupported 1/100 must keep the native child 0")

        self.assertTrue(bool(g._u_nan_restored),
                        "NaN ratio must restore every notch alpha")
        self.assertTrue(bool(g._u_nan_no_lease),
                        "NaN ratio must not mask the native notches")
        self.assertTrue(bool(g._u_nan_hidden),
                        "NaN ratio must fall back to native priority")
        self.assertTrue(bool(g._u_nan_markers),
                        "NaN ratio must hide every owned marker")
        self.assertTrue(bool(g._u_nan_container),
                        "NaN ratio must not mutate the native container")
        self.assertTrue(bool(g._u_nan_same),
                        "NaN ratio must keep the native child 0")

        self.assertTrue(bool(g._u_recover_leases),
                        "restored .2 must reacquire the native notches")
        self.assertTrue(bool(g._u_recover_visible),
                        "restored .2 must keep the player visible")
        self.assertTrue(bool(g._u_recover_verify),
                        "restored .2 must certify the owned render")
        self.assertTrue(bool(g._u_recover_markers),
                        "restored .2 must restore the five COPR thresholds")
        self.assertTrue(bool(g._u_recover_owned),
                        "restored .2 must reuse the same owned primitives")

        self.assertTrue(bool(g._u_marker_present),
                        "the owned gauge must expose a corruptable COPR marker")
        self.assertTrue(bool(g._u_corrupt_restored),
                        "corrupt marker geometry must restore every notch alpha")
        self.assertTrue(bool(g._u_corrupt_no_lease),
                        "corrupt marker geometry must not mask native notches")
        self.assertTrue(bool(g._u_corrupt_hidden),
                        "corrupt marker geometry must fail closed to native priority")
        self.assertTrue(bool(g._u_repair_leases),
                        "repaired marker geometry must reacquire the notches")
        self.assertTrue(bool(g._u_repair_visible),
                        "repaired marker geometry must keep the player visible")
        self.assertTrue(bool(g._u_repair_verify),
                        "repaired marker geometry must certify the owned render")
        self.assertTrue(bool(g._u_repair_owned),
                        "repaired marker geometry must reuse the same primitives")


class CoprReplacementUserdataBoundaryTests(unittest.TestCase):
    def test_userdata_notches_support_coverage_and_unknown_children_fail_closed_then_recover(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(COPR_PRELIM + COPR_USERDATA_BOUNDARY)
        g = lua.globals()

        self.assertTrue(bool(g._tbl_ready_leases),
                        "precondition: table notches must lease")
        self.assertTrue(bool(g._tbl_ready_visible),
                        "precondition: table notches must keep the player visible")
        self.assertTrue(bool(g._tbl_ready_markers),
                        "precondition: table notches must expose the five COPR thresholds")

        self.assertTrue(bool(g._ud_child_same),
                        "child(name) must return the userdata proxy")
        self.assertTrue(bool(g._ud_child_userdata),
                        "native-shaped notches must stay userdata")
        self.assertTrue(bool(g._ud_children_same),
                        "children() must expose the same userdata proxies")
        self.assertTrue(bool(g._ud_alive_index),
                        "_alive must be forwarded through __index")
        self.assertTrue(bool(g._ud_name_index),
                        "name() must resolve to the real native key")

        self.assertTrue(bool(g._ud_valid_leases),
                        "valid userdata notches must lease each proxy alpha")
        self.assertEqual(int(g._ud_valid_lease_count), 5,
                         "exactly the five userdata proxies must be leased")
        self.assertTrue(bool(g._ud_valid_no_original_lease),
                        "valid userdata coverage must not lease the original tables")
        self.assertTrue(bool(g._ud_valid_alphas),
                        "valid userdata coverage must replace the native notch alphas")
        self.assertTrue(bool(g._ud_valid_visible),
                        "valid userdata coverage must keep the owned player visible")
        self.assertTrue(bool(g._ud_valid_verify),
                        "valid userdata coverage must certify the owned render")
        self.assertTrue(bool(g._ud_valid_owned),
                        "valid userdata coverage must reuse the owned primitives")
        self.assertTrue(bool(g._ud_valid_markers),
                        "valid userdata coverage must expose the five COPR thresholds")
        self.assertEqual(int(g._ud_valid_marker_count), 5,
                         "valid userdata coverage must keep exactly five COPR markers")
        self.assertTrue(bool(g._ud_valid_container),
                        "valid userdata coverage must not mutate the native container")
        self.assertTrue(bool(g._ud_valid_no_foreign),
                        "valid userdata coverage must not lease container or parents")
        self.assertTrue(bool(g._ud_valid_visibility),
                        "valid userdata coverage must not rewrite native visibility")

        self.assertTrue(bool(g._ud_extra_no_proxy_lease),
                        "unknown sibling must release every userdata proxy lease")
        self.assertTrue(bool(g._ud_extra_no_original_lease),
                        "unknown sibling must not lease the original tables")
        self.assertTrue(bool(g._ud_extra_no_extra_lease),
                        "unknown sibling must not be leased")
        self.assertTrue(bool(g._ud_extra_restored),
                        "unknown sibling must restore the exact native alphas")
        self.assertTrue(bool(g._ud_extra_hidden),
                        "unknown sibling must fall back to native priority")
        self.assertTrue(bool(g._ud_extra_markers),
                        "unknown sibling must keep the owned five COPR thresholds")
        self.assertEqual(int(g._ud_extra_marker_count), 5,
                         "unknown sibling must not remove an owned marker")
        self.assertTrue(bool(g._ud_extra_container),
                        "unknown sibling must not mutate the native container")
        self.assertTrue(bool(g._ud_extra_no_foreign),
                        "unknown sibling must not lease container or parents")
        self.assertTrue(bool(g._ud_extra_visibility),
                        "unknown sibling must not rewrite native visibility")

        self.assertTrue(bool(g._ud_recover_leases),
                        "removing the sibling must reacquire the same userdata proxies")
        self.assertEqual(int(g._ud_recover_lease_count), 5,
                         "removing the sibling must lease exactly five proxies")
        self.assertTrue(bool(g._ud_recover_no_original_lease),
                        "removing the sibling must not lease the original tables")
        self.assertTrue(bool(g._ud_recover_alphas),
                        "removing the sibling must replace every native notch alpha")
        self.assertTrue(bool(g._ud_recover_visible),
                        "removing the sibling must keep the owned player visible")
        self.assertTrue(bool(g._ud_recover_verify),
                        "removing the sibling must certify the owned render")
        self.assertTrue(bool(g._ud_recover_owned),
                        "removing the sibling must reuse the owned primitives")
        self.assertTrue(bool(g._ud_recover_markers),
                        "removing the sibling must restore the five COPR thresholds")
        self.assertEqual(int(g._ud_recover_marker_count), 5,
                         "removing the sibling must keep exactly five COPR markers")
        self.assertTrue(bool(g._ud_recover_container),
                        "removing the sibling must reuse the same native container")
        self.assertTrue(bool(g._ud_recover_child_same),
                        "removing the sibling must reuse the same proxy child 0")
        self.assertTrue(bool(g._ud_recover_visibility),
                        "removing the sibling must not rewrite native visibility")

        self.assertTrue(bool(g._ud_throw_survived),
                        "a throwing children getter must fail closed, not abort")
        self.assertTrue(bool(g._ud_throw_no_proxy_lease),
                        "a throwing children getter must release the proxy leases")
        self.assertTrue(bool(g._ud_throw_no_original_lease),
                        "a throwing children getter must not lease the original tables")
        self.assertTrue(bool(g._ud_throw_restored),
                        "a throwing children getter must restore the exact native alphas")
        self.assertTrue(bool(g._ud_throw_hidden),
                        "a throwing children getter must fall back to native priority")
        self.assertTrue(bool(g._ud_throw_markers),
                        "a throwing children getter must keep the owned COPR thresholds")
        self.assertEqual(int(g._ud_throw_marker_count), 5,
                         "a throwing children getter must not remove an owned marker")
        self.assertTrue(bool(g._ud_throw_container),
                        "a throwing children getter must not mutate the container")
        self.assertTrue(bool(g._ud_throw_no_foreign),
                        "a throwing children getter must not lease container or parents")
        self.assertTrue(bool(g._ud_throw_visibility),
                        "a throwing children getter must not rewrite native visibility")

        self.assertTrue(bool(g._ud_restore_leases),
                        "restoring children must reacquire the same userdata proxies")
        self.assertEqual(int(g._ud_restore_lease_count), 5,
                         "restoring children must lease exactly five proxies")
        self.assertTrue(bool(g._ud_restore_no_original_lease),
                        "restoring children must not lease the original tables")
        self.assertTrue(bool(g._ud_restore_alphas),
                        "restoring children must replace every native notch alpha")
        self.assertTrue(bool(g._ud_restore_visible),
                        "restoring children must keep the owned player visible")
        self.assertTrue(bool(g._ud_restore_verify),
                        "restoring children must certify the owned render")
        self.assertTrue(bool(g._ud_restore_owned),
                        "restoring children must reuse the owned primitives")
        self.assertTrue(bool(g._ud_restore_markers),
                        "restoring children must restore the five COPR thresholds")
        self.assertEqual(int(g._ud_restore_marker_count), 5,
                         "restoring children must keep exactly five COPR markers")
        self.assertTrue(bool(g._ud_restore_container),
                        "restoring children must reuse the same native container")
        self.assertTrue(bool(g._ud_restore_child_same),
                        "restoring children must reuse the same proxy child 0")
        self.assertTrue(bool(g._ud_restore_visibility),
                        "restoring children must not rewrite native visibility")


if __name__ == "__main__":
    unittest.main()
