"""Slot labels and an owned downs cell left of unchanged local health geometry."""
import unittest
from test_hud_local_e_compact import mounted


class SlotLabelsDownsBoxTests(unittest.TestCase):
    def test_switch_preserves_all_cell_bounds_and_downs_alignment(self):
        lua=mounted()
        lua.execute(r'''
            local e=W._layout_cache.e
            local card1_prim=W._cards[1]._root
            local card2_prim=W._cards[2]._root
            local eq_x,eq_w=E._root:x(),E._root:w()
            for i=1,6 do
                inventory:_native_set_equipped(i%2+1);W:refresh(managers.hud)
                RT:update(managers.hud,1+i*.1,.1)
                local c2=W._cards[2]._root
                local c1=W._cards[1]._root
                assert(c2:x()<c1:x(),'RED: native order card2 left card1 right')
                assert(W._cards[1]._root==card1_prim,'RED: card1 primitive identity')
                assert(W._cards[2]._root==card2_prim,'RED: card2 primitive identity')
                assert(math.abs(E._root:x()-eq_x)<.05,'RED: equipment x stable')
                assert(math.abs(E._root:w()-eq_w)<.05,'RED: equipment w stable')
                assert(math.abs(c2:x()-40*e)<.05,'RED: left start 40e')
                assert(math.abs(W._root:x()+c1:x()+c1:w()+4*e-E._root:x())<.05,'RED: weapon right/equipment gap 4e')
                assert(W:verify() and E:verify())
            end
            local P=kyohud.hud.player
            local d=P:_desired_layout()
            assert(d.downs_box.x+d.downs_box.w<d.gauge.x,'RED: downs box left of gauge')
            assert(d.downs_label_fs==d.downs_text_fs,'RED: same downs font size')
            assert(d.downs_label.y==d.downs_text.y and d.downs_label.h==d.downs_text.h,'RED: shared downs text line')
        ''')

    def test_slot_labels_follow_slots_not_equipped_position(self):
        lua=mounted()
        lua.execute(r'''
            assert(W._cards[2]._name_text:text()=='','RED: card 2 name empty')
            assert(not W._cards[2]._name_text:visible(),'RED: card 2 name hidden')
            assert(W._cards[1]._name_text:text()=='','RED: card 1 name empty')
            assert(not W._cards[1]._name_text:visible(),'RED: card 1 name hidden')
            inventory:_native_set_equipped(1);W:refresh(managers.hud)
            RT:update(managers.hud,1.1,.06)
            assert(W._cards[2]._root:x()<W._cards[1]._root:x())
            assert(W._cards[1]._name_text:text()=='')
            assert(not W._cards[1]._name_text:visible())
            assert(W._cards[2]._name_text:text()=='')
            assert(not W._cards[2]._name_text:visible())
            assert(W:verify())
            managers.player:_native_set_equipment('trip_mine',{3,2})
            E:refresh(managers.hud);RT:update(managers.hud,1.2,.06)
            assert(W._cards[1]._name_text:text()=='')
            assert(not W._cards[1]._name_text:visible())
            assert(W._cards[2]._name_text:text()=='')
            assert(not W._cards[2]._name_text:visible())
            assert(W:verify() and E:verify())
        ''')

    def test_downs_cell_is_left_of_health_without_moving_the_gauge(self):
        lua=mounted()
        lua.execute(r'''
            local P=kyohud.hud.player
            assert(P._downs_bg,'RED: owned downs background')
            local d=P:_desired_layout()
            assert(d.downs_box.x+d.downs_box.w<d.gauge.x,'RED: cell left of health')
            local e=W._layout_cache.e
            local margin=RT._root_panel:w()*.02
            local old_x=RT._root_panel:w()-margin-300*e
            assert(math.abs(P._root:x()+d.gauge.x-old_x)<.05,'gauge world X preserved')
            assert(math.abs(d.gauge.w-300*e)<.05)
            assert(math.abs(d.gauge.h-42*360*e/440)<.05)
            assert(math.abs(d.downs_box.y-(d.gauge.y+P._gauge._armor_bg:y()))<.05)
            assert(P:verify())
            local bg=P._downs_bg
            local x,y,w,h=bg:x(),bg:y(),bg:w(),bg:h()
            bg:set_shape(x+5,y,w,h)
            assert(not P:verify(),'cell corruption rejected')
            RT:update(managers.hud,1.1,.06)
            assert(P:verify() and P._downs_bg==bg,'ordinary update repairs same cell')
            P:render({downs=0,health={valid=false},armor={valid=false}})
            assert(P._downs_text:text()=='0')
            P:render({health={valid=false},armor={valid=false}})
            assert(P._downs_text:text()=='--')
        ''')

    def test_downs_cell_and_gauge_scale_together(self):
        for width,height in ((1920,1080),(1680,1050),(1280,720)):
            for scale in (.95,1,1.05):
                with self.subTest(width=width,height=height,scale=scale):
                    lua=mounted()
                    lua.globals().pw=width;lua.globals().ph=height
                    lua.globals().s=scale
                    lua.execute(r'''
                        RT._parent_panel:set_shape(0,0,pw,ph)
                        kyohud.settings.hud_scale=s
                        RT:refresh_settings(managers.hud)
                        RT:update(managers.hud,2,.06)
                        local P=kyohud.hud.player
                        local d=P:_desired_layout()
                        local e=math.min(pw/1920,ph/1080)*s
                        assert(P:verify())
                        assert(W._cards[1]._name_text:text()=='')
                        assert(not W._cards[1]._name_text:visible())
                        assert(W._cards[2]._name_text:text()=='')
                        assert(not W._cards[2]._name_text:visible())
                        assert(d.downs_box.x+d.downs_box.w<d.gauge.x)
                        assert(math.abs(d.gauge.w-300*e)<.05)
                        assert(math.abs(P._root:x()+d.gauge.x-(pw-pw*.02-300*e))<.05)
                    ''')

    def test_downs_background_style_recovery_and_lifecycle(self):
        lua=mounted()
        lua.execute(r'''
            local P=kyohud.hud.player
            local bg=P._downs_bg
            bg:set_alpha(0)
            assert(not P:verify())
            RT:update(managers.hud,1.1,.06)
            assert(P:verify() and P._downs_bg==bg)
            local root=P._root
            local setter=bg.set_shape
            bg:set_shape(99,0,1,1)
            bg.set_shape=function() end
            RT:update(managers.hud,1.2,.06)
            assert(not P:verify() and not root:visible())
            bg.set_shape=setter
            RT:update(managers.hud,1.3,.06)
            assert(P:verify() and P._root==root and P._downs_bg==bg)
            kyohud.settings.enable_player=false
            RT:refresh_settings(managers.hud)
            assert(not P._root and not P._downs_bg and not alive(bg))
            kyohud.settings.enable_player=true
            RT:refresh_settings(managers.hud)
            assert(P:verify() and P._downs_bg~=bg)
        ''')

if __name__=='__main__':
    unittest.main()
