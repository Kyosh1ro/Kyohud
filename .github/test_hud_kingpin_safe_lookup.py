"""Lot 6 RED: the equipment `safe_call` lookup must be reusable top-level Lua.

The literal production helper at lua/hud/equipment.lua allocates a fresh
anonymous closure for `obj[method]` on every guarded call. This suite extracts
the real upvalue through `_fresh_cooldown` (residual wrapper `original`, then
the real `safe_call`) and observes the actual `debug.sethook` hook invocations
while a stable native radial is published after a positive Kingpin activation.

No production helper, renderer or source line number is duplicated or replaced
here: the tests read the real chunk and exercise the actual upvalues.
"""
import unittest

from test_hud_kingpin_active import KINGPIN_ACTIVATE, kingpin_lua


# Extract the real safe_call upvalue: _E._fresh_cooldown is the residual wrapper
# installed over the fresh method, whose upvalue is `original`
# (`_fresh_cooldown`), whose own upvalues include the literal `safe_call`.
EXTRACT_SAFE_CALL = r'''
local function scan_upvalue(fn, wanted)
    if type(fn) ~= "function" then return nil end
    local n = 1
    while true do
        local name, value = debug.getupvalue(fn, n)
        if name == nil then return nil end
        if name == wanted then return value, n end
        n = n + 1
    end
end

local fresh = _E._fresh_cooldown
_G._lookup_fresh_ref = fresh
local original = scan_upvalue(fresh, "original")
_G._safe_call_exists = (type(original) == "function")
_G._safe_call = scan_upvalue(original, "safe_call")
_G._safe_call_found = (type(_G._safe_call) == "function")
_G._lookup_fresh_identity = (_E._fresh_cooldown == fresh)
if _G._safe_call_found then
    local info = debug.getinfo(_G._safe_call, "S")
    _G._safe_call_source = info.source
    _G._safe_call_linedefined = info.linedefined
    _G._safe_call_lastlinedefined = info.lastlinedefined
end
'''

# Count real safe_call executions and nested anonymous lookup closures created
# inside its own definition range, using debug.sethook("c", ...) around the
# production publication only. Nothing here replaces the helper or a renderer.
OBSERVE_PUBLICATION = r'''
local safe_call = _G._safe_call
local safe_source = _G._safe_call_source
local safe_first = _G._safe_call_linedefined
local safe_last = _G._safe_call_lastlinedefined

_G._lookup_helper_calls = 0
_G._lookup_nested_closure_calls = 0

local function captures_lookup_upvalues(fn)
    local has_obj = false
    local has_method = false
    local n = 1
    while true do
        local name = debug.getupvalue(fn, n)
        if name == nil then break end
        if name == "obj" then
            has_obj = true
        elseif name == "method" then
            has_method = true
        else
            return false
        end
        n = n + 1
    end
    return has_obj and has_method
end

local function is_nested_lookup(info)
    if info.what ~= "Lua" then return false end
    if info.source ~= safe_source then return false end
    if info.func == safe_call then return false end
    if info.linedefined < safe_first or info.linedefined > safe_last then
        return false
    end
    if not captures_lookup_upvalues(info.func) then return false end
    local level = 3
    while level <= 6 do
        local caller = debug.getinfo(level, "f")
        if caller == nil then return false end
        if caller.func == safe_call then return true end
        level = level + 1
    end
    return false
end

local function hook()
    local info = debug.getinfo(2, "Slnf")
    if info == nil then return end
    if info.func == safe_call then
        _G._lookup_helper_calls = _G._lookup_helper_calls + 1
        return
    end
    if is_nested_lookup(info) then
        _G._lookup_nested_closure_calls =
            _G._lookup_nested_closure_calls + 1
    end
end

_G._lookup_pre_rows =
    (_E._rows ~= nil and _E._rows[4] ~= nil and _E._rows[6] ~= nil)
_G._lookup_pre_e_verify = (_E:verify() == true)
_G._lookup_pre_root_visible =
    (_E._root ~= nil and _E._root:visible() == true)
_G._lookup_pre_meter_hidden = (_ability_meter:visible() == false)
_G._lookup_pre_icon_hidden = (_ability_icon:visible() == false)

-- JIT traces omit call hooks; an interpreter-only census is required for
-- deterministic counts. This is not a performance benchmark.
_G._ky_lookup_jit_was_on = jit.status()
jit.off()
jit.flush()
debug.sethook(hook, "c")
_m:set_player_ability_radial({current = 6, total = 6})
debug.sethook()
if _G._ky_lookup_jit_was_on then
    jit.on()
end
_G._ky_lookup_jit_was_on = nil

_G._lookup_post_e_verify = (_E:verify() == true)
_G._lookup_post_root_visible =
    (_E._root ~= nil and _E._root:visible() == true)
_G._lookup_post_rows =
    (_E._rows ~= nil and _E._rows[4] ~= nil and _E._rows[6] ~= nil)
_G._lookup_post_meter_hidden = (_ability_meter:visible() == false)
_G._lookup_post_icon_hidden = (_ability_icon:visible() == false)
_G._lookup_post_meter_parent = (_ability_meter:parent() == _ability_parent)
_G._lookup_post_icon_parent = (_ability_icon:parent() == _ability_parent)

_G._lookup_fresh_preserved = (_E._fresh_cooldown == _G._lookup_fresh_ref)
local current_safe_call = _G._safe_call
_G._lookup_safe_call_preserved = (type(current_safe_call) == "function"
    and debug.getinfo(current_safe_call, "S").source == safe_source)
'''


# Contract of the actual extracted safe_call, exercised against real tables,
# metatables, closures and LuaJIT userdata (newproxy).
SAFE_CALL_CONTRACT = r'''
local safe_call = _G._safe_call
local function run(label, obj, method, ...)
    local a, b = safe_call(obj, method, ...)
    _G["_contract_" .. label .. "_a"] = a
    _G["_contract_" .. label .. "_b"] = b
end

run("nil_obj", nil, "set_visible", true)

local missing = {}
run("missing_method", missing, "does_not_exist")

local nonfunction = {method = 42}
run("nonfunction", nonfunction, "method")

local index_calls = 0
local metatable_throw = setmetatable({}, {
    __index = function()
        index_calls = index_calls + 1
        error("index exploded")
    end,
})
run("throwing_index", metatable_throw, "method")
_G._contract_throwing_index_index_calls = index_calls

local body_calls_received = 0
local throwing_body = {}
throwing_body.method = function(self, ...)
    body_calls_received = body_calls_received + 1
    error("body exploded")
end
run("throwing_body", throwing_body, "method")
_G._contract_throwing_body_calls_received = body_calls_received

local receiver_ok = false
local vararg_count, trailing_nil_count
local success_target = {}
function success_target.method(self, ...)
    receiver_ok = (self == success_target)
    vararg_count = select("#", ...)
    trailing_nil_count = 0
    local n = vararg_count
    while n > 0 and select(n, ...) == nil do
        trailing_nil_count = trailing_nil_count + 1
        n = n - 1
    end
    return ...
end
local ok, v1, v2, v3, v4 = safe_call(success_target, "method", 1, nil, 3, nil)
_G._contract_success_ok = (ok == true)
_G._contract_success_receiver = receiver_ok
_G._contract_success_vararg_count = vararg_count
_G._contract_success_trailing_nil = trailing_nil_count
_G._contract_success_positions = select("#", v1, v2, v3, v4)
_G._contract_success_v1 = v1
_G._contract_success_v2_is_nil = (v2 == nil)
_G._contract_success_v3 = v3
_G._contract_success_v4_is_nil = (v4 == nil)
_G._contract_actual_return_count =
    select("#", safe_call(success_target, "method", 1, nil, 3, nil))

local userdata = newproxy(true)
local userdata_called = false
getmetatable(userdata).__index = function(_, key)
    if key == "method" then
        userdata_called = true
        return function(self, value) return self == userdata, value end
    end
end
local ua, ub, uc = safe_call(userdata, "method", "payload")
_G._contract_userdata_called = userdata_called
_G._contract_userdata_ok = (ua == true)
_G._contract_userdata_receiver = (ub == true)
_G._contract_userdata_value = uc
'''


class KingpinSafeLookupTests(unittest.TestCase):
    def test_safe_lookup_has_no_per_call_nested_closure(self):
        lua = kingpin_lua()
        g = lua.globals()

        lua.execute(EXTRACT_SAFE_CALL)
        self.assertTrue(bool(g._safe_call_exists),
            "fresh cooldown wrapper must expose its original upvalue")
        self.assertTrue(bool(g._safe_call_found),
            "original _fresh_cooldown must expose the real safe_call upvalue")
        self.assertTrue(bool(g._lookup_fresh_identity),
            "_E._fresh_cooldown wrapper identity must stay untouched")

        lua.execute(KINGPIN_ACTIVATE)
        lua.execute(OBSERVE_PUBLICATION)

        self.assertTrue(bool(g._lookup_pre_rows))
        self.assertTrue(bool(g._lookup_pre_e_verify))
        self.assertTrue(bool(g._lookup_pre_root_visible))
        self.assertTrue(bool(g._lookup_pre_meter_hidden))
        self.assertTrue(bool(g._lookup_pre_icon_hidden))

        self.assertGreater(int(g._lookup_helper_calls), 0,
            "real safe_call must actually run during stable radial publication")
        self.assertEqual(int(g._lookup_nested_closure_calls), 0,
            "RED: safe_call must not allocate/execute a nested lookup closure")

        self.assertTrue(bool(g._lookup_post_e_verify))
        self.assertTrue(bool(g._lookup_post_root_visible))
        self.assertTrue(bool(g._lookup_post_rows))
        self.assertTrue(bool(g._lookup_post_meter_hidden))
        self.assertTrue(bool(g._lookup_post_icon_hidden))
        self.assertTrue(bool(g._lookup_post_meter_parent))
        self.assertTrue(bool(g._lookup_post_icon_parent))
        self.assertTrue(bool(g._lookup_fresh_preserved),
            "_E._fresh_cooldown identity must remain untouched")
        self.assertTrue(bool(g._lookup_safe_call_preserved),
            "safe_call source identity must remain untouched")

    def test_safe_call_contract_preserves_failure_and_success(self):
        lua = kingpin_lua()
        g = lua.globals()

        lua.execute(EXTRACT_SAFE_CALL)
        self.assertTrue(bool(g._safe_call_found),
            "real safe_call upvalue must be extractable from _fresh_cooldown")
        lua.execute(SAFE_CALL_CONTRACT)

        for label in ("nil_obj", "missing_method", "nonfunction",
                "throwing_index"):
            self.assertFalse(bool(g[f"_contract_{label}_a"]),
                f"{label} must return false")
            self.assertIsNone(g[f"_contract_{label}_b"],
                f"{label} must return nil")

        self.assertFalse(bool(g._contract_throwing_body_a),
            "throwing method body must return false")
        self.assertIsInstance(g._contract_throwing_body_b, str,
            "throwing method body must return the actual error string")

        self.assertEqual(int(g._contract_throwing_index_index_calls), 1,
            "throwing __index must be consulted exactly once")
        self.assertEqual(int(g._contract_throwing_body_calls_received), 1,
            "throwing method body must be invoked exactly once")

        self.assertTrue(bool(g._contract_success_ok))
        self.assertTrue(bool(g._contract_success_receiver),
            "actual receiver must be the supplied object")
        self.assertEqual(int(g._contract_success_vararg_count), 4,
            "all four forwarded positions (including trailing nil) must arrive")
        self.assertEqual(int(g._contract_success_trailing_nil), 1)
        self.assertEqual(int(g._contract_success_positions), 4,
            "successful return must keep four select positions")
        self.assertEqual(int(g._contract_success_v1), 1)
        self.assertTrue(bool(g._contract_success_v2_is_nil))
        self.assertEqual(int(g._contract_success_v3), 3)
        self.assertTrue(bool(g._contract_success_v4_is_nil))
        self.assertEqual(int(g._contract_actual_return_count), 5,
            "actual safe_call success must return bool + four results")

        self.assertTrue(bool(g._contract_userdata_called))
        self.assertTrue(bool(g._contract_userdata_ok))
        self.assertTrue(bool(g._contract_userdata_receiver))
        self.assertEqual(g._contract_userdata_value, "payload")


if __name__ == "__main__":
    unittest.main()
