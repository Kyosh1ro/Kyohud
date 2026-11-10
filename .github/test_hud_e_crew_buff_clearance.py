"""Fixed crew: unadapted/unknown combat obstacles still fail closed.

The real buff producer yields in test_hud_crew_online_placement.py. These
artificial rectangles do not run that producer and must never move the crew
or be silently ignored. Retain hidden/empty/unknown geometry recovery checks.
"""
import unittest
from test_hud_crew_acceptance import mounted


class CrewBuffClearanceTests(unittest.TestCase):
    """Unadapted obstacles yield visibility, never crew placement."""

    def test_unadapted_buff_overlap_hides_without_moving_crew(self):
        """Unadapted rectangle hides crew at its fixed anchor, preserving roots."""
        lua = mounted()
        lua.execute(r'''
            local parent = C._parent_panel
            local buff = parent:panel({name='kyohud_buff_panel'})
            local lc = C._layout_cache
            local state_h = lc.state_h
            local card_h = lc.card_h
            local scale = kyohud.settings.hud_scale or 1
            local geom = kyohud.hud.layout.resolve(parent:w(), parent:h(), scale)
            local e = (geom.uniform_scale or 1) * (geom.scale or 1)
            local gap = 12 * e
            buff:set_shape(0, 0, parent:w(), parent:h())
            buff:set_visible(true)
            buff:set_alpha(1)
            local icon = buff:rect({name='icon1'})
            icon:set_shape(lc.x, lc.y - 40 * e, lc.total_w, card_h)
            icon:set_visible(true)
            icon:set_alpha(1)
            kyohud._panel = buff

            local card1_root = C._cards[1].root
            local card2_root = C._cards[2].root
            local card3_root = C._cards[3].root
            local crew_root = C._root
            local nominal_y = lc.y

            local pre_visible = C._root:visible()
            local pre_verified = C:_verify_render()

            RT:update(managers.hud, 2.0, 0.05)
            _crew_visible = C._root:visible()
            _verified = C:_verify_render()
            _above = C._root:y() < (nominal_y - state_h)
            _nominal = math.abs(C._root:y() - (nominal_y - state_h)) < .01
            _buff_unchanged = buff:visible() and buff:alpha() == 1
            _same_roots = C._root == crew_root
                and C._cards[1].root == card1_root
                and C._cards[2].root == card2_root
                and C._cards[3].root == card3_root
            local new_y = C._root:y()
            local root_h = C._root:h()
            local icon_top = icon:y()
            local expected_gap = icon_top - (new_y + root_h)
            _gap_ok = math.abs(expected_gap - gap) < 1.0
            _pre_visible = pre_visible
            _pre_verified = pre_verified
        ''')
        g = lua.globals()
        self.assertIs(g._pre_visible, True, "crew must be visible before obstacle")
        self.assertIs(g._pre_verified, True, "crew must verify before obstacle")
        self.assertIs(g._crew_visible, False, "unadapted obstacle must fail closed")
        self.assertIs(g._verified, False, "hidden crew must not certify")
        self.assertIs(g._above, False, "crew must not move above buff")
        self.assertIs(g._nominal, True, "crew anchor stays fixed")
        self.assertIs(g._buff_unchanged, True, "buff must be unchanged")
        self.assertIs(g._same_roots, True, "same roots/cards preserved")
        self.assertIs(g._gap_ok, False, "crew must not create clearance by moving")

    def test_buff_hide_restores_nominal(self):
        """Removing the obstacle restores visibility without changing the anchor."""
        lua = mounted()
        lua.execute(r'''
            local parent = C._parent_panel
            local buff = parent:panel({name='kyohud_buff_panel'})
            local lc = C._layout_cache
            local state_h = lc.state_h
            local card_h = lc.card_h
            local scale = kyohud.settings.hud_scale or 1
            local geom = kyohud.hud.layout.resolve(parent:w(), parent:h(), scale)
            local e = (geom.uniform_scale or 1) * (geom.scale or 1)
            buff:set_shape(0, 0, parent:w(), parent:h())
            buff:set_visible(true)
            local icon = buff:rect({name='icon1'})
            icon:set_shape(lc.x, lc.y - 40 * e, lc.total_w, card_h)
            icon:set_visible(true)
            icon:set_alpha(1)
            kyohud._panel = buff

            local nominal_y_num = lc.y

            RT:update(managers.hud, 2.0, 0.05)
            _moved = C._root:y() < (nominal_y_num - state_h)

            buff:set_visible(false)
            RT:update(managers.hud, 2.6, 0.05)
            _restored = math.abs(C._root:y() - (nominal_y_num - state_h)) < 0.5
            _verified = C:_verify_render()
        ''')
        g = lua.globals()
        self.assertIs(g._moved, False, "crew must stay fixed when buff present")
        self.assertIs(g._restored, True, "crew must restore nominal y")
        self.assertIs(g._verified, True, "crew must verify after restore")

    def test_buff_alpha0_no_movement(self):
        """Alpha=0 buff -> no crew movement.

        Buff with alpha=0 is not a visible obstacle; crew stays nominal.
        """
        lua = mounted()
        lua.execute(r'''
            local parent = C._parent_panel
            local buff = parent:panel({name='kyohud_buff_panel'})
            local lc = C._layout_cache
            local state_h = lc.state_h
            local card_h = lc.card_h
            local scale = kyohud.settings.hud_scale or 1
            local geom = kyohud.hud.layout.resolve(parent:w(), parent:h(), scale)
            local e = (geom.uniform_scale or 1) * (geom.scale or 1)
            buff:set_shape(0, 0, parent:w(), parent:h())
            buff:set_visible(true)
            local icon = buff:rect({name='icon1'})
            icon:set_shape(lc.x, lc.y - 40 * e, lc.total_w, card_h)
            icon:set_visible(true)
            icon:set_alpha(0)
            kyohud._panel = buff

            local nominal_y_num = lc.y

            RT:update(managers.hud, 2.0, 0.05)
            _nominal = math.abs(C._root:y() - (nominal_y_num - state_h)) < 0.5
            _verified = C:_verify_render()
        ''')
        g = lua.globals()
        self.assertIs(g._nominal, True, "alpha=0 buff must not move crew")
        self.assertIs(g._verified, True, "crew must verify")

    def test_buff_hidden_no_movement(self):
        """Hidden buff -> no crew movement.

        Buff with visible=false is not an obstacle; crew stays nominal.
        """
        lua = mounted()
        lua.execute(r'''
            local parent = C._parent_panel
            local buff = parent:panel({name='kyohud_buff_panel'})
            local lc = C._layout_cache
            local state_h = lc.state_h
            local card_h = lc.card_h
            local scale = kyohud.settings.hud_scale or 1
            local geom = kyohud.hud.layout.resolve(parent:w(), parent:h(), scale)
            local e = (geom.uniform_scale or 1) * (geom.scale or 1)
            buff:set_shape(0, 0, parent:w(), parent:h())
            buff:set_visible(true)
            local icon = buff:rect({name='icon1'})
            icon:set_shape(lc.x, lc.y - 40 * e, lc.total_w, card_h)
            icon:set_visible(false)
            icon:set_alpha(1)
            kyohud._panel = buff

            local nominal_y_num = lc.y

            RT:update(managers.hud, 2.0, 0.05)
            _nominal = math.abs(C._root:y() - (nominal_y_num - state_h)) < 0.5
            _verified = C:_verify_render()
        ''')
        g = lua.globals()
        self.assertIs(g._nominal, True, "hidden buff must not move crew")
        self.assertIs(g._verified, True, "crew must verify")

    def test_impossible_top_obstacle_hides(self):
        """An unadapted full-parent obstacle retains the hide fallback."""
        lua = mounted()
        lua.execute(r'''
            local parent = C._parent_panel
            local buff = parent:panel({name='kyohud_buff_panel'})
            local lc = C._layout_cache
            buff:set_shape(0, 0, parent:w(), parent:h())
            buff:set_visible(true)
            buff:set_alpha(1)
            local icon = buff:rect({name='fullcover'})
            icon:set_shape(0, 0, parent:w(), parent:h())
            icon:set_visible(true)
            icon:set_alpha(1)
            kyohud._panel = buff

            RT:update(managers.hud, 2.0, 0.05)
            _hidden = not C._root:visible()
        ''')
        g = lua.globals()
        self.assertIs(g._hidden, True, "impossible fullcover must hide crew")

    def test_unknown_blocker_keeps_hide_fallback(self):
        """Unknown blocker name (not kyohud_buff_panel) -> hide fallback.

        Generic/unknown obstacle names retain conservative existing fallback
        (hide crew). The real buff producer alone implements one-way yielding.
        """
        lua = mounted()
        lua.execute(r'''
            local parent = C._parent_panel
            local blocker = parent:panel({name='unknown_blocker'})
            local lc = C._layout_cache
            local card_h = lc.card_h
            local scale = kyohud.settings.hud_scale or 1
            local geom = kyohud.hud.layout.resolve(parent:w(), parent:h(), scale)
            local e = (geom.uniform_scale or 1) * (geom.scale or 1)
            blocker:set_shape(0, 0, parent:w(), parent:h())
            blocker:set_visible(true)
            blocker:set_alpha(1)
            local icon = blocker:rect({name='icon1'})
            icon:set_shape(lc.x, lc.y - 40 * e, lc.total_w, card_h)
            icon:set_visible(true)
            icon:set_alpha(1)
            kyohud._panel = blocker

            RT:update(managers.hud, 2.0, 0.05)
            _hidden = not C._root:visible()
        ''')
        g = lua.globals()
        self.assertIs(g._hidden, True, "unknown blocker must hide crew")

    def test_no_buff_stays_nominal(self):
        """Empty parent with no children -> crew stays at nominal y.

        When kyohud._panel is an empty kyohud_buff_panel (no children), crew stays nominal.
        """
        lua = mounted()
        lua.execute(r'''
            local parent = C._parent_panel
            local empty_panel = parent:panel({name='kyohud_buff_panel'})
            empty_panel:set_shape(0, 0, parent:w(), parent:h())
            empty_panel:set_visible(true)
            empty_panel:set_alpha(1)
            kyohud._panel = empty_panel

            local lc = C._layout_cache
            local state_h = lc.state_h
            local nominal_y_num = lc.y

            RT:update(managers.hud, 2.0, 0.05)
            _nominal = math.abs(C._root:y() - (nominal_y_num - state_h)) < 0.5
            _verified = C:_verify_render()
        ''')
        g = lua.globals()
        self.assertIs(g._nominal, True, "empty parent keeps nominal")
        self.assertIs(g._verified, True, "crew must verify")

    def test_multiple_unadapted_obstacles_hide_without_moving_crew(self):
        """Two stacked buff icons -> crew above both with gap.

        When there are two obstacles at different heights, the resolver
        iterates to find a position above the highest one.
        """
        lua = mounted()
        lua.execute(r'''
            local parent = C._parent_panel
            local buff = parent:panel({name='kyohud_buff_panel'})
            local lc = C._layout_cache
            local state_h = lc.state_h
            local card_h = lc.card_h
            local scale = kyohud.settings.hud_scale or 1
            local geom = kyohud.hud.layout.resolve(parent:w(), parent:h(), scale)
            local e = (geom.uniform_scale or 1) * (geom.scale or 1)
            local gap = 12 * e
            buff:set_shape(0, 0, parent:w(), parent:h())
            buff:set_visible(true)
            buff:set_alpha(1)
            local icon_low = buff:rect({name='icon_low'})
            icon_low:set_shape(lc.x, lc.y - 40 * e, lc.total_w, card_h)
            icon_low:set_visible(true)
            icon_low:set_alpha(1)
            local icon_high = buff:rect({name='icon_high'})
            icon_high:set_shape(lc.x, lc.y - 100 * e, lc.total_w, card_h)
            icon_high:set_visible(true)
            icon_high:set_alpha(1)
            kyohud._panel = buff

            local card1_root = C._cards[1].root
            local card2_root = C._cards[2].root
            local card3_root = C._cards[3].root
            local crew_root = C._root
            local nominal_y_num = lc.y

            RT:update(managers.hud, 2.0, 0.05)
            _crew_visible = C._root:visible()
            _verified = C:_verify_render()
            _above_both = C._root:y() < (nominal_y_num - state_h - 50 * e)
            _nominal = math.abs(C._root:y() - (nominal_y_num - state_h)) < .01
            _same_roots = C._root == crew_root
                and C._cards[1].root == card1_root
                and C._cards[2].root == card2_root
                and C._cards[3].root == card3_root
            local root_bottom = C._root:y() + C._root:h()
            local high_top = icon_high:y()
            local expected_gap = high_top - root_bottom
            _gap_ok = math.abs(expected_gap - gap) < 1.0
            _buff_unchanged = buff:visible() and buff:alpha() == 1
            _icons_unchanged = icon_low:visible() and icon_low:alpha() == 1
                and icon_high:visible() and icon_high:alpha() == 1
        ''')
        g = lua.globals()
        self.assertIs(g._crew_visible, False, "unadapted obstacle must fail closed")
        self.assertIs(g._verified, False, "hidden crew must not certify")
        self.assertIs(g._above_both, False, "crew must not move above obstacles")
        self.assertIs(g._nominal, True, "crew anchor stays fixed")
        self.assertIs(g._same_roots, True, "same roots/cards preserved")
        self.assertIs(g._gap_ok, False, "crew must not create clearance by moving")
        self.assertIs(g._buff_unchanged, True, "buff parent unchanged")
        self.assertIs(g._icons_unchanged, True, "icons unchanged")


class CrewUnknownBuffGeometryTests(unittest.TestCase):
    def test_nonfinite_obstacles_hide_and_recover_same_crew(self):
        for mutation in ('parent_alpha', 'child_x', 'child_width'):
            with self.subTest(mutation=mutation):
                lua = mounted()
                lua.globals().mutation = mutation
                lua.execute(r'''
                    local parent = C._parent_panel
                    local lc = C._layout_cache
                    local root, card = C._root, C._cards[1].root
                    local buff = parent:panel({name='kyohud_buff_panel'})
                    buff:set_shape(0,0,parent:w(),parent:h())
                    buff:set_alpha(1)
                    local icon = buff:rect({name='occupied'})
                    icon:set_shape(lc.x,lc.y,20,20)
                    icon:set_alpha(1)
                    kyohud._panel = buff
                    RT:update(managers.hud,2,.05)
                    _positive = C._root:visible() and C:_verify_render()
                    if mutation == 'parent_alpha' then buff:set_alpha(0/0)
                    elseif mutation == 'child_x' then icon:set_shape(0/0,lc.y,20,20)
                    else icon:set_shape(lc.x,lc.y,0/0,20) end
                    RT:update(managers.hud,2.6,.05)
                    _hidden = not C._root:visible()
                    buff:set_alpha(1)
                    icon:set_shape(lc.x,lc.y,20,20)
                    RT:update(managers.hud,3.2,.05)
                    _recovered = C._root:visible() and C:_verify_render()
                        and C._root == root and C._cards[1].root == card
                ''')
                self.assertTrue(lua.globals()._positive)
                self.assertTrue(lua.globals()._hidden)
                self.assertTrue(lua.globals()._recovered)


if __name__ == "__main__":
    unittest.main()
