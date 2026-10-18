"""Pager success rewards through native host/client paths, not optimistic completion."""
import json
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime
from test_stealth_first_batch import _common_stubs

ROOT = Path(__file__).resolve().parents[1]


class PagerRewardTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + "/"
        self.lua.execute(_common_stubs())
        self.lua.execute('''
            successes = 0; sound_ids = {}; next_sound_id = 10
            SoundDevice = {string_to_id = function(self, name)
                if not sound_ids[name] then next_sound_id=next_sound_id+1; sound_ids[name]=next_sound_id end
                return sound_ids[name]
            end}
            tweak_data.character = {security = {radio_prefix='prefix_'}, cop={}}
            local group = {
                whisper_mode = function() return whisper_mode_val end,
                get_nr_successful_alarm_pager_bluffs = function() return successes end,
            }
            managers.groupai.state = function() return group end
            CopBrain = {on_alarm_pager_interaction = function(self, status, player)
                if not whisper_mode_val or not self._alarm_pager_data then return end
                if status == 'complete' then
                    if not self.fail then successes=successes+1 end
                    self._alarm_pager_data = nil
                end
            end}
            CopSound = {play = function(self, name, source, sync) self.last_sound=name end}
            IntimitateInteractionExt._at_interact_interupt = function() end
            IntimitateInteractionExt.sync_interacted = function() end
            IntimitateInteractionExt.interact = function(self, player)
                if not self:can_interact(player) then return end
                if self.tweak_data == 'corpse_alarm_pager' then
                    if is_client_val then
                        -- The native client updates its count before host decides.
                        successes = successes + 1
                    else
                        self.brain:on_alarm_pager_interaction('complete',player)
                    end
                end
            end
            function pager(prefix)
                local unit = enemy(prefix == false and 'cop' or 'security')
                local brain = setmetatable({_unit=unit,_alarm_pager_data={}}, {__index=CopBrain})
                local sound = setmetatable({_unit=unit}, {__index=CopSound})
                local interaction = setmetatable({
                    _unit=unit,brain=brain,tweak_data='corpse_alarm_pager',_tweak_data={},
                }, {__index=IntimitateInteractionExt})
                return unit,interaction,brain,sound
            end
        ''')
        wanted = {
            "lua/core.lua", "lua/ky_combat_medals.lua", "lua/ky_hud_banners.lua",
            "lua/ky_killfeed.lua", "lua/ky_stealth.lua", "lua/ky_pager.lua", "lua/ky_buff_render.lua",
        }
        hooks = json.loads((ROOT / "mod.txt").read_text(encoding="utf-8"))["hooks"]
        for context in (
            "lib/managers/hudmanagerpd2", "lib/managers/playermanager",
            "lib/units/enemies/cop/copdamage", "lib/units/enemies/cop/copbrain",
            "lib/units/interactions/interactionext", "lib/units/enemies/cop/copsound",
        ):
            for hook in hooks:
                if hook["hook_id"] == context and hook["script_path"] in wanted:
                    self.lua.globals().RequiredScript = context
                    self.lua.execute((ROOT / hook["script_path"]).read_text(encoding="utf-8-sig"))
        self.lua.execute('''
            kyohud.settings = {enable_killfeed=true,killfeed_size=5}
            kyohud:ResetHeistCombatState()
        ''')

    def test_host_accepted_pager_banner_score_and_no_kill_state(self):
        self.lua.execute('''
            whisper_mode_val=true
            local unit,interaction= pager()
            interaction:interact(local_player)
            assert(#kyohud._kills == 1, 'accepted pager needs one event card')
            local entry=kyohud._kills[1]
            assert(entry.action == 'pager_answered' and entry.score == 5)
            assert(entry.name == 'Pager answered')
            assert(kyohud._special_kill_banner.label == 'PAGER ANSWERED')
            assert(kyohud._special_kill_banner.multikill_style == true)
            assert(kyohud._heist_score_total == 5 and kyohud._killfeed_score_total == 5)
            assert(kyohud._kill_combo.count == 0 and kyohud._heist_kill_count == 0)
            assert(not kyohud._first_blood_done and not kyohud._medal_card)
            assert(not kyohud._recorded_kill_units[unit], 'action must not dedup as enemy kill')
        ''')

    def test_host_failure_interruption_third_party_and_loud_no_reward(self):
        self.lua.execute('''
            whisper_mode_val=true
            local unit,interaction,brain=pager(); brain.fail=true
            interaction:interact(local_player)
            local u2,i2,b2=pager(); b2:on_alarm_pager_interaction('interrupted',local_player)
            local u3,i3,b3=pager(); i3:interact({})
            whisper_mode_val=false
            local u4,i4=pager(); i4:interact(local_player)
            assert(#kyohud._kills == 0 and kyohud._heist_score_total == 0)
        ''')

    def test_client_completion_alone_is_not_success(self):
        self.lua.execute('''
            is_client_val=true; whisper_mode_val=true
            local unit,interaction,brain,sound=pager()
            interaction:interact(local_player)
            assert(successes == 1, 'test must exercise native optimistic counter')
            assert(#kyohud._kills == 0)
            local accepted=SoundDevice:string_to_id('prefix_dsp_radio_fooled_1')
            sound:play(accepted,'',false)
            assert(#kyohud._kills == 1 and kyohud._kills[1].score == 5)
            sound:play(accepted,'',false)
            assert(#kyohud._kills == 1, 'duplicate success sound rewarded twice')
        ''')

    def test_client_alarm_query_spectator_and_expired_response(self):
        self.lua.execute('''
            is_client_val=true; whisper_mode_val=true
            local unit,interaction,brain,sound=pager()
            interaction:interact(local_player)
            sound:play(SoundDevice:string_to_id('prefix_dsp_radio_alarm_1'),'',false)
            sound:play(SoundDevice:string_to_id('prefix_dsp_radio_fooled_1'),'',false)
            local u2,i2,b2,s2=pager()
            s2:play(SoundDevice:string_to_id('prefix_dsp_radio_fooled_1'),'',false)
            local u3,i3,b3,s3=pager(); i3:interact(local_player)
            game_t=game_t+20
            s3:play(SoundDevice:string_to_id('prefix_dsp_radio_fooled_1'),'',false)
            assert(#kyohud._kills == 0 and kyohud._heist_score_total == 0)
        ''')

    def test_client_final_pager_unprefixed_and_unrelated_sound(self):
        self.lua.execute('''
            is_client_val=true; whisper_mode_val=true
            local unit,interaction,brain,sound=pager(false)
            interaction:interact(local_player)
            sound:play(SoundDevice:string_to_id('dsp_radio_query_1'),'',false)
            assert(#kyohud._kills == 0)
            sound:play(SoundDevice:string_to_id('dsp_radio_fooled_4'),'',false)
            assert(#kyohud._kills == 1)
        ''')

    def test_other_responders_completion_cancels_local_pending(self):
        self.lua.execute('''
            is_client_val=true; whisper_mode_val=true
            local unit,interaction,brain,sound=pager()
            interaction:interact(local_player)
            -- The host excludes the actual responder from this completion relay.
            interaction:sync_interacted(nil,nil,3)
            sound:play(SoundDevice:string_to_id('prefix_dsp_radio_fooled_1'),'',false)
            assert(#kyohud._kills == 0, 'another responder received local credit')
        ''')

    def test_client_cancel_and_reset_clear_pending(self):
        self.lua.execute('''
            is_client_val=true; whisper_mode_val=true
            local unit,interaction,brain,sound=pager()
            interaction:interact(local_player)
            interaction:_at_interact_interupt(local_player,false)
            sound:play(SoundDevice:string_to_id('prefix_dsp_radio_fooled_1'),'',false)
            local u2,i2,b2,s2=pager(); i2:interact(local_player)
            kyohud:ResetHeistCombatState()
            s2:play(SoundDevice:string_to_id('prefix_dsp_radio_fooled_1'),'',false)
            assert(#kyohud._kills == 0 and not kyohud._special_kill_banner)
        ''')

    def test_three_variants_cycle_without_affecting_combo(self):
        self.lua.execute('''
            whisper_mode_val=true
            kyohud._kill_combo = {count=3,last_t=99,updated_t=99,label='UNCHANGED'}
            local labels={}
            for n=1,4 do
                game_t=game_t+3; kyohud._special_kill_banner=nil
                local unit,interaction=pager()
                interaction:interact(local_player)
                labels[n]=kyohud._special_kill_banner.label
            end
            assert(labels[1]=='PAGER ANSWERED' and labels[2]=='ALL CLEAR')
            assert(labels[3]=='NOTHING TO REPORT' and labels[4]==labels[1])
            assert(kyohud._kill_combo.count==3 and kyohud._kill_combo.last_t==99)
        ''')

    def test_preview_covers_all_pager_variants_without_consuming_real_pagers(self):
        self.lua.execute('''
            local seen = {}
            local cases = kyohud.DEBUG_BANNER_PREVIEWS
            for index, case in ipairs(cases) do
                if case.banner == 'pager' then
                    kyohud._debug_banner_preview_index = index-1
                    kyohud:DebugSimulate()
                    assert(kyohud._special_kill_banner.preview)
                    seen[kyohud._special_kill_banner.label] = true
                    assert(kyohud._kills[#kyohud._kills].action == 'pager_answered')
                    assert(not next(kyohud._pager_state.awarded), 'preview consumed pager award')
                    kyohud:DebugClear()
                    assert(#kyohud._kills==0 and kyohud._heist_score_total==0)
                end
            end
            assert(seen['PAGER ANSWERED'] and seen['ALL CLEAR'] and seen['NOTHING TO REPORT'])
        ''')

    def test_difficulty_multiplier_and_killfeed_hidden_accounting(self):
        self.lua.execute('''
            whisper_mode_val=true
            Global={game_settings={difficulty='sm_wish'}}
            kyohud.settings.enable_killfeed=false
            local expected=5 * kyohud:GetKillScore('cop',false)
            local unit,interaction=pager(); interaction:interact(local_player)
            assert(kyohud._heist_score_total == expected)
            assert(kyohud._kills[1].score == expected)
        ''')


class PagerBannerRenderTests(unittest.TestCase):
    def test_real_banner_and_event_card_fit_all_variations(self):
        from test_killfeed_render_extraction import _make_lua, _load_production_chunks, _make_full_panel
        lua = _make_lua()
        _load_production_chunks(lua)
        lua.execute((ROOT / 'lua/ky_pager.lua').read_text(encoding='utf-8'))
        _make_full_panel(lua)
        lua.execute('''
            kyohud.settings={enable_killfeed=true,killfeed_size=5,icon_size=32,opacity=0.9}
            for variant=1,3 do
                kyohud:ResetHeistCombatState()
                kyohud:AddActionEntry('pager_answered','Pager answered',5)
                local banner=kyohud:MakePagerBanner(variant)
                kyohud:_show_special_banner(game_t-0.2,banner,false)
                kyohud._panel:clear()
                kyohud:render_killfeed(kyohud._panel,800,600,32,0.9,250)
                local saw_banner,saw_entry,saw_score=false,false,false
                for _,text in ipairs(kyohud._panel.texts) do
                    if text.visible ~= false then
                        if text.text==banner.label then
                            saw_banner=true
                            assert(#text.text*text.font_size*0.58<=text.w,'pager banner label clipped')
                        elseif text.text=='Pager answered' then saw_entry=true
                        elseif text.text=='+5' then saw_score=true end
                    end
                end
                assert(saw_banner and saw_entry and saw_score,'missing banner/action/score primitive')
                assert(kyohud._kill_combo.count==0)
            end
        ''')


if __name__ == '__main__':
    unittest.main()
