"""Single RED probe for the opt-in Stoic runtime transition trace.

The runtime opens/closes the empty root sentinel KYO_STOIC_TRACE once at load
and emits prefixed records through log(). A non-finite native radial color is
reported as an unknown native color.
"""
import re
import unittest

from test_hud_player import RUNTIME_PATH, _lua
from test_hud_player_delayed_replacement import PRELIM, SETUP

PREAMBLE = r'''
local _KYO_SENTINEL = ModPath .. "KYO_STOIC_TRACE"
KYO_TRACE_TEXT = ""
KYO_TRACE_OPENS = 0
KYO_TRACE_CLOSES = 0
local function _kyo_append(msg)
    msg = tostring(msg)
    if not msg:find("[KyoHUD][StoicTrace]", 1, true) then return end
    KYO_TRACE_TEXT = KYO_TRACE_TEXT .. msg
    if msg:sub(-1) ~= "\n" then KYO_TRACE_TEXT = KYO_TRACE_TEXT .. "\n" end
end
local _kyo_open = io.open
local _kyo_sentinel_absent = _KYO_TRACE_SENTINEL_ABSENT == true
io.open = function(path, mode, ...)
    if path ~= _KYO_SENTINEL then
        if mode == nil then return _kyo_open(path) end
        return _kyo_open(path, mode, ...)
    end
    KYO_TRACE_OPENS = KYO_TRACE_OPENS + 1
    if _kyo_sentinel_absent then return nil end
    return {
        read = function(_, fmt)
            if fmt == "*a" or fmt == "a" then return "" end
            return nil
        end,
        write = function() return true end,
        flush = function() return true end,
        close = function()
            KYO_TRACE_CLOSES = KYO_TRACE_CLOSES + 1
            return true
        end,
    }
end
local _kyo_log = log
log = function(...)
    local parts = {}
    for i = 1, select("#", ...) do parts[#parts + 1] = tostring(select(i, ...)) end
    _kyo_append(table.concat(parts, " "))
    return _kyo_log(...)
end
'''

TRACE = r'''
local chain, sent = mount_positive()
KYO_LOAD_OPENS = KYO_TRACE_OPENS
KYO_LOAD_CLOSES = KYO_TRACE_CLOSES

-- Settle the healthy zero-debt state silently before the known positive.
cd._remaining_delayed = 0
cd._health = 100
cd._armor = 50
sync_native(chain)
chain.armor:set_visible(false)
chain.health:set_visible(false)
for i = 1, 4 do RT:update(mgr, 0.1 * i, 0.1) end

-- Known positive synced debt: the runtime must own the replacement.
cd._remaining_delayed = 60
cd._health = 60
cd._armor = 25
cd._armor_max = 50
sync_native(chain)
chain.armor:set_visible(true)
chain.health:set_visible(true)
RT:update(mgr, 1.0, 0.1)
KYO_POSITIVE_P = P._root:visible()
KYO_POSITIVE_HEALTH = chain.health:alpha()

-- Drop everything emitted up to the settled positive state.
KYO_TRACE_TEXT = ""
local owned_root = P._root
local debt_prim = chain.health
local delayed_prim = chain.delayed

-- The native radial health red channel becomes non-finite (0/0).
chain.radial_health:set_color(Color(1, 0 / 0, 0, 0))
RT:update(mgr, 1.2, 0.1)
KYO_FIRST_P = P._root:visible()
KYO_FIRST_HEALTH = chain.health:alpha()

-- Ordinary monotonic frames: the unchanged first refusal must not repeat.
for i = 1, 8 do RT:update(mgr, 1.2 + 0.1 * i, 0.1) end
KYO_STABLE_P = P._root:visible()
KYO_STABLE_HEALTH = chain.health:alpha()

-- Restore the exact native color and observe the covered recovery.
local restore_offset = #KYO_TRACE_TEXT
sync_native(chain)
RT:update(mgr, 3.0, 0.1)
KYO_RESTORE_OFFSET = restore_offset
KYO_COVERED_P = P._root:visible()
KYO_COVERED_HEALTH = chain.health:alpha()
KYO_COVERED_SAME_ROOT = rawequal(P._root, owned_root)
KYO_COVERED_SAME_DEBT = rawequal(chain.health, debt_prim)
KYO_COVERED_SAME_DELAYED = rawequal(chain.delayed, delayed_prim)
KYO_FINAL_OPENS = KYO_TRACE_OPENS
KYO_FINAL_CLOSES = KYO_TRACE_CLOSES
'''

ABSENT = r'''
local chain, sent = mount_positive()

cd._remaining_delayed = 60
cd._health = 60
cd._armor = 25
sync_native(chain)
chain.armor:set_visible(true)
chain.health:set_visible(true)
RT:update(mgr, 1.0, 0.1)
KYO_ABSENT_POSITIVE_P = P._root:visible()
KYO_ABSENT_POSITIVE_HEALTH = chain.health:alpha()
KYO_ABSENT_POSITIVE_ARMOR = chain.armor:alpha()

chain.radial_health:set_color(Color(1, 0 / 0, 0, 0))
RT:update(mgr, 1.1, 0.1)
KYO_ABSENT_FIRST_P = P._root:visible()
KYO_ABSENT_FIRST_HEALTH = chain.health:alpha()
KYO_ABSENT_FIRST_ARMOR = chain.armor:alpha()

for i = 1, 4 do RT:update(mgr, 1.1 + 0.1 * i, 0.1) end
KYO_ABSENT_STABLE_P = P._root:visible()
KYO_ABSENT_STABLE_HEALTH = chain.health:alpha()
KYO_ABSENT_STABLE_ARMOR = chain.armor:alpha()

sync_native(chain)
RT:update(mgr, 1.6, 0.1)
KYO_ABSENT_COVERED_P = P._root:visible()
KYO_ABSENT_COVERED_HEALTH = chain.health:alpha()
KYO_ABSENT_COVERED_ARMOR = chain.armor:alpha()

KYO_ABSENT_TEXT = KYO_TRACE_TEXT
KYO_ABSENT_OPENS = KYO_TRACE_OPENS
KYO_ABSENT_CLOSES = KYO_TRACE_CLOSES
'''

BUDGET_RELOAD = r'''
local chain, sent = mount_positive()
local t = 1.0

cd._remaining_delayed = 60
cd._health = 60
cd._armor = 25
sync_native(chain)
chain.armor:set_visible(true)
chain.health:set_visible(true)
RT:update(mgr, t, 0.1)
t = t + 0.1

for i = 1, 70 do
    chain.radial_health:set_color(Color(1, 0 / 0, 0, 0))
    RT:update(mgr, t, 0.1)
    t = t + 0.1
    sync_native(chain)
    RT:update(mgr, t, 0.1)
    t = t + 0.1
end

KYO_BUDGET_TEXT = KYO_TRACE_TEXT
KYO_BUDGET_OPENS = KYO_TRACE_OPENS
KYO_BUDGET_CLOSES = KYO_TRACE_CLOSES

assert(loadstring(KYO_RUNTIME_SOURCE))()
KYO_RELOAD_OPENS = KYO_TRACE_OPENS
KYO_RELOAD_CLOSES = KYO_TRACE_CLOSES

for i = 1, 21 do
    chain.radial_health:set_color(Color(1, 0 / 0, 0, 0))
    RT:update(mgr, t, 0.1)
    t = t + 0.1
    sync_native(chain)
    RT:update(mgr, t, 0.1)
    t = t + 0.1
end
KYO_RELOAD_TEXT = KYO_TRACE_TEXT
'''

THROWING_LOG = r'''
local captured_log = log
KYO_LOGGER_ATTEMPTS = 0
log = function(...)
    KYO_LOGGER_ATTEMPTS = KYO_LOGGER_ATTEMPTS + 1
    error("injected logger failure")
end

local chain, sent = mount_positive()

cd._remaining_delayed = 60
cd._health = 60
cd._armor = 25
sync_native(chain)
chain.armor:set_visible(true)
chain.health:set_visible(true)
KYO_THROW_WARM_OK = pcall(RT.update, RT, mgr, 1.0, 0.1)

chain.radial_health:set_color(Color(1, 0 / 0, 0, 0))
KYO_THROW_FIRST_OK = pcall(RT.update, RT, mgr, 1.1, 0.1)
KYO_THROW_FIRST_P = P._root:visible()
KYO_THROW_FIRST_HEALTH = chain.health:alpha()

sync_native(chain)
KYO_THROW_COVER_OK = pcall(RT.update, RT, mgr, 1.2, 0.1)
KYO_THROW_COVERED_P = P._root:visible()
KYO_THROW_COVERED_HEALTH = chain.health:alpha()

KYO_THROW_ATTEMPTS = KYO_LOGGER_ATTEMPTS
KYO_THROW_CAPTURED_SPY = type(captured_log) == "function"
log = captured_log
'''

MARK = "[KyoHUD][StoicTrace]"
FIELDS = re.compile(
    r"([A-Za-z_]+)=([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)")
REASON = re.compile(r"reason=([A-Za-z_]+)")


def _records(text):
    return [MARK + part for part in text.split(MARK)[1:]]


def _fields(record):
    return {name: float(value) for name, value in FIELDS.findall(record)}


class PlayerDelayedStoicTraceTests(unittest.TestCase):
    def test_native_color_drift_emits_one_first_fail_then_covered_recovery(self):
        lua, ok = _lua(setup=SETUP + PREAMBLE)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + TRACE)
        g = lua.globals()

        self.assertEqual(int(g.KYO_LOAD_OPENS), 1,
                         "the sentinel must be opened once at runtime load")
        self.assertEqual(int(g.KYO_LOAD_CLOSES), 1,
                         "the sentinel must be closed once at runtime load")
        self.assertEqual(int(g.KYO_FINAL_OPENS), 1,
                         "no sentinel attempt may happen after runtime load")
        self.assertEqual(int(g.KYO_FINAL_CLOSES), 1,
                         "no sentinel close may happen after runtime load")

        self.assertTrue(bool(g.KYO_POSITIVE_P),
                        "the known positive debt must keep the owned player")
        self.assertAlmostEqual(float(g.KYO_POSITIVE_HEALTH), 0.0, places=5,
                               msg="the positive debt must own the health leaf")

        self.assertFalse(bool(g.KYO_FIRST_P),
                         "the native color mismatch must fall back to native priority")
        self.assertAlmostEqual(float(g.KYO_FIRST_HEALTH), 0.85, places=5,
                               msg="the mismatch must restore the native health alpha")
        self.assertFalse(bool(g.KYO_STABLE_P),
                         "repeated frames must keep the native fallback")
        self.assertAlmostEqual(float(g.KYO_STABLE_HEALTH), 0.85, places=5,
                               msg="repeated frames must keep the native health alpha")

        text = g.KYO_TRACE_TEXT
        mismatches = [r for r in _records(text)
                      if "FIRSTFAIL" in r and "reason=native_color_unknown" in r]
        self.assertEqual(len(mismatches), 1,
                         "the unchanged first refusal must be emitted exactly once")
        fields = _fields(mismatches[0])
        for name, value in (("hp", 60.0), ("hp_max", 100.0),
                            ("armor", 25.0), ("armor_max", 50.0),
                            ("debt", 60.0), ("real_hp_ratio", 0.6)):
            self.assertIn(name, fields, f"first fail must report {name}")
            self.assertAlmostEqual(fields[name], value, places=5,
                                   msg=f"first fail {name}")
        self.assertNotIn("native_hp_ratio", fields,
                         "an unknown native color must not report a native ratio")

        tail = _records(text[int(g.KYO_RESTORE_OFFSET):])
        self.assertFalse(any("reason=native_color_unknown" in r for r in tail),
                         "the restored native color must clear the refusal")
        self.assertEqual(sum("reason=covered" in r for r in tail), 1,
                         "the restored color must emit exactly one covered reason")
        self.assertTrue(bool(g.KYO_COVERED_P),
                        "the recovered replacement must keep the owned player")
        self.assertAlmostEqual(float(g.KYO_COVERED_HEALTH), 0.0, places=5,
                               msg="the recovered replacement must own the health leaf")
        self.assertTrue(bool(g.KYO_COVERED_SAME_ROOT),
                        "recovery must reuse the owned root")
        self.assertTrue(bool(g.KYO_COVERED_SAME_DEBT),
                        "recovery must reuse the debt primitive")
        self.assertTrue(bool(g.KYO_COVERED_SAME_DELAYED),
                        "recovery must reuse the delayed container")


class PlayerDelayedStoicTraceSafetyTests(unittest.TestCase):
    def test_absent_sentinel_disables_trace_without_changing_fallback_alphas(self):
        lua, ok = _lua(setup=SETUP + "_KYO_TRACE_SENTINEL_ABSENT = true\n" + PREAMBLE)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + ABSENT)
        g = lua.globals()

        self.assertEqual(int(g.KYO_ABSENT_OPENS), 1,
                         "an absent sentinel must still be probed exactly once")
        self.assertEqual(int(g.KYO_ABSENT_CLOSES), 0,
                         "an absent sentinel must not be closed")
        self.assertEqual(_records(g.KYO_ABSENT_TEXT), [],
                         "an absent sentinel must not emit any trace record")

        self.assertTrue(bool(g.KYO_ABSENT_POSITIVE_P),
                        "the neutral positive must keep the owned player")
        self.assertAlmostEqual(float(g.KYO_ABSENT_POSITIVE_HEALTH), 0.0, places=5,
                               msg="the neutral positive must own the health leaf")
        self.assertAlmostEqual(float(g.KYO_ABSENT_POSITIVE_ARMOR), 0.0, places=5,
                               msg="the neutral positive must own the armor leaf")
        self.assertFalse(bool(g.KYO_ABSENT_FIRST_P),
                         "a native color mismatch must fall back to native priority")
        self.assertAlmostEqual(float(g.KYO_ABSENT_FIRST_HEALTH), 0.85, places=5,
                               msg="a mismatch must restore the native health alpha")
        self.assertAlmostEqual(float(g.KYO_ABSENT_FIRST_ARMOR), 0.65, places=5,
                               msg="a mismatch must restore the native armor alpha")
        self.assertFalse(bool(g.KYO_ABSENT_STABLE_P),
                         "repeated frames must keep the native fallback")
        self.assertAlmostEqual(float(g.KYO_ABSENT_STABLE_HEALTH), 0.85, places=5,
                               msg="repeated frames must keep the native health alpha")
        self.assertAlmostEqual(float(g.KYO_ABSENT_STABLE_ARMOR), 0.65, places=5,
                               msg="repeated frames must keep the native armor alpha")
        self.assertTrue(bool(g.KYO_ABSENT_COVERED_P),
                        "the recovered replacement must keep the owned player")
        self.assertAlmostEqual(float(g.KYO_ABSENT_COVERED_HEALTH), 0.0, places=5,
                               msg="the recovered replacement must own the health leaf")
        self.assertAlmostEqual(float(g.KYO_ABSENT_COVERED_ARMOR), 0.0, places=5,
                               msg="the recovered replacement must own the armor leaf")

    def test_enabled_trace_budget_caps_and_survives_runtime_chunk_reload(self):
        lua, ok = _lua(setup=SETUP + PREAMBLE)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.globals().KYO_RUNTIME_SOURCE = RUNTIME_PATH.read_text(
            encoding="utf-8-sig")
        lua.execute(PRELIM + BUDGET_RELOAD)
        g = lua.globals()

        records = _records(g.KYO_BUDGET_TEXT)
        ordinary = [record for record in records if "PRIORITY" not in record]
        self.assertEqual(len(ordinary), 40,
                         "the trace budget must cap at exactly forty records")
        reasons = [REASON.search(record).group(1) for record in ordinary]
        self.assertIn("native_color_unknown", reasons,
                      "the unknown-native-color cycle must be traced")
        self.assertIn("covered", reasons,
                      "the covered cycle must be traced")
        for left, right in zip(reasons, reasons[1:]):
            self.assertNotEqual(left, right,
                                "stable repeats must not duplicate a trace reason")

        self.assertEqual(int(g.KYO_BUDGET_OPENS), 1,
                         "the sentinel must be opened once at runtime load")
        self.assertEqual(int(g.KYO_BUDGET_CLOSES), 1,
                         "the sentinel must be closed once at runtime load")
        self.assertEqual(int(g.KYO_RELOAD_OPENS), int(g.KYO_BUDGET_OPENS),
                         "a runtime chunk reload must not re-read the sentinel")
        self.assertEqual(int(g.KYO_RELOAD_CLOSES), int(g.KYO_BUDGET_CLOSES),
                         "a runtime chunk reload must not close the sentinel again")
        self.assertEqual(g.KYO_RELOAD_TEXT, g.KYO_BUDGET_TEXT,
                         "a runtime chunk reload must not reset the trace budget")
        reloaded = _records(g.KYO_RELOAD_TEXT)
        self.assertEqual(len([record for record in reloaded if "PRIORITY" not in record]), 40,
                         "the reloaded runtime must keep the capped record count")
        self.assertLessEqual(len([record for record in reloaded if "PRIORITY" in record]), 16,
                             "the priority trace budget must remain capped")

    def test_throwing_logger_is_contained_and_behavior_is_unchanged(self):
        lua, ok = _lua(setup=SETUP + PREAMBLE)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + THROWING_LOG)
        g = lua.globals()

        self.assertTrue(bool(g.KYO_THROW_WARM_OK),
                        "the throwing logger must not escape the warm frame")
        self.assertTrue(bool(g.KYO_THROW_FIRST_OK),
                        "the throwing logger must not escape the mismatch frame")
        self.assertTrue(bool(g.KYO_THROW_COVER_OK),
                        "the throwing logger must not escape the recovery frame")
        self.assertGreater(int(g.KYO_THROW_ATTEMPTS), 0,
                           "the throwing logger must be attempted")
        self.assertTrue(bool(g.KYO_THROW_CAPTURED_SPY),
                        "the captured logger spy must be a function")

        self.assertFalse(bool(g.KYO_THROW_FIRST_P),
                         "a throwing logger must not change the native fallback")
        self.assertAlmostEqual(float(g.KYO_THROW_FIRST_HEALTH), 0.85, places=5,
                               msg="a throwing logger must not change the fallback alpha")
        self.assertTrue(bool(g.KYO_THROW_COVERED_P),
                        "a throwing logger must not change the owned recovery")
        self.assertAlmostEqual(float(g.KYO_THROW_COVERED_HEALTH), 0.0, places=5,
                               msg="a throwing logger must not change the recovery alpha")


if __name__ == "__main__":
    unittest.main()
