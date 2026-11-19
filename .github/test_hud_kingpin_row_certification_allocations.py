"""Lot 6 RED: equipment row certification must not allocate dynamic verifier or
style closures, and failed certification must be fail-closed, repairable and
free of primitive writes.
"""
import unittest

from test_hud_kingpin_active import kingpin_lua
from test_hud_kingpin_terminal_player import SETUP


PREPARE = r'''
_m:set_player_ability_radial({current = 6, total = 6})
_R:update(_m, 3.3, 0.05)
_m:set_player_ability_radial({current = 5.9, total = 6})
assert(_E:verify() == true)
assert(_E._rows[4]:verify() == true)
assert(_E._rows[6]:verify() == true)
'''

ALLOCATION_PROBE = r'''
local row4 = _E._rows[4]
local row6 = _E._rows[6]
assert(row4 ~= nil and row6 ~= nil)

local verify4 = row4.verify
local verify6 = row6.verify
local cell4 = row4._verify_cell
local cell6 = row6._verify_cell
assert(type(verify4) == "function")
assert(type(verify6) == "function")
assert(type(cell4) == "function")
assert(type(cell6) == "function")

local function def_info(fn)
    local ok, info = pcall(debug.getinfo, fn, "S")
    if not ok or type(info) ~= "table" or info.what ~= "Lua" then return nil end
    return info
end

local function upvalue_named(fn, name)
    local i = 1
    while true do
        local ok, key, value = pcall(debug.getupvalue, fn, i)
        if not ok or key == nil then return nil end
        if key == name then return value end
        i = i + 1
    end
end

local function find_named(fn, name, seen)
    if type(fn) ~= "function" then return nil end
    seen = seen or {}
    if seen[fn] then return nil end
    seen[fn] = true
    if not def_info(fn) then return nil end
    local i = 1
    while true do
        local ok, key, value = pcall(debug.getupvalue, fn, i)
        if not ok or key == nil then break end
        if key == name and type(value) == "function" then return value end
        if type(value) == "function" then
            local found = find_named(value, name, seen)
            if found then return found end
        end
        i = i + 1
    end
    return nil
end

local function inside(fn, ancestor)
    local candidate = def_info(fn)
    local owner = def_info(ancestor)
    return candidate ~= nil and owner ~= nil
        and candidate.source == owner.source
        and candidate.linedefined >= owner.linedefined
        and candidate.lastlinedefined <= owner.lastlinedefined
end

local function has_ancestor(wanted)
    for level = 3, 14 do
        local ok, info = pcall(debug.getinfo, level, "f")
        if not ok or type(info) ~= "table" or type(info.func) ~= "function" then
            return false
        end
        if info.func == wanted then return true end
    end
    return false
end

local style = find_named(verify4, "style") or find_named(cell4, "style")
assert(type(style) == "function", "actual style helper not found")
local finite = find_named(style, "finite")
assert(type(finite) == "function", "actual finite helper not found")

local counts = {
    verify = 0,
    cell = 0,
    style = 0,
    verifier_self = 0,
    style_finite = 0,
}

local function hook(event)
    if event ~= "call" then return end
    local info = debug.getinfo(2, "fSL")
    local fn = info and info.func
    if type(fn) ~= "function" then return end

    if fn == verify4 or fn == verify6 then
        counts.verify = counts.verify + 1
        return
    end
    if fn == cell4 or fn == cell6 then
        counts.cell = counts.cell + 1
        return
    end
    if fn == style then
        counts.style = counts.style + 1
        return
    end

    if has_ancestor(verify4) or has_ancestor(verify6)
        or has_ancestor(cell4) or has_ancestor(cell6) then
        local self_value = upvalue_named(fn, "self")
        if self_value == row4 or self_value == row6 then
            counts.verifier_self = counts.verifier_self + 1
            return
        end
    end

    if inside(fn, style) and has_ancestor(style) then
        local captured = upvalue_named(fn, "finite")
        if captured == finite then
            counts.style_finite = counts.style_finite + 1
        end
    end
end

local jit_was_on = jit.status()
jit.off()
jit.flush()

local ok, err = pcall(function()
    debug.sethook(hook, "c")
    _m:set_player_ability_radial({current = 5.8, total = 6})
    _R:update(_m, 3.31, 0.01)
    for _ = 1, 3 do
        row4:verify()
        row6:verify()
        row4:_verify_cell()
    end
end)
debug.sethook()
if jit_was_on then jit.on() else jit.off() end
jit.flush()
if not ok then error(err) end

local style_again = find_named(row4.verify, "style")
    or find_named(row4._verify_cell, "style")
local finite_again = style_again and find_named(style_again, "finite") or nil

_G._alloc_counts = counts
_G._alloc_identity_ok = row4.verify == verify4
    and row6.verify == verify6
    and row4._verify_cell == cell4
    and row6._verify_cell == cell6
    and style_again == style
    and finite_again == finite
'''

FAILCLOSED_PROBE = r'''
local row4 = _E._rows[4]
local row6 = _E._rows[6]
assert(row4 ~= nil and row6 ~= nil)

local write_count = 0
local counting = false
local saved_setters = {}

local function wrap_setters(row)
    local objects = {row._root, row._label, row._value, row._track, row._fill}
    for _, object in ipairs(objects) do
        local entries = {}
        for key, value in pairs(object) do
            if type(value) == "function" and key:sub(1, 4) == "set_" then
                entries[#entries + 1] = {key = key, value = value}
            end
        end
        for _, entry in ipairs(entries) do
            local original = entry.value
            object[entry.key] = function(self, ...)
                if counting then write_count = write_count + 1 end
                return original(self, ...)
            end
            saved_setters[#saved_setters + 1] = {
                object = object,
                key = entry.key,
                value = original,
            }
        end
    end
end

local function verify_result(row)
    counting = true
    local ok, result = pcall(row.verify, row)
    counting = false
    return ok, result
end

local function verify_true(row)
    local ok, result = verify_result(row)
    return ok and result == true
end

local function verify_false(row)
    local ok, result = verify_result(row)
    return ok and result == false
end

local function snapshot(row)
    return {
        root = row._root,
        label = row._label,
        value = row._value,
        track = row._track,
        fill = row._fill,
    }
end

local function same_identity(row, saved)
    return row._root == saved.root
        and row._label == saved.label
        and row._value == saved.value
        and row._track == saved.track
        and row._fill == saved.fill
end

local function run_case(row, apply, restore)
    local saved = snapshot(row)
    apply()
    local failed = verify_false(row)
    restore()
    local repaired = verify_true(row)
    return failed and repaired and same_identity(row, saved)
end

local function case_x_throw(row)
    local root = row._root
    local original = root.x
    return function() root.x = function() error("row root x threw") end end,
        function() root.x = original end
end

local function case_x_nan(row)
    local root = row._root
    local original = root.x
    return function() root.x = function() return 0 / 0 end end,
        function() root.x = original end
end

local function case_visible_false(row)
    local root = row._root
    local original = root.visible
    return function() root.visible = function() return false end end,
        function() root.visible = original end
end

local function case_text_wrong(row)
    local value = row._value
    local original = value.text
    return function() value.text = function() return "WRONG" end end,
        function() value.text = original end
end

local function case_color_wrong(row)
    local value = row._value
    local original = value.color
    return function()
        value.color = function() return {r = 0, g = 0, b = 0, a = 1} end
    end, function() value.color = original end
end

local cases = {
    case_x_throw,
    case_x_nan,
    case_visible_false,
    case_text_wrong,
    case_color_wrong,
}

local all_ok = true
local ok, err = pcall(function()
    wrap_setters(row4)
    wrap_setters(row6)
    for _, row in ipairs({row4, row6}) do
        all_ok = verify_true(row) and all_ok
        for _, make_case in ipairs(cases) do
            local apply, restore = make_case(row)
            if not run_case(row, apply, restore) then all_ok = false end
        end
    end
end)

for _, entry in ipairs(saved_setters) do
    entry.object[entry.key] = entry.value
end
if not ok then error(err) end

_G._failclosed_ok = all_ok
_G._failclosed_write_count = write_count
'''


class RowCertificationAllocationTests(unittest.TestCase):
    def test_verification_reuses_helpers_without_dynamic_closures(self):
        lua = kingpin_lua()
        g = lua.globals()

        lua.execute(SETUP)
        lua.execute(PREPARE)
        lua.execute(ALLOCATION_PROBE)

        counts = g._alloc_counts
        self.assertGreater(int(counts.verify), 0,
            "the real Row.verify must actually run")
        self.assertGreater(int(counts.cell), 0,
            "the real Row._verify_cell must actually run")
        self.assertGreater(int(counts.style), 0,
            "the real style helper must actually run")
        self.assertEqual(int(counts.verifier_self), 0,
            "verify must not create dynamic closures capturing the row")
        self.assertEqual(int(counts.style_finite), 0,
            "style must not create dynamic closures capturing finite")
        self.assertTrue(bool(g._alloc_identity_ok),
            "method and helper identities must be preserved")

    def test_failed_certification_is_fail_closed_and_repairs_without_writes(self):
        lua = kingpin_lua()
        g = lua.globals()

        lua.execute(SETUP)
        lua.execute(PREPARE)
        lua.execute(FAILCLOSED_PROBE)

        self.assertTrue(bool(g._failclosed_ok),
            "every corruption must fail closed and repair with identical objects")
        self.assertEqual(int(g._failclosed_write_count), 0,
            "direct verification must never write owned primitives")


if __name__ == "__main__":
    unittest.main()
