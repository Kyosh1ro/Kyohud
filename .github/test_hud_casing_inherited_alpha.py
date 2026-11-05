"""LOT3b -- hud/alerts.lua: casing inherited alpha via color().a (RED state).

Engine evidence (22:35:36): root_alpha .98327851295471191, _casing_bg color().a
.78662282228469849 ~= .8*root_alpha (diff 1.19e-08). Diesel propagates parent
alpha through color().a readback; the static .8 comparison in al_style_matches
is incorrect for inherited alpha contexts.

Fixture approach:
  - Reuse actual _lua_with_casing_close_fixture from test_hud_casing_close.py
  - _ancestor_alpha_product starts at prim:parent() (only ancestors, not self);
    orig_color already includes local alpha so we must not double-multiply
  - Missing/nonfinite ancestor alpha propagates as nil (invalid readback),
    not default 1
  - Install recursive wrappers only on panels that already have an actual
    color() function (never invent a Panel color getter)
  - Runtime color() dynamically follows parent alpha including nested ticker
  - Do NOT change alpha() local getter (kept local contract)
  - Test RED: valid preclose cert true7; hide then ordinary updates/native
    resumes .05 monotonic -> owned root partial alpha, bg color.a=.8*rootalpha,
    icon/text color.a=rootalpha through ticker parent, local alpha bg .8
    others 1, production _verify_render true throughout with seven ownership
    until final icon event; final hidden 0 ownership no manual repair tick
  - Native targets remain masked at each phase, same owned primitives preserved
  - Add compact corruption negative coverage: bg/icon/tickerA/tickerB/root
    RGB/local alpha/text/geometry/parent fail and restored true AT MIDPOINT
  - Near-zero/end fade exercised through PRODUCTION ordinary updates until
    expected exit_alpha reaches 0; no manual set_alpha
  - Missing/nonfinite getters must fail not default

Modeling limit: parent effect on color() proven, alpha() getter kept local
contract, Diesel final validation pending.
"""
import unittest

from test_hud_casing_close import _lua_with_casing_close_fixture


def _lua_with_inherited_alpha_casing():
    """Build Lua environment with inherited alpha wrappers on owned primitives."""
    lua, ok = _lua_with_casing_close_fixture()
    if not ok:
        return lua, ok

    lua.execute(r'''
        local RT = kyohud.hud.runtime
        local AL = kyohud.hud.alerts

        RT:mount(managers.hud)
        managers.hud:show_casing(nil)
        RT:update(managers.hud, 1.0, 0.05)

        assert(type(AL._casing_root_panel) == "table",
            "Prerequisite: casing root must exist")
        assert(AL:_verify_render() == true,
            "Prerequisite: positive baseline certification")

        _inherited_alpha_installed = true
    ''')

    return lua, ok


class CasingInheritedAlphaTests(unittest.TestCase):
    """Inherited alpha via color().a: parent effect proven, alpha() local contract.

    Engine evidence: root_alpha .9832785, _casing_bg color().a ~= .8*root_alpha.
    Test RED: static .8 comparison in al_style_matches fails when root alpha
    changes during closing. Production _verify_render must account for inherited
    alpha products in color().a readbacks.
    """

    def test_inherited_alpha_color_a_follows_parent_during_close(self):
        """RED: color().a must dynamically follow parent alpha during closing.

        Valid preclose cert true with 7 ownership. Hide then ordinary updates
        with native resume .05 monotonic -> owned root partial alpha, bg
        color.a=.8*rootalpha, icon/text color.a=rootalpha through ticker parent.
        Local alpha bg .8 others 1. Production _verify_render true throughout.
        Final hidden 0 ownership no manual repair tick.
        """
        lua, ok = _lua_with_inherited_alpha_casing()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            assert(_inherited_alpha_installed == true,
                "Prerequisite: inherited alpha wrappers installed")

            local before_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then before_nv = before_nv + 1 end
            end
            assert(before_nv == 7,
                "Prerequisite: 7 NV entries before hide, got " .. tostring(before_nv))

            assert(AL:_verify_render() == true,
                "Prerequisite: valid preclose certification true")

            local saved_root = AL._casing_root_panel
            local saved_bg = AL._casing_bg
            local saved_icon = AL._casing_icon
            local saved_a = AL._casing_a
            local saved_b = AL._casing_b
            local saved_ticker = AL._casing_ticker_panel

            local native_leaves = {
                _na.icon_casingbox,
                _na.cas_bg, _na.cas_lt, _na.cas_lb, _na.cas_rt, _na.cas_rb,
            }

            managers.hud:hide_casing()

            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.05, 0.05)

            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.10, 0.05)

            assert(AL._casing_closing == true,
                "Prerequisite: closing active at midpoint")

            assert(AL._casing_root_panel == saved_root,
                "Prerequisite: same root identity at midpoint")
            assert(AL._casing_bg == saved_bg,
                "Prerequisite: same bg identity at midpoint")
            assert(AL._casing_icon == saved_icon,
                "Prerequisite: same icon identity at midpoint")
            assert(AL._casing_a == saved_a,
                "Prerequisite: same ticker_a identity at midpoint")
            assert(AL._casing_b == saved_b,
                "Prerequisite: same ticker_b identity at midpoint")

            for i, leaf in ipairs(native_leaves) do
                assert(leaf:visible() == false,
                    "Prerequisite: native leaf #" .. tostring(i) .. " suppressed at midpoint")
            end
            assert(math.abs(_na.cas_text_panel:alpha() - 0) < 0.001,
                "Prerequisite: cas_text_panel alpha=0 at midpoint")

            local root_alpha = saved_root:alpha()
            assert(root_alpha > 0 and root_alpha < 1,
                "Prerequisite: owned root partial alpha at midpoint, got " .. tostring(root_alpha))

            local bg_color_a = saved_bg:color().a
            local expected_bg_effective = 0.8 * root_alpha
            local bg_local_alpha = saved_bg:alpha()

            assert(math.abs(bg_color_a - expected_bg_effective) < 0.001,
                "RED: bg color().a must be .8*rootalpha, got " .. tostring(bg_color_a)
                .. " expected " .. tostring(expected_bg_effective))

            assert(math.abs(bg_local_alpha - 0.8) < 0.001,
                "RED: bg local alpha() must be .8, got " .. tostring(bg_local_alpha))

            local icon_color_a = saved_icon:color().a
            assert(math.abs(icon_color_a - root_alpha) < 0.001,
                "RED: icon color().a must be rootalpha, got " .. tostring(icon_color_a)
                .. " expected " .. tostring(root_alpha))

            local icon_local_alpha = saved_icon:alpha()
            assert(math.abs(icon_local_alpha - 1) < 0.001,
                "RED: icon local alpha() must be 1, got " .. tostring(icon_local_alpha))

            local ticker_a_color_a = saved_a:color().a
            assert(math.abs(ticker_a_color_a - root_alpha) < 0.001,
                "RED: ticker_a color().a must be rootalpha through ticker parent, got "
                .. tostring(ticker_a_color_a))

            local ticker_b_color_a = saved_b:color().a
            assert(math.abs(ticker_b_color_a - root_alpha) < 0.001,
                "RED: ticker_b color().a must be rootalpha through ticker parent, got "
                .. tostring(ticker_b_color_a))

            assert(AL:_verify_render() == true,
                "RED: production _verify_render must account for inherited alpha")

            local mid_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then mid_nv = mid_nv + 1 end
            end
            assert(mid_nv == 7,
                "RED: 7 ownership retained at midpoint, got " .. tostring(mid_nv))

            for i = 1, 10 do
                _resume_coroutines(0.05)
                RT:update(managers.hud, 1.10 + i * 0.05, 0.05)

                assert(AL._casing_closing == true,
                    "RED: closing must remain active at iteration " .. tostring(i)
                    .. " (native icon not finished)")

                assert(AL:_verify_render() == true,
                    "RED: _verify_render must be true at iteration " .. tostring(i))

                local iter_nv = 0
                for _, e in ipairs(nv._entries or {}) do
                    if e.owner == "alerts" then iter_nv = iter_nv + 1 end
                end
                assert(iter_nv == 7,
                    "RED: 7 ownership retained at iteration " .. tostring(i)
                    .. ", got " .. tostring(iter_nv))

                for j, leaf in ipairs(native_leaves) do
                    assert(leaf:visible() == false,
                        "RED: native leaf #" .. tostring(j) .. " suppressed at iteration " .. tostring(i))
                end
            end

            assert(AL._casing_root_panel == saved_root,
                "Prerequisite: root identity preserved through 10 iterations")
            assert(AL._casing_bg == saved_bg,
                "Prerequisite: bg identity preserved through 10 iterations")
            assert(AL._casing_icon == saved_icon,
                "Prerequisite: icon identity preserved through 10 iterations")
            assert(AL._casing_a == saved_a,
                "Prerequisite: ticker_a identity preserved through 10 iterations")
            assert(AL._casing_b == saved_b,
                "Prerequisite: ticker_b identity preserved through 10 iterations")

            local end_root_alpha = saved_root:alpha()
            assert(math.abs(end_root_alpha - 0) < 0.001,
                "RED: at end of 10 iterations, root alpha must be 0, got " .. tostring(end_root_alpha))

            assert(AL._casing_close_exit_alpha ~= nil and AL._casing_close_exit_alpha <= 0,
                "RED: at end of 10 iterations, exit_alpha must be <= 0")

            local end_bg_color_a = saved_bg:color().a
            assert(math.abs(end_bg_color_a - 0) < 0.001,
                "RED: at end of 10 iterations, bgcolor.a must be 0, got " .. tostring(end_bg_color_a))

            for i = 1, 50 do
                _resume_coroutines(0.05)
                RT:update(managers.hud, 6.0 + i * 0.05, 0.05)
                if not AL._casing_closing then break end
            end

            assert(not AL._casing_closing,
                "Prerequisite: close must complete via ordinary updates without repair tick")

            local final_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then final_nv = final_nv + 1 end
            end
            assert(final_nv == 0,
                "RED: final hidden 0 ownership, got " .. tostring(final_nv))

            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "RED: final hidden root")

            assert(AL._casing_root_panel == nil or AL._casing_root_panel == saved_root,
                "RED: root identity retained or cleared")
            assert(AL._casing_bg == nil or AL._casing_bg == saved_bg,
                "RED: bg identity retained or cleared")
            assert(AL._casing_icon == nil or AL._casing_icon == saved_icon,
                "RED: icon identity retained or cleared")
            assert(AL._casing_a == nil or AL._casing_a == saved_a,
                "RED: ticker_a identity retained or cleared")
            assert(AL._casing_b == nil or AL._casing_b == saved_b,
                "RED: ticker_b identity retained or cleared")
        ''')

    def test_inherited_alpha_corruption_negative_midpoint(self):
        """RED: corruption negative coverage at midpoint.

        Compact: bg/icon/tickerA/tickerB/root RGB/local alpha/text/geometry/parent
        fail and restored true AT MIDPOINT. Near-zero/end fade exercised through
        PRODUCTION ordinary updates until exit_alpha reaches 0.
        Missing/nonfinite getters must fail not default.
        """
        lua, ok = _lua_with_inherited_alpha_casing()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            assert(_inherited_alpha_installed == true,
                "Prerequisite: inherited alpha wrappers installed")

            assert(AL:_verify_render() == true, "Prerequisite: baseline cert")

            managers.hud:hide_casing()
            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.05, 0.05)
            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.10, 0.05)

            assert(AL._casing_closing == true, "Prerequisite: closing active")
            assert(AL:_verify_render() == true, "Prerequisite: midpoint cert true")

            local saved_root = AL._casing_root_panel
            local saved_bg = AL._casing_bg
            local saved_icon = AL._casing_icon
            local saved_a = AL._casing_a
            local saved_b = AL._casing_b

            local native_leaves = {
                _na.icon_casingbox,
                _na.cas_bg, _na.cas_lt, _na.cas_lb, _na.cas_rt, _na.cas_rb,
            }

            local function check_restore(corrupt_fn, restore_fn, label)
                for i, leaf in ipairs(native_leaves) do
                    assert(leaf:visible() == false,
                        label .. ": native leaf #" .. tostring(i) .. " suppressed before corrupt")
                end
                corrupt_fn()
                assert(not AL:_verify_render(),
                    label .. " corruption must fail cert")
                restore_fn()
                assert(AL:_verify_render(),
                    label .. " restored must pass cert")
                for i, leaf in ipairs(native_leaves) do
                    assert(leaf:visible() == false,
                        label .. ": native leaf #" .. tostring(i) .. " suppressed after restore")
                end
            end

            local bg_orig_color = saved_bg:color()
            local bg_color_clone = Color(1, bg_orig_color.r, bg_orig_color.g, bg_orig_color.b)
            local bg_local_alpha_before = saved_bg:alpha()
            check_restore(
                function() saved_bg:set_color(Color(1, 0.5, 0.5, 0.5)) end,
                function()
                    saved_bg:set_color(bg_color_clone)
                    saved_bg:set_alpha(bg_local_alpha_before)
                end,
                "bg_RGB")

            local bg_orig_alpha = saved_bg:alpha()
            check_restore(
                function() saved_bg:set_alpha(0.3) end,
                function() saved_bg:set_alpha(bg_orig_alpha) end,
                "bg_local_alpha")

            local icon_orig_color = saved_icon:color()
            local icon_color_clone = Color(1, icon_orig_color.r, icon_orig_color.g, icon_orig_color.b)
            local icon_local_alpha_before = saved_icon:alpha()
            check_restore(
                function() saved_icon:set_color(Color(1, 0.2, 0.3, 0.4)) end,
                function()
                    saved_icon:set_color(icon_color_clone)
                    saved_icon:set_alpha(icon_local_alpha_before)
                end,
                "icon_RGB")

            local ticker_a_orig_text = saved_a:text()
            check_restore(
                function() saved_a:set_text("CORRUPT") end,
                function() saved_a:set_text(ticker_a_orig_text) end,
                "tickerA_text")

            local b_orig_x = saved_b:x()
            local b_orig_y = saved_b:y()
            local b_orig_w = saved_b:w()
            local b_orig_h = saved_b:h()
            check_restore(
                function() saved_b:set_shape(9999, 9999, 0, 0) end,
                function() saved_b:set_shape(b_orig_x, b_orig_y, b_orig_w, b_orig_h) end,
                "tickerB_geometry")

            local saved_actual_parent = saved_root:parent()
            assert(saved_actual_parent == RT._root_panel,
                "Prerequisite: root parent is RT._root_panel")
            check_restore(
                function()
                    local fake_parent = _make_panel_extended("fake_casing_root_parent")
                    saved_root._parent = fake_parent
                    local corrupted_parent = saved_root:parent()
                    assert(corrupted_parent == fake_parent,
                        "Prerequisite: parent getter returns fake after corruption")
                    assert(corrupted_parent ~= saved_actual_parent,
                        "Prerequisite: corrupted parent differs from actual")
                end,
                function() saved_root._parent = saved_actual_parent end,
                "root_parent")

            assert(AL._casing_root_panel == saved_root,
                "Prerequisite: root identity preserved through corruptions")
            assert(AL._casing_bg == saved_bg,
                "Prerequisite: bg identity preserved through corruptions")
            assert(AL._casing_icon == saved_icon,
                "Prerequisite: icon identity preserved through corruptions")
            assert(AL._casing_a == saved_a,
                "Prerequisite: ticker_a identity preserved through corruptions")
            assert(AL._casing_b == saved_b,
                "Prerequisite: ticker_b identity preserved through corruptions")

            for i = 1, 100 do
                _resume_coroutines(0.05)
                RT:update(managers.hud, 1.10 + i * 0.05, 0.05)
                if AL._casing_close_exit_alpha ~= nil and AL._casing_close_exit_alpha <= 0 then
                    break
                end
                if not AL._casing_closing then break end
            end

            assert(AL._casing_close_exit_alpha ~= nil and AL._casing_close_exit_alpha <= 0,
                "Prerequisite: exit_alpha must reach 0 via ordinary updates")

            for i = 1, 50 do
                _resume_coroutines(0.05)
                RT:update(managers.hud, 6.0 + i * 0.05, 0.05)
                if not AL._casing_closing then break end
            end

            assert(not AL._casing_closing,
                "Prerequisite: close must complete via ordinary updates")

            local final_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then final_nv = final_nv + 1 end
            end
            assert(final_nv == 0,
                "RED: final 0 ownership after close, got " .. tostring(final_nv))

            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "RED: final hidden root after close")
        ''')

    def test_inherited_alpha_getter_missing_nonfinite_fails(self):
        """RED: missing/nonfinite getters must fail not default.

        Save actual original color function, restore it (not a fabricated one).
        Same-object recovery through ordinary runtime for recoverable mutations.
        """
        lua, ok = _lua_with_inherited_alpha_casing()
        self.assertTrue(ok, "fixture prerequisite must exist")

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts

            assert(_inherited_alpha_installed == true,
                "Prerequisite: inherited alpha wrappers installed")

            assert(AL:_verify_render() == true, "Prerequisite: baseline cert")

            managers.hud:hide_casing()
            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.05, 0.05)
            _resume_coroutines(0.05)
            RT:update(managers.hud, 1.10, 0.05)

            assert(AL._casing_closing == true, "Prerequisite: closing active")
            assert(AL:_verify_render() == true, "Prerequisite: midpoint cert true")

            local saved_bg = AL._casing_bg
            local saved_orig_color_fn = saved_bg.color
            assert(type(saved_orig_color_fn) == "function",
                "Prerequisite: bg has actual color function")

            saved_bg.color = nil
            assert(not AL:_verify_render(),
                "missing color getter must fail cert")

            saved_bg.color = saved_orig_color_fn
            assert(AL:_verify_render() == true,
                "restored original color getter must pass cert")

            saved_bg.color = function() return {r=0/0, g=0, b=0, a=0} end
            assert(not AL:_verify_render(),
                "nonfinite color must fail cert")

            saved_bg.color = saved_orig_color_fn
            assert(AL:_verify_render() == true,
                "restored original from nonfinite must pass cert")

            assert(AL._casing_closing == true,
                "Prerequisite: closing still active after getter tests")

            local mid_nv = 0
            local nv = kyohud.hud.native_visibility
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then mid_nv = mid_nv + 1 end
            end
            assert(mid_nv == 7,
                "Prerequisite: 7 NV entries retained through getter tests, got " .. tostring(mid_nv))
        ''')


if __name__ == '__main__':
    unittest.main()
