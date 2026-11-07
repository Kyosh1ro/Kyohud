"""Player legibility refinements exercise real Lua and existing Diesel fixtures."""
import unittest

from test_hud_gauge import _lua
from test_hud_player import _lua as player_lua


class PlayerLegibilityTests(unittest.TestCase):
    def test_health_separators_share_thick_integer_geometry(self):
        for scale in (.65, .95, 1, 1.05):
            with self.subTest(scale=scale):
                lua, ok = _lua()
                self.assertTrue(ok)
                lua.globals().scale = scale
                lua.execute('''
                    local g=kyohud.hud.gauge.new(panel_double,"separators")
                    g:set_geometry(.37,.21,440*scale,42*scale)
                    local hp={current=100,total=100,ratio=1,valid=true}
                    g:render(hp,hp,"real",10)
                    assert(g:verify())
                    for i=1,3 do
                        local m=g.markers[i]
                        assert(m:w()==math.ceil(3*scale),"uniform thick separator")
                        assert(m:x()==math.floor(m:x()),"common raster phase")
                        assert(m:layer()>g.health_segments[i].fill:layer(),"overlay above fills")
                        local c=m:color()
                        assert(c.r==0 and c.g==0 and c.b==0 and m:alpha()==1)
                    end
                ''')

    def test_vanilla_reference_palette_on_bars_and_numbers(self):
        # Native radial interior sampled from the user's reference screenshot:
        # modal HP RGB (159,208,94), armor white (255,255,255).
        # This tests the chosen flat-color reference, not a copied radial shader.
        lua, ok = _lua()
        self.assertTrue(ok)
        lua.execute('''
            gauge=kyohud.hud.gauge.new(panel_double,"vanilla_palette")
            gauge:set_geometry(0,0,440,42)
            hp={current=82,total=100,ratio=.82,valid=true,provenance="local"}
            ar={current=65,total=100,ratio=.65,valid=true,provenance="local"}
            gauge:render(hp,ar,"real",10)
            assert(gauge:verify())
        ''')
        for primitive, rgb in (("health_text",(159,208,94)),("armor_text",(255,255,255)),("armor_fill",(255,255,255))):
            for channel, value in zip(('r','g','b'),rgb):
                self.assertAlmostEqual(lua.eval(f'gauge.{primitive}:color().{channel}'),value/255)
        for index in range(1,5):
            for channel, value in zip(('r','g','b'),(159,208,94)):
                self.assertAlmostEqual(lua.eval(f'gauge.health_segments[{index}].fill:color().{channel}'),value/255)
        lua.execute('''
            old=gauge.health_segments[1].fill
            old:set_color(Color(0,1,1))
            assert(not gauge:verify())
            gauge:render(hp,ar,"real",10)
            assert(gauge:verify() and gauge.health_segments[1].fill==old)
        ''')

    def test_thick_armor_black_empty_outline_and_equal_numeric_sizes(self):
        lua, ok = _lua()
        self.assertTrue(ok)
        lua.execute('''
            gauge=kyohud.hud.gauge.new(panel_double,"legibility")
            gauge:set_geometry(0,0,440,42)
            hp={current=82,total=100,ratio=.82,valid=true,provenance="local"}
            ar={current=0,total=100,ratio=0,valid=true,provenance="local"}
            gauge:render(hp,ar,"real",10)
        ''')
        self.assertEqual(lua.eval('gauge.armor_fill:h()'), 26)
        self.assertEqual(lua.eval('gauge.health_fill:h()'), 14)
        self.assertEqual(lua.eval('gauge.health_fill:y()-gauge.armor_fill:y()'), 6)
        self.assertEqual(lua.eval('gauge.health_fill:x()-gauge.armor_fill:x()'), 6)
        self.assertEqual(lua.eval('gauge._armor_bg:w()-gauge.health_fill:w()'), 12)
        self.assertEqual(lua.eval('gauge._armor_bg:h()-gauge.health_fill:h()'), 12)
        self.assertEqual(lua.eval('gauge.armor_fill:w()'), 0)
        self.assertEqual(lua.eval('gauge._armor_bg:alpha()'), 1)
        self.assertEqual(lua.eval('gauge._armor_bg:color().r'), 0)
        self.assertEqual(lua.eval('gauge._armor_bg:color().g'), 0)
        self.assertEqual(lua.eval('gauge._armor_bg:color().b'), 0)
        self.assertEqual(lua.eval('gauge.armor_text:font_size()'), 24)
        self.assertEqual(lua.eval('gauge.health_text:font_size()'), 24)
        self.assertEqual(lua.eval('gauge.health_text:y() + gauge.health_text:h()/2'), lua.eval('gauge.armor_text:y() + gauge.armor_text:h()/2'))
        for channel in ('r','g','b'):
            self.assertAlmostEqual(lua.eval(f'gauge.health_text:color().{channel}'), lua.eval(f'gauge.health_segments[1].fill:color().{channel}'))
        self.assertTrue(lua.eval('gauge:verify()'))
        lua.execute('ar.ratio=.65; gauge:render(hp,ar,"real",10)')
        for channel, expected in (('r',1),('g',1),('b',1)):
            self.assertAlmostEqual(lua.eval(f'gauge.armor_fill:color().{channel}'), expected)
        self.assertTrue(lua.eval('gauge:verify()'))

    def test_labels_removed_and_downs_number_only_in_both_languages(self):
        for label in ('DOWNS','CHUTES'):
            for scale in (.95,1,1.05):
                with self.subTest(label=label,scale=scale):
                    lua, ok = player_lua()
                    self.assertTrue(ok)
                    lua.globals().downs_label=label
                    lua.globals().desired_scale=scale
                    lua.execute('''
                        managers.localization={text=function(self,key)
                            if key=="ky_hud_player_downs" then return downs_label end
                            return key
                        end}
                        kyohud.settings.enable_hud_foundation=true
                        kyohud.settings.enable_player=true
                        kyohud.settings.hud_scale=desired_scale
                        managers.hud._safe_script={panel=panel_double}
                        kyohud.hud.runtime:refresh_settings(managers.hud)
                        P=kyohud.hud.player
                        P:refresh_settings(managers.hud)
                        root=P._root
                    ''')
                    self.assertIsNone(lua.eval('P._health_label'))
                    self.assertIsNone(lua.eval('P._armor_label'))
                    lua.execute('''
                        assert(not P._downs_label:visible(),"localized label retained but not drawn")
                        assert(P._downs_text:font_size()==P._gauge.health_text:font_size())
                        assert(P._downs_label:text()==downs_label)
                        assert(P:verify())
                        local x,y=root:x(),root:y()
                        P:render({downs=0},10)
                        assert(P._downs_text:text()=="0")
                        P:render({},10)
                        assert(P._downs_text:text()=="--")
                        assert(root:x()==x and root:y()==y)
                    ''')

    def test_border_corruption_recovers_without_recreation(self):
        lua, ok = _lua()
        self.assertTrue(ok)
        lua.execute('''
            gauge=kyohud.hud.gauge.new(panel_double,"outline")
            gauge:set_geometry(0,0,440,42)
            hp={current=50,total=100,ratio=.5,valid=true,provenance="local"}
            zero={current=0,total=100,ratio=0,valid=true,provenance="local"}
            gauge:render(hp,zero,"real",10)
            outline=gauge._armor_bg
            assert(gauge:verify())
            outline:set_color(Color(1,1,1))
            assert(not gauge:verify())
            gauge:render(hp,zero,"real",10)
            assert(gauge:verify() and gauge._armor_bg==outline)
        ''')


if __name__ == '__main__':
    unittest.main()
