"""HUD user scale range 0.85-1.10 (default 1.0) regression tests.

Covers slider metadata, saved-value clamping, invalid-type fallback,
callback behavior, layout effective scale, and localization descriptions.

Run: uv run --with lupa python -B -m unittest discover -s .github -p test_hud_scale_range.py -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
OPTIONS_CHUNK = (ROOT / "lua" / "ky_options.lua").read_text(encoding="utf-8-sig")
LAYOUT_PATH = ROOT / "lua" / "hud" / "layout.lua"
LOCALIZATION_CHUNK = (ROOT / "lua" / "ky_localization.lua").read_text(encoding="utf-8-sig")
MENU_PATH = ROOT / "menu" / "menu.json"

SCALE_MIN = 0.85
SCALE_MAX = 1.10
SCALE_DEFAULT = 1.0

sys.path.insert(0, str(ROOT / ".github"))
from test_hud_runtime import acceptance_env as runtime_acceptance_env


def _find_scale_slider(menu_items):
    for item in menu_items:
        if item.get("value") == "hud_scale":
            return item
    return None


class SliderMetadataTests(unittest.TestCase):
    def setUp(self):
        self.menu = json.loads(MENU_PATH.read_text(encoding="utf-8-sig"))
        self.slider = _find_scale_slider(self.menu["items"])
        self.assertIsNotNone(self.slider, "menu.json must contain hud_scale slider")

    def test_slider_type(self):
        self.assertEqual(self.slider.get("type"), "slider")

    def test_slider_min(self):
        self.assertAlmostEqual(float(self.slider["min"]), SCALE_MIN, places=5)

    def test_slider_max(self):
        self.assertAlmostEqual(float(self.slider["max"]), SCALE_MAX, places=5)

    def test_slider_default(self):
        self.assertAlmostEqual(float(self.slider["default_value"]), SCALE_DEFAULT, places=5)

    def test_slider_step(self):
        self.assertAlmostEqual(float(self.slider["step"]), 0.05, places=5)

    def test_slider_callback(self):
        self.assertEqual(self.slider.get("callback"), "KY_SetHudScale")

    def test_slider_display_precision(self):
        self.assertEqual(self.slider.get("display_precision"), 2)


class _OptionsMixin:
    def _load_with_decoded(self, decoded_table):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        save_dir = self._tmpdir.name
        settings_path = Path(save_dir) / "kyohud_settings.json"
        settings_path.write_text("dummy", encoding="utf-8")
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.globals().SavePath = Path(save_dir).as_posix() + "/"
        lua.execute(r'''
            kyohud = nil
            Kyosh1roHUD = nil
            MenuCallbackHandler = {}
            Hooks = {callbacks = {}}
            function Hooks:Add(event, id, callback) self.callbacks[id] = callback end
            MenuHelper = {}
            BLT = nil
            function log(...) end
            json = {}
            function json.encode(data) return "{}" end
        ''')
        lua.globals()._decoded = lua.table_from(decoded_table)
        lua.execute(r'''
            function json.decode(raw) return _decoded end
        ''')
        lua.execute(OPTIONS_CHUNK)
        return lua


class SavedScaleClampTests(unittest.TestCase, _OptionsMixin):
    def test_saved_negative_clamps_to_min(self):
        lua = self._load_with_decoded({"hud_scale": -1})
        val = float(lua.eval("kyohud.settings.hud_scale"))
        self.assertAlmostEqual(val, SCALE_MIN, places=5)

    def test_saved_zero_clamps_to_min(self):
        lua = self._load_with_decoded({"hud_scale": 0})
        val = float(lua.eval("kyohud.settings.hud_scale"))
        self.assertAlmostEqual(val, SCALE_MIN, places=5)

    def test_saved_old_low_clamps_to_min(self):
        lua = self._load_with_decoded({"hud_scale": 0.50})
        val = float(lua.eval("kyohud.settings.hud_scale"))
        self.assertAlmostEqual(val, SCALE_MIN, places=5)

    def test_saved_old_high_clamps_to_max(self):
        lua = self._load_with_decoded({"hud_scale": 2.0})
        val = float(lua.eval("kyohud.settings.hud_scale"))
        self.assertAlmostEqual(val, SCALE_MAX, places=5)

    def test_saved_just_below_min_clamps(self):
        lua = self._load_with_decoded({"hud_scale": 0.84})
        val = float(lua.eval("kyohud.settings.hud_scale"))
        self.assertAlmostEqual(val, SCALE_MIN, places=5)

    def test_saved_just_above_max_clamps(self):
        lua = self._load_with_decoded({"hud_scale": 1.11})
        val = float(lua.eval("kyohud.settings.hud_scale"))
        self.assertAlmostEqual(val, SCALE_MAX, places=5)

    def test_in_range_values_unchanged(self):
        for v in (SCALE_MIN, 0.90, SCALE_DEFAULT, 1.05, SCALE_MAX):
            with self.subTest(v=v):
                lua = self._load_with_decoded({"hud_scale": v})
                val = float(lua.eval("kyohud.settings.hud_scale"))
                self.assertAlmostEqual(val, v, places=5)

    def test_saved_min_endpoint_retained(self):
        lua = self._load_with_decoded({"hud_scale": SCALE_MIN})
        val = float(lua.eval("kyohud.settings.hud_scale"))
        self.assertAlmostEqual(val, SCALE_MIN, places=5)

    def test_saved_max_endpoint_retained(self):
        lua = self._load_with_decoded({"hud_scale": SCALE_MAX})
        val = float(lua.eval("kyohud.settings.hud_scale"))
        self.assertAlmostEqual(val, SCALE_MAX, places=5)

    def test_normalized_save_persists_on_reload(self):
        import json as py_json
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        save_dir = self._tmpdir.name
        settings_path = Path(save_dir) / "kyohud_settings.json"

        def make_lua():
            lua = LuaRuntime(unpack_returned_tuples=True)
            lua.globals().ModPath = ROOT.as_posix() + "/"
            lua.globals().SavePath = Path(save_dir).as_posix() + "/"
            lua.execute(r'''
                kyohud = nil; Kyosh1roHUD = nil
                MenuCallbackHandler = {}
                Hooks = {callbacks = {}}
                function Hooks:Add(event, id, callback) self.callbacks[id] = callback end
                MenuHelper = {}
                BLT = nil
                function log(...) end
            ''')
            def py_encode(lua_table):
                d = {}
                for k, v in lua_table.items():
                    d[str(k)] = v
                return py_json.dumps(d)
            def py_decode(raw_str):
                d = py_json.loads(str(raw_str))
                return lua.table_from(d)
            lua.globals()._py_encode = py_encode
            lua.globals()._py_decode = py_decode
            lua.execute(r'''
                json = {
                    encode = function(data) return _py_encode(data) end,
                    decode = function(raw) return _py_decode(raw) end,
                }
            ''')
            return lua

        for written, expected in ((0.50, SCALE_MIN), (2.0, SCALE_MAX)):
            with self.subTest(written=written):
                settings_path.write_text(
                    py_json.dumps({"hud_scale": written, "language": 1}),
                    encoding="utf-8",
                )
                lua = make_lua()
                lua.execute(OPTIONS_CHUNK)
                val_after_load = float(lua.eval("kyohud.settings.hud_scale"))
                self.assertAlmostEqual(val_after_load, expected, places=5)
                file_data = py_json.loads(settings_path.read_text(encoding="utf-8"))
                self.assertAlmostEqual(float(file_data["hud_scale"]), expected, places=5)
                lua2 = make_lua()
                lua2.execute(OPTIONS_CHUNK)
                val_reload = float(lua2.eval("kyohud.settings.hud_scale"))
                self.assertAlmostEqual(val_reload, expected, places=5)


class InvalidScaleDefaultTests(unittest.TestCase, _OptionsMixin):
    def test_nan_defaults(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        save_dir = self._tmpdir.name
        settings_path = Path(save_dir) / "kyohud_settings.json"
        settings_path.write_text("dummy", encoding="utf-8")
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.globals().SavePath = Path(save_dir).as_posix() + "/"
        lua.execute(r'''
            kyohud = nil; Kyosh1roHUD = nil
            MenuCallbackHandler = {}
            Hooks = {callbacks = {}}
            function Hooks:Add(event, id, callback) self.callbacks[id] = callback end
            MenuHelper = {}; BLT = nil
            function log(...) end
            json = {}
            function json.encode(data) return "{}" end
        ''')
        lua.execute(r'''
            function json.decode(raw) return {hud_scale = 0/0, language = 1} end
        ''')
        lua.execute(OPTIONS_CHUNK)
        val = float(lua.eval("kyohud.settings.hud_scale"))
        self.assertAlmostEqual(val, SCALE_DEFAULT, places=5)

    def test_positive_infinity_defaults(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        save_dir = self._tmpdir.name
        settings_path = Path(save_dir) / "kyohud_settings.json"
        settings_path.write_text("dummy", encoding="utf-8")
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.globals().SavePath = Path(save_dir).as_posix() + "/"
        lua.execute(r'''
            kyohud = nil; Kyosh1roHUD = nil
            MenuCallbackHandler = {}
            Hooks = {callbacks = {}}
            function Hooks:Add(event, id, callback) self.callbacks[id] = callback end
            MenuHelper = {}; BLT = nil
            function log(...) end
            json = {}
            function json.encode(data) return "{}" end
        ''')
        lua.execute(r'''
            function json.decode(raw) return {hud_scale = math.huge, language = 1} end
        ''')
        lua.execute(OPTIONS_CHUNK)
        val = float(lua.eval("kyohud.settings.hud_scale"))
        self.assertAlmostEqual(val, SCALE_DEFAULT, places=5)

    def test_negative_infinity_defaults(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        save_dir = self._tmpdir.name
        settings_path = Path(save_dir) / "kyohud_settings.json"
        settings_path.write_text("dummy", encoding="utf-8")
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.globals().SavePath = Path(save_dir).as_posix() + "/"
        lua.execute(r'''
            kyohud = nil; Kyosh1roHUD = nil
            MenuCallbackHandler = {}
            Hooks = {callbacks = {}}
            function Hooks:Add(event, id, callback) self.callbacks[id] = callback end
            MenuHelper = {}; BLT = nil
            function log(...) end
            json = {}
            function json.encode(data) return "{}" end
        ''')
        lua.execute(r'''
            function json.decode(raw) return {hud_scale = -math.huge, language = 1} end
        ''')
        lua.execute(OPTIONS_CHUNK)
        val = float(lua.eval("kyohud.settings.hud_scale"))
        self.assertAlmostEqual(val, SCALE_DEFAULT, places=5)

    def test_string_type_defaults(self):
        lua = self._load_with_decoded({"hud_scale": "wide"})
        val = float(lua.eval("kyohud.settings.hud_scale"))
        self.assertAlmostEqual(val, SCALE_DEFAULT, places=5)

    def test_bool_type_defaults(self):
        lua = self._load_with_decoded({"hud_scale": True})
        val = float(lua.eval("kyohud.settings.hud_scale"))
        self.assertAlmostEqual(val, SCALE_DEFAULT, places=5)

    def test_missing_key_defaults(self):
        lua = self._load_with_decoded({"language": 1})
        val = float(lua.eval("kyohud.settings.hud_scale"))
        self.assertAlmostEqual(val, SCALE_DEFAULT, places=5)


class ScaleCallbackTests(unittest.TestCase):
    def _load_with_runtime(self, initial_settings=None):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmpdir.cleanup)
        save_dir = self._tmpdir.name
        lua = runtime_acceptance_env()
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.globals().SavePath = Path(save_dir).as_posix() + "/"
        lua.execute(r'''
            MenuCallbackHandler = MenuCallbackHandler or {}
            MenuHelper = MenuHelper or {}
            function MenuHelper:AddToggle(p) end
            function MenuHelper:AddSlider(p) end
            function MenuHelper:AddMultipleChoice(p) end
            function MenuHelper:AddButton(p) end
            function MenuHelper:AddDivider(p) end
            function MenuHelper:NewMenu(id) end
            function MenuHelper:BuildMenu(id, opts) return {} end
            function MenuHelper:AddMenuItem(a,b,c,d) end
            BLT = nil
            function Hooks:Add(event, id, callback) end
            function dofile(...) return true end
        ''')
        import json as py_json
        def py_json_encode(lua_table):
            d = {}
            for k, v in lua_table.items():
                d[str(k)] = v
            return py_json.dumps(d)
        def py_json_decode(raw_str):
            d = py_json.loads(str(raw_str))
            return lua.table_from(d)
        lua.globals()._py_encode = py_json_encode
        lua.globals()._py_decode = py_json_decode
        lua.execute(r'''
            json = {
                encode = function(data) return _py_encode(data) end,
                decode = function(raw) return _py_decode(raw) end,
            }
        ''')
        lua.execute('kyohud.settings = {}')
        if initial_settings:
            settings_path = Path(save_dir) / "kyohud_settings.json"
            settings_path.write_text(py_json.dumps(initial_settings), encoding="utf-8")
        lua.execute(OPTIONS_CHUNK)
        return lua

    def test_callback_clamps_out_of_range_high(self):
        lua = self._load_with_runtime({"enable_hud_foundation": True, "hud_scale": 1.0})
        lua.execute('''
            local cb_toggle = MenuCallbackHandler.KY_ToggleHudFoundation
            cb_toggle(nil, {value = function() return "on" end})
            kyohud.RefreshHUD = function() end
            local cb = MenuCallbackHandler.KY_SetHudScale
            cb(nil, {value = function() return "1.5" end})
            _v = kyohud.settings.hud_scale
        ''')
        self.assertAlmostEqual(float(lua.globals()._v), SCALE_MAX, places=5)

    def test_callback_clamps_out_of_range_low(self):
        lua = self._load_with_runtime({"enable_hud_foundation": True, "hud_scale": 1.0})
        lua.execute('''
            local cb_toggle = MenuCallbackHandler.KY_ToggleHudFoundation
            cb_toggle(nil, {value = function() return "on" end})
            kyohud.RefreshHUD = function() end
            local cb = MenuCallbackHandler.KY_SetHudScale
            cb(nil, {value = function() return "0.1" end})
            _v = kyohud.settings.hud_scale
        ''')
        self.assertAlmostEqual(float(lua.globals()._v), SCALE_MIN, places=5)

    def test_callback_accepts_in_range(self):
        lua = self._load_with_runtime({"enable_hud_foundation": True, "hud_scale": 1.0})
        lua.execute('''
            local cb_toggle = MenuCallbackHandler.KY_ToggleHudFoundation
            cb_toggle(nil, {value = function() return "on" end})
            kyohud.RefreshHUD = function() end
            local cb = MenuCallbackHandler.KY_SetHudScale
            cb(nil, {value = function() return "1.05" end})
            _v = kyohud.settings.hud_scale
        ''')
        self.assertAlmostEqual(float(lua.globals()._v), 1.05, places=5)

    def test_callback_invalid_defaults(self):
        lua = self._load_with_runtime({"enable_hud_foundation": True, "hud_scale": 1.0})
        lua.execute('''
            local cb_toggle = MenuCallbackHandler.KY_ToggleHudFoundation
            cb_toggle(nil, {value = function() return "on" end})
            kyohud.RefreshHUD = function() end
            local cb = MenuCallbackHandler.KY_SetHudScale
            cb(nil, {value = function() return "garbage" end})
            _v = kyohud.settings.hud_scale
        ''')
        self.assertAlmostEqual(float(lua.globals()._v), SCALE_DEFAULT, places=5)

    def test_callback_saves_to_disk(self):
        import json as py_json
        lua = self._load_with_runtime({"enable_hud_foundation": True, "hud_scale": 1.0})
        lua.execute('''
            local cb_toggle = MenuCallbackHandler.KY_ToggleHudFoundation
            cb_toggle(nil, {value = function() return "on" end})
            kyohud.RefreshHUD = function() end
            local cb = MenuCallbackHandler.KY_SetHudScale
            cb(nil, {value = function() return "1.05" end})
        ''')
        save_dir = self._tmpdir.name
        file_on_disk = (Path(save_dir) / "kyohud_settings.json").read_text(encoding="utf-8")
        data = py_json.loads(file_on_disk)
        self.assertAlmostEqual(float(data["hud_scale"]), 1.05, places=5)

    def test_callback_triggers_refresh(self):
        lua = self._load_with_runtime({"enable_hud_foundation": True, "hud_scale": 1.0})
        lua.execute('''
            local cb_toggle = MenuCallbackHandler.KY_ToggleHudFoundation
            cb_toggle(nil, {value = function() return "on" end})
            _refreshed = false
            kyohud.hud.runtime.refresh_settings = function(self, mgr)
                _refreshed = true
            end
            local cb = MenuCallbackHandler.KY_SetHudScale
            cb(nil, {value = function() return "1.05" end})
        ''')
        self.assertTrue(bool(lua.globals()._refreshed))


def _make_layout_lua():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute('''
        _hook_calls = {add=0, post=0, pre=0}
        Hooks = {}
        function Hooks:PostHook(class, method, id, fn) end
        function Hooks:PreHook(class, method, id, fn) end
        function Hooks:Add(event, id, callback) end
        function log(...) end
    ''')
    with open(LAYOUT_PATH, "r", encoding="utf-8-sig") as f:
        lua.execute(f.read())
    return lua


class LayoutScaleTests(unittest.TestCase):
    def setUp(self):
        self.lua = _make_layout_lua()

    def _scale(self, code):
        self.lua.execute(code)
        return self.lua.globals()

    def test_endpoint_min_retained(self):
        g = self._scale(f"_s = kyohud.hud.layout.resolve(1920, 1080, {SCALE_MIN}).scale")
        self.assertAlmostEqual(float(g._s), SCALE_MIN, places=5)

    def test_endpoint_max_retained(self):
        g = self._scale(f"_s = kyohud.hud.layout.resolve(1920, 1080, {SCALE_MAX}).scale")
        self.assertAlmostEqual(float(g._s), SCALE_MAX, places=5)

    def test_default_retained(self):
        g = self._scale(f"_s = kyohud.hud.layout.resolve(1920, 1080, {SCALE_DEFAULT}).scale")
        self.assertAlmostEqual(float(g._s), SCALE_DEFAULT, places=5)

    def test_old_low_clamped_to_min(self):
        g = self._scale("_s = kyohud.hud.layout.resolve(1920, 1080, 0.5).scale")
        self.assertAlmostEqual(float(g._s), SCALE_MIN, places=5)

    def test_old_high_clamped_to_max(self):
        g = self._scale("_s = kyohud.hud.layout.resolve(1920, 1080, 2.0).scale")
        self.assertAlmostEqual(float(g._s), SCALE_MAX, places=5)

    def test_negative_falls_back_to_default(self):
        g = self._scale("_s = kyohud.hud.layout.resolve(1920, 1080, -0.5).scale")
        self.assertAlmostEqual(float(g._s), SCALE_DEFAULT, places=5)

    def test_very_large_clamped_to_max(self):
        g = self._scale("_s = kyohud.hud.layout.resolve(1920, 1080, 99.0).scale")
        self.assertAlmostEqual(float(g._s), SCALE_MAX, places=5)

    def test_zero_falls_back_to_default(self):
        g = self._scale("_s = kyohud.hud.layout.resolve(1920, 1080, 0).scale")
        self.assertAlmostEqual(float(g._s), SCALE_DEFAULT, places=5)

    def test_nil_falls_back_to_default(self):
        g = self._scale("_s = kyohud.hud.layout.resolve(1920, 1080, nil).scale")
        self.assertAlmostEqual(float(g._s), SCALE_DEFAULT, places=5)

    def test_nan_falls_back_to_default(self):
        g = self._scale("_s = kyohud.hud.layout.resolve(1920, 1080, 0/0).scale")
        self.assertAlmostEqual(float(g._s), SCALE_DEFAULT, places=5)

    def test_positive_infinity_falls_back_to_default(self):
        g = self._scale("_s = kyohud.hud.layout.resolve(1920, 1080, math.huge).scale")
        self.assertAlmostEqual(float(g._s), SCALE_DEFAULT, places=5)

    def test_negative_infinity_falls_back_to_default(self):
        g = self._scale("_s = kyohud.hud.layout.resolve(1920, 1080, -math.huge).scale")
        self.assertAlmostEqual(float(g._s), SCALE_DEFAULT, places=5)

    def test_string_coerced_in_range(self):
        g = self._scale('_s = kyohud.hud.layout.resolve(1920, 1080, "1.05").scale')
        self.assertAlmostEqual(float(g._s), 1.05, places=5)

    def test_numeric_string_old_high_clamped(self):
        g = self._scale('_s = kyohud.hud.layout.resolve(1920, 1080, "2.0").scale')
        self.assertAlmostEqual(float(g._s), SCALE_MAX, places=5)

    def test_non_numeric_string_falls_back(self):
        g = self._scale('_s = kyohud.hud.layout.resolve(1920, 1080, "wide").scale')
        self.assertAlmostEqual(float(g._s), SCALE_DEFAULT, places=5)

    def test_bool_falls_back_to_default(self):
        g = self._scale("_s = kyohud.hud.layout.resolve(1920, 1080, true).scale")
        self.assertAlmostEqual(float(g._s), SCALE_DEFAULT, places=5)

    def test_invalid_dims_still_clamps_scale(self):
        g = self._scale("_r = kyohud.hud.layout.resolve(0, 0, 0.5); _s = _r.scale")
        self.assertAlmostEqual(float(g._s), SCALE_MIN, places=5)


class ScaleLocalizationTests(unittest.TestCase):
    EXPECTED_EN_DESC = "Scale factor for HUD elements (0.85-1.10). Default: 1.0"
    EXPECTED_FR_DESC = "Facteur d'\u00e9chelle des \u00e9l\u00e9ments du HUD (0,85-1,10). Par d\u00e9faut : 1,0"

    def setUp(self):
        self.en = json.loads((ROOT / "loc" / "english.json").read_text(encoding="utf-8-sig"))
        self.fr = json.loads((ROOT / "loc" / "french.json").read_text(encoding="utf-8-sig"))

    def test_english_desc_exact(self):
        self.assertEqual(self.en["ky_opt_hud_scale_desc"], self.EXPECTED_EN_DESC)

    def test_french_desc_exact(self):
        self.assertEqual(self.fr["ky_opt_hud_scale_desc"], self.EXPECTED_FR_DESC)

    def test_english_title_present(self):
        self.assertEqual(self.en["ky_opt_hud_scale"], "HUD Scale")

    def test_french_title_present(self):
        self.assertEqual(self.fr["ky_opt_hud_scale"], "\u00c9chelle du HUD")

    def test_fallback_desc_matches_new_range(self):
        self.assertIn("(0.85-1.10)", LOCALIZATION_CHUNK)
        self.assertIn("Default: 1.0", LOCALIZATION_CHUNK)
        self.assertNotIn("0.5-2.0", LOCALIZATION_CHUNK)

    def test_english_no_old_range(self):
        self.assertNotIn("0.5-2.0", self.en.get("ky_opt_hud_scale_desc", ""))

    def test_french_no_old_range(self):
        self.assertNotIn("0,5-2,0", self.fr.get("ky_opt_hud_scale_desc", ""))


if __name__ == "__main__":
    unittest.main()
