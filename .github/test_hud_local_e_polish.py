"""Readable slot labels, explicit equipment spacing and number-only downs badge."""
import unittest
from test_hud_local_e_compact import mounted


class LocalEPolishTests(unittest.TestCase):
    def test_readable_headers_and_explicit_equipment_gaps(self):
        lua=mounted()
        lua.execute(r'''
            local e=W._layout_cache.e
            for i=1,2 do
                local p=W._cards[i]._name_text
                assert(p:font_size()>=16*e-.05,'RED: larger slot labels')
                assert(p:color().r==1 and p:color().g==1 and p:color().b==1 and p:alpha()==1)
            end
            local right=math.max(W._cards[1]._root:x()+W._cards[1]._root:w(),W._cards[2]._root:x()+W._cards[2]._root:w())+W._root:x()
            assert(math.abs(E._root:x()-right-4*e)<.05,'RED: fixed small weapon/equipment gap')
            local last
            for _,i in ipairs({1,2,3,4}) do
                local p=E._rows[i]._root
                if p:visible() then
                    if last then assert(math.abs(p:x()-last-2*e)<.05,'RED: regular equipment gaps') end
                    last=p:x()+p:w()
                    local value=E._rows[i]._value
                    local center=E._rows[i]._cell_both and p:w()/2 or (p:w()-4*e)/2
                    assert(math.abs(value:x()+value:w()/2-center)<.05,'counts centered in cut silhouettes')
                end
            end
            assert(W:verify() and E:verify())
        ''')

    def test_downs_matches_health_typography_and_visible_bar_height(self):
        for width,height in ((1920,1080),(1280,720),(1680,1050)):
            for scale in (.95,1,1.05):
                with self.subTest(width=width,height=height,scale=scale):
                    lua=mounted()
                    lua.globals().pw=width;lua.globals().ph=height;lua.globals().s=scale
                    lua.execute(r'''
                        RT._parent_panel:set_shape(0,0,pw,ph)
                        kyohud.settings.hud_scale=s
                        RT:refresh_settings(managers.hud);RT:update(managers.hud,2,.06)
                        local P=kyohud.hud.player
                        local g=P._gauge
                        assert(not P._downs_label:visible(),'RED: number-only downs badge')
                        assert(math.abs(P._downs_text:font_size()-g.health_text:font_size())<.05,'RED: actual HP typography')
                        assert(math.abs(P._downs_bg:h()-g._armor_bg:h())<.05,'RED: visible frame height, not gauge root height')
                        local cy=P._downs_bg:y()+P._downs_bg:h()/2
                        assert(math.abs(cy-(g.root:y()+g._armor_bg:y()+g._armor_bg:h()/2))<.05)
                        assert(math.abs(cy-(P._downs_text:y()+P._downs_text:h()/2))<.05)
                        assert(P:verify())
                    ''')

    def test_replacement_vertex_strips(self):
        lua=mounted()
        lua.execute(r'''
            local e=W._layout_cache.e
            local cut=RT._local_bg_cut
            assert(cut and cut._kind=='polygon','RED: genuine shared rounded mesh')
            local tri=cut._triangles
            assert(#tri>3 and #tri%3==0,'RED: tri count >3 divisible by 3')
            local full_bgw=RT._local_bg_panel:w()
            local full_bgh=cut:h()
            assert(math.abs(cut:w()-full_bgw)<.05,'RED: cut w = full bgw')
            for i,v in ipairs(tri) do
                assert(v.x==v.x and v.y==v.y,'RED: vertex '..i..' not finite')
                assert(v.x>=-0.05 and v.x<=full_bgw+0.05,'RED: vertex '..i..' x outside bg')
                assert(v.y>=-0.05 and v.y<=full_bgh+0.05,'RED: vertex '..i..' y outside bg')
            end
            for i,v in ipairs(tri) do
                local is_corner=false
                if math.abs(v.x)<0.05 and math.abs(v.y)<0.05 then is_corner=true end
                if math.abs(v.x-full_bgw)<0.05 and math.abs(v.y)<0.05 then is_corner=true end
                if math.abs(v.x)<0.05 and math.abs(v.y-full_bgh)<0.05 then is_corner=true end
                if math.abs(v.x-full_bgw)<0.05 and math.abs(v.y-full_bgh)<0.05 then is_corner=true end
                assert(not is_corner,'RED: corner vertex at '..i)
            end
            for i,v in ipairs(tri) do
                local in_left=v.x<=6*e+0.05
                local in_right=v.x>=full_bgw-6*e-0.05
                assert(in_left or in_right,'RED: vertex '..i..' outside rounded strips')
            end
            local vector=Vector3
            local calls=0
            Vector3=function(...) calls=calls+1;return vector(...) end
            for i=1,6 do
                inventory:_native_set_equipped(i%2+1);W:refresh(managers.hud)
                RT:update(managers.hud,1+i*.1,.1)
                assert(RT._local_bg_cut==cut and RT:_verify_local_backdrop() and E:verify() and W:verify())
            end
            assert(calls==0,'no idle or switch vertex allocation')
            cut:set_alpha(0)
            assert(not RT:_verify_local_backdrop())
            RT:update(managers.hud,2,.1)
            assert(RT:_verify_local_backdrop() and E:verify() and RT._local_bg_cut==cut)
            local x,y,w,h=cut:x(),cut:y(),cut:w(),cut:h()
            cut:set_shape(x+5,y,w,h)
            assert(not RT:_verify_local_backdrop())
            RT:update(managers.hud,2.1,.1)
            assert(RT:_verify_local_backdrop() and E:verify() and RT._local_bg_cut==cut)
            kyohud.settings.hud_scale=1.05
            RT:refresh_settings(managers.hud);RT:update(managers.hud,2.2,.1)
            assert(RT:_verify_local_backdrop() and E:verify() and RT._local_bg_cut~=cut and not alive(cut))
            local fresh_e=W._layout_cache.e
            local replacement=RT._local_bg_cut
            local rw=replacement:w()
            local rh=replacement:h()
            for i,v in ipairs(replacement._triangles) do
                assert(v.x==v.x and v.y==v.y,'RED: replacement vertex '..i..' not finite')
                assert(v.x>=-0.05 and v.x<=rw+0.05 and v.y>=-0.05 and v.y<=rh+0.05,'RED: replacement vertex '..i..' outside bounds')
                local is_outer=false
                if math.abs(v.x)<0.05 and math.abs(v.y)<0.05 then is_outer=true end
                if math.abs(v.x-rw)<0.05 and math.abs(v.y)<0.05 then is_outer=true end
                if math.abs(v.x)<0.05 and math.abs(v.y-rh)<0.05 then is_outer=true end
                if math.abs(v.x-rw)<0.05 and math.abs(v.y-rh)<0.05 then is_outer=true end
                assert(not is_outer,'RED: replacement outer corner at '..i)
            end
            for i,v in ipairs(replacement._triangles) do
                local in_left=v.x<=6*fresh_e+0.05
                local in_right=v.x>=rw-6*fresh_e-0.05
                assert(in_left or in_right,'RED: replacement vertex '..i..' outside rounded strips')
            end
            kyohud.settings.enable_equipment=false;RT:refresh_settings(managers.hud)
            assert(not E._rows and alive(replacement) and not RT:_verify_local_backdrop() and W:verify())
        ''')

    def test_common_bg_alpha_and_tint(self):
        lua=mounted()
        lua.execute(r'''
            local bg=RT._local_bg_body
            assert(bg,'RED: common equipment background exists')
            assert(math.abs(bg:alpha()-.86)<.005,'RED: common bg alpha .86')
            local c=bg:color()
            assert(math.abs(c.r-8/255)<.005 and math.abs(c.g-9/255)<.005 and math.abs(c.b-11/255)<.005,'RED: common bg tint dark')
            assert(RT:_verify_local_backdrop())
            bg:set_alpha(0)
            assert(not RT:_verify_local_backdrop(),'common bg alpha corruption refused')
            RT:update(managers.hud,1.1,.06)
            assert(RT:_verify_local_backdrop() and RT._local_bg_body==bg)
            bg:set_shape(0,0,1,1)
            assert(not RT:_verify_local_backdrop(),'common bg shape corruption refused')
            RT:update(managers.hud,1.2,.06)
            assert(RT:_verify_local_backdrop() and RT._local_bg_body==bg)
        ''')

if __name__=='__main__':
    unittest.main()
