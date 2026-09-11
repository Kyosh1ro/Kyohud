"""Persistence regression tests against the real ky_options.lua chunk.

Run: uv run --with lupa python -B -m unittest discover -s .github -p test_settings_persistence.py -v
"""
import json
import tempfile
import unittest
from pathlib import Path

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
OPTIONS_CHUNK = (ROOT / "lua" / "ky_options.lua").read_text(encoding="utf-8-sig")


class SettingsPersistenceTests(unittest.TestCase):
    def load_options(self, save_dir, rename_failures=None, load_rename_failures=None):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.globals().SavePath = Path(save_dir).as_posix() + "/"
        lua.execute(
            r'''
            kyohud = nil
            Kyosh1roHUD = nil
            MenuCallbackHandler = {}
            Hooks = {callbacks = {}}
            function Hooks:Add(event, id, callback) self.callbacks[id] = callback end
            MenuHelper = {}
            BLT = nil
            function log(...) end
            function dofile(...) return true end
            json = {}
            function json.encode(data)
                return "language=" .. tostring(data.language)
            end
            function json.decode(raw)
                local language = tonumber(string.match(raw, "language=(%d+)"))
                if not language then error("invalid settings") end
                return {language = language}
            end
            '''
        )
        if load_rename_failures:
            lua.globals().rename_failures = lua.table_from(load_rename_failures)
            lua.execute(
                r'''
                original_rename = os.rename
                rename_call = 0
                os.rename = function(source, destination)
                    rename_call = rename_call + 1
                    if rename_failures[rename_call] then return nil, "controlled failure" end
                    return original_rename(source, destination)
                end
                '''
            )
        lua.execute(OPTIONS_CHUNK)
        if rename_failures:
            lua.globals().rename_failures = lua.table_from(rename_failures)
            lua.execute(
                r'''
                original_rename = os.rename
                rename_call = 0
                os.rename = function(source, destination)
                    rename_call = rename_call + 1
                    if rename_failures[rename_call] then return nil, "controlled failure" end
                    return original_rename(source, destination)
                end
                '''
            )
        return lua

    def test_global_buff_options_do_not_require_the_local_catalog(self):
        with tempfile.TemporaryDirectory() as save_dir:
            lua = LuaRuntime(unpack_returned_tuples=True)
            lua.globals().ModPath = ROOT.as_posix() + "/"
            lua.globals().SavePath = Path(save_dir).as_posix() + "/"
            lua.execute(
                r'''
                kyohud = nil
                Kyosh1roHUD = nil
                MenuCallbackHandler = {}
                Hooks = {callbacks = {}}
                function Hooks:Add(event, id, callback) self.callbacks[id] = callback end
                MenuHelper = {}
                BLT = nil
                function log(...) end
                function dofile(...) error("local buff catalog must not be loaded") end
                json = {
                    encode = function() return "{}" end,
                    decode = function() return {} end,
                }
                '''
            )

            lua.execute(OPTIONS_CHUNK)

            for key in (
                "enable_buffs",
                "buff_position_x",
                "buff_position_y",
                "opacity",
                "icon_size",
            ):
                self.assertIsNotNone(lua.eval(f"kyohud._defaults.{key}"), key)
            self.assertIsNone(lua.eval("kyohud._default_categories"))
            self.assertIsNone(lua.eval("kyohud.settings.buff_categories"))
            self.assertIsNone(lua.eval("kyohud.settings.buff_toggles"))

            menu = json.loads((ROOT / "menu" / "menu.json").read_text(encoding="utf-8-sig"))
            values = {item.get("value") for item in menu["items"]}
            self.assertTrue(
                {"enable_buffs", "buff_position_x", "buff_position_y", "opacity", "icon_size"}
                <= values
            )
            self.assertFalse(any(item.get("next_menu") == "kyohud_buffs_menu" for item in menu["items"]))

    def test_legacy_buff_filters_are_removed_without_losing_false_settings(self):
        with tempfile.TemporaryDirectory() as save_dir:
            settings_path = Path(save_dir) / "kyohud_settings.json"
            settings_path.write_text("legacy", encoding="utf-8")
            lua = LuaRuntime(unpack_returned_tuples=True)
            lua.globals().ModPath = ROOT.as_posix() + "/"
            lua.globals().SavePath = Path(save_dir).as_posix() + "/"
            lua.execute(
                r'''
                kyohud = nil
                Kyosh1roHUD = nil
                MenuCallbackHandler = {}
                Hooks = {callbacks = {}}
                function Hooks:Add(event, id, callback) self.callbacks[id] = callback end
                MenuHelper = {}
                BLT = nil
                function log(...) end
                json = {}
                function json.decode()
                    return {
                        enable_buffs = false,
                        enable_killfeed = false,
                        show_total_score = false,
                        show_best_streak = false,
                        killfeed_size = 5,
                        score_position_x = 42,
                        score_position_y = 73,
                        buff_categories = {mastermind = false},
                        buff_toggles = {inspire = false},
                    }
                end
                function json.encode(data)
                    assert(data.enable_buffs == false)
                    assert(data.enable_killfeed == false)
                    assert(data.show_total_score == false)
                    assert(data.show_best_streak == false)
                    assert(data.killfeed_size == 5)
                    assert(data.score_position_x == 42 and data.score_position_y == 73)
                    assert(data.buff_categories == nil and data.buff_toggles == nil)
                    return "migrated"
                end
                '''
            )

            lua.execute(OPTIONS_CHUNK)

            self.assertFalse(lua.eval("kyohud.settings.enable_buffs"))
            self.assertFalse(lua.eval("kyohud.settings.enable_killfeed"))
            self.assertFalse(lua.eval("kyohud.settings.show_total_score"))
            self.assertFalse(lua.eval("kyohud.settings.show_best_streak"))
            self.assertEqual(5, lua.eval("kyohud.settings.killfeed_size"))
            self.assertEqual(42, lua.eval("kyohud.settings.score_position_x"))
            self.assertEqual(73, lua.eval("kyohud.settings.score_position_y"))
            self.assertEqual("migrated", settings_path.read_text(encoding="utf-8"))

    def test_buff_toggle_describes_an_unavailable_provider(self):
        with tempfile.TemporaryDirectory() as save_dir:
            lua = LuaRuntime(unpack_returned_tuples=True)
            lua.globals().ModPath = ROOT.as_posix() + "/"
            lua.globals().SavePath = Path(save_dir).as_posix() + "/"
            lua.execute(
                r'''
                kyohud = nil
                Kyosh1roHUD = nil
                MenuCallbackHandler = {}
                Hooks = {callbacks = {}}
                function Hooks:Add(event, id, callback) self.callbacks[id] = callback end
                captured_items = {}
                created_menu_items = {}
                MenuHelper = {}
                function MenuHelper:AddToggle(params)
                    captured_items[#captured_items + 1] = params
                    local item = {enabled = params.disabled ~= true}
                    function item:set_enabled(enabled) self.enabled = enabled end
                    created_menu_items[#created_menu_items + 1] = item
                    return item
                end
                function MenuHelper:AddSlider(params)
                    captured_items[#captured_items + 1] = params
                    local item = {enabled = params.disabled ~= true}
                    function item:set_enabled(enabled) self.enabled = enabled end
                    created_menu_items[#created_menu_items + 1] = item
                    return item
                end
                BLT = nil
                managers = {}
                HUDList = nil
                HUDListManager = nil
                function log(...) end
                json = {
                    encode = function() return "{}" end,
                    decode = function()
                        return {
                            menu_id = "kyohud_options",
                            items = {
                                {
                                    type = "toggle",
                                    id = "ky_enable_buffs",
                                    description = "ky_opt_enable_buffs_desc",
                                    unavailable_description = "ky_opt_enable_buffs_unavailable_desc",
                                    provider_required = true,
                                    value = "enable_buffs",
                                    default_value = true,
                                },
                                {
                                    type = "slider", id = "ky_buff_position_x",
                                    description = "x", provider_required = true,
                                    enabled_by = "enable_buffs",
                                    value = "buff_position_x", default_value = 50,
                                },
                                {
                                    type = "slider", id = "ky_buff_position_y",
                                    description = "y", provider_required = true,
                                    enabled_by = "enable_buffs",
                                    value = "buff_position_y", default_value = 83,
                                },
                                {
                                    type = "slider", id = "ky_opacity",
                                    description = "opacity", value = "opacity",
                                    default_value = 0.9,
                                },
                            },
                        }
                    end,
                }
                '''
            )

            lua.execute(OPTIONS_CHUNK)
            lua.execute("Hooks.callbacks.KY_PopulateMenu()")
            self.assertEqual(
                "ky_opt_enable_buffs_unavailable_desc",
                lua.eval("captured_items[1].desc"),
            )
            self.assertTrue(lua.eval("captured_items[1].disabled"))
            self.assertTrue(lua.eval("captured_items[2].disabled"))
            self.assertTrue(lua.eval("captured_items[3].disabled"))
            self.assertFalse(lua.eval("captured_items[4].disabled == true"))

            lua.execute('''
                BLT = {
                    Mods = {
                        GetModByName = function(self, name)
                            if name ~= "VanillaHUDPlus" then return nil end
                            return {IsEnabled = function() return true end}
                        end,
                    },
                }
                kyohud.settings.enable_buffs = false
                Hooks.callbacks.KY_PopulateMenu()
            ''')
            self.assertEqual(
                "ky_opt_enable_buffs_desc",
                lua.eval("captured_items[5].desc"),
            )
            self.assertFalse(lua.eval("captured_items[5].disabled == true"))
            self.assertTrue(lua.eval("captured_items[6].disabled"))
            self.assertTrue(lua.eval("captured_items[7].disabled"))

            lua.execute('''
                MenuCallbackHandler.KY_ToggleBuffs(nil, {
                    value = function() return "on" end,
                })
            ''')
            self.assertTrue(lua.eval("created_menu_items[6].enabled"))
            self.assertTrue(lua.eval("created_menu_items[7].enabled"))

            lua.execute('''
                MenuCallbackHandler.KY_ToggleBuffs(nil, {
                    value = function() return "off" end,
                })
            ''')
            self.assertFalse(lua.eval("created_menu_items[6].enabled"))
            self.assertFalse(lua.eval("created_menu_items[7].enabled"))

            lua.execute('''
                BLT = nil
                kyohud.settings.enable_buffs = true
                managers.gameinfo = {
                    register_listener = function() end,
                    get_buffs = function() return {} end,
                    get_player_actions = function() return {} end,
                }
                HUDList = {BuffItemBase = {MAP = {}}}
                HUDListManager = {BUFFS = {}}
                Hooks.callbacks.KY_PopulateMenu()
            ''')
            self.assertEqual(
                "ky_opt_enable_buffs_desc",
                lua.eval("captured_items[9].desc"),
            )
            self.assertFalse(lua.eval("captured_items[9].disabled == true"))
            self.assertFalse(lua.eval("captured_items[10].disabled == true"))
            self.assertFalse(lua.eval("captured_items[11].disabled == true"))

    def test_catalog_derived_menus_callbacks_and_localizations_are_removed(self):
        source = OPTIONS_CHUNK
        localization_source = (ROOT / "lua" / "ky_localization.lua").read_text(
            encoding="utf-8-sig"
        )

        removed_map = "BUFF" + "_MAP"
        self.assertNotIn("KH." + removed_map, source)
        self.assertNotIn("KY_ToggleCat_", source)
        self.assertNotIn("KY_ToggleBuff_", source)
        self.assertNotIn("BUFFS_MENU_DEFINITION", source)
        self.assertNotIn("kyohud." + removed_map, localization_source)
        self.assertFalse((ROOT / "menu" / "buffs.json").exists())

        allowed_buff_option_keys = {
            "ky_opt_buff_position_x",
            "ky_opt_buff_position_x_desc",
            "ky_opt_buff_position_y",
            "ky_opt_buff_position_y_desc",
        }
        for locale_name in ("english.json", "french.json"):
            locale = json.loads((ROOT / "loc" / locale_name).read_text(encoding="utf-8-sig"))
            self.assertFalse(any(key.startswith("ky_opt_cat_") for key in locale))
            self.assertNotIn("ky_opt_buffs_menu", locale)
            self.assertNotIn("ky_opt_buffs_menu_desc", locale)
            self.assertEqual(
                allowed_buff_option_keys,
                {key for key in locale if key.startswith("ky_opt_buff_")},
            )
            self.assertTrue(locale["ky_opt_enable_buffs_unavailable_desc"])

    def test_normal_save_replaces_destination_directly(self):
        with tempfile.TemporaryDirectory() as save_dir:
            settings_path = Path(save_dir) / "kyohud_settings.json"
            settings_path.write_text("language=2", encoding="utf-8")
            lua = self.load_options(save_dir)

            lua.execute("kyohud.settings.language = 3")

            self.assertTrue(lua.eval("kyohud.Save()"))
            self.assertEqual("language=3", settings_path.read_text(encoding="utf-8"))
            self.assertFalse(Path(str(settings_path) + ".tmp").exists())
            self.assertFalse(Path(str(settings_path) + ".bak").exists())

    def test_encode_failure_preserves_existing_settings(self):
        with tempfile.TemporaryDirectory() as save_dir:
            settings_path = Path(save_dir) / "kyohud_settings.json"
            settings_path.write_text("language=2", encoding="utf-8")
            lua = self.load_options(save_dir)
            lua.execute('json.encode = function() error("controlled encode failure") end')

            self.assertFalse(lua.eval("kyohud.Save()"))
            self.assertEqual("language=2", settings_path.read_text(encoding="utf-8"))

    def test_write_failure_preserves_existing_settings(self):
        with tempfile.TemporaryDirectory() as save_dir:
            settings_path = Path(save_dir) / "kyohud_settings.json"
            settings_path.write_text("language=2", encoding="utf-8")
            lua = self.load_options(save_dir)
            lua.execute(
                r'''
                original_open = io.open
                io.open = function(path, mode)
                    if path == kyohud._settings_path .. ".tmp" and mode == "w" then
                        return {write = function() return nil end, close = function() return true end}
                    end
                    return original_open(path, mode)
                end
                '''
            )

            self.assertFalse(lua.eval("kyohud.Save()"))
            self.assertEqual("language=2", settings_path.read_text(encoding="utf-8"))

    def test_close_failure_preserves_existing_settings(self):
        with tempfile.TemporaryDirectory() as save_dir:
            settings_path = Path(save_dir) / "kyohud_settings.json"
            settings_path.write_text("language=2", encoding="utf-8")
            lua = self.load_options(save_dir)
            lua.execute(
                r'''
                original_open = io.open
                io.open = function(path, mode)
                    if path == kyohud._settings_path .. ".tmp" and mode == "w" then
                        return {write = function() return true end, close = function() return nil end}
                    end
                    return original_open(path, mode)
                end
                '''
            )

            self.assertFalse(lua.eval("kyohud.Save()"))
            self.assertEqual("language=2", settings_path.read_text(encoding="utf-8"))

    def test_windows_backup_replacement_cleans_stale_backup(self):
        with tempfile.TemporaryDirectory() as save_dir:
            settings_path = Path(save_dir) / "kyohud_settings.json"
            backup_path = Path(str(settings_path) + ".bak")
            settings_path.write_text("language=2", encoding="utf-8")
            backup_path.write_text("language=1", encoding="utf-8")
            lua = self.load_options(save_dir, {1: True})
            lua.execute("kyohud.settings.language = 3")

            self.assertTrue(lua.eval("kyohud.Save()"))
            self.assertEqual("language=3", settings_path.read_text(encoding="utf-8"))
            self.assertFalse(backup_path.exists())

    def test_failed_replacement_restores_backup_immediately(self):
        with tempfile.TemporaryDirectory() as save_dir:
            settings_path = Path(save_dir) / "kyohud_settings.json"
            settings_path.write_text("language=2", encoding="utf-8")
            lua = self.load_options(save_dir, {1: True, 3: True})
            lua.execute("kyohud.settings.language = 3")

            self.assertFalse(lua.eval("kyohud.Save()"))
            self.assertEqual("language=2", settings_path.read_text(encoding="utf-8"))
            self.assertFalse(Path(str(settings_path) + ".tmp").exists())
            self.assertFalse(Path(str(settings_path) + ".bak").exists())

    def test_next_load_recovers_backup_after_restore_rename_failure(self):
        with tempfile.TemporaryDirectory() as save_dir:
            settings_path = Path(save_dir) / "kyohud_settings.json"
            backup_path = Path(str(settings_path) + ".bak")
            settings_path.write_text("language=2", encoding="utf-8")

            lua = self.load_options(save_dir, {1: True, 3: True, 4: True})
            lua.execute("kyohud.settings.language = 3")
            self.assertFalse(lua.eval("kyohud.Save()"))
            self.assertFalse(settings_path.exists())
            self.assertTrue(backup_path.exists())
            self.assertEqual("language=2", backup_path.read_text(encoding="utf-8"))

            reloaded = self.load_options(save_dir)
            self.assertEqual(2, reloaded.eval("kyohud.settings.language"))

    def test_next_load_reads_backup_when_recovery_rename_still_fails(self):
        with tempfile.TemporaryDirectory() as save_dir:
            settings_path = Path(save_dir) / "kyohud_settings.json"
            backup_path = Path(str(settings_path) + ".bak")
            backup_path.write_text("language=2", encoding="utf-8")

            reloaded = self.load_options(save_dir, load_rename_failures={1: True})

            self.assertEqual(2, reloaded.eval("kyohud.settings.language"))
            self.assertFalse(settings_path.exists())
            self.assertTrue(backup_path.exists())


if __name__ == "__main__":
    unittest.main()
