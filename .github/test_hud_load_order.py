"""LOT1 -- mod.txt load order and HUD foundation script paths."""
import json
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

from test_hud_runtime import ACCEPTANCE_ENV

ROOT = Path(__file__).resolve().parents[1]


class ModTxtStructureTests(unittest.TestCase):
    def setUp(self):
        self.meta = json.loads(
            (ROOT / "mod.txt").read_text(encoding="utf-8-sig")
        )

    def test_mod_txt_valid_json(self):
        self.assertIn("hooks", self.meta)

    def test_all_script_paths_exist(self):
        for hook in self.meta["hooks"]:
            p = ROOT / hook["script_path"]
            self.assertTrue(p.is_file(), f"missing: {hook['script_path']}")

    def test_hud_foundation_scripts_present(self):
        paths = [h["script_path"] for h in self.meta["hooks"]]
        consumers = {"lua/hud/mission.lua", "lua/hud/objectives.lua", "lua/hud/alerts.lua",
                     "lua/hud/assault.lua", "lua/hud/actors.lua", "lua/hud/components/gauge.lua",
                     "lua/hud/player.lua", "lua/hud/components/weapon.lua", "lua/hud/weapons.lua",
                     "lua/hud/components/equipment.lua", "lua/hud/equipment.lua",
                     "lua/hud/components/crew_card.lua", "lua/hud/crew.lua"}
        foundation_paths = {p for p in paths if p.startswith("lua/hud/") and p not in consumers}
        expected = {"lua/hud/layout.lua", "lua/hud/native_visibility.lua", "lua/hud/runtime.lua"}
        self.assertEqual(foundation_paths, expected,
            f"foundation must be exactly {expected}, got {foundation_paths}")

    def test_foundation_order_layout_before_visibility_before_runtime(self):
        paths = [h["script_path"] for h in self.meta["hooks"]]
        li = paths.index("lua/hud/layout.lua")
        ni = paths.index("lua/hud/native_visibility.lua")
        ri = paths.index("lua/hud/runtime.lua")
        self.assertLess(li, ni)
        self.assertLess(ni, ri)

    def test_foundation_after_existing_hudmanager_hooks(self):
        paths = [h["script_path"] for h in self.meta["hooks"]]
        last_existing = max(
            i for i, p in enumerate(paths)
            if p.startswith("lua/") and not p.startswith("lua/hud/")
            and self.meta["hooks"][i]["hook_id"] == "lib/managers/hudmanagerpd2"
        )
        li = paths.index("lua/hud/layout.lua")
        self.assertGreater(li, last_existing)

    def test_all_hud_foundation_hooks_use_hudmanagerpd2(self):
        for h in self.meta["hooks"]:
            if h["script_path"] in {"lua/hud/layout.lua", "lua/hud/native_visibility.lua", "lua/hud/runtime.lua"}:
                self.assertEqual(
                    h["hook_id"], "lib/managers/hudmanagerpd2",
                    f"{h['script_path']} must hook hudmanagerpd2",
                )


class HudFoundationChunksLoadTests(unittest.TestCase):
    def _env(self):
        l = LuaRuntime(unpack_returned_tuples=True)
        l.execute(ACCEPTANCE_ENV)
        l.globals().ModPath = ROOT.as_posix() + '/'
        return l

    def test_runtime_alone_exposes_mount_interface(self):
        l = self._env()
        l.execute((ROOT / "lua" / "hud" / "runtime.lua").read_text(encoding="utf-8-sig"))
        l.execute("assert(type(kyohud.hud.runtime.mount)=='function')")
        l.execute("assert(type(kyohud.hud.runtime.unmount)=='function')")
        l.execute("assert(type(kyohud.hud.runtime.rebuild)=='function')")
        l.execute("assert(type(kyohud.hud.runtime.update)=='function')")
        for name in ("layout", "native_visibility"):
            l.execute((ROOT / "lua" / "hud" / f"{name}.lua").read_text(encoding="utf-8-sig"))
        l.globals().RequiredScript = "lib/managers/hudmanagerpd2"
        l.execute("kyohud.settings.enable_hud_foundation=true")
        l.execute("fire('init_finalize',M)")
        l.execute("assert(alive(kyohud.hud.runtime._root_panel),'runtime must mount live root after full load')")

    def test_foundation_chunks_load_and_expose_api(self):
        l = self._env()
        for name in ("layout", "native_visibility", "runtime"):
            l.execute((ROOT / "lua" / "hud" / f"{name}.lua").read_text(encoding="utf-8-sig"))
        l.execute("assert(type(kyohud.hud.layout.resolve)=='function')")
        l.execute("assert(type(kyohud.hud.native_visibility.new)=='function')")
        l.execute("assert(type(kyohud.hud.runtime.mount)=='function')")
        l.execute("assert(rawequal(kyohud, Kyosh1roHUD))")

    def test_no_duplicate_hooks_from_ordered_load(self):
        l = self._env()
        l.globals().RequiredScript = "lib/managers/hudmanagerpd2"
        for name in ("layout", "native_visibility", "runtime"):
            l.execute((ROOT / "lua" / "hud" / f"{name}.lua").read_text(encoding="utf-8-sig"))
        l.execute('''
            _ids = {}
            _dupes = 0
            for _, e in ipairs(Hooks._all) do
                if _ids[e.id] then _dupes = _dupes + 1 end
                _ids[e.id] = true
            end
        ''')
        self.assertEqual(int(l.globals()._dupes), 0)


class ManifestIntegrationAcceptanceTests(unittest.TestCase):
    EXPECTED_HUDMANAGER_SCRIPTS = [
        "lua/hudlist.lua", "lua/core.lua", "lua/ky_buff_render.lua",
        "lua/ky_combat_medals.lua", "lua/ky_heist_score.lua",
        "lua/ky_hud_banners.lua", "lua/ky_killfeed_render.lua",
        "lua/ky_stealth.lua", "lua/ky_pager.lua",
        "lua/hud/layout.lua", "lua/hud/native_visibility.lua",
        "lua/hud/runtime.lua", "lua/hud/mission.lua", "lua/hud/objectives.lua",
        "lua/hud/alerts.lua", "lua/hud/assault.lua",
        "lua/hud/actors.lua", "lua/hud/components/gauge.lua",
        "lua/hud/player.lua",
        "lua/hud/components/weapon.lua", "lua/hud/weapons.lua",
        "lua/hud/components/equipment.lua", "lua/hud/equipment.lua",
    ]
    EXPECTED_HUDMANAGER_SCRIPTS += ["lua/hud/components/crew_card.lua", "lua/hud/crew.lua"]

    def test_actual_manifest_order_and_graphics_isolation(self):
        l = LuaRuntime(unpack_returned_tuples=True)
        l.execute(ACCEPTANCE_ENV)
        l.globals().ModPath = ROOT.as_posix() + '/'
        l.execute('''
            tweak_data={};PlayerManager={}
            Color=setmetatable({white={},black={}},{__call=function() return {with_alpha=function(self) return self end} end})
            function Vector3(...) return {...} end
            TimerManager={game=function() return {time=function() return 100 end} end}
            Application={time=function() return 1000 end}
            game_state_machine={last_queued_state_name=function() return 'ingame_standard' end}
            function dofile(path) local f=assert(loadfile(path)); f(); return nil end
        ''')
        meta = json.loads((ROOT / 'mod.txt').read_text(encoding='utf-8-sig'))
        paths = [h['script_path'] for h in meta['hooks'] if h['hook_id'] == 'lib/managers/hudmanagerpd2']
        self.assertEqual(paths, self.EXPECTED_HUDMANAGER_SCRIPTS)
        for p in paths:
            l.globals().RequiredScript = 'lib/managers/hudmanagerpd2'
            l.execute((ROOT / p).read_text(encoding='utf-8-sig'))
        l.execute('''
            local seen={}
            for _,e in ipairs(Hooks.entries) do assert(not seen[e.id],'duplicate hook '..e.id);seen[e.id]=true end
            kyohud.settings.enable_hud_foundation=true
            fire('init_finalize',M)
            local rt=kyohud.hud.runtime
            assert(alive(rt._root_panel),'foundation not mounted in production script order')
            kyohud._heist_score_total=123
            local buffs=kyohud._buffs;local kills=kyohud._kills;local h=rt._heist_generation
            local combat=kyohud._panel
            local r=rt._root_panel
            fire('resolution_changed',M)
            assert(rt._root_panel==r,'resolution recreated persistent root')
            fire('_setup_player_info_hud_pd2',M)
            assert(kyohud._panel==combat and alive(combat),'rebuild changed combat root')
            assert(kyohud._heist_score_total==123 and kyohud._buffs==buffs and kyohud._kills==kills,'rebuild reset combat state')
            assert(rt._heist_generation==h,'rebuild reset heist state')
            assert(next(kyohud.hud.native_visibility._whitelist)==nil,'production native target introduced')
        ''')

    def test_hud_foundation_scripts_order_unchanged(self):
        meta = json.loads(
            (ROOT / "mod.txt").read_text(encoding="utf-8-sig")
        )
        hudmanager_scripts = [
            h["script_path"] for h in meta["hooks"]
            if h["hook_id"] == "lib/managers/hudmanagerpd2"
        ]
        foundation_idx = [
            hudmanager_scripts.index(s) for s in self.EXPECTED_HUDMANAGER_SCRIPTS
        ]
        for i in range(len(foundation_idx) - 1):
            self.assertLess(foundation_idx[i], foundation_idx[i+1],
                f"foundation order violated: {self.EXPECTED_HUDMANAGER_SCRIPTS[i]} must come before {self.EXPECTED_HUDMANAGER_SCRIPTS[i+1]}")


class DiagnosticRemovalRegressionTests(unittest.TestCase):
    def setUp(self):
        self.meta = json.loads(
            (ROOT / "mod.txt").read_text(encoding="utf-8-sig")
        )

    def test_no_diagnostic_script_in_manifest(self):
        paths = [h["script_path"] for h in self.meta["hooks"]]
        diag_paths = [p for p in paths if "diagnostic" in p.lower()]
        self.assertEqual(len(diag_paths), 0,
            f"no diagnostic scripts allowed in manifest, got {diag_paths}")
        for p in paths:
            self.assertNotIn("_diag", p.lower(),
                f"diagnostic wrapper found in manifest: {p}")

    def test_no_diagnostic_callback_in_score_chunk(self):
        score_path = ROOT / "lua" / "ky_heist_score.lua"
        content = score_path.read_text(encoding="utf-8-sig")
        self.assertNotIn("_diag_score_callback", content,
            "diagnostic callback seam found in ky_heist_score.lua")

    def test_diagnostic_source_paths_absent(self):
        diag_lua = ROOT / "lua" / "ky_layout_diagnostics.lua"
        diag_test = ROOT / ".github" / "test_layout_diagnostics.py"
        self.assertFalse(diag_lua.exists(),
            "diagnostic source file should be removed by coordinator")
        self.assertFalse(diag_test.exists(),
            "diagnostic test file should be removed by coordinator")

    def test_combat_resize_suite_preserved(self):
        resize_test = ROOT / ".github" / "test_combat_panel_resize.py"
        self.assertTrue(resize_test.exists(),
            "real combat resize suite must be preserved")


if __name__ == "__main__":
    unittest.main()
