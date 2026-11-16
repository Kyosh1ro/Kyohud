"""Alpha-channel probes for the owned grenade flash.

The fixture seam overrides each leased native ghost's primitive ``alpha`` getter
with 1 while its Color alpha is changed independently. Desired production must
follow the native Color alpha for the pulse phase/terminal decision and for the
owned flash alpha, never the primitive getter. Current production reads the
primitive alpha, so both probes are expected to fail meaningfully.
"""
import unittest

from test_hud_grenade_flash_replacement import _flash_lua


class GrenadeFlashAlphaChannelTests(unittest.TestCase):
    def test_held_pulse_uses_native_color_alpha(self):
        lua = _flash_lua()
        lua.execute(r'''
            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            _G._flash_exists = flash ~= nil and flash:visible()

            local radial_ghost = _gren:child('grenades_radial_ghost')
            local icon_ghost = _gren:child('grenades_icon_ghost')
            _G._ghosts_exist = radial_ghost ~= nil and icon_ghost ~= nil

            if flash and radial_ghost and icon_ghost then
                local function retarget(g, base)
                    g:set_color(Color(.5, 1, 1, 1))
                    local w, h = base:w() * 1.5, base:h() * 1.5
                    g:set_shape(base:x() - .25 * base:w(),
                        base:y() - .25 * base:h(), w, h)
                    g.alpha = function() return 1 end
                end
                retarget(radial_ghost, _radial)
                retarget(icon_ghost, _icon)

                _G._native_getter_ok = radial_ghost:alpha() == 1
                    and icon_ghost:alpha() == 1
                _G._native_color_ok = radial_ghost:color().a == .5
                    and icon_ghost:color().a == .5
                _G._ghost_shape_ok =
                    math.abs(radial_ghost:w() - _radial:w() * 1.5) <= .05
                    and math.abs(icon_ghost:w() - _icon:w() * 1.5) <= .05

                _R:update(_m, 1.14, .01)

                local after = _E._rows[4] and _E._rows[4]._grenade_flash
                _G._flash_retained = after == flash
                _G._flash_visible = after ~= nil and after:visible()
                _G._flash_alpha = after and after:alpha() or -1
                _G._verify_ok = _E:_verify_grenade_flash() == true
                _G._natives_hidden = radial_ghost:visible() == false
                    and icon_ghost:visible() == false
            end
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._flash_exists),
            "fixture must expose the held owned pulse before the probe")
        self.assertTrue(bool(g._ghosts_exist),
            "fixture must expose both native ghost leaves")
        self.assertTrue(bool(g._native_getter_ok),
            "the seam must override the primitive alpha getter independently")
        self.assertTrue(bool(g._native_color_ok),
            "the seam must keep the native Color alpha at .5")
        self.assertTrue(bool(g._ghost_shape_ok),
            "the probe must scale native ghost shapes 1.5 around the base")
        self.assertTrue(bool(g._flash_retained),
            "the owned pulse must remain the same retained primitive")
        self.assertTrue(bool(g._flash_visible),
            "the owned pulse must stay visible while the pulse is held")
        self.assertAlmostEqual(float(g._flash_alpha), .5, places=3,
            msg="owned pulse must follow the native Color alpha .5, not the "
                "primitive alpha getter 1")
        self.assertTrue(bool(g._verify_ok),
            "the equipment verifier must still certify the owned pulse")
        self.assertTrue(bool(g._natives_hidden),
            "both native ghosts must stay leased hidden during the pulse")

    def test_terminal_pulse_uses_native_color_alpha(self):
        lua = _flash_lua()
        lua.execute(r'''
            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            _G._flash_exists = flash ~= nil and flash:visible()

            local radial_ghost = _gren:child('grenades_radial_ghost')
            local icon_ghost = _gren:child('grenades_icon_ghost')
            _G._ghosts_exist = radial_ghost ~= nil and icon_ghost ~= nil

            if flash and radial_ghost and icon_ghost then
                local function terminal(g, base)
                    g:set_color(Color(0, 1, 1, 1))
                    g:set_shape(base:x(), base:y(), base:w(), base:h())
                    g.alpha = function() return 1 end
                    g:set_visible(false)
                end
                terminal(radial_ghost, _radial)
                terminal(icon_ghost, _icon)

                _G._native_getter_ok = radial_ghost:alpha() == 1
                    and icon_ghost:alpha() == 1
                _G._native_color_ok = radial_ghost:color().a == 0
                    and icon_ghost:color().a == 0

                local p_grenade_flash = flash
                _R:update(_m, 1.20, .06)

                _G._owned_pulse_hidden = p_grenade_flash ~= nil
                    and p_grenade_flash:visible() == false
                _G._local_p_grenade_flash_absent = _R._h5_groups == nil
                    or _R._h5_groups["local_p_grenade_flash"] == nil
                _G._flash_same = flash == _E._rows[4]._grenade_flash
                _G._natives_hidden = radial_ghost:visible() == false
                    and icon_ghost:visible() == false
            end
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._flash_exists),
            "fixture must expose the held owned pulse before the probe")
        self.assertTrue(bool(g._ghosts_exist),
            "fixture must expose both native ghost leaves")
        self.assertTrue(bool(g._native_getter_ok),
            "the seam must override the primitive alpha getter independently")
        self.assertTrue(bool(g._native_color_ok),
            "the seam must keep the native Color alpha at 0")
        self.assertTrue(bool(g._owned_pulse_hidden),
            "a terminal native pulse must hide the retained owned pulse")
        self.assertTrue(bool(g._local_p_grenade_flash_absent),
            "a terminal native pulse must leave no remaining native visibility lease group")
        self.assertTrue(bool(g._flash_same),
            "a terminal native pulse must retain the same owned flash bitmap")
        self.assertTrue(bool(g._natives_hidden),
            "both native ghosts must stay hidden at the terminal state")


if __name__ == "__main__":
    unittest.main()
