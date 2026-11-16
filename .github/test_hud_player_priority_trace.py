"""RED contract for native-priority provenance in the Stoic trace.

The runtime priority pass must report, once per transition, the first native
blocker it actually attributes:

  [KyoHUD][StoicTrace] PRIORITY cause=overlap_player_union
      leaf=teammate_panels[<PP>]/condition_timer
      native_bounds=x,y,w,h owned_bounds=x,y,w,h slot=<PP> local=true

Bounds are full tuples in the common parent panel coordinates, derived from the
real primitive geometry; the slot is read from the live teammate ownership, not
hardcoded. Unknown visibility/alpha/geometry/player-union keep the native
fallback and restore the exact .65/.85 delayed leaves. Stable frames do not
repeat, recovery allows another transition, and the PRIORITY budget is a hard
sixteen lines across a runtime chunk reload, independent of the ordinary trace
budget of forty. A disabled trace emits no PRIORITY line and walks no native
names; diagnostic logger failures stay contained.

RED: the runtime priority pass is currently silent.
"""
import re
import unittest

from test_hud_player import RUNTIME_PATH, _lua
from test_hud_player_delayed_trace import MARK, PREAMBLE, _records
from test_hud_player_delayed_replacement import PRELIM, SETUP

CAUSE = re.compile(r"\bcause=([A-Za-z_]+)")
LEAF = re.compile(r"\bleaf=(\S+)")
SLOT = re.compile(r"\bslot=(\d+)\b")
LOCAL = re.compile(r"\blocal=(true|false)\b")
TUPLE = re.compile(
    r"\b(native_bounds|owned_bounds)="
    r"([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*,"
    r"([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)")


def _priority_records(text):
    return [record for record in _records(text)
            if record.startswith(MARK + " PRIORITY")]


def _tuple_fields(record):
    return {match.group(1): tuple(float(match.group(i)) for i in range(2, 6))
            for match in TUPLE.finditer(record)}


GEOMETRY = r'''
local function bounds_in_common(panel)
    local COMMON = RT._parent_panel
    if not panel or not alive(panel) or not COMMON or not alive(COMMON) then
        return nil
    end
    if panel == COMMON then
        return {x = 0, y = 0, w = panel:w(), h = panel:h()}
    end
    local ox, oy = 0, 0
    local current = panel
    for _ = 1, 6 do
        ox = ox + current:x()
        oy = oy + current:y()
        local parent = current:parent()
        if not parent then return nil end
        if parent == COMMON then
            return {x = ox, y = oy, w = panel:w(), h = panel:h()}
        end
        current = parent
    end
    return nil
end

local function chain_visible(panel)
    if not panel or not alive(panel) then return false end
    local current = panel
    for _ = 1, 6 do
        if current:visible() ~= true then return false end
        local parent = current:parent()
        if not parent then return true end
        current = parent
    end
    return true
end

local function chain_alpha(panel)
    if not panel or not alive(panel) then return 0 end
    local cumulative = 1
    local current = panel
    for _ = 1, 6 do
        local alpha = current:alpha()
        if type(alpha) ~= "number" or alpha ~= alpha then return nil end
        if alpha <= 0 then return 0 end
        cumulative = cumulative * alpha
        local parent = current:parent()
        if not parent then break end
        current = parent
    end
    return cumulative
end

local function union_bounds(P)
    local union
    local function add(prim, text_only)
        if not prim or not alive(prim) then return end
        if chain_visible(prim) ~= true then return end
        local alpha = chain_alpha(prim)
        if alpha == nil or alpha <= 0 then return end
        if text_only then
            local ok, text = pcall(function() return prim:text() end)
            if not ok or type(text) ~= "string" or text == "" then return end
        end
        local bounds = bounds_in_common(prim)
        if not bounds then return end
        if not union then
            union = {x = bounds.x, y = bounds.y, w = bounds.w, h = bounds.h}
        else
            local x1 = math.min(union.x, bounds.x)
            local y1 = math.min(union.y, bounds.y)
            local x2 = math.max(union.x + union.w, bounds.x + bounds.w)
            local y2 = math.max(union.y + union.h, bounds.y + bounds.h)
            union = {x = x1, y = y1, w = x2 - x1, h = y2 - y1}
        end
    end
    add(P._gauge and P._gauge.root)
    for _, fname in ipairs({"_downs_bg", "_downs_text", "_downs_icon",
        "_h5_id_label", "_condition_text"}) do
        add(P[fname], fname == "_condition_text" or fname == "_h5_id_label")
    end
    return union
end

local function export_bounds(prefix, bounds)
    if not bounds then
        _G[prefix .. "_MISSING"] = true
        return
    end
    _G[prefix .. "_X"] = bounds.x
    _G[prefix .. "_Y"] = bounds.y
    _G[prefix .. "_W"] = bounds.w
    _G[prefix .. "_H"] = bounds.h
end

local function make_condition_timer(chain)
    local timer = chain.entry:panel({name = "condition_timer"})
    timer:set_shape(0, 0, chain.pw, chain.ph)
    timer:set_visible(true)
    timer:set_alpha(1)
    return timer
end

local function slot_for_entry(entry)
    for slot, state in pairs(mgr._teammate_panels) do
        if type(state) == "table" and state._panel == entry then
            return tostring(slot)
        end
    end
    return "?"
end
'''

PRIMARY = r'''
local chain, sent = mount_positive()
KYO_ROOT_BEFORE = P._root
KYO_ARMOR_BEFORE = chain.armor
KYO_HEALTH_BEFORE = chain.health
RT:update(mgr, 1.0, 0.1)
KYO_WARM_VISIBLE = P._root:visible()
KYO_WARM_ARMOR = chain.armor:alpha()
KYO_WARM_HEALTH = chain.health:alpha()
KYO_TRACE_TEXT = ""

local timer = make_condition_timer(chain)
KYO_PP = slot_for_entry(chain.entry)
export_bounds("KYO_NATIVE", bounds_in_common(timer))
export_bounds("KYO_OWNED", union_bounds(P))

local name_calls = 0
local function spy_name(panel)
    local original = panel.name
    panel.name = function(self)
        name_calls = name_calls + 1
        return original(self)
    end
end
spy_name(timer)
spy_name(chain.entry)

RT:update(mgr, 1.1, 0.1)
KYO_NAME_CALLS = name_calls
KYO_AFTER_FIRST_TEXT = KYO_TRACE_TEXT
KYO_FIRST_VISIBLE = P._root:visible()
KYO_FIRST_ARMOR = chain.armor:alpha()
KYO_FIRST_HEALTH = chain.health:alpha()
KYO_FIRST_SAME_ROOT = rawequal(P._root, KYO_ROOT_BEFORE)
KYO_FIRST_SAME_ARMOR = rawequal(chain.armor, KYO_ARMOR_BEFORE)
KYO_FIRST_SAME_HEALTH = rawequal(chain.health, KYO_HEALTH_BEFORE)

for i = 1, 8 do RT:update(mgr, 1.1 + 0.1 * i, 0.1) end
KYO_STABLE_TEXT = KYO_TRACE_TEXT
KYO_STABLE_VISIBLE = P._root:visible()

chain.entry:remove(timer)
RT:update(mgr, 3.0, 0.1)
KYO_RECOVERY_TEXT = KYO_TRACE_TEXT
KYO_RECOVERY_VISIBLE = P._root:visible()
KYO_RECOVERY_ARMOR = chain.armor:alpha()
KYO_RECOVERY_HEALTH = chain.health:alpha()
KYO_RECOVERY_SAME_ROOT = rawequal(P._root, KYO_ROOT_BEFORE)
KYO_RECOVERY_SAME_ARMOR = rawequal(chain.armor, KYO_ARMOR_BEFORE)
KYO_RECOVERY_SAME_HEALTH = rawequal(chain.health, KYO_HEALTH_BEFORE)

local second_timer = make_condition_timer(chain)
RT:update(mgr, 3.1, 0.1)
KYO_SECOND_TEXT = KYO_TRACE_TEXT
KYO_SECOND_VISIBLE = P._root:visible()
KYO_SECOND_ARMOR = chain.armor:alpha()
KYO_SECOND_HEALTH = chain.health:alpha()
'''

FIRST_CAUSE = r'''
local chain, sent = mount_positive()
RT:update(mgr, 1.0, 0.1)
KYO_TRACE_TEXT = ""

local timer = make_condition_timer(chain)
KYO_PP = slot_for_entry(chain.entry)
export_bounds("KYO_NATIVE", bounds_in_common(timer))
export_bounds("KYO_OWNED", union_bounds(P))

-- Post-release priority runs again with the exact delayed leaves restored to
-- .65/.85; those leaves are inspected before condition_timer on the second
-- pass and must not replace the first cause captured on the first pass.
RT:update(mgr, 1.1, 0.1)
KYO_CAUSE_TEXT = KYO_TRACE_TEXT
KYO_CAUSE_VISIBLE = P._root:visible()
KYO_CAUSE_ARMOR = chain.armor:alpha()
KYO_CAUSE_HEALTH = chain.health:alpha()

RT:update(mgr, 1.2, 0.1)
KYO_CAUSE_STABLE_TEXT = KYO_TRACE_TEXT
'''

UNKNOWN = r'''
local chain, sent = mount_positive()
KYO_ROOT_BEFORE = P._root
KYO_ARMOR_BEFORE = chain.armor
KYO_HEALTH_BEFORE = chain.health
RT:update(mgr, 1.0, 0.1)
KYO_WARM_ARMOR = chain.armor:alpha()
KYO_WARM_HEALTH = chain.health:alpha()
KYO_TRACE_TEXT = ""

local timer = make_condition_timer(chain)
KYO_PP = slot_for_entry(chain.entry)
local mode = KYO_UNKNOWN_MODE
if mode == "unknown_visibility" then
    timer.visible = function() error("unknown visibility") end
elseif mode == "unknown_alpha" then
    timer.alpha = function() error("unknown alpha") end
elseif mode == "unknown_geometry" then
    timer.x = function() error("unknown geometry") end
elseif mode == "unknown_player_union" then
    KYO_UNION_SLOT = slot_for_entry(sent.remote)
    KYO_UNION_LEAF = "teammate_panels[" .. KYO_UNION_SLOT .. "]"
        .. "/player/radial_health_panel/radial_delayed_damage/radial_delayed_damage_armor"
    P._gauge.root.alpha = function() error("unknown player union") end
end

RT:update(mgr, 1.1, 0.1)
KYO_UNKNOWN_TEXT = KYO_TRACE_TEXT
KYO_UNKNOWN_VISIBLE = P._root:visible()
KYO_UNKNOWN_ARMOR = chain.armor:alpha()
KYO_UNKNOWN_HEALTH = chain.health:alpha()
KYO_UNKNOWN_SAME_ROOT = rawequal(P._root, KYO_ROOT_BEFORE)
KYO_UNKNOWN_SAME_ARMOR = rawequal(chain.armor, KYO_ARMOR_BEFORE)
KYO_UNKNOWN_SAME_HEALTH = rawequal(chain.health, KYO_HEALTH_BEFORE)

if mode == "unknown_visibility" then
    timer.visible = nil
elseif mode == "unknown_alpha" then
    timer.alpha = nil
elseif mode == "unknown_geometry" then
    timer.x = nil
elseif mode == "unknown_player_union" then
    P._gauge.root.alpha = nil
end
timer:set_visible(false)

RT:update(mgr, 1.2, 0.1)
KYO_RECOVER_TEXT = KYO_TRACE_TEXT
KYO_RECOVER_VISIBLE = P._root:visible()
KYO_RECOVER_ARMOR = chain.armor:alpha()
KYO_RECOVER_HEALTH = chain.health:alpha()
KYO_RECOVER_SAME_ROOT = rawequal(P._root, KYO_ROOT_BEFORE)
KYO_RECOVER_SAME_ARMOR = rawequal(chain.armor, KYO_ARMOR_BEFORE)
KYO_RECOVER_SAME_HEALTH = rawequal(chain.health, KYO_HEALTH_BEFORE)
'''

DISABLED = r'''
local chain, sent = mount_positive()
RT:update(mgr, 1.0, 0.1)
KYO_TRACE_TEXT = ""

local timer = make_condition_timer(chain)
local name_calls = 0
local function spy_name(panel)
    local original = panel.name
    panel.name = function(self)
        name_calls = name_calls + 1
        return original(self)
    end
end
spy_name(timer)
spy_name(chain.entry)

RT:update(mgr, 1.1, 0.1)
KYO_NAME_CALLS = name_calls
KYO_DISABLED_TEXT = KYO_TRACE_TEXT
KYO_DISABLED_VISIBLE = P._root:visible()
KYO_DISABLED_ARMOR = chain.armor:alpha()
KYO_DISABLED_HEALTH = chain.health:alpha()
'''

LOGGER_FAILURE = r'''
local captured_log = log
KYO_LOGGER_ATTEMPTS = 0
log = function(...)
    KYO_LOGGER_ATTEMPTS = KYO_LOGGER_ATTEMPTS + 1
    error("injected priority logger failure")
end

local chain, sent = mount_positive()
KYO_WARM_OK = pcall(RT.update, RT, mgr, 1.0, 0.1)
local timer = make_condition_timer(chain)
KYO_PRIORITY_OK = pcall(RT.update, RT, mgr, 1.1, 0.1)
KYO_THROW_VISIBLE = P._root:visible()
KYO_THROW_ARMOR = chain.armor:alpha()
KYO_THROW_HEALTH = chain.health:alpha()
KYO_THROW_ATTEMPTS = KYO_LOGGER_ATTEMPTS
KYO_THROW_CAPTURED_SPY = type(captured_log) == "function"
log = captured_log
'''

BUDGET = r'''
local chain, sent = mount_positive()
RT:update(mgr, 1.0, 0.1)

-- Exhaust the ordinary forty-line budget without creating a native blocker:
-- the delayed leaves are leased while the player is mounted, and the priority
-- pass returns early while the player is unmounted.
local t = 1.1
for _ = 1, 30 do
    kyohud.settings.enable_player = false
    RT:update(mgr, t, 0.1)
    t = t + 0.1
    kyohud.settings.enable_player = true
    RT:update(mgr, t, 0.1)
    t = t + 0.1
end
KYO_ORDINARY_TEXT = KYO_TRACE_TEXT
KYO_TRACE_TEXT = ""

local timer = make_condition_timer(chain)
KYO_PP = slot_for_entry(chain.entry)
RT:update(mgr, t, 0.1)
t = t + 0.1
KYO_AFTER_CAP_TEXT = KYO_TRACE_TEXT

for _ = 1, 20 do
    timer:set_visible(true)
    RT:update(mgr, t, 0.1)
    t = t + 0.1
    timer:set_visible(false)
    RT:update(mgr, t, 0.1)
    t = t + 0.1
end
KYO_CAPPED_TEXT = KYO_TRACE_TEXT

assert(loadstring(KYO_RUNTIME_SOURCE))()
KYO_RELOAD_START_TEXT = KYO_TRACE_TEXT

for _ = 1, 5 do
    timer:set_visible(true)
    RT:update(mgr, t, 0.1)
    t = t + 0.1
    timer:set_visible(false)
    RT:update(mgr, t, 0.1)
    t = t + 0.1
end
KYO_FINAL_TEXT = KYO_TRACE_TEXT
'''


class PriorityTraceContractTests(unittest.TestCase):
    def _assert_bounds(self, record, g):
        fields = _tuple_fields(record)
        self.assertIn("native_bounds", fields,
                      "PRIORITY must record the full native bounds tuple")
        self.assertIn("owned_bounds", fields,
                      "PRIORITY must record the full owned bounds tuple")
        for key, prefix in (("native_bounds", "KYO_NATIVE"),
                            ("owned_bounds", "KYO_OWNED")):
            self.assertFalse(bool(g[prefix + "_MISSING"]),
                             f"{key} must be derived from real geometry")
            expected = tuple(float(g[f"{prefix}_{axis}"])
                             for axis in ("X", "Y", "W", "H"))
            actual = fields[key]
            self.assertEqual(len(actual), 4, f"{key} must be x,y,w,h")
            for index, (value, want) in enumerate(zip(actual, expected)):
                self.assertAlmostEqual(
                    value, want, places=5,
                    msg=f"{key} component {index} must match actual geometry")

    def _assert_unknown_bounds(self, record, field):
        fields = _tuple_fields(record)
        self.assertNotIn(field, fields,
                         f"{field} must not fabricate a numeric tuple")
        self.assertRegex(record, rf"\b{field}=unknown\b",
                         f"{field} must be reported as explicitly unknown")

    def _assert_contract(self, record, slot, leaf_tail, local_value="true"):
        cause = CAUSE.search(record)
        self.assertIsNotNone(cause, "PRIORITY must report a cause")
        self.assertEqual(cause.group(1), "overlap_player_union")
        leaf = LEAF.search(record)
        self.assertIsNotNone(leaf, "PRIORITY must report the blocking leaf")
        self.assertEqual(leaf.group(1),
                         f"teammate_panels[{slot}]/{leaf_tail}")
        recorded_slot = SLOT.search(record)
        self.assertIsNotNone(recorded_slot,
                             "PRIORITY must record the ownership slot")
        self.assertEqual(recorded_slot.group(1), slot)
        recorded_local = LOCAL.search(record)
        self.assertIsNotNone(recorded_local,
                             "PRIORITY must record the local overlap flag")
        self.assertEqual(recorded_local.group(1), local_value)

    def test_positive_overlap_reports_exact_tuples_then_stable_and_transitions(self):
        lua, ok = _lua(setup=SETUP + PREAMBLE)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + GEOMETRY + PRIMARY)
        g = lua.globals()
        slot = str(g.KYO_PP)

        self.assertTrue(bool(g.KYO_WARM_VISIBLE),
                        "precondition: certified positive debt keeps the player")
        self.assertAlmostEqual(float(g.KYO_WARM_ARMOR), 0.0, places=5)
        self.assertAlmostEqual(float(g.KYO_WARM_HEALTH), 0.0, places=5)
        self.assertEqual(int(g.KYO_NAME_CALLS), 0,
                         "PRIORITY must use known semantic paths, not name walking")

        first = _priority_records(g.KYO_AFTER_FIRST_TEXT)
        self.assertEqual(len(first), 1,
                         "the first overlapping native leaf must emit one PRIORITY")
        self._assert_contract(first[0], slot, "condition_timer")
        self._assert_bounds(first[0], g)
        self.assertFalse(bool(g.KYO_FIRST_VISIBLE),
                         "the overlapping native leaf must hide the local player")
        self.assertAlmostEqual(float(g.KYO_FIRST_ARMOR), 0.65, places=5,
                               msg="the native fallback must restore the exact armor alpha")
        self.assertAlmostEqual(float(g.KYO_FIRST_HEALTH), 0.85, places=5,
                               msg="the native fallback must restore the exact health alpha")
        self.assertTrue(bool(g.KYO_FIRST_SAME_ROOT),
                        "the fallback must not replace the owned root")
        self.assertTrue(bool(g.KYO_FIRST_SAME_ARMOR),
                        "the fallback must not replace the armor leaf")
        self.assertTrue(bool(g.KYO_FIRST_SAME_HEALTH),
                        "the fallback must not replace the health leaf")

        stable = _priority_records(g.KYO_STABLE_TEXT)
        self.assertEqual(len(stable), len(first),
                         "stable frames must not repeat the PRIORITY line")
        self.assertFalse(bool(g.KYO_STABLE_VISIBLE),
                         "stable frames must keep the native fallback")

        self.assertEqual(len(_priority_records(g.KYO_RECOVERY_TEXT)), len(first),
                         "recovery must not emit a new PRIORITY line")
        self.assertTrue(bool(g.KYO_RECOVERY_VISIBLE),
                        "removing the blocker must recover the local player")
        self.assertAlmostEqual(float(g.KYO_RECOVERY_ARMOR), 0.0, places=5,
                               msg="recovery must reacquire the armor leaf")
        self.assertAlmostEqual(float(g.KYO_RECOVERY_HEALTH), 0.0, places=5,
                               msg="recovery must reacquire the health leaf")
        self.assertTrue(bool(g.KYO_RECOVERY_SAME_ROOT),
                        "recovery must reuse the owned root")
        self.assertTrue(bool(g.KYO_RECOVERY_SAME_ARMOR),
                        "recovery must reuse the armor leaf")
        self.assertTrue(bool(g.KYO_RECOVERY_SAME_HEALTH),
                        "recovery must reuse the health leaf")

        second = _priority_records(g.KYO_SECOND_TEXT)
        self.assertEqual(len(second), len(first) + 1,
                         "recovery must allow another PRIORITY transition")
        self._assert_contract(second[-1], slot, "condition_timer")
        self.assertFalse(bool(g.KYO_SECOND_VISIBLE),
                         "the second overlap must hide the local player again")
        self.assertAlmostEqual(float(g.KYO_SECOND_ARMOR), 0.65, places=5)
        self.assertAlmostEqual(float(g.KYO_SECOND_HEALTH), 0.85, places=5)

    def test_first_cause_survives_the_post_release_priority_pass(self):
        lua, ok = _lua(setup=SETUP + PREAMBLE)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + GEOMETRY + FIRST_CAUSE)
        g = lua.globals()
        slot = str(g.KYO_PP)

        records = _priority_records(g.KYO_CAUSE_TEXT)
        self.assertEqual(len(records), 1,
                         "one frame must report a single first PRIORITY cause")
        self._assert_contract(records[0], slot, "condition_timer")
        self._assert_bounds(records[0], g)
        self.assertFalse(bool(g.KYO_CAUSE_VISIBLE),
                         "the first cause must hide the local player")
        self.assertAlmostEqual(float(g.KYO_CAUSE_ARMOR), 0.65, places=5)
        self.assertAlmostEqual(float(g.KYO_CAUSE_HEALTH), 0.85, places=5)

        stable = _priority_records(g.KYO_CAUSE_STABLE_TEXT)
        self.assertEqual(len(stable), 1,
                         "the later blocker must not replace the first cause")
        self._assert_contract(stable[0], slot, "condition_timer")

    def test_unknown_inputs_keep_fallback_and_restore_the_same_roots(self):
        modes = ("unknown_visibility", "unknown_alpha",
                 "unknown_geometry", "unknown_player_union")
        for mode in modes:
            with self.subTest(mode=mode):
                lua, ok = _lua(setup=SETUP + PREAMBLE)
                self.assertTrue(ok, "lua/hud/player.lua must exist")
                if not ok:
                    continue

                lua.globals().KYO_UNKNOWN_MODE = mode
                lua.execute(PRELIM + GEOMETRY + UNKNOWN)
                g = lua.globals()
                slot = str(g.KYO_PP)

                self.assertAlmostEqual(float(g.KYO_WARM_ARMOR), 0.0, places=5)
                self.assertAlmostEqual(float(g.KYO_WARM_HEALTH), 0.0, places=5)
                records = _priority_records(g.KYO_UNKNOWN_TEXT)
                self.assertEqual(len(records), 1,
                                 f"{mode} must report one PRIORITY classification")
                cause = CAUSE.search(records[0])
                self.assertIsNotNone(cause, f"{mode} must report a cause")
                observed = cause.group(1)
                leaf = LEAF.search(records[0])
                self.assertIsNotNone(leaf, f"{mode} must report the leaf")
                if mode == "unknown_player_union":
                    # The damaged owned alpha fails certification and restores
                    # the delayed leaves; the first real blocker is therefore
                    # the remote native delayed armor in teammate slot 1.
                    self.assertEqual(observed, "unknown_player_union",
                                     f"{mode} must report its own cause")
                    self.assertEqual(leaf.group(1), g.KYO_UNION_LEAF,
                                     f"{mode} must report the remote native leaf")
                    recorded_slot = SLOT.search(records[0])
                    self.assertIsNotNone(
                        recorded_slot,
                        f"{mode} must record the remote ownership slot")
                    self.assertEqual(recorded_slot.group(1),
                                     str(g.KYO_UNION_SLOT))
                    recorded_local = LOCAL.search(records[0])
                    self.assertIsNotNone(recorded_local,
                                         f"{mode} must record the local flag")
                    self.assertEqual(recorded_local.group(1), "true")
                else:
                    self.assertEqual(observed, mode,
                                     f"{mode} must report its own cause")
                    self.assertEqual(leaf.group(1),
                                     f"teammate_panels[{slot}]/condition_timer")
                relevant = ("owned_bounds"
                            if mode == "unknown_player_union"
                            else "native_bounds")
                self._assert_unknown_bounds(records[0], relevant)
                self.assertFalse(bool(g.KYO_UNKNOWN_VISIBLE),
                                 f"{mode} must keep the native fallback")
                self.assertAlmostEqual(
                    float(g.KYO_UNKNOWN_ARMOR), 0.65, places=5,
                    msg=f"{mode} must restore the exact armor alpha")
                self.assertAlmostEqual(
                    float(g.KYO_UNKNOWN_HEALTH), 0.85, places=5,
                    msg=f"{mode} must restore the exact health alpha")
                self.assertTrue(bool(g.KYO_UNKNOWN_SAME_ROOT),
                                f"{mode} must not replace the owned root")
                self.assertTrue(bool(g.KYO_UNKNOWN_SAME_ARMOR),
                                f"{mode} must not replace the armor leaf")
                self.assertTrue(bool(g.KYO_UNKNOWN_SAME_HEALTH),
                                f"{mode} must not replace the health leaf")

                recovered = _priority_records(g.KYO_RECOVER_TEXT)
                self.assertEqual(recovered, records,
                                 f"{mode} recovery must retain the same "
                                 f"single PRIORITY event")
                self.assertTrue(bool(g.KYO_RECOVER_VISIBLE),
                                f"{mode} recovery must show the local player")
                self.assertAlmostEqual(float(g.KYO_RECOVER_ARMOR), 0.0, places=5)
                self.assertAlmostEqual(float(g.KYO_RECOVER_HEALTH), 0.0, places=5)
                self.assertTrue(bool(g.KYO_RECOVER_SAME_ROOT),
                                f"{mode} recovery must reuse the owned root")
                self.assertTrue(bool(g.KYO_RECOVER_SAME_ARMOR),
                                f"{mode} recovery must reuse the armor leaf")
                self.assertTrue(bool(g.KYO_RECOVER_SAME_HEALTH),
                                f"{mode} recovery must reuse the health leaf")

    def test_disabled_trace_emits_no_priority_and_no_name_walk(self):
        lua, ok = _lua(
            setup=SETUP + "_KYO_TRACE_SENTINEL_ABSENT = true\n" + PREAMBLE)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + GEOMETRY + DISABLED)
        g = lua.globals()

        self.assertEqual(_priority_records(g.KYO_DISABLED_TEXT), [],
                         "a disabled trace must not emit PRIORITY")
        self.assertEqual(int(g.KYO_NAME_CALLS), 0,
                         "a disabled trace must add no diagnostic name walk")
        self.assertFalse(bool(g.KYO_DISABLED_VISIBLE),
                         "a disabled trace must keep the native fallback")
        self.assertAlmostEqual(float(g.KYO_DISABLED_ARMOR), 0.65, places=5)
        self.assertAlmostEqual(float(g.KYO_DISABLED_HEALTH), 0.85, places=5)

    def test_throwing_logger_is_contained_during_priority(self):
        lua, ok = _lua(setup=SETUP + PREAMBLE)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.execute(PRELIM + GEOMETRY + LOGGER_FAILURE)
        g = lua.globals()

        self.assertTrue(bool(g.KYO_WARM_OK),
                        "the throwing logger must not escape the warm frame")
        self.assertTrue(bool(g.KYO_PRIORITY_OK),
                        "the throwing logger must not escape the PRIORITY frame")
        self.assertGreater(int(g.KYO_THROW_ATTEMPTS), 0,
                           "the logger must actually be attempted")
        self.assertTrue(bool(g.KYO_THROW_CAPTURED_SPY),
                        "the captured logger must remain a function")
        self.assertFalse(bool(g.KYO_THROW_VISIBLE),
                         "a throwing logger must not change the native fallback")
        self.assertAlmostEqual(float(g.KYO_THROW_ARMOR), 0.65, places=5)
        self.assertAlmostEqual(float(g.KYO_THROW_HEALTH), 0.85, places=5)

    def test_priority_budget_is_sixteen_across_reload_and_independent_of_ordinary(self):
        lua, ok = _lua(setup=SETUP + PREAMBLE)
        self.assertTrue(ok, "lua/hud/player.lua must exist")
        if not ok:
            return

        lua.globals().KYO_RUNTIME_SOURCE = RUNTIME_PATH.read_text(
            encoding="utf-8-sig")
        lua.execute(PRELIM + GEOMETRY + BUDGET)
        g = lua.globals()

        ordinary = [record for record in _records(g.KYO_ORDINARY_TEXT)
                    if not record.startswith(MARK + " PRIORITY")]
        self.assertEqual(len(ordinary), 40,
                         "precondition: the ordinary trace budget must be exhausted")
        self.assertEqual(_priority_records(g.KYO_ORDINARY_TEXT), [],
                         "ordinary budget setup must not emit PRIORITY")

        after_cap = _priority_records(g.KYO_AFTER_CAP_TEXT)
        self.assertEqual(len(after_cap), 1,
                         "ordinary budget exhaustion must not suppress PRIORITY")
        self._assert_contract(after_cap[0], str(g.KYO_PP), "condition_timer")

        capped = _priority_records(g.KYO_CAPPED_TEXT)
        self.assertEqual(len(capped), 16,
                         "the PRIORITY budget must be a hard sixteen lines")
        self.assertEqual(_priority_records(g.KYO_RELOAD_START_TEXT), capped,
                         "a runtime chunk reload must preserve the PRIORITY budget")

        final = _priority_records(g.KYO_FINAL_TEXT)
        self.assertLessEqual(len(final), 16,
                             "a runtime chunk reload must not reset the PRIORITY cap")
        self.assertEqual(len(final), len(capped),
                         "exhausted PRIORITY budget must not emit after reload")
        self.assertEqual(g.KYO_FINAL_TEXT, g.KYO_RELOAD_START_TEXT,
                         "a reloaded runtime must not replay capped PRIORITY lines")


if __name__ == "__main__":
    unittest.main()
