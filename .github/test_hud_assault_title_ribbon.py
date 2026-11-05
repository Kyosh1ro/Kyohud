"""Short title ribbons repeat with ///; BUILD is not a displayed reminder."""
import unittest
import test_hud_assault_split_presentation as split
import test_hud_assault_alternation as alternation


class AssaultTitleRibbonTests(unittest.TestCase):
    def test_lull_title_also_repeats_after_known_end(self):
        lua=split.make_banner('english')
        alternation.start_assault(lua)
        lua.execute('''
            local state=managers.groupai:state()
            state._task_data.assault.active=false
            state._task_data.assault.phase=nil
            state._assault_mode=false
            managers.hud._hud_assault_corner._assault=false
            managers.hud:sync_end_assault(1)
            A:update(managers.hud,3,.2)
            A:update(managers.hud,5,2)
            local dt=(A._title_cycle-.1+A._title_x)/(60*A._layout_cache.es)
            A:update(managers.hud,5+dt,dt)
        ''')
        self.assertEqual(lua.eval('A._ticker_a:text()'),'HARD')
        self.assertTrue(lua.eval('A._title_a:text()').startswith('ASSAULT ENDED /// '))
        self.assertGreaterEqual(lua.eval('A._title_b:x()+A._title_b:w()'),lua.eval('A._title_panel:w()'))
        self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))

    def test_short_title_repeats_and_covers_clip_through_full_cycle(self):
        lua=split.make_banner('english')
        self.assertIn(' /// ',lua.eval('A._title_a:text()'))
        self.assertGreaterEqual(lua.eval('A._title_a:w()'),lua.eval('A._title_panel:w()'))
        lua.execute('''
            _a,_b=A._title_a,A._title_b
            _time=1
            _step=A._title_cycle/(60*A._layout_cache.es)/20
        ''')
        for _ in range(22):
            lua.execute('''
                _time=_time+_step
                A:update(managers.hud,_time,_step)
                _coverage=A._title_a:x()<=0
                    and A._title_a:x()+A._title_a:w()>=A._title_b:x()-.5
                    and A._title_b:x()+A._title_b:w()>=A._title_panel:w()
            ''')
            self.assertTrue(lua.eval('_coverage'))
            self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))
        self.assertTrue(lua.eval('A._title_a==_a and A._title_b==_b'))
        lua.execute('A._title_b:set_text("BROKEN")')
        self.assertFalse(lua.eval('A:_verify_render()'))
        lua.execute('A:update(managers.hud,_time+.6,.05)')
        self.assertTrue(lua.eval('A:_verify_render() and A._title_b==_b'))

    def test_build_reminder_is_replaced_by_difficulty_but_sustain_remains(self):
        lua=split.make_banner()
        alternation.start_assault(lua)
        lua.execute('A:update(managers.hud,10.1,8.1)')
        self.assertEqual(lua.eval('A._ticker_a:text()'),'DIFFICILE')
        self.assertEqual(lua.eval('A:_resolve_status_label()'),'MONTÉE')
        lua.execute('''
            managers.groupai:state()._task_data.assault.phase='sustain'
            A:update(managers.hud,10.7,.6)
        ''')
        self.assertEqual(lua.eval('A._ticker_a:text()'),'MAINTIEN')
        self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))
