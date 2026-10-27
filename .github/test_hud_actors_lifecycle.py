"""LOT4a lifecycle -- hud/actors.lua: remove_teammate_panel, unit swap, init_finalize.

Three lifecycle regressions exercising real native dispatch and production
callbacks. No manual repair ticks, no conditional-pass, no fixture
implementations of production identity/reset logic.

1. HUDManager:remove_teammate_panel(id) marks panel vacant without replacing
   object; immediate get_actor(id)==nil; reuse same object with same peer_id
   and new health callback; old armor/condition absent.
2. Local unit swap between refreshes: unit A snapshot, swap to B, condition
   callback; immediate get_actor must not expose A HP/armor; subsequent
   refresh(B) retains B condition and new unit token/generation differs.
3. init_finalize registered callbacks: spy ACT:on_heist_start wrapping
   original count, invoke registered HUDManager init_finalize PostHooks once,
   assert count==1, combat sentinel unchanged; graphical rebuild must not
   increment reset count.
"""
from pathlib import Path
import unittest

from test_hud_actors import _lua  # noqa: E402  -- imported from sibling test module
from test_hud_player import _lua as _player_lua  # noqa: E402  -- full player graph

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

REMOVE_PANEL_FIXTURE = r'''
-- Native HUDManager:remove_teammate_panel fixture (minimal shape for testing).
-- Marks panel vacant (_peer_id=nil, _ai=false) without replacing the object.
function HUDManager:remove_teammate_panel(id)
    local panel = self._teammate_panels[id]
    if panel then
        panel._peer_id = nil
        panel._ai = false
    end
end
'''


class ActorsRemoveTeammatePanelTests(unittest.TestCase):
    """Lifecycle 1 -- remove_teammate_panel marks vacant without replacing object.

    After native remove and real PreHook/PostHook dispatch, get_actor(id)
    must be nil immediately (no repair tick). Reuse same object with same
    peer_id and new health callback; old armor/condition must be absent.
    """

    def test_remove_panel_marks_vacant_reuse_same_object(self):
        lua, ok = _lua(setup=REMOVE_PANEL_FIXTURE)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute(DISPATCH)
        lua.execute('''
            local mgr = managers.hud
            local id = 1
            mgr._teammate_panels[id] = {
                _peer_id = 2,
                _ai = false,
            }

            -- Seed health/armor/condition via real callbacks.
            local hp = {current = 80, total = 100}
            local ar = {current = 40, total = 50}
            mgr:set_teammate_health(id, hp)
            mgr:set_teammate_armor(id, ar)
            mgr:set_teammate_condition(id, "down", "Downed")
            _KY_dispatch("set_teammate_health", id, hp)
            _KY_dispatch("set_teammate_armor", id, ar)
            _KY_dispatch("set_teammate_condition", id, "down", "Downed")

            local before = kyohud.hud.actors:get_actor(id)
            _hp_before = before and before.health and before.health.current or nil
            _ar_before = before and before.armor and before.armor.current or nil
            _cond_before = before and before.condition_icon or nil

            -- Capture panel object identity before remove.
            local panel_obj_before = mgr._teammate_panels[id]

            -- Dispatch real PreHooks, native remove, PostHooks.
            for _, e in ipairs(Hooks._all) do
                if e.kind == "pre" and e.method == "remove_teammate_panel" then
                    e.fn(mgr, id)
                end
            end
            mgr:remove_teammate_panel(id)
            for _, e in ipairs(Hooks._all) do
                if e.kind == "post" and e.method == "remove_teammate_panel" then
                    e.fn(mgr, id)
                end
            end

            -- Immediate get_actor(id) must be nil (no repair tick).
            local after_remove = kyohud.hud.actors:get_actor(id)
            _actor_nil = (after_remove == nil)

            -- Panel object must be same (not replaced).
            local panel_obj_after = mgr._teammate_panels[id]
            _panel_same = (panel_obj_before == panel_obj_after)
            _peer_id_nil = (panel_obj_after._peer_id == nil)
            _ai_false = (panel_obj_after._ai == false)

            -- Reuse same object, same peer_id, new health callback.
            panel_obj_after._peer_id = 2
            local new_hp = {current = 25, total = 100}
            mgr:set_teammate_health(id, new_hp)
            _KY_dispatch("set_teammate_health", id, new_hp)

            local reused = kyohud.hud.actors:get_actor(id)
            _hp_reused = reused and reused.health and reused.health.current or nil
            _ar_reused = reused and reused.armor and reused.armor.current or nil
            _cond_reused = reused and reused.condition_icon or nil
        ''')
        g = lua.globals()
        self.assertEqual(float(g._hp_before), 80.0,
            "precondition: health must be seeded before remove")
        self.assertEqual(float(g._ar_before), 40.0,
            "precondition: armor must be seeded before remove")
        self.assertEqual(g._cond_before, "down",
            "precondition: condition must be seeded before remove")
        self.assertTrue(bool(g._actor_nil),
            "RED: get_actor(id) must be nil immediately after remove (no repair tick)")
        self.assertTrue(bool(g._panel_same),
            "RED: remove_teammate_panel must not replace panel object")
        self.assertTrue(bool(g._peer_id_nil),
            "RED: panel._peer_id must be nil after remove")
        self.assertTrue(bool(g._ai_false),
            "RED: panel._ai must be false after remove")
        self.assertEqual(float(g._hp_reused), 25.0,
            "RED: reused panel with same peer_id must accept new health")
        self.assertIsNone(g._ar_reused,
            "RED: reused panel must not expose old armor after remove")
        self.assertIsNone(g._cond_reused,
            "RED: reused panel must not expose old condition after remove")


class ActorsUnitSwapBetweenRefreshesTests(unittest.TestCase):
    """Lifecycle 2 -- local unit swap between refreshes.

    Unit A valid getters snapshot, swap to B between refreshes then condition
    callback; immediate get_actor must not expose A HP/armor; subsequent
    refresh(B) retains B condition and new unit token/generation differs.
    Exact getter names _max_health/_max_armor functions.
    """

    def test_unit_swap_clears_old_hp_armor_retains_new_condition(self):
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

        lua.execute(DISPATCH)
        lua.execute('''
            local ACT = kyohud.hud.actors
            local mgr = managers.hud

            -- First refresh with unit A.
            ACT:refresh(mgr)
            local snap_A = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _hp_A = snap_A and snap_A.health and snap_A.health.current or nil
            _ar_A = snap_A and snap_A.armor and snap_A.armor.current or nil
            _token_A = snap_A and snap_A.unit_id or nil
            _gen_A = snap_A and snap_A.generation or nil

            -- Swap to unit B between refreshes.
            local damage_B = {
                _health = 75,
                _health_max = 100,
                _armor = 30,
                _armor_max = 50,
                _revives = 2,
                get_real_health = function(self) return self._health end,
                _max_health = function(self) return self._health_max end,
                get_real_armor = function(self) return self._armor end,
                _max_armor = function(self) return self._armor_max end,
                get_revives = function(self) return self._revives end,
            }
            local unit_B = {
                _alive = true,
                _id = "B",
                character_damage = function(self) return damage_B end,
            }
            managers.player.player_unit = function(self) return unit_B end

            -- Seed condition callback before second refresh.
            mgr:set_teammate_condition(HUDManager.PLAYER_PANEL, "down", "Downed")
            _KY_dispatch("set_teammate_condition",
                HUDManager.PLAYER_PANEL, "down", "Downed")

            -- Immediate get_actor must not expose A HP/armor.
            local snap_immediate = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _hp_immediate = snap_immediate and snap_immediate.health and snap_immediate.health.current or nil
            _ar_immediate = snap_immediate and snap_immediate.armor and snap_immediate.armor.current or nil

            -- Second refresh with unit B.
            ACT:refresh(mgr)
            local snap_B = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _hp_B = snap_B and snap_B.health and snap_B.health.current or nil
            _ar_B = snap_B and snap_B.armor and snap_B.armor.current or nil
            _cond_B = snap_B and snap_B.condition_icon or nil
            _token_B = snap_B and snap_B.unit_id or nil
            _gen_B = snap_B and snap_B.generation or nil

            _token_differs = (_token_A ~= _token_B)
            _gen_differs = (_gen_A ~= _gen_B)
        ''')
        g = lua.globals()
        self.assertEqual(float(g._hp_A), 100.0,
            "precondition: unit A health must be 100")
        self.assertEqual(float(g._ar_A), 50.0,
            "precondition: unit A armor must be 50")
        self.assertIsNone(g._hp_immediate,
            "RED: immediate get_actor after unit swap must not expose old A HP")
        self.assertIsNone(g._ar_immediate,
            "RED: immediate get_actor after unit swap must not expose old A armor")
        self.assertEqual(float(g._hp_B), 75.0,
            "RED: refresh(B) must snapshot unit B health=75")
        self.assertEqual(float(g._ar_B), 30.0,
            "RED: refresh(B) must snapshot unit B armor=30")
        self.assertEqual(g._cond_B, "down",
            "RED: refresh(B) must retain condition seeded before refresh")
        self.assertIsNotNone(g._token_A,
            "precondition: unit A unit_id must not be nil")
        self.assertIsNotNone(g._gen_A,
            "precondition: unit A generation must not be nil")
        self.assertIsNotNone(g._token_B,
            "RED: refresh(B) unit_id must not be nil")
        self.assertIsNotNone(g._gen_B,
            "RED: refresh(B) generation must not be nil")
        self.assertTrue(bool(g._token_differs),
            "RED: unit token/generation must differ between A and B")
        self.assertTrue(bool(g._gen_differs),
            "RED: generation must differ between A and B")


class ActorsInitFinalizeCallbacksTests(unittest.TestCase):
    """Lifecycle 3 -- init_finalize registered callbacks count.

    Spy ACT:on_heist_start wrapping original count, invoke registered
    HUDManager init_finalize PostHooks once, assert count==1, combat
    sentinel unchanged; graphical rebuild must not increment reset count.
    Managers.hud._safe_script panel etc ready before chunks.
    """

    def test_init_finalize_posthooks_invoke_once(self):
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
            mgr._safe_script = {panel = _G.panel_double}

            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
        '''
        lua, ok = _player_lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/player.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute(DISPATCH)
        lua.execute('''
            local ACT = kyohud.hud.actors
            local RT = kyohud.hud.runtime
            local P = kyohud.hud.player
            if not ACT.on_heist_start then
                _on_heist_start_missing = true
                return
            end
            _on_heist_start_missing = false

            local mgr = managers.hud
            RT:refresh_settings(mgr)

            -- Spy ACT:on_heist_start wrapping original.
            local original_on_heist_start = ACT.on_heist_start
            local call_count = 0
            ACT.on_heist_start = function(self, mgr)
                call_count = call_count + 1
                return original_on_heist_start(self, mgr)
            end

            -- Combat sentinel unchanged.
            kyohud.killstreak = kyohud.killstreak or {}
            kyohud.killstreak.count = 99

            -- Invoke registered HUDManager init_finalize PostHooks once.
            for _, e in ipairs(Hooks._all) do
                if e.kind == "post" and e.method == "init_finalize" then
                    e.fn(managers.hud)
                end
            end

            _final_count = call_count
            _killstreak_count = kyohud.killstreak.count

            -- Root alive before graphical rebuild.
            _root_alive_before = P._root ~= nil and alive(P._root)
            _count_before_rebuild = call_count

            -- Graphical rebuild must not increment reset count.
            kyohud.hud.runtime:rebuild(managers.hud)

            _count_after_rebuild = call_count
            _root_alive_after = P._root ~= nil and alive(P._root)
        ''')
        g = lua.globals()
        if g._on_heist_start_missing:
            self.fail("RED: ACT:on_heist_start(manager) must exist")
            return
        self.assertEqual(float(g._final_count), 1.0,
            "RED: init_finalize PostHooks must invoke on_heist_start exactly once")
        self.assertEqual(float(g._killstreak_count), 99.0,
            "RED: combat sentinel must remain unchanged")
        self.assertTrue(bool(g._root_alive_before),
            "precondition: player root must be alive before rebuild")
        self.assertEqual(float(g._count_before_rebuild), 1.0,
            "precondition: call count must be 1 before rebuild")
        self.assertEqual(float(g._count_after_rebuild), 1.0,
            "RED: graphical rebuild (runtime:rebuild) must not increment reset count")
        self.assertTrue(bool(g._root_alive_after),
            "RED: player root must be alive after rebuild")


if __name__ == "__main__":
    unittest.main()
