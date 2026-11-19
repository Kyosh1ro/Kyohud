"""RED regression: stable temporal equipment rows must not rewrite static native state.

`_present_kingpin_activity_event` republishes the same temporal row roughly
112 times per second. Only the displayed value and the fill progress change
between those publications, yet the current `Row:render` temporal path
unconditionally rewrites colors, alphas, visibility, alignment and static
shapes. This test counts real native setter calls on the row primitives during
a second render with unchanged label/selected/icon state and requires a
fill/value-only write budget.
"""
import unittest

from test_hud_equipment_presentation import presentation


class EquipmentTemporalRowRenderWriteTests(unittest.TestCase):
    def test_stable_temporal_rerender_skips_static_native_writes(self):
        lua = presentation()
        lua.execute(r'''
            local proto = getmetatable(panel_double)
            assert(proto, 'panel_double prototype missing')
            function proto:set_align(value) self._align = value end
            function proto:align() return self._align end

            local component = kyohud.hud.equipment_component
            local row = component.new(panel_double, 'row_render_writes_probe')
            assert(row, 'temporal probe row must be created')
            row:layout(0, 0, 160, 28)
            row:render('ACTIVE', '6s', 1.0, false)
            assert(row:verify(), 'first temporal render must certify')

            local setters = {
                'set_shape', 'set_color', 'set_alpha', 'set_visible',
                'set_text', 'set_font_size', 'set_align', 'set_image',
            }
            local writes = 0
            local function wrap(primitive)
                assert(primitive, 'temporal row primitive missing')
                for _, name in ipairs(setters) do
                    local original = primitive[name]
                    if type(original) == 'function' then
                        primitive[name] = function(self, ...)
                            writes = writes + 1
                            return original(self, ...)
                        end
                    end
                end
            end
            for _, primitive in ipairs({
                row._root, row._label, row._value, row._track, row._fill,
            }) do
                wrap(primitive)
            end

            writes = 0
            row:render('ACTIVE', '5s', 0.83, false)
            _stable_render_writes = writes
        ''')
        writes = lua.globals()._stable_render_writes
        self.assertIsNotNone(writes, "the native write counter must be exported")
        self.assertLessEqual(
            int(writes),
            10,
            "a stable temporal re-render must only update the fill and value, "
            f"but it performed {int(writes)} native setter calls",
        )

    def test_track_visibility_repair_on_nil_to_non_nil_progress(self):
        lua = presentation()
        lua.execute(r'''
            local proto = getmetatable(panel_double)
            assert(proto, 'panel_double prototype missing')
            function proto:set_align(value) self._align = value end
            function proto:align() return self._align end

            local component = kyohud.hud.equipment_component
            local row = component.new(panel_double, 'row_track_visibility_probe')
            assert(row, 'temporal probe row must be created')
            row:layout(0, 0, 160, 28)
            row:render('ACTIVE', '--', nil, false)
            assert(row:verify(), 'initial nil-progress render must certify')
            assert(not row._track:visible() and not row._fill:visible(),
                'nil progress must hide both track and fill')

            row:render('ACTIVE', '5s', 0.83, false)
            assert(row._track:visible(),
                'track must become visible when progress becomes non-nil')
            assert(row._fill:visible(),
                'fill must become visible when progress becomes non-nil')
            assert(row:verify(),
                'nil to non-nil progress transition must certify both primitives')
        ''')

    def test_failed_full_render_does_not_commit_static_cache(self):
        lua = presentation()
        lua.execute(r'''
            local proto = getmetatable(panel_double)
            assert(proto, 'panel_double prototype missing')
            function proto:set_align(value) self._align = value end
            function proto:align() return self._align end

            local component = kyohud.hud.equipment_component
            local row = component.new(panel_double, 'row_failed_cache_probe')
            assert(row, 'temporal probe row must be created')
            row:layout(0, 0, 160, 28)

            local label = row._label
            local original = label.set_color
            local threw = false
            label.set_color = function(self, ...)
                if not threw then
                    threw = true
                    error('forced full render failure')
                end
                return original(self, ...)
            end
            row:render('ACTIVE', '5s', 0.83, false)
            assert(threw, 'forced full render must reach the throwing setter')
            label.set_color = original

            row:render('ACTIVE', '5s', 0.83, false)
            assert(row:verify(),
                'restored full render must recertify after the failed attempt')
        ''')


if __name__ == '__main__':
    unittest.main()
