"""Persistent equipment rows and local runtime wiring; no native mutations."""
import json
from pathlib import Path
import unittest

from test_hud_weapons_integration import _lua_with_weapons_runtime, _ACTIVATE_BOILER
from test_hud_equipment import NATIVE_EQUIPMENT_FIXTURE
from test_hud_equipment_consumables import NATIVE_CONSUMABLES_FIXTURE
from test_hud_equipment_events import EVENTS
from test_hud_alerts_integration import _lua_with_options

ROOT=Path(__file__).resolve().parents[1]
COMPONENT=ROOT/'lua/hud/components/equipment.lua'


def presentation():
    l,_,_=_lua_with_weapons_runtime()
    l.execute(_ACTIVATE_BOILER)
    l.execute(NATIVE_EQUIPMENT_FIXTURE+NATIVE_CONSUMABLES_FIXTURE+EVENTS+r'''
        managers.player:_native_set_equipment('trip_mine',{3,2})
        managers.player:_native_set_equipment('doctor_bag',{1})
        managers.player._equipment.selected_index=1
        managers.player:_native_set_grenades('pocket',1,2)
        _native_set_projectile_tweak('pocket',{ability=true,base_cooldown=30})
        managers.player:_native_set_specials('cable_tie',{3})
        _game_clock:set_time(1000)
        managers.player:_native_set_replenish_timer(1017)
    ''')
    assert COMPONENT.is_file(), 'equipment component missing'
    l.execute(COMPONENT.read_text(encoding='utf-8-sig'))
    for context in ('lib/managers/playermanager','lib/managers/hudmanagerpd2'):
        l.globals().RequiredScript=context
        l.execute((ROOT/'lua/hud/equipment.lua').read_text(encoding='utf-8-sig'))
    l.execute(r'''
        E=kyohud.hud.equipment; RT=kyohud.hud.runtime
        kyohud.settings.enable_equipment=true
        RT:refresh_settings(managers.hud)
    ''')
    return l


class EquipmentPresentationTests(unittest.TestCase):
    def test_mount_current_values_and_event_before_poll(self):
        l=presentation()
        l.execute(r'''
            assert(E._root and E:verify(),'runtime must mount verified equipment')
            assert(E._rows[1]._value:text()=='3 | 2','subquantities must stay ordered')
            assert(E._rows[3]._value:text()=='3','cables')
            assert(E._rows[4]._value:text()=='1 / 2','charges')
            local primitive=E._rows[2]._value
            RT:update(managers.hud,1,0.06)
            managers.player:set_equipment_amount('doctor_bag',0,1)
            dispatch(PlayerManager,'set_equipment_amount',managers.player,'doctor_bag',0,1)
            RT:update(managers.hud,1.06,0.06)
            assert(primitive==E._rows[2]._value and primitive:text()=='0','dirty event before recovery')
            _game_clock:set_time(1001)
            RT:update(managers.hud,1.12,0.06)
            assert(E._rows[5]._value:text()=='16s','cooldown advances between polls')
        ''')

    def test_readback_failure_hidden_then_repaired_on_same_primitives(self):
        l=presentation()
        l.execute(r'''
            local row=E._rows[1]
            local root,value=E._root,row._value
            value:set_text('corrupt')
            assert(not E:verify())
            local setter=value.set_text
            value.set_text=function() end
            RT:update(managers.hud,1,0.06)
            assert(not E._root:visible(),'invalid render must hide only owned root')
            value.set_text=setter
            RT:update(managers.hud,1.06,0.06)
            assert(E:verify() and E._root:visible())
            assert(root==E._root and value==E._rows[1]._value,'repair must retain primitives')
            value:set_font_size(99)
            assert(not E:verify(),'font readback')
            RT:update(managers.hud,1.12,0.06)
            assert(E:verify())
            local x,y,w,h=root:x(),root:y(),root:w(),root:h()
            root:set_shape(x+12,y,w,h)
            assert(not E:verify(),'root position readback')
            RT:update(managers.hud,1.18,0.06)
            assert(E:verify() and root==E._root)
        ''')

    def test_toggle_late_vr_budget_and_layout_do_not_move_existing_blocks(self):
        l=presentation()
        l.execute(r'''
            local parent=RT._root_panel
            local sentinel=parent:panel({name='native_sentinel'})
            sentinel:set_shape(13,14,15,16)
            kyohud.settings.enable_equipment=false;RT:refresh_settings(managers.hud)
            assert(not E._root and alive(sentinel))
            managers.player:_native_set_specials('cable_tie',{0})
            kyohud.settings.enable_equipment=true;RT:refresh_settings(managers.hud)
            assert(E._rows[3]._value:text()=='0')
            for _,size in ipairs({{1920,1080},{3440,1440},{1280,1024}}) do
                for _,scale in ipairs({0.95,1,1.05}) do
                    parent:set_shape(0,0,size[1],size[2]);kyohud.settings.hud_scale=scale
                    E:refresh_settings(managers.hud)
                    local p=kyohud.hud.player:_compute_layout(size[1],size[2])
                    assert(E._root:x()+E._root:w()<p.x,'equipment must stay left of player/weapons region')
                    assert(E:verify())
                end
            end
            parent:set_shape(0,0,100,50);E:refresh_settings(managers.hud)
            assert(not E._root:visible(),'insufficient budget hides owned block')
            IS_VR=true;E:refresh_settings(managers.hud);assert(not E._root)
            assert(sentinel:x()==13 and sentinel:w()==15 and sentinel:visible(),'native intact')
        ''')

    def test_component_instances_measurement_corruption_and_safe_dead_teardown(self):
        l=presentation()
        l.execute(r'''
            local component=kyohud.hud.equipment_component
            local a=component.new(E._root,'independent_a')
            local b=component.new(E._root,'independent_b')
            assert(a and b and a._value~=b._value)
            for _,p in ipairs({a._label,a._value}) do
                p.text_rect=function(self) return 0,0,#self:text()*self:font_size()*.6,self:font_size() end
            end
            a:layout(0,0,160,28);b:layout(0,28,160,28)
            a:render(string.rep('Équipement ',40),'4s',.5,true)
            b:render('B','0',nil,false)
            assert(a:verify() and b:verify(),'measured fitting')
            assert(a._label:text()~=string.rep('Équipement ',40))
            a._fill:set_shape(a._fill:x(),a._fill:y(),1,a._fill:h())
            assert(not a:verify(),'progress geometry must be read')
            a:render(string.rep('Équipement ',40),'4s',.5,true)
            assert(a:verify() and b._value:text()=='0')
            local label=a._label
            label._alive=false
            label.x=function() error('dead read') end
            assert(not a:verify(),'dead required primitive fails closed')
            E._root._alive=false
            a:destroy();a:destroy();b:destroy()
        ''')

    def test_rebuild_preserves_activity_new_heist_clears_it(self):
        l=presentation()
        l.execute(r'''
            dispatch(HUDManager,'activate_teammate_ability_radial',managers.hud,HUDManager.PLAYER_PANEL,8,10)
            _game_clock:set_time(1002)
            RT:rebuild(managers.hud)
            assert(E:get_snapshot().activity.remaining==6,'graphics is not heist reset')
            E:on_heist_start(managers.hud)
            E:refresh(managers.hud)
            assert(not E:get_snapshot().activity.known)
        ''')

    def test_root_visibility_is_certified_and_setter_recovery_reuses_root(self):
        l=presentation()
        l.execute(r'''
            local root=E._root
            root:set_visible(false)
            local setter=root.set_visible
            root.set_visible=function() end
            RT:update(managers.hud,1,.06)
            assert(not E:verify(),'hidden owned root must not be certified')
            root.set_visible=setter
            RT:update(managers.hud,1.06,.06)
            assert(E:verify() and root:visible() and root==E._root)
        ''')


class EquipmentIntegrationContractTests(unittest.TestCase):
    def test_real_json_roundtrip_old_save_and_independent_toggles(self):
        l,ok=_lua_with_options()
        self.assertTrue(ok)
        l.execute(r'''
            local f=io.open(kyohud._settings_path,'w');f:write('{"enable_player":true}');f:close()
            kyohud.Load()
            assert(kyohud.settings.enable_equipment==false,'old save inherits default off')
            for _,value in ipairs({'on','off'}) do
                MenuCallbackHandler:KY_ToggleEquipment({value=function() return value end})
                local decoded=json.decode(_ky_mem_files[kyohud._settings_path])
                assert(decoded.enable_equipment==(value=='on'),'actual serialized bool')
                kyohud.settings.enable_equipment=nil;kyohud.Load()
                assert(kyohud.settings.enable_equipment==(value=='on'),'true and false roundtrip')
                assert(kyohud.settings.enable_player==true,'independent player toggle')
            end
        ''')

    def test_option_persistence_callback_menu_and_languages(self):
        l,ok=_lua_with_options()
        self.assertTrue(ok)
        l.execute(r'''
            assert(kyohud._defaults.enable_equipment==false,'default off')
            saved=0;refreshed=0
            kyohud.Save=function() saved=saved+1 end
            managers.hud={}
            kyohud.hud=kyohud.hud or {};kyohud.hud.runtime={refresh_settings=function() refreshed=refreshed+1 end}
            assert(type(MenuCallbackHandler.KY_ToggleEquipment)=='function')
            MenuCallbackHandler:KY_ToggleEquipment({value=function() return 'on' end})
            assert(kyohud.settings.enable_equipment==true and saved==1 and refreshed==1)
            MenuCallbackHandler:KY_ToggleEquipment({value=function() return 'off' end})
            assert(kyohud.settings.enable_equipment==false)
        ''')
        menu=json.loads((ROOT/'menu/menu.json').read_text(encoding='utf-8-sig'))
        def walk(value):
            if isinstance(value,dict):
                yield value
                for child in value.values(): yield from walk(child)
            elif isinstance(value,list):
                for child in value: yield from walk(child)
        entries=[v for v in walk(menu) if v.get('value')=='enable_equipment']
        self.assertEqual(len(entries),1)
        self.assertIs(entries[0]['default_value'],False)
        self.assertEqual(entries[0]['callback'],'KY_ToggleEquipment')
        for language in ('english','french'):
            loc=json.loads((ROOT/f'loc/{language}.json').read_text(encoding='utf-8-sig'))
            for key in ('ky_opt_enable_equipment','ky_opt_enable_equipment_desc','ky_hud_equipment_deployable',
                        'ky_hud_equipment_cables','ky_hud_equipment_throwable','ky_hud_equipment_ability',
                        'ky_hud_equipment_cooldown','ky_hud_equipment_active','ky_hud_equipment_unlimited'):
                self.assertTrue(loc.get(key),key)
                self.assertIn(key,(ROOT/'lua/ky_localization.lua').read_text(encoding='utf-8-sig'))

    def test_manifest_exact_contexts_and_component_order(self):
        hooks=json.loads((ROOT/'mod.txt').read_text(encoding='utf-8-sig'))['hooks']
        contexts=[h['hook_id'] for h in hooks if h['script_path']=='lua/hud/equipment.lua']
        self.assertEqual(contexts,['lib/managers/playermanager','lib/managers/hudmanagerpd2'])
        hud=[h['script_path'] for h in hooks if h['hook_id']=='lib/managers/hudmanagerpd2']
        self.assertEqual(hud.count('lua/hud/components/equipment.lua'),1)
        self.assertLess(hud.index('lua/hud/components/equipment.lua'),hud.index('lua/hud/equipment.lua'))


if __name__=='__main__': unittest.main()
