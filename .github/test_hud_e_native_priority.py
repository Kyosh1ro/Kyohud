"""_apply_native_priority -- real paths: only indispensable leaves block, not whole containers.

Scope: native teammate panel structure mirrors PAYDAY 2 runtime (hudteammate.lua):
  entry._panel -> child("player") -> carry_panel, interact_panel
  entry._panel -> child("player") -> radial_health_panel
  radial_health_panel children: condition_timer (WRONG: actually under entry._panel),
    radial_custom, radial_ability, radial_rip, radial_rip_bg (sibling of radial_rip),
    radial_absorb_shield_active, radial_absorb_health_active, radial_info_meter,
    radial_info_meter_bg, radial_delayed_damage (container, initially empty default-visible),
    copr_overlay_panel (container, initially empty default-visible)
  radial_delayed_damage children: radial_delayed_damage_armor, radial_delayed_damage_health
  entry._panel -> condition_timer (NOT under radial_health_panel)

Only actual indispensable leaves with active geometry block KyoHUD crew/player when
they overlap. Ordinary name/health/shield and empty containers (radial_delayed_damage,
copr_overlay_panel without child 0) NEVER block. For copr_overlay_panel, only consider
its rectangle if exact child "0" exists/alive (set_copr_indicator creates numeric 0).

Uses test_hud_final_integration._crew_lua fixture (returns 4 values).
No production monkeypatch/certification. Setter spy counts installed AFTER fixture
move each time; never count test mutations. Compare native fields exactly at each step.
Real runtime consumers, no certification monkeypatches.

Expected: current production _apply_native_priority inspects exact leaf paths via
bounded child lookups, skipping empty containers, with no recursive scans.
"""
import unittest

from test_hud_final_integration import _crew_lua
from test_hud_crew_acceptance import mounted


class NativePanelPriorityTests(unittest.TestCase):
    def test_native_panel_priority_blocks_crew_and_player(self):
        """Real native paths: indispensable leaves block, containers do not.

        Constructs actual PAYDAY 2 native teammate panel structure:
          entry._panel -> player -> carry_panel, interact_panel
          entry._panel -> player -> radial_health_panel -> radial_custom, ...
          entry._panel -> condition_timer (NOT under radial)
        The container (entry._panel, player child) being visible does NOT block.
        Only condition_timer with active geometry overlapping crew/player blocks.
        """
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        self.assertTrue(crew_ok, "crew.lua must exist")
        self.assertTrue(weapons_ok, "weapons.lua must exist")
        self.assertTrue(equipment_ok, "equipment.lua must exist")

        lua.execute(r'''
            -- Configuration: foundation/player/crew/weapons/equipment all true
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            kyohud.settings.enable_crew = true
            kyohud.settings.enable_weapons = true
            kyohud.settings.enable_equipment = true
            kyohud.settings.hud_scale = 1.0
            _G.panel_double:set_shape(0, 0, 1920, 1080)

            -- Third-party sibling sentinel
            local sibling = _G.panel_double:panel({name="third_party_sentinel"})
            sibling:set_shape(100, 200, 150, 250)
            sibling:set_visible(true)
            _sibling_x_before = sibling:x()
            _sibling_y_before = sibling:y()
            _sibling_w_before = sibling:w()
            _sibling_h_before = sibling:h()
            _sibling_vis_before = sibling:visible()

            -- Create real native teammate panel structure at crew geometry
            local native_entry_panel = _G.panel_double:panel({name="native_teammate_entry"})
            native_entry_panel:set_shape(44, 918, 432, 120)
            native_entry_panel:set_visible(true)

            -- Player child container (NOT a blocker itself)
            local native_player = native_entry_panel:panel({name="player"})
            native_player:set_shape(0, 0, 432, 120)
            native_player:set_visible(true)

            -- radial_health_panel container (NOT a blocker itself)
            local native_radial_health = native_player:panel({name="radial_health_panel"})
            native_radial_health:set_shape(0, 0, 432, 120)
            native_radial_health:set_visible(true)

            -- condition_timer under entry._panel (NOT radial_health_panel)
            local condition_timer = native_entry_panel:text({
                name="condition_timer",
                text="timer",
                font="fonts/font_medium_mf"
            })
            -- Position to overlap crew area (crew at x=44, y=918)
            condition_timer:set_shape(100, 40, 200, 30)
            condition_timer:set_visible(false)  -- initially inactive

            -- Add other native leaves with inactive initial visibility
            local carry_panel = native_player:panel({name="carry_panel"})
            carry_panel:set_shape(50, 50, 100, 40)
            carry_panel:set_visible(false)

            local interact_panel = native_player:text({name="interact_panel", text="X", font="f"})
            interact_panel:set_shape(60, 60, 80, 30)
            interact_panel:set_visible(false)

            local radial_custom = native_radial_health:bitmap({name="radial_custom"})
            radial_custom:set_shape(0, 0, 432, 120)
            radial_custom:set_visible(false)

            local radial_ability = native_radial_health:panel({name="radial_ability"})
            radial_ability:set_shape(0, 0, 432, 120)
            radial_ability:set_visible(false)

            local radial_rip = native_radial_health:bitmap({name="radial_rip"})
            radial_rip:set_shape(0, 0, 432, 120)
            radial_rip:set_visible(false)

            -- radial_rip_bg is SIBLING of radial_rip under radial_health_panel
            local radial_rip_bg = native_radial_health:bitmap({name="radial_rip_bg", color=Color(0,0,0)})
            radial_rip_bg:set_shape(0, 0, 432, 120)
            radial_rip_bg:set_visible(false)

            -- Empty radial_delayed_damage (default visible, MUST NOT block)
            local radial_delayed_damage = native_radial_health:panel({name="radial_delayed_damage"})
            radial_delayed_damage:set_shape(0, 0, 432, 120)
            radial_delayed_damage:set_visible(true)  -- default visible but empty

            -- Empty copr_overlay_panel (default visible, MUST NOT block)
            local copr_overlay_panel = native_radial_health:panel({name="copr_overlay_panel"})
            copr_overlay_panel:set_shape(0, 0, 432, 120)
            copr_overlay_panel:set_visible(true)  -- default visible but empty

            -- Native-shaped manager._teammate_panels with REAL structure
            managers.hud._teammate_panels = {[1] = {_panel = native_entry_panel, _special_equipment = {}}}

            -- ACT: refresh_crew then mount/refresh/update with ALL enabled
            local mgr = managers.hud
            local ACT = kyohud.hud.actors
            ACT:refresh_crew(mgr, 0)
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.runtime:update(mgr, 1.0, 0.05)

            local P = kyohud.hud.player
            local C = kyohud.hud.crew
            local WEAP = kyohud.hud.weapons
            local E = kyohud.hud.equipment

            -- Real P and crew must certify before blockers
            _p_verify_before = P and P:verify() or false
            _c_verify_before = C and C:_verify_render() or false
            _weap_verify_before = WEAP and WEAP:verify() or false
            _e_verify_before = E and E:verify() or false

            -- ALL owned modules must be visible under ordinary native containers
            _p_root_visible_1_0 = P._root and P._root:visible() or false
            _c_root_visible_1_0 = C._root and C._root:visible() or false
            _weap_root_visible_1_0 = WEAP._root and WEAP._root:visible() or false
            _e_root_visible_1_0 = E._root and E._root:visible() or false

            -- Save root/primitives for identity checks
            _p_root_before = P._root
            _c_root_before = C._root
            _weap_root_before = WEAP._root
            _e_root_before = E._root
            _p_gauge_before = P._gauge
            _p_health_text_before = P._gauge and P._gauge.health_text or nil

            -- Activate condition_timer (the indispensable leaf)
            condition_timer:set_visible(true)

            -- Update 1.6: crew root should be hidden due to condition_timer blocker
            kyohud.hud.runtime:update(mgr, 1.6, 0.05)

            _c_root_visible_1_6 = C._root and C._root:visible() or false
            _p_root_visible_1_6 = P._root and P._root:visible() or false
            _weap_root_visible_1_6 = WEAP._root and WEAP._root:visible() or false
            _e_root_visible_1_6 = E._root and E._root:visible() or false

            -- Native containers still visible with same shape
            _native_entry_x_1_6 = native_entry_panel:x()
            _native_entry_vis_1_6 = native_entry_panel:visible()
            _native_player_vis_1_6 = native_player:visible()
            _native_radial_vis_1_6 = native_radial_health:visible()
            _native_timer_vis_1_6 = condition_timer:visible()

            -- Deactivate condition_timer, activate carry_panel at crew area
            condition_timer:set_visible(false)
            carry_panel:set_shape(100, 40, 200, 30)  -- overlap crew
            carry_panel:set_visible(true)

            -- Update 2.2: crew should still be hidden due to carry_panel
            kyohud.hud.runtime:update(mgr, 2.2, 0.05)
            _c_root_visible_2_2 = C._root and C._root:visible() or false
            _carry_vis_2_2 = carry_panel:visible()

            -- Deactivate all leaves
            carry_panel:set_visible(false)

            -- Update 2.8: all recover
            kyohud.hud.runtime:update(mgr, 2.8, 0.05)
            _c_root_visible_2_8 = C._root and C._root:visible() or false
            _p_root_visible_2_8 = P._root and P._root:visible() or false
            _weap_root_visible_2_8 = WEAP._root and WEAP._root:visible() or false
            _e_root_visible_2_8 = E._root and E._root:visible() or false

            -- Identity booleans (Lua-side, not proxy)
            _same_c = (C._root == _c_root_before)
            _same_p_root = (P._root == _p_root_before)
            _same_weap_root = (WEAP._root == _weap_root_before)
            _same_e_root = (E._root == _e_root_before)
            _same_p_gauge = (P._gauge == _p_gauge_before)
            _same_p_ht = ((P._gauge and P._gauge.health_text or nil) == _p_health_text_before)

            -- Third-party sibling intact at end
            _sibling_x_after = sibling:x()
            _sibling_y_after = sibling:y()
            _sibling_w_after = sibling:w()
            _sibling_h_after = sibling:h()
            _sibling_vis_after = sibling:visible()
            _sibling_alive_after = alive(sibling)
        ''')

        g = lua.globals()

        # Real P and crew must certify before blockers
        self.assertTrue(bool(g._p_verify_before),
            "player:verify() must be true before blockers")
        self.assertTrue(bool(g._c_verify_before),
            "crew:_verify_render() must be true before blockers")
        self.assertTrue(bool(g._weap_verify_before),
            "weapons:verify() must be true before blockers")
        self.assertTrue(bool(g._e_verify_before),
            "equipment:verify() must be true before blockers")

        # ALL owned modules visible under ordinary native containers (no active leaves)
        self.assertTrue(bool(g._p_root_visible_1_0),
            "player root must be visible under ordinary native containers")
        self.assertTrue(bool(g._c_root_visible_1_0),
            "crew root must be visible under ordinary native containers")
        self.assertTrue(bool(g._weap_root_visible_1_0),
            "weapons root must be visible under ordinary native containers")
        self.assertTrue(bool(g._e_root_visible_1_0),
            "equipment root must be visible under ordinary native containers")

        # Update 1.6: crew root hidden when condition_timer (indispensable leaf) active
        self.assertFalse(bool(g._c_root_visible_1_6),
            "crew root must be hidden when condition_timer occupies crew geometry")
        self.assertTrue(bool(g._p_root_visible_1_6),
            "player root must remain visible at 1.6 (condition_timer not at P geometry)")
        self.assertTrue(bool(g._weap_root_visible_1_6),
            "weapons root must remain visible at 1.6")
        self.assertTrue(bool(g._e_root_visible_1_6),
            "equipment root must remain visible at 1.6")

        # Native containers still visible
        self.assertTrue(bool(g._native_entry_vis_1_6))
        self.assertTrue(bool(g._native_player_vis_1_6))
        self.assertTrue(bool(g._native_radial_vis_1_6))
        self.assertTrue(bool(g._native_timer_vis_1_6))

        # Update 2.2: crew still hidden due to carry_panel
        self.assertFalse(bool(g._c_root_visible_2_2),
            "crew root must be hidden when carry_panel occupies crew geometry")
        self.assertTrue(bool(g._carry_vis_2_2))

        # Update 2.8: all recover when no active leaves
        self.assertTrue(bool(g._c_root_visible_2_8),
            "crew root must recover when no indispensable leaves active")
        self.assertTrue(bool(g._p_root_visible_2_8),
            "player root must remain visible")
        self.assertTrue(bool(g._weap_root_visible_2_8),
            "weapons root must remain visible")
        self.assertTrue(bool(g._e_root_visible_2_8),
            "equipment root must remain visible")

        # Same roots preserved (Lua boolean identity, not proxy equality)
        self.assertTrue(bool(g._same_c),
            "crew root identity must be preserved")
        self.assertTrue(bool(g._same_p_root),
            "player root identity must be preserved")
        self.assertTrue(bool(g._same_weap_root),
            "weapons root identity must be preserved")
        self.assertTrue(bool(g._same_e_root),
            "equipment root identity must be preserved")
        self.assertTrue(bool(g._same_p_gauge),
            "player gauge identity must be preserved")
        self.assertTrue(bool(g._same_p_ht),
            "player health_text identity must be preserved")

        # Third-party sibling intact
        self.assertEqual(float(g._sibling_x_after), float(g._sibling_x_before))
        self.assertEqual(float(g._sibling_y_after), float(g._sibling_y_before))
        self.assertEqual(float(g._sibling_w_after), float(g._sibling_w_before))
        self.assertEqual(float(g._sibling_h_after), float(g._sibling_h_before))
        self.assertTrue(bool(g._sibling_vis_after))
        self.assertTrue(bool(g._sibling_alive_after))

    def test_native_read_failure_fail_closed_same_primitive_recovery(self):
        """Indispensable leaf (condition_timer) getter failure: fail-closed, recover same primitives.

        Tests that when condition_timer (the actual indispensable leaf) fails to read,
        crew hides fail-closed. Recovers same primitives when leaf reader restored.
        Container (entry._panel, player) visibility/reads do not affect this test.
        """
        lua = mounted()
        lua.execute('''
            local r = C._root; local rx, ry, rw, rh = r:x(), r:y(), r:w(), r:h()
            local card = C._cards[1]; local cardname = card._name_text

            -- Create real native structure
            local native_entry = panel_double:panel({name="native_entry"})
            native_entry:set_shape(rx, ry, rw, rh)
            native_entry:set_visible(true)

            local native_player = native_entry:panel({name="player"})
            native_player:set_shape(0, 0, rw, rh)
            native_player:set_visible(true)

            local native_radial = native_player:panel({name="radial_health_panel"})
            native_radial:set_shape(0, 0, rw, rh)
            native_radial:set_visible(true)

            -- condition_timer under entry._panel (NOT radial_health_panel)
            local condition_timer = native_entry:text({
                name="condition_timer", text="timer", font="f"
            })
            condition_timer:set_shape(0, 0, rw, rh)
            condition_timer:set_visible(true)

            local mgr = managers.hud
            local old_tp = mgr._teammate_panels or {}
            mgr._teammate_panels = {[1] = {_panel = native_entry, _special_equipment = {}}}
            for k, v in pairs(old_tp) do if k ~= 1 then mgr._teammate_panels[k] = v end end

            local sib = panel_double:panel({name="fail_closed_sib"})
            sib:set_shape(50, 50, 80, 80); sib:set_visible(true); local sib_x = sib:x()

            -- Fail condition_timer visible reader (the indispensable leaf)
            local orig_vis = condition_timer.visible
            condition_timer.visible = function() error('getter unavailable') end
            RT:update(mgr, 1.6, 0.05)
            _c_hidden_1_6 = not C._root:visible()
            condition_timer.visible = orig_vis

            RT:update(mgr, 2.2, 0.05)
            _c_hidden_2_2 = not C._root:visible()
            condition_timer:set_visible(false)
            RT:update(mgr, 2.8, 0.05)
            _c_verify_2_8 = C:_verify_render()
            _same_root_2_8 = C._root == r
            _same_card_2_8 = C._cards[1] == card
            _same_name_2_8 = C._cards[1]._name_text == cardname

            -- Fail condition_timer alpha reader
            condition_timer:set_visible(true)
            local orig_alpha = condition_timer.alpha
            condition_timer.alpha = function() return 0/0 end
            RT:update(mgr, 3.4, 0.05)
            _c_hidden_3_4 = not C._root:visible()
            condition_timer.alpha = orig_alpha
            condition_timer:set_visible(false)
            RT:update(mgr, 4.0, 0.05)
            _c_verify_4_0 = C:_verify_render()
            _same_root_4_0 = C._root == r
            _sib_intact = sib:visible() and sib:x() == sib_x
        ''')
        g = lua.globals()
        self.assertIs(g._c_hidden_1_6, True)
        self.assertIs(g._c_hidden_2_2, True)
        self.assertIs(g._c_verify_2_8, True)
        self.assertIs(g._same_root_2_8, True)
        self.assertIs(g._same_card_2_8, True)
        self.assertIs(g._same_name_2_8, True)
        self.assertIs(g._c_hidden_3_4, True)
        self.assertIs(g._c_verify_4_0, True)
        self.assertIs(g._same_root_4_0, True)
        self.assertIs(g._sib_intact, True)


    def test_native_special_carry_interaction_priority(self):
        """Native special-equipment / hud_temp / hud_interaction priority over crew.

        Tests that special equipment, bag panels, throw instructions, and interaction
        panels (when overlapping) take priority over crew. Retains original assertions
        for backward compatibility.
        """
        for case in ('special', 'bag_panel', 'throw_instruction', 'interaction'):
            with self.subTest(case=case):
                lua = mounted()
                lua.execute(f'''
                    local r=C._root; local card=C._cards[1]; local nm=card._name_text
                    local rx,ry=r:x(),r:y(); local mgr=managers.hud
                    local nat=panel_double:panel({{name="npri"}})
                    nat:set_shape(17,13,200,80); nat:set_visible(true)
                    local obs; local c="{case}"
                    if c=="special" then
                        obs=nat:panel({{name="sp"}}); obs:set_shape(rx-17,ry-13,120,60)
                        obs:set_visible(true)
                        mgr._teammate_panels={{[1]={{_panel=nat,_special_equipment={{obs}}}}}}
                    elseif c=="bag_panel" or c=="throw_instruction" then
                        obs=nat:panel({{name=c}}); obs:set_shape(rx-17,ry-13,120,60)
                        obs:set_visible(true); mgr._hud_temp={{_temp_panel=nat}}
                    else
                        obs=nat:text({{name="interact_text",text="X",font="f"}})
                        obs:set_shape(rx-17,ry-13,120,60); obs:set_visible(true)
                        mgr._hud_interaction={{_hud_panel=nat,
                            _child_name_text="interact_text",
                            _child_ivalid_name_text="interact_invalid_text"}}
                    end
                    local nx,ny,nw,nh=nat:x(),nat:y(),nat:w(),nat:h()
                    local nv=nat:visible(); local na=nat:alpha()
                    RT:update(mgr,1.6,.05)
                    _h16=not C._root:visible()
                    _nk=nat:x()==nx and nat:y()==ny and nat:w()==nw and nat:h()==nh
                        and nat:visible()==nv and nat:alpha()==na
                    nat:set_visible(false); RT:update(mgr,2.2,.05)
                    _v22=C._root:visible()
                    _s22=C._root==r and C._cards[1]==card and C._cards[1]._name_text==nm
                    nat:set_visible(true); obs:set_alpha(0); RT:update(mgr,2.8,.05)
                    _v28=C._root:visible()
                    obs:set_alpha(1); RT:update(mgr,3.4,.05)
                    _h34=not C._root:visible()
                    obs:set_visible(false); RT:update(mgr,4,.05)
                    _v40=C._root:visible(); _s40=C._root==r
                ''')
                g = lua.globals()
                for k in ('_h16', '_nk', '_v22', '_s22', '_v28', '_h34', '_v40', '_s40'):
                    self.assertTrue(bool(g[k]), f"{case}:{k}")

    def test_leaf_activation_cycles_both_overlaps_recovery(self):
        """Table-driven leaf activation cycles: separate crew and local phases per leaf.

        Each leaf is tested at crew geometry (C._root x/y) then player geometry (P._root x/y).
        Crew phase: C hidden, P/W/E/backdrop visible. Local phase: P/W/E/backdrop hidden, C visible.
        Inactive: all visible, identities preserved. Empty containers never block.
        """
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        self.assertTrue(crew_ok, "crew.lua must exist")
        self.assertTrue(weapons_ok, "weapons.lua must exist")
        self.assertTrue(equipment_ok, "equipment.lua must exist")

        lua.execute(r'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            kyohud.settings.enable_crew = true
            kyohud.settings.enable_weapons = true
            kyohud.settings.enable_equipment = true
            kyohud.settings.hud_scale = 1.0
            _G.panel_double:set_shape(0, 0, 1920, 1080)

            local mgr = managers.hud
            local ACT = kyohud.hud.actors
            ACT:refresh_crew(mgr, 0)
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.runtime:update(mgr, 1.0, 0.05)

            local P = kyohud.hud.player
            local C = kyohud.hud.crew
            local WEAP = kyohud.hud.weapons
            local E = kyohud.hud.equipment

            local native_entry = _G.panel_double:panel({name="native_entry_cycles"})
            native_entry:set_shape(44, 918, 432, 120)
            native_entry:set_visible(true)

            local native_player = native_entry:panel({name="player"})
            native_player:set_shape(0, 0, 432, 120)
            native_player:set_visible(true)

            local native_radial = native_player:panel({name="radial_health_panel"})
            native_radial:set_shape(0, 0, 432, 120)
            native_radial:set_visible(true)

            managers.hud._teammate_panels = {[1] = {_panel = native_entry, _special_equipment = {}}}

            local leaves = {}

            leaves.condition_timer = native_entry:text({name="condition_timer", text="T", font="f"})
            leaves.condition_timer:set_shape(100, 40, 200, 30)
            leaves.condition_timer:set_visible(false)

            leaves.carry_panel = native_player:panel({name="carry_panel"})
            leaves.carry_panel:set_shape(100, 40, 200, 30)
            leaves.carry_panel:set_visible(false)

            leaves.interact_panel = native_player:text({name="interact_panel", text="X", font="f"})
            leaves.interact_panel:set_shape(100, 40, 200, 30)
            leaves.interact_panel:set_visible(false)

            leaves.radial_custom = native_radial:bitmap({name="radial_custom"})
            leaves.radial_custom:set_shape(100, 40, 200, 30)
            leaves.radial_custom:set_visible(false)

            leaves.radial_ability = native_radial:panel({name="radial_ability"})
            leaves.radial_ability:set_shape(100, 40, 200, 30)
            leaves.radial_ability:set_visible(false)

            leaves.radial_rip = native_radial:bitmap({name="radial_rip"})
            leaves.radial_rip:set_shape(100, 40, 200, 30)
            leaves.radial_rip:set_visible(false)

            leaves.radial_rip_bg = native_radial:bitmap({name="radial_rip_bg", color=Color(0,0,0)})
            leaves.radial_rip_bg:set_shape(100, 40, 200, 30)
            leaves.radial_rip_bg:set_visible(false)

            leaves.radial_absorb_shield_active = native_radial:bitmap({name="radial_absorb_shield_active"})
            leaves.radial_absorb_shield_active:set_shape(100, 40, 200, 30)
            leaves.radial_absorb_shield_active:set_visible(false)

            leaves.radial_absorb_health_active = native_radial:bitmap({name="radial_absorb_health_active"})
            leaves.radial_absorb_health_active:set_shape(100, 40, 200, 30)
            leaves.radial_absorb_health_active:set_visible(false)

            leaves.radial_info_meter = native_radial:bitmap({name="radial_info_meter"})
            leaves.radial_info_meter:set_shape(100, 40, 200, 30)
            leaves.radial_info_meter:set_visible(false)

            leaves.radial_info_meter_bg = native_radial:bitmap({name="radial_info_meter_bg", color=Color(0,0,0)})
            leaves.radial_info_meter_bg:set_shape(100, 40, 200, 30)
            leaves.radial_info_meter_bg:set_visible(false)

            local radial_delayed_damage = native_radial:panel({name="radial_delayed_damage"})
            radial_delayed_damage:set_shape(100, 40, 200, 30)
            radial_delayed_damage:set_visible(true)

            leaves.radial_delayed_damage_armor = radial_delayed_damage:bitmap({name="radial_delayed_damage_armor"})
            leaves.radial_delayed_damage_armor:set_shape(100, 40, 200, 30)
            leaves.radial_delayed_damage_armor:set_visible(false)

            leaves.radial_delayed_damage_health = radial_delayed_damage:bitmap({name="radial_delayed_damage_health"})
            leaves.radial_delayed_damage_health:set_shape(100, 40, 200, 30)
            leaves.radial_delayed_damage_health:set_visible(false)

            local copr_overlay_panel = native_radial:panel({name="copr_overlay_panel"})
            copr_overlay_panel:set_shape(100, 40, 200, 30)
            copr_overlay_panel:set_visible(true)

            local crew_x, crew_y = C._root:x(), C._root:y()
            local crew_w, crew_h = C._root:w(), C._root:h()
            local player_x, player_y = P._root:x(), P._root:y()
            local player_w, player_h = P._root:w(), P._root:h()

            local _bg = kyohud.hud.runtime._local_bg_panel

            _p_root_before = P._root
            _c_root_before = C._root
            _weap_root_before = WEAP._root
            _e_root_before = E._root
            _p_gauge_before = P._gauge
            _p_ht_before = P._gauge and P._gauge.health_text or nil

            kyohud.hud.runtime:update(mgr, 1.6, 0.05)
            _baseline_crew_visible = C._root:visible()
            _baseline_player_visible = P._root:visible()
            _baseline_weap_visible = WEAP._root:visible()
            _baseline_equip_visible = E._root:visible()
            _empty_delayed_visible = radial_delayed_damage:visible()
            _empty_copr_visible = copr_overlay_panel:visible()
            _bg_baseline_visible = _bg and _bg:visible() or false

            _leaf_results = {}
            local t = 2.2

            for leaf_name, leaf_prim in pairs(leaves) do
                native_entry:set_shape(crew_x, crew_y, crew_w, crew_h)
                leaf_prim:set_visible(true)
                kyohud.hud.runtime:update(mgr, t, 0.05)
                _leaf_results[leaf_name .. "_crew_hidden"] = not C._root:visible()
                _leaf_results[leaf_name .. "_crew_p_vis"] = P._root:visible()
                _leaf_results[leaf_name .. "_crew_w_vis"] = WEAP._root:visible()
                _leaf_results[leaf_name .. "_crew_e_vis"] = E._root:visible()
                _leaf_results[leaf_name .. "_crew_bg_vis"] = _bg and _bg:visible() or false
                t = t + 0.6

                leaf_prim:set_visible(false)
                kyohud.hud.runtime:update(mgr, t, 0.05)
                _leaf_results[leaf_name .. "_recov1_crew"] = C._root:visible()
                _leaf_results[leaf_name .. "_recov1_player"] = P._root:visible()
                _leaf_results[leaf_name .. "_recov1_weap"] = WEAP._root:visible()
                _leaf_results[leaf_name .. "_recov1_equip"] = E._root:visible()
                t = t + 0.6

                native_entry:set_shape(player_x, player_y, player_w, player_h)
                leaf_prim:set_visible(true)
                kyohud.hud.runtime:update(mgr, t, 0.05)
                _leaf_results[leaf_name .. "_local_c_vis"] = C._root:visible()
                _leaf_results[leaf_name .. "_local_p_hidden"] = not P._root:visible()
                _leaf_results[leaf_name .. "_local_w_hidden"] = not WEAP._root:visible()
                _leaf_results[leaf_name .. "_local_e_hidden"] = not E._root:visible()
                _leaf_results[leaf_name .. "_local_bg_hidden"] = not (_bg and _bg:visible())
                t = t + 0.6

                leaf_prim:set_visible(false)
                native_entry:set_shape(crew_x, crew_y, crew_w, crew_h)
                kyohud.hud.runtime:update(mgr, t, 0.05)
                _leaf_results[leaf_name .. "_recov2_crew"] = C._root:visible()
                _leaf_results[leaf_name .. "_recov2_player"] = P._root:visible()
                t = t + 0.6
            end

            native_entry:set_shape(crew_x, crew_y, crew_w, crew_h)
            local copr_child0 = copr_overlay_panel:polygon({
                name="0", layer=0, color=Color(0.6, 0, 0, 0),
                triangles={Vector3(0,0,0), Vector3(10,0,0), Vector3(5,10,0)}
            })
            kyohud.hud.runtime:update(mgr, t, 0.05)
            _nonempty_copr_hidden_crew = not C._root:visible()
            _nonempty_copr_p_vis = P._root:visible()
            t = t + 0.6

            native_entry:set_shape(player_x, player_y, player_w, player_h)
            kyohud.hud.runtime:update(mgr, t, 0.05)
            _nonempty_copr_hidden_local = not P._root:visible()
            _nonempty_copr_c_vis = C._root:visible()
            t = t + 0.6

            copr_overlay_panel:clear()
            native_entry:set_shape(crew_x, crew_y, crew_w, crew_h)
            kyohud.hud.runtime:update(mgr, t, 0.05)
            _empty_copr_recovered = C._root:visible()
            t = t + 0.6

            leaves.condition_timer:set_visible(true)
            native_entry:set_visible(false)
            kyohud.hud.runtime:update(mgr, t, 0.05)
            _ancestor_hidden_recovered = C._root:visible()
            native_entry:set_visible(true)
            t = t + 0.6

            native_entry:set_alpha(0)
            kyohud.hud.runtime:update(mgr, t, 0.05)
            _ancestor_alpha0_recovered = C._root:visible()
            native_entry:set_alpha(1)
            leaves.condition_timer:set_visible(false)
            t = t + 0.6

            kyohud.hud.runtime:update(mgr, t, 0.05)
            _final_crew_visible = C._root:visible()
            _final_player_visible = P._root:visible()
            _final_weap_visible = WEAP._root:visible()
            _final_equip_visible = E._root:visible()

            _same_c = (C._root == _c_root_before)
            _same_p_root = (P._root == _p_root_before)
            _same_weap_root = (WEAP._root == _weap_root_before)
            _same_e_root = (E._root == _e_root_before)
            _same_p_gauge = (P._gauge == _p_gauge_before)
            _same_p_ht = ((P._gauge and P._gauge.health_text or nil) == _p_ht_before)
        ''')

        g = lua.globals()

        self.assertTrue(bool(g._baseline_crew_visible),
            "crew must be visible under ordinary native containers with empty defaults")
        self.assertTrue(bool(g._baseline_player_visible),
            "player must be visible under ordinary native containers with empty defaults")
        self.assertTrue(bool(g._baseline_weap_visible),
            "weapons must be visible under ordinary native containers with empty defaults")
        self.assertTrue(bool(g._baseline_equip_visible),
            "equipment must be visible under ordinary native containers with empty defaults")

        self.assertTrue(bool(g._empty_delayed_visible),
            "empty radial_delayed_damage must be visible by default")
        self.assertTrue(bool(g._empty_copr_visible),
            "empty copr_overlay_panel must be visible by default")

        indispensable_leaves = [
            "condition_timer", "carry_panel", "interact_panel", "radial_custom",
            "radial_ability", "radial_rip", "radial_rip_bg",
            "radial_absorb_shield_active", "radial_absorb_health_active",
            "radial_info_meter", "radial_info_meter_bg",
            "radial_delayed_damage_armor", "radial_delayed_damage_health"
        ]

        for leaf_name in indispensable_leaves:
            self.assertTrue(bool(g._leaf_results[leaf_name + "_crew_hidden"]),
                f"{leaf_name} at crew must hide crew")
            self.assertTrue(bool(g._leaf_results[leaf_name + "_crew_p_vis"]),
                f"{leaf_name} at crew: player must remain visible")
            self.assertTrue(bool(g._leaf_results[leaf_name + "_crew_w_vis"]),
                f"{leaf_name} at crew: weapons must remain visible")
            self.assertTrue(bool(g._leaf_results[leaf_name + "_crew_e_vis"]),
                f"{leaf_name} at crew: equipment must remain visible")
            self.assertTrue(bool(g._leaf_results[leaf_name + "_crew_bg_vis"]),
                f"{leaf_name} at crew: backdrop must remain visible")
            self.assertTrue(bool(g._leaf_results[leaf_name + "_recov1_crew"]),
                f"{leaf_name} inactive must recover crew")
            self.assertTrue(bool(g._leaf_results[leaf_name + "_recov1_player"]),
                f"{leaf_name} inactive must recover player")
            self.assertTrue(bool(g._leaf_results[leaf_name + "_recov1_weap"]),
                f"{leaf_name} inactive must recover weapons")
            self.assertTrue(bool(g._leaf_results[leaf_name + "_recov1_equip"]),
                f"{leaf_name} inactive must recover equipment")
            self.assertTrue(bool(g._leaf_results[leaf_name + "_local_c_vis"]),
                f"{leaf_name} at player: crew must remain visible")
            self.assertTrue(bool(g._leaf_results[leaf_name + "_local_p_hidden"]),
                f"{leaf_name} at player must hide player")
            self.assertTrue(bool(g._leaf_results[leaf_name + "_local_w_hidden"]),
                f"{leaf_name} at player must hide weapons")
            self.assertTrue(bool(g._leaf_results[leaf_name + "_local_e_hidden"]),
                f"{leaf_name} at player must hide equipment")
            self.assertTrue(bool(g._leaf_results[leaf_name + "_local_bg_hidden"]),
                f"{leaf_name} at player: backdrop must be hidden")
            self.assertTrue(bool(g._leaf_results[leaf_name + "_recov2_crew"]),
                f"{leaf_name} inactive2 must recover crew")
            self.assertTrue(bool(g._leaf_results[leaf_name + "_recov2_player"]),
                f"{leaf_name} inactive2 must recover player")

        self.assertTrue(bool(g._nonempty_copr_hidden_crew),
            "nonempty copr at crew must hide crew")
        self.assertTrue(bool(g._nonempty_copr_p_vis),
            "nonempty copr at crew: player must remain visible")
        self.assertTrue(bool(g._nonempty_copr_hidden_local),
            "nonempty copr at player must hide player")
        self.assertTrue(bool(g._nonempty_copr_c_vis),
            "nonempty copr at player: crew must remain visible")
        self.assertTrue(bool(g._empty_copr_recovered),
            "empty copr_overlay_panel (after clear) must recover crew")

        self.assertTrue(bool(g._ancestor_hidden_recovered),
            "crew must recover when ancestor entry._panel hidden even with active leaf")
        self.assertTrue(bool(g._ancestor_alpha0_recovered),
            "crew must recover when ancestor entry._panel alpha=0 even with active leaf")

        self.assertTrue(bool(g._final_crew_visible),
            "crew must be visible after all cycles")
        self.assertTrue(bool(g._final_player_visible),
            "player must be visible after all cycles")
        self.assertTrue(bool(g._final_weap_visible),
            "weapons must be visible after all cycles")
        self.assertTrue(bool(g._final_equip_visible),
            "equipment must be visible after all cycles")

        self.assertTrue(bool(g._same_c), "crew root identity must be preserved")
        self.assertTrue(bool(g._same_p_root), "player root identity must be preserved")
        self.assertTrue(bool(g._same_weap_root), "weapons root identity must be preserved")
        self.assertTrue(bool(g._same_e_root), "equipment root identity must be preserved")
        self.assertTrue(bool(g._same_p_gauge), "player gauge identity must be preserved")
        self.assertTrue(bool(g._same_p_ht), "player health_text identity must be preserved")

    def test_ordinary_overlap_all_visible(self):
        """Ordinary native overlap: name/health/shield visible, optional leaves invisible.

        Two native entries at crew and player geometry with ordinary name/health/shield
        visible and all optional leaves invisible. Empty containers under both radials.
        All owned roots+backdrop must remain visible across repeated updates.
        Certify/visible positive BEFORE adding native nodes.
        """
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        self.assertTrue(crew_ok, "crew.lua must exist")
        self.assertTrue(weapons_ok, "weapons.lua must exist")
        self.assertTrue(equipment_ok, "equipment.lua must exist")

        lua.execute(r'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            kyohud.settings.enable_crew = true
            kyohud.settings.enable_weapons = true
            kyohud.settings.enable_equipment = true
            kyohud.settings.hud_scale = 1.0
            _G.panel_double:set_shape(0, 0, 1920, 1080)

            local mgr = managers.hud
            local ACT = kyohud.hud.actors
            ACT:refresh_crew(mgr, 0)
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.runtime:update(mgr, 1.0, 0.05)

            local P = kyohud.hud.player
            local C = kyohud.hud.crew
            local WEAP = kyohud.hud.weapons
            local E = kyohud.hud.equipment

            _pre_cert_p = P:verify()
            _pre_cert_c = C:_verify_render()
            _pre_cert_w = WEAP:verify()
            _pre_cert_e = E:verify()
            _pre_vis_p = P._root:visible()
            _pre_vis_c = C._root:visible()
            _pre_vis_w = WEAP._root:visible()
            _pre_vis_e = E._root:visible()

            local _bg = kyohud.hud.runtime._local_bg_panel
            _pre_bg_vis = _bg and _bg:visible() or false

            _p_root_before = P._root
            _c_root_before = C._root
            _weap_root_before = WEAP._root
            _e_root_before = E._root
            _p_gauge_before = P._gauge

            local crew_entry = _G.panel_double:panel({name="crew_native_entry"})
            crew_entry:set_shape(44, 918, 432, 120)
            crew_entry:set_visible(true)
            local crew_player = crew_entry:panel({name="player"})
            crew_player:set_shape(0, 0, 432, 120)
            crew_player:set_visible(true)
            local crew_radial = crew_player:panel({name="radial_health_panel"})
            crew_radial:set_shape(0, 0, 432, 120)
            crew_radial:set_visible(true)

            local crew_name = crew_entry:text({name="name", text="Crew", font="f"})
            crew_name:set_shape(100, 10, 200, 20)
            crew_name:set_visible(true)

            local crew_health = crew_radial:bitmap({name="radial_health"})
            crew_health:set_shape(0, 0, 432, 120)
            crew_health:set_visible(true)
            local crew_shield = crew_radial:bitmap({name="radial_shield"})
            crew_shield:set_shape(0, 0, 432, 120)
            crew_shield:set_visible(true)

            local crew_delayed = crew_radial:panel({name="radial_delayed_damage"})
            crew_delayed:set_shape(0, 0, 432, 120)
            crew_delayed:set_visible(true)
            local crew_copr = crew_radial:panel({name="copr_overlay_panel"})
            crew_copr:set_shape(0, 0, 432, 120)
            crew_copr:set_visible(true)

            local crew_delayed_armor = crew_delayed:bitmap({name="radial_delayed_damage_armor"})
            crew_delayed_armor:set_shape(100, 40, 200, 30)
            crew_delayed_armor:set_visible(false)
            local crew_delayed_health = crew_delayed:bitmap({name="radial_delayed_damage_health"})
            crew_delayed_health:set_shape(100, 40, 200, 30)
            crew_delayed_health:set_visible(false)

            local crew_timer = crew_entry:text({name="condition_timer", text="T", font="f"})
            crew_timer:set_visible(false)

            local player_entry = _G.panel_double:panel({name="player_native_entry"})
            player_entry:set_shape(1400, 900, 480, 160)
            player_entry:set_visible(true)
            local player_player = player_entry:panel({name="player"})
            player_player:set_shape(0, 0, 480, 160)
            player_player:set_visible(true)
            local player_radial = player_player:panel({name="radial_health_panel"})
            player_radial:set_shape(0, 0, 480, 160)
            player_radial:set_visible(true)

            local player_name = player_entry:text({name="name", text="Player", font="f"})
            player_name:set_shape(100, 10, 200, 20)
            player_name:set_visible(true)

            local player_health = player_radial:bitmap({name="radial_health"})
            player_health:set_shape(0, 0, 480, 160)
            player_health:set_visible(true)
            local player_shield = player_radial:bitmap({name="radial_shield"})
            player_shield:set_shape(0, 0, 480, 160)
            player_shield:set_visible(true)

            local player_delayed = player_radial:panel({name="radial_delayed_damage"})
            player_delayed:set_shape(0, 0, 480, 160)
            player_delayed:set_visible(true)
            local player_copr = player_radial:panel({name="copr_overlay_panel"})
            player_copr:set_shape(0, 0, 480, 160)
            player_copr:set_visible(true)

            local player_delayed_armor = player_delayed:bitmap({name="radial_delayed_damage_armor"})
            player_delayed_armor:set_shape(100, 40, 200, 30)
            player_delayed_armor:set_visible(false)
            local player_delayed_health = player_delayed:bitmap({name="radial_delayed_damage_health"})
            player_delayed_health:set_shape(100, 40, 200, 30)
            player_delayed_health:set_visible(false)

            local player_timer = player_entry:text({name="condition_timer", text="T", font="f"})
            player_timer:set_visible(false)

            managers.hud._teammate_panels = {
                [1] = {_panel = crew_entry, _special_equipment = {}},
                [4] = {_panel = player_entry, _special_equipment = {}}
            }

            kyohud.hud.runtime:update(mgr, 1.6, 0.05)
            _t1_crew = C._root:visible()
            _t1_player = P._root:visible()
            _t1_weap = WEAP._root:visible()
            _t1_equip = E._root:visible()
            _t1_bg = _bg and _bg:visible() or false

            kyohud.hud.runtime:update(mgr, 2.2, 0.05)
            _t2_crew = C._root:visible()
            _t2_player = P._root:visible()
            _t2_weap = WEAP._root:visible()
            _t2_equip = E._root:visible()
            _t2_bg = _bg and _bg:visible() or false

            kyohud.hud.runtime:update(mgr, 2.8, 0.05)
            _t3_crew = C._root:visible()
            _t3_player = P._root:visible()
            _t3_weap = WEAP._root:visible()
            _t3_equip = E._root:visible()
            _t3_bg = _bg and _bg:visible() or false

            _crew_name_vis = crew_name:visible()
            _crew_health_vis = crew_health:visible()
            _crew_shield_vis = crew_shield:visible()
            _player_name_vis = player_name:visible()
            _player_health_vis = player_health:visible()
            _player_shield_vis = player_shield:visible()

            _same_p = (P._root == _p_root_before)
            _same_c = (C._root == _c_root_before)
            _same_w = (WEAP._root == _weap_root_before)
            _same_e = (E._root == _e_root_before)
            _same_gauge = (P._gauge == _p_gauge_before)
        ''')

        g = lua.globals()

        self.assertTrue(bool(g._pre_cert_p), "player:verify() positive before native nodes")
        self.assertTrue(bool(g._pre_cert_c), "crew:_verify_render() positive before native nodes")
        self.assertTrue(bool(g._pre_cert_w), "weapons:verify() positive before native nodes")
        self.assertTrue(bool(g._pre_cert_e), "equipment:verify() positive before native nodes")
        self.assertTrue(bool(g._pre_vis_p), "player visible before native nodes")
        self.assertTrue(bool(g._pre_vis_c), "crew visible before native nodes")
        self.assertTrue(bool(g._pre_vis_w), "weapons visible before native nodes")
        self.assertTrue(bool(g._pre_vis_e), "equipment visible before native nodes")

        for t_idx in ('1', '2', '3'):
            self.assertTrue(bool(g[f'_t{t_idx}_crew']),
                f"crew must remain visible at t{t_idx} with ordinary overlap")
            self.assertTrue(bool(g[f'_t{t_idx}_player']),
                f"player must remain visible at t{t_idx} with ordinary overlap")
            self.assertTrue(bool(g[f'_t{t_idx}_weap']),
                f"weapons must remain visible at t{t_idx} with ordinary overlap")
            self.assertTrue(bool(g[f'_t{t_idx}_equip']),
                f"equipment must remain visible at t{t_idx} with ordinary overlap")
            self.assertTrue(bool(g[f'_t{t_idx}_bg']),
                f"backdrop must remain visible at t{t_idx} with ordinary overlap")

        self.assertTrue(bool(g._crew_name_vis))
        self.assertTrue(bool(g._crew_health_vis))
        self.assertTrue(bool(g._crew_shield_vis))
        self.assertTrue(bool(g._player_name_vis))
        self.assertTrue(bool(g._player_health_vis))
        self.assertTrue(bool(g._player_shield_vis))

        self.assertTrue(bool(g._same_p), "player root identity preserved")
        self.assertTrue(bool(g._same_c), "crew root identity preserved")
        self.assertTrue(bool(g._same_w), "weapons root identity preserved")
        self.assertTrue(bool(g._same_e), "equipment root identity preserved")
        self.assertTrue(bool(g._same_gauge), "player gauge identity preserved")


    def test_no_native_write_during_priority(self):
        """No native setters invoked by _apply_native_priority during production updates.

        Spy native set_visible/set_alpha/set_shape/clear/remove/set_parent on ALL
        native test nodes (entry, player, radial, leaf) after fixture setup.
        Export before-values as Lua globals. Reset counters AFTER fixture mutation
        and BEFORE each production update. Assert zero counters after each update.
        Preserve native leaf text/alpha/visibility and sentinel snapshot.
        """
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        self.assertTrue(crew_ok, "crew.lua must exist")
        self.assertTrue(weapons_ok, "weapons.lua must exist")
        self.assertTrue(equipment_ok, "equipment.lua must exist")

        lua.execute(r'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            kyohud.settings.enable_crew = true
            kyohud.settings.enable_weapons = true
            kyohud.settings.enable_equipment = true
            kyohud.settings.hud_scale = 1.0
            _G.panel_double:set_shape(0, 0, 1920, 1080)

            local mgr = managers.hud
            local ACT = kyohud.hud.actors
            ACT:refresh_crew(mgr, 0)
            kyohud.hud.runtime:mount(mgr)
            kyohud.hud.runtime:refresh_settings(mgr)
            kyohud.hud.runtime:update(mgr, 1.0, 0.05)

            local C = kyohud.hud.crew
            local P = kyohud.hud.player

            local native_entry = _G.panel_double:panel({name="spy_entry"})
            native_entry:set_shape(44, 918, 432, 120)
            native_entry:set_visible(true)
            local native_player = native_entry:panel({name="player"})
            native_player:set_shape(0, 0, 432, 120)
            native_player:set_visible(true)
            local native_radial = native_player:panel({name="radial_health_panel"})
            native_radial:set_shape(0, 0, 432, 120)
            native_radial:set_visible(true)

            local leaf = native_entry:text({name="condition_timer", text="T", font="f"})
            leaf:set_shape(100, 40, 200, 30)
            leaf:set_visible(false)

            _leaf_text_before = leaf:text()
            _leaf_vis_before = leaf:visible()
            _leaf_alpha_before = leaf:alpha()

            managers.hud._teammate_panels = {[1] = {_panel = native_entry, _special_equipment = {}}}

            local sentinel = _G.panel_double:panel({name="sentinel"})
            sentinel:set_shape(500, 500, 100, 100)
            sentinel:set_visible(true)
            _sentinel_x_before = sentinel:x()
            _sentinel_vis_before = sentinel:visible()

            local total = 0
            local function install_spy(node)
                local os = node.set_visible
                local oa = node.set_alpha
                local oh = node.set_shape
                node.set_visible = function(s, ...) total = total + 1; return os(s, ...) end
                node.set_alpha = function(s, ...) total = total + 1; return oa(s, ...) end
                node.set_shape = function(s, ...) total = total + 1; return oh(s, ...) end
                if type(node.clear) == "function" then
                    local oc = node.clear
                    node.clear = function(s, ...) total = total + 1; return oc(s, ...) end
                end
                if type(node.remove) == "function" then
                    local orr = node.remove
                    node.remove = function(s, ...) total = total + 1; return orr(s, ...) end
                end
                if type(node.set_parent) == "function" then
                    local osp = node.set_parent
                    node.set_parent = function(s, ...) total = total + 1; return osp(s, ...) end
                end
            end
            install_spy(native_entry)
            install_spy(native_player)
            install_spy(native_radial)
            install_spy(leaf)

            total = 0
            kyohud.hud.runtime:update(mgr, 1.6, 0.05)
            _spy_1 = total
            _leaf_text_1 = leaf:text()
            _leaf_vis_1 = leaf:visible()
            _leaf_alpha_1 = leaf:alpha()
            _sentinel_x_1 = sentinel:x()
            _sentinel_vis_1 = sentinel:visible()

            leaf:set_visible(true)
            total = 0
            kyohud.hud.runtime:update(mgr, 2.2, 0.05)
            _spy_2 = total
            _c_hidden_2 = not C._root:visible()
            _leaf_text_2 = leaf:text()
            _leaf_vis_2 = leaf:visible()
            _leaf_alpha_2 = leaf:alpha()

            local px, py = P._root:x(), P._root:y()
            local pw, ph = P._root:w(), P._root:h()
            native_entry:set_shape(px, py, pw, ph)
            total = 0
            kyohud.hud.runtime:update(mgr, 2.8, 0.05)
            _spy_3 = total
            _p_hidden_3 = not P._root:visible()

            leaf:set_visible(false)
            native_entry:set_shape(44, 918, 432, 120)
            total = 0
            kyohud.hud.runtime:update(mgr, 3.4, 0.05)
            _spy_4 = total
            _c_vis_4 = C._root:visible()
            _p_vis_4 = P._root:visible()

            _leaf_text_final = leaf:text()
            _leaf_vis_final = leaf:visible()
            _leaf_alpha_final = leaf:alpha()
            _sentinel_x_final = sentinel:x()
            _sentinel_vis_final = sentinel:visible()
            _sentinel_alive = alive(sentinel)
        ''')

        g = lua.globals()

        self.assertEqual(int(g._spy_1), 0, "no native setters after update 1 (inactive)")
        self.assertEqual(int(g._spy_2), 0, "no native setters after update 2 (leaf active at crew)")
        self.assertEqual(int(g._spy_3), 0, "no native setters after update 3 (entry at player)")
        self.assertEqual(int(g._spy_4), 0, "no native setters after update 4 (recovery)")

        self.assertEqual(str(g._leaf_text_1), str(g._leaf_text_before))
        self.assertIs(bool(g._leaf_vis_1), bool(g._leaf_vis_before))
        self.assertAlmostEqual(float(g._leaf_alpha_1), float(g._leaf_alpha_before), places=2)
        self.assertEqual(str(g._leaf_text_2), str(g._leaf_text_before))
        self.assertIs(bool(g._leaf_vis_2), True)
        self.assertAlmostEqual(float(g._leaf_alpha_2), float(g._leaf_alpha_before), places=2)

        self.assertEqual(str(g._leaf_text_final), str(g._leaf_text_before))
        self.assertIs(bool(g._leaf_vis_final), bool(g._leaf_vis_before))
        self.assertAlmostEqual(float(g._leaf_alpha_final), float(g._leaf_alpha_before), places=2)

        self.assertAlmostEqual(float(g._sentinel_x_1), float(g._sentinel_x_before), places=1)
        self.assertIs(bool(g._sentinel_vis_1), bool(g._sentinel_vis_before))
        self.assertAlmostEqual(float(g._sentinel_x_final), float(g._sentinel_x_before), places=1)
        self.assertIs(bool(g._sentinel_vis_final), bool(g._sentinel_vis_before))
        self.assertTrue(bool(g._sentinel_alive))

        self.assertIs(bool(g._c_hidden_2), True, "crew hidden when leaf active at crew")
        self.assertIs(bool(g._p_hidden_3), True, "player hidden when entry at player")
        self.assertTrue(bool(g._c_vis_4), "crew visible after recovery")
        self.assertTrue(bool(g._p_vis_4), "player visible after recovery")

    def test_condition_timer_child_lookup_fail_closes_restores(self):
        """condition_timer entry:child failure: fail-closed, same primitives on recovery."""
        lua = mounted()
        lua.execute('''
            local r = C._root; local card = C._cards[1]; local nm = card._name_text
            local rx, ry, rw, rh = r:x(), r:y(), r:w(), r:h()

            local native_entry = panel_double:panel({name="ct_fail_entry"})
            native_entry:set_shape(rx, ry, rw, rh)
            native_entry:set_visible(true)

            local ct = native_entry:text({name="condition_timer", text="T", font="f"})
            ct:set_shape(0, 0, rw, rh)
            ct:set_visible(true)

            managers.hud._teammate_panels = {[1] = {_panel = native_entry, _special_equipment = {}}}

            local orig_child = native_entry.child
            native_entry.child = function() error('child unavailable') end
            RT:update(managers.hud, 1.6, 0.05)
            _fail_hidden = not C._root:visible()

            native_entry.child = orig_child
            RT:update(managers.hud, 2.2, 0.05)
            _restored_still_blocked = not C._root:visible()
            ct:set_visible(false)
            RT:update(managers.hud, 2.8, 0.05)
            _recover_vis = C._root:visible()
            _same_root = C._root == r
            _same_card = C._cards[1] == card
            _same_name = C._cards[1]._name_text == nm
        ''')
        g = lua.globals()
        self.assertIs(bool(g._fail_hidden), True)
        self.assertIs(bool(g._restored_still_blocked), True)
        self.assertIs(bool(g._recover_vis), True)
        self.assertIs(bool(g._same_root), True)
        self.assertIs(bool(g._same_card), True)
        self.assertIs(bool(g._same_name), True)

    def test_special_registry_blocks_without_entry_panel(self):
        """Special equipment panel blocks crew even when entry._panel is nil."""
        lua = mounted()
        lua.execute('''
            local r = C._root; local rx, ry, rw, rh = r:x(), r:y(), r:w(), r:h()

            local obs = panel_double:panel({name="special_obs"})
            obs:set_shape(rx, ry, rw, rh)
            obs:set_visible(true)

            managers.hud._teammate_panels = {[1] = {_panel = nil, _special_equipment = {obs}}}

            RT:update(managers.hud, 1.6, 0.05)
            _blocked = not C._root:visible()

            obs:set_visible(false)
            RT:update(managers.hud, 2.2, 0.05)
            _recovered = C._root:visible()
            _same_root = C._root == r
        ''')
        g = lua.globals()
        self.assertIs(bool(g._blocked), True)
        self.assertIs(bool(g._recovered), True)
        self.assertIs(bool(g._same_root), True)


if __name__ == "__main__":
    unittest.main()
