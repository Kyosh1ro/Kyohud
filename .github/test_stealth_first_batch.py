"""Stealth first-batch regression tests against real mod chunks.
Run: uv run --with lupa python -B -m unittest discover -s .github -p test_stealth_first_batch.py -v
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
                self:chk_killshot(attack_data.attacker_unit, "bullet", false, nil)
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
        HuskCopBrain = {
            _NET_EVENTS = {surrender_civilian_tied = 5, surrender_civilian_untied = 6},
            sync_net_event = function(self, event_id) end,
        }
        CivilianLogicSurrender = {
            on_tied = function(data, aggressor, not_tied, can_flee)
                if data.is_tied then return end
                if not_tied then return end
                data.is_tied = true
            end,
        }
        IntimitateInteractionExt = {
            interact = function(self, player)
                if not self:can_interact(player) then return end
            end,
            can_interact = function() return true end,
        }
        PlayerDamage = {
            damage_tase=function() end, damage_bullet=function() end,
            damage_melee=function() end, damage_explosion=function() end,
            damage_fire=function() end, on_downed=function() end,
            on_incapacitated=function() end, on_arrested=function() end,
            set_health=function() end, _upd_health_regen=function() end
        }
        PlayerMovement = {on_SPOOCed=function() end}
        NewRaycastWeaponBase = {on_reload = function() end}
        RaycastWeaponBase = {_check_kill_achievements=function() end}
        managers = {}; tweak_data = {
            weapon = {
                test_sniper = {categories = {'snp'}},
                test_shotgun = {categories = {'shotgun'}},
                test_melee = {categories = {'melee'}},
            },
            hud_icons = {get_icon_data = function(self, name)
                return 'resolved/' .. name, {0,0,1,1}
            end},
            preplanning = {gui = {type_icons_path = 'guis/test'}},
        }
        DB = {has = function() return true end}
        function Idstring(value) return {key = function() return value end} end
        function Vector3(...) return {...} end
        mvector3 = {
            distance = function(a, b)
                local ax, ay, az = a.x or a[1] or 0, a.y or a[2] or 0, a.z or a[3] or 0
                local bx, by, bz = b.x or b[1] or 0, b.y or b[2] or 0, b.z or b[3] or 0
                return math.sqrt((ax-bx)^2 + (ay-by)^2 + (az-bz)^2)
            end,
            set = function(v) end,
            set_z = function(v, z) end,
            normalize = function(v) end,
            dot = function(a, b)
                return (a.x or a[1] or 0) * (b.x or b[1] or 0)
                     + (a.y or a[2] or 0) * (b.y or b[2] or 0)
                     + (a.z or a[3] or 0) * (b.z or b[3] or 0)
            end,
        }
        _enemy_fwd = nil
        mrotation = {y = function(rot)
            if _enemy_fwd then
                return {x = _enemy_fwd.x, y = _enemy_fwd.y, z = _enemy_fwd.z or 0}
            end
            return {x = 0, y = 1, z = 0}
        end}
        function log(...) end
        function alive(x) return x ~= nil and x ~= false end
        Color = setmetatable({white = {}, black = {}}, {__call = function(_, ...) return {r=1,g=1,b=1} end})
        game_t = 100; state_name = 'menu_main'; is_client_val = false
        Network = {is_client = function() return is_client_val end, is_server = function() return not is_client_val end}
        TimerManager = {game = function() return {time = function() return game_t end} end}
        game_state_machine = {last_queued_state_name = function() return state_name end}
        whisper_mode_val = false
        local_player = {
            position = function() return {x=0,y=0,z=0} end,
            movement = function() return {
                m_head_rot = function() return {y = function() return {x=0,y=1,z=0} end} end,
                current_state_name = function() return 'standard' end,
            } end,
            character_damage = function() return {health_ratio = function() return 1.0 end} end,
        }
        registered_messages = {}
        managers.player = PlayerManager
        PlayerManager.player_unit = function() return local_player end
        PlayerManager.current_state = function() return 'standard' end
        PlayerManager.register_message = function(self, msg_id, uid, callback)
            registered_messages[#registered_messages+1] = {
                msg_id = msg_id, uid = uid, callback = callback
            }
        end
        PlayerManager.local_player = function() return local_player end
        PlayerManager.has_special_equipment = function() return true end
        managers.groupai = {state = function() return {
            whisper_mode = function() return whisper_mode_val end,
        } end}
        function enemy(id, animation, rope, action, position, cool, fwd)
            local unit = {
                base = function() return {_tweak_table = id or 'cop'} end,
                anim_data = function() return animation or {} end,
                position = function() return position or {x=0,y=100,z=0} end,
                rotation = function() return {
                    y = function() return _enemy_fwd or {x=0,y=1,z=0} end,
                } end,
                movement = function() return {
                    _active_actions = {action},
                    rope_unit = function() return rope end,
                    cool = function() return cool end,
                } end,
                key = function() return 'unit_key_' .. (id or 'cop') end,
            }
            return unit
        end
        function make_cop_damage(unit, is_husk)
            local cls = is_husk and HuskCopDamage or CopDamage
            local obj = setmetatable({_unit = unit, _dead = false}, {__index = cls})
            return obj
        end
        function set_player_position(x, y, z)
            local_player.position = function() return {x=x, y=y, z=z} end
        end
        function set_enemy_forward(fx, fy, fz)
            _enemy_fwd = {x=fx, y=fy, z=fz}
        end
        function clear_enemy_forward()
            _enemy_fwd = nil
        end
        function install_wrapped_methods()
        end
    '''


class StealthHooksOrderTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + '/'
        self.lua.execute(_common_stubs())

    def load(self, name, context):
        self.lua.globals().RequiredScript = context
        self.lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

    def test_stealth_module_loads_in_copdamage_context(self):
        self.load('core.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_combat_medals.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_stealth.lua', 'lib/units/enemies/cop/copdamage')
        self.lua.execute('''
            install_wrapped_methods()
        ''')

    def test_damage_bullet_prehook_installed(self):
        self.load('core.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_combat_medals.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_stealth.lua', 'lib/units/enemies/cop/copdamage')
        self.lua.execute('''
            install_wrapped_methods()
            local pre = _pre_hooks[CopDamage] and _pre_hooks[CopDamage]["damage_bullet"]
            assert(pre and #pre >= 1, 'PreHook on damage_bullet must be installed')
            local pre_melee = _pre_hooks[CopDamage] and _pre_hooks[CopDamage]["damage_melee"]
            assert(pre_melee and #pre_melee >= 1, 'PreHook on damage_melee must be installed')
        ''')

    def test_no_redundant_on_killshot_hook(self):
        self.load('core.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_combat_medals.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_stealth.lua', 'lib/managers/playermanager')
        self.lua.execute('''
            local post = _post_hooks[PlayerManager] and _post_hooks[PlayerManager]["on_killshot"]
            local has_stealth_killshot = false
            if post then
                for _, entry in ipairs(post) do
                    if entry.id == "KH_StealthOnKillshot" then has_stealth_killshot = true end
                end
            end
            assert(not has_stealth_killshot, 'KH_StealthOnKillshot must be removed (redundant)')
        ''')


class StealthDetectionHostTests(unittest.TestCase):
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
        self.load('ky_killfeed.lua', 'lib/units/enemies/cop/huskcopdamage')
        self.load('ky_stealth.lua', 'lib/units/enemies/cop/copdamage')
        self.load('ky_playerinventory.lua', 'lib/units/beings/player/playerinventory')
        self.lua.execute('''
            install_wrapped_methods()
            kyohud.settings = {enable_killfeed = true, killfeed_size = 5}
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
        ''')

    def load(self, name, context):
        self.lua.globals().RequiredScript = context
        self.lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

    def test_host_melee_stealth_cool_guard(self):
        """Host: melee kill on cool guard during whisper -> Silent medal"""
        self.lua.execute('''
            whisper_mode_val = true
            clear_enemy_forward()
            local victim = enemy('security', nil, nil, nil, nil, true)
            local dmg = make_cop_damage(victim, false)
            dmg:damage_melee({attacker_unit = local_player, variant = 'melee', weapon_unit = local_player})
            assert(count_event('silent_guard') == 1, 'Silent medal not emitted')
            assert(count_event('stealth_melee') == 0, 'Au contact should be exclusive')
        ''')

    def test_host_melee_stealth_alerted_guard(self):
        """Host: melee kill on alerted guard during whisper -> Au contact medal"""
        self.lua.execute('''
            whisper_mode_val = true
            clear_enemy_forward()
            local victim = enemy('security', nil, nil, nil, nil, false)
            local dmg = make_cop_damage(victim, false)
            dmg:damage_melee({attacker_unit = local_player, variant = 'melee', weapon_unit = local_player})
            assert(count_event('stealth_melee') == 1, 'Au contact medal not emitted')
            assert(count_event('silent_guard') == 0, 'Silent should be exclusive')
        ''')

    def test_host_bullet_frontal_stealth_no_medal_but_stealth_flag(self):
        """Host: frontal bullet kill during whisper -> stealth flag on entry, NO medal"""
        self.lua.execute('''
            whisper_mode_val = true
            clear_enemy_forward()
            local victim = enemy('cop', nil, nil, nil, nil, false)
            local dmg = make_cop_damage(victim, false)
            dmg:damage_bullet({attacker_unit = local_player, variant = 'bullet', weapon_unit = local_player})
            assert(count_event('stealth_melee') == 0, 'no melee medal for bullet')
            assert(count_event('silent_guard') == 0, 'no silent medal for bullet')
            local kill = kyohud._kills[#kyohud._kills]
            assert(kill, 'kill entry must exist')
            assert(kill.stealth == true, 'stealth flag missing from bullet kill in whisper')
        ''')

    def test_host_loud_no_stealth(self):
        """Host: kill outside whisper -> no stealth flag, no medal"""
        self.lua.execute('''
            whisper_mode_val = false
            clear_enemy_forward()
            local victim = enemy('cop', nil, nil, nil, nil, false)
            local dmg = make_cop_damage(victim, false)
            dmg:damage_bullet({attacker_unit = local_player, variant = 'bullet', weapon_unit = local_player})
            local kill = kyohud._kills[#kyohud._kills]
            assert(kill.stealth == nil or kill.stealth == false, 'loud kill must not have stealth flag')
            assert(count_event('stealth_melee') == 0, 'no stealth medal in loud')
        ''')

    def test_host_stealth_to_loud_transition_no_leak(self):
        """Host: stealth kill then loud kill -> loud has no stealth state"""
        self.lua.execute('''
            whisper_mode_val = true
            clear_enemy_forward()
            local v1 = enemy('cop', nil, nil, nil, nil, false)
            local d1 = make_cop_damage(v1, false)
            d1:damage_bullet({attacker_unit = local_player, variant = 'bullet'})
            local stealth_count_after_first = kyohud._kills[#kyohud._kills].stealth == true and 1 or 0
            whisper_mode_val = false
            local v2 = enemy('cop', nil, nil, nil, nil, false)
            local d2 = make_cop_damage(v2, false)
            d2:damage_bullet({attacker_unit = local_player, variant = 'bullet'})
            local last = kyohud._kills[#kyohud._kills]
            assert(last.stealth == nil or last.stealth == false, 'loud kill leaked stealth')
        ''')

    def test_host_duplicate_kill_no_double_medal(self):
        """Host: same unit killed twice (dedup) -> medals only once"""
        self.lua.execute('''
            whisper_mode_val = true
            clear_enemy_forward()
            local victim = enemy('security', nil, nil, nil, nil, false)
            local d1 = make_cop_damage(victim, false)
            d1:damage_melee({attacker_unit = local_player, variant = 'melee', weapon_unit = local_player})
            local first_count = count_event('stealth_melee')
            local d2 = make_cop_damage(victim, false)
            d2:damage_melee({attacker_unit = local_player, variant = 'melee', weapon_unit = local_player})
            assert(count_event('stealth_melee') == first_count, 'duplicate must not emit medal again')
        ''')

    def test_host_sentry_no_stealth_medal(self):
        """Host: sentry kill during stealth -> no stealth medals"""
        self.lua.execute('''
            whisper_mode_val = true
            clear_enemy_forward()
            local victim = enemy('cop', nil, nil, nil, nil, true)
            local sentry_unit = {base = function() return {
                sentry_gun = true,
                get_owner = function() return local_player end,
            } end}
            local dmg = make_cop_damage(victim, false)
            dmg:damage_bullet({attacker_unit = sentry_unit, variant = 'bullet', weapon_unit = sentry_unit})
            assert(count_event('stealth_melee') == 0, 'no stealth medal for sentry')
            assert(count_event('silent_guard') == 0, 'no silent medal for sentry')
        ''')

    def test_host_civilian_no_stealth_medal(self):
        """Host: civilian kill during stealth -> no stealth medals"""
        self.lua.execute('''
            whisper_mode_val = true
            clear_enemy_forward()
            local victim = enemy('civilian', nil, nil, nil, nil, true)
            local dmg = make_cop_damage(victim, false)
            dmg:damage_melee({attacker_unit = local_player, variant = 'melee'})
            assert(count_event('stealth_melee') == 0, 'no stealth medal for civilian')
            assert(count_event('silent_guard') == 0, 'no silent medal for civilian')
        ''')

    def test_host_non_lethal_cleanup_no_stale_state(self):
        """Host: non-lethal damage then different attack kills -> no stale stealth state"""
        self.lua.execute('''
            whisper_mode_val = true
            clear_enemy_forward()
            local victim = enemy('cop', nil, nil, nil, nil, false)
            local dmg = make_cop_damage(victim, false)
            dmg:damage_bullet({attacker_unit = local_player, variant = 'bullet'})
            local kill1 = kyohud._kills[#kyohud._kills]
            assert(kill1.stealth == true, 'first kill should be stealth')
            assert(kyohud._stealth_pre_die_states[victim] == nil, 'capture must be cleaned up')
        ''')


class StealthClientPathTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.globals().ModPath = ROOT.as_posix() + '/'
        self.lua.execute(_common_stubs())
        self.lua.execute('is_client_val = true')
        self.load('core.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_combat_medals.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_hud_banners.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_buff_render.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_killfeed.lua', 'lib/managers/playermanager')
        self.load('ky_killfeed.lua', 'lib/units/enemies/cop/copdamage')
        self.load('ky_killfeed.lua', 'lib/units/enemies/cop/huskcopdamage')
        self.load('ky_stealth.lua', 'lib/units/enemies/cop/copdamage')
        self.load('ky_playerinventory.lua', 'lib/units/beings/player/playerinventory')
        self.lua.execute('''
            install_wrapped_methods()
            kyohud.settings = {enable_killfeed = true, killfeed_size = 5}
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
        ''')

    def load(self, name, context):
        self.lua.globals().RequiredScript = context
        self.lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

    def test_client_husk_melee_stealth_cool_guard(self):
        """Client: HuskCopDamage melee kill on cool guard -> Silent medal via on_killshot path"""
        self.lua.execute('''
            whisper_mode_val = true
            clear_enemy_forward()
            local victim = enemy('security', nil, nil, nil, nil, true)
            local dmg = make_cop_damage(victim, true)
            dmg:damage_melee({attacker_unit = local_player, variant = 'melee', weapon_unit = local_player})
            assert(count_event('silent_guard') == 1, 'client Silent medal not emitted')
            assert(count_event('stealth_melee') == 0, 'client: Au contact exclusive with Silent')
        ''')

    def test_client_husk_bullet_frontal_stealth(self):
        """Client: HuskCopDamage frontal bullet during whisper -> stealth flag, no medal"""
        self.lua.execute('''
            whisper_mode_val = true
            clear_enemy_forward()
            local victim = enemy('cop', nil, nil, nil, nil, false)
            local dmg = make_cop_damage(victim, true)
            dmg:damage_bullet({attacker_unit = local_player, variant = 'bullet', weapon_unit = local_player})
            assert(count_event('stealth_melee') == 0, 'no melee medal for bullet on client')
            local kill = kyohud._kills[#kyohud._kills]
            assert(kill, 'client kill entry must exist')
            assert(kill.stealth == true, 'client: stealth flag missing from bullet kill in whisper')
        ''')

    def test_client_husk_loud_no_stealth(self):
        """Client: HuskCopDamage loud kill -> no stealth flag"""
        self.lua.execute('''
            whisper_mode_val = false
            clear_enemy_forward()
            local victim = enemy('cop', nil, nil, nil, nil, false)
            local dmg = make_cop_damage(victim, true)
            dmg:damage_bullet({attacker_unit = local_player, variant = 'bullet', weapon_unit = local_player})
            local kill = kyohud._kills[#kyohud._kills]
            assert(kill.stealth == nil or kill.stealth == false, 'client: loud kill leaked stealth')
        ''')

    def test_client_capture_cleaned_after_damage_method(self):
        """Client: after damage_bullet completes, no residual stealth state"""
        self.lua.execute('''
            whisper_mode_val = true
            clear_enemy_forward()
            local victim = enemy('cop', nil, nil, nil, nil, false)
            local dmg = make_cop_damage(victim, true)
            dmg:damage_bullet({attacker_unit = local_player, variant = 'bullet'})
            assert(kyohud._stealth_pre_die_states[victim] == nil,
                'client: stealth capture not cleaned up after damage_bullet')
        ''')


class TiedCivilianTests(unittest.TestCase):
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
        self.load('ky_stealth.lua', 'lib/units/enemies/cop/copdamage')
        self.load('ky_stealth.lua', 'lib/units/civilians/logics/civilianlogicsurrender')
        self.load('ky_stealth.lua', 'lib/units/interactions/interactionext')
        self.load('ky_stealth.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_playerinventory.lua', 'lib/units/beings/player/playerinventory')
        self.lua.execute('''
            install_wrapped_methods()
            kyohud.settings = {enable_killfeed = true, killfeed_size = 5}
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
        ''')

    def load(self, name, context):
        self.lua.globals().RequiredScript = context
        self.lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

    def test_tied_civilian_stealth_host(self):
        """Host: successful tie during whisper -> Sous controle medal"""
        self.lua.execute('''
            whisper_mode_val = true
            local victim = enemy('civilian')
            kyohud._stealth_tie_intents[victim] = {whisper = true, t = 100}
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            assert(count_event('tied_civilian') == 1, 'Sous controle medal not emitted')
            assert(#kyohud._kills == 0, 'tied civilian must not produce a kill entry')
        ''')

    def test_tied_civilian_not_tied_no_medal(self):
        """not_tied=true -> no medal"""
        self.lua.execute('''
            whisper_mode_val = true
            local victim = enemy('civilian')
            kyohud._stealth_tie_intents[victim] = {whisper = true, t = 100}
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, true)
            assert(count_event('tied_civilian') == 0, 'not_tied must not emit medal')
        ''')

    def test_tied_civilian_no_intent_no_medal(self):
        """No intent (drop-in) -> no medal"""
        self.lua.execute('''
            whisper_mode_val = true
            local victim = enemy('civilian')
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            assert(count_event('tied_civilian') == 0, 'no intent must not emit medal')
        ''')

    def test_tied_civilian_intent_consumed_even_on_filter_fail(self):
        """Intent consumed even if later filter fails (non-civilian)"""
        self.lua.execute('''
            whisper_mode_val = true
            local victim = enemy('security')
            kyohud._stealth_tie_intents[victim] = {whisper = true, t = 100}
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            assert(kyohud._stealth_tie_intents[victim] == nil, 'intent must be consumed even if filter fails')
        ''')

    def test_tied_civilian_wrong_player_no_medal(self):
        """Third-party player intent -> no medal"""
        self.lua.execute('''
            whisper_mode_val = true
            local victim = enemy('civilian')
            kyohud._stealth_tie_intents[victim] = {whisper = true, t = 100}
            local other_player = {position = function() return {x=999,y=999,z=0} end}
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, other_player, false)
            assert(count_event('tied_civilian') == 0, 'wrong player must not emit medal')
            assert(kyohud._stealth_tie_intents[victim] == nil, 'intent consumed for wrong player')
        ''')

    def test_tied_civilian_intent_expires(self):
        """Intent expired (>4s) -> no medal"""
        self.lua.execute('''
            whisper_mode_val = true
            game_t = 100
            local victim = enemy('civilian')
            kyohud._stealth_tie_intents[victim] = {whisper = true, t = 90}
            game_t = 105
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            assert(count_event('tied_civilian') == 0, 'expired intent must not emit medal')
        ''')

    def test_tied_civilian_already_tied_no_double_medal(self):
        """Same unit tied twice -> only one medal"""
        self.lua.execute('''
            whisper_mode_val = true
            local victim = enemy('civilian')
            kyohud._stealth_tie_intents[victim] = {whisper = true, t = 100}
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            kyohud._stealth_tie_intents[victim] = {whisper = true, t = 101}
            local data2 = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data2, local_player, false)
            assert(count_event('tied_civilian') == 1, 'same unit tied twice emitted more than one medal')
        ''')

    def test_tied_civilian_reset_clears_tracking(self):
        """ResetHeistCombatState allows new tracking"""
        self.lua.execute('''
            whisper_mode_val = true
            local victim = enemy('civilian')
            kyohud._stealth_tie_intents[victim] = {whisper = true, t = 100}
            local data = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data, local_player, false)
            kyohud:ResetHeistCombatState()
            kyohud._stealth_tie_intents[victim] = {whisper = true, t = 200}
            local data2 = {is_tied = false, unit = victim, internal_data = {}}
            CivilianLogicSurrender.on_tied(data2, local_player, false)
            assert(count_event('tied_civilian') == 2, 'reset should allow new tracking')
        ''')

    def test_interaction_capture_clears_old_intent(self):
        """New interaction clears old intent before setting new one"""
        self.lua.execute('''
            whisper_mode_val = true
            local victim = enemy('civilian')
            kyohud._stealth_tie_intents[victim] = {whisper = true, t = 50}
            local old_intent = kyohud._stealth_tie_intents[victim]
            local interaction = setmetatable({
                _unit = victim,
                tweak_data = "intimidate",
                _tweak_data = {dont_need_equipment = true, special_equipment = 'cable_tie'},
            }, {__index = IntimitateInteractionExt})
            IntimitateInteractionExt.interact(interaction, local_player)
            local new_intent = kyohud._stealth_tie_intents[victim]
            assert(new_intent ~= nil, 'new intent must be set')
            assert(new_intent ~= old_intent, 'old intent must be replaced')
        ''')


class StealthKillfeedPresentationTests(unittest.TestCase):
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
        self.load('ky_killfeed.lua', 'lib/units/enemies/cop/huskcopdamage')
        self.load('ky_stealth.lua', 'lib/units/enemies/cop/copdamage')
        self.load('ky_killfeed_render.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_playerinventory.lua', 'lib/units/beings/player/playerinventory')
        self.lua.execute('''
            install_wrapped_methods()
            kyohud.settings = {enable_killfeed = true, killfeed_size = 5}
            kyohud:ResetHeistCombatState()
        ''')

    def load(self, name, context):
        self.lua.globals().RequiredScript = context
        self.lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

    def test_stealth_kill_entry_has_stealth_flag(self):
        """Kill during whisper gets stealth flag via event_info.stealth"""
        self.lua.execute('''
            whisper_mode_val = true
            clear_enemy_forward()
            local victim = enemy('cop')
            local dmg = make_cop_damage(victim, false)
            dmg:damage_bullet({attacker_unit = local_player, variant = 'bullet'})
            local kill = kyohud._kills[#kyohud._kills]
            assert(kill.stealth == true, 'stealth flag missing from kill entry')
        ''')

    def test_loud_kill_entry_no_stealth_flag(self):
        """Kill outside whisper -> no stealth flag"""
        self.lua.execute('''
            whisper_mode_val = false
            clear_enemy_forward()
            local victim = enemy('cop')
            local dmg = make_cop_damage(victim, false)
            dmg:damage_bullet({attacker_unit = local_player, variant = 'bullet'})
            local kill = kyohud._kills[#kyohud._kills]
            assert(kill.stealth == nil or kill.stealth == false, 'loud kill must not have stealth flag')
        ''')

    def test_duplicate_kill_does_not_modify_previous_entry(self):
        """Dedup: second attempt on same unit must not alter first kill entry"""
        self.lua.execute('''
            whisper_mode_val = true
            clear_enemy_forward()
            local victim = enemy('cop')
            local d1 = make_cop_damage(victim, false)
            d1:damage_bullet({attacker_unit = local_player, variant = 'bullet'})
            local first_entry = kyohud._kills[#kyohud._kills]
            local original_stealth = first_entry.stealth
            local original_name = first_entry.name
            local d2 = make_cop_damage(victim, false)
            d2:damage_bullet({attacker_unit = local_player, variant = 'bullet'})
            assert(first_entry.stealth == original_stealth, 'duplicate must not modify stealth')
            assert(first_entry.name == original_name, 'duplicate must not modify name')
            assert(#kyohud._kills == 1, 'duplicate must not add second entry')
        ''')


class StealthLabelRenderTests(unittest.TestCase):
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
        self.load('ky_stealth.lua', 'lib/units/enemies/cop/copdamage')
        self.load('ky_killfeed_render.lua', 'lib/managers/hudmanagerpd2')
        self.load('ky_localization.lua', 'lib/managers/localizationmanager')
        self.lua.execute('''
            kyohud.settings = {enable_killfeed = true, killfeed_size = 5}
            kyohud:ResetHeistCombatState()
        ''')

    def load(self, name, context):
        self.lua.globals().RequiredScript = context
        self.lua.execute((ROOT / 'lua' / name).read_text(encoding='utf-8-sig'))

    def test_stealth_label_key_exists_in_render(self):
        render_src = (ROOT / 'lua' / 'ky_killfeed_render.lua').read_text(encoding='utf-8-sig')
        self.assertIn('ky_hud_stealth_kill_label', render_src)

    def test_stealth_color_used_for_stealth_cards(self):
        render_src = (ROOT / 'lua' / 'ky_killfeed_render.lua').read_text(encoding='utf-8-sig')
        self.assertIn('STEALTH_KILLFEED_COLOR', render_src)
        self.assertIn('kill.stealth', render_src)

    def test_full_display_text_used_in_draw(self):
        render_src = (ROOT / 'lua' / 'ky_killfeed_render.lua').read_text(encoding='utf-8-sig')
        self.assertIn('_full_display_text', render_src)


if __name__ == "__main__":
    unittest.main()