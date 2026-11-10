"""Crew online inactive ammo slice -- bounded RED tracer (data + render only).

Scope: new human crew snapshot channel entry.ammo_slots[1]/[2] and new owned
crew card Text Card._inactive_ammo_text showing the OTHER weapon slot
discreetly. This pass covers ONLY the inactive ammo data path and rendering
regressions: no crew placement change, no native masking, no buff yielding
work (crew stays fixed bottom; that approval is not retested here).

Approved production contract under test:
- entry.weapon remains the equipped weapon exactly as before.
- entry.ammo_slots[1]/[2] carry the same detached field set as the current
  weapon.ammo {max_clip, current_clip, total_raw, max, reserve, provenance},
  independent of the selected slot. Source is the real PlayerManager
  get_synced_ammo_info through collect_human_ammo and the existing
  _qualify_pm_publication tracker; no local inventory ammo substituted, no
  bot/client guessed health.
- Card._inactive_ammo_text (owned Text, same parent as equipment content)
  shows the other slot clip/reserve in gray at nominal 16e versus the
  existing active 22e, three digits each ("012/083"), unknown "---/---",
  zero "000/000", >999 preserved ("1000/1234"). Selected index comes from
  actor.weapon.selection_index. Placed below existing equipment content,
  inside the expanded OWNED backdrop, no overlap; the drawn footer stays
  anchored by the ordinary C:update. Bots hide the row. Inactive vanilla
  info is never discarded: active texts keep rendering.

RED state: actors.lua collects only the selected slot (no entry.ammo_slots)
and crew_card.lua has no _inactive_ammo_text primitive. Every new-contract
assertion must fail with an explicit message until production lands; missing
fields fail unconditionally (nil-safe captures, no optional skips).

Fixtures reused (no new helper modules):
- test_hud_crew_events._fresh_lua: actors.lua executed in both real contexts
  (lib/managers/hudmanagerpd2, lib/managers/playermanager) with wrapping
  Hooks so genuine native-shaped PM setters fire the actual registered
  PostHooks. Native model HUDManager.PLAYER_PANEL = 4.
- test_hud_crew._lua: full crew stack (layout, native_visibility, runtime,
  actors, gauge, player, crew_card, crew) over the native roster; PM and
  weapon-selected events installed per the test_hud_crew_owner_contract
  pattern (genuine setters defined before the actors.lua context reload).
- test_hud_crew_card._lua: real crew_card chunk alone for the pure
  component verify/corruption case.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_crew_events import _fresh_lua
from test_hud_crew import _lua as _crew_lua, ROOT
from test_hud_crew_card import _lua as _card_lua

ACTORS_PATH = ROOT / "lua" / "hud" / "actors.lua"

SOURCE_SETUP = r'''
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
        _units = {[1] = gunA, [2] = gunB},
        equipped_selection = function(self) return self._equipped_selection end,
        equipped_unit = function(self) return self._equipped_unit end,
        unit_by_selection = function(self, index) return self._units[index] end,
    }
    unitA.inventory = function(self) return inventory end
    _G._inventory = inventory

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
            max = max,
        }
    end

    function HUDManager:_set_teammate_weapon_selected(panel_id, selection_index, icon)
        if not self._teammate_panels[panel_id] then
            self._teammate_panels[panel_id] = {}
        end
        self._teammate_panels[panel_id].weapon_selection = selection_index
        self._teammate_panels[panel_id].weapon_icon = icon
    end

    function PlayerManager:set_synced_ammo_info(peer_id, selection_index, max_clip, current_clip, current_left, max)
        self._global.synced_ammo_info[peer_id] = self._global.synced_ammo_info[peer_id] or {}
        self._global.synced_ammo_info[peer_id][selection_index] = {
            max_clip,
            current_clip,
            current_left,
            max,
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
            if rec.peer_id == peer_id then
                return rec
            end
        end
        return nil
    end
'''

RENDER_SETUP = r'''
    PlayerManager = {}
    PlayerManager.__index = PlayerManager
    local _roster_player_unit = managers.player and managers.player.player_unit or nil
    local pm = setmetatable({
        _global = {
            synced_deployables = {[2] = {deployable = "ammo_bag", amount = 2}},
            synced_cable_ties = {[2] = {amount = 1}},
            synced_grenades = {},
            synced_ammo_info = {},
        },
        _turret_for_peer = nil,
    }, PlayerManager)
    managers.player = pm
    function PlayerManager:player_unit()
        if _roster_player_unit then
            return _roster_player_unit(self)
        end
        return nil
    end
    function PlayerManager:get_synced_deployable_equipment(id)
        return self._global.synced_deployables[id]
    end
    function PlayerManager:get_synced_cable_ties(id)
        return self._global.synced_cable_ties[id]
    end
    function PlayerManager:get_synced_grenades(id)
        return self._global.synced_grenades[id]
    end
    function PlayerManager:get_synced_ammo_info(id)
        return self._global.synced_ammo_info[id]
    end
    function PlayerManager:get_player_turret_for_peer(id)
        return self._turret_for_peer
    end
    function PlayerManager:set_synced_ammo_info(id, selection, max_clip, current_clip, current_left, max)
        self._global.synced_ammo_info[id] = self._global.synced_ammo_info[id] or {}
        self._global.synced_ammo_info[id][selection] = {max_clip, current_clip, current_left, max}
    end

    function HUDManager:_set_teammate_weapon_selected(i, selection_index, icon)
        if not self._teammate_panels[i] then
            self._teammate_panels[i] = {}
        end
        self._teammate_panels[i].weapon_selection = selection_index
        self._teammate_panels[i].weapon_icon = icon
    end

    local post = Hooks.PostHook
    function Hooks:PostHook(cls, method, id, fn)
        post(self, cls, method, id, fn)
        if type(cls) ~= "table" or type(cls[method]) ~= "function" then
            return
        end
        local original = cls[method]
        cls[method] = function(self, ...)
            original(self, ...)
            fn(self, ...)
        end
    end

    local function mkgun(id)
        local base = {
            get_name_id = function() return id end,
            weapon_tweak_data = function() return {name_id = id .. "_name"} end,
        }
        return {base = function() return base end}
    end
    _G._gunA = mkgun("gun_a")
    _G._gunB = mkgun("gun_b")
    _G._inventory = {
        _equipped_selection = 1,
        _equipped_unit = _G._gunA,
        _units = {[1] = _G._gunA, [2] = _G._gunB},
        equipped_selection = function(self) return self._equipped_selection end,
        equipped_unit = function(self) return self._equipped_unit end,
        unit_by_selection = function(self, index) return self._units[index] end,
    }
    for _, rec in ipairs(managers.criminals:characters()) do
        if rec.peer_id == 2 then
            rec.unit = {inventory = function() return _G._inventory end}
        end
    end
'''


class CrewOnlineInactiveAmmoTests(unittest.TestCase):

    def test_publications_feed_both_ammo_slots_with_detachment_and_invalidation(self):
        """Source: genuine PM ammo/weapon events publish BOTH weapon slots.

        Setup: localpeer1, remotepeer2 (human, slot 2) with live unitA carrying
        a two-weapon native inventory (gun_a selected 1, gun_b at 2). PM
        native-shaped _global.synced_ammo_info with genuine
        set_synced_ammo_info(peer_id, selection, max_clip, current_clip,
        current_left, max) relaying to the native
        HUDManager:set_teammate_ammo_amount; genuine
        HUDManager:_set_teammate_weapon_selected(panel, selection, icon).
        actors.lua runs in both real contexts through
        test_hud_crew_events._fresh_lua so the actual registered PostHooks
        fire from the genuine setters.

        Flow: refresh_crew(0) builds the roster with an empty PM ammo registry
        (weapon.ammo nil). Genuine events publish slot1 {30,7,67,120} and
        slot2 {40,12,95,160}; an immediate get_crew_snapshot WITHOUT refresh
        must expose entry.weapon (equipped gun_a, selection 1, ammo = slot1
        fields) AND entry.ammo_slots[1]/[2] with the same detached field set,
        reserve subtracted once (67-7=60, 95-12=83). Mutating the returned
        nested copies then calling the getter again WITHOUT refresh must
        return the originals (detached deep copies, no re-subtraction).
        refresh_crew(0.5) must collect both slots from the real registry. A
        further genuine slot2 event {40,10,90,160} must update the INACTIVE
        channel through the actual callback while selection stays 1 (active
        channel untouched). The actual registered weapon-selected event then
        switches the equipped slot to gun_b/2: weapon.ammo becomes slot2
        values while ammo_slots[1] survives (independent of selection).
        Replacing the occupant peer object at the same id and refreshing must
        invalidate weapon.ammo and both ammo_slots (owner evidence rule);
        fresh genuine events from the new peer must republish both slots;
        removing the occupant (taken=false) must drop the crew entry.
        """
        lua, ok = _fresh_lua(setup=SOURCE_SETUP)
        self.assertTrue(ok,
            "RED: lua/hud/actors.lua must exist (production chunk missing)")
        if not ok:
            return

        lua.execute(r'''
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

            local function find_peer2(snap)
                for _, e in ipairs(snap) do
                    if e.peer_id == 2 then
                        return e
                    end
                end
                return nil
            end

            local function ammo_fields(a)
                if type(a) ~= "table" then return nil end
                return a.max_clip, a.current_clip, a.total_raw, a.max, a.reserve, a.provenance
            end

            -- A: initial roster; PM ammo registry empty.
            ACT:refresh_crew(mgr, 0)
            local snap0 = ACT:get_crew_snapshot()
            _snap0_len = #snap0
            local e0 = find_peer2(snap0)
            _token0 = e0 and e0.occupant_token or nil
            _w0_sel = e0 and e0.weapon and e0.weapon.selection_index or nil
            _w0_id = e0 and e0.weapon and e0.weapon.weapon_id or nil
            _w0_ammo_nil = (e0 == nil) or (e0.weapon == nil) or (e0.weapon.ammo == nil)

            -- B: genuine PM events publish BOTH slots; snapshot WITHOUT refresh.
            managers.player:set_synced_ammo_info(2, 1, 30, 7, 67, 120)
            managers.player:set_synced_ammo_info(2, 2, 40, 12, 95, 160)

            local snap1 = ACT:get_crew_snapshot()
            local e1 = find_peer2(snap1)
            _snap1_len = #snap1
            _b_token_same = (e1 ~= nil) and (e1.occupant_token == _token0) or false
            _b_w_sel = e1 and e1.weapon and e1.weapon.selection_index or nil
            _b_w_id = e1 and e1.weapon and e1.weapon.weapon_id or nil
            local b_w_ammo = e1 and e1.weapon and e1.weapon.ammo or nil
            local b_slots = e1 and e1.ammo_slots or nil
            local b_s1 = b_slots and b_slots[1] or nil
            local b_s2 = b_slots and b_slots[2] or nil
            _b_w_ammo_present = b_w_ammo ~= nil
            _b_w_max_clip, _b_w_clip, _b_w_total, _b_w_max, _b_w_reserve, _b_w_prov = ammo_fields(b_w_ammo)
            _b_s1_present = b_s1 ~= nil
            _b_s2_present = b_s2 ~= nil
            _b_s1_max_clip, _b_s1_clip, _b_s1_total, _b_s1_max, _b_s1_reserve, _b_s1_prov = ammo_fields(b_s1)
            _b_s2_max_clip, _b_s2_clip, _b_s2_total, _b_s2_max, _b_s2_reserve, _b_s2_prov = ammo_fields(b_s2)
            _b_s1_distinct = (b_s1 ~= nil) and (b_w_ammo ~= nil) and (b_s1 ~= b_w_ammo)

            -- C: mutate returned nested copies, then getter WITHOUT refresh.
            if b_s2 then b_s2.reserve = 9999 end
            if b_s1 then b_s1.current_clip = 777 end
            if b_w_ammo then b_w_ammo.reserve = 8888 end
            local snap1b = ACT:get_crew_snapshot()
            local e1b = find_peer2(snap1b)
            _c_w_reserve = e1b and e1b.weapon and e1b.weapon.ammo and e1b.weapon.ammo.reserve or nil
            _c_s1_clip = e1b and e1b.ammo_slots and e1b.ammo_slots[1] and e1b.ammo_slots[1].current_clip or nil
            _c_s2_reserve = e1b and e1b.ammo_slots and e1b.ammo_slots[2] and e1b.ammo_slots[2].reserve or nil

            -- D: poll rescan collects BOTH slots from the real registry.
            ACT:refresh_crew(mgr, 0.5)
            local snap2 = ACT:get_crew_snapshot()
            local e2 = find_peer2(snap2)
            _d_w_clip = e2 and e2.weapon and e2.weapon.ammo and e2.weapon.ammo.current_clip or nil
            _d_w_reserve = e2 and e2.weapon and e2.weapon.ammo and e2.weapon.ammo.reserve or nil
            _d_s1_clip = e2 and e2.ammo_slots and e2.ammo_slots[1] and e2.ammo_slots[1].current_clip or nil
            _d_s1_reserve = e2 and e2.ammo_slots and e2.ammo_slots[1] and e2.ammo_slots[1].reserve or nil
            _d_s2_clip = e2 and e2.ammo_slots and e2.ammo_slots[2] and e2.ammo_slots[2].current_clip or nil
            _d_s2_reserve = e2 and e2.ammo_slots and e2.ammo_slots[2] and e2.ammo_slots[2].reserve or nil

            -- E: actual PM callback updates the INACTIVE channel, selection unchanged.
            managers.player:set_synced_ammo_info(2, 2, 40, 10, 90, 160)
            local snap3 = ACT:get_crew_snapshot()
            local e3 = find_peer2(snap3)
            _e_w_sel = e3 and e3.weapon and e3.weapon.selection_index or nil
            _e_w_clip = e3 and e3.weapon and e3.weapon.ammo and e3.weapon.ammo.current_clip or nil
            _e_w_reserve = e3 and e3.weapon and e3.weapon.ammo and e3.weapon.ammo.reserve or nil
            _e_s1_clip = e3 and e3.ammo_slots and e3.ammo_slots[1] and e3.ammo_slots[1].current_clip or nil
            _e_s1_reserve = e3 and e3.ammo_slots and e3.ammo_slots[1] and e3.ammo_slots[1].reserve or nil
            _e_s2_clip = e3 and e3.ammo_slots and e3.ammo_slots[2] and e3.ammo_slots[2].current_clip or nil
            _e_s2_total = e3 and e3.ammo_slots and e3.ammo_slots[2] and e3.ammo_slots[2].total_raw or nil
            _e_s2_reserve = e3 and e3.ammo_slots and e3.ammo_slots[2] and e3.ammo_slots[2].reserve or nil

            -- F: actual registered weapon-selected event switches the equipped slot.
            _G._inventory._equipped_selection = 2
            _G._inventory._equipped_unit = _G._gunB
            managers.hud:_set_teammate_weapon_selected(2, 2, "icon")
            local snap4 = ACT:get_crew_snapshot()
            local e4 = find_peer2(snap4)
            _f_token_same = (e4 ~= nil) and (e4.occupant_token == _token0) or false
            _f_w_sel = e4 and e4.weapon and e4.weapon.selection_index or nil
            _f_w_id = e4 and e4.weapon and e4.weapon.weapon_id or nil
            _f_w_clip = e4 and e4.weapon and e4.weapon.ammo and e4.weapon.ammo.current_clip or nil
            _f_w_reserve = e4 and e4.weapon and e4.weapon.ammo and e4.weapon.ammo.reserve or nil
            _f_s1_clip = e4 and e4.ammo_slots and e4.ammo_slots[1] and e4.ammo_slots[1].current_clip or nil
            _f_s1_reserve = e4 and e4.ammo_slots and e4.ammo_slots[1] and e4.ammo_slots[1].reserve or nil
            _f_s2_clip = e4 and e4.ammo_slots and e4.ammo_slots[2] and e4.ammo_slots[2].current_clip or nil

            -- G: replacing the occupant peer object at the same id invalidates.
            local session = managers.network:session()
            local Peer = getmetatable(session:local_peer())
            session._peers[2] = Peer:new(2, "Replacement", 9, 0, nil)
            ACT:refresh_crew(mgr, 1.0)
            local snap5 = ACT:get_crew_snapshot()
            local e5 = find_peer2(snap5)
            _snap5_len = #snap5
            _g_name = e5 and e5.name or nil
            _g_token_changed = (e5 ~= nil) and (e5.occupant_token ~= _token0) or false
            _g_w_ammo = e5 and e5.weapon and e5.weapon.ammo or nil
            _g_s1 = e5 and e5.ammo_slots and e5.ammo_slots[1] or nil
            _g_s2 = e5 and e5.ammo_slots and e5.ammo_slots[2] or nil

            -- H: fresh genuine events from the new peer republish both slots.
            managers.player:set_synced_ammo_info(2, 1, 30, 7, 67, 120)
            managers.player:set_synced_ammo_info(2, 2, 40, 10, 90, 160)
            local snap6 = ACT:get_crew_snapshot()
            local e6 = find_peer2(snap6)
            _h_w_sel = e6 and e6.weapon and e6.weapon.selection_index or nil
            _h_w_clip = e6 and e6.weapon and e6.weapon.ammo and e6.weapon.ammo.current_clip or nil
            _h_w_reserve = e6 and e6.weapon and e6.weapon.ammo and e6.weapon.ammo.reserve or nil
            _h_s1_clip = e6 and e6.ammo_slots and e6.ammo_slots[1] and e6.ammo_slots[1].current_clip or nil
            _h_s1_reserve = e6 and e6.ammo_slots and e6.ammo_slots[1] and e6.ammo_slots[1].reserve or nil
            _h_s2_clip = e6 and e6.ammo_slots and e6.ammo_slots[2] and e6.ammo_slots[2].current_clip or nil
            _h_s2_reserve = e6 and e6.ammo_slots and e6.ammo_slots[2] and e6.ammo_slots[2].reserve or nil

            -- I: removing the occupant drops the crew entry entirely.
            managers.criminals:characters()[2].taken = false
            ACT:refresh_crew(mgr, 1.5)
            local snap7 = ACT:get_crew_snapshot()
            _snap7_len = #snap7
            _i_has_peer2 = (find_peer2(snap7) ~= nil)
        ''')
        g = lua.globals()
        if g._api_missing:
            self.fail(f"RED: ACT:{g._api_missing} must exist")
            return

        self.assertEqual(float(g._snap0_len), 1.0,
            "RED: initial crew snapshot must contain the single human peer2")
        self.assertIsNotNone(g._token0,
            "RED: human occupant_token must be captured")
        self.assertEqual(float(g._w0_sel), 1.0,
            "RED: entry.weapon must be the equipped weapon (selection 1)")
        self.assertEqual(g._w0_id, "gun_a",
            "RED: entry.weapon.weapon_id must be 'gun_a'")
        self.assertIs(g._w0_ammo_nil, True,
            "known positive: empty PM ammo registry must leave weapon.ammo nil")

        self.assertEqual(float(g._snap1_len), 1.0,
            "RED: snapshot after both genuine events must keep 1 entry")
        self.assertIs(g._b_token_same, True,
            "RED: genuine PM events must not change the occupant token")
        self.assertEqual(float(g._b_w_sel), 1.0,
            "RED: entry.weapon must remain the equipped weapon (selection 1)")
        self.assertEqual(g._b_w_id, "gun_a",
            "RED: entry.weapon.weapon_id must remain 'gun_a'")
        self.assertIs(g._b_w_ammo_present, True,
            "known positive: weapon.ammo must be present after the slot1 genuine event")
        self.assertEqual(float(g._b_w_max_clip), 30.0,
            "RED: weapon.ammo.max_clip must be 30")
        self.assertEqual(float(g._b_w_clip), 7.0,
            "RED: weapon.ammo.current_clip must be 7")
        self.assertEqual(float(g._b_w_total), 67.0,
            "RED: weapon.ammo.total_raw must be 67")
        self.assertEqual(float(g._b_w_max), 120.0,
            "RED: weapon.ammo.max must be 120")
        self.assertEqual(float(g._b_w_reserve), 60.0,
            "RED: weapon.ammo.reserve must be 60 (67-7, subtracted once)")
        self.assertEqual(g._b_w_prov, "network_synced",
            "RED: weapon.ammo.provenance must be 'network_synced'")

        self.assertIs(g._b_s1_present, True,
            "RED: entry.ammo_slots[1] must exist with the same detached fields as weapon.ammo")
        self.assertEqual(float(g._b_s1_max_clip), 30.0,
            "RED: ammo_slots[1].max_clip must be 30")
        self.assertEqual(float(g._b_s1_clip), 7.0,
            "RED: ammo_slots[1].current_clip must be 7")
        self.assertEqual(float(g._b_s1_total), 67.0,
            "RED: ammo_slots[1].total_raw must be 67")
        self.assertEqual(float(g._b_s1_max), 120.0,
            "RED: ammo_slots[1].max must be 120")
        self.assertEqual(float(g._b_s1_reserve), 60.0,
            "RED: ammo_slots[1].reserve must be 60")
        self.assertEqual(g._b_s1_prov, "network_synced",
            "RED: ammo_slots[1].provenance must be 'network_synced'")

        self.assertIs(g._b_s2_present, True,
            "RED: entry.ammo_slots[2] must exist independent of the selected slot")
        self.assertEqual(float(g._b_s2_max_clip), 40.0,
            "RED: ammo_slots[2].max_clip must be 40")
        self.assertEqual(float(g._b_s2_clip), 12.0,
            "RED: ammo_slots[2].current_clip must be 12")
        self.assertEqual(float(g._b_s2_total), 95.0,
            "RED: ammo_slots[2].total_raw must be 95")
        self.assertEqual(float(g._b_s2_max), 160.0,
            "RED: ammo_slots[2].max must be 160")
        self.assertEqual(float(g._b_s2_reserve), 83.0,
            "RED: ammo_slots[2].reserve must be 83 (95-12, subtracted once)")
        self.assertEqual(g._b_s2_prov, "network_synced",
            "RED: ammo_slots[2].provenance must be 'network_synced'")
        self.assertIs(g._b_s1_distinct, True,
            "RED: ammo_slots[1] must be a detached table, not the weapon.ammo reference")

        self.assertEqual(float(g._c_w_reserve), 60.0,
            "RED: weapon.ammo must stay detached and reserve must not be re-subtracted (still 60)")
        self.assertEqual(float(g._c_s1_clip), 7.0,
            "RED: ammo_slots[1] must be a detached nested copy (mutation must not leak)")
        self.assertEqual(float(g._c_s2_reserve), 83.0,
            "RED: ammo_slots[2] must be a detached nested copy, reserve subtracted once (still 83)")

        self.assertEqual(float(g._d_w_clip), 7.0,
            "RED: poll rescan must keep weapon.ammo.current_clip 7")
        self.assertEqual(float(g._d_w_reserve), 60.0,
            "RED: poll rescan must keep weapon.ammo.reserve 60")
        self.assertEqual(float(g._d_s1_clip), 7.0,
            "RED: poll rescan must collect ammo_slots[1] from the real registry")
        self.assertEqual(float(g._d_s1_reserve), 60.0,
            "RED: poll rescan must keep ammo_slots[1].reserve 60")
        self.assertEqual(float(g._d_s2_clip), 12.0,
            "RED: poll rescan must collect ammo_slots[2] independent of selection")
        self.assertEqual(float(g._d_s2_reserve), 83.0,
            "RED: poll rescan must keep ammo_slots[2].reserve 83")

        self.assertEqual(float(g._e_w_sel), 1.0,
            "RED: selection must remain 1 while the inactive channel updates")
        self.assertEqual(float(g._e_w_clip), 7.0,
            "RED: the active channel must be untouched by the inactive slot event")
        self.assertEqual(float(g._e_w_reserve), 60.0,
            "RED: active weapon.ammo.reserve must stay 60")
        self.assertEqual(float(g._e_s1_clip), 7.0,
            "RED: ammo_slots[1].current_clip must stay 7")
        self.assertEqual(float(g._e_s1_reserve), 60.0,
            "RED: ammo_slots[1].reserve must stay 60")
        self.assertEqual(float(g._e_s2_clip), 10.0,
            "RED: the actual PM callback must update the inactive channel while selected unchanged")
        self.assertEqual(float(g._e_s2_total), 90.0,
            "RED: ammo_slots[2].total_raw must be 90 after the genuine event")
        self.assertEqual(float(g._e_s2_reserve), 80.0,
            "RED: ammo_slots[2].reserve must be 80 (90-10, recomputed once)")

        self.assertIs(g._f_token_same, True,
            "RED: the weapon-selected event must not change the occupant token")
        self.assertEqual(float(g._f_w_sel), 2.0,
            "RED: the actual weapon-selected event must switch entry.weapon to slot 2")
        self.assertEqual(g._f_w_id, "gun_b",
            "RED: entry.weapon.weapon_id must be 'gun_b' after the switch")
        self.assertEqual(float(g._f_w_clip), 10.0,
            "RED: weapon.ammo.current_clip must be slot2 value 10 after the switch")
        self.assertEqual(float(g._f_w_reserve), 80.0,
            "RED: weapon.ammo.reserve must be slot2 value 80 after the switch")
        self.assertEqual(float(g._f_s1_clip), 7.0,
            "RED: ammo_slots[1] must survive the slot switch (independent of selected slot)")
        self.assertEqual(float(g._f_s1_reserve), 60.0,
            "RED: ammo_slots[1].reserve must stay 60 after the switch")
        self.assertEqual(float(g._f_s2_clip), 10.0,
            "RED: ammo_slots[2].current_clip must stay 10 after the switch")

        self.assertEqual(float(g._snap5_len), 1.0,
            "RED: the replaced peer must still occupy one crew entry")
        self.assertEqual(g._g_name, "Replacement",
            "RED: the roster must reflect the replaced peer object")
        self.assertIs(g._g_token_changed, True,
            "RED: replacing the occupant must issue a new occupant_token")
        self.assertIsNone(g._g_w_ammo,
            "RED: stale weapon.ammo must not survive occupant replacement")
        self.assertIsNone(g._g_s1,
            "RED: stale ammo_slots[1] must not survive occupant replacement")
        self.assertIsNone(g._g_s2,
            "RED: stale ammo_slots[2] must not survive occupant replacement")

        self.assertEqual(float(g._h_w_sel), 2.0,
            "RED: entry.weapon must remain selection 2 after republish")
        self.assertEqual(float(g._h_w_clip), 10.0,
            "RED: fresh genuine event must restore weapon.ammo.current_clip 10")
        self.assertEqual(float(g._h_w_reserve), 80.0,
            "RED: fresh genuine event must restore weapon.ammo.reserve 80")
        self.assertEqual(float(g._h_s1_clip), 7.0,
            "RED: fresh genuine event must republish ammo_slots[1] through the actual callback")
        self.assertEqual(float(g._h_s1_reserve), 60.0,
            "RED: republished ammo_slots[1].reserve must be 60")
        self.assertEqual(float(g._h_s2_clip), 10.0,
            "RED: fresh genuine event must republish ammo_slots[2]")
        self.assertEqual(float(g._h_s2_reserve), 80.0,
            "RED: republished ammo_slots[2].reserve must be 80")

        self.assertEqual(float(g._snap7_len), 0.0,
            "RED: removing the occupant must drop the crew entry")
        self.assertIs(g._i_has_peer2, False,
            "RED: no peer2 entry may survive occupant removal")

    def test_crew_card_renders_inactive_slot_ammo_row(self):
        """Render: real crew stack draws the inactive ammo row below equipment.

        Setup: test_hud_crew._lua full stack over the native roster (human
        peer2 slot 2, bots at slots 1/3). RENDER_SETUP installs the
        native-shaped PM publication fixture (genuine set_synced_ammo_info,
        genuine HUDManager:_set_teammate_weapon_selected, wrapping Hooks) and
        attaches the two-weapon inventory to peer2, then actors.lua reloads
        in both real contexts (owner-contract pattern) so genuine PM events
        fire the actual registered callbacks.

        Flow: enable foundation+crew at 1920x1080 scale 1; refresh_crew(0);
        genuine PM events publish slot1 {30,7,67,120} and slot2
        {40,12,95,160}; runtime mount, crew mount, ordinary C:update. Known
        positive existing verification FIRST: C:_verify_render() true and the
        existing active texts _weapon_text '007' / _reserve_text '/060'.
        Then the new owned primitive Card._inactive_ammo_text: exact string
        '012/083' (three digits each), visible, gray 0.7, nominal font 16e
        versus the existing active 22e, same parent as the equipment content
        (card root), strictly below the equipment texts/icons (no overlap),
        inside the expanded owned backdrop and the untouched 120-high card
        slot. A real slot switch (inventory to gun_b/2 + genuine
        weapon-selected event + ordinary C:update) must keep the SAME
        _inactive_ammo_text reference, now showing slot1 '007/060', with
        active '012'/'/083', certification still true and the footer still
        anchored by the ordinary update (_bottom_offset). Bot cards must own
        the primitive but hide the row. Finally a clearly scoped
        pure-component parameter loop (direct Card:update) pins zero
        '000/000', unknown '---/---' (nil slot table, nil fields, nil
        ammo_slots) and >999 preserved '1000/1234' while the active clip
        stays '001'.
        """
        lua, ok = _crew_lua()
        self.assertTrue(ok, "RED: lua/hud/crew.lua must exist")
        if not ok:
            return

        lua.execute(RENDER_SETUP)
        actors_src = ACTORS_PATH.read_text(encoding="utf-8-sig")
        for context in ("lib/managers/playermanager", "lib/managers/hudmanagerpd2"):
            lua.globals().RequiredScript = context
            lua.execute(actors_src)

        lua.execute(r'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_crew = true
            kyohud.settings.hud_scale = 1.0
            _G.panel_double:set_shape(0, 0, 1920, 1080)

            local mgr = managers.hud
            local ACT = kyohud.hud.actors
            ACT:refresh_crew(mgr, 0)

            managers.player:set_synced_ammo_info(2, 1, 30, 7, 67, 120)
            managers.player:set_synced_ammo_info(2, 2, 40, 12, 95, 160)

            kyohud.hud.runtime:mount(mgr)
            local C = kyohud.hud.crew
            C:mount(mgr)
            C:update(mgr, 1.0, 0.05)

            -- Known positive existing component verification FIRST.
            _c_verify = C:_verify_render()
            local card = C._cards[2]
            _card2_exists = card ~= nil
            _wt = card and card._weapon_text and card._weapon_text:text() or nil
            _rt = card and card._reserve_text and card._reserve_text:text() or nil

            -- NEW owned primitive: inactive slot ammo row.
            local ia = card and card._inactive_ammo_text or nil
            _ia_exists = ia ~= nil
            _ia_text = ia and ia:text() or nil
            _ia_visible = ia and ia:visible() or nil
            _ia_fsize = ia and ia:font_size() or nil
            _wt_fsize = card and card._weapon_text and card._weapon_text:font_size() or nil
            local iac = ia and ia:color() or nil
            _ia_r = iac and iac.r or nil
            _ia_g = iac and iac.g or nil
            _ia_b = iac and iac.b or nil
            _ia_parent_ok = (ia ~= nil) and (card._equipment_text ~= nil)
                and (ia:parent() == card._equipment_text:parent())
                and (ia:parent() == card.root)

            -- Below existing equipment content, inside the expanded owned
            -- backdrop, no overlap; card slot height (placement) untouched.
            local function bottom(p)
                return p:y() + p:h()
            end
            _eq_bottom = math.max(
                bottom(card._equipment_text),
                bottom(card._cables_text),
                bottom(card._projectile_text),
                bottom(card._deployable_icon),
                bottom(card._cables_icon),
                bottom(card._projectile_icon))
            _ia_y = ia and ia:y() or nil
            _ia_bottom = ia and bottom(ia) or nil
            _bg_bottom = card and bottom(card._backdrop) or nil
            _ia_below_eq = (ia ~= nil) and (_ia_y >= _eq_bottom - 0.01)
            _ia_inside_backdrop = (ia ~= nil) and (_ia_bottom <= _bg_bottom + 0.01)
            _ia_inside_root = (ia ~= nil) and (_ia_bottom <= card.root:h() + 0.01)
            _root_h = card and card.root:h() or nil

            -- Identity stable through a real slot switch driven by the
            -- actual registered weapon-selected event.
            _ia_ref = ia
            _G._inventory._equipped_selection = 2
            _G._inventory._equipped_unit = _G._gunB
            mgr:_set_teammate_weapon_selected(2, 2, "icon")
            C:update(mgr, 1.1, 0.05)
            local card_b = C._cards[2]
            _ia_same_ref = (card_b ~= nil) and (card_b._inactive_ammo_text ~= nil)
                and (card_b._inactive_ammo_text == _ia_ref)
            _ia_text2 = card_b and card_b._inactive_ammo_text and card_b._inactive_ammo_text:text() or nil
            _wt2 = card_b and card_b._weapon_text and card_b._weapon_text:text() or nil
            _rt2 = card_b and card_b._reserve_text and card_b._reserve_text:text() or nil
            _c_verify2 = C:_verify_render()
            _bottom_offset = card_b and card_b._bottom_offset or nil

            -- Bots hide the row.
            local bot1 = C._cards[1]
            local bot3 = C._cards[3]
            _bot1_prim = bot1 and bot1._inactive_ammo_text or nil
            _bot3_prim = bot3 and bot3._inactive_ammo_text or nil
            _bot1_exists = _bot1_prim ~= nil
            _bot3_exists = _bot3_prim ~= nil
            _bot1_hidden = _bot1_exists and (_bot1_prim:visible() == false)
            _bot3_hidden = _bot3_exists and (_bot3_prim:visible() == false)
        ''')
        g = lua.globals()

        self.assertIs(g._c_verify, True,
            "known positive: ordinary C:update render certification must hold")
        self.assertIs(g._card2_exists, True,
            "known positive: the human crew card must exist at position 2")
        self.assertEqual(g._wt, "007",
            "known positive: existing active clip text from real publications must be '007'")
        self.assertEqual(g._rt, "/060",
            "known positive: existing active reserve text from real publications must be '/060'")

        self.assertIs(g._ia_exists, True,
            "RED: Card._inactive_ammo_text must exist (owned Text for the inactive slot)")
        self.assertEqual(g._ia_text, "012/083",
            "RED: inactive text must be '012/083' (slot2 clip 12 / reserve 83, three digits each)")
        self.assertIs(g._ia_visible, True,
            "RED: the inactive ammo row must be visible for humans")
        self.assertEqual(float(g._ia_fsize), 16.0,
            "RED: inactive text nominal font must be 16e (e=1 at 1920x1080 scale 1)")
        self.assertEqual(float(g._wt_fsize), 22.0,
            "RED: existing active text nominal font must remain 22e")
        self.assertLess(float(g._ia_fsize), float(g._wt_fsize),
            "RED: inactive text must be smaller than active text")
        self.assertAlmostEqual(float(g._ia_r), 0.7, places=1,
            msg="RED: inactive text must be gray (r 0.7)")
        self.assertAlmostEqual(float(g._ia_g), 0.7, places=1,
            msg="RED: inactive text must be gray (g 0.7)")
        self.assertAlmostEqual(float(g._ia_b), 0.7, places=1,
            msg="RED: inactive text must be gray (b 0.7)")
        self.assertIs(g._ia_parent_ok, True,
            "RED: the inactive row must share the card root parent with equipment content")
        self.assertIs(g._ia_below_eq, True,
            "RED: the inactive row must sit below existing equipment content (no overlap)")
        self.assertIs(g._ia_inside_backdrop, True,
            "RED: the inactive row must fit within the expanded owned backdrop")
        self.assertIs(g._ia_inside_root, True,
            "RED: the inactive row must fit inside the card slot")
        self.assertEqual(float(g._root_h), 120.0,
            "RED: the card slot height must stay 120 (no placement change this pass)")

        self.assertIs(g._ia_same_ref, True,
            "RED: _inactive_ammo_text identity must be stable through the slot switch")
        self.assertEqual(g._ia_text2, "007/060",
            "RED: after the switch the inactive text must show slot 1 ('007/060')")
        self.assertEqual(g._wt2, "012",
            "RED: after the switch the active clip must show slot 2 ('012')")
        self.assertEqual(g._rt2, "/083",
            "RED: after the switch the active reserve must show slot 2 ('/083')")
        self.assertIs(g._c_verify2, True,
            "RED: ordinary C:update render certification must hold after the slot switch")
        self.assertIsNotNone(g._bottom_offset,
            "RED: the drawn footer must still be anchored by the ordinary C:update (_bottom_offset set)")
        self.assertGreaterEqual(float(g._bottom_offset), 0.0,
            "RED: _bottom_offset must remain a non-negative anchor")

        self.assertIs(g._bot1_exists, True,
            "RED: bot cards must own the _inactive_ammo_text primitive")
        self.assertIs(g._bot3_exists, True,
            "RED: bot cards must own the _inactive_ammo_text primitive")
        self.assertIs(g._bot1_hidden, True,
            "RED: bots must hide the inactive ammo row")
        self.assertIs(g._bot3_hidden, True,
            "RED: bots must hide the inactive ammo row")

        lua.execute(r'''
            local CC = kyohud.hud.crew_card
            _pc = CC.new(_G.panel_double, "ammo_slots_param_card")
            _pc:set_geometry(0, 0, 340, 120)
            _p_card_ok = _pc ~= nil

            _p_slots = {
                [1] = {max_clip = 30, current_clip = 1, total_raw = 46, max = 120, reserve = 45, provenance = "network_synced"},
                [2] = {max_clip = 40, current_clip = 12, total_raw = 95, max = 160, reserve = 83, provenance = "network_synced"},
            }
            _p_actor = {
                name = "Param", level = 7, rank = 0, ai = false, peer_id = 3,
                character_name = "spanish",
                health = {ratio = 0.82, valid = true, provenance = "network_quantized"},
                armor = {ratio = 0.45, valid = true, provenance = "network_quantized"},
                weapon = {
                    selection_index = 1, weapon_id = "g36_crew", name_id = "g36_crew",
                    ammo = {max_clip = 30, current_clip = 1, total_raw = 46, max = 120, reserve = 45, provenance = "network_synced"},
                },
                ammo_slots = _p_slots,
                equipment = {
                    deployable = {id = "ammo_bag", amount = 1, name_id = "ammo_bag"},
                    cable_ties = {amount = 0},
                    projectile = {id = "smoke", amount = 1, kind = "ability", name_id = "smoke"},
                },
                interaction = nil,
                downs = 0, condition_text = "normal",
            }
            _pc:update(_p_actor, 0)
            _p_exists = _pc._inactive_ammo_text ~= nil
            _p_txt0 = _pc._inactive_ammo_text and _pc._inactive_ammo_text:text() or nil
        ''')
        g = lua.globals()
        self.assertIs(g._p_card_ok, True,
            "RED: the param crew card component must build")
        self.assertIs(g._p_exists, True,
            "RED: the param card must own _inactive_ammo_text (missing fields must fail)")
        self.assertEqual(g._p_txt0, "012/083",
            "RED: the param card must show the inactive slot as '012/083'")

        param_cases = [
            ("_p_slots[2] = {max_clip = 40, current_clip = 0, total_raw = 40, max = 160, reserve = 0, provenance = 'network_synced'}",
                "000/000"),
            ("_p_slots[2] = nil",
                "---/---"),
            ("_p_slots[2] = {max_clip = nil, current_clip = nil, total_raw = nil, max = nil, reserve = nil, provenance = 'network_synced'}",
                "---/---"),
            ("_p_slots[2] = {max_clip = 50, current_clip = 1000, total_raw = 2234, max = 2500, reserve = 1234, provenance = 'network_synced'}",
                "1000/1234"),
            ("_p_actor.ammo_slots = nil",
                "---/---"),
        ]
        for mutation, expected in param_cases:
            with self.subTest(mutation=mutation):
                lua.execute(mutation)
                lua.execute(r'''
                    _pc:update(_p_actor, 0)
                    _p_txt = _pc._inactive_ammo_text and _pc._inactive_ammo_text:text() or "?"
                    _p_wt = _pc._weapon_text and _pc._weapon_text:text() or "?"
                    _p_ok = _pc:verify()
                ''')
                gf = lua.globals()
                self.assertIs(gf._p_ok, True,
                    f"RED: verify must hold for param case: {mutation}")
                self.assertEqual(gf._p_txt, expected,
                    f"RED: inactive text for param case: {mutation}")
                self.assertEqual(gf._p_wt, "001",
                    f"RED: active clip must stay '001' for param case: {mutation}")

    def test_card_verify_guards_inactive_ammo_text(self):
        """Verify: the new Text is certified, corruption detected, repair by update.

        Pure component (test_hud_crew_card._lua real chunk, direct
        Card:update on a clearly scoped synthetic actor; nothing is injected
        into any production registry). Known positive first: update renders
        the human actor and verify() certifies. Then the new
        _inactive_ammo_text must exist and read '012/083'. Corrupting its
        text ('MUTATED') must make the actual card verify() false; update
        ALONE must repair verify() true, restore '012/083' and reuse the same
        primitive reference. Corrupting its geometry (set_shape 999,999,5,5)
        must make verify() false again; update must repair it back to true.
        """
        lua, ok = _card_lua()
        self.assertTrue(ok,
            "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return

        lua.execute(r'''
            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            _card = CC.new(parent, "inactive_ammo_verify_card")
            _card_ok = _card ~= nil
            if _card then
                _card:set_geometry(0, 0, 340, 120)
            end

            _actor = {
                name = "Verify", level = 7, rank = 0, ai = false, peer_id = 4,
                character_name = "spanish",
                health = {ratio = 0.82, valid = true, provenance = "network_quantized"},
                armor = {ratio = 0.45, valid = true, provenance = "network_quantized"},
                weapon = {
                    selection_index = 1, weapon_id = "g36_crew", name_id = "g36_crew",
                    ammo = {max_clip = 30, current_clip = 1, total_raw = 46, max = 120, reserve = 45, provenance = "network_synced"},
                },
                ammo_slots = {
                    [1] = {max_clip = 30, current_clip = 1, total_raw = 46, max = 120, reserve = 45, provenance = "network_synced"},
                    [2] = {max_clip = 40, current_clip = 12, total_raw = 95, max = 160, reserve = 83, provenance = "network_synced"},
                },
                equipment = {
                    deployable = {id = "ammo_bag", amount = 1, name_id = "ammo_bag"},
                    cable_ties = {amount = 0},
                    projectile = {id = "smoke", amount = 1, kind = "ability", name_id = "smoke"},
                },
                interaction = nil,
                downs = 0, condition_text = "normal",
            }

            -- Known positive existing component behavior first.
            _u1 = _card and _card:update(_actor, 0) or false
            _v1 = _card and _card:verify() or false

            _ia = _card and _card._inactive_ammo_text or nil
            _ia_exists = _ia ~= nil
            _ia_txt1 = _ia and _ia:text() or nil
            _ia_ref = _ia

            -- Corrupt the new Text content: verify must go false.
            if _ia then
                _ia:set_text("MUTATED")
            end
            _v2 = _card and _card:verify() or false

            -- Repair through update ALONE: same reference, verify true.
            _u3 = _card and _card:update(_actor, 0) or false
            _v3 = _card and _card:verify() or false
            _ia_txt3 = _card and _card._inactive_ammo_text and _card._inactive_ammo_text:text() or nil
            _ia_same = (_card ~= nil) and (_card._inactive_ammo_text ~= nil)
                and (_card._inactive_ammo_text == _ia_ref)

            -- Corrupt the new Text geometry: verify must go false again.
            if _card and _card._inactive_ammo_text then
                _card._inactive_ammo_text:set_shape(999, 999, 5, 5)
            end
            _v4 = _card and _card:verify() or false

            _u5 = _card and _card:update(_actor, 0) or false
            _v5 = _card and _card:verify() or false
        ''')
        g = lua.globals()

        self.assertIs(g._card_ok, True,
            "RED: the crew card component must build")
        self.assertIs(g._u1, True,
            "known positive: the existing card update must render the human actor")
        self.assertIs(g._v1, True,
            "known positive: the existing card verify must certify before corruption")
        self.assertIs(g._ia_exists, True,
            "RED: Card._inactive_ammo_text must exist for the corruption contract")
        self.assertEqual(g._ia_txt1, "012/083",
            "RED: the certified card must show the inactive text '012/083' before corruption")
        self.assertIs(g._v2, False,
            "RED: the actual card verify must be false after corrupting _inactive_ammo_text text")
        self.assertIs(g._v3, True,
            "RED: update alone must repair verify after the text corruption")
        self.assertEqual(g._ia_txt3, "012/083",
            "RED: the repaired _inactive_ammo_text must show '012/083'")
        self.assertIs(g._ia_same, True,
            "RED: the repair must reuse the same _inactive_ammo_text reference")
        self.assertIs(g._v4, False,
            "RED: the actual card verify must be false after corrupting _inactive_ammo_text geometry")
        self.assertIs(g._v5, True,
            "RED: update alone must repair verify after the geometry corruption")


if __name__ == "__main__":
    unittest.main()
