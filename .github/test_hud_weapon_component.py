"""Weapon Component -- hud/components/weapon.lua: weapon slot renderer.

Three tests against lua/hud/components/weapon.lua via real lupa.luajit21.

Interface under test:
  kyohud.hud.weapon_component.new(parent, name) -> instance
    instance._root, instance._name_text, instance._ammo_text, instance._mode_text
    :layout(x, y, w, h)
    :render(slot_snapshot, selected, texts)
    :verify()
    :destroy()

slot_snapshot: {current_clip=number|nil, reserve=number|nil, fire_mode=string}
  fire_mode: "single" | "auto" | "burst" | "volley" | nil
  alt fire: slot_snapshot.alt_fire=true appends " ALT" to mode text

texts: {name="SHOTGUN", single="SINGLE", auto="AUTO", burst="BURST", volley="VOLLEY", alt="ALT"}

Render rules:
  ammo text: "current_clip / reserve" e.g. "6 / 26"
  unknown current_clip -> "-- / 26"; unknown reserve -> "6 / --" (per-side)
  zero current_clip -> "0 / 26" (zero is a valid number, not unknown)
  mode text: fire_mode mapped to texts[fire_mode], " ALT" appended if alt_fire=true
  name text: texts.name

RED: lua/hud/components/weapon.lua does not exist yet. Tests that need it
fail with assertTrue(path.exists()), not FileNotFoundError.
"""
from pathlib import Path
import unittest

from lupa.luajit21 import LuaRuntime
from test_hud_gauge import STUBS


ROOT = Path(__file__).resolve().parents[1]
WEAPON_PATH = ROOT / "lua" / "hud" / "components" / "weapon.lua"


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


def _lua():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    weapon_src = _read(WEAPON_PATH)
    exists = weapon_src is not None
    if exists:
        lua.execute(weapon_src)
    return lua, exists


class WeaponFileExistsTests(unittest.TestCase):
    def test_weapon_chunk_exists(self):
        self.assertTrue(WEAPON_PATH.is_file(),
            "RED: lua/hud/components/weapon.lua must exist")


class WeaponRealContentAndGeometryTests(unittest.TestCase):
    def test_real_content_and_disjoint_text_geometry_360x64(self):
        """Render real ammo/mode/name; three text primitives occupy disjoint geometry."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/weapon.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local WC = kyohud.hud.weapon_component
            assert(WC and WC.new, "RED: kyohud.hud.weapon_component.new must exist")
            local inst = WC.new(parent, "w1")
            inst:layout(0, 0, 360, 64)

            local texts = {
                name = "SHOTGUN",
                single = "SINGLE",
                auto = "AUTO",
                burst = "BURST",
                volley = "VOLLEY",
                alt = "ALT"
            }
            local snap = {current_clip = 6, reserve = 26, fire_mode = "auto"}
            inst:render(snap, true, texts)

            _name_text = inst._name_text:text()
            _ammo_text = inst._ammo_text:text()
            _mode_text = inst._mode_text:text()

            _nx = inst._name_text:x(); _ny = inst._name_text:y()
            _ax = inst._ammo_text:x(); _ay = inst._ammo_text:y()
            _mx = inst._mode_text:x(); _my = inst._mode_text:y()

            _nw = inst._name_text:w(); _nh = inst._name_text:h()
            _aw = inst._ammo_text:w(); _ah = inst._ammo_text:h()
            _mw = inst._mode_text:w(); _mh = inst._mode_text:h()
        ''')
        g = lua.globals()
        self.assertEqual(g._name_text, "SHOTGUN")
        self.assertEqual(g._ammo_text, "6 / 26")
        self.assertEqual(g._mode_text, "AUTO")

        def rect_disjoint(ax, ay, aw, ah, bx, by, bw, bh):
            return (ax + aw <= bx or bx + bw <= ax or
                    ay + ah <= by or by + bh <= ay)

        name_r = (float(g._nx), float(g._ny), float(g._nw), float(g._nh))
        ammo_r = (float(g._ax), float(g._ay), float(g._aw), float(g._ah))
        mode_r = (float(g._mx), float(g._my), float(g._mw), float(g._mh))
        self.assertTrue(rect_disjoint(*name_r, *ammo_r),
            f"name and ammo text overlap: name={name_r} ammo={ammo_r}")
        self.assertTrue(rect_disjoint(*name_r, *mode_r),
            f"name and mode text overlap: name={name_r} mode={mode_r}")
        self.assertTrue(rect_disjoint(*ammo_r, *mode_r),
            f"ammo and mode text overlap: ammo={ammo_r} mode={mode_r}")


class WeaponIndependenceAndStabilityTests(unittest.TestCase):
    def test_two_independent_instances_and_primitive_identity(self):
        """Two instances hold distinct state; repeated render+swap+layout A-B-A
        preserves primitive identity; zero current_clip -> '0 / 26'; unknown per-side."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/weapon.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local a = kyohud.hud.weapon_component.new(parent, "wa")
            local b = kyohud.hud.weapon_component.new(parent, "wb")
            a:layout(0, 0, 200, 40)
            b:layout(0, 0, 300, 60)
            _aw = a._root:w(); _bw = b._root:w()

            local texts_a = {
                name = "PISTOL", single = "SINGLE", auto = "AUTO",
                burst = "BURST", volley = "VOLLEY", alt = "ALT"
            }
            local texts_b = {
                name = "RIFLE", single = "SINGLE", auto = "AUTO",
                burst = "BURST", volley = "VOLLEY", alt = "ALT"
            }
            local snap_a = {current_clip = 12, reserve = 48, fire_mode = "single"}
            local snap_b = {current_clip = 30, reserve = 90, fire_mode = "auto", alt_fire = true}
            a:render(snap_a, true, texts_a)
            b:render(snap_b, true, texts_b)
            _a_ammo = a._ammo_text:text()
            _b_ammo = b._ammo_text:text()
            _a_mode = a._mode_text:text()
            _b_mode = b._mode_text:text()

            -- primitive identity: capture the actual text primitive references
            local id_name_a = a._name_text
            local id_ammo_a = a._ammo_text
            local id_mode_a = a._mode_text

            -- repeated render must reuse same primitives
            for _ = 1, 10 do
                a:render(snap_a, true, texts_a)
            end
            _same_after_repeat = (a._name_text == id_name_a) and
                                 (a._ammo_text == id_ammo_a) and
                                 (a._mode_text == id_mode_a)

            -- swap content
            local snap_swap = {current_clip = 99, reserve = 199, fire_mode = "burst"}
            a:render(snap_swap, true, texts_a)
            _same_after_swap = (a._name_text == id_name_a) and
                               (a._ammo_text == id_ammo_a) and
                               (a._mode_text == id_mode_a)
            _swapped_ammo = a._ammo_text:text()
            _swapped_mode = a._mode_text:text()

            -- layout A-B-A
            a:layout(1, 2, 101, 33)
            a:layout(500, 600, 999, 88)
            a:layout(1, 2, 101, 33)
            _aba_x = a._root:x(); _aba_y = a._root:y()
            _aba_w = a._root:w(); _aba_h = a._root:h()
            _same_after_layout = (a._name_text == id_name_a) and
                                 (a._ammo_text == id_ammo_a) and
                                 (a._mode_text == id_mode_a)

            -- zero current_clip -> "0 / 26" (zero is valid, not unknown)
            local snap_zero = {current_clip = 0, reserve = 26, fire_mode = "single"}
            a:render(snap_zero, true, texts_a)
            _zero_ammo = a._ammo_text:text()

            -- unknown (nil reserve) -> "6 / --" (per-side)
            local snap_unknown = {current_clip = 6, reserve = nil, fire_mode = "single"}
            a:render(snap_unknown, true, texts_a)
            _unknown_ammo = a._ammo_text:text()

            -- unknown (nil current_clip) -> "-- / 26" (per-side)
            local snap_unknown2 = {current_clip = nil, reserve = 26, fire_mode = "single"}
            a:render(snap_unknown2, true, texts_a)
            _unknown_ammo2 = a._ammo_text:text()
        ''')
        g = lua.globals()
        self.assertEqual(float(g._aw), 200.0)
        self.assertEqual(float(g._bw), 300.0)
        self.assertEqual(g._a_ammo, "12 / 48")
        self.assertEqual(g._b_ammo, "30 / 90")
        self.assertEqual(g._a_mode, "SINGLE")
        self.assertEqual(g._b_mode, "AUTO ALT",
            "alt_fire=true must append ' ALT' to mode text")
        self.assertTrue(bool(g._same_after_repeat),
            "repeated render must reuse same primitive references")
        self.assertTrue(bool(g._same_after_swap),
            "swapped render must reuse same primitive references")
        self.assertEqual(g._swapped_ammo, "99 / 199")
        self.assertEqual(g._swapped_mode, "BURST")
        self.assertEqual(float(g._aba_x), 1.0)
        self.assertEqual(float(g._aba_y), 2.0)
        self.assertEqual(float(g._aba_w), 101.0)
        self.assertEqual(float(g._aba_h), 33.0)
        self.assertTrue(bool(g._same_after_layout),
            "layout A-B-A must reuse same primitive references")
        self.assertEqual(g._zero_ammo, "0 / 26",
            "zero current_clip must render as '0 / 26', not '--'")
        self.assertEqual(g._unknown_ammo, "6 / --",
            "nil reserve must render as '6 / --'")
        self.assertEqual(g._unknown_ammo2, "-- / 26",
            "nil current_clip must render as '-- / 26'")


class WeaponVerifyAndDestroyTests(unittest.TestCase):
    def test_verify_corrupt_text_then_repair_and_destroy_leaves_sibling(self):
        """verify() false after corrupting text primitives; render repairs same primitives;
        destroy() kills only own root, sibling and parent survive."""
        lua, ok = _lua()
        self.assertTrue(ok, "RED: lua/hud/components/weapon.lua must exist")
        if not ok:
            return
        lua.execute('''
            local parent = _G.panel_double
            local inst = kyohud.hud.weapon_component.new(parent, "wv")
            inst:layout(0, 0, 200, 40)

            local texts = {
                name = "SHOTGUN", single = "SINGLE", auto = "AUTO",
                burst = "BURST", volley = "VOLLEY", alt = "ALT"
            }
            local snap = {current_clip = 6, reserve = 26, fire_mode = "auto"}
            inst:render(snap, true, texts)
            _ok_clean = inst:verify()

            -- capture primitive refs
            local ref_name = inst._name_text
            local ref_ammo = inst._ammo_text
            local ref_mode = inst._mode_text

            -- corrupt ammo text
            if inst._ammo_text then
                inst._ammo_text:set_text("CORRUPTED")
            end
            _ok_bad_ammo = inst:verify()

            -- repair
            inst:render(snap, true, texts)
            _ok_ammo_restored = inst:verify()
            _same_after_repair = (inst._name_text == ref_name) and
                                 (inst._ammo_text == ref_ammo) and
                                 (inst._mode_text == ref_mode)
            _repaired_ammo = inst._ammo_text:text()

            -- corrupt mode text
            if inst._mode_text then
                inst._mode_text:set_text("WRONG")
            end
            _ok_bad_mode = inst:verify()

            -- repair
            inst:render(snap, true, texts)
            _ok_mode_restored = inst:verify()

            -- destroy leaves sibling
            local sibling = parent:panel({name = "sibling_weapon_test"})
            local own_root = inst._root
            inst:destroy()
            _own_alive = alive(own_root)
            _sibling_alive = alive(sibling)
            _parent_alive = alive(parent)
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._ok_clean),
            "verify() must be true on a healthy weapon component")
        self.assertFalse(bool(g._ok_bad_ammo),
            "verify() must be false after corrupting ammo text")
        self.assertTrue(bool(g._ok_ammo_restored),
            "verify() must be true after render repairs ammo text")
        self.assertTrue(bool(g._same_after_repair),
            "render must repair using same primitive references")
        self.assertEqual(g._repaired_ammo, "6 / 26")
        self.assertFalse(bool(g._ok_bad_mode),
            "verify() must be false after corrupting mode text")
        self.assertTrue(bool(g._ok_mode_restored),
            "verify() must be true after render repairs mode text")
        self.assertFalse(bool(g._own_alive),
            "destroy() must kill the weapon component's own root panel")
        self.assertTrue(bool(g._sibling_alive),
            "destroy() must NOT destroy the sibling panel")
        self.assertTrue(bool(g._parent_alive),
            "destroy() must NOT destroy the parent panel")


if __name__ == "__main__":
    unittest.main()
