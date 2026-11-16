"""Integrated grenade recharge rendered on the grenade cell (vertical orange reveal)."""
import unittest

from test_hud_equipment_presentation import presentation
from test_hud_native_cooldown_replacement import _runtime


class EquipmentIntegratedRechargeTests(unittest.TestCase):
    def test_real_cooldown_moves_into_grenade_row_then_clear_restores_counter(self):
        l = presentation()
        l.execute(r'''
            assert(E:verify(), 'precondition: mounted equipment is certified')
            local row = E._rows[4]
            local root, value = row._root, row._value
            assert(root:visible() and value:text() == '1', 'precondition: grenade counter 1')
            assert(root:w() > 0 and root:h() > 0, 'precondition: existing grenade cell geometry')
            assert(E:get_snapshot().projectile.charges.raw == 1, 'precondition: real charge snapshot')
            assert(not row._track:visible() and not row._fill:visible(), 'precondition: old strip hidden')

            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20, end_time = 117})
            RT:update(managers.hud, 1, 0.06)

            assert(E:get_snapshot().projectile.charges.raw == 1, 'charges stay snapshot 1')
            assert(value:text() == '17s', 'integrated grenade row shows 17s')
            assert(not E._rows[5]._root:visible(), 'separate RECHARGE row stays hidden')
            local reveal = row._recharge_reveal
            assert(reveal and reveal:visible(), 'integrated progress reveal visible')
            assert(reveal:h() > 0, 'reveal height available')
            assert(math.abs(reveal:w() - root:w()) < .05, 'reveal width available')
            assert(math.abs(reveal:y() - root:h() * (17 / 20)) < .05, 'initial reveal y')
            local ratio = reveal:h() / root:h()
            assert(math.abs(ratio - (1 - 17 / 20)) < .02, 'initial elapsed ratio ' .. ratio)

            _game_clock:set_time(1005)
            RT:update(managers.hud, 1.06, 0.06)

            assert(value:text() == '12s', 'integrated grenade row advances to 12s')
            ratio = reveal:h() / root:h()
            assert(math.abs(ratio - (1 - 12 / 20)) < .02, 'advanced elapsed ratio ' .. ratio)
            assert(math.abs(reveal:y() - root:h() * (12 / 20)) < .05, 'advanced reveal y')

            managers.player:clear_timers()
            dispatch(PlayerManager, 'clear_timers', managers.player)
            RT:update(managers.hud, 1.12, 0.06)

            assert(value:text() == '1', 'counter restored after native clear')
            assert(not reveal:visible(), 'reveal hidden but retained after clear')
            assert(not E._rows[4]._track:visible() and not E._rows[4]._fill:visible(),
                'old strip hidden after clear')
            assert(root == E._rows[4]._root and value == E._rows[4]._value
                and reveal == E._rows[4]._recharge_reveal,
                'same row4 primitives')
            assert(not E._rows[5]._root:visible(), 'RECHARGE row remains hidden')
            assert(not E._rows[6]._root:visible(), 'ACTIVE row remains independent')
            assert(E:verify(), 'equipment still certified')
        ''')

    def test_runtime_event_integrated_row_keeps_native_radial_leased(self):
        lua = _runtime()
        lua.execute("RT=_R; E=_E")
        lua.execute(r'''
            _fallback_lease = _radial:visible() == false and _radial == _leaf
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20, end_time = 1017})
            RT:update(managers.hud, 1.06, 0.06)

            local row = E._rows[4]
            local root, value = row._root, row._value
            local reveal = row._recharge_reveal
            _integrated_verified = E:verify()
            _integrated_value = value:text() == '17s'
            _integrated_visible = root:visible() and reveal ~= nil and reveal:visible()
            _integrated_reveal_height = reveal ~= nil and reveal:h() > 0
            local ratio = _integrated_reveal_height and reveal:h() / root:h() or -1
            _integrated_ratio = math.abs(ratio - (1 - 17 / 20)) < .02
            _integrated_row5_hidden = not E._rows[5]._root:visible()
            _integrated_snapshot = E:get_snapshot().projectile.charges.raw == 1
            _integrated_radial_leased = _radial:visible() == false and _radial == _leaf
            _integrated_alpha = _radial:alpha() == .5
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._fallback_lease), "old RECHARGE fallback must lease the radial")
        self.assertTrue(bool(g._integrated_verified), "integrated row4 render must certify")
        self.assertTrue(bool(g._integrated_value), "integrated grenade row shows 17s")
        self.assertTrue(bool(g._integrated_visible), "integrated progress must be visible")
        self.assertTrue(bool(g._integrated_reveal_height), "integrated reveal height available")
        self.assertTrue(bool(g._integrated_ratio), "integrated elapsed ratio")
        self.assertTrue(bool(g._integrated_row5_hidden), "separate RECHARGE row stays hidden")
        self.assertTrue(bool(g._integrated_snapshot), "charges stay snapshot 1")
        self.assertTrue(bool(g._integrated_radial_leased), "native radial stays leased while integrated")
        self.assertTrue(bool(g._integrated_alpha), "native radial alpha untouched")

    def test_corrupt_integrated_fill_on_throttled_frame_restores_then_releases(self):
        lua = _runtime()
        lua.execute("RT=_R; E=_E")
        lua.execute(r'''
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20, end_time = 1017})
            RT:update(managers.hud, 1.06, 0.06)

            local row = E._rows[4]
            local root, value = row._root, row._value
            local reveal = row._recharge_reveal
            _qualified = E:verify() and value:text() == '17s'
                and reveal ~= nil and reveal:visible() and reveal:h() > 0
            local correct_h = reveal:h()
            reveal:set_shape(reveal:x(), reveal:y(), reveal:w(), reveal:h() + 1)

            RT:update(managers.hud, 1.07, 0.01)

            _corrupt_verify = E:verify() == false
            _corrupt_restored = _radial:visible() == true and _radial == _leaf
                and _radial:alpha() == .5

            RT:update(managers.hud, 1.13, 0.06)

            _recovered_verify = E:verify()
            _recovered_same = root == E._rows[4]._root and value == E._rows[4]._value
                and reveal == E._rows[4]._recharge_reveal
            _recovered_value = value:text() == '17s'
            _recovered_row5_hidden = not E._rows[5]._root:visible()
            _recovered_reveal = math.abs(reveal:h() - correct_h) < .05
            _recovered_radial = _radial:visible() == false and _radial == _leaf
                and _radial:alpha() == .5
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._qualified), "integrated row4 must qualify before corruption")
        self.assertTrue(bool(g._corrupt_verify), "corrupt reveal height must fail equipment verify")
        self.assertTrue(bool(g._corrupt_restored), "throttled frame must restore native radial")
        self.assertTrue(bool(g._recovered_verify), "ordinary update must repair row4 certification")
        self.assertTrue(bool(g._recovered_same), "recovery must retain the same row4 primitives")
        self.assertTrue(bool(g._recovered_value), "recovered row4 keeps 17s")
        self.assertTrue(bool(g._recovered_row5_hidden), "recovered integrated row keeps row5 hidden")
        self.assertTrue(bool(g._recovered_reveal), "ordinary update restores the retained reveal height")
        self.assertTrue(bool(g._recovered_radial), "recovered integrated row re-leases native radial")

    def test_source_freshness_rejects_stale_integrated_record_and_nan_clock(self):
        lua = presentation()
        lua.execute(r'''
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20})
            RT:update(managers.hud, 1, 0.06)

            _qualified = E:get_snapshot().cooldown.integrated == true
            managers.player._timers.replenish_grenades = {t = 1017}
            local fresh = E:get_snapshot().cooldown
            _fresh_no_integrated = fresh.integrated ~= true

            _game_clock:set_time(0 / 0)
            local invalid = E:get_snapshot().cooldown
            _invalid_no_integrated = invalid.integrated ~= true
            _invalid_no_active = not (invalid.known == true and invalid.active == true)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._qualified), "event must qualify integrated before record change")
        self.assertTrue(bool(g._fresh_no_integrated), "stale cooldown record must not inherit integrated")
        self.assertTrue(bool(g._invalid_no_integrated), "NaN game time must not expose integrated")
        self.assertTrue(bool(g._invalid_no_active), "NaN game time must not expose known active")

    def test_native_speedup_record_change_and_final_counter(self):
        lua = presentation()
        lua.execute(r'''
            assert(E:verify(), 'precondition: mounted equipment')
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20})
            RT:update(managers.hud, 1, 0.06)
            _qualified = E:get_snapshot().cooldown.integrated == true

            _game_clock:set_time(1001)
            managers.player._timers.replenish_grenades.t = 1004
            RT:update(managers.hud, 1.06, 0.06)
            local snap = E:get_snapshot()
            _speed_value = E._rows[4]._value:text()
            _speed_ratio = E._rows[4]._recharge_reveal:h() / E._rows[4]._root:h()
            _speed_charges = snap.projectile.charges.raw
            _speed_integrated = snap.cooldown.integrated == true
            _speed_row5 = E._rows[5]._root:visible()

            managers.player._timers.replenish_grenades = {t = 1021}
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20})
            RT:update(managers.hud, 1.12, 0.06)
            snap = E:get_snapshot()
            _new_value = E._rows[4]._value:text()
            _new_ratio = E._rows[4]._recharge_reveal:h() / E._rows[4]._root:h()
            _new_charges = snap.projectile.charges.raw
            _new_integrated = snap.cooldown.integrated == true

            managers.player:_native_clear_replenish_timer()
            managers.player:_native_set_grenades('pocket', 2, 2)
            E:refresh(managers.hud)
            RT:update(managers.hud, 1.18, 0.06)
            snap = E:get_snapshot()
            _final_value = E._rows[4]._value:text()
            _final_charges = snap.projectile.charges.raw
            _final_integrated = snap.cooldown.integrated == true
            _final_reveal = E._rows[4]._recharge_reveal
            _final_reveal_visible = _final_reveal ~= nil and _final_reveal:visible()
            _final_oldstrip = E._rows[4]._track:visible() or E._rows[4]._fill:visible()
            _final_verified = E:verify()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._qualified), "precondition: valid event integrates")
        self.assertEqual(g._speed_value, '3s')
        self.assertLess(abs(float(g._speed_ratio) - 0.85), 0.02)
        self.assertEqual(float(g._speed_charges), 1.0)
        self.assertTrue(bool(g._speed_integrated))
        self.assertFalse(bool(g._speed_row5))
        self.assertEqual(g._new_value, '20s')
        self.assertLess(abs(float(g._new_ratio) - 0.0), 0.02)
        self.assertEqual(float(g._new_charges), 1.0)
        self.assertTrue(bool(g._new_integrated))
        self.assertEqual(g._final_value, '2')
        self.assertEqual(float(g._final_charges), 2.0)
        self.assertFalse(bool(g._final_integrated))
        self.assertFalse(bool(g._final_reveal_visible))
        self.assertFalse(bool(g._final_oldstrip))
        self.assertTrue(bool(g._final_verified))

    def test_event_lifecycle_invalidate_toggle_rebuild_and_active_isolation(self):
        lua = presentation()
        lua.execute(r'''
            E:invalidate()
            E:refresh(managers.hud)
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20})
            _after_invalidate = E:get_snapshot().cooldown.integrated == true

            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, nil)
            _off_integrated = E:get_snapshot().cooldown.integrated == true
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20})
            _on_integrated = E:get_snapshot().cooldown.integrated == true

            RT:rebuild(managers.hud)
            _rebuild_integrated = E:get_snapshot().cooldown.integrated == true
            _rebuild_value = E._rows[4]._value:text()

            dispatch(HUDManager, 'activate_teammate_ability_radial', managers.hud,
                HUDManager.PLAYER_PANEL, 8, 10)
            RT:update(managers.hud, 1, 0.06)
            _active_row = E._rows[6]._root:visible()
            _active_value = E._rows[6]._value:text()
            _active_row5 = E._rows[5]._root:visible()

            _game_clock:set_time(1002)
            RT:update(managers.hud, 1.06, 0.06)
            _active_advanced = E._rows[6]._value:text()

            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, nil)
            RT:update(managers.hud, 1.12, 0.06)
            local snap = E:get_snapshot()
            _cancel_integrated = snap.cooldown.integrated == true
            _cancel_value = E._rows[4]._value:text()
            _cancel_activity = snap.activity.known == true and snap.activity.active == true
            _cancel_active_row = E._rows[6]._root:visible()
            _cancel_row5 = E._rows[5]._root:visible()
            _cancel_verified = E:verify()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._after_invalidate))
        self.assertFalse(bool(g._off_integrated))
        self.assertTrue(bool(g._on_integrated))
        self.assertTrue(bool(g._rebuild_integrated))
        self.assertEqual(g._rebuild_value, '17s')
        self.assertTrue(bool(g._active_row))
        self.assertEqual(g._active_value, '8s')
        self.assertFalse(bool(g._active_row5))
        self.assertEqual(g._active_advanced, '6s')
        self.assertFalse(bool(g._cancel_integrated))
        self.assertEqual(g._cancel_value, '1')
        self.assertTrue(bool(g._cancel_activity))
        self.assertTrue(bool(g._cancel_active_row))
        self.assertFalse(bool(g._cancel_row5))
        self.assertTrue(bool(g._cancel_verified))

    def test_invalid_duration_unknown_kind_and_unknown_charges_preserve_counter(self):
        duration_events = [
            ('missing', '{}'),
            ('zero', '{duration = 0}'),
            ('nan', '{duration = 0 / 0}'),
            ('infinite', '{duration = math.huge}'),
        ]
        for name, event in duration_events:
            with self.subTest(case=name):
                lua = presentation()
                lua.execute(r'''
                    dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                        HUDManager.PLAYER_PANEL, ''' + event + r''')
                    RT:update(managers.hud, 1, 0.06)
                    local snap = E:get_snapshot()
                    _integrated = snap.cooldown.integrated == true
                    _value = E._rows[4]._value:text()
                    local reveal = E._rows[4]._recharge_reveal
                    _reveal_visible = reveal ~= nil and reveal:visible()
                    _oldstrip = E._rows[4]._track:visible() or E._rows[4]._fill:visible()
                    _row5 = E._rows[5]._root:visible()
                    _row5_value = E._rows[5]._value:text()
                    _verified = E:verify()
                ''')
                g = lua.globals()
                self.assertFalse(bool(g._integrated), name)
                self.assertEqual(g._value, '1', name)
                self.assertFalse(bool(g._reveal_visible), name)
                self.assertFalse(bool(g._oldstrip), name)
                self.assertTrue(bool(g._row5), name)
                self.assertEqual(g._row5_value, '17s', name)
                self.assertTrue(bool(g._verified), name)

        with self.subTest(case='unknown_kind'):
            lua = presentation()
            lua.execute(r'''
                _native_set_projectile_tweak('pocket', {base_cooldown = 30})
                E:refresh(managers.hud)
                dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                    HUDManager.PLAYER_PANEL, {duration = 20})
                RT:update(managers.hud, 1, 0.06)
                local snap = E:get_snapshot()
                _kind = snap.projectile.kind
                _integrated = snap.cooldown.integrated == true
                _value = E._rows[4]._value:text()
                local reveal = E._rows[4]._recharge_reveal
                _reveal_visible = reveal ~= nil and reveal:visible()
                _oldstrip = E._rows[4]._track:visible() or E._rows[4]._fill:visible()
                _row5 = E._rows[5]._root:visible()
                _verified = E:verify()
            ''')
            g = lua.globals()
            self.assertEqual(g._kind, 'unknown')
            self.assertFalse(bool(g._integrated))
            self.assertEqual(g._value, '1')
            self.assertFalse(bool(g._reveal_visible))
            self.assertFalse(bool(g._oldstrip))
            self.assertFalse(bool(g._row5))
            self.assertTrue(bool(g._verified))

        with self.subTest(case='unknown_charges'):
            lua = presentation()
            lua.execute(r'''
                managers.player.get_grenade_amount = function() return nil end
                E:refresh(managers.hud)
                dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                    HUDManager.PLAYER_PANEL, {duration = 20})
                RT:update(managers.hud, 1, 0.06)
                local snap = E:get_snapshot()
                _charges_known = snap.projectile.charges.known == true
                _integrated = snap.cooldown.integrated == true
                _value = E._rows[4]._value:text()
                local reveal = E._rows[4]._recharge_reveal
                _reveal_visible = reveal ~= nil and reveal:visible()
                _oldstrip = E._rows[4]._track:visible() or E._rows[4]._fill:visible()
                _row5 = E._rows[5]._root:visible()
                _row5_value = E._rows[5]._value:text()
                _verified = E:verify()
            ''')
            g = lua.globals()
            self.assertFalse(bool(g._charges_known))
            self.assertFalse(bool(g._integrated))
            self.assertEqual(g._value, '--')
            self.assertFalse(bool(g._reveal_visible))
            self.assertFalse(bool(g._oldstrip))
            self.assertTrue(bool(g._row5))
            self.assertEqual(g._row5_value, '17s')
            self.assertTrue(bool(g._verified))

    def test_clock_identity_and_backward_time_do_not_inherit_integration(self):
        lua = presentation()
        lua.execute(r'''
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20})
            RT:update(managers.hud, 1, 0.06)
            _qualified = E:get_snapshot().cooldown.integrated == true

            local fresh = {_time = 1000}
            function fresh:time() return self._time end
            function fresh:set_time(value) self._time = value end
            TimerManager.game = function() return fresh end
            _same_time_integrated = E:get_snapshot().cooldown.integrated == true
            fresh:set_time(1001)
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20})
            _clock_recovered = E:get_snapshot().cooldown.integrated == true
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._qualified))
        self.assertFalse(bool(g._same_time_integrated))
        self.assertTrue(bool(g._clock_recovered))

        lua = presentation()
        lua.execute(r'''
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20})
            RT:update(managers.hud, 1, 0.06)
            _qualified = E:get_snapshot().cooldown.integrated == true

            _game_clock:set_time(900)
            local immediate = E:get_snapshot().cooldown
            _back_immediate_unknown = immediate.known ~= true
            E:refresh(managers.hud)
            local after_poll = E:get_snapshot().cooldown
            _back_after_poll_unknown = after_poll.known ~= true
            _back_after_poll_integrated = after_poll.integrated == true

            _game_clock:set_time(1001)
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20})
            _back_recovered = E:get_snapshot().cooldown.integrated == true
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._qualified))
        self.assertTrue(bool(g._back_immediate_unknown))
        self.assertTrue(bool(g._back_after_poll_unknown))
        self.assertFalse(bool(g._back_after_poll_integrated))
        self.assertTrue(bool(g._back_recovered))

    def test_source_replacements_do_not_inherit_and_recover_with_new_event(self):
        cases = [
            ('unit', '''player_unit = {_alive = true}
                managers.player.player_unit = function() return player_unit end'''),
            ('player_manager', '''local old = managers.player
                managers.player = setmetatable({}, {__index = old})'''),
            ('session', '''local peer = native_local_peer
                local fresh = {}
                function fresh:local_peer() return peer end
                managers.network.session = function() return fresh end'''),
            ('registry', '''local record = managers.player._global.synced_grenades[1]
                managers.player._global.synced_grenades = {[1] = record}'''),
            ('projectile', '''_native_set_projectile_tweak('pocket2', {ability = true, base_cooldown = 30})
                managers.player:_native_set_grenades('pocket2', 1, 2)'''),
        ]
        for name, mutation in cases:
            with self.subTest(source=name):
                lua = presentation()
                lua.execute(r'''
                    dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                        HUDManager.PLAYER_PANEL, {duration = 20})
                    RT:update(managers.hud, 1, 0.06)
                    _qualified = E:get_snapshot().cooldown.integrated == true
                ''' + mutation + r'''
                    E:refresh(managers.hud)
                    local snap = E:get_snapshot()
                    _source_known = snap.source_known == true
                    _no_integrated = snap.cooldown.integrated ~= true
                    dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                        HUDManager.PLAYER_PANEL, {duration = 20})
                    _recovered = E:get_snapshot().cooldown.integrated == true
                ''')
                g = lua.globals()
                self.assertTrue(bool(g._qualified), name)
                self.assertTrue(bool(g._source_known), name)
                self.assertTrue(bool(g._no_integrated), name)
                self.assertTrue(bool(g._recovered), name)

    def test_mutation_loop_repairs_track_fill_and_value_on_same_primitives(self):
        lua = presentation()
        lua.execute(r'''
            dispatch(HUDManager, 'set_teammate_grenade_cooldown', managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20})
            RT:update(managers.hud, 1, 0.06)
            local row = E._rows[4]
            local root, value = row._root, row._value
            local reveal, reveal_bg = row._recharge_reveal, row._reveal_bg
            local function same()
                return E._rows[4] == row and E._rows[4]._root == root
                    and E._rows[4]._value == value
                    and E._rows[4]._recharge_reveal == reveal
                    and E._rows[4]._reveal_bg == reveal_bg
            end
            local mutations = {
                function() reveal:set_shape(reveal:x() + 5, reveal:y(), reveal:w(), reveal:h()) end,
                function() reveal:set_shape(reveal:x(), reveal:y() + 5, reveal:w(), reveal:h()) end,
                function() reveal:set_shape(reveal:x(), reveal:y(), reveal:w() + 5, reveal:h()) end,
                function() reveal:set_shape(reveal:x(), reveal:y(), reveal:w(), reveal:h() + 5) end,
                function() reveal_bg:set_shape(reveal_bg:x(), reveal_bg:y(), reveal_bg:w() + 5, reveal_bg:h()) end,
                function() reveal_bg:set_color(Color(0, 0, 0)) end,
                function() reveal_bg:set_alpha(.2) end,
                function() reveal_bg:set_visible(false) end,
                function() value:set_text('corrupt') end,
            }
            _positive = true
            _corrupt = true
            _repaired = true
            _same = true
            for i, mutate in ipairs(mutations) do
                if not E:verify() then _positive = false end
                mutate()
                if E:verify() then _corrupt = false end
                RT:update(managers.hud, 1 + i * 0.055, 0.055)
                if not E:verify() then _repaired = false end
                if not same() then _same = false end
            end
            _final = E:verify()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._positive))
        self.assertTrue(bool(g._corrupt))
        self.assertTrue(bool(g._repaired))
        self.assertTrue(bool(g._same))
        self.assertTrue(bool(g._final))

    def test_accepted_integration_keeps_cell_placements_through_finish(self):
        lua = presentation()
        lua.execute(r'''
            tweak_data.hud_icons = tweak_data.hud_icons or {}
            function tweak_data.hud_icons:get_icon_data(id)
                if id == "frag_grenade" then
                    return "guis/textures/pd2/equip_icons", {128, 0, 32, 32}
                end
            end
            tweak_data.blackmarket.projectiles.pocket.icon = "frag_grenade"
            DB = DB or {has = function() return true end}
            Idstring = Idstring or function(value) return value end
            E:refresh_settings(managers.hud)

            local function placement(index)
                local row = E._rows[index]
                return {
                    x = E._root:x() + row._root:x(),
                    y = E._root:y() + row._root:y(),
                    w = row._root:w(),
                    h = row._root:h(),
                }
            end
            local function same_placement(a, b)
                return math.abs(a.x - b.x) <= .05
                    and math.abs(a.y - b.y) <= .05
                    and math.abs(a.w - b.w) <= .05
                    and math.abs(a.h - b.h) <= .05
            end
            local function fitted(row)
                local _, _, tw, th = row._value:text_rect()
                if type(tw) ~= "number" or type(th) ~= "number"
                    or tw ~= tw or th ~= th then return false end
                local value = row._value
                return tw <= value:w() + .05 and th <= value:h() + .05
                    and value:x() >= -.05 and value:x() + value:w() <= row._root:w() + .05
                    and value:y() >= -.05 and value:y() + value:h() <= row._root:h() + .05
            end

            local expected = {}
            for i = 1, 4 do expected[i] = placement(i) end
            local stable_text = {
                E._rows[1]._value:text(), E._rows[2]._value:text(), E._rows[3]._value:text()
            }
            local before = E:get_snapshot()
            local charges = before.projectile.charges.raw
            local cables = before.cables.raw
            local trip = before.deployables.trip_mine.quantities[1].raw
            local trip2 = before.deployables.trip_mine.quantities[2].raw
            local doctor = before.deployables.doctor_bag.quantities[1].raw
            local row4 = E._rows[4]
            local icon = row4._icon
            local descriptor = row4._icon_descriptor
            local selected = row4._selected
            assert(icon and descriptor and icon:visible(), "precondition: row4 icon")
            assert(selected == false, "precondition: row4 selection")
            assert(E._rows[5]._root:visible() and row4._value:text() == "1",
                "precondition: initial fallback counter with separate RECHARGE")

            local function assert_state(tag, value)
                assert(E:verify(), tag .. ": equipment must stay certified")
                for i = 1, 4 do
                    assert(same_placement(expected[i], placement(i)),
                        tag .. ": row" .. i .. " world placement must stay stable")
                end
                for i = 1, 3 do
                    assert(E._rows[i]._value:text() == stable_text[i],
                        tag .. ": row" .. i .. " quantity must stay unchanged")
                end
                assert(E._rows[4]._value:text() == value, tag .. ": row4 value " .. value)
                assert(fitted(E._rows[4]), tag .. ": row4 value must fit its body")
            end

            dispatch(HUDManager, "set_teammate_grenade_cooldown", managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20, end_time = 1017})
            RT:update(managers.hud, 1, .06)

            local snap = E:get_snapshot()
            assert(snap.cooldown.integrated == true and snap.cooldown.remaining == 17,
                "qualified 20s event with 17s remaining must integrate")
            local reveal = E._rows[4]._recharge_reveal
            assert(reveal and reveal:visible(), "integrated progress reveal must be visible")
            assert(not E._rows[4]._track:visible() and not E._rows[4]._fill:visible(),
                "old strip must stay hidden")
            assert(not E._rows[5]._root:visible(), "separate RECHARGE must be hidden")
            assert(E._rows[4]._icon == icon and E._rows[4]._icon_descriptor == descriptor
                and E._rows[4]._selected == selected and icon:visible(),
                "row4 icon and selection must be preserved")
            assert(snap.projectile.charges.raw == charges, "charges must stay unchanged")
            assert(snap.cables.raw == cables, "cables must stay unchanged")
            assert(snap.deployables.trip_mine.quantities[1].raw == trip
                and snap.deployables.trip_mine.quantities[2].raw == trip2
                and snap.deployables.doctor_bag.quantities[1].raw == doctor,
                "deployable quantities must stay unchanged")
            assert_state("17s", "17s")

            _game_clock:set_time(1008)
            RT:update(managers.hud, 1.06, .06)

            snap = E:get_snapshot()
            assert(snap.cooldown.integrated == true and snap.cooldown.remaining == 9,
                "accepted event must advance to 9s")
            assert_state("9s", "9s")

            managers.player:_native_clear_replenish_timer()
            dispatch(HUDManager, "set_teammate_grenade_cooldown", managers.hud,
                HUDManager.PLAYER_PANEL, nil)
            RT:update(managers.hud, 1.12, .06)

            snap = E:get_snapshot()
            assert(snap.cooldown.integrated ~= true, "nil timer must end integration")
            assert(not reveal:visible(), "reveal hidden but retained after finish")
            assert(reveal == E._rows[4]._recharge_reveal, "reveal not destroyed after finish")
            assert(not E._rows[4]._track:visible() and not E._rows[4]._fill:visible(),
                "old strip must hide after finish")
            assert(E._rows[4]._icon == icon and E._rows[4]._icon_descriptor == descriptor
                and E._rows[4]._selected == selected,
                "row4 icon and selection must survive finish")
            assert_state("counter", "1")
            assert(snap.projectile.charges.raw == charges, "finish must retain charges")
        ''')

    def test_actual_setting_toggle_captures_qualified_event_and_activity(self):
        lua = presentation()
        lua.execute(r'''
            _game_clock:set_time(1000)
            managers.player:_native_set_replenish_timer(1017)
            kyohud.settings.enable_equipment = false
            RT:refresh_settings(managers.hud)
            assert(not E._root and not E._mounted, "disabled setting must unmount equipment")

            dispatch(HUDManager, "set_teammate_grenade_cooldown", managers.hud,
                HUDManager.PLAYER_PANEL, {duration = 20, end_time = 1017})
            dispatch(HUDManager, "activate_teammate_ability_radial", managers.hud,
                HUDManager.PLAYER_PANEL, 8, 10)
            local event = E._cooldown_event
            local activity = E._activity
            assert(type(event) == "table" and event.duration == 20 and not event.cancelled,
                "qualified event must be captured while the option is off")
            assert(type(activity) == "table" and activity.known == true
                and activity.active == true and activity.remaining == 8,
                "active ability must be captured while the option is off")
            _game_clock:set_time(1005)
            kyohud.settings.enable_equipment = true
            RT:refresh_settings(managers.hud)
            assert(E._root and E:verify(), "enabling must mount certified equipment")

            local snap = E:get_snapshot()
            assert(snap.cooldown.integrated == true, "captured event must integrate on enable")
            assert(snap.cooldown.remaining == 12 and snap.cooldown.active == true,
                "remaining must follow the advanced native timer")
            assert(E._rows[4]._value:text() == "12s", "row4 must show correct remaining")
            local reveal = E._rows[4]._recharge_reveal
            assert(reveal and reveal:visible(), "integrated reveal must be visible")
            local ratio = reveal:h() / E._rows[4]._root:h()
            assert(math.abs(ratio - (1 - 12 / 20)) < .02, "integrated progress ratio " .. ratio)
            assert(not E._rows[5]._root:visible(), "separate RECHARGE must stay hidden")
            assert(snap.activity.known == true and snap.activity.active == true
                and snap.activity.remaining == 3, "captured ACTIVE must retain remaining")
            assert(E._rows[6]._root:visible() and E._rows[6]._value:text() == "3s",
                "ACTIVE row must be retained after late mount")
            assert(snap.projectile.charges.raw == 1, "counter quantity must be retained")
        ''')

    def test_initial_late_mount_without_event_keeps_counter_and_separate_fallback(self):
        lua = presentation()
        lua.execute(r'''
            _game_clock:set_time(1000)
            managers.player:_native_set_replenish_timer(1017)
            kyohud.settings.enable_equipment = false
            RT:refresh_settings(managers.hud)
            assert(not E._root and not E._mounted, "disabled setting must unmount equipment")
            assert(E._cooldown_event == nil, "precondition: no qualified event")
            _game_clock:set_time(1005)
            kyohud.settings.enable_equipment = true
            RT:refresh_settings(managers.hud)
            assert(E._root and E:verify(), "late mount must certify")

            local snap = E:get_snapshot()
            assert(snap.cooldown.integrated ~= true, "no event must not integrate")
            assert(snap.cooldown.known == true and snap.cooldown.active == true
                and snap.cooldown.remaining == 12, "native cooldown must remain measurable")
            assert(E._rows[4]._value:text() == "1", "late mount must retain counter")
            assert(E._rows[5]._root:visible(), "no event must keep separate RECHARGE fallback")
            assert(E._rows[5]._label:text() == "RECHARGE", "separate fallback label")
            assert(E._rows[5]._value:text() == "12s", "separate fallback remaining")
            assert(not E._rows[6]._root:visible(), "no captured ACTIVE must stay hidden")
            assert(snap.projectile.charges.raw == 1, "counter quantity must remain 1")
        ''')


if __name__ == '__main__':
    unittest.main()
