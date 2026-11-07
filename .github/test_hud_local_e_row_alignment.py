"""One-line weapon headers and full-height, individually cut equipment cards."""
import unittest
from test_hud_local_e_compact import mounted


class LocalRowAlignmentTests(unittest.TestCase):
    def test_weapon_gap_is_visible_and_does_not_shift_equipment_on_switch(self):
        for width,height in ((1920,1080),(1280,720),(1680,1050)):
            for scale in (.95,1,1.05):
                with self.subTest(width=width,height=height,scale=scale):
                    lua=mounted()
                    lua.globals().pw=width;lua.globals().ph=height;lua.globals().s=scale
                    lua.execute(r'''
                        RT._parent_panel:set_shape(0,0,pw,ph)
                        kyohud.settings.hud_scale=s
                        RT:refresh_settings(managers.hud);RT:update(managers.hud,2,.1)
                        local eqx,eqw=E._root:x(),E._root:w()
                        for i=1,4 do
                            inventory:_native_set_equipped(i%2+1);W:refresh(managers.hud)
                            RT:update(managers.hud,2+i*.1,.1)
                            local a,b=W._cards[1]._root,W._cards[2]._root
                            if a:x()>b:x() then a,b=b,a end
                            assert(math.abs(b:x()-a:x()-a:w()-8*W._layout_cache.e)<.05,'RED: eight-unit transparent weapon gap')
                            assert(math.abs(E._root:x()-eqx)<.05 and math.abs(E._root:w()-eqw)<.05)
                            assert(W:verify() and E:verify())
                        end
                    ''')

    def test_headers_share_line_and_equipment_matches_weapon_height(self):
        lua=mounted()
        lua.execute(r'''
            local e=W._layout_cache.e
            for i=1,2 do
                local card=W._cards[i]
                assert(card._name_text:y()==card._mode_text:y(),'RED: common header line')
                assert(card._name_text:x()+card._name_text:w()<=card._mode_bg:x(),'header separation')
            end
            for _,i in ipairs({1,3,4}) do
                local row=E._rows[i]
                assert(math.abs(row._root:y()-12*e)<.05,'RED: equipment row y at 12e')
                assert(row._root:h()==W._cards[1]._root:h(),'RED: equipment row matches card height not root')
            end
            assert(E._rows[1]._cell_left_cut and E._rows[3]._cell_left_cut and E._rows[4]._cell_left_cut,'RED: all equipment cut both sides')
            assert(W:verify() and E:verify())
            local cut=E._rows[3]._cell_left_cut
            cut:set_alpha(0)
            assert(not E:verify(),'left cut certified')
            RT:update(managers.hud,1.1,.1)
            assert(E:verify() and E._rows[3]._cell_left_cut==cut)
        ''')


if __name__=='__main__':
    unittest.main()
