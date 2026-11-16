"""Approved assault quality-split contract tests (test-only, RED on current).

The full verifier body is `A._verify_render_residual_body`; a delegating
test-local counter around it is the authoritative full-check counter. The
desired contract keeps full checks on ~20 meta frames/s, uses fresh light checks
between metas, and still fails closed immediately when a dynamic element is
corrupted after its real animation write.

No production file, current test, fixture copy, or hypothetical API is added
here. `_lua_with_assault_state` supplies the real mount/warm fixture; the real
crossfade fixture is reused from test_hud_assault_states.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_hud_assault_states as states
from test_hud_assault_render import _lua_with_assault_state

DT = 1.0 / 60.0

MOUNT_WARM = r'''
local RT = kyohud.hud.runtime
RT:mount(managers.hud)
local A = kyohud.hud.assault
A:mount(managers.hud)

local t = 1.0
for i = 1, 3 do
    A:update(managers.hud, t, 1 / 60)
    t = t + 1 / 60
end
_G._t = t
'''


def to_py(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "items"):
        return {str(k): to_py(v) for k, v in value.items()}
    return value


def _wrap_full_body(lua, name):
    lua.execute(f'''
        local A = kyohud.hud.assault
        local original = A._verify_render_residual_body
        _G.{name} = {{full = 0}}
        A._verify_render_residual_body = function(self, ...)
            _G.{name}.full = _G.{name}.full + 1
            return original(self, ...)
        end
    ''')


def _native_entries_lua():
    return r'''
        local nv = kyohud.hud.native_visibility
        local entries = 0
        if nv and nv._entries then
            for _, entry in ipairs(nv._entries) do
                if entry.owner == "assault" then entries = entries + 1 end
            end
        end
    '''


class AssaultQualitySplitTests(unittest.TestCase):
    def test_stable_120hz_stream_bounds_full_body_calls(self):
        lua, ok = _lua_with_assault_state()
        self.assertTrue(ok, "assault fixture must exist")
        lua.execute(MOUNT_WARM)
        _wrap_full_body(lua, "_split")
        lua.execute(r'''
            local A = kyohud.hud.assault
            local root_before = A._root_panel
            local title_a_before = A._title_a
            local title_b_before = A._title_b
            _G._split.before_cert = A._render_verified == true
            _G._split.before_acquired = A._native_acquired == true

            local t = _G._t
            for i = 1, 120 do
                A:update(managers.hud, t, 1 / 120)
                t = t + 1 / 120
            end
            _G._split.after_cert = A._render_verified == true
            _G._split.after_acquired = A._native_acquired == true
            _G._split.same_root = A._root_panel == root_before
            _G._split.same_title_a = A._title_a == title_a_before
            _G._split.same_title_b = A._title_b == title_b_before

            local hostages = A._hostages_prim
            local original_text = hostages:text()
            local full_before = _G._split.full
            hostages:set_text("IMPOSSIBLE_STATIC_MARKER")
            _G._split.direct_false = A:_verify_render() == false
            _G._split.direct_full_delta = _G._split.full - full_before
            hostages:set_text(original_text)
            _G._split.direct_restored_true = A:_verify_render() == true
        ''')
        split = to_py(lua.globals()._split)

        self.assertTrue(split["before_cert"], "render must start certified")
        self.assertTrue(split["before_acquired"],
                        "native ownership must start positive")
        self.assertGreater(split["full"], 0,
                           "full verifier body must run on meta frames")
        self.assertLessEqual(
            split["full"], 48,
            "RED: 1s at 120Hz must run ~20 meta frames * 2 full checks, not 240")
        self.assertTrue(split["after_cert"],
                        "render must stay certified during the stable stream")
        self.assertTrue(split["after_acquired"],
                        "native ownership must stay positive during the stream")
        self.assertTrue(split["same_root"],
                        "stable stream must preserve the owned root")
        self.assertTrue(split["same_title_a"],
                        "stable stream must preserve owned title_a")
        self.assertTrue(split["same_title_b"],
                        "stable stream must preserve owned title_b")
        self.assertTrue(split["direct_false"],
                        "direct subthrottle verifier must read static corruption")
        self.assertGreaterEqual(split["direct_full_delta"], 1,
                                "direct verifier must run the full body")
        self.assertTrue(split["direct_restored_true"],
                        "restoring the static text must restore direct cert")

    def test_static_text_corruption_waits_for_next_meta(self):
        lua, ok = _lua_with_assault_state()
        self.assertTrue(ok, "assault fixture must exist")
        lua.execute(MOUNT_WARM)
        _wrap_full_body(lua, "_meta")
        lua.execute(r'''
            local A = kyohud.hud.assault
            local root_before = A._root_panel
            local title_a_before = A._title_a
            local title_b_before = A._title_b
            _G._meta.before_cert = A._render_verified == true
            _G._meta.before_acquired = A._native_acquired == true

            local t = 2.0
            A:update(managers.hud, t, 1 / 60)
            _G._meta.at_200_cert = A._render_verified == true
            _G._meta.at_200_acquired = A._native_acquired == true

            local hostages = A._hostages_prim
            local original_text = hostages:text()
            local full_before = _G._meta.full
            hostages:set_text("IMPOSSIBLE_STATIC_MARKER")

            t = 2.01
            A:update(managers.hud, t, 1 / 60)
            _G._meta.full_delta_201 = _G._meta.full - full_before
            _G._meta.cert_201 = A._render_verified == true
            _G._meta.acquired_201 = A._native_acquired == true
            _G._meta.root_visible_201 = A._root_panel and A._root_panel:visible() == true

            local full_before_2061 = _G._meta.full
            t = 2.061
            A:update(managers.hud, t, 1 / 60)
            _G._meta.full_delta_2061 = _G._meta.full - full_before_2061
            _G._meta.cert_2061 = A._render_verified == true
            _G._meta.render_failed_2061 = A._render_failed == true
            _G._meta.acquired_2061 = A._native_acquired == true
            _G._meta.corner_nil_2061 = A._native_corner == nil
            _G._meta.root_visible_2061 = A._root_panel and A._root_panel:visible() == true
            ''' + _native_entries_lua() + r'''
            _G._meta.entries_2061 = entries

            hostages:set_text(original_text)
            t = 2.061 + 1 / 60
            for i = 1, 40 do
                A:update(managers.hud, t, 1 / 60)
                t = t + 1 / 60
            end
            _G._meta.recovered_cert = A._render_verified == true
            _G._meta.recovered_acquired = A._native_acquired == true
            _G._meta.recovered_root_visible = A._root_panel and A._root_panel:visible() == true
            _G._meta.same_root = A._root_panel == root_before
            _G._meta.same_title_a = A._title_a == title_a_before
            _G._meta.same_title_b = A._title_b == title_b_before
            ''' + _native_entries_lua() + r'''
            _G._meta.recovered_entries = entries
        ''')
        meta = to_py(lua.globals()._meta)

        self.assertTrue(meta["before_cert"], "render must start certified")
        self.assertTrue(meta["before_acquired"],
                        "native ownership must start positive")
        self.assertTrue(meta["at_200_cert"], "meta frame must certify")
        self.assertTrue(meta["at_200_acquired"], "meta frame must keep native")
        self.assertEqual(
            meta["full_delta_201"], 0,
            "RED: 2.01 is a subthrottle frame and must not run the full body")
        self.assertTrue(meta["cert_201"],
                        "RED: static text may remain verified until the next meta")
        self.assertTrue(meta["acquired_201"],
                        "RED: native must remain acquired until the next meta")
        self.assertTrue(meta["root_visible_201"],
                        "RED: root must remain visible until the next meta")
        self.assertGreater(meta["full_delta_2061"], 0,
                           "2.061 must run the next full meta check")
        self.assertFalse(meta["cert_2061"],
                         "corrupt static text must fail the next full check")
        self.assertTrue(meta["render_failed_2061"],
                        "corrupt static text must flag render failure")
        self.assertFalse(meta["acquired_2061"],
                         "corrupt static text must release native ownership")
        self.assertTrue(meta["corner_nil_2061"],
                        "corrupt static text must clear the native corner")
        self.assertFalse(meta["root_visible_2061"],
                         "corrupt static text must hide the owned root")
        self.assertEqual(meta["entries_2061"], 0,
                         "corrupt static text must release assault native entries")
        self.assertTrue(meta["recovered_cert"],
                        "ordinary updates must recover certification")
        self.assertTrue(meta["recovered_acquired"],
                        "ordinary updates must recover native ownership")
        self.assertTrue(meta["recovered_root_visible"],
                        "ordinary updates must recover root visibility")
        self.assertTrue(meta["same_root"], "recovery must reuse the owned root")
        self.assertTrue(meta["same_title_a"], "recovery must reuse owned title_a")
        self.assertTrue(meta["same_title_b"], "recovery must reuse owned title_b")
        self.assertGreater(meta["recovered_entries"], 0,
                           "recovery must re-acquire assault native entries")

    def test_direct_full_verifier_reads_static_corruption(self):
        lua, ok = _lua_with_assault_state()
        self.assertTrue(ok, "assault fixture must exist")
        lua.execute(MOUNT_WARM)
        _wrap_full_body(lua, "_direct")
        lua.execute(r'''
            local A = kyohud.hud.assault
            _G._direct.before_cert = A._render_verified == true
            _G._direct.before_acquired = A._native_acquired == true
            local hostages = A._hostages_prim
            local original_text = hostages:text()
            local full_before = _G._direct.full
            hostages:set_text("IMPOSSIBLE_STATIC_MARKER")
            _G._direct.false_result = A:_verify_render() == false
            _G._direct.full_delta = _G._direct.full - full_before
            hostages:set_text(original_text)
            _G._direct.restored_true = A:_verify_render() == true
        ''')
        direct = to_py(lua.globals()._direct)

        self.assertTrue(direct["before_cert"], "render must start certified")
        self.assertTrue(direct["before_acquired"],
                        "native ownership must start positive")
        self.assertTrue(direct["false_result"],
                        "direct full verifier must reject static corruption")
        self.assertGreaterEqual(direct["full_delta"], 1,
                                "direct verifier must run the full body")
        self.assertTrue(direct["restored_true"],
                        "direct verifier must pass after restoration")

    def test_dynamic_title_and_root_alpha_on_throttled_frame(self):
        lua, ok = _lua_with_assault_state()
        self.assertTrue(ok, "assault fixture must exist")
        lua.execute(MOUNT_WARM)
        _wrap_full_body(lua, "_dyn")
        lua.execute(r'''
            local A = kyohud.hud.assault
            local root_before = A._root_panel
            local title_a_before = A._title_a
            local title_b_before = A._title_b
            _G._dyn.before_cert = A._render_verified == true
            _G._dyn.before_acquired = A._native_acquired == true

            local t = 2.0
            A:update(managers.hud, t, 1 / 60)
            _G._dyn.meta_cert = A._render_verified == true
            _G._dyn.meta_acquired = A._native_acquired == true

            local title_a = A._title_a
            local original_set_x = title_a.set_x
            title_a.set_x = function(self, value)
                return original_set_x(self, value + 1000)
            end
            t = 2.01
            A:update(managers.hud, t, 1 / 60)
            _G._dyn.title_cert = A._render_verified == true
            _G._dyn.title_render_failed = A._render_failed == true
            _G._dyn.title_acquired = A._native_acquired == true
            _G._dyn.title_corner_nil = A._native_corner == nil
            _G._dyn.title_root_visible = A._root_panel and A._root_panel:visible() == true
            ''' + _native_entries_lua() + r'''
            _G._dyn.title_entries = entries
            title_a.set_x = original_set_x

            t = 2.01 + 1 / 60
            for i = 1, 40 do
                A:update(managers.hud, t, 1 / 60)
                t = t + 1 / 60
            end
            _G._dyn.recovered_cert = A._render_verified == true
            _G._dyn.recovered_acquired = A._native_acquired == true
            _G._dyn.recovered_root_visible = A._root_panel and A._root_panel:visible() == true
            _G._dyn.same_root = A._root_panel == root_before
            _G._dyn.same_title_a = A._title_a == title_a_before
            _G._dyn.same_title_b = A._title_b == title_b_before
            ''' + _native_entries_lua() + r'''
            _G._dyn.recovered_entries = entries

            t = 3.0
            A:update(managers.hud, t, 1 / 60)
            _G._dyn.root_meta_cert = A._render_verified == true
            _G._dyn.root_meta_acquired = A._native_acquired == true
            A._root_panel:set_alpha(0 / 0)
            t = 3.01
            A:update(managers.hud, t, 1 / 60)
            _G._dyn.root_cert = A._render_verified == true
            _G._dyn.root_render_failed = A._render_failed == true
            local ra = A._root_panel:alpha()
            _G._dyn.root_alpha_valid = (ra == ra) and ra > 0
            _G._dyn.root_no_false_success = (_G._dyn.root_render_failed == true)
                or (_G._dyn.root_cert == true and _G._dyn.root_alpha_valid == true)
        ''')
        dyn = to_py(lua.globals()._dyn)

        self.assertTrue(dyn["before_cert"], "render must start certified")
        self.assertTrue(dyn["before_acquired"],
                        "native ownership must start positive")
        self.assertTrue(dyn["meta_cert"], "meta frame must certify")
        self.assertTrue(dyn["meta_acquired"], "meta frame must keep native")
        self.assertFalse(dyn["title_cert"],
                         "dynamic title corruption must fail the throttled frame")
        self.assertTrue(dyn["title_render_failed"],
                        "dynamic title corruption must flag render failure")
        self.assertFalse(dyn["title_acquired"],
                         "dynamic title corruption must release native")
        self.assertTrue(dyn["title_corner_nil"],
                        "dynamic title corruption must clear the native corner")
        self.assertFalse(dyn["title_root_visible"],
                         "dynamic title corruption must hide the owned root")
        self.assertEqual(dyn["title_entries"], 0,
                         "dynamic title corruption must release native entries")
        self.assertTrue(dyn["recovered_cert"],
                        "ordinary updates must recover certification")
        self.assertTrue(dyn["recovered_acquired"],
                        "ordinary updates must recover native ownership")
        self.assertTrue(dyn["recovered_root_visible"],
                        "ordinary updates must recover root visibility")
        self.assertTrue(dyn["same_root"], "recovery must reuse the owned root")
        self.assertTrue(dyn["same_title_a"], "recovery must reuse owned title_a")
        self.assertTrue(dyn["same_title_b"], "recovery must reuse owned title_b")
        self.assertGreater(dyn["recovered_entries"], 0,
                           "recovery must re-acquire assault native entries")
        self.assertTrue(dyn["root_meta_cert"], "root meta frame must certify")
        self.assertTrue(dyn["root_meta_acquired"], "root meta frame must keep native")
        self.assertTrue(
            dyn["root_no_false_success"],
            "RED: invalid root alpha must fail closed or be repaired and certified")

    def test_crossfade_outgoing_incoming_corruption_fails_closed(self):
        cases = ("outgoing_text", "outgoing_color", "incoming_alpha")
        for case in cases:
            with self.subTest(case=case):
                lua, ok = states.AssaultMultiStateLabelTests()._make_lua(
                    True, "sustain", False, True, False, False)
                self.assertTrue(ok, "crossfade fixture must exist")
                lua.execute(r'''
                    local state = managers.groupai:state()
                    state._task_data.assault.phase = "fade"
                    local A = kyohud.hud.assault
                    A:update(managers.hud, 2.0, 0.0)
                    A:update(managers.hud, 2.075, 0.075)
                    _G._xf = {
                        outgoing_present = A._outgoing_ticker_a ~= nil,
                        transition_active = A._transition_active == true,
                        before_cert = A._render_verified == true,
                        before_acquired = A._native_acquired == true,
                    }
                ''')
                if case == "outgoing_text":
                    lua.execute(
                        'kyohud.hud.assault._outgoing_ticker_a:set_text("CORRUPTED_OUTGOING")')
                elif case == "outgoing_color":
                    lua.execute(
                        'kyohud.hud.assault._outgoing_ticker_a:set_color(Color(0, 0, 0))')
                else:
                    lua.execute(r'''
                        local A = kyohud.hud.assault
                        local ticker_a = A._ticker_a
                        local original = ticker_a.set_alpha
                        ticker_a.set_alpha = function(self, value)
                            original(self, value)
                            return original(self, 0.123)
                        end
                    ''')
                lua.execute(r'''
                    local A = kyohud.hud.assault
                    A:update(managers.hud, 2.08, 0.005)
                    _G._xf.cert = A._render_verified == true
                    _G._xf.render_failed = A._render_failed == true
                    _G._xf.acquired = A._native_acquired == true
                    _G._xf.corner_nil = A._native_corner == nil
                    _G._xf.root_visible = A._root_panel and A._root_panel:visible() == true
                    ''' + _native_entries_lua() + r'''
                    _G._xf.entries = entries
                ''')
                xf = to_py(lua.globals()._xf)

                self.assertTrue(xf["outgoing_present"],
                                "real crossfade must create outgoing primitives")
                self.assertTrue(xf["transition_active"],
                                "real crossfade must be active before corruption")
                self.assertTrue(xf["before_cert"],
                                "crossfade must be certified before corruption")
                self.assertTrue(xf["before_acquired"],
                                "crossfade must keep native before corruption")
                self.assertFalse(xf["cert"],
                                 "corrupted crossfade primitive must fail closed")
                self.assertTrue(xf["render_failed"],
                                "corrupted crossfade primitive must flag failure")
                self.assertFalse(xf["acquired"],
                                 "corrupted crossfade primitive must release native")
                self.assertTrue(xf["corner_nil"],
                                "corrupted crossfade primitive must clear the corner")
                self.assertFalse(xf["root_visible"],
                                 "corrupted crossfade primitive must hide the root")
                self.assertEqual(xf["entries"], 0,
                                 "corrupted crossfade primitive must release entries")

    def test_backward_submeta_time_forces_full(self):
        lua, ok = _lua_with_assault_state()
        self.assertTrue(ok, "assault fixture must exist")
        lua.execute(MOUNT_WARM)
        _wrap_full_body(lua, "_backward")
        lua.execute(r'''
            local A = kyohud.hud.assault
            local root_before = A._root_panel
            local title_a_before = A._title_a
            local title_b_before = A._title_b
            A:update(managers.hud, 2.0, 1 / 60)
            _G._backward.at_200_cert = A._render_verified == true
            _G._backward.at_200_acquired = A._native_acquired == true
            A:update(managers.hud, 2.04, 1 / 60)
            _G._backward.at_204_cert = A._render_verified == true
            _G._backward.at_204_acquired = A._native_acquired == true
            _G._backward.full = 0
            A:update(managers.hud, 2.03, 1 / 60)
            _G._backward.full_delta = _G._backward.full
            _G._backward.cert = A._render_verified == true
            _G._backward.acquired = A._native_acquired == true
            _G._backward.root_visible = A._root_panel and A._root_panel:visible() == true
            _G._backward.same_root = A._root_panel == root_before
            _G._backward.same_title_a = A._title_a == title_a_before
            _G._backward.same_title_b = A._title_b == title_b_before
        ''')
        backward = to_py(lua.globals()._backward)

        self.assertTrue(backward["at_200_cert"], "2.0 must certify")
        self.assertTrue(backward["at_200_acquired"], "2.0 must keep native")
        self.assertTrue(backward["at_204_cert"], "2.04 must remain certified")
        self.assertTrue(backward["at_204_acquired"], "2.04 must keep native")
        self.assertGreater(
            backward["full_delta"], 0,
            "RED: backward submeta t must force a full body run")
        self.assertTrue(backward["cert"],
                        "backward t must keep render positive")
        self.assertTrue(backward["acquired"],
                        "backward t must keep native positive")
        self.assertTrue(backward["root_visible"],
                        "backward t must keep the root visible")
        self.assertTrue(backward["same_root"],
                        "backward t must preserve the owned root")
        self.assertTrue(backward["same_title_a"],
                        "backward t must preserve owned title_a")
        self.assertTrue(backward["same_title_b"],
                        "backward t must preserve owned title_b")

    def test_fallback_gap_does_not_consume_tick_and_forces_full_on_reacquire(self):
        lua, ok = _lua_with_assault_state()
        self.assertTrue(ok, "assault fixture must exist")
        lua.execute(MOUNT_WARM)
        _wrap_full_body(lua, "_fallback")
        lua.execute(r'''
            local A = kyohud.hud.assault
            local corner = managers.hud._hud_assault_corner
            local bg_box = corner._bg_box
            local text_panel = bg_box and bg_box:child("text_panel")
            local right_bottom = bg_box and bg_box:child("right_bottom")
            local root_before = A._root_panel
            local title_a_before = A._title_a
            local title_b_before = A._title_b
            _G._fallback.full_before_try = nil
            local original_try = A._try_acquire_native
            A._try_acquire_native = function(self, ...)
                if _G._fallback.full_before_try == nil then
                    _G._fallback.full_before_try = _G._fallback.full
                end
                return original_try(self, ...)
            end
            A:update(managers.hud, 2.0, 1 / 60)
            _G._fallback.at_200_cert = A._render_verified == true
            _G._fallback.at_200_acquired = A._native_acquired == true
            corner._point_of_no_return = true
            local full_before_gap = _G._fallback.full
            local t = 2.01
            for i = 1, 20 do
                A:update(managers.hud, t, 1 / 60)
                t = t + 0.01
            end
            _G._fallback.full_delta_gap = _G._fallback.full - full_before_gap
            _G._fallback.gap_acquired = A._native_acquired == true
            _G._fallback.gap_corner_nil = A._native_corner == nil
            _G._fallback.gap_root_visible = A._root_panel and A._root_panel:visible() == true
            local nv = kyohud.hud.native_visibility
            local entries = 0
            if nv and nv._entries then
                for _, entry in ipairs(nv._entries) do
                    if entry.owner == "assault" then entries = entries + 1 end
                end
            end
            _G._fallback.gap_entries = entries
            local ta = text_panel and text_panel:alpha()
            _G._fallback.text_panel_alpha = ta
            _G._fallback.text_panel_alpha_restored = ta == 0.37
            _G._fallback.right_bottom_visible = right_bottom and right_bottom:visible() == true
            corner._point_of_no_return = false
            _G._fallback.full = 0
            _G._fallback.full_before_try = nil
            A:update(managers.hud, 2.21, 1 / 60)
            _G._fallback.full_delta_reacquire = _G._fallback.full
            _G._fallback.full_before_try_value = _G._fallback.full_before_try
            _G._fallback.reacquired_cert = A._render_verified == true
            _G._fallback.reacquired_acquired = A._native_acquired == true
            _G._fallback.reacquired_root_visible = A._root_panel and A._root_panel:visible() == true
            _G._fallback.same_root = A._root_panel == root_before
            _G._fallback.same_title_a = A._title_a == title_a_before
            _G._fallback.same_title_b = A._title_b == title_b_before
            local recovered_entries = 0
            if nv and nv._entries then
                for _, entry in ipairs(nv._entries) do
                    if entry.owner == "assault" then recovered_entries = recovered_entries + 1 end
                end
            end
            _G._fallback.recovered_entries = recovered_entries
        ''')
        fallback = to_py(lua.globals()._fallback)

        self.assertTrue(fallback["at_200_cert"], "2.0 must certify")
        self.assertTrue(fallback["at_200_acquired"], "2.0 must keep native")
        self.assertEqual(fallback["full_delta_gap"], 0,
                         "fallback gap must not run the full body")
        self.assertFalse(fallback["gap_acquired"],
                         "fallback must release native")
        self.assertTrue(fallback["gap_corner_nil"],
                        "fallback must clear the native corner")
        self.assertFalse(fallback["gap_root_visible"],
                         "fallback must hide the owned root")
        self.assertEqual(fallback["gap_entries"], 0,
                         "fallback must release native entries")
        self.assertTrue(fallback["text_panel_alpha_restored"],
                        "fallback must restore the .37 native text_panel alpha")
        self.assertFalse(fallback["right_bottom_visible"],
                         "fallback must restore right_bottom visible=false")
        self.assertGreater(fallback["full_delta_reacquire"], 0,
                           "reacquisition must run a full body first")
        self.assertGreater(fallback["full_before_try_value"], 0,
                           "the full body must run before _try_acquire_native")
        self.assertTrue(fallback["reacquired_cert"],
                        "reacquisition must certify")
        self.assertTrue(fallback["reacquired_acquired"],
                        "reacquisition must re-acquire native")
        self.assertTrue(fallback["reacquired_root_visible"],
                        "reacquisition must show the root")
        self.assertTrue(fallback["same_root"],
                        "reacquisition must reuse the owned root")
        self.assertTrue(fallback["same_title_a"],
                        "reacquisition must reuse owned title_a")
        self.assertTrue(fallback["same_title_b"],
                        "reacquisition must reuse owned title_b")
        self.assertGreater(fallback["recovered_entries"], 0,
                           "reacquisition must restore assault native entries")


if __name__ == "__main__":
    unittest.main()
