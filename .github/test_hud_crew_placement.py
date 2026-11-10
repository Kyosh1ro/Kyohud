"""Crew placement geometry contract -- cap at parent_h*0.5-margin_x.

These tests define the desired contract for crew-only geometry:
- Keep current x, width, card sizes, gaps and equipment budget
- Cap crew bottom at parent_h*0.5-margin_x (above vertical midpoint)
- y=min(old bottom-reserve-derived y, parent_h*.5-margin_x-card_h)
- No dynamic obstacle-driven reposition
- Existing fail-closed overlap guard unchanged

Three combat rectangles at logged geometries:
1. Tactical banner: 522,482.5,236,36 (from frame 520,480.5,240,40 with inset2)
2. Medal: 520,527.5,240,33 (from frame 520,526.5,240,35)
3. Buff element: 556.4,527,38,27

Tests must fail meaningfully on current source before production fix.
"""
import unittest
from test_hud_crew_acceptance import mounted


class CrewPlacementGeometryContractTests(unittest.TestCase):
    """Crew must cap at parent_h*0.5-margin_x and avoid combat rectangles."""

    def test_resize_and_combat_rectangles_crew_bottom_capped(self):
        """Resize to 1280x720 at scale 1.0033333333 with three combat rectangles.

        OLD crew formula intersects each rectangle (precondition).
        NEW crew bottom <= parent_h*0.5-margin_x (contract).
        Root visible and certified on real runtime update.
        Obstacle coordinates unchanged.
        """
        lua = mounted()
        lua.execute(r'''
            panel_double:set_shape(0, 0, 1280, 720)
            kyohud.settings.hud_scale = 1.0033333333
            RT:_do_refresh(managers.hud)
            C:refresh_settings(managers.hud)
            RT:update(managers.hud, 1.1, 0.05)

            _rt_root_w = C._parent_panel and C._parent_panel:w() or -1
            _rt_root_h = C._parent_panel and C._parent_panel:h() or -1

            local parent = C._parent_panel
            local combat = parent:child("kyohud_buff_panel")
            if not combat then
                combat = panel_double:panel({name="kyohud_buff_panel"})
                combat:set_shape(0, 0, 1280, 720)
            end
            combat:set_visible(true)
            kyohud._panel = combat

            local rect1 = combat:rect({name="tactical_banner", x=522, y=482.5, w=236, h=36, visible=true})
            local rect2 = combat:rect({name="medal_panel", x=520, y=527.5, w=240, h=33, visible=true})
            local rect3 = combat:rect({name="buff_element", x=556.4, y=527, w=38, h=27, visible=true})

            local geom = kyohud.hud.layout.resolve(1280, 720, 1.0033333333)
            local margin_x = geom.margin_x or 0
            local us = geom.uniform_scale or 1
            local scale = geom.scale or 1

            local old_x = margin_x
            local old_y = 720 - margin_x - 200 * us - 120 * us * scale
            local old_w = 3 * 280 * us * scale + 24 * us
            local old_h = 120 * us * scale

            _old_x = old_x
            _old_y = old_y
            _old_w = old_w
            _old_h = old_h

            local function old_intersects(rx, ry, rw, rh)
                return (old_x < rx + rw) and (old_x + old_w > rx)
                    and (old_y < ry + rh) and (old_y + old_h > ry)
            end

            _old_intersect1 = old_intersects(522, 482.5, 236, 36)
            _old_intersect2 = old_intersects(520, 527.5, 240, 33)
            _old_intersect3 = old_intersects(556.4, 527, 38, 27)

            local lc = C._layout_cache
            local crew_x, crew_y = lc.x, lc.y
            local crew_w, crew_h = lc.total_w, lc.card_h
            local crew_bottom = crew_y + crew_h

            local function new_intersects(rx, ry, rw, rh)
                return (crew_x < rx + rw) and (crew_x + crew_w > rx)
                    and (crew_y < ry + rh) and (crew_y + crew_h > ry)
            end

            _new_intersect1 = new_intersects(522, 482.5, 236, 36)
            _new_intersect2 = new_intersects(520, 527.5, 240, 33)
            _new_intersect3 = new_intersects(556.4, 527, 38, 27)

            local e = us * scale
            local expected_crew_y = 720 - 144 * e
            _crew_y_formula = math.abs(crew_y - expected_crew_y) < 0.5

            RT:update(managers.hud, 1.5, 0.05)
            _root_visible = C._root:visible()
            _certified = C:_verify_render()

            _rect1_x = rect1:x()
            _rect1_y = rect1:y()
            _rect1_w = rect1:w()
            _rect1_h = rect1:h()
            _rect2_x = rect2:x()
            _rect2_y = rect2:y()
            _rect2_w = rect2:w()
            _rect2_h = rect2:h()
            _rect3_x = rect3:x()
            _rect3_y = rect3:y()
            _rect3_w = rect3:w()
            _rect3_h = rect3:h()
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._old_x), 25.6, places=1,
            msg="OLD crew x must be margin_x=25.6")
        self.assertAlmostEqual(float(g._old_y), 480.8, places=1,
            msg="OLD crew y must be 720-margin_x-200*us-120*us*scale~480.8")
        self.assertAlmostEqual(float(g._old_w), 577.9, places=1,
            msg="OLD crew w must be 3*280*us*scale+24*us~577.9")
        self.assertAlmostEqual(float(g._old_h), 80.3, places=1,
            msg="OLD crew h must be 120*us*scale~80.3")
        self.assertIs(g._old_intersect1, True,
            "OLD crew formula must intersect tactical banner at 522,482.5,236,36")
        self.assertIs(g._old_intersect2, True,
            "OLD crew formula must intersect medal at 520,527.5,240,33")
        self.assertIs(g._old_intersect3, True,
            "OLD crew formula must intersect buff element at 556.4,527,38,27")
        self.assertIs(g._new_intersect1, False,
            "NEW crew must NOT intersect tactical banner")
        self.assertIs(g._new_intersect2, False,
            "NEW crew must NOT intersect medal panel")
        self.assertIs(g._new_intersect3, False,
            "NEW crew must NOT intersect buff element")
        self.assertAlmostEqual(float(g._rt_root_w), 1280.0, places=1,
            msg="RED: runtime root width must match parent width 1280")
        self.assertAlmostEqual(float(g._rt_root_h), 720.0, places=1,
            msg="RED: runtime root height must match parent height 720")
        self.assertIs(g._crew_y_formula, True,
            "NEW crew y must be h-162e")
        self.assertIs(g._root_visible, True,
            "RED: crew root must be visible after runtime update")
        self.assertIs(g._certified, True,
            "RED: crew render must be certified after runtime update")
        self.assertAlmostEqual(float(g._rect1_x), 522.0, places=1)
        self.assertAlmostEqual(float(g._rect1_y), 482.5, places=1)
        self.assertAlmostEqual(float(g._rect1_w), 236.0, places=1)
        self.assertAlmostEqual(float(g._rect1_h), 36.0, places=1)
        self.assertAlmostEqual(float(g._rect2_x), 520.0, places=1)
        self.assertAlmostEqual(float(g._rect2_y), 527.5, places=1)
        self.assertAlmostEqual(float(g._rect2_w), 240.0, places=1)
        self.assertAlmostEqual(float(g._rect2_h), 33.0, places=1)
        self.assertAlmostEqual(float(g._rect3_x), 556.4, places=1)
        self.assertAlmostEqual(float(g._rect3_y), 527.0, places=1)
        self.assertAlmostEqual(float(g._rect3_w), 38.0, places=1)
        self.assertAlmostEqual(float(g._rect3_h), 27.0, places=1)

    def test_monotonic_updates_with_obstacle_states_same_primitives(self):
        """Repeated monotonic updates with three log-coordinate obstacles + genuine blocker.

        Three log-coordinate obstacles cycled visible/hidden/remove-recreate at .6 increments.
        Exact crew geometry and same roots/cards/text primitives preserved each phase.
        Each phase certified. Then genuine blocker at crew position: hide+uncertified, then recovery.
        """
        lua = mounted()
        lua.execute(r'''
            panel_double:set_shape(0, 0, 1280, 720)
            kyohud.settings.hud_scale = 1.0033333333
            RT:_do_refresh(managers.hud)
            C:refresh_settings(managers.hud)
            RT:update(managers.hud, 1.1, 0.05)

            local parent = C._parent_panel
            local combat = parent:child("kyohud_buff_panel")
            if not combat then
                combat = panel_double:panel({name="kyohud_buff_panel"})
                combat:set_shape(0, 0, 1280, 720)
            end
            combat:set_visible(true)
            kyohud._panel = combat

            local obs1 = combat:rect({name="log_obstacle_1", x=522, y=482.5, w=236, h=36, visible=false})
            local obs2 = combat:rect({name="log_obstacle_2", x=520, y=527.5, w=240, h=33, visible=false})
            local obs3 = combat:rect({name="log_obstacle_3", x=556.4, y=527, w=38, h=27, visible=false})

            RT:update(managers.hud, 1.6, 0.05)

            local lc = C._layout_cache
            local crew_x0, crew_y0 = lc.x, lc.y
            local crew_w0, crew_h0 = lc.total_w, lc.card_h
            _crew_x0 = crew_x0
            _crew_y0 = crew_y0
            _crew_w0 = crew_w0
            _crew_h0 = crew_h0

            local root_before = C._root
            local card1_before = C._cards[1]
            local name_text_before = card1_before._name_text
            local health_text_before = card1_before._health_text

            _phaseA_certified = C:_verify_render()
            _phaseA_x = lc.x
            _phaseA_y = lc.y
            _phaseA_w = lc.total_w
            _phaseA_h = lc.card_h

            obs1:set_visible(true)
            RT:update(managers.hud, 2.2, 0.05)
            _phaseB_certified = C:_verify_render()
            _phaseB_same_root = C._root == root_before
            _phaseB_same_card = C._cards[1] == card1_before
            _phaseB_same_name = C._cards[1]._name_text == name_text_before
            _phaseB_same_health = C._cards[1]._health_text == health_text_before
            _phaseB_x = C._layout_cache.x
            _phaseB_y = C._layout_cache.y
            _phaseB_w = C._layout_cache.total_w
            _phaseB_h = C._layout_cache.card_h

            obs1:set_visible(false)
            obs2:set_visible(true)
            RT:update(managers.hud, 2.8, 0.05)
            _phaseC_certified = C:_verify_render()
            _phaseC_same_root = C._root == root_before
            _phaseC_same_card = C._cards[1] == card1_before
            _phaseC_x = C._layout_cache.x
            _phaseC_y = C._layout_cache.y
            _phaseC_w = C._layout_cache.total_w
            _phaseC_h = C._layout_cache.card_h

            obs2:set_visible(false)
            combat:remove(combat:child("log_obstacle_1"))
            local obs1_new = combat:rect({name="log_obstacle_1_new", x=522, y=482.5, w=236, h=36, visible=false})
            obs3:set_visible(true)
            RT:update(managers.hud, 3.4, 0.05)
            _phaseD_certified = C:_verify_render()
            _phaseD_same_root = C._root == root_before
            _phaseD_same_card = C._cards[1] == card1_before
            _phaseD_same_name = C._cards[1]._name_text == name_text_before
            _phaseD_same_health = C._cards[1]._health_text == health_text_before
            _phaseD_x = C._layout_cache.x
            _phaseD_y = C._layout_cache.y
            _phaseD_w = C._layout_cache.total_w
            _phaseD_h = C._layout_cache.card_h

            obs3:set_visible(false)
            obs1_new:set_visible(true)
            RT:update(managers.hud, 4.0, 0.05)
            _phaseE_certified = C:_verify_render()
            _phaseE_same_root = C._root == root_before
            _phaseE_same_card = C._cards[1] == card1_before
            _phaseE_x = C._layout_cache.x
            _phaseE_y = C._layout_cache.y
            _phaseE_w = C._layout_cache.total_w
            _phaseE_h = C._layout_cache.card_h

            obs1_new:set_visible(false)
            combat:remove(combat:child("log_obstacle_1_new"))
            combat:remove(combat:child("log_obstacle_2"))
            combat:remove(combat:child("log_obstacle_3"))
            local obs1_re = combat:rect({name="log_obstacle_1_re", x=522, y=482.5, w=236, h=36, visible=false})
            local obs2_re = combat:rect({name="log_obstacle_2_re", x=520, y=527.5, w=240, h=33, visible=false})
            local obs3_re = combat:rect({name="log_obstacle_3_re", x=556.4, y=527, w=38, h=27, visible=false})
            RT:update(managers.hud, 4.6, 0.05)
            _phaseF_certified = C:_verify_render()
            _phaseF_same_root = C._root == root_before
            _phaseF_same_card = C._cards[1] == card1_before
            _phaseF_same_name = C._cards[1]._name_text == name_text_before
            _phaseF_same_health = C._cards[1]._health_text == health_text_before
            _phaseF_x = C._layout_cache.x
            _phaseF_y = C._layout_cache.y
            _phaseF_w = C._layout_cache.total_w
            _phaseF_h = C._layout_cache.card_h

            -- UNAVOIDABLE: full parent-height barrier spanning all possible crew Y positions;
            -- compact buff avoidance cannot route around a full-height obstacle, so hide is correct.
            local blocker = combat:rect({name="genuine_blocker", x=crew_x0, y=-combat:y(), w=crew_w0, h=C._parent_panel:h(), visible=true})
            RT:update(managers.hud, 5.2, 0.05)
            _blocker_hidden = not C._root:visible()
            _blocker_uncertified = not C:_verify_render()

            blocker:set_visible(false)
            RT:update(managers.hud, 5.8, 0.05)
            _recovered_certified = C:_verify_render()
            _recovered_same_root = C._root == root_before
            _recovered_same_card = C._cards[1] == card1_before
            _recovered_same_name = C._cards[1]._name_text == name_text_before
            _recovered_same_health = C._cards[1]._health_text == health_text_before
            _recovered_x = C._layout_cache.x
            _recovered_y = C._layout_cache.y
            _recovered_w = C._layout_cache.total_w
            _recovered_h = C._layout_cache.card_h
        ''')
        g = lua.globals()
        self.assertIs(g._phaseA_certified, True,
            "RED: phase A all obstacles hidden must be certified")
        self.assertIs(g._phaseB_certified, True,
            "RED: phase B obstacle 1 visible (no overlap) must be certified")
        self.assertIs(g._phaseB_same_root, True, "RED: phase B root primitive preserved")
        self.assertIs(g._phaseB_same_card, True, "RED: phase B card primitive preserved")
        self.assertIs(g._phaseB_same_name, True, "RED: phase B name text primitive preserved")
        self.assertIs(g._phaseB_same_health, True, "RED: phase B health text primitive preserved")
        self.assertIs(g._phaseC_certified, True,
            "RED: phase C obstacle 2 visible must be certified")
        self.assertIs(g._phaseC_same_root, True, "RED: phase C root primitive preserved")
        self.assertIs(g._phaseC_same_card, True, "RED: phase C card primitive preserved")
        self.assertIs(g._phaseD_certified, True,
            "RED: phase D remove-recreate obstacle 1, obstacle 3 visible must be certified")
        self.assertIs(g._phaseD_same_root, True, "RED: phase D root primitive preserved")
        self.assertIs(g._phaseD_same_card, True, "RED: phase D card primitive preserved")
        self.assertIs(g._phaseD_same_name, True, "RED: phase D name text primitive preserved")
        self.assertIs(g._phaseD_same_health, True, "RED: phase D health text primitive preserved")
        self.assertIs(g._phaseE_certified, True,
            "RED: phase E recreated obstacle 1 visible must be certified")
        self.assertIs(g._phaseE_same_root, True, "RED: phase E root primitive preserved")
        self.assertIs(g._phaseE_same_card, True, "RED: phase E card primitive preserved")
        self.assertIs(g._phaseF_certified, True,
            "RED: phase F all recreated obstacles hidden must be certified")
        self.assertIs(g._phaseF_same_root, True, "RED: phase F root primitive preserved")
        self.assertIs(g._phaseF_same_card, True, "RED: phase F card primitive preserved")
        self.assertIs(g._phaseF_same_name, True, "RED: phase F name text primitive preserved")
        self.assertIs(g._phaseF_same_health, True, "RED: phase F health text primitive preserved")
        for phase_letter in ('A', 'B', 'C', 'D', 'E', 'F'):
            px = float(g['_phase' + phase_letter + '_x'])
            py = float(g['_phase' + phase_letter + '_y'])
            pw = float(g['_phase' + phase_letter + '_w'])
            ph = float(g['_phase' + phase_letter + '_h'])
            self.assertAlmostEqual(px, float(g._crew_x0), places=3,
                msg="RED: phase " + phase_letter + " crew x must be unchanged")
            self.assertAlmostEqual(py, float(g._crew_y0), places=3,
                msg="RED: phase " + phase_letter + " crew y must be unchanged")
            self.assertAlmostEqual(pw, float(g._crew_w0), places=3,
                msg="RED: phase " + phase_letter + " crew w must be unchanged")
            self.assertAlmostEqual(ph, float(g._crew_h0), places=3,
                msg="RED: phase " + phase_letter + " crew h must be unchanged")
        self.assertIs(g._blocker_hidden, True,
            "RED: crew must be hidden when genuine blocker visible across crew")
        self.assertIs(g._blocker_uncertified, True,
            "RED: crew must be uncertified when genuine blocker visible")
        self.assertIs(g._recovered_certified, True,
            "RED: crew must recover certified when blocker hidden")
        self.assertIs(g._recovered_same_root, True,
            "RED: root primitive must be preserved after blocker recovery")
        self.assertIs(g._recovered_same_card, True,
            "RED: card primitive must be preserved after blocker recovery")
        self.assertIs(g._recovered_same_name, True,
            "RED: name text primitive must be preserved after blocker recovery")
        self.assertIs(g._recovered_same_health, True,
            "RED: health text primitive must be preserved after blocker recovery")
        self.assertAlmostEqual(float(g._recovered_x), float(g._crew_x0), places=3,
            msg="RED: recovered crew x must be unchanged")
        self.assertAlmostEqual(float(g._recovered_y), float(g._crew_y0), places=3,
            msg="RED: recovered crew y must be unchanged")
        self.assertAlmostEqual(float(g._recovered_w), float(g._crew_w0), places=3,
            msg="RED: recovered crew w must be unchanged")
        self.assertAlmostEqual(float(g._recovered_h), float(g._crew_h0), places=3,
            msg="RED: recovered crew h must be unchanged")

    def test_multi_dimension_scale_combinations_geometry_contract(self):
        """Multiple dimensions and scales: geometry cap/in-bounds/equipment separation.

        Dimensions: 1280x720, 1680x1050, 1920x1080
        Scales: 0.95, 1.0, 1.05
        Nonzero world offsets via world_x/world_y fixture recursively through parent.
        panel_double x=37, y=19; combat child offset 11, 13.
        Genuine blocker with adjusted local coords from lc; conflict then recovery.
        A-B-A same primitives and deterministic positions across all four layout fields.
        """
        lua = mounted()
        lua.execute(r'''
            local Panel_mt = getmetatable(panel_double)
            function Panel_mt.__index:world_x()
                if self._parent and type(self._parent.world_x) == "function" then
                    return self._parent:world_x() + self._x
                end
                return self._x
            end
            function Panel_mt.__index:world_y()
                if self._parent and type(self._parent.world_y) == "function" then
                    return self._parent:world_y() + self._y
                end
                return self._y
            end

            panel_double:set_shape(37, 19, 1280, 720)
            kyohud.settings.hud_scale = 1.0033333333
            RT:_do_refresh(managers.hud)
            C:refresh_settings(managers.hud)
            RT:update(managers.hud, 1.1, 0.05)

            local parent = C._parent_panel
            local combat = parent:child("kyohud_buff_panel")
            if not combat then
                combat = panel_double:panel({name="kyohud_buff_panel"})
            end
            combat:set_shape(11, 13, 1280, 720)
            combat:set_visible(true)
            kyohud._panel = combat

            local lc = C._layout_cache
            local lc_x0, lc_y0 = lc.x, lc.y
            local root_before = C._root
            local card1_before = C._cards[1]
            local blocker_x = lc_x0 - 11
            -- UNAVOIDABLE: world-space full parent-height barrier at combat offset y=13;
            -- compact buff avoidance cannot route around a full-height obstacle, so hide is correct.
            local blocker_y = -13
            local blocker = combat:rect({name="world_blocker", x=blocker_x, y=blocker_y, w=lc.total_w, h=parent:h(), visible=true})
            RT:update(managers.hud, 1.6, 0.05)
            _world_conflict_hidden = not C._root:visible()
            _world_conflict_uncertified = not C:_verify_render()

            blocker:set_visible(false)
            RT:update(managers.hud, 2.2, 0.05)
            _world_recovered = C:_verify_render()
            _world_recovered_same_root = C._root == root_before
            _world_recovered_same_card = C._cards[1] == card1_before

            combat:remove(combat:child("world_blocker"))

            local dimensions = {{1280, 720}, {1680, 1050}, {1920, 1080}}
            local scales = {0.95, 1.0, 1.05}
            local results = {}
            local combo_count = 0
            local certified_count = 0

            for _, dim in ipairs(dimensions) do
                for _, scale in ipairs(scales) do
                    combo_count = combo_count + 1
                    panel_double:set_shape(37, 19, dim[1], dim[2])
                    kyohud.settings.hud_scale = scale
                    RT:_do_refresh(managers.hud)
                    C:refresh_settings(managers.hud)
                    RT:update(managers.hud, 2.2 + combo_count * 0.6, 0.05)

                    local c = C:_verify_render()
                    if c then certified_count = certified_count + 1 end

                    local lc2 = C._layout_cache
                    if lc2 then
                        local geom = kyohud.hud.layout.resolve(dim[1], dim[2], scale)
                        local e = geom.uniform_scale * geom.scale
                        local lp = kyohud.hud.layout.local_player(dim[1], dim[2], scale)
                        local boundary = lp and (lp.x - 12 * e) or 0
                        local crew_bottom = lc2.y + lc2.card_h
                        local state_top = lc2.y - (lc2.state_h or 0)
                        local expected_y = dim[2] - 144 * e

                        local in_bounds = (lc2.x >= 0) and (state_top >= 0)
                            and (lc2.x + lc2.total_w <= dim[1])
                            and (crew_bottom <= dim[2])

                        local equipment_separation = boundary > 0 and (lc2.x + lc2.total_w) <= boundary + 0.5

                        results[combo_count] = {
                            capped = math.abs(lc2.y - expected_y) < 0.5,
                            in_bounds = in_bounds,
                            equipment_sep = equipment_separation,
                            x = lc2.x,
                            y = lc2.y,
                            w = lc2.total_w,
                            h = lc2.card_h,
                            certified = c,
                        }
                    else
                        results[combo_count] = {capped = false, in_bounds = false, equipment_sep = false, certified = false}
                    end
                end
            end

            _combo_count = combo_count
            _certified_count = certified_count
            _all_capped = true
            _all_in_bounds = true
            _all_equipment_sep = true
            _all_certified = true
            for _, r in ipairs(results) do
                if not r.capped then _all_capped = false end
                if not r.in_bounds then _all_in_bounds = false end
                if not r.equipment_sep then _all_equipment_sep = false end
                if not r.certified then _all_certified = false end
            end

            panel_double:set_shape(37, 19, 1920, 1080)
            kyohud.settings.hud_scale = 1.0
            RT:_do_refresh(managers.hud)
            C:refresh_settings(managers.hud)
            RT:update(managers.hud, 10.0, 0.05)
            local root_a = C._root
            local card1_a = C._cards[1]
            local pos_x_a = C._layout_cache and C._layout_cache.x or nil
            local pos_y_a = C._layout_cache and C._layout_cache.y or nil
            local pos_w_a = C._layout_cache and C._layout_cache.total_w or nil
            local pos_h_a = C._layout_cache and C._layout_cache.card_h or nil

            panel_double:set_shape(37, 19, 1280, 720)
            kyohud.settings.hud_scale = 0.95
            RT:_do_refresh(managers.hud)
            C:refresh_settings(managers.hud)
            RT:update(managers.hud, 10.6, 0.05)

            panel_double:set_shape(37, 19, 1920, 1080)
            kyohud.settings.hud_scale = 1.0
            RT:_do_refresh(managers.hud)
            C:refresh_settings(managers.hud)
            RT:update(managers.hud, 11.2, 0.05)
            local root_b = C._root
            local card1_b = C._cards[1]
            local pos_x_b = C._layout_cache and C._layout_cache.x or nil
            local pos_y_b = C._layout_cache and C._layout_cache.y or nil
            local pos_w_b = C._layout_cache and C._layout_cache.total_w or nil
            local pos_h_b = C._layout_cache and C._layout_cache.card_h or nil

            _aba_same_root = root_a == root_b
            _aba_same_card = card1_a == card1_b
            _aba_same_x = pos_x_a == pos_x_b
            _aba_same_y = pos_y_a == pos_y_b
            _aba_same_w = pos_w_a == pos_w_b
            _aba_same_h = pos_h_a == pos_h_b
        ''')
        g = lua.globals()
        self.assertIs(g._world_conflict_hidden, True,
            "RED: crew must be hidden when world-offset blocker overlaps")
        self.assertIs(g._world_conflict_uncertified, True,
            "RED: crew must be uncertified when world-offset blocker overlaps")
        self.assertIs(g._world_recovered, True,
            "RED: crew must recover after world-offset blocker hidden")
        self.assertIs(g._world_recovered_same_root, True,
            "RED: root must survive world-offset blocker recovery")
        self.assertIs(g._world_recovered_same_card, True,
            "RED: card must survive world-offset blocker recovery")
        self.assertEqual(int(g._combo_count), 9,
            "RED: must audit all 9 dimension-scale combinations")
        self.assertEqual(int(g._certified_count), 9,
            "RED: all 9 combinations must be certified")
        self.assertIs(g._all_capped, True,
            "RED: all 9 combinations must have y = h-162e")
        self.assertIs(g._all_in_bounds, True,
            "RED: all 9 combinations must keep crew in bounds")
        self.assertIs(g._all_equipment_sep, True,
            "RED: all 9 combinations must maintain equipment separation")
        self.assertIs(g._aba_same_root, True,
            "RED: A-B-A dimension changes must preserve root primitive")
        self.assertIs(g._aba_same_card, True,
            "RED: A-B-A dimension changes must preserve card primitive")
        self.assertIs(g._aba_same_x, True,
            "RED: A-B-A dimension changes must produce deterministic x")
        self.assertIs(g._aba_same_y, True,
            "RED: A-B-A dimension changes must produce deterministic y")
        self.assertIs(g._aba_same_w, True,
            "RED: A-B-A dimension changes must produce deterministic w")
        self.assertIs(g._aba_same_h, True,
            "RED: A-B-A dimension changes must produce deterministic h")


if __name__ == '__main__':
    unittest.main()
