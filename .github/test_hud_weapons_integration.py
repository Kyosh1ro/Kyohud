"""LOT4b -- weapons integration: option contract, runtime lifecycle, manifest.

Bounded integration regressions BEFORE production wiring.

Proposed contract:
  - enable_weapons=false default in KH._defaults
  - KY_ToggleWeapons saves bool and invokes runtime refresh, independent of enable_player
  - menu: exactly one toggle id ky_enable_weapons, value enable_weapons,
    callback KY_ToggleWeapons, default_value false, enabled_by enable_hud_foundation
  - loc keys: ky_opt_enable_weapons, ky_opt_enable_weapons_desc,
    ky_hud_weapon_single, ky_hud_weapon_auto, ky_hud_weapon_burst, ky_hud_weapon_volley,
    ky_hud_weapon_alt, ky_hud_weapon_primary, ky_hud_weapon_secondary in fallbacks and EN/FR
  - mod.txt: exactly one component hook lua/hud/components/weapon.lua in hudmanagerpd2,
    after runtime; exactly two weapons.lua entries:
    1) RequiredScript hudmanagerpd2, after component
    2) RequiredScript playerinventory, after hudlist
  - runtime: _coordinate_weapons exists, called in mount/unmount/refresh_settings/destroy

No production writes. No bash/Git/external writes. Missing functionality = fail not skip.
"""
from pathlib import Path
import json as pyjson
import unittest

from test_hud_player import _lua as _lua_player, STUBS as PLAYER_STUBS
from test_hud_weapons import NATIVE_INVENTORY_WEAPON_FIXTURE
from test_hud_alerts_integration import _lua_with_options

ROOT = Path(__file__).resolve().parents[1]
WEAPONS_PATH = ROOT / "lua" / "hud" / "weapons.lua"
COMPONENT_PATH = ROOT / "lua" / "hud" / "components" / "weapon.lua"
RUNTIME_PATH = ROOT / "lua" / "hud" / "runtime.lua"
OPTIONS_PATH = ROOT / "lua" / "ky_options.lua"
MENU_PATH = ROOT / "menu" / "menu.json"
LOC_EN_PATH = ROOT / "loc" / "english.json"
LOC_FR_PATH = ROOT / "loc" / "french.json"
LOC_LUA_PATH = ROOT / "lua" / "ky_localization.lua"


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua_with_weapons_runtime():
    """Load full player harness + weapon component + weapons.lua explicitly.
    Component loaded before weapons; assert component exists.
    Two stable weapons+inventory initialized BEFORE runtime mount activation.
    managers.player.current_state returns STRING 'standard'."""
    setup = '''
        local damage = {
            _health = 100, _health_max = 100, _armor = 50, _armor_max = 50, _revives = 1,
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
    lua, player_exists = _lua_player(setup=setup)
    lua.execute(NATIVE_INVENTORY_WEAPON_FIXTURE)

    component_src = _read(COMPONENT_PATH)
    component_exists = component_src is not None
    assert component_exists, "RED: lua/hud/components/weapon.lua must exist"
    if component_src:
        lua.execute(component_src)

    weapons_src = _read(WEAPONS_PATH)
    weapons_exists = weapons_src is not None
    if weapons_src:
        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        lua.execute(weapons_src)
        lua.execute('RequiredScript = "lib/units/beings/player/playerinventory"')
        lua.execute(weapons_src)

    return lua, weapons_exists, player_exists


_ACTIVATE_BOILER = '''
    kyohud.settings.enable_hud_foundation = true
    kyohud.settings.enable_weapons = false
    kyohud.settings.enable_player = false
    kyohud.killstreak = 17

    managers.player.current_state = function(self) return "standard" end

    unit1, base1 = make_weapon("new_m1014")
    base1:_native_set_ammo(8, 6, 32, 40)
    base1:_native_set_fire_mode("auto")
    inventory:_native_set_slot(1, unit1)

    unit2, base2 = make_weapon("new_m16")
    base2:_native_set_ammo(30, 25, 120, 150)
    base2:_native_set_fire_mode("single")
    inventory:_native_set_slot(2, unit2)
    inventory:_native_set_equipped(2)

    local mgr = _G.managers.hud
    kyohud.hud.runtime:mount(mgr)
'''


class WeaponsRuntimeLifecycleTests(unittest.TestCase):
    """enable_weapons=true + foundation=true mounts weapons._root with two _cards.
    Update after ammo mutation reflects changes. Disable removes weapons only."""

    def test_enable_weapons_mounts_root_and_cards(self):
        lua, weapons_ok, player_ok = _lua_with_weapons_runtime()
        self.assertTrue(weapons_ok, "RED: lua/hud/weapons.lua must exist")
        self.assertTrue(player_ok, "RED: player harness must load")
        self.assertTrue(lua.eval("kyohud.hud.weapons ~= nil"),
            "RED: kyohud.hud.weapons must exist after load")
        lua.execute(_ACTIVATE_BOILER + '''
            local WEAP = kyohud.hud.weapons
            local RT = kyohud.hud.runtime
            local mgr = _G.managers.hud

            kyohud.settings.enable_weapons = true
            RT:refresh_settings(mgr)
            _root_exists = WEAP._root ~= nil
            _cards_count = 0
            if WEAP._root then
                for _, c in pairs(WEAP._root:children()) do
                    if c:name():find("weapon_card") then _cards_count = _cards_count + 1 end
                end
            end
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._root_exists),
            "RED: enable_weapons=true must mount WEAP._root")
        self.assertEqual(int(g._cards_count), 2,
            "RED: WEAP._root must have exactly 2 _card children")

    def test_update_after_ammo_mutation(self):
        lua, weapons_ok, player_ok = _lua_with_weapons_runtime()
        self.assertTrue(weapons_ok, "RED: lua/hud/weapons.lua must exist")
        lua.execute(_ACTIVATE_BOILER + '''
            local WEAP = kyohud.hud.weapons
            local RT = kyohud.hud.runtime
            local mgr = _G.managers.hud

            kyohud.settings.enable_weapons = true
            RT:refresh_settings(mgr)
            RT:update(mgr, 1.0, 0.05)

            _card1_ammo_ref = WEAP._cards and WEAP._cards[1] and WEAP._cards[1]._ammo_text or nil
            _card2_ammo_ref = WEAP._cards and WEAP._cards[2] and WEAP._cards[2]._ammo_text or nil
            _ammo1_before = _card1_ammo_ref and _card1_ammo_ref:text() or nil
            _ammo2_before = _card2_ammo_ref and _card2_ammo_ref:text() or nil

            base1:_native_set_ammo(8, 4, 30, 40)
            base2:_native_set_ammo(30, 20, 110, 150)
            -- This fixture mutates without a native event: exercise bounded rescue polling.
            RT:update(mgr, 1.66, 0.66)

            _ammo1_after = _card1_ammo_ref and _card1_ammo_ref:text() or nil
            _ammo2_after = _card2_ammo_ref and _card2_ammo_ref:text() or nil
            _same_refs = (_card1_ammo_ref == WEAP._cards[1]._ammo_text) and (_card2_ammo_ref == WEAP._cards[2]._ammo_text)
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._card1_ammo_ref,
            "RED: _cards[1]._ammo_text must exist as component instance primitive")
        self.assertIsNotNone(g._card2_ammo_ref,
            "RED: _cards[2]._ammo_text must exist as component instance primitive")
        self.assertEqual(g._ammo1_before, "6 / 26",
            "RED: initial _cards[1]._ammo_text:text() must be '6 / 26'")
        self.assertEqual(g._ammo2_before, "25 / 95",
            "RED: initial _cards[2]._ammo_text:text() must be '25 / 95'")
        self.assertEqual(g._ammo1_after, "4 / 26",
            "RED: after mutation _cards[1]._ammo_text:text() must be '4 / 26'")
        self.assertEqual(g._ammo2_after, "20 / 90",
            "RED: after mutation _cards[2]._ammo_text:text() must be '20 / 90'")
        self.assertTrue(bool(g._same_refs),
            "RED: saved _ammo_text refs must be identical to current WEAP._cards _ammo_text after update")

    def test_disable_removes_weapons_only(self):
        lua, weapons_ok, player_ok = _lua_with_weapons_runtime()
        self.assertTrue(weapons_ok, "RED: lua/hud/weapons.lua must exist")
        lua.execute(_ACTIVATE_BOILER + '''
            local WEAP = kyohud.hud.weapons
            local RT = kyohud.hud.runtime
            local mgr = _G.managers.hud

            kyohud.settings.enable_weapons = true
            RT:refresh_settings(mgr)
            _root_before_disable = WEAP._root

            kyohud.settings.enable_weapons = false
            RT:refresh_settings(mgr)
            _root_after_disable = WEAP._root
            _player_still_false = kyohud.settings.enable_player
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._root_before_disable,
            "RED: weapons root must exist before disable")
        self.assertIsNone(g._root_after_disable,
            "RED: disable must remove weapons root")
        self.assertFalse(bool(g._player_still_false),
            "RED: enable_player must remain false proving independence")


class WeaponsTurretStateTests(unittest.TestCase):
    """Turret state hides weapons, standard recovers. Runtime rebuild/destroy safe."""

    def test_turret_state_hides_weapons(self):
        lua, weapons_ok, _ = _lua_with_weapons_runtime()
        self.assertTrue(weapons_ok, "RED: lua/hud/weapons.lua must exist")
        lua.execute(_ACTIVATE_BOILER + '''
            local WEAP = kyohud.hud.weapons
            local RT = kyohud.hud.runtime
            local mgr = _G.managers.hud

            kyohud.settings.enable_weapons = true
            RT:refresh_settings(mgr)
            RT:update(mgr, 1.0, 0.05)

            _root_owned_before = WEAP._root
            _root_vis_before = _root_owned_before and _root_owned_before:visible() or nil

            managers.player.current_state = function(self) return "turret" end
            RT:update(mgr, 1.5, 0.06)
            _root_vis_turret = WEAP._root and WEAP._root:visible() or nil

            managers.player.current_state = function(self) return "standard" end
            RT:update(mgr, 2.0, 0.06)
            _root_vis_standard = WEAP._root and WEAP._root:visible() or nil
            _ammo1_standard = WEAP._cards and WEAP._cards[1] and WEAP._cards[1]._ammo_text and WEAP._cards[1]._ammo_text:text() or nil
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._root_owned_before,
            "RED: weapons root must exist after mount")
        self.assertTrue(bool(g._root_vis_before),
            "RED: weapons root must be visible in standard state initially")
        self.assertFalse(bool(g._root_vis_turret),
            "RED: turret state must set weapons root visible=false")
        self.assertTrue(bool(g._root_vis_standard),
            "RED: standard state must restore weapons root visible=true")
        self.assertEqual(g._ammo1_standard, "6 / 26",
            "RED: standard recovery must show fresh values '6 / 26'")

    def test_runtime_rebuild_and_destroy_safe(self):
        lua, weapons_ok, _ = _lua_with_weapons_runtime()
        self.assertTrue(weapons_ok, "RED: lua/hud/weapons.lua must exist")
        lua.execute(_ACTIVATE_BOILER + '''
            local WEAP = kyohud.hud.weapons
            local RT = kyohud.hud.runtime
            local mgr = _G.managers.hud

            kyohud.settings.enable_weapons = true
            RT:refresh_settings(mgr)
            _root_before_rebuild = WEAP._root

            RT:rebuild(mgr)
            _root_after_rebuild = WEAP._root
            _rebuild_different = (_root_after_rebuild ~= _root_before_rebuild)

            RT:destroy(mgr)
            _root_after_destroy = WEAP._root
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._root_before_rebuild,
            "RED: weapons root must exist before rebuild")
        self.assertIsNotNone(g._root_after_rebuild,
            "RED: weapons root must exist after rebuild")
        self.assertTrue(bool(g._rebuild_different),
            "RED: rebuilt root must be a new instance")
        self.assertIsNone(g._root_after_destroy,
            "RED: destroy must remove weapons root")


class WeaponsOptionContractTests(unittest.TestCase):
    """enable_weapons=false default; KY_ToggleWeapons exists and persists."""

    def test_option_contract(self):
        lua, ok = _lua_with_options()
        self.assertTrue(ok, "RED: ky_options.lua must load")
        self.assertTrue(lua.eval("kyohud._defaults.enable_weapons ~= nil"),
            "RED: _defaults must explicitly have enable_weapons key")
        self.assertEqual(lua.eval("kyohud._defaults.enable_weapons"), False,
            "RED: _defaults.enable_weapons must explicitly be false")
        self.assertEqual(lua.eval("kyohud.settings.enable_weapons"), False,
            "RED: settings.enable_weapons must default to false")
        self.assertTrue(lua.eval("MenuCallbackHandler.KY_ToggleWeapons ~= nil"),
            "RED: MenuCallbackHandler.KY_ToggleWeapons must exist")
        lua.execute('''
            for k in pairs(_ky_mem_files) do _ky_mem_files[k] = nil end
            local old = '{"enable_killfeed":true}'
            local f = io.open(kyohud._settings_path, "w"); f:write(old); f:close()
            kyohud.settings.enable_weapons = true
            kyohud.Load()
            _absent_old = kyohud.settings.enable_weapons
        ''')
        self.assertEqual(lua.eval("_absent_old"), False,
            "RED: old save without enable_weapons must yield false after Load")
        lua.execute('''
            kyohud.settings.enable_weapons = true; kyohud.Save()
            kyohud.settings.enable_weapons = false; kyohud.Load()
            _rt_true = kyohud.settings.enable_weapons
            kyohud.settings.enable_weapons = false; kyohud.Save()
            kyohud.settings.enable_weapons = true; kyohud.Load()
            _rt_false = kyohud.settings.enable_weapons
        ''')
        self.assertEqual(lua.eval("_rt_true"), True,
            "RED: Save(true)/Load must preserve true")
        self.assertEqual(lua.eval("_rt_false"), False,
            "RED: Save(false)/Load must preserve false")


class WeaponsCallbackContractTests(unittest.TestCase):
    """KY_ToggleWeapons persists on/off through Save and Load, without changing
    enable_player, for both enable_player true and false independence cases."""

    def test_callback_contract(self):
        lua, ok = _lua_with_options()
        self.assertTrue(ok, "RED: ky_options.lua must load")
        self.assertTrue(lua.eval("MenuCallbackHandler.KY_ToggleWeapons ~= nil"),
            "RED: MenuCallbackHandler.KY_ToggleWeapons must exist")
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_weapons = false
            kyohud.settings.enable_player = false
        ''' + '''
            kyohud.settings.enable_player = false
            local fake_on = {value = function() return "on" end}
            MenuCallbackHandler.KY_ToggleWeapons(nil, fake_on)
            _weapons_on = kyohud.settings.enable_weapons
            _player_unchanged_1 = kyohud.settings.enable_player

            local file_on = _ky_mem_files[kyohud._settings_path]
            assert(type(file_on) == "string" and #file_on > 0,
                "RED: Save must write nonempty in-memory file")
            local decoded_on = json.decode(file_on)
            _file_weapons_on = decoded_on.enable_weapons
            _file_player_on = decoded_on.enable_player

            kyohud.settings.enable_weapons = false
            kyohud.Load()
            _after_load_on = kyohud.settings.enable_weapons
        ''')
        g = lua.globals()
        self.assertEqual(g._weapons_on, True,
            "RED: callback ON must set enable_weapons=true")
        self.assertEqual(g._player_unchanged_1, False,
            "RED: callback ON must not change enable_player")
        self.assertEqual(g._file_weapons_on, True,
            "RED: decoded in-memory file must contain enable_weapons=true after callback ON")
        self.assertEqual(g._file_player_on, False,
            "RED: decoded in-memory file must preserve enable_player=false after callback ON")
        self.assertEqual(g._after_load_on, True,
            "RED: Load after Save(true) must restore enable_weapons=true")
        lua.execute('''
            local fake_off = {value = function() return "off" end}
            MenuCallbackHandler.KY_ToggleWeapons(nil, fake_off)
            _weapons_off = kyohud.settings.enable_weapons
            _player_unchanged_2 = kyohud.settings.enable_player

            local file_off = _ky_mem_files[kyohud._settings_path]
            local decoded_off = json.decode(file_off)
            _file_weapons_off = decoded_off.enable_weapons
            _file_player_off = decoded_off.enable_player

            kyohud.settings.enable_weapons = true
            kyohud.Load()
            _after_load_off = kyohud.settings.enable_weapons
        ''')
        g2 = lua.globals()
        self.assertEqual(g2._weapons_off, False,
            "RED: callback OFF must set enable_weapons=false")
        self.assertEqual(g2._player_unchanged_2, False,
            "RED: callback OFF must not change enable_player")
        self.assertEqual(g2._file_weapons_off, False,
            "RED: decoded in-memory file must contain enable_weapons=false after callback OFF")
        self.assertEqual(g2._file_player_off, False,
            "RED: decoded in-memory file must preserve enable_player=false after callback OFF")
        self.assertEqual(g2._after_load_off, False,
            "RED: Load after Save(false) must restore enable_weapons=false")
        lua.execute('''
            kyohud.settings.enable_player = true
            local fake_on2 = {value = function() return "on" end}
            MenuCallbackHandler.KY_ToggleWeapons(nil, fake_on2)
            local file_a = _ky_mem_files[kyohud._settings_path]
            local decoded_a = json.decode(file_a)
            _file_weapons_player_true = decoded_a.enable_weapons
            _file_player_preserved = decoded_a.enable_player

            local fake_off2 = {value = function() return "off" end}
            MenuCallbackHandler.KY_ToggleWeapons(nil, fake_off2)
            local file_b = _ky_mem_files[kyohud._settings_path]
            local decoded_b = json.decode(file_b)
            _file_weapons_player_true_off = decoded_b.enable_weapons
            _file_player_still_true = decoded_b.enable_player
        ''')
        g3 = lua.globals()
        self.assertEqual(g3._file_weapons_player_true, True,
            "RED: callback ON with enable_player=true must set enable_weapons=true in file")
        self.assertEqual(g3._file_player_preserved, True,
            "RED: enable_player=true must be preserved in saved file when callback toggles weapons")
        self.assertEqual(g3._file_weapons_player_true_off, False,
            "RED: callback OFF with enable_player=true must set enable_weapons=false in file")
        self.assertEqual(g3._file_player_still_true, True,
            "RED: enable_player=true must remain preserved after callback OFF")


class WeaponsManifestContractTests(unittest.TestCase):
    """Exactly two weapons.lua hooks in mod.txt (hudmanagerpd2 + playerinventory),
    menu toggle, EN/FR parity, fallback keys."""

    def test_manifest_contract(self):
        src = _read(WEAPONS_PATH)
        self.assertIsNotNone(src, "RED: weapons.lua must exist")
        self.assertIn("RequiredScript", src,
            "RED: weapons.lua must check RequiredScript")
        comp_src = _read(COMPONENT_PATH)
        self.assertIsNotNone(comp_src, "RED: lua/hud/components/weapon.lua must exist")
        mod_raw = _read(ROOT / "mod.txt")
        self.assertIsNotNone(mod_raw, "RED: mod.txt must exist")
        mod = pyjson.loads(mod_raw)
        hooks = mod.get("hooks", [])
        weapons_hooks = [h for h in hooks if h.get("script_path") == "lua/hud/weapons.lua"]
        self.assertEqual(len(weapons_hooks), 2,
            "RED: exactly two mod.txt hooks for lua/hud/weapons.lua")
        component_hooks = [h for h in hooks if h.get("script_path") == "lua/hud/components/weapon.lua"]
        self.assertEqual(len(component_hooks), 1,
            "RED: exactly one mod.txt hook for lua/hud/components/weapon.lua")
        hudmgrpd2_hooks = [h for h in hooks if h.get("hook_id") == "lib/managers/hudmanagerpd2"]
        playerinv_hooks = [h for h in hooks if h.get("hook_id") == "lib/units/beings/player/playerinventory"]
        weapons_hud_idx = None
        weapons_inv_idx = None
        for i, h in enumerate(hudmgrpd2_hooks):
            if h.get("script_path") == "lua/hud/weapons.lua":
                weapons_hud_idx = i
        for i, h in enumerate(playerinv_hooks):
            if h.get("script_path") == "lua/hud/weapons.lua":
                weapons_inv_idx = i
        component_hud_idx = None
        for i, h in enumerate(hudmgrpd2_hooks):
            if h.get("script_path") == "lua/hud/components/weapon.lua":
                component_hud_idx = i
        self.assertIsNotNone(weapons_hud_idx,
            "RED: weapons.lua must appear in hudmanagerpd2 hooks")
        self.assertIsNotNone(weapons_inv_idx,
            "RED: weapons.lua must appear in playerinventory hooks")
        self.assertIsNotNone(component_hud_idx,
            "RED: component weapon.lua must appear in hudmanagerpd2 hooks")
        runtime_idx = None
        for i, h in enumerate(hudmgrpd2_hooks):
            if h.get("script_path") == "lua/hud/runtime.lua":
                runtime_idx = i
        self.assertIsNotNone(runtime_idx,
            "RED: runtime.lua must appear in hudmanagerpd2 hooks")
        self.assertGreater(component_hud_idx, runtime_idx,
            "RED: component weapon.lua must come after runtime.lua")
        self.assertGreater(weapons_hud_idx, component_hud_idx,
            "RED: weapons.lua must come after component weapon.lua")
        menu_raw = _read(MENU_PATH)
        self.assertIsNotNone(menu_raw, "RED: menu.json must exist")
        menu = pyjson.loads(menu_raw)
        self.assertIn("items", menu,
            "RED: menu.json root must have 'items' key")
        items = menu["items"]
        weapons_entries = [
            e for e in items
            if isinstance(e, dict) and e.get("value") == "enable_weapons"
        ]
        self.assertEqual(len(weapons_entries), 1,
            "RED: exactly one menu entry with value enable_weapons")
        entry = weapons_entries[0]
        self.assertEqual(entry.get("type"), "toggle",
            "RED: menu entry type must be toggle")
        self.assertEqual(entry.get("default_value"), False,
            "RED: menu default_value must be false")
        self.assertEqual(entry.get("callback"), "KY_ToggleWeapons",
            "RED: callback must be KY_ToggleWeapons")
        self.assertEqual(entry.get("enabled_by"), "enable_hud_foundation",
            "RED: enabled_by must be enable_hud_foundation")
        lua, ok = _lua_with_options()
        self.assertTrue(ok, "RED: ky_options.lua must load")
        self.assertTrue(lua.eval("MenuCallbackHandler.KY_ToggleWeapons ~= nil"),
            "RED: KY_ToggleWeapons symbol must exist (not regex-only)")
        required_keys = [
            "ky_opt_enable_weapons", "ky_opt_enable_weapons_desc",
            "ky_hud_weapon_single", "ky_hud_weapon_auto", "ky_hud_weapon_burst",
            "ky_hud_weapon_volley", "ky_hud_weapon_alt",
            "ky_hud_weapon_primary", "ky_hud_weapon_secondary",
        ]
        en = pyjson.loads(_read(LOC_EN_PATH))
        fr = pyjson.loads(_read(LOC_FR_PATH))
        for key in required_keys:
            self.assertIn(key, en, f"RED: EN loc missing {key}")
            self.assertIn(key, fr, f"RED: FR loc missing {key}")
            self.assertTrue(isinstance(en[key], str) and len(en[key]) > 0,
                f"RED: EN value for {key} must be nonempty")
            self.assertTrue(isinstance(fr[key], str) and len(fr[key]) > 0,
                f"RED: FR value for {key} must be nonempty")
        loc_src = _read(LOC_LUA_PATH)
        self.assertIsNotNone(loc_src, "RED: ky_localization.lua must exist")
        for key in required_keys:
            self.assertIn(key, loc_src,
                f"RED: ky_localization.lua fallback must contain key {key}")


class WeaponsRuntimeCoordinateTests(unittest.TestCase):
    """Runtime must have _coordinate_weapons method called in lifecycle methods."""

    def test_runtime_coordinate_weapons_exists(self):
        lua, ok = _lua_with_options()
        self.assertTrue(ok, "RED: base runtime must load")
        self.assertTrue(lua.eval("type(kyohud.hud.runtime._coordinate_weapons) == 'function'"),
            "RED: runtime._coordinate_weapons must exist as a function")

    def test_runtime_calls_coordinate_weapons(self):
        lua, weapons_ok, _ = _lua_with_weapons_runtime()
        self.assertTrue(weapons_ok, "RED: weapons.lua must load")
        lua.execute(_ACTIVATE_BOILER + '''
            local RT = kyohud.hud.runtime
            local mgr = _G.managers.hud

            _coord_calls = 0
            local original_coord = RT._coordinate_weapons
            RT._coordinate_weapons = function(self, method_name, ...)
                _coord_calls = _coord_calls + 1
                return original_coord(self, method_name, ...)
            end

            kyohud.settings.enable_weapons = true
            RT:refresh_settings(mgr)
            _calls_after_refresh = _coord_calls

            RT:rebuild(mgr)
            _calls_after_rebuild = _coord_calls

            RT:destroy(mgr)
            _calls_after_destroy = _coord_calls
        ''')
        g = lua.globals()
        self.assertGreater(int(g._calls_after_refresh), 0,
            "RED: refresh_settings must call _coordinate_weapons")
        self.assertGreater(int(g._calls_after_rebuild), int(g._calls_after_refresh),
            "RED: rebuild must call _coordinate_weapons")
        self.assertGreater(int(g._calls_after_destroy), int(g._calls_after_rebuild),
            "RED: destroy must call _coordinate_weapons")


if __name__ == "__main__":
    unittest.main()
