"""Crew obstacle qualification -- bug reproduction for empty container dimension mismatch.

These tests reproduce the exact bug at crew.lua:260 where an empty combat panel
(core.lua:1714 kyohud_buff_panel) with dimensions smaller than crew parent
causes false occupancy detection, hiding crew.

Bug mechanism:
  The combat panel is created as an empty container with no children. Its
  dimensions are synchronized to its parent panel. When the combat panel is
  smaller than the crew parent (dimension mismatch), crew.lua:260 incorrectly
  treats the entire empty container as occupied, hiding crew.

Test strategy (bug reproduction, not proof of engine dimensions):
  - Use mismatched combat root 1280x1080 (width smaller than 1920, intersects crew)
  - Assert geometry precondition: combat panel intersects crew region
  - Empty container with dimension mismatch => visible/certified (bug reproduction)
   - Real child rect crossing crew => hidden (preserve existing conflict detection)
   - Child hide => recover same primitives (root, card instances preserved)
   - Hidden/alpha=0 child => ignored (no conflict)

These tests define the desired contract for the real producer. They are bug
reproduction tests demonstrating the false conflict, not proof that engine
dimensions are exact.
"""
import unittest
from test_hud_crew_acceptance import mounted


class RealProducerEmptyContainerTests(unittest.TestCase):
    """Real producer: core.lua:1714 kyohud_buff_panel (empty container).

    Tests the actual engine cause: an empty combat panel with dimensions
    smaller than crew parent triggers crew.lua:260 occupancy check, hiding crew.
    """

    def test_empty_combat_dimension_mismatch_must_not_hide(self):
        """Empty combat panel at 1280x1080 against mounted 1920x1080 must NOT hide crew.

        This reproduces the real producer: core.lua:1714 creates kyohud_buff_panel
        as an empty container whose size is synced to its parent. When combat panel
        width (1280) is smaller than crew parent width (1920), crew.lua:260
        must NOT treat this empty container as occupied.

        Bug reproduction: geometry precondition asserts intersection exists.
        """
        lua = mounted()
        lua.execute(r'''
            local parent = C._parent_panel
            local combat = panel_double:panel({name='kyohud_buff_panel'})
            combat:set_shape(0, 0, 1280, 1080)
            combat:set_visible(true)
            kyohud._panel = combat

            local lc = C._layout_cache
            local cx, cy, cw, ch = combat:x(), combat:y(), combat:w(), combat:h()
            local lx, ly, lw, lh = lc.x, lc.y, lc.total_w, lc.card_h
            _intersects = (cx < lx + lw) and (cx + cw > lx) and (cy < ly + lh) and (cy + ch > ly)

            RT:update(managers.hud, 2.0, 0.05)
            _not_hidden = C._root:visible()
            _verified = C:_verify_render()
        ''')
        g = lua.globals()
        self.assertIs(g._intersects, True,
            "Geometry precondition: combat panel must intersect crew region")
        self.assertIs(g._not_hidden, True,
            "RED: empty combat panel with dimension mismatch must not hide crew")
        self.assertIs(g._verified, True,
            "RED: crew render must verify after empty container obstacle")

    def test_empty_combat_real_child_crossing_must_hide(self):
        """Empty combat panel with real child rect crossing crew MUST hide crew.

        When the empty container (core.lua:1714) gains a real child that overlaps
        crew region, crew must be hidden (existing behavior preserved). Bug
        reproduction with geometry precondition.
        """
        lua = mounted()
        lua.execute(r'''
            local parent = C._parent_panel
            local combat = panel_double:panel({name='kyohud_buff_panel_with_child'})
            combat:set_shape(0, 0, 1280, 1080)
            combat:set_visible(true)
            kyohud._panel = combat

            local lc = C._layout_cache
            local cx, cy, cw, ch = combat:x(), combat:y(), combat:w(), combat:h()
            local lx, ly, lw, lh = lc.x, lc.y, lc.total_w, lc.card_h
            _intersects = (cx < lx + lw) and (cx + cw > lx) and (cy < ly + lh) and (cy + ch > ly)

            local blocker = combat:rect({
                name='real_child_blocker',
                x=lc.x, y=lc.y, w=lc.total_w, h=lc.card_h,
                visible=true,
            })

            RT:update(managers.hud, 2.0, 0.05)
            _hidden = not C._root:visible()
        ''')
        g = lua.globals()
        self.assertIs(g._intersects, True,
            "Geometry precondition: combat panel must intersect crew region")
        self.assertIs(g._hidden, True,
            "RED: empty container with real child crossing crew must hide crew")

    def test_empty_combat_child_hide_recover_same_primitives(self):
        """When child in empty container hides, crew recovers same root/card.

        Tests that disappearance of a real child from the empty container
        preserves crew primitives (same root, same card instances). Bug
        reproduction with geometry precondition.
        """
        lua = mounted()
        lua.execute(r'''
            local parent = C._parent_panel
            local combat = panel_double:panel({name='kyohud_buff_panel_transient'})
            combat:set_shape(0, 0, 1280, 1080)
            combat:set_visible(true)
            kyohud._panel = combat

            local lc = C._layout_cache
            local cx, cy, cw, ch = combat:x(), combat:y(), combat:w(), combat:h()
            local lx, ly, lw, lh = lc.x, lc.y, lc.total_w, lc.card_h
            _intersects = (cx < lx + lw) and (cx + cw > lx) and (cy < ly + lh) and (cy + ch > ly)

            local blocker = combat:rect({
                name='transient_child_blocker',
                x=lc.x, y=lc.y, w=lc.total_w, h=lc.card_h,
                visible=true,
            })

            RT:update(managers.hud, 2.0, 0.05)
            _hidden = not C._root:visible()

            local card1 = C._cards[1]
            local root = C._root
            local name_text = card1._name_text
            local health_text = card1._health_text

            blocker:set_visible(false)
            RT:update(managers.hud, 2.6, 0.05)
            _recovered = C:_verify_render()
            _same_root = C._root == root
            _same_card = C._cards[1] == card1
            _same_name = C._cards[1]._name_text == name_text
            _same_health = C._cards[1]._health_text == health_text
        ''')
        g = lua.globals()
        self.assertIs(g._intersects, True,
            "Geometry precondition: combat panel must intersect crew region")
        self.assertIs(g._hidden, True,
            "RED: real child crossing crew must hide crew")
        self.assertIs(g._recovered, True,
            "RED: crew must recover when child disappears from empty container")
        self.assertIs(g._same_root, True,
            "RED: root primitive must be preserved")
        self.assertIs(g._same_card, True,
            "RED: card primitive must be preserved")
        self.assertIs(g._same_name, True,
            "RED: name text primitive must be preserved")
        self.assertIs(g._same_health, True,
            "RED: health text primitive must be preserved")

    def test_empty_combat_alpha0_and_hidden_child_ignored(self):
        """Empty combat panel with hidden or alpha=0 child must NOT hide crew.

        Even when a child exists in the empty container, if it has visible=false
        or alpha=0, it must not cause conflict. Bug reproduction with geometry
        precondition.
        """
        lua = mounted()
        lua.execute(r'''
            local parent = C._parent_panel
            local combat = panel_double:panel({name='kyohud_buff_panel_alpha'})
            combat:set_shape(0, 0, 1280, 1080)
            combat:set_visible(true)
            kyohud._panel = combat

            local lc = C._layout_cache
            local cx, cy, cw, ch = combat:x(), combat:y(), combat:w(), combat:h()
            local lx, ly, lw, lh = lc.x, lc.y, lc.total_w, lc.card_h
            _intersects = (cx < lx + lw) and (cx + cw > lx) and (cy < ly + lh) and (cy + ch > ly)

            local hidden_child = combat:rect({
                name='hidden_crossing_child',
                x=lc.x, y=lc.y, w=lc.total_w, h=lc.card_h,
                visible=false,
            })

            RT:update(managers.hud, 2.0, 0.05)
            _not_hidden_invisible = C._root:visible()

            hidden_child:set_visible(true)
            hidden_child:set_alpha(0)
            RT:update(managers.hud, 2.6, 0.05)
            _not_hidden_alpha0 = C._root:visible()
        ''')
        g = lua.globals()
        self.assertIs(g._intersects, True,
            "Geometry precondition: combat panel must intersect crew region")
        self.assertIs(g._not_hidden_invisible, True,
            "RED: invisible child must not conflict")
        self.assertIs(g._not_hidden_alpha0, True,
            "RED: alpha=0 child must not conflict")


if __name__ == '__main__':
    unittest.main()
