"""Engine contract: callable TABLE Idstring ACCEPTED, float32 readback tolerance.

Idstring installed as setmetatable({}, {__call=...}) must type=="table" and
be accepted by the guard (desired GREEN). Production rejects type(table)
so these tests document the regression. DB.has must be probed
(db_calls>0) and icons must certify. No newproxy, no userdata fabrication.
"""
import unittest

from test_hud_presentation_recovery import runtime as _rt


class CallableTableIdstringAcceptedTests(unittest.TestCase):
    """callable TABLE Idstring ACCEPTED across assault, casing, pnr."""

    def test_callable_table_idstring_accepted_all_modes(self):
        before = r'''
            _db_calls = 0
            if Idstring == nil then Idstring = function(path) return path end end
            local _saved_Idstring = Idstring
            Idstring = setmetatable({}, {
                __call = function(_, path) return _saved_Idstring(path) end
            })
            assert(type(Idstring) == "table",
                "Idstring must be table, got " .. type(Idstring))
            DB = {has = function(self, kind, path)
                _db_calls = _db_calls + 1
                return true
            end}
        '''
        icons = {"assault": "_glyph_prim", "casing": "_casing_icon", "pnr": "_pnr_icon"}
        for mode in ("assault", "casing", "pnr"):
            with self.subTest(mode=mode):
                lua = _rt(mode, before)
                lua.globals().icon_field = icons[mode]
                lua.execute(r'''
                    assert(_db_calls > 0, "DB.has must be probed, got 0")
                    local icon = subject[icon_field]
                    assert(icon ~= nil, icon_field .. " must exist")
                    assert(subject:_verify_render(),
                        "callable table Idstring: _verify_render must be true (desired GREEN)")
                    local saved_root = subject[root_field]
                    local saved_icon = icon
                    local pid = _panel_id
                    kyohud.hud.runtime:update(managers.hud, 1.6, 0.05)
                    kyohud.hud.runtime:update(managers.hud, 2.2, 0.05)
                    assert(subject[root_field] == saved_root,
                        "root identity preserved across updates")
                    assert(subject[icon_field] == saved_icon,
                        "icon identity preserved across updates")
                    assert(_panel_id == pid, "no allocations across updates")
                    assert(subject:_verify_render(),
                        "still verified after ordinary updates")
                ''')


class CasingTinyWidthGetterDeviationTests(unittest.TestCase):
    """casing tiny width deviation via getter replacement, not setter mutation."""

    def test_casing_tiny_width_deviation_accepted(self):
        lua = _rt("casing")
        lua.execute(r'''
            local AL = kyohud.hud.alerts
            local tp = AL._casing_ticker_panel
            local saved_w = tp.w
            tp.w = function(self) return saved_w(self) - 0.00000666863471 end
            assert(subject:_verify_render(),
                "tiny getter deviation must certify (desired GREEN)")
            local saved_root = subject[root_field]
            local saved_tp = tp
            local pid = _panel_id
            kyohud.hud.runtime:update(managers.hud, 1.6, 0.05)
            kyohud.hud.runtime:update(managers.hud, 2.2, 0.05)
            assert(subject:_verify_render(), "still verified after updates")
            assert(subject[root_field] == saved_root, "root identity preserved")
            assert(AL._casing_ticker_panel == saved_tp, "ticker identity preserved")
            assert(_panel_id == pid, "no allocations")
            tp.w = saved_w
        ''')


class CasingInvalidGeometryMatrixTests(unittest.TestCase):
    """casing invalid geometry matrix x,y,w,h each +0.6, NaN, infinity rejected."""

    def test_casing_invalid_geometry_matrix(self):
        lua = _rt("casing")
        lua.execute(r'''
            local AL = kyohud.hud.alerts
            local tp = AL._casing_ticker_panel
            local fields = {"x", "y", "w", "h"}
            for _, f in ipairs(fields) do
                local saved = tp[f]
                tp[f] = function(self) return saved(self) + 0.6 end
                assert(not subject:_verify_render(),
                    f .. " +0.6 must be rejected")
                tp[f] = saved
                assert(subject:_verify_render(), f .. " restored")

                tp[f] = function(self) return 0/0 end
                assert(not subject:_verify_render(), f .. " NaN must be rejected")
                tp[f] = saved

                tp[f] = function(self) return math.huge end
                assert(not subject:_verify_render(), f .. " infinity must be rejected")
                tp[f] = saved
                assert(subject:_verify_render(), f .. " restored after infinity")
            end
            local orig_alpha = tp.alpha
            tp.alpha = function() return 0.3 end
            assert(not subject:_verify_render(), "alpha mismatch rejected")
            tp.alpha = orig_alpha
            assert(subject:_verify_render(), "alpha restored")

            local orig_layer = tp.layer
            tp.layer = function(self) return orig_layer(self) + 99 end
            assert(not subject:_verify_render(), "layer mismatch rejected")
            tp.layer = orig_layer
            assert(subject:_verify_render(), "layer restored")

            local orig_parent = tp.parent
            local fake = _make_panel_extended("fake_casing_parent")
            tp.parent = function() return fake end
            assert(not subject:_verify_render(), "parent mismatch rejected")
            tp.parent = orig_parent
            assert(subject:_verify_render(), "parent restored")
        ''')


class DoubleAlphaApplicationContractTests(unittest.TestCase):
    """Dual-channel alpha: tint*primitive product, independent setters."""

    def test_casing_pnr_double_alpha_contract(self):
        """Certify effective alpha and recover through ordinary updates.

        Fixture now exposes defect: tint_alpha from opts.color.a (not opts.alpha),
        set_color preserves c.a as _tint_alpha. Production ignores these inputs.
        """
        for mode, desired_effective_a in [("casing", 0.8), ("pnr", 0.75)]:
            with self.subTest(mode=mode, desired=desired_effective_a):
                before = r'''
                    _dual_color_calls = 0
                    _dual_alpha_calls = 0
                    local original_factory = _make_panel_extended
                    function _make_panel_extended(name)
                        local p = original_factory(name)
                        local original_rect = p.rect
                        function p:rect(opts)
                            local ch = original_rect(self, opts)
                            if opts and (opts.name == "kyohud_casing_bg" or opts.name == "pnr_status_bg") then
                                local tint_r = 1
                                local tint_g = 1
                                local tint_b = 1
                                if opts.color then
                                    tint_r = opts.color.r
                                    tint_g = opts.color.g
                                    tint_b = opts.color.b
                                end
                                local tint_a = (opts.color and opts.color.a) or 1
                                local prim_a = 1
                                if opts.alpha ~= nil then
                                    prim_a = opts.alpha
                                end
                                ch._tint = {r=tint_r, g=tint_g, b=tint_b}
                                ch._tint_alpha = tint_a
                                ch._primitive_alpha = prim_a
                                function ch:color()
                                    local eff_a = self._tint_alpha * self._primitive_alpha
                                    return {r=self._tint.r, g=self._tint.g, b=self._tint.b, a=eff_a,
                                            [1]=self._tint.r, [2]=self._tint.g, [3]=self._tint.b, [4]=eff_a}
                                end
                                function ch:alpha()
                                    return self._primitive_alpha
                                end
                                function ch:set_color(c)
                                    _dual_color_calls = _dual_color_calls + 1
                                    if c then
                                        self._tint_alpha = c.a
                                        self._tint = {r=c.r, g=c.g, b=c.b}
                                    end
                                end
                                function ch:set_alpha(a)
                                    _dual_alpha_calls = _dual_alpha_calls + 1
                                    self._primitive_alpha = a
                                end
                            end
                            return ch
                        end
                        return p
                    end
                '''
                lua = _rt(mode, before)
                lua.globals().desired_effective = desired_effective_a
                lua.execute(r'''
                    local bg_field = presentation_mode == "casing" and "_casing_bg" or "_pnr_status_bg"
                    local bg = subject[bg_field]
                    local root = subject[root_field]
                    local n = _panel_id

                    local c1 = _dual_color_calls
                    local a1 = _dual_alpha_calls

                    assert(subject:_verify_render(), "initial positive certification")

                    local ec = bg:color().a
                    local pa = bg:alpha()
                    local ta = bg._tint_alpha
                    assert(math.abs(ec - desired_effective) < 0.001,
                        "effective color().a must be " .. desired_effective .. " got " .. ec)
                    assert(math.abs(pa - desired_effective) < 0.001,
                        "alpha() must be " .. desired_effective .. " got " .. pa)
                    assert(math.abs(ta - 1.0) < 0.001,
                        "tint_alpha must be 1 after sync, got " .. ta)

                    kyohud.hud.runtime:update(managers.hud, 1.6, 0.05)
                    kyohud.hud.runtime:update(managers.hud, 2.2, 0.05)

                    local c2 = _dual_color_calls
                    local a2 = _dual_alpha_calls
                    assert(c2 == c1, "set_color not repeated once stable")
                    assert(a2 == a1, "set_alpha not repeated once stable")

                    assert(subject[bg_field] == bg, "same bg identity")
                    assert(subject[root_field] == root, "same root identity")
                    assert(_panel_id == n, "no allocations")

                    bg:set_color(Color(1, 0.42, 0.43, 0.44))
                    assert(not subject:_verify_render(), "corrupt RGB rejected")
                    kyohud.hud.runtime:update(managers.hud, 2.8, 0.05)
                    assert(subject:_verify_render(), "RGB recovered through production")
                    assert(subject[bg_field] == bg, "bg identity preserved after RGB recovery")

                    bg:set_alpha(0.3)
                    assert(not subject:_verify_render(), "corrupt primitive alpha rejected")
                    kyohud.hud.runtime:update(managers.hud, 3.4, 0.05)
                    assert(subject:_verify_render(), "primitive alpha recovered through production")
                    assert(subject[bg_field] == bg, "bg identity preserved after alpha recovery")
                ''')


if __name__ == "__main__":
    unittest.main()
