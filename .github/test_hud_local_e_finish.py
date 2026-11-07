"""Finition E -- local behavioral RED for proposed weapons split/side-by-side
and equipment compact rows.

Tests assert proposed first-version behavior which does not yet exist in
production. Each test must fail with a meaningful RED message until
production implements the corresponding change.

Weapons (component + manager):
  1. _clip_text / _reserve_text as separate persistent primitives
  2. Dominant (selected) clip size > secondary (non-selected) clip size
  3. Exact zero / unknown / reserve values in split texts
  4. Side-by-side layout: selected LEFT, other RIGHT
  5. Swap stability: same card instances, unchanged root anchors

Equipment (component + module):
  6. Ordinary throwable: no temporal reserved content extent
  7. Both channels active independently, event captured source-first
  8. Both deployables preserved with opaque amount_text
  9. Row icon bitmap child exists (proposed bitmap primitive)

No production writes. No shell/Git. Reuses existing fixtures by import.
"""
from pathlib import Path
import unittest

from test_hud_weapons_integration import (
    _lua_with_weapons_runtime, _ACTIVATE_BOILER,
)
from test_hud_equipment import NATIVE_EQUIPMENT_FIXTURE
from test_hud_equipment_consumables import NATIVE_CONSUMABLES_FIXTURE
from test_hud_equipment_events import EVENTS

ROOT = Path(__file__).resolve().parents[1]
EQUIPMENT_COMPONENT = ROOT / "lua" / "hud" / "components" / "equipment.lua"
EQUIPMENT_MODULE = ROOT / "lua" / "hud" / "equipment.lua"


class WeaponSplitClipReserveTests(unittest.TestCase):

    def test_clip_and_reserve_are_separate_persistent_texts(self):
        lua, ok, playerok = _lua_with_weapons_runtime()
        self.assertTrue(ok, "weapon component must exist")
        lua.execute(_ACTIVATE_BOILER + '''
            local WEAP = kyohud.hud.weapons
            local RT = kyohud.hud.runtime
            kyohud.settings.enable_weapons = true
            RT:refresh_settings(managers.hud)
            local card = WEAP._cards[1]
            _has_clip = card._clip_text ~= nil
            _has_reserve = card._reserve_text ~= nil
            _clip_is_ammo = (card._clip_text == card._ammo_text)
            _reserve_is_ammo = (card._reserve_text == card._ammo_text)
            _clip_distinct = (card._clip_text ~= card._reserve_text)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._has_clip),
            "RED: weapon card must expose _clip_text persistent primitive")
        self.assertTrue(bool(g._has_reserve),
            "RED: weapon card must expose _reserve_text persistent primitive")
        # _ammo_text is retained as the internal compatibility alias for clip.
        self.assertTrue(bool(g._clip_is_ammo))
        self.assertFalse(bool(g._reserve_is_ammo),
            "RED: _reserve_text must NOT alias legacy combined _ammo_text")
        self.assertTrue(bool(g._clip_distinct),
            "RED: _clip_text and _reserve_text must be distinct primitives")

    def test_dominant_clip_larger_than_secondary(self):
        lua, ok, playerok = _lua_with_weapons_runtime()
        self.assertTrue(ok, "weapon component must exist")
        lua.execute(_ACTIVATE_BOILER + '''
            local WEAP = kyohud.hud.weapons
            local RT = kyohud.hud.runtime
            kyohud.settings.enable_weapons = true
            RT:refresh_settings(managers.hud)
            RT:update(managers.hud, 1.0, 0.06)
            local snap = WEAP._current_snapshot
            local sel = snap and snap.selected or 2
            local other = 3 - sel
            local dom = WEAP._cards[sel]
            local sub = WEAP._cards[other]
            _dom_clip = dom._clip_text and dom._clip_text:font_size() or 0
            _sub_clip = sub._clip_text and sub._clip_text:font_size() or 0
            _dom_res = dom._reserve_text and dom._reserve_text:font_size() or 0
            _sub_res = sub._reserve_text and sub._reserve_text:font_size() or 0
        ''')
        g = lua.globals()
        self.assertGreater(float(g._dom_clip), float(g._sub_clip),
            "RED: dominant _clip_text font size must exceed secondary")
        self.assertGreater(float(g._dom_res), float(g._sub_res),
            "RED: dominant _reserve_text font size must exceed secondary")

    def test_exact_zero_unknown_reserve_in_split_texts(self):
        lua, ok, playerok = _lua_with_weapons_runtime()
        self.assertTrue(ok, "weapon component must exist")
        lua.execute(_ACTIVATE_BOILER + '''
            local WEAP = kyohud.hud.weapons
            local RT = kyohud.hud.runtime
            kyohud.settings.enable_weapons = true
            RT:refresh_settings(managers.hud)
            local card = WEAP._cards[1]
            local T = {name="GUN",single="S",auto="A",burst="B",volley="V",alt="X"}
            local function safe_text(p) return p and p:text() or "__MISSING__" end

            local s1 = {current_clip=0, reserve=26, fire_mode="single"}
            card:render(s1, true, T)
            _z_clip = safe_text(card._clip_text)
            _z_res = safe_text(card._reserve_text)

            local s2 = {current_clip=6, reserve=nil, fire_mode="single"}
            card:render(s2, true, T)
            _nr_clip = safe_text(card._clip_text)
            _nr_res = safe_text(card._reserve_text)

            local s3 = {current_clip=nil, reserve=26, fire_mode="single"}
            card:render(s3, true, T)
            _nc_clip = safe_text(card._clip_text)
            _nc_res = safe_text(card._reserve_text)
        ''')
        g = lua.globals()
        self.assertNotEqual(g._z_clip, "__MISSING__",
            "RED: _clip_text primitive must exist before value assertions")
        self.assertNotEqual(g._z_res, "__MISSING__",
            "RED: _reserve_text primitive must exist before value assertions")
        self.assertEqual(g._z_clip, "0",
            "RED: zero clip must render '0' in _clip_text, not '--'")
        self.assertEqual(g._z_res, "26",
            "RED: reserve 26 must render '26' in _reserve_text")
        self.assertEqual(g._nr_clip, "6",
            "RED: clip 6 must render '6' in _clip_text")
        self.assertEqual(g._nr_res, "--",
            "RED: nil reserve must render '--' in _reserve_text")
        self.assertEqual(g._nc_clip, "--",
            "RED: nil clip must render '--' in _clip_text")
        self.assertEqual(g._nc_res, "26",
            "RED: reserve 26 must render '26' in _reserve_text")


class WeaponSideBySideLayoutTests(unittest.TestCase):

    def test_selected_left_other_right(self):
        lua, ok, playerok = _lua_with_weapons_runtime()
        self.assertTrue(ok, "weapon component must exist")
        lua.execute(_ACTIVATE_BOILER + '''
            local WEAP = kyohud.hud.weapons
            local RT = kyohud.hud.runtime
            kyohud.settings.enable_weapons = true
            RT:refresh_settings(managers.hud)
            RT:update(managers.hud, 1.0, 0.06)
            local snap = WEAP._current_snapshot
            local sel = snap and snap.selected or 2
            local other = 3 - sel
            _sel_x = WEAP._cards[sel]._root:x()
            _oth_x = WEAP._cards[other]._root:x()
            _sel_left = _sel_x < _oth_x
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._sel_left),
            "RED: selected card x must be strictly left of non-selected card x")

    def test_swap_stability_same_instances_and_root_anchors(self):
        lua, ok, playerok = _lua_with_weapons_runtime()
        self.assertTrue(ok, "weapon component must exist")
        lua.execute(_ACTIVATE_BOILER + '''
            local WEAP = kyohud.hud.weapons
            local RT = kyohud.hud.runtime
            kyohud.settings.enable_weapons = true
            RT:refresh_settings(managers.hud)
            RT:update(managers.hud, 1.0, 0.06)
            local root = WEAP._root
            _rx0 = root:x(); _ry0 = root:y()
            _rw0 = root:w(); _rh0 = root:h()
            local c1 = WEAP._cards[1]
            local c2 = WEAP._cards[2]

            inventory:_native_set_equipped(1)
            WEAP:refresh(managers.hud)
            WEAP:_apply()
            WEAP:_render()

            _rx1 = root:x(); _ry1 = root:y()
            _rw1 = root:w(); _rh1 = root:h()
            _same1 = (WEAP._cards[1] == c1)
            _same2 = (WEAP._cards[2] == c2)
            _s1x = WEAP._cards[1]._root:x()
            _s2x = WEAP._cards[2]._root:x()
            _slot2_left = _s2x < _s1x
        ''')
        g = lua.globals()
        self.assertEqual(float(g._rx0), float(g._rx1), "RED: root x unchanged after swap")
        self.assertEqual(float(g._ry0), float(g._ry1), "RED: root y unchanged after swap")
        self.assertEqual(float(g._rw0), float(g._rw1), "RED: root w unchanged after swap")
        self.assertEqual(float(g._rh0), float(g._rh1), "RED: root h unchanged after swap")
        self.assertTrue(bool(g._same1), "RED: card[1] instance preserved after swap")
        self.assertTrue(bool(g._same2), "RED: card[2] instance preserved after swap")
        self.assertTrue(bool(g._slot2_left),
            "RED: after swap, slot 2 must be LEFT")


def _equipment_lua():
    lua, _, _ = _lua_with_weapons_runtime()
    lua.execute(_ACTIVATE_BOILER)
    lua.execute(NATIVE_EQUIPMENT_FIXTURE + NATIVE_CONSUMABLES_FIXTURE + EVENTS)
    lua.execute(r'''
        local P=getmetatable(panel_double)
        function P:set_image(texture,...)
            self._texture=texture; self._crop={...}
        end
        function P:texture_name() return self._texture end
        function P:set_texture_rect(...) self._crop={...} end
    ''')

    assert EQUIPMENT_COMPONENT.is_file(), "equipment component missing"
    lua.execute(EQUIPMENT_COMPONENT.read_text(encoding="utf-8-sig"))
    for context in ("lib/managers/playermanager", "lib/managers/hudmanagerpd2"):
        lua.globals().RequiredScript = context
        lua.execute(EQUIPMENT_MODULE.read_text(encoding="utf-8-sig"))
    lua.execute(r'''
        E = kyohud.hud.equipment; RT = kyohud.hud.runtime
        kyohud.settings.enable_equipment = true
        RT:refresh_settings(managers.hud)
    ''')
    return lua


class EquipmentCompactRowsTests(unittest.TestCase):

    def test_ordinary_no_temporal_reserved_content_extent(self):
        lua = _equipment_lua()
        lua.execute(r'''
            managers.player:_native_set_equipment('trip_mine', {3, 2})
            managers.player._equipment.selected_index = 1
            managers.player:_native_set_grenades('frag', 2, 2)
            _native_set_projectile_tweak('frag', {throwable=true, is_a_grenade=true})
            managers.player:_native_set_specials('cable_tie', {3})
            _game_clock:set_time(1000)
            E:refresh(managers.hud)
            E:_present()
            local s = E:get_snapshot()
            _cd_known = s.cooldown.known
            _cd_active = s.cooldown.active
            _act_known = s.activity.known
            _r5v = E._rows[5]._value:text()
            _r6v = E._rows[6]._value:text()
            _r5prog = E._rows[5]._root:visible() and E._rows[5]._fill:visible()
            _r6prog = E._rows[6]._root:visible() and E._rows[6]._fill:visible()
            _r5shown = E._rows[5]._root:visible()
            _r6shown = E._rows[6]._root:visible()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._cd_known),
            "RED: ordinary throwable cooldown must be known (checked, no timer)")
        self.assertFalse(bool(g._cd_active),
            "RED: ordinary throwable must have no active cooldown")
        self.assertFalse(bool(g._act_known),
            "RED: ordinary throwable must have unknown activity (no event)")
        self.assertFalse(bool(g._r5shown))
        self.assertFalse(bool(g._r6shown))
        self.assertFalse(bool(g._r5prog),
            "RED: ordinary throwable must reserve no RECHARGE progress extent")
        self.assertFalse(bool(g._r6prog),
            "RED: ordinary throwable must reserve no ACTIVE progress extent")

    def test_bothchannels_active_independently_event_captured_source_first(self):
        lua = _equipment_lua()
        lua.execute(r'''
            managers.player:_native_set_equipment('trip_mine', {3})
            managers.player._equipment.selected_index = 1
            managers.player:_native_set_grenades('frag', 1, 2)
            _native_set_projectile_tweak('frag', {ability=true, base_cooldown=30})
            managers.player:_native_set_specials('cable_tie', {3})
            _game_clock:set_time(1000)
            managers.player:_native_set_replenish_timer(1017)
            E:refresh(managers.hud)
            dispatch(HUDManager, 'activate_teammate_ability_radial',
                managers.hud, HUDManager.PLAYER_PANEL, 8, 10)
            E:refresh(managers.hud)
            E:_present()
            local s = E:get_snapshot()
            _cd_known = s.cooldown.known
            _cd_active = s.cooldown.active
            _cd_remaining = s.cooldown.remaining
            _act_known = s.activity.known
            _act_active = s.activity.active
            _act_remaining = s.activity.remaining
            _r5v = E._rows[5]._value:text()
            _r6v = E._rows[6]._value:text()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._cd_known),
            "RED: cooldown channel must be known from source timer")
        self.assertTrue(bool(g._cd_active),
            "RED: cooldown channel must be active independently")
        self.assertTrue(bool(g._act_known),
            "RED: activity channel must be known from event captured source-first")
        self.assertTrue(bool(g._act_active),
            "RED: activity channel must be active independently")
        self.assertNotEqual(g._r5v, "--",
            "RED: RECHARGE row must show active cooldown text")
        self.assertNotEqual(g._r6v, "--",
            "RED: ACTIVE row must show active activity text")

    def test_both_deployables_preserved_with_opaque_amount_text(self):
        lua = _equipment_lua()
        lua.execute(r'''
            managers.player:_native_set_equipment('trip_mine', {0/0, math.huge})
            managers.player:_native_set_equipment('doctor_bag', {1})
            managers.player._equipment.selected_index = 1
            managers.player:_native_set_grenades('frag', 2, 2)
            _native_set_projectile_tweak('frag', {throwable=true, is_a_grenade=true})
            managers.player:_native_set_specials('cable_tie', {3})
            E:refresh(managers.hud)
            dispatch(HUDManager,
                'set_teammate_deployable_equipment_amount_from_string',
                managers.hud, HUDManager.PLAYER_PANEL, 1,
                {amount_str='CUSTOM STOCK', amount={0/0, math.huge}})
            E:_present()
            _r1v = E._rows[1]._value:text()
            _r2vis = E._rows[2]._root:visible()
            _r2v = E._rows[2]._value:text()
            local snap = E:get_snapshot()
            _opaque = snap.deployables.trip_mine.amount_text
        ''')
        g = lua.globals()
        self.assertEqual(g._r1v, "CUSTOM STOCK",
            "RED: opaque amount_text must survive into rendered row 1")
        self.assertTrue(bool(g._r2vis),
            "RED: second deployable row must be visible when slot occupied")
        self.assertEqual(g._r2v, "1",
            "RED: second deployable must show its numeric quantity")
        self.assertEqual(g._opaque, "CUSTOM STOCK",
            "RED: snapshot amount_text preserved separately from quantities")

    def test_row_icon_bitmap_primitive_exists(self):
        lua = _equipment_lua()
        lua.execute(r'''
            DB = DB or {}
            function DB.has(idstring)
                return true
            end
            Idstring = Idstring or function(s)
                return {s = s, str = function(self) return self.s end}
            end
            tweak_data = tweak_data or {}
            tweak_data.hud_icons = tweak_data.hud_icons or {}
            tweak_data.equipments = tweak_data.equipments or {}
            tweak_data.equipments.ammo_bag = {icon="equipment_ammo_bag",text_id="eq_ammo"}
            tweak_data.blackmarket = tweak_data.blackmarket or {}
            tweak_data.blackmarket.projectiles = tweak_data.blackmarket.projectiles or {}
            tweak_data.blackmarket.projectiles.frag = {icon="frag_grenade"}
            function tweak_data.hud_icons:get_icon_data(id)
                return id, {0,0,48,48}
            end
            managers.player:_native_set_equipment('ammo_bag', {2})
            managers.player._equipment.selected_index = 1
            managers.player:_native_set_grenades('frag', 2, 2)
            _native_set_projectile_tweak('frag', {throwable=true, is_a_grenade=true})
            managers.player:_native_set_specials('cable_tie', {3})
            E:refresh(managers.hud)
            E:_present()
            local row = E._rows[1]
            _has_icon = row._icon ~= nil
            _verified = E:verify()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._has_icon),
            "RED: equipment row must have _icon bitmap primitive")
        self.assertTrue(bool(g._verified), "icon render must be certified, not just allocated")


class LocalERecoveryTests(unittest.TestCase):
    def test_weapon_style_reserve_and_separator_certification(self):
        lua, _, _ = _lua_with_weapons_runtime()
        lua.execute(_ACTIVATE_BOILER + r'''
            kyohud.settings.enable_weapons=true
            local R=kyohud.hud.runtime
            R:refresh_settings(managers.hud)
            local W=kyohud.hud.weapons
            local c=W._cards[2]
            assert(W:verify())
            assert(W._separator, 'owned vertical separator required')
            assert(c._mode_bg:visible() and c._mode_bg:alpha()>0,'RED: active mode bg visible')
            for _,p in ipairs({c._reserve_text,c._clip_text,c._mode_text,c._mode_bg}) do
                local color=p:color()
                local saved=Color(color.a,color.r,color.g,color.b)
                p:set_color(Color(.2,.3,.4))
                assert(not W:verify(),'RGB corruption must refuse')
                p:set_color(saved)
                assert(W:verify())
                p:set_alpha(.2)
                assert(not W:verify(),'alpha corruption must refuse')
                R:update(managers.hud,1,.06)
                assert(W:verify())
            end
            local p=c._reserve_text
            local setter=p.set_text
            p:set_text('bad');p.set_text=function() end
            R:update(managers.hud,1.1,.06)
            assert(not W._root:visible())
            p.set_text=setter
            R:update(managers.hud,1.2,.06)
            assert(W:verify() and W._cards[2]._reserve_text==p)
            local ic=W._cards[1]
            assert(ic~=c,'inactive card distinct from active')
            local ip=ic._reserve_text
            assert(ip,'inactive card has reserve_text')
            local icol=ip:color()
            local isaved=Color(icol.a,icol.r,icol.g,icol.b)
            ip:set_color(Color(.2,.3,.4))
            assert(not W:verify(),'inactive reserve RGB corruption must refuse')
            ip:set_color(isaved)
            assert(W:verify())
            ip:set_alpha(.2)
            assert(not W:verify(),'inactive reserve alpha corruption must refuse')
            R:update(managers.hud,1.3,.06)
            assert(W:verify() and ic._reserve_text==ip)
        ''')

    def test_icon_geometry_corruption_and_cached_resources(self):
        lua = _equipment_lua()
        lua.execute(r'''
            _probes=0
            Idstring=setmetatable({}, {__call=function(_,s) return {key=function() return s end} end})
            DB={has=function() _probes=_probes+1;return true end}
            tweak_data.equipments=tweak_data.equipments or {}
            tweak_data.equipments.ammo_bag={icon='e_test_ammo',text_id='eq_ammo'}
            tweak_data.hud_icons={get_icon_data=function(_,id) return id,{0,0,48,32} end}
            managers.player:_native_set_equipment('ammo_bag',{2})
            managers.player._equipment.selected_index=1
            E:refresh(managers.hud);E:_present()
            assert(E:verify())
            local p=E._rows[1]._icon
            assert(p and p:visible())
            local probes=_probes
            E:_present();assert(_probes==probes,'resource cache')
            p:set_shape(p:x()+10,p:y(),p:w(),p:h())
            assert(not E:verify(),'icon X corruption must refuse')
            E:_present()
            assert(E:verify() and E._rows[1]._icon==p)
            p._texture='wrong'
            assert(not E:verify(),'texture corruption must refuse')
            E:_present();assert(E:verify())
        ''')

    def test_workspace_scale_and_compact_content(self):
        for w, h in ((1920,1080),(3440,1440),(1280,1024)):
            for scale in (.95,1,1.05):
                with self.subTest(w=w,h=h,scale=scale):
                    lua = _equipment_lua()
                    lua.globals().target_w=w
                    lua.globals().target_h=h
                    lua.globals().target_scale=scale
                    lua.execute(r'''
                        managers.player._equipment.selections={}
                        managers.player:_native_set_equipment('doctor_bag',{1})
                        managers.player:_native_set_grenades('frag',2,2)
                        _native_set_projectile_tweak('frag',{throwable=true})
                        kyohud.settings.hud_scale=target_scale
                        RT._root_panel:set_shape(0,0,target_w,target_h)
                        E:refresh_settings(managers.hud)
                        assert(E:verify())
                        local rows={}
                        for _,row in ipairs(E._rows) do
                            if row._root:visible() then rows[#rows+1]=row._root end
                        end
                        assert(#rows==3,'one deployable+cables+grenade only')
                        for i=2,#rows do
                            assert(math.abs(rows[i]:y()-rows[i-1]:y())<.05)
                            assert(rows[i]:x()>=rows[i-1]:x()+rows[i-1]:w())
                        end
                    ''')
                    lua, _, _ = _lua_with_weapons_runtime()
                    lua.globals().target_w=w
                    lua.globals().target_h=h
                    lua.globals().target_scale=scale
                    lua.execute(_ACTIVATE_BOILER + r'''
                        local RT=kyohud.hud.runtime
                        RT._root_panel:set_shape(0,0,target_w,target_h)
                        kyohud.settings.hud_scale=target_scale
                        local W=kyohud.hud.weapons
                        kyohud.settings.enable_weapons=true
                        W:refresh_settings(managers.hud)
                        assert(W:verify())
                        assert(W._cards[2]._root:x()<W._cards[1]._root:x())
                        local e=math.min(target_w/1920,target_h/1080)*target_scale
                        assert(math.abs(W._root:w()-380*e)<.05)
                    ''')

if __name__ == "__main__":
    unittest.main()
