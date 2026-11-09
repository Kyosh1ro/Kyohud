"""Crew Card ammo primitives -- _weapon_text (clip) and _reserve_text (reserve).

One test method validating:
  _weapon_text shows zero-padded clip only (e.g. "001"), never the raw identifier.
  _reserve_text shows "/" + zero-padded reserve (e.g. "/045").
  Clip font size > reserve font size; clip WHITE, reserve DIM 0.7.
  Equipment text vertical center == human outer armor track (_ar_bg) center.
  All 3 equipment icons share that same vertical center.
  Ammo row sits above equipment row.
  Corruption of _reserve_text -> verify false -> update alone repairs same ref.
  Formatting loop: 0/0=>000,/000; 45/195=>045,/195; nil/nil=>---,/---;
    1000/1234=>1000,/1234; negative/NaN/infinite=>---,/---.
  Bot switch hides both ammo primitives.

RED: production code currently concatenates name_id + clip/reserve into
_weapon_text and has no _reserve_text primitive.
"""
import unittest

from test_hud_crew_card import _lua


class CrewCardAmmoPrimitiveTests(unittest.TestCase):
    def test_human_ammo_formatting_layout_and_corruption(self):
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return

        lua.execute('''
            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            inst = CC.new(parent, "ammo")
            inst:set_geometry(0, 0, 340, 120)

            _g_actor = {
                name = "Test", level = 1, rank = 0, ai = false, peer_id = 1,
                character_name = "spanish",
                health = {ratio = 0.82, valid = true, provenance = "network_quantized"},
                armor = {ratio = 0.45, valid = true, provenance = "network_quantized"},
                weapon = {
                    selection_index = 1, weapon_id = "g36_crew", name_id = "g36_crew",
                    ammo = {current_clip = 1, reserve = 45, provenance = "network_synced"}
                },
                equipment = {
                    deployable = {id = "ammo_bag", amount = 1, name_id = "ammo_bag"},
                    cable_ties = {amount = 0},
                    projectile = {id = "smoke", amount = 1, kind = "ability", name_id = "smoke"}
                },
                interaction = nil,
                downs = 0, condition_text = "normal"
            }

            inst:update(_g_actor, 0)

            _wt = inst._weapon_text:text()
            _rt_exists = inst._reserve_text ~= nil
            _rt = ""
            if inst._reserve_text then _rt = inst._reserve_text:text() end

            _clip_sz = inst._weapon_text:font_size()
            _res_sz = inst._reserve_text and inst._reserve_text:font_size() or 0

            local wc = inst._weapon_text:color()
            _cr, _cg, _cb = wc.r, wc.g, wc.b
            local rc = inst._reserve_text and inst._reserve_text:color() or {r=0,g=0,b=0}
            _rr, _rg, _rb = rc.r, rc.g, rc.b

            _eq_cy = inst._equipment_text:y() + inst._equipment_text:h() * 0.5
            _ar_cy = inst._ar_bg:y() + inst._ar_bg:h() * 0.5
            _di_cy = inst._deployable_icon:y() + inst._deployable_icon:h() * 0.5
            _ci_cy = inst._cables_icon:y() + inst._cables_icon:h() * 0.5
            _pi_cy = inst._projectile_icon:y() + inst._projectile_icon:h() * 0.5

            _ammo_above_eq = inst._weapon_text:y() < inst._equipment_text:y()

            _ok1 = inst:verify()

            local ref_rt = inst._reserve_text
            if inst._reserve_text then
                inst._reserve_text:set_text("MUTATED")
            end
            _ok2 = inst:verify()

            inst:update(_g_actor, 0)
            _ok3 = inst:verify()
            _rt_repaired = inst._reserve_text and inst._reserve_text:text() or ""
            _same_ref = (inst._reserve_text == ref_rt)
        ''')
        g = lua.globals()

        self.assertEqual(g._wt, "001",
            "weapon_text must be formatted clip '001', not identifier")
        self.assertNotIn("g36_crew", str(g._wt),
            "no raw weapon identifier in weapon_text")

        self.assertTrue(bool(g._rt_exists), "_reserve_text primitive must exist")
        self.assertEqual(g._rt, "/045", "reserve_text must be '/045'")
        self.assertNotIn("g36_crew", str(g._rt),
            "no raw weapon identifier in reserve_text")

        self.assertAlmostEqual(float(g._clip_sz), float(g._res_sz), places=3,
            msg="clip and reserve must share the approved font size")

        self.assertAlmostEqual(float(g._cr), 1.0, places=1)
        self.assertAlmostEqual(float(g._cg), 1.0, places=1)
        self.assertAlmostEqual(float(g._cb), 1.0, places=1)
        self.assertAlmostEqual(float(g._rr), 0.7, places=1)
        self.assertAlmostEqual(float(g._rg), 0.7, places=1)
        self.assertAlmostEqual(float(g._rb), 0.7, places=1)

        self.assertAlmostEqual(float(g._eq_cy), float(g._ar_cy), delta=0.05,
            msg="equipment text vertical center must match armor track center")
        for ic in ("_di_cy", "_ci_cy", "_pi_cy"):
            self.assertAlmostEqual(float(g[ic]), float(g._ar_cy), delta=0.05,
                msg=f"icon {ic} center must match armor track center")
        self.assertTrue(bool(g._ammo_above_eq), "ammo must sit above equipment")

        self.assertTrue(bool(g._ok1), "clean verify must pass")
        self.assertFalse(bool(g._ok2),
            "verify must be false after mutating _reserve_text")
        self.assertTrue(bool(g._ok3),
            "verify must be true after update repairs _reserve_text")
        self.assertEqual(g._rt_repaired, "/045",
            "repaired reserve_text must show '/045'")
        self.assertTrue(bool(g._same_ref),
            "update must repair via same _reserve_text reference")

        fmt_cases = [
            ("_g_clip = 0; _g_reserve = 0", "000", "/000"),
            ("_g_clip = 45; _g_reserve = 195", "045", "/195"),
            ("_g_clip = nil; _g_reserve = nil", "---", "/---"),
            ("_g_clip = 1000; _g_reserve = 1234", "1000", "/1234"),
        ]
        for setup, exp_c, exp_r in fmt_cases:
            lua.execute(setup)
            lua.execute('''
                _g_actor.weapon.ammo.current_clip = _g_clip
                _g_actor.weapon.ammo.reserve = _g_reserve
                inst:update(_g_actor, 0)
                _fc = inst._weapon_text:text()
                _fr = inst._reserve_text and inst._reserve_text:text() or "?"
                _fok = inst:verify()
            ''')
            gf = lua.globals()
            self.assertTrue(bool(gf._fok), f"verify for {setup}")
            self.assertEqual(gf._fc, exp_c, f"clip format {setup}")
            self.assertEqual(gf._fr, exp_r, f"reserve format {setup}")
            self.assertNotIn("g36_crew", str(gf._fc))
            self.assertNotIn("g36_crew", str(gf._fr))

        edge_cases = [
            ("_g_clip = -1; _g_reserve = -5", "---", "/---"),
            ("_g_clip = 0/0; _g_reserve = 0/0", "---", "/---"),
            ("_g_clip = math.huge; _g_reserve = -math.huge", "---", "/---"),
        ]
        for setup, exp_c, exp_r in edge_cases:
            lua.execute(setup)
            lua.execute('''
                _g_actor.weapon.ammo.current_clip = _g_clip
                _g_actor.weapon.ammo.reserve = _g_reserve
                inst:update(_g_actor, 0)
                _fc = inst._weapon_text:text()
                _fr = inst._reserve_text and inst._reserve_text:text() or "?"
                _fok = inst:verify()
            ''')
            gf = lua.globals()
            self.assertTrue(bool(gf._fok), f"verify edge {setup}")
            self.assertEqual(gf._fc, exp_c, f"edge clip {setup}")
            self.assertEqual(gf._fr, exp_r, f"edge reserve {setup}")

        lua.execute('''
            local bot = {
                name = "Dallas", ai = true, character_name = "russian",
                health = nil, armor = nil, weapon = nil, equipment = nil,
                interaction = nil, downs = nil, condition_text = nil
            }
            inst:update(bot, 0)
            _bwp = inst._weapon_text:visible()
            assert(inst._reserve_text ~= nil)
            _brt = inst._reserve_text:visible()
            inst:destroy()
        ''')
        gb = lua.globals()
        self.assertFalse(bool(gb._bwp), "bot must hide weapon_text")
        self.assertFalse(bool(gb._brt), "bot must hide reserve_text")


if __name__ == "__main__":
    unittest.main()
