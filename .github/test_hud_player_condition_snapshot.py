"""LOT4a condition snapshot regression -- hud/actors.lua: initial condition readback.

Diagnosis:
  - Native HUDTeammate:remove_panel() directly sets normal via
    set_condition("mugshot_normal"), hiding _condition_icon.
  - Native HUDTeammate:set_condition("mugshot_normal") (hudteammate.lua:2342)
    hides _condition_icon via set_visible(false).
  - Native _create_condition (hudteammate.lua:547-559) creates _condition_icon
    initially with visible=false.
  - HUDManager:set_teammate_condition (hudmanagerpd2.lua:510) delegates to
    panel:set_condition(icon_data, text), bypassing the actors PostHook when
    called directly by add_panel or other native paths.

  The actors module only captures condition via the PostHook on
  set_teammate_condition. When native calls set_condition("mugshot_normal")
  directly (bypassing the manager method), the hook never fires. The
  initial condition remains UNKNOWN because:
    1. No condition event has been captured yet.
    2. ACT:refresh() polls health/armor but NOT condition.

Authoritative source:
  The native _condition_icon visibility state on the HUDTeammate panel.
  visible=false => mugshot_normal (healthy).
  visible=true => abnormal condition (down, bleeding, etc.).

Fix intent:
  In ACT:refresh(), after polling health/armor, read the native panel's
  _condition_icon:visible() state. If a getter exists and returns false,
  set entry.condition_icon = "mugshot_normal" and entry.condition_text = "".
  If the getter throws or the icon is missing/throwing, leave condition
  unknown (do NOT invent mugshot_normal). If an explicit abnormal condition
  event was already captured, polling must NOT overwrite it.

This test file exercises the real Lua chunk via lupa.luajit21 using existing
fixture imports. It does NOT duplicate production logic; it validates the
contract.
"""
from pathlib import Path
import unittest

from test_hud_actors import _lua

ROOT = Path(__file__).resolve().parents[1]

DISPATCH = r'''
local function _dispatch(method, ...)
    for _, e in ipairs(Hooks._all) do
        if e.method == method then
            e.fn(managers.hud, ...)
        end
    end
end
_KY_dispatch = _dispatch
'''


class InitialConditionSnapshotTests(unittest.TestCase):
    """Initial healthy local actor: native condition icon hidden.

    Scenario: local player unit established, native HUDTeammate panel has
    _condition_icon with visible=false (mugshot_normal). No manager condition
    event has fired yet. ACT:refresh() must yield condition_icon="mugshot_normal"
    and empty condition_text, without any manager condition event.
    """

    def test_initial_healthy_local_actor_with_hidden_native_icon(self):
        setup = '''
            local damage = {
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
            local unit = {
                _alive = true,
                character_damage = function(self) return damage end,
            }
            managers.player = managers.player or {}
            managers.player.player_unit = function(self) return unit end

            local mgr = managers.hud
            local panel = {
                _peer_id = nil,
                _ai = false,
                _condition_icon = {
                    _visible = false,
                    visible = function(self) return self._visible end,
                },
            }
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = panel
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

            ACT:refresh(mgr)

            local snap = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _cond_icon = snap and snap.condition_icon or nil
            _cond_text = snap and snap.condition_text or nil
        ''')

        g = lua.globals()
        self.assertEqual(g._cond_icon, "mugshot_normal",
            "RED: initial healthy local actor with native _condition_icon "
            "visible=false must yield condition_icon='mugshot_normal' after "
            "ACT:refresh(); current refresh polls health/armor but NOT condition")
        self.assertEqual(g._cond_text, "",
            "RED: initial healthy local actor must yield empty condition_text")


class MissingOrThrowingNativeReadbackTests(unittest.TestCase):
    """Missing or throwing native readback: condition stays unknown.

    Scenario: local player unit established, but native _condition_icon is
    missing (nil) or its visible() getter throws an error. ACT:refresh() must
    NOT invent mugshot_normal; condition must remain unknown (nil).
    """

    def test_missing_native_icon_stays_unknown(self):
        setup = '''
            local damage = {
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
            local unit = {
                _alive = true,
                character_damage = function(self) return damage end,
            }
            managers.player = managers.player or {}
            managers.player.player_unit = function(self) return unit end

            local mgr = managers.hud
            local panel = {
                _peer_id = nil,
                _ai = false,
                _condition_icon = nil,
            }
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = panel
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

            ACT:refresh(mgr)

            local snap = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _cond_icon = snap and snap.condition_icon or nil
            _cond_text = snap and snap.condition_text or nil
        ''')

        g = lua.globals()
        self.assertIsNone(g._cond_icon,
            "RED: missing native _condition_icon must NOT invent mugshot_normal; "
            "condition must stay unknown (nil)")
        self.assertIsNone(g._cond_text,
            "RED: missing native _condition_icon must NOT invent empty text; "
            "condition_text must stay unknown (nil)")

    def test_throwing_native_icon_stays_unknown(self):
        setup = '''
            local damage = {
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
            local unit = {
                _alive = true,
                character_damage = function(self) return damage end,
            }
            managers.player = managers.player or {}
            managers.player.player_unit = function(self) return unit end

            local mgr = managers.hud
            local panel = {
                _peer_id = nil,
                _ai = false,
                _condition_icon = {
                    visible = function(self) error("native getter threw") end,
                },
            }
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = panel
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

            ACT:refresh(mgr)

            local snap = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _cond_icon = snap and snap.condition_icon or nil
            _cond_text = snap and snap.condition_text or nil
        ''')

        g = lua.globals()
        self.assertIsNone(g._cond_icon,
            "RED: throwing native _condition_icon visible() must NOT invent "
            "mugshot_normal; condition must stay unknown (nil)")
        self.assertIsNone(g._cond_text,
            "RED: throwing native _condition_icon visible() must NOT invent "
            "empty text; condition_text must stay unknown (nil)")


class ExplicitAbnormalConditionNotOverwrittenTests(unittest.TestCase):
    """Explicit abnormal condition event: polling must NOT overwrite.

    Scenario: explicit condition event (icon="down", text="Downed") captured
    via manager hook. Native _condition_icon is now visible=true. ACT:refresh()
    must preserve the captured abnormal condition, not overwrite it with
    mugshot_normal or empty.
    """

    def test_explicit_abnormal_condition_preserved_after_refresh(self):
        setup = '''
            local damage = {
                _health = 50,
                _health_max = 100,
                _armor = 25,
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
            local panel = {
                _peer_id = nil,
                _ai = false,
                _condition_icon = {
                    _visible = true,
                    visible = function(self) return self._visible end,
                },
            }
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = panel
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

            mgr:set_teammate_condition(HUDManager.PLAYER_PANEL, "down", "Downed")
            _KY_dispatch("set_teammate_condition",
                HUDManager.PLAYER_PANEL, "down", "Downed")

            ACT:refresh(mgr)

            local snap = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _cond_icon = snap and snap.condition_icon or nil
            _cond_text = snap and snap.condition_text or nil
        ''')

        g = lua.globals()
        self.assertEqual(g._cond_icon, "down",
            "RED: explicit abnormal condition event must be preserved after "
            "ACT:refresh(); polling must NOT overwrite captured condition with "
            "mugshot_normal or empty")
        self.assertEqual(g._cond_text, "Downed",
            "RED: explicit abnormal condition text must be preserved after "
            "ACT:refresh()")


class NativeIconVisibilityLifecycleTests(unittest.TestCase):
    """Native icon visibility lifecycle: refresh infers normal/nil correctly.

    Scenario: 10-step lifecycle of native _condition_icon visibility mutations.
    refresh must infer mugshot_normal when visible=false and no explicit event;
    clear inference when visible=true or icon removed/throwing/non-boolean;
    preserve explicit abnormal condition even when native hidden.
    """

    def test_native_icon_visibility_lifecycle(self):
        setup = '''
            local damage = {
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
            local unit = {
                _alive = true,
                character_damage = function(self) return damage end,
            }
            managers.player = managers.player or {}
            managers.player.player_unit = function(self) return unit end

            local mgr = managers.hud
            local icon = {
                _alive = true,
                _visible = false,
                visible = function(self) return self._visible end,
            }
            local panel = {
                _peer_id = nil,
                _ai = false,
                _condition_icon = icon,
            }
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = panel
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
            local panel = mgr._teammate_panels[HUDManager.PLAYER_PANEL]
            local icon = panel._condition_icon

            -- Step 1: refresh with visible=false -> normal
            ACT:refresh(mgr)
            local snap1 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _step1_icon = snap1 and snap1.condition_icon or nil
            _step1_text = snap1 and snap1.condition_text or nil

            -- Step 2: mutate icon visible true -> refresh condition nil
            icon._visible = true
            ACT:refresh(mgr)
            local snap2 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _step2_icon = snap2 and snap2.condition_icon or nil
            _step2_text = snap2 and snap2.condition_text or nil

            -- Step 3: visible false -> normal
            icon._visible = false
            ACT:refresh(mgr)
            local snap3 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _step3_icon = snap3 and snap3.condition_icon or nil
            _step3_text = snap3 and snap3.condition_text or nil

            -- Step 4: remove icon -> refresh nil
            panel._condition_icon = nil
            ACT:refresh(mgr)
            local snap4 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _step4_icon = snap4 and snap4.condition_icon or nil
            _step4_text = snap4 and snap4.condition_text or nil

            -- Step 5: restore throwing getter -> nil
            panel._condition_icon = {
                visible = function(self) error("native getter threw") end,
            }
            ACT:refresh(mgr)
            local snap5 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _step5_icon = snap5 and snap5.condition_icon or nil
            _step5_text = snap5 and snap5.condition_text or nil

            -- Step 6: restore false -> normal
            panel._condition_icon = {
                _alive = true,
                _visible = false,
                visible = function(self) return self._visible end,
            }
            ACT:refresh(mgr)
            local snap6 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _step6_icon = snap6 and snap6.condition_icon or nil
            _step6_text = snap6 and snap6.condition_text or nil

            -- Step 7: mark icon _alive=false -> nil
            panel._condition_icon._alive = false
            ACT:refresh(mgr)
            local snap7 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _step7_icon = snap7 and snap7.condition_icon or nil
            _step7_text = snap7 and snap7.condition_text or nil

            -- Step 8: restore alive and visible getter returning nonboolean 0 -> nil
            panel._condition_icon = {
                _alive = true,
                _visible = 0,
                visible = function(self) return self._visible end,
            }
            ACT:refresh(mgr)
            local snap8 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _step8_icon = snap8 and snap8.condition_icon or nil
            _step8_text = snap8 and snap8.condition_text or nil

            -- Step 9: restore false -> normal
            panel._condition_icon._visible = false
            ACT:refresh(mgr)
            local snap9 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _step9_icon = snap9 and snap9.condition_icon or nil
            _step9_text = snap9 and snap9.condition_text or nil

            -- Step 10: dispatch explicit condition down Downed WHILE native hidden false,
            -- refresh must preserve down Downed
            mgr:set_teammate_condition(HUDManager.PLAYER_PANEL, "down", "Downed")
            _KY_dispatch("set_teammate_condition",
                HUDManager.PLAYER_PANEL, "down", "Downed")
            ACT:refresh(mgr)
            local snap10 = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _step10_icon = snap10 and snap10.condition_icon or nil
            _step10_text = snap10 and snap10.condition_text or nil
        ''')

        g = lua.globals()
        self.assertEqual(g._step1_icon, "mugshot_normal",
            "RED: step 1: visible=false must infer mugshot_normal")
        self.assertEqual(g._step1_text, "",
            "RED: step 1: visible=false must infer empty condition_text")

        self.assertIsNone(g._step2_icon,
            "RED: step 2: visible=true must clear inference (nil)")
        self.assertIsNone(g._step2_text,
            "RED: step 2: visible=true must clear inference (nil)")

        self.assertEqual(g._step3_icon, "mugshot_normal",
            "RED: step 3: visible=false must re-infer mugshot_normal")
        self.assertEqual(g._step3_text, "",
            "RED: step 3: visible=false must re-infer empty condition_text")

        self.assertIsNone(g._step4_icon,
            "RED: step 4: removed icon must yield nil")
        self.assertIsNone(g._step4_text,
            "RED: step 4: removed icon must yield nil")

        self.assertIsNone(g._step5_icon,
            "RED: step 5: throwing getter must yield nil")
        self.assertIsNone(g._step5_text,
            "RED: step 5: throwing getter must yield nil")

        self.assertEqual(g._step6_icon, "mugshot_normal",
            "RED: step 6: restored visible=false must infer mugshot_normal")
        self.assertEqual(g._step6_text, "",
            "RED: step 6: restored visible=false must infer empty condition_text")

        self.assertIsNone(g._step7_icon,
            "RED: step 7: _alive=false icon must yield nil")
        self.assertIsNone(g._step7_text,
            "RED: step 7: _alive=false icon must yield nil")

        self.assertIsNone(g._step8_icon,
            "RED: step 8: nonboolean visible (0) must yield nil")
        self.assertIsNone(g._step8_text,
            "RED: step 8: nonboolean visible (0) must yield nil")

        self.assertEqual(g._step9_icon, "mugshot_normal",
            "RED: step 9: restored visible=false must infer mugshot_normal")
        self.assertEqual(g._step9_text, "",
            "RED: step 9: restored visible=false must infer empty condition_text")

        self.assertEqual(g._step10_icon, "down",
            "RED: step 10: explicit condition must be preserved even when native hidden")
        self.assertEqual(g._step10_text, "Downed",
            "RED: step 10: explicit condition text must be preserved")


class PlayerResolveConditionStrTests(unittest.TestCase):
    """player.lua:_resolve_condition_str(snapshot) contract.

    Scenario: load real player.lua in same harness. Assert _resolve_condition_str
    returns empty string on initial normal (actors._local_unit set, condition_icon="mugshot_normal"),
    and UNKNOWN fallback on invalidated snapshot (actors._local_unit=nil).
    Localization may be absent; fallback is fine.
    """

    def test_resolve_condition_str_normal_and_unknown(self):
        setup = '''
            local damage = {
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
            local unit = {
                _alive = true,
                character_damage = function(self) return damage end,
            }
            managers.player = managers.player or {}
            managers.player.player_unit = function(self) return unit end

            local mgr = managers.hud
            local panel = {
                _peer_id = nil,
                _ai = false,
                _condition_icon = {
                    _alive = true,
                    _visible = false,
                    visible = function(self) return self._visible end,
                },
            }
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = panel
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        player_src = (ROOT / "lua" / "hud" / "player.lua").read_text(encoding="utf-8-sig")
        lua.execute(player_src)
        lua.execute(DISPATCH)
        lua.execute('''
            local ACT = kyohud.hud.actors
            local P = kyohud.hud.player
            local mgr = managers.hud

            ACT:refresh(mgr)
            local snap_normal = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _str_normal = P:_resolve_condition_str(snap_normal)

            ACT._local_unit = nil
            local snap_invalid = { condition_icon = "mugshot_normal", condition_text = "" }
            _str_unknown = P:_resolve_condition_str(snap_invalid)
        ''')

        g = lua.globals()
        self.assertEqual(g._str_normal, "",
            "RED: _resolve_condition_str must return empty on initial normal")
        self.assertEqual(g._str_unknown, "UNKNOWN",
            "RED: _resolve_condition_str must return UNKNOWN on invalidated snapshot")


if __name__ == "__main__":
    unittest.main()
