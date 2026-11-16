"""Boundary characterization for the H5 grenade flash.

Covers the generic supported local kinds, atomic native acquisition rollback,
and native source identity replacement. These cases use the real runtime and
the existing flash fixture; they do not claim every engine projectile is tested.
"""
import unittest

from test_hud_grenade_flash_replacement import _flash_lua


class GrenadeFlashBoundaryTests(unittest.TestCase):
    def test_supported_local_kinds_and_initial_idle(self):
        for kind in ("ability", "throwable"):
            with self.subTest(kind=kind):
                lua = _flash_lua()
                g = lua.globals()
                g._kind = kind

                lua.execute(r'''
                    local kind = _kind
                    local row = _E._rows[4]
                    local active = _E._rows[6]
                    local flash = row and row._grenade_flash
                    local active_root = active and active._root
                    local active_value = active and active._value
                    local active_visible = active_root and active_root:visible()
                    local active_text = active_value and active_value:text()
                    _G._fixture_ok = flash ~= nil and active_root ~= nil
                        and active_value ~= nil
                        and _E:_verify_grenade_flash() == true
                    if not _G._fixture_ok then return end

                    local entry = {base_cooldown = 30, icon = 'frag_grenade'}
                    if kind == 'ability' then
                        entry.ability = true
                    else
                        entry.throwable = true
                    end
                    _native_set_projectile_tweak('pocket', entry)
                    _E:refresh(_m)
                    _R:update(_m, 1.20, .06)

                    local snap = _E:get_snapshot()
                    local rg = _gren:child('grenades_radial_ghost')
                    local ig = _gren:child('grenades_icon_ghost')
                    local current = _E._rows[4]._grenade_flash
                    _G._kind_ok = snap.projectile.kind == kind
                    _G._mirror_visible = current ~= nil
                        and current:visible() == true
                        and math.abs(current:alpha() - .75) <= .005
                    _G._verify_ok = _E:_verify_grenade_flash() == true
                    _G._ghosts_leased = rg ~= nil and ig ~= nil
                        and rg:visible() == false and ig:visible() == false
                    _G._count_ok = snap.projectile.charges.raw == 1
                    _G._active_cooldown = snap.cooldown.active == true
                    _G._not_ready = row._value:text() ~= 'READY'
                        and _E._rows[5]._label:text() ~= 'READY'
                    _G._active_ok = _E._rows[6]._root == active_root
                        and _E._rows[6]._value == active_value
                        and _E._rows[6]._root:visible() == active_visible
                        and _E._rows[6]._value:text() == active_text

                    managers.player:_native_clear_replenish_timer()
                    local radial_base = {
                        _radial:x(), _radial:y(), _radial:w(), _radial:h()}
                    local icon_base = {
                        _icon:x(), _icon:y(), _icon:w(), _icon:h()}
                    local function terminal(ghost, base)
                        ghost:set_color(Color(0, 1, 1, 1))
                        ghost:set_shape(base[1], base[2], base[3], base[4])
                        ghost:set_visible(false)
                    end
                    terminal(rg, radial_base)
                    terminal(ig, icon_base)
                    _E:refresh(_m)
                    _R:update(_m, 1.26, .06)

                    local idle = _E:get_snapshot()
                    local idle_flash = _E._rows[4]._grenade_flash
                    _G._idle_count = idle.projectile.charges.raw == 1
                    _G._idle_cooldown = idle.cooldown.active == false
                    _G._idle_no_pulse = idle_flash == nil
                        or idle_flash:visible() == false
                    local leases = 0
                    for _, lease in ipairs(
                        kyohud.hud.native_visibility._entries) do
                        if lease.owner == _E then leases = leases + 1 end
                    end
                    _G._idle_no_lease = leases == 0
                ''')

                self.assertTrue(bool(g._fixture_ok),
                    "%s fixture must expose the certified flash and ACTIVE row"
                    % kind)
                self.assertTrue(bool(g._kind_ok),
                    "%s tweak must be classified as the matching local kind"
                    % kind)
                self.assertTrue(bool(g._mirror_visible),
                    "%s must keep the owned flash mirror visible with alpha .75"
                    % kind)
                self.assertTrue(bool(g._verify_ok),
                    "%s must keep the owned flash certified" % kind)
                self.assertTrue(bool(g._ghosts_leased),
                    "%s must lease both native ghost leaves hidden" % kind)
                self.assertTrue(bool(g._count_ok),
                    "%s must retain the current charge of one" % kind)
                self.assertTrue(bool(g._active_cooldown),
                    "%s must retain the active native cooldown" % kind)
                self.assertTrue(bool(g._not_ready),
                    "%s must not claim READY while one charge is cooling down"
                    % kind)
                self.assertTrue(bool(g._active_ok),
                    "%s must not change the independent ACTIVE row" % kind)
                self.assertTrue(bool(g._idle_count),
                    "%s idle terminal state must retain one known charge" % kind)
                self.assertTrue(bool(g._idle_cooldown),
                    "%s idle terminal state must have no active cooldown" % kind)
                self.assertTrue(bool(g._idle_no_pulse),
                    "%s idle terminal state must not show an owned pulse" % kind)
                self.assertTrue(bool(g._idle_no_lease),
                    "%s idle availability must not invent a native lease" % kind)

    def test_native_acquisition_rollback_and_retry(self):
        lua = _flash_lua()
        g = lua.globals()
        lua.execute(r'''
            local rg = _gren:child('grenades_radial_ghost')
            local ig = _gren:child('grenades_icon_ghost')
            _G._fixture_ok = rg ~= nil and ig ~= nil
                and _E:verify() == true
            if not _G._fixture_ok then return end

            kyohud.settings.enable_equipment = false
            _R:refresh_settings(_m)
            _G._off_native = rg:visible() == true and ig:visible() == true

            local original_set_visible = rg.set_visible
            rg.set_visible = function(self, value)
                if value == false then
                    error('kyohud radial ghost false refused before mutation')
                end
                return original_set_visible(self, value)
            end

            kyohud.settings.enable_equipment = true
            _R:refresh_settings(_m)
            _R:update(_m, 1.20, .06)

            local fail_row = _E._rows[4]
            local fail_root = fail_row and fail_row._root
            local fail_flash = fail_row and fail_row._grenade_flash
            _G._fail_flash_exists = fail_root ~= nil and fail_flash ~= nil
            _G._rollback_native = rg:visible() == true
                and ig:visible() == true
            _G._fail_no_effective = not (
                fail_root ~= nil and fail_flash ~= nil
                and fail_root:visible() and fail_flash:visible())
            local count = 0
            if fail_root ~= nil then
                for _, child in pairs(fail_root:children()) do
                    if child == fail_flash then count = count + 1 end
                end
            end
            _G._fail_single = fail_row ~= nil
                and fail_row._grenade_flash == fail_flash and count == 1

            rg.set_visible = original_set_visible
            _R:update(_m, 1.26, .06)

            local recovered = _E._rows[4]
                and _E._rows[4]._grenade_flash
            _G._recovered_same = fail_flash ~= nil
                and recovered == fail_flash
            _G._recovered_verify = _E:verify() == true
            _G._recovered_flash_verify =
                _E:_verify_grenade_flash() == true
            _G._recovered_visible = recovered ~= nil
                and recovered:visible() == true
                and math.abs(recovered:alpha() - .75) <= .005
            _G._recovered_ghosts = rg:visible() == false
                and ig:visible() == false
        ''')

        self.assertTrue(bool(g._fixture_ok),
            "fixture must expose both native ghosts and certified equipment")
        self.assertTrue(bool(g._off_native),
            "disabling equipment must restore both native leaves visible")
        self.assertTrue(bool(g._fail_flash_exists),
            "the failed acquisition must retain the owned flash primitive")
        self.assertTrue(bool(g._rollback_native),
            "a throwing radial set_visible(false) must roll both natives back")
        self.assertTrue(bool(g._fail_no_effective),
            "failed acquisition must not leave an effective owned pulse")
        self.assertTrue(bool(g._fail_single),
            "failed acquisition must not duplicate the owned flash primitive")
        self.assertTrue(bool(g._recovered_same),
            "restored setter must retain the same owned flash bitmap")
        self.assertTrue(bool(g._recovered_verify),
            "restored setter must recertify equipment")
        self.assertTrue(bool(g._recovered_flash_verify),
            "restored setter must recertify the owned grenade flash")
        self.assertTrue(bool(g._recovered_visible),
            "restored setter must recover the owned flash at alpha .75")
        self.assertTrue(bool(g._recovered_ghosts),
            "restored setter must lease both native ghosts hidden again")

    def test_native_source_identity_replacement_and_alpha_failure(self):
        lua = _flash_lua()
        g = lua.globals()
        lua.execute(r'''
            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            local rg = _gren:child('grenades_radial_ghost')
            local ig = _gren:child('grenades_icon_ghost')
            local sentinel = _gren:child('native_flash_sentinel')
            _G._fixture_ok = flash ~= nil and rg ~= nil and ig ~= nil
                and sentinel ~= nil
                and _E:_verify_grenade_flash() == true
            if not _G._fixture_ok then return end

            local function close(a, b) return math.abs(a - b) <= .05 end
            local old_shape = {rg:x(), rg:y(), rg:w(), rg:h()}
            local old_color = rg:color()
            local old_visible = rg:visible()
            local sentinel_shape = {
                sentinel:x(), sentinel:y(), sentinel:w(), sentinel:h()}
            local sentinel_color = sentinel:color()
            local sentinel_visible = sentinel:visible()

            local function old_intact()
                local color = rg:color()
                return not alive(rg)
                    and _gren:child('grenades_radial_ghost') ~= rg
                    and close(rg:x(), old_shape[1])
                    and close(rg:y(), old_shape[2])
                    and close(rg:w(), old_shape[3])
                    and close(rg:h(), old_shape[4])
                    and close(color.r, old_color.r)
                    and close(color.g, old_color.g)
                    and close(color.b, old_color.b)
                    and close(color.a, old_color.a)
                    and rg:visible() == old_visible
            end

            local function sentinel_intact()
                local color = sentinel:color()
                return sentinel == _gren:child('native_flash_sentinel')
                    and sentinel:parent() == _gren
                    and sentinel:visible() == sentinel_visible
                    and close(sentinel:x(), sentinel_shape[1])
                    and close(sentinel:y(), sentinel_shape[2])
                    and close(sentinel:w(), sentinel_shape[3])
                    and close(sentinel:h(), sentinel_shape[4])
                    and close(color.r, sentinel_color.r)
                    and close(color.g, sentinel_color.g)
                    and close(color.b, sentinel_color.b)
                    and close(color.a, sentinel_color.a)
            end

            _gren:remove(rg)
            local replacement = _gren:bitmap({name = 'grenades_radial_ghost'})
            replacement:set_color(Color(.75, 1, 1, 1))
            local scale = 1.25
            local w, h = _radial:w() * scale, _radial:h() * scale
            replacement:set_shape(_radial:x() + _radial:w() * .5 - w * .5,
                _radial:y() + _radial:h() * .5 - h * .5, w, h)
            replacement:set_visible(true)

            _R:update(_m, 1.14, .01)

            local current = _E._rows[4]._grenade_flash
            _G._replace_source =
                _gren:child('grenades_radial_ghost') == replacement
            _G._replace_same = current == flash
            _G._replace_verified = _E:_verify_grenade_flash() == true
            _G._replace_flash = current ~= nil and current:visible() == true
                and math.abs(current:alpha() - .75) <= .005
            _G._replace_leased = replacement:visible() == false
                and ig:visible() == false
            _G._replace_alpha = math.abs(replacement:alpha() - .75) <= .005
            _G._replace_old = old_intact()
            _G._replace_sentinel = sentinel_intact()

            local original_alpha = replacement.alpha
            replacement.alpha = function()
                error('kyohud native alpha getter failure')
            end
            _R:update(_m, 1.15, .01)

            local failed = _E._rows[4]._grenade_flash
            _G._alpha_same = failed == flash
            _G._alpha_hidden = failed ~= nil and failed:visible() == false
            _G._alpha_fallback = replacement:visible() == true
                and ig:visible() == true
            _G._alpha_verify_false = _E:_verify_grenade_flash() == false
            _G._alpha_old = old_intact()
            _G._alpha_sentinel = sentinel_intact()

            replacement.alpha = original_alpha
            _R:update(_m, 1.21, .06)

            local recovered = _E._rows[4]._grenade_flash
            _G._recover_same = recovered == flash
            _G._recover_verified = _E:verify() == true
                and _E:_verify_grenade_flash() == true
            _G._recover_flash = recovered ~= nil
                and recovered:visible() == true
                and math.abs(recovered:alpha() - .75) <= .005
            _G._recover_leased = replacement:visible() == false
                and ig:visible() == false
            _G._recover_old = old_intact()
            _G._recover_sentinel = sentinel_intact()
        ''')

        self.assertTrue(bool(g._fixture_ok),
            "fixture must expose the flash, both ghosts and the sentinel")
        self.assertTrue(bool(g._replace_source),
            "the replacement bitmap must become the named native radial source")
        self.assertTrue(bool(g._replace_same),
            "source identity replacement must retain the owned flash bitmap")
        self.assertTrue(bool(g._replace_verified),
            "the replacement source must keep the owned flash certified")
        self.assertTrue(bool(g._replace_flash),
            "the replacement source must mirror alpha .75 on the owned flash")
        self.assertTrue(bool(g._replace_leased),
            "the replacement and icon ghosts must both be leased hidden")
        self.assertTrue(bool(g._replace_alpha),
            "the replacement source alpha getter must expose phase .75")
        self.assertTrue(bool(g._replace_old),
            "the removed native radial must not be mutated or reinserted")
        self.assertTrue(bool(g._replace_sentinel),
            "the native sentinel must survive source replacement unchanged")
        self.assertTrue(bool(g._alpha_same),
            "a failed alpha getter must retain the same owned flash bitmap")
        self.assertTrue(bool(g._alpha_hidden),
            "a failed alpha getter must hide the owned flash")
        self.assertTrue(bool(g._alpha_fallback),
            "a failed alpha getter must restore both native leaves as fallback")
        self.assertTrue(bool(g._alpha_verify_false),
            "a failed alpha getter must fail owned flash certification")
        self.assertTrue(bool(g._alpha_old),
            "alpha failure must not mutate or reinsert the removed native radial")
        self.assertTrue(bool(g._alpha_sentinel),
            "alpha failure must not mutate the native sentinel")
        self.assertTrue(bool(g._recover_same),
            "restored alpha getter must reuse the same owned flash bitmap")
        self.assertTrue(bool(g._recover_verified),
            "restored alpha getter must recertify equipment and owned flash")
        self.assertTrue(bool(g._recover_flash),
            "restored alpha getter must mirror the replacement alpha .75")
        self.assertTrue(bool(g._recover_leased),
            "restored alpha getter must lease both native ghosts hidden again")
        self.assertTrue(bool(g._recover_old),
            "recovery must not mutate or reinsert the removed native radial")
        self.assertTrue(bool(g._recover_sentinel),
            "recovery must leave the native sentinel unchanged")

    def test_owned_flash_bounds_follow_original_icon_across_native_phases(self):
        lua = _flash_lua()
        g = lua.globals()
        lua.execute(r'''
            local row = _E._rows[4]
            local flash = row and row._grenade_flash
            local icon = row and row._icon
            local value = row and row._value
            local rg = _gren:child('grenades_radial_ghost')
            local ig = _gren:child('grenades_icon_ghost')
            _G._fixture_ok = flash ~= nil and icon ~= nil and value ~= nil
                and rg ~= nil and ig ~= nil
                and _E:verify() == true
            if not _G._fixture_ok then return end

            local function close(a, b) return math.abs(a - b) <= .05 end
            local function rect(p) return {p:x(), p:y(), p:w(), p:h()} end
            local function same_rect(shape, p)
                return close(shape[1], p:x()) and close(shape[2], p:y())
                    and close(shape[3], p:w()) and close(shape[4], p:h())
            end

            local icon_rect = rect(icon)
            local value_y = value:y()
            local radial_rect = rect(_radial)
            local icon_src_rect = rect(_icon)
            local seconds = value:text()
            local charges = _E:get_snapshot().projectile.charges.raw

            local phases = {.25, .5, .9}
            local times = {1.20, 1.26, 1.32}

            _G._inside = {}
            _G._above_seconds = {}
            _G._leased = {}
            _G._same_flash = {}
            _G._seconds_ok = {}
            _G._verify_ok = {}
            _G._charges_ok = {}
            _G._sources_ok = {}

            for i = 1, #phases do
                local p = phases[i]
                local function phase_ghost(ghost, source)
                    local w = source:w() * (1 + p)
                    local h = source:h() * (1 + p)
                    ghost:set_shape(source:x() + source:w() * .5 - w * .5,
                        source:y() + source:h() * .5 - h * .5, w, h)
                    ghost:set_color(Color(1 - p, 1, 1, 1))
                end
                phase_ghost(rg, _radial)
                phase_ghost(ig, _icon)

                _R:update(_m, times[i], .06)

                local current = _E._rows[4]._grenade_flash
                local x, y = current:x(), current:y()
                local w, h = current:w(), current:h()
                _G._inside[i] = x >= icon_rect[1] - .05
                    and y >= icon_rect[2] - .05
                    and x + w <= icon_rect[1] + icon_rect[3] + .05
                    and y + h <= icon_rect[2] + icon_rect[4] + .05
                _G._above_seconds[i] = y + h <= value_y
                _G._leased[i] = rg:visible() == false and ig:visible() == false
                _G._same_flash[i] = current == flash
                _G._seconds_ok[i] = _E._rows[4]._value:text() == seconds
                _G._verify_ok[i] = _E:verify() == true
                _G._charges_ok[i] = _E:get_snapshot().projectile.charges.raw
                    == charges
                _G._sources_ok[i] = same_rect(icon_rect, icon)
                    and same_rect(radial_rect, _radial)
                    and same_rect(icon_src_rect, _icon)
            end
            _G._seconds_is_17 = seconds == '17s'
        ''')

        self.assertTrue(bool(g._fixture_ok),
            "fixture must expose the row4 flash, icon, ghosts and certification")
        self.assertTrue(bool(g._seconds_is_17),
            "the ordinary fixture must start from the 17s recharge")
        for i, phase in enumerate((.25, .5, .9), start=1):
            with self.subTest(phase=phase):
                self.assertTrue(bool(g._inside[i]),
                    "owned flash at phase %s must stay inside the original "
                    "row icon rectangle" % phase)
                self.assertTrue(bool(g._above_seconds[i]),
                    "owned flash at phase %s must end at or above the seconds "
                    "text" % phase)
                self.assertTrue(bool(g._leased[i]),
                    "both native ghost leaves must stay leased hidden at "
                    "phase %s" % phase)
                self.assertTrue(bool(g._same_flash[i]),
                    "the same owned flash bitmap must be retained at phase %s"
                    % phase)
                self.assertTrue(bool(g._seconds_ok[i]),
                    "the 17s recharge must be preserved at phase %s" % phase)
                self.assertTrue(bool(g._verify_ok[i]),
                    "equipment must stay certified at phase %s" % phase)
                self.assertTrue(bool(g._charges_ok[i]),
                    "the charge count must be preserved at phase %s" % phase)
                self.assertTrue(bool(g._sources_ok[i]),
                    "native source fields must stay unedited at phase %s"
                    % phase)


if __name__ == "__main__":
    unittest.main()
