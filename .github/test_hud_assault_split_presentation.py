"""Real-chunk contract for the approved split assault presentation."""
import json
from pathlib import Path
import unittest
import test_hud_assault_first_preparation as prep


def make_banner(language='french', width=1920, height=1080, scale=1):
    lua, ok = prep._make_base_lua()
    assert ok
    strings = json.loads((Path(__file__).resolve().parents[1] / 'loc' / (language+'.json')).read_text(encoding='utf-8-sig'))
    strings['menu_difficulty_hard'] = 'DIFFICILE' if language == 'french' else 'HARD'
    lua.globals()._strings = lua.table_from(strings)
    lua.execute('''
        function managers.localization:text(k) return _strings[k] or k end
        Global={game_settings={difficulty='hard'}}
        tweak_data.difficulty_name_ids={hard='menu_difficulty_hard'}
    ''')
    prep._set_host_anticipation(lua)
    lua.globals()._test_width=width
    lua.globals()._test_height=height
    lua.globals()._test_scale=scale
    lua.execute('''
        _init_fp:set_shape(0,0,_test_width,_test_height)
        kyohud.settings.hud_scale=_test_scale
        kyohud.hud.runtime:mount(managers.hud)
        A=kyohud.hud.assault
        A:mount(managers.hud)
        A:update(managers.hud,1,.05)
    ''')
    return lua


class SplitPresentationTests(unittest.TestCase):
    def test_state_width_tracks_ink_and_reclaims_space_for_title(self):
        lua=make_banner()
        lua.execute('''
            _title=A._title_a
            _state=A._ticker_a
            _logo_x=A._glyph_prim:x()
            local x,y,w,h=_state:text_rect()
            _prep_ink=w
            _prep_width=A._ticker_panel:w()
            _prep_title_width=A._title_panel:w()
            local state=managers.groupai:state()
            state._task_data.assault.phase='build'
            state._assault_mode=true
            managers.hud._hud_assault_corner._assault=true
            managers.hud:sync_start_assault(1)
            A:update(managers.hud,2,0)
            _start_cert=A:_verify_render()
            _transition_width=A._ticker_panel:w()
            A:update(managers.hud,2.075,.075)
            _mid_cert=A:_verify_render()
            A:update(managers.hud,2.16,.085)
            _settle_cert=A:_verify_render()
            local x,y,w,h=_state:text_rect()
            _build_ink=w
            _build_width=A._ticker_panel:w()
            _build_title_width=A._title_panel:w()
            _same=A._title_a==_title and A._ticker_a==_state
                and A._glyph_prim:x()==_logo_x
        ''')
        es=lua.eval('A._layout_cache.es')
        for phase in ('prep','build'):
            self.assertGreaterEqual(lua.eval('_'+phase+'_width'),lua.eval('_'+phase+'_ink'))
            self.assertLessEqual(lua.eval('_'+phase+'_width')-lua.eval('_'+phase+'_ink'),3*es)
        self.assertLess(lua.eval('_build_width'),lua.eval('_prep_width'))
        self.assertGreater(lua.eval('_build_title_width'),lua.eval('_prep_title_width'))
        self.assertGreaterEqual(lua.eval('_transition_width'),lua.eval('_prep_ink'))
        for flag in ('_start_cert','_mid_cert','_settle_cert','_same'):
            self.assertTrue(lua.eval(flag),flag)

    def test_named_difficulty_preserves_crime_spree_level(self):
        lua=make_banner()
        lua.execute('''
            managers.crime_spree={
                is_active=function() return true end,
                server_spree_level=function() return 123 end
            }
            local state=managers.groupai:state()
            state._task_data.assault.phase='build'
            state._assault_mode=true
            managers.hud._hud_assault_corner._assault=true
            managers.hud:sync_start_assault(1)
            A:update(managers.hud,2,.1)
        ''')
        self.assertIn('DIFFICILE',lua.eval('A._ticker_a:text()'))
        self.assertIn('[123]',lua.eval('A._ticker_a:text()'))
        self.assertNotIn('DIFFICILE',lua.eval('A._title_a:text()'))
        self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))

    def test_split_geometry_workspace_and_scale_matrix(self):
        for width,height in ((1920,1080),(1280,720),(1680,1050)):
            for scale in (.95,1,1.05):
                with self.subTest(width=width,height=height,scale=scale):
                    lua=make_banner(width=width,height=height,scale=scale)
                    expected=min(width/1920,height/1080)*scale
                    self.assertAlmostEqual(lua.eval('A._layout_cache.es'),expected)
                    self.assertEqual(lua.eval('A._ticker_a:font_size()'),max(12,int(20*expected)))
                    lua.execute('local x,y,w,h=A._ticker_a:text_rect(); _state_ink=w')
                    ink=lua.eval('_state_ink')
                    self.assertGreaterEqual(lua.eval('A._ticker_panel:w()'),ink)
                    self.assertLessEqual(lua.eval('A._ticker_panel:w()')-ink,3*expected+1e-6)
                    self.assertAlmostEqual(lua.eval('A._title_panel:w()+A._ticker_panel:w()'),316*expected)
                    self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))
                    self.assertTrue(lua.eval('A._ticker_b:x() > A._ticker_panel:w()'))

    def test_main_scrolls_and_localized_state_stays_fixed(self):
        for language,title,state,difficulty in (
            ('french','ASSAUT DE LA POLICE','PRÉPARATION','DIFFICILE'),
            ('english','POLICE ASSAULT','PREPARATION','HARD')):
            with self.subTest(language=language):
                lua=make_banner(language)
                self.assertTrue(lua.eval('A._title_a~=nil'), 'separate main title required')
                self.assertIn(title,lua.eval('A._title_a:text()'))
                self.assertNotIn(difficulty,lua.eval('A._title_a:text()'))
                self.assertEqual(lua.eval('A._ticker_a:text()'),state)
                lua.execute('''
                    _title,_state=A._title_a,A._ticker_a
                    _tx,_sx=_title:x(),_state:x()
                    A:update(managers.hud,1.1,.1)
                    _moves=_title:x()~=_tx
                    _fixed=_state:x()==_sx
                    _same=_title==A._title_a and _state==A._ticker_a
                    local tp,sp=_title:parent(),_state:parent()
                    _separated=tp:parent()==A._root_panel and sp:parent()==A._root_panel
                        and tp:x()+tp:w()<=sp:x() and sp:x()+sp:w()<=A._glyph_prim:x()
                    local x,y,w,h=_state:text_rect()
                    _fits=w<=sp:w() and h<=sp:h()
                ''')
                for flag in ('_moves','_fixed','_same','_separated','_fits'):
                    self.assertTrue(lua.eval(flag),flag)
                self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))

    def test_known_end_persists_as_lull(self):
        lua=make_banner()
        lua.execute('''
            local state=managers.groupai:state()
            state._task_data.assault.phase='build'
            state._assault_mode=true
            managers.hud._hud_assault_corner._assault=true
            managers.hud:sync_start_assault(1)
            A:update(managers.hud,2,.2)
            state._task_data.assault.active=false
            state._task_data.assault.phase=nil
            state._assault_mode=false
            managers.hud._hud_assault_corner._assault=false
            managers.hud:sync_end_assault(1)
            A:update(managers.hud,3,.2)
            A:update(managers.hud,3.2,.2)
            _after=A._ticker_a:text()
            A:update(managers.hud,5,.2)
            A:update(managers.hud,5.2,.2)
        ''')
        self.assertEqual(lua.eval('_after'),'DIFFICILE')
        self.assertEqual(lua.eval('A._ticker_a:text()'),'DIFFICILE')
        self.assertIn('ASSAUT TERMINÉ',lua.eval('A._title_a:text()'))
        self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired and A._root_panel:visible()'))
        lua.execute('''
            A:rebuild(managers.hud)
            A:update(managers.hud,6,.2)
        ''')
        self.assertEqual(lua.eval('A._ticker_a:text()'),'DIFFICILE')
        self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))
        lua.execute('''
            managers.hud._hud_assault_corner._point_of_no_return=true
            A:update(managers.hud,6.2,.1)
        ''')
        self.assertFalse(lua.eval('A._root_panel:visible()'))
        self.assertFalse(lua.eval('A._native_acquired'))
        lua.execute('''
            managers.hud._hud_assault_corner._point_of_no_return=false
            A:update(managers.hud,6.8,.1)
        ''')
        self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))
        lua.execute('''
            local old=managers.groupai:state()
            local fresh=setmetatable({}, {__index=old})
            fresh._task_data={assault={active=false}}
            managers.groupai.state=function() return fresh end
            A:update(managers.hud,7.5,.1)
        ''')
        self.assertFalse(lua.eval('A._state.presenting'))
        self.assertFalse(lua.eval('A._root_panel:visible()'))

    def test_title_corruptions_fail_closed_and_recover_same_primitives(self):
        lua=make_banner()
        self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))
        lua.execute('_saved_title=A._title_a; _saved_root=A._root_panel')
        mutations=(
            'A._title_a:set_text("BROKEN")',
            'A._title_a:set_x(A._title_a:x()+10)',
            'A._title_a:set_alpha(.2)',
            'A._title_a:set_layer(9)',
            'A._title_a:set_color(Color(1,.8,.1,.3))',
            'A._title_divider:set_x(A._title_divider:x()+8)',
            'A._title_panel:set_shape(99,0,20,20)',
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                lua.execute(mutation)
                self.assertFalse(lua.eval('A:_verify_render()'),mutation)
                lua.execute('A:update(managers.hud,(A._last_counter_time or 1)+.6,.05)')
                self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'),mutation)
                self.assertTrue(lua.eval('A._title_a==_saved_title and A._root_panel==_saved_root'))
        lua.execute('''
            _real_set_text=A._title_a.set_text
            A._title_a:set_text('BROKEN')
            A._title_a.set_text=function() end
            A:update(managers.hud,A._last_counter_time+.6,.05)
        ''')
        self.assertFalse(lua.eval('A._root_panel:visible()'))
        self.assertFalse(lua.eval('A._native_acquired'))
        lua.execute('''
            A._title_a.set_text=_real_set_text
            A:update(managers.hud,A._last_counter_time+.6,.05)
        ''')
        self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))
        self.assertTrue(lua.eval('A._title_a==_saved_title and A._root_panel==_saved_root'))

    def test_unknown_inactive_is_not_lull(self):
        lua=make_banner()
        lua.execute('''
            local state=managers.groupai:state()
            state._task_data.assault.active=false
            state._task_data.assault.phase=nil
            A:update(managers.hud,2,.1)
        ''')
        self.assertFalse(lua.eval('A._state.presenting'))
        self.assertFalse(lua.eval('A._root_panel:visible()'))
