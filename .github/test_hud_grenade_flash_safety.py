"""Safety invariants for the owned H5 grenade flash.

Production verification must be read-only. The fixture bitmap follows the
Diesel API (setters plus texture_name/texture_width/texture_height) and has no
texture_rect getter, so this file does not fake an atlas crop readback; the
crop limitation is reported here instead of being tested through an invented
getter.
"""
import unittest

from test_hud_grenade_flash_replacement import _flash_lua


class GrenadeFlashSafetyTests(unittest.TestCase):
    def test_verification_is_read_only(self):
        lua = _flash_lua()
        g = lua.globals()

        lua.execute(r'''
            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            _G._readonly_missing = flash == nil
            if not flash then
                _G._readonly_wrapped = false
                _G._readonly_first = false
                _G._readonly_second = false
                _G._readonly_count = -1
                return
            end

            local count = 0
            local original = flash.set_image
            flash.set_image = function(self, ...)
                count = count + 1
                return original(self, ...)
            end

            _G._readonly_wrapped = true
            _G._readonly_first = _E:verify() == true
            _G._readonly_second = _E:verify() == true
            _G._readonly_count = count
        ''')

        self.assertFalse(bool(g._readonly_missing),
            "row4 owned flash must exist before read-only verification")
        self.assertTrue(bool(g._readonly_wrapped),
            "the test must wrap the owned flash set_image")
        self.assertTrue(bool(g._readonly_first),
            "first production verification must certify equipment")
        self.assertTrue(bool(g._readonly_second),
            "second production verification must certify equipment")
        self.assertEqual(int(g._readonly_count), 0,
            "production verification must not write the flash image; "
            "the current baseline writes the atlas crop on every verify")

    def test_equipment_off_restores_native_state(self):
        for state in ("midpulse", "terminal"):
            with self.subTest(state=state):
                lua = _flash_lua()
                g = lua.globals()
                g._off_state = state

                lua.execute(r'''
                    local state = _off_state
                    local row = _E._rows[4]
                    local flash = row and row._grenade_flash
                    local rg = _gren:child('grenades_radial_ghost')
                    local ig = _gren:child('grenades_icon_ghost')
                    local sentinel = _gren:child('native_flash_sentinel')

                    _G._off_fixture_ok = flash ~= nil and rg ~= nil
                        and ig ~= nil and sentinel ~= nil
                    if not _G._off_fixture_ok then return end

                    local function base_shape(panel)
                        return {panel:x(), panel:y(), panel:w(), panel:h()}
                    end
                    local radial_base = base_shape(_radial)
                    local icon_base = base_shape(_icon)

                    local function pulse(ghost, source, alpha, overhang)
                        ghost:set_color(Color(alpha, 1, 1, 1))
                        ghost:set_shape(
                            source:x() - source:w() * overhang,
                            source:y() - source:h() * overhang,
                            source:w() * (1 + overhang * 2),
                            source:h() * (1 + overhang * 2))
                    end

                    local function terminal(ghost, base)
                        ghost:set_color(Color(0, 1, 1, 1))
                        ghost:set_shape(base[1], base[2], base[3], base[4])
                        ghost:set_visible(false)
                    end

                    if state == 'midpulse' then
                        pulse(rg, _radial, .5, .25)
                        pulse(ig, _icon, .5, .25)
                        rg:set_visible(true)
                        ig:set_visible(true)
                    else
                        terminal(rg, radial_base)
                        terminal(ig, icon_base)
                    end

                    kyohud.settings.enable_equipment = false
                    _R:refresh_settings(_m)

                    local expected_visible = state == 'midpulse'
                    _G._off_native_visible = rg:visible() == expected_visible
                        and ig:visible() == expected_visible
                    _G._off_parents = rg:parent() == _gren
                        and ig:parent() == _gren
                    _G._off_sentinel = sentinel == _gren:child('native_flash_sentinel')
                        and sentinel:parent() == _gren and sentinel:visible()

                    terminal(rg, radial_base)
                    terminal(ig, icon_base)

                    kyohud.settings.enable_equipment = true
                    _R:refresh_settings(_m)
                    _R:update(_m, 1.15, .01)

                    local current = _E._rows[4]
                        and _E._rows[4]._grenade_flash
                    _G._off_no_fake_flash = current == nil
                        or current:visible() == false
                    _G._off_final_native_hidden = rg:visible() == false
                        and ig:visible() == false
                ''')

                self.assertTrue(bool(g._off_fixture_ok),
                    "fixture must expose flash, both ghosts and the sentinel")
                self.assertTrue(bool(g._off_native_visible),
                    "disabling equipment must restore midpulse ghosts visible "
                    "and keep terminal ghosts hidden")
                self.assertTrue(bool(g._off_parents),
                    "releasing native ghosts must not reparent them")
                self.assertTrue(bool(g._off_sentinel),
                    "the native sentinel must stay visible under the same parent")
                self.assertTrue(bool(g._off_no_fake_flash),
                    "a terminal native flash must not invent an owned flash")
                self.assertTrue(bool(g._off_final_native_hidden),
                    "terminal native ghosts must stay hidden after re-enable")

        lua = _flash_lua()
        g = lua.globals()
        lua.execute(r'''
            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            local rg = _gren:child('grenades_radial_ghost')
            local ig = _gren:child('grenades_icon_ghost')
            _G._count_fixture_ok = flash ~= nil and rg ~= nil
                and ig ~= nil
            if not _G._count_fixture_ok then
                _G._count_before = -1
                _G._count_after = -1
                _G._count_no_notification = false
                return
            end

            local function base_shape(panel)
                return {panel:x(), panel:y(), panel:w(), panel:h()}
            end
            local function terminal(ghost, base)
                ghost:set_color(Color(0, 1, 1, 1))
                ghost:set_shape(base[1], base[2], base[3], base[4])
                ghost:set_visible(false)
            end
            terminal(rg, base_shape(_radial))
            terminal(ig, base_shape(_icon))

            managers.player:_native_clear_replenish_timer()

            _G._count_before = _E:get_snapshot().projectile.charges.raw
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 0, end_time = 0})
            _E:refresh(_m)
            _R:update(_m, 1.20, .06)
            _G._count_after = _E:get_snapshot().projectile.charges.raw
            local current = _E._rows[4] and _E._rows[4]._grenade_flash
            _G._count_no_notification = current == nil
                or current:visible() == false
        ''')

        self.assertTrue(bool(g._count_fixture_ok),
            "count case needs the owned flash and both native ghosts")
        self.assertEqual(float(g._count_before), 1.0,
            "fixture must start with one known grenade")
        self.assertEqual(float(g._count_after), 1.0,
            "a cleared native replenish timer and fresh refresh must retain "
            "the known count of one")
        self.assertTrue(bool(g._count_no_notification),
            "a cleared native timer must not invent a flash notification")

    def test_matrix_source_registry_and_owned_corruption(self):
        for case in ("rgb", "alpha", "geometry", "visibility", "layer", "texture"):
            with self.subTest(case=case):
                lua = _flash_lua()
                g = lua.globals()
                g._matrix_case = case

                lua.execute(r'''
                    local case = _matrix_case
                    local row = _E._rows[4]
                    local flash = row and row._grenade_flash
                    _G._matrix_fixture_ok = flash ~= nil and _icon ~= nil
                        and _bg ~= nil
                    _G._matrix_missing = flash == nil
                    if not flash then
                        _G._matrix_corrupt_verify = false
                        _G._matrix_throttle_native = false
                        _G._matrix_throttle_verify = true
                        _G._matrix_repair_same = false
                        _G._matrix_repair_native_hidden = false
                        _G._matrix_repair_verify = false
                        _G._matrix_repair_visible = false
                        return
                    end

                    local probe_texture = _bg:texture_name()
                    if probe_texture == flash:texture_name() then
                        probe_texture = 'guis/textures/pd2/kyohud_matrix_probe'
                    end

                    if case == 'rgb' then
                        flash:set_color(Color(flash:alpha(), 0, 1, 0))
                    elseif case == 'alpha' then
                        flash:set_alpha(0)
                    elseif case == 'geometry' then
                        flash:set_shape(
                            flash:x() + 4, flash:y() + 3,
                            flash:w(), flash:h())
                    elseif case == 'visibility' then
                        flash:set_visible(false)
                    elseif case == 'layer' then
                        if type(flash.set_layer) == 'function' then
                            local layer = 0
                            if type(flash.layer) == 'function' then
                                layer = flash:layer()
                            end
                            flash:set_layer(layer + 7)
                        end
                    elseif case == 'texture' then
                        flash:set_image(probe_texture)
                    end

                    _G._matrix_corrupt_verify = _E:verify() == false

                    _R:update(_m, 1.14, .01)
                    local rg = _gren:child('grenades_radial_ghost')
                    local ig = _gren:child('grenades_icon_ghost')
                    _G._matrix_throttle_native = rg ~= nil and ig ~= nil
                        and rg:visible() == true and ig:visible() == true
                    _G._matrix_throttle_verify = _E:verify() == false

                    _R:update(_m, 1.20, .06)
                    local repaired = _E._rows[4]
                        and _E._rows[4]._grenade_flash
                    _G._matrix_repair_same = repaired == flash
                    _G._matrix_repair_native_hidden = rg ~= nil and ig ~= nil
                        and rg:visible() == false and ig:visible() == false
                    _G._matrix_repair_verify = _E:verify() == true
                    _G._matrix_repair_visible = repaired ~= nil
                        and repaired:visible() == true
                ''')

                self.assertTrue(bool(g._matrix_fixture_ok),
                    "fixture must expose the owned flash and source bitmaps")
                self.assertFalse(bool(g._matrix_missing),
                    "row4 owned flash must exist for every corruption case")
                self.assertTrue(bool(g._matrix_corrupt_verify),
                    "corrupting %s must fail production verification" % case)
                self.assertTrue(bool(g._matrix_throttle_native),
                    "sub-throttle update must release both native ghosts for %s"
                    % case)
                self.assertTrue(bool(g._matrix_throttle_verify),
                    "sub-throttle update must keep %s uncertified" % case)
                self.assertTrue(bool(g._matrix_repair_same),
                    "ordinary update must repair the same flash for %s" % case)
                self.assertTrue(bool(g._matrix_repair_native_hidden),
                    "repaired %s must lease both native ghosts hidden" % case)
                self.assertTrue(bool(g._matrix_repair_verify),
                    "repaired %s must certify equipment again" % case)
                self.assertTrue(bool(g._matrix_repair_visible),
                    "repaired %s must be visible again" % case)

        lua = _flash_lua()
        g = lua.globals()
        lua.execute(r'''
            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            _G._source_fixture_ok = flash ~= nil
            if not flash then
                _G._source_throttle_native = false
                _G._source_throttle_owned_hidden = false
                _G._source_throttle_verify = true
                _G._source_recovered_same = false
                _G._source_recovered_native_hidden = false
                _G._source_recovered_verify = false
                return
            end

            local original_class = PlayerManager.get_grenade_amount
            local original_instance = managers.player
                and managers.player.get_grenade_amount
            local function boom()
                error('kyohud test get_grenade_amount failure')
            end
            PlayerManager.get_grenade_amount = boom
            if managers.player then
                managers.player.get_grenade_amount = boom
            end

            _R:update(_m, 1.14, .01)
            local rg = _gren:child('grenades_radial_ghost')
            local ig = _gren:child('grenades_icon_ghost')
            _G._source_throttle_native = rg ~= nil and ig ~= nil
                and rg:visible() == true and ig:visible() == true
            _G._source_throttle_owned_hidden = flash:visible() == false
            _G._source_throttle_verify = _E:_verify_grenade_flash() == false

            PlayerManager.get_grenade_amount = original_class
            if managers.player then
                managers.player.get_grenade_amount = original_instance
            end
            _E:refresh(_m)
            _R:update(_m, 1.20, .06)

            local recovered = _E._rows[4] and _E._rows[4]._grenade_flash
            _G._source_recovered_same = recovered == flash
            _G._source_recovered_native_hidden = rg ~= nil and ig ~= nil
                and rg:visible() == false and ig:visible() == false
            _G._source_recovered_verify = _E:verify() == true
        ''')

        self.assertTrue(bool(g._source_fixture_ok),
            "source failure case needs the owned flash")
        self.assertTrue(bool(g._source_throttle_native),
            "a throwing source getter must release both native ghosts")
        self.assertTrue(bool(g._source_throttle_owned_hidden),
            "a throwing source getter must hide the owned flash")
        self.assertTrue(bool(g._source_throttle_verify),
            "a throwing source getter must fail production verification")
        self.assertTrue(bool(g._source_recovered_same),
            "restored source getter must recover the same owned flash")
        self.assertTrue(bool(g._source_recovered_native_hidden),
            "recovered source getter must lease both native ghosts hidden")
        self.assertTrue(bool(g._source_recovered_verify),
            "recovered source getter must certify equipment again")

        lua = _flash_lua()
        g = lua.globals()
        lua.execute(r'''
            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            _G._registry_fixture_ok = flash ~= nil
            if not flash then
                _G._registry_available = false
                _G._registry_throttle_native = false
                _G._registry_throttle_owned_hidden = false
                _G._registry_throttle_verify = true
                _G._registry_recovered_same = false
                _G._registry_recovered_native_hidden = false
                _G._registry_recovered_verify = false
                return
            end

            local function copy_table(source)
                local copy = {}
                for key, value in pairs(source) do
                    copy[key] = value
                end
                return setmetatable(copy, getmetatable(source))
            end

            assert(managers.player ~= nil
                and type(managers.player._global) == 'table',
                'fixture must expose managers.player._global')
            local holder = managers.player._global
            local key = 'synced_grenades'
            assert(type(holder[key]) == 'table',
                'fixture must expose managers.player._global.synced_grenades '
                .. 'as a table')
            _G._registry_available = true

            local original = holder[key]
            holder[key] = copy_table(original)

            _R:update(_m, 1.14, .01)
            local rg = _gren:child('grenades_radial_ghost')
            local ig = _gren:child('grenades_icon_ghost')
            _G._registry_throttle_native = rg ~= nil and ig ~= nil
                and rg:visible() == true and ig:visible() == true
            _G._registry_throttle_owned_hidden = flash:visible() == false
            _G._registry_throttle_verify = _E:_verify_grenade_flash() == false

            holder[key] = original
            _E:refresh(_m)
            _R:update(_m, 1.20, .06)

            local recovered = _E._rows[4] and _E._rows[4]._grenade_flash
            _G._registry_recovered_same = recovered == flash
            _G._registry_recovered_native_hidden = rg ~= nil and ig ~= nil
                and rg:visible() == false and ig:visible() == false
            _G._registry_recovered_verify = _E:verify() == true
        ''')

        self.assertTrue(bool(g._registry_fixture_ok),
            "registry case needs the owned flash")
        self.assertTrue(bool(g._registry_available),
            "fixture must expose a synced_grenades table to replace")
        self.assertTrue(bool(g._registry_throttle_native),
            "a replaced synced_grenades identity must release native ghosts")
        self.assertTrue(bool(g._registry_throttle_owned_hidden),
            "a replaced synced_grenades identity must hide the owned flash")
        self.assertTrue(bool(g._registry_throttle_verify),
            "a replaced synced_grenades identity must fail production verification")
        self.assertTrue(bool(g._registry_recovered_same),
            "restoring synced_grenades identity must recover the same flash")
        self.assertTrue(bool(g._registry_recovered_native_hidden),
            "restored synced_grenades identity must lease natives hidden")
        self.assertTrue(bool(g._registry_recovered_verify),
            "restored synced_grenades identity must certify equipment again")


if __name__ == "__main__":
    unittest.main()
