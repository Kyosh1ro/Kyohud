"""Compact E composition, exercising the existing local collectors/runtime."""
import unittest
from test_hud_final_integration import _crew_lua

SETUP = r'''
kyohud.settings.enable_hud_foundation=true
kyohud.settings.enable_player=true
kyohud.settings.enable_weapons=true
kyohud.settings.enable_equipment=true
kyohud.settings.enable_crew=false
managers.player.current_state=function() return 'standard' end
u1,b1=make_weapon('new_m1014');b1:_native_set_ammo(8,6,32,40)
u2,b2=make_weapon('new_m16');b2:_native_set_ammo(30,25,120,150)
inventory:_native_set_slot(1,u1);inventory:_native_set_slot(2,u2)
inventory:_native_set_equipped(2)
managers.player:_native_set_equipment('doctor_bag',{2})
managers.player._equipment.selected_index=1
managers.player:_native_set_grenades('frag',2,2)
_native_set_projectile_tweak('frag',{throwable=true})
managers.player:_native_set_specials('cable_tie',{3})
RT=kyohud.hud.runtime;W=kyohud.hud.weapons;E=kyohud.hud.equipment
RT:refresh_settings(managers.hud)
RT:update(managers.hud,1,.06)
'''


def mounted():
    lua, *present = _crew_lua()
    assert all(present)
    lua.execute(SETUP)
    return lua


class CompactCompositionTests(unittest.TestCase):
    def test_equipment_is_inside_same_horizontal_loadout(self):
        lua = mounted()
        lua.execute(r'''
            assert(W:verify() and E:verify())
            assert(W._root:h()<=102, 'compact header and numeric rows, not fixed 120-high cards')
            assert(math.abs(W._root:y()-E._root:y())<.05, 'RED: common row top')
            assert(E._root:x()>W._root:x(), 'RED: equipment right of weapons')
            assert(E._root:x()+E._root:w()<=W._root:x()+W._root:w()+.05)
            assert(E._rows[1]._root:x()<E._rows[3]._root:x())
            assert(E._rows[3]._root:x()<E._rows[4]._root:x())
            assert(math.abs(E._rows[1]._root:y()-E._rows[4]._root:y())<.05)
            local c=W._cards[2]
            local _,_,mode_w=c._mode_text:text_rect()
            assert(c._mode_bg:w()<=mode_w+10, 'RED: intrinsic badge, not wide white cell')
            local P=kyohud.hud.player
            assert(W._root:y()+W._root:h()<=P._root:y()+22+.05)
            local bg=E._rows[1]._cell_bg
            bg:set_shape(1,0,bg:w(),bg:h())
            assert(not E:verify(),'RED: shared equipment background must be certified')
            E:_present()
            assert(E:verify() and E._rows[1]._cell_bg==bg)
        ''')

    def test_switch_preserves_primitives_and_gauge(self):
        lua = mounted()
        lua.execute(r'''
            local p=kyohud.hud.player._root
            local x,y,w,h=p:x(),p:y(),p:w(),p:h()
            local c1,c2=W._cards[1],W._cards[2]
            inventory:_native_set_equipped(1);W:refresh(managers.hud)
            RT:update(managers.hud,1.1,.06)
            assert(W:verify() and E:verify())
            assert(W._cards[1]==c1 and W._cards[2]==c2)
            assert(c2._root:x()<c1._root:x())
            assert(p:x()==x and p:y()==y and p:w()==w and p:h()==h)
            assert(E._root:x()>W._root:x())
        ''')

    def test_unchanged_updates_do_not_remeasure_numeric_budgets(self):
        lua=mounted()
        lua.execute(r'''
            local clip=W._cards[2]._clip_text
            local value=E._rows[1]._value
            local a,b=clip.set_text,value.set_text
            local calls=0
            clip.set_text=function(self,...) calls=calls+1;return a(self,...) end
            value.set_text=function(self,...) calls=calls+1;return b(self,...) end
            for i=1,10 do RT:update(managers.hud,1+i*.06,.06) end
            assert(W:verify() and E:verify())
            assert(calls==0,'RED: native numeric measurement only when its inputs change')
        ''')

    def test_toggle_independence_and_second_deployable(self):
        lua = mounted()
        lua.execute(r'''
            managers.player:_native_set_equipment('trip_mine',{3,2})
            E:refresh(managers.hud);RT:update(managers.hud,1.1,.06)
            assert(E._rows[2]._root:visible())
            assert(E._rows[2]._value:text()=='3|2')
            assert(E._rows[2]._root:x()>E._rows[1]._root:x())
            kyohud.settings.enable_weapons=false;RT:refresh_settings(managers.hud)
            assert(not W._root and E:verify())
            kyohud.settings.enable_weapons=true
            kyohud.settings.enable_equipment=false;RT:refresh_settings(managers.hud)
            assert(not E._root and W:verify())
        ''')

    def test_compact_scale_matrix(self):
        for width,height in ((1920,1080),(1680,1050),(1280,720)):
            for scale in (.95,1,1.05):
                with self.subTest(width=width,height=height,scale=scale):
                    lua=mounted()
                    lua.globals().pw=width;lua.globals().ph=height
                    lua.globals().requested_scale=scale
                    lua.execute(r'''
                        RT._parent_panel:set_shape(0,0,pw,ph)
                        kyohud.settings.hud_scale=requested_scale
                        RT:refresh_settings(managers.hud)
                        RT:update(managers.hud,2,.06)
                        local e=math.min(pw/1920,ph/1080)*requested_scale
                        assert(W:verify() and E:verify())
                        assert(math.abs(W._root:w()-380*e)<.05)
                        assert(math.abs(W._root:h()-102*e)<.05)
                        assert(E._root:x()>W._root:x())
                        assert(E._root:x()+E._root:w()<=W._root:x()+W._root:w()+.05)
                    ''')

if __name__=='__main__':
    unittest.main()
