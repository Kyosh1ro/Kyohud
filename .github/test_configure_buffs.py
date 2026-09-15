"""Tests for Configure Buffs feature.

Run: uv run --with lupa python -B -m unittest discover -s .github -p test_configure_buffs.py -v
"""
import json
import tempfile
import unittest
from pathlib import Path

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
OPTIONS_CHUNK = (ROOT / "lua" / "ky_options.lua").read_text(encoding="utf-8-sig")


class ConfigureBuffsTests(unittest.TestCase):
    def load_options(self, save_dir):
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
        lua.execute(OPTIONS_CHUNK)
        return lua

    def test_kyohud_defaults_include_individual_buff_toggles(self):
        """Individual buff toggles must be present in KH._defaults."""
        with tempfile.TemporaryDirectory() as save_dir:
            lua = self.load_options(save_dir)

            # Cerveau (Mastermind)
            self.assertTrue(lua.eval("kyohud._defaults.forced_friendship"))
            self.assertTrue(lua.eval("kyohud._defaults.aggressive_reload_aced"))
            self.assertTrue(lua.eval("kyohud._defaults.combat_medic"))
            self.assertFalse(lua.eval("kyohud._defaults.combat_medic_passive"))
            self.assertFalse(lua.eval("kyohud._defaults.hostage_taker"))
            self.assertTrue(lua.eval("kyohud._defaults.inspire"))
            self.assertFalse(lua.eval("kyohud._defaults.painkiller"))
            self.assertFalse(lua.eval("kyohud._defaults.partner_in_crime"))
            self.assertFalse(lua.eval("kyohud._defaults.quick_fix"))
            self.assertTrue(lua.eval("kyohud._defaults.uppers"))
            self.assertTrue(lua.eval("kyohud._defaults.inspire_debuff"))
            self.assertTrue(lua.eval("kyohud._defaults.inspire_revive_debuff"))

            # Exécuteur (Enforcer) - 519-526
            self.assertTrue(lua.eval("kyohud._defaults.bulletproof"))
            self.assertTrue(lua.eval("kyohud._defaults.bullet_storm"))
            self.assertFalse(lua.eval("kyohud._defaults.die_hard"))
            self.assertFalse(lua.eval("kyohud._defaults.overkill"))
            self.assertFalse(lua.eval("kyohud._defaults.underdog"))
            self.assertTrue(lua.eval("kyohud._defaults.bullseye_debuff"))

            # Technicien (Technician) - 527-529
            self.assertTrue(lua.eval("kyohud._defaults.lock_n_load"))

            # Fantôme (Ghost) - 530-536
            self.assertTrue(lua.eval("kyohud._defaults.dire_need"))
            self.assertTrue(lua.eval("kyohud._defaults.second_wind"))
            self.assertTrue(lua.eval("kyohud._defaults.sixth_sense"))
            self.assertFalse(lua.eval("kyohud._defaults.old_sixth_sense"))
            self.assertTrue(lua.eval("kyohud._defaults.unseen_strike"))

            # Fugitif (Fugitive) - 537-548
            self.assertTrue(lua.eval("kyohud._defaults.berserker"))
            self.assertFalse(lua.eval("kyohud._defaults.bloodthirst_basic"))
            self.assertTrue(lua.eval("kyohud._defaults.bloodthirst_aced"))
            self.assertTrue(lua.eval("kyohud._defaults.desperado"))
            self.assertFalse(lua.eval("kyohud._defaults.frenzy"))
            self.assertTrue(lua.eval("kyohud._defaults.messiah"))
            self.assertTrue(lua.eval("kyohud._defaults.running_from_death"))
            self.assertFalse(lua.eval("kyohud._defaults.swan_song"))
            self.assertFalse(lua.eval("kyohud._defaults.trigger_happy"))
            self.assertFalse(lua.eval("kyohud._defaults.up_you_go"))

            # Composites - all true by default
            self.assertTrue(lua.eval("kyohud._defaults.damage_increase"))
            self.assertTrue(lua.eval("kyohud._defaults.damage_reduction"))
            self.assertTrue(lua.eval("kyohud._defaults.total_dodge_chance"))
            self.assertTrue(lua.eval("kyohud._defaults.melee_damage_increase"))
            self.assertTrue(lua.eval("kyohud._defaults.passive_health_regen"))

            # ammo_efficiency must NOT be present (explicitly excluded)
            self.assertIsNone(lua.eval("kyohud._defaults.ammo_efficiency"))

    def test_persistence_preserves_false_values(self):
        """Saved false values must be preserved, not overwritten by defaults."""
        with tempfile.TemporaryDirectory() as save_dir:
            settings_path = Path(save_dir) / "kyohud_settings.json"
            settings_path.write_text("language=1", encoding="utf-8")

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
                        language = 1,
                        forced_friendship = false,
                        damage_increase = false,
                        inspire = false,
                    }
                end
                function json.encode(data)
                    return "language=" .. tostring(data.language)
                end
                '''
            )
            lua.execute(OPTIONS_CHUNK)

            # false must be preserved, not replaced by default true
            self.assertFalse(lua.eval("kyohud.settings.forced_friendship"))
            self.assertFalse(lua.eval("kyohud.settings.damage_increase"))
            self.assertFalse(lua.eval("kyohud.settings.inspire"))

    def test_menu_json_has_configure_buffs_button(self):
        """Main menu must have a button to open Configure Buffs submenu."""
        menu = json.loads((ROOT / "menu" / "menu.json").read_text(encoding="utf-8-sig"))

        button_ids = [
            item["id"] for item in menu["items"]
            if item.get("type") == "button"
        ]
        self.assertIn("ky_configure_buffs", button_ids)

        button = next(item for item in menu["items"] if item.get("id") == "ky_configure_buffs")
        self.assertEqual(button.get("next_menu"), "kyohud_buffs_menu")
        self.assertEqual(button.get("enabled_by"), "enable_buffs")

    def test_submenus_are_linked_only_by_declarative_buttons(self):
        """Declarative next_menu buttons must not be duplicated by AddMenuItem calls."""
        self.assertEqual(OPTIONS_CHUNK.count("MenuHelper:AddMenuItem("), 1)

    def test_buffs_menu_json_exists_with_correct_structure(self):
        """menu/buffs.json must exist with 5 categories + separator + 5 composites."""
        buffs_menu_path = ROOT / "menu" / "buffs.json"
        self.assertTrue(buffs_menu_path.exists())

        menu = json.loads(buffs_menu_path.read_text(encoding="utf-8-sig"))
        self.assertEqual(menu["menu_id"], "kyohud_buffs_menu")
        self.assertEqual(menu["parent_menu_id"], "kyohud_options")

        items = menu["items"]

        # Expected order: 5 categories, separator, 5 composites
        category_ids = [
            "ky_buff_cat_mastermind",
            "ky_buff_cat_enforcer",
            "ky_buff_cat_technician",
            "ky_buff_cat_ghost",
            "ky_buff_cat_fugitive",
        ]
        composite_ids = [
            "ky_buff_damage_increase",
            "ky_buff_damage_reduction",
            "ky_buff_total_dodge_chance",
            "ky_buff_melee_damage_increase",
            "ky_buff_passive_health_regen",
        ]

        # Find all buttons (categories) and their positions
        button_positions = []
        for i, item in enumerate(items):
            if item.get("type") == "button":
                button_positions.append((i, item["id"]))

        # 5 category buttons in exact order
        self.assertEqual(len(button_positions), 5)
        for i, expected_id in enumerate(category_ids):
            pos, actual_id = button_positions[i]
            self.assertEqual(actual_id, expected_id)
            self.assertEqual(items[pos].get("enabled_by"), "enable_buffs")

        # Find all toggles (composites) and their positions
        toggle_positions = []
        for i, item in enumerate(items):
            if item.get("type") == "toggle":
                toggle_positions.append((i, item["id"]))

        # 5 composite toggles in exact order
        self.assertEqual(len(toggle_positions), 5)
        for i, expected_id in enumerate(composite_ids):
            pos, actual_id = toggle_positions[i]
            self.assertEqual(actual_id, expected_id)

        # There must be a divider between categories and composites
        divider_found = False
        last_category_pos = button_positions[-1][0]
        first_composite_pos = toggle_positions[0][0]
        for i, item in enumerate(items):
            if i > last_category_pos and i < first_composite_pos:
                if item.get("type") == "divider":
                    divider_found = True
                    break
        self.assertTrue(divider_found)

    def test_buff_toggle_json_defaults_match_lua_defaults(self):
        """Every declarative buff toggle must expose the persisted Lua default."""
        with tempfile.TemporaryDirectory() as save_dir:
            lua = self.load_options(save_dir)
            for filename in (
                "buffs.json",
                "buffs_mastermind.json",
                "buffs_enforcer.json",
                "buffs_technician.json",
                "buffs_ghost.json",
                "buffs_fugitive.json",
            ):
                definition = json.loads(
                    (ROOT / "menu" / filename).read_text(encoding="utf-8-sig")
                )
                for item in definition["items"]:
                    if item.get("type") != "toggle":
                        continue
                    self.assertIn("default_value", item, f"{filename}: {item['id']}")
                    self.assertEqual(
                        item["default_value"],
                        bool(lua.eval(f"kyohud._defaults.{item['value']}")),
                        f"{filename}: {item['id']}",
                    )

    def test_buffs_menu_categories_have_correct_toggles(self):
        """Each category submenu must have the correct individual toggles."""
        # Mastermind submenu
        mastermind_path = ROOT / "menu" / "buffs_mastermind.json"
        self.assertTrue(mastermind_path.exists())
        mastermind = json.loads(mastermind_path.read_text(encoding="utf-8-sig"))
        mastermind_toggles = [item["id"] for item in mastermind["items"] if item.get("type") == "toggle"]
        expected_mastermind = [
            "ky_buff_forced_friendship",
            "ky_buff_aggressive_reload_aced",
            "ky_buff_combat_medic",
            "ky_buff_combat_medic_passive",
            "ky_buff_hostage_taker",
            "ky_buff_inspire",
            "ky_buff_painkiller",
            "ky_buff_partner_in_crime",
            "ky_buff_quick_fix",
            "ky_buff_uppers",
            "ky_buff_inspire_debuff",
            "ky_buff_inspire_revive_debuff",
        ]
        self.assertEqual(mastermind_toggles, expected_mastermind)

        # Enforcer submenu
        enforcer_path = ROOT / "menu" / "buffs_enforcer.json"
        self.assertTrue(enforcer_path.exists())
        enforcer = json.loads(enforcer_path.read_text(encoding="utf-8-sig"))
        enforcer_toggles = [item["id"] for item in enforcer["items"] if item.get("type") == "toggle"]
        expected_enforcer = [
            "ky_buff_bulletproof",
            "ky_buff_bullet_storm",
            "ky_buff_die_hard",
            "ky_buff_overkill",
            "ky_buff_underdog",
            "ky_buff_bullseye_debuff",
        ]
        self.assertEqual(enforcer_toggles, expected_enforcer)

        # Technician submenu
        technician_path = ROOT / "menu" / "buffs_technician.json"
        self.assertTrue(technician_path.exists())
        technician = json.loads(technician_path.read_text(encoding="utf-8-sig"))
        technician_toggles = [item["id"] for item in technician["items"] if item.get("type") == "toggle"]
        self.assertEqual(technician_toggles, ["ky_buff_lock_n_load"])

        # Ghost submenu
        ghost_path = ROOT / "menu" / "buffs_ghost.json"
        self.assertTrue(ghost_path.exists())
        ghost = json.loads(ghost_path.read_text(encoding="utf-8-sig"))
        ghost_toggles = [item["id"] for item in ghost["items"] if item.get("type") == "toggle"]
        expected_ghost = [
            "ky_buff_dire_need",
            "ky_buff_second_wind",
            "ky_buff_sixth_sense",
            "ky_buff_old_sixth_sense",
            "ky_buff_unseen_strike",
        ]
        self.assertEqual(ghost_toggles, expected_ghost)

        # Fugitive submenu
        fugitive_path = ROOT / "menu" / "buffs_fugitive.json"
        self.assertTrue(fugitive_path.exists())
        fugitive = json.loads(fugitive_path.read_text(encoding="utf-8-sig"))
        fugitive_toggles = [item["id"] for item in fugitive["items"] if item.get("type") == "toggle"]
        expected_fugitive = [
            "ky_buff_berserker",
            "ky_buff_bloodthirst_basic",
            "ky_buff_bloodthirst_aced",
            "ky_buff_desperado",
            "ky_buff_frenzy",
            "ky_buff_messiah",
            "ky_buff_running_from_death",
            "ky_buff_swan_song",
            "ky_buff_trigger_happy",
            "ky_buff_up_you_go",
        ]
        self.assertEqual(fugitive_toggles, expected_fugitive)

    def test_callbacks_registered_for_all_buff_toggles(self):
        """All buff toggle callbacks must be registered in MenuCallbackHandler."""
        with tempfile.TemporaryDirectory() as save_dir:
            lua = self.load_options(save_dir)

            # Individual buff callbacks
            individual_buffs = [
                "forced_friendship", "aggressive_reload_aced", "combat_medic",
                "combat_medic_passive", "hostage_taker", "inspire", "painkiller",
                "partner_in_crime", "quick_fix", "uppers", "inspire_debuff",
                "inspire_revive_debuff", "bulletproof", "bullet_storm", "die_hard",
                "overkill", "underdog", "bullseye_debuff", "lock_n_load",
                "dire_need", "second_wind", "sixth_sense", "old_sixth_sense",
                "unseen_strike", "berserker", "bloodthirst_basic", "bloodthirst_aced",
                "desperado", "frenzy", "messiah", "running_from_death", "swan_song",
                "trigger_happy", "up_you_go",
            ]

            for buff_id in individual_buffs:
                callback_name = f"KY_ToggleBuff_{buff_id}"
                self.assertIsNotNone(
                    lua.eval(f"MenuCallbackHandler.{callback_name}"),
                    f"Missing callback {callback_name}"
                )

            # Composite callbacks
            composite_buffs = [
                "damage_increase", "damage_reduction", "total_dodge_chance",
                "melee_damage_increase", "passive_health_regen",
            ]
            for buff_id in composite_buffs:
                callback_name = f"KY_ToggleBuff_{buff_id}"
                self.assertIsNotNone(
                    lua.eval(f"MenuCallbackHandler.{callback_name}"),
                    f"Missing callback {callback_name}"
                )

    def _setup_core_lua(self):
        """Set up a Lua runtime with all stubs needed to load core.lua."""
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
            local function color()
                return {with_alpha = function(self) return self end}
            end
            Color = setmetatable({white = color(), black = color()}, {
                __call = function(...) return color() end
            })
            TimerManager = {
                game = function()
                    return {time = function() return 100 end}
                end
            }
        ''')
        lua.execute((ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig"))
        lua.execute('''
            kyohud._BUFF_TOGGLE_SET = {forced_friendship = true, inspire = true}
            kyohud.settings = {enable_buffs = true}
        ''')
        return lua

    def test_kh_is_buff_visible_respects_settings_over_autonomous_catalog(self):
        """KyoHUD settings must override catalog visibility for configured buffs."""
        lua = self._setup_core_lua()

        lua.execute('''
            kyohud.hudlist_catalog = {definitions = {
                forced_friendship = {ignore = true},
                inspire = {ignore = false},
            }}
            kyohud._gameinfo_bridge_active = true
            kyohud.settings.enable_buffs = true
            kyohud.settings.forced_friendship = true
            kyohud.settings.inspire = false
        ''')

        # KyoHUD setting true must override catalog ignore = true.
        self.assertTrue(lua.eval("kyohud:is_buff_visible('forced_friendship')"))

        # KyoHUD setting false must override catalog ignore = false.
        self.assertFalse(lua.eval("kyohud:is_buff_visible('inspire')"))

    def test_kh_is_buff_visible_falls_back_to_catalog_for_unknown_ids(self):
        """For unlisted buff IDs, the autonomous catalog controls visibility."""
        lua = self._setup_core_lua()

        lua.execute('''
            kyohud.hudlist_catalog = {definitions = {
                unknown_buff_hidden = {ignore = true},
                unknown_buff_shown = {ignore = false},
            }}
            kyohud._gameinfo_bridge_active = true
            kyohud.settings.enable_buffs = true
        ''')

        self.assertFalse(lua.eval("kyohud:is_buff_visible('unknown_buff_hidden')"))
        self.assertTrue(lua.eval("kyohud:is_buff_visible('unknown_buff_shown')"))

    def test_buff_toggles_respect_enable_buffs_global(self):
        """Buff toggles must be disabled when enable_buffs is off."""
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
                function log(...) end
                json = {
                    encode = function() return "{}" end,
                    decode = function()
                        return {
                            menu_id = "kyohud_buffs_menu",
                            items = {
                                {
                                    type = "toggle",
                                    id = "ky_buff_forced_friendship",
                                    value = "forced_friendship",
                                    enabled_by = "enable_buffs",
                                    default_value = true,
                                },
                                {
                                    type = "toggle",
                                    id = "ky_buff_damage_increase",
                                    value = "damage_increase",
                                    enabled_by = "enable_buffs",
                                    default_value = true,
                                },
                            },
                        }
                    end,
                }
                '''
            )
            lua.execute(OPTIONS_CHUNK)
            lua.execute("Hooks.callbacks.KY_PopulateMenu()")

            # With enable_buffs = true, toggles should be enabled
            # 14 items created (2 toggles × 7 menus: menu.json + buffs.json + 5 category files)
            self.assertEqual(14, lua.eval("#captured_items"))
            self.assertFalse(lua.eval("captured_items[1].disabled == true"))
            self.assertFalse(lua.eval("captured_items[2].disabled == true"))

            # With enable_buffs = false, toggles should be disabled
            lua.execute('''
                kyohud.settings.enable_buffs = false
                Hooks.callbacks.KY_PopulateMenu()
            ''')
            # Now 28 items total (14 + 14 new ones)
            self.assertEqual(28, lua.eval("#captured_items"))
            # Check the newly created items (indices 15-28)
            self.assertTrue(lua.eval("captured_items[15].disabled"))
            self.assertTrue(lua.eval("captured_items[16].disabled"))

    def test_localization_keys_present_for_configure_buffs(self):
        """All new localization keys must be present in fallbacks and both language files."""
        fallback_source = (ROOT / "lua" / "ky_localization.lua").read_text(encoding="utf-8-sig")
        english = json.loads((ROOT / "loc" / "english.json").read_text(encoding="utf-8-sig"))
        french = json.loads((ROOT / "loc" / "french.json").read_text(encoding="utf-8-sig"))

        required_keys = [
            "ky_opt_configure_buffs",
            "ky_opt_configure_buffs_desc",
            "ky_opt_buff_cat_mastermind",
            "ky_opt_buff_cat_mastermind_desc",
            "ky_opt_buff_cat_enforcer",
            "ky_opt_buff_cat_enforcer_desc",
            "ky_opt_buff_cat_technician",
            "ky_opt_buff_cat_technician_desc",
            "ky_opt_buff_cat_ghost",
            "ky_opt_buff_cat_ghost_desc",
            "ky_opt_buff_cat_fugitive",
            "ky_opt_buff_cat_fugitive_desc",
            "ky_opt_buff_forced_friendship",
            "ky_opt_buff_forced_friendship_desc",
            "ky_opt_buff_damage_increase",
            "ky_opt_buff_damage_increase_desc",
        ]

        for key in required_keys:
            self.assertIn(key, fallback_source, f"Missing fallback for {key}")
            self.assertIn(key, english, f"Missing English translation for {key}")
            self.assertIn(key, french, f"Missing French translation for {key}")


if __name__ == "__main__":
    unittest.main()
