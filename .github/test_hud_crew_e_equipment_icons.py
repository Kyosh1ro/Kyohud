"""Crew card equipment icons -- row r4 native bitmap rendering (RED tracer).

Three tests against lua/hud/components/crew_card.lua via real lupa.luajit21.

Interface under test (extends existing crew card):
  CC.new creates 3 bitmap primitives: _deployable_icon, _cables_icon, _projectile_icon
  Card:update resolves icons from RESOURCES and calls :set_image(texture, x, y, w, h)
  Card:verify checks bitmap texture_name/visibility/crop

Bitmap Diesel contract (G:/PD2-Modding-Docs/pd2-code-doc/src/diesel/classes/ui/bitmap.lua):
  :set_image(texture, x, y, w, h)  -- applies texture + crop (NO texture_rect getter)
  :texture_name()                  -- returns Idstring
  :visible/:set_visible            -- inherited from Panel

Crop is verified via private _texture_rect captured by set_image in base harness.
Production must NOT call texture_rect() (no such getter in Diesel).

RED: crew_card.lua has no _deployable_icon/_cables_icon/_projectile_icon fields,
no icon resolution, and text shows full label instead of quantity-only.
"""
import unittest
from pathlib import Path

from lupa.luajit21 import LuaRuntime
from test_hud_crew_card import STUBS as _CARD_STUBS

ROOT = Path(__file__).resolve().parents[1]
CREW_CARD_PATH = ROOT / "lua" / "hud" / "components" / "crew_card.lua"

BITMAP_ONLY = '''
local _bm_count = 0
local _mt = getmetatable(_G.panel_double)
local _orig_bitmap = _mt.__index.bitmap
_mt.__index.bitmap = function(self, cfg)
    _bm_count = _bm_count + 1
    return _orig_bitmap(self, cfg)
end
_G._bitmap_count = function() return _bm_count end
'''

STUBS = _CARD_STUBS + "\n" + BITMAP_ONLY

ICON_FIXTURE = '''
    managers = managers or {}
    managers.localization = managers.localization or {}
    function managers.localization:text(key)
        local t = {
            menu_spanish = "Chains", menu_russian = "Dallas",
            menu_american = "Hoxton", menu_german = "Wolf",
            ammo_bag_name = "Ammo Bag", doctor_bag_name = "Doctor Bag",
            ability_smoke = "Smoke", ability_frag = "Frag",
        }
        return t[key] or "Loc:" .. tostring(key)
    end

    tweak_data = tweak_data or {}
    tweak_data.hud_icons = tweak_data.hud_icons or {}
    _G._icon_lookups = 0
    function tweak_data.hud_icons:get_icon_data(id)
        _G._icon_lookups = _G._icon_lookups + 1
        local icons = {
            equipment_ammo_bag     = {"guis/textures/pd2/equip_icons", {0, 0, 32, 32}},
            equipment_doctor_bag   = {"guis/textures/pd2/equip_icons", {32, 0, 32, 32}},
            equipment_cable_ties   = {"guis/textures/pd2/equip_icons", {64, 0, 32, 32}},
            smoke_screen_grenade   = {"guis/textures/pd2/equip_icons", {96, 0, 32, 32}},
            frag_grenade           = {"guis/textures/pd2/equip_icons", {128, 0, 32, 32}},
        }
        local e = icons[id]
        if e then return e[1], e[2] end
        error("unknown icon: " .. tostring(id))
    end
    tweak_data.equipments = tweak_data.equipments or {}
    tweak_data.equipments.ammo_bag   = {text_id = "ammo_bag_name",   icon = "equipment_ammo_bag"}
    tweak_data.equipments.doctor_bag = {text_id = "doctor_bag_name", icon = "equipment_doctor_bag"}
    tweak_data.blackmarket = tweak_data.blackmarket or {}
    tweak_data.blackmarket.projectiles = tweak_data.blackmarket.projectiles or {}
    tweak_data.blackmarket.projectiles.smoke_screen_grenade = {
        ability = true, name_id = "ability_smoke", icon = "smoke_screen_grenade"
    }
    tweak_data.blackmarket.projectiles.frag_grenade = {
        ability = true, name_id = "ability_frag", icon = "frag_grenade"
    }

    DB = DB or {}
    _G._db_has_calls = 0
    function DB:has(tid, sid) _G._db_has_calls = _G._db_has_calls + 1; return true end
    Idstring = Idstring or function(s) return s end
'''

_HUMAN_201 = '''
    name = "Test", level = 5, rank = 0, ai = false, peer_id = 1,
    character_name = "spanish",
    health = {current = 50, total = 100, ratio = 0.5, valid = true, provenance = "network_quantized"},
    armor  = {current = 2,  total = 5,   ratio = 0.4, valid = true, provenance = "network_quantized"},
    weapon = {name_id = "wpn_test", ammo = {current_clip = 10, reserve = 50}},
    downs = 0, condition_text = "normal",
    condition_icon = nil, condition_phase = nil
'''

_BOT = '''
    name = nil, level = nil, rank = nil, ai = true, peer_id = nil,
    character_name = "russian",
    health = nil, armor = nil, weapon = nil, equipment = nil, interaction = nil,
    downs = nil, condition_text = nil, condition_icon = nil, condition_phase = nil
'''


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua(setup=""):
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    if setup:
        lua.execute(setup)
    src = _read(CREW_CARD_PATH)
    exists = src is not None
    if exists:
        lua.execute(src)
    return lua, exists


def _setup_card(lua, name="eqicon"):
    lua.execute(f'''
        local parent = _G.panel_double
        local CC = kyohud.hud.crew_card
        _inst = CC.new(parent, "{name}")
        _inst:set_geometry(0, 0, 280, 120)
    ''')


class CrewEquipmentIconTests(unittest.TestCase):

    def test_human_icons_visible_and_transition(self):
        """Human deployable=2/cables=0/projectile=1: 3 distinct bitmaps visible with
        correct textures+crops (via private _texture_rect), texts '2'/'0'/'1', verify true.
        Transition ammo_bag->doctor_bag amount=0 + smoke->frag amount=3: same 3 bitmap
        objects get new textures/crops, texts '0'/'3', verify true."""
        lua, ok = _lua(setup=ICON_FIXTURE)
        self.assertTrue(ok, "RED: crew_card.lua must exist")
        if not ok:
            return
        _setup_card(lua, "eqicon")

        # Phase 1: update human, capture texts FIRST (RED: qty-only before bitmap fields)
        lua.execute('''
            local human = {
                ''' + _HUMAN_201 + ''',
                equipment = {
                    deployable  = {id = "ammo_bag", amount = 2, name_id = "ammo_bag_name"},
                    cable_ties  = {amount = 0},
                    projectile  = {id = "smoke_screen_grenade", amount = 1, kind = "ability", name_id = "ability_smoke"}
                },
            }
            _inst:update(human, 0)
            _eq_txt = _inst._equipment_text:text()
            _cb_txt = _inst._cables_text:text()
            _pj_txt = _inst._projectile_text:text()
        ''')
        g = lua.globals()

        # RED: qty-only texts asserted BEFORE bitmap field access
        self.assertEqual(g._eq_txt, "2",
            "RED: deployable text must be quantity-only '2', not 'ammo_bag_name x2'")
        self.assertEqual(g._cb_txt, "0",
            "RED: cables text must be quantity-only '0', not 'x0'")
        self.assertEqual(g._pj_txt, "1",
            "RED: projectile text must be quantity-only '1', not 'ability charge1'")

        # Phase 2: bitmap fields (crop via private _texture_rect, no texture_rect() getter)
        lua.execute('''
            _has_di  = _inst._deployable_icon ~= nil
            _has_ci  = _inst._cables_icon ~= nil
            _has_pi  = _inst._projectile_icon ~= nil
            _distinct = _has_di and _has_ci and _has_pi and
                (_inst._deployable_icon ~= _inst._cables_icon) and
                (_inst._cables_icon ~= _inst._projectile_icon) and
                (_inst._deployable_icon ~= _inst._projectile_icon)

            _di_tex = _has_di and _inst._deployable_icon:texture_name() or nil
            _ci_tex = _has_ci and _inst._cables_icon:texture_name() or nil
            _pi_tex = _has_pi and _inst._projectile_icon:texture_name() or nil

            -- crop via private _texture_rect (set_image captures it)
            if _has_di then
                local r = _inst._deployable_icon._texture_rect
                _di_x = r and r[1] or 0; _di_y = r and r[2] or 0
                _di_w = r and r[3] or 0; _di_h = r and r[4] or 0
            end
            if _has_ci then
                local r = _inst._cables_icon._texture_rect
                _ci_x = r and r[1] or 0; _ci_y = r and r[2] or 0
            end
            if _has_pi then
                local r = _inst._projectile_icon._texture_rect
                _pi_x = r and r[1] or 0
            end

            -- visibility: preserve false (no 'or nil')
            _di_vis = _has_di and _inst._deployable_icon:visible()
            _ci_vis = _has_ci and _inst._cables_icon:visible()
            _pi_vis = _has_pi and _inst._projectile_icon:visible()

            _ok1 = _inst:verify()

            -- transition: ammo_bag->doctor_bag amount=0, smoke->frag amount=3
            _ref_di = _inst._deployable_icon
            _ref_ci = _inst._cables_icon
            _ref_pi = _inst._projectile_icon

            local human2 = {
                ''' + _HUMAN_201 + ''',
                equipment = {
                    deployable  = {id = "doctor_bag", amount = 0, name_id = "doctor_bag_name"},
                    cable_ties  = {amount = 0},
                    projectile  = {id = "frag_grenade", amount = 3, kind = "ability", name_id = "ability_frag"}
                },
            }
            _inst:update(human2, 1)

            _same_di  = _inst._deployable_icon == _ref_di
            _same_ci  = _inst._cables_icon == _ref_ci
            _same_pi  = _inst._projectile_icon == _ref_pi

            _di_tex2 = _inst._deployable_icon:texture_name()
            _pi_tex2 = _inst._projectile_icon:texture_name()
            local r2 = _inst._deployable_icon._texture_rect
            _di_x2 = r2 and r2[1] or 0
            local r3 = _inst._projectile_icon._texture_rect
            _pi_x2 = r3 and r3[1] or 0

            _eq_txt2 = _inst._equipment_text:text()
            _pj_txt2 = _inst._projectile_text:text()
            _ok2 = _inst:verify()
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._has_di), "RED: _deployable_icon must exist")
        self.assertTrue(bool(g._has_ci), "RED: _cables_icon must exist")
        self.assertTrue(bool(g._has_pi), "RED: _projectile_icon must exist")
        self.assertTrue(bool(g._distinct), "3 bitmaps must be distinct")

        self.assertEqual(g._di_tex, "guis/textures/pd2/equip_icons")
        self.assertEqual(float(g._di_x), 0.0)
        self.assertEqual(float(g._di_y), 0.0)
        self.assertEqual(float(g._di_w), 32.0)
        self.assertEqual(float(g._di_h), 32.0)

        self.assertEqual(g._ci_tex, "guis/textures/pd2/equip_icons")
        self.assertEqual(float(g._ci_x), 64.0)

        self.assertEqual(g._pi_tex, "guis/textures/pd2/equip_icons")
        self.assertEqual(float(g._pi_x), 96.0)

        self.assertTrue(bool(g._di_vis), "deployable visible for human")
        self.assertTrue(bool(g._ci_vis), "cables visible for human")
        self.assertTrue(bool(g._pi_vis), "projectile visible for human")

        self.assertTrue(bool(g._ok1), "verify() true with valid icons")

        self.assertTrue(bool(g._same_di), "same _deployable_icon after transition")
        self.assertTrue(bool(g._same_ci), "same _cables_icon after transition")
        self.assertTrue(bool(g._same_pi), "same _projectile_icon after transition")

        self.assertEqual(g._di_tex2, "guis/textures/pd2/equip_icons")
        self.assertEqual(float(g._di_x2), 32.0, "doctor_bag rect x=32")
        self.assertEqual(float(g._pi_x2), 128.0, "frag rect x=128")

        self.assertEqual(g._eq_txt2, "0", "deployable text '0' after transition")
        self.assertEqual(g._pj_txt2, "3", "projectile text '3' after transition")
        self.assertTrue(bool(g._ok2), "verify() true after transition")

    def test_bot_hide_corrupt_repair_stability(self):
        """Bot: all 3 icons hidden (preserve false), then human restores visible.
        Corrupt bitmap texture -> verify false, update repairs same object.
        Corrupt bitmap visibility (set_visible(false)) -> verify false, update repairs.
        Corrupt bitmap geometry -> verify false, update repairs.
        20 stable updates: no new allocations, bitmap creations, icon lookups, or DB:has calls."""
        lua, ok = _lua(setup=ICON_FIXTURE)
        self.assertTrue(ok, "RED: crew_card.lua must exist")
        if not ok:
            return
        _setup_card(lua, "stab")

        lua.execute('''
            local human = {
                ''' + _HUMAN_201 + ''',
                equipment = {
                    deployable  = {id = "ammo_bag", amount = 2, name_id = "ammo_bag_name"},
                    cable_ties  = {amount = 0},
                    projectile  = {id = "smoke_screen_grenade", amount = 1, kind = "ability", name_id = "ability_smoke"}
                },
            }
            local bot = { ''' + _BOT + ''' }

            _inst:update(human, 0)
            _human_di_vis = _inst._deployable_icon and _inst._deployable_icon:visible()
            _human_ci_vis = _inst._cables_icon and _inst._cables_icon:visible()
            _human_pi_vis = _inst._projectile_icon and _inst._projectile_icon:visible()
            _ref_di = _inst._deployable_icon
            _ref_ci = _inst._cables_icon
            _ref_pi = _inst._projectile_icon

            -- bot: all hidden (preserve false)
            _inst:update(bot, 1)
            _bot_di_vis = _inst._deployable_icon and _inst._deployable_icon:visible()
            _bot_ci_vis = _inst._cables_icon and _inst._cables_icon:visible()
            _bot_pi_vis = _inst._projectile_icon and _inst._projectile_icon:visible()
            _bot_same_di = _inst._deployable_icon == _ref_di
            _bot_same_ci = _inst._cables_icon == _ref_ci
            _bot_same_pi = _inst._projectile_icon == _ref_pi

            -- human restore
            _inst:update(human, 2)
            _rest_di_vis = _inst._deployable_icon:visible()
            _rest_ci_vis = _inst._cables_icon:visible()
            _rest_pi_vis = _inst._projectile_icon:visible()
            _rest_same  = _inst._deployable_icon == _ref_di and
                _inst._cables_icon == _ref_ci and _inst._projectile_icon == _ref_pi
            _ok_clean = _inst:verify()

            -- corruption 1: deployable texture
            _inst._deployable_icon:set_image("wrong/texture", 0, 0, 1, 1)
            _ok_bad_tex = _inst:verify()
            _inst:update(human, 3)
            _ok_tex_rep = _inst:verify()
            _same_tex_rep = _inst._deployable_icon == _ref_di
            _rep_tex = _inst._deployable_icon:texture_name()

            -- corruption 2: cables visibility (set_visible(false))
            _inst._cables_icon:set_visible(false)
            _ok_bad_vis = _inst:verify()
            _bad_vis_val = _inst._cables_icon:visible()
            _inst:update(human, 4)
            _ok_vis_rep = _inst:verify()
            _same_vis_rep = _inst._cables_icon == _ref_ci
            _rep_vis = _inst._cables_icon:visible()

            -- corruption 3: projectile geometry
            _inst._projectile_icon:set_shape(-1, -1, -1, -1)
            _ok_bad_geom = _inst:verify()
            _inst:update(human, 5)
            _ok_geom_rep = _inst:verify()
            _same_geom_rep = _inst._projectile_icon == _ref_pi

            -- stability: 20 updates, no new creations/resolutions
            _alloc_before = _G._alloc_count()
            _bm_before = _G._bitmap_count()
            _icon_before = _G._icon_lookups
            _db_before = _G._db_has_calls
            for i = 1, 20 do
                _inst:update(human, 5 + i * 0.1)
            end
            _alloc_after = _G._alloc_count()
            _bm_after = _G._bitmap_count()
            _icon_after = _G._icon_lookups
            _db_after = _G._db_has_calls
            _alloc_delta = _alloc_after - _alloc_before
            _bm_delta = _bm_after - _bm_before
            _icon_delta = _icon_after - _icon_before
            _db_delta = _db_after - _db_before
            _stable_same = _inst._deployable_icon == _ref_di and
                _inst._cables_icon == _ref_ci and _inst._projectile_icon == _ref_pi
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._human_di_vis))
        self.assertTrue(bool(g._human_ci_vis))
        self.assertTrue(bool(g._human_pi_vis))

        self.assertFalse(bool(g._bot_di_vis), "RED: deployable hidden for bot")
        self.assertFalse(bool(g._bot_ci_vis), "RED: cables hidden for bot")
        self.assertFalse(bool(g._bot_pi_vis), "RED: projectile hidden for bot")
        self.assertTrue(bool(g._bot_same_di), "bot preserves _deployable_icon ref")
        self.assertTrue(bool(g._bot_same_ci), "bot preserves _cables_icon ref")
        self.assertTrue(bool(g._bot_same_pi), "bot preserves _projectile_icon ref")

        self.assertTrue(bool(g._rest_di_vis))
        self.assertTrue(bool(g._rest_ci_vis))
        self.assertTrue(bool(g._rest_pi_vis))
        self.assertTrue(bool(g._rest_same), "same 3 bitmaps after restore")
        self.assertTrue(bool(g._ok_clean), "verify() true before corruption")

        self.assertFalse(bool(g._ok_bad_tex), "RED: verify false after texture corruption")
        self.assertTrue(bool(g._ok_tex_rep), "verify true after texture repair")
        self.assertTrue(bool(g._same_tex_rep), "same bitmap after texture repair")
        self.assertEqual(g._rep_tex, "guis/textures/pd2/equip_icons")

        self.assertFalse(bool(g._ok_bad_vis), "RED: verify false after visibility corruption")
        self.assertFalse(bool(g._bad_vis_val), "corrupted visibility is actual false")
        self.assertTrue(bool(g._ok_vis_rep), "verify true after visibility repair")
        self.assertTrue(bool(g._same_vis_rep), "same bitmap after visibility repair")
        self.assertTrue(bool(g._rep_vis), "restored visibility is true")

        self.assertFalse(bool(g._ok_bad_geom), "RED: verify false after geometry corruption")
        self.assertTrue(bool(g._ok_geom_rep), "verify true after geometry repair")
        self.assertTrue(bool(g._same_geom_rep), "same bitmap after geometry repair")

        self.assertEqual(int(g._alloc_delta), 0, "20 updates: no new allocations")
        self.assertEqual(int(g._bm_delta), 0, "20 updates: no new bitmap creations")
        self.assertEqual(int(g._icon_delta), 0, "20 updates: no new icon lookups")
        self.assertEqual(int(g._db_delta), 0, "20 updates: no new DB:has calls")
        self.assertTrue(bool(g._stable_same), "20 updates: same bitmap objects")

    def test_fallback_db_absent_throwing_unknown_infinity(self):
        """DB absent: icons hidden, texts keep existing format, verify true.
        DB:has throws: icons hidden, verify true.
        Nil equipment: texts not '0', fallback '--'/''.
        Cables -1: infinity symbol."""
        # Scenario 1: DB absent (no hud_icons, no DB)
        lua1, ok1 = _lua(setup='')
        self.assertTrue(ok1, "RED: crew_card.lua must exist")
        if not ok1:
            return
        lua1.execute('''
            managers = managers or {}
            managers.localization = managers.localization or {}
            function managers.localization:text(key)
                local t = { menu_spanish = "Chains", ammo_bag_name = "Ammo Bag" }
                return t[key] or "Loc:" .. tostring(key)
            end
            tweak_data = tweak_data or {}
            tweak_data.equipments = { ammo_bag = {text_id = "ammo_bag_name"} }
            tweak_data.blackmarket = { projectiles = {
                smoke_screen_grenade = {ability = true, name_id = "ability_smoke"}
            }}

            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            _inst1 = CC.new(parent, "fb1")
            _inst1:set_geometry(0, 0, 280, 120)

            local human_no_db = {
                name = "Test", level = 5, rank = 0, ai = false, peer_id = 1,
                character_name = "spanish",
                health = {current=50, total=100, ratio=0.5, valid=true, provenance="network_quantized"},
                armor  = {current=2,  total=5,   ratio=0.4, valid=true, provenance="network_quantized"},
                weapon = {name_id="wpn_test", ammo={current_clip=10, reserve=50}},
                equipment = {
                    deployable  = {id = "ammo_bag", amount = 2, name_id = "ammo_bag_name"},
                    cable_ties  = {amount = 0},
                    projectile  = {id = "smoke_screen_grenade", amount = 1, kind = "ability", name_id = "ability_smoke"}
                },
                downs = 0, condition_text = "normal",
                condition_icon = nil, condition_phase = nil
            }
            _inst1:update(human_no_db, 0)
            _fb_has_di  = _inst1._deployable_icon ~= nil
            _fb_di_vis  = _fb_has_di and _inst1._deployable_icon:visible()
            _fb_ci_vis  = _inst1._cables_icon ~= nil and _inst1._cables_icon:visible()
            _fb_pi_vis  = _inst1._projectile_icon ~= nil and _inst1._projectile_icon:visible()
            _fb_eq_txt  = _inst1._equipment_text:text()
            _fb_cb_txt  = _inst1._cables_text:text()
            _fb_ok      = _inst1:verify()
        ''')
        g1 = lua1.globals()

        self.assertTrue(bool(g1._fb_has_di), "RED: bitmap exists even when DB absent")
        self.assertFalse(bool(g1._fb_di_vis), "RED: deployable hidden when DB absent")
        self.assertFalse(bool(g1._fb_ci_vis), "RED: cables hidden when DB absent")
        self.assertFalse(bool(g1._fb_pi_vis), "RED: projectile hidden when DB absent")
        self.assertIn("x2", g1._fb_eq_txt, "fallback text keeps label format")
        self.assertIn("x0", g1._fb_cb_txt, "fallback cables keeps format")
        self.assertTrue(bool(g1._fb_ok), "verify() true with unresolved icons")

        # Scenario 2: DB:has throws
        lua2, ok2 = _lua(setup='')
        if not ok2:
            return
        lua2.execute('''
            managers = managers or {}
            managers.localization = managers.localization or {}
            function managers.localization:text(key) return "Loc:" .. tostring(key) end
            tweak_data = tweak_data or {}
            tweak_data.equipments = {ammo_bag = {text_id = "ammo_bag_name"}}
            tweak_data.blackmarket = {projectiles = {smoke_screen_grenade = {ability = true, name_id = "ability_smoke"}}}

            DB = {}
            function DB:has(tid, sid) error("DB unavailable") end
            Idstring = function(s) return s end

            tweak_data.hud_icons = {}
            function tweak_data.hud_icons:get_icon_data(id) error("unknown icon") end

            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            _inst2 = CC.new(parent, "fb2")
            _inst2:set_geometry(0, 0, 280, 120)

            local human = {
                name = "Test", level = 5, rank = 0, ai = false, peer_id = 1,
                character_name = "spanish",
                health = {current=50, total=100, ratio=0.5, valid=true, provenance="network_quantized"},
                armor  = {current=2,  total=5,   ratio=0.4, valid=true, provenance="network_quantized"},
                weapon = {name_id="wpn_test", ammo={current_clip=10, reserve=50}},
                equipment = {
                    deployable  = {id = "ammo_bag", amount = 2, name_id = "ammo_bag_name"},
                    cable_ties  = {amount = 0},
                    projectile  = {id = "smoke_screen_grenade", amount = 1, kind = "ability", name_id = "ability_smoke"}
                },
                downs = 0, condition_text = "normal",
                condition_icon = nil, condition_phase = nil
            }
            _inst2:update(human, 0)
            _fb2_di_vis = _inst2._deployable_icon and _inst2._deployable_icon:visible()
            _fb2_ci_vis = _inst2._cables_icon and _inst2._cables_icon:visible()
            _fb2_pi_vis = _inst2._projectile_icon and _inst2._projectile_icon:visible()
            _fb2_ok = _inst2:verify()
        ''')
        g2 = lua2.globals()
        self.assertFalse(bool(g2._fb2_di_vis), "hidden when DB:has throws")
        self.assertFalse(bool(g2._fb2_ci_vis), "hidden when DB:has throws")
        self.assertFalse(bool(g2._fb2_pi_vis), "hidden when DB:has throws")
        self.assertTrue(bool(g2._fb2_ok), "verify() true even when DB:has throws")

        # Scenario 3: nil equipment -> texts not "0"
        lua3, ok3 = _lua(setup='')
        if not ok3:
            return
        lua3.execute('''
            managers = managers or {}
            managers.localization = managers.localization or {}
            function managers.localization:text(key) return "Loc:" .. tostring(key) end

            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            _inst3 = CC.new(parent, "fb3")
            _inst3:set_geometry(0, 0, 280, 120)

            local human_nil = {
                name = "X", level = 1, rank = 0, ai = false, peer_id = 2,
                character_name = "spanish",
                health = {current=50, total=100, ratio=0.5, valid=true, provenance="network_quantized"},
                armor  = {current=2,  total=5,   ratio=0.4, valid=true, provenance="network_quantized"},
                weapon = {name_id="wpn_test", ammo={current_clip=10, reserve=50}},
                equipment = nil,
                downs = 0, condition_text = "normal",
                condition_icon = nil, condition_phase = nil
            }
            _inst3:update(human_nil, 0)
            _nil_eq_txt = _inst3._equipment_text:text()
            _nil_cb_txt = _inst3._cables_text:text()
            _nil_pj_txt = _inst3._projectile_text:text()
        ''')
        g3 = lua3.globals()
        self.assertNotEqual(g3._nil_eq_txt, "0", "nil equip text not '0'")
        self.assertEqual(g3._nil_eq_txt, "--", "nil equip fallback '--'")
        self.assertEqual(g3._nil_cb_txt, "", "nil cables fallback ''")
        self.assertEqual(g3._nil_pj_txt, "--", "nil projectile fallback '--'")

        # Scenario 4: cables -1 -> infinity
        lua4, ok4 = _lua(setup='')
        if not ok4:
            return
        lua4.execute('''
            managers = managers or {}
            managers.localization = managers.localization or {}
            function managers.localization:text(key) return "Loc:" .. tostring(key) end

            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            _inst4 = CC.new(parent, "fb4")
            _inst4:set_geometry(0, 0, 280, 120)

            local human_inf = {
                name = "X", level = 1, rank = 0, ai = false, peer_id = 2,
                character_name = "spanish",
                health = {current=50, total=100, ratio=0.5, valid=true, provenance="network_quantized"},
                armor  = {current=2,  total=5,   ratio=0.4, valid=true, provenance="network_quantized"},
                weapon = {name_id="wpn_test", ammo={current_clip=10, reserve=50}},
                equipment = {
                    deployable  = {id = "ammo_bag", amount = 1, name_id = "ammo_bag_name"},
                    cable_ties  = {amount = -1},
                    projectile  = {id = "smoke_screen_grenade", amount = 1, kind = "ability", name_id = "ability_smoke"}
                },
                downs = 0, condition_text = "normal",
                condition_icon = nil, condition_phase = nil
            }
            _inst4:update(human_inf, 0)
            _inf_cb_txt = _inst4._cables_text:text()
        ''')
        g4 = lua4.globals()
        inf = g4._inf_cb_txt
        self.assertTrue(
            "\u221e" in inf or "\xe2\x88\x9e" in inf,
            "cables amount=-1 must render infinity symbol (U+221E)")

        # Scenario 4b: fallback text captures when all_bound false (DB absent)
        # Desired: semantic labels like "Ammo Bag x3", "x1", "ability charge2"
        lua4b, ok4b = _lua(setup='')
        if not ok4b:
            return
        lua4b.execute('''
            managers = managers or {}
            managers.localization = managers.localization or {}
            function managers.localization:text(key)
                local t = {
                    menu_spanish = "Chains",
                    ammo_bag_name = "Ammo Bag",
                    ability_smoke = "Smoke",
                }
                return t[key] or "Loc:" .. tostring(key)
            end
            tweak_data = tweak_data or {}
            tweak_data.equipments = { ammo_bag = {text_id = "ammo_bag_name"} }
            tweak_data.blackmarket = { projectiles = {
                smoke_screen_grenade = {ability = true, name_id = "ability_smoke"}
            }}

            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            _inst4b = CC.new(parent, "fb4b")
            _inst4b:set_geometry(0, 0, 280, 120)

            local human_fb = {
                name = "Test", level = 5, rank = 0, ai = false, peer_id = 1,
                character_name = "spanish",
                health = {current=50, total=100, ratio=0.5, valid=true, provenance="network_quantized"},
                armor  = {current=2,  total=5,   ratio=0.4, valid=true, provenance="network_quantized"},
                weapon = {name_id="wpn_test", ammo={current_clip=10, reserve=50}},
                equipment = {
                    deployable  = {id = "ammo_bag", amount = 3, name_id = "ammo_bag_name"},
                    cable_ties  = {amount = 1},
                    projectile  = {id = "smoke_screen_grenade", amount = 2, kind = "ability", name_id = "ability_smoke"}
                },
                downs = 0, condition_text = "normal",
                condition_icon = nil, condition_phase = nil
            }
            _inst4b:update(human_fb, 0)
            _fb4b_eq_txt = _inst4b._equipment_text:text()
            _fb4b_cb_txt = _inst4b._cables_text:text()
            _fb4b_pj_txt = _inst4b._projectile_text:text()
            _fb4b_di_vis = _inst4b._deployable_icon and _inst4b._deployable_icon:visible()
            _fb4b_ci_vis = _inst4b._cables_icon and _inst4b._cables_icon:visible()
            _fb4b_pi_vis = _inst4b._projectile_icon and _inst4b._projectile_icon:visible()
            _fb4b_ok = _inst4b:verify()
        ''')
        g4b = lua4b.globals()

        # Icons hidden when DB absent (no hud_icons)
        self.assertFalse(bool(g4b._fb4b_di_vis), "fallback: deployable hidden when DB absent")
        self.assertFalse(bool(g4b._fb4b_ci_vis), "fallback: cables hidden when DB absent")
        self.assertFalse(bool(g4b._fb4b_pi_vis), "fallback: projectile hidden when DB absent")

        # Fallback texts must show semantic labels, not bare numbers
        self.assertTrue(g4b._fb4b_eq_txt.startswith("Amm"),
            "fallback equipment text must start with fitted prefix 'Amm'")
        self.assertIn("x3", g4b._fb4b_eq_txt,
            "fallback equipment text must contain quantity 'x3'")
        self.assertTrue(g4b._fb4b_eq_txt.endswith("x3"),
            "fallback equipment text must end with quantity 'x3'")

        self.assertEqual(g4b._fb4b_cb_txt, "x1",
            "fallback cables text must be 'x1' (quantity format)")

        self.assertIn("charge", g4b._fb4b_pj_txt,
            "fallback projectile text must contain 'charge' keyword")
        self.assertIn("2", g4b._fb4b_pj_txt,
            "fallback projectile text must contain quantity '2'")
        self.assertTrue(g4b._fb4b_pj_txt.endswith("charge2"),
            "fallback projectile text must end with 'charge2' (kind + charge + quantity)")

        self.assertTrue(bool(g4b._fb4b_ok), "verify() true with fallback texts")


    def test_native_bitmap_boundary(self):
        """Strict Idstring/DB/bitmap boundary test (desired-correct contract).

        Strict mocks:
        - Idstring(value):key() returns "key:"..value (distinct from raw path)
        - DB:has checks tid:key()==Idstring("texture"):key() AND sid:key()==Idstring(path):key()
        - Bitmap wrapper: newproxy(true) proxy, methods delegate to real bitmap with
          receiver stripped (function(_, ...) ...), texture_name returns Idstring,
          _-prefixed field access raises error, __newindex forbidden
        - alive() overridden to handle wrappers via weak-key mapping

        Expected (correct behavior): qty texts correct, 3 icons visible (DB:has succeeds
        with proper args), verify() true (no private field access needed),
        private_getter_attempts == 0, DB:has called > 0.
        """
        extension = '''
            local _idstring_mt = {
                __index = function(self, key)
                    if key == "key" then
                        return function() return self._key end
                    end
                    error("Idstring: unknown method " .. tostring(key))
                end,
                __tostring = function(self) return self._key end
            }

            Idstring = function(value)
                return setmetatable({_key = "key:" .. tostring(value), _value = tostring(value)}, _idstring_mt)
            end

            local _db_has_calls = 0
            DB = setmetatable({}, {__index = {has = function(self, tid, sid)
                _db_has_calls = _db_has_calls + 1
                local exp_tid_key = Idstring("texture"):key()
                local exp_sid_key = Idstring("guis/textures/pd2/equip_icons"):key()
                local tid_ok, tid_key = pcall(function() return tid:key() end)
                local sid_ok, sid_key = pcall(function() return sid:key() end)
                return tid_ok and sid_ok and tid_key == exp_tid_key and sid_key == exp_sid_key
            end}})
            _G._db_has_calls = function() return _db_has_calls end

            local _mt = getmetatable(_G.panel_double)
            local _orig_bitmap = _mt.__index.bitmap
            local _wrapper_alive = setmetatable({}, {__mode = "k"})
            local _private_getter_attempts = 0

            _mt.__index.bitmap = function(self, cfg)
                local real = _orig_bitmap(self, cfg)
                local proxy = newproxy(true)
                local mt = getmetatable(proxy)
                mt.__index = function(w, name)
                    if type(name) == "string" and name:sub(1, 1) == "_" then
                        _private_getter_attempts = _private_getter_attempts + 1
                        error("private field access forbidden: " .. name)
                    end
                    if name == "texture_name" then
                        return function()
                            local tex = real._texture
                            return tex and Idstring(tex) or Idstring("")
                        end
                    end
                    local fn = real[name]
                    if type(fn) == "function" then
                        return function(_, ...) return fn(real, ...) end
                    end
                    return fn
                end
                mt.__newindex = function(w, name, value)
                    error("bitmap wrapper: write forbidden")
                end
                _wrapper_alive[proxy] = real
                return proxy
            end

            local _orig_alive = alive
            alive = function(p)
                if _wrapper_alive[p] then
                    return _orig_alive(_wrapper_alive[p])
                end
                return _orig_alive(p)
            end

            _G._private_getter_attempts = function() return _private_getter_attempts end
        '''

        lua, ok = _lua(setup=ICON_FIXTURE + extension)
        self.assertTrue(ok, "RED: crew_card.lua must exist")
        if not ok:
            return
        _setup_card(lua, "boundary")

        lua.execute('''
            local human = {
                ''' + _HUMAN_201 + ''',
                equipment = {
                    deployable  = {id = "ammo_bag", amount = 2, name_id = "ammo_bag_name"},
                    cable_ties  = {amount = 0},
                    projectile  = {id = "smoke_screen_grenade", amount = 1, kind = "ability", name_id = "ability_smoke"}
                },
            }
            _inst:update(human, 0)
            _eq_txt = _inst._equipment_text:text()
            _cb_txt = _inst._cables_text:text()
            _pj_txt = _inst._projectile_text:text()
            _db_calls = _G._db_has_calls()
            _di_vis = _inst._deployable_icon:visible()
            _ci_vis = _inst._cables_icon:visible()
            _pi_vis = _inst._projectile_icon:visible()
            _ok = _inst:verify()
            _priv_attempts = _G._private_getter_attempts()
        ''')
        g = lua.globals()

        self.assertEqual(g._eq_txt, "2", "deployable text qty '2'")
        self.assertEqual(g._cb_txt, "0", "cables text qty '0'")
        self.assertEqual(g._pj_txt, "1", "projectile text qty '1'")

        self.assertGreater(int(g._db_calls), 0, "DB:has called")

        self.assertTrue(bool(g._di_vis), "deployable visible (DB:has correct args)")
        self.assertTrue(bool(g._ci_vis), "cables visible (DB:has correct args)")
        self.assertTrue(bool(g._pi_vis), "projectile visible (DB:has correct args)")

        self.assertTrue(bool(g._ok), "verify() true (no private field access)")
        self.assertEqual(int(g._priv_attempts), 0, "no private field access attempted")

    def test_callable_table_idstring_engine_compatibility(self):
        """Engine Idstring is callable table with __call metatable, not plain function.
        Install callable TABLE Idstring wrapping old function BEFORE consumer executes.
        Assert all 3 icons visible quantities-only, DB probes positive, certification true.
        RED: crew_card.lua resolve_icon line 217 does type(Idstring) ~= "function" which
        rejects callable table Idstring (type returns "table", not "function").
        This test documents the gap between engine reality and production guard."""
        extension = '''
            -- Save original Idstring function
            local _orig_Idstring = Idstring

            -- Install callable TABLE Idstring with __call metatable (engine reality)
            local _idstring_mt = {
                __call = function(self, value)
                    return _orig_Idstring(value)
                end,
                __tostring = function(self) return "callable_table_Idstring" end
            }
            Idstring = setmetatable({}, _idstring_mt)

            -- Verify it's callable
            assert(type(Idstring) == "table", "Idstring must be table")
            local test_result = Idstring("test")
            assert(test_result ~= nil, "callable table Idstring must work")
        '''

        lua, ok = _lua(setup=ICON_FIXTURE + extension)
        self.assertTrue(ok, "RED: crew_card.lua must exist")
        if not ok:
            return
        _setup_card(lua, "callable_idstring")

        lua.execute('''
            local human = {
                ''' + _HUMAN_201 + ''',
                equipment = {
                    deployable  = {id = "ammo_bag", amount = 2, name_id = "ammo_bag_name"},
                    cable_ties  = {amount = 0},
                    projectile  = {id = "smoke_screen_grenade", amount = 1, kind = "ability", name_id = "ability_smoke"}
                },
            }
            _inst:update(human, 0)

            -- Capture texts (quantities-only)
            _eq_txt = _inst._equipment_text:text()
            _cb_txt = _inst._cables_text:text()
            _pj_txt = _inst._projectile_text:text()

            -- Capture icon visibility
            _di_vis = _inst._deployable_icon:visible()
            _ci_vis = _inst._cables_icon:visible()
            _pi_vis = _inst._projectile_icon:visible()

            -- DB probes
            _db_calls = _G._db_has_calls

            -- Certification
            _ok = _inst:verify()

            -- Verify Idstring is callable table
            _idstring_type = type(Idstring)
            _idstring_callable = pcall(function() Idstring("test") end)
        ''')
        g = lua.globals()

        # Idstring is callable table (engine reality)
        self.assertEqual(g._idstring_type, "table",
            "Idstring must be table type (engine callable table)")
        self.assertTrue(bool(g._idstring_callable),
            "callable table Idstring must be invocable")

        # Quantities-only texts
        self.assertEqual(g._eq_txt, "2",
            "deployable text must be quantity-only '2'")
        self.assertEqual(g._cb_txt, "0",
            "cables text must be quantity-only '0'")
        self.assertEqual(g._pj_txt, "1",
            "projectile text must be quantity-only '1'")

        # RED: icons should be visible but production rejects callable table Idstring
        self.assertTrue(bool(g._di_vis),
            "RED: deployable icon visible (callable table Idstring accepted)")
        self.assertTrue(bool(g._ci_vis),
            "RED: cables icon visible (callable table Idstring accepted)")
        self.assertTrue(bool(g._pi_vis),
            "RED: projectile icon visible (callable table Idstring accepted)")

        # DB probes positive
        self.assertGreater(int(g._db_calls), 0,
            "DB:has must be called (probes positive)")

        # Certification true
        self.assertTrue(bool(g._ok),
            "RED: verify() true with callable table Idstring")

    def test_bitmap_assignment_precedes_visibility(self):
        """Native boundary: hudteammate calls set_image BEFORE visible=true.
        Current crew_card calls set_visible(true) BEFORE set_image (unsafe exposure).

        Instrument bitmap metatable BEFORE crew consumer loads:
        - Count set_visible(true) when bitmap texture not assigned (unsafe exposure)
        - Count set_image on bitmap currently visible (redundant churn)
        - Count ALL set_image attempts externally (total, regardless of visibility)
        - set_image wrapper checks _G._fail_bitmap_assignment and errors BEFORE original

        Exercise scenarios:
        1. First update all 3 icons visible
        2. Repeated same update (no set_image calls at all desired)
        3. Resource id change same texture atlas (must rebind correct crop)
        4. Injected set_image exception via _fail_bitmap_assignment (all 3 must remain hidden)
        5. Restore and ordinary update positive same primitives certification
        6. Corruption recovery: externally mutate texture, update restores, verify true

        Track counts externally (no production fields injected).
        Assert first meaningful failure: unsafe exposure count zero (current crew_card exposes 3).
        """
        extension = '''
            local _unsafe_exposure_count = 0
            local _redundant_churn_count = 0
            local _total_set_image_attempts = 0

            local _mt = getmetatable(_G.panel_double)
            local _orig_bitmap = _mt.__index.bitmap
            local _panel_set_visible = _mt.__index.set_visible
            local _panel_set_image = _mt.__index.set_image
            _G._orig_set_image_backing = _panel_set_image

            _mt.__index.bitmap = function(self, cfg)
                local bm = _orig_bitmap(self, cfg)
                bm.set_visible = function(b, v)
                    if v == true and b._texture == nil then
                        _unsafe_exposure_count = _unsafe_exposure_count + 1
                    end
                    _panel_set_visible(b, v)
                end
                bm.set_image = function(b, tex, x, y, w, h)
                    _total_set_image_attempts = _total_set_image_attempts + 1
                    if _G._fail_bitmap_assignment then
                        error("injected bitmap assignment failure")
                    end
                    if b._visible then
                        _redundant_churn_count = _redundant_churn_count + 1
                    end
                    _panel_set_image(b, tex, x, y, w, h)
                end
                return bm
            end

            _G._unsafe_exposure_count = function() return _unsafe_exposure_count end
            _G._redundant_churn_count = function() return _redundant_churn_count end
            _G._total_set_image_attempts = function() return _total_set_image_attempts end
        '''

        lua, ok = _lua(setup=ICON_FIXTURE + extension)
        self.assertTrue(ok, "RED: crew_card.lua must exist")
        if not ok:
            return
        _setup_card(lua, "bitmap_order")

        lua.execute('''
            -- Save actual primitive refs BEFORE any update
            _ref_di0 = _inst._deployable_icon
            _ref_ci0 = _inst._cables_icon
            _ref_pi0 = _inst._projectile_icon

            -- Scenario 1: First update all 3 icons visible
            local human1 = {
                ''' + _HUMAN_201 + ''',
                equipment = {
                    deployable  = {id = "ammo_bag", amount = 2, name_id = "ammo_bag_name"},
                    cable_ties  = {amount = 0},
                    projectile  = {id = "smoke_screen_grenade", amount = 1, kind = "ability", name_id = "ability_smoke"}
                },
            }
            _inst:update(human1, 0)
            _unsafe1 = _G._unsafe_exposure_count()
            _churn1 = _G._redundant_churn_count()
            _total1 = _G._total_set_image_attempts()

            -- Scenario 2: Repeated same update (no set_image calls at all desired)
            _inst:update(human1, 1)
            _unsafe2 = _G._unsafe_exposure_count()
            _churn2 = _G._redundant_churn_count()
            _total2 = _G._total_set_image_attempts()

            -- Scenario 3: Resource id change while prior icons visible (same texture atlas, different crop)
            local human2 = {
                ''' + _HUMAN_201 + ''',
                equipment = {
                    deployable  = {id = "doctor_bag", amount = 1, name_id = "doctor_bag_name"},
                    cable_ties  = {amount = 5},
                    projectile  = {id = "frag_grenade", amount = 2, kind = "ability", name_id = "ability_frag"}
                },
            }
            _inst:update(human2, 2)
            _unsafe3 = _G._unsafe_exposure_count()
            _churn3 = _G._redundant_churn_count()
            _total3 = _G._total_set_image_attempts()
            -- Verify correct crop rebind for changed atlas region
            local r3di = _inst._deployable_icon._texture_rect
            _di_x3 = r3di and r3di[1] or -1
            local r3pi = _inst._projectile_icon._texture_rect
            _pi_x3 = r3pi and r3pi[1] or -1

            -- Scenario 4: Injected set_image exception via external flag (must remain hidden)
            _G._fail_bitmap_assignment = true
            local human3 = {
                ''' + _HUMAN_201 + ''',
                equipment = {
                    deployable  = {id = "ammo_bag", amount = 3, name_id = "ammo_bag_name"},
                    cable_ties  = {amount = 1},
                    projectile  = {id = "smoke_screen_grenade", amount = 2, kind = "ability", name_id = "ability_smoke"}
                },
            }
            _inst:update(human3, 3)
            _unsafe4 = _G._unsafe_exposure_count()
            _churn4 = _G._redundant_churn_count()
            _total4 = _G._total_set_image_attempts()
            _di_vis4 = _inst._deployable_icon and _inst._deployable_icon:visible()
            _ci_vis4 = _inst._cables_icon and _inst._cables_icon:visible()
            _pi_vis4 = _inst._projectile_icon and _inst._projectile_icon:visible()
            _G._fail_bitmap_assignment = nil

            -- Scenario 5: Restore and ordinary update positive same primitives certification
            _inst:update(human1, 4)
            _unsafe5 = _G._unsafe_exposure_count()
            _churn5 = _G._redundant_churn_count()
            _total5 = _G._total_set_image_attempts()
            _ok5 = _inst:verify()

            -- Corruption recovery: externally mutate texture via original backing setter
            _G._orig_set_image_backing(_inst._deployable_icon, "wrong/texture", 0, 0, 1, 1)
            _tex_corrupted = _inst._deployable_icon:texture_name()
            _unsafe_before_recover = _G._unsafe_exposure_count()
            _inst:update(human1, 5)
            _unsafe6 = _G._unsafe_exposure_count()
            _churn6 = _G._redundant_churn_count()
            _ok6 = _inst:verify()
            _tex_restored = _inst._deployable_icon:texture_name()
            _same_di_final = _inst._deployable_icon == _ref_di0
            _same_ci_final = _inst._cables_icon == _ref_ci0
            _same_pi_final = _inst._projectile_icon == _ref_pi0
        ''')
        g = lua.globals()

        # Native boundary: set_image BEFORE set_visible(true) -> zero unsafe exposure
        self.assertEqual(int(g._unsafe1), 0,
            "RED: first update must not expose visible bitmap without texture (native order: set_image before visible)")
        self.assertEqual(int(g._churn1), 0,
            "first update: no redundant set_image on already visible bitmaps")

        # Repeated update: no set_image calls at all (total unchanged)
        self.assertEqual(int(g._unsafe2), 0,
            "repeated update: no unsafe exposure")
        self.assertEqual(int(g._total2), int(g._total1),
            "repeated update: total set_image attempts unchanged (no churn even if implementation hides first)")

        # Resource id change: correct crop rebind, no unsafe exposure
        self.assertEqual(int(g._unsafe3), 0,
            "RED: resource id change must not expose visible bitmap without texture")
        self.assertEqual(float(g._di_x3), 32.0,
            "RED: resource id change must rebind correct crop (doctor_bag x=32)")
        self.assertEqual(float(g._pi_x3), 128.0,
            "RED: resource id change must rebind correct crop (frag x=128)")

        # Injected exception via flag: all 3 icons must remain hidden
        self.assertFalse(bool(g._di_vis4), "injected exception: deployable hidden")
        self.assertFalse(bool(g._ci_vis4), "injected exception: cables hidden")
        self.assertFalse(bool(g._pi_vis4), "injected exception: projectile hidden")
        self.assertEqual(int(g._unsafe4), 0,
            "injected exception: no unsafe exposure")

        # Restore: same primitives, verify true, no unsafe exposure
        self.assertEqual(int(g._unsafe5), 0,
            "restore: no unsafe exposure")
        self.assertTrue(bool(g._ok5), "restore: verify() true")

        # Corruption recovery: texture restored, verify true, no visible rebind
        self.assertEqual(g._tex_corrupted, "wrong/texture",
            "corruption: texture mutated externally")
        self.assertEqual(int(g._unsafe6), int(g._unsafe_before_recover),
            "corruption recovery: no visible rebind (unsafe count unchanged)")
        self.assertTrue(bool(g._ok6), "corruption recovery: verify() true")
        self.assertEqual(g._tex_restored, "guis/textures/pd2/equip_icons",
            "corruption recovery: texture restored to correct value")

        # Exact primitive identity: same objects as BEFORE scenario1
        self.assertTrue(bool(g._same_di_final), "final: exact same _deployable_icon ref as before scenario1")
        self.assertTrue(bool(g._same_ci_final), "final: exact same _cables_icon ref as before scenario1")
        self.assertTrue(bool(g._same_pi_final), "final: exact same _projectile_icon ref as before scenario1")

    def test_negative_hide_setter_noop_resource_transition(self):
        """Negative hide setter: override set_visible(false) as no-op while visible.
        Inject new resource transition, count image-on-visible must remain zero.
        Production must fail closed: card update fails with no set_image on still-visible bitmap.
        Restore setter and ordinary update recovers."""
        extension = '''
            local _image_on_visible_count = 0

            local _mt = getmetatable(_G.panel_double)
            local _orig_bitmap = _mt.__index.bitmap
            local _panel_set_visible = _mt.__index.set_visible
            local _panel_set_image = _mt.__index.set_image

            _mt.__index.bitmap = function(self, cfg)
                local bm = _orig_bitmap(self, cfg)
                local _hidden_set_visible = false
                local _local_orig_set_visible = function(b, v)
                    if _hidden_set_visible then
                        return
                    end
                    _panel_set_visible(b, v)
                end
                bm.set_visible = function(b, v)
                    _local_orig_set_visible(b, v)
                end
                bm.set_image = function(b, tex, x, y, w, h)
                    if b._visible then
                        _image_on_visible_count = _image_on_visible_count + 1
                    end
                    _panel_set_image(b, tex, x, y, w, h)
                end
                bm._disable_set_visible = function(b)
                    _hidden_set_visible = true
                end
                bm._restore_set_visible = function(b)
                    _hidden_set_visible = false
                end
                return bm
            end

            _G._image_on_visible_count = function() return _image_on_visible_count end
        '''

        lua, ok = _lua(setup=ICON_FIXTURE + extension)
        self.assertTrue(ok, "RED: crew_card.lua must exist")
        if not ok:
            return
        _setup_card(lua, "neg_hide")

        lua.execute('''
            local human1 = {
                ''' + _HUMAN_201 + ''',
                equipment = {
                    deployable  = {id = "ammo_bag", amount = 2, name_id = "ammo_bag_name"},
                    cable_ties  = {amount = 0},
                    projectile  = {id = "smoke_screen_grenade", amount = 1, kind = "ability", name_id = "ability_smoke"}
                },
            }
            _inst:update(human1, 0)
            _initial_vis = _inst._deployable_icon:visible()
            _initial_img_on_vis = _G._image_on_visible_count()

            _inst._deployable_icon:_disable_set_visible()
            _after_disable_vis = _inst._deployable_icon:visible()

            _inst._deployable_icon:set_visible(false)
            _after_noop_vis = _inst._deployable_icon:visible()

            local human2 = {
                ''' + _HUMAN_201 + ''',
                equipment = {
                    deployable  = {id = "doctor_bag", amount = 1, name_id = "doctor_bag_name"},
                    cable_ties  = {amount = 5},
                    projectile  = {id = "frag_grenade", amount = 3, kind = "ability", name_id = "ability_frag"}
                },
            }
            _G._ok_update = _inst:update(human2, 1)
            _after_transition_vis = _inst._deployable_icon:visible()
            _after_transition_img_on_vis = _G._image_on_visible_count()
            _tex_after_transition = _inst._deployable_icon:texture_name()

            _inst._deployable_icon:_restore_set_visible()
            _after_restore_vis = _inst._deployable_icon:visible()

            _inst:update(human1, 2)
            _after_recovery_vis = _inst._deployable_icon:visible()
            _after_recovery_img_on_vis = _G._image_on_visible_count()
            _tex_after_recovery = _inst._deployable_icon:texture_name()
            _ok_recovery = _inst:verify()
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._initial_vis), "initial: deployable visible")
        self.assertEqual(int(g._initial_img_on_vis), 0,
            "initial: no set_image on visible bitmap")

        self.assertTrue(bool(g._after_disable_vis), "after disable: still visible (no-op)")
        self.assertTrue(bool(g._after_noop_vis), "after set_visible(false): still visible (no-op)")

        self.assertTrue(bool(g._after_transition_vis),
            "after transition: bitmap still visible (setter disabled)")
        self.assertEqual(int(g._after_transition_img_on_vis), 0,
            "RED: transition must NOT call set_image on still-visible bitmap (closed card update)")
        self.assertFalse(bool(g._ok_update),
            "RED: card update must fail when set_visible is broken and bitmap stays visible")

        self.assertEqual(g._tex_after_transition, "guis/textures/pd2/equip_icons",
            "texture unchanged during failed transition")

        self.assertTrue(bool(g._after_recovery_vis),
            "after recovery: deployable visible again")
        self.assertEqual(g._tex_after_recovery, "guis/textures/pd2/equip_icons",
            "after recovery: correct texture restored")
        self.assertTrue(bool(g._ok_recovery),
            "after recovery: verify() true")


if __name__ == "__main__":
    unittest.main()
