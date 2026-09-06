"""Regression tests against real mod chunks, with Diesel/SuperBLT API stubs.

Run: uv run --with lupa python -B -m unittest discover -s .github -p test_combat_state.py -v
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class CombatStateTests(unittest.TestCase):
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
            Color = setmetatable({white = {}, black = {}}, {
                __call = function(...) return {} end
            })
            game_t = 100; app_t = 1000; state_name = 'menu_main'
            TimerManager = {game = function() return {time = function() return game_t end} end}
            Application = {time = function() return app_t end}
            game_state_machine = {last_queued_state_name = function() return state_name end}
        ''')
        for name in ("ky_buffhud.lua", "ky_hooks.lua"):
            self.lua.execute((ROOT / "lua" / name).read_text(encoding="utf-8-sig"))
        self.lua.execute('''
            kyohud.settings = {enable_killfeed = true, killfeed_size = 3}
            kyohud:ResetHeistCombatState()
        ''')

    def test_temporary_buff_uses_application_clock(self):
        self.lua.execute('''
            local captured
            kyohud.GetBuffTargets = function() return {'overkill'} end
            kyohud.handle_buff_event = function(self, event, id, data) captured = data.duration end
            local pm = {
                _temporary_upgrades = {temporary = {
                    overkill_damage_multiplier = {expire_time = 1020}
                }},
                upgrade_value = function() return {1.75, 20} end
            }
            Hooks.callbacks.KH_OnBuffOn(pm, 'temporary', 'overkill_damage_multiplier')
            assert(captured == 20, 'expected 20 seconds remaining, got ' .. tostring(captured))
        ''')

    def test_hidden_killfeed_preserves_heist_accounting(self):
        self.lua.execute('''
            kyohud:add_kill('Enemy', 10, true)
            kyohud.settings.enable_killfeed = false
            kyohud:add_kill('Enemy', 20, true)
            kyohud.settings.enable_killfeed = true
            kyohud:add_kill('Enemy', 30, true)
            assert(kyohud._heist_score_total == 60, 'hidden kills lost from total')
            assert(kyohud._heist_kill_count == 3, 'hidden kills lost from count')
            assert(kyohud._heist_score_best_streak == 60, 'hidden kills lost from best streak')
            kyohud.settings.enable_killfeed = false
            game_t = 110
            kyohud:add_kill('Civilian', -15, false)
            assert(kyohud._heist_score_total == 45, 'hidden civilian penalty lost')
            assert(kyohud._heist_kill_count == 3, 'civilian counted as enemy')
            assert(kyohud._killfeed_score_total == -15, 'expired streak not reset')
            assert(kyohud._heist_score_best_streak == 60, 'best streak decreased')
        ''')

    def test_clear_without_preview_preserves_live_state(self):
        self.lua.execute('''
            kyohud:add_kill('Enemy', 10, true)
            local buffs = kyohud._buffs
            local kills = kyohud._kills
            kyohud:DebugClear()
            assert(kyohud._heist_score_total == 10, 'clear destroyed live score')
            assert(kyohud._heist_kill_count == 1, 'clear destroyed live kill count')
            assert(kyohud._buffs == buffs and kyohud._kills == kills, 'clear replaced live tables')
        ''')

    def test_preview_refused_outside_main_menu(self):
        self.lua.execute('''
            kyohud:add_kill('Enemy', 10, true)
            local buffs = kyohud._buffs
            local kills = kyohud._kills
            for _, state in ipairs({'ingame_standard', 'ingame_waiting_for_players',
                    'ingame_waiting_for_respawn', 'ingame_bleed_out', 'victoryscreen'}) do
                state_name = state
                kyohud:DebugSimulate(0)
                assert(not kyohud._debug_preview_active, 'preview started in ' .. state)
                assert(kyohud._heist_score_total == 10, 'preview changed live score')
                assert(kyohud._heist_kill_count == 1, 'preview changed live count')
                assert(kyohud._buffs == buffs and kyohud._kills == kills, 'preview changed live tables')
            end
            game_state_machine = nil
            kyohud:DebugSimulate(0)
            assert(not kyohud._debug_preview_active, 'preview allowed with unknown game state')
        ''')

    def test_main_menu_preview_cycles_and_clears(self):
        self.lua.execute('''
            local clears = 0
            kyohud._panel = {clear = function() clears = clears + 1 end}
            kyohud:DebugSimulate(8)
            assert(kyohud._debug_preview_active)
            local preview_index = kyohud._debug_banner_preview_index
            local score = kyohud._heist_score_total
            assert(#kyohud._kills == 3 and next(kyohud._buffs))
            kyohud:DebugSimulate(8)
            assert(#kyohud._kills == 3 and kyohud._heist_score_total == score)
            assert(kyohud._debug_banner_preview_index ~= preview_index)
            kyohud:DebugClear()
            assert(not kyohud._debug_preview_active)
            assert(#kyohud._kills == 0 and next(kyohud._buffs) == nil)
            assert(kyohud._heist_score_total == 0 and clears == 1)
            kyohud:DebugClear()
            assert(clears == 1, 'clear without preview touched panel')
        ''')

    def test_new_hud_resets_preview_before_real_kills(self):
        self.lua.execute('''
            kyohud:DebugSimulate(8)
            kyohud.ensure_panel = function() end
            kyohud.TryRegisterGameInfoBridge = function() end
            kyohud.RefreshDetectedBuffs = function() end
            Hooks.callbacks.KH_InitHUD()
            assert(not kyohud._debug_preview_active)
            assert(kyohud._heist_score_total == 0 and kyohud._heist_kill_count == 0)
            assert(kyohud._bridge_delayed_sync_done == false)
            kyohud:add_kill('Enemy', 10, true)
            kyohud:DebugClear()
            assert(kyohud._heist_score_total == 10 and kyohud._heist_kill_count == 1)
        ''')

    def test_temporary_buff_duration_fallback(self):
        self.lua.execute('''
            local captured
            kyohud.GetBuffTargets = function() return {'overkill'} end
            kyohud.handle_buff_event = function(self, event, id, data) captured = data.duration end
            local pm = {upgrade_value = function() return {1.75, 12} end}
            Hooks.callbacks.KH_OnBuffOn(pm, 'temporary', 'overkill_damage_multiplier')
            assert(captured == 12)
            pm.upgrade_value = function() return nil end
            Hooks.callbacks.KH_OnBuffOn(pm, 'temporary', 'overkill_damage_multiplier')
            assert(captured == 5)
        ''')


if __name__ == "__main__":
    unittest.main()
