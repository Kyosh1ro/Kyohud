"""Sixth Sense buff lifecycle regressions.

Invokes the actual native _update_omniscience method through real Pre/PostHook
wrapping with stubbed Diesel boundaries. The native body is copied verbatim
from the authoritative source (provenance below) so the test exercises the
real timing semantics: warmup, scan, deadline advancement, and detection map
expiry.

Provenance of native fixture:
  G:/PD2-Modding-Docs/Payday-2-LuaJIT-Complete-master/lib/units/beings/player/states/playerstandard.lua
  lines 4556-4630
"""
import json
import sys
import unittest
from pathlib import Path

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]
HUDLIST = (ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig")

NATIVE_OMNISCIENCE = r'''
function PlayerStandard:_update_omniscience(t, dt)
    local omniscience_settings = tweak_data.player.omniscience
    if not omniscience_settings then
        return
    end
    local action_forbidden = not managers.player:has_category_upgrade("player", "standstill_omniscience") or managers.player:current_state() == "civilian" or self:_interacting() or self._ext_movement:has_carry_restriction() or self:is_deploying() or self:_is_throwing_projectile() or self:_is_meleeing() or self:_on_zipline() or self:running() or self:in_air() or self:shooting() or not managers.groupai:state():whisper_mode()
    if action_forbidden then
        if self._state_data.omniscience_t then
            self._state_data.omniscience_t = nil
            self._state_data.omniscience_pos = nil
        end
        return
    end
    local player_m_pos = self._unit:movement():m_pos()
    if not player_m_pos then
        return
    end
    if self._moving then
        if self._state_data.omniscience_pos and mvec3_dis_sq(player_m_pos, self._state_data.omniscience_pos) > omniscience_settings.sense_exit_sq then
            self._state_data.omniscience_t = nil
            self._state_data.omniscience_pos = nil
            self._state_data.omniscience_units_detected = nil
            return
        end
        if not self._state_data.omniscience_pos then
            return
        end
    end
    if not self._moving and not self._state_data.omniscience_pos then
        self._state_data.omniscience_pos = self._state_data.omniscience_pos or Vector3()
        mvec3_set(self._state_data.omniscience_pos, player_m_pos)
    end
    if not self._state_data.omniscience_t then
        self._state_data.omniscience_t = t + omniscience_settings.start_t
    end
    if self._state_data.omniscience_pos and t >= self._state_data.omniscience_t then
        local sensed_targets = World:find_units_quick("sphere", player_m_pos, omniscience_settings.sense_radius, managers.slot:get_mask("trip_mine_targets"))
        for _, unit in ipairs(sensed_targets) do
            if alive(unit) and not unit:base():char_tweak().is_escort then
                self._state_data.omniscience_units_detected = self._state_data.omniscience_units_detected or {}
                local unit_detected = self._state_data.omniscience_units_detected[unit:key()]
                if not unit_detected or unit_detected <= t then
                    unit_detected = t + omniscience_settings.target_resense_t
                    self._state_data.omniscience_units_detected[unit:key()] = unit_detected
                    managers.game_play_central:auto_highlight_enemy(unit, true)
                    break
                end
            end
        end
        self._state_data.omniscience_t = t + omniscience_settings.interval_t
        if self._state_data.omniscience_pos then
            mvec3_set(self._state_data.omniscience_pos, player_m_pos)
        end
    end
end
'''


def make_runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute('''
        kyohud = {settings = {}}
        Kyosh1roHUD = kyohud
        RequiredScript = "lib/units/beings/player/states/playerstandard"
        Application = {time = function() return 0 end}
        Hooks = {installed = {}, _pre = {}, _post = {}}
        function Hooks:PostHook(class, method, id, callback)
            self.installed[#self.installed + 1] = {"post", method, id}
            if not self._post[method] then self._post[method] = {} end
            self._post[method][#self._post[method] + 1] = callback
        end
        function Hooks:PreHook(class, method, id, callback)
            self.installed[#self.installed + 1] = {"pre", method, id}
            if not self._pre[method] then self._pre[method] = {} end
            self._pre[method][#self._pre[method] + 1] = callback
        end
        PlayerStandard = {}
    ''')
    lua.execute(NATIVE_OMNISCIENCE)
    lua.execute('''
        local native_body = PlayerStandard._update_omniscience
        PlayerStandard._update_omniscience = function(self, t, dt)
            local pre_cbs = Hooks._pre["_update_omniscience"]
            if pre_cbs then for _, cb in ipairs(pre_cbs) do cb(self, t, dt) end end
            native_body(self, t, dt)
            local post_cbs = Hooks._post["_update_omniscience"]
            if post_cbs then for _, cb in ipairs(post_cbs) do cb(self, t, dt) end end
        end
        PlayerStandard.exit = function(self, state_data, new_state_name)
            local post_cbs = Hooks._post["exit"]
            if post_cbs then for _, cb in ipairs(post_cbs) do cb(self, state_data, new_state_name) end end
        end
    ''')
    lua.execute(HUDLIST)
    return lua


def setup_player(lua):
    lua.execute('''
        function Vector3() return {x=0,y=0,z=0} end
        function alive(u) return u ~= nil end
        player = {
            _state_data = {},
            _unit = {movement = function() return {m_pos = function() return {x=0,y=0,z=0} end} end},
            _ext_movement = {has_carry_restriction = function() return false end},
            _interacting = function() return false end,
            is_deploying = function() return false end,
            _is_throwing_projectile = function() return false end,
            _is_meleeing = function() return false end,
            _on_zipline = function() return false end,
            running = function() return false end,
            in_air = function() return false end,
            shooting = function() return false end,
        }
        setmetatable(player, {__index = PlayerStandard})
        tweak_data = {player = {omniscience = {
            start_t = 2, interval_t = 1, sense_radius = 500,
            target_resense_t = 5, sense_exit_sq = 10000
        }}}
        managers = {
            player = {
                has_category_upgrade = function() return true end,
                current_state = function() return "standard" end
            },
            groupai = {state = function() return {whisper_mode = function() return true end} end},
            game_play_central = {auto_highlight_enemy = function() end},
            slot = {get_mask = function() return 1 end}
        }
        mvec3_set = function(dst, src) dst.x, dst.y, dst.z = src.x, src.y, src.z end
        mvec3_dis_sq = function(a, b) return 0 end
        World = {find_units_quick = function() return {} end}
    ''')


def call_native(lua, t, dt=0.016):
    lua.execute(f"player:_update_omniscience({t}, {dt})")


def get_count(lua):
    return lua.eval('''
        (function()
            local buff = kyohud.hudlist:get_buffs().sixth_sense
            return buff and buff.value or nil
        end)()
    ''')


class SixthSenseNativeRegressionTests(unittest.TestCase):

    def test_hooks_registered(self):
        lua = make_runtime()
        methods = []
        count = lua.eval("#Hooks.installed")
        for i in range(1, count + 1):
            entry = lua.eval(f"Hooks.installed[{i}]")
            methods.append((str(entry[1]), str(entry[2]), str(entry[3])))
        self.assertIn(("pre", "_update_omniscience", "KyoHUD_HUDList_SixthSensePreObserve"), methods)
        self.assertIn(("post", "_update_omniscience", "KyoHUD_HUDList_SixthSenseObserve"), methods)
        self.assertIn(("post", "exit", "KyoHUD_HUDList_SixthSenseExit"), methods)

    def test_native_progression_warmup_then_targets(self):
        """t=0 warmup→0, t=2 first target→1, t=3 second target→2, persist between scans."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            World.find_units_quick = function()
                return {{
                    alive = function() return true end,
                    base = function() return {char_tweak = function() return {is_escort = false} end} end,
                    key = function() return "enemy1" end
                }}
            end
        ''')
        call_native(lua, 0)
        self.assertEqual(get_count(lua), 0, "warmup at t=0 must show 0")
        call_native(lua, 2)
        self.assertEqual(get_count(lua), 1, "first scan at t=2 must find 1 target")
        lua.execute('''
            World.find_units_quick = function()
                return {
                    {alive = function() return true end,
                     base = function() return {char_tweak = function() return {is_escort = false} end} end,
                     key = function() return "enemy1" end},
                    {alive = function() return true end,
                     base = function() return {char_tweak = function() return {is_escort = false} end} end,
                     key = function() return "enemy2" end}
                }
            end
        ''')
        call_native(lua, 3)
        self.assertEqual(get_count(lua), 2, "second scan at t=3 must find 2 targets")
        call_native(lua, 3.5)
        self.assertEqual(get_count(lua), 2, "between scans count must persist at 2")

    def test_no_extra_world_scans(self):
        """World:find_units_quick called only during native scan, not by hooks."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            kyohud._world_scan_count = 0
            local orig = World.find_units_quick
            World.find_units_quick = function(...)
                kyohud._world_scan_count = kyohud._world_scan_count + 1
                return {}
            end
        ''')
        call_native(lua, 0)
        call_native(lua, 0.5)
        call_native(lua, 1.0)
        count_before_scan = lua.eval("kyohud._world_scan_count")
        self.assertEqual(count_before_scan, 0, "warmup phase must not trigger World scan")
        call_native(lua, 2)
        count_after_scan = lua.eval("kyohud._world_scan_count")
        self.assertEqual(count_after_scan, 1, "exactly one scan at t=2 (native deadline)")

    def test_no_contour_calls_from_hooks(self):
        """Hooks must not call auto_highlight_enemy; only native scan does."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            kyohud._contour_count = 0
            managers.game_play_central.auto_highlight_enemy = function()
                kyohud._contour_count = kyohud._contour_count + 1
            end
            World.find_units_quick = function()
                return {{
                    alive = function() return true end,
                    base = function() return {char_tweak = function() return {is_escort = false} end} end,
                    key = function() return "enemy1" end
                }}
            end
        ''')
        call_native(lua, 0)
        self.assertEqual(lua.eval("kyohud._contour_count"), 0)
        call_native(lua, 2)
        self.assertEqual(lua.eval("kyohud._contour_count"), 1,
                         "only native scan calls auto_highlight_enemy")

    def test_dedup_same_unit_across_scans(self):
        """Same unit detected twice does not double count."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            World.find_units_quick = function()
                return {{
                    alive = function() return true end,
                    base = function() return {char_tweak = function() return {is_escort = false} end} end,
                    key = function() return "enemy1" end
                }}
            end
        ''')
        call_native(lua, 0)
        call_native(lua, 2)
        self.assertEqual(get_count(lua), 1)
        call_native(lua, 3)
        self.assertEqual(get_count(lua), 1, "same unit must not be counted twice")

    def test_expiry_boundary(self):
        """Expired detection entries are not counted."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            World.find_units_quick = function()
                return {{
                    alive = function() return true end,
                    base = function() return {char_tweak = function() return {is_escort = false} end} end,
                    key = function() return "enemy1" end
                }}
            end
        ''')
        call_native(lua, 0)
        call_native(lua, 2)
        self.assertEqual(get_count(lua), 1)
        lua.execute('World.find_units_quick = function() return {} end')
        call_native(lua, 7.0)
        self.assertEqual(get_count(lua), 0,
                         "entry with expire_t=2+5=7 must expire at t=7 (strict >)")

    def test_no_targets_zero(self):
        """Scan with no enemies yields zero."""
        lua = make_runtime()
        setup_player(lua)
        call_native(lua, 0)
        call_native(lua, 2)
        self.assertEqual(get_count(lua), 0)

    def test_toggle_false_clears(self):
        """Settings.sixth_sense = false clears buff."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            World.find_units_quick = function()
                return {{
                    alive = function() return true end,
                    base = function() return {char_tweak = function() return {is_escort = false} end} end,
                    key = function() return "enemy1" end
                }}
            end
        ''')
        call_native(lua, 0)
        call_native(lua, 2)
        self.assertEqual(get_count(lua), 1)
        lua.execute("kyohud.settings.sixth_sense = false")
        call_native(lua, 3)
        self.assertIsNone(get_count(lua))

    def test_forbidden_then_restart(self):
        """Active→forbidden→restart: warmup shows 0 even with stale native map."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            World.find_units_quick = function()
                return {{
                    alive = function() return true end,
                    base = function() return {char_tweak = function() return {is_escort = false} end} end,
                    key = function() return "enemy1" end
                }}
            end
        ''')
        call_native(lua, 0)
        call_native(lua, 2)
        self.assertEqual(get_count(lua), 1)
        lua.execute("managers.player.has_category_upgrade = function() return false end")
        call_native(lua, 2.5)
        self.assertIsNone(get_count(lua), "forbidden must clear buff")
        lua.execute("managers.player.has_category_upgrade = function() return true end")
        call_native(lua, 3)
        self.assertEqual(get_count(lua), 0, "new warmup must show 0 despite stale map")
        call_native(lua, 5)
        self.assertEqual(get_count(lua), 1, "scan after restart must find target")

    def test_movement_clears_from_active(self):
        """Movement beyond tolerance clears detection from active state."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            World.find_units_quick = function()
                return {{
                    alive = function() return true end,
                    base = function() return {char_tweak = function() return {is_escort = false} end} end,
                    key = function() return "enemy1" end
                }}
            end
        ''')
        call_native(lua, 0)
        call_native(lua, 2)
        self.assertEqual(get_count(lua), 1)
        lua.execute('''
            player._moving = true
            mvec3_dis_sq = function(a, b) return 20000 end
        ''')
        call_native(lua, 3)
        self.assertIsNone(get_count(lua))

    def test_exit_deactivates_and_clears(self):
        """Exit from active deactivates buff and clears cache."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            World.find_units_quick = function()
                return {{
                    alive = function() return true end,
                    base = function() return {char_tweak = function() return {is_escort = false} end} end,
                    key = function() return "enemy1" end
                }}
            end
        ''')
        call_native(lua, 0)
        call_native(lua, 2)
        self.assertEqual(get_count(lua), 1)
        lua.execute("Hooks._post['exit'][1](player, player._state_data, 'driving')")
        self.assertIsNone(get_count(lua))

    def test_exit_does_not_mutate_native_state(self):
        """Exit hook must not modify omniscience_t/pos/units_detected."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            World.find_units_quick = function()
                return {{
                    alive = function() return true end,
                    base = function() return {char_tweak = function() return {is_escort = false} end} end,
                    key = function() return "enemy1" end
                }}
            end
        ''')
        call_native(lua, 0)
        call_native(lua, 2)
        lua.execute('''
            local saved_t = player._state_data.omniscience_t
            local saved_pos = player._state_data.omniscience_pos
            local saved_units = player._state_data.omniscience_units_detected
            Hooks._post['exit'][1](player, player._state_data, 'driving')
            assert(player._state_data.omniscience_t == saved_t, "exit must not mutate omniscience_t")
            assert(player._state_data.omniscience_pos == saved_pos, "exit must not mutate omniscience_pos")
            assert(player._state_data.omniscience_units_detected == saved_units, "exit must not mutate units_detected")
        ''')

    def test_reset_then_reactivation(self):
        """Provider:reset clears cache so reactivation can emit even with same count."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            World.find_units_quick = function()
                return {{
                    alive = function() return true end,
                    base = function() return {char_tweak = function() return {is_escort = false} end} end,
                    key = function() return "enemy1" end
                }}
            end
            kyohud._notify_count = 0
            local orig_event = kyohud.hudlist.event
            kyohud.hudlist.event = function(self, source, event, id, data)
                if id == "sixth_sense" and event == "activate" then
                    kyohud._notify_count = kyohud._notify_count + 1
                end
                return orig_event(self, source, event, id, data)
            end
        ''')
        call_native(lua, 0)
        call_native(lua, 2)
        self.assertEqual(get_count(lua), 1)
        initial_notifies = lua.eval("kyohud._notify_count")
        lua.execute("kyohud.hudlist:reset()")
        self.assertIsNone(get_count(lua))
        call_native(lua, 3)
        self.assertEqual(get_count(lua), 1)
        self.assertGreater(lua.eval("kyohud._notify_count"), initial_notifies,
                           "reactivation after reset must re-emit")

    def test_idempotence_same_count_no_redundant_event(self):
        """Same count across frames emits activate only once."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            World.find_units_quick = function()
                return {{
                    alive = function() return true end,
                    base = function() return {char_tweak = function() return {is_escort = false} end} end,
                    key = function() return "enemy1" end
                }}
            end
        ''')
        call_native(lua, 0)
        call_native(lua, 2)
        self.assertEqual(get_count(lua), 1)
        lua.execute('''
            kyohud._notify_count = 0
            local orig_event = kyohud.hudlist.event
            kyohud.hudlist.event = function(self, source, event, id, data)
                if id == "sixth_sense" and event == "activate" then
                    kyohud._notify_count = kyohud._notify_count + 1
                end
                return orig_event(self, source, event, id, data)
            end
        ''')
        call_native(lua, 2.5)
        call_native(lua, 2.9)
        call_native(lua, 3.0)
        self.assertEqual(lua.eval("kyohud._notify_count"), 0,
                         "same count must emit no additional activates")

    def test_inactive_no_repeated_deactivate(self):
        """Inactive state does not emit repeated no-op deactivates."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            kyohud._deactivate_count = 0
            local orig_event = kyohud.hudlist.event
            kyohud.hudlist.event = function(self, source, event, id, data)
                if id == "sixth_sense" and event == "deactivate" then
                    kyohud._deactivate_count = kyohud._deactivate_count + 1
                end
                return orig_event(self, source, event, id, data)
            end
            managers.player.has_category_upgrade = function() return false end
        ''')
        call_native(lua, 0)
        first = lua.eval("kyohud._deactivate_count")
        call_native(lua, 0.5)
        call_native(lua, 1.0)
        self.assertEqual(lua.eval("kyohud._deactivate_count"), first,
                         "inactive must not emit repeated deactivates")

    def test_hook_idempotence_repeated_chunk_load(self):
        """Loading HUDLIST chunk multiple times installs each hook exactly once."""
        lua = make_runtime()
        setup_player(lua)
        initial_count = lua.eval("#Hooks.installed")
        lua.execute(HUDLIST)
        lua.execute(HUDLIST)
        self.assertEqual(lua.eval("#Hooks.installed"), initial_count,
                         "repeated HUDLIST load must not install duplicate hooks")

    def test_active_to_loud_clears(self):
        """Transition from active state to loud mode clears buff."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            World.find_units_quick = function()
                return {{
                    alive = function() return true end,
                    base = function() return {char_tweak = function() return {is_escort = false} end} end,
                    key = function() return "enemy1" end
                }}
            end
        ''')
        call_native(lua, 0)
        call_native(lua, 2)
        self.assertEqual(get_count(lua), 1, "active state with target")
        lua.execute("managers.groupai.state = function() return {whisper_mode = function() return false end} end")
        call_native(lua, 3)
        self.assertIsNone(get_count(lua), "loud mode must clear buff")

    def test_active_to_interaction_clears(self):
        """Transition from active state to interaction clears buff."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            World.find_units_quick = function()
                return {{
                    alive = function() return true end,
                    base = function() return {char_tweak = function() return {is_escort = false} end} end,
                    key = function() return "enemy1" end
                }}
            end
        ''')
        call_native(lua, 0)
        call_native(lua, 2)
        self.assertEqual(get_count(lua), 1, "active state with target")
        lua.execute("player._interacting = function() return true end")
        call_native(lua, 3)
        self.assertIsNone(get_count(lua), "interaction must clear buff")

    def test_disabled_option_no_redundant_events(self):
        """Disabled option must not emit repeated deactivate events."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            kyohud.settings.sixth_sense = false
            kyohud._deactivate_count = 0
            local orig_event = kyohud.hudlist.event
            kyohud.hudlist.event = function(self, source, event, id, data)
                if id == "sixth_sense" and event == "deactivate" then
                    kyohud._deactivate_count = kyohud._deactivate_count + 1
                end
                return orig_event(self, source, event, id, data)
            end
        ''')
        call_native(lua, 0)
        first = lua.eval("kyohud._deactivate_count")
        call_native(lua, 0.5)
        call_native(lua, 1.0)
        call_native(lua, 1.5)
        self.assertEqual(lua.eval("kyohud._deactivate_count"), first,
                         "disabled option must not emit repeated deactivates")

    def test_exit_removes_cache_entry(self):
        """Exit must remove cache entry entirely, not leave empty table."""
        lua = make_runtime()
        setup_player(lua)
        lua.execute('''
            World.find_units_quick = function()
                return {{
                    alive = function() return true end,
                    base = function() return {char_tweak = function() return {is_escort = false} end} end,
                    key = function() return "enemy1" end
                }}
            end
        ''')
        call_native(lua, 0)
        call_native(lua, 2)
        self.assertEqual(get_count(lua), 1, "active state with target")
        lua.execute("PlayerStandard.exit(player, player._state_data, 'driving')")
        self.assertFalse(lua.eval("kyohud._sixth_sense_cache[player] ~= nil"),
                         "cache entry must be removed, not left as empty table")


class SixthSenseRendererIntegrationTests(unittest.TestCase):

    def make_presentation_runtime(self):
        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.execute('''
            kyohud = {}; Kyosh1roHUD = kyohud
            RequiredScript = "lib/managers/hudmanagerpd2"
            Hooks = {callbacks = {}, _pre = {}, _post = {}}
            function Hooks:PostHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:PreHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:Add(...) end
            HUDManager = {}; PlayerManager = {}; managers = {}; tweak_data = {}
            function Vector3(...) return {...} end
            function log(...) end
            function alive(value) return value ~= nil end
            function Idstring(value) return value end
            DB = {has = function() return true end}
            local function color() return {with_alpha = function(self) return self end} end
            Color = setmetatable({white = color(), black = color()}, {
                __call = function(...) return color() end,
            })
            TimerManager = {game = function()
                return {time = function() return 100 end}
            end}
            Application = {time = function() return 100 end}
        ''')
        lua.execute((ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig"))
        lua.execute((ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig"))
        lua.execute((ROOT / "lua" / "ky_buff_render.lua").read_text(encoding="utf-8-sig"))
        lua.execute((ROOT / "lua" / "ky_hud_banners.lua").read_text(encoding="utf-8-sig"))
        lua.execute('kyohud.settings = {enable_buffs = true}')
        return lua

    def test_renderer_value_text_zero_and_two(self):
        lua = self.make_presentation_runtime()
        lua.execute('''
            assert(kyohud:TryRegisterGameInfoBridge() == true)
            kyohud.hudlist:event("buff", "activate", "sixth_sense", {value = 0})
            assert(kyohud._buffs.sixth_sense ~= nil)
            assert(kyohud._buffs.sixth_sense.value_text == nil,
                "value_text for 0 must be nil (hidden), got: " .. tostring(kyohud._buffs.sixth_sense.value_text))
            kyohud.hudlist:event("buff", "activate", "sixth_sense", {value = 2})
            assert(kyohud._buffs.sixth_sense.value_text == "2",
                "value_text for 2 must be '2', got: " .. tostring(kyohud._buffs.sixth_sense.value_text))
            kyohud.hudlist:event("buff", "activate", "sixth_sense", {value = 0})
            assert(kyohud._buffs.sixth_sense.value_text == nil,
                "value_text must clear to nil on return to 0, got: " .. tostring(kyohud._buffs.sixth_sense.value_text))
        ''')


class SixthSenseMenuSingletonTests(unittest.TestCase):

    def setUp(self):
        self.menu = json.loads((ROOT / "menu" / "buffs_ghost.json").read_text("utf-8-sig"))

    def test_singleton_sixth_sense_option(self):
        ids = [item["id"] for item in self.menu["items"] if "sixth_sense" in item.get("value", "")]
        self.assertEqual(ids, ["ky_buff_sixth_sense"])

    def test_no_old_sixth_sense_in_menu(self):
        ids = [item["id"] for item in self.menu["items"]]
        self.assertNotIn("ky_buff_old_sixth_sense", ids)


class SixthSenseLocalizationTests(unittest.TestCase):

    def test_english_description_mentions_count(self):
        loc = json.loads((ROOT / "loc" / "english.json").read_text("utf-8-sig"))
        self.assertIn("count", loc["ky_opt_buff_sixth_sense_desc"].lower())

    def test_french_description_mentions_count(self):
        loc = json.loads((ROOT / "loc" / "french.json").read_text("utf-8-sig"))
        self.assertIn("nombre", loc["ky_opt_buff_sixth_sense_desc"].lower())

    def test_fallback_description_mentions_count(self):
        content = (ROOT / "lua" / "ky_localization.lua").read_text("utf-8-sig")
        self.assertIn("count", content.lower())


class SixthSenseSavedFalseTests(unittest.TestCase):
    """Real KH.Load() preserves sixth_sense=false and ignores removed old_sixth_sense."""

    def _load_options_with_fixture(self, save_dir):
        import tempfile
        from pathlib import Path
        OPTIONS_CHUNK = (ROOT / "lua" / "ky_options.lua").read_text(encoding="utf-8-sig")

        settings_path = Path(save_dir) / "kyohud_settings.json"
        settings_path.write_text('{"sixth_sense": false, "old_sixth_sense": true}')

        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + "/"
        lua.globals().SavePath = Path(save_dir).as_posix() + "/"
        lua.execute(r'''
            kyohud = nil
            Kyosh1roHUD = nil
            MenuCallbackHandler = {}
            Hooks = {callbacks = {}}
            function Hooks:Add(event, id, callback) self.callbacks[id] = callback end
            MenuHelper = {}
            BLT = nil
            function log(...) end
            function dofile(...) return true end
            json = {}
            function json.encode(data) return "{}" end
            function json.decode(raw)
                return {sixth_sense = false, old_sixth_sense = true}
            end
        ''')
        lua.execute(OPTIONS_CHUNK)
        return lua

    def test_saved_false_preserved_on_load(self):
        import tempfile
        with tempfile.TemporaryDirectory() as save_dir:
            lua = self._load_options_with_fixture(save_dir)
            self.assertFalse(lua.eval("kyohud.settings.sixth_sense"),
                             "saved sixth_sense=false must be preserved")
            self.assertIsNone(lua.eval("kyohud.settings.old_sixth_sense"),
                              "removed old_sixth_sense default must not appear in settings")
            self.assertFalse(lua.eval(
                "kyohud._defaults.old_sixth_sense ~= nil"),
                "old_sixth_sense must not be in _defaults")

    def test_removed_callback_not_installed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as save_dir:
            lua = self._load_options_with_fixture(save_dir)
            has_old_cb = lua.eval(
                "Hooks.callbacks['KY_ToggleBuff_old_sixth_sense'] ~= nil")
            self.assertFalse(has_old_cb,
                             "removed old_sixth_sense callback must not be installed")


if __name__ == '__main__':
    unittest.main()
