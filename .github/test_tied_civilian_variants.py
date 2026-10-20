"""Tied-civilian variant rotation and loud-context regression tests.
Run: uv run --with lupa python -B -m unittest discover -s .github -p test_tied_civilian_variants.py -v
"""
import json
from pathlib import Path
import unittest
from lupa.luajit21 import LuaRuntime
from test_stealth_first_batch import _common_stubs

ROOT = Path(__file__).resolve().parents[1]


class TiedCivilianVariantRotationTests(unittest.TestCase):
    """Rotation of three wording variants and contextual color."""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + '/'
        self.lua.execute(_common_stubs())
        self.lua.execute('''
            Color = setmetatable({white = {}, black = {}}, {
                __call = function(_, r, g, b) return {r = r or 1, g = g or 1, b = b or 1} end
            })
        ''')
        self._load_all()
        self.lua.execute('''
            install_wrapped_methods()
            kyohud.settings = {enable_killfeed = true, killfeed_size = 5}
            kyohud:ResetHeistCombatState()
            cards = {}
            original_show = kyohud._show_medal_card
            kyohud._show_medal_card = function(self, t, card, preview)
                if card then cards[#cards+1] = card end
                return original_show(self, t, card, preview)
            end
            function count_event(id)
                local n = 0
                for _, card in ipairs(cards) do if card.event == id then n = n + 1 end end
                return n
            end
            function tied_cards()
                local result = {}
                for _, card in ipairs(cards) do
                    if card.event == 'tied_civilian' then result[#result+1] = card end
                end
                return result
            end
        ''')

    def _load_all(self):
        for name, ctx in [
            ('core.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_combat_medals.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_hud_banners.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_buff_render.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_killfeed.lua', 'lib/managers/playermanager'),
            ('ky_killfeed.lua', 'lib/units/enemies/cop/copdamage'),
            ('ky_stealth.lua', 'lib/units/enemies/cop/copdamage'),
            ('ky_stealth.lua', 'lib/units/civilians/logics/civilianlogicsurrender'),
            ('ky_stealth.lua', 'lib/units/interactions/interactionext'),
            ('ky_stealth.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_playerinventory.lua', 'lib/units/beings/player/playerinventory'),
        ]:
            self.lua.globals().RequiredScript = ctx
            self.lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

    def test_three_distinct_labels_in_stealth(self):
        """Three consecutive stealth ties produce three distinct labels cycling."""
        self.lua.execute('''
            whisper_mode_val = true
            for i = 1, 3 do
                local victim = enemy(i % 2 == 0 and 'civilian_female' or 'civilian')
                local orig_key = victim.key
                victim.key = function() return 'unique_civ_key_' .. i end
                kyohud._stealth_tie_intents[victim] = {whisper = true, t = 100}
                local data = {is_tied = false, unit = victim, internal_data = {}}
                CivilianLogicSurrender.on_tied(data, local_player, false)
            end
            local tc = tied_cards()
            assert(#tc == 3, 'expected 3 tied_civilian medals, got ' .. #tc)
            local labels = {}
            for _, card in ipairs(tc) do labels[card.label] = true end
            local n = 0; for _ in pairs(labels) do n = n + 1 end
            assert(n == 3, 'expected 3 distinct labels, got ' .. n)
        ''')

    def test_variant_cycles_back_to_first(self):
        """Fourth stealth tie wraps back to first variant label."""
        self.lua.execute('''
            whisper_mode_val = true
            for i = 1, 4 do
                local victim = enemy(i % 2 == 0 and 'civilian_female' or 'civilian')
                victim.key = function() return 'cycle_civ_key_' .. i end
                kyohud._stealth_tie_intents[victim] = {whisper = true, t = 100}
                local data = {is_tied = false, unit = victim, internal_data = {}}
                CivilianLogicSurrender.on_tied(data, local_player, false)
            end
            local tc = tied_cards()
            assert(#tc == 4)
            assert(tc[1].label == tc[4].label, 'fourth must wrap to first variant')
        ''')

    def test_stealth_color_is_sage(self):
        """Stealth tied_civilian medal uses sage green."""
        self.lua.execute('''
            whisper_mode_val = true
            local victim = enemy('civilian')
            kyohud._stealth_tie_intents[victim] = {whisper = true, t = 100}
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            local tc = tied_cards()
            assert(#tc == 1)
            assert(tc[1].color.r < 0.7 and tc[1].color.g > 0.6 and tc[1].color.b < 0.6,
                'stealth color should be sage green')
        ''')

    def test_loud_color_is_amber(self):
        """Loud tied_civilian medal uses amber orange, not sage."""
        self.lua.execute('''
            whisper_mode_val = false
            local victim = enemy('civilian')
            kyohud._stealth_tie_intents[victim] = {whisper = false, t = 100}
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            local tc = tied_cards()
            assert(#tc == 1, 'loud tie must emit a medal')
            assert(tc[1].color.r > 0.8 and tc[1].color.g > 0.4 and tc[1].color.b < 0.3,
                'loud color should be amber orange')
        ''')

    def test_variant_index_reset_on_heist_reset(self):
        """ResetHeistCombatState resets the tied_civilian variant index."""
        self.lua.execute('''
            whisper_mode_val = true
            local victim_a = enemy('civilian')
            kyohud._stealth_tie_intents[victim_a] = {whisper = true, t = 100}
            local data_a = {is_tied = false, unit = victim_a, internal_data = {}}
            CivilianLogicSurrender.on_tied(data_a, local_player, false)
            local tc_first = tied_cards()
            assert(#tc_first == 1)
            local first_label = tc_first[1].label

            local victim_b = enemy('civilian')
            victim_b.key = function() return 'reset_civ_key_b' end
            kyohud._stealth_tie_intents[victim_b] = {whisper = true, t = 101}
            local data_b = {is_tied = false, unit = victim_b, internal_data = {}}
            CivilianLogicSurrender.on_tied(data_b, local_player, false)
            local tc_second = tied_cards()
            assert(#tc_second == 2)
            assert(tc_second[2].label ~= first_label,
                'second tie must advance to a different variant')

            kyohud:ResetHeistCombatState()
            cards = {}
            local victim_c = enemy('civilian')
            victim_c.key = function() return 'reset_civ_key_c' end
            kyohud._stealth_tie_intents[victim_c] = {whisper = true, t = 200}
            local data_c = {is_tied = false, unit = victim_c, internal_data = {}}
            CivilianLogicSurrender.on_tied(data_c, local_player, false)
            local tc = tied_cards()
            assert(#tc == 1)
            assert(tc[1].label == first_label,
                'after reset, variant should restart from first')
        ''')

    def test_no_kill_no_score_no_combo(self):
        """Tied civilian in loud still produces no kill, no score, no combo."""
        self.lua.execute('''
            whisper_mode_val = false
            local score_before = kyohud._heist_score_total
            local combo_before = kyohud._kill_combo.count
            local victim = enemy('civilian')
            kyohud._stealth_tie_intents[victim] = {whisper = false, t = 100}
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            assert(#kyohud._kills == 0, 'tied civilian must not produce a kill entry')
            assert(kyohud._heist_score_total == score_before, 'score must not change')
            assert(kyohud._kill_combo.count == combo_before, 'combo must not change')
        ''')


class TiedCivilianHostLoudTests(unittest.TestCase):
    """Host confirmation path: loud/stealth e2e, negative and color preservation tests."""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + '/'
        self.lua.execute(_common_stubs())
        self.lua.execute('''
            Color = setmetatable({white = {}, black = {}}, {
                __call = function(_, r, g, b) return {r = r or 1, g = g or 1, b = b or 1} end
            })
        ''')
        self._load_all()
        self.lua.execute('''
            install_wrapped_methods()
            kyohud.settings = {enable_killfeed = true, killfeed_size = 5}
            kyohud:ResetHeistCombatState()
            cards = {}
            original_show = kyohud._show_medal_card
            kyohud._show_medal_card = function(self, t, card, preview)
                if card then cards[#cards+1] = card end
                return original_show(self, t, card, preview)
            end
            function count_event(id)
                local n = 0
                for _, card in ipairs(cards) do if card.event == id then n = n + 1 end end
                return n
            end
        ''')

    def _load_all(self):
        for name, ctx in [
            ('core.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_combat_medals.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_hud_banners.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_buff_render.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_killfeed.lua', 'lib/managers/playermanager'),
            ('ky_killfeed.lua', 'lib/units/enemies/cop/copdamage'),
            ('ky_stealth.lua', 'lib/units/enemies/cop/copdamage'),
            ('ky_stealth.lua', 'lib/units/civilians/logics/civilianlogicsurrender'),
            ('ky_stealth.lua', 'lib/units/interactions/interactionext'),
            ('ky_stealth.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_playerinventory.lua', 'lib/units/beings/player/playerinventory'),
        ]:
            self.lua.globals().RequiredScript = ctx
            self.lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

    def test_host_loud_successful_tie_awards_medal(self):
        """Host: successful tie during loud -> tied_civilian medal with amber color."""
        self.lua.execute('''
            whisper_mode_val = false
            local victim = enemy('civilian')
            kyohud._stealth_tie_intents[victim] = {whisper = false, t = 100}
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            assert(count_event('tied_civilian') == 1, 'loud host tie must emit medal')
        ''')

    def test_host_loud_no_intent_no_medal(self):
        """Host: loud tie without intent -> no medal."""
        self.lua.execute('''
            whisper_mode_val = false
            local victim = enemy('civilian')
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            assert(count_event('tied_civilian') == 0, 'no intent must not emit medal in loud')
        ''')

    def test_host_loud_not_tied_no_medal(self):
        """Host: loud not_tied=true -> no medal."""
        self.lua.execute('''
            whisper_mode_val = false
            local victim = enemy('civilian')
            kyohud._stealth_tie_intents[victim] = {whisper = false, t = 100}
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, true)
            assert(count_event('tied_civilian') == 0, 'not_tied must not emit medal in loud')
        ''')

    def test_host_loud_expired_intent_no_medal(self):
        """Host: loud intent expired (>4s) -> no medal."""
        self.lua.execute('''
            whisper_mode_val = false
            game_t = 100
            local victim = enemy('civilian')
            kyohud._stealth_tie_intents[victim] = {whisper = false, t = 90}
            game_t = 105
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            assert(count_event('tied_civilian') == 0, 'expired intent must not emit in loud')
        ''')

    def test_host_loud_duplicate_no_double_medal(self):
        """Host: same unit tied twice in loud -> only one medal."""
        self.lua.execute('''
            whisper_mode_val = false
            local victim = enemy('civilian')
            kyohud._stealth_tie_intents[victim] = {whisper = false, t = 100}
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            kyohud._stealth_tie_intents[victim] = {whisper = false, t = 101}
            local data2 = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data2, local_player, false)
            assert(count_event('tied_civilian') == 1, 'same unit tied twice in loud emitted more than one')
        ''')

    def test_host_loud_e2e_interaction_to_confirmation(self):
        """Host: interaction in loud -> on_tied -> amber medal."""
        self.lua.execute('''
            whisper_mode_val = false
            local victim = enemy('civilian')
            victim.key = function() return 'host_loud_e2e_key' end
            local interaction = setmetatable({
                _unit = victim,
                tweak_data = "intimidate",
                _tweak_data = {special_equipment = 'cable_tie'},
            }, {__index = IntimitateInteractionExt})
            IntimitateInteractionExt.interact(interaction, local_player)
            assert(kyohud._stealth_tie_intents[victim] ~= nil, 'interaction must arm intent')
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            assert(count_event('tied_civilian') == 1, 'host loud e2e must emit medal')
            assert(#cards == 1)
            assert(cards[1].color.r > 0.8 and cards[1].color.g > 0.4 and cards[1].color.b < 0.3,
                'host loud e2e medal must be amber')
        ''')

    def test_host_stealth_e2e_interaction_to_confirmation(self):
        """Host: interaction in stealth -> on_tied -> sage medal."""
        self.lua.execute('''
            whisper_mode_val = true
            local victim = enemy('civilian')
            victim.key = function() return 'host_stealth_e2e_key' end
            local interaction = setmetatable({
                _unit = victim,
                tweak_data = "intimidate",
                _tweak_data = {special_equipment = 'cable_tie'},
            }, {__index = IntimitateInteractionExt})
            IntimitateInteractionExt.interact(interaction, local_player)
            assert(kyohud._stealth_tie_intents[victim] ~= nil, 'interaction must arm intent')
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            assert(count_event('tied_civilian') == 1, 'host stealth e2e must emit medal')
            assert(#cards == 1)
            assert(cards[1].color.r < 0.7 and cards[1].color.g > 0.6 and cards[1].color.b < 0.6,
                'host stealth e2e medal must be sage')
        ''')

    def test_host_color_preserved_when_whisper_flips(self):
        """Host: intent captured at whisper=true, mode flips to false before confirmation -> sage card."""
        self.lua.execute('''
            whisper_mode_val = true
            local victim = enemy('civilian')
            victim.key = function() return 'color_preserve_key' end
            local interaction = setmetatable({
                _unit = victim,
                tweak_data = "intimidate",
                _tweak_data = {special_equipment = 'cable_tie'},
            }, {__index = IntimitateInteractionExt})
            IntimitateInteractionExt.interact(interaction, local_player)
            local intent = kyohud._stealth_tie_intents[victim]
            assert(intent ~= nil and intent.whisper == true, 'intent must be stealth')
            whisper_mode_val = false
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            assert(count_event('tied_civilian') == 1, 'must emit medal from intent')
            assert(#cards == 1)
            assert(cards[1].color.r < 0.7 and cards[1].color.g > 0.6 and cards[1].color.b < 0.6,
                'color must come from intent whisper=true, not current mode')
        ''')


class TiedCivilianClientLoudTests(unittest.TestCase):
    """Client confirmation path: loud/stealth e2e and loud negative tests."""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + '/'
        self.lua.execute(_common_stubs())
        self.lua.execute('is_client_val = true')
        self.lua.execute('''
            Color = setmetatable({white = {}, black = {}}, {
                __call = function(_, r, g, b) return {r = r or 1, g = g or 1, b = b or 1} end
            })
        ''')
        self._load_all()
        self.lua.execute('''
            install_wrapped_methods()
            kyohud.settings = {enable_killfeed = true, killfeed_size = 5}
            kyohud:ResetHeistCombatState()
            cards = {}
            original_show = kyohud._show_medal_card
            kyohud._show_medal_card = function(self, t, card, preview)
                if card then cards[#cards+1] = card end
                return original_show(self, t, card, preview)
            end
            function count_event(id)
                local n = 0
                for _, card in ipairs(cards) do if card.event == id then n = n + 1 end end
                return n
            end
        ''')

    def _load_all(self):
        for name, ctx in [
            ('core.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_combat_medals.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_hud_banners.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_buff_render.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_killfeed.lua', 'lib/managers/playermanager'),
            ('ky_killfeed.lua', 'lib/units/enemies/cop/copdamage'),
            ('ky_stealth.lua', 'lib/units/enemies/cop/copdamage'),
            ('ky_stealth.lua', 'lib/units/civilians/logics/civilianlogicsurrender'),
            ('ky_stealth.lua', 'lib/units/enemies/cop/huskcopbrain'),
            ('ky_stealth.lua', 'lib/units/interactions/interactionext'),
            ('ky_stealth.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_playerinventory.lua', 'lib/units/beings/player/playerinventory'),
        ]:
            self.lua.globals().RequiredScript = ctx
            self.lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

    def test_client_loud_confirmed_tie_awards_medal(self):
        """Client: loud intent + sync_net_event confirmation -> medal with amber color."""
        self.lua.execute('''
            whisper_mode_val = false
            local victim = enemy('civilian')
            victim.key = function() return 'client_loud_civ_key' end
            local brain = setmetatable(
                {_unit = victim, _surrendered = false},
                {__index = HuskCopBrain}
            )
            kyohud._stealth_tie_intents[victim] = {whisper = false, t = 100}
            local hook_fn
            for _, entries in pairs(_post_hooks[HuskCopBrain]["sync_net_event"]) do
                if entries.id == "KH_StealthHuskCopBrainNetEvent" then
                    hook_fn = entries.fn
                end
            end
            assert(hook_fn, 'hook function not found')
            local pre_fn
            for _, entries in pairs(_pre_hooks[HuskCopBrain]["sync_net_event"]) do
                if entries.id == "KH_StealthHuskCopBrainPreCapture" then
                    pre_fn = entries.fn
                end
            end
            pre_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            brain._surrendered = true
            hook_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            assert(count_event('tied_civilian') == 1, 'client loud confirmed tie must emit medal')
        ''')

    def test_client_loud_e2e_interaction_to_confirmation(self):
        """Client: loud interaction -> sync_net_event -> amber medal."""
        self.lua.execute('''
            whisper_mode_val = false
            local victim = enemy('civilian')
            victim.key = function() return 'client_loud_e2e_key' end
            local interaction = setmetatable({
                _unit = victim,
                tweak_data = "intimidate",
                _tweak_data = {special_equipment = 'cable_tie'},
            }, {__index = IntimitateInteractionExt})
            IntimitateInteractionExt.interact(interaction, local_player)
            assert(kyohud._stealth_tie_intents[victim] ~= nil, 'interaction must arm intent')
            local brain = setmetatable(
                {_unit = victim, _surrendered = false},
                {__index = HuskCopBrain}
            )
            local hook_fn, pre_fn
            for _, entries in pairs(_post_hooks[HuskCopBrain]["sync_net_event"]) do
                if entries.id == "KH_StealthHuskCopBrainNetEvent" then hook_fn = entries.fn end
            end
            for _, entries in pairs(_pre_hooks[HuskCopBrain]["sync_net_event"]) do
                if entries.id == "KH_StealthHuskCopBrainPreCapture" then pre_fn = entries.fn end
            end
            assert(hook_fn and pre_fn, 'hooks not found')
            pre_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            brain._surrendered = true
            hook_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            assert(count_event('tied_civilian') == 1, 'client loud e2e must emit medal')
            assert(#cards == 1)
            assert(cards[1].color.r > 0.8 and cards[1].color.g > 0.4 and cards[1].color.b < 0.3,
                'client loud e2e medal must be amber')
        ''')

    def test_client_stealth_e2e_interaction_to_confirmation(self):
        """Client: stealth interaction -> sync_net_event -> sage medal."""
        self.lua.execute('''
            whisper_mode_val = true
            local victim = enemy('civilian')
            victim.key = function() return 'client_stealth_e2e_key' end
            local interaction = setmetatable({
                _unit = victim,
                tweak_data = "intimidate",
                _tweak_data = {special_equipment = 'cable_tie'},
            }, {__index = IntimitateInteractionExt})
            IntimitateInteractionExt.interact(interaction, local_player)
            assert(kyohud._stealth_tie_intents[victim] ~= nil, 'interaction must arm intent')
            assert(kyohud._stealth_tie_intents[victim].whisper == true, 'stealth intent')
            local brain = setmetatable(
                {_unit = victim, _surrendered = false},
                {__index = HuskCopBrain}
            )
            local hook_fn, pre_fn
            for _, entries in pairs(_post_hooks[HuskCopBrain]["sync_net_event"]) do
                if entries.id == "KH_StealthHuskCopBrainNetEvent" then hook_fn = entries.fn end
            end
            for _, entries in pairs(_pre_hooks[HuskCopBrain]["sync_net_event"]) do
                if entries.id == "KH_StealthHuskCopBrainPreCapture" then pre_fn = entries.fn end
            end
            assert(hook_fn and pre_fn, 'hooks not found')
            pre_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            brain._surrendered = true
            hook_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            assert(count_event('tied_civilian') == 1, 'client stealth e2e must emit medal')
            assert(#cards == 1)
            assert(cards[1].color.r < 0.7 and cards[1].color.g > 0.6 and cards[1].color.b < 0.6,
                'client stealth e2e medal must be sage')
        ''')

    def test_client_loud_no_confirmation_no_medal(self):
        """Client: loud interaction but no sync_net_event -> no medal."""
        self.lua.execute('''
            whisper_mode_val = false
            local victim = enemy('civilian')
            victim.key = function() return 'client_no_confirm_key' end
            local interaction = setmetatable({
                _unit = victim,
                tweak_data = "intimidate",
                _tweak_data = {special_equipment = 'cable_tie'},
            }, {__index = IntimitateInteractionExt})
            IntimitateInteractionExt.interact(interaction, local_player)
            assert(kyohud._stealth_tie_intents[victim] ~= nil, 'intent must be armed')
            assert(count_event('tied_civilian') == 0, 'no confirmation must not emit medal')
        ''')

    def test_client_loud_no_intent_no_medal(self):
        """Client: sync_net_event without interaction (no intent) -> no medal."""
        self.lua.execute('''
            whisper_mode_val = false
            local victim = enemy('civilian')
            victim.key = function() return 'client_no_intent_key' end
            local brain = setmetatable(
                {_unit = victim, _surrendered = false},
                {__index = HuskCopBrain}
            )
            local hook_fn, pre_fn
            for _, entries in pairs(_post_hooks[HuskCopBrain]["sync_net_event"]) do
                if entries.id == "KH_StealthHuskCopBrainNetEvent" then hook_fn = entries.fn end
            end
            for _, entries in pairs(_pre_hooks[HuskCopBrain]["sync_net_event"]) do
                if entries.id == "KH_StealthHuskCopBrainPreCapture" then pre_fn = entries.fn end
            end
            assert(hook_fn and pre_fn, 'hooks not found')
            pre_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            brain._surrendered = true
            hook_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            assert(count_event('tied_civilian') == 0, 'no intent must not emit medal')
        ''')

    def test_client_loud_nonlocal_interaction_no_medal(self):
        """Client: nonlocal interaction -> no intent -> sync_net_event -> no medal."""
        self.lua.execute('''
            whisper_mode_val = false
            local victim = enemy('civilian')
            victim.key = function() return 'client_nonlocal_key' end
            local other = enemy('security')
            local interaction = setmetatable({
                _unit = victim,
                tweak_data = "intimidate",
                _tweak_data = {special_equipment = 'cable_tie'},
            }, {__index = IntimitateInteractionExt})
            IntimitateInteractionExt.interact(interaction, other)
            assert(kyohud._stealth_tie_intents[victim] == nil,
                'nonlocal interaction must not arm intent')
            local brain = setmetatable(
                {_unit = victim, _surrendered = false},
                {__index = HuskCopBrain}
            )
            local hook_fn, pre_fn
            for _, entries in pairs(_post_hooks[HuskCopBrain]["sync_net_event"]) do
                if entries.id == "KH_StealthHuskCopBrainNetEvent" then hook_fn = entries.fn end
            end
            for _, entries in pairs(_pre_hooks[HuskCopBrain]["sync_net_event"]) do
                if entries.id == "KH_StealthHuskCopBrainPreCapture" then pre_fn = entries.fn end
            end
            pre_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            brain._surrendered = true
            hook_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            assert(count_event('tied_civilian') == 0,
                'nonlocal interaction must not lead to medal via sync')
        ''')

    def test_client_loud_expired_intent_no_medal(self):
        """Client: loud interaction -> intent expires -> sync_net_event -> no medal."""
        self.lua.execute('''
            whisper_mode_val = false
            game_t = 100
            local victim = enemy('civilian')
            victim.key = function() return 'client_expired_key' end
            local interaction = setmetatable({
                _unit = victim,
                tweak_data = "intimidate",
                _tweak_data = {special_equipment = 'cable_tie'},
            }, {__index = IntimitateInteractionExt})
            IntimitateInteractionExt.interact(interaction, local_player)
            assert(kyohud._stealth_tie_intents[victim] ~= nil, 'intent must be armed')
            game_t = 105
            local brain = setmetatable(
                {_unit = victim, _surrendered = false},
                {__index = HuskCopBrain}
            )
            local hook_fn, pre_fn
            for _, entries in pairs(_post_hooks[HuskCopBrain]["sync_net_event"]) do
                if entries.id == "KH_StealthHuskCopBrainNetEvent" then hook_fn = entries.fn end
            end
            for _, entries in pairs(_pre_hooks[HuskCopBrain]["sync_net_event"]) do
                if entries.id == "KH_StealthHuskCopBrainPreCapture" then pre_fn = entries.fn end
            end
            pre_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            brain._surrendered = true
            hook_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            assert(count_event('tied_civilian') == 0, 'expired intent must not emit on client')
        ''')

    def test_client_loud_duplicate_no_double_medal(self):
        """Client: interaction -> sync_net_event twice -> only one medal."""
        self.lua.execute('''
            whisper_mode_val = false
            local victim = enemy('civilian')
            victim.key = function() return 'client_dup_key' end
            local interaction = setmetatable({
                _unit = victim,
                tweak_data = "intimidate",
                _tweak_data = {special_equipment = 'cable_tie'},
            }, {__index = IntimitateInteractionExt})
            IntimitateInteractionExt.interact(interaction, local_player)
            local brain = setmetatable(
                {_unit = victim, _surrendered = false},
                {__index = HuskCopBrain}
            )
            local hook_fn, pre_fn
            for _, entries in pairs(_post_hooks[HuskCopBrain]["sync_net_event"]) do
                if entries.id == "KH_StealthHuskCopBrainNetEvent" then hook_fn = entries.fn end
            end
            for _, entries in pairs(_pre_hooks[HuskCopBrain]["sync_net_event"]) do
                if entries.id == "KH_StealthHuskCopBrainPreCapture" then pre_fn = entries.fn end
            end
            pre_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            brain._surrendered = true
            hook_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            assert(count_event('tied_civilian') == 1, 'first confirmation must emit')
            pre_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            hook_fn(brain, HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            assert(count_event('tied_civilian') == 1, 'duplicate must not emit second medal')
        ''')


class TiedCivilianInteractionCaptureTests(unittest.TestCase):
    """Interaction intent capture in both whisper and loud modes."""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + '/'
        self.lua.execute(_common_stubs())
        self.lua.execute('''
            Color = setmetatable({white = {}, black = {}}, {
                __call = function(_, r, g, b) return {r = r or 1, g = g or 1, b = b or 1} end
            })
        ''')
        self._load_all()
        self.lua.execute('''
            install_wrapped_methods()
            kyohud.settings = {enable_killfeed = true, killfeed_size = 5}
            kyohud:ResetHeistCombatState()
        ''')

    def _load_all(self):
        for name, ctx in [
            ('core.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_combat_medals.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_hud_banners.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_buff_render.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_killfeed.lua', 'lib/managers/playermanager'),
            ('ky_killfeed.lua', 'lib/units/enemies/cop/copdamage'),
            ('ky_stealth.lua', 'lib/units/enemies/cop/copdamage'),
            ('ky_stealth.lua', 'lib/units/civilians/logics/civilianlogicsurrender'),
            ('ky_stealth.lua', 'lib/units/interactions/interactionext'),
            ('ky_stealth.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_playerinventory.lua', 'lib/units/beings/player/playerinventory'),
        ]:
            self.lua.globals().RequiredScript = ctx
            self.lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

    def test_interaction_capture_in_loud_sets_whisper_false(self):
        """Interaction during loud captures intent with whisper=false."""
        self.lua.execute('''
            whisper_mode_val = false
            local victim = enemy('civilian')
            local interaction = setmetatable({
                _unit = victim,
                tweak_data = "intimidate",
                _tweak_data = {special_equipment = 'cable_tie'},
            }, {__index = IntimitateInteractionExt})
            IntimitateInteractionExt.interact(interaction, local_player)
            local intent = kyohud._stealth_tie_intents[victim]
            assert(intent ~= nil, 'loud interaction must capture intent')
            assert(intent.whisper == false, 'loud intent must have whisper=false')
        ''')

    def test_interaction_capture_in_stealth_sets_whisper_true(self):
        """Interaction during whisper captures intent with whisper=true."""
        self.lua.execute('''
            whisper_mode_val = true
            local victim = enemy('civilian')
            local interaction = setmetatable({
                _unit = victim,
                tweak_data = "intimidate",
                _tweak_data = {special_equipment = 'cable_tie'},
            }, {__index = IntimitateInteractionExt})
            IntimitateInteractionExt.interact(interaction, local_player)
            local intent = kyohud._stealth_tie_intents[victim]
            assert(intent ~= nil, 'stealth interaction must capture intent')
            assert(intent.whisper == true, 'stealth intent must have whisper=true')
        ''')

    def test_interaction_no_cable_no_intent(self):
        """No cable tie equipment -> no intent captured."""
        self.lua.execute('''
            whisper_mode_val = false
            managers.player.has_special_equipment = function() return false end
            local victim = enemy('civilian')
            local interaction = setmetatable({
                _unit = victim,
                tweak_data = "intimidate",
                _tweak_data = {special_equipment = 'cable_tie'},
            }, {__index = IntimitateInteractionExt})
            IntimitateInteractionExt.interact(interaction, local_player)
            assert(kyohud._stealth_tie_intents[victim] == nil,
                'no cable must not arm tie intent in loud')
        ''')

    def test_non_civilian_no_intent(self):
        """Non-civilian unit interaction -> no intent."""
        self.lua.execute('''
            whisper_mode_val = false
            local victim = enemy('security')
            local interaction = setmetatable({
                _unit = victim,
                tweak_data = "intimidate",
                _tweak_data = {special_equipment = 'cable_tie'},
            }, {__index = IntimitateInteractionExt})
            IntimitateInteractionExt.interact(interaction, local_player)
            assert(kyohud._stealth_tie_intents[victim] == nil,
                'non-civilian must not capture tie intent')
        ''')


class TiedCivilianPreviewTests(unittest.TestCase):
    """Preview exposes all three variants in both stealth and loud."""

    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + '/'
        self.lua.execute(_common_stubs())
        self.lua.execute('''
            Color = setmetatable({white = {}, black = {}}, {
                __call = function(_, r, g, b) return {r = r or 1, g = g or 1, b = b or 1} end
            })
        ''')
        self._load_all()
        self.lua.execute('''
            install_wrapped_methods()
            kyohud.settings = {enable_killfeed = true, killfeed_size = 5}
            kyohud:ResetHeistCombatState()
        ''')

    def _load_all(self):
        for name, ctx in [
            ('core.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_combat_medals.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_hud_banners.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_buff_render.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_killfeed.lua', 'lib/managers/playermanager'),
            ('ky_killfeed.lua', 'lib/units/enemies/cop/copdamage'),
            ('ky_killfeed_render.lua', 'lib/managers/hudmanagerpd2'),
            ('ky_stealth.lua', 'lib/units/enemies/cop/copdamage'),
            ('ky_playerinventory.lua', 'lib/units/beings/player/playerinventory'),
        ]:
            self.lua.globals().RequiredScript = ctx
            self.lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

    def test_preview_all_six_variants_reachable(self):
        """Preview cycles reach 3 variants × 2 contexts = 6 distinct tied_civilian cards."""
        self.lua.execute('''
            local seen = {}
            for i = 1, 50 do
                kyohud:DebugSimulate(0)
                local card = kyohud._medal_card
                if card and card.event == 'tied_civilian' then
                    local key = card.label .. ':' .. tostring(card.color.r)
                        .. ':' .. tostring(card.color.g) .. ':' .. tostring(card.color.b)
                    seen[key] = true
                end
            end
            local n = 0; for _ in pairs(seen) do n = n + 1 end
            assert(n >= 6, 'preview must show at least 6 distinct tied_civilian cards, got ' .. n)
        ''')


class TiedCivilianLocalizationTests(unittest.TestCase):
    """Localization keys for the three variants in both languages."""

    def test_localization_keys_present(self):
        fallback = (ROOT / 'lua' / 'ky_localization.lua').read_text(encoding='utf-8-sig')
        keys = (
            'ky_hud_event_medal_tied_civilian',
            'ky_hud_event_medal_tied_civilian_2',
            'ky_hud_event_medal_tied_civilian_3',
        )
        for language in ('english', 'french'):
            data = json.loads((ROOT / 'loc' / (language + '.json')).read_text(encoding='utf-8-sig'))
            for key in keys:
                self.assertTrue(data.get(key), (language, key, 'missing'))
                self.assertIn(key, fallback, (language, key, 'missing from fallback'))

    def test_distinct_labels_per_variant(self):
        keys = (
            'ky_hud_event_medal_tied_civilian',
            'ky_hud_event_medal_tied_civilian_2',
            'ky_hud_event_medal_tied_civilian_3',
        )
        for language in ('english', 'french'):
            data = json.loads((ROOT / 'loc' / (language + '.json')).read_text(encoding='utf-8-sig'))
            labels = set()
            for key in keys:
                labels.add(data[key])
            self.assertEqual(len(labels), 3, language + ' must have 3 distinct labels')


if __name__ == "__main__":
    unittest.main()
