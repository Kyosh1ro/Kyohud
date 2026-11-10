"""NO DIAGNOSTIC contract; zero log messages and no diagnostic methods."""
import unittest
from test_hud_crew_acceptance import mounted


class CrewDiagnosticTests(unittest.TestCase):
    def test_no_diagnostics_during_transitions(self):
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
            kyohud._panel:rect({x=0,y=0,w=r:w(),h=r:h()})
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
            _total=#_messages
            _has_diagnostic=C._diagnostic~=nil
        ''')
        g=lua.globals()
        self.assertEqual(g._stable,0,'no log messages during stable phase')
        self.assertEqual(g._total,0,'no log messages across all transitions')
        self.assertFalse(g._has_diagnostic,'no _diagnostic method')
        self.assertIs(g._hidden,True)
        self.assertIs(g._render_hidden,True)
        self.assertIs(g._empty_hidden,True)


    def test_no_diagnostics_with_genuine_overlap(self):
        lua=mounted()
        lua.execute(r'''
            local lc=C._layout_cache
            local combat=panel_double:panel({name='diag_combat_root'})
            combat:set_shape(0,0,1280,1080)
            combat:set_visible(true)
            kyohud._panel=combat
            local card=C._cards[1]
            local drawn_y=C._root:y()+card.root:y()+card._backdrop:y()
            local obstacle=combat:rect({x=lc.x+5,y=drawn_y+5,w=46,h=27,visible=true})
            _name_attempts=0
            obstacle.name=function() _name_attempts=_name_attempts+1; return 'obstacle' end
            local root_before=C._root
            local card_before=C._cards[1]
            local name_before=card_before._name_text
            local health_before=card_before._health_text
            RT:update(managers.hud,2.0,.05)
            _hidden=not C._root:visible()
            obstacle:set_visible(false)
            RT:update(managers.hud,2.6,.05)
            _recovered=C:_verify_render() and C._root:visible()
            _same_root=C._root==root_before
            _same_card=C._cards[1]==card_before
            _same_name=C._cards[1]._name_text==name_before
            _same_health=C._cards[1]._health_text==health_before
            obstacle.name=function() _name_attempts=_name_attempts+1; error('name getter threw') end
            obstacle:set_visible(true)
            RT:update(managers.hud,3.2,.05)
            _hidden_again=not C._root:visible()
            obstacle:set_visible(false)
            RT:update(managers.hud,3.8,.05)
            _recovered_again=C:_verify_render() and C._root:visible()
            obstacle.name=false
            obstacle:set_visible(true)
            RT:update(managers.hud,4.4,.05)
            _hidden_final=not C._root:visible()
        ''')
        g=lua.globals()
        self.assertIs(g._hidden,True,'real overlap must hide crew')
        self.assertIs(g._recovered,True,'recovery must succeed when obstacle hides')
        self.assertIs(g._same_root,True,'root primitive must be preserved')
        self.assertIs(g._same_card,True,'card primitive must be preserved')
        self.assertIs(g._same_name,True,'name text primitive must be preserved')
        self.assertIs(g._same_health,True,'health text primitive must be preserved')
        self.assertIs(g._hidden_again,True,'obstacle must hide crew again')
        self.assertEqual(g._name_attempts,0,'name getter must not be called')
        self.assertIs(g._recovered_again,True,'recovery must succeed again')
        self.assertIs(g._hidden_final,True,'obstacle without name getter must hide crew')


if __name__=='__main__': unittest.main()
