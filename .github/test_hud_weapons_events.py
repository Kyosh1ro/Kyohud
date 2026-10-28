"""LOT4b events -- hud/weapons.lua: transition hooks (RED vertical tracer).

1. set_teammate_ammo_amount local4 updates same-unit snapshot; remote1/old mgr ignored
2. _set_teammate_weapon_selected/firemode read actual inventory/mode after switch
3. PlayerInventory equip/add/remove/unequip only owner local _unit==player_unit; missing slot clears state
4. Load chunk twice across contexts: hook IDs unique, singleton retained, wrong context none
"""
from pathlib import Path
import unittest
from test_hud_weapons import _lua

ROOT = Path(__file__).resolve().parents[1]
WEAPONS_PATH = ROOT / "lua" / "hud" / "weapons.lua"

NATIVE_HUD_FIXTURE = r'''
HUDManager.PLAYER_PANEL = 4
function HUDManager:set_teammate_ammo_amount(id, selection_index, max_clip, current_clip, current_left, max)
    if not self._teammate_panels[id] then self._teammate_panels[id] = {} end
    self._teammate_panels[id].ammo_data = {selection_index=selection_index, max_clip=max_clip, current_clip=current_clip, current_left=current_left, max=max}
end
function HUDManager:_set_teammate_weapon_selected(i, sel)
    if not self._teammate_panels[i] then self._teammate_panels[i] = {} end
    self._teammate_panels[i].weapon_selected = sel
end
function HUDManager:set_teammate_weapon_firemode(id, selection_index, mode, alt)
    if not self._teammate_panels[id] then self._teammate_panels[id] = {} end
    self._teammate_panels[id].weapon_firemode = {selection_index=selection_index, mode=mode, alt=alt}
end
function PlayerInventory:equip_selection(idx) self._equipped_slot = idx end
function PlayerInventory:add_unit(u, s) self._selections[s] = {unit=u} end
function PlayerInventory:remove_selection(s) self._selections[s] = nil end
function PlayerInventory:unequip_selection() self._equipped_slot = nil end
'''
DISPATCH = r'''
local function _dispatch(cls, method, ...)
    for _, e in ipairs(Hooks._all) do
        if e.class == cls and e.method == method then e.fn(...) end
    end
end
_KY_dispatch = _dispatch
'''
def _load(context="lib/managers/hudmanagerpd2", setup=None):
    lua, ok = _lua(with_weapons=False, context=context, setup=setup)
    lua.execute(NATIVE_HUD_FIXTURE)
    src = WEAPONS_PATH.read_text(encoding="utf-8-sig") if WEAPONS_PATH.is_file() else None
    if src: lua.execute(src)
    return lua, ok, src is not None


class AmmoAmountLocal4Tests(unittest.TestCase):
    def test_local4_updates_same_unit_snapshot_remote1_old_mgr_ignored(self):
        setup = '''
            unit1, base1 = make_weapon("wpn_a")
            base1:_native_set_ammo(10, 8, 40, 60)
            base1:_native_set_fire_mode("auto")
            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_slot(2, unit1)
            inventory:_native_set_equipped(1)
        '''
        lua, ok, exists = _load(setup=setup)
        self.assertTrue(exists, "RED: weapons.lua missing")
        if not exists: return
        lua.execute(DISPATCH)
        lua.execute('''
            _has_hook = false
            for _, e in ipairs(Hooks._all) do
                if e.class == HUDManager and e.method == "set_teammate_ammo_amount" then
                    _has_hook = true; break
                end
            end
            if not _has_hook then return end
            local WPNS = kyohud.hud.weapons
            WPNS:refresh(managers.hud)
            local snap0 = WPNS:get_snapshot()
            _clip0 = snap0.slots[1].current_clip
            base1:_native_set_ammo(10, 3, 30, 60)
            local mgr = managers.hud
            mgr:set_teammate_ammo_amount(HUDManager.PLAYER_PANEL, 1, 10, 3, 30, 60)
            _KY_dispatch(HUDManager, "set_teammate_ammo_amount", mgr, HUDManager.PLAYER_PANEL, 1, 10, 3, 30, 60)
            local snap1 = WPNS:get_snapshot()
            _clip1 = snap1.slots[1].current_clip
            base1:_native_set_ammo(10, 55, 30, 60)
            mgr:set_teammate_ammo_amount(1, 1, 10, 99, 99, 150)
            _KY_dispatch(HUDManager, "set_teammate_ammo_amount", mgr, 1, 1, 10, 99, 99, 150)
            local snap2 = WPNS:get_snapshot()
            _clip2 = snap2.slots[1].current_clip
            base1:_native_set_ammo(10, 77, 30, 60)
            local old_mgr = setmetatable({_teammate_panels={}}, {__index=HUDManager})
            old_mgr:set_teammate_ammo_amount(HUDManager.PLAYER_PANEL, 1, 10, 77, 77, 150)
            _KY_dispatch(HUDManager, "set_teammate_ammo_amount", old_mgr, HUDManager.PLAYER_PANEL, 1, 10, 77, 77, 150)
            local snap3 = WPNS:get_snapshot()
            _clip3 = snap3.slots[1].current_clip
        ''')
        g = lua.globals()
        if not g._has_hook:
            self.fail("RED: weapons.lua must PostHook HUDManager:set_teammate_ammo_amount")
            return
        self.assertEqual(float(g._clip0), 8.0, "precondition: initial clip=8")
        self.assertEqual(float(g._clip1), 3.0, "RED: local4 ammo callback must refresh same-unit snapshot from source")
        self.assertEqual(float(g._clip2), 3.0, "RED: remote1 ammo callback must be ignored")
        self.assertEqual(float(g._clip3), 3.0, "RED: old manager ammo callback must be ignored")


class WeaponSelectedFiremodeTests(unittest.TestCase):
    def test_callbacks_read_actual_inventory_mode_after_switch(self):
        setup = '''
            unit1, base1 = make_weapon("wpn_a")
            base1:_native_set_ammo(10, 8, 40, 60)
            base1:_native_set_fire_mode("auto")
            unit2, base2 = make_weapon("wpn_b")
            base2:_native_set_ammo(30, 25, 120, 150)
            base2:_native_set_fire_mode("single")
            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_slot(2, unit2)
            inventory:_native_set_equipped(1)
        '''
        lua, ok, exists = _load(setup=setup)
        self.assertTrue(exists, "RED: weapons.lua missing")
        if not exists: return
        lua.execute(DISPATCH)
        lua.execute('''
            _has_sel = false; _has_fm = false
            for _, e in ipairs(Hooks._all) do
                if e.method == "_set_teammate_weapon_selected" then _has_sel = true end
                if e.method == "set_teammate_weapon_firemode" then _has_fm = true end
            end
            if not _has_sel or not _has_fm then return end
            local WPNS = kyohud.hud.weapons
            WPNS:refresh(managers.hud)
            local mgr = managers.hud
            inventory:_native_set_equipped(2)
            mgr:_set_teammate_weapon_selected(HUDManager.PLAYER_PANEL, 2)
            _KY_dispatch(HUDManager, "_set_teammate_weapon_selected", mgr, HUDManager.PLAYER_PANEL, 2)
            local snap1 = WPNS:get_snapshot()
            _sel = snap1 and snap1.selected or nil
            base2:_native_set_fire_mode("burst")
            mgr:set_teammate_weapon_firemode(HUDManager.PLAYER_PANEL, 2, "burst", false)
            _KY_dispatch(HUDManager, "set_teammate_weapon_firemode", mgr, HUDManager.PLAYER_PANEL, 2, "burst", false)
            local snap2 = WPNS:get_snapshot()
            _mode = snap2 and snap2.slots[2] and snap2.slots[2].fire_mode or nil
        ''')
        g = lua.globals()
        if not g._has_sel or not g._has_fm:
            self.fail("RED: weapons.lua must PostHook _set_teammate_weapon_selected and set_teammate_weapon_firemode")
            return
        self.assertEqual(float(g._sel), 2.0, "RED: selected must reflect actual inventory after switch")
        self.assertEqual(g._mode, "burst", "RED: firemode must reflect actual weapon base after change")


class InventoryOwnerTests(unittest.TestCase):
    def test_callback_only_owner_local_unit_missing_slot_clears(self):
        setup = '''
            unit1, base1 = make_weapon("wpn_a")
            base1:_native_set_ammo(10, 8, 40, 60)
            inventory:_native_set_slot(1, unit1)
            inventory:_native_set_slot(2, unit1)
            inventory:_native_set_equipped(1)
            inventory._unit = player_unit
            other_inv = PlayerInventory.new()
            other_inv._unit = {_alive = true, _id = "other"}
        '''
        lua, ok, exists = _load(context="lib/units/beings/player/playerinventory", setup=setup)
        self.assertTrue(exists, "RED: weapons.lua missing")
        if not exists: return
        lua.execute(DISPATCH)
        lua.execute('''
            _has_equip = false
            for _, e in ipairs(Hooks._all) do
                if e.class == PlayerInventory and e.method == "equip_selection" then
                    _has_equip = true; break
                end
            end
            if not _has_equip then return end
            local WPNS = kyohud.hud.weapons
            WPNS:refresh(managers.hud)
            inventory:equip_selection(2)
            _KY_dispatch(PlayerInventory, "equip_selection", inventory, 2)
            local snap1 = WPNS:get_snapshot()
            _sel_owner = snap1 and snap1.selected or nil
            other_inv:equip_selection(1)
            _KY_dispatch(PlayerInventory, "equip_selection", other_inv, 1)
            local snap2 = WPNS:get_snapshot()
            _sel_other = snap2 and snap2.selected or nil
            inventory:remove_selection(1)
            _KY_dispatch(PlayerInventory, "remove_selection", inventory, 1)
            local snap3 = WPNS:get_snapshot()
            _s1_present = snap3 and snap3.slots[1] and snap3.slots[1].present
        ''')
        g = lua.globals()
        if not g._has_equip:
            self.fail("RED: weapons.lua must PostHook PlayerInventory:equip_selection")
            return
        self.assertEqual(float(g._sel_owner), 2.0,
            "RED: owner inventory equip must refresh snapshot")
        self.assertEqual(float(g._sel_other), 2.0,
            "RED: non-owner inventory equip must be ignored")
        self.assertFalse(bool(g._s1_present),
            "RED: missing slot must clear previous state")


class HookIdempotenceAndContextTests(unittest.TestCase):
    def test_load_twice_across_contexts_unique_ids_singleton(self):
        lua, ok, exists = _load()
        self.assertTrue(exists, "RED: weapons.lua missing")
        if not exists: return
        lua.execute('_w_before = kyohud.hud.weapons')
        src = WEAPONS_PATH.read_text(encoding="utf-8-sig")
        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
        lua.execute(src)
        lua.execute('RequiredScript = "lib/units/beings/player/playerinventory"')
        lua.execute(src)
        hook_count = lua.eval("#Hooks._all")
        self.assertEqual(hook_count, 7, "RED: expected 7 hooks (3 HUD + 4 inventory)")
        local_before = lua.eval("#Hooks._all")
        lua.execute('RequiredScript = "lib/units/wrong"')
        lua.execute(src)
        lua.execute('''
            _all_ids = {}
            for _, e in ipairs(Hooks._all) do table.insert(_all_ids, e.id) end
            _total = #_all_ids
            _seen = {}; _dupes = 0
            for _, id in ipairs(_all_ids) do
                if _seen[id] then _dupes = _dupes + 1 end
                _seen[id] = true
            end
            _w_singleton = (kyohud.hud.weapons == _w_before)
            _w_not_nil = (kyohud.hud.weapons ~= nil)
        ''')
        g = lua.globals()
        self.assertEqual(g._dupes, 0, "RED: no duplicate hook IDs after double load")
        self.assertTrue(bool(g._w_singleton),
            "RED: singleton kyohud.hud.weapons must retain identity across reloads")
        self.assertTrue(bool(g._w_not_nil),
            "RED: singleton kyohud.hud.weapons must not be nil")
        wrong_total = lua.eval("#Hooks._all")
        self.assertEqual(wrong_total, local_before,
            "RED: wrong RequiredScript must install no hooks")


if __name__ == "__main__":
    unittest.main()
