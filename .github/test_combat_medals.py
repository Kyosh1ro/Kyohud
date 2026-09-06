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
            PlayerManager = {}; PlayerInventory = {equip_selection = function() end}
            CopDamage = {is_civilian = function(id) return id == 'civilian' end}
            PlayerDamage = {
                damage_tase=function() end, damage_bullet=function() end,
                damage_melee=function() end, damage_explosion=function() end,
                damage_fire=function() end, on_downed=function() end,
                on_incapacitated=function() end, on_arrested=function() end,
                set_health=function() end, _upd_health_regen=function() end
            }
            PlayerMovement = {on_SPOOCed=function() end}
            RaycastWeaponBase = {_check_kill_achievements=function() end}
            hud_icon_calls = 0
            managers = {}; tweak_data = {
                weapon = {
                    test_sniper = {categories = {'snp'}},
                    test_shotgun = {categories = {'shotgun'}}
                },
                hud_icons = {get_icon_data = function(self, name)
                    hud_icon_calls = hud_icon_calls + 1
                    return 'resolved/' .. name, {0,0,1,1}
                end}
            }
            DB = {has = function() return true end}
            function Idstring(value) return value end
            function Vector3(...) return {...} end
            mvector3 = {distance = function(a, b)
                local x = (a.x or 0) - (b.x or 0)
                local y = (a.y or 0) - (b.y or 0)
                local z = (a.z or 0) - (b.z or 0)
                return math.sqrt(x*x + y*y + z*z)
            end}
            function log(...) end
            function alive(x) return x ~= nil and x ~= false end
            Color = setmetatable({white = {}, black = {}}, {__call = function(...) return {} end})
            game_t = 100; state_name = 'menu_main'; is_client = false
            Network = {is_client = function() return is_client end}
            TimerManager = {game = function() return {time = function() return game_t end} end}
            game_state_machine = {last_queued_state_name = function() return state_name end}
            local_player = {position = function() return {x=0,y=0,z=0} end}
            managers.player = {player_unit = function() return local_player end,
                current_state = function() return 'standard' end}
            function enemy(id, animation, rope, action, position)
                return {base = function() return {_tweak_table = id or 'cop'} end,
                    anim_data = function() return animation or {} end,
                    position = function() return position or {x=0,y=0,z=0} end,
                    movement = function() return {
                        _active_actions = {action},
                        rope_unit = function() return rope end
                    } end}
            end
        ''')
        self.load('ky_buffhud.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_killfeed.lua', 'lib/managers/playermanager')
        self.load('ky_killfeed.lua', 'lib/units/enemies/cop/copdamage')
        self.load('ky_playerinventory.lua', 'lib/units/beings/player/playerinventory')
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
            function last_event(id)
                for i = #cards, 1, -1 do
                    if cards[i].event == id then return cards[i] end
                end
            end
        ''')

    def load(self, name, context):
        self.lua.globals().RequiredScript = context
        self.lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

    def test_headshot_is_killfeed_icon_not_event_medal(self):
        self.lua.execute('''
            kill({headshot = true})
            local headshot = kyohud._kills[#kyohud._kills]
            assert(headshot.headshot == true, 'headshot flag missing from kill entry')
            assert(headshot.headshot_icon and headshot.headshot_icon.texture == 'resolved/pd2_kill',
                'pd2_kill was not resolved before draw')
            assert(headshot.headshot_icon.rect[3] == 1, 'resolved atlas rect missing')
            assert(count_event('headshot') == 0, 'obsolete headshot medal emitted')

            local calls = hud_icon_calls
            kill(nil)
            local normal = kyohud._kills[#kyohud._kills]
            assert(normal.headshot == false, 'normal kill marked as headshot')
            assert(normal.headshot_icon == nil, 'normal kill reserved a headshot icon')
            assert(hud_icon_calls == calls, 'normal kill resolved the headshot texture')
        ''')

    def test_headshot_preview_uses_normal_kill_card(self):
        self.lua.execute('''
            kyohud:DebugSimulate(0)
            local found
            for _, entry in ipairs(kyohud._kills) do
                if entry.headshot then found = entry break end
            end
            assert(found, 'preview has no headshot kill')
            assert(found.name and found.score_text, 'preview headshot is not a normal kill card')
            assert(found.headshot_icon and found.headshot_icon.texture == 'resolved/pd2_kill',
                'preview headshot icon unresolved')
        ''')

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

    def test_first_blood_once_per_heist_after_dedup(self):
        self.lua.execute('''
            local duplicate = enemy()
            kill(nil, nil, true)
            assert(count_event('first_blood') == 0, 'civilian consumed first blood')
            kill(nil, duplicate)
            kill(nil, duplicate)
            kill(nil)
            assert(count_event('first_blood') == 1, 'first blood must be once per heist')
            assert(kyohud._first_blood_done == true)
            kyohud:ResetWeaponStreaks()
            kill(nil)
            assert(count_event('first_blood') == 1, 'down reset first blood')
            kyohud:ResetHeistCombatState()
            assert(kyohud._first_blood_done == false)
            kill(nil)
            assert(count_event('first_blood') == 2, 'heist reset did not rearm first blood')
        ''')

    def test_flashbang_state_and_hotswap_window(self):
        self.lua.execute('''
            managers.environment_controller = {_current_flashbang = 0.05}
            assert(not kyohud:IsLocalPlayerFlashbanged(), 'threshold must be strict')
            managers.environment_controller._current_flashbang = 0.051
            assert(kyohud:IsLocalPlayerFlashbanged(), 'active flashbang not detected')
            managers.environment_controller = setmetatable({}, {
                __index = function() error('engine') end
            })
            assert(not kyohud:IsLocalPlayerFlashbanged(), 'fragile access was not protected')

            local inventory = {_equipped_selection = 1}
            Hooks.callbacks.KH_OnWeaponSwap(inventory, 1, false)
            assert(kyohud._last_weapon_switch_t == nil, 'spawn equip started hotswap window')
            game_t = 101
            inventory._equipped_selection = 2
            Hooks.callbacks.KH_OnWeaponSwap(inventory, 2, false)
            assert(kyohud._last_weapon_switch_t == 101, 'real switch was not timestamped')

            managers.environment_controller = {_current_flashbang = 0.2}
            is_client = true
            game_t = 103.499
            Hooks.callbacks.KH_OnLocalPlayerKillshot({}, enemy(), 'bullet', false)
            assert(count_event('blindfire') == 1, 'blindfire medal missing')
            assert(count_event('hotswap') == 1, 'hotswap medal missing inside window')

            game_t = 103.5
            Hooks.callbacks.KH_OnLocalPlayerKillshot({}, enemy(), 'bullet', false)
            assert(count_event('hotswap') == 1, 'hotswap window must be strictly below 2.5s')
            kyohud:ResetHeistCombatState()
            assert(kyohud._last_weapon_switch_t == nil, 'heist reset kept weapon timestamp')
        ''')

    def test_long_shot_uses_strict_thirty_meter_threshold(self):
        self.lua.execute('''
            assert(not kyohud:IsLongDistanceKill(
                enemy('cop', nil, nil, nil, {x=3000,y=0,z=0})),
                'exactly 30m must not trigger')
            assert(kyohud:IsLongDistanceKill(
                enemy('cop', nil, nil, nil, {x=3000.1,y=0,z=0})),
                'distance above 30m did not trigger')
            local broken = enemy()
            broken.position = function() error('engine') end
            assert(not kyohud:IsLongDistanceKill(broken), 'distance access was not protected')

            is_client = true
            Hooks.callbacks.KH_OnLocalPlayerKillshot({},
                enemy('cop', nil, nil, nil, {x=3001,y=0,z=0}),
                'bullet', false, 'test_sniper')
            assert(count_event('long_shot') == 1, 'long-shot medal missing from kill path')
            Hooks.callbacks.KH_OnLocalPlayerKillshot({},
                enemy('cop', nil, nil, nil, {x=2999,y=0,z=0}),
                'bullet', false, 'test_sniper')
            assert(count_event('long_shot') == 1, 'short kill emitted long-shot medal')
        ''')

    def test_overwatch_requires_sniper_weapon_and_sniper_target(self):
        self.lua.execute('''
            kyohud:RecordScoredKill(enemy('sniper'), 'sniper', 'Sniper', false,
                {variant='bullet', weapon_id='test_sniper'}, {})
            assert(count_event('overwatch') == 1, 'sniper versus sniper did not trigger')
            kyohud:RecordScoredKill(enemy('cop'), 'cop', 'Cop', false,
                {variant='bullet', weapon_id='test_sniper'}, {})
            kyohud:RecordScoredKill(enemy('sniper'), 'sniper', 'Sniper', false,
                {variant='bullet', weapon_id='test_shotgun'}, {})
            assert(count_event('overwatch') == 1,
                'invalid target or weapon triggered overwatch')
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
            assert(count_event('rope') == 2 and last_event('rope').tier_index == 2, 'third kill tier')
            game_t = 106
            kill({rope=true}, nil, true)
            kill({run=true})
            game_t = 108
            kill({rope=true})
            assert(count_event('rope') == 2, 'civilian/nonrope advanced counter')
            game_t = 111
            kill({rope=true})
            assert(count_event('rope') == 3 and last_event('rope').tier_index == 3, 'fifth kill tier')
            local labels = {}
            for _, card in ipairs(cards) do if card.event == 'rope' then labels[card.label] = true end end
            local n = 0; for _ in pairs(labels) do n = n + 1 end
            assert(n == 3, 'tiers need distinct labels')
            game_t = 112; kill({rope=true})
            assert(count_event('rope') == 3, 'must stay silent after max')
            game_t = 115.001; kill({rope=true})
            assert(count_event('rope') == 4 and last_event('rope').tier_index == 1, 'gap >3 must reset')
            kyohud:ResetWeaponStreaks(); kill({rope=true})
            assert(count_event('rope') == 5 and last_event('rope').tier_index == 1, 'down reset')
            kyohud:ResetHeistCombatState(); kill({rope=true})
            assert(count_event('rope') == 6 and last_event('rope').tier_index == 1, 'heist reset')
        ''')

    def test_preview_covers_event_medals_and_rope_tiers(self):
        self.lua.execute('''
            local seen = {}
            for i = 1, 22 do
                kyohud:DebugSimulate(0)
                local card = kyohud._medal_card
                if card and card.event then
                    seen[card.event .. ':' .. tostring(card.tier_index or 0)] = true
                end
            end
            for _, id in ipairs({
                'first_strike','grave','low_hp','reload','through_shield',
                'one_shot_two_kills','revenge','bulltrue','showstopper',
                'blindfire','first_blood','hotswap','overwatch','long_shot'
            }) do
                assert(seen[id .. ':0'], 'preview missing ' .. id)
            end
            for i = 1, 3 do assert(seen['rope:' .. i], 'preview missing rope tier ' .. i) end
            assert(not seen['headshot:0'], 'old headshot preview')
            assert(not seen['run:0'], 'removed run preview')
        ''')

    def test_event_localizations(self):
        import json
        ids = [
            'first_strike', 'grave', 'low_hp', 'reload', 'rope', 'rope_3',
            'rope_5', 'through_shield', 'one_shot_two_kills', 'revenge',
            'bulltrue', 'showstopper', 'blindfire', 'first_blood', 'hotswap',
            'overwatch', 'long_shot'
        ]
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
            assert(#kyohud._kills == 1 and kyohud._kills[1].headshot == true,
                'host headshot missing from killfeed')
            for _, id in ipairs({'first_strike','grave','low_hp','reload','rope'}) do
                assert(count_event(id) == 1, 'host missing ' .. id)
            end
            assert(count_event('headshot') == 0)
            assert(count_event('run') == 0, 'removed run medal emitted')
            is_client = true
            Hooks.callbacks.KH_OnLocalPlayerKillshot({}, victim, 'bullet', true)
            assert(#kyohud._kills == 1, 'host/client duplicate kill card')
            assert(count_event('first_strike') == 1 and count_event('grave') == 1, 'host/client duplicate')
            Hooks.callbacks.KH_EventAssaultEnd({})
            Hooks.callbacks.KH_EventAssaultStart({}, 2)
            Hooks.callbacks.KH_OnLocalPlayerKillshot({}, enemy('cop', {reload=true,run=true}, {}), 'bullet', true)
            assert(kyohud._kills[#kyohud._kills].headshot == true,
                'client headshot missing from killfeed')
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

    def test_cloaker_attack_state_and_revenge_events(self):
        self.lua.execute('''
            local flying = {
                type=function() return 'spooc' end,
                is_flying_strike=function() return true end
            }
            local ground = {
                type=function() return 'spooc' end,
                is_flying_strike=function() return false end
            }
            local flying_victim = enemy('spooc', {}, nil, flying)
            local ground_victim = enemy('spooc', {}, nil, ground)
            local attack = {attacker_unit=local_player, variant='bullet'}

            Hooks.callbacks.KH_OnEnemyDiePre({_unit=flying_victim}, attack)
            Hooks.callbacks.KH_OnEnemyDie({_unit=flying_victim}, attack)
            assert(count_event('bulltrue') == 1 and count_event('showstopper') == 0)

            Hooks.callbacks.KH_OnEnemyDiePre({_unit=ground_victim}, attack)
            Hooks.callbacks.KH_OnEnemyDie({_unit=ground_victim}, attack)
            assert(count_event('bulltrue') == 1 and count_event('showstopper') == 1)

            local revenge_victim = enemy('cop')
            kyohud._revenge_targets[revenge_victim] = true
            Hooks.callbacks.KH_OnEnemyDiePre({_unit=revenge_victim}, attack)
            Hooks.callbacks.KH_OnEnemyDie({_unit=revenge_victim}, attack)
            assert(count_event('revenge') == 1, 'revenge medal missing')
            assert(not kyohud._revenge_targets[revenge_victim], 'revenge target not consumed')
        ''')

    def test_weapon_hook_emits_cards_without_scoring(self):
        self.load('ky_raycastweaponbase.lua', 'lib/units/weapons/raycastweaponbase')
        self.lua.execute('''
            local before = kyohud._heist_kill_count
            local hook = Hooks.callbacks.KH_RaycastKillMedals
            assert(hook, 'raycast hook missing')
            hook({}, 1, {}, 'cop', false, false, false)
            hook({}, 2, {}, 'cop', false, false, false)
            hook({}, 3, {}, 'cop', false, false, false)
            assert(count_event('one_shot_two_kills') == 1, 'multi-kill emitted more than once')
            hook({}, 1, {}, 'shield', false, false, true)
            assert(count_event('through_shield') == 1, 'shield penetration missing')
            hook({}, 1, {}, 'cop', false, false, true)
            hook({}, 1, {}, 'shield', true, false, true)
            assert(count_event('through_shield') == 1, 'invalid shield medal')
            assert(kyohud._heist_kill_count == before, 'weapon hook changed kill scoring')
        ''')

    def test_revenge_target_capture_and_heist_reset(self):
        self.load('ky_playerdamage.lua', 'lib/units/beings/player/playerdamage')
        self.load('ky_playermovement.lua', 'lib/units/beings/player/playermovement')
        self.lua.execute('''
            local downer = enemy('cop')
            local damage = {}
            Hooks.callbacks.KH_RevengeRemember_damage_bullet(damage, {attacker_unit=downer})
            Hooks.callbacks.KH_ResetWeaponStreaks_on_downed(damage)
            Hooks.callbacks.KH_RevengeForget_damage_bullet(damage)
            assert(kyohud._revenge_targets[downer], 'down attacker not captured')

            local taser = enemy('taser')
            local tase_damage = {tase_data=function() return {attacker_unit=taser} end}
            Hooks.callbacks.KH_RevengeRememberTase(tase_damage)
            assert(kyohud._revenge_targets[taser], 'tase attacker not captured')

            local cloaker = enemy('spooc')
            local movement = {current_state_name=function() return 'incapacitated' end}
            Hooks.callbacks.KH_RevengeRememberSpooc(movement, cloaker)
            assert(kyohud._revenge_targets[cloaker], 'cloaker attacker not captured')

            kyohud:ResetHeistCombatState()
            assert(not kyohud._revenge_targets[downer]
                and not kyohud._revenge_targets[taser]
                and not kyohud._revenge_targets[cloaker], 'revenge reset failed')
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
            assert(count_event('rope') == 3 and last_event('rope').tier_index == 3)
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

    def test_exact_playerinventory_context_registration(self):
        self.lua.execute('Hooks.callbacks = {}')
        self.load('ky_playerinventory.lua', 'lib/units/beings/player/playerinventory')
        self.assertEqual(set(self.lua.globals().Hooks.callbacks.keys()), {'KH_OnWeaponSwap'})

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
