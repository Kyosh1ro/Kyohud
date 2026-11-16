"""RED first pass -- actors local health_effects snapshot.

Scope: bounded local delayed-damage and stored-health capture only.
No rendering, no lifecycle matrix, no crew roster matrix.

Expected API (not implemented yet):
  get_actor(HUDManager.PLAYER_PANEL).health_effects.delayed_damage
      = {known = true, amount = <raw remaining>}
  get_actor(HUDManager.PLAYER_PANEL).health_effects.stored_health
      = {known = true, ratio = <current>, max_ratio = <max>}

Native-shaped relay methods are installed before actors.lua loads. The shared
Hooks double only records callbacks; the test dispatches the recorded posthooks
with the real receiver and native args via the lifecycle DISPATCH helper.
"""
import unittest

from test_hud_actors import _lua
from test_hud_actors_lifecycle import DISPATCH

NATIVE_HEALTH_EFFECTS_FIXTURE = r'''
-- Native HUDManager health-effects relay fixtures (hudmanagerpd2.lua:345,424,428).
-- They only retain native data; production capture remains owned by actors PostHooks.
function HUDManager:set_teammate_delayed_damage(i, delayed_damage)
    self._teammate_panels[i] = self._teammate_panels[i] or {}
    self._teammate_panels[i].delayed_damage = delayed_damage
end

function HUDManager:set_stored_health(stored_health_ratio)
    local i = HUDManager.PLAYER_PANEL
    self._teammate_panels[i] = self._teammate_panels[i] or {}
    self._teammate_panels[i].stored_health = stored_health_ratio
end

function HUDManager:set_stored_health_max(stored_health_ratio)
    local i = HUDManager.PLAYER_PANEL
    self._teammate_panels[i] = self._teammate_panels[i] or {}
    self._teammate_panels[i].stored_health_max = stored_health_ratio
end
'''

NATIVE_EFFECTS_RELAY_FIXTURE = r'''
-- Native HUDManager absorption/info/copr relay fixtures (hudmanagerpd2.lua:432-442).
-- They only retain native data; production capture remains owned by actors PostHooks.
function HUDManager:set_absorb_active(i, absorb_amount)
    i = i or HUDManager.PLAYER_PANEL
    self._teammate_panels[i] = self._teammate_panels[i] or {}
    self._teammate_panels[i].absorb_amount = absorb_amount
end

function HUDManager:set_info_meter(i, data)
    i = i or HUDManager.PLAYER_PANEL
    self._teammate_panels[i] = self._teammate_panels[i] or {}
    self._teammate_panels[i].info_meter = data
end

function HUDManager:set_copr_indicator(enabled, static_damage_ratio)
    local i = HUDManager.PLAYER_PANEL
    self._teammate_panels[i] = self._teammate_panels[i] or {}
    self._teammate_panels[i].copr = {
        enabled = enabled,
        static_damage_ratio = static_damage_ratio,
    }
end
'''

NATIVE_RADIAL_FIXTURE = r'''
-- Native HUDManager custom/ability radial relay fixtures (hudmanagerpd2.lua:325-339).
-- Player aliases delegate to the explicit teammate slot; production only needs
-- PostHooks on the two teammate methods.
function HUDManager:set_player_custom_radial(data)
    self:set_teammate_custom_radial(HUDManager.PLAYER_PANEL, data)
end

function HUDManager:set_teammate_custom_radial(i, data)
    self._teammate_panels[i] = self._teammate_panels[i] or {}
    self._teammate_panels[i].custom_radial = data
end

function HUDManager:set_player_ability_radial(data)
    self:set_teammate_ability_radial(HUDManager.PLAYER_PANEL, data)
end

function HUDManager:set_teammate_ability_radial(i, data)
    self._teammate_panels[i] = self._teammate_panels[i] or {}
    self._teammate_panels[i].ability_radial = data
end
'''

LOCAL_SOURCE_TOPOLOGY = r'''
local function hook_present(method)
    for _, e in ipairs(Hooks._all) do
        if e.kind == "post" and e.method == method then return true end
    end
    return false
end

local function effects(snap)
    return snap and snap.health_effects or nil
end

local function delayed(snap)
    local ef = effects(snap)
    return ef and ef.delayed_damage or nil
end

local function stored(snap)
    local ef = effects(snap)
    return ef and ef.stored_health or nil
end
'''

LOCAL_SOURCE_SETUP = r'''
local damage = {
    _health = 100,
    _health_max = 100,
    _armor = 50,
    _armor_max = 50,
    _revives = 1,
    _remaining_delayed = 25,
    _stored_health_amount = 20,
    _max_stored_health_amount = 40,
    get_real_health = function(self) return self._health end,
    _max_health = function(self) return self._health_max end,
    get_real_armor = function(self) return self._armor end,
    _max_armor = function(self) return self._armor_max end,
    get_revives = function(self) return self._revives end,
    remaining_delayed_damage = function(self) return self._remaining_delayed end,
    armor_stored_health = function(self) return self._stored_health_amount end,
    max_armor_stored_health = function(self) return self._max_stored_health_amount end,
}
local unit = {
    _alive = true,
    character_damage = function(self) return damage end,
}
managers.player = managers.player or {}
managers.player.player_unit = function(self) return unit end

local mgr = managers.hud
mgr._teammate_panels[HUDManager.PLAYER_PANEL] = {
    _peer_id = nil,
    _ai = false,
}
'''

LOCAL_SOURCE_SETUP_WITH_REMOTE = LOCAL_SOURCE_SETUP + r'''
mgr._teammate_panels[1] = {
    _peer_id = 2,
    _ai = false,
}
'''

LOCAL_SOURCE_SETUP_EXPORTED = LOCAL_SOURCE_SETUP + r'''
-- Test-only exports so mutations and source replacement reach the real unit.
_KY_test_damage = damage
_KY_test_unit = unit
'''


class ActorsLocalDelayedDamageTests(unittest.TestCase):
    """Family 1 -- live local source, absolute publish, zero, detached snapshot."""

    def test_local_initial_absolute_publish_zero_and_detachment(self):
        lua, ok = _lua(setup=NATIVE_HEALTH_EFFECTS_FIXTURE + LOCAL_SOURCE_SETUP)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute(DISPATCH)
        lua.execute(LOCAL_SOURCE_TOPOLOGY + r'''
            local ACT = kyohud.hud.actors
            local mgr = managers.hud

            _has_delayed_hook = hook_present("set_teammate_delayed_damage")
            _has_stored_hook = hook_present("set_stored_health")
            _has_stored_max_hook = hook_present("set_stored_health_max")

            ACT:refresh(mgr)
            local snap0 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _effects_present = snap0 ~= nil and snap0.health_effects ~= nil
            local dd0 = delayed(snap0)
            local sh0 = stored(snap0)
            _initial_delayed_known = dd0 and dd0.known
            _initial_delayed_amount = dd0 and dd0.amount or nil
            _initial_stored_known = sh0 and sh0.known
            _initial_stored_ratio = sh0 and sh0.ratio or nil
            _initial_stored_max_ratio = sh0 and sh0.max_ratio or nil

            local function publish_delayed(amount)
                mgr:set_teammate_delayed_damage(HUDManager.PLAYER_PANEL, amount)
                _KY_dispatch("set_teammate_delayed_damage",
                    HUDManager.PLAYER_PANEL, amount)
                local dd = delayed(ACT:get_actor(HUDManager.PLAYER_PANEL))
                return dd and dd.amount or nil
            end

            _published_once = publish_delayed(7)
            _published_twice = publish_delayed(3)
            _published_repeated = publish_delayed(3)
            publish_delayed(0)
            local zero = delayed(ACT:get_actor(HUDManager.PLAYER_PANEL))
            _zero_known = zero and zero.known
            _zero_amount = zero and zero.amount or nil

            local mutation = ACT:get_actor(HUDManager.PLAYER_PANEL)
            local mut_dd = delayed(mutation)
            local mut_sh = stored(mutation)
            _mutation_available = mut_dd ~= nil and mut_sh ~= nil
            if _mutation_available then
                mut_dd.amount = 999
                mut_sh.ratio = 0.99
                mut_sh.max_ratio = 0.99
            end

            local reread = ACT:get_actor(HUDManager.PLAYER_PANEL)
            local reread_dd = delayed(reread)
            local reread_sh = stored(reread)
            _reread_delayed_amount = reread_dd and reread_dd.amount or nil
            _reread_stored_ratio = reread_sh and reread_sh.ratio or nil
            _reread_stored_max_ratio = reread_sh and reread_sh.max_ratio or nil
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._has_delayed_hook),
            "RED: actors must register PostHook HUDManager:set_teammate_delayed_damage")
        self.assertTrue(bool(g._has_stored_hook),
            "RED: actors must register PostHook HUDManager:set_stored_health")
        self.assertTrue(bool(g._has_stored_max_hook),
            "RED: actors must register PostHook HUDManager:set_stored_health_max")
        self.assertTrue(bool(g._effects_present),
            "RED: get_actor(PLAYER_PANEL) must expose health_effects")

        self.assertTrue(bool(g._initial_delayed_known),
            "RED: initial delayed_damage.known must come from remaining_delayed_damage()")
        self.assertIsNotNone(g._initial_delayed_amount,
            "RED: initial delayed_damage.amount must snapshot remaining_delayed_damage()")
        self.assertEqual(float(g._initial_delayed_amount), 25.0,
            "RED: initial delayed_damage.amount must be the raw remaining amount")
        self.assertTrue(bool(g._initial_stored_known),
            "RED: initial stored_health.known must come from armor stored health getters")
        self.assertAlmostEqual(float(g._initial_stored_ratio), 0.2, places=5,
            msg="RED: initial stored_health.ratio must be armor_stored_health()/_max_health()")
        self.assertAlmostEqual(float(g._initial_stored_max_ratio), 0.4, places=5,
            msg="RED: initial stored_health.max_ratio must be max_armor_stored_health()/_max_health()")

        self.assertEqual(float(g._published_once), 7.0,
            "RED: delayed damage callback must publish the absolute amount 7")
        self.assertEqual(float(g._published_twice), 3.0,
            "RED: delayed damage callback must publish the absolute amount 3, not accumulate")
        self.assertEqual(float(g._published_repeated), 3.0,
            "RED: repeated identical delayed damage must publish the absolute amount 3, not accumulate")
        self.assertTrue(bool(g._zero_known),
            "RED: delayed damage zero must remain a known value")
        self.assertEqual(float(g._zero_amount), 0.0,
            "RED: delayed damage zero must be preserved as amount 0")

        self.assertTrue(bool(g._mutation_available),
            "RED: health_effects nested tables must be exposed for detachment")
        self.assertEqual(float(g._reread_delayed_amount), 0.0,
            "RED: mutating returned health_effects must not change delayed_damage amount")
        self.assertAlmostEqual(float(g._reread_stored_ratio), 0.2, places=5,
            msg="RED: mutating returned health_effects must not change stored_health ratio")
        self.assertAlmostEqual(float(g._reread_stored_max_ratio), 0.4, places=5,
            msg="RED: mutating returned health_effects must not change stored_health max_ratio")


class ActorsStoredHealthCallbacksTests(unittest.TestCase):
    """Family 2 -- slotless stored ratios, zero, and remote delayed isolation."""

    def test_slotless_stored_ratios_zero_and_remote_delayed_isolation(self):
        lua, ok = _lua(
            setup=NATIVE_HEALTH_EFFECTS_FIXTURE + LOCAL_SOURCE_SETUP_WITH_REMOTE)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute(DISPATCH)
        lua.execute(LOCAL_SOURCE_TOPOLOGY + r'''
            local ACT = kyohud.hud.actors
            local mgr = managers.hud

            _has_stored_hook = hook_present("set_stored_health")
            _has_stored_max_hook = hook_present("set_stored_health_max")
            _has_delayed_hook = hook_present("set_teammate_delayed_damage")

            ACT:refresh(mgr)
            local snap0 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _effects_present = snap0 ~= nil and snap0.health_effects ~= nil

            mgr:set_stored_health(0.75)
            _KY_dispatch("set_stored_health", 0.75)
            mgr:set_stored_health_max(0.5)
            _KY_dispatch("set_stored_health_max", 0.5)

            local snap1 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            local sh1 = stored(snap1)
            _stored_known = sh1 and sh1.known
            _stored_ratio = sh1 and sh1.ratio or nil
            _stored_max_ratio = sh1 and sh1.max_ratio or nil

            mgr:set_stored_health(0)
            _KY_dispatch("set_stored_health", 0)
            local snap_zero = ACT:get_actor(HUDManager.PLAYER_PANEL)
            local sh_zero = stored(snap_zero)
            _zero_stored_known = sh_zero and sh_zero.known
            _zero_stored_ratio = sh_zero and sh_zero.ratio or nil
            _zero_stored_max_ratio = sh_zero and sh_zero.max_ratio or nil

            mgr:set_teammate_delayed_damage(1, 42)
            _KY_dispatch("set_teammate_delayed_damage", 1, 42)
            local snap_remote = ACT:get_actor(HUDManager.PLAYER_PANEL)
            local local_dd = delayed(snap_remote)
            _local_delayed_amount = local_dd and local_dd.amount or nil
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._has_stored_hook),
            "RED: actors must register PostHook HUDManager:set_stored_health")
        self.assertTrue(bool(g._has_stored_max_hook),
            "RED: actors must register PostHook HUDManager:set_stored_health_max")
        self.assertTrue(bool(g._has_delayed_hook),
            "RED: actors must register PostHook HUDManager:set_teammate_delayed_damage")
        self.assertTrue(bool(g._effects_present),
            "RED: get_actor(PLAYER_PANEL) must expose health_effects")

        self.assertTrue(bool(g._stored_known),
            "RED: stored_health.known must be true after slotless callbacks")
        self.assertAlmostEqual(float(g._stored_ratio), 0.75, places=5,
            msg="RED: set_stored_health(ratio) must update local stored_health.ratio")
        self.assertAlmostEqual(float(g._stored_max_ratio), 0.5, places=5,
            msg="RED: set_stored_health_max(ratio) must update local stored_health.max_ratio")

        self.assertTrue(bool(g._zero_stored_known),
            "RED: stored_health zero must remain known")
        self.assertEqual(float(g._zero_stored_ratio), 0.0,
            "RED: set_stored_health(0) must preserve ratio 0")
        self.assertAlmostEqual(float(g._zero_stored_max_ratio), 0.5, places=5,
            msg="RED: zero stored ratio must not clear the max ratio")

        self.assertIsNotNone(g._local_delayed_amount,
            "RED: local delayed_damage must remain available after a remote slot publish")
        self.assertEqual(float(g._local_delayed_amount), 25.0,
            "RED: remote set_teammate_delayed_damage(1, 42) must not become local delayed damage")


class ActorsHealthEffectsRefreshLifecycleTests(unittest.TestCase):
    """Refresh must re-resolve optional getters and absolute values each time."""

    def test_refresh_recovers_missing_getter_and_refreshes_absolute_effects(self):
        lua, ok = _lua(
            setup=NATIVE_HEALTH_EFFECTS_FIXTURE + LOCAL_SOURCE_SETUP_EXPORTED)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute(DISPATCH)
        lua.execute(LOCAL_SOURCE_TOPOLOGY + r'''
            local ACT = kyohud.hud.actors
            local mgr = managers.hud
            local cd = _KY_test_damage

            -- Initial valid capture: delayed 25 and stored 0.2/0.4.
            ACT:refresh(mgr)
            local snap0 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            local dd0 = delayed(snap0)
            local sh0 = stored(snap0)
            _initial_delayed_known = dd0 and dd0.known
            _initial_delayed_amount = dd0 and dd0.amount or nil
            _initial_stored_known = sh0 and sh0.known
            _initial_stored_ratio = sh0 and sh0.ratio or nil
            _initial_stored_max_ratio = sh0 and sh0.max_ratio or nil

            -- The optional delayed getter disappears on the same source.
            cd.remaining_delayed_damage = nil
            ACT:refresh(mgr)
            local snap_missing = ACT:get_actor(HUDManager.PLAYER_PANEL)
            local dd_missing = delayed(snap_missing)
            _missing_delayed_present = dd_missing ~= nil
            _missing_delayed_known = dd_missing and dd_missing.known
            _missing_delayed_amount = dd_missing and dd_missing.amount or nil

            -- The same source exposes the getter again with an absolute value.
            cd.remaining_delayed_damage = function(self)
                return 8
            end
            ACT:refresh(mgr)
            local snap_restored = ACT:get_actor(HUDManager.PLAYER_PANEL)
            local dd_restored = delayed(snap_restored)
            _restored_delayed_known = dd_restored and dd_restored.known
            _restored_delayed_amount = dd_restored and dd_restored.amount or nil

            -- Stored health must be re-read, not frozen at its seed value.
            cd._stored_health_amount = 10
            ACT:refresh(mgr)
            local snap_stored = ACT:get_actor(HUDManager.PLAYER_PANEL)
            local sh_stored = stored(snap_stored)
            _refreshed_stored_known = sh_stored and sh_stored.known
            _refreshed_stored_ratio = sh_stored and sh_stored.ratio or nil
            _refreshed_stored_max_ratio = sh_stored and sh_stored.max_ratio or nil

            local dd_before_nan = delayed(ACT:get_actor(HUDManager.PLAYER_PANEL))
            _pre_nan_delayed_amount = dd_before_nan and dd_before_nan.amount or nil

            -- Invalid event must clear the stale valid value.
            mgr:set_teammate_delayed_damage(HUDManager.PLAYER_PANEL, 0/0)
            _KY_dispatch("set_teammate_delayed_damage",
                HUDManager.PLAYER_PANEL, 0/0)
            local snap_nan = ACT:get_actor(HUDManager.PLAYER_PANEL)
            local dd_nan = delayed(snap_nan)
            _nan_delayed_present = dd_nan ~= nil
            _nan_delayed_known = dd_nan and dd_nan.known
            _nan_delayed_amount = dd_nan and dd_nan.amount or nil

            -- A real valid event recovers the absolute value.
            mgr:set_teammate_delayed_damage(HUDManager.PLAYER_PANEL, 5)
            _KY_dispatch("set_teammate_delayed_damage",
                HUDManager.PLAYER_PANEL, 5)
            local snap_event = ACT:get_actor(HUDManager.PLAYER_PANEL)
            local dd_event = delayed(snap_event)
            _event_delayed_known = dd_event and dd_event.known
            _event_delayed_amount = dd_event and dd_event.amount or nil

            -- Replace the damage source with a partial stored-health getter
            -- pair: known must stay false because max_ratio is absent.
            local replacement = {
                _health = 100,
                _health_max = 100,
                _armor = 50,
                _armor_max = 50,
                get_real_health = function(self) return self._health end,
                _max_health = function(self) return self._health_max end,
                get_real_armor = function(self) return self._armor end,
                _max_armor = function(self) return self._armor_max end,
                armor_stored_health = function(self) return 15 end,
            }
            _KY_test_unit.character_damage = function(self)
                return replacement
            end
            ACT:refresh(mgr)
            local snap_replaced = ACT:get_actor(HUDManager.PLAYER_PANEL)
            local sh_replaced = stored(snap_replaced)
            _replaced_stored_present = sh_replaced ~= nil
            _replaced_stored_known = sh_replaced and sh_replaced.known
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._initial_delayed_known),
            "precondition: initial delayed damage must be known")
        self.assertEqual(float(g._initial_delayed_amount), 25.0,
            "precondition: initial delayed damage must be the absolute 25")
        self.assertTrue(bool(g._initial_stored_known),
            "precondition: initial stored health must be known")
        self.assertAlmostEqual(float(g._initial_stored_ratio), 0.2, places=5,
            msg="precondition: initial stored ratio must be 0.2")
        self.assertAlmostEqual(float(g._initial_stored_max_ratio), 0.4, places=5,
            msg="precondition: initial stored max_ratio must be 0.4")

        self.assertTrue(bool(g._missing_delayed_present),
            "RED: refresh must expose delayed_damage even without a getter")
        self.assertFalse(bool(g._missing_delayed_known),
            "RED: refresh without remaining_delayed_damage must clear known")
        self.assertIsNone(g._missing_delayed_amount,
            "RED: refresh without remaining_delayed_damage must not keep stale 25")

        self.assertTrue(bool(g._restored_delayed_known),
            "RED: refresh must recover the getter on the same character_damage")
        self.assertEqual(float(g._restored_delayed_amount), 8.0,
            "RED: refresh must publish the recovered absolute amount 8")

        self.assertTrue(bool(g._refreshed_stored_known),
            "RED: refreshed stored health must remain known")
        self.assertAlmostEqual(float(g._refreshed_stored_ratio), 0.1, places=5,
            msg="RED: refresh must re-read stored amount 10 / max health 100")
        self.assertAlmostEqual(float(g._refreshed_stored_max_ratio), 0.4, places=5,
            msg="RED: refresh must preserve the absolute max ratio 0.4")

        self.assertEqual(float(g._pre_nan_delayed_amount), 8.0,
            "precondition: valid delayed amount must be 8 before the NaN event")
        self.assertTrue(bool(g._nan_delayed_present),
            "RED: non-finite delayed event must keep a delayed_damage entry")
        self.assertFalse(bool(g._nan_delayed_known),
            "RED: non-finite delayed event must clear known")
        self.assertNotEqual(g._nan_delayed_amount, 8.0,
            "RED: non-finite delayed event must not keep stale amount 8")

        self.assertTrue(bool(g._event_delayed_known),
            "RED: valid event after NaN must recover known=true")
        self.assertEqual(float(g._event_delayed_amount), 5.0,
            "RED: valid event after NaN must publish the absolute amount 5")

        self.assertTrue(bool(g._replaced_stored_present),
            "RED: replacement source must expose stored_health")
        self.assertFalse(bool(g._replaced_stored_known),
            "RED: partial stored getters must not report known=true without max_ratio")


class ActorsHealthEffectsBroadCallbacksTests(unittest.TestCase):
    """Family 3 -- absorption, info_meter and copr native-shaped callbacks.

    Phased single test: hook presence, nil-slot defaults, explicit/remote
    routing, detached nested snapshots, non-finite invalidation with recovery,
    and COPR enabled/ratio qualification (true needs finite ratio in (0, 1]).
    """

    def test_absorption_info_meter_copr_callbacks(self):
        lua, ok = _lua(
            setup=NATIVE_HEALTH_EFFECTS_FIXTURE
                + NATIVE_EFFECTS_RELAY_FIXTURE
                + LOCAL_SOURCE_SETUP_WITH_REMOTE)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute(DISPATCH)
        lua.execute(LOCAL_SOURCE_TOPOLOGY + r'''
            local ACT = kyohud.hud.actors
            local mgr = managers.hud
            local PP = HUDManager.PLAYER_PANEL

            local function absorption(snap)
                local ef = effects(snap)
                return ef and ef.absorption or nil
            end

            local function info_meter(snap)
                local ef = effects(snap)
                return ef and ef.info_meter or nil
            end

            local function copr(snap)
                local ef = effects(snap)
                return ef and ef.copr or nil
            end

            local function current_snapshot()
                return ACT:get_actor(PP)
            end

            local function publish_absorb(i, amount)
                mgr:set_absorb_active(i, amount)
                _KY_dispatch("set_absorb_active", i, amount)
            end

            local function publish_info(i, data)
                mgr:set_info_meter(i, data)
                _KY_dispatch("set_info_meter", i, data)
            end

            local function publish_copr(enabled, ratio)
                mgr:set_copr_indicator(enabled, ratio)
                _KY_dispatch("set_copr_indicator", enabled, ratio)
            end

            _has_absorb_hook = hook_present("set_absorb_active")
            _has_info_hook = hook_present("set_info_meter")
            _has_copr_hook = hook_present("set_copr_indicator")

            -- Phase 0: start from a valid local source.
            ACT:refresh(mgr)
            local s0 = current_snapshot()
            _effects_present = s0 ~= nil and s0.health_effects ~= nil

            -- Phase 1: absorption nil slot defaults local; explicit local wins;
            -- remote slot is ignored.
            publish_absorb(nil, 7)
            local a_nil = absorption(current_snapshot())
            _absorb_nil_known = a_nil ~= nil and a_nil.known == true
            _absorb_nil_amount = a_nil and a_nil.amount or nil

            publish_absorb(PP, 9)
            local a_local = absorption(current_snapshot())
            _absorb_local_amount = a_local and a_local.amount or nil

            publish_absorb(1, 42)
            local a_remote = absorption(current_snapshot())
            _absorb_remote_amount = a_remote and a_remote.amount or nil

            -- Phase 2: info meter nil slot defaults local and copies scalars.
            publish_info(nil, {current = 0.2, total = 0.8, max = 1})
            local im = info_meter(current_snapshot())
            _info_known = im ~= nil and im.known == true
            _info_current = im and im.current or nil
            _info_total = im and im.total or nil
            _info_max = im and im.max or nil

            -- Phase 3: COPR active true ratio 0.2, then explicit inactive false
            -- with nil ratio; boolean false must stay distinct from nil.
            publish_copr(true, 0.2)
            local c_on = copr(current_snapshot())
            _copr_on_known = c_on ~= nil and c_on.known == true
            _copr_on_active = c_on and c_on.active
            _copr_on_ratio = c_on and c_on.static_damage_ratio or nil

            publish_copr(false, nil)
            local c_off = copr(current_snapshot())
            _copr_off_known = c_off ~= nil and c_off.known == true
            _copr_off_active_is_false = c_off ~= nil and c_off.active == false
            _copr_off_active_is_present = c_off ~= nil and c_off.active ~= nil
            _copr_off_ratio_is_nil = c_off ~= nil
                and c_off.static_damage_ratio == nil

            -- Phase 4: returned nested tables are detached; mutate the returned
            -- snapshot then reread without refreshing.
            local mutation = current_snapshot()
            local mutation_available = mutation ~= nil
                and mutation.health_effects ~= nil
                and mutation.health_effects.absorption ~= nil
                and mutation.health_effects.info_meter ~= nil
                and mutation.health_effects.copr ~= nil
            _mutation_available = mutation_available == true
            if mutation_available then
                mutation.health_effects.absorption.amount = 999
                mutation.health_effects.info_meter.current = 0.99
                mutation.health_effects.copr.active = true
            end
            local reread = current_snapshot()
            local r_abs = absorption(reread)
            local r_info = info_meter(reread)
            local r_copr = copr(reread)
            _detach_absorb_amount = r_abs and r_abs.amount or nil
            _detach_info_current = r_info and r_info.current or nil
            _detach_copr_active_is_false = r_copr ~= nil
                and r_copr.active == false

            -- Phase 5: non-finite local values become unknown and clear stale
            -- data; remote invalid events leave the local snapshot untouched.
            publish_absorb(PP, 7)
            publish_info(PP, {current = 0.2, total = 0.8, max = 1})
            publish_copr(true, 0.2)

            publish_absorb(1, 0/0)
            publish_info(1, {current = 0/0, total = 0.8, max = 1})
            local after_remote = current_snapshot()
            local ar_abs = absorption(after_remote)
            local ar_info = info_meter(after_remote)
            _remote_invalid_absorb_amount = ar_abs and ar_abs.amount or nil
            _remote_invalid_info_current = ar_info and ar_info.current or nil

            publish_absorb(PP, 0/0)
            local bad_abs = absorption(current_snapshot())
            _local_invalid_absorb_known = bad_abs ~= nil
                and bad_abs.known == true
            _local_invalid_absorb_amount_cleared = bad_abs ~= nil
                and bad_abs.amount == nil

            publish_info(PP, {current = 0/0, total = 0.8, max = 1})
            local bad_info = info_meter(current_snapshot())
            _local_invalid_info_known = bad_info ~= nil
                and bad_info.known == true
            _local_invalid_info_cleared = bad_info ~= nil
                and bad_info.current == nil
                and bad_info.total == nil
                and bad_info.max == nil

            publish_absorb(PP, 4)
            publish_info(PP, {current = 0.5, total = 1, max = 2})
            local recovered = current_snapshot()
            local rec_abs = absorption(recovered)
            local rec_info = info_meter(recovered)
            _recovered_absorb_known = rec_abs ~= nil and rec_abs.known == true
            _recovered_absorb_amount = rec_abs and rec_abs.amount or nil
            _recovered_info_known = rec_info ~= nil
                and rec_info.known == true
            _recovered_info_current = rec_info and rec_info.current or nil
            _recovered_info_total = rec_info and rec_info.total or nil
            _recovered_info_max = rec_info and rec_info.max or nil

            -- Phase 6: COPR enabled=true requires a finite ratio in (0, 1];
            -- false is the sentinel for a nil ratio argument in the table.
            local invalid_ratios = {false, 0, -0.1, 1.1, 0/0, math.huge}
            local invalid_seen = 0
            local invalid_unknown = 0
            for _, raw_ratio in ipairs(invalid_ratios) do
                local ratio = raw_ratio
                if ratio == false then ratio = nil end
                publish_copr(true, ratio)
                local c_bad = copr(current_snapshot())
                invalid_seen = invalid_seen + 1
                if c_bad ~= nil and c_bad.known == false then
                    invalid_unknown = invalid_unknown + 1
                end
            end
            _copr_invalid_seen = invalid_seen
            _copr_invalid_unknown = invalid_unknown

            publish_copr(true, 0.5)
            local c_rec = copr(current_snapshot())
            _copr_recovered_known = c_rec ~= nil and c_rec.known == true
            _copr_recovered_active_is_true = c_rec ~= nil
                and c_rec.active == true
            _copr_recovered_ratio = c_rec and c_rec.static_damage_ratio or nil
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._has_absorb_hook),
            "RED: actors must register PostHook HUDManager:set_absorb_active")
        self.assertTrue(bool(g._has_info_hook),
            "RED: actors must register PostHook HUDManager:set_info_meter")
        self.assertTrue(bool(g._has_copr_hook),
            "RED: actors must register PostHook HUDManager:set_copr_indicator")
        self.assertTrue(bool(g._effects_present),
            "RED: get_actor(PLAYER_PANEL) must expose health_effects")

        self.assertTrue(bool(g._absorb_nil_known),
            "RED: nil absorb slot must default to PLAYER_PANEL and be known")
        self.assertEqual(float(g._absorb_nil_amount), 7.0,
            "RED: nil absorb slot must publish amount 7")
        self.assertEqual(float(g._absorb_local_amount), 9.0,
            "RED: explicit local absorb must publish amount 9")
        self.assertEqual(float(g._absorb_remote_amount), 9.0,
            "RED: remote absorb slot must be ignored")

        self.assertTrue(bool(g._info_known),
            "RED: nil info slot must default to PLAYER_PANEL and be known")
        self.assertAlmostEqual(float(g._info_current), 0.2, places=5,
            msg="RED: info_meter.current must copy 0.2")
        self.assertAlmostEqual(float(g._info_total), 0.8, places=5,
            msg="RED: info_meter.total must copy 0.8")
        self.assertAlmostEqual(float(g._info_max), 1.0, places=5,
            msg="RED: info_meter.max must copy 1")

        self.assertTrue(bool(g._copr_on_known),
            "RED: COPR enabled=true with ratio 0.2 must be known")
        self.assertTrue(bool(g._copr_on_active),
            "RED: COPR enabled=true must publish active=true")
        self.assertAlmostEqual(float(g._copr_on_ratio), 0.2, places=5,
            msg="RED: COPR must publish static_damage_ratio 0.2")
        self.assertTrue(bool(g._copr_off_known),
            "RED: COPR enabled=false must stay explicitly known")
        self.assertIs(g._copr_off_active_is_false, True,
            "RED: COPR enabled=false must publish active=false (not nil)")
        self.assertIs(g._copr_off_active_is_present, True,
            "RED: COPR active must be present and boolean false")
        self.assertIs(g._copr_off_ratio_is_nil, True,
            "RED: COPR inactive must preserve static_damage_ratio as nil")

        self.assertTrue(bool(g._mutation_available),
            "RED: absorption/info_meter/copr nested tables must be exposed")
        self.assertEqual(float(g._detach_absorb_amount), 9.0,
            "RED: mutating returned absorption must not change internal amount")
        self.assertAlmostEqual(float(g._detach_info_current), 0.2, places=5,
            msg="RED: mutating returned info_meter must not change internal current")
        self.assertIs(g._detach_copr_active_is_false, True,
            "RED: mutating returned copr must not change internal active")

        self.assertEqual(float(g._remote_invalid_absorb_amount), 7.0,
            "RED: remote non-finite absorb must not clear local absorption")
        self.assertAlmostEqual(float(g._remote_invalid_info_current), 0.2,
            places=5,
            msg="RED: remote non-finite info must not clear local info_meter")
        self.assertFalse(bool(g._local_invalid_absorb_known),
            "RED: non-finite local absorb must clear absorption.known")
        self.assertIs(g._local_invalid_absorb_amount_cleared, True,
            "RED: non-finite local absorb must clear stale absorption.amount")
        self.assertFalse(bool(g._local_invalid_info_known),
            "RED: non-finite local info must clear info_meter.known")
        self.assertIs(g._local_invalid_info_cleared, True,
            "RED: non-finite local info must clear stale info_meter values")

        self.assertTrue(bool(g._recovered_absorb_known),
            "RED: valid absorb event must recover absorption.known")
        self.assertEqual(float(g._recovered_absorb_amount), 4.0,
            "RED: valid absorb event must publish amount 4")
        self.assertTrue(bool(g._recovered_info_known),
            "RED: valid info event must recover info_meter.known")
        self.assertAlmostEqual(float(g._recovered_info_current), 0.5, places=5,
            msg="RED: recovered info_meter.current must be 0.5")
        self.assertAlmostEqual(float(g._recovered_info_total), 1.0, places=5,
            msg="RED: recovered info_meter.total must be 1")
        self.assertAlmostEqual(float(g._recovered_info_max), 2.0, places=5,
            msg="RED: recovered info_meter.max must be 2")

        self.assertEqual(int(g._copr_invalid_seen), 6,
            "precondition: six invalid COPR ratios must be exercised")
        self.assertEqual(int(g._copr_invalid_unknown), 6,
            "RED: enabled=true with nil/zero/negative/>1/NaN/inf ratio must be unknown")
        self.assertTrue(bool(g._copr_recovered_known),
            "RED: COPR enabled=true with ratio 0.5 must recover known")
        self.assertIs(g._copr_recovered_active_is_true, True,
            "RED: recovered COPR must publish active=true")
        self.assertAlmostEqual(float(g._copr_recovered_ratio), 0.5, places=5,
            msg="RED: recovered COPR ratio must be 0.5")


class ActorsHealthEffectsInitialSnapshotLifecycleTests(unittest.TestCase):
    """Initial native-source snapshot for absorption, info_meter and copr.

    Native HUD init sources (playermanager.lua:875-885 for the cocaine info
    meter and :6310-6312 for the COPR indicator) plus damage_absorption are
    read by ACT:refresh only. The test never writes production snapshots.
    Missing/erroring queries must not be inferred as confirmed inactivity.
    """

    def test_initial_snapshot_absorption_info_copr_lifecycle(self):
        lua, ok = _lua(setup=NATIVE_HEALTH_EFFECTS_FIXTURE
            + LOCAL_SOURCE_SETUP_EXPORTED)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute(LOCAL_SOURCE_TOPOLOGY + r'''
            local ACT = kyohud.hud.actors
            local mgr = managers.hud
            local PP = HUDManager.PLAYER_PANEL
            local unit = _KY_test_unit

            local function absorption(snap)
                local ef = effects(snap)
                return ef and ef.absorption or nil
            end

            local function info_meter(snap)
                local ef = effects(snap)
                return ef and ef.info_meter or nil
            end

            local function copr(snap)
                local ef = effects(snap)
                return ef and ef.copr or nil
            end

            local function current_snapshot()
                return ACT:get_actor(PP)
            end

            -- Native-shaped PlayerManager sources installed before refresh.
            local function install_native_pm(pm)
                pm.player_unit = function(self) return unit end
                pm.damage_absorption = function(self) return 6 end
                pm.has_category_upgrade = function(self, category, upgrade)
                    return category == "player"
                        and upgrade == "cocaine_stacking"
                end
                pm.get_local_cocaine_damage_absorption_ratio = function(self)
                    return 0.3
                end
                pm.get_local_cocaine_damage_absorption_max_ratio = function(self)
                    return 0.9
                end
                pm.has_activate_temporary_upgrade = function(self, category, upgrade)
                    return category == "temporary"
                        and upgrade == "copr_ability"
                end
                pm.upgrade_value = function(self, category, upgrade, default)
                    if category == "player"
                        and upgrade == "copr_static_damage_ratio" then
                        return 0.2
                    end
                    return default
                end
                return pm
            end

            install_native_pm(managers.player)
            ACT:refresh(mgr)
            local s0 = current_snapshot()
            local a0 = absorption(s0)
            local i0 = info_meter(s0)
            local c0 = copr(s0)
            _init_absorption_present = a0 ~= nil
            _init_absorption_known = a0 and a0.known
            _init_absorption_amount = a0 and a0.amount or nil
            _init_info_present = i0 ~= nil
            _init_info_known = i0 and i0.known
            _init_info_current = i0 and i0.current or nil
            _init_info_total = i0 and i0.total or nil
            _init_info_max = i0 and i0.max or nil
            _init_copr_present = c0 ~= nil
            _init_copr_known = c0 and c0.known
            _init_copr_active = c0 and c0.active
            _init_copr_ratio = c0 and c0.static_damage_ratio or nil

            -- Replace the whole manager with a new object that still returns
            -- the same live unit but exposes none of the native getters.
            local replacement_pm = {
                player_unit = function(self) return unit end,
            }
            managers.player = replacement_pm
            _replacement_same_unit =
                managers.player:player_unit() == unit
            ACT:refresh(mgr)
            local s1 = current_snapshot()
            local a1 = absorption(s1)
            local i1 = info_meter(s1)
            local c1 = copr(s1)
            _missing_absorption_present = a1 ~= nil
            _missing_absorption_known = a1 and a1.known
            _missing_absorption_amount = a1 and a1.amount
            _missing_info_present = i1 ~= nil
            _missing_info_known = i1 and i1.known
            _missing_info_current = i1 and i1.current
            _missing_info_total = i1 and i1.total
            _missing_info_max = i1 and i1.max
            _missing_copr_present = c1 ~= nil
            _missing_copr_known = c1 and c1.known
            _missing_copr_active = c1 and c1.active
            _missing_copr_ratio = c1 and c1.static_damage_ratio

            -- Present but erroring queries must stay unknown, not inactive.
            replacement_pm.damage_absorption = function(self)
                error("damage_absorption failed")
            end
            replacement_pm.has_category_upgrade = function(self)
                error("has_category_upgrade failed")
            end
            replacement_pm.has_activate_temporary_upgrade = function(self)
                error("has_activate_temporary_upgrade failed")
            end
            ACT:refresh(mgr)
            local s_err = current_snapshot()
            local a_err = absorption(s_err)
            local i_err = info_meter(s_err)
            local c_err = copr(s_err)
            _error_absorption_present = a_err ~= nil
            _error_absorption_known = a_err and a_err.known
            _error_absorption_amount = a_err and a_err.amount
            _error_info_present = i_err ~= nil
            _error_info_known = i_err and i_err.known
            _error_info_current = i_err and i_err.current
            _error_info_total = i_err and i_err.total
            _error_info_max = i_err and i_err.max
            _error_copr_present = c_err ~= nil
            _error_copr_known = c_err and c_err.known
            _error_copr_active = c_err and c_err.active
            _error_copr_ratio = c_err and c_err.static_damage_ratio

            -- Restore the native getters on that same manager and recover.
            install_native_pm(replacement_pm)
            ACT:refresh(mgr)
            local s2 = current_snapshot()
            local a2 = absorption(s2)
            local i2 = info_meter(s2)
            local c2 = copr(s2)
            _restored_absorption_known = a2 and a2.known
            _restored_absorption_amount = a2 and a2.amount or nil
            _restored_info_known = i2 and i2.known
            _restored_info_current = i2 and i2.current or nil
            _restored_info_total = i2 and i2.total or nil
            _restored_info_max = i2 and i2.max or nil
            _restored_copr_known = c2 and c2.known
            _restored_copr_active = c2 and c2.active
            _restored_copr_ratio = c2 and c2.static_damage_ratio or nil

            -- Confirmed absence is distinct from a missing query: the info
            -- meter is known but empty and COPR is known inactive.
            replacement_pm.has_category_upgrade = function(self, category, upgrade)
                return false
            end
            replacement_pm.has_activate_temporary_upgrade = function(self, category, upgrade)
                return false
            end
            ACT:refresh(mgr)
            local s3 = current_snapshot()
            local a3 = absorption(s3)
            local i3 = info_meter(s3)
            local c3 = copr(s3)
            _inactive_absorption_known = a3 and a3.known
            _inactive_absorption_amount = a3 and a3.amount or nil
            _inactive_info_known = i3 and i3.known
            _inactive_info_current = i3 and i3.current or nil
            _inactive_info_total = i3 and i3.total or nil
            _inactive_info_max = i3 and i3.max or nil
            _inactive_copr_known = c3 and c3.known
            _inactive_copr_active = c3 and c3.active
            _inactive_copr_ratio = c3 and c3.static_damage_ratio
        ''')
        g = lua.globals()

        self.assertIs(g._init_absorption_present, True,
            "RED: refresh must expose health_effects.absorption")
        self.assertIs(g._init_absorption_known, True,
            "RED: damage_absorption()=6 must make absorption known")
        self.assertEqual(float(g._init_absorption_amount), 6.0,
            "RED: initial absorption amount must be damage_absorption()=6")
        self.assertIs(g._init_info_present, True,
            "RED: refresh must expose health_effects.info_meter")
        self.assertIs(g._init_info_known, True,
            "RED: cocaine_stacking=true must make info_meter known")
        self.assertAlmostEqual(float(g._init_info_current), 0.3, places=5,
            msg="RED: info_meter.current must be the local cocaine ratio 0.3")
        self.assertAlmostEqual(float(g._init_info_total), 0.9, places=5,
            msg="RED: info_meter.total must be the local cocaine max ratio 0.9")
        self.assertAlmostEqual(float(g._init_info_max), 1.0, places=5,
            msg="RED: info_meter.max must be the native HUD max 1")
        self.assertIs(g._init_copr_present, True,
            "RED: refresh must expose health_effects.copr")
        self.assertIs(g._init_copr_known, True,
            "RED: active copr_ability must make copr known")
        self.assertIs(g._init_copr_active, True,
            "RED: initial COPR active must be true")
        self.assertAlmostEqual(float(g._init_copr_ratio), 0.2, places=5,
            msg="RED: initial COPR static_damage_ratio must be 0.2")

        self.assertIs(g._replacement_same_unit, True,
            "precondition: replacement manager must return the same live unit")
        self.assertIs(g._missing_absorption_present, True,
            "RED: missing absorption getter must still expose absorption")
        self.assertIs(g._missing_absorption_known, False,
            "RED: missing absorption getter must clear known")
        self.assertIsNone(g._missing_absorption_amount,
            "RED: missing absorption getter must not keep stale amount 6")
        self.assertIs(g._missing_info_present, True,
            "RED: missing cocaine getters must still expose info_meter")
        self.assertIs(g._missing_info_known, False,
            "RED: missing cocaine query must clear info_meter.known")
        self.assertIsNone(g._missing_info_current,
            "RED: missing cocaine query must not keep stale current 0.3")
        self.assertIsNone(g._missing_info_total,
            "RED: missing cocaine query must not keep stale total 0.9")
        self.assertIsNone(g._missing_info_max,
            "RED: missing cocaine query must not keep stale max 1")
        self.assertIs(g._missing_copr_present, True,
            "RED: missing COPR getters must still expose copr")
        self.assertIs(g._missing_copr_known, False,
            "RED: missing COPR query must clear copr.known")
        self.assertIsNone(g._missing_copr_active,
            "RED: missing COPR query must not keep stale active true")
        self.assertIsNone(g._missing_copr_ratio,
            "RED: missing COPR query must not keep stale ratio 0.2")

        self.assertIs(g._error_absorption_present, True,
            "RED: erroring absorption getter must still expose absorption")
        self.assertIs(g._error_absorption_known, False,
            "RED: erroring absorption getter must clear known")
        self.assertIsNone(g._error_absorption_amount,
            "RED: erroring absorption getter must not keep stale amount")
        self.assertIs(g._error_info_present, True,
            "RED: erroring cocaine query must still expose info_meter")
        self.assertIs(g._error_info_known, False,
            "RED: erroring cocaine query must not be inferred inactive")
        self.assertIsNone(g._error_info_current,
            "RED: erroring cocaine query must not publish current 0")
        self.assertIsNone(g._error_info_total,
            "RED: erroring cocaine query must not publish total 0")
        self.assertIsNone(g._error_info_max,
            "RED: erroring cocaine query must not publish max 1")
        self.assertIs(g._error_copr_present, True,
            "RED: erroring COPR query must still expose copr")
        self.assertIs(g._error_copr_known, False,
            "RED: erroring COPR query must not be inferred inactive")
        self.assertIsNone(g._error_copr_active,
            "RED: erroring COPR query must not publish active false")
        self.assertIsNone(g._error_copr_ratio,
            "RED: erroring COPR query must not publish a ratio")

        self.assertIs(g._restored_absorption_known, True,
            "RED: restored absorption getter must recover known")
        self.assertEqual(float(g._restored_absorption_amount), 6.0,
            "RED: restored absorption getter must recover amount 6")
        self.assertIs(g._restored_info_known, True,
            "RED: restored cocaine getters must recover info_meter.known")
        self.assertAlmostEqual(float(g._restored_info_current), 0.3, places=5,
            msg="RED: restored info_meter.current must recover 0.3")
        self.assertAlmostEqual(float(g._restored_info_total), 0.9, places=5,
            msg="RED: restored info_meter.total must recover 0.9")
        self.assertAlmostEqual(float(g._restored_info_max), 1.0, places=5,
            msg="RED: restored info_meter.max must recover 1")
        self.assertIs(g._restored_copr_known, True,
            "RED: restored COPR getters must recover copr.known")
        self.assertIs(g._restored_copr_active, True,
            "RED: restored COPR getters must recover active true")
        self.assertAlmostEqual(float(g._restored_copr_ratio), 0.2, places=5,
            msg="RED: restored COPR ratio must recover 0.2")

        self.assertIs(g._inactive_absorption_known, True,
            "RED: absorption must remain known when other queries are false")
        self.assertEqual(float(g._inactive_absorption_amount), 6.0,
            "RED: confirmed inactive queries must not alter absorption 6")
        self.assertIs(g._inactive_info_known, True,
            "RED: confirmed cocaine_stacking=false must be known inactive")
        self.assertEqual(float(g._inactive_info_current), 0.0,
            "RED: confirmed inactive info_meter.current must be 0")
        self.assertEqual(float(g._inactive_info_total), 0.0,
            "RED: confirmed inactive info_meter.total must be 0")
        self.assertEqual(float(g._inactive_info_max), 1.0,
            "RED: confirmed inactive info_meter.max must be 1")
        self.assertIs(g._inactive_copr_known, True,
            "RED: confirmed copr_ability=false must be known inactive")
        self.assertIs(g._inactive_copr_active, False,
            "RED: confirmed inactive COPR must publish active=false directly")
        self.assertIsNone(g._inactive_copr_ratio,
            "RED: confirmed inactive COPR must omit static_damage_ratio")


class ActorsHealthEffectsRadialCallbacksTests(unittest.TestCase):
    """Local custom/ability radial scalar channels.

    Native-shaped player aliases relay through explicit teammate-slot methods.
    One loop covers both channels: valid ratio, zero, remote isolation, source
    and snapshot detachment, invalid NaN/total=0, then valid-event recovery.
    No activate-timer clock and no revive capture in this pass.
    """

    def test_custom_and_ability_radial_event_channels(self):
        lua, ok = _lua(setup=NATIVE_HEALTH_EFFECTS_FIXTURE
            + NATIVE_RADIAL_FIXTURE
            + LOCAL_SOURCE_SETUP_EXPORTED)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute(DISPATCH)
        lua.execute(LOCAL_SOURCE_TOPOLOGY + r'''
            local ACT = kyohud.hud.actors
            local mgr = managers.hud
            local PP = HUDManager.PLAYER_PANEL

            local function radial(snap, channel)
                local ef = effects(snap)
                return ef and ef[channel] or nil
            end

            local function capture(channel)
                local r = radial(ACT:get_actor(PP), channel)
                return {
                    present = r ~= nil,
                    known = r and r.known,
                    current = r and r.current,
                    total = r and r.total,
                    ratio = r and r.ratio,
                }
            end

            local function publish(spec, slot, data)
                if slot == PP then
                    mgr[spec.alias](mgr, data)
                else
                    mgr[spec.method](mgr, slot, data)
                end
                _KY_dispatch(spec.method, slot, data)
            end

            local specs = {
                {
                    channel = "custom_radial",
                    alias = "set_player_custom_radial",
                    method = "set_teammate_custom_radial",
                },
                {
                    channel = "ability_radial",
                    alias = "set_player_ability_radial",
                    method = "set_teammate_ability_radial",
                },
            }

            _radial_hooks = {}
            for _, spec in ipairs(specs) do
                _radial_hooks[spec.channel] = hook_present(spec.method)
            end

            ACT:refresh(mgr)
            local initial = ACT:get_actor(PP)
            _effects_present = initial ~= nil and initial.health_effects ~= nil

            _radial_results = {}
            for _, spec in ipairs(specs) do
                local result = {}

                local data = {current = 3, total = 10}
                publish(spec, PP, data)
                result.valid = capture(spec.channel)

                data.current = 999
                data.total = 999
                result.source_detached = capture(spec.channel)

                local snapshot = ACT:get_actor(PP)
                local nested = radial(snapshot, spec.channel)
                if nested then
                    nested.current = 999
                    nested.total = 999
                    nested.ratio = 0.99
                end
                result.snapshot_detached = capture(spec.channel)

                publish(spec, PP, {current = 0, total = 10})
                result.zero = capture(spec.channel)

                publish(spec, 1, {current = 7, total = 10})
                result.remote = capture(spec.channel)

                publish(spec, PP, {current = 0/0, total = 10})
                result.nan = capture(spec.channel)

                publish(spec, PP, {current = 5, total = 0})
                result.total_zero = capture(spec.channel)

                publish(spec, PP, {current = 5, total = 10})
                result.recovered = capture(spec.channel)

                _radial_results[spec.channel] = result
            end
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._effects_present),
            "RED: get_actor(PLAYER_PANEL) must expose health_effects")

        channels = (
            ("custom_radial", "set_teammate_custom_radial"),
            ("ability_radial", "set_teammate_ability_radial"),
        )
        for channel, method in channels:
            self.assertTrue(bool(g._radial_hooks[channel]),
                "RED: actors must register PostHook HUDManager:%s" % method)

        results = g._radial_results or {}
        for channel, _method in channels:
            with self.subTest(channel=channel):
                result = results[channel]
                self.assertIsNotNone(result,
                    "RED: %s events must produce a radial snapshot" % channel)
                if result is None:
                    continue

                cases = (
                    ("valid", result.valid, True, 3.0, 10.0, 0.3),
                    ("source_detached", result.source_detached,
                        True, 3.0, 10.0, 0.3),
                    ("snapshot_detached", result.snapshot_detached,
                        True, 3.0, 10.0, 0.3),
                    ("zero", result.zero, True, 0.0, 10.0, 0.0),
                    ("remote_ignored", result.remote, True, 0.0, 10.0, 0.0),
                    ("nan", result.nan, False, None, None, None),
                    ("total_zero", result.total_zero, False, None, None, None),
                    ("recovered", result.recovered, True, 5.0, 10.0, 0.5),
                )
                for label, values, known, current, total, ratio in cases:
                    with self.subTest(channel=channel, case=label):
                        self.assertTrue(bool(values.present),
                            "RED: %s.%s channel must exist after its event"
                            % (channel, label))
                        self.assertIs(values.known, known,
                            "RED: %s.%s known=%s" % (channel, label, known))
                        for field, expected in (
                            ("current", current),
                            ("total", total),
                            ("ratio", ratio),
                        ):
                            actual = values[field]
                            if expected is None:
                                self.assertIsNone(actual,
                                    "RED: %s.%s.%s must be cleared"
                                    % (channel, label, field))
                            else:
                                self.assertIsNotNone(actual,
                                    "RED: %s.%s.%s must be published"
                                    % (channel, label, field))
                                self.assertAlmostEqual(
                                    float(actual), expected, places=5,
                                    msg="RED: %s.%s.%s expected %s"
                                    % (channel, label, field, expected))


if __name__ == "__main__":
    unittest.main()
