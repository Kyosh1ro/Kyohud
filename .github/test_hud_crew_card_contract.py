"""Actual actor schema and measured text budget; no invented source fields."""
import unittest
from test_hud_crew_card import _lua


class CrewCardActualContractTests(unittest.TestCase):
    def test_constructor_font_only_no_native_font_getter_or_setter(self):
        lua, ok = _lua()
        self.assertTrue(ok)
        lua.execute('''
            local mt=getmetatable(panel_double).__index
            _font_calls=0
            function mt:font()
                _font_calls=_font_calls+1
                error('unsafe Diesel font getter')
            end
            function mt:set_font()
                _font_calls=_font_calls+1
                error('unsafe Diesel font setter')
            end
            _font_constructors=0
            local text=mt.text
            function mt:text(config)
                if type(config)=='table' then
                    assert(config.font=='fonts/font_medium_mf')
                    _font_constructors=_font_constructors+1
                end
                return text(self,config)
            end
        ''')
        from test_hud_crew_card import CREW_CARD_PATH
        lua.execute(CREW_CARD_PATH.read_text(encoding='utf-8-sig'))
        lua.execute('''
            card=kyohud.hud.crew_card.new(panel_double,'font_id')
            card:set_geometry(0,0,280,120)
            card:update({name='Alice'},0)
            _cert=card:verify()
            local name=card._name_text
            _all_verified=true
            for i=1,5 do
                card:update({name='Alice'},i*.1)
                if not card:verify() then _all_verified=false end
            end
            _same=card._name_text==name
        ''')
        self.assertEqual(lua.globals()._font_calls,0,
                         'neither font() nor set_font() is permitted, even inside pcall')
        self.assertGreater(lua.globals()._font_constructors,0)
        self.assertIs(lua.globals()._cert,True)
        self.assertIs(lua.globals()._same,True)
        self.assertIs(lua.globals()._all_verified,True)

    def test_localized_names_independent_unknowns_and_unlimited(self):
        lua, ok = _lua()
        self.assertTrue(ok)
        lua.execute('''
            managers={localization={text=function(self,key)
                return ({wpn_long='Shotgun',dep_long='Medic',ky_hud_crew_ai='AI'})[key] or key
            end}}
            card=kyohud.hud.crew_card.new(panel_double,'actual')
            card:set_geometry(0,0,280,120)
            actor={name='Alice',ai=false,health={valid=true,ratio=.659},
                weapon={name_id='wpn_long',ammo={reserve=40}},
                equipment={deployable={name_id='dep_long',id='doctor_bag'},cable_ties={amount=-1}}}
            card:update(actor,0)
            _weapon=card._weapon_text:text()
            _dep=card._equipment_text:text()
            _cables=card._cables_text:text()
            _hp=card._health_text:text()
            card:update({name='Dallas',ai=true,phase='bleedout'},1)
            _bot=card._name_text:text()
            _phase=card._status_text:text()
        ''')
        g=lua.globals()
        self.assertIn('Shotgun',g._weapon)
        self.assertIn('--/40',g._weapon)
        self.assertIn('Medic',g._dep)
        self.assertIn('--',g._dep)
        self.assertIn('∞',g._cables)
        self.assertEqual(g._hp,'66%')
        self.assertEqual(g._bot,'Dallas AI')
        self.assertIn('bleed',g._phase.lower())

    def test_long_names_never_trim_numeric_suffix_and_readback_requires_measurement(self):
        lua, ok = _lua()
        self.assertTrue(ok)
        lua.execute('''
            card=kyohud.hud.crew_card.new(panel_double,'long')
            card:set_geometry(0,0,266,114)
            actor={name=string.rep('É',90),weapon={name_id=string.rep('W',100),ammo={current_clip=123,reserve=4567}},
                equipment={deployable={name_id=string.rep('D',100),amount=123}}}
            card:update(actor,0)
            _good=card:verify()
            _wp=card._weapon_text:text(); _dep=card._equipment_text:text()
            _min_font=math.min(card._weapon_text:font_size(),card._equipment_text:font_size())
            local mt=getmetatable(panel_double).__index
            local measure=mt.text_rect
            mt.text_rect=nil
            _no_measure=card:verify()
            mt.text_rect=measure
            _restored=card:verify()
        ''')
        g=lua.globals()
        self.assertIs(g._good,True)
        self.assertTrue(g._wp.endswith('123/4567'),g._wp)
        self.assertTrue(g._dep.endswith('x123'),g._dep)
        self.assertGreaterEqual(g._min_font,9.5)
        self.assertIs(g._no_measure,False)
        self.assertIs(g._restored,True)


if __name__=='__main__': unittest.main()
