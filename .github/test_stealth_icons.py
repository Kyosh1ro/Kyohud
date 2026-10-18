"""Native preplanning atlas icons for the stealth medals and pager feed card."""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime
from test_stealth_first_batch import _common_stubs

ROOT = Path(__file__).resolve().parents[1]


class StealthIconTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + '/'
        self.lua.globals().RequiredScript = 'lib/managers/hudmanagerpd2'
        self.lua.execute(_common_stubs())
        self.lua.execute('''
            requested = {}
            tweak_data.preplanning = {
                gui = {type_icons_path = 'guis/native_preplanning'},
                get_type_texture_rect = function(self,id)
                    requested[#requested+1] = id
                    return {id,777,48,48}
                end,
            }
        ''')
        for filename in ('core.lua', 'ky_combat_medals.lua', 'ky_hud_banners.lua', 'ky_pager.lua'):
            self.lua.execute((ROOT / 'lua' / filename).read_text(encoding='utf-8-sig'))

    def test_selected_medals_request_real_atlas_ids(self):
        self.lua.execute('''
            for event,id in pairs({stealth_melee=72,silent_guard=105,backstab=94}) do
                local card = kyohud.MakeEventMedalCard(event)
                assert(card.icon.texture == 'guis/native_preplanning', 'stealth medal uses wrong texture')
                assert(card.icon.rect[1] == id and card.icon.rect[2] == 777,
                    'native atlas lookup result was not preserved')
                assert(requested[#requested] == id, 'wrong native icon ID requested')
            end
            local civilian = kyohud.MakeEventMedalCard('tied_civilian')
            assert(civilian.icon.texture == 'resolved/equipment_cable_ties')
        ''')

    def test_preplanning_fallback_uses_verified_native_grid(self):
        self.lua.execute('''
            tweak_data.preplanning = nil
            local expected = {
                [32]={96,48,48,48}, [72]={288,48,48,48},
                [94]={384,144,48,48}, [105]={432,192,48,48},
            }
            for id,coords in pairs(expected) do
                local texture,rect = kyohud.get_icon_data({preplanning=id})
                assert(texture=='guis/dlcs/deep/textures/pd2/pre_planning/preplan_icon_types')
                assert(rect, 'native fallback rect missing')
                for i=1,4 do assert(rect[i]==coords[i], 'wrong fallback cell') end
            end
        ''')

    def test_broken_native_lookup_retains_verified_fallback(self):
        self.lua.execute('''
            tweak_data.preplanning.get_type_texture_rect = function() error('engine boundary') end
            local texture,rect=kyohud.get_icon_data({preplanning=72})
            assert(texture=='guis/native_preplanning' and rect[1]==288 and rect[2]==48)
        ''')

    def test_missing_texture_fails_to_existing_safe_icon(self):
        self.lua.execute('''
            DB.has=function() return false end
            local texture,rect=kyohud.get_icon_data({preplanning=72})
            assert(texture==kyohud.FALLBACK_TEXTURE and rect==nil)
        ''')

    def test_pager_action_has_radio_but_banner_has_no_icon(self):
        self.lua.execute('''
            kyohud.settings={enable_killfeed=true,killfeed_size=5}
            kyohud:ResetHeistCombatState()
            local icon = assert(kyohud.GetPagerIconDescriptor, 'pager radio resolver missing')(kyohud)
            kyohud:AddActionEntry('pager_answered','Pager answered',5,icon)
            assert(kyohud._kills[1].action_icon == icon, 'radio not attached to action card')
            assert(icon.texture == 'guis/native_preplanning' and icon.rect[1] == 32)
            assert(kyohud:MakePagerBanner(1).icon == nil, 'radio should not fill big banner')
        ''')


class PagerRadioRenderTests(unittest.TestCase):
    def test_radio_bitmap_reserves_space_and_keeps_exact_atlas_rect(self):
        from test_killfeed_render_extraction import _make_lua, _load_production_chunks, _make_full_panel
        lua = _make_lua()
        _load_production_chunks(lua)
        _make_full_panel(lua)
        lua.execute('''
            kyohud.settings={enable_killfeed=true,killfeed_size=5,icon_size=32,opacity=0.9}
            local icon={texture='guis/radio',rect={96,48,48,48}}
            kyohud:AddActionEntry('pager_answered','Pager answered',5,icon)
            game_t=100.3
            kyohud:render_killfeed(kyohud._panel,800,600,32,0.9,250)
            local bitmap,name,score
            for _,item in ipairs(kyohud._panel.bitmaps) do
                if item.texture=='guis/radio' then bitmap=item end
            end
            for _,text in ipairs(kyohud._panel.texts) do
                if text.visible~=false then
                    if text.text=='Pager answered' then name=text
                    elseif text.text=='+5' then score=text end
                end
            end
            assert(bitmap and name and score, 'radio/name/score not rendered')
            assert(bitmap.texture_rect==icon.rect, 'radio atlas rect lost')
            assert(bitmap.x+bitmap.w<=name.x, 'radio overlaps action name')
            assert(name.x+name.w<=score.x, 'name overlaps score')
            assert(bitmap.h<=name.h, 'radio exceeds card height')
        ''')


if __name__ == '__main__':
    unittest.main()
