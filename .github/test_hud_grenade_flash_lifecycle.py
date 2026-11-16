"""H5 grenade flash lifecycle: the owned row4 flash follows native ghost pulses
while both native leaves stay leased, vanishes with the native flash, and must
restart on the next native pulse even during a sub-throttle update.
"""
import unittest

from test_hud_grenade_flash_replacement import _flash_lua


class GrenadeFlashLifecycleTests(unittest.TestCase):
    def test_native_pulse_restart_on_subthrottle_update(self):
        lua = _flash_lua()
        g = lua.globals()

        lua.execute(r'''
            _G._lifecycle_verify_initial = _E:verify() == true
            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            _G._lifecycle_missing_flash = flash == nil
            if not flash then return end

            local rg = _gren:child('grenades_radial_ghost')
            local ig = _gren:child('grenades_icon_ghost')
            _G._lifecycle_missing_ghosts = rg == nil or ig == nil
            if not (rg and ig) then return end

            local function base_shape(base)
                return {base:x(), base:y(), base:w(), base:h()}
            end
            local radial_base = base_shape(_radial)
            local icon_base = base_shape(_icon)

            local function apply_pulse(ghost, base, alpha, overhang)
                ghost:set_color(Color(alpha, 1, 1, 1))
                ghost:set_shape(
                    base:x() - base:w() * overhang,
                    base:y() - base:h() * overhang,
                    base:w() * (1 + overhang * 2),
                    base:h() * (1 + overhang * 2))
            end

            local function restore_native(ghost, base)
                ghost:set_color(Color(0, 1, 1, 1))
                ghost:set_shape(base[1], base[2], base[3], base[4])
                ghost:set_visible(false)
            end

            local function runtime_group_absent(name)
                local panels = {_gren, row._root}
                for i = 1, #panels do
                    local panel = panels[i]
                    if panel ~= nil and panel:child(name) ~= nil then
                        return false
                    end
                end
                return true
            end

            apply_pulse(rg, _radial, .5, .25)
            apply_pulse(ig, _icon, .5, .25)
            _R:update(_m, 1.14, .01)

            _G._lifecycle_sync_same = _E._rows[4]._grenade_flash == flash
            _G._lifecycle_sync_alpha = math.abs(flash:alpha() - .5) <= .005
            _G._lifecycle_sync_ghosts_hidden = rg:visible() == false
                and ig:visible() == false

            restore_native(rg, radial_base)
            restore_native(ig, icon_base)
            _R:update(_m, 1.20, .06)

            _G._lifecycle_off_flash_hidden = flash:visible() == false
            _G._lifecycle_off_ghosts_hidden = rg:visible() == false
                and ig:visible() == false
            _G._lifecycle_off_group_absent =
                runtime_group_absent('local_p_grenade_flash')
            _G._lifecycle_off_seconds = row._value:text()

            apply_pulse(rg, _radial, .9, .05)
            apply_pulse(ig, _icon, .9, .05)
            rg:set_visible(true)
            ig:set_visible(true)
            _R:update(_m, 1.21, .01)

            local current = _E._rows[4]._grenade_flash
            _G._lifecycle_restart_same = current == flash
            _G._lifecycle_restart_visible = current ~= nil
                and current:visible() == true
            _G._lifecycle_restart_alpha = current ~= nil
                and math.abs(current:alpha() - .9) <= .005
            _G._lifecycle_restart_ghosts_hidden = rg:visible() == false
                and ig:visible() == false
            _G._lifecycle_final_seconds = row._value:text()
            _G._lifecycle_verify_final = _E:verify() == true
        ''')

        self.assertTrue(bool(g._lifecycle_verify_initial),
            "equipment must be certified before the lifecycle starts")
        self.assertFalse(bool(g._lifecycle_missing_flash),
            "row4._grenade_flash must exist before the lifecycle starts")
        self.assertFalse(bool(g._lifecycle_missing_ghosts),
            "both native ghost leaves must exist before the lifecycle starts")

        self.assertTrue(bool(g._lifecycle_sync_same),
            "mid-pulse update must retain the same owned flash primitive")
        self.assertTrue(bool(g._lifecycle_sync_alpha),
            "mid-pulse update must mirror the native alpha .5 onto the flash")
        self.assertTrue(bool(g._lifecycle_sync_ghosts_hidden),
            "mid-pulse update must keep both native ghost leaves hidden")

        self.assertTrue(bool(g._lifecycle_off_flash_hidden),
            "owned flash must be hidden once the native flash is off")
        self.assertTrue(bool(g._lifecycle_off_ghosts_hidden),
            "both native ghost leaves must stay hidden while the flash is off")
        self.assertTrue(bool(g._lifecycle_off_group_absent),
            "runtime group local_p_grenade_flash must be absent when off")
        self.assertEqual(g._lifecycle_off_seconds, "17s",
            "flash-off update must keep the existing recharge at 17s")

        self.assertTrue(bool(g._lifecycle_restart_same),
            "new native pulse must reuse the same owned flash primitive")
        self.assertTrue(bool(g._lifecycle_restart_visible),
            "new native pulse must make the owned flash visible again")
        self.assertTrue(bool(g._lifecycle_restart_alpha),
            "new native pulse must mirror the native alpha .9 onto the flash")
        self.assertTrue(bool(g._lifecycle_restart_ghosts_hidden),
            "new native pulse must keep both native ghost leaves hidden")
        self.assertEqual(g._lifecycle_final_seconds, "17s",
            "new native pulse must keep the existing recharge at 17s")
        self.assertTrue(bool(g._lifecycle_verify_final),
            "equipment must stay certified after the new pulse restart")


if __name__ == "__main__":
    unittest.main()
