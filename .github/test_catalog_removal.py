"""Regressions for removing KyoHUD's bundled buff catalog.

Run: uv run --with lupa python -B -m unittest discover -s .github -p test_catalog_removal.py -v
"""
import json
from pathlib import Path
import tempfile
import unittest

from lupa.luajit21 import LuaRuntime


ROOT = Path(__file__).resolve().parents[1]


class LocalBuffCatalogRemovalTests(unittest.TestCase):
    def test_every_runtime_chunk_loads_without_the_local_catalog(self):
        metadata = json.loads((ROOT / "mod.txt").read_text(encoding="utf-8-sig"))
        script_paths = list(dict.fromkeys(hook["script_path"] for hook in metadata["hooks"]))
        catalog_name = "ky_buff_" + "catalog.lua"

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            (temp_root / "lua").mkdir()
            for source in (ROOT / "lua").glob("*.lua"):
                if source.name != catalog_name:
                    (temp_root / "lua" / source.name).write_bytes(source.read_bytes())

            for script_path in script_paths:
                with self.subTest(script_path=script_path):
                    lua = LuaRuntime(unpack_returned_tuples=True)
                    lua.globals().ModPath = temp_root.as_posix() + "/"
                    lua.globals().SavePath = temp_root.as_posix() + "/"
                    lua.execute('''
                        captured_logs = {}
                        function log(message) captured_logs[#captured_logs + 1] = tostring(message) end
                        Hooks = {callbacks = {}}
                        function Hooks:PostHook(class, method, id, fn) self.callbacks[id] = fn end
                        function Hooks:PreHook(class, method, id, fn) self.callbacks[id] = fn end
                        function Hooks:Add(id, event, fn) self.callbacks[id] = fn end
                        HUDManager = {}; PlayerManager = {}; PlayerInventory = {}
                        PlayerDamage = {}; PlayerMovement = {}; RaycastWeaponBase = {}
                        NewRaycastWeaponBase = {}; CopDamage = {}; HuskCopDamage = {}
                        CivilianDamage = {}; managers = {}; tweak_data = {}
                        MenuCallbackHandler = {}
                        Application = {time = function() return 0 end}
                        TimerManager = {game = function() return {time = function() return 0 end} end}
                        function Vector3(...) return {...} end
                        function Idstring(value) return value end
                        function alive(value) return value ~= nil end
                        local function color() return {with_alpha = function(self) return self end} end
                        Color = setmetatable({white = color(), black = color()}, {
                            __call = function(...) return color() end,
                        })
                    ''')

                    source = temp_root / script_path
                    lua.execute(source.read_text(encoding="utf-8-sig"))
                    catalog_logs = lua.eval('''
                        function()
                            local found = {}
                            for _, message in ipairs(captured_logs) do
                                if string.find(string.lower(message), "buff catalog", 1, true) then
                                    found[#found + 1] = message
                                end
                            end
                            return table.concat(found, "\\n")
                        end
                    ''')()
                    self.assertEqual("", catalog_logs)

    def test_catalog_symbols_and_obsolete_native_hooks_are_removed(self):
        catalog_name = "ky_buff_" + "catalog.lua"
        self.assertFalse((ROOT / "lua" / catalog_name).exists())

        removed_symbols = [
            left + right
            for left, right in (
                ("BUFF", "_MAP"),
                ("BUFF", "_CATEGORIES"),
                ("BUFF", "_COLORS"),
                ("PERK_DECK", "_BUFFS"),
                ("UPGRADE_TO", "_BUFF"),
                ("BUFF_SOURCE", "_TARGETS"),
                ("GetBuff", "Targets"),
            )
        ]
        runtime_sources = "\n".join(
            path.read_text(encoding="utf-8-sig")
            for path in (ROOT / "lua").glob("*.lua")
            if path.name != catalog_name
        )
        for symbol in removed_symbols:
            self.assertNotIn("KH." + symbol, runtime_sources)
            self.assertNotIn("kyohud." + symbol, runtime_sources)

        metadata = json.loads((ROOT / "mod.txt").read_text(encoding="utf-8-sig"))
        script_paths = {hook["script_path"] for hook in metadata["hooks"]}
        self.assertNotIn("lua/ky_" + "hooks.lua", script_paths)
        self.assertFalse((ROOT / "lua" / ("ky_" + "hooks.lua")).exists())

        playerdamage = (ROOT / "lua" / "ky_playerdamage.lua").read_text(encoding="utf-8-sig")
        for obsolete in ("PASSIVE_" + "REGEN", "RefreshPassive" + "HealthRegen"):
            self.assertNotIn(obsolete, playerdamage)
        for preserved in ("KH_RevengeRemember_", "KH_ResetWeaponStreaks_"):
            self.assertIn(preserved, playerdamage)


if __name__ == "__main__":
    unittest.main()
