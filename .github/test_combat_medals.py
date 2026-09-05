"""Real KyoHUD LuaJIT chunks with minimal Diesel/SuperBLT stubs.
Run: uv run --with lupa python -B -m unittest discover -s .github -p test_combat_medals.py -v
"""
from pathlib import Path
import unittest
from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]

class CombatMedalTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + '/'
        self.lua.execute('''
            Hooks = {callbacks = {}}
            function Hooks:PostHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:PreHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:Add(...) end
            HUDManager = {sync_start_assault = function() end, sync_end_assault = function() end}
            PlayerManager = {}; CopDamage = {is_civilian = function(id) return id == 'civilian' end}
            managers = {}; tweak_data = {hud_icons = {get_icon_data = function(self, name) return name, {0,0,1,1} end}}
            function Vector3(...) return {...} end
            function log(...) end
            function alive(x) return x ~= nil and x ~= false end
            Color = setmetatable({white = {}, black = {}}, {__call = function(...) return {} end})
            game_t = 100; state_name = 'menu_main'; is_client = false
            Network = {is_client = function() return is_client end}
            TimerManager = {game = function() return {time = function() return game_t end} end}
            game_state_machine = {last_queued_state_name = function() return state_name end}
            local_player = {}
            managers.player = {player_unit = function() return local_player end,
                current_state = function() return 'standard' end}
            function enemy(id, animation, rope)
                return {base = function() return {_tweak_table = id or 'cop'} end,
                    anim_data = function() return animation or {} end,
                    movement = function() return {rope_unit = function() return rope end} end}
            end
        ''')
        self.load('ky_buffhud.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_killfeed.lua', 'lib/managers/playermanager')
        self.load('ky_killfeed.lua', 'lib/units/enemies/cop/copdamage')
        self.lua.execute('''
            kyohud.settings = {enable_killfeed = true, killfeed_size = 3}
            kyohud:ResetHeistCombatState()
            cards = {}
            original_show = kyohud._show_medal_card
            kyohud._show_medal_card = function(self, t, card, preview)
                if card then cards[#cards+1] = card end
                return original_show(self, t, card, preview)
            end
            function kill(events, unit, civilian)
                kyohud:RecordScoredKill(unit or enemy(), civilian and 'civilian' or 'cop',
                    'Enemy', civilian or false, nil, events)
            end
            function count_event(id)
                local n = 0
                for _, card in ipairs(cards) do if card.event == id then n = n + 1 end end
                return n
            end
        ''')

    def load(self, name, context):
        self.lua.globals().RequiredScript = context
        self.lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

    def test_headshot_is_not_an_event_medal(self):
        self.lua.execute("kill({headshot = true}); assert(count_event('headshot') == 0, 'obsolete headshot medal emitted')")

    def test_first_strike_once_per_assault_after_dedup(self):
        self.lua.execute('''
            assert(Hooks.callbacks.KH_EventAssaultStart, 'assault start hook missing')
            assert(Hooks.callbacks.KH_EventAssaultEnd, 'assault end hook missing')
            local seen = enemy()
            kill(nil, seen)
            assert(count_event('first_strike') == 0, 'outside assault')
            Hooks.callbacks.KH_EventAssaultStart({}, 1)
            kill(nil, seen)
            kill(nil, nil, true)
            assert(count_event('first_strike') == 0, 'duplicate/civilian consumed first kill')
            kill(nil)
            kill(nil)
            Hooks.callbacks.KH_EventAssaultStart({}, 1)
            kill(nil)
            assert(count_event('first_strike') == 1, 'first strike must be once per wave')
            Hooks.callbacks.KH_EventAssaultEnd({})
            kill(nil)
            assert(count_event('first_strike') == 1, 'control phase awarded')
            Hooks.callbacks.KH_EventAssaultStart({}, 1)
            kill(nil)
            assert(count_event('first_strike') == 2, 'reused/capped wave id must still reset')
            kyohud:ResetWeaponStreaks()
            kill(nil)
            assert(count_event('first_strike') == 2, 'down must not reset assault medal')
            kyohud:ResetHeistCombatState()
            kill(nil)
            assert(count_event('first_strike') == 2, 'heist reset kept assault active')
        ''')

    def test_rope_tiers_window_and_resets(self):
        self.lua.execute('''
            local same = enemy()
            kill({rope=true}, same)
            kill({rope=true}, same)
            assert(count_event('rope') == 1, 'duplicate counted')
            game_t = 103
            kill({rope=true})
            assert(count_event('rope') == 1, 'second rope kill must be silent')
            game_t = 105
            kill({rope=true})
            assert(count_event('rope') == 2 and cards[#cards].tier_index == 2, 'third kill tier')
            game_t = 106
            kill({rope=true}, nil, true)
            kill({run=true})
            game_t = 108
            kill({rope=true})
            assert(count_event('rope') == 2, 'civilian/nonrope advanced counter')
            game_t = 111
            kill({rope=true})
            assert(count_event('rope') == 3 and cards[#cards].tier_index == 3, 'fifth kill tier')
            local labels = {}
            for _, card in ipairs(cards) do if card.event == 'rope' then labels[card.label] = true end end
            local n = 0; for _ in pairs(labels) do n = n + 1 end
            assert(n == 3, 'tiers need distinct labels')
            game_t = 112; kill({rope=true})
            assert(count_event('rope') == 3, 'must stay silent after max')
            game_t = 115.001; kill({rope=true})
            assert(count_event('rope') == 4 and cards[#cards].tier_index == 1, 'gap >3 must reset')
            kyohud:ResetWeaponStreaks(); kill({rope=true})
            assert(count_event('rope') == 5 and cards[#cards].tier_index == 1, 'down reset')
            kyohud:ResetHeistCombatState(); kill({rope=true})
            assert(count_event('rope') == 6 and cards[#cards].tier_index == 1, 'heist reset')
        ''')

    def test_preview_covers_five_events_and_three_rope_tiers(self):
        self.lua.execute('''
            local seen = {}
            for i = 1, 12 do
                kyohud:DebugSimulate(0)
                local card = kyohud._medal_card
                if card and card.event then
                    seen[card.event .. ':' .. tostring(card.tier_index or 0)] = true
                end
            end
            for _, id in ipairs({'first_strike','grave','low_hp','reload'}) do
                assert(seen[id .. ':0'], 'preview missing ' .. id)
            end
            for i = 1, 3 do assert(seen['rope:' .. i], 'preview missing rope tier ' .. i) end
            assert(not seen['headshot:0'], 'old headshot preview')
            assert(not seen['run:0'], 'removed run preview')
        ''')

    def test_event_localizations(self):
        import json
        ids = ['first_strike', 'grave', 'low_hp', 'reload', 'rope', 'rope_3', 'rope_5']
        fallback = (ROOT / 'lua/ky_localization.lua').read_text(encoding='utf-8-sig')
        for language in ('english', 'french'):
            data = json.loads((ROOT / 'loc' / (language + '.json')).read_text(encoding='utf-8-sig'))
            for event in ids:
                key = 'ky_hud_event_medal_' + event
                self.assertTrue(data.get(key), (language, key))
                self.assertIn(key, fallback)
            for removed in ('ky_hud_event_medal_headshot', 'ky_hud_event_medal_run'):
                self.assertNotIn(removed, data)
        self.assertNotIn('ky_hud_event_medal_headshot', fallback)
        self.assertNotIn('ky_hud_event_medal_run', fallback)

    def test_host_predeath_capture_and_client_hooks(self):
        self.lua.execute('''
            managers.player.current_state = function() return 'bleed_out' end
            local_player.character_damage = function() return {health_ratio = function() return 0.05 end} end
            Hooks.callbacks.KH_EventAssaultStart({}, 1)
            local anim = {reload=true, run=true}
            local victim = enemy('cop', anim, {})
            local damage = {_unit=victim}
            local attack = {attacker_unit=local_player, variant='bullet', headshot=true}
            Hooks.callbacks.KH_OnEnemyDiePre(damage, attack)
            anim.reload = nil; anim.run = nil
            Hooks.callbacks.KH_OnEnemyDie(damage, attack)
            for _, id in ipairs({'first_strike','grave','low_hp','reload','rope'}) do
                assert(count_event(id) == 1, 'host missing ' .. id)
            end
            assert(count_event('headshot') == 0)
            assert(count_event('run') == 0, 'removed run medal emitted')
            is_client = true
            Hooks.callbacks.KH_OnLocalPlayerKillshot({}, victim, 'bullet', true)
            assert(count_event('first_strike') == 1 and count_event('grave') == 1, 'host/client duplicate')
            Hooks.callbacks.KH_EventAssaultEnd({})
            Hooks.callbacks.KH_EventAssaultStart({}, 2)
            Hooks.callbacks.KH_OnLocalPlayerKillshot({}, enemy('cop', {reload=true,run=true}, {}), 'bullet', true)
            assert(count_event('first_strike') == 2 and count_event('reload') == 2)
            assert(count_event('run') == 0, 'client emitted removed run medal')
            local before = #cards
            Hooks.callbacks.KH_OnLocalPlayerKillshot({}, enemy('civilian', {reload=true}, {}), 'bullet', true)
            assert(#cards == before, 'civilian medals')
            managers.player.current_state = function() error('engine') end
            local_player.character_damage = function() error('engine') end
            local broken = enemy()
            broken.anim_data = function() error('engine') end
            broken.movement = function() error('engine') end
            Hooks.callbacks.KH_OnLocalPlayerKillshot({}, broken, 'bullet', false)
            assert(#cards == before, 'failed engine read leaked prior events')
        ''')

    def test_hidden_hud_preserves_medal_and_heist_accounting(self):
        self.lua.execute('''
            Hooks.callbacks.KH_EventAssaultStart({}, 1)
            kyohud.settings.enable_killfeed = false
            kill({rope=true}); kill({rope=true}); kill({rope=true})
            assert(kyohud._heist_kill_count == 3, 'hidden enemy kills lost')
            assert(count_event('first_strike') == 1, 'hidden first strike lost')
            assert(count_event('rope') == 2, 'hidden rope tiers lost')
            kyohud.settings.enable_killfeed = true
            kill({rope=true}); kill({rope=true})
            assert(kyohud._heist_kill_count == 5)
            assert(count_event('first_strike') == 1, 'first strike replayed')
            assert(count_event('rope') == 3 and cards[#cards].tier_index == 3)
        ''')

    def test_health_threshold_and_player_state_fallback(self):
        self.lua.execute('''
            local ratio = 0.1
            local_player.character_damage = function() return {health_ratio = function() return ratio end} end
            assert(not kyohud:IsLocalPlayerLowHealth())
            ratio = 0.099; assert(kyohud:IsLocalPlayerLowHealth())
            ratio = 0/0; assert(not kyohud:IsLocalPlayerLowHealth())
            managers.player.current_state = nil
            local_player.movement = function() return {current_state_name = function() return 'bleed_out' end} end
            assert(kyohud:IsLocalPlayerDowned())
        ''')

    def test_exact_killfeed_context_registrations(self):
        for context, expected in (
            ('lib/managers/playermanager', {'KH_OnLocalPlayerKillshot'}),
            ('lib/units/enemies/cop/copdamage', {'KH_OnEnemyDiePre', 'KH_OnEnemyDie'}),
            ('lib/units/civilians/civiliandamage', set()),
        ):
            self.lua.execute('Hooks.callbacks = {}')
            self.load('ky_killfeed.lua', context)
            self.assertEqual(set(self.lua.globals().Hooks.callbacks.keys()), expected)

if __name__ == '__main__':
    unittest.main()
