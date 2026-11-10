"""Crew Card horizontal layout test (RED tracer).

Tests horizontal card layout: armor gauge LEFT, weapon text RIGHT.
"""
import unittest
from test_hud_crew_card import _lua
from test_hud_crew import _lua as crew_lua


class CrewCardHorizontalLayoutTests(unittest.TestCase):
    def test_horizontal_armor_left_weapon_right(self):
        """Horizontal card: armor gauge LEFT, weapon text RIGHT.

        Card 340x120, human Alpha color .7,.2,.4, rank 10, level 50,
        health valid .82, armor valid .45, weapon Rifle ammo 10/50, equipment nil.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return

        lua.execute('''
            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            assert(CC and CC.new, "RED: kyohud.hud.crew_card.new must exist")

            _G.inst = CC.new(parent, "hz")
            assert(_G.inst, "card must be created")
            _G.inst:set_geometry(0, 0, 340, 120)

            _G.actor = {
                name = "Alpha",
                level = 50,
                rank = 10,
                ai = false,
                peer_id = 1,
                character_name = "spanish",
                color = {r = 0.7, g = 0.2, b = 0.4},
                health = {
                    current = 82,
                    total = 100,
                    ratio = 0.82,
                    valid = true,
                    provenance = "network_quantized"
                },
                armor = {
                    current = 45,
                    total = 100,
                    ratio = 0.45,
                    valid = true,
                    provenance = "network_quantized"
                },
                weapon = {
                    selection_index = 1,
                    weapon_id = "Rifle",
                    name_id = "Rifle",
                    ammo = {
                        max_clip = 30,
                        current_clip = 10,
                        total_raw = 50,
                        reserve = 50,
                        max = 120,
                        provenance = "network_synced"
                    }
                },
                equipment = nil,
                interaction = nil,
                downs = 0,
                condition_text = "normal",
                condition_icon = nil,
                condition_phase = nil
            }

            _G.update_ok = _G.inst:update(_G.actor, 1)
            _G.verify_ok = _G.inst:verify()

            local ar_bg = _G.inst._ar_bg
            local weapon_text = _G.inst._weapon_text
            local name_text = _G.inst._name_text
            local rank_text = _G.inst._rank_text
            local equipment_text = _G.inst._equipment_text
            local cables_text = _G.inst._cables_text
            local projectile_text = _G.inst._projectile_text

            _G.ar_bg_right = ar_bg:x() + ar_bg:w()
            _G.weapon_x = weapon_text:x()
            _G.name_right = name_text:x() + name_text:w()
            _G.rank_right = rank_text:x() + rank_text:w()
            _G.eq_x = equipment_text:x()
            _G.cb_x = cables_text:x()
            _G.pj_x = projectile_text:x()
            _G.eq_y = equipment_text:y()
            _G.weapon_y = weapon_text:y()

            _G.ref_name = _G.inst._name_text
            _G.ref_hf = _G.inst._health_fill
            _G.ref_ht = _G.inst._health_text
            _G.ref_af = _G.inst._armor_fill
            _G.ref_at = _G.inst._armor_text
            _G.ref_wt = _G.inst._weapon_text
            _G.ref_et = _G.inst._equipment_text
            _G.ref_ct = _G.inst._cables_text
            _G.ref_pt = _G.inst._projectile_text
            _G.ref_it = _G.inst._interaction_text
            _G.ref_st = _G.inst._status_text
        ''')

        g = lua.globals()

        self.assertLess(float(g.ar_bg_right), float(g.weapon_x),
            "armor background right edge must be < weapon_text:x() (LEFT gauge vs RIGHT weapon)")

        self.assertLessEqual(float(g.name_right), float(g.weapon_x),
            "name right edge must be <= weapon x")
        self.assertLessEqual(float(g.rank_right), float(g.weapon_x),
            "rank right edge must be <= weapon x")

        self.assertGreaterEqual(float(g.eq_x), float(g.weapon_x),
            "equipment text x must be >= weapon x")
        self.assertGreaterEqual(float(g.cb_x), float(g.weapon_x),
            "cables text x must be >= weapon x")
        self.assertGreaterEqual(float(g.pj_x), float(g.weapon_x),
            "projectile text x must be >= weapon x")

        self.assertGreater(float(g.eq_y), float(g.weapon_y),
            "equipment y must be > weapon y")

        self.assertTrue(bool(g.update_ok),
            "update must return true")
        self.assertTrue(bool(g.verify_ok),
            "verify must return true")

        lua.execute('''
            local weapon_text = _G.inst._weapon_text
            weapon_text:set_shape(999, weapon_text:y(), weapon_text:w(), weapon_text:h())
            _G.verify_after_corrupt = _G.inst:verify()
        ''')

        g = lua.globals()
        self.assertFalse(bool(g.verify_after_corrupt),
            "verify must be false after corrupting weapon x")

        lua.execute('''
            _G.update_ok2 = _G.inst:update(_G.actor, 2)
            _G.verify_ok2 = _G.inst:verify()

            _G.same_name = (_G.inst._name_text == _G.ref_name)
            _G.same_hf = (_G.inst._health_fill == _G.ref_hf)
            _G.same_ht = (_G.inst._health_text == _G.ref_ht)
            _G.same_af = (_G.inst._armor_fill == _G.ref_af)
            _G.same_at = (_G.inst._armor_text == _G.ref_at)
            _G.same_wt = (_G.inst._weapon_text == _G.ref_wt)
            _G.same_et = (_G.inst._equipment_text == _G.ref_et)
            _G.same_cb = (_G.inst._cables_text == _G.ref_ct)
            _G.same_pt = (_G.inst._projectile_text == _G.ref_pt)
            _G.same_it = (_G.inst._interaction_text == _G.ref_it)
            _G.same_st = (_G.inst._status_text == _G.ref_st)
        ''')

        g = lua.globals()
        self.assertTrue(bool(g.update_ok2),
            "update must return true after repair")
        self.assertTrue(bool(g.verify_ok2),
            "verify must return true after repair")

        self.assertTrue(bool(g.same_wt),
            "update must reuse same weapon_text primitive")
        self.assertTrue(bool(g.same_name),
            "update must reuse same name_text primitive")
        self.assertTrue(bool(g.same_hf),
            "update must reuse same health_fill primitive")
        self.assertTrue(bool(g.same_ht),
            "update must reuse same health_text primitive")
        self.assertTrue(bool(g.same_af),
            "update must reuse same armor_fill primitive")
        self.assertTrue(bool(g.same_at),
            "update must reuse same armor_text primitive")
        self.assertTrue(bool(g.same_et),
            "update must reuse same equipment_text primitive")
        self.assertTrue(bool(g.same_cb),
            "update must reuse same cables_text primitive")
        self.assertTrue(bool(g.same_pt),
            "update must reuse same projectile_text primitive")
        self.assertTrue(bool(g.same_it),
            "update must reuse same interaction_text primitive")
        self.assertTrue(bool(g.same_st),
            "update must reuse same status_text primitive")


class CrewOwnerLayoutTests(unittest.TestCase):
    def test_pure_owner_layout_across_sizes_and_scales(self):
        """Pure-owner layout: _compute_layout with correct receiver across 12 combos.
        Expected from actual layout.resolve: eff=us*s, x=44e,
        rightboundary=local_player.x-12e, gap=20e,
        expected_card_w=min(432e,(rightboundary-x-2*gap-slack)/3).
        Assert card width exact, gap exact, x+total<=boundary, card_h=120e,
        y=h-162e.
        """
        lua, ok = crew_lua()
        self.assertTrue(ok, "RED: lua/hud/crew.lua must exist")
        if not ok:
            return
        lua.execute(r'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_crew = true

            local C = kyohud.hud.crew
            local layout = kyohud.hud.layout

            _results = {}
            local sizes = {{1920, 1080}, {1280, 1024}, {958, 748}, {1600, 900}}
            local scales = {0.95, 1.0, 1.05}
            for _, size in ipairs(sizes) do
                for _, scale in ipairs(scales) do
                    kyohud.settings.hud_scale = scale
                    local w, h = size[1], size[2]
                    _G.panel_double:set_shape(0, 0, w, h)

                    local geom = layout.resolve(w, h, scale)
                    local us = geom.uniform_scale
                    local s = geom.scale
                    local eff = us * s
                    local margin_x = geom.margin_x

                    local lp = layout.local_player(w, h, scale)
                    local rightboundary = lp and (lp.x - 12 * eff) or 0
                    local gap_expected = 20 * eff
                    local x_expected = 44 * eff
                    local card_w_expected = math.min(432 * eff, (rightboundary - x_expected - 2 * gap_expected - 1e-6 * us) / 3)
                    local card_h_expected = 120 * eff
                    local y_expected = h - 144 * eff

                    local actual = C:_compute_layout(w, h)

                    table.insert(_results, {
                        w = w, h = h, scale = scale,
                        eff = eff, margin_x = margin_x,
                        rightboundary = rightboundary,
                        gap_expected = gap_expected,
                        x_expected = x_expected,
                        card_w_expected = card_w_expected,
                        card_h_expected = card_h_expected,
                        y_expected = y_expected,
                        actual_card_w = actual and actual.card_w or -1,
                        actual_card_h = actual and actual.card_h or -1,
                        actual_gap = actual and actual.gap or -1,
                        actual_x = actual and actual.x or -1,
                        actual_y = actual and actual.y or -1,
                        actual_total_w = actual and actual.total_w or -1,
                        actual_nil = actual == nil,
                    })
                end
            end
        ''')
        g = lua.globals()
        results = list(g._results.values())
        self.assertEqual(len(results), 12, "all twelve size/scale combos must produce results")

        for i, r in enumerate(results):
            self.assertFalse(bool(r.actual_nil),
                f"combo {i}: _compute_layout must not return nil")
            self.assertAlmostEqual(float(r.actual_gap), float(r.gap_expected), places=3,
                msg=f"RED: gap expected {float(r.gap_expected):.3f}, got {float(r.actual_gap):.3f}")
            self.assertAlmostEqual(float(r.actual_card_w), float(r.card_w_expected), places=3,
                msg=f"card_w mismatch combo {i}: expected {float(r.card_w_expected):.3f}, got {float(r.actual_card_w):.3f}")
            self.assertLessEqual(float(r.actual_x) + float(r.actual_total_w), float(r.rightboundary) + 0.5,
                msg=f"x+total exceeds boundary combo {i}")
            self.assertAlmostEqual(float(r.actual_card_h), float(r.card_h_expected), places=3,
                msg=f"card_h mismatch combo {i}")
            self.assertAlmostEqual(float(r.actual_y), float(r.y_expected), places=3,
                msg=f"y mismatch combo {i}")


if __name__ == "__main__":
    unittest.main()
