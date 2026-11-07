"""Replay the captured Diesel downs-font height without loosening certification."""
import unittest
from test_hud_local_e_compact import mounted


class NativeDownsMetricsTests(unittest.TestCase):
    def test_native_line_height_does_not_hide_the_player(self):
        for scale in (.95,1.0041298879984,1.05):
            with self.subTest(scale=scale):
                lua=mounted()
                lua.globals().s=scale
                lua.execute(r'''
                    local P=kyohud.hud.player
                    local root,gauge,number,bg=P._root,P._gauge,P._downs_text,P._downs_bg
                    local original=number.text_rect
                    local calls=0
                    number.text_rect=function(self)
                        calls=calls+1
                        local x,y,w=original(self)
                        -- Native trace: font_size=13.144972801208496;
                        -- ink height=13.69268798828125, above its old box+.5.
                        return x,y,w,self:font_size()*(13.69268798828125/13.144972801208496)
                    end
                    RT._parent_panel:set_shape(0,0,1280,720)
                    kyohud.settings.hud_scale=s
                    RT:refresh_settings(managers.hud);RT:update(managers.hud,2,.1)
                    assert(P:verify() and root:visible(),'RED: native downs line height must not hide health')
                    assert(P._root==root and P._gauge==gauge and P._downs_bg==bg)
                    assert(number:font_size()==gauge.health_text:font_size(),'no font-size workaround')
                    assert(math.abs(bg:h()-gauge._armor_bg:h())<.05,'background unchanged')
                    for _,value in ipairs({'--','0','3'}) do
                        local snap={health={valid=false},armor={valid=false}}
                        if value~='--' then snap.downs=tonumber(value) end
                        P:render(snap,10)
                        assert(number:text()==value and P:verify())
                        local _,_,_,ink=number:text_rect()
                        assert(ink<=number:h()+.5)
                        assert(math.abs(number:y()+number:h()/2-(bg:y()+bg:h()/2))<.05)
                    end
                    local x,y,w,h=number:x(),number:y(),number:w(),number:h()
                    number:set_shape(x+5,y,w,h)
                    assert(not P:verify(),'geometry certification retained')
                    RT:update(managers.hud,2.2,.1)
                    assert(P:verify() and P._downs_text==number)
                    local measure=number.text_rect
                    number.text_rect=function() return 0,0,8,999 end
                    assert(not P:verify(),'out-of-bounds ink still refused')
                    number.text_rect=measure
                    RT:update(managers.hud,2.4,.1)
                    assert(P:verify())
                ''')

    def test_impossible_native_measurement_cannot_expand_past_root(self):
        lua=mounted()
        lua.execute(r'''
            local P=kyohud.hud.player
            P._downs_text.text_rect=function() return 0,0,8,999 end
            P:render({downs=7,health={valid=false},armor={valid=false}},10)
            assert(not P:verify())
        ''')

if __name__=='__main__':
    unittest.main()
