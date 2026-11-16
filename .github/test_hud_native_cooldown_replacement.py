"""H5 native cooldown replacement: lease `grenades_radial` visible only while
the certified equipment RECHARGE row represents a source-known active grenade
cooldown; unknown/corrupt/off states restore the original visible."""
import unittest

from test_hud_final_integration import _crew_lua


def _runtime():
    lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
    assert crew_ok and equipment_ok
    lua.execute(r'''
        Idstring = Idstring or function(v) return v end
        kyohud.settings.enable_hud_foundation = true
        kyohud.settings.enable_player = false
        kyohud.settings.enable_weapons = false
        kyohud.settings.enable_equipment = true
        kyohud.settings.enable_crew = false
        kyohud.settings.hud_scale = 1.0
        panel_double:set_shape(0, 0, 1920, 1080)
        managers.player.current_state = function() return "standard" end
        managers.player:_native_set_grenades('pocket', 1, 2)
        _native_set_projectile_tweak('pocket', {ability = true, base_cooldown = 30})
        managers.player:_native_set_specials('cable_tie', {3})
        _game_clock:set_time(1000)
        managers.player:_native_set_replenish_timer(1017)

        local slot = HUDManager.PLAYER_PANEL
        local ep = panel_double:panel({name = "teammate_" .. slot})
        ep:set_shape(0, 0, 432, 120); ep:set_visible(true)
        local player = ep:panel({name = "player"})
        player:set_shape(0, 0, 432, 120); player:set_visible(true)
        local gren = player:panel({name = "grenades_panel"})
        gren:set_shape(150, 0, 48, 32); gren:set_visible(true)
        local bg = gren:bitmap({name = "bg"})
        bg:set_shape(0, 0, 48, 32); bg:set_visible(true); bg:set_alpha(.7)
        local icon = gren:bitmap({name = "grenades_icon"})
        icon:set_shape(0, 0, 32, 32); icon:set_visible(true); icon:set_alpha(.7)
        local amount = gren:text({name = "amount", text = "1"})
        amount:set_shape(0, 0, 48, 32); amount:set_visible(true); amount:set_alpha(.7)
        local radial = gren:bitmap({name = "grenades_radial"})
        radial:set_shape(0, 0, 32, 32); radial:set_visible(true); radial:set_alpha(.5)
        _G._gren, _G._bg, _G._icon, _G._amount = gren, bg, icon, amount
        _G._radial, _G._leaf = radial, radial
        managers.hud._teammate_panels = managers.hud._teammate_panels or {}
        managers.hud._teammate_panels[slot] = {
            _ai = false, _peer_id = 1, _panel = ep, _special_equipment = {},
        }
        _G._R, _G._m, _G._E = kyohud.hud.runtime, managers.hud, kyohud.hud.equipment
        _R:mount(_m); _R:refresh_settings(_m); _R:update(_m, 1.0, .1)
    ''')
    return lua


class NativeCooldownReplacementTests(unittest.TestCase):
    def test_active_cooldown_lease_unknown_timer_recovery_and_off(self):
        lua = _runtime()
        lua.execute(r'''
            _certified = _E:verify() and _E._visible_rows[5] == true
                and _E._rows[5]._root:visible() == true
                and _E._rows[5]._label:text() == "RECHARGE"
            _masked = _radial:visible() == false and _radial:alpha() == .5
            _intact = _radial:parent() == _gren and _gren:visible() == true
                and _bg:visible() and _icon:visible() and _amount:visible()
            local original = managers.player.get_timer_remaining
            managers.player.get_timer_remaining = function() return -1 end
            _R:update(_m, 1.6, .1)
            _unknown = _radial:visible() == true and _radial == _leaf
                and _radial:alpha() == .5
            managers.player.get_timer_remaining = original
            _R:update(_m, 2.2, .1)
            _back = _radial:visible() == false and _radial == _leaf
            kyohud.settings.enable_equipment = false
            _R:refresh_settings(_m); _R:update(_m, 2.8, .1)
            _e_off = _radial:visible() == true and _radial:alpha() == .5
            kyohud.settings.enable_hud_foundation = false
            _R:refresh_settings(_m); _R:update(_m, 3.4, .1)
            _f_off = _radial:visible() == true and _radial:alpha() == .5
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._certified), "visible RECHARGE must gate the lease")
        self.assertTrue(bool(g._masked), "active cooldown must hide only grenades_radial")
        self.assertTrue(bool(g._intact), "alpha, parent and sibling leaves must be preserved")
        self.assertTrue(bool(g._unknown), "unknown timer must restore original visible")
        self.assertTrue(bool(g._back), "known cooldown must re-lease the same leaf")
        self.assertTrue(bool(g._e_off), "equipment off must restore original visible")
        self.assertTrue(bool(g._f_off), "foundation off must restore original visible")

    def test_corrupt_render_and_expired_cooldown_restore_visible(self):
        lua = _runtime()
        lua.execute(r'''
            _certified = _E:verify() and _E._visible_rows[5] == true
            _masked = _radial:visible() == false
            local row = _E._rows[5]
            local original_set_text = row._label.set_text
            row._label:set_text("CORRUPT")
            row._label.set_text = function() end
            _R:update(_m, 1.6, .1)
            _corrupt = _radial:visible() == true and _radial == _leaf
            row._label.set_text = original_set_text
            _R:update(_m, 2.2, .1)
            _recovered = _radial:visible() == false and _radial == _leaf
            _game_clock:set_time(1020)
            _radial:set_color(Color(0, 0, 0))
            _R:update(_m, 2.8, .1)
            _expired = _radial:visible() == true and _radial:alpha() == .5
                and _radial == _leaf
            local c = _radial:color()
            _color_zero = c and c.r == 0 and c.g == 0 and c.b == 0
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._certified), "visible RECHARGE must gate the lease")
        self.assertTrue(bool(g._masked), "active cooldown must hide only grenades_radial")
        self.assertTrue(bool(g._corrupt), "corrupt/noop own render must restore visible")
        self.assertTrue(bool(g._recovered), "same leaf must be re-leased after repair")
        self.assertTrue(bool(g._expired), "expired cooldown must not add a new mask")
        self.assertTrue(bool(g._color_zero), "native radial color must stay untouched")


if __name__ == "__main__":
    unittest.main()
