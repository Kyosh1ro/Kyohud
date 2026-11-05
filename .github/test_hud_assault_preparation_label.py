"""Preparation must have an immediately visible stationary label."""
import unittest
import test_hud_assault_split_presentation as split
import test_hud_assault_alternation as alternation


class PreparationLabelTests(unittest.TestCase):
    def test_preparation_entry_is_opaque_after_known_end(self):
        for language,label in (('english','PREPARATION'),('french','PRÉPARATION')):
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
                    A:update(managers.hud,5,2)
                    _right=A._ticker_a
                    state._task_data.assault.active=true
                    state._task_data.assault.phase='anticipation'
                    A:update(managers.hud,5.6,0)
                ''')
                self.assertEqual(lua.eval('A._ticker_a:text()'),label)
                self.assertEqual(lua.eval('A._ticker_a:alpha()'),1)
                self.assertFalse(lua.eval('A._transition_active'))
                self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))
                lua.execute('A:update(managers.hud,5.65,.05)')
                self.assertEqual(lua.eval('A._ticker_a:alpha()'),1)
                self.assertTrue(lua.eval('A._ticker_a==_right and A._ticker_a:x()==0'))
                self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))
