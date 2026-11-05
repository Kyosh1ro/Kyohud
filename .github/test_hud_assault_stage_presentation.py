"""Distinct stage palettes, persistent ended announcement, 6/4 reminders."""
import unittest
import test_hud_assault_split_presentation as split
import test_hud_assault_alternation as alternation


class AssaultStagePresentationTests(unittest.TestCase):
    def assert_palette(self, lua, rgb):
        for channel, expected in zip(('r','g','b'),rgb):
            self.assertAlmostEqual(lua.eval('A._bg_rect:color().'+channel),expected,delta=.001)
        self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))

    def test_preparation_amber_and_endless_preserved(self):
        lua=split.make_banner()
        self.assert_palette(lua,(1,.68,.12))
        alternation.start_assault(lua)
        self.assert_palette(lua,(.949,.890,.106))
        lua.execute('''
            managers.groupai:state()._hunt_mode=true
            A:update(managers.hud,3,.2)
        ''')
        self.assert_palette(lua,(1,.165,.333))

    def test_new_sustain_and_fade_show_immediately_for_four_seconds(self):
        lua=split.make_banner()
        alternation.start_assault(lua)
        lua.execute('''
            managers.groupai:state()._task_data.assault.phase='sustain'
            A:update(managers.hud,2.6,.6)
        ''')
        self.assertEqual(lua.eval('A._ticker_a:text()'),'MAINTIEN')
        self.assert_palette(lua,(1,.48,.12))
        lua.execute('A:update(managers.hud,6.59,3.99)')
        self.assertEqual(lua.eval('A._ticker_a:text()'),'MAINTIEN')
        lua.execute('A:update(managers.hud,6.61,.02)')
        self.assertEqual(lua.eval('A._ticker_a:text()'),'DIFFICILE')
        lua.execute('''
            managers.groupai:state()._task_data.assault.phase='fade'
            A:update(managers.hud,7.2,.59)
        ''')
        self.assertEqual(lua.eval('A._ticker_a:text()'),'RETRAIT')
        self.assert_palette(lua,(.93,.87,.56))
        lua.execute('''
            A._bg_rect:set_color(Color(1,.1,.2,.3))
            _rejected=not A:_verify_render()
            A:update(managers.hud,7.8,.6)
        ''')
        self.assertTrue(lua.eval('_rejected'))
        self.assert_palette(lua,(.93,.87,.56))

    def test_client_periodic_reminder_starts_at_six_seconds(self):
        lua=split.make_banner()
        lua.execute('''
            Network._is_server=false
            managers.groupai:state()._is_server=false
            managers.hud:sync_start_assault(1)
            A:update(managers.hud,2,0)
            A:update(managers.hud,7.99,5.99)
            _before=A._ticker_a:text()
            A:update(managers.hud,8.01,.02)
            _reminder=A._ticker_a:text()
            A:update(managers.hud,11.99,3.98)
            _last=A._ticker_a:text()
            A:update(managers.hud,12.01,.02)
        ''')
        self.assertEqual(lua.eval('_before'),'DIFFICILE')
        self.assertEqual(lua.eval('_reminder'),'ASSAUT')
        self.assertEqual(lua.eval('_last'),'ASSAUT')
        self.assertEqual(lua.eval('A._ticker_a:text()'),'DIFFICILE')
        self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))

    def test_ended_heading_and_muted_palette_persist_without_lull_label(self):
        for language,ended in (('french','ASSAUT TERMINÉ'),('english','ASSAULT ENDED')):
            with self.subTest(language=language):
                lua=split.make_banner(language)
                alternation.start_assault(lua)
                lua.execute('''
                    local state=managers.groupai:state()
                    state._task_data.assault.active=false
                    state._task_data.assault.phase=nil
                    state._assault_mode=false
                    managers.hud._hud_assault_corner._assault=false
                    managers.hud:sync_end_assault(1)
                    A:update(managers.hud,3,.2)
                    A:update(managers.hud,3.2,.2)
                ''')
                self.assertEqual(lua.eval('A:_resolve_title_text()'),ended)
                self.assertNotIn('LULL',lua.eval('A._ticker_a:text()'))
                self.assert_palette(lua,(.30,.40,.49))
                lua.execute('A:update(managers.hud,20,16.8)')
                self.assertEqual(lua.eval('A:_resolve_title_text()'),ended)
                self.assertIn(ended+' /// ',lua.eval('A._title_a:text()'))
                self.assertEqual(lua.eval('A._ticker_a:text()'),'DIFFICILE' if language=='french' else 'HARD')
                self.assert_palette(lua,(.30,.40,.49))
                lua.execute('''
                    Global.game_settings.difficulty='unknown'
                    managers.job=nil
                    A:update(managers.hud,20.6,.6)
                ''')
                self.assertEqual(lua.eval('A._ticker_a:text()'),'--')
                self.assert_palette(lua,(.30,.40,.49))
                lua.execute('''
                    local state=managers.groupai:state()
                    state._task_data.assault.active=true
                    state._task_data.assault.phase='anticipation'
                    A:update(managers.hud,21.2,.6)
                    A:update(managers.hud,21.4,.2)
                ''')
                self.assertEqual(lua.eval('A:_resolve_title_text()'),
                                 'ASSAUT DE LA POLICE' if language=='french' else 'POLICE ASSAULT')
                self.assert_palette(lua,(1,.68,.12))
