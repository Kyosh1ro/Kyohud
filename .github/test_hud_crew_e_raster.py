"""Physical-pixel containment for the E nested human gauges."""
import unittest

from test_hud_crew_e_equipment_icons import _lua, ICON_FIXTURE
from test_hud_crew import _lua as crew_lua

WORLD = '''
local P = getmetatable(_G.panel_double).__index
function P:world_x() local p,n=self,0; while p do n=n+p:x(); p=p:parent() end; return n end
function P:world_y() local p,n=self,0; while p do n=n+p:y(); p=p:parent() end; return n end
'''


class CrewRasterTests(unittest.TestCase):
    def test_nested_gauges_snap_equal_physical_insets_and_repair(self):
        lua, exists = _lua(setup=ICON_FIXTURE + WORLD)
        self.assertTrue(exists)
        lua.execute('''
            parent = _G.panel_double:panel({name='raster_parent', x=3.3,y=7.7,w=500,h=200})
            card = kyohud.hud.crew_card.new(parent,'raster_card')
            actor = {name='Alpha',ai=false,level=5,rank=0,downs=3,
                health={ratio=.45,valid=true},armor={ratio=.95,valid=true},
                weapon={ammo={current_clip=24,reserve=114}}}
        ''')
        for e in (.95, 1, 1.05):
            for scale in (1.25, 1.6, 2):
                with self.subTest(e=e, scale=scale):
                    lua.globals().e, lua.globals().s = e, scale
                    lua.execute('''
                        raster={scale=s,x=4.75,y=3.25}
                        card:set_geometry(.3,.7,432*e,120*e,raster)
                        raster.scale=100 -- caller mutation must not leak
                        assert(card:update(actor,0))
                        outer_top=3.25+(card.root:world_y()+card._ar_bg:y())*s
                        top=(card._hp_bg:y()-card._ar_bg:y())*s
                        bottom=(card._ar_bg:y()+card._ar_bg:h()-card._hp_bg:y()-card._hp_bg:h())*s
                        left=(card._hp_bg:x()-card._ar_bg:x())*s
                        right=(card._ar_bg:x()+card._ar_bg:w()-card._hp_bg:x()-card._hp_bg:w())*s
                        inner_h=card._hp_bg:h()*s
                        clean=card:verify()
                        ar=card._armor_fill:w()/card._ar_bg:w()
                        hp=card._health_fill:w()/card._hp_bg:w()
                    ''')
                    g = lua.globals()
                    self.assertAlmostEqual(g.outer_top, round(g.outer_top), places=7)
                    inset = max(1, int(2 * e * scale + .5))
                    for margin in (g.top, g.bottom, g.left, g.right):
                        self.assertAlmostEqual(margin, inset, places=7)
                    self.assertAlmostEqual(g.inner_h, max(1, int(14 * e * scale + .5)), places=7)
                    self.assertAlmostEqual(g.ar, .95)
                    self.assertAlmostEqual(g.hp, .45)
                    self.assertTrue(g.clean)
                    lua.execute('''
                        saved=card._health_fill
                        local p=card._health_fill
                        p:set_shape(p:x(),p:y()+2,p:w(),p:h())
                        assert(not card:verify())
                        assert(card:update(actor,1) and card:verify())
                        assert(saved==card._health_fill)
                    ''')
        lua.execute('''
            for _,r in ipairs({false,{scale=0,x=0,y=0},{scale=0/0,x=0,y=0}}) do
                card:set_geometry(.3,.7,432,120,r)
                assert(card:update(actor,0) and card:verify())
                assert(math.abs(card._ar_bg:h()-18)<1e-8)
                assert(math.abs(card._hp_bg:h()-14)<1e-8)
                assert(math.abs(card._hp_bg:y()-card._ar_bg:y()-2)<1e-8)
            end
        ''')

    def test_real_owner_validates_native_workspace_and_recovers(self):
        lua, exists = crew_lua(setup=WORLD)
        self.assertTrue(exists)
        lua.execute('''
            _G.panel_double:set_shape(0,0,1198,674)
            gui=_G.panel_double:panel({name='native_gui',x=.3,y=.7,w=1198,h=674})
            managers.hud._safe_script={panel=gui}
            ws={key=function() return 'raster' end,panel=function() return _G.panel_double end}
            function managers.hud:workspace(name) assert(name=='saferect'); return ws end
            data={w=1198,h=674,x=4.75,y=3.25,on_screen_width=1920}
            config={workspace_object='screen'}
            managers.gui_data={_ws_size_data={raster=data},_workspace_configuration={raster=config}}
            kyohud.settings.enable_hud_foundation=true
            kyohud.settings.enable_crew=true
            local rt=kyohud.hud.runtime
            rt:refresh_settings(managers.hud)
            crew=kyohud.hud.crew
            crew:refresh_settings(managers.hud)
            mapping=crew._pixel_mapping
        ''')
        mapping = lua.globals().mapping
        self.assertIsNotNone(mapping)
        self.assertAlmostEqual(mapping.scale, 1920 / 1198)
        self.assertEqual(mapping.x, 4.75)
        self.assertEqual(mapping.y, 3.25)
        lua.execute('''
            local panel_fn=ws.panel
            local function check_invalid(change,restore)
                change(); crew:refresh_settings(managers.hud)
                assert(crew._pixel_mapping==nil)
                restore(); crew:refresh_settings(managers.hud)
                assert(crew._pixel_mapping and crew._pixel_mapping.scale==1920/1198)
            end
            check_invalid(function() data.w=0 end,function() data.w=1198 end)
            check_invalid(function() data.h=0/0 end,function() data.h=674 end)
            check_invalid(function() config.workspace_object='linked' end,function() config.workspace_object='screen' end)
            check_invalid(function() ws.panel=function() error('unavailable') end end,function() ws.panel=panel_fn end)
            check_invalid(function() managers.hud._safe_script={panel=_G.panel_double} end,
                function() managers.hud._safe_script={panel=gui} end)
            local foreign_gui=_G.panel_double:panel({name='foreign_gui',w=1198,h=674})
            check_invalid(function() managers.hud._safe_script={panel=foreign_gui} end,
                function() managers.hud._safe_script={panel=gui} end)
        ''')


if __name__ == '__main__':
    unittest.main()
