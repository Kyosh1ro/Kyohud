"""Fixed crew anchor and one-way buff yielding through the real row producer."""
import unittest
from test_hud_crew_acceptance import mounted
from test_hud_crew import ROOT


class CrewOnlinePlacementTests(unittest.TestCase):
    def test_real_buff_row_yields_without_moving_or_recreating_crew(self):
        for width, height in ((1920, 1080), (1600, 900)):
            for scale in (.95, 1, 1.05):
                with self.subTest(width=width, height=height, scale=scale):
                    self._exercise_layout(width, height, scale)

    def _exercise_layout(self, width, height, scale):
        lua = mounted()
        lua.execute(f'''
            panel_double:set_shape(0,0,{width},{height})
            kyohud.settings.hud_scale={scale}
            RT:update(managers.hud,1.6,.05)
            assert(C:_verify_render(),'matrix precondition')
        ''')
        lua.execute('''
            dofile=function() end
            TimerManager={game=function() return {time=function() return 1 end} end}
            local make=Color
            Color=setmetatable({white=make(1,1,1),black=make(0,0,0)},
                {__call=function(_,...) return make(...) end})
        ''')
        lua.execute((ROOT / 'lua/ky_buff_presentation.lua').read_text(encoding='utf-8'))
        lua.execute((ROOT / 'lua/core.lua').read_text(encoding='utf-8'))
        lua.execute("RequiredScript='lib/managers/hudmanagerpd2'")
        lua.execute((ROOT / 'lua/ky_buff_render.lua').read_text(encoding='utf-8'))
        lua.execute((ROOT / 'lua/ky_killfeed_render.lua').read_text(encoding='utf-8'))
        lua.execute(r'''
            local parent = C._parent_panel
            local buff = parent:panel({name='kyohud_buff_panel'})
            buff:set_shape(0,0,parent:w(),parent:h())
            kyohud._panel = buff
            kyohud.settings.enable_buffs=true
            kyohud.settings.buff_position_x=30
            kyohud.settings.buff_position_y=98
            kyohud.settings.enable_killfeed=false
            kyohud.settings.enable_kill_score=false
            kyohud.settings.enable_kill_medals=false
            kyohud._gameinfo_bridge_active=true
            kyohud._buffs.test={id='test',icon='texture',color=Color.white}
            kyohud.is_buff_visible=function(_,id) return id=='test' end
            kyohud.DrawBuffCellFrame=function(panel,x,y,w,h)
                _buff_y=y+h/2
                local r=panel:rect({name='buff_frame'})
                r:set_shape(x,y,w,h)
            end
            local root,card=C._root,C._cards[1].root
            local nominal=C._layout_cache.y-C._layout_cache.state_h
            local default=kyohud.compute_buff_row_layout(1,30,98,parent:w(),parent:h(),32,5.12,2.56,18)
            _default_y=default.positions[1].y
            kyohud:draw()
            RT:update(managers.hud,2,.05)
            _fixed=math.abs(C._root:y()-nominal)<.01
            _visible=C:_verify_render()
            _yielded=_buff_y<_default_y
            _same=C._root==root and C._cards[1].root==card
            for i=1,4 do
                kyohud:draw()
                RT:update(managers.hud,2+i*.6,.05)
                assert(math.abs(C._root:y()-nominal)<.01,'crew must not oscillate')
                assert(C:_verify_render(),'crew must remain certified')
            end
            kyohud.settings.buff_position_x=95
            kyohud:draw()
            _restored=math.abs(_buff_y-_default_y)<.01
        ''')
        for name in ('_fixed','_visible','_yielded','_same','_restored'):
            self.assertIs(lua.globals()[name], True, name)
