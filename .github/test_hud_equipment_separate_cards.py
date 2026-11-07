"""Separate equipment silhouettes, larger modes/counts, current stock only."""
import unittest
from test_hud_local_e_compact import mounted


class SeparateEquipmentCardsTests(unittest.TestCase):
    def test_each_equipment_has_its_own_cut_and_centered_content(self):
        lua=mounted()
        lua.execute(r'''
            tweak_data.equipments=tweak_data.equipments or {}
            tweak_data.equipments.doctor_bag={icon='fixture_medical'}
            tweak_data.blackmarket.projectiles.frag.icon='fixture_grenade'
            tweak_data.hud_icons={get_icon_data=function(_,id) return id,{0,0,48,48} end}
            DB={has=function() return true end};Idstring=function(s) return s end
            E._icon_cache=nil;E:refresh(managers.hud);E:_present()
            local e=W._layout_cache.e
            local cuts={}
            for _,i in ipairs({1,3,4}) do
                local row=E._rows[i]
                assert(row._cell_bg and row._cell_cut,'RED: one silhouette per equipment')
                assert(row._cell_bg:parent()==row._root and row._cell_cut:parent()==row._root)
                assert(not cuts[row._cell_cut]);cuts[row._cell_cut]=true
                local center=row._cell_both and row._root:w()/2 or (row._root:w()-4*e)/2
                assert(math.abs(row._icon:x()+row._icon:w()/2-center)<.05)
                assert(math.abs(row._value:x()+row._value:w()/2-center)<.05)
                assert(row._value:font_size()>=20*e-.05,'RED: larger stock numbers')
                local left=row._cell_left_cut and row._cell_left_cut:w() or 0
                assert(math.abs(left+row._cell_bg:w()+row._cell_cut:w()-row._root:w())<.05)
                local top=math.min(row._icon:y(),row._value:y())
                local bottom=math.max(row._icon:y()+row._icon:h(),row._value:y()+row._value:h())
                assert(math.abs((top+bottom)/2-row._root:h()/2)<.05,'vertical content centering')
            end
            assert(not E._background and not E._cut,'no common equipment silhouette')
            assert(E._rows[4]._value:text()=='2','RED: available charges only')
            assert(E:get_snapshot().projectile.maximum.raw==2,'collector capacity retained')
            for i=1,2 do assert(W._cards[i]._mode_text:font_size()>=16*e-.05,'RED: larger modes') end
            assert(W:verify() and E:verify())
        ''')

    def test_per_card_cut_corruption_repair_switch_and_cleanup(self):
        lua=mounted()
        lua.execute(r'''
            local row=E._rows[1]
            local bg,cut=row._cell_bg,row._cell_cut
            assert(bg and cut,'RED: per-card owned geometry')
            local original=Vector3;local allocations=0
            Vector3=function(...) allocations=allocations+1;return original(...) end
            for i=1,6 do
                inventory:_native_set_equipped(i%2+1);W:refresh(managers.hud)
                RT:update(managers.hud,1+i*.1,.1)
                assert(row._cell_bg==bg and row._cell_cut==cut and E:verify() and W:verify())
            end
            assert(allocations==0)
            cut:set_shape(cut:x()+5,cut:y(),cut:w(),cut:h())
            assert(not E:verify())
            RT:update(managers.hud,2,.1)
            assert(E:verify() and row._cell_cut==cut)
            bg:set_alpha(0)
            assert(not E:verify())
            RT:update(managers.hud,2.1,.1)
            assert(E:verify() and row._cell_bg==bg)
            kyohud.settings.enable_equipment=false;RT:refresh_settings(managers.hud)
            assert(not alive(bg) and not alive(cut) and W:verify())
        ''')

    def test_two_deployables_fit_through_scale_matrix_without_capacity_suffix(self):
        for width,height in ((1920,1080),(1280,720),(1680,1050)):
            for scale in (.95,1,1.05):
                with self.subTest(width=width,height=height,scale=scale):
                    lua=mounted()
                    lua.globals().pw=width;lua.globals().ph=height;lua.globals().s=scale
                    lua.execute(r'''
                        managers.player:_native_set_equipment('trip_mine',{3,2})
                        RT._parent_panel:set_shape(0,0,pw,ph)
                        kyohud.settings.hud_scale=s
                        RT:refresh_settings(managers.hud);RT:update(managers.hud,2,.06)
                        assert(W:verify() and E:verify(),'full four-equipment loadout fits')
                        assert(E._rows[2]._value:text()=='3|2','ordered subquantities retained compactly')
                        assert(E._rows[4]._value:text()=='2')
                        for i=1,4 do assert(E._rows[i]._cell_cut and E._rows[i]._root:visible()) end
                        assert(W._cards[1]._name_text:text()=='')
                        assert(not W._cards[1]._name_text:visible())
                        assert(W._cards[2]._name_text:text()=='')
                        assert(not W._cards[2]._name_text:visible())
                    ''')

if __name__=='__main__':
    unittest.main()
