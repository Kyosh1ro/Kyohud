"""Mission visibility trace: one root_shape first-refusal transition.

RED vertical tracer for the opt-in KYO_MISSION_TRACE diagnostic. A Lua
io.open/log spy is prepended to the first real Mission chunk, then the same
real chunk is loaded under the other production contexts. The sentinel must
be opened and closed exactly once across those loads. A healthy Mission is
mounted and certified through the real dispatch fixture. The retained root is
corrupted through its original set_shape before the setter is replaced by a
no-op, so ordinary feed cannot repair it. One real feed must emit exactly one
[KyoHUD][MissionTrace] refusal with reason=root_shape. Twenty identical feeds
must not repeat that reason. Restoring the original setter and feeding twice
must recover the same root with reason=ok.

The production trace does not exist yet. These assertions are therefore RED
with an explicit missing-diagnostic message; they are not a test-side trace.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_hud_mission as mission_fixture
from test_hud_mission_fixed_anchor import INSTALL_PARENT_LINKS
from test_hud_mission_phase_probe import INSTALL_DISPATCH, MOUNT_CERTIFY

TRACE_PREAMBLE = r'''
_real_io_open = io.open
_real_io_close = io.close
_trace_handle = nil
_trace_opens = 0
_trace_closes = 0
io.open = function(path, mode)
    if path == ModPath .. "KYO_MISSION_TRACE" then
        _trace_opens = _trace_opens + 1
        local handle = {
            close = function(self)
                _trace_closes = _trace_closes + 1
                return true
            end,
        }
        _trace_handle = handle
        return handle
    end
    return _real_io_open(path, mode)
end
io.close = function(handle)
    if handle ~= nil and handle == _trace_handle then
        _trace_closes = _trace_closes + 1
        return true
    end
    return _real_io_close(handle)
end
_trace_real_log = log
_trace_logs = {}
log = function(message, ...)
    local text = tostring(message)
    if text:find("[KyoHUD][MissionTrace]", 1, true) == 1 then
        _trace_logs[#_trace_logs + 1] = text
    end
    return _trace_real_log(message, ...)
end
'''

CORRUPT_ROOT = r'''
local M = kyohud.hud.mission
local mgr = _G._phase_mgr
_G._trace_root = M._root_panel
_G._trace_original_set_shape = M._root_panel.set_shape
local x, y, w, h = M._root_panel:x(), M._root_panel:y(),
    M._root_panel:w(), M._root_panel:h()
_G._trace_original_set_shape(M._root_panel, x + 25, y, w, h)
M._root_panel.set_shape = function() end

_G._dispatch_feed(125)

_G._trace_failure_verified = M._render_verified == true
_G._trace_failure_visible = M._root_panel:visible()
_G._trace_failure_alpha = mgr._hud_heist_timer._timer_text:alpha()
_G._trace_failure_same = rawequal(M._root_panel, _G._trace_root)
_G._trace_failure_logs = #_trace_logs
_G._trace_failure_reasons = 0
for _, message in ipairs(_trace_logs) do
    if message:find("reason=root_shape", 1, true) then
        _G._trace_failure_reasons = _G._trace_failure_reasons + 1
    end
end
'''

REPEAT_FEED = r'''
local M = kyohud.hud.mission
local mgr = _G._phase_mgr
for i = 1, 20 do
    _G._dispatch_feed(125)
end
_G._trace_repeat_logs = #_trace_logs
_G._trace_repeat_reasons = 0
for _, message in ipairs(_trace_logs) do
    if message:find("reason=root_shape", 1, true) then
        _G._trace_repeat_reasons = _G._trace_repeat_reasons + 1
    end
end
_G._trace_repeat_verified = M._render_verified == true
_G._trace_repeat_visible = M._root_panel:visible()
_G._trace_repeat_alpha = mgr._hud_heist_timer._timer_text:alpha()
_G._trace_repeat_same = rawequal(M._root_panel, _G._trace_root)
'''

RESTORE_AND_RECOVER = r'''
local M = kyohud.hud.mission
local mgr = _G._phase_mgr
M._root_panel.set_shape = _G._trace_original_set_shape
_G._dispatch_feed(125)
_G._dispatch_feed(125)
_G._trace_recovered_verified = M._render_verified == true
_G._trace_recovered_visible = M._root_panel:visible()
_G._trace_recovered_alpha = mgr._hud_heist_timer._timer_text:alpha()
_G._trace_recovered_same = rawequal(M._root_panel, _G._trace_root)
_G._trace_recovered_logs = #_trace_logs
_G._trace_recovered_second_ok = false
if _trace_logs[2] then
    _G._trace_recovered_second_ok =
        _trace_logs[2]:find("reason=ok", 1, true) ~= nil
end

_G._trace_all_prefixed = true
_G._trace_all_clean = true
local forbidden = {"firestarter", "heist_", "kyohud_mission", "objective_text",
    "amount_text", "native objective", "player_unit", "player"}
for _, message in ipairs(_trace_logs) do
    if message:find("[KyoHUD][MissionTrace]", 1, true) ~= 1 then
        _G._trace_all_prefixed = false
    end
    local lowered = string.lower(message)
    for _, needle in ipairs(forbidden) do
        if lowered:find(needle, 1, true) then
            _G._trace_all_clean = false
        end
    end
end
'''


DISABLED_PREAMBLE = r'''
_real_io_open = io.open
_real_io_close = io.close
_trace_handle = {}
_trace_opens = 0
_trace_closes = 0
io.open = function(path, mode)
    if path == ModPath .. "KYO_MISSION_TRACE" then
        _trace_opens = _trace_opens + 1
        return nil
    end
    return _real_io_open(path, mode)
end
io.close = function(handle)
    if handle ~= nil and handle == _trace_handle then
        _trace_closes = _trace_closes + 1
        return true
    end
    return _real_io_close(handle)
end
_trace_real_clock = os.clock
_trace_clock_reads = 0
os.clock = function()
    _trace_clock_reads = _trace_clock_reads + 1
    return _trace_real_clock()
end
_trace_real_log = log
_trace_logs = {}
log = function(message, ...)
    local text = tostring(message)
    if text:find("[KyoHUD][MissionTrace]", 1, true) == 1 then
        _trace_logs[#_trace_logs + 1] = text
    end
    return _trace_real_log(message, ...)
end
'''

NATIVE_FIRST_REFUSAL = r'''
local M = kyohud.hud.mission
local common = _G._phase_parent
local parent = common:panel({ name = "native_objectives_hud_panel" })
parent:set_shape(0, 0, 1920, 1080)
parent:set_visible(true)
parent:set_alpha(1)
local panel = parent:panel({ name = "objectives_panel", w = 500, h = 100 })
panel:set_shape(0, 0, 500, 100)
panel:set_visible(false)
_G._phase_mgr._hud_objectives = { _hud_panel = parent }
_G._native_root = M._root_panel
_G._native_parent_original = parent.parent
_G._native_parent_attempts = 0

_G._native_baseline_start = #_trace_logs
_G._dispatch_feed(125)
_G._native_baseline_verified = M._render_verified == true
_G._native_baseline_logs = #_trace_logs - _G._native_baseline_start

parent.parent = function(self)
    _G._native_parent_attempts = _G._native_parent_attempts + 1
    error("synthetic parent read failure")
end
_G._native_failure_start = #_trace_logs
_G._dispatch_feed(125)
_G._native_failure_verified = M._render_verified == true
_G._native_failure_visible = M._root_panel:visible()
_G._native_failure_alpha = _G._phase_mgr._hud_heist_timer._timer_text:alpha()
_G._native_failure_same = rawequal(M._root_panel, _G._native_root)
_G._native_failure_logs = #_trace_logs - _G._native_failure_start
_G._native_failure_reason = false
for i = _G._native_failure_start + 1, #_trace_logs do
    if _trace_logs[i]:find("reason=native:read_error:hud:parent@1", 1, true) then
        _G._native_failure_reason = true
    end
end

parent.parent = _G._native_parent_original
_G._native_recovery_start = #_trace_logs
_G._dispatch_feed(125)
_G._dispatch_feed(125)
_G._native_recovery_verified = M._render_verified == true
_G._native_recovery_visible = M._root_panel:visible()
_G._native_recovery_alpha = _G._phase_mgr._hud_heist_timer._timer_text:alpha()
_G._native_recovery_same = rawequal(M._root_panel, _G._native_root)
_G._native_recovery_logs = #_trace_logs - _G._native_recovery_start
_G._native_recovery_ok = false
if _trace_logs[#_trace_logs] then
    _G._native_recovery_ok =
        _trace_logs[#_trace_logs]:find("reason=ok", 1, true) ~= nil
end
'''

LOGGER_CAP = r'''
local M = kyohud.hud.mission
local root = M._root_panel
_G._cap_root = root
_G._cap_x, _G._cap_y = root:x(), root:y()
_G._cap_w, _G._cap_h = root:w(), root:h()
_G._cap_attempts = 0
local real_log = log
log = function(message, ...)
    local text = tostring(message)
    if text:find("[KyoHUD][MissionTrace]", 1, true) == 1 then
        _G._cap_attempts = _G._cap_attempts + 1
        real_log(message, ...)
        error("synthetic logger failure")
    end
    return real_log(message, ...)
end
local ok, err = pcall(function()
    for i = 1, 40 do
        root:set_visible(false)
        M:_verify_render()
        root:set_visible(true)
        M:_verify_render()
    end
end)
_G._cap_loop_ok = ok
_G._cap_loop_err = tostring(err or "")
_G._cap_verified = M._render_verified == true
_G._cap_same = rawequal(M._root_panel, root)
_G._cap_geometry_same = M._root_panel:x() == _G._cap_x
    and M._root_panel:y() == _G._cap_y
    and M._root_panel:w() == _G._cap_w
    and M._root_panel:h() == _G._cap_h
'''

DEAD_ROOT = r'''
local M = kyohud.hud.mission
local root = M._root_panel
_G._dead_root_original_alive = alive
alive = function(x)
    if x == root then return false end
    return _G._dead_root_original_alive(x)
end
_G._dead_root_attempts = 0
_G._dead_root_originals = {}
for _, name in ipairs({"visible", "x", "y", "w", "h"}) do
    local original = root[name]
    _G._dead_root_originals[name] = original
    root[name] = function(self, ...)
        _G._dead_root_attempts = _G._dead_root_attempts + 1
        return original(self, ...)
    end
end
_G._dead_root_verified = M:_verify_render()
alive = _G._dead_root_original_alive
'''


def _lua_with_preamble(preamble):
    original_read = mission_fixture._read
    mission_source = original_read(mission_fixture.MISSION_PATH)

    def traced_read(path):
        source = original_read(path)
        if source is not None and path == mission_fixture.MISSION_PATH:
            return preamble + "\n" + source
        return source

    mission_fixture._read = traced_read
    try:
        lua, ok = mission_fixture._lua()
    finally:
        mission_fixture._read = original_read
    return lua, ok, mission_source


def _load_existing_contexts(lua, mission_source):
    for context in ("lib/managers/lootmanager",
                    "lib/managers/gameplaycentralmanager"):
        lua.execute(f'RequiredScript = "{context}"')
        lua.execute(mission_source)
    lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')


class MissionVisibilityTraceTests(unittest.TestCase):
    def _assert_certified(self, g, label="positive baseline"):
        self.assertIs(g._cert_mounted, True, f"{label}: mission must be mounted")
        self.assertIs(g._cert_root, True, f"{label}: mission must own a root")
        self.assertIs(g._cert_verified, True, f"{label}: render must verify")
        self.assertEqual(g._cert_timer_text, "02:05",
                         f"{label}: real feed hook must capture 02:05")
        self.assertIs(g._cert_native_acquired, True,
                      f"{label}: native timer must be acquired")
        self.assertEqual(g._cert_native_alpha, 0,
                         f"{label}: acquired native timer alpha must be 0")

    def test_root_shape_refusal_logs_once_then_recovers(self):
        original_read = mission_fixture._read
        mission_source = original_read(mission_fixture.MISSION_PATH)

        def traced_read(path):
            source = original_read(path)
            if source is not None and path == mission_fixture.MISSION_PATH:
                return TRACE_PREAMBLE + "\n" + source
            return source

        mission_fixture._read = traced_read
        try:
            lua, ok = mission_fixture._lua()
        finally:
            mission_fixture._read = original_read

        self.assertTrue(ok, "lua/hud/mission.lua must exist")
        if not ok:
            return

        self.assertIsNotNone(mission_source,
                             "lua/hud/mission.lua must be readable")
        if mission_source is None:
            return

        for context in ("lib/managers/lootmanager",
                        "lib/managers/gameplaycentralmanager"):
            lua.execute(f'RequiredScript = "{context}"')
            lua.execute(mission_source)
        lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')

        lua.execute(INSTALL_PARENT_LINKS)
        lua.execute(INSTALL_DISPATCH)
        lua.execute(MOUNT_CERTIFY)

        g = lua.globals()
        self.assertIs(g._cert_mounted, True,
                      "positive baseline: the real Mission must be mounted")
        self.assertIs(g._cert_root, True,
                      "positive baseline: the mounted Mission must own a root")
        self.assertIs(g._cert_verified, True,
                      "positive baseline: the healthy Mission render must verify")
        self.assertEqual(g._cert_timer_text, "02:05",
                         "positive baseline: the real feed hook must capture 02:05")
        self.assertIs(g._cert_native_acquired, True,
                      "positive baseline: the native timer must be acquired")
        self.assertEqual(g._cert_native_alpha, 0,
                         "positive baseline: acquired native timer alpha must be 0")

        lua.execute("_G._trace_initial_logs = #_trace_logs")
        self.assertEqual(g._trace_initial_logs, 0,
                         "positive baseline: a healthy mounted Mission must be silent")

        lua.execute(CORRUPT_ROOT)
        self.assertIs(g._trace_failure_verified, False,
                      "a shifted retained root must fail Mission render verification")
        self.assertIs(g._trace_failure_visible, False,
                      "a shifted retained root must hide the owned Mission root")
        self.assertEqual(g._trace_failure_alpha, 1,
                         "a root_shape refusal must restore native timer alpha to 1")
        self.assertIs(g._trace_failure_same, True,
                      "a root_shape refusal must retain the original root identity")
        self.assertEqual(
            g._trace_failure_logs, 1,
            "RED: production MissionTrace diagnostic is missing: the corrupt "
            "root shape transition must emit exactly one "
            "[KyoHUD][MissionTrace] line with reason=root_shape",
        )
        self.assertEqual(g._trace_failure_reasons, 1,
                         "RED: the single first-refusal line must carry reason=root_shape")

        lua.execute(REPEAT_FEED)
        self.assertIs(g._trace_repeat_verified, False,
                      "ordinary feeds must not repair the retained root shape")
        self.assertIs(g._trace_repeat_visible, False,
                      "ordinary feeds must keep the refused root hidden")
        self.assertEqual(g._trace_repeat_alpha, 1,
                         "ordinary feeds must keep native timer alpha at 1")
        self.assertIs(g._trace_repeat_same, True,
                      "ordinary feeds must retain the original root identity")
        self.assertEqual(g._trace_repeat_reasons, 1,
                         "RED: recovery attempts must not repeat reason=root_shape")
        self.assertEqual(g._trace_repeat_logs, 1,
                         "RED: twenty identical refusals must stay silent after the "
                         "first reason=root_shape line")

        lua.execute(RESTORE_AND_RECOVER)
        self.assertIs(g._trace_recovered_verified, True,
                      "restoring the original setter must certify the same root")
        self.assertIs(g._trace_recovered_visible, True,
                      "restoring the original setter must show the same root")
        self.assertEqual(g._trace_recovered_alpha, 0,
                         "recovery must reacquire native timer alpha 0")
        self.assertIs(g._trace_recovered_same, True,
                      "recovery must retain the original root identity")
        self.assertEqual(
            g._trace_recovered_logs, 2,
            "RED: recovery must add exactly one second MissionTrace line",
        )
        self.assertIs(g._trace_recovered_second_ok, True,
                      "RED: the second MissionTrace line must carry reason=ok")
        self.assertIs(g._trace_all_prefixed, True,
                      "every captured trace line must carry the "
                      "[KyoHUD][MissionTrace] prefix")
        self.assertIs(g._trace_all_clean, True,
                      "trace lines must not expose mission, objective or player names")
        self.assertEqual(
            g._trace_opens, 1,
            "RED: the mission chunk must read ModPath .. \"KYO_MISSION_TRACE\" "
            "exactly once",
        )
        self.assertEqual(
            g._trace_closes, 1,
            "RED: the returned KYO_MISSION_TRACE handle must be closed exactly once",
        )

    def test_disabled_sentinel_keeps_same_ownership_without_trace(self):
        lua, ok, mission_source = _lua_with_preamble(DISABLED_PREAMBLE)
        self.assertTrue(ok, "lua/hud/mission.lua must exist")
        if not ok:
            return
        self.assertIsNotNone(mission_source,
                             "lua/hud/mission.lua must be readable")
        if mission_source is None:
            return

        _load_existing_contexts(lua, mission_source)
        lua.execute(INSTALL_PARENT_LINKS)
        lua.execute(INSTALL_DISPATCH)
        lua.execute(MOUNT_CERTIFY)

        g = lua.globals()
        self._assert_certified(g)
        self.assertEqual(g._trace_opens, 1,
                         "the mission chunk must open the absent sentinel once")
        self.assertEqual(g._trace_closes, 0,
                         "a nil sentinel handle must never be closed")
        self.assertEqual(g._trace_clock_reads, 0,
                         "a disabled trace must not read the diagnostic clock")

        lua.execute(CORRUPT_ROOT)
        self.assertIs(g._trace_failure_verified, False,
                      "a shifted retained root must fail Mission render verification")
        self.assertIs(g._trace_failure_visible, False,
                      "a shifted retained root must hide the owned Mission root")
        self.assertEqual(g._trace_failure_alpha, 1,
                         "a root_shape refusal must restore native timer alpha to 1")
        self.assertIs(g._trace_failure_same, True,
                      "a root_shape refusal must retain the original root identity")
        self.assertEqual(g._trace_failure_logs, 0,
                         "a disabled trace must emit no MissionTrace line")
        self.assertEqual(g._trace_failure_reasons, 0,
                         "a disabled trace must emit no reason")

        lua.execute(REPEAT_FEED)
        self.assertIs(g._trace_repeat_verified, False,
                      "ordinary feeds must not repair the retained root shape")
        self.assertIs(g._trace_repeat_visible, False,
                      "ordinary feeds must keep the refused root hidden")
        self.assertEqual(g._trace_repeat_alpha, 1,
                         "ordinary feeds must keep native timer alpha at 1")
        self.assertIs(g._trace_repeat_same, True,
                      "ordinary feeds must retain the original root identity")
        self.assertEqual(g._trace_repeat_logs, 0,
                         "a disabled trace must stay silent across repeated feeds")
        self.assertEqual(g._trace_repeat_reasons, 0,
                         "a disabled trace must not repeat a reason")

        lua.execute(RESTORE_AND_RECOVER)
        self.assertIs(g._trace_recovered_verified, True,
                      "restoring the original setter must certify the same root")
        self.assertIs(g._trace_recovered_visible, True,
                      "restoring the original setter must show the same root")
        self.assertEqual(g._trace_recovered_alpha, 0,
                         "recovery must reacquire native timer alpha 0")
        self.assertIs(g._trace_recovered_same, True,
                      "recovery must retain the original root identity")
        self.assertEqual(g._trace_recovered_logs, 0,
                         "a disabled trace must stay silent through recovery")
        self.assertEqual(g._trace_opens, 1,
                         "all chunk loads must share the single sentinel read")
        self.assertEqual(g._trace_closes, 0,
                         "a nil sentinel handle must stay unclosed")
        self.assertEqual(g._trace_clock_reads, 0,
                         "a disabled trace must never read the diagnostic clock")

    def test_native_first_refusal_injected_parent_read_error(self):
        lua, ok, _ = _lua_with_preamble(TRACE_PREAMBLE)
        self.assertTrue(ok, "lua/hud/mission.lua must exist")
        if not ok:
            return

        lua.execute(INSTALL_PARENT_LINKS)
        lua.execute("kyohud.settings.enable_objectives = true")
        lua.execute(INSTALL_DISPATCH)
        lua.execute(MOUNT_CERTIFY)

        g = lua.globals()
        self._assert_certified(g)

        lua.execute(NATIVE_FIRST_REFUSAL)
        self.assertIs(g._native_baseline_verified, True,
                      "hidden objective source must certify the baseline")
        self.assertEqual(g._native_baseline_logs, 0,
                         "a healthy baseline must stay silent")
        self.assertIs(g._native_failure_verified, False,
                      "an injected parent read failure must refuse Mission render")
        self.assertIs(g._native_failure_visible, False,
                      "the parent read failure must hide the owned Mission root")
        self.assertEqual(g._native_failure_alpha, 1,
                         "the refusal must restore native timer alpha to 1")
        self.assertIs(g._native_failure_same, True,
                      "the refusal must retain the original root identity")
        self.assertEqual(g._native_failure_logs, 1,
                         "the first refusal must emit exactly one trace line")
        self.assertIs(g._native_failure_reason, True,
                      "the refusal line must carry "
                      "reason=native:read_error:hud:parent@1")
        self.assertEqual(g._native_parent_attempts, 1,
                         "the injected getter must be attempted exactly once")
        self.assertIs(g._native_recovery_verified, True,
                      "restoring the parent getter must certify the same root")
        self.assertIs(g._native_recovery_visible, True,
                      "restoring the parent getter must show the same root")
        self.assertEqual(g._native_recovery_alpha, 0,
                         "recovery must reacquire native timer alpha 0")
        self.assertIs(g._native_recovery_same, True,
                      "recovery must retain the original root identity")
        self.assertEqual(g._native_recovery_logs, 1,
                         "two recovery feeds must add exactly one trace line")
        self.assertIs(g._native_recovery_ok, True,
                      "the recovery line must carry reason=ok")

    def test_trace_logger_cap_survives_throwing_logger(self):
        lua, ok, _ = _lua_with_preamble(TRACE_PREAMBLE)
        self.assertTrue(ok, "lua/hud/mission.lua must exist")
        if not ok:
            return

        lua.execute(INSTALL_PARENT_LINKS)
        lua.execute(INSTALL_DISPATCH)
        lua.execute(MOUNT_CERTIFY)

        g = lua.globals()
        self._assert_certified(g)

        lua.execute(LOGGER_CAP)
        self.assertIs(g._cap_loop_ok, True,
                      "a throwing trace logger must never propagate: "
                      + str(g._cap_loop_err))
        self.assertEqual(g._cap_attempts, 24,
                         "the trace line cap must stop at exactly 24 attempts")
        self.assertIs(g._cap_verified, True,
                      "the final positive certification must stay verified")
        self.assertIs(g._cap_same, True,
                      "the retained Mission root identity must not change")
        self.assertIs(g._cap_geometry_same, True,
                      "the retained Mission root geometry must not change")

    def test_dead_root_verification_avoids_dead_diagnostic_reads(self):
        lua, ok, _ = _lua_with_preamble(TRACE_PREAMBLE)
        self.assertTrue(ok, "lua/hud/mission.lua must exist")
        if not ok:
            return

        lua.execute(INSTALL_PARENT_LINKS)
        lua.execute(INSTALL_DISPATCH)
        lua.execute(MOUNT_CERTIFY)

        g = lua.globals()
        self._assert_certified(g)

        lua.execute(DEAD_ROOT)
        self.assertIs(g._dead_root_verified, False,
                      "a known-dead retained root must fail verification")
        self.assertEqual(
            g._dead_root_attempts, 0,
            "RED: the MissionTrace diagnostic must not read getters on a "
            "known-dead retained root",
        )


if __name__ == "__main__":
    unittest.main()
