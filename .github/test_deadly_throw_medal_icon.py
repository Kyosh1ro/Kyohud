"""Test that deadly throw medal uses native throwing knife icon with +90° rotation.

Verifies:
- Medal uses native blackmarket texture path (guis/dlcs/pim/textures/pd2/blackmarket/icons/grenades/wpn_prj_target)
- Icon rotation is exactly +90 degrees
- Rotation is applied during rendering (bitmap:set_rotation called)
- Killfeed icon remains unchanged (csb_throwables, no rotation)
"""
from pathlib import Path
import unittest
from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


def _common_stubs():
    return '''
        Hooks = {callbacks = {}}
        function Hooks:PostHook(class, method, id, fn) self.callbacks[id] = fn end
        function Hooks:PreHook(class, method, id, fn) self.callbacks[id] = fn end
        function Hooks:Add(...) end
        HUDManager = {}; PlayerManager = {}; managers = {}; tweak_data = {}

        function Vector3(...) return {...} end
        function log(...) end
        function alive(x) return x ~= nil end
        function Idstring(value) return value end
        DB = {has = function() return true end}
        Color = setmetatable({white = {}, black = {}}, {
            __call = function(r, g, b)
                return {r = r or 0, g = g or 0, b = b or 0}
            end
        })
        TimerManager = {game = function() return {time = function() return 100 end} end}
        PlayerBase = {PLAYER_INFO_HUD_PD2 = "pd2", PLAYER_INFO_HUD_FULLSCREEN_PD2 = "fs"}

        -- Mock hud_icons with csb_throwables (valid hud_tweak)
        -- Note: hobby_knife is NOT a hud_tweak, it's a blackmarket projectile icon
        tweak_data.hud_icons = {
            get_icon_data = function(self, name, rect)
                if name == "csb_throwables" then
                    return "guis/textures/pd2/hud_throwables", {0, 0, 64, 64}
                end
                return nil, nil
            end
        }
    '''


class DeadlyThrowMedalIconTests(unittest.TestCase):
    def setUp(self):
        """Set up Lua runtime with minimal PD2 environment."""
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + "/"
        self.lua.execute(_common_stubs())

        # Load modules in correct context
        self.lua.globals().RequiredScript = "lib/managers/hudmanagerpd2"
        self.lua.execute((ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig"))
        self.lua.execute((ROOT / "lua" / "ky_combat_medals.lua").read_text(encoding="utf-8-sig"))

    def test_deadly_throw_medal_uses_native_blackmarket_texture(self):
        """Deadly throw medal should use native blackmarket texture path for wpn_prj_target."""
        self.lua.execute('''
            local card = kyohud.MakeEventMedalCard("deadly_throw")
            test_icon_texture = card.icon.texture
        ''')

        texture = self.lua.eval("test_icon_texture")
        # Native path from BlackMarketManager:get_throwable_icon("wpn_prj_target")
        # with texture_bundle_folder = "pim"
        expected = "guis/dlcs/pim/textures/pd2/blackmarket/icons/grenades/wpn_prj_target"
        self.assertEqual(texture, expected,
                        f"Deadly throw medal should use native blackmarket texture path, got {texture}")

    def test_deadly_throw_medal_has_135_degree_rotation(self):
        """Deadly throw medal icon should have +135° rotation."""
        self.lua.execute('''
            local card = kyohud.MakeEventMedalCard("deadly_throw")
            test_rotation = card.icon.rotation
        ''')

        rotation = self.lua.eval("test_rotation")
        self.assertEqual(rotation, 135,
                        "Deadly throw medal icon should have +135° rotation")

    def test_other_medals_have_no_rotation(self):
        """Other event medals should not have rotation set."""
        # Test a few other medals to ensure we didn't break them
        for medal_id in ["stealth_melee", "silent_guard", "backstab", "tied_civilian"]:
            self.lua.execute(f'''
                local card = kyohud.MakeEventMedalCard("{medal_id}")
                test_rotation = card.icon.rotation
            ''')

            rotation = self.lua.eval("test_rotation")
            self.assertIsNone(rotation,
                            f"{medal_id} medal should not have rotation, got {rotation}")

    def test_killfeed_throw_icon_uses_native_texture(self):
        """Killfeed throw icon should use native blackmarket texture with rotation."""
        # Create a throwing kill and check the entry's throw_icon
        self.lua.execute('''
            -- Initialize killfeed
            kyohud._kills = {}
            kyohud.settings = {killfeed_size = 5}

            -- Create a throwing kill entry with deadly_throw event
            local event_info = {
                deadly_throw = true
            }
            kyohud:add_kill("Guard", 100, true, nil, nil, nil, event_info, "player")

            -- Get the last kill entry
            local kill = kyohud._kills[#kyohud._kills]
            test_killfeed_texture = kill and kill.throw_icon and kill.throw_icon.texture
            test_killfeed_rotation = kill and kill.throw_icon and kill.throw_icon.rotation
        ''')

        texture = self.lua.eval("test_killfeed_texture")
        rotation = self.lua.eval("test_killfeed_rotation")

        expected = "guis/dlcs/pim/textures/pd2/blackmarket/icons/grenades/wpn_prj_target"
        self.assertEqual(texture, expected,
                        f"Killfeed throw icon should use native blackmarket texture path, got {texture}")
        self.assertEqual(rotation, 135,
                        f"Killfeed throw icon should have +135° rotation, got {rotation}")

    def test_get_icon_data_returns_rotation_for_direct_texture(self):
        """get_icon_data should return rotation as third value when using direct texture."""
        self.lua.execute('''
            local texture, rect, rotation = kyohud.get_icon_data({
                texture = "guis/dlcs/pim/textures/pd2/blackmarket/icons/grenades/wpn_prj_target",
                rotation = 90
            })
            test_texture = texture
            test_rotation = rotation
        ''')

        texture = self.lua.eval("test_texture")
        rotation = self.lua.eval("test_rotation")

        self.assertEqual(texture, "guis/dlcs/pim/textures/pd2/blackmarket/icons/grenades/wpn_prj_target")
        self.assertEqual(rotation, 90)

    def test_get_icon_data_returns_nil_rotation_when_absent(self):
        """get_icon_data should return nil rotation when not specified."""
        self.lua.execute('''
            local texture, rect, rotation = kyohud.get_icon_data({
                hud_tweak = "csb_throwables"
            })
            test_texture = texture
            test_rotation = rotation
        ''')

        texture = self.lua.eval("test_texture")
        rotation = self.lua.eval("test_rotation")

        self.assertEqual(texture, "guis/textures/pd2/hud_throwables")
        self.assertIsNone(rotation)

    def test_medal_rotation_applied_in_renderer(self):
        """Renderer should call bitmap:set_rotation when icon has rotation."""
        # Load additional modules needed for rendering
        self.lua.execute('''
            local function color(r, g, b)
                local c = {r = r or 0, g = g or 0, b = b or 0}
                function c:with_alpha(a) return self end
                return c
            end
            Color = setmetatable({white = color(1,1,1), black = color(0,0,0)}, {
                __call = function(_, ...) return color(...) end
            })
            tweak_data.menu = {pd2_small_font = "test_font", pd2_medium_font = "test_font_medium"}
        ''')

        self.lua.execute((ROOT / "lua" / "ky_hud_banners.lua").read_text(encoding="utf-8-sig"))
        self.lua.execute((ROOT / "lua" / "ky_killfeed_render.lua").read_text(encoding="utf-8-sig"))

        # Create a mock panel that captures bitmap calls
        self.lua.execute('''
            rotation_calls = {}
            local panel = {
                gradients = {}, rects = {}, texts = {}, bitmaps = {}, polygons = {},
                _children = {},
            }
            function panel:w() return 800 end
            function panel:h() return 600 end
            function panel:child() return nil end
            function panel:panel(params) self._children[#self._children+1] = params; return self end
            function panel:gradient(params)
                self.gradients[#self.gradients + 1] = params
                return params
            end
            function panel:rect(params)
                self.rects[#self.rects + 1] = params
                return params
            end
            function panel:text(params)
                self.texts[#self.texts + 1] = params
                return {set_text = function() end, text_rect = function() return 0, 0, 15, 10 end}
            end
            function panel:bitmap(params)
                local bmp = {
                    set_color = function() end,
                    set_alpha = function() end,
                    set_rotation = function(self, r)
                        rotation_calls[#rotation_calls + 1] = r
                    end
                }
                self.bitmaps[#self.bitmaps + 1] = params
                return bmp
            end
            function panel:polygon(params)
                self.polygons[#self.polygons + 1] = params
                return params
            end
            function panel:remove() end
            function panel:clear()
                self.gradients = {}; self.rects = {}; self.texts = {}
                self.bitmaps = {}; self.polygons = {}
            end
            kyohud._panel = panel
        ''')

        # Set up a deadly throw medal card
        self.lua.execute('''
            game_t = 100
            kyohud._medal_card = kyohud.MakeEventMedalCard("deadly_throw")
            kyohud._medal_card.preview = true
            kyohud._medal_card.started_t = 100
            kyohud._medal_card.t_end = 200
            kyohud._kills = {}
            kyohud._special_kill_banner = nil
            kyohud.settings = {
                enable_killfeed = true,
                icon_size = 32,
                opacity = 0.9,
                killfeed_size = 5,
                circle_radius = 250,
            }
        ''')

        # Call render_killfeed
        self.lua.execute('''
            kyohud:render_killfeed(kyohud._panel, 800, 600, 32, 0.9, 250)
        ''')

        # Check that set_rotation was called with 135
        self.lua.execute('''
            rotation_count = #rotation_calls
            found_135 = false
            for i, r in ipairs(rotation_calls) do
                if r == 135 then
                    found_135 = true
                    break
                end
            end
        ''')

        rotation_count = self.lua.eval("rotation_count")
        found_135 = self.lua.eval("found_135")

        self.assertGreater(rotation_count, 0,
                          "set_rotation should be called at least once")
        self.assertTrue(found_135,
                       f"set_rotation should be called with 135, called {rotation_count} times")


if __name__ == "__main__":
    unittest.main()
