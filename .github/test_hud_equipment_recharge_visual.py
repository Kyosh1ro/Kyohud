"""Vertically clipped orange recharge reveal and raw projectile icon default rect.

The tile row must expose an owned `_recharge_reveal` panel (layer 1) whose
width is the full row width, whose height is `row_height * progress`, and whose
y is `row_height * (1 - progress)`. Its silhouette children are genuinely
clipped to that local box: the background and left cut keep their widths but use
`row_height * progress`, while the right cut uses `cut_width * progress`; all
three use the KILLFEED_SCORE_COLOR orange (1, 0.63, 0.12) at alpha 0.4 and stay
anchored relative to the retained reveal. The thin `_track`/`_fill` strip is
hidden in the tile path only. The seconds text must be centered through the
native `set_align`/`align` methods. Standalone rows keep the legacy thin strip.

The projectile icon path must forward the native 32x32 default rectangle for a
raw texture path (`HUDTeammate:set_grenades` lines 1971-1976) instead of
replacing the raw hacker texture with `equipment_ecm_jammer`.
"""
import unittest

import test_hud_equipment_presentation as presentation_module
from test_hud_equipment_presentation import presentation

TEXT_ALIGN_FIXTURE = r'''
    local proto = getmetatable(panel_double)
    if proto then
        function proto:set_align(value) self._align = value end
        function proto:align() return self._align end
    end
'''


def _presentation_with_text_align():
    """Reuse presentation() with test-only native text alignment methods."""
    original = presentation_module._lua_with_weapons_runtime

    def wrapped():
        lua, weapons_exists, player_exists = original()
        lua.execute(TEXT_ALIGN_FIXTURE)
        return lua, weapons_exists, player_exists

    presentation_module._lua_with_weapons_runtime = wrapped
    try:
        return presentation()
    finally:
        presentation_module._lua_with_weapons_runtime = original


class EquipmentRechargeRevealVisualTests(unittest.TestCase):
    def test_vertical_orange_silhouette_fills_bottom_up_and_hides_thin_strip(self):
        lua = _presentation_with_text_align()
        lua.execute(r'''
            tweak_data.hud_icons = {
                get_icon_data = function(self, id, default_rect)
                    if id == 'fixture_grenade' then
                        return 'guis/textures/pd2/equip_icons', {128, 0, 32, 32}
                    end
                    return id, default_rect or {0, 0, 48, 48}
                end,
            }
            DB = {has = function() return true end}
            Idstring = function(value) return value end
            tweak_data.blackmarket.projectiles.pocket.icon = 'fixture_grenade'
            E._icon_cache = nil
            E:refresh(managers.hud)
            E:_present()

            _game_clock:set_time(1000)
            managers.player:_native_set_replenish_timer(1017)
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20})
            RT:update(managers.hud, 1, 0.06)

            local row = E._rows[4]
            assert(row._icon and row._icon:visible(), 'precondition: projectile icon')
            assert(E:get_snapshot().cooldown.integrated == true,
                'precondition: real cooldown qualifier integrates')
            assert(row._value:text() == '1', 'precondition: charge counter 1 at progress 0.15')

            local function close(a, b)
                return type(a) == 'number' and type(b) == 'number'
                    and math.abs(a - b) <= 0.05
            end
            local function fits(p, r)
                return close(p:x(), r[1]) and close(p:y(), r[2])
                    and close(p:w(), r[3]) and close(p:h(), r[4])
            end
            local function kids(p)
                local out = {}
                for _, child in pairs(p:children()) do out[#out + 1] = child end
                return out
            end
            local function assert_orange(child, tag)
                local c = child:color()
                assert(c, tag .. ': silhouette must expose its color')
                assert(close(c.r, 1) and close(c.g, 0.63) and close(c.b, 0.12),
                    tag .. ': silhouette must use KILLFEED_SCORE_COLOR orange')
                assert(type(child:alpha()) == 'number' and close(child:alpha(), 0.4),
                    tag .. ': silhouette alpha must be 0.4')
                assert(child:layer() == 1, tag .. ': silhouette layer must be 1')
                return c
            end

            local saved_children = {}
            local function check_reveal(progress, tag)
                local reveal = row._recharge_reveal
                assert(reveal and reveal:parent() == row._root,
                    tag .. ': required recharge reveal must be owned by the row root')
                assert(reveal:layer() == 1, tag .. ': reveal panel layer must be 1')
                assert(reveal:visible(), tag .. ': reveal must be visible')
                local root_w, root_h = row._root:w(), row._root:h()
                assert(close(reveal:w(), root_w),
                    tag .. ': reveal width must equal the full row width')
                assert(close(reveal:h(), root_h * progress),
                    tag .. ': reveal height must equal row height * progress')
                assert(close(reveal:x(), 0),
                    tag .. ': reveal must anchor at x=0')
                assert(close(reveal:y(), root_h * (1 - progress)),
                    tag .. ': reveal y must equal row height * (1 - progress)')
                assert(row._label:layer() == 2 and row._value:layer() == 2
                    and row._icon:layer() == 2,
                    tag .. ': label/value/icon content must stay on layer 2')

                local shapes = row:_cell_shapes(row._icon_descriptor)
                local fill_h = root_h * progress
                local expected = {
                    reveal_background = {shapes.background[1], 0,
                        shapes.background[3], fill_h},
                    reveal_left = {0, 0, shapes.left[3], fill_h},
                    reveal_cut = {shapes.cut[1], 0,
                        shapes.cut[3] * progress, fill_h},
                }
                local children = kids(reveal)
                assert(#children == 3,
                    tag .. ': reveal must own exactly three clipped silhouette meshes')
                local seen = {}
                for _, child in ipairs(children) do
                    local name = child:name()
                    local expected_shape = expected[name]
                    assert(expected_shape,
                        tag .. ': unexpected reveal child ' .. tostring(name))
                    assert(not seen[name],
                        tag .. ': reveal child ' .. tostring(name) .. ' duplicated')
                    seen[name] = true
                    assert(fits(child, expected_shape),
                        tag .. ': ' .. name .. ' must be clipped to its local reveal box')
                    assert_orange(child, tag .. ' ' .. name)
                    assert(child:visible(), tag .. ': ' .. name .. ' must be visible')
                    local saved = saved_children[name]
                    if saved then
                        assert(saved == child,
                            tag .. ': ' .. name .. ' primitive must be retained')
                    else
                        saved_children[name] = child
                    end
                end
                for name in pairs(expected) do
                    assert(seen[name], tag .. ': missing reveal child ' .. name)
                end
                assert(not row._track:visible(),
                    tag .. ': thin orange track must stay hidden in the tile path')
                assert(not row._fill:visible(),
                    tag .. ': thin orange fill must stay hidden in the tile path')
                assert(row._value:align() == 'center', tag .. ': seconds must be centered')
            end

            check_reveal(0.15, 'progress 0.15')
            local reveal_at_015 = row._recharge_reveal

            _game_clock:set_time(1005)
            RT:update(managers.hud, 1.06, 0.06)
            assert(row._value:text() == '1', 'precondition: charge counter 1 at progress 0.4')
            assert(row._recharge_reveal == reveal_at_015,
                'reveal primitive must be retained while progress advances')
            check_reveal(0.4, 'progress 0.4')

            local component = kyohud.hud.equipment_component
            local standalone = component.new(panel_double, 'standalone_recharge_probe')
            assert(standalone, 'standalone row probe must be created')
            standalone:layout(0, 0, 160, 28)
            standalone:render('RECHARGE', '4s', 0.5, false, nil)
            assert(standalone._track:visible() and standalone._fill:visible(),
                'standalone rows must keep the legacy thin track/fill strip')
            standalone:destroy()
        ''')


    def test_cell_layout_without_both_uses_two_reveal_clones_without_left_cut(self):
        lua = _presentation_with_text_align()
        lua.execute(r'''
            local component = kyohud.hud.equipment_component
            local row = component.new(E._root, 'accepted_cell_probe')
            assert(row, 'accepted cell probe row must be created')
            assert(row:cell_width('1', 1, false), 'probe cell width must be measured')
            row:cell_layout(0, 0, 60, 84, 1, false)
            row:render('label1', '1', 0.5, false)
            assert(row:verify(), 'accepted no-both cell must be certified')

            local reveal = row._recharge_reveal
            assert(reveal, 'accepted no-both cell must own its reveal panel')
            local count = 0
            local names = {}
            for _, child in pairs(reveal:children()) do
                count = count + 1
                names[child:name()] = true
            end
            assert(count == 2,
                'no-both reveal must own exactly background and right cut copies')
            assert(names.reveal_background and names.reveal_cut,
                'no-both reveal must clone background and right cut only')
            assert(row._reveal_left == nil,
                'no-both reveal must not create a left triangle without a left cut')
            row:destroy()

            _game_clock:set_time(1000)
            managers.player:_native_set_replenish_timer(1017)
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20})
            RT:update(managers.hud, 1, 0.06)

            local runtime_row = E._rows[4]
            assert(runtime_row._recharge_reveal and runtime_row:verify(),
                'normal runtime both=true cell must stay certified')
            local runtime_count = 0
            for _ in pairs(runtime_row._recharge_reveal:children()) do
                runtime_count = runtime_count + 1
            end
            assert(runtime_count == 3,
                'normal runtime both=true cell must keep three silhouette copies')
            assert(runtime_row._reveal_left ~= nil,
                'normal runtime both=true cell must keep its left triangle')
        ''')


class EquipmentProjectileIconDefaultRectTests(unittest.TestCase):
    def test_raw_hacker_texture_uses_native_32_default_rect(self):
        lua = _presentation_with_text_align()
        lua.execute(r'''
            local raw = 'guis/dlcs/joy/textures/pd2/hud_pocket_ecm_jammer'
            _captured_default = nil
            tweak_data.hud_icons = {
                get_icon_data = function(self, id, default_rect)
                    if id == raw then
                        _captured_default = default_rect
                        return id, default_rect or {0, 0, 48, 48}
                    end
                    return id, default_rect or {0, 0, 48, 48}
                end,
            }
            DB = {has = function() return true end}
            Idstring = function(value)
                return {key = function(self) return value end}
            end
            _native_set_projectile_tweak('pocket', {
                ability = true,
                base_cooldown = 30,
                icon = raw,
            })
            E._icon_cache = nil
            E:refresh(managers.hud)
            E:_present()

            local row = E._rows[4]
            local descriptor = row._icon_descriptor
            _descriptor_exists = descriptor ~= nil
            _icon_visible = descriptor ~= nil and row._icon ~= nil
                and row._icon:visible()
            _texture = descriptor and descriptor.texture or nil
            _not_ecm_replacement = _texture ~= 'equipment_ecm_jammer'

            local rect = descriptor and descriptor.rect or nil
            _rect_ok = rect ~= nil and rect[1] == 0 and rect[2] == 0
                and rect[3] == 32 and rect[4] == 32
            _rect_w = rect and rect[3] or -1
            _rect_h = rect and rect[4] or -1

            local default_rect = _captured_default
            _default_ok = default_rect ~= nil
                and default_rect[1] == 0 and default_rect[2] == 0
                and default_rect[3] == 32 and default_rect[4] == 32
            _default_w = default_rect and default_rect[3] or -1
            _default_h = default_rect and default_rect[4] or -1
        ''')
        g = lua.globals()
        raw = "guis/dlcs/joy/textures/pd2/hud_pocket_ecm_jammer"
        self.assertTrue(bool(g._descriptor_exists),
            "captured projectile icon descriptor is required")
        self.assertTrue(bool(g._icon_visible), "captured projectile icon must be visible")
        self.assertEqual(g._texture, raw,
            "the actual raw hacker texture path must be preserved")
        self.assertTrue(bool(g._not_ecm_replacement),
            "the raw projectile path must not become equipment_ecm_jammer")
        self.assertTrue(bool(g._rect_ok),
            "captured icon.rect must be {0,0,32,32}")
        self.assertEqual(float(g._rect_w), 32.0,
            "HUDTeammate:set_grenades passes a 32x32 default rect")
        self.assertEqual(float(g._rect_h), 32.0,
            "HUDTeammate:set_grenades passes a 32x32 default rect")
        self.assertTrue(bool(g._default_ok),
            "_icon must forward the native {0,0,32,32} default rect")
        self.assertEqual(float(g._default_w), 32.0,
            "production currently omits default_rect (RED)")
        self.assertEqual(float(g._default_h), 32.0,
            "production currently omits default_rect (RED)")


class EquipmentRechargeAnimationSafetyTests(unittest.TestCase):
    def test_qualified_subframes_animate_reveal_without_cloning(self):
        lua = _presentation_with_text_align()
        lua.execute(r'''
            _game_clock:set_time(1000)
            managers.player:_native_set_replenish_timer(1017)
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20})
            RT:update(managers.hud, 1, 0.06)
            local row = E._rows[4]
            local reveal = row._recharge_reveal
            assert(reveal and row._value:text() == '1' and E:verify(),
                'precondition: qualified 20s event at 17s with charge counter 1')
            local root_h = row._root:h()
            local function kids(p)
                local out = {}
                for _, child in pairs(p:children()) do out[#out + 1] = child end
                return out
            end
            local saved = kids(reveal)
            local function same()
                local now = kids(reveal)
                if #now ~= #saved then return false end
                for _, old in ipairs(saved) do
                    local found = false
                    for _, child in ipairs(now) do
                        if child == old then found = true break end
                    end
                    if not found then return false end
                end
                return E._rows[4] == row and row._recharge_reveal == reveal
                    and row._value:text() == '1'
            end
            _game_clock:set_time(1000.01)
            RT:update(managers.hud, 1.01, 0.01)
            _r1 = reveal:h() / root_h
            _ok1 = math.abs(_r1 - (1 - 16.99 / 20)) <= 1e-6
                and math.abs(reveal:y() - root_h * (16.99 / 20)) <= 1e-6
            _v1, _e1 = E:verify(), same()
            _game_clock:set_time(1000.02)
            RT:update(managers.hud, 1.02, 0.01)
            _r2 = reveal:h() / root_h
            _ok2 = math.abs(_r2 - (1 - 16.98 / 20)) <= 1e-6
                and math.abs(reveal:y() - root_h * (16.98 / 20)) <= 1e-6
            _v2, _same2 = E:verify(), same()
            _s1 = #saved
        ''')
        g = lua.globals()
        self.assertEqual(int(g._s1), 3, "three silhouette clones are mandatory")
        self.assertTrue(bool(g._ok1), "subframe 0.01 reveal height and y must track 16.99s")
        self.assertTrue(bool(g._v1), "equipment must stay certified on subframe")
        self.assertTrue(bool(g._e1), "subframe must retain reveal, children and charge counter 1")
        self.assertTrue(bool(g._ok2), "subframe 0.02 reveal height and y must track 16.98s")
        self.assertTrue(bool(g._v2), "equipment must stay certified on second subframe")
        self.assertTrue(bool(g._same2), "second subframe must not clone reveal children")

    def test_reveal_children_alpha_layer_and_align_are_verified_and_repaired(self):
        lua = _presentation_with_text_align()
        lua.execute(r'''
            _game_clock:set_time(1000)
            managers.player:_native_set_replenish_timer(1017)
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20})
            RT:update(managers.hud, 1, 0.06)
            local row = E._rows[4]
            local reveal, value = row._recharge_reveal, row._value
            local children = {}
            for _, child in pairs(reveal:children()) do children[#children + 1] = child end
            local function same()
                local now = 0
                for _, child in pairs(reveal:children()) do
                    now = now + 1
                    local found = false
                    for _, old in ipairs(children) do
                        if child == old then found = true break end
                    end
                    if not found then return false end
                end
                return now == #children and E._rows[4] == row
                    and row._recharge_reveal == reveal and row._value == value
            end
            _positive = E:verify() and #children == 3
            local mutations = {
                function() reveal:set_alpha(0) end,
                function() children[1]:set_visible(false) end,
                function() children[1]:set_layer(0) end,
                function() value:set_align('left') end,
            }
            _caught, _repaired, _same = true, true, true
            for i, mutate in ipairs(mutations) do
                mutate()
                if E:verify() then _caught = false end
                RT:update(managers.hud, 1 + i * 0.06, 0.06)
                if not E:verify() then _repaired = false end
                if not same() then _same = false end
            end
            local proto = getmetatable(panel_double)
            local align_getter = proto.align
            proto.align = nil
            _missing_caught = E:verify() == false
            proto.align = align_getter
            RT:update(managers.hud, 1.3, 0.06)
            _missing_repaired = E:verify()
            local saved_getter = reveal.children
            local repeated = children[1]
            reveal.children = function() return {repeated, repeated, repeated} end
            _repeated_caught = E:verify() == false
            reveal.children = saved_getter
            _repeated_restored = E:verify()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._positive), "precondition: certified three-copy reveal")
        self.assertTrue(bool(g._caught), "alpha/visible/layer/align corruption must fail verify")
        self.assertTrue(bool(g._repaired), "ordinary update must repair the same primitives")
        self.assertTrue(bool(g._same), "repair must retain reveal, children and value")
        self.assertTrue(bool(g._missing_caught), "missing align getter must fail closed")
        self.assertTrue(bool(g._missing_repaired), "restoring align must certify again")
        self.assertTrue(bool(g._repeated_caught), "three repeats of one child are not all clones")
        self.assertTrue(bool(g._repeated_restored), "restoring children getter must certify")


if __name__ == '__main__':
    unittest.main()
