"""LOT3a -- hud/assault.lua: first preparation without native text_panel (RED).

Scope: native ticker text_panel absence during first host anticipation.
Native hudassaultcorner.lua:790-797 creates bg:child("text_panel") only
inside _start_assault(), not during anticipation. The first Preparation
therefore has no text_panel target. Current prod _resolve_native_targets
(assault.lua:2824-2827) returns nil when text_panel is absent, causing
native_acquire_failed fallback on the very first anticipation.

Approved safe solution (NOT yet implemented in production):
  Nonactive preparation: corner._assault false/nil AND assault_mode false
  AND bg:child("text_panel") returns nil => qualify as first preparation,
  acquire only same 13 verified existing leaves (5 bg_leaves + 5 hostage
  bg_leaves + assault_icon + hostage_icon + num_hostages), all visible=false,
  NO alpha request for absent text_panel.
  Active assault: corner._assault true OR assault_mode true AND text_panel
  absent => refuse acquisition (fail closed).
  Nil getter exception != genuine absence: pcall error on child lookup
  must also fail closed.
  Native creation reconciliation: when text_panel later appears (build
  phase), target set changes to 14 requests (13 visible + 1 alpha=0);
  _try_acquire_native must detect set change even if corner identity is
  unchanged, not return early just because corner is same.

No native creation or parent masking or whitelist expansion.
No production writes. No fabricated production state in fixture.
Preserve all existing tests. Baseline SOL 1360.
"""
import unittest
from pathlib import Path
from lupa.luajit21 import LuaRuntime

from test_hud_assault import (
    STUBS,
    NATIVE_ASSAULT_CORNER_FIXTURE,
    HUDMANAGER_ASSAULT_FIXTURE,
    GROUPAI_STATE_FIXTURE,
)
from test_hud_assault_render import (
    DIESEL,
    HUD_RELAY_FIXTURE,
    ASSAULT_PATH,
    LAYOUT_PATH,
    RUNTIME_PATH,
    NATIVE_VIS_PATH,
    attach_native,
)

ROOT = Path(__file__).resolve().parents[1]


def _read(p):
    return p.read_text(encoding="utf-8-sig") if p.is_file() else None


LOCALIZATION_MULTI_STATE_FIXTURE = r'''
managers.localization = managers.localization or {}
local _loc_map = {
    ky_hud_assault_status = "ASSAULT",
    ky_hud_assault_endless = "ENDLESS",
    ky_hud_assault_preparation = "PREPARATION",
    ky_hud_assault_build = "MONTEE",
    ky_hud_assault_sustain = "MAINTIEN",
    ky_hud_assault_fade = "RETRAIT",
    ky_hud_assault_after = "AFTER ASSAULT",
    ky_hud_hostages_label = "HOSTAGES",
    ky_hud_converted_label = "CONVERTED",
}
function managers.localization:text(key)
    return _loc_map[key] or ("LOC:" .. tostring(key))
end
function managers.localization:get_default_macro(key)
    if key == "BTN_SKULL" then return "S" end
    return "?"
end
'''

NETWORK_FIXTURE = r'''
Network = Network or {}
function Network:is_server()
    return self._is_server == true
end
'''

HUDMANAGER_SYNC_SIGNALS_FIXTURE = r'''
_kyohud_anticipation_count = 0
function HUDManager:sync_start_anticipation_music()
    _kyohud_anticipation_count = _kyohud_anticipation_count + 1
end
'''


def _make_base_lua():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.globals().ModPath = ROOT.as_posix() + "/"
    lua.execute(STUBS)
    lua.execute(
        '_G.Color=function(a1,a2,a3,a4)'
        ' if a4==nil then return{r=a1,g=a2,b=a3,a=1}'
        ' else return{a=a1,r=a2,g=a3,b=a4} end end'
    )
    lua.execute(
        'tweak_data.hud = tweak_data.hud or {};'
        ' tweak_data.hud.medium_font_noshadow = "fonts/font_medium_mf"'
    )
    lua.execute(NATIVE_ASSAULT_CORNER_FIXTURE)
    lua.execute(HUDMANAGER_ASSAULT_FIXTURE)
    lua.execute(GROUPAI_STATE_FIXTURE)
    lua.execute(NETWORK_FIXTURE)
    lua.execute(HUDMANAGER_SYNC_SIGNALS_FIXTURE)
    lua.execute('''
        function GroupAIState:hostage_count() return self._hostage_count end
        function GroupAIState:all_converted_enemies() return self._converted end
    ''')
    lua.execute(DIESEL)
    lua.execute(HUD_RELAY_FIXTURE)
    lua.execute(LOCALIZATION_MULTI_STATE_FIXTURE)
    lua.execute(
        "_init_fp = _make_panel_extended('safe_hud_parent');"
        " _init_fp._w=1920; _init_fp._h=1080"
    )
    lua.execute(
        "_init_mgr_safe = {panel = _init_fp};"
        " _G.managers.hud = setmetatable({"
        " script = function(self, name) return _init_mgr_safe end,"
        " disabled = function() return false end"
        " }, {__index = HUDManager})"
    )
    lua.execute('RequiredScript = "lib/managers/hudmanagerpd2"')

    layout_src = _read(LAYOUT_PATH)
    native_vis_src = _read(NATIVE_VIS_PATH)
    runtime_src = _read(RUNTIME_PATH)
    assault_src = _read(ASSAULT_PATH)
    if not all([layout_src, native_vis_src, runtime_src, assault_src]):
        return lua, False

    lua.execute(layout_src)
    lua.execute(native_vis_src)
    lua.execute(runtime_src)
    lua.execute(assault_src)

    attach_native(lua)
    return lua, True


def _remove_native_text_panel(lua):
    lua.execute(r'''
        local corner = managers.hud._hud_assault_corner
        local bg = corner._bg_box
        local tp = bg._children["text_panel"]
        if tp then
            tp._alive = false
        end
        bg._children["text_panel"] = nil
        _removed_tp = tp
        _verify_gone = bg:child("text_panel")
    ''')


def _set_host_anticipation(lua):
    lua.execute(r'''
        kyohud.settings.enable_hud_foundation = true
        kyohud.settings.enable_assault = true
        local state = managers.groupai:state()
        state._assault_mode = false
        state._hunt_mode = false
        state._is_server = true
        state._task_data = state._task_data or {}
        state._task_data.assault = state._task_data.assault or {}
        state._task_data.assault.active = true
        state._task_data.assault.phase = "anticipation"
        state._hostage_count = 0
        state._converted = {}
        Network._is_server = true
        local corner = managers.hud._hud_assault_corner
        corner._assault = false
        corner._point_of_no_return = false
        corner._casing = false
    ''')


def _set_host_build_active(lua):
    lua.execute(r'''
        local state = managers.groupai:state()
        state._assault_mode = true
        state._task_data.assault.active = true
        state._task_data.assault.phase = "build"
        local corner = managers.hud._hud_assault_corner
        corner._assault = true
        managers.hud:sync_start_assault(1)
    ''')


def _create_native_text_panel(lua):
    lua.execute(r'''
        local corner = managers.hud._hud_assault_corner
        local bg = corner._bg_box
        local new_tp = bg:panel({name = "text_panel", x = 0, y = 0, w = 200, h = 38})
        new_tp._alpha = 0.37
        _new_tp = new_tp
    ''')


class FirstPreparationNoTextPanelTests(unittest.TestCase):
    """RED: first host anticipation without native text_panel.

    Native creates text_panel only in _start_assault() (hudac:790-797),
    not during anticipation. First preparation has no text_panel.
    Current prod _resolve_native_targets returns nil -> native_acquire_failed.

    Desired: qualify nonactive preparation (corner._assault false,
    assault_mode false) + text_panel absent => 13 visible requests only,
    no alpha entry, owned certified preparation visible.
    """

    def test_first_prep_nonactive_no_text_panel_13_requests(self):
        lua, ok = _make_base_lua()
        self.assertTrue(ok, "mandatory chunks missing")

        _remove_native_text_panel(lua)
        g = lua.globals()
        self.assertIsNone(g._verify_gone,
            "text_panel must be removed from bg_box children")

        _set_host_anticipation(lua)

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local A = kyohud.hud.assault
            A:mount(managers.hud)
            A:update(managers.hud, 1.0, 0.05)

            _root_vis = A._root_panel:visible()
            _presenting = A._state.presenting
            _label = A:_resolve_status_label()
            _verify = A:_verify_render()
            _acquired = A._native_acquired
            _req_count = A._native_requests and #A._native_requests or -1
            _has_alpha_req = false
            if A._native_requests then
                for _, req in ipairs(A._native_requests) do
                    if req.property == "alpha" then
                        _has_alpha_req = true
                    end
                end
            end
            _root_id = tostring(A._root_panel)

            local corner = managers.hud._hud_assault_corner
            local bg = corner._bg_box
            local hp = corner._hud_panel
            local ap = hp:child("assault_panel")
            local hostages_p = hp:child("hostages_panel")
            local hb = corner._hostages_bg_box
            _allowlist_ids = {}
            local expected_objs = {
                ap:child("icon_assaultbox"),
                hostages_p:child("hostages_icon"),
                hb:child("num_hostages"),
            }
            local bg_names = {"bg","left_top","left_bottom","right_top","right_bottom"}
            for _, n in ipairs(bg_names) do
                table.insert(expected_objs, bg:child(n))
            end
            local hb_names = {"bg","left_top","left_bottom","right_top","right_bottom"}
            for _, n in ipairs(hb_names) do
                table.insert(expected_objs, hb:child(n))
            end
            for _, obj in ipairs(expected_objs) do
                _allowlist_ids[tostring(obj)] = true
            end
            _all_vis_false = true
            _all_req_in_allowlist = true
            _actual_vis_count = 0
            if A._native_requests then
                for _, req in ipairs(A._native_requests) do
                    local tid = tostring(req.id)
                    if not _allowlist_ids[tid] then
                        _all_req_in_allowlist = false
                    end
                    if req.property == "visible" then
                        local ok_v, v = pcall(function() return req.id:visible() end)
                        if ok_v and v ~= false then
                            _all_vis_false = false
                        end
                        if ok_v and v == false then
                            _actual_vis_count = _actual_vis_count + 1
                        end
                    end
                end
            end
        ''')

        g = lua.globals()
        self.assertEqual(str(g._label), "PREPARATION",
            "label must be PREPARATION during host anticipation")
        self.assertTrue(bool(g._presenting),
            "presenting must be true during anticipation")
        self.assertTrue(bool(g._verify),
            "RED: _verify_render must be true for owned preparation")
        self.assertTrue(bool(g._root_vis),
            "RED: root must be visible for owned preparation")
        self.assertTrue(bool(g._acquired),
            "RED: nonactive prep without text_panel must acquire"
            " 13 leaf requests, got native_acquired=false")
        self.assertEqual(int(g._req_count), 13,
            "RED: must have exactly 13 visible=false requests"
            " (5 bg + 5 hostage_bg + icon_assault + icon_hostage + num),"
            " got " + str(g._req_count))
        self.assertFalse(bool(g._has_alpha_req),
            "RED: absent text_panel must not generate alpha request")
        self.assertTrue(bool(g._all_vis_false),
            "RED: all 13 visible requests must be actually applied (visible=false)")
        self.assertEqual(int(g._actual_vis_count), 13,
            "RED: exactly 13 leaves must read visible=false, got "
            + str(g._actual_vis_count))
        self.assertTrue(bool(g._all_req_in_allowlist),
            "RED: every request target must be in the 13-leaf allowlist,"
            " no unrelated target")

    def test_active_assault_missing_text_panel_refused(self):
        """RED: active assault with missing text_panel must fail closed.

        During active assault (corner._assault=true, assault_mode=true),
        text_panel absence is abnormal. _resolve_native_targets must
        return nil, acquisition refused, root hidden.
        """
        lua, ok = _make_base_lua()
        self.assertTrue(ok, "mandatory chunks missing")

        _set_host_anticipation(lua)
        _remove_native_text_panel(lua)

        lua.execute(r'''
            local state = managers.groupai:state()
            state._assault_mode = true
            state._task_data.assault.phase = "build"
            local corner = managers.hud._hud_assault_corner
            corner._assault = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local A = kyohud.hud.assault
            A:mount(managers.hud)
            A:update(managers.hud, 1.0, 0.05)

            _acquired = A._native_acquired
            _root_vis = A._root_panel:visible()
            _targets = A:_resolve_native_targets()
        ''')

        g = lua.globals()
        self.assertIsNone(g._targets,
            "RED: active assault missing text_panel => targets nil")
        self.assertFalse(bool(g._acquired),
            "RED: active assault missing text_panel => acquisition refused")
        self.assertFalse(bool(g._root_vis),
            "RED: acquisition refused => root hidden")

    def test_throwing_child_lookup_fails_closed(self):
        """RED: throwing bg:child("text_panel") must fail closed.

        If the child getter throws (not returns nil), pcall catches it
        but the lookup is not a clean nil. Must fail closed: no crash,
        no acquisition.
        """
        lua, ok = _make_base_lua()
        self.assertTrue(ok, "mandatory chunks missing")

        _set_host_anticipation(lua)

        lua.execute(r'''
            local corner = managers.hud._hud_assault_corner
            local bg = corner._bg_box
            local orig_child = bg.child
            bg.child = function(self, name)
                if name == "text_panel" then
                    error("text_panel unavailable")
                end
                return orig_child(self, name)
            end
            corner._assault = false

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local A = kyohud.hud.assault
            A:mount(managers.hud)

            _targets_ok, targets_result = pcall(function()
                return A:_resolve_native_targets()
            end)
            _acquired = A._native_acquired
        ''')

        g = lua.globals()
        self.assertTrue(bool(g._targets_ok),
            "_resolve_native_targets must not crash on throwing child")
        self.assertIsNone(g.targets_result,
            "RED: throwing child => targets nil (fail closed)")
        self.assertFalse(bool(g._acquired),
            "RED: throwing child => acquisition refused")

    def test_native_creation_reconciliation_14_requests(self):
        """RED: native text_panel creation reconciles to 14 requests.

        After first prep with 13 requests (no text_panel), native
        creates text_panel during build phase. corner._assault becomes
        true. Next update must detect target set change (even though
        corner identity is unchanged) and reconcile to 14 requests:
        13 visible=false + 1 alpha=0 for new text_panel.
        """
        lua, ok = _make_base_lua()
        self.assertTrue(ok, "mandatory chunks missing")

        _remove_native_text_panel(lua)
        _set_host_anticipation(lua)

        lua.execute(r'''
            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local A = kyohud.hud.assault
            A:mount(managers.hud)
            A:update(managers.hud, 1.0, 0.05)

            _root_id_before = tostring(A._root_panel)
            _req_before = A._native_requests and #A._native_requests or -1
            _acquired_before = A._native_acquired
        ''')
        g = lua.globals()
        self.assertEqual(int(g._req_before), 13,
            "baseline: 13 requests before native text_panel creation")
        self.assertTrue(bool(g._acquired_before),
            "baseline: must be acquired with 13 requests")

        _create_native_text_panel(lua)
        _set_host_build_active(lua)

        lua.execute(r'''
            local A = kyohud.hud.assault
            A:update(managers.hud, 2.0, 0.05)
            A:update(managers.hud, 2.1, 0.15)
            A:update(managers.hud, 2.3, 0.05)

            _root_id_after = tostring(A._root_panel)
            _acquired_after = A._native_acquired
            _req_after = A._native_requests and #A._native_requests or -1
            _has_alpha_after = false
            _alpha_target_name = nil
            if A._native_requests then
                for _, req in ipairs(A._native_requests) do
                    if req.property == "alpha" then
                        _has_alpha_after = true
                        _alpha_target_name = tostring(req.id)
                    end
                end
            end
            _new_tp_id = tostring(_new_tp)
            _alpha_matches_new_tp = (_alpha_target_name == _new_tp_id)
            _new_tp_alpha = _new_tp:alpha()
            _verify_after = A:_verify_render()
            _label_after = A:_resolve_status_label()
            _root_vis_after = A._root_panel:visible()
        ''')

        g = lua.globals()
        self.assertEqual(str(g._root_id_before), str(g._root_id_after),
            "same owned root panel after reconciliation")
        self.assertTrue(bool(g._acquired_after),
            "RED: must be acquired after native text_panel creation")
        self.assertEqual(int(g._req_after), 14,
            "RED: 14 requests after reconciliation"
            " (13 visible + 1 alpha), got " + str(g._req_after))
        self.assertTrue(bool(g._has_alpha_after),
            "RED: new text_panel must generate alpha=0 request")
        self.assertTrue(bool(g._alpha_matches_new_tp),
            "RED: alpha request target must be exactly _new_tp, got "
            + str(g._alpha_target_name) + " expected " + str(g._new_tp_id))
        self.assertEqual(float(g._new_tp_alpha), 0.0,
            "RED: _new_tp:alpha() must be 0 after acquisition, got "
            + str(g._new_tp_alpha))
        self.assertTrue(bool(g._root_vis_after),
            "RED: root must be visible after settling")
        self.assertTrue(bool(g._verify_after),
            "RED: _verify_render must be true after reconciliation and settling")
        self.assertEqual(str(g._label_after), "MONTEE",
            "label must be MONTEE during build phase")

        lua.execute(r'''
            kyohud.settings.enable_assault = false
            local A = kyohud.hud.assault
            A:update(managers.hud, 3.0, 0.05)
            _restored_alpha = _new_tp:alpha()
        ''')
        g = lua.globals()
        self.assertAlmostEqual(float(g._restored_alpha), 0.37, places=2,
            msg="RED: after release, _new_tp alpha must restore to 0.37, got "
            + str(g._restored_alpha))

    def test_active_assault_with_existing_text_panel_acquires_14(self):
        """Positive control: active assault with text_panel present
        acquires 14 requests (baseline for comparison).
        """
        lua, ok = _make_base_lua()
        self.assertTrue(ok, "mandatory chunks missing")

        lua.execute(r'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_assault = true
            local state = managers.groupai:state()
            state._assault_mode = true
            state._hunt_mode = false
            state._is_server = true
            state._task_data = state._task_data or {}
            state._task_data.assault = state._task_data.assault or {}
            state._task_data.assault.active = true
            state._task_data.assault.phase = "sustain"
            state._hostage_count = 0
            state._converted = {}
            Network._is_server = true
            local corner = managers.hud._hud_assault_corner
            corner._assault = true

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local A = kyohud.hud.assault
            A:mount(managers.hud)
            A:update(managers.hud, 1.0, 0.05)

            _acquired = A._native_acquired
            _req_count = A._native_requests and #A._native_requests or -1
            _has_alpha = false
            if A._native_requests then
                for _, req in ipairs(A._native_requests) do
                    if req.property == "alpha" then
                        _has_alpha = true
                    end
                end
            end
        ''')

        g = lua.globals()
        self.assertTrue(bool(g._acquired),
            "positive control: active assault with text_panel => acquired")
        self.assertEqual(int(g._req_count), 14,
            "positive control: 14 requests with text_panel present")
        self.assertTrue(bool(g._has_alpha),
            "positive control: text_panel alpha request present")


    def test_dead_child_text_panel_refused(self):
        """RED: dead text_panel child must be refused, not treated as absent.

        Only tp==nil qualifies as optional absent. A dead text_panel
        (alive=false) must fail closed: no acquisition, root hidden.
        """
        lua, ok = _make_base_lua()
        self.assertTrue(ok, "mandatory chunks missing")

        _set_host_anticipation(lua)

        lua.execute(r'''
            local corner = managers.hud._hud_assault_corner
            local bg = corner._bg_box
            local tp = bg:child("text_panel")
            if tp then
                tp._alive = false
            end
            corner._assault = false

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local A = kyohud.hud.assault
            A:mount(managers.hud)

            _targets_ok, targets_result = pcall(function()
                return A:_resolve_native_targets()
            end)
            _acquired = A._native_acquired
        ''')

        g = lua.globals()
        self.assertTrue(bool(g._targets_ok),
            "_resolve_native_targets must not crash on dead text_panel")
        self.assertIsNone(g.targets_result,
            "RED: dead text_panel => targets nil (fail closed)")
        self.assertFalse(bool(g._acquired),
            "RED: dead text_panel => acquisition refused")

    def test_unknown_inactive_missing_ticker_refused(self):
        """RED: unknown inactive state with missing ticker must refuse.

        When state is not active, not endless, NOT host anticipation,
        and NOT client prep (unknown inactive), tp_absent qualification
        must fail. No coerced qualification for unknown states.
        """
        lua, ok = _make_base_lua()
        self.assertTrue(ok, "mandatory chunks missing")

        _remove_native_text_panel(lua)

        lua.execute(r'''
            kyohud.settings.enable_hud_foundation = true
            kyohud.settings.enable_assault = true
            local state = managers.groupai:state()
            state._assault_mode = false
            state._hunt_mode = false
            state._is_server = true
            state._task_data = state._task_data or {}
            state._task_data.assault = state._task_data.assault or {}
            state._task_data.assault.active = false
            state._task_data.assault.phase = "sustain"
            state._hostage_count = 0
            state._converted = {}
            Network._is_server = true
            local corner = managers.hud._hud_assault_corner
            corner._assault = false
            corner._point_of_no_return = false
            corner._casing = false

            local RT = kyohud.hud.runtime
            RT:mount(managers.hud)
            local A = kyohud.hud.assault
            A:mount(managers.hud)
            A:update(managers.hud, 1.0, 0.05)

            _presenting = A._state.presenting
            _acquired = A._native_acquired
            _root_vis = A._root_panel:visible()
            _targets = A:_resolve_native_targets()
        ''')

        g = lua.globals()
        self.assertFalse(bool(g._presenting),
            "unknown inactive must not be presenting")
        self.assertIsNone(g._targets,
            "RED: unknown inactive with missing ticker => targets nil")
        self.assertFalse(bool(g._acquired),
            "RED: unknown inactive => acquisition refused")
        self.assertFalse(bool(g._root_vis),
            "RED: unknown inactive => root hidden")


if __name__ == "__main__":
    unittest.main()
