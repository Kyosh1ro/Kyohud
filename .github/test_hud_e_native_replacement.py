"""H5 native replacement -- ordinary leaves alpha=0 via NV, indispensable preserved.

H5 runtime coordinates AFTER consumers and _apply_native_priority. Eligibility
is actual visible verified owned render. For local slot use HUDManager.PLAYER_PANEL
verified native constant (fallback native actual slot4 only if source verified).

Ordinary player targets: entry._panel child name,name_bg,callsign,callsign_bg;
entry._panel child player child radial_health_panel leaves radial_bg,radial_health,
radial_shield ONLY. Revive counter duplicates exact player/revive_panel leaves
revive_bg,revive_amount,revive_arrow only if actual custom downs is known and rendered.

DO NOT mask main radial ancestors or damage_indicator / overlays (carry/interact/
condition/custom/ability/rip/absorb/info/delayed/copr/special leaf).

Weapons targets under player/weapons_panel/primary_weapon_panel and secondary_weapon_panel:
bg,ammo_clip,ammo_total and weapon_selection BITMAP (nested inside weapon_selection panel)
only. DO NOT mask weapon_selection panel container itself.

Equipment under player/deployable_equipment_panel leaves bg,equipment,amount;
player/cable_ties_panel bg,cable_ties,amount; player/grenades_panel bg,grenades_icon,
amount ONLY; leave grenades_radial/ghost/ability-specific native leaves intact.

Gate each category independently on matching P/W/E enabled, :verify(), owned root
effective visible (runtime root disabled/freeflight -> release). Native source
supported (turret etc unsupported preserve).

Crew native targets ONLY each actual rendered card mapped from ACT:get_crew_snapshot()
crew entries position AND slot with card verify and alive visible, no blanket slots1..3
hiding. Cover actual replaced name/normal health/armor/ammo/equipment leaves only when
actor values valid and custom renders them. Bots unknown armor never invent replacement.

If data absent/unsupported leave native. Bound slots1..4.

NV contract: nv._whitelist[obj].alpha=true; nv:acquire(owner,generation,...);
nv:release(owner,generation). Cache per-owner target lists, safe source replacement,
release old generation preserve unresolved restoration entries.

Local identity: owned text label within P root, reads native name text/color read-only,
verifies actual text/shape/visible/alpha/font before hiding native name/name_bg.
"""
import unittest
from test_hud_final_integration import _crew_lua


def _base_fixture(lua, enable_player=True, enable_weapons=True, enable_equipment=True, enable_crew=True):
    """Common fixture setup for H5 tests. Seeds LEGIT known source data."""
    lua.execute(f'''
        Idstring = Idstring or function(v) return v end
        kyohud.settings.enable_hud_foundation = true
        kyohud.settings.enable_player = {str(enable_player).lower()}
        kyohud.settings.enable_weapons = {str(enable_weapons).lower()}
        kyohud.settings.enable_equipment = {str(enable_equipment).lower()}
        kyohud.settings.enable_crew = {str(enable_crew).lower()}
        kyohud.settings.hud_scale = 1.0
        panel_double:set_shape(0, 0, 1920, 1080)
        managers.player.current_state = function(self) return "standard" end
        unit1, h5_test_base1 = make_weapon("new_m1014")
        h5_test_base1:_native_set_ammo(8, 6, 32, 40)
        h5_test_base1:_native_set_fire_mode("auto")
        inventory:_native_set_slot(1, unit1)
        unit2, h5_test_base2 = make_weapon("new_m16")
        h5_test_base2:_native_set_ammo(30, 25, 120, 150)
        h5_test_base2:_native_set_fire_mode("single")
        inventory:_native_set_slot(2, unit2)
        inventory:_native_set_equipped(2)
        managers.player:_native_set_equipment('doctor_bag',{{1}})
        managers.player._equipment.selected_index=1
        managers.player:_native_set_grenades('frag',3,3)
        _native_set_projectile_tweak('frag',{{throwable=true}})
        managers.player:_native_set_specials('cable_tie',{{6}})
    ''')


def _radial_runtime(**kw):
    lua, crew_ok, wk, ek = _crew_lua()
    assert crew_ok
    _base_fixture(lua, **kw)
    lua.execute(r'''
        local mgr = managers.hud
        R = kyohud.hud.runtime
        m = mgr
        R:mount(m); R:refresh_settings(m); R:update(m, .6, .05)
        assert(kyohud.hud.player:verify(), "P must verify")
        assert(kyohud.hud.crew:_verify_render(), "C must verify")
        local slot = HUDManager.PLAYER_PANEL
        local ep = panel_double:panel({name="teammate_" .. slot})
        ep:set_shape(0, 0, 100, 100); ep:set_visible(true)
        mgr._teammate_panels = mgr._teammate_panels or {}
        local entry = mgr._teammate_panels[slot] or {_ai=false, _peer_id=1}
        entry._panel = ep; mgr._teammate_panels[slot] = entry
        n = ep:text({name="name", text="Test"})
        n:set_shape(10, 0, 80, 20); n:set_visible(true); n:set_alpha(.7)
        local player = ep:panel({name="player"})
        player:set_shape(0, 0, 100, 100); player:set_visible(true)
        rad = player:panel({name="radial_health_panel"})
        rad:set_shape(0, 0, 68, 68); rad:set_visible(true)
        h = rad:bitmap({name="radial_health"})
        h:set_shape(0, 0, 68, 68); h:set_alpha(.7)
        R:update(m, 1.6, .05)
        assert(h:alpha() == 0, "positive mask: h alpha must be 0")
        assert(n:alpha() == 0, "positive mask: n alpha must be 0")
    ''')
    return lua


class NativeReplacementOrdinaryLeavesTests(unittest.TestCase):
    """Ordinary native duplicates alpha=0, indispensable preserved."""

    def test_player_ordinary_leaves_alpha0_indispensable_preserved(self):
        """Local player slot: ordinary leaves alpha=0, overlays preserved.

        name, name_bg, callsign, callsign_bg, radial_bg, radial_health,
        radial_shield -> alpha=0 when P enabled/verified/visible.
        carry_panel, interact_panel, condition_timer, radial_custom, radial_ability,
        radial_rip, radial_rip_bg, radial_absorb_*, radial_info_meter*, radial_delayed_*,
        copr_overlay_panel -> preserved (alpha unchanged).
        """
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        self.assertTrue(crew_ok)
        _base_fixture(lua, enable_player=True, enable_weapons=False, enable_equipment=False)
        lua.execute(r'''
            local mgr = managers.hud
            local slot = HUDManager.PLAYER_PANEL
            local entry_panel = panel_double:panel({name="teammate_" .. slot})
            entry_panel:set_shape(0, 0, 432, 120)
            entry_panel:set_visible(true)

            local name = entry_panel:text({name="name", text="Test"})
            name:set_shape(10, 0, 100, 20)
            name:set_visible(true)
            name:set_alpha(1)

            local name_bg = entry_panel:bitmap({name="name_bg"})
            name_bg:set_shape(10, 0, 100, 20)
            name_bg:set_visible(true)
            name_bg:set_alpha(1)

            local callsign = entry_panel:bitmap({name="callsign"})
            callsign:set_shape(0, 0, 20, 20)
            callsign:set_visible(true)
            callsign:set_alpha(1)

            local callsign_bg = entry_panel:bitmap({name="callsign_bg"})
            callsign_bg:set_shape(0, 0, 20, 20)
            callsign_bg:set_visible(true)
            callsign_bg:set_alpha(1)

            local player = entry_panel:panel({name="player"})
            player:set_shape(0, 0, 432, 120)
            player:set_visible(true)

            local radial = player:panel({name="radial_health_panel"})
            radial:set_shape(0, 0, 68, 68)
            radial:set_visible(true)

            local radial_bg = radial:bitmap({name="radial_bg"})
            radial_bg:set_shape(0, 0, 68, 68)
            radial_bg:set_alpha(1)

            local radial_health = radial:bitmap({name="radial_health"})
            radial_health:set_shape(0, 0, 68, 68)
            radial_health:set_alpha(1)

            local radial_shield = radial:bitmap({name="radial_shield"})
            radial_shield:set_shape(0, 0, 68, 68)
            radial_shield:set_alpha(1)

            local damage_indicator = radial:bitmap({name="damage_indicator"})
            damage_indicator:set_shape(0, 0, 68, 68)
            damage_indicator:set_alpha(1)

            local radial_custom = radial:bitmap({name="radial_custom"})
            radial_custom:set_shape(0, 0, 68, 68)
            radial_custom:set_visible(false)
            radial_custom:set_alpha(0.5)

            mgr._teammate_panels = mgr._teammate_panels or {}
            mgr._teammate_panels[slot] = {
                _panel = entry_panel,
                _ai = false,
                _peer_id = 1,
            }

            local P = kyohud.hud.player
            local RT = kyohud.hud.runtime
            RT:mount(mgr)
            RT:update(mgr, 1.0, 0.05)

            _name_alpha = name:alpha()
            _name_bg_alpha = name_bg:alpha()
            _callsign_alpha = callsign:alpha()
            _callsign_bg_alpha = callsign_bg:alpha()
            _radial_bg_alpha = radial_bg:alpha()
            _radial_health_alpha = radial_health:alpha()
            _radial_shield_alpha = radial_shield:alpha()
            _damage_alpha = damage_indicator:alpha()
            _custom_alpha = radial_custom:alpha()

            local id_label = P._h5_id_label
            _has_id_label = id_label ~= nil
            if id_label then
                _id_label_text = id_label:text()
                _id_label_visible = id_label:visible()
                _id_label_alpha = id_label:alpha()
                _id_label_font = id_label:font()
            end
        ''')
        g = lua.globals()
        self.assertEqual(g._name_alpha, 0, "name must be alpha=0")
        self.assertEqual(g._name_bg_alpha, 0, "name_bg must be alpha=0")
        self.assertEqual(g._callsign_alpha, 0, "callsign must be alpha=0")
        self.assertEqual(g._callsign_bg_alpha, 0, "callsign_bg must be alpha=0")
        self.assertEqual(g._radial_bg_alpha, 0, "radial_bg must be alpha=0")
        self.assertEqual(g._radial_health_alpha, 0, "radial_health must be alpha=0")
        self.assertEqual(g._radial_shield_alpha, 0, "radial_shield must be alpha=0")
        self.assertNotEqual(g._damage_alpha, 0, "damage_indicator must NOT be alpha=0")
        self.assertNotEqual(g._custom_alpha, 0, "radial_custom must NOT be alpha=0")
        self.assertTrue(g._has_id_label, "local identity label must exist")
        self.assertEqual(g._id_label_text, "Test", "local identity text must match native name")
        self.assertTrue(g._id_label_visible, "local identity label must be visible")
        self.assertGreater(g._id_label_alpha, 0, "local identity label must have alpha > 0")
        self.assertEqual(g._id_label_font, "fonts/font_medium_mf", "local identity must use correct font")

    def test_weapons_ordinary_leaves_alpha0_firemode_preserved(self):
        """Weapons: bg/clip/total/selection BITMAP alpha=0, panel container preserved."""
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        self.assertTrue(crew_ok and weapons_ok)
        _base_fixture(lua, enable_player=False, enable_weapons=True, enable_equipment=False)
        lua.execute(r'''
            local mgr = managers.hud
            local slot = HUDManager.PLAYER_PANEL
            local entry_panel = panel_double:panel({name="teammate_" .. slot})
            entry_panel:set_shape(0, 0, 432, 120)
            entry_panel:set_visible(true)

            local player = entry_panel:panel({name="player"})
            player:set_shape(0, 0, 432, 120)
            player:set_visible(true)

            local weapons = player:panel({name="weapons_panel"})
            weapons:set_shape(70, 0, 80, 68)
            weapons:set_visible(true)

            local primary = weapons:panel({name="primary_weapon_panel"})
            primary:set_shape(0, 0, 80, 32)
            primary:set_visible(true)

            local bg = primary:bitmap({name="bg"})
            bg:set_shape(0, 0, 80, 32)
            bg:set_alpha(1)

            local clip = primary:text({name="ammo_clip", text="30"})
            clip:set_shape(0, 0, 40, 32)
            clip:set_alpha(1)

            local total = primary:text({name="ammo_total", text="90"})
            total:set_shape(40, 0, 40, 32)
            total:set_alpha(1)

            local selection_panel = primary:panel({name="weapon_selection"})
            selection_panel:set_shape(68, 0, 12, 32)
            selection_panel:set_visible(true)
            selection_panel:set_alpha(0.7)

            local sel_bitmap = selection_panel:bitmap({name="weapon_selection"})
            sel_bitmap:set_shape(0, 0, 12, 32)
            sel_bitmap:set_alpha(1)

            mgr._teammate_panels = mgr._teammate_panels or {}
            mgr._teammate_panels[slot] = {
                _panel = entry_panel,
                _ai = false,
                _peer_id = 1,
            }

            local WEAP = kyohud.hud.weapons
            local RT = kyohud.hud.runtime
            RT:mount(mgr)
            RT:update(mgr, 1.0, 0.05)

            _bg_alpha = bg:alpha()
            _clip_alpha = clip:alpha()
            _total_alpha = total:alpha()
            _sel_panel_alpha = selection_panel:alpha()
            _sel_bitmap_alpha = sel_bitmap:alpha()
        ''')
        g = lua.globals()
        self.assertEqual(g._bg_alpha, 0, "weapons bg must be alpha=0")
        self.assertEqual(g._clip_alpha, 0, "ammo_clip must be alpha=0")
        self.assertEqual(g._total_alpha, 0, "ammo_total must be alpha=0")
        self.assertNotEqual(g._sel_panel_alpha, 0, "weapon_selection PANEL must NOT be alpha=0")
        self.assertEqual(g._sel_bitmap_alpha, 0, "weapon_selection BITMAP must be alpha=0")

    def test_equipment_ordinary_leaves_alpha0_radial_ghost_preserved(self):
        """Equipment: bg/icon/amount alpha=0, grenades_radial/ghost preserved."""
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        self.assertTrue(crew_ok and equipment_ok)
        _base_fixture(lua, enable_player=False, enable_weapons=False, enable_equipment=True)
        lua.execute(r'''
            local mgr = managers.hud
            local slot = HUDManager.PLAYER_PANEL
            local entry_panel = panel_double:panel({name="teammate_" .. slot})
            entry_panel:set_shape(0, 0, 432, 120)
            entry_panel:set_visible(true)

            local player = entry_panel:panel({name="player"})
            player:set_shape(0, 0, 432, 120)
            player:set_visible(true)

            local grenades = player:panel({name="grenades_panel"})
            grenades:set_shape(150, 0, 48, 32)
            grenades:set_visible(true)

            local bg = grenades:bitmap({name="bg"})
            bg:set_shape(0, 0, 48, 32)
            bg:set_alpha(1)

            local icon = grenades:bitmap({name="grenades_icon"})
            icon:set_shape(0, 0, 32, 32)
            icon:set_alpha(1)

            local amount = grenades:text({name="amount", text="3"})
            amount:set_shape(0, 0, 48, 32)
            amount:set_alpha(1)

            local radial = grenades:bitmap({name="grenades_radial"})
            radial:set_shape(0, 0, 32, 32)
            radial:set_alpha(1)

            local ghost = grenades:bitmap({name="grenades_radial_ghost"})
            ghost:set_shape(0, 0, 32, 32)
            ghost:set_alpha(0.5)

            mgr._teammate_panels = mgr._teammate_panels or {}
            mgr._teammate_panels[slot] = {
                _panel = entry_panel,
                _ai = false,
                _peer_id = 1,
            }

            local E = kyohud.hud.equipment
            local RT = kyohud.hud.runtime
            RT:mount(mgr)
            RT:update(mgr, 1.0, 0.05)

            _bg_alpha = bg:alpha()
            _icon_alpha = icon:alpha()
            _amount_alpha = amount:alpha()
            _radial_alpha = radial:alpha()
            _ghost_alpha = ghost:alpha()
        ''')
        g = lua.globals()
        self.assertEqual(g._bg_alpha, 0, "grenades bg must be alpha=0")
        self.assertEqual(g._icon_alpha, 0, "grenades_icon must be alpha=0")
        self.assertEqual(g._amount_alpha, 0, "grenades amount must be alpha=0")
        self.assertNotEqual(g._radial_alpha, 0, "grenades_radial must NOT be alpha=0")
        self.assertNotEqual(g._ghost_alpha, 0, "grenades_radial_ghost must NOT be alpha=0")

    def test_release_on_disable_restores_alpha(self):
        """Module disable -> restore original alpha (including non-1 initial)."""
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        self.assertTrue(crew_ok)
        _base_fixture(lua, enable_player=True, enable_weapons=False, enable_equipment=False)
        lua.execute(r'''
            local mgr = managers.hud
            local slot = HUDManager.PLAYER_PANEL
            local entry_panel = panel_double:panel({name="teammate_" .. slot})
            entry_panel:set_shape(0, 0, 432, 120)
            entry_panel:set_visible(true)

            local name = entry_panel:text({name="name", text="Test"})
            name:set_shape(10, 0, 100, 20)
            name:set_visible(true)
            name:set_alpha(0.7)

            mgr._teammate_panels = mgr._teammate_panels or {}
            mgr._teammate_panels[slot] = {
                _panel = entry_panel,
                _ai = false,
                _peer_id = 1,
            }

            local RT = kyohud.hud.runtime
            RT:mount(mgr)
            RT:update(mgr, 1.0, 0.05)
            _masked_alpha = name:alpha()

            kyohud.settings.enable_player = false
            RT:refresh_settings(mgr)
            RT:update(mgr, 1.5, 0.05)
            _restored_alpha = name:alpha()
        ''')
        g = lua.globals()
        self.assertEqual(g._masked_alpha, 0, "name must be masked")
        self.assertAlmostEqual(g._restored_alpha, 0.7, places=2, msg="must restore 0.7")

    def test_crew_slot_mapped_no_blanket_hide(self):
        """Crew: only mapped slots from snapshot, no blanket slots1..3."""
        lua, crew_ok, weapons_ok, equipment_ok = _crew_lua()
        self.assertTrue(crew_ok)
        _base_fixture(lua, enable_player=False, enable_weapons=False, enable_equipment=False, enable_crew=True)
        lua.execute(r'''
            local mgr = managers.hud
            mgr._teammate_panels = mgr._teammate_panels or {}

            local slot1 = 1
            local entry1 = panel_double:panel({name="teammate_1"})
            entry1:set_shape(0, 0, 280, 120)
            entry1:set_visible(true)
            local name1 = entry1:text({name="name", text="Bot1"})
            name1:set_shape(10, 0, 100, 20)
            name1:set_visible(true)
            name1:set_alpha(1)
            local decorations = {}
            for _, key in ipairs({'name_bg', 'callsign', 'callsign_bg'}) do
                local leaf
                if key == 'callsign' then leaf = entry1:text({name=key,text='1'})
                else leaf = entry1:bitmap({name=key}) end
                leaf:set_shape(0,0,20,20); leaf:set_alpha(.7)
                decorations[#decorations+1] = leaf
            end
            local player1 = entry1:panel({name='player'})
            local radial1 = player1:panel({name='radial_health_panel'})
            local bg1 = radial1:bitmap({name='radial_bg'})
            bg1:set_shape(0,0,68,68); bg1:set_alpha(.7)
            mgr._teammate_panels[slot1] = {_panel=entry1, _ai=true, _peer_id=nil}

            local slot4 = HUDManager.PLAYER_PANEL
            local entry4 = panel_double:panel({name="teammate_4"})
            entry4:set_shape(0, 0, 432, 120)
            entry4:set_visible(true)
            local name4 = entry4:text({name="name", text="Player"})
            name4:set_shape(10, 0, 100, 20)
            name4:set_visible(true)
            name4:set_alpha(1)
            mgr._teammate_panels[slot4] = {_panel=entry4, _ai=false, _peer_id=1}

            local ACT = kyohud.hud.actors
            ACT:refresh_crew(mgr, 0)


            local RT = kyohud.hud.runtime
            RT:mount(mgr)
            RT:update(mgr, 1.0, 0.05)

            _slot1_alpha = name1:alpha()
            _slot4_alpha = name4:alpha()
            _crew_verified = kyohud.hud.crew:_verify_render()
            _decorations_masked = true
            for _, leaf in ipairs(decorations) do
                _decorations_masked = _decorations_masked and leaf:alpha() == 0
            end
            _crew_bg_alpha = bg1:alpha()
            _crew_health_known = false
            for _, actor in ipairs(ACT:get_crew_snapshot()) do
                if actor.slot == slot1 then
                    _crew_health_known = actor.health ~= nil and actor.health.valid == true
                end
            end
        ''')
        g = lua.globals()
        self.assertEqual(g._slot1_alpha, 0, "mapped crew slot must be masked")
        self.assertEqual(g._slot4_alpha, 1, "native local-player name preserved when own local module is off")
        self.assertTrue(g._crew_verified)
        self.assertTrue(g._decorations_masked)
        self.assertFalse(g._crew_health_known, 'unitless bot fixture has no qualified health')
        self.assertAlmostEqual(g._crew_bg_alpha, .7, msg='unknown bot health retains its native frame')


class NativeOwnershipParametrizedTests(unittest.TestCase):
    def test_disable_restores_and_whitelist_cleanup(self):
        lua = _radial_runtime()
        lua.execute(r'''
            kyohud.settings.enable_player = false
            R:refresh_settings(m)
            R:update(m, 2.2, .05)
            _ha = h:alpha(); _na = n:alpha(); _ra = rad:alpha()
            _nv = kyohud.hud.native_visibility
            _wlok = true
            for _,e in ipairs(_nv._entries) do
                if e.object == h or e.object == n then _wlok = false end
            end
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._ha), .7, places=2)
        self.assertAlmostEqual(float(g._na), .7, places=2)
        self.assertAlmostEqual(float(g._ra), 1, places=2)
        self.assertTrue(bool(g._wlok))

    def test_replace_panel_restores_old_masks_new(self):
        lua = _radial_runtime()
        lua.execute(r'''
            _gen_b = R._h5_generation
            local old_h = h
            local old_n = n
            local slot = HUDManager.PLAYER_PANEL
            local new_ep = panel_double:panel({name="teammate_new_" .. slot})
            new_ep:set_shape(0, 0, 100, 100); new_ep:set_visible(true)
            local new_n = new_ep:text({name="name", text="Test2"})
            new_n:set_shape(10, 0, 80, 20); new_n:set_visible(true); new_n:set_alpha(.4)
            local new_player = new_ep:panel({name="player"})
            new_player:set_shape(0, 0, 100, 100); new_player:set_visible(true)
            local new_rad = new_player:panel({name="radial_health_panel"})
            new_rad:set_shape(0, 0, 68, 68); new_rad:set_visible(true)
            local new_h = new_rad:bitmap({name="radial_health"})
            new_h:set_shape(0, 0, 68, 68); new_h:set_alpha(.4)
            m._teammate_panels[slot]._panel = new_ep
            R:update(m, 2.2, .05)
            _old_a = old_h:alpha(); _old_na = old_n:alpha()
            _new_a = new_h:alpha(); _new_na = new_n:alpha()
            R:update(m, 2.8, .05)
            _new_a2 = new_h:alpha(); _new_na2 = new_n:alpha()
            _gen_a = R._h5_generation
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._old_a), .7, places=2)
        self.assertAlmostEqual(float(g._old_na), .7, places=2)
        self.assertAlmostEqual(float(g._new_a), 0, places=2)
        self.assertAlmostEqual(float(g._new_na), 0, places=2)
        self.assertAlmostEqual(float(g._new_a2), 0, places=2)
        self.assertAlmostEqual(float(g._new_na2), 0, places=2)
        self.assertGreater(int(g._gen_a), int(g._gen_b))

    def test_remove_recreate_releases_dead_masks_new(self):
        lua = _radial_runtime()
        lua.execute(r'''
            local old_h = h
            rad:remove(old_h)
            local new_h = rad:bitmap({name="radial_health"})
            new_h:set_shape(0, 0, 68, 68)
            new_h:set_alpha(.7)
            h = new_h
            R:update(m, 2.2, .05)
            _new_a = new_h:alpha()
            _nv = kyohud.hud.native_visibility
            _dead_gone = true
            for _,e in ipairs(_nv._entries) do
                if e.object == old_h then _dead_gone = false end
            end
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._new_a), 0, places=2)
        self.assertTrue(bool(g._dead_gone))

    def test_native_reassert_recovers(self):
        lua = _radial_runtime()
        lua.execute(r'''
            h:set_alpha(.4)
            R:update(m, 2.2, .05)
            _a1 = h:alpha()
            R:update(m, 2.8, .05)
            _a2 = h:alpha()
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._a1), .4, places=2)
        self.assertAlmostEqual(float(g._a2), 0, places=2)

    def test_unmount_restores(self):
        lua = _radial_runtime()
        lua.execute(r'''
            R:unmount()
            _ha = h:alpha(); _na = n:alpha()
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._ha), .7, places=2)
        self.assertAlmostEqual(float(g._na), .7, places=2)

    def test_rebuild_ledger_restoration_before_reacquire(self):
        lua = _radial_runtime()
        lua.execute(r'''
            _gen_b = R._h5_generation
            local ledger = {}
            local orig_set_alpha = h.set_alpha
            h.set_alpha = function(self, value)
                table.insert(ledger, value)
                return orig_set_alpha(self, value)
            end
            R:rebuild(m)
            R:update(m, 2.2, .05)
            h.set_alpha = orig_set_alpha
            _ha = h:alpha()
            _gen_a = R._h5_generation
            _ledger = ledger
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._ha), 0, places=2)
        self.assertGreater(int(g._gen_a), int(g._gen_b))
        ledger = [g._ledger[i] for i in range(1, len(g._ledger) + 1)]
        self.assertGreater(len(ledger), 0, "ledger must have entries")
        restored_idx = None
        reacquired_idx = None
        for i, val in enumerate(ledger):
            if abs(float(val) - 0.7) < 0.01 and restored_idx is None:
                restored_idx = i
            if abs(float(val) - 0.0) < 0.01 and restored_idx is not None and reacquired_idx is None:
                reacquired_idx = i
        self.assertIsNotNone(restored_idx, "must restore .7")
        self.assertIsNotNone(reacquired_idx, "must reacquire 0")
        self.assertLess(restored_idx, reacquired_idx, "restoration .7 must occur before reacquire 0")

    def test_setter_throw_retains_entry_then_restores(self):
        for scenario in ["throw", "noop"]:
            with self.subTest(scenario=scenario):
                lua = _radial_runtime()
                lua.execute(r'''
                    local nv = kyohud.hud.native_visibility
                    local orig_set_alpha = h.set_alpha
                    ''' + ('''
                    h.set_alpha = function(self, value) error("boom") end
                    ''' if scenario == "throw" else '''
                    h.set_alpha = function(self, value) end
                    ''') + r'''
                    local owned_sentinel = panel_double:bitmap({name="owned_sentinel"})
                    owned_sentinel:set_alpha(.6)
                    local orig_owned_set = owned_sentinel.set_alpha
                    local owned_called = false
                    owned_sentinel.set_alpha = function(self, value)
                        owned_called = true
                        return orig_owned_set(self, value)
                    end
                    kyohud.settings.enable_player = false
                    R:refresh_settings(m)
                    R:update(m, 2.2, .05)
                    _ha = h:alpha()
                    _entry_kept = false
                    for _,e in ipairs(nv._entries) do
                        if e.object == h then _entry_kept = true end
                    end
                    _wl_alpha = nv._whitelist[h] and nv._whitelist[h].alpha or false
                    h.set_alpha = orig_set_alpha
                    owned_sentinel.set_alpha = orig_owned_set
                    _owned_called = owned_called
                    _owned_alpha = owned_sentinel:alpha()
                    R:update(m, 2.8, .05)
                    _ha2 = h:alpha()
                ''')
                g = lua.globals()
                self.assertAlmostEqual(float(g._ha), 0, places=2)
                self.assertTrue(bool(g._entry_kept))
                self.assertTrue(bool(g._wl_alpha))
                self.assertFalse(bool(g._owned_called), "owned UI setters must not be affected")
                self.assertAlmostEqual(float(g._owned_alpha), .6, places=2)
                self.assertAlmostEqual(float(g._ha2), .7, places=2)

    def test_other_owner_untouched(self):
        lua = _radial_runtime()
        lua.execute(r'''
            local nv = kyohud.hud.native_visibility
            local sentinel = panel_double:bitmap({name="sentinel"})
            sentinel:set_alpha(.5)
            nv._whitelist[sentinel] = {alpha=true}
            nv:acquire("other_owner", 1, {{id=sentinel, property="alpha", value=.3}})
            _before = sentinel:alpha()
            kyohud.settings.enable_player = false
            R:refresh_settings(m)
            R:update(m, 2.2, .05)
            _after = sentinel:alpha()
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._before), .3, places=2)
        self.assertAlmostEqual(float(g._after), .3, places=2)

    def test_preexisting_wl_restored_exactly(self):
        lua = _radial_runtime()
        lua.execute(r'''
            local nv = kyohud.hud.native_visibility
            nv._whitelist[h] = {alpha=false}
            kyohud.settings.enable_player = false
            R:refresh_settings(m)
            R:update(m, 2.2, .05)
            _ha = h:alpha()
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._ha), .7, places=2)


class NativeIdentityTests(unittest.TestCase):
    def test_identity_mount_color_and_recovery(self):
        lua = _radial_runtime()
        lua.execute(r'''
            local color_proxy = newproxy(true)
            getmetatable(color_proxy).__index = {r=0.2, g=0.6, b=0.3}
            local orig_n_color = n.color
            n.color = function(self) return color_proxy end
            local font_proxy_id = newproxy(true)
            local orig_Idstring = Idstring
            Idstring = function(v)
                if v == "fonts/font_medium_mf" then
                    return font_proxy_id
                end
                return orig_Idstring(v)
            end
            local P = kyohud.hud.player
            local label = P._h5_id_label
            local orig_label_font = label.font
            local orig_label_set_font = label.set_font
            _font_attempts = 0
            label.font = function(self)
                _font_attempts = _font_attempts + 1
                error("unsafe native live font getter")
            end
            label.set_font = function(self)
                _font_attempts = _font_attempts + 1
                error("unsafe native live font setter")
            end
            R:update(m, 2.2, .05)
            _has_label = label ~= nil
            _lbl_text = label and label:text() or nil
            _lbl_vis = label and label:visible() or false
            _lbl_alpha = label and label:alpha() or 0

            local lbl_color = label:color()
            _lbl_r = lbl_color and lbl_color.r or 0
            _lbl_g = lbl_color and lbl_color.g or 0
            _lbl_b = lbl_color and lbl_color.b or 0
            _n_alpha = n:alpha()
            label.font = orig_label_font
            label.set_font = orig_label_set_font
            n.color = orig_n_color
            Idstring = orig_Idstring
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._has_label))
        self.assertEqual(g._lbl_text, "Test")
        self.assertTrue(bool(g._lbl_vis))
        self.assertGreater(float(g._lbl_alpha), 0)
        self.assertEqual(g._font_attempts, 0, "font is fixed at construction, never probed live")
        self.assertAlmostEqual(float(g._lbl_r), .2, places=2)
        self.assertAlmostEqual(float(g._lbl_g), .6, places=2)
        self.assertAlmostEqual(float(g._lbl_b), .3, places=2)
        self.assertAlmostEqual(float(g._n_alpha), 0, places=2, msg="native name must stay masked")

    def test_identity_corruption_recovery(self):
        lua = _radial_runtime()
        lua.execute(r'''
            local P = kyohud.hud.player
            local label = P._h5_id_label
            label:set_text("CORRUPT")
            label:set_alpha(0.1)
            label:set_visible(false)
            R:update(m, 2.2, .05)
            _text = label:text()
            _alpha = label:alpha()
            _vis = label:visible()
            _same = (label == P._h5_id_label)
        ''')
        g = lua.globals()
        self.assertEqual(g._text, "Test")
        self.assertGreater(float(g._alpha), 0)
        self.assertTrue(bool(g._vis))
        self.assertTrue(bool(g._same))

    def test_identity_long_utf8_truncation(self):
        lua = _radial_runtime()
        lua.execute(r'''
            local slot = HUDManager.PLAYER_PANEL
            local ep = m._teammate_panels[slot]._panel
            local name_leaf = ep:child("name")
            name_leaf:set_text(string.rep("\195\169", 128))
            R:update(m, 2.2, .05)
            local P = kyohud.hud.player
            local label = P._h5_id_label
            _text = label and label:text() or nil
            _len = _text and #_text or 0
            _source_unchanged = name_leaf:text() == string.rep("\195\169", 128)
            local _, _, ink_w, ink_h = label:text_rect()
            _fits = ink_w <= label:w() and ink_h <= label:h()
            local original_measure = label.text_rect
            _repeat_measures = 0
            label.text_rect = function(self)
                _repeat_measures = _repeat_measures + 1
                return original_measure(self)
            end
            R:update(m, 2.8, .05)
        ''')
        g = lua.globals()
        self.assertIsNotNone(g._text)
        self.assertLess(int(g._len), 256)
        self.assertTrue(g._source_unchanged)
        self.assertTrue(g._fits)
        self.assertLessEqual(g._repeat_measures, 3, 'unchanged long names must not refit every frame')

    def test_unknown_owned_child_lookup_refuses_identity_creation(self):
        lua = _radial_runtime()
        lua.execute(r'''
            local P = kyohud.hud.player
            P._root:remove(P._h5_id_label)
            P._h5_id_label = nil
            local original_child = P._root.child
            local original_text = P._root.text
            _created = 0
            P._root.child = function() error('unreadable child registry') end
            P._root.text = function(self, cfg)
                _created = _created + 1
                return original_text(self, cfg)
            end
            R:update(m, 2.2, .05)
            _native_alpha = n:alpha()
            P._root.child = original_child
            R:update(m, 2.8, .05)
            _recovered = P._h5_id_label ~= nil and P._h5_id_label:visible() and n:alpha() == 0
        ''')
        self.assertEqual(lua.globals()._created, 1, 'only recovery may construct a label')
        self.assertAlmostEqual(lua.globals()._native_alpha, .7)
        self.assertTrue(lua.globals()._recovered)

    def test_condition_timer_overlap_releases_native(self):
        lua = _radial_runtime()
        lua.execute(r'''
            local slot = HUDManager.PLAYER_PANEL
            local ep = m._teammate_panels[slot]._panel
            local P = kyohud.hud.player
            local owned_before = P._h5_id_label
            local ct = ep:text({name="condition_timer", text="10"})
            ct:set_shape(P._root:x(), P._root:y(), 50, 20)
            ct:set_visible(true)
            _ha_before = h:alpha(); _na_before = n:alpha()
            R:update(m, 2.2, .05)
            _p_vis = P._root and P._root:visible() or false
            _ha_after = h:alpha(); _na_after = n:alpha()
            ct:set_visible(false)
            R:update(m, 2.8, .05)
            _p_vis2 = P._root and P._root:visible() or false
            local owned_name = P._h5_id_label
            _same_name = owned_before == owned_name
            _owned_vis = owned_name and owned_name:visible() or false
            _owned_text = owned_name and owned_name:text() or nil
            _ha_final = h:alpha(); _na_final = n:alpha()
        ''')
        g = lua.globals()
        self.assertFalse(bool(g._p_vis), "P must be hidden when condition_timer present")
        self.assertAlmostEqual(float(g._ha_after), .7, places=2, msg="h alpha restored to .7")
        self.assertAlmostEqual(float(g._na_after), .7, places=2, msg="n alpha restored to .7")
        self.assertTrue(bool(g._p_vis2), "P must be visible after timer hidden")
        self.assertTrue(bool(g._owned_vis), "owned name must be visible")
        self.assertEqual(g._owned_text, "Test", "owned name must be same primitive")
        self.assertTrue(g._same_name)
        self.assertAlmostEqual(float(g._ha_final), 0, places=2, msg="h alpha masked to 0")
        self.assertAlmostEqual(float(g._na_final), 0, places=2, msg="n alpha masked to 0")

    def test_foreign_name_collision_preserves_unknown(self):
        lua = _radial_runtime()
        lua.execute(r'''
            local P = kyohud.hud.player
            local old_label = P._h5_id_label
            P._root:remove(old_label)
            P._h5_id_label = nil
            local foreign = P._root:text({name="kyohud_local_id_text", text="Foreign"})
            foreign:set_shape(10, 10, 50, 20); foreign:set_visible(true)
            _foreign_text_before = foreign:text()
            _foreign_vis_before = foreign:visible()
            _foreign_x, _foreign_y = foreign:x(), foreign:y()
            _foreign_w, _foreign_h = foreign:w(), foreign:h()
            R:update(m, 2.2, .05)
            _foreign_alive = alive(foreign)
            _foreign_text_after = alive(foreign) and foreign:text() or nil
            _foreign_vis_after = alive(foreign) and foreign:visible() or false
            _foreign_x2, _foreign_y2 = foreign:x(), foreign:y()
            _foreign_w2, _foreign_h2 = foreign:w(), foreign:h()
            local slot = HUDManager.PLAYER_PANEL
            local ep = m._teammate_panels[slot]._panel
            local native_name = ep:child("name")
            _native_name_alpha = native_name:alpha()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._foreign_alive), "foreign text must stay alive")
        self.assertEqual(g._foreign_text_after, g._foreign_text_before, "foreign text must be unchanged")
        self.assertEqual(bool(g._foreign_vis_after), bool(g._foreign_vis_before), "foreign visible must be unchanged")
        for dimension in ('x', 'y', 'w', 'h'):
            self.assertEqual(g['_foreign_' + dimension + '2'], g['_foreign_' + dimension])
        self.assertAlmostEqual(float(g._native_name_alpha), .7, places=2, msg="native name must be unmasked")


class NativeUnknownSourceTests(unittest.TestCase):
    def test_partial_deployable_quantities_preserve_native(self):
        lua = _radial_runtime()
        lua.execute(r'''
            local player = m._teammate_panels[HUDManager.PLAYER_PANEL]._panel:child('player')
            local deploy = player:panel({name='deployable_equipment_panel'})
            local amount = deploy:text({name='amount',text='1|2'})
            amount:set_shape(0, 0, 40, 20); amount:set_alpha(.7)
            managers.player:_native_set_equipment('doctor_bag', {1,2})
            R:update(m, 2.2, .05)
            _positive = amount:alpha()
            managers.player:_native_set_equipment('doctor_bag', {1,'unknown'})
            R:update(m, 2.8, .05)
            _after_unknown = amount:alpha()
        ''')
        self.assertEqual(lua.globals()._positive, 0)
        self.assertAlmostEqual(lua.globals()._after_unknown, .7)

    def test_damage_health_nil_restores_native(self):
        lua = _radial_runtime()
        lua.execute(r'''
            local pu = managers.player:player_unit()
            pu:character_damage()._health = nil
            R:update(m, 2.2, .05)
            _ha = h:alpha()
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._ha), .7, places=2)

    def test_weapon_clip_nil_preserves_native_ammo(self):
        lua = _radial_runtime(enable_weapons=True)
        lua.execute(r'''
            local slot = HUDManager.PLAYER_PANEL
            local ep = m._teammate_panels[slot]._panel
            local player = ep:child("player")
            local weapons = player:panel({name="weapons_panel"})
            weapons:set_shape(70, 0, 80, 68); weapons:set_visible(true)
            local primary = weapons:panel({name="primary_weapon_panel"})
            primary:set_shape(0, 0, 80, 32); primary:set_visible(true)
            local clip = primary:text({name="ammo_clip", text="30"})
            clip:set_shape(0, 0, 40, 32); clip:set_visible(true); clip:set_alpha(.7)
            local total = primary:text({name="ammo_total", text="120"})
            total:set_shape(40, 0, 40, 32); total:set_visible(true); total:set_alpha(.7)
            R:update(m, 2.2, .05)
            _clip_alpha_masked = clip:alpha()
            _total_alpha_masked = total:alpha()
            h5_test_base2:_native_set_ammo(30, nil, 120, 150)
            R:update(m, 2.8, .05)
            _clip_alpha_restored = clip:alpha()
            _total_alpha_restored = total:alpha()
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._clip_alpha_masked), 0, places=2, msg="clip must be masked to 0")
        self.assertAlmostEqual(float(g._total_alpha_masked), 0, places=2, msg="total must be masked to 0")
        self.assertAlmostEqual(float(g._clip_alpha_restored), .7, places=2, msg="clip must restore to .7")
        self.assertAlmostEqual(float(g._total_alpha_restored), .7, places=2, msg="total must restore to .7")

    def test_grenade_unknown_kind_preserves_native(self):
        lua = _radial_runtime()
        lua.execute(r'''
            local slot = HUDManager.PLAYER_PANEL
            local ep = m._teammate_panels[slot]._panel
            local player = ep:child("player")
            local grenades = player:panel({name="grenades_panel"})
            grenades:set_shape(150, 0, 48, 32); grenades:set_visible(true)
            local gbg = grenades:bitmap({name="bg"})
            gbg:set_shape(0, 0, 48, 32); gbg:set_visible(true); gbg:set_alpha(.7)
            local gicon = grenades:bitmap({name="grenades_icon"})
            gicon:set_shape(0, 0, 32, 32); gicon:set_visible(true); gicon:set_alpha(.7)
            local gamt = grenades:text({name="amount", text="3"})
            gamt:set_shape(0, 0, 48, 32); gamt:set_visible(true); gamt:set_alpha(.7)
            local grad = grenades:bitmap({name="grenades_radial"})
            grad:set_shape(0, 0, 32, 32); grad:set_visible(true); grad:set_alpha(.5)
            local gghost = grenades:bitmap({name="grenades_radial_ghost"})
            gghost:set_shape(0, 0, 32, 32); gghost:set_visible(true); gghost:set_alpha(.5)
            _known_kind = kyohud.hud.equipment:get_snapshot().projectile.kind
            R:update(m, 2.2, .05)
            _bg_a = gbg:alpha(); _icon_a = gicon:alpha(); _amt_a = gamt:alpha()
            _rad_a = grad:alpha(); _ghost_a = gghost:alpha()
            _native_set_projectile_tweak('frag', {})
            managers.player:_native_set_grenades('frag', 3, 3)
            local E = kyohud.hud.equipment
            R:update(m, 2.8, .05)
            _bg_a2 = gbg:alpha(); _icon_a2 = gicon:alpha(); _amt_a2 = gamt:alpha()
            _rad_a2 = grad:alpha(); _ghost_a2 = gghost:alpha()
        ''')
        g = lua.globals()
        self.assertEqual(g._known_kind, 'throwable')
        self.assertAlmostEqual(float(g._bg_a), 0, places=2)
        self.assertAlmostEqual(float(g._icon_a), 0, places=2)
        self.assertAlmostEqual(float(g._amt_a), 0, places=2)
        self.assertAlmostEqual(float(g._rad_a), .5, places=2, msg="radial must NOT be masked")
        self.assertAlmostEqual(float(g._ghost_a), .5, places=2, msg="ghost must NOT be masked")
        self.assertAlmostEqual(float(g._bg_a2), .7, places=2)
        self.assertAlmostEqual(float(g._icon_a2), .7, places=2)
        self.assertAlmostEqual(float(g._amt_a2), .7, places=2)
        self.assertAlmostEqual(float(g._rad_a2), .5, places=2, msg="radial unchanged")
        self.assertAlmostEqual(float(g._ghost_a2), .5, places=2, msg="ghost unchanged")
if __name__ == "__main__":
    unittest.main()
