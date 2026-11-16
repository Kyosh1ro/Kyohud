"""H5 grenade flash replacement: the two native ghost leaves are leased hidden
while row4 exposes an owned bitmap pulse with the source-observed alpha. The
existing integrated recharge and the native source/sibling geometry stay intact.
"""
import unittest

from test_hud_native_cooldown_replacement import _runtime


def _flash_lua():
    lua = _runtime()
    lua.execute(r'''
        tweak_data.hud_icons = {
            get_icon_data = function(self, id, default_rect)
                if id == 'frag_grenade' then
                    return 'guis/textures/pd2/equip_icons', {128, 0, 32, 32}
                end
                return id, default_rect or {0, 0, 48, 48}
            end,
        }
        DB = {has = function() return true end}
        Idstring = function(value) return value end
        _native_set_projectile_tweak('pocket', {
            ability = true, base_cooldown = 30, icon = 'frag_grenade'})
        _E._icon_cache = nil
        _R:refresh_settings(_m)

        local row = _E._rows[4]
        _G._row_icon_ok = row ~= nil and row._icon_descriptor ~= nil
            and row._icon ~= nil and row._icon:visible()
        local color = Color(.75, 1, 1, 1)
        _G._color_ok = color.a == .75 and color.r == 1
            and color.g == 1 and color.b == 1

        local function ghost(source, name)
            local g = _gren:bitmap({name = name})
            g:set_shape(source:x(), source:y(), source:w(), source:h())
            g:set_image(source:texture_name())
            g:set_color(Color(.75, 1, 1, 1))
            g:set_visible(true)
            return g
        end
        local radial_ghost = ghost(_radial, 'grenades_radial_ghost')
        local icon_ghost = ghost(_icon, 'grenades_icon_ghost')
        local pulse, scale = .25, 1.25
        local function pulse_shape(g, source)
            local w, h = source:w() * scale, source:h() * scale
            g:set_shape(source:x() + source:w() * .5 - w * .5,
                source:y() + source:h() * .5 - h * .5, w, h)
        end
        pulse_shape(radial_ghost, _radial)
        pulse_shape(icon_ghost, _icon)
        local sentinel = _gren:bitmap({name = 'native_flash_sentinel'})
        sentinel:set_shape(120, 0, 8, 8)
        sentinel:set_color(Color(1, 1, 1, 1))
        sentinel:set_visible(true)

        local function close(a, b) return math.abs(a - b) <= .05 end
        local radial_shape = {_radial:x(), _radial:y(), _radial:w(), _radial:h()}
        local icon_shape = {_icon:x(), _icon:y(), _icon:w(), _icon:h()}
        local radial_ghost_shape = {
            radial_ghost:x(), radial_ghost:y(), radial_ghost:w(), radial_ghost:h()}
        local icon_ghost_shape = {
            icon_ghost:x(), icon_ghost:y(), icon_ghost:w(), icon_ghost:h()}
        local function same_shape(shape, source)
            return close(shape[1], source:x()) and close(shape[2], source:y())
                and close(shape[3], source:w()) and close(shape[4], source:h())
        end
        local function centered(shape, source)
            return close(shape[1] + shape[3] * .5, source:x() + source:w() * .5)
                and close(shape[2] + shape[4] * .5, source:y() + source:h() * .5)
        end
        _G._pulse_geometry_ok = close(radial_ghost_shape[3], _radial:w() * scale)
            and close(radial_ghost_shape[4], _radial:h() * scale)
            and close(icon_ghost_shape[3], _icon:w() * scale)
            and close(icon_ghost_shape[4], _icon:h() * scale)
            and centered(radial_ghost_shape, _radial)
            and centered(icon_ghost_shape, _icon)
        _G._native_alpha_ok = radial_ghost:alpha() == .75
            and icon_ghost:alpha() == .75

        dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
            HUDManager.PLAYER_PANEL, {duration = 20, end_time = 1017})
        local charges_before = _E:get_snapshot().projectile.charges.raw
        local maximum_before = _E:get_snapshot().projectile.maximum.raw
        _R:update(_m, 1.06, .06)

        row = _E._rows[4]
        local flash = row and row._grenade_flash
        _G._missing_flash = flash == nil
        if not flash then return end

        local icon = row._icon
        local reveal = row._recharge_reveal
        local seconds = row._value:text()
        local reveal_shape = reveal and {reveal:x(), reveal:y(), reveal:w(), reveal:h()}
        local reveal_alpha = reveal and reveal:alpha() or 0
        local function shape_table(p)
            return p and {p:x(), p:y(), p:w(), p:h()} or nil
        end

        _G._flash_visible = flash:visible()
        _G._flash_alpha = flash:alpha()
        _G._flash_distinct = flash ~= icon and flash:parent() == row._root
        _G._flash_texture_matches = icon ~= nil
            and flash:texture_name() == icon:texture_name()
        local flash_rect = flash._texture_rect
        local icon_rect = icon and icon._texture_rect
        local crop_ok = type(flash_rect) == 'table' and type(icon_rect) == 'table'
            and #flash_rect == #icon_rect
        if crop_ok then
            for i = 1, #flash_rect do
                crop_ok = crop_ok and type(flash_rect[i]) == 'number'
                    and math.abs(flash_rect[i] - icon_rect[i]) <= .001
            end
        end
        _G._flash_crop_matches = crop_ok
        _G._flash_inside = flash:x() >= -.05 and flash:y() >= -.05
            and flash:x() + flash:w() <= row._root:w() + .05
            and flash:y() + flash:h() <= row._root:h() + .05
        _G._ghosts_leased = radial_ghost:visible() == false
            and icon_ghost:visible() == false
        _G._ghost_parents = radial_ghost:parent() == _gren
            and icon_ghost:parent() == _gren
        _G._sources_unchanged = same_shape(radial_shape, _radial)
            and same_shape(icon_shape, _icon)
        _G._siblings_unchanged = _gren:visible() and _bg:visible()
            and _amount:visible() and _icon:visible()
            and _amount:parent() == _gren and _bg:parent() == _gren
            and _icon:parent() == _gren
        _G._sentinel_unchanged = sentinel == _gren:child('native_flash_sentinel')
            and sentinel:parent() == _gren and sentinel:visible()
            and close(sentinel:x(), 120) and close(sentinel:y(), 0)
            and close(sentinel:w(), 8) and close(sentinel:h(), 8)
        _G._native_alpha_after = radial_ghost:alpha() == .75
            and icon_ghost:alpha() == .75
        _G._seconds = seconds
        _G._reveal_visible = reveal ~= nil and reveal:visible()
        _G._verified = _E:verify()
        _G._charges = _E:get_snapshot().projectile.charges.raw
        _G._maximum = _E:get_snapshot().projectile.maximum.raw
        _G._active_hidden = not _E._rows[6]._root:visible()

        flash:set_alpha(.2)
        _R:update(_m, 1.07, .01)

        _G._throttle_verify_false = _E:verify() == false
        _G._throttle_restored = radial_ghost:visible() == true
            and icon_ghost:visible() == true
        _G._throttle_native_alpha = radial_ghost:alpha() == .75
            and icon_ghost:alpha() == .75
        _G._throttle_parents = radial_ghost:parent() == _gren
            and icon_ghost:parent() == _gren
            and sentinel:parent() == _gren and sentinel:visible()
        _G._throttle_same = _E._rows[4]._grenade_flash == flash

        _R:update(_m, 1.13, .06)

        local repaired = _E._rows[4]._grenade_flash
        _G._repair_same = repaired == flash
        _G._repair_verify = _E:verify() == true
        _G._repair_flash_visible = repaired ~= nil and repaired:visible()
        _G._repair_flash_alpha = repaired ~= nil
            and math.abs(repaired:alpha() - .75) <= .005
        _G._repair_released = radial_ghost:visible() == false
            and icon_ghost:visible() == false
        _G._repair_seconds_same = row._value:text() == seconds
        _G._repair_reveal_same = row._recharge_reveal == reveal
            and type(reveal_shape) == 'table'
            and type(shape_table(row._recharge_reveal)) == 'table'
            and #reveal_shape == #shape_table(row._recharge_reveal)
            and close(reveal_shape[1], row._recharge_reveal:x())
            and close(reveal_shape[2], row._recharge_reveal:y())
            and close(reveal_shape[3], row._recharge_reveal:w())
            and close(reveal_shape[4], row._recharge_reveal:h())
            and reveal ~= nil and reveal:visible()
            and math.abs(reveal:alpha() - reveal_alpha) <= .005
        _G._repair_charges_same =
            _E:get_snapshot().projectile.charges.raw == charges_before
            and _E:get_snapshot().projectile.maximum.raw == maximum_before
        _G._repair_active_hidden = not _E._rows[6]._root:visible()
    ''')
    return lua


class GrenadeFlashReplacementTests(unittest.TestCase):
    def test_source_observed_row4_flash_lease_throttle_restore_and_repair(self):
        lua = _flash_lua()
        g = lua.globals()

        self.assertTrue(bool(g._color_ok),
            "fixture Color(a,r,g,b) must expose native-shaped alpha")
        self.assertTrue(bool(g._row_icon_ok),
            "row4 icon descriptor and visible icon must exist in the fixture")
        self.assertFalse(bool(g._missing_flash),
            "row4._grenade_flash must exist after an ordinary update")
        self.assertTrue(bool(g._pulse_geometry_ok),
            "native ghost pulse must scale 1.25 around the same center")
        self.assertTrue(bool(g._native_alpha_ok),
            "native ghost leaves must start with the native alpha .75")

        self.assertTrue(bool(g._flash_visible),
            "owned row4 flash must be visible during the source pulse")
        self.assertEqual(float(g._flash_alpha), .75,
            "owned row4 flash must use the source-observed alpha .75")
        self.assertTrue(bool(g._flash_distinct),
            "owned flash must be a distinct row4 primitive under the cell")
        self.assertTrue(bool(g._flash_texture_matches),
            "owned flash must use the equipped row icon texture")
        self.assertTrue(bool(g._flash_crop_matches),
            "owned flash must use the equipped row icon crop")
        self.assertTrue(bool(g._flash_inside),
            "owned flash must stay entirely inside the row4 cell")

        self.assertTrue(bool(g._ghosts_leased),
            "both native ghost leaves must be hidden by native_visibility")
        self.assertTrue(bool(g._ghost_parents),
            "native ghost parents must stay unchanged")
        self.assertTrue(bool(g._sources_unchanged),
            "native source geometry must stay unchanged")
        self.assertTrue(bool(g._siblings_unchanged),
            "native sibling leaves must stay visible and under the same parent")
        self.assertTrue(bool(g._sentinel_unchanged),
            "native sibling sentinel must stay visible with its geometry")
        self.assertTrue(bool(g._native_alpha_after),
            "native ghost alpha must stay untouched while leased")

        self.assertEqual(g._seconds, "17s",
            "existing integrated seconds must remain unchanged")
        self.assertTrue(bool(g._reveal_visible),
            "existing orange recharge reveal must remain visible")
        self.assertTrue(bool(g._verified),
            "equipment must stay certified with the owned flash")
        self.assertEqual(float(g._charges), 1.0,
            "existing grenade counter must remain unchanged")
        self.assertEqual(float(g._maximum), 2.0,
            "multiple charges must still be able to recharge")
        self.assertTrue(bool(g._active_hidden),
            "ACTIVE row must remain independent and hidden")

        self.assertTrue(bool(g._throttle_verify_false),
            "corrupt owned flash alpha must fail the production verifier")
        self.assertTrue(bool(g._throttle_restored),
            "sub-throttle update must restore both native ghost leaves")
        self.assertTrue(bool(g._throttle_native_alpha),
            "restored native ghost leaves must keep their native alpha")
        self.assertTrue(bool(g._throttle_parents),
            "restoring native leaves must not reparent ghosts or sentinel")
        self.assertTrue(bool(g._throttle_same),
            "throttled verification must retain the same owned flash primitive")

        self.assertTrue(bool(g._repair_same),
            "ordinary update must repair the same retained flash primitive")
        self.assertTrue(bool(g._repair_verify),
            "equipment must certify again after flash repair")
        self.assertTrue(bool(g._repair_flash_visible),
            "repaired flash must be visible again")
        self.assertTrue(bool(g._repair_flash_alpha),
            "repaired flash must return to the source-observed alpha .75")
        self.assertTrue(bool(g._repair_released),
            "repaired flash must lease both native ghost leaves again")
        self.assertTrue(bool(g._repair_seconds_same),
            "flash repair must not change the existing seconds")
        self.assertTrue(bool(g._repair_reveal_same),
            "flash repair must not change the existing orange recharge")
        self.assertTrue(bool(g._repair_charges_same),
            "flash repair must not change existing charges or maximum")
        self.assertTrue(bool(g._repair_active_hidden),
            "flash repair must not expose or alter the ACTIVE row")


if __name__ == "__main__":
    unittest.main()
