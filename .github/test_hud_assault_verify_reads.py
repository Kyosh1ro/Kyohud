"""Bounded assault verifier read characterization and safety tests.

Test-only. The real fixture and mount pattern come from
test_hud_assault_render._lua_with_assault_state. No production file, field,
cache, fallback or native index is changed here.

The first test is a budget: twenty direct A:_verify_render() calls after a
positive warm must each run the full body and reuse the ticker_a rect measured
by _verify_title inside the same _verify_render call, and reuse the X/W values
already validated by check_text for the later geometry checks in that same
verifier. No reuse across verifiers or frames is allowed.

The second test preserves the same-frame fail-closed guard and proves ordinary
recovery after the real _update_title set_x animation setter is restored. The
third test proves there is no stale readback reuse across verifier calls.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hud_assault_render import _lua_with_assault_state

DT = 1.0 / 60.0
WARM = 3
MEASURE = 10

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

MEASURE_READS = r'''
local A = kyohud.hud.assault
_G._probe = {
    verify_render = 0,
    ticker_a = {},
    ticker_b = {},
    before_cert = A._render_verified == true,
    before_acquired = A._native_acquired == true,
}

local original_verify = A._verify_render
A._verify_render = function(self, ...)
    _G._probe.verify_render = _G._probe.verify_render + 1
    return original_verify(self, ...)
end

for _, name in ipairs({ "ticker_a", "ticker_b" }) do
    local prim = A["_" .. name]
    for _, method in ipairs({ "text_rect", "x", "w" }) do
        local original = prim[method]
        _G._probe[name][method] = 0
        prim[method] = function(self, ...)
            _G._probe[name][method] = _G._probe[name][method] + 1
            return original(self, ...)
        end
    end
end

_G._probe.all_true = true
for i = 1, 20 do
    if A:_verify_render() ~= true then
        _G._probe.all_true = false
    end
end
_G._probe.after_cert = A._render_verified == true
_G._probe.after_acquired = A._native_acquired == true
'''

GUARD_RECOVERY = r'''
local A = kyohud.hud.assault
_G._guard = {
    before_cert = A._render_verified == true,
    before_acquired = A._native_acquired == true,
    before_root_visible = A._root_panel and A._root_panel:visible() == true,
    title_a_before = A._title_a,
    title_b_before = A._title_b,
}

local title_a = A._title_a
local original_set_x = title_a.set_x
title_a.set_x = function(self, value)
    return original_set_x(self, value + 1000)
end

local t = _G._t
A:update(managers.hud, t, 1 / 60)
t = t + 1 / 60

_G._guard.after_cert = A._render_verified == true
_G._guard.after_render_failed = A._render_failed == true
_G._guard.after_acquired = A._native_acquired == true
_G._guard.after_native_corner_nil = A._native_corner == nil
_G._guard.after_root_visible = A._root_panel and A._root_panel:visible() == true

local nv = kyohud.hud.native_visibility
local entries = 0
if nv and nv._entries then
    for _, entry in ipairs(nv._entries) do
        if entry.owner == "assault" then entries = entries + 1 end
    end
end
_G._guard.assault_entries = entries

title_a.set_x = original_set_x

for i = 1, 40 do
    A:update(managers.hud, t, 1 / 60)
    t = t + 1 / 60
end

_G._guard.recovered_cert = A._render_verified == true
_G._guard.recovered_acquired = A._native_acquired == true
_G._guard.recovered_root_visible = A._root_panel and A._root_panel:visible() == true
_G._guard.same_title_a = A._title_a == _G._guard.title_a_before
_G._guard.same_title_b = A._title_b == _G._guard.title_b_before
_G._guard.title_a_before = nil
_G._guard.title_b_before = nil

local recovered_entries = 0
if nv and nv._entries then
    for _, entry in ipairs(nv._entries) do
        if entry.owner == "assault" then recovered_entries = recovered_entries + 1 end
    end
end
_G._guard.recovered_assault_entries = recovered_entries

local ticker_a = A._ticker_a
local original_text_rect = ticker_a.text_rect
local reads = 0
ticker_a.text_rect = function(self, ...)
    reads = reads + 1
    return original_text_rect(self, ...)
end
_G._guard.direct_verify_title = A:_verify_title() == true
_G._guard.direct_verify_title_reads = reads
ticker_a.text_rect = original_text_rect
'''

STALE_READS = r'''
local A = kyohud.hud.assault
_G._reads = {}
_G._reads.positive = A:_verify_render() == true

local ticker_a = A._ticker_a
local ticker_b = A._ticker_b

local original_text_rect_a = ticker_a.text_rect
ticker_a.text_rect = function(self, ...)
    error("probe text_rect throw")
end
_G._reads.throw_false = A:_verify_render() == false
ticker_a.text_rect = original_text_rect_a
_G._reads.throw_restored_true = A:_verify_render() == true

ticker_a.text_rect = function(self, ...)
    return 0, 0, 0 / 0, 0 / 0
end
_G._reads.nan_false = A:_verify_render() == false
ticker_a.text_rect = original_text_rect_a
_G._reads.nan_restored_true = A:_verify_render() == true

local ax = ticker_a:x()
ticker_a:set_x(ax + 50)
_G._reads.ticker_a_x_false = A:_verify_render() == false
ticker_a:set_x(ax)
_G._reads.ticker_a_x_restored_true = A:_verify_render() == true

local bx = ticker_b:x()
ticker_b:set_x(bx + 50)
_G._reads.ticker_b_x_false = A:_verify_render() == false
ticker_b:set_x(bx)
_G._reads.ticker_b_x_restored_true = A:_verify_render() == true

local aw = ticker_a:w()
ticker_a:set_shape(ticker_a:x(), ticker_a:y(), aw + 50, ticker_a:h())
_G._reads.ticker_a_w_false = A:_verify_render() == false
ticker_a:set_shape(ticker_a:x(), ticker_a:y(), aw, ticker_a:h())
_G._reads.ticker_a_w_restored_true = A:_verify_render() == true

local bw = ticker_b:w()
ticker_b:set_shape(ticker_b:x(), ticker_b:y(), bw + 50, ticker_b:h())
_G._reads.ticker_b_w_false = A:_verify_render() == false
ticker_b:set_shape(ticker_b:x(), ticker_b:y(), bw, ticker_b:h())
_G._reads.ticker_b_w_restored_true = A:_verify_render() == true
'''


def to_py(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if hasattr(value, "items"):
        return {str(k): to_py(v) for k, v in value.items()}
    return value


class AssaultVerifyReadTests(unittest.TestCase):
    def test_direct_full_verifiers_reuse_same_verifier_readbacks(self):
        lua, ok = _lua_with_assault_state()
        self.assertTrue(ok, "assault fixture must exist")
        lua.execute(MOUNT_WARM)
        lua.execute(MEASURE_READS)
        probe = to_py(lua.globals()._probe)

        self.assertTrue(probe["before_cert"],
                        "render must be certified before measurement")
        self.assertTrue(probe["before_acquired"],
                        "native ownership must be positive before measurement")
        self.assertTrue(probe["after_cert"],
                        "render must remain certified after measurement")
        self.assertTrue(probe["after_acquired"],
                        "native ownership must remain positive after measurement")
        self.assertEqual(
            probe["verify_render"], 20,
            "twenty direct full verifiers must each run the full body")
        self.assertTrue(probe["all_true"],
                        "every direct full verifier must return true")
        self.assertEqual(
            probe["ticker_a"]["text_rect"], 20,
            "ticker_a text_rect must be read once per direct full verifier by "
            "reusing _verify_title's same-call measurement")
        self.assertEqual(
            probe["ticker_b"]["text_rect"], 20,
            "ticker_b text_rect must be read once per direct full verifier")
        for name in ("ticker_a", "ticker_b"):
            for method in ("x", "w"):
                self.assertLessEqual(
                    probe[name][method], 20,
                    "%s %s must reuse the same-verifier validated "
                    "check_text readback" % (name, method))

    def test_same_frame_title_corruption_fails_closed_and_recovers(self):
        lua, ok = _lua_with_assault_state()
        self.assertTrue(ok, "assault fixture must exist")
        lua.execute(MOUNT_WARM)
        lua.execute(GUARD_RECOVERY)
        guard = to_py(lua.globals()._guard)

        self.assertTrue(guard["before_cert"],
                        "guard render must start certified")
        self.assertTrue(guard["before_acquired"],
                        "guard native ownership must start positive")
        self.assertTrue(guard["before_root_visible"],
                        "guard root must start visible")
        self.assertFalse(guard["after_cert"],
                         "corrupted title x must fail the same-frame verifier")
        self.assertTrue(guard["after_render_failed"],
                        "corrupted title x must flag render failure")
        self.assertFalse(guard["after_acquired"],
                         "corrupted title x must release native ownership")
        self.assertTrue(guard["after_native_corner_nil"],
                        "corrupted title x must clear the native corner")
        self.assertFalse(guard["after_root_visible"],
                         "corrupted title x must hide the owned root")
        self.assertEqual(guard["assault_entries"], 0,
                         "corrupted title x must release assault native entries")

        self.assertTrue(guard["recovered_cert"],
                        "ordinary updates must recover certification")
        self.assertTrue(guard["recovered_acquired"],
                        "ordinary updates must recover native ownership")
        self.assertTrue(guard["recovered_root_visible"],
                        "ordinary updates must recover root visibility")
        self.assertTrue(guard["same_title_a"],
                        "recovery must reuse the same owned title_a primitive")
        self.assertTrue(guard["same_title_b"],
                        "recovery must reuse the same owned title_b primitive")
        self.assertGreater(guard["recovered_assault_entries"], 0,
                           "recovery must re-acquire assault native entries")
        self.assertTrue(guard["direct_verify_title"],
                        "_verify_title must remain directly callable and fresh")
        self.assertGreaterEqual(
            guard["direct_verify_title_reads"], 1,
            "_verify_title must read ticker_a text_rect on direct invocation")

    def test_no_stale_readbacks_across_verifier_calls(self):
        lua, ok = _lua_with_assault_state()
        self.assertTrue(ok, "assault fixture must exist")
        lua.execute(MOUNT_WARM)
        lua.execute(STALE_READS)
        reads = to_py(lua.globals()._reads)

        self.assertTrue(reads["positive"],
                        "baseline direct verifier must pass")
        self.assertTrue(reads["throw_false"],
                        "throwing text_rect must fail the same verifier call")
        self.assertTrue(reads["throw_restored_true"],
                        "restoring text_rect must pass the next verifier call")
        self.assertTrue(reads["nan_false"],
                        "NaN text_rect must fail the same verifier call")
        self.assertTrue(reads["nan_restored_true"],
                        "restoring text_rect must pass the next verifier call")
        self.assertTrue(reads["ticker_a_x_false"],
                        "corrupted ticker_a x must fail immediately")
        self.assertTrue(reads["ticker_a_x_restored_true"],
                        "restoring ticker_a x must pass immediately")
        self.assertTrue(reads["ticker_b_x_false"],
                        "corrupted ticker_b x must fail immediately")
        self.assertTrue(reads["ticker_b_x_restored_true"],
                        "restoring ticker_b x must pass immediately")
        self.assertTrue(reads["ticker_a_w_false"],
                        "corrupted ticker_a w must fail immediately")
        self.assertTrue(reads["ticker_a_w_restored_true"],
                        "restoring ticker_a w must pass immediately")
        self.assertTrue(reads["ticker_b_w_false"],
                        "corrupted ticker_b w must fail immediately")
        self.assertTrue(reads["ticker_b_w_restored_true"],
                        "restoring ticker_b w must pass immediately")


if __name__ == "__main__":
    unittest.main()
