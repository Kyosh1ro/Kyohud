"""Lot 4b: regression gates for the final local, additive consumer."""
from pathlib import Path
import unittest

from test_hud_weapons_integration import _lua_with_weapons_runtime, _ACTIVATE_BOILER
from test_hud_weapons_events import NATIVE_HUD_FIXTURE, DISPATCH

ROOT = Path(__file__).resolve().parents[1]


def activated():
    lua, _, _ = _lua_with_weapons_runtime()
    lua.execute(_ACTIVATE_BOILER + '''
        kyohud.settings.enable_weapons = true
        kyohud.hud.runtime:refresh_settings(managers.hud)
        W = kyohud.hud.weapons
        RT = kyohud.hud.runtime
    ''')
    return lua


class WeaponsFinalizationTests(unittest.TestCase):
    def test_weapons_stay_above_accepted_player_region_at_supported_scales(self):
        lua=activated()
        lua.execute('''
            disjoint=true
            for _, size in ipairs({{1920,1080},{3440,1440},{1280,1024}}) do
                for _, scale in ipairs({0.95,1,1.05}) do
                    kyohud.settings.hud_scale=scale
                    W._parent:set_shape(0,0,size[1],size[2])
                    W:refresh_settings(managers.hud)
                    local p=kyohud.hud.player:_compute_layout(size[1],size[2])
                    if not p or W._root:y()+W._root:h()>p.y then disjoint=false end
                end
            end
        ''')
        self.assertTrue(lua.globals().disjoint)

    def test_partial_mount_recovery_is_bounded_and_keeps_native_sibling(self):
        lua = activated()
        lua.execute('''
            W:unmount()
            local parent=RT._root_panel
            local sibling=parent:panel({name="third_party"})
            local factory=kyohud.hud.weapon_component.new
            local attempts=0
            kyohud.hud.weapon_component.new=function() attempts=attempts+1; return nil end
            W:update(managers.hud,0,0.06)
            local first=attempts
            for n=1,10 do W:update(managers.hud,n*0.01,0.01) end
            bounded=attempts==first and first==1
            kyohud.hud.weapon_component.new=factory
            W:update(managers.hud,0.6,0.5)
            recovered=W._root~=nil and W:verify()
            sibling_safe=alive(sibling) and parent:child("third_party")==sibling
        ''')
        self.assertTrue(lua.globals().bounded)
        self.assertTrue(lua.globals().recovered)
        self.assertTrue(lua.globals().sibling_safe)

    def test_stable_update_does_not_create_or_relayout_primitives(self):
        lua = activated()
        lua.execute('''
            local card=W._cards[1]
            local root=card._root
            local shape=root.set_shape
            calls=0
            root.set_shape=function(self,...) calls=calls+1; return shape(self,...) end
            local source=base1._ammo_info
            for n=1,12 do
                source.current_clip=6-(n%3)
                W:refresh(managers.hud)
                W:update(managers.hud,n,0.06)
            end
            same=root==W._cards[1]._root
        ''')
        self.assertTrue(lua.globals().same)
        self.assertEqual(lua.globals().calls, 0)

    def test_long_utf8_name_fits_and_noop_font_setter_fails_closed(self):
        lua = activated()
        lua.execute('''
            local card=W._cards[1]
            local p=card._name_text
            p.text_rect=function(self)
                return 0,0,#self:text()*self:font_size()*0.6,self:font_size()
            end
            local source=string.rep("Équipement ",40)
            card:render({current_clip=6,reserve=26,fire_mode="single"},false,
                {name=source,single="SEMI"})
            fitted=p:text()
            local _,_,tw=p:text_rect()
            fits=tw<=p:w()+0.5
            certified=card:verify()
            local old=p.set_font_size
            p:set_font_size(99)
            p.set_font_size=function() end
            card:render({current_clip=6,reserve=26,fire_mode="single"},false,
                {name=source,single="SEMI"})
            rejected=not card:verify()
            p.set_font_size=old
        ''')
        self.assertTrue(lua.globals().fits)
        self.assertTrue(lua.globals().certified)
        self.assertTrue(lua.globals().rejected)
        self.assertTrue(lua.globals().fitted.endswith('...'))

    def test_real_weapon_name_and_bounded_recovery_poll(self):
        lua = activated()
        lua.execute('''
            managers.localization = {text=function(self, key)
                if key == "test_weapon_name" then return "SHOTGUN" end
                return key
            end}
            base1._tweak = {name_id="test_weapon_name"}
            W:refresh_settings(managers.hud)
            observed_name = W._cards[1]._name_text:text()
            local original = base1.ammo_info
            polls = 0
            base1.ammo_info = function(self) polls=polls+1; return original(self) end
            RT:update(managers.hud, 1, 0.06)
            first_polls = polls
            RT:update(managers.hud, 1.06, 0.06)
            second_polls = polls
            RT:update(managers.hud, 1.6, 0.54)
            third_polls = polls
        ''')
        g = lua.globals()
        self.assertEqual(g.observed_name, "SHOTGUN")
        self.assertEqual(g.second_polls, g.first_polls)
        self.assertGreater(g.third_polls, g.second_polls)

    def test_ammo_event_updates_before_next_recovery_poll(self):
        lua = activated()
        lua.execute(NATIVE_HUD_FIXTURE)
        lua.execute('RequiredScript="lib/managers/hudmanagerpd2"')
        lua.execute((ROOT / 'lua/hud/weapons.lua').read_text(encoding='utf-8-sig'))
        lua.execute(DISPATCH)
        lua.execute('''
            RT:update(managers.hud, 1, 0.06)
            local card = W._cards[1]._ammo_text
            base1:_native_set_ammo(8, 2, 28, 40)
            _KY_dispatch(HUDManager, "set_teammate_ammo_amount", managers.hud, 4, 1, 8, 2, 28, 40)
            RT:update(managers.hud, 1.06, 0.06)
            result = card:text()
            same = card == W._cards[1]._ammo_text
        ''')
        self.assertEqual(lua.globals().result, '2 / 26')
        self.assertTrue(lua.globals().same)

    def test_root_and_font_corruption_repaired_without_recreation(self):
        lua = activated()
        lua.execute('''
            local root, prim = W._root, W._cards[1]._ammo_text
            local x,y,w,h = root:x(),root:y(),root:w(),root:h()
            root:set_shape(x+40,y,w,h)
            prim:set_font_size(99)
            bad = W:verify()
            RT:update(managers.hud, 1, 0.06)
            fixed = W:verify()
            same = root==W._root and prim==W._cards[1]._ammo_text
        ''')
        self.assertFalse(lua.globals().bad)
        self.assertTrue(lua.globals().fixed)
        self.assertTrue(lua.globals().same)

    def test_failed_render_hides_owned_root_then_recovers(self):
        lua = activated()
        lua.execute('''
            local prim = W._cards[1]._ammo_text
            local setter = prim.set_text
            prim:set_text("broken")
            prim.set_text = function() end
            RT:update(managers.hud, 1, 0.06)
            failed = W:verify()
            visible_failed = W._root:visible()
            prim.set_text = setter
            RT:update(managers.hud, 1.1, 0.1)
            recovered = W:verify() and W._root:visible()
        ''')
        self.assertFalse(lua.globals().failed)
        self.assertFalse(lua.globals().visible_failed)
        self.assertTrue(lua.globals().recovered)

    def test_dead_required_primitive_not_read(self):
        lua = activated()
        lua.execute('''
            local p = W._cards[1]._ammo_text
            p._alive=false
            dead_reads=0
            p.x=function() dead_reads=dead_reads+1; error("dead Diesel") end
            valid = W:verify()
        ''')
        self.assertFalse(lua.globals().valid)
        self.assertEqual(lua.globals().dead_reads, 0)

    def test_missing_collision_lookup_refuses_creation(self):
        lua = activated()
        lua.execute('''
            local p = W._root
            local mt = getmetatable(p)
            local child = mt.__index.child
            mt.__index.child = nil
            local c = kyohud.hud.weapon_component.new(p,"unknown_collision")
            refused = c == nil
            mt.__index.child = child
        ''')
        self.assertTrue(lua.globals().refused)

    def test_rebuild_does_not_restore_old_source_snapshot(self):
        lua = activated()
        lua.execute('''
            local u,b = make_weapon("replacement")
            b:_native_set_ammo(10,3,15,20)
            inventory:_native_set_slot(1,u)
            W:rebuild(managers.hud)
            snapshot_clip = W:get_snapshot().slots[1].current_clip
            rendered = W._cards[1]._ammo_text:text()
        ''')
        self.assertEqual(lua.globals().snapshot_clip, 3)
        self.assertEqual(lua.globals().rendered, '3 / 12')

    def test_small_budget_fails_closed_and_recovers(self):
        lua = activated()
        lua.execute('''
            local parent=W._parent
            local x,y,w,h=parent:x(),parent:y(),parent:w(),parent:h()
            parent:set_shape(0,0,40,20)
            W:update(managers.hud,1,0.06)
            small_visible=W._root:visible()
            parent:set_shape(x,y,w,h)
            W:update(managers.hud,1.1,0.1)
            recovered=W:verify() and W._root:visible()
        ''')
        self.assertFalse(lua.globals().small_visible)
        self.assertTrue(lua.globals().recovered)


if __name__ == '__main__':
    unittest.main()
