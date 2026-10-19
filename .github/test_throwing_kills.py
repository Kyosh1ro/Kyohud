"""Throwing kill medals regression tests against real mod chunks.
Run: uv run --with lupa python -B -m unittest discover -s .github -p test_throwing_kills.py -v
"""
from pathlib import Path
import unittest
from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


def _common_stubs():
    return '''
        _pre_hooks = {}
        _post_hooks = {}
        _wrapped = {}
        Hooks = {}
        local function ensure_wrapper(class, method)
            local key = tostring(class) .. ":" .. method
            if _wrapped[key] then return end
            _wrapped[key] = true
            local orig = class[method] or function() end
            class[method] = function(self, ...)
                local pre = _pre_hooks[class] and _pre_hooks[class][method] or {}
                for _, entry in ipairs(pre) do entry.fn(self, ...) end
                local result = {orig(self, ...)}
                local post = _post_hooks[class] and _post_hooks[class][method] or {}
                for _, entry in ipairs(post) do entry.fn(self, ...) end
                return unpack(result)
            end
        end
        function Hooks:PreHook(class, method, id, fn)
            if type(class) == 'table' then class[method] = class[method] or function() end end
            if not _pre_hooks[class] then _pre_hooks[class] = {} end
            if not _pre_hooks[class][method] then _pre_hooks[class][method] = {} end
            local list = _pre_hooks[class][method]
            for _, entry in ipairs(list) do
                if entry.id == id then return end
            end
            list[#list + 1] = {id = id, fn = fn}
            ensure_wrapper(class, method)
        end
        function Hooks:PostHook(class, method, id, fn)
            if type(class) == 'table' then class[method] = class[method] or function() end end
            if not _post_hooks[class] then _post_hooks[class] = {} end
            if not _post_hooks[class][method] then _post_hooks[class][method] = {} end
            local list = _post_hooks[class][method]
            for _, entry in ipairs(list) do
                if entry.id == id then return end
            end
            list[#list + 1] = {id = id, fn = fn}
            ensure_wrapper(class, method)
        end
        function Hooks:Add(...) end
        HUDManager = {sync_start_assault = function() end, sync_end_assault = function() end}
        PlayerManager = {spawned_player = function() end, on_killshot = function() end}
        PlayerInventory = {equip_selection = function() end}
        CopDamage = {
            is_civilian = function(id) return id == 'civilian' or id == 'civilian_female' end,
            die = function(self, attack_data) end,
            chk_killshot = function(self, attacker, variant, headshot, weapon_id)
                if attacker and attacker == local_player then
                    PlayerManager:on_killshot(self._unit, variant, headshot, weapon_id)
                end
            end,
            damage_bullet = function(self, attack_data)
                attack_data.result = {type = "death", variant = "bullet"}
                self:die(attack_data)
                local weapon_id = nil
                if attack_data.weapon_unit and alive(attack_data.weapon_unit) then
                    local base = attack_data.weapon_unit:base()
                    if base and base.get_name_id then weapon_id = base:get_name_id() end
                end
                self:chk_killshot(attack_data.attacker_unit, "bullet", false, weapon_id)
            end,
            damage_melee = function(self, attack_data)
                attack_data.result = {type = "death", variant = "melee"}
                self:die(attack_data)
                self:chk_killshot(attack_data.attacker_unit, "melee", false, nil)
            end,
        }
        HuskCopDamage = setmetatable({}, {__index = CopDamage})
        HuskCopDamage.die = function(self, attack_data)
            self._health = 0
            self._dead = true
        end
        CivilianDamage = {
            _on_damage_received = function(self, attack_data) end
        }
        hud_icon_calls = 0
        bitmap_calls = {}
        managers = {}; tweak_data = {
            weapon = {
                test_sniper = {categories = {'snp'}},
                test_shotgun = {categories = {'shotgun'}}
            },
            hud_icons = {get_icon_data = function(self, name)
                hud_icon_calls = hud_icon_calls + 1
                return 'resolved/' .. name, {0,0,1,1}
            end}
        }
        DB = {has = function() return true end}
        function Idstring(value) return value end
        function Vector3(...) return {...} end
        mvector3 = {distance = function(a, b)
            local x = (a.x or 0) - (b.x or 0)
            local y = (a.y or 0) - (b.y or 0)
            local z = (a.z or 0) - (b.z or 0)
            return math.sqrt(x*x + y*y + z*z)
        end}
        function log(...) end
        function alive(x) return x ~= nil and x ~= false end
        Color = setmetatable({white = {}, black = {}}, {__call = function(...) return {} end})
        game_t = 100; state_name = 'menu_main'; is_client = false
        Network = {is_client = function() return is_client end}
        TimerManager = {game = function() return {time = function() return game_t end} end}
        game_state_machine = {last_queued_state_name = function() return state_name end}
        local_player = {position = function() return {x=0,y=0,z=0} end}
        other_player = {position = function() return {x=100,y=0,z=0} end}
        registered_messages = {}
        managers.player = {player_unit = function() return local_player end,
            current_state = function() return 'standard' end,
            register_message = function(self, msg_id, uid, callback)
                registered_messages[#registered_messages+1] = {
                    msg_id = msg_id, uid = uid, callback = callback
                }
            end}
        function make_projectile_base(entry_name)
            return {
                thrower_unit = function() return local_player end,
                projectile_entry = function() return entry_name end,
                get_name_id = function() return entry_name end,
            }
        end
        function enemy(id, animation, rope, action, position)
            return {base = function() return {_tweak_table = id or 'cop'} end,
                anim_data = function() return animation or {} end,
                position = function() return position or {x=0,y=0,z=0} end,
                movement = function() return {
                    _active_actions = {action},
                    rope_unit = function() return rope end
                } end}
        end
        function throwing_projectile(entry_name, thrower)
            local proj_base = make_projectile_base(entry_name or 'wpn_prj_jav')
            if thrower then
                proj_base.thrower_unit = function() return thrower end
            end
            return {base = function() return proj_base end}
        end
        function attack_data_for_bullet_throw(projectile, target)
            return {
                attacker_unit = local_player,
                weapon_unit = projectile,
                variant = 'bullet',
                headshot = false,
                damage = 1000,
                col_ray = {body = {name = function() return Idstring('body') end}, position = {x=0,y=0,z=0}},
            }
        end
        function attack_data_for_melee_throw(projectile, target)
            return {
                attacker_unit = local_player,
                weapon_unit = projectile,
                variant = 'melee',
                headshot = false,
                damage = 1000,
                col_ray = {body = {name = function() return Idstring('body') end}, position = {x=0,y=0,z=0}},
            }
        end
    '''


class ThrowingKillTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + '/'
        self.lua.execute(_common_stubs())
        self.load('core.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_combat_medals.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_hud_banners.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_buff_render.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_killfeed.lua', 'lib/managers/playermanager')
        self.load('ky_killfeed.lua', 'lib/units/enemies/cop/copdamage')
        self.load('ky_playerinventory.lua', 'lib/units/beings/player/playerinventory')
        self.lua.execute('''
            kyohud.settings = {enable_killfeed = true, killfeed_size = 3}
            kyohud:ResetHeistCombatState()
            cards = {}
            original_show = kyohud._show_medal_card
            kyohud._show_medal_card = function(self, t, card, preview)
                if card then cards[#cards+1] = card end
                return original_show(self, t, card, preview)
            end
            function count_event(id)
                local n = 0
                for _, card in ipairs(cards) do if card.event == id then n = n + 1 end end
                return n
            end
            function host_bullet_throw_kill(entry)
                local proj = throwing_projectile(entry or 'wpn_prj_jav')
                local unit = enemy('cop')
                local cop_damage = {
                    _unit = unit,
                    _health = 0,
                    _dead = true,
                }
                setmetatable(cop_damage, {__index = CopDamage})
                local ad = attack_data_for_bullet_throw(proj, unit)
                CopDamage.damage_bullet(cop_damage, ad)
                return kyohud._kills
            end
            function host_melee_throw_kill(entry)
                local proj = throwing_projectile(entry or 'wpn_prj_target')
                local unit = enemy('cop')
                local cop_damage = {
                    _unit = unit,
                    _health = 0,
                    _dead = true,
                }
                setmetatable(cop_damage, {__index = CopDamage})
                local ad = attack_data_for_melee_throw(proj, unit)
                CopDamage.die(cop_damage, ad)
                return kyohud._kills
            end
            function client_throw_kill(entry, variant)
                local proj = throwing_projectile(entry or 'wpn_prj_jav')
                local unit = enemy('cop')
                local cop_damage = {
                    _unit = unit,
                    _health = 0,
                    _dead = true,
                }
                setmetatable(cop_damage, {__index = CopDamage})
                CopDamage.chk_killshot(cop_damage, local_player, variant or 'bullet', false, entry or 'wpn_prj_jav')
                return kyohud._kills
            end
        ''')

    def load(self, name, context):
        self.lua.globals().RequiredScript = context
        self.lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

    def test_host_javelin_bullet_direct_hit_awards_medal(self):
        self.lua.execute('''
            cards = {}
            host_bullet_throw_kill('wpn_prj_jav')
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 1)

    def test_host_target_knife_melee_hit_awards_medal(self):
        self.lua.execute('''
            cards = {}
            host_melee_throw_kill('wpn_prj_target')
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 1)

    def test_host_throwing_axe_awards_medal(self):
        self.lua.execute('''
            cards = {}
            host_melee_throw_kill('wpn_prj_hur')
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 1)

    def test_host_four_throwable_awards_medal(self):
        self.lua.execute('''
            cards = {}
            host_melee_throw_kill('wpn_prj_four')
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 1)

    def test_host_ace_throwable_awards_medal(self):
        self.lua.execute('''
            cards = {}
            host_melee_throw_kill('wpn_prj_ace')
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 1)

    def test_poison_dot_does_not_award_throwing_medal(self):
        self.lua.execute('''
            cards = {}
            local proj = throwing_projectile('wpn_prj_target')
            local unit = enemy('cop')
            local cop_damage = {_unit = unit, _health = 0, _dead = true}
            setmetatable(cop_damage, {__index = CopDamage})
            local ad = {
                attacker_unit = local_player,
                weapon_unit = proj,
                variant = 'poison',
                headshot = false,
                damage = 100,
                col_ray = {body = {name = function() return Idstring('body') end}, position = {x=0,y=0,z=0}},
            }
            CopDamage.die(cop_damage, ad)
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 0)

    def test_fire_dot_does_not_award_throwing_medal(self):
        self.lua.execute('''
            cards = {}
            local proj = throwing_projectile('wpn_prj_target')
            local unit = enemy('cop')
            local cop_damage = {_unit = unit, _health = 0, _dead = true}
            setmetatable(cop_damage, {__index = CopDamage})
            local ad = {
                attacker_unit = local_player,
                weapon_unit = proj,
                variant = 'fire',
                headshot = false,
                damage = 100,
                col_ray = {body = {name = function() return Idstring('body') end}, position = {x=0,y=0,z=0}},
            }
            CopDamage.die(cop_damage, ad)
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 0)

    def test_explosion_does_not_award_throwing_medal(self):
        self.lua.execute('''
            cards = {}
            local unit = enemy('cop')
            local cop_damage = {_unit = unit, _health = 0, _dead = true}
            setmetatable(cop_damage, {__index = CopDamage})
            local ad = {
                attacker_unit = local_player,
                weapon_unit = nil,
                weapon_id = 'wpn_prj_jav',
                variant = 'explosion',
                headshot = false,
                damage = 100,
                col_ray = {body = {name = function() return Idstring('body') end}, position = {x=0,y=0,z=0}},
            }
            CopDamage.die(cop_damage, ad)
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 0)

    def test_unknown_projectile_id_does_not_award_throwing_medal(self):
        self.lua.execute('''
            cards = {}
            local unit = enemy('cop')
            local cop_damage = {_unit = unit, _health = 0, _dead = true}
            setmetatable(cop_damage, {__index = CopDamage})
            local ad = {
                attacker_unit = local_player,
                weapon_unit = nil,
                weapon_id = 'frag',
                variant = 'bullet',
                headshot = false,
                damage = 100,
                col_ray = {body = {name = function() return Idstring('body') end}, position = {x=0,y=0,z=0}},
            }
            CopDamage.die(cop_damage, ad)
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 0)

    def test_bow_arrow_does_not_award_throwing_medal(self):
        self.lua.execute('''
            cards = {}
            local unit = enemy('cop')
            local cop_damage = {_unit = unit, _health = 0, _dead = true}
            setmetatable(cop_damage, {__index = CopDamage})
            local ad = {
                attacker_unit = local_player,
                weapon_unit = nil,
                weapon_id = 'plainsrider',
                variant = 'bullet',
                headshot = false,
                damage = 100,
                col_ray = {body = {name = function() return Idstring('body') end}, position = {x=0,y=0,z=0}},
            }
            CopDamage.die(cop_damage, ad)
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 0)

    def test_launcher_does_not_award_throwing_medal(self):
        self.lua.execute('''
            cards = {}
            local unit = enemy('cop')
            local cop_damage = {_unit = unit, _health = 0, _dead = true}
            setmetatable(cop_damage, {__index = CopDamage})
            local ad = {
                attacker_unit = local_player,
                weapon_unit = nil,
                weapon_id = 'gre_m79',
                variant = 'explosion',
                headshot = false,
                damage = 100,
                col_ray = {body = {name = function() return Idstring('body') end}, position = {x=0,y=0,z=0}},
            }
            CopDamage.die(cop_damage, ad)
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 0)

    def test_other_player_throw_does_not_award_medal(self):
        self.lua.execute('''
            cards = {}
            local proj = throwing_projectile('wpn_prj_jav', other_player)
            local unit = enemy('cop')
            local cop_damage = {_unit = unit, _health = 0, _dead = true}
            setmetatable(cop_damage, {__index = CopDamage})
            local ad = attack_data_for_bullet_throw(proj, unit)
            ad.attacker_unit = other_player
            CopDamage.damage_bullet(cop_damage, ad)
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 0)

    def test_throwing_kill_does_not_advance_weapon_streak(self):
        self.lua.execute('''
            kyohud._weapon_streaks = {}
            cards = {}
            host_bullet_throw_kill('wpn_prj_jav')
        ''')
        has_bullet_streak = self.lua.execute('''
            return kyohud._weapon_streaks.bullet ~= nil
                and kyohud._weapon_streaks.bullet.count > 0
        ''')
        self.assertFalse(has_bullet_streak)
        has_melee_streak = self.lua.execute('''
            return kyohud._weapon_streaks.melee ~= nil
                and kyohud._weapon_streaks.melee.count > 0
        ''')
        self.assertFalse(has_melee_streak)

    def test_throwing_kill_still_scores(self):
        self.lua.execute('''
            kyohud._killfeed_score_total = 0
            kyohud._killfeed_score_has_value = false
            host_bullet_throw_kill('wpn_prj_jav')
        ''')
        score = self.lua.execute('return kyohud._killfeed_score_total')
        self.assertGreater(score, 0)

    def test_throwing_kill_advances_combo(self):
        self.lua.execute('''
            kyohud._kill_combo = { count = 0, last_t = nil, updated_t = nil }
            host_bullet_throw_kill('wpn_prj_jav')
        ''')
        combo_count = self.lua.execute('return kyohud._kill_combo.count')
        self.assertEqual(combo_count, 1)

    def test_throwing_kill_increments_heist_total(self):
        self.lua.execute('''
            kyohud._heist_kill_count = 0
            host_bullet_throw_kill('wpn_prj_jav')
        ''')
        count = self.lua.execute('return kyohud._heist_kill_count')
        self.assertEqual(count, 1)

    def test_killfeed_entry_has_display_text_with_target(self):
        self.lua.execute('''
            host_bullet_throw_kill('wpn_prj_jav')
        ''')
        entry = self.lua.execute('''
            local kills = kyohud._kills
            return kills[#kills]
        ''')
        self.assertIsNotNone(entry)
        self.assertTrue(entry['display_text'] and len(str(entry['display_text'])) > 0)
        self.assertIn('Cop', str(entry['display_text']))

    def test_killfeed_entry_has_throw_icon_with_texture(self):
        self.lua.execute('''
            host_bullet_throw_kill('wpn_prj_jav')
        ''')
        has_icon = self.lua.execute('''
            local kills = kyohud._kills
            local entry = kills[#kills]
            return entry.throw_icon ~= nil
                and entry.throw_icon.texture ~= nil
        ''')
        self.assertTrue(has_icon)

    def test_throw_icon_rendered_as_leading_icon_bitmap(self):
        """Real rendering test: load production chunks, call render_killfeed, verify bitmap + text offset."""
        from pathlib import Path
        from lupa.luajit21 import LuaRuntime
        ROOT = Path(__file__).resolve().parents[1]

        lua = LuaRuntime(unpack_returned_tuples=True)
        lua.globals().ModPath = ROOT.as_posix() + '/'
        lua.globals().RequiredScript = 'lib/managers/hudmanagerpd2'

        # Minimal production stubs matching test_killfeed_render_extraction.py
        lua.execute('''
            Hooks = {callbacks = {}}
            function Hooks:PostHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:PreHook(class, method, id, fn) self.callbacks[id] = fn end
            function Hooks:Add(...) end
            HUDManager = {}; PlayerManager = {}; managers = {}; tweak_data = {}
            function Vector3(...) return {...} end
            function log(...) end
            function alive(x) return x ~= nil end
            function Idstring(s) return s end
            DB = { has = function() return false end }
            local function color(r, g, b)
                local c = {r = r or 0, g = g or 0, b = b or 0}
                function c:with_alpha(a) return self end
                return c
            end
            Color = setmetatable({white = color(1,1,1), black = color(0,0,0)}, {
                __call = function(_, ...) return color(...) end
            })
            tweak_data.menu = {pd2_small_font = "test_font", pd2_large_font = "test_font_large", pd2_medium_font = "test_font_medium"}
            tweak_data.hud_icons = {
                get_icon_data = function(self, name)
                    return 'resolved/' .. (name or 'unknown'), {0, 0, 48, 48}
                end
            }
            game_t = 100
            TimerManager = {game = function() return {time = function() return game_t end} end}
            PlayerBase = {PLAYER_INFO_HUD_PD2 = "pd2", PLAYER_INFO_HUD_FULLSCREEN_PD2 = "fs"}
        ''')

        # Load production chunks in order
        for name in [
            'hudlist.lua', 'core.lua', 'ky_buff_render.lua',
            'ky_combat_medals.lua', 'ky_heist_score.lua',
            'ky_hud_banners.lua', 'ky_killfeed_render.lua'
        ]:
            lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

        # Install panel mock that records bitmaps
        lua.execute('''
            bitmap_count = 0
            throw_bitmap_x = nil
            local panel = {
                gradients = {}, rects = {}, texts = {}, bitmaps = {}, polygons = {},
                _children = {},
            }
            function panel:w() return 800 end
            function panel:h() return 600 end
            function panel:child() return nil end
            function panel:panel(params) self._children[#self._children+1] = params; return self end
            function panel:gradient(params)
                self.gradients[#self.gradients + 1] = params
                return params
            end
            function panel:rect(params)
                self.rects[#self.rects + 1] = params
                return params
            end
            function panel:text(params)
                self.texts[#self.texts + 1] = params
                return {
                    set_text = function() end,
                    text_rect = function() return 0, 0, 15, 10 end,
                }
            end
            function panel:bitmap(params)
                bitmap_count = bitmap_count + 1
                if params.texture == "resolved/csb_throwables" then
                    throw_bitmap_x = params.x
                end
                self.bitmaps[#self.bitmaps + 1] = params
                return {set_color = function() end, set_alpha = function() end, set_rotation = function() end}
            end
            function panel:polygon(params)
                self.polygons[#self.polygons + 1] = params
                return params
            end
            function panel:remove() end
            function panel:clear()
                self.gradients = {}; self.rects = {}; self.texts = {}
                self.bitmaps = {}; self.polygons = {}
            end
            kyohud._panel = panel
            kyohud._panel_record = panel
        ''')

        # Create a kill entry with throw_icon and render
        lua.execute('''
            game_t = 100
            kyohud._kills = {{
                name = "Guard",
                display_text = "DEADLY THROW Guard",
                score_text = "+5",
                throw_icon = {
                    texture = "resolved/csb_throwables",
                    rect = {0, 0, 48, 48},
                },
                start_t = 100,
                t_end = 200,
            }}
            kyohud._killfeed_score_total = 5
            kyohud._killfeed_score_has_value = true
            kyohud._special_kill_banner = nil
            kyohud._medal_card = nil
            kyohud.settings = {
                enable_killfeed = true,
                icon_size = 32,
                opacity = 0.9,
                killfeed_size = 5,
                circle_radius = 250,
            }

            kyohud:render_killfeed(kyohud._panel, 800, 600, 32, 0.9, 250)

            assert(bitmap_count > 0, "render_killfeed must create bitmaps")
            assert(throw_bitmap_x ~= nil, "throw_icon bitmap must be created with csb_throwables texture")

            local name_x = nil
            for _, t in ipairs(kyohud._panel.texts) do
                if t.text == "DEADLY THROW Guard" and t.layer == 102 then
                    name_x = t.x
                    break
                end
            end
            assert(name_x ~= nil, "kill name text must be emitted")
            assert(name_x > throw_bitmap_x,
                "name text x must be right of throw_icon (text offset/reservation); name_x="
                .. tostring(name_x) .. " bitmap_x=" .. tostring(throw_bitmap_x))
        ''')

    def test_variant_rotates_across_kills(self):
        self.lua.execute('''
            kyohud._throw_kill_variant_index = 0
            host_bullet_throw_kill('wpn_prj_jav')
            host_bullet_throw_kill('wpn_prj_jav')
            host_bullet_throw_kill('wpn_prj_jav')
            host_bullet_throw_kill('wpn_prj_jav')
        ''')
        variant_after = self.lua.execute('return kyohud._throw_kill_variant_index')
        self.assertEqual(variant_after, 1)

    def test_variant_reset_on_heist_reset(self):
        self.lua.execute('''
            kyohud._throw_kill_variant_index = 2
            kyohud:ResetHeistCombatState()
        ''')
        variant = self.lua.execute('return kyohud._throw_kill_variant_index')
        self.assertEqual(variant, 0)

    def test_dedup_does_not_double_count(self):
        self.lua.execute('''
            cards = {}
            local proj = throwing_projectile('wpn_prj_jav')
            local unit = enemy('cop')
            local cop_damage = {_unit = unit, _health = 0, _dead = true}
            setmetatable(cop_damage, {__index = CopDamage})
            local ad = attack_data_for_bullet_throw(proj, unit)
            CopDamage.damage_bullet(cop_damage, ad)
            CopDamage.damage_bullet(cop_damage, ad)
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 1)

    def test_stale_throwing_flag_reset_between_kills(self):
        self.lua.execute('''
            cards = {}
            host_bullet_throw_kill('wpn_prj_jav')
            local proj2 = throwing_projectile('wpn_prj_target')
            local unit2 = enemy('cop')
            local cop_damage2 = {_unit = unit2, _health = 0, _dead = true}
            setmetatable(cop_damage2, {__index = CopDamage})
            local ad2 = {
                attacker_unit = local_player,
                weapon_unit = proj2,
                variant = 'poison',
                headshot = false,
                damage = 100,
                col_ray = {body = {name = function() return Idstring('body') end}, position = {x=0,y=0,z=0}},
            }
            CopDamage.die(cop_damage2, ad2)
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 1)

    def test_client_path_bullet_javelin_kill(self):
        self.lua.execute('''
            is_client = true
            cards = {}
            client_throw_kill('wpn_prj_jav', 'bullet')
            is_client = false
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 1)

    def test_client_path_melee_throw_kill(self):
        self.lua.execute('''
            is_client = true
            cards = {}
            client_throw_kill('wpn_prj_target', 'melee')
            is_client = false
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 1)

    def test_client_path_all_native_ids(self):
        for native_id in ['wpn_prj_jav', 'wpn_prj_target', 'wpn_prj_hur', 'wpn_prj_four', 'wpn_prj_ace']:
            self.lua.execute(f'''
                is_client = true
                cards = {{}}
                client_throw_kill('{native_id}', 'bullet')
                is_client = false
            ''')
            count = self.lua.execute('return count_event("deadly_throw")')
            self.assertEqual(count, 1, f"Client path failed for {native_id}")

    def test_client_path_unknown_projectile_no_medal(self):
        self.lua.execute('''
            is_client = true
            cards = {}
            client_throw_kill('frag', 'bullet')
            is_client = false
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 0)

    def test_medal_definition_exists(self):
        definition = self.lua.execute('''
            return kyohud.EVENT_MEDAL_DEFINITIONS.deadly_throw
        ''')
        self.assertIsNotNone(definition)
        self.assertEqual(definition['id'], 'ky_hud_event_medal_deadly_throw')

    def test_medal_in_order(self):
        found = self.lua.execute('''
            for i, id in ipairs(kyohud.EVENT_MEDAL_ORDER) do
                if id == 'deadly_throw' then return true end
            end
            return false
        ''')
        self.assertTrue(found)

    def test_localization_fallback_medal(self):
        self.lua.execute('''
            kyohud.localized_text = function(id, fallback) return fallback end
        ''')
        result = self.lua.execute('''
            local card = kyohud.MakeEventMedalCard('deadly_throw')
            return card and card.label
        ''')
        self.assertEqual(result, 'Deadly Throw')

    def test_localization_third_variant_is_neutral(self):
        result = self.lua.execute('''
            return kyohud.localized_text
                and kyohud.localized_text("ky_hud_throw_kill_3", "PERFECT THROW")
                or "PERFECT THROW"
        ''')
        self.assertNotIn('SILENT', str(result).upper())

    def test_is_throwing_kill_api_exists(self):
        exists = self.lua.execute('return kyohud.IsThrowingKill ~= nil')
        self.assertTrue(exists)

    def test_is_throwing_kill_rejects_nil(self):
        result = self.lua.execute('return kyohud:IsThrowingKill(nil)')
        self.assertFalse(result)

    def test_is_throwing_kill_rejects_no_weapon(self):
        result = self.lua.execute('return kyohud:IsThrowingKill({variant = "bullet", weapon_unit = nil, weapon_id = nil})')
        self.assertFalse(result)

    def test_is_throwing_kill_rejects_dot_variant(self):
        result = self.lua.execute('''
            local proj = throwing_projectile('wpn_prj_target')
            return kyohud:IsThrowingKill({
                variant = "poison", weapon_unit = proj, weapon_id = "wpn_prj_target"
            })
        ''')
        self.assertFalse(result)

    def test_is_throwing_kill_accepts_bullet_variant(self):
        result = self.lua.execute('''
            return kyohud:IsThrowingKill({
                variant = "bullet", weapon_unit = nil, weapon_id = "wpn_prj_jav"
            })
        ''')
        self.assertTrue(result)

    def test_is_throwing_kill_accepts_melee_variant(self):
        result = self.lua.execute('''
            return kyohud:IsThrowingKill({
                variant = "melee", weapon_unit = nil, weapon_id = "wpn_prj_target"
            })
        ''')
        self.assertTrue(result)

    def test_sentry_path_no_throwing_medal(self):
        self.lua.execute('''
            is_client = true
            cards = {}
            local sentry_unit = {
                base = function() return {
                    sentry_gun = true,
                    get_owner = function() return local_player end,
                } end
            }
            local unit = enemy('cop')
            local cop_damage = {_unit = unit, _health = 0, _dead = true}
            setmetatable(cop_damage, {__index = HuskCopDamage})
            local ad = {
                attacker_unit = sentry_unit,
                weapon_unit = nil,
                variant = 'bullet',
                headshot = false,
            }
            HuskCopDamage.die(cop_damage, ad)
            is_client = false
        ''')
        count = self.lua.execute('return count_event("deadly_throw")')
        self.assertEqual(count, 0)

    def test_stealth_preserved_with_throwing(self):
        self.lua.execute('''
            kyohud.ConsumeStealthContext = function(self, unit)
                return {whisper = true, cool = false, backstab = false}
            end
            host_bullet_throw_kill('wpn_prj_jav')
            kyohud.ConsumeStealthContext = nil
        ''')
        stealth = self.lua.execute('''
            local kills = kyohud._kills
            return kills[#kills].stealth == true
        ''')
        self.assertTrue(stealth)

    def test_stealth_melee_medal_not_awarded_for_throw(self):
        self.lua.execute('''
            kyohud.ConsumeStealthContext = function(self, unit)
                return {whisper = true, cool = true, backstab = false}
            end
            cards = {}
            host_bullet_throw_kill('wpn_prj_jav')
            kyohud.ConsumeStealthContext = nil
        ''')
        stealth_melee_count = self.lua.execute('return count_event("stealth_melee")')
        self.assertEqual(stealth_melee_count, 0)
        silent_guard_count = self.lua.execute('return count_event("silent_guard")')
        self.assertEqual(silent_guard_count, 0)

    def test_throw_icon_resolved_at_creation_not_draw(self):
        self.lua.execute('''
            hud_icon_calls = 0
            host_bullet_throw_kill('wpn_prj_jav')
        ''')
        calls_after_kill = self.lua.execute('return hud_icon_calls')
        self.assertGreater(calls_after_kill, 0)

    def test_preview_throwing_visible_at_killfeed_size_1(self):
        self.lua.execute('''
            kyohud.settings = {enable_killfeed = true, killfeed_size = 1}
            kyohud._debug_banner_preview_index = 0
            for i, p in ipairs(kyohud.DEBUG_BANNER_PREVIEWS) do
                if p.medal == "event" and p.event == "deadly_throw" then
                    kyohud._debug_banner_preview_index = i - 1
                    break
                end
            end
            kyohud:DebugSimulate()
        ''')
        kill_count = self.lua.execute('return #kyohud._kills')
        self.assertEqual(kill_count, 1)
        has_throw = self.lua.execute('''
            local k = kyohud._kills[1]
            return k.throw_icon ~= nil and k.throw_icon.texture ~= nil
        ''')
        self.assertTrue(has_throw)

    def test_preview_throwing_visible_at_killfeed_size_5(self):
        self.lua.execute('''
            kyohud.settings = {enable_killfeed = true, killfeed_size = 5}
            kyohud._debug_banner_preview_index = 0
            for i, p in ipairs(kyohud.DEBUG_BANNER_PREVIEWS) do
                if p.medal == "event" and p.event == "deadly_throw" then
                    kyohud._debug_banner_preview_index = i - 1
                    break
                end
            end
            kyohud:DebugSimulate()
        ''')
        kill_count = self.lua.execute('return #kyohud._kills')
        self.assertEqual(kill_count, 5)
        has_throw = self.lua.execute('''
            for _, k in ipairs(kyohud._kills) do
                if k.throw_icon ~= nil then return true end
            end
            return false
        ''')
        self.assertTrue(has_throw)

    def test_preview_taser_keeps_special_metadata(self):
        self.lua.execute('''
            kyohud.settings = {enable_killfeed = true, killfeed_size = 5}
            local taser_idx
            for i, p in ipairs(kyohud.DEBUG_BANNER_PREVIEWS) do
                if p.medal == "event" and p.event == "deadly_throw" then
                    taser_idx = i
                    break
                end
            end
            kyohud._debug_banner_preview_index = (taser_idx - 2) % #kyohud.DEBUG_BANNER_PREVIEWS
            kyohud:DebugSimulate()
        ''')
        has_taser = self.lua.execute('''
            for _, k in ipairs(kyohud._kills) do
                if k.special_kind == "taser" then return true end
            end
            return false
        ''')
        self.assertTrue(has_taser)

    def test_preview_no_throw_icon_for_non_throw_previews(self):
        self.lua.execute('''
            kyohud.settings = {enable_killfeed = true, killfeed_size = 5}
            kyohud._debug_banner_preview_index = 0
            for i, p in ipairs(kyohud.DEBUG_BANNER_PREVIEWS) do
                if p.combo == 4 then
                    kyohud._debug_banner_preview_index = i - 1
                    break
                end
            end
            kyohud:DebugSimulate()
        ''')
        has_any_throw = self.lua.execute('''
            for _, k in ipairs(kyohud._kills) do
                if k.throw_icon ~= nil then return true end
            end
            return false
        ''')
        self.assertFalse(has_any_throw)

    def test_native_ids_table_completeness(self):
        for native_id in ['wpn_prj_jav', 'wpn_prj_target', 'wpn_prj_hur', 'wpn_prj_four', 'wpn_prj_ace']:
            result = self.lua.execute(f'''
                return kyohud:IsThrowingKill({{
                    variant = "bullet", weapon_unit = nil, weapon_id = "{native_id}"
                }})
            ''')
            self.assertTrue(result, f"Native ID {native_id} not recognized")

    def test_preview_all_three_variants_reachable(self):
        """All 3 throw label variants (DEADLY THROW, THROWN BLADE, PERFECT THROW) must be reachable via preview cycles."""
        seen_indices = set()
        for cycle in range(6):
            self.lua.execute(f'''
                kyohud.settings = {{enable_killfeed = true, killfeed_size = 5}}
                kyohud._debug_banner_preview_index = 0
                for i, p in ipairs(kyohud.DEBUG_BANNER_PREVIEWS) do
                    if p.medal == "event" and p.event == "deadly_throw" then
                        kyohud._debug_banner_preview_index = i - 1
                        break
                    end
                end
                kyohud:DebugSimulate()
            ''')
            variant_index = self.lua.execute('return kyohud._throw_kill_variant_index')
            seen_indices.add(variant_index)

        self.assertEqual(len(seen_indices), 3, f"Must see all 3 variant indices (1,2,3); got {seen_indices}")

    def test_preview_visible_at_all_killfeed_sizes(self):
        """Throw preview must be visible at killfeed sizes 1, 2, 3, 4, and 5."""
        for size in [1, 2, 3, 4, 5]:
            self.lua.execute(f'''
                kyohud.settings = {{enable_killfeed = true, killfeed_size = {size}}}
                kyohud._debug_banner_preview_index = 0
                for i, p in ipairs(kyohud.DEBUG_BANNER_PREVIEWS) do
                    if p.medal == "event" and p.event == "deadly_throw" then
                        kyohud._debug_banner_preview_index = i - 1
                        break
                    end
                end
                kyohud:DebugSimulate()
            ''')
            kill_count = self.lua.execute('return #kyohud._kills')
            self.assertEqual(kill_count, size, f"Size {size}: must have {size} kills")
            has_throw = self.lua.execute('''
                for _, k in ipairs(kyohud._kills) do
                    if k.throw_icon ~= nil then return true end
                end
                return false
            ''')
            self.assertTrue(has_throw, f"Size {size}: throw preview must be visible")

    def test_preview_stealth_alternation_across_cycles(self):
        """Throw preview alternates between loud and stealth across cycles."""
        stealth_values = []
        for cycle in range(4):
            self.lua.execute('''
                kyohud.settings = {enable_killfeed = true, killfeed_size = 5}
                kyohud._debug_banner_preview_index = 0
                for i, p in ipairs(kyohud.DEBUG_BANNER_PREVIEWS) do
                    if p.medal == "event" and p.event == "deadly_throw" then
                        kyohud._debug_banner_preview_index = i - 1
                        break
                    end
                end
                kyohud:DebugSimulate()
            ''')
            has_stealth = self.lua.execute('''
                for _, k in ipairs(kyohud._kills) do
                    if k.throw_icon ~= nil then return k.stealth == true end
                end
                return false
            ''')
            stealth_values.append(has_stealth)

        # Must alternate: False, True, False, True (or vice versa depending on starting state)
        self.assertEqual(len(set(stealth_values)), 2, "Must see both stealth=True and stealth=False across cycles")

    def test_get_kill_weapon_family_returns_nil_for_throw(self):
        result = self.lua.execute('''
            return kyohud:GetKillWeaponFamily({throwing = true, variant = "bullet"})
        ''')
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
