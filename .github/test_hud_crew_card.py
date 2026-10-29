"""Crew Card -- hud/components/crew_card.lua: compact crew card renderer (RED tracer).

Three tests against lua/hud/components/crew_card.lua via real lupa.luajit21.

Interface under test:
  kyohud.hud.crew_card.new(parent, name) -> instance
    instance.root
    instance._name_text, instance._health_fill, instance._health_text,
    instance._armor_fill, instance._armor_text, instance._weapon_text,
    instance._equipment_text (deployable), instance._cables_text,
    instance._projectile_text, instance._interaction_text, instance._status_text
    :set_geometry(x, y, w, h)
    :update(actor, t)
    :verify()
    :destroy()

actor: crew snapshot entry from actors:get_crew_snapshot() format:
  {name, level, rank, ai, peer_id, character_name, slot, position,
   occupant_token, health={current,total,ratio,valid,provenance},
   armor={current,total,ratio,valid,provenance},
   weapon={selection_index,weapon_id,name_id,unit_id,
     ammo={max_clip,current_clip,total_raw,reserve,max,provenance}},
   equipment={deployable={id,amount,name_id},cable_ties={amount},
     projectile={id,amount,kind,name_id}},
   interaction={type_index,tweak_data_id,enabled,duration,started_t,success},
   downs=<number>, condition_text=<string>, condition_icon=<string>,
   condition_phase=<string>}

Render rules:
  name text: human -> "NAME L{level} R{rank}" or "NAME L{level}" when rank=0;
             bot -> character display name + " IA" (no level/rank, FR localization).
  health: percentage mode -> rounded(ratio*100).."%", "--" when invalid.
  armor: same; bot with no armor observation -> "--".
  weapon: "{name_id} {current_clip}/{reserve}" or "--" when missing.
   equipment (separate primitives):
     _equipment_text: "{deployable.name_id} x{amount}" or "--" none.
     _cables_text: "x{amount}" (zero is valid, not empty).
     _projectile_text: "{kind} charge{amount}" or "--" none.
  interaction: enabled+!success -> "{tweak_data_id} {progress}%"; success/!enabled/absent -> "".
  status: downs+condition_text, e.g. "0 normal" or "1 bleed_out"; "--" when downs nil or condition_text nil.

Primitive identity: update() must reuse the same text/fill references.
verify(): false after corrupting text/color/geometry; true after repair via update() ALONE.
destroy(): only kills own root; sibling and parent survive.
no-op setter: set_geometry with same values does not break verify.
dead subtree: methods on dead instance return/count gracefully without error.

RED: lua/hud/components/crew_card.lua does not exist yet. Tests that need it
fail with assertTrue(path.exists()), not FileNotFoundError.
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime
from test_hud_gauge import STUBS as _BASE_STUBS


ROOT = Path(__file__).resolve().parents[1]
CREW_CARD_PATH = ROOT / "lua" / "hud" / "components" / "crew_card.lua"

COLOR_AUGMENT = '''
-- Native Color fields (not methods); set_alpha/set_color semantics.
local _OrigColor = Color
Color = function(arg1, arg2, arg3, arg4)
    if arg4 == nil then
        -- 3 args: Color(r, g, b)
        return { r = arg1 or 0, g = arg2 or 0, b = arg3 or 0, a = 1 }
    else
        -- 4 args: Color(a, r, g, b)
        return { r = arg2 or 0, g = arg3 or 0, b = arg4 or 0, a = arg1 or 1 }
    end
end
local _mt = getmetatable(_G.panel_double)
function _mt.__index:color() return self._color end
function _mt.__index:alpha() return self._alpha or (self._color and self._color.a) or 1 end
function _mt.__index:font() return self._font or 'fonts/font_medium_mf' end
function _mt.__index:set_font(font) self._font=font end
function _mt.__index:text_rect()
    local n=0
    for byte in self:text():gmatch('.') do if byte:byte()<128 or byte:byte()>=192 then n=n+1 end end
    return 0,0,n*self:font_size()*.45,self:font_size()
end
function _mt.__index:set_alpha(a)
    if self._color then self._color.a = a
    else self._color = Color(a, 0, 0, 0) end
end
local _orig_set_color = _mt.__index.set_color
function _mt.__index:set_color(c)
    if _orig_set_color then _orig_set_color(self, c) end
    if c and c.a then self._color = Color(c.a, c.r, c.g, c.b)
    else self._color = c end
end
'''

STUBS = _BASE_STUBS + "\n" + COLOR_AUGMENT


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    src = _read(CREW_CARD_PATH)
    exists = src is not None
    if exists:
        lua.execute(src)
    return lua, exists


class CrewCardFileExistsTests(unittest.TestCase):
    def test_crew_card_chunk_exists(self):
        self.assertTrue(CREW_CARD_PATH.is_file(),
            "RED: lua/hud/components/crew_card.lua must exist")


class CrewCardThreeIndependentCards280x120Tests(unittest.TestCase):
    def test_three_independent_cards_human_bot_and_unknown(self):
        """Build 3 cards at 280x120: human with full data, bot with IA, unknown actor.

        Card 1 (human peer2): name "AlPhA L5", health 50%, armor 80%,
        weapon "wpn_a 7/60", equipment "ammo_bag_name x2", cables "x0",
        projectile "ability charge1", interaction "lockpick 50%", status "0 normal".
        Card 2 (bot): name "Dallas IA", health "--", armor "--", weapon "--",
        equipment "--", cables "", projectile "--", interaction "", status "0 normal".
        Card 3 (unknown/minimal): name "--", health "--", armor "--", weapon "--".
        Each card independent with own geometry and primitives.
        """
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            assert(CC and CC.new, "RED: kyohud.hud.crew_card.new must exist")

            local c1 = CC.new(parent, "card1")
            local c2 = CC.new(parent, "card2")
            local c3 = CC.new(parent, "card3")
            c1:set_geometry(0, 0, 280, 120)
            c2:set_geometry(290, 0, 280, 120)
            c3:set_geometry(580, 0, 280, 120)

            _c1_root_alive = alive(c1.root)
            _c2_root_alive = alive(c2.root)
            _c3_root_alive = alive(c3.root)

            _c1_rw = c1.root:w(); _c1_rh = c1.root:h()
            _c2_rw = c2.root:w(); _c2_rh = c2.root:h()
            _c3_rw = c3.root:w(); _c3_rh = c3.root:h()

            _c2_rx = c2.root:x()
            _c3_rx = c3.root:x()

            -- primitives exist
            _c1_nt = c1._name_text ~= nil
            _c1_hf = c1._health_fill ~= nil
            _c1_ht = c1._health_text ~= nil
            _c1_af = c1._armor_fill ~= nil
            _c1_at = c1._armor_text ~= nil
            _c1_wt = c1._weapon_text ~= nil
            _c1_et = c1._equipment_text ~= nil
            _c1_ct = c1._cables_text ~= nil
            _c1_pt = c1._projectile_text ~= nil
            _c1_it = c1._interaction_text ~= nil
            _c1_st = c1._status_text ~= nil

            -- Human actor with full data, network_quantized provenance
            local human = {
                name = "AlPhA", level = 5, rank = 0, ai = false,
                peer_id = 2, character_name = "spanish",
                health = {current = 50, total = 100, ratio = 0.5, valid = true, provenance = "network_quantized"},
                armor = {current = 4, total = 5, ratio = 0.8, valid = true, provenance = "network_quantized"},
                weapon = {
                    selection_index = 1, weapon_id = "gun_a", name_id = "wpn_a",
                    ammo = {max_clip = 30, current_clip = 7, total_raw = 67, reserve = 60, max = 120, provenance = "network_synced"}
                },
                equipment = {
                    deployable = {id = "ammo_bag", amount = 2, name_id = "ammo_bag_name"},
                    cable_ties = {amount = 0},
                    projectile = {id = "smoke_screen_grenade", amount = 1, kind = "ability", name_id = "ability_smoke"}
                },
                interaction = {
                    type_index = 1, tweak_data_id = "lockpick", enabled = true,
                    duration = 10, started_t = 1, success = nil
                },
                downs = 0, condition_text = "normal",
                condition_icon = nil, condition_phase = nil
            }

            -- Bot actor: no level/rank, no armor, no weapon, no equipment, no interaction, no downs
            local bot = {
                name = "Dallas", level = nil, rank = nil, ai = true,
                peer_id = nil, character_name = "russian",
                health = nil, armor = nil, weapon = nil, equipment = nil, interaction = nil,
                downs = nil, condition_text = nil, condition_icon = nil, condition_phase = nil
            }

            -- Minimal actor: only name
            local minimal = {
                name = nil, level = nil, rank = nil, ai = nil,
                peer_id = nil, character_name = nil,
                health = nil, armor = nil, weapon = nil, equipment = nil, interaction = nil,
                downs = nil, condition_text = nil, condition_icon = nil, condition_phase = nil
            }

            c1:update(human, 6)
            c2:update(bot, 6)
            c3:update(minimal, 6)

            _c1_name = c1._name_text:text()
            _c1_hp = c1._health_text:text()
            _c1_ar = c1._armor_text:text()
            _c1_wp = c1._weapon_text:text()
            _c1_eq = c1._equipment_text:text()
            _c1_ct_text = c1._cables_text:text()
            _c1_pt_text = c1._projectile_text:text()
            _c1_int = c1._interaction_text:text()
            _c1_status = c1._status_text:text()

            _c2_name = c2._name_text:text()
            _c2_hp = c2._health_text:text()
            _c2_ar = c2._armor_text:text()
            _c2_wp = c2._weapon_text:text()
            _c2_eq = c2._equipment_text:text()
            _c2_ct_text = c2._cables_text:text()
            _c2_pt_text = c2._projectile_text:text()
            _c2_int = c2._interaction_text:text()
            _c2_status = c2._status_text:text()

            _c3_name = c3._name_text:text()
            _c3_hp = c3._health_text:text()
            _c3_ar = c3._armor_text:text()
            _c3_wp = c3._weapon_text:text()

            -- Native callsign color fields
            local nc = c1._name_text:color()
            _c1_nc_r = nc.r
            _c1_nc_g = nc.g
            _c1_nc_b = nc.b
        ''')
        g = lua.globals()

        self.assertTrue(bool(g._c1_root_alive), "card1 root must be alive")
        self.assertTrue(bool(g._c2_root_alive), "card2 root must be alive")
        self.assertTrue(bool(g._c3_root_alive), "card3 root must be alive")

        self.assertEqual(float(g._c1_rw), 280.0)
        self.assertEqual(float(g._c1_rh), 120.0)
        self.assertEqual(float(g._c2_rw), 280.0)
        self.assertEqual(float(g._c2_rh), 120.0)
        self.assertEqual(float(g._c3_rw), 280.0)
        self.assertEqual(float(g._c3_rh), 120.0)
        self.assertEqual(float(g._c2_rx), 290.0)
        self.assertEqual(float(g._c3_rx), 580.0)

        for attr in ("_c1_nt", "_c1_hf", "_c1_ht", "_c1_af", "_c1_at",
                      "_c1_wt", "_c1_et", "_c1_ct", "_c1_pt", "_c1_it", "_c1_st"):
            self.assertTrue(bool(g[attr]),
                f"card1 primitive {attr} must exist")

        self.assertEqual(g._c1_name, "AlPhA L5",
            "human rank=0 -> 'NAME L{level}' (no rank suffix)")
        self.assertEqual(g._c1_hp, "50%")
        self.assertEqual(g._c1_ar, "80%")
        self.assertEqual(g._c1_wp, "wpn_a 7/60")
        self.assertEqual(g._c1_eq, "ammo_bag_name x2",
            "equipment_text shows deployable")
        self.assertEqual(g._c1_ct_text, "x0",
            "cables_text x0 when amount=0 (zero is valid)")
        self.assertEqual(g._c1_pt_text, "ability charge1",
            "projectile_text shows kind+amount")
        self.assertEqual(g._c1_int, "lockpick 50%")
        self.assertEqual(g._c1_status, "0 normal",
            "status_text shows downs+condition")

        self.assertIn(g._c2_name, ("Dallas IA", "Dallas AI"),
            "bot -> display name + ' IA' (FR) or 'AI' (EN)")
        self.assertEqual(g._c2_hp, "--",
            "bot health nil -> '--'")
        self.assertEqual(g._c2_ar, "--",
            "bot armor nil -> '--' (no fake bot armor)")
        self.assertEqual(g._c2_wp, "--",
            "bot weapon nil -> '--'")
        self.assertEqual(g._c2_eq, "--",
            "bot equipment nil -> '--' (no fake bot equipment)")
        self.assertEqual(g._c2_ct_text, "",
            "bot cables nil -> ''")
        self.assertEqual(g._c2_pt_text, "--",
            "bot projectile nil -> '--'")
        self.assertEqual(g._c2_int, "",
            "bot interaction nil -> '' (no fake bot interaction)")
        self.assertEqual(g._c2_status, "--",
            "bot status unknown (nil downs/condition) -> '--'")

        self.assertEqual(g._c3_name, "--",
            "minimal actor name nil -> '--'")
        self.assertEqual(g._c3_hp, "--",
            "minimal health nil -> '--'")
        self.assertEqual(g._c3_ar, "--",
            "minimal armor nil -> '--'")
        self.assertEqual(g._c3_wp, "--",
            "minimal weapon nil -> '--'")

        # Native callsign color: numeric fields .r/.g/.b (not methods)
        self.assertIsNotNone(g._c1_nc_r, "callsign color .r must exist")
        self.assertIsNotNone(g._c1_nc_g, "callsign color .g must exist")
        self.assertIsNotNone(g._c1_nc_b, "callsign color .b must exist")
        self.assertIsInstance(float(g._c1_nc_r), float,
            "callsign color .r must be numeric")
        self.assertIsInstance(float(g._c1_nc_g), float,
            "callsign color .g must be numeric")
        self.assertIsInstance(float(g._c1_nc_b), float,
            "callsign color .b must be numeric")


class CrewCardStabilityAndRepairTests(unittest.TestCase):
    def test_primitive_identity_corrupt_and_repair(self):
        """Repeated update preserves primitive identity; corrupt text/color/geometry
        then verify false; ordinary update ALONE repairs same primitives (no manual set_geometry)."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            local inst = CC.new(parent, "stab")
            inst:set_geometry(0, 0, 280, 120)

            local actor = {
                name = "Test", level = 10, rank = 3, ai = false, peer_id = 5,
                health = {current = 75, total = 100, ratio = 0.75, valid = true, provenance = "network_quantized"},
                armor = {current = 2, total = 5, ratio = 0.4, valid = true, provenance = "network_quantized"},
                weapon = {name_id = "wpn_test",
                    ammo = {current_clip = 12, reserve = 48, provenance = "network_synced"}},
                equipment = {deployable = {id = "doc", amount = 1, name_id = "doc_name"},
                    cable_ties = {amount = 0}, projectile = {id = "smoke", amount = 1, kind = "ability", name_id = "smoke_name"}},
                interaction = {type_index = 2, tweak_data_id = "ammo_bag",
                    enabled = true, duration = 5, started_t = 3, success = nil},
                downs = 1, condition_text = "bleed_out",
                condition_icon = nil, condition_phase = nil
            }

            inst:update(actor, 5)
            _ok_clean = inst:verify()

            local ref_name = inst._name_text
            local ref_hf = inst._health_fill
            local ref_ht = inst._health_text
            local ref_af = inst._armor_fill
            local ref_at = inst._armor_text
            local ref_wt = inst._weapon_text
            local ref_et = inst._equipment_text
            local ref_ct = inst._cables_text
            local ref_pt = inst._projectile_text
            local ref_it = inst._interaction_text
            local ref_st = inst._status_text

            for _ = 1, 10 do
                inst:update(actor, 5)
            end
            _same_after_repeat = (inst._name_text == ref_name) and
                (inst._health_fill == ref_hf) and
                (inst._health_text == ref_ht) and
                (inst._armor_fill == ref_af) and
                (inst._armor_text == ref_at) and
                (inst._weapon_text == ref_wt) and
                (inst._equipment_text == ref_et) and
                (inst._cables_text == ref_ct) and
                (inst._projectile_text == ref_pt) and
                (inst._interaction_text == ref_it) and
                (inst._status_text == ref_st)

            -- corrupt name text
            if inst._name_text then
                inst._name_text:set_text("CORRUPTED")
            end
            _ok_bad_name = inst:verify()

            -- repair by update ALONE
            inst:update(actor, 5)
            _ok_name_restored = inst:verify()
            _same_after_name_repair = (inst._name_text == ref_name)
            _repaired_name = inst._name_text:text()

            -- corrupt health fill geometry
            if inst._health_fill then
                inst._health_fill:set_shape(-1, -1, -1, -1)
            end
            _ok_bad_fill = inst:verify()

            -- repair by update ALONE
            inst:update(actor, 5)
            _ok_fill_restored = inst:verify()
            _same_after_fill_repair = (inst._health_fill == ref_hf)

            -- corrupt health text
            if inst._health_text then
                inst._health_text:set_text("WRONG")
            end
            _ok_bad_ht = inst:verify()

            -- repair by update ALONE
            inst:update(actor, 5)
            _ok_ht_restored = inst:verify()
            _same_after_ht_repair = (inst._health_text == ref_ht)
            _repaired_hp = inst._health_text:text()

            -- corrupt root geometry
            if inst.root then
                inst.root:set_shape(999, 999, 1, 1)
            end
            _ok_bad_geom = inst:verify()

            -- repair by update ALONE (no manual set_geometry)
            inst:update(actor, 5)
            _ok_geom_restored = inst:verify()
            _geom_x = inst.root:x()
            _geom_w = inst.root:w()

            -- corrupt color on name text
            if inst._name_text then
                inst._name_text:set_color(Color(0, 0, 0))
            end
            _ok_bad_color = inst:verify()

            -- repair by update ALONE
            inst:update(actor, 5)
            _ok_color_restored = inst:verify()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._ok_clean),
            "verify() must be true on a healthy crew card")
        self.assertTrue(bool(g._same_after_repeat),
            "repeated update must reuse same primitive references")
        self.assertFalse(bool(g._ok_bad_name),
            "verify() must be false after corrupting name text")
        self.assertTrue(bool(g._ok_name_restored),
            "verify() must be true after update repairs name text")
        self.assertTrue(bool(g._same_after_name_repair),
            "update must repair using same name_text reference")
        self.assertEqual(g._repaired_name, "Test L10 R3",
            "repaired name text must show 'Test L10 R3'")
        self.assertFalse(bool(g._ok_bad_fill),
            "verify() must be false after corrupting health fill geometry")
        self.assertTrue(bool(g._ok_fill_restored),
            "verify() must be true after update repairs health fill")
        self.assertTrue(bool(g._same_after_fill_repair),
            "update must repair using same health_fill reference")
        self.assertFalse(bool(g._ok_bad_ht),
            "verify() must be false after corrupting health text")
        self.assertTrue(bool(g._ok_ht_restored),
            "verify() must be true after update repairs health text")
        self.assertTrue(bool(g._same_after_ht_repair),
            "update must repair using same health_text reference")
        self.assertEqual(g._repaired_hp, "75%")
        self.assertFalse(bool(g._ok_bad_geom),
            "verify() must be false after corrupting root geometry")
        self.assertTrue(bool(g._ok_geom_restored),
            "verify() must be true after update ALONE restores geometry")
        self.assertAlmostEqual(float(g._geom_x), 0.0, places=3,
            msg="update must restore root x to 0")
        self.assertAlmostEqual(float(g._geom_w), 280.0, places=3,
            msg="update must restore root w to 280")
        self.assertFalse(bool(g._ok_bad_color),
            "verify() must be false after corrupting name text color")
        self.assertTrue(bool(g._ok_color_restored),
            "verify() must be true after update restores color")


class CrewCardDestroyAndNoOpTests(unittest.TestCase):
    def test_destroy_only_own_root_sibling_and_parent_survive(self):
        """destroy() kills only own root; sibling and parent survive.
        Engine-dead root: calling destroy on dead root must not error.
        No-op setter (set_geometry with same values) does not break verify.
        Dead subtree: methods on destroyed instance return/count gracefully."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            local inst = CC.new(parent, "d1")
            inst:set_geometry(0, 0, 280, 120)

            local actor = {
                name = "X", level = 1, rank = 0, ai = false,
                health = {current = 50, total = 100, ratio = 0.5, valid = true, provenance = "network_quantized"},
                armor = {current = 1, total = 5, ratio = 0.2, valid = true, provenance = "network_quantized"},
                downs = 0, condition_text = "normal",
                condition_icon = nil, condition_phase = nil
            }
            inst:update(actor, 0)
            _ok_before = inst:verify()

            -- sibling panel
            local sibling = parent:panel({name = "sibling_crew_card_test"})
            local own_root = inst.root
            inst:destroy()
            _own_alive = alive(own_root)
            _sibling_alive = alive(sibling)
            _parent_alive = alive(parent)

            -- engine-dead root: destroy on nil root must not error
            _dead_destroy_ok = pcall(function() inst:destroy() end)

            -- no-op setter: same geometry must not break verify
            local inst2 = CC.new(parent, "d2")
            inst2:set_geometry(10, 20, 280, 120)
            inst2:update(actor, 0)
            _ok2_before = inst2:verify()
            inst2:set_geometry(10, 20, 280, 120)
            _ok2_noop = inst2:verify()
            inst2:destroy()

            -- dead subtree: methods on destroyed instance
            local inst3 = CC.new(parent, "d3")
            inst3:set_geometry(0, 0, 280, 120)
            inst3:update(actor, 0)
            inst3:destroy()
            -- attempt methods on dead root
            _dead_set_geom_ok = pcall(function() inst3:set_geometry(0, 0, 280, 120) end)
            _dead_update_ok = pcall(function() inst3:update(actor, 0) end)
            _dead_verify_ok = pcall(function() inst3:verify() end)
            _dead_methods_called = 0
            if _dead_set_geom_ok then _dead_methods_called = _dead_methods_called + 1 end
            if _dead_update_ok then _dead_methods_called = _dead_methods_called + 1 end
            if _dead_verify_ok then _dead_methods_called = _dead_methods_called + 1 end
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._ok_before),
            "verify() must be true before destroy")
        self.assertFalse(bool(g._own_alive),
            "destroy() must kill the crew card's own root panel")
        self.assertTrue(bool(g._sibling_alive),
            "destroy() must NOT destroy the sibling panel")
        self.assertTrue(bool(g._parent_alive),
            "destroy() must NOT destroy the parent panel")
        self.assertTrue(bool(g._dead_destroy_ok),
            "destroy() on engine-dead root must not error")
        self.assertTrue(bool(g._ok2_before),
            "second instance verify() must be true")
        self.assertTrue(bool(g._ok2_noop),
            "no-op set_geometry (same values) must not break verify()")
        self.assertTrue(bool(g._dead_set_geom_ok),
            "set_geometry on dead instance must not error")
        self.assertTrue(bool(g._dead_update_ok),
            "update on dead instance must not error")
        self.assertTrue(bool(g._dead_verify_ok),
            "verify on dead instance must not error")
        self.assertGreaterEqual(int(g._dead_methods_called), 0,
            "dead subtree methods must return gracefully")


class CrewCardTransitionZeroAndBleedoutTests(unittest.TestCase):
    def test_zero_ammo_deployable_cables_projectile_and_bleedout_without_health(self):
        """Transition test: zero values render correctly, bleedout phase visible without health,
        downs/condition independent, localization resolves name_id to actual name."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/crew_card.lua must exist")
        if not ok:
            return
        lua.execute('''
            -- Add managers.localization mock for this test
            managers = managers or {}
            managers.localization = managers.localization or {}
            function managers.localization:text(key)
                if key == "menu_russian" then return "Dallas"
                elseif key == "menu_american" then return "Hoxton"
                elseif key == "menu_german" then return "Wolf"
                elseif key == "menu_spanish" then return "Chains"
                elseif key == "ammo_bag_name" then return "Ammo"
                elseif key == "ky_hud_crew_ai" then return "IA"
                else return "Loc:" .. tostring(key) end
            end

            local parent = _G.panel_double
            local CC = kyohud.hud.crew_card
            local inst = CC.new(parent, "transition")
            inst:set_geometry(0, 0, 280, 120)

            -- Human with zero/nil values
            local human_zero = {
                name = "Test", level = 1, rank = 0, ai = false,
                peer_id = 1, character_name = "test_char",
                health = {current = 50, total = 100, ratio = 0.5, valid = true, provenance = "network_quantized"},
                armor = {current = 1, total = 5, ratio = 0.2, valid = true, provenance = "network_quantized"},
                weapon = {
                    selection_index = 1, weapon_id = "gun_test", name_id = "wpn_test",
                    ammo = {max_clip = 30, current_clip = 7, total_raw = nil, reserve = nil, max = 120, provenance = "network_synced"}
                },
                equipment = {
                    deployable = {id = "ammo_bag", amount = 0, name_id = "ammo_bag_name"},
                    cable_ties = {amount = 0},
                    projectile = {id = "smoke", amount = 0, kind = "charge", name_id = "smoke_name"}
                },
                interaction = nil,
                downs = 0, condition_text = "normal",
                condition_icon = nil, condition_phase = nil
            }

            inst:update(human_zero, 0)
            _wp_text = inst._weapon_text:text()
            _eq_text = inst._equipment_text:text()
            _ct_text = inst._cables_text:text()
            _pt_text = inst._projectile_text:text()

            -- Bot with bleedout phase but no health
            local bot_bleedout = {
                name = nil, level = nil, rank = nil, ai = true,
                peer_id = nil, character_name = "russian",
                health = nil, armor = nil, weapon = nil, equipment = nil, interaction = nil,
                downs = 1, condition_text = nil, condition_icon = nil, phase = "bleedout"
            }

            inst:update(bot_bleedout, 1)
            _bot_name = inst._name_text:text()
            _bot_hp = inst._health_text:text()
            _bot_status = inst._status_text:text()

            -- Bot with downs but no condition
            local bot_downs_only = {
                name = nil, level = nil, rank = nil, ai = true,
                peer_id = nil, character_name = "american",
                health = nil, armor = nil, weapon = nil, equipment = nil, interaction = nil,
                downs = 2, condition_text = nil, condition_icon = nil, condition_phase = nil
            }

            inst:update(bot_downs_only, 2)
            _bot_downs_name = inst._name_text:text()
            _bot_downs_status = inst._status_text:text()

            -- Bot with condition but no downs
            local bot_condition_only = {
                name = nil, level = nil, rank = nil, ai = true,
                peer_id = nil, character_name = "german",
                health = nil, armor = nil, weapon = nil, equipment = nil, interaction = nil,
                downs = nil, condition_text = "bleed_out", condition_icon = nil, condition_phase = nil
            }

            inst:update(bot_condition_only, 3)
            _bot_cond_name = inst._name_text:text()
            _bot_cond_status = inst._status_text:text()

            inst:destroy()
        ''')
        g = lua.globals()

        # Weapon: clip=7, reserve=nil -> "7/--" NOT "7/0"
        self.assertIn("7/--", g._wp_text,
            "weapon with clip=7 and reserve=nil must show '7/--' not '7/0'")
        self.assertNotIn("7/0", g._wp_text,
            "weapon must NOT show '7/0' when reserve is nil")

        # Deployable: amount=0 -> "x0" NOT "--"
        self.assertEqual(g._eq_text, "Ammo x0",
            "deployable with amount=0 must show 'x0' not '--'")

        # Cable ties: amount=0 -> "x0" (strengthened zero contract)
        self.assertEqual(g._ct_text, "x0",
            "cable ties with amount=0 must show 'x0' (zero is valid)")

        # Projectile: amount=0 -> "charge0" NOT "--"
        self.assertEqual(g._pt_text, "charge charge0",
            "projectile with amount=0 must show 'charge0' not '--'")

        # Bot localization: name resolved via managers.localization:text(name_id)
        self.assertIn("Dallas", g._bot_name,
            "bot name must be resolved via managers.localization:text('menu_russian')")
        self.assertNotEqual(g._bot_name, "russian",
            "bot name must NOT be raw character_name token")

        # Bot bleedout phase without health -> condition visible, not fake normal
        self.assertEqual(g._bot_hp, "--",
            "bot with health=nil must show '--'")
        self.assertNotEqual(g._bot_status, "--",
            "bot with bleedout phase must NOT show '--' for status")
        self.assertIn("bleed", g._bot_status.lower(),
            "bot with condition_phase=bleedout must show bleedout in status")
        self.assertNotIn("normal", g._bot_status.lower(),
            "bot with bleedout phase must NOT show fake 'normal'")

        # Downs independently tracked despite condition unknown
        self.assertIn("Hoxton", g._bot_downs_name,
            "bot name resolved via managers.localization:text('menu_american')")
        self.assertIn("2", g._bot_downs_status,
            "bot with downs=2 and no condition must still show downs count")

        # Condition independently tracked despite downs unknown
        self.assertIn("Wolf", g._bot_cond_name,
            "bot name resolved via managers.localization:text('menu_german')")
        self.assertIn("bleed", g._bot_cond_status.lower(),
            "bot with condition_text and no downs must still show condition")


if __name__ == "__main__":
    unittest.main()
