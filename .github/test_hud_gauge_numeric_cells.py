"""Gauge numeric cells -- HP/armor value text backgrounds and frames (RED).

NEW required contract (not yet implemented in gauge.lua):
  _health_value_bg / _armor_value_bg: rect layer 4, RGB(.03,.035,.043) a=.86,
    x=text.x-4e y=0 w=text.w+8e h=32e
  _health_value_frame[1..4] / _armor_value_frame[1..4]: rect layer 5,
    RGB(.35,.38,.42) thickness 1e, order top/right/bottom/left.
  Both texts font 24e y=4e h=24e (center 16e) layer 6.
  Thickbar 26 / inset 6 / inner 14 unchanged.
"""
import unittest
from test_hud_gauge import _lua


def _L():
    return _lua()


_WS = ((1920, 1080), (1280, 720), (1680, 1050))
_SC = (.95, 1, 1.0041298879984, 1.05)


class NumericCellsTests(unittest.TestCase):

    def test_geometry_matrix_colors_layers_verify(self):
        for w, h in _WS:
            for sc in _SC:
                with self.subTest(ws=(w, h), sc=sc):
                    lua, ok = _L()
                    self.assertTrue(ok, "gauge chunk required")
                    g = lua.globals()
                    g.tw, g.th, g.ts = w, h, sc
                    lua.execute(r'''
                        local e=math.min(tw/1920,th/1080)*ts
                        local g=kyohud.hud.gauge.new(panel_double,"nc")
                        g:set_geometry(0,0,440*e,42*e)
                        local hp={current=82,total=100,ratio=.82,valid=true,provenance="local"}
                        local ar={current=65,total=100,ratio=.65,valid=true,provenance="local"}
                        g:render(hp,ar,"real",10)
                        assert(alive(g._health_value_bg) and alive(g._armor_value_bg),"bg required")
                        for i=1,4 do
                            assert(alive(g._health_value_frame[i]),"hf["..i.."]")
                            assert(alive(g._armor_value_frame[i]),"af["..i.."]")
                        end
                        local gauges={
                            {text=g.health_text,bg=g._health_value_bg,fr=g._health_value_frame,lb="hp"},
                            {text=g.armor_text,bg=g._armor_value_bg,fr=g._armor_value_frame,lb="ar"},
                        }
                        for _,ga in ipairs(gauges) do
                            local t,bg,fr=ga.text,ga.bg,ga.fr
                            assert(math.abs(t:font_size()-24*e)<.01,ga.lb.." text font")
                            assert(math.abs(t:y()-4*e)<.01,ga.lb.." text y")
                            assert(math.abs(t:h()-24*e)<.01,ga.lb.." text h")
                            assert(t:layer()==6,ga.lb.." text layer")
                            local tc=t:color()
                            assert(tc~=nil and tc.r and tc.g and tc.b,ga.lb.." text color")
                            assert(bg:visible()==true,ga.lb.." bg visible")
                            assert(math.abs(bg:x()-(t:x()-4*e))<.01,ga.lb.." bg x")
                            assert(math.abs(bg:y())<.01,ga.lb.." bg y")
                            assert(math.abs(bg:w()-(t:w()+8*e))<.01,ga.lb.." bg w")
                            assert(math.abs(bg:h()-32*e)<.01,ga.lb.." bg h")
                            assert(math.abs((bg:x()+bg:w())-(t:x()+t:w()+4*e))<.01,ga.lb.." bg right")
                            assert(math.abs(bg:y()+bg:h()-32*e)<.01,ga.lb.." bg bottom")
                            assert(bg:layer()==4,ga.lb.." bg layer")
                            local bc=bg:color()
                            assert(math.abs(bc.r-.03)<.001 and math.abs(bc.g-.035)<.001,ga.lb.." bg rg")
                            assert(math.abs(bc.b-.043)<.001,ga.lb.." bg b")
                            assert(math.abs(bg:alpha()-.86)<.001,ga.lb.." bg alpha")
                            local fex={
                                {x=bg:x(),y=bg:y(),w=bg:w(),h=e},
                                {x=bg:x()+bg:w()-e,y=bg:y(),w=e,h=bg:h()},
                                {x=bg:x(),y=bg:y()+bg:h()-e,w=bg:w(),h=e},
                                {x=bg:x(),y=bg:y(),w=e,h=bg:h()},
                            }
                            for i=1,4 do
                                local f=fr[i]
                                local ex=fex[i]
                                assert(f:visible()==true,ga.lb.." f"..i.." visible")
                                assert(math.abs(f:x()-ex.x)<.01,ga.lb.." f"..i.." x")
                                assert(math.abs(f:y()-ex.y)<.01,ga.lb.." f"..i.." y")
                                assert(math.abs(f:w()-ex.w)<.01,ga.lb.." f"..i.." w")
                                assert(math.abs(f:h()-ex.h)<.01,ga.lb.." f"..i.." h")
                                assert(math.abs((f:x()+f:w())-(ex.x+ex.w))<.01,ga.lb.." f"..i.." right")
                                assert(math.abs((f:y()+f:h())-(ex.y+ex.h))<.01,ga.lb.." f"..i.." bottom")
                                assert(f:layer()==5,ga.lb.." f"..i.." layer")
                                local fc=f:color()
                                assert(math.abs(fc.r-.35)<.001 and math.abs(fc.g-.38)<.001,ga.lb.." f"..i.." rg")
                                assert(math.abs(fc.b-.42)<.001,ga.lb.." f"..i.." b")
                            end
                        end
                        assert(math.abs(g.armor_fill:h()-26*e)<.01)
                        assert(math.abs(g.health_fill:y()-g.armor_fill:y()-6*e)<.01)
                        assert(math.abs(g.health_fill:h()-14*e)<.01)
                        assert(g:verify())
                        assert(g.health_text._kind=="text" and g._health_value_bg._kind=="rect")
                        local p=g._health_value_bg
                        p:set_shape(p:x(),p:y(),p:w(),p:h())
                        p:set_alpha(p:alpha())
                        p:set_color(p:color())
                        p:set_layer(p:layer())
                        _=p:layer()
                    ''')

    def test_mode_toggle_zero_unknown_stable_identities(self):
        lua, ok = _L()
        self.assertTrue(ok)
        lua.execute(r'''
            local g=kyohud.hud.gauge.new(panel_double,"mt")
            g:set_geometry(0,0,440,42)
            local hp={current=82,total=100,ratio=.82,valid=true,provenance="local"}
            local ar={current=65,total=100,ratio=.65,valid=true,provenance="local"}
            g:render(hp,ar,"percentage",10)
            _pct_h=g.health_text:text(); _pct_a=g.armor_text:text()
            _bw1=g.armor_fill:w()
            local hbg_r,abg_r=g._health_value_bg,g._armor_value_bg
            local hfr,afr={},{}
            for i=1,4 do hfr[i]=g._health_value_frame[i]; afr[i]=g._armor_value_frame[i] end
            g:render(hp,ar,"real",10)
            _real_h=g.health_text:text(); _real_a=g.armor_text:text()
            _bw2=g.armor_fill:w()
            _same_hbg=(g._health_value_bg==hbg_r); _same_abg=(g._armor_value_bg==abg_r)
            _same_hf=true; _same_af=true
            for i=1,4 do
                if g._health_value_frame[i]~=hfr[i] then _same_hf=false end
                if g._armor_value_frame[i]~=afr[i] then _same_af=false end
            end
            local hz={current=0,total=100,ratio=0,valid=true,provenance="local"}
            local az={current=0,total=100,ratio=0,valid=true,provenance="local"}
            g:render(hz,az,"percentage",10)
            _zero_h=g.health_text:text(); _zero_a=g.armor_text:text()
            local hu={current=0,total=0,ratio=0,valid=false,provenance="local"}
            local au={current=0,total=0,ratio=0,valid=false,provenance="local"}
            g:render(hu,au,"percentage",10)
            _unk_h=g.health_text:text(); _unk_a=g.armor_text:text()
        ''')
        g = lua.globals()
        self.assertEqual(str(g._pct_h), "82%")
        self.assertEqual(str(g._pct_a), "65%")
        self.assertEqual(str(g._real_h), "820")
        self.assertEqual(str(g._real_a), "650")
        self.assertAlmostEqual(float(g._bw1), float(g._bw2), places=3,
            msg="same bar width across modes")
        self.assertTrue(bool(g._same_hbg), "same _health_value_bg")
        self.assertTrue(bool(g._same_abg), "same _armor_value_bg")
        self.assertTrue(bool(g._same_hf), "same _health_value_frame")
        self.assertTrue(bool(g._same_af), "same _armor_value_frame")
        self.assertEqual(str(g._zero_h), "0%")
        self.assertEqual(str(g._zero_a), "0%")
        self.assertEqual(str(g._unk_h), "--")
        self.assertEqual(str(g._unk_a), "--")

    def test_mutation_rejected_repair_retains_objects(self):
        lua, ok = _L()
        self.assertTrue(ok)
        lua.execute(r'''
            local g=kyohud.hud.gauge.new(panel_double,"mu")
            g:set_geometry(0,0,440,42)
            local hp={current=82,total=100,ratio=.82,valid=true,provenance="local"}
            local ar={current=65,total=100,ratio=.65,valid=true,provenance="local"}
            g:render(hp,ar,"real",10)
            assert(g:verify())
            local bgs={g._health_value_bg,g._armor_value_bg}
            local hbg_r,abg_r=bgs[1],bgs[2]
            local frames={}
            for i=1,4 do
                frames[#frames+1]=g._health_value_frame[i]
                frames[#frames+1]=g._armor_value_frame[i]
            end
            for _,bg in ipairs(bgs) do
                assert(g:verify(),"pre-shape bg")
                bg:set_shape(-1,-1,-1,-1)
                assert(not g:verify(),"corrupt bg shape")
                g:render(hp,ar,"real",10)
                assert(g:verify(),"repair bg shape")
                assert(g._health_value_bg==hbg_r and g._armor_value_bg==abg_r,"same bg after shape repair")
            end
            for _,f in ipairs(frames) do
                assert(g:verify(),"pre-shape frame")
                f:set_shape(-1,-1,-1,-1)
                assert(not g:verify(),"corrupt frame shape")
                g:render(hp,ar,"real",10)
                assert(g:verify(),"repair frame shape")
            end
            for _,bg in ipairs(bgs) do
                assert(g:verify(),"pre-alpha bg")
                bg:set_alpha(0)
                assert(not g:verify(),"corrupt bg alpha")
                g:render(hp,ar,"real",10)
                assert(g:verify(),"repair bg alpha")
                assert(g._health_value_bg==hbg_r and g._armor_value_bg==abg_r,"same bg after alpha repair")
            end
            for _,f in ipairs(frames) do
                assert(g:verify(),"pre-alpha frame")
                f:set_alpha(0)
                assert(not g:verify(),"corrupt frame alpha")
                g:render(hp,ar,"real",10)
                assert(g:verify(),"repair frame alpha")
            end
            for _,bg in ipairs(bgs) do
                assert(g:verify(),"pre-color bg")
                bg:set_color(Color(1,1,0,0))
                assert(not g:verify(),"corrupt bg RGB")
                g:render(hp,ar,"real",10)
                assert(g:verify(),"repair bg RGB")
                assert(g._health_value_bg==hbg_r and g._armor_value_bg==abg_r,"same bg after color repair")
            end
            for _,f in ipairs(frames) do
                assert(g:verify(),"pre-color frame")
                f:set_color(Color(1,0,0))
                assert(not g:verify(),"corrupt frame RGB")
                g:render(hp,ar,"real",10)
                assert(g:verify(),"repair frame RGB")
            end
            for _,bg in ipairs(bgs) do
                assert(g:verify(),"pre-layer bg")
                bg:set_layer(99)
                assert(not g:verify(),"corrupt bg layer")
                g:render(hp,ar,"real",10)
                assert(g:verify(),"repair bg layer")
                assert(g._health_value_bg==hbg_r and g._armor_value_bg==abg_r,"same bg after layer repair")
            end
            for _,f in ipairs(frames) do
                assert(g:verify(),"pre-layer frame")
                f:set_layer(99)
                assert(not g:verify(),"corrupt frame layer")
                g:render(hp,ar,"real",10)
                assert(g:verify(),"repair frame layer")
            end
            local af1=g._armor_value_frame[1]
            af1:parent():remove(af1)
            assert(not g:verify(),"dead frame rejected")
        ''')

    def test_destroy_owned_sibling_stays(self):
        lua, ok = _L()
        self.assertTrue(ok)
        lua.execute(r'''
            local sib=panel_double:panel({name="sibling"})
            local g=kyohud.hud.gauge.new(panel_double,"ds")
            g:set_geometry(0,0,440,42)
            local hp={current=82,total=100,ratio=.82,valid=true,provenance="local"}
            local ar={current=65,total=100,ratio=.65,valid=true,provenance="local"}
            g:render(hp,ar,"real",10)
            local root=g.root
            g:destroy()
            _root_alive=alive(root)
            _sib_alive=alive(sib)
        ''')
        g = lua.globals()
        self.assertFalse(bool(g._root_alive), "own root destroyed")
        self.assertTrue(bool(g._sib_alive), "unrelated sibling stays")

    def test_native_separate_tint_alpha(self):
        """Separate native tint/primitive opacity: effective = color().a * alpha().

        Override Panel metatable to model Diesel: set_color stores {r,g,b,a},
        set_alpha stores self._alpha. If gauge sets color().a=1 and alpha()=.86,
        effective=.86. Current gauge code sets both to .86, producing .7396
        (meaningful RED -- test fails, demonstrating the bug).
        """
        lua, ok = _L()
        self.assertTrue(ok)
        lua.execute(r'''
            -- Override Panel metatable to model separate tint/primitive opacity
            local Panel = getmetatable(panel_double)
            Panel.set_color = function(self, c)
                self._color = {r=c.r, g=c.g, b=c.b, a=c.a}
            end
            Panel.set_alpha = function(self, a)
                self._alpha = a
            end
            Panel.alpha = function(self)
                return self._alpha or 1
            end
            Panel.color = function(self)
                return self._color
            end

            -- Create gauge, geometry 440x42, render valid hp/ar
            local g = kyohud.hud.gauge.new(panel_double, "sep")
            g:set_geometry(0, 0, 440, 42)
            local hp = {current=82, total=100, ratio=.82, valid=true, provenance="local"}
            local ar = {current=65, total=100, ratio=.65, valid=true, provenance="local"}
            g:render(hp, ar, "real", 10)

            -- Check both bgs: effective = color().a * alpha() must = .86
            local hbg = g._health_value_bg
            local abg = g._armor_value_bg
            _hbg_ca = hbg:color().a
            _hbg_pa = hbg:alpha()
            _hbg_eff = _hbg_ca * _hbg_pa
            _abg_ca = abg:color().a
            _abg_pa = abg:alpha()
            _abg_eff = _abg_ca * _abg_pa

            -- Verify positive
            _ok = g:verify()
        ''')
        g = lua.globals()
        # tintalpha=1, primitivealpha=.86
        self.assertAlmostEqual(float(g._hbg_ca), 1.0, places=3, msg="health bg tint alpha")
        self.assertAlmostEqual(float(g._hbg_pa), 0.86, places=3, msg="health bg primitive alpha")
        self.assertAlmostEqual(float(g._hbg_eff), 0.86, places=3, msg="health bg effective alpha")
        self.assertAlmostEqual(float(g._abg_ca), 1.0, places=3, msg="armor bg tint alpha")
        self.assertAlmostEqual(float(g._abg_pa), 0.86, places=3, msg="armor bg primitive alpha")
        self.assertAlmostEqual(float(g._abg_eff), 0.86, places=3, msg="armor bg effective alpha")
        self.assertTrue(bool(g._ok), "verify positive")

    def test_numeric_text_centered_in_framed_cells(self):
        lua, ok = _L()
        self.assertTrue(ok, "gauge chunk required")
        lua.globals().tw, lua.globals().th, lua.globals().ts = 1920, 1080, 1.0
        lua.execute(r'''
            local e = math.min(tw/1920, th/1080) * ts
            local g = kyohud.hud.gauge.new(panel_double, "ctr")
            g:set_geometry(0, 0, 440*e, 42*e)
            local hp = {current=82, total=100, ratio=.82, valid=true, provenance="local"}
            local ar = {current=65, total=100, ratio=.65, valid=true, provenance="local"}
            local hbg0, abg0 = g._health_value_bg, g._armor_value_bg
            g:render(hp, ar, "percentage", 10)
            _pct_h, _pct_a = g.health_text:text(), g.armor_text:text()
            _ha_p, _aa_p = g.health_text._align, g.armor_text._align
            _htx_p, _htw_p = g.health_text:x(), g.health_text:w()
            _atx_p, _atw_p = g.armor_text:x(), g.armor_text:w()
            _hbx_p, _hbw_p = g._health_value_bg:x(), g._health_value_bg:w()
            _abx_p, _abw_p = g._armor_value_bg:x(), g._armor_value_bg:w()
            _hty_p, _hth_p = g.health_text:y(), g.health_text:h()
            _aty_p, _ath_p = g.armor_text:y(), g.armor_text:h()
            _hby_p, _hbh_p = g._health_value_bg:y(), g._health_value_bg:h()
            _aby_p, _abh_p = g._armor_value_bg:y(), g._armor_value_bg:h()
            g:render(hp, ar, "real", 10)
            _real_h, _real_a = g.health_text:text(), g.armor_text:text()
            _ha_r, _aa_r = g.health_text._align, g.armor_text._align
            _htx_r, _htw_r = g.health_text:x(), g.health_text:w()
            _atx_r, _atw_r = g.armor_text:x(), g.armor_text:w()
            _hbx_r, _hbw_r = g._health_value_bg:x(), g._health_value_bg:w()
            _abx_r, _abw_r = g._armor_value_bg:x(), g._armor_value_bg:w()
            _same_hbg, _same_abg = (g._health_value_bg == hbg0), (g._armor_value_bg == abg0)
            local hz = {current=0, total=100, ratio=0, valid=true, provenance="local"}
            local az = {current=0, total=100, ratio=0, valid=true, provenance="local"}
            g:render(hz, az, "percentage", 10)
            _zero_h, _zero_a = g.health_text:text(), g.armor_text:text()
            local hu = {current=0, total=0, ratio=0, valid=false, provenance="local"}
            g:render(hu, hu, "percentage", 10)
            _unk_h, _unk_a = g.health_text:text(), g.armor_text:text()
        ''')
        g = lua.globals()
        self.assertEqual(str(g._pct_h), "82%"); self.assertEqual(str(g._pct_a), "65%")
        self.assertEqual(str(g._real_h), "820"); self.assertEqual(str(g._real_a), "650")
        self.assertEqual(str(g._zero_h), "0%"); self.assertEqual(str(g._zero_a), "0%")
        self.assertEqual(str(g._unk_h), "--"); self.assertEqual(str(g._unk_a), "--")
        for lb, v in (("health_pct", g._ha_p), ("armor_pct", g._aa_p),
                      ("health_real", g._ha_r), ("armor_real", g._aa_r)):
            self.assertEqual(str(v), "center", f"{lb}._align must be 'center'")
        for lb, tx, tw_, bx, bw in (
            ("hp_pct", g._htx_p, g._htw_p, g._hbx_p, g._hbw_p),
            ("ar_pct", g._atx_p, g._atw_p, g._abx_p, g._abw_p),
            ("hp_real", g._htx_r, g._htw_r, g._hbx_r, g._hbw_r),
            ("ar_real", g._atx_r, g._atw_r, g._abx_r, g._abw_r),
        ):
            self.assertAlmostEqual(float(tx)+float(tw_)/2, float(bx)+float(bw)/2,
                places=2, msg=f"{lb} horiz center")
        for lb, ty, th_, by, bh in (
            ("hp_pct", g._hty_p, g._hth_p, g._hby_p, g._hbh_p),
            ("ar_pct", g._aty_p, g._ath_p, g._aby_p, g._abh_p),
        ):
            self.assertAlmostEqual(float(ty)+float(th_)/2, float(by)+float(bh)/2,
                places=2, msg=f"{lb} vert center")
        self.assertTrue(bool(g._same_hbg), "health_value_bg identity preserved")
        self.assertTrue(bool(g._same_abg), "armor_value_bg identity preserved")
        self.assertAlmostEqual(float(g._hbw_p), float(g._hbw_r), places=3, msg="health bg w stable")
        self.assertAlmostEqual(float(g._abw_p), float(g._abw_r), places=3, msg="armor bg w stable")


if __name__ == "__main__":
    unittest.main()
