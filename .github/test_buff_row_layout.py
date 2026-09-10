"""Buff-row layout regression tests against the real KyoHUD Lua chunk.

Run: uv run --with lupa python -B -m unittest discover -s .github -p test_buff_row_layout.py -v
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class BuffRowLayoutTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + "/"
        self.lua.execute('''
            Hooks = {callbacks = {}}
            function Hooks:PostHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:PreHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:Add(...) end
            HUDManager = {}; PlayerManager = {}; managers = {}; tweak_data = {}
            function Vector3(...) return {...} end
            function log(...) end
            function alive(x) return x ~= nil end
            local function color(r, g, b)
                return {r = r, g = g, b = b, with_alpha = function(self) return self end}
            end
            Color = setmetatable({white = color(), black = color()}, {
                __call = function(_, ...) return color(...) end
            })
            tweak_data.menu = {}
            game_t = 100
            TimerManager = {game = function() return {time = function() return game_t end} end}
            function assert_row_geometry(layout, total_count, panel_w)
                local epsilon = 0.0001
                assert(layout.visible_count + layout.hidden_count == total_count)
                assert(#layout.positions == layout.slot_count)
                assert(layout.pitch + epsilon >= layout.cell_w or layout.slot_count < 2,
                    'rendered cells overlap')
                for index, position in ipairs(layout.positions) do
                    assert(position.x - layout.cell_w * 0.5 >= 4 - epsilon,
                        'cell exits left edge')
                    assert(position.x + layout.cell_w * 0.5 <= panel_w - 4 + epsilon,
                        'cell exits right edge')
                    if index < #layout.positions then
                        assert(layout.positions[index + 1].x - position.x + epsilon >= layout.cell_w,
                            'adjacent cells overlap')
                    end
                end
                if layout.hidden_count > 0 then
                    assert(layout.slot_count == layout.visible_count + 1)
                    assert(layout.overflow_text == '+' .. tostring(layout.hidden_count))
                else
                    assert(layout.slot_count == layout.visible_count)
                    assert(layout.overflow_text == nil)
                end
            end
        ''')
        self.lua.execute(
            (ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig")
        )

    def test_zero_buffs_returns_empty_layout(self):
        self.lua.execute('''
            local layout = kyohud.compute_buff_row_layout(0, 50, 85, 800, 600, 32, 6, 3, 18)
            assert(layout.visible_count == 0)
            assert(layout.hidden_count == 0)
            assert(layout.slot_count == 0)
            assert(#layout.positions == 0)
            assert(layout.effective_size == 32)
            assert_row_geometry(layout, 0, 800)
        ''')

    def test_one_buff_uses_preferred_size_and_stays_centered(self):
        self.lua.execute('''
            local layout = kyohud.compute_buff_row_layout(1, 50, 85, 800, 600, 32, 6, 3, 18)
            assert(layout.effective_size == 32)
            assert(layout.cell_w == 44)
            assert(layout.gap == 8)
            assert(layout.pitch == 52)
            assert(math.abs(layout.positions[1].x - 400) < 0.0001)
            assert_row_geometry(layout, 1, 800)
        ''')

    def test_normal_row_keeps_preferred_size_and_gap(self):
        self.lua.execute('''
            local layout = kyohud.compute_buff_row_layout(4, 50, 85, 800, 600, 32, 6, 3, 18)
            assert(layout.effective_size == 32)
            assert(layout.frame_pad_x == 6 and layout.frame_pad_y == 3)
            assert(layout.cell_w == 44)
            assert(layout.gap == 8 and layout.pitch == 52)
            assert_row_geometry(layout, 4, 800)
        ''')

    def test_slight_overflow_reduces_gap_only(self):
        self.lua.execute('''
            local layout = kyohud.compute_buff_row_layout(4, 50, 85, 190, 600, 32, 6, 3, 18)
            assert(layout.effective_size == 32)
            assert(layout.cell_w == 44)
            assert(layout.gap > 0 and layout.gap < 8)
            assert(math.abs(layout.pitch - (layout.cell_w + layout.gap)) < 0.0001)
            assert_row_geometry(layout, 4, 190)
        ''')

    def test_wider_row_scales_cells_proportionally(self):
        self.lua.execute('''
            local layout = kyohud.compute_buff_row_layout(6, 50, 85, 200, 600, 32, 6, 3, 18)
            assert(layout.effective_size < 32 and layout.effective_size > 20)
            assert(math.abs(layout.frame_pad_x / layout.effective_size - 6 / 32) < 0.0001)
            assert(math.abs(layout.frame_pad_y / layout.effective_size - 3 / 32) < 0.0001)
            assert(layout.gap == 0 and layout.pitch == layout.cell_w)
            assert(layout.visible_count == 6 and layout.hidden_count == 0)
            assert_row_geometry(layout, 6, 200)
        ''')

    def test_layout_invariants_across_counts_widths_sizes_and_anchors(self):
        self.lua.execute('''
            for _, panel_w in ipairs({40, 80, 160, 320, 800, 1920}) do
                for _, icon_size in ipairs({32, 40}) do
                    for _, x_percent in ipairs({0, 50, 100}) do
                        for count = 0, 100 do
                            local pad_x = math.max(4, math.min(9, icon_size * 0.16))
                            local pad_y = math.max(2, math.min(4, icon_size * 0.08))
                            local layout = kyohud.compute_buff_row_layout(
                                count, x_percent, 85, panel_w, 1080,
                                icon_size, pad_x, pad_y, 35
                            )
                            assert_row_geometry(layout, count, panel_w)
                        end
                    end
                end
            end
        ''')

    def test_extreme_row_reserves_explicit_overflow_cell(self):
        self.lua.execute('''
            local layout = kyohud.compute_buff_row_layout(20, 50, 85, 200, 600, 32, 6, 3, 35)
            assert(layout.effective_size == 20)
            assert(layout.visible_count == 5)
            assert(layout.hidden_count == 15)
            assert(layout.slot_count == 6)
            assert(layout.overflow_text == '+15')
            assert_row_geometry(layout, 20, 200)
        ''')

    def test_row_shifts_inside_left_edge(self):
        self.lua.execute('''
            local layout = kyohud.compute_buff_row_layout(4, 0, 85, 800, 600, 32, 6, 3, 18)
            assert(math.abs(layout.positions[1].x - (4 + layout.cell_w * 0.5)) < 0.0001)
            assert_row_geometry(layout, 4, 800)
        ''')

    def test_row_shifts_inside_right_edge(self):
        self.lua.execute('''
            local layout = kyohud.compute_buff_row_layout(4, 100, 85, 800, 600, 32, 6, 3, 18)
            local last = layout.positions[#layout.positions]
            assert(math.abs(last.x + layout.cell_w * 0.5 - 796) < 0.0001)
            assert_row_geometry(layout, 4, 800)
        ''')

    def test_normal_width_restores_every_buff_without_mutating_state(self):
        self.lua.execute('''
            kyohud.settings = {enable_buffs = true}
            for index = 1, 20 do
                game_t = 100 + index
                kyohud:add_buff('layout_' .. index, {}, 30)
            end
            local buffs = kyohud._buffs
            local extreme = kyohud.compute_buff_row_layout(20, 50, 85, 200, 600, 32, 6, 3, 18)
            local normal = kyohud.compute_buff_row_layout(20, 50, 85, 1200, 600, 32, 6, 3, 18)
            local count = 0
            for _ in pairs(kyohud._buffs) do count = count + 1 end
            assert(extreme.hidden_count > 0)
            assert(normal.visible_count == 20 and normal.hidden_count == 0)
            assert(kyohud._buffs == buffs and count == 20)
            assert_row_geometry(normal, 20, 1200)
        ''')

    def test_refresh_keeps_arrival_order_and_does_not_duplicate(self):
        self.lua.execute('''
            kyohud.settings = {enable_buffs = true}
            game_t = 100
            kyohud:add_buff('first', {}, 30)
            game_t = 101
            kyohud:add_buff('second', {}, 30)
            local first_order = kyohud._buffs.first.order_t
            local second_order = kyohud._buffs.second.order_t
            kyohud.compute_buff_row_layout(20, 50, 85, 200, 600, 32, 6, 3, 18)
            game_t = 102
            kyohud:add_buff('first', {}, 60)
            local count = 0
            for _ in pairs(kyohud._buffs) do count = count + 1 end
            assert(count == 2)
            assert(kyohud._buffs.first.order_t == first_order)
            assert(kyohud._buffs.second.order_t == second_order)
            assert(kyohud._buffs.first.order_t < kyohud._buffs.second.order_t)
        ''')

    def test_draw_uses_layout_and_renders_exact_overflow_count(self):
        self.lua.execute('''
            local panel = {texts = {}, bitmaps = {}, width = 174}
            function panel:clear() self.texts = {}; self.bitmaps = {} end
            function panel:w() return self.width end
            function panel:h() return 600 end
            function panel:gradient(params) return params end
            function panel:rect(params) return params end
            function panel:polyline(params) return params end
            function panel:bitmap(params)
                local bitmap = {
                    params = params,
                    set_color = function() end,
                    set_alpha = function() end,
                }
                self.bitmaps[#self.bitmaps + 1] = bitmap
                return bitmap
            end
            function panel:text(params)
                self.texts[#self.texts + 1] = params
                return {text_rect = function() return 0, 0, 20, 12 end}
            end

            kyohud._panel = panel
            kyohud._buffs = {}
            kyohud._kills = {}
            HUDList = {BuffItemBase = {MAP = {
                equipped_perk_deck = {ignore = true},
            }}}
            kyohud._gameinfo_bridge_active = true
            kyohud.settings = {
                enable_buffs = true,
                enable_killfeed = false,
                icon_size = 32,
                opacity = 0.9,
                buff_position_x = 50,
                buff_position_y = 85,
                circle_radius = 250,
            }
            for index = 1, 20 do
                game_t = 100 + index
                kyohud:add_buff('draw_' .. index, {texture = 'buff/' .. index}, nil, nil, true)
            end
            local expected = kyohud.compute_buff_row_layout(
                20, 50, 85, 174, 600, 32, 32 * 0.16, 32 * 0.08, 18
            )
            kyohud:draw()

            local overflow_count = 0
            local rendered_text = {}
            for _, text in ipairs(panel.texts) do
                rendered_text[#rendered_text + 1] = tostring(text.text)
                if text.text == expected.overflow_text then
                    overflow_count = overflow_count + 1
                    assert(text.color.r == 0.52 and text.color.g == 0.88 and text.color.b == 0.92,
                        'overflow indicator does not use the cyan HUD accent')
                end
            end
            assert(#panel.bitmaps == expected.visible_count,
                'draw did not limit real buff cells')
            assert(overflow_count == 1,
                'expected ' .. tostring(expected.overflow_text)
                    .. ', rendered: ' .. table.concat(rendered_text, ', '))
            assert(panel.bitmaps[1].params.w == 20 and panel.bitmaps[1].params.h == 20,
                'draw ignored effective layout size')
            for index, bitmap in ipairs(panel.bitmaps) do
                assert(bitmap.params.texture == 'buff/' .. index,
                    'draw changed arrival order while adapting the row')
            end
            local count = 0
            for _ in pairs(kyohud._buffs) do count = count + 1 end
            assert(count == 20, 'draw removed hidden buff state')

            panel.width = 1200
            kyohud:draw()
            assert(#panel.bitmaps == 20, 'hidden buffs did not reappear')
            for _, text in ipairs(panel.texts) do
                assert(string.sub(tostring(text.text), 1, 1) ~= '+',
                    'overflow indicator remained after recovery')
            end
            count = 0
            for _ in pairs(kyohud._buffs) do count = count + 1 end
            assert(count == 20, 'recovery mutated buff state')
        ''')

    def test_buff_scale_is_local_to_buff_rendering(self):
        source = (ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig")
        buff_block = source.split("-- ── Draw buffs ──", 1)[1].split(
            "-- ── Draw streak banner and horizontal killfeed ──", 1
        )[0]
        later_block = source.split(
            "-- ── Draw streak banner and horizontal killfeed ──", 1
        )[1]
        self.assertNotRegex(buff_block, r"(?m)^\s*size\s*=")
        self.assertIn("local buff_size = layout.effective_size", buff_block)
        self.assertIn("local item_h = clamp(size * 0.72 + 6, 28, 42)", later_block)
        self.assertIn("local font_size = clamp(size * 0.48, 15, 21)", later_block)
        self.assertIn(
            "draw_heist_score_widget(self, self._panel, w, h, size, alpha, s)",
            later_block,
        )


if __name__ == "__main__":
    unittest.main()
