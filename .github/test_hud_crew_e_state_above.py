"""Crew card state above -- condition+interaction placed ABOVE main dark body (RED tracer).

Two compact tests against lua/hud/components/crew_card.lua via real lupa.luajit21.

Interface under test:
  CC.new creates: _state_bg rect, _condition_icon bitmap,
    _down_top/_down_bottom/_down_left/_down_right rects
  Root extends upward reserving space; body children translate down preserving
  WORLD positions of name/gauge/ammo/equipment across normal->interaction->downed->normal.
  State bottom <= mainbackdrop top - 2e; statebg covers icon/text in root coords.
  Status+interaction disjoint if both present.
  Normal: no statebg/icon/outline visible; bots minimal no alerts.
  condition_icon mugshot_downed -> native bitmap 24e separate from downsheart.
  Down icon: guis/textures/hud_icons rect {240, 464, 48, 48} (verified native hudiconstweakdata.lua:2127).
  Pulse icon alpha .55 to 1 at t=0,.5,1,2 incl time backwards finite, no disappearing.
  Subtle four red strokes alpha .15-.5; root/backdrop remains dark peer name/health color unchanged.
  Scales .95/1/1.05 compact loops.

Helper sums x/y through parent() (no unimplemented fixture set_y).
Capture BEFORE positions and primitive identities.
"""
import unittest

from test_hud_crew_e_equipment_icons import _lua, ICON_FIXTURE

_MUGSHOT_DOWNED_FIXTURE = ICON_FIXTURE + '''
    tweak_data.hud_icons = tweak_data.hud_icons or {}
    local _orig_get_icon = tweak_data.hud_icons.get_icon_data
    function tweak_data.hud_icons:get_icon_data(id)
        if id == "mugshot_downed" then
            return "guis/textures/hud_icons", {240, 464, 48, 48}
        end
        return _orig_get_icon(self, id)
    end
'''

_WORLD_POS_HELPER = '''
    function _world_y(p)
        local total = 0
        local cur = p
        while cur ~= nil do
            local ok, y = pcall(function() return cur:y() end)
            if ok and type(y) == "number" then total = total + y end
            local pok, par = pcall(function() return cur:parent() end)
            if not pok or par == nil then break end
            cur = par
        end
        return total
    end
    function _world_x(p)
        local total = 0
        local cur = p
        while cur ~= nil do
            local ok, x = pcall(function() return cur:x() end)
            if ok and type(x) == "number" then total = total + x end
            local pok, par = pcall(function() return cur:parent() end)
            if not pok or par == nil then break end
            cur = par
        end
        return total
    end
'''

_HUMAN_NORMAL = '''
    name = "Test", level = 5, rank = 0, ai = false, peer_id = 1,
    character_name = "spanish",
    health = {current=50, total=100, ratio=0.5, valid=true, provenance="network_quantized"},
    armor  = {current=2,  total=5,   ratio=0.4, valid=true, provenance="network_quantized"},
    weapon = {name_id="wpn_test", ammo={current_clip=24, reserve=114}},
    equipment = {
        deployable  = {id="ammo_bag", amount=2, name_id="ammo_bag_name"},
        cable_ties  = {amount=0},
        projectile  = {id="smoke_screen_grenade", amount=1, kind="ability", name_id="ability_smoke"}
    },
    downs = 0, condition_text = "normal", interaction = nil,
    condition_icon = nil, condition_phase = nil
'''

_BOT = '''
    name = nil, level = nil, rank = nil, ai = true, peer_id = nil,
    character_name = "russian",
    health = nil, armor = nil, weapon = nil, equipment = nil, interaction = nil,
    downs = nil, condition_text = nil, condition_icon = nil, condition_phase = nil
'''


def _setup(lua, name="sta"):
    lua.execute(f'''
        local parent = _G.panel_double
        local CC = kyohud.hud.crew_card
        _inst = CC.new(parent, "{name}")
        _inst:set_geometry(0, 0, 340, 120)
    ''')


class CrewCardStateAboveTests(unittest.TestCase):

    def test_state_above_red_fields_and_positioning(self):
        """Fields _state_bg/_condition_icon/_down_* MUST exist.
        Normal: no statebg/icon/outline visible.
        Interaction ABOVE: state text bottom <= mainbackdrop top - 2e, font >= 18.
        Downed ABOVE: same body WORLD coords preserved, status+interaction disjoint.
        Normal restore: deco hidden. Bot: minimal no alerts.
        Unknown health alone must NOT trigger down state."""
        lua, ok = _lua(setup=_MUGSHOT_DOWNED_FIXTURE + _WORLD_POS_HELPER)
        self.assertTrue(ok, "RED: crew_card.lua must exist")
        if not ok:
            return
        _setup(lua, "above1")

        lua.execute('''
            _has_state_bg = _inst._state_bg ~= nil
            _has_cond_icon = _inst._condition_icon ~= nil
            _has_dt = _inst._down_top ~= nil
            _has_db = _inst._down_bottom ~= nil
            _has_dl = _inst._down_left ~= nil
            _has_dr = _inst._down_right ~= nil
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._has_state_bg),
            "_state_bg must exist")
        self.assertTrue(bool(g._has_cond_icon),
            "_condition_icon must exist")
        self.assertTrue(bool(g._has_dt),
            "_down_top must exist")
        self.assertTrue(bool(g._has_db),
            "_down_bottom must exist")
        self.assertTrue(bool(g._has_dl),
            "_down_left must exist")
        self.assertTrue(bool(g._has_dr),
            "_down_right must exist")

        lua.execute('''
            _normal = { ''' + _HUMAN_NORMAL + ''' }
            _inst:update(_normal, 0)

            _sbg_vis_normal = _inst._state_bg:visible()
            _ci_vis_normal = _inst._condition_icon:visible()
            _dt_vis_normal = _inst._down_top:visible()
            _db_vis_normal = _inst._down_bottom:visible()
            _dl_vis_normal = _inst._down_left:visible()
            _dr_vis_normal = _inst._down_right:visible()
            _nm_wy_before = _world_y(_inst._name_text)
            _hp_wy_before = _world_y(_inst._hp_bg)
            _wp_wy_before = _world_y(_inst._weapon_text)
            _eq_wy_before = _world_y(_inst._equipment_text)
            _nm_wx_before = _world_x(_inst._name_text)
            _hp_wx_before = _world_x(_inst._hp_bg)
            _wp_wx_before = _world_x(_inst._weapon_text)
            _eq_wx_before = _world_x(_inst._equipment_text)
            _nm_ref = _inst._name_text
            _hp_ref = _inst._hp_bg
            _wp_ref = _inst._weapon_text
            _eq_ref = _inst._equipment_text
            _bd_ref = _inst._backdrop
            _st_ref = _inst._status_text
            _it_ref = _inst._interaction_text
            _ci_ref = _inst._condition_icon
            _sbg_ref = _inst._state_bg
            _ok_normal = _inst:verify()
        ''')
        g2 = lua.globals()
        self.assertFalse(bool(g2._sbg_vis_normal),
            "state_bg hidden for normal")
        self.assertFalse(bool(g2._ci_vis_normal),
            "condition_icon hidden for normal")
        self.assertFalse(bool(g2._dt_vis_normal),
            "down_top hidden for normal")
        self.assertFalse(bool(g2._db_vis_normal),
            "down_bottom hidden for normal")
        self.assertFalse(bool(g2._dl_vis_normal),
            "down_left hidden for normal")
        self.assertFalse(bool(g2._dr_vis_normal),
            "down_right hidden for normal")
        self.assertTrue(bool(g2._ok_normal), "verify true for normal human")

        lua.execute('''
            _normal.interaction = {enabled=true, success=false,
                tweak_data_id="lockpick", duration=10, started_t=0}
            _inst:update(_normal, 5)
            _nm_wy_int = _world_y(_inst._name_text)
            _hp_wy_int = _world_y(_inst._hp_bg)
            _wp_wy_int = _world_y(_inst._weapon_text)
            _eq_wy_int = _world_y(_inst._equipment_text)
            _nm_wx_int = _world_x(_inst._name_text)
            _hp_wx_int = _world_x(_inst._hp_bg)
            _wp_wx_int = _world_x(_inst._weapon_text)
            _eq_wx_int = _world_x(_inst._equipment_text)
            _same_nm_int = _inst._name_text == _nm_ref
            _same_hp_int = _inst._hp_bg == _hp_ref
            _same_wp_int = _inst._weapon_text == _wp_ref
            _same_eq_int = _inst._equipment_text == _eq_ref
            _st_bottom_int = _inst._interaction_text:y() + _inst._interaction_text:h()
            _bd_top_int = _inst._backdrop:y()
            _state_above_int = _st_bottom_int <= _bd_top_int - 2
            _st_font_int = _inst._interaction_text:font_size()
            _sbg_vis_int = _inst._state_bg:visible()
            _st_vis_int = _inst._interaction_text:visible()
            _int_string = _inst._interaction_text:text()
            _ok_int = _inst:verify()
        ''')
        gi = lua.globals()
        self.assertAlmostEqual(float(gi._nm_wy_int), float(g2._nm_wy_before), delta=1.0,
            msg="name world_y preserved during interaction")
        self.assertAlmostEqual(float(gi._hp_wy_int), float(g2._hp_wy_before), delta=1.0,
            msg="gauge world_y preserved during interaction")
        self.assertAlmostEqual(float(gi._wp_wy_int), float(g2._wp_wy_before), delta=1.0,
            msg="ammo world_y preserved during interaction")
        self.assertAlmostEqual(float(gi._eq_wy_int), float(g2._eq_wy_before), delta=1.0,
            msg="equipment world_y preserved during interaction")
        self.assertAlmostEqual(float(gi._nm_wx_int), float(g2._nm_wx_before), delta=1.0,
            msg="name world_x preserved during interaction")
        self.assertAlmostEqual(float(gi._hp_wx_int), float(g2._hp_wx_before), delta=1.0,
            msg="gauge world_x preserved during interaction")
        self.assertAlmostEqual(float(gi._wp_wx_int), float(g2._wp_wx_before), delta=1.0,
            msg="ammo world_x preserved during interaction")
        self.assertAlmostEqual(float(gi._eq_wx_int), float(g2._eq_wx_before), delta=1.0,
            msg="equipment world_x preserved during interaction")
        self.assertTrue(bool(gi._same_nm_int), "same _name_text during interaction")
        self.assertTrue(bool(gi._same_hp_int), "same _hp_bg during interaction")
        self.assertTrue(bool(gi._same_wp_int), "same _weapon_text during interaction")
        self.assertTrue(bool(gi._same_eq_int), "same _equipment_text during interaction")
        self.assertTrue(bool(gi._state_above_int),
            "state text bottom <= mainbackdrop top - 2e during interaction")
        self.assertGreaterEqual(float(gi._st_font_int), 18.0,
            "state text font >= 18 during interaction")
        self.assertTrue(bool(gi._sbg_vis_int),
            "state_bg visible during interaction")
        self.assertTrue(bool(gi._st_vis_int),
            "interaction text visible during interaction")
        self.assertEqual(gi._int_string, "lockpick 50%")
        self.assertTrue(bool(gi._ok_int), "verify true during interaction")

        lua.execute('''
            _normal.interaction = nil
            _normal.condition_icon = "mugshot_downed"
            _normal.condition_text = "À terre"
            _normal.downs = 3
            _inst:update(_normal, 10)
            _nm_wy_dn = _world_y(_inst._name_text)
            _hp_wy_dn = _world_y(_inst._hp_bg)
            _wp_wy_dn = _world_y(_inst._weapon_text)
            _eq_wy_dn = _world_y(_inst._equipment_text)
            _nm_wx_dn = _world_x(_inst._name_text)
            _hp_wx_dn = _world_x(_inst._hp_bg)
            _wp_wx_dn = _world_x(_inst._weapon_text)
            _eq_wx_dn = _world_x(_inst._equipment_text)
            _same_nm_dn = _inst._name_text == _nm_ref
            _same_hp_dn = _inst._hp_bg == _hp_ref
            _same_wp_dn = _inst._weapon_text == _wp_ref
            _same_eq_dn = _inst._equipment_text == _eq_ref
            _same_ci_dn = _inst._condition_icon == _ci_ref
            _same_bd_dn = _inst._backdrop == _bd_ref
            _st_bottom_dn = _inst._status_text:y() + _inst._status_text:h()
            _bd_top_dn = _inst._backdrop:y()
            _state_above_dn = _st_bottom_dn <= _bd_top_dn - 2
            _st_font_dn = _inst._status_text:font_size()
            _sbg_vis_dn = _inst._state_bg:visible()
            _st_vis_dn = _inst._status_text:visible()
            _ci_vis_dn = _inst._condition_icon:visible()
            _st_text_dn = _inst._status_text:text()
            _ok_dn = _inst:verify()
        ''')
        gd = lua.globals()
        self.assertAlmostEqual(float(gd._nm_wy_dn), float(g2._nm_wy_before), delta=1.0,
            msg="name world_y preserved across downed transition")
        self.assertAlmostEqual(float(gd._hp_wy_dn), float(g2._hp_wy_before), delta=1.0,
            msg="gauge world_y preserved across downed transition")
        self.assertAlmostEqual(float(gd._wp_wy_dn), float(g2._wp_wy_before), delta=1.0,
            msg="ammo world_y preserved across downed transition")
        self.assertAlmostEqual(float(gd._eq_wy_dn), float(g2._eq_wy_before), delta=1.0,
            msg="equipment world_y preserved across downed transition")
        self.assertTrue(bool(gd._same_nm_dn), "same _name_text after downed")
        self.assertTrue(bool(gd._same_hp_dn), "same _hp_bg after downed")
        self.assertTrue(bool(gd._same_wp_dn), "same _weapon_text after downed")
        self.assertTrue(bool(gd._same_eq_dn), "same _equipment_text after downed")
        self.assertTrue(bool(gd._same_ci_dn), "same _condition_icon after downed")
        self.assertTrue(bool(gd._same_bd_dn), "same _backdrop after downed")
        self.assertTrue(bool(gd._state_above_dn),
            "state text bottom <= mainbackdrop top - 2e during downed")
        self.assertGreaterEqual(float(gd._st_font_dn), 18.0,
            "state text font >= 18 during downed")
        self.assertTrue(bool(gd._sbg_vis_dn),
            "state_bg visible during downed")
        self.assertTrue(bool(gd._st_vis_dn),
            "status text visible during downed")
        self.assertTrue(bool(gd._ci_vis_dn),
            "condition_icon visible during downed")
        self.assertEqual(gd._st_text_dn, "À terre",
            "state text matches supplied UTF-8 string")
        self.assertTrue(bool(gd._ok_dn), "verify true during downed")

        lua.execute('''
            _normal.condition_icon = "mugshot_downed"
            _normal.condition_text = "À terre"
            _normal.downs = 3
            _normal.interaction = {enabled=true, success=false,
                tweak_data_id="lockpick", duration=10, started_t=0}
            _inst:update(_normal, 20)
            _st_y_both = _inst._status_text:y()
            _it_y_both = _inst._interaction_text:y()
            _st_vis_both = _inst._status_text:visible()
            _it_vis_both = _inst._interaction_text:visible()
            _st_text_both = _inst._status_text:text()
            _it_text_both = _inst._interaction_text:text()
            _st_x_both = _inst._status_text:x()
            _st_w_both = _inst._status_text:w()
            _it_x_both = _inst._interaction_text:x()
            _it_w_both = _inst._interaction_text:w()
            _it_right = _it_x_both + _it_w_both
            _st_left = _st_x_both
            _disjoint = _it_right <= _st_left + 0.5
            _sbg_vis_both = _inst._state_bg:visible()
            _sbg_x_both = _inst._state_bg:x()
            _sbg_y_both = _inst._state_bg:y()
            _sbg_w_both = _inst._state_bg:w()
            _sbg_h_both = _inst._state_bg:h()
            _sbg_right = _sbg_x_both + _sbg_w_both
            _sbg_bottom = _sbg_y_both + _sbg_h_both
            _st_x = _inst._status_text:x()
            _st_y = _inst._status_text:y()
            _st_right = _st_x + _inst._status_text:w()
            _st_bottom = _st_y + _inst._status_text:h()
            _ci_x = _inst._condition_icon:x()
            _ci_y = _inst._condition_icon:y()
            _ci_right = _ci_x + _inst._condition_icon:w()
            _ci_bottom = _ci_y + _inst._condition_icon:h()
            _sbg_covers_st = _sbg_x_both <= _st_x and _sbg_y_both <= _st_y and
                _sbg_right >= _st_right and _sbg_bottom >= _st_bottom
            _sbg_covers_ci = _sbg_x_both <= _ci_x and _sbg_y_both <= _ci_y and
                _sbg_right >= _ci_right and _sbg_bottom >= _ci_bottom
            _ok_both = _inst:verify()
        ''')
        gb = lua.globals()
        self.assertTrue(bool(gb._st_vis_both), "status visible with both")
        self.assertTrue(bool(gb._it_vis_both), "interaction visible with both")
        self.assertTrue(bool(gb._disjoint),
            "status and interaction must be disjoint if both present")
        self.assertTrue(bool(gb._sbg_vis_both),
            "state_bg visible with both status and interaction")
        self.assertTrue(bool(gb._sbg_covers_st),
            "state_bg covers status text")
        self.assertTrue(bool(gb._sbg_covers_ci),
            "state_bg covers condition icon")
        self.assertTrue(bool(gb._ok_both), "verify true with both status and interaction")

        lua.execute('''
            _normal.condition_icon = nil
            _normal.condition_text = "normal"
            _normal.downs = 0
            _normal.interaction = nil
            _inst:update(_normal, 15)
            _nm_wy_rest = _world_y(_inst._name_text)
            _hp_wy_rest = _world_y(_inst._hp_bg)
            _wp_wy_rest = _world_y(_inst._weapon_text)
            _eq_wy_rest = _world_y(_inst._equipment_text)
            _same_nm_rest = _inst._name_text == _nm_ref
            _same_hp_rest = _inst._hp_bg == _hp_ref
            _same_wp_rest = _inst._weapon_text == _wp_ref
            _same_eq_rest = _inst._equipment_text == _eq_ref
            _same_bd_rest = _inst._backdrop == _bd_ref
            _same_ci_rest = _inst._condition_icon == _ci_ref
            _same_sbg_rest = _inst._state_bg == _sbg_ref
            _sbg_vis_rest = _inst._state_bg:visible()
            _ci_vis_rest = _inst._condition_icon:visible()
            _dt_vis_rest = _inst._down_top:visible()
            _db_vis_rest = _inst._down_bottom:visible()
            _dl_vis_rest = _inst._down_left:visible()
            _dr_vis_rest = _inst._down_right:visible()
            _ok_rest = _inst:verify()
        ''')
        gr = lua.globals()
        self.assertAlmostEqual(float(gr._nm_wy_rest), float(g2._nm_wy_before), delta=1.0,
            msg="name world_y preserved on restore to normal")
        self.assertAlmostEqual(float(gr._hp_wy_rest), float(g2._hp_wy_before), delta=1.0,
            msg="gauge world_y preserved on restore to normal")
        self.assertAlmostEqual(float(gr._wp_wy_rest), float(g2._wp_wy_before), delta=1.0,
            msg="ammo world_y preserved on restore to normal")
        self.assertAlmostEqual(float(gr._eq_wy_rest), float(g2._eq_wy_before), delta=1.0,
            msg="equipment world_y preserved on restore to normal")
        self.assertTrue(bool(gr._same_nm_rest), "same _name_text on restore")
        self.assertTrue(bool(gr._same_hp_rest), "same _hp_bg on restore")
        self.assertTrue(bool(gr._same_wp_rest), "same _weapon_text on restore")
        self.assertTrue(bool(gr._same_eq_rest), "same _equipment_text on restore")
        self.assertTrue(bool(gr._same_bd_rest), "same _backdrop on restore")
        self.assertTrue(bool(gr._same_ci_rest), "same _condition_icon on restore")
        self.assertTrue(bool(gr._same_sbg_rest), "same _state_bg on restore")
        self.assertFalse(bool(gr._sbg_vis_rest),
            "state_bg hidden on restore to normal")
        self.assertFalse(bool(gr._ci_vis_rest),
            "condition_icon hidden on restore to normal")
        self.assertFalse(bool(gr._dt_vis_rest),
            "down_top hidden on restore to normal")
        self.assertFalse(bool(gr._db_vis_rest),
            "down_bottom hidden on restore to normal")
        self.assertFalse(bool(gr._dl_vis_rest),
            "down_left hidden on restore to normal")
        self.assertFalse(bool(gr._dr_vis_rest),
            "down_right hidden on restore to normal")
        self.assertTrue(bool(gr._ok_rest), "verify true after full cycle")

        lua.execute('''
            local bot = { ''' + _BOT + ''' }
            _inst:update(bot, 25)
            _bot_st_vis = _inst._status_text:visible()
            _bot_it_vis = _inst._interaction_text:visible()
            _bot_st_text = _inst._status_text:text()
            _bot_it_text = _inst._interaction_text:text()
            _bot_sbg_vis = _inst._state_bg:visible()
            _bot_ci_vis = _inst._condition_icon:visible()
        ''')
        gbot = lua.globals()
        self.assertFalse(bool(gbot._bot_st_vis), "status hidden for bot")
        self.assertFalse(bool(gbot._bot_it_vis), "interaction hidden for bot")
        self.assertEqual(gbot._bot_st_text, "", "bot status empty")
        self.assertEqual(gbot._bot_it_text, "", "bot interaction empty")
        self.assertFalse(bool(gbot._bot_sbg_vis), "state_bg hidden for bot")
        self.assertFalse(bool(gbot._bot_ci_vis), "condition_icon hidden for bot")

        lua.execute('''
            local unknown_health = {
                name = "Test", level = 5, rank = 0, ai = false, peer_id = 1,
                character_name = "spanish",
                health = {current=nil, total=nil, ratio=nil, valid=false, provenance="unknown"},
                armor = {current=nil, total=nil, ratio=nil, valid=false, provenance="unknown"},
                weapon = nil, equipment = nil, interaction = nil,
                downs = 0, condition_text = "normal",
                condition_icon = nil, condition_phase = nil
            }
            _inst:update(unknown_health, 30)
            _uh_st_vis = _inst._status_text:visible()
            _uh_st_text = _inst._status_text:text()
            _uh_sbg_vis = _inst._state_bg:visible()
            _uh_ci_vis = _inst._condition_icon:visible()
        ''')
        guh = lua.globals()
        self.assertFalse(bool(guh._uh_st_vis),
            "unknown health alone must NOT trigger down state")
        self.assertFalse(bool(guh._uh_sbg_vis),
            "state_bg hidden for unknown health")
        self.assertFalse(bool(guh._uh_ci_vis),
            "condition_icon hidden for unknown health")

    def test_state_above_pulse_corruption_scale_certification(self):
        """condition_icon mugshot_downed bitmap 24e separate from downsheart.
        Native bitmap texture guis/textures/hud_icons, fixture captured rect {240,464,48,48}.
        Pulse icon alpha .55-1 at t=0,.5,1,2 incl time backwards finite, VARIES.
        Subtle four red strokes alpha .15-.5, thin, covering actual mainbackdrop perimeter.
        Root/backdrop remains dark, peer name/health color unchanged.
        Inject state/icon/stroke corruption -> verify false -> ordinary update repair same primitive.
        Scales .95/1/1.05 compact loops."""
        lua, ok = _lua(setup=_MUGSHOT_DOWNED_FIXTURE + _WORLD_POS_HELPER)
        self.assertTrue(ok, "RED: crew_card.lua must exist")
        if not ok:
            return
        _setup(lua, "above2")

        lua.execute('''
            _normal = { ''' + _HUMAN_NORMAL + ''' }
            _normal.condition_icon = "mugshot_downed"
            _normal.condition_text = "À terre"
            _normal.downs = 3
            _inst:update(_normal, 0)

            _ci_ref = _inst._condition_icon
            _bd_ref = _inst._backdrop
            _sbg_ref = _inst._state_bg
            _dt_ref = _inst._down_top
            _db_ref = _inst._down_bottom
            _dl_ref = _inst._down_left
            _dr_ref = _inst._down_right

            _ci_tex = _inst._condition_icon:texture_name()
            _ci_w = _inst._condition_icon:w()
            _ci_h = _inst._condition_icon:h()
            local r = _inst._condition_icon._texture_rect
            _ci_rx = r and r[1] or -1
            _ci_ry = r and r[2] or -1
            _ci_rw = r and r[3] or -1
            _ci_rh = r and r[4] or -1
            _ci_vis = _inst._condition_icon:visible()
            _ci_alpha0 = _inst._condition_icon:alpha()

            _dhi_ref = _inst._downs_icon
            _dhi_vis = _inst._downs_icon:visible()

            _nm_color_before = nil
            pcall(function() _nm_color_before = _inst._name_text:color() end)
            _hp_fill_color_before = nil
            pcall(function() _hp_fill_color_before = _inst._health_fill:color() end)

            _bd_color_before = nil
            pcall(function() _bd_color_before = _inst._backdrop:color() end)
            _bd_alpha_before = _inst._backdrop:alpha()

            _dt_vis = _inst._down_top:visible()
            _db_vis = _inst._down_bottom:visible()
            _dl_vis = _inst._down_left:visible()
            _dr_vis = _inst._down_right:visible()
            _dt_color = nil
            pcall(function() _dt_color = _inst._down_top:color() end)
            _dt_alpha = _inst._down_top:alpha()
            _dt_h = _inst._down_top:h()
            _bd_y = _inst._backdrop:y()
            _bd_x = _inst._backdrop:x()
            _bd_w = _inst._backdrop:w()
            _bd_h = _inst._backdrop:h()
            _dt_x = _inst._down_top:x()
            _dt_y = _inst._down_top:y()
            _dt_w = _inst._down_top:w()
            _db_x = _inst._down_bottom:x()
            _db_y = _inst._down_bottom:y()
            _db_w = _inst._down_bottom:w()
            _db_h = _inst._down_bottom:h()
            _dl_x = _inst._down_left:x()
            _dl_y = _inst._down_left:y()
            _dl_w = _inst._down_left:w()
            _dl_h = _inst._down_left:h()
            _dr_x = _inst._down_right:x()
            _dr_y = _inst._down_right:y()
            _dr_w = _inst._down_right:w()
            _dr_h = _inst._down_right:h()
            _dt_covers_top = _dt_x <= _bd_x and _dt_y <= _bd_y and
                (_dt_x + _dt_w) >= (_bd_x + _bd_w)
            _db_covers_bottom = _db_x <= _bd_x and (_db_y + _db_h) >= (_bd_y + _bd_h) and
                (_db_x + _db_w) >= (_bd_x + _bd_w)
            _dl_covers_left = _dl_x <= _bd_x and _dl_y <= _bd_y and
                (_dl_y + _dl_h) >= (_bd_y + _bd_h)
            _dr_covers_right = (_dr_x + _dr_w) >= (_bd_x + _bd_w) and _dr_y <= _bd_y and
                (_dr_y + _dr_h) >= (_bd_y + _bd_h)

            _ok1 = _inst:verify()
        ''')
        g = lua.globals()
        self.assertEqual(g._ci_tex, "guis/textures/hud_icons",
            "condition_icon texture is guis/textures/hud_icons")
        self.assertEqual(float(g._ci_w), 24.0,
            "condition_icon width is 24")
        self.assertEqual(float(g._ci_h), 24.0,
            "condition_icon height is 24")
        self.assertEqual(float(g._ci_rx), 240.0,
            "condition_icon rect x is 240")
        self.assertEqual(float(g._ci_ry), 464.0,
            "condition_icon rect y is 464")
        self.assertEqual(float(g._ci_rw), 48.0,
            "condition_icon rect w is 48")
        self.assertEqual(float(g._ci_rh), 48.0,
            "condition_icon rect h is 48")
        self.assertTrue(bool(g._ci_vis), "condition_icon visible for downed")
        self.assertGreaterEqual(float(g._ci_alpha0), 0.55,
            "condition_icon alpha >= .55 at t=0")
        self.assertLessEqual(float(g._ci_alpha0), 1.0,
            "condition_icon alpha <= 1 at t=0")
        self.assertTrue(bool(g._dhi_vis), "downs heart still visible for downed human")
        self.assertTrue(bool(g._dt_vis), "down_top visible for downed")
        self.assertTrue(bool(g._db_vis), "down_bottom visible for downed")
        self.assertTrue(bool(g._dl_vis), "down_left visible for downed")
        self.assertTrue(bool(g._dr_vis), "down_right visible for downed")
        self.assertIsNotNone(g._dt_color, "down_top color captured")
        dt_r = float(g._dt_color.r)
        dt_g = float(g._dt_color.g)
        self.assertGreater(dt_r, dt_g,
            "down_top red channel > green channel (red stroke)")
        self.assertGreaterEqual(float(g._dt_alpha), 0.15,
            "down_top alpha >= .15")
        self.assertLessEqual(float(g._dt_alpha), 0.5,
            "down_top alpha <= .5")
        self.assertLessEqual(float(g._dt_h), 3.0,
            "down_top thin (height <= 3)")
        self.assertTrue(bool(g._dt_covers_top),
            "down_top covers mainbackdrop top perimeter")
        self.assertTrue(bool(g._db_covers_bottom),
            "down_bottom covers mainbackdrop bottom perimeter")
        self.assertTrue(bool(g._dl_covers_left),
            "down_left covers mainbackdrop left perimeter")
        self.assertTrue(bool(g._dr_covers_right),
            "down_right covers mainbackdrop right perimeter")
        self.assertTrue(bool(g._ok1), "verify true with downed human")

        lua.execute('''
            _inst:update(_normal, 0)
            _alpha_t0 = _inst._condition_icon:alpha()
            _inst:update(_normal, 0.5)
            _alpha_t05 = _inst._condition_icon:alpha()
            _inst:update(_normal, 1)
            _alpha_t1 = _inst._condition_icon:alpha()
            _inst:update(_normal, 2)
            _alpha_t2 = _inst._condition_icon:alpha()
            _inst:update(_normal, 0.3)
            _alpha_tback = _inst._condition_icon:alpha()
            _same_ci = _inst._condition_icon == _ci_ref
            _ci_vis_t2 = _inst._condition_icon:visible()
        ''')
        gp = lua.globals()
        a0 = float(gp._alpha_t0)
        a05 = float(gp._alpha_t05)
        a1 = float(gp._alpha_t1)
        a2 = float(gp._alpha_t2)
        aback = float(gp._alpha_tback)
        self.assertGreaterEqual(a0, 0.55, "pulse alpha >= .55 at t=0")
        self.assertLessEqual(a0, 1.0, "pulse alpha <= 1 at t=0")
        self.assertGreaterEqual(a05, 0.55, "pulse alpha >= .55 at t=0.5")
        self.assertLessEqual(a05, 1.0, "pulse alpha <= 1 at t=0.5")
        self.assertGreaterEqual(a1, 0.55, "pulse alpha >= .55 at t=1")
        self.assertLessEqual(a1, 1.0, "pulse alpha <= 1 at t=1")
        self.assertGreaterEqual(a2, 0.55, "pulse alpha >= .55 at t=2")
        self.assertLessEqual(a2, 1.0, "pulse alpha <= 1 at t=2")
        self.assertGreaterEqual(aback, 0.55, "pulse alpha >= .55 at t=0.3 (back)")
        self.assertLessEqual(aback, 1.0, "pulse alpha <= 1 at t=0.3 (back)")
        self.assertFalse(a0 == a05 == a1 == a2 == aback,
            "pulse alpha VARIES across t=0/0.5/1/2/0.3")
        self.assertTrue(bool(gp._same_ci), "same _condition_icon across pulse updates")
        self.assertTrue(bool(gp._ci_vis_t2), "condition_icon visible at t=2 (no disappearing)")

        lua.execute('''
            _st_ref = _inst._status_text
            _inst._status_text:set_text("CORRUPTED")
            _ok_bad_st = _inst:verify()
            _st_text_bad = _inst._status_text:text()
            _inst:update(_normal, 5)
            _ok_st_rep = _inst:verify()
            _same_st = _inst._status_text == _st_ref
            _st_text_rep = _inst._status_text:text()
        ''')
        gc = lua.globals()
        self.assertFalse(bool(gc._ok_bad_st),
            "verify false after state text corruption")
        self.assertEqual(gc._st_text_bad, "CORRUPTED", "corruption took effect")
        self.assertTrue(bool(gc._ok_st_rep),
            "verify true after ordinary update repair")
        self.assertTrue(bool(gc._same_st),
            "same _status_text primitive after repair")
        self.assertEqual(gc._st_text_rep, "À terre",
            "state text restored to supplied UTF-8 string")

        lua.execute('''
            _inst._condition_icon:set_image("wrong/texture", 0, 0, 1, 1)
            _ok_bad_ci = _inst:verify()
            _inst:update(_normal, 6)
            _ok_ci_rep = _inst:verify()
            _same_ci_rep = _inst._condition_icon == _ci_ref
            _ci_tex_rep = _inst._condition_icon:texture_name()
        ''')
        gci = lua.globals()
        self.assertFalse(bool(gci._ok_bad_ci),
            "verify false after condition_icon texture corruption")
        self.assertTrue(bool(gci._ok_ci_rep),
            "verify true after condition_icon repair")
        self.assertTrue(bool(gci._same_ci_rep),
            "same _condition_icon primitive after repair")
        self.assertEqual(gci._ci_tex_rep, "guis/textures/hud_icons",
            "condition_icon texture restored after repair")

        lua.execute('''
            _inst._down_top:set_visible(false)
            _ok_bad_stroke = _inst:verify()
            _inst:update(_normal, 7)
            _ok_stroke_rep = _inst:verify()
            _same_dt_rep = _inst._down_top == _dt_ref
            _dt_vis_rep = _inst._down_top:visible()
        ''')
        gs2 = lua.globals()
        self.assertFalse(bool(gs2._ok_bad_stroke),
            "verify false after stroke visibility corruption")
        self.assertTrue(bool(gs2._ok_stroke_rep),
            "verify true after stroke repair")
        self.assertTrue(bool(gs2._same_dt_rep),
            "same _down_top primitive after repair")
        self.assertTrue(bool(gs2._dt_vis_rep),
            "down_top visible after repair")

        lua.execute('''
            _inst:set_geometry(0, 0, 340 * 0.95, 120 * 0.95)
            _inst:update(_normal, 10)
            _ok_s95 = _inst:verify()
            _inst:set_geometry(0, 0, 340, 120)
            _inst:update(_normal, 11)
            _ok_s100 = _inst:verify()
            _inst:set_geometry(0, 0, 340 * 1.05, 120 * 1.05)
            _inst:update(_normal, 12)
            _ok_s105 = _inst:verify()
            _same_bd_scale = _inst._backdrop == _bd_ref
            _same_st_scale = _inst._status_text == _st_ref
            _same_ci_scale = _inst._condition_icon == _ci_ref
        ''')
        gs = lua.globals()
        self.assertTrue(bool(gs._ok_s95), "verify true at scale .95")
        self.assertTrue(bool(gs._ok_s100), "verify true at scale 1.0")
        self.assertTrue(bool(gs._ok_s105), "verify true at scale 1.05")
        self.assertTrue(bool(gs._same_bd_scale), "same _backdrop across scales")
        self.assertTrue(bool(gs._same_st_scale), "same _status_text across scales")
        self.assertTrue(bool(gs._same_ci_scale), "same _condition_icon across scales")

        lua.execute('''
            _nm_color_after = nil
            pcall(function() _nm_color_after = _inst._name_text:color() end)
            _hp_fill_color_after = nil
            pcall(function() _hp_fill_color_after = _inst._health_fill:color() end)
            _bd_color_after = nil
            pcall(function() _bd_color_after = _inst._backdrop:color() end)
            _bd_alpha_after = _inst._backdrop:alpha()
            _nm_r_before = _nm_color_before and _nm_color_before.r or nil
            _nm_r_after = _nm_color_after and _nm_color_after.r or nil
            _hp_r_before = _hp_fill_color_before and _hp_fill_color_before.r or nil
            _hp_r_after = _hp_fill_color_after and _hp_fill_color_after.r or nil
            _bd_r = _bd_color_after and _bd_color_after.r or 1
            _bd_g = _bd_color_after and _bd_color_after.g or 1
            _bd_b = _bd_color_after and _bd_color_after.b or 1
        ''')
        gk = lua.globals()
        self.assertIsNotNone(gk._nm_r_before, "name color captured before")
        self.assertAlmostEqual(float(gk._nm_r_after), float(gk._nm_r_before), places=2,
            msg="peer name color unchanged during downed state")
        self.assertIsNotNone(gk._hp_r_before, "health fill color captured before")
        self.assertAlmostEqual(float(gk._hp_r_after), float(gk._hp_r_before), places=2,
            msg="peer health color unchanged during downed state")
        self.assertLessEqual(float(gk._bd_r), 0.1,
            "root/backdrop remains dark R<=.1")
        self.assertLessEqual(float(gk._bd_g), 0.1,
            "root/backdrop remains dark G<=.1")
        self.assertLessEqual(float(gk._bd_b), 0.1,
            "root/backdrop remains dark B<=.1")
        self.assertAlmostEqual(float(gk._bd_alpha_after), float(g._bd_alpha_before), places=2,
            msg="backdrop alpha unchanged")


class CrewCardStateSafetyTests(unittest.TestCase):
    def test_condition_bitmap_binding_is_hidden_cached_and_recoverable(self):
        lua, exists = _lua(setup=_MUGSHOT_DOWNED_FIXTURE)
        self.assertTrue(exists)
        _setup(lua, "safe_state")
        lua.execute('''
            actor = { ''' + _HUMAN_NORMAL + ''' }
            actor.condition_icon = "mugshot_downed"
            actor.condition_text = "À terre"
            local icon = _inst._condition_icon
            local image = icon.set_image
            local visible = icon.set_visible
            local calls, unsafe, fail = 0, 0, false
            icon.set_image = function(self, ...)
                calls = calls + 1
                if self:visible() then unsafe = unsafe + 1 end
                if fail then error("bind unavailable") end
                return image(self, ...)
            end
            assert(_inst:update(actor, 0) and _inst:verify())
            assert(calls == 1 and unsafe == 0 and icon:visible())
            assert(_inst:update(actor, .5) and _inst:verify())
            assert(calls == 1, "unchanged condition must not rebind")
            image(icon, "wrong/texture", 0, 0, 1, 1)
            fail = true
            assert(_inst:update(actor, 1) and _inst:verify())
            assert(not icon:visible() and _inst._status_text:visible())
            assert(_inst._status_text:text() == "À terre" and unsafe == 0)
            fail = false
            assert(_inst:update(actor, 1.5) and _inst:verify())
            assert(icon:visible() and icon == _inst._condition_icon and unsafe == 0)
            local before = calls
            icon.set_visible = function(self, value)
                if value ~= false then visible(self, value) end
            end
            assert(not _inst:update(actor, 2))
            assert(calls == before and not _inst.root:visible())
            icon.set_visible = visible
            assert(_inst:update(actor, 2.5) and _inst:verify())
            _inst._state_bg:set_alpha(0)
            assert(not _inst:verify())
            assert(_inst:update(actor, 3) and _inst:verify())
            actor.condition_icon = "mugshot_normal"
            actor.condition_text = ""
            assert(_inst:update(actor, 4) and _inst:verify())
            assert(not icon:visible() and not _inst._state_bg:visible())
        ''')

    def test_runtime_header_is_inside_owned_parent_without_moving_body(self):
        from test_hud_crew import _lua as owner_lua

        lua, exists = owner_lua(setup=_MUGSHOT_DOWNED_FIXTURE + _WORLD_POS_HELPER)
        self.assertTrue(exists)
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_crew = true
            _G.panel_double:set_shape(0, 0, 1920, 1080)
            local mgr, rt = managers.hud, kyohud.hud.runtime
            rt:refresh_settings(mgr)
            rt:update(mgr, 0, 0)
            local crew = kyohud.hud.crew
            assert(crew._render_verified)
            local card
            for _, entry in ipairs(kyohud.hud.actors:get_crew_snapshot()) do
                if entry.peer_id == 2 then card = crew._cards[entry.position] end
            end
            assert(card, "actual remote roster actor required")
            local gauge_y, name_y = _world_y(card._hp_bg), _world_y(card._name_text)
            local card_root, parent = card.root, crew._root
            local function condition(icon, text)
                mgr:set_teammate_condition(2, icon, text)
                local dispatched = false
                for _, hook in ipairs(Hooks._all) do
                    if hook.method == "set_teammate_condition" then
                        hook.fn(mgr, 2, icon, text)
                        dispatched = true
                    end
                end
                assert(dispatched, "real registered condition callback required")
            end
            condition("mugshot_downed", "À terre")
            rt:update(mgr, 1, 1)
            assert(crew._render_verified and card:verify())
            assert(card._state_bg:visible() and card._condition_icon:visible())
            assert(card.root == card_root and crew._root == parent)
            assert(math.abs(_world_y(card._hp_bg) - gauge_y) < .01)
            assert(math.abs(_world_y(card._name_text) - name_y) < .01)
            assert(card.root:y() >= 0 and card.root:y() + card.root:h() <= parent:h() + .01)
            assert(card._state_bg:y() >= 0)
            assert(card._state_bg:y() + card._state_bg:h() < card._backdrop:y())
            condition("mugshot_normal", "")
            rt:update(mgr, 2, 1)
            assert(crew._render_verified and card:verify())
            assert(not card._state_bg:visible() and not card._down_top:visible())
            assert(math.abs(_world_y(card._hp_bg) - gauge_y) < .01)
            assert(card.root == card_root and crew._root == parent)
        ''')


if __name__ == "__main__":
    unittest.main()
