"""Source-loss regression for both personal crew ammunition channels."""
import unittest
from test_hud_crew_online_ammo import SOURCE_SETUP, _fresh_lua


class CrewAmmoSourceLossTests(unittest.TestCase):
    def test_both_slots_yield_on_turret_unknown_or_missing_weapon(self):
        for transition in ("turret", "unknown", "missing"):
            with self.subTest(transition=transition):
                lua, _ = _fresh_lua(SOURCE_SETUP)
                lua.globals().transition = transition
                lua.execute(r'''
                    local ACT = kyohud.hud.actors
                    ACT:refresh_crew(managers.hud, 1)
                    managers.player:set_synced_ammo_info(2, 1, 30, 7, 67, 120)
                    managers.player:set_synced_ammo_info(2, 2, 40, 12, 95, 160)
                    local before = ACT:get_crew_snapshot()[1]
                    assert(before.ammo_slots[1] and before.ammo_slots[2], 'positive source')
                    local getter = managers.player.get_player_turret_for_peer
                    if transition == 'turret' then
                        managers.player._turret_for_peer = {_alive=true}
                        managers.hud:_set_teammate_weapon_selected(2, 1, 'gun_a')
                    elseif transition == 'unknown' then
                        managers.player.get_player_turret_for_peer = function() error('unreadable turret') end
                        managers.player:set_synced_ammo_info(2, 1, 30, 6, 66, 120)
                    else
                        _inventory._equipped_unit = nil
                        managers.hud:_set_teammate_weapon_selected(2, 1, 'gun_a')
                    end
                    local lost = ACT:get_crew_snapshot()[1]
                    _slots_cleared = not lost.ammo_slots
                        or (not lost.ammo_slots[1] and not lost.ammo_slots[2])
                    _active_cleared = not lost.weapon or not lost.weapon.ammo
                    managers.player.get_player_turret_for_peer = getter
                    managers.player._turret_for_peer = nil
                    _inventory._equipped_unit = _gunA
                    managers.hud:_set_teammate_weapon_selected(2, 1, 'gun_a')
                    managers.player:set_synced_ammo_info(2, 1, 30, 5, 65, 120)
                    managers.player:set_synced_ammo_info(2, 2, 40, 11, 94, 160)
                    local recovered = ACT:get_crew_snapshot()[1]
                    _recovered = recovered.occupant_token == before.occupant_token
                        and recovered.ammo_slots[1].current_clip == 5
                        and recovered.ammo_slots[2].current_clip == 11
                ''')
                self.assertIs(lua.globals()._slots_cleared, True)
                self.assertIs(lua.globals()._active_cleared, True)
                self.assertIs(lua.globals()._recovered, True)
