"""Equipment hooks execute in their real contexts, independently of presentation."""
from pathlib import Path
import unittest

from test_hud_equipment import _lua
from test_hud_equipment_consumables import _consumable_setup

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'lua/hud/equipment.lua'

EVENTS = r'''
function dispatch(cls, method, receiver, ...)
    for _, h in ipairs(Hooks._all) do
        if h.class == cls and h.method == method and h.kind == 'post' then
            h.fn(receiver, ...)
        end
    end
end
function PlayerManager:set_equipment_amount(id, amount, slot)
    self:equipment_data_by_name(id).amount[slot or 1] = Application:digest_value(amount,true)
end
function PlayerManager:equipment_data_by_name(id)
    for _, entry in ipairs(self._equipment.selections) do
        if entry.equipment == id then return entry end
    end
end
function PlayerManager:from_server_equipment_place_result(index)
    local entry=self._equipment.selections[index]
    local n=Application:digest_value(entry.amount[1],false)
    entry.amount[1]=Application:digest_value(n-1,true)
end
function PlayerManager:add_special() end
function PlayerManager:remove_special() end
function PlayerManager:clear_timers() self._timers={} end
function PlayerManager:reset() end
function PlayerManager:soft_reset() self._equipment={selections={},specials={}} end
function PlayerManager:player_destroyed() player_unit._alive=false;self:clear_timers() end
function PlayerManager:set_synced_grenades() end
function HUDManager:set_teammate_ability_radial(i,data) end
function HUDManager:activate_teammate_ability_radial(i,left,total) end
function HUDManager:set_teammate_grenade_cooldown(i,data) end
function HUDManager:set_cable_ties_amount(i,amount) end
function HUDManager:set_deployable_equipment_from_string(i,data) end
function HUDManager:set_teammate_deployable_equipment_amount_from_string(i,index,data) end
function HUDManager:set_teammate_grenades_amount(i,data) end
'''


def event_lua():
    lua, exists = _lua(setup=_consumable_setup(EVENTS + r'''
        managers.player:_native_set_equipment('trip_mine',{3,2})
        managers.player:_native_set_equipment('doctor_bag',{1})
        managers.player._equipment.selected_index=1
        managers.player:_native_set_grenades('pocket',1,2)
        _native_set_projectile_tweak('pocket',{ability=true,base_cooldown=30})
        managers.player:_native_set_specials('cable_tie',{1})
    '''))
    assert exists
    for context in ('lib/managers/playermanager', 'lib/managers/hudmanagerpd2'):
        lua.globals().RequiredScript = context
        lua.execute(SOURCE.read_text(encoding='utf-8-sig'))
    lua.execute('E=kyohud.hud.equipment;E:refresh(managers.hud)')
    return lua


class EquipmentEventsTests(unittest.TestCase):
    def test_absolute_pm_events_and_deferred_other_selection(self):
        l=event_lua()
        l.execute(r'''
            local pm=managers.player
            pm:set_equipment_amount('doctor_bag',0,1)
            dispatch(PlayerManager,'set_equipment_amount',pm,'doctor_bag',0,1)
            assert(E:get_snapshot().deployables.doctor_bag.quantities[1].raw==0,'PM hook must capture accepted state')
            pm:from_server_equipment_place_result(1)
            dispatch(PlayerManager,'from_server_equipment_place_result',pm,1)
            dispatch(PlayerManager,'from_server_equipment_place_result',pm,1)
            assert(E:get_snapshot().deployables.trip_mine.quantities[1].raw==2,'duplicate event must not consume twice')
        ''')

    def test_activity_is_distinct_and_survives_toggle_but_not_source_change(self):
        l=event_lua()
        l.execute(r'''
            _game_clock:set_time(1000)
            managers.player:_native_set_replenish_timer(1017)
            dispatch(HUDManager,'activate_teammate_ability_radial',managers.hud,1,8,10)
            _game_clock:set_time(1003)
            E:refresh(managers.hud)
            local s=E:get_snapshot()
            assert(s.activity and s.activity.known and s.activity.remaining==5,'capture while option off')
            assert(s.cooldown.remaining==14,'activity must not overwrite recharge')
            dispatch(HUDManager,'activate_teammate_ability_radial',managers.hud,2,99,100)
            E:refresh(managers.hud)
            assert(E:get_snapshot().activity.remaining==5,'remote panel must be ignored')
            dispatch(HUDManager,'activate_teammate_ability_radial',managers.hud,1,9,10)
            _game_clock:set_time(1004)
            E:refresh(managers.hud)
            assert(E:get_snapshot().activity.remaining==8,'extension must replace deadline')
            player_unit={_alive=true}
            E:refresh(managers.hud)
            assert(not E:get_snapshot().activity.known,'new occupant cannot inherit activity')
        ''')

    def test_direct_radial_stop_unknown_initial_and_reset(self):
        l=event_lua()
        l.execute(r'''
            assert(E:get_snapshot().activity and not E:get_snapshot().activity.known,'unobserved activity is unknown')
            dispatch(HUDManager,'set_teammate_ability_radial',managers.hud,1,{current=4,total=6})
            E:refresh(managers.hud)
            assert(E:get_snapshot().activity.remaining==4)
            dispatch(HUDManager,'activate_teammate_ability_radial',managers.hud,1,0)
            E:refresh(managers.hud)
            assert(E:get_snapshot().activity.known and not E:get_snapshot().activity.active,'stop must not divide 0/0')
            dispatch(PlayerManager,'soft_reset',managers.player)
            E:refresh(managers.hud)
            assert(not E:get_snapshot().activity.known,'reset must invalidate captured intent')
        ''')

    def test_last_cable_zero_is_proven_by_consumption_not_missing_table(self):
        l=event_lua()
        l.execute(r'''
            managers.player._equipment.specials.cable_tie=nil
            dispatch(PlayerManager,'remove_special',managers.player,'cable_tie')
            local s=E:get_snapshot()
            assert(s.cables.known and s.cables.raw==0,'confirmed last cable must stay zero')
            managers.player._equipment.specials={}
            E:refresh(managers.hud)
            assert(not E:get_snapshot().cables.known,'new specials source cannot inherit zero')
            dispatch(PlayerManager,'remove_special',managers.player,'cable_tie')
            assert(not E:get_snapshot().cables.known,'no-op remove is not proof of zero')
        ''')

    def test_hooks_idempotent_and_wrong_context_inert(self):
        l=event_lua()
        l.execute('before=#Hooks._all')
        for context in ('lib/managers/playermanager','lib/managers/hudmanagerpd2','wrong/context'):
            l.globals().RequiredScript=context
            l.execute(SOURCE.read_text(encoding='utf-8-sig'))
        l.execute('assert(#Hooks._all==before); assert(before>0,"no equipment hooks installed")')

    def test_source_replacement_and_destroy_cannot_leak_activity(self):
        l=event_lua()
        l.execute(r'''
            dispatch(HUDManager,'activate_teammate_ability_radial',managers.hud,1,9)
            E:refresh(managers.hud)
            assert(E:get_snapshot().activity.remaining==9)
            managers.player:player_destroyed(1)
            dispatch(PlayerManager,'player_destroyed',managers.player,1)
            assert(not E:get_snapshot().source_known,'custody must not retain inventory')
            player_unit={_alive=true}
            E:refresh(managers.hud)
            assert(not E:get_snapshot().activity.known,'respawn snapshot must be fresh')
        ''')

    def test_radial_feed_is_lightweight_and_cooldown_cancel_is_not_activity_stop(self):
        l=event_lua()
        l.execute(r'''
            dispatch(HUDManager,'activate_teammate_ability_radial',managers.hud,1,8,10)
            local digest=Application.digest_value
            reads=0
            Application.digest_value=function(self,...) reads=reads+1;return digest(self,...) end
            for i=1,30 do
                dispatch(HUDManager,'set_teammate_ability_radial',managers.hud,1,{current=4,total=6})
            end
            assert(reads==0,'per-frame radial must not scan inventory')
            dispatch(HUDManager,'set_teammate_grenade_cooldown',managers.hud,1,nil)
            E:refresh(managers.hud)
            assert(E:get_snapshot().activity.remaining==4,'recharge cancellation is not an activity stop')
        ''')

    def test_explicit_nil_cooldown_cancels_until_real_new_recharge(self):
        l=event_lua()
        l.execute(r'''
            managers.player:_native_set_replenish_timer(17)
            E:refresh(managers.hud)
            assert(E:get_snapshot().cooldown.active)
            dispatch(HUDManager,'set_teammate_grenade_cooldown',managers.hud,1,nil)
            E:refresh(managers.hud)
            assert(E:get_snapshot().cooldown.known and not E:get_snapshot().cooldown.active,'nil explicitly cancels HUD timer')
            dispatch(HUDManager,'set_teammate_grenade_cooldown',managers.hud,1,{end_time=17,duration=30})
            E:refresh(managers.hud)
            assert(E:get_snapshot().cooldown.active,'new accepted native recharge recovers')
        ''')

    def test_first_activity_event_after_projectile_change_survives_refresh(self):
        for method, args in (
            ('set_teammate_ability_radial', '{current=4,total=6}'),
            ('activate_teammate_ability_radial', '4,6'),
        ):
            with self.subTest(method=method):
                l=event_lua()
                l.execute(r'''
                    dispatch(HUDManager,'activate_teammate_ability_radial',managers.hud,1,8,10)
                    managers.player:_native_set_grenades('new_ability',1,1)
                    _native_set_projectile_tweak('new_ability',{ability=true})
                ''')
                l.execute(f"dispatch(HUDManager,'{method}',managers.hud,1,{args})")
                l.execute(r'''
                    E:refresh(managers.hud)
                    local s=E:get_snapshot()
                    assert(s.projectile.projectile_id=='new_ability')
                    assert(s.activity.known and s.activity.remaining==4,
                        'first activity event for new projectile must survive refresh')
                    assert(s.activity.duration==6,'new duration must replace old activity')
                    _game_clock:set_time(1)
                    E:refresh(managers.hud)
                    assert(E:get_snapshot().activity.remaining==3,'new activity must keep advancing')
                ''')

    def test_registry_replacement_invalidates_activity_even_with_same_id(self):
        l=event_lua()
        l.execute(r'''
            dispatch(HUDManager,'activate_teammate_ability_radial',managers.hud,1,8,10)
            local record=managers.player._global.synced_grenades[1]
            managers.player._global.synced_grenades={[1]=record}
            E:refresh(managers.hud)
            assert(not E:get_snapshot().activity.known,'new registry must not inherit event cache')
        ''')

    def test_opaque_text_is_preserved_without_numeric_conversion(self):
        l=event_lua()
        l.execute(r'''
            managers.player:_native_set_equipment('trip_mine',{0/0,math.huge})
            dispatch(HUDManager,'set_teammate_deployable_equipment_amount_from_string',managers.hud,1,1,
                {amount_str='CUSTOM STOCK',amount={0/0,math.huge}})
            local d=E:get_snapshot().deployables.trip_mine
            assert(d.amount_text=='CUSTOM STOCK','preserve explicit native text separately')
            assert(not d.quantities[1].known and not d.quantities[2].known,'text is not numerical evidence')
            managers.player:_native_set_equipment('trip_mine',{3,2})
            dispatch(PlayerManager,'set_equipment_amount',managers.player,'trip_mine',3,1)
            assert(E:get_snapshot().deployables.trip_mine.amount_text==nil,'fresh numeric source clears opaque fallback')
        ''')


if __name__=='__main__':
    unittest.main()
