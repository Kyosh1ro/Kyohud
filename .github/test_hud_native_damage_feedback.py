"""Native damage-indicator mirror feedback slice (RED acceptance spec).

Reuses the real local runtime from test_hud_local_h5_lifecycle._local_runtime.
No production code, no Python copy of the feature, no fixture-only snapshots.
"""
import unittest

from test_hud_local_h5_lifecycle import _local_runtime

_SETUP = r'''
    _DMG = _LOCAL_RADIAL:bitmap({name = "damage_indicator"})
    _DMG:set_shape(0, 0, 68, 68); _DMG:set_color(Color(1, 1, 0, 0))
    _DMG:set_alpha(.8); _DMG:set_visible(true)
    _GAUGE = P._gauge.root; local gc = _GAUGE:color()
    _G_R, _G_G, _G_B = gc and gc.r, gc and gc.g, gc and gc.b
    _G_X, _G_Y, _G_W, _G_H = _GAUGE:x(), _GAUGE:y(), _GAUGE:w(), _GAUGE:h()
    _ABG = P._gauge._armor_bg; local ac = _ABG:color()
    _A_R, _A_G, _A_B = ac and ac.r, ac and ac.g, ac and ac.b
    _A_X, _A_Y, _A_W, _A_H = _ABG:x(), _ABG:y(), _ABG:w(), _ABG:h()
    _CD = managers.player:player_unit():character_damage()
    _parent_writes = 0; R:update(mgr, 1.2, .05)
    _FB = P._damage_feedback; _EDGES = _FB and _FB.edges; _FBROOT = _FB and _FB.root
    _NATALPHA = _DMG:alpha(); _NV = kyohud.hud.native_visibility
    function _gauge_same()
        local c = _GAUGE:color()
        return (c and c.r or nil) == _G_R and (c and c.g or nil) == _G_G
            and (c and c.b or nil) == _G_B and _GAUGE:x() == _G_X
            and _GAUGE:y() == _G_Y and _GAUGE:w() == _G_W and _GAUGE:h() == _G_H
    end
    function _armor_same()
        local c = _ABG:color()
        return _ABG:visible() == true and _ABG:parent() == _GAUGE
            and (c and c.r or nil) == _A_R and (c and c.g or nil) == _A_G
            and (c and c.b or nil) == _A_B and _ABG:x() == _A_X
            and _ABG:y() == _A_Y and _ABG:w() == _A_W and _ABG:h() == _A_H
    end
'''


class NativeDamageFeedbackTests(unittest.TestCase):
    def test_native_alpha_mirrors_and_recovers(self):
        lua = _local_runtime(); lua.execute(_SETUP)
        lua.execute(r'''
            local fb, edges = _FB, _EDGES
            _fb_table = type(fb) == "table"
            _four = type(edges) == "table" and #edges == 4
            _alive = _four and alive(edges[1]) and alive(edges[4])
            _parent = _FBROOT ~= nil and _FBROOT:parent() == P._root
            _vis = _FBROOT ~= nil and _FBROOT:visible() == true
            _evis, _ered, _ea = true, true, 0
            if _four then for i = 1, 4 do
                local e = edges[i]; local c = e:color()
                _evis = _evis and e:visible() == true
                _ered = _ered and c ~= nil and c.r == 1 and c.g == 0 and c.b == 0
                _ea = _ea + (c and c.a or 0)
            end end
            _ea = _four and _ea / 4 or 0
            local function _g_close(a, b)
                return a ~= nil and b ~= nil and math.abs(a - b) <= .01
            end
            local function _g_shape(p, x, y, w, h)
                if not p or not alive(p) then return false end
                local ok, px, py, pw, ph = pcall(function()
                    return p:x(), p:y(), p:w(), p:h()
                end)
                return ok and _g_close(px, x) and _g_close(py, y)
                    and _g_close(pw, w) and _g_close(ph, h)
            end
            _geometry = _four and _alive and _FBROOT ~= nil and _GAUGE ~= nil
                and _ABG ~= nil
            if _geometry then
                local ax, ay = _GAUGE:x() + _ABG:x(), _GAUGE:y() + _ABG:y()
                local aw, ah = _ABG:w(), _ABG:h()
                local th = 2 * P._root:w() / 380
                _geometry = _g_shape(_FBROOT, ax, ay, aw, ah)
                    and _g_shape(edges[1], 0, 0, aw, th)
                    and _g_shape(edges[2], 0, ah - th, aw, th)
                    and _g_shape(edges[3], 0, 0, th, ah)
                    and _g_shape(edges[4], aw - th, 0, th, ah)
            end
            local function _track_ok()
                local f = P._damage_feedback
                if not f or f.root ~= _FBROOT or f.edges ~= _EDGES then
                    return false
                end
                local ax, ay = _GAUGE:x() + _ABG:x(), _GAUGE:y() + _ABG:y()
                local aw, ah = _ABG:w(), _ABG:h()
                local th = 2 * P._root:w() / 380
                return _g_shape(f.root, ax, ay, aw, ah)
                    and _g_shape(f.edges[1], 0, 0, aw, th)
                    and _g_shape(f.edges[2], 0, ah - th, aw, th)
                    and _g_shape(f.edges[3], 0, 0, th, ah)
                    and _g_shape(f.edges[4], aw - th, 0, th, ah)
            end
            local _saved_armor = _CD._armor
            _CD._armor = _CD._armor_max * .84; R:update(mgr, 1.201, .01)
            _track84 = _track_ok()
            _CD._armor = 0; R:update(mgr, 1.202, .01)
            _track0 = _track_ok()
            _CD._armor = _CD._armor_max; R:update(mgr, 1.203, .01)
            _track100 = _track_ok()
            _CD._armor = _saved_armor; R:update(mgr, 1.204, .01)
            _trackback = _track_ok()
            _armor_untouched = _armor_same()
            local nc = _DMG:color()
            _nat = _NATALPHA == .8 and nc ~= nil and nc.r == 1
                and nc.g == 0 and nc.b == 0
            _dvis = _DMG:visible()
            _wl = _NV._whitelist[_DMG] ~= nil
                and _NV._whitelist[_DMG].visible == true
            _parent_ok = _parent_writes == 0
            _DMG:set_alpha(.4); R:update(mgr, 1.21, .01)
            _a40 = _four and edges[1]:color() and edges[1]:color().a or -1
            _DMG:set_alpha(0); R:update(mgr, 1.22, .01)
            local f0 = P._damage_feedback
            _ended = f0 ~= nil and ((f0.edges and f0.edges[1]
                and f0.edges[1]:color().a == 0)
                or (f0.root ~= nil and f0.root:visible() == false))
            _same = f0 ~= nil and fb ~= nil and f0 == fb
                and f0.root == _FBROOT and f0.edges ~= nil and edges ~= nil
                and f0.edges[1] == edges[1] and f0.edges[4] == edges[4]
            _zero = _DMG:alpha() == 0
            local function hidden()
                local f = P._damage_feedback
                return f == nil or f.root == nil or not alive(f.root)
                    or f.root:visible() == false
            end
            local oa = _DMG.alpha; _DMG.alpha = function() return nil end
            R:update(mgr, 1.23, .05); _miss = _DMG:visible() == true and hidden()
            _DMG.alpha = oa; _DMG:set_alpha(0 / 0); R:update(mgr, 1.24, .05)
            _nan = _DMG:visible() == true and hidden()
            local op = _DMG.parent
            _DMG.parent = function() return _LOCAL_PLAYER end
            R:update(mgr, 1.25, .05); _pm = _DMG:visible() == true and hidden()
            _DMG.parent = op; _DMG:set_alpha(.8); R:update(mgr, 1.26, .05)
            local fr = P._damage_feedback
            _rec = fr ~= nil and fr == fb and fr.root == _FBROOT
                and fr.edges ~= nil and fr.edges[1] == edges[1]
                and fr.root:visible() == true
            _back = _DMG:visible() == false
            local ogp = _GAUGE.parent
            _GAUGE.parent = function() return _LOCAL_PLAYER end
            R:update(mgr, 1.27, .05)
            _gparent_bad = _DMG:visible() == true and hidden()
            _GAUGE.parent = ogp
            R:update(mgr, 1.28, .05)
            local fback = P._damage_feedback
            _gparent_back = fback ~= nil and fback == fb
                and fback.root == _FBROOT and fback.root:visible() == true
                and _DMG:visible() == false
            local oabgp = _ABG.parent
            _ABG.parent = function() return _LOCAL_PLAYER end
            R:update(mgr, 1.29, .05)
            _abgparent_bad = _DMG:visible() == true and hidden()
            _ABG.parent = oabgp
            R:update(mgr, 1.30, .05)
            local fabg = P._damage_feedback
            _abgparent_back = fabg ~= nil and fabg == fb
                and fabg.root == _FBROOT and fabg.root:visible() == true
                and _DMG:visible() == false
            _gsame = _gauge_same()
            _asame = _armor_same()
        ''')
        g = lua.globals()
        self.assertTrue(bool(g._fb_table) and bool(g._parent) and bool(g._four)
                        and bool(g._alive),
                        "feedback root/edges must be owned persistent primitives")
        self.assertTrue(bool(g._vis) and bool(g._evis) and bool(g._ered),
                        "owned frame and four edges must be visible red")
        self.assertAlmostEqual(float(g._ea), .52, places=3,
                               msg="contour opacity must mirror .65 * native alpha")
        self.assertTrue(bool(g._nat) and not bool(g._dvis) and bool(g._wl),
                        "native alpha/color untouched, hidden via visible whitelist")
        self.assertTrue(bool(g._parent_ok),
                        "native parents must not be mutated")
        self.assertTrue(bool(g._geometry),
                        "feedback root/edges must mirror the fixed armor track with local edge offsets")
        self.assertTrue(bool(g._track84) and bool(g._track0)
                        and bool(g._track100) and bool(g._trackback),
                        "full-width armor-track frame must not follow 84/0/100% armor fill")
        self.assertTrue(bool(g._armor_untouched),
                        "native armor track must stay visible and unchanged")
        self.assertAlmostEqual(float(g._a40), .26, places=3,
                               msg="native .4 must mirror .65 * .4 while player throttled")
        self.assertTrue(bool(g._ended) and bool(g._same) and bool(g._zero),
                        "zero alpha must end the outline with the same objects")
        self.assertTrue(bool(g._miss) and bool(g._nan) and bool(g._pm),
                        "missing/NaN alpha and parent mismatch must fail closed")
        self.assertTrue(bool(g._rec) and bool(g._back),
                        "same indicator and same owned root/edges must recover")
        self.assertTrue(bool(g._gsame), "gauge RGB/position must stay unchanged")
        self.assertTrue(bool(g._asame), "armor-track RGB/position must stay unchanged")
        self.assertTrue(bool(g._gparent_bad),
                        "wrong gauge parent must restore native and hide owned feedback")
        self.assertTrue(bool(g._gparent_back),
                        "restored gauge parent must recertify the same owned root")
        self.assertTrue(bool(g._abgparent_bad),
                        "wrong armor-track parent must restore native and hide owned feedback")
        self.assertTrue(bool(g._abgparent_back),
                        "restored armor-track parent must recertify the same owned root")

    def test_invalid_edge_fails_closed_and_disable_restores_native(self):
        lua = _local_runtime(); lua.execute(_SETUP)
        lua.execute(r'''
            local fb, edges = _FB, _EDGES
            if not (fb and edges and edges[1]) then _absent = true; return end
            _w_state = R._h5_groups and R._h5_groups["local_p_w"]
            _e_state = R._h5_groups and R._h5_groups["local_p_e"]
            local oa = edges[1].set_alpha
            edges[1]:set_alpha(.1)
            edges[1].set_alpha = function() end
            R:update(mgr, 1.3, .05)
            local f1 = P._damage_feedback
            _bad_native = _DMG:visible() == true
            _bad_hidden = f1 == nil or f1.root == nil or not alive(f1.root)
                or f1.root:visible() == false
            edges[1].set_alpha = oa; R:update(mgr, 1.35, .05)
            local f2 = P._damage_feedback
            _good_native = _DMG:visible() == false
            _good_vis = f2 ~= nil and f2.root ~= nil and f2.root:visible() == true
            _good_same = f2 == fb and f2.root == _FBROOT and f2.edges[1] == edges[1]
            _w_ok = W:verify()
                and (R._h5_groups and R._h5_groups["local_p_w"] == _w_state)
            _e_ok = R._h5_groups and R._h5_groups["local_p_e"] == _e_state
            _g_ok = _gauge_same()
            _parent_writes = 0
            kyohud.settings.enable_player = false; R:refresh_settings(mgr)
            R:update(mgr, 1.4, .05)
            _off = _DMG:visible() == true and _parent_writes == 0
            kyohud.settings.enable_player = true
            kyohud.settings.enable_hud_foundation = false
            R:refresh_settings(mgr); R:update(mgr, 1.5, .05)
            _found = _DMG:visible() == true and _parent_writes == 0
        ''')
        g = lua.globals()
        self.assertFalse(bool(g._absent), "P._damage_feedback runtime must exist")
        self.assertTrue(bool(g._bad_native) and bool(g._bad_hidden),
                        "corrupt edge setter must release native and hide feedback")
        self.assertTrue(bool(g._good_native) and bool(g._good_vis)
                        and bool(g._good_same),
                        "repair must recertify the same owned root/edges")
        self.assertTrue(bool(g._w_ok) and bool(g._e_ok) and bool(g._g_ok),
                        "weapons/equipment/gauge must stay unrelated and unchanged")
        self.assertTrue(bool(g._off) and bool(g._found),
                        "player/foundation off must restore native visible untouched")


if __name__ == "__main__":
    unittest.main()
