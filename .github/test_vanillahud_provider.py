"""VanillaHUD+ provider regressions against the real KyoHUD core chunk.

Run: uv run --with lupa python -B -m unittest discover -s .github -p test_vanillahud_provider.py -v
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime

ROOT = Path(__file__).resolve().parents[1]


class VanillaHUDBuffProviderTests(unittest.TestCase):
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
            local function color()
                return {with_alpha = function(self) return self end}
            end
            Color = setmetatable({white = color(), black = color()}, {
                __call = function(...) return color() end
            })
            TimerManager = {
                game = function()
                    return {time = function() return 100 end}
                end
            }
        ''')
        self.lua.execute((ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig"))
        self.lua.execute('kyohud.settings = {enable_buffs = true}')

    def test_kyohud_presentation_is_loaded_from_its_own_module(self):
        presentation_path = ROOT / "lua" / "ky_buff_presentation.lua"
        self.assertTrue(presentation_path.is_file())

        source = (ROOT / "lua" / "core.lua").read_text(encoding="utf-8-sig")
        self.assertIn('dofile(MY_MOD_PATH .. "lua/ky_buff_presentation.lua")', source)
        self.assertNotIn("local KYO_BUFF_PRESENTATION = {", source)
        self.assertNotIn("local KYO_BUFF_COLORS = {", source)

        self.lua.execute('''
            assert(kyohud.KYO_BUFF_PRESENTATION.damage_increase.fixed_slot == 6)
            assert(kyohud.KYO_BUFF_PRESENTATION.damage_increase.label.placement == "timer")
            assert(kyohud.KYO_BUFF_PRESENTATION.pocket_ecm_jammer_debuff.separate_source == true)
        ''')

    def test_definition_is_resolved_lazily_from_vanillahud_map(self):
        self.lua.execute('''
            HUDList = nil
            assert(kyohud:GetVanillaHUDBuffDefinition("overkill") == nil)

            local definition = {skills_new = {2, 0}, class = "TimedBuffItem"}
            HUDList = {BuffItemBase = {MAP = {overkill = definition}}}

            assert(kyohud:GetVanillaHUDBuffDefinition("overkill") == definition)
        ''')

    def test_buff_icon_uses_only_the_exact_runtime_map_entry(self):
        self.lua.execute('''
            function Idstring(value) return value end
            DB = {has = function() return true end}
            HUDList = {BuffItemBase = {MAP = {
                runtime_only = {texture = "runtime/exact"},
            }}}

            kyohud:add_buff("runtime_only", nil, nil, nil, true)
            kyohud:add_buff("overkill", nil, nil, nil, true)

            assert(kyohud._buffs.runtime_only.icon.texture == "runtime/exact")
            assert(kyohud._buffs.overkill.icon.texture == "guis/textures/pd2/hud_timer",
                "a missing runtime definition fell back to the local catalog")
        ''')

    def test_buff_title_uses_runtime_localized_and_literal_metadata(self):
        self.lua.execute('''
            managers.localization = {
                text = function(self, id)
                    if id == "vhud_aced" then return "ACED" end
                    return "ERROR: " .. tostring(id)
                end,
            }
            HUDList = {BuffItemBase = {MAP = {
                localized_title = {title = "vhud_aced", localized = true},
                missing_translation = {title = "vhud_missing", localized = true},
                literal_title = {title = "BASIC"},
            }}}

            kyohud:add_buff("localized_title", {}, nil, nil, true)
            kyohud:add_buff("missing_translation", {}, nil, nil, true)
            kyohud:add_buff("literal_title", {}, nil, nil, true)

            assert(kyohud._buffs.localized_title.title_text == "ACED")
            assert(kyohud._buffs.missing_translation.title_text == "vhud_missing")
            assert(kyohud._buffs.literal_title.title_text == "BASIC")
        ''')

    def test_show_value_function_formats_runtime_source_value(self):
        self.lua.execute('''
            HUDList = {BuffItemBase = {MAP = {
                function_value = {
                    show_value = function(value)
                        return string.format("VALUE %.1f", value)
                    end,
                },
            }}}
            HUDListManager = {BUFFS = {
                function_source = {"function_value"},
            }}
            kyohud._gameinfo_bridge_active = true

            kyohud:handle_buff_event("activate", "function_source", {value = 2.5})

            assert(kyohud._buffs.function_value.value_text == "VALUE 2.5")
        ''')

    def test_show_value_format_string_formats_runtime_source_value(self):
        self.lua.execute('''
            HUDList = {BuffItemBase = {MAP = {
                formatted_value = {show_value = "-%.1f"},
            }}}
            HUDListManager = {BUFFS = {
                formatted_source = {"formatted_value"},
            }}
            kyohud._gameinfo_bridge_active = true

            kyohud:handle_buff_event("activate", "formatted_source", {value = 3.25})

            assert(kyohud._buffs.formatted_value.value_text == "-3.2")
        ''')

    def test_timed_buff_preserves_runtime_priority_and_expiry(self):
        self.lua.execute('''
            Application = {time = function() return 100 end}
            HUDList = {BuffItemBase = {MAP = {
                timed = {class = "TimedBuffItem", priority = 7},
            }}}
            HUDListManager = {BUFFS = {timed_source = {"timed"}}}
            kyohud._gameinfo_bridge_active = true

            kyohud:handle_buff_event("activate", "timed_source", {
                t = 100,
                expire_t = 112,
            })

            local buff = kyohud._buffs.timed
            assert(buff ~= nil)
            assert(buff.duration == 12 and buff.t_end == 112 and buff.persistent == false)
            assert(buff.priority == 7)
        ''')

    def test_runtime_priority_orders_nonfixed_buffs_and_keeps_arrival_ties(self):
        self.lua.execute('''
            local panel = {bitmaps = {}, texts = {}}
            function panel:clear() self.bitmaps = {}; self.texts = {} end
            function panel:w() return 800 end
            function panel:h() return 600 end
            function panel:gradient(params) return params end
            function panel:rect(params) return params end
            function panel:polyline(params) return params end
            function panel:bitmap(params)
                self.bitmaps[#self.bitmaps + 1] = params
                return {set_color = function() end, set_alpha = function() end}
            end
            function panel:text(params)
                self.texts[#self.texts + 1] = params
                return {text_rect = function() return 0, 0, 20, 12 end}
            end
            HUDList = {BuffItemBase = {MAP = {
                late_priority = {priority = 8},
                first_equal = {priority = 2},
                second_equal = {priority = 2},
            }}}
            kyohud._panel = panel
            kyohud._kills = {}
            kyohud.settings = {
                enable_buffs = true,
                enable_killfeed = false,
                icon_size = 32,
                opacity = 0.9,
                buff_position_x = 50,
                buff_position_y = 85,
                circle_radius = 250,
                buff_toggles = {equipped_perk_deck = false},
            }

            kyohud:add_buff("late_priority", {texture = "p8"}, nil, nil, true)
            kyohud:add_buff("first_equal", {texture = "equal_first"}, nil, nil, true)
            kyohud:add_buff("second_equal", {texture = "equal_second"}, nil, nil, true)
            kyohud:draw()

            assert(panel.bitmaps[1].texture == "equal_first")
            assert(panel.bitmaps[2].texture == "equal_second")
            assert(panel.bitmaps[3].texture == "p8")
        ''')

    def test_persistent_buff_has_no_synthetic_timer(self):
        self.lua.execute('''
            HUDList = {BuffItemBase = {MAP = {
                persistent = {class = "BuffItemBase", priority = 3},
            }}}
            HUDListManager = {BUFFS = {persistent_source = {"persistent"}}}
            kyohud._gameinfo_bridge_active = true

            kyohud:handle_buff_event("activate", "persistent_source", {})

            local buff = kyohud._buffs.persistent
            assert(buff ~= nil)
            assert(buff.persistent == true)
            assert(buff.duration == nil and buff.t_end == nil)
            assert(buff.provider_class == "BuffItemBase" and buff.priority == 3)
        ''')

    def test_runtime_stack_count_uses_kyohud_badge(self):
        self.lua.execute('''
            HUDList = {BuffItemBase = {MAP = {
                stacked = {class = "BuffItemBase"},
            }}}
            HUDListManager = {BUFFS = {stacked_source = {"stacked"}}}
            kyohud._gameinfo_bridge_active = true

            kyohud:handle_buff_event("activate", "stacked_source", {stack_count = 4})

            assert(kyohud._buffs.stacked.stack_text == "x4")
        ''')

    def test_timed_stack_expiry_tracks_latest_stack_and_removes_empty_item(self):
        self.lua.execute('''
            app_t = 100
            game_t = 100
            Application = {time = function() return app_t end}
            TimerManager = {game = function()
                return {time = function() return game_t end}
            end}
            HUDList = {BuffItemBase = {MAP = {
                timed_stacks = {class = "TimedStacksBuffItem"},
            }}}
            HUDListManager = {BUFFS = {timed_stack_source = {"timed_stacks"}}}
            kyohud._gameinfo_bridge_active = true

            kyohud:handle_buff_event("add_timed_stack", "timed_stack_source", {
                stacks = {
                    {t = 99, expire_t = 104},
                    {t = 100, expire_t = 109},
                },
            })

            local buff = kyohud._buffs.timed_stacks
            assert(buff ~= nil and buff.duration == 9 and buff.t_end == 109)
            assert(buff.stack_text == "x2")

            app_t = 105
            game_t = 105
            kyohud:handle_buff_event("remove_timed_stack", "timed_stack_source", {
                stacks = {{t = 100, expire_t = 109}},
            })
            buff = kyohud._buffs.timed_stacks
            assert(buff ~= nil and buff.duration == 4 and buff.t_end == 109)
            assert(buff.stack_text == "x1")

            kyohud:handle_buff_event("remove_timed_stack", "timed_stack_source", {
                stacks = {},
            })
            assert(kyohud._buffs.timed_stacks == nil)
        ''')

    def test_kyohud_timer_label_survives_without_catalog_metadata(self):
        self.lua.execute('''
            managers.localization = {text = function() return "DAMAGE+" end}
            HUDList = {BuffItemBase = {MAP = {
                damage_increase = {title = "upstream_title"},
            }}}
            kyohud.BUFF_MAP.damage_increase = nil

            kyohud:add_buff("damage_increase", {}, nil, nil, true, false, "+25%")

            local buff = kyohud._buffs.damage_increase
            assert(buff.label_text == "DAMAGE+")
            assert(buff.label_placement == "timer")
            assert(buff.title_text == "upstream_title")
            assert(buff.color ~= Color.white)
        ''')

    def test_kyohud_aggregate_value_survives_without_catalog_metadata(self):
        self.lua.execute('''
            HUDList = {BuffItemBase = {MAP = {
                passive_health_regen = {class = "PassiveHealthRegenBuff"},
            }}}
            HUDListManager = {BUFFS = {
                regen_a = {"passive_health_regen"},
                regen_b = {"passive_health_regen"},
            }}
            kyohud.BUFF_MAP.passive_health_regen = nil
            kyohud._gameinfo_bridge_active = true

            kyohud:handle_buff_event("activate", "regen_a", {value = 0.01})
            kyohud:handle_buff_event("activate", "regen_b", {value = 0.02})

            assert(kyohud._buffs.passive_health_regen.value_text == "3.0%")
        ''')

    def test_source_targets_are_filtered_through_vanillahud_map(self):
        self.lua.execute('''
            HUDList = {BuffItemBase = {MAP = {
                berserker = {},
                damage_increase = {},
            }}}
            HUDListManager = {BUFFS = {
                berserker_aced = {
                    "berserker", "damage_increase", "missing_entry"
                }
            }}

            local targets = kyohud:GetVanillaHUDBuffTargets("berserker_aced")
            assert(#targets == 2)
            assert(targets[1] == "berserker")
            assert(targets[2] == "damage_increase")
        ''')

    def test_unmapped_source_uses_matching_vanillahud_definition(self):
        self.lua.execute('''
            HUDList = {BuffItemBase = {MAP = {inspire = {}}}}
            HUDListManager = {BUFFS = {}}

            local targets = kyohud:GetVanillaHUDBuffTargets("inspire")
            assert(#targets == 1)
            assert(targets[1] == "inspire")
        ''')

    def test_composite_debuff_uses_vanillahud_parent_definition(self):
        self.lua.execute('''
            HUDList = {BuffItemBase = {MAP = {grinder = {}}}}
            HUDListManager = {BUFFS = {
                composite_debuffs = {grinder_debuff = "grinder"},
            }}

            local targets = kyohud:GetVanillaHUDBuffTargets("grinder_debuff")
            assert(#targets == 1)
            assert(targets[1] == "grinder")
        ''')

    def test_pocket_ecm_cooldown_remains_a_separate_kyohud_cell(self):
        self.lua.execute('''
            HUDList = {BuffItemBase = {MAP = {
                pocket_ecm_jammer = {},
                pocket_ecm_jammer_debuff = {},
            }}}
            HUDListManager = {BUFFS = {
                composite_debuffs = {
                    pocket_ecm_jammer_debuff = "pocket_ecm_jammer",
                },
            }}

            local targets = kyohud:GetVanillaHUDBuffTargets("pocket_ecm_jammer_debuff")
            assert(#targets == 1)
            assert(targets[1] == "pocket_ecm_jammer_debuff")
        ''')

    def test_equipped_deck_promotion_is_owned_by_kyohud_presentation(self):
        self.lua.execute('''
            kyohud.PERK_DECK_BUFFS = nil

            local armorer = kyohud:GetKyoEquippedPerkBuffCandidates(3)
            local hacker = kyohud:GetKyoEquippedPerkBuffCandidates(21)
            local copycat = kyohud:GetKyoEquippedPerkBuffCandidates(23)

            assert(#armorer == 1 and armorer[1] == "armor_break_invulnerable")
            assert(#hacker == 0, "Hacker must retain its equipped-deck cell")
            assert(copycat[1] == "copycat_health_invul")
            assert(copycat[#copycat] == "copr_ability")
        ''')

    def test_equipped_skill_counter_is_owned_by_kyohud_presentation(self):
        self.lua.execute('''
            HUDList = {BuffItemBase = {MAP = {partner_in_crime = {priority = 3}}}}
            kyohud.BUFF_MAP.partner_in_crime = nil
            managers.skilltree = {skill_step = function() return 1 end}
            managers.player = {
                num_local_minions = function() return 1 end,
                upgrade_value = function() return 2 end,
            }

            kyohud:RefreshEquippedSkillCounters()

            local buff = kyohud._buffs.partner_in_crime
            assert(buff ~= nil and buff.persistent == true)
            assert(buff.value_text == "1/2")
        ''')

    def test_bridge_waits_until_vanillahud_metadata_is_available(self):
        self.lua.execute('''
            local registrations = 0
            managers.gameinfo = {
                register_listener = function() registrations = registrations + 1 end,
                get_buffs = function() return {} end,
                get_player_actions = function() return {} end,
            }
            HUDList = nil
            HUDListManager = nil

            assert(kyohud:TryRegisterGameInfoBridge() == false)
            assert(registrations == 0)
            assert(kyohud._gameinfo_bridge_active ~= true)
        ''')

    def test_bridge_uses_vanillahud_targets_for_unknown_sources(self):
        self.lua.execute('''
            local listeners = {}
            managers.gameinfo = {
                register_listener = function(self, listener_id, source, event, callback)
                    listeners[source .. ":" .. event] = callback
                end,
                get_buffs = function() return {} end,
                get_player_actions = function() return {} end,
            }
            HUDList = {BuffItemBase = {MAP = {
                future_buff = {skills_new = {1, 2}, class = "TimedBuffItem"},
            }}}
            HUDListManager = {BUFFS = {
                future_source = {"future_buff"},
            }}
            kyohud.GetBuffTargets = nil

            assert(kyohud:TryRegisterGameInfoBridge() == true)
            listeners["buff:activate"]("activate", "future_source", {duration = 8})

            assert(kyohud._buffs.future_buff ~= nil, "mapped buff was not created")
            assert(kyohud._buffs.future_buff.duration == 8, "mapped duration was not preserved")
        ''')

    def test_successful_bridge_registration_is_idempotent(self):
        self.lua.execute('''
            local registrations = 0
            managers.gameinfo = {
                register_listener = function() registrations = registrations + 1 end,
                get_buffs = function() return {} end,
                get_player_actions = function() return {} end,
            }
            HUDList = {BuffItemBase = {MAP = {}}}
            HUDListManager = {BUFFS = {}}

            assert(kyohud:TryRegisterGameInfoBridge() == true)
            local first_count = registrations
            assert(first_count > 0)
            assert(kyohud:TryRegisterGameInfoBridge() == true)
            assert(registrations == first_count)
        ''')

    def test_panel_rebuild_removes_only_kyohud_owned_panels(self):
        self.lua.execute('''
            local current = {name = "kyohud_buff_panel"}
            local legacy = {name = "kyosh1ro_buff_panel"}
            local foreign = {name = "vanillahud_buff_list"}
            local removed = {}
            local created
            local parent = {}
            function parent:child(name)
                if name == current.name then return current end
                if name == legacy.name then return legacy end
                if name == foreign.name then return foreign end
            end
            function parent:remove(panel)
                removed[#removed + 1] = panel.name
            end
            function parent:panel(params)
                created = params.name
                return {name = params.name}
            end
            PlayerBase = {
                PLAYER_INFO_HUD_PD2 = "player_info",
                PLAYER_INFO_HUD_FULLSCREEN_PD2 = "fullscreen",
            }
            managers.hud = {script = function() return {panel = parent} end}

            assert(kyohud:ensure_panel(true) == true)
            assert(#removed == 2)
            assert(removed[1] == "kyohud_buff_panel")
            assert(removed[2] == "kyosh1ro_buff_panel")
            assert(created == "kyohud_buff_panel")
        ''')


if __name__ == "__main__":
    unittest.main()
