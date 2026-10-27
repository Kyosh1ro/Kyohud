"""LOT3b -- hud/alerts.lua: vertical slice 3 -- casing (RED state).

Slice 3: native casing show/hide and owned casing replacement via RT.
  - Native show_casing(mode) preempts active Assault before native writes,
    even when enable_alerts=false, without requiring any subsequent update tick.
  - Standard casing replacement via RT with 7 NV records (icon + 5 bg frame
    leaves visible=false, bg text_panel alpha=0).
  - Owned casing ticker with _casing_a and _casing_b texts under clipping panel.
  - Hide casing while whisper_mode=true; coexistence with PNR.
  - Unsupported casing mode preserves native; PNR+casing simultaneous fallback.

Fixture fidelity:
  - show_casing in native (hudassaultcorner.lua:1065-1115) schedules
    _animate_show_casing coroutine; this fixture applies the post-show
    panel state synchronously.
  - hide_casing (hudassaultcorner.lua:1117-1140) schedules
    HUDBGBox_animate_close_left; this fixture applies the completed
    closure state synchronously.
  - GroupAIState:whisper_mode returns _whisper_mode (groupaistatebase.lua).
"""
from pathlib import Path
import unittest

from test_hud_alerts import ALERTS_PATH, NATIVE_PNR_SHOW_FIXTURE
from test_hud_assault_render import (
    ROOT,
    _read,
    _lua_with_assault_state,
)

NATIVE_CASING_FIXTURE = r'''
_casing_orig_boundary = nil

do
    local corner = managers.hud._hud_assault_corner
    local casing_panel = _na.hud_panel:child("casing_panel")

    local icon_casingbox = casing_panel:rect({
        name = "icon_casingbox", x = 276, y = 0, w = 24, h = 24, visible = true,
    })
    icon_casingbox._alpha = 0.63

    local casing_bg_box = casing_panel:panel({
        x = 31, y = 0, w = 242, h = 38, visible = true,
    })
    casing_bg_box._alpha = 0.87
    corner._casing_bg_box = casing_bg_box

    casing_bg_box._script_data = {text_list = {}}
    function casing_bg_box:script() return self._script_data end

    local cas_bg = casing_bg_box:rect({name = "bg", x = 0, y = 0, w = 242, h = 38, visible = true})
    cas_bg._alpha = 0.43
    local cas_lt = casing_bg_box:rect({name = "left_top", x = 0, y = 0, w = 8, h = 8, visible = true})
    cas_lt._alpha = 0.43
    local cas_lb = casing_bg_box:rect({name = "left_bottom", x = 0, y = 30, w = 8, h = 8, visible = true})
    cas_lb._alpha = 0.43
    local cas_rt = casing_bg_box:rect({name = "right_top", x = 234, y = 0, w = 8, h = 8, visible = true})
    cas_rt._alpha = 0.43
    local cas_rb = casing_bg_box:rect({name = "right_bottom", x = 234, y = 30, w = 8, h = 8, visible = false})
    cas_rb._alpha = 0.43

    local cas_text_panel = casing_bg_box:panel({name = "text_panel", x = 0, y = 0, w = 196, h = 38, visible = true})
    cas_text_panel._alpha = 0.43
    cas_text_panel._script_data = {text_list = {}}
    function cas_text_panel:script() return self._script_data end
    function cas_text_panel:stop() end
    function cas_text_panel:clear()
        for _, child in pairs(self._children or {}) do
            child._alive = false
        end
        self._children = {}
    end

    local decoy_tp = casing_panel:panel({name = "text_panel", x = 0, y = 50, w = 200, h = 24, visible = true})
    decoy_tp._alpha = 0.55
    decoy_tp._script_data = {text_list = {"DECOY"}}
    function decoy_tp:script() return self._script_data end

    local cas_third_party = casing_panel:panel({
        name = "cas_third_party", x = 0, y = 80, w = 80, h = 16, visible = true,
    })
    cas_third_party._alpha = 0.59

    casing_panel:set_visible(false)

    _na.casing_panel = casing_panel
    _na.icon_casingbox = icon_casingbox
    _na.casing_bg_box = casing_bg_box
    _na.cas_bg = cas_bg
    _na.cas_lt = cas_lt
    _na.cas_lb = cas_lb
    _na.cas_rt = cas_rt
    _na.cas_rb = cas_rb
    _na.cas_text_panel = cas_text_panel
    _na.decoy_tp = decoy_tp
    _na.cas_third_party = cas_third_party
end

function GroupAIState:whisper_mode()
    return self._whisper_mode
end

do
    local state = managers.groupai:state()
    state._whisper_mode = false
end

do
    local prev_loc_text = managers.localization.text
    local casing_loc_map = {
        hud_casing_mode_ticker = "CASING MODE",
        hud_casing_mode_ticker_clean = "CIVILIAN MODE",
        hud_assault_end_line = "------------------------",
    }
    function managers.localization:text(key, macros)
        if casing_loc_map[key] then return casing_loc_map[key] end
        return prev_loc_text(self, key, macros)
    end
end

function HUDAssaultCorner:show_casing(mode)
    local nv = kyohud and kyohud.hud and kyohud.hud.native_visibility
    local entries = (nv and nv._entries) or {}
    local total_nv = 0
    local assault_nv = 0
    local alerts_nv = 0
    for _, e in ipairs(entries) do
        total_nv = total_nv + 1
        if e.owner == "assault" then assault_nv = assault_nv + 1 end
        if e.owner == "alerts" then alerts_nv = alerts_nv + 1 end
    end

    local A = kyohud and kyohud.hud and kyohud.hud.assault
    local assault_root_vis = nil
    if A and A._root_panel and type(A._root_panel.visible) == "function" then
        assault_root_vis = A._root_panel:visible()
    end

    local AL = kyohud and kyohud.hud and kyohud.hud.alerts
    local alerts_root_vis = nil
    if AL and AL._root_panel and type(AL._root_panel.visible) == "function" then
        alerts_root_vis = AL._root_panel:visible()
    end

    _casing_orig_boundary = {
        called = true,
        mode = mode,
        nv_count = total_nv,
        assault_nv_count = assault_nv,
        alerts_nv_count = alerts_nv,
        assault_root_vis = assault_root_vis,
        alerts_root_vis = alerts_root_vis,
        casing_flag_before = self._casing,
        casing_panel_vis_before = _na.casing_panel:visible(),
    }

    self._assault = false
    self._casing = true

    local casing_panel = self._hud_panel:child("casing_panel")
    local tp = casing_panel:child("text_panel")
    if tp and tp.script then
        tp:script().text_list = {}
    end
    self._casing_bg_box:script().text_list = {}

    local msg
    if mode == "civilian" then
        msg = {"hud_casing_mode_ticker_clean", "hud_assault_end_line",
               "hud_casing_mode_ticker_clean", "hud_assault_end_line"}
    else
        msg = {"hud_casing_mode_ticker", "hud_assault_end_line",
               "hud_casing_mode_ticker", "hud_assault_end_line"}
    end
    for _, text_id in ipairs(msg) do
        if tp and tp.script then
            table.insert(tp:script().text_list, text_id)
        end
        table.insert(self._casing_bg_box:script().text_list, text_id)
    end

    casing_panel:set_visible(true)
end

function HUDAssaultCorner:hide_casing()
    self._casing = false
    if self._casing_bg_box:child("text_panel") then
        self._casing_bg_box:child("text_panel"):stop()
        self._casing_bg_box:child("text_panel"):clear()
    end
    self._casing_bg_box:set_visible(false)
    _na.icon_casingbox._alpha = 0
end

function HUDManager:show_casing(mode)
    return self._hud_assault_corner:show_casing(mode)
end

function HUDManager:hide_casing()
    return self._hud_assault_corner:hide_casing()
end
'''


def _lua_with_assault_and_alerts_casing_slice(enable_alerts_val=False):
    lua, ok = _lua_with_assault_state(
        difficulty_stars=3, hostages=4, converted_alive=2,
        assault_mode=True, hunt_mode=False, assault_number=3,
    )
    if not ok:
        return lua, ok
    lua.execute('kyohud.settings.enable_alerts = ' + str(enable_alerts_val).lower())
    lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
    lua.execute(NATIVE_PNR_SHOW_FIXTURE)
    lua.execute(NATIVE_CASING_FIXTURE)
    lua.execute(r'''
        _HUDBGBox_animate_open_left_called = false
        _HUDBGBox_animate_open_left_params = nil

        function HUDBGBox_animate_open_left(panel, wait_t, target_w, done_cb, config)
            _HUDBGBox_animate_open_left_called = true
            _HUDBGBox_animate_open_left_params = {
                panel = panel,
                wait_t = wait_t,
                target_w = target_w,
                done_cb = done_cb,
                config = config,
            }
            coroutine.yield()
            if type(done_cb) == "function" then
                done_cb()
            end
        end

        function HUDAssaultCorner:_animate_show_texts(anim_object, texts)
            if type(texts) == "table" then
                for _, t in ipairs(texts) do
                    if t and type(t.set_visible) == "function" then
                        t:set_visible(true)
                    end
                end
            end
            coroutine.yield()
        end
    ''')
    alerts_src = _read(ALERTS_PATH)
    if alerts_src:
        lua.execute(alerts_src)
    return lua, ok


class CasingPreemptionTests(unittest.TestCase):
    """Native casing show must preempt acquired Assault before native writes."""

    def _run_casing_preemption(self, mode_literal, enable_alerts_val):
        lua, ok = _lua_with_assault_and_alerts_casing_slice(enable_alerts_val)
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")

        lua.execute(f'''
            local RT = kyohud.hud.runtime
            local A = kyohud.hud.assault
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            RT:update(managers.hud, 1.0, 0.05)

            assert(A._root_panel ~= nil,
                "Before: A._root_panel must exist after RT mount/update")
            assert(A._root_panel:visible() == true,
                "Before: A._root_panel must be visible during active assault")

            local before_nv = 0
            local before_assault_nv = 0
            for _, e in ipairs(nv._entries or {{}}) do
                before_nv = before_nv + 1
                if e.owner == "assault" then before_assault_nv = before_assault_nv + 1 end
            end
            assert(before_nv == 14,
                "Before: expected exactly 14 NV records, got " .. tostring(before_nv))
            assert(before_assault_nv == 14,
                "Before: all 14 NV records must be owned by assault, got " .. tostring(before_assault_nv))

            local corner = managers.hud._hud_assault_corner
            assert(corner._casing == false,
                "Before: native corner _casing must be false")
            assert(_na.casing_panel:visible() == false,
                "Before: native casing_panel must be hidden")

            managers.hud:show_casing({mode_literal})

            local obs = _casing_orig_boundary
            assert(type(obs) == "table" and obs.called == true,
                "Native original show_casing must execute")
            assert(obs.casing_flag_before == false,
                "Boundary observation must occur before native sets _casing")
            assert(obs.casing_panel_vis_before == false,
                "Boundary observation must occur before native sets casing_panel visible")

            assert(obs.assault_nv_count == 0 and obs.nv_count == 0,
                "RED: native original must see 0 NV records before native writes, got assault="
                .. tostring(obs.assault_nv_count) .. " alerts=" .. tostring(obs.alerts_nv_count)
                .. " total=" .. tostring(obs.nv_count))
            assert(obs.assault_root_vis == false,
                "RED: native original must see hidden owned Assault root before native writes, got "
                .. tostring(obs.assault_root_vis))

            assert(corner._casing == true,
                "Original native show must set corner._casing = true")
            assert(_na.casing_panel:visible() == true,
                "Original native show must set casing_panel visible = true")

            assert(_na.hud_panel:visible() == true,
                "Parent hud_panel must remain untouched")
            assert(_na.assault_panel:visible() == false,
                "Native assault_panel parent must remain untouched")
            assert(_na.hostages_panel:visible() == true,
                "Native hostages_panel parent must remain untouched")
            assert(_na.bg_box:visible() == true,
                "Native bg_box parent must remain untouched")
            assert(_na.third_party:visible() == true and _na.third_party:alpha() == 1,
                "Third-party sibling panel must remain untouched")
            assert(_na.cas_third_party:visible() == true
                and math.abs(_na.cas_third_party:alpha() - 0.59) < 0.001,
                "Casing third-party child must remain untouched")
            assert(_na.pnr_panel:visible() == false,
                "Native pnr_panel sentinel must remain untouched")
            assert(_na.buffs_panel:visible() == false,
                "Native buffs_panel sentinel must remain untouched")

            assert(kyohud.killstreak == _sentinel_before,
                "Combat sentinel must be preserved, got "
                .. tostring(kyohud.killstreak) .. " expected " .. tostring(_sentinel_before))
        ''')

    def test_normal_casing_show_preempts_assault_before_native_writes(self):
        self._run_casing_preemption('nil', True)

    def test_civilian_casing_show_preempts_assault_before_native_writes(self):
        self._run_casing_preemption('"civilian"', True)

    def test_normal_casing_show_preempts_assault_alerts_disabled(self):
        self._run_casing_preemption('nil', False)


class CasingStandardLifecycleTests(unittest.TestCase):
    """Standard casing replacement via runtime (RED state).

    With enable_alerts=true, RT:update after native show_casing must produce
    a visible owned casing ticker with correct text, acquire exactly 7 NV
    records (icon + 5 bg frame leaves visible=false, bg text_panel alpha=0),
    present _casing_a and _casing_b under a clipping ticker panel, move
    ticker x on tick, preserve primitive identities, and restore all native
    leaf properties on disable.
    """

    def test_standard_casing_lifecycle_with_alerts(self):
        lua, ok = _lua_with_assault_and_alerts_casing_slice(True)
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")

        lua.execute('''
            kyohud.settings.enable_alerts = true

            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            assert(type(AL) == "table", "kyohud.hud.alerts table must exist")
            assert(type(AL.mount) == "function",
                "RED: alerts:mount must be a function, got " .. tostring(type(AL.mount)))
            assert(type(AL.update) == "function",
                "RED: alerts:update must be a function, got " .. tostring(type(AL.update)))
            assert(type(AL.refresh_settings) == "function",
                "RED: alerts:refresh_settings must be a function, got " .. tostring(type(AL.refresh_settings)))

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(type(AL._casing_root_panel) == "table",
                "RED: AL._casing_root_panel must exist after standard casing show + RT:update")
            assert(AL._casing_root_panel:visible() == true,
                "RED: AL._casing_root_panel must be visible during standard casing")
            assert(AL:_verify_render() == true,
                "RED: AL:_verify_render() must return true during standard casing")
            assert(AL._casing_root_panel:parent() == RT._root_panel,
                "RED: AL._casing_root_panel parent must be RT._root_panel")

            assert(type(AL._casing_ticker_panel) == "table",
                "RED: AL._casing_ticker_panel must exist")
            assert(AL._casing_ticker_panel._clipping == true,
                "RED: AL._casing_ticker_panel must have clipping=true")

            assert(type(AL._casing_a) == "table",
                "RED: AL._casing_a must exist")
            assert(type(AL._casing_b) == "table",
                "RED: AL._casing_b must exist")
            assert(AL._casing_a:parent() == AL._casing_ticker_panel,
                "RED: AL._casing_a parent must be AL._casing_ticker_panel")
            assert(AL._casing_b:parent() == AL._casing_ticker_panel,
                "RED: AL._casing_b parent must be AL._casing_ticker_panel")

            local casing_a_text = AL._casing_a:text()
            assert(type(casing_a_text) == "string" and #casing_a_text > 0,
                "RED: _casing_a text must be nonempty, got " .. tostring(casing_a_text))
            assert(casing_a_text:find("CASING MODE") ~= nil,
                "RED: _casing_a text must contain CASING MODE, got " .. tostring(casing_a_text))

            local casing_b_text = AL._casing_b:text()
            assert(type(casing_b_text) == "string" and #casing_b_text > 0,
                "RED: _casing_b text must be nonempty, got " .. tostring(casing_b_text))

            local casing_leaves = {
                _na.icon_casingbox,
                _na.cas_bg,
                _na.cas_lt,
                _na.cas_lb,
                _na.cas_rt,
                _na.cas_rb,
            }
            for i, leaf in ipairs(casing_leaves) do
                assert(leaf:visible() == false,
                    "RED: native casing leaf #" .. tostring(i) .. " (" .. tostring(leaf._name)
                    .. ") must have visible=false while Alerts owns casing")
            end
            assert(math.abs(_na.cas_text_panel:alpha() - 0) < 0.001,
                "RED: native casing text_panel must have alpha=0 while Alerts owns casing, got "
                .. tostring(_na.cas_text_panel:alpha()))

            local alerts_nv = 0
            local total_nv = 0
            local nv_objects_vis = {}
            local nv_obj_alpha = nil
            for _, e in ipairs(nv._entries or {}) do
                total_nv = total_nv + 1
                if e.owner == "alerts" then
                    alerts_nv = alerts_nv + 1
                    if e.property == "visible" then
                        assert(e.applied_value == false,
                            "RED: alerts visible NV entry must set visible=false")
                        nv_objects_vis[e.object] = true
                    elseif e.property == "alpha" then
                        assert(e.applied_value == 0,
                            "RED: alerts alpha NV entry must set alpha=0")
                        nv_obj_alpha = e.object
                    end
                end
            end
            assert(alerts_nv == 7 and total_nv == 7,
                "RED: expected exactly 7 NV entries owned by 'alerts', got alerts="
                .. tostring(alerts_nv) .. " total=" .. tostring(total_nv))
            for _, leaf in ipairs(casing_leaves) do
                assert(nv_objects_vis[leaf] == true,
                    "RED: leaf " .. tostring(leaf._name) .. " must be tracked by NV owner 'alerts' visible=false")
            end
            assert(nv_obj_alpha == _na.cas_text_panel,
                "RED: cas_text_panel must be tracked by NV owner 'alerts' alpha=0")

            assert(_na.hud_panel:visible() == true, "hud_panel parent must remain visible")
            assert(_na.casing_panel:visible() == true,
                "casing_panel parent must remain visible (native parent never hidden)")
            assert(_na.casing_bg_box:visible() == true
                and math.abs(_na.casing_bg_box:alpha() - 0.87) < 0.001,
                "casing_bg_box parent must remain visible with original alpha 0.87")
            assert(_na.decoy_tp:visible() == true
                and math.abs(_na.decoy_tp:alpha() - 0.55) < 0.001,
                "decoy text_panel must remain untouched (visible=true, alpha=0.55)")
            assert(_na.cas_third_party:visible() == true
                and math.abs(_na.cas_third_party:alpha() - 0.59) < 0.001,
                "casing third-party child must remain untouched")
            assert(_na.third_party:visible() == true and _na.third_party:alpha() == 1,
                "assault third_party panel must remain untouched")
            assert(_na.pnr_panel:visible() == false,
                "pnr_panel sentinel must remain untouched")

            local saved_casing_root = AL._casing_root_panel
            local saved_casing_a = AL._casing_a
            local saved_casing_b = AL._casing_b
            local panel_id_after_first = _panel_id

            local clip_x = AL._casing_ticker_panel:x()
            local casing_x_before = AL._casing_a:x()

            RT:update(managers.hud, 1.05, 0.05)

            local casing_x_after = AL._casing_a:x()
            assert(casing_x_after < casing_x_before,
                "RED: _casing_a x must move left after tick, before="
                .. casing_x_before .. " after=" .. casing_x_after)
            assert(AL._casing_ticker_panel:x() == clip_x,
                "RED: _casing_ticker_panel x must remain fixed")

            assert(rawequal(saved_casing_a, AL._casing_a),
                "RED: _casing_a identity must be preserved")
            assert(rawequal(saved_casing_b, AL._casing_b),
                "RED: _casing_b identity must be preserved")
            assert(rawequal(saved_casing_root, AL._casing_root_panel),
                "RED: _casing_root_panel identity must be preserved")
            assert(_panel_id == panel_id_after_first,
                "RED: no extra Diesel primitives may be created on subsequent ticks, before="
                .. tostring(panel_id_after_first) .. " after=" .. tostring(_panel_id))

            kyohud.settings.enable_alerts = false
            RT:refresh_settings(managers.hud)

            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "RED: disabling enable_alerts must immediately hide or remove AL._casing_root_panel")

            local remaining_nv = 0
            for _ in ipairs(nv._entries or {}) do
                remaining_nv = remaining_nv + 1
            end
            assert(remaining_nv == 0,
                "RED: disabling enable_alerts must immediately clear all NV records, got "
                .. tostring(remaining_nv))

            assert(math.abs(_na.cas_text_panel:alpha() - 0.43) < 0.001,
                "RED: cas_text_panel must restore alpha=0.43, got " .. tostring(_na.cas_text_panel:alpha()))
            assert(_na.icon_casingbox:visible() == true
                and math.abs(_na.icon_casingbox:alpha() - 0.63) < 0.001,
                "RED: icon_casingbox must restore visible=true and alpha=0.63")
            assert(_na.cas_bg:visible() == true and math.abs(_na.cas_bg:alpha() - 0.43) < 0.001,
                "RED: cas_bg must restore visible=true and alpha=0.43")
            assert(_na.cas_lt:visible() == true and math.abs(_na.cas_lt:alpha() - 0.43) < 0.001,
                "RED: cas_lt must restore visible=true and alpha=0.43")
            assert(_na.cas_lb:visible() == true and math.abs(_na.cas_lb:alpha() - 0.43) < 0.001,
                "RED: cas_lb must restore visible=true and alpha=0.43")
            assert(_na.cas_rt:visible() == true and math.abs(_na.cas_rt:alpha() - 0.43) < 0.001,
                "RED: cas_rt must restore visible=true and alpha=0.43")
            assert(_na.cas_rb:visible() == false and math.abs(_na.cas_rb:alpha() - 0.43) < 0.001,
                "RED: cas_rb must restore exact prior visible=false and alpha=0.43")

            assert(_na.decoy_tp:visible() == true
                and math.abs(_na.decoy_tp:alpha() - 0.55) < 0.001,
                "RED: decoy text_panel must remain untouched after disable")
            assert(_na.casing_panel:visible() == true,
                "RED: casing_panel parent must remain visible after disable")
            assert(_na.casing_bg_box:visible() == true
                and math.abs(_na.casing_bg_box:alpha() - 0.87) < 0.001,
                "RED: casing_bg_box parent must remain visible with alpha 0.87")
            assert(_na.cas_third_party:visible() == true
                and math.abs(_na.cas_third_party:alpha() - 0.59) < 0.001,
                "RED: casing third-party must remain untouched")

            assert(kyohud.killstreak == _sentinel_before,
                "Combat sentinel must be preserved")
        ''')


class CasingHideAndCoexistenceTests(unittest.TestCase):
    """Casing hide + whisper + unsupported mode + PNR coexistence (RED state).

    - hide_casing while whisper_mode=true must end owned casing without
      inventing furtif/loud banners.
    - Native casing_panel stays visible (parent never hidden), bg_box visible
      false, icon alpha 0 after native hide.
    - Must NOT veto later standard PNR show/feed/runtime.
    - Unsupported casing mode preserves native / no owned overlay.
    - PNR+casing simultaneous: native fallback, not overlapping.
    """

    def test_casing_hide_whisper_then_pnr_runtime(self):
        lua, ok = _lua_with_assault_and_alerts_casing_slice(True)
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")

        lua.execute('''
            kyohud.settings.enable_alerts = true

            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local state = managers.groupai:state()
            local corner = managers.hud._hud_assault_corner

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(type(AL._casing_root_panel) == "table" and AL._casing_root_panel:visible() == true,
                "RED: positive prerequisite must have visible AL._casing_root_panel")

            local pos_alerts_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then pos_alerts_nv = pos_alerts_nv + 1 end
            end
            assert(pos_alerts_nv == 7,
                "RED: positive prerequisite must acquire 7 NV records, got "
                .. tostring(pos_alerts_nv))

            state._whisper_mode = true

            managers.hud:hide_casing()

            assert(corner._casing == false,
                "Native hide must set corner._casing = false")
            assert(_na.casing_panel:visible() == true,
                "casing_panel parent must remain visible (native parent never hidden)")
            assert(_na.casing_bg_box:visible() == false,
                "casing_bg_box must be visible=false after native hide")
            assert(math.abs(_na.icon_casingbox:alpha() - 0) < 0.001,
                "icon_casingbox alpha must be 0 after native hide")

            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "RED: after native hide_casing, owned casing root must be hidden or removed")

            local after_hide_nv = 0
            for _ in ipairs(nv._entries or {}) do
                after_hide_nv = after_hide_nv + 1
            end
            assert(after_hide_nv == 0,
                "RED: after native hide_casing, NV records must be 0, got " .. tostring(after_hide_nv))

            assert(_na.decoy_tp:visible() == true
                and math.abs(_na.decoy_tp:alpha() - 0.55) < 0.001,
                "decoy text_panel must remain untouched after hide")
            assert(_na.cas_third_party:visible() == true
                and math.abs(_na.cas_third_party:alpha() - 0.59) < 0.001,
                "casing third-party must remain untouched after hide")

            state._point_of_no_return_timer = 65.9
            state._point_of_no_return_id = 101
            state._point_of_no_return_tweak_id = "noreturn"
            state._is_inside_point_of_no_return = false
            managers.hud:show_point_of_no_return_timer("noreturn")
            managers.hud:feed_point_of_no_return_timer(65.9, false)
            RT:update(managers.hud, 1.1, 0.05)

            assert(corner._point_of_no_return == true,
                "After hide_casing: PNR show must set corner._point_of_no_return = true")
            assert(_na.pnr_panel:visible() == true,
                "After hide_casing: PNR show must set pnr_panel visible = true")

            assert(type(AL._root_panel) == "table" and AL._root_panel:visible() == true,
                "RED: PNR replacement must work after hide_casing")

            local pnr_timer = AL._root_panel:child("pnr_timer")
            assert(type(pnr_timer) == "table" and pnr_timer:text() == "01:05",
                "RED: PNR timer text must be correct after hide_casing, got "
                .. tostring(pnr_timer and pnr_timer:text()))

            assert(kyohud.killstreak == _sentinel_before,
                "Combat sentinel must be preserved")
        ''')

    def test_unsupported_casing_mode_preserves_native(self):
        lua, ok = _lua_with_assault_and_alerts_casing_slice(True)
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")

        lua.execute('''
            kyohud.settings.enable_alerts = true

            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(type(AL._casing_root_panel) == "table" and AL._casing_root_panel:visible() == true,
                "RED: positive prerequisite must have visible AL._casing_root_panel")
            local pos_nv = 0
            for _ in ipairs(nv._entries or {}) do
                pos_nv = pos_nv + 1
            end
            assert(pos_nv == 7,
                "RED: positive prerequisite must acquire 7 NV records, got " .. tostring(pos_nv))

            managers.hud:show_casing("custom_unsupported_mode")
            RT:update(managers.hud, 1.05, 0.05)

            local total_nv = 0
            for _ in ipairs(nv._entries or {}) do
                total_nv = total_nv + 1
            end
            assert(total_nv == 0,
                "RED: unsupported casing mode must have 0 NV records, got " .. tostring(total_nv))

            assert(_na.casing_panel:visible() == true,
                "Native casing_panel must remain visible during unsupported casing")
            assert(_na.casing_bg_box:visible() == true,
                "Native casing_bg_box must remain visible during unsupported casing")
            assert(_na.icon_casingbox:visible() == true
                and math.abs(_na.icon_casingbox:alpha() - 0.63) < 0.001,
                "Native icon_casingbox must remain untouched")
            assert(_na.cas_bg:visible() == true and math.abs(_na.cas_bg:alpha() - 0.43) < 0.001,
                "Native cas_bg must remain untouched")
            assert(_na.cas_rb:visible() == false,
                "Native cas_rb must preserve exact prior visible=false")
            assert(math.abs(_na.cas_text_panel:alpha() - 0.43) < 0.001,
                "Native cas_text_panel must remain at alpha=0.43")

            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "RED: unsupported casing must not leave owned root visible")

            assert(kyohud.killstreak == _sentinel_before,
                "Combat sentinel must be preserved")
        ''')

    def test_pnr_and_casing_simultaneous_native_fallback(self):
        lua, ok = _lua_with_assault_and_alerts_casing_slice(True)
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")

        lua.execute('''
            kyohud.settings.enable_alerts = true

            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local state = managers.groupai:state()
            local corner = managers.hud._hud_assault_corner

            RT:mount(managers.hud)
            managers.hud:show_casing(nil)
            RT:update(managers.hud, 1.0, 0.05)

            assert(corner._casing == true, "Prerequisite: corner._casing must be true")

            state._point_of_no_return_timer = 65.9
            state._point_of_no_return_id = 101
            state._point_of_no_return_tweak_id = "noreturn"
            state._is_inside_point_of_no_return = false
            managers.hud:show_point_of_no_return_timer("noreturn")

            assert(corner._point_of_no_return == true,
                "PNR show during casing must set corner._point_of_no_return = true")

            RT:update(managers.hud, 1.05, 0.05)

            local total_nv = 0
            local alerts_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                total_nv = total_nv + 1
                if e.owner == "alerts" then alerts_nv = alerts_nv + 1 end
            end
            assert(total_nv == 0,
                "RED: PNR+casing overlap must have 0 NV records, got " .. tostring(total_nv))
            assert(AL._root_panel == nil or AL._root_panel:visible() == false,
                "RED: AL._root_panel must be absent or hidden after PNR+casing overlap")
            assert(AL._casing_root_panel == nil or AL._casing_root_panel:visible() == false,
                "RED: AL._casing_root_panel must be absent or hidden after PNR+casing overlap")

            assert(_na.pnr_panel:visible() == true,
                "Native pnr_panel must be visible during PNR+casing overlap")
            assert(_na.casing_panel:visible() == true,
                "Native casing_panel must remain visible during PNR+casing overlap")

            assert(kyohud.killstreak == _sentinel_before,
                "Combat sentinel must be preserved")
        ''')
