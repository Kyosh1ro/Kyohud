"""Slice A -- shared backdrop and revised E composition (RED tracer).

Approved A contract:
- layout.local_loadout w380e h102e
- player root w380e, gauge actual w300e (downs reserve 80)
- SAME font physical as before using explicit gauge reference_scale ge=(360/440)*e
- numbers 24ge and heart 16e
- Weapons: native 2 left 1 right, no individual background visible
- active 60/22, inactive 24/15
- equipment right, gap 2e
- all cells oblique both left and right
- cell body y12e h80e (root loadout 102 minus padding 12+10)
- qty 20e unchanged
- Both deployables values 2 and 3|2 and frag 2 retained 4 cells
- Shared backdrop: NEW owner runtime._local_bg_panel (layer -1)
- _local_bg_body rect x6e w(bgw-12e), _local_bg_cut rounded full bgw radius 6e
- _local_backdrop_verified flag and method _verify_local_backdrop()
- ONLY shown when all 3 modules enabled+certified+visible
- absent/failed sibling => hide common immediately, native untouched
- Shared background root w382e, body x6e w(bgw-12e), cut full bgw rounded radius 6e, height same
- color RGB 8/255 9/255 11/255 alpha .86 once
- common bottom covers player numeric boxes plus 14e padding, top=loadout y

RED until implementation updated in runtime.lua and layout.lua.
"""
import unittest
from test_hud_final_integration import _crew_lua

SETUP = r'''
kyohud.settings.enable_hud_foundation=true
kyohud.settings.enable_player=true
kyohud.settings.enable_weapons=true
kyohud.settings.enable_equipment=true
kyohud.settings.enable_crew=false
kyohud.settings.hud_scale=1.0
_G.panel_double:set_shape(0,0,1920,1080)
managers.player.current_state=function() return 'standard' end
u1,b1=make_weapon('new_m1014');b1:_native_set_ammo(8,6,32,40);b1:_native_set_fire_mode('auto')
u2,b2=make_weapon('new_m16');b2:_native_set_ammo(30,25,120,150);b2:_native_set_fire_mode('single')
inventory:_native_set_slot(1,u1);inventory:_native_set_slot(2,u2)
inventory:_native_set_equipped(2)
managers.player:_native_set_equipment('doctor_bag',{2})
managers.player:_native_set_equipment('trip_mine',{3,2})
managers.player._equipment.selected_index=1
managers.player:_native_set_grenades('frag',2,2)
_native_set_projectile_tweak('frag',{throwable=true})
managers.player:_native_set_specials('cable_tie',{3})
DB={has=function() return true end}
Idstring=function(s) return s end
RT=kyohud.hud.runtime;W=kyohud.hud.weapons;E=kyohud.hud.equipment;P=kyohud.hud.player
RT:refresh_settings(managers.hud)
RT:update(managers.hud,1,.06)
'''


def mounted():
    lua, *present = _crew_lua()
    assert all(present)
    lua.execute(SETUP)
    return lua


class RevisedECompositionTests(unittest.TestCase):

    def test_workspace_scale_matrix_revised_dimensions(self):
        for width, height in ((1920, 1080), (1680, 1050), (1280, 720)):
            for scale in (.95, 1, 1.0041298879984, 1.05):
                with self.subTest(width=width, height=height, scale=scale):
                    lua = mounted()
                    lua.globals().pw = width
                    lua.globals().ph = height
                    lua.globals().requested_scale = scale
                    lua.execute(r'''
                        RT._parent_panel:set_shape(0, 0, pw, ph)
                        kyohud.settings.hud_scale = requested_scale
                        RT:refresh_settings(managers.hud)
                        RT:update(managers.hud, 2, .06)
                        local e = math.min(pw / 1920, ph / 1080) * requested_scale
                        local ge = (360 / 440) * e
                        assert(W:verify() and E:verify() and P:verify(), 'RED: all 3 certify')
                        assert(math.abs(W._root:w() - 380 * e) < .05, 'RED: weapons w380e')
                        assert(math.abs(W._root:h() - 102 * e) < .05, 'RED: weapons h102e')
                        assert(math.abs(P._root:w() - 380 * e) < .05, 'RED: player w380e')
                        assert(math.abs(P._gauge.root:w() - 300 * e) < .05, 'RED: gauge w300e')
                        local fs = P._gauge.health_text:font_size()
                        assert(math.abs(fs - 24 * ge) < .1, 'RED: numbers 24ge')
                        local icon_h = P._downs_icon:h()
                        assert(math.abs(icon_h - 16 * e) < .05, 'RED: heart 16e')
                        for i = 1, 2 do
                            local cell_h = W._cards[i]._root:h()
                            assert(math.abs(cell_h - 80 * e) < .05, 'RED: cell body h80e')
                            local cell_y = W._cards[i]._root:y()
                            assert(math.abs(cell_y - 12 * e) < .05, 'RED: cell body y12e')
                        end
                        for i = 1, 3 do
                            local prev = E._rows[i]._root
                            local nxt = E._rows[i+1]._root
                            local cell_gap = nxt:x() - (prev:x() + prev:w())
                            assert(math.abs(cell_gap - 2 * e) < .05, 'RED: equipment cell gap 2e')
                        end
                        assert(E._rows[1]._root:visible() and E._rows[1]._value:text() == '2', 'RED: row1 value 2')
                        assert(E._rows[2]._root:visible() and E._rows[2]._value:text() == '3|2', 'RED: row2 value 3|2')
                        assert(E._rows[3]._root:visible(), 'RED: row3 visible')
                        assert(E._rows[4]._root:visible() and E._rows[4]._value:text() == '2', 'RED: row4 value 2')
                        assert(E._root:x() + E._root:w() <= W._root:x() + W._root:w() + .05, 'RED: E root right <= W root right')
                        local card1_gap = E._root:x() - (W._root:x() + W._cards[1]._root:x() + W._cards[1]._root:w())
                        assert(math.abs(card1_gap - 4 * e) < .05, 'RED: gap to card1 right 4e')
                        assert(math.abs(E._rows[1]._value:font_size() - 20 * e) < .1, 'RED: qty 20e')
                        local bg = RT._local_bg_panel
                        assert(bg ~= nil, 'RED: shared backdrop exists')
                        assert(bg:layer() == -1, 'RED: backdrop layer -1')
                        assert(math.abs(bg:w() - 382 * e) < .05, 'RED: backdrop w382e')
                        local body = RT._local_bg_body
                        local cut = RT._local_bg_cut
                        assert(math.abs(body:x() - 6 * e) < .05, 'RED: body x6e')
                        assert(math.abs(body:w() - (382 * e - 12 * e)) < .05, 'RED: body w bgw-12e')
                        assert(math.abs(cut:w() - 382 * e) < .05, 'RED: cut full bgw')
                        local bc = body:color()
                        assert(bc and math.abs(bc.r - 8/255) < .005 and math.abs(bc.g - 9/255) < .005 and math.abs(bc.b - 11/255) < .005, 'RED: body color RGB')
                        assert(math.abs(body:alpha() - .86) < .005, 'RED: body alpha .86')
                        local cc = cut:color()
                        assert(cc and math.abs(cc.r - 8/255) < .005 and math.abs(cc.g - 9/255) < .005 and math.abs(cc.b - 11/255) < .005, 'RED: cut color RGB')
                        assert(math.abs(cut:alpha() - .86) < .005, 'RED: cut alpha .86')
                        for i = 1, 4 do
                            assert(E._rows[i]._cell_cut and E._rows[i]._cell_cut:visible(), 'RED: cell right cut '..i)
                            assert(E._rows[i]._cell_left_cut and E._rows[i]._cell_left_cut:visible(), 'RED: cell left cut '..i)
                        end
                        for i = 1, 2 do
                            assert(not W._cards[i]._background:visible(), 'RED: weapon bg hidden '..i)
                        end
                        local active_card = W._cards[2]
                        local max_bottom = 0
                        for _, prim in ipairs({active_card._clip_text, active_card._reserve_text, active_card._mode_text}) do
                            max_bottom = math.max(max_bottom, prim:y() + prim:h())
                        end
                        assert(max_bottom <= 80 * e + .05, 'RED: active content fits 80h')
                        assert(RT:_verify_local_backdrop(), 'RED: backdrop verified')
                    ''')

    def test_toggle_hides_common_and_recovery_preserves_objects(self):
        lua = mounted()
        lua.execute(r'''
            assert(RT:_verify_local_backdrop(), 'RED: initial backdrop verified')
            local bg = RT._local_bg_panel
            local body = RT._local_bg_body
            local cut = RT._local_bg_cut
            kyohud.settings.enable_weapons = false
            RT:refresh_settings(managers.hud)
            assert(not bg:visible(), 'RED: common hidden when weapons off')
            kyohud.settings.enable_weapons = true
            RT:refresh_settings(managers.hud)
            RT:update(managers.hud, 2, .06)
            assert(bg:visible() and W:verify(), 'RED: common restored')
            assert(RT._local_bg_panel == bg, 'RED: same backdrop panel')
            assert(RT._local_bg_body == body, 'RED: same body primitive')
            assert(RT._local_bg_cut == cut, 'RED: same cut primitive')
        ''')

    def test_source_failure_hides_common_not_others(self):
        lua = mounted()
        lua.execute(r'''
            assert(RT:_verify_local_backdrop(), 'RED: initial verify')
            local bg = RT._local_bg_panel
            local clip = W._cards[2]._clip_text
            clip:set_shape(clip:x()+50, clip:y()+50, clip:w(), clip:h())
            local saved = clip.set_shape
            clip.set_shape = function() end
            RT:update(managers.hud, 2, .06)
            assert(not bg:visible(), 'RED: common hidden on setter failure')
            assert(P:verify() and E:verify(), 'RED: siblings not hidden')
            clip.set_shape = saved
            RT:update(managers.hud, 3, .06)
            assert(bg:visible() and RT:_verify_local_backdrop(), 'RED: recovered')
            assert(RT._local_bg_panel == bg, 'RED: same primitive after recovery')
        ''')

    def test_backdrop_verify_rejects_corrupt_body_then_repairs(self):
        lua = mounted()
        lua.execute(r'''
            assert(RT:_verify_local_backdrop(), 'RED: initial positive')
            local body = RT._local_bg_body
            body:set_shape(body:x() + 50, body:y(), body:w(), body:h())
            assert(not RT:_verify_local_backdrop(), 'RED: corrupt body rejected')
            RT:update(managers.hud, 2, .06)
            assert(RT:_verify_local_backdrop(), 'RED: repaired by update')
            assert(RT._local_bg_body == body, 'RED: same body primitive')
        ''')

    def test_cut_alpha_and_rgb_rejected_then_restored(self):
        lua = mounted()
        lua.execute(r'''
            local cut = RT._local_bg_cut
            cut:set_alpha(0.5)
            assert(not RT:_verify_local_backdrop(), 'RED: cut alpha drift rejected')
            RT:update(managers.hud, 2, .06)
            assert(RT:_verify_local_backdrop(), 'RED: alpha restored')
            cut:set_color(Color(1, 0, 0))
            assert(not RT:_verify_local_backdrop(), 'RED: cut RGB drift rejected')
            RT:update(managers.hud, 3, .06)
            assert(RT:_verify_local_backdrop(), 'RED: RGB restored')
        ''')

    def test_polygon_point_alloc_stable_during_unchanged_updates(self):
        lua = mounted()
        lua.execute(r'''
            local cut = RT._local_bg_cut
            local original_Vector3 = Vector3
            local allocations = 0
            Vector3 = function(...) allocations = allocations + 1; return original_Vector3(...) end
            for i = 1, 5 do
                RT:update(managers.hud, 1 + i * 0.1, 0.06)
                assert(RT:_verify_local_backdrop(), 'RED: backdrop stable')
            end
            assert(allocations == 0, 'RED: no Vector3 allocations')
            assert(RT._local_bg_cut == cut, 'RED: same cut object')
            Vector3 = original_Vector3
        ''')

    def test_foreign_collision_not_adopted(self):
        lua = mounted()
        lua.execute(r'''
            assert(RT:_verify_local_backdrop(), 'RED: initial positive')
            local root = RT._root_panel
            local ownedbg = RT._local_bg_panel
            local savedname = ownedbg:name()
            root:remove(ownedbg)
            RT:_clear_local_backdrop()
            local foreign = root:panel({name = savedname})
            local spy = {set_shape=0, set_layer=0, set_alpha=0, set_color=0, set_visible=0}
            local orig_set_shape = foreign.set_shape
            foreign.set_shape = function(self, ...)
                spy.set_shape = spy.set_shape + 1
                return orig_set_shape(self, ...)
            end
            local orig_set_layer = foreign.set_layer
            foreign.set_layer = function(self, ...)
                spy.set_layer = spy.set_layer + 1
                return orig_set_layer(self, ...)
            end
            local orig_set_alpha = foreign.set_alpha
            foreign.set_alpha = function(self, ...)
                spy.set_alpha = spy.set_alpha + 1
                return orig_set_alpha(self, ...)
            end
            local orig_set_color = foreign.set_color
            foreign.set_color = function(self, ...)
                spy.set_color = spy.set_color + 1
                return orig_set_color(self, ...)
            end
            local orig_set_visible = foreign.set_visible
            foreign.set_visible = function(self, ...)
                spy.set_visible = spy.set_visible + 1
                return orig_set_visible(self, ...)
            end
            RT:update(managers.hud, 2, .06)
            assert(foreign == root:child(savedname), 'RED: foreign identity preserved')
            local total_calls = spy.set_shape + spy.set_layer + spy.set_alpha + spy.set_color + spy.set_visible
            assert(total_calls == 0, 'RED: zero setter calls on foreign')
            local child_count = 0
            for _ in pairs(foreign:children()) do child_count = child_count + 1 end
            assert(child_count == 0, 'RED: zero children under foreign')
            assert(not RT:_verify_local_backdrop(), 'RED: backdrop not verified')
            root:remove(foreign)
            RT:update(managers.hud, 3, .06)
            local newbg = RT._local_bg_panel
            assert(newbg ~= nil, 'RED: own bg created')
            assert(newbg ~= foreign, 'RED: own bg is not foreign')
            assert(RT:_verify_local_backdrop(), 'RED: backdrop verified after recreation')
        ''')

    def test_E_verify_true_but_timers_overlap_cells(self):
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

            local e_cell_wy_before = {}
            local e_cell_root_before = {}
            for i = 1, 4 do
                e_cell_wy_before[i] = E._rows[i]._root:world_y()
                e_cell_root_before[i] = E._rows[i]._root
            end

            local card1_wy = W._cards[1]._root:world_y()
            local card2_wy = W._cards[2]._root:world_y()
            local card1_root = W._cards[1]._root
            local card2_root = W._cards[2]._root

            _game_clock:set_time(1000)
            managers.player:_native_set_grenades('frag', 1, 2)
            _native_set_projectile_tweak('frag', {ability=true, base_cooldown=30})
            managers.player:_native_set_replenish_timer(1017)
            E:refresh(managers.hud)
            dispatch(HUDManager, 'activate_teammate_ability_radial', managers.hud, HUDManager.PLAYER_PANEL, 8, 10)
            E:refresh(managers.hud)
            RT:update(managers.hud, 2, .1)

            assert(P:verify() and W:verify() and E:verify(), 'RED: P/W/E verified')
            assert(RT:_verify_local_backdrop(), 'RED: backdrop verified')

            assert(E._rows[5]._root:visible(), 'RED: RECHARGE row visible')
            assert(E._rows[6]._root:visible(), 'RED: ACTIVE row visible')

            local snap = E:get_snapshot()
            assert(snap.cooldown.active and math.ceil(snap.cooldown.remaining) == 17, 'RED: 17s cooldown')
            assert(snap.activity.active and snap.activity.remaining == 8, 'RED: 8s activity')

            assert(E._rows[5]._value:text() == [[17s]], 'RED: RECHARGE row value text 17s')
            assert(E._rows[6]._value:text() == [[8s]], 'RED: ACTIVE row value text 8s')

            assert(E._rows[1]._value:text() == '2', 'RED: deployable 1 = 2')
            assert(E._rows[2]._value:text() == '3|2', 'RED: deployable 2 = 3|2')

            local first_card_local_y = E._rows[1]._root:y()
            local r5_bottom = E._rows[5]._root:y() + E._rows[5]._root:h()
            local r6_bottom = E._rows[6]._root:y() + E._rows[6]._root:h()
            assert(r5_bottom <= first_card_local_y + .05,
                'RED: RECHARGE bottom ' .. r5_bottom .. ' overlaps card local y ' .. first_card_local_y)
            assert(r6_bottom <= first_card_local_y + .05,
                'RED: ACTIVE bottom ' .. r6_bottom .. ' overlaps card local y ' .. first_card_local_y)

            local r5_top = E._rows[5]._root:y()
            local r6_top = E._rows[6]._root:y()
            assert(r5_bottom <= r6_top + .05 or r6_bottom <= r5_top + .05,
                'RED: temporal rows mutually overlap')

            for i = 1, 4 do
                assert(math.abs(E._rows[i]._root:world_y() - e_cell_wy_before[i]) < .05,
                    'RED: E cell ' .. i .. ' world y changed after activation')
                assert(E._rows[i]._root == e_cell_root_before[i],
                    'RED: E cell ' .. i .. ' identity lost after activation')
            end

            assert(math.abs(W._cards[1]._root:world_y() - card1_wy) < .05, 'RED: card1 world y changed')
            assert(math.abs(W._cards[2]._root:world_y() - card2_wy) < .05, 'RED: card2 world y changed')

            local bg = RT._local_bg_panel
            local bg_top = bg:world_y()
            local bg_bottom = bg:world_y() + bg:h()
            local e_wy = E._root:world_y()
            local player_bottom = P._root:world_y() + P._gauge.root:y() + P._gauge._health_value_bg:y() + P._gauge._health_value_bg:h()
            assert(bg_top <= e_wy + .05, 'RED: backdrop top ' .. bg_top .. ' > E root y ' .. e_wy)
            assert(bg_bottom >= player_bottom - .05, 'RED: backdrop bottom ' .. bg_bottom .. ' < player bottom ' .. player_bottom)

            _game_clock:set_time(1040)
            E:refresh(managers.hud)
            RT:update(managers.hud, 3, .1)

            assert(not E._rows[5]._root:visible(), 'RED: RECHARGE should be hidden after expiry')
            assert(not E._rows[6]._root:visible(), 'RED: ACTIVE should be hidden after expiry')

            for i = 1, 4 do
                assert(math.abs(E._rows[i]._root:world_y() - e_cell_wy_before[i]) < .05,
                    'RED: E cell ' .. i .. ' world y changed after expiry')
                assert(E._rows[i]._root == e_cell_root_before[i],
                    'RED: E cell ' .. i .. ' identity lost after expiry')
            end

            assert(math.abs(W._cards[1]._root:world_y() - card1_wy) < .05, 'RED: card1 world y changed after expiry')
            assert(math.abs(W._cards[2]._root:world_y() - card2_wy) < .05, 'RED: card2 world y changed after expiry')

            assert(math.abs(E._root:world_y() - W._root:world_y()) < .05,
                'RED: E root y ' .. E._root:world_y() .. ' ~= W root y ' .. W._root:world_y() .. ' (empty temporal reservation)')

            assert(W._cards[1]._root == card1_root, 'RED: card1 identity lost')
            assert(W._cards[2]._root == card2_root, 'RED: card2 identity lost')

            assert(P:verify() and W:verify() and E:verify(), 'RED: P/W/E verify after expiry')
            assert(RT:_verify_local_backdrop(), 'RED: backdrop verified after expiry')
        ''')

    def test_strict_readback_body_mutations_repaired(self):
        lua = mounted()
        lua.execute(r'''
            assert(RT:_verify_local_backdrop(), 'RED: initial positive')
            local body = RT._local_bg_body
            local cut = RT._local_bg_cut
            local mutations = {
                {name='visible_false', fn=function() body:set_visible(false) end},
                {name='layer_9', fn=function() body:set_layer(9) end},
                {name='shape_nan_x', fn=function() body:set_shape(0/0, body:y(), body:w(), body:h()) end},
                {name='alpha_nan', fn=function() body:set_alpha(0/0) end},
                {name='color_nan_r', fn=function() body:set_color(Color(0/0, 0, 0)) end},
                {name='cut_layer_9', fn=function() cut:set_layer(9) end},
            }
            for i, mut in ipairs(mutations) do
                mut.fn()
                assert(not RT:_verify_local_backdrop(), 'RED: ' .. mut.name .. ' rejected')
                RT:update(managers.hud, 2 + i * 0.1, .06)
                assert(RT:_verify_local_backdrop(), 'RED: ' .. mut.name .. ' repaired')
                assert(RT._local_bg_body == body, 'RED: same body after ' .. mut.name)
                assert(RT._local_bg_cut == cut, 'RED: same cut after ' .. mut.name)
            end
        ''')


if __name__ == '__main__':
    unittest.main()
