"""Bottom-right placement -- player, crew, and native overlap fallback.

Three tests validating actual visually drawn positions:
1. Player bottom-right: shared owned backdrop bottom == parent_h - 24e, P._root right == w - 40e
2. Crew cards bottom: each visible card._backdrop world-relative bottom == parent_h - 24e
3. Native HUDTemp bag_panel overlap: P/W/E/backdrop verified visible, native unchanged, fallback when overlapping

Uses real _radial_runtime from test_hud_e_native_replacement and mounted() from test_hud_crew_acceptance.
Native primitives are tables with x/y/w/h, no shape() accessor.
"""
import unittest
from test_hud_e_native_replacement import _radial_runtime, _base_fixture, _crew_lua
from test_hud_crew_acceptance import mounted


class PlayerBottomRightPlacementTests(unittest.TestCase):
    """Player bottom-right: shared backdrop bottom, P._root right edge."""

    def test_player_bottom_right_backdrop_and_root_placement(self):
        """Actual visible drawn bottom/right placement.

        Reuse _radial_runtime for real composed runtime/data.
        Compute e from min(actualRTparentw/1920, h/1080) * settings.hud_scale.
        Shared owned backdrop R:_local_backdrop_geometry() y+h == actual parent h - 24e within 0.5.
        P._root right == w - 40e.
        Do NOT assert condition_text/root bottom as substitute for VISIBLY drawn bottom.
        """
        lua = _radial_runtime()
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local P = kyohud.hud.player
            local W = kyohud.hud.weapons
            local E = kyohud.hud.equipment
            local parent = RT._parent_panel
            local pw = parent:w()
            local ph = parent:h()
            local scale = kyohud.settings.hud_scale
            local e = math.min(pw / 1920, ph / 1080) * scale

            assert(P:verify(), "P must verify positive")
            assert(W:verify(), "W must verify positive")
            assert(E:verify(), "E must verify positive")

            local geom = RT:_local_backdrop_geometry()
            assert(geom ~= nil, "RED: _local_backdrop_geometry must return geometry")

            local backdrop_bottom = geom.y + geom.h
            local expected_bottom = ph - 24 * e

            _backdrop_bottom = backdrop_bottom
            _expected_bottom = expected_bottom
            _bottom_within = math.abs(backdrop_bottom - expected_bottom) <= 0.5

            local p_root = P._root
            assert(p_root ~= nil and alive(p_root), "P._root must exist")
            local p_right = p_root:x() + p_root:w()
            local expected_right = pw - 40 * e

            _p_right = p_right
            _expected_right = expected_right
            _right_within = math.abs(p_right - expected_right) <= 0.5

            local p_bottom = p_root:y() + p_root:h()
            _p_bottom = p_bottom
            _p_vis = p_root:visible()

            local w_root = W._root
            _w_vis = w_root ~= nil and alive(w_root) and w_root:visible()

            local e_root = E._root
            _e_vis = e_root ~= nil and alive(e_root) and e_root:visible()

            _pw = pw
            _ph = ph
            _e = e
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._p_vis), "P._root must be visible")
        self.assertTrue(bool(g._w_vis), "W._root must be visible")
        self.assertTrue(bool(g._e_vis), "E._root must be visible")
        self.assertTrue(bool(g._bottom_within),
            f"RED: shared backdrop bottom {float(g._backdrop_bottom):.2f} must be within 0.5 of parent_h - 24e = {float(g._expected_bottom):.2f}")
        self.assertTrue(bool(g._right_within),
            f"RED: P._root right {float(g._p_right):.2f} must be within 0.5 of w - 40e = {float(g._expected_right):.2f}")


class CrewCardsBottomPlacementTests(unittest.TestCase):
    """Crew cards: each visible card._backdrop world-relative bottom == parent_h - 24e."""

    def test_empty_reserved_space_does_not_raise_cards_above_buffs(self):
        lua = mounted()
        lua.execute(r'''
            local root = C._root
            local first = C._cards[1].root
            local parent = C._parent_panel
            local min_top = math.huge
            for _, card in ipairs(C._cards) do
                if card.root:visible() then
                    min_top = math.min(min_top,root:y()+card.root:y()+card._backdrop:y())
                end
            end
            local buff = parent:panel({name='kyohud_buff_panel'})
            buff:set_shape(0,0,parent:w(),parent:h())
            local icon = buff:rect({name='real_drawn_buff'})
            icon:set_shape(root:x(),root:y()+2,root:w(),12)
            assert(icon:y()+icon:h()<min_top, 'buff must be above actual card bodies')
            kyohud._panel = buff
            RT:update(managers.hud,2,.05)
            _kept_bottom = C:_verify_render() and C._root == root and C._cards[1].root == first
            local e = math.min(parent:w()/1920,parent:h()/1080)*kyohud.settings.hud_scale
            for _, card in ipairs(C._cards) do
                if card.root:visible() then
                    local bottom=root:y()+card.root:y()+card._backdrop:y()+card._backdrop:h()
                    _kept_bottom=_kept_bottom and math.abs(bottom-(parent:h()-24*e))<.5
                end
            end
            _presentations = 0
            for _, card in ipairs(C._cards) do
                local original=card.update
                card.update=function(self,...)
                    _presentations=_presentations+1
                    return original(self,...)
                end
            end
            RT:update(managers.hud,2.6,.05)
            _stable_verified = C:_verify_render()
        ''')
        self.assertTrue(lua.globals()._kept_bottom)
        self.assertTrue(lua.globals()._stable_verified)
        self.assertEqual(lua.globals()._presentations, 3, 'stable cards render once per presentation')

    def test_crew_cards_backdrop_bottom_placement(self):
        """Each visible C card actual _backdrop world-relative bottom == parent_h - 24e.

        Use mounted() from test_hud_crew_acceptance.
        Same card/root primitives after ordinary repeated updates.
        All bots in fixture have tiny artwork at top of 120-high reserved slots.
        Test actual _backdrop, not card_h.
        """
        lua = mounted()
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local C = kyohud.hud.crew
            local parent = RT._parent_panel
            local pw = parent:w()
            local ph = parent:h()
            local scale = kyohud.settings.hud_scale
            local e = math.min(pw / 1920, ph / 1080) * scale

            assert(C:_verify_render(), "C must verify positive")

            local function _world_y(prim)
                local y = prim:y()
                local p = prim:parent()
                while p do
                    y = y + p:y()
                    p = p:parent()
                end
                return y
            end

            local parent_world_y = _world_y(parent)

            _cards_checked = 0
            _all_bottoms_ok = true
            _all_within = true
            _card_results = {}

            for i, card in ipairs(C._cards or {}) do
                if card.root and alive(card.root) and card.root:visible() then
                    _cards_checked = _cards_checked + 1
                    local bd = card._backdrop
                    if bd and alive(bd) then
                        local bd_world_y = _world_y(bd)
                        local bd_h = bd:h()
                        local bd_bottom = bd_world_y + bd_h - parent_world_y
                        local expected_bottom = ph - 24 * e
                        local within = math.abs(bd_bottom - expected_bottom) <= 0.5

                        local card_root = card.root
                        local card_root_world_y = _world_y(card_root)
                        local card_root_h = card_root:h()
                        local card_root_bottom = card_root_world_y + card_root_h - parent_world_y

                        _card_results[i] = {
                            bd_bottom = bd_bottom,
                            expected_bottom = expected_bottom,
                            within = within,
                            card_root_bottom = card_root_bottom,
                            card_h = card._geo and card._geo.h or 0,
                            bd_h = bd_h,
                        }

                        if not within then
                            _all_bottoms_ok = false
                        end
                    else
                        _all_bottoms_ok = false
                    end
                end
            end

            _root_before = C._root
            _card1_before = C._cards and C._cards[1]

            for _ = 1, 5 do
                RT:update(managers.hud, 1.5 + _ * 0.05, 0.05)
            end

            _same_root = C._root == _root_before
            _same_card1 = C._cards and C._cards[1] == _card1_before
            _still_verified = C:_verify_render()
        ''')
        g = lua.globals()
        self.assertGreater(int(g._cards_checked), 0, "RED: at least one card must be checked")
        self.assertTrue(bool(g._all_bottoms_ok),
            "RED: all visible card._backdrop bottoms must be within 0.5 of parent_h - 24e")
        self.assertTrue(bool(g._same_root), "RED: root primitive preserved after updates")
        self.assertTrue(bool(g._same_card1), "RED: card1 primitive preserved after updates")
        self.assertTrue(bool(g._still_verified), "RED: crew still verified after updates")

        results = lua.eval('_card_results') or {}
        for i, result in results.items():
            idx = int(i) if not isinstance(i, int) else i
            with self.subTest(card=idx):
                self.assertTrue(bool(result['within']),
                    f"card {idx} backdrop bottom {float(result['bd_bottom']):.2f} "
                    f"must equal parent_h - 24e = {float(result['expected_bottom']):.2f}")


class NativeHUDTempBagPanelOverlapTests(unittest.TestCase):
    """Native HUDTemp bag_panel overlap: fallback when overlapping foreground."""

    def test_native_bag_panel_overlap_fallback(self):
        """Native HUDTemp bag_panel at x=w-360e, y=h-300e, w=320e, h=110e with throw_instruction above.

        Use _radial_runtime for real composed runtime/data.
        Enable AFTER known positive.
        Monotonically update 2.2.
        P/W/E roots/backdrop remain verified visible and native bag/throw unchanged.
        While all visible bottom/right assertions hold.
        Native truly overlapping actual drawn foreground still yields fallback.
        """
        lua = _radial_runtime()
        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local P = kyohud.hud.player
            local W = kyohud.hud.weapons
            local E = kyohud.hud.equipment
            local parent = RT._parent_panel
            local pw = parent:w()
            local ph = parent:h()
            local scale = kyohud.settings.hud_scale
            local e = math.min(pw / 1920, ph / 1080) * scale

            assert(P:verify(), "P must verify positive before native")
            for _, hook in ipairs(Hooks._all) do
                if hook.id == 'KyohHUD_Actors_Condition' then
                    hook.fn(managers.hud,HUDManager.PLAYER_PANEL,'mugshot_normal','')
                end
            end
            assert(W:verify(), "W must verify positive before native")
            assert(E:verify(), "E must verify positive before native")
            assert(RT:_verify_local_backdrop(), "backdrop must verify before native")

            local bag_panel = parent:panel({name="bag_panel"})
            bag_panel:set_shape(pw - 360 * e, ph - 300 * e, 320 * e, 110 * e)
            bag_panel:set_visible(true)

            local throw_instruction = parent:text({name="throw_instruction", text="Throw"})
            throw_instruction:set_shape(pw - 360 * e, ph - 300 * e - 30 * e, 100 * e, 24 * e)
            throw_instruction:set_visible(true)

            local mgr = managers.hud
            mgr._hud_temp = mgr._hud_temp or {}
            mgr._hud_temp._temp_panel = parent

            local bag_x_before = bag_panel:x()
            local bag_y_before = bag_panel:y()
            local bag_w_before = bag_panel:w()
            local bag_h_before = bag_panel:h()
            local bag_vis_before = bag_panel:visible()

            local throw_x_before = throw_instruction:x()
            local throw_y_before = throw_instruction:y()
            local throw_vis_before = throw_instruction:visible()

            RT:update(mgr, 2.2, 0.05)

            local p_vis_after = P._root:visible()
            local w_vis_after = W._root:visible()
            local e_vis_after = E._root:visible()
            local backdrop_vis_after = RT:_verify_local_backdrop()

            local bag_x_after = bag_panel:x()
            local bag_y_after = bag_panel:y()
            local bag_w_after = bag_panel:w()
            local bag_h_after = bag_panel:h()
            local bag_vis_after_native = bag_panel:visible()

            local throw_x_after = throw_instruction:x()
            local throw_y_after = throw_instruction:y()
            local throw_vis_after_native = throw_instruction:visible()

            local p_right = P._root:x() + P._root:w()
            local expected_p_right = pw - 40 * e
            local p_right_within = math.abs(p_right - expected_p_right) <= 0.5

            local geom = RT:_local_backdrop_geometry()
            local backdrop_bottom = geom and (geom.y + geom.h) or 0
            local expected_bottom = ph - 24 * e
            local backdrop_within = geom and math.abs(backdrop_bottom - expected_bottom) <= 0.5 or false

            _p_vis = p_vis_after
            _w_vis = w_vis_after
            _e_vis = e_vis_after
            _backdrop_vis = backdrop_vis_after

            _bag_unchanged = bag_x_after == bag_x_before
                and bag_y_after == bag_y_before
                and bag_w_after == bag_w_before
                and bag_h_after == bag_h_before
                and bag_vis_after_native == bag_vis_before

            _throw_unchanged = throw_x_after == throw_x_before
                and throw_y_after == throw_y_before
                and throw_vis_after_native == throw_vis_before

            _p_right_within = p_right_within
            _backdrop_within = backdrop_within

            _p_verify = P:verify()
            _w_verify = W:verify()
            _e_verify = E:verify()
            local original_player = P._root
            bag_panel:set_shape(P._root:x(), P._root:y()+P._gauge.root:y(),100*e,24*e)
            RT:update(mgr,2.8,.05)
            _real_overlap_falls_back = not P._root:visible() and not W._root:visible()
            bag_panel:set_visible(false)
            throw_instruction:set_visible(false)
            RT:update(mgr,3.4,.05)
            _recovers_same = P._root == original_player and P._root:visible()
                and P:verify() and W:verify() and E:verify()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._p_vis), "P._root must remain visible")
        self.assertTrue(bool(g._w_vis), "W._root must remain visible")
        self.assertTrue(bool(g._e_vis), "E._root must remain visible")
        self.assertTrue(bool(g._backdrop_vis), "backdrop must remain verified")
        self.assertTrue(bool(g._bag_unchanged), "RED: native bag_panel must be unchanged")
        self.assertTrue(bool(g._throw_unchanged), "RED: native throw_instruction must be unchanged")
        self.assertTrue(bool(g._p_right_within), "RED: P._root right must still be w - 40e")
        self.assertTrue(bool(g._backdrop_within), "RED: backdrop bottom must still be parent_h - 24e")
        self.assertTrue(bool(g._p_verify), "P must still verify")
        self.assertTrue(bool(g._w_verify), "W must still verify")
        self.assertTrue(bool(g._e_verify), "E must still verify")
        self.assertTrue(g._real_overlap_falls_back)
        self.assertTrue(g._recovers_same)


if __name__ == "__main__":
    unittest.main()
