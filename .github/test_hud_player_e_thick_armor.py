"""Player E thick-armor gauge geometry -- pure gauge scaling, not runtime.

Derives es = min(width/1920, height/1080) * scale and verifies that gauge
geometry follows: 26-high outer armor, 6-unit inset, 14-high inner health,
24-pt armor font, 24-pt health font, with centered bbox equality.
"""
import unittest

from test_hud_gauge import _lua


class ThickArmorGaugeGeometryTests(unittest.TestCase):
    def test_workspace_scale_matrix_thick_armor_geometry(self):
        for width, height in ((1920, 1080), (1280, 720), (1680, 1050)):
            for scale in (1.0041298879984, .95, 1, 1.05):
                with self.subTest(workspace=(width, height), scale=scale):
                    lua, ok = _lua()
                    self.assertTrue(ok)
                    g = lua.globals()
                    g.test_w, g.test_h, g.test_scale = width, height, scale
                    lua.execute('''
                        local es = math.min(test_w / 1920, test_h / 1080) * test_scale
                        local gauge = kyohud.hud.gauge.new(panel_double, "thick")
                        gauge:set_geometry(0, 0, 440 * es, 42 * es)
                        local hp = {current=82, total=100, ratio=.82, valid=true, provenance="local"}
                        local ar = {current=0, total=100, ratio=0, valid=true, provenance="local"}
                        gauge:render(hp, ar, "real", 10)

                        _armor_h = gauge.armor_fill:h()
                        _health_h = gauge.health_fill:h()
                        _dy = gauge.health_fill:y() - gauge.armor_fill:y()
                        _dx = gauge.health_fill:x() - gauge.armor_fill:x()
                        _dw = gauge._armor_bg:w() - gauge.health_fill:w()
                        _dh = gauge._armor_bg:h() - gauge.health_fill:h()
                        _afs = gauge.armor_text:font_size()
                        _hfs = gauge.health_text:font_size()
                        _armor_w = gauge.armor_fill:w()
                        _centered = math.abs(
                            (gauge.health_text:y() + gauge.health_text:h() / 2) -
                            (gauge.armor_text:y() + gauge.armor_text:h() / 2)
                        ) < 0.001
                        _ok_pos = gauge:verify()
                        _es = es

                        local af = gauge.armor_fill
                        af:set_shape(af:x(), af:y(), af:w(), af:h() + 7)
                        _ok_corrupt = gauge:verify()
                        _same_af_corrupt = (gauge.armor_fill == af)

                        gauge:render(hp, ar, "real", 10)
                        _ok_recovered = gauge:verify()
                        _same_af_recovered = (gauge.armor_fill == af)
                    ''')
                    g2 = lua.globals()
                    es = float(g2._es)
                    self.assertAlmostEqual(float(g2._armor_h), 26 * es, places=3,
                        msg="armor_fill h == 26*es")
                    self.assertAlmostEqual(float(g2._health_h), 14 * es, places=3,
                        msg="health_fill h == 14*es")
                    self.assertAlmostEqual(float(g2._dy), 6 * es, places=3,
                        msg="y inset == 6*es")
                    self.assertAlmostEqual(float(g2._dx), 6 * es, places=3,
                        msg="x inset == 6*es")
                    self.assertAlmostEqual(float(g2._dw), 12 * es, places=3,
                        msg="outer-inner width diff == 12*es")
                    self.assertAlmostEqual(float(g2._dh), 12 * es, places=3,
                        msg="outer-inner height diff == 12*es")
                    self.assertAlmostEqual(float(g2._afs), 24 * es, places=3,
                        msg="armor font == 24*es")
                    self.assertAlmostEqual(float(g2._hfs), 24 * es, places=3,
                        msg="health font == 24*es")
                    self.assertAlmostEqual(float(g2._armor_w), 0.0, places=3,
                        msg="zero armor fill width")
                    self.assertTrue(bool(g2._centered),
                        "health and armor text must share vertical center")
                    self.assertTrue(bool(g2._ok_pos),
                        "positive verify must pass before corruption")
                    self.assertFalse(bool(g2._ok_corrupt),
                        "corrupt armor_fill height must fail verify")
                    self.assertTrue(bool(g2._same_af_corrupt),
                        "armor_fill object identity preserved after corruption")
                    self.assertTrue(bool(g2._ok_recovered),
                        "render must restore armor_fill height")
                    self.assertTrue(bool(g2._same_af_recovered),
                        "armor_fill object identity preserved after recovery")


    def test_gauge_numeric_contract(self):
        lua, ok = _lua()
        self.assertTrue(ok)
        if not ok:
            return
        lua.execute('''
            local gauge = kyohud.hud.gauge.new(panel_double, "contract")
            gauge:set_geometry(0, 0, 440, 42)
            local hp = {current=82, total=100, ratio=.82, valid=true, provenance="local"}
            local ar = {current=65, total=100, ratio=.65, valid=true, provenance="local"}

            gauge:render(hp, ar, "percentage", 10)
            _pct_hp = gauge.health_text:text()
            _pct_ar = gauge.armor_text:text()
            _bgw = gauge._armor_bg:w()
            _afw = gauge.armor_fill:w()
            _usable = gauge.health_fill:w() - 6
            _inner_usable = _bgw - 18
            _seg_bw = {}
            for i = 1, 4 do
                _seg_bw[i] = gauge.health_segments[i].background:w()
            end
            _mk_w = {}
            _mk_alpha = {}
            for i = 1, 3 do
                _mk_w[i] = gauge.markers[i]:w()
                _mk_alpha[i] = gauge.markers[i]:alpha()
            end
            _seg_fill_c = {}
            for i = 1, 4 do
                local c = gauge.health_segments[i].fill:color()
                _seg_fill_c[i] = {c.r, c.g, c.b}
            end
            _af_c = gauge.armor_fill:color()
            _af_ref = gauge.armor_fill
            _abg_ref = gauge._armor_bg

            gauge:render(hp, ar, "real", 10)
            _real_hp = gauge.health_text:text()
            _real_ar = gauge.armor_text:text()
            _bgw2 = gauge._armor_bg:w()
            _same_bgw = (_bgw == _bgw2)
            _same_af = (gauge.armor_fill == _af_ref)
            _same_abg = (gauge._armor_bg == _abg_ref)

            local hp_inv = {current=0, total=0, ratio=0, valid=false, provenance="local"}
            local ar_inv = {current=0, total=0, ratio=0, valid=false, provenance="local"}
            gauge:render(hp_inv, ar_inv, "percentage", 10)
            _inv_hp = gauge.health_text:text()
            _inv_ar = gauge.armor_text:text()

            local hp_zero = {current=0, total=100, ratio=0, valid=true, provenance="local"}
            local ar_zero = {current=0, total=100, ratio=0, valid=true, provenance="local"}
            gauge:render(hp_zero, ar_zero, "percentage", 10)
            _zero_hp = gauge.health_text:text()
            _zero_ar = gauge.armor_text:text()
            _zero_afw = gauge.armor_fill:w()
            _zero_sf = {}
            for i = 1, 4 do
                _zero_sf[i] = gauge.health_segments[i].fill:w()
            end
        ''')
        g = lua.globals()
        self.assertEqual(str(g._pct_hp), "82%")
        self.assertEqual(str(g._pct_ar), "65%")
        self.assertAlmostEqual(float(g._afw) / float(g._bgw), 0.65, places=3,
            msg="armor width == .65 * bgWidth")
        self.assertAlmostEqual(float(g._usable), float(g._inner_usable), places=3,
            msg="inner usable == bgw - 18")
        seg_ratios = [0.3, 0.2, 0.25, 0.25]
        for i in range(4):
            self.assertAlmostEqual(float(g._seg_bw[i+1]),
                seg_ratios[i] * float(g._inner_usable), places=2,
                msg=f"segment {i+1} bg width")
        mk_ws = [float(g._mk_w[i+1]) for i in range(3)]
        self.assertEqual(mk_ws[0], mk_ws[1])
        self.assertEqual(mk_ws[1], mk_ws[2])
        for i in range(3):
            self.assertGreater(float(g._mk_alpha[i+1]), 0.99,
                msg=f"marker {i+1} opaque")
        for i in range(4):
            c = g._seg_fill_c[i+1]
            self.assertAlmostEqual(float(c[1]), 159/255, places=2)
            self.assertAlmostEqual(float(c[2]), 208/255, places=2)
            self.assertAlmostEqual(float(c[3]), 94/255, places=2)
        afc = g._af_c
        self.assertAlmostEqual(float(afc.r), 1.0, places=2)
        self.assertAlmostEqual(float(afc.g), 1.0, places=2)
        self.assertAlmostEqual(float(afc.b), 1.0, places=2)
        self.assertEqual(str(g._real_hp), "820")
        self.assertEqual(str(g._real_ar), "650")
        self.assertTrue(bool(g._same_bgw), "same bgWidth across modes")
        self.assertTrue(bool(g._same_af), "same armor_fill object across modes")
        self.assertTrue(bool(g._same_abg), "same _armor_bg object across modes")
        self.assertEqual(str(g._inv_hp), "--")
        self.assertEqual(str(g._inv_ar), "--")
        self.assertEqual(str(g._zero_hp), "0%")
        self.assertEqual(str(g._zero_ar), "0%")
        self.assertAlmostEqual(float(g._zero_afw), 0.0, places=3)
        for i in range(4):
            self.assertAlmostEqual(float(g._zero_sf[i+1]), 0.0, places=3,
                msg=f"zero fill segment {i+1}")


if __name__ == "__main__":
    unittest.main()
