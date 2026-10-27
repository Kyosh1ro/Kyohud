"""LOT3b -- hud/alerts.lua: recovery slices (RED state for bounded recovery).

Slice 1: Late enable with default nil tweak via native GroupAI snapshot.
  - Alerts off, source timer=12.9, id=901, tweak_id=nil, inside=false
  - Native HUDManager show(nil), no feed needed
  - enable_alerts true then RT:refresh_settings/update => visible verified owned
    root timer=00:12, outside, NV=8
  - Nil means real native default (noreturn), never unknown/custom
  - Assert positive never writes production fields

Slice 2: Standard PNR with real coroutine and native abort.
  - Start valid standard PNR with source fields/show/feed/runtime
  - Open real global coroutine with exact bg FIRST RESUME only => NV=0/ownroot hidden
  - A regular RT:update during suspension must keep NV=0/hidden (not repair)
  - Then mgr:hide_point_of_no_return_timer (native abort old animation; never
    resume old coroutine)
  - Source new id=902, timer=45, tweak_id=noreturn, inside=true
  - Native show/feed and RT:update => new visible certified root/NV=8 timer=00:45,
    not stuck on old opening flag
"""
from pathlib import Path
import unittest

from test_hud_alerts import _lua_with_assault_and_alerts_slice


class AlertsLateEnableNilTweakTests(unittest.TestCase):
    """Late enable with default nil tweak via native GroupAI snapshot."""

    def test_late_enable_with_nil_tweak_shows_valid_noreturn(self):
        lua, ok = _lua_with_assault_and_alerts_slice()
        self.assertTrue(ok, "assault.lua fixture prerequisite must exist")

        lua.execute('''
            kyohud.settings.enable_alerts = false

            local RT = kyohud.hud.runtime
            local AL = kyohud.hud.alerts
            local nv = kyohud.hud.native_visibility
            local state = managers.groupai:state()

            RT:mount(managers.hud)
            RT:update(managers.hud, 1.0, 0.05)

            state._point_of_no_return_timer = 12.9
            state._point_of_no_return_id = 901
            state._point_of_no_return_tweak_id = nil
            state._is_inside_point_of_no_return = false
            managers.hud:show_point_of_no_return_timer(nil)

            kyohud.settings.enable_alerts = true
            RT:refresh_settings(managers.hud)
            RT:update(managers.hud, 1.05, 0.05)

            assert(type(AL._root_panel) == "table" and AL._root_panel:visible() == true,
                "RED: late enable with nil tweak must show visible AL._root_panel")
            assert(AL:_verify_render() == true,
                "RED: late enable with nil tweak must verify render")

            local pnr_timer = AL._root_panel:child("pnr_timer")
            local pnr_status = AL._root_panel:child("pnr_status")
            assert(type(pnr_timer) == "table" and pnr_timer:visible() == true,
                "RED: pnr_timer must exist and be visible")
            assert(pnr_timer:text() == "00:12",
                "RED: pnr_timer text for 12.9s must be '00:12', got " .. tostring(pnr_timer:text()))

            local status_text = pnr_status:text()
            assert(type(status_text) == "string" and #status_text > 0,
                "RED: pnr_status must be nonempty")
            assert(not status_text:find("^LOC:"),
                "RED: pnr_status must not be raw LOC fallback, got " .. tostring(status_text))
            assert(status_text:upper():find("OUTSIDE") ~= nil,
                "RED: pnr_status when is_inside=false must contain OUTSIDE, got " .. tostring(status_text))

            local alerts_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then
                    alerts_nv = alerts_nv + 1
                end
            end
            assert(alerts_nv == 8,
                "RED: expected exactly 8 NV entries owned by 'alerts', got " .. tostring(alerts_nv))

            local title_text = AL._root_panel:child("pnr_title"):text()
            assert(type(title_text) == "string" and #title_text > 0 and not title_text:find("^LOC:"),
                "RED: pnr_title must be nonempty and not raw LOC fallback")
            assert(not title_text:upper():find("CUSTOM") and not title_text:upper():find("UNKNOWN"),
                "RED: nil tweak must resolve to real native default (noreturn), never unknown/custom, got "
                .. tostring(title_text))

            assert(kyohud.killstreak == _sentinel_before,
                "RED: positive never writes production fields, sentinel got "
                .. tostring(kyohud.killstreak) .. " expected " .. tostring(_sentinel_before))
        ''')


class AlertsCoroutineAbortAndRecoveryTests(unittest.TestCase):
    """Standard PNR with real coroutine and native abort."""

    def test_coroutine_abort_and_recovery_to_new_valid_pnr(self):
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
                "RED: initial PNR must show visible AL._root_panel")
            assert(AL:_verify_render() == true,
                "RED: initial PNR must verify render")

            local corner = managers.hud._hud_assault_corner
            local noreturn_bg_box = corner._noreturn_bg_box
            local pnr_text = noreturn_bg_box:child("point_of_no_return_text")
            local pnr_timer_native = noreturn_bg_box:child("point_of_no_return_timer")

            local done_cb = function()
                local text_co = coroutine.create(function()
                    corner:_animate_show_texts(noreturn_bg_box, {pnr_text, pnr_timer_native})
                end)
                local ok_resume, err = coroutine.resume(text_co)
                assert(ok_resume, "text coroutine first resume failed: " .. tostring(err))
            end

            local open_co = coroutine.create(function()
                HUDBGBox_animate_open_left(noreturn_bg_box, 0, 242, done_cb, {})
            end)

            local ok1, err1 = coroutine.resume(open_co)
            assert(ok1, "open coroutine first resume failed: " .. tostring(err1))
            assert(coroutine.status(open_co) == "suspended",
                "After first resume: open coroutine must be suspended")

            local nv_during_suspend = 0
            for _ in ipairs(nv._entries or {}) do
                nv_during_suspend = nv_during_suspend + 1
            end
            assert(nv_during_suspend == 0,
                "After first resume: NV must be 0 before callback writes, got "
                .. tostring(nv_during_suspend))
            assert(AL._root_panel:visible() == false,
                "After first resume: owned root must be hidden before callback writes")

            RT:update(managers.hud, 1.05, 0.05)

            local nv_during_update = 0
            for _ in ipairs(nv._entries or {}) do
                nv_during_update = nv_during_update + 1
            end
            assert(nv_during_update == 0,
                "During suspension: RT:update must keep NV=0, not repair, got "
                .. tostring(nv_during_update))
            assert(AL._root_panel:visible() == false,
                "During suspension: RT:update must keep owned root hidden, not repair")

            managers.hud:hide_point_of_no_return_timer()

            state._point_of_no_return_timer = 45.0
            state._point_of_no_return_id = 902
            state._point_of_no_return_tweak_id = "noreturn"
            state._is_inside_point_of_no_return = true
            managers.hud:show_point_of_no_return_timer("noreturn")
            managers.hud:feed_point_of_no_return_timer(45.0, true)

            RT:update(managers.hud, 1.10, 0.05)

            assert(type(AL._root_panel) == "table" and AL._root_panel:visible() == true,
                "RED: new PNR after abort must show visible certified root")
            assert(AL:_verify_render() == true,
                "RED: new PNR after abort must verify render")

            local new_pnr_timer = AL._root_panel:child("pnr_timer")
            local new_pnr_status = AL._root_panel:child("pnr_status")
            assert(type(new_pnr_timer) == "table" and new_pnr_timer:visible() == true,
                "RED: new pnr_timer must exist and be visible")
            assert(new_pnr_timer:text() == "00:45",
                "RED: new pnr_timer text for 45s must be '00:45', got " .. tostring(new_pnr_timer:text()))

            local new_status_text = new_pnr_status:text()
            assert(type(new_status_text) == "string" and #new_status_text > 0,
                "RED: new pnr_status must be nonempty")
            assert(new_status_text:upper():find("INSIDE") ~= nil,
                "RED: new pnr_status when is_inside=true must contain INSIDE, got "
                .. tostring(new_status_text))

            local new_alerts_nv = 0
            for _, e in ipairs(nv._entries or {}) do
                if e.owner == "alerts" then
                    new_alerts_nv = new_alerts_nv + 1
                end
            end
            assert(new_alerts_nv == 8,
                "RED: new PNR must have 8 NV entries owned by 'alerts', got "
                .. tostring(new_alerts_nv))

            assert(coroutine.status(open_co) == "suspended",
                "After abort: old coroutine must remain suspended, never resumed, got "
                .. tostring(coroutine.status(open_co)))

            assert(kyohud.killstreak == _sentinel_before,
                "RED: sentinel preserved through abort and recovery")
        ''')
