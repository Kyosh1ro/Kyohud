"""Test that medal extraction into ky_combat_medals.lua works correctly.

This test file verifies:
1. Both contexts (hudmanagerpd2 and newraycastweaponbase) load correctly
2. Medal constants and functions are exposed via KH
3. Core.lua references use KH prefix correctly
4. No undefined references remain in core.lua
"""
import unittest
from pathlib import Path
from lupa import LuaRuntime

ROOT = Path(__file__).parent.parent

class MedalExtractionContextTests(unittest.TestCase):
    """Test medal extraction across multiple SuperBLT contexts."""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)

        # Minimal SuperBLT stubs
        self.lua.globals().ModPath = ROOT.as_posix() + '/'
        self.lua.execute('''
            -- SuperBLT globals
            Hooks = {callbacks = {}, post_hook_counts = {}}
            function Hooks:PostHook(class, method, id, fn)
                if not self.callbacks then self.callbacks = {} end
                self.post_hook_counts[id] = (self.post_hook_counts[id] or 0) + 1
                self.callbacks[id] = fn
            end
            function Hooks:PreHook(class, method, id, fn)
                if not self.callbacks then self.callbacks = {} end
                self.callbacks[id] = fn
            end
            function Hooks:Add(...) end

            -- Game managers
            HUDManager = {
                sync_start_assault = function() end,
                sync_end_assault = function() end
            }
            PlayerManager = {
                spawned_player = function() return true end
            }
            PlayerInventory = {
                equip_selection = function() end
            }
            CopDamage = {
                is_civilian = function(id) return id == 'civilian' end
            }
            PlayerDamage = {
                damage_tase=function() end,
                damage_bullet=function() end,
                damage_melee=function() end,
                damage_explosion=function() end,
                damage_fire=function() end,
                on_downed=function() end,
                on_incapacitated=function() end,
                on_arrested=function() end,
                set_health=function() end,
                _upd_health_regen=function() end
            }
            PlayerMovement = {
                on_SPOOCed=function() end
            }
            RaycastWeaponBase = {
                _check_kill_achievements=function() end
            }
            NewRaycastWeaponBase = {
                on_reload = function() end
            }

            -- Game state
            managers = {}
            managers.player = {
                player_unit = function() return {position = function() return {x=0,y=0,z=0} end} end,
                current_state = function() return 'standard' end,
                register_message = function() end
            }

            tweak_data = {
                weapon = {},
                hud_icons = {
                    get_icon_data = function(self, name)
                        return 'resolved/' .. name, {0,0,1,1}
                    end
                }
            }

            DB = {has = function() return true end}
            function Idstring(value) return value end
            function Vector3(...) return {...} end
            mvector3 = {
                distance = function(a, b)
                    local x = (a.x or 0) - (b.x or 0)
                    local y = (a.y or 0) - (b.y or 0)
                    local z = (a.z or 0) - (b.z or 0)
                    return math.sqrt(x*x + y*y + z*z)
                end
            }

            function log(...) end
            function alive(x) return x ~= nil and x ~= false end

            Color = setmetatable(
                {white = {}, black = {}},
                {__call = function(...) return {} end}
            )

            game_t = 100
            state_name = 'menu_main'
            is_client = false

            Network = {
                is_client = function() return is_client end
            }

            TimerManager = {
                game = function() return {time = function() return game_t end} end
            }

            game_state_machine = {
                last_queued_state_name = function() return state_name end
            }

            local_player = {
                position = function() return {x=0,y=0,z=0} end
            }

            registered_messages = {}

            function enemy(id, animation, rope, action, position)
                return {
                    base = function() return {_tweak_table = id or 'cop'} end,
                    anim_data = function() return animation or {} end,
                    position = function() return position or {x=0,y=0,z=0} end,
                    movement = function() return {
                        _active_actions = {action},
                        rope_unit = function() return rope end
                    } end
                }
            end
        ''')

    def test_hudmanagerpd2_context_loads_both_files(self):
        """Verify core.lua and ky_combat_medals.lua both load in hudmanagerpd2 context."""
        self.lua.globals().RequiredScript = 'lib/managers/hudmanagerpd2'

        core_src = (ROOT / 'lua' / 'core.lua').read_text(encoding='utf-8-sig')
        self.lua.execute(core_src)

        medals_src = (ROOT / 'lua' / 'ky_combat_medals.lua').read_text(encoding='utf-8-sig')
        self.lua.execute(medals_src)

        # Verify KH table exists and has medal constants
        kh = self.lua.eval('kyohud')
        self.assertIsNotNone(kh)

        # Check that medal constants are exposed
        self.assertIsNotNone(self.lua.eval('kyohud.EVENT_MEDAL_DEFINITIONS'))
        self.assertIsNotNone(self.lua.eval('kyohud.EVENT_MEDAL_ORDER'))
        self.assertIsNotNone(self.lua.eval('kyohud.KILL_MEDAL_THRESHOLDS'))
        self.assertIsNotNone(self.lua.eval('kyohud.SENTRY_KILL_MEDAL_THRESHOLDS'))
        self.assertIsNotNone(self.lua.eval('kyohud.LAST_BREATH_MEDAL_COOLDOWN'))
        self.assertIsNotNone(self.lua.eval('kyohud.SPRAY_DOWN_WINDOW'))
        self.assertIsNotNone(self.lua.eval('kyohud.MEDAL_CARD_DURATION'))
        self.assertIsNotNone(self.lua.eval('kyohud.MAX_MEDAL_QUEUE'))

        # Check that medal functions are exposed
        self.assertIsNotNone(self.lua.eval('kyohud.MakeKillMedalCard'))
        self.assertIsNotNone(self.lua.eval('kyohud.MakeEventMedalCard'))
        self.assertIsNotNone(self.lua.eval('kyohud.MakeSentryKillMedalCard'))
        self.assertIsNotNone(self.lua.eval('kyohud.SentryIconDescriptor'))

    def test_newraycastweaponbase_context_loads_medals(self):
        """Verify ky_combat_medals.lua loads correctly in newraycastweaponbase context."""
        self.lua.globals().RequiredScript = 'lib/units/weapons/newraycastweaponbase'

        # First load core.lua in hudmanagerpd2 context to set up KH
        self.lua.globals().RequiredScript = 'lib/managers/hudmanagerpd2'
        core_src = (ROOT / 'lua' / 'core.lua').read_text(encoding='utf-8-sig')
        self.lua.execute(core_src)

        medals_src = (ROOT / 'lua' / 'ky_combat_medals.lua').read_text(encoding='utf-8-sig')
        self.lua.execute(medals_src)

        # Now load in newraycastweaponbase context
        self.lua.globals().RequiredScript = 'lib/units/weapons/newraycastweaponbase'
        self.lua.execute(medals_src)
        self.lua.execute(medals_src)

        # Verify reload hook was installed exactly once despite a repeated load.
        hook_installed = self.lua.eval('kyohud._spray_down_reload_hook_installed')
        self.assertTrue(hook_installed)
        self.assertEqual(
            1,
            self.lua.eval('Hooks.post_hook_counts.KH_ResetSprayDownOnReload'),
        )

    def test_core_uses_kh_prefix_for_medals(self):
        """Verify core.lua uses KH prefix for all medal references."""
        core_src = (ROOT / 'lua' / 'core.lua').read_text(encoding='utf-8-sig')

        # Check that medal constants are referenced with KH. prefix
        # These should appear in the code
        self.assertIn('KH.EVENT_MEDAL_DEFINITIONS', core_src)
        self.assertIn('KH.EVENT_MEDAL_ORDER', core_src)
        self.assertIn('KH.KILL_MEDAL_THRESHOLDS', core_src)
        self.assertIn('KH.SENTRY_KILL_MEDAL_THRESHOLDS', core_src)
        self.assertIn('KH.LAST_BREATH_MEDAL_COOLDOWN', core_src)
        self.assertIn('KH.SPRAY_DOWN_WINDOW', core_src)
        self.assertIn('KH.MEDAL_CARD_DURATION', core_src)
        self.assertIn('KH.MAX_MEDAL_QUEUE', core_src)

        # Check that medal functions are called with KH. prefix
        self.assertIn('KH.MakeKillMedalCard', core_src)
        self.assertIn('KH.MakeEventMedalCard', core_src)
        self.assertIn('KH.MakeSentryKillMedalCard', core_src)
        self.assertIn('KH.SentryIconDescriptor', core_src)

    def test_no_bare_medal_references_in_core(self):
        """Verify core.lua has no bare (unprefixed) medal constant references."""
        core_src = (ROOT / 'lua' / 'core.lua').read_text(encoding='utf-8-sig')
        lines = core_src.split('\n')

        # List of medal constants/functions that should NOT appear bare
        bare_symbols = [
            'EVENT_MEDAL_DEFINITIONS',
            'EVENT_MEDAL_ORDER',
            'KILL_MEDAL_THRESHOLDS',
            'SENTRY_KILL_MEDAL_THRESHOLDS',
            'LAST_BREATH_MEDAL_COOLDOWN',
            'SPRAY_DOWN_WINDOW',
            'MEDAL_CARD_DURATION',
            'MAX_MEDAL_QUEUE',
            'MEDAL_POST_W',
            'MEDAL_RIBBON_RATIO',
            'MEDAL_ROW_GAP',
            'MEDAL_TOP_GAP',
            'MEDAL_CHEVRON_STYLE',
            'MEDAL_CHEVRON_GROUP_W',
            'MEDAL_CHEVRON_MARGIN',
            'MEDAL_CHEVRON_TEXT_GAP',
            'MEDAL_CONTENT_PADDING',
            'MEDAL_ICON_TEXT_GAP',
            'MEDAL_ICON_H_RATIO',
            'MEDAL_ICON_MIN',
            'MEDAL_ICON_MAX',
            'KILL_MEDAL_COLOR',
            'MEDAL_KIND_WEAPON_STREAK',
            'MEDAL_KIND_KILL_TOTAL',
            'MEDAL_KIND_EVENT',
            'MEDAL_KIND_SENTRY_KILL',
            'make_kill_medal_card',
            'make_event_medal_card',
            'make_sentry_kill_medal_card',
            'sentry_icon_descriptor',
            'draw_medal_frame',
            'draw_medal_edge',
            'medal_frame_gradient_for',
        ]

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith('--'):
                continue

            # Check for bare references (not prefixed with KH.)
            for symbol in bare_symbols:
                # Look for the symbol not preceded by "KH." or "C."
                import re
                # Match symbol that's not preceded by KH. or C.
                pattern = r'(?<!KH\.)(?<!C\.)\b' + re.escape(symbol) + r'\b'
                if re.search(pattern, line):
                    # Allow if it's in a comment at end of line
                    if '--' in line:
                        code_part = line.split('--')[0]
                        if not re.search(pattern, code_part):
                            continue

                    self.fail(
                        f"Line {line_num} contains bare reference to '{symbol}': {line.strip()}"
                    )

    def test_sentry_icon_descriptor_not_duplicated_in_core(self):
        """Verify sentry_icon_descriptor is not defined in core.lua."""
        core_src = (ROOT / 'lua' / 'core.lua').read_text(encoding='utf-8-sig')

        # Should not have local SENTRY_ICON_DESCRIPTOR
        self.assertNotIn('local SENTRY_ICON_DESCRIPTOR', core_src)

        # Should not have local function sentry_icon_descriptor
        self.assertNotIn('local function sentry_icon_descriptor', core_src)

        # Should not have function KH.sentry_icon_descriptor (duplicate)
        self.assertNotIn('function KH.SentryIconDescriptor', core_src)

        # But should have comment about it being in ky_combat_medals.lua
        self.assertIn('sentry_icon_descriptor', core_src)  # In comments
        self.assertIn('ky_combat_medals.lua', core_src)

    def test_medal_rendering_not_duplicated_in_core(self):
        """Verify medal rendering functions are not defined in core.lua."""
        core_src = (ROOT / 'lua' / 'core.lua').read_text(encoding='utf-8-sig')

        # Should not have local MEDAL_POST_W, MEDAL_RIBBON_RATIO, etc.
        self.assertNotIn('local MEDAL_POST_W', core_src)
        self.assertNotIn('local MEDAL_RIBBON_RATIO', core_src)
        self.assertNotIn('local MEDAL_ROW_GAP', core_src)
        self.assertNotIn('local MEDAL_TOP_GAP', core_src)
        self.assertNotIn('local MEDAL_CHEVRON_STYLE', core_src)

        # Should not have local function draw_medal_edge
        self.assertNotIn('local function draw_medal_edge', core_src)

        # Should not have function RENDER_CACHES.medal_frame_gradient_for
        self.assertNotIn('function RENDER_CACHES.medal_frame_gradient_for', core_src)

        # Should not have local function draw_medal_frame
        self.assertNotIn('local function draw_medal_frame', core_src)

    def test_mod_txt_load_order(self):
        """Verify mod.txt loads ky_combat_medals.lua after core.lua in hudmanagerpd2."""
        import json

        mod_txt = (ROOT / 'mod.txt').read_text(encoding='utf-8-sig')
        mod_data = json.loads(mod_txt)

        hooks = mod_data['hooks']

        # Find all hudmanagerpd2 hooks
        hudmanager_hooks = []
        for hook in hooks:
            if hook['hook_id'] == 'lib/managers/hudmanagerpd2':
                hudmanager_hooks.append(hook['script_path'])

        # Verify core.lua comes before ky_combat_medals.lua
        self.assertIn('lua/core.lua', hudmanager_hooks)
        self.assertIn('lua/ky_combat_medals.lua', hudmanager_hooks)

        core_idx = hudmanager_hooks.index('lua/core.lua')
        medals_idx = hudmanager_hooks.index('lua/ky_combat_medals.lua')

        self.assertLess(
            core_idx,
            medals_idx,
            "core.lua must be loaded before ky_combat_medals.lua in hudmanagerpd2 context"
        )

        # Verify newraycastweaponbase also loads ky_combat_medals.lua
        newraycast_hooks = []
        for hook in hooks:
            if hook['hook_id'] == 'lib/units/weapons/newraycastweaponbase':
                newraycast_hooks.append(hook['script_path'])

        self.assertIn('lua/ky_combat_medals.lua', newraycast_hooks)

    def test_kh_combat_medals_initialized_flag(self):
        """Verify _combat_medals_initialized flag prevents duplicate initialization."""
        self.lua.globals().RequiredScript = 'lib/managers/hudmanagerpd2'

        core_src = (ROOT / 'lua' / 'core.lua').read_text(encoding='utf-8-sig')
        self.lua.execute(core_src)

        medals_src = (ROOT / 'lua' / 'ky_combat_medals.lua').read_text(encoding='utf-8-sig')

        # Load once
        self.lua.execute(medals_src)
        self.assertTrue(self.lua.eval('kyohud._combat_medals_initialized'))

        # Store original function references as Lua values
        original_make_kill_str = self.lua.eval('tostring(kyohud.MakeKillMedalCard)')
        original_make_event_str = self.lua.eval('tostring(kyohud.MakeEventMedalCard)')

        # Load again (should be idempotent due to guard)
        self.lua.execute(medals_src)

        # Functions should have the same string representation (same Lua function object)
        self.assertEqual(original_make_kill_str, self.lua.eval('tostring(kyohud.MakeKillMedalCard)'))
        self.assertEqual(original_make_event_str, self.lua.eval('tostring(kyohud.MakeEventMedalCard)'))

        # Verify the guard flag is still set
        self.assertTrue(self.lua.eval('kyohud._combat_medals_initialized'))

if __name__ == '__main__':
    unittest.main()
