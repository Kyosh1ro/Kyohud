"""Fresh scalar eligibility must not broaden the public actor contract."""
import unittest
from test_hud_crew_online_native import online_runtime


class CrewOnlineCoverageTests(unittest.TestCase):
    def test_zero_is_known_but_unknown_ammo_stays_native(self):
        lua = online_runtime()
        lua.execute('''
            managers.player:set_synced_ammo_info(2,2,40,0,0,160)
            R:update(managers.hud,1.6,.05)
            assert(C._cards[2]._inactive_ammo_text:text()=='000/000')
            _zero=targets[5]:alpha()==0
            managers.player:set_synced_ammo_info(2,2,40,nil,nil,160)
            R:update(managers.hud,2.2,.05)
            assert(C._cards[2]._inactive_ammo_text:text()=='---/---')
            _unknown=targets[5]:alpha()==.7
            _active=targets[1]:alpha()==0
        ''')
        self.assertIs(lua.globals()._zero, True)
        self.assertIs(lua.globals()._unknown, True)
        self.assertIs(lua.globals()._active, True)

    def test_known_grenade_leaves_only_and_teardown_metadata(self):
        lua = online_runtime()
        lua.execute('''
            tweak_data.blackmarket=tweak_data.blackmarket or {}
            tweak_data.blackmarket.projectiles={frag={throwable=true,name_id='frag'}}
            managers.player._global.synced_grenades[2]={grenade='frag',amount=0}
            local player=managers.hud._teammate_panels[2]._panel:child('player')
            local gren=player:panel({name='grenades_panel'})
            local leaves={}
            for _,name in ipairs({'bg','grenades_icon','amount'}) do
                local p=gren:bitmap({name=name}); p:set_alpha(.4)
                leaves[#leaves+1]=p
            end
            local radial=gren:bitmap({name='grenades_radial'}); radial:set_alpha(.6)
            R:update(managers.hud,1.6,.05)
            assert(C:_verify_render(),'known grenade presentation')
            _masked=true
            for _,p in ipairs(leaves) do if p:alpha()~=0 then _masked=false end end
            _radial=radial:alpha()==.6
            C:get_buff_exclusions(kyohud._panel or C._parent_panel)
            C:unmount()
            R:_coordinate_h5_native_duplicates()
            _restored=true
            for _,p in ipairs(leaves) do if p:alpha()~=.4 then _restored=false end end
            _cleared=C._native_coverage==nil and C._buff_exclusions==nil
        ''')
        for key in ('_masked','_radial','_restored','_cleared'):
            self.assertIs(lua.globals()[key], True, key)

    def test_non_network_metrics_are_not_eligible(self):
        lua = online_runtime()
        lua.execute('''
            local r=A._store[2]
            r.health={valid=true,current=10,total=10,ratio=1,provenance='local'}
            r.armor={valid=true,current=10,total=10,ratio=1,provenance='local'}
            local public=A:get_crew_snapshot()[2]
            assert(public.health==nil and public.armor==nil)
            local rows=A:write_crew_native_coverage({})
            _health=rows[2].health; _armor=rows[2].armor
        ''')
        self.assertIs(lua.globals()._health, False)
        self.assertIs(lua.globals()._armor, False)

    def test_pm_registry_replacement_releases_without_waiting_for_poll(self):
        lua = online_runtime()
        lua.execute('''
            local old=managers.player._global.synced_ammo_info
            managers.player._global.synced_ammo_info={}
            R:_coordinate_h5_native_duplicates()
            _released=true
            for i=1,8 do if targets[i]:alpha()~=.7 then _released=false end end
            _other=targets[9]:alpha()==0
            managers.player._global.synced_ammo_info=old
            R:_coordinate_h5_native_duplicates()
            _recovered=targets[1]:alpha()==0
        ''')
        self.assertIs(lua.globals()._released, True)
        self.assertIs(lua.globals()._other, True)
        self.assertIs(lua.globals()._recovered, True)

    def test_source_loss_releases_and_same_source_recovers(self):
        lua = online_runtime()
        lua.execute('''
            local session=managers.network._session
            managers.network._session=nil
            R:_coordinate_h5_native_duplicates()
            _released=true
            for _,p in ipairs(targets) do if p:alpha()~=.7 then _released=false end end
            managers.network._session=session
            R:_coordinate_h5_native_duplicates()
            _recovered=true
            for _,p in ipairs(targets) do if p:alpha()~=0 then _recovered=false end end
        ''')
        self.assertIs(lua.globals()._released, True)
        self.assertIs(lua.globals()._recovered, True)
