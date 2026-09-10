"""Icon-resolution regressions against the real KyoHUD Lua chunk.

Run: uv run --with lupa python -B -m unittest discover -s .github -p test_icon_resolution.py -v
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
FALLBACK_TEXTURE = "guis/textures/pd2/hud_timer"


class IconResolutionTests(unittest.TestCase):
    def load_chunk(self, native_setup):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            Hooks = {callbacks = {}}
            function Hooks:PostHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:PreHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:Add(...) end
            HUDManager = {}; PlayerManager = {}; managers = {}; tweak_data = {}
            function Vector3(...) return {...} end
            function log(...) end
            function alive(x) return x ~= nil end
            Color = setmetatable({white = {}, black = {}}, {
                __call = function(...) return {} end
            })
            TimerManager = {
                game = function()
                    return {time = function() return 100 end}
                end
            }
        ''')
        lua.execute(native_setup)

        source = (ROOT / "lua" / "ky_buffhud.lua").read_text(encoding="utf-8-sig")
        function_header = "local function get_icon_data(icon)"
        self.assertEqual(source.count(function_header), 1)
        source = source.replace(
            function_header,
            "function kyohud.__test_get_icon_data(icon)",
            1,
        )
        lua.execute(source)
        return lua

    def assert_native_failure_uses_fallback(self, native_setup):
        lua = self.load_chunk(native_setup)
        texture, rect = lua.eval(
            'kyohud.__test_get_icon_data({texture = "third_party/bad"})'
        )
        self.assertEqual(texture, FALLBACK_TEXTURE)
        self.assertIsNone(rect)

    def test_db_has_failure_uses_fallback(self):
        self.assert_native_failure_uses_fallback('''
            function Idstring(value) return value end
            DB = {has = function() error("forced DB:has failure") end}
        ''')

    def test_idstring_failure_uses_fallback(self):
        self.assert_native_failure_uses_fallback('''
            function Idstring(value) error("forced Idstring failure") end
            DB = {has = function() return true end}
        ''')


if __name__ == "__main__":
    unittest.main()
