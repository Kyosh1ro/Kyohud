"""Owner transitions required by the compact crew consumer."""
import unittest
from test_hud_crew import _lua, ROOT

SETUP = '''
    PlayerManager={}; PlayerManager.__index=PlayerManager
    local pm=setmetatable({_global={synced_deployables={[2]={deployable='ammo_bag',amount=2}},
        synced_cable_ties={[2]={amount=1}},synced_grenades={}}},PlayerManager)
    managers.player=pm
    function PlayerManager:get_synced_deployable_equipment(id) return self._global.synced_deployables[id] end
    function PlayerManager:get_synced_cable_ties(id) return self._global.synced_cable_ties[id] end
    function PlayerManager:get_synced_grenades(id) return self._global.synced_grenades[id] end
    function PlayerManager:set_synced_cable_ties(id,amount) self._global.synced_cable_ties[id]={amount=amount} end
    local post=Hooks.PostHook
    function Hooks:PostHook(cls,method,id,fn)
        post(self,cls,method,id,fn)
        local original=cls[method]
        cls[method]=function(self,...) original(self,...); fn(self,...) end
    end
'''


class CrewOwnerContractTests(unittest.TestCase):
    def test_departure_rejoin_keeps_old_registry_unqualified(self):
        lua,ok=_lua()
        self.assertTrue(ok)
        lua.execute(SETUP + '''
            A=kyohud.hud.actors
            A:refresh_crew(managers.hud,0)
            local session=managers.network:session()
            local Peer=getmetatable(session:peer(2))
            for _,rec in ipairs(managers.criminals:characters()) do if rec.peer_id==2 then rec.taken=false end end
            session._peers[2]=nil
            A:refresh_crew(managers.hud,.5)
            session._peers[2]=Peer:new(2,'Rejoined',50,0,nil)
            for _,rec in ipairs(managers.criminals:characters()) do if rec.peer_id==2 then rec.taken=true end end
            A:refresh_crew(managers.hud,1)
            _old_equipment=nil
            for _,e in ipairs(A:get_crew_snapshot()) do if e.peer_id==2 then _old_equipment=e.equipment end end
        ''')
        self.assertIsNone(lua.globals()._old_equipment)

    def test_selection_event_recollects_actual_weapon_and_turret_ammo_event_hides_personal(self):
        lua, ok = _lua()
        self.assertTrue(ok)
        lua.execute(SETUP + '''
            function HUDManager:_set_teammate_weapon_selected(i,id,icon) end
            function PlayerManager:get_synced_ammo_info(id) return self._global.synced_ammo_info[id] end
            function PlayerManager:get_player_turret_for_peer(id) return self._turret end
            function PlayerManager:set_synced_ammo_info(id,selection,a,b,c,d)
                self._global.synced_ammo_info[id][selection]={a,b,c,d}
            end
            managers.player._global.synced_ammo_info={[2]={[1]={30,7,67,120}}}
            local function gun(id)
                local base={get_name_id=function() return id end,weapon_tweak_data=function() return {name_id=id} end}
                return {base=function() return base end}
            end
            _gun_a=gun('gun_a'); _gun_b=gun('gun_b')
            _inventory={_gun=_gun_a,equipped_selection=function() return 1 end,
                equipped_unit=function(self) return self._gun end,
                unit_by_selection=function(self) return self._gun end}
            for _,rec in ipairs(managers.criminals:characters()) do
                if rec.peer_id==2 then rec.unit={inventory=function() return _inventory end} end
            end
        ''')
        for context in ('lib/managers/playermanager','lib/managers/hudmanagerpd2'):
            lua.globals().RequiredScript=context
            lua.execute((ROOT/'lua/hud/actors.lua').read_text(encoding='utf-8-sig'))
        lua.execute('''
            A=kyohud.hud.actors
            A:refresh_crew(managers.hud,0)
            assert(A:get_crew_snapshot()[2].weapon.weapon_id=='gun_a')
            _inventory._gun=_gun_b
            managers.hud:_set_teammate_weapon_selected(2,1,'icon')
            _after=A:get_crew_snapshot()[2].weapon.weapon_id
            managers.player._turret={}
            managers.player:set_synced_ammo_info(2,1,30,8,100,120)
            _turret_weapon=A:get_crew_snapshot()[2].weapon
        ''')
        self.assertEqual(lua.globals()._after,'gun_b')
        self.assertIsNone(lua.globals()._turret_weapon)

    def test_latest_record_not_initial_record_is_owner_evidence(self):
        lua, ok = _lua()
        self.assertTrue(ok)
        lua.execute(SETUP)
        lua.execute('''
            A=kyohud.hud.actors
            A:refresh_crew(managers.hud,0)
            managers.player._global.synced_deployables[2]={deployable='doctor_bag',amount=1}
            A:refresh_crew(managers.hud,.5)
            local session=managers.network:session()
            local Peer=getmetatable(session:peer(2))
            session._peers[2]=Peer:new(2,'New',1,0,nil)
            A:refresh_crew(managers.hud,1)
            _equipment=nil
            for _,e in ipairs(A:get_crew_snapshot()) do if e.peer_id==2 then _equipment=e.equipment end end
        ''')
        self.assertIsNone(lua.globals()._equipment)

    def test_event_certifies_only_its_channel_after_peer_replacement(self):
        lua, ok = _lua()
        self.assertTrue(ok)
        lua.execute(SETUP)
        lua.globals().RequiredScript='lib/managers/playermanager'
        lua.execute((ROOT/'lua/hud/actors.lua').read_text(encoding='utf-8-sig'))
        lua.execute('''
            A=kyohud.hud.actors
            A:refresh_crew(managers.hud,0)
            assert(A:get_crew_snapshot()[2].equipment.deployable.amount==2)
            local session=managers.network:session()
            local Peer=getmetatable(session:peer(2))
            session._peers[2]=Peer:new(2,'Replacement',99,0,nil)
            A:refresh_crew(managers.hud,.5)
            managers.player:set_synced_cable_ties(2,3)
            local snap=A:get_crew_snapshot()[2]
            _dep=snap.equipment and snap.equipment.deployable
            _cable=snap.equipment and snap.equipment.cable_ties.amount
        ''')
        self.assertIsNone(lua.globals()._dep,'a cable event must not reauthorize stale deployable')
        self.assertEqual(lua.globals()._cable,3)

    def test_replacement_before_poll_does_not_publish_old_name_with_new_event(self):
        lua, ok = _lua()
        self.assertTrue(ok)
        lua.execute(SETUP)
        lua.globals().RequiredScript='lib/managers/playermanager'
        lua.execute((ROOT/'lua/hud/actors.lua').read_text(encoding='utf-8-sig'))
        lua.execute('''
            A=kyohud.hud.actors
            A:refresh_crew(managers.hud,0)
            local session=managers.network:session()
            local Peer=getmetatable(session:peer(2))
            session._peers[2]=Peer:new(2,'Replacement',99,0,nil)
            managers.player:set_synced_cable_ties(2,3)
            _stale=false
            for _,e in ipairs(A:get_crew_snapshot()) do
                if e.peer_id==2 and e.name~='Replacement' then _stale=true end
            end
            A:refresh_crew(managers.hud,.5)
            _recovered=false
            for _,e in ipairs(A:get_crew_snapshot()) do
                if e.peer_id==2 then _recovered=e.name=='Replacement' end
            end
        ''')
        self.assertIs(lua.globals()._stale,False)
        self.assertIs(lua.globals()._recovered,True)


if __name__=='__main__': unittest.main()
