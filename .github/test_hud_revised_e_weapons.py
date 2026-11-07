"""Slice B -- fixed PRIMARY LEFT / SECONDARY RIGHT, BIG/SMALL exchange, no labels.

Approved B contract:
- native _cards[2]=PRIMARY LEFT; native _cards[1]=SECONDARY RIGHT
- selection change swaps BIG/SMALL, never reorders physical cards
- no PRIMARY/SECONDARY or weapon-name labels displayed
- BIG (active): clip/reserve 60e/22e inline row, mode badge visible
- SMALL (inactive): clip/reserve 24e/15e column, clip ABOVE reserve, mode+mode_bg hidden
- actual ammo values, collector, maxima caches, modes/ALT, zero/unknown unchanged
- backgrounds deferred to slice A

RED until implementation updated in weapons.lua _apply/_render and
components/weapon.lua render/_compact_shapes/_verify_compact.
"""
import unittest
from test_hud_final_integration import _crew_lua

SETUP = r'''
kyohud.settings.enable_hud_foundation=true
kyohud.settings.enable_player=true
kyohud.settings.enable_weapons=true
kyohud.settings.enable_equipment=true
kyohud.settings.enable_crew=false
kyohud.settings.hud_scale=1.0
_G.panel_double:set_shape(0,0,1920,1080)
managers.player.current_state=function() return 'standard' end
u1,b1=make_weapon('new_m1014');b1:_native_set_ammo(8,6,32,40);b1:_native_set_fire_mode('auto')
u2,b2=make_weapon('new_m16');b2:_native_set_ammo(30,25,120,150);b2:_native_set_fire_mode('single')
inventory:_native_set_slot(1,u1);inventory:_native_set_slot(2,u2)
inventory:_native_set_equipped(2)
managers.player:_native_set_equipment('doctor_bag',{2})
managers.player._equipment.selected_index=1
managers.player:_native_set_grenades('frag',2,2)
_native_set_projectile_tweak('frag',{throwable=true})
managers.player:_native_set_specials('cable_tie',{3})
RT=kyohud.hud.runtime;W=kyohud.hud.weapons;E=kyohud.hud.equipment
RT:refresh_settings(managers.hud)
RT:update(managers.hud,1,.06)
'''


def mounted():
    lua, *present = _crew_lua()
    assert all(present)
    lua.execute(SETUP)
    return lua


class SliceBFixedOrderTests(unittest.TestCase):

    def test_fixed_primary_left_secondary_right_with_switch(self):
        lua = mounted()
        lua.execute(r'''
            assert(W:verify() and E:verify(), 'RED: initial certify')
            local c1,c2=W._cards[2],W._cards[1]

            assert(c1._root:x()<c2._root:x(), 'RED: card1 LEFT of card2')

            assert(c1._clip_text:text()=='25', 'RED: card1 clip=25 (slot2)')
            assert(c1._reserve_text:text()=='95', 'RED: card1 reserve=95 (slot2)')
            assert(c2._clip_text:text()=='6', 'RED: card2 clip=6 (slot1)')
            assert(c2._reserve_text:text()=='26', 'RED: card2 reserve=26 (slot1)')

            assert(c1._mode_text:visible(), 'RED: BIG mode visible')
            assert(c1._mode_bg:visible(), 'RED: BIG mode_bg visible')
            assert(not c2._mode_text:visible(), 'RED: SMALL mode hidden')
            assert(not c2._mode_bg:visible(), 'RED: SMALL mode_bg hidden')

            assert(not c1._name_text:visible(), 'RED: card1 label hidden')
            assert(not c2._name_text:visible(), 'RED: card2 label hidden')

            assert(math.abs(c1._clip_text:font_size()-60)<.05, 'RED: BIG clip 60')
            assert(math.abs(c1._reserve_text:font_size()-22)<.05, 'RED: BIG reserve 22')
            assert(math.abs(c2._clip_text:font_size()-24)<.05, 'RED: SMALL clip 24')
            assert(math.abs(c2._reserve_text:font_size()-15)<.05, 'RED: SMALL reserve 15')

            assert(c2._clip_text:y()<c2._reserve_text:y(),
                'RED: SMALL clip above reserve')
            assert(c1._clip_text:x()+c1._clip_text:w()<=c1._reserve_text:x()+.5,
                'RED: BIG inline no overlap')

            local c1r,c2r=c1._root,c2._root
            local er=E._root
            local wrx,wry=W._root:x(),W._root:y()
            local erx,ery=E._root:x(),E._root:y()

            inventory:_native_set_equipped(1);W:refresh(managers.hud)
            RT:update(managers.hud,1.1,.06)
            assert(W:verify() and E:verify(), 'RED: certify after switch')

            assert(c1._root:x()<c2._root:x(), 'RED: order preserved selected=1')

            assert(c1._root==c1r and c2._root==c2r, 'RED: card roots stable')
            assert(E._root==er, 'RED: equipment root stable')
            assert(math.abs(W._root:x()-wrx)<.5 and math.abs(W._root:y()-wry)<.5,
                'RED: weapons root bounds stable')
            assert(math.abs(E._root:x()-erx)<.5 and math.abs(E._root:y()-ery)<.5,
                'RED: equipment root bounds stable')

            assert(not c1._mode_text:visible(), 'RED: card1 now SMALL mode hidden')
            assert(c2._mode_text:visible(), 'RED: card2 now BIG mode visible')
            assert(math.abs(c1._clip_text:font_size()-24)<.05,
                'RED: card1 SMALL clip 24')
            assert(math.abs(c2._clip_text:font_size()-60)<.05,
                'RED: card2 BIG clip 60')

            assert(c1._clip_text:text()=='25' and c1._reserve_text:text()=='95',
                'RED: card1 data stable')
            assert(c2._clip_text:text()=='6' and c2._reserve_text:text()=='26',
                'RED: card2 data stable')

            for i=1,6 do
                local sel=i%2==0 and 2 or 1
                inventory:_native_set_equipped(sel);W:refresh(managers.hud)
                RT:update(managers.hud,1.2+i*.1,.06)
                assert(W:verify() and E:verify())
                assert(c1._root:x()<c2._root:x(), 'RED: order stable loop')
                assert(c1._root==c1r and c2._root==c2r,
                    'RED: identities stable loop')
            end
        ''')

    def test_corruption_clip_text_rejected_then_repaired(self):
        lua = mounted()
        lua.execute(r'''
            local c1=W._cards[2]
            local clip=c1._clip_text
            assert(W:verify(), 'RED: initial certify')

            clip:set_shape(clip:x()+50,clip:y()+50,clip:w(),clip:h())
            assert(not W:verify(), 'RED: clip corruption rejected')

            RT:update(managers.hud,2.0,.06)
            assert(W:verify(), 'RED: runtime 2.0 repaired')
            assert(c1._clip_text==clip, 'RED: same clip primitive')
        ''')

    def test_corruption_mode_bg_rejected_then_repaired(self):
        lua = mounted()
        lua.execute(r'''
            local c1=W._cards[2]
            local mbg=c1._mode_bg
            assert(W:verify(), 'RED: initial certify')

            mbg:set_shape(mbg:x()+30,mbg:y()+30,mbg:w(),mbg:h())
            assert(not W:verify(), 'RED: mode_bg corruption rejected')

            RT:update(managers.hud,2.1,.06)
            assert(W:verify(), 'RED: runtime 2.1 repaired')
            assert(c1._mode_bg==mbg, 'RED: same mode_bg primitive')
        ''')

    def test_zero_ammo_shows_zero(self):
        lua = mounted()
        lua.execute(r'''
            b1:_native_set_ammo(8,0,0,40)
            W:refresh(managers.hud)
            RT:update(managers.hud,2.0,.06)
            assert(W:verify(), 'RED: certify after zero')
            local c2=W._cards[1]
            assert(c2._clip_text:text()=='0', 'RED: zero clip shows "0"')
            assert(c2._reserve_text:text()=='0', 'RED: zero reserve shows "0"')
        ''')


if __name__ == '__main__':
    unittest.main()
