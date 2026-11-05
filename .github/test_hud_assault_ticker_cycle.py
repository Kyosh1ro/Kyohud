"""Keep a retained scrolling ticker valid when its measured cycle shrinks."""
import unittest

import test_hud_assault_states as states


class AssaultTickerCycleTests(unittest.TestCase):
    def test_preparation_to_shorter_build_at_end_of_old_cycle(self):
        lua, ok = states.AssaultMultiStateLabelTests()._make_lua(
            True, "anticipation", False, False, False, False
        )
        self.assertTrue(ok)
        lua.execute(r'''
            local A = kyohud.hud.assault
            local original_loc = managers.localization.text
            _difficulty_label = string.rep("LONG DIFFICULTY ", 6)
            function managers.localization:text(key)
                if key == "ky_hud_assault_title" or key == "ky_hud_assault_active_title" then
                    return _difficulty_label
                end
                return original_loc(self,key)
            end
            A:update(managers.hud,1.6,0)
            _root_before = A._root_panel
            _a_before, _b_before = A._ticker_a, A._ticker_b
            _title_before = A._title_a
            local cycle = A._title_cycle
            -- Reach the end of the longer preparation via real scrolling,
            -- without injecting renderer positions or desired state.
            local dt = (cycle - 2 + A._title_x) / (60 * A._layout_cache.es)
            _now = 1.6 + dt
            A:update(managers.hud, _now, dt)
            _old_x = A._title_a:x()
            _old_cycle = A._title_cycle
            _positive_before = A:_verify_render() and A._native_acquired
            local state = managers.groupai:state()
            state._assault_mode = true
            state._task_data.assault.phase = "build"
            managers.hud._hud_assault_corner._assault = true
            managers.hud:sync_start_assault(1)
            _difficulty_label = "SHORT"
            A:update(managers.hud, _now + 0.6, 0)
            _new_cycle = A._title_cycle
            _start_verified = A:_verify_render()
            _start_owned = A._native_acquired and A._root_panel:visible()
        ''')
        self.assertTrue(lua.eval('_positive_before'))
        self.assertLess(lua.eval('_new_cycle'), lua.eval('_old_cycle'))
        self.assertLess(lua.eval('_old_x'), -lua.eval('_new_cycle') - 0.5)
        self.assertTrue(lua.eval('_start_verified'),
                        "shorter build must certify before its next scrolling tick")
        self.assertTrue(lua.eval('_start_owned'))
        lua.execute(r'''
            local A = kyohud.hud.assault
            _out_a, _out_b = A._outgoing_ticker_a, A._outgoing_ticker_b
            assert(_out_a and _out_b)
            assert(_out_a:x() == 0, "outgoing state remains stationary")
            A:update(managers.hud, _now + 0.675, 0.075)
            _mid_verified = A:_verify_render() and A._native_acquired
            A:update(managers.hud, _now + 0.76, 0.085)
            _settled_verified = A:_verify_render() and A._native_acquired
            _identities = A._root_panel == _root_before
                and A._ticker_a == _a_before and A._ticker_b == _b_before
                and A._title_a == _title_before
            _settled_label = A._ticker_a:text()
            local saved = A._ticker_a:x()
            A._ticker_a:set_x(saved + 5)
            _corruption_rejected = not A:_verify_render()
            A._ticker_a:set_x(saved)
            _restored = A:_verify_render()
        ''')
        self.assertTrue(lua.eval('_mid_verified'))
        self.assertTrue(lua.eval('_settled_verified'))
        self.assertTrue(lua.eval('_identities'))
        self.assertEqual(lua.eval('_settled_label'), 'ASSAULT')
        self.assertEqual(lua.eval('kyohud.hud.assault:_resolve_status_label()'), 'MONTEE')
        self.assertTrue(lua.eval('_corruption_rejected'))
        self.assertTrue(lua.eval('_restored'))


if __name__ == '__main__':
    unittest.main()
