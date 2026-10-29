"""Crew fail-closed readback, lifecycle and placement regressions."""
import unittest
from test_hud_crew import _lua


def mounted():
    lua, ok = _lua()
    assert ok
    lua.execute('''
        panel_double:set_shape(0,0,1920,1080)
        kyohud.settings.enable_hud_foundation=true
        kyohud.settings.enable_crew=true
        RT=kyohud.hud.runtime; C=kyohud.hud.crew; A=kyohud.hud.actors
        RT:mount(managers.hud); RT:update(managers.hud,1,.05)
        assert(C:_verify_render(), 'positive precondition')
    ''')
    return lua


class CrewReadbackTests(unittest.TestCase):
    def test_partial_creation_and_dead_card_recover_on_bounded_poll(self):
        lua, ok=_lua()
        self.assertTrue(ok)
        lua.execute('''
            panel_double:set_shape(0,0,1920,1080)
            kyohud.settings.enable_hud_foundation=true; kyohud.settings.enable_crew=true
            local cc=kyohud.hud.crew_card
            local new=cc.new
            cc.new=function() return nil end
            RT=kyohud.hud.runtime; C=kyohud.hud.crew
            RT:mount(managers.hud)
            RT:update(managers.hud,1,.05)
            _initial_hidden=not C._root:visible()
            cc.new=new
            RT:update(managers.hud,1.6,.05)
            _creation_recovered=C:_verify_render()
            if C._cards[1] then
                local card=C._cards[1]
                card._health_text._alive=false
                RT:update(managers.hud,2.2,.05)
                _dead_recovered=C:_verify_render() and C._cards[1]~=card
            end
        ''')
        self.assertIs(lua.globals()._initial_hidden,True)
        self.assertIs(lua.globals()._creation_recovered,True)
        self.assertIs(lua.globals()._dead_recovered,True)

    def test_throwing_and_noop_shape_fail_closed_then_repair_same_primitives(self):
        lua=mounted()
        lua.execute('''
            local card=C._cards[1]
            local root=card.root
            local setter=root.set_shape
            root:set_shape(-9,-9,1,1)
            root.set_shape=function() error('unavailable setter') end
            _safe_throw=pcall(function() RT:update(managers.hud,1.1,.05) end)
            _throw_cert=C:_verify_render()
            root.set_shape=function() end
            RT:update(managers.hud,1.2,.05)
            _noop_cert=C:_verify_render()
            root.set_shape=setter
            RT:update(managers.hud,1.3,.05)
            _recover=C:_verify_render() and C._cards[1].root==root
        ''')
        self.assertIs(lua.globals()._safe_throw,True)
        self.assertIs(lua.globals()._throw_cert,False)
        self.assertIs(lua.globals()._noop_cert,False)
        self.assertIs(lua.globals()._recover,True)

    def test_root_geometry_alpha_and_missing_expected_card_fail_closed(self):
        lua = mounted()
        lua.execute('''
            root=C._root; card=C._cards[1]; name=card._name_text
            root:set_shape(99,99,1,1)
            _bad_root=C:_verify_render()
            RT:update(managers.hud,1.1,.05)
            _repaired=C:_verify_render() and C._root==root and card._name_text==name
            root:set_alpha(.2)
            _bad_alpha=C:_verify_render()
            RT:update(managers.hud,1.2,.05)
            _alpha_repaired=C:_verify_render() and root:alpha()==1
            card.root:set_visible(false)
            _missing=C:_verify_render()
            RT:update(managers.hud,1.3,.05)
            _card_repaired=C:_verify_render() and card.root:visible()
            -- Font identity is constructor-only; verify supported size readback.
            card._health_text:set_font_size(99)
            _bad_font=C:_verify_render()
            RT:update(managers.hud,1.4,.05)
            _font_repaired=C:_verify_render()
        ''')
        for key in ('_bad_root','_bad_alpha','_missing','_bad_font'):
            self.assertIs(lua.globals()[key],False,key)
        for key in ('_repaired','_alpha_repaired','_card_repaired','_font_repaired'):
            self.assertIs(lua.globals()[key],True,key)

    def test_dead_subtree_destroy_attempts_no_dead_methods(self):
        lua = mounted()
        lua.execute('''
            local mt=getmetatable(panel_double).__index
            local function kill_tree(p)
                for _,child in pairs(p:children()) do kill_tree(child) end
                p._alive=false
            end
            kill_tree(C._root)
            _dead_calls=0
            for key, fn in pairs(mt) do
                if type(fn)=='function' then
                    mt[key]=function(self,...)
                        if self._alive==false then _dead_calls=_dead_calls+1 end
                        return fn(self,...)
                    end
                end
            end
            C:destroy(managers.hud); C:destroy(managers.hud)
        ''')
        self.assertEqual(lua.globals()._dead_calls,0)

    def test_roster_departure_hides_hole_and_arrival_reuses_same_card(self):
        lua = mounted()
        lua.execute('''
            local characters=managers.criminals:characters()
            local old=C._cards[1].root
            local oldpos=A:get_crew_snapshot()[1].position
            for _,rec in ipairs(characters) do
                if rec.data.panel_id==1 then rec.taken=false end
            end
            RT:update(managers.hud,1.6,.05)
            _hidden=not C._cards[oldpos].root:visible()
            _count=#A:get_crew_snapshot()
            for _,rec in ipairs(characters) do
                if rec.data.panel_id==1 then rec.taken=true end
            end
            RT:update(managers.hud,2.2,.05)
            _reused=C._cards[1].root==old and C:_verify_render()
        ''')
        self.assertIs(lua.globals()._hidden,True)
        self.assertEqual(lua.globals()._count,2)
        self.assertIs(lua.globals()._reused,True)

    def test_budget_against_equipment_and_observed_sibling(self):
        lua = mounted()
        lua.execute('''
            _layout_ok=true
            for _,size in ipairs({{1920,1080},{1680,1050},{1280,1024},{1198,673},{958,748},{2560,1080}}) do
                for _,s in ipairs({.95,1,1.05}) do
                    kyohud.settings.hud_scale=s
                    local l=C:_compute_layout(size[1],size[2])
                    local u=math.min(size[1]/1920,size[2]/1080)
                    local equipment_left=size[1]-.02*size[1]-(680*s+12)*u
                    if not l or l.x+l.total_w>equipment_left then _layout_ok=false end
                end
            end
            kyohud.settings.hud_scale=1
            local r=C._root
            -- A visible owned combat panel is a concrete conflict, not a speculative full-HUD scan.
            kyohud._panel=panel_double:panel({name='combat_sentinel'})
            kyohud._panel:set_shape(r:x(),r:y(),r:w(),r:h())
            kyohud._panel:set_visible(true)
            RT:update(managers.hud,1.7,.05)
            _conflict_hidden=not r:visible()
            _sentinel_intact=kyohud._panel:visible()
            kyohud._panel:set_visible(false)
            RT:update(managers.hud,2.3,.05)
            _recovered=C:_verify_render() and r:visible()
        ''')
        self.assertIs(lua.globals()._layout_ok,True)
        self.assertIs(lua.globals()._conflict_hidden,True)
        self.assertIs(lua.globals()._sentinel_intact,True)
        self.assertIs(lua.globals()._recovered,True)


if __name__=='__main__': unittest.main()
