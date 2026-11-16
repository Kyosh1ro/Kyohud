"""Local native delayed-damage replacement, bounded RED characterization.

Scope: the local player native radial delayed-damage duplicate. The real runtime,
player, actors, gauge and native_visibility chunks are loaded through
test_hud_player._lua. A live local damage source is installed before the chunks
(health 60/100, armor 25/50, remaining delayed 60). The native teammate chain is
built under the shared panel_double at the owned player rectangle:

  mgr._teammate_panels[HUDManager.PLAYER_PANEL]._panel
    -> player -> radial_health_panel -> radial_delayed_damage
       -> radial_delayed_damage_armor  (original alpha .65)
       -> radial_delayed_damage_health (original alpha .85)

Native update_delayed_damage changes visible and color, never alpha. KyoHUD must
therefore hide the two duplicate leaves through alpha 0, preserving their native
visibility and every parent property, and restore the differing original alphas
exactly when the live debt disappears or the replacement cannot be certified.
None of the tests write production snapshots or monkeypatch certification
helpers; they only drive ordinary RT:update calls and mutate the live source.

RED: the runtime currently lets the active delayed leaves block the owned local
player instead of replacing them.
"""
import unittest

from test_hud_player import _lua
from test_hud_player_health_effects import (
    LOCAL_SOURCE_SETUP_EXPORTED,
    NATIVE_HEALTH_EFFECTS_FIXTURE,
)

SETUP = (
    NATIVE_HEALTH_EFFECTS_FIXTURE
    + LOCAL_SOURCE_SETUP_EXPORTED
    + r'''
mgr._safe_script = {panel = _G.panel_double}
'''
)

PRELIM = r'''
local RT = kyohud.hud.runtime
local P = kyohud.hud.player
local ACT = kyohud.hud.actors
local mgr = managers.hud
local PP = HUDManager.PLAYER_PANEL
local cd = _KY_test_damage
local unit = _KY_test_unit

local function near(a, b, eps)
    if type(a) ~= "number" or type(b) ~= "number" then return a == b end
    return math.abs(a - b) <= (eps or 0.01)
end

local function props(p)
    return {x = p:x(), y = p:y(), w = p:w(), h = p:h(),
        v = p:visible(), a = p:alpha()}
end

local function same_props(a, b)
    if not a or not b then return false end
    return near(a.x, b.x) and near(a.y, b.y) and near(a.w, b.w)
        and near(a.h, b.h) and a.v == b.v and near(a.a, b.a, 0.001)
end

local function chain_props(chain)
    return {
        entry = props(chain.entry),
        player = props(chain.player),
        radial = props(chain.radial),
        delayed = props(chain.delayed),
    }
end

local function same_chain_props(chain, saved)
    return same_props(props(chain.entry), saved.entry)
        and same_props(props(chain.player), saved.player)
        and same_props(props(chain.radial), saved.radial)
        and same_props(props(chain.delayed), saved.delayed)
end

local function sync_native(chain, source)
    source = source or cd
    local entry_state = mgr._teammate_panels[PP]
    local health_max = source._health_max or 0
    local armor_max = source._armor_max or 0
    local health_ratio = health_max > 0 and (source._health / health_max) or 0
    local armor_ratio = armor_max > 0 and (source._armor / armor_max) or 0
    entry_state._health_data = {current = source._health, total = health_max}
    entry_state._armor_data = {current = source._armor, total = armor_max}
    chain.radial_health:set_color(Color(1, health_ratio, 0, 0))
    chain.radial_shield:set_color(Color(1, armor_ratio, 0, 0))
end

local function build_local_chain()
    local px, py, pw, ph = P._root:x(), P._root:y(), P._root:w(), P._root:h()
    local entry = panel_double:panel({name = "local_delayed_entry"})
    entry:set_shape(px, py, pw, ph)
    entry:set_visible(true)
    entry:set_alpha(1)
    local player = entry:panel({name = "player"})
    player:set_shape(0, 0, pw, ph)
    player:set_visible(true)
    player:set_alpha(1)
    local radial = player:panel({name = "radial_health_panel"})
    radial:set_shape(0, 0, pw, ph)
    radial:set_visible(true)
    radial:set_alpha(1)
    local radial_health = radial:bitmap({name = "radial_health"})
    radial_health:set_shape(0, 0, pw, ph)
    radial_health:set_visible(true)
    radial_health:set_alpha(0.7)
    local radial_shield = radial:bitmap({name = "radial_shield"})
    radial_shield:set_shape(0, 0, pw, ph)
    radial_shield:set_visible(true)
    radial_shield:set_alpha(0.7)
    local delayed = radial:panel({name = "radial_delayed_damage"})
    delayed:set_shape(0, 0, pw, ph)
    delayed:set_visible(true)
    delayed:set_alpha(1)
    local armor = delayed:bitmap({name = "radial_delayed_damage_armor"})
    armor:set_shape(0, 0, pw, ph)
    armor:set_visible(true)
    armor:set_alpha(0.65)
    local health = delayed:bitmap({name = "radial_delayed_damage_health"})
    health:set_shape(0, 0, pw, ph)
    health:set_visible(true)
    health:set_alpha(0.85)
    local entry_state = mgr._teammate_panels[PP] or {}
    entry_state._peer_id = nil
    entry_state._ai = false
    entry_state._panel = entry
    entry_state._special_equipment = entry_state._special_equipment or {}
    mgr._teammate_panels[PP] = entry_state
    local chain = {entry = entry, player = player, radial = radial,
        radial_health = radial_health, radial_shield = radial_shield,
        delayed = delayed, armor = armor, health = health, pw = pw, ph = ph}
    sync_native(chain)
    return chain
end

local function build_sentinels()
    local panel = panel_double:panel({name = "unrelated_sentinel"})
    panel:set_shape(10, 10, 40, 40)
    panel:set_visible(true)
    panel:set_alpha(0.42)
    local leaf = panel:bitmap({name = "unrelated_leaf"})
    leaf:set_shape(0, 0, 40, 40)
    leaf:set_visible(true)
    leaf:set_alpha(0.37)
    local remote = panel_double:panel({name = "remote_delayed_entry"})
    remote:set_shape(0, 0, 20, 20)
    remote:set_visible(true)
    remote:set_alpha(1)
    local rplayer = remote:panel({name = "player"})
    rplayer:set_shape(0, 0, 20, 20)
    rplayer:set_visible(true)
    rplayer:set_alpha(1)
    local rradial = rplayer:panel({name = "radial_health_panel"})
    rradial:set_shape(0, 0, 20, 20)
    rradial:set_visible(true)
    rradial:set_alpha(1)
    local rdelayed = rradial:panel({name = "radial_delayed_damage"})
    rdelayed:set_shape(0, 0, 20, 20)
    rdelayed:set_visible(true)
    rdelayed:set_alpha(1)
    local rarmor = rdelayed:bitmap({name = "radial_delayed_damage_armor"})
    rarmor:set_shape(0, 0, 20, 20)
    rarmor:set_visible(true)
    rarmor:set_alpha(0.35)
    local rhealth = rdelayed:bitmap({name = "radial_delayed_damage_health"})
    rhealth:set_shape(0, 0, 20, 20)
    rhealth:set_visible(true)
    rhealth:set_alpha(0.45)
    mgr._teammate_panels[1] = {
        _peer_id = 2, _ai = false, _panel = remote,
        _special_equipment = {},
    }
    return {panel = panel, leaf = leaf, remote = remote,
        rarmor = rarmor, rhealth = rhealth}
end

local function mount_positive()
    kyohud.settings.enable_hud_foundation = true
    kyohud.settings.enable_player = true
    kyohud.settings.player_value_mode = 1
    cd._health = 60
    cd._health_max = 100
    cd._armor = 25
    cd._armor_max = 50
    cd._remaining_delayed = 60
    RT:refresh_settings(mgr)
    local chain = build_local_chain()
    local sent = build_sentinels()
    return chain, sent
end

local function two_zero_leaves(chain)
    local zero_count = 0
    for _, leaf in pairs(chain.delayed._children) do
        if near(leaf:alpha(), 0, 0.001) then zero_count = zero_count + 1 end
    end
    return zero_count == 2
end
'''

POSITIVE = r'''
local chain, sent = mount_positive()
local parents = chain_props(chain)
local sentinel = {
    leaf = sent.leaf:alpha(),
    panel = props(sent.panel),
    rarmor = sent.rarmor:alpha(),
    rhealth = sent.rhealth:alpha(),
    remote = props(sent.remote),
}

RT:update(mgr, 1.0, 0.1)

_positive_p_visible = P._root:visible()
_positive_armor_alpha = chain.armor:alpha()
_positive_health_alpha = chain.health:alpha()
_positive_armor_visible = chain.armor:visible()
_positive_health_visible = chain.health:visible()
_positive_exact_two_zero = two_zero_leaves(chain)
_positive_parents_unchanged = same_chain_props(chain, parents)
_positive_sentinels_unchanged = near(sent.leaf:alpha(), sentinel.leaf)
    and same_props(props(sent.panel), sentinel.panel)
    and near(sent.rarmor:alpha(), sentinel.rarmor)
    and near(sent.rhealth:alpha(), sentinel.rhealth)
    and same_props(props(sent.remote), sentinel.remote)

-- Native update_delayed_damage toggles visibility and color channels without
-- calling set_alpha. Replacement must stay alpha based and must not rewrite the
-- native visibility values.
chain.armor:set_visible(false)
chain.health:set_visible(true)
RT:update(mgr, 1.1, 0.1)
_native_armor_alpha = chain.armor:alpha()
_native_health_alpha = chain.health:alpha()
_native_armor_visible = chain.armor:visible()
_native_health_visible = chain.health:visible()

-- Repeated ordinary frames reassert the same two alpha targets.
RT:update(mgr, 1.2, 0.1)
_reassert_armor_alpha = chain.armor:alpha()
_reassert_health_alpha = chain.health:alpha()
_reassert_p_visible = P._root:visible()

-- The live debt disappears and the native leaves are hidden natively. The
-- differing third-party alphas must be restored exactly, not normalized.
cd._remaining_delayed = 0
chain.armor:set_visible(false)
chain.health:set_visible(false)
RT:update(mgr, 1.3, 0.1)
_release_armor_alpha = chain.armor:alpha()
_release_health_alpha = chain.health:alpha()
_release_p_visible = P._root:visible()
_release_same_primitives = chain.armor == chain.delayed:child("radial_delayed_damage_armor")
    and chain.health == chain.delayed:child("radial_delayed_damage_health")

-- Same primitives must re-qualify on the next positive live value.
cd._remaining_delayed = 60
chain.armor:set_visible(true)
chain.health:set_visible(true)
RT:update(mgr, 1.4, 0.1)
_recovery_armor_alpha = chain.armor:alpha()
_recovery_health_alpha = chain.health:alpha()
_recovery_p_visible = P._root:visible()
_recovery_parents_unchanged = same_chain_props(chain, parents)
'''

LOSS_NAN = r'''
local chain, sent = mount_positive()
RT:update(mgr, 1.0, 0.1)
_positive_known = (function()
    local snap = ACT:get_actor(PP)
    local dd = snap and snap.health_effects and snap.health_effects.delayed_damage
    return dd ~= nil and dd.known == true
end)()
_positive_armor_alpha = chain.armor:alpha()
_positive_health_alpha = chain.health:alpha()
_positive_p_visible = P._root:visible()

cd.remaining_delayed_damage = nil
RT:update(mgr, 1.1, 0.1)
_missing_known = (function()
    local snap = ACT:get_actor(PP)
    local dd = snap and snap.health_effects and snap.health_effects.delayed_damage
    return dd and dd.known
end)()
_missing_armor_alpha = chain.armor:alpha()
_missing_health_alpha = chain.health:alpha()
_missing_p_visible = P._root:visible()
_missing_same_primitives = chain.armor == chain.delayed:child("radial_delayed_damage_armor")
    and chain.health == chain.delayed:child("radial_delayed_damage_health")

cd.remaining_delayed_damage = function(self) return 0 / 0 end
RT:update(mgr, 1.2, 0.1)
_nan_known = (function()
    local snap = ACT:get_actor(PP)
    local dd = snap and snap.health_effects and snap.health_effects.delayed_damage
    return dd and dd.known
end)()
_nan_armor_alpha = chain.armor:alpha()
_nan_health_alpha = chain.health:alpha()
_nan_p_visible = P._root:visible()

-- Same live damage object, same getter name, same two primitives: recovery.
cd.remaining_delayed_damage = function(self) return 60 end
RT:update(mgr, 1.3, 0.1)
_recovered_known = (function()
    local snap = ACT:get_actor(PP)
    local dd = snap and snap.health_effects and snap.health_effects.delayed_damage
    return dd ~= nil and dd.known == true
end)()
_recovered_armor_alpha = chain.armor:alpha()
_recovered_health_alpha = chain.health:alpha()
_recovered_p_visible = P._root:visible()
_recovered_same_primitives = chain.armor == chain.delayed:child("radial_delayed_damage_armor")
    and chain.health == chain.delayed:child("radial_delayed_damage_health")
'''

SETTER_FAILURE = r'''
local chain, sent = mount_positive()
RT:update(mgr, 1.0, 0.1)
_positive_armor_alpha = chain.armor:alpha()
_positive_health_alpha = chain.health:alpha()

cd._remaining_delayed = 0
chain.armor:set_visible(false)
chain.health:set_visible(false)
RT:update(mgr, 1.1, 0.1)
_released_armor_alpha = chain.armor:alpha()
_released_health_alpha = chain.health:alpha()

-- The second lease write fails after the first leaf has changed: the partial
-- mutation must roll back to the exact differing originals and certification
-- must fail closed. The wrapper fails exactly one write so the rollback write
-- itself still reaches the real setter, independently of request order.
local original_armor_setter = chain.armor.set_alpha
local original_health_setter = chain.health.set_alpha
local lease_writes = 0
local function flaky_setter(original)
    return function(self, value)
        lease_writes = lease_writes + 1
        if lease_writes == 2 then
            error("delayed lease setter failed")
        end
        return original(self, value)
    end
end
chain.armor.set_alpha = flaky_setter(original_armor_setter)
chain.health.set_alpha = flaky_setter(original_health_setter)
cd._remaining_delayed = 60
chain.armor:set_visible(true)
chain.health:set_visible(true)
RT:update(mgr, 1.2, 0.1)
_failed_armor_alpha = chain.armor:alpha()
_failed_health_alpha = chain.health:alpha()
_failed_zero_leaves = two_zero_leaves(chain)
_failed_p_visible = P._root:visible()
_failed_same_primitives = chain.armor == chain.delayed:child("radial_delayed_damage_armor")
    and chain.health == chain.delayed:child("radial_delayed_damage_health")

chain.armor.set_alpha = original_armor_setter
chain.health.set_alpha = original_health_setter
RT:update(mgr, 1.3, 0.1)
_recovered_armor_alpha = chain.armor:alpha()
_recovered_health_alpha = chain.health:alpha()
_recovered_exact_two_zero = two_zero_leaves(chain)
_recovered_p_visible = P._root:visible()
_recovered_same_primitives = chain.armor == chain.delayed:child("radial_delayed_damage_armor")
    and chain.health == chain.delayed:child("radial_delayed_damage_health")
'''

OTHER_BLOCKERS = r'''
local chain, sent = mount_positive()
local pw, ph = chain.pw, chain.ph
local carry = chain.player:panel({name = "carry_panel"})
carry:set_shape(0, 0, pw, ph)
carry:set_visible(false)
carry:set_alpha(0.5)
local custom = chain.radial:bitmap({name = "radial_custom"})
custom:set_shape(0, 0, pw, ph)
custom:set_visible(false)
custom:set_alpha(0.5)
local interact = chain.player:text({
    name = "interact_panel", text = "X", font = "fonts/font_medium_mf"})
interact:set_shape(0, 0, pw, ph)
interact:set_visible(false)
interact:set_alpha(0.5)
local copr = chain.radial:panel({name = "copr_overlay_panel"})
copr:set_shape(0, 0, pw, ph)
copr:set_visible(true)
copr:set_alpha(1)

RT:update(mgr, 1.0, 0.1)
_positive_armor_alpha = chain.armor:alpha()
_positive_health_alpha = chain.health:alpha()
_positive_p_visible = P._root:visible()

local blockers = {
    {name = "carry", prim = carry},
    {name = "custom", prim = custom},
    {name = "interact", prim = interact},
    {name = "copr"},
}
local results = {}
local t = 1.1
for _, entry in ipairs(blockers) do
    if entry.name == "copr" then
        -- The numeric "0" child is created only while the COPR source is
        -- active, matching the native create/destroy population.
        local copr0 = copr:polygon({
            name = "0", layer = 0,
            triangles = {Vector3(0, 0, 0), Vector3(10, 0, 0), Vector3(5, 10, 0)},
        })
        copr0:set_shape(0, 0, pw, ph)
        copr0:set_visible(true)
        copr0:set_alpha(0.5)
    else
        entry.prim:set_visible(true)
    end
    RT:update(mgr, t, 0.1)
    results[entry.name] = {
        p_visible = P._root:visible(),
        armor_alpha = chain.armor:alpha(),
        health_alpha = chain.health:alpha(),
        same_primitives = chain.armor == chain.delayed:child("radial_delayed_damage_armor")
            and chain.health == chain.delayed:child("radial_delayed_damage_health"),
    }
    if entry.name == "copr" then
        copr:clear()
    else
        entry.prim:set_visible(false)
    end
    t = t + 0.1
    RT:update(mgr, t, 0.1)
    results[entry.name].recover_p_visible = P._root:visible()
    results[entry.name].recover_armor_alpha = chain.armor:alpha()
    results[entry.name].recover_health_alpha = chain.health:alpha()
    t = t + 0.1
end
_blocker_results = results
'''

LIFECYCLE = r'''
local chain, sent = mount_positive()
RT:update(mgr, 1.0, 0.1)
_positive_armor_alpha = chain.armor:alpha()
_positive_health_alpha = chain.health:alpha()
_positive_p_visible = P._root:visible()

-- Player option off unmounts the owned block.
kyohud.settings.enable_player = false
RT:refresh_settings(mgr)
RT:update(mgr, 1.1, 0.1)
_player_off_root = P._root
_player_off_armor = chain.armor:alpha()
_player_off_health = chain.health:alpha()

kyohud.settings.enable_player = true
RT:refresh_settings(mgr)
RT:update(mgr, 1.2, 0.1)
_player_on_armor = chain.armor:alpha()
_player_on_health = chain.health:alpha()
_player_on_p_visible = P._root:visible()

-- Foundation off removes the runtime and the player with it.
kyohud.settings.enable_hud_foundation = false
RT:refresh_settings(mgr)
_foundation_off_armor = chain.armor:alpha()
_foundation_off_health = chain.health:alpha()

kyohud.settings.enable_hud_foundation = true
RT:refresh_settings(mgr)
RT:update(mgr, 1.4, 0.1)
_foundation_on_armor = chain.armor:alpha()
_foundation_on_health = chain.health:alpha()
_foundation_on_p_visible = P._root:visible()

-- Explicit runtime unmount releases the replacement without a stale mask.
RT:unmount()
_unmount_armor = chain.armor:alpha()
_unmount_health = chain.health:alpha()

RT:refresh_settings(mgr)
RT:update(mgr, 1.6, 0.1)
_remount_armor = chain.armor:alpha()
_remount_health = chain.health:alpha()
_remount_p_visible = P._root:visible()

-- Live source replacement removes the delayed getter. Restoration must release
-- the two alphas, then the original source recovers the same primitives.
local original_character_damage = unit.character_damage
local replacement = {
    _health = 100,
    _health_max = 100,
    _armor = 50,
    _armor_max = 50,
    _revives = 1,
    get_real_health = function(self) return self._health end,
    _max_health = function(self) return self._health_max end,
    get_real_armor = function(self) return self._armor end,
    _max_armor = function(self) return self._armor_max end,
    get_revives = function(self) return self._revives end,
}
unit.character_damage = function(self) return replacement end
sync_native(chain, replacement)
RT:update(mgr, 1.8, 0.1)
_source_off_armor = chain.armor:alpha()
_source_off_health = chain.health:alpha()
_source_off_same_primitives = chain.armor == chain.delayed:child("radial_delayed_damage_armor")
    and chain.health == chain.delayed:child("radial_delayed_damage_health")

unit.character_damage = original_character_damage
sync_native(chain)
RT:update(mgr, 1.9, 0.1)
_source_on_armor = chain.armor:alpha()
_source_on_health = chain.health:alpha()
_source_on_p_visible = P._root:visible()
_source_on_same_primitives = chain.armor == chain.delayed:child("radial_delayed_damage_armor")
    and chain.health == chain.delayed:child("radial_delayed_damage_health")
'''

INVALID_CHAIN = r'''
local chain, sent = mount_positive()
RT:update(mgr, 1.0, 0.1)
_positive_armor_alpha = chain.armor:alpha()
_positive_health_alpha = chain.health:alpha()

-- Return to the neutral released state before invalidating the chain.
cd._remaining_delayed = 0
chain.armor:set_visible(false)
chain.health:set_visible(false)
RT:update(mgr, 1.1, 0.1)
_neutral_armor_alpha = chain.armor:alpha()
_neutral_health_alpha = chain.health:alpha()

-- One cached leaf is reparented away from its required container. The whole
-- replacement must be invalid: neither this foreign target nor its sibling may
-- be hidden.
chain.delayed._children["radial_delayed_damage_armor"] = nil
chain.armor._parent = panel_double
panel_double._children["foreign_delayed_armor"] = chain.armor
cd._remaining_delayed = 60
chain.armor:set_visible(true)
chain.health:set_visible(true)
RT:update(mgr, 1.2, 0.1)
_invalid_foreign_alpha = chain.armor:alpha()
_invalid_sibling_alpha = chain.health:alpha()
_invalid_p_visible = P._root:visible()
_invalid_same_health = chain.health == chain.delayed:child("radial_delayed_damage_health")

-- Reattach the exact same leaf and recover the exact two alpha targets.
panel_double._children["foreign_delayed_armor"] = nil
chain.armor._parent = chain.delayed
chain.delayed._children["radial_delayed_damage_armor"] = chain.armor
RT:update(mgr, 1.3, 0.1)
_repair_armor_alpha = chain.armor:alpha()
_repair_health_alpha = chain.health:alpha()
_repair_p_visible = P._root:visible()

-- A replaced delayed container is a different native chain. Its foreign leaves
-- must keep their own alphas while the stale replacement is released.
cd._remaining_delayed = 0
chain.armor:set_visible(false)
chain.health:set_visible(false)
RT:update(mgr, 1.4, 0.1)
local pw, ph = chain.pw, chain.ph
local foreign_delayed = chain.radial:panel({name = "radial_delayed_damage"})
foreign_delayed:set_shape(0, 0, pw, ph)
foreign_delayed:set_visible(true)
foreign_delayed:set_alpha(1)
local foreign_armor = foreign_delayed:bitmap({name = "radial_delayed_damage_armor"})
foreign_armor:set_shape(0, 0, pw, ph)
foreign_armor:set_visible(true)
foreign_armor:set_alpha(0.61)
local foreign_health = foreign_delayed:bitmap({name = "radial_delayed_damage_health"})
foreign_health:set_shape(0, 0, pw, ph)
foreign_health:set_visible(true)
foreign_health:set_alpha(0.83)

cd._remaining_delayed = 60
RT:update(mgr, 1.5, 0.1)
_replaced_foreign_armor_alpha = foreign_armor:alpha()
_replaced_foreign_health_alpha = foreign_health:alpha()
_replaced_old_armor_alpha = chain.armor:alpha()
_replaced_old_health_alpha = chain.health:alpha()
_replaced_p_visible = P._root:visible()

chain.radial._children["radial_delayed_damage"] = chain.delayed
chain.armor:set_visible(true)
chain.health:set_visible(true)
RT:update(mgr, 1.6, 0.1)
_restored_armor_alpha = chain.armor:alpha()
_restored_health_alpha = chain.health:alpha()
_restored_p_visible = P._root:visible()
_restored_same_primitives = chain.armor == chain.delayed:child("radial_delayed_damage_armor")
    and chain.health == chain.delayed:child("radial_delayed_damage_health")
'''

OWNED_DEBT_PARENT = r'''
local chain, sent = mount_positive()
RT:update(mgr, 1.0, 0.1)
_positive_armor_alpha = chain.armor:alpha()
_positive_health_alpha = chain.health:alpha()

local gauge = P._gauge
local root = gauge.root

local function neutral(t)
    cd._remaining_delayed = 0
    chain.armor:set_visible(false)
    chain.health:set_visible(false)
    RT:update(mgr, t, 0.1)
end

local function arm(t)
    cd._remaining_delayed = 60
    chain.armor:set_visible(true)
    chain.health:set_visible(true)
end

-- Foreign parent: the owned gauge root is no longer owned by the player root.
local actual_parent = root._parent
root._parent = panel_double
arm(1.1)
RT:update(mgr, 1.1, 0.1)
_foreign_armor_alpha = chain.armor:alpha()
_foreign_health_alpha = chain.health:alpha()
root._parent = actual_parent
RT:update(mgr, 1.2, 0.1)
_foreign_recover_armor_alpha = chain.armor:alpha()
_foreign_recover_health_alpha = chain.health:alpha()
_foreign_recover_p_visible = P._root:visible()

-- Corrupt geometry that the owned render cannot repair in the same frame.
neutral(1.3)
local original_set_shape = root.set_shape
root:set_shape(root:x() + 30, root:y(), root:w(), root:h())
root.set_shape = function() end
arm(1.4)
RT:update(mgr, 1.4, 0.1)
_corrupt_armor_alpha = chain.armor:alpha()
_corrupt_health_alpha = chain.health:alpha()
root.set_shape = original_set_shape
RT:update(mgr, 1.5, 0.1)
_corrupt_recover_armor_alpha = chain.armor:alpha()
_corrupt_recover_health_alpha = chain.health:alpha()
_corrupt_recover_p_visible = P._root:visible()

-- Invisible owned debt parent.
neutral(1.6)
local original_set_visible = root.set_visible
root:set_visible(false)
root.set_visible = function() end
arm(1.7)
RT:update(mgr, 1.7, 0.1)
_invisible_armor_alpha = chain.armor:alpha()
_invisible_health_alpha = chain.health:alpha()
root.set_visible = original_set_visible
RT:update(mgr, 1.8, 0.1)
_invisible_recover_armor_alpha = chain.armor:alpha()
_invisible_recover_health_alpha = chain.health:alpha()
_invisible_recover_p_visible = P._root:visible()

-- Alpha-zero owned debt parent.
neutral(1.9)
local original_set_alpha = root.set_alpha
root:set_alpha(0)
root.set_alpha = function() end
arm(2.0)
RT:update(mgr, 2.0, 0.1)
_alpha0_armor_alpha = chain.armor:alpha()
_alpha0_health_alpha = chain.health:alpha()
root.set_alpha = original_set_alpha
RT:update(mgr, 2.1, 0.1)
_alpha0_recover_armor_alpha = chain.armor:alpha()
_alpha0_recover_health_alpha = chain.health:alpha()
_alpha0_recover_p_visible = P._root:visible()
'''

THROTTLED = r'''
local chain, sent = mount_positive()
RT:update(mgr, 1.0, 0.1)
_positive_armor_alpha = chain.armor:alpha()
_positive_health_alpha = chain.health:alpha()
_positive_p_visible = P._root:visible()

-- Throttled frames (< 0.5 s after the last recovery pass) still observe the
-- live source. The debt disappears with the live health/armor change and the
-- native leaves hide natively: the replacement must release, not mask.
cd._remaining_delayed = 0
cd._health = 100
cd._armor = 50
sync_native(chain)
chain.armor:set_visible(false)
chain.health:set_visible(false)
RT:update(mgr, 1.1, 0.1)
_throttled_off_armor_alpha = chain.armor:alpha()
_throttled_off_health_alpha = chain.health:alpha()
_throttled_off_p_visible = P._root:visible()

-- A new live positive debt on another throttled frame must reacquire the same
-- primitives from fresh values, not from a cached render.
cd._remaining_delayed = 60
cd._health = 60
cd._armor = 25
sync_native(chain)
chain.armor:set_visible(true)
chain.health:set_visible(true)
RT:update(mgr, 1.2, 0.1)
_throttled_back_armor_alpha = chain.armor:alpha()
_throttled_back_health_alpha = chain.health:alpha()
_throttled_back_p_visible = P._root:visible()
_throttled_back_same_primitives = chain.armor == chain.delayed:child("radial_delayed_damage_armor")
    and chain.health == chain.delayed:child("radial_delayed_damage_health")

-- A live health change alone does not invalidate an otherwise positive debt.
cd._health = 40
cd._armor = 0
sync_native(chain)
RT:update(mgr, 1.3, 0.1)
_throttled_health_armor_alpha = chain.armor:alpha()
_throttled_health_health_alpha = chain.health:alpha()
_throttled_health_p_visible = P._root:visible()
'''


class DelayedReplacementPositiveTests(unittest.TestCase):
    def test_positive_known_debt_replaces_two_leaves_and_restores_exact_alphas(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + POSITIVE)
        g = lua.globals()

        self.assertTrue(bool(g._positive_p_visible),
                        "positive live debt must keep the owned player visible")
        self.assertAlmostEqual(float(g._positive_armor_alpha), 0.0, places=5,
                               msg="positive debt must set the armor duplicate alpha to 0")
        self.assertAlmostEqual(float(g._positive_health_alpha), 0.0, places=5,
                               msg="positive debt must set the health duplicate alpha to 0")
        self.assertTrue(bool(g._positive_armor_visible),
                        "replacement must not rewrite the native armor visibility")
        self.assertTrue(bool(g._positive_health_visible),
                        "replacement must not rewrite the native health visibility")
        self.assertTrue(bool(g._positive_exact_two_zero),
                        "exactly the two delayed-damage leaves must be alpha 0")
        self.assertTrue(bool(g._positive_parents_unchanged),
                        "replacement must not mutate any native parent property")
        self.assertTrue(bool(g._positive_sentinels_unchanged),
                        "unrelated and remote sentinels must remain unchanged")

        self.assertAlmostEqual(float(g._native_armor_alpha), 0.0, places=5,
                               msg="native visibility/color mutation must not restore alpha")
        self.assertAlmostEqual(float(g._native_health_alpha), 0.0, places=5,
                               msg="native visibility/color mutation must not restore alpha")
        self.assertFalse(bool(g._native_armor_visible),
                         "native armor visibility must keep the value set by the native update")
        self.assertTrue(bool(g._native_health_visible),
                        "native health visibility must keep the value set by the native update")
        self.assertAlmostEqual(float(g._reassert_armor_alpha), 0.0, places=5,
                               msg="ordinary reassertion must keep the armor alpha at 0")
        self.assertAlmostEqual(float(g._reassert_health_alpha), 0.0, places=5,
                               msg="ordinary reassertion must keep the health alpha at 0")
        self.assertTrue(bool(g._reassert_p_visible),
                        "ordinary reassertion must keep the player visible")

        self.assertAlmostEqual(float(g._release_armor_alpha), 0.65, places=5,
                               msg="release must restore the exact original armor alpha")
        self.assertAlmostEqual(float(g._release_health_alpha), 0.85, places=5,
                               msg="release must restore the exact original health alpha")
        self.assertTrue(bool(g._release_p_visible),
                        "release must leave the owned player visible")
        self.assertTrue(bool(g._release_same_primitives),
                        "release must keep the exact two native leaf identities")

        self.assertAlmostEqual(float(g._recovery_armor_alpha), 0.0, places=5,
                               msg="positive debt recovery must reacquire the armor leaf")
        self.assertAlmostEqual(float(g._recovery_health_alpha), 0.0, places=5,
                               msg="positive debt recovery must reacquire the health leaf")
        self.assertTrue(bool(g._recovery_p_visible),
                        "positive debt recovery must keep the player visible")
        self.assertTrue(bool(g._recovery_parents_unchanged),
                        "recovery must not mutate any native parent property")


class DelayedReplacementLossTests(unittest.TestCase):
    def test_loss_getter_nan_fallback_and_same_primitive_recovery(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + LOSS_NAN)
        g = lua.globals()

        self.assertTrue(bool(g._positive_known),
                        "precondition: live debt must be known before the loss")
        self.assertAlmostEqual(float(g._positive_armor_alpha), 0.0, places=5)
        self.assertAlmostEqual(float(g._positive_health_alpha), 0.0, places=5)
        self.assertTrue(bool(g._positive_p_visible))

        self.assertFalse(bool(g._missing_known),
                         "a lost delayed getter must clear the known debt")
        self.assertAlmostEqual(float(g._missing_armor_alpha), 0.65, places=5,
                               msg="lost getter must restore the exact armor alpha")
        self.assertAlmostEqual(float(g._missing_health_alpha), 0.85, places=5,
                               msg="lost getter must restore the exact health alpha")
        self.assertFalse(bool(g._missing_p_visible),
                         "lost getter must fall back to native blocker priority")
        self.assertTrue(bool(g._missing_same_primitives),
                        "fallback must not replace the native leaves")

        self.assertFalse(bool(g._nan_known),
                         "a non-finite delayed getter must clear the known debt")
        self.assertAlmostEqual(float(g._nan_armor_alpha), 0.65, places=5,
                               msg="NaN must restore the exact armor alpha")
        self.assertAlmostEqual(float(g._nan_health_alpha), 0.85, places=5,
                               msg="NaN must restore the exact health alpha")
        self.assertFalse(bool(g._nan_p_visible),
                         "NaN must fall back to native blocker priority")

        self.assertTrue(bool(g._recovered_known),
                        "the same live getter must recover known debt")
        self.assertAlmostEqual(float(g._recovered_armor_alpha), 0.0, places=5,
                               msg="recovery must reacquire the same armor leaf")
        self.assertAlmostEqual(float(g._recovered_health_alpha), 0.0, places=5,
                               msg="recovery must reacquire the same health leaf")
        self.assertTrue(bool(g._recovered_p_visible),
                        "recovery must keep the owned player visible")
        self.assertTrue(bool(g._recovered_same_primitives),
                        "recovery must reuse the exact same two native leaves")


class DelayedReplacementSetterFailureTests(unittest.TestCase):
    def test_failed_lease_setter_rolls_back_exact_alphas_then_recovers(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + SETTER_FAILURE)
        g = lua.globals()

        self.assertAlmostEqual(float(g._positive_armor_alpha), 0.0, places=5)
        self.assertAlmostEqual(float(g._positive_health_alpha), 0.0, places=5)
        self.assertAlmostEqual(float(g._released_armor_alpha), 0.65, places=5)
        self.assertAlmostEqual(float(g._released_health_alpha), 0.85, places=5)

        self.assertAlmostEqual(float(g._failed_armor_alpha), 0.65, places=5,
                               msg="partial lease mutation must roll the armor alpha back")
        self.assertAlmostEqual(float(g._failed_health_alpha), 0.85, places=5,
                               msg="failed setter must leave the health alpha untouched")
        self.assertFalse(bool(g._failed_zero_leaves),
                         "a failed lease must not leave either leaf hidden")
        self.assertFalse(bool(g._failed_p_visible),
                         "a failed lease must fail closed to native blocker priority")
        self.assertTrue(bool(g._failed_same_primitives),
                        "a failed lease must not replace the native leaves")

        self.assertAlmostEqual(float(g._recovered_armor_alpha), 0.0, places=5,
                               msg="a repaired setter must reacquire the armor leaf")
        self.assertAlmostEqual(float(g._recovered_health_alpha), 0.0, places=5,
                               msg="a repaired setter must reacquire the health leaf")
        self.assertTrue(bool(g._recovered_exact_two_zero),
                        "recovery must hide exactly the two delayed leaves")
        self.assertTrue(bool(g._recovered_p_visible),
                        "recovery must keep the owned player visible")
        self.assertTrue(bool(g._recovered_same_primitives),
                        "recovery must reuse the exact same two native leaves")


class DelayedReplacementOtherBlockerTests(unittest.TestCase):
    def test_other_native_blockers_restore_exact_alphas_then_recover(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + OTHER_BLOCKERS)
        g = lua.globals()

        self.assertAlmostEqual(float(g._positive_armor_alpha), 0.0, places=5)
        self.assertAlmostEqual(float(g._positive_health_alpha), 0.0, places=5)
        self.assertTrue(bool(g._positive_p_visible))

        for name in ("carry", "custom", "interact", "copr"):
            with self.subTest(blocker=name):
                result = g._blocker_results[name]
                self.assertFalse(bool(result["p_visible"]),
                                 f"{name} blocker must hide the owned player")
                self.assertAlmostEqual(float(result["armor_alpha"]), 0.65,
                                       places=5,
                                       msg=f"{name} blocker must restore the exact armor alpha")
                self.assertAlmostEqual(float(result["health_alpha"]), 0.85,
                                       places=5,
                                       msg=f"{name} blocker must restore the exact health alpha")
                self.assertTrue(bool(result["same_primitives"]),
                                f"{name} blocker must not replace the native leaves")
                self.assertTrue(bool(result["recover_p_visible"]),
                                f"{name} blocker removal must recover the player")
                self.assertAlmostEqual(float(result["recover_armor_alpha"]), 0.0,
                                       places=5,
                                       msg=f"{name} removal must reacquire the armor leaf")
                self.assertAlmostEqual(float(result["recover_health_alpha"]), 0.0,
                                       places=5,
                                       msg=f"{name} removal must reacquire the health leaf")


class DelayedReplacementLifecycleTests(unittest.TestCase):
    def test_player_foundation_unmount_and_source_replacement_release_exactly(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + LIFECYCLE)
        g = lua.globals()

        self.assertAlmostEqual(float(g._positive_armor_alpha), 0.0, places=5)
        self.assertAlmostEqual(float(g._positive_health_alpha), 0.0, places=5)
        self.assertTrue(bool(g._positive_p_visible))

        self.assertIsNone(g._player_off_root,
                          "player option off must unmount the owned root")
        self.assertAlmostEqual(float(g._player_off_armor), 0.65, places=5,
                               msg="player option off must restore the armor alpha")
        self.assertAlmostEqual(float(g._player_off_health), 0.85, places=5,
                               msg="player option off must restore the health alpha")
        self.assertAlmostEqual(float(g._player_on_armor), 0.0, places=5,
                               msg="player option on must reacquire the armor leaf")
        self.assertAlmostEqual(float(g._player_on_health), 0.0, places=5,
                               msg="player option on must reacquire the health leaf")
        self.assertTrue(bool(g._player_on_p_visible))

        self.assertAlmostEqual(float(g._foundation_off_armor), 0.65, places=5,
                               msg="foundation off must restore the armor alpha")
        self.assertAlmostEqual(float(g._foundation_off_health), 0.85, places=5,
                               msg="foundation off must restore the health alpha")
        self.assertAlmostEqual(float(g._foundation_on_armor), 0.0, places=5,
                               msg="foundation on must reacquire the armor leaf")
        self.assertAlmostEqual(float(g._foundation_on_health), 0.0, places=5,
                               msg="foundation on must reacquire the health leaf")
        self.assertTrue(bool(g._foundation_on_p_visible))

        self.assertAlmostEqual(float(g._unmount_armor), 0.65, places=5,
                               msg="runtime unmount must restore the armor alpha")
        self.assertAlmostEqual(float(g._unmount_health), 0.85, places=5,
                               msg="runtime unmount must restore the health alpha")
        self.assertAlmostEqual(float(g._remount_armor), 0.0, places=5,
                               msg="runtime remount must reacquire the armor leaf")
        self.assertAlmostEqual(float(g._remount_health), 0.0, places=5,
                               msg="runtime remount must reacquire the health leaf")
        self.assertTrue(bool(g._remount_p_visible))

        self.assertAlmostEqual(float(g._source_off_armor), 0.65, places=5,
                               msg="source replacement must restore the armor alpha")
        self.assertAlmostEqual(float(g._source_off_health), 0.85, places=5,
                               msg="source replacement must restore the health alpha")
        self.assertTrue(bool(g._source_off_same_primitives),
                        "source replacement must not replace the native leaves")
        self.assertAlmostEqual(float(g._source_on_armor), 0.0, places=5,
                               msg="restored live source must reacquire the armor leaf")
        self.assertAlmostEqual(float(g._source_on_health), 0.0, places=5,
                               msg="restored live source must reacquire the health leaf")
        self.assertTrue(bool(g._source_on_p_visible))
        self.assertTrue(bool(g._source_on_same_primitives),
                        "restored live source must reuse the exact same two leaves")


class DelayedReplacementInvalidChainTests(unittest.TestCase):
    def test_replaced_or_reparented_native_child_never_hides_foreign_targets(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + INVALID_CHAIN)
        g = lua.globals()

        self.assertAlmostEqual(float(g._positive_armor_alpha), 0.0, places=5)
        self.assertAlmostEqual(float(g._positive_health_alpha), 0.0, places=5)
        self.assertAlmostEqual(float(g._neutral_armor_alpha), 0.65, places=5)
        self.assertAlmostEqual(float(g._neutral_health_alpha), 0.85, places=5)

        self.assertAlmostEqual(float(g._invalid_foreign_alpha), 0.65, places=5,
                               msg="a reparented leaf must not be hidden as a foreign target")
        self.assertAlmostEqual(float(g._invalid_sibling_alpha), 0.85, places=5,
                               msg="an invalid chain must not partially hide the sibling")
        self.assertFalse(bool(g._invalid_p_visible),
                         "an invalid chain must fall back to native blocker priority")
        self.assertTrue(bool(g._invalid_same_health),
                        "the invalid chain must not replace the sibling primitive")

        self.assertAlmostEqual(float(g._repair_armor_alpha), 0.0, places=5,
                               msg="repaired chain must reacquire the armor leaf")
        self.assertAlmostEqual(float(g._repair_health_alpha), 0.0, places=5,
                               msg="repaired chain must reacquire the health leaf")
        self.assertTrue(bool(g._repair_p_visible),
                        "repaired chain must keep the owned player visible")

        self.assertAlmostEqual(float(g._replaced_foreign_armor_alpha), 0.61,
                               places=5,
                               msg="a replaced container's foreign armor leaf must stay untouched")
        self.assertAlmostEqual(float(g._replaced_foreign_health_alpha), 0.83,
                               places=5,
                               msg="a replaced container's foreign health leaf must stay untouched")
        self.assertAlmostEqual(float(g._replaced_old_armor_alpha), 0.65, places=5,
                               msg="the stale replaced armor leaf must stay released")
        self.assertAlmostEqual(float(g._replaced_old_health_alpha), 0.85, places=5,
                               msg="the stale replaced health leaf must stay released")

        self.assertAlmostEqual(float(g._restored_armor_alpha), 0.0, places=5,
                               msg="restored container must reacquire the armor leaf")
        self.assertAlmostEqual(float(g._restored_health_alpha), 0.0, places=5,
                               msg="restored container must reacquire the health leaf")
        self.assertTrue(bool(g._restored_p_visible),
                        "restored container must keep the owned player visible")
        self.assertTrue(bool(g._restored_same_primitives),
                        "restored container must reuse the exact same two leaves")


class DelayedReplacementOwnedDebtParentTests(unittest.TestCase):
    def test_foreign_corrupt_invisible_or_alpha0_owned_debt_parent_blocks_replacement(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + OWNED_DEBT_PARENT)
        g = lua.globals()

        self.assertAlmostEqual(float(g._positive_armor_alpha), 0.0, places=5)
        self.assertAlmostEqual(float(g._positive_health_alpha), 0.0, places=5)

        cases = (
            ("foreign",
             g._foreign_armor_alpha, g._foreign_health_alpha,
             g._foreign_recover_armor_alpha, g._foreign_recover_health_alpha,
             g._foreign_recover_p_visible),
            ("corrupt",
             g._corrupt_armor_alpha, g._corrupt_health_alpha,
             g._corrupt_recover_armor_alpha, g._corrupt_recover_health_alpha,
             g._corrupt_recover_p_visible),
            ("invisible",
             g._invisible_armor_alpha, g._invisible_health_alpha,
             g._invisible_recover_armor_alpha, g._invisible_recover_health_alpha,
             g._invisible_recover_p_visible),
            ("alpha0",
             g._alpha0_armor_alpha, g._alpha0_health_alpha,
             g._alpha0_recover_armor_alpha, g._alpha0_recover_health_alpha,
             g._alpha0_recover_p_visible),
        )
        for name, armor, health, rec_armor, rec_health, rec_p in cases:
            with self.subTest(condition=name):
                self.assertAlmostEqual(float(armor), 0.65, places=5,
                                       msg=f"{name} owned debt parent must not authorize hiding")
                self.assertAlmostEqual(float(health), 0.85, places=5,
                                       msg=f"{name} owned debt parent must not authorize hiding")
                self.assertAlmostEqual(float(rec_armor), 0.0, places=5,
                                       msg=f"{name} repair must reacquire the armor leaf")
                self.assertAlmostEqual(float(rec_health), 0.0, places=5,
                                       msg=f"{name} repair must reacquire the health leaf")
                self.assertTrue(bool(rec_p),
                                f"{name} repair must keep the owned player visible")


class DelayedReplacementThrottledTests(unittest.TestCase):
    def test_throttled_frames_follow_live_debt_and_health_without_stale_mask(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + THROTTLED)
        g = lua.globals()

        self.assertAlmostEqual(float(g._positive_armor_alpha), 0.0, places=5)
        self.assertAlmostEqual(float(g._positive_health_alpha), 0.0, places=5)
        self.assertTrue(bool(g._positive_p_visible))

        self.assertAlmostEqual(float(g._throttled_off_armor_alpha), 0.65,
                               places=5,
                               msg="a throttled frame must release stale armor alpha")
        self.assertAlmostEqual(float(g._throttled_off_health_alpha), 0.85,
                               places=5,
                               msg="a throttled frame must release stale health alpha")
        self.assertTrue(bool(g._throttled_off_p_visible),
                        "a release on a throttled frame must keep the player visible")

        self.assertAlmostEqual(float(g._throttled_back_armor_alpha), 0.0,
                               places=5,
                               msg="a throttled frame must use the fresh positive debt")
        self.assertAlmostEqual(float(g._throttled_back_health_alpha), 0.0,
                               places=5,
                               msg="a throttled frame must use the fresh positive debt")
        self.assertTrue(bool(g._throttled_back_p_visible),
                        "a fresh positive debt on a throttled frame must keep the player visible")
        self.assertTrue(bool(g._throttled_back_same_primitives),
                        "throttled recovery must reuse the exact same two leaves")

        self.assertAlmostEqual(float(g._throttled_health_armor_alpha), 0.0,
                               places=5,
                               msg="a live health change must not restore a stale mask")
        self.assertAlmostEqual(float(g._throttled_health_health_alpha), 0.0,
                               places=5,
                               msg="a live health change must not restore a stale mask")
        self.assertTrue(bool(g._throttled_health_p_visible),
                        "a live health change must keep the player visible")


class DelayedReplacementReviewRedTests(unittest.TestCase):
    """Compact RED cases for the independent Stoic replacement review."""

    def test_zero_max_known_armor_masks_then_missing_getter_falls_back(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + r'''
            local chain, sent = mount_positive()
            cd._health = 60
            cd._health_max = 100
            cd._armor = 0
            cd._armor_max = 0
            cd._remaining_delayed = 20
            sync_native(chain)
            chain.armor:set_visible(false)
            chain.health:set_visible(true)
            RT:update(mgr, 1.0, 0.1)
            _zero_positive_p = P._root:visible()
            _zero_positive_armor = chain.armor:alpha()
            _zero_positive_health = chain.health:alpha()

            local original_get_real_armor = cd.get_real_armor
            cd.get_real_armor = nil
            RT:update(mgr, 1.1, 0.1)
            _zero_missing_armor = chain.armor:alpha()
            _zero_missing_health = chain.health:alpha()
            _zero_missing_p = P._root:visible()

            cd.get_real_armor = original_get_real_armor
            RT:update(mgr, 1.2, 0.1)
            _zero_recover_armor = chain.armor:alpha()
            _zero_recover_health = chain.health:alpha()
            _zero_recover_p = P._root:visible()
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._zero_positive_p),
                        "known raw 0/0 armor must keep the player visible")
        self.assertAlmostEqual(float(g._zero_positive_armor), 0.0, places=5,
                               msg="known 0/0 armor must still hide the armor duplicate")
        self.assertAlmostEqual(float(g._zero_positive_health), 0.0, places=5,
                               msg="positive health debt must hide the health duplicate")
        self.assertAlmostEqual(float(g._zero_missing_armor), 0.65, places=5,
                               msg="missing armor getter must restore the armor alpha")
        self.assertAlmostEqual(float(g._zero_missing_health), 0.85, places=5,
                               msg="missing armor getter must restore the health alpha")
        self.assertFalse(bool(g._zero_missing_p),
                         "missing armor getter must fall back to native priority")
        self.assertAlmostEqual(float(g._zero_recover_armor), 0.0, places=5,
                               msg="restored 0/0 armor source must reacquire the armor leaf")
        self.assertAlmostEqual(float(g._zero_recover_health), 0.0, places=5,
                               msg="restored health debt must reacquire the health leaf")
        self.assertTrue(bool(g._zero_recover_p),
                        "restored 0/0 armor source must keep the player visible")

    def test_native_color_userdata_is_accepted_without_global_color_change(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + r'''
            local chain, sent = mount_positive()
            local original_color = Color
            local health_proxy = newproxy(true)
            getmetatable(health_proxy).__index = function(_, key)
                if key == "r" then return 0.6 end
                return 0
            end
            local shield_proxy = newproxy(true)
            getmetatable(shield_proxy).__index = function(_, key)
                if key == "r" then return 0.5 end
                return 0
            end
            local original_health_color = chain.radial_health.color
            local original_shield_color = chain.radial_shield.color
            chain.radial_health.color = function() return health_proxy end
            chain.radial_shield.color = function() return shield_proxy end
            RT:update(mgr, 1.0, 0.1)
            _ud_p = P._root:visible()
            _ud_armor = chain.armor:alpha()
            _ud_health = chain.health:alpha()
            _ud_type = type(health_proxy)
            _ud_color_unchanged = (Color == original_color)
            chain.radial_health.color = original_health_color
            chain.radial_shield.color = original_shield_color
        ''')
        g = lua.globals()

        self.assertEqual(str(g._ud_type), "userdata",
                         "fixture must exercise a real userdata color proxy")
        self.assertTrue(bool(g._ud_color_unchanged),
                        "global Color must remain unchanged")
        self.assertTrue(bool(g._ud_p),
                        "userdata native color must keep the player visible")
        self.assertAlmostEqual(float(g._ud_armor), 0.0, places=5,
                               msg="userdata color.r must authorize the armor alpha lease")
        self.assertAlmostEqual(float(g._ud_health), 0.0, places=5,
                               msg="userdata color.r must authorize the health alpha lease")

    def test_player_throttle_corrupt_debt_rect_and_live_source_change_release(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + r'''
            local chain, sent = mount_positive()
            RT:update(mgr, 1.0, 0.1)
            _pt_positive_armor = chain.armor:alpha()
            _pt_positive_health = chain.health:alpha()

            local rect = P._gauge._delayed_health[1]
            local original_set_shape = rect.set_shape
            rect:set_shape(rect:x() + 30, rect:y(), rect:w(), rect:h())
            rect.set_shape = function() end
            RT:update(mgr, 1.01, 0.01)
            _pt_corrupt_armor = chain.armor:alpha()
            _pt_corrupt_health = chain.health:alpha()
            _pt_corrupt_same = chain.armor == chain.delayed:child("radial_delayed_damage_armor")
                and chain.health == chain.delayed:child("radial_delayed_damage_health")
            rect.set_shape = original_set_shape
            RT:update(mgr, 1.1, 0.1)
            _pt_corrupt_recover_armor = chain.armor:alpha()
            _pt_corrupt_recover_health = chain.health:alpha()
            _pt_corrupt_recover_p = P._root:visible()

            cd._health = 40
            cd._remaining_delayed = 20
            sync_native(chain)
            RT:update(mgr, 1.11, 0.01)
            _pt_source_armor = chain.armor:alpha()
            _pt_source_health = chain.health:alpha()
            _pt_source_gauge_health = P._gauge ~= nil
                and near(P._gauge._health.current, 40)
            _pt_source_gauge_debt = P._gauge ~= nil
                and P._gauge._health_effects ~= nil
                and P._gauge._health_effects.delayed_damage ~= nil
                and P._gauge._health_effects.delayed_damage.known == true
                and near(P._gauge._health_effects.delayed_damage.amount, 20)
            _pt_source_verify = P:verify() == true
            _pt_source_same = chain.armor == chain.delayed:child("radial_delayed_damage_armor")
                and chain.health == chain.delayed:child("radial_delayed_damage_health")
            RT:update(mgr, 1.2, 0.1)
            _pt_source_recover_armor = chain.armor:alpha()
            _pt_source_recover_health = chain.health:alpha()
            _pt_source_recover_p = P._root:visible()
        ''')
        g = lua.globals()

        self.assertAlmostEqual(float(g._pt_positive_armor), 0.0, places=5)
        self.assertAlmostEqual(float(g._pt_positive_health), 0.0, places=5)
        self.assertAlmostEqual(float(g._pt_corrupt_armor), 0.65, places=5,
                               msg="a P-throttled corrupt debt rect must release the armor alpha")
        self.assertAlmostEqual(float(g._pt_corrupt_health), 0.85, places=5,
                               msg="a P-throttled corrupt debt rect must release the health alpha")
        self.assertTrue(bool(g._pt_corrupt_same),
                        "throttled corruption fallback must keep the same native leaves")
        self.assertAlmostEqual(float(g._pt_corrupt_recover_armor), 0.0, places=5,
                               msg="repaired debt rect must reacquire the armor leaf")
        self.assertAlmostEqual(float(g._pt_corrupt_recover_health), 0.0, places=5,
                               msg="repaired debt rect must reacquire the health leaf")
        self.assertTrue(bool(g._pt_corrupt_recover_p),
                        "repaired debt rect must keep the player visible")

        self.assertAlmostEqual(float(g._pt_source_armor), 0.0, places=5,
                               msg="a P-throttled live change must render fresh then keep the armor lease")
        self.assertAlmostEqual(float(g._pt_source_health), 0.0, places=5,
                               msg="a P-throttled live change must render fresh then keep the health lease")
        self.assertTrue(bool(g._pt_source_gauge_health),
                        "the fresh certified gauge must show the live health 40")
        self.assertTrue(bool(g._pt_source_gauge_debt),
                        "the fresh certified gauge must show the live debt 20")
        self.assertTrue(bool(g._pt_source_verify),
                        "the fresh owned render must be certified")
        self.assertTrue(bool(g._pt_source_same),
                        "the fresh owned render must keep the same native leaves")
        self.assertAlmostEqual(float(g._pt_source_recover_armor), 0.0, places=5,
                               msg="the next full render must keep the armor lease")
        self.assertAlmostEqual(float(g._pt_source_recover_health), 0.0, places=5,
                               msg="the next full render must keep the health lease")
        self.assertTrue(bool(g._pt_source_recover_p),
                        "the next full render must keep the player visible")

    def test_direct_player_unmount_restores_exact_alphas_immediately(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + r'''
            local chain, sent = mount_positive()
            RT:update(mgr, 1.0, 0.1)
            _du_positive_armor = chain.armor:alpha()
            _du_positive_health = chain.health:alpha()
            P:unmount()
            _du_root = P._root
            _du_armor = chain.armor:alpha()
            _du_health = chain.health:alpha()
            _du_same = chain.armor == chain.delayed:child("radial_delayed_damage_armor")
                and chain.health == chain.delayed:child("radial_delayed_damage_health")
            P:mount(mgr)
            RT:update(mgr, 1.1, 0.1)
            _du_recover_armor = chain.armor:alpha()
            _du_recover_health = chain.health:alpha()
            _du_recover_p = P._root and P._root:visible()
        ''')
        g = lua.globals()

        self.assertAlmostEqual(float(g._du_positive_armor), 0.0, places=5)
        self.assertAlmostEqual(float(g._du_positive_health), 0.0, places=5)
        self.assertIsNone(g._du_root,
                          "direct P:unmount must leave the owned root removed")
        self.assertAlmostEqual(float(g._du_armor), 0.65, places=5,
                               msg="direct P:unmount must restore the armor alpha immediately")
        self.assertAlmostEqual(float(g._du_health), 0.85, places=5,
                               msg="direct P:unmount must restore the health alpha immediately")
        self.assertTrue(bool(g._du_same),
                        "direct P:unmount must not replace the native leaves")
        self.assertAlmostEqual(float(g._du_recover_armor), 0.0, places=5,
                               msg="remount must reacquire the armor leaf")
        self.assertAlmostEqual(float(g._du_recover_health), 0.0, places=5,
                               msg="remount must reacquire the health leaf")
        self.assertTrue(bool(g._du_recover_p),
                        "remount must keep the player visible")

    def test_failed_acquire_rollback_keeps_entries_until_repaired(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + r'''
            local chain, sent = mount_positive()
            local NV = kyohud.hud.native_visibility
            local function owned_entries()
                local count = 0
                for _, entry in ipairs(NV._entries or {}) do
                    if entry.object == chain.armor or entry.object == chain.health then
                        count = count + 1
                    end
                end
                return count
            end
            local function armor_marker_active()
                return NV._whitelist[chain.armor] ~= nil
                    and NV._whitelist[chain.armor].alpha == true
            end

            RT:update(mgr, 1.0, 0.1)
            cd._remaining_delayed = 0
            chain.armor:set_visible(false)
            chain.health:set_visible(false)
            RT:update(mgr, 1.1, 0.1)
            _fa_released_armor = chain.armor:alpha()
            _fa_released_health = chain.health:alpha()

            local original_armor_setter = chain.armor.set_alpha
            local original_health_setter = chain.health.set_alpha
            local fail_restore = false
            chain.armor.set_alpha = function(self, value)
                if fail_restore then
                    if self._color then self._color.r = 0.321 end
                    error("rollback setter failed")
                end
                return original_armor_setter(self, value)
            end
            chain.health.set_alpha = function(self, value)
                fail_restore = true
                if self._color then self._color.r = 0.654 end
                error("second acquire setter failed")
            end

            cd._remaining_delayed = 60
            chain.armor:set_visible(true)
            chain.health:set_visible(true)
            RT:update(mgr, 1.2, 0.1)
            _fa_failed_armor = chain.armor:alpha()
            _fa_failed_health = chain.health:alpha()
            _fa_failed_entries = owned_entries()
            _fa_failed_marker = armor_marker_active()

            cd._remaining_delayed = 0
            chain.armor:set_visible(false)
            chain.health:set_visible(false)
            RT:update(mgr, 1.3, 0.1)
            _fa_pending_entries = owned_entries()
            _fa_pending_marker = armor_marker_active()
            _fa_pending_armor = chain.armor:alpha()

            chain.armor.set_alpha = original_armor_setter
            chain.health.set_alpha = original_health_setter
            RT:update(mgr, 1.4, 0.1)
            _fa_restored_armor = chain.armor:alpha()
            _fa_restored_health = chain.health:alpha()
            _fa_final_entries = owned_entries()
            _fa_final_marker = armor_marker_active()
        ''')
        g = lua.globals()

        self.assertAlmostEqual(float(g._fa_released_armor), 0.65, places=5)
        self.assertAlmostEqual(float(g._fa_released_health), 0.85, places=5)
        self.assertEqual(int(g._fa_failed_entries), 1,
                         "failed acquire rollback must retain exactly the partial NV entry")
        self.assertTrue(bool(g._fa_failed_marker),
                        "failed acquire rollback must keep the whitelist alpha marker")
        self.assertEqual(int(g._fa_pending_entries), 1,
                         "still-failing restoration must retain the NV entry")
        self.assertTrue(bool(g._fa_pending_marker),
                        "still-failing restoration must keep the whitelist marker")
        self.assertAlmostEqual(float(g._fa_pending_armor), 0.0, places=5,
                               msg="still-failing rollback must leave the applied alpha pending")
        self.assertAlmostEqual(float(g._fa_restored_armor), 0.65, places=5,
                               msg="repaired setter must restore the exact armor alpha")
        self.assertAlmostEqual(float(g._fa_restored_health), 0.85, places=5,
                               msg="repaired setter must restore the exact health alpha")
        self.assertEqual(int(g._fa_final_entries), 0,
                         "repaired restoration must drop every owned NV entry")
        self.assertFalse(bool(g._fa_final_marker),
                         "repaired restoration must not leave an orphan whitelist marker")

    def test_owned_parent_getter_error_does_not_escape_update_and_restores(self):
        lua, ok = _lua(setup=SETUP)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + r'''
            local chain, sent = mount_positive()
            RT:update(mgr, 1.0, 0.1)
            _og_positive_armor = chain.armor:alpha()
            _og_positive_health = chain.health:alpha()
            local owner_root = P._gauge.root
            local original_parent = owner_root.parent
            owner_root.parent = function() error("owned parent getter failed") end
            local ok_update = pcall(function() RT:update(mgr, 1.1, 0.1) end)
            owner_root.parent = original_parent
            _og_update_ok = ok_update
            _og_armor = chain.armor:alpha()
            _og_health = chain.health:alpha()
            _og_same = chain.armor == chain.delayed:child("radial_delayed_damage_armor")
                and chain.health == chain.delayed:child("radial_delayed_damage_health")
            RT:update(mgr, 1.2, 0.1)
            _og_recover_armor = chain.armor:alpha()
            _og_recover_health = chain.health:alpha()
            _og_recover_p = P._root:visible()
        ''')
        g = lua.globals()

        self.assertAlmostEqual(float(g._og_positive_armor), 0.0, places=5)
        self.assertAlmostEqual(float(g._og_positive_health), 0.0, places=5)
        self.assertTrue(bool(g._og_update_ok),
                        "an owned parent getter error must not escape RT:update")
        self.assertAlmostEqual(float(g._og_armor), 0.65, places=5,
                               msg="owned parent getter error must restore the armor alpha")
        self.assertAlmostEqual(float(g._og_health), 0.85, places=5,
                               msg="owned parent getter error must restore the health alpha")
        self.assertTrue(bool(g._og_same),
                        "owned parent getter error must not replace the native leaves")
        self.assertAlmostEqual(float(g._og_recover_armor), 0.0, places=5,
                               msg="repaired owned ancestry must reacquire the armor leaf")
        self.assertAlmostEqual(float(g._og_recover_health), 0.0, places=5,
                               msg="repaired owned ancestry must reacquire the health leaf")
        self.assertTrue(bool(g._og_recover_p),
                        "repaired owned ancestry must keep the player visible")


if __name__ == "__main__":
    unittest.main()
