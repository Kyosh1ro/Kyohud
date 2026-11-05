"""Lot6 integration -- local+crew combined foundation and off/on preservation.

Scope: integration qualification for local player, weapons, equipment, and crew
consumers in realistic combined scenario. Real runtime/callbacks, not monkeypatched
certification. Combat state preservation through foundation off/on. Third-party
sibling sentinel preservation.

Imports existing fixtures to avoid copying hundreds of lines. Reuses:
- test_hud_crew._lua (loads layout, native_vis, runtime, actors, gauge, player, crew_card, crew + ROSTER_SETUP)
- test_hud_weapons.NATIVE_INVENTORY_WEAPON_FIXTURE
- test_hud_equipment.NATIVE_EQUIPMENT_FIXTURE
- test_hud_equipment_consumables.NATIVE_CONSUMABLES_FIXTURE
- test_hud_equipment_events.EVENTS

Loading order: crew base (includes player) -> weapons -> equipment.
NOTE: Crew is loaded before weapons in _base_crew_lua(), not in strict manifest order.
The _crew_lua() function enriches with weapons and equipment after the crew base.

Limitations:
- No Diesel engine reproduction; stubs are minimal but allow real callbacks
- Bounded first tranche: local+crew only; mission/objectives/alerts/assault next tranche
- No native panel structural mutations (clear/remove/reparent) on native panels allowed
- Combat state preservation verified via killstreak/score sentinels
- Complete loading graph already tested in test_load_order
"""
from pathlib import Path
import unittest

from test_hud_crew import _lua as _base_crew_lua
from test_hud_weapons import NATIVE_INVENTORY_WEAPON_FIXTURE
from test_hud_equipment import NATIVE_EQUIPMENT_FIXTURE
from test_hud_equipment_consumables import NATIVE_CONSUMABLES_FIXTURE
from test_hud_equipment_events import EVENTS

ROOT = Path(__file__).resolve().parents[1]
COMPONENT_WEAPON_PATH = ROOT / "lua" / "hud" / "components" / "weapon.lua"
WEAPONS_PATH = ROOT / "lua" / "hud" / "weapons.lua"
COMPONENT_EQUIPMENT_PATH = ROOT / "lua" / "hud" / "components" / "equipment.lua"
EQUIPMENT_PATH = ROOT / "lua" / "hud" / "equipment.lua"


def _read(p):
    assert p.is_file(), f"required production chunk missing: {p}"
    return p.read_text(encoding="utf-8-sig")


def _crew_lua():
    """Build combined Lua runtime: crew base + weapons + equipment.
    Enriches test_hud_crew._lua with weapon and equipment components/fixtures.
    Loads in manifest order: weapon component -> weapons -> equipment component -> equipment.
    Returns (lua, crew_ok, weapons_ok, equipment_ok).
    """
    lua, crew_ok = _base_crew_lua()
    if not crew_ok:
        return lua, crew_ok, False, False

    lua.execute(NATIVE_INVENTORY_WEAPON_FIXTURE)

    weapon_comp_src = _read(COMPONENT_WEAPON_PATH)
    if weapon_comp_src:
        lua.execute(weapon_comp_src)

    weapons_src = _read(WEAPONS_PATH)
    weapons_ok = weapons_src is not None
    if weapons_src:
        lua.globals().RequiredScript = "lib/managers/hudmanagerpd2"
        lua.execute(weapons_src)
        lua.globals().RequiredScript = "lib/units/beings/player/playerinventory"
        lua.execute(weapons_src)

    lua.execute(NATIVE_EQUIPMENT_FIXTURE + NATIVE_CONSUMABLES_FIXTURE + EVENTS)

    # NATIVE_EQUIPMENT_FIXTURE overwrites player_unit; restore inventory link
    # and attach legitimate damage source AFTER fixture with distinct ratios
    lua.execute('''
        player_unit.inventory = function() return inventory end
        player_unit.current_state = function() return {name="standard"} end
        managers.player.player_unit = function(self) return player_unit end
        local damage = {
            _health = 75, _health_max = 100, _armor = 20, _armor_max = 50, _revives = 1,
            get_real_health = function(self) return self._health end,
            _max_health = function(self) return self._health_max end,
            get_real_armor = function(self) return self._armor end,
            _max_armor = function(self) return self._armor_max end,
            get_revives = function(self) return self._revives end,
        }
        player_unit.character_damage = function(self) return damage end
    ''')

    equip_comp_src = _read(COMPONENT_EQUIPMENT_PATH)
    if equip_comp_src:
        lua.execute(equip_comp_src)

    equip_src = _read(EQUIPMENT_PATH)
    equipment_ok = equip_src is not None
    if equip_src:
        lua.globals().RequiredScript = "lib/managers/playermanager"
        lua.execute(equip_src)
        lua.globals().RequiredScript = "lib/managers/hudmanagerpd2"
        lua.execute(equip_src)

    return lua, crew_ok, weapons_ok, equipment_ok


class LocalCrewCombinedIntegrationTests(unittest.TestCase):
    """Runtime coordinates player, weapons, equipment, crew ALL active.
    Each verify/verify_render true with known source. Assert effective text
    rendering for each module. Real callbacks, no monkeypatched certification.
    """

    def test_runtime_coordinates_local_and_crew_all_active(self):
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        self.assertTrue(crew_ok, "crew.lua must exist")
        self.assertTrue(weapons_ok, "weapons.lua must exist")
        self.assertTrue(equipment_ok, "equipment.lua must exist")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            kyohud.settings.enable_weapons = true
            kyohud.settings.enable_equipment = true
            kyohud.settings.enable_crew = true
            kyohud.settings.hud_scale = 1.0
            _G.panel_double:set_shape(0, 0, 1920, 1080)

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

            managers.player:_native_set_equipment('trip_mine',{3,2})
            managers.player:_native_set_equipment('doctor_bag',{1})
            managers.player._equipment.selected_index=1
            managers.player:_native_set_grenades('pocket',1,2)
            _native_set_projectile_tweak('pocket',{ability=true,base_cooldown=30})
            managers.player:_native_set_specials('cable_tie',{3})
            _game_clock:set_time(1000)
            managers.player:_native_set_replenish_timer(1017)

            local mgr = managers.hud
            local ACT = kyohud.hud.actors
            ACT:refresh_crew(mgr, 0)
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.runtime:update(mgr, 1.0, 0.05)

            local P = kyohud.hud.player
            local WEAP = kyohud.hud.weapons
            local E = kyohud.hud.equipment
            local C = kyohud.hud.crew

            _p_verify = P and P:verify() or false
            _weap_verify = WEAP and WEAP:verify() or false
            _e_verify = E and E:verify() or false
            _c_verify = C and C:_verify_render() or false

            -- Real field names from components: gauge uses health_text (not _health_text)
            _p_gauge_text = P and P._gauge and P._gauge.health_text and P._gauge.health_text:text() or nil
            _p_gauge_armor_text = P and P._gauge and P._gauge.armor_text and P._gauge.armor_text:text() or nil
            _weap_card1_ammo = WEAP and WEAP._cards and WEAP._cards[1] and WEAP._cards[1]._ammo_text and WEAP._cards[1]._ammo_text:text() or nil
            _weap_card2_ammo = WEAP and WEAP._cards and WEAP._cards[2] and WEAP._cards[2]._ammo_text and WEAP._cards[2]._ammo_text:text() or nil
            _e_row1_value = E and E._rows and E._rows[1] and E._rows[1]._value and E._rows[1]._value:text() or nil
            _c_card1_name = C and C._cards and C._cards[1] and C._cards[1]._name_text and C._cards[1]._name_text:text() or nil

            -- Combined lifecycle qualification complements (does not duplicate)
            -- the pure crew geometry matrix in test_hud_crew_placement.py.
            local RT = kyohud.hud.runtime
            local root_before, crew_before = RT._root_panel, C._root
            local x_before, y_before = C._root:x(), C._root:y()
            kyohud.killstreak = 37
            kyohud._heist_score_total = 4321
            for i, state in ipairs({{1680,1050,0.95},{1920,1080,1.05},{1920,1080,1}}) do
                panel_double:set_shape(0,0,state[1],state[2])
                kyohud.settings.hud_scale = state[3]
                RT:refresh_settings(mgr)
                RT:update(mgr,1+i*0.1,0.1)
                assert(P:verify() and WEAP:verify() and E:verify() and C:_verify_render(),
                    "all local/crew renders must certify after combined resize")
                assert(RT._root_panel == root_before and C._root == crew_before,
                    "combined resize must preserve roots")
            end
            assert(math.abs(C._root:x()-x_before)<0.01 and math.abs(C._root:y()-y_before)<0.01,
                "A-B-A must not drift")
            RT:rebuild(mgr)
            RT:update(mgr,1.4,0.1)
            assert(P:verify() and WEAP:verify() and E:verify() and C:_verify_render(),
                "runtime rebuild must recertify all local/crew consumers")
            assert(RT._root_panel ~= root_before and C._root ~= crew_before,
                "rebuild must replace the captured owned roots")
            assert(C._root:parent() == RT._root_panel and P._root:parent() == RT._root_panel,
                "rebuilt consumers must belong to current foundation")
            assert(kyohud.killstreak == 37 and kyohud._heist_score_total == 4321,
                "resize/rebuild must preserve combat")
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._p_verify),
            "player:verify() must be true with known source")
        self.assertTrue(bool(g._weap_verify),
            "weapons:verify() must be true with known source")
        self.assertTrue(bool(g._e_verify),
            "equipment:verify() must be true with known source")
        self.assertTrue(bool(g._c_verify),
            "crew:_verify_render() must be true with known source")
        self.assertIsNotNone(g._p_gauge_text,
            "player gauge health_text must have effective text rendering")
        self.assertEqual(g._p_gauge_text, "75%",
            "player gauge health_text must be '75%' (hp 75/100)")
        self.assertIsNotNone(g._p_gauge_armor_text,
            "player gauge armor_text must have effective text rendering")
        self.assertEqual(g._p_gauge_armor_text, "40%",
            "player gauge armor_text must be '40%' (armor 20/50)")
        self.assertIsNotNone(g._weap_card1_ammo,
            "weapons card 1 ammo_text must have effective text rendering")
        self.assertEqual(g._weap_card1_ammo, "6 / 26",
            "weapons card 1 ammo must be '6 / 26'")
        self.assertIsNotNone(g._weap_card2_ammo,
            "weapons card 2 ammo_text must have effective text rendering")
        self.assertEqual(g._weap_card2_ammo, "25 / 95",
            "weapons card 2 ammo must be '25 / 95'")
        self.assertIsNotNone(g._e_row1_value,
            "equipment row 1 value must have effective text rendering")
        self.assertEqual(g._e_row1_value, "3 | 2",
            "equipment row 1 value must be '3 | 2' (trip_mine quantities)")
        self.assertIsNotNone(g._c_card1_name,
            "crew card 1 name_text must have effective text rendering")
        self.assertEqual(g._c_card1_name, "Dallas IA",
            "crew card 1 name must be 'Dallas IA' (russian AI)")


class FoundationOffOnPreservationTests(unittest.TestCase):
    """Foundation off/on preserves combat state and third-party sibling sentinel.
    All modules runtime only refresh/update. Asserts before roots validated,
    after off roots nil, after on certification true. Combat sentinels assigned
    BEFORE actions and verified AFTER. Third-party sentinel created BEFORE mount.
    Count native mutations on exact parent; announce sibling preservation.
    """

    def test_foundation_off_on_preserves_combat_state_and_siblings(self):
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        self.assertTrue(crew_ok, "crew.lua must exist")
        self.assertTrue(weapons_ok, "weapons.lua must exist")
        self.assertTrue(equipment_ok, "equipment.lua must exist")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            kyohud.settings.enable_weapons = true
            kyohud.settings.enable_equipment = true
            kyohud.settings.enable_crew = true
            kyohud.settings.hud_scale = 1.0
            _G.panel_double:set_shape(0, 0, 1920, 1080)

            local sibling = _G.panel_double:panel({name="third_party_sentinel"})
            sibling:set_shape(100, 200, 150, 250)
            sibling:set_visible(true)
            _sibling_x_before = sibling:x()
            _sibling_y_before = sibling:y()
            _sibling_w_before = sibling:w()
            _sibling_h_before = sibling:h()
            _sibling_vis_before = sibling:visible()

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

            managers.player:_native_set_equipment('trip_mine',{3,2})
            managers.player:_native_set_equipment('doctor_bag',{1})
            managers.player._equipment.selected_index=1
            managers.player:_native_set_grenades('pocket',1,2)
            _native_set_projectile_tweak('pocket',{ability=true,base_cooldown=30})
            managers.player:_native_set_specials('cable_tie',{3})
            _game_clock:set_time(1000)
            managers.player:_native_set_replenish_timer(1017)

            local mgr = managers.hud
            local ACT = kyohud.hud.actors
            ACT:refresh_crew(mgr, 0)
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.runtime:refresh_settings(mgr)

            kyohud.killstreak = 42
            kyohud._heist_score_total = 9999
            _kills_before = kyohud.killstreak
            _score_before = kyohud._heist_score_total

            _rt_root_before = kyohud.hud.runtime._root_panel
            _p_root_before = kyohud.hud.player._root
            _weap_root_before = kyohud.hud.weapons._root
            _e_root_before = kyohud.hud.equipment._root
            _c_root_before = kyohud.hud.crew._root

            kyohud.hud.runtime:update(mgr, 1.0, 0.05)
            _p_verify_before_off = kyohud.hud.player:verify()
            _weap_verify_before_off = kyohud.hud.weapons:verify()
            _e_verify_before_off = kyohud.hud.equipment:verify()
            _c_verify_before_off = kyohud.hud.crew:_verify_render()

            kyohud.settings.enable_hud_foundation = false
            kyohud.hud.runtime:refresh_settings(mgr)

            _rt_root_off = kyohud.hud.runtime._root_panel
            _p_root_off = kyohud.hud.player and kyohud.hud.player._root or nil
            _weap_root_off = kyohud.hud.weapons and kyohud.hud.weapons._root or nil
            _e_root_off = kyohud.hud.equipment and kyohud.hud.equipment._root or nil
            _c_root_off = kyohud.hud.crew and kyohud.hud.crew._root or nil

            _kills_after_off = kyohud.killstreak
            _score_after_off = kyohud._heist_score_total

            _sibling_x_off = sibling:x()
            _sibling_y_off = sibling:y()
            _sibling_w_off = sibling:w()
            _sibling_h_off = sibling:h()
            _sibling_vis_off = sibling:visible()
            _sibling_alive_off = alive(sibling)

            kyohud.settings.enable_hud_foundation = true
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.runtime:update(mgr, 2.0, 0.05)

            _rt_root_on = kyohud.hud.runtime._root_panel
            _p_root_on = kyohud.hud.player._root
            _weap_root_on = kyohud.hud.weapons._root
            _e_root_on = kyohud.hud.equipment._root
            _c_root_on = kyohud.hud.crew._root

            _p_verify_after_on = kyohud.hud.player:verify()
            _weap_verify_after_on = kyohud.hud.weapons:verify()
            _e_verify_after_on = kyohud.hud.equipment:verify()
            _c_verify_after_on = kyohud.hud.crew:_verify_render()

            _kills_after_on = kyohud.killstreak
            _score_after_on = kyohud._heist_score_total

            _sibling_x_on = sibling:x()
            _sibling_y_on = sibling:y()
            _sibling_w_on = sibling:w()
            _sibling_h_on = sibling:h()
            _sibling_vis_on = sibling:visible()
            _sibling_alive_on = alive(sibling)
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._rt_root_before,
            "runtime root must exist before foundation off")
        self.assertIsNotNone(g._p_root_before,
            "player root must exist before foundation off")
        self.assertIsNotNone(g._weap_root_before,
            "weapons root must exist before foundation off")
        self.assertIsNotNone(g._e_root_before,
            "equipment root must exist before foundation off")
        self.assertIsNotNone(g._c_root_before,
            "crew root must exist before foundation off")
        self.assertEqual(int(g._kills_before), 42,
            "combat killstreak sentinel must be 42 before off")
        self.assertEqual(int(g._score_before), 9999,
            "combat score sentinel must be 9999 before off")
        self.assertTrue(bool(g._p_verify_before_off),
            "player:verify() must be true before foundation off")
        self.assertTrue(bool(g._weap_verify_before_off),
            "weapons:verify() must be true before foundation off")
        self.assertTrue(bool(g._e_verify_before_off),
            "equipment:verify() must be true before foundation off")
        self.assertTrue(bool(g._c_verify_before_off),
            "crew:_verify_render() must be true before foundation off")

        self.assertIsNone(g._rt_root_off,
            "runtime root must be nil after foundation off")
        self.assertIsNone(g._p_root_off,
            "player root must be nil after foundation off")
        self.assertIsNone(g._weap_root_off,
            "weapons root must be nil after foundation off")
        self.assertIsNone(g._e_root_off,
            "equipment root must be nil after foundation off")
        self.assertIsNone(g._c_root_off,
            "crew root must be nil after foundation off")
        self.assertEqual(int(g._kills_after_off), 42,
            "foundation off must preserve killstreak")
        self.assertEqual(int(g._score_after_off), 9999,
            "foundation off must preserve score")
        self.assertEqual(float(g._sibling_x_off), float(g._sibling_x_before),
            "third-party sibling x must be preserved after foundation off")
        self.assertEqual(float(g._sibling_y_off), float(g._sibling_y_before),
            "third-party sibling y must be preserved after foundation off")
        self.assertEqual(float(g._sibling_w_off), float(g._sibling_w_before),
            "third-party sibling w must be preserved after foundation off")
        self.assertEqual(float(g._sibling_h_off), float(g._sibling_h_before),
            "third-party sibling h must be preserved after foundation off")
        self.assertTrue(bool(g._sibling_vis_off),
            "third-party sibling must remain visible after foundation off")
        self.assertTrue(bool(g._sibling_alive_off),
            "third-party sibling must remain alive after foundation off")

        self.assertIsNotNone(g._rt_root_on,
            "runtime root must exist after foundation on")
        self.assertIsNotNone(g._p_root_on,
            "player root must exist after foundation on")
        self.assertIsNotNone(g._weap_root_on,
            "weapons root must exist after foundation on")
        self.assertIsNotNone(g._e_root_on,
            "equipment root must exist after foundation on")
        self.assertIsNotNone(g._c_root_on,
            "crew root must exist after foundation on")
        self.assertEqual(int(g._kills_after_on), 42,
            "foundation on must preserve killstreak")
        self.assertEqual(int(g._score_after_on), 9999,
            "foundation on must preserve score")
        self.assertTrue(bool(g._p_verify_after_on),
            "player:verify() must be true after foundation on")
        self.assertTrue(bool(g._weap_verify_after_on),
            "weapons:verify() must be true after foundation on")
        self.assertTrue(bool(g._e_verify_after_on),
            "equipment:verify() must be true after foundation on")
        self.assertTrue(bool(g._c_verify_after_on),
            "crew:_verify_render() must be true after foundation on")
        self.assertEqual(float(g._sibling_x_on), float(g._sibling_x_before),
            "third-party sibling x must be preserved after foundation on")
        self.assertEqual(float(g._sibling_y_on), float(g._sibling_y_before),
            "third-party sibling y must be preserved after foundation on")
        self.assertEqual(float(g._sibling_w_on), float(g._sibling_w_before),
            "third-party sibling w must be preserved after foundation on")
        self.assertEqual(float(g._sibling_h_on), float(g._sibling_h_before),
            "third-party sibling h must be preserved after foundation on")
        self.assertTrue(bool(g._sibling_vis_on),
            "third-party sibling must remain visible after foundation on")
        self.assertTrue(bool(g._sibling_alive_on),
            "third-party sibling must remain alive after foundation on")


class StableOrdinaryUpdateTests(unittest.TestCase):
    """Stable ordinary update: no new allocations, same identities across monotonic ticks."""

    def test_stable_ordinary_update_preserves_identities_and_allocations(self):
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        self.assertTrue(crew_ok, "crew.lua must exist")
        self.assertTrue(weapons_ok, "weapons.lua must exist")
        self.assertTrue(equipment_ok, "equipment.lua must exist")

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            kyohud.settings.enable_weapons = true
            kyohud.settings.enable_equipment = true
            kyohud.settings.enable_crew = true
            kyohud.settings.hud_scale = 1.0
            _G.panel_double:set_shape(0, 0, 1920, 1080)

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

            managers.player:_native_set_equipment('trip_mine',{3,2})
            managers.player:_native_set_equipment('doctor_bag',{1})
            managers.player._equipment.selected_index=1
            managers.player:_native_set_grenades('pocket',1,2)
            _native_set_projectile_tweak('pocket',{ability=true,base_cooldown=30})
            managers.player:_native_set_specials('cable_tie',{3})
            _game_clock:set_time(1000)
            managers.player:_native_set_replenish_timer(1017)

            local mgr = managers.hud
            local ACT = kyohud.hud.actors
            ACT:refresh_crew(mgr, 0)
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.runtime:update(mgr, 1.0, 0.05)

            _alloc_before = _G._alloc_count()
            _rt_root_snap = kyohud.hud.runtime._root_panel
            _p_root_snap = kyohud.hud.player._root
            _weap_root_snap = kyohud.hud.weapons._root
            _e_root_snap = kyohud.hud.equipment._root
            _c_root_snap = kyohud.hud.crew._root

            _p_gauge_snap = kyohud.hud.player._gauge and kyohud.hud.player._gauge.root or nil
            _weap_card1_snap = kyohud.hud.weapons._cards and kyohud.hud.weapons._cards[1]
                and kyohud.hud.weapons._cards[1]._root or nil
            _e_row1_snap = kyohud.hud.equipment._rows and kyohud.hud.equipment._rows[1]
                and kyohud.hud.equipment._rows[1]._root or nil
            _c_card1_snap = kyohud.hud.crew._cards and kyohud.hud.crew._cards[1]
                and kyohud.hud.crew._cards[1].root or nil

            for _, key in ipairs({"_rt_root_snap", "_p_root_snap", "_weap_root_snap",
                "_e_root_snap", "_c_root_snap", "_p_gauge_snap", "_weap_card1_snap",
                "_e_row1_snap", "_c_card1_snap"}) do
                assert(_G[key] ~= nil and alive(_G[key]), key .. " must be a live primitive")
            end

            _snap_alive_rt = _rt_root_snap ~= nil
            _snap_alive_p = _p_root_snap ~= nil
            _snap_alive_weap = _weap_root_snap ~= nil
            _snap_alive_e = _e_root_snap ~= nil
            _snap_alive_c = _c_root_snap ~= nil

            _p_verify_snap = kyohud.hud.player:verify()
            _weap_verify_snap = kyohud.hud.weapons:verify()
            _e_verify_snap = kyohud.hud.equipment:verify()
            _c_verify_snap = kyohud.hud.crew:_verify_render()

            for i = 1, 10 do
                kyohud.hud.runtime:update(mgr, 1.0 + i * 0.05, 0.05)
            end

            _alloc_after = _G._alloc_count()
            _rt_root_after = kyohud.hud.runtime._root_panel
            _p_root_after = kyohud.hud.player._root
            _weap_root_after = kyohud.hud.weapons._root
            _e_root_after = kyohud.hud.equipment._root
            _c_root_after = kyohud.hud.crew._root

            _p_gauge_after = kyohud.hud.player._gauge and kyohud.hud.player._gauge.root or nil
            _weap_card1_after = kyohud.hud.weapons._cards and kyohud.hud.weapons._cards[1]
                and kyohud.hud.weapons._cards[1]._root or nil
            _e_row1_after = kyohud.hud.equipment._rows and kyohud.hud.equipment._rows[1]
                and kyohud.hud.equipment._rows[1]._root or nil
            _c_card1_after = kyohud.hud.crew._cards and kyohud.hud.crew._cards[1]
                and kyohud.hud.crew._cards[1].root or nil

            for _, key in ipairs({"_rt_root_after", "_p_root_after", "_weap_root_after",
                "_e_root_after", "_c_root_after", "_p_gauge_after", "_weap_card1_after",
                "_e_row1_after", "_c_card1_after"}) do
                assert(_G[key] ~= nil and alive(_G[key]), key .. " must remain live")
            end

            _after_alive_rt = _rt_root_after ~= nil
            _after_alive_p = _p_root_after ~= nil
            _after_alive_weap = _weap_root_after ~= nil
            _after_alive_e = _e_root_after ~= nil
            _after_alive_c = _c_root_after ~= nil

            _p_verify_after = kyohud.hud.player:verify()
            _weap_verify_after = kyohud.hud.weapons:verify()
            _e_verify_after = kyohud.hud.equipment:verify()
            _c_verify_after = kyohud.hud.crew:_verify_render()

            _same_rt = (_rt_root_snap == _rt_root_after)
            _same_p = (_p_root_snap == _p_root_after)
            _same_weap = (_weap_root_snap == _weap_root_after)
            _same_e = (_e_root_snap == _e_root_after)
            _same_c = (_c_root_snap == _c_root_after)
            _same_gauge = (_p_gauge_snap == _p_gauge_after)
            _same_wcard1 = (_weap_card1_snap == _weap_card1_after)
            _same_erow1 = (_e_row1_snap == _e_row1_after)
            _same_ccard1 = (_c_card1_snap == _c_card1_after)
        ''')
        g = lua.globals()
        self.assertEqual(int(g._alloc_before), int(g._alloc_after),
            "stable ordinary update must not create new primitives")
        self.assertTrue(bool(g._snap_alive_rt),
            "runtime root snapshot must be non-nil before stable loop")
        self.assertTrue(bool(g._snap_alive_p),
            "player root snapshot must be non-nil before stable loop")
        self.assertTrue(bool(g._snap_alive_weap),
            "weapons root snapshot must be non-nil before stable loop")
        self.assertTrue(bool(g._snap_alive_e),
            "equipment root snapshot must be non-nil before stable loop")
        self.assertTrue(bool(g._snap_alive_c),
            "crew root snapshot must be non-nil before stable loop")
        self.assertTrue(bool(g._p_verify_snap),
            "player:verify() must be true before stable loop")
        self.assertTrue(bool(g._weap_verify_snap),
            "weapons:verify() must be true before stable loop")
        self.assertTrue(bool(g._e_verify_snap),
            "equipment:verify() must be true before stable loop")
        self.assertTrue(bool(g._c_verify_snap),
            "crew:_verify_render() must be true before stable loop")
        self.assertTrue(bool(g._after_alive_rt),
            "runtime root must be non-nil after stable loop")
        self.assertTrue(bool(g._after_alive_p),
            "player root must be non-nil after stable loop")
        self.assertTrue(bool(g._after_alive_weap),
            "weapons root must be non-nil after stable loop")
        self.assertTrue(bool(g._after_alive_e),
            "equipment root must be non-nil after stable loop")
        self.assertTrue(bool(g._after_alive_c),
            "crew root must be non-nil after stable loop")
        self.assertTrue(bool(g._p_verify_after),
            "player:verify() must be true after stable loop")
        self.assertTrue(bool(g._weap_verify_after),
            "weapons:verify() must be true after stable loop")
        self.assertTrue(bool(g._e_verify_after),
            "equipment:verify() must be true after stable loop")
        self.assertTrue(bool(g._c_verify_after),
            "crew:_verify_render() must be true after stable loop")
        self.assertTrue(bool(g._same_rt),
            "runtime root identity must be preserved across monotonic updates")
        self.assertTrue(bool(g._same_p),
            "player root identity must be preserved across monotonic updates")
        self.assertTrue(bool(g._same_weap),
            "weapons root identity must be preserved across monotonic updates")
        self.assertTrue(bool(g._same_e),
            "equipment root identity must be preserved across monotonic updates")
        self.assertTrue(bool(g._same_c),
            "crew root identity must be preserved across monotonic updates")
        self.assertTrue(bool(g._same_gauge),
            "player gauge root identity must be preserved across monotonic updates")
        self.assertTrue(bool(g._same_wcard1),
            "weapons card 1 root identity must be preserved across monotonic updates")
        self.assertTrue(bool(g._same_erow1),
            "equipment row 1 root identity must be preserved across monotonic updates")
        self.assertTrue(bool(g._same_ccard1),
            "crew card 1 root identity must be preserved across monotonic updates")


class MissionCrewIntegrationTests(unittest.TestCase):
    """Mission+local+crew integration: timer, native alpha, sibling preservation.

    Uses same _crew_lua fixture as other tests. Loads mission module with native
    timer methods added BEFORE context. Asserts mission:_verify_render + 4 verify
    true, concrete timer text, native alpha acquisition/restitution on foundation
    off, and third-party sibling preservation.
    """

    def test_mission_crew_timer_alpha_sibling_integration(self):
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        self.assertTrue(crew_ok, "crew.lua must exist")
        self.assertTrue(weapons_ok, "weapons.lua must exist")
        self.assertTrue(equipment_ok, "equipment.lua must exist")

        lua.execute(r'''
            tweak_data.hud = {medium_font_noshadow = "fonts/font_medium_mf"}
            HUDHeistTimer = {}; HUDHeistTimer.__index = HUDHeistTimer
            function HUDHeistTimer:new(tweak_hud)
                local obj = setmetatable({}, self)
                obj._last_time = 0
                obj._enabled = not (tweak_hud and tweak_hud.no_timer)
                obj._timer_text = {
                    _text = "00:00", _alpha = 0.37, _font_size = 24, _visible = true,
                    text = function(s) return s._text end,
                    set_text = function(s, str) s._text = str end,
                    alpha = function(s) return s._alpha end,
                    set_alpha = function(s, a) s._alpha = a end,
                    set_visible = function(s, v) s._visible = v end,
                    visible = function(s) return s._visible end,
                }
                return obj
            end
            function HUDHeistTimer:set_time(time)
                if time < 0 then time = math.abs(time) end
                if not self._enabled then return end
                self._last_time = time; time = math.floor(time)
                local h = math.floor(time/3600); time = time - h*3600
                local m = math.floor(time/60); time = time - m*60; local s = math.round(time)
                local t = h > 0 and (h < 10 and "0"..h or h)..":" or ""
                t = t..(m < 10 and "0"..m or m)..":"..(s < 10 and "0"..s or s)
                self._timer_text:set_text(t)
            end
            HUDManager._hud_heist_timer = nil
            function HUDManager:_create_heist_timer()
                self._hud_heist_timer = HUDHeistTimer:new({})
            end
            function HUDManager:feed_heist_time(t)
                self._hud_heist_timer:set_time(t)
            end
        ''')

        mission_src = _read(ROOT / "lua" / "hud" / "mission.lua")
        self.assertIsNotNone(mission_src, "mission.lua must exist")
        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        lua.execute(mission_src)
        lua.execute('RequiredScript = "lib/managers/lootmanager"')
        lua.execute(mission_src)
        # These consumers have no native objective/corner source in this fixture.
        # Qualify combined opt-in fallback, not their positive-state rendering
        # (covered separately by their native-shaped integration suites).
        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        for module in ("objectives", "alerts", "assault"):
            lua.execute(_read(ROOT / "lua" / "hud" / (module + ".lua")))

        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_mission = true
            kyohud.settings.enable_objectives = true
            kyohud.settings.enable_alerts = true
            kyohud.settings.enable_assault = true
            kyohud.settings.enable_player = true
            kyohud.settings.enable_weapons = true
            kyohud.settings.enable_equipment = true
            kyohud.settings.enable_crew = true
            kyohud.settings.hud_scale = 1.0
            _G.panel_double:set_shape(0, 0, 1920, 1080)

            local sibling = _G.panel_double:panel({name="third_party_sentinel"})
            sibling:set_shape(100, 200, 150, 250)
            sibling:set_visible(true)
            _sibling_x_before = sibling:x()
            _sibling_y_before = sibling:y()
            _sibling_w_before = sibling:w()
            _sibling_h_before = sibling:h()
            _sibling_vis_before = sibling:visible()

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

            managers.player:_native_set_equipment('trip_mine',{3,2})
            managers.player:_native_set_equipment('doctor_bag',{1})
            managers.player._equipment.selected_index=1
            managers.player:_native_set_grenades('pocket',1,2)
            _native_set_projectile_tweak('pocket',{ability=true,base_cooldown=30})
            managers.player:_native_set_specials('cable_tie',{3})
            _game_clock:set_time(1000)
            managers.player:_native_set_replenish_timer(1017)

            local mgr = managers.hud
            mgr:_create_heist_timer({})
            mgr:feed_heist_time(300)

            local ACT = kyohud.hud.actors
            ACT:refresh_crew(mgr, 0)
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.runtime:update(mgr, 1.0, 0.05)

            local P = kyohud.hud.player
            local WEAP = kyohud.hud.weapons
            local E = kyohud.hud.equipment
            local C = kyohud.hud.crew
            local M = kyohud.hud.mission

            -- Execute the registered feed callback between recovery polls.
            mgr:feed_heist_time(301)
            dispatch(HUDManager, "feed_heist_time", mgr, 301)
            _only_mission_owns_native = true
            _mission_owner_count = 0
            for _, entry in ipairs(kyohud.hud.native_visibility._entries) do
                if entry.owner ~= M then _only_mission_owns_native = false end
                if entry.owner == M then _mission_owner_count = _mission_owner_count + 1 end
            end

            _p_verify = P and P:verify() or false
            _weap_verify = WEAP and WEAP:verify() or false
            _e_verify = E and E:verify() or false
            _c_verify = C and C:_verify_render() or false
            _m_verify = M and M:_verify_render() or false

            _timer_text = M and M._timer_prim and M._timer_prim:text() or nil
            _native_alpha = mgr._hud_heist_timer._timer_text:alpha()

            _m_root_before = M and M._root_panel or nil
            _timer_prim_before = M and M._timer_prim or nil

            kyohud.settings.enable_hud_foundation = false
            kyohud.hud.runtime:refresh_settings(mgr)

            _native_alpha_after_off = mgr._hud_heist_timer._timer_text:alpha()

            _sibling_x_off = sibling:x()
            _sibling_y_off = sibling:y()
            _sibling_w_off = sibling:w()
            _sibling_h_off = sibling:h()
            _sibling_vis_off = sibling:visible()
            _sibling_alive_off = alive(sibling)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._p_verify),
            "player:verify() must be true with mission enabled")
        self.assertTrue(bool(g._weap_verify),
            "weapons:verify() must be true with mission enabled")
        self.assertTrue(bool(g._e_verify),
            "equipment:verify() must be true with mission enabled")
        self.assertTrue(bool(g._c_verify),
            "crew:_verify_render() must be true with mission enabled")
        self.assertTrue(bool(g._m_verify),
            "mission:_verify_render() must be true with known source")
        self.assertEqual(g._timer_text, "05:01",
            "mission must consume the actual registered feed callback")
        self.assertIs(g._only_mission_owns_native, True,
            "missing objective/corner sources must not acquire native leaves")
        self.assertEqual(g._mission_owner_count, 1)
        self.assertAlmostEqual(float(g._native_alpha), 0.0, places=2,
            msg="native alpha must be acquired to 0 after successful render")
        self.assertIsNotNone(g._m_root_before,
            "mission root must exist before foundation off")
        self.assertIsNotNone(g._timer_prim_before,
            "mission timer primitive must exist before foundation off")
        self.assertAlmostEqual(float(g._native_alpha_after_off), 0.37, places=2,
            msg="native alpha 0.37 must be restored on foundation off")
        self.assertEqual(float(g._sibling_x_off), float(g._sibling_x_before),
            "third-party sibling x must be preserved after foundation off")
        self.assertEqual(float(g._sibling_y_off), float(g._sibling_y_before),
            "third-party sibling y must be preserved after foundation off")
        self.assertEqual(float(g._sibling_w_off), float(g._sibling_w_before),
            "third-party sibling w must be preserved after foundation off")
        self.assertEqual(float(g._sibling_h_off), float(g._sibling_h_before),
            "third-party sibling h must be preserved after foundation off")
        self.assertTrue(bool(g._sibling_vis_off),
            "third-party sibling must remain visible after foundation off")
        self.assertTrue(bool(g._sibling_alive_off),
            "third-party sibling must remain alive after foundation off")


if __name__ == "__main__":
    unittest.main()
