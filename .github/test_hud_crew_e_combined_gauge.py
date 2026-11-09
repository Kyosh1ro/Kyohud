"""Combined gauge E — crew_card.lua: nested armor+health gauge for humans (desired contract).

Two bounded methods testing nested gauge geometry:
   1. Human color(.7,.2,.4) health=.82 armor=.45 => nameRGB=peer(.7,.2,.4), healthRGB=peer(.7,.2,.4),
      health_text/armor_text invisible, armor=outer(18e), health=inner(14e), inset=2e,
      health contained in _ar_bg (outer track), outerwidth-innerwidth=4e, ratios independent
      (armorfill/outer=.45, healthfill/inner=.82), no separators, no %/numbers, nested rectangles
      not 2 gauges, root 280x120 unchanged.
   2. Matrix e*{.95,1,1.05} x 3 colors, constant ratios .82/.45 (NOT scaled), human->bot->human
      same primitives, each of 9 cases captures nameRGB and healthRGB and compares to expected peer
      color, positive certification, corrupt healthfill geometry then verify false then update true,
      peer color health and name corrupted => false then recover.
   3. Observable phases: PV=.1 armor=1 same peer color, PV=0 armor=0 fills=0, unknown valid=false
      fills=0 + texts invisible, asserts source unchanged.

Desired contract: assertions reflect the desired behavior where human peer color drives both name
and health fill RGB, geometry uses exact inset 2e and height 18e/14e with tolerance .05.
"""
import unittest
from test_hud_crew_card import _lua, CREW_CARD_PATH


class CombinedGaugeHumanNestedTests(unittest.TestCase):
    """Method 1: Human with nested armor+health gauge, desired contract."""

    def test_human_nested_gauge_characterization(self):
        """Human color(.7,.2,.4) health=.82 armor=.45: assert desired peer color contract."""
        lua, ok = _lua()
        self.assertTrue(ok, "lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            local inst = CC.new(parent, "combined_human")
            inst:set_geometry(0, 0, 280, 120)

            local actor = {
                name = "TestHuman", level = 50, rank = 10, ai = false,
                peer_id = 1, character_name = "test",
                color = {r = 0.7, g = 0.2, b = 0.4},
                health = {valid = true, ratio = 0.82, provenance = "network_quantized"},
                armor = {valid = true, ratio = 0.45, provenance = "network_quantized"}
            }
            inst:update(actor, 0)

            -- Name color RGB
            local name_c = inst._name_text:color()
            _name_r = name_c.r
            _name_g = name_c.g
            _name_b = name_c.b

            -- Health fill color RGB
            local health_c = inst._health_fill:color()
            _health_r = health_c.r
            _health_g = health_c.g
            _health_b = health_c.b

            -- Health/armor text invisible
            _health_text_visible = inst._health_text:visible()
            _armor_text_visible = inst._armor_text:visible()

            -- Outer armor track (_ar_bg) geometry
            local ar_bg = inst._ar_bg
            _ar_bg_x = ar_bg:x()
            _ar_bg_y = ar_bg:y()
            _ar_bg_w = ar_bg:w()
            _ar_bg_h = ar_bg:h()

            -- Armor fill geometry
            local ar_fill = inst._armor_fill
            _ar_fill_x = ar_fill:x()
            _ar_fill_y = ar_fill:y()
            _ar_fill_w = ar_fill:w()
            _ar_fill_h = ar_fill:h()

            -- Inner health track (_hp_bg) geometry
            local hp_bg = inst._hp_bg
            _hp_bg_x = hp_bg:x()
            _hp_bg_y = hp_bg:y()
            _hp_bg_w = hp_bg:w()
            _hp_bg_h = hp_bg:h()

            -- Health fill geometry
            local hp_fill = inst._health_fill
            _hp_fill_x = hp_fill:x()
            _hp_fill_y = hp_fill:y()
            _hp_fill_w = hp_fill:w()
            _hp_fill_h = hp_fill:h()

            -- Outer height should be 26e (26 * scale)
            _outer_h = _ar_bg_h

            -- Inner height should be 14e (14 * scale)
            _inner_h = _hp_bg_h

            -- Inset on x: hp_bg.x - ar_bg.x should be 6e
            _inset_x = _hp_bg_x - _ar_bg_x

            -- Inset on y: hp_bg.y - ar_bg.y should be 6e
            _inset_y = _hp_bg_y - _ar_bg_y

            -- Outer width - inner width should be 12e
            _outer_inner_w = _ar_bg_w - _hp_bg_w

            -- Ratios: armorfill/outertrackwidth=.45, healthfill/innertrackwidth=.82
            _armor_ratio = _ar_fill_w / _ar_bg_w
            _health_ratio = _hp_fill_w / _hp_bg_w

            -- Verify health contained in armor TRACK (_ar_bg), not fill
            _health_inside_armor_track = (_hp_bg_x >= _ar_bg_x) and
                (_hp_bg_y >= _ar_bg_y) and
                (_hp_bg_x + _hp_bg_w <= _ar_bg_x + _ar_bg_w) and
                (_hp_bg_y + _hp_bg_h <= _ar_bg_y + _ar_bg_h)

            _verify = inst:verify()
        ''')
        g = lua.globals()

        # Desired contract: name color = peer color (.7, .2, .4)
        self.assertAlmostEqual(float(g._name_r), 0.7, places=1,
            msg="name color .r must be peer .7")
        self.assertAlmostEqual(float(g._name_g), 0.2, places=1,
            msg="name color .g must be peer .2")
        self.assertAlmostEqual(float(g._name_b), 0.4, places=1,
            msg="name color .b must be peer .4")

        # Desired contract: health fill color = peer color (.7, .2, .4)
        self.assertAlmostEqual(float(g._health_r), 0.7, places=1,
            msg="health fill .r must be peer .7")
        self.assertAlmostEqual(float(g._health_g), 0.2, places=1,
            msg="health fill .g must be peer .2")
        self.assertAlmostEqual(float(g._health_b), 0.4, places=1,
            msg="health fill .b must be peer .4")

        # Text invisible
        self.assertFalse(bool(g._health_text_visible),
            "health_text must be invisible (no %/numbers)")
        self.assertFalse(bool(g._armor_text_visible),
            "armor_text must be invisible (no %/numbers)")

        # Nested geometry: health inside armor TRACK
        self.assertTrue(bool(g._health_inside_armor_track),
            "health bg must be inside armor track _ar_bg (nested rectangles)")

        # Outer height 18e, inner height 14e (tolerance .05)
        self.assertAlmostEqual(float(g._outer_h), 18.0, delta=0.05,
            msg="outer armor track height must be 18e (tol .05)")
        self.assertAlmostEqual(float(g._inner_h), 14.0, delta=0.05,
            msg="inner health track height must be 14e (tol .05)")

        # Inset on x and y must be exactly 2e (tolerance .05)
        self.assertAlmostEqual(float(g._inset_x), 2.0, delta=0.05,
            msg="inset x (hp_bg.x - ar_bg.x) must be 2e (tol .05)")
        self.assertAlmostEqual(float(g._inset_y), 2.0, delta=0.05,
            msg="inset y (hp_bg.y - ar_bg.y) must be 2e (tol .05)")

        # Outer width - inner width must be 4e (tolerance .05)
        self.assertAlmostEqual(float(g._outer_inner_w), 4.0, delta=0.05,
            msg="outer width - inner width must be 4e (tol .05)")

        # Ratios independent
        self.assertAlmostEqual(float(g._armor_ratio), 0.45, places=2,
            msg="armor fill ratio must be 0.45")
        self.assertAlmostEqual(float(g._health_ratio), 0.82, places=2,
            msg="health fill ratio must be 0.82")

        # Verify positive
        self.assertTrue(bool(g._verify),
            "Card:verify must be positive")


class CombinedGaugeMatrixAndCorruptionTests(unittest.TestCase):
    """Method 2: Matrix e*{.95,1,1.05} x 3 colors, human->bot->human, corruption+repair, phases."""

    def test_matrix_and_corruption_repair(self):
        """Matrix 3 scales x 3 colors, constant ratios .82/.45, human->bot->human, corrupt+repair, phases."""
        lua, ok = _lua()
        self.assertTrue(ok, "lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            local inst = CC.new(parent, "combined_matrix")
            inst:set_geometry(0, 0, 280, 120)

            local colors = {
                {r = 0.7, g = 0.2, b = 0.4},
                {r = 0.3, g = 0.8, b = 0.5},
                {r = 0.9, g = 0.4, b = 0.1}
            }
            local scales = {0.95, 1.0, 1.05}

            -- Loop over scales x colors (real matrix)
            _matrix_results = {}
            local idx = 1
            for si, scale in ipairs(scales) do
                for ci, color in ipairs(colors) do
                    -- Set geometry with scale
                    local w = 280 * scale
                    local h = 120 * scale
                    inst:set_geometry(0, 0, w, h)

                    -- Human with constant ratios .82/.45 (NOT scaled)
                    local actor = {
                        name = "Human_" .. si .. "_" .. ci,
                        level = 50, rank = 10, ai = false,
                        peer_id = 1, character_name = "test",
                        color = color,
                        health = {valid = true, ratio = 0.82, provenance = "network_quantized"},
                        armor = {valid = true, ratio = 0.45, provenance = "network_quantized"}
                    }
                    inst:update(actor, idx)

                    -- Capture geometry and ratios
                    local ar_bg = inst._ar_bg
                    local ar_fill = inst._armor_fill
                    local hp_bg = inst._hp_bg
                    local hp_fill = inst._health_fill

                    local armor_ratio = ar_fill:w() / ar_bg:w()
                    local health_ratio = hp_fill:w() / hp_bg:w()

                    -- Health inside armor track
                    local health_inside = (hp_bg:x() >= ar_bg:x()) and
                        (hp_bg:y() >= ar_bg:y()) and
                        (hp_bg:x() + hp_bg:w() <= ar_bg:x() + ar_bg:w()) and
                        (hp_bg:y() + hp_bg:h() <= ar_bg:y() + ar_bg:h())

                    -- Text invisible
                    local health_text_inv = not inst._health_text:visible()
                    local armor_text_inv = not inst._armor_text:visible()

                    local verify = inst:verify()

                    -- Capture name and health fill colors
                    local name_c = inst._name_text:color()
                    local health_c = inst._health_fill:color()

                    table.insert(_matrix_results, {
                        scale = scale,
                        color_idx = ci,
                        expected_r = color.r,
                        expected_g = color.g,
                        expected_b = color.b,
                        name_r = name_c.r,
                        name_g = name_c.g,
                        name_b = name_c.b,
                        health_r = health_c.r,
                        health_g = health_c.g,
                        health_b = health_c.b,
                        armor_ratio = armor_ratio,
                        health_ratio = health_ratio,
                        health_inside = health_inside,
                        texts_invisible = health_text_inv and armor_text_inv,
                        verify = verify
                    })

                    idx = idx + 1
                end
            end

            -- Human->bot->human same primitives
            local human1 = {
                name = "Human1", level = 50, rank = 10, ai = false,
                peer_id = 1, character_name = "test",
                color = colors[1],
                health = {valid = true, ratio = 0.82, provenance = "network_quantized"},
                armor = {valid = true, ratio = 0.45, provenance = "network_quantized"}
            }
            inst:update(human1, idx)
            idx = idx + 1

            local ref_hp = inst._health_fill
            local ref_ar = inst._armor_fill
            local ref_name = inst._name_text

            local bot = {
                name = "Dallas", level = nil, rank = nil, ai = true,
                peer_id = nil, character_name = "russian",
                health = nil, armor = nil
            }
            inst:update(bot, idx)
            idx = idx + 1

            local human2 = {
                name = "Human2", level = 60, rank = 15, ai = false,
                peer_id = 2, character_name = "test2",
                color = colors[2],
                health = {valid = true, ratio = 0.82, provenance = "network_quantized"},
                armor = {valid = true, ratio = 0.45, provenance = "network_quantized"}
            }
            inst:update(human2, idx)
            idx = idx + 1

            _same_primitives = (inst._health_fill == ref_hp) and
                (inst._armor_fill == ref_ar) and
                (inst._name_text == ref_name)

            -- Positive certification
            _verify_clean = inst:verify()

            -- Corrupt health fill geometry
            inst._health_fill:set_shape(-1, -1, -1, -1)
            _verify_corrupt = inst:verify()

            -- Repair by update ALONE
            inst:update(human2, idx)
            idx = idx + 1
            _verify_repaired = inst:verify()
            _same_after_repair = (inst._health_fill == ref_hp)

            -- Corrupt name color
            inst._name_text:set_color(Color(0, 0, 0))
            _verify_bad_name_color = inst:verify()

            -- Repair by update ALONE
            inst:update(human2, idx)
            idx = idx + 1
            _verify_name_recovered = inst:verify()

            -- Corrupt health color
            inst._health_fill:set_color(Color(0, 0, 0))
            _verify_bad_health_color = inst:verify()

            -- Repair by update ALONE
            inst:update(human2, idx)
            idx = idx + 1
            _verify_health_recovered = inst:verify()

            -- Observable phases
            -- Phase 1: PV=.1 armor=1 (same peer color)
            local phase1 = {
                name = "Phase1", level = 50, rank = 10, ai = false,
                peer_id = 1, character_name = "test",
                color = colors[1],
                health = {valid = true, ratio = 0.1, provenance = "network_quantized"},
                armor = {valid = true, ratio = 1.0, provenance = "network_quantized"}
            }
            inst:update(phase1, idx)
            idx = idx + 1
            _phase1_verify = inst:verify()
            _phase1_hp_fill_w = inst._health_fill:w()
            _phase1_ar_fill_w = inst._armor_fill:w()
            _phase1_hp_color = inst._health_fill:color()
            _phase1_ar_color = inst._armor_fill:color()
            _phase1_name_color = inst._name_text:color()
            _phase1_expected_r = colors[1].r
            _phase1_expected_g = colors[1].g
            _phase1_expected_b = colors[1].b

            -- Phase 2: PV=0 armor=0 fills=0
            local phase2 = {
                name = "Phase2", level = 50, rank = 10, ai = false,
                peer_id = 1, character_name = "test",
                color = colors[1],
                health = {valid = true, ratio = 0.0, provenance = "network_quantized"},
                armor = {valid = true, ratio = 0.0, provenance = "network_quantized"}
            }
            inst:update(phase2, idx)
            idx = idx + 1
            _phase2_verify = inst:verify()
            _phase2_hp_fill_w = inst._health_fill:w()
            _phase2_ar_fill_w = inst._armor_fill:w()

            -- Phase 3: unknown valid=false fills=0 + texts invisible
            local phase3 = {
                name = "Phase3", level = 50, rank = 10, ai = false,
                peer_id = 1, character_name = "test",
                color = colors[1],
                health = {valid = false, ratio = 0.5, provenance = "network_quantized"},
                armor = {valid = false, ratio = 0.5, provenance = "network_quantized"}
            }
            inst:update(phase3, idx)
            idx = idx + 1
            _phase3_verify = inst:verify()
            _phase3_hp_fill_w = inst._health_fill:w()
            _phase3_ar_fill_w = inst._armor_fill:w()
            _phase3_hp_text_visible = inst._health_text:visible()
            _phase3_ar_text_visible = inst._armor_text:visible()

            -- Assert source unchanged (same primitives)
            _source_unchanged = (inst._health_fill == ref_hp) and
                (inst._armor_fill == ref_ar) and
                (inst._name_text == ref_name)
        ''')
        g = lua.globals()

        # Matrix results
        matrix = g._matrix_results
        self.assertEqual(len(matrix), 9, "matrix must have 9 results (3 scales x 3 colors)")

        for i, result in enumerate(matrix.values()):
            scale = result['scale']
            color_idx = result['color_idx']

            # Name color must match expected peer color
            self.assertAlmostEqual(float(result['name_r']), float(result['expected_r']), places=1,
                msg=f"scale={scale} color={color_idx}: name .r must match peer")
            self.assertAlmostEqual(float(result['name_g']), float(result['expected_g']), places=1,
                msg=f"scale={scale} color={color_idx}: name .g must match peer")
            self.assertAlmostEqual(float(result['name_b']), float(result['expected_b']), places=1,
                msg=f"scale={scale} color={color_idx}: name .b must match peer")

            # Health fill color must match expected peer color
            self.assertAlmostEqual(float(result['health_r']), float(result['expected_r']), places=1,
                msg=f"scale={scale} color={color_idx}: health .r must match peer")
            self.assertAlmostEqual(float(result['health_g']), float(result['expected_g']), places=1,
                msg=f"scale={scale} color={color_idx}: health .g must match peer")
            self.assertAlmostEqual(float(result['health_b']), float(result['expected_b']), places=1,
                msg=f"scale={scale} color={color_idx}: health .b must match peer")

            # Ratios constant .82/.45 (not scaled)
            self.assertAlmostEqual(float(result['armor_ratio']), 0.45, places=2,
                msg=f"scale={scale} color={color_idx}: armor ratio must be .45")
            self.assertAlmostEqual(float(result['health_ratio']), 0.82, places=2,
                msg=f"scale={scale} color={color_idx}: health ratio must be .82")

            # Health inside armor track
            self.assertTrue(bool(result['health_inside']),
                msg=f"scale={scale} color={color_idx}: health must be inside armor track")

            # Texts invisible
            self.assertTrue(bool(result['texts_invisible']),
                msg=f"scale={scale} color={color_idx}: texts must be invisible")

            # Verify positive
            self.assertTrue(bool(result['verify']),
                msg=f"scale={scale} color={color_idx}: verify must be positive")

        # Same primitives reused across human->bot->human
        self.assertTrue(bool(g._same_primitives),
            "same primitives must be reused across human->bot->human transitions")

        # Positive certification
        self.assertTrue(bool(g._verify_clean),
            "verify must be positive after human update")

        # Corruption and repair
        self.assertFalse(bool(g._verify_corrupt),
            "verify must be false after corrupting health fill geometry")
        self.assertTrue(bool(g._verify_repaired),
            "verify must be true after update repairs health fill")
        self.assertTrue(bool(g._same_after_repair),
            "health fill reference must persist after repair")

        # Name color corruption and recovery
        self.assertFalse(bool(g._verify_bad_name_color),
            "verify must be false after corrupting name color")
        self.assertTrue(bool(g._verify_name_recovered),
            "verify must be true after update recovers name color")

        # Health color corruption and recovery
        self.assertFalse(bool(g._verify_bad_health_color),
            "verify must be false after corrupting health color")
        self.assertTrue(bool(g._verify_health_recovered),
            "verify must be true after update recovers health color")

        # Observable phases
        # Phase 1: PV=.1 armor=1 — same peer color
        self.assertTrue(bool(g._phase1_verify),
            "phase1 (PV=.1 armor=1): verify must be positive")
        self.assertGreater(float(g._phase1_hp_fill_w), 0.0,
            "phase1: health fill width must be > 0")
        self.assertGreater(float(g._phase1_ar_fill_w), 0.0,
            "phase1: armor fill width must be > 0")
        # Phase 1 colors must match peer exactly
        self.assertAlmostEqual(float(g._phase1_hp_color.r), float(g._phase1_expected_r), places=1,
            msg="phase1: health fill .r must match peer")
        self.assertAlmostEqual(float(g._phase1_hp_color.g), float(g._phase1_expected_g), places=1,
            msg="phase1: health fill .g must match peer")
        self.assertAlmostEqual(float(g._phase1_hp_color.b), float(g._phase1_expected_b), places=1,
            msg="phase1: health fill .b must match peer")
        self.assertAlmostEqual(float(g._phase1_name_color.r), float(g._phase1_expected_r), places=1,
            msg="phase1: name .r must match peer")
        self.assertAlmostEqual(float(g._phase1_name_color.g), float(g._phase1_expected_g), places=1,
            msg="phase1: name .g must match peer")
        self.assertAlmostEqual(float(g._phase1_name_color.b), float(g._phase1_expected_b), places=1,
            msg="phase1: name .b must match peer")

        # Phase 2: PV=0 armor=0 fills=0
        self.assertTrue(bool(g._phase2_verify),
            "phase2 (PV=0 armor=0): verify must be positive")
        self.assertAlmostEqual(float(g._phase2_hp_fill_w), 0.0, delta=0.1,
            msg="phase2: health fill width must be ~0")
        self.assertAlmostEqual(float(g._phase2_ar_fill_w), 0.0, delta=0.1,
            msg="phase2: armor fill width must be ~0")

        # Phase 3: unknown valid=false fills=0 + texts invisible
        self.assertTrue(bool(g._phase3_verify),
            "phase3 (unknown valid=false): verify must be positive")
        self.assertAlmostEqual(float(g._phase3_hp_fill_w), 0.0, delta=0.1,
            msg="phase3: health fill width must be ~0")
        self.assertAlmostEqual(float(g._phase3_ar_fill_w), 0.0, delta=0.1,
            msg="phase3: armor fill width must be ~0")
        self.assertFalse(bool(g._phase3_hp_text_visible),
            "phase3: health text must be invisible")
        self.assertFalse(bool(g._phase3_ar_text_visible),
            "phase3: armor text must be invisible")

        # Source unchanged
        self.assertTrue(bool(g._source_unchanged),
            "source primitives must remain unchanged across all phases")


if __name__ == "__main__":
    unittest.main()
