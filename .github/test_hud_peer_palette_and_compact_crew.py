"""Peer palette & compact crew -- gauge.lua + crew_card.lua (RED tracer).

Three compact regression tests against real Lua chunks via lupa.luajit21.

Test 1: Local peer color flows into gauge health fill and health number.
  Desired contract: gauge.render() accepts an optional 5th arg peer_color;
  when valid, health segment fills and health_text use that color instead of
  the constant INK_HEALTH green.  Fallback to INK_HEALTH when peer_color is
  nil or invalid.  Client peer 3 red must NOT render as constant green.
  RED: gauge.lua currently ignores any peer_color argument and always uses
  INK_HEALTH = Color(159/255, 208/255, 94/255) for segment fills and text.

Test 2: Compact crew geometry + bot fixed-blue transition.
  Desired human contract: armor outer height 18e (currently 26e), health inner
  14e (unchanged), inset 2e (currently 6e), no percentage text, fixed peer HP
  color preserved.  Desired bot contract: fixed blue RGB(0.35, 0.70, 0.95)
  for health fill and name only, bar track width = 30% of existing human
  health-track width, fill = ratio * short track, no armor contour or other
  information.
  RED: crew_card.lua currently renders outer_h=26e, inset=6e, bot uses
  actor.color instead of fixed blue, bot bar width is near-full-card.

Test 3: Player-runtime integration with real actors:get_local_peer_color().
  Mounts real player panel through test_hud_player harness, sets up
  managers.network:session():local_peer():id()=3, tweak_data.chat_colors[3]
  as native Color userdata via newproxy.  Asserts gauge fill+number use actual
  peer color (red).  Changes peer id/color then ordinary update.  Missing
  session fallback green.  Certification and stable primitives.  Tests real
  added method actors:get_local_peer_color(), NOT substituted fixture.
"""
import unittest

from test_hud_gauge import _lua as gauge_lua
from test_hud_crew_card import _lua as crew_lua
from test_hud_player import _lua as player_lua


class LocalPeerPaletteTests(unittest.TestCase):
    """Gauge health fill and text must reflect actual local peer color."""

    def test_peer_color_overrides_constant_green(self):
        """RED: segment fills and health_text use peer_color when provided."""
        lua, ok = gauge_lua()
        self.assertTrue(ok, "gauge.lua must exist")
        if not ok:
            return
        lua.execute('''
            local inst = kyohud.hud.gauge.new(panel_double, "peer_pal")
            inst:set_geometry(0, 0, 440, 42)

            local hp = {current=80, total=100, ratio=0.8, valid=true, provenance="local"}
            local ar = {current=3, total=6, ratio=0.5, valid=true, provenance="local"}

            -- Peer 3 red (typical chat_colors[3] in PAYDAY 2).
            local peer_red = {r = 0.88, g = 0.24, b = 0.24}

            -- Desired contract: pass peer_color as 5th arg to render().
            inst:render(hp, ar, "percentage", 10, peer_red)

            -- Capture segment[1] fill color (health, first band).
            local seg1_fill_c = inst.health_segments[1].fill:color()
            _s1_r = seg1_fill_c.r
            _s1_g = seg1_fill_c.g
            _s1_b = seg1_fill_c.b

            -- Capture health_text color.
            local txt_c = inst.health_text:color()
            _ht_r = txt_c.r
            _ht_g = txt_c.g
            _ht_b = txt_c.b

            -- Fallback: nil peer_color must still render INK_HEALTH green.
            inst:render(hp, ar, "percentage", 10)
            local seg1_fb = inst.health_segments[1].fill:color()
            _fb_r = seg1_fb.r
            _fb_g = seg1_fb.g
            _fb_b = seg1_fb.b

            -- Corruption: set segment fill to black, render again with peer
            -- color => must repair to peer color, verify true.
            inst.health_segments[1].fill:set_color(Color(0, 0, 0))
            _corrupt = inst:verify()
            inst:render(hp, ar, "percentage", 10, peer_red)
            _repaired = inst:verify()
            local rep_c = inst.health_segments[1].fill:color()
            _rep_r = rep_c.r
            _rep_g = rep_c.g
            _rep_b = rep_c.b

            _same_ref = inst.health_segments[1].fill
        ''')
        g = lua.globals()

        # INK_HEALTH = Color(159/255, 208/255, 94/255) ~= (0.624, 0.816, 0.369)
        INK_R, INK_G, INK_B = 159 / 255, 208 / 255, 94 / 255

        # Peer color must be used for segment fill (NOT constant green).
        self.assertAlmostEqual(float(g._s1_r), 0.88, delta=0.02,
            msg="segment[1] fill .r must match peer_red .r=0.88")
        self.assertAlmostEqual(float(g._s1_g), 0.24, delta=0.02,
            msg="segment[1] fill .g must match peer_red .g=0.24")
        self.assertAlmostEqual(float(g._s1_b), 0.24, delta=0.02,
            msg="segment[1] fill .b must match peer_red .b=0.24")

        # Health text must also reflect peer color.
        self.assertAlmostEqual(float(g._ht_r), 0.88, delta=0.02,
            msg="health_text .r must match peer_red .r=0.88")
        self.assertAlmostEqual(float(g._ht_g), 0.24, delta=0.02,
            msg="health_text .g must match peer_red .g=0.24")
        self.assertAlmostEqual(float(g._ht_b), 0.24, delta=0.02,
            msg="health_text .b must match peer_red .b=0.24")

        # Fallback: nil peer_color => INK_HEALTH green preserved.
        self.assertAlmostEqual(float(g._fb_r), INK_R, delta=0.02,
            msg="fallback: nil peer_color must use INK_HEALTH .r")
        self.assertAlmostEqual(float(g._fb_g), INK_G, delta=0.02,
            msg="fallback: nil peer_color must use INK_HEALTH .g")
        self.assertAlmostEqual(float(g._fb_b), INK_B, delta=0.02,
            msg="fallback: nil peer_color must use INK_HEALTH .b")

        # Corruption + repair.
        self.assertFalse(bool(g._corrupt),
            "verify must be false after black corruption of segment fill")
        self.assertTrue(bool(g._repaired),
            "verify must be true after render with peer_color repairs fill")
        self.assertAlmostEqual(float(g._rep_r), 0.88, delta=0.02,
            msg="repaired segment fill .r must match peer_red")
        self.assertAlmostEqual(float(g._rep_g), 0.24, delta=0.02,
            msg="repaired segment fill .g must match peer_red")
        self.assertAlmostEqual(float(g._rep_b), 0.24, delta=0.02,
            msg="repaired segment fill .b must match peer_red")


class CompactCrewGeometryAndBotTransitionTests(unittest.TestCase):
    """Crew card: compact human gauge + bot fixed-blue minimal contract."""

    def test_human_compact_gauge_and_bot_fixed_blue(self):
        """RED: outer 18e inset 2e, bot fixed blue RGB(.35,.70,.95) 30% track."""
        lua, ok = crew_lua()
        self.assertTrue(ok, "crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            managers = managers or {}
            managers.localization = managers.localization or {}
            function managers.localization:text(key)
                if key == "menu_russian" then return "Dallas"
                elseif key == "menu_american" then return "Hoxton"
                else return "Loc:" .. tostring(key) end
            end

            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            local inst = CC.new(parent, "compact")
            inst:set_geometry(0, 0, 280, 120)

            ----------------------------------------------------------------
            -- Phase 1: Human with known health/armor, peer color (.7,.2,.4)
            ----------------------------------------------------------------
            local human = {
                name = "Tester", level = 50, rank = 10, ai = false,
                peer_id = 1, character_name = "test",
                color = {r = 0.7, g = 0.2, b = 0.4},
                health = {valid = true, ratio = 0.82, provenance = "network_quantized"},
                armor = {valid = true, ratio = 0.45, provenance = "network_quantized"}
            }
            inst:update(human, 0)

            local ar_bg = inst._ar_bg
            local hp_bg = inst._hp_bg

            -- Outer armor track height (desired 18e, currently 26e).
            _outer_h = ar_bg:h()
            -- Inner health track height (desired 14e, unchanged).
            _inner_h = hp_bg:h()
            -- Inset: hp_bg.x - ar_bg.x (desired 2e, currently 6e).
            _inset_x = hp_bg:x() - ar_bg:x()
            -- Inset y: hp_bg.y - ar_bg.y (desired 2e, currently 6e).
            _inset_y = hp_bg:y() - ar_bg:y()

            -- Human health-track width for bot comparison.
            _human_hp_track_w = hp_bg:w()

            -- Health text invisible (no %/numbers).
            _hp_text_vis = inst._health_text:visible()
            _ar_text_vis = inst._armor_text:visible()

            -- Health fill color = peer color.
            local hf_c = inst._health_fill:color()
            _hf_r = hf_c.r; _hf_g = hf_c.g; _hf_b = hf_c.b

            _v1 = inst:verify()

            -- Remember human references.
            local ref_hf = inst._health_fill
            local ref_ar = inst._ar_bg
            local ref_nt = inst._name_text

            ----------------------------------------------------------------
            -- Phase 2: Bot transition
            ----------------------------------------------------------------
            local bot = {
                name = nil, level = nil, rank = nil, ai = true,
                peer_id = nil, character_name = "russian",
                color = {r = 0.1, g = 0.7, b = 0.9},
                health = {valid = true, ratio = 0.42, provenance = "bot_host"},
                armor = nil, weapon = nil, equipment = nil, interaction = nil,
                downs = 0, condition_text = nil, condition_icon = nil
            }
            inst:update(bot, 1)

            -- Bot health fill color: desired fixed blue RGB(.35,.70,.95).
            local bf_c = inst._health_fill:color()
            _bf_r = bf_c.r; _bf_g = bf_c.g; _bf_b = bf_c.b

            -- Bot name color: desired same fixed blue.
            local bn_c = inst._name_text:color()
            _bn_r = bn_c.r; _bn_g = bn_c.g; _bn_b = bn_c.b

            -- Bot health bar track width: desired 30% of human health-track.
            _bot_bar_w = inst._hp_bg:w()
            _bot_ratio_track = _bot_bar_w / _human_hp_track_w

            -- Bot fill = ratio * short track.
            _bot_fill_w = inst._health_fill:w()
            _bot_fill_ratio = _bot_fill_w / _bot_bar_w

            -- Bot: no armor contour.
            _bot_ar_bg_vis = inst._ar_bg:visible()
            _bot_ar_fill_vis = inst._armor_fill:visible()

            -- Bot: name text.
            _bot_name = inst._name_text:text()

            -- Bot: everything else hidden.
            _bot_wp_vis = inst._weapon_text:visible()
            _bot_eq_vis = inst._equipment_text:visible()
            _bot_cb_vis = inst._cables_text:visible()
            _bot_pj_vis = inst._projectile_text:visible()
            _bot_int_vis = inst._interaction_text:visible()
            _bot_st_vis = inst._status_text:visible()
            _bot_peer_dot_vis = inst._peer_dot:visible()
            _bot_rank_vis = inst._rank_text:visible()
            _bot_hp_text_vis = inst._health_text:visible()

            _v2 = inst:verify()

            ----------------------------------------------------------------
            -- Phase 3: Corruption + repair (same primitives)
            ----------------------------------------------------------------
            inst._health_fill:set_color(Color(0, 0, 0))
            _corrupt = inst:verify()
            inst:update(bot, 2)
            _repaired = inst:verify()
            _same_hf = (inst._health_fill == ref_hf)
            _same_ar = (inst._ar_bg == ref_ar)
            _same_nt = (inst._name_text == ref_nt)
        ''')
        g = lua.globals()

        FIXED_BLUE_R, FIXED_BLUE_G, FIXED_BLUE_B = 0.35, 0.70, 0.95

        # Human compact gauge geometry.
        self.assertAlmostEqual(float(g._outer_h), 18.0, delta=0.05,
            msg="outer armor track height must be 18e (currently 26e)")
        self.assertAlmostEqual(float(g._inner_h), 14.0, delta=0.05,
            msg="inner health track height must be 14e")
        self.assertAlmostEqual(float(g._inset_x), 2.0, delta=0.05,
            msg="inset x must be 2e (currently 6e)")
        self.assertAlmostEqual(float(g._inset_y), 2.0, delta=0.05,
            msg="inset y must be 2e (currently 6e)")

        # No percentage text.
        self.assertFalse(bool(g._hp_text_vis),
            "health_text must be invisible (no % for humans)")
        self.assertFalse(bool(g._ar_text_vis),
            "armor_text must be invisible (no % for humans)")

        # Health fill color = peer color.
        self.assertAlmostEqual(float(g._hf_r), 0.7, delta=0.02,
            msg="human health fill .r must match peer .r=0.7")
        self.assertAlmostEqual(float(g._hf_g), 0.2, delta=0.02,
            msg="human health fill .g must match peer .g=0.2")
        self.assertAlmostEqual(float(g._hf_b), 0.4, delta=0.02,
            msg="human health fill .b must match peer .b=0.4")

        self.assertTrue(bool(g._v1),
            "verify must be true for human compact gauge")

        # Bot: fixed blue health fill (NOT actor.color).
        self.assertAlmostEqual(float(g._bf_r), FIXED_BLUE_R, delta=0.02,
            msg="bot health fill .r must be fixed blue 0.35")
        self.assertAlmostEqual(float(g._bf_g), FIXED_BLUE_G, delta=0.02,
            msg="bot health fill .g must be fixed blue 0.70")
        self.assertAlmostEqual(float(g._bf_b), FIXED_BLUE_B, delta=0.02,
            msg="bot health fill .b must be fixed blue 0.95")

        # Bot: name same fixed blue (NOT white).
        self.assertAlmostEqual(float(g._bn_r), FIXED_BLUE_R, delta=0.02,
            msg="bot name .r must be fixed blue 0.35")
        self.assertAlmostEqual(float(g._bn_g), FIXED_BLUE_G, delta=0.02,
            msg="bot name .g must be fixed blue 0.70")
        self.assertAlmostEqual(float(g._bn_b), FIXED_BLUE_B, delta=0.02,
            msg="bot name .b must be fixed blue 0.95")

        # Bot: bar track width = 30% of human health-track width.
        self.assertAlmostEqual(float(g._bot_ratio_track), 0.30, delta=0.02,
            msg="bot bar track width must be 30% of human health-track width")

        # Bot: fill = ratio * short track.
        self.assertAlmostEqual(float(g._bot_fill_ratio), 0.42, places=2,
            msg="bot fill width / bot track width must be ~0.42")

        # Bot: no armor contour.
        self.assertFalse(bool(g._bot_ar_bg_vis),
            "bot: _ar_bg must be invisible (no armor contour)")
        self.assertFalse(bool(g._bot_ar_fill_vis),
            "bot: _armor_fill must be invisible (no armor contour)")

        # Bot: localized name.
        self.assertEqual(g._bot_name, "Dallas",
            "bot name must be localized 'Dallas'")

        # Bot: everything else hidden.
        for attr, label in [
            ("_bot_wp_vis", "weapon"), ("_bot_eq_vis", "equipment"),
            ("_bot_cb_vis", "cables"), ("_bot_pj_vis", "projectile"),
            ("_bot_int_vis", "interaction"), ("_bot_st_vis", "status"),
            ("_bot_peer_dot_vis", "peer_dot"), ("_bot_rank_vis", "rank"),
            ("_bot_hp_text_vis", "health_text"),
        ]:
            self.assertFalse(bool(g[attr]),
                f"bot: {label} must be invisible")

        self.assertTrue(bool(g._v2),
            "verify must be true for bot fixed-blue presentation")

        # Corruption + repair, same primitives.
        self.assertFalse(bool(g._corrupt),
            "verify must be false after black corruption of bot health fill")
        self.assertTrue(bool(g._repaired),
            "verify must be true after update repairs bot health fill")
        self.assertTrue(bool(g._same_hf),
            "health_fill primitive identity preserved")
        self.assertTrue(bool(g._same_ar),
            "ar_bg primitive identity preserved")
        self.assertTrue(bool(g._same_nt),
            "name_text primitive identity preserved")


class PlayerRuntimePeerPaletteIntegrationTests(unittest.TestCase):
    """Player-runtime integration: real actors:get_local_peer_color() via session/peer."""

    def test_player_runtime_real_peer_color_integration(self):
        """Mount real player, peer_id=3, chat_colors[3] via newproxy Color. Assert gauge
        fill+number red. Change peer id/color, ordinary update. Missing session fallback green.
        Certification and stable primitives. Test real added method, not fixture substitute."""
        setup = '''
            local damage = {
                _health = 80, _health_max = 100, _armor = 30, _armor_max = 50, _revives = 1,
                get_real_health = function(self) return self._health end,
                _max_health = function(self) return self._health_max end,
                get_real_armor = function(self) return self._armor end,
                _max_armor = function(self) return self._armor_max end,
                get_revives = function(self) return self._revives end,
            }
            local unit = {
                _alive = true,
                character_damage = function(self) return damage end,
            }
            managers.player = managers.player or {}
            managers.player.player_unit = function(self) return unit end

            local mgr = managers.hud
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = {_peer_id = nil, _ai = false}
            local parent = _G.panel_double
            mgr._safe_script = {panel = parent}

            -- Mock session with local_peer():id() = 3
            managers.network = managers.network or {}
            local mock_peer = {}
            function mock_peer:id() return 3 end
            local mock_session = {}
            function mock_session:local_peer() return mock_peer end
            function managers.network:session() return mock_session end

            -- tweak_data.chat_colors[3] as native Color userdata via newproxy
            tweak_data = tweak_data or {}
            tweak_data.chat_colors = tweak_data.chat_colors or {}
            local peer3_color = newproxy(true)
            local mt = getmetatable(peer3_color)
            mt.__index = function(self, key)
                if key == "r" then return 0.88 end
                if key == "g" then return 0.24 end
                if key == "b" then return 0.24 end
                if key == "a" then return 1 end
                return nil
            end
            mt.__tostring = function(self) return "Color(0.88, 0.24, 0.24)" end
            tweak_data.chat_colors[3] = peer3_color
        '''
        lua, ok = player_lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/player.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            kyohud.settings.player_value_mode = 1
            local mgr = _G.managers.hud
            kyohud.hud.runtime:refresh_settings(mgr)

            local P = kyohud.hud.player
            local ACT = kyohud.hud.actors
            ACT:refresh(mgr)

            -- Test real added method actors:get_local_peer_color()
            _real_peer_color = ACT:get_local_peer_color()
            _has_real_method = (type(ACT.get_local_peer_color) == "function")

            -- Render with real peer color
            local snap = ACT:get_actor(HUDManager.PLAYER_PANEL)
            local mult = tweak_data.gui.stats_present_multiplier
            P:render(snap, mult)

            -- Capture gauge fill and number color
            local gauge = P._gauge
            _gauge_fill_c = gauge.health_segments[1].fill:color()
            _gauge_fill_r = _gauge_fill_c.r
            _gauge_fill_g = _gauge_fill_c.g
            _gauge_fill_b = _gauge_fill_c.b
            _gauge_text_c = gauge.health_text:color()
            _gauge_text_r = _gauge_text_c.r
            _gauge_text_g = _gauge_text_c.g
            _gauge_text_b = _gauge_text_c.b

            _verify1 = P:verify()

            -- Remember primitives
            local ref_root = P._root
            local ref_gauge = P._gauge
            local ref_fill = gauge.health_segments[1].fill
            local ref_text = gauge.health_text

            -- Change peer id to 4 with different color
            local peer4_color = newproxy(true)
            local mt4 = getmetatable(peer4_color)
            mt4.__index = function(self, key)
                if key == "r" then return 0.24 end
                if key == "g" then return 0.88 end
                if key == "b" then return 0.24 end
                if key == "a" then return 1 end
                return nil
            end
            tweak_data.chat_colors[4] = peer4_color

            -- Change local_peer id to 4
            managers.network.session = function(self)
                return {
                    local_peer = function() return {id = function() return 4 end} end
                }
            end

            -- Ordinary update
            P:update(mgr, 1.0, 0.1)

            -- Capture new colors
            local gauge2 = P._gauge
            _gauge2_fill_c = gauge2.health_segments[1].fill:color()
            _gauge2_fill_r = _gauge2_fill_c.r
            _gauge2_fill_g = _gauge2_fill_c.g
            _gauge2_fill_b = _gauge2_fill_c.b

            _verify2 = P:verify()

            -- Same primitives
            _same_root = (P._root == ref_root)
            _same_gauge = (P._gauge == ref_gauge)
            _same_fill = (P._gauge.health_segments[1].fill == ref_fill)
            _same_text = (P._gauge.health_text == ref_text)

            -- Missing session fallback: remove session
            managers.network.session = function(self) return nil end
            P:update(mgr, 2.0, 0.1)

            -- Fallback should be INK_HEALTH green
            local INK_R, INK_G, INK_B = 159/255, 208/255, 94/255
            local gauge3 = P._gauge
            _gauge3_fill_c = gauge3.health_segments[1].fill:color()
            _fallback_r = _gauge3_fill_c.r
            _fallback_g = _gauge3_fill_c.g
            _fallback_b = _gauge3_fill_c.b

            _verify3 = P:verify()
        ''')
        g = lua.globals()

        # Real method exists
        self.assertTrue(bool(g._has_real_method),
            "actors:get_local_peer_color() must exist as real method")

        # Real peer color retrieved
        self.assertIsNotNone(g._real_peer_color,
            "get_local_peer_color() must return actual color from session/peer/tweak_data")

        # Gauge fill and text use peer color (red)
        self.assertAlmostEqual(float(g._gauge_fill_r), 0.88, delta=0.02,
            msg="gauge fill .r must match peer3 .r=0.88")
        self.assertAlmostEqual(float(g._gauge_fill_g), 0.24, delta=0.02,
            msg="gauge fill .g must match peer3 .g=0.24")
        self.assertAlmostEqual(float(g._gauge_fill_b), 0.24, delta=0.02,
            msg="gauge fill .b must match peer3 .b=0.24")
        self.assertAlmostEqual(float(g._gauge_text_r), 0.88, delta=0.02,
            msg="gauge text .r must match peer3 .r=0.88")
        self.assertAlmostEqual(float(g._gauge_text_g), 0.24, delta=0.02,
            msg="gauge text .g must match peer3 .g=0.24")
        self.assertAlmostEqual(float(g._gauge_text_b), 0.24, delta=0.02,
            msg="gauge text .b must match peer3 .b=0.24")

        self.assertTrue(bool(g._verify1),
            "verify must be true after first render with peer color")

        # After peer change, colors updated
        self.assertAlmostEqual(float(g._gauge2_fill_r), 0.24, delta=0.02,
            msg="after peer change, gauge fill .r must match peer4 .r=0.24")
        self.assertAlmostEqual(float(g._gauge2_fill_g), 0.88, delta=0.02,
            msg="after peer change, gauge fill .g must match peer4 .g=0.88")
        self.assertAlmostEqual(float(g._gauge2_fill_b), 0.24, delta=0.02,
            msg="after peer change, gauge fill .b must match peer4 .b=0.24")

        self.assertTrue(bool(g._verify2),
            "verify must be true after peer change update")

        # Primitives stable
        self.assertTrue(bool(g._same_root), "root primitive identity preserved")
        self.assertTrue(bool(g._same_gauge), "gauge primitive identity preserved")
        self.assertTrue(bool(g._same_fill), "health_fill primitive identity preserved")
        self.assertTrue(bool(g._same_text), "health_text primitive identity preserved")

        # Missing session fallback green
        INK_R, INK_G, INK_B = 159/255, 208/255, 94/255
        self.assertAlmostEqual(float(g._fallback_r), INK_R, delta=0.02,
            msg="missing session fallback must use INK_HEALTH .r")
        self.assertAlmostEqual(float(g._fallback_g), INK_G, delta=0.02,
            msg="missing session fallback must use INK_HEALTH .g")
        self.assertAlmostEqual(float(g._fallback_b), INK_B, delta=0.02,
            msg="missing session fallback must use INK_HEALTH .b")

        self.assertTrue(bool(g._verify3),
            "verify must be true after fallback")


if __name__ == "__main__":
    unittest.main()
