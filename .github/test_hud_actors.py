"""LOT4a -- hud/actors.lua: scalar capture for health/armor snapshots (RED vertical tracer).

Scope: scalar capture, detachment, independent health/armor, zero/invalid ratios,
context gating and idempotence. No rendering, no crew, no weapons, no gauge,
no player panel composition, no occupant callbacks, no Diesel panels.

The native HUDManager set_teammate_health/set_teammate_armor fixture below is
extracted from Payday-2-LuaJIT-Complete-master/lib/managers/hudmanagerpd2.lua:317-358.
It is embedded so permanent tests do not require external G: files.

RED state: lua/hud/actors.lua does not exist yet. Tests that depend on
the production chunk must fail with an explicit message, not
FileNotFoundError.
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
ACTORS_PATH = ROOT / "lua" / "hud" / "actors.lua"

NATIVE_HEALTH_ARMOR_FIXTURE = r'''
-- Native HUDManager health/armor relay fixture (from hudmanagerpd2.lua:317-358).
-- set_player_health/set_player_armor delegate to set_teammate_health(i,data)
-- and set_teammate_armor(i,data). The native stores data by reference;
-- actors must copy only the scalars it needs.
--
-- HUDManager.PLAYER_PANEL identifies the local player panel slot.
HUDManager.PLAYER_PANEL = 4
HUDManager._teammate_panels = HUDManager._teammate_panels or {}

function HUDManager:set_teammate_health(i, data, dont_flash)
    -- Native stores data by reference (hudteammate.lua:1664-1667).
    -- The fixture preserves that shape for testing copy semantics.
    if not self._teammate_panels[i] then
        self._teammate_panels[i] = {}
    end
    self._teammate_panels[i].health_data = data
end

function HUDManager:set_teammate_armor(i, data, dont_flash)
    if not self._teammate_panels[i] then
        self._teammate_panels[i] = {}
    end
    self._teammate_panels[i].armor_data = data
end

function HUDManager:set_player_health(data, dont_flash)
    self:set_teammate_health(HUDManager.PLAYER_PANEL, data, dont_flash)
end

function HUDManager:set_player_armor(data, dont_flash)
    self:set_teammate_armor(HUDManager.PLAYER_PANEL, data, dont_flash)
end

-- Test helpers only; production must use its own captured state.
function HUDManager:_native_health_data(i)
    local tp = self._teammate_panels[i or HUDManager.PLAYER_PANEL]
    return tp and tp.health_data or nil
end

function HUDManager:_native_armor_data(i)
    local tp = self._teammate_panels[i or HUDManager.PLAYER_PANEL]
    return tp and tp.armor_data or nil
end
'''

NATIVE_REVIVES_CONDITION_FIXTURE = r'''
-- Native HUDManager revives/condition fixture (minimal shape for testing).
-- set_teammate_revives(i, amount) and set_teammate_condition(i, icon, text)
-- capture scalars for down state tracking.
function HUDManager:set_teammate_revives(i, amount)
    if not self._teammate_panels[i] then
        self._teammate_panels[i] = {}
    end
    self._teammate_panels[i].revives = amount
end

function HUDManager:set_teammate_condition(i, icon, text)
    if not self._teammate_panels[i] then
        self._teammate_panels[i] = {}
    end
    self._teammate_panels[i].condition_icon = icon
    self._teammate_panels[i].condition_text = text
end
'''

STUBS = '''
kyohud = kyohud or {}
Kyosh1roHUD = Kyosh1roHUD or kyohud
if Kyosh1roHUD ~= kyohud then Kyosh1roHUD = kyohud end
kyohud.settings = kyohud.settings or {}
if kyohud.settings.enable_hud_foundation == nil then
    kyohud.settings.enable_hud_foundation = false
end
if kyohud.settings.hud_scale == nil then
    kyohud.settings.hud_scale = 1.0
end
kyohud.hud = kyohud.hud or {}

if not math.round then
    function math.round(v) return math.floor(v + 0.5) end
end

Hooks = {_all = {}}
function Hooks:PostHook(class, method, id, fn)
    table.insert(self._all, {kind="post", class=class, method=method, id=id, fn=fn})
end
function Hooks:PreHook(class, method, id, fn)
    table.insert(self._all, {kind="pre", class=class, method=method, id=id, fn=fn})
end
function Hooks:Add(id, event, fn) end
function log(...) end
function alive(x) return x ~= nil and x._alive ~= false end
Color = setmetatable({}, {__call = function(...) return {} end})

HUDManager = {}
HUDManager.update = function() end
HUDManager.init_finalize = function() end
HUDManager._setup_player_info_hud_pd2 = function() end
HUDManager.resolution_changed = function() end
HUDManager.set_disabled = function() end
HUDManager.set_enabled = function() end
HUDManager.set_freeflight_disabled = function() end
HUDManager.set_freeflight_enabled = function() end
HUDManager.destroy = function() end
HUDManager.loot_value_updated = function() end

managers = managers or {}
managers.hud = setmetatable({_teammate_panels={}}, {__index=HUDManager})
PlayerBase = {
    PLAYER_INFO_HUD_PD2 = "player_info_hud_pd2",
    PLAYER_INFO_HUD_FULLSCREEN_PD2 = "player_info_hud_fullscreen_pd2",
}
RequiredScript = "lib/managers/hudmanagerpd2"

tweak_data = tweak_data or {}
tweak_data.hud = tweak_data.hud or {}
if tweak_data.hud.medium_font_noshadow == nil then
    tweak_data.hud.medium_font_noshadow = "fonts/font_medium_mf"
end
'''


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua(with_actors=True, context=None, setup=None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute(NATIVE_HEALTH_ARMOR_FIXTURE)
    lua.execute(NATIVE_REVIVES_CONDITION_FIXTURE)
    if context:
        lua.execute(f'RequiredScript = "{context}"')
    if setup:
        lua.execute(setup)
    actors_src = _read(ACTORS_PATH)
    actors_exists = actors_src is not None
    if with_actors and actors_src:
        lua.execute(actors_src)
    return lua, actors_exists


class ActorsScalarDetachmentTests(unittest.TestCase):
    """RED: health/armor scalars copied independently via registered callbacks.

    actors.lua must install PostHooks on HUDManager:set_teammate_health and
    set_teammate_armor. After native runs, the accepted scalars must be
    copied into kyohud.hud.actors internal state, not held by reference.
    """

    def test_scalar_detachment_health_and_armor(self):
        """After callbacks, mutating original data must not change captured scalars."""
        lua, ok = _lua()
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local mgr = _G.managers.hud
            local hp = {current = 80, total = 100}
            local ar = {current = 40, total = 50}
            mgr:set_teammate_health(HUDManager.PLAYER_PANEL, hp)
            mgr:set_teammate_armor(HUDManager.PLAYER_PANEL, ar)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, hp)
                end
                if e.method == "set_teammate_armor" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, ar)
                end
            end
            hp.current = 999
            hp.total = 999
            ar.current = 999
            ar.total = 999
            local snap = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _hp_cur = snap and snap.health and snap.health.current or nil
            _hp_tot = snap and snap.health and snap.health.total or nil
            _ar_cur = snap and snap.armor and snap.armor.current or nil
            _ar_tot = snap and snap.armor and snap.armor.total or nil
        ''')
        g = lua.globals()
        self.assertEqual(float(g._hp_cur), 80.0,
            "RED: captured health.current must be 80 (copied, not reference)")
        self.assertEqual(float(g._hp_tot), 100.0,
            "RED: captured health.total must be 100 (copied scalar)")
        self.assertEqual(float(g._ar_cur), 40.0,
            "RED: captured armor.current must be 40 (copied, not reference)")
        self.assertEqual(float(g._ar_tot), 50.0,
            "RED: captured armor.total must be 50 (copied scalar)")

    def test_independence_distinct_ratios(self):
        """Health and armor must maintain independent state with distinct ratios."""
        lua, ok = _lua()
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local mgr = _G.managers.hud
            local hp = {current = 80, total = 100}
            local ar = {current = 20, total = 50}
            mgr:set_teammate_health(HUDManager.PLAYER_PANEL, hp)
            mgr:set_teammate_armor(HUDManager.PLAYER_PANEL, ar)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, hp)
                end
                if e.method == "set_teammate_armor" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, ar)
                end
            end
            local snap = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _hp_rat = snap and snap.health and snap.health.ratio or nil
            _ar_rat = snap and snap.armor and snap.armor.ratio or nil
            _unknown = kyohud.hud.actors:get_actor(99)
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._hp_rat), 0.8, places=5,
            msg="RED: health.ratio = 80/100 = 0.8")
        self.assertAlmostEqual(float(g._ar_rat), 0.4, places=5,
            msg="RED: armor.ratio = 20/50 = 0.4")
        self.assertIsNone(g._unknown,
            "RED: get_actor on an untouched slot must return nil")


class ActorsZeroAndInvalidRatioTests(unittest.TestCase):
    """RED: zero is valid, total=0/non-finite invalidates ratio but preserves raw."""

    def test_zero_validity(self):
        """current=0, total=100: ratio=0, valid=true, zero is not unknown."""
        lua, ok = _lua()
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local mgr = _G.managers.hud
            local data = {current = 0, total = 100}
            mgr:set_teammate_health(HUDManager.PLAYER_PANEL, data)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, data)
                end
            end
            local snap = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _cur = snap.health.current
            _tot = snap.health.total
            _rat = snap.health.ratio
            _val = snap.health.valid
        ''')
        g = lua.globals()
        self.assertEqual(float(g._cur), 0.0,
            "RED: zero current must be captured as 0")
        self.assertEqual(float(g._tot), 100.0)
        self.assertAlmostEqual(float(g._rat), 0.0, places=5,
            msg="RED: 0/100 ratio must be 0")
        self.assertTrue(bool(g._val),
            "RED: zero current with valid total must be valid=true")

    def test_total_invalid_including_zero_nan_inf_and_current_nan_inf(self):
        """total=0/NaN/inf and current=NaN/inf: ratio invalid, raw preserved."""
        lua, ok = _lua()
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local mgr = _G.managers.hud

            local data1 = {current = 50, total = 0}
            mgr:set_teammate_health(HUDManager.PLAYER_PANEL, data1)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, data1)
                end
            end
            local snap1 = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _cur1 = snap1.health.current
            _tot1 = snap1.health.total
            _rat1 = snap1.health.ratio
            _val1 = snap1.health.valid

            local data2 = {current = 50, total = math.huge}
            mgr:set_teammate_health(HUDManager.PLAYER_PANEL, data2)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, data2)
                end
            end
            local snap2 = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _cur2 = snap2.health.current
            _tot2 = snap2.health.total
            _rat2 = snap2.health.ratio
            _val2 = snap2.health.valid

            local data3 = {current = 0/0, total = 100}
            mgr:set_teammate_health(HUDManager.PLAYER_PANEL, data3)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, data3)
                end
            end
            local snap3 = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _cur3 = snap3.health.current
            _rat3 = snap3.health.ratio
            _val3 = snap3.health.valid

            local data4 = {current = math.huge, total = 100}
            mgr:set_teammate_health(HUDManager.PLAYER_PANEL, data4)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, data4)
                end
            end
            local snap4 = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _cur4 = snap4.health.current
            _rat4 = snap4.health.ratio
            _val4 = snap4.health.valid

            local data5 = {current = 50, total = 0/0}
            mgr:set_teammate_health(HUDManager.PLAYER_PANEL, data5)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, data5)
                end
            end
            local snap5 = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _cur5 = snap5.health.current
            _tot5 = snap5.health.total
            _rat5 = snap5.health.ratio
            _val5 = snap5.health.valid
        ''')
        g = lua.globals()
        self.assertEqual(float(g._cur1), 50.0,
            "RED: raw current preserved when total=0")
        self.assertEqual(float(g._tot1), 0.0,
            "RED: raw total preserved as 0")
        self.assertIsNone(g._rat1,
            "RED: total=0 must invalidate ratio (nil)")
        self.assertFalse(bool(g._val1),
            "RED: total=0 must mark valid=false")

        self.assertEqual(float(g._cur2), 50.0,
            "RED: raw current preserved when total=inf")
        self.assertEqual(float(g._tot2), float('inf'),
            "RED: raw total preserved as inf")
        self.assertIsNone(g._rat2,
            "RED: total=inf must invalidate ratio (nil)")
        self.assertFalse(bool(g._val2),
            "RED: total=inf must mark valid=false")

        self.assertTrue(str(g._cur3) == 'nan' or g._cur3 != g._cur3,
            "RED: NaN current preserved as NaN")
        self.assertIsNone(g._rat3,
            "RED: current=NaN must invalidate ratio (nil)")
        self.assertFalse(bool(g._val3),
            "RED: current=NaN must mark valid=false")

        self.assertEqual(float(g._cur4), float('inf'),
            "RED: inf current preserved as inf")
        self.assertIsNone(g._rat4,
            "RED: current=inf must invalidate ratio (nil)")
        self.assertFalse(bool(g._val4),
            "RED: current=inf must mark valid=false")

        self.assertEqual(float(g._cur5), 50.0,
            "RED: raw current preserved when total=NaN")
        self.assertTrue(str(g._tot5) == 'nan' or g._tot5 != g._tot5,
            "RED: total=NaN preserved as NaN")
        self.assertIsNone(g._rat5,
            "RED: total=NaN must invalidate ratio (nil)")
        self.assertFalse(bool(g._val5),
            "RED: total=NaN must mark valid=false")


class ActorsClampedRatioTests(unittest.TestCase):
    """RED: ratio clamped to [0,1] but raw current/total preserved."""

    def test_clamped_ratio_raw_retention(self):
        """current > total: ratio clamped to 1.0. current < 0: clamped to 0.0. Raw preserved."""
        lua, ok = _lua()
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return
        lua.execute('''
            local mgr = _G.managers.hud

            local over = {current = 200, total = 100}
            mgr:set_teammate_health(HUDManager.PLAYER_PANEL, over)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, over)
                end
            end
            local snap1 = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _rat_over = snap1.health.ratio
            _cur_over = snap1.health.current

            local neg = {current = -10, total = 100}
            mgr:set_teammate_health(HUDManager.PLAYER_PANEL, neg)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, neg)
                end
            end
            local snap2 = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _rat_neg = snap2.health.ratio
            _cur_neg = snap2.health.current
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._rat_over), 1.0, places=5,
            msg="RED: ratio clamped to 1.0 when current > total")
        self.assertEqual(float(g._cur_over), 200.0,
            "RED: raw current preserved even when ratio clamped")
        self.assertAlmostEqual(float(g._rat_neg), 0.0, places=5,
            msg="RED: ratio clamped to 0.0 when current < 0")
        self.assertEqual(float(g._cur_neg), -10.0,
            "RED: raw current preserved even when negative")


class ActorsContextAndIdempotenceTests(unittest.TestCase):
    """RED: actors hooks only install under correct RequiredScript, idempotent."""

    def test_context_and_idempotence(self):
        """Load actors with wrong RequiredScript: no health/armor hooks.
        Load with correct RequiredScript twice: hooks appear once, no duplicates."""
        lua, ok = _lua(with_actors=False)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        actors_src = _read(ACTORS_PATH)
        if not actors_src:
            self.fail("RED: lua/hud/actors.lua must exist (production chunk missing)")
            return

        lua.execute('RequiredScript = "lib/units/something_else"')
        lua.execute(actors_src)
        lua.execute('''
            _wrong_hooks = 0
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health"
                    or e.method == "set_teammate_armor" then
                    _wrong_hooks = _wrong_hooks + 1
                end
            end
        ''')
        self.assertEqual(lua.globals()._wrong_hooks, 0,
            "RED: wrong RequiredScript must not register actors health/armor hooks")

        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        lua.execute(actors_src)
        lua.execute(actors_src)
        lua.execute('''
            _actor_ids = {}
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health"
                    or e.method == "set_teammate_armor" then
                    table.insert(_actor_ids, e.id)
                end
            end
            _count = #_actor_ids
            _seen = {}
            _dupes = 0
            for _, id in ipairs(_actor_ids) do
                if _seen[id] then _dupes = _dupes + 1 end
                _seen[id] = true
            end
            _bad_class = 0
            for _, e in ipairs(Hooks._all) do
                if (e.method == "set_teammate_health"
                    or e.method == "set_teammate_armor")
                    and e.class ~= HUDManager then
                    _bad_class = _bad_class + 1
                end
            end
        ''')
        g = lua.globals()
        self.assertGreaterEqual(g._count, 2,
            "RED: must register at least 2 hooks")
        self.assertEqual(g._dupes, 0,
            "RED: no duplicate hooks after double load")
        self.assertEqual(g._bad_class, 0,
            "RED: actors health/armor hooks must target HUDManager only")


class ActorsRefreshLifecycleTests(unittest.TestCase):
    """ACT:refresh(manager) snapshot/reconcile and ACT:on_heist_start(manager).

    Tests local player unit polling via managers.player:player_unit(),
    character_damage() getters, downs calculation, unit identity change,
    callback capture for revives/condition, and heist start reset.
    """

    def test_refresh_snapshot_local_health_armor_revives_downs(self):
        """refresh(manager) snapshots local player health/armor/revives -> downs.

        Mock managers.player:player_unit() returning alive unit with character_damage().
        health=8, max_health=23, armor=2, max_armor=5, revives=3 -> downs=2.
        health.provenance=local, zero is valid.
        """
        setup = '''
            local damage = {
                _health = 8,
                _health_max = 23,
                _armor = 2,
                _armor_max = 5,
                _revives = 3,
                get_real_health = function(self) return self._health end,
                _max_health = function(self) return self._health_max end,
                get_real_armor = function(self) return self._armor end,
                _max_armor = function(self) return self._armor_max end,
                get_revives = function(self) return self._revives end,
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
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute('''
            local ACT = kyohud.hud.actors
            if not ACT.refresh then
                _refresh_missing = true
                return
            end
            _refresh_missing = false
            local mgr = managers.hud
            ACT:refresh(mgr)
            local snap = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _hp_cur = snap and snap.health and snap.health.current or nil
            _hp_tot = snap and snap.health and snap.health.total or nil
            _hp_prov = snap and snap.health and snap.health.provenance or nil
            _hp_val = snap and snap.health and snap.health.valid
            _ar_cur = snap and snap.armor and snap.armor.current or nil
            _ar_tot = snap and snap.armor and snap.armor.total or nil
            _downs = snap and snap.downs or nil
        ''')
        g = lua.globals()
        if g._refresh_missing:
            self.fail("RED: ACT:refresh(manager) must exist")
            return
        self.assertEqual(float(g._hp_cur), 8.0,
            "RED: refresh must snapshot health.current=8")
        self.assertEqual(float(g._hp_tot), 23.0,
            "RED: refresh must snapshot health.total=23")
        self.assertEqual(g._hp_prov, "local",
            "RED: health.provenance must be 'local'")
        self.assertTrue(bool(g._hp_val),
            "RED: zero current with valid total must be valid=true")
        self.assertEqual(float(g._ar_cur), 2.0,
            "RED: refresh must snapshot armor.current=2")
        self.assertEqual(float(g._ar_tot), 5.0,
            "RED: refresh must snapshot armor.total=5")
        self.assertEqual(float(g._downs), 2.0,
            "RED: revives=3 -> downs=2 (revives - 1)")

    def test_scalar_snapshot_detached_from_consumer_mutation(self):
        """Snapshot returned by get_actor must be detached from internal state.

        Mutating the returned snapshot must not affect subsequent get_actor calls.
        """
        setup = '''
            local damage = {
                _health = 50,
                _health_max = 100,
                _armor = 30,
                _armor_max = 50,
                _revives = 0,
                get_real_health = function(self) return self._health end,
                _max_health = function(self) return self._health_max end,
                get_real_armor = function(self) return self._armor end,
                _max_armor = function(self) return self._armor_max end,
                get_revives = function(self) return self._revives end,
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
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute('''
            local ACT = kyohud.hud.actors
            if not ACT.refresh then
                _refresh_missing = true
                return
            end
            _refresh_missing = false
            local mgr = managers.hud
            ACT:refresh(mgr)
            local snap1 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            snap1.health.current = 9999
            snap1.armor.current = 9999
            local snap2 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _hp_cur2 = snap2 and snap2.health and snap2.health.current or nil
            _ar_cur2 = snap2 and snap2.armor and snap2.armor.current or nil
        ''')
        g = lua.globals()
        if g._refresh_missing:
            self.fail("RED: ACT:refresh(manager) must exist")
            return
        self.assertEqual(float(g._hp_cur2), 50.0,
            "RED: mutating snapshot must not affect internal state (health)")
        self.assertEqual(float(g._ar_cur2), 30.0,
            "RED: mutating snapshot must not affect internal state (armor)")

    def test_unit_identity_change_invalidates_old_snapshot(self):
        """Changing player_unit() identity on refresh invalidates old data.

        Old condition/HP must be replaced; unavailable getters return 'unknown',
        not old data.
        """
        setup = '''
            local damage_A = {
                _health = 100,
                _health_max = 100,
                _armor = 50,
                _armor_max = 50,
                _revives = 0,
                get_real_health = function(self) return self._health end,
                _max_health = function(self) return self._health_max end,
                get_real_armor = function(self) return self._armor end,
                _max_armor = function(self) return self._armor_max end,
                get_revives = function(self) return self._revives end,
            }
            local unit_A = {
                _alive = true,
                _id = "A",
                character_damage = function(self) return damage_A end,
            }
            managers.player = managers.player or {}
            managers.player.player_unit = function(self) return unit_A end

            local mgr = managers.hud
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = {
                _peer_id = nil,
                _ai = false,
            }
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute('''
            local ACT = kyohud.hud.actors
            if not ACT.refresh then
                _refresh_missing = true
                return
            end
            _refresh_missing = false
            local mgr = managers.hud
            ACT:refresh(mgr)
            local snap1 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _hp1 = snap1 and snap1.health and snap1.health.current or nil

            -- Seed condition via real callback before unit swap
            mgr:set_teammate_condition(HUDManager.PLAYER_PANEL, "down", "Downed")
            mgr:set_teammate_revives(HUDManager.PLAYER_PANEL, 2)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_condition" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, "down", "Downed")
                end
                if e.method == "set_teammate_revives" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, 2)
                end
            end
            local snap_cond = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _cond_icon_before = snap_cond and snap_cond.condition_icon or nil
            _revives_before = snap_cond and snap_cond.revives or nil

            local damage_B = {
                _health = 25,
                _health_max = 100,
                _armor = 10,
                _armor_max = 50,
                get_real_health = function(self) return self._health end,
                _max_health = function(self) return self._health_max end,
                get_real_armor = function(self) return self._armor end,
                _max_armor = function(self) return self._armor_max end,
            }
            local unit_B = {
                _alive = true,
                _id = "B",
                character_damage = function(self) return damage_B end,
            }
            managers.player.player_unit = function(self) return unit_B end
            ACT:refresh(mgr)
            local snap2 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _hp2 = snap2 and snap2.health and snap2.health.current or nil
            _revives2 = snap2 and snap2.revives or nil
            _downs2 = snap2 and snap2.downs or nil
            _cond_icon_after = snap2 and snap2.condition_icon or nil
        ''')
        g = lua.globals()
        if g._refresh_missing:
            self.fail("RED: ACT:refresh(manager) must exist")
            return
        self.assertEqual(float(g._hp1), 100.0,
            "RED: first refresh must snapshot unit_A health=100")
        self.assertEqual(g._cond_icon_before, "down",
            "RED: condition must be seeded via callback before unit swap")
        self.assertEqual(float(g._revives_before), 2.0,
            "RED: revives must be seeded via callback before unit swap")
        self.assertEqual(float(g._hp2), 25.0,
            "RED: second refresh must snapshot unit_B health=25 (not old 100)")
        self.assertIsNone(g._cond_icon_after,
            "RED: old condition must be cleared after unit identity change")
        self.assertIsNone(g._revives2,
            "RED: revives must be nil after unit identity change (not old data)")
        self.assertIsNone(g._downs2,
            "RED: downs must be nil after unit identity change (not old data)")

    def test_revives_condition_callbacks_capture_scalars(self):
        """set_teammate_revives/set_teammate_condition callbacks capture scalars.

        Registered PostHooks must copy scalars into internal state.
        """
        lua, ok = _lua()
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute('''
            local mgr = managers.hud
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = mgr._teammate_panels[HUDManager.PLAYER_PANEL] or {}

            local has_revives_hook = false
            local has_condition_hook = false
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_revives" then has_revives_hook = true end
                if e.method == "set_teammate_condition" then has_condition_hook = true end
            end
            _hooks_missing = (not has_revives_hook or not has_condition_hook)
        ''')
        g = lua.globals()
        if g._hooks_missing:
            self.fail("RED: ACT must register PostHooks on set_teammate_revives and set_teammate_condition")
            return

        lua.execute('''
            local mgr = managers.hud
            mgr:set_teammate_revives(HUDManager.PLAYER_PANEL, 3)
            mgr:set_teammate_condition(HUDManager.PLAYER_PANEL, "down", "Downed")
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_revives" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, 3)
                end
                if e.method == "set_teammate_condition" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, "down", "Downed")
                end
            end
            local snap = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _revives = snap and snap.revives or nil
            _cond_icon = snap and snap.condition_icon or nil
            _cond_text = snap and snap.condition_text or nil
        ''')
        g = lua.globals()
        self.assertEqual(float(g._revives), 3.0,
            "RED: set_teammate_revives callback must capture revives=3")
        self.assertEqual(g._cond_icon, "down",
            "RED: set_teammate_condition callback must capture icon='down'")
        self.assertEqual(g._cond_text, "Downed",
            "RED: set_teammate_condition callback must capture text='Downed'")

    def test_on_heist_start_resets_registry_without_killstreak(self):
        """on_heist_start(manager) resets registry including remote slots.

        Must not touch kyohud.killstreak sentinel.
        """
        setup = '''
            local damage = {
                _health = 50,
                _health_max = 100,
                _armor = 30,
                _armor_max = 50,
                _revives = 1,
                get_real_health = function(self) return self._health end,
                _max_health = function(self) return self._health_max end,
                get_real_armor = function(self) return self._armor end,
                _max_armor = function(self) return self._armor_max end,
                get_revives = function(self) return self._revives end,
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
            mgr._teammate_panels[1] = {
                _peer_id = 2,
                _ai = false,
            }
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute('''
            local ACT = kyohud.hud.actors
            if not ACT.on_heist_start then
                _on_heist_start_missing = true
                return
            end
            _on_heist_start_missing = false
            if not ACT.refresh then
                _refresh_missing = true
                return
            end
            _refresh_missing = false

            local mgr = managers.hud
            ACT:refresh(mgr)
            -- Seed remote health via real callback before reset
            local remote_hp = {current = 60, total = 80}
            mgr:set_teammate_health(1, remote_hp)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, 1, remote_hp)
                end
            end
            snap_before_local = ACT:get_actor(HUDManager.PLAYER_PANEL)
            snap_before_remote = ACT:get_actor(1)

            kyohud.killstreak = kyohud.killstreak or {}
            kyohud.killstreak.count = 99

            ACT:on_heist_start(mgr)

            snap_after_local = ACT:get_actor(HUDManager.PLAYER_PANEL)
            snap_after_remote = ACT:get_actor(1)
            _killstreak_count = kyohud.killstreak and kyohud.killstreak.count or nil
        ''')
        g = lua.globals()
        if g._on_heist_start_missing:
            self.fail("RED: ACT:on_heist_start(manager) must exist")
            return
        if g._refresh_missing:
            self.fail("RED: ACT:refresh(manager) must exist")
            return
        self.assertIsNotNone(g.snap_before_local,
            "RED: refresh must populate local slot before on_heist_start")
        self.assertIsNotNone(g.snap_before_remote,
            "RED: refresh must populate remote slot before on_heist_start")
        self.assertIsNone(g.snap_after_local,
            "RED: on_heist_start must clear local slot")
        self.assertIsNone(g.snap_after_remote,
            "RED: on_heist_start must clear remote slot")
        self.assertEqual(float(g._killstreak_count), 99.0,
            "RED: on_heist_start must not touch kyohud.killstreak sentinel")

    def test_manager_replacement_clears_remote_slots(self):
        """refresh(new_manager) must clear remote slots from previous manager.

        Seed remote health via callback, then refresh with a new native-shaped
        manager instance. Remote slot must be cleared. Local unit must preserve
        condition across refresh with same manager before swap.
        """
        setup = '''
            local damage = {
                _health = 50,
                _health_max = 100,
                _armor = 30,
                _armor_max = 50,
                _revives = 1,
                get_real_health = function(self) return self._health end,
                _max_health = function(self) return self._health_max end,
                get_real_armor = function(self) return self._armor end,
                _max_armor = function(self) return self._armor_max end,
                get_revives = function(self) return self._revives end,
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
            mgr._teammate_panels[1] = {
                _peer_id = 2,
                _ai = false,
            }
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute('''
            local ACT = kyohud.hud.actors
            if not ACT.refresh then
                _refresh_missing = true
                return
            end
            _refresh_missing = false

            local mgr = managers.hud
            ACT:refresh(mgr)

            -- Seed remote health via real callback
            local remote_hp = {current = 60, total = 80}
            mgr:set_teammate_health(1, remote_hp)
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_health" then
                    e.fn(mgr, 1, remote_hp)
                end
            end
            snap_before = ACT:get_actor(1)

            -- Seed local condition via callback
            mgr:set_teammate_condition(HUDManager.PLAYER_PANEL, "down", "Downed")
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_condition" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, "down", "Downed")
                end
            end
            local snap_local_before = ACT:get_actor(HUDManager.PLAYER_PANEL)
            cond_before = snap_local_before and snap_local_before.condition_icon or nil

            -- Refresh with same manager: local condition must be preserved
            ACT:refresh(mgr)
            local snap_local_preserved = ACT:get_actor(HUDManager.PLAYER_PANEL)
            cond_preserved = snap_local_preserved and snap_local_preserved.condition_icon or nil

            -- Create new native-shaped manager and refresh with it
            local new_mgr = setmetatable({_teammate_panels={}}, {__index=HUDManager})
            new_mgr._teammate_panels[HUDManager.PLAYER_PANEL] = {
                _peer_id = nil,
                _ai = false,
            }
            new_mgr._teammate_panels[1] = {
                _peer_id = 2,
                _ai = false,
            }
            ACT:refresh(new_mgr)
            snap_after_new_mgr = ACT:get_actor(1)
        ''')
        g = lua.globals()
        if g._refresh_missing:
            self.fail("RED: ACT:refresh(manager) must exist")
            return
        self.assertIsNotNone(g.snap_before,
            "RED: remote slot must be populated after seeding via callback")
        self.assertEqual(g.cond_before, "down",
            "RED: local condition must be seeded via callback")
        self.assertEqual(g.cond_preserved, "down",
            "RED: local condition must be preserved across refresh with same manager")
        self.assertIsNone(g.snap_after_new_mgr,
            "RED: refresh with new manager must clear remote slots from previous manager")


if __name__ == "__main__":
    unittest.main()
