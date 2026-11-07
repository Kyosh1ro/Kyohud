"""Player E presentation -- gauge row contract (RED tracer).

Current legibility contract: equal-size numbers, nominal budgets 40/40;
  26-high outer armor, thick6 frame, 14-high inner health and 3 gaps of 2.
  Segment widths remain proportional 30/20/25/25 of usable ink span.
"""
from pathlib import Path
import unittest

from test_hud_gauge import _lua

ROOT = Path(__file__).resolve().parents[1]


def _row_contracts():
    """Derive all gauge dimensions from explicit row contracts."""
    row_total = 440
    padding = 28
    health_num_w = 40
    armor_num_w = 40
    outer_gaps = 24
    bar_w = row_total - padding - health_num_w - armor_num_w - outer_gaps
    inset_each_side = 6
    health_span = bar_w - 2 * inset_each_side
    seg_gap = 2
    n_gaps = 3
    usable = health_span - n_gaps * seg_gap
    ratios = (0.30, 0.20, 0.25, 0.25)
    bg = tuple(r * usable for r in ratios)
    return bar_w, health_span, usable, bg


BAR_W, HEALTH_SPAN, USABLE, SEG_BG = _row_contracts()


class PlayerEPresentationTests(unittest.TestCase):
    def test_new_render_failure_hides_in_the_same_update(self):
        from test_hud_player import _lua as player_lua
        lua, ok = player_lua()
        self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation=true
            kyohud.settings.enable_player=true
            managers.hud._safe_script={panel=panel_double}
            kyohud.hud.runtime:refresh_settings(managers.hud)
            P=kyohud.hud.player
            P:refresh_settings(managers.hud)
            local number=P._gauge.health_text
            local measure=number.text_rect
            attempts=0
            number.text_rect=function(self)
                attempts=attempts+1
                if attempts>1 then error("measurement fails after pre-update certification") end
                return measure(self)
            end
            P:update(managers.hud,1,.1)
        ''')
        self.assertGreater(lua.eval('attempts'), 1)
        self.assertFalse(lua.eval('P._root:visible()'), 'a failed new render must not remain visible for another update')

    def test_nonfinite_font_and_invalid_data_fail_closed(self):
        lua, ok = _lua()
        self.assertTrue(ok)
        lua.execute('''
            inst=kyohud.hud.gauge.new(panel_double,"invalid")
            inst:set_geometry(0,0,440,42)
            hp={current=50,total=100,ratio=.5,valid=true,provenance="local"}
            inst:render(hp,hp,"real",10)
            inst.health_text:set_font_size(0/0)
        ''')
        self.assertFalse(lua.eval('inst:verify()'), 'NaN font_size must not pass numeric readback')
        lua.execute('''
            for _,bad in ipairs({0/0,math.huge,-math.huge}) do
                inst:render(hp,hp,"real",bad)
                assert(inst.health_text:text()=="--")
                inst:render({valid=true,ratio=bad,current=bad},nil,"percentage",10)
                assert(inst.health_text:text()=="--" and inst.armor_text:text()=="--")
                for _,s in ipairs(inst.health_segments) do assert(s.fill:w()==0) end
            end
            inst:render(hp,hp,"real",10)
            inst.root:set_alpha(0)
            assert(not inst:verify())
            inst:render(hp,hp,"real",10)
            assert(inst:verify())
        ''')

    def test_missing_measurement_recovery_and_dead_segment(self):
        from test_hud_player import _lua as player_lua
        lua, ok = player_lua()
        self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation=true
            kyohud.settings.enable_player=true
            managers.hud._safe_script={panel=panel_double}
            kyohud.hud.runtime:refresh_settings(managers.hud)
            P=kyohud.hud.player
            P:refresh_settings(managers.hud)
            root=P._root; gauge=P._gauge
            number=gauge.health_text; measure=number.text_rect
            number.text_rect=false
            P:update(managers.hud,1,.1)
            assert(P._root==root and not root:visible())
            number.text_rect=measure
            P:update(managers.hud,2,.1)
            assert(P:verify() and P._root==root)
            dead=gauge.health_segments[1].fill
            dead:parent():remove(dead)
            P:update(managers.hud,3,.1)
            assert(P:verify())
            assert(P._root~=root and P._gauge.health_segments[1].fill~=dead)
            P._downs_label=nil
            P:update(managers.hud,4,.1)
            assert(P:verify(), "incomplete owned text construction must recover")
        ''')

    def test_workspace_scale_matrix_thresholds_and_numeric_fitting(self):
        from test_hud_player import _lua as player_lua
        for width, height in ((1920,1080),(1280,720),(1680,1050)):
            for scale in (.95,1,1.05):
                with self.subTest(workspace=(width,height), scale=scale):
                    lua, ok = player_lua()
                    self.assertTrue(ok)
                    g = lua.globals()
                    g.test_w, g.test_h, g.test_scale = width, height, scale
                    lua.execute('''
                        panel_double:set_shape(0,0,test_w,test_h)
                        kyohud.settings.enable_hud_foundation=true
                        kyohud.settings.enable_player=true
                        kyohud.settings.hud_scale=test_scale
                        managers.hud._safe_script={panel=panel_double}
                        kyohud.hud.runtime:refresh_settings(managers.hud)
                        P=kyohud.hud.player
                        P:refresh_settings(managers.hud)
                        root=P._root
                        gauge=P._gauge
                        local e=math.min(test_w/1920,test_h/1080)*test_scale
                        assert(math.abs(root:w()-380*e)<.001)
                        assert(math.abs(gauge.root:w()-300*e)<.001)
                        assert(math.abs(root:x()+gauge.root:x()-(test_w-test_w*.02-300*e))<.001)
                        assert(math.abs(root:h()-120*e)<.001)
                        local function metric(r) return {current=r*100,total=100,ratio=r,valid=true,provenance="local"} end
                        for _, r in ipairs({0,.29,.30,.31,.49,.5,.51,.74,.75,.76,1,2}) do
                            P:render({health=metric(r),armor=metric(1-r),downs=3,condition_icon="mugshot_normal"},10)
                            assert(P:verify())
                            local filled,usable=0,0
                            for _,s in ipairs(gauge.health_segments) do
                                filled=filled+s.fill:w(); usable=usable+s.background:w()
                            end
                            assert(math.abs(filled/usable-math.min(r,1))<.00001)
                            assert(math.abs(gauge.armor_fill:w()/gauge._armor_bg:w()-math.max(0,1-r))<.00001)
                        end
                        for _,mode in ipairs({1,2}) do
                            kyohud.settings.player_value_mode=mode
                            P:render({health=metric(.82),armor=metric(.45),downs=0},10)
                            assert(P:verify())
                            assert(P._downs_text:text()=="0")
                            if mode==1 then bar_pct=gauge._armor_bg:w() else assert(math.abs(gauge._armor_bg:w()-bar_pct)<.001) end
                        end
                        local huge={current=12345,total=20000,ratio=.61725,valid=true,provenance="local"}
                        P:render({health=huge,armor=huge},10)
                        assert(P:verify())
                        assert(gauge.health_text:text()=="123450")
                        assert(P._downs_text:text()=="--")
                        local oldx,oldy=root:x(),root:y()
                        panel_double:set_shape(0,0,1920,1080)
                        kyohud.hud.runtime:refresh_settings(managers.hud)
                        panel_double:set_shape(0,0,test_w,test_h)
                        kyohud.hud.runtime:refresh_settings(managers.hud)
                        assert(P._root==root and P._gauge==gauge)
                        assert(math.abs(root:x()-oldx)<.001 and math.abs(root:y()-oldy)<.001)
                    ''')

    def test_setter_noop_hides_and_recovers_retained_primitives(self):
        from test_hud_player import _lua as player_lua
        lua, ok = player_lua()
        self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation=true
            kyohud.settings.enable_player=true
            managers.hud._safe_script={panel=panel_double}
            kyohud.hud.runtime:refresh_settings(managers.hud)
            P=kyohud.hud.player
            P:refresh_settings(managers.hud)
            root=P._root; gauge=P._gauge
            prim=gauge.health_segments[1].fill
            saved=prim.set_shape
            prim:set_shape(0,0,999,999)
            prim.set_shape=function() end
            P:update(managers.hud,1,.1)
        ''')
        self.assertTrue(lua.eval('P._root==root and P._gauge==gauge'), 'recoverable setter failure must not recreate the root')
        self.assertFalse(lua.eval('root:visible()'))
        lua.execute('prim.set_shape=saved; P:update(managers.hud,2,.1)')
        self.assertTrue(lua.eval('P:verify()'))
        self.assertTrue(lua.eval('P._root==root and P._gauge==gauge and gauge.health_segments[1].fill==prim'))

    def test_numeric_modes_preserve_geometry_and_native_style(self):
        lua, ok = _lua()
        self.assertTrue(ok)
        lua.execute('''
            inst=kyohud.hud.gauge.new(panel_double,"mode_geometry")
            inst:set_geometry(0,0,440,42)
            hp={current=82,total=100,ratio=.82,valid=true,provenance="local"}
            ar={current=25,total=100,ratio=.25,valid=true,provenance="local"}
            inst:render(hp,ar,"percentage",10)
            width_pct=inst._armor_bg:w()
            inst:render(hp,ar,"real",10)
            width_real=inst._armor_bg:w()
        ''')
        self.assertEqual(lua.eval('width_pct'), lua.eval('width_real'))
        self.assertAlmostEqual(lua.eval('inst._armor_bg:alpha()'), 1)
        self.assertEqual(lua.eval('inst.health_text._align'), 'center')
        self.assertEqual(lua.eval('inst.armor_text._align'), 'center')
        lua.execute('inst.health_segments[1].fill.color=false')
        self.assertFalse(lua.eval('inst:verify()'), 'missing required color readback must fail closed')

    def test_color_alpha_and_segment_geometry_certification(self):
        lua, ok = _lua()
        self.assertTrue(ok)
        lua.execute('''
            inst = kyohud.hud.gauge.new(panel_double, "cert")
            inst:set_geometry(0,0,440,42)
            hp={current=50,total=100,ratio=.5,valid=true,provenance="local"}
            inst:render(hp,hp,"real",10)
            assert(inst:verify())
            segment = inst.health_segments[1].fill
            segment:set_alpha(.2)
        ''')
        self.assertFalse(lua.eval('inst:verify()'), "alpha drift must invalidate the real verifier")
        lua.execute('inst:render(hp,hp,"real",10)')
        self.assertTrue(lua.eval('inst:verify()'))
        lua.execute('segment:set_color(Color(1,0,0))')
        self.assertFalse(lua.eval('inst:verify()'))
        lua.execute('inst:render(hp,hp,"real",10)')
        self.assertTrue(lua.eval('inst:verify()'))
        lua.execute('segment:set_shape(0,2,1,1)')
        self.assertFalse(lua.eval('inst:verify()'))
        lua.execute('inst:render(hp,hp,"real",10)')
        self.assertTrue(lua.eval('inst:verify()'))
        self.assertTrue(lua.eval('segment == inst.health_segments[1].fill'))

    def test_player_compact_layout_without_font_binding(self):
        from test_hud_player import _lua as player_lua
        lua, ok = player_lua()
        self.assertTrue(ok)
        lua.execute('''
            kyohud.settings.enable_hud_foundation=true
            kyohud.settings.enable_player=true
            managers.hud._safe_script={panel=panel_double}
            kyohud.hud.runtime:refresh_settings(managers.hud)
            P=kyohud.hud.player
            P:refresh_settings(managers.hud)
            assert(P._mounted)
        ''')
        self.assertEqual(lua.eval('P._gauge.root:x()'), 80)
        self.assertEqual(lua.eval('P._gauge.root:w()'), 300)
        self.assertEqual(lua.eval('P._root:w()'), 380)
        lua.execute('''
            P._downs_label.font=function() error("unsafe font binding") end
            P._downs_label:set_font_size(999)
        ''')
        self.assertFalse(lua.eval('P:verify()'), "player must certify font_size without calling font")

    def test_armor_height_and_segmented_health_contract(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/gauge.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local G = kyohud.hud.gauge
            assert(G and G.new, "RED: kyohud.hud.gauge.new must exist")
            local inst = G.new(parent, "pe_gauge")
            inst:set_geometry(0, 0, 440, 42)

            local hp = {current=50, total=100, ratio=0.5, valid=true, provenance="local"}
            local ar = {current=20, total=100, ratio=0.2, valid=true, provenance="local"}
            inst:render(hp, ar, "real", 10)

            _armor_h = inst.armor_fill:h()
            _armor_w = inst.armor_fill:w()

            _hs = inst.health_segments
            _hs_count = 0
            if type(_hs) == "table" then
                for _ in pairs(_hs) do _hs_count = _hs_count + 1 end
            end

            local function seg_bg_w(i)
                if type(_hs) ~= "table" then return -1 end
                local s = _hs[i]
                if not s then return -1 end
                if not s.background then return -1 end
                return s.background:w()
            end
            local function seg_fill_w(i)
                if type(_hs) ~= "table" then return -1 end
                local s = _hs[i]
                if not s then return -1 end
                if not s.fill then return -1 end
                return s.fill:w()
            end

            _bg1 = seg_bg_w(1); _bg2 = seg_bg_w(2); _bg3 = seg_bg_w(3); _bg4 = seg_bg_w(4)
            _f1  = seg_fill_w(1); _f2  = seg_fill_w(2); _f3  = seg_fill_w(3); _f4  = seg_fill_w(4)
        ''')
        g = lua.globals()

        self.assertEqual(float(g._armor_h), 26.0,
            "armor_fill:h() must preserve the thick6 frame")

        self.assertEqual(int(g._hs_count), 4,
            "health_segments must have exactly 4 ordered handles")

        self.assertAlmostEqual(float(g._bg1), SEG_BG[0], places=1,
            msg=f"segment 1 background width: 30% of usable {USABLE}")
        self.assertAlmostEqual(float(g._bg2), SEG_BG[1], places=1,
            msg=f"segment 2 background width: 20% of usable {USABLE}")
        self.assertAlmostEqual(float(g._bg3), SEG_BG[2], places=1,
            msg=f"segment 3 background width: 25% of usable {USABLE}")
        self.assertAlmostEqual(float(g._bg4), SEG_BG[3], places=1,
            msg=f"segment 4 background width: 25% of usable {USABLE}")

        self.assertAlmostEqual(float(g._f1), SEG_BG[0], places=1,
            msg="seg 1 [0,0.30]: ratio=0.5 clamps to full")
        self.assertAlmostEqual(float(g._f2), SEG_BG[1], places=1,
            msg="seg 2 [0.30,0.50]: ratio=0.5 clamps to full")
        self.assertAlmostEqual(float(g._f3), 0.0, places=1,
            msg="seg 3 [0.50,0.75]: ratio=0.5 at start -> 0.0")
        self.assertAlmostEqual(float(g._f4), 0.0, places=1,
            msg="seg 4 [0.75,1.0]: ratio=0.5 below range -> 0.0")

        self.assertAlmostEqual(float(g._armor_w), BAR_W * 0.2, places=1,
            msg=f"armor_fill:w() == bar_w({BAR_W}) * 0.2 with 500/200 strings in 40/40 budgets")


if __name__ == "__main__":
    unittest.main()
