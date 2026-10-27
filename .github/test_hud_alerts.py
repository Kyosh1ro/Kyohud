"""LOT3b -- hud/alerts.lua: vertical slices 1 & 2 (RED state for slice 2).

Slice 1: native PNR show immediately preempts already-acquired Assault, even when
enable_alerts=false, BEFORE the native show method performs its own writes or
animations, and without requiring any subsequent manager:update repair tick.

Slice 2: standard Point of No Return (PNR) replacement via HUD runtime:
  - Lifecycle coordinated via RT:mount / RT:update / RT:refresh_settings
  - Owned alerts._root_panel with persistent children pnr_timer, pnr_status,
    and pnr_title, verified via alerts:_verify_render()
  - Acquires visible=false on the 8 exact native PNR leaves under owner "alerts"
    (icon_noreturnbox on point_of_no_return_panel, plus point_of_no_return_text,
    point_of_no_return_timer, bg, left_top, left_bottom, right_top, right_bottom
    on unnamed corner._noreturn_bg_box) while leaving native parents and
    third-party panels untouched
  - Restores exact nonstandard original leaf properties and clears owner "alerts"
    NV records immediately on disable (enable_alerts=false + RT:refresh_settings)
    or when transitioning from a verified positive state to an unsupported PNR
    state (unsupported tweak_id and/or is_inside == nil).

Fixture fidelity note (scheduled coroutine vs fully simulated):
  - In native PAYDAY 2 (hudassaultcorner.lua:1015-1029, 1041-1063, 1193-1251),
    show_point_of_no_return_timer(id) schedules _animate_show_noreturn via
    point_of_no_return_panel:animate(...) (which yields for delay_time, sets
    point_of_no_return_panel visible, runs HUDBGBox_animate_open_left, and in
    open_done runs _animate_show_texts), and flash_point_of_no_return_timer(beep)
    schedules a flash_timer coroutine on point_of_no_return_timer:animate(...).
  - Because unit tests do not run a multi-frame Diesel coroutine scheduler,
    show_point_of_no_return_timer and flash_point_of_no_return_timer record the
    scheduled animation boundary and synchronously apply the post-show panel
    visibility/state (self._assault = false, self:_update_noreturn(id),
    point_of_no_return_panel:set_visible(true), self._point_of_no_return = true).
  - By contrast, feed_point_of_no_return_timer(time, is_inside) and
    _get_noreturn_data(id) / _update_noreturn(id) / hide_point_of_no_return_timer()
    are fully simulated per hudassaultcorner.lua:330-395, 1005-1039.
"""
from pathlib import Path
import unittest

from test_hud_assault_render import (
    ROOT,
    _read,
    _lua_with_assault_state,
)

ALERTS_PATH = ROOT / "lua" / "hud" / "alerts.lua"

NATIVE_PNR_SHOW_FIXTURE = r'''
_pnr_orig_boundary = nil

tweak_data = tweak_data or {}
tweak_data.hud_corner = tweak_data.hud_corner or {
    assault_font = "fonts/font_medium_mf",
    noreturn_size = 24,
}
tweak_data.point_of_no_returns = tweak_data.point_of_no_returns or {
    noreturn = {
        text_id = "hud_assault_point_no_return_in",
        texture = "guis/textures/pd2/hud_icon_noreturnbox",
        texture_rect = {0, 0, 32, 32},
        color = Color(1, 1, 0, 0),
        timer_flash_color = Color(1, 1, 0.8, 0.2),
        attention_color = Color(1, 1, 1, 1),
        scale_box = false,
    },
    custom_unsupported_variant = {
        text_id = "hud_assault_point_no_return_custom",
        texture = "guis/textures/pd2/hud_icon_noreturnbox",
        texture_rect = {0, 0, 24, 24},
        color = Color(1, 1, 0, 1),
        timer_flash_color = Color(1, 1, 0.5, 1),
        attention_color = Color(1, 1, 1, 1),
        scale_box = true,
    },
}

do
    local prev_text = managers.localization and managers.localization.text
    local pnr_loc_map = {
        ky_hud_pnr_inside = "INSIDE",
        ky_hud_pnr_outside = "OUTSIDE",
        ky_hud_pnr_title = "POINT OF NO RETURN",
        hud_assault_point_no_return_in = "POINT OF NO RETURN IN",
        hud_assault_point_no_return = "POINT OF NO RETURN",
        hud_assault_point_no_return_custom = "CUSTOM NO RETURN",
    }
    managers.localization = managers.localization or {}
    function managers.localization:text(key, macros)
        if pnr_loc_map[key] then
            return pnr_loc_map[key]
        end
        if prev_text then
            return prev_text(self, key, macros)
        end
        return "LOC:" .. tostring(key)
    end
    function managers.localization:to_upper_text(key, macros)
        return string.upper(self:text(key, macros))
    end
end

function GroupAIState:get_point_of_no_return_timer()
    return self._point_of_no_return_timer, self._point_of_no_return_id
end

do
    local state = managers.groupai:state()
    state._point_of_no_return_timer = nil
    state._point_of_no_return_id = nil
    state._point_of_no_return_tweak_id = nil
    state._is_inside_point_of_no_return = nil

    local corner = managers.hud._hud_assault_corner
    corner._bg_box_size = 242
    local pnr_panel = _na.pnr_panel
    pnr_panel._alpha = 0.91

    local icon_noreturnbox = pnr_panel:rect({
        name = "icon_noreturnbox", x = 276, y = 0, w = 24, h = 24, visible = true,
    })
    icon_noreturnbox._alpha = 0.63

    -- Unnamed _noreturn_bg_box created by HUDBGBox_create(point_of_no_return_panel, ...)
    local noreturn_bg_box = pnr_panel:panel({
        x = 31, y = 0, w = 242, h = 38, visible = true,
    })
    noreturn_bg_box._alpha = 0.87
    corner._noreturn_bg_box = noreturn_bg_box

    local pnr_bg = noreturn_bg_box:rect({name = "bg", x = 0, y = 0, w = 242, h = 38, visible = true})
    pnr_bg._alpha = 0.41
    local pnr_lt = noreturn_bg_box:rect({name = "left_top", x = 0, y = 0, w = 8, h = 8, visible = true})
    pnr_lt._alpha = 0.42
    local pnr_lb = noreturn_bg_box:rect({name = "left_bottom", x = 0, y = 30, w = 8, h = 8, visible = true})
    pnr_lb._alpha = 0.43
    local pnr_rt = noreturn_bg_box:rect({name = "right_top", x = 234, y = 0, w = 8, h = 8, visible = true})
    pnr_rt._alpha = 0.44
    -- Nonstandard original leaf visibility (false) to verify exact restoration on release
    local pnr_rb = noreturn_bg_box:rect({name = "right_bottom", x = 234, y = 30, w = 8, h = 8, visible = false})
    pnr_rb._alpha = 0.45

    local pnr_text = noreturn_bg_box:text({
        name = "point_of_no_return_text", x = 0, y = 0, w = 196, h = 38,
        text = "POINT OF NO RETURN IN", font = "fonts/font_medium_mf", font_size = 24, visible = true,
    })
    pnr_text._alpha = 0.77

    local pnr_timer = noreturn_bg_box:text({
        name = "point_of_no_return_timer", x = 196, y = 0, w = 46, h = 38,
        text = "00:00", font = "fonts/font_medium_mf", font_size = 24, visible = true,
    })
    pnr_timer._alpha = 0.81

    local pnr_third_party = pnr_panel:panel({
        name = "pnr_third_party", x = 0, y = 20, w = 80, h = 16, visible = true,
    })
    pnr_third_party._alpha = 0.59

    _na.icon_noreturnbox = icon_noreturnbox
    _na.noreturn_bg_box = noreturn_bg_box
    _na.pnr_bg = pnr_bg
    _na.pnr_lt = pnr_lt
    _na.pnr_lb = pnr_lb
    _na.pnr_rt = pnr_rt
    _na.pnr_rb = pnr_rb
    _na.pnr_text = pnr_text
    _na.pnr_timer = pnr_timer
    _na.pnr_third_party = pnr_third_party
end

function HUDAssaultCorner:_get_noreturn_data(id)
    local pnr_td = tweak_data and tweak_data.point_of_no_returns or {}
    local noreturn_tweak_data = (id and pnr_td[id]) or pnr_td.noreturn or {}
    local noreturn_data = {}

    noreturn_data.color = noreturn_tweak_data.color or Color(1, 1, 0, 0)
    noreturn_data.flash_color = noreturn_tweak_data.timer_flash_color or noreturn_tweak_data.color or Color(1, 1, 0.8, 0.2)
    noreturn_data.attention_color = noreturn_tweak_data.attention_color or Color(1, 1, 1, 1)
    noreturn_data.icon_texture = noreturn_tweak_data.texture or "guis/textures/pd2/hud_icon_noreturnbox"
    noreturn_data.icon_texture_rect = noreturn_tweak_data.texture_rect or nil
    noreturn_data.scale_box = noreturn_tweak_data.scale_box or false
    noreturn_data.text_id = noreturn_tweak_data.text_id

    if not noreturn_data.text_id then
        if _G.IS_VR then
            noreturn_data.text_id = "hud_assault_point_no_return"
        else
            noreturn_data.text_id = "hud_assault_point_no_return_in"
        end
    end

    return noreturn_data
end

function HUDAssaultCorner:_update_noreturn(id)
    local point_of_no_return_panel = self._hud_panel and self._hud_panel:child("point_of_no_return_panel")
    local icon_noreturnbox = point_of_no_return_panel and point_of_no_return_panel:child("icon_noreturnbox")
    local point_of_no_return_text = self._noreturn_bg_box and self._noreturn_bg_box:child("point_of_no_return_text")
    local point_of_no_return_timer = self._noreturn_bg_box and self._noreturn_bg_box:child("point_of_no_return_timer")
    local noreturn_data = self:_get_noreturn_data(id)

    if point_of_no_return_text and (not self._noreturn_data or noreturn_data.text_id ~= self._noreturn_data.text_id) then
        point_of_no_return_text:set_text(managers.localization:to_upper_text(noreturn_data.text_id))
    end
    if point_of_no_return_text then point_of_no_return_text:set_color(noreturn_data.color) end
    if point_of_no_return_timer then point_of_no_return_timer:set_color(noreturn_data.color) end
    if icon_noreturnbox then icon_noreturnbox:set_color(noreturn_data.color) end

    self._noreturn_data = noreturn_data
end

function HUDAssaultCorner:feed_point_of_no_return_timer(time, is_inside)
    -- Fully simulated per hudassaultcorner.lua:1005-1013
    time = math.floor(time)

    local minutes = math.floor(time / 60)
    local seconds = math.round(time - minutes * 60)
    local text = (minutes < 10 and "0" .. minutes or minutes) .. ":" .. (seconds < 10 and "0" .. seconds or seconds)

    if self._noreturn_bg_box and self._noreturn_bg_box:child("point_of_no_return_timer") then
        self._noreturn_bg_box:child("point_of_no_return_timer"):set_text(text)
    end
end

function HUDAssaultCorner:show_point_of_no_return_timer(tweak_id)
    local nv = kyohud and kyohud.hud and kyohud.hud.native_visibility
    local entries = (nv and nv._entries) or {}
    local total_nv = 0
    local assault_nv = 0
    for _, e in ipairs(entries) do
        total_nv = total_nv + 1
        if e.owner == "assault" then
            assault_nv = assault_nv + 1
        end
    end

    local A = kyohud and kyohud.hud and kyohud.hud.assault
    local assault_root_vis = nil
    if A and A._root_panel and type(A._root_panel.visible) == "function" then
        assault_root_vis = A._root_panel:visible()
    end

    local restore_leaves = {
        _na.bg_leaf, _na.left_top, _na.left_bottom, _na.right_top,
        _na.h_bg, _na.h_lt, _na.h_lb, _na.h_rt, _na.h_rb,
        _na.num_hostages, _na.icon_assaultbox, _na.hostages_icon,
    }
    local all_leaves_restored = true
    for _, leaf in ipairs(restore_leaves) do
        if leaf:visible() ~= true then
            all_leaves_restored = false
            break
        end
    end

    _pnr_orig_boundary = {
        called = true,
        tweak_id = tweak_id,
        pnr_flag_before_write = self._point_of_no_return,
        pnr_panel_vis_before_write = _na.pnr_panel:visible(),
        nv_count = total_nv,
        assault_nv_count = assault_nv,
        assault_root_vis = assault_root_vis,
        tp_alpha = _na.text_panel:alpha(),
        all_leaves_restored = all_leaves_restored,
        right_bottom_vis = _na.right_bottom:visible(),
    }

    -- Native show_point_of_no_return_timer schedules coroutines, but this fixture
    -- represents the COMPLETED state: opening/text animations have already finished.
    -- Set the post-show contract synchronously, matching original 4 tests.
    self._assault = false
    self:_update_noreturn(tweak_id)
    local pnr_panel = self._hud_panel and self._hud_panel:child("point_of_no_return_panel")
    if pnr_panel then
        pnr_panel:set_visible(true)
    end
    self._point_of_no_return = true
end

function HUDAssaultCorner:hide_point_of_no_return_timer()
    local pnr_panel = self._hud_panel and self._hud_panel:child("point_of_no_return_panel")
    if pnr_panel then
        pnr_panel:set_visible(false)
    end
    self._point_of_no_return = false
end

function HUDAssaultCorner:flash_point_of_no_return_timer(beep)
    -- Native schedules flash_timer coroutine on point_of_no_return_timer:animate(...)
    self._last_flash_beep = (beep == true)
end

function HUDManager:show_point_of_no_return_timer(tweak_id)
    return self._hud_assault_corner:show_point_of_no_return_timer(tweak_id)
end

function HUDManager:hide_point_of_no_return_timer()
    return self._hud_assault_corner:hide_point_of_no_return_timer()
end

function HUDManager:feed_point_of_no_return_timer(time, is_inside)
    return self._hud_assault_corner:feed_point_of_no_return_timer(time, is_inside)
end

function HUDManager:flash_point_of_no_return_timer(beep)
    return self._hud_assault_corner:flash_point_of_no_return_timer(beep)
end
'''


def _lua_with_assault_and_alerts_slice():
    lua, ok = _lua_with_assault_state(
        difficulty_stars=3, hostages=4, converted_alive=2,
        assault_mode=True, hunt_mode=False, assault_number=3,
    )
    if not ok:
        return lua, ok
    lua.execute('kyohud.settings.enable_alerts = false')
    lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')
    lua.execute(NATIVE_PNR_SHOW_FIXTURE)
    # Define HUDBGBox_animate_open_left BEFORE loading alerts.lua
    # Native signature: (panel, wait_t, target_w, done_cb, config)
    # Native behavior (hudobjectives.lua:143-184): yields once, calls done_cb before return
    # done_cb starts _animate_show_texts which sets text/timer visible=true BEFORE first yield
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


class AlertsPnrImmediatePreemptionTests(unittest.TestCase):
    """Native PNR show must preempt acquired Assault before native writes."""

    def _run_pnr_preemption_case(self, tweak_id_lua_literal):
        lua, ok = _lua_with_assault_and_alerts_slice()
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")

        lua.execute(f'''
            local RT = kyohud.hud.runtime
            local A = kyohud.hud.assault
            local nv = kyohud.hud.native_visibility

            RT:mount(managers.hud)
            RT:update(managers.hud, 1.0, 0.05)

            assert(A._root_panel ~= nil,
                "Before: A._root_panel must exist after RT mount/update")
            assert(A._root_panel:visible() == true,
                "Before: A._root_panel must be visible during active assault")

            local before_nv = 0
            for _, e in ipairs(nv._entries or {{}}) do
                before_nv = before_nv + 1
                assert(e.owner == "assault",
                    "Before: all 14 NV entries must be owned by assault")
            end
            assert(before_nv == 14,
                "Before: expected exactly 14 NV records, got " .. tostring(before_nv))

            local saved_root = A._root_panel
            local corner = managers.hud._hud_assault_corner
            assert(corner._point_of_no_return == false,
                "Before: native corner _point_of_no_return must be false")
            assert(_na.pnr_panel:visible() == false,
                "Before: native point_of_no_return_panel must be hidden")

            managers.hud:show_point_of_no_return_timer({tweak_id_lua_literal})

            local obs = _pnr_orig_boundary
            assert(type(obs) == "table" and obs.called == true,
                "Native original show_point_of_no_return_timer must execute")
            assert(obs.pnr_flag_before_write == false,
                "Boundary observation must occur before native sets _point_of_no_return")
            assert(obs.pnr_panel_vis_before_write == false,
                "Boundary observation must occur before native sets pnr_panel visible")

            assert(obs.assault_nv_count == 0 and obs.nv_count == 0,
                "RED: native original must see 0 Assault NV records before native writes, got assault="
                .. tostring(obs.assault_nv_count) .. " total=" .. tostring(obs.nv_count))
            assert(obs.assault_root_vis == false,
                "RED: native original must see hidden owned Assault root before native writes, got "
                .. tostring(obs.assault_root_vis))
            assert(math.abs(obs.tp_alpha - 0.37) < 0.01,
                "RED: text_panel alpha must be restored to 0.37 before native writes, got "
                .. tostring(obs.tp_alpha))
            assert(obs.all_leaves_restored == true,
                "RED: all 12 static leaves must be restored to visible=true before native writes")
            assert(obs.right_bottom_vis == false,
                "RED: decorative right_bottom leaf must remain visible=false before native writes")

            assert(corner._point_of_no_return == true,
                "Original native show must set corner._point_of_no_return = true")
            assert(_na.pnr_panel:visible() == true,
                "Original native show must set point_of_no_return_panel visible = true")

            local after_nv = 0
            for _ in ipairs(nv._entries or {{}}) do
                after_nv = after_nv + 1
            end
            assert(after_nv == 0,
                "After show (no update tick): NV records must remain 0, got " .. tostring(after_nv))
            assert(A._root_panel:visible() == false,
                "After show (no update tick): owned Assault root must remain hidden")
            assert(rawequal(A._root_panel, saved_root),
                "Owned Assault root panel identity must be preserved")

            assert(_na.hud_panel:visible() == true,
                "Parent hud_panel must remain untouched")
            assert(_na.assault_panel:visible() == false,
                "Native assault_panel parent must remain untouched")
            assert(_na.hostages_panel:visible() == true,
                "Native hostages_panel parent must remain untouched")
            assert(_na.bg_box:visible() == true,
                "Native bg_box parent must remain untouched")
            assert(_na.hostages_bg_box:visible() == true,
                "Native hostages_bg_box parent must remain untouched")
            assert(_na.third_party:visible() == true and _na.third_party:alpha() == 1,
                "Third-party sibling panel must remain untouched")
            assert(_na.ap_text_panel:visible() == true and _na.ap_text_panel:alpha() == 1,
                "Assault panel text_panel sibling must remain untouched")
            assert(_na.casing_panel:visible() == false,
                "Native casing_panel sentinel must remain untouched")
            assert(_na.buffs_panel:visible() == false,
                "Native buffs_panel sentinel must remain untouched")

            assert(kyohud.killstreak == _sentinel_before,
                "Combat sentinel must be preserved, got "
                .. tostring(kyohud.killstreak) .. " expected " .. tostring(_sentinel_before))
        ''')

    def test_standard_pnr_show_preempts_assault_before_native_writes(self):
        self._run_pnr_preemption_case('"noreturn"')

    def test_unsupported_pnr_variant_show_preempts_assault_before_native_writes(self):
        self._run_pnr_preemption_case('"custom_unsupported_variant"')


class AlertsStandardPnrReplacementTests(unittest.TestCase):
    """Standard PNR replacement via runtime (RED state).

    Fixture note:
      - HUDAssaultCorner:show_point_of_no_return_timer in real PAYDAY 2 schedules
        _animate_show_noreturn as a coroutine; this fixture applies the post-show
        visibility/state synchronously without coroutine ticks.
      - HUDAssaultCorner:feed_point_of_no_return_timer is fully simulated per
        hudassaultcorner.lua:1005-1013, and GroupAIState PNR fields
        (_point_of_no_return_timer, _point_of_no_return_id,
        _point_of_no_return_tweak_id, _is_inside_point_of_no_return) mirror
        groupaistatebase.lua:2711-2893.
    """

    def test_standard_pnr_lifecycle_feed_transitions_and_disable_restore(self):
        lua, ok = _lua_with_assault_and_alerts_slice()
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")

        lua.execute('''
            kyohud.settings.enable_alerts = true

            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local state = managers.groupai:state()

            assert(type(AL) == "table", "kyohud.hud.alerts table must exist")
            assert(type(AL.mount) == "function",
                "RED: alerts:mount must be a function, got " .. tostring(type(AL.mount)))
            assert(type(AL.update) == "function",
                "RED: alerts:update must be a function, got " .. tostring(type(AL.update)))
            assert(type(AL.refresh_settings) == "function",
                "RED: alerts:refresh_settings must be a function, got " .. tostring(type(AL.refresh_settings)))
            assert(type(AL._verify_render) == "function",
                "RED: alerts:_verify_render must be a function, got " .. tostring(type(AL._verify_render)))

            RT:mount(managers.hud)

            -- Mirror GroupAIStateBase:set_point_of_no_return_timer + first _update_point_of_no_return
            state._point_of_no_return_timer = 65.9
            state._point_of_no_return_id = 101
            state._point_of_no_return_tweak_id = "noreturn"
            state._is_inside_point_of_no_return = false
            managers.hud:show_point_of_no_return_timer("noreturn")
            managers.hud:feed_point_of_no_return_timer(65.9, false)

            RT:update(managers.hud, 1.0, 0.05)

            assert(type(AL._root_panel) == "table",
                "RED: AL._root_panel must exist after standard PNR show+feed and RT:update")
            assert(AL._root_panel:parent() == RT._root_panel,
                "RED: AL._root_panel parent must be RT._root_panel")
            assert(AL._root_panel:visible() == true,
                "RED: AL._root_panel must be visible during standard PNR")
            assert(AL:_verify_render() == true,
                "RED: AL:_verify_render() must return true during standard PNR")

            local pnr_timer = AL._root_panel:child("pnr_timer")
            local pnr_status = AL._root_panel:child("pnr_status")
            local pnr_title = AL._root_panel:child("pnr_title")
            assert(type(pnr_timer) == "table" and pnr_timer:visible() == true,
                "RED: persistent child pnr_timer must exist and be visible")
            assert(type(pnr_status) == "table" and pnr_status:visible() == true,
                "RED: persistent child pnr_status must exist and be visible")
            assert(type(pnr_title) == "table" and pnr_title:visible() == true,
                "RED: persistent child pnr_title must exist and be visible")

            assert(pnr_timer:text() == "01:05",
                "RED: pnr_timer text for 65.9s must be '01:05', got " .. tostring(pnr_timer:text()))

            local outside_text = pnr_status:text()
            assert(type(outside_text) == "string" and #outside_text > 0,
                "RED: pnr_status text must be nonempty when is_inside=false")
            assert(not outside_text:find("^LOC:"),
                "RED: pnr_status must not be raw LOC fallback, got " .. tostring(outside_text))
            assert(outside_text:upper():find("OUTSIDE") ~= nil,
                "RED: pnr_status when is_inside=false must contain OUTSIDE, got " .. tostring(outside_text))

            local title_text = pnr_title:text()
            assert(type(title_text) == "string" and #title_text > 0 and not title_text:find("^LOC:"),
                "RED: pnr_title text must be nonempty and not raw LOC fallback, got " .. tostring(title_text))

            -- Native 8 exact PNR leaves must be hidden via NV owner "alerts"
            local pnr_leaves = {
                _na.icon_noreturnbox,
                _na.pnr_text,
                _na.pnr_timer,
                _na.pnr_bg,
                _na.pnr_lt,
                _na.pnr_lb,
                _na.pnr_rt,
                _na.pnr_rb,
            }
            for i, leaf in ipairs(pnr_leaves) do
                assert(leaf:visible() == false,
                    "RED: native PNR leaf #" .. tostring(i) .. " (" .. tostring(leaf._name)
                    .. ") must have visible=false while Alerts owns PNR")
            end

            local alerts_nv = 0
            local total_nv = 0
            local nv_objects = {}
            for _, e in ipairs(nv._entries or {}) do
                total_nv = total_nv + 1
                if e.owner == "alerts" then
                    alerts_nv = alerts_nv + 1
                    assert(e.property == "visible" and e.applied_value == false,
                        "RED: alerts NV entry must set visible=false")
                    nv_objects[e.object] = true
                end
            end
            assert(alerts_nv == 8 and total_nv == 8,
                "RED: expected exactly 8 NV entries owned by 'alerts', got alerts="
                .. tostring(alerts_nv) .. " total=" .. tostring(total_nv))
            for _, leaf in ipairs(pnr_leaves) do
                assert(nv_objects[leaf] == true,
                    "RED: leaf " .. tostring(leaf._name) .. " must be tracked by NV owner 'alerts'")
            end

            -- Native parents and third-party panels must remain untouched
            assert(_na.hud_panel:visible() == true, "hud_panel parent must remain visible")
            assert(_na.pnr_panel:visible() == true and math.abs(_na.pnr_panel:alpha() - 0.91) < 0.001,
                "pnr_panel parent must remain visible with original alpha 0.91")
            assert(_na.noreturn_bg_box:visible() == true and math.abs(_na.noreturn_bg_box:alpha() - 0.87) < 0.001,
                "noreturn_bg_box parent must remain visible with original alpha 0.87")
            assert(_na.pnr_third_party:visible() == true and math.abs(_na.pnr_third_party:alpha() - 0.59) < 0.001,
                "pnr_third_party child must remain untouched")
            assert(_na.third_party:visible() == true and _na.third_party:alpha() == 1,
                "assault third_party panel must remain untouched")

            local saved_root = AL._root_panel
            local saved_timer = pnr_timer
            local saved_status = pnr_status
            local saved_title = pnr_title
            local panel_id_after_first = _panel_id

            -- Transition 1: feed(65.1, true) + tick => INSIDE label
            state._point_of_no_return_timer = 65.1
            state._is_inside_point_of_no_return = true
            managers.hud:feed_point_of_no_return_timer(65.1, true)
            RT:update(managers.hud, 1.05, 0.05)

            assert(pnr_timer:text() == "01:05",
                "RED: pnr_timer text for 65.1s must be '01:05', got " .. tostring(pnr_timer:text()))
            local inside_text = pnr_status:text()
            assert(type(inside_text) == "string" and #inside_text > 0 and not inside_text:find("^LOC:"),
                "RED: pnr_status text must be nonempty when is_inside=true")
            assert(inside_text ~= outside_text,
                "RED: INSIDE status must be distinct from OUTSIDE status")
            assert(inside_text:upper():find("INSIDE") ~= nil,
                "RED: pnr_status when is_inside=true must contain INSIDE, got " .. tostring(inside_text))
            assert(AL:_verify_render() == true,
                "RED: AL:_verify_render() must remain true after feed(65.1, true)")

            -- Transition 2: feed(0, true) + tick => 00:00, same identities, no extra creations
            state._point_of_no_return_timer = 0
            state._is_inside_point_of_no_return = true
            managers.hud:feed_point_of_no_return_timer(0, true)
            RT:update(managers.hud, 1.10, 0.05)

            assert(pnr_timer:text() == "00:00",
                "RED: pnr_timer text for 0s must be '00:00', got " .. tostring(pnr_timer:text()))
            assert(pnr_status:text():upper():find("INSIDE") ~= nil,
                "RED: pnr_status must remain INSIDE at 0s")
            assert(rawequal(AL._root_panel, saved_root),
                "RED: AL._root_panel identity must be preserved across ticks")
            assert(rawequal(AL._root_panel:child("pnr_timer"), saved_timer),
                "RED: pnr_timer primitive identity must be preserved")
            assert(rawequal(AL._root_panel:child("pnr_status"), saved_status),
                "RED: pnr_status primitive identity must be preserved")
            assert(rawequal(AL._root_panel:child("pnr_title"), saved_title),
                "RED: pnr_title primitive identity must be preserved")
            assert(_panel_id == panel_id_after_first,
                "RED: no extra Diesel primitives may be created on subsequent ticks, before="
                .. tostring(panel_id_after_first) .. " after=" .. tostring(_panel_id))
            assert(AL:_verify_render() == true,
                "RED: AL:_verify_render() must remain true at 00:00")

            -- Transition 3: disable enable_alerts=false + RT:refresh_settings => immediate restore
            kyohud.settings.enable_alerts = false
            RT:refresh_settings(managers.hud)

            assert(AL._root_panel == nil or AL._root_panel:visible() == false,
                "RED: disabling enable_alerts must immediately hide or remove AL._root_panel")

            local remaining_nv = 0
            for _ in ipairs(nv._entries or {}) do
                remaining_nv = remaining_nv + 1
            end
            assert(remaining_nv == 0,
                "RED: disabling enable_alerts must immediately clear all NV records, got "
                .. tostring(remaining_nv))

            -- Exact prior leaf visibilities (7 true, 1 false) and nonstandard alphas restored
            assert(_na.icon_noreturnbox:visible() == true and math.abs(_na.icon_noreturnbox:alpha() - 0.63) < 0.001,
                "RED: icon_noreturnbox must restore visible=true and alpha=0.63")
            assert(_na.pnr_text:visible() == true and math.abs(_na.pnr_text:alpha() - 0.77) < 0.001,
                "RED: point_of_no_return_text must restore visible=true and alpha=0.77")
            assert(_na.pnr_timer:visible() == true and math.abs(_na.pnr_timer:alpha() - 0.81) < 0.001,
                "RED: point_of_no_return_timer must restore visible=true and alpha=0.81")
            assert(_na.pnr_bg:visible() == true and math.abs(_na.pnr_bg:alpha() - 0.41) < 0.001,
                "RED: pnr_bg must restore visible=true and alpha=0.41")
            assert(_na.pnr_lt:visible() == true and math.abs(_na.pnr_lt:alpha() - 0.42) < 0.001,
                "RED: pnr_lt must restore visible=true and alpha=0.42")
            assert(_na.pnr_lb:visible() == true and math.abs(_na.pnr_lb:alpha() - 0.43) < 0.001,
                "RED: pnr_lb must restore visible=true and alpha=0.43")
            assert(_na.pnr_rt:visible() == true and math.abs(_na.pnr_rt:alpha() - 0.44) < 0.001,
                "RED: pnr_rt must restore visible=true and alpha=0.44")
            assert(_na.pnr_rb:visible() == false and math.abs(_na.pnr_rb:alpha() - 0.45) < 0.001,
                "RED: pnr_rb must restore exact prior visible=false and alpha=0.45")

            -- Native parents and combat sentinel preserved
            assert(_na.hud_panel:visible() == true, "hud_panel parent must remain visible")
            assert(_na.pnr_panel:visible() == true and math.abs(_na.pnr_panel:alpha() - 0.91) < 0.001,
                "pnr_panel parent must remain visible with alpha 0.91")
            assert(_na.noreturn_bg_box:visible() == true and math.abs(_na.noreturn_bg_box:alpha() - 0.87) < 0.001,
                "noreturn_bg_box parent must remain visible with alpha 0.87")
            assert(_na.pnr_third_party:visible() == true and math.abs(_na.pnr_third_party:alpha() - 0.59) < 0.001,
                "pnr_third_party must remain untouched")
            assert(kyohud.killstreak == _sentinel_before,
                "Combat sentinel must be preserved, got "
                .. tostring(kyohud.killstreak) .. " expected " .. tostring(_sentinel_before))
        ''')

    def test_unsupported_pnr_keeps_native_and_hides_owned_after_positive_state(self):
        lua, ok = _lua_with_assault_and_alerts_slice()
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")

        lua.execute('''
            kyohud.settings.enable_alerts = true

            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local state = managers.groupai:state()

            RT:mount(managers.hud)

            -- Step 1: Establish positive standard PNR replacement state first
            state._point_of_no_return_timer = 65.9
            state._point_of_no_return_id = 101
            state._point_of_no_return_tweak_id = "noreturn"
            state._is_inside_point_of_no_return = false
            managers.hud:show_point_of_no_return_timer("noreturn")
            managers.hud:feed_point_of_no_return_timer(65.9, false)
            RT:update(managers.hud, 1.0, 0.05)

            assert(type(AL._root_panel) == "table" and AL._root_panel:visible() == true,
                "RED: positive prerequisite must have visible AL._root_panel")
            assert(AL:_verify_render() == true,
                "RED: positive prerequisite must verify render")

            local pos_alerts_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then
                    pos_alerts_nv = pos_alerts_nv + 1
                end
            end
            assert(pos_alerts_nv == 8,
                "RED: positive prerequisite must acquire 8 NV records for 'alerts', got "
                .. tostring(pos_alerts_nv))

            -- Step 2: Transition to unsupported PNR state (unsupported tweak_id and inside=nil)
            state._point_of_no_return_timer = 45.0
            state._point_of_no_return_id = 102
            state._point_of_no_return_tweak_id = "custom_unsupported_variant"
            state._is_inside_point_of_no_return = nil
            managers.hud:show_point_of_no_return_timer("custom_unsupported_variant")
            managers.hud:feed_point_of_no_return_timer(45.0, nil)
            RT:update(managers.hud, 1.05, 0.05)

            assert(AL._root_panel == nil or AL._root_panel:visible() == false,
                "RED: unsupported PNR must not leave owned AL._root_panel visible")

            local unsupported_nv = 0
            for _ in ipairs(nv._entries or {}) do
                unsupported_nv = unsupported_nv + 1
            end
            assert(unsupported_nv == 0,
                "RED: unsupported PNR must have 0 NV records, got " .. tostring(unsupported_nv))

            -- Native PNR panel and leaves kept/restored to their exact prior values
            assert(_na.pnr_panel:visible() == true,
                "Native pnr_panel must remain visible during unsupported PNR")
            assert(_na.noreturn_bg_box:visible() == true,
                "Native noreturn_bg_box must remain visible during unsupported PNR")
            assert(_na.icon_noreturnbox:visible() == true and math.abs(_na.icon_noreturnbox:alpha() - 0.63) < 0.001,
                "Native icon_noreturnbox must be visible with alpha 0.63")
            assert(_na.pnr_text:visible() == true and math.abs(_na.pnr_text:alpha() - 0.77) < 0.001,
                "Native point_of_no_return_text must be visible with alpha 0.77")
            assert(_na.pnr_timer:visible() == true and math.abs(_na.pnr_timer:alpha() - 0.81) < 0.001,
                "Native point_of_no_return_timer must be visible with alpha 0.81")
            assert(_na.pnr_bg:visible() == true and _na.pnr_lt:visible() == true
                and _na.pnr_lb:visible() == true and _na.pnr_rt:visible() == true,
                "Native PNR bg and 3 visible corners must be visible=true")
            assert(_na.pnr_rb:visible() == false,
                "Native PNR right_bottom must preserve exact prior visible=false")
            assert(kyohud.killstreak == _sentinel_before,
                "Combat sentinel must be preserved")
        ''')


class AlertsOpeningCallbackBoundaryTests(unittest.TestCase):
    """Opening callback boundary: coroutine fixture reproduces native behavior.

    Native PAYDAY 2 (hudobjectives.lua:143-184) calls HUDBGBox_animate_open_left
    which yields once then calls done_cb. done_cb starts _animate_show_texts which
    sets text/timer visible=true BEFORE its first yield, then only alpha changes.

    This test manually creates and resumes coroutines to verify boundary behavior.
    """

    def test_opening_callback_boundary_releases_and_reacquires_without_update_tick(self):
        lua, ok = _lua_with_assault_and_alerts_slice()
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")

        lua.execute('''
            kyohud.settings.enable_alerts = true

            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local state = managers.groupai:state()

            RT:mount(managers.hud)

            state._point_of_no_return_timer = 65.9
            state._point_of_no_return_id = 101
            state._point_of_no_return_tweak_id = "noreturn"
            state._is_inside_point_of_no_return = false
            managers.hud:show_point_of_no_return_timer("noreturn")
            managers.hud:feed_point_of_no_return_timer(65.9, false)
            RT:update(managers.hud, 1.0, 0.05)

            assert(type(AL._root_panel) == "table" and AL._root_panel:visible() == true,
                "RED: positive prerequisite must have visible AL._root_panel")
            assert(AL:_verify_render() == true,
                "RED: positive prerequisite must verify render")

            local pos_alerts_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then
                    pos_alerts_nv = pos_alerts_nv + 1
                end
            end
            assert(pos_alerts_nv == 8,
                "RED: positive prerequisite must acquire 8 NV records for 'alerts', got "
                .. tostring(pos_alerts_nv))

            local corner = managers.hud._hud_assault_corner
            local noreturn_bg_box = corner._noreturn_bg_box
            local pnr_text = noreturn_bg_box:child("point_of_no_return_text")
            local pnr_timer = noreturn_bg_box:child("point_of_no_return_timer")

            local text_co = nil
            local callback_text_visible = nil
            local callback_timer_visible = nil

            local done_cb = function()
                text_co = coroutine.create(function()
                    corner:_animate_show_texts(noreturn_bg_box, {pnr_text, pnr_timer})
                end)
                local ok_resume, err = coroutine.resume(text_co)
                assert(ok_resume, "text coroutine first resume failed: " .. tostring(err))

                callback_text_visible = pnr_text:visible()
                callback_timer_visible = pnr_timer:visible()
            end

            local open_co = coroutine.create(function()
                HUDBGBox_animate_open_left(noreturn_bg_box, 0, 242, done_cb, {})
            end)

            local ok1, status1 = coroutine.resume(open_co)
            assert(ok1, "open coroutine first resume failed: " .. tostring(status1))
            assert(coroutine.status(open_co) == "suspended",
                "After first resume: open coroutine must be suspended, got "
                .. tostring(coroutine.status(open_co)))

            local nv_during_suspend = 0
            for _ in ipairs(nv._entries or {}) do
                nv_during_suspend = nv_during_suspend + 1
            end
            assert(nv_during_suspend == 0,
                "After first resume: NV must be 0 before callback writes, got "
                .. tostring(nv_during_suspend))
            assert(AL._root_panel:visible() == false,
                "After first resume: owned root must be hidden before callback writes")

            local ok2, status2 = coroutine.resume(open_co)
            assert(ok2, "open coroutine second resume failed: " .. tostring(status2))
            assert(coroutine.status(open_co) == "dead",
                "After second resume: open coroutine must be dead, got "
                .. tostring(coroutine.status(open_co)))

            assert(callback_text_visible == true,
                "Callback observation: text must have been visible=true inside done_cb, got "
                .. tostring(callback_text_visible))
            assert(callback_timer_visible == true,
                "Callback observation: timer must have been visible=true inside done_cb, got "
                .. tostring(callback_timer_visible))

            local nv_after_sync = 0
            for _ in ipairs(nv._entries or {}) do
                nv_after_sync = nv_after_sync + 1
            end
            assert(nv_after_sync == 8,
                "After second resume: NV must be 8 after sync, got "
                .. tostring(nv_after_sync))
            assert(AL._root_panel:visible() == true,
                "After second resume: owned root must be visible after sync")
            assert(coroutine.status(text_co) == "suspended",
                "After second resume: text coroutine must still be suspended, got "
                .. tostring(coroutine.status(text_co)))

            assert(pnr_text:visible() == false,
                "RED: actual text must be visible=false after NV acquire, got "
                .. tostring(pnr_text:visible()))
            assert(pnr_timer:visible() == false,
                "RED: actual timer must be visible=false after NV acquire, got "
                .. tostring(pnr_timer:visible()))

            local assault_bg_box = corner._bg_box
            assert(assault_bg_box and type(assault_bg_box.set_visible) == "function",
                "RED: assault_bg_box must exist and support set_visible")

            local assault_bg_box_vis_before = assault_bg_box:visible()
            local nv_before_unrelated = 0
            for _ in ipairs(nv._entries or {}) do
                nv_before_unrelated = nv_before_unrelated + 1
            end
            local root_vis_before_unrelated = AL._root_panel:visible()

            local unrelated_done_cb = function() end
            local unrelated_co = coroutine.create(function()
                HUDBGBox_animate_open_left(assault_bg_box, 0, 200, unrelated_done_cb, {})
            end)
            local ok_unrel1, err_unrel1 = coroutine.resume(unrelated_co)
            assert(ok_unrel1, "unrelated coroutine first resume failed: " .. tostring(err_unrel1))

            local nv_after_unrel1 = 0
            for _ in ipairs(nv._entries or {}) do
                nv_after_unrel1 = nv_after_unrel1 + 1
            end
            assert(nv_after_unrel1 == 8,
                "After unrelated first resume: NV must remain 8, got "
                .. tostring(nv_after_unrel1))
            assert(AL._root_panel:visible() == true,
                "After unrelated first resume: owned root must remain visible")

            local ok_unrel2, err_unrel2 = coroutine.resume(unrelated_co)
            assert(ok_unrel2, "unrelated coroutine second resume failed: " .. tostring(err_unrel2))

            local nv_after_unrel2 = 0
            for _ in ipairs(nv._entries or {}) do
                nv_after_unrel2 = nv_after_unrel2 + 1
            end
            assert(nv_after_unrel2 == 8,
                "After unrelated second resume: NV must remain 8, got "
                .. tostring(nv_after_unrel2))
            assert(AL._root_panel:visible() == true,
                "After unrelated second resume: owned root must remain visible")

            kyohud.settings.enable_alerts = false
            RT:refresh_settings(managers.hud)

            assert(pnr_text:visible() == true,
                "After disable: text must be restored to visible=true, got "
                .. tostring(pnr_text:visible()))
            assert(pnr_timer:visible() == true,
                "After disable: timer must be restored to visible=true, got "
                .. tostring(pnr_timer:visible()))

            assert(_na.icon_noreturnbox:visible() == true and math.abs(_na.icon_noreturnbox:alpha() - 0.63) < 0.001,
                "RED: icon_noreturnbox must restore visible=true and alpha=0.63")
            assert(_na.pnr_bg:visible() == true and math.abs(_na.pnr_bg:alpha() - 0.41) < 0.001,
                "RED: pnr_bg must restore visible=true and alpha=0.41")
            assert(_na.pnr_lt:visible() == true and math.abs(_na.pnr_lt:alpha() - 0.42) < 0.001,
                "RED: pnr_lt must restore visible=true and alpha=0.42")
            assert(_na.pnr_lb:visible() == true and math.abs(_na.pnr_lb:alpha() - 0.43) < 0.001,
                "RED: pnr_lb must restore visible=true and alpha=0.43")
            assert(_na.pnr_rt:visible() == true and math.abs(_na.pnr_rt:alpha() - 0.44) < 0.001,
                "RED: pnr_rt must restore visible=true and alpha=0.44")
            assert(_na.pnr_rb:visible() == false and math.abs(_na.pnr_rb:alpha() - 0.45) < 0.001,
                "RED: pnr_rb must restore exact prior visible=false and alpha=0.45")

            assert(_na.hud_panel:visible() == true, "hud_panel parent must remain visible")
            assert(_na.pnr_panel:visible() == true and math.abs(_na.pnr_panel:alpha() - 0.91) < 0.001,
                "pnr_panel parent must remain visible with alpha 0.91")
            assert(_na.noreturn_bg_box:visible() == true and math.abs(_na.noreturn_bg_box:alpha() - 0.87) < 0.001,
                "noreturn_bg_box parent must remain visible with alpha 0.87")
            assert(_na.pnr_third_party:visible() == true and math.abs(_na.pnr_third_party:alpha() - 0.59) < 0.001,
                "pnr_third_party must remain untouched")

            assert(kyohud.killstreak == _sentinel_before,
                "Combat sentinel must be preserved")
        ''')
