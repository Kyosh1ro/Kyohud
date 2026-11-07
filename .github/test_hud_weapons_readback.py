import unittest
from test_hud_weapons_integration import _lua_with_weapons_runtime, _ACTIVATE_BOILER

class TestHudWeaponsReadback(unittest.TestCase):
    def test_geometry_certification_and_repair(self):
        lua, _, _ = _lua_with_weapons_runtime()
        _immediate, _healthy, _bad, _repaired, _same, _x, _desired = lua.execute(_ACTIVATE_BOILER + """
            local W = kyohud.hud.weapons
            local RT = kyohud.hud.runtime
            kyohud.settings.enable_weapons = true
            RT:refresh_settings(managers.hud)
            local _immediate = W._cards[1]._clip_text:text() .. " / " .. W._cards[1]._reserve_text:text()
            RT:update(managers.hud, 1, 0.06)
            local _healthy = W:verify()
            local p = W._cards[1]._ammo_text
            p:set_shape(999, 999, 1, 1)
            local _bad = W:verify()
            RT:update(managers.hud, 1.1, 0.1)
            local _repaired = W:verify()
            local _same = (p == W._cards[1]._ammo_text)
            local _x = p:x()
            local card = W._cards[1]
            local _desired = (card._w - card._compact_clip_w) / 2
            return _immediate, _healthy, _bad, _repaired, _same, _x, _desired
        """)
        self.assertEqual(_immediate, "6 / 26")
        self.assertTrue(_healthy)
        self.assertFalse(_bad)
        self.assertTrue(_repaired)
        self.assertTrue(_same)
        self.assertAlmostEqual(_x, _desired, places=1)

if __name__ == "__main__":
    unittest.main()
