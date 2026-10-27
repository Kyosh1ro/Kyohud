"""LOT4a -- hud/player.lua: player panel lifecycle and rendering.

Scope: player panel composition with gauge component, downs tracking, condition
text, value mode switching (percentage/real), lifecycle coordination with runtime,
native visibility isolation, and render certification. No combat state, no crew,
no killstreak, no objective panels, no assault/alerts logic.

Interface under test:
  kyohud.hud.player singleton module (like mission/assault)
    P._root, P._gauge, P._downs_text, P._condition_text
    P:mount(manager)
    P:refresh_settings(manager)
    P:update(manager, t, dt)
    P:unmount()
    P:rebuild(manager)
    P:render(actor_snapshot, multiplier)
    P:verify()

Settings:
  kyohud.settings.enable_player = false (opt-in, disabled by default)
  kyohud.settings.player_value_mode = 1 (percentage) or 2 (real)
  tweak_data.gui.stats_present_multiplier = 10 (native multiplier)

RequiredScript: "lib/managers/hudmanagerpd2"

RED: lua/hud/player.lua does not exist yet. Tests that need it
fail with assertTrue(path.exists()), not FileNotFoundError.
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

from test_hud_gauge import STUBS as GAUGE_STUBS
from test_hud_actors import NATIVE_HEALTH_ARMOR_FIXTURE, NATIVE_REVIVES_CONDITION_FIXTURE

ROOT = Path(__file__).resolve().parents[1]
PLAYER_PATH = ROOT / "lua" / "hud" / "player.lua"
GAUGE_PATH = ROOT / "lua" / "hud" / "components" / "gauge.lua"
LAYOUT_PATH = ROOT / "lua" / "hud" / "layout.lua"
NATIVE_VIS_PATH = ROOT / "lua" / "hud" / "native_visibility.lua"
RUNTIME_PATH = ROOT / "lua" / "hud" / "runtime.lua"
ACTORS_PATH = ROOT / "lua" / "hud" / "actors.lua"

STUBS = GAUGE_STUBS + '''
kyohud.settings = kyohud.settings or {}
if kyohud.settings.enable_hud_foundation == nil then
    kyohud.settings.enable_hud_foundation = false
end
if kyohud.settings.enable_player == nil then
    kyohud.settings.enable_player = false
end
if kyohud.settings.player_value_mode == nil then
    kyohud.settings.player_value_mode = 1
end
if kyohud.settings.hud_scale == nil then
    kyohud.settings.hud_scale = 1.0
end

HUDManager = HUDManager or {}
HUDManager.PLAYER_PANEL = 4
HUDManager._teammate_panels = HUDManager._teammate_panels or {}
HUDManager.update = function() end
HUDManager.init_finalize = function() end
HUDManager._setup_player_info_hud_pd2 = function() end
HUDManager.resolution_changed = function() end
HUDManager.set_disabled = function() end
HUDManager.set_enabled = function() end
HUDManager.set_freeflight_disabled = function() end
HUDManager.set_freeflight_enabled = function() end
HUDManager.destroy = function() end

managers = managers or {}
managers.hud = setmetatable({_teammate_panels={}}, {__index=HUDManager})

function managers.hud:script(name)
    if not self._safe_script then return nil end
    return self._safe_script
end
function managers.hud:disabled()
    return false
end

PlayerBase = {
    PLAYER_INFO_HUD_PD2 = "player_info_hud_pd2",
    PLAYER_INFO_HUD_FULLSCREEN_PD2 = "player_info_hud_fullscreen_pd2",
}
RequiredScript = "lib/managers/hudmanagerpd2"

tweak_data = tweak_data or {}
tweak_data.gui = tweak_data.gui or {}
tweak_data.gui.stats_present_multiplier = 10

panel_double:set_shape(0, 0, 1920, 1080)

Hooks = {_all = {}}
function Hooks:PostHook(class, method, id, fn)
    table.insert(self._all, {kind="post", class=class, method=method, id=id, fn=fn})
end
function Hooks:PreHook(class, method, id, fn)
    table.insert(self._all, {kind="pre", class=class, method=method, id=id, fn=fn})
end
function Hooks:Add(id, event, fn) end
function log(...) end
'''


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua(setup=None):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute(NATIVE_HEALTH_ARMOR_FIXTURE)
    lua.execute(NATIVE_REVIVES_CONDITION_FIXTURE)
    if setup:
        lua.execute(setup)
    lua.execute(_read(LAYOUT_PATH))
    lua.execute(_read(NATIVE_VIS_PATH))
    lua.execute(_read(RUNTIME_PATH))
    lua.execute(_read(ACTORS_PATH))
    gauge_src = _read(GAUGE_PATH)
    if gauge_src:
        lua.execute(gauge_src)
    player_src = _read(PLAYER_PATH)
    player_exists = player_src is not None
    if player_src:
        lua.execute(player_src)
    return lua, player_exists


class PlayerFileExistsTests(unittest.TestCase):
    def test_player_chunk_exists(self):
        self.assertTrue(PLAYER_PATH.is_file(),
            "RED: lua/hud/player.lua must exist")


class PlayerLifecycleAndNativeIsolationTests(unittest.TestCase):
    def test_opt_in_foundation_vr_native_sentinel(self):
        """enable_player=false does nothing. enable_player=true without foundation does nothing.
        enable_player=true with IS_VR=true does nothing. enable_player=true with foundation mounts under RT._root_panel.
        native_sentinel sibling remains same visible/geometry."""
        setup = '''
            local parent = _G.panel_double
            local sentinel = parent:panel({name="native_sentinel"})
            sentinel:set_shape(100, 100, 200, 50)
            sentinel:set_visible(true)
            _sentinel_x_before = sentinel:x()
            _sentinel_y_before = sentinel:y()
            _sentinel_w_before = sentinel:w()
            _sentinel_h_before = sentinel:h()
            _sentinel_vis_before = sentinel:visible()

            local damage = {
                _health = 50, _health_max = 100, _armor = 25, _armor_max = 50, _revives = 1,
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
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = {_peer_id = nil, _ai = false}
            mgr._safe_script = {panel = parent}
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/player.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local P = kyohud.hud.player

            kyohud.settings.enable_player = false
            kyohud.settings.enable_hud_foundation = true
            local mgr = _G.managers.hud
            kyohud.hud.runtime:refresh_settings(mgr)
            _disabled_no_root = P._root

            kyohud.settings.enable_player = true
            kyohud.settings.enable_hud_foundation = false
            kyohud.hud.runtime:refresh_settings(mgr)
            _no_foundation_no_root = P._root

            _G.IS_VR = true
            kyohud.settings.enable_player = true
            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:refresh_settings(mgr)
            _vr_no_root = P._root

            _G.IS_VR = false
            kyohud.hud.runtime:refresh_settings(mgr)
            _enabled_root = P._root
            _root_parent_is_rt = (P._root:parent() == kyohud.hud.runtime._root_panel)
            _sentinel_x_after = parent:child("native_sentinel"):x()
            _sentinel_y_after = parent:child("native_sentinel"):y()
            _sentinel_w_after = parent:child("native_sentinel"):w()
            _sentinel_h_after = parent:child("native_sentinel"):h()
            _sentinel_vis_after = parent:child("native_sentinel"):visible()
        ''')
        g = lua.globals()
        self.assertIsNone(g._disabled_no_root,
            "enable_player=false must not mount player panel")
        self.assertIsNone(g._no_foundation_no_root,
            "enable_hud_foundation=false must not mount player panel")
        self.assertIsNone(g._vr_no_root,
            "IS_VR=true must not mount player panel")
        self.assertIsNotNone(g._enabled_root,
            "enable_player=true with foundation must mount player panel")
        self.assertTrue(bool(g._root_parent_is_rt),
            "player root parent must be RT._root_panel")
        self.assertEqual(float(g._sentinel_x_after), float(g._sentinel_x_before))
        self.assertEqual(float(g._sentinel_y_after), float(g._sentinel_y_before))
        self.assertEqual(float(g._sentinel_w_after), float(g._sentinel_w_before))
        self.assertEqual(float(g._sentinel_h_after), float(g._sentinel_h_before))
        self.assertEqual(bool(g._sentinel_vis_after), bool(g._sentinel_vis_before))


class PlayerSnapshotAndModeSwitchTests(unittest.TestCase):
    def test_snapshot_via_actors_refresh_and_mode_switch_identity(self):
        """Local h8/23 a2/5 revives3 renders 35%/40% in mode 1, 80/20 in mode 2 with SAME primitive identities via rawequal."""
        setup = '''
            local damage = {
                _health = 8, _health_max = 23, _armor = 2, _armor_max = 5, _revives = 3,
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
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = {_peer_id = nil, _ai = false}
            local parent = _G.panel_double
            mgr._safe_script = {panel = parent}
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/player.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            kyohud.settings.player_value_mode = 1
            local mgr = _G.managers.hud
            kyohud.hud.runtime:refresh_settings(mgr)

            local P = kyohud.hud.player
            local mult = tweak_data.gui.stats_present_multiplier

            _hp_text_mode1 = P._gauge.health_text:text()
            _ar_text_mode1 = P._gauge.armor_text:text()
            _downs_text_mode1 = P._downs_text:text()

            local old_root = P._root
            local old_gauge = P._gauge
            local old_hp = P._gauge.health_text
            local old_ar = P._gauge.armor_text

            kyohud.settings.player_value_mode = 2
            kyohud.hud.runtime:refresh_settings(mgr)

            _hp_text_mode2 = P._gauge.health_text:text()
            _ar_text_mode2 = P._gauge.armor_text:text()

            _same_root = rawequal(old_root, P._root)
            _same_gauge = rawequal(old_gauge, P._gauge)
            _same_hp_text = rawequal(old_hp, P._gauge.health_text)
            _same_ar_text = rawequal(old_ar, P._gauge.armor_text)
        ''')
        g = lua.globals()
        self.assertEqual(g._hp_text_mode1, "35%",
            "mode 1 percentage: 8/23 -> 35%")
        self.assertEqual(g._ar_text_mode1, "40%",
            "mode 1 percentage: 2/5 -> 40%")
        self.assertEqual(g._downs_text_mode1, "2",
            "downs=2 must be shown as '2'")
        self.assertEqual(g._hp_text_mode2, "80",
            "mode 2 real: 8 * 10 -> 80")
        self.assertEqual(g._ar_text_mode2, "20",
            "mode 2 real: 2 * 10 -> 20")
        self.assertTrue(bool(g._same_root),
            "mode switch must preserve root primitive identity via rawequal")
        self.assertTrue(bool(g._same_gauge),
            "mode switch must preserve gauge primitive identity via rawequal")
        self.assertTrue(bool(g._same_hp_text),
            "mode switch must preserve health_text primitive identity via rawequal")
        self.assertTrue(bool(g._same_ar_text),
            "mode switch must preserve armor_text primitive identity via rawequal")


class PlayerRuntimeCoordinationTests(unittest.TestCase):
    def test_runtime_refresh_enable_off_on_unmount_restore(self):
        """runtime:refresh_settings enable off unmounts player, on restores. foundation off removes."""
        setup = '''
            local damage = {
                _health = 50, _health_max = 100, _armor = 25, _armor_max = 50, _revives = 1,
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
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = {_peer_id = nil, _ai = false}
            local parent = _G.panel_double
            mgr._safe_script = {panel = parent}
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/player.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            local mgr = _G.managers.hud
            kyohud.hud.runtime:refresh_settings(mgr)
            _after_enable = kyohud.hud.player._root

            kyohud.settings.enable_player = false
            kyohud.hud.runtime:refresh_settings(mgr)
            _after_disable = kyohud.hud.player._root

            kyohud.settings.enable_player = true
            kyohud.hud.runtime:refresh_settings(mgr)
            _after_reenable = kyohud.hud.player._root
            _reenable_alive = alive(_after_reenable)

            kyohud.settings.enable_hud_foundation = false
            kyohud.hud.runtime:refresh_settings(mgr)
            _after_foundation_off = kyohud.hud.player._root
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._after_enable,
            "enable must mount player panel")
        self.assertIsNone(g._after_disable,
            "disable must unmount player panel")
        self.assertIsNotNone(g._after_reenable,
            "reenable must restore player panel")
        self.assertTrue(bool(g._reenable_alive),
            "restored player root must be alive")
        self.assertIsNone(g._after_foundation_off,
            "foundation off must remove player panel")


class PlayerRootLossAndRebuildTests(unittest.TestCase):
    def test_root_loss_remove_via_parent_and_rebuild_recovery(self):
        """Lost owned root via P._root:parent():remove(P._root), runtime:rebuild recovers.
        Condition seeded by actual registered hook, sentinel combat same."""
        setup = '''
            local damage = {
                _health = 50, _health_max = 100, _armor = 30, _armor_max = 50, _revives = 1,
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
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = {_peer_id = nil, _ai = false}
            local parent = _G.panel_double
            mgr._safe_script = {panel = parent}

            kyohud.killstreak = kyohud.killstreak or {}
            kyohud.killstreak.count = 99
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/player.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            local mgr = _G.managers.hud
            kyohud.hud.runtime:refresh_settings(mgr)

            mgr:set_teammate_condition(HUDManager.PLAYER_PANEL, "down", "Downed")
            for _, e in ipairs(Hooks._all) do
                if e.method == "set_teammate_condition" then
                    e.fn(mgr, HUDManager.PLAYER_PANEL, "down", "Downed")
                end
            end

            local ACT = kyohud.hud.actors
            ACT:refresh(mgr)
            local snap_before = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _cond_icon_before = snap_before and snap_before.condition_icon or nil

            local P = kyohud.hud.player
            local old_root = P._root
            local parent = old_root:parent()
            parent:remove(old_root)

            kyohud.hud.runtime:rebuild(mgr)

            local new_root = P._root
            _recovered = alive(new_root)
            _new_root_is_different = (new_root ~= old_root)
            _killstreak_count = kyohud.killstreak and kyohud.killstreak.count or nil

            ACT:refresh(mgr)
            local snap_after = ACT:get_actor(HUDManager.PLAYER_PANEL)
            _cond_icon_after = snap_after and snap_after.condition_icon or nil
        ''')
        g = lua.globals()
        self.assertEqual(g._cond_icon_before, "down",
            "condition must be seeded via registered hook before root loss")
        self.assertTrue(bool(g._recovered),
            "rebuild must recover player root after loss via parent:remove")
        self.assertTrue(bool(g._new_root_is_different),
            "recovered root must be a new instance")
        self.assertEqual(float(g._killstreak_count), 99.0,
            "rebuild must not touch kyohud.killstreak sentinel")
        self.assertEqual(g._cond_icon_after, "down",
            "condition must be preserved after rebuild via registered hook")


class PlayerVerifyAndRestoreTests(unittest.TestCase):
    def test_verify_detects_corruption_and_update_restores(self):
        """verify() detects fill and text corruption with restoration P:update(mgr,monotonic_t,.1) actual path."""
        setup = '''
            local damage = {
                _health = 40, _health_max = 100, _armor = 20, _armor_max = 50, _revives = 1,
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
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = {_peer_id = nil, _ai = false}
            local parent = _G.panel_double
            mgr._safe_script = {panel = parent}
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/player.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            local mgr = _G.managers.hud
            kyohud.hud.runtime:refresh_settings(mgr)

            local ACT = kyohud.hud.actors
            ACT:refresh(mgr)
            local snap = ACT:get_actor(HUDManager.PLAYER_PANEL)

            local P = kyohud.hud.player
            local mult = tweak_data.gui.stats_present_multiplier
            P:render(snap, mult)
            _ok_clean = P:verify()

            if P._gauge and P._gauge.health_fill then
                P._gauge.health_fill:set_shape(-1, -1, -1, -1)
            end
            _ok_bad_fill = P:verify()

            P:update(mgr, 1.0, 0.1)
            _ok_fill_restored = P:verify()

            if P._gauge and P._gauge.health_text then
                P._gauge.health_text:set_text("WRONG")
            end
            _ok_bad_text = P:verify()

            P:update(mgr, 2.0, 0.1)
            _ok_text_restored = P:verify()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._ok_clean),
            "verify() must be true on a healthy player panel")
        self.assertFalse(bool(g._ok_bad_fill),
            "verify() must be false after corrupting gauge fill")
        self.assertTrue(bool(g._ok_fill_restored),
            "verify() must be true after update restores gauge fill")
        self.assertFalse(bool(g._ok_bad_text),
            "verify() must be false after corrupting gauge text")
        self.assertTrue(bool(g._ok_text_restored),
            "verify() must be true after update restores gauge text")


if __name__ == "__main__":
    unittest.main()
