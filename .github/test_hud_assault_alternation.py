"""The right cell uses 6/4 cycles and announces qualified phase changes."""
import unittest
import test_hud_assault_split_presentation as split


def start_assault(lua, time=2):
    lua.globals()._start_time=time
    lua.execute('''
        local state=managers.groupai:state()
        state._task_data.assault.phase='build'
        state._task_data.assault.active=true
        state._assault_mode=true
        managers.hud._hud_assault_corner._assault=true
        managers.hud:sync_start_assault(1)
        A:update(managers.hud,_start_time,0)
    ''')


class AssaultAlternationTests(unittest.TestCase):
    def test_client_reminder_stays_generic_despite_local_task_phase(self):
        lua=split.make_banner()
        lua.execute('''
            Network._is_server=false
            local state=managers.groupai:state()
            state._is_server=false
            state._task_data.assault.phase='sustain'
            managers.hud:sync_start_assault(1)
            A:update(managers.hud,2,0)
            _difficulty=A._ticker_a:text()
            A:update(managers.hud,10.1,8.1)
        ''')
        self.assertEqual(lua.eval('_difficulty'),'DIFFICILE')
        self.assertEqual(lua.eval('A._ticker_a:text()'),'ASSAUT')
        self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))

    def test_rebuild_preserves_cycle_and_source_change_resets_it(self):
        lua=split.make_banner()
        start_assault(lua)
        lua.execute('''
            managers.groupai:state()._task_data.assault.phase='sustain'
            A:update(managers.hud,10.2,8.2)
            A:rebuild(managers.hud)
            A:update(managers.hud,10.3,.1)
            _rebuilt=A._ticker_a:text()
            local old=managers.groupai:state()
            local fresh=setmetatable({}, {__index=old})
            fresh._task_data={assault={active=true,phase='sustain'}}
            managers.groupai.state=function() return fresh end
            A:update(managers.hud,11,.7)
        ''')
        self.assertEqual(lua.eval('_rebuilt'),'MAINTIEN')
        self.assertEqual(lua.eval('A._ticker_a:text()'),'DIFFICILE')
        self.assertTrue(lua.eval('A:_verify_render() and A._native_acquired'))

    def test_phase_change_immediate_then_four_second_hold(self):
        lua=split.make_banner()
        start_assault(lua)
        self.assertEqual(lua.eval('A._ticker_a:text()'),'DIFFICILE')
        self.assertEqual(lua.eval('A:_resolve_title_text()'),'ASSAUT POLICIER EN COURS')
        self.assertTrue(lua.eval('A._title_a:text()').startswith('ASSAUT POLICIER EN COURS /// '))
        lua.execute('''
            _right=A._ticker_a
            _title=A._title_a
            A:update(managers.hud,2.4,.4)
            _before=A._ticker_a:text()
            managers.groupai:state()._task_data.assault.phase='sustain'
            A:update(managers.hud,2.6,.2)
            _reminder=A._ticker_a:text()
            _start=A:_verify_render() and A._native_acquired
            A:update(managers.hud,2.655,.055)
            _mid=A:_verify_render() and A._native_acquired
            A:update(managers.hud,2.76,.105)
            _settled=A:_verify_render() and A._native_acquired
            A:update(managers.hud,6.59,3.83)
            _held=A._ticker_a:text()
            A:update(managers.hud,6.61,.02)
            _returned=A._ticker_a:text()
            local state=managers.groupai:state()
            state._task_data.assault.phase='fade'
            A:update(managers.hud,7.2,.59)
            _fresh_phase=A._ticker_a:text()
            A:update(managers.hud,7.36,.16)
            _end=A:_verify_render() and A._native_acquired
            _same=A._ticker_a==_right and A._title_a==_title
            _fixed=A._ticker_a:x()==0
        ''')
        self.assertEqual(lua.eval('_before'),'DIFFICILE')
        self.assertEqual(lua.eval('_reminder'),'MAINTIEN')
        self.assertEqual(lua.eval('_held'),'MAINTIEN')
        self.assertEqual(lua.eval('_fresh_phase'),'RETRAIT')
        self.assertEqual(lua.eval('_returned'),'DIFFICILE')
        for flag in ('_start','_mid','_settled','_end','_same','_fixed'):
            self.assertTrue(lua.eval(flag),flag)

    def test_preparation_and_lull_do_not_alternate_and_new_assault_resets(self):
        lua=split.make_banner()
        lua.execute('A:update(managers.hud,11,10)')
        self.assertEqual(lua.eval('A._ticker_a:text()'),'PRÉPARATION')
        start_assault(lua,12)
        lua.execute('''
            A:update(managers.hud,20.1,8.1)
            local state=managers.groupai:state()
            state._task_data.assault.active=false
            state._task_data.assault.phase=nil
            state._assault_mode=false
            managers.hud._hud_assault_corner._assault=false
            managers.hud:sync_end_assault(1)
            A:update(managers.hud,21,.9)
            _after=A._ticker_a:text()
            A:update(managers.hud,23,2)
            A:update(managers.hud,33,10)
            _lull=A._ticker_a:text()
        ''')
        self.assertEqual(lua.eval('_after'),'DIFFICILE')
        self.assertEqual(lua.eval('_lull'),'DIFFICILE')
        self.assertEqual(lua.eval('A:_resolve_title_text()'),'ASSAUT TERMINÉ')
        start_assault(lua,34)
        self.assertEqual(lua.eval('A._ticker_a:text()'),'DIFFICILE')
