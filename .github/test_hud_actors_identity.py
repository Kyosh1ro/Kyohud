"""LOT4a identity regressions -- hud/actors.lua: callback + refresh identity invariants.

Four bounded real-callback regressions exercising identity reconciliation
between manager/panel state and the actors registry. Each test uses real
callable PostHook callbacks registered by the production chunk; no manual
repair ticks, no conditional-pass.

1. Condition callback before first refresh(manager) with no local unit:
   must survive the refresh (same mgr). Current refresh clears on first
   manager because ACT._mgr starts nil, so manager ~= ACT._mgr on the
   very first call and wipes _reg.
2. Local unit disappears after a valid snapshot: refresh must clear old
   health/armor/condition. Uses mock callable getters _max_health /
   _max_armor.
3. Seeded remote health slot-1 callback, then mgr._teammate_panels[1]
   identity replaced (_peer_id=3 vs 2) and new health callback before
   next refresh: old armor/condition must be nil, new health correct.
   Requires event captures to reconcile manager/panel identity BEFORE
   capture using native fields _peer_id/_ai only.
4. Malformed new health callback data={} after a previously valid health
   must invalidate health (nil or valid=false), preserve armor.
"""
from pathlib import Path
import unittest

from test_hud_actors import _lua  # noqa: E402  -- imported from sibling test module

ROOT = Path(__file__).resolve().parents[1]

DISPATCH = r'''
-- Real callback dispatcher: after native runs, invoke every registered
-- PostHook fn for the given method with the supplied positional args.
local function _dispatch(method, ...)
    for _, e in ipairs(Hooks._all) do
        if e.method == method then
            e.fn(managers.hud, ...)
        end
    end
end
_KY_dispatch = _dispatch
'''


class ActorsConditionSurvivesFirstRefreshTests(unittest.TestCase):
    """Regression 1 -- condition seeded before first refresh must survive.

    ACT._mgr is nil at load. The first refresh(mgr) triggers the
    manager-changed branch (mgr ~= nil) which currently clears _reg,
    wiping the condition that was just captured by real callback.
    """

    def test_condition_before_first_refresh_survives_same_mgr(self):
        lua, ok = _lua()
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute(DISPATCH)
        lua.execute('''
            local mgr = managers.hud
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] =
                mgr._teammate_panels[HUDManager.PLAYER_PANEL] or {}

            -- Seed condition via real registered callback, no local unit.
            mgr:set_teammate_condition(HUDManager.PLAYER_PANEL, "down", "Downed")
            _KY_dispatch("set_teammate_condition",
                HUDManager.PLAYER_PANEL, "down", "Downed")

            local before = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _icon_before = before and before.condition_icon or nil
            _text_before = before and before.condition_text or nil

            -- First refresh with this manager; no local unit available.
            -- managers.player has no player_unit, so unit is nil.
            kyohud.hud.actors:refresh(mgr)

            local after = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _icon_after = after and after.condition_icon or nil
            _text_after = after and after.condition_text or nil
        ''')
        g = lua.globals()
        self.assertEqual(g._icon_before, "down",
            "precondition: condition must be seeded via real callback")
        self.assertEqual(g._text_before, "Downed",
            "precondition: condition text must be seeded via real callback")
        self.assertEqual(g._icon_after, "down",
            "RED: condition must survive first refresh(manager) with same mgr, "
            "no local unit; current refresh clears on first manager because "
            "ACT._mgr starts nil")
        self.assertEqual(g._text_after, "Downed",
            "RED: condition_text must survive first refresh(manager)")


class ActorsLocalUnitDisappearedClearsSnapshotTests(unittest.TestCase):
    """Regression 2 -- disappearing local unit must clear stale snapshot.

    After a valid refresh with a local unit, removing the unit and
    refreshing again must clear health/armor/condition rather than
    preserve stale values.
    """

    def test_local_unit_disappears_clears_health_armor_condition(self):
        setup = '''
            local damage = {
                _health = 80,
                _health_max = 100,
                _armor = 40,
                _armor_max = 50,
                _revives = 2,
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

        lua.execute(DISPATCH)
        lua.execute('''
            local ACT = kyohud.hud.actors
            local mgr = managers.hud

            -- First refresh: valid local snapshot.
            ACT:refresh(mgr)

            -- Seed condition via real callback after first refresh.
            mgr:set_teammate_condition(HUDManager.PLAYER_PANEL, "down", "Downed")
            _KY_dispatch("set_teammate_condition",
                HUDManager.PLAYER_PANEL, "down", "Downed")

            local snap1 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _hp1 = snap1 and snap1.health and snap1.health.current or nil
            _ar1 = snap1 and snap1.armor and snap1.armor.current or nil
            _cond1 = snap1 and snap1.condition_icon or nil

            -- Local unit disappears.
            managers.player.player_unit = function(self) return nil end

            -- Second refresh with same manager; unit is gone.
            ACT:refresh(mgr)

            local snap2 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _hp2 = snap2 and snap2.health and snap2.health.current or nil
            _ar2 = snap2 and snap2.armor and snap2.armor.current or nil
            _cond2 = snap2 and snap2.condition_icon or nil
        ''')
        g = lua.globals()
        self.assertEqual(float(g._hp1), 80.0,
            "precondition: first refresh must snapshot health=80")
        self.assertEqual(float(g._ar1), 40.0,
            "precondition: first refresh must snapshot armor=40")
        self.assertEqual(g._cond1, "down",
            "precondition: condition seeded after first refresh")
        self.assertIsNone(g._hp2,
            "RED: refresh with no local unit must clear stale health.current")
        self.assertIsNone(g._ar2,
            "RED: refresh with no local unit must clear stale armor.current")
        self.assertIsNone(g._cond2,
            "RED: refresh with no local unit must clear stale condition")


class ActorsRemotePanelIdentityReconcileTests(unittest.TestCase):
    """Regression 3 -- remote slot identity change via callback reconciliation.

    After seeding health at slot 1 (_peer_id=2), replacing the panel's
    identity (_peer_id=3) and firing a new health callback must clear
    old armor/condition and record the new health. Reconciliation must
    happen in the callback BEFORE capture, using native _peer_id/_ai only.
    """

    def test_remote_slot_identity_change_clears_old_armor_condition(self):
        setup = '''
            local mgr = managers.hud
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

        lua.execute(DISPATCH)
        lua.execute('''
            local mgr = managers.hud

            -- Seed remote health at slot 1 (peer_id=2).
            local hp1 = {current = 60, total = 80}
            mgr:set_teammate_health(1, hp1)
            _KY_dispatch("set_teammate_health", 1, hp1)

            -- Seed armor + condition on the same slot.
            local ar1 = {current = 20, total = 40}
            mgr:set_teammate_armor(1, ar1)
            _KY_dispatch("set_teammate_armor", 1, ar1)
            mgr:set_teammate_condition(1, "down", "Downed")
            _KY_dispatch("set_teammate_condition", 1, "down", "Downed")

            local snap_before = kyohud.hud.actors:get_actor(1)
            _hp_before = snap_before and snap_before.health
                and snap_before.health.current or nil
            _ar_before = snap_before and snap_before.armor
                and snap_before.armor.current or nil
            _cond_before = snap_before and snap_before.condition_icon or nil

            -- Replace panel identity: peer_id 2 -> 3.
            mgr._teammate_panels[1] = {
                _peer_id = 3,
                _ai = false,
            }

            -- New health callback on slot 1 with new identity.
            local hp2 = {current = 90, total = 100}
            mgr:set_teammate_health(1, hp2)
            _KY_dispatch("set_teammate_health", 1, hp2)

            local snap_after = kyohud.hud.actors:get_actor(1)
            _hp_after = snap_after and snap_after.health
                and snap_after.health.current or nil
            _ar_after = snap_after and snap_after.armor
                and snap_after.armor.current or nil
            _cond_after = snap_after and snap_after.condition_icon or nil
        ''')
        g = lua.globals()
        self.assertEqual(float(g._hp_before), 60.0,
            "precondition: seeded remote health=60 at peer_id=2")
        self.assertEqual(float(g._ar_before), 20.0,
            "precondition: seeded remote armor=20 at peer_id=2")
        self.assertEqual(g._cond_before, "down",
            "precondition: seeded condition at peer_id=2")
        self.assertEqual(float(g._hp_after), 90.0,
            "RED: new health must be captured for peer_id=3")
        self.assertIsNone(g._ar_after,
            "RED: old armor must be nil after panel identity change "
            "(peer_id 2 -> 3); callback must reconcile via _peer_id/_ai "
            "BEFORE capture")
        self.assertIsNone(g._cond_after,
            "RED: old condition must be nil after panel identity change; "
            "callback must reconcile via native fields only")


class ActorsMalformedHealthCallbackInvalidatesTests(unittest.TestCase):
    """Regression 4 -- malformed health callback invalidates, armor preserved.

    After a valid health capture, a callback with data={} must invalidate
    the health entry (nil or valid=false). Armor captured earlier must
    remain intact.
    """

    def test_malformed_health_callback_invalidates_health_preserves_armor(self):
        lua, ok = _lua()
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute(DISPATCH)
        lua.execute('''
            local mgr = managers.hud
            local slot = HUDManager.PLAYER_PANEL
            mgr._teammate_panels[slot] = mgr._teammate_panels[slot] or {}

            -- Seed valid health.
            local hp_valid = {current = 75, total = 100}
            mgr:set_teammate_health(slot, hp_valid)
            _KY_dispatch("set_teammate_health", slot, hp_valid)

            -- Seed valid armor on the same slot.
            local ar_valid = {current = 30, total = 50}
            mgr:set_teammate_armor(slot, ar_valid)
            _KY_dispatch("set_teammate_armor", slot, ar_valid)

            local snap_before = kyohud.hud.actors:get_actor(slot)
            _hp_before = snap_before and snap_before.health
                and snap_before.health.current or nil
            _ar_before = snap_before and snap_before.armor
                and snap_before.armor.current or nil

            -- Malformed health callback: data={} has no current/total.
            local hp_bad = {}
            mgr:set_teammate_health(slot, hp_bad)
            _KY_dispatch("set_teammate_health", slot, hp_bad)

            local snap_after = kyohud.hud.actors:get_actor(slot)
            _hp_after = snap_after and snap_after.health or nil
            _hp_cur_after = _hp_after and _hp_after.current or nil
            _hp_val_after = _hp_after and _hp_after.valid
            _ar_after = snap_after and snap_after.armor
                and snap_after.armor.current or nil
        ''')
        g = lua.globals()
        self.assertEqual(float(g._hp_before), 75.0,
            "precondition: valid health.current=75 captured")
        self.assertEqual(float(g._ar_before), 30.0,
            "precondition: valid armor.current=30 captured")
        hp_after = g._hp_after
        hp_cur_after = g._hp_cur_after
        hp_val_after = g._hp_val_after
        health_invalidated = (
            hp_after is None
            or hp_cur_after is None
            or (not bool(hp_val_after))
        )
        self.assertTrue(health_invalidated,
            "RED: malformed health callback data={} must invalidate health "
            "(nil or valid=false); current on_health returns early and "
            "preserves the previous valid entry")
        self.assertEqual(float(g._ar_after), 30.0,
            "RED: armor must be preserved across malformed health callback")


class ActorsSamePanelIdentityMutationTests(unittest.TestCase):
    """Regression 5 -- same panel object identity mutation clears stale metrics.

    A panel table at slot 1 has _peer_id mutated in-place from 2 to 3 (same
    reference). reconcile must detect the identity change via native _peer_id /
    _ai fields rather than reference equality, clearing old armor/condition
    before the new health capture. get_actor snapshot must expose identity
    metadata (peer_id, ai, slot, generation).
    """

    def test_same_panel_peer_id_mutation_clears_old_armor_condition(self):
        setup = '''
            local mgr = managers.hud
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

        lua.execute(DISPATCH)
        lua.execute('''
            local mgr = managers.hud

            -- Seed health + armor + condition at slot 1 (peer_id=2).
            local hp1 = {current = 60, total = 80}
            mgr:set_teammate_health(1, hp1)
            _KY_dispatch("set_teammate_health", 1, hp1)

            local ar1 = {current = 20, total = 40}
            mgr:set_teammate_armor(1, ar1)
            _KY_dispatch("set_teammate_armor", 1, ar1)

            mgr:set_teammate_condition(1, "down", "Downed")
            _KY_dispatch("set_teammate_condition", 1, "down", "Downed")

            local snap_before = kyohud.hud.actors:get_actor(1)
            _gen_before = snap_before and snap_before.generation or nil

            -- Mutate SAME panel object in-place: peer_id 2 -> 3.
            mgr._teammate_panels[1]._peer_id = 3

            -- New health callback fires under mutated identity.
            local hp2 = {current = 90, total = 100}
            mgr:set_teammate_health(1, hp2)
            _KY_dispatch("set_teammate_health", 1, hp2)

            local snap = kyohud.hud.actors:get_actor(1)
            _hp_after = snap and snap.health and snap.health.current or nil
            _ar_after = snap and snap.armor and snap.armor.current or nil
            _cond_after = snap and snap.condition_icon or nil
            _snap_peer = snap and snap.peer_id or nil
            _snap_ai = snap and snap.ai
            _snap_slot = snap and snap.slot or nil
            _snap_gen = snap and snap.generation or nil
            _gen_after = _snap_gen
        ''')
        g = lua.globals()
        self.assertEqual(float(g._hp_after), 90.0,
            "precondition: new health must be captured for peer_id=3")
        self.assertIsNone(g._ar_after,
            "RED: same-panel identity mutation (_peer_id 2->3 in-place) must clear "
            "old armor; reconcile currently uses reference equality and misses "
            "in-place identity changes")
        self.assertIsNone(g._cond_after,
            "RED: same-panel identity mutation must clear old condition; reconcile "
            "must compare native _peer_id/_ai fields, not just table reference")
        self.assertEqual(g._snap_peer, 3,
            "RED: snapshot must include peer_id=3 from mutated panel identity")
        self.assertEqual(g._snap_ai, False,
            "RED: snapshot must include ai=false from panel identity")
        slot_val = float(g._snap_slot) if g._snap_slot is not None else None
        self.assertEqual(slot_val, 1.0,
            "RED: snapshot must include slot=1")
        self.assertIsNotNone(g._snap_gen,
            "RED: snapshot must include a generation counter")
        self.assertIsNotNone(g._gen_before,
            "RED: pre-mutation snapshot must include generation")
        self.assertNotEqual(g._gen_before, g._gen_after,
            "RED: generation must change after panel identity mutation")


class ActorsConditionWithLocalUnitSurvivesRefreshAndReloadTests(unittest.TestCase):
    """Regression 6 -- condition seeded before first refresh with local unit.

    A condition callback fires before the first refresh while a local unit is
    already established. The condition must survive the same-unit refresh and
    a subsequent actors chunk reload. Actual health/armor getters must remain
    standard. The get_actor snapshot must include unit identity and generation
    but no raw reference to the source unit/damage tables.
    """

    def test_condition_before_first_refresh_with_local_unit_survives(self):
        setup = '''
            local damage = {
                _health = 80, _health_max = 100,
                _armor = 40, _armor_max = 50,
                _revives = 2,
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

        lua.execute(DISPATCH)

        # Seed condition BEFORE first refresh (local unit already established).
        lua.execute('''
            local mgr = managers.hud
            mgr:set_teammate_condition(HUDManager.PLAYER_PANEL, "down", "Downed")
            _KY_dispatch("set_teammate_condition",
                HUDManager.PLAYER_PANEL, "down", "Downed")

            local before = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _cond_before = before and before.condition_icon or nil
            _text_before = before and before.condition_text or nil

            -- First refresh with same local unit.
            kyohud.hud.actors:refresh(mgr)

            local after_refresh = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _cond_after_refresh = after_refresh
                and after_refresh.condition_icon or nil
            _text_after_refresh = after_refresh
                and after_refresh.condition_text or nil

            -- Standard getters still produce health/armor.
            _hp = after_refresh and after_refresh.health
                and after_refresh.health.current or nil
            _ar = after_refresh and after_refresh.armor
                and after_refresh.armor.current or nil

            -- Identity and generation fields.
            _uid = after_refresh and after_refresh.unit_id or nil
            _gen = after_refresh and after_refresh.generation or nil

            -- No raw reference source table in snapshot.
            _raw_ref_keys = {}
            if after_refresh then
                for k, v in pairs(after_refresh) do
                    if type(v) == "table" and k ~= "health" and k ~= "armor" then
                        table.insert(_raw_ref_keys, k)
                    end
                end
            end
            _raw_ref_count = #_raw_ref_keys
        ''')

        # Chunk reload: re-execute actors.lua source.
        actors_src = (ROOT / "lua" / "hud" / "actors.lua").read_text(
            encoding="utf-8-sig")
        lua.execute(actors_src)

        lua.execute('''
            local mgr = managers.hud
            kyohud.hud.actors:refresh(mgr)

            local after_reload = kyohud.hud.actors:get_actor(HUDManager.PLAYER_PANEL)
            _cond_after_reload = after_reload
                and after_reload.condition_icon or nil
            _text_after_reload = after_reload
                and after_reload.condition_text or nil
            _hp_after_reload = after_reload and after_reload.health
                and after_reload.health.current or nil
        ''')

        g = lua.globals()
        self.assertEqual(g._cond_before, "down",
            "precondition: condition seeded via real callback")
        self.assertEqual(g._text_before, "Downed",
            "precondition: condition text seeded via real callback")

        self.assertEqual(g._cond_after_refresh, "down",
            "RED: condition must survive first refresh when local unit is "
            "already established; current refresh clears via "
            "clear_slot_metrics when unit ~= ACT._local_unit (nil -> unit)")
        self.assertEqual(g._text_after_refresh, "Downed",
            "RED: condition_text must survive first refresh with local unit")

        self.assertEqual(float(g._hp), 80.0,
            "RED: health getter must remain standard after refresh")
        self.assertEqual(float(g._ar), 40.0,
            "RED: armor getter must remain standard after refresh")

        self.assertIsNotNone(g._uid,
            "RED: snapshot must include unit_id for identity tracking")
        self.assertIsNotNone(g._gen,
            "RED: snapshot must include generation counter")

        self.assertEqual(int(g._raw_ref_count), 0,
            "RED: snapshot must not expose raw references to source tables")

        self.assertEqual(g._cond_after_reload, "down",
            "RED: condition must survive chunk reload + refresh")
        self.assertEqual(g._text_after_reload, "Downed",
            "RED: condition_text must survive chunk reload + refresh")
        self.assertEqual(float(g._hp_after_reload), 80.0,
            "RED: health must survive chunk reload + refresh")


if __name__ == "__main__":
    unittest.main()
