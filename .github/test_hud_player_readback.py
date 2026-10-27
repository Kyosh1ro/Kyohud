"""Player readback regressions -- hud/player.lua: label localization and corruption recovery.

Three bounded regressions:

1. Labels _health_label/_armor_label/_downs_label exist as text primitives
   created by the player module. Localization fixture via
   managers.localization:text(key) returns distinguishable strings. With no
   local unit, downs text is exactly "--" and condition text is nonempty
   "unknown", not "normal". With alive local unit and missing revives,
   downs text is still "--". Assert labels use correct localization keys.

2. Geometry: _health_label, _armor_label, _downs_label, _downs_text,
   _condition_text and gauge texts must be pairwise non-overlapping in
   player root coordinates (walk :parent offsets). All rectangles must
   have positive dimensions and lie within root bounds.

3. Corruption detection: mounted healthy -> verify true. Corrupt ROOT x ->
   verify false -> restore via P:update(t1). Corrupt armor_text font_size
   -> verify false -> restore. Corrupt marker x -> verify false -> restore.
   Corrupt downs_text text -> verify false -> restore. Corrupt ROOT w ->
   verify false -> restore. Corrupt _health_label geometry -> verify false
   -> restore. Actual readback must catch each, no manual caches.
   Monotonic t1,t2,... >= 0.1. Repair must not allocate new primitives.
"""
from pathlib import Path
import unittest

from test_hud_player import _lua

ROOT = Path(__file__).resolve().parents[1]


LOCALIZATION_FIXTURE = r'''
local _loc_strings = {
    ky_hud_player_health = "HP",
    ky_hud_player_armor = "ARMOR",
    ky_hud_player_downs = "DOWNS",
    ky_hud_player_unknown_condition = "UNKNOWN",
    ky_hud_player_normal_condition = "NORMAL",
}
managers.localization = managers.localization or {}
function managers.localization:text(key)
    return _loc_strings[key] or ("??" .. tostring(key))
end
'''


class PlayerReadbackLabelsAndUnknownTextTests(unittest.TestCase):
    """Labels _health_label/_armor_label/_downs_label exist; localization fixture
    returns distinguishable strings. With no local unit, downs text is not fake0
    and condition text is nonempty unknown, not normal."""

    def test_labels_exist_and_unknown_downs_not_fake0(self):
        setup = LOCALIZATION_FIXTURE + '''
            managers.player = managers.player or {}
            managers.player.player_unit = function(self) return nil end

            local mgr = managers.hud
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = {_peer_id = nil, _ai = false}
            local parent = _G.panel_double
            mgr._safe_script = {panel = parent}
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/player.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            local mgr = _G.managers.hud
            kyohud.hud.runtime:refresh_settings(mgr)

            local P = kyohud.hud.player
            _hl = P._health_label
            _al = P._armor_label
            _dl = P._downs_label

            _hl_text = _hl and _hl:text() or nil
            _al_text = _al and _al:text() or nil
            _dl_text = _dl and _dl:text() or nil

            _hl_alive = _hl and alive(_hl)
            _al_alive = _al and alive(_al)
            _dl_alive = _dl and alive(_dl)

            _downs_txt = P._downs_text and P._downs_text:text() or nil

            _cond_txt = P._condition_text and P._condition_text:text() or nil
        ''')
        g = lua.globals()

        self.assertIsNotNone(g._hl,
            "RED: P._health_label must exist as a text primitive")
        self.assertIsNotNone(g._al,
            "RED: P._armor_label must exist as a text primitive")
        self.assertIsNotNone(g._dl,
            "RED: P._downs_label must exist as a text primitive")

        self.assertTrue(bool(g._hl_alive),
            "RED: _health_label must be alive")
        self.assertTrue(bool(g._al_alive),
            "RED: _armor_label must be alive")
        self.assertTrue(bool(g._dl_alive),
            "RED: _downs_label must be alive")

        self.assertEqual(g._hl_text, "HP",
            "RED: _health_label must use localization key ky_hud_player_health")
        self.assertEqual(g._al_text, "ARMOR",
            "RED: _armor_label must use localization key ky_hud_player_armor")
        self.assertEqual(g._dl_text, "DOWNS",
            "RED: _downs_label must use localization key ky_hud_player_downs")

        downs_text = g._downs_txt
        self.assertIsNotNone(downs_text,
            "RED: downs text must exist with no local unit")
        self.assertEqual(downs_text, "--",
            "RED: downs text with no local unit must be exactly '--'")

        cond_text = g._cond_txt
        self.assertIsNotNone(cond_text,
            "RED: condition text must exist")
        self.assertNotEqual(cond_text, "",
            "RED: condition text must be nonempty")
        self.assertNotEqual(cond_text.lower(), "normal",
            "RED: condition text must not be 'normal'")
        self.assertEqual(cond_text, "UNKNOWN",
            "RED: condition text must be 'UNKNOWN' from localization key "
            "ky_hud_player_unknown_condition")

    def test_alive_unit_missing_revives_downs_dashdash(self):
        """With alive local unit but no get_revives, downs text must be '--'."""
        setup = LOCALIZATION_FIXTURE + '''
            local damage = {
                _health = 40, _health_max = 100, _armor = 20, _armor_max = 50,
                get_real_health = function(self) return self._health end,
                _max_health = function(self) return self._health_max end,
                get_real_armor = function(self) return self._armor end,
                _max_armor = function(self) return self._armor_max end,
            }
            local unit = {
                _alive = true,
                character_damage = function(self) return damage end,
            }
            managers.player = managers.player or {}
            managers.player.player_unit = function(self) return unit end

            local mgr = managers.hud
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = {_peer_id = nil, _ai = false}
            local parent = _G.panel_double
            mgr._safe_script = {panel = parent}
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/player.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            local mgr = _G.managers.hud
            kyohud.hud.runtime:refresh_settings(mgr)

            local P = kyohud.hud.player
            _downs_txt_alive = P._downs_text and P._downs_text:text() or nil
        ''')
        g = lua.globals()
        downs_text = g._downs_txt_alive
        self.assertIsNotNone(downs_text,
            "RED: downs text must exist with alive local unit")
        self.assertEqual(downs_text, "--",
            "RED: downs text with alive local unit and missing revives "
            "must be exactly '--'")


class PlayerReadbackLabelGeometryNonOverlapTests(unittest.TestCase):
    """Labels and gauge texts must be pairwise non-overlapping in player root
    coordinates. Walk :parent offsets to convert to root space. All rectangles
    must have positive dimensions and lie within root bounds."""

    def test_label_and_gauge_text_rects_pairwise_disjoint(self):
        setup = LOCALIZATION_FIXTURE + '''
            local damage = {
                _health = 40, _health_max = 100, _armor = 20, _armor_max = 50, _revives = 1,
                get_real_health = function(self) return self._health end,
                _max_health = function(self) return self._health_max end,
                get_real_armor = function(self) return self._armor end,
                _max_armor = function(self) return self._armor_max end,
                get_revives = function(self) return self._revives end,
            }
            local unit = {
                _alive = true,
                character_damage = function(self) return damage end,
            }
            managers.player = managers.player or {}
            managers.player.player_unit = function(self) return unit end

            local mgr = managers.hud
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = {_peer_id = nil, _ai = false}
            local parent = _G.panel_double
            mgr._safe_script = {panel = parent}
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/player.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            local mgr = _G.managers.hud
            kyohud.hud.runtime:refresh_settings(mgr)

            local P = kyohud.hud.player
            local root = P._root

            local function to_root_coords(prim, stop_at)
                local ox, oy = 0, 0
                local cur = prim
                while cur ~= nil and cur ~= stop_at do
                    ox = ox + cur:x()
                    oy = oy + cur:y()
                    cur = cur:parent()
                end
                return ox, oy
            end

            _geom_root_w = root:w()
            _geom_root_h = root:h()
            _geom_rects = {}
            _geom_n = 0

            local function add_rect(name, prim)
                if prim and alive(prim) then
                    local rx, ry = to_root_coords(prim, root)
                    _geom_n = _geom_n + 1
                    _geom_rects[_geom_n] = {
                        name = name,
                        x = rx, y = ry,
                        w = prim:w(), h = prim:h(),
                    }
                end
            end

            add_rect("_health_label", P._health_label)
            add_rect("_armor_label", P._armor_label)
            add_rect("_downs_label", P._downs_label)
            add_rect("_downs_text", P._downs_text)
            add_rect("_condition_text", P._condition_text)
            if P._gauge then
                add_rect("gauge.health_text", P._gauge.health_text)
                add_rect("gauge.armor_text", P._gauge.armor_text)
            end
        ''')
        g = lua.globals()
        n = int(g._geom_n)
        rw = float(g._geom_root_w)
        rh = float(g._geom_root_h)
        self.assertGreaterEqual(n, 7,
            "RED: must have at least 7 labeled/gauge text primitives")
        rects = []
        for i in range(1, n + 1):
            r = g._geom_rects[i]
            rects.append({
                'name': str(r.name),
                'x': float(r.x),
                'y': float(r.y),
                'w': float(r.w),
                'h': float(r.h),
            })
        for r in rects:
            self.assertGreater(r['w'], 0.0,
                f"RED: {r['name']} must have positive width")
            self.assertGreater(r['h'], 0.0,
                f"RED: {r['name']} must have positive height")
            self.assertGreaterEqual(r['x'], 0.0,
                f"RED: {r['name']} x must be >= 0 in root coords")
            self.assertGreaterEqual(r['y'], 0.0,
                f"RED: {r['name']} y must be >= 0 in root coords")
            self.assertLessEqual(r['x'] + r['w'], rw,
                f"RED: {r['name']} must fit within root width")
            self.assertLessEqual(r['y'] + r['h'], rh,
                f"RED: {r['name']} must fit within root height")
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a = rects[i]
                b = rects[j]
                disjoint = (a['x'] + a['w'] <= b['x'] or
                            b['x'] + b['w'] <= a['x'] or
                            a['y'] + a['h'] <= b['y'] or
                            b['y'] + b['h'] <= a['y'])
                self.assertTrue(disjoint,
                    f"RED: {a['name']} and {b['name']} must not overlap")


class PlayerReadbackCorruptionRecoveryTests(unittest.TestCase):
    """Corruption detection via verify(): ROOT x, armor_text font_size, marker x,
    downs_text text, ROOT w, _health_label geometry. Each must be detected false,
    then restored true via P:update(mgr, monotonic_t, dt). Actual readback, no
    manual caches. Repair must not allocate new primitives."""

    def test_corruption_detect_and_restore(self):
        setup = LOCALIZATION_FIXTURE + '''
            local damage = {
                _health = 40, _health_max = 100, _armor = 20, _armor_max = 50, _revives = 1,
                get_real_health = function(self) return self._health end,
                _max_health = function(self) return self._health_max end,
                get_real_armor = function(self) return self._armor end,
                _max_armor = function(self) return self._armor_max end,
                get_revives = function(self) return self._revives end,
            }
            local unit = {
                _alive = true,
                character_damage = function(self) return damage end,
            }
            managers.player = managers.player or {}
            managers.player.player_unit = function(self) return unit end

            local mgr = managers.hud
            mgr._teammate_panels[HUDManager.PLAYER_PANEL] = {_peer_id = nil, _ai = false}
            local parent = _G.panel_double
            mgr._safe_script = {panel = parent}
        '''
        lua, ok = _lua(setup=setup)
        self.assertTrue(ok, "RED: lua/hud/player.lua must exist")
        if not ok:
            return
        lua.execute('''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_player = true
            local mgr = _G.managers.hud
            kyohud.hud.runtime:refresh_settings(mgr)

            local P = kyohud.hud.player
            _ok_healthy = P:verify()

            -- Corrupt ROOT x
            P._root:set_shape(999, P._root:y(), P._root:w(), P._root:h())
            _ok_bad_root_x = P:verify()

            P:update(mgr, 0.1, 0.1)
            _ok_root_restored = P:verify()

            -- Corrupt armor_text font_size to 0
            P._gauge.armor_text:set_font_size(0)
            _ok_bad_armor_fs = P:verify()

            P:update(mgr, 0.2, 0.1)
            _ok_armor_fs_restored = P:verify()

            -- Corrupt marker x
            local mk = P._gauge.markers[1]
            mk:set_shape(999, mk:y(), mk:w(), mk:h())
            _ok_bad_marker = P:verify()

            P:update(mgr, 0.3, 0.1)
            _ok_marker_restored = P:verify()

            -- Corrupt downs_text text
            P._downs_text:set_text("GARBAGE")
            _ok_bad_downs = P:verify()

            P:update(mgr, 0.4, 0.1)
            _ok_downs_restored = P:verify()

            _alloc_before = _G._alloc_count()

            -- Corrupt ROOT w
            P._root:set_shape(P._root:x(), P._root:y(), 999, P._root:h())
            _ok_bad_root_w = P:verify()
            P:update(mgr, 0.5, 0.1)
            _ok_root_w_restored = P:verify()

            -- Corrupt _health_label geometry
            P._health_label:set_shape(999, 999, 0, 0)
            _ok_bad_label_geom = P:verify()
            P:update(mgr, 0.6, 0.1)
            _ok_label_geom_restored = P:verify()

            _alloc_after = _G._alloc_count()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._ok_healthy),
            "RED: verify() must be true on a healthy mounted player panel")
        self.assertFalse(bool(g._ok_bad_root_x),
            "RED: verify() must be false after corrupting ROOT x")
        self.assertTrue(bool(g._ok_root_restored),
            "RED: verify() must be true after P:update restores ROOT x")
        self.assertFalse(bool(g._ok_bad_armor_fs),
            "RED: verify() must be false after corrupting armor_text font_size")
        self.assertTrue(bool(g._ok_armor_fs_restored),
            "RED: verify() must be true after P:update restores armor_text font_size")
        self.assertFalse(bool(g._ok_bad_marker),
            "RED: verify() must be false after corrupting marker x")
        self.assertTrue(bool(g._ok_marker_restored),
            "RED: verify() must be true after P:update restores marker x")
        self.assertFalse(bool(g._ok_bad_downs),
            "RED: verify() must be false after corrupting downs_text text")
        self.assertTrue(bool(g._ok_downs_restored),
            "RED: verify() must be true after P:update restores downs_text text")
        self.assertFalse(bool(g._ok_bad_root_w),
            "RED: verify() must be false after corrupting ROOT w")
        self.assertTrue(bool(g._ok_root_w_restored),
            "RED: verify() must be true after P:update restores ROOT w")
        self.assertFalse(bool(g._ok_bad_label_geom),
            "RED: verify() must be false after corrupting _health_label geometry")
        self.assertTrue(bool(g._ok_label_geom_restored),
            "RED: verify() must be true after P:update restores _health_label geometry")
        self.assertEqual(int(g._alloc_before), int(g._alloc_after),
            "RED: repair must not allocate new primitives")


if __name__ == "__main__":
    unittest.main()
