"""LOT5 crew events -- genuine class setter transitions and registry replacement.

Scope: two tests verifying equipment/ammo transitions via genuine PM class setters
(set_synced_deployable_equipment and set_synced_ammo_info) and retained registry
peer replacement qualification. Tests execute actors.lua real chunk in both
PlayerManager and HUDManager contexts (both orders) with double-load guards.

Native signatures traced:
- PlayerManager:set_synced_deployable_equipment(peer, deployable, amount)
  First arg is peer OBJECT (calls peer:id() internally)
- PlayerManager:set_synced_ammo_info(peer_id, selection_index, max_clip, current_clip, current_left, max)
  First arg is peer_id integer

RED state: equipment/ammo event capture and poll gate bypass via genuine setters
must exist. Tests must fail with explicit messages.
"""
from pathlib import Path
import sys
import unittest

from lupa.luajit21 import LuaRuntime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hud_actors import STUBS
from test_hud_actors_crew import (
    NATIVE_CRIMINALS_FIXTURE,
    NATIVE_SESSION_FIXTURE,
    NATIVE_LOCALIZATION_FIXTURE,
    _read,
)

ROOT = Path(__file__).resolve().parents[1]
ACTORS_PATH = ROOT / "lua" / "hud" / "actors.lua"


def _fresh_lua(setup=None):
    """Construct fresh LuaRuntime with STUBS+fixtures, load actors.lua once."""
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    # Override STUBS recording-only Hooks with native-shaped wrapping versions
    # that actually call registered callbacks around the original method
    lua.execute(r'''
        local _original_post = Hooks.PostHook
        local _original_pre = Hooks.PreHook

        function Hooks:PostHook(class, method, id, fn)
            _original_post(self, class, method, id, fn)
            if type(class) ~= "table" then return end
            if type(class[method]) ~= "function" then return end
            local original = class[method]
            class[method] = function(self, ...)
                local args = {...}
                local nargs = select("#", ...)
                local result = {original(self, unpack(args, 1, nargs))}
                fn(self, unpack(args, 1, nargs))
                return unpack(result)
            end
        end

        function Hooks:PreHook(class, method, id, fn)
            _original_pre(self, class, method, id, fn)
            if type(class) ~= "table" then return end
            if type(class[method]) ~= "function" then return end
            local original = class[method]
            class[method] = function(self, ...)
                local args = {...}
                local nargs = select("#", ...)
                fn(self, unpack(args, 1, nargs))
                return original(self, unpack(args, 1, nargs))
            end
        end
    ''')
    lua.execute("HUDManager.PLAYER_PANEL = 4")
    lua.execute(NATIVE_CRIMINALS_FIXTURE)
    lua.execute(NATIVE_SESSION_FIXTURE)
    lua.execute(NATIVE_LOCALIZATION_FIXTURE)
    if setup:
        lua.execute(setup)
    actors_src = _read(ACTORS_PATH)
    if actors_src:
        lua.globals().RequiredScript = "lib/managers/hudmanagerpd2"
        lua.execute(actors_src)
        lua.globals().RequiredScript = "lib/managers/playermanager"
        lua.execute(actors_src)
    return lua, actors_src is not None


class GenuineSetterPollGateTests(unittest.TestCase):
    """RED: genuine class setter transitions bypass poll gate for immediate snapshot.

    Test 1: Equipment - call PM:set_synced_deployable_equipment(peer_obj, "ammo_bag", 2)
    then get_crew_snapshot() immediately (no manual refresh_crew) must reflect accepted
    publication despite .5 poll gate.

    Test 2: Ammo - call PM:set_synced_ammo_info(peer_id=2, selection=1, max_clip=30,
    current_clip=7, current_left=67, max=120) then get_crew_snapshot() immediately must
    reflect accepted publication despite .5 poll gate.

    Both tests execute actors.lua in PlayerManager THEN HUDManager contexts (and vice
    versa) with double-load guards verifying no duplicate hooks.
    """

    def _run_equipment_order(self, order_name, contexts):
        """Run equipment test for a single context order with fresh Lua."""
        setup = r'''
            local Peer = getmetatable(managers.network:session():local_peer())
            local local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local Session = getmetatable(managers.network:session())
            local session = Session:new(local_peer)
            session:_register_peer(local_peer)
            managers.network._session = session

            local remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
            session:_register_peer(remote_peer)
            _G._remote_peer = remote_peer

            local unitA = {_alive = true, _label = "unitA", _id = 100}

            managers.criminals:_set_character(1, {
                name = "american",
                taken = true,
                unit = nil,
                peer_id = 1,
                data = {ai = false, panel_id = 4},
            })
            managers.criminals:_set_character(2, {
                name = "spanish",
                taken = true,
                unit = unitA,
                peer_id = 2,
                data = {ai = false, panel_id = 2},
            })

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

            local PlayerManager = {}
            PlayerManager.__index = PlayerManager
            managers.player = setmetatable({
                _global = {
                    synced_deployables = {},
                    synced_cable_ties = {},
                    synced_grenades = {},
                },
            }, PlayerManager)

            function managers.player:get_synced_deployable_equipment(peer_id)
                return self._global.synced_deployables[peer_id]
            end
            function managers.player:get_synced_cable_ties(peer_id)
                return self._global.synced_cable_ties[peer_id]
            end
            function managers.player:get_synced_grenades(peer_id)
                return self._global.synced_grenades[peer_id]
            end

            tweak_data = tweak_data or {}
            tweak_data.equipments = tweak_data.equipments or {}
            tweak_data.equipments.ammo_bag = {text_id = "ammo_bag_name"}

            function HUDManager:set_deployable_equipment(panel_id, data)
                if not self._teammate_panels[panel_id] then
                    self._teammate_panels[panel_id] = {}
                end
                self._teammate_panels[panel_id].deployable_equipment = data
            end

            function PlayerManager:set_synced_deployable_equipment(peer, deployable, amount)
                local peer_id = peer:id()
                self._global.synced_deployables[peer_id] = {
                    deployable = deployable,
                    amount = amount
                }
                local character_data = managers.criminals:character_data_by_peer_id(peer_id)
                if character_data and character_data.panel_id then
                    managers.hud:set_deployable_equipment(character_data.panel_id, {
                        icon = tweak_data.equipments[deployable].icon,
                        amount = amount
                    })
                end
            end

            local CriminalsManager = getmetatable(managers.criminals)
            function CriminalsManager:character_data_by_peer_id(peer_id)
                for _, rec in ipairs(self:characters()) do
                    if rec.peer_id == peer_id then return rec.data end
                end
                return nil
            end
        '''
        lua, ok = _fresh_lua(setup=setup)
        if not ok:
            return None, "RED: lua/hud/actors.lua must exist (production chunk missing)"

        actors_src = _read(ACTORS_PATH)
        if not actors_src:
            return None, "RED: actors.lua source not found"

        lua.execute(f'_order_name = "{order_name}"')

        for ctx in contexts:
            lua.globals().RequiredScript = ctx
            lua.execute(actors_src)

        lua.execute('_hooks_after_initial = #Hooks._all')

        for ctx in contexts:
            lua.globals().RequiredScript = ctx
            lua.execute(actors_src)

        lua.execute('_hooks_after_reload = #Hooks._all')

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

            _snap0_len = #snap0
            _human0 = nil
            for _, e in ipairs(snap0) do
                if e.peer_id == 2 then _human0 = e; break end
            end
            _human0_eq = _human0 and _human0.equipment or nil
            _human0_deploy = _human0_eq and _human0_eq.deployable or nil

            managers.player:set_synced_deployable_equipment(_G._remote_peer, "ammo_bag", 2)

            local snap1 = ACT:get_crew_snapshot()
            _snap1_len = #snap1
            _human1 = nil
            for _, e in ipairs(snap1) do
                if e.peer_id == 2 then _human1 = e; break end
            end
            _human1_eq = _human1 and _human1.equipment or nil
            _human1_deploy = _human1_eq and _human1_eq.deployable or nil
            _human1_deploy_id = _human1_deploy and _human1_deploy.id or nil
            _human1_deploy_amount = _human1_deploy and _human1_deploy.amount or nil
            _human1_deploy_name_id = _human1_deploy and _human1_deploy.name_id or nil

            _hooks_delta = _hooks_after_reload - _hooks_after_initial
        ''')
        return lua, None

    def test_equipment_genuine_setter_immediate_snapshot_both_context_orders(self):
        """Equipment: genuine setter -> immediate snapshot reflects publication.

        Setup: localpeer1, remotepeer2 slot2 ai=false with unit. Criminals record
        peer_id=2 panel_id=2. PM native-shaped _global.synced_deployables initially
        empty. tweak_data.equipments.ammo_bag.text_id="ammo_bag_name".

        Execute actors.lua in BOTH context orders (PM then HUD, and HUD then PM)
        with double-load guards. refresh_crew(mgr, 0) initializes roster.

        Call genuine PM:set_synced_deployable_equipment(remote_peer, "ammo_bag", 2).
        This native setter stores in _global.synced_deployables[2] AND calls
        managers.hud:set_deployable_equipment(panel_id, data).

        Immediately call get_crew_snapshot() WITHOUT calling refresh_crew again.
        Snapshot must reflect equipment.deployable={id="ammo_bag", amount=2,
        name_id="ammo_bag_name"} despite .5 poll gate not elapsed.

        Verify both context orders produce same result and no duplicate hooks.
        """
        for order_name, contexts in [
            ("PM_then_HUD", ["lib/managers/playermanager", "lib/managers/hudmanagerpd2"]),
            ("HUD_then_PM", ["lib/managers/hudmanagerpd2", "lib/managers/playermanager"]),
        ]:
            with self.subTest(order=order_name):
                lua, err = self._run_equipment_order(order_name, contexts)
                if err:
                    self.fail(err)
                    return

                g = lua.globals()
                if g._api_missing:
                    self.fail(f"RED: ACT:{g._api_missing} must exist (order={order_name})")
                    return

                self.assertEqual(float(g._snap0_len), 1.0,
                    f"RED: initial snapshot must have 1 entry (order={order_name})")
                self.assertIsNone(g._human0_deploy,
                    f"RED: initial equipment.deployable must be nil (order={order_name})")

                self.assertEqual(float(g._snap1_len), 1.0,
                    f"RED: after setter snapshot must have 1 entry (order={order_name})")
                self.assertIsNotNone(g._human1_deploy,
                    f"RED: after genuine setter, equipment.deployable must be present (order={order_name})")
                if g._human1_deploy:
                    self.assertEqual(g._human1_deploy_id, "ammo_bag",
                        f"RED: deployable.id must be 'ammo_bag' (order={order_name})")
                    self.assertEqual(float(g._human1_deploy_amount), 2.0,
                        f"RED: deployable.amount must be 2 (order={order_name})")
                    self.assertEqual(g._human1_deploy_name_id, "ammo_bag_name",
                        f"RED: deployable.name_id must be 'ammo_bag_name' (order={order_name})")

                self.assertEqual(float(g._hooks_delta), 0.0,
                    f"RED: double-load must not install duplicate hooks (order={order_name})")

    def _run_ammo_order(self, order_name, contexts):
        """Run ammo test for a single context order with fresh Lua."""
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

            managers.criminals:_set_character(1, {
                name = "american",
                taken = true,
                unit = nil,
                peer_id = 1,
                data = {ai = false, panel_id = 4},
            })
            managers.criminals:_set_character(2, {
                name = "spanish",
                taken = true,
                unit = unitA,
                peer_id = 2,
                data = {ai = false, panel_id = 2},
            })

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
            local baseA = {
                get_name_id = function(self) return "gun_a" end,
                weapon_tweak_data = function(self)
                    return {name_id = "wpn_a"}
                end,
            }
            gunA.base = function(self) return baseA end

            local inventory = {
                _equipped_selection = 1,
                _equipped_unit = gunA,
                _units = {[1] = gunA},
                equipped_selection = function(self) return self._equipped_selection end,
                equipped_unit = function(self) return self._equipped_unit end,
                unit_by_selection = function(self, index) return self._units[index] end,
            }
            unitA.inventory = function(self) return inventory end

            local PlayerManager = {}
            PlayerManager.__index = PlayerManager
            managers.player = setmetatable({
                _global = {
                    synced_ammo_info = {},
                },
                _turret_for_peer = nil,
            }, PlayerManager)

            function managers.player:get_synced_ammo_info(peer_id)
                return self._global.synced_ammo_info[peer_id]
            end

            function managers.player:get_player_turret_for_peer(peer_id)
                return self._turret_for_peer
            end

            function HUDManager:set_teammate_ammo_amount(panel_id, selection_index, max_clip, current_clip, current_left, max)
                if not self._teammate_panels[panel_id] then
                    self._teammate_panels[panel_id] = {}
                end
                self._teammate_panels[panel_id].ammo_data = {
                    selection_index = selection_index,
                    max_clip = max_clip,
                    current_clip = current_clip,
                    current_left = current_left,
                    max = max
                }
            end

            function PlayerManager:set_synced_ammo_info(peer_id, selection_index, max_clip, current_clip, current_left, max)
                self._global.synced_ammo_info[peer_id] = self._global.synced_ammo_info[peer_id] or {}
                self._global.synced_ammo_info[peer_id][selection_index] = {
                    max_clip,
                    current_clip,
                    current_left,
                    max
                }
                local character = managers.criminals:character_by_peer_id(peer_id)
                if character and character.taken then
                    local character_data = character.data
                    if character_data and character_data.panel_id then
                        managers.hud:set_teammate_ammo_amount(character_data.panel_id, selection_index, max_clip, current_clip, current_left, max)
                    end
                end
            end

            local CriminalsManager = getmetatable(managers.criminals)
            function CriminalsManager:character_by_peer_id(peer_id)
                for _, rec in ipairs(self:characters()) do
                    if rec.peer_id == peer_id then return rec end
                end
                return nil
            end
        '''
        lua, ok = _fresh_lua(setup=setup)
        if not ok:
            return None, "RED: lua/hud/actors.lua must exist (production chunk missing)"

        actors_src = _read(ACTORS_PATH)
        if not actors_src:
            return None, "RED: actors.lua source not found"

        lua.execute(f'_order_name = "{order_name}"')

        for ctx in contexts:
            lua.globals().RequiredScript = ctx
            lua.execute(actors_src)

        lua.execute('_hooks_after_initial = #Hooks._all')

        for ctx in contexts:
            lua.globals().RequiredScript = ctx
            lua.execute(actors_src)

        lua.execute('_hooks_after_reload = #Hooks._all')

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

            _snap0_len = #snap0
            _human0 = nil
            for _, e in ipairs(snap0) do
                if e.peer_id == 2 then _human0 = e; break end
            end
            _human0_weapon = _human0 and _human0.weapon or nil
            _human0_ammo0 = _human0_weapon and _human0_weapon.ammo or nil

            managers.player:set_synced_ammo_info(2, 1, 30, 7, 67, 120)

            local snap1 = ACT:get_crew_snapshot()
            _snap1_len = #snap1
            _human1 = nil
            for _, e in ipairs(snap1) do
                if e.peer_id == 2 then _human1 = e; break end
            end
            _human1_weapon = _human1 and _human1.weapon or nil
            _human1_ammo = _human1_weapon and _human1_weapon.ammo or nil
            _max_clip = _human1_ammo and _human1_ammo.max_clip or nil
            _current_clip = _human1_ammo and _human1_ammo.current_clip or nil
            _total_raw = _human1_ammo and _human1_ammo.total_raw or nil
            _reserve = _human1_ammo and _human1_ammo.reserve or nil
            _max_total = _human1_ammo and _human1_ammo.max or nil
            _provenance = _human1_ammo and _human1_ammo.provenance or nil

            _hooks_delta = _hooks_after_reload - _hooks_after_initial
        ''')
        return lua, None

    def test_ammo_genuine_setter_immediate_snapshot_both_context_orders(self):
        """Ammo: genuine setter -> immediate snapshot reflects publication.

        Setup: localpeer1, remotepeer2 slot2 ai=false with unit, inventory equipped1
        gunA, unit_by_selection1 gunA. gunA base id gun_a name_id wpn_a. PM native-shaped
        _global.synced_ammo_info initially empty.

        Execute actors.lua in BOTH context orders with double-load guards.
        refresh_crew(mgr, 0) initializes roster.

        Call genuine PM:set_synced_ammo_info(peer_id=2, selection_index=1, max_clip=30,
        current_clip=7, current_left=67, max=120). This native setter stores in
        _global.synced_ammo_info[2][1] AND calls managers.hud:set_teammate_ammo_amount.

        Immediately call get_crew_snapshot() WITHOUT calling refresh_crew again.
        Snapshot must reflect weapon.ammo={max_clip=30, current_clip=7, total_raw=67,
        reserve=60, max=120, provenance="network_synced"} despite .5 poll gate.

        Verify both context orders produce same result and no duplicate hooks.
        """
        for order_name, contexts in [
            ("PM_then_HUD", ["lib/managers/playermanager", "lib/managers/hudmanagerpd2"]),
            ("HUD_then_PM", ["lib/managers/hudmanagerpd2", "lib/managers/playermanager"]),
        ]:
            with self.subTest(order=order_name):
                lua, err = self._run_ammo_order(order_name, contexts)
                if err:
                    self.fail(err)
                    return

                g = lua.globals()
                if g._api_missing:
                    self.fail(f"RED: ACT:{g._api_missing} must exist (order={order_name})")
                    return

                self.assertEqual(float(g._snap0_len), 1.0,
                    f"RED: initial snapshot must have 1 entry (order={order_name})")
                self.assertIsNone(g._human0_ammo0,
                    f"RED: initial weapon.ammo must be nil (order={order_name})")

                self.assertEqual(float(g._snap1_len), 1.0,
                    f"RED: after setter snapshot must have 1 entry (order={order_name})")
                self.assertIsNotNone(g._human1_ammo,
                    f"RED: after genuine setter, weapon.ammo must be present (order={order_name})")
                if g._human1_ammo:
                    self.assertEqual(float(g._max_clip), 30.0,
                        f"RED: ammo.max_clip must be 30 (order={order_name})")
                    self.assertEqual(float(g._current_clip), 7.0,
                        f"RED: ammo.current_clip must be 7 (order={order_name})")
                    self.assertEqual(float(g._total_raw), 67.0,
                        f"RED: ammo.total_raw must be 67 (order={order_name})")
                    self.assertEqual(float(g._reserve), 60.0,
                        f"RED: ammo.reserve must be 60 (order={order_name})")
                    self.assertEqual(float(g._max_total), 120.0,
                        f"RED: ammo.max must be 120 (order={order_name})")
                    self.assertEqual(g._provenance, "network_synced",
                        f"RED: ammo.provenance must be 'network_synced' (order={order_name})")

                self.assertEqual(float(g._hooks_delta), 0.0,
                    f"RED: double-load must not install duplicate hooks (order={order_name})")


class RetainedRegistryPeerReplacementTests(unittest.TestCase):
    """RED: retained registry peer replacement qualification.

    Fresh genuine event with identical values restores after owner invalidation,
    while session replacement retaining same peer object and PM record must not
    inherit old channel.
    """

    def test_fresh_genuine_event_restores_after_owner_invalidation(self):
        """Fresh genuine event with identical values restores after owner invalidation.

        Setup: human peer2 with equipment registry published (deployable ammo_bag
        amount=2). refresh_crew(0) obtains it. Replace session peer object for same
        id=2 (new Peer table, same id). PM registry RETAINED IDENTICALLY.
        refresh_crew(.5) clears old published equipment (owner invalidated).

        Dispatch fresh genuine event: PM:set_synced_deployable_equipment(new_peer,
        "ammo_bag", 2) with IDENTICAL values. refresh_crew(1) must restore
        equipment.deployable={id="ammo_bag", amount=2} via new genuine publication.
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
            _G._remote_peer_old = remote_peer

            local unitA = {_alive = true, _label = "unitA", _id = 100}

            managers.criminals:_set_character(1, {
                name = "american",
                taken = true,
                unit = nil,
                peer_id = 1,
                data = {ai = false, panel_id = 4},
            })
            managers.criminals:_set_character(2, {
                name = "spanish",
                taken = true,
                unit = unitA,
                peer_id = 2,
                data = {ai = false, panel_id = 2},
            })

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

            local PlayerManager = {}
            PlayerManager.__index = PlayerManager
            managers.player = setmetatable({
                _global = {
                    synced_deployables = {
                        [2] = {deployable = "ammo_bag", amount = 2}
                    },
                    synced_cable_ties = {},
                    synced_grenades = {},
                },
            }, PlayerManager)

            function managers.player:get_synced_deployable_equipment(peer_id)
                return self._global.synced_deployables[peer_id]
            end
            function managers.player:get_synced_cable_ties(peer_id)
                return self._global.synced_cable_ties[peer_id]
            end
            function managers.player:get_synced_grenades(peer_id)
                return self._global.synced_grenades[peer_id]
            end

            tweak_data = tweak_data or {}
            tweak_data.equipments = tweak_data.equipments or {}
            tweak_data.equipments.ammo_bag = {text_id = "ammo_bag_name"}

            function HUDManager:set_deployable_equipment(panel_id, data)
                if not self._teammate_panels[panel_id] then
                    self._teammate_panels[panel_id] = {}
                end
                self._teammate_panels[panel_id].deployable_equipment = data
            end

            function PlayerManager:set_synced_deployable_equipment(peer, deployable, amount)
                local peer_id = peer:id()
                self._global.synced_deployables[peer_id] = {
                    deployable = deployable,
                    amount = amount
                }
                local character_data = managers.criminals:character_data_by_peer_id(peer_id)
                if character_data and character_data.panel_id then
                    managers.hud:set_deployable_equipment(character_data.panel_id, {
                        icon = tweak_data.equipments[deployable].icon,
                        amount = amount
                    })
                end
            end

            local CriminalsManager = getmetatable(managers.criminals)
            function CriminalsManager:character_data_by_peer_id(peer_id)
                for _, rec in ipairs(self:characters()) do
                    if rec.peer_id == peer_id then return rec.data end
                end
                return nil
            end
        '''
        lua, ok = _fresh_lua(setup=setup)
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

            _snap0_len = #snap0
            _human0 = nil
            for _, e in ipairs(snap0) do
                if e.peer_id == 2 then _human0 = e; break end
            end
            _human0_eq = _human0 and _human0.equipment or nil
            _human0_deploy = _human0_eq and _human0_eq.deployable or nil
            _human0_deploy_id = _human0_deploy and _human0_deploy.id or nil

            local Peer = getmetatable(managers.network:session():local_peer())
            local Session = getmetatable(managers.network:session())
            local session = managers.network:session()

            local new_remote_peer = Peer:new(2, "AlPhA", 5, 0, nil)
            session._peers[2] = new_remote_peer
            _G._remote_peer_new = new_remote_peer

            ACT:refresh_crew(mgr, 0.5)
            local snap1 = ACT:get_crew_snapshot()

            _snap1_len = #snap1
            _human1 = nil
            for _, e in ipairs(snap1) do
                if e.peer_id == 2 then _human1 = e; break end
            end
            _human1_eq = _human1 and _human1.equipment or nil
            _human1_deploy = _human1_eq and _human1_eq.deployable or nil

            managers.player:set_synced_deployable_equipment(_G._remote_peer_new, "ammo_bag", 2)

            ACT:refresh_crew(mgr, 1)
            local snap2 = ACT:get_crew_snapshot()

            _snap2_len = #snap2
            _human2 = nil
            for _, e in ipairs(snap2) do
                if e.peer_id == 2 then _human2 = e; break end
            end
            _human2_eq = _human2 and _human2.equipment or nil
            _human2_deploy = _human2_eq and _human2_eq.deployable or nil
            _human2_deploy_id = _human2_deploy and _human2_deploy.id or nil
            _human2_deploy_amount = _human2_deploy and _human2_deploy.amount or nil
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertEqual(float(g._snap0_len), 1.0,
            "RED: initial snapshot must have 1 entry")
        self.assertIsNotNone(g._human0_deploy,
            "RED: initial equipment.deployable must be present")
        self.assertEqual(g._human0_deploy_id, "ammo_bag",
            "RED: initial deployable.id must be 'ammo_bag'")

        self.assertEqual(float(g._snap1_len), 1.0,
            "RED: after peer replacement snapshot must have 1 entry")
        self.assertIsNone(g._human1_deploy,
            "RED: after peer replacement, stale deployable must be cleared (owner invalidated)")

        self.assertEqual(float(g._snap2_len), 1.0,
            "RED: after fresh genuine event snapshot must have 1 entry")
        self.assertIsNotNone(g._human2_deploy,
            "RED: after fresh genuine event with identical values, equipment.deployable must be restored")
        if g._human2_deploy:
            self.assertEqual(g._human2_deploy_id, "ammo_bag",
                "RED: restored deployable.id must be 'ammo_bag'")
            self.assertEqual(float(g._human2_deploy_amount), 2.0,
                "RED: restored deployable.amount must be 2")

    def test_session_replacement_retaining_same_peer_must_not_inherit_old_channel(self):
        """Session replacement retaining same peer object and PM record must not inherit old channel.

        Setup: human peer2 with equipment registry published (deployable ammo_bag
        amount=2). refresh_crew(0) obtains it. Replace ENTIRE session object with
        new Session, but register SAME peer object at same id=2. PM record RETAINED.

        refresh_crew(.5) must NOT inherit old equipment channel (new session = new
        identity context). Equipment must be nil until fresh genuine event.
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
            _G._remote_peer_same = remote_peer

            local unitA = {_alive = true, _label = "unitA", _id = 100}

            managers.criminals:_set_character(1, {
                name = "american",
                taken = true,
                unit = nil,
                peer_id = 1,
                data = {ai = false, panel_id = 4},
            })
            managers.criminals:_set_character(2, {
                name = "spanish",
                taken = true,
                unit = unitA,
                peer_id = 2,
                data = {ai = false, panel_id = 2},
            })

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

            managers.player = managers.player or {}
            managers.player._global = managers.player._global or {}
            managers.player._global.synced_deployables = {
                [2] = {deployable = "ammo_bag", amount = 2}
            }
            managers.player._global.synced_cable_ties = {}
            managers.player._global.synced_grenades = {}

            function managers.player:get_synced_deployable_equipment(peer_id)
                return self._global.synced_deployables[peer_id]
            end
            function managers.player:get_synced_cable_ties(peer_id)
                return self._global.synced_cable_ties[peer_id]
            end
            function managers.player:get_synced_grenades(peer_id)
                return self._global.synced_grenades[peer_id]
            end

            tweak_data = tweak_data or {}
            tweak_data.equipments = tweak_data.equipments or {}
            tweak_data.equipments.ammo_bag = {text_id = "ammo_bag_name"}
        '''
        lua, ok = _fresh_lua(setup=setup)
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

            _snap0_len = #snap0
            _human0 = nil
            for _, e in ipairs(snap0) do
                if e.peer_id == 2 then _human0 = e; break end
            end
            _human0_eq = _human0 and _human0.equipment or nil
            _human0_deploy = _human0_eq and _human0_eq.deployable or nil

            local Peer = getmetatable(managers.network:session():local_peer())
            local Session = getmetatable(managers.network:session())

            local new_local_peer = Peer:new(1, "LocalHost", 10, 2, nil)
            local new_session = Session:new(new_local_peer)
            new_session:_register_peer(new_local_peer)
            new_session:_register_peer(_G._remote_peer_same)
            managers.network._session = new_session

            ACT:refresh_crew(mgr, 0.5)
            local snap1 = ACT:get_crew_snapshot()

            _snap1_len = #snap1
            _human1 = nil
            for _, e in ipairs(snap1) do
                if e.peer_id == 2 then _human1 = e; break end
            end
            _human1_eq = _human1 and _human1.equipment or nil
            _human1_deploy = _human1_eq and _human1_eq.deployable or nil
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertEqual(float(g._snap0_len), 1.0,
            "RED: initial snapshot must have 1 entry")
        self.assertIsNotNone(g._human0_deploy,
            "RED: initial equipment.deployable must be present")

        self.assertEqual(float(g._snap1_len), 1.0,
            "RED: after session replacement snapshot must have 1 entry")
        self.assertIsNone(g._human1_deploy,
            "RED: after session replacement (same peer object, PM record retained), old equipment channel must NOT be inherited")


if __name__ == "__main__":
    unittest.main()
