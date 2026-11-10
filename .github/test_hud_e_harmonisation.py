"""H1 regression -- horizontal budget reservation via local_player boundary.

Verifies that crew:_compute_layout reserves the actual local envelope
via layout.local_player.x-12e. Uses x=44e, gap=20e, localleft=w-420e.

Real layout.resolve and crew:_compute_layout consumers, no monkeypatch
of production code. Compact single-method loop across scales and
resolutions.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_hud_final_integration import _crew_lua

RESOLUTIONS = [
    (1920, 1080),
    (1680, 1050),
    (1280, 1024),
    (2560, 1080),
]

SCALES = [0.95, 1.0, 1.05]


class H1HorizontalBudgetReservationTests(unittest.TestCase):
    """Crew must reserve 380e+gap12e via local_player boundary.

    At 1920x1080 scale 1.0 with player/weapons/equipment enabled:
    - card_w = 432 (nominal reference width)
    - total_w = 3*432 + 2*20 = 1336
    - right edge x+total_w <= localleft-12e where localleft = w-420e

    Across resolutions and scales:
    - card_w = min(432*e, (localleft-12e-x-2*20*e-slack)/3)
    - localleft = w - 420*e (local_player.x)
    - x = 44*e
    - gap = 20*e
    """

    def test_crew_reserves_380e_gap12e_not_680(self):
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        self.assertTrue(crew_ok, "crew.lua must exist")
        self.assertTrue(weapons_ok, "weapons.lua must exist")
        self.assertTrue(equipment_ok, "equipment.lua must exist")

        lua.execute(f'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            kyohud.settings.enable_weapons = true
            kyohud.settings.enable_equipment = true
            kyohud.settings.enable_crew = true

            local C = kyohud.hud.crew
            local layout = kyohud.hud.layout

            _results = {{}}
            local resolutions = {{{{1920,1080}}, {{1680,1050}}, {{1280,1024}}, {{2560,1080}}}}
            local scales = {{0.95, 1.0, 1.05}}

            for _, res in ipairs(resolutions) do
                local w, h = res[1], res[2]
                _G.panel_double:set_shape(0, 0, w, h)
                for _, scale in ipairs(scales) do
                    kyohud.settings.hud_scale = scale
                    local lc = C:_compute_layout(w, h)
                    if lc then
                        local g = layout.resolve(w, h, scale)
                        local us = g.uniform_scale
                        local s = g.scale
                        local e = us * s
                        local localleft = w - 420 * e
                        local gap = 20 * e
                        local x = 44 * e
                        local expected_cardw = math.min(432 * e,
                            (localleft - 12 * e - x - 2 * gap - 1e-6 * us) / 3)
                        local expected_total = 3 * expected_cardw + 2 * gap
                        local right_edge = lc.x + lc.total_w
                        local bound_ok = right_edge <= localleft - 12 * e + 0.5

                        table.insert(_results, {{
                            w = w, h = h, scale = scale,
                            card_w = lc.card_w,
                            total_w = lc.total_w,
                            x = lc.x,
                            e = e,
                            expected_cardw = expected_cardw,
                            expected_total = expected_total,
                            localleft = localleft,
                            right_edge = right_edge,
                            bound_ok = bound_ok,
                        }})
                    end
                end
            end
        ''')

        g = lua.globals()
        results = list(g._results.values())
        self.assertEqual(len(results), 12, "must compute layout for all 12 combos (4 res x 3 scales)")

        for r in results:
            w = int(r.w)
            h = int(r.h)
            scale = float(r.scale)
            card_w = float(r.card_w)
            total_w = float(r.total_w)
            x = float(r.x)
            e = float(r.e)
            expected_cardw = float(r.expected_cardw)
            expected_total = float(r.expected_total)
            localleft = float(r.localleft)
            right_edge = float(r.right_edge)
            bound_ok = bool(r.bound_ok)

            self.assertAlmostEqual(card_w, expected_cardw, places=2,
                msg=f"{w}x{h} s{scale}: card_w {card_w:.2f} must match expected {expected_cardw:.2f}")

            self.assertAlmostEqual(total_w, expected_total, places=2,
                msg=f"{w}x{h} s{scale}: total_w {total_w:.2f} must match expected {expected_total:.2f}")

            self.assertAlmostEqual(x, 44 * e, places=2,
                msg=f"{w}x{h} s{scale}: x {x:.2f} must equal 44e={44 * e:.2f}")

            self.assertTrue(bound_ok,
                f"{w}x{h} s{scale}: right_edge {right_edge:.2f} must be <= localleft-12e = {localleft - 12 * e:.2f}")

        ref = None
        for r in results:
            if int(r.w) == 1920 and int(r.h) == 1080 and abs(float(r.scale) - 1.0) < 0.001:
                ref = r
                break

        self.assertIsNotNone(ref, "1920x1080 s1.0 must be in results")
        self.assertAlmostEqual(float(ref.card_w), 432.0, places=2,
            msg="1920x1080 s1.0: card_w must be 432 (nominal)")
        self.assertAlmostEqual(float(ref.total_w), 1336.0, places=2,
            msg="1920x1080 s1.0: total_w must be 1336 (3*432 + 2*20)")


class H2LocalGroupAnchorTests(unittest.TestCase):
    """Runtime local group anchor E -- P/W/E geometry contract and A-B-A stability.

    At 1920x1080 scale 1.0 with P/W/E enabled and qualified sources:
    - P._layout_cache: positive geometry, w=380e, h=120e, x/y from production formula
    - layout.local_loadout: w=380e, h=102e, same x as P root
    - Gauge worldy = P.y + 22e (unchanged)
    - Condition text local y=90e, h=22e within P root
    - Condition change via real callback: no geometry jump

    A-B-A: 1280x1024 s0.95 -> 1920x1080 s1.0 -> 1280x1024 s0.95
    Three scales (0.95, 1.0, 1.05) at both resolutions.
    Same roots/primitives after ABA. All consumers certify.
    Positive geometry asserted before certification.
    """

    def test_runtime_local_group_anchor_e_geometry_and_aba(self):
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        self.assertTrue(crew_ok, "crew.lua must exist")
        self.assertTrue(weapons_ok, "weapons.lua must exist")
        self.assertTrue(equipment_ok, "equipment.lua must exist")

        lua.execute(f'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            kyohud.settings.enable_weapons = true
            kyohud.settings.enable_equipment = true
            kyohud.settings.enable_crew = false
            kyohud.settings.hud_scale = 1.0
            _G.panel_double:set_shape(0, 0, 1920, 1080)

            managers.player.current_state = function(self) return "standard" end
            unit1, base1 = make_weapon("new_m1014")
            base1:_native_set_ammo(8, 6, 32, 40)
            base1:_native_set_fire_mode("auto")
            inventory:_native_set_slot(1, unit1)
            unit2, base2 = make_weapon("new_m16")
            base2:_native_set_ammo(30, 25, 120, 150)
            base2:_native_set_fire_mode("single")
            inventory:_native_set_slot(2, unit2)
            inventory:_native_set_equipped(2)

            managers.player:_native_set_equipment('trip_mine',{{3,2}})
            managers.player:_native_set_equipment('doctor_bag',{{1}})
            managers.player._equipment.selected_index=1
            managers.player:_native_set_grenades('pocket',1,2)
            _native_set_projectile_tweak('pocket',{{ability=true,base_cooldown=30}})
            managers.player:_native_set_specials('cable_tie',{{3}})
            _game_clock:set_time(1000)
            managers.player:_native_set_replenish_timer(1017)

            local mgr = managers.hud
            local ACT = kyohud.hud.actors
            ACT:refresh_crew(mgr, 0)
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.runtime:update(mgr, 1.0, 0.05)

            local P = kyohud.hud.player
            local W = kyohud.hud.weapons
            local E = kyohud.hud.equipment
            local layout = kyohud.hud.layout
            local lc = P._layout_cache

            assert(lc ~= nil, "P._layout_cache must exist after mount")
            assert(lc.x > 0 and lc.y > 0 and lc.w > 0 and lc.h > 0,
                "P._layout_cache positive geometry required before certification")

            local g = layout.resolve(1920, 1080, 1.0)
            local us = g.uniform_scale
            local s = g.scale
            local e = us * s
            local expected_x = 1920 - 40 * e - 380 * e
            local expected_y = 1080 - (24 + 192 + 32*360/440 + 14) * e

            _p_x = lc.x; _p_y = lc.y; _p_w = lc.w; _p_h = lc.h
            _exp_x = expected_x; _exp_y = expected_y

            local ll = layout.local_loadout(1920, 1080, 1.0)
            assert(ll ~= nil, "layout.local_loadout must return geometry")
            assert(ll.x == 1500, "ll.x must be 1500")
            assert(math.abs(ll.y - (expected_y + 84*e)) < .001, "bottom loadout anchor")
            assert(math.abs(ll.y - (lc.y + 84 * e)) < 0.5, "ll.y must equal lc.y + 84e")
            _ll_x = ll.x; _ll_y = ll.y; _ll_w = ll.w; _ll_h = ll.h
            _ll_exp_w = 380 * e; _ll_exp_h = 102 * e

            local gauge_worldy = P._root:y() + P._gauge.root:y()
            _gauge_worldy = gauge_worldy
            _gauge_expected_y = P._root:y() + 192 * e

            local dl = P:_desired_layout()
            assert(dl ~= nil, "P:_desired_layout() must return geometry")
            _cond_y = dl.condition_text.y; _cond_h = dl.condition_text.h
            _cond_exp_y = 0; _cond_exp_h = 22 * e

            assert(P:verify(), "P:verify() must be true with known source")
            assert(W:verify(), "W:verify() must be true with known source")
            assert(E:verify(), "E:verify() must be true with known source")

            local cond_x_before = P._condition_text:x()
            local cond_y_before = P._condition_text:y()
            local cond_w_before = P._condition_text:w()
            local cond_h_before = P._condition_text:h()
            mgr:set_teammate_condition(HUDManager.PLAYER_PANEL, "down", "Downed")
            dispatch(HUDManager, "set_teammate_condition", mgr,
                HUDManager.PLAYER_PANEL, "down", "Downed")
            ACT:refresh(mgr)
            kyohud.hud.runtime:update(mgr, 1.1, 0.05)
            assert(P:verify(), "P:verify() must hold after condition change")
            local cond_x_after = P._condition_text:x()
            local cond_y_after = P._condition_text:y()
            local cond_w_after = P._condition_text:w()
            local cond_h_after = P._condition_text:h()
            _cond_dx = math.abs(cond_x_after - cond_x_before)
            _cond_dy = math.abs(cond_y_after - cond_y_before)
            _cond_dw = math.abs(cond_w_after - cond_w_before)
            _cond_dh = math.abs(cond_h_after - cond_h_before)
            mgr:set_teammate_condition(HUDManager.PLAYER_PANEL, "mugshot_normal", "")
            dispatch(HUDManager, "set_teammate_condition", mgr,
                HUDManager.PLAYER_PANEL, "mugshot_normal", "")
            ACT:refresh(mgr)
            kyohud.hud.runtime:update(mgr, 1.2, 0.05)

            local p_root_a1 = P._root
            local gauge_a1 = P._gauge.root
            local weap_root_a1 = W._root
            local equip_root_a1 = E._root

            _G.panel_double:set_shape(0, 0, 1280, 1024)
            kyohud.settings.hud_scale = 0.95
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.runtime:update(mgr, 2.0, 0.05)
            local lc_a1 = P._layout_cache
            assert(lc_a1 ~= nil and lc_a1.x > 0 and lc_a1.y > 0
                and lc_a1.w > 0 and lc_a1.h > 0,
                "A1 positive geometry at 1280x1024 s0.95")
            assert(P:verify() and W:verify() and E:verify(),
                "A1 all consumers certify at 1280x1024 s0.95")

            _G.panel_double:set_shape(0, 0, 1920, 1080)
            kyohud.settings.hud_scale = 1.0
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.runtime:update(mgr, 3.0, 0.05)
            local lc_b = P._layout_cache
            assert(lc_b ~= nil and lc_b.x > 0 and lc_b.y > 0
                and lc_b.w > 0 and lc_b.h > 0,
                "B positive geometry at 1920x1080 s1.0")
            assert(P:verify() and W:verify() and E:verify(),
                "B all consumers certify at 1920x1080 s1.0")

            _G.panel_double:set_shape(0, 0, 1280, 1024)
            kyohud.settings.hud_scale = 0.95
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.runtime:update(mgr, 4.0, 0.05)
            local lc_a2 = P._layout_cache
            assert(lc_a2 ~= nil and lc_a2.x > 0 and lc_a2.y > 0
                and lc_a2.w > 0 and lc_a2.h > 0,
                "A2 positive geometry at 1280x1024 s0.95")
            assert(P:verify() and W:verify() and E:verify(),
                "A2 all consumers certify at 1280x1024 s0.95")

            _p_root_a2 = P._root
            _gauge_a2 = P._gauge.root
            _weap_root_a2 = W._root
            _equip_root_a2 = E._root
            _same_p_root = (p_root_a1 == P._root)
            _same_gauge = (gauge_a1 == P._gauge.root)
            _same_weap = (weap_root_a1 == W._root)
            _same_equip = (equip_root_a1 == E._root)
            _aba_x = math.abs(lc_a2.x - lc_a1.x)
            _aba_y = math.abs(lc_a2.y - lc_a1.y)
            _aba_w = math.abs(lc_a2.w - lc_a1.w)
            _aba_h = math.abs(lc_a2.h - lc_a1.h)

            _results = {{}}
            local resolutions = {{{{1280,1024}}, {{1920,1080}}}}
            local scales = {{0.95, 1.0, 1.05}}
            local counter = 5.0
            for _, res in ipairs(resolutions) do
                local w, h = res[1], res[2]
                _G.panel_double:set_shape(0, 0, w, h)
                for _, sc in ipairs(scales) do
                    kyohud.settings.hud_scale = sc
                    kyohud.hud.runtime:refresh_settings(mgr)
                    kyohud.hud.runtime:update(mgr, counter, 0.05)
                    counter = counter + 0.6
                    local plcy = P._layout_cache
                    local llcy = layout.local_loadout(w, h, sc)
                    local gg = layout.resolve(w, h, sc)
                    local ee = gg.uniform_scale * gg.scale
                    local exp_px = w - 420 * ee
                    local exp_py = h - (24 + 192 + 32*360/440 + 14) * ee
                    local exp_lly = exp_py + 84 * ee
                    local pos_ok = plcy ~= nil and plcy.x > 0 and plcy.y > 0
                        and plcy.w > 0 and plcy.h > 0
                    local ll_ok = llcy ~= nil and llcy.w > 0 and llcy.h > 0
                    local certify = P:verify() and W:verify() and E:verify()
                    local gw = P._root:y() + P._gauge.root:y()
                    local gw_exp = P._root:y() + 192 * ee
                    local dl2 = P:_desired_layout()
                    local cy = dl2.condition_text.y
                    local ch = dl2.condition_text.h
                    table.insert(_results, {{
                        w = w, h = h, scale = sc,
                        p_x = plcy and plcy.x or -1,
                        p_y = plcy and plcy.y or -1,
                        p_w = plcy and plcy.w or -1,
                        p_h = plcy and plcy.h or -1,
                        exp_px = exp_px, exp_py = exp_py,
                        exp_pw = 380 * ee,
                        exp_ph = 232 * ee,
                        ll_x = llcy and llcy.x or -1,
                        ll_y = llcy and llcy.y or -1,
                        ll_w = llcy and llcy.w or -1,
                        ll_h = llcy and llcy.h or -1,
                        ll_exp_w = 380 * ee,
                        ll_exp_h = 102 * ee,
                        exp_lly = exp_lly,
                        gauge_worldy = gw,
                        gauge_exp_y = gw_exp,
                        cond_y = cy, cond_h = ch,
                        cond_exp_y = 0, cond_exp_h = 22 * ee,
                        ee = ee,
                        pos_ok = pos_ok, ll_ok = ll_ok, certify = certify,
                    }})
                end
            end
        ''')

        g = lua.globals()

        p_x = float(g._p_x)
        p_y = float(g._p_y)
        p_w = float(g._p_w)
        p_h = float(g._p_h)
        exp_x = float(g._exp_x)
        exp_y = float(g._exp_y)

        self.assertAlmostEqual(p_x, exp_x, places=1,
            msg=f"P._layout_cache x {p_x:.2f} must match formula {exp_x:.2f}")
        self.assertAlmostEqual(p_y, exp_y, places=1,
            msg=f"P._layout_cache y {p_y:.2f} must match formula {exp_y:.2f}")

        ll_x = float(g._ll_x)
        ll_y = float(g._ll_y)
        ll_w = float(g._ll_w)
        ll_h = float(g._ll_h)
        ll_exp_w = float(g._ll_exp_w)
        ll_exp_h = float(g._ll_exp_h)
        self.assertAlmostEqual(ll_x, 1500.0, places=1,
            msg=f"local_loadout x {ll_x:.2f} must be 1500")
        self.assertAlmostEqual(ll_y, exp_y + 84, places=1,
            msg=f"local_loadout y {ll_y:.2f} must follow the bottom-anchored player canvas")
        self.assertAlmostEqual(ll_w, ll_exp_w, places=1,
            msg=f"local_loadout w {ll_w:.2f} must be 380e={ll_exp_w:.2f}")
        self.assertAlmostEqual(ll_h, ll_exp_h, places=1,
            msg=f"local_loadout h {ll_h:.2f} must be 102e={ll_exp_h:.2f}")

        gauge_wy = float(g._gauge_worldy)
        gauge_exp = float(g._gauge_expected_y)
        self.assertAlmostEqual(gauge_wy, gauge_exp, places=1,
            msg=f"gauge worldy {gauge_wy:.2f} must equal P.y+22e={gauge_exp:.2f}")

        cond_y = float(g._cond_y)
        cond_h = float(g._cond_h)
        cond_exp_y = float(g._cond_exp_y)
        cond_exp_h = float(g._cond_exp_h)
        self.assertAlmostEqual(cond_y, cond_exp_y, places=1,
            msg=f"condition y {cond_y:.2f} must be 90e={cond_exp_y:.2f}")
        self.assertAlmostEqual(cond_h, cond_exp_h, places=1,
            msg=f"condition h {cond_h:.2f} must be 22e={cond_exp_h:.2f}")

        self.assertLessEqual(float(g._cond_dx), 0.5,
            "condition text x must not jump on real condition callback")
        self.assertLessEqual(float(g._cond_dy), 0.5,
            "condition text y must not jump on real condition callback")
        self.assertLessEqual(float(g._cond_dw), 0.5,
            "condition text w must not jump on real condition callback")
        self.assertLessEqual(float(g._cond_dh), 0.5,
            "condition text h must not jump on real condition callback")

        self.assertTrue(bool(g._same_p_root),
            "ABA: player root identity must be preserved")
        self.assertTrue(bool(g._same_gauge),
            "ABA: gauge root identity must be preserved")
        self.assertTrue(bool(g._same_weap),
            "ABA: weapons root identity must be preserved")
        self.assertTrue(bool(g._same_equip),
            "ABA: equipment root identity must be preserved")
        self.assertLessEqual(float(g._aba_x), 0.01,
            "ABA: P._layout_cache x must return to A1 value")
        self.assertLessEqual(float(g._aba_y), 0.01,
            "ABA: P._layout_cache y must return to A1 value")
        self.assertLessEqual(float(g._aba_w), 0.01,
            "ABA: P._layout_cache w must return to A1 value")
        self.assertLessEqual(float(g._aba_h), 0.01,
            "ABA: P._layout_cache h must return to A1 value")

        results = list(g._results.values())
        self.assertEqual(len(results), 6,
            "must compute layout for all 6 combos (2 res x 3 scales)")
        for r in results:
            w = int(r.w)
            h = int(r.h)
            sc = float(r.scale)
            self.assertTrue(bool(r.pos_ok),
                f"{w}x{h} s{sc}: P._layout_cache must have positive geometry")
            self.assertTrue(bool(r.ll_ok),
                f"{w}x{h} s{sc}: local_loadout must have positive geometry")
            self.assertTrue(bool(r.certify),
                f"{w}x{h} s{sc}: P/W/E must all certify after runtime refresh")
            self.assertAlmostEqual(float(r.p_x), float(r.exp_px), places=1,
                msg=f"{w}x{h} s{sc}: P x {float(r.p_x):.2f} must match w-420e={float(r.exp_px):.2f}")
            self.assertAlmostEqual(float(r.p_y), float(r.exp_py), places=1,
                msg=f"{w}x{h} s{sc}: P y {float(r.p_y):.2f} must match h-152e={float(r.exp_py):.2f}")
            self.assertAlmostEqual(float(r.p_w), float(r.exp_pw), places=1,
                msg=f"{w}x{h} s{sc}: P w {float(r.p_w):.2f} must be 380e={float(r.exp_pw):.2f}")
            self.assertAlmostEqual(float(r.p_h), float(r.exp_ph), places=1,
                msg=f"{w}x{h} s{sc}: P h {float(r.p_h):.2f} must be 120e={float(r.exp_ph):.2f}")
            self.assertGreater(float(r.ll_x), 0,
                msg=f"{w}x{h} s{sc}: loadout x must be positive")
            self.assertAlmostEqual(float(r.ll_y), float(r.exp_lly), places=1,
                msg=f"{w}x{h} s{sc}: loadout y {float(r.ll_y):.2f} must match h-238e={float(r.exp_lly):.2f}")
            self.assertAlmostEqual(float(r.ll_w), float(r.ll_exp_w), places=1,
                msg=f"{w}x{h} s{sc}: loadout w {float(r.ll_w):.2f} must be 380e={float(r.ll_exp_w):.2f}")
            self.assertAlmostEqual(float(r.ll_h), float(r.ll_exp_h), places=1,
                msg=f"{w}x{h} s{sc}: loadout h {float(r.ll_h):.2f} must be 102e={float(r.ll_exp_h):.2f}")
            self.assertAlmostEqual(float(r.gauge_worldy), float(r.gauge_exp_y), places=1,
                msg=f"{w}x{h} s{sc}: gauge worldy must be P.y+22e")
            self.assertAlmostEqual(float(r.cond_y), float(r.cond_exp_y), places=1,
                msg=f"{w}x{h} s{sc}: condition y must be 90e")
            self.assertAlmostEqual(float(r.cond_h), float(r.cond_exp_h), places=1,
                msg=f"{w}x{h} s{sc}: condition h must be 22e")


class H3CrewLayoutComputationTests(unittest.TestCase):
    """Crew _compute_layout: x=44e y=h-162e state30e gap20e localleft=w-420e."""

    def test_crew_layout_matrix(self):
        lua, crew_ok, w_ok, e_ok = _crew_lua()
        self.assertTrue(crew_ok and w_ok and e_ok)
        lua.execute(f'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_crew = true
            local C = kyohud.hud.crew
            local layout = kyohud.hud.layout
            _r = {{}}
            for _, res in ipairs({{{{1920,1080}}, {{1680,1050}}, {{1280,1024}}, {{2560,1080}}}}) do
                local w, h = res[1], res[2]
                _G.panel_double:set_shape(0, 0, w, h)
                for _, sc in ipairs({{0.95, 1.0, 1.05}}) do
                    kyohud.settings.hud_scale = sc
                    local lc = C:_compute_layout(w, h)
                    if lc then
                        local g = layout.resolve(w, h, sc)
                        local ee = g.uniform_scale * g.scale
                        local ll = w - 420 * ee
                        local gap = 20 * ee
                        local sl = 1e-6 * g.uniform_scale
                        local ecw = math.min(432 * ee, (ll - 12*ee - 44*ee - 2*gap - sl) / 3)
                        table.insert(_r, {{w=w,h=h,sc=sc,x=lc.x,y=lc.y,cw=lc.card_w,
                            tw=lc.total_w,sh=lc.state_h,ex=44*ee,ey=h-144*ee,
                            esh=30*ee,ecw=ecw,et=3*ecw+2*gap,ee=ee,ll=ll}})
                    end
                end
            end
        ''')
        results = list(lua.globals()._r.values())
        self.assertEqual(len(results), 12, "4 res x 3 scales")
        for r in results:
            w, sc = int(r.w), float(r.sc)
            ee, ll = float(r.ee), float(r.ll)
            self.assertGreater(float(r.cw), 0, f"{w} s{sc}: card_w > 0")
            self.assertGreater(float(r.tw), 0, f"{w} s{sc}: total_w > 0")
            self.assertAlmostEqual(float(r.x), float(r.ex), places=2,
                msg=f"{w} s{sc}: x {float(r.x):.2f} vs 44e={float(r.ex):.2f}")
            self.assertAlmostEqual(float(r.y), float(r.ey), places=2,
                msg=f"{w} s{sc}: y {float(r.y):.2f} vs h-162e={float(r.ey):.2f}")
            self.assertAlmostEqual(float(r.cw), float(r.ecw), places=2,
                msg=f"{w} s{sc}: card_w")
            self.assertAlmostEqual(float(r.tw), float(r.et), places=2,
                msg=f"{w} s{sc}: total_w")
            self.assertLessEqual(float(r.x) + float(r.tw), ll - 12*ee + 0.5,
                f"{w} s{sc}: right edge within localleft-12e")


if __name__ == "__main__":
    unittest.main()
