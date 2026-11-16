"""Runtime recharge animation cost regression (TEST ONLY).

The 600 ``Color`` constructions and 900 redundant
``set_color``/``set_alpha``/``set_layer`` writes were measured in the first
vertical implementation before style optimization, not in the original
horizontal installed baseline: that baseline's 100-animation diagnostic had 0
style writes and 100 ``set_shape`` calls, while the final vertical path does 400
shape plus 200 clear plus 200 add_triangles, and ``Color`` went from 600 on the
original horizontal path to 0. This tracer requires zero ``Color`` and zero
redundant style writes so the first vertical regression does not return,
preserving 200 spied ``_verify_cell`` reads and 400 ``text_rect`` getter calls
per loop, not FPS; it claims no FPS or net native-call reduction.
The geometry test keeps the same-table, invalidation, restore and verification/
corruption primitives as the present regression contract; no production code is touched here.
"""
import unittest

from test_hud_equipment_recharge_vertical import (
    _presentation_with_vertical_fixture,
    RUNTIME_SETUP,
)


class EquipmentRechargeAnimationCostTests(unittest.TestCase):
    def test_100_animations_construct_no_colors_and_write_no_redundant_style(self):
        lua = _presentation_with_vertical_fixture()
        lua.execute(RUNTIME_SETUP + r'''
            _game_clock:set_time(1000)
            RT:update(managers.hud, 1, 0.06)

            local row = E._rows[4]
            local reveal = row and row._recharge_reveal
            assert(row and reveal and E:verify(), 'precondition: qualified positive row')
            assert(row._value:text() == '17s', 'precondition: positive value 17s')
            assert(row._progress ~= nil and row._progress > 0,
                'precondition: positive progress')

            local function kids(p)
                local out = {}
                for _, child in pairs(p:children()) do out[#out + 1] = child end
                return out
            end
            local children = kids(reveal)
            assert(#children == 3, 'precondition: three owned reveal children')
            local root_before, root_count = {}, 0
            for _, child in pairs(row._root:children()) do
                root_before[child] = true
                root_count = root_count + 1
            end
            local bg, cut, left = row._reveal_bg, row._reveal_cut, row._reveal_left
            local reveal_before, value_before = row._recharge_reveal, row._value

            assert(type(Color) == 'function', 'fixture Color must be a function')
            local base_color = Color
            _G._color_calls = 0
            Color = function(...)
                _G._color_calls = _G._color_calls + 1
                return base_color(...)
            end

            local row_mt = getmetatable(row)
            assert(type(row_mt) == 'table' and type(row_mt._verify_cell) == 'function',
                'row metatable must expose _verify_cell')
            local base_verify = row_mt._verify_cell
            _G._verify_calls = 0
            row_mt._verify_cell = function(self)
                _G._verify_calls = _G._verify_calls + 1
                return base_verify(self)
            end

            local panel_mt = getmetatable(row._value)
            assert(type(panel_mt) == 'table' and type(panel_mt.text_rect) == 'function',
                'panel metatable must expose the actual text_rect getter')
            local base_text_rect = panel_mt.text_rect
            _G._text_rect_calls = 0
            panel_mt.text_rect = function(self)
                _G._text_rect_calls = _G._text_rect_calls + 1
                return base_text_rect(self)
            end

            _G._setter_calls = 0
            for _, child in ipairs(children) do
                for _, name in ipairs({'set_color', 'set_alpha', 'set_layer'}) do
                    local base = child[name]
                    assert(type(base) == 'function', 'actual setter required: ' .. name)
                    child[name] = function(self, value)
                        _G._setter_calls = _G._setter_calls + 1
                        return base(self, value)
                    end
                end
            end

            _G._vector3_calls = 0
            for i = 1, 100 do
                _game_clock:set_time(1000 + i * 0.001)
                E:_animate_recharge()
            end

            local after = kids(reveal)
            local children_ok = #after == #children
            for i, child in ipairs(children) do
                if after[i] ~= child then children_ok = false end
            end
            local root_ok, after_root_count = true, 0
            for _, child in pairs(row._root:children()) do
                after_root_count = after_root_count + 1
                if not root_before[child] then root_ok = false end
            end
            _G._identity_ok = children_ok and root_ok
                and after_root_count == root_count
                and row._recharge_reveal == reveal_before
                and row._reveal_bg == bg and row._reveal_cut == cut
                and row._reveal_left == left and row._value == value_before
        ''')
        g = lua.globals()
        counters = (
            ('identity', bool(g._identity_ok), True,
             'animation must retain every reveal child, root primitive and row reference'),
            ('verify_calls', int(g._verify_calls), 200,
             'every animation must keep exactly pre/post _verify_cell certification'),
            ('text_rect_calls', int(g._text_rect_calls), 400,
             'certification must use the actual label/value text_rect getters'),
            ('vector3_calls', int(g._vector3_calls), 0,
             'animation must not allocate new Vector3 payloads'),
            ('color_calls', int(g._color_calls), 0,
             'animation must not construct Color objects for certification style'),
            ('setter_calls', int(g._setter_calls), 0,
             'fresh pre-verify already proves style; reveal setters must not repeat it'),
        )
        for name, actual, expected, message in counters:
            with self.subTest(counter=name):
                self.assertEqual(actual, expected, message)


class EquipmentRechargeCellShapesCacheTests(unittest.TestCase):
    def test_cell_shapes_cache_invalidation_and_corruption_recovery(self):
        lua = _presentation_with_vertical_fixture()
        lua.execute(RUNTIME_SETUP + r'''
            _game_clock:set_time(1000)
            RT:update(managers.hud, 1, 0.06)

            local row = E._rows[4]
            assert(row and row:verify(), 'precondition: positive tile row')
            local desc = row._icon_descriptor
            local first = row:_cell_shapes(desc)
            _G._same_table = first == row:_cell_shapes(desc)

            local g = row._geometry
            local x, y, w, h = g.x, g.y, g.w, g.h
            local tile, both = row._tile, row._cell_both
            row:cell_layout(x, y, w + 10, h, tile, both)
            local wider = row:_cell_shapes(desc)
            _G._dims_invalidate = wider ~= first
                and wider.background[3] ~= first.background[3]

            local alt = {texture = desc.texture,
                rect = {desc.rect[1], desc.rect[2], desc.rect[3] * 2, desc.rect[4]}}
            local aspect = row:_cell_shapes(alt)
            _G._aspect_invalidate = aspect ~= wider
                and (aspect.icon[3] ~= wider.icon[3]
                    or aspect.icon[4] ~= wider.icon[4])

            row:cell_layout(x, y, w, h, tile, both)
            local restored = row:_cell_shapes(desc)
            _G._restored_geometry = restored ~= wider
                and restored.background[3] == first.background[3]
                and restored.background[4] == first.background[4]
                and restored.cut[1] == first.cut[1]

            row:render('RECHARGE', '17s', row._progress, true, desc)
            _G._render_verify = row:verify()
            local value, bg = row._value, row._cell_bg
            value:set_text('corrupt')
            _G._text_rejected = not row:verify()
            value:set_text('17s')
            bg:set_color(Color(1, 0, 0))
            _G._style_rejected = not row:verify()
            row:render('RECHARGE', '17s', row._progress, true, desc)
            _G._recovery_same = row._value == value and row._cell_bg == bg
                and row:verify()
        ''')
        g = lua.globals()
        checks = (
            ('same_table', bool(g._same_table),
             '_cell_shapes must return the same cached table for equal inputs'),
            ('dims_invalidate', bool(g._dims_invalidate),
             'different row dimensions must invalidate the cached shape table'),
            ('aspect_invalidate', bool(g._aspect_invalidate),
             'different icon aspect must invalidate the cached shape table'),
            ('restored_geometry', bool(g._restored_geometry),
             'restoring the original dimensions must restore the original geometry'),
            ('render_verify', bool(g._render_verify),
             'the restored row must render and certify positively'),
            ('text_rejected', bool(g._text_rejected),
             'corrupting the actual value text must still fail certification'),
            ('style_rejected', bool(g._style_rejected),
             'corrupting the actual cell style must still fail certification'),
            ('recovery_same', bool(g._recovery_same),
             'recovery must keep the same value/background primitives and certify'),
        )
        for name, ok, message in checks:
            with self.subTest(check=name):
                self.assertTrue(ok, message)


if __name__ == '__main__':
    unittest.main()
