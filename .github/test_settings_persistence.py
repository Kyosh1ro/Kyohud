"""Persistence regression tests against the real ky_options.lua chunk.

Run: uv run --with lupa python -B -m unittest discover -s .github -p test_settings_persistence.py -v
"""
from pathlib import Path
import tempfile
import unittest

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
