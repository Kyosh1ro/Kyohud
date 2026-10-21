"""Regression test for combat panel resize behavior.

Verifies ensure_panel(false) resizes the SAME root when parent dimensions change.
Expected RED: panel retains stale 1280x720 instead of tracking parent resize.

Run: uv run --with lupa python -B -m unittest discover -s .github -p test_combat_panel_resize.py -v
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class CombatPanelResizeTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + "/"
        self.lua.execute('''
            Hooks = {callbacks = {}}
            function Hooks:PostHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:PreHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:Add(...) end

            HUDManager = {}; PlayerManager = {}; managers = {}; tweak_data = {}
            function Vector3(...) return {...} end
            function log(...) end
            function alive(x) return x ~= nil end
            Color = setmetatable({white = {}, black = {}}, {
                __call = function(...) return {} end
            })
            game_t = 100; app_t = 1000; state_name = 'menu_main'
            TimerManager = {game = function() return {time = function() return game_t end} end}
            Application = {time = function() return app_t end}
            game_state_machine = {last_queued_state_name = function() return state_name end}

            PlayerBase = {
                PLAYER_INFO_HUD_PD2 = "player_info_hud_pd2",
                PLAYER_INFO_HUD_FULLSCREEN_PD2 = "player_info_hud_fullscreen_pd2"
            }

            id_str = function(s) return s end
            function Idstring(s) return s end
            DB = {has = function(_, _, _) return true end}

            panel_states = {}
            function make_panel(w, h)
                local proxy = newproxy(true)
                panel_states[proxy] = {
                    w = w, h = h, x = 0, y = 0,
                    children = {},
                    parent = nil,
                    set_shape_calls = 0,
                    create_count = 0,
                    remove_count = 0,
                    clear_count = 0,
                    w_error = false,
                    h_missing = false,
                    set_shape_error = false,
                    set_shape_missing = false,
                }
                local mt = getmetatable(proxy)
                mt.__index = function(self, key)
                    if key == "w" then
                        if panel_states[self].w_error then
                            error("w is broken")
                        end
                        return function() return panel_states[self].w end
                    elseif key == "h" then
                        if panel_states[self].h_missing then
                            return nil
                        end
                        return function() return panel_states[self].h end
                    elseif key == "x" then
                        return function() return panel_states[self].x end
                    elseif key == "y" then
                        return function() return panel_states[self].y end
                    elseif key == "parent" then
                        return function() return panel_states[self].parent end
                    elseif key == "child" then
                        return function(_, name) return panel_states[self].children[name] end
                    elseif key == "panel" then
                        return function(_, params)
                            local name = params and params.name or "unnamed"
                            local child = make_panel(panel_states[self].w, panel_states[self].h)
                            panel_states[child].parent = self
                            panel_states[self].children[name] = child
                            panel_states[self].create_count = panel_states[self].create_count + 1
                            return child
                        end
                    elseif key == "remove" then
                        return function(_, child)
                            if child then
                                for k, v in pairs(panel_states[self].children) do
                                    if v == child then
                                        panel_states[self].children[k] = nil
                                        panel_states[self].remove_count = panel_states[self].remove_count + 1
                                        return
                                    end
                                end
                            end
                        end
                    elseif key == "clear" then
                        return function()
                            panel_states[self].clear_count = panel_states[self].clear_count + 1
                            for k in pairs(panel_states[self].children) do
                                panel_states[self].children[k] = nil
                            end
                        end
                    elseif key == "set_shape" then
                        if panel_states[self].set_shape_missing then
                            return nil
                        end
                        if panel_states[self].set_shape_error then
                            return function() error("set_shape broken") end
                        end
                        return function(_, x, y, w, h)
                            panel_states[self].x = x
                            panel_states[self].y = y
                            panel_states[self].w = w
                            panel_states[self].h = h
                            panel_states[self].set_shape_calls = panel_states[self].set_shape_calls + 1
                        end
                    end
                    return nil
                end
                mt.__newindex = function() end
                mt.__len = function() return 0 end
                return proxy
            end
        ''')
        self.lua.execute((ROOT / "lua" / "hudlist.lua").read_text(encoding="utf-8-sig"))
        self.lua.execute((ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig"))
        self.lua.globals().RequiredScript = 'lib/managers/hudmanagerpd2'
        self.lua.execute((ROOT / "lua" / "ky_hud_banners.lua").read_text(encoding="utf-8-sig"))
        self.lua.execute((ROOT / "lua" / "ky_buff_render.lua").read_text(encoding="utf-8-sig"))
        self.lua.execute((ROOT / "lua" / "ky_combat_medals.lua").read_text(encoding="utf-8-sig"))
        self.lua.execute('''
            kyohud.settings = {enable_killfeed = true, killfeed_size = 3}
            kyohud:ResetHeistCombatState()
        ''')

    def test_panel_resize_same_parent_trace(self):
        """Same parent object resizes through 1280x720 -> 1198x958 -> 1198x748 -> 1198x673."""
        self.lua.execute('''
            local parent = make_panel(1280, 720)
            managers.hud = {
                script = function(_, hud_name)
                    if hud_name == PlayerBase.PLAYER_INFO_HUD_PD2 or
                       hud_name == PlayerBase.PLAYER_INFO_HUD_FULLSCREEN_PD2 then
                        return {panel = parent}
                    end
                    return nil
                end
            }

            kyohud:ensure_panel(false)
            local root = kyohud._panel
            assert(root ~= nil and alive(root), "root must be alive")
            assert(root:w() == 1280, "initial width")
            assert(root:h() == 720, "initial height")
            assert(root:x() == 0, "initial x")
            assert(root:y() == 0, "initial y")
            assert(root:w() == parent:w(), "root:w() == parent:w()")
            assert(root:h() == parent:h(), "root:h() == parent:h()")

            local parent_state = panel_states[parent]
            local initial_create = parent_state.create_count
            local initial_remove = parent_state.remove_count
            local initial_set_shape = parent_state.set_shape_calls
            assert(parent_state.set_shape_calls == 0, "parent set_shape not called by engine")

            kyohud:add_kill("Enemy1", 10, true)
            kyohud:add_kill("Enemy2", 20, true)
            local score = kyohud._heist_score_total
            local kills = kyohud._heist_kill_count
            local buffs = kyohud._buffs
            local kills_ref = kyohud._kills
            local streaks_ref = kyohud._weapon_streaks
            local banner_ref = kyohud._special_kill_banner
            local medal_ref = kyohud._medal_card
            assert(score > 0, "combat score nonzero")
            assert(type(kills_ref) == "table", "kills table nonnil")
            assert(type(buffs) == "table", "buffs table nonnil")
            assert(type(streaks_ref) == "table", "streaks table nonnil")

            parent_state.w = 1198
            parent_state.h = 958
            kyohud:ensure_panel(false)
            assert(kyohud._panel == root, "same root identity")
            assert(root:w() == 1198, "RED: expected 1198, got " .. tostring(root:w()))
            assert(root:h() == 958, "RED: expected 958, got " .. tostring(root:h()))
            assert(root:x() == 0 and root:y() == 0, "x/y still 0")
            assert(parent_state.set_shape_calls == 0, "parent set_shape count unchanged")
            assert(parent_state.create_count == initial_create, "create count unchanged")
            assert(parent_state.remove_count == initial_remove, "remove count unchanged")
            assert(kyohud._heist_score_total == score, "score unchanged")
            assert(kyohud._heist_kill_count == kills, "kills unchanged")
            assert(kyohud._buffs == buffs, "buffs ref unchanged")
            assert(kyohud._kills == kills_ref, "kills ref unchanged after first resize")
            assert(kyohud._weapon_streaks == streaks_ref, "streaks ref unchanged after first resize")
            assert(kyohud._special_kill_banner == banner_ref, "banner ref unchanged after first resize")
            assert(kyohud._medal_card == medal_ref, "medal ref unchanged after first resize")

            parent_state.w = 1198
            parent_state.h = 748
            kyohud:ensure_panel(false)
            assert(kyohud._panel == root, "same root identity")
            assert(root:w() == 1198, "RED: expected 1198, got " .. tostring(root:w()))
            assert(root:h() == 748, "RED: expected 748, got " .. tostring(root:h()))
            assert(kyohud._kills == kills_ref, "kills ref unchanged after second resize")
            assert(kyohud._buffs == buffs, "buffs ref unchanged after second resize")
            assert(kyohud._weapon_streaks == streaks_ref, "streaks ref unchanged after second resize")
            assert(kyohud._special_kill_banner == banner_ref, "banner ref unchanged after second resize")
            assert(kyohud._medal_card == medal_ref, "medal ref unchanged after second resize")

            parent_state.w = 1198
            parent_state.h = 673
            kyohud:ensure_panel(false)
            assert(kyohud._panel == root, "same root identity")
            assert(root:w() == 1198, "RED: expected 1198, got " .. tostring(root:w()))
            assert(root:h() == 673, "RED: expected 673, got " .. tostring(root:h()))
            assert(kyohud._kills == kills_ref, "kills ref unchanged after third resize")
            assert(kyohud._buffs == buffs, "buffs ref unchanged after third resize")
            assert(kyohud._weapon_streaks == streaks_ref, "streaks ref unchanged after third resize")
            assert(kyohud._special_kill_banner == banner_ref, "banner ref unchanged after third resize")
            assert(kyohud._medal_card == medal_ref, "medal ref unchanged after third resize")
        ''')

    def test_no_redundant_set_shape_unchanged_geometry(self):
        """No redundant set_shape when parent geometry unchanged."""
        self.lua.execute('''
            local parent = make_panel(800, 600)
            managers.hud = {
                script = function(_, hud_name)
                    if hud_name == PlayerBase.PLAYER_INFO_HUD_PD2 then
                        return {panel = parent}
                    end
                    return nil
                end
            }

            kyohud:ensure_panel(false)
            local root = kyohud._panel
            local root_state = panel_states[root]
            local initial_calls = root_state.set_shape_calls

            kyohud:ensure_panel(false)
            assert(root_state.set_shape_calls == initial_calls, "no redundant set_shape")

            kyohud:ensure_panel(false)
            assert(root_state.set_shape_calls == initial_calls, "still no set_shape")
        ''')

    def test_parent_missing_w_returns_false(self):
        """Parent with w_error or h_missing causes ensure_panel to return false."""
        self.lua.execute('''
            local parent = make_panel(1024, 768)
            managers.hud = {
                script = function(_, hud_name)
                    if hud_name == PlayerBase.PLAYER_INFO_HUD_PD2 then
                        return {panel = parent}
                    end
                    return nil
                end
            }

            kyohud:ensure_panel(false)
            local root = kyohud._panel
            assert(root ~= nil, "root created")

            panel_states[parent].w_error = true
            local ok, result = pcall(function() return kyohud:ensure_panel(false) end)
            assert(ok, "pcall success")
            assert(result == false, "ensure_panel returns false when parent w errors")

            panel_states[parent].w_error = false
            panel_states[parent].h_missing = true
            local ok2, result2 = pcall(function() return kyohud:ensure_panel(false) end)
            assert(ok2, "pcall success with h_missing")
            assert(result2 == false, "ensure_panel returns false when parent h missing")

            panel_states[parent].h_missing = false
            panel_states[parent].w = 1024
            panel_states[parent].h = 768
            local ok3, result3 = pcall(function() return kyohud:ensure_panel(false) end)
            assert(ok3, "pcall success after restore")
            assert(result3 == true, "ensure_panel succeeds after restore")
            assert(kyohud._panel == root, "same root")
        ''')

    def test_root_set_shape_failure_no_crash(self):
        """Root set_shape throws via set_shape_error flag, ensure_panel returns false."""
        self.lua.execute('''
            local parent = make_panel(1024, 768)
            managers.hud = {
                script = function(_, hud_name)
                    if hud_name == PlayerBase.PLAYER_INFO_HUD_PD2 then
                        return {panel = parent}
                    end
                    return nil
                end
            }

            kyohud:ensure_panel(false)
            local root = kyohud._panel

            panel_states[root].set_shape_error = true
            panel_states[parent].w = 1200
            panel_states[parent].h = 900

            local ok, result = pcall(function() return kyohud:ensure_panel(false) end)
            assert(ok, "pcall success")
            assert(result == false, "ensure_panel returns false when set_shape throws")
            assert(kyohud._panel == root, "same root after throw")

            panel_states[root].set_shape_error = false
            local ok2, result2 = pcall(function() return kyohud:ensure_panel(false) end)
            assert(ok2, "pcall success after clear")
            assert(result2 == true, "ensure_panel succeeds after clear")
            assert(root:w() == 1200, "new width applied")
            assert(root:h() == 900, "new height applied")
        ''')

    def test_missing_set_shape_api(self):
        """Root set_shape missing via set_shape_missing flag, ensure_panel returns false."""
        self.lua.execute('''
            local parent = make_panel(1024, 768)
            managers.hud = {
                script = function(_, hud_name)
                    if hud_name == PlayerBase.PLAYER_INFO_HUD_PD2 then
                        return {panel = parent}
                    end
                    return nil
                end
            }

            kyohud:ensure_panel(false)
            local root = kyohud._panel

            panel_states[root].set_shape_missing = true
            panel_states[parent].w = 1300
            panel_states[parent].h = 1000

            local ok, result = pcall(function() return kyohud:ensure_panel(false) end)
            assert(ok, "pcall success")
            assert(result == false, "ensure_panel returns false when set_shape missing")
            assert(kyohud._panel == root, "same root after missing")

            panel_states[root].set_shape_missing = false
            local ok2, result2 = pcall(function() return kyohud:ensure_panel(false) end)
            assert(ok2, "pcall success after restore")
            assert(result2 == true, "ensure_panel succeeds after restore")
            assert(root:w() == 1300, "width after restore")
            assert(root:h() == 1000, "height after restore")
        ''')


    def test_parent_infinite_width_rejected(self):
        """Parent with w=math.huge must cause ensure_panel to return false."""
        self.lua.execute('''
            local parent = make_panel(800, 600)
            managers.hud = {
                script = function(_, hud_name)
                    if hud_name == PlayerBase.PLAYER_INFO_HUD_PD2 then
                        return {panel = parent}
                    end
                    return nil
                end
            }

            kyohud:ensure_panel(false)
            local root = kyohud._panel
            assert(root ~= nil and alive(root), "root must be alive")

            kyohud:add_kill("Enemy1", 10, true)
            local score = kyohud._heist_score_total
            local kills_ref = kyohud._kills
            local buffs_ref = kyohud._buffs
            local streaks_ref = kyohud._weapon_streaks
            local banner_ref = kyohud._special_kill_banner
            local medal_ref = kyohud._medal_card
            assert(score > 0, "combat score nonzero")

            panel_states[parent].w = math.huge
            local ok, result = pcall(function() return kyohud:ensure_panel(false) end)
            assert(ok, "pcall success")
            assert(result == false, "ensure_panel returns false when parent w is math.huge")
            assert(kyohud._panel == root, "same root identity")
            assert(kyohud._kills == kills_ref, "kills ref unchanged")
            assert(kyohud._buffs == buffs_ref, "buffs ref unchanged")
            assert(kyohud._weapon_streaks == streaks_ref, "streaks ref unchanged")
            assert(kyohud._special_kill_banner == banner_ref, "banner ref unchanged")
            assert(kyohud._medal_card == medal_ref, "medal ref unchanged")

            panel_states[parent].w = 800
            panel_states[parent].h = 600
            local ok2, result2 = pcall(function() return kyohud:ensure_panel(false) end)
            assert(ok2, "pcall success after restore")
            assert(result2 == true, "ensure_panel succeeds after restore")
            assert(kyohud._panel == root, "same root after restore")
            assert(kyohud._kills == kills_ref, "kills ref unchanged after restore")
            assert(kyohud._buffs == buffs_ref, "buffs ref unchanged after restore")
            assert(kyohud._weapon_streaks == streaks_ref, "streaks ref unchanged after restore")
            assert(kyohud._special_kill_banner == banner_ref, "banner ref unchanged after restore")
            assert(kyohud._medal_card == medal_ref, "medal ref unchanged after restore")
        ''')

    def test_noop_setter_with_offset_root_rejected(self):
        """Root with x~=0 and a no-op setter must cause ensure_panel to return false."""
        self.lua.execute('''
            local parent = make_panel(800, 600)
            managers.hud = {
                script = function(_, hud_name)
                    if hud_name == PlayerBase.PLAYER_INFO_HUD_PD2 then
                        return {panel = parent}
                    end
                    return nil
                end
            }

            kyohud:ensure_panel(false)
            local root = kyohud._panel
            assert(root ~= nil and alive(root), "root must be alive")

            kyohud:add_kill("Enemy1", 10, true)
            local score = kyohud._heist_score_total
            local kills_ref = kyohud._kills
            local buffs_ref = kyohud._buffs
            local streaks_ref = kyohud._weapon_streaks
            local banner_ref = kyohud._special_kill_banner
            local medal_ref = kyohud._medal_card
            assert(score > 0, "combat score nonzero")

            panel_states[root].x = 12

            local root_mt = getmetatable(root)
            local original_index = root_mt.__index
            root_mt.__index = function(self, key)
                if key == "set_shape" then
                    return function() end
                end
                return original_index(self, key)
            end

            panel_states[parent].w = 800
            panel_states[parent].h = 600
            local ok, result = pcall(function() return kyohud:ensure_panel(false) end)
            assert(ok, "pcall success")
            assert(result == false,
                "ensure_panel returns false when setter is no-op and root x ~= 0")
            assert(kyohud._panel == root, "same root identity")
            assert(kyohud._kills == kills_ref, "kills ref unchanged")
            assert(kyohud._buffs == buffs_ref, "buffs ref unchanged")
            assert(kyohud._weapon_streaks == streaks_ref, "streaks ref unchanged")
            assert(kyohud._special_kill_banner == banner_ref, "banner ref unchanged")
            assert(kyohud._medal_card == medal_ref, "medal ref unchanged")

            root_mt.__index = original_index
            local ok2, result2 = pcall(function() return kyohud:ensure_panel(false) end)
            assert(ok2, "pcall success after restore")
            assert(result2 == true, "ensure_panel succeeds with restored setter")
            assert(root:x() == 0, "x reset to 0")
            assert(root:y() == 0, "y reset to 0")
            assert(root:w() == 800, "width matches")
            assert(root:h() == 600, "height matches")
            assert(kyohud._kills == kills_ref, "kills ref unchanged after restore")
            assert(kyohud._buffs == buffs_ref, "buffs ref unchanged after restore")
            assert(kyohud._weapon_streaks == streaks_ref, "streaks ref unchanged after restore")
            assert(kyohud._special_kill_banner == banner_ref, "banner ref unchanged after restore")
            assert(kyohud._medal_card == medal_ref, "medal ref unchanged after restore")
        ''')


if __name__ == "__main__":
    unittest.main()
