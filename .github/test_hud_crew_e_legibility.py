"""Crew card legibility -- name/equipment font floors and right-anchored geometry (RED tracer).

Two compact tests against lua/hud/components/crew_card.lua via real lupa.luajit21.

Method 1: Font scaling legibility.
  Human name font >= 20e (current 17.28e = r0.h*0.72).
  Equipment icon >= 22e (current min(r1.h, 18*e) = 18e).
  Equipment quantities text >= 20e (current r1.h*0.80 = 16.32e).
  Scales .95/1/1.05: all floors hold at every scale.
  Corruption: externally set font size -> verify false -> update restores same primitive.

Method 2: Geometry and right-anchoring.
  Peer dot vertically centered on actual measured name ink (text_rect 4th return).
  Heart+downs right-anchored with fixed 4e right padding from card right edge.
  Independent ammo strings 24/114 and 999/1234: no overlap, same font clip/reserve.
  Downs=0 -> "0"; nil -> "--".
  Corruption: move heart -> verify false -> update restores same primitive.
  Snapshot before transition preserves identity.

No production writes. No shell/Git. Reuses fixtures by import.
"""
import unittest

from test_hud_crew_e_equipment_icons import _lua, ICON_FIXTURE

FIXTURE = ICON_FIXTURE


def _setup(lua, name="leg"):
    lua.execute(f'''
        local parent = _G.panel_double
        local CC = kyohud.hud.crew_card
        _inst = CC.new(parent, "{name}")
    ''')


class CrewCardLegibilityTests(unittest.TestCase):

    def test_name_and_equipment_font_floors(self):
        """Name >= 20e, equipment icon >= 22e, equipment quantities >= 20e at all scales."""
        for scale in (0.95, 1.0, 1.05):
            with self.subTest(scale=scale):
                lua, ok = _lua(setup=FIXTURE)
                self.assertTrue(ok, "RED: crew_card.lua must exist")
                if not ok:
                    return
                _setup(lua, f"fs{scale}")

                w = 340 * scale
                h = 120 * scale

                lua.execute(f'''
                    _inst:set_geometry(0, 0, {w}, {h})
                    actor = {{
                        name = "Test", level = 5, rank = 0, ai = false, peer_id = 1,
                        character_name = "spanish",
                        health = {{current=50, total=100, ratio=0.5, valid=true, provenance="network_quantized"}},
                        armor  = {{current=2,  total=5,   ratio=0.4, valid=true, provenance="network_quantized"}},
                        weapon = {{name_id="wpn_test", ammo={{current_clip=24, reserve=114}}}},
                        equipment = {{
                            deployable  = {{id="ammo_bag", amount=2, name_id="ammo_bag_name"}},
                            cable_ties  = {{amount=0}},
                            projectile  = {{id="smoke_screen_grenade", amount=1, kind="ability", name_id="ability_smoke"}}
                        }},
                        downs = 3, condition_text = "normal", interaction = nil,
                        condition_icon = nil, condition_phase = nil
                    }}
                    _inst:update(actor, 0)

                    _e = _inst._geo.h / 120
                    _nm_sz = _inst._name_text:font_size()
                    _eq_icon_sz = _inst._deployable_icon:w()
                    _eq_txt_sz = _inst._equipment_text:font_size()
                    _ok = _inst:verify()
                    _ref_nm = _inst._name_text
                    _ref_di = _inst._deployable_icon
                    _ref_eq = _inst._equipment_text

                    _eq_txt = _inst._equipment_text:text()
                    _cb_txt = _inst._cables_text:text()
                    _pj_txt = _inst._projectile_text:text()
                    _cb_txt_sz = _inst._cables_text:font_size()
                    _pj_txt_sz = _inst._projectile_text:font_size()

                    _di_x = _inst._deployable_icon:x()
                    _di_r = _di_x + _inst._deployable_icon:w()
                    _ci_x = _inst._cables_icon:x()
                    _ci_r = _ci_x + _inst._cables_icon:w()
                    _pi_x = _inst._projectile_icon:x()
                    _pi_r = _pi_x + _inst._projectile_icon:w()
                    _eq_x = _inst._equipment_text:x()
                    _eq_r = _eq_x + _inst._equipment_text:w()
                    _cb_x = _inst._cables_text:x()
                    _cb_r = _cb_x + _inst._cables_text:w()
                    _pj_x = _inst._projectile_text:x()
                    _pj_r = _pj_x + _inst._projectile_text:w()
                    _c1_l = math.min(_di_x, _eq_x)
                    _c1_r = math.max(_di_r, _eq_r)
                    _c2_l = math.min(_ci_x, _cb_x)
                    _c2_r = math.max(_ci_r, _cb_r)
                    _c3_l = math.min(_pi_x, _pj_x)
                    _c3_r = math.max(_pi_r, _pj_r)
                    _disjoint_12 = _c1_r <= _c2_l + 0.5
                    _disjoint_23 = _c2_r <= _c3_l + 0.5
                    _card_w_eq = _inst._geo.w
                    _within_card = _c1_l >= -0.5 and _c3_r <= _card_w_eq + 0.5
                ''')
                g = lua.globals()
                e = float(g._e)

                self.assertGreaterEqual(float(g._nm_sz), 20.0 * e - 0.5,
                    f"RED: name font must be >= 20e (got {float(g._nm_sz)/e:.2f}e)")

                self.assertGreaterEqual(float(g._eq_icon_sz), 22.0 * e - 0.5,
                    f"RED: equipment icon must be >= 22e (got {float(g._eq_icon_sz)/e:.2f}e)")

                self.assertGreaterEqual(float(g._eq_txt_sz), 20.0 * e - 0.5,
                    f"RED: equipment quantities must be >= 20e (got {float(g._eq_txt_sz)/e:.2f}e)")

                self.assertEqual(g._eq_txt, "2", "RED: deployable text is short qty '2'")
                self.assertEqual(g._cb_txt, "0", "RED: cables text is short qty '0'")
                self.assertEqual(g._pj_txt, "1", "RED: projectile text is short qty '1'")
                self.assertGreaterEqual(float(g._cb_txt_sz), 20.0 * e - 0.5,
                    f"RED: cables qty font >= 20e (got {float(g._cb_txt_sz)/e:.2f}e)")
                self.assertGreaterEqual(float(g._pj_txt_sz), 20.0 * e - 0.5,
                    f"RED: projectile qty font >= 20e (got {float(g._pj_txt_sz)/e:.2f}e)")

                self.assertTrue(bool(g._disjoint_12),
                    "RED: equipment cell 1 (deployable) and cell 2 (cables) must be disjoint")
                self.assertTrue(bool(g._disjoint_23),
                    "RED: equipment cell 2 (cables) and cell 3 (projectile) must be disjoint")
                self.assertTrue(bool(g._within_card),
                    "RED: all 3 equipment cells within card bounds")

                self.assertTrue(bool(g._ok), "verify() true before corruption")

                lua.execute('''
                    _inst._name_text:set_font_size(5)
                    _ok_bad = _inst:verify()
                    _inst:update(actor, 1)
                    _ok_rep = _inst:verify()
                    _same_nm = _inst._name_text == _ref_nm
                    _rep_sz = _inst._name_text:font_size()
                ''')
                gc = lua.globals()
                self.assertFalse(bool(gc._ok_bad), "verify false after name font corruption")
                self.assertTrue(bool(gc._ok_rep), "verify true after name font repair")
                self.assertTrue(bool(gc._same_nm), "same _name_text after repair")
                self.assertGreaterEqual(float(gc._rep_sz), 20.0 * e - 0.5,
                    "restored name font >= 20e")

                lua.execute('''
                    _inst._equipment_text:set_font_size(5)
                    _ok_bad_eq = _inst:verify()
                    _inst:update(actor, 2)
                    _ok_rep_eq = _inst:verify()
                    _same_eq = _inst._equipment_text == _ref_eq
                ''')
                ge = lua.globals()
                self.assertFalse(bool(ge._ok_bad_eq), "verify false after equipment font corruption")
                self.assertTrue(bool(ge._ok_rep_eq), "verify true after equipment font repair")
                self.assertTrue(bool(ge._same_eq), "same _equipment_text after repair")

    def test_peer_dot_centering_and_right_anchor(self):
        """Peer dot centered on name ink, heart+downs right-anchored 4e from edge,
        ammo independent at 24/114 vs 999/1234."""
        for scale in (0.95, 1.0, 1.05):
            with self.subTest(scale=scale):
                lua, ok = _lua(setup=FIXTURE)
                self.assertTrue(ok, "RED: crew_card.lua must exist")
                if not ok:
                    return
                _setup(lua, f"ra{scale}")

                w = 340 * scale
                h = 120 * scale

                lua.execute(f'''
                    _inst:set_geometry(0, 0, {w}, {h})
                    actor = {{
                        name = "Test", level = 5, rank = 0, ai = false, peer_id = 1,
                        character_name = "spanish",
                        health = {{current=50, total=100, ratio=0.5, valid=true, provenance="network_quantized"}},
                        armor  = {{current=2,  total=5,   ratio=0.4, valid=true, provenance="network_quantized"}},
                        weapon = {{name_id="wpn_test", ammo={{current_clip=24, reserve=114}}}},
                        equipment = {{
                            deployable  = {{id="ammo_bag", amount=2, name_id="ammo_bag_name"}},
                            cable_ties  = {{amount=0}},
                            projectile  = {{id="smoke_screen_grenade", amount=1, kind="ability", name_id="ability_smoke"}}
                        }},
                        downs = 3, condition_text = "normal", interaction = nil,
                        condition_icon = nil, condition_phase = nil
                    }}
                    _inst:update(actor, 0)

                    _e = _inst._geo.h / 120
                    _card_w = _inst._geo.w

                    -- Peer dot vs name ink vertical center (text_rect: x,y,w,h)
                    local _nm_tr_x, _nm_tr_y, _nm_tr_w, _nm_tr_h = _inst._name_text:text_rect()
                    _nm_ink_cy = _inst._name_text:y() + _nm_tr_y + _nm_tr_h * 0.5
                    _dot_cy = _inst._peer_dot:y() + _inst._peer_dot:h() * 0.5

                    -- Heart+downs right-anchoring: right edge of downs_text from card edge
                    _dt_right = _inst._downs_text:x() + _inst._downs_text:w()
                    _right_margin = _card_w - _dt_right

                    -- Clip/reserve same font
                    _clip_sz = _inst._weapon_text:font_size()
                    _res_sz = _inst._reserve_text:font_size()

                    -- No overlap clip/reserve at 24/114
                    _clip_right = _inst._weapon_text:x() + _inst._weapon_text:w()
                    _res_x = _inst._reserve_text:x()
                    _overlap_114 = _res_x < _clip_right

                    _ok1 = _inst:verify()
                    _ref_di = _inst._downs_icon
                    _ref_dt = _inst._downs_text
                    _snap_di = _inst._downs_icon
                    _snap_dt = _inst._downs_text
                ''')
                g = lua.globals()
                e = float(g._e)

                self.assertAlmostEqual(float(g._dot_cy), float(g._nm_ink_cy), delta=1.0,
                    msg="RED: peer dot must be vertically centered on measured name ink (text_rect)")

                self.assertAlmostEqual(float(g._right_margin), 4.0 * e, delta=1.0,
                    msg="RED: heart+downs right-anchored with fixed 4e right padding")

                self.assertAlmostEqual(float(g._clip_sz), float(g._res_sz), places=1,
                    msg="RED: clip and reserve font sizes must be equal")

                self.assertFalse(bool(g._overlap_114),
                    "RED: clip and reserve must not overlap at 24/114")

                self.assertTrue(bool(g._ok1), "verify true at 24/114")

                lua.execute(f'''
                    -- Transition to 999/1234 ammo
                    actor2 = {{
                        name = "Test", level = 5, rank = 0, ai = false, peer_id = 1,
                        character_name = "spanish",
                        health = {{current=50, total=100, ratio=0.5, valid=true, provenance="network_quantized"}},
                        armor  = {{current=2,  total=5,   ratio=0.4, valid=true, provenance="network_quantized"}},
                        weapon = {{name_id="wpn_test", ammo={{current_clip=999, reserve=1234}}}},
                        equipment = {{
                            deployable  = {{id="ammo_bag", amount=2, name_id="ammo_bag_name"}},
                            cable_ties  = {{amount=0}},
                            projectile  = {{id="smoke_screen_grenade", amount=1, kind="ability", name_id="ability_smoke"}}
                        }},
                        downs = 3, condition_text = "normal", interaction = nil,
                        condition_icon = nil, condition_phase = nil
                    }}
                    _inst:update(actor2, 1)

                    _clip_right2 = _inst._weapon_text:x() + _inst._weapon_text:w()
                    _res_x2 = _inst._reserve_text:x()
                    _overlap_1234 = _res_x2 < _clip_right2

                    _clip_sz2 = _inst._weapon_text:font_size()
                    _res_sz2 = _inst._reserve_text:font_size()

                    _dt_right2 = _inst._downs_text:x() + _inst._downs_text:w()
                    _right_margin2 = _card_w - _dt_right2

                    _clip_text = _inst._weapon_text:text()
                    _res_text = _inst._reserve_text:text()

                    _res_right2 = _inst._reserve_text:x() + _inst._reserve_text:w()
                    _heart_x = _inst._downs_icon:x()
                    _res_to_heart_gap = _heart_x - _res_right2

                    _ok2 = _inst:verify()
                    _same_after_trans = _inst._downs_icon == _snap_di and _inst._downs_text == _snap_dt
                ''')
                g2 = lua.globals()

                self.assertFalse(bool(g2._overlap_1234),
                    "RED: clip and reserve must not overlap at 999/1234")

                self.assertAlmostEqual(float(g2._clip_sz2), float(g2._res_sz2), places=1,
                    msg="RED: clip/reserve same font at 999/1234")

                self.assertAlmostEqual(float(g2._right_margin2), 4.0 * e, delta=1.0,
                    msg="RED: right margin stays 4e at 999/1234")

                self.assertTrue(bool(g2._ok2), "verify true at 999/1234")
                self.assertTrue(bool(g2._same_after_trans),
                    "same heart+downs primitives after ammo transition")

                self.assertEqual(g2._clip_text, "999",
                    "RED: clip text must be exact '999'")
                self.assertEqual(g2._res_text, "/1234",
                    "RED: reserve text must be exact '/1234'")

                self.assertGreaterEqual(float(g2._res_to_heart_gap), 2.0 * e - 0.5,
                    "RED: reserve right <= heart x minus gap (>= 2e)")

                lua.execute('''
                    -- Downs=0 and nil
                    actor2.downs = 0
                    _inst:update(actor2, 2)
                    _d0_text = _inst._downs_text:text()
                    _d0_di_vis = _inst._downs_icon:visible()

                    actor2.downs = nil
                    _inst:update(actor2, 3)
                    _dn_text = _inst._downs_text:text()
                    _dn_di_vis = _inst._downs_icon:visible()

                    -- Corruption: move heart position
                    _inst._downs_icon:set_shape(-5, -5, 1, 1)
                    _ok_bad = _inst:verify()

                    -- Restore
                    actor2.downs = 3
                    _inst:update(actor2, 4)
                    _ok_rep = _inst:verify()
                    _same_di = _inst._downs_icon == _ref_di
                    _same_dt = _inst._downs_text == _ref_dt
                ''')
                gd = lua.globals()
                self.assertEqual(gd._d0_text, "0", "RED: downs=0 shows '0'")
                self.assertTrue(bool(gd._d0_di_vis), "RED: heart visible for downs=0")
                self.assertEqual(gd._dn_text, "--", "RED: downs=nil shows '--'")
                self.assertTrue(bool(gd._dn_di_vis), "RED: heart visible for downs=nil")
                self.assertFalse(bool(gd._ok_bad), "verify false after heart geometry corruption")
                self.assertTrue(bool(gd._ok_rep), "verify true after heart geometry repair")
                self.assertTrue(bool(gd._same_di), "same _downs_icon after repair")
                self.assertTrue(bool(gd._same_dt), "same _downs_text after repair")


if __name__ == "__main__":
    unittest.main()
