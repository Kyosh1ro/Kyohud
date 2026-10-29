"""LOT5 crew weapons slice -- remote weapon swap with same ammo tuple.

Scope: single test verifying equipped remote weapon swap preserves ammo tuple
and occupant token while updating weapon identity fields. Native APIs:
unit:inventory():equipped_selection(), :equipped_unit(), :unit_by_selection(index)
(HuskPlayerInventory); weapon:base():get_name_id(), :weapon_tweak_data().name_id;
PM:get_synced_ammo_info(peer_id) returns {[selection]={max_clip,current_clip,total_raw,max}};
PM:get_player_turret_for_peer(peer_id) indicates turret; no personal tuple while turret alive.

RED state: crew weapon capture and turret gating must exist in actors.lua.
Tests must fail with explicit messages.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hud_actors_crew import _lua

ROOT = Path(__file__).resolve().parents[1]


class CrewWeaponsRemoteSwapTests(unittest.TestCase):
    """RED: remote weapon swap preserves ammo tuple and occupant token.

    Setup: localpeer1, remotepeer2 criminals live unit slot2/panel_peer2.
    Remote inventory selected1 equipped gunA, unit_by_selection1 same gunA;
    gunA base id gun_a name_id wpn_a; gunB base gun_b name wpn_b; separate
    alive units. PM native-shaped _global.synced_ammo_info[2][1]={30,7,67,120},
    getter and turret getter(nil initially). refresh_crew0 then assert entry.weapon
    table {selection_index=1,weapon_id="gun_a",name_id="wpn_a",unit_id numeric,
    ammo={max_clip=30,current_clip=7,total_raw=67,reserve=60,max=120,
    provenance="network_synced"}}. No mode/ALT promised. Swap inventory
    equipped_unit and unit_by_selection1 to gunB (same actor/unit, SAME tuple);
    refresh_crew .5 requires gun_b/wpn_b and new weapon.unit_id, token occupant
    unchanged. Set turret alive; refresh_crew1 must have weapon nil (no personal
    attribution); remove turret and replace ammo tuple {30,0,60,120}; refresh_crew1.5
    recovers gunB current_clip0/reserve60. Mutate snapshot nested ammo.reserve then
    getter WITHOUT refresh ensure detached before later transitions. Fail explicitly
    if weapon missing before deref.
    """

    def test_remote_weapon_swap_same_ammo_tuple(self):
        """Remote weapon swap: same actor/unit, same ammo tuple, new weapon identity.

        Initial: gunA equipped, ammo tuple {30,7,67,120}. refresh_crew0: entry.weapon
        has selection_index=1, weapon_id="gun_a", name_id="wpn_a", numeric unit_id,
        ammo.max_clip=30, ammo.current_clip=7, ammo.total_raw=67, ammo.reserve=60,
        ammo.max=120, ammo.provenance="network_synced".

        Swap to gunB (same actor/unit): refresh_crew.5: weapon_id="gun_b", name_id="wpn_b",
        NEW unit_id, occupant_token unchanged, same ammo tuple.

        Set turret alive: refresh_crew1: weapon nil (no personal attribution).
        Remove turret, replace ammo tuple {30,0,60,120}: refresh_crew1.5: weapon
        current_clip=0, reserve=60.

        Mutate snapshot nested ammo.reserve then getter WITHOUT refresh: must be
        detached (later getter returns original value, not mutated).
        """
        setup = r'''
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            local remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
            session:_register_peer(remote_peer)

            local unitA = {_alive = true, _label = "unitA", _id = 100}
            _G._unitA = unitA

            managers.criminals:_set_character(1, {
                name = "spanish",
                taken = true,
                unit = unitA,
                peer_id = 2,
                data = {ai = false, panel_id = 2},
            })
            remote_peer._unit = unitA

            local mgr = managers.hud
            mgr._teammate_panels[2] = {
                _peer_id = 2,
                _ai = false,
            }
            mgr._hud = mgr._hud or {}
            mgr._hud.teammate_panels_data = {}
            for i = 1, 4 do
                mgr._hud.teammate_panels_data[i] = {taken = true}
            end

            local gunA = {_alive = true, _label = "gunA"}
            local gunB = {_alive = true, _label = "gunB"}
            _G._gunA = gunA
            _G._gunB = gunB

            local baseA = {
                get_name_id = function(self) return "gun_a" end,
                weapon_tweak_data = function(self)
                    return {name_id = "wpn_a"}
                end,
            }
            local baseB = {
                get_name_id = function(self) return "gun_b" end,
                weapon_tweak_data = function(self)
                    return {name_id = "wpn_b"}
                end,
            }

            gunA.base = function(self) return baseA end
            gunB.base = function(self) return baseB end

            local inventory = {
                _equipped_selection = 1,
                _equipped_unit = gunA,
                _units = {[1] = gunA},
                equipped_selection = function(self) return self._equipped_selection end,
                equipped_unit = function(self) return self._equipped_unit end,
                unit_by_selection = function(self, index) return self._units[index] end,
            }
            unitA.inventory = function(self) return inventory end
            _G._inventory = inventory

            managers.player = managers.player or {}
            managers.player._global = managers.player._global or {}
            managers.player._global.synced_ammo_info = {}
            managers.player._global.synced_ammo_info[2] = {}
            managers.player._global.synced_ammo_info[2][1] = {30, 7, 67, 120}

            managers.player.get_synced_ammo_info = function(self, peer_id)
                return self._global.synced_ammo_info[peer_id]
            end

            managers.player._turret_for_peer = nil
            managers.player.get_player_turret_for_peer = function(self, peer_id)
                return self._turret_for_peer
            end
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute('''
            local ACT = kyohud.hud.actors
            if not ACT.refresh_crew then
                _api_missing = "refresh_crew"
                return
            end
            if not ACT.get_crew_snapshot then
                _api_missing = "get_crew_snapshot"
                return
            end
            _api_missing = false

            local mgr = managers.hud

            ACT:refresh_crew(mgr, 0)
            local snap0 = ACT:get_crew_snapshot()

            _entry0 = nil
            _token0 = nil
            _weapon0 = nil
            _selection0 = nil
            _weapon_id0 = nil
            _name_id0 = nil
            _unit_id0 = nil
            _ammo0 = nil
            _max_clip0 = nil
            _current_clip0 = nil
            _total_raw0 = nil
            _reserve0 = nil
            _max0 = nil
            _provenance0 = nil
            for _, e in ipairs(snap0) do
                if e.peer_id == 2 then
                    _entry0 = e
                    _token0 = e.occupant_token
                    _weapon0 = e.weapon
                    if _weapon0 then
                        _selection0 = _weapon0.selection_index
                        _weapon_id0 = _weapon0.weapon_id
                        _name_id0 = _weapon0.name_id
                        _unit_id0 = _weapon0.unit_id
                        _ammo0 = _weapon0.ammo
                        if _ammo0 then
                            _max_clip0 = _ammo0.max_clip
                            _current_clip0 = _ammo0.current_clip
                            _total_raw0 = _ammo0.total_raw
                            _reserve0 = _ammo0.reserve
                            _max0 = _ammo0.max
                            _provenance0 = _ammo0.provenance
                        end
                    end
                    break
                end
            end

            _G._inventory._equipped_unit = _G._gunB
            _G._inventory._units[1] = _G._gunB

            ACT:refresh_crew(mgr, 0.5)
            local snap05 = ACT:get_crew_snapshot()

            _entry05 = nil
            _token05 = nil
            _weapon05 = nil
            _selection05 = nil
            _weapon_id05 = nil
            _name_id05 = nil
            _unit_id05 = nil
            _ammo05 = nil
            _max_clip05 = nil
            _current_clip05 = nil
            _total_raw05 = nil
            _reserve05 = nil
            _max05 = nil
            _provenance05 = nil
            for _, e in ipairs(snap05) do
                if e.peer_id == 2 then
                    _entry05 = e
                    _token05 = e.occupant_token
                    _weapon05 = e.weapon
                    if _weapon05 then
                        _selection05 = _weapon05.selection_index
                        _weapon_id05 = _weapon05.weapon_id
                        _name_id05 = _weapon05.name_id
                        _unit_id05 = _weapon05.unit_id
                        _ammo05 = _weapon05.ammo
                        if _ammo05 then
                            _max_clip05 = _ammo05.max_clip
                            _current_clip05 = _ammo05.current_clip
                            _total_raw05 = _ammo05.total_raw
                            _reserve05 = _ammo05.reserve
                            _max05 = _ammo05.max
                            _provenance05 = _ammo05.provenance
                        end
                    end
                    break
                end
            end

            _token_same = (_token05 == _token0)
            _unit_id_changed = (_unit_id05 ~= _unit_id0)

            managers.player._turret_for_peer = {_alive = true, _label = "turret"}
            ACT:refresh_crew(mgr, 1.0)
            local snap1 = ACT:get_crew_snapshot()

            _weapon1 = nil
            for _, e in ipairs(snap1) do
                if e.peer_id == 2 then
                    _weapon1 = e.weapon
                    break
                end
            end
            _weapon_nil_during_turret = (_weapon1 == nil)

            managers.player._turret_for_peer = nil
            managers.player._global.synced_ammo_info[2][1] = {30, 0, 60, 120}
            ACT:refresh_crew(mgr, 1.5)
            local snap15 = ACT:get_crew_snapshot()

            _weapon15 = nil
            _current_clip15 = nil
            _reserve15 = nil
            for _, e in ipairs(snap15) do
                if e.peer_id == 2 then
                    _weapon15 = e.weapon
                    if _weapon15 and _weapon15.ammo then
                        _current_clip15 = _weapon15.ammo.current_clip
                        _reserve15 = _weapon15.ammo.reserve
                    end
                    break
                end
            end

            local snap_check = ACT:get_crew_snapshot()
            _snap_check_weapon = nil
            _snap_check_reserve_orig = nil
            for _, e in ipairs(snap_check) do
                if e.peer_id == 2 then
                    _snap_check_weapon = e.weapon
                    if _snap_check_weapon and _snap_check_weapon.ammo then
                        _snap_check_reserve_orig = _snap_check_weapon.ammo.reserve
                    end
                    break
                end
            end

            if _snap_check_weapon and _snap_check_weapon.ammo then
                _snap_check_weapon.ammo.reserve = 9999
            end

            local snap_check2 = ACT:get_crew_snapshot()
            _snap_check2_reserve = nil
            for _, e in ipairs(snap_check2) do
                if e.peer_id == 2 then
                    if e.weapon and e.weapon.ammo then
                        _snap_check2_reserve = e.weapon.ammo.reserve
                    end
                    break
                end
            end
            _detached = (_snap_check2_reserve == _snap_check_reserve_orig)

            managers.player.get_player_turret_for_peer = nil
            ACT:refresh_crew(mgr, 2.0)
            local snap2 = ACT:get_crew_snapshot()

            _weapon2 = nil
            _weapon_id2 = nil
            _name_id2 = nil
            _unit_id2 = nil
            _ammo2 = nil
            _has_weapon_entry2 = false
            for _, e in ipairs(snap2) do
                if e.peer_id == 2 then
                    _weapon2 = e.weapon
                    if _weapon2 then
                        _has_weapon_entry2 = true
                        _weapon_id2 = _weapon2.weapon_id
                        _name_id2 = _weapon2.name_id
                        _unit_id2 = _weapon2.unit_id
                        _ammo2 = _weapon2.ammo
                    end
                    break
                end
            end
            _ammo2_is_nil = (_ammo2 == nil)
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertIsNotNone(g._entry0,
            "RED: crew entry must exist for peer2 after refresh_crew(0)")
        self.assertIsNotNone(g._weapon0,
            "RED: weapon must exist before deref")
        self.assertEqual(float(g._selection0), 1.0,
            "RED: weapon.selection_index must be 1")
        self.assertEqual(g._weapon_id0, "gun_a",
            "RED: weapon.weapon_id must be 'gun_a'")
        self.assertEqual(g._name_id0, "wpn_a",
            "RED: weapon.name_id must be 'wpn_a'")
        self.assertIsNotNone(g._unit_id0,
            "RED: weapon.unit_id must be numeric")
        self.assertEqual(float(g._max_clip0), 30.0,
            "RED: ammo.max_clip must be 30")
        self.assertEqual(float(g._current_clip0), 7.0,
            "RED: ammo.current_clip must be 7")
        self.assertEqual(float(g._total_raw0), 67.0,
            "RED: ammo.total_raw must be 67")
        self.assertEqual(float(g._reserve0), 60.0,
            "RED: ammo.reserve must be 60")
        self.assertEqual(float(g._max0), 120.0,
            "RED: ammo.max must be 120")
        self.assertEqual(g._provenance0, "network_synced",
            "RED: ammo.provenance must be 'network_synced'")

        self.assertIsNotNone(g._entry05,
            "RED: crew entry must exist for peer2 after weapon swap")
        self.assertIsNotNone(g._weapon05,
            "RED: weapon must exist after swap before deref")
        self.assertEqual(g._weapon_id05, "gun_b",
            "RED: weapon.weapon_id must be 'gun_b' after swap")
        self.assertEqual(g._name_id05, "wpn_b",
            "RED: weapon.name_id must be 'wpn_b' after swap")
        self.assertIsNotNone(g._unit_id05,
            "RED: weapon.unit_id must be numeric after swap")
        self.assertIs(g._token_same, True,
            "RED: occupant_token must be unchanged after weapon swap (same actor/unit)")
        self.assertIs(g._unit_id_changed, True,
            "RED: weapon.unit_id must change after weapon swap (different weapon unit)")
        self.assertEqual(float(g._max_clip05), 30.0,
            "RED: ammo.max_clip must remain 30 after swap (same tuple)")
        self.assertEqual(float(g._current_clip05), 7.0,
            "RED: ammo.current_clip must remain 7 after swap (same tuple)")
        self.assertEqual(float(g._total_raw05), 67.0,
            "RED: ammo.total_raw must remain 67 after swap (same tuple)")
        self.assertEqual(float(g._reserve05), 60.0,
            "RED: ammo.reserve must remain 60 after swap (same tuple)")
        self.assertEqual(float(g._max05), 120.0,
            "RED: ammo.max must remain 120 after swap (same tuple)")
        self.assertEqual(g._provenance05, "network_synced",
            "RED: ammo.provenance must remain 'network_synced' after swap")

        self.assertIs(g._weapon_nil_during_turret, True,
            "RED: weapon must be nil while turret alive (no personal attribution)")

        self.assertIsNotNone(g._weapon15,
            "RED: weapon must exist after turret removal and ammo tuple replacement")
        self.assertEqual(float(g._current_clip15), 0.0,
            "RED: ammo.current_clip must be 0 after tuple replacement")
        self.assertEqual(float(g._reserve15), 60.0,
            "RED: ammo.reserve must be 60 after tuple replacement")

        self.assertIs(g._detached, True,
            "RED: get_crew_snapshot must return detached deep copy (mutating snapshot must not affect later getter)")

        self.assertIs(g._ammo2_is_nil, True,
            "RED: ammo must be nil when get_player_turret_for_peer unavailable (inability to rule out turret is not proof of personal ammo source)")


if __name__ == "__main__":
    unittest.main()
