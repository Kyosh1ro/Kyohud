"""Runtime-order regressions for stealth; execute production LuaJIT chunks."""
import json
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime
from test_stealth_first_batch import _common_stubs

ROOT = Path(__file__).resolve().parents[1]


class StealthRuntimeIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + "/"
        self.lua.execute(_common_stubs())
        # Model the relevant native order, including failed/nonlethal actions.
        self.lua.execute('''
            function native_damage(self, attack)
                if attack.nonlethal then return end
                if attack.turn_loud then whisper_mode_val = false end
                self:die(attack)
                self:chk_killshot(attack.attacker_unit, attack.variant, false, nil)
            end
            CopDamage.damage_bullet = native_damage
            CopDamage.damage_melee = native_damage
            CopDamage.damage_fire = native_damage
            CopDamage.damage_explosion = native_damage
            CopDamage.damage_dot = native_damage
            CopDamage.damage_simple = native_damage
            CopDamage.damage_tase = native_damage
            CopDamage.damage_mission = native_damage
            CivilianLogicSurrender.on_tied = function(data, aggressor, not_tied)
                if data.is_tied or not_tied or data.fail then return end
                data.is_tied = true
            end
            HuskCopBrain.sync_net_event = function(self, event)
                if event == self._NET_EVENTS.surrender_civilian_tied then
                    self._surrendered = true
                end
            end
            IntimitateInteractionExt.interact = function(self, player)
                if not self:can_interact(player) then return end
                if self.tweak_data ~= 'intimidate' and self.tweak_data ~= 'intimidate_and_search'
                        and self.tweak_data ~= 'intimidate_with_contour'
                        and self.tweak_data ~= 'intimidate_and_search_with_contour' then return end
                local has_equipment = managers.player:has_special_equipment('cable_tie')
                if self._tweak_data.dont_need_equipment and not has_equipment then
                    if not is_client_val then
                        CivilianLogicSurrender.on_tied(self.data, player, true)
                    end
                    return
                end
                if not has_equipment then return end
                if is_client_val then
                    tie_requests = tie_requests + 1
                else
                    CivilianLogicSurrender.on_tied(self.data, player, false)
                end
            end
            -- Diesel mrotation.y requires an output Vector3, unlike Rotation:y().
            mrotation.y = function(rotation, output)
                assert(output ~= nil, 'native mrotation.y requires output vector')
            end
            local original_enemy = enemy
            function enemy(...)
                local unit = original_enemy(...)
                unit.rotation = function()
                    return {y = function() return _enemy_fwd or {x=0,y=1,z=0} end}
                end
                return unit
            end
            tie_requests = 0
            function make_tie(id, failed, already_tied)
                local victim = enemy(id or 'civilian')
                local data = {unit=victim, is_tied=already_tied == true, fail=failed}
                local interaction = setmetatable({
                    _unit=victim, data=data, tweak_data='intimidate',
                    _tweak_data={special_equipment='cable_tie'},
                }, {__index=IntimitateInteractionExt})
                local brain = setmetatable({_unit=victim, _surrendered=already_tied == true},
                    {__index=HuskCopBrain})
                return victim, interaction, brain
            end
        ''')
        wanted = {
            "lua/core.lua", "lua/ky_combat_medals.lua", "lua/ky_hud_banners.lua",
            "lua/ky_killfeed.lua", "lua/ky_killfeed_render.lua",
            "lua/ky_stealth.lua", "lua/ky_playerinventory.lua",
        }
        hooks = json.loads((ROOT / "mod.txt").read_text(encoding="utf-8"))["hooks"]
        contexts = [
            "lib/managers/hudmanagerpd2", "lib/managers/playermanager",
            "lib/units/enemies/cop/copdamage", "lib/units/enemies/cop/huskcopdamage",
            "lib/units/civilians/logics/civilianlogicsurrender",
            "lib/units/interactions/interactionext", "lib/units/enemies/cop/huskcopbrain",
            "lib/units/beings/player/playerinventory",
        ]
        for context in contexts:
            for hook in hooks:
                if hook["hook_id"] == context and hook["script_path"] in wanted:
                    self.lua.globals().RequiredScript = context
                    self.lua.execute((ROOT / hook["script_path"]).read_text(encoding="utf-8-sig"))
        self.lua.execute('''
            kyohud.settings = {enable_killfeed=true, killfeed_size=5}
            kyohud:ResetHeistCombatState()
            awards = {}
            local original = kyohud._show_medal_card
            kyohud._show_medal_card = function(self, t, card, preview)
                if card then awards[card.event] = (awards[card.event] or 0) + 1 end
                return original(self, t, card, preview)
            end
            function count_event(id) return awards[id] or 0 end
        ''')

    def test_host_failed_tie_never_awards(self):
        self.lua.execute('''
            whisper_mode_val = true
            local unit, interaction = make_tie('civilian', true)
            interaction:interact(local_player)
            assert(not interaction.data.is_tied, 'native action must actually fail')
            assert(count_event('tied_civilian') == 0, 'failed tie awarded medal')
            assert(kyohud._stealth_tie_intents[unit] == nil)
        ''')

    def test_host_successful_tie_no_kill_score_or_combo(self):
        self.lua.execute('''
            whisper_mode_val = true
            local unit, interaction = make_tie()
            local score, combo = kyohud._heist_score_total, kyohud._kill_combo.count
            interaction:interact(local_player)
            interaction:interact(local_player)
            assert(interaction.data.is_tied)
            assert(count_event('tied_civilian') == 1)
            assert(#kyohud._kills == 0)
            assert(kyohud._heist_score_total == score and kyohud._kill_combo.count == combo)
        ''')

    def test_client_tie_waits_for_native_confirmation(self):
        self.lua.execute('''
            is_client_val = true; whisper_mode_val = true
            local unit, interaction, brain = make_tie()
            interaction:interact(local_player)
            assert(tie_requests == 1)
            assert(count_event('tied_civilian') == 0, 'request is not confirmation')
            brain:sync_net_event(HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            assert(brain._surrendered == true)
            assert(count_event('tied_civilian') == 1, 'confirmed local tie missing')
            brain:sync_net_event(HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            assert(count_event('tied_civilian') == 1)
            assert(#kyohud._kills == 0)
        ''')

    def test_client_no_cable_optional_equipment_no_intent(self):
        self.lua.execute('''
            is_client_val = true; whisper_mode_val = true
            managers.player.has_special_equipment = function() return false end
            local unit, interaction, brain = make_tie()
            interaction.tweak_data = 'intimidate_and_search'
            interaction._tweak_data.dont_need_equipment = true
            interaction:interact(local_player)
            assert(kyohud._stealth_tie_intents[unit] == nil, 'no cable must not arm tie intent')
            brain:sync_net_event(HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            assert(count_event('tied_civilian') == 0)
        ''')

    def test_native_equipment_record_is_accepted(self):
        self.lua.execute('''
            whisper_mode_val = true
            -- Native PlayerManager:has_special_equipment returns a record, not true.
            managers.player.has_special_equipment = function() return {amount=2} end
            local unit, interaction = make_tie()
            interaction:interact(local_player)
            assert(interaction.data.is_tied)
            assert(count_event('tied_civilian') == 1, 'native equipment record was rejected')
        ''')

    def test_client_guard_remote_player_and_dropin_do_not_award(self):
        self.lua.execute('''
            is_client_val = true; whisper_mode_val = true
            local guard, gi, gb = make_tie('security')
            gi:interact(local_player)
            gb:sync_net_event(HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            local unit, interaction, brain = make_tie()
            interaction:interact({})
            brain:sync_net_event(HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            local dropin, di, db = make_tie()
            db:sync_net_event(HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            assert(count_event('tied_civilian') == 0)
        ''')

    def test_invalid_followup_interaction_clears_old_client_intent(self):
        self.lua.execute('''
            is_client_val = true; whisper_mode_val = true
            local unit, interaction, brain = make_tie()
            interaction:interact(local_player)
            assert(kyohud._stealth_tie_intents[unit])
            interaction.tweak_data = 'hostage_move'
            interaction:interact(local_player)
            assert(kyohud._stealth_tie_intents[unit] == nil, 'invalid attempt left stale intent')
        ''')

    def test_expired_or_reset_intent_cannot_award(self):
        self.lua.execute('''
            is_client_val = true; whisper_mode_val = true
            local unit, interaction, brain = make_tie()
            interaction:interact(local_player)
            game_t = game_t + 5
            brain:sync_net_event(HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            assert(count_event('tied_civilian') == 0)
            local unit2, interaction2, brain2 = make_tie()
            interaction2:interact(local_player)
            kyohud:ResetHeistCombatState()
            brain2:sync_net_event(HuskCopBrain._NET_EVENTS.surrender_civilian_tied)
            assert(count_event('tied_civilian') == 0)
        ''')

    def test_backstab_uses_native_rotation_accessor_host_and_client(self):
        for client in (False, True):
            with self.subTest(client=client):
                self.lua.globals().is_client_val = client
                self.lua.execute('''
                    kyohud:ResetHeistCombatState(); awards = {}; whisper_mode_val = true
                    local unit = enemy('security', nil,nil,nil, {x=0,y=100}, true)
                    local damage = make_cop_damage(unit, is_client_val)
                    damage:damage_melee({attacker_unit=local_player, variant='melee'})
                    assert(count_event('backstab') == 1, 'valid native backstab missing')
                    assert(count_event('silent_guard') == 1)
                    assert(count_event('stealth_melee') == 0)
                ''')

    def test_front_side_degenerate_geometry_never_backstab(self):
        for position in ((0, 200), (100, 100), (0, 100)):
            with self.subTest(position=position):
                self.lua.globals().px, self.lua.globals().py = position
                self.lua.execute('''
                    kyohud:ResetHeistCombatState(); awards = {}; whisper_mode_val = true
                    set_player_position(px, py, 0)
                    local unit = enemy('security',nil,nil,nil,{x=0,y=100},false)
                    make_cop_damage(unit,false):damage_bullet({attacker_unit=local_player,variant='bullet'})
                    assert(count_event('backstab') == 0)
                    assert(kyohud._kills[1].stealth == true)
                ''')

    def test_missing_coordinates_fail_closed(self):
        self.lua.execute('''
            whisper_mode_val = true
            local_player.position = function() return {y=0} end
            assert(not kyohud:IsBackstabKill(enemy('cop')), 'missing X became a backstab')
        ''')

    def test_loud_during_original_damage_preserves_capture_and_existing_card(self):
        for client in (False, True):
            with self.subTest(client=client):
                self.lua.globals().is_client_val = client
                self.lua.execute('''
                    kyohud:ResetHeistCombatState(); awards = {}; whisper_mode_val = true
                    local unit = enemy('security', nil,nil,nil,nil,true)
                    make_cop_damage(unit,is_client_val):damage_melee({
                        attacker_unit=local_player,variant='melee',turn_loud=true})
                    assert(not whisper_mode_val)
                    assert(count_event('silent_guard') == 1)
                    local first = kyohud._kills[1]
                    assert(first.stealth == true)
                    local next = enemy('cop')
                    make_cop_damage(next,is_client_val):damage_bullet({attacker_unit=local_player,variant='bullet'})
                    assert(first.stealth == true and not kyohud._kills[2].stealth)
                ''')

    def test_nonlethal_capture_is_cleaned_before_different_lethal_attack(self):
        for client in (False, True):
            with self.subTest(client=client):
                self.lua.globals().is_client_val = client
                self.lua.execute('''
                    kyohud:ResetHeistCombatState(); awards = {}; whisper_mode_val = true
                    local unit = enemy('security',nil,nil,nil,nil,true)
                    local damage = make_cop_damage(unit,is_client_val)
                    damage:damage_melee({attacker_unit=local_player,variant='melee',nonlethal=true})
                    assert(#kyohud._kills == 0 and kyohud._stealth_pre_die_states[unit] == nil)
                    whisper_mode_val = false
                    damage:damage_bullet({attacker_unit=local_player,variant='bullet'})
                    assert(not kyohud._kills[1].stealth)
                    assert(count_event('silent_guard') == 0)
                ''')

    def test_all_native_damage_variants_keep_stealth_style_on_client(self):
        for variant in ("fire", "explosion", "dot", "simple", "tase", "mission"):
            with self.subTest(variant=variant):
                self.lua.globals().variant = variant
                self.lua.execute('''
                    kyohud:ResetHeistCombatState(); awards = {}
                    is_client_val = true; whisper_mode_val = true
                    local damage = make_cop_damage(enemy('cop'),true)
                    damage['damage_' .. variant](damage,{attacker_unit=local_player,variant=variant})
                    assert(#kyohud._kills == 1)
                    assert(kyohud._kills[1].stealth == true, 'non-bullet client kill lacks style')
                ''')

    def test_context_reload_installs_each_hook_once(self):
        self.lua.execute('''
            function hook_count()
                local n = 0
                for _, registry in ipairs({_pre_hooks, _post_hooks}) do
                    for _, methods in pairs(registry) do
                        for _, entries in pairs(methods) do n = n + #entries end
                    end
                end
                return n
            end
            before_reload = hook_count()
        ''')
        for hook in json.loads((ROOT / "mod.txt").read_text())["hooks"]:
            if hook["script_path"] == "lua/ky_stealth.lua":
                self.lua.globals().RequiredScript = hook["hook_id"]
                self.lua.execute((ROOT / hook["script_path"]).read_text(encoding="utf-8"))
        self.lua.execute("assert(hook_count() == before_reload, 'reload duplicated hooks')")


class StealthPrimitiveRenderTests(unittest.TestCase):
    def setUp(self):
        from test_killfeed_render_extraction import (
            _make_lua, _load_production_chunks, _make_full_panel,
        )
        self.lua = _make_lua()
        _load_production_chunks(self.lua)
        _make_full_panel(self.lua)
        self.lua.execute('''
            kyohud.localized_text = function(id, fallback)
                if id == 'ky_hud_stealth_kill_label' then return 'FURTIF' end
                return fallback
            end
            function kyohud._panel:text(params)
                self.texts[#self.texts+1] = params
                local text = params.text
                return {
                    set_text = function(self, value) text = value end,
                    text_rect = function() return 0,0,#text * 5,10 end,
                }
            end
            kyohud.settings = {enable_killfeed=true, killfeed_size=5, icon_size=32, opacity=0.9}
            function render_entry(stealth)
                local entry = {name='Guard', stealth=stealth, start_t=99, t_end=104}
                kyohud._kills = {entry}
                kyohud._panel:clear()
                kyohud:render_killfeed(kyohud._panel,800,600,32,0.9,250)
                local found
                for _, text in ipairs(kyohud._panel.texts) do
                    if text.visible ~= false and text.text == entry._full_display_text then found=text end
                end
                assert(found, 'visible name primitive missing')
                return entry, found
            end
        ''')

    def test_stealth_label_measured_drawn_and_tinted(self):
        self.lua.execute('''
            local entry, text = render_entry(true)
            assert(text.text == 'FURTIF Guard')
            assert(entry._measured_name_w == #text.text * 5, 'label absent from measurement')
            assert(text.w >= entry._measured_name_w, 'card clips the label')
            assert(text.color == kyohud.STEALTH_KILLFEED_COLOR)
        ''')

    def test_loud_name_and_color_unchanged(self):
        self.lua.execute('''
            local entry, text = render_entry(false)
            assert(text.text == 'Guard')
            assert(entry._measured_name_w == 25)
            assert(text.color == kyohud.RENDER_CACHES.killfeed_name_color)
        ''')


if __name__ == "__main__":
    unittest.main()
