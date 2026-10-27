"""Teardown regression -- gauge/player/runtime safe teardown when engine kills workspace.

Context: engine crash returning to lobby with EHI present. Crash signature:
  gauge.lua:344 self._parent:remove(self.root) inside pcall
  -> player.unmount:501 -> player.destroy:619 -> RT.destroy:309 PostHook
  -> EHI HUDManagerPD2.lua:61 original.destroy
No claim EHI is the culprit. These tests document the safe-teardown contract
for KyoHUD-owned panels when the engine workspace is already dead.

Three tests:
  1. Gauge under parent, parent subtree killed via native parent:remove(gauge.root),
     then spy parent.remove attempts: gauge:destroy must make ZERO remove calls
     against dead root even though Lua refs are nonnil.
  2. Full mounted player via RT.refresh with local snapshot fixture; mimic engine
     workspace parent removed recursively (panel_double subtree killed); spy dead
     player root.remove and dead parent.remove counters; invoke actual registered
     HUDManager destroy post callbacks; require zero dead-object Diesel method calls;
     P._root/_gauge and RT._root_panel cleared, no exception; repeat destroy idempotent.
     Mock method attempts count OUTSIDE raising error since pcall can swallow Lua
     error but cannot engine AV; assert counters zero.
  3. Live normal unmount removes only owned root once, native/thirdparty sibling
     alive, repeated unmount no extra calls.
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

from test_hud_gauge import STUBS as GAUGE_STUBS
from test_hud_actors import NATIVE_HEALTH_ARMOR_FIXTURE, NATIVE_REVIVES_CONDITION_FIXTURE

ROOT = Path(__file__).resolve().parents[1]
GAUGE_PATH = ROOT / "lua" / "hud" / "components" / "gauge.lua"
PLAYER_PATH = ROOT / "lua" / "hud" / "player.lua"
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
    if player_src:
        lua.execute(player_src)
    return lua


PLAYER_MOUNT_SETUP = '''
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

    kyohud.settings.enable_hud_foundation = true
    kyohud.settings.enable_player = true
'''


class GaugeDeadParentTeardownTests(unittest.TestCase):
    def test_gauge_destroy_zero_remove_calls_after_parent_killed_root(self):
        """Gauge under parent; parent:remove(gauge.root) kills subtree; then spy
        parent.remove; gauge:destroy must make ZERO remove calls against dead root
        even though Lua refs are nonnil."""
        lua = _lua()
        lua.execute('''
            local parent = _G.panel_double
            local inst = kyohud.hud.gauge.new(parent, "teardown_g1")
            assert(inst, "gauge must be created")
            inst:set_geometry(0, 0, 200, 40)

            local dead_root = inst.root
            local dead_root_name = dead_root:name()

            parent:remove(dead_root)

            _root_alive_after_kill = alive(dead_root)
            _parent_has_root = parent:child(dead_root_name) ~= nil

            _lua_refs_nonnil = (inst._parent ~= nil and inst.root ~= nil)

            _remove_attempts = 0
            local orig_remove = getmetatable(parent).remove
            parent.remove = function(self, c)
                _remove_attempts = _remove_attempts + 1
                error("engine AV: remove on dead subtree")
            end

            inst:destroy()

            _gauge_parent_after = inst._parent
            _gauge_root_after = inst.root
        ''')
        g = lua.globals()
        self.assertFalse(bool(g._root_alive_after_kill),
            "parent:remove must kill the gauge root subtree")
        self.assertFalse(bool(g._parent_has_root),
            "parent:remove must unlink root from parent children")
        self.assertTrue(bool(g._lua_refs_nonnil),
            "Lua refs on gauge instance must remain nonnil after external kill")
        self.assertEqual(int(g._remove_attempts), 0,
            "gauge:destroy must make ZERO parent:remove calls when root is already dead; "
            "pcall swallows Lua error but real engine would AV")
        self.assertIsNone(g._gauge_parent_after,
            "gauge:destroy must nil _parent")
        self.assertIsNone(g._gauge_root_after,
            "gauge:destroy must nil root")


class PlayerEngineWorkspaceTeardownTests(unittest.TestCase):
    def test_full_player_teardown_zero_dead_calls_and_cleared_state(self):
        """Full mounted player via RT.refresh; engine workspace parent killed
        recursively; invoke actual registered HUDManager destroy post callbacks;
        zero dead-object Diesel method calls; P._root/_gauge and RT._root_panel
        cleared; destroy idempotent."""
        lua = _lua(setup=PLAYER_MOUNT_SETUP)
        lua.execute('''
            kyohud.hud.runtime:refresh_settings(managers.hud)

            local P = kyohud.hud.player
            local RT = kyohud.hud.runtime
            local mgr = _G.managers.hud

            assert(P._root, "player root must be mounted")
            assert(P._gauge, "player gauge must be mounted")
            assert(RT._root_panel, "runtime root must be mounted")

            local owned_player_root = P._root
            local owned_rt_root = RT._root_panel
            local parent = _G.panel_double

            local function _kill_tree(p)
                if p == nil then return end
                p._alive = false
                for _, sub in pairs(p._children or {}) do _kill_tree(sub) end
            end
            _kill_tree(parent)

            _workspace_dead = not alive(parent)
            _player_root_dead = not alive(owned_player_root)
            _rt_root_dead = not alive(owned_rt_root)

            _dead_remove_attempts = 0
            local mt = getmetatable(parent)
            local orig_remove = mt.remove
            mt.remove = function(self, c)
                local self_alive = true
                local c_alive = true
                if type(alive) == "function" then
                    local ok1, a1 = pcall(alive, self)
                    self_alive = ok1 and a1
                    local ok2, a2 = pcall(alive, c)
                    c_alive = ok2 and a2
                end
                if not self_alive or not c_alive then
                    _dead_remove_attempts = _dead_remove_attempts + 1
                    error("engine AV: remove on dead panel")
                end
                return orig_remove(self, c)
            end

            _fire_ok = true
            _fire_err = nil
            for _, e in ipairs(Hooks._all) do
                if e.method == "destroy" then
                    local ok, err = pcall(e.fn, mgr)
                    if not ok then
                        _fire_ok = false
                        _fire_err = tostring(err)
                    end
                end
            end

            _P_root_after = P._root
            _P_gauge_after = P._gauge
            _RT_root_after = RT._root_panel

            _fire2_ok = true
            _fire2_err = nil
            for _, e in ipairs(Hooks._all) do
                if e.method == "destroy" then
                    local ok, err = pcall(e.fn, mgr)
                    if not ok then
                        _fire2_ok = false
                        _fire2_err = tostring(err)
                    end
                end
            end

            _attempts_after_second = _dead_remove_attempts
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._workspace_dead),
            "workspace must be dead after recursive kill")
        self.assertTrue(bool(g._player_root_dead),
            "owned player root must be dead after recursive kill")
        self.assertTrue(bool(g._rt_root_dead),
            "owned runtime root must be dead after recursive kill")
        self.assertTrue(bool(g._fire_ok),
            "firing destroy hooks must not raise; err=" + str(g._fire_err))
        self.assertEqual(int(g._dead_remove_attempts), 0,
            "zero dead-object method calls during teardown; "
            "pcall swallows Lua error but cannot prevent engine AV")
        self.assertIsNone(g._P_root_after,
            "P._root must be cleared after destroy")
        self.assertIsNone(g._P_gauge_after,
            "P._gauge must be cleared after destroy")
        self.assertIsNone(g._RT_root_after,
            "RT._root_panel must be cleared after destroy")
        self.assertTrue(bool(g._fire2_ok),
            "second destroy invocation must not raise; err=" + str(g._fire2_err))
        self.assertEqual(int(g._attempts_after_second), 0,
            "idempotent destroy must make zero additional dead-object calls")


class PlayerLiveNormalUnmountTests(unittest.TestCase):
    def test_live_unmount_removes_owned_root_once_sibling_alive(self):
        """Live normal unmount removes only owned root once, native/thirdparty
        sibling alive, repeated unmount no extra calls."""
        lua = _lua(setup=PLAYER_MOUNT_SETUP)
        lua.execute('''
            kyohud.hud.runtime:refresh_settings(managers.hud)

            local P = kyohud.hud.player
            local RT = kyohud.hud.runtime
            local parent = _G.panel_double

            local sibling = parent:panel({name="native_sibling_panel"})
            sibling:set_shape(100, 100, 200, 50)
            sibling:set_visible(true)
            _sibling_alive_before = alive(sibling)

            local owned_root = P._root
            local owned_root_name = owned_root:name()
            local owned_root_parent = owned_root:parent()

            _parent_remove_count = 0
            local orig_remove = getmetatable(owned_root_parent).remove
            owned_root_parent.remove = function(self, c)
                if c == owned_root or (type(c) == "table" and c:name() == owned_root_name) then
                    _parent_remove_count = _parent_remove_count + 1
                end
                orig_remove(self, c)
            end

            P:unmount()

            _sibling_alive_after = alive(sibling)
            _sibling_x = sibling:x()
            _sibling_y = sibling:y()
            _parent_remove_after_first = _parent_remove_count

            P:unmount()

            _parent_remove_after_second = _parent_remove_count

            _P_root = P._root
            _P_gauge = P._gauge
            _P_mounted = P._mounted
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._sibling_alive_before),
            "sibling must be alive before unmount")
        self.assertTrue(bool(g._sibling_alive_after),
            "sibling must remain alive after unmount")
        self.assertEqual(float(g._sibling_x), 100.0,
            "sibling geometry must be preserved after unmount")
        self.assertEqual(float(g._sibling_y), 100.0,
            "sibling geometry must be preserved after unmount")
        self.assertEqual(int(g._parent_remove_after_first), 1,
            "unmount must call parent:remove exactly once for owned root")
        self.assertEqual(int(g._parent_remove_after_second), 1,
            "repeated unmount must make zero additional parent:remove calls")
        self.assertIsNone(g._P_root,
            "P._root must be nil after unmount")
        self.assertIsNone(g._P_gauge,
            "P._gauge must be nil after unmount")
        self.assertFalse(bool(g._P_mounted),
            "P._mounted must be false after unmount")


if __name__ == "__main__":
    unittest.main()
