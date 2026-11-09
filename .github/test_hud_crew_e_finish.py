"""Crew card finish -- downs heart, clip/reserve font parity, interaction/status
separation from downs (RED tracer), content backdrop + conditional certification.

Three compact tests against lua/hud/components/crew_card.lua via real lupa.luajit21.

Method 1: human 340x120 clip=24 reserve=114 downs=3.
  FIRST: clip/reserve font sizes equal.
  Require _downs_icon bitmap + _downs_text persistent primitives.
  Heart texture guis/dlcs/chico/textures/pd2/specialization/icons_atlas crop {64,0,64,64}.
  Heart 22e visible RIGHT of reserve; count 3 RIGHT of heart; all bounds <= cardwidth.
  Ammo clip/reserve tightly packed gap <= 6e, no overlap.
  downs=0 -> text "0"; nil -> heart visible, count "--".
  Corrupt heart texture -> verify false -> update -> verify true same object.
  Certification positive clean / corrupt reserve X / repair sameobject.

Method 2: human normal downs=3 interaction=nil.
  _status_text and _interaction_text empty + invisible (downs separated).
  Real interaction -> t=5 -> visible text "lockpick 50%".
  Top <= armor bottom + 8e (no large permanent gap).
  Status hidden during interaction.
  Cancel -> empty hidden.
  condition bleed_out/arrested -> status visible no prefix downs.
  normal/nil -> hidden empty; bot -> both hidden.

Method 3: content backdrop + conditional certification.
  _backdrop rect exists, parent==inst.root, visible, dark RGB<=.1, alpha .65.
  Geometry covers name/ammo/heart+gauge/equipment, height<.75*cardh on normal.
  Verifytrue before corrupt set_alpha(0) -> verifyfalse -> update verifies true samebg.
  Active interaction: backdrop bottom covers interaction box, height grows only occupied row.
  Cancel restores normalheight, gaugeY unchanged, samebg.
  Native condition: mugshot_normal+empty hides status; mugshot_downed+"À terre" shows supplied string.

No production writes. No shell/Git. Reuses fixtures by import.
"""
import unittest

from test_hud_crew_e_equipment_icons import _lua, ICON_FIXTURE

FIXTURE = ICON_FIXTURE

_BOT = '''
    name = nil, level = nil, rank = nil, ai = true, peer_id = nil,
    character_name = "russian",
    health = nil, armor = nil, weapon = nil, equipment = nil, interaction = nil,
    downs = nil, condition_text = nil, condition_icon = nil, condition_phase = nil
'''


def _setup(lua, name="fin"):
    lua.execute(f'''
        local parent = _G.panel_double
        local CC = kyohud.hud.crew_card
        _inst = CC.new(parent, "{name}")
        _inst:set_geometry(0, 0, 340, 120)
    ''')


class CrewCardDownsHeartAmmoFinishTests(unittest.TestCase):

    def test_human_downs_heart_ammo_parity_and_certification(self):
        lua, ok = _lua(setup=FIXTURE)
        self.assertTrue(ok, "RED: crew_card.lua must exist")
        if not ok:
            return
        _setup(lua, "fin1")

        lua.execute('''
            _g_actor = {
                name = "Test", level = 5, rank = 0, ai = false, peer_id = 1,
                character_name = "spanish",
                health = {current=50, total=100, ratio=0.5, valid=true, provenance="network_quantized"},
                armor  = {current=2,  total=5,   ratio=0.4, valid=true, provenance="network_quantized"},
                weapon = {name_id="wpn_test", ammo={current_clip=24, reserve=114}},
                equipment = {
                    deployable  = {id="ammo_bag", amount=2, name_id="ammo_bag_name"},
                    cable_ties  = {amount=0},
                    projectile  = {id="smoke_screen_grenade", amount=1, kind="ability", name_id="ability_smoke"}
                },
                downs = 3, condition_text = "normal", interaction = nil,
                condition_icon = nil, condition_phase = nil
            }
            _inst:update(_g_actor, 0)

            _clip_sz = _inst._weapon_text:font_size()
            _res_sz = _inst._reserve_text:font_size()

            _has_di = _inst._downs_icon ~= nil
            _has_dt = _inst._downs_text ~= nil

            _di_tex = nil
            _di_rect = nil
            if _has_di then
                local tn_ok, tn = pcall(function() return _inst._downs_icon:texture_name() end)
                if tn_ok then _di_tex = tn end
                local r = _inst._downs_icon._texture_rect
                if r then _di_rect = {r[1], r[2], r[3], r[4]} end
            end

            _di_vis = false
            if _has_di then _di_vis = _inst._downs_icon:visible() end
            _di_w = 0
            if _has_di then _di_w = _inst._downs_icon:w() end
            _di_x = 0
            if _has_di then _di_x = _inst._downs_icon:x() end
            _di_right = 0
            if _has_di then _di_right = _inst._downs_icon:x() + _inst._downs_icon:w() end

            _res_right = _inst._reserve_text:x() + _inst._reserve_text:w()

            _dt_vis = false
            if _has_dt then _dt_vis = _inst._downs_text:visible() end
            _dt_text = nil
            if _has_dt then _dt_text = _inst._downs_text:text() end
            _dt_x = 0
            if _has_dt then _dt_x = _inst._downs_text:x() end
            _dt_right = 0
            if _has_dt then _dt_right = _inst._downs_text:x() + _inst._downs_text:w() end

            _card_w = _inst._geo.w

            _clip_right = _inst._weapon_text:x() + _inst._weapon_text:w()
            _res_x = _inst._reserve_text:x()
            _ammo_gap = _res_x - _clip_right
            _ammo_overlap = _res_x < _clip_right

            _ok1 = _inst:verify()

            _ref_di = _inst._downs_icon
            _ref_dt = _inst._downs_text
            _ref_rt = _inst._reserve_text
        ''')
        g = lua.globals()

        self.assertAlmostEqual(float(g._clip_sz), float(g._res_sz), places=1,
            msg="RED: clip and reserve font sizes must be equal")

        self.assertTrue(bool(g._has_di), "RED: _downs_icon bitmap must exist")
        self.assertTrue(bool(g._has_dt), "RED: _downs_text must exist")

        self.assertEqual(g._di_tex,
            "guis/dlcs/chico/textures/pd2/specialization/icons_atlas",
            "RED: heart texture must be chico specialization atlas")
        self.assertIsNotNone(g._di_rect, "RED: _texture_rect must be set")
        self.assertEqual(float(g._di_rect[1]), 64.0)
        self.assertEqual(float(g._di_rect[2]), 0.0)
        self.assertEqual(float(g._di_rect[3]), 64.0)
        self.assertEqual(float(g._di_rect[4]), 64.0)

        self.assertTrue(bool(g._di_vis), "RED: heart visible for downs=3")
        e_val = float(120) / 120.0
        self.assertAlmostEqual(float(g._di_w), 22.0 * e_val, delta=0.05,
            msg="RED: heart size must be 22e")

        self.assertGreaterEqual(float(g._di_x), float(g._res_right) - 0.5,
            "RED: heart must be RIGHT of reserve text")

        self.assertGreaterEqual(float(g._dt_x), float(g._di_right) - 0.5,
            "RED: count must be RIGHT of heart icon")

        self.assertLessEqual(float(g._dt_right), float(g._card_w) + 0.5,
            "RED: all downs bounds must be <= cardwidth")

        self.assertEqual(g._dt_text, "3", "RED: count must be '3'")
        self.assertTrue(bool(g._dt_vis), "RED: count must be visible")

        self.assertFalse(bool(g._ammo_overlap),
            "RED: clip and reserve must not overlap")
        self.assertLessEqual(float(g._ammo_gap), 6.0 * e_val + 0.5,
            "RED: clip/reserve gap must be <= 6e")

        self.assertTrue(bool(g._ok1), "RED: verify() must pass clean")

        lua.execute('''
            _g_actor.downs = 0
            _inst:update(_g_actor, 1)
            _d0_text = _inst._downs_text:text()
            _d0_di_vis = _inst._downs_icon:visible()
            _d0_dt_vis = _inst._downs_text:visible()
        ''')
        g0 = lua.globals()
        self.assertEqual(g0._d0_text, "0", "RED: downs=0 must show '0'")
        self.assertTrue(bool(g0._d0_di_vis), "RED: heart visible for downs=0")
        self.assertTrue(bool(g0._d0_dt_vis), "RED: count visible for downs=0")

        lua.execute('''
            _g_actor.downs = nil
            _inst:update(_g_actor, 2)
            _dn_di = _inst._downs_icon:visible()
            _dn_dt = _inst._downs_text:visible()
            _dn_text = _inst._downs_text:text()
        ''')
        gn = lua.globals()
        self.assertTrue(bool(gn._dn_di), "RED: heart visible for downs=nil")
        self.assertTrue(bool(gn._dn_dt), "RED: count visible for downs=nil")
        self.assertEqual(gn._dn_text, "--", "RED: unknown human downs nil shows '--'")

        lua.execute('''
            _g_actor.downs = 3
            _inst:update(_g_actor, 3)
            _ok_clean = _inst:verify()
            _inst._downs_icon:set_image("wrong/texture", 0, 0, 1, 1)
            _ok_bad = _inst:verify()
            _inst:update(_g_actor, 4)
            _ok_rep = _inst:verify()
            _same_di = _inst._downs_icon == _ref_di
            _rep_tex = _inst._downs_icon:texture_name()
        ''')
        gc = lua.globals()
        self.assertTrue(bool(gc._ok_clean), "clean verify before corruption")
        self.assertFalse(bool(gc._ok_bad),
            "RED: verify false after heart texture corruption")
        self.assertTrue(bool(gc._ok_rep),
            "RED: verify true after heart texture repair")
        self.assertTrue(bool(gc._same_di),
            "RED: same _downs_icon after repair")
        self.assertEqual(gc._rep_tex,
            "guis/dlcs/chico/textures/pd2/specialization/icons_atlas",
            "RED: heart texture restored")

        lua.execute('''
            _inst._reserve_text:set_text("X")
            _ok_bad_rt = _inst:verify()
            _inst:update(_g_actor, 5)
            _ok_rt_rep = _inst:verify()
            _same_rt = _inst._reserve_text == _ref_rt
            _rt_text = _inst._reserve_text:text()
        ''')
        gx = lua.globals()
        self.assertFalse(bool(gx._ok_bad_rt),
            "RED: verify false after reserve text corruption")
        self.assertTrue(bool(gx._ok_rt_rep),
            "RED: verify true after reserve text repair")
        self.assertTrue(bool(gx._same_rt),
            "RED: same _reserve_text after repair")
        self.assertEqual(gx._rt_text, "/114",
            "RED: reserve text restored to '/114'")

        lua.execute('''
            local bot = { ''' + _BOT + ''' }
            _inst:update(bot, 6)
            _bot_di_vis = _inst._downs_icon:visible()
            _bot_dt_vis = _inst._downs_text:visible()
            _bot_has_di = _inst._downs_icon ~= nil
            _bot_has_dt = _inst._downs_text ~= nil
            _bot_same_di = _inst._downs_icon == _ref_di
            _bot_same_dt = _inst._downs_text == _ref_dt
        ''')
        gb = lua.globals()
        self.assertFalse(bool(gb._bot_di_vis), "RED: heart invisible for bot")
        self.assertFalse(bool(gb._bot_dt_vis), "RED: count invisible for bot")
        self.assertTrue(bool(gb._bot_has_di), "RED: human _downs_icon ref retained for bot")
        self.assertTrue(bool(gb._bot_has_dt), "RED: human _downs_text ref retained for bot")
        self.assertTrue(bool(gb._bot_same_di), "RED: same _downs_icon object after bot switch")
        self.assertTrue(bool(gb._bot_same_dt), "RED: same _downs_text object after bot switch")

    def test_human_interaction_status_separated_from_downs(self):
        lua, ok = _lua(setup=FIXTURE)
        self.assertTrue(ok, "RED: crew_card.lua must exist")
        if not ok:
            return
        _setup(lua, "fin2")

        lua.execute('''
            _g_actor = {
                name = "Test", level = 5, rank = 0, ai = false, peer_id = 1,
                character_name = "spanish",
                health = {current=50, total=100, ratio=0.5, valid=true, provenance="network_quantized"},
                armor  = {current=2,  total=5,   ratio=0.4, valid=true, provenance="network_quantized"},
                weapon = {name_id="wpn_test", ammo={current_clip=24, reserve=114}},
                equipment = {
                    deployable  = {id="ammo_bag", amount=2, name_id="ammo_bag_name"},
                    cable_ties  = {amount=0},
                    projectile  = {id="smoke_screen_grenade", amount=1, kind="ability", name_id="ability_smoke"}
                },
                downs = 3, condition_text = "normal", interaction = nil,
                condition_icon = nil, condition_phase = nil
            }
            _inst:update(_g_actor, 0)

            _st_text = _inst._status_text:text()
            _st_vis = _inst._status_text:visible()
            _it_text = _inst._interaction_text:text()
            _it_vis = _inst._interaction_text:visible()
        ''')
        g = lua.globals()
        self.assertEqual(g._st_text, "",
            "RED: _status_text empty when downs separated")
        self.assertFalse(bool(g._st_vis),
            "RED: _status_text invisible when no condition")
        self.assertEqual(g._it_text, "",
            "RED: _interaction_text empty when no interaction")
        self.assertFalse(bool(g._it_vis),
            "RED: _interaction_text invisible when no interaction")

        lua.execute('''
            _g_actor.interaction = {
                enabled=true, success=false,
                tweak_data_id="lockpick", duration=10, started_t=0
            }
            _inst:update(_g_actor, 5)
            _it2_text = _inst._interaction_text:text()
            _it2_vis = _inst._interaction_text:visible()
            _st2_vis = _inst._status_text:visible()
            _st2_text = _inst._status_text:text()
            _it_y = _inst._interaction_text:y()
            _ar_bottom = _inst._ar_bg:y() + _inst._ar_bg:h()
            _e = _inst._geo.h / 120
        ''')
        g2 = lua.globals()
        self.assertEqual(g2._it2_text, "lockpick 50%",
            "RED: interaction text at t=5")
        self.assertTrue(bool(g2._it2_vis),
            "RED: interaction visible during active interaction")
        self.assertFalse(bool(g2._st2_vis),
            "RED: status hidden during interaction")
        self.assertLessEqual(float(g2._it_y),
            float(g2._ar_bottom) + 8.0 * float(g2._e) + 0.5,
            "RED: interaction top <= armor bottom + 8e")

        lua.execute('''
            _g_actor.interaction = {
                enabled=false, success=false,
                tweak_data_id="lockpick", duration=10, started_t=0
            }
            _inst:update(_g_actor, 6)
            _it3_text = _inst._interaction_text:text()
            _it3_vis = _inst._interaction_text:visible()
        ''')
        g3 = lua.globals()
        self.assertEqual(g3._it3_text, "",
            "RED: interaction empty after cancel")
        self.assertFalse(bool(g3._it3_vis),
            "RED: interaction invisible after cancel")

        lua.execute('''
            _g_actor.interaction = nil
            _g_actor.condition_text = "bleed_out"
            _inst:update(_g_actor, 7)
            _st4_text = _inst._status_text:text()
            _st4_vis = _inst._status_text:visible()
        ''')
        g4 = lua.globals()
        self.assertTrue(bool(g4._st4_vis),
            "RED: status visible for bleed_out")
        self.assertNotIn("3", str(g4._st4_text),
            "RED: status no downs prefix for bleed_out")

        lua.execute('''
            _g_actor.condition_text = "arrested"
            _inst:update(_g_actor, 8)
            _st5_text = _inst._status_text:text()
            _st5_vis = _inst._status_text:visible()
        ''')
        g5 = lua.globals()
        self.assertTrue(bool(g5._st5_vis),
            "RED: status visible for arrested")
        self.assertNotIn("3", str(g5._st5_text),
            "RED: status no downs prefix for arrested")

        lua.execute('''
            _g_actor.condition_text = "normal"
            _inst:update(_g_actor, 9)
            _st6_text = _inst._status_text:text()
            _st6_vis = _inst._status_text:visible()
        ''')
        g6 = lua.globals()
        self.assertEqual(g6._st6_text, "",
            "RED: status empty for normal")
        self.assertFalse(bool(g6._st6_vis),
            "RED: status hidden for normal")

        lua.execute('''
            _g_actor.condition_text = nil
            _inst:update(_g_actor, 10)
            _st7_text = _inst._status_text:text()
            _st7_vis = _inst._status_text:visible()
        ''')
        g7 = lua.globals()
        self.assertEqual(g7._st7_text, "",
            "RED: status empty for nil")
        self.assertFalse(bool(g7._st7_vis),
            "RED: status hidden for nil")

        lua.execute('''
            local bot = { ''' + _BOT + ''' }
            _inst:update(bot, 11)
            _st8_vis = _inst._status_text:visible()
            _it8_vis = _inst._interaction_text:visible()
            _st8_text = _inst._status_text:text()
            _it8_text = _inst._interaction_text:text()
        ''')
        g8 = lua.globals()
        self.assertFalse(bool(g8._st8_vis), "RED: status hidden for bot")
        self.assertFalse(bool(g8._it8_vis), "RED: interaction hidden for bot")
        self.assertEqual(g8._st8_text, "", "RED: status empty for bot")
        self.assertEqual(g8._it8_text, "", "RED: interaction empty for bot")

    def test_backdrop_content_and_condition_certification(self):
        lua, ok = _lua(setup=FIXTURE)
        self.assertTrue(ok, "RED: crew_card.lua must exist")
        if not ok: return
        _setup(lua, "bd1")
        lua.execute('''
            _g_actor = {
                name = "Test", level = 5, rank = 0, ai = false, peer_id = 1,
                character_name = "spanish",
                health = {current=50, total=100, ratio=0.5, valid=true, provenance="network_quantized"},
                armor  = {current=2,  total=5,   ratio=0.4, valid=true, provenance="network_quantized"},
                weapon = {name_id="wpn_test", ammo={current_clip=24, reserve=114}},
                equipment = {
                    deployable  = {id="ammo_bag", amount=2, name_id="ammo_bag_name"},
                    cable_ties  = {amount=0},
                    projectile  = {id="smoke_screen_grenade", amount=1, kind="ability", name_id="ability_smoke"}
                },
                downs = 3, condition_text = "normal", interaction = nil,
                condition_icon = nil, condition_phase = nil
            }
            _inst:update(_g_actor, 0)
            _bd = _inst._backdrop
            _bd_exists = _bd ~= nil
            _bd_parent_ok = false; _bd_vis = false; _bd_alpha = 0
            _bd_r = 1; _bd_g = 1; _bd_b = 1
            _bd_x = 0; _bd_y = 0; _bd_w = 0; _bd_h = 0
            if _bd_exists then
                _bd_parent_ok = (_bd:parent() == _inst.root)
                _bd_vis = _bd:visible(); _bd_alpha = _bd:alpha()
                local c = _bd:color()
                if c then _bd_r = c.r or 1; _bd_g = c.g or 1; _bd_b = c.b or 1 end
                _bd_x = _bd:x(); _bd_y = _bd:y(); _bd_w = _bd:w(); _bd_h = _bd:h()
            end
            _cardh = _inst._geo.h
            _nm_y = _inst._name_text:y(); _nm_bottom = _inst._name_text:y() + _inst._name_text:h()
            _wp_bottom = _inst._weapon_text:y() + _inst._weapon_text:h()
            _heart_bottom = _inst._downs_icon:y() + _inst._downs_icon:h()
            _eq_bottom = _inst._equipment_text:y() + _inst._equipment_text:h()
            _ok_clean = _inst:verify(); _ref_bd = _inst._backdrop
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._bd_exists), "RED: _backdrop rect must exist")
        self.assertTrue(bool(g._bd_parent_ok), "RED: _backdrop parent==inst.root")
        self.assertTrue(bool(g._bd_vis), "RED: _backdrop visible")
        self.assertLessEqual(float(g._bd_r), 0.1, "RED: dark R<=.1")
        self.assertLessEqual(float(g._bd_g), 0.1, "RED: dark G<=.1")
        self.assertLessEqual(float(g._bd_b), 0.1, "RED: dark B<=.1")
        self.assertAlmostEqual(float(g._bd_alpha), 0.65, places=2, msg="RED: alpha .65")
        self.assertLessEqual(float(g._bd_y), float(g._nm_y) + 0.5, "RED: covers name top")
        self.assertGreaterEqual(float(g._bd_y) + float(g._bd_h), float(g._nm_bottom) - 0.5, "RED: covers name")
        self.assertGreaterEqual(float(g._bd_y) + float(g._bd_h), float(g._wp_bottom) - 0.5, "RED: covers ammo")
        self.assertGreaterEqual(float(g._bd_y) + float(g._bd_h), float(g._heart_bottom) - 0.5, "RED: covers heart+gauge")
        self.assertGreaterEqual(float(g._bd_y) + float(g._bd_h), float(g._eq_bottom) - 0.5, "RED: covers equipment")
        self.assertLess(float(g._bd_h), 0.75 * float(g._cardh), "RED: height<.75*cardh normal")
        self.assertTrue(bool(g._ok_clean), "RED: verifytrue before corrupt")
        lua.execute('''
            _inst._backdrop:set_alpha(0)
            _ok_bad = _inst:verify()
            _inst:update(_g_actor, 1)
            _ok_rep = _inst:verify()
            _same_bg = _inst._backdrop == _ref_bd
            _bd_alpha_rep = _inst._backdrop:alpha()
        ''')
        gc = lua.globals()
        self.assertFalse(bool(gc._ok_bad), "RED: verifyfalse after set_alpha(0)")
        self.assertTrue(bool(gc._ok_rep), "RED: update verifies true")
        self.assertTrue(bool(gc._same_bg), "RED: samebg after repair")
        self.assertAlmostEqual(float(gc._bd_alpha_rep), 0.65, places=2, msg="RED: alpha restored")
        lua.execute('''
            _g_actor.interaction = {enabled=true, success=false, tweak_data_id="lockpick", duration=10, started_t=0}
            _inst:update(_g_actor, 5)
            _bd_h_int = _inst._backdrop:h(); _bd_y_int = _inst._backdrop:y()
            _bd_bottom_int = _bd_y_int + _bd_h_int
            _it_bottom = _inst._interaction_text:y() + _inst._interaction_text:h()
            _gauge_y = _inst.root:y() + _inst._hp_bg:y(); _cardh_int = _inst._geo.h
            _state_bottom = _inst._state_bg:y() + _inst._state_bg:h()
            _state_top = _inst._state_bg:y()
        ''')
        gi = lua.globals()
        self.assertGreaterEqual(float(gi._state_bottom), float(gi._it_bottom) - 0.5, "state backing covers interaction")
        self.assertLess(float(gi._state_bottom), float(gi._bd_y_int), "state backing is above main body")
        self.assertAlmostEqual(float(gi._bd_h_int), float(g._bd_h), places=3, msg="body backdrop does not grow for the header")
        lua.execute('''
            _g_actor.interaction = nil
            _inst:update(_g_actor, 6)
            _bd_h_cancel = _inst._backdrop:h()
            _gauge_y_after = _inst.root:y() + _inst._hp_bg:y()
            _same_bg_cancel = _inst._backdrop == _ref_bd
        ''')
        gk = lua.globals()
        self.assertAlmostEqual(float(gk._bd_h_cancel), float(g._bd_h), places=1, msg="RED: normalheight restored")
        self.assertAlmostEqual(float(gk._gauge_y_after), float(gi._gauge_y), places=1, msg="RED: gaugeY unchanged")
        self.assertTrue(bool(gk._same_bg_cancel), "RED: samebg after cancel")
        lua.execute('''
            _g_actor.condition_icon = "mugshot_normal"; _g_actor.condition_text = ""
            _inst:update(_g_actor, 7)
            _st_vis_mn = _inst._status_text:visible(); _st_text_mn = _inst._status_text:text()
        ''')
        gm = lua.globals()
        self.assertFalse(bool(gm._st_vis_mn), "RED: mugshot_normal+empty hides status")
        lua.execute('''
            _g_actor.condition_icon = "mugshot_downed"; _g_actor.condition_text = "\\195\\128 terre"
            _inst:update(_g_actor, 8)
            _st_vis_md = _inst._status_text:visible(); _st_text_md = _inst._status_text:text()
        ''')
        gd = lua.globals()
        self.assertTrue(bool(gd._st_vis_md), "RED: mugshot_downed shows status")
        self.assertEqual(gd._st_text_md, "À terre", "RED: actual supplied string, no invented localization")


if __name__ == "__main__":
    unittest.main()
