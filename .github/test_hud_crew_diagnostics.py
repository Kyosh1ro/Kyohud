"""Temporary bounded transition diagnostics; no display-policy change."""
import unittest
from test_hud_crew_acceptance import mounted


class CrewDiagnosticTests(unittest.TestCase):
    def test_logs_visible_conflict_render_and_empty_only_on_transition_with_cap(self):
        lua=mounted()
        lua.execute(r'''
            _messages={}
            function log(message) _messages[#_messages+1]=message end
            RT:update(managers.hud,1.1,.05)
            RT:update(managers.hud,1.2,.05)
            _stable=#_messages
            local r=C._root
            kyohud._panel=panel_double:panel({name='diag_sentinel'})
            kyohud._panel:set_shape(r:x(),r:y(),r:w(),r:h())
            RT:update(managers.hud,1.7,.05)
            RT:update(managers.hud,1.8,.05)
            _hidden=not r:visible()
            kyohud._panel:set_visible(false)
            RT:update(managers.hud,2.3,.05)
            local p=C._cards[1]._equipment_text
            local measure=p.text_rect
            p.text_rect=function() return 0,0,999,999 end
            RT:update(managers.hud,2.4,.05)
            _render_hidden=not r:visible()
            p.text_rect=measure
            RT:update(managers.hud,2.5,.05)
            for _,rec in ipairs(managers.criminals:characters()) do rec.taken=false end
            RT:update(managers.hud,3.1,.05)
            _empty_hidden=not r:visible()
            _joined=table.concat(_messages,'\n')
            if C._diagnostic then
                for i=1,50 do C:_diagnostic(i%2==0 and 'visible' or 'empty') end
            end
            _capped=#_messages
        ''')
        g=lua.globals()
        self.assertLessEqual(g._stable,1)
        self.assertIs(g._hidden,True)
        self.assertIs(g._render_hidden,True)
        self.assertIs(g._empty_hidden,True)
        for marker in ('[KyoHUD][CrewDiag]','conflict','render','equipment','empty','visible'):
            self.assertIn(marker,g._joined)
        self.assertLessEqual(g._capped,12)


if __name__=='__main__': unittest.main()
