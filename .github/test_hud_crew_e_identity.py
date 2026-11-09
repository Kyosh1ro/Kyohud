"""Identity line E — crew_card.lua: name, peer marker, and rank/level text (RED tracer).

Target behavior for identity line E (name zone r0, root 280x120 preserved):
  - Name "Alpha" alone in peer color
  - Persistent peer marker rect (_peer_dot) in peer color
  - Separate rank/level text (_rank_text) as "XXI·100" (rank as roman · level)
  - rank=0 → level alone without fake roman
  - Missing level/rank → no invented value
  - Bot: localized name + IA suffix, no invented level

Name budget measured after marker and rank reservation.
Name and rank measured via select(3/4, p:text_rect()) for ink w/h; ink fits panel;
peer rect verified via geometry/bounds (no text_rect, no font_size);
peer/name/rank bounds disjoint in parent-local coordinates.
Card:verify positive.

Corruption then repair on _peer_dot and _rank_text primitives.

RED: assertions on new fields (_peer_dot, _rank_text) and name behavior
will fail because production crew_card.lua has not been updated yet.
The name "Alpha" alone assertion is placed FIRST to make RED significant.
"""
import unittest
from test_hud_crew_card import _lua, CREW_CARD_PATH


class CrewCardEIdentityNameAlphaTests(unittest.TestCase):
    """First: assert name "Alpha" alone in peer color — significant RED."""

    def test_human_name_alpha_alone_in_peer_color(self):
        """Human actor name Alpha level100 rank21 must show 'Alpha' alone in peer color."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            local inst = CC.new(parent, "e_identity")
            inst:set_geometry(0, 0, 280, 120)

            local actor = {
                name = "Alpha", level = 100, rank = 21, ai = false,
                peer_id = 1, character_name = "test",
                color = {r = 0.2, g = 0.6, b = 1.0},
                health = {valid = true, ratio = 0.8, provenance = "network_quantized"},
                armor = {valid = true, ratio = 0.5, provenance = "network_quantized"}
            }
            inst:update(actor, 0)

            _name_text = inst._name_text:text()
            local _name_color = inst._name_text:color()
            _name_r = _name_color.r
            _name_g = _name_color.g
            _name_b = _name_color.b
        ''')
        g = lua.globals()

        # Name "Alpha" alone, not "Alpha L100 R21"
        self.assertEqual(g._name_text, "Alpha",
            "name must be 'Alpha' alone, without level/rank suffix")

        # Name in peer color
        self.assertAlmostEqual(float(g._name_r), 0.2, places=1,
            msg="name color .r must match actor.color.r (peer color)")
        self.assertAlmostEqual(float(g._name_g), 0.6, places=1,
            msg="name color .g must match actor.color.g (peer color)")
        self.assertAlmostEqual(float(g._name_b), 1.0, places=1,
            msg="name color .b must match actor.color.b (peer color)")


class CrewCardEIdentityPeerMarkerTests(unittest.TestCase):
    """Peer marker rect (_peer_dot) must exist, persist, and show peer color."""

    def test_peer_dot_marker_persistent_and_colored(self):
        """_peer_dot rect in peer color, persistent across updates."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            local inst = CC.new(parent, "e_peer")
            inst:set_geometry(0, 0, 280, 120)

            local actor = {
                name = "Alpha", level = 100, rank = 21, ai = false,
                peer_id = 1, character_name = "test",
                color = {r = 0.2, g = 0.6, b = 1.0},
                health = {valid = true, ratio = 0.8, provenance = "network_quantized"},
                armor = {valid = true, ratio = 0.5, provenance = "network_quantized"}
            }
            inst:update(actor, 0)

            assert(inst._peer_dot ~= nil, "_peer_dot must exist after update")

            _peer_dot_exists = inst._peer_dot ~= nil
            _peer_dot_alive = alive(inst._peer_dot)

            local peer_color = inst._peer_dot:color()
            _peer_r = peer_color.r
            _peer_g = peer_color.g
            _peer_b = peer_color.b

            local ref_peer_dot = inst._peer_dot
            for _ = 1, 10 do
                inst:update(actor, _)
            end
            _same_peer_dot = (inst._peer_dot == ref_peer_dot)
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._peer_dot_exists),
            "_peer_dot rect must exist")
        self.assertTrue(bool(g._peer_dot_alive),
            "_peer_dot must be alive")

        self.assertAlmostEqual(float(g._peer_r), 0.2, places=1,
            msg="_peer_dot color .r must match actor.color.r")
        self.assertAlmostEqual(float(g._peer_g), 0.6, places=1,
            msg="_peer_dot color .g must match actor.color.g")
        self.assertAlmostEqual(float(g._peer_b), 1.0, places=1,
            msg="_peer_dot color .b must match actor.color.b")

        self.assertTrue(bool(g._same_peer_dot),
            "_peer_dot must persist across updates (same reference)")


class CrewCardEIdentityRankLevelTextTests(unittest.TestCase):
    """Rank/level text (_rank_text) as 'XXI·100' format."""

    def test_rank_level_text_roman_format(self):
        """_rank_text shows 'XXI·100' for rank=21 level=100."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            local inst = CC.new(parent, "e_rank")
            inst:set_geometry(0, 0, 280, 120)

            local actor = {
                name = "Alpha", level = 100, rank = 21, ai = false,
                peer_id = 1, character_name = "test",
                health = {valid = true, ratio = 0.8, provenance = "network_quantized"},
                armor = {valid = true, ratio = 0.5, provenance = "network_quantized"}
            }
            inst:update(actor, 0)

            assert(inst._rank_text ~= nil, "_rank_text must exist after update")
            _rank_text_exists = inst._rank_text ~= nil
            _rank_text_value = inst._rank_text:text()
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._rank_text_exists),
            "_rank_text must exist")
        self.assertEqual(g._rank_text_value, "XXI·100",
            "_rank_text must show 'XXI·100' (rank as roman · level)")


class CrewCardEIdentityRankZeroTests(unittest.TestCase):
    """rank=0 -> level alone without fake roman."""

    def test_rank_zero_level_alone(self):
        """rank=0 must show level alone, not '0·50' or fake roman."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            local inst = CC.new(parent, "e_rank0")
            inst:set_geometry(0, 0, 280, 120)

            local actor = {
                name = "Beta", level = 50, rank = 0, ai = false,
                peer_id = 2, character_name = "test",
                health = {valid = true, ratio = 0.9, provenance = "network_quantized"},
                armor = {valid = true, ratio = 0.7, provenance = "network_quantized"}
            }
            inst:update(actor, 0)

            assert(inst._rank_text ~= nil, "_rank_text must exist after update")
            _rank_text = inst._rank_text:text()
        ''')
        g = lua.globals()

        self.assertEqual(g._rank_text, "50",
            "rank=0 must show level alone '50', not '0·50' or fake roman")


class CrewCardEIdentityMissingLevelRankTests(unittest.TestCase):
    """Missing level/rank -> no invented value."""

    def test_missing_level_rank_no_invention(self):
        """Missing level/rank must show empty string, not invented value."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            local inst = CC.new(parent, "e_missing")
            inst:set_geometry(0, 0, 280, 120)

            local actor = {
                name = "Gamma", level = nil, rank = nil, ai = false,
                peer_id = 3, character_name = "test",
                health = {valid = true, ratio = 0.6, provenance = "network_quantized"},
                armor = {valid = true, ratio = 0.4, provenance = "network_quantized"}
            }
            inst:update(actor, 0)

            assert(inst._rank_text ~= nil, "_rank_text must exist after update")
            _rank_text = inst._rank_text:text()
        ''')
        g = lua.globals()

        self.assertEqual(g._rank_text, "",
            "missing level/rank must show empty string, not invented value")


class CrewCardEIdentityBotNoLevelTests(unittest.TestCase):
    """Bot: localized name + IA suffix, no invented level."""

    def test_bot_localized_name_ia_no_level(self):
        """Bot must show localized name + IA suffix, no invented level/rank."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            managers = managers or {}
            managers.localization = managers.localization or {}
            function managers.localization:text(key)
                if key == "menu_russian" then return "Dallas"
                elseif key == "ky_hud_crew_ai" then return "IA"
                else return key end
            end

            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            local inst = CC.new(parent, "e_bot")
            inst:set_geometry(0, 0, 280, 120)

            local actor = {
                name = nil, level = nil, rank = nil, ai = true,
                peer_id = nil, character_name = "russian",
                health = nil, armor = nil
            }
            inst:update(actor, 0)

            assert(inst._rank_text ~= nil, "_rank_text must exist after update")
            _name_text = inst._name_text:text()
            _rank_text = inst._rank_text:text()
        ''')
        g = lua.globals()

        self.assertEqual(g._name_text, "Dallas",
            "bot name must be exactly 'Dallas' without AI suffix")
        self.assertEqual(g._rank_text, "",
            "bot must not have invented level/rank")


class CrewCardEIdentityMeasurementAndVerifyTests(unittest.TestCase):
    """Measured ink (name/rank) via text_rect, peer geometry/bounds, disjoint bounds, verify positive."""

    def test_measured_texts_no_overflow_and_verify_positive(self):
        """Name + rank + peer at rank=100 with long accented name: ink fits, disjoint, verify."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            local inst = CC.new(parent, "e_measure")
            inst:set_geometry(0, 0, 280, 120)

            local actor = {
                name = "Émïlïöñ Àccéntué",
                level = 100, rank = 100, ai = false,
                peer_id = 1, character_name = "test",
                color = {r = 0.2, g = 0.6, b = 1.0},
                health = {valid = true, ratio = 0.8, provenance = "network_quantized"},
                armor = {valid = true, ratio = 0.5, provenance = "network_quantized"}
            }
            inst:update(actor, 0)

            assert(inst._peer_dot ~= nil, "_peer_dot must exist after update")
            assert(inst._rank_text ~= nil, "_rank_text must exist after update")

            _verify = inst:verify()

            local peer = inst._peer_dot
            local name_p = inst._name_text
            local rank_p = inst._rank_text

            local function ink_w(p) return select(3, p:text_rect()) end
            local function ink_h(p) return select(4, p:text_rect()) end

            _peer_x = peer:x()
            _peer_y = peer:y()
            _peer_pw = peer:w()
            _peer_ph = peer:h()
            _peer_pos = (_peer_x >= 0) and (_peer_y >= 0)
            _peer_bounded = (_peer_x + _peer_pw <= 280.5) and (_peer_y + _peer_ph <= 120.5)
            _peer_fits = (_peer_pw > 0) and (_peer_ph > 0) and _peer_pos and _peer_bounded

            _name_ink_w = ink_w(name_p)
            _name_ink_h = ink_h(name_p)
            _name_pw = name_p:w()
            _name_ph = name_p:h()
            _name_fits = (_name_ink_w <= _name_pw) and (_name_ink_h <= _name_ph)

            _rank_ink_w = ink_w(rank_p)
            _rank_ink_h = ink_h(rank_p)
            _rank_pw = rank_p:w()
            _rank_ph = rank_p:h()
            _rank_fits = (_rank_ink_w <= _rank_pw) and (_rank_ink_h <= _rank_ph)

            local function disjoint(a, b)
                local ax, ay, aw, ah = a:x(), a:y(), a:w(), a:h()
                local bx, by, bw, bh = b:x(), b:y(), b:w(), b:h()
                return (ax + aw <= bx) or (bx + bw <= ax)
                    or (ay + ah <= by) or (by + bh <= ay)
            end

            _peer_name_disjoint = disjoint(peer, name_p)
            _peer_rank_disjoint = disjoint(peer, rank_p)
            _name_rank_disjoint = disjoint(name_p, rank_p)

            _total_bounds = _name_ink_w + _rank_ink_w + peer:w()
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._verify),
            "Card:verify must be positive")

        self.assertTrue(bool(g._peer_fits),
            "_peer_dot bounds must be positive and within card (geometry check, no text API)")
        self.assertTrue(bool(g._name_fits),
            "_name_text ink must fit within its panel (ink_w<=w, ink_h<=h)")
        self.assertTrue(bool(g._rank_fits),
            "_rank_text ink must fit within its panel (ink_w<=w, ink_h<=h)")

        self.assertTrue(bool(g._peer_name_disjoint),
            "peer_dot and name_text bounds must be disjoint in parent-local coords")
        self.assertTrue(bool(g._peer_rank_disjoint),
            "peer_dot and rank_text bounds must be disjoint in parent-local coords")
        self.assertTrue(bool(g._name_rank_disjoint),
            "name_text and rank_text bounds must be disjoint in parent-local coords")

        self.assertLessEqual(float(g._total_bounds), 280.0,
            "total bounds (name ink + rank ink + peer rect) must not overflow 280px card width")


class CrewCardEIdentityCorruptionAndRepairTests(unittest.TestCase):
    """Corruption then repair same primitive on _peer_dot and _rank_text."""

    def test_corruption_repair_peer_dot_and_rank_text(self):
        """Corrupt _peer_dot and _rank_text, repair by update ALONE."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            local inst = CC.new(parent, "e_corrupt")
            inst:set_geometry(0, 0, 280, 120)

            local actor = {
                name = "Alpha", level = 100, rank = 21, ai = false,
                peer_id = 1, character_name = "test",
                color = {r = 0.2, g = 0.6, b = 1.0},
                health = {valid = true, ratio = 0.8, provenance = "network_quantized"},
                armor = {valid = true, ratio = 0.5, provenance = "network_quantized"}
            }
            inst:update(actor, 0)

            assert(inst._peer_dot ~= nil, "_peer_dot must exist after update")
            assert(inst._rank_text ~= nil, "_rank_text must exist after update")

            _ok_clean = inst:verify()

            local ref_peer_dot = inst._peer_dot
            local ref_rank_text = inst._rank_text

            -- Corrupt _peer_dot geometry
            inst._peer_dot:set_shape(-1, -1, -1, -1)
            _ok_bad_peer = inst:verify()

            -- Repair by update ALONE
            inst:update(actor, 1)
            _ok_peer_restored = inst:verify()
            _same_peer = (inst._peer_dot == ref_peer_dot)

            -- Corrupt _rank_text
            inst._rank_text:set_text("CORRUPTED")
            _ok_bad_rank = inst:verify()

            -- Repair by update ALONE
            inst:update(actor, 2)
            _ok_rank_restored = inst:verify()
            _same_rank = (inst._rank_text == ref_rank_text)
            _restored_rank = inst._rank_text:text()
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._ok_clean),
            "verify must be true before corruption")
        self.assertFalse(bool(g._ok_bad_peer),
            "verify must be false after corrupting _peer_dot")
        self.assertTrue(bool(g._ok_peer_restored),
            "verify must be true after update repairs _peer_dot")
        self.assertTrue(bool(g._same_peer),
            "_peer_dot reference must persist after repair")
        self.assertFalse(bool(g._ok_bad_rank),
            "verify must be false after corrupting _rank_text")
        self.assertTrue(bool(g._ok_rank_restored),
            "verify must be true after update repairs _rank_text")
        self.assertTrue(bool(g._same_rank),
            "_rank_text reference must persist after repair")
        self.assertEqual(g._restored_rank, "XXI·100",
            "_rank_text must be restored to 'XXI·100'")


if __name__ == "__main__":
    unittest.main()
