"""Grenade flash trace diagnostic regression.

Enabled through the real sentinel file beside the equipment module: one
source-stage radial_shape trace must describe the exact deviated ghost geometry
and its alpha fields, then the same failure must stay deduped on throttled
updates. The functional source guard must still restore the native ghosts and
hide the owned row4 pulse. This is intentionally RED until production emits the
contracted trace.
"""
import unittest
from pathlib import Path

from test_hud_grenade_flash_replacement import _flash_lua


_PREPARE = r'''
_G._kyo_trace_log_texts = {}
_G._kyo_trace_log_original = log or nil
log = function(...)
    local parts, n = {}, select('#', ...)
    for i = 1, n do parts[i] = tostring((select(i, ...))) end
    _G._kyo_trace_log_texts[#_G._kyo_trace_log_texts + 1] =
        table.concat(parts, ' ')
    if _G._kyo_trace_log_original then
        return _G._kyo_trace_log_original(...)
    end
end

_G._kyo_trace_io_open_original = io.open
io.open = function(path, mode, ...)
    if path == ModPath .. 'KYO_GRENADE_FLASH_TRACE' then
        return {close = function() end}
    end
    return _G._kyo_trace_io_open_original(path, mode, ...)
end

ModPath = '/virtual/'
RequiredScript = 'lib/managers/hudmanagerpd2'
if _E then _E._grenade_flash_trace_state = nil end

_G._kyo_trace_count_reason = function()
    local count = 0
    for i = 1, #_G._kyo_trace_log_texts do
        local line = _G._kyo_trace_log_texts[i]
        if string.find(line, '[KyoHUD][GrenadeFlashTrace]', 1, true)
            and string.find(line, 'reason=radial_shape', 1, true) then
            count = count + 1
        end
    end
    return count
end

_G._kyo_trace_lines_after = function(index)
    local out = {}
    for i = index + 1, #_G._kyo_trace_log_texts do
        out[#out + 1] = _G._kyo_trace_log_texts[i]
    end
    return table.concat(out, '\n')
end
'''


_RELOAD = r'''
_G._reload_ok, _G._reload_err = pcall(function()
    if _E and type(_E.refresh) == 'function' then _E:refresh(_m) end
    _E._icon_cache = nil
    _R:refresh_settings(_m)
end)
_G._reload_err = tostring(_G._reload_err or '')
'''


_CERTIFY = r'''
_G._certify_ok, _G._certify_err = pcall(function()
    _R:update(_m, 1.20, .06)
end)
_G._certify_err = tostring(_G._certify_err or '')
_G._trace_baseline = #_G._kyo_trace_log_texts
'''


_CORRUPT = r'''
_G._corrupt_ok, _G._corrupt_err = pcall(function()
    local ghost = _gren:child('grenades_radial_ghost')
    local x, y, w, h = ghost:x(), ghost:y(), ghost:w(), ghost:h()
    _G._trace_base_x, _G._trace_base_y = x, y
    _G._trace_base_w, _G._trace_base_h = w, h
    _G._expected_base_shape = string.format(
        '(%.17g,%.17g,%.17g,%.17g)', _radial:x(), _radial:y(),
        _radial:w(), _radial:h())
    ghost:set_shape(x + 3, y, w, h)
    _G._expected_ghost_shape = string.format(
        '(%.17g,%.17g,%.17g,%.17g)',
        ghost:x(), ghost:y(), ghost:w(), ghost:h())
    _G._expected_native_alpha = string.format('%.17g', ghost:alpha())
    local color = ghost:color()
    _G._expected_tint_alpha = string.format(
        '%.17g', color and color.a or 0)
end)
_G._corrupt_err = tostring(_G._corrupt_err or '')
'''


_FAIL_ONCE = r'''
_G._fail1_ok, _G._fail1_err = pcall(function()
    _R:update(_m, 1.21, .01)
end)
_G._fail1_err = tostring(_G._fail1_err or '')
_G._trace_after_first = #_G._kyo_trace_log_texts
_G._trace_new_lines_text = _G._kyo_trace_lines_after(
    _G._trace_baseline or 0)
_G._trace_reason_count_first = _G._kyo_trace_count_reason()

local function visible(name)
    local child = _gren:child(name)
    return child ~= nil and child:visible() == true
end
_G._ghosts_restored = visible('grenades_radial_ghost')
    and visible('grenades_icon_ghost')
local row = _E and _E._rows and _E._rows[4]
local flash = row and row._grenade_flash
_G._pulse_hidden = flash ~= nil and flash:visible() == false
'''


_REPEAT = r'''
_G._repeat_ok, _G._repeat_err = pcall(function()
    local ghost = _gren:child('grenades_radial_ghost')
    ghost:set_shape(_G._trace_base_x + 3, _G._trace_base_y,
        _G._trace_base_w, _G._trace_base_h)
    _R:update(_m, 1.22, .01)
    ghost:set_shape(_G._trace_base_x + 3, _G._trace_base_y,
        _G._trace_base_w, _G._trace_base_h)
    _R:update(_m, 1.23, .01)
end)
_G._repeat_err = tostring(_G._repeat_err or '')
_G._trace_reason_count_after = _G._kyo_trace_count_reason()
'''


_RESTORE = r'''
if _G._kyo_trace_io_open_original then
    io.open = _G._kyo_trace_io_open_original
end
'''


_EQUIPMENT_PATH = (Path(__file__).resolve().parents[1]
                   / "lua" / "hud" / "equipment.lua")

_TRACE_IO_SETUP = r'''
_G._kyo_trace_sentinel_present = __SENTINEL__
_G._kyo_trace_open_count = 0
_G._kyo_trace_io_open_original = io.open
io.open = function(path, mode, ...)
    if path == ModPath .. 'KYO_GRENADE_FLASH_TRACE' then
        _G._kyo_trace_open_count = _G._kyo_trace_open_count + 1
        if _G._kyo_trace_sentinel_present then
            return {close = function() end}
        end
        return nil
    end
    return _G._kyo_trace_io_open_original(path, mode, ...)
end
'''

_TRACE_LOG = r'''
_G._kyo_trace_log_texts = {}
_G._kyo_trace_log_original = log or nil
log = function(...)
    local parts, n = {}, select('#', ...)
    for i = 1, n do parts[i] = tostring((select(i, ...))) end
    _G._kyo_trace_log_texts[#_G._kyo_trace_log_texts + 1] =
        table.concat(parts, ' ')
    if _G._kyo_trace_log_original then
        return _G._kyo_trace_log_original(...)
    end
end
_G._kyo_trace_all = function()
    return table.concat(_G._kyo_trace_log_texts, '\n')
end
'''

_TRACE_RESTORE = r'''
if _G._kyo_trace_io_open_original then
    io.open = _G._kyo_trace_io_open_original
end
if _G._kyo_trace_log_original then
    log = _G._kyo_trace_log_original
end
'''

_PARITY_INSTRUMENT = r'''
_G._getter_counts = {}
local function instrument(panel, tag)
    if panel == nil then return end
    local methods = {'visible', 'alpha', 'color', 'x', 'y', 'w', 'h'}
    for i = 1, #methods do
        local method = methods[i]
        local original = panel[method]
        if type(original) == 'function' then
            local key = tag .. '.' .. method
            _G._getter_counts[key] = 0
            panel[method] = function(self, ...)
                _G._getter_counts[key] = _G._getter_counts[key] + 1
                return original(self, ...)
            end
        end
    end
end
instrument(_gren:child('grenades_radial_ghost'), 'radial_ghost')
instrument(_gren:child('grenades_icon_ghost'), 'icon_ghost')
instrument(_gren:child('grenades_radial'), 'radial_base')
instrument(_gren:child('grenades_icon'), 'icon_base')
'''

_PARITY_RUN = r'''
_G._parity_logs_before = #_G._kyo_trace_log_texts
_R:update(_m, 1.10, .05)
_R:update(_m, 1.11, .01)
_game_clock:set_time(1010)
_R:update(_m, 1.12, .05)
_R:update(_m, 1.13, .01)
_G._parity_logs_after = #_G._kyo_trace_log_texts
local row = _E._rows and _E._rows[4]
local flash = row and row._grenade_flash
_G._parity_verify = _E:verify() == true
_G._parity_flash_present = flash ~= nil
_G._parity_flash_visible = flash ~= nil and flash:visible() == true
_G._parity_flash_alpha = flash and flash:alpha() or -1
local radial_ghost = _gren:child('grenades_radial_ghost')
local icon_ghost = _gren:child('grenades_icon_ghost')
_G._parity_radial_ghost_visible = radial_ghost ~= nil
    and radial_ghost:visible()
_G._parity_icon_ghost_visible = icon_ghost ~= nil
    and icon_ghost:visible()
_G._parity_native_radial = string.format('%.17g,%.17g,%.17g,%.17g',
    _radial:x(), _radial:y(), _radial:w(), _radial:h())
_G._parity_native_icon = string.format('%.17g,%.17g,%.17g,%.17g',
    _icon:x(), _icon:y(), _icon:w(), _icon:h())
_G._parity_flash_ok = _E._grenade_flash_ok == true
local keys = {}
for key in pairs(_G._getter_counts) do keys[#keys + 1] = key end
table.sort(keys)
local parts = {}
for i = 1, #keys do
    parts[i] = keys[i] .. '=' .. _G._getter_counts[keys[i]]
end
_G._parity_getters = table.concat(parts, ';')
_G._parity_getter_total = 0
for _, count in pairs(_G._getter_counts) do
    _G._parity_getter_total = _G._parity_getter_total + count
end
'''


def _equipment_source():
    return _EQUIPMENT_PATH.read_text(encoding="utf-8-sig")


def _boot_trace(lua, sentinel):
    lua.execute(_TRACE_IO_SETUP.replace(
        "__SENTINEL__", "true" if sentinel else "false"))
    lua.execute("_E._grenade_flash_trace_state = nil\n_E._icon_cache = nil")
    lua.globals().RequiredScript = "lib/managers/hudmanagerpd2"
    lua.execute(_equipment_source())
    lua.execute(_TRACE_LOG)
    lua.execute(_RELOAD)


def _reexecute_equipment(lua, required_script):
    lua.globals().RequiredScript = required_script
    lua.execute(_equipment_source())


def _text(value):
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


class GrenadeFlashTraceTests(unittest.TestCase):
    def test_diagnostic_source_radial_shape_trace_and_dedupe(self):
        lua = _flash_lua()
        g = lua.globals()
        source = (Path(__file__).resolve().parents[1]
                  / "lua" / "hud" / "equipment.lua").read_text(
                      encoding="utf-8-sig")
        try:
            lua.execute(_PREPARE)
            lua.execute(source)
            lua.execute(_RELOAD)
            lua.execute(_CERTIFY)
            lua.execute(_CORRUPT)
            lua.execute(_FAIL_ONCE)
            lua.execute(_REPEAT)
        finally:
            try:
                lua.execute(_RESTORE)
            except Exception:
                pass

        self.assertIs(bool(g._reload_ok), True,
            "equipment reload failed before corruption: %s"
            % _text(g._reload_err))
        self.assertIs(bool(g._certify_ok), True,
            "equipment certification failed before corruption: %s"
            % _text(g._certify_err))
        self.assertIs(bool(g._corrupt_ok), True,
            "could not corrupt the radial ghost: %s"
            % _text(g._corrupt_err))

        ghost_shape = _text(g._expected_ghost_shape)
        base_shape = _text(g._expected_base_shape)
        native_alpha = _text(g._expected_native_alpha)
        tint_alpha = _text(g._expected_tint_alpha)
        self.assertTrue(
            ghost_shape.startswith("(") and base_shape.startswith("("),
            "expected radial ghost shape tuples were not captured")
        self.assertNotEqual(native_alpha, "",
            "expected native alpha was not captured")
        self.assertNotEqual(tint_alpha, "",
            "expected tint alpha was not captured")

        new_lines = [
            line for line in _text(g._trace_new_lines_text).splitlines()
            if line
        ]
        fragments = [
            "stage=source",
            "reason=radial_shape",
            "leaf=grenades_radial_ghost",
            "ghost_shape=" + ghost_shape,
            "base_shape=" + base_shape,
            "native_alpha=" + native_alpha,
            "tint_alpha=" + tint_alpha,
        ]
        matches = [
            line for line in new_lines
            if "[KyoHUD][GrenadeFlashTrace]" in line
            and all(fragment in line for fragment in fragments)
        ]
        self.assertTrue(matches,
            "expected a [KyoHUD][GrenadeFlashTrace] stage=source "
            "reason=radial_shape line for leaf=grenades_radial_ghost with "
            "ghost_shape=%s base_shape=%s native_alpha=%s tint_alpha=%s; "
            "new lines: %r" % (ghost_shape, base_shape, native_alpha,
                               tint_alpha, new_lines))

        self.assertIs(bool(g._fail1_ok), True, _text(g._fail1_err))
        self.assertIs(bool(g._ghosts_restored), True,
            "native radial and icon ghosts must be restored when the "
            "radial ghost geometry deviates")
        self.assertIs(bool(g._pulse_hidden), True,
            "owned row4 pulse must stay hidden when the radial ghost "
            "geometry deviates")

        first_count = int(g._trace_reason_count_first or 0)
        after_count = int(g._trace_reason_count_after or 0)
        self.assertGreaterEqual(first_count, 1,
            "the first deviated update must emit a radial_shape trace")
        self.assertEqual(first_count, 1,
            "the first deviated update must emit exactly one radial_shape trace")
        self.assertEqual(after_count, first_count,
            "repeated radial_shape failures must stay deduped")
        self.assertIs(bool(g._repeat_ok), True, _text(g._repeat_err))

    def test_runtime_lease_trace_and_missing_chain_reason(self):
        lua = _flash_lua()
        g = lua.globals()
        try:
            _boot_trace(lua, True)
            lua.execute(r'''
                local baseline_radial = _gren:child('grenades_radial')
                local baseline_icon = _gren:child('grenades_icon')
                _G._baseline_radial_visible = baseline_radial ~= nil
                    and baseline_radial:visible() == true
                _G._baseline_icon_visible = baseline_icon ~= nil
                    and baseline_icon:visible() == true
                _G._acquired_before = #_G._kyo_trace_log_texts
                _R:update(_m, 1.20, .06)
                _G._acquired_verify = _E:verify() == true
                local row = _E._rows and _E._rows[4]
                local flash = row and row._grenade_flash
                _G._acquired_flash_visible = flash ~= nil
                    and flash:visible() == true
                _G._acquired_flash_alpha = flash and flash:alpha() or nil
                local ghost = _gren:child('grenades_radial_ghost')
                _G._acquired_ghost_alpha = ghost and ghost:alpha() or nil
                local radial = _gren:child('grenades_radial')
                local icon = _gren:child('grenades_icon')
                _G._acquired_native_ok = radial ~= nil and icon ~= nil
                    and (radial:visible() == true)
                        == _G._baseline_radial_visible
                    and (icon:visible() == true)
                        == _G._baseline_icon_visible
                _G._acquired_text = _G._kyo_trace_all()

                local function acquired_count()
                    local count = 0
                    for i = 1, #_G._kyo_trace_log_texts do
                        local line = _G._kyo_trace_log_texts[i]
                        if string.find(line, 'stage=lease', 1, true)
                            and string.find(line, 'reason=acquired', 1, true) then
                            count = count + 1
                        end
                    end
                    return count
                end
                _G._acquired_count = acquired_count()

                if flash then flash:set_alpha(.2) end
                _G._throttle_before_logs = #_G._kyo_trace_log_texts
                _R:update(_m, 1.21, .01)
                local throttle_group = _R._h5_groups
                _G._throttle_verify = _E._grenade_flash_ok == false
                    and (not throttle_group
                        or throttle_group["local_p_grenade_flash"] == nil)
                _G._throttle_same = flash ~= nil
                    and _E._rows[4]._grenade_flash == flash
                _G._throttle_ghosts =
                    _gren:child('grenades_radial_ghost'):visible() == true
                    and _gren:child('grenades_icon_ghost'):visible() == true
                _G._throttle_count = acquired_count()
                _G._throttle_text = _G._kyo_trace_all()

                local before_missing = #_G._kyo_trace_log_texts
                _gren:remove('grenades_icon_ghost')
                local ret = _E:_read_grenade_flash_source()
                _G._missing_ret_nil = ret == nil
                local texts = {}
                for i = before_missing + 1, #_G._kyo_trace_log_texts do
                    texts[#texts + 1] = _G._kyo_trace_log_texts[i]
                end
                _G._missing_text = table.concat(texts, '\n')
            ''')
        finally:
            try:
                lua.execute(_TRACE_RESTORE)
            except Exception:
                pass

        self.assertIs(bool(g._acquired_verify), True,
            "the ordinary update must certify the owned flash")
        self.assertIs(bool(g._acquired_flash_visible), True,
            "the owned row4 flash must be visible during the source pulse")
        self.assertIs(bool(g._acquired_native_ok), True,
            "both native source leaves must retain their captured baseline "
            "visibility")
        self.assertIsNotNone(g._acquired_flash_alpha,
            "the owned flash alpha must be readable")
        self.assertIsNotNone(g._acquired_ghost_alpha,
            "the native ghost alpha must be readable")
        self.assertAlmostEqual(float(g._acquired_flash_alpha),
            float(g._acquired_ghost_alpha), places=6,
            msg="the owned flash must use the actual native ghost alpha")

        acquired_lines = [
            line for line in _text(g._acquired_text).splitlines()
            if "stage=lease" in line and "reason=acquired" in line
        ]
        required = (
            "ghost1_visible=false",
            "ghost1_held=true",
            "ghost2_visible=false",
            "ghost2_held=true",
        )
        self.assertTrue(any(all(fragment in line for fragment in required)
                            for line in acquired_lines),
            "the lease acquired trace must report both original readbacks "
            "as hidden and held; acquired lines: %r" % acquired_lines)
        self.assertGreaterEqual(int(g._acquired_count or 0), 1,
            "the actual runtime route must emit the lease acquired reason")
        certified_lines = [
            line for line in _text(g._acquired_text).splitlines()
            if "stage=owned" in line and "reason=certified" in line
            and "verify=true" in line and "flash_visible=true" in line
        ]
        self.assertTrue(certified_lines,
            "the acquired trace must certify the owned flash on one line; "
            "certified lines: %r" % certified_lines)

        self.assertIs(bool(g._throttle_verify), True,
            "the corrupted owned alpha must fail certification on throttle")
        self.assertIs(bool(g._throttle_same), True,
            "the throttle must retain the same owned flash primitive")
        self.assertIs(bool(g._throttle_ghosts), True,
            "the throttle failure must restore both native ghost leaves")
        self.assertEqual(int(g._throttle_count or 0),
            int(g._acquired_count or 0),
            "the throttled failure must not emit a new owned repair trace")
        throttle_lines = [
            line for line in _text(g._throttle_text).splitlines()
            if "stage=owned" in line
            and "reason=throttle_verify_failed" in line
        ]
        self.assertTrue(throttle_lines,
            "the throttle failure must emit its owned stage reason; "
            "throttle lines: %r" % throttle_lines)

        missing = _text(g._missing_text)
        self.assertIs(bool(g._missing_ret_nil), True,
            "a missing icon ghost must fail the source read")
        self.assertIn("stage=source", missing,
            "the missing chain regression must use the source stage")
        self.assertIn("reason=chain_icon_ghost", missing,
            "the missing icon ghost must report its exact chain reason")
        self.assertNotIn("reason=chain_missing", missing,
            "the missing icon ghost must not fall back to chain_missing")

    def test_trace_logger_budget_throw_and_reload(self):
        lua = _flash_lua()
        g = lua.globals()
        try:
            _boot_trace(lua, True)
            lua.execute(r'''
                local state = _E._grenade_flash_trace_state
                _G._saved_state = state
                _G._boot_enabled = state ~= nil and state.enabled == true
                _G._boot_count = state and state.count or 0
                for i = 1, 15 - state.count do
                    _E:_trace_grenade_flash('unit', 'budget_' .. i,
                        'n=' .. i)
                end
                _G._fill_count = state.count
                _G._throw_attempts = 0
                local original_log = log
                log = function()
                    _G._throw_attempts = _G._throw_attempts + 1
                    error('trace logger failure')
                end
                local ok, result = pcall(function()
                    return _E:_trace_grenade_flash('unit', 'throwing',
                        'n=16')
                end)
                _G._throw_ok = ok
                _G._throw_result = result
                _G._throw_count = state.count
                log = original_log
                local over_ok, over_result = pcall(function()
                    return _E:_trace_grenade_flash('unit', 'over_cap',
                        'n=17')
                end)
                _G._over_ok = over_ok
                _G._over_result = over_result
                _G._throw_attempts_over = _G._throw_attempts
                _G._seen_throw = state.seen['unit|throwing'] == true
                local seen_count = 0
                for _ in pairs(state.seen) do seen_count = seen_count + 1 end
                _G._seen_count = seen_count
            ''')
            _reexecute_equipment(lua, "lib/managers/playermanager")
            lua.execute(r'''
                local state = _E._grenade_flash_trace_state
                _G._reload_same_state = state == _G._saved_state
                _G._reload_count = state and state.count or -1
                _G._reload_seen_throw = state
                    and state.seen['unit|throwing'] == true
                local seen_count = 0
                if state and state.seen then
                    for _ in pairs(state.seen) do seen_count = seen_count + 1 end
                end
                _G._reload_seen_count = seen_count
                _G._reload_open_count = _G._kyo_trace_open_count
            ''')
        finally:
            try:
                lua.execute(_TRACE_RESTORE)
            except Exception:
                pass

        self.assertIs(bool(g._boot_enabled), True,
            "the sentinel must enable the trace at the module boot")
        self.assertGreaterEqual(int(g._boot_count or 0), 0,
            "the module boot trace count must be non-negative")
        self.assertLessEqual(int(g._boot_count or 0), 15,
            "the module boot trace count must stay within the budget")
        self.assertEqual(int(g._fill_count or 0), 15,
            "fifteen unique direct reasons must consume fifteen slots")
        self.assertIs(bool(g._throw_ok), True,
            "a throwing logger must not propagate through the trace helper")
        self.assertIs(bool(g._throw_result), True,
            "the throwing helper must still report an emitted diagnostic")
        self.assertEqual(int(g._throw_count or 0), 16,
            "a throwing logger must still consume the final budget slot")
        self.assertEqual(int(g._throw_attempts_over or 0), 1,
            "calls over the cap must not invoke the logger")
        self.assertIs(bool(g._over_ok), True,
            "an over-cap trace call must not propagate any error")
        self.assertIs(bool(g._over_result), False,
            "an over-cap trace call must report no emission")
        self.assertIs(bool(g._seen_throw), True,
            "the throwing reason must be recorded in the dedupe table")
        self.assertEqual(int(g._seen_count or 0), 16,
            "the dedupe table must contain exactly the sixteen budget reasons")
        self.assertIs(bool(g._reload_same_state), True,
            "reexecuting the module must preserve the trace state table")
        self.assertEqual(int(g._reload_count or -1), 16,
            "reexecuting the module must preserve the consumed count")
        self.assertIs(bool(g._reload_seen_throw), True,
            "reexecuting the module must preserve the dedupe seen table")
        self.assertEqual(int(g._reload_seen_count or 0), 16,
            "reexecuting the module must preserve all seen reasons")
        self.assertEqual(int(g._reload_open_count or 0), 1,
            "reexecuting the module must not reread the sentinel marker")

    def test_disabled_and_capped_trace_runtime_parity(self):
        disabled = _flash_lua()
        enabled = _flash_lua()
        dg = disabled.globals()
        eg = enabled.globals()
        try:
            _boot_trace(disabled, False)
            _boot_trace(enabled, True)
            _reexecute_equipment(disabled, "lib/managers/playermanager")
            _reexecute_equipment(enabled, "lib/managers/playermanager")
            enabled.execute(r'''
                for i = 1, 16 do
                    _E:_trace_grenade_flash('parity', 'fill_' .. i,
                        'n=' .. i)
                end
                _G._parity_filled = _E._grenade_flash_trace_state.count
            ''')
            disabled.execute(_PARITY_INSTRUMENT)
            enabled.execute(_PARITY_INSTRUMENT)
            disabled.execute(_PARITY_RUN)
            enabled.execute(_PARITY_RUN)
            disabled.execute(r'''
                _G._parity_logs = #_G._kyo_trace_log_texts
                _G._parity_open_count = _G._kyo_trace_open_count
            ''')
            enabled.execute(r'''
                _G._parity_logs = #_G._kyo_trace_log_texts
                _G._parity_open_count = _G._kyo_trace_open_count
            ''')
        finally:
            for lua in (disabled, enabled):
                try:
                    lua.execute(_TRACE_RESTORE)
                except Exception:
                    pass

        self.assertEqual(int(eg._parity_filled or 0), 16,
            "the enabled fixture must reach the diagnostic cap before "
            "the parity transitions")
        self.assertEqual(int(dg._parity_logs or 0), 0,
            "an absent sentinel must never emit trace diagnostics")
        self.assertEqual(int(eg._parity_logs or 0), 16,
            "the capped enabled fixture must not emit new diagnostics")
        self.assertEqual(int(dg._parity_open_count or 0), 1,
            "an absent sentinel must be read once and not reread on reload")
        self.assertEqual(int(eg._parity_open_count or 0), 1,
            "the enabled sentinel must be read once and not reread on reload")
        self.assertEqual(int(dg._parity_logs_before or 0),
            int(dg._parity_logs_after or 0),
            "the disabled runtime must not log during the transitions")
        self.assertEqual(int(eg._parity_logs_before or 0),
            int(eg._parity_logs_after or 0),
            "the capped runtime must not log during the transitions")

        self.assertEqual(_text(dg._parity_getters), _text(eg._parity_getters),
            "disabled and capped diagnostics must issue identical leaf "
            "getter calls")
        self.assertEqual(int(dg._parity_getter_total or 0),
            int(eg._parity_getter_total or 0),
            "disabled and capped diagnostics must issue the same getter "
            "volume")
        for name in ("_parity_verify", "_parity_flash_present",
                     "_parity_flash_visible", "_parity_flash_ok",
                     "_parity_radial_ghost_visible",
                     "_parity_icon_ghost_visible"):
            self.assertEqual(bool(dg[name]), bool(eg[name]),
                "final %s must match between disabled and capped runtime"
                % name)
        self.assertAlmostEqual(float(dg._parity_flash_alpha),
            float(eg._parity_flash_alpha), places=6,
            msg="final owned flash alpha must match")
        self.assertEqual(_text(dg._parity_native_radial),
            _text(eg._parity_native_radial),
            "final native radial source geometry must match")
        self.assertEqual(_text(dg._parity_native_icon),
            _text(eg._parity_native_icon),
            "final native icon source geometry must match")


if __name__ == "__main__":
    unittest.main()
